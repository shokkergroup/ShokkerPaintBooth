"""SNAKESKIN SPEC-TEXTURE CANDIDATES (2026-10-04) -- OWNER LOOK REQUIRED, NOT WIRED.

Why: the copilot maps "snakeskin / reptile / snake scales" to the spec overlay
`snake_scale_diamond` (rescue_snake_scale_diamond -> _diamond_snake_scales), a
rotated-square rhombus lattice. FIRSTTEST + FIRSTTEST2 both saw it read as a
regular grid in the spec preview, not snakeskin. Report:
docs/handoff_reports/SNAKESKIN_CANDIDATES.md.

Three candidates, each new generative math (no recolour of an existing field).
All share ONE new primitive -- an IMBRICATE SCALE LATTICE: seeds on a sheared,
jittered lattice living in a smoothly WARPED + rotated coordinate frame (row
curvature, no period anywhere), each seed a rounded-lozenge scale with its own
size; scales are resolved per pixel either by ROOF-TILE PRIORITY (the scale in
front covers the base of the one behind -> overlapping scales with a cast shadow
under every free edge) or by nearest-shape (Voronoi-like tight mosaic).

  snakeskin_cand_python      imbricate rounded lozenges + per-scale python
                             saddle blotches (macro tiers quantised per scale)
  snakeskin_cand_viper       narrow lanceolate keeled scales (ridge down each
                             scale, one flank lit) + jittered diamondback chain
  snakeskin_cand_sunbeam     tiny smooth imbricate scales, every scale a different
                             phase of a cycling metal/roughness/clearcoat triple
                             (iridescent sheen through spec only)

They are SPEC overlays: paint is never touched (colour-preserving SHINE
texture). Contract = every legacy spec pattern: fn(shape, seed, sm, **kw) ->
float32 HxWx3 in [0, 1] = (metal, rough, clearcoat-gloss) deltas around 0.5.
Docstrings deliberately carry no channel "Targets" tags -> compose routes MRC.

Perf: the canvas is resolved in 64-row strips on a small thread pool (numpy
releases the GIL; strips stay cache-resident) and only the 6 lattice cells
that can own a pixel are tested (3 rows x the 2 nearest columns).

Not registered in PATTERN_CATALOG on purpose (owner picks first). Callable via
CANDIDATES below; the render/gate harness is _snakeskin_work/snake_harness.py.
"""
from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

try:
    import cv2 as _cv2
except Exception:  # pragma: no cover
    _cv2 = None

_STRIP = 64
_WORKERS = max(1, min(8, (os.cpu_count() or 2)))


# ------------------------------------------------------------------ helpers
def _smooth(h, w, rng, period):
    """Smooth zero-mean unit-variance noise field with ~`period` px features."""
    gh = max(3, int(math.ceil(h / float(period))) + 2)
    gw = max(3, int(math.ceil(w / float(period))) + 2)
    g = rng.standard_normal((gh, gw)).astype(np.float32)
    if _cv2 is not None:
        f = _cv2.resize(g, (w, h), interpolation=_cv2.INTER_CUBIC)
    else:  # pragma: no cover
        from scipy.ndimage import zoom
        f = zoom(g, (h / gh, w / gw), order=3)[:h, :w]
    f -= float(f.mean())
    f /= float(f.std()) + 1e-6
    return f.astype(np.float32, copy=False)


def _hash_tab(r, c, salt):
    """uint32 avalanche hash of integer lattice coords -> float32 [0,1)."""
    r = np.asarray(r).astype(np.int64).astype(np.uint32)
    c = np.asarray(c).astype(np.int64).astype(np.uint32)
    with np.errstate(over="ignore"):
        x = (r * np.uint32(0x8DA6B343)) ^ (c * np.uint32(0xD8163841)) ^ np.uint32((salt * 0x9E3779B1) & 0xFFFFFFFF)
        x ^= x >> np.uint32(15)
        x *= np.uint32(0x2C1B3C6D)
        x ^= x >> np.uint32(12)
        x *= np.uint32(0x297A2D39)
        x ^= x >> np.uint32(15)
    return (x >> np.uint32(8)).astype(np.float32) / np.float32(16777216.0)


def _sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _sc(shape):
    return max(min(shape) / 2048.0, 0.125)


