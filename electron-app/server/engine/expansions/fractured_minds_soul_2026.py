# -*- coding: utf-8 -*-
"""FRACTURED MINDS — SOUL-PHYSICS RETUNE (2026-06-12, owner mandate).

"With what you've learned from today and FRACTURED SOULS and how the channels
and colors work — rebuild FRACTURED MINDS with the same thought process. They
are already there, they just need COLOR tweaks and spec map tweaks."

So: every fm_* finish KEEPS its own design (the v2/v3 generators stay the
single source of the art), but both halves are re-tuned at the registry level:

  SPEC  -> the winner physics recovered from the owner's Blood Marble
           forensics: M ~252 (amplifier rail, +/- the design's own micro
           texture), B railed flat 255 (power supply), G = ultra-gloss floor
           30 + aperture lanes 30..78 that TRACE the finish's own paint
           geometry (Wovenlight ignition doctrine — the lanes are extracted
           from the design's actual edges + micro relief, never alien noise).

  PAINT -> crushed-but-COLORFUL: saturation boosted, value crushed to
           0.05..~0.37 (deliberately LESS crushed than FRACTURED SOULS —
           owner: "you went 'too far' on some of the souls... make the paint
           side actually colorful"). 47 designs x their own palettes = many
           hues popping through at angle.

Wrapping happens AFTER fractured_minds_2026 + _v3 install (see the hook in
shokker_engine_v2). Idempotent: wrapped fns carry ``_fm_soul`` and are never
double-wrapped.
"""
import numpy as np
import cv2

# 768 keeps the lane extraction visually identical after upscale while cutting
# the extra art pass ~45% (heaviest FM finishes were riding the 3s ceiling)
_WORKF = 768
_ART_CACHE = {}
# Lane/micro-texture cache. ``_lanes_from_art`` is a PURE function of the work-
# res design art, and the art is already deterministic per (fid, seed) via
# _ART_CACHE — so the 5-blur lane stack only ever needs to run ONCE per design.
# The app re-renders a finish's spec on every color / angle / strength tweak
# while the design + seed stay fixed; this cache makes those repeats free
# (bit-identical: same art object in -> same arrays out). _lanes_from_art itself
# stays pure + untouched so engine.shokkerize (which feeds its own synthesized
# art) is unaffected.
_LANE_CACHE = {}
# Output-res M/G cache: M and G are a deterministic function of the cached
# (lane, mtex) + lane_gain + the resize target, so the two 768->native resizes
# only need to run ONCE per (fid, seed, lane_gain, h, w). Only the per-zone mask
# blend (cheap) then varies per call. Bit-identical (resize of identical input).
_MG_CACHE = {}

# Winner contract (Blood Marble forensic bake, 2026-06-12)
_FM_M = 252.0
_FM_G_FLOOR = 30.0
_FM_G_LANE = 78.0

# Per-finish overrides: {fid: {"sat":, "vbase":, "vscale":, "lane_gain":}}
TUNE = {}


def _skey(seed):
    try:
        return int(seed) & 0x7FFFFFFF
    except Exception:
        try:
            return int(np.asarray(seed).ravel()[0]) & 0x7FFFFFFF
        except Exception:
            return 51


def _design_art(fid, old_paint_fn, seed):
    """The finish's own art, rendered once on neutral gray at work res."""
    key = (fid, _skey(seed))
    if key in _ART_CACHE:
        return _ART_CACHE[key]
    if len(_ART_CACHE) > 6:
        _ART_CACHE.pop(next(iter(_ART_CACHE)))
    src = np.full((_WORKF, _WORKF, 3), 0.5, np.float32)
    mask = np.ones((_WORKF, _WORKF), np.float32)
    art = old_paint_fn(src, (_WORKF, _WORKF, 3), mask, seed, 1.0, None)
    art = np.clip(np.asarray(art, np.float32)[:, :, :3], 0, 1)
    _ART_CACHE[key] = art
    return art


def _design_lanes(fid, old_paint_fn, seed):
    """``_lanes_from_art`` for this finish's design, memoized per (fid, seed).

    Returns the SAME (lane, mtex) arrays ``_lanes_from_art(_design_art(...))``
    would — bit-identical — but only runs the blur stack once per design."""
    key = (fid, _skey(seed))
    cached = _LANE_CACHE.get(key)
    if cached is not None:
        return cached
    if len(_LANE_CACHE) > 6:
        _LANE_CACHE.pop(next(iter(_LANE_CACHE)))
    lane, mtex = _lanes_from_art(_design_art(fid, old_paint_fn, seed))
    _LANE_CACHE[key] = (lane, mtex)
    return lane, mtex


