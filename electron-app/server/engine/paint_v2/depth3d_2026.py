"""depth3d_2026 — reusable DEPTH / FAKE-3D / MOTION primitive library for SPB spec maps.

PURE numpy (cv2 used *only* as a fast resize accelerator with a numpy fallback, so this
module imports and runs standalone with no engine boot side-effects). Every public function
is a deterministic, vectorized pure function that operates on HxW float fields and returns
HxW float fields or, at the compose stage, an (H, W, 4) uint8 spec array.

WHY THIS EXISTS (the SPB identity):
    A flat 2048x2048 UV livery looks painted-on. The SPEC MAP is what makes it look
    SCULPTED and makes it FLASH / MOVE under iRacing's moving sun. This library packages
    the four mechanics that buy that illusion, so any per-finish recipe can compose them
    instead of re-deriving them:

      1. FAKE-3D   — treat a height field as geometry, finite-difference it into normals,
                     and bake bevel shading so flat paint catches light like it has relief.
      2. PAINT-TRACED — derive spec detail from the *paint's own* luminance/field so glints
                     land exactly on the paint topology (shared geometry, not alien noise).
      3. BEVEL EDGE CATCH — boost spec at high-gradient edges so seams/creases throw a
                     bright rim glint (the "machined edge" read).
      4. MOTION    — a phase-parameterized traveling color/glint shift: the SAME pixel
                     brightens at one sun angle and darkens at another. No animation is
                     stored; the phase is the sun-angle proxy iRacing supplies for free as
                     the car rotates relative to the light.

SPEC CHANNEL CONVENTIONS (matches engine/core.py):
    Channel 0  M  = Metallic   (0..255; >=240 reads as chrome)
    Channel 1  R  = Roughness  (0 = mirror, 255 = matte) — iron floor 15 for non-chrome
    Channel 2  Cc = Clearcoat  (16 = MAX gloss .. 255 = dull/destroyed) — iron floor 16
    Channel 3  A  = Alpha      (255 opaque)

    NOTE the Cc polarity: LOW is glossy. compose_depth_spec() inverts "gloss intent"
    accordingly so a recipe author thinks in "how glossy" and the channel comes out right.

DECORRELATION DOCTRINE:
    M / R / Cc must each carry their OWN geometry so |corr| < 0.85 between any pair.
    decorrelated_mrcc() builds three independent fields; compose_depth_spec() lets a recipe
    blend traced/bevel/motion detail per-channel with independent weights + seed offsets.

PERFORMANCE:
    Heavy primitives accept a `work_cap` and solve on a downscaled grid, then upscale the
    result. Target: full (M,R,Cc) solve for a 2048 field in well under ~1.5s.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

# --- optional accelerators (module stays importable + correct without them) ---------------
try:  # fast resize; falls back to a pure-numpy bilinear resampler below.
    import cv2  # type: ignore
    _HAVE_CV2 = True
except Exception:  # pragma: no cover - exercised only on cv2-less installs
    cv2 = None  # type: ignore
    _HAVE_CV2 = False

try:  # iron-rule enforcement; falls back to an inline clamp if the engine isn't importable.
    from engine.core import enforce_iron_rules as _engine_enforce_iron_rules
    _HAVE_ENGINE_IRON = True
except Exception:  # pragma: no cover - exercised only when run fully standalone
    _engine_enforce_iron_rules = None  # type: ignore
    _HAVE_ENGINE_IRON = False

# Iron-rule floors (mirror engine/core.py so the standalone fallback agrees bit-for-bit).
_CC_MIN = 16
_R_MIN = 15
_CHROME_M = 240

__all__ = [
    "height_to_normals",
    "shade_bevels",
    "paint_traced_spec",
    "bevel_edge_catch",
    "traveling_colorshift",
    "decorrelated_mrcc",
    "compose_depth_spec",
    "decorrelate_envelope",
    "enforce_iron_rules",
]


# =====================================================================================
# small internal helpers (pure)
# =====================================================================================
def _as_field(a: np.ndarray) -> np.ndarray:
    """Coerce input to a float32 HxW field. Accepts HxW, HxWx{1,3,4} (RGB->luma)."""
    a = np.asarray(a)
    if a.ndim == 3:
        if a.shape[2] >= 3:
            # Rec.709 luma; ignores any alpha channel.
            a = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])
        else:
            a = a[..., 0]
    return a.astype(np.float32)


def _norm01(a: np.ndarray) -> np.ndarray:
    """Min-max normalize to 0..1 (flat input -> all zeros, never NaN)."""
    a = a.astype(np.float32)
    lo = float(a.min())
    rng = float(np.ptp(a))
    if rng < 1e-12:
        return np.zeros_like(a)
    return (a - lo) / rng


def _resize(field: np.ndarray, h: int, w: int) -> np.ndarray:
    """Resize a 2D float field to (h, w). cv2 cubic when available, else numpy bilinear."""
    field = np.asarray(field, dtype=np.float32)
    if field.shape[0] == h and field.shape[1] == w:
        return field
    if _HAVE_CV2:
        interp = cv2.INTER_CUBIC if (h >= field.shape[0]) else cv2.INTER_AREA
        return cv2.resize(field, (w, h), interpolation=interp).astype(np.float32)
    # --- pure-numpy bilinear fallback -----------------------------------------------------
    sh, sw = field.shape[:2]
    ys = (np.linspace(0, sh - 1, h)).astype(np.float32)
    xs = (np.linspace(0, sw - 1, w)).astype(np.float32)
    y0 = np.floor(ys).astype(np.int64); y1 = np.minimum(y0 + 1, sh - 1)
    x0 = np.floor(xs).astype(np.int64); x1 = np.minimum(x0 + 1, sw - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    top = field[y0][:, x0] * (1 - wx) + field[y0][:, x1] * wx
    bot = field[y1][:, x0] * (1 - wx) + field[y1][:, x1] * wx
    return (top * (1 - wy) + bot * wy).astype(np.float32)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _fbm(h: int, w: int, seed: int, *, octaves: int = 5, lacunarity: float = 2.0,
         gain: float = 0.5, base: int = 6) -> np.ndarray:
    """Cheap fractal value-noise field in 0..1 (low-res lattice per octave, smooth-resized).

    Self-contained (does not depend on engine.core) so the module is standalone. Each octave
    is a small random lattice upsampled to full size; octaves are summed with falling gain.
    """
    rng = _rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    total = 0.0
    freq = base
    for o in range(octaves):
        gh = max(2, int(freq))
        gw = max(2, int(freq))
        lattice = rng.standard_normal((gh, gw)).astype(np.float32)
        out += amp * _resize(lattice, h, w)
        total += amp
        amp *= gain
        freq = int(round(freq * lacunarity))
    return _norm01(out / (total + 1e-9))


def _grad(field: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Central-difference gradient (gx along x/cols, gy along y/rows). Edge-replicated."""
    gx = np.empty_like(field)
    gy = np.empty_like(field)
    gx[:, 1:-1] = (field[:, 2:] - field[:, :-2]) * 0.5
    gx[:, 0] = field[:, 1] - field[:, 0]
    gx[:, -1] = field[:, -1] - field[:, -2]
    gy[1:-1, :] = (field[2:, :] - field[:-2, :]) * 0.5
    gy[0, :] = field[1, :] - field[0, :]
    gy[-1, :] = field[-1, :] - field[-2, :]
    return gx, gy


