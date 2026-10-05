# -*- coding: utf-8 -*-
"""Regression guard: base_color_mode='source' (the "Use source paint" dropdown
choice) must keep the painter's source colors EXACTLY — the base contributes
SPEC ONLY.

Owner report 2026-07-08: "when you click USE SOURCE PAINT it's SUPPOSED to use
the SOURCE PAINT of the car as it is. If I'm in a Zone tied to an orange,
black, blue, and green color layer ALL of those colors should remain. At that
point what I'm changing is the SPEC BASE." Art-producing base paint_fns (e.g.
ghost_graphic) were overwriting the source with their own paint — a 4-hue
source rendered gray. If this test fails, someone re-enabled the base paint
pass in source mode (compose.py _source_paint_lock).
"""
import colorsys
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


QUADS = {
    'orange': (slice(20, 108), slice(20, 108)),
    'black': (slice(20, 108), slice(148, 236)),
    'blue': (slice(148, 236), slice(20, 108)),
    'green': (slice(148, 236), slice(148, 236)),
}


def _median_hue(img, q):
    px = img[q].reshape(-1, 3).astype(np.float32) / 255.0
    px = px[::37]
    hues = [colorsys.rgb_to_hsv(*p)[0] for p in px if colorsys.rgb_to_hsv(*p)[1] > 0.2]
    return float(np.median(hues)) if hues else None


def _mean_sat(img, q):
    px = img[q].reshape(-1, 3).astype(np.float32) / 255.0
    px = px[::37]
    return float(np.mean([colorsys.rgb_to_hsv(*p)[1] for p in px]))


def _render_source_mode(base_id):
    import tempfile
    import uuid

    import shokker_engine_v2 as eng

    # conftest redirects tempfile.tempdir into tests/_runtime_harness/temp_files
    # (its mkdtemp shim returns a non-created fixed path — use gettempdir directly).
    work = os.path.join(tempfile.gettempdir(), 'spb_srcmode_' + uuid.uuid4().hex[:8])
    os.makedirs(work, exist_ok=True)
    src = np.zeros((256, 256, 3), np.uint8)
    src[:128, :128] = (255, 120, 0)
    src[:128, 128:] = (25, 25, 25)
    src[128:, :128] = (30, 80, 255)
    src[128:, 128:] = (40, 200, 80)
    src_path = os.path.join(work, 'src.png')
    Image.fromarray(src).save(src_path)

    zones = [{
        "name": "Z1", "color": "everything", "colorMode": "special",
        "intensity": "100", "base": base_id, "base_color_mode": "source",
    }]
    out_dir = os.path.join(work, 'out_' + base_id)
    os.makedirs(out_dir, exist_ok=True)
    paint_rgb, _spec = eng.build_multi_zone(src_path, out_dir, zones, seed=51, preview_mode=True)
    arr = np.asarray(paint_rgb)
    if arr.dtype != np.uint8:
        arr = np.clip(arr * (255.0 if arr.max() <= 1.001 else 1.0), 0, 255).astype(np.uint8)
    return src, arr[:, :, :3]


def _assert_hues_preserved(src, out, base_id):
    for name, q in QUADS.items():
        if name == 'black':
            sat = _mean_sat(out, q)
            assert sat < 0.45, (
                f"[{base_id}] source-mode: black quadrant became colored (sat={sat:.2f})")
            continue
        sh = _median_hue(src, q)
        oh = _median_hue(out, q)
        assert oh is not None, (
            f"[{base_id}] source-mode: {name} quadrant lost ALL color — "
            f"the base paint pass overwrote the source paint")
        wrap = min(abs(oh - sh), 1 - abs(oh - sh))
        assert wrap < 0.09, (
            f"[{base_id}] source-mode: {name} hue drifted (src={sh:.3f} out={oh:.3f})")


def test_source_mode_keeps_colors_flat_base():
    src, out = _render_source_mode('gloss')
    _assert_hues_preserved(src, out, 'gloss')


def test_source_mode_keeps_colors_art_base():
    # ghost_graphic's paint_fn draws its own art — the historical color killer.
    src, out = _render_source_mode('ghost_graphic')
    _assert_hues_preserved(src, out, 'ghost_graphic')


