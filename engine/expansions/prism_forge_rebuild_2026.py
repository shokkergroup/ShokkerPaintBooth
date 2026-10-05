# ============================================================================
# engine/expansions/prism_forge_rebuild_2026.py
# OWNER-APPROVED rebuild of PRISM FORGE (50 pf_*), 2026-06-21.
# Each finish = a DISTINCT engine (from exotic_engines_2026 + the iridescent
# old fractured_math library), NAME-TRUE palette, prismatic edge sheen + 3D
# relief spec. Replaces the recycled lazy install_prismforge. Owner taste:
# fine iridescent FLOW + color diversity; name colors dominate, prism is accent.
# pf_ live in BASE_REGISTRY. Install DEAD-LAST (final authority).
# Ported from the gated 3-pass proof (_reworks_2026/prism_forge_proof.py).
# 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations
from functools import lru_cache
import numpy as np
import cv2

from engine.paint_v2 import exotic_engines_2026 as _ex
from engine.paint_v2 import fractured_math as _fmold
from engine.paint_v2 import depth3d_2026 as _d3
from engine.paint_v2.fable_collection import _shape2, _seed_of, _work_shape, _mask2, _upscale, _pack_spec, _blend_paint
from engine.expansions.color_science_rebuild_2026 import _travel, RAINBOW

COLORS = {
    'molten': (0.92, 0.32, 0.04), 'aurora': (0.10, 0.80, 0.45), 'void': (0.02, 0.02, 0.05), 'pearl': (0.90, 0.90, 0.95),
    'ion': (0.15, 0.75, 0.95), 'sapphire': (0.10, 0.28, 0.85), 'blood': (0.62, 0.03, 0.06), 'emerald': (0.05, 0.72, 0.38),
    'inferno': (0.95, 0.30, 0.04), 'violet': (0.52, 0.15, 0.85), 'sunrise': (0.98, 0.55, 0.30), 'copper': (0.80, 0.42, 0.18),
    'moon': (0.78, 0.80, 0.88), 'toxic': (0.55, 0.90, 0.08), 'glacial': (0.55, 0.82, 0.95), 'burn': (0.95, 0.35, 0.05),
    'oil': (0.12, 0.16, 0.20), 'nebula': (0.35, 0.15, 0.65), 'rose': (0.95, 0.40, 0.55), 'quantum': (0.20, 0.45, 0.95),
    'cobalt': (0.08, 0.25, 0.85), 'fire': (0.95, 0.28, 0.05), 'midnight': (0.04, 0.06, 0.20), 'crystal': (0.75, 0.88, 0.96),
    'tar': (0.03, 0.03, 0.04), 'eclipse': (0.05, 0.05, 0.10), 'bitumen': (0.05, 0.06, 0.07), 'obsidian': (0.04, 0.04, 0.07),
    'gild': (0.88, 0.70, 0.22), 'gold': (0.90, 0.72, 0.20), 'golden': (0.92, 0.74, 0.24), 'coal': (0.05, 0.05, 0.05),
    'solar': (0.98, 0.62, 0.10), 'daffodil': (0.98, 0.86, 0.15), 'hyperpink': (0.98, 0.10, 0.55), 'seafoam': (0.35, 0.95, 0.70),
    'cerulean': (0.10, 0.55, 0.92), 'canary': (0.98, 0.90, 0.20), 'magenta': (0.95, 0.10, 0.70), 'lime': (0.65, 0.95, 0.10),
    'voltage': (0.80, 0.95, 0.10), 'peach': (0.99, 0.72, 0.50), 'ice': (0.70, 0.92, 0.98), 'orchid': (0.85, 0.40, 0.90),
    'crimson': (0.80, 0.06, 0.18), 'cyan': (0.10, 0.90, 0.92), 'mage': (0.55, 0.18, 0.85), 'jade': (0.10, 0.70, 0.50),
    'slate': (0.36, 0.42, 0.52), 'teal': (0.05, 0.62, 0.62), 'sunset': (0.96, 0.45, 0.25), 'ocean': (0.04, 0.32, 0.55),
    'ivory': (0.95, 0.92, 0.82), 'iris': (0.48, 0.30, 0.82), 'velvet': (0.30, 0.10, 0.40), 'tidepool': (0.08, 0.60, 0.62),
    'coral': (0.98, 0.45, 0.38), 'ember': (0.92, 0.32, 0.08), 'ultraviolet': (0.40, 0.12, 0.85), 'venetian': (0.70, 0.10, 0.10),
    'neon': (0.20, 0.98, 0.55), 'star': (0.85, 0.90, 1.0), 'halo': (0.55, 0.45, 0.85), 'white': (0.93, 0.94, 0.97), 'silver': (0.78, 0.80, 0.85),
}
CONCEPTS = {
    'event_horizon_spectra': [(0.02, 0.02, 0.05), (0.55, 0.12, 0.85), (0.10, 0.35, 0.92), (0.98, 0.55, 0.10), (0.05, 0.82, 0.70)],
    'chromatic_storm': list(RAINBOW), 'apex_spectrum': list(RAINBOW), 'spectrum_chaos_crown': list(RAINBOW),
    'prismatic_void_madness': [(0.02, 0.02, 0.04)] + list(RAINBOW),
    'hyperwave': [(0.06, 0.05, 0.22), (0.95, 0.10, 0.70), (0.10, 0.85, 0.95), (0.45, 0.20, 0.95)],
    'crystal_fade': [(0.20, 0.28, 0.40), (0.55, 0.78, 0.95), (0.85, 0.92, 0.98), (0.70, 0.60, 0.92)],
    'dark_matter_halo': [(0.02, 0.02, 0.06), (0.30, 0.10, 0.55), (0.15, 0.30, 0.80), (0.55, 0.45, 0.90)],
    'midnight_prism': [(0.03, 0.05, 0.18), (0.20, 0.20, 0.75), (0.85, 0.30, 0.65), (0.20, 0.80, 0.80)],
    'oil_nebula': [(0.04, 0.05, 0.08), (0.45, 0.15, 0.65), (0.10, 0.55, 0.55), (0.85, 0.45, 0.20)],
    'neon_nova': [(0.04, 0.04, 0.10), (0.98, 0.10, 0.60), (0.10, 0.95, 0.95), (0.65, 0.98, 0.15)],
    'molten_aurora': [(0.10, 0.03, 0.02), (0.95, 0.35, 0.05), (0.98, 0.70, 0.15), (0.10, 0.82, 0.45)],
    'white_castle_of_fear': [(0.22, 0.22, 0.30), (0.62, 0.64, 0.74), (0.92, 0.94, 0.98), (0.50, 0.30, 0.55)],
    'tar_eclipse': [(0.03, 0.03, 0.05), (0.30, 0.18, 0.40), (0.65, 0.30, 0.85), (0.95, 0.55, 0.20)],
    'bitumen_aurora': [(0.04, 0.05, 0.06), (0.05, 0.55, 0.40), (0.15, 0.85, 0.55), (0.55, 0.95, 0.70)],
    'obsidian_gild': [(0.03, 0.03, 0.05), (0.45, 0.32, 0.10), (0.90, 0.72, 0.22), (0.99, 0.90, 0.55)],
    'coal_starfield': [(0.03, 0.03, 0.06), (0.20, 0.30, 0.55), (0.70, 0.82, 0.98), (0.95, 0.96, 1.0)],
    'void_islands': [(0.02, 0.03, 0.06), (0.05, 0.45, 0.55), (0.10, 0.80, 0.70), (0.55, 0.95, 0.55)],
}

