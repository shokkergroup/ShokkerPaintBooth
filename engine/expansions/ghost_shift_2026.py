# -*- coding: utf-8 -*-
"""GHOST SHIFT (2026-06-11) — the owner found it: GHOST FRACTURE used as a BASE
with the color crushed near-black produces real angle-driven color flashes in
iRacing (dark red flashes teal, purple flashes green, green flashes gold).

THE EXTRACTED MECHANISM (see wiki Finish Doctrine "Ghost Shift recipe"):
  1. METAL ~176-255 everywhere -> reflections are TINTED BY THE PAINT HUE even
     when the paint is crushed dark (the body-hue flash lobe).
  2. CLEARCOAT CARVED BY THE PATTERN (B = 212 - pattern*148 + edge*46): big
     coherent cells swing ~64 <-> 255. Clearcoat is a PAINT-INDEPENDENT white
     lobe -> the HIGH cells mirror the ENVIRONMENT: teal-blue sky dome at one
     angle, gold sun/tarmac at another. That env travel IS the color shift.
  3. ROUGHNESS LOW-ish (58-130), glossiest on cell edges -> sharp flashes.
  4. The owner crushes the base color near black -> diffuse goes to zero, so
     the two specular lobes are all you see: metal cells stay dark (off),
     clearcoat cells flash sky/sun (on) -> on/off patchwork sweeps with angle.

This module = the SAME spec contract on six new coherent-cell geometries.
Use as a BASE, pick a color, drag brightness way down, daytime track.
"""
import numpy as np
import cv2

from engine.expansions.redesign_wave2_2026 import (
    _rng, _noise, _n01, _sstep, _gauss, _coords, _warp, _crystal, _gray_scott,
    _flow_theta, _flowlines, _seed_int, _memo, _sr,
)

_WORKG = 1024


def _edges_of(pattern, sr):
    gy, gx = np.gradient(_gauss(pattern, 1.5))
    return np.clip(_n01(np.abs(gx) + np.abs(gy)) * 2.2, 0, 1)


_GS_CACHE = {}


def _gs_fields(h, w, s, mode="tessellate"):
    _k = (mode, h, w, s)
    if _k in _GS_CACHE:
        return _GS_CACHE[_k]
    if len(_GS_CACHE) > 8:
        _GS_CACHE.pop(next(iter(_GS_CACHE)))
    out = _gs_fields_build(h, w, s, mode)
    _GS_CACHE[_k] = out
    return out


def _gs_fields_build(h, w, s, mode="tessellate"):
    """(pattern, detail, micro, edge) — pattern must be COHERENT large cells
    (the clearcoat carve only reads at distance when zones are big)."""
    sr = _sr(h, w)
    rng = _rng(s, 5)
    if mode == "tessellate":
        cid, edge_d, orient, axial = _crystal(h, w, s, n_sites=150, aniso=2.4, res=0.5)
        per = _n01(np.sin(cid * 12.99) + 1)
        pattern = _sstep(0.46, 0.54, per)
    elif mode == "riverine":
        rd = _gray_scott(h, w, s, "maze", iters=420, grid=448, seeds=30, fine=0.85, speckle=0.05)
        pattern = _sstep(0.46, 0.58, rd)
    elif mode == "weave":
        yy, xx = _coords(h, w)
        a = float(rng.uniform(0, np.pi))
        wy, wx = _warp(yy, xx, h, w, s ^ 0x21, 30 * sr)
        p = 120 * sr
        u = wx * np.cos(a) + wy * np.sin(a)
        v = -wx * np.sin(a) + wy * np.cos(a)
        pattern = ((np.floor(u / p) + np.floor(v / p)) % 2).astype(np.float32)
    elif mode == "magma":
        cid, edge_d, orient, axial = _crystal(h, w, s, n_sites=420, aniso=1.6, res=0.5)
        per = _n01(np.sin(cid * 12.99) + 1)
        pattern = _sstep(0.40, 0.48, per)
    elif mode == "serpentine":
        yy, xx = _coords(h, w)
        a = float(rng.uniform(0, np.pi))
        wy, wx = _warp(yy, xx, h, w, s ^ 0x31, 140 * sr)
        u = wx * np.cos(a) + wy * np.sin(a)
        pattern = (0.5 + 0.5 * np.sin(u * (2 * np.pi / (170 * sr)))).astype(np.float32)
        pattern = _sstep(0.42, 0.58, pattern)
    else:  # orbital
        yy, xx = _coords(h, w)
        acc = np.zeros((h, w), np.float32)
        for _ in range(5):
            cx, cy = rng.uniform(-0.3, 1.3) * w, rng.uniform(-0.3, 1.3) * h
            r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            acc += np.sin(r * (2 * np.pi / (rng.uniform(130, 240) * sr)))
        pattern = _sstep(0.48, 0.56, _n01(acc))
    detail = _noise(h, w, s ^ 0x44, (9, 22, 50))
    micro = _noise(h, w, s ^ 0x55, (2, 4))
    edge = _edges_of(pattern, sr)
    return pattern.astype(np.float32), detail, micro, edge


