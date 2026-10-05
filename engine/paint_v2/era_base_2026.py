# -*- coding: utf-8 -*-
"""🏗 ERA BASE (2026-08-31) — the shared machinery behind the five new shelves.

The BASE contract is not the monolithic one. A base finish registers as

    BASE_REGISTRY[id] = {"M":…, "R":…, "CC":…, "desc":…,
                         "paint_fn":  paint(paint, shape, mask, seed, pm, bb),
                         "base_spec_fn": spec(shape, seed, sm, base_m, base_r)}

and `engine/base_registry_data.py` wires it by NAME: `getattr(mod, "paint_"+id)`
and `getattr(mod, "spec_"+id)`. So a 60-finish shelf needs 120 module-level
functions. Writing them out would be 60 near-identical blocks per category; this
generates them from a recipe table instead, which is the AI-as-compiler rule in
CLAUDE.md and keeps each category file a readable list of ideas.

One field is built per finish and CACHED, so the paint call and the spec call
that follows it share the work instead of doing it twice.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

try:
    import cv2
except Exception:                                            # pragma: no cover
    cv2 = None

from engine.paint_v2 import era_kit_2026 as K
from engine.paint_v2 import era_decks_2026 as D


def labels_from_field(f, cells):
    """Cells derived from the finish's OWN field.

    The shelves all fell back to `worley(seed + 7, cells=166)` when a recipe's
    stack donated no labels. The seed varies so the mosaic MOVES between
    finishes, but the generator and cell count do not, so every one of those
    finishes wears the same ~12px mosaic character — and because the palette
    index is taken from the cell-meaned field, that mosaic IS the visible
    motif. 142 of 300 era finishes reached that fallback.

    These cells instead come from the finish's own construction: quantise it
    into bands, then split each band with a lattice warped BY the field, so the
    cell walls follow the artwork's own contours.
    """
    n = int(f.shape[0])
    q = np.clip((K.pct(f) * 9.0).astype(np.int64), 0, 8)
    step = max(2, int(round(n / max(np.sqrt(max(cells, 1)), 1.0))))
    yy, xx = np.mgrid[0:n, 0:n]
    warp = (np.asarray(f, np.float32) - 0.5) * step * 1.6
    gy = ((yy + warp) / step).astype(np.int64)
    gx = ((xx - warp) / step).astype(np.int64)
    return (q * np.int64(1000003) + gy * np.int64(7919) + gx).astype(np.int32)

GEN = 1024
WORK = 1152


def hash_fid(fid):
    import zlib
    return zlib.crc32(str(fid).encode())


def _vary(fid, lo, hi, salt):
    """A stable per-finish value in [lo, hi]. zlib.crc32, never Python's salted
    hash(), so a finish does not change between processes."""
    import zlib
    t = (zlib.crc32((str(fid) + str(salt)).encode()) % 1000) / 999.0
    return lo + (hi - lo) * t


def build_field(structs, stack, shape, seed, mix="sum"):
    """Compose a recipe's primitive stack into one 0..1 field plus a label map."""
    # THE LABEL MAP COMES FROM THE HEAVIEST DONOR, NOT THE FIRST.
    #
    # This used to take the first non-None label in stack order, ignoring
    # weight — so a 0.6-weight garnish layer donated 100% of the geometry that
    # cell_mean then quantised the whole finish into. Audited across the five
    # shelves that share this idiom: 157 recipes took their entire visible
    # motif from a layer weighted BELOW their own primary. Cabinet Side Art is
    # the clean example: splatter 1.0 + bands 0.9 + cells 0.6, and the cells
    # decided what the finish looked like.
    acc, lab, lab_w, wsum = None, None, -1.0, 0.0
    for i, (name, wgt, kw) in enumerate(stack):
        f, l = structs[name](shape, seed + 101 * i, dict(kw))
        if l is not None and float(wgt) > lab_w:
            lab, lab_w = l, float(wgt)
        if acc is None:
            acc, wsum = f * float(wgt), float(wgt)
        elif mix == "max":
            acc = np.maximum(acc, f * float(wgt))
        else:
            acc = acc + f * float(wgt)
            wsum += float(wgt)
    if mix == "sum" and wsum > 0:
        acc = acc / wsum
    return K.pct(acc), lab