def _run_strips(h, w, strip_fn, sm):
    """Run strip_fn(y0, y1) -> (M, R, C) over the canvas; assemble + sm-compress."""
    out = np.empty((h, w, 3), np.float32)
    s = 1.0 if sm is None else float(min(max(sm, 0.0), 1.0))

    def job(y0):
        y1 = min(h, y0 + _STRIP)
        for i, ch in enumerate(strip_fn(y0, y1)):
            np.clip(0.5 + (ch - 0.5) * s, 0.0, 1.0, out=out[y0:y1, :, i])

    starts = list(range(0, h, _STRIP))
    if len(starts) > 2 and _WORKERS > 1:
        with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
            list(ex.map(job, starts))
    else:
        for y0 in starts:
            job(y0)
    return out


# ---------------------------------------------------- the shared primitive
class _Lattice:
    """A warped, sheared, jittered scale lattice resolved strip by strip.

    px, py      lattice pitch across / along the body (px at 2048)
    a, b        scale half-width / half-length (px)   -- b > py/2 => overlap
    lozenge     0 = ellipse, 1 = diamond (L2 -> L1 blend)
    tip         extra pointedness on the free (posterior) half
    overlap     True  -> roof-tile priority (front row covers rear row)
                False -> nearest-shape mosaic (tight Voronoi-like tiling)
    """

    def __init__(self, h, w, seed, *, px, py, a, b, rot, warp_amp, warp_period,
                 jitter, size_jit, lozenge, tip, overlap):
        self.h, self.w, self.rot = h, w, rot
        self.px, self.py, self.overlap = float(px), float(py), overlap
        self.k_lo, self.k_tip = np.float32(lozenge), np.float32(tip)
        rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
        self.rng = rng
        yy = np.arange(h, dtype=np.float32)[:, None]
        xx = np.arange(w, dtype=np.float32)[None, :]
        cr, sr = math.cos(rot), math.sin(rot)
        self.cr, self.sr = cr, sr
        # Row curvature: two octaves of smooth warp. No period anywhere.
        self.X = ((xx * cr - yy * sr) + warp_amp * _smooth(h, w, rng, warp_period)
                  + (0.35 * warp_amp) * _smooth(h, w, rng, warp_period * 0.41)).astype(np.float32)
        self.Y = ((xx * sr + yy * cr) + warp_amp * _smooth(h, w, rng, warp_period * 1.17)
                  + (0.35 * warp_amp) * _smooth(h, w, rng, warp_period * 0.47)).astype(np.float32)
        r_lo = int(math.floor(float(self.Y.min()) / py)) - 3
        r_hi = int(math.floor(float(self.Y.max()) / py)) + 3
        c_lo = int(math.floor(float(self.X.min()) / px)) - 3
        c_hi = int(math.floor(float(self.X.max()) / px)) + 3
        rows = np.arange(r_lo, r_hi + 1)
        cols = np.arange(c_lo, c_hi + 1)
        self.r_lo, self.c_lo, self.nR, self.nC = r_lo, c_lo, rows.size, cols.size
        salt = int(seed) * 7919 + 17
        self.rowoff = (0.5 * (rows & 1) + 0.16 * (_hash_tab(rows, rows * 0 + 3, salt) - 0.5)).astype(np.float32)
        RR, CC = np.meshgrid(rows, cols, indexing="ij")
        h1 = _hash_tab(RR, CC, salt + 1)
        h2 = _hash_tab(RR, CC, salt + 2)
        h3 = _hash_tab(RR, CC, salt + 3)
        msz = (1.0 + size_jit * 2.0 * (h3 - 0.5)).astype(np.float32)
        self.tcx = ((CC + 0.5 + self.rowoff[:, None] + jitter * (h1 - 0.5)) * px).astype(np.float32).ravel()
        self.tcy = ((RR + 0.5 + 0.55 * jitter * (h2 - 0.5)) * py).astype(np.float32).ravel()
        self.tia = (1.0 / (a * msz)).astype(np.float32).ravel()
        self.tib = (1.0 / (b * msz)).astype(np.float32).ravel()
        self.th4 = _hash_tab(RR, CC, salt + 4).ravel()
        self.th5 = _hash_tab(RR, CC, salt + 5).ravel()

    def resolve(self, y0, y1):
        X = self.X[y0:y1]
        Y = self.Y[y0:y1]
        shp = X.shape
        big = np.float32(1e9)
        ipx = np.float32(1.0 / self.px)
        r0 = np.floor(Y * np.float32(1.0 / self.py)).astype(np.int32)
        best_s = np.full(shp, big, np.float32)
        second_s = np.full(shp, big, np.float32)
        best_i = np.zeros(shp, np.int32)
        best_du = np.zeros(shp, np.float32)
        best_dv = np.zeros(shp, np.float32)
        near_hi = np.full(shp, big, np.float32)
        shadow_src = np.full(shp, big, np.float32)
        assigned = np.zeros(shp, bool)
        for dr in (-1, 0, 1):
            ri = np.clip(r0 + dr - self.r_lo, 0, self.nR - 1)
            u = X * ipx - np.take(self.rowoff, ri)
            c0 = np.floor(u).astype(np.int32)
            c1 = c0 + np.where((u - c0) < 0.5, -1, 1).astype(np.int32)
            base = ri * self.nC - self.c_lo
            if self.overlap:
                row_s = np.full(shp, big, np.float32)
                row_i = np.zeros(shp, np.int32)
                row_du = np.zeros(shp, np.float32)
                row_dv = np.zeros(shp, np.float32)
                tgt = (row_s, row_i, row_du, row_dv)
            for cc in (c0, c1):
                idx = base + np.clip(cc, self.c_lo, self.c_lo + self.nC - 1)
                du = (X - np.take(self.tcx, idx)) * np.take(self.tia, idx)
                dv = (Y - np.take(self.tcy, idx)) * np.take(self.tib, idx)
                l2 = np.sqrt(du * du + dv * dv)
                k = self.k_lo + self.k_tip * (dv > 0)
                s = l2 + k * (np.abs(du) + np.abs(dv) - l2)
                if self.overlap:
                    m = s < row_s
                    np.copyto(row_s, s, where=m)
                    np.copyto(row_i, idx, where=m)
                    np.copyto(row_du, du, where=m)
                    np.copyto(row_dv, dv, where=m)
                else:
                    m = s < best_s
                    np.copyto(second_s, np.where(m, best_s, np.minimum(second_s, s)))
                    np.copyto(best_s, s, where=m)
                    np.copyto(best_i, idx, where=m)
                    np.copyto(best_du, du, where=m)
                    np.copyto(best_dv, dv, where=m)
            if self.overlap:
                take = (~assigned) & (row_s < 1.0)
                np.copyto(best_s, row_s, where=take)
                np.copyto(best_i, row_i, where=take)
                np.copyto(best_du, row_du, where=take)
                np.copyto(best_dv, row_dv, where=take)
                np.copyto(shadow_src, near_hi, where=take)
                assigned |= take
                np.minimum(near_hi, row_s, out=near_hi)
        if self.overlap:
            gap = ~assigned
            seam = np.zeros(shp, np.float32)
            shadow = np.clip(1.0 - (shadow_src - 1.0) / np.float32(0.42), 0.0, 1.0)
            shadow[gap] = 0.0
            best_s[gap] = 1.0
            s = best_s
        else:
            gap = np.zeros(shp, bool)
            rel = (second_s - best_s) / (second_s + np.float32(1e-3))
            seam = (1.0 - _sstep(0.035, 0.11, rel)).astype(np.float32)
            shadow = np.zeros(shp, np.float32)
            s = np.minimum(best_s, 1.0)
        cx = np.take(self.tcx, best_i)
        cy = np.take(self.tcy, best_i)
        # seed position back in canvas pixels (warp is smooth: +-1-2 px)
        dX = X - cx
        dY = Y - cy
        yy = np.arange(y0, y1, dtype=np.float32)[:, None]
        xx = np.arange(self.w, dtype=np.float32)[None, :]
        sy = np.clip(np.rint(yy + dX * self.sr - dY * self.cr), 0, self.h - 1).astype(np.int32)
        sx = np.clip(np.rint(xx - dX * self.cr - dY * self.sr), 0, self.w - 1).astype(np.int32)
        return {
            "s": s, "du": best_du, "dv": best_dv, "shadow": shadow, "gap": gap, "seam": seam,
            "cx": cx, "cy": cy, "sy": sy, "sx": sx,
            "h4": np.take(self.th4, best_i), "h5": np.take(self.th5, best_i),
        }


