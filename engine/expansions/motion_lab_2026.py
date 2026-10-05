"""FRACTURED MOTION — finishes engineered to READ AS MOVING under a changing light angle.

Owner mission 2026-08-10: "finishes that look like they dance/move/shift within the light...
running water, bullet travel, lightning striking". Theory + the 7 mechanisms:
docs/MOTION_LAB_THEORY.md. Sibling of nightshift_lab_2026.py (that one exploits a change of
LIGHTING CONDITION; this one exploits a change of ANGLE).

THE PHYSICS, STATED HONESTLY (this drove every design decision here)
-------------------------------------------------------------------
pixel ~= diffuse(albedo * N.L * ambient) + specular(N, V, L, M, G, Cc). We have NO normal map,
so N is fixed per pixel by the car's geometry. As the car turns, the only thing changing per
pixel is N.H. The locus where N.H ~ 1 is the highlight, and it SWEEPS across the body.

Crucially: roughness (G) sets the WIDTH of a pixel's angular response, NOT the angle at which it
triggers. Two pixels with the same normal fire at the same instant no matter what G is. So we
cannot literally schedule a pixel to light "later".

What we CAN do -- and what this whole module is built on -- is make the sweep's own progress
LEGIBLE. The car's curvature already sequences the crossing; the paint decides whether that
reads as a smooth smear (invisible) or as a pulse stepping along a path (motion):

  * DISCRETENESS  -- quantized bands, so the eye sees steps instead of a gradient
  * NARROW APERTURE -- each step is a brief bright pop, not a dim always-on glow
  * ADJACENT CONTRAST -- neighbouring bands differ in amplifier/colour, so the lit band is
    unmistakable against the ones not yet lit
  * TWO LOBES OFFSET -- base spec (M/G) and the WHITE clearcoat lobe carry displaced patterns, so
    two highlights slide past each other = the only real depth cue available without a normal map

LAW A (non-negotiable): UV is reversed / rotated / scattered per car, so NO global straight-line
flow -- it would look broken on most cars. Every flow field here is locally coherent but globally
omnidirectional (curl noise, radial/spiral, or multi-domain).
LAW B: bands stay 8-32 px. Finer bands = more steps per panel = smoother chase.

Channel map: R=Metallic(0..255) G=Roughness(0=mirror..255=matte) B=Clearcoat(16=max gloss..255=dull)
"""

import zlib
from collections import OrderedDict

import cv2
import numpy as np

_W = 1024          # work grid; resized to the render canvas (2048 -> x2)


# ------------------------------------------------------------------ helpers
def _salt(gid):
    """Stable per-finish salt. NOT hash() -- python randomizes string hashing per process, so
    hash(gid) gave a different value in every process and the finish rendered DIFFERENTLY on every
    server restart (measured: 44772 / 44321 / 1039 for the same id). crc32 is specified and
    identical everywhere."""
    return zlib.crc32(gid.encode("utf-8")) & 0xFFFF


def _rng(seed, salt):
    return np.random.default_rng((int(seed) * 1000003 + int(salt)) & 0x7FFFFFFF)


