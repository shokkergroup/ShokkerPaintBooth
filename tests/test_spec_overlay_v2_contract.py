"""Behavioral proof of v2 overlays; legacy pixels have a separate golden guard."""
import contextlib,io
import numpy as np
import pytest
from engine.spec_overlay_v2.contract import apply_material,opacity,seed,transform

def fixture_field(shape,seed,sm,**params):
    y,x=np.mgrid[:shape[0],:shape[1]].astype(np.float32)
    a=np.empty((*shape,4),np.float32)
    a[:,:,0]=(x%16)/15;a[:,:,1]=.1+.8*((y%13)/12)
    a[:,:,2]=np.where((x+y)%16<8,0,.9);a[:,:,3]=(x>shape[1]//4)*sm
    return a
fixture_field._spb_overlay_version=2

@pytest.fixture
def catalog(monkeypatch):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from engine.spec_patterns import PATTERN_CATALOG
    monkeypatch.setitem(PATTERN_CATALOG,'_v2_test',fixture_field)
    return PATTERN_CATALOG

def test_material_strength_is_linear_and_noop_is_exact():
    a=fixture_field((32,32),42,1);base=[np.full((32,32),v,np.float32) for v in [64,180,0]]
    assert all(np.array_equal(x,y) for x,y in zip(base,apply_material(a,*base,0)))
    half=apply_material(a,*base,.5);full=apply_material(a,*base,1)
    for i in range(3):assert np.allclose(half[i],(base[i]+full[i])*.5)
    assert np.array_equal(full[2][:,:9],base[2][:,:9])

@pytest.mark.parametrize('channels',['','M','R','C','MR','MC','RC','MRC'])
def test_channel_selection_and_transparent_area_are_exact(channels):
    a=fixture_field((32,32),42,1);base=[np.full((32,32),v,np.float32) for v in [64,180,0]]
    result=apply_material(a,*base,1,channels)
    for i,ch in enumerate('MRC'):
        assert np.array_equal(result[i][:,:9],base[i][:,:9])
        if ch not in channels:assert np.array_equal(result[i],base[i])

def test_seed_is_explicit_and_strength_has_no_hidden_sqrt():
    layer={'pattern':'_v2_test','opacity':.5}
    assert opacity(layer,fixture_field)==.5
    assert seed(layer,fixture_field,999,5000)==42
    assert seed({**layer,'seed':753},fixture_field,100,8000)==753
    assert opacity({**layer,'muted':True},fixture_field)==0

@pytest.mark.parametrize('composer',['single','stacked'])
def test_public_composer_clearcoat_and_zero_strength(catalog,composer):
    from engine.compose import compose_finish,compose_finish_stacked
    fn=compose_finish if composer=='single' else compose_finish_stacked
    args=('f_electroplate','none' if composer=='single' else [],(64,64),np.ones((64,64),np.float32),42,1.)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        base=fn(*args,dither=False)
        off=fn(*args,dither=False,spec_pattern_stack=[dict(pattern='_v2_test',opacity=0,channels='C')])
        on=fn(*args,dither=False,spec_pattern_stack=[dict(pattern='_v2_test',opacity=1,channels='C')])
    assert np.array_equal(base,off)
    assert np.array_equal(base[:,:,:2],on[:,:,:2])
    assert on[:,:,2].std()>20
    assert np.any(on[:,:,2]==0),'Explicit no-coat areas must survive final composition.'

def test_transform_keeps_coverage_and_material_values_separate():
    out=transform(fixture_field,(64,64),42,1,{},1.25,31,.5,.5,50)
    assert out.shape==(64,64,4)
    assert np.isfinite(out).all()
    assert out.min()>=0 and out.max()<=1.000001
    assert np.all(out[:8,:,3]==0)

def test_v2_legacy_id_fix_is_opt_in(catalog):
    from engine.compose import compose_finish_stacked
    args=('f_electroplate',[],(64,64),np.ones((64,64),np.float32),42,1.)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        base=compose_finish_stacked(*args,dither=False)
        old=compose_finish_stacked(*args,dither=False,spec_pattern_stack=[dict(pattern='hex_cells',opacity=.5,channels='C',range=40)])
        new=compose_finish_stacked(*args,dither=False,spec_pattern_stack=[dict(pattern='hex_cells',opacity=.5,channels='C',range=40,render_version=2,seed=42)])
    assert np.array_equal(base,old),'Unversioned saved recipes retain their prior result.'
    assert not np.array_equal(base[:,:,2],new[:,:,2]),'New layers get the corrected scalar-coat behavior.'

@pytest.mark.parametrize('composer',['single','stacked'])
def test_saved_mute_solo_and_empty_channels(catalog,composer):
    from engine.compose import compose_finish,compose_finish_stacked
    fn=compose_finish if composer=='single' else compose_finish_stacked
    args=('f_electroplate','none' if composer=='single' else [],(64,64),np.ones((64,64),np.float32),42,1.)
    modern=dict(pattern='_v2_test',opacity=.8,channels='MRC',render_version=2,seed=42)
    legacy=dict(pattern='hex_cells',opacity=.5,channels='MR',seed=71)
    def render(stack):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):return fn(*args,dither=False,spec_pattern_stack=stack)
    assert np.array_equal(render([]),render([{**modern,'channels':''}]))
    assert np.array_equal(render([modern]),render([legacy,{**modern,'solo':True}]))
    assert np.array_equal(render([legacy]),render([{**legacy,'solo':True},modern]))
    assert np.array_equal(render([legacy]),render([legacy,{**modern,'muted':True}]))

