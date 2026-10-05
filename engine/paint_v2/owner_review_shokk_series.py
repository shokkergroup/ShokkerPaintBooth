"""Owner-review Shokk Series source renderers for SPB-30.

The original Shokk set had several dead-flat or oversized outputs. These are
native base renderers, not wrappers around previous paint, with each finish
using a different topology tuned for 2048-scale detail.
"""

from __future__ import annotations

import numpy as np

try:
    import cv2 as _cv2
    _CV2_OK = True
except Exception:  # pragma: no cover - cv2 always present in app env
    _cv2 = None
    _CV2_OK = False

# Smooth carrier geometry (band-limited sinusoids of position) is computed at a
# capped working resolution and bilinearly upscaled; the softening is invisible
# because every per-mode field here is a low/mid-frequency sine field. Only the
# per-pixel hash noise (_hash) and its thresholded sparkle/speckle/static/star
# binary terms stay at FULL resolution so noise density / grain is unchanged.
_FIELD_CAP = 1024
# "cipher"/"void" draw razor-thin (sub-2px) line motifs via large clamp
# multipliers (1 - grid*18 / wisps*18). The smooth carriers are still capped
# for speed, but the thin-line geometry itself is recomputed at FULL resolution
# (see _thin_lines) and re-injected so the lines stay crisp.
_THIN_MODES = ("cipher", "void")


def _thin_lines(h, w, seed, cfg, base_full):
    """Full-resolution thin-line geometry for cipher/void modes.

    base_full is the (already upscaled) smooth wave field; the line term is a
    cheap 1-2 sin evaluation so doing it at full res is nearly free but keeps
    the razor-thin lines from blurring under upscale.
    """
    x, y = _xy((h, w))
    mode = cfg["mode"]
    if mode == "cipher":
        grid = np.minimum(
            np.abs(np.sin(x * cfg["freq"] * np.pi)),
            np.abs(np.sin(y * cfg["freq"] * 0.83 * np.pi)),
        )
        return (1.0 - grid * 18.0).astype(np.float32)
    # void
    cx = x - cfg.get("cx", 0.5)
    cy = y - cfg.get("cy", 0.5)
    dist = np.sqrt(cx * cx + cy * cy)
    wisps = np.clip(1.0 - np.abs(np.sin((base_full * cfg["freq"] + dist * 8.0) * np.pi)) * 18.0, 0, 1)
    return wisps.astype(np.float32)


def _work_shape(h, w, cap=_FIELD_CAP):
    h = int(h)
    w = int(w)
    if max(h, w) <= cap:
        return h, w
    s = float(cap) / float(max(h, w))
    return max(2, int(round(h * s))), max(2, int(round(w * s)))


def _upscale(field, h, w):
    field = np.asarray(field, dtype=np.float32)
    if field.shape[:2] == (h, w):
        return field
    if _CV2_OK:
        return _cv2.resize(field, (w, h), interpolation=_cv2.INTER_LINEAR).astype(np.float32)
    # Fallback: nearest-neighbour index map (rarely hit; cv2 ships with the app)
    yi = np.clip((np.arange(h) * field.shape[0] / h).astype(np.int64), 0, field.shape[0] - 1)
    xi = np.clip((np.arange(w) * field.shape[1] / w).astype(np.int64), 0, field.shape[1] - 1)
    return field[yi][:, xi].astype(np.float32)


def _xy(shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _ensure_bb(bb, shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    if bb is None:
        return np.zeros((h, w), dtype=np.float32)
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 0:
        return np.full((h, w), float(arr), dtype=np.float32)
    if arr.ndim == 3:
        return arr[:h, :w, :3].mean(axis=2).astype(np.float32)
    return arr[:h, :w].astype(np.float32)


def _norm(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def _hsv_to_rgb(h, s, v):
    h6 = (h * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p, np.where(i == 3, p, np.where(i == 4, t, v)))))
    g = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v, np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t, np.where(i == 3, v, np.where(i == 4, v, q)))))
    return np.stack([r, g, b], axis=2).astype(np.float32)