PF_MAP = [
    ("pf_event_horizon_spectra", "nebulabrot_density", 0), ("pf_chromatic_storm", "warp_moire", 0),
    ("pf_neon_nova", "ember_burst", 0), ("pf_molten_aurora", "magma", 0),
    ("pf_void_pearl", "opal_playofcolor", 0), ("pf_ion_trap", "arc_lattice", 0),
    ("pf_sapphire_blood", "mokume_gane", 0), ("pf_emerald_inferno", "lava_veins", 0),
    ("pf_violet_sunrise", "caustic_rose", 0), ("pf_copper_moon", "widmanstatten", 0),
    ("pf_toxic_horizon", "bz_spirals", 0), ("pf_glacial_burn", "thinfilm_bands", 0),
    ("pf_oil_nebula", "cd_dvd_rainbow", 0), ("pf_rose_quantum", "maurer_rose", 0),
    ("pf_cobalt_fire", "diffraction_grating", 0), ("pf_midnight_prism", "spectre_monotile", 0),
    ("pf_hyperwave", "lissajous_lattice", 0), ("pf_crystal_fade", "bismuth_terraces", 1),
    ("pf_dark_matter_halo", "depth_portal", 1), ("pf_apex_spectrum", "wallpaper_p6m", 0),
    ("pf_cluster_tar_eclipse", "soot_accum", 0), ("pf_cluster_bitumen_aurora", "oil_seep", 0),
    ("pf_cluster_obsidian_gild", "fracture_armor_sdf", 1), ("pf_cluster_coal_starfield", "sandblast_pit", 0),
    ("pf_cluster_void_islands", "terraced_strata", 1), ("pf_bright_solar_daffodil", "superformula_field", 0),
    ("pf_bright_hyperpink", "spray_drip_curtains", 0), ("pf_bright_seafoam_bolt", "dazzle_razor", 0),
    ("pf_bright_cerulean_pop", "bubble_lattice", 0), ("pf_bright_canary_glass", "rose_window", 0),
    ("pf_bright_magenta_arc", "magnetic_dipole", 0), ("pf_bright_lime_voltage", "tech_panel_circuit", 1),
    ("pf_bright_peach_fizz", "splatter_fleck_burst", 0), ("pf_bright_neon_ice_stream", "schlieren_refraction", 0),
    ("pf_bright_orchid_pulse", "cyclic_ca", 0), ("pf_blend_triad_mist", "electrostatic_equipotential", 0),
    ("pf_blend_quad_weave", "nacre", 0), ("pf_spectrum_chaos_crown", "lyapunov_marble", 0),
    ("pf_prismatic_void_madness", "peacock_optic", 0), ("pf_white_castle_of_fear", "spire_fractal", 1),
    ("pf_gradient_venetian_veil", "dark_damask", 0), ("pf_tri_crimson_cyan_mage", "girih_strapwork", 0),
    ("pf_quad_jade_violet_gold_slate", "ammann_beenker", 0), ("pf_fade_copper_teal_sunset", "liesegang_rings", 0),
    ("pf_blend_ocean_peach_ivory", "julia_smooth", 0), ("pf_iris_velvet_crossfade", "domain_coloring", 0),
    ("pf_spectral_tidepool_wash", "collatz_escape", 0), ("pf_midnight_coral_ember", "thorn_bramble", 0),
    ("pf_emerald_orchid_storm", "neural_ca_worms", 0), ("pf_golden_ultraviolet_fog", "dichroic_drift", 1),
]