# ------------------------------------------------------------- candidate A
def snakeskin_cand_python(shape, seed, sm, **kwargs):
    """PYTHON IMBRICATE -- candidate A (2026-10-04, owner look pending).

    Rounded-lozenge scales ~17x14 px laid like roof tiles on curved rows; each
    free edge casts a soft shadow on the scale behind it. Macro python SADDLES
    (~130 px organic blotches with a one-scale light halo, light flecks
    inside) are quantised per scale. Saddle scales = deep metal mirror, halo
    scales = bare clear gloss over the paint, ground = satin. Every scale:
    glossy crown, rough dull rim, faint growth lines.
    """
    h, w = int(shape[0]), int(shape[1])
    k = _sc(shape)
    px, py = 17.0 * k, 10.5 * k
    L = _Lattice(h, w, seed + 4101, px=px, py=py, a=0.62 * px, b=1.12 * py,
                 rot=0.38, warp_amp=30.0 * k, warp_period=420.0 * k,
                 jitter=0.24, size_jit=0.13, lozenge=0.42, tip=0.10, overlap=True)
    F = 0.85 * _smooth(h, w, L.rng, 170.0 * k) + 0.30 * _smooth(h, w, L.rng, 70.0 * k)

    def strip(y0, y1):
        d = L.resolve(y0, y1)
        f = F[d["sy"], d["sx"]]
        saddle = (f > 0.55).astype(np.float32)
        halo = ((f > 0.30) & (f <= 0.55)).astype(np.float32)
        spot = (d["h5"] < 0.07).astype(np.float32) * saddle
        saddle -= spot
        halo += spot
        ground = 1.0 - saddle - halo
        tj = (d["h4"] - 0.5) * 0.12
        # saddle = dark metal mirror, halo = bare bright colour under clear, ground = satin metal
        M = ground * 0.52 + saddle * 0.92 + halo * 0.04 + tj
        R = ground * 0.60 + saddle * 0.24 + halo * 0.40 - tj * 0.5
        C = ground * 0.44 + saddle * 0.56 + halo * 0.80 + tj * 0.5
        s, dv, sh = d["s"], d["dv"], d["shadow"]
        hump = np.clip(1.0 - s, 0.0, 1.0) ** 0.7
        edge = _sstep(0.70, 1.0, s)
        crest = np.clip(0.5 + 0.5 * dv, 0.0, 1.0) * hump      # light catches the free half
        growth = 0.035 * np.cos(dv * 9.0)                      # fine growth lines across each scale
        M = M + 0.10 * crest - 0.30 * sh
        R = R - 0.20 * hump + 0.40 * edge + 0.30 * sh + growth
        C = C + 0.14 * crest - 0.50 * edge - 0.45 * sh - growth
        g = d["gap"]
        M[g], R[g], C[g] = 0.14, 0.95, 0.04
        return M, R, C

    return _run_strips(h, w, strip, sm)


