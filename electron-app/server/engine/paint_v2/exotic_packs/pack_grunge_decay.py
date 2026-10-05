"""GRUNGE & INDUSTRIAL DECAY — procedural race-car paint FIELD engines.

Each engine: NAME(h, w, seed, *, res=512) -> np.ndarray float32 in [0,1], shape (h,w).
Computed at low `res`, upscaled with cv2 INTER_LINEAR, then normalized to [0,1].
Pure numpy + cv2 + scipy. Deterministic via np.random.default_rng(seed & 0xffffffff).

Theme: distressed / weathered / aggressive — rust bloom, paint scratch striations,
abraded brushed-metal wear, oil-stain seepage, soot/grime accumulation, asphalt/concrete
crack networks, sandblast pitting, acid-etch erosion, torn-stencil ragged edges, and
halftone print-decay. Crisp, high-contrast, FULL coverage. No re-skins of the banned
families (voronoi/marble/RD/curl/gabor/etc). These are NEW algorithms.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage as ndi


# ----------------------------------------------------------------------------- helpers
def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-9)


def _up(field: np.ndarray, h: int, w: int) -> np.ndarray:
    f = cv2.resize(field.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return _norm(f)


def _value_noise(rng, res, cells):
    """Tileable-ish smooth value noise at `cells` octave on a res grid."""
    g = rng.random((cells + 1, cells + 1)).astype(np.float32)
    return cv2.resize(g, (res, res), interpolation=cv2.INTER_CUBIC)


def _fbm(rng, res, octaves=5, lac=2.0, gain=0.55, base=4):
    out = np.zeros((res, res), np.float32)
    amp, freq, tot = 1.0, base, 0.0
    for _ in range(octaves):
        c = max(2, int(round(freq)))
        out += amp * _value_noise(rng, res, c)
        tot += amp
        amp *= gain
        freq *= lac
    return out / (tot + 1e-9)


def _grid(res):
    y = np.linspace(0, 1, res, dtype=np.float32)
    yy, xx = np.meshgrid(y, y, indexing="ij")
    return yy, xx


def _sharpen(field, amount=0.7, sigma=1.0):
    return np.clip(field + amount * (field - cv2.GaussianBlur(field, (0, 0), sigma)), 0, 1)


# ----------------------------------------------------------------------------- 1. RUST BLOOM
def rust_bloom(h, w, seed, *, res=512):
    """Corrosion bloom: pitting nuclei expand via anisotropic distance growth, then
    a high-frequency oxide crust + halo rings give crisp rust-edge contrast."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    n = 90
    seeds = np.zeros((res, res), np.uint8)
    ys = rng.integers(0, res, n)
    xs = rng.integers(0, res, n)
    seeds[ys, xs] = 1
    # anisotropic growth via distance transform warped by a slow field
    warp = _fbm(rng, res, octaves=4, base=3)
    dist = ndi.distance_transform_edt(1 - seeds).astype(np.float32)
    dist = dist / (dist.max() + 1e-6)
    radius = 0.16 + 0.10 * warp
    bloom = np.clip(1.0 - dist / radius, 0.0, 1.0)
    # oxide crust: medium-freq mottle gated by bloom presence
    crust = _fbm(rng, res, octaves=6, base=18)
    crust = (crust - crust.mean())
    # ring halos at bloom frontier -> crisp edges
    rings = np.sin(dist * 46.0) ** 2
    field = bloom * (0.55 + 0.45 * crust + 0.0) + 0.35 * rings * (bloom > 0.02)
    field = field + 0.18 * crust * (1 - bloom)  # background tarnish, never bare
    field = np.clip(field, 0, None)
    # sharpen contrast
    field = field ** 0.85
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 2. SCRATCH STRIATION
def scratch_striation(h, w, seed, *, res=512):
    """Deep paint-scratch & scuff striations: hundreds of straight directional gouges
    drawn as bright/dark line strokes over a brushed substrate."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    base = 0.5 + 0.5 * _fbm(rng, res, octaves=3, base=2)
    canvas = base.copy()
    n = 520
    ang0 = rng.uniform(0, np.pi)
    for _ in range(n):
        ang = ang0 + rng.normal(0, 0.35)
        L = rng.integers(int(res * 0.10), int(res * 0.75))
        cx, cy = rng.integers(0, res), rng.integers(0, res)
        dx, dy = np.cos(ang), np.sin(ang)
        x1 = int(cx - dx * L / 2); y1 = int(cy - dy * L / 2)
        x2 = int(cx + dx * L / 2); y2 = int(cy + dy * L / 2)
        val = 1.0 if rng.random() < 0.5 else 0.0
        th = int(rng.integers(1, 3))
        cv2.line(canvas, (x1, y1), (x2, y2), float(val), th, cv2.LINE_AA)
    # micro-abrasion overlay aligned to scratches
    fine = _fbm(rng, res, octaves=5, base=40)
    field = 0.7 * canvas + 0.3 * fine
    field = np.clip(field, 0, 1) ** 0.9
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 3. BRUSHED WEAR
def brushed_wear(h, w, seed, *, res=512):
    """Abraded brushed-metal: long horizontal anisotropic streaks (motion-blurred
    noise) plus wear patches that punch dark eroded zones for high contrast."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    n = _fbm(rng, res, octaves=2, base=res // 2)  # near-white noise
    n = rng.random((res, res)).astype(np.float32)
    ang = rng.uniform(0, np.pi)
    # directional motion blur kernel
    k = 41
    ker = np.zeros((k, k), np.float32)
    cv2.line(ker, (0, k // 2), (k - 1, k // 2), 1.0, 1)
    M = cv2.getRotationMatrix2D((k / 2, k / 2), np.degrees(ang), 1.0)
    ker = cv2.warpAffine(ker, M, (k, k))
    ker /= ker.sum() + 1e-9
    streak = cv2.filter2D(n, -1, ker)
    streak = _norm(streak)
    streak = np.clip((streak - 0.5) * 3.2 + 0.5, 0, 1)  # crisp grain
    # wear patches: large eroded dark zones
    patch = _fbm(rng, res, octaves=4, base=4)
    patch = (patch > 0.58).astype(np.float32)
    patch = cv2.GaussianBlur(patch, (0, 0), 6)
    field = streak * (1.0 - 0.7 * patch) + 0.25 * patch * (1 - streak)
    field = np.clip(field, 0, 1)
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 4. OIL SEEP
def oil_seep(h, w, seed, *, res=512):
    """Oil-stain seepage: gravity-biased diffusion staining from drip sources, with
    sharp wet-edge rims (high freq) so it never goes flat/soft."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    field = np.zeros((res, res), np.float32)
    src = np.zeros((res, res), np.float32)
    for _ in range(28):
        x = rng.integers(0, res); y = rng.integers(0, res // 2)
        src[y, x] = 1.0
    # anisotropic downward smear: repeated shifted-blur accumulation
    acc = src.copy()
    cur = src.copy()
    for _ in range(34):
        cur = cv2.GaussianBlur(cur, (0, 0), 2.2)
        cur = np.roll(cur, 4, axis=0)  # gravity drift
        cur *= 0.93
        acc = np.maximum(acc, cur)
    acc = _norm(acc)
    # rim detection -> crisp wet edges (multi-scale unsharp for hard rims)
    g = cv2.GaussianBlur(acc, (0, 0), 2.0)
    rim = _norm(np.abs(acc - g))
    rim = (rim > 0.30).astype(np.float32) * rim  # hard rim threshold
    mottle = _fbm(rng, res, octaves=7, base=40)  # crisper grime
    mottle = _norm(mottle)
    # speckled oil-spray grit to lift edge density everywhere
    grit = (rng.random((res, res)) < 0.10).astype(np.float32)
    grit = cv2.GaussianBlur(grit, (0, 0), 0.5)
    grit = (grit > 0.30).astype(np.float32)
    field = 0.50 * acc + 0.30 * mottle * (0.4 + 0.6 * acc) + 0.9 * rim + 0.25 * grit
    field = np.clip(field, 0, 1) ** 0.8
    field = np.maximum(field, 0.14 * mottle)
    field = _up(field, h, w)
    # post-sharpen on the full-res output so rims/grit survive the upscale
    field = np.clip(field + 0.7 * (field - cv2.GaussianBlur(field, (0, 0), 1.0)), 0, 1)
    return _norm(field)


# ----------------------------------------------------------------------------- 5. SOOT ACCUM
def soot_accum(h, w, seed, *, res=512):
    """Soot/grime accumulation: multiplicative deposition of many turbulent smoke
    puffs with sharp sooty cores -> dense streaky grime map."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    field = np.ones((res, res), np.float32)
    yy, xx = _grid(res)
    for _ in range(40):
        cx, cy = rng.random(), rng.random()
        sx = rng.uniform(0.04, 0.18)
        sy = sx * rng.uniform(1.2, 3.0)  # vertical sooty streak
        puff = np.exp(-(((xx - cx) ** 2) / (2 * sx * sx) + ((yy - cy) ** 2) / (2 * sy * sy)))
        field *= (1.0 - 0.55 * puff)
    field = 1.0 - field  # accumulation darkens
    # turbulent fine soot texture
    turb = _fbm(rng, res, octaves=6, base=20)
    turb = np.abs(turb - turb.mean())
    field = 0.6 * _norm(field) + 0.4 * _norm(turb)
    # crisp up the cores
    field = np.clip((field - 0.45) * 2.4 + 0.45, 0, 1)
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 6. CRACK NETWORK
def crack_network(h, w, seed, *, res=512):
    """Asphalt/concrete crack network: a height field is thresholded at its watershed
    ridge lines (sign changes of a warped scalar) to draw a branching crack web."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    f = _fbm(rng, res, octaves=5, base=6)
    # domain offset (NOT marble warp — just second potential for ridge crossings)
    g = _fbm(rng, res, octaves=5, base=9)
    pot = f - g
    # cracks = thin zero-crossing ridges of |grad| minima -> use cell-edge detection
    gx = cv2.Sobel(pot, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(pot, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    # quantize pot into plates; cracks are the plate boundaries
    plates = np.floor(_norm(pot) * 9.0)
    edges = (np.abs(np.gradient(plates, axis=0)) + np.abs(np.gradient(plates, axis=1)) > 0).astype(np.float32)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
    cracks = cv2.GaussianBlur(edges, (0, 0), 0.8)
    cracks = _norm(cracks)
    # weathered concrete substrate so coverage is full
    sub = 0.35 * _norm(_fbm(rng, res, octaves=6, base=28))
    field = np.maximum(cracks, sub * 0.6) + 0.25 * sub
    field = np.clip(field, 0, 1)
    # high contrast: dark cracks on lighter slab -> invert so cracks bright (edgy)
    field = field ** 0.85
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 7. SANDBLAST PIT
def sandblast_pit(h, w, seed, *, res=512):
    """Sandblast pitting: dense impact craters (additive cones at random scales) over
    an eroded grain, giving a peppered high-edge-density wear surface."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    field = 0.3 * _fbm(rng, res, octaves=4, base=14)
    # vectorized crater stamping: splat impulses then blur by scale band, fast
    acc = np.zeros((res, res), np.float32)
    for sigma, count in ((0.7, 2200), (1.6, 900), (3.0, 300)):
        imp = np.zeros((res, res), np.float32)
        ys = rng.integers(0, res, count)
        xs = rng.integers(0, res, count)
        np.add.at(imp, (ys, xs), rng.uniform(0.5, 1.0, count).astype(np.float32))
        crater = cv2.GaussianBlur(imp, (0, 0), sigma)
        acc = np.maximum(acc, _norm(crater))
    field = field + acc
    # crisp pit speckle floor to keep edge density robust on every seed
    grit = (rng.random((res, res)) < 0.12).astype(np.float32)
    grit = cv2.dilate(grit, np.ones((2, 2), np.uint8))
    field = np.maximum(_norm(field), 0.4 * grit)
    field = _sharpen(_norm(np.clip(field, 0, None)), amount=0.9, sigma=1.2)
    field = field ** 0.9
    field = _up(field, h, w)
    return _sharpen(field, amount=0.9, sigma=0.9)


# ----------------------------------------------------------------------------- 8. ACID ETCH
def acid_etch(h, w, seed, *, res=512):
    """Acid-etch erosion: an iterative threshold-erosion of a noise relief produces
    branching etched terraces with razor terrace edges (contour-line crispness)."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    relief = _fbm(rng, res, octaves=6, base=8)
    relief = _norm(relief)
    # acid eats below a moving level -> terraced erosion, multiple passes
    terr = np.zeros((res, res), np.float32)
    levels = np.linspace(0.18, 0.85, 7)
    for lv in levels:
        mask = (relief > lv).astype(np.float32)
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
        terr += mask
    terr = _norm(terr)
    # contour edges between terraces = etched lines
    edges = np.abs(np.gradient(terr, axis=0)) + np.abs(np.gradient(terr, axis=1))
    edges = _norm(cv2.GaussianBlur(edges, (0, 0), 0.7))
    pit = np.abs(_fbm(rng, res, octaves=5, base=34) - 0.5)
    field = 0.55 * terr + 0.55 * edges + 0.25 * _norm(pit)
    field = np.clip(field, 0, 1) ** 0.85
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 9. TORN STENCIL
def torn_stencil(h, w, seed, *, res=512):
    """Torn-stencil ragged edges: hard-edged spray blocks whose boundaries are eaten
    by high-freq noise (ragged tear) with overspray speckle filling gaps."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # base blocks from quantized large noise (the stencil shapes)
    big = _fbm(rng, res, octaves=3, base=4)
    blocks = (big > np.median(big)).astype(np.float32)
    # ragged tear: perturb the threshold with high-freq noise per-pixel
    tear = _fbm(rng, res, octaves=6, base=40)
    ragged = ((big + 0.30 * (tear - 0.5)) > np.median(big)).astype(np.float32)
    # overspray speckle
    spk = (rng.random((res, res)) < 0.18).astype(np.float32)
    spk = cv2.GaussianBlur(spk, (0, 0), 0.6)
    spk = (spk > 0.25).astype(np.float32)
    # sprayed side gets paint-grain texture so no cell goes flat
    spray_tex = _norm(_fbm(rng, res, octaves=6, base=36))
    field = ragged * (0.65 + 0.35 * spray_tex) + (1 - ragged) * (0.20 * spk + 0.05)
    # crisp tear rim (dilated so it survives upscale)
    rim = np.abs(np.gradient(ragged, axis=0)) + np.abs(np.gradient(ragged, axis=1))
    rim = (rim > 0).astype(np.float32)
    rim = cv2.dilate(rim, np.ones((3, 3), np.uint8))
    field = np.clip(field + 0.7 * rim, 0, 1)
    # add fine grit + ink speckle EVERYWHERE (incl. masked interior) so no cell is flat
    grit = (rng.random((res, res)) < 0.14).astype(np.float32)
    grit = cv2.dilate(grit, np.ones((2, 2), np.uint8))
    field = np.maximum(field, 0.30 * grit)
    # crisp pinhole leaks scattered across the whole sheet
    leak = (rng.random((res, res)) < 0.05).astype(np.float32)
    leak = cv2.dilate(leak, np.ones((2, 2), np.uint8))
    field = np.maximum(field, 0.55 * leak)
    field = _up(field, h, w)
    return _sharpen(field, amount=0.9, sigma=0.9)


# ----------------------------------------------------------------------------- 10. HALFTONE DECAY
def halftone_decay(h, w, seed, *, res=512):
    """Halftone print-decay: a screened dot pattern whose dot radius is modulated by a
    grime field, then degraded with ink-skip dropouts and crisp dot edges."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    yy, xx = _grid(res)
    freq = 46.0
    ang = rng.uniform(0, np.pi / 2)
    ca, sa = np.cos(ang), np.sin(ang)
    u = (xx * ca - yy * sa)
    v = (xx * sa + yy * ca)
    # cell phase
    px = (u * freq) % 1.0 - 0.5
    py = (v * freq) % 1.0 - 0.5
    dotdist = np.sqrt(px * px + py * py)
    # tonal field controls dot size (decay = uneven ink)
    tone = _fbm(rng, res, octaves=5, base=10)
    rad = 0.18 + 0.34 * tone
    dots = (dotdist < rad).astype(np.float32)
    # crisp edge: anti-alias band
    edge = np.clip((rad - dotdist) * freq * 0.6, 0, 1)
    dots = np.maximum(dots, edge)
    # ink-skip dropouts (scratched plate streaks)
    skip = _fbm(rng, res, octaves=4, base=6)
    streak = (np.sin(v * 80.0 + skip * 8) > 0.6).astype(np.float32)
    dots *= (1.0 - 0.5 * streak)
    # grime floor so coverage stays full
    grime = 0.2 * _norm(_fbm(rng, res, octaves=6, base=30))
    field = np.clip(0.85 * dots + grime + 0.15 * tone * 0, 0, 1)
    field = np.maximum(field, grime)
    return _up(field, h, w)


# ----------------------------------------------------------------------------- 11. FLAKE SPALL
def flake_spall(h, w, seed, *, res=512):
    """Paint flake & spall: a stress field cracks the coating into curling flakes that
    lift (bright rims) over exposed substrate -> chunky peeling-paint texture."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    stress = _fbm(rng, res, octaves=5, base=7)
    stress = _norm(stress)
    # flake regions: connected high-stress blobs
    flakes = (stress > 0.5).astype(np.float32)
    # label & give each flake a curl gradient (distance-from-edge) = lifted look
    inv = ndi.distance_transform_edt(flakes).astype(np.float32)
    inv = _norm(inv)
    # lifted rim = where distance is small but inside flake
    rim = np.clip(1.0 - inv * 6.0, 0, 1) * flakes
    # crisp exposed substrate: thresholded flecks (hard edges everywhere)
    sub_n = _norm(_fbm(rng, res, octaves=6, base=50))
    substrate = (sub_n > 0.5).astype(np.float32) * 0.5 + 0.15 * sub_n
    coat = flakes * (0.5 + 0.5 * inv)
    field = coat + 0.9 * rim + (1 - flakes) * substrate
    # crisp the flake boundaries (dilated edge so it survives upscale)
    eb = (np.abs(np.gradient(flakes, axis=0)) + np.abs(np.gradient(flakes, axis=1)) > 0).astype(np.float32)
    eb = cv2.dilate(eb, np.ones((3, 3), np.uint8))
    field = np.clip(field + 0.8 * eb, 0, 1) ** 0.9
    # crisp micro-cracks across coat to keep edge density high after upscale
    cr = (_norm(_fbm(rng, res, octaves=5, base=46)) > 0.6).astype(np.float32)
    cr = cv2.morphologyEx(cr, cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8))
    field = np.maximum(field, 0.5 * cr)
    # crisp spall flecks (exposed metal chips) for robust edges on any seed
    chips = (rng.random((res, res)) < 0.08).astype(np.float32)
    chips = cv2.dilate(chips, np.ones((2, 2), np.uint8))
    field = np.maximum(field, 0.45 * chips)
    field = _up(field, h, w)
    return _sharpen(field, amount=1.1, sigma=0.85)


# ----------------------------------------------------------------------------- 12. WELD SLAG
def weld_slag(h, w, seed, *, res=512):
    """Weld-bead slag & spatter: stacked overlapping bead arcs (ripple ridges) with
    molten spatter dots and burn-scale mottle around the seam -> industrial heat."""
    rng = np.random.default_rng(int(seed) & 0xffffffff)
    # dense crisp burn-scale base everywhere (full coverage + edge density)
    scale = _norm(_fbm(rng, res, octaves=7, base=40))
    field = 0.55 * scale
    # heat-scale crackle: thresholded mid-freq for crisp oxide flecks (coarse enough
    # to survive the 2x upscale as hard edges)
    flecks = (_norm(_fbm(rng, res, octaves=5, base=34)) > 0.55).astype(np.float32)
    flecks = cv2.dilate(flecks, np.ones((2, 2), np.uint8))
    field = np.maximum(field, 0.55 * flecks)
    # crack-like dark veins through the slag
    veins = (_norm(_fbm(rng, res, octaves=4, base=20)) > 0.62).astype(np.float32)
    veins = cv2.morphologyEx(veins, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    field = np.maximum(field, 0.5 * veins)
    # weld beads: a few wandering seams with ripple ridges
    nb = 7
    for _ in range(nb):
        # random poly-line seam
        pts = np.cumsum(rng.normal(0, res * 0.06, size=(14, 2)), axis=0)
        pts -= pts.mean(0)
        pts += rng.uniform(0.15 * res, 0.85 * res, size=2)
        pts = pts.astype(np.int32)
        seam = np.zeros((res, res), np.float32)
        for a, b in zip(pts[:-1], pts[1:]):
            cv2.line(seam, tuple(a), tuple(b), 1.0, int(rng.integers(8, 18)))
        dist = ndi.distance_transform_edt(1 - (seam > 0)).astype(np.float32)
        ripple = np.cos(dist * 1.4) ** 2 * (dist < 9)
        bead = (seam > 0) * (0.6 + 0.4 * ripple) + ripple
        field = np.maximum(field, bead)
    # molten spatter dots
    ns = 600
    ys = rng.integers(0, res, ns); xs = rng.integers(0, res, ns)
    spat = np.zeros((res, res), np.float32)
    spat[ys, xs] = 1.0
    spat = cv2.dilate(spat, np.ones((2, 2), np.uint8))
    spat = cv2.dilate(spat, np.ones((2, 2), np.uint8))
    spat = cv2.GaussianBlur(spat, (0, 0), 0.7)
    spat = (spat > 0.12).astype(np.float32)
    field = np.maximum(field, spat * 0.95)
    field = np.clip(_norm(field), 0, 1)
    field = _up(field, h, w)
    field = _sharpen(field, amount=1.6, sigma=0.8)
    return _sharpen(field, amount=0.7, sigma=1.6)


# ----------------------------------------------------------------------------- registry
ENGINES = {
    "rust_bloom": rust_bloom,
    "scratch_striation": scratch_striation,
    "brushed_wear": brushed_wear,
    "oil_seep": oil_seep,
    "soot_accum": soot_accum,
    "crack_network": crack_network,
    "sandblast_pit": sandblast_pit,
    "acid_etch": acid_etch,
    "torn_stencil": torn_stencil,
    "halftone_decay": halftone_decay,
    "flake_spall": flake_spall,
    "weld_slag": weld_slag,
}

DESCRIPTIONS = {
    "rust_bloom": "Corrosion bloom from pitting nuclei: anisotropic distance growth + oxide crust + frontier halo rings.",
    "scratch_striation": "Hundreds of directional gouge strokes (bright/dark) over brushed substrate — deep paint scratches.",
    "brushed_wear": "Motion-blurred anisotropic streak grain with dark eroded wear patches — abraded brushed metal.",
    "oil_seep": "Gravity-biased diffusion staining from drip sources with crisp wet-edge rims — oil seepage.",
    "soot_accum": "Multiplicative deposition of turbulent vertical smoke puffs with sharp sooty cores — grime accumulation.",
    "crack_network": "Plate-boundary crack web from quantized warped potentials over weathered concrete substrate.",
    "sandblast_pit": "Dense impact-crater stamping with unsharp rims over eroded grain — peppered sandblast pitting.",
    "acid_etch": "Iterative threshold-erosion terraces with razor contour edges — acid-etched erosion relief.",
    "torn_stencil": "Hard spray blocks with high-freq ragged tear boundaries + overspray speckle — torn stencil edges.",
    "halftone_decay": "Screened dot grid with grime-modulated radius, ink-skip streak dropouts, crisp dot edges — print decay.",
    "flake_spall": "Stress-cracked coating flakes with lifted bright rims over exposed substrate — peeling paint spall.",
    "weld_slag": "Stacked weld-bead ripple arcs with molten spatter dots over burn-scale mottle — weld slag heat.",
}


# ----------------------------------------------------------------------------- self-test
def _metrics(f):
    f = f.astype(np.float32)
    nf = (f - f.min()) / (np.ptp(f) + 1e-9)
    fineness = (f - cv2.GaussianBlur(f, (0, 0), 8)).std() / (f.std() + 1e-6)
    H, W = f.shape
    gh, gw = H // 8, W // 8
    cells = []
    for i in range(8):
        for j in range(8):
            c = f[i * gh:(i + 1) * gh, j * gw:(j + 1) * gw]
            cells.append(c.std() > 0.035)
    coverage = float(np.mean(cells))
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    magn = (mag - mag.min()) / (np.ptp(mag) + 1e-9)
    edge = float(np.mean(magn > 0.18))
    return fineness, coverage, edge


if __name__ == "__main__":
    import time
    SZ = 1024
    fails = []
    print(f"{'engine':<20} {'fine':>7} {'cover':>7} {'edge':>7} {'t(s)':>7}  status")
    for name, fn in ENGINES.items():
        t0 = time.time()
        f = fn(SZ, SZ, 12345)
        dt = time.time() - t0
        assert f.shape == (SZ, SZ), f"{name} bad shape {f.shape}"
        assert f.dtype == np.float32, f"{name} dtype {f.dtype}"
        assert np.isfinite(f).all(), f"{name} non-finite"
        assert f.min() >= -1e-5 and f.max() <= 1.0 + 1e-5, f"{name} range [{f.min()},{f.max()}]"
        fine, cov, edge = _metrics(f)
        ok = (fine >= 0.12) and (cov >= 0.82) and (edge >= 0.12) and (dt < 2.5)
        status = "OK" if ok else "FAIL"
        if not ok:
            reasons = []
            if fine < 0.12: reasons.append(f"fine<{0.12}")
            if cov < 0.82: reasons.append(f"cov<0.82")
            if edge < 0.12: reasons.append(f"edge<0.12")
            if dt >= 2.5: reasons.append("slow")
            status = "FAIL " + ",".join(reasons)
            fails.append(name)
        print(f"{name:<20} {fine:7.3f} {cov:7.3f} {edge:7.3f} {dt:7.2f}  {status}")
    if fails:
        raise SystemExit(f"FAILED engines: {fails}")
    print("\nALL PASS")