def _periodic_resize(g, w, h, interpolation):
    """Resize a coarse random grid to (w,h) PERIODICALLY (torus), not clamped.

    [SPB SEAMLESS 2026-08-16 — owner: "MANY of them have an outside border. When we size these
    down the borders become a HUGE issue... should be seamless where they tile easier and
    absolutely NO outside border."] Plain cv2.resize extrapolates at the canvas edge, so every
    field carried an edge bias; the narrow _aa threshold windows (Law C) then saturated it into
    a hard ring — measured: path mask pinned at 1.0 for the outer ~8px on 11 finishes (dark
    border), 0.18 on quicksilver (bright border). Interpolating on a 2x2 tiling and cropping the
    fully-interior centre tile makes the field wrap exactly: no border, and the finish tiles
    seamlessly at any base_scale.
    """
    t = np.tile(g, (2, 2))
    big = cv2.resize(t, (2 * w, 2 * h), interpolation=interpolation)
    return np.ascontiguousarray(big[h // 2:h // 2 + h, w // 2:w // 2 + w])


def _hash01(h, w, rng, cell):
    """White noise at `cell` px, nearest-upsampled: crisp per-feature randomness. Periodic."""
    gh, gw = max(1, h // cell), max(1, w // cell)
    return _periodic_resize(rng.random((gh, gw), dtype=np.float32), w, h, cv2.INTER_NEAREST)


def _smooth(h, w, rng, cell):
    gh, gw = max(2, h // cell), max(2, w // cell)
    return _periodic_resize(rng.random((gh, gw), dtype=np.float32), w, h, cv2.INTER_CUBIC)


def _xy(h, w):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return x / w, y / h


def _cellF1F2(h, w, rng, cell):
    """Worley F1/F2 + per-cell id. Used for multi-domain (omnidirectional) flows.

    [T1 perf -> REVERTED 2026-08-10] A half-resolution solve with bilinear upsample was ~4x
    cheaper, and I assumed _aa() would re-sharpen the walls. It does not: the upsample smooths
    F1/F2 themselves, so every mask derived from them gets soft low-frequency edges. The gate
    caught it -- the three worst feature-scale scores in the fleet were exactly the Worley-driven
    finishes (0.153-0.179) while the two best were driven by INTER_NEAREST noise (0.264, 0.288).
    That was premature optimisation: the fleet renders in ~1.7s against a 3s budget, so there is
    no need to buy speed with sharpness. Solving at full resolution.
    """
    gh, gw = max(2, h // cell), max(2, w // cell)
    pts = np.stack([rng.random((gh, gw), dtype=np.float32),
                    rng.random((gh, gw), dtype=np.float32)], -1)
    ids = rng.random((gh, gw), dtype=np.float32)
    x, y = _xy(h, w)
    gx = np.clip((x * gw).astype(np.int32), 0, gw - 1)
    gy = np.clip((y * gh).astype(np.int32), 0, gh - 1)
    F1 = np.full((h, w), 9.0, np.float32)
    F2 = np.full((h, w), 9.0, np.float32)
    ID = np.zeros((h, w), np.float32)
    # [SPB SEAMLESS 2026-08-16] Toroidal Worley. The old np.clip DUPLICATED edge cells for the
    # out-of-range neighbours, which skewed F1/F2 in the outer half-cell; the narrow _aa windows
    # saturated that skew into the owner-reported hard border, and the field could never tile.
    # Wrap the neighbour lookup (modulo) and measure distance on the torus (shortest wrapped
    # delta per axis): no border, exact seamless tiling.
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx = (gx + dx) % gw
            cy = (gy + dy) % gh
            ddx = x * gw - (cx + pts[cy, cx, 0])
            ddy = y * gh - (cy + pts[cy, cx, 1])
            ddx -= gw * np.round(ddx / gw)
            ddy -= gh * np.round(ddy / gh)
            d = np.sqrt(ddx * ddx + ddy * ddy)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, ids[cy, cx], ID)
            F1 = np.minimum(F1, d)
    # UNITS: d is scaled by gw/gh, so F1/F2/(F2-F1) are in CELL widths, NOT pixels.
    # (F2-F1) typically lands ~0.05-0.5. Thresholds passed to _aa() MUST be in those units --
    # writing pixel-scale thresholds (0.55, 1.6) saturates _aa and the mask becomes all-ones,
    # i.e. no structure at all. That bug made the whole first pilot batch structureless.
    return F1, F2, ID


def _aa(field, lo, hi):
    """Hard edge with a ~1px ramp. Half-metal reads mushy in PBR (nightshift lesson)."""
    return np.clip((field - lo) / max(1e-6, (hi - lo)), 0, 1)


# The CRUSH LAW ladder, reused verbatim: quantized razor terraces. Invented for colour flip,
# it is ALSO the motion engine -- discrete steps are what make a sweep read as travel.
_TIERS = np.float32([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92])


def _tiers(idfield):
    return np.take(_TIERS, (idfield * len(_TIERS)).astype(np.int32) % len(_TIERS))


def _quant(field, n):
    """Quantize 0..1 to n discrete steps, returned as 0..1. THE core motion primitive."""
    n = max(2, int(n))
    return np.floor(np.clip(field, 0, 0.9999) * n) / (n - 1.0)


def _curl_flow(h, w, rng, cell):
    """Divergence-free-ish flow potential -> a phase field that is locally smooth but has NO
    global direction (LAW A). `phase` is 'distance along the streamline'."""
    p = _smooth(h, w, rng, cell)
    q = _smooth(h, w, rng, max(4, cell // 2))
    gy, gx = np.gradient(p)
    # rotate the gradient 90deg = flow along iso-lines of p; integrate cheaply via q blend
    ang = np.arctan2(gx, -gy)
    phase = (ang / (2 * np.pi) + 0.5 + 0.35 * q) % 1.0
    return phase.astype(np.float32)


def _radial_phase(h, w, rng, n_centres, twist=0.0):
    """Radial/spiral phase from scattered centres. Direction-free by construction."""
    x, y = _xy(h, w)
    phase = np.zeros((h, w), np.float32)
    wsum = np.zeros((h, w), np.float32)
    # [SPB SEAMLESS 2026-08-16] Toroidal distance: a centre near one edge now continues on the
    # opposite edge instead of leaving a chopped arc + border discontinuity (owner report:
    # spiral/radial finishes showed the worst tiling seams). Same look everywhere else — only
    # the wrap-around neighbourhood changes.
    for _ in range(int(n_centres)):
        cx, cy = float(rng.random()), float(rng.random())
        dx, dy = (x - cx), (y - cy)
        dx -= np.round(dx)
        dy -= np.round(dy)
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        a = np.arctan2(dy, dx) / (2 * np.pi) + 0.5
        ph = (r * 6.0 + twist * a) % 1.0
        wt = 1.0 / (r + 0.12)
        phase += ph * wt
        wsum += wt
    return (phase / np.maximum(wsum, 1e-6)).astype(np.float32)


# ---------------------------------------------------------------- the factory
def _make_motion(gid, base_rgb, accent_rgb, flow, mech,
                 bands=16, g_lo=9.0, g_hi=64.0,
                 parallax=0, trail=0.0, ramp=0.0, counter=False,
                 graze=0.0, lattice=0.0, accent_mix=0.55, fine=0.0):
    """flow(h, w, rng) -> dict(phase=0..1 progress-along-path, [path]=0..1 structure mask,
                               [id], [micro])

    mech: label string for the owner's in-sim verdict ("M1", "M1+M3", ...). Recorded so a
    verdict maps back to a MECHANISM, not just to one finish.
    bands:    discrete steps in the chase ladder (higher = finer = smoother travel)
    g_lo/hi:  aperture ladder ends. Narrow (low) = brief bright pop.
    parallax: px offset between the base-spec pattern and the WHITE clearcoat pattern (M2)
    trail:    0..1 how much the highlight switches metal<->dielectric along phase (M3)
    ramp:     0..1 large-scale aperture gradient -> dwell varies -> accel/decel (M4)
    counter:  interleave two 3px populations with opposite phase -> churn, not translate (M5)
    graze:    0..1 slow large-scale Cc migration band (M6)
    lattice:  0..1 sparse near-mirror crawl points (M7)
    fine:     0..1 fine-scale perturbation of the phase BEFORE quantizing. Coarse flows (curl
              cell >=110) produce bands many pixels wide, which fails the 8-32px fine-detail law
              (measured fineness 0.075-0.091 vs the 0.10 bar). Perturbing phase subdivides the
              band boundaries into intricate edges instead of smooth curves -- it raises
              high-frequency energy AND gives more steps, so it helps the chase too.
    """

    # [T1 perf] spec_fn and paint_fn each need the SAME fields, and the flow (Worley at fine
    # cells) is the expensive part -- computing it twice pushed three finishes to ~3.6s, over
    # the 3s budget. Cache per seed; a finish is always rendered spec-then-paint with one seed.
    _cache = {}

    def _fields(seed):
        key = int(seed)
        hit = _cache.get(key)
        if hit is not None:
            return hit
        rng = _rng(seed, _salt(gid))
        f = flow(_W, _W, rng)
        f.setdefault("path", np.ones((_W, _W), np.float32))
        f.setdefault("micro", _hash01(_W, _W, rng, 2))
        f.setdefault("id", _hash01(_W, _W, rng, 6))
        f["macro"] = _smooth(_W, _W, rng, 192)
        if counter:
            # 3px interleave: two populations, opposite progress along the same flow
            yy, xx = np.mgrid[0:_W, 0:_W]
            f["pop"] = np.float32(((xx // 3) + (yy // 3)) % 2)
        if lattice > 0:
            f["lat"] = _hash01(_W, _W, rng, 4)
        if fine > 0:
            # cell 12 on the 1024 grid -> ~24px features at the 2048 canvas: inside the law
            f["fine"] = _smooth(_W, _W, rng, 12)
        if len(_cache) > 4:
            _cache.clear()
        _cache[key] = f
        return f

    def _rs(a, fw, fh):
        return cv2.resize(a, (fw, fh), interpolation=cv2.INTER_LINEAR)

    def _mask2(mask, fh, fw):
        m2 = np.asarray(mask, np.float32)
        if m2.ndim == 3:
            m2 = m2[:, :, 0]
        if m2.shape[:2] != (fh, fw):
            m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
        return np.clip(m2, 0, 1)

    def _chase(f, fw, fh):
        """Shared band computation: the discrete step index along the flow, 0..1."""
        ph = _rs(f["phase"], fw, fh)
        if fine > 0 and "fine" in f:
            ph = (ph + fine * (_rs(f["fine"], fw, fh) - 0.5)) % 1.0
        if counter and "pop" in f:
            pop = _rs(f["pop"], fw, fh)
            ph = np.where(pop > 0.5, (ph + 0.5) % 1.0, ph)   # opposite progress
        return _quant(ph, bands), ph

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        mm = _mask2(mask, fh, fw)
        f = _fields(seed)
        step, ph = _chase(f, fw, fh)
        path = _rs(f["path"], fw, fh)
        micro = _rs(f["micro"], fw, fh)
        idf = _rs(f["id"], fw, fh)
        macro = _rs(f["macro"], fw, fh)
        tier = _tiers(idf)

        # --- M1: aperture ladder across the discrete bands -----------------
        # Narrow apertures on-path = a brief bright pop as the sweep crosses.
        G = g_lo + (g_hi - g_lo) * step
        # --- M4: large-scale ramp stretches/compresses dwell ---------------
        if ramp > 0:
            G = G * (1.0 - ramp * 0.55) + (g_hi * 1.45) * (ramp * 0.55) * macro
        # off-path skin stays matte so it never competes with the pulse -- but keep a gentle
        # band echo in it, otherwise a finish whose path is only thin cores has almost all its
        # area at one aperture and G variance collapses (mo_tracer_fire measured G std 14).
        G = G * path + (186.0 + micro * 40.0 + 26.0 * step) * (1.0 - path)
        G = G + micro * 6.0

        # --- amplifier: metal on-path, dielectric off ----------------------
        # [T1 fix] M was `6 + path*(232+..)`, and the M2/parallax flows set no `path` (defaults
        # to ones) -> metal uniformly maxed, M std ~4. That breaks the ADJACENT CONTRAST rule in
        # docs/MOTION_LAB_THEORY.md: neighbouring bands must differ in AMPLIFIER as well as
        # aperture, or the lit band is not unmistakable against the ones not yet lit. Bands now
        # step the amplifier too, which is both the fix and better motion.
        band_amp = 0.42 + 0.58 * step
        # Off-path skin is NOT uniform: it carries banded micro-flake. Without this a thin-vein
        # finish has ~89% of its canvas at one constant M and fails the strength gate however
        # good the lit lane is (breakdown_arc, measured). Doctrine wants many distinct shades.
        skin_m = 10.0 + 26.0 * step * tier + micro * 22.0
        M = skin_m * (1.0 - path) + (14.0 + (232.0 + tier * 20.0) * band_amp) * path
        # --- M3: colour trail. Along phase, hand the highlight to the WHITE
        # clearcoat lobe instead of albedo-tinted metal -> it changes hue as it moves.
        white = np.zeros_like(M)
        if trail > 0:
            wz = _aa(np.abs(step - 0.5) * 2.0, 1.0 - trail, 1.0 - trail * 0.35) * path
            white = wz
            M = M * (1.0 - wz) + 44.0 * wz            # mostly-dielectric = white flash

        # --- Cc: the second lobe. M2 offsets it from the base pattern ------
        if parallax:
            step_cc = np.roll(step, int(parallax), axis=1)
            step_cc = np.roll(step_cc, int(parallax) // 2, axis=0)
        else:
            step_cc = step
        # Same for clearcoat: the skin gets a banded sheen instead of a flat 236, so the
        # dominant off-path population contributes variance too.
        CC = (208.0 + 40.0 * step_cc + micro * 12.0) * (1.0 - path)              + (236.0 - 200.0 * step_cc) * path          # low Cc = gloss POWER on
        if graze > 0:
            CC = CC * (1.0 - graze) + (16.0 + 200.0 * macro) * graze
        if trail > 0:
            CC = CC * (1.0 - white) + 16.0 * white     # white lobe fully on at the hot tip

        # --- M7: sparse near-mirror crawl points ---------------------------
        if lattice > 0:
            lat = _rs(f["lat"], fw, fh)
            spark = (lat > (1.0 - 0.06 * lattice)).astype(np.float32)
            M = M * (1.0 - spark) + 252.0 * spark
            G = G * (1.0 - spark) + (4.0 + 8.0 * tier) * spark
            CC = CC * (1.0 - spark) + 18.0 * spark

        out = np.zeros((fh, fw, 4), np.uint8)
        inv = 1.0 - mm
        out[:, :, 0] = np.clip(M * mm + 4.0 * inv, 0, 255)
        out[:, :, 1] = np.clip(np.clip(G, 4, 255) * mm + 120.0 * inv, 0, 255)
        out[:, :, 2] = np.clip(np.clip(CC, 16, 255) * mm + 16.0 * inv, 0, 255)
        out[:, :, 3] = 255
        return out

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.max() > 1.5:
            src = src / 255.0
        mm = _mask2(mask, fh, fw)
        f = _fields(seed)
        step, ph = _chase(f, fw, fh)
        path = _rs(f["path"], fw, fh)[..., None]
        micro = _rs(f["micro"], fw, fh)[..., None]
        tier = _tiers(_rs(f["id"], fw, fh))[..., None]
        stepc = step[..., None]

        base = np.float32(base_rgb)[None, None, :] / 255.0
        acc = np.float32(accent_rgb)[None, None, :] / 255.0
        # pre-crushed paint: dark so the specular pulse dominates. The albedo carries the
        # SAME discrete banding as the spec, so the structure stays visible in flat light too.
        body = base * (0.30 + 0.34 * tier) * (0.93 + 0.14 * micro)
        lane = acc * (0.42 + 0.58 * stepc)
        outc = body * (1.0 - path * accent_mix) + lane * (path * accent_mix)
        strength = np.clip(mm * float(pm), 0, 1)[..., None]
        out = src * (1.0 - strength) + np.clip(outc, 0, 1) * strength
        return out.astype(np.float32)

    return spec_fn, paint_fn


# ------------------------------------------------------- flows (LAW A: no global direction)
def _f_stream(h, w, rng):
    """Running water: curl flow, banded along the streamlines."""
    ph = _curl_flow(h, w, rng, 96)
    F1, F2, _ = _cellF1F2(h, w, rng, 26)
    # cell units: wide gaps = channel interiors, narrow = the braid walls
    path = _aa(F2 - F1, 0.04, 0.26)                # braided channels
    return {"phase": ph, "path": np.clip(0.18 + 0.82 * path, 0, 1)}


def _f_tracer(h, w, rng):
    """Bullet/tracer: thin high-contrast streaks along a curl field.
    [gate 2026-08-10] curl cell was 120 -> feature-scale 0.152, below the approved-fleet floor of
    0.192. Halved to 58: same omnidirectional flow, roughly twice the spatial frequency."""
    ph = _curl_flow(h, w, rng, 58)
    # cell is WORK-GRID px and the canvas is 2x it, so cell 34 meant 68px features -- outside the
    # 8-32px law, which is why the gate failed this one on feature scale. 13 -> ~26px.
    F1, F2, ID = _cellF1F2(h, w, rng, 13)
    core = 1.0 - _aa(F2 - F1, 0.02, 0.18)          # sharp thin filament cores
    return {"phase": ph, "path": np.clip(core, 0, 1), "id": ID}


def _f_bolt(h, w, rng):
    """Lightning: branching ridges (ridged noise) as the discharge path."""
    a = _smooth(h, w, rng, 64)
    b = _smooth(h, w, rng, 23)
    ridge = 1.0 - np.abs(2.0 * a - 1.0)
    ridge = ridge * (0.65 + 0.35 * (1.0 - np.abs(2.0 * b - 1.0)))
    # was 0.72-0.94 -> path_mean 0.08, i.e. a black car with two scratches on it. Denser.
    path = np.clip(0.14 + 0.86 * _aa(ridge, 0.52, 0.80), 0, 1)
    ph = _curl_flow(h, w, rng, 80)
    return {"phase": ph, "path": path}


def _f_vortex(h, w, rng):
    """Spiral phase from scattered centres -- direction-free by construction."""
    ph = _radial_phase(h, w, rng, 5, twist=3.0)
    # sheared arm structure so the vortex has substance, not just banding
    arms = _aa(np.abs(2.0 * _smooth(h, w, rng, 34) - 1.0), 0.18, 0.62)
    return {"phase": ph, "path": np.clip(0.25 + 0.75 * arms, 0, 1)}


def _f_ripple(h, w, rng):
    """Concentric interference; a fine crazing net gives the lacquer something to sit under."""
    ph = _radial_phase(h, w, rng, 3, twist=0.0)
    F1, F2, _ = _cellF1F2(h, w, rng, 14)
    craze = 1.0 - _aa(F2 - F1, 0.03, 0.22)
    return {"phase": ph, "path": np.clip(0.30 + 0.70 * craze, 0, 1)}


def _f_shatterdomain(h, w, rng):
    """Multi-domain: every Worley cell gets its OWN phase offset -> omnidirectional."""
    F1, F2, ID = _cellF1F2(h, w, rng, 14)      # 28 -> 56px features, outside the law; halved
    # [gate 2026-08-10] curl 110 / cell 40 measured 0.153, under the approved floor -> finer both.
    ph = (_curl_flow(h, w, rng, 54) + ID) % 1.0
    walls = 1.0 - _aa(F2 - F1, 0.03, 0.20)
    return {"phase": ph, "path": np.clip(0.22 + 0.78 * walls, 0, 1), "id": ID}


def _f_weave(h, w, rng):
    """Fine woven bands riding a curl field -- dense, high step count."""
    ph = _curl_flow(h, w, rng, 72)
    m = _hash01(h, w, rng, 3)
    return {"phase": ph, "path": np.clip(0.55 + 0.45 * m, 0, 1)}


# ------------------------------------------------- batch 2 flows (new MATH, not recolours)
def _f_droplet(h, w, rng):
    """Rain on water: many expanding ring systems, nearest-impact wins. Phase = ring index, so
    the chase runs OUTWARD from each impact -- omnidirectional by construction."""
    x, y = _xy(h, w)
    best = np.full((h, w), 9.0, np.float32)
    ph = np.zeros((h, w), np.float32)
    for _ in range(9):
        cx, cy = float(rng.random()), float(rng.random())
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        take = r < best
        best = np.where(take, r, best)
        ph = np.where(take, (r * 26.0) % 1.0, ph)          # tight rings ~= 20px at 2048
    rim = _aa(np.abs(2.0 * ((best * 26.0) % 1.0) - 1.0), 0.35, 0.95)
    return {"phase": ph, "path": np.clip(0.20 + 0.80 * rim, 0, 1)}


def _f_moire(h, w, rng):
    """MOIRE BEAT -- the strongest angle amplifier available. Two near-identical fine grids at a
    small relative rotation produce a beat whose apparent position shifts far more than the
    angle change that caused it. Rotation is per-domain so there is no global direction."""
    F1, F2, ID = _cellF1F2(h, w, rng, 18)
    x, y = _xy(h, w)
    a1 = (ID * 2.0 * np.pi)
    a2 = a1 + 0.13                                          # the beat comes from this offset
    # [gate 2026-08-10] k was 150 -> ~86px grid period, and PATH was taken from the beat. A beat
    # IS the low-frequency difference of two grids, so structuring on it guarantees coarse
    # features (measured 0.166 vs the 0.19 approved floor). Keep the beat as PHASE -- that is the
    # angle amplifier and coarse is fine there -- but take the STRUCTURE from the fine grid.
    # k=430 -> ~15px period on the work grid (~30px on canvas), inside the 8-32px law.
    k = 430.0
    g1 = np.sin((x * np.cos(a1) + y * np.sin(a1)) * k)
    g2 = np.sin((x * np.cos(a2) + y * np.sin(a2)) * k)
    beat = (g1 * g2 + 1.0) * 0.5
    grid = (g1 + 1.0) * 0.5                                 # the FINE carrier = the structure
    # [gate 2026-08-10, third pass] Measured the components: the fine grid scored 0.143 -- WORSE
    # than the coarse beat -- even at a 35px period. Because a SINE IS SMOOTH: almost no energy
    # below 3px, so a soft _aa ramp over it reads as a blob however short its period. The
    # fine-detail law is about SHARP EDGES, not just spatial frequency (CLAUDE.md: "never a smooth
    # flat ramp"). Threshold the carrier to crisp lines + a micro dither, and drop the path floor
    # so the lines actually bite.
    # Both carriers thresholded = a crisp CROSS-HATCH, which is also truer to the moire idea
    # (two interfering grids) than one line set. The 1024->2048 bilinear upsample softens edges,
    # so the structure has to be finer than the target on the work grid to survive it.
    lines1 = _aa(grid, 0.475, 0.525)
    lines2 = _aa((g2 + 1.0) * 0.5, 0.46, 0.54)
    hatch = np.maximum(lines1, lines2 * 0.8)
    dither = _hash01(h, w, rng, 2)
    return {"phase": beat.astype(np.float32),
            "path": np.clip(0.06 + 0.94 * hatch * (0.80 + 0.40 * dither), 0, 1), "id": ID}


def _f_ferro(h, w, rng):
    """Ferrofluid spikes: cusped radial lobes from scattered poles (Rosensweig-ish)."""
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    ph = np.zeros((h, w), np.float32)
    for _ in range(7):
        cx, cy = float(rng.random()), float(rng.random())
        dx, dy = x - cx, y - cy
        dx -= np.round(dx)                                  # [SEAMLESS 2026-08-16] toroidal
        dy -= np.round(dy)
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        a = np.arctan2(dy, dx)
        lobes = np.abs(np.cos(a * 9.0))                     # cusped spikes
        v = lobes / (1.0 + 26.0 * r)
        ph = np.where(v > acc, (r * 18.0) % 1.0, ph)
        acc = np.maximum(acc, v)
    return {"phase": ph, "path": np.clip(_aa(acc, 0.08, 0.42), 0, 1)}


def _f_shockring(h, w, rng):
    """Supersonic crack: a FEW hard-edged expanding rings, mostly empty between them."""
    x, y = _xy(h, w)
    ph = np.zeros((h, w), np.float32)
    hit = np.zeros((h, w), np.float32)
    for _ in range(4):
        cx, cy = float(rng.random()), float(rng.random())
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        band = np.abs(((r * 9.0) % 1.0) - 0.5)
        edge = _aa(0.5 - band, 0.34, 0.49)                  # thin hard shells
        ph = np.where(edge > hit, (r * 9.0) % 1.0, ph)
        hit = np.maximum(hit, edge)
    return {"phase": ph, "path": np.clip(0.14 + 0.86 * hit, 0, 1)}


def _f_turbulence(h, w, rng):
    """Smoke/heat: two curl scales stacked, so the fine flow is dragged by the coarse one."""
    coarse = _curl_flow(h, w, rng, 140)
    fine = _curl_flow(h, w, rng, 34)
    ph = (fine + 0.45 * coarse) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.30 + 0.70 * _smooth(h, w, rng, 26), 0, 1)}


def _f_capillary(h, w, rng):
    """Branching veins by iterated blur+threshold (cheap reaction-diffusion stand-in)."""
    f = _smooth(h, w, rng, 20)
    for _ in range(3):
        b = cv2.GaussianBlur(f, (0, 0), 2.0)
        f = np.clip(f + 1.35 * (f - b), 0, 1)               # unsharp -> filaments sharpen
    veins = _aa(f, 0.60, 0.80)
    ph = _curl_flow(h, w, rng, 66)
    return {"phase": ph, "path": np.clip(0.18 + 0.82 * veins, 0, 1)}


def _f_lamella(h, w, rng):
    """Overlapping scales/plates: each Worley cell gets a radial phase from its own centre."""
    F1, F2, ID = _cellF1F2(h, w, rng, 16)
    ph = ((F1 * 3.2) + ID) % 1.0                            # phase runs out from each cell centre
    plate = 1.0 - _aa(F2 - F1, 0.02, 0.22)
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.26 + 0.74 * plate, 0, 1), "id": ID}


def _f_sparkshower(h, w, rng):
    """Sparse hot points with radial comet trails -- population migrates as the sweep turns."""
    pts = _hash01(h, w, rng, 9)
    seeds = (pts > 0.955).astype(np.float32)
    trail = cv2.GaussianBlur(seeds, (0, 0), 3.5)
    ph = _radial_phase(h, w, rng, 6, twist=1.4)
    return {"phase": ph, "path": np.clip(_aa(trail, 0.004, 0.10), 0, 1)}


# ------------------------------------------------- batch 3 flows (Law C: crisp edges throughout)
def _f_chevron_domains(h, w, rng):
    """Herringbone, but every Worley domain sets its OWN chevron angle (Law A)."""
    F1, F2, ID = _cellF1F2(h, w, rng, 22)
    x, y = _xy(h, w)
    a = ID * 2.0 * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    v = -x * np.sin(a) + y * np.cos(a)
    saw = np.abs(((v * 110.0) % 2.0) - 1.0)
    band = _aa(np.abs(((u * 96.0 + saw * 0.5) % 1.0) - 0.5), 0.34, 0.48)
    ph = (u * 6.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.14 + 0.86 * band, 0, 1), "id": ID}


def _f_hex_chase(h, w, rng):
    """Tight cell lattice; phase runs out of each cell centre so the comb lights cell by cell."""
    F1, F2, ID = _cellF1F2(h, w, rng, 13)
    walls = 1.0 - _aa(F2 - F1, 0.015, 0.14)
    ph = ((F1 * 4.5) + ID * 0.7) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * walls, 0, 1), "id": ID}


def _f_crack_impact(h, w, rng):
    """Windscreen strike: thin Voronoi cracks, phase radiating from the impact points."""
    F1, F2, ID = _cellF1F2(h, w, rng, 10)
    cracks = 1.0 - _aa(F2 - F1, 0.02, 0.18)
    ph = _radial_phase(h, w, rng, 3, twist=0.0)
    return {"phase": ph, "path": np.clip(0.18 + 0.82 * cracks, 0, 1), "id": ID}


def _f_thread_cross(h, w, rng):
    """Two crossed crisp thread sets, angle per domain."""
    F1, F2, ID = _cellF1F2(h, w, rng, 30)
    x, y = _xy(h, w)
    a = ID * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    v = -x * np.sin(a) + y * np.cos(a)
    t1 = _aa(np.abs(((u * 104.0) % 1.0) - 0.5), 0.30, 0.46)
    t2 = _aa(np.abs(((v * 104.0) % 1.0) - 0.5), 0.30, 0.46)
    ph = (u * 5.0 + v * 3.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.12 + 0.88 * np.maximum(t1, t2 * 0.85), 0, 1), "id": ID}


def _f_bubble_rim(h, w, rng):
    """Packed cells with phase living on the RIM only -- foam that travels."""
    F1, F2, ID = _cellF1F2(h, w, rng, 15)
    rim = _aa(F1, 0.30, 0.52) * (1.0 - _aa(F1, 0.52, 0.74))
    rim = _aa(rim, 0.25, 0.65)
    ph = (F1 * 5.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * rim, 0, 1), "id": ID}


def _f_lichtenberg(h, w, rng):
    """Dielectric breakdown: sparse seeds grown by iterated dilate, thresholded hard."""
    seeds = (_hash01(h, w, rng, 26) > 0.985).astype(np.float32)
    k = np.ones((3, 3), np.float32)
    grown = seeds.copy()
    for _ in range(9):
        grown = np.clip(cv2.dilate(grown, k) * 0.88 + grown, 0, 1)
    veins = _aa(grown, 0.12, 0.40)
    ph = _curl_flow(h, w, rng, 70)
    return {"phase": ph, "path": np.clip(0.10 + 0.90 * veins, 0, 1)}


def _f_glitch_slivers(h, w, rng):
    """Signal tearing: crisp slivers whose direction is per domain, never global."""
    F1, F2, ID = _cellF1F2(h, w, rng, 34)
    x, y = _xy(h, w)
    a = ID * 2.0 * np.pi
    v = -x * np.sin(a) + y * np.cos(a)
    jitter = _hash01(h, w, rng, 3)
    sliv = _aa(np.abs(((v * 70.0 + jitter * 0.6) % 1.0) - 0.5), 0.38, 0.49)
    ph = (v * 8.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.12 + 0.88 * sliv, 0, 1), "id": ID}


