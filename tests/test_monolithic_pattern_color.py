"""The real Soul Core + PATTERN route must obey the regular overlay contract."""
import contextlib
import io
import uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def runtime():
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as engine
        engine._ensure_expansions_loaded()
        from engine.registry import PATTERN_REGISTRY
        from engine.compose import compose_paint_mod
    return engine, PATTERN_REGISTRY, compose_paint_mod


@pytest.mark.parametrize('pid', ['decade_80s_leg_warmer', 'decade_70s_funk_zigzag',
                               'decade_60s_peter_max_gradient'])
@pytest.mark.parametrize('mode', ['overlay', 'blend'])
def test_monolithic_matches_regular_plate_with_placement_and_mask(runtime, pid, mode):
    engine, _, primary = runtime
    shape=(128,128); y,x=np.mgrid[:128,:128]
    source=np.stack([x/127,y/127,1-x/127],axis=2).astype(np.float32)
    mask=np.ones(shape,np.float32);mask[:16]=0;mask[:,110:]=0
    controls=dict(pattern_offset_x=.68,pattern_offset_y=.35,pattern_flip_h=True,
                  pattern_flip_v=True,pattern_fit_zone=True)
    zone=dict(pattern_paint_mode=mode,pattern_spec_mult=.8,pattern_intensity='75',**controls)
    with contextlib.redirect_stdout(io.StringIO()):
        expected=primary('metallic',pid,source.copy(),shape,mask,42,1,0,
            base_strength=0,pattern_paint_mode=mode,
            spec_mult=.8,pattern_intensity=.75,scale=.4,rotation=25,**controls)
        expected=source*.5+expected*.5  # Regular zone dispatcher applies opacity once.
        actual=engine.overlay_pattern_paint(source.copy(),pid,shape,mask,42,.01,99,
            scale=.4,rotation=25,opacity=.5,zone=zone)
    np.testing.assert_allclose(actual,expected,atol=1e-6)
    np.testing.assert_array_equal(actual[mask==0],source[mask==0])


@pytest.mark.parametrize('target_key',['finish','base'])
@pytest.mark.parametrize('pid',['248169','decade_80s_leg_warmer','decade_70s_funk_zigzag'])
def test_actual_soul_core_tga_full_half_zero_and_stack(runtime,tmp_path,target_key,pid):
    engine,registry,_=runtime
    from engine.pattern_artwork import pattern_color_source,load_pattern_artwork
    tmp_path=tmp_path/('mono-color-'+uuid.uuid4().hex);tmp_path.mkdir()
    source=tmp_path/'source.png';Image.new('RGB',(128,128),(30,80,160)).save(source)
    zone=dict(name='Soul Core regression',color='remaining',intensity='100',
              pattern=pid,base_color_mode='original',**{target_key:'fs_core_crimson'})
    cases={'full':{},'half':{'pattern_opacity':.5},'zero':{'pattern_opacity':0},
           'strength_zero':{'pattern_spec_mult':0},'none':{'pattern':'none'},
           'stack':{'pattern':'none','pattern_stack':[dict(id=pid,opacity=1)]}}
    results={}
    for label,extra in cases.items():
        out=tmp_path/label;out.mkdir()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            engine.build_multi_zone(str(source),str(out),[{**zone,**extra}],
                iracing_id='MONO_TEST',seed=42,car_prefix='car_num')
        results[label]=np.asarray(Image.open(out/'car_num_MONO_TEST.tga'),dtype=float)
    art=load_pattern_artwork(pattern_color_source(pid,registry[pid],'overlay'),(128,128))
    np.testing.assert_allclose(results['full'],art[:,:,:3]*255,atol=1)
    np.testing.assert_allclose(results['half'],(results['full']+results['none'])/2,atol=1)
    for label in ('zero','strength_zero'):
        np.testing.assert_array_equal(results[label],results['none'])
    np.testing.assert_array_equal(results['stack'],results['full'])
