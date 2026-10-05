# -*- coding: utf-8 -*-
"""Regression guards for the 2026-06-13 overnight run.

Pins the fixes + the three MEGA features so a future edit can't silently
re-break them. All additive; no existing behavior touched. Designed to be
fast + non-flaky (synthetic inputs where possible; no full-registry boot
except the one test that genuinely needs it).
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── FIX: spec_lfr_capitol_veins SIZE_FRAGILE (256-floor broadcast crash) ──────
@pytest.mark.parametrize("size", [64, 160, 256, 512])
def test_capitol_veins_renders_at_small_sizes(size):
    import engine.spec_patterns as sp
    out = sp.spec_lfr_capitol_veins((size, size), 12345, 1.0)
    assert out.shape == (size, size, 3), out.shape
    assert np.isfinite(out).all()


# ── FIX: fs_carnival_night was DEAD (confetti ~0.1% coverage) ─────────────────
def test_carnival_night_not_dead():
    import engine.expansions.fractured_souls_2026 as fs
    F = fs.SOULS["fs_carnival_night"]["fields"](512, 512, 12345)
    art, _k = fs.SOULS["fs_carnival_night"]["paint"](F, None)
    art = np.clip(np.asarray(art, np.float32), 0, 1)
    cov = float((art.max(2) > 0.18).mean())
    assert cov > 0.005, f"carnival confetti coverage {cov:.4f} too sparse (DEAD regression)"


# ── PERF FIX: micro_scatter must stay DETERMINISTIC + valid (guards the class
#    of bug where 'optimizing' it changes the random sequence / output) ────────
@pytest.mark.parametrize("kind", ["dot", "star5", "streak", "arc", "petal"])
def test_micro_scatter_deterministic_and_valid(kind):
    import engine.recipe_kit as rk
    a = rk.micro_scatter(256, 256, 777, 200, 9.0, kind=kind, amp=(0.4, 1.0))
    b = rk.micro_scatter(256, 256, 777, 200, 9.0, kind=kind, amp=(0.4, 1.0))
    assert a.shape == (256, 256)
    assert np.isfinite(a).all()
    assert np.array_equal(a, b), f"micro_scatter[{kind}] not deterministic for a fixed seed"
    assert float(a.max()) > 0.0, f"micro_scatter[{kind}] produced an empty field"


# ── MEGA 2: Shokker-ize emits the winner four-dial physics on any paint ───────
def test_shokkerize_winner_physics():
    from engine.shokkerize import shokkerize
    paint = np.random.RandomState(0).rand(256, 256, 3).astype(np.float32)
    spec = shokkerize(paint, intensity=1.0)
    assert spec.shape == (256, 256, 3)
    assert np.isfinite(spec).all()
    assert float(spec[:, :, 0].mean()) >= 240.0, "metal rail lost"
    assert float(spec[:, :, 2].mean()) >= 250.0, "clearcoat rail lost"


# ── The 3 experimental features stay WIRED (guards against accidental de-wiring) ─
# (Light Bench was scrapped 2026-06-13 per owner — iRacing users use the in-sim viewer.)
def test_experimental_features_wired_in_server_and_html():
    server = open(os.path.join(ROOT, "server.py"), encoding="utf-8").read()
    for reg in ("register_livery_designer_routes", "register_shokkerize_routes",
                "register_photo_livery_routes"):
        assert reg in server, f"{reg} missing from server.py (feature de-wired)"
    html = open(os.path.join(ROOT, "paint-booth-v2.html"), encoding="utf-8").read()
    for js in ("js/features/livery-designer.js", "js/features/shokkerize.js",
               "js/features/photo-livery.js"):
        assert js in html, f"{js} missing from paint-booth-v2.html (feature de-wired)"
    assert "light-bench.js" not in html, "light-bench.js should be scrapped"


# ── MEGA 1: Prompt-to-Livery returns a valid, renderable zone config ──────────
# (kept last; this one may boot the registry to resolve finish IDs.)
def test_livery_designer_returns_valid_zones():
    from engine.livery_designer import design_from_prompt
    r = design_from_prompt("aggressive red and black with a carbon hood", seed=51)
    zones = r.get("zones")
    assert zones and len(zones) >= 1, "no zones produced"
    assert any(z.get("finish") or z.get("base") for z in zones), "no zone carries a finish/base"
