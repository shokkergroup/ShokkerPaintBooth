"""THE BOOTH — everything that goes wrong between the gun and the cure.

Owner mandate 2026-09-04: four new shelves, minimum 15 finishes each.

THE ARC
-------
Authentic paint-shop defects. This app IS a paint booth, and this is the
trade's own failure vocabulary: fisheye, solvent pop, sags, dry spray, mottling,
tiger stripe, die-back, blush, lifting, sanding-scratch telegraph, dirt nibs,
edge mapping, buffing holograms, mask bleed, tape ridge, water spotting. Every
one is caused by a specific physical mechanism — surface tension, solvent
evaporation, contamination, gravity flow, abrasion — and every one MODULATES the
painter's own colour rather than replacing it, because a defect happens TO paint.

WHY THIS SHELF, WITH EVIDENCE
-----------------------------
Exact-term search across all 4035 picker base finishes:

    fisheye / silicone crater ......... 0
    die-back / blushing ............... 0
    sanding-scratch telegraph ......... 0
    buffing holograms / swirl marks ... 0
    dry spray / overspray ............. 1
    solvent pop / pinhole ............. 3  (all unrelated)

The app's own subject matter was the emptiest shelf in the catalog.

HOW IT WAS BUILT
----------------
Each finish was authored against `_authoring_contract.md` by a dedicated agent
and then audited against the same contract by a second one, because the contract
encodes measured facts that are not guessable — the exact SCALE annulus, the
fact that a blur can never be load-bearing, and that FOLLOW must be CONSTRUCTED
(the spec rebuilds the paint's own field through a shared cache key) rather than
reasoned about. Each finish then declares a knob SPACE, and
`scripts/spb_variant_search.py` renders and scores ten samples of it, writing the
winner to `the_booth_2026_params.json` with the full score table beside it — so "best of
ten" is checkable rather than asserted.
"""

from __future__ import annotations

import numpy as np

from engine.paint_v2 import _finish_kit_2026 as K
from engine.paint_v2._variant_params import chooser

OVERRIDE = None          # (finish_id, params) — set by the variant search harness


def _P(fid):
    if OVERRIDE is not None and OVERRIDE[0] == fid:
        return OVERRIDE[1]
    return _CHOSEN[fid]


def _k(P):
    return K.kkey(P)


# ═══════════════════════════════════════════════════════════ FINISHES ══


def _hash2(a, b, salt=0.0):
    """Per-cell pseudo-random in 0..1 from two integer lattice coords."""
    v = np.sin(a * 127.1 + b * 311.7 + salt) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


# ════════════════════════════════════════════════════════════ 01 · FISHEYE ══
def _fisheye(shape, seed, P):
    """Silicone contamination: paint RETRACTS from a point.

    The profile is what makes it a fisheye rather than a dent — a depressed floor
    showing what is underneath, a raised rim of the material that pulled back, and
    a hard outer boundary where retraction stopped. Craters sit on a jittered
    lattice at ~46px so the CRATER (18-26px) is the dominant band, not the spacing.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        jx = _hash2(iu, iv, 1.9) - 0.5
        jy = _hash2(iu, iv, 5.3) - 0.5
        fu = (u - iu - 0.5 - jx * 0.94) * pitch
        fv = (v - iv - 0.5 - jy * 0.94) * pitch
        d = np.sqrt(fu * fu + fv * fv)
        keep = (_hash2(iu, iv, 17.7) < float(P["density"])).astype(np.float32)
        rad = pitch * float(P["rad"]) * (0.55 + 0.85 * _hash2(iu, iv, 23.1))
        d = d + (1.0 - keep) * pitch * 4.0          # empty cells: no crater at all
        floor = np.clip((rad * 0.62 - d) / 2.0, 0, 1)
        rim = np.clip(1.0 - np.abs(d - rad * 0.86) / (rad * 0.24), 0, 1)
        k = float(P["depth"])
        return (np.clip(1.0 - 0.62 * k * floor + 0.55 * k * rim, 0, 2)
                .astype(np.float32), floor.astype(np.float32))

    return K.cache(("bthfe", h, w, int(seed), _k(P)), build)


def paint_bth_fisheye(paint, shape, mask, seed, pm, bb):
    """Craters where silicone stopped the paint wetting the panel."""
    P = _P("bth_fisheye")
    src = K.incoming(paint, shape)
    mod, floor = _fisheye(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    out = out * (1.0 - 0.30 * floor[:, :, None])       # the substrate shows through
    return K.finish(out, src, mask)


def spec_bth_fisheye(shape, seed, sm, base_m, base_r):
    """GRAMMAR: rim-pair three-material — crater floor, raised rim, clean film."""
    mod, floor = _fisheye(shape, seed, _P("bth_fisheye"))
    m = K.norm(mod)
    M = np.clip(20.0 + 52.0 * m * sm, 0, 255)
    R = np.clip(60.0 + 90.0 * floor - 34.0 * m, 15, 255)   # the floor is raw, unflowed
    CC = np.clip(25.0 + 70.0 * floor, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 02 · SOLVENT POP ══
def _solvent_pop(shape, seed, P):
    """Solvent boils through a skinned surface, leaving an EVERTED lip.

    Holes are gated by a film-thickness field, because pops happen where the paint
    went on heavy. The lip is the tell: a drilled hole has no lip.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        jx = _hash2(iu, iv, 1.7) - 0.5
        jy = _hash2(iu, iv, 4.3) - 0.5
        fu = (u - iu - 0.5 - jx * 0.6) * pitch
        fv = (v - iv - 0.5 - jy * 0.6) * pitch
        d = np.sqrt(fu * fu + fv * fv)
        thick = K.norm(K.mid(shape, 70.0, seed + 3, octaves=2))
        keep = (_hash2(iu, iv, 9.1) < (0.18 + 0.62 * thick)).astype(np.float32)
        rad = float(P["rad"])
        hole = np.clip((rad - d) / 1.2, 0, 1) * keep
        lip = np.clip(1.0 - np.abs(d - rad * 1.25) / 1.8, 0, 1) * keep
        k = float(P["depth"])
        return np.clip(1.0 - 0.85 * k * hole + 0.50 * k * lip, 0, 2).astype(np.float32)

    return K.cache(("bthsp", h, w, int(seed), _k(P)), build)


