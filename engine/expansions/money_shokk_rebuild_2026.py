# ============================================================================
# engine/expansions/money_shokk_rebuild_2026.py
# Total rebuild of MONEY SHOKK (40 msh/msha/mshc/mshx_, all BASE-only), 2026-06-22.
# Replaces the recycled install_moneyshokk (_grad_struct 9-mode). Each finish =
# a DISTINCT exotic engine chosen to EVOKE its themed name (cobra->scale shards,
# widow->web, kintsugi->gold cracks, seigaiha->wave arcs, panther->schiller,
# afterburner->jet smoke, jackpot->coins...) + a hand-authored LUXURY palette so
# the paint matches the name. 40 unique engines => structural uniqueness for free.
# Owner taste: edgy/badass, premium/glossy, name colors dominate. Avoids the
# owner-disliked engines (burning_ship/nova/newton/penrose/clelie/hodgepodge...).
# Mirrors the locked prism_forge_rebuild_2026 contract. Install DEAD-LAST.
# 2-copy file (root -> electron-app/server).
# ============================================================================
from __future__ import annotations
from functools import lru_cache
import numpy as np
import cv2

from engine.paint_v2 import depth3d_2026 as _d3
from engine.paint_v2.fable_collection import _shape2, _seed_of, _work_shape, _mask2, _upscale, _pack_spec, _blend_paint
from engine.expansions.color_science_rebuild_2026 import _travel
from engine.expansions.prism_forge_rebuild_2026 import _getfield, _edge, _coverage, _n, _ensure_pop

# (finish_id, exotic_engine, depth_relief, prismatic_accent)
MSH_MAP = [
    ("msh_canary_coffin", "ossuary_lattice", 0, 0), ("msh_cerulean_cobra", "blade_shard_tess", 0, 0),
    ("msh_daffodil_bayou", "oil_seep", 0, 0), ("msh_hyperpink_torii", "girih_strapwork", 0, 0),
    ("msh_lime_scorpion", "armor_plate_bevel", 1, 0), ("msh_magenta_widow", "tracery_web", 0, 0),
    ("msh_neonice_rising", "schlieren_refraction", 0, 1), ("msh_orchid_kintsugi", "crack_network", 0, 1),
    ("msh_peach_jellyshock", "ferrofluid_spikes", 0, 1), ("msh_seafoam_piranha", "wildstyle_blades", 0, 0),
    ("msha_canary_gris_gris", "iron_filigree", 0, 0), ("msha_cherry_blossom_flux", "rhodonea_field", 0, 0),
    ("msha_emerald_brocade", "dark_damask", 0, 0), ("msha_fuji_neon_crest", "potential_flow_cylinders", 0, 1),
    ("msha_hyperpink_threads", "clifford_web", 0, 0), ("msha_peach_burlap", "carbon_forge_weave", 0, 0),
    ("msha_seafoam_charm", "quatrefoil_tess", 0, 0), ("msha_solar_moss", "dla_aggregate", 0, 0),
    ("msha_volcanic_croc", "extruded_tessellation", 1, 0), ("msha_waxen_voodoo", "thorn_bramble", 0, 0),
    ("mshc_acid_hornet", "hazard_chevron", 0, 0), ("mshc_amber_panther", "labradorite_schiller", 0, 1),
    ("mshc_canary_widow_redux", "spirograph_lattice", 0, 0), ("mshc_copper_jubilee", "hopalong_burst", 0, 0),
    ("mshc_emerald_sharkbite", "impact_shatter", 0, 0), ("mshc_oni_orchid_glass", "stress_fracture", 0, 1),
    ("mshc_oxblood_seigaiha", "ford_circles", 0, 0), ("mshc_rosethorn_bonsai", "pythagoras_tree", 0, 0),
    ("mshc_tigerblood_voltage", "arc_lattice", 0, 0), ("mshc_violet_kyoto", "rib_vault", 1, 0),
    ("mshx_blueprint_jackpot", "tech_panel_circuit", 1, 0), ("mshx_coral_sharkskin", "scratch_striation", 0, 0),
    ("mshx_dover_jackpot", "bubble_lattice", 0, 0), ("mshx_glacier_pinkslip", "terraced_strata", 1, 0),
    ("mshx_kintsugi_ransom", "pasteup_torn_layers", 0, 1), ("mshx_lime_afterburner", "curl_smoke", 0, 0),
    ("mshx_miami_blacklight", "glitch_mosh", 0, 1), ("mshx_prism_tipjar", "diffraction_grating", 0, 1),
    ("mshx_royal_sunstroke", "rose_window", 0, 0), ("mshx_venom_cashmere", "baroque_acanthus", 0, 0),
]