def _f_marble_vein(h, w, rng):
    """Domain-warped seams: warp the coordinate field by noise, then threshold hard."""
    warp = _smooth(h, w, rng, 60)
    warp2 = _smooth(h, w, rng, 22)
    x, y = _xy(h, w)
    f = np.sin((x * 30.0 + warp * 9.0) + (y * 22.0 + warp2 * 7.0))
    veins = _aa(np.abs(f), 0.00, 0.16)
    ph = (warp + warp2 * 0.5) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.12 + 0.88 * (1.0 - veins), 0, 1)}


# ------------------------------------------------- batch 4 flows (2x rule + Law C from the start)
def _f_spiral_arms(h, w, rng):
    """Log-spiral arms from scattered cores; arms thresholded crisp."""
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    ph = np.zeros((h, w), np.float32)
    for _ in range(4):
        cx, cy = float(rng.random()), float(rng.random())
        dx, dy = x - cx, y - cy
        dx -= np.round(dx)                                  # [SEAMLESS 2026-08-16] toroidal
        dy -= np.round(dy)
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        a = np.arctan2(dy, dx)
        arm = np.cos(a * 3.0 - np.log(r + 0.02) * 7.0)
        v = _aa(arm, 0.55, 0.80) / (1.0 + 5.0 * r)
        ph = np.where(v > acc, (r * 22.0) % 1.0, ph)
        acc = np.maximum(acc, v)
    return {"phase": ph, "path": np.clip(0.12 + 0.88 * _aa(acc, 0.05, 0.30), 0, 1)}


