# -*- coding: utf-8 -*-
"""FRACTURED TESSERA KIT (2026-08-30) — the glasswork assembler.

Owner, 2026-08-30: *"TRUCHET GLASS from Fractured FORGE is one of my favorite
finishes so I want that protected and MOVED somewhere safe… that category as a
whole is all over the place."* The answer: build the new category around
Truchet Glass's OWN mechanism, so it can never be orphaned again.

THE MECHANISM (reverse-engineered from `ff_truchet_glass`):
    a TILING assigns integer labels -> every cell takes a palette hue at a
    per-cell shade (jewel panes) -> cell boundaries become a bright traced seam
    -> `fracture_spec` IGNITES those seams on the car.
Panes plus luminous cames. It is the same reason Hologram Metal wins: adjacent
contrasting regions with boundaries that fire under light.

WHAT THIS KIT ADDS over the original `colorize_cells` (which is flat panes +
a flat 2px seam — fine for one finish, not enough to carry fifty):

  * PANE TREATMENTS — real glass is never flat. slump / drawn / seedy / ripple /
    crackle / iris / granite, each riding the in-pane depth field so the
    treatment follows the tile instead of floating over it.
  * CAME TREATMENTS — the lead itself is an identity axis: hairline, fat lead,
    beveled (bright inner shoulder over a dark core), copper foil (Tiffany),
    dalle-de-verre (fat dark concrete), double-line, and wire.
  * GLASS DEPTH — panes darken toward their edges the way real glass thickens
    into the came, which is what makes a flat tiling read as a SLAB.
  * THE PANE-SCALE LAW — the defect that ruined most of the family: Parquet,
    Pinwheel, Ziggurat and Catacomb render two-to-four giant blocks on a whole
    car. Panes must sit at 40-120px on the 2048 canvas. `pane_stats()` measures
    it and the harness gates on it.

Every finish is one recipe row: a tiling name + its args, a palette, a came, a
pane treatment, and the fracture dials. Tilings live in the category module.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

WORK = 1152          # art computed here, resized to the requested render size
GEN = 768            # tilings are generated here, then upscaled (labels: NEAREST)
_TAU = 6.283185307179586

# 8-tier shade ladder (owner law: many shades, never two levels)
_TIERS = np.array([0.42, 0.52, 0.61, 0.69, 0.77, 0.84, 0.91, 0.98], np.float32)


def rng(seed, salt=0):
    return np.random.default_rng([(int(seed) * 100003) & 0x7FFFFFFF, int(salt) & 0x7FFFFFFF])


def coords(res):
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    return yy, xx


def frac(a):
    a = np.asarray(a, np.float32)
    return (a - np.floor(a)).astype(np.float32)


def n01(a):
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-9)


def h1(i, salt=0):
    """Deterministic per-label hash -> 0..1."""
    x = (np.asarray(i, np.int64) * 2654435761 + int(salt) * 40503) & 0x7FFFFFFF
    return (x % 100003).astype(np.float32) / 100003.0


def fbm(res, r, octaves=4, base=4, gain=0.55):
    acc = np.zeros((res, res), np.float32)
    amp, tot, s = 1.0, 0.0, int(base)
    for _ in range(int(octaves)):
        g = r.random((s, s)).astype(np.float32)
        acc += amp * cv2.resize(g, (res, res), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= gain
        s = min(s * 2, res)
        if s >= res:
            break
    return acc / max(tot, 1e-9)


# ════════════════════════════════════════════════════════════════════════════
# LABEL FIELD ANALYSIS — boundaries, in-pane depth, per-pane identity
# ════════════════════════════════════════════════════════════════════════════

def boundary(labels):
    """True on any pixel whose 4-neighbourhood crosses a label change."""
    li = np.asarray(labels, np.int64)
    return ((li != np.roll(li, 1, 0)) | (li != np.roll(li, 1, 1))
            | (li != np.roll(li, -1, 0)) | (li != np.roll(li, -1, 1)))


def pane_depth(bnd):
    """Distance from every pixel to the nearest came, in px (the glass gets
    thicker away from the lead — this is what makes a tiling read as a slab)."""
    inside = (~bnd).astype(np.uint8)
    return cv2.distanceTransform(inside, cv2.DIST_L2, 3).astype(np.float32)


def pane_stats(labels):
    """(pane count, median pane WIDTH in px).

    THE PANE-SCALE LAW measures WIDTH, not equivalent diameter. Measured on the
    reference: `ff_truchet_glass` — the finish the owner calls a huge winner —
    has an equivalent diameter of 162px, which sounds enormous, but its arc
    bands are only **32.5px wide**; the diameter is inflated because the regions
    are long and thin. Width is what the eye reads on a car. Argyle Glass, the
    other strong sibling, sits at 43px. So the law is width 24-60px, centred on
    Truchet's 32px, and it correctly fails the giant-block siblings."""
    li = np.asarray(labels, np.int64)
    b = boundary(li)
    d = pane_depth(b)
    inside = d[d > 0.5]
    if inside.size == 0:
        return 0, 0.0
    n = int(np.unique(li).size)
    return n, float(np.median(inside)) * 2.0