# =====================================================================================
# 1. FAKE-3D: height field -> normals -> bevel shading
# =====================================================================================
def height_to_normals(H: np.ndarray, strength: float = 1.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a height field into fake-3D surface normals via finite-difference gradients.

    The classic normal-mapping derivation: a height field H(x, y) has the surface
    z = H(x, y); its (un-normalized) normal is (-dH/dx, -dH/dy, 1). `strength` scales the
    in-plane gradient (taller relief => more tilted normals => stronger bevel catch).

    Args:
        H: HxW height field (any float range; internally normalized to 0..1 so the result
           is scale-invariant). RGB/RGBA inputs are reduced to luma.
        strength: relief exaggeration. 0 => flat (normal == +Z everywhere). Typical 0.5..4.

    Returns:
        (nx, ny, nz) each HxW float32, unit-length per pixel (nx^2+ny^2+nz^2 == 1).
        nz is always positive (surface faces the viewer).
    """
    Hf = _norm01(_as_field(H))
    gx, gy = _grad(Hf)
    s = float(strength)
    nx = -gx * s
    ny = -gy * s
    nz = np.ones_like(Hf)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-12)
    return (nx * inv).astype(np.float32), (ny * inv).astype(np.float32), (nz * inv).astype(np.float32)


def shade_bevels(normals: Tuple[np.ndarray, np.ndarray, np.ndarray],
                 light_dir: Tuple[float, float, float] = (0.6, 0.4, 0.7),
                 *, ambient: float = 0.15, gamma: float = 1.0) -> np.ndarray:
    """Lambertian bevel shading from fake-3D normals: how brightly each pixel catches light.

    This is the payoff of `height_to_normals`: dotting the per-pixel normal with a light
    direction makes the *flat* paint read as beveled relief. Slopes facing the light go
    bright, slopes facing away go dark — the fake-3D "catch".

    Args:
        normals: (nx, ny, nz) from height_to_normals (or any unit normal triple).
        light_dir: (lx, ly, lz) light vector (auto-normalized). Acts as the SUN ANGLE; vary
            it (or use traveling_colorshift) to make the same relief flash differently.
        ambient: floor brightness in 0..1 so shadowed slopes aren't pure black.
        gamma: contrast shaping of the final shade (>1 deepens shadows).

    Returns:
        HxW float32 shading map in 0..1.
    """
    nx, ny, nz = normals
    lx, ly, lz = light_dir
    ln = np.sqrt(lx * lx + ly * ly + lz * lz) + 1e-12
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    ndl = nx * lx + ny * ly + nz * lz          # Lambert term, [-1, 1]
    ndl = np.clip(ndl, 0.0, 1.0)               # back-faces -> 0
    shade = float(ambient) + (1.0 - float(ambient)) * ndl
    if gamma != 1.0:
        shade = np.power(np.clip(shade, 0.0, 1.0), float(gamma))
    return np.clip(shade, 0.0, 1.0).astype(np.float32)


# =====================================================================================
# 2. PAINT-TRACED spec detail (glints align with the paint's own topology)
# =====================================================================================
def paint_traced_spec(paint_luma_or_field: np.ndarray, *,
                      relief_strength: float = 2.0,
                      light_dir: Tuple[float, float, float] = (0.6, 0.4, 0.7),
                      edge_gain: float = 0.6,
                      detail_seed: Optional[int] = None,
                      detail_amount: float = 0.0) -> np.ndarray:
    """Build spec DETAIL that TRACES the paint geometry, so glints land on the paint topology.

    The paint's luminance is treated as a height field: bright paint = raised, dark = sunken.
    We bevel-shade that relief and add an edge-catch term, so wherever the *painted design*
    has structure, the spec map gets a matching, aligned glint. This is the SPB doctrine that
    spec must trace the paint (shared geometry / seed), not float alien noise on top.

    Args:
        paint_luma_or_field: HxW field or RGB/RGBA paint (reduced to luma). This IS the
            shared geometry the spec will trace.
        relief_strength: how strongly to treat paint luma as relief (see height_to_normals).
        light_dir: sun-angle proxy for the traced bevel shading.
        edge_gain: weight of the edge-catch term mixed into the traced detail.
        detail_seed: if given, fold in a faint paint-modulated fbm so flat paint regions
            still get believable micro-structure (kept coherent with the paint via masking).
        detail_amount: 0..1 weight for that optional micro-detail.

    Returns:
        HxW float32 field in 0..1, ready to drive any of M / R / Cc (the caller decides
        polarity). High = the paint topology catches light here.
    """
    field = _norm01(_as_field(paint_luma_or_field))
    n = height_to_normals(field, strength=relief_strength)
    traced = shade_bevels(n, light_dir=light_dir, ambient=0.12)
    if edge_gain > 0.0:
        traced = np.clip(traced + edge_gain * bevel_edge_catch(field), 0.0, 1.0)
    if detail_seed is not None and detail_amount > 0.0:
        h, w = field.shape[:2]
        micro = _fbm(h, w, detail_seed, octaves=4, base=max(6, h // 64))
        # Modulate the micro-detail BY the paint so it stays correlated with the design.
        micro = micro * (0.35 + 0.65 * field)
        traced = np.clip((1.0 - detail_amount) * traced + detail_amount * micro, 0.0, 1.0)
    return _norm01(traced).astype(np.float32)


# =====================================================================================
# 3. BEVEL EDGE CATCH (gradient-magnitude rim glint)
# =====================================================================================
def bevel_edge_catch(field: np.ndarray, *, blur: float = 1.0, gamma: float = 0.8) -> np.ndarray:
    """Edge-strength (|grad|) map: bright where the field has steep transitions (creases/seams).

    A fake bevel reads as a hot rim exactly at the edges of a shape. The gradient magnitude
    of a field IS that rim. We normalize it, optionally soften it (so the glint has width),
    and gamma-shape it to taste.

    Args:
        field: HxW field (or RGB/RGBA -> luma). Edges of THIS field become the glint.
        blur: gaussian-ish softening radius in pixels (0 = razor edges). Gives the rim width.
        gamma: <1 fattens/brightens the rim, >1 thins it.

    Returns:
        HxW float32 edge-catch map in 0..1.
    """
    f = _norm01(_as_field(field))
    gx, gy = _grad(f)
    mag = np.sqrt(gx * gx + gy * gy)
    mag = _norm01(mag)
    if blur and blur > 0.0:
        mag = _blur(mag, float(blur))
        mag = _norm01(mag)
    if gamma != 1.0:
        mag = np.power(mag, float(gamma))
    return mag.astype(np.float32)


def _blur(field: np.ndarray, radius: float) -> np.ndarray:
    """Separable gaussian blur. cv2 when present, else a small separable numpy convolution."""
    if radius <= 0:
        return field
    if _HAVE_CV2:
        k = max(1, int(radius * 3) | 1)  # odd kernel
        return cv2.GaussianBlur(field, (k, k), radius)
    # pure-numpy separable gaussian
    r = max(1, int(round(radius * 3)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    g = np.exp(-(x * x) / (2.0 * radius * radius + 1e-9))
    g /= g.sum()
    pad = np.pad(field, ((r, r), (0, 0)), mode="reflect")
    tmp = np.zeros_like(field)
    for i, gi in enumerate(g):
        tmp += gi * pad[i:i + field.shape[0], :]
    pad2 = np.pad(tmp, ((0, 0), (r, r)), mode="reflect")
    out = np.zeros_like(field)
    for i, gi in enumerate(g):
        out += gi * pad2[:, i:i + field.shape[1]]
    return out


# =====================================================================================
# 4. MOTION: phase-parameterized traveling color / glint shift
# =====================================================================================
def traveling_colorshift(field: np.ndarray, phase: float, *,
                         bands: float = 5.0,
                         travel: float = 1.0,
                         sharpness: float = 2.0,
                         direction: Tuple[float, float] = (1.0, 0.35),
                         contrast: float = 1.0) -> np.ndarray:
    """Phase-parameterized traveling glint: the SAME pixel brightens at one phase, darkens at another.

    This encodes MOTION without storing animation. `phase` is a sun-angle proxy (e.g. the
    angle iRacing's moving sun makes with the panel). We build banded peaks across the field
    whose centers MIGRATE with phase, so as the car turns relative to the light, a bright band
    sweeps across the paint — the flip/flop / color-travel read. The field's own value warps
    the bands so the migration follows the paint topology rather than marching in straight
    lines (UV-orientation-agnostic).

    Args:
        field: HxW field (paint/height/any) — its value modulates band position so the glint
            travels along the design.
        phase: scalar in any range (interpreted mod 2pi). THE motion knob: sweep it 0->2pi to
            sweep the bright band across the surface.
        bands: number of glint bands across the field (more = finer flip).
        travel: how far bands migrate per unit phase (1.0 = one full band per 2pi).
        sharpness: band peak sharpness (>1 = tighter, hotter glint lines).
        direction: (dx, dy) travel axis in field space (auto-normalized). Diagonal by default
            so it never reads as upright stripes on the car.
        contrast: final contrast shaping of the 0..1 output.

    Returns:
        HxW float32 map in 0..1. High = this pixel is lit at this phase.
    """
    f = _norm01(_as_field(field))
    h, w = f.shape[:2]
    dx, dy = direction
    dn = np.hypot(dx, dy) + 1e-12
    dx, dy = dx / dn, dy / dn
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yy /= max(1, h - 1)
    xx /= max(1, w - 1)
    coord = xx * dx + yy * dy                     # 0..~1 along the travel axis
    # The paint field WARPS the phase so bands follow topology, not straight lines.
    arg = (coord + 0.25 * f) * (2.0 * np.pi * float(bands)) - float(phase) * float(travel)
    glint = 0.5 + 0.5 * np.cos(arg)               # 0..1 traveling cosine bands
    if sharpness != 1.0:
        glint = np.power(glint, float(sharpness))  # tighten peaks
    if contrast != 1.0:
        glint = np.clip((glint - 0.5) * float(contrast) + 0.5, 0.0, 1.0)
    return np.clip(glint, 0.0, 1.0).astype(np.float32)


# =====================================================================================
# 5. DECORRELATED M / R / Cc fields (each its own geometry => |corr| < 0.85)
# =====================================================================================
def decorrelated_mrcc(shape: Tuple[int, int], seed: int = 0, *,
                      work_cap: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three independent 0..1 fields (M, R, Cc) each built from its OWN geometry + seed.

    Decorrelation doctrine: M, R, Cc must not be the same map scaled three ways (|corr| must
    stay < 0.85). We give each channel a structurally different generator and a different seed
    offset:
        M  — coarse cellular/blobby relief (where metal flake reads).
        R  — fine fbm grain, ridged (roughness micro-texture), rotated frequency.
        Cc — broad smooth swells + a faint orthogonal ripple (clearcoat thickness variation).

    Args:
        shape: (H, W) output size.
        seed: base seed; each channel uses a distinct derived seed.
        work_cap: if > 0, solve on a grid capped at this size then upscale (speed for big H).

    Returns:
        (M, R, Cc) each HxW float32 in 0..1.
    """
    H, W = int(shape[0]), int(shape[1])
    if work_cap and max(H, W) > work_cap:
        scale = work_cap / float(max(H, W))
        wh, ww = max(2, int(round(H * scale))), max(2, int(round(W * scale)))
    else:
        wh, ww = H, W

    # M: coarse blobby relief — low-octave fbm, contrast-pushed into cells.
    m = _fbm(wh, ww, seed * 7 + 11, octaves=4, base=max(4, ww // 96), gain=0.55)
    m = _norm01(np.power(m, 1.6))

    # R: fine ridged grain — different seed, high base freq, ridged transform, rotated feel.
    r = _fbm(wh, ww, seed * 13 + 101, octaves=6, base=max(8, ww // 24), gain=0.5)
    r = 1.0 - np.abs(2.0 * r - 1.0)          # ridged (turbulence) — structurally unlike M
    r = _norm01(r)

    # Cc: broad smooth swells + faint orthogonal ripple — yet another seed/geometry.
    base_sw = _fbm(wh, ww, seed * 17 + 7, octaves=3, base=max(3, ww // 160), gain=0.6)
    yy, xx = np.mgrid[0:wh, 0:ww].astype(np.float32)
    ripple = 0.5 + 0.5 * np.sin((xx / max(1, ww) * 2 - yy / max(1, wh)) * np.pi * 6.0)
    cc = _norm01(0.75 * base_sw + 0.25 * ripple)

    if (wh, ww) != (H, W):
        m = _norm01(_resize(m, H, W))
        r = _norm01(_resize(r, H, W))
        cc = _norm01(_resize(cc, H, W))
    return m.astype(np.float32), r.astype(np.float32), cc.astype(np.float32)


# =====================================================================================
# iron rules (engine import with inline fallback per spec)
# =====================================================================================
def enforce_iron_rules(spec: np.ndarray) -> np.ndarray:
    """Apply SPB iron rules to an (H,W,4) uint8 spec: CC>=16 (where CC>0), R>=15 for non-chrome.

    Uses engine.core.enforce_iron_rules when importable; otherwise applies the identical
    clamp inline so this module is correct standalone. Modifies in place AND returns.
    """
    if spec is None or spec.size == 0:
        return spec
    if _HAVE_ENGINE_IRON:
        return _engine_enforce_iron_rules(spec)
    M = spec[:, :, 0]
    R = spec[:, :, 1]
    CC = spec[:, :, 2]
    np.maximum(CC, _CC_MIN, out=CC, where=(CC > 0))
    non_chrome = M < _CHROME_M
    np.maximum(R, _R_MIN, out=R, where=non_chrome)
    return spec


# =====================================================================================
# DECORRELATE: rescue a spec whose M/R/Cc collapsed onto one field (generic post-pass)
# =====================================================================================
def decorrelate_envelope(M, R, CC, seed: int = 0, *, blend: float = 0.66,
                         relief: float = 28.0, cap: int = 512):
    """Add fake-3D bevel relief to M and DECORRELATE R/Cc onto independent geometry.

    Many older SPB specs drive M, R and Cc from one shared field (|corr| -> ~1.0). This
    is a drop-in rescue: it treats the (normalized) M channel as a HEIGHT field, bakes a
    Lambert bevel into M for fake-3D relief, and blends R and Cc toward their OWN geometry
    — R onto truly-independent grain + inverse relief, Cc onto the orthogonal-sun bevel +
    a traveling motion phase + its own grain — each remapped into that channel's existing
    value RANGE (5–95 pct) so the finish's roughness/clearcoat LEVEL holds while the three
    channels decorrelate. `blend` is how far R/Cc move toward the independent geometry
    (0 = unchanged, 1 = fully replaced). Bevels solved at `cap` then upscaled (cheap).

    Args:
        M, R, CC: HxW float arrays (0..255 scale). M carries the design/flash signature.
        seed: per-finish seed for the independent grain (deterministic).
        blend: 0..1 mix toward independent geometry for R/Cc.
        relief: peak +/- bevel relief added to M (in 0..255 units).
        cap: work cap for the bevel/motion solve.

    Returns:
        (M, R, CC) float32 arrays, same shape, iron-respecting clamps applied.
    """
    M = np.asarray(M, np.float32); R = np.asarray(R, np.float32); CC = np.asarray(CC, np.float32)
    h, w = M.shape[:2]

    def _n(a):
        a = a.astype(np.float32); lo = float(a.min()); rg = float(np.ptp(a))
        return np.zeros_like(a) if rg < 1e-6 else (a - lo) / rg

    motif = _n(M)
    if cap and max(h, w) > cap:
        sc = cap / float(max(h, w))
        wh, ww = max(2, int(round(h * sc))), max(2, int(round(w * sc)))
        ms = _resize(motif, wh, ww)
    else:
        wh, ww, ms = h, w, motif
    nrm = height_to_normals(ms, strength=2.1)
    bevelA = shade_bevels(nrm, light_dir=(0.55, 0.42, 0.72), ambient=0.16, gamma=1.08)
    bevelB = shade_bevels(nrm, light_dir=(-0.46, -0.38, 0.74), ambient=0.20, gamma=0.92)
    motB = traveling_colorshift(ms, float((int(seed) % 19) * 0.331 + 2.1),
                                bands=5.5, sharpness=1.7, direction=(0.35, 1.0))
    rng = _rng(int(seed) * 131 + 613)
    g1 = rng.random((wh, ww), dtype=np.float32)
    g2 = rng.random((wh, ww), dtype=np.float32)
    if (wh, ww) != (h, w):
        bevelA = _resize(bevelA, h, w); bevelB = _resize(bevelB, h, w); motB = _resize(motB, h, w)
        g1 = _resize(g1, h, w); g2 = _resize(g2, h, w)

    # subsample for the percentile range (9x fewer elements, ~identical 5/95 pct).
    Rs = R[::3, ::3] if R.size > 500000 else R
    Cs = CC[::3, ::3] if CC.size > 500000 else CC
    Mout = np.clip(M + (bevelA - 0.5) * float(relief), 0, 255)
    r_lo = float(np.percentile(Rs, 5)); r_hi = float(np.percentile(Rs, 95))
    if r_hi - r_lo < 10.0:
        r_lo = max(15.0, r_lo - 18.0); r_hi = min(255.0, r_hi + 18.0)
    gR = _n(0.78 * g1 + 0.22 * (1.0 - bevelA))
    Rout = np.clip(R * (1.0 - blend) + (r_lo + gR * (r_hi - r_lo)) * blend, 15, 255)
    c_lo = float(np.percentile(Cs, 5)); c_hi = float(np.percentile(Cs, 95))
    if c_hi - c_lo < 10.0:
        c_lo = max(16.0, c_lo - 18.0); c_hi = min(255.0, c_hi + 18.0)
    gC = _n(0.44 * bevelB + 0.31 * motB + 0.25 * g2)
    CCout = np.clip(CC * (1.0 - blend) + (c_lo + gC * (c_hi - c_lo)) * blend, 16, 255)
    return Mout.astype(np.float32), Rout.astype(np.float32), CCout.astype(np.float32)


# =====================================================================================
# COMPOSE: paint field + recipe -> (M, R, Cc) uint8 spec (iron-ruled)
# =====================================================================================
def _resolve(val, h, w):
    """Turn a recipe value into an HxW float field: scalar -> constant, field -> resized 0..1."""
    if np.isscalar(val):
        return np.full((h, w), float(val), np.float32)
    arr = _norm01(_as_field(val))
    if arr.shape[:2] != (h, w):
        arr = _norm01(_resize(arr, h, w))
    return arr.astype(np.float32)


def compose_depth_spec(paint_field: np.ndarray, recipe: Optional[Dict] = None) -> np.ndarray:
    """Compose a fake-3D, paint-traced, motion-capable (M, R, Cc) spec map from a paint field.

    This is the one-call entry point a per-finish recipe uses. It blends the library's
    primitives per channel with independent weights so the three channels stay decorrelated,
    then bakes the iron rules.

    Pipeline per pixel value:
        traced   = paint_traced_spec(paint)              # spec traces the paint topology
        edge     = bevel_edge_catch(paint)               # fake bevel rim glint
        bevel    = shade_bevels(height_to_normals(paint))# fake-3D relief shading
        motion   = traveling_colorshift(paint, phase)    # angle-gated flash (set phase!)
        base_m/r/cc = decorrelated_mrcc(...)             # each channel's own geometry

      Each channel is base + (weighted traced/edge/bevel/motion), independently configured.

    Recipe keys (all optional; sensible defaults give a believable sculpted gloss):
        work_cap (int)        : solve detail at this cap then upscale (default 1024).
        phase (float)         : sun-angle proxy for the motion term (default 0.0).
        relief_strength,light_dir,edge_gain : forwarded to the traced/bevel primitives.
        seed (int)            : seed for decorrelated base fields + micro detail.
        For each channel ch in {"M","R","Cc"}, a dict of weights:
            base, traced, edge, bevel, motion : 0..1 blend weights (need not sum to 1)
            bias   : added constant before scaling to 0..255
            scale  : multiplies the normalized channel value (default 255)
            invert : if True, use (1 - value) before scaling (use for Cc gloss: low=glossy)
        Defaults below encode: glossy clearcoat that follows paint relief, metallic that
        pools in coarse blobs lit by the traced bevel, roughness broken up by fine grain +
        edges — three different geometries.

    Args:
        paint_field: HxW field or RGB/RGBA paint. The shared geometry everything traces.
        recipe: dict as described above (or None for defaults).

    Returns:
        (H, W, 4) uint8 spec array [M, R, Cc, A=255], with iron rules enforced.
    """
    recipe = dict(recipe or {})
    pf = _norm01(_as_field(paint_field))
    H, W = pf.shape[:2]

    work_cap = int(recipe.get("work_cap", 1024))
    seed = int(recipe.get("seed", 0))
    phase = float(recipe.get("phase", 0.0))
    relief_strength = float(recipe.get("relief_strength", 2.0))
    light_dir = tuple(recipe.get("light_dir", (0.6, 0.4, 0.7)))
    edge_gain = float(recipe.get("edge_gain", 0.6))

    # Solve detail on a (possibly) downscaled paint field for speed, upscale at the end.
    if work_cap and max(H, W) > work_cap:
        scale = work_cap / float(max(H, W))
        wh, ww = max(2, int(round(H * scale))), max(2, int(round(W * scale)))
        wpf = _norm01(_resize(pf, wh, ww))
    else:
        wh, ww = H, W
        wpf = pf

    # --- shared building blocks (computed once, reused across channels) -------------------
    traced = paint_traced_spec(wpf, relief_strength=relief_strength, light_dir=light_dir,
                               edge_gain=edge_gain, detail_seed=seed * 3 + 1,
                               detail_amount=0.15)
    edge = bevel_edge_catch(wpf, blur=1.0)
    bevel = shade_bevels(height_to_normals(wpf, strength=relief_strength), light_dir=light_dir)
    motion = traveling_colorshift(wpf, phase, bands=6.0, travel=1.0, sharpness=2.0)
    bM, bR, bCc = decorrelated_mrcc((wh, ww), seed=seed)

    parts = {"traced": traced, "edge": edge, "bevel": bevel, "motion": motion}
    bases = {"M": bM, "R": bR, "Cc": bCc}

    # --- per-channel defaults (each leans on DIFFERENT primitives => decorrelated) --------
    defaults = {
        # Metallic pools in coarse blobs, lit by traced relief + a touch of motion flash.
        "M":  {"base": 0.55, "traced": 0.30, "edge": 0.05, "bevel": 0.10, "motion": 0.25,
               "bias": 0.0, "scale": 220.0, "invert": False},
        # Roughness rides its own fine grain + edge breakup; LESS traced relief than M.
        "R":  {"base": 0.60, "traced": 0.10, "edge": 0.35, "bevel": 0.05, "motion": 0.05,
               "bias": 0.0, "scale": 200.0, "invert": False},
        # Clearcoat follows paint relief/bevel (glossy in the troughs); inverted (low=glossy).
        "Cc": {"base": 0.35, "traced": 0.20, "edge": 0.10, "bevel": 0.40, "motion": 0.10,
               "bias": 0.0, "scale": 200.0, "invert": True},
    }

    out = np.empty((wh, ww, 4), np.uint8)
    ch_index = {"M": 0, "R": 1, "Cc": 2}
    for ch in ("M", "R", "Cc"):
        cfg = dict(defaults[ch])
        cfg.update(recipe.get(ch, {}))
        acc = cfg.get("base", 0.0) * bases[ch]
        for pname, pfield in parts.items():
            wgt = float(cfg.get(pname, 0.0))
            if wgt != 0.0:
                acc = acc + wgt * pfield
        val = _norm01(acc)
        if cfg.get("invert", False):
            val = 1.0 - val
        val = val * float(cfg.get("scale", 255.0)) + float(cfg.get("bias", 0.0))
        out[:, :, ch_index[ch]] = np.clip(val, 0, 255).astype(np.uint8)
    out[:, :, 3] = 255

    if (wh, ww) != (H, W):
        full = np.empty((H, W, 4), np.uint8)
        for c in range(3):
            full[:, :, c] = np.clip(_resize(out[:, :, c].astype(np.float32), H, W), 0, 255).astype(np.uint8)
        full[:, :, 3] = 255
        out = full

    return enforce_iron_rules(out)


# =====================================================================================
# self-test (run module directly: python -m engine.paint_v2.depth3d_2026)
# =====================================================================================
def _self_test() -> None:
    import time
    rng = np.random.default_rng(7)
    # synthetic paint: smooth swells + a hard-edged blob (so there ARE edges/relief to trace)
    yy, xx = np.mgrid[0:256, 0:256].astype(np.float32)
    paint = (np.sin(xx / 18.0) * np.cos(yy / 23.0)).astype(np.float32)
    paint += 0.4 * rng.standard_normal((256, 256)).astype(np.float32)
    paint[64:160, 64:160] += 2.0  # a raised square -> sharp edges

    t0 = time.time()
    spec = compose_depth_spec(paint, {"seed": 3, "phase": 1.1, "work_cap": 256})
    dt = time.time() - t0

    assert spec.shape == (256, 256, 4), f"bad shape {spec.shape}"
    assert spec.dtype == np.uint8, f"bad dtype {spec.dtype}"
    M, R, Cc = spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]
    # iron rules
    assert (Cc[Cc > 0] >= _CC_MIN).all(), "CC floor violated"
    nonchrome = M < _CHROME_M
    assert (R[nonchrome] >= _R_MIN).all(), "R floor violated"
    # non-trivial variance per channel
    for name, ch in (("M", M), ("R", R), ("Cc", Cc)):
        assert float(ch.std()) > 1.0, f"{name} channel too flat (std={ch.std():.3f})"
    # decorrelation |corr| < 0.85 between channels
    def corr(a, b):
        a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
        a -= a.mean(); b -= b.mean()
        d = (np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())) + 1e-9
        return float((a * b).sum() / d)
    cmr, cmc, crc = corr(M, R), corr(M, Cc), corr(R, Cc)
    # motion: same pixels differ across phase
    s0 = compose_depth_spec(paint, {"seed": 3, "phase": 0.0, "work_cap": 256})
    s1 = compose_depth_spec(paint, {"seed": 3, "phase": 3.14159, "work_cap": 256})
    motion_delta = float(np.abs(s0[:, :, 0].astype(np.int16) - s1[:, :, 0].astype(np.int16)).mean())

    print("depth3d_2026 self-test")
    print(f"  shape={spec.shape} dtype={spec.dtype} compose_time={dt*1000:.1f}ms")
    print(f"  M  std={M.std():.2f} R std={R.std():.2f} Cc std={Cc.std():.2f}")
    print(f"  corr |M,R|={abs(cmr):.3f} |M,Cc|={abs(cmc):.3f} |R,Cc|={abs(crc):.3f} (want<0.85)")
    print(f"  motion mean|dM| across phase = {motion_delta:.2f} (want>0)")
    print(f"  iron rules: CC>=16 OK, R>=15 OK   engine_iron={_HAVE_ENGINE_IRON} cv2={_HAVE_CV2}")
    assert motion_delta > 0.0, "motion term produced no change across phase"
    print("  ALL ASSERTS PASSED")


if __name__ == "__main__":
    _self_test()