# Hand-authored LUXURY palettes [dark_base, c1, c2, accent] — name-true.
MSH_CONCEPTS = {
    "msh_canary_coffin": [(0.03, 0.03, 0.04), (0.12, 0.11, 0.05), (0.98, 0.88, 0.18), (0.75, 0.62, 0.12)],
    "msh_cerulean_cobra": [(0.02, 0.05, 0.12), (0.06, 0.30, 0.70), (0.12, 0.62, 0.95), (0.55, 0.90, 0.85)],
    "msh_daffodil_bayou": [(0.04, 0.08, 0.05), (0.20, 0.35, 0.15), (0.55, 0.65, 0.10), (0.98, 0.88, 0.20)],
    "msh_hyperpink_torii": [(0.10, 0.02, 0.04), (0.80, 0.12, 0.10), (0.98, 0.12, 0.55), (0.99, 0.55, 0.45)],
    "msh_lime_scorpion": [(0.06, 0.06, 0.04), (0.30, 0.28, 0.10), (0.65, 0.95, 0.10), (0.85, 0.95, 0.40)],
    "msh_magenta_widow": [(0.03, 0.02, 0.04), (0.20, 0.02, 0.10), (0.95, 0.08, 0.55), (0.80, 0.05, 0.15)],
    "msh_neonice_rising": [(0.03, 0.08, 0.12), (0.10, 0.55, 0.75), (0.55, 0.92, 0.98), (0.85, 0.98, 1.0)],
    "msh_orchid_kintsugi": [(0.10, 0.04, 0.12), (0.55, 0.20, 0.60), (0.85, 0.40, 0.90), (0.95, 0.78, 0.30)],
    "msh_peach_jellyshock": [(0.10, 0.05, 0.10), (0.99, 0.70, 0.50), (0.98, 0.45, 0.55), (0.30, 0.92, 0.95)],
    "msh_seafoam_piranha": [(0.03, 0.10, 0.08), (0.30, 0.92, 0.70), (0.65, 0.98, 0.85), (0.75, 0.10, 0.12)],
    "msha_canary_gris_gris": [(0.05, 0.05, 0.05), (0.35, 0.34, 0.30), (0.70, 0.66, 0.30), (0.98, 0.90, 0.25)],
    "msha_cherry_blossom_flux": [(0.12, 0.04, 0.08), (0.55, 0.15, 0.30), (0.98, 0.55, 0.70), (0.99, 0.82, 0.88)],
    "msha_emerald_brocade": [(0.02, 0.10, 0.07), (0.04, 0.45, 0.28), (0.10, 0.70, 0.42), (0.88, 0.72, 0.28)],
    "msha_fuji_neon_crest": [(0.04, 0.06, 0.14), (0.25, 0.40, 0.75), (0.55, 0.75, 0.95), (0.10, 0.95, 0.85)],
    "msha_hyperpink_threads": [(0.08, 0.02, 0.06), (0.55, 0.05, 0.35), (0.98, 0.10, 0.62), (0.99, 0.55, 0.80)],
    "msha_peach_burlap": [(0.12, 0.08, 0.05), (0.55, 0.40, 0.25), (0.85, 0.62, 0.42), (0.99, 0.78, 0.55)],
    "msha_seafoam_charm": [(0.03, 0.10, 0.09), (0.20, 0.70, 0.58), (0.50, 0.92, 0.78), (0.85, 0.92, 0.90)],
    "msha_solar_moss": [(0.04, 0.07, 0.03), (0.25, 0.40, 0.12), (0.55, 0.70, 0.18), (0.99, 0.75, 0.15)],
    "msha_volcanic_croc": [(0.06, 0.02, 0.02), (0.35, 0.08, 0.04), (0.92, 0.30, 0.05), (0.22, 0.32, 0.12)],
    "msha_waxen_voodoo": [(0.06, 0.05, 0.06), (0.45, 0.40, 0.32), (0.88, 0.82, 0.66), (0.70, 0.10, 0.12)],
    "mshc_acid_hornet": [(0.04, 0.04, 0.03), (0.15, 0.14, 0.04), (0.95, 0.82, 0.08), (0.65, 0.95, 0.10)],
    "mshc_amber_panther": [(0.03, 0.03, 0.04), (0.20, 0.14, 0.06), (0.86, 0.55, 0.12), (0.98, 0.78, 0.35)],
    "mshc_canary_widow_redux": [(0.03, 0.03, 0.04), (0.30, 0.28, 0.06), (0.98, 0.88, 0.18), (0.75, 0.06, 0.12)],
    "mshc_copper_jubilee": [(0.10, 0.05, 0.02), (0.55, 0.28, 0.10), (0.85, 0.50, 0.18), (0.98, 0.82, 0.35)],
    "mshc_emerald_sharkbite": [(0.02, 0.10, 0.08), (0.04, 0.50, 0.32), (0.20, 0.80, 0.55), (0.80, 0.88, 0.90)],
    "mshc_oni_orchid_glass": [(0.06, 0.02, 0.06), (0.55, 0.06, 0.18), (0.85, 0.35, 0.85), (0.80, 0.90, 0.95)],
    "mshc_oxblood_seigaiha": [(0.10, 0.02, 0.03), (0.35, 0.05, 0.08), (0.10, 0.25, 0.45), (0.80, 0.85, 0.88)],
    "mshc_rosethorn_bonsai": [(0.06, 0.04, 0.04), (0.20, 0.35, 0.18), (0.55, 0.60, 0.25), (0.92, 0.30, 0.45)],
    "mshc_tigerblood_voltage": [(0.06, 0.03, 0.02), (0.55, 0.05, 0.05), (0.95, 0.50, 0.08), (0.85, 0.95, 0.15)],
    "mshc_violet_kyoto": [(0.06, 0.03, 0.10), (0.30, 0.12, 0.45), (0.60, 0.25, 0.80), (0.88, 0.72, 0.30)],
    "mshx_blueprint_jackpot": [(0.02, 0.06, 0.14), (0.08, 0.30, 0.62), (0.30, 0.55, 0.85), (0.95, 0.80, 0.25)],
    "mshx_coral_sharkskin": [(0.10, 0.05, 0.06), (0.55, 0.30, 0.28), (0.98, 0.50, 0.42), (0.50, 0.55, 0.58)],
    "mshx_dover_jackpot": [(0.10, 0.10, 0.12), (0.55, 0.58, 0.62), (0.90, 0.92, 0.95), (0.95, 0.80, 0.25)],
    "mshx_glacier_pinkslip": [(0.05, 0.10, 0.14), (0.40, 0.70, 0.85), (0.80, 0.92, 0.98), (0.98, 0.45, 0.65)],
    "mshx_kintsugi_ransom": [(0.04, 0.04, 0.05), (0.18, 0.18, 0.20), (0.55, 0.55, 0.58), (0.95, 0.78, 0.30)],
    "mshx_lime_afterburner": [(0.03, 0.05, 0.08), (0.10, 0.40, 0.65), (0.55, 0.95, 0.20), (0.95, 0.98, 0.55)],
    "mshx_miami_blacklight": [(0.04, 0.02, 0.10), (0.10, 0.85, 0.85), (0.95, 0.10, 0.65), (0.55, 0.20, 0.95)],
    "mshx_prism_tipjar": [(0.03, 0.03, 0.05), (0.95, 0.10, 0.30), (0.10, 0.80, 0.85), (0.95, 0.82, 0.25)],
    "mshx_royal_sunstroke": [(0.06, 0.03, 0.12), (0.30, 0.10, 0.55), (0.65, 0.25, 0.85), (0.99, 0.80, 0.20)],
    "mshx_venom_cashmere": [(0.05, 0.08, 0.03), (0.30, 0.55, 0.10), (0.55, 0.90, 0.15), (0.82, 0.74, 0.60)],
}


