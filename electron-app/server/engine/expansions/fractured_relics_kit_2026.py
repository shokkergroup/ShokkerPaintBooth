# -*- coding: utf-8 -*-
"""FRACTURED RELICS KIT (2026-08-30) — shared machinery for the rebuilt
FRACTURED RELICS category (owner mandate 2026-08-30: 100 -> 50, one occult /
cryptozoology identity, every finish unique, "the most advanced spec map
properties you can possibly build ... the spec maps should follow the pattern
designs ... millions of details").

Two things live here so the category module stays pure recipes:

1. THE IN-BAND PRIMITIVE SET — carried over verbatim in behaviour from
   engine/expansions/fractured_relic_2026.py [SPB-FRACTURED-090b 2026-08-02],
   whose authors solved the hard problem: on a 2048 car the visible band is
   8-32px, which at GEN 640 is a 6-10px window (r 64..256 of the 512 paint),
   and an anti-static guard (lag-1 autocorrelation >= 0.55) caps the top end.
   Every feature therefore has to be a BOUNDED-JITTER DOMED LATTICE, and every
   generator ends with `_lowcut` (subtract the field's own slow local mean).
   Re-deriving that would be a waste; it is copied here so the new category
   owns its primitives outright and the old module can be retired.

2. RelicKit — CategoryKit + two upgrades:
   * structure-following hue anchors (colour changes feature to feature, not
     on a hash checkerboard slicing through the geometry);
   * THE MATERIAL-STATE SPEC CARVE (new 2026-08-30): the finish's own
     generator is re-run cheaply and quantised into four material zones that
     follow the artifact's anatomy - void / matrix / polished relief / metal
     inlay - each owning a discrete (M,R,Cc) centre, blended over the
     FRACTURED ghost-shift base so family DNA survives, then plied with
     tool-mark shoulders, structural tooth, patina grain, gated pit lattices,
     metal fleck and a burial gradient. Spec follows the paint's own geometry
     by construction, and carries five independent detail bands.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from engine.expansions import fractured_catlib_2026 as catlib
from engine.expansions.fractured_catlib_2026 import (  # noqa: F401
    coords, fbm, frac, gauss, h2, n01, rng, rot, sstep, warp_pair,
)

_TAU = 6.283185307179586
_S = 768.0            # generator px-space anchor (pitch scales as res/_S)
_P0 = 10.4            # canonical lattice pitch: 8.7px @GEN640 == 28px on car
_LC = 1.9             # low-cut sigma in _S units -> high-pass knee at r=64
_TIERS = np.array([0.16, 0.27, 0.38, 0.49, 0.60, 0.70, 0.81, 0.93], np.float32)


# ════════════════════════════════════════════════════════════════════════════
# IN-BAND PRIMITIVES
# ════════════════════════════════════════════════════════════════════════════

def _tier(hv):
    """8-tier brightness ladder (owner law: many shades, never 2 levels)."""
    return _TIERS[np.clip((np.asarray(hv, np.float32) * 8.0).astype(np.int32), 0, 7)]


def _sd(seed):
    return int(seed) % 7919


def _bump(t2):
    return np.clip(1.0 - np.asarray(t2, np.float32) * 0.45, 0.0, 1.0) ** 2


def _flat(x, s=1.6):
    """Low-cut a field: subtract its own local mean, keep the global mean."""
    x = np.asarray(x, np.float32)
    return x - gauss(x, float(s)) + float(x.mean())


def _fat(d, w, soft=0.34):
    """Fat smooth seam from a 0..1 edge-distance field (0 = seam centre)."""
    w = np.asarray(w, np.float32)
    t = np.clip((d - w) / np.minimum(w * (float(soft) - 1.0), -1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _grain(xx, yy, cell, salt, thr=0.62):
    """Per-cell speckle, DOMED and floored inside the car band."""
    res = int(np.asarray(xx).shape[0])
    c = max(float(cell), 4.0 * res / 640.0)
    du = frac(xx / c) - 0.5
    dv = frac(yy / c) - 0.5
    dome = np.clip(1.0 - 3.6 * (du * du + dv * dv), 0.0, 1.0)
    g = h2(np.floor(xx / c), np.floor(yy / c), salt)
    return sstep(thr, min(thr + 0.18, 0.999), g) * dome


def _fine(res, seed, k=0.13):
    """Closing micro-relief: two dome lattices (r=84 / r=123), random per-cell
    amplitude. A shape field of thousands of 8-14px domes, never pixel noise."""
    s = res / 640.0
    sd = _sd(seed)
    yy, xx = coords(res)
    acc = np.zeros((res, res), np.float32)
    for c, w, salt in ((7.6, 0.62, 811), (5.2, 0.38, 823)):
        cc = c * s
        du = frac(xx / cc) - 0.5
        dv = frac(yy / cc) - 0.5
        dome = np.clip(1.0 - 3.4 * (du * du + dv * dv), 0.0, 1.0)
        g = h2(np.floor(xx / cc), np.floor(yy / cc), sd + salt)
        acc += (g - 0.5) * dome * w
    return (acc * (1.15 * float(k))).astype(np.float32)


def _ptier(res, cell, salt, ang=0.0, relief=0.55, jit=0.30):
    """8-tier tint on an in-band domed patch lattice (tint arrives WITH relief)."""
    yy, xx = coords(res)
    if ang:
        ca, sa = np.cos(float(ang)), np.sin(float(ang))
        u, v = xx * ca + yy * sa, -xx * sa + yy * ca
    else:
        u, v = xx, yy
    c = float(cell)
    ci, cj = np.floor(u / c), np.floor(v / c)
    jx = (h2(ci, cj, salt + 3) - 0.5) * float(jit)
    jy = (h2(ci, cj, salt + 7) - 0.5) * float(jit)
    d = np.maximum(np.abs(frac(u / c) - 0.5 + jx),
                   np.abs(frac(v / c) - 0.5 + jy)) * 2.0
    return _tier(h2(ci, cj, salt)) * (1.0 - relief + relief * sstep(1.02, 0.24, d))


def _cells(res, pitch, salt, jit=0.85, taps=9, need2=True):
    """Jittered-grid nearest-feature field -> (dx, dy, d1, id1, d2). The kernel
    that stamps THOUSANDS of 8-32px features vectorized."""
    g = float(pitch)
    yy, xx = coords(res)
    cu = np.floor(xx / g)
    cv_ = np.floor(yy / g)
    n = int(np.ceil(res / g)) + 4
    ii = np.arange(-1, n, dtype=np.float32)
    CU, CV = np.meshgrid(ii, ii)
    JX = h2(CU, CV, salt)
    JY = h2(CU, CV, salt + 57)
    JB = h2(CU, CV, salt + 91)
    iu = cu.astype(np.int32) + 1
    iv = cv_.astype(np.int32) + 1
    best = np.full((res, res), 1e9, np.float32)
    second = np.full((res, res), 1e9, np.float32) if need2 else None
    bdx = np.zeros((res, res), np.float32)
    bdy = np.zeros((res, res), np.float32)
    bid = np.zeros((res, res), np.float32)
    offs = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1))[:int(taps)]
    for di, dj in offs:
        ix = np.clip(iu + di, 0, n)
        iy = np.clip(iv + dj, 0, n)
        jx = JX[iy, ix]
        jy = JY[iy, ix]
        fx = (cu + (di + 0.5) + (jx - 0.5) * jit) * g
        fy = (cv_ + (dj + 0.5) + (jy - 0.5) * jit) * g
        ddx = xx - fx
        ddy = yy - fy
        d = ddx * ddx + ddy * ddy
        m = d < best
        if need2:
            second = np.where(m, best, np.minimum(second, d))
        best = np.where(m, d, best)
        bdx = np.where(m, ddx, bdx)
        bdy = np.where(m, ddy, bdy)
        bid = np.where(m, JB[iy, ix], bid)
    return (bdx, bdy, np.sqrt(best), bid,
            np.sqrt(second) if need2 else None)


def _pave(res, p, salt, jit=0.45, seam=0.22, taps=9):
    """Bounded-jitter cell pave carrying in-cell relief + a fat edge seam ->
    (dx, dy, d1, id1, edge, crown, seam_mask)."""
    dx, dy, d1, id1, d2 = _cells(res, p, salt, jit, taps=taps, need2=True)
    edge = (d2 - d1) / p
    return dx, dy, d1, id1, edge, sstep(0.02, 0.40, edge), _fat(edge, float(seam))


def _age(res, seed, chip=0.20, tooth=0.12):
    """Antiquity ply (MANDATORY on every relic): small dark losses + tooth."""
    s = res / _S
    sd = _sd(seed)
    _, _, cd, cid, _ = _cells(res, 8.6 * s, sd + 303, 0.5, taps=5, need2=False)
    chips = _bump((cd / (2.0 * s)) ** 2) * sstep(0.55, 0.85,
                                                 h2(np.floor(cid * 37.0), 0.0, sd + 7))
    grit = _fine(res, seed + 313, 1.0)
    return (-chips * float(chip) + grit * float(tooth)).astype(np.float32)


def _fibers(res, seed, ang, pitch, wob=2.4, salt=0, duty=0.55):
    """Directional fiber/thread bundle field (hair, hemp, horn tubule, linen).
    Bounded wobble keeps the stripe fundamental sharp and in band."""
    s = res / _S
    yy, xx = coords(res)
    ca, sa = np.cos(float(ang)), np.sin(float(ang))
    u = xx * ca + yy * sa
    v = -xx * sa + yy * ca
    w1 = (fbm(res, res, rng(seed, 41 + salt), 3, 5) - 0.5) * float(wob) * s * 4.0
    p = float(pitch) * s
    q = (u + w1) / p
    ci = np.floor(q)
    f = frac(q) - 0.5
    amp = 0.55 + 0.45 * h2(ci, np.floor(v / (p * 9.0)), _sd(seed) + 77 + salt)
    core = np.clip(1.0 - (np.abs(f) / (0.5 * float(duty))) ** 2, 0.0, 1.0)
    return (core * amp).astype(np.float32)


def _lut_steep(lut, span=0.5):
    """T position of the steepest monotone stretch of a thin-film LUT's luma."""
    t = catlib.thinfilm_lut(*lut)
    L = t[:, 0] * 0.299 + t[:, 1] * 0.587 + t[:, 2] * 0.114
    g = np.abs(np.diff(L.astype(np.float64)))
    w = max(4, int(float(span) * len(L)))
    k = np.convolve(g, np.ones(w) / w, mode="valid")
    return float(int(np.argmax(k)) + w // 2) / float(len(L) - 1)


def lowcut(fn):
    """Universal LOW-CUT + LUT-SPAN wrapper around every generator.
    `lowcut` px at GEN deletes power under r=64 without touching a shape;
    `span`/`mid` compress the LUT traversal so the film stack does not
    multiply the generator's frequencies out of the coherent end of the band."""
    def wrapped(res, seed, *a, lowcut=_LC, span=None, mid=0.5, pct=1.2,
                contrast=1.0, **kw):
        T = np.asarray(fn(res, seed, *a, **kw), np.float32)
        if lowcut:
            T = _flat(T, float(lowcut) * res / _S)
        # ROBUST normalisation [relics 2026-08-30 iter9]. Plain n01 lets a
        # handful of outliers — a bored hole, a struck rim — set the range and
        # squeeze the whole body of the field into a narrow slice of the LUT,
        # which is where five of the first ten cards lost their luma
        # micro-contrast (fineness 5.6-9.3 against a family bar of 10.5-24.2).
        # Percentile clipping spends the LUT on the material, not the extremes.
        if pct:
            lo, hi = np.percentile(T, (float(pct), 100.0 - float(pct)))
            T = np.clip((T - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
        else:
            T = n01(T)
        if contrast and contrast != 1.0:
            # S-curve about the midpoint: strokes brighten, ground darkens, so
            # the incised FIGURE reads instead of averaging to flat grey.
            T = np.clip(0.5 + (T - 0.5) * float(contrast), 0.0, 1.0)
            T = T * T * (3.0 - 2.0 * T) * 0.5 + T * 0.5
        if span:
            T = float(mid) + (T - 0.5) * float(span)
        return np.clip(T, 0.0, 1.0).astype(np.float32)
    wrapped.__name__ = getattr(fn, "__name__", "gen")
    wrapped.__doc__ = fn.__doc__
    return wrapped


# ════════════════════════════════════════════════════════════════════════════
# THE RELIC KIT — structure-following hue + material-state spec
# ════════════════════════════════════════════════════════════════════════════

# Four material centres (M, R, Cc), lowest structure -> highest:
#   0 void/incision  : cut away, never touched, dead matte, dull clearcoat
#   1 matrix/body    : the aged substrate — stone, leather, wax, bone
#   2 polished relief: what hands and cloth have rubbed for centuries
#   3 inlay/metal    : the precious lane — gilt wire, silver, mirror-black glass
MATS_DEFAULT = ((26.0, 214.0, 238.0),
                (96.0, 152.0, 186.0),
                (204.0, 62.0, 74.0),
                (248.0, 20.0, 26.0))


class RelicKit(catlib.CategoryKit):
    """CategoryKit + structure-following hue anchors + material-state spec."""

    def __init__(self, engines, groups, tag, **kw):
        super().__init__(engines, groups, tag, **kw)
        self.struct_cached = lru_cache(maxsize=6)(self._struct)

    # ---- structural probe: the finish's OWN generator, cheaply ------------
    def _struct(self, fid, res):
        d = self.ALL[fid]
        eargs = dict(d.get("eargs", {}))
        T = self.engines[d["engine"]](int(res), int(d["seed"]), **eargs)
        return n01(np.asarray(T, np.float32))

    # ---- THE SURFACE PLY: micro-relief at WORK res, following the structure
    def art_work(self, fid):
        """Family art + a RELICS-only closing ply.

        [relics 2026-08-30 iter14] Structural generators run at GEN 640 and are
        cubic-upscaled to 2048, so the finest detail a generator can express on
        the car is ~3.2px and the upscale low-passes even that — which is why
        the soft-field cards sat at fineness 6-9 against a family bar of
        10.5-24.2. The fix is not more amplitude in the generator (that only
        coarsens the figure): it is a THIRD scale, applied after the upscale, at
        WORK 1152 where 2048 is only 1.78x away. Three dome lattices at 4.6 /
        3.1 / 2.2px, amplitude keyed to the structure itself so the tooth sits
        on the raised material and the incised voids stay smooth — the way real
        tooling, casting grain and burial etch actually distribute. This is the
        'millions of details' ply, and it is a shape field, never pixel noise."""
        rgb = super().art_work(fid)
        d = self.ALL[fid]
        k = float(d.get("micro", 1.0))
        if k <= 0.0:
            return rgb
        W = self.WORK
        S = cv2.resize(self.struct_cached(fid, 448), (W, W), interpolation=cv2.INTER_CUBIC)
        sd = _sd(int(d["seed"]))
        yy, xx = coords(W)
        acc = np.zeros((W, W), np.float32)
        for c, w, salt in ((4.6, 0.55, 733), (3.1, 0.34, 751), (2.15, 0.22, 769)):
            du, dv = frac(xx / c) - 0.5, frac(yy / c) - 0.5
            dome = np.clip(1.0 - 3.4 * (du * du + dv * dv), 0.0, 1.0)
            acc += (h2(np.floor(xx / c), np.floor(yy / c), sd + salt) - 0.5) * dome * w
        tooth = acc * (0.42 + 0.95 * np.clip(S, 0.0, 1.0))
        out = rgb * (1.0 + (tooth * (0.62 * k))[..., None])
        # THE BURNISH PASS — a structure-keyed unsharp at WORK. Relic tooling is
        # CRISP: chisel walls, cast rims and fracture lips have hard shoulders,
        # and the GEN->WORK->2048 upscale chain softens exactly those. This
        # amplifies detail that already exists (never adds grain) and is what
        # moves relative micro-contrast (fine/meanL) into the approved family
        # window of 0.16-0.28. Amplitude per recipe via `burnish`.
        b = float(d.get("burnish", 0.55))
        if b > 0.0:
            out = np.clip(out + (out - cv2.GaussianBlur(out, (0, 0), 1.35)) * b, 0.0, 1.0)
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    # ---- hue anchors follow the geometry, not a hash checkerboard ---------
    def macro_maps(self, d):
        Mval, Ddom = super().macro_maps(d)
        g = float(d.get("hue_cell", 0.0))
        if g <= 0.0:
            return Mval, Ddom
        r = 192
        sd = _sd(int(d["seed"]))
        T = np.asarray(self.engines[d["engine"]](r, int(d["seed"]),
                                                 **d.get("eargs", {})), np.float32)
        T = n01(gauss(n01(T), float(d.get("hue_blur", 2.2))))
        T = cv2.resize(T, (self.GEN, self.GEN), interpolation=cv2.INTER_LINEAR)
        yy, xx = coords(self.GEN)
        jit = h2(np.floor(xx / g), np.floor(yy / g), sd + 421)
        drift = gauss(Ddom, self.GEN / 48.0)
        D = frac(T * float(d.get("hue_levels", 1.4))
                 + jit * float(d.get("hue_jit", 0.14))
                 + drift * float(d.get("hue_drift", 0.5)))
        return Mval, np.clip(D, 0.0, 1.0).astype(np.float32)

    # ---- THE MATERIAL-STATE SPEC CARVE -----------------------------------
    def mk(self, fid):
        """(spec_fn, paint_fn). paint_fn is the family contract; spec_fn is the
        ghost-shift base with the RELICS material-state carve laid over it."""
        spec_base, paint_fn = super().mk(fid)
        WORK = self.WORK
        d = self.ALL[fid]
        rkw = dict(d.get("kw", {}))
        mats = np.asarray(d.get("mats", MATS_DEFAULT), np.float32)
        matmix = float(d.get("matmix", 0.58))
        cuts = tuple(d.get("mat_cuts", (0.34, 0.62, 0.86)))
        pit_k = float(d.get("pit", 1.0))
        seed = int(d["seed"])

        @lru_cache(maxsize=2)
        def _plates():
            """Material map + detail plies at WORK, cached (never per render)."""
            S = self.struct_cached(fid, 448)
            S = cv2.resize(S, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
            S = np.clip(S, 0.0, 1.0)
            Ssm = gauss(S, 1.7)
            q = np.quantile(Ssm, np.asarray(cuts, np.float32))
            mat = np.digitize(Ssm, q).astype(np.int32)          # 0..3, balanced
            gx = cv2.Sobel(gauss(S, 1.1), cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gauss(S, 1.1), cv2.CV_32F, 0, 1, ksize=3)
            shoulder = sstep(0.30, 0.88, n01(np.hypot(gx, gy)))  # worn tool marks
            tooth = S - gauss(S, 1.4)                            # structural tooth
            # gated pit lattice: crust and matrix pit, polished metal does not
            yy, xx = coords(WORK)
            c = 6.4 * WORK / 640.0
            du, dv = frac(xx / c) - 0.5, frac(yy / c) - 0.5
            dome = np.clip(1.0 - 3.4 * (du * du + dv * dv), 0.0, 1.0)
            pit = sstep(0.58, 0.92, h2(np.floor(xx / c), np.floor(yy / c),
                                       _sd(seed) + 907)) * dome
            # sparse metal fleck, inlay lane only
            c2 = 4.2 * WORK / 640.0
            fleck = sstep(0.86, 0.99, h2(np.floor(xx / c2), np.floor(yy / c2),
                                         _sd(seed) + 613))
            burial = n01(gauss(fbm(WORK // 6, WORK // 6, rng(seed, 951), 3, 3), 2.0))
            burial = cv2.resize(burial, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
            return (mat, shoulder.astype(np.float32), tooth.astype(np.float32),
                    pit.astype(np.float32), fleck.astype(np.float32),
                    burial.astype(np.float32), S.astype(np.float32))

        def spec_fn(shape, mask, seed_, sm):
            fh, fw = int(shape[0]), int(shape[1])
            base = spec_base((WORK, WORK), np.ones((WORK, WORK), np.float32), seed_, sm)
            mat, shoulder, tooth, pit, fleck, burial, Ssharp = _plates()
            M = base[:, :, 0].astype(np.float32)
            R = base[:, :, 1].astype(np.float32)
            C = base[:, :, 2].astype(np.float32)
            # 1. MATERIAL PLATES — discrete states that follow the artifact
            tM, tR, tC = mats[mat, 0], mats[mat, 1], mats[mat, 2]
            M = M * (1.0 - matmix) + tM * matmix
            R = R * (1.0 - matmix) + tR * matmix
            C = C * (1.0 - matmix) + tC * matmix
            # 1b. CONTINUOUS STRUCTURE TERM — the quantised plates are steps, so
            # on finishes whose structure histogram is skewed most pixels land in
            # one zone and the independent plies (pits, burial) start to dominate
            # the map. This rides the structure itself, guaranteeing the spec
            # tracks the paint's geometry everywhere, not just at the plate steps.
            sg = float(d.get("struct_gain", 1.0))
            sc_ = (np.clip(Ssharp, 0.0, 1.0) - 0.5) * 2.0
            M += 46.0 * sc_ * sg
            R -= 40.0 * sc_ * sg
            C -= 30.0 * sc_ * sg
            # 2. TOOL-MARK SHOULDERS — every carved edge polished by handling
            M += 46.0 * shoulder
            R -= 52.0 * shoulder
            C -= 26.0 * shoulder
            # 3. STRUCTURAL TOOTH + PATINA GRAIN (two independent detail bands)
            soft = (mat <= 1).astype(np.float32)
            R += np.clip(tooth * 260.0, -70.0, 70.0) * (0.45 + 0.55 * soft)
            M += np.clip(tooth * 300.0, -80.0, 80.0) * (1.0 - 0.45 * soft)
            # 4. GATED PIT LATTICE — crust pits, metal does not. Amplitude rides
            # the structure so the pitting sits in the material, not over it.
            env = np.clip(0.30 + 0.90 * np.clip(Ssharp, 0.0, 1.0), 0.0, 1.2)
            R += 34.0 * pit * soft * pit_k * env
            C += 22.0 * pit * soft * pit_k * env
            M -= 20.0 * pit * soft * pit_k * env
            # 5. METAL FLECK — inlay lane only, same structural envelope
            inl = (mat == 3).astype(np.float32)
            M += 20.0 * fleck * inl * env
            R -= 22.0 * fleck * inl * env
            # 6. BURIAL GRADIENT — whole regions go dead; decorrelates channels
            bur = (burial - 0.5) * float(rkw.get("burial", 0.75))
            M -= 54.0 * np.clip(bur, 0.0, 1.0)
            R += 46.0 * np.clip(bur, 0.0, 1.0)
            C += 40.0 * np.clip(bur, 0.0, 1.0)
            m2 = np.asarray(mask, np.float32)
            if m2.ndim == 3:
                m2 = m2[:, :, 0]
            if m2.shape[:2] != (WORK, WORK):
                m2 = cv2.resize(m2, (WORK, WORK), interpolation=cv2.INTER_LINEAR)
            mk_ = np.clip(m2, 0.0, 1.0)
            inv = 1.0 - mk_
            out = np.empty((WORK, WORK, 4), np.uint8)
            out[:, :, 0] = np.clip(M * mk_ + 4.0 * inv, 0, 255).astype(np.uint8)
            out[:, :, 1] = np.clip(R * mk_ + 120.0 * inv, 6, 255).astype(np.uint8)
            out[:, :, 2] = np.clip(C * mk_ + 16.0 * inv, 16, 255).astype(np.uint8)
            out[:, :, 3] = 255
            if (fh, fw) != (WORK, WORK):
                out = cv2.resize(out, (fw, fh), interpolation=cv2.INTER_LINEAR)
            return out

        return spec_fn, paint_fn