# ------------------------------------------------------------- candidate B
def snakeskin_cand_viper(shape, seed, sm, **kwargs):
    """DIAMONDBACK KEEL -- candidate B (2026-10-04, owner look pending).

    Narrow lanceolate scales ~13x28 px with a pointed free tip and a raised
    KEEL down each one (bright gloss ridge, one flank lit, one flank satin),
    overlapping on curved, half-offset rows. Macro: a jittered diamondback
    chain (~150x190 px diamonds, own size/centre/aspect per diamond, some
    missing, edges noise-broken) quantised per scale: dark metal body, a
    one-scale bright clear border, a lighter centre, satin ground with darker
    speckle scales.
    """
    h, w = int(shape[0]), int(shape[1])
    k = _sc(shape)
    px, py = 12.5 * k, 10.5 * k
    a, b = 0.60 * px, 1.36 * py
    L = _Lattice(h, w, seed + 5203, px=px, py=py, a=a, b=b,
                 rot=-0.52, warp_amp=34.0 * k, warp_period=470.0 * k,
                 jitter=0.20, size_jit=0.12, lozenge=0.55, tip=0.38, overlap=True)
    Dx, Dy = 150.0 * k, 190.0 * k
    WN = _smooth(h, w, L.rng, 70.0 * k)
    salt = int(seed) * 31 + 9

    def strip(y0, y1):
        d = L.resolve(y0, y1)
        cx, cy = d["cx"], d["cy"]
        dyi = np.floor(cy / Dy).astype(np.int32)
        off = 0.5 * (dyi & 1)
        dxi = np.floor(cx / Dx - off).astype(np.int32)
        jx = _hash_tab(dyi, dxi, salt) - 0.5
        jy = _hash_tab(dyi, dxi, salt + 1) - 0.5
        sz = 0.72 + 0.30 * _hash_tab(dyi, dxi, salt + 2)
        asp = 0.85 + 0.30 * _hash_tab(dyi, dxi, salt + 4)
        keep = _hash_tab(dyi, dxi, salt + 3) > 0.15
        dcx = (dxi + 0.5 + off + 0.24 * jx) * Dx
        dcy = (dyi + 0.5 + 0.24 * jy) * Dy
        dd = (np.abs(cx - dcx) / (0.5 * Dx * sz * asp) + np.abs(cy - dcy) / (0.5 * Dy * sz / asp)) \
            + 0.16 * WN[d["sy"], d["sx"]]
        dd = np.where(keep, dd, 9.0)
        core = (dd < 0.24).astype(np.float32)
        dark = ((dd >= 0.24) & (dd < 0.66)).astype(np.float32)
        border = ((dd >= 0.66) & (dd < 0.86)).astype(np.float32)
        ground = 1.0 - core - dark - border
        speck = (d["h5"] < 0.10).astype(np.float32) * ground
        ground -= speck
        tj = (d["h4"] - 0.5) * 0.10
        M = ground * 0.42 + speck * 0.70 + dark * 0.82 + border * 0.14 + core * 0.55 + tj
        R = ground * 0.60 + speck * 0.42 + dark * 0.34 + border * 0.20 + core * 0.30 - tj * 0.5
        C = ground * 0.40 + speck * 0.52 + dark * 0.58 + border * 0.94 + core * 0.74 + tj * 0.5
        s, du, dv, sh = d["s"], d["du"], d["dv"], d["shadow"]
        hump = np.clip(1.0 - s, 0.0, 1.0) ** 0.6
        edge = _sstep(0.68, 1.0, s)
        keel = np.exp(-(du / 0.17) ** 2) * np.clip(dv + 0.75, 0.0, 1.0) * hump
        flank = np.clip(du, -1.0, 1.0) * hump                  # one side of the ridge lit
        M = M + 0.20 * keel - 0.32 * sh
        R = R - 0.34 * keel + 0.14 * flank + 0.40 * edge + 0.30 * sh - 0.08 * hump
        C = C + 0.32 * keel - 0.12 * flank - 0.50 * edge - 0.45 * sh
        g = d["gap"]
        M[g], R[g], C[g] = 0.12, 0.96, 0.04
        return M, R, C

    return _run_strips(h, w, strip, sm)


