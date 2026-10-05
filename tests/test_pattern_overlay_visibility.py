"""Owner09-07: full pattern overlays, linear controls, isolated placement/export."""
import contextlib
import io
import numpy as np
import pytest


@pytest.fixture(scope='module')
def composers():
    with contextlib.redirect_stdout(io.StringIO()):
        from engine.compose import compose_paint_mod, compose_paint_mod_stacked
    return compose_paint_mod, compose_paint_mod_stacked


def fixture():
    shape = (256, 256)
    source = np.full((*shape, 3), (.34, .025, .075), np.float32)
    source[80:110, 95:145] = (.95, .8, .03)
    mask = np.zeros(shape, np.float32); mask[20:230, 15:240] = 1
    mask[80:110, 95:145] = 0  # protected logo/source layer excluded from zone
    return shape, source, mask


@pytest.mark.parametrize('pattern', ['checker_warp', 'ammonite_chambers', 'acid_wash', 'argyle', '1191'])
@pytest.mark.parametrize('mode', ['overlay', 'blend'])
def test_full_half_zero_and_primary_stack_parity(composers, pattern, mode):
    primary, stacked = composers
    shape, source, mask = fixture()
    options=dict(base_strength=0, base_color_mode='original', pattern_paint_mode=mode)
    with contextlib.redirect_stdout(io.StringIO()):
        full=primary('metallic',pattern,source.copy(),shape,mask,42,1,0,**options)
        def stack(opacity=1, strength=1, extra=None):
            layers=[dict(id=pattern,opacity=opacity)] + (extra or [])
            return stacked('metallic',layers,source.copy(),shape,mask,42,1,0,spec_mult=strength,**options)
        np.testing.assert_allclose(stack(),full,atol=1e-6)
        np.testing.assert_allclose(stack(.5),(full+source)/2,atol=1e-6)
        np.testing.assert_allclose(stack(strength=.5),(full+source)/2,atol=1e-6)
        assert np.array_equal(stack(0),source)
        assert np.array_equal(stack(strength=0),source)
        assert np.array_equal(primary('metallic',pattern,source.copy(),shape,mask,42,1,0,spec_mult=0,**options),source)
        np.testing.assert_allclose(stack(extra=[dict(id='checker_warp',opacity=0)]),full,atol=1e-6)
    assert np.mean(np.abs(full[mask>0]-source[mask>0]))>.03
    assert np.array_equal(full[mask==0],source[mask==0])


@pytest.mark.parametrize('scale',[.25,.4,.7,1.,1.5])
def test_checker_overlay_independent_of_underpaint_at_full_strength(composers,scale):
    primary,_=composers
    shape,source,mask=fixture()
    other=1-source
    opts=dict(base_strength=0,base_color_mode='original',pattern_paint_mode='overlay',scale=scale,rotation=23,pattern_offset_x=.6)
    with contextlib.redirect_stdout(io.StringIO()):
        a=primary('metallic','checker_warp',source.copy(),shape,mask,42,1,0,**opts)
        b=primary('metallic','checker_warp',other.copy(),shape,mask,42,1,0,**opts)
    np.testing.assert_allclose(a[mask>0],b[mask>0],atol=1e-6)
    # Authored colored artwork can have lower luminance variance than the old
    # grayscale carrier; it must still be a substantial, fully opaque overlay.
    assert np.mean(np.abs(a[mask>0]-source[mask>0]))>.10
    assert np.array_equal(a[mask==0],source[mask==0])


def test_real_tga_export_default_mode_and_linear_controls(tmp_path):
    import uuid
    tmp_path = tmp_path / ('pattern-visibility-' + uuid.uuid4().hex)
    tmp_path.mkdir()
    from PIL import Image
    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2 as engine
    shape,source,mask=fixture()
    source_path=tmp_path/'synthetic.png'
    Image.fromarray(np.uint8(source*255)).save(source_path)
    outputs={}
    base=dict(name='Pattern visibility fixture',color='remaining',base='metallic',pattern='checker_warp',intensity='100',base_color_mode='original')
    for name,controls in [('none',dict(pattern='none')),('full',{}),('half',dict(pattern_opacity=.5)),('zero',dict(pattern_opacity=0)),('strength0',dict(pattern_spec_mult=0)),('blend',dict(pattern_paint_mode='blend'))]:
        target=tmp_path/name;target.mkdir()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            engine.build_multi_zone(str(source_path),str(target),[{**base,**controls}],iracing_id='PATTERN_TEST',seed=42,car_prefix='car_num')
        outputs[name]=np.array(Image.open(target/'car_num_PATTERN_TEST.tga')).astype(float)
    assert np.array_equal(outputs['zero'],outputs['none'])
    assert np.array_equal(outputs['strength0'],outputs['none'])
    np.testing.assert_allclose(outputs['half'],(outputs['full']+outputs['none'])/2,atol=1.1)
    assert np.abs(outputs['full']-outputs['none']).mean()>25
    assert np.abs(outputs['blend']-outputs['full']).mean()>10