def _f_coalesce(h, w, rng):
    """Merging droplets: metaball field thresholded hard, phase on the merge rims."""
    x, y = _xy(h, w)
    field = np.zeros((h, w), np.float32)
    for _ in range(26):
        cx, cy = float(rng.random()), float(rng.random())
        rr = 0.035 + 0.045 * float(rng.random())
        dx, dy = x - cx, y - cy
        dx -= np.round(dx)                                  # [SEAMLESS 2026-08-16] toroidal
        dy -= np.round(dy)
        d2 = dx * dx + dy * dy
        field += np.exp(-d2 / (rr * rr))
    blobs = _aa(field, 0.55, 0.72)
    rim = _aa(np.abs(field - 0.62), 0.00, 0.10)
    ph = (field * 3.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(1.0 - rim, blobs * 0.4), 0, 1)}


def _f_turing_stripe(h, w, rng):
    """Reaction-diffusion-ish stripes: difference of gaussians, thresholded to crisp bands."""
    n = _smooth(h, w, rng, 8)
    a = cv2.GaussianBlur(n, (0, 0), 1.6)
    b = cv2.GaussianBlur(n, (0, 0), 4.2)
    dog = a - b
    # A DoG contour is smooth by construction, so dither the threshold itself: the stripe EDGE
    # then carries sub-3px irregularity instead of being a clean curve (the moire lesson).
    dither = _hash01(h, w, rng, 2)
    stripes = _aa(dog + (dither - 0.5) * 0.010, 0.0, 0.004)
    # phase wraps 16x instead of 4x -> narrower bands -> the G channel carries real mid/high
    # frequency instead of a few wide smooth contours. THIS is the lever the metric responds to.
    ph = (n * 30.0) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * stripes, 0, 1)}


def _f_shard_fan(h, w, rng):
    """Angular fan sectors, one fan per domain: crisp radial spokes, no global direction."""
    F1, F2, ID = _cellF1F2(h, w, rng, 15)
    # Same fix as gearworks: irregular Worley-derived fan centres, no axis-aligned grid.
    # Same jittered-hub fix as gearworks.
    x, y = _xy(h, w)
    Nf = 8.0
    jfx = _hash01(h, w, rng, max(2, int(h / Nf)))
    jfy = _hash01(h, w, rng, max(2, int(h / Nf)) + 1)
    cx = (np.floor(x * Nf) + 0.2 + 0.6 * jfx) / Nf
    cy = (np.floor(y * Nf) + 0.2 + 0.6 * jfy) / Nf
    a = np.arctan2(y - cy, x - cx) / (2 * np.pi) + 0.5
    spokes = _aa(np.abs(((a * 26.0 + ID) % 1.0) - 0.5), 0.32, 0.47)
    ph = (a * 5.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.12 + 0.88 * spokes, 0, 1), "id": ID}


def _f_fiber_bundle(h, w, rng):
    """Dense fine fibres combed along a curl field; crisp so each fibre reads separately."""
    ph = _curl_flow(h, w, rng, 52)
    fine = _hash01(h, w, rng, 2)
    comb = _aa(np.abs(((ph * 90.0 + fine * 0.4) % 1.0) - 0.5), 0.33, 0.47)
    return {"phase": ph, "path": np.clip(0.12 + 0.88 * comb, 0, 1)}


def _f_ember_grid(h, w, rng):
    """Sparse hot cells on a fine lattice, phase radiating from each hot cell."""
    F1, F2, ID = _cellF1F2(h, w, rng, 12)
    hot = (ID > 0.72).astype(np.float32)
    hot = cv2.GaussianBlur(hot, (0, 0), 1.1)
    cells = 1.0 - _aa(F2 - F1, 0.02, 0.16)
    ph = ((F1 * 5.5) + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(cells, _aa(hot, 0.20, 0.65)), 0, 1),
            "id": ID}


