import base64
import copy
import zlib
import numpy as np
import pytest
from engine.zone_material_instances import apply_instances
from engine.zone_material_snapshot import encode, decode

def fixture():
    paint=np.arange(16*16*3,dtype=np.uint8).reshape(16,16,3)
    spec=np.arange(16*16*4,dtype=np.uint8).reshape(16,16,4)
    spec[:,:,3]=0
    mask=np.ones((16,16),np.float32);mask[2:4,2:4]=.371234
    original=paint.copy();original[1:5,1:5,0]=0
    record=dict(version=2,id='copy',documentWidth=16,documentHeight=16,
        sourceBbox=dict(x1=1,y1=1,x2=5,y2=5),instanceBbox=dict(x1=8,y1=7,x2=12,y2=11),rotation=30)
    zone=dict(material_instances=[record],_material_capture_ids=['copy'])
    return paint,spec,mask,original,record,zone

def test_native_capture_unlink_exact_and_independent_after_source_change():
    p,s,m,original,record,zone=fixture()
    before=apply_instances(p,s,[zone],[m],source_paint=original)
    record['frozenMaterial']=zone['_material_captures']['copy'];record['detached']=True
    after=apply_instances(p,s,[zone],[m],source_paint=original)
    for a,b in zip(before,after):np.testing.assert_array_equal(a,b)
    newp,news,newm=p.copy(),s.copy(),m.copy()
    newp[1:5,1:5]=200;news[1:5,1:5]=99;newm[1:5,1:5]=0
    independent=apply_instances(newp,news,[zone],[newm],source_paint=original)
    for a,b in zip(before,independent):np.testing.assert_array_equal(a[5:13,6:14],b[5:13,6:14])
    assert len(zone['material_instances'])==1

def test_fractional_coverage_and_alpha_zero_roundtrip_lossless():
    p,s,m,original,record,zone=fixture()
    snapshot=encode(p,s,m,m*.33333)
    for a,b in zip((p,s,m,m*.33333),decode(snapshot)):np.testing.assert_array_equal(a,b)

def test_spec_only_detach_never_copies_underlying_art():
    p,s,m,original,record,zone=fixture()
    apply_instances(p,s,[zone],[m],source_paint=p)
    record['frozenMaterial']=zone['_material_captures']['copy']
    assert not decode(record['frozenMaterial'])[0].any(), 'Unowned artwork is not retained in a snapshot'
    new=p.copy();new[1:5,1:5]=255
    out,_=apply_instances(new,s,[zone],[m],source_paint=original)
    np.testing.assert_array_equal(out,new)

def test_frozen_copy_preview_geometry_uses_native_snapshot_dimensions():
    p,s,m,original,record,zone=fixture();record['rotation']=0
    apply_instances(p,s,[zone],[m],source_paint=original)
    record['frozenMaterial']=zone['_material_captures']['copy']
    smallp=np.zeros((8,8,3),np.uint8);smalls=np.zeros((8,8,4),np.uint8)
    outp,outs=apply_instances(smallp,smalls,[zone],source_paint=smallp)
    delta=np.any(outs,axis=2);ys,xs=np.where(delta)
    assert xs.min()>=4 and xs.max()<=5 and ys.min()>=3 and ys.max()<=5

def test_preview_capture_keeps_exact_visible_material_in_its_own_resolution():
    p,s,m,original,record,zone=fixture()
    apply_instances(p,s,[zone],[m],source_paint=original)
    native=zone['_material_captures']['copy']
    smallp=p[::2,::2].copy();smalls=s[::2,::2].copy();smallm=m[::2,::2].copy()
    before=apply_instances(smallp,smalls,[zone],[smallm],source_paint=original[::2,::2])
    preview=zone['_material_captures']['copy']
    record['frozenMaterial']={**native,'preview':dict(documentWidth=8,documentHeight=8,material=preview)}
    after=apply_instances(smallp,smalls,[zone],[smallm],source_paint=original[::2,::2])
    for a,b in zip(before,after):np.testing.assert_array_equal(a,b)