# ── MONOLITHIC / SPECIAL path ─────────────────────────────────────────────────
# [SPB SOURCE-MODE PARITY 2026-08-15] The two tests above only prove the BASE path
# (compose.py _source_paint_lock). Both 'gloss' and 'ghost_graphic' resolve to
# compose_paint_mod, so they passed for 13 months while every one of the 846
# MONOLITHIC_REGISTRY finishes stayed broken — those are routed to the
# `[monolithic]` branch in shokker_engine_v2 by the `finish or base` resolve and
# never reach that lock. Owner re-reported it 2026-08-15: "it should use the SOURCE
# PAINT of the car. NOT the SOURCE PAINT of the BASE MATERIAL."
#
# Measured repro before the fix — fs_core_aurum (gold) over the 4-hue source:
#   blue 0.630 -> 0.106, green 0.375 -> 0.171, byte-identical to mode='special'.
MONO_PROBE = 'fs_core_aurum'


def _render_zone(zone_extra, tag):
    import tempfile
    import uuid

    import shokker_engine_v2 as eng

    work = os.path.join(tempfile.gettempdir(), 'spb_srcmono_' + uuid.uuid4().hex[:8])
    os.makedirs(work, exist_ok=True)
    src = np.zeros((256, 256, 3), np.uint8)
    src[:128, :128] = (255, 120, 0)
    src[:128, 128:] = (25, 25, 25)
    src[128:, :128] = (30, 80, 255)
    src[128:, 128:] = (40, 200, 80)
    src_path = os.path.join(work, 'src.png')
    Image.fromarray(src).save(src_path)

    zone = {"name": "Z1", "color": "everything", "colorMode": "special", "intensity": "100"}
    zone.update(zone_extra)
    out_dir = os.path.join(work, 'out_' + tag)
    os.makedirs(out_dir, exist_ok=True)
    paint_rgb, spec = eng.build_multi_zone(src_path, out_dir, [zone], seed=51, preview_mode=True)

    def _u8(a):
        a = np.asarray(a)
        if a.dtype != np.uint8:
            a = np.clip(a * (255.0 if a.max() <= 1.001 else 1.0), 0, 255).astype(np.uint8)
        return a

    return src, _u8(paint_rgb)[:, :, :3], _u8(spec)


# [SPB MONO-COLOUR DEFAULT 2026-08-30] The contract gained a second half. Source
# mode still means SPEC ONLY — but only when the user CHOSE it. Every zone saved
# before this date carries 'source' as an inherited default it never asked for,
# and the owner reported the consequence directly: "there's a LOT of finishes ...
# the COLOR is not showing up for the BASE MATERIAL at all". So the client now
# stamps base_color_explicit when the dropdown is actually used, and both halves
# are guarded below.
def test_source_mode_keeps_colors_monolithic_finish():
    """A monolithic carried as zone['finish'] must contribute SPEC ONLY when the
    user has explicitly chosen source mode."""
    src, out, _spec = _render_zone(
        {"finish": MONO_PROBE, "base_color_mode": "source",
         "base_color_explicit": True}, 'mono_src')
    _assert_hues_preserved(src, out, MONO_PROBE + ' (finish/source)')


def test_source_mode_keeps_colors_monolithic_via_base_key():
    """Same finish sent as zone['base'] — the engine resolves it to the monolithic path too."""
    src, out, _spec = _render_zone(
        {"base": MONO_PROBE, "base_color_mode": "source",
         "base_color_explicit": True}, 'mono_basekey')
    _assert_hues_preserved(src, out, MONO_PROBE + ' (base-key/source)')


def test_unchosen_source_mode_keeps_the_finish_colour():
    """THE OTHER HALF: a zone that merely inherited 'source' (no explicit flag)
    must render the MATERIAL'S OWN colour, not the car's paint. This is the
    regression the owner hit on 2026-08-30 across the whole monolithic catalog."""
    src, out, _spec = _render_zone(
        {"finish": MONO_PROBE, "base_color_mode": "source"}, 'mono_unchosen')
    # the finish is gold; the source quadrants are orange / near-black / blue /
    # green. If the material's colour survived, the output cannot still be the
    # four source hues.
    import numpy as _np
    diff = float(_np.abs(out.astype(_np.float32) - src.astype(_np.float32)).mean())
    assert diff > 12.0, (
        "unchosen source mode discarded the monolithic's paint (mean diff %.2f) — "
        "the finish rendered spec-only" % diff)