def _f_caustic_web(h, w, rng):
    """Pool caustics: three warped sine sheets, product thresholded to crisp filaments."""
    w1 = _smooth(h, w, rng, 40)
    w2 = _smooth(h, w, rng, 26)
    x, y = _xy(h, w)
    s1 = np.sin((x * 72.0) + w1 * 12.0)
    s2 = np.sin((y * 72.0) + w2 * 12.0)
    s3 = np.sin(((x + y) * 66.0) + (w1 + w2) * 8.0)
    web = np.abs(s1 * s2 * s3)
    fil = _aa(web, 0.00, 0.05)                              # only the near-zero crossings survive
    ph = (w1 + w2) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * (1.0 - fil), 0, 1)}


def _f_ratchet(h, w, rng):
    """ASYMMETRIC sawtooth bands per domain -- a deliberately non-symmetric aperture profile.

    Every other flow here uses a symmetric band, which is direction-agnostic. A sawtooth has a
    fast edge and a slow edge, so the sweep crossing it may bias the PERCEIVED direction of
    travel. Untested in sim -- that is exactly what this experiment is for.
    """
    F1, F2, ID = _cellF1F2(h, w, rng, 16)
    x, y = _xy(h, w)
    a = ID * 2.0 * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    saw = (u * 80.0 + ID) % 1.0                             # asymmetric ramp, not abs()
    teeth = _aa(saw, 0.600, 0.645)                          # NARROW window = truly crisp
    return {"phase": saw.astype(np.float32),
            "path": np.clip(0.12 + 0.88 * teeth, 0, 1), "id": ID}


# ------------------------------------------------- batch 5 flows
def _f_creep_hatch(h, w, rng):
    """REPLACEMENT for the parked DoG turing idea: keep 'creeping stripes' but build them from a
    CRISP cross-hatch whose spacing is modulated by a slow field, so the bands appear to creep
    across each other while every edge stays razor sharp."""
    slow = _smooth(h, w, rng, 64)
    x, y = _xy(h, w)
    u = x * 88.0 + slow * 10.0
    v = y * 88.0 - slow * 10.0
    l1 = _aa(np.abs((u % 1.0) - 0.5), 0.44, 0.485)
    l2 = _aa(np.abs((v % 1.0) - 0.5), 0.44, 0.485)
    ph = (slow * 22.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(l1, l2 * 0.9), 0, 1)}


def _f_shear_plates(h, w, rng):
    """Plates that slide: hard domain boundaries, each plate's phase offset from its neighbours."""
    F1, F2, ID = _cellF1F2(h, w, rng, 14)
    edge = 1.0 - _aa(F2 - F1, 0.015, 0.09)
    ph = (ID * 1.0 + F1 * 3.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.16 + 0.84 * np.maximum(edge, 0.35), 0, 1), "id": ID}


def _f_pinstripe_wave(h, w, rng):
    """Crisp fine pinstripes whose SPACING is modulated, so the pitch appears to breathe."""
    mod = _smooth(h, w, rng, 48)
    F1, F2, ID = _cellF1F2(h, w, rng, 16)
    x, y = _xy(h, w)
    a = ID * np.pi
    u = (x * np.cos(a) + y * np.sin(a)) * (78.0 + 26.0 * mod)
    stripe = _aa(np.abs((u % 1.0) - 0.5), 0.43, 0.48)
    ph = (u * 0.16) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * stripe, 0, 1), "id": ID}


def _f_droplet_trail(h, w, rng):
    """Comet droplets: a crisp head with a directional tail, direction set per domain."""
    F1, F2, ID = _cellF1F2(h, w, rng, 13)
    head = 1.0 - _aa(F1, 0.10, 0.30)
    x, y = _xy(h, w)
    a = ID * 2.0 * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    tail = _aa(np.abs(((u * 96.0) % 1.0) - 0.5), 0.40, 0.47) * (1.0 - _aa(F1, 0.25, 0.62))
    ph = (F1 * 6.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(head, tail * 0.8), 0, 1), "id": ID}


def _f_comb_flash(h, w, rng):
    """Lattice cells alternating in phase like a checkerboard -- adjacent cells fire out of step."""
    F1, F2, ID = _cellF1F2(h, w, rng, 12)
    cells = 1.0 - _aa(F2 - F1, 0.02, 0.14)
    alt = np.float32(ID > 0.5) * 0.5
    ph = ((F1 * 5.0) + alt) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.12 + 0.88 * cells, 0, 1), "id": ID}


def _f_filament_knot(h, w, rng):
    """Two curl fields multiplied and cut near zero: knotted filaments that cross themselves."""
    a = _curl_flow(h, w, rng, 44)
    b = _curl_flow(h, w, rng, 29)
    prod = np.sin(a * 6.283) * np.sin(b * 6.283)
    fil = _aa(np.abs(prod), 0.00, 0.06)
    ph = (a + b) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * (1.0 - fil), 0, 1)}


def _f_sand_ripple(h, w, rng):
    """Wind ripples: crisp crest lines on a warped field, crest spacing ~20px."""
    warp = _smooth(h, w, rng, 36)
    x, y = _xy(h, w)
    r = np.sin((x * 70.0 + warp * 14.0) + np.sin(y * 26.0) * 1.2)
    crest = _aa(r, 0.62, 0.70)
    ph = (warp * 18.0) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.12 + 0.88 * crest, 0, 1)}


def _f_prism_split(h, w, rng):
    """Three slightly offset crisp channel gratings -- a colour-separation look that slides."""
    F1, F2, ID = _cellF1F2(h, w, rng, 15)
    x, y = _xy(h, w)
    a = ID * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    g1 = _aa(np.abs(((u * 84.0) % 1.0) - 0.5), 0.42, 0.47)
    g2 = _aa(np.abs((((u + 0.004) * 84.0) % 1.0) - 0.5), 0.42, 0.47)
    g3 = _aa(np.abs((((u + 0.008) * 84.0) % 1.0) - 0.5), 0.42, 0.47)
    ph = (u * 9.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.08 + 0.92 * np.maximum(g1, np.maximum(g2 * 0.8, g3 * 0.6)), 0, 1),
            "id": ID}


def _f_static_burst(h, w, rng):
    """Sparse crisp noise bursts riding a phase gradient -- interference, not sparkle."""
    n = _hash01(h, w, rng, 2)
    clumps = _smooth(h, w, rng, 20)
    burst = _aa(n * (0.35 + 0.65 * clumps), 0.62, 0.66)
    ph = (clumps * 20.0) % 1.0
    return {"phase": ph.astype(np.float32), "path": np.clip(0.10 + 0.90 * burst, 0, 1)}


def _f_gear_teeth(h, w, rng):
    """Radial gear teeth around per-domain hubs: crisp, mechanical, rotationally phased."""
    # Hubs on Worley cell CENTRES, not a floor(x*N) grid: a floor grid is axis-aligned and
    # repeats, which showed as visible square seams on the 1:1 crop and breaks Law A.
    # ONE hub per cell, cell centre JITTERED by a per-cell hash. Removes the axis-aligned
    # regularity that showed as square seams, without collapsing the radial fan (offsetting from
    # the pixel itself did collapse it: path 0.91, 18 steps).
    x, y = _xy(h, w)
    N = 10.0
    jx = _hash01(h, w, rng, max(2, int(h / N)))
    jy = _hash01(h, w, rng, max(2, int(h / N)) + 1)
    cx = (np.floor(x * N) + 0.18 + 0.64 * jx) / N
    cy = (np.floor(y * N) + 0.18 + 0.64 * jy) / N
    dx, dy = x - cx, y - cy
    r = np.sqrt(dx * dx + dy * dy)
    a = np.arctan2(dy, dx) / (2 * np.pi) + 0.5
    teeth = _aa(np.abs(((a * 30.0) % 1.0) - 0.5), 0.30, 0.44)
    ring = _aa(np.abs(r - 0.038), 0.00, 0.016)
    ph = (a * 6.0 + r * 12.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(teeth * (1.0 - ring), ring * 0.9), 0, 1)}


# ------------------------------------------------- batch 6 flows (the flagships)
def _f_double_moire(h, w, rng):
    """Moire on moire: two beats at different scales, structure from the finest carrier.
    The single strongest angle amplifier in the fleet -- two nested beats mean a small angle
    change moves two patterns at different apparent rates."""
    F1, F2, ID = _cellF1F2(h, w, rng, 14)
    x, y = _xy(h, w)
    a1 = ID * 2.0 * np.pi
    a2 = a1 + 0.11
    a3 = a1 + 0.045
    g1 = np.sin((x * np.cos(a1) + y * np.sin(a1)) * 460.0)
    g2 = np.sin((x * np.cos(a2) + y * np.sin(a2)) * 460.0)
    g3 = np.sin((x * np.cos(a3) + y * np.sin(a3)) * 300.0)
    beat = ((g1 * g2) + 1.0) * 0.5
    beat2 = ((g2 * g3) + 1.0) * 0.5
    hatch = np.maximum(_aa((g1 + 1.0) * 0.5, 0.475, 0.515),
                       _aa((g3 + 1.0) * 0.5, 0.475, 0.515) * 0.85)
    dither = _hash01(h, w, rng, 2)
    ph = (beat * 0.6 + beat2 * 0.4) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.06 + 0.94 * hatch * (0.82 + 0.36 * dither), 0, 1), "id": ID}


