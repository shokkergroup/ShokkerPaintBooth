# -*- coding: utf-8 -*-
"""SIN ORCHID v2 (2026-06-11) — procedural recreation of the owner's noir
comic-ink orchid reference, CRUSHED: ~20x smaller blooms, ~50x more of them
(a wall-to-wall micro-garden on the 2048 canvas), plus the reference's soul:
zippo lighters, pink flames and curling smoke threading the dark gaps.

Spec: THE GARDEN BLOOMS IN SEQUENCE — three per-bloom gate groups detonate in
turn as the view sweeps (veins white-hot, petals mirror); every flame and
lighter stays pinned near-max at all angles; ink shadows stay dead matte.
"""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _curves, _flow_theta, _flowlines,
    _seed_int, _up, _m2, _pack, _WORK, _native_finish, _memo,
)


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


# ------------------------------------------------------------- micro orchid stamp
def _stamp_orchid(L, vein, lip, bid, cx, cy, R, rot, bloom_id, depth):
    """Tiny analytic moth orchid: 5 broad petals + comic outline + white rim +
    radial vein texture + crimson lip dot. All vectorized inside one window."""
    h, w = L.shape
    r_i = int(R * 1.3) + 2
    x0, x1 = max(0, int(cx) - r_i), min(w, int(cx) + r_i)
    y0, y1 = max(0, int(cy) - r_i), min(h, int(cy) + r_i)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    r = np.sqrt(dx * dx + dy * dy)
    th = np.arctan2(dy, dx)
    # 5-petal silhouette: radius swells per petal lobe (phalaenopsis-ish)
    lobe = 0.62 + 0.38 * np.abs(np.cos((th - rot) * 2.5))
    rmax = R * lobe
    t = r / np.maximum(rmax, 1e-3)
    m = t < 1.0
    # body: bright petal, tight dark throat, white rim, bold ink outline
    v = (0.82 + 0.18 * t)
    v *= (1.0 - 0.45 * np.exp(-(t * 6.5)))
    v = np.where((t > 0.86) & (t <= 0.94), 1.02, v)
    v = np.where(t > 0.94, 0.08, v)
    # radial vein texture (reads at tiny scale better than polylines)
    veins = np.clip(np.cos((th - rot) * 14.0), 0, 1) ** 3 * _sstep(0.18, 0.45, t) * (1 - _sstep(0.80, 0.9, t))
    v *= (1.0 - 0.38 * veins)
    L[y0:y1, x0:x1] = np.where(m, v * depth, L[y0:y1, x0:x1])
    bid[y0:y1, x0:x1] = np.where(m, bloom_id, bid[y0:y1, x0:x1])
    vein[y0:y1, x0:x1] = np.where(m, np.maximum(vein[y0:y1, x0:x1], veins), vein[y0:y1, x0:x1])
    lm = r < R * 0.14
    lip[y0:y1, x0:x1] = np.where(lm, 1.0, lip[y0:y1, x0:x1])
    L[y0:y1, x0:x1] = np.where(lm, 0.18 * depth, L[y0:y1, x0:x1])
    ring = (r >= R * 0.14) & (r < R * 0.20) & m
    L[y0:y1, x0:x1] = np.where(ring, 0.95 * depth, L[y0:y1, x0:x1])


