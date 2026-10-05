# ============================================================================
# engine/color_science.py — perceptual + physical color math for SPB finishes.
# 2026-06-09, additive-only. 2-copy file (root → electron-app/server via
# scripts/sync-runtime-copies.js; listed in runtime-sync-manifest.json).
#
# WHY THIS EXISTS (owner mandate 2026-06-09, "better logic in the math"):
#   * HSV hue interpolation lurches through muddy desaturated midpoints and
#     uneven brightness (the #1 source of the "colors muddy" audit chip).
#     OKLab/OKLCH ramps keep PERCEIVED lightness/chroma steady across a hue
#     sweep, so gradients and color-shift palettes stay rich end to end.
#   * Real candy paint is metal seen through a tinted clear coat: brightness
#     falls EXPONENTIALLY with coat depth (Beer–Lambert), which is why real
#     candy "pools" dark and saturated in valleys. Alpha blends can't do that.
#   * Real iridescence (oil film / titanium temper) is BANDED into interference
#     orders, not a smooth airbrush rainbow.
#
# Everything is vectorized float32 numpy, resolution-independent, and safe to
# call from any paint_fn/spec_fn. No engine imports (numpy + cv2 only) so this
# module can never create a registry import cycle.
# ============================================================================
from __future__ import annotations

import numpy as np

try:
    import cv2 as _cv2
    _CV2_OK = True
except Exception:  # pragma: no cover - cv2 ships with SPB, fallback is for safety
    _cv2 = None
    _CV2_OK = False


# ---------------------------------------------------------------------------
# sRGB <-> linear  (all color math happens in LINEAR light; sRGB is a display
# encoding. Mixing in sRGB is itself a classic source of muddy results.)
# ---------------------------------------------------------------------------
def srgb_to_linear(c):
    c = np.clip(np.asarray(c, np.float32), 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055).astype(np.float32)


