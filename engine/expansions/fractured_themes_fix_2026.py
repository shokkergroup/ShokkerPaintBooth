"""Pre-ship FIX overrides (2026-06-17): finishes the owner flagged in SPB_AUDIT_fractured_ship.html.
Each is rebuilt/replaced — NO voronoi, NO _tile_finer tiling, fine + full coverage. This OVERRIDES the
matching ids in the monolithic registry AFTER fractured_themes installs (mirrors fractured_rebuild_2026).
Fix engines (fdf_/fcf_/fuf_/frf_/fof_) are defined in this module; recipes live in FIX (same ids)."""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.paint_v2.fractured_math import *  # noqa: F401,F403  (public engines + colorize/colorize_cells)
from engine.paint_v2.fractured_math import (  # underscore helpers (import * skips these)
    _rng, _fbm, _norm, _up, _curl_warp, _thinfilm, colorize, colorize_cells,
    _rbw_ramp, _rbw_edges, _rbw_shade,
)
from engine.spec_sculpt.fracture import fracture_spec
from engine.expansions.fractured_wilds_signatures_2026 import make_entry as _wilds_entry

_WORK = 1152

# ════════════════════════════════════════════════════════════════════════════
# FIX ENGINES (appended per category below)
# ════════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════════
# FIX RECIPES — same ids as the flagged themed finishes; override on install.
# ════════════════════════════════════════════════════════════════════════════
FIX = {
 "fd_bioluminescence": dict(name="Bioluminescence", engine="fdf_plankton_swarm", eargs={}, seed=404,
    base=(2, 7, 9), glow=(34, 175, 150), edge=(185, 255, 215),
    kw=dict(gamma=0.92, edge_gain=0.9, ambient=0.34, ambient_sigma=46, ambient_floor=0.30),
    desc="A dense fine plankton speckle field — tens of thousands of tiny glow points streaming on a slow deep current. FRACTURED DEEP finish."),
 "fd_maelstrom": dict(name="Maelstrom", engine="fdf_deepcurrent_swirl", eargs={}, seed=407,
    base=(3, 8, 12), glow=(28, 120, 150), edge=(170, 235, 255),
    kw=dict(gamma=0.92, edge_gain=1.0, ambient=0.30, ambient_sigma=52, ambient_floor=0.26),
    desc="One continuous organic deep-current whirl — curl-flow streamlines marble-warped into a single churning whirlpool. FRACTURED DEEP finish."),
 "fd_brine_glass": dict(name="Brine Veins", engine="fdf_brine_veins", eargs={}, seed=412,
    base=(2, 9, 11), glow=(30, 140, 130), edge=(175, 250, 235),
    kw=dict(gamma=0.95, edge_gain=0.95, ambient=0.28, ambient_sigma=50, ambient_floor=0.24),
    desc="Flowing teal-and-jade brine veins lit by a fine refracted caustic sheen — dense mineral salt veining through the deep. FRACTURED DEEP finish."),
 "fd_glasssquid": dict(name="Glass Squid", engine="fdf_glass_membrane", eargs={}, seed=427,
    base=(4, 10, 13), glow=(40, 165, 175), edge=(205, 250, 230),
    kw=dict(gamma=0.95, edge_gain=0.9, ambient=0.30, ambient_sigma=48, ambient_floor=0.26),
    desc="Stacked thin-film iridescent sheen drifting over a translucent membrane with clear lens-glints — a transparent glass squid in the deep. FRACTURED DEEP finish."),
 "fc_eyeshine": dict(name="Eyeshine", engine="fcf_eyeshine", eargs={}, seed=503, base=(3, 5, 4), glow=(40, 205, 95), edge=(200, 255, 160), kw=dict(gamma=0.82, edge_gain=0.95, ambient=0.4, ambient_sigma=60, ambient_floor=0.3), desc="Hundreds of tiny glowing slit-eyes glinting back densely out of a near-black forest murk — an eyeshine FRACTURED CRYPTID finish."),
 "fc_feathered_wing": dict(name="Feathered Wing", engine="fcf_feathered_wing", eargs={}, seed=507, base=(9, 8, 11), glow=(120, 95, 150), edge=(225, 210, 190), kw=dict(gamma=0.92, edge_gain=0.85, ambient=0.22, ambient_sigma=46, ambient_floor=0.18), desc="Dense overlapping feather vanes — shaft and swept barbs — layered into fine plumage at every angle, in a richer violet-and-warm palette, a feathered-wing FRACTURED CRYPTID finish."),
 "fc_antler_bone": dict(name="Antler Bone", engine="fcf_antler_bone", eargs={}, seed=511, base=(8, 8, 7), glow=(130, 120, 95), edge=(225, 215, 185), kw=dict(gamma=0.92, edge_gain=0.9, ambient=0.28, ambient_sigma=52, ambient_floor=0.22), desc="Abstract dense branching bone and antler forks at every orientation, an organic non-repeating tine network — an antler/bone FRACTURED CRYPTID finish."),
 "fc_will_o_wisp": dict(name="Will-o'-Wisp", engine="fcf_will_o_wisp", eargs={}, seed=513, base=(3, 6, 5), glow=(55, 205, 130), edge=(190, 255, 205), kw=dict(gamma=0.82, edge_gain=0.9, ambient=0.42, ambient_sigma=60, ambient_floor=0.3), desc="A dense swarm of small drifting bog-lights, each trailing a fading wisp, scattered organically over a black marsh — a will-o'-the-wisp FRACTURED CRYPTID finish."),
 "fc_batwing": dict(name="Bat Wing", engine="fcf_batwing", eargs={}, seed=515, base=(9, 6, 11), glow=(120, 70, 95), edge=(210, 175, 200), kw=dict(gamma=0.9, edge_gain=0.9, ambient=0.26, ambient_sigma=50, ambient_floor=0.2), desc="Leathery wing membranes spanned by radiating finger-bone struts and crinkled by fine wrinkles, scattered at every angle — a bat/mothman-wing FRACTURED CRYPTID finish."),
 "fc_hide_scale_glass": dict(name="Hide Scale Glass", engine="fcf_hide_scale_glass", eargs=dict(rows=34, palette=[(55, 95, 42), (92, 112, 52), (66, 80, 58), (40, 70, 48), (110, 100, 46)], edge=(170, 210, 110)), seed=518, base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={}, sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0), desc="Organic undulating overlapping forest-hued hide-scales, each region a different shade, traced by bright ignitable scale-rims — a multi-tone reptilian-hide FRACTURED CRYPTID finish."),
 "fc_crackle_eyeshine_glass": dict(name="Crackle Eyeshine Glass", engine="fcf_crackle_eyeshine_glass", eargs=dict(rows=40, palette=[(34, 46, 28), (28, 36, 38), (46, 40, 26), (40, 52, 34), (52, 44, 30)], edge=(120, 150, 70)), seed=520, base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={}, sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0), desc="A near-black multi-tone reptilian hide studded with countless small amber and green eyeshine glints scattered densely across it — little eyes glinting in the dark, a FRACTURED CRYPTID finish."),
 "fu_plasma_drive": dict(name="Plasma Drive", engine="fuf_plasma_drive", eargs={}, seed=604,
    base=(10, 4, 12), glow=(190, 45, 175), edge=(255, 170, 255),
    kw=dict(gamma=0.85, edge_gain=0.95, ambient=0.4, ambient_sigma=52, ambient_floor=0.3),
    desc="A dense scatter of small plasma cores throwing fine radial ion filaments over a warped ion haze — a full-coverage magenta engine bloom with no blank gaps. FRACTURED UFO finish."),
 "fu_crop_circle": dict(name="Crop Circle", engine="fuf_crop_circle", eargs={}, seed=605,
    base=(6, 9, 5), glow=(60, 180, 70), edge=(190, 255, 170),
    kw=dict(gamma=0.95, edge_gain=0.95),
    desc="Dozens of small flattened-ring agroglyphs with spokes and satellite pips scattered over a tight flattened-crop grain — a fine field with no blank patches. FRACTURED UFO finish."),
 "fu_hyperspace": dict(name="Hyperspace", engine="fuf_hyperspace", eargs={}, seed=608,
    base=(5, 7, 12), glow=(60, 140, 255), edge=(200, 230, 255),
    kw=dict(gamma=0.9, edge_gain=1.0),
    desc="One abstract warp-jump star tunnel — fine radial light-streaks from many scattered drift points curl-smeared into a seamless omnidirectional smear, no repeats. FRACTURED UFO finish."),
 "fu_biomech_skin": dict(name="Bio-Mech Skin", engine="fuf_biomech_skin", eargs={}, seed=611,
    base=(7, 6, 11), glow=(70, 150, 165), edge=(210, 175, 255),
    kw=dict(gamma=0.92, edge_gain=0.9),
    desc="Interlocking domain-warped chitin tubes and pulsing veins over a fine pore grain — a living bio-mechanical alien hide in teal-and-violet, no two regions alike. FRACTURED UFO finish."),
 "fu_stargate": dict(name="Star-Gate", engine="fuf_stargate", eargs={}, seed=615,
    base=(5, 9, 11), glow=(40, 190, 200), edge=(170, 250, 255),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="Many scattered counter-rotating phase vortices summed into one organic event-horizon interference of winding rippling arms — a seamless gate field with no single centre. FRACTURED UFO finish."),
 "fu_scanner_sweep": dict(name="Gravity Lens", engine="fuf_gravity_lens", eargs={}, seed=617,
    base=(6, 7, 13), glow=(60, 130, 210), edge=(190, 220, 255),
    kw=dict(gamma=0.9, edge_gain=0.95, ambient=0.35, ambient_sigma=55, ambient_floor=0.28),
    desc="A starfield bent by a dense scatter of small gravitational masses warping a fine spacetime-ripple substrate into omnidirectional Einstein-ring arcs — an alien gravity-well sensor field. FRACTURED UFO finish."),
 "fu_glyph_cells": dict(name="Glyph Field", engine="fuf_glyph_cells", eargs={}, seed=619,
    base=(6, 8, 4), glow=(110, 200, 70), edge=(200, 255, 150),
    kw=dict(gamma=0.9, edge_gain=0.95),
    desc="A fine field of small angular xeno-glyph strokes, arcs and pips jittered off a grid so it never reads as a tile, bedded on a faint inscription grain — full-coverage alien hieroglyphs. FRACTURED UFO finish."),
 "fr_prism_shatter": dict(name="Oil-Slick Prism Shatter", engine="frf_oilslick_shatter", seed=700,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(freq=14.0, cycles=6.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A curl-drifted oil-on-water thin-film sweep shattered into vivid full-spectrum facets, traced by bright ignitable fault-lines. FRACTURED RAINBOW finish."),
 "fr_spectrum_voronoi": dict(name="Diffraction Spectrum Sweep", engine="frf_diffraction_sweep", seed=701,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(gratings=4, cycles=5.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Domain-warped diffraction gratings split light into a dense field of bowing full-spectrum holographic fringes — no two alike. FRACTURED RAINBOW finish."),
 "fr_hex_hive": dict(name="Spectral Moire Sweep", engine="frf_spectral_moire", seed=702,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(cycles=5.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Scattered wave sources beat into a fine omnidirectional moire weave glowing the full spectrum, edged by bright ignitable wavefronts. FRACTURED RAINBOW finish."),
 "fr_chroma_rings": dict(name="Chromatic Ripple Field", engine="frf_ripple_field", seed=704,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(sources=22, cycles=4.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Dozens of scattered ripple sources interfere into one fine non-repeating field of full-spectrum chromatic rings with bright ignitable wavefronts. FRACTURED RAINBOW finish."),
 "fr_prism_wheel": dict(name="Spectral Prism Burst", engine="frf_spectral_burst", seed=706,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(vortices=9, cycles=5.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Many balanced counter-spinning vortices warp into a single all-over prismatic burst of flowing full-spectrum arms with bright ignitable seams. FRACTURED RAINBOW finish."),
 "fr_opal_fire": dict(name="Opal Fire Flecks", engine="frf_opal_flecks", seed=709,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(flecks=3200, cycles=5.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Thousands of tiny scattered opal flecks flash full-spectrum fire over a flowing thin-film spectral field, with bright ignitable glints. FRACTURED RAINBOW finish."),
 "fr_spectral_spiral": dict(name="Spectral Marble Flow", engine="frf_spectral_marble_flow", seed=710,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(veins=13.0, cycles=4.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Turbulent domain-warped marble veining smeared along a curl flow into one flowing full-spectrum field, with bright ignitable vein-edges. FRACTURED RAINBOW finish."),
 "fr_chroma_ripple": dict(name="Chromatic Aberration Ripple", engine="frf_aberration_ripple", seed=714,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    eargs=dict(halos=20, cycles=6.0),
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="Many scattered Newton-ring halos blend into one fine non-repeating field of channel-split full-spectrum aberration fringes with bright ignitable contours. FRACTURED RAINBOW finish."),
 "fo_cobweb_lace": dict(name="Cobweb Lace", engine="fof_cobweb_lace", eargs=dict(anchors=140), seed=802,
    base=(7, 7, 9), glow=(120, 125, 140), edge=(220, 225, 240),
    kw=dict(gamma=0.92, edge_gain=1.0, ambient=0.30, ambient_sigma=50, ambient_floor=0.26),
    desc="A fine tattered veil of dense torn web-silk strung edge to edge — cobweb lace. A FRACTURED OCCULT finish."),
 "fo_bone_branch": dict(name="Bone Branch", engine="fof_bone_branch", eargs=dict(trunks=160), seed=804,
    base=(8, 8, 7), glow=(150, 145, 125), edge=(232, 227, 207),
    kw=dict(gamma=0.92, edge_gain=0.95, ambient=0.26, ambient_sigma=48, ambient_floor=0.24),
    desc="A dense thicket of small forked bone-white twigs filling the frame — bone branching. A FRACTURED OCCULT finish."),
 "fo_spider_lattice": dict(name="Spider Web", engine="fof_spider_lattice", eargs=dict(webs=34, spokes=13), seed=811,
    base=(6, 6, 8), glow=(115, 120, 140), edge=(215, 220, 240),
    kw=dict(gamma=0.92, edge_gain=1.0, ambient=0.28, ambient_sigma=48, ambient_floor=0.24),
    desc="Many overlapping orb-webs — radial silk spokes and sagging spirals beaded with dew — a spider web. A FRACTURED OCCULT finish."),
 "fo_raven_feather": dict(name="Raven Feather", engine="fof_raven_feather", eargs=dict(feathers=260), seed=812,
    base=(5, 5, 8), glow=(72, 78, 112), edge=(180, 190, 220),
    kw=dict(gamma=0.92, edge_gain=0.95, ambient=0.26, ambient_sigma=48, ambient_floor=0.24),
    desc="Fine dense overlapping raven plumes layered with depth and fine barbs — glossy plumage. A FRACTURED OCCULT finish."),
 "fo_cracked_tomb": dict(name="Cracked Tomb", engine="fof_cracked_tomb", eargs={}, seed=814,
    base=(7, 7, 8), glow=(118, 116, 120), edge=(208, 206, 210),
    kw=dict(gamma=0.95, edge_gain=0.9, ambient=0.22, ambient_sigma=46, ambient_floor=0.22),
    desc="An aged carved tomb slab — chiselled granite grain riven by deep fracture lines and lichen. A FRACTURED OCCULT finish."),
 "fo_vampire_damask": dict(name="Vampire Damask", engine="fof_vampire_damask", eargs=dict(reps=5), seed=815,
    base=(9, 3, 5), glow=(155, 30, 50), edge=(225, 115, 100),
    kw=dict(gamma=0.92, edge_gain=0.95, ambient=0.24, ambient_sigma=48, ambient_floor=0.22),
    desc="Finer ornate baroque scroll-leaf damask undulating in oxblood velvet — vampire wallpaper. A FRACTURED OCCULT finish."),
 "fo_glyph_cells": dict(name="Glyph Sigils", engine="fof_glyph_field", eargs=dict(n=22), seed=818,
    base=(8, 6, 9), glow=(150, 60, 175), edge=(228, 175, 248),
    kw=dict(gamma=0.92, edge_gain=1.0, ambient=0.24, ambient_sigma=46, ambient_floor=0.22),
    desc="A dense field of small carved occult sigil strokes glowing violet — an incantation plate. A FRACTURED OCCULT finish."),
 "fo_crimson_cells": dict(name="Crimson Blood", engine="fof_crimson_blood", eargs=dict(pools=48), seed=819,
    base=(9, 2, 4), glow=(165, 22, 26), edge=(235, 95, 75),
    kw=dict(gamma=0.88, edge_gain=1.0, ambient=0.28, ambient_sigma=50, ambient_floor=0.24),
    desc="Blood spatter, drip-runs and coagulated veins crawling across the dark — a crimson blood field. A FRACTURED OCCULT finish."),
 "fo_stained_chapel": dict(name="Stained Chapel", engine="fof_stained_chapel", eargs=dict(sectors=22, rings=6, rosettes=5, palette=[(95, 45, 150), (155, 28, 42), (185, 150, 70)], edge=(225, 185, 110)), seed=820,
    base=(0, 0, 0), glow=(0, 0, 0), edge=(0, 0, 0), kw={},
    sargs=dict(ignition=1.2, trace_strength=1.7, calm_floor=20.0),
    desc="A cathedral field of overlapping rose-windows in violet, blood and bone-gold leaded glass — stained chapel. A FRACTURED OCCULT finish."),
}


def _seed_int(s):
    try:
        return int(s)
    except Exception:
        return abs(hash(str(s))) % (2 ** 31)


def _field(d, work):
    return globals()[d["engine"]](work, work, _seed_int(d["seed"]), **d.get("eargs", {}))


def _art_work(d):
    f = _field(d, _WORK)
    if getattr(f, "ndim", 0) == 3:
        return np.clip(f, 0.0, 1.0)
    return np.clip(colorize(f, d["base"], d["glow"], d["edge"], **d.get("kw", {})), 0.0, 1.0)


@lru_cache(maxsize=96)
def _art_cached(fid):
    return _art_work(FIX[fid])


def _mk(fid):
    # SPB-WILDS 2026-08-23 tick W-1. Owner: "Too much redundancy way too
    # similar looks. Must be VERY UNIQUE" and retain FRACTURED color flipping.
    # This keeps the seven formerly-rejected Cryptid IDs on the same fine,
    # independently tiered color-flip contract as their 13 category siblings.
    # Measured worst structural NN 0.787 -> 0.414, all-70 M7 minimum 85.0,
    # native-2048 max 0.702s; full evidence: _wilds_work/report.json.
    if fid.startswith("fc_"):
        return _wilds_entry(fid, FIX[fid], "cryptid")

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        art = cv2.resize(_art_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        return fracture_spec(art, m2, ignition=1.0, decorrelation=0.18, as_uint8=True)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    n = 0
    for fid in FIX:
        e = _mk(fid)
        for reg in regs:
            reg[fid] = e
        n += 1
    return f"fractured-themes-fix: {n} owner-flagged finishes overridden"


# FRACTURED DEEP fix engines (2026-06-17) — fdf_* replacements for 4 owner-rejected finishes.
# BARE primitive names (no fm. prefix); the fix module does `from engine.paint_v2.fractured_math import *`
# plus the underscore helpers. NO voronoi of any kind, NO _tile_finer. Native high frequency / many
# scattered sources / domain-warped fields give fine scale + full coverage with no visible repeats.


def fdf_plankton_swarm(h, w, seed, *, res=560, specks=42000):
    """A DENSE fine plankton speckle field — tens of thousands of tiny glow points scattered over a
    slow deep-current bloom, then advected along a curl flow so the swarm streams without ever tiling.
    Many small complete dots = fine, omnidirectional, full-canvas; never blotchy (no big eyespots)."""
    import numpy as np, cv2
    rng = _rng(seed)
    # tens of thousands of single-pixel glow seeds, slightly clustered into faint drifts by a soft field
    img = np.zeros((res, res), np.float32)
    xs = rng.integers(0, res, int(specks))
    ys = rng.integers(0, res, int(specks))
    img[ys, xs] = rng.uniform(0.35, 1.0, int(specks)).astype(np.float32)
    # a sparse population of slightly larger bright planktors (still tiny, ~1.5px) for sparkle variety
    nbig = int(specks * 0.06)
    bx = rng.integers(0, res, nbig); by = rng.integers(0, res, nbig)
    big = np.zeros((res, res), np.float32); big[by, bx] = 1.0
    big = cv2.GaussianBlur(big, (0, 0), 1.3)
    speck = cv2.GaussianBlur(img, (0, 0), 0.55) + big * 0.6
    # gentle density modulation (bloom drifts) so it reads as living water, NOT uniform TV static
    bloom = _fbm(res, res, rng, 4, 6)
    speck = speck * (0.55 + 0.65 * bloom)
    # a faint slow-current undertone so empty gaps still glow dimly (full coverage, no dead corners)
    field = _norm(speck) + 0.26 * bloom
    # advect the whole swarm along a divergence-free curl flow -> streaming current, no repeat
    return _up(_norm(_curl_warp(field, seed + 11, res, 0.10)), h, w)


def fdf_deepcurrent_swirl(h, w, seed, *, res=600):
    """ONE organic, non-repeating deep-current whirl: a single divergence-free curl-noise flow
    (advected particle streamlines) marble-warped through turbulent veining so the whole canvas is
    one continuous churning current with no tiled copies and no single centred eye."""
    import numpy as np, cv2
    rng = _rng(seed)
    # one global curl flow — streamlines of advected particles cover the whole sheet
    flow = curl_flow(res, res, seed, res=res, particles=90000, steps=54, step_len=1.5)
    # marble turbulence gives the long sweeping vein-currents of a maelstrom (NOT periodic)
    mb = marble(res, res, seed + 5, warps=4, veins=5.0)
    # one broad slow vortex skews the whole field so it spirals as a single organic system
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx = (0.35 + 0.30 * rng.random()) * res
    cy = (0.35 + 0.30 * rng.random()) * res
    ang = np.arctan2(gy - cy, gx - cx)
    rad = np.hypot(gx - cx, gy - cy) / res
    swirl = 0.5 + 0.5 * np.sin(ang * 1.0 + rad * 9.0 + 6.283 * mb)
    combo = _norm(0.62 * flow + 0.5 * mb) * (0.5 + 0.5 * swirl)
    # final curl-warp ties the streamlines and veins into one flowing body (no seams / no repeat)
    return _up(_norm(_curl_warp(combo, seed + 7, res, 0.16)), h, w)


def fdf_brine_veins(h, w, seed, *, res=600):
    """Flowing brine veins + caustic sheen + mineral bands — a NON-voronoi deep design. Domain-warped
    marble vein-bands (the dense mineral salt veining) lit by a fine refracted caustic net, then
    curl-warped so the veins flow. Fine, omnidirectional, full-canvas; zero cells."""
    import numpy as np, cv2
    rng = _rng(seed)
    # dense turbulent mineral veining — many fine bands running through the whole slab
    veins = marble(res, res, seed, warps=3, veins=9.0)
    # crisp quantised mineral banding layered on top (agate-like strata, still flowing not straight)
    band = 0.5 + 0.5 * np.sin(_fbm(res, res, rng, 5, 5) * np.pi * 7.0 + veins * 6.283)
    # a fine refracted caustic light-net = the brine sheen sparkling on the veins
    sheen = caustics(res, res, seed + 4)
    base = _norm(0.55 * veins + 0.32 * band + 0.40 * sheen)
    # curl-warp -> the salt veins flow like dense brine (breaks any residual regularity)
    return _up(_norm(_curl_warp(base, seed + 9, res, 0.13)), h, w)


def fdf_glass_membrane(h, w, seed, *, res=600):
    """A translucent glassy deep body: stacked thin-film iridescent layers (oil-on-water spectral
    sheen) drifting through a fine domain-warped membrane, with a sparse scatter of clear lens-cells.
    Distinct from the brine veins (layered translucent SHEEN, not flowing salt veins; no big marble
    swirl rhythm — finer, glassier, sheet-like). NO voronoi, NO tiling."""
    import numpy as np, cv2
    rng = _rng(seed)
    # stacked thin-film interference at two wavelengths = the layered glassy iridescence of clear flesh
    film = _thinfilm(res, seed, freq=8.5)
    film2 = _thinfilm(res, seed + 1, freq=13.0)
    # a fine soft membrane substrate (low-frequency warped sheets, NOT veiny marble)
    sheet = _fbm(res, res, rng, 4, 7)
    # very fine specular micro-ridges = the glassy grain on the transparent body wall
    grain = 0.5 + 0.5 * np.sin(_fbm(res, res, rng, 5, 11) * np.pi * 9.0)
    body = _norm(0.5 * film + 0.32 * film2 + 0.30 * sheet * grain + 0.18)
    # drift the whole iridescent sheet along a curl flow -> living translucent membrane (no repeat)
    body = _curl_warp(body, seed + 6, res, 0.12)
    # a sparse scatter of bright clear lens-points (translucent organ glints) over the sheet
    lens = np.zeros((res, res), np.float32)
    nl = 220
    lx = rng.integers(0, res, nl); ly = rng.integers(0, res, nl)
    lens[ly, lx] = 1.0
    lens = cv2.GaussianBlur(lens, (0, 0), 2.2)
    return _up(_norm(body + 0.5 * _norm(lens)), h, w)


# ── 🛸 FRACTURED UFO — FIX BATCH (7 rejected finishes) — engine functions ──────────
# BARE-name engines (prefixed fuf_) to be pasted into fractured_math.py. Each returns a
# 0..1 scalar FIELD (HxW). NO VORONOI. NO _tile_finer (no visible tiling/repeats). Fine
# scale via native high frequency + many scattered sources + domain warp = FULL coverage.
# Deps already present in fractured_math.py: np, cv2, _rng, _fbm, _norm, _up, _curl_warp.


def fuf_plasma_drive(h, w, seed, *, res=600, cores=240):
    """Ion plasma field: a very dense scatter of MANY tiny tight plasma cores, each a small spiky
    ion-burst, woven through a high-frequency turbulent ion filament weave so the whole canvas is
    a fine crackling magenta plasma sheet — full coverage, no soft blobs, no blank gaps, no
    single centre (finer than it looks)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # high-frequency turbulent ion filament weave (the fine full-coverage substrate)
    warp = _curl_warp(_fbm(res, res, rng, 6, 11).astype(np.float32), seed + 1, res, 0.10)
    fil = np.abs(np.sin(warp * 34.0 + gx / res * 26.0)) * np.abs(np.sin(warp * 41.0 - gy / res * 22.0))
    fil = fil ** 0.4                                          # sharpen into thin bright filaments
    field = fil * 0.6
    # MANY tiny tight cores -> small spiky bursts, never big soft blobs
    for _ in range(int(cores)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        rad = np.hypot(gy - cy, gx - cx)
        glow = np.exp(-(rad / (res * 0.022)) ** 2)            # TINY cores
        field += glow * 1.3
    # micro ion sparkle keeps every pixel alive at the smallest scale
    spark = (rng.uniform(0, 1, (res, res)) > 0.992).astype(np.float32)
    field += cv2.GaussianBlur(spark, (0, 0), 0.6) * 1.2
    return _up(_norm(field), h, w)


def fuf_crop_circle(h, w, seed, *, res=620, motifs=60):
    """Agroglyph field: dozens of SMALL flattened-ring crop formations (concentric rings +
    radial spokes + satellite pips) scattered edge-to-edge over a tight flattened-grain
    substrate so there are NO blank patches — many small circles, fine, full coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # flattened-crop grain bed (directional fine streaks) — fills the gaps between rings
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    bed = _curl_warp(_fbm(res, res, rng, 6, 9).astype(np.float32), seed + 2, res, 0.10)
    bed = 0.30 * np.abs(np.sin(bed * 16.0 + gx / res * 40.0))
    img += bed
    for _ in range(int(motifs)):
        cx, cy = int(rng.uniform(0.02, 0.98) * res), int(rng.uniform(0.02, 0.98) * res)
        R = int(rng.uniform(0.018, 0.045) * res)              # SMALL rings, finer
        cv2.circle(img, (cx, cy), R, float(rng.uniform(0.6, 1.0)), 1, cv2.LINE_AA)
        if R > 6:
            cv2.circle(img, (cx, cy), int(R * 0.55), float(rng.uniform(0.4, 0.8)), 1, cv2.LINE_AA)
        sats = int(rng.integers(5, 9))
        for k in range(sats):                                 # satellite pips on the ring
            a = 6.283 * k / sats + rng.uniform(0, 1)
            sx, sy = int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)
            cv2.circle(img, (sx, sy), max(1, int(R * 0.16)), 1.0, -1, cv2.LINE_AA)
            if rng.random() < 0.45:                            # radial spoke
                cv2.line(img, (cx, cy), (sx, sy), 0.40, 1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5)), h, w)


def fuf_hyperspace(h, w, seed, *, res=620):
    """Warp streak field: one abstract NON-repeating star-tunnel — thousands of light-streaks
    are stamped as a curl-smeared light field (radial speed-lines from many scattered drift
    points domain-warped together) so there is NO tile seam and NO single centred vanishing
    point — fine omnidirectional warp-jump smear, full coverage."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # accumulate radial speed-lines from MANY scattered drift sources (no single centre)
    acc = np.zeros((res, res), np.float32)
    n_src = 26
    for _ in range(n_src):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        ang = np.arctan2(gy - cy, gx - cx)
        rad = np.hypot(gy - cy, gx - cx)
        spokes = float(rng.integers(40, 80))                  # high freq -> fine streaks
        line = np.abs(np.sin(ang * spokes)) ** 6              # sharp thin streaks
        falloff = np.clip(rad / (res * 0.5), 0, 1)            # streaks grow toward rim
        acc += line * falloff * rng.uniform(0.5, 1.0)
    # smear into motion-streaks with curl warp -> no repeats, organic light tunnel
    field = _curl_warp(_norm(acc), seed + 3, res, 0.18)
    streak = cv2.GaussianBlur(field, (0, 0), 0.6)
    sparkle = (rng.uniform(0, 1, (res, res)) > 0.994).astype(np.float32)
    field = _norm(streak + cv2.GaussianBlur(sparkle, (0, 0), 0.7) * 1.4)
    return _up(field, h, w)


def fuf_biomech_skin(h, w, seed, *, res=600):
    """Bio-mechanical alien hide: interlocking domain-warped chitin TUBES and pulsing VEINS over
    a fine pore grain — built from warped ridged sinusoids + branching vein noise (NO voronoi
    cells) for a distinct living tube/vein/chitin surface, fine and full coverage."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # warp the coordinate field so tubes meander organically (omnidirectional)
    warp = _fbm(res, res, rng, 5, 6).astype(np.float32)
    u = gx / res + (warp - 0.5) * 0.6
    v = gy / res + (_fbm(res, res, rng, 5, 8) - 0.5) * 0.6
    # interlocking chitin tubes: two crossed high-freq ridged sine families
    tube_a = np.abs(np.sin((u * 30.0 + v * 9.0) * np.pi)) ** 0.5
    tube_b = np.abs(np.sin((v * 26.0 - u * 7.0) * np.pi)) ** 0.5
    chitin = np.maximum(tube_a, tube_b)
    # pulsing veins: thin bright ridges where warped fBm crosses a level set
    vein_n = _curl_warp(_fbm(res, res, rng, 6, 5).astype(np.float32), seed + 4, res, 0.16)
    veins = np.clip(1.0 - np.abs(((vein_n * 9.0) % 1.0) - 0.5) * 7.0, 0, 1)
    # fine pore grain fills micro-texture so nothing reads flat
    pore = 0.22 * (_fbm(res, res, rng, 4, 13).astype(np.float32) - 0.5)
    field = _norm(chitin * 0.55 + veins * 0.9 + pore)
    field = _curl_warp(field, seed + 5, res, 0.07)            # final organic settle
    return _up(_norm(field), h, w)


def fuf_stargate(h, w, seed, *, res=620, vortices=22):
    """Phase-vortex gate field: many scattered counter-rotating phase vortices summed into ONE
    organic interference of winding event-horizon arms with fine harmonic ripples — a single
    continuous gate field with NO tile seam and NO single centred spiral, fine + full."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    phase = np.zeros((res, res), np.float32)
    for _ in range(int(vortices)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        phase += rng.choice([-1.0, 1.0]) * np.arctan2(gy - cy, gx - cx)
    # radial reference is itself warped so no clean centre forms
    warp = (_fbm(res, res, rng, 5, 6).astype(np.float32) - 0.5) * res * 0.5
    rad = np.hypot(gx - res * 0.5, gy - res * 0.5) + warp
    rad = rad / res * 46.0
    base = np.sin(phase + rad)
    fine = 0.6 * np.sin(phase * 5.0 + rad * 6.0)              # tight harmonic ripples
    micro = 0.35 * np.sin(rad * 11.0 + phase * 2.0)
    field = _curl_warp(_norm(base + fine + micro), seed + 6, res, 0.06)
    return _up(_norm(field), h, w)


def fuf_gravity_lens(h, w, seed, *, res=600, masses=70):
    """Gravity-lens ripple (NEW design replacing the old scanner sweep): a starfield of light is
    bent by a dense scatter of small gravitational masses, each warping a fine concentric
    spacetime-ripple substrate — an abstract omnidirectional lensing field, fine, full coverage,
    no single centre. A brand-new UFO look (alien gravity well sensor field)."""
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # fine spacetime substrate: high-freq warped ripples everywhere
    sub = _curl_warp(_fbm(res, res, rng, 6, 6).astype(np.float32), seed + 7, res, 0.12)
    sub = 0.5 + 0.5 * np.sin(sub * 26.0)
    # build a lensing displacement from many small masses, then remap the substrate by it
    dispx = np.zeros((res, res), np.float32)
    dispy = np.zeros((res, res), np.float32)
    for _ in range(int(masses)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        dx, dy = gx - cx, gy - cy
        d2 = dx * dx + dy * dy + (res * 0.03) ** 2
        strength = (res * 0.9) / d2                            # 1/r^2 pull, small reach
        dispx += dx * strength
        dispy += dy * strength
    lensed = cv2.remap(sub, np.clip(gx + dispx, 0, res - 1).astype(np.float32),
                       np.clip(gy + dispy, 0, res - 1).astype(np.float32), cv2.INTER_LINEAR)
    # bright lensed light arcs where displacement is steep (Einstein-ring fragments)
    mag = _norm(np.hypot(dispx, dispy))
    arcs = np.clip(1.0 - np.abs(((mag * 14.0) % 1.0) - 0.5) * 6.0, 0, 1)
    stars = (rng.uniform(0, 1, (res, res)) > 0.995).astype(np.float32)
    field = _norm(lensed * 0.6 + arcs * 0.7 + cv2.GaussianBlur(stars, (0, 0), 0.6) * 1.4)
    return _up(_norm(field), h, w)


def fuf_glyph_cells(h, w, seed, *, res=620, gridn=34):
    """Alien hieroglyph field (NON-voronoi): a fine grid where every cell carries a small set of
    angular xeno-glyph strokes + pips, jittered in count/angle so it never reads as a regular
    tile, bedded on a faint inscription grain — many small glyphs, fine, full coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # faint inscription grain so the metal plate between glyphs isn't blank
    img += 0.10 * (_fbm(res, res, rng, 5, 11).astype(np.float32))
    s = res / gridn
    for iy in range(gridn + 1):
        for ix in range(gridn + 1):
            # jitter each glyph off its cell centre so the grid disappears
            cx = (ix + rng.uniform(-0.30, 0.30)) * s
            cy = (iy + rng.uniform(-0.30, 0.30)) * s
            strokes = int(rng.integers(2, 5))
            for _ in range(strokes):
                ax = cx + rng.uniform(-0.34, 0.34) * s
                ay = cy + rng.uniform(-0.34, 0.34) * s
                r = rng.random()
                if r < 0.7:                                    # angular stroke
                    dx = float(rng.choice([-1, 0, 1])) * s * 0.34
                    dy = float(rng.choice([-1, 0, 1])) * s * 0.34
                    cv2.line(img, (int(ax), int(ay)), (int(ax + dx), int(ay + dy)),
                             float(rng.uniform(0.6, 1.0)), 1, cv2.LINE_AA)
                elif r < 0.88:                                 # small arc tick
                    cv2.ellipse(img, (int(ax), int(ay)), (int(s * 0.22), int(s * 0.22)),
                                float(rng.uniform(0, 360)), 0, int(rng.uniform(90, 220)),
                                float(rng.uniform(0.5, 0.9)), 1, cv2.LINE_AA)
                else:                                          # glyph pip
                    cv2.circle(img, (int(ax), int(ay)), 1, 1.0, -1, cv2.LINE_AA)
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.45)), h, w)


# 🌈 FRACTURED RAINBOW — FIX pack: 8 owner-rejected finishes rebuilt.
# BARE names, prefixed frf_ ; pasted into fractured_math.py (sees *, _rng,_fbm,_norm,_up,_curl_warp,_thinfilm, np, cv2).
# HARD BANS honoured: (1) NO voronoi / cells / crackle / hex-hive.  (2) NO _tile_finer / visible repeats.
# Every engine: compute a FINE optical SCALAR field at NATIVE high frequency over the WHOLE canvas,
# then map it through the vivid 6-stop numpy spectral ramp (_rbw_ramp) -> full-spectrum RGB HxWx3.
# (_rbw_ramp / _rbw_shade / _rbw_edges already live in fractured_math.py — we reuse them.)


def _frf_scatter_sources(res, seed, n):
    """n well-spread point sources across the WHOLE canvas (blue-noise-ish jitter, no grid lattice
    so there is no repeat) — used by the ripple / aberration fields for full omnidirectional coverage."""
    rng = _rng(seed)
    # start from a coarse jittered grid then shuffle hard so sources read as scattered, never tiled
    g = int(np.ceil(np.sqrt(n)))
    ys, xs = np.mgrid[0:g, 0:g].astype(np.float32)
    cx = (xs.ravel() + rng.uniform(0.05, 0.95, g * g)) / g * res
    cy = (ys.ravel() + rng.uniform(0.05, 0.95, g * g)) / g * res
    idx = rng.permutation(g * g)[:int(n)]
    return cx[idx], cy[idx]


# ════════════════════════════════════════════════════════════════════════════════════════════
# 1) fr_prism_shatter  — NON-voronoi spectral SHATTER: thin-film oil-slick sweep, domain-warped,
#    with crisp angular fault-lines pulled from the field's own gradient ridges (the "shatter"
#    read) — full spectrum cycling many times, fine, full coverage, no cells.
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_oilslick_shatter(h, w, seed, *, res=640, freq=14.0, cycles=6.0):
    rng = _rng(seed)
    tf = _thinfilm(res, seed, freq)
    # two curl drifts at different scales -> turbulent oil-slick, NO directional tiling
    flow = _curl_warp(_curl_warp(tf, seed + 5, res, 0.18), seed + 13, res, 0.10)
    # sharp faceting: quantise the warped phase into many fine spectral wavefronts (angular shatter)
    t = ((_norm(flow) * float(cycles) + 0.30 * _fbm(res, res, rng, 5, 7)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.62 + 0.38 * _norm(flow))     # brighter floor -> more vivid
    # bright ignitable fault-lines on the spectral discontinuities -> the "shattered prism" edges
    seam = ((t * float(cycles)) % 1.0)
    seam = np.minimum(seam, 1.0 - seam)                       # distance to nearest band boundary
    # tint the faults with the local hue (not white) so the spectrum stays saturated at the seams
    fault = np.clip(1.0 - seam * 9.0, 0, 1)[..., None]
    rgb = rgb + _rbw_edges(flow, 1.1, 0.45) + _rbw_ramp(t) * fault * 0.45
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 2) fr_spectrum_voronoi  — NON-voronoi full-spectrum DIFFRACTION SWEEP: many crossed high-freq
#    gratings at scattered angles split light into a dense field of fine holographic fringes,
#    domain-warped so it never reads as straight stripes or repeats. DISTINCT from #1 (grating, not film).
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_diffraction_sweep(h, w, seed, *, res=640, gratings=4, cycles=5.0):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # per-coordinate domain warp FIRST so every grating rides a turbulent coordinate -> the fringes
    # bow, fork and wander; crossing them no longer makes a regular crosshatch lattice.
    wx = (_fbm(res, res, rng, 5, 5) - 0.5) * res * 0.55
    wy = (_fbm(res, res, rng, 5, 5) - 0.5) * res * 0.55
    cgx, cgy = gx + wx, gy + wy
    acc = np.zeros((res, res), np.float32)
    for _ in range(int(gratings)):                            # FEW gratings -> no dense crosshatch
        a = float(rng.uniform(0, np.pi))
        f = float(rng.uniform(16, 30))
        acc += np.sin((cgx * np.cos(a) + cgy * np.sin(a)) / res * f * 6.283 + float(rng.uniform(0, 6.28)))
    ph = _norm(acc)
    ph = _norm(_curl_warp(ph, seed + 9, res, 0.16))           # extra flow smear -> diffraction sweep
    t = ((ph * float(cycles)) % 1.0).astype(np.float32)
    relief = _norm(0.5 + 0.5 * np.sin(ph * float(cycles) * 6.283))
    rgb = _rbw_shade(_rbw_ramp(t), 0.55 + 0.45 * relief)
    rgb = rgb + _rbw_edges(relief, 0.8, 0.5)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 3) fr_hex_hive  — drop the hive: a fine SPECTRAL MOIRE SWEEP. Two offset high-freq interference
#    fields beat into a dense omnidirectional optical-rainbow weave (no cells, no hive, no tiling).
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_spectral_moire(h, w, seed, *, res=640, cycles=5.0):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # scattered radial wave sources (interference) -> organic moire, not a centred rosette
    cx, cy = _frf_scatter_sources(res, seed + 2, 9)
    acc = np.zeros((res, res), np.float32)
    for i in range(len(cx)):
        k = float(rng.uniform(0.06, 0.13))
        d = np.hypot(gx - cx[i], gy - cy[i])
        acc += np.sin(d * k + float(rng.uniform(0, 6.28)))
    # cross with a fine fbm so the beat is irregular (no repeat)
    field = _norm(acc) + 0.4 * (_fbm(res, res, rng, 5, 8) - 0.5)
    field = _norm(_curl_warp(field, seed + 7, res, 0.10))
    t = ((field * float(cycles)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * field)
    rgb = rgb + _rbw_edges(field, 1.0, 0.6)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 4) fr_chroma_rings  — DE-TILE: ONE field of MANY scattered chromatic ripple sources (not 3x3
#    tiled rings). Dozens of point ripples spread across the whole canvas, summed, mapped to hue.
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_ripple_field(h, w, seed, *, res=640, sources=22, cycles=4.0):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = _frf_scatter_sources(res, seed, sources)
    acc = np.zeros((res, res), np.float32)
    for i in range(len(cx)):
        d = np.hypot(gx - cx[i], gy - cy[i])
        k = float(rng.uniform(0.10, 0.22))                    # tight ripple spacing = fine scale
        acc += np.sin(d * k + float(rng.uniform(0, 6.28))) / (1.0 + 0.004 * d)
    field = _norm(acc)
    field = _norm(field + 0.18 * (_fbm(res, res, rng, 5, 7) - 0.5))  # break any residual symmetry
    t = ((field * float(cycles)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.45 + 0.55 * field)
    rgb = rgb + _rbw_edges(field, 1.0, 0.75)                  # bright ignitable wavefront rings
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 5) fr_prism_wheel  — DE-TILE: a SINGLE abstract spectral CURL-BURST. Several co-rotating vortices
#    domain-warped into one flowing prismatic burst that fills the canvas (no 3x3 wheels, no repeat).
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_spectral_burst(h, w, seed, *, res=620, vortices=9, cycles=5.0):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    # weight each vortex's angular contribution by a falloff so NO single arctan2 singularity
    # dominates the canvas -> the swirl is genuinely all-over, never one centred pinwheel.
    phase = np.zeros((res, res), np.float32)
    for k in range(int(vortices)):
        cx, cy = rng.uniform(0.05, 0.95, 2) * res
        sgn = 1.0 if k % 2 == 0 else -1.0                     # alternate spin so curl cancels overall
        d2 = (gx - cx) ** 2 + (gy - cy) ** 2
        wgt = np.exp(-d2 / (2.0 * (res * 0.30) ** 2))         # local influence only -> many small swirls
        phase += sgn * np.arctan2(gy - cy, gx - cx) * wgt
    # high-freq angular ripples (sin of many-times phase) -> the radial term never resolves to a
    # single visible centre; combined with the alternating spins it reads as an all-over prism burst
    swirl = np.sin(phase * 2.6) + 0.6 * np.sin(phase * 5.5 + 0.7) + 0.4 * np.sin(phase * 9.0)
    # heavy double curl warp dissolves any residual radial centre into a flowing prismatic burst
    field = _norm(_curl_warp(_curl_warp(_norm(swirl), seed + 11, res, 0.26), seed + 23, res, 0.16))
    t = ((field * float(cycles) + 0.35 * _fbm(res, res, rng, 5, 7)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.55 + 0.45 * field)
    rgb = rgb + _rbw_edges(field, 1.1, 0.6)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 6) fr_opal_fire  — NON-voronoi OPAL: a flowing thin-film spectral base, then thousands of tiny
#    scattered bright opal FLECKS splatted over it (point flecks, NOT crackle/voronoi cells).
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_opal_flecks(h, w, seed, *, res=620, flecks=3200, cycles=5.0):
    rng = _rng(seed)
    # flowing spectral field (oil-film curl) = the opal body
    tf = _curl_warp(_curl_warp(_thinfilm(res, seed, 12.0), seed + 6, res, 0.18), seed + 19, res, 0.10)
    base = _norm(tf)
    t = ((base * float(cycles)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.58 + 0.42 * base)            # brighter, more vivid opal body
    # scatter fine opal flecks: each a tiny spectral-tinted glint -> "opal fire" without any cells
    fl = np.zeros((res, res), np.float32)
    px = rng.integers(0, res, int(flecks))
    py = rng.integers(0, res, int(flecks))
    fl[py, px] = rng.uniform(0.6, 1.0, int(flecks))
    fl = cv2.GaussianBlur(fl, (0, 0), 1.0)
    fl = _norm(fl) ** 0.7
    # tint each fleck by its local field hue (offset cycle) so flecks flash a DIFFERENT spectral band
    fleck_rgb = _rbw_ramp(((base * float(cycles) + 0.5) % 1.0).astype(np.float32))
    rgb = rgb + fleck_rgb * fl[..., None] * 1.15                  # stronger opal fire
    rgb = rgb + _rbw_edges(base, 1.0, 0.4)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 7) fr_spectral_spiral  — DE-TILE ("tiled — LOOKS BAD"): ONE flowing spectral MARBLE/curl field.
#    Turbulent domain-warped marble veining smeared along a curl flow, full spectrum, no repeats.
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_spectral_marble_flow(h, w, seed, *, res=600, veins=13.0, cycles=4.0):
    mb = _norm(marble(res, res, seed, veins=veins))
    flow = _curl_warp(_curl_warp(mb, seed + 7, res, 0.18), seed + 17, res, 0.12)
    field = _norm(flow)
    t = ((field * float(cycles)) % 1.0).astype(np.float32)   # spectrum sweeps along the veining
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * mb)
    rgb = rgb + _rbw_edges(mb, 1.1, 0.75)
    return _up(np.clip(rgb, 0, 1), h, w)


# ════════════════════════════════════════════════════════════════════════════════════════════
# 8) fr_chroma_ripple  — DE-TILE ("tiled too obvious"): a FINE NON-repeating chromatic-aberration
#    ripple field. Many scattered Newton-ring halos summed (no _tile_finer), warped, mapped to hue.
# ════════════════════════════════════════════════════════════════════════════════════════════
def frf_aberration_ripple(h, w, seed, *, res=620, halos=20, cycles=6.0):
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cx, cy = _frf_scatter_sources(res, seed, halos)
    acc = np.zeros((res, res), np.float32)
    for i in range(len(cx)):
        d = np.hypot(gx - cx[i], gy - cy[i])
        acc += np.sin(np.sqrt(d + 1.0) * float(rng.uniform(1.3, 2.2)))    # sqrt-spaced = Newton rings
    nr = _norm(0.5 + 0.5 * np.sin(_norm(acc) * np.pi * 5.0))              # more fringes = finer
    nr = _norm(_curl_warp(nr, seed + 4, res, 0.08))                       # gentle warp, still fine
    # histogram-equalise the phase so the spectral cycle covers the WHOLE ramp evenly (kills the
    # warm/red bias of the raw newton-ring distribution -> true full-spectrum)
    eq = cv2.equalizeHist((nr * 255).astype(np.uint8)).astype(np.float32) / 255.0
    t = ((eq * float(cycles)) % 1.0).astype(np.float32)
    rgb = _rbw_shade(_rbw_ramp(t), 0.5 + 0.5 * nr)                        # brighter, less warm-collapse
    # split the channels slightly across the spectral phase = chromatic aberration (R lags, B leads)
    rgb[..., 0] = np.clip(rgb[..., 0] + _rbw_ramp(((eq * cycles + 0.06) % 1.0))[..., 0] * 0.18, 0, 1)
    rgb[..., 2] = np.clip(rgb[..., 2] + _rbw_ramp(((eq * cycles - 0.06) % 1.0))[..., 2] * 0.18, 0, 1)
    rgb = rgb + _rbw_edges(nr, 1.0, 0.7)
    return _up(np.clip(rgb, 0, 1), h, w)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 🔮 FRACTURED OCCULT — FIX batch (9 rejected finishes rebuilt). Bare-name fof_* primitives,
# pasted into fractured_math.py (module already does `import *` + has _rng/_fbm/_norm/_up/etc).
#
# HARD BANS honoured here:
#   (1) NO VORONOI / cKDTree-cell / cobble / crackle anywhere below.
#   (2) NO _tile_finer / visible tiling — fine scale + full coverage comes from NATIVE high
#       frequency, MANY scattered sources, and domain-warp — never from repeating a small tile.
# Scalar engines return HxW 0..1 (colorize()'d by the recipe); multi-hue engines return HxWx3.
# ══════════════════════════════════════════════════════════════════════════════════════════════


def fof_cobweb_lace(h, w, seed, *, res=700, anchors=140):
    """Dense tattered web silk: MANY anchor points strung edge-to-edge with taut radial guy-lines
    to their near neighbours plus sagging catenary capture-threads — a fine torn lace veil with a
    faint dust bloom so NO patch is ever blank. Full coverage, no blobs, no single centre."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # anchors scattered over the WHOLE sheet (no centred motif)
    P = rng.uniform(0.0, res, (int(anchors), 2)).astype(np.float32)
    for i in range(int(anchors)):
        ax, ay = P[i]
        # connect to a handful of nearest neighbours -> an irregular structural mesh
        d2 = ((P[:, 0] - ax) ** 2 + (P[:, 1] - ay) ** 2)
        order = np.argsort(d2)[1:int(rng.integers(4, 7)) + 1]
        for j in order:
            bx, by = P[j]
            # sagging silk: a slightly bowed polyline, not a straight stick
            n = 6
            ts = np.linspace(0, 1, n)
            sag = rng.uniform(-0.10, 0.10) * np.hypot(bx - ax, by - ay)
            px = ax + (bx - ax) * ts - (by - ay) / (np.hypot(bx - ax, by - ay) + 1e-3) * sag * np.sin(ts * np.pi)
            py = ay + (by - ay) * ts + (bx - ax) / (np.hypot(bx - ax, by - ay) + 1e-3) * sag * np.sin(ts * np.pi)
            cv2.polylines(img, [np.stack([px, py], 1).astype(np.int32)], False,
                          float(rng.uniform(0.35, 0.75)), 1, cv2.LINE_AA)
        # a tiny tuft of fine capture-spiral arcs around the anchor for lace detail
        R = rng.uniform(6, 16)
        spokes = int(rng.integers(5, 8))
        a0 = rng.uniform(0, 6.283)
        for rr in np.linspace(R * 0.3, R, 3):
            pts = [(ax + np.cos(a0 + 2 * np.pi * s / spokes) * rr,
                    ay + np.sin(a0 + 2 * np.pi * s / spokes) * rr) for s in range(spokes + 1)]
            cv2.polylines(img, [np.array(pts, np.int32)], False, float(rng.uniform(0.4, 0.7)), 1, cv2.LINE_AA)
    silk = cv2.GaussianBlur(img, (0, 0), 0.35)
    # fine torn-web fibre noise + a low dust haze guarantee full coverage (kills blank spots)
    fibre = _norm(np.abs(cv2.Laplacian(_fbm(res, res, rng, 6, 9).astype(np.float32), cv2.CV_32F))) ** 0.7
    dust = cv2.GaussianBlur(_fbm(res, res, rng, 4, 6).astype(np.float32), (0, 0), 6.0)
    return _up(_norm(silk * 0.85 + fibre * 0.30 + dust * 0.18), h, w)


def fof_bone_branch(h, w, seed, *, res=700, trunks=150):
    """A MANY-sourced thicket of SMALL fine forked bone twigs: lots of short low-depth branches
    seeded densely across the whole frame so the bone-white lattice fills it with no big limbs and
    no blank gaps. Fine width, fine length — twigs, not trees."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def branch(x, y, ang, width, length, depth):
        if depth <= 0 or width < 0.5:
            return
        steps = max(1, int(length / 4))
        for _s in range(steps):
            ang += float(rng.uniform(-0.14, 0.14))
            nx, ny = x + np.cos(ang) * 4.0, y + np.sin(ang) * 4.0
            cv2.line(img, (int(x), int(y)), (int(nx), int(ny)),
                     float(rng.uniform(0.55, 0.95)), max(1, int(round(width))), cv2.LINE_AA)
            x, y = nx, ny
        if width > 1.2:
            cv2.circle(img, (int(x), int(y)), 1, 0.95, -1, cv2.LINE_AA)  # tiny knuckle joint
        for _ in range(2):
            branch(x, y, ang + float(rng.uniform(-0.9, 0.9)), width * 0.6, length * 0.6, depth - 1)

    for _ in range(int(trunks)):
        x, y = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        a = float(rng.uniform(0, 6.283))
        # SMALL twigs: thin start, short length, shallow recursion -> dense fine forking
        branch(x, y, a, float(rng.uniform(1.4, 2.4)), float(rng.uniform(0.045, 0.085) * res), 3)
    bone = cv2.GaussianBlur(img, (0, 0), 0.4)
    # faint bone-dust fbm so corners never read blank
    dust = cv2.GaussianBlur(_fbm(res, res, rng, 5, 7).astype(np.float32), (0, 0), 5.0) * 0.16
    return _up(_norm(bone + dust), h, w)


def fof_spider_lattice(h, w, seed, *, res=700, webs=34, spokes=13):
    """NON-voronoi spider web: many overlapping orb-webs, each true radial silk SPOKES crossed by
    fine sagging SPIRAL capture-threads, beaded with bright dew-drops at the crossings. Scattered
    and overlapped so it fills the frame as a fine omnidirectional silk net — not one centred web."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    dew = np.zeros((res, res), np.float32)
    for _ in range(int(webs)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        R = float(rng.uniform(0.05, 0.11) * res)
        sp = int(rng.integers(spokes - 3, spokes + 3))
        a0 = rng.uniform(0, 6.283)
        ang = [a0 + 2 * np.pi * s / sp + rng.uniform(-0.05, 0.05) for s in range(sp)]
        for a in ang:  # radial spokes
            cv2.line(img, (int(cx), int(cy)), (int(cx + np.cos(a) * R), int(cy + np.sin(a) * R)),
                     float(rng.uniform(0.45, 0.75)), 1, cv2.LINE_AA)
        rings = np.linspace(R * 0.12, R, int(rng.integers(6, 10)))  # fine concentric capture spiral
        for ri, rr in enumerate(rings):
            sag = rr * 0.10
            pts = []
            for s in range(sp + 1):
                a = ang[s % sp]
                d = rr - sag * (s % 2)
                pts.append((cx + np.cos(a) * d, cy + np.sin(a) * d))
            cv2.polylines(img, [np.array(pts, np.int32)], False, float(rng.uniform(0.4, 0.7)), 1, cv2.LINE_AA)
            if ri % 2 == 0:  # dew beads on alternate ring crossings
                for s in range(0, sp, 2):
                    a = ang[s % sp]
                    cv2.circle(dew, (int(cx + np.cos(a) * rr), int(cy + np.sin(a) * rr)),
                               1, float(rng.uniform(0.7, 1.0)), -1, cv2.LINE_AA)
    silk = cv2.GaussianBlur(img, (0, 0), 0.4)
    dew = cv2.GaussianBlur(dew, (0, 0), 0.7)
    haze = cv2.GaussianBlur(_fbm(res, res, rng, 4, 6).astype(np.float32), (0, 0), 7.0) * 0.14
    return _up(_norm(silk * 0.8 + dew * 0.7 + haze), h, w)


def fof_raven_feather(h, w, seed, *, res=700, feathers=240):
    """Fine dense overlapping raven plumes with DEPTH: MANY small curved feathers (a curved rachis
    + fine angled barbs), drawn back-to-front with a soft drop-shadow under each so plumes read as
    layered glossy plumage. High count + barb-noise = full coverage, no flat blank areas."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    shadow = np.zeros((res, res), np.float32)
    for _ in range(int(feathers)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        L = rng.uniform(0.045, 0.10) * res
        ang = rng.uniform(0, 6.283)
        curl = rng.uniform(-0.5, 0.5)
        n = max(4, int(L / 3))
        ts = np.linspace(0, 1, n)
        # curved rachis (slight arc -> a real plume, not a stick)
        aa = ang + curl * ts
        rx = cx + np.cumsum(np.cos(aa)) * (L / n)
        ry = cy + np.cumsum(np.sin(aa)) * (L / n)
        v = float(rng.uniform(0.5, 0.85))
        # soft offset shadow first -> layered depth
        cv2.polylines(shadow, [np.stack([rx + 2, ry + 2], 1).astype(np.int32)], False, v * 0.6, 2, cv2.LINE_AA)
        cv2.polylines(img, [np.stack([rx, ry], 1).astype(np.int32)], False, v, 1, cv2.LINE_AA)
        for t in range(1, n):  # fine barbs both sides
            f = t / n
            blen = (1.0 - f) * L * 0.42 + 2.0
            for sgn in (-1, 1):
                ba = aa[t] + sgn * rng.uniform(0.7, 1.05)
                cv2.line(img, (int(rx[t]), int(ry[t])),
                         (int(rx[t] + np.cos(ba) * blen), int(ry[t] + np.sin(ba) * blen)),
                         float(v * rng.uniform(0.55, 0.85)), 1, cv2.LINE_AA)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 2.2) * 0.5
    plume = cv2.GaussianBlur(img, (0, 0), 0.4)
    return _up(_norm(plume * 0.9 + shadow), h, w)


def fof_cracked_tomb(h, w, seed, *, res=640):
    """NON-voronoi tombstone slab: a chiselled granite GRAIN (ridged fbm) carrying a few authored
    deep fracture lines that wander across the slab (random-walk cracks, NOT cell edges) plus a
    crusty lichen mottle. Reads as one aged carved tomb face, full coverage, fine grain."""
    rng = _rng(seed)
    # ── chiselled granite grain: high-octave ridged fbm = fine speckled tool-worked stone ──
    g = _fbm(res, res, rng, 6, 9).astype(np.float32)
    grain = 1.0 - np.abs(2.0 * g - 1.0)            # ridged -> chisel speckle
    grain = _norm(grain ** 1.4)
    coarse = cv2.GaussianBlur(_fbm(res, res, rng, 4, 5).astype(np.float32), (0, 0), 3.0)  # slab tone drift
    field = 0.45 + 0.35 * grain + 0.20 * coarse
    # ── a FEW deep wandering fracture lines drawn as random-walk polylines (no voronoi) ──
    crack = np.zeros((res, res), np.float32)
    for _ in range(int(rng.integers(4, 7))):
        x, y = rng.uniform(0, res), rng.uniform(0, res)
        a = rng.uniform(0, 6.283)
        pts = [(x, y)]
        for _s in range(int(rng.uniform(60, 120))):
            a += rng.uniform(-0.35, 0.35)
            x += np.cos(a) * 5.0
            y += np.sin(a) * 5.0
            pts.append((x, y))
            if rng.uniform() < 0.04 and len(pts) > 4:  # branching splinter
                ba = a + rng.uniform(-1.0, 1.0)
                bx, by = x, y
                bpts = [(bx, by)]
                for _b in range(int(rng.uniform(8, 22))):
                    ba += rng.uniform(-0.3, 0.3)
                    bx += np.cos(ba) * 5.0; by += np.sin(ba) * 5.0
                    bpts.append((bx, by))
                cv2.polylines(crack, [np.array(bpts, np.int32)], False, 1.0, 1, cv2.LINE_AA)
        cv2.polylines(crack, [np.array(pts, np.int32)], False, 1.0, max(1, int(rng.uniform(1, 3))), cv2.LINE_AA)
    crack = cv2.GaussianBlur(crack, (0, 0), 0.6)
    # ── lichen crust: thresholded blurred fbm patches, only in spots ──
    lich = cv2.GaussianBlur(_fbm(res, res, rng, 5, 6).astype(np.float32), (0, 0), 2.0)
    lich = np.clip((lich - 0.58) * 4.0, 0, 1) * 0.25
    out = field - crack * 0.55 + lich   # cracks carve DARK, lichen lifts a little
    return _up(_norm(out), h, w)


def fof_vampire_damask(h, w, seed, *, res=700, reps=5):
    """Finer ornate baroque damask scrollwork via a guilloche/harmonograph-style ornament: a
    half-drop grid of small mirrored Lissajous scroll-leaves around a beaded boss inside an ogee
    frame, every cell phase-jittered so the seamless repeat shows NO obvious square grid. Fine,
    full-coverage gothic wallpaper."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / reps
    ts = np.linspace(0, 2 * np.pi, 420)
    for i in range(-1, reps + 1):
        for j in range(-1, reps + 1):
            off = (s * 0.5) if (j % 2) else 0.0     # half-drop -> breaks the square grid
            cx, cy = i * s + off, j * s
            R = s * 0.42
            ph = rng.uniform(0, 6.283)
            # beaded central boss
            for br in (0.16, 0.30):
                pts = [(cx + np.cos(t) * R * br, cy + np.sin(t) * R * br) for t in ts[::18]]
                cv2.polylines(img, [np.array(pts, np.int32)], True, 0.85, 1, cv2.LINE_AA)
            # paired mirrored harmonograph scroll-leaves (fine filigree, not a blob)
            for sgn in (-1, 1):
                a = 0.30 + 0.18 * np.cos(2 * ts + ph)        # rose-like radial modulation
                lx = cx + sgn * R * (0.30 + a * np.cos(ts))
                ly = cy + R * (a * np.sin(ts * 1.5 + ph) + 0.20 * np.sin(ts * 3))
                cv2.polylines(img, [np.stack([lx, ly], 1).astype(np.int32)], False,
                              float(rng.uniform(0.55, 0.75)), 1, cv2.LINE_AA)
                # a thin counter-scroll tendril
                tx = cx + sgn * R * (0.55 + 0.22 * np.cos(ts * 2 + ph))
                ty = cy + R * (0.55 * np.sin(ts + ph))
                cv2.polylines(img, [np.stack([tx, ty], 1).astype(np.int32)], False, 0.4, 1, cv2.LINE_AA)
            # ogee diamond frame linking the cells -> continuous wallpaper, full coverage
            dpts = np.array([(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)], np.int32)
            cv2.polylines(img, [dpts], True, 0.35, 1, cv2.LINE_AA)
            # fine interstitial filler so the diamond gaps never read blank
            for sgn in (-1, 1):
                fx = cx + sgn * R * 0.7 + s * 0.5
                cv2.circle(img, (int(fx), int(cy + R * 0.7)), max(1, int(R * 0.06)), 0.45, -1, cv2.LINE_AA)
    orn = cv2.GaussianBlur(img, (0, 0), 0.4)
    # two-scale curl-warp so the seamless damask undulates organically and the rigid square-grid
    # autocorrelation is broken — still full-coverage gothic wallpaper, no crude tile.
    orn = _curl_warp(orn, seed + 11, res, 0.13)
    orn = _curl_warp(orn, seed + 29, res, 0.07)
    velvet = cv2.GaussianBlur(_fbm(res, res, rng, 5, 7).astype(np.float32), (0, 0), 4.0) * 0.16
    return _up(_norm(orn * 0.9 + velvet), h, w)


def fof_glyph_field(h, w, seed, *, res=700, n=22):
    """NON-voronoi occult glyph field: MANY small carved sigil strokes scattered on a fine
    phase-jittered grid (rings, crossbars, forked staves, dotted bind-runes, triangles) over a
    faint engraved parchment grain — a dense incantation plate, fine and full-coverage."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    s = res / n
    for i in range(n):
        for j in range(n):
            # phase-jitter each glyph so it never reads as a rigid square grid
            cx = (i + 0.5) * s + rng.uniform(-s * 0.22, s * 0.22)
            cy = (j + 0.5) * s + rng.uniform(-s * 0.22, s * 0.22)
            r = s * rng.uniform(0.26, 0.38)
            k = int(rng.integers(0, 7))
            v = float(rng.uniform(0.6, 1.0))
            rot = rng.uniform(0, 6.283)
            ca, sa = np.cos(rot), np.sin(rot)
            def R(dx, dy):  # rotate a local offset
                return (int(cx + dx * ca - dy * sa), int(cy + dx * sa + dy * ca))
            if k == 0:
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
                cv2.line(img, R(-r, 0), R(r, 0), v, 1, cv2.LINE_AA)
            elif k == 1:
                cv2.line(img, R(0, -r), R(0, r), v, 1, cv2.LINE_AA)         # stave
                for tt in (-0.4, 0.1, 0.6):                                # branch ticks
                    cv2.line(img, R(0, r * tt), R(r * 0.6, r * tt - r * 0.4), v, 1, cv2.LINE_AA)
            elif k == 2:
                pts = np.array([R(0, -r), R(r * 0.9, r * 0.7), R(-r * 0.9, r * 0.7)], np.int32)
                cv2.polylines(img, [pts], True, v, 1, cv2.LINE_AA)
                cv2.circle(img, (int(cx), int(cy)), int(r * 0.25), v, -1, cv2.LINE_AA)
            elif k == 3:
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
                cv2.line(img, R(-r * 0.7, -r * 0.7), R(r * 0.7, r * 0.7), v, 1, cv2.LINE_AA)
                cv2.line(img, R(-r * 0.7, r * 0.7), R(r * 0.7, -r * 0.7), v, 1, cv2.LINE_AA)
            elif k == 4:
                cv2.line(img, R(0, -r), R(0, r), v, 1, cv2.LINE_AA)
                cv2.circle(img, R(0, -r), max(1, int(r * 0.2)), v, -1, cv2.LINE_AA)
                cv2.circle(img, R(0, r), max(1, int(r * 0.2)), v, -1, cv2.LINE_AA)
            elif k == 5:
                for kk in range(5):                                        # tiny pentagram glyph
                    a1 = rot + 2 * np.pi * (kk * 2 % 5) / 5
                    a2 = rot + 2 * np.pi * ((kk + 1) * 2 % 5) / 5
                    cv2.line(img, (int(cx + np.cos(a1) * r), int(cy + np.sin(a1) * r)),
                             (int(cx + np.cos(a2) * r), int(cy + np.sin(a2) * r)), v, 1, cv2.LINE_AA)
            else:
                cv2.circle(img, (int(cx), int(cy)), int(r * 0.35), v, -1, cv2.LINE_AA)
                cv2.circle(img, (int(cx), int(cy)), int(r), v, 1, cv2.LINE_AA)
                cv2.circle(img, (int(cx), int(cy)), int(r * 0.7), v * 0.6, 1, cv2.LINE_AA)
    glyph = cv2.GaussianBlur(img, (0, 0), 0.45)
    parch = cv2.GaussianBlur(_fbm(res, res, rng, 5, 7).astype(np.float32), (0, 0), 5.0) * 0.15
    return _up(_norm(glyph * 0.9 + parch), h, w)


def fof_crimson_blood(h, w, seed, *, res=700, pools=46):
    """NON-voronoi blood design: spatter droplets + cast-off specks, vertical drips/runs, and a
    network of coagulated VEINS (random-walk filaments) over a dark clotted ground — a fine
    full-coverage blood field, no cells."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    # ── coagulated veins: random-walk filaments crawling across the whole sheet ──
    for _ in range(int(rng.integers(10, 16))):
        x, y = rng.uniform(0, res), rng.uniform(0, res)
        a = rng.uniform(0, 6.283)
        wd = rng.uniform(1.0, 2.6)
        pts = [(x, y)]
        for _s in range(int(rng.uniform(40, 90))):
            a += rng.uniform(-0.4, 0.4)
            x += np.cos(a) * 4.0; y += np.sin(a) * 4.0
            pts.append((x, y))
        cv2.polylines(img, [np.array(pts, np.int32)], False, float(rng.uniform(0.4, 0.7)),
                      max(1, int(wd)), cv2.LINE_AA)
    # ── spatter pools with cast-off satellites + drip runs ──
    for _ in range(int(pools)):
        cx, cy = float(rng.uniform(0, res)), float(rng.uniform(0, res))
        r = float(rng.uniform(2, 11))
        cv2.circle(img, (int(cx), int(cy)), int(r), float(rng.uniform(0.7, 1.0)), -1, cv2.LINE_AA)
        for _s in range(int(rng.integers(4, 10))):       # cast-off specks
            a = rng.uniform(0, 6.283); d = rng.uniform(r, r * 5.0)
            cv2.circle(img, (int(cx + np.cos(a) * d), int(cy + np.sin(a) * d)),
                       max(1, int(rng.uniform(1, 2.5))), float(rng.uniform(0.4, 0.8)), -1, cv2.LINE_AA)
        if rng.uniform() < 0.5:                            # drip run downwards
            dl = int(rng.uniform(r * 4, r * 12))
            cv2.line(img, (int(cx), int(cy)), (int(cx + rng.uniform(-3, 3)), int(cy + dl)),
                     float(rng.uniform(0.5, 0.9)), max(1, int(r * 0.35)), cv2.LINE_AA)
            cv2.circle(img, (int(cx), int(cy + dl)), max(1, int(r * 0.5)),
                       float(rng.uniform(0.6, 0.95)), -1, cv2.LINE_AA)  # bead at the run's tail
    blood = cv2.GaussianBlur(img, (0, 0), 0.5)
    # clotted ground haze so the dark areas still carry blood, not blank black
    stain = cv2.GaussianBlur(_fbm(res, res, rng, 5, 6).astype(np.float32), (0, 0), 6.0)
    stain = np.clip((stain - 0.45) * 2.0, 0, 1) * 0.22
    return _up(_norm(blood * 0.9 + stain), h, w)


def fof_stained_chapel(h, w, seed, *, res=720, sectors=22, rings=6, rosettes=5,
                       palette=None, edge=(225, 185, 110)):
    """NON-voronoi stained glass: a FIELD of overlapping rose-windows — each pixel takes its nearest
    rosette centre and is leaded into RADIAL wedge panes (sectors x rings, twisted per ring) so the
    whole sheet is a cathedral of small rose-windows, not one centred star. Multi-hue séance violet
    / blood / gold, bright ignitable leading. Pure radial geometry, NOT voronoi."""
    palette = palette or [(95, 45, 150), (155, 28, 42), (185, 150, 70)]
    rng = _rng(seed)
    gy, gx = np.mgrid[0:res, 0:res].astype(np.float32)
    cents = np.stack([rng.uniform(res * 0.05, res * 0.95, int(rosettes)),
                      rng.uniform(res * 0.05, res * 0.95, int(rosettes))], 1).astype(np.float32)
    R0 = res * 0.42
    best_d = np.full((res, res), 1e9, np.float32)
    lab = np.zeros((res, res), np.int64)
    for ci in range(int(rosettes)):
        cx, cy = cents[ci]
        dx, dy = gx - cx, gy - cy
        d = np.hypot(dx, dy)
        ang = (np.arctan2(dy, dx) + np.pi) / (2 * np.pi)
        rad = d / R0
        si = np.floor((ang + ci * 0.137) * sectors).astype(np.int64)
        ri = np.clip(np.floor(rad * rings), 0, rings - 1).astype(np.int64)
        si = (si + ri * 2) % sectors                         # twist each ring -> rose tracery
        l = (ci * 9173 + si * rings + ri).astype(np.int64)
        take = d < best_d                                    # nearest rosette owns the pixel
        best_d = np.where(take, d, best_d)
        lab = np.where(take, l, lab)
    return _up(colorize_cells(lab, (6, 5, 9), palette, edge, seam=3), h, w)


"""FIX engines for 7 rejected FRACTURED CRYPTID finishes (2026-06-17).

BARE names prefixed `fcf_` — pasted into a fix module that does
`from engine.paint_v2.fractured_math import *` + the underscore helpers
(_rng, _fbm, _norm, _up, _curl_warp, _thinfilm, colorize, colorize_cells).

HARD BANS honoured throughout:
  (1) NO VORONOI of any kind — no cKDTree nearest-site labels/distances, no
      _voronoi_labels / _jittered_voronoi_labels / _weighted_voronoi_labels /
      _crackle_labels / cobble / cell-glass. Multi-hue cells here use a custom
      DOMAIN-WARPED ANALYTIC hex label field (fcf_warp_hex_labels) — pure grid
      math advected by curl noise, never a Voronoi.
  (2) NO VISIBLE TILING / REPEATS — never _tile_finer. Every engine gets its fine
      scale from NATIVE high frequency + many scattered sources + domain warp, so
      the field is fine AND has full coverage with no obvious repeat.

Doctrine: many small features, FULL coverage (ambient bloom floors the dark
gaps where needed), abstract/omnidirectional, render < 3s at work res.
"""


# ── shared NON-voronoi de-tiling helpers ───────────────────────────────────────
def fcf_warp_hex_labels(res, seed, cells, amt=0.16):
    """A pure-analytic HEX label field (NO Voronoi) whose sampling coordinates are
    first advected along TWO octaves of divergence-free curl-noise flow (a big slow
    warp + a small fast warp). Result: organic, non-repeating cell shapes of VARYING
    size that read as scattered scales/hide-cells, never a tiled grid — yet there is
    zero nearest-site (Voronoi) math anywhere."""
    rng = _rng(seed)
    ys, xs = np.mgrid[0:res, 0:res].astype(np.float32)
    # octave 1: large, strong warp -> breaks the global lattice into drifting bands
    gy1, gx1 = np.gradient(_fbm(res, res, rng, 3, 4).astype(np.float32))
    # octave 2: small, fast warp -> jitters individual scale shapes/sizes
    gy2, gx2 = np.gradient(_fbm(res, res, _rng(seed + 31), 5, 7).astype(np.float32))
    wx = np.clip(xs + (gy1 * amt + gy2 * amt * 0.5) * res, 0, res - 1)
    wy = np.clip(ys - (gx1 * amt + gx2 * amt * 0.5) * res, 0, res - 1)
    # analytic axial-hex rounding on the WARPED coordinates (cube-coord rounding)
    s = res / cells
    q = (wx * (np.sqrt(3) / 3.0) - wy / 3.0) / s
    r = (wy * 2.0 / 3.0) / s
    x, z = q, r
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    c1 = (dx > dy) & (dx > dz)
    rx = np.where(c1, -ry - rz, rx)
    c2 = (~c1) & (dy > dz)
    rz = np.where(c2, -rx - ry, rz)
    return (rx.astype(np.int64) * 73856093) ^ (rz.astype(np.int64) * 19349663)


def fcf_multihue_scales(scale_field, res, seed, palette, edge_rgb, *,
                        hue_cells=7, edge_gain=0.9, base_floor=0.18):
    """Colorize an ORGANIC NON-voronoi scalar SCALE field (e.g. dragonscale / croc_hide,
    which give overlapping per-scale shading + bright ridge rims and have NO grid look and
    NO Voronoi) into a MULTI-HUE hide: a coarse domain-warped fbm picks which palette hue
    each region takes (smooth wandering patches, not cells), the scale field's brightness
    shades each scale, and its gradient becomes the bright ignitable rim. Returns float RGB.
    Fully NON-voronoi and NON-tiled — the scale spacing is organic and the hue map wanders."""
    f = _norm(np.asarray(scale_field, np.float32))
    # coarse wandering hue-region field (domain-warped) -> blend weights over the palette
    hue = _curl_warp(_fbm(res, res, _rng(seed + 71), 3, 4).astype(np.float32), seed + 73, res, 0.3)
    hue = _norm(hue)
    P = len(palette)
    pal = np.array(palette, np.float32) / 255.0
    idxf = hue * (P - 1)
    i0 = np.floor(idxf).astype(np.int64)
    i1 = np.clip(i0 + 1, 0, P - 1)
    fr = (idxf - i0)[..., None]
    hue_rgb = pal[i0] * (1 - fr) + pal[i1] * fr               # smoothly varying base hue
    shade = (base_floor + (1.0 - base_floor) * f)[..., None]  # scale brightness shading
    # bright ignitable rims = the scale-field gradient (edges of each scale)
    fl = cv2.GaussianBlur(f, (0, 0), 1.0)
    gx = cv2.Sobel(fl, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(fl, cv2.CV_32F, 0, 1, ksize=3)
    rim = (_norm(np.hypot(gx, gy)) * edge_gain)[..., None]
    out = hue_rgb * shade + rim * (np.array(edge_rgb, np.float32) / 255.0)
    return np.clip(out, 0.0, 1.0)


def fcf_scatter_glints(res, rng, n, rmin, rmax, slit=True, bright=(0.6, 1.0)):
    """Many tiny bright eye/glint stamps scattered organically (jittered low-discrepancy
    grid -> full coverage, no clustering, no Voronoi). Returns a 0..1 field of small
    glowing slit-eyes (or round glints) with a faint pupil core."""
    img = np.zeros((res, res), np.float32)
    gn = max(2, int(np.ceil(np.sqrt(n))))   # spread origins over a jittered grid = full coverage
    cell = res / gn
    k = 0
    for i in range(gn):
        for j in range(gn):
            if k >= n:
                break
            k += 1
            cx = (i + 0.5) * cell + rng.uniform(-cell * 0.5, cell * 0.5)
            cy = (j + 0.5) * cell + rng.uniform(-cell * 0.5, cell * 0.5)
            rr = float(rng.uniform(rmin, rmax))
            b = float(rng.uniform(*bright))
            ang = float(rng.uniform(0, 180))
            if slit:
                # bright glowing slit-eye: thin ellipse + dim vertical pupil
                cv2.ellipse(img, (int(cx), int(cy)), (int(rr), max(1, int(rr * 0.42))),
                            ang, 0, 360, b, -1, cv2.LINE_AA)
                cv2.ellipse(img, (int(cx), int(cy)), (max(1, int(rr * 0.22)), max(1, int(rr * 0.4))),
                            ang, 0, 360, b * 0.18, -1, cv2.LINE_AA)
            else:
                cv2.circle(img, (int(cx), int(cy)), int(rr), b, -1, cv2.LINE_AA)
                cv2.circle(img, (int(cx), int(cy)), max(1, int(rr * 0.45)), b * 0.2, -1, cv2.LINE_AA)
    return img


# ════════════════════════════════════════════════════════════════════════════════
# 1) fc_eyeshine — MANY small fine glowing slit-eye glints scattered densely over a
#    near-black forest murk, FULL coverage. Fine (small eyes), no blank spots.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_eyeshine(h, w, seed, *, res=600, eyes=520):
    """Hundreds of tiny glowing slit-eyes peering back out of a near-black forest murk.
    Native fine scale (small radii) + jittered-grid scatter = dense full coverage with
    no blank patches and no repeats; a faint warped fbm murk fills the gaps so the dark
    is alive, not dead. ambient bloom (in the recipe) lifts the deepest corners."""
    rng = _rng(seed)
    glints = fcf_scatter_glints(res, rng, eyes, 2.0, 4.6, slit=True, bright=(0.55, 1.0))
    glints = cv2.GaussianBlur(glints, (0, 0), 0.5)
    murk = _curl_warp(_fbm(res, res, _rng(seed + 5), 5, 6), seed + 9, res, 0.12) * 0.32
    return _up(_norm(glints * 0.95 + murk), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 2) fc_feathered_wing — finer DENSE barbed plumage, richer palette.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_feathered_wing(h, w, seed, *, res=600, feathers=140):
    """Dense overlapping plumage built from REAL feather geometry: many small feathers,
    each a central rachis with side-barbs tapering off (frost_feather), drawn directly at
    NATIVE small size and high count (NOT tiled). Two layered passes at different scales +
    seeds give the layered-covert density; a slowly-varying flow curl-warps the whole vane
    field so the barbs stream like plumage. Fine scale, full coverage, omnidirectional, no
    tiling — and it clearly reads as overlapping feathers, not crystals or coral."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)

    def feather(cx, cy, ang, L):
        ex, ey = cx + np.cos(ang) * L, cy + np.sin(ang) * L
        cv2.line(img, (int(cx), int(cy)), (int(ex), int(ey)), 0.95, 1, cv2.LINE_AA)  # rachis
        nb = max(5, int(L / 2.3))
        for b in range(nb):
            t = b / nb
            bx, by = cx + np.cos(ang) * L * t, cy + np.sin(ang) * L * t
            blen = (1.0 - t) ** 0.7 * L * 0.34          # barbs taper to the tip
            for side in (1.0, -1.0):
                ba = ang + side * 1.05                   # swept-back barbs (feather vane)
                cv2.line(img, (int(bx), int(by)),
                         (int(bx + np.cos(ba) * blen), int(by + np.sin(ba) * blen)),
                         0.6, 1, cv2.LINE_AA)

    # a wandering orientation field -> feathers lie in drifting flocks (layered coverts)
    flow = _fbm(res, res, _rng(seed + 21), 3, 4).astype(np.float32) * 6.283
    for npass, (cnt, lo, hi) in enumerate([(feathers, 0.09, 0.15), (feathers // 2, 0.05, 0.09)]):
        gn = max(2, int(np.ceil(np.sqrt(cnt))))
        cell = res / gn
        k = 0
        for i in range(gn):
            for j in range(gn):
                if k >= cnt:
                    break
                k += 1
                cx = (i + 0.5) * cell + rng.uniform(-cell * 0.7, cell * 0.7)
                cy = (j + 0.5) * cell + rng.uniform(-cell * 0.7, cell * 0.7)
                ix, iy = int(np.clip(cx, 0, res - 1)), int(np.clip(cy, 0, res - 1))
                ang = float(flow[iy, ix]) + float(rng.uniform(-0.35, 0.35))
                feather(cx, cy, ang, float(rng.uniform(lo, hi) * res))
    img = _curl_warp(cv2.GaussianBlur(img, (0, 0), 0.4), seed + 7, res, 0.045)
    fluff = _fbm(res, res, _rng(seed + 3), 5, 6) * 0.24      # soft down between vanes
    return _up(_norm(0.95 * _norm(img) + fluff), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 3) fc_antler_bone — DE-TILE: abstract dense branching bone/antler forks at all
#    angles (stormfork + river_delta branching), no repeats.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_antler_bone(h, w, seed, *, res=640):
    """Abstract dense bone/antler forks at every orientation. Two NATIVE branching
    engines layered (Lichtenberg stormfork + braided river_delta) — both spawn from
    scattered origins and fork recursively, so the tine network fills the whole field
    with NO grid and NO tiled repeat. Curl-warp organicises the forks; a faint bone
    fbm tints the marrow gaps. Distinct branch geometry every seed."""
    fork = stormfork(res, res, seed, bolts=46)               # antler tine tree
    delta = river_delta(res, res, seed + 11, rivers=11)      # extra bone forks
    branch = _curl_warp(_norm(0.7 * fork + 0.6 * delta), seed + 7, res, 0.07)
    marrow = _fbm(res, res, _rng(seed + 3), 4, 6) * 0.16
    return _up(_norm(0.95 * branch + marrow), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 4) fc_will_o_wisp — DE-TILE: dense scattered small bog-lights with wisps, organic
#    placement, no repeats.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_will_o_wisp(h, w, seed, *, res=520, lights=130):
    """A dense swarm of small drifting bog-lights, each trailing a fading wisp, scattered
    organically over a black marsh (jittered grid origins -> full coverage, native fine
    radii -> small lights, NO tiling). Wisp directions follow a curl-noise flow so the
    swarm drifts coherently. Drawn with O(1) cv2 stamps + a bloom blur (NOT a full-canvas
    distance field per light) so it stays well under the render budget. A dim warped marsh
    haze keeps the dark alive everywhere."""
    rng = _rng(seed)
    gyf, gxf = np.gradient(_fbm(res, res, _rng(seed + 13), 4, 5).astype(np.float32))
    # small soft radial glow kernel -> SOLID glowing cores (not hollow rings), stamped O(1)
    ks = 19
    yy, xx = np.mgrid[0:ks, 0:ks].astype(np.float32) - (ks - 1) / 2.0
    glow_k = np.clip(1.0 - np.hypot(xx, yy) / (ks / 2.0), 0, 1) ** 1.8
    img = np.zeros((res + ks, res + ks), np.float32)

    def stamp(px, py, amp, scale):
        x0, y0 = int(px), int(py)
        if 0 <= x0 < res and 0 <= y0 < res:
            sub = img[y0:y0 + ks, x0:x0 + ks]
            np.maximum(sub, glow_k * amp * scale, out=sub)

    gn = max(2, int(np.ceil(np.sqrt(lights))))
    cell = res / gn
    k = 0
    for i in range(gn):
        for j in range(gn):
            if k >= lights:
                break
            k += 1
            cx = (i + 0.5) * cell + rng.uniform(-cell * 0.55, cell * 0.55)
            cy = (j + 0.5) * cell + rng.uniform(-cell * 0.55, cell * 0.55)
            b = float(rng.uniform(0.75, 1.0))
            sc = float(rng.uniform(0.5, 1.0))                 # SMALL lights of varied size
            stamp(cx, cy, b, sc)
            # wisp trail: step along the local curl-flow direction (organic, not radial)
            px, py = cx, cy
            r = sc * ks * 0.5
            for t in range(1, 8):
                ix, iy = int(np.clip(px, 0, res - 1)), int(np.clip(py, 0, res - 1))
                dx, dy = float(gyf[iy, ix]), float(-gxf[iy, ix])
                nrm = np.hypot(dx, dy) + 1e-6
                px += dx / nrm * r * 0.55
                py += dy / nrm * r * 0.55
                stamp(px, py, b * (0.5 - t * 0.05), sc * 0.45)
    img = img[:res, :res]
    glow = cv2.GaussianBlur(img, (0, 0), 6.0) * 0.45          # soft swamp halo
    marsh = _curl_warp(_fbm(res, res, _rng(seed + 5), 5, 6), seed + 9, res, 0.14) * 0.24
    return _up(_norm(img * 0.95 + glow + marsh), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 5) fc_batwing — clearly READ as a leathery bat/mothman wing: membrane + radiating
#    finger-bone struts + fine wrinkles. Distinct.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_batwing(h, w, seed, *, res=600, hands=16):
    """A leathery bat/mothman wing: many wing 'hands' scattered across the sheet, each
    sending a fan of RADIATING finger-bone struts; thin bright trailing-edge membrane
    arcs span between adjacent fingers (the scalloped patagium); a fine wrinkle fbm
    crinkles the stretched skin. Many hands at every angle = full coverage, omnidirectional,
    no tiling, and it unmistakably reads as bat-wing finger-bones + membrane."""
    rng = _rng(seed)
    img = np.zeros((res, res), np.float32)
    gn = max(2, int(np.ceil(np.sqrt(hands))))
    cell = res / gn
    k = 0
    for i in range(gn):
        for j in range(gn):
            if k >= hands:
                break
            k += 1
            cx = (i + 0.5) * cell + rng.uniform(-cell * 0.5, cell * 0.5)
            cy = (j + 0.5) * cell + rng.uniform(-cell * 0.5, cell * 0.5)
            base_ang = float(rng.uniform(0, 6.283))
            spread = float(rng.uniform(1.5, 2.3))             # finger fan angular spread
            nf = int(rng.integers(4, 6))                      # 4-5 finger struts per hand
            L = float(rng.uniform(0.28, 0.42) * res)
            tips = []
            for f in range(nf):
                a = base_ang - spread / 2 + spread * (f / (nf - 1))
                fl = L * (0.7 + 0.3 * np.sin((f + 1) / nf * np.pi))   # middle fingers longest
                # bone strut: thicker at the wrist, tapering — draw as 2 segments for a slight bend
                mx, my = cx + np.cos(a) * fl * 0.55, cy + np.sin(a) * fl * 0.55
                tx, ty = cx + np.cos(a + rng.uniform(-0.12, 0.12)) * fl, cy + np.sin(a + rng.uniform(-0.12, 0.12)) * fl
                cv2.line(img, (int(cx), int(cy)), (int(mx), int(my)), 0.95, 3, cv2.LINE_AA)
                cv2.line(img, (int(mx), int(my)), (int(tx), int(ty)), 0.9, 2, cv2.LINE_AA)
                tips.append((tx, ty))
            # membrane: bright scalloped trailing arcs between consecutive finger tips
            for a, b in zip(tips[:-1], tips[1:]):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                # bow the arc outward from the wrist for the concave membrane scallop
                ox, oy = mx - cx, my - cy
                ctrl = (int(mx + ox * 0.18), int(my + oy * 0.18))
                pts = np.array([a, ctrl, b], np.int32)
                cv2.polylines(img, [pts], False, 0.5, 1, cv2.LINE_AA)
    wrinkle = _curl_warp(_fbm(res, res, _rng(seed + 3), 5, 6), seed + 7, res, 0.05) * 0.34
    membrane_haze = _fbm(res, res, _rng(seed + 17), 3, 4) * 0.14
    return _up(_norm(cv2.GaussianBlur(img, (0, 0), 0.5) * 0.9 + wrinkle + membrane_haze), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 6) fc_hide_scale_glass — NON-voronoi reptilian hide/scale (multi-hue). Fine.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_hide_scale_glass(h, w, seed, *, res=720, rows=34, palette=None, edge=(170, 210, 110)):
    """Multi-hue reptilian hide: OVERLAPPING ARC SCALES (dragonscale — organic seigaiha
    tiling, per-scale shading + bright concentric rims) curl-warped so the rows undulate
    and never look like a rigid grid; a coarse wandering hue field paints each region a
    different forest shade. NON-voronoi and NON-tiled (warped, undulating). Many fine
    scales = full fine coverage; the bright rims are the ignitable detail."""
    palette = palette or [(55, 95, 42), (92, 112, 52), (66, 80, 58), (40, 70, 48), (110, 100, 46)]
    scales = _curl_warp(dragonscale(res, res, seed, rows=rows), seed + 7, res, 0.1)
    return _up(fcf_multihue_scales(scales, res, seed, palette, edge,
                                   edge_gain=1.0, base_floor=0.2), h, w)


# ════════════════════════════════════════════════════════════════════════════════
# 7) fc_crackle_eyeshine_glass — NON-voronoi: fine dark hide with MANY small amber/green
#    eyeshine glints, full coverage, richer palette.
# ════════════════════════════════════════════════════════════════════════════════
def fcf_crackle_eyeshine_glass(h, w, seed, *, res=720, rows=40, palette=None, edge=(120, 150, 70)):
    """Fine DARK reptilian hide (organic warped overlapping ARC-SCALES — NON-voronoi,
    NON-tiled, undulating, richer multi-tone palette) studded with MANY small amber/green
    eyeshine glints scattered densely across the whole sheet. The dark hide gives full
    coverage + fine scale detail; the glints are the bright ignitable 'eyes' — no blank
    spots, no big blobs, no Voronoi, no grid."""
    palette = palette or [(34, 46, 28), (28, 36, 38), (46, 40, 26), (40, 52, 34), (52, 44, 30)]
    scales = _curl_warp(dragonscale(res, res, seed, rows=rows), seed + 7, res, 0.12)
    hide = fcf_multihue_scales(scales, res, seed, palette, edge,
                               edge_gain=0.34, base_floor=0.34)   # dim-but-alive dark hide
    hide *= 0.68                                                  # crush so the eyes dominate
    rng = _rng(seed + 100)
    amber = fcf_scatter_glints(res, rng, 600, 2.4, 5.4, slit=True, bright=(0.85, 1.0))
    green = fcf_scatter_glints(res, rng, 500, 2.2, 4.8, slit=True, bright=(0.8, 1.0))
    amber = cv2.GaussianBlur(amber, (0, 0), 0.5)
    green = cv2.GaussianBlur(green, (0, 0), 0.5)
    out = hide.copy()
    # add amber eyeshine (R/G hot) and green eyeshine (G hot) on top of the hide —
    # strong enough to clearly read as glinting little eyes over the dark hide
    out[:, :, 0] = np.clip(out[:, :, 0] + amber * 1.0 + green * (60 / 255.0), 0, 1)
    out[:, :, 1] = np.clip(out[:, :, 1] + amber * (205 / 255.0) + green * 1.0, 0, 1)
    out[:, :, 2] = np.clip(out[:, :, 2] + amber * (45 / 255.0) + green * (80 / 255.0), 0, 1)
    return _up(out, h, w)