_GS_TINTS = {
    "tessellate": np.float32([0.82, 0.88, 1.00]),
    "riverine":   np.float32([0.80, 1.00, 0.92]),
    "weave":      np.float32([1.00, 0.86, 0.92]),
    "magma":      np.float32([1.00, 0.88, 0.78]),
    "serpentine": np.float32([0.88, 0.82, 1.00]),
    "orbital":    np.float32([0.86, 0.95, 1.00]),
}


def _make_ghost_shift(mode, base_m, base_g, seed_off):
    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        pattern, detail, micro, edge = [
            cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR)
            for a in _gs_fields(_WORKG, _WORKG, _seed_int(seed) + seed_off, mode)]
        smf = float(sm)
        # THE GHOST FRACTURE CONTRACT (measured: M mean 225 p5 187 p95 255;
        # G 58-119; B carved 124<->240 by the pattern, +46 on edges)
        M = np.clip(base_m + detail * 56.0 * smf + edge * 72.0 * smf, 0, 255)
        G = np.clip(base_g + (1.0 - detail) * 54.0 - edge * 18.0, 0, 255)
        B = np.clip(212.0 - pattern * 148.0 + edge * 46.0 + micro * 18.0, 16, 255)
        out = np.zeros((fh, fw, 4), np.uint8)
        inv = 1.0 - np.clip(m2, 0, 1)
        out[:, :, 0] = np.clip(M * np.clip(m2, 0, 1) + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(G * np.clip(m2, 0, 1) + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(B * np.clip(m2, 0, 1) + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        # ghost doctrine (SPB-78): paint stays near-neutral — the SPEC carries
        # the shift; the owner's color + brightness crush does the rest. A 6%
        # pattern ghost keeps the geometry visible in the booth preview.
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        pattern, detail, micro, edge = [
            cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR)
            for a in _gs_fields(_WORKG, _WORKG, _seed_int(seed) + seed_off, mode)]
        strength = np.clip(m2 * float(pm), 0, 1)
        ghost = np.clip((pattern - 0.4) * 1.3, 0, 1) * 0.06 * strength
        tint = _GS_TINTS[mode]
        out = src * (1.0 - ghost[..., None]) + tint[None, None, :] * ghost[..., None]
        out = np.clip(out + edge[..., None] * 0.025 * strength[..., None]
                      - (1 - pattern)[..., None] * 0.02 * strength[..., None], 0, 1)
        return out.astype(np.float32)

    return spec_fn, paint_fn


GHOST_SHIFT_DEFS = {
    # id: (mode, base_m, base_g, seed_off) — base_m/base_g spread around the
    # proven fracture sweet spot (176/76)
    "ghost_shift_tessellate": ("tessellate", 176, 76, 11100),
    "ghost_shift_riverine":   ("riverine",   188, 64, 11110),
    "ghost_shift_weave":      ("weave",      170, 84, 11120),
    "ghost_shift_magma":      ("magma",      182, 70, 11130),
    "ghost_shift_serpentine": ("serpentine", 176, 60, 11140),
    "ghost_shift_orbital":    ("orbital",    192, 72, 11150),
}


def install_into_engine(mono_reg, base_reg=None):
    n = 0
    entries = {}
    for fid, (mode, bm, bg, so) in GHOST_SHIFT_DEFS.items():
        entries[fid] = _make_ghost_shift(mode, bm, bg, so)
        mono_reg[fid] = entries[fid]
        n += 1
    try:
        import engine.expansions.fusions as _fus
        _fus.FUSION_REGISTRY.update(entries)
    except Exception:
        pass
    return "ghost-shift: %d color-shift bases registered (Ghost Geometry lane)" % n