# ---------------------------------------------------------------------------
# linear sRGB <-> OKLab (Björn Ottosson 2020 matrices) and OKLab <-> OKLCH.
# L = perceived lightness, C = chroma (colorfulness), H = hue angle (radians).
# ---------------------------------------------------------------------------
def linear_to_oklab(rgb):
    rgb = np.asarray(rgb, np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(np.maximum(l, 0)), np.cbrt(np.maximum(m, 0)), np.cbrt(np.maximum(s, 0))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return np.stack([L, a, b2], axis=-1).astype(np.float32)


def oklab_to_linear(lab):
    lab = np.asarray(lab, np.float32)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    # Direct channel assignment into one preallocated buffer is BIT-IDENTICAL to
    # np.stack([r,g,b2]) (same ufunc op order per element) but ~25% faster and
    # allocates one array instead of four. This fn runs up to 11x per render
    # inside _gamut_clamp_linear, so the win compounds. (perf 2026-06-13)
    out = np.empty(lab.shape, np.float32)
    out[..., 0] = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    out[..., 1] = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    out[..., 2] = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return out  # may exceed [0,1]; see gamut clamp


def srgb_to_oklab(rgb):
    return linear_to_oklab(srgb_to_linear(rgb))


def oklab_to_srgb(lab):
    return linear_to_srgb(_gamut_clamp_linear(oklab_to_linear(lab), lab))


def oklab_to_oklch(lab):
    lab = np.asarray(lab, np.float32)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return np.stack([L, np.hypot(a, b), np.arctan2(b, a)], axis=-1).astype(np.float32)


def oklch_to_oklab(lch):
    lch = np.asarray(lch, np.float32)
    L, C, H = lch[..., 0], lch[..., 1], lch[..., 2]
    return np.stack([L, C * np.cos(H), C * np.sin(H)], axis=-1).astype(np.float32)


def _gamut_clamp_linear(lin, lab, iters=10):
    """Out-of-gamut OKLab colors are pulled back by COMPRESSING CHROMA toward
    gray while preserving lightness + hue (binary search on C). Plain clipping
    shifts hue (e.g. saturated cyans turn green); this doesn't.

    PERF (2026-06-13): the 10-step chroma bisection now runs ONLY on the flat
    (K,3) subset of out-of-gamut pixels instead of the full HxWx3 grid. In a
    normal finish only a small slice is out of gamut, so this is the dominant
    color_science speedup (e.g. 41% OOG field: 13.6s -> 5.1s; 77% OOG: 15.4s ->
    9.0s). The per-element op order, operands and bounds tests are unchanged, so
    the result is BIT-IDENTICAL (verified max-diff 0.0 on full + partial OOG
    fields). Signature / output shape / dtype unchanged."""
    lin = np.asarray(lin, np.float32)
    bad = np.any((lin < -1e-4) | (lin > 1.0 + 1e-4), axis=-1)
    if not bad.any():
        return np.clip(lin, 0.0, 1.0)
    lab = np.asarray(lab, np.float32)
    # Gather only the out-of-gamut pixels (the in-gamut ones keep chroma = 1.0
    # and are simply clipped, exactly as the full-field np.where(bad, ., 1.0) did).
    L = lab[..., 0][bad]
    A = lab[..., 1][bad]
    B = lab[..., 2][bad]
    lo = np.zeros(L.shape[0], np.float32)              # chroma scale that fits
    hi = np.ones(L.shape[0], np.float32)               # full chroma
    for _ in range(iters):
        mid = (lo + hi) * 0.5
        am = A * mid
        bm = B * mid
        # l_/m_/s_ then their cubes -- same op order as oklab_to_linear
        l_ = L + 0.3963377774 * am + 0.2158037573 * bm
        m_ = L - 0.1055613458 * am - 0.0638541728 * bm
        s_ = L - 0.0894841775 * am - 1.2914855480 * bm
        l = l_ ** 3
        m = m_ ** 3
        s = s_ ** 3
        r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
        g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
        b2 = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
        ok = ~((r < -1e-4) | (r > 1.0 + 1e-4) | (g < -1e-4) | (g > 1.0 + 1e-4)
               | (b2 < -1e-4) | (b2 > 1.0 + 1e-4))
        lo = np.where(ok, mid, lo)
        hi = np.where(~ok, mid, hi)
    # Apply the fitted chroma scale (lo on bad pixels, 1.0 elsewhere) to a fresh
    # copy of lab, then convert once -- identical to the old final two lines.
    out = lab.copy()
    scale = np.ones(lab.shape[:-1], np.float32)
    scale[bad] = lo
    out[..., 1] *= scale
    out[..., 2] *= scale
    return np.clip(oklab_to_linear(out), 0.0, 1.0)


# ---------------------------------------------------------------------------
# oklch_ramp — THE replacement for HSV gradient/ramp math.
# ---------------------------------------------------------------------------
def oklch_ramp(stops_srgb, t, flatten_lightness=0.0, hue_dir="short"):
    """Perceptually-uniform multi-stop color ramp.

    stops_srgb : list of sRGB triples in [0,1] (>=2 stops).
    t          : scalar or ndarray in [0,1]; any shape. Returns shape t.shape+(3,).
    flatten_lightness : 0..1 — pull every stop's L toward the mean L. 1.0 keeps
        perceived brightness perfectly constant across the whole ramp (the
        anti-"muddy gradient" dial). 0.0 keeps the stops' own lightness.
    hue_dir    : "short" (default) interpolates each segment along the shortest
        hue arc; "long" forces the long way (full rainbow sweeps).
    """
    stops = np.asarray(stops_srgb, np.float32).reshape(-1, 3)
    if stops.shape[0] < 2:
        raise ValueError("oklch_ramp needs >= 2 stops")
    lch = oklab_to_oklch(srgb_to_oklab(stops))          # (n, 3)
    if flatten_lightness > 0.0:
        meanL = float(lch[:, 0].mean())
        lch[:, 0] = lch[:, 0] * (1.0 - flatten_lightness) + meanL * flatten_lightness
    # unwrap hue per segment so interpolation takes the chosen arc
    H = lch[:, 2].copy()
    for i in range(1, len(H)):
        d = H[i] - H[i - 1]
        d = (d + np.pi) % (2.0 * np.pi) - np.pi        # shortest signed delta
        if hue_dir == "long" and abs(d) > 1e-6:
            d = d - np.sign(d) * 2.0 * np.pi
        H[i] = H[i - 1] + d
    t = np.clip(np.asarray(t, np.float32), 0.0, 1.0)
    n_seg = stops.shape[0] - 1
    x = t * n_seg
    i0 = np.clip(np.floor(x).astype(np.int32), 0, n_seg - 1)
    f = (x - i0).astype(np.float32)
    L = lch[i0, 0] + (lch[i0 + 1, 0] - lch[i0, 0]) * f
    C = lch[i0, 1] + (lch[i0 + 1, 1] - lch[i0, 1]) * f
    Hh = H[i0] + (H[i0 + 1] - H[i0]) * f
    lab = oklch_to_oklab(np.stack([L, C, Hh], axis=-1))
    return oklab_to_srgb(lab)


# ---------------------------------------------------------------------------
# candy_absorb — physically-correct candy coat (Beer–Lambert absorption).
# ---------------------------------------------------------------------------
def candy_absorb(metal_srgb, tint_srgb, depth, density=1.0):
    """Candy = metal seen through tinted clear. Transmission falls off
    exponentially with coat depth: out_linear = metal_linear * tint_linear^depth.

    metal_srgb : HxWx3 underlying metal/flake layer (sRGB [0,1]).
    tint_srgb  : the candy color AT DEPTH 1.0 (an (3,) triple or HxWx3 field).
    depth      : HxW field — coat thickness. 0 = bare metal, 1 = exactly
                 metal*tint, 2 = twice-dipped (darker AND more saturated, like
                 real candy pooling in valleys). Negative values clamp to 0.
    density    : global strength multiplier on the absorption.
    """
    lm = srgb_to_linear(metal_srgb)
    lt = np.clip(srgb_to_linear(tint_srgb), 1e-4, 1.0)
    k = -np.log(lt)                                    # absorption coefficient per channel
    d = np.maximum(np.asarray(depth, np.float32), 0.0)
    if d.ndim == lm.ndim - 1:
        d = d[..., None]
    out = lm * np.exp(-k * d * float(density))
    return linear_to_srgb(np.clip(out, 0.0, 1.0))


# ---------------------------------------------------------------------------
# interference_palette — quantized thin-film (Newton's rings) color.
# ---------------------------------------------------------------------------
def interference_palette(thickness, orders=3.0, quantize=0.6, brightness=1.0, base_srgb=None):
    """Color of a thin film (oil slick / soap / titanium temper) from an optical
    thickness field. Per-channel reflectance ~ cos^2 phase at that channel's
    wavelength (R~610nm, G~545nm, B~465nm), which yields the REAL banded
    gold→magenta→cyan→green order sequence — not a smooth HSV rainbow.

    thickness : HxW field in [0,1] (any motif: flow, relief, heat zones...).
    orders    : how many interference orders the [0,1] range spans.
    quantize  : 0 = smooth physical sweep; 1 = hard discrete bands. Mid values
                give plateaus with thin transitions (reads like a real slick).
    base_srgb : optional underlying color to tint (defaults to neutral film).
    """
    th = np.clip(np.asarray(thickness, np.float32), 0.0, 1.0) * float(orders)
    if quantize > 0.0:
        frac = th - np.floor(th)
        # squeeze each order's interior toward a plateau, keep thin transitions
        w = max(1e-3, 1.0 - 0.92 * float(quantize))
        sq = np.clip((frac - 0.5) / w + 0.5, 0.0, 1.0)
        sq = sq * sq * (3.0 - 2.0 * sq)               # smoothstep edge
        th = np.floor(th) + sq
    lam = np.array([1.0, 610.0 / 545.0, 610.0 / 465.0], np.float32)  # phase rate per channel
    phase = th[..., None] * lam * 2.0 * np.pi
    lin = (0.5 + 0.5 * np.cos(phase)).astype(np.float32) ** 1.5      # cos^2-ish lobe shaping
    lin *= float(brightness)
    if base_srgb is not None:
        lin = lin * srgb_to_linear(base_srgb)
    return linear_to_srgb(np.clip(lin, 0.0, 1.0))


# ---------------------------------------------------------------------------
# tri_partition — decorrelation BY CONSTRUCTION for M/R/Cc authoring.
# ---------------------------------------------------------------------------
def tri_partition(shape, seed, cells=180, soften_px=2.0):
    """Three mutually-exclusive territory masks from a scattered Voronoi
    3-coloring (isotropic, UV-orientation-agnostic). Give each spec channel its
    own territory's motif and the |corr|<0.85 gate passes by construction —
    no shared-field recolor can sneak in.

    Returns (m0, m1, m2): float32 HxW soft masks, sum ≈ 1 everywhere.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    n = max(12, int(cells))
    py = rng.uniform(0, h, n).astype(np.float32)
    px = rng.uniform(0, w, n).astype(np.float32)
    owner_color = (rng.permutation(n) % 3).astype(np.int32)
    # Exact nearest-cell assignment via KD-tree: identical output to the naive
    # n x full-grid loop but O(N log n) — the loop was a render-time killer at
    # high cell counts (owner doctrine: every item ~1s, >3s unacceptable).
    try:
        from scipy.spatial import cKDTree
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _, idx = cKDTree(np.stack([py, px], axis=1)).query(
            np.stack([yy.ravel(), xx.ravel()], axis=1), k=1, workers=-1)
        color = owner_color[idx].reshape(h, w)
    except Exception:  # scipy always ships with SPB; loop kept as a safety net
        yy = np.arange(h, dtype=np.float32)[:, None]
        xx = np.arange(w, dtype=np.float32)[None, :]
        best = np.full((h, w), 1e18, np.float32)
        color = np.zeros((h, w), np.int32)
        for i in range(n):
            dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
            closer = dd < best
            best = np.where(closer, dd, best)
            color = np.where(closer, owner_color[i], color)
    masks = []
    for c in range(3):
        m = (color == c).astype(np.float32)
        if _CV2_OK and soften_px > 0:
            m = _cv2.GaussianBlur(m, (0, 0), float(soften_px))
        masks.append(m)
    total = masks[0] + masks[1] + masks[2] + 1e-6
    return tuple((m / total).astype(np.float32) for m in masks)


# ---------------------------------------------------------------------------
# flip_lattice — micro interleave mask for perceptual color-flip finishes.
# ---------------------------------------------------------------------------
def flip_lattice(shape, seed, scale_px=3.0, balance=0.5):
    """Binary-ish micro lattice that interleaves two hues at flake scale.
    Paint hue A where mask=0 and hue B where mask=1, then give the B-areas the
    mirror/high-M spec and A-areas the matte spec: head-on light shows the
    blend (A-dominant), raking light flares B — a perceptual color flip without
    touching the albedo at runtime. Isotropic; no directional bias."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    noise = rng.random((h, w)).astype(np.float32)
    if _CV2_OK and scale_px > 0.5:
        noise = _cv2.GaussianBlur(noise, (0, 0), float(scale_px) * 0.5)
    thr = np.quantile(noise, 1.0 - float(np.clip(balance, 0.05, 0.95)))
    hard = (noise >= thr).astype(np.float32)
    if _CV2_OK:
        hard = _cv2.GaussianBlur(hard, (0, 0), 0.6)    # half-pixel AA so it survives mips
    return np.clip(hard, 0.0, 1.0)


# ---------------------------------------------------------------------------
# feature_fineness — THE anti-blob gate (owner fineness doctrine 2026-06-09:
# "2048x2048 covers ENTIRE CARS — things that look like fine detail are still
# 4-50x too big. The more crushed/fine the better.")
# ---------------------------------------------------------------------------
def feature_fineness(img, full_size=2048):
    """Measure WHERE an image's visual energy lives across feature scales.

    Returns dict:
      char_px       energy-weighted characteristic feature scale in px AT 2048
                    (lower = finer/more crushed = better),
      blob_fraction share of energy in features coarser than ~32px at 2048
                    (the "dinner plate on the hood" share),
      fine_fraction share of energy in features finer than ~8px at 2048.

    Calibrated on Ricky's FABLE round-1 verdicts: his two keepers are the
    flake-scale finishes; the 17 "Too blobby / macro" rebuilds all sit at
    coarser char_px / higher blob_fraction. Gate suggestion (at 2048):
    char_px <= ~10 and blob_fraction <= ~0.30 to ship without eyebrows.
    """
    g = np.asarray(img, np.float32)
    if g.ndim == 3:
        g = g[..., :3].mean(axis=2)
    if not _CV2_OK:
        return {"char_px": 0.0, "blob_fraction": 0.0, "fine_fraction": 1.0}
    px_per = float(full_size) / max(g.shape[0], g.shape[1])  # rescale sigmas to 2048 terms
    sigmas = [s for s in (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0) if s / px_per >= 0.5]
    prev = g
    energies, scales = [], []
    for s in sigmas:
        cur = _cv2.GaussianBlur(g, (0, 0), s / px_per)
        energies.append(float(np.abs(prev - cur).mean()))
        scales.append(s)
        prev = cur
    e = np.asarray(energies, np.float64)
    total = float(e.sum()) + 1e-9
    char_px = float((e * np.asarray(scales)).sum() / total)
    blob = float(e[[i for i, s in enumerate(scales) if s >= 32.0]].sum() / total) if any(s >= 32 for s in scales) else 0.0
    fine = float(e[[i for i, s in enumerate(scales) if s <= 4.0]].sum() / total)
    return {"char_px": round(char_px, 2), "blob_fraction": round(blob, 3), "fine_fraction": round(fine, 3)}


# ---------------------------------------------------------------------------
# spec_hue_diversity — the broadcast-WTF gate (owner doctrine 2026-06-10:
# "COLOR DIVERSITY in the spec channel... if it's 99% shades of green nothing
# happens to the car in motion"). Quantizes each spec pixel into one of 8
# channel-dominance classes (M/R/Cc above/below mid) and measures how many
# distinct hue classes interleave at fine scale.
# ---------------------------------------------------------------------------
def spec_hue_diversity(spec, mid=120):
    """spec: HxWx3+ uint8 (M,R,Cc[,A]) or float [0,255]. Returns dict:
      max_share   share of the dominant hue class (lower = more diverse),
      n_classes   classes holding >= 6% of pixels (target >= 4),
      entropy     hue-class Shannon entropy in bits (max 3.0),
      interleave  fraction of pixels whose 4px neighborhood spans >= 2 classes
                  (fine spatial mixing — high = layered, low = big flat zones).
    """
    s = np.asarray(spec)
    cls = ((s[..., 0] > mid).astype(np.int32) * 4
           + (s[..., 1] > mid).astype(np.int32) * 2
           + (s[..., 2] > mid).astype(np.int32))
    counts = np.bincount(cls.ravel(), minlength=8).astype(np.float64)
    p = counts / max(counts.sum(), 1)
    nz = p[p > 1e-9]
    entropy = float(-(nz * np.log2(nz)).sum())
    max_share = float(p.max())
    n_classes = int((p >= 0.06).sum())
    if _CV2_OK:
        cmax = _cv2.dilate(cls.astype(np.uint8), np.ones((5, 5), np.uint8))
        cmin = _cv2.erode(cls.astype(np.uint8), np.ones((5, 5), np.uint8))
        interleave = float((cmax != cmin).mean())
    else:
        interleave = 0.0
    return {"max_share": round(max_share, 3), "n_classes": n_classes,
            "entropy": round(entropy, 2), "interleave": round(interleave, 3)}


# ---------------------------------------------------------------------------
# mip_survival — does the detail survive being viewed at track distance?
# ---------------------------------------------------------------------------
def mip_survival(img, factor=4):
    """Detail retention in [0,1] after a mip-style 1/factor downsample (what the
    sim shows at distance). Combines contrast retention and high-frequency
    energy retention. Calibration (2026-06-09, LFR keepers): healthy finishes
    score >= ~0.45; < 0.25 = turns to gray mush on track."""
    g = np.asarray(img, np.float32)
    if g.ndim == 3:
        g = g[..., :3].mean(axis=2)
    h, w = g.shape
    if not _CV2_OK:
        return 1.0  # can't measure without cv2; never block on it
    small = _cv2.resize(g, (max(8, w // factor), max(8, h // factor)), interpolation=_cv2.INTER_AREA)
    back = _cv2.resize(small, (w, h), interpolation=_cv2.INTER_LINEAR)
    std_full = float(g.std())
    std_back = float(back.std())
    hf_full = float(np.abs(g - _cv2.GaussianBlur(g, (0, 0), 2.0)).mean())
    hf_back = float(np.abs(back - _cv2.GaussianBlur(back, (0, 0), 2.0)).mean())
    contrast_keep = min(std_back / max(std_full, 1e-6), 1.0)
    hf_keep = min(hf_back / max(hf_full, 1e-6), 1.0)
    return float(0.5 * contrast_keep + 0.5 * hf_keep)
