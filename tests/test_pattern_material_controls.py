"""Owner-facing pattern paint/spec controls across real dispatch and exports."""
import contextlib
import base64
import io
import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope='module')
def runtime():
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as engine
        engine._ensure_expansions_loaded()
    return engine


def test_blend_keeps_source_hue_saturation_and_strong_pattern_detail():
    from engine.pattern_paint_placement import composite_pattern_pixels
    source=np.full((64,64,3),(.8,.2,.04),np.float32)
    x=np.linspace(0,1,64,dtype=np.float32)
    art=np.empty_like(source);art[:,:,:]=x[None,:,None]*[.2,.7,1]
    mask=np.ones((64,64),np.float32);mask[:4]=0
    result=composite_pattern_pixels(source,art,mask,mode='blend')
    base_hsv=cv2.cvtColor(source,cv2.COLOR_RGB2HSV)
    actual_hsv=cv2.cvtColor(result,cv2.COLOR_RGB2HSV)
    np.testing.assert_allclose(actual_hsv[4:,:,:2],base_hsv[4:,:,:2],atol=.0001)
    assert np.ptp(actual_hsv[4:,:,2])>.6
    assert np.abs(result-source)[mask>0].mean()>.1
    np.testing.assert_array_equal(result[:4],source[:4])


@pytest.mark.parametrize('base', ['f_electroplate', 'fs_core_crimson'])
def test_real_exports_separate_color_controls_and_spec_amount(runtime,tmp_path,base):
    from engine.pattern_material import pattern_spec_plate
    root=tmp_path/('pattern-controls-'+uuid.uuid4().hex);root.mkdir()
    source=root/'source.png';Image.new('RGB',(128,128),(190,55,12)).save(source)
    pid='decade_80s_leg_warmer'
    zone=dict(name='Pattern controls',color='remaining',base=base,pattern=pid,
              intensity='100',base_color_mode='original',pattern_paint_mode='overlay',pattern_spec_opacity=0)
    cases={
        'none':{'pattern':'none'},'zero':{},'full':{'pattern_spec_opacity':1},
        'half':{'pattern_spec_opacity':.5},
        'paint_off':{'pattern_spec_opacity':1,'pattern_opacity':0,'pattern_spec_mult':0},
        'hue':{'pattern_hue_shift':120}, 'gray':{'pattern_saturation':-100},
        'small':{'pattern_spec_opacity':1,'scale':.4},
        'stack':{'pattern':'none','pattern_stack':[dict(id=pid,opacity=1,spec_opacity=1)]},
        'blend':{'pattern_paint_mode':'blend'},
    }
    results={}
    for name,options in cases.items():
        out=root/name;out.mkdir()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            runtime.build_multi_zone(str(source),str(out),[{**zone,**options}],
                iracing_id='PATTERN_CONTROL_TEST',seed=42,car_prefix='car_num')
        results[name]=(np.array(Image.open(out/'car_num_PATTERN_CONTROL_TEST.tga')),
                       np.array(Image.open(out/'car_spec_PATTERN_CONTROL_TEST.tga')))
    paint,spec=results['zero']
    np.testing.assert_array_equal(spec,results['none'][1])
    for key in ['full','half']:
        np.testing.assert_array_equal(results[key][0],paint)
    full=results['full'][1].astype(float)
    np.testing.assert_allclose(results['half'][1],(spec.astype(float)+full)/2,atol=1)
    np.testing.assert_array_equal(results['paint_off'][1],results['full'][1])
    np.testing.assert_array_equal(results['hue'][1],spec)
    np.testing.assert_array_equal(results['gray'][1],spec)
    np.testing.assert_array_equal(results['stack'][1],results['full'][1])
    assert np.abs(paint.astype(float)-results['hue'][0]).mean()>25
    assert np.ptp(results['gray'][0].astype(float),axis=2).max()<=1
    assert np.abs(paint.astype(float)-results['blend'][0]).mean()>25
    assert np.abs(results['small'][1].astype(float)-full).mean()>2
    expected=pattern_spec_plate(pid,(128,128),42,np.ones((128,128),np.float32))
    np.testing.assert_allclose(full[:,:,:3],expected,atol=1)
    expected_small=pattern_spec_plate(pid,(128,128),42,np.ones((128,128),np.float32),scale=.4)
    np.testing.assert_allclose(results['small'][1][:,:,:3],expected_small,atol=1)


def test_independent_spec_amount_preserves_mask_and_alpha(runtime):
    from engine.pattern_material import apply_zone_pattern_spec
    spec=np.full((64,64,4),(40,95,130,72),np.uint8)
    mask=np.ones((64,64),np.float32)
    zone=dict(pattern='decade_80s_leg_warmer',pattern_spec_opacity=0)
    assert apply_zone_pattern_spec(spec,zone,(64,64),mask,42) is spec
    result=apply_zone_pattern_spec(spec,{**zone,'pattern_spec_opacity':1},(64,64),mask,42)
    np.testing.assert_array_equal(result[:,:,3],spec[:,:,3])
    np.testing.assert_array_equal(spec[0,0],[40,95,130,72])


@pytest.mark.parametrize('target', [{'base':'f_electroplate'}, {'finish':'fs_core_crimson'}])
def test_actual_preview_route_forwards_pattern_controls(runtime,monkeypatch,target):
    with contextlib.redirect_stdout(io.StringIO()):
        import server
    seen=[]
    def preview(_path,zones,**kwargs):
        seen.extend(zones)
        return np.full((64,64,3),100,np.uint8),np.full((64,64,4),100,np.uint8),1.
    monkeypatch.setattr(server.engine,'preview_render',preview)
    monkeypatch.setattr(server,'_record_recent_render',lambda *a,**kw: None)
    buffer=io.BytesIO();Image.new('RGB',(64,64),(31,91,171)).save(buffer,format='PNG')
    fields=dict(pattern_paint_mode='blend',pattern_hue_shift=120,pattern_saturation=-70,
                pattern_spec_opacity=0,pattern_stack=[dict(id='decade_70s_funk_zigzag',spec_opacity=.5,hue_shift=-30,saturation=50)])
    zone=dict(name='Transport regression',color='remaining',pattern='decade_80s_leg_warmer',**target,**fields)
    response=server.app.test_client().post('/preview-render',json=dict(source_mode='live_flat_canvas',
        paint_image_base64=base64.b64encode(buffer.getvalue()).decode(),seed=42,zones=[zone],settings={}))
    assert response.status_code==200,response.get_json()
    assert len(seen)==1
    for key,value in fields.items():assert seen[0][key]==value,key