def test_source_mode_preserves_the_finish_spec_exactly():
    """The other half of the contract: keeping the paint must NOT weaken the spec.

    Source mode and special mode must emit a byte-identical spec — only the PAINT differs.
    If this fails, someone "fixed" source mode by suppressing the finish instead of just
    its paint pass, and the user loses the spec they picked the finish for.
    """
    _s1, _p1, spec_source = _render_zone(
        {"finish": MONO_PROBE, "base_color_mode": "source"}, 'spec_src')
    _s2, _p2, spec_special = _render_zone(
        {"finish": MONO_PROBE, "base_color_mode": "special",
         "base_color_source": "mono:" + MONO_PROBE}, 'spec_spec')
    assert spec_source.shape == spec_special.shape, "spec shape changed between color modes"
    diff = int(np.abs(spec_source.astype(int) - spec_special.astype(int)).max())
    assert diff == 0, (
        f"[{MONO_PROBE}] source mode altered the SPEC (max channel diff {diff}); "
        f"source mode must change PAINT only")


def test_source_mode_does_not_disable_explicit_color_modes():
    """Guard the opposite regression: explicit modes must still override the finish's paint.

    The source-mode branch is mutually exclusive with the explicit-override branch; if someone
    merges them, 'Use solid color' silently stops working on monolithics (the 2026-06-02 bug).
    """
    src, out, _spec = _render_zone(
        {"finish": MONO_PROBE, "base_color_mode": "solid", "base_color": [1.0, 0.0, 0.0]},
        'solid_red')
    # Solid red must WIN over the source blue/green quadrants.
    for name in ('blue', 'green'):
        q = QUADS[name]
        sh, oh = _median_hue(src, q), _median_hue(out, q)
        assert oh is not None, f"solid-color override wiped all saturation in {name}"
        wrap = min(abs(oh - sh), 1 - abs(oh - sh))
        assert wrap > 0.09, (
            f"[{MONO_PROBE}] 'Use solid color' no longer overrides the {name} quadrant "
            f"(src={sh:.3f} out={oh:.3f}) — the explicit-override path regressed")


# ── BASE STRENGTH is the paint blend; INTENSITY must not delete the colour ────
# [SPB MONO-PAINT-STRENGTH 2026-08-30] Owner, third report of the same symptom:
# "I pick a base material and have the color from the base material, then I dial
# the BASE STRENGTH slider from 100 down to 20-50% to blend it with the SOURCE
# PAINT ... right now its still NOT WORKING."
#
# Cause: the zone INTENSITY preset produced `pm`, which scaled the monolithic's
# paint at RENDER time. Captured from the owner's own session, a zone sat at
# intensity '10', so every material picked into it rendered 10% paint / 100%
# spec — colourless — regardless of Base Strength. Both monolithic blocks now
# render the complete colour and let Base Strength do the single mix.
def test_low_intensity_does_not_delete_monolithic_colour():
    """A zone left at intensity 10 must STILL show the material's colour."""
    src, out, _spec = _render_zone(
        {"finish": MONO_PROBE, "intensity": "10",
         "base_color_mode": "special", "base_color_source": "mono:" + MONO_PROBE},
        'mono_lowint')
    import numpy as _np
    diff = float(_np.abs(out.astype(_np.float32) - src.astype(_np.float32)).mean())
    assert diff > 12.0, (
        "zone intensity crushed the monolithic's paint (mean diff %.2f) — the "
        "material rendered spec-only" % diff)


def test_base_strength_is_the_paint_blend():
    """100 = the material's full colour; dialling down blends toward the source
    paint. This is the owner's stated workflow and must stay monotonic."""
    import numpy as _np
    diffs = []
    for bs in (1.0, 0.5, 0.2):
        src, out, _spec = _render_zone(
            {"finish": MONO_PROBE, "base_strength": bs,
             "base_color_mode": "special", "base_color_source": "mono:" + MONO_PROBE},
            'mono_bs_%s' % bs)
        diffs.append(float(_np.abs(out.astype(_np.float32) - src.astype(_np.float32)).mean()))
    assert diffs[0] > diffs[1] > diffs[2], (
        "base_strength is not blending monotonically toward the source paint: %s" % diffs)
    assert diffs[0] > 12.0, "base_strength 1.0 did not show the material's colour"