# ------------------------------------------------------------- flame + lighter
def _stamp_flame(flame, core, cx, cy, Hf, rot):
    """Teardrop flame with wavy tip + hot core, rotated to any orientation."""
    h, w = flame.shape
    r_i = int(Hf * 1.2) + 2
    x0, x1 = max(0, int(cx) - r_i), min(w, int(cx) + r_i)
    y0, y1 = max(0, int(cy) - r_i), min(h, int(cy) + r_i)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    u = dx * np.cos(rot) + dy * np.sin(rot)          # along flame axis
    v = -dx * np.sin(rot) + dy * np.cos(rot)
    tt = np.clip(u / Hf, 0, 1)                        # 0=base 1=tip
    width = Hf * 0.34 * (1 - tt) ** 0.65 * (1 + 0.18 * np.sin(tt * 9.0))
    m = (u >= 0) & (u <= Hf) & (np.abs(v) < width)
    body = np.where(m, 1.0 - tt * 0.25, 0.0)
    flame[y0:y1, x0:x1] = np.maximum(flame[y0:y1, x0:x1], body)
    cm = (u >= 0) & (u <= Hf * 0.55) & (np.abs(v) < width * 0.42)
    core[y0:y1, x0:x1] = np.maximum(core[y0:y1, x0:x1], cm.astype(np.float32))


def _stamp_lighter(L, lit, cx, cy, Hl, rot):
    """Abstract zippo: silver rounded body + open lid, ink outline."""
    h, w = L.shape
    r_i = int(Hl * 1.3) + 2
    x0, x1 = max(0, int(cx) - r_i), min(w, int(cx) + r_i)
    y0, y1 = max(0, int(cy) - r_i), min(h, int(cy) + r_i)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    u = dx * np.cos(rot) + dy * np.sin(rot)
    v = -dx * np.sin(rot) + dy * np.cos(rot)
    bw, bh = Hl * 0.36, Hl * 0.52
    body = (np.abs(v) < bw) & (u > -bh) & (u < 0)
    lid = (np.abs(v - bw * 0.9) < bw * 0.78) & (u > 0) & (u < bh * 0.6)
    m = body | lid
    inner = ((np.abs(v) < bw - 1.6) & (u > -bh + 1.6) & (u < -1.6)) | \
            ((np.abs(v - bw * 0.9) < bw * 0.78 - 1.6) & (u > 1.6) & (u < bh * 0.6 - 1.6))
    edge = m & ~inner
    sheen = 0.55 + 0.35 * np.clip(np.sin((v / max(bw, 1e-3)) * 2.2 + 1.0), 0, 1)
    L[y0:y1, x0:x1] = np.where(m, sheen, L[y0:y1, x0:x1])
    L[y0:y1, x0:x1] = np.where(edge, 0.08, L[y0:y1, x0:x1])
    lit[y0:y1, x0:x1] = np.maximum(lit[y0:y1, x0:x1], m.astype(np.float32))


