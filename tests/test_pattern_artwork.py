"""Owner09-07: full-color pattern output must use the artwork shown in the picker."""
import contextlib, io, json, re, uuid
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def runtime():
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as engine
        from engine.compose import compose_paint_mod, compose_paint_mod_stacked
        from engine.registry import PATTERN_REGISTRY
    return engine,compose_paint_mod,compose_paint_mod_stacked,PATTERN_REGISTRY


@pytest.mark.parametrize('pid',['decade_80s_leg_warmer','decade_70s_funk_zigzag'])
def test_full_overlay_reproduces_authored_native_pixels(runtime,pid):
    engine,primary,stacked,registry=runtime
    path=ROOT/engine._SPB_REGULAR_IMAGE_OVERRIDES[pid]
    expected=np.array(Image.open(path).convert('RGB'),dtype=np.float32)/255
    shape=expected.shape[:2];source=np.full(expected.shape,(.03,.1,.35),np.float32)
    mask=np.ones(shape,np.float32);mask[:8,:]=0
    opts=dict(base_strength=0,pattern_paint_mode='overlay')
    with contextlib.redirect_stdout(io.StringIO()):
        actual=primary('metallic',pid,source.copy(),shape,mask,42,1,0,**opts)
        stacked_actual=stacked('metallic',[dict(id=pid,opacity=1)],source.copy(),shape,mask,42,1,0,**opts)
    np.testing.assert_allclose(actual[mask>0],expected[mask>0],atol=1e-6)
    assert np.array_equal(actual[mask==0],source[mask==0])
    np.testing.assert_allclose(stacked_actual,actual,atol=1e-6)


def test_all_decades_match_their_authored_color_content(runtime):
    engine,primary,_,registry=runtime
    catalog=(ROOT/'paint-booth-0-finish-data.js').read_text(encoding='utf-8')
    ids=json.loads(re.search(r'Decades 50s-80s": (\[[^\n]+\])',catalog).group(1))
    from engine.pattern_artwork import pattern_color_source,load_pattern_artwork
    shape=(160,160);source=np.full((*shape,3),.3,np.float32);mask=np.ones(shape,np.float32)
    for pid in ids:
        path=pattern_color_source(pid,registry[pid],'overlay')
        if path:
            art=np.array(Image.open(ROOT/path).convert('RGB'),dtype=float)/255
        else:
            authored=registry[pid].get('_spb_authored_paint_fn')
            assert callable(authored),pid
            art=authored(np.full_like(source,.5),shape,mask,42,1.8,0)
        with contextlib.redirect_stdout(io.StringIO()):
            actual=primary('metallic',pid,source.copy(),shape,mask,42,1,0,base_strength=0,pattern_paint_mode='overlay')
        # Colored authored assets cannot silently become achromatic in the renderer.
        if np.ptp(art,axis=2).mean()>.1:
            assert np.ptp(actual,axis=2).mean()>.035,pid
        elif not path:
            assert np.ptp(actual,axis=2).max()>.05,pid


def test_authored_alpha_dark_pixels_placement_and_cache_isolation(runtime,monkeypatch,tmp_path):
    _,primary,stacked,registry=runtime
    from engine.spec_paint import paint_none
    from engine.render import _load_color_image_pattern
    path=tmp_path/('alpha-'+uuid.uuid4().hex+'.png')
    pixels=np.zeros((64,64,4),np.uint8);pixels[:,:,:]=[0,0,0,255]
    pixels[:,16:32]=[255,255,255,255];pixels[:,32:48]=[255,0,70,96];pixels[:,48:]=[15,200,255,0]
    Image.fromarray(pixels).save(path)
    monkeypatch.setitem(registry,'_artwork_alpha_test',dict(image_path=str(path),paint_fn=paint_none))
    source=np.full((64,64,3),(.2,.5,.8),np.float32);mask=np.ones((64,64),np.float32)
    alpha=pixels[:,:,3:4].astype(np.float32)/255
    expected=source*(1-alpha)+(pixels[:,:,:3].astype(np.float32)/255)*alpha
    _load_color_image_pattern(str(path),(64,64))  # Warm legacy key-out cache first.
    opts=dict(base_strength=0,pattern_paint_mode='overlay')
    with contextlib.redirect_stdout(io.StringIO()):
        center=primary('metallic','_artwork_alpha_test',source.copy(),(64,64),mask,42,1,0,**opts)
        moved=primary('metallic','_artwork_alpha_test',source.copy(),(64,64),mask,42,1,0,pattern_offset_x=.7,**opts)
        repeated=primary('metallic','_artwork_alpha_test',source.copy(),(64,64),mask,42,1,0,**opts)
        stack=stacked('metallic',[dict(id='_artwork_alpha_test',opacity=1,offset_x=.7)],source.copy(),(64,64),mask,42,1,0,**opts)
    np.testing.assert_allclose(center,expected,atol=1e-6)
    assert np.array_equal(center,repeated)
    assert not np.array_equal(center,moved)
    np.testing.assert_allclose(moved,stack,atol=1e-6)


def test_browser_fingerprint_tracks_authored_color_before_first_render(runtime,monkeypatch):
    engine,_,_,registry=runtime
    with contextlib.redirect_stdout(io.StringIO()):
        import server
    pid='decade_60s_peter_max_gradient'
    real_entry=dict(registry[pid]);legacy_entry=dict(real_entry)
    legacy_entry.pop('_spb_authored_paint_fn',None)
    # Startup may still expose the older, separate legacy entry. The picker
    # already resolves original color from engine.registry at this point.
    monkeypatch.setattr(engine,'PATTERN_REGISTRY',{**engine.PATTERN_REGISTRY,pid:legacy_entry})
    server._PICKER_RENDERER_HASH_MEMO.clear()
    colored=server._picker_finish_renderer_hash('pattern',pid)
    monkeypatch.setitem(registry,pid,{**real_entry,'_spb_authored_paint_fn':None})
    server._PICKER_RENDERER_HASH_MEMO.clear()
    missing_color=server._picker_finish_renderer_hash('pattern',pid)
    assert colored!=missing_color
    server._PICKER_RENDERER_HASH_MEMO.clear()


@pytest.mark.parametrize('pid',['248169','decade_80s_leg_warmer','decade_70s_funk_zigzag'])
def test_real_export_full_color_and_linear_opacity(runtime,tmp_path,pid):
    engine,_,_,registry=runtime
    from engine.pattern_artwork import pattern_color_source,load_pattern_artwork
    target=tmp_path/('art-export-'+uuid.uuid4().hex);target.mkdir()
    source=target/'source.png';Image.new('RGB',(256,256),(17,37,71)).save(source)
    result={}
    zone=dict(name='Authored color fixture',color='remaining',base='metallic',pattern=pid,intensity='100',base_color_mode='original')
    for label,amount in [('full',1),('half',.5),('zero',0)]:
        out=target/label;out.mkdir()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            engine.build_multi_zone(str(source),str(out),[{**zone,'pattern_opacity':amount}],iracing_id='COLOR_TEST',seed=42,car_prefix='car_num')
        result[label]=np.array(Image.open(out/'car_num_COLOR_TEST.tga')).astype(float)
    artwork=load_pattern_artwork(pattern_color_source(pid,registry[pid],'overlay'),(256,256))
    np.testing.assert_allclose(result['full'],artwork[:,:,:3]*255,atol=1)
    np.testing.assert_allclose(result['half'],(result['full']+result['zero'])/2,atol=1)
    assert np.ptp(result['full'],axis=2).mean()>30
