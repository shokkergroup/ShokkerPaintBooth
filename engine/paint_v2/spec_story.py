# -*- coding: utf-8 -*-
"""SPEC STORY — build a spec that follows its artwork, one story per finish.

Owner mandate 2026-08-31/09-01, after FRACTURED ELEMENTS shipped 60 finishes on
5 chapter-level spec decks:

    "the specs should be diverse, unique, follow the pattern of the base paint
     and MAKE SENSE. If it says MINERAL: CHALK CHROME then by GOD it should
     make you instantly feel like this finish IS chalk chrome with the
     appropriate spec colors as well to help make it happen."

THE POINT OF THIS MODULE
------------------------
Every failure the FINISH LAW catches in the older shelves has the same shape:
cards were dealt over an INDEPENDENT noise field laid on top of the artwork,
instead of being dealt on the artwork's own geometry. That produces a spec that
is statistically busy but visually unrelated to the paint - the owner's "chaotic
but makes no sense".

So this module makes the two hard axes pass BY CONSTRUCTION rather than by
iteration:

  FOLLOW  Regions are level sets of the finish's OWN field, so region
          boundaries ARE artwork boundaries. And the within-region micro
          variation is modulated by the artwork's own band-limited envelope, so
          where the artwork is busy the spec is busy and where it is calm the
          spec is calm. amp_corr measures exactly that, so it cannot come out
          low unless the caller passes an unrelated field.
  SCALE   The micro variation lives at 8-32px on a 2048 canvas, so the spec
          carries the car window even when the paint is deliberately broad
          (the DICHROIC SKIN case).
  STORY   The deck is an argument, never a module-level default. There is no
          chapter table in here to fall back on - that absence is deliberate.

Cards are dealt COMPLETE, never interpolated between (a material is a material),
which is the existing spec_cards doctrine.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.paint_v2 import spec_cards as SC


# --------------------------------------------------------------- vocabulary
# The owner's rule: the NAME is the brief. A finish called "chalk chrome" must
# read as chalk and chrome. These words map to real cards so a recipe can say
# what it IS and get a deck that means it.
WORDS = {
    "chalk":      ("ceramic_matte", "matte", "clear_matte"),
    "matte":      ("matte", "clear_matte", "flat_black"),
    "flat":       ("flat_black", "void", "matte"),
    "powder":     ("powder", "bead_blast", "ceramic_matte"),
    "blast":      ("bead_blast", "galvanized", "brushed_ti"),
    "suede":      ("eggshell", "satin", "vinyl"),
    "velvet":     ("vinyl", "satin", "eggshell"),
    "rubber":     ("vinyl", "satin_carbon", "powder"),
    "plastic":    ("fiberglass", "vinyl", "semi_gloss"),
    "eggshell":   ("eggshell", "satin", "semi_gloss"),
    "satin":      ("satin", "soft_gloss", "semi_gloss"),
    "gloss":      ("gloss", "soft_gloss", "ceramic_gloss"),
    "wet":        ("wet", "liquid_glaze", "gloss"),
    "glaze":      ("liquid_glaze", "wet", "ceramic_gloss"),
    "lacquer":    ("candy", "gloss", "ceramic_gloss"),
    "candy":      ("candy", "candy_chrome", "spectraflame"),
    "glass":      ("sea_glass", "milk_glass", "fiberglass"),
    "ceramic":    ("ceramic_gloss", "ceramic_matte", "milk_glass"),
    "porcelain":  ("milk_glass", "ceramic_gloss", "ceramic_matte"),
    "ice":        ("frozen_film", "frozen_metal", "sea_glass"),
    "frost":      ("frozen_film", "milk_glass", "bead_blast"),
    "chrome":     ("chrome", "dark_chrome", "satin_chrome"),
    "mirror":     ("chrome", "mercury", "candy_chrome"),
    "mercury":    ("mercury", "chrome", "liquid_glaze"),
    "steel":      ("gunmetal", "brushed_ti", "galvanized"),
    "iron":       ("gunmetal", "patina", "galvanized"),
    "gunmetal":   ("gunmetal", "dark_chrome", "satin_carbon"),
    "titanium":   ("brushed_ti", "anodized", "galvanized"),
    "anodized":   ("anodized", "brushed_ti", "frozen_metal"),
    "galvanized": ("galvanized", "bead_blast", "patina"),
    "metallic":   ("metallic", "pearl", "gunmetal"),
    "pearl":      ("pearl", "milk_glass", "metallic"),
    "oxide":      ("patina", "powder", "bead_blast"),
    "patina":     ("patina", "galvanized", "powder"),
    "carbon":     ("gloss_carbon", "satin_carbon", "razor"),
    "graphite":   ("satin_carbon", "gunmetal", "flat_black"),
    "spectral":   ("spectraflame", "candy_chrome", "antique_chrome"),
    "dichroic":   ("spectraflame", "candy_chrome", "pearl"),
    "void":       ("void", "flat_black", "clear_matte"),
    "shadow":     ("flat_black", "void", "satin_carbon"),
    "neon":       ("carrier_high", "carrier_mid", "gloss"),
    "carrier":    ("carrier_mid", "carrier_high", "carrier_low"),
}


def deck_from_words(words, *, extra=(), min_cards=5):
    """Build an ordered deck from the finish's own material words.

    Ordered roughness-DESCENDING so the deck reads as the artwork's geometry:
    the deepest parts of the field get the deadest material, the highlights get
    the sharpest. Duplicates are dropped, order is stable.
    """
    out = []
    for w in list(words) + list(extra):
        for card in WORDS.get(w, (w,)):
            if card in SC.CARDS and card not in out:
                out.append(card)
    if len(out) < min_cards:
        raise ValueError("deck too thin (%d cards) for words %r — name more materials"
                         % (len(out), list(words)))
    return tuple(sorted(out, key=lambda c: -SC.CARDS[c][1]))


# ------------------------------------------------------------------ helpers
def _blur(img, sigma):
    if cv2 is None or sigma <= 0:
        return img
    return cv2.GaussianBlur(img, (0, 0), float(sigma))


def envelope(field, res, work=1024):
    """The artwork's own detail envelope, band-limited to the car window.

    This is the quantity the FINISH LAW's FOLLOW axis correlates against, so
    driving the spec's micro-contrast with it is what makes the spec read as
    belonging to the paint instead of being sprinkled over it.

    Solved at <=1024 and upscaled. The envelope is a heavily blurred quantity by
    construction (sigma 16 at 2048), so full-resolution work buys nothing and
    cost 2.5s inside compose() at 2048.
    """
    f = np.asarray(field, np.float32)
    n = f.shape[0]
    w = min(int(work), n)
    if cv2 is not None and w != n:
        f = cv2.resize(f, (w, w), interpolation=cv2.INTER_AREA)
    lo = _blur(f, w / 2048.0 * 32.0 / 2.0)
    hi = _blur(f, max(0.6, w / 2048.0 * 8.0 / 2.0))
    env = np.abs(hi - lo)
    env = _blur(env, w / 2048.0 * 24.0)
    m = float(env.max())
    env = (env / m) if m > 1e-6 else env
    if cv2 is not None and w != n:
        env = cv2.resize(env, (n, n), interpolation=cv2.INTER_LINEAR)
    return env


def _hash01(a, salt):
    x = (np.asarray(a, np.int64) * np.int64(2654435761) + np.int64(salt * 40503)) & np.int64(0x7FFFFFFF)
    x = (x ^ (x >> np.int64(13))) * np.int64(1274126177) & np.int64(0x7FFFFFFF)
    return (x & np.int64(0xFFFFFF)).astype(np.float32) / np.float32(0xFFFFFF)


def compose(field, deck, *, seed, res=None, lab=None, edge=None,
            grain=0.55, micro=None, edge_width=0.018, cc_jitter=0.10, art=None,
            chips=0.34, edge_max=0.07, env_floor=0.10, bands="quantile",
            chip_floor=0.30):
    """Deal `deck` onto `field`'s own geometry. Returns HxWx3 float 0-255.

    field  HxW float 0..1 — the finish's OWN artwork field (the same one the
           paint is coloured from). Passing anything else defeats the module.
    deck   ordered card names, roughness-descending, ONE PER FINISH.
    lab    optional HxW int labels for a plate/cell look; regions are then the
           intersection of the artwork's level sets with the cells.
    edge   card name laid in a thin lip on region boundaries. This is the
           single strongest "the spec follows the design" cue — it is what
           TRUCHET GLASS does.
    art    HxWx3 RENDERED PAINT, strongly recommended. PASS THIS.

    Why `art` matters more than `field`: FOLLOW correlates the band-limited
    detail envelopes of the finished paint and the finished spec. A generator
    usually adds its own fine grain, hue jitter and cell tinting AFTER the
    field, so the field is not where the painted detail actually ends up. Two
    finishes measured with equally structured envelopes (TRUCHET 0.291,
    ELM_MONSOON 0.321) scored 0.844 and 0.052 — the difference was not how
    peaky the detail is, but whether both peak in the SAME PLACES. Driving the
    spec's micro-amplitude from the rendered paint makes that true by
    construction, for any category, however its paint is built.
    """
    f = np.clip(np.asarray(field, np.float32), 0.0, 1.0)
    h, w = f.shape[:2]
    res = int(res or max(h, w))
    n = len(deck)
    if n < 2:
        raise ValueError("a story needs at least 2 cards")

    # The region field. When the rendered paint is available it IS the region
    # field: the owner's rule is that the spec "follows the outline of the base
    # paint", so the bands must be the paint's own tonal regions, not the
    # pre-paint field's. Modulating only the grain by the paint (and cutting
    # regions from the field) leaves the dominant spec structure — the region
    # boundaries — sitting in the wrong places, which measured as FOLLOW still
    # failing on 3 of 5 test finishes.
    art_l = None
    if art is not None:
        a = np.asarray(art, np.float32)
        if a.ndim == 3 and a.shape[2] >= 3:
            if float(a.max()) > 1.5:
                a = a / 255.0
            a = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        art_l = np.ascontiguousarray(a, np.float32)
        lo, hi = float(art_l.min()), float(art_l.max())
        f = (art_l - lo) / max(hi - lo, 1e-6)

    # --- regions ARE the artwork's level sets -----------------------------
    # QUANTILE bands give every card an equal share of the canvas, which is right
    # for area-filling constructions. It is WRONG for a construction that is
    # mostly background by area — a filament net, a dendrite, a vein field —
    # because six of the seven band edges then fall inside the background and
    # only one lands on the structure that actually carries the artwork. Those
    # finishes measured FOLLOW 0.29-0.33 while area-filling ones on identical
    # code measured 0.70-0.87. LINEAR bands cut by value instead, so the
    # structure gets its own cards and the background collapses into one.
    if bands == "linear":
        lo, hi = float(f.min()), float(f.max())
        qs = np.linspace(lo, hi, n + 1)[1:].astype(np.float32)
    else:
        qs = np.percentile(f[::4, ::4], np.linspace(0.0, 100.0, n + 1)[1:])
    qs = np.maximum.accumulate(np.asarray(qs, np.float32))
    idx = np.clip(np.searchsorted(qs, f.ravel(), side="left"), 0, n - 1).reshape(h, w)
    if lab is not None:
        # keep cell coherence but never let cells invent regions the artwork
        # does not have: the cell only breaks ties inside one level set
        jitter = (_hash01(np.asarray(lab, np.int64), seed + 17) - 0.5) * 0.8
        idx = np.clip(idx + np.round(jitter).astype(np.int32), 0, n - 1)

    cards = np.asarray([SC.CARDS[c] for c in deck], np.float32)
    out = cards[idx]

    # --- micro variation, amplitude tied to the artwork -------------------
    env = envelope(art_l if art_l is not None else f, res)
    if isinstance(micro, str) and micro == "paint":
        # The spec's fine layer IS the paint's fine layer. On a texture that is
        # equally busy everywhere (bark, corrugate, canvas) an independent grain
        # cannot follow anything: both car-band envelopes are flat, and FOLLOW
        # measured 0.02-0.14 on PARADIGM 2026-09-02 while both mutual
        # information and amplitude correlation agreed the spec was NOT on the
        # creases. Riding the paint's own car-band detail puts the material
        # change exactly where the paint's crease is.
        src = np.asarray(art_l if art_l is not None else f, np.float32)
        lo = _blur(src, max(1.0, w / 2048.0 * 16.0))
        hi = _blur(src, max(0.6, w / 2048.0 * 3.0))
        bp = hi - lo
        p1, p99 = np.percentile(bp, [1, 99])
        micro = np.clip((bp - p1) / max(float(p99 - p1), 1e-6), 0, 1).astype(np.float32)
    if micro is None:
        # built at <=1024 and upscaled: it is blurred to ~3px anyway, and the
        # meshgrid + int64 hash over 4M cells was a measurable part of compose()
        mw = min(1024, w)
        gy_, gx_ = np.meshgrid(np.arange(mw), np.arange(mw), indexing="ij")
        micro = _hash01(gy_.astype(np.int64) * np.int64(73856093)
                        ^ gx_.astype(np.int64) * np.int64(19349663), seed + 31)
        px = max(1.0, mw / 2048.0 * 3.0)
        micro = _blur(micro.astype(np.float32), px)
        mn, mx = float(micro.min()), float(micro.max())
        micro = (micro - mn) / max(mx - mn, 1e-6)
        if cv2 is not None and mw != w:
            micro = cv2.resize(micro, (w, h), interpolation=cv2.INTER_LINEAR)
    # Fine CHIPS of the neighbouring card inside each region. Multiplying a
    # single card by noise only shades it; the car window needs an actual
    # second material at 8-32px or SCALE collapses the moment regions get
    # smooth (measured: fine 0.332 -> 0.260 with shading alone). Chip density
    # follows the paint's envelope, so the busy parts of the artwork are where
    # the material mix is busiest.
    if chips > 0.0:
        cell = max(2.0, res / 2048.0 * 14.0)
        gy, gx = np.mgrid[0:h, 0:w]
        cid = (gy / cell).astype(np.int64) * np.int64(7919) + (gx / cell).astype(np.int64)
        pick = _hash01(cid, seed + 101)
        # chip_floor is how much of the chipping happens REGARDLESS of where
        # the artwork has detail. Dropping it concentrates the material change
        # onto the artwork's structure, which is what lets a shelf use quantile
        # bands (so every card gets real area, and the spec is not one flat
        # material) while still following the paint.
        take = pick < np.clip(chips * (chip_floor + (1.0 - chip_floor) * env), 0.0, 0.95)
        alt = np.clip(idx + np.where(_hash01(cid, seed + 211) < 0.5, -1, 1), 0, n - 1)
        out[take] = cards[alt][take]

    # env_floor is the share of the spec's micro detail that is laid down
    # REGARDLESS of where the artwork has detail. At 0.25 that uniform baseline
    # decorrelates the two envelopes badly on constructions whose artwork is
    # mostly background by area — filament nets, dendrites, veins — which is why
    # three of those measured FOLLOW 0.29-0.33 while area-filling constructions
    # on the same code measured 0.7-0.87. Lower it and the spec's detail
    # concentrates where the artwork's detail actually is.
    amp = grain * (env_floor + (1.0 - env_floor) * env)
    # roughness carries the grain; metallic follows more gently; clearcoat gets
    # a small independent walk so the film reads as a film and not as a mask
    out[..., 1] = np.clip(out[..., 1] * (1.0 + (micro - 0.5) * 2.0 * amp * 0.42), 0, 255)
    out[..., 0] = np.clip(out[..., 0] * (1.0 + (micro - 0.5) * 2.0 * amp * 0.16), 0, 255)
    ccj = _hash01(np.arange(h * w).reshape(h, w) // max(1, int(res / 2048.0 * 11)), seed + 53)
    out[..., 2] = np.clip(out[..., 2] * (1.0 + (ccj - 0.5) * 2.0 * cc_jitter), 0, 255)

    # --- the lip on the artwork's own boundaries --------------------------
    if edge is not None and cv2 is not None:
        # the lip is a binary mask; gradient + dilate over 4M pixels at 2048 was
        # a measurable slice of the render budget for no visible difference
        ew = min(1024, h)
        idx_s = (cv2.resize(idx.astype(np.float32), (ew, ew), interpolation=cv2.INTER_NEAREST)
                 if ew != h else idx.astype(np.float32))
        gy, gx = np.gradient(idx_s)
        mag = np.hypot(gx, gy)
        border = (mag > 0.25).astype(np.float32)
        k = max(1, int(round(ew * edge_width * 0.35)))
        border = cv2.dilate(border, np.ones((k, k), np.float32))
        # CAP THE LIP. Region boundaries are level sets of the artwork, so on a
        # busy paint they run everywhere; dilating all of them by 6px flooded
        # ~85% of the canvas with the edge card. Rendered, that is a spec map
        # that is uniformly chrome — and a uniform spec has no structure for
        # FOLLOW to find, which is exactly how seven finishes measured 0.08-0.32
        # while looking, on inspection, like a sheet of red.
        cov = float(border.mean())
        if cov > edge_max:
            # keep only the strongest boundaries, then re-dilate more tightly
            thr = float(np.percentile(mag, 100.0 * (1.0 - edge_max * 0.55)))
            border = (mag > max(thr, 0.25)).astype(np.float32)
            k2 = max(1, k // 2)
            border = cv2.dilate(border, np.ones((k2, k2), np.float32))
            if float(border.mean()) > edge_max:
                # TIE-BREAK RANDOMLY. `mag` comes from an integer region index,
                # so it takes a handful of discrete values and most pixels tie.
                # argsort is stable, so [::-1] hands the budget to the HIGHEST
                # indices of the tie class first — the bottom rows of the image.
                # Owner 2026-09-02 on DARK CITY: "very weird strip on the bottom
                # of the spec map" (Cobalt Night, Copper Dark, Dried Rose, Rust
                # Noir): a chrome bar ~5% up from the bottom, measured M +125 /
                # R -119 in rows 1952-1969 at 2048. A hashed jitter far below the
                # value spacing breaks the ties without changing the ranking of
                # real boundaries.
                # ...and NEVER spend the budget on non-boundaries: if the real
                # boundaries are fewer than the cap, take them all and stop.
                # Filling the remainder with tie-broken zeros scattered chrome
                # confetti over the whole canvas (garnet_dark FOLLOW 0.68 -> 0.03).
                jit = _hash01(np.arange(mag.size, dtype=np.int64), seed + 307).astype(np.float32) * 1e-3
                order = np.argsort(mag.ravel() + jit)[::-1]
                real = int((mag > 0.25).sum())
                keep = order[:min(int(edge_max * mag.size), real)]
                border = np.zeros(mag.size, np.float32)
                border[keep] = 1.0
                border = cv2.dilate(border.reshape(mag.shape), np.ones((2, 2), np.float32))
        if ew != h:
            border = cv2.resize(border, (w, h), interpolation=cv2.INTER_LINEAR)
        border *= (0.35 + 0.65 * env)          # brightest where the art is busy
        card = np.asarray(SC.card(edge), np.float32)
        m = border[..., None]
        out = out * (1.0 - m) + card[None, None, :] * m

    return SC.iron_safe(out)


def distinct(stories):
    """Assert every finish owns its material story.

    `stories` maps finish id -> deck tuple. Raises with the offending ids, so a
    module cannot import with a shared deck. This is the STORY axis enforced at
    authoring time instead of discovered by a gate afterwards.
    """
    seen = {}
    for fid, deck in stories.items():
        key = frozenset(deck)
        seen.setdefault(key, []).append(fid)
    clashes = {k: v for k, v in seen.items() if len(v) > 1}
    if clashes:
        lines = ["%d finishes share one material story: %s" % (len(v), ", ".join(sorted(v)))
                 for v in clashes.values()]
        raise ValueError("SPEC STORY violation — " + "; ".join(lines))
    return True