def _f_vortex_shed(h, w, rng):
    """Karman vortex street: alternating counter-rotating cores shedding off a line."""
    x, y = _xy(h, w)
    acc = np.zeros((h, w), np.float32)
    ph = np.zeros((h, w), np.float32)
    for i in range(9):
        cx = (i + 0.5) / 9.0
        cy = 0.5 + (0.16 if i % 2 == 0 else -0.16)
        dx, dy = x - cx, y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-6
        a = np.arctan2(dy, dx) / (2 * np.pi) + 0.5
        spin = (a * (1.0 if i % 2 == 0 else -1.0) + r * 9.0) % 1.0
        v = 1.0 / (1.0 + 30.0 * r)
        ph = np.where(v > acc, spin, ph)
        acc = np.maximum(acc, v)
    swirl = _aa(np.abs(((ph * 26.0) % 1.0) - 0.5), 0.40, 0.47)
    return {"phase": ph.astype(np.float32), "path": np.clip(0.12 + 0.88 * swirl, 0, 1)}


def _f_chrono_rings(h, w, rng):
    """Nested ring systems at three scales -- rings inside rings, phased independently."""
    x, y = _xy(h, w)
    cx, cy = 0.5, 0.5
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    r1 = _aa(np.abs(((r * 70.0) % 1.0) - 0.5), 0.40, 0.47)
    r2 = _aa(np.abs(((r * 132.0) % 1.0) - 0.5), 0.42, 0.48)
    warp = _smooth(h, w, rng, 40)
    ph = ((r * 70.0) + warp * 3.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(r1, r2 * 0.8), 0, 1)}


def _f_scale_armour(h, w, rng):
    """Overlapping armour scales: crisp lens shapes, each phased from its own hinge."""
    F1, F2, ID = _cellF1F2(h, w, rng, 12)
    lens = 1.0 - _aa(F1, 0.34, 0.52)
    edge = _aa(np.abs(F1 - 0.42), 0.00, 0.05)
    ph = ((F1 * 6.0) + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.12 + 0.88 * np.maximum(lens * 0.55, 1.0 - edge), 0, 1), "id": ID}


def _f_cascade_steps(h, w, rng):
    """Terraced steps at two scales - a literal staircase for the highlight to walk down."""
    slow = _smooth(h, w, rng, 46)
    steps = np.floor(slow * 9.0) / 9.0
    F1, F2, ID = _cellF1F2(h, w, rng, 13)
    riser = _aa(np.abs(F2 - F1), 0.02, 0.09)
    ph = (steps + F1 * 2.4) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.14 + 0.86 * (1.0 - riser), 0, 1), "id": ID}


def _f_plasma_thread(h, w, rng):
    """Hot threads: crisp filaments on a curl field with sparse mirror nodes along them."""
    ph = _curl_flow(h, w, rng, 40)
    fine = _hash01(h, w, rng, 2)
    thread = _aa(np.abs(((ph * 110.0 + fine * 0.35) % 1.0) - 0.5), 0.42, 0.47)
    nodes = (_hash01(h, w, rng, 7) > 0.965).astype(np.float32) * thread
    return {"phase": ph, "path": np.clip(0.10 + 0.90 * np.maximum(thread, nodes), 0, 1)}


def _f_fracture_grid(h, w, rng):
    """Grid that has been broken: crisp orthogonal lines with per-domain offsets and gaps."""
    F1, F2, ID = _cellF1F2(h, w, rng, 15)
    x, y = _xy(h, w)
    ox = np.floor(ID * 7.0) / 7.0 * 0.01
    gx = _aa(np.abs((((x + ox) * 92.0) % 1.0) - 0.5), 0.43, 0.48)
    gy = _aa(np.abs((((y - ox) * 92.0) % 1.0) - 0.5), 0.43, 0.48)
    gap = np.float32(ID > 0.16)
    ph = ((x + y) * 11.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * np.maximum(gx, gy) * gap, 0, 1), "id": ID}


def _f_aurora_curtain(h, w, rng):
    """Curtain folds: crisp vertical-in-domain striations that ripple along their length."""
    F1, F2, ID = _cellF1F2(h, w, rng, 16)
    x, y = _xy(h, w)
    a = ID * 2.0 * np.pi
    u = x * np.cos(a) + y * np.sin(a)
    v = -x * np.sin(a) + y * np.cos(a)
    ripple = np.sin(v * 26.0) * 0.012
    fold = _aa(np.abs((((u + ripple) * 86.0) % 1.0) - 0.5), 0.42, 0.47)
    ph = (v * 7.0 + ID) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.10 + 0.90 * fold, 0, 1), "id": ID}


def _f_singularity_pull(h, w, rng):
    """Everything drawn toward one point: log-spaced crisp rings collapsing inward."""
    x, y = _xy(h, w)
    cx, cy = 0.5, 0.5
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) + 1e-4
    lr = np.log(r + 0.01)
    rings = _aa(np.abs(((lr * 26.0) % 1.0) - 0.5), 0.40, 0.47)
    a = np.arctan2(y - cy, x - cx) / (2 * np.pi) + 0.5
    spokes = _aa(np.abs(((a * 40.0) % 1.0) - 0.5), 0.44, 0.49)
    ph = (lr * 26.0) % 1.0
    return {"phase": ph.astype(np.float32),
            "path": np.clip(0.08 + 0.92 * np.maximum(rings, spokes * 0.7), 0, 1)}