def paint_bth_solvent_pop(paint, shape, mask, seed, pm, bb):
    """Pinholes blown through the skin by solvent that could not get out."""
    P = _P("bth_solvent_pop")
    src = K.incoming(paint, shape)
    mod = _solvent_pop(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_solvent_pop(shape, seed, sm, base_m, base_r):
    """GRAMMAR: hard duotone with an everted halo — open pore versus intact film."""
    mod = _solvent_pop(shape, seed, _P("bth_solvent_pop"))
    m = K.norm(mod)
    open_pore = (m < 0.35).astype(np.float32)
    M = np.clip(15.0 + 40.0 * m * sm, 0, 255)
    R = np.clip(110.0 + 120.0 * open_pore - 40.0 * m, 15, 255)
    CC = np.clip(40.0 + 110.0 * open_pore, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 03 · SAG CURTAIN ══
def _sag(shape, seed, P):
    """Gravity wins: the film slumps into hanging curtains.

    The vertical run is deliberately LOW contrast and the curtain EDGE carries the
    signal, because a long vertical gradient is macro energy the SCALE gate throws
    away, while the edge sits exactly in the car window.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        xw = px + (K.mid(shape, 140.0, seed + 5, octaves=2) - 0.5) * pitch * 0.9
        f = xw / pitch
        f = f - np.floor(f)
        edge = np.clip(1.0 - np.abs(f - 0.5) * float(P["sharp"]), 0, 1)
        # the bulbous leading edge: a thickening toward the bottom of each run
        foot = K.norm(K.mid(shape, 200.0, seed + 6, octaves=1))
        k = float(P["depth"])
        return np.clip(1.0 - k * edge * (0.55 + 0.45 * foot), 0, 2).astype(np.float32), edge

    return K.cache(("bthsag", h, w, int(seed), _k(P)), build)


def paint_bth_sag_curtain(paint, shape, mask, seed, pm, bb):
    """Curtains of paint that ran before they could flash off."""
    P = _P("bth_sag_curtain")
    src = K.incoming(paint, shape)
    mod, edge = _sag(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    out = out + np.roll(edge, 2, 1)[:, :, None] * 0.16 * float(pm)   # the lit lip
    return K.finish(out, src, mask)


def spec_bth_sag_curtain(shape, seed, sm, base_m, base_r):
    """GRAMMAR: film-thickness ladder — a run is thicker paint, and thick paint is
    glossier and flatter than the starved film beside it."""
    mod, edge = _sag(shape, seed, _P("bth_sag_curtain"))
    m = K.norm(mod)
    M = np.clip(30.0 + 34.0 * m * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - m, 6, 24.0, 86.0), 15, 255)
    CC = np.clip(K.ladder(1.0 - m, 5, 30.0, 108.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════ 04 · DRY SPRAY ══
def _dry_spray(shape, seed, P):
    """Droplets that arrived half-cured and stacked instead of flowing together.

    The LADDER is doing the physical work here: it flattens the tops of the
    droplet field into discrete stacked caps, which is exactly what happens when
    droplets land dry and cannot level out.
    """
    h, w = shape[:2]

    def build():
        caps = K.norm(K.mid(shape, float(P["cap_px"]), seed + 9, octaves=1))
        stacked = K.ladder(caps, int(P["steps"]), 0.0, 1.0)
        return np.clip(0.5 + float(P["depth"]) * (stacked - 0.5), 0, 2).astype(np.float32)

    return K.cache(("bthdry", h, w, int(seed), _k(P)), build)


def paint_bth_dry_spray(paint, shape, mask, seed, pm, bb):
    """Gun too far, paint half dry on arrival: a powdery mound of droplet caps."""
    P = _P("bth_dry_spray")
    src = K.incoming(paint, shape)
    mod = _dry_spray(shape, seed, P)
    out = src * (0.62 + 0.76 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_dry_spray(shape, seed, sm, base_m, base_r):
    """GRAMMAR: smooth inverse-roughness. Dry spray is the matte-est thing in the
    booth, and the only gloss it has is on the caps that did manage to flow."""
    mod = _dry_spray(shape, seed, _P("bth_dry_spray"))
    m = K.norm(mod)
    M = np.clip(25.0 + 30.0 * m * sm, 0, 255)
    R = np.clip(210.0 - 70.0 * m, 15, 255)
    CC = np.clip(120.0 - 45.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 05 · MOTTLING ══
def _mottle(shape, seed, P):
    """Metallic flake clumping as the solvent flashes unevenly.

    Two POPULATIONS, not a gradient: flake that laid down flat (bright, specular)
    and flake that tumbled (dark, diffuse). The hard boundary between them is what
    makes mottling look like mottling rather than like soft noise.
    """
    h, w = shape[:2]

    def build():
        patch = K.norm(K.mid(shape, float(P["patch_px"]), seed + 11, octaves=2))
        laid = (patch > 0.5).astype(np.float32)
        soft = K.box(laid, 2)                       # flake does not switch instantly
        fine = K.norm(K.mid(shape, 5.0, seed + 12, octaves=1)) - 0.5
        k = float(P["depth"])
        return np.clip(0.5 + k * (soft - 0.5) + 0.10 * fine, 0, 2).astype(np.float32), soft

    return K.cache(("bthmot", h, w, int(seed), _k(P)), build)


def paint_bth_mottling(paint, shape, mask, seed, pm, bb):
    """Blotchy flop where the flake clumped instead of laying down evenly."""
    P = _P("bth_mottling")
    src = K.incoming(paint, shape)
    mod, soft = _mottle(shape, seed, P)
    out = src * (0.58 + 0.84 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_mottling(shape, seed, sm, base_m, base_r):
    """GRAMMAR: dual population — laid flake against tumbled flake, two materials
    that differ in metallic more than in roughness."""
    mod, soft = _mottle(shape, seed, _P("bth_mottling"))
    m = K.norm(mod)
    M = np.clip(90.0 + 130.0 * m * sm, 0, 255)
    R = np.clip(96.0 - 42.0 * m, 15, 255)
    CC = np.clip(30.0 + 22.0 * (1.0 - m), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 06 · TIGER STRIPE ══
def _tiger(shape, seed, P):
    """Gun overlap error: each pass lays more metallic at its centre than its edge.

    Strictly periodic and strictly parallel — that regularity is the diagnosis. A
    painter reading this knows immediately it is the gun, not the paint.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        yw = py + (K.mid(shape, 320.0, seed + 13, octaves=1) - 0.5) * 44.0
        b = 0.5 + 0.5 * np.sin(yw * (6.2832 / float(P["pitch"])))
        return np.clip(0.5 + float(P["depth"]) * (b - 0.5), 0, 2).astype(np.float32)

    return K.cache(("bthtig", h, w, int(seed), _k(P)), build)


def paint_bth_tiger_stripe(paint, shape, mask, seed, pm, bb):
    """Banding at the gun's pass pitch — the classic overlap failure."""
    P = _P("bth_tiger_stripe")
    src = K.incoming(paint, shape)
    mod = _tiger(shape, seed, P)
    out = src * (0.60 + 0.80 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_tiger_stripe(shape, seed, sm, base_m, base_r):
    """GRAMMAR: anisotropic banded ramp — metallic content rises and falls with the
    pass, so M carries the stripe and roughness barely moves."""
    mod = _tiger(shape, seed, _P("bth_tiger_stripe"))
    m = K.norm(mod)
    M = np.clip(70.0 + 150.0 * m * sm, 0, 255)
    R = np.clip(92.0 - 22.0 * m, 15, 255)
    CC = np.clip(35.0 + 14.0 * (1.0 - m), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 07 · DIE-BACK ══
def _die_back(shape, seed, P):
    """The clear keeps shrinking after it looked cured, and gloss dies unevenly.

    Almost purely a GLOSS defect: the hue does not move, so the spec carries the
    story and the paint only shows the sheen change as luminance.
    """
    h, w = shape[:2]

    def build():
        cell = K.norm(K.mid(shape, float(P["cell_px"]), seed + 15, octaves=2))
        return K.ladder(cell, int(P["steps"]), 0.0, 1.0)

    return K.cache(("bthdb", h, w, int(seed), _k(P)), build)


def paint_bth_die_back(paint, shape, mask, seed, pm, bb):
    """Gloss dying back in patches while the colour underneath stays put."""
    P = _P("bth_die_back")
    src = K.incoming(paint, shape)
    mod = _die_back(shape, seed, P)
    k = float(P["depth"])
    out = src * (1.0 - 0.5 * k + k * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_die_back(shape, seed, sm, base_m, base_r):
    """GRAMMAR: gloss-only ramp. M is nearly flat by design — the entire defect
    lives in roughness and clearcoat, which is what die-back physically is."""
    mod = _die_back(shape, seed, _P("bth_die_back"))
    M = np.clip(18.0 + 12.0 * mod * sm, 0, 255)
    R = np.clip(150.0 - 120.0 * mod, 15, 255)
    CC = np.clip(190.0 - 150.0 * mod, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════ 08 · BLUSH ══
def _blush(shape, seed, P):
    """Moisture condensing into the film as evaporation chills it.

    A veil with structure, not a fog: the haze is denser where the surface cooled
    fastest, so it has a legible 14-20px cell rather than being a flat wash.
    """
    h, w = shape[:2]

    def build():
        veil = K.norm(K.mid(shape, float(P["veil_px"]), seed + 17, octaves=2))
        return (veil ** float(P["bias"])).astype(np.float32)

    return K.cache(("bthbl", h, w, int(seed), _k(P)), build)


def paint_bth_blush(paint, shape, mask, seed, pm, bb):
    """Milky bloom precipitating in the clear — it desaturates, it does not tint."""
    P = _P("bth_blush")
    src = K.incoming(paint, shape)
    veil = _blush(shape, seed, P)
    a = np.clip(float(P["haze"]) * veil * float(pm), 0, 1)[:, :, None]
    lum = src.mean(axis=2, keepdims=True)
    milk = lum * 0.45 + 0.55
    out = src * (1.0 - a) + milk * a
    return K.finish(out, src, mask)


def spec_bth_blush(shape, seed, sm, base_m, base_r):
    """GRAMMAR: milky veil bimodal — hazed film and clear film are two materials,
    and the hazed one scatters instead of reflecting."""
    veil = _blush(shape, seed, _P("bth_blush"))
    M = np.clip(10.0 + 16.0 * (1.0 - veil) * sm, 0, 255)
    R = np.clip(60.0 + 150.0 * veil, 15, 255)
    CC = np.clip(50.0 + 160.0 * veil, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════════ 09 · LIFTING ══
def _lifting(shape, seed, P):
    """Fresh solvent attacks the layer beneath, which swells and buckles.

    Buckling is a COMPRESSION instability, so the ridges are periodic and appear
    only where the underlayer actually swelled — not a folded noise field, which
    would put ridges everywhere at equal strength.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        swell = K.norm(K.mid(shape, 90.0, seed + 19, octaves=2))
        phase = px / float(P["pitch"]) + (K.mid(shape, 60.0, seed + 20, octaves=2) - 0.5) * 3.4
        wave = 0.5 + 0.5 * np.cos(phase * 6.2832)
        ridge = (wave ** 3.0) * np.clip(swell * 1.6 - 0.35, 0, 1)
        k = float(P["depth"])
        return np.clip(1.0 - k * ridge, 0, 2).astype(np.float32), ridge.astype(np.float32)

    return K.cache(("bthlift", h, w, int(seed), _k(P)), build)


def paint_bth_lifting(paint, shape, mask, seed, pm, bb):
    """The film wrinkling as what is under it swells and lets go."""
    P = _P("bth_lifting")
    src = K.incoming(paint, shape)
    mod, ridge = _lifting(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    out = out + np.roll(ridge, -2, 1)[:, :, None] * 0.30 * float(pm)
    return K.finish(out, src, mask)


def spec_bth_lifting(shape, seed, sm, base_m, base_r):
    """GRAMMAR: ridge edge-driven — the crest of a wrinkle is stretched and dull,
    the valley still holds its clear."""
    mod, ridge = _lifting(shape, seed, _P("bth_lifting"))
    m = K.norm(mod)
    M = np.clip(35.0 + 30.0 * m * sm, 0, 255)
    R = np.clip(150.0 + 80.0 * (1.0 - m) - 30.0 * m, 15, 255)
    CC = np.clip(60.0 + 90.0 * (1.0 - m), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 10 · SAND SCRATCH ══
def _sand_scratch(shape, seed, P):
    """320-grit telegraphing through the topcoat.

    The tell is that the DIRECTION changes between sanding patches while staying
    perfectly parallel inside each one — that is a hand moving, and no isotropic
    noise field reproduces it.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        patch = K.mid(shape, float(P["patch_px"]), seed + 21, octaves=1)
        ang = np.floor(patch * 4.0) / 4.0 * np.float32(np.pi)
        u = px * np.cos(ang) + py * np.sin(ang)
        s = 0.5 + 0.5 * np.sin(u * (6.2832 / float(P["pitch"])))
        grit = K.norm(K.mid(shape, 3.0, seed + 22, octaves=1)) - 0.5
        k = float(P["depth"])
        return np.clip(0.5 + k * (s - 0.5) + 0.06 * grit, 0, 2).astype(np.float32)

    return K.cache(("bthsand", h, w, int(seed), _k(P)), build)


def paint_bth_sand_scratch(paint, shape, mask, seed, pm, bb):
    """Sanding scratches showing through the colour that was meant to bury them."""
    P = _P("bth_sand_scratch")
    src = K.incoming(paint, shape)
    mod = _sand_scratch(shape, seed, P)
    out = src * (0.66 + 0.70 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_sand_scratch(shape, seed, sm, base_m, base_r):
    """GRAMMAR: directional patch anisotropy — each patch is one material whose
    roughness runs along its own axis."""
    mod = _sand_scratch(shape, seed, _P("bth_sand_scratch"))
    m = K.norm(mod)
    M = np.clip(45.0 + 44.0 * m * sm, 0, 255)
    R = np.clip(125.0 + 60.0 * (1.0 - m) - 40.0 * m, 15, 255)
    CC = np.clip(50.0 + 40.0 * (1.0 - m), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 11 · DIRT NIB ══
def _dirt_nib(shape, seed, P):
    """An inclusion in wet paint: particle, the film TENTED over it, and a halo.

    Three parts, which is what separates a nib from a bump. The tent is the give-
    away every painter checks for before deciding whether it can be nibbed out.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        jx = _hash2(iu, iv, 2.9) - 0.5
        jy = _hash2(iu, iv, 6.1) - 0.5
        fu = (u - iu - 0.5 - jx * 0.96) * pitch
        fv = (v - iv - 0.5 - jy * 0.96) * pitch
        d = np.sqrt(fu * fu + fv * fv)
        keep = (_hash2(iu, iv, 11.3) < float(P["density"])).astype(np.float32)
        r0 = float(P["rad"]) * (0.5 + 1.1 * _hash2(iu, iv, 19.7))
        grain = np.clip((r0 - d) / 1.2, 0, 1) * keep
        tent = (np.clip((r0 * 2.3 - d) / (r0 * 1.3), 0, 1) - np.clip((r0 - d) / 1.2, 0, 1)) * keep
        halo = np.clip(1.0 - np.abs(d - r0 * 3.0) / 2.2, 0, 1) * keep
        k = float(P["depth"])
        return (np.clip(1.0 + k * (-0.90 * grain + 0.34 * tent - 0.18 * halo), 0, 2)
                .astype(np.float32), grain.astype(np.float32), tent.astype(np.float32))

    return K.cache(("bthnib", h, w, int(seed), _k(P)), build)


def paint_bth_dirt_nib(paint, shape, mask, seed, pm, bb):
    """Dust that landed in the wet, with the paint pulled up over the top of it."""
    P = _P("bth_dirt_nib")
    src = K.incoming(paint, shape)
    mod, grain, tent = _dirt_nib(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_dirt_nib(shape, seed, sm, base_m, base_r):
    """GRAMMAR: three-material stack — particle, tented film, settled halo."""
    mod, grain, tent = _dirt_nib(shape, seed, _P("bth_dirt_nib"))
    m = K.norm(mod)
    M = np.clip(55.0 + 60.0 * m * sm + 40.0 * grain, 0, 255)
    R = np.clip(80.0 + 120.0 * grain - 30.0 * tent, 15, 255)
    CC = np.clip(28.0 + 60.0 * grain + 20.0 * tent, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═════════════════════════════════════════════════════════════ 12 · EDGE MAP ══
def _edge_map(shape, seed, P):
    """A repair halo: contour steps where old clear was feather-sanded away.

    Contours of a smooth field, so their SPACING is set by the gradient — pick the
    field scale so the rings land 14-24px apart, which is what puts this in the
    car window rather than making one big ring nobody sees.
    """
    h, w = shape[:2]

    def build():
        z = K.norm(K.mid(shape, float(P["zone_px"]), seed + 25, octaves=2))
        step = K.ladder(z, int(P["steps"]), 0.0, 1.0)
        contour = np.clip(np.abs(step - K.box(step, 1)) * 6.0, 0, 1)
        k = float(P["depth"])
        return np.clip(1.0 - k * contour + 0.16 * (step - 0.5), 0, 2).astype(np.float32), contour

    return K.cache(("bthem", h, w, int(seed), _k(P)), build)


def paint_bth_edge_map(paint, shape, mask, seed, pm, bb):
    """The ghost outline of a repair, mapped in rings of gloss and texture."""
    P = _P("bth_edge_map")
    src = K.incoming(paint, shape)
    mod, contour = _edge_map(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_edge_map(shape, seed, sm, base_m, base_r):
    """GRAMMAR: contour-band ladder — each sanding step is its own flat material."""
    mod, contour = _edge_map(shape, seed, _P("bth_edge_map"))
    m = K.norm(mod)
    M = np.clip(22.0 + 44.0 * m * sm, 0, 255)
    R = np.clip(K.ladder(1.0 - m, 6, 40.0, 120.0) + 60.0 * contour, 15, 255)
    CC = np.clip(85.0 + 70.0 * contour - 30.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════ 13 · BUFF HOLOGRAM ══
def _buff(shape, seed, P):
    """Rotary swirl: interfering families of concentric scratch rings.

    Not a spiral — a polisher head makes CONCENTRIC arcs, and it is the overlap of
    several head positions that produces the holographic shimmer you see in low
    sun. Summing a few ring families is literally what the machine did.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        rng = np.random.default_rng((int(seed) ^ 0x8A31) & 0xFFFFFFFF)
        acc = np.zeros((h, w), np.float32)
        inv = 6.2832 / float(P["pitch"])
        for _ in range(int(P["heads"])):
            cy, cx = rng.uniform(0, h), rng.uniform(0, w)
            dy, dx = py - cy, px - cx
            r = np.sqrt(dy * dy + dx * dx)
            acc += np.sin(r * inv) / (1.0 + r / (min(h, w) * 0.45))
        s = K.norm(acc)
        return np.clip(0.5 + float(P["depth"]) * (s - 0.5), 0, 2).astype(np.float32)

    return K.cache(("bthbuf", h, w, int(seed), _k(P)), build)


def paint_bth_buff_hologram(paint, shape, mask, seed, pm, bb):
    """Holograms: the arcs a rotary leaves, visible only as a directional haze."""
    P = _P("bth_buff_hologram")
    src = K.incoming(paint, shape)
    mod = _buff(shape, seed, P)
    out = src * (0.70 + 0.62 * mod[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_buff_hologram(shape, seed, sm, base_m, base_r):
    """GRAMMAR: phase-quantised polar — the scratch phase is stepped, so the panel
    deals a fixed set of materials that wheel around the polisher's path."""
    mod = _buff(shape, seed, _P("bth_buff_hologram"))
    step = K.ladder(K.norm(mod), 7, 0.0, 1.0)
    M = np.clip(95.0 + 90.0 * step * sm, 0, 255)
    R = np.clip(70.0 - 42.0 * step, 15, 255)
    CC = np.clip(22.0 + 24.0 * (1.0 - step), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════════ 14 · MASK BLEED ══
def _mask_bleed(shape, seed, P):
    """Paint creeping under a tape edge along the substrate's own texture.

    One side is a hard tape line, the other is capillary FINGERS whose reach
    varies with how well the tape was burnished down. The asymmetry is the whole
    diagnosis: a clean line on one side, feathering on the other.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        yw = py + (K.mid(shape, 260.0, seed + 27, octaves=2) - 0.5) * pitch * 1.2
        f = yw / pitch
        d = (f - np.floor(f)) * pitch                      # distance past the tape edge
        finger = K.norm(K.mid(shape, float(P["finger_px"]), seed + 28, octaves=1))
        reach = (finger ** 2.2) * float(P["reach"]) * pitch
        bleed = np.clip((reach - d) / 2.5, 0, 1)
        line = np.clip(1.0 - d / 2.5, 0, 1)                # the hard tape edge itself
        k = float(P["depth"])
        return (np.clip(1.0 - k * (0.55 * bleed + 0.45 * line), 0, 2)
                .astype(np.float32), bleed.astype(np.float32))

    return K.cache(("bthmb", h, w, int(seed), _k(P)), build)


def paint_bth_mask_bleed(paint, shape, mask, seed, pm, bb):
    """Colour wicking under the tape into fine capillary fingers."""
    P = _P("bth_mask_bleed")
    src = K.incoming(paint, shape)
    mod, bleed = _mask_bleed(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_mask_bleed(shape, seed, sm, base_m, base_r):
    """GRAMMAR: feathered capillary duotone — bled paint is thin and starved, so it
    is duller than either the masked ground or the full-build colour."""
    mod, bleed = _mask_bleed(shape, seed, _P("bth_mask_bleed"))
    m = K.norm(mod)
    M = np.clip(28.0 + 40.0 * m * sm, 0, 255)
    R = np.clip(170.0 - 96.0 * m, 15, 255)
    CC = np.clip(110.0 - 68.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ═══════════════════════════════════════════════════════════ 15 · TAPE RIDGE ══
def _tape_ridge(shape, seed, P):
    """Tape pulled after the paint set: a wall of build with a starved zone before it.

    A three-zone profile across each edge — starved, ridge, shadow — repeated on a
    regular pitch, because masking is laid out deliberately and not at random.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        ang = np.deg2rad(float(P["angle"]))
        u = px * np.cos(ang) + py * np.sin(ang)
        u = u + (K.mid(shape, 240.0, seed + 29, octaves=2) - 0.5) * 18.0
        f = u / pitch
        t = (f - np.floor(f)) * pitch
        ridge = np.clip(1.0 - np.abs(t - pitch * 0.5) / float(P["wall"]), 0, 1)
        starve = np.clip(1.0 - np.abs(t - pitch * 0.5 + float(P["wall"]) * 2.2)
                         / (float(P["wall"]) * 1.6), 0, 1)
        k = float(P["depth"])
        return (np.clip(1.0 + k * (0.85 * ridge - 0.40 * starve), 0, 2)
                .astype(np.float32), ridge.astype(np.float32), starve.astype(np.float32))

    return K.cache(("bthtr", h, w, int(seed), _k(P)), build)


def paint_bth_tape_ridge(paint, shape, mask, seed, pm, bb):
    """The hard wall of paint build a tape edge leaves behind."""
    P = _P("bth_tape_ridge")
    src = K.incoming(paint, shape)
    mod, ridge, starve = _tape_ridge(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    return K.finish(out, src, mask)


def spec_bth_tape_ridge(shape, seed, sm, base_m, base_r):
    """GRAMMAR: step edge-driven — a hard three-level profile across every edge,
    with no gradient anywhere. The cleanest spec on this shelf."""
    mod, ridge, starve = _tape_ridge(shape, seed, _P("bth_tape_ridge"))
    m = K.norm(mod)
    M = np.clip(40.0 + 50.0 * m * sm, 0, 255)
    R = np.clip(150.0 - 100.0 * m, 15, 255)
    CC = np.clip(110.0 - 78.0 * m, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ══════════════════════════════════════════════════════════ 16 · WATER SPOT ══
def _water_spot(shape, seed, P):
    """Hard water drying on fresh clear: minerals deposit at the RECEDING contact
    line, so the ring is sharp and the interior is barely touched.

    The same coffee-ring physics that makes a spilled drink leave an outline, and
    the reason a water spot cannot be polished off by wiping the middle.
    """
    h, w = shape[:2]

    def build():
        py, px = K.px(shape)
        pitch = float(P["pitch"])
        u, v = px / pitch, py / pitch
        iu, iv = np.floor(u), np.floor(v)
        jx = _hash2(iu, iv, 3.3) - 0.5
        jy = _hash2(iu, iv, 7.7) - 0.5
        fu = (u - iu - 0.5 - jx * 0.8) * pitch
        fv = (v - iv - 0.5 - jy * 0.8) * pitch
        d = np.sqrt(fu * fu + fv * fv)
        rad = pitch * (0.28 + 0.20 * _hash2(iu, iv, 13.1))
        ring = np.clip(1.0 - np.abs(d - rad) / float(P["ring_px"]), 0, 1)
        inner = np.clip((rad - d) / 3.0, 0, 1) * 0.18
        k = float(P["depth"])
        return np.clip(1.0 - k * (ring + inner), 0, 2).astype(np.float32), ring.astype(np.float32)

    return K.cache(("bthws", h, w, int(seed), _k(P)), build)


def paint_bth_water_spot(paint, shape, mask, seed, pm, bb):
    """Mineral rings etched where hard water dried on the clear."""
    P = _P("bth_water_spot")
    src = K.incoming(paint, shape)
    mod, ring = _water_spot(shape, seed, P)
    out = src * (1.0 + (mod - 1.0)[:, :, None] * float(pm))
    out = out + ring[:, :, None] * 0.14 * float(pm)        # the deposit itself is pale
    return K.finish(out, src, mask)


def spec_bth_water_spot(shape, seed, sm, base_m, base_r):
    """GRAMMAR: ring deposit ladder — the deposit is a mineral crust, a genuinely
    different material from the clear it sits on."""
    mod, ring = _water_spot(shape, seed, _P("bth_water_spot"))
    m = K.norm(mod)
    M = np.clip(12.0 + 20.0 * m * sm, 0, 255)
    R = np.clip(K.ladder(ring, 5, 60.0, 210.0), 15, 255)
    CC = np.clip(K.ladder(ring, 4, 60.0, 200.0), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)



# ══════════════════════════════════════════════════════════════ CATALOG ══
CATALOG = {
    "bth_fisheye":       {"M": 20,  "R": 60,  "CC": 25,
                          "desc": "Fisheye — silicone contamination the paint refused to wet over"},
    "bth_solvent_pop":   {"M": 15,  "R": 110, "CC": 40,
                          "desc": "Solvent Pop — pinholes blown through a skin by solvent that could not escape"},
    "bth_sag_curtain":   {"M": 30,  "R": 40,  "CC": 70,
                          "desc": "Sag Curtain — too much material, and gravity got to it first"},
    "bth_dry_spray":     {"M": 25,  "R": 190, "CC": 95,
                          "desc": "Dry Spray — droplets that landed half-cured and never flowed together"},
    "bth_mottling":      {"M": 140, "R": 70,  "CC": 30,
                          "desc": "Mottling — metallic flake clumped instead of laying down flat"},
    "bth_tiger_stripe":  {"M": 120, "R": 85,  "CC": 35,
                          "desc": "Tiger Stripe — banding at the gun's own pass pitch"},
    "bth_die_back":      {"M": 18,  "R": 95,  "CC": 120,
                          "desc": "Die-Back — gloss dying away in patches long after it looked cured"},
    "bth_blush":         {"M": 10,  "R": 140, "CC": 160,
                          "desc": "Blush — moisture precipitating into the film as it chilled"},
    "bth_lifting":       {"M": 35,  "R": 150, "CC": 60,
                          "desc": "Lifting — fresh solvent attacking what was underneath until it buckled"},
    "bth_sand_scratch":  {"M": 45,  "R": 125, "CC": 50,
                          "desc": "Sand Scratch — 320-grit telegraphing up through the colour"},
    "bth_dirt_nib":      {"M": 55,  "R": 80,  "CC": 28,
                          "desc": "Dirt Nib — dust in the wet, with the film tented over the top of it"},
    "bth_edge_map":      {"M": 22,  "R": 70,  "CC": 85,
                          "desc": "Edge Map — the ghost outline of a repair, ringed in gloss and texture"},
    "bth_buff_hologram": {"M": 95,  "R": 45,  "CC": 22,
                          "desc": "Buff Hologram — the arcs a rotary leaves, seen only in low sun"},
    "bth_mask_bleed":    {"M": 28,  "R": 100, "CC": 45,
                          "desc": "Mask Bleed — colour wicking under a tape edge into capillary fingers"},
    "bth_tape_ridge":    {"M": 40,  "R": 55,  "CC": 32,
                          "desc": "Tape Ridge — the wall of build left where the tape was pulled"},
    "bth_water_spot":    {"M": 12,  "R": 165, "CC": 140,
                          "desc": "Water Spot — hard water drying its minerals into the clear"},
}

SPACE = {
    "bth_fisheye":       {"pitch": (30.0, 50.0), "rad": (0.22, 0.34), "density": (0.30, 0.62),
                          "depth": (0.70, 1.60)},
    "bth_solvent_pop":   {"pitch": (13.0, 22.0), "rad": (3.0, 6.0), "depth": (0.55, 1.30)},
    "bth_sag_curtain":   {"pitch": (24.0, 44.0), "sharp": (2.2, 5.0), "depth": (0.45, 1.05)},
    "bth_dry_spray":     {"cap_px": (9.0, 15.0), "steps": [3, 4, 5, 6], "depth": (0.55, 1.30)},
    "bth_mottling":      {"patch_px": (11.0, 19.0), "depth": (0.55, 1.25)},
    "bth_tiger_stripe":  {"pitch": (18.0, 30.0), "depth": (0.45, 1.10)},
    "bth_die_back":      {"cell_px": (11.0, 20.0), "steps": [4, 5, 6, 8], "depth": (0.40, 0.95)},
    "bth_blush":         {"veil_px": (13.0, 22.0), "bias": (0.8, 2.0), "haze": (0.45, 1.00)},
    "bth_lifting":       {"pitch": (11.0, 18.0), "depth": (0.50, 1.20)},
    "bth_sand_scratch":  {"patch_px": (55.0, 120.0), "pitch": (9.0, 15.0), "depth": (0.45, 1.05)},
    "bth_dirt_nib":      {"pitch": (26.0, 46.0), "rad": (2.4, 4.6), "density": (0.35, 0.80),
                          "depth": (0.60, 1.40)},
    "bth_edge_map":      {"zone_px": (40.0, 85.0), "steps": [6, 8, 11], "depth": (0.95, 2.10)},
    "bth_buff_hologram": {"heads": [3, 4, 6], "pitch": (12.0, 22.0), "depth": (0.50, 1.20)},
    "bth_mask_bleed":    {"pitch": (22.0, 40.0), "finger_px": (10.0, 17.0), "reach": (0.30, 0.72),
                          "depth": (0.50, 1.15)},
    "bth_tape_ridge":    {"pitch": (17.0, 28.0), "wall": (1.6, 3.4), "angle": (0.0, 90.0),
                          "depth": (0.55, 1.30)},
    "bth_water_spot":    {"pitch": (14.0, 24.0), "ring_px": (1.4, 3.0), "depth": (0.55, 1.25)},
}

_CHOSEN = chooser(__name__, SPACE)


def install(registry):
    """Wire this shelf into a BASE_REGISTRY. Returns the number installed."""
    import sys as _sys
    me = _sys.modules[__name__]
    n = 0
    for fid, meta in CATALOG.items():
        entry = registry.setdefault(fid, {})
        entry.update(meta)
        entry["paint_fn"] = getattr(me, "paint_" + fid)
        entry["base_spec_fn"] = getattr(me, "spec_" + fid)
        n += 1
    return n
