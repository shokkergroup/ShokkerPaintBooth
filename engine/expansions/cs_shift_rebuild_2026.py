# ============================================================================
# engine/expansions/cs_shift_rebuild_2026.py
# Total rebuild of COLOR SCIENCE cs_ (110 color-shift duos/concepts), 2026-06-22.
# Replaces the recycled install_csshift (_grad_struct 9-mode + _grad_spec). These
# are DUOCHROME color-SHIFT finishes: identity = the color PAIR + the angle flip.
# Reuses the existing (good) name->duochrome palette (_cs_palette) and ID list
# (CS_IDS) from color_science_rebuild_2026; swaps the structure to a curated set
# of 36 OPTICAL / FLOW exotic engines (spread across the 110 so structure varies)
# and gives each a true color-SHIFT spec (high metallic + pattern-carved clearcoat
# + low roughness = the duochrome flips with the environment, per the Ghost-Shift
# physics). Avoids owner-disliked engines. Install DEAD-LAST.
# 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations
from functools import lru_cache
import hashlib
import numpy as np
import cv2

from engine.paint_v2 import depth3d_2026 as _d3
from engine.paint_v2.fable_collection import _shape2, _seed_of, _work_shape, _mask2, _upscale, _pack_spec, _blend_paint
from engine.expansions.color_science_rebuild_2026 import _travel, CS_IDS, _cs_palette
from engine.expansions.prism_forge_rebuild_2026 import _getfield, _edge, _coverage, _n, _ensure_pop

# Curated OPTICAL / FLOW engines (smooth, omnidirectional, good for color travel).
# All confirmed present; none from the owner's disliked list.
CS_ENGINES = [
    # abstract OMNIDIRECTIONAL optical/flow only — no obvious-center rings/spirals
    # (those land oriented on the car, against the UV-agnostic rule), no blobby
    # reaction. Spread over the 110 finishes (~5x each, every one a different duo).
    "thinfilm_bands", "schlieren_refraction", "nacre", "opal_playofcolor", "peacock_optic",
    "dichroic_drift", "labradorite_schiller", "mokume_gane", "oil_seep", "curl_smoke",
    "curl_streaklines", "warp_moire", "lyapunov_marble", "widmanstatten", "diffraction_grating",
    "cd_dvd_rainbow", "anisotropic_turing", "potential_flow_cylinders", "glitch_mosh", "stress_fracture",
    "halftone_decay", "brushed_wear",
]


def _h(s, salt=0):
    return int(hashlib.md5(f"{s}|{salt}".encode()).hexdigest(), 16)


def _engine_for(fid):
    # spread evenly: index by a stable hash; offset by a second hash to de-cluster
    return CS_ENGINES[(_h(fid, 7) + (_h(fid, 13) % 5)) % len(CS_ENGINES)]


def _palette(fid):
    core = fid[3:] if fid.startswith("cs_") else fid
    return _ensure_pop([tuple(map(float, c)) for c in _cs_palette(core)])


def _make_cs(fid):
    pal = _palette(fid)
    engine = _engine_for(fid)
    base = tuple(np.clip(np.float32(pal[0]) * 0.7, 0, 1))
    A = np.float32(pal[1] if len(pal) > 1 else pal[0])
    B = np.float32(pal[2] if len(pal) > 2 else pal[-1])
    nmid = np.clip((A + B) * 0.5, 0, 1)   # named mid-tone for empty-area lift

    @lru_cache(maxsize=4)
    def _fields(h, w, seed):
        f = _getfield(engine, h, w, seed)
        rc = _coverage(f)
        fillw = float(np.clip((0.90 - rc) * 2.4, 0.0, 0.55))
        amb = _n(cv2.GaussianBlur(f, (0, 0), 30))
        ff = _n(f * (1.0 - fillw * 0.6) + amb * fillw)
        # strong A<->B duochrome travel (the shift IS the finish)
        col = _travel(ff, pal, irid=0.34, cycles=2.4, sat=0.92, smooth=0.55, base=base)
        edge = _edge(f)
        col = col * (0.62 + ff[..., None] * 0.5) + edge[..., None] * B[None, None, :] * 0.22
        col = col + ((1.0 - ff)[..., None] ** 2) * nmid[None, None, :] * 0.12   # named glow in dead areas
        col = np.clip((col - 0.5) * 1.13 + 0.5, 0, 1)
        col = np.clip(col * 1.09 + 0.04, 0, 1)
        paint = np.clip(col, 0, 1).astype(np.float32)
        g = _n(_d3._fbm(h, w, (seed ^ 0x37) & 0xFFFFFFFF, octaves=4, base=3)) if hasattr(_d3, "_fbm") else _n(edge)
        # COLOR-SHIFT physics: high metallic (reflects environment -> flips), pattern-
        # carved clearcoat (angle-dependent flip), low roughness (mirror/wet).
        M = np.clip(55 + np.clip(f, 0, 1) * 175 + edge * 22, 0, 255)
        R = np.clip(28 + g * 95 - f * 14, 15, 255)
        Cc = np.clip(26 + (1 - f) * 150 + edge * 48, 16, 255)
        M, R, Cc = _d3.decorrelate_envelope(M, R, Cc, seed=(seed * 5 + 29) & 0xFFFFFFFF, blend=0.6, relief=24.0)
        _msd = float(np.std(M))
        if 1e-3 < _msd < 25.0:                                   # target >20 with margin (clip can shave a hair)
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (25.0 / _msd), 0, 255)
        return paint, np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(Cc, 16, 255).astype(np.float32)

    def paint_fn(paint, shape, mask, seed, pm, bb, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        p, _M, _R, _C = _fields(h, w, _seed_of(_f, seed))
        return _blend_paint(paint, _upscale(p, fh, fw), _mask2(mask, fh, fw), pm)

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, _f=fid, **_kw):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(Cc, 16, 255)

    def mono_spec_fn(shape, mask, seed, sm, _f=fid):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

    return base_spec_fn, paint_fn, mono_spec_fn


def install_csshift_v2(mono_reg, base_reg=None):
    """Install the rebuilt cs_ color-shift finishes over the recycled version."""
    ids = set()
    for fid in CS_IDS:
        bsf, pfn, msf = _make_cs(fid)
        if base_reg is not None:
            be = base_reg.get(fid)
            if isinstance(be, dict) and "base_spec_fn" in be:
                be["base_spec_fn"] = bsf; be["paint_fn"] = pfn; ids.add(fid)
        if fid in mono_reg:
            mono_reg[fid] = (msf, pfn); ids.add(fid)
    return len(ids)