# ------------------------------------------------------------- candidate C
def snakeskin_cand_sunbeam(shape, seed, sm, **kwargs):
    """SUNBEAM IRIDESCENT -- candidate C (2026-10-04, owner look pending).

    Tiny smooth overlapping scales ~13x15 px on curved half-offset rows (thin
    rough rim, a faint shadow under each free edge -- a polished skin). Each
    scale carries ONE phase of a cycling (metal, roughness, clearcoat) triple
    with 120-degree offsets, so neighbouring scales are different materials;
    the phase follows long sweeping sheen waves plus per-scale jitter and
    slides slightly across each scale, so the sheen rolls as the car turns.
    Iridescence through spec only -- the paint colour is untouched.
    """
    h, w = int(shape[0]), int(shape[1])
    k = _sc(shape)
    px, py = 10.5 * k, 6.4 * k
    L = _Lattice(h, w, seed + 6301, px=px, py=py, a=0.62 * px, b=1.18 * py,
                 rot=0.95, warp_amp=26.0 * k, warp_period=360.0 * k,
                 jitter=0.22, size_jit=0.15, lozenge=0.30, tip=0.12, overlap=True)
    wave = 0.9 * _smooth(h, w, L.rng, 300.0 * k) + 0.35 * _smooth(h, w, L.rng, 110.0 * k)
    inv = np.float32(1.0 / (260.0 * k))

    def strip(y0, y1):
        d = L.resolve(y0, y1)
        f = wave[d["sy"], d["sx"]]
        band = (d["cx"] * 0.6 + d["cy"] * 0.8) * inv
        phi = 2.0 * np.pi * (band + 0.55 * f + 0.22 * d["h4"]) + 0.9 * d["du"]
        M = 0.50 + 0.36 * np.cos(phi)
        R = 0.34 + 0.20 * np.cos(phi + 2.094)
        C = 0.64 + 0.32 * np.cos(phi + 4.189)
        s, sh = d["s"], d["shadow"]
        hump = np.clip(1.0 - s, 0.0, 1.0) ** 0.5
        edge = _sstep(0.78, 1.0, s)
        M = M * (1.0 - 0.6 * edge) + 0.06 * hump - 0.18 * sh
        R = R - 0.16 * hump + 0.55 * edge + 0.18 * sh
        C = C + 0.10 * hump - 0.62 * edge - 0.25 * sh
        g = d["gap"]
        M[g], R[g], C[g] = 0.20, 0.90, 0.06
        return M, R, C

    return _run_strips(h, w, strip, sm)


CANDIDATES = {
    "snakeskin_cand_python": snakeskin_cand_python,
    "snakeskin_cand_viper": snakeskin_cand_viper,
    "snakeskin_cand_sunbeam": snakeskin_cand_sunbeam,
}
