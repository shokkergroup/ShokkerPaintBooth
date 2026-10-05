# ============================================================================
# engine/expansions/shokk_series_rebuild_2026.py
# OWNER-APPROVED rebuild of SHOKK SERIES (25 shokk_*), 2026-06-21.
# Each finish = a DISTINCT engine, energy/sci-fi, NAME-TRUE palette, 3-pass
# reviewed. KEEPS shokk_tesseract_v2/shokk_cipher/shokk_helix/shokk_venom/
# burnt_headers (NOT in this map). shokk_ live in BASE_REGISTRY and are re-wired
# by wild_spec_lab on first render, so this installs in the COLOR-SCIENCE
# FINAL-AUTHORITY hook (runs AFTER wild_spec). Ported from the gated proof
# (_reworks_2026/shokk_series_proof.py). 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations
from functools import lru_cache
import numpy as np
import cv2

from engine.paint_v2 import depth3d_2026 as _d3
from engine.paint_v2.fable_collection import _shape2, _seed_of, _work_shape, _mask2, _upscale, _pack_spec, _blend_paint
from engine.expansions.color_science_rebuild_2026 import _travel, RAINBOW
from engine.expansions.prism_forge_rebuild_2026 import _getfield, _edge, _coverage, _n

SHOKK_MAP = [
    ("electric_ice", "iceshard", 0), ("mercury", "oil_serpent", 0), ("plasma_metal", "ion_bloom", 0),
    ("shokk_blood", "maelstrom", 0), ("shokk_pulse", "aura_rings", 0), ("shokk_static", "static_crackle", 0),
    ("shokk_void", "soliton_reef", 0), ("volcanic", "vent_plume", 0), ("shokk_flux", "guilloche_drift", 0),
    ("shokk_phase", "moire_vortex", 0), ("shokk_dual", "oilfilm_weave", 0), ("shokk_spectrum", "spectra_wheel", 0),
    ("shokk_aurora", "aurora_veil", 0), ("shokk_catalyst", "resonant_cells", 0), ("shokk_mirage", "schlieren_refraction", 0),
    ("shokk_polarity", "standing_field", 0), ("shokk_reactor", "reactor_lattice", 1), ("shokk_prism", "prism_facet", 1),
    ("shokk_wraith", "sonar_glass", 0), ("shokk_fusion_base", "plasma_arc", 0), ("shokk_rift", "shardfield", 1),
    ("shokk_vortex", "spiral_prism", 0), ("shokk_surge", "rbw_spectral_curl", 0), ("shokk_inferno", "flame_helix", 0),
    ("shokk_apex", "cubist_prism", 1),
]
SHOKK_CONCEPTS = {
    "electric_ice": [(0.04, 0.10, 0.20), (0.20, 0.70, 0.95), (0.72, 0.93, 1.0), (0.55, 0.88, 0.95)],
    "mercury": [(0.10, 0.11, 0.13), (0.45, 0.47, 0.52), (0.75, 0.78, 0.84), (0.93, 0.95, 0.99)],
    "plasma_metal": [(0.05, 0.02, 0.12), (0.92, 0.10, 0.70), (0.10, 0.72, 0.95), (0.60, 0.20, 0.92)],
    "shokk_blood": [(0.06, 0.0, 0.0), (0.46, 0.02, 0.04), (0.82, 0.08, 0.10), (0.97, 0.32, 0.20)],
    "shokk_pulse": [(0.03, 0.04, 0.12), (0.10, 0.50, 0.92), (0.88, 0.15, 0.55), (0.97, 0.82, 0.20)],
    "shokk_static": [(0.05, 0.05, 0.07), (0.40, 0.42, 0.46), (0.76, 0.79, 0.84), (0.93, 0.94, 0.97)],
    "shokk_void": [(0.01, 0.01, 0.04), (0.10, 0.06, 0.32), (0.32, 0.16, 0.62), (0.20, 0.42, 0.88)],
    "volcanic": [(0.04, 0.02, 0.01), (0.52, 0.06, 0.02), (0.92, 0.30, 0.04), (1.0, 0.72, 0.15)],
    "shokk_flux": [(0.04, 0.06, 0.12), (0.10, 0.62, 0.60), (0.52, 0.20, 0.78), (0.92, 0.62, 0.20)],
    "shokk_phase": [(0.05, 0.05, 0.16), (0.20, 0.32, 0.78), (0.62, 0.20, 0.62), (0.20, 0.78, 0.74)],
    "shokk_dual": [(0.05, 0.05, 0.08), (0.88, 0.16, 0.10), (0.10, 0.42, 0.92), (0.92, 0.86, 0.42)],
    "shokk_spectrum": list(RAINBOW),
    "shokk_aurora": [(0.02, 0.06, 0.10), (0.05, 0.62, 0.36), (0.10, 0.46, 0.76), (0.46, 0.16, 0.66)],
    "shokk_catalyst": [(0.03, 0.08, 0.03), (0.32, 0.72, 0.10), (0.72, 0.96, 0.20), (0.20, 0.62, 0.82)],
    "shokk_mirage": [(0.08, 0.06, 0.05), (0.62, 0.46, 0.20), (0.30, 0.62, 0.66), (0.92, 0.82, 0.52)],
    "shokk_polarity": [(0.03, 0.04, 0.10), (0.10, 0.30, 0.92), (0.92, 0.26, 0.10), (0.93, 0.93, 0.96)],
    "shokk_reactor": [(0.02, 0.07, 0.04), (0.10, 0.72, 0.40), (0.72, 0.96, 0.20), (0.92, 1.0, 0.62)],
    "shokk_prism": list(RAINBOW),
    "shokk_wraith": [(0.04, 0.05, 0.07), (0.25, 0.40, 0.46), (0.52, 0.66, 0.70), (0.72, 0.62, 0.86)],
    "shokk_fusion_base": [(0.04, 0.03, 0.10), (0.72, 0.20, 0.52), (0.20, 0.56, 0.92), (0.96, 0.96, 0.92)],
    "shokk_rift": [(0.02, 0.02, 0.07), (0.32, 0.06, 0.46), (0.62, 0.12, 0.72), (0.20, 0.46, 0.93)],
    "shokk_vortex": [(0.03, 0.04, 0.12), (0.10, 0.46, 0.76), (0.52, 0.20, 0.72), (0.86, 0.52, 0.20)],
    "shokk_surge": [(0.02, 0.07, 0.13), (0.10, 0.62, 0.92), (0.52, 0.92, 0.96), (0.96, 0.96, 0.52)],
    "shokk_inferno": [(0.04, 0.01, 0.01), (0.62, 0.06, 0.02), (0.96, 0.30, 0.04), (1.0, 0.82, 0.20)],
    "shokk_apex": [(0.05, 0.04, 0.10), (0.52, 0.10, 0.62), (0.10, 0.62, 0.86), (0.96, 0.86, 0.30)],
}