def _n(a):
    a = a.astype(np.float32); lo = float(a.min()); r = float(np.ptp(a))
    return np.zeros_like(a) if r < 1e-9 else (a - lo) / r


def _edge(f):
    fl = cv2.GaussianBlur(f, (0, 0), 1.0)
    gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
    return _n(np.hypot(gx, gy))


def _coverage(f):
    f = _n(f); G = 8; H = f.shape[0] // G; a = 0
    for i in range(G):
        for j in range(G):
            if f[i*H:(i+1)*H, j*H:(j+1)*H].std() > 0.035:
                a += 1
    return a / 64.0


def _getfield(name, h, w, seed):
    if name in _ex.ENGINES:
        return _ex.field(name, h, w, seed)
    a = np.asarray(getattr(_fmold, name)(h, w, int(seed)), np.float32)
    if a.ndim == 3:
        a = a[..., :3].mean(2)
    if a.shape[:2] != (h, w):
        a = cv2.resize(a, (w, h))
    return _n(a)


def _mono(c):
    c = np.float32(c)
    warm = np.clip(c + np.float32([0.13, 0.03, -0.09]), 0, 1)
    cool = np.clip(c + np.float32([-0.09, 0.01, 0.15]), 0, 1)
    return [tuple(np.clip(c * 0.25, 0, 1)), tuple(warm), tuple(c), tuple(cool), tuple(np.clip(c * 0.5 + 0.5, 0, 1))]


def _from_colors(toks):
    cs = [np.float32(t) for t in toks]; base = tuple(np.clip(cs[0] * 0.28, 0, 1))
    if len(cs) >= 4:
        return [base] + [tuple(c) for c in cs[:4]]
    if len(cs) == 3:
        return [base, tuple(cs[0]), tuple(cs[1]), tuple(cs[2])]
    return [base, tuple(cs[0]), tuple(cs[1]), tuple(np.clip(cs[1] * 0.5 + 0.5, 0, 1))]


def _brighten(pal):
    out = []
    for i, c in enumerate(pal):
        c = np.float32(c)
        out.append(tuple(np.clip(c * 0.65 + 0.18, 0, 1)) if i == 0 else tuple(np.clip(c * 1.12 + 0.05, 0, 1)))
    return out


def _ensure_pop(pal):
    mx = max(max(c) for c in pal)
    if mx >= 0.62:
        return pal
    k = 0.85 / (mx + 1e-6)
    return [pal[0]] + [tuple(np.clip(np.float32(c) * k, 0, 1)) for c in pal[1:]]