def test_route_capture_resolves_filtered_zone_index_and_retains_native_mask():
    from server_routes.zone_material_capture import prepare_capture
    p,s,m,original,record,zone=fixture()
    zone['region_mask']=m.copy()
    plan=prepare_capture(dict(zoneIndex=4,id='copy'),[{},zone])
    assert plan.zone is zone
    zone['region_mask']=m[::2,::2]
    zone['_material_captures']={'copy':encode(p[::2,::2],s[::2,::2],m[::2,::2],m[::2,::2])}
    called=[]
    def render(path,zones,**options):
        called.append(options)
        np.testing.assert_array_equal(zones[1]['region_mask'],m)
        zones[1]['_material_captures']={'copy':encode(p,s,m,m)}
        return p,s,1
    response=plan.finish((p[::2,::2],s[::2,::2],1),.5,render,'source',seed=51)
    assert response['resolution']==[16,16]
    assert response['material_capture']['preview']['documentWidth']==8
    assert called==[dict(preview_scale=1.0,seed=51)]
    assert prepare_capture(None,[]) is None

def test_promoted_master_supplies_members_and_source_proxy_without_geometry_collapse():
    p,s,m,original,record,zone=fixture();record['rotation']=0;m[:]=1
    apply_instances(p,s,[zone],[m],source_paint=original)
    record['frozenMaterial']=zone['_material_captures']['copy'];record['masterId']='copy'
    proxy={**record,'id':'source','instanceBbox':copy.deepcopy(record['sourceBbox']),'isSource':True}
    del proxy['frozenMaterial']
    peer={**record,'id':'peer','instanceBbox':dict(x1=11,y1=11,x2=15,y2=15)}
    del peer['frozenMaterial']
    zone['material_instances']=[record,proxy,peer]
    before=apply_instances(p,s,[zone],[m],source_paint=original)
    edited=s.copy();edited[1:5,1:5]=42
    after=apply_instances(p,edited,[zone],[m],source_paint=original)
    np.testing.assert_array_equal(before[1],after[1])
    peer['frozenMaterial']=encode(p[1:5,1:5],np.full((4,4,4),37,np.uint8),m[1:5,1:5],m[1:5,1:5])
    override=apply_instances(p,s,[zone],[m],source_paint=original)
    assert np.any(override[1][11:15,11:15]!=before[1][11:15,11:15])
    del peer['frozenMaterial']
    synced=apply_instances(p,s,[zone],[m],source_paint=original)
    np.testing.assert_array_equal(synced[1],before[1])

def test_odd_source_preview_bounds_preserve_the_entire_original_region():
    p=np.zeros((8,8,3),np.uint8);s=np.zeros((8,8,4),np.uint8)
    s[1:4,1:4]=[200,70,99,0]
    record=dict(version=2,id='master',documentWidth=16,documentHeight=16,
        sourceBbox=dict(x1=3,y1=3,x2=7,y2=7),instanceBbox=dict(x1=10,y1=8,x2=14,y2=12),masterId='master')
    zone=dict(material_instances=[record],_material_capture_ids=['master'])
    apply_instances(p,s,[zone],source_paint=p)
    material=zone['_material_captures']['master'];assert (material['width'],material['height'])==(3,3)
    record['frozenMaterial']=material
    proxy={**record,'id':'source','instanceBbox':dict(record['sourceBbox']),'isSource':True}
    del proxy['frozenMaterial'];zone['material_instances'].append(proxy)
    before=apply_instances(p,s,[zone],source_paint=p)
    edited=s.copy();edited[1:4,1:4]=[100,35,50,0]
    after=apply_instances(p,edited,[zone],source_paint=p)
    np.testing.assert_array_equal(before[1],after[1])

@pytest.mark.parametrize('mutation',[
    lambda v:v.update(width=0),lambda v:v.update(width=999999),
    lambda v:v.update(data='broken'),lambda v:v.update(data=base64.b64encode(zlib.compress(b'wrong')).decode()),
])
def test_invalid_snapshot_rejected(mutation):
    p,s,m,*_=fixture();value=encode(p,s,m,m);mutation(value)
    with pytest.raises((ValueError,zlib.error)):decode(value)