def _make_shokk(sid, engine, depth):
    pal = [tuple(map(float, c)) for c in SHOKK_CONCEPTS.get(sid, RAINBOW)]
    base = tuple(np.clip(np.float32(pal[0]) * 0.6, 0, 1)); hi = np.float32(pal[-1])
    prismatic = any(k in sid for k in ('spectrum', 'prism', 'phase', 'flux', 'mirage', 'aurora'))
    relief = 34.0 if depth else 22.0

    @lru_cache(maxsize=4)
    def _fields(h, w, seed):
        f = _getfield(engine, h, w, seed)
        rc = _coverage(f); fillw = float(np.clip((0.90 - rc) * 2.2, 0.0, 0.5))
        amb = _n(cv2.GaussianBlur(f, (0, 0), 30)); ff = _n(f * (1.0 - fillw * 0.6) + amb * fillw)
        col = _travel(ff, pal, irid=(0.28 if prismatic else 0.12), cycles=(2.7 if prismatic else 2.2), sat=0.9, smooth=0.5, base=base)
        edge = _edge(f)
        col = col * (0.60 + ff[..., None] * 0.5) + edge[..., None] * hi[None, None, :] * 0.32
        col = np.clip((col - 0.5) * 1.14 + 0.5, 0, 1)
        paint = np.clip(col, 0, 1).astype(np.float32)
        g = _n(_d3._fbm(h, w, (seed ^ 0x2B) & 0xFFFFFFFF, octaves=4, base=3)) if hasattr(_d3, "_fbm") else edge
        M = np.clip(16 + np.clip(f * 1.5, 0, 1) * 205 + edge * 40, 0, 255)
        R = np.clip(58 + g * 150 - f * 25, 15, 255)
        Cc = np.clip(20 + (1 - f) * 120 + edge * 40, 16, 255)
        M, R, Cc = _d3.decorrelate_envelope(M, R, Cc, seed=(seed * 3 + 17) & 0xFFFFFFFF, blend=0.62, relief=relief)
        _msd = float(np.std(M))
        if 1e-3 < _msd < 20.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (20.0 / _msd), 0, 255)
        return paint, np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(Cc, 16, 255).astype(np.float32)

    def paint_fn(paint, shape, mask, seed, pm, bb, _f=sid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        p, _M, _R, _C = _fields(h, w, _seed_of(_f, seed))
        return _blend_paint(paint, _upscale(p, fh, fw), _mask2(mask, fh, fw), pm)

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, _f=sid, **_kw):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(Cc, 16, 255)

    def mono_spec_fn(shape, mask, seed, sm, _f=sid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

    return base_spec_fn, paint_fn, mono_spec_fn


def install_shokk_series(mono_reg, base_reg=None):
    ids = set()
    for sid, engine, depth in SHOKK_MAP:
        bsf, pfn, msf = _make_shokk(sid, engine, depth)
        if base_reg is not None:
            be = base_reg.get(sid)
            if isinstance(be, dict) and "base_spec_fn" in be:
                be["base_spec_fn"] = bsf; be["paint_fn"] = pfn; ids.add(sid)
        if sid in mono_reg:
            mono_reg[sid] = (msf, pfn); ids.add(sid)
    return len(ids)