# ════════════════════════════════════════════════════════════════════════════
# PANE TREATMENTS — what the glass itself is doing inside every cell
# ════════════════════════════════════════════════════════════════════════════

def _pane_texture(kind, res, depth, lab, seed, amt):
    """0-centred luminance modulation inside the panes (never touches the came)."""
    if not kind or kind == "flat" or amt <= 0:
        return np.zeros((res, res), np.float32)
    yy, xx = coords(res)
    d = depth / max(float(depth.max()), 1e-6)
    r = rng(seed, 77)
    if kind == "slump":                     # kiln-slumped: the pane sags, bright at its heart
        t = np.clip(d * 1.6, 0, 1) ** 0.7 - 0.45
    elif kind == "drawn":                   # hand-drawn cylinder glass: directional striae
        a = h1(lab, 5) * _TAU
        u = xx * np.cos(a) + yy * np.sin(a)
        t = 0.5 * np.sin(u / 2.6 + h1(lab, 9) * _TAU) * np.clip(0.35 + d * 0.65, 0, 1)
    elif kind == "seedy":                   # seedy glass: trapped bubbles
        c = 5.2
        du, dv = frac(xx / c) - 0.5, frac(yy / c) - 0.5
        dome = np.clip(1.0 - 4.2 * (du * du + dv * dv), 0, 1)
        g = frac(np.sin(np.floor(xx / c) * 127.1 + np.floor(yy / c) * 311.7) * 43758.5453)
        t = (g > 0.72).astype(np.float32) * dome * np.clip(0.35 + d * 0.65, 0, 1) - 0.06
    elif kind == "ripple":                  # water glass: concentric ripple pressed in
        t = 0.5 * np.sin(depth / 2.2 + h1(lab, 13) * _TAU) * np.clip(0.40 + d * 0.60, 0, 1)
    elif kind == "crackle":                 # crackle/craquelure glass
        f = fbm(res, r, 4, 7)
        t = (np.abs(frac(f * 26.0) - 0.5) * 2.0 - 0.55) * 0.9 * np.clip(0.40 + d * 0.60, 0, 1)
    elif kind == "iris":                    # iridised surface film — hue handled by caller
        t = 0.4 * np.sin(depth / 3.4 + h1(lab, 3) * _TAU) * np.clip(d, 0, 1)
    elif kind == "granite":                 # granite/oatmeal rolled glass
        f = fbm(res, r, 3, 96)
        t = (f - 0.5) * 1.5 * np.clip(0.40 + d * 0.60, 0, 1)
    elif kind == "reamy":                   # reamy: slow swirling density
        f = fbm(res, r, 3, 6)
        t = np.sin(f * 9.0 + depth / 5.0) * 0.5 * np.clip(0.40 + d * 0.60, 0, 1)
    else:
        t = np.zeros((res, res), np.float32)
    return (t * float(amt)).astype(np.float32)


def glass_grain(res, seed, amt, depth):
    """THE SURFACE GRAIN every pane carries. Rolled, drawn and cathedral glass
    all have a fine tooth; without it a pane is a dead flat plate. It also does
    the measurable work: the shaped treatments above (slump, ripple, reamy) vary
    smoothly ACROSS a pane, so they carry no energy above the 18px scale the
    micro-contrast gate reads — this does, at 4-9px on the car."""
    if amt <= 0:
        return np.zeros((res, res), np.float32)
    yy, xx = coords(res)
    r = rng(seed, 313)
    g = fbm(res, r, 2, max(8, int(res / 3.2)))            # ~3px cells at WORK
    fine = (g - 0.5) * 2.0
    c = 3.1
    du, dv = frac(xx / c) - 0.5, frac(yy / c) - 0.5
    dome = np.clip(1.0 - 3.6 * (du * du + dv * dv), 0, 1)
    hh = frac(np.sin(np.floor(xx / c) * 91.7 + np.floor(yy / c) * 233.3) * 43758.5453)
    tooth = (hh - 0.5) * dome
    keep = np.clip(depth / 2.0, 0.0, 1.0)                 # not on the came itself
    return ((fine * 0.55 + tooth * 0.85) * float(amt) * keep).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# CAME TREATMENTS — the lead is an identity axis, not a 2px outline