# Per-finish spec composition baked by the richness-first sweep, as DATA.
_ERA_SPECKW = {}
try:
    import json as _json, os as _os
    _p = _os.path.join(_os.path.dirname(__file__), "era_speckw_2026.json")
    if _os.path.exists(_p):
        _ERA_SPECKW = _json.load(open(_p, encoding="utf-8"))
except Exception:
    _ERA_SPECKW = {}


def _floor_ground(pal, lo=0.075):
    """A dark ground is not a void (DARK CITY decision, 2026-09-02). Bright-line
    designs on black — neon tubes, trace routes, muzzle flash — measured 0.5-0.9
    of the canvas below luma 0.06 on the era shelves. Lift only stops darker than
    `lo`, hue preserved; a design keeps its blackness as a deep colour."""
    out = []
    for c in pal:
        l = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        if l < lo:
            c = (np.array([lo, lo, lo * 1.08], np.float32) if l < 0.01 else np.clip(np.asarray(c) * (lo / max(l, 1e-3)), 0, 1))
        out.append(np.asarray(c, np.float32))
    return np.asarray(out, np.float32)


def make(mod, recipes, structs, palettes):
    """Generate and attach `paint_<id>` / `spec_<id>` for every recipe.

    `mod` is the calling module (so the generated functions are importable by
    name, which is what base_registry_data.py does).
    """

    _LAB_OWN = {}

    @lru_cache(maxsize=10)
    def _field(fid):
        """The finish's own construction when era_designs_2026 has one for it
        (SPB-105 / owner 2026-09-01: finishes first, spec to the finishes);
        otherwise the recipe's primitive stack."""
        d = recipes[fid]
        design = None
        try:
            from engine.paint_v2 import era_designs_2026 as ED
            design = ED.design_for(fid)
        except Exception:
            design = None
        if design is None:
            f, lab = build_field(structs, d["stack"], (GEN, GEN), d["seed"],
                                 mix=d.get("mix", "sum"))
            _LAB_OWN[fid] = lab is not None
            if lab is None:
                lab = labels_from_field(f, int(d.get("shade_cells", 166)))
            return f, lab
        from engine.expansions import nightshift_forms_2026 as NF
        from engine.paint_v2 import era_kit_2026 as EK
        form, params, kind = design
        fn = getattr(EK, form[3:]) if form.startswith("ek:") else getattr(NF, form)
        out = fn((GEN, GEN), d["seed"], **params)
        f, lab = out if isinstance(out, tuple) else (out, None)
        f = np.asarray(f, np.float32)
        f = NF.compose_form(f, d["seed"], kind=kind,
                            amount=float(d.get("detail", ED.DETAIL.get(fid, 0.40))), res=GEN)
        # PLACES: busy zones and calm zones, as every gold standard has
        slow = np.asarray(K.fbm((GEN, GEN), d["seed"] + 7, octaves=(5, 10, 20),
                                weights=(1.0, 0.6, 0.35)), np.float32)
        slow = (slow - float(slow.min())) / max(float(slow.max() - slow.min()), 1e-6)
        mm = float(f.mean())
        f = np.clip(mm + (f - mm) * (0.50 + 1.0 * slow), 0, 1).astype(np.float32)
        # FINE: a second, smaller construction nested in the first (intricacy)
        fine = ED.FINE.get(fid)
        if fine is not None:
            form2, params2, w = fine
            fn2 = getattr(EK, form2[3:]) if form2.startswith("ek:") else getattr(NF, form2)
            out2 = fn2((GEN, GEN), d["seed"] + 41, **params2)
            f2 = np.asarray(out2[0] if isinstance(out2, tuple) else out2, np.float32)
            f2 = (f2 - float(f2.min())) / max(float(f2.max() - f2.min()), 1e-6)
            gy, gx = np.gradient(f)
            key = np.hypot(gx, gy)
            key = key / max(float(np.percentile(key, 98)), 1e-6)
            key = 0.45 + 0.55 * np.clip(key, 0, 1)
            f = np.clip(f * (1.0 - w) + f2 * w * key + f * w * (1.0 - key), 0, 1).astype(np.float32)
        _LAB_OWN[fid] = lab is not None
        if lab is None:
            lab = labels_from_field(f, int(d.get("shade_cells", 166)))
        return f, lab

    @lru_cache(maxsize=6)
    def _art(fid):
        d = recipes[fid]
        f, lab = _field(fid)
        f = K.upscale(f, WORK)
        lab = K.upscale(lab, WORK)
        pal = _floor_ground(np.asarray(palettes[d["palette"]], np.float32))
        # HOW MUCH OF THE FIELD IS FLATTENED PER CELL. cell_mean gives each label
        # one value, which is what makes plate-like finishes read as plates — but
        # it also WIPES any detail finer than a cell. A scanline at 5px inside an
        # 8px worley cell is averaged away completely, which is why the arcade
        # cards measured 0.17-0.33 on the car band with a primitive that scores
        # 0.60 on its own. Screen-like recipes set `cell_mean` low and keep their
        # own frequency.
        # DEFAULT 0.0, WAS 1.0. Full cell_mean replaces the construction with
        # its own cell averages, which is what made 125 of 300 era finishes read
        # as the same mosaic. Plate-like recipes opt IN.
        # cell means only when the construction drew the cells (the 12px-mosaic bug)
        cm = float(d.get("cell_mean", 0.35)) if _LAB_OWN.get(fid, True) else 0.0
        fc = K.cell_mean(f, lab) if cm > 0 else f
        if 0.0 < cm < 1.0:
            fc = fc * cm + f * (1.0 - cm)
        # RE-RANK BEFORE THE PALETTE LOOKUP.
        #
        # build_field returns a rank-normalised (uniform) field, but upscaling to
        # WORK and blending with cell means both re-concentrate it toward the
        # middle. The palettes are 4-stop and several have two middle stops close
        # in luma — at_disc_rainbow's are 0.39 and 0.42 — so a concentrated field
        # lands almost everything between those two and the finish renders flat.
        # Measured on that finish: field std 0.27 -> 0.18 after upscale -> 0.14
        # after the cell blend -> luma std 0.057 after the palette. Re-ranking
        # here guarantees the whole ramp is traversed whatever the field's
        # histogram looks like, which is the same reason _pop cuts its threshold
        # by percentile rather than by value.
        t = np.clip(K.pct(fc) ** float(d.get("gamma", 1.0)), 0, 1)
        idx = np.clip((t * (len(pal) - 1)).astype(np.int32), 0, len(pal) - 2)
        frac = np.clip(t * (len(pal) - 1) - idx, 0, 1)[..., None]
        art = pal[idx] * (1.0 - frac) + pal[idx + 1] * frac
        art = art * (0.74 + 0.52 * f)[..., None]
        if cv2 is not None:
            hsv = cv2.cvtColor(np.clip(art, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
            hsv[..., 0] = np.mod(hsv[..., 0] + (K._h1(lab, 97) - 0.5)
                                 * float(d.get("hue_jitter", _vary(fid, 8.0, 26.0, 11))), 360.0)
            hsv[..., 1] = np.clip(hsv[..., 1] * (0.88 + 0.24 * K._h1(lab, 149)), 0, 1)
            art = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            # KEYED detail, not a uniform grain layer. A constant-amplitude fbm
            # over the whole canvas makes the paint's band-limited detail
            # envelope FLAT, and a flat envelope is one no spec can follow —
            # that is why finishes whose specs visibly traced their artwork
            # still measured FOLLOW near zero. Riding the finish's own field
            # concentrates the detail where the artwork has structure.
            from engine.expansions import nightshift_forms_2026 as NF
            # grain kind and amplitude vary per finish. No recipe in any of the
            # 300 overrode these, so all 300 carried an identical grain layer.
            _GK = ("grain", "fibre", "flake", "crackle", "stipple", "ridge", "spark")
            gkind = d.get("grain") or _GK[abs(hash_fid(fid)) % len(_GK)]
            gk, _key = NF.detail(fc, d["seed"] + 3, kind=gkind, amount=1.0, res=WORK)
            art = art * (1.0 + (gk - 0.5) * 2.0
                         * float(d.get("gamt", _vary(fid, 0.10, 0.34, 29))))[..., None]
        return np.clip(art, 0, 1).astype(np.float32)

    # expose for the richness sweep / variant sheets (closures are otherwise unreachable)
    mod._spb_field = _field
    mod._spb_art = _art

    def _mk_paint(fid):
        def paint_fn(paint, shape, mask, seed, pm, bb):
            fh, fw = int(shape[0]), int(shape[1])
            src = np.asarray(paint, np.float32)[:, :, :3]
            if src.size and src.max() > 1.5:
                src = src / 255.0
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (fh, fw) and cv2 is not None:
                m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
            art = _art(fid)
            if cv2 is not None and art.shape[:2] != (fh, fw):
                art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
            kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
            return np.clip(src * (1.0 - kk) + art * kk, 0.0, 1.0).astype(np.float32)
        paint_fn.__name__ = "paint_" + fid
        return paint_fn

    def _mk_spec(fid):
        d = recipes[fid]

        def spec_fn(shape, seed, sm, base_m, base_r):
            """Owner 2026-09-01: the spec must "follow the pattern of the base
            paint and MAKE SENSE", and every finish must own its material story.

            Two things were wrong here and both are fixed by the same rewrite.
            The deck came from `D.DECKS[d["deck"]]` — a NAMED deck out of a pool
            of 27 shared roughly three ways across each 60-finish shelf. And the
            cards were dealt onto the raw pre-paint FIELD, so the spec's
            boundaries had no particular relationship to the finished artwork's.

            Now: `cards` on the recipe is a hand-authored per-finish deck, and
            the layout is composed against the RENDERED PAINT so every material
            boundary lands on a tonal boundary of the artwork. Same change that
            took FRACTURED NIGHTSHIFT from 0/50 to 50/50 on the finish law.
            """
            from engine.paint_v2 import spec_story as ST
            fh, fw = int(shape[0]), int(shape[1])
            res = max(fh, fw)
            f, lab = _field(fid)
            f = K.upscale(f, res)
            lab = K.upscale(lab, res)
            if f.shape[:2] != (fh, fw) and cv2 is not None:
                f = cv2.resize(f, (fw, fh), interpolation=cv2.INTER_LINEAR)
                lab = cv2.resize(np.asarray(lab, np.int32), (fw, fh),
                                 interpolation=cv2.INTER_NEAREST)
            # hand-authored per-finish deck, if this finish has one yet
            from engine.paint_v2 import era_authored_decks_2026 as AD
            authored = AD.CARDS.get(fid)
            cards = d.get("cards")
            edge = d.get("edge")
            kw = dict(d.get("spec_kw", {}))
            if authored:
                cards, edge, akw = authored
                kw.update(akw)
            kw.update(_ERA_SPECKW.get(fid, {}))   # richness-first sweep (_rebuild/rich_sweep.py era:<prefix>)
            if not cards:
                # fall back to the shelf's named deck until this finish is
                # hand-authored; extract just the card names from its bands
                cards = tuple(c for c, _u in D.DECKS[d["deck"]])
            art = _art(fid)
            if cv2 is not None and art.shape[:2] != (fh, fw):
                art = cv2.resize(art, (fw, fh), interpolation=cv2.INTER_LINEAR)
            out = np.asarray(ST.compose(f, cards, seed=d["seed"], res=res, lab=lab,
                                        edge=edge, art=art, **kw), np.float32)
            # the BASE contract wants three separate channels, not a packed image
            return out[..., 0], out[..., 1], out[..., 2]
        spec_fn.__name__ = "spec_" + fid
        return spec_fn

    for fid in recipes:
        setattr(mod, "paint_" + fid, _mk_paint(fid))
        setattr(mod, "spec_" + fid, _mk_spec(fid))
    mod._field = _field
    mod._art = _art
    return len(recipes)


def registry_rows(recipes):
    """The M/R/CC + desc rows base_registry_data.py needs, taken from the deck's
    own mid-card so a finish's flat fallback matches the material it is made of."""
    from engine.paint_v2 import spec_cards as SC
    rows = {}
    for fid, d in recipes.items():
        mid = D.DECKS[d["deck"]][3][0]
        m, r, cc = SC.CARDS[mid]
        rows[fid] = {"M": int(m), "R": int(r), "CC": int(cc), "desc": d["desc"]}
    return rows