# ------------------------------------------------------------- fields
@_memo
def _sin_orchid_fields(h, w, s):
    rng = _rng(s, 3)
    sr = max(h, w) / 1024.0

    ink = np.zeros((h, w), np.float32)
    vein = np.zeros((h, w), np.float32)
    lip = np.zeros((h, w), np.float32)
    bid = np.zeros((h, w), np.float32)

    # --- noir backdrop: city silhouettes + halftone ---------------------------
    city = np.zeros((h, w), np.float32)
    for _ in range(6):
        cw, ch = int(rng.uniform(160, 300) * sr), int(rng.uniform(100, 190) * sr)
        tile = np.zeros((ch, cw), np.float32)
        x = 0
        while x < cw - 8:
            bw_ = int(rng.uniform(10, 28) * sr)
            bh_ = int(rng.uniform(0.35, 0.95) * ch)
            tile[ch - bh_:, x:x + bw_] = rng.uniform(0.5, 0.85)
            for wy in range(ch - bh_ + 2, ch - 2, max(2, int(4 * sr))):
                for wx in range(x + 1, min(x + bw_ - 1, cw), max(2, int(4 * sr))):
                    if rng.random() < 0.5:
                        tile[wy, wx] = 0.15
            x += bw_ + int(rng.uniform(2, 6) * sr)
        ang = rng.uniform(0, 360)
        M = cv2.getRotationMatrix2D((cw / 2, ch / 2), ang, 1.0)
        tile = cv2.warpAffine(tile, M, (cw, ch))
        cx, cy = int(rng.uniform(0, max(1, w - cw))), int(rng.uniform(0, max(1, h - ch)))
        city[cy:cy + ch, cx:cx + cw] = np.maximum(city[cy:cy + ch, cx:cx + cw], tile)
    city = _gauss(city, 1.0 * sr) * 0.55

    # --- SMOKE: curling wisps drifting through the dark gaps ------------------
    th_s = _flow_theta(h, w, s ^ 0x5A, scale=110, turns=2.2, swirls=5)
    smoke = np.maximum(
        _flowlines(h, w, s ^ 0x5B, n=int(900 * sr * sr), steps=60, step_len=2.2,
                   theta=th_s, thick=1, glow=3, fade=True),
        _flowlines(h, w, s ^ 0x5C, n=int(500 * sr * sr), steps=40, step_len=1.8,
                   theta=th_s, thick=2, glow=5, fade=True) * 0.7)
    smoke = np.clip(smoke + _gauss(smoke, 4 * sr) * 0.6, 0, 1)

    ink = 0.05 + city + smoke * 0.40

    # --- LIGHTERS (sparse, scattered rotations) -------------------------------
    lit = np.zeros((h, w), np.float32)
    flame = np.zeros((h, w), np.float32)
    fcore = np.zeros((h, w), np.float32)
    n_lt = int(7 * sr * sr) + 2
    for _ in range(n_lt):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        Hl = rng.uniform(34, 60) * sr
        rot = rng.uniform(0, 2 * np.pi)
        _stamp_lighter(ink, lit, cx, cy, Hl, rot)
        _stamp_flame(flame, fcore, cx + np.cos(rot) * 2, cy + np.sin(rot) * 2,
                     Hl * rng.uniform(0.8, 1.15), rot)
    # free flames (no lighter) licking through the garden
    for _ in range(int(16 * sr * sr) + 4):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        _stamp_flame(flame, fcore, cx, cy, rng.uniform(18, 44) * sr, rng.uniform(0, 2 * np.pi))

    # --- THE MICRO GARDEN: ~50x more blooms, ~20x smaller ---------------------
    n_bloom = int(950 * sr * sr) + 60
    blooms = []
    for i in range(n_bloom):
        R = rng.uniform(7.5, 19) * sr
        if rng.random() < 0.06:
            R *= rng.uniform(1.8, 2.6)          # rare mid-size feature blooms
        blooms.append((rng.uniform(0, w), rng.uniform(0, h), R, rng.uniform(0, 2 * np.pi)))
    blooms.sort(key=lambda b: b[2])
    for i, (cx, cy, R, rot) in enumerate(blooms):
        depth = 0.55 + 0.45 * (i + 1) / n_bloom
        _stamp_orchid(ink, vein, lip, bid, cx, cy, R, rot, i + 1, depth)

    # --- stipple + halftone ----------------------------------------------------
    stip = (_noise(h, w, s ^ 0x51, (1.4, 2.8)) > 0.60).astype(np.float32)
    clus = _sstep(0.45, 0.75, _noise(h, w, s ^ 0x52, (10, 26)))
    onb = (bid > 0).astype(np.float32)
    ink = np.clip(ink - stip * clus * onb * 0.30, 0, 1.1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dotg = (np.sin(xx * 0.62 / sr) * np.sin(yy * 0.62 / sr)) > 0.3
    ink = np.clip(ink + dotg.astype(np.float32) * _sstep(0.12, 0.4, 1 - ink) * 0.10, 0, 1.1)

    per = _n01(np.sin(bid * 12.9898) + 1.0) * onb
    return ink, vein, lip, bid, per, smoke, flame, fcore, lit, city


# ------------------------------------------------------------- paint
def _sin_orchid_paint(h, w, s):
    ink, vein, lip, bid, per, smoke, flame, fcore, lit, city = _sin_orchid_fields(h, w, s)
    g = np.clip(ink, 0, 1)[..., None]
    body = g * np.float32([0.90, 0.90, 0.95])[None, None, :]      # silver ink

    onb = (bid > 0).astype(np.float32)
    mag = (_sstep(0.30, 0.40, per) * (1 - _sstep(0.66, 0.74, per))) * onb
    pur = _sstep(0.70, 0.78, per) * onb
    body *= (1 - mag[..., None] * 0.72) + np.float32([1.0, 0.10, 0.58])[None, None, :] * (mag * 0.72)[..., None]
    body *= (1 - pur[..., None] * 0.78) + np.float32([0.58, 0.08, 0.92])[None, None, :] * (pur * 0.78)[..., None]
    # crimson lips
    body = body * (1 - lip[..., None] * 0.75) + np.float32([0.55, 0.02, 0.10])[None, None, :] * (lip * 0.6)[..., None]
    # smoke: cool silver-violet wisps
    body += np.float32([0.62, 0.58, 0.75])[None, None, :] * (smoke * 0.30)[..., None]
    # flames: hot pink-red bodies with white-gold cores + glow
    fl_glow = _gauss(flame, 5)
    body += np.float32([0.95, 0.06, 0.28])[None, None, :] * (flame * 0.9)[..., None]
    body += np.float32([1.0, 0.85, 0.55])[None, None, :] * (fcore * 0.85)[..., None]
    body += np.float32([0.9, 0.12, 0.35])[None, None, :] * (fl_glow * 0.35)[..., None]
    return np.clip(body, 0, 1).astype(np.float32)


# ------------------------------------------------------------- spec
def _sin_orchid_spec(h, w, s):
    ink, vein, lip, bid, per, smoke, flame, fcore, lit, city = _sin_orchid_fields(h, w, s)
    onb = (bid > 0).astype(np.float32)
    grp = np.floor(per * 3.0) % 3
    gateA = (grp == 0).astype(np.float32) * onb
    gateB = (grp == 1).astype(np.float32) * onb

    M = (28 + 150 * np.clip(ink, 0, 1) * onb + 50 * gateA
         + 70 * lit + 45 * flame + 25 * city)
    R = (155 - 100 * onb * gateA - 60 * lit - 70 * flame
         + 55 * (_noise(h, w, s ^ 0x77, (1.8, 3.6)) - 0.5)
         + 40 * smoke + 40 * (1 - np.clip(ink, 0, 1)))
    Cc = (14 + 205 * vein * gateA + 90 * vein * gateB
          + 215 * lip + 235 * fcore + 150 * flame + 90 * lit
          + 45 * gateA * np.clip(ink, 0, 1))
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 16, 255).astype(np.float32),
            np.clip(Cc, 0, 255).astype(np.float32))


