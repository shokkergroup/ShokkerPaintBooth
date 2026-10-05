# -*- coding: utf-8 -*-
"""★ MORTAL SHOKK — the 2026-08-31 spec rebuild. 26 finishes, 26 spec designs.

Owner: *"I want the 26 finishes preserved BUT I want the entire spec maps that
go with them totally redone with the new math we have. It still needs to follow
the pattern of the base paint design but we now can do these MUCH better than
the archaic spec patterns we have right now... Try to match the specs to the
base paint. Like MS Zero Hour it has the steel grey with crisis veins — this one
should have frozen look in the spec but with the hot pink (fractured) highlights
and some other specs in there too. EVERY one unique."*

WHAT WAS THERE. All 26 shared ONE algorithm: `_mortal_v2_spec_spice` — two sine
carriers plus a sparse random grid of "crystalline hits" — differing only by a
seed derived from the finish id. Same structure, same material neighbourhood,
26 times. That is the "archaic" the owner means.

WHAT THIS DOES. The paint asset is untouched (it is a baked texture; the owner
wants the finishes preserved). Instead the spec is authored from that texture's
OWN anatomy, in six roles:

    VOID    the darkest field        — what the light should fall into
    GROUND  the dominant mid field   — what the car mostly IS
    FIGURE  the structures on it     — scales, plates, petals, chains
    VEIN    thin bright filaments    — crisis veins, cracks, circuitry
    HOT     the brightest/most saturated accents
    FLASH   a sparse subset of HOT   — the rarest, loudest state

Every finish names a different material card for each role, chosen to match what
its paint is *depicting* — so Zero Hour's steel really is frozen metal with a
carrier-pink crisis vein, Cryo Shard really is milk glass and ice, and Soul
Forge really is hot metal under a wet coat. Roles are found in the paint, so the
spec follows the design by construction rather than by a correlation gate.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.paint_v2 import spec_cards as SC

_TAU = 6.283185307179586


# ════════════════════════════════════════════════════════════════════════════
# READING THE PAINT — the six roles, found in the texture itself
# ════════════════════════════════════════════════════════════════════════════

def _luma(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)


def _chroma(rgb):
    mx = rgb.max(2)
    mn = rgb.min(2)
    return (mx - mn).astype(np.float32)


def _pct(a, lo=1.0, hi=99.0):
    a = np.asarray(a, np.float32)
    p0, p1 = np.percentile(a, lo), np.percentile(a, hi)
    return np.clip((a - p0) / max(p1 - p0, 1e-6), 0.0, 1.0).astype(np.float32)


def roles(rgb, recipe, seed):
    """Split the paint into the six material roles as soft 0..1 masks.

    Thresholds are PERCENTILES of this finish's own histogram, never absolute
    levels — a bone-white plate and a shadow-wraith black have nothing in
    common on an absolute scale, and an absolute cut would hand one of them
    every role and the other none.
    """
    L = _luma(rgb)
    C = _chroma(rgb)
    if rgb.max() > 1.5:
        L = L / 255.0
        C = C / 255.0

    # WHICH FIELD CARRIES THE DESIGN? Some of these liveries are built in
    # brightness (a bone plate with shadow ribs) and some are built in COLOUR at
    # nearly constant brightness (venom eclipse, thunder mandala, the flame
    # chains on dark metal). Cutting roles out of luma on a chroma-led livery
    # finds nothing, and the spec then ignores the artwork entirely — measured:
    # those four scored 0.03-0.19 on the follow test while luma-led siblings
    # scored 0.5-0.8. So weight the two by how much STRUCTURE each actually
    # holds, per finish, and cut the roles from that combined field.
    Cn = _pct(C)
    lead = recipe.get("lead", "auto")
    if lead == "luma":
        wl, wc = 1.0, 0.0
    elif lead == "chroma":
        wl, wc = 0.25, 0.75
    elif cv2 is not None:
        el = float(np.abs(cv2.Laplacian(cv2.GaussianBlur(L, (0, 0), 1.4), cv2.CV_32F)).mean())
        ec = float(np.abs(cv2.Laplacian(cv2.GaussianBlur(Cn, (0, 0), 1.4), cv2.CV_32F)).mean())
        wc = float(np.clip(ec / max(el + ec, 1e-6), 0.15, 0.80))
        wl = 1.0 - wc
    else:
        wl, wc = 1.0, 0.0
    F = np.clip(L * wl + Cn * wc, 0.0, 1.0).astype(np.float32)

    q = list(recipe.get("cuts", (14.0, 52.0, 82.0, 95.0)))    # void / ground / figure / hot

    # SPEND THE ROLES WHERE THE IMAGE HAS CONTRAST. Equal-area percentile cuts
    # are wrong for a high-contrast painting: Chainburst Inferno's median luma
    # is 0.078, so a 14/52/82 split put three of its four roles INSIDE the black
    # — all landing on pixels that are visually identical — and left the chains
    # to a single role. Its spec then tracked the artwork at 0.046 against a
    # control floor of 0.04, i.e. not at all. So find the level below which the
    # image is simply dark, give all of that to VOID, and spread the remaining
    # roles across the range that actually carries the design.
    lo, hi = float(np.percentile(F, 0.5)), float(np.percentile(F, 99.5))
    floor_v = lo + 0.12 * max(hi - lo, 1e-6)
    floor_pct = float((F <= floor_v).mean() * 100.0)
    # NO ROLE MAY OWN THE WHOLE SURFACE. On a near-uniform black plate the floor
    # logic below hands 95% of the canvas to VOID, which leaves the other five
    # roles ~1% each — under the 1.5% area threshold, so the finish reports ONE
    # material and has no story at all (vm_mosaic_jaguar: 8 cards, 1 family).
    # Capping the void share forces the dark itself to carry material variation,
    # which is also true to the object: obsidian's black is sheen, not flatness.
    floor_pct = min(floor_pct, float(recipe.get("void_max", 100.0)))
    if floor_pct > q[0]:
        span = 100.0 - floor_pct
        q = [floor_pct] + [floor_pct + span * ((x - q[0]) / max(100.0 - q[0], 1e-6))
                           for x in q[1:]]
    kv, kg, kf, kh = (float(np.percentile(F, min(x, 99.6))) for x in q)

    soft = float(recipe.get("soft", 0.045))
    ramp = lambda x, a: np.clip((x - a) / max(soft, 1e-4), 0.0, 1.0)

    void = 1.0 - ramp(F, kv)
    ground = ramp(F, kv) * (1.0 - ramp(F, kg))
    figure = ramp(F, kg) * (1.0 - ramp(F, kf))
    hot = ramp(F, kf)

    # VEINS are thin bright filaments, not merely bright area: a ridge filter
    # (bright minus its own morphological opening) finds the crisis veins,
    # cracks and circuitry that these liveries are actually made of, and
    # ignores broad highlights.
    vein = np.zeros_like(L)
    if cv2 is not None:
        k = max(3, int(recipe.get("vein_px", 9)) | 1)
        opened = cv2.morphologyEx(F, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        vein = _pct(np.clip(F - opened, 0, None)) ** float(recipe.get("vein_gamma", 0.65))
        vein = vein * float(recipe.get("vein", 1.0))

    # FLASH: the rarest, loudest state — the top of the hot role, thinned by a
    # per-finish stochastic field so it lands as sparse hits, not a solid cap.
    flash = np.zeros_like(L)
    fr = float(recipe.get("flash", 0.0))
    if fr > 0 and cv2 is not None:
        rng = np.random.default_rng((int(seed) * 977) & 0x7FFFFFFF)
        g = rng.random((max(8, L.shape[0] // 6), max(8, L.shape[1] // 6))).astype(np.float32)
        g = cv2.resize(g, (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
        flash = ((g > (1.0 - fr)) & (F >= kh)).astype(np.float32)
        flash = cv2.GaussianBlur(flash, (0, 0), 0.8)

    # A saturated-colour role, for liveries whose story is in the chroma
    # (venom greens, jade souls, acid mists) rather than in the luminance.
    # It is an ACCENT, cut at a percentile like every other role — as a
    # continuous ramp it covered almost the whole canvas on the liveries that
    # are saturated everywhere (flame chains, dragon gold), burying the void /
    # ground / figure anatomy underneath one card and dropping those finishes
    # to a follow score of 0.05 against a control noise floor of 0.04.
    Cn2 = _pct(C)
    ks = float(np.percentile(Cn2, float(recipe.get("sat_cut", 74.0))))
    sat = ramp(Cn2, ks) ** float(recipe.get("sat_gamma", 0.8))

    return dict(void=void, ground=ground, figure=figure, hot=hot,
                vein=np.clip(vein, 0, 1), flash=np.clip(flash, 0, 1),
                sat=np.clip(sat, 0, 1), L=L, C=C, F=F)


# ════════════════════════════════════════════════════════════════════════════
# PAINTING THE MATERIAL
# ════════════════════════════════════════════════════════════════════════════

def _grain(shape, seed, scale, amt):
    """Fine per-material grain so no card lands as a dead flat plate. Applied to
    roughness only — the channel where real surfaces genuinely vary most."""
    if cv2 is None or amt <= 0:
        return np.zeros(shape, np.float32)
    rng = np.random.default_rng((int(seed) * 7919) & 0x7FFFFFFF)
    n = max(4, int(scale))
    g = rng.random((n, n)).astype(np.float32)
    g = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return (g - 0.5) * 2.0 * float(amt)


def build_spec(rgb, recipe, seed, sm=1.0):
    """The finished M/R/Cc for one MORTAL SHOKK finish.

    Roles are painted in order of increasing rarity, so the loud states win:
    void, ground and figure lay the field; the saturated role tints it; veins
    cut through everything; hot and flash sit on top.
    """
    x = np.asarray(rgb, np.float32)
    if x.max() > 1.5:
        x = x / 255.0
    h, w = x.shape[:2]
    R = roles(x, recipe, seed)

    out = np.zeros((h, w, 3), np.float32)
    out[:] = SC.card(recipe["ground"])[None, None, :]

    def lay(mask, name, gain=1.0):
        if not name:
            return
        m = np.clip(np.asarray(mask, np.float32) * float(gain), 0.0, 1.0)[..., None]
        out[:] = out * (1.0 - m) + SC.card(name)[None, None, :] * m

    lay(R["void"], recipe.get("void"))
    lay(R["figure"], recipe.get("figure"))
    if recipe.get("sat"):
        lay(R["sat"], recipe["sat"], recipe.get("sat_gain", 0.7))
    lay(R["vein"], recipe.get("vein_card"), recipe.get("vein_gain", 1.0))
    lay(R["hot"], recipe.get("hot"))
    lay(R["flash"], recipe.get("flash_card"))

    # ── fine per-role grain, roughness only ────────────────────────────────
    g = _grain((h, w), seed, recipe.get("grain_scale", 220), recipe.get("grain", 16.0))
    out[..., 1] = out[..., 1] + g * (1.0 - R["void"] * 0.6)

    # ── the clearcoat structure is OFFSET from the metal/roughness structure,
    #    so the two specular lobes peak at different view angles (Spec Guide
    #    v1 §8). Cloned channels look synthetic and travel as one lobe.
    off = int(recipe.get("cc_offset", max(2, h // 420)))
    if off:
        out[..., 2] = np.roll(np.roll(out[..., 2], off, 0), -off, 1)

    # ── chrome and carrier are defined by EXTREME values; any blend drags them
    #    out of their tier. Re-assert them where they were meant to land.
    for role, name in (("vein", recipe.get("vein_card")), ("hot", recipe.get("hot")),
                       ("flash", recipe.get("flash_card"))):
        if not name:
            continue
        c = SC.CARDS[name]
        if c[0] >= 235 or c[2] >= 240:
            hard = R[role] > 0.62
            if hard.any():
                out[hard] = SC.card(name)

    out[..., 0] = np.clip(out[..., 0] * float(sm), 0, 255)
    return SC.iron_safe(out)


# ════════════════════════════════════════════════════════════════════════════
# THE 26 — one bespoke material anatomy each
# ════════════════════════════════════════════════════════════════════════════
# Read each row as a sentence: "the dark is X, the body is Y, the structures
# are Z, the veins are W, and the hottest points flash to V."
R = dict

MORTAL_SHOKK_SPECS = {

    # steel grey with last-second crisis veins — the owner's worked example
    "ms_zero_hour": R(
        void="flat_black", ground="frozen_metal", figure="gunmetal",
        sat=None, vein_card="carrier_high", hot="dark_chrome",
        flash_card="chrome", flash=0.16, vein_px=7, vein=1.15, grain=22,
        note="frozen steel, crisis veins ignited to the carrier, chrome at the breaks"),

    # acid mist veil hiding chrome strike zones
    "ms_acid_veil_ambush": R(
        void="void", ground="ceramic_matte", figure="satin_carbon",
        sat="anodized", sat_gain=0.85, vein_card="carrier_mid", hot="chrome",
        flash_card="mercury", flash=0.10, vein_px=11, grain=13,
        note="dead acid haze that the strike zones cut through as mirror"),

    # regal deep crimson, imperial gold edges
    "ms_blood_empress": R(
        void="flat_black", ground="candy", figure="metallic",
        sat="candy_chrome", sat_gain=0.55, vein_card="spectraflame", hot="dark_chrome",
        flash_card="mercury", flash=0.07, vein_px=13, grain=10,
        note="candy over lacquer with a spectraflame edge — regalia, not armour"),

    # bone-white plate, melodic shadow ribs
    "ms_bone_sonata": R(
        void="ceramic_matte", ground="milk_glass", figure="ceramic_gloss",
        sat=None, vein_card="satin_chrome", hot="pearl",
        flash_card="chrome", flash=0.08, vein_px=15, vein=0.9, grain=18,
        note="milk glass and ceramic — bone reads as glaze, ribs as satin chrome"),

    # cascading flame chains on dark metal
    "ms_chainburst_inferno": R(
        void="flat_black", ground="gunmetal", figure="galvanized",
        sat="spectraflame", sat_gain=0.75, vein_card="carrier_high", hot="candy_chrome",
        flash_card="chrome", flash=0.18, vein_px=7, vein=1.2, grain=20,
        note="chain links as galvanised metal, the burst itself as carrier"),

    # spiralling ember sparks on cooling ash
    "ms_cinder_spiral": R(
        void="void", ground="ceramic_matte", figure="bead_blast",
        sat="candy", sat_gain=0.6, vein_card="dark_chrome", hot="carrier_mid",
        flash_card="spectraflame", flash=0.22, vein_px=9, grain=26,
        note="ash is genuinely dead; only the spiral carries heat"),

    # dragon-scale crimson, shadow-etched boundaries
    "ms_crimson_dragon": R(
        void="flat_black", ground="candy", figure="pearl",
        sat=None, vein_card="gunmetal", hot="candy_chrome",
        flash_card="mercury", flash=0.06, vein_px=17, vein=1.1, grain=12,
        note="scale bodies pearl, the etched boundary a dark metal seam"),

    # frozen cyan shards on glacial substrate
    "ms_cryo_shard": R(
        void="ceramic_matte", ground="milk_glass", figure="sea_glass",
        sat="frozen_metal", sat_gain=0.7, vein_card="liquid_glaze", hot="chrome",
        flash_card="mercury", flash=0.12, vein_px=9, grain=8,
        note="glass first, metal only where the shard edge catches"),

    # faceted crystal assault, prism-edge refraction
    "ms_crystal_onslaught": R(
        void="ceramic_matte", ground="sea_glass", figure="ceramic_gloss",
        sat="frozen_metal", sat_gain=0.55, vein_card="chrome", hot="candy_chrome",
        flash_card="razor", flash=0.20, vein_px=5, vein=1.3, grain=6,
        note="every facet edge is a mirror; the razor is the refraction flash"),

    # ascending dragon gold, flame trails
    "ms_dragon_ascent": R(
        void="flat_black", ground="metallic", figure="spectraflame",
        sat="candy_chrome", sat_gain=0.6, vein_card="carrier_mid", hot="mercury",
        flash_card="chrome", flash=0.10, vein_px=11, grain=14,
        note="gold as spectraflame, the trail as carrier"),

    # soul-ember dragon jade, inner glow channels
    "ms_dragon_soul": R(
        void="flat_black", ground="anodized", figure="patina",
        sat="candy", sat_gain=0.8, vein_card="carrier_high", hot="spectraflame",
        flash_card="chrome", flash=0.09, vein_px=7, vein=1.25, grain=17,
        note="jade as anodised metal; the channels glow as carrier"),

    # emerald scale shimmer that shifts with angle
    "ms_emerald_scale_mirage": R(
        void="satin_carbon", ground="pearl", figure="anodized",
        sat="carrier_low", sat_gain=0.9, vein_card="satin_chrome", hot="candy_chrome",
        flash_card="mercury", flash=0.08, vein_px=13, grain=11,
        note="the mirage IS the carrier — a shifting population, not a gradient"),

    # tooth-shard cataclysm on slate armour
    "ms_fang_cataclysm": R(
        void="void", ground="satin_carbon", figure="bead_blast",
        sat=None, vein_card="chrome", hot="milk_glass",
        flash_card="dark_chrome", flash=0.14, vein_px=7, vein=1.15, grain=24,
        note="slate is composite, the fangs are bone-glass, the cracks mirror"),

    # frozen sentinel blue, vigilant ice crystals
    "ms_frost_sentinel": R(
        void="gloss_carbon", ground="frozen_metal", figure="milk_glass",
        sat="frozen_film", sat_gain=0.75, vein_card="liquid_glaze", hot="chrome",
        flash_card="razor", flash=0.15, vein_px=9, grain=9,
        note="hazed metal ground so the ice reads as the clear thing on it"),

    # paradox blue cold-flame on icefire
    "ms_frozen_inferno": R(
        void="ceramic_matte", ground="milk_glass", figure="frozen_metal",
        sat="carrier_low", sat_gain=0.85, vein_card="candy_chrome", hot="carrier_high",
        flash_card="mercury", flash=0.13, vein_px=7, vein=1.2, grain=12,
        note="the paradox is literal: glass and ice below, carrier fire above"),

    # sacred lotus in pink-gold petals
    "ms_lotus_ascention": R(
        void="ceramic_matte", ground="ceramic_gloss", figure="pearl",
        sat="candy", sat_gain=0.7, vein_card="spectraflame", hot="candy_chrome",
        flash_card="chrome", flash=0.07, vein_px=15, vein=0.85, grain=9,
        note="porcelain petals with gilt veins — the quietest of the 26"),

    # molten metal sting, droplet flares
    "ms_molten_sting": R(
        void="flat_black", ground="metallic", figure="galvanized",
        sat="spectraflame", sat_gain=0.8, vein_card="carrier_high", hot="mercury",
        flash_card="chrome", flash=0.20, vein_px=5, vein=1.3, grain=19,
        note="droplets flash to liquid mirror; the sting is the carrier vein"),

    # encoded porcelain glaze, cipher-line crackles
    "ms_porcelain_cipher": R(
        void="satin_carbon", ground="ceramic_gloss", figure="milk_glass",
        sat=None, vein_card="dark_chrome", hot="gloss",
        flash_card="carrier_mid", flash=0.11, vein_px=5, vein=1.35, grain=7,
        note="the crackle IS the cipher — thin, hard, and metallic in the glaze"),

    # toxic serpent haze, venom-strike accents
    "ms_serpent_haze_strike": R(
        void="void", ground="ceramic_matte", figure="anodized",
        sat="candy", sat_gain=0.9, vein_card="carrier_mid", hot="candy_chrome",
        flash_card="chrome", flash=0.12, vein_px=11, grain=21,
        note="haze genuinely dull so the strike has something to cut"),

    # spectral wraith-black with a faint shadow duplicate
    "ms_shadow_wraith": R(
        void="void", ground="flat_black", figure="gloss_carbon",
        sat=None, vein_card="carrier_low", hot="satin_chrome",
        flash_card="chrome", flash=0.05, vein_px=13, vein=0.8, grain=14,
        cuts=(8.0, 46.0, 86.0, 97.0),
        note="almost invisible by design — the whole card lives in the dead tiers"),

    # forged amber with soul-ember inner glow
    "ms_soul_forge": R(
        void="patina", ground="brushed_ti", figure="bead_blast",
        sat="candy", sat_gain=0.75, vein_card="carrier_high", hot="spectraflame",
        flash_card="mercury", flash=0.14, vein_px=7, vein=1.2, grain=20,
        note="brushed metal that has been in a fire; the glow is under the skin"),

    # storm-crown tempest blue, lightning crown veins
    "ms_tempest_crown": R(
        void="flat_black", ground="gunmetal", figure="frozen_film",
        sat="anodized", sat_gain=0.7, vein_card="chrome", hot="carrier_high",
        flash_card="razor", flash=0.19, vein_px=5, vein=1.4, grain=16,
        note="lightning must be the hardest edge on the car — chrome veins, razor flash"),

    # sacred thunder mandala in electric violet
    "ms_thunder_mandala": R(
        void="flat_black", ground="anodized", figure="satin_carbon",
        sat="carrier_mid", sat_gain=0.8, vein_card="candy_chrome", hot="chrome",
        flash_card="razor", flash=0.16, vein_px=7, vein=1.25, grain=12,
        note="the mandala rays as candy chrome over an anodised ground"),

    # toxic neon maze on contaminated substrate
    "ms_toxic_labyrinth": R(
        void="void", ground="powder", figure="patina",
        sat="carrier_mid", sat_gain=0.95, vein_card="candy_chrome", hot="chrome",
        flash_card="spectraflame", flash=0.15, vein_px=5, vein=1.35, grain=23,
        note="powder-coat contamination underneath, neon maze walls on top"),

    # eclipse venom-dark purple with corona shimmer
    "ms_venom_eclipse": R(
        void="void", ground="gloss_carbon", figure="anodized",
        sat="carrier_low", sat_gain=0.85, vein_card="satin_chrome", hot="carrier_high",
        flash_card="mercury", flash=0.10, vein_px=15, vein=0.95, grain=15,
        cuts=(10.0, 50.0, 88.0, 97.0),
        note="a corona is a thin ring of light around a dark disc — keep the disc dark"),

    # venomous veil of serpent green and amethyst poison
    "ms_venom_veil": R(
        void="flat_black", ground="satin_carbon", figure="anodized",
        sat="candy", sat_gain=0.9, vein_card="carrier_mid", hot="candy_chrome",
        flash_card="chrome", flash=0.09, vein_px=11, grain=18,
        note="two poisons, so two saturated populations over a composite ground"),
}
