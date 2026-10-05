# -*- coding: utf-8 -*-
"""THE SPEC CARD LIBRARY — the whole iRacing material cube, in one place.

This is Spec Guide v1 §5 ("Exact production paint cards") as data, plus the
legality rules from §3 and the dealing rules from §7–§9. Every category that
wants real material variety should build on this instead of inventing its own
four-state palette — which is how FRACTURED TESSERA ended up with six glass
states that all sat in one corner of the cube and rendered as a single colour
family (owner, 2026-08-31).

Channel meanings, since they are easy to get backwards:
    M    red   0 dielectric … 255 chrome
    R    green 0 mirror-smooth … 255 dead rough      (floors at 15 unless M≥240)
    Cc   blue  **INVERTED** — 16 is the STRONGEST active clearcoat, 255 is none,
                and 1–15 is an illegal band that must never be authored.

Reading the literal Combined map, which is what the owner sees in the app:
    deep green   dielectric gloss ladder      bright red   chrome tier
    cyan         dead/matte films             deep red     metal, dark chrome
    magenta/pink the Fractured carrier rail   yellow       rough metal, oxide
"""
from __future__ import annotations

import numpy as np

# ════════════════════════════════════════════════════════════════════════════
# THE CARDS
# ════════════════════════════════════════════════════════════════════════════
#   name: (M, Rough, Cc)                       # guide id — what it reads as
CARDS = {
    # ── dielectric paint, lacquer, film (the greens through the cyans) ──────
    "liquid_glaze":   (0, 15, 16),      # D-01  razor wetness
    "wet":            (0, 22, 16),      # D-02  wet lacquer / piano black
    "gloss":          (0, 30, 16),      # D-03  standard glossy body
    "soft_gloss":     (0, 42, 22),      # D-04  controlled gloss
    "semi_gloss":     (0, 55, 40),      # D-05  everyday enamel
    "satin":          (0, 95, 70),      # D-06  satin body film
    "vinyl":          (0, 100, 110),    # D-07  flat vinyl
    "eggshell":       (0, 130, 100),    # D-08  soft diffuse
    "matte":          (0, 200, 160),    # D-09  matte body / primer
    "clear_matte":    (0, 220, 210),    # D-10  very dull film
    "flat_black":     (0, 248, 220),    # D-11  dead flat
    "void":           (0, 255, 240),    # D-12  porous, light-swallowing
    # ── metal, chrome, candy, pearl (the reds) ──────────────────────────────
    "pearl":          (100, 40, 16),    # M-01
    "anodized":       (170, 80, 140),   # M-02  coloured metal, weak coat
    "brushed_ti":     (180, 70, 16),    # M-03
    "metallic":       (200, 50, 16),    # M-04  general body metallic
    "gunmetal":       (220, 40, 16),    # M-05
    "galvanized":     (195, 65, 30),    # M-06  mottled zinc
    "antique_chrome": (220, 18, 50),    # M-07
    "dark_chrome":    (250, 15, 40),    # M-08
    "chrome":         (255, 2, 16),     # M-09  needs near-white albedo
    "satin_chrome":   (250, 45, 40),    # M-10  broader, softer
    "mercury":        (255, 3, 16),     # M-11  extreme liquid mirror
    "candy":          (200, 15, 16),    # M-12  colour lives in the albedo
    "candy_chrome":   (250, 4, 16),     # M-13  bright coloured mirror
    "spectraflame":   (245, 15, 16),    # M-14
    "frozen_metal":   (225, 140, 100),  # M-15  rough, hazed metallic
    "bead_blast":     (180, 160, 140),  # M-16  broad diffuse metal sparkle
    # ── composite and specialty ─────────────────────────────────────────────
    "gloss_carbon":   (55, 30, 16),     # C-01
    "satin_carbon":   (55, 110, 120),   # C-02
    "fiberglass":     (0, 55, 30),      # C-03
    "powder":         (10, 120, 145),   # C-04  orange-peel cells
    "ceramic_gloss":  (10, 15, 16),     # C-05  strong white coat
    "ceramic_matte":  (10, 195, 160),   # C-06  chalky
    "sea_glass":      (0, 55, 40),      # C-07  smooth frosted
    "milk_glass":     (0, 45, 30),      # C-08
    "patina":         (80, 120, 140),   # C-09  mixed oxide / metal
    "frozen_film":    (160, 85, 130),   # C-10  metallic haze
    # ── the Fractured carrier rail, FR-01 (the pinks) ───────────────────────
    #    smooth near-metal with the clearcoat suppressed; this is the population
    #    that thresholds under track light and makes a car "fracture"
    "carrier_low":    (242, 78, 246),
    "carrier_mid":    (252, 30, 255),
    "carrier_high":   (255, 22, 255),
    "razor":          (40, 16, 16),     # FR-02 white clearcoat razor

    # ── C-11..C-16 metals under DIFFERENT COATS (added 2026-09-01) ─────────
    # Owner: "the specs should be diverse". FRACTURED NIGHTSHIFT needs its night
    # population to be chrome-tier (only a metal tints its own reflection, which
    # is the whole day/night hue mechanism), but the seven existing chrome cards
    # span M 220-255, R 2-45, Cc 16-50 — visually one material. Fifty finishes
    # were given hand-authored "distinct" night decks out of that pool and the
    # rendered spec maps still all read as the same sheet of red.
    #
    # These keep M >= 228 so the flip physics is untouched, and vary the COAT
    # instead: clearcoat 16 -> 190 and roughness 2 -> 58. A duller clear also
    # suppresses the white specular lobe, which helps hue retention rather than
    # hurting it (see the whiteout note in fractured_nightshift_2026).
    "mirror_deep":    (255, 6, 70),     # C-11  mirror under a deep coat
    "chrome_veil":    (252, 30, 120),   # C-12  polished metal, hazy clear
    "chrome_dry":     (250, 58, 190),   # C-13  metal with a matte topcoat
    "bronze_raw":     (230, 44, 92),    # C-14  unlacquered alloy
    "pewter_metal":   (236, 52, 150),   # C-15  soft alloy, dull coat
    "steel_dark":     (240, 26, 60),    # C-16  dark brushed steel
}