def _palette(hues, t):
    hues = np.asarray(hues, dtype=np.float32) % 1.0
    n = len(hues)
    pos = np.clip(t, 0.0, 0.9999) * n
    idx = np.floor(pos).astype(np.int32) % n
    frac = pos - np.floor(pos)
    a = hues[idx]
    b = hues[(idx + 1) % n]
    delta = ((b - a + 0.5) % 1.0) - 0.5
    return (a + delta * frac) % 1.0


def _hash(shape, seed, salt):
    x, y = _xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + (seed + salt) * 0.137) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _hnoise_terms(shape, seed, cfg):
    """Per-pixel hash-noise binary terms, always at FULL resolution.

    Returns the thresholded contributions that each mode mixes into motif/field
    plus the universal sparkle layer. Keeping these full-res preserves grain
    density / sparkle count exactly while the smooth carriers are capped.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    hnoise = _hash((h, w), seed, cfg["salt"])
    sparkle = (hnoise > cfg.get("spark_threshold", 0.982)).astype(np.float32)
    return hnoise, sparkle


def _waves(shape, seed, cfg):
    x, y = _xy(shape)
    phase = ((int(seed) + cfg["salt"]) % 4096) * 0.017
    f = cfg["freq"]
    return (
        np.sin((x * f + y * f * 0.37 + phase) * np.pi) * 0.42
        + np.sin((x * f * 0.41 - y * f * 0.83 + phase * 1.7) * np.pi) * 0.31
        + np.sin((x * f * 1.71 + y * f * 1.29 + phase * 0.6) * np.pi) * 0.18
        + np.sin((x * f * 3.13 - y * f * 2.47 + phase * 2.2) * np.pi) * 0.09
    ).astype(np.float32)


def _cracks(shape, seed, cfg):
    x, y = _xy(shape)
    phase = ((int(seed) + cfg["salt"]) % 997) * 0.019
    f = cfg["freq"]
    a = np.abs(np.sin((x * f + y * f * 0.32 + phase) * np.pi))
    b = np.abs(np.sin((x * -f * 0.43 + y * f * 0.88 + phase * 1.3) * np.pi))
    c = np.abs(np.sin((x * f * 0.71 - y * f * 0.61 + phase * 0.7) * np.pi))
    return np.clip(1.0 - np.minimum(np.minimum(a, b), c) * cfg.get("crack_width", 25.0), 0.0, 1.0).astype(np.float32)


def _field_smooth(shape, seed, cfg):
    """Smooth (band-limited) carriers only; safe to compute at capped res.

    Returns (field_s, motif_s, micro) built purely from sinusoidal/position
    geometry. The per-pixel hash-noise binary terms are injected later at full
    resolution by ``_field`` so grain density is unchanged.
    """
    x, y = _xy(shape)
    cx = x - cfg.get("cx", 0.5)
    cy = y - cfg.get("cy", 0.5)
    dist = np.sqrt(cx * cx + cy * cy)
    ang = np.arctan2(cy, cx)
    base = _norm(_waves(shape, seed, cfg))
    crack = _cracks(shape, seed, cfg)
    mode = cfg["mode"]

    if mode == "speckle":
        motif = crack * 0.35 + base * 0.35
        field = base * 0.55
    elif mode == "branch":
        motif = crack
        field = _norm(crack * 0.7 + base * 0.3)
    elif mode == "liquid":
        ripples = np.sin((dist * cfg["freq"] * 4.0 + base * 2.4) * np.pi)
        motif = np.abs(ripples) * 0.72 + crack * 0.18
        field = _norm(ripples + base * 0.55)
    elif mode == "static":
        motif = crack * 0.30
        field = base * 0.6
    elif mode == "cells":
        warp = base * 0.045
        gx = np.floor((x + warp) * cfg["freq"])
        gy = np.floor((y - warp * 0.7) * cfg["freq"] * 0.82)
        cell_hash = np.sin((gx * 127.1 + gy * 311.7 + cfg["salt"] * 19.19) * 43758.5453)
        cell = (cell_hash - np.floor(cell_hash)).astype(np.float32)
        edge_x = np.abs(((x + warp) * cfg["freq"]) - gx - 0.5) * 2.0
        edge_y = np.abs(((y - warp * 0.7) * cfg["freq"] * 0.82) - gy - 0.5) * 2.0
        edge = np.clip(1.0 - np.maximum(edge_x, edge_y) * 8.0, 0, 1)
        field = _norm(cell * 0.82 + base * 0.18)
        motif = np.clip(edge * 0.75 + crack * 0.28 + np.abs(field - 0.5) * 0.35, 0, 1)
    elif mode == "void":
        # wisps recomputed at full res in _field via _thin_lines; placeholders.
        motif = base * 0.0
        field = base * 0.15
    elif mode == "helix":
        strand_a = np.clip(1.0 - np.abs(np.sin((x * cfg["freq"] + np.sin(y * 11.0) * 0.7) * np.pi)) * 22.0, 0, 1)
        strand_b = np.clip(1.0 - np.abs(np.sin((x * cfg["freq"] - np.sin(y * 11.0) * 0.7 + 0.5) * np.pi)) * 22.0, 0, 1)
        ribs = np.clip(1.0 - np.abs(np.sin(y * cfg["freq"] * 3.0 * np.pi)) * 17.0, 0, 1)
        motif = np.clip(strand_a + strand_b + ribs * 0.45, 0, 1)
        field = _norm(strand_a * 0.7 + strand_b * 0.25 + base * 0.3)
    elif mode == "reactor":
        ring = np.clip(1.0 - np.abs(np.sin((dist * cfg["freq"] * 5.2 + base * 0.5) * np.pi)) * 16.0, 0, 1)
        spokes = np.clip(1.0 - np.abs(np.sin((ang * cfg.get("spokes", 12.0) + base) * np.pi)) * 24.0, 0, 1)
        arc = np.clip(1.0 - np.abs(np.sin((dist * cfg["freq"] * 13.0 - ang * 5.0 + base * 1.7) * np.pi)) * 26.0, 0, 1)
        motif = np.clip(ring * 0.72 + spokes * 0.48 + arc * 0.55 + crack * 0.20, 0, 1)
        field = _norm(ring * 0.52 + spokes * 0.31 + arc * 0.42 + base * 0.28)
    elif mode == "vortex":
        spiral = np.sin((dist * cfg["freq"] * 4.8 + ang * cfg.get("twist", 3.0) + base * 1.2) * np.pi)
        motif = np.clip(1.0 - np.abs(spiral) * 10.0, 0, 1)
        field = _norm(spiral + base * 0.45)
    elif mode == "cipher":
        # grid recomputed at full res in _field via _thin_lines; placeholders.
        motif = base * 0.0
        field = base * 0.2
    else:
        motif = np.clip(crack * 0.45 + base * 0.55, 0, 1)
        field = base * 0.7

    micro = _norm(
        np.sin((x * cfg["micro"] + y * cfg["micro"] * 0.61 + cfg["salt"]) * np.pi)
        + np.sin((x * cfg["micro"] * 1.91 - y * cfg["micro"] * 1.33 + seed * 0.07) * np.pi) * 0.55
    )
    return (field.astype(np.float32), motif.astype(np.float32),
            micro.astype(np.float32), base.astype(np.float32))


def _field(shape, seed, cfg):
    h, w = shape[:2] if len(shape) > 2 else shape
    mode = cfg["mode"]
    wh, ww = _work_shape(h, w, _FIELD_CAP)

    # Smooth carriers at capped resolution -> upscale (softening invisible).
    field_s, motif_s, micro_s, base_s = _field_smooth((wh, ww), seed, cfg)
    if (wh, ww) != (h, w):
        field_s = _upscale(field_s, h, w)
        motif_s = _upscale(motif_s, h, w)
        micro = _upscale(micro_s, h, w)
        base_s = _upscale(base_s, h, w)
    else:
        micro = micro_s

    # Thin-line modes (cipher/void): recompute their razor-thin geometry at FULL
    # resolution from the (cheap) line term so the lines stay crisp; the smooth
    # field carriers came from the capped pass above.
    if mode == "cipher":
        line = _thin_lines(h, w, seed, cfg, base_s)   # = 1 - grid*18 (unclipped)
        motif_s = line                                # crack/base not used by cipher motif
    elif mode == "void":
        wisps = _thin_lines(h, w, seed, cfg, base_s)  # clipped 0..1
        motif_s = wisps * 0.65
        field_s = wisps * 0.5 + base_s * 0.15         # raw; single _norm with stars below

    # Per-pixel hash noise + sparkle stay at FULL resolution.
    hnoise, sparkle = _hnoise_terms((h, w), seed, cfg)

    # Re-inject the full-res hash-noise binary terms exactly where the original
    # mixed them, so the recombined field/motif matches the un-capped output.
    if mode == "speckle":
        motif = np.clip((hnoise > 0.88).astype(np.float32) + motif_s, 0, 1)
        field = _norm(field_s + hnoise * 0.45)
    elif mode == "branch":
        motif = np.clip(motif_s + (hnoise > 0.965).astype(np.float32) * 0.65, 0, 1)
        field = field_s
    elif mode == "static":
        snow = (hnoise > 0.52).astype(np.float32)
        motif = np.clip(snow * 0.62 + motif_s, 0, 1)
        field = _norm(snow * 0.4 + field_s)
    elif mode == "void":
        stars = (hnoise > 0.992).astype(np.float32)
        motif = np.clip(motif_s + stars, 0, 1)
        field = _norm(field_s + stars * 1.5)
    elif mode == "cipher":
        bits = (hnoise > 0.76).astype(np.float32)
        motif = np.clip(motif_s + bits * 0.35, 0, 1)
        field = _norm(motif * 0.8 + field_s)
    elif mode in ("liquid", "cells", "helix", "reactor", "vortex"):
        motif = motif_s
        field = field_s
    else:
        motif = motif_s
        field = _norm(field_s + hnoise * 0.3)

    return field.astype(np.float32), motif.astype(np.float32), micro.astype(np.float32), sparkle


def _make_paint(cfg):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = shape[:2] if len(shape) > 2 else shape
        mask_arr = np.asarray(mask, dtype=np.float32)
        bb_arr = _ensure_bb(bb, (h, w))
        base = paint[:, :, :3].astype(np.float32, copy=True)
        field, motif, micro, sparkle = _field((h, w), seed, cfg)
        hue = _palette(cfg["hues"], np.clip(field + motif * cfg.get("motif_hue", 0.12) + (micro - 0.5) * 0.06, 0, 1))
        sat = np.clip(cfg.get("sat", 0.86) + motif * 0.12 + (micro - 0.5) * 0.06, 0, 1)
        val = np.clip(cfg.get("val", 0.48) + field * cfg.get("val_span", 0.28) + motif * 0.24 + sparkle * 0.30, 0, 1)
        if cfg.get("dark"):
            val *= np.clip(0.18 + field * 0.40 + motif * 0.42 + sparkle * 0.40, 0, 1)
        target = _hsv_to_rgb(hue, sat, val)
        tint = np.array(cfg.get("tint", (0.0, 0.0, 0.0)), dtype=np.float32).reshape(1, 1, 3)
        target = np.clip(target + tint * motif[:, :, None] * 0.22 + sparkle[:, :, None] * 0.14, 0, 1)
        blend = cfg.get("blend", 0.88) * float(pm) * mask_arr[:, :, None]
        out = base * (1.0 - blend) + target * blend
        out = np.clip(out + bb_arr[:, :, None] * cfg.get("bb", 0.08) * mask_arr[:, :, None], 0, 1)
        return np.ascontiguousarray(out.astype(np.float32))

    return paint_fn


def _make_spec(cfg):
    def spec_fn(shape, seed, sm, base_m, base_r):
        h, w = shape[:2] if len(shape) > 2 else shape
        field, motif, micro, sparkle = _field((h, w), seed, cfg)
        # 2026-06-20 SHOKK SERIES rework — add fake-3D DEPTH + MOTION and DECORRELATE.
        # The old spec drove M and Cc from the SAME field+motif (|corr| 0.73–0.97, fails
        # the <0.85 gate) and had no relief/motion. The field already IS the paint
        # geometry (shared with paint_fn), so treat it as a HEIGHT field: 2-sun Lambert
        # bevels give the RD veins sculpted 3D, a traveling shift adds the in-sim moving
        # glint, and Cc/R move onto their OWN geometry (other-sun bevel / independent
        # grain) so the three channels decorrelate while M keeps the vein signature.
        try:
            from engine.paint_v2 import depth3d_2026 as _d3
            # bevels + motion are smooth macro fields → solve on a downscaled field and
            # upscale (near-free vs the full-res _field; keeps the spec well under budget).
            _cap = 640
            ih, iw = int(h), int(w)
            if max(ih, iw) > _cap:
                _wh = max(2, int(round(ih * _cap / max(ih, iw))))
                _ww = max(2, int(round(iw * _cap / max(ih, iw))))
                fs = _d3._resize(field, _wh, _ww)
            else:
                _wh, _ww, fs = ih, iw, field
            nrm = _d3.height_to_normals(fs, strength=2.3)
            bevelA = _d3.shade_bevels(nrm, light_dir=(0.55, 0.42, 0.72), ambient=0.16, gamma=1.08)
            bevelB = _d3.shade_bevels(nrm, light_dir=(-0.46, -0.38, 0.74), ambient=0.20, gamma=0.92)
            phase = float((int(cfg.get("salt", 101)) % 19) * 0.331)
            motA = _d3.traveling_colorshift(fs, phase, bands=6.5, sharpness=1.9)
            motB = _d3.traveling_colorshift(fs, phase + 2.1, bands=4.5, sharpness=1.7,
                                            direction=(0.35, 1.0))
            if (_wh, _ww) != (ih, iw):
                bevelA = _d3._resize(bevelA, ih, iw); bevelB = _d3._resize(bevelB, ih, iw)
                motA = _d3._resize(motA, ih, iw); motB = _d3._resize(motB, ih, iw)
        except Exception:
            bevelA = np.full_like(field, 0.5); bevelB = np.full_like(field, 0.5)
            motA = np.full_like(field, 0.5); motB = np.full_like(field, 0.5)
        rng = np.random.default_rng((int(seed) + int(cfg.get("salt", 101)) * 131 + 977) & 0xFFFFFFFF)
        grainR = rng.random((int(h), int(w)), dtype=np.float32)

        # M: vein signature (motif+sparkle+field) + bevel relief + traveling motion.
        m = (cfg.get("m", base_m) + field * cfg.get("m_span", 46.0) + motif * 42.0
             + sparkle * 58.0 + (micro - 0.5) * 16.0
             + (bevelA - 0.5) * 40.0 + (motA - 0.5) * 22.0)
        # R: independent grain + shadowed slope + INVERSE paint field (rough where the
        # design is dark) — still mirrors the paint, but as M's inverse so they decorrelate.
        r = (cfg.get("r", base_r) + grainR * (cfg.get("r_span", 34.0) * 0.62)
             + (1.0 - field) * (cfg.get("r_span", 34.0) * 0.5)
             + (1.0 - bevelA) * 10.0 - sparkle * 6.0 + (micro - 0.5) * 8.0)
        # Cc: other-sun bevel + own motion phase + a touch of direct field (mirrors paint,
        # but via the orthogonal sun + phase so it stays decorrelated from M).
        cc = (cfg.get("cc", 22.0) + bevelB * (cfg.get("cc_span", 18.0) * 1.2)
              + field * (cfg.get("cc_span", 18.0) * 0.5) + motB * 14.0 + motif * 8.0)
        return (
            np.clip(m * float(sm), 0, 255).astype(np.float32),
            np.clip(r, 15, 255).astype(np.float32),
            np.clip(cc, 16, 255).astype(np.float32),
        )

    return spec_fn


_CONFIGS = {
    "burnt_headers": dict(mode="speckle", hues=[0.60, 0.78, 0.94, 0.08, 0.13], freq=32.0, micro=120.0, salt=101, sat=0.88, val=0.38, val_span=0.34, m=170, r=54, cc=38, tint=(0.25, 0.08, 0.01)),
    "electric_ice": dict(mode="branch", hues=[0.48, 0.55, 0.63, 0.70], freq=34.0, micro=138.0, salt=102, sat=0.72, val=0.48, val_span=0.34, m=208, r=18, cc=18, tint=(0.0, 0.16, 0.22), crack_width=20.0),
    "mercury": dict(mode="liquid", hues=[0.55, 0.61, 0.72, 0.05], freq=26.0, micro=104.0, salt=103, sat=0.38, val=0.54, val_span=0.34, m=230, r=10, cc=16, tint=(0.10, 0.10, 0.12)),
    "plasma_metal": dict(mode="branch", hues=[0.46, 0.58, 0.78, 0.91], freq=42.0, micro=150.0, salt=104, sat=0.84, val=0.38, val_span=0.38, m=220, r=16, cc=18, tint=(0.02, 0.16, 0.20), crack_width=17.0),
    "shokk_blood": dict(mode="branch", hues=[0.98, 0.00, 0.03, 0.95], freq=38.0, micro=132.0, salt=105, sat=0.92, val=0.34, val_span=0.30, m=196, r=22, cc=20, tint=(0.30, 0.0, 0.0), crack_width=18.0),
    "shokk_pulse": dict(mode="liquid", hues=[0.78, 0.86, 0.93, 0.72], freq=28.0, micro=128.0, salt=106, sat=0.90, val=0.34, val_span=0.42, m=206, r=18, cc=18, tint=(0.18, 0.02, 0.23)),
    "shokk_static": dict(mode="static", hues=[0.53, 0.61, 0.72, 0.15], freq=58.0, micro=190.0, salt=107, sat=0.55, val=0.32, val_span=0.30, m=185, r=42, cc=34, tint=(0.06, 0.10, 0.16)),
    "shokk_venom": dict(mode="cells", hues=[0.22, 0.30, 0.36, 0.17], freq=40.0, micro=150.0, salt=108, sat=0.96, val=0.24, val_span=0.48, m=176, r=44, cc=36, tint=(0.06, 0.25, 0.0)),
    "shokk_void": dict(mode="void", hues=[0.62, 0.72, 0.82, 0.92], freq=34.0, micro=142.0, salt=109, sat=0.82, val=0.28, val_span=0.28, m=98, r=96, cc=76, dark=True, tint=(0.03, 0.01, 0.16), spark_threshold=0.988),
    "volcanic": dict(mode="branch", hues=[0.00, 0.04, 0.09, 0.13], freq=44.0, micro=130.0, salt=110, sat=0.95, val=0.28, val_span=0.48, m=138, r=86, cc=60, tint=(0.30, 0.07, 0.0), crack_width=15.0),
    "shokk_flux": dict(mode="liquid", hues=[0.02, 0.15, 0.38, 0.58, 0.78, 0.92], freq=40.0, micro=170.0, salt=111, sat=0.92, val=0.42, val_span=0.40, m=214, r=18, cc=16),
    "shokk_phase": dict(mode="cells", hues=[0.08, 0.20, 0.38, 0.56, 0.76, 0.90], freq=54.0, micro=156.0, salt=112, sat=0.90, val=0.45, val_span=0.34, m=202, r=22, cc=18),
    "shokk_dual": dict(mode="cells", hues=[0.00, 0.58, 0.97, 0.11], freq=30.0, micro=118.0, salt=113, sat=0.88, val=0.42, val_span=0.34, m=190, r=34, cc=26),
    "shokk_spectrum": dict(mode="liquid", hues=[0.00, 0.12, 0.28, 0.47, 0.62, 0.78, 0.91], freq=50.0, micro=180.0, salt=114, sat=0.95, val=0.46, val_span=0.38, m=216, r=16, cc=18),
    "shokk_aurora": dict(mode="liquid", hues=[0.34, 0.48, 0.62, 0.76, 0.88], freq=36.0, micro=150.0, salt=115, sat=0.86, val=0.42, val_span=0.38, m=194, r=22, cc=18),
    "shokk_helix": dict(mode="helix", hues=[0.42, 0.56, 0.80, 0.92], freq=20.0, micro=132.0, salt=116, sat=0.88, val=0.38, val_span=0.42, m=198, r=24, cc=20),
    "shokk_catalyst": dict(mode="reactor", hues=[0.02, 0.11, 0.28, 0.56, 0.74], freq=18.0, micro=128.0, salt=117, sat=0.94, val=0.42, val_span=0.36, m=205, r=18, cc=18, spokes=10.0),
    "shokk_mirage": dict(mode="liquid", hues=[0.45, 0.52, 0.62, 0.91], freq=44.0, micro=165.0, salt=118, sat=0.64, val=0.32, val_span=0.32, m=152, r=64, cc=44, tint=(0.04, 0.14, 0.16), dark=True),
    "shokk_polarity": dict(mode="static", hues=[0.06, 0.12, 0.58, 0.66], freq=62.0, micro=176.0, salt=119, sat=0.88, val=0.42, val_span=0.34, m=188, r=36, cc=26),
    "shokk_reactor": dict(mode="reactor", hues=[0.52, 0.35, 0.17, 0.08], freq=24.0, micro=144.0, salt=120, sat=0.92, val=0.30, val_span=0.52, m=215, r=14, cc=16, spokes=18.0),
    "shokk_prism": dict(mode="cells", hues=[0.00, 0.14, 0.30, 0.50, 0.70, 0.86], freq=70.0, micro=200.0, salt=121, sat=0.92, val=0.46, val_span=0.36, m=216, r=16, cc=18),
    "shokk_wraith": dict(mode="void", hues=[0.54, 0.68, 0.78, 0.90], freq=42.0, micro=150.0, salt=122, sat=0.50, val=0.26, val_span=0.30, m=112, r=92, cc=62, dark=True, tint=(0.04, 0.06, 0.12)),
    "shokk_tesseract_v2": dict(mode="cipher", hues=[0.55, 0.77, 0.02, 0.14], freq=34.0, micro=150.0, salt=123, sat=0.88, val=0.38, val_span=0.38, m=202, r=24, cc=20),
    "shokk_fusion_base": dict(mode="reactor", hues=[0.00, 0.07, 0.13, 0.55], freq=30.0, micro=160.0, salt=124, sat=0.94, val=0.30, val_span=0.54, m=222, r=12, cc=16, spokes=22.0),
    "shokk_rift": dict(mode="branch", hues=[0.58, 0.64, 0.03, 0.09], freq=46.0, micro=156.0, salt=125, sat=0.92, val=0.40, val_span=0.40, m=196, r=26, cc=20, crack_width=16.0),
    "shokk_vortex": dict(mode="vortex", hues=[0.58, 0.74, 0.88, 0.04, 0.13], freq=26.0, micro=154.0, salt=126, sat=0.94, val=0.42, val_span=0.40, m=210, r=16, cc=18, twist=5.0),
    "shokk_surge": dict(mode="branch", hues=[0.50, 0.57, 0.67, 0.82], freq=58.0, micro=190.0, salt=127, sat=0.94, val=0.38, val_span=0.44, m=214, r=14, cc=16, crack_width=14.0),
    "shokk_cipher": dict(mode="cipher", hues=[0.36, 0.48, 0.58, 0.74], freq=48.0, micro=180.0, salt=128, sat=0.76, val=0.24, val_span=0.36, m=160, r=58, cc=42, dark=True),
    "shokk_inferno": dict(mode="speckle", hues=[0.00, 0.04, 0.09, 0.15], freq=52.0, micro=180.0, salt=129, sat=0.96, val=0.34, val_span=0.52, m=178, r=50, cc=32, tint=(0.28, 0.08, 0.0), spark_threshold=0.975),
    "shokk_apex": dict(mode="cells", hues=[0.78, 0.92, 0.08, 0.30, 0.55], freq=64.0, micro=210.0, salt=130, sat=0.95, val=0.46, val_span=0.40, m=225, r=12, cc=16),
}


OWNER_REVIEW_SHOKK_OVERRIDES = {
    finish_id: (_make_paint(cfg), _make_spec(cfg)) for finish_id, cfg in _CONFIGS.items()
}
