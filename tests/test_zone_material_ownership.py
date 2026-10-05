import copy
from pathlib import Path
import ast
import numpy as np
import pytest
from engine.zone_material_ownership import release_source_footprints
from engine.zone_material_snapshot import encode
from engine.zone_material_instances import apply_instances

def fixture():
    mask=np.zeros((12,12),np.float32);mask[2:5,1:4]=1
    p=np.zeros((3,3,3),np.uint8);s=np.full((3,3,4),[240,17,80,0],np.uint8)
    content=encode(p,s,np.ones((3,3),np.float32),np.zeros((3,3),np.float32))
    master=dict(version=2,id='master',sourceBbox=dict(x1=1,y1=2,x2=4,y2=5),instanceBbox=dict(x1=7,y1=7,x2=10,y2=10),documentWidth=12,documentHeight=12,frozenMaterial=content,masterId='master')
    source={**copy.deepcopy(master),'id':'source','isSource':True,'instanceBbox':dict(master['sourceBbox'])}
    del source['frozenMaterial']
    return mask,master,source,dict(material_instances=[master,source])

def test_unchanged_source_keeps_original_material_and_no_copy_tax():
    mask,master,source,zone=fixture()
    assert release_source_footprints(mask,zone) is mask
    assert release_source_footprints(mask,{}) is mask

def test_moved_source_releases_only_old_footprint_and_reveals_lower_material():
    mask,master,source,zone=fixture();original=mask.copy()
    source['instanceBbox']=dict(x1=5,y1=1,x2=8,y2=4)
    released=release_source_footprints(mask,zone)
    np.testing.assert_array_equal(mask,original);assert not released.any()
    paint=np.full((12,12,3),100,np.uint8)
    lower_spec=np.full((12,12,4),[5,90,16,0],np.uint8)
    # A lower Zone owns the released region before independent materials compose.
    pp,ss=apply_instances(paint,lower_spec,[zone],[released],source_paint=paint)
    np.testing.assert_array_equal(pp,paint)
    np.testing.assert_array_equal(ss[2:5,1:4],lower_spec[2:5,1:4])
    assert np.all(ss[1:4,5:8]==[240,17,80,0])
    assert np.all(ss[7:10,7:10]==[240,17,80,0])

def test_preview_release_covers_odd_source_origin_without_erasing_other_mask():
    mask,master,source,zone=fixture()
    source.update(documentWidth=24,documentHeight=24,sourceBbox=dict(x1=3,y1=5,x2=7,y2=9),instanceBbox=dict(x1=12,y1=12,x2=16,y2=16))
    mask[:]=1
    out=release_source_footprints(mask,zone);expected=mask.copy();expected[2:5,1:4]=0
    np.testing.assert_array_equal(out,expected)

@pytest.mark.parametrize('change',[dict(rotation=30),dict(muted=True)])
def test_rotation_or_muting_releases_source(change):
    mask,master,source,zone=fixture();source.update(change)
    assert not release_source_footprints(mask,zone).any()

def test_detached_source_retains_ownership_without_a_master():
    mask,master,source,zone=fixture()
    source.update(detached=True,frozenMaterial=master['frozenMaterial'],instanceBbox=dict(x1=8,y1=1,x2=11,y2=4))
    zone['material_instances']=[source]
    assert not release_source_footprints(mask,zone).any()

@pytest.mark.parametrize('change',[dict(masterId='missing'),dict(documentWidth=0),dict(rotation='bad'),dict(sourceBbox=None)])
def test_incomplete_record_cannot_erase_source(change):
    mask,master,source,zone=fixture();source.update(instanceBbox=dict(x1=8,y1=1,x2=11,y2=4),**change)
    assert release_source_footprints(mask,zone) is mask

def test_actual_engine_applies_release_to_shape_color_and_remainder_masks():
    tree=ast.parse(Path('shokker_engine_v2.py').read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_multi_zone')
    calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_release_material_source']
    assert len(calls)==3
    assert sorted(n.args[0].id for n in calls)==['mask','mask','remainder_mask']