FAMILIES = {
    "gloss":      ("liquid_glaze", "wet", "gloss", "soft_gloss", "semi_gloss",
                   "ceramic_gloss", "milk_glass", "fiberglass", "sea_glass"),
    "dead":       ("satin", "vinyl", "eggshell", "matte", "clear_matte",
                   "flat_black", "void", "ceramic_matte", "powder"),
    "metal":      ("pearl", "anodized", "brushed_ti", "metallic", "gunmetal",
                   "galvanized", "frozen_metal", "bead_blast", "patina",
                   "frozen_film", "candy"),
    "chrome":     ("antique_chrome", "dark_chrome", "chrome", "satin_chrome",
                   "mercury", "candy_chrome", "spectraflame"),
    "composite":  ("gloss_carbon", "satin_carbon"),
    "carrier":    ("carrier_low", "carrier_mid", "carrier_high", "razor"),
}
FAMILY_OF = {n: f for f, names in FAMILIES.items() for n in names}
FAMILY_ORDER = ("gloss", "dead", "metal", "chrome", "composite", "carrier")

# The loud tiers read across a whole car; too many and the livery is a mirror
# ball or a slab of pink. These are hands-per-deck caps, not area caps.
DEFAULT_CAPS = {"chrome": 2, "carrier": 3}
DEFAULT_WEIGHT = {"gloss": 3, "dead": 3, "metal": 3, "chrome": 2,
                  "composite": 2, "carrier": 2}


def card(name):
    """One card as a float32 (3,) — raises loudly on a typo rather than
    silently substituting something plausible."""
    return np.asarray(CARDS[name], np.float32)


def deck(names):
    """A named hand as an (N,3) float32 array."""
    return np.asarray([CARDS[n] for n in names], np.float32)


def deal(seed, size=13, must=(), avoid=(), caps=None, weight=None):
    """Deal a hand that is GUARANTEED to span the material cube.

    Every family contributes one card before any family repeats, so a hand can
    never collapse into a single neighbourhood — which is the failure mode this
    library exists to prevent. `must` names cards that always appear (a card's
    authored character), `avoid` names cards it must never draw.
    """
    rng = np.random.default_rng((int(seed) * 2654435761) & 0x7FFFFFFF)
    caps = dict(DEFAULT_CAPS if caps is None else caps)
    weight = dict(DEFAULT_WEIGHT if weight is None else weight)
    avoid = set(avoid)
    hand = [n for n in must if n in CARDS and n not in avoid]

    for fam in FAMILY_ORDER:
        pool = [n for n in FAMILIES[fam] if n not in hand and n not in avoid]
        if pool and sum(1 for n in hand if FAMILY_OF.get(n) == fam) < caps.get(fam, 99):
            hand.append(pool[int(rng.integers(len(pool)))])

    fams = [f for f in FAMILY_ORDER for _ in range(weight.get(f, 1))]
    guard = 0
    while len(hand) < int(size) and guard < 400:
        guard += 1
        fam = fams[int(rng.integers(len(fams)))]
        if sum(1 for n in hand if FAMILY_OF.get(n) == fam) >= caps.get(fam, 99):
            continue
        pool = [n for n in FAMILIES[fam] if n not in hand and n not in avoid]
        if pool:
            hand.append(pool[int(rng.integers(len(pool)))])
    return hand


def iron_safe(spec):
    """Spec Guide v1 §3 legality, applied last, always.

    Roughness floors at 15 unless the pixel is chrome tier (M≥240), and an
    ACTIVE clearcoat may never sit in the illegal 1–15 band. Anti-aliasing and
    any blend between two cards will produce both, so this is not optional.
    """
    s = np.asarray(spec, np.float32)
    if s.shape[-1] < 3:
        raise ValueError("spec needs at least 3 channels")
    mirror = s[..., 0] >= 240.0
    s[..., 1] = np.where(mirror, s[..., 1], np.clip(s[..., 1], 15, 255))
    cc = s[..., 2]
    s[..., 2] = np.where((cc > 0) & (cc < 16), 16.0, cc)
    return np.clip(s, 0, 255).astype(np.uint8)


def classify(spec, names=None, stride=7):
    """(share per card, mean drift) — what materials is this spec ACTUALLY
    showing? Used by every gate: deal thirteen cards and it means nothing if
    the pipeline blends them all back toward the middle."""
    keys = list(names or CARDS)
    ref = deck(keys)
    px = np.asarray(spec, np.float32)[..., :3].reshape(-1, 3)[::int(stride)]
    d = ((px[:, None, :] - ref[None, :, :]) ** 2).sum(-1)
    idx = d.argmin(1)
    drift = float(np.sqrt(d[np.arange(idx.size), idx]).mean())
    share = np.bincount(idx, minlength=len(keys)) / float(idx.size)
    return {keys[i]: float(share[i]) for i in range(len(keys))}, drift


def report(spec, min_share=0.015):
    """(live card names, family count, chrome share, drift) for a gate line."""
    share, drift = classify(spec)
    live = [n for n, s in sorted(share.items(), key=lambda kv: -kv[1]) if s >= min_share]
    fams = {FAMILY_OF.get(n, "?") for n in live}
    chrome = sum(s for n, s in share.items() if FAMILY_OF.get(n) == "chrome")
    return live, len(fams), float(chrome), drift