# ════════════════════════════════════════════════════════════════════════════

_CAMES = {
    #  name          width  core rgb          shoulder rgb        shoulder
    "hairline":     (1.10, (222, 244, 255), (255, 255, 255), 0.30),
    "lead":         (2.40, (150, 168, 186), (238, 248, 255), 0.55),
    "fatlead":      (3.60, (108, 122, 140), (226, 240, 252), 0.62),
    "bevel":        (2.20, (198, 222, 245), (255, 255, 255), 0.95),
    "foil":         (1.90, (196, 132, 74), (255, 226, 176), 0.70),
    "brass":        (2.30, (176, 146, 62), (255, 240, 178), 0.66),
    "dalle":        (5.20, (26, 26, 30), (120, 132, 148), 0.42),
    "double":       (3.20, (40, 44, 52), (236, 248, 255), 0.85),
    "wire":         (1.60, (128, 140, 152), (216, 232, 246), 0.50),
    "smoke":        (2.60, (58, 62, 72), (150, 168, 190), 0.40),
}


def _came_mask(depth, width, res):
    """Soft came profile from the in-pane distance field (1 on the lead, 0 in glass)."""
    w = float(width) * res / GEN
    return np.clip(1.0 - depth / max(w, 1e-3), 0.0, 1.0) ** 1.35


# ════════════════════════════════════════════════════════════════════════════
# THE ASSEMBLER
# ════════════════════════════════════════════════════════════════════════════