# --------------------------------------------------------------- pilot fleet (batch 1)
#  id                    base RGB         accent RGB       flow           mech      knobs
MOTION_DEFS = OrderedDict([
    ("mo_quicksilver_run", ((16, 22, 30), (196, 216, 236), _f_stream, "M1+M5",
                            dict(bands=18, g_lo=8, g_hi=58, counter=True, ramp=0.35))),
    ("mo_tracer_fire",     ((10, 10, 12), (255, 168, 40), _f_tracer, "M1+M3+M4",
                            dict(bands=22, g_lo=6, g_hi=48, trail=0.55, ramp=0.5, fine=0.22))),
    ("mo_arc_strike",      ((8, 10, 18), (150, 210, 255), _f_bolt, "M1+M3",
                            dict(bands=14, g_lo=5, g_hi=40, trail=0.7, fine=0.16))),
    ("mo_undertow",        ((10, 20, 26), (60, 190, 200), _f_vortex, "M2+M5",
                            dict(bands=16, g_lo=10, g_hi=66, parallax=9, counter=True))),
    ("mo_deep_lacquer",    ((14, 12, 26), (170, 140, 255), _f_ripple, "M2",
                            dict(bands=20, g_lo=8, g_hi=54, parallax=13))),
    ("mo_shatter_drift",   ((18, 16, 16), (235, 96, 60), _f_shatterdomain, "M1+M2",
                            dict(bands=15, g_lo=7, g_hi=52, parallax=7, fine=0.22))),
    ("mo_tide_breather",   ((12, 18, 22), (120, 200, 235), _f_weave, "M6",
                            dict(bands=24, g_lo=11, g_hi=70, graze=0.55))),
    ("mo_swarm_crawl",     ((10, 12, 14), (255, 230, 150), _f_weave, "M7+M1",
                            dict(bands=20, g_lo=9, g_hi=60, lattice=0.9))),

    # ---- batch 2 --------------------------------------------------------------------------
    ("mo_rain_on_glass",   ((12, 16, 20), (150, 205, 225), _f_droplet, "M1+M4",
                            dict(bands=20, g_lo=8, g_hi=56, ramp=0.42))),
    ("mo_moire_engine",    ((14, 14, 18), (220, 230, 255), _f_moire, "M1+M2",
                            dict(bands=26, g_lo=6, g_hi=44, parallax=11))),
    ("mo_ferro_spine",     ((10, 10, 14), (120, 150, 190), _f_ferro, "M1+M7",
                            dict(bands=18, g_lo=7, g_hi=50, lattice=0.55))),
    ("mo_sonic_crack",     ((8, 9, 12), (255, 245, 220), _f_shockring, "M1+M3",
                            dict(bands=12, g_lo=5, g_hi=38, trail=0.62))),
    ("mo_heat_mirage",     ((16, 14, 12), (255, 190, 120), _f_turbulence, "M5+M4",
                            dict(bands=22, g_lo=10, g_hi=68, counter=True, ramp=0.5))),
    ("mo_vein_pulse",      ((12, 10, 14), (230, 70, 90), _f_capillary, "M1+M3",
                            dict(bands=16, g_lo=6, g_hi=46, trail=0.48))),
    ("mo_scale_cascade",   ((14, 16, 14), (170, 220, 180), _f_lamella, "M1+M2",
                            dict(bands=20, g_lo=8, g_hi=54, parallax=6))),
    ("mo_spark_shower",    ((10, 10, 12), (255, 210, 120), _f_sparkshower, "M7+M3",
                            dict(bands=18, g_lo=5, g_hi=42, lattice=0.8, trail=0.4))),

    # ---- batch 3 --------------------------------------------------------------------------
    ("mo_herringbone_run", ((12, 14, 18), (200, 214, 235), _f_chevron_domains, "M1+M2",
                            dict(bands=22, g_lo=7, g_hi=50, parallax=8))),
    ("mo_hive_pulse",      ((14, 16, 12), (255, 206, 86), _f_hex_chase, "M1+M4",
                            dict(bands=24, g_lo=6, g_hi=46, ramp=0.44))),
    ("mo_impact_star",     ((10, 12, 16), (236, 244, 255), _f_crack_impact, "M1+M3",
                            dict(bands=14, g_lo=5, g_hi=40, trail=0.66))),
    ("mo_loom_drift",      ((16, 12, 14), (198, 150, 255), _f_thread_cross, "M2+M1",
                            dict(bands=20, g_lo=8, g_hi=52, parallax=12))),
    ("mo_foam_travel",     ((10, 18, 22), (170, 235, 240), _f_bubble_rim, "M1+M5",
                            dict(bands=20, g_lo=9, g_hi=58, counter=True))),
    ("mo_breakdown_arc",   ((8, 8, 14), (140, 200, 255), _f_lichtenberg, "M1+M3",
                            dict(bands=16, g_lo=5, g_hi=42, trail=0.32, graze=0.42))),
    ("mo_signal_tear",     ((12, 12, 16), (255, 96, 180), _f_glitch_slivers, "M1+M7",
                            dict(bands=26, g_lo=6, g_hi=44, lattice=0.6))),
    ("mo_marble_current",  ((16, 14, 12), (222, 196, 140), _f_marble_vein, "M2+M6",
                            dict(bands=18, g_lo=9, g_hi=60, parallax=9, graze=0.4))),

    # ---- batch 4 --------------------------------------------------------------------------
    ("mo_spiral_wake",     ((10, 14, 20), (140, 190, 255), _f_spiral_arms, "M1+M4",
                            dict(bands=20, g_lo=7, g_hi=52, ramp=0.46))),
    ("mo_mercury_merge",   ((14, 16, 20), (210, 220, 232), _f_coalesce, "M2+M5",
                            dict(bands=18, g_lo=8, g_hi=56, parallax=10, counter=True, graze=0.34))),
    # PARKED 2026-08-10: feature-scale ceiling 0.189 vs the 0.19 approved-fleet floor. A
    # difference-of-gaussians is smooth by construction and cannot carry sub-3px energy; six
    # attempts (noise cell, threshold width, edge dither, phase freq, band count) plateaued.
    # Needs rebuilding from a CRISP primitive, not retuning. See _motion_lab/park_turing.py.
    # ("mo_turing_creep",    ((12, 18, 16), (120, 235, 190), _f_turing_stripe, "M1",
    #                         dict(bands=44, g_lo=6, g_hi=44))),
    ("mo_shatter_fan",     ((18, 14, 18), (255, 150, 90), _f_shard_fan, "M1+M2",
                            dict(bands=22, g_lo=7, g_hi=50, parallax=7))),
    ("mo_fiber_optic",     ((10, 12, 18), (90, 220, 255), _f_fiber_bundle, "M1+M3",
                            dict(bands=24, g_lo=5, g_hi=42, trail=0.34))),
    ("mo_ember_bed",       ((16, 10, 8), (255, 130, 40), _f_ember_grid, "M1+M7",
                            dict(bands=20, g_lo=6, g_hi=48, lattice=0.7))),
    ("mo_caustic_pool",    ((8, 16, 22), (150, 240, 235), _f_caustic_web, "M1+M5",
                            dict(bands=22, g_lo=7, g_hi=54, counter=True))),
    ("mo_ratchet_drive",   ((14, 14, 14), (235, 210, 120), _f_ratchet, "M1+M4",
                            dict(bands=20, g_lo=6, g_hi=50, ramp=0.5))),

    # ---- batch 5 --------------------------------------------------------------------------
    ("mo_creep_hatch",     ((12, 18, 16), (120, 235, 190), _f_creep_hatch, "M1+M2",
                            dict(bands=28, g_lo=6, g_hi=44, parallax=7))),
    ("mo_shear_plates",    ((16, 16, 20), (190, 200, 220), _f_shear_plates, "M2+M1",
                            dict(bands=22, g_lo=8, g_hi=54, parallax=11))),
    ("mo_pinstripe_wave",  ((14, 12, 16), (240, 225, 190), _f_pinstripe_wave, "M1+M4",
                            dict(bands=30, g_lo=6, g_hi=46, ramp=0.42, graze=0.48))),
    ("mo_comet_shed",      ((10, 12, 18), (255, 235, 190), _f_droplet_trail, "M1+M3",
                            dict(bands=24, g_lo=6, g_hi=46, trail=0.42))),
    ("mo_comb_flash",      ((12, 14, 12), (200, 255, 140), _f_comb_flash, "M1+M5",
                            dict(bands=26, g_lo=7, g_hi=50, counter=True))),
    ("mo_knot_current",    ((14, 10, 18), (180, 120, 255), _f_filament_knot, "M1+M2",
                            dict(bands=24, g_lo=6, g_hi=48, parallax=9))),
    ("mo_dune_drift",      ((18, 16, 12), (230, 200, 150), _f_sand_ripple, "M1+M6",
                            dict(bands=26, g_lo=8, g_hi=56, graze=0.42))),
    ("mo_prism_slide",     ((12, 12, 14), (255, 170, 220), _f_prism_split, "M2+M3",
                            dict(bands=28, g_lo=6, g_hi=44, parallax=13, trail=0.3))),
    ("mo_interference",    ((10, 14, 16), (170, 220, 255), _f_static_burst, "M7+M1",
                            dict(bands=26, g_lo=5, g_hi=42, lattice=0.5))),
    ("mo_gearworks",       ((16, 14, 10), (215, 185, 120), _f_gear_teeth, "M1+M4",
                            dict(bands=24, g_lo=7, g_hi=52, ramp=0.4))),

    # ---- batch 6: the flagships -------------------------------------------------------------
    ("mo_double_moire",    ((12, 12, 16), (232, 240, 255), _f_double_moire, "M1+M2+M3",
                            dict(bands=30, g_lo=5, g_hi=42, parallax=15, trail=0.28))),
    ("mo_vortex_street",   ((10, 16, 20), (110, 210, 225), _f_vortex_shed, "M1+M5+M4",
                            dict(bands=24, g_lo=7, g_hi=52, counter=True, ramp=0.44))),
    ("mo_chrono_rings",    ((14, 12, 18), (200, 180, 255), _f_chrono_rings, "M1+M2+M6",
                            dict(bands=28, g_lo=6, g_hi=46, parallax=10, graze=0.36))),
    ("mo_scale_armour",    ((16, 16, 14), (185, 200, 165), _f_scale_armour, "M1+M2",
                            dict(bands=22, g_lo=8, g_hi=54, parallax=8))),
    ("mo_cascade_steps",   ((12, 14, 20), (170, 205, 245), _f_cascade_steps, "M1+M4",
                            dict(bands=26, g_lo=7, g_hi=50, ramp=0.5))),
    ("mo_plasma_thread",   ((10, 10, 16), (255, 120, 240), _f_plasma_thread, "M1+M7+M3",
                            dict(bands=26, g_lo=5, g_hi=44, lattice=0.6, trail=0.3, graze=0.3))),
    ("mo_fracture_grid",   ((14, 14, 14), (245, 235, 210), _f_fracture_grid, "M1+M2",
                            dict(bands=24, g_lo=6, g_hi=48, parallax=12, graze=0.32))),
    ("mo_aurora_curtain",  ((10, 14, 18), (140, 255, 210), _f_aurora_curtain, "M1+M6",
                            dict(bands=28, g_lo=7, g_hi=52, graze=0.5))),
    ("mo_singularity_pull",((8, 8, 12), (255, 200, 90), _f_singularity_pull, "M1+M4+M3",
                            dict(bands=30, g_lo=5, g_hi=44, ramp=0.52, trail=0.32))),
])


