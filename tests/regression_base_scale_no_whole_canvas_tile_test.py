# -*- coding: utf-8 -*-
"""Regression guard: scaling the BASE down (base_scale < 1) must tile ONLY the base-material
field, never the whole composited canvas (which already holds template decals / car number /
logos). The recurring "mini-cars" bug was engine/compose.py _apply_base_placement_to_paint
transforming the full `paint` buffer instead of the source-safe base-material delta.

If this test fails, someone re-widened base placement back into whole-composite tiling.
Tile the FIELD, not the CANVAS. See spb-pattern-scale-tiling memory + Linear SPB-41 family.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.compose import _apply_base_placement_to_paint


def _scene():
    """background = template with a unique 'decal' marker; paint = background + base material."""
    H = W = 128
    bg = np.full((H, W, 3), 0.5, dtype=np.float32)            # neutral template
    bg[12:40, 12:40, 0] = 1.0                                  # one bright magenta 'decal',
    bg[12:40, 12:40, 1] = 0.0                                  # off-centre, top-left quadrant only
    bg[12:40, 12:40, 2] = 1.0
    grad = np.linspace(0.0, 0.15, W, dtype=np.float32)[None, :, None]  # base-material delta
    paint = np.clip(bg + grad, 0.0, 1.0).astype(np.float32)
    mask = np.ones((H, W), dtype=np.float32)
    return paint, bg, mask, (H, W)


def _magenta_blobs(out):
    import cv2
    m = ((out[:, :, 0] > 0.7) & (out[:, :, 1] < 0.35) & (out[:, :, 2] > 0.7)).astype(np.uint8)
    n, _ = cv2.connectedComponents(m)
    return n - 1  # subtract the background label


def test_base_scale_down_does_not_replicate_decals():
    paint, bg, mask, shape = _scene()
    out = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=0.5, background_paint=bg))
    blobs = _magenta_blobs(out)
    assert blobs == 1, (
        f"base_scale<1 replicated the decal into {blobs} copies — whole-canvas tiling regression "
        f"(the engine tiled the composite instead of the base-material field)")


def test_base_scale_down_quadrants_not_identical():
    paint, bg, mask, shape = _scene()
    out = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=0.5, background_paint=bg))
    H, W = shape
    tl = out[:H // 2, :W // 2]
    tr = out[:H // 2, W // 2:]
    diff = float(np.mean(np.abs(tl - tr)))
    # Whole-composite tiling makes the quadrants near-identical (the bug measured ~0.01).
    # The single off-centre decal must keep them clearly different.
    assert diff > 0.05, (
        f"top-left vs top-right quadrants near-identical (mean abs diff {diff:.4f}); "
        f"base_scale tiled the whole composite into mini-cars")


def test_base_scale_down_still_tiles_the_material():
    # The base MATERIAL (here a horizontal gradient delta) must STILL shrink/tile when scaled
    # down — the fix must remove whole-canvas tiling WITHOUT disabling base scaling itself.
    paint, bg, mask, shape = _scene()
    out1 = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=1.0, background_paint=bg))
    out05 = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=0.5, background_paint=bg))
    H, W = shape
    region = (slice(H // 2, H), slice(0, W))  # bottom half — away from the top-left decal
    diff = float(np.mean(np.abs(out1[region] - out05[region])))
    assert diff > 0.01, (
        f"base material did not change between scale 1.0 and 0.5 (diff={diff:.4f}); "
        f"the fix disabled base scaling instead of just removing whole-canvas tiling")


def test_base_scale_one_is_noop():
    paint, bg, mask, shape = _scene()
    out = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=1.0, background_paint=bg))
    assert np.allclose(out[:, :, :3], paint[:, :, :3], atol=1e-6), "scale==1.0 must be a no-op"


def test_base_scale_down_no_background_still_does_not_tile_composite():
    """Defense-in-depth: even when a caller omits background_paint, base_scale<1 must NOT
    stamp a 2x2 grid of the whole composite. The legacy fallback used to transform the full
    rgb (the proven 'mini-cars' tiler). Without a true pre-material background there is no
    safe way to separate base material from decals, so the hardened fallback refuses to tile
    (returns the composite unchanged) rather than risk replicating the decals."""
    paint, _bg, mask, shape = _scene()
    out = np.asarray(_apply_base_placement_to_paint(
        paint, shape, mask, base_scale=0.5, background_paint=None))
    blobs = _magenta_blobs(out)
    assert blobs == 1, (
        f"base_scale<1 with no background_paint replicated the decal into {blobs} copies — "
        f"the legacy whole-composite tiler regressed in the fallback branch")
    H, W = shape
    diff = float(np.mean(np.abs(out[:H // 2, :W // 2] - out[:H // 2, W // 2:])))
    assert diff > 0.05, (
        f"no-background fallback tiled the whole composite (TL vs TR diff {diff:.4f})")
    # Safe behavior is a no-op when no background is available to isolate the base material.
    assert np.allclose(out[:, :, :3], paint[:, :, :3], atol=1e-6), (
        "no-background fallback must leave the composite unchanged (no tiling)")


def test_preview_render_real_composite_no_whole_car_tile():
    """INTEGRATION guard through the REAL engine.preview_render path (not just the unit).

    Renders a synthetic 'client composite' (car-number stand-in markers) through
    preview_render with the logged scenario (gloss + snake_skin scale=0.5, base_scale=0.5,
    cathedral-glass + f_metallic overlays). The off-centre markers must stay single-instance
    in their origin quadrant; a whole-car 2x2 tile would copy them into the other quadrants
    and collapse the top-left/top-right quadrant self-difference toward 0."""
    import shokker_engine_v2 as _E
    H = W = 256
    comp = np.full((H, W, 3), 40, dtype=np.uint8)
    comp[20:60, 20:80] = [255, 0, 255]    # magenta marker, TL only
    comp[180:230, 190:240] = [0, 255, 255]  # cyan marker, BR only
    import tempfile
    from PIL import Image
    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf.close()
    Image.fromarray(comp).save(tf.name)
    zones = [{
        "name": "Zone 1", "color": "#282828", "intensity": "100",
        "base": "gloss", "pattern": "snake_skin", "scale": 0.5, "base_scale": 0.5,
        "second_base": "mono:cathedral_glass",
        "second_base_color_source": "mono:cathedral_glass",
        "second_base_color": [0.2274, 0.5019, 0.6], "second_base_strength": 1.0,
        "second_base_blend_mode": "pattern-vivid", "second_base_pattern_scale": 0.5,
    }]
    try:
        _E.build_multi_zone._zone_cache.clear()
    except Exception:
        pass
    paint_rgb, _spec, _ms = _E.preview_render(tf.name, zones, seed=51, preview_scale=1.0)
    os.unlink(tf.name)
    out = paint_rgb.astype(np.float32) / 255.0
    # Magenta marker must remain only in the top-left quadrant.
    m = (out[:, :, 0] > 0.55) & (out[:, :, 1] < 0.45) & (out[:, :, 2] > 0.55)
    qy, qx = H // 2, W // 2
    tl, tr, bl, br = m[:qy, :qx].sum(), m[:qy, qx:].sum(), m[qy:, :qx].sum(), m[qy:, qx:].sum()
    assert tl > 0 and (tr + bl + br) < tl * 0.25, (
        f"magenta marker leaked out of its origin quadrant (TL={tl} TR={tr} BL={bl} BR={br}) — "
        f"whole-car tiling through preview_render")


if __name__ == "__main__":
    for fn in (test_base_scale_down_does_not_replicate_decals,
               test_base_scale_down_quadrants_not_identical,
               test_base_scale_down_still_tiles_the_material,
               test_base_scale_one_is_noop,
               test_base_scale_down_no_background_still_does_not_tile_composite,
               test_preview_render_real_composite_no_whole_car_tile):
        fn(); print("PASS", fn.__name__)


def _render_zone_on_marked_comp(zone_extra, H=256, W=256):
    """Shared harness: gray comp + corner markers; zone targets ONLY the gray.
    Returns (paint float01, spec float, marker_mask_fn). Asserts real coverage —
    the 2026-06-10 audit found color='everything' resolved to a 0%-pixel zone,
    so the old integration guard was passing while testing NOTHING."""
    import io as _io
    import contextlib
    import tempfile
    from PIL import Image
    import shokker_engine_v2 as _E
    comp = np.full((H, W, 3), 40, dtype=np.uint8)
    comp[20:60, 20:80] = [255, 0, 255]
    comp[H - 70:H - 30, W - 80:W - 30] = [0, 255, 255]
    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf.close()
    Image.fromarray(comp).save(tf.name)
    zone = {"name": "Z1", "color": {"color_rgb": [40, 40, 40], "tolerance": 30}, "intensity": "100"}
    zone.update(zone_extra)
    try:
        _E.build_multi_zone._zone_cache.clear()
    except Exception:
        pass
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        paint_rgb, spec, _ms = _E.preview_render(tf.name, [zone], seed=51, preview_scale=1.0)
    os.unlink(tf.name)
    cov_lines = [l for l in buf.getvalue().splitlines() if "of pixels" in l]
    cov = float(cov_lines[0].split("]:")[1].split("%")[0]) if cov_lines else 0.0
    assert cov > 30.0, f"test zone resolved to {cov}% pixels — harness no-op, fix the color desc"
    return paint_rgb.astype(np.float32) / 255.0, np.asarray(spec, np.float32), comp


def test_explicit_special_base_scale_no_whole_canvas_tile():
    """2026-06-10 owner report lock-in: From-special zone + base_scale<1 must
    scale ONLY the finish inside the zone. Markers (excluded from the zone by
    color) must survive byte-exact and never replicate anywhere."""
    out, _spec, comp = _render_zone_on_marked_comp({
        "base": "gloss",
        "base_color_mode": "special",
        "base_color_source": "mono:fable_ember_glass",
        "base_color_strength": 1.0,
        "base_scale": 0.5,
    })
    H, W = out.shape[:2]
    src = comp.astype(np.float32) / 255.0
    # markers untouched in place
    assert float(np.abs(out[26:54, 26:74] - src[26:54, 26:74]).max()) < 0.02, "magenta marker altered"
    assert float(np.abs(out[H - 64:H - 36, W - 74:W - 36] - src[H - 64:H - 36, W - 74:W - 36]).max()) < 0.02, "cyan marker altered"
    # no replicated marker-colored pixels outside their home boxes
    mg = (out[:, :, 0] > 0.75) & (out[:, :, 1] < 0.25) & (out[:, :, 2] > 0.75)
    mg[16:64, 16:84] = False
    cy = (out[:, :, 0] < 0.25) & (out[:, :, 1] > 0.75) & (out[:, :, 2] > 0.75)
    cy[H - 74:H - 26, W - 84:W - 26] = False
    assert int(mg.sum()) == 0 and int(cy.sum()) == 0, (
        f"marker ghosts replicated (magenta={int(mg.sum())} cyan={int(cy.sum())}) — whole-canvas tiling is back")


def test_spec_pattern_stack_scale_changes_output_live_path():
    """2026-06-10 owner report lock-in: the spec overlay Scale slider must
    actually change the spec map through the REAL preview_render path
    (0.5 = finer/tiled-down). Guards the zone→v6kw→compose forwarding."""
    base_zone = {"base": "gloss"}
    _p1, s1, _ = _render_zone_on_marked_comp(dict(base_zone, spec_pattern_stack=[
        {"pattern": "banded_rows", "opacity": 1.0, "channels": "MRC", "scale": 1.0}]))
    _p2, s2, _ = _render_zone_on_marked_comp(dict(base_zone, spec_pattern_stack=[
        {"pattern": "banded_rows", "opacity": 1.0, "channels": "MRC", "scale": 0.5}]))
    _p0, s0, _ = _render_zone_on_marked_comp(base_zone)
    assert float(np.abs(s1 - s0).mean()) > 0.5, "spec pattern stack did not apply through preview_render"
    assert float(np.abs(s1 - s2).mean()) > 0.5, "spec pattern scale had NO effect through preview_render"


def test_source_mode_art_base_scale_down_keeps_source_exact():
    """[2026-08-15 owner: "if the BASE SCALE is scaled down it's actually scaling down the
    entire canvas... on ALL BASE FINISHES"] Reproduced on glitch_rgb @0.1 in SOURCE color mode:
    a 10x10 grid of mini-cars, decals included.

    Root cause: the 2026-07-08 _source_paint_lock skips the base paint pass in source mode, but
    the base-placement block still ran. Its finer branch tiles `paint` assuming it holds the
    pure base pattern that skipped block would have produced — in source mode `paint` is the
    painter's SOURCE COMPOSITE, so it tiled the car itself. None of the tests above covered
    source mode with an ART base (they use explicit color modes or gloss), which is how this
    shipped for five weeks under a green guard.

    Contract: in source mode the base contributes SPEC ONLY, so the rendered paint must equal
    the source composite EXACTLY regardless of base_scale — and the spec must still scale."""
    import tempfile

    from PIL import Image

    import shokker_engine_v2 as _E

    H = W = 256
    comp = np.full((H, W, 3), 40, dtype=np.uint8)
    comp[20:60, 20:80] = [255, 0, 255]      # magenta marker, TL only
    comp[180:230, 190:240] = [0, 255, 255]  # cyan marker, BR only
    tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tf.close()
    Image.fromarray(comp).save(tf.name)

    def _run(base_scale):
        zones = [{
            "name": "Zone 1", "color": "everything", "intensity": "100",
            "base": "glitch_rgb", "pattern": "none",
            "base_color_mode": "source", "base_scale": base_scale, "spec_scale": base_scale,
        }]
        if hasattr(_E.build_multi_zone, "_zone_cache"):
            _E.build_multi_zone._zone_cache.clear()
        pr, sp, _ms = _E.preview_render(tf.name, zones, seed=51, preview_scale=1.0)
        return np.asarray(pr), np.asarray(sp)

    try:
        p_small, s_small = _run(0.1)
        p_one, s_one = _run(1.0)
    finally:
        os.unlink(tf.name)

    # 1. Paint == source composite, bit-for-bit, at BOTH scales (source mode = spec only).
    for tag, p in (("0.1", p_small), ("1.0", p_one)):
        diff = int(np.abs(p[:, :, :3].astype(np.int32) - comp.astype(np.int32)).max())
        assert diff <= 1, (
            f"source-mode paint deviates from the source composite at base_scale={tag} "
            f"(max channel diff {diff}) — the whole-canvas tile (or another paint writer) is back")
    # 2. The markers exist ONCE (no replication anywhere outside their home boxes).
    m = (p_small[:, :, 0] > 200) & (p_small[:, :, 1] < 60) & (p_small[:, :, 2] > 200)
    m[10:70, 10:90] = False
    assert int(m.sum()) == 0, f"{int(m.sum())} replicated magenta pixels — mini-car tiling is back"
    # 3. base_scale still does its real job: the SPEC changes with scale.
    assert not np.array_equal(s_small, s_one), (
        "spec identical at base_scale 0.1 vs 1.0 — the fix over-suppressed scaling")