# ------------------------------------------------------------- wiring
def install_into_engine(mono_reg, base_reg=None):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        eff = _up(_sin_orchid_paint(_WORK, _WORK, _seed_int(seed)), fh, fw)
        eff = _native_finish(eff, seed, grain=0.07)
        base = np.asarray(paint, np.float32)[:, :, :3]
        m = (_m2(mask, fh, fw) * float(pm))[..., None]
        return np.clip(base * (1.0 - m) + eff * m, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        M, R, Cc = _sin_orchid_spec(_WORK, _WORK, _seed_int(seed))
        return _pack(_up(M, fh, fw), _up(R, fh, fw), _up(Cc, fh, fw),
                     _m2(mask, fh, fw), float(sm))

    entry = (spec_fn, paint_fn)
    mono_reg["spectrum_sin_orchid"] = entry
    mono_reg.pop("sin_orchid", None)
    # join the Spectrum Shift picker lane (built from FUSION_REGISTRY spectrum_*)
    try:
        import engine.expansions.fusions as _fus
        _fus.FUSION_REGISTRY["spectrum_sin_orchid"] = entry
        _fus.FUSION_REGISTRY.pop("sin_orchid", None)
    except Exception:
        pass
    return "sin-orchid v2 registered as spectrum_sin_orchid (Spectrum Shift lane)"