# ---------------------------------------------------------------- display metadata
# SINGLE SOURCE OF TRUTH for the picker rows. js/spb-motion-lab.js is GENERATED from this by
# emit_js_defs() -- edit here, never the JS, or the two drift (the nightshift wave-2 lesson).
# Every description names the MOTION to look for, because the owner's verdict happens in sim and
# "which mechanism worked" is the only feedback that transfers to the next finish.
MOTION_META = {
    "mo_quicksilver_run": ("Quicksilver Run",
        "Liquid-metal braids that CHURN instead of sliding - two interleaved populations light on "
        "opposite edges of the sweep. Watch the surface boil as the car turns.", "#c4d8ec"),
    "mo_tracer_fire": ("Tracer Fire",
        "Thin filament cores that snap past with a WHITE-HOT tip - the highlight changes colour as "
        "it travels, and an aperture ramp makes it read as accelerating.", "#ffa828"),
    "mo_arc_strike": ("Arc Strike",
        "Branching discharge paths whose strike point flares white while the branches stay blue. "
        "A bolt that lands somewhere new every time the light moves.", "#96d2ff"),
    "mo_undertow": ("Undertow",
        "Spiral arms with the clearcoat lobe OFFSET from the metal one, so two highlights slide "
        "past each other. The strongest depth cue in the set - it looks layered.", "#3cbec8"),
    "mo_deep_lacquer": ("Deep Lacquer",
        "Concentric interference under a crazed net, base and clearcoat displaced 13px. Reads like "
        "something suspended below the surface rather than painted on it.", "#aa8cff"),
    "mo_shatter_drift": ("Shatter Drift",
        "Every shard domain carries its OWN phase, so the pulse crosses each one out of step with "
        "its neighbours. Chaotic travel that never repeats across the body.", "#eb603c"),
    "mo_tide_breather": ("Tide Breather",
        "A slow, whole-car wave: the clearcoat band migrates across panels with the grazing angle "
        "while fine woven bands shimmer underneath. Breathing, not racing.", "#78c8eb"),
    "mo_swarm_crawl": ("Swarm Crawl",
        "Sparse near-mirror points on a phase-gradient lattice - the sparkle POPULATION migrates "
        "along a direction instead of twinkling at random. Crawling glitter.", "#ffe696"),
    "mo_rain_on_glass": ("Rain on Glass",
        "Expanding ring systems from nine impacts, nearest one wins. The chase runs OUTWARD from "
        "each strike and slows as it spreads.", "#96cde1"),
    "mo_moire_engine": ("Moire Engine",
        "Two crisp grids at a slight relative rotation. The beat pattern shifts FAR more than the "
        "angle change that caused it - the biggest amplifier in the category. Test this one first.",
        "#dce6ff"),
    "mo_ferro_spine": ("Ferro Spine",
        "Cusped ferrofluid spikes from scattered magnetic poles, with mirror flecks riding the "
        "ridges. Bristling metal that seems to stand up as you pass.", "#7896be"),
    "mo_sonic_crack": ("Sonic Crack",
        "A FEW hard-edged shells expanding through mostly-empty dark, each with a white leading "
        "edge. Not a shimmer - a crack.", "#fff5dc"),
    "mo_heat_mirage": ("Heat Mirage",
        "Two curl scales stacked so the fine flow is dragged by the coarse one, populations "
        "counter-running. Air above hot tarmac.", "#ffbe78"),
    "mo_vein_pulse": ("Vein Pulse",
        "Sharpened branching veins carrying a pulse that goes white at the branch points. "
        "Something circulating under the paint.", "#e6465a"),
    "mo_scale_cascade": ("Scale Cascade",
        "Overlapping plates, each with phase running out from its own centre, clearcoat offset 6px. "
        "The cascade crosses plate to plate like scales lifting.", "#aadcb4"),
    "mo_herringbone_run": ("Herringbone Run",
        "Chevron weave where every domain picks its own angle, base and clearcoat offset 8px. The "
        "zig-zag appears to run along itself as the light crosses it.", "#c8d6eb"),
    "mo_hive_pulse": ("Hive Pulse",
        "Tight hex cells with the pulse running outward from each centre and an aperture ramp - the "
        "comb lights up cell by cell, quicker toward the edges.", "#ffce56"),
    "mo_impact_star": ("Impact Star",
        "Thin cracks radiating from three strike points, white-hot at the impact itself. A "
        "windscreen the instant it goes.", "#ecf4ff"),
    "mo_loom_drift": ("Loom Drift",
        "Two crossed thread sets at per-domain angles with a 12px clearcoat offset, so the weave "
        "seems to slide over itself. The deepest-looking one in the set.", "#c696ff"),
    "mo_foam_travel": ("Foam Travel",
        "Phase living only on the cell rims with populations counter-running: foam that churns and "
        "travels at once.", "#aaebf0"),
    "mo_breakdown_arc": ("Breakdown Arc",
        "Dielectric breakdown grown from sparse seeds - branching veins with a white leading tip. "
        "Electricity finding a path through the paint.", "#8cc8ff"),
    "mo_signal_tear": ("Signal Tear",
        "Crisp tearing slivers, direction per domain so it never reads as stripes, with mirror "
        "flecks strobing between them. Broadcast failure at speed.", "#ff60b4"),
    "mo_marble_current": ("Marble Current",
        "Domain-warped seams with the grazing band migrating across panels - stone that flows "
        "slowly instead of shimmering.", "#dec48c"),
    "mo_spiral_wake": ("Spiral Wake",
        "Log-spiral arms from four cores with an aperture ramp, so the pulse runs outward and slows "
        "as the arms widen. A wake opening up behind you.", "#8cbeff"),
    "mo_mercury_merge": ("Mercury Merge",
        "Droplets caught mid-merge, phase living on the join rims, populations counter-running with "
        "a 10px clearcoat offset. Liquid metal deciding whether to be one thing or two.", "#d2dce8"),
    "mo_shatter_fan": ("Shatter Fan",
        "Crisp radial spokes, a separate fan per domain, clearcoat offset 7px. Light rakes across "
        "the spokes and the fan seems to rotate.", "#ff965a"),
    "mo_fiber_optic": ("Fiber Optic",
        "Dense fine fibres combed along a flow field, each carrying a travelling glint that goes "
        "white at the tip. A bundle of lit filaments.", "#5adcff"),
    "mo_ember_bed": ("Ember Bed",
        "A fine cell lattice with scattered hot cells and mirror flecks between them - coals where "
        "the glow moves around rather than sitting still.", "#ff8228"),
    "mo_caustic_pool": ("Caustic Pool",
        "Three warped sheets multiplied and cut to near-zero filaments: the caustic web you see on "
        "a pool floor, churning as the surface moves.", "#96f0eb"),
    "mo_ratchet_drive": ("Ratchet Drive",
        "The experiment: an ASYMMETRIC sawtooth aperture instead of a symmetric band. A fast edge "
        "and a slow edge may bias which way the motion appears to run. Tell me if it has a "
        "direction.", "#ebd278"),
    "mo_creep_hatch": ("Creep Hatch",
        "Razor cross-hatch whose spacing is modulated by a slow field, so the bands appear to creep "
        "across one another while every edge stays sharp.", "#78ebbe"),
    "mo_shear_plates": ("Shear Plates",
        "Hard-edged plates each phased differently from its neighbours, clearcoat offset 11px - the "
        "surface looks like it is sliding against itself.", "#bec8dc"),
    "mo_pinstripe_wave": ("Pinstripe Wave",
        "Fine pinstripes whose PITCH breathes across the body, with an aperture ramp so the travel "
        "speeds up where they tighten.", "#f0e1be"),
    "mo_comet_shed": ("Comet Shed",
        "Crisp droplet heads with directional tails, direction per domain, tips flashing white. "
        "Debris shedding off the bodywork.", "#ffebbe"),
    "mo_comb_flash": ("Comb Flash",
        "Lattice cells alternating in phase like a checkerboard with counter-running populations - "
        "adjacent cells fire out of step and the whole comb seems to ripple.", "#c8ff8c"),
    "mo_knot_current": ("Knot Current",
        "Two flow fields multiplied and cut near zero: knotted filaments that cross themselves, "
        "clearcoat offset 9px so the crossings gain depth.", "#b478ff"),
    "mo_dune_drift": ("Dune Drift",
        "Crisp wind-ripple crests with the grazing band migrating across panels - sand that drifts "
        "slowly rather than shimmering.", "#e6c896"),
    "mo_prism_slide": ("Prism Slide",
        "Three slightly offset gratings with a 13px clearcoat displacement and a white tip: colour "
        "separation that slides apart as the angle changes.", "#ffaadc"),
    "mo_interference": ("Interference",
        "Sparse crisp bursts riding a phase gradient with mirror flecks between them. Reads as "
        "interference rather than glitter.", "#aadcff"),
    "mo_gearworks": ("Gearworks",
        "Radial gear teeth around per-domain hubs with a ramp, so the teeth appear to rotate at "
        "different rates across the car. Mechanical, deliberate.", "#d7b978"),
    "mo_double_moire": ("Double Moire",
        "THE FLAGSHIP. Two nested beats at different scales over a crisp cross-hatch, plus a white "
        "tip. A small change of angle moves two patterns at different apparent rates - the strongest "
        "amplifier in the whole category. Test this one first.", "#e8f0ff"),
    "mo_vortex_street": ("Vortex Street",
        "A Karman vortex street: nine alternating counter-rotating cores shedding off a line, with "
        "counter-running populations and a ramp. Turbulence you can see the rhythm of.", "#6ed2e1"),
    "mo_chrono_rings": ("Chrono Rings",
        "Ring systems at two scales, clearcoat offset 10px, grazing band migrating - rings inside "
        "rings, each keeping its own time.", "#c8b4ff"),
    "mo_scale_armour": ("Scale Armour",
        "Crisp overlapping lens plates, each phased from its own hinge, clearcoat offset 8px. Plate "
        "armour lifting as the light rakes across it.", "#b9c8a5"),
    "mo_cascade_steps": ("Cascade Steps",
        "Terraced steps at two scales with a strong ramp - a literal staircase for the highlight to "
        "walk down, accelerating as it goes.", "#aacdf5"),
    "mo_plasma_thread": ("Plasma Thread",
        "Hot crisp filaments on a flow field with sparse mirror nodes burning along them and white "
        "tips. Current finding its way through the paint.", "#ff78f0"),
    "mo_fracture_grid": ("Fracture Grid",
        "An orthogonal grid that has been broken - per-domain offsets and missing spans, clearcoat "
        "displaced 12px. Order coming apart at speed.", "#f5ebd2"),
    "mo_aurora_curtain": ("Aurora Curtain",
        "Crisp striated folds that ripple along their own length while the grazing band sweeps the "
        "body. Curtains of light, whole-car scale.", "#8cffd2"),
    "mo_singularity_pull": ("Singularity Pull",
        "Log-spaced rings and spokes collapsing toward one point, with the strongest ramp in the "
        "fleet so the pulse accelerates inward. Everything gets pulled in.", "#ffc85a"),
    "mo_spark_shower": ("Spark Shower",
        "Sparse hot points with comet trails on a spiral phase - the lit population migrates and "
        "the tips flash white. Grinder sparks, frozen mid-arc.", "#ffd278"),
}


def emit_js_defs():
    """Print the JS DEFS rows for js/spb-motion-lab.js. Regenerate after adding finishes:
        py -3 -c "import sys;sys.path.insert(0,'.');from engine.expansions.motion_lab_2026 import emit_js_defs;emit_js_defs()"
    """
    for fid in MOTION_DEFS:
        name, desc, sw = MOTION_META.get(fid, (fid, "", "#888888"))
        mech = MOTION_DEFS[fid][3]
        d = desc.replace("'", "\'")
        print("        ['%s', '%s', '%s', '%s', '%s']," % (fid, name, d, sw, mech))


def install_into_engine(mono_reg, base_reg=None):
    n = 0
    for fid, (base, acc, flow, mech, kw) in MOTION_DEFS.items():
        mono_reg[fid] = _make_motion(fid, base, acc, flow, mech, **kw)
        n += 1
    try:
        import engine.expansions.fusions as _fus
        for fid in MOTION_DEFS:
            _fus.FUSION_REGISTRY[fid] = mono_reg[fid]
    except Exception:
        pass
    return "motion-lab: %d apparent-motion experiments registered" % n


def mechanism_of(fid):
    """So an in-sim verdict maps back to a MECHANISM, not just one finish."""
    d = MOTION_DEFS.get(fid)
    return d[3] if d else ""