def test_material_stack_order_and_each_base_mask(catalog):
    from engine.spec_overlay_v2.compose import apply_stacks
    base=np.full((64,64,3),128,np.uint8);mask=np.ones((64,64),np.float32)
    left=mask.copy();left[:,32:]=0
    a=dict(pattern='_v2_test',opacity=.8,channels='MRC',seed=42)
    b={**a,'rotation':90}
    ab=apply_stacks(base,[a,b],{},mask,42,1);ba=apply_stacks(base,[b,a],{},mask,42,1)
    assert not np.array_equal(ab,ba)
    for key in ['overlay_spec_pattern_stack','third_overlay_spec_pattern_stack','fourth_overlay_spec_pattern_stack','fifth_overlay_spec_pattern_stack']:
        scoped=apply_stacks(base,[],{key:[a]},mask,42,1,{key:left},['authored']*4)
        assert np.array_equal(scoped[:,32:],base[:,32:])
        assert not np.array_equal(scoped[:,:32],base[:,:32])
        absent=apply_stacks(base,[],{key:[a]},mask,42,1,{key:mask*0},['authored']*4)
        assert np.array_equal(absent,base),'A hidden side base must not spill over the whole zone.'

def test_inspector_and_composer_apply_the_same_settings(catalog):
    from engine.spec_overlay_v2.preview import render_native
    from engine.spec_overlay_v2.compose import apply_stacks
    layer=dict(pattern='_v2_test',opacity=.37,channels='RC',scale=.65,rotation=27,offset_x=.21,offset_y=.73,box_size=40,seed=781)
    _,preview=render_native('_v2_test',seed=781,strength=.37,settings=layer)
    base=np.full((2048,2048,3),128,np.uint8)
    actual=apply_stacks(base,[layer],{},np.ones((2048,2048),np.float32),88,1)
    assert np.array_equal(preview,actual)

def test_explicit_variation_survives_a_fresh_python_process():
    import subprocess,sys,os,json
    code="import hashlib;from engine.spec_overlay_v2.preview import render_native;print('RESULT:'+hashlib.sha256(render_native('spov2_truchet_switchyard',seed=572)[1].tobytes()).hexdigest())"
    hashes=[]
    for hash_seed in ['113','907']:
        output=subprocess.check_output([sys.executable,'-c',code],env={**os.environ,'PYTHONHASHSEED':hash_seed},text=True)
        hashes.append(output.split('RESULT:')[-1].strip())
    assert hashes[0]==hashes[1]

@pytest.mark.parametrize('base,mode',[('metallic','original'),('astra_cobalt_guillotine','special')])
def test_real_tga_exports_preserve_paint_bytes_with_one_and_five_layers(tmp_path,base,mode):
    import uuid
    tmp_path=tmp_path/('spec-v2-'+uuid.uuid4().hex);tmp_path.mkdir()
    from PIL import Image
    import shokker_engine_v2 as engine
    y,x=np.mgrid[:512,:512];paint=np.stack((x%256,y%256,(x+y)%256),axis=2).astype(np.uint8)
    source=tmp_path/'source.png';Image.fromarray(paint).save(source)
    baseline=None;spec_base=None
    ids=['spov2_toolpath_reversal','spov2_braided_junction','spov2_crystal_front','spov2_denticle_armor','spov2_tidal_meniscus']
    for count in [0,1,5]:
        target=tmp_path/str(count);target.mkdir()
        zone=dict(name='Overlay export fixture',color='remaining',base=base,pattern='none',intensity='100',base_color_mode=mode)
        if mode=='special':zone['base_color_source']=base
        zone['spec_pattern_stack']=[dict(pattern=pid,opacity=.65,channels='MRC',render_version=2,seed=42) for pid in ids[:count]]
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            engine.build_multi_zone(str(source),str(target),[zone],iracing_id='V2_TEST',seed=42,car_prefix='car_num')
        paint_bytes=(target/'car_num_V2_TEST.tga').read_bytes();spec_bytes=(target/'car_spec_V2_TEST.tga').read_bytes()
        if count==0:baseline=paint_bytes;spec_base=spec_bytes
        else:
            assert paint_bytes==baseline
            assert spec_bytes!=spec_base
