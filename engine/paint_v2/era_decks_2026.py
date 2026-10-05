# -*- coding: utf-8 -*-
"""🎛 ERA DECKS (2026-08-31) — the material vocabulary for the five new shelves.

Owner: *"Apply the best spec rules possible across the board to make totally
unique finishes. DO NOT just automatically make them all Fractured styles. You
can combine ANY combinations of styles from our catalog to come up with really
unique things across the board. Plenty of stuff with the hot pink Fractured look
(the combined spec look not a base color pink) is fine but it shouldn't revolve
around this. SOME finishes should lean flat, chalky, glossy, wet, GLITTERY —
ALL looks and blends welcome."*

That is a direct instruction about the SPEC, and it is enforceable, so it is
enforced here rather than left to taste. `audit()` reports what share of the
decks reach for the Fractured carrier rail; `CARRIER_SHARE_MAX` is the ceiling
and `tests/` can assert it.

Twenty-six decks spanning the whole material space:

    dead / chalk / powder      flat, no coat at all
    satin / eggshell           a coat, but a soft one
    gloss / wet / glass        a real coat, up to standing water
    glitter / flake / sequin   discrete specular events, not a smooth surface
    metal / chrome / mercury   conductors
    pearl / candy / spectral   layered coats that shift
    rubber / vinyl / plastic   the ones nothing else in the catalog does well
    carrier                    the Fractured rail — a minority, on purpose

Every deck is ordered by DESCENDING roughness so the spec still reads as the
geometry of the thing (the FOLLOW lesson), and every deck spans at least three
material families in its large-area roles (the substrate lesson).
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.paint_v2 import spec_cards as SC

# ── the decks ───────────────────────────────────────────────────────────────
# (card, upper-percentile) — the field is banded by percentile, so the second
# number is "what share of the surface is this material or duller".

DECKS = {
    "chalk":         (("void", 0.28), ("clear_matte", 0.50), ("ceramic_matte", 0.68), ("powder", 0.84), ("satin_carbon", 0.95), ("brushed_ti", 1.01)),
    "suede":         (("clear_matte", 0.28), ("matte", 0.50), ("vinyl", 0.68), ("satin", 0.84), ("pearl", 0.95), ("gloss_carbon", 1.01)),
    "primer":        (("void", 0.28), ("matte", 0.50), ("bead_blast", 0.68), ("powder", 0.84), ("satin_carbon", 0.95), ("brushed_ti", 1.01)),
    "satin":         (("ceramic_matte", 0.28), ("eggshell", 0.50), ("vinyl", 0.68), ("satin", 0.84), ("soft_gloss", 0.95), ("pearl", 1.01)),
    "eggshell":      (("matte", 0.28), ("eggshell", 0.50), ("powder", 0.68), ("satin", 0.84), ("semi_gloss", 0.95), ("metallic", 1.01)),
    "gloss":         (("ceramic_matte", 0.28), ("satin_carbon", 0.50), ("semi_gloss", 0.68), ("soft_gloss", 0.84), ("gloss", 0.95), ("liquid_glaze", 1.01)),
    "wet":           (("satin_carbon", 0.28), ("gloss_carbon", 0.50), ("gloss", 0.68), ("wet", 0.84), ("liquid_glaze", 0.95), ("mercury", 1.01)),
    "glass":         (("frozen_film", 0.28), ("sea_glass", 0.50), ("milk_glass", 0.68), ("gloss_carbon", 0.84), ("wet", 0.95), ("liquid_glaze", 1.01)),
    "lacquer":       (("eggshell", 0.28), ("powder", 0.50), ("soft_gloss", 0.68), ("candy", 0.84), ("candy_chrome", 0.95), ("chrome", 1.01)),
    "glitter":       (("clear_matte", 0.28), ("satin", 0.50), ("pearl", 0.68), ("gloss_carbon", 0.84), ("spectraflame", 0.95), ("chrome", 1.01)),
    "flake":         (("flat_black", 0.28), ("metallic", 0.50), ("gloss_carbon", 0.68), ("candy", 0.84), ("candy_chrome", 0.95), ("chrome", 1.01)),
    "sequin":        (("satin_carbon", 0.28), ("vinyl", 0.50), ("satin_chrome", 0.68), ("pearl", 0.84), ("mercury", 0.95), ("chrome", 1.01)),
    "lurex":         (("satin", 0.28), ("brushed_ti", 0.50), ("metallic", 0.68), ("gloss_carbon", 0.84), ("candy_chrome", 0.95), ("mercury", 1.01)),
    "steel":         (("bead_blast", 0.28), ("satin_carbon", 0.50), ("brushed_ti", 0.68), ("galvanized", 0.84), ("gunmetal", 0.95), ("chrome", 1.01)),
    "chrome":        (("frozen_metal", 0.28), ("sea_glass", 0.50), ("satin_chrome", 0.68), ("gloss_carbon", 0.84), ("mercury", 0.95), ("chrome", 1.01)),
    "gold":          (("ceramic_matte", 0.28), ("patina", 0.50), ("metallic", 0.68), ("gloss_carbon", 0.84), ("candy", 0.95), ("mercury", 1.01)),
    "oxide":         (("void", 0.28), ("ceramic_matte", 0.50), ("patina", 0.68), ("satin_carbon", 0.84), ("galvanized", 0.95), ("antique_chrome", 1.01)),
    "pearl":         (("eggshell", 0.28), ("frozen_film", 0.50), ("milk_glass", 0.68), ("pearl", 0.84), ("spectraflame", 0.95), ("candy_chrome", 1.01)),
    "candy":         (("flat_black", 0.28), ("metallic", 0.50), ("gloss_carbon", 0.68), ("candy", 0.84), ("candy_chrome", 0.95), ("chrome", 1.01)),
    "spectral":      (("frozen_film", 0.28), ("anodized", 0.50), ("milk_glass", 0.68), ("pearl", 0.84), ("spectraflame", 0.95), ("chrome", 1.01)),
    "dichroic":      (("anodized", 0.28), ("sea_glass", 0.50), ("milk_glass", 0.68), ("gloss_carbon", 0.84), ("spectraflame", 0.95), ("candy_chrome", 1.01)),
    "rubber":        (("void", 0.28), ("flat_black", 0.50), ("matte", 0.68), ("satin_carbon", 0.84), ("galvanized", 0.95), ("gloss_carbon", 1.01)),
    "plastic":       (("powder", 0.28), ("satin_carbon", 0.50), ("vinyl", 0.68), ("semi_gloss", 0.84), ("ceramic_gloss", 0.95), ("liquid_glaze", 1.01)),
    "velvet":        (("void", 0.28), ("clear_matte", 0.50), ("matte", 0.68), ("vinyl", 0.84), ("pearl", 0.95), ("spectraflame", 1.01)),
    "neon":          (("flat_black", 0.28), ("satin_carbon", 0.50), ("gloss_carbon", 0.68), ("ceramic_gloss", 0.84), ("liquid_glaze", 0.95), ("spectraflame", 1.01)),
    "carrier":       (("flat_black", 0.28), ("carrier_low", 0.50), ("gloss_carbon", 0.68), ("carrier_mid", 0.84), ("carrier_high", 0.95), ("mercury", 1.01)),
    "carrier_ice":   (("frozen_metal", 0.28), ("carrier_low", 0.50), ("milk_glass", 0.68), ("carrier_mid", 0.84), ("carrier_high", 0.95), ("razor", 1.01)),
}

# Owner: the Fractured look "shouldn't revolve around this". A recipe table that
# reaches for a carrier deck more often than this is not following the brief.
CARRIER_SHARE_MAX = 0.22
CARRIER_DECKS = tuple(k for k, v in DECKS.items()
                      if any(SC.FAMILY_OF[c] == "carrier" for c, _u in v))


def audit(recipes, deck_key="deck"):
    """What share of a recipe table reaches for the Fractured rail, and how many
    distinct decks it uses. Returns (share, n_decks, Counter)."""
    from collections import Counter
    used = Counter(r[deck_key] for r in recipes)
    carrier = sum(n for k, n in used.items() if k in CARRIER_DECKS)
    total = max(sum(used.values()), 1)
    return carrier / total, len(used), used


def check_decks():
    """Every deck must descend in roughness (so the spec reads as geometry) and
    span >= 3 material families. Raises rather than warns."""
    bad = []
    for name, deck in DECKS.items():
        rs = [SC.CARDS[c][1] for c, _u in deck]
        if any(rs[i] < rs[i + 1] - 1 for i in range(len(rs) - 1)):
            bad.append("%s: roughness not descending %s" % (name, rs))
        fams = {SC.FAMILY_OF[c] for c, _u in deck}
        if len(fams) < 3:
            bad.append("%s: only %d families %s" % (name, len(fams), sorted(fams)))
    if bad:
        raise AssertionError("era deck problems:\n  " + "\n  ".join(bad))
    return len(DECKS)


# ════════════════════════════════════════════════════════════════════════════
# FIELD -> SPEC
# ════════════════════════════════════════════════════════════════════════════

def spec_from(field, lab, deck, seed=51, sm=1.0, dither=0.15, r_spread=26.0,
              edge=None, edge_pct=97.6, cc_offset=None, base_m=None, base_r=None,
              cell_mean=1.0):
    """Band a field into complete material cards and return (M, R, Cc) floats.

    This is the same machinery the FLAMES / TESSERA / PARADIGM / WORLD lanes
    proved, adapted to the BASE contract (`base_spec_fn` returns three separate
    channels rather than a packed image):

      * bands are PERCENTILES of this finish's own field, never absolute levels
      * a per-cell hash offset stops six bands over a smooth cell-mean merging
        neighbouring cells into one 80px slab (the SPECBAND lesson)
      * the clearcoat structure is offset from the metal/roughness one, so the
        two specular lobes peak at different view angles (Spec Guide v1 section 8)
      * chrome and carrier are defined by extreme values, so an edge lip takes
        its card exactly rather than being blended toward its neighbours
    """
    from engine.paint_v2.era_kit_2026 import _h1

    f = np.asarray(field, np.float32)
    h, w = f.shape[:2]
    lab = np.asarray(lab)
    # See era_base_2026._art: flattening per cell wipes anything finer than a
    # cell, so screen-like finishes keep their own frequency instead.
    cm = float(cell_mean)
    fc = _cell_mean_safe(f, lab) if cm > 0 else f
    if 0.0 < cm < 1.0:
        fc = fc * cm + f * (1.0 - cm)
    fc = np.clip(fc + (_h1(lab, 61) - 0.5) * float(dither), 0.0, 1.0)

    edges = np.asarray([u for _c, u in deck], np.float32)
    cards = np.asarray([SC.CARDS[c] for c, _u in deck], np.float32)
    qs = np.maximum.accumulate(np.asarray(
        np.percentile(fc[::4, ::4], np.clip(edges * 100.0, 0, 100)), np.float32))
    bi = np.clip(np.searchsorted(qs, fc.ravel(), side="left"), 0, len(deck) - 1)
    out = cards[bi].reshape(h, w, 3)

    if edge and cv2 is not None:
        gy, gx = np.gradient(cv2.GaussianBlur(f, (0, 0), 1.2))
        grad = np.hypot(gx, gy)
        lip = (grad > float(np.percentile(grad[::2, ::2], edge_pct))).astype(np.float32)
        k = int(max(2, w / 700.0))
        lip = cv2.dilate(lip, np.ones((k, k), np.float32))
        out[lip > 0] = SC.card(edge)

    frac = float(r_spread) / 255.0
    out[..., 1] = np.clip(out[..., 1] * (1.0 + (_h1(lab, 173) - 0.5) * 2.0 * frac), 0, 255)
    out[..., 0] = np.clip(out[..., 0] * (0.94 + 0.12 * _h1(lab, 211)), 0, 255)
    off = int(cc_offset if cc_offset is not None else max(2, w // 420))
    if off:
        out[..., 2] = np.roll(np.roll(out[..., 2], off, 0), -off, 1)

    out = SC.iron_safe(out).astype(np.float32)
    # `sm` is the zone's spec-strength dial; it scales the metal channel exactly
    # as the other base renderers do.
    return (np.clip(out[..., 0] * float(sm), 0, 255),
            np.clip(out[..., 1], 15, 255),
            np.clip(out[..., 2], 16, 255))


def _cell_mean_safe(f, lab):
    from engine.paint_v2.era_kit_2026 import cell_mean
    try:
        return cell_mean(f, lab)
    except Exception:
        return f
