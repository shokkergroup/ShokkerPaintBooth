"""Base modes must survive the actual preview endpoint, including explicit false/true."""
import base64, contextlib, io
import numpy as np
import pytest
from PIL import Image

@pytest.mark.parametrize("marker", [None, False, True])
@pytest.mark.parametrize("target", [{"base":"chrome"},{"base":"fs_core_crimson"},{"finish":"fs_core_crimson"}])
@pytest.mark.parametrize("mode", ["source","finish","solid","special","gradient"])
def test_preview_preserves_selected_base_color_mode(monkeypatch,target,mode,marker):
    with contextlib.redirect_stdout(io.StringIO()):
        import server
    monkeypatch.setattr(server,"_rate_limit",lambda *a,**kw:True)
    seen=[]
    def preview(_path,zones,**kwargs):
        seen.extend(zones)
        return np.full((32,32,3),100,np.uint8),np.full((32,32,4),100,np.uint8),1.
    monkeypatch.setattr(server.engine,"preview_render",preview)
    monkeypatch.setattr(server,"_record_recent_render",lambda *a,**kw:None)
    b=io.BytesIO();Image.new("RGB",(32,32),(25,100,210)).save(b,format="PNG")
    zone=dict(name="Base mode transport",color="remaining",pattern="none",base_color_mode=mode,
              pattern_spec_opacity=0,**target)
    if marker is not None:
        zone["base_color_explicit"] = marker
    r=server.app.test_client().post("/preview-render",json=dict(source_mode="live_flat_canvas",
        paint_image_base64=base64.b64encode(b.getvalue()).decode(),seed=42,zones=[zone],settings={}))
    assert r.status_code==200,r.get_json()
    assert len(seen)==1
    assert seen[0]["base_color_mode"]==mode
    assert seen[0]["base_color_explicit"] is True
    assert seen[0]["pattern_spec_opacity"]==0


def test_saved_camel_case_and_unset_mode_boundary():
    with contextlib.redirect_stdout(io.StringIO()):
        import server
    assert server._convert_zone_keys({"baseColorMode":"source"}) == {"base_color_mode":"source","base_color_explicit":True}
    assert server._convert_zone_keys({"base":"gloss"}) == {"base":"gloss"}


@pytest.mark.parametrize("finish", [
    "ffl_flashpoint", "pdg_burlap_glaze", "fab_vellum_leaf", "rs_rising_sun_flare",
    "prizm_adaptive", "pp_holographic_oil_circuit", "grd_oklab_flow", "aurora_glow",
    "grad_arctic_dawn", "grad_black_gold",
])
def test_collection_modes_in_real_tga_exports(tmp_path, finish):
    """One per collection section, through app normalization and real TGA writes."""
    with contextlib.redirect_stdout(io.StringIO()):
        import server
        import shokker_engine_v2 as engine
        engine._ensure_expansions_loaded()
    source = np.empty((96, 96, 3), np.uint8)
    source[:48, :48] = (230, 80, 15)
    source[:48, 48:] = (20, 20, 20)
    source[48:, :48] = (25, 100, 210)
    source[48:, 48:] = (40, 200, 80)
    src = tmp_path / (finish + '.png')
    Image.fromarray(source).save(src)
    results = {}
    for mode in ['source', 'finish']:
        output = tmp_path / finish / mode
        output.mkdir(parents=True, exist_ok=True)
        zone = server._convert_zone_keys(dict(
            name='Base color contract', color='remaining', base=finish, pattern='none',
            intensity='100', baseColorMode=mode, patternSpecOpacity=0))
        with contextlib.redirect_stdout(io.StringIO()):
            engine.build_multi_zone(str(src), str(output), [zone], seed=42,
                                    iracing_id='BASE_MODE_TEST', car_prefix='car_num')
        results[mode] = (
            np.array(Image.open(output / 'car_num_BASE_MODE_TEST.tga')),
            np.array(Image.open(output / 'car_spec_BASE_MODE_TEST.tga')))
    np.testing.assert_array_equal(results['source'][0][:, :, :3], source)
    np.testing.assert_allclose(results['source'][1].astype(float),
                               results['finish'][1].astype(float), atol=1)


def test_mutating_material_cannot_destroy_source_snapshot():
    import shokker_engine_v2 as engine
    original = np.full((8, 8, 3), (.1, .4, .8), np.float32)
    before = original.copy()
    material_input = engine._monolithic_underpaint_from_zone(
        original, {}, (8, 8), np.ones((8, 8), np.float32), 42)
    material_input[:] = (1., .1, .8)
    np.testing.assert_array_equal(original, before)