def _palette(pfid):
    core = pfid[3:]; bright = core.startswith('bright_')
    if core in CONCEPTS:
        return [tuple(map(float, c)) for c in CONCEPTS[core]]
    for pre in ('cluster_', 'bright_', 'blend_', 'tri_', 'quad_', 'fade_', 'gradient_'):
        if core.startswith(pre):
            core = core[len(pre):]; break
    if core in CONCEPTS:
        pal = [tuple(map(float, c)) for c in CONCEPTS[core]]
    else:
        toks = [COLORS[t] for t in core.split('_') if t in COLORS]
        pal = _from_colors(toks) if len(toks) >= 2 else (_mono(toks[0]) if len(toks) == 1 else [tuple(map(float, c)) for c in RAINBOW])
    pal = _brighten(pal) if bright else pal
    return _ensure_pop(pal)


def _make_pf(pf, engine, depth):
    pal = _palette(pf)
    bright = pf[3:].startswith('bright_')
    prismatic = any(k in pf for k in ('spectra', 'spectrum', 'prism', 'chromatic', 'iris', 'oil_nebula',
                                      'hyperwave', 'apex', 'madness', 'crossfade', 'opal', 'nebula'))
    base = tuple(np.clip(np.float32(pal[0]) * (0.9 if bright else 0.55), 0, 1))
    hi = np.float32(pal[-1])
    relief = 34.0 if depth else 22.0

    @lru_cache(maxsize=4)
    def _fields(h, w, seed):
        f = _getfield(engine, h, w, seed)
        rc = _coverage(f)
        fillw = float(np.clip((0.90 - rc) * 2.2, 0.0, 0.5))
        amb = _n(cv2.GaussianBlur(f, (0, 0), 30))
        ff = _n(f * (1.0 - fillw * 0.6) + amb * fillw)
        col = _travel(ff, pal, irid=(0.30 if prismatic else 0.12), cycles=(2.7 if prismatic else 2.2),
                      sat=(0.98 if bright else 0.88), smooth=0.5, base=base)
        edge = _edge(f)
        col = col * (0.60 + ff[..., None] * 0.5) + edge[..., None] * hi[None, None, :] * 0.32
        col = np.clip((col - 0.5) * 1.13 + 0.5, 0, 1)
        if bright:
            col = np.clip(col * 1.10 + 0.05, 0, 1)
        paint = np.clip(col, 0, 1).astype(np.float32)
        g = _n(_d3._fbm(h, w, (seed ^ 0x2B) & 0xFFFFFFFF, octaves=4, base=3)) if hasattr(_d3, "_fbm") else _n(edge)
        M = np.clip(16 + np.clip(f * 1.5, 0, 1) * 205 + edge * 40, 0, 255)
        R = np.clip(58 + g * 150 - f * 25, 15, 255)
        Cc = np.clip(20 + (1 - f) * 120 + edge * 40, 16, 255)
        M, R, Cc = _d3.decorrelate_envelope(M, R, Cc, seed=(seed * 3 + 17) & 0xFFFFFFFF, blend=0.62, relief=relief)
        _msd = float(np.std(M))
        if 1e-3 < _msd < 20.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (20.0 / _msd), 0, 255)
        return paint, np.clip(M, 0, 255).astype(np.float32), np.clip(R, 15, 255).astype(np.float32), np.clip(Cc, 16, 255).astype(np.float32)

    def paint_fn(paint, shape, mask, seed, pm, bb, _f=pf):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        p, _M, _R, _C = _fields(h, w, _seed_of(_f, seed))
        return _blend_paint(paint, _upscale(p, fh, fw), _mask2(mask, fh, fw), pm)

    def base_spec_fn(shape, seed, sm, base_m=None, base_r=None, _f=pf, **_kw):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(Cc, 16, 255)

    def mono_spec_fn(shape, mask, seed, sm, _f=pf):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape)
        _p, M, R, Cc = _fields(h, w, _seed_of(_f, seed))
        M, R, Cc = (_upscale(a, fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)

    return base_spec_fn, paint_fn, mono_spec_fn


def install_prism_forge(mono_reg, base_reg=None):
    """Install the rebuilt Prism Forge over the recycled version, in BOTH registries."""
    ids = set()
    for pf, engine, depth in PF_MAP:
        bsf, pfn, msf = _make_pf(pf, engine, depth)
        if base_reg is not None:
            be = base_reg.get(pf)
            if isinstance(be, dict) and "base_spec_fn" in be:
                be["base_spec_fn"] = bsf; be["paint_fn"] = pfn; ids.add(pf)
        if pf in mono_reg:
            mono_reg[pf] = (msf, pfn); ids.add(pf)
    return len(ids)