def glass_art(labels, recipe, res):
    """labels (int, res x res) + recipe -> RGB float 0..1. The look IS the art;
    fracture_spec then ignites the seams from this same geometry."""
    seed = int(recipe.get("seed", 7))
    pal = np.asarray(recipe["palette"], np.float32) / 255.0
    lab = upscale_labels(np.asarray(labels, np.int64), res)   # see glass_spec
    bnd = boundary(lab)
    depth = pane_depth(bnd)

    # ---- pane bodies: palette hue x 8-tier shade, per pane -------------------
    P = max(1, len(pal))
    hs = h1(lab, 1)
    idx = np.clip((hs * P).astype(np.int64), 0, P - 1)
    tier = _TIERS[np.clip((h1(lab, 2) * 8).astype(np.int64), 0, 7)]
    body = pal[idx] * tier[..., None]

    # per-pane hue jitter so no two panes of the same palette entry are twins
    jit = float(recipe.get("hue_jit", 0.05))
    if jit > 0:
        hsv = cv2.cvtColor(np.clip(body, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + (h1(lab, 4) - 0.5) * jit * 360.0, 360.0)
        hsv[..., 1] = np.clip(hsv[..., 1] * (0.85 + 0.30 * h1(lab, 6)), 0, 1)
        body = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    # ---- pane treatment ------------------------------------------------------
    tex = _pane_texture(recipe.get("pane", "flat"), res, depth, lab, seed,
                        float(recipe.get("pane_amt", 0.22)))
    tex = tex + glass_grain(res, seed, float(recipe.get("grain", 0.30)), depth)
    body = body * (1.0 + tex[..., None])

    # iridised film: a thin-film hue drift across the pane (the only treatment
    # that moves hue rather than luminance)
    if recipe.get("pane") == "iris":
        d = depth / max(float(depth.max()), 1e-6)
        hsv = cv2.cvtColor(np.clip(body, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
        hsv[..., 0] = np.mod(hsv[..., 0] + np.sin(d * 7.0 + h1(lab, 8) * _TAU) * 26.0, 360.0)
        body = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    # ---- glass depth: the pane darkens into the lead -------------------------
    dg = float(recipe.get("depth", 0.30))
    if dg > 0:
        shade = 1.0 - dg * np.clip(1.0 - depth / (7.0 * res / GEN), 0.0, 1.0)
        body = body * shade[..., None]

    # ---- the came ------------------------------------------------------------
    cname = recipe.get("came", "lead")
    width, core, shoulder, sh_amt = _CAMES.get(cname, _CAMES["lead"])
    width = float(recipe.get("came_w", width))
    cm = _came_mask(depth, width, res)
    core_rgb = np.asarray(recipe.get("came_rgb", core), np.float32) / 255.0
    sh_rgb = np.asarray(shoulder, np.float32) / 255.0
    # shoulder = the lit inner lip of the lead; core = the metal itself
    lip = np.clip((cm - 0.42) / 0.30, 0.0, 1.0) if cname == "bevel" else \
        np.clip(1.0 - np.abs(cm - 0.55) / 0.34, 0.0, 1.0)
    lead = core_rgb[None, None, :] * (1.0 - lip * sh_amt)[..., None] + \
        sh_rgb[None, None, :] * (lip * sh_amt)[..., None]
    out = body * (1.0 - cm[..., None]) + lead * cm[..., None]

    if cname == "double":                    # a bright hairline down the middle of the lead
        mid = np.clip(1.0 - np.abs(cm - 0.92) / 0.10, 0.0, 1.0)
        out = out * (1.0 - mid[..., None]) + sh_rgb[None, None, :] * mid[..., None]

    return np.clip(out, 0.0, 1.0).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# THE GLASSWORK SPEC LAYER
# ════════════════════════════════════════════════════════════════════════════
#
# `fracture_spec` alone is what ignites the seams — that is the half of the look
# the owner already loves and it stays untouched underneath. But measured on the
# reference itself, `ff_truchet_glass` ships spec channel sigma of 7 / 20 / 2:
# the clearcoat is very nearly a constant. That is a real weakness, not a bar.
#
# The physics gives the fix for free. A leaded window is TWO materials:
#   * the came is METAL — high metallic, low roughness, tight clearcoat;
#   * the panes are DIELECTRIC glass — near-zero metallic, glossy, deep clear.
# And no two panes in a real window are the same glass, so each pane draws a
# GLASS TYPE (clear / opal / flashed / mirrored / textured / smoked), which is
# where the M/R/Cc variance comes from. The layer rides the finish's own label
# map, so the spec follows the tiling exactly.

#                      M     R     Cc
_GLASS = np.array([[  8.0,  26.0,  18.0],   # clear   — deep gloss, dielectric
                   [ 20.0, 104.0, 118.0],   # opal    — milky, softer, duller clear
                   [ 40.0,  46.0,  56.0],   # flashed — two-layer, slight sheen
                   [226.0,  16.0,  22.0],   # mirrored— silvered back, hard clear
                   [ 14.0, 150.0, 176.0],   # textured— rolled surface, scattered
                   [ 28.0,  70.0, 214.0]],  # smoked  — dead clearcoat
                  np.float32)

# ════════════════════════════════════════════════════════════════════════════
# THE MATERIAL DECK  (owner, 2026-08-31)
# ════════════════════════════════════════════════════════════════════════════
# Owner: *"the spec channel colors are not diverse enough ... I'd LIKE to see
# many other states created inside of these specs. Where side-by-side lives
# chrome, pearl, mercury, candy, metallic, flat, clear matte, wet look,
# clearcoat, gloss carbon, milk glass, frozen, etc ... so many different types
# of material looks firing on the car at one time its a shock to the system."*
#
# Six glass states could never do that — they sit in one corner of the material
# cube, so the Combined map came out as one colour family. These are the EXACT
# production cards from Spec Guide v1 §5, which is the whole cube: the deep
# greens of the dielectric gloss ladder, the bright and deep reds of the chrome
# and metal tiers, the magentas of the Fractured carrier, the cyans of the dead
# films. A pane draws one COMPLETE card; nothing is ever interpolated between
# two of them (§8).
MATERIALS = {
    # ── dielectric: the green end of the Combined map (D-01 … D-11) ────────
    "liquid_glaze":   (0, 15, 16),      "wet":            (0, 22, 16),
    "gloss":          (0, 30, 16),      "soft_gloss":     (0, 42, 22),
    "semi_gloss":     (0, 55, 40),      "satin":          (0, 95, 70),
    "vinyl":          (0, 100, 110),    "eggshell":       (0, 130, 100),
    "matte":          (0, 200, 160),    "clear_matte":    (0, 220, 210),
    "flat":           (0, 248, 220),
    # ── metal + chrome: the reds, from pearl through mercury (M-01 … M-16) ─
    "pearl":          (100, 40, 16),    "anodized":       (170, 80, 140),
    "brushed_ti":     (180, 70, 16),    "metallic":       (200, 50, 16),
    "gunmetal":       (220, 40, 16),    "galvanized":     (195, 65, 30),
    "antique_chrome": (220, 18, 50),    "dark_chrome":    (250, 15, 40),
    "chrome":         (255, 2, 16),     "satin_chrome":   (250, 45, 40),
    "mercury":        (255, 3, 16),     "candy":          (200, 15, 16),
    "candy_chrome":   (250, 4, 16),     "spectraflame":   (245, 15, 16),
    "frozen_metal":   (225, 140, 100),  "bead_blast":     (180, 160, 140),
    # ── composite + specialty (C-01 … C-10) ────────────────────────────────
    "gloss_carbon":   (55, 30, 16),     "satin_carbon":   (55, 110, 120),
    "fiberglass":     (0, 55, 30),      "powder":         (10, 120, 145),
    "ceramic_gloss":  (10, 15, 16),     "ceramic_matte":  (10, 195, 160),
    "sea_glass":      (0, 55, 40),      "milk_glass":     (0, 45, 30),
    "patina":         (80, 120, 140),   "frozen_film":    (160, 85, 130),
    # ── the Fractured carrier rail, FR-01 (the pinks) ──────────────────────
    "carrier_a":      (242, 78, 246),   "carrier_b":      (252, 30, 255),
    "carrier_c":      (255, 22, 255),
    # ── the cames themselves: lead, foil, brass, concrete are materials too ─
    "came_hairline":  (196, 40, 30),    "came_lead":      (188, 62, 44),
    "came_fatlead":   (176, 78, 52),    "came_bevel":     (236, 16, 20),
    "came_foil":      (222, 34, 28),    "came_brass":     (232, 30, 26),
    "came_dalle":     (24, 208, 190),   "came_double":    (208, 44, 34),
    "came_wire":      (198, 70, 48),    "came_smoke":     (150, 96, 74),
    # ── the six original glass states, kept so old recipes still resolve ───
    "clear":          (8, 26, 18),      "opal":           (20, 104, 118),
    "flashed":        (40, 46, 56),     "mirrored":       (226, 16, 22),
    "textured":       (14, 150, 176),   "smoked":         (28, 70, 214),
}

# Families exist so a deck can be REQUIRED to span the cube rather than
# happening to. A window that draws six cards all from `dielectric` is the old
# problem wearing new names.
FAMILIES = {
    "dielectric": ("liquid_glaze", "wet", "gloss", "soft_gloss", "semi_gloss",
                   "satin", "clear", "flashed", "sea_glass", "milk_glass"),
    "dead":       ("vinyl", "eggshell", "matte", "clear_matte", "flat",
                   "ceramic_matte", "powder", "textured", "smoked", "opal"),
    "metal":      ("pearl", "anodized", "brushed_ti", "metallic", "gunmetal",
                   "galvanized", "frozen_metal", "bead_blast", "patina",
                   "frozen_film", "candy"),
    "chrome":     ("antique_chrome", "dark_chrome", "chrome", "satin_chrome",
                   "mercury", "candy_chrome", "spectraflame", "mirrored"),
    "composite":  ("gloss_carbon", "satin_carbon", "fiberglass", "ceramic_gloss"),
    "carrier":    ("carrier_a", "carrier_b", "carrier_c"),
    # never dealt into a pane hand - the came is chosen by the recipe - but
    # present so the material classifier can name what it is looking at
    "came":       ("came_hairline", "came_lead", "came_fatlead", "came_bevel",
                   "came_foil", "came_brass", "came_dalle", "came_double",
                   "came_wire", "came_smoke"),
}
_FAM_ORDER = ("dielectric", "dead", "metal", "chrome", "composite", "carrier")

# How much of a window each family should claim. Chrome and carrier are the
# loud ones — enough that they read across a whole car, not so much that the
# livery becomes a mirror ball.
_FAM_WEIGHT = {"dielectric": 3, "dead": 3, "metal": 3, "chrome": 2,
               "composite": 2, "carrier": 2}


def material_deck(recipe, seed, size=13):
    """The per-finish hand of material cards, as an (N,3) float array.

    Built to GUARANTEE family spread: every family contributes before any
    family repeats, and the finish's own declared glass states are dealt in
    first so its authored character survives. A recipe can override the whole
    thing with `materials=[...]` when a card wants an exact hand.
    """
    named = recipe.get("materials")
    if named:
        return np.asarray([MATERIALS[n] for n in named], np.float32), list(named)

    rng = np.random.default_rng((int(seed) * 2654435761) & 0x7FFFFFFF)
    hand = []
    # the finish's authored glass character leads
    for i in recipe.get("glass", (0, 1, 2, 3, 4)):
        nm = ("clear", "opal", "flashed", "mirrored", "textured", "smoked")[int(i) % 6]
        if nm not in hand:
            hand.append(nm)
    # then one card from every family, so the hand always spans the cube
    for fam in _FAM_ORDER:
        pool = [n for n in FAMILIES[fam] if n not in hand]
        if pool:
            hand.append(pool[int(rng.integers(len(pool)))])
    # then fill by family weight until the hand is `size` cards, with the loud
    # tiers capped: four chrome cards in one hand hands a third of the car to
    # specular white, which is a mirror ball, not a window.
    cap = {"chrome": 2, "carrier": 3}
    fams = [f for f in _FAM_ORDER for _ in range(_FAM_WEIGHT[f])]
    guard = 0
    while len(hand) < int(size) and guard < 200:
        guard += 1
        fam = fams[int(rng.integers(len(fams)))]
        if fam in cap and sum(1 for n in hand if n in FAMILIES[fam]) >= cap[fam]:
            continue
        pool = [n for n in FAMILIES[fam] if n not in hand]
        if pool:
            hand.append(pool[int(rng.integers(len(pool)))])
    return np.asarray([MATERIALS[n] for n in hand], np.float32), hand

_CAME_SPEC = {           # M,   R,   Cc  — the metal of the came itself
    "hairline": (196.0, 40.0, 30.0), "lead": (188.0, 62.0, 44.0),
    "fatlead": (176.0, 78.0, 52.0), "bevel": (236.0, 16.0, 20.0),
    "foil": (222.0, 34.0, 28.0), "brass": (232.0, 30.0, 26.0),
    "dalle": (24.0, 208.0, 190.0), "double": (208.0, 44.0, 34.0),
    "wire": (198.0, 70.0, 48.0), "smoke": (150.0, 96.0, 74.0),
}


def glass_spec(base_spec, labels, recipe, res, glass_mix=0.92):
    """Lay the glass/came material layer over the fracture ignition.

    The material target is built at WORK and resized to the render size: the
    boundary scan and distance transform are the expensive half, and running
    them at 2048 was putting the heavier tilings on the 3s line for no visible
    gain (the plates are piecewise constant; the came edge wants the softening
    anyway)."""
    if res > WORK:
        small = glass_spec(np.zeros((WORK, WORK, 4), np.uint8),
                           upscale_labels(labels, WORK), recipe, WORK, glass_mix=1.0)
        # NEAREST, not LINEAR: this is a piecewise-constant STATE map, and
        # interpolating between two complete cards invents a material that is
        # in neither of them along every single pane boundary (Spec Guide v1
        # section 8: never smear tuples together).
        tgt = cv2.resize(small[..., :3], (res, res), interpolation=cv2.INTER_NEAREST)
        out = np.asarray(base_spec, np.float32).copy()
        k = float(recipe.get("glass_mix", glass_mix))
        out[..., :3] = out[..., :3] * (1.0 - k) + tgt.astype(np.float32) * k
        return np.clip(out, 0, 255).astype(np.uint8)
    # [SPB-TESSERA-FIX 2026-08-30, owner: "thumbnail previews won't load nor will
    #  the finishes themselves"] Labels arrive at GEN (768). The res > WORK branch
    #  above upscales them; THIS branch used to consume them raw, so every render
    #  at or below WORK — which is every swatch (48/256) and every 1024 preview —
    #  died with "operands could not be broadcast together with shapes
    #  (1024,1024,3) (768,768,3)". Only the 2048 car render, the one size the
    #  build gates measured, took the branch that resized. Normalise here (and in
    #  glass_art) so the label map is ALWAYS at the size being rendered.
    lab = upscale_labels(np.asarray(labels, np.int64), res)
    bnd = boundary(lab)
    depth = pane_depth(bnd)
    out = np.asarray(base_spec, np.float32).copy()

    # ONE COMPLETE MATERIAL CARD PER PANE, dealt from a hand that spans the
    # whole cube (see MATERIALS / material_deck). This is the owner's
    # 2026-08-31 note: chrome, pearl, mercury, candy, metallic, flat, clear
    # matte, wet look, gloss carbon, milk glass and frozen all firing at once,
    # instead of six neighbouring glass states that packed into one colour.
    deck, _names = material_deck(recipe, recipe.get("seed", 7), int(recipe.get("deck", 13)))
    pick = np.clip((h1(lab, 17) * len(deck)).astype(np.int64), 0, len(deck) - 1)
    tgt = deck[pick]                                         # HxWx3 pane targets

    # A second, independent draw re-deals a minority of panes so the hand does
    # not read as a fixed rotation around the tiling — real leaded glass is
    # sorted by what was in the rack, not by a pattern.
    redeal = h1(lab, 53) < float(recipe.get("redeal", 0.34))
    if redeal.any():
        alt = deck[np.clip((h1(lab, 89) * len(deck)).astype(np.int64), 0, len(deck) - 1)]
        tgt = np.where(redeal[..., None], alt, tgt)

    width, *_ = _CAMES.get(recipe.get("came", "lead"), _CAMES["lead"])
    width = float(recipe.get("came_w", width))
    cm = _came_mask(depth, width, res)                       # 1 on the lead
    cs = np.asarray(_CAME_SPEC.get(recipe.get("came", "lead"), _CAME_SPEC["lead"]), np.float32)
    # The came takes its material HARD. Lead meets glass at an edge, not a
    # gradient, and a soft mask interpolates between two complete cards along
    # the whole length of every came — which on a fat came (dalle-de-verre) is
    # a large share of the surface sitting between two materials, belonging to
    # neither. The soft mask is still used below for the roughness shoulder,
    # where a gradient is physically right.
    cm_hard = (cm > 0.5).astype(np.float32)
    tgt = tgt * (1.0 - cm_hard[..., None]) + cs[None, None, :] * cm_hard[..., None]

    # glass thins toward the came -> a touch rougher at the edge of every pane
    edge = np.clip(1.0 - depth / (6.0 * res / GEN), 0.0, 1.0)
    # ...but never roughen a mirror: +34 on a chrome pane's roughness of 2 is
    # the difference between M-09 Chrome and a satin nothing.
    _soft = (tgt[..., 0] < 235.0).astype(np.float32)
    tgt[..., 1] = tgt[..., 1] + 34.0 * edge * (1.0 - cm) * _soft

    k = float(recipe.get("glass_mix", glass_mix))
    out[..., :3] = out[..., :3] * (1.0 - k) + tgt * k

    # IDENTITY LOCK. Chrome tier and Fractured carrier are defined by EXTREME
    # values - chrome is roughness 2, the carrier is clearcoat 255. Blending
    # even a tenth of the ignition into them drags roughness to ~40 and the
    # pane stops being chrome at all, which is how a hand of thirteen distinct
    # cards still rendered as one colour family. These two tiers take their
    # card exactly; everything else keeps the ignition's fine modulation.
    hard = ((tgt[..., 0] >= 235.0) | (tgt[..., 2] >= 240.0)) & (cm < 0.5)
    out[..., :3] = np.where(hard[..., None], tgt, out[..., :3])
    return iron_safe(out)


def iron_safe(spec):
    """Spec Guide v1 section 3 legality: roughness floors at 15 unless the pixel
    is chrome tier (M >= 240), and an ACTIVE clearcoat may never land in the
    illegal 1..15 band. With a deck this wide the deal can now produce both."""
    s = np.asarray(spec, np.float32)
    mirror = s[..., 0] >= 240.0
    s[..., 1] = np.where(mirror, s[..., 1], np.clip(s[..., 1], 15, 255))
    cc = s[..., 2]
    s[..., 2] = np.where((cc > 0) & (cc < 16), 16.0, cc)
    return np.clip(s, 0, 255).astype(np.uint8)


def upscale_labels(lab, res):
    """Tilings generate at GEN; labels must be NEAREST-upscaled (never blurred)."""
    if lab.shape[0] == res:
        return lab
    return cv2.resize(lab.astype(np.float32), (res, res),
                      interpolation=cv2.INTER_NEAREST).astype(np.int64)
