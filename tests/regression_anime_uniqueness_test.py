"""MECHANICAL GATE for the ★ ANIME INSPIRED 25-design overhaul (owner mandate 2026-08-25).

Fail-closed, mirroring tests/regression_flame_uniqueness_test.py (the reference gate) with the
anime-specific additions:
  1. UNIQUENESS    — every pair of the 25 anime structures < 80% similarity, measured with the
                     CANONICAL catalog fingerprint math (scripts/spb_catalog_fingerprint), the
                     same math scripts/spb_uniqueness_gate.py uses.
  2. RENDER-TIME   — each structure (paint+spec, one shared build) < 3s at 2048², load-normalized
                     best-of-2 like the flame test.
  3. COVERAGE      — >= MIN_COVERAGE at the NATIVE 2048 doctrine canvas (several anime designs
                     are halftone/glyph fields whose dots undersample at 512 — the flame test's
                     512 shortcut would misjudge them). Opt-outs only via anime_math.COVERAGE_EXEMPT.
  4. FINE DETAIL   — >= MIN_FINENESS at 2048, opt-outs only via anime_math.FINE_DETAIL_EXEMPT.
  5. SPEC RICHNESS — married-spec channel stds (M/R/CC) each >= 18 (owner Rule 2: many shades,
                     not two levels).
  6. WIRING        — 25 structures; every catalog fid maps to a real structure; the JS specials
                     group lists all 15 anime2 ids.

Run:  py -3 -m pytest tests/regression_anime_uniqueness_test.py -q
Ledger: docs/ANIME_OVERHAUL_2026-08-25.md
"""
import itertools
import os
import re
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import engine.paint_v2.anime_math as am
from engine.paint_v2.flame_math import coverage_score, fineness_score, MIN_COVERAGE, MIN_FINENESS
from spb_catalog_fingerprint import fingerprint, _sim_matrix

S = 2048
SIM_FAIL = 0.80
_METRICS = None


def _metrics():
    """Render every structure ONCE at the native 2048 doctrine canvas (paint+spec share one
    build), streaming — arrays are dropped after their scalars/fingerprints are extracted."""
    global _METRICS
    if _METRICS is not None:
        return _METRICS
    rows = {}
    for key in am.ANIME_STRUCTURES:
        am.build.cache_clear()
        t0 = time.time()
        built = am.build(key, (S, S), 7)
        dt1 = time.time() - t0
        rgb = np.asarray(built["rgb"])
        spec = np.asarray(built["spec"])
        assert rgb.shape == (S, S, 3), f"{key} bad rgb shape {rgb.shape}"
        assert spec.shape == (S, S, 3), f"{key} bad spec shape {spec.shape}"
        pf, ph, trace, energy = fingerprint(rgb, np.clip(spec, 0, 255).astype(np.uint8))
        rows[key] = dict(
            t=dt1,
            cov=coverage_score(rgb),
            fin=fineness_score(rgb),
            stds=tuple(float(spec[:, :, i].std()) for i in range(3)),
            pf=pf, ph=ph,
        )
        del built, rgb, spec
    # second timing trial (interleaved) for load-normalized best-of-2
    for key in am.ANIME_STRUCTURES:
        am.build.cache_clear()
        t0 = time.time()
        am.build(key, (S, S), 7)
        rows[key]["t"] = min(rows[key]["t"], time.time() - t0)
    am.build.cache_clear()
    _METRICS = rows
    return rows


def test_anime_structures_are_distinct():
    m = _metrics()
    keys = sorted(m)
    sim = _sim_matrix(np.stack([m[k]["pf"] for k in keys]), np.stack([m[k]["ph"] for k in keys]))
    too_similar = []
    for i, j in itertools.combinations(range(len(keys)), 2):
        if sim[i, j] >= SIM_FAIL:
            too_similar.append((keys[i], keys[j], round(float(sim[i, j]), 3)))
    assert not too_similar, (
        f"anime structures exceed the {SIM_FAIL:.0%} uniqueness gate "
        f"(redesign the MATH, not the palette): {too_similar}")


def test_anime_structures_render_under_3s():
    m = _metrics()
    fastest = min(r["t"] for r in m.values())
    budget = max(3.0, 8.0 * fastest)     # absolute 3s when idle; load-scaled when busy
    slow = [(k, round(r["t"], 2)) for k, r in m.items() if r["t"] > budget]
    assert not slow, (
        f"anime structures over the render-time doctrine at 2048 (paint+spec, best of 2, "
        f"budget {budget:.1f}s): {slow}")


def test_anime_structures_cover_the_canvas():
    m = _metrics()
    weak = [(k, round(r["cov"], 2)) for k, r in m.items()
            if k not in am.COVERAGE_EXEMPT and r["cov"] < MIN_COVERAGE]
    assert not weak, (
        f"anime structures below the {MIN_COVERAGE} coverage mandate at 2048 (fill the canvas — "
        f"or add to COVERAGE_EXEMPT with a reason): {weak}")


def test_anime_structures_are_crushed_fine():
    m = _metrics()
    smooth = [(k, round(r["fin"], 2)) for k, r in m.items()
              if k not in am.FINE_DETAIL_EXEMPT and r["fin"] < MIN_FINENESS]
    assert not smooth, (
        f"anime structures below the {MIN_FINENESS} fine-detail mandate at 2048 (crush in fine "
        f"structure — or add to FINE_DETAIL_EXEMPT with a reason): {smooth}")


def test_anime_specs_use_many_shades():
    m = _metrics()
    flat = [(k, tuple(round(v, 1) for v in r["stds"])) for k, r in m.items() if min(r["stds"]) < 18]
    assert not flat, (
        f"anime married specs too flat (owner Rule 2 — wide M/R/CC shade ranges, std >= 18): {flat}")


def test_anime_wiring_is_complete():
    from engine.expansions.anime_catalog_2026 import ANIME_FINISHES
    assert len(am.ANIME_STRUCTURES) == 25, f"expected 25 structures, got {len(am.ANIME_STRUCTURES)}"
    assert len(ANIME_FINISHES) == 15, f"expected 15 catalog fids, got {len(ANIME_FINISHES)}"
    for fid, row in ANIME_FINISHES.items():
        assert row[0] in am.ANIME_STRUCTURES, f"{fid} maps to unknown structure {row[0]}"
    import engine.paint_v2.anime_style as ast_
    for fn in ("paint_anime_cel_shade_chrome", "spec_anime_crystal_facet",
               "paint_anime_sakura_scatter", "spec_anime_neon_outline"):
        assert callable(getattr(ast_, fn)), f"anime_style missing {fn}"
    js = open(os.path.join(ROOT, "paint-booth-0-finish-data.js"), encoding="utf-8").read()
    mspec = re.search(r'"★ ANIME INSPIRED": \[([^\]]*)\]', js)
    assert mspec, "JS specials group missing"
    ids = re.findall(r'"(anime2_[a-z_]+)"', mspec.group(1))
    assert sorted(ids) == sorted(ANIME_FINISHES.keys()), (
        f"JS specials list != catalog fids: js={sorted(ids)} vs catalog={sorted(ANIME_FINISHES)}")
    for fid in ANIME_FINISHES:
        assert js.count(f'id: "{fid}"') == 1, f"JS display entry missing/dup for {fid}"
