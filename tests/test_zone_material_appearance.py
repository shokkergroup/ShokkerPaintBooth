import colorsys
import copy
import math
import numpy as np
import pytest
from engine.zone_material_snapshot import encode,decode
from engine.zone_material_appearance import match_material,rgb_to_hsl,hsl_to_rgb
from engine.zone_material_instances import apply_instances
from server_routes.zone_material_capture import prepare_capture

def material(rgb,mask=None):
    p=np.array(rgb,dtype=np.uint8).reshape(2,3,3)
    m=np.ones((2,3),np.float32) if mask is None else mask
    s=np.arange(24,dtype=np.uint8).reshape(2,3,4);s[:,:,3]=0
    return encode(p,s,m,m)

def fixture():
    target=material([[200,20,60],[40,170,100],[10,30,220],[120,120,120],[140,90,20],[70,180,190]])
    master=material([[80,130,150],[90,150,110],[140,80,130],[140,150,160],[70,80,140],[150,90,70]])
    return target,master

@pytest.mark.parametrize('mode',['hue','saturation','vibrance'])
def test_matches_independent_colorsys_reference_and_preserves_spec_masks(mode):
    target,master=fixture();p,s,m,pm=decode(target);mp,*_=decode(master)
    hls=[colorsys.rgb_to_hls(*(rgb/255)) for rgb in mp.reshape(-1,3)]
    hue=math.degrees(math.atan2(sum(math.sin(h*math.tau)*sat for h,l,sat in hls),sum(math.cos(h*math.tau)*sat for h,l,sat in hls)))%360
    saturation=sum(sat for h,l,sat in hls)/len(hls)
    expected=[]
    for rgb in p.reshape(-1,3):
        h,l,sat=colorsys.rgb_to_hls(*(rgb/255));h*=360
        if mode=='hue':h=(h+((hue-h+540)%360-180)*.85)%360;sat+=(saturation-sat)*.6
        else:sat+=(saturation-sat)*((1-sat)*.9 if mode=='vibrance' else .85)
        expected.append([math.floor(c*255+.5) for c in colorsys.hls_to_rgb(h/360,l,sat)])
    result,stats=match_material(target,master,mode);out=decode(result)
    np.testing.assert_array_equal(out[0],np.array(expected).reshape(p.shape))
    for a,b in zip(out[1:],(s,m,pm)):np.testing.assert_array_equal(a,b)
    assert stats['changedPixels']>0

def test_tint_is_half_master_paint_and_keeps_target_coverage():
    target,master=fixture();p,s,m,pm=decode(target);mp,*_=decode(master)
    result,stats=match_material(target,master,'tint');out=decode(result)
    np.testing.assert_array_equal(out[0],np.floor((p.astype(float)+mp)/2+.5).astype(np.uint8))
    for a,b in zip(out[1:],(s,m,pm)):np.testing.assert_array_equal(a,b)
    assert stats['changedPixels']==6

def test_fractional_and_empty_paint_coverage_remain_exact():
    target,master=fixture();p,s,m,pm=decode(target);pm=np.array([[1,.3,0],[.7,0,1]],np.float32)
    target=encode(p,s,m,pm)
    result,_=match_material(target,master,'hue');out=decode(result)
    np.testing.assert_array_equal(out[3],pm);np.testing.assert_array_equal(out[1],s)
    assert not out[0][pm==0].any()
    empty=encode(p,s,m,np.zeros_like(pm))
    result,stats=match_material(empty,master,'hue')
    assert result==empty and stats['changedPixels']==0 and stats['ownedPaintPixels']==0

def test_identical_tint_is_a_noop_and_rgb_roundtrip_is_exact():
    target,_=fixture();result,stats=match_material(target,target,'tint')
    assert result==target and stats['changedPixels']==0
    p=decode(target)[0];np.testing.assert_array_equal(hsl_to_rgb(*rgb_to_hsl(p)),p)

def test_batch_captures_members_and_one_canonical_master_in_two_renders():
    target,master=fixture()
    p=np.zeros((8,8,3),np.uint8);s=np.zeros((8,8,4),np.uint8)
    p[1:3,1:4]=decode(master)[0]
    records=[dict(version=2,id=id,sourceBbox=dict(x1=1,y1=1,x2=4,y2=3),instanceBbox=dict(x1=4,y1=4,x2=7,y2=6),documentWidth=8,documentHeight=8,frozenMaterial=copy.deepcopy(target)) for id in ['a','b']]
    zone=dict(material_instances=records);plan=prepare_capture(dict(zoneIndex=4,ids=['a','b'],appearance='hue'),[zone])
    assert len(zone['material_instances'])==3
    calls=[]
    def render(path,zones,**options):
        calls.append(options['preview_scale'])
        return (*apply_instances(p,s,zones,source_paint=np.full_like(p,255)),1)
    result=render('source',[zone],preview_scale=.5)
    response=plan.finish(result,.5,render,'source')
    assert calls==[.5,1.0] and set(response['material_captures'])=={'a','b'}
    for value in response['material_captures'].values():
        assert value['operation']['changedPixels']>0 and value['operation']['previewChangedPixels']>0
        np.testing.assert_array_equal(decode(value)[1],decode(target)[1])

def test_explicit_master_is_captured_instead_of_original_zone_material():
    target,master=fixture()
    record=dict(version=2,id='member',sourceBbox=dict(x1=1,y1=1,x2=4,y2=3),instanceBbox=dict(x1=4,y1=4,x2=7,y2=6),documentWidth=8,documentHeight=8,masterId='master',frozenMaterial=target)
    leader={**record,'id':'master','frozenMaterial':master}
    zone=dict(material_instances=[record,leader]);plan=prepare_capture(dict(zoneIndex=0,id='member',appearance='tint'),[zone])
    p=np.zeros((8,8,3),np.uint8);s=np.zeros((8,8,4),np.uint8)
    result=(*apply_instances(p,s,[zone],source_paint=p),1)
    response=plan.finish(result,1,None,'source')
    expected,_=match_material(target,master,'tint')
    np.testing.assert_array_equal(decode(response['material_capture'])[0],decode(expected)[0])