def _lanes_from_art(art):
    """Aperture lanes = the design's OWN geometry: multi-channel edges + micro
    luminance relief. Hairline-fine by construction (gradients are 1-2px)."""
    lum = (0.299 * art[..., 0] + 0.587 * art[..., 1] + 0.114 * art[..., 2])
    edges = np.zeros_like(lum)
    for c in range(3):
        g = cv2.GaussianBlur(art[..., c], (0, 0), 1.0)
        gy, gx = np.gradient(g)
        edges += np.abs(gx) + np.abs(gy)
    e = edges / max(float(np.percentile(edges, 99.5)), 1e-6)
    band = lum - cv2.GaussianBlur(lum, (0, 0), 6.0)
    babs = np.abs(band)
    b = babs / max(float(np.percentile(babs, 99.5)), 1e-6)
    lane = np.clip(1.5 * e + 0.6 * b, 0, 1)
    t = np.clip((lane - 0.14) / 0.50, 0, 1)
    lane = (t * t * (3 - 2 * t)).astype(np.float32)
    # NO BLOTCH (owner): top-hat — keep only structure finer than ~14px; a
    # solid fill collapses to its rim band, blob interiors return to floor
    lane = np.clip(lane - 0.75 * cv2.GaussianBlur(lane, (0, 0), 7.0), 0, 1)
    # restore full lane amplitude after the subtraction
    ln99 = float(np.percentile(lane, 99.5))
    if ln99 > 1e-3:
        lane = np.clip((lane / ln99 - 0.05) / 0.95, 0, 1)
    # floor-contrast guarantee: the aperture must stay mostly FLOOR (gloss
    # pins) with the design as lanes — dense micro designs otherwise saturate
    # G flat and the flash dies. Hard percentile gate keeps the strongest
    # ~30% of structure at full lane, everything else returns to floor.
    cov = 0.30
    if float(lane.mean()) > cov + 0.05:
        q = float(np.percentile(lane, 100.0 * (1.0 - cov)))
        t3 = np.clip((lane - q) / max(1e-3, 0.6 * (1.0 - q)), 0, 1)
        lane = (t3 * t3 * (3 - 2 * t3)).astype(np.float32)
    mtex = np.clip(band * 8.0, -1, 1).astype(np.float32)
    return lane, mtex


def _mk_spec(fid, old_paint_fn, tune):
    lane_gain = float(tune.get("lane_gain", 1.0))

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        mgkey = (fid, _skey(seed), lane_gain, fh, fw)
        cached_mg = _MG_CACHE.get(mgkey)
        if cached_mg is not None:
            M, G = cached_mg
        else:
            lane, mtex = _design_lanes(fid, old_paint_fn, seed)
            lane = np.clip(lane * lane_gain, 0, 1)
            M = _FM_M + 6.0 * mtex
            G = _FM_G_FLOOR + (_FM_G_LANE - _FM_G_FLOOR) * lane
            M, G = [cv2.resize(np.clip(a, 0, 255).astype(np.float32), (fw, fh),
                               interpolation=cv2.INTER_LINEAR) for a in (M, G)]
            if len(_MG_CACHE) > 6:
                _MG_CACHE.pop(next(iter(_MG_CACHE)))
            _MG_CACHE[mgkey] = (M, G)
        out = np.zeros((fh, fw, 4), np.uint8)
        mm = np.clip(m2, 0, 1)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(np.clip(G, 14, 110) * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(255.0 * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    spec_fn._fm_soul = True
    return spec_fn


def _mk_paint(old_paint_fn, tune):
    sat = float(tune.get("sat", 1.70))
    sat_add = float(tune.get("sat_add", 0.10))
    vbase = float(tune.get("vbase", 0.05))
    vscale = float(tune.get("vscale", 0.33))

    def paint_fn(paint, shape, mask, seed, pm, bb):
        out = old_paint_fn(paint, shape, mask, seed, pm, bb)
        out = np.clip(np.asarray(out, np.float32)[:, :, :3], 0, 1)
        fh, fw = out.shape[:2]
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        hsv = cv2.cvtColor(out, cv2.COLOR_RGB2HSV)
        hsv[..., 1] = np.clip(hsv[..., 1] * sat + sat_add, 0, 1)
        hsv[..., 2] = np.clip(vbase + vscale * hsv[..., 2], 0, 1)
        crushed = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        mm = np.clip(m2 * float(pm), 0, 1)[..., None]
        return np.clip(out * (1 - mm) + crushed * mm, 0, 1).astype(np.float32)

    paint_fn._fm_soul = True
    return paint_fn


def install_into_engine(mono_reg):
    n = skipped = 0
    wrapped = {}
    for fid, entry in list(mono_reg.items()):
        if not fid.startswith("fm_"):
            continue
        try:
            old_spec, old_paint = entry
        except Exception:
            skipped += 1
            continue
        if getattr(old_spec, "_fm_soul", False) or not callable(old_paint):
            continue
        tune = TUNE.get(fid, {})
        new_entry = (_mk_spec(fid, old_paint, tune), _mk_paint(old_paint, tune))
        mono_reg[fid] = new_entry
        wrapped[fid] = new_entry
        n += 1
    try:
        import engine.expansions.fusions as _fus
        _fus.FUSION_REGISTRY.update(wrapped)
    except Exception:
        pass
    msg = f"fractured-minds soul-physics retune: {n} finishes re-dialed (M252/B255/G-lanes + colorful crush)"
    if skipped:
        msg += f", {skipped} skipped (non-tuple entries)"
    return msg