def _palette(fid):
    return _ensure_pop([tuple(map(float, c)) for c in MSH_CONCEPTS[fid]])


def _make_msh(fid, engine, depth, prismatic):
    pal = _palette(fid)
    base = tuple(np.clip(np.float32(pal[0]) * 0.85, 0, 1))
    hi = np.float32(pal[-1])
    relief = 36.0 if depth else 22.0

    nmid = np.clip((np.float32(pal[1]) + np.float32(pal[2])) * 0.5, 0, 1)   # named mid-tone for empty-area lift
    @lru_cache(maxsize=4)
    def _fields(h, w, seed):
        f = _getfield(engine, h, w, seed)
        rc = _coverage(f)
        fillw = float(np.clip((0.92 - rc) * 2.6, 0.0, 0.62))                 # sparse engines fill more (coverage)
        amb = _n(cv2.GaussianBlur(f, (0, 0), 30))
        ff = _n(f * (1.0 - fillw * 0.6) + amb * fillw)
        col = _travel(ff, pal, irid=(0.28 if prismatic else 0.13), cycles=(2.7 if prismatic else 2.1),
                      sat=0.95, smooth=0.5, base=base)
        edge = _edge(f)
        # luxe: rich body + bright accent on the structure's hero ridges (gloss pop)
        col = col * (0.64 + ff[..., None] * 0.5) + edge[..., None] * hi[None, None, :] * 0.34
        # faint NAMED-color glow in dead/empty areas so light names aren't lost to black (keeps moody themes moody)
        col = col + ((1.0 - ff)[..., None] ** 2) * nmid[None, None, :] * 0.13
        col = np.clip((col - 0.5) * 1.15 + 0.5, 0, 1)
        col = np.clip(col * 1.07 + 0.03, 0, 1)
        paint = np.clip(col, 0, 1).astype(np.float32)
        g = _n(_d3._fbm(h, w, (seed ^ 0x2B) & 0xFFFFFFFF, octaves=4, base=3)) if hasattr(_d3, "_fbm") else _n(edge)
        # premium spec: bright metallic flake on features, GLOSSY wet clearcoat
        M = np.clip(16 + np.clip(f * 1.5, 0, 1) * 210 + edge * 40, 0, 255)
        R = np.clip(48 + g * 150 - f * 28, 15, 255)                  # low-ish = glossy
        Cc = np.clip(28 + (1 - f) * 130 + edge * 45, 16, 255)        # wet clearcoat pools
        M, R, Cc = _d3.decorrelate_envelope(M, R, Cc, seed=(seed * 3 + 23) & 0xFFFFFFFF, blend=0.62, relief=relief)
        _msd = float(np.std(M))
        if 1e-3 < _msd < 20.0:
            _mm = float(np.mean(M)); M = np.clip(_mm + (M - _mm) * (20.0 / _msd), 0, 255)
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


def install_money_shokk(mono_reg, base_reg=None):
    """Install the rebuilt Money Shokk over the recycled version (BASE-only finishes)."""
    ids = set()
    for fid, engine, depth, prismatic in MSH_MAP:
        bsf, pfn, msf = _make_msh(fid, engine, depth, prismatic)
        if base_reg is not None:
            be = base_reg.get(fid)
            if isinstance(be, dict) and "base_spec_fn" in be:
                be["base_spec_fn"] = bsf; be["paint_fn"] = pfn; ids.add(fid)
        if fid in mono_reg:
            mono_reg[fid] = (msf, pfn); ids.add(fid)
    return len(ids)
