"""PHOTO-TO-LIVERY — drop in ANY reference image, get a complete multi-zone livery.

MEGA FEATURE.  Owner mandate (2026-06-13): make this SMART, FUNCTIONAL and VIRAL —
a 30-second "load a sunset photo -> click -> stunning livery that FEELS like the
photo" moment, not a flat recolor.  This module is the IMAGE counterpart to the
text ``engine/livery_designer.py`` (Prompt-to-Livery) and is PURELY ADDITIVE: it
edits no existing file, boots no registry on import, and keeps its public surface
(``design_from_image(image, seed)``) backward compatible.

design_from_image(image_bgr_or_path, seed=51)
    -> {"zones": [...], "explanation": "...", "palette": [...], "_meta": {...}}

How it works (v2 — the intelligent rewrite)
-------------------------------------------
1. LOAD       — accept a path (cv2/PIL), a numpy HxWx3 (BGR, cv2 convention) or
                HxWx4 array, or raw bytes.  Downsample to <=160px on the long edge.
2. PALETTE    — k-means on the downsampled pixels (sklearn if installed, else a
                dependency-free numpy mini-batch k-means) -> dominant colors with
                pixel-share weights.  We then compute a SALIENCE score per swatch
                (chroma + how far it stands off the image mean) so the livery is
                colored by the photo's MEMORABLE colors — the sunset's amber and
                violet — not just the big neutral sky/asphalt that dominates pixel
                count.  Dominant + accent roles fall out of that ranking.
3. MOOD       — image statistics (luma, saturation, warm/cool temperature,
                contrast, colorfulness) are scored against the SAME curated theme
                library the text feature uses (``engine/livery_themes``) so a photo
                inherits a hand-authored art direction: crown-jewel FINISH ROLES
                (fs_/fm_/chameleon_/prizm_/spectrum_/candy/chrome/pearl) plus the
                multi-zone COMPOSITION (body / feature / accent / number).
4. PHOTO PALETTE -> THEME ROLES — the heart of the upgrade.  We do NOT just recolor
                the theme.  We take the photo's salient colors, HARMONIZE them in
                OKLab, and MAP them onto the chosen theme's role structure: the
                dominant evocative color drives the body, accents drive the
                feature/accent panels, and each color is lightness-shaped so the
                structured crown-jewel finish painted over it actually reveals its
                geometry.  The result is a cohesive livery that EVOKES the image
                while wearing the catalog's best finishes — assembled through the
                designer's OWN ``_compose_design`` so the schema/safety-net zones
                are identical to the text feature.
5. FALLBACK   — if the theme machinery is unavailable for any reason, we fall back
                to the legacy synthetic-prompt path (color words + mood ->
                ``design_from_prompt``) so the module is never dead.

The result is a config that ``shokker_engine_v2.build_multi_zone(..., preview_mode=
True)`` renders without error, identical in shape to a recipe.json ``zoneSnapshot``.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as _np

# Reuse the text feature's machinery + tables.  Import is defensive so a layout
# change can never make this module fail to import.
try:  # pragma: no cover - import shim
    from engine import livery_designer as _ld  # type: ignore
except Exception:  # pragma: no cover
    import livery_designer as _ld  # type: ignore

# The theme library (curated art directions).  Defensive: if it's missing we
# silently drop to the synthetic-prompt fallback.
try:  # pragma: no cover - import shim
    from engine import livery_themes as _themes  # type: ignore
except Exception:  # pragma: no cover
    try:
        import livery_themes as _themes  # type: ignore
    except Exception:
        _themes = None  # type: ignore


# ---------------------------------------------------------------------------
# IMAGE LOADING — path / numpy / bytes -> float RGB array in 0..1, shape (H,W,3)
# ---------------------------------------------------------------------------
def _load_rgb01(src: Union[str, bytes, "_np.ndarray"]) -> _np.ndarray:
    """Return an HxWx3 float32 RGB image in 0..1 from many input shapes.

    Accepts: a filesystem path, raw encoded image bytes, or a numpy array.
    numpy arrays are assumed BGR (the cv2 convention this codebase uses); a 4th
    alpha channel is dropped.  Single-channel arrays are broadcast to 3 channels.
    """
    arr: Optional[_np.ndarray] = None

    if isinstance(src, _np.ndarray):
        arr = src
        if arr.ndim == 2:
            arr = _np.stack([arr] * 3, axis=-1)
        if arr.ndim == 3 and arr.shape[2] == 4:
            arr = arr[:, :, :3]
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"unsupported image array shape {getattr(arr,'shape',None)!r}")
        # numpy input is treated as BGR (cv2) -> flip to RGB.
        arr = arr[:, :, ::-1]
    elif isinstance(src, (bytes, bytearray)):
        arr = _decode_bytes(bytes(src))
    elif isinstance(src, str):
        if not os.path.isfile(src):
            raise FileNotFoundError(f"image not found: {src}")
        arr = _decode_path(src)
    else:
        raise TypeError(f"unsupported image source type {type(src)!r}")

    arr = _np.asarray(arr)
    if arr.dtype.kind in "ui":  # 0..255 ints
        arr = arr.astype(_np.float32) / 255.0
    else:
        arr = arr.astype(_np.float32)
        if float(arr.max() if arr.size else 0.0) > 1.5:  # looks like 0..255 floats
            arr = arr / 255.0
    return _np.clip(arr[:, :, :3], 0.0, 1.0)


def _decode_path(path: str) -> _np.ndarray:
    """Load an on-disk image as RGB uint8 via cv2 then PIL fallback."""
    try:
        import cv2  # type: ignore
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is not None:
            return bgr[:, :, ::-1].copy()  # BGR -> RGB
    except Exception:
        pass
    from PIL import Image  # PIL is an engine dep
    with Image.open(path) as im:
        return _np.asarray(im.convert("RGB"))


def _decode_bytes(data: bytes) -> _np.ndarray:
    """Decode encoded image bytes as RGB uint8 via cv2 then PIL fallback."""
    try:
        import cv2  # type: ignore
        buf = _np.frombuffer(data, dtype=_np.uint8)
        bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if bgr is not None:
            return bgr[:, :, ::-1].copy()
    except Exception:
        pass
    import io
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        return _np.asarray(im.convert("RGB"))


def _downsample(rgb01: _np.ndarray, long_edge: int = 160) -> _np.ndarray:
    """Cheap nearest-neighbour downsample so k-means runs on a few thousand px."""
    h, w = rgb01.shape[:2]
    if max(h, w) <= long_edge:
        return rgb01
    scale = long_edge / float(max(h, w))
    nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
    ys = (_np.linspace(0, h - 1, nh)).astype(_np.int64)
    xs = (_np.linspace(0, w - 1, nw)).astype(_np.int64)
    return rgb01[ys][:, xs]


# ---------------------------------------------------------------------------
# PALETTE — k-means (sklearn if present, else a numpy mini-batch k-means)
# ---------------------------------------------------------------------------
def _kmeans_palette(pixels: _np.ndarray, k: int, seed: int) -> Tuple[_np.ndarray, _np.ndarray]:
    """Return (centers Kx3 in 0..1, weights K summing to 1), most-dominant first.

    Tries sklearn.cluster.KMeans; if unavailable, falls back to ``_mini_batch_kmeans``.
    """
    pixels = pixels.reshape(-1, 3).astype(_np.float32)
    if pixels.shape[0] == 0:
        return _np.zeros((1, 3), _np.float32), _np.ones((1,), _np.float32)
    k = int(max(1, min(k, pixels.shape[0])))
    try:  # pragma: no cover - only when sklearn is installed
        from sklearn.cluster import KMeans  # type: ignore
        km = KMeans(n_clusters=k, n_init=4, random_state=int(seed) & 0x7FFFFFFF)
        labels = km.fit_predict(pixels)
        centers = _np.asarray(km.cluster_centers_, _np.float32)
    except Exception:
        centers, labels = _mini_batch_kmeans(pixels, k, seed)
    counts = _np.bincount(labels, minlength=centers.shape[0]).astype(_np.float32)
    weights = counts / max(1.0, counts.sum())
    order = _np.argsort(-weights)
    return _np.clip(centers[order], 0.0, 1.0), weights[order]


def _mini_batch_kmeans(pixels: _np.ndarray, k: int, seed: int,
                       iters: int = 40, batch: int = 2048) -> Tuple[_np.ndarray, _np.ndarray]:
    """A small, dependency-free mini-batch k-means (Lloyd with sampled batches).

    Returns (centers Kx3, labels for every pixel).  k-means++ style seeding makes
    it deterministic for a given seed and stable across reasonable image sizes.
    """
    rng = _np.random.default_rng(int(seed) & 0x7FFFFFFF)
    n = pixels.shape[0]
    k = int(max(1, min(k, n)))

    # --- k-means++ seeding ---
    centers = _np.empty((k, 3), _np.float32)
    centers[0] = pixels[rng.integers(0, n)]
    d2 = _np.sum((pixels - centers[0]) ** 2, axis=1)
    for c in range(1, k):
        total = float(d2.sum())
        if total <= 1e-12:
            centers[c] = pixels[rng.integers(0, n)]
        else:
            probs = d2 / total
            centers[c] = pixels[rng.choice(n, p=probs)]
        nd2 = _np.sum((pixels - centers[c]) ** 2, axis=1)
        d2 = _np.minimum(d2, nd2)

    # --- mini-batch Lloyd iterations ---
    counts = _np.zeros((k,), _np.float64)
    bsz = int(min(batch, n))
    for _ in range(iters):
        idx = rng.integers(0, n, size=bsz)
        sample = pixels[idx]
        dists = _np.sum((sample[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        lab = _np.argmin(dists, axis=1)
        for c in range(k):
            sel = sample[lab == c]
            if sel.shape[0] == 0:
                continue
            counts[c] += sel.shape[0]
            lr = sel.shape[0] / counts[c]  # per-cluster learning rate
            centers[c] = centers[c] * (1.0 - lr) + sel.mean(axis=0) * lr

    # --- final hard assignment over ALL pixels (for accurate weights) ---
    full = _np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2)
    labels = _np.argmin(full, axis=1).astype(_np.int64)
    return centers.astype(_np.float32), labels


def _merge_near_duplicates(centers: _np.ndarray, weights: _np.ndarray,
                           min_dist: float = 0.06) -> Tuple[_np.ndarray, _np.ndarray]:
    """Merge palette swatches that are nearly identical (sum their weights)."""
    keep_c: List[_np.ndarray] = []
    keep_w: List[float] = []
    for c, w in zip(centers, weights):
        merged = False
        for i, kc in enumerate(keep_c):
            if float(_np.sqrt(_np.sum((kc - c) ** 2))) < min_dist:
                total = keep_w[i] + float(w)
                keep_c[i] = (kc * keep_w[i] + c * float(w)) / max(1e-6, total)
                keep_w[i] = total
                merged = True
                break
        if not merged:
            keep_c.append(c.astype(_np.float32))
            keep_w.append(float(w))
    c_arr = _np.asarray(keep_c, _np.float32)
    w_arr = _np.asarray(keep_w, _np.float32)
    order = _np.argsort(-w_arr)
    return c_arr[order], w_arr[order]


def _swatch_metrics(c01: Sequence[float]) -> Dict[str, float]:
    """Per-swatch perceptual metrics in OKLCh when available, else HSV-ish."""
    r, g, b = float(c01[0]), float(c01[1]), float(c01[2])
    mx, mn = max(r, g, b), min(r, g, b)
    cs = getattr(_ld, "_cs", None)
    if cs is not None:
        try:
            lch = cs.oklab_to_oklch(cs.srgb_to_oklab(
                _np.asarray([[r, g, b]], _np.float32)))[0]
            return {"L": float(lch[0]), "C": float(lch[1]), "H": float(lch[2])}
        except Exception:
            pass
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = (mx - mn) / mx if mx > 1e-6 else 0.0
    # crude hue angle (radians) so callers can still spread hues
    import colorsys
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)
    return {"L": float(luma), "C": float(sat) * 0.4, "H": float(h * 2.0 * _np.pi)}


# ---------------------------------------------------------------------------
# MOOD INFERENCE — image stats -> livery_designer mood / style vocabulary
# ---------------------------------------------------------------------------
def _image_stats(rgb01: _np.ndarray) -> Dict[str, float]:
    """Compute luma, saturation, warm/cool temperature, contrast, colorfulness."""
    px = rgb01.reshape(-1, 3)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx = px.max(axis=1)
    mn = px.min(axis=1)
    sat = _np.where(mx > 1e-6, (mx - mn) / _np.maximum(mx, 1e-6), 0.0)
    # warm/cool: red-vs-blue lean.
    temperature = float(_np.mean(r - b))  # >0 warm, <0 cool, roughly -1..1
    # Hasler-Süsstrunk colorfulness (how vivid/varied the hues are overall).
    rg = r - g
    yb = 0.5 * (r + g) - b
    colorfulness = float(
        _np.sqrt(rg.std() ** 2 + yb.std() ** 2)
        + 0.3 * _np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )
    # Hue SCATTER: how spread the chromatic pixels' hues are around the wheel.
    # An oil-slick / holographic photo has fine multi-hue speckle that k-means
    # averages into muted means (low global colorfulness) but whose per-pixel
    # hues fan across the whole wheel. This catches that "rainbow sheen" case.
    import colorsys as _csys
    chroma = mx - mn
    chromatic = chroma > 0.10
    hue_spread = 0.0
    n_hue_bins = 0
    if int(chromatic.sum()) > 16:
        cpx = px[chromatic]
        # vectorized hue via max-channel formula (avoids per-pixel colorsys)
        cmx = cpx.max(axis=1); cmn = cpx.min(axis=1); dl = _np.maximum(cmx - cmn, 1e-6)
        rr, gg, bb = cpx[:, 0], cpx[:, 1], cpx[:, 2]
        hue = _np.where(cmx == rr, ((gg - bb) / dl) % 6.0,
              _np.where(cmx == gg, (bb - rr) / dl + 2.0, (rr - gg) / dl + 4.0)) / 6.0
        # circular spread = 1 - resultant-vector length (0=one hue, ~1=all hues)
        ang = hue * 2.0 * _np.pi
        rvec = _np.hypot(_np.cos(ang).mean(), _np.sin(ang).mean())
        # TRUE iridescence smears hue across MANY bins (a rainbow), not just two
        # far-apart blocks (a flag). Count how many of 12 hue bins each hold a
        # meaningful share, and gate the spread on that bin-occupancy so a clean
        # red/white/blue (2 bins) does not masquerade as holographic.
        bins = _np.clip((hue * 12).astype(_np.int32), 0, 11)
        bc = _np.bincount(bins, minlength=12).astype(_np.float64)
        bp = bc / max(bc.sum(), 1.0)
        n_bins = int((bp >= 0.04).sum())
        bin_factor = float(min(1.0, max(0.0, (n_bins - 2)) / 4.0))  # 0 at <=2 bins, 1 at >=6
        hue_spread = float((1.0 - rvec) * (chromatic.mean() ** 0.5) * bin_factor)
        n_hue_bins = n_bins
    return {
        "luma": float(_np.mean(luma)),
        "luma_std": float(_np.std(luma)),
        "sat": float(_np.mean(sat)),
        "sat_std": float(_np.std(sat)),
        "temperature": temperature,
        "contrast": float(_np.percentile(luma, 90) - _np.percentile(luma, 10)),
        "colorfulness": colorfulness,
        "hue_spread": hue_spread,
        "hue_bins": float(n_hue_bins),
    }


# The mood words we hand the theme matcher.  Each tuple is (predicate, words).
# The words are real theme synonyms (see engine/livery_themes) so scoring lands
# on a curated art direction.  Order matters: earlier, more specific moods win.
def _mood_words(stats: Dict[str, float], salient: List[Dict]) -> List[str]:
    """Translate image statistics + salient colors into theme-synonym words."""
    luma = stats["luma"]
    sat = stats["sat"]
    temp = stats["temperature"]
    contrast = stats["contrast"]
    cf = stats["colorfulness"]
    hue_spread = stats.get("hue_spread", 0.0)

    words: List[str] = []

    # --- SALIENT-COLOR statistics: what colors actually carry the photo's
    # identity (the neon signs on a black street, the sun in a grey sky)?  These
    # are far more reliable than global averages, which a dominant neutral
    # background can wash out. ---
    sw_top = [s for s in salient[:5]]
    chromas = [s["C"] for s in sw_top]
    peak_chroma = max(chromas) if chromas else 0.0
    n_colorful = sum(1 for c in chromas if c > 0.10)
    # Hue is reported by ``_swatch_metrics`` as an OKLCh angle (when
    # color_science is present), whose boundaries differ a LOT from HSV — in
    # OKLCh red~0-40, orange~40-72, yellow/gold/amber~72-112, lime~112-140,
    # green~140-185, teal/cyan~185-220, blue~220-285, violet~285-322,
    # magenta/pink~322-360. Classifying with HSV boundaries was making warm
    # gold read as "green" (the fire-vs-viper bug). One OKLCh-correct family
    # map is used for every hue decision below.
    def _deg(s):
        return (s.get("H", 0.0) * 180.0 / _np.pi) % 360.0

    def _hue_family(deg: float) -> str:
        if deg < 40 or deg >= 350:
            return "red"
        if deg < 72:
            return "orange"
        if deg < 112:
            return "yellow"      # gold / amber live here in OKLab
        if deg < 140:
            return "lime"
        if deg < 185:
            return "green"
        if deg < 220:
            return "teal"
        if deg < 285:
            return "blue"
        if deg < 322:
            return "violet"
        return "magenta"

    # distinct hue FAMILIES among the chromatic swatches (semantic, not /45 bins).
    hue_fams = set(_hue_family(_deg(s)) for s in sw_top if s["C"] > 0.09)
    WARM_FAMS = {"red", "orange", "yellow"}
    GREEN_FAMS = {"lime", "green"}
    BLUE_FAMS = {"teal", "blue"}            # the families that read as WATER
    PURPLE_FAMS = {"violet", "magenta"}     # jewel-tone purples/magentas
    warm_hue = bool(hue_fams & WARM_FAMS)
    green_hue = bool(hue_fams & GREEN_FAMS)
    blue_hue = bool(hue_fams & BLUE_FAMS)
    purple_hue = bool(hue_fams & PURPLE_FAMS)

    very_dark = luma < 0.24
    dark = luma < 0.40
    bright = luma > 0.70
    # "vivid" now also fires on a dark scene whose SALIENT colors are electric
    # (neon-on-black) — global sat/cf understate that case.
    vivid = sat > 0.45 or cf > 0.45 or (peak_chroma > 0.16 and n_colorful >= 1)
    # true monochrome / metallic-neutral: almost no color anywhere.
    monochrome = (cf < 0.06 and peak_chroma < 0.07)
    # METALLIC / INDUSTRIAL: a near-neutral surface (low chroma everywhere) that
    # nonetheless has real LIGHT structure — brushed steel, gunmetal plate, a
    # machined part. Distinct from a flat monochrome wall (no structure) and from
    # a colorful scene. Drives the chrome/titanium/gunmetal/damascus art
    # directions instead of leaking to generic gloss.
    low_chroma = (cf < 0.14 and peak_chroma < 0.13 and n_colorful <= 1)
    metallic = low_chroma and not monochrome and (contrast > 0.20 or stats.get("luma_std", 0.0) > 0.10)
    warm = temp > 0.05
    cool = temp < -0.05
    high_contrast = contrast > 0.55
    # PASTEL / ORGANIC SOFT: a bright, low-saturation, gentle-contrast image whose
    # colors are soft tints (lavender / blush / mint / cream) — route to pearl /
    # elegant / cotton-candy rather than a punchy neon or candy theme.
    pastel = (bright and sat < 0.34 and cf < 0.30 and contrast < 0.45
              and peak_chroma < 0.16 and not metallic and not monochrome)
    # NEON POP = MULTIPLE distinct electric colors on a dark stage (a neon street,
    # an arcade) — hot pink + cyan + violet, not one saturated hue and not a band
    # of ADJACENT shades. The signature is at least one ELECTRIC-cool family
    # (cyan/teal/blue/violet/magenta) AND >=2 families spanning a real chunk of
    # the wheel. This separates a true neon scene from a dark-but-single-subject
    # image: a saturated FOREST reads as {green, lime} (adjacent, no electric-cool
    # family) and a fire reads warm-only — neither should masquerade as synthwave.
    _electric_fams = {"teal", "blue", "violet", "magenta"}
    _FAM_ORDER = {"red": 0, "orange": 1, "yellow": 2, "lime": 3, "green": 4,
                  "teal": 5, "blue": 6, "violet": 7, "magenta": 8}

    def _hue_family_span(fams) -> int:
        """Wheel distance between the most-separated families (0=one family).
        Adjacent shades (green+lime) span ~1; opposite neon (magenta+teal) ~3+."""
        idx = sorted(_FAM_ORDER[f] for f in fams if f in _FAM_ORDER)
        if len(idx) < 2:
            return 0
        # circular span of 9 families: max gap accounting for wrap-around.
        spans = [b - a for a, b in zip(idx, idx[1:])]
        spans.append(idx[0] + 9 - idx[-1])
        return 9 - max(spans)

    # Standard case: several distinct electric colors well-separated on the wheel.
    neon_pop = (peak_chroma > 0.16 and n_colorful >= 2 and dark
                and len(hue_fams) >= 2
                and bool(hue_fams & _electric_fams)
                and _hue_family_span(hue_fams) >= 3)
    # Deep-dark electric case: vivid saturated color glowing on near-black is
    # unmistakably a neon / synthwave look even if k-means muted the speckle into
    # adjacent cool families (violet+magenta+blue). A WARM-dominant deep scene is
    # still a fire/ember (handled below), so this fires only when the electric
    # cool families carry the scene. CRUCIALLY it requires >=2 distinct hue
    # FAMILIES: a neon street is many electric colors, whereas a single deep,
    # saturated jewel-tone (a royal-purple field — all swatches one violet family)
    # is NOT neon and must be free to read as its true color (Purple Reign). The
    # old gate only counted colorful SWATCHES, so several shades of one violet
    # (n_colorful>=2 but one family) wrongly masqueraded as synthwave.
    if (not neon_pop and very_dark and sat > 0.55 and peak_chroma > 0.15
            and n_colorful >= 2 and len(hue_fams) >= 2
            and bool(hue_fams & _electric_fams) and not warm):
        neon_pop = True

    # ...but a TRUE oil-slick / holographic sheen is a fine rainbow smeared across
    # the WHOLE wheel — a far higher hue_spread + bin-occupancy than a neon street
    # of a few discrete blobs (oil slick ~0.6 over 12 bins vs a neon street ~0.11
    # over a handful). When the speckle is unmistakably a full-wheel rainbow, it is
    # iridescent, not neon, so stand neon_pop down and let the iridescent branch
    # below claim it (routing to the spectral/oil-slick crown jewels).
    if neon_pop and stats.get("hue_spread", 0.0) > 0.40 and stats.get("hue_bins", 0.0) >= 8:
        neon_pop = False

    # --- IRIDESCENT / OIL-SLICK: fine multi-hue speckle that fans across the
    # whole color wheel (a holographic sheen, a gasoline rainbow, a beetle
    # shell). Detected via hue_spread so it survives k-means averaging the
    # speckle into muted means. Routes to the spectral crown jewels. ---
    # Iridescent = a real rainbow at FINE scale (oil slick / holographic sheen):
    # high circular hue spread that survives the bin-occupancy gate baked into
    # hue_spread. A smooth sunset GRADIENT also touches many hue bins but its
    # hues vary slowly/coherently (low hue_spread ~0.1), so it is NOT caught
    # here — only genuinely scattered multi-hue speckle (hue_spread >~0.22) is.
    # A dark scene of DISCRETE bright multi-color blobs (neon_pop) shares the high
    # hue_spread of an oil slick, but it is a neon street, not a gasoline sheen —
    # let neon_pop claim it (handled just below) instead of routing to oilslick.
    iridescent = ((hue_spread > 0.22 and not monochrome) or cf > 0.60) and not neon_pop
    if iridescent:
        if dark:
            words += ["oilslick", "oil", "petrol", "iridescent", "rainbow", "beetle"]
        else:
            words += ["holographic", "prismatic", "iridescent", "spectrum", "rainbow"]

    # --- MONOCHROME first: a near-colorless photo is about light + finish, never
    # a hue. Route by lightness to clean elegant / chrome / stealth. ---
    if monochrome:
        if bright:
            words += ["elegant", "pearl", "clean", "chrome"]
        elif very_dark:
            words += ["stealth", "carbon", "blackout", "matte"]
        else:
            words += ["chrome", "liquid", "metallic", "silver"]
        if high_contrast:
            words += ["damascus", "steel"]  # high-contrast mono -> watered steel
        seen: set = set()
        return [w for w in words if not (w in seen or seen.add(w))]

    # --- METALLIC / INDUSTRIAL: brushed/forged near-neutral metal with light
    # structure. Route by lightness + warmth: cool steel -> liquid chrome /
    # gunmetal; a warm tint -> burnt titanium / copper; high-contrast -> damascus.
    # This is BEFORE the colored-mood branches so a steel photo never reads as a
    # faint-blue "ocean". ---
    if metallic:
        words += ["metallic", "machined", "industrial"]
        if very_dark:
            words += ["gunmetal", "carbon", "stealth"]
        elif warm:
            words += ["titanium", "anodized", "tempered", "copper"]
        else:
            words += ["chrome", "liquid", "silver", "steel"]
        if high_contrast or contrast > 0.45:
            words += ["damascus", "forged", "metalgrain"]
        seen_m: set = set()
        return [w for w in words if not (w in seen_m or seen_m.add(w))]

    # --- NEON POP: dark scene lit by multiple electric colors -> synthwave /
    # carnival / electric bloom (hot pink + cyan + violet). Checked before the
    # ocean/abyss branch so a neon street doesn't read as "deep water". ---
    if neon_pop:
        words += ["neon", "electric", "synthwave", "vaporwave", "carnival"]
        if len(hue_fams) >= 3 or peak_chroma > 0.24:
            words += ["rave", "glow"]

    # --- headline mood from the global statistics ---
    # Sunset/fire require the warmth to come from ACTUAL warm salient colors, not
    # just a slightly-warm average over a green/blue scene.
    #
    # Sunset-vs-fire must NOT hinge on the GLOBAL mean luma alone: a real sunset
    # photo is globally dim (a dark sky fills most of the frame) yet its HERO is a
    # bright warm sun/horizon — gating "sunset" on luma>0.40 mislabels it a "fire".
    # The honest signal is the lightness of the photo's DOMINANT warm color
    # (presence-weighted), NOT the single brightest pixel: a fire scene's only
    # bright warm tone is a tiny sparse ember (high L but ~3% area) over near-black
    # dark-warm coals (the real dominant), while a sunset's amber sun/horizon is
    # itself a broad, LIGHT, present region. So measure the warm hero by the
    # most-salient warm swatch, and treat a near-black overall scene as fire.
    _warm_sw = sorted([s for s in salient[:5]
                       if s["C"] >= 0.08 and _hue_family(_deg(s)) in WARM_FAMS],
                      key=lambda s: -s["salience"])
    warm_hero_L = _warm_sw[0]["L"] if _warm_sw else 0.0
    if vivid and warm and warm_hue and not green_hue and not neon_pop:
        if very_dark:
            words += ["fire", "ember", "molten"]   # near-black warm scene -> inferno
        elif warm_hero_L >= 0.52 or luma > 0.40:
            words += ["sunset", "warm", "golden"]  # bright dominant warm hero -> sunset
        else:
            words += ["fire", "ember", "molten"]   # dim, dark-warm dominant -> inferno
    if vivid and cool and luma > 0.45 and not neon_pop and not purple_hue:
        words += ["neon", "electric", "synthwave"] # bright cool vivid -> neon/synthwave
    # DEEP OCEAN is specifically dark saturated BLUE/TEAL water — gate it on a
    # blue/teal hero so a deep VIOLET (a royal purple, an amethyst night) is not
    # dragged to "ocean". A violet-only dark scene routes to the purple headline
    # just below instead. NOTE: deep water is DARK, where OKLab chroma collapses
    # below the 0.09 hue_fams floor even though the pixel is unmistakably blue, so
    # we read the dominant cool hue with a RELAXED chroma floor (and confirm it is
    # blue/teal, not violet) rather than trusting hue_fams here.
    _cool_sw = sorted([s for s in salient[:5] if s["C"] >= 0.04],
                      key=lambda s: -s["salience"])
    _cool_blue = bool(_cool_sw and _hue_family(_deg(_cool_sw[0])) in BLUE_FAMS)
    if (cool and dark and sat > 0.30 and not neon_pop and not green_hue
            and (blue_hue or _cool_blue) and not (purple_hue and not blue_hue)):
        words += ["ocean", "deep", "abyss"]        # dark saturated blue -> deep ocean
    # ROYAL PURPLE / AMETHYST: a saturated violet/magenta-dominant scene with no
    # competing warm/green/blue hero -> purple reign / amethyst (a real jewel
    # tone), instead of leaking to neon or ocean. Brightness-agnostic: a deep
    # plum and a bright orchid are both "purple". Uses a relaxed-chroma dominant
    # hue read too (dark plums lose OKLab chroma) so a midnight amethyst still
    # reads purple rather than slipping to the ocean branch.
    _cool_purple = bool(_cool_sw and _hue_family(_deg(_cool_sw[0])) in PURPLE_FAMS)
    if ((purple_hue or (_cool_purple and not _cool_blue)) and not warm_hue
            and not green_hue and not blue_hue
            and (sat > 0.30 or peak_chroma > 0.13) and not neon_pop):
        words += ["purple", "violet", "amethyst"]
    # GREEN NATURE: a chromatic green-dominant scene (forest, foliage, jungle) ->
    # emerald/serpent/jungle. Dark + saturated greens read deep-emerald; brighter
    # mixed greens read jungle. Kept off neon_pop so a neon scene isn't dragged.
    if green_hue and not warm_hue and (sat > 0.28 or peak_chroma > 0.12) and not neon_pop:
        if dark:
            words += ["emerald", "serpent", "viper", "jungle", "forest"]
        else:
            words += ["jungle", "wild", "green", "emerald", "tropical"]
    # PASTEL / SOFT-ORGANIC: gentle bright tints -> elegant pearl / cotton-candy /
    # rose-gold by the dominant soft hue. Checked before "ice" so a warm/pink
    # pastel doesn't get dragged cold, and gated so a vivid scene never lands here.
    if pastel and not vivid and not neon_pop:
        if warm_hue or (warm and not green_hue):
            words += ["cottoncandy", "pastel", "rosegold", "blush", "soft", "elegant"]
        elif green_hue:
            words += ["pastel", "mint", "soft", "elegant", "pearl"]
        else:
            words += ["pastel", "cottoncandy", "soft", "dreamy", "pearl", "elegant"]
    if cool and not dark and sat < 0.45 and not vivid and not pastel:
        words += ["ice", "frost", "arctic"]        # bright cool low-sat -> arctic ice
    if very_dark and not vivid and not neon_pop:
        words += ["midnight", "shadow", "night"]

    # --- per-salient-swatch hue nudges so a rich photo gets varied finishes ---
    # During neon_pop we keep the synthwave headline dominant and only let the
    # single MOST chromatic swatch add a hue accent, so a neon street doesn't get
    # dragged to a literal "blue"/"green" single-color theme.
    #
    # The same containment must protect ANY strong headline: when a clear scene
    # mood already fired (sunset/fire/ocean/green/etc.), a MINORITY color must not
    # add enough hue synonyms to out-score the headline theme. A sunset's small
    # violet sky was injecting purple/violet/amethyst (3 strong synonyms) and
    # hijacking the match to "Purple Reign" away from the warm headline. So once a
    # headline has spoken, only the single MOST-SALIENT swatch (the body — the
    # color that actually drives the livery) is allowed to nudge the hue; the
    # secondary colors still reach the PALETTE (fidelity is untouched), they just
    # can't reroute the art direction. With no headline we keep the full 4-swatch
    # spread so a multi-color photo still gets a varied, rich finish set.
    _headline_set = {"sunset", "fire", "ember", "molten", "ocean", "deep", "abyss",
                     "emerald", "serpent", "viper", "jungle", "forest", "green",
                     "ice", "frost", "arctic", "midnight", "shadow", "night",
                     "cottoncandy", "pastel", "mint", "rosegold",
                     "purple", "violet", "amethyst"}
    _has_headline = bool(set(words) & _headline_set)
    if neon_pop:
        # neon: the single most CHROMATIC sign adds one hue accent (unchanged).
        hue_swatches = sorted([s for s in salient[:4] if s["C"] >= 0.07],
                              key=lambda s: -s["C"])[:1]
    elif _has_headline:
        # headline spoke: only the body (most-salient) color may nudge the hue, so
        # a minority swatch can't reroute the theme away from the scene mood.
        hue_swatches = sorted([s for s in salient[:4] if s["C"] >= 0.07],
                              key=lambda s: -s["salience"])[:1]
    else:
        hue_swatches = salient[:4]
    for sw in hue_swatches:
        L, C = sw["L"], sw["C"]
        if C < 0.07:
            continue  # near-neutral, no hue signal
        fam = _hue_family(_deg(sw))
        if fam == "orange":
            words += ["amber", "copper"]
        elif fam == "yellow":
            words += ["gold", "golden"]
        elif fam == "lime":
            words += ["lime", "viper"]
        elif fam == "green":
            words += ["green", "emerald"] if L < 0.62 else ["lime", "viper"]
        elif fam == "teal":
            words += ["teal", "ocean"]
        elif fam == "blue":
            words += ["blue", "cobalt", "sapphire"]
        elif fam == "violet":
            words += ["purple", "violet", "amethyst"]
        elif fam in ("magenta", "red"):
            words += ["crimson", "blood"] if L < 0.45 else ["pink", "magenta"]

    # high contrast only reads "aggressive" when there's also real color; a
    # high-contrast neutral is handled by the monochrome branch above.
    if high_contrast and (sat > 0.30 or peak_chroma > 0.14) and not neon_pop:
        words += ["aggressive", "bold"]
    if (cf > 0.55 or len(hue_fams) >= 3) and "iridescent" not in words:
        words += ["iridescent", "holographic", "prismatic"]  # many hues -> spectral

    if not words:
        words += ["gloss", "clean"]

    # de-dup preserving order
    seen2: set = set()
    return [w for w in words if not (w in seen2 or seen2.add(w))]


# ---------------------------------------------------------------------------
# COLOR -> NEAREST NAMED COLOR (reuses livery_designer._COLOR_NAMES)
# ---------------------------------------------------------------------------
def _nearest_color_word(rgb255: Tuple[int, int, int]) -> str:
    """Return the livery_designer color-name word closest to ``rgb255`` in OKLab.

    Falls back to a plain RGB distance if color_science is unavailable.
    """
    table = getattr(_ld, "_COLOR_NAMES", {})
    if not table:
        return "gray"
    target = _np.array([[c / 255.0 for c in rgb255]], dtype=_np.float32)

    cs = getattr(_ld, "_cs", None)
    use_lab = cs is not None
    tlab = None
    if use_lab:
        try:
            tlab = cs.srgb_to_oklab(target)[0]
        except Exception:
            use_lab = False

    best_word = "gray"
    best_d = 1e9
    for word, rgb in table.items():
        cand = _np.array([[c / 255.0 for c in rgb]], dtype=_np.float32)
        if use_lab and tlab is not None:
            try:
                clab = cs.srgb_to_oklab(cand)[0]
                d = float(_np.sum((clab - tlab) ** 2))
            except Exception:
                d = float(_np.sum((cand[0] - target[0]) ** 2))
        else:
            d = float(_np.sum((cand[0] - target[0]) ** 2))
        if d < best_d:
            best_d = d
            best_word = word
    return best_word


def _rgb255(c01: Sequence[float]) -> Tuple[int, int, int]:
    return (
        int(max(0, min(255, round(float(c01[0]) * 255)))),
        int(max(0, min(255, round(float(c01[1]) * 255)))),
        int(max(0, min(255, round(float(c01[2]) * 255)))),
    )


def _hex(rgb255: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % (rgb255[0], rgb255[1], rgb255[2])


# ---------------------------------------------------------------------------
# PHOTO PALETTE -> THEME ROLE COLORS  (the "evokes the image" heart)
# ---------------------------------------------------------------------------
def _theme_role_palette(theme: Dict,
                        salient: List[Dict],
                        stats: Dict[str, float]) -> List[Tuple[int, int, int]]:
    """Build the palette that the theme's roles will wear, FROM the photo.

    The theme defines a role->palette-index structure and an authored lightness
    intent for each slot.  We keep that intent (so a "body" slot stays a broad
    mid color and an "accent" slot stays a punchy pop) but PAINT it with the
    photo's salient colors — dominant color -> body, brightest/most chromatic
    accents -> feature/accent — re-lit to the theme slot's target lightness in
    OKLab so the crown-jewel finish over it reveals its geometry.  Everything is
    then perceptually spaced via the designer's own ``_harmonize_palette`` so the
    set always reads as a designed, cohesive livery rather than a raw dump.
    """
    theme_pal = [tuple(int(c) for c in rgb) for rgb in theme.get("palette", [])]
    n = max(len(theme_pal), 3)

    cs = getattr(_ld, "_cs", None)

    # Photo colors as OKLCh (or HSV-approx) — most salient first.
    photo = list(salient)
    if not photo:
        return theme_pal

    # Slot target lightness from the AUTHORED theme palette (its design intent).
    def slot_L(i: int) -> float:
        if i < len(theme_pal) and cs is not None:
            try:
                lch = cs.oklab_to_oklch(cs.srgb_to_oklab(
                    _np.asarray([[c / 255.0 for c in theme_pal[i]]], _np.float32)))[0]
                return float(lch[0])
            except Exception:
                pass
        # graceful default ladder if no color_science: body mid, others spread
        return [0.42, 0.62, 0.78, 0.30][i % 4]

    # Pick which photo color drives each slot, deliberately keeping the three
    # role colors PERCEPTUALLY DISTINCT so the multi-zone livery reads as an
    # intentional composition (body / hero feature / accent), not a one-color
    # wash. Every pick still comes FROM the photo, so fidelity survives.
    #   slot 0 (body)    <- most salient color (the photo's headline color)
    #   slot 1 (feature) <- the chromatic color most DIFFERENT from the body
    #   slot 2 (accent)  <- a punchy color distinct from BOTH body and feature
    by_salience = photo
    body_src = by_salience[0]

    def hue_dist(a, b):
        d = abs(((a.get("H", 0.0) - b.get("H", 0.0)) + _np.pi) % (2 * _np.pi) - _np.pi)
        return float(d)

    def diff_score(s, refs):
        """How perceptually different is swatch ``s`` from every ref already
        chosen? Rewards hue separation (when both carry chroma) and lightness
        separation, plus the swatch's own chroma so a vivid pop wins ties."""
        if not refs:
            return s["C"]
        worst_h = min((hue_dist(s, r) / _np.pi) if (s["C"] > 0.06 and r["C"] > 0.06)
                      else 0.0 for r in refs)
        worst_l = min(abs(s["L"] - r["L"]) for r in refs)
        return 0.55 * worst_h + 0.45 * worst_l + 0.30 * s["C"]

    # feature: maximize chroma + difference from the body.
    feat_candidates = sorted(
        photo, key=lambda s: -(s["C"] * 0.6 + diff_score(s, [body_src]) * 1.0))
    feature_src = feat_candidates[0] if feat_candidates else body_src
    # accent: maximize difference from BOTH body and feature (a real third color).
    acc_candidates = sorted(
        photo, key=lambda s: -diff_score(s, [body_src, feature_src]))
    accent_src = acc_candidates[0] if acc_candidates else feature_src

    sources = [body_src, feature_src, accent_src]

    def relight(src: Dict, target_L: float, is_body: bool) -> Tuple[int, int, int]:
        """Recolor a photo swatch to a slot's target lightness, keeping its hue +
        as much chroma as the photo offers (so the livery still reads as the
        photo's color)."""
        if cs is None:
            # luma-scale fallback
            rgb = src.get("rgb255")
            if rgb is None:
                return (40, 44, 52)
            lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0
            k = (target_L) / max(0.05, lum)
            return tuple(int(max(0, min(255, round(c * k)))) for c in rgb)
        L, C, H = src["L"], src["C"], src.get("H", 0.0)
        # Body wants real area-color presence: lean toward the PHOTO's own
        # lightness so the car reads as the photo's color, but still pull toward
        # the slot intent enough that a structured finish has light to reveal its
        # geometry. Feature/accent lean a bit harder on the slot intent (they are
        # the designed pops). Then enforce an OKLab floor so dark hero colors
        # aren't crushed to unreadable black under fs_/prizm_/etc. finishes.
        wL = 0.38 if is_body else 0.6
        outL = float(_np.clip(L * (1.0 - wL) + target_L * wL, 0.06, 0.95))
        if is_body:
            outL = max(outL, 0.20)   # never crush the area color to near-black
        # keep the photo's chroma (the whole point — fidelity), only lifting a
        # muddy near-gray a touch so it doesn't read as flat lifeless gray.
        outC = C if C > 0.04 else 0.06
        try:
            lab = cs.oklch_to_oklab(_np.asarray([[outL, outC, H]], _np.float32))
            out = cs.oklab_to_srgb(lab)[0]
            return _rgb255(out)
        except Exception:
            return src.get("rgb255", (40, 44, 52))

    palette: List[Tuple[int, int, int]] = []
    for i in range(n):
        src = sources[i] if i < len(sources) else photo[i % len(photo)]
        is_body = (i == 0)
        palette.append(relight(src, slot_L(i), is_body))

    # Perceptually space the result via the designer's own harmonizer.
    try:
        palette = _ld._harmonize_palette(palette)
    except Exception:
        pass
    return palette


def _rank_themes_by_words(words: List[str]) -> List[Tuple[float, Dict]]:
    """Score the mood words against the theme library using the designer's own
    scorer so photo-matching is consistent with text-matching."""
    if _themes is None:
        return []
    prompt = " ".join(words)
    try:
        return _ld._rank_themes(prompt)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# FINISH COLOR-TEMPERATURE GUARD  (the "a fire photo MUST make a fiery car" fix)
# ---------------------------------------------------------------------------
# Some crown-jewel color-SHIFT finishes render their OWN physically-derived color
# regardless of the body color we pass (Fractured Minds fm_* especially). A few
# of those sit in WARM-named theme roles (Inferno / Phoenix / Solar Forge) yet
# render COOL blue-violet on the car — so a fire photo produced a BLUE car. We
# cannot edit the theme library here, so this guard runs AFTER the theme composes
# its zones: when the photo's mood is unambiguously WARM, any body/feature finish
# whose ACTUAL render is cool (verified offline against the booted engine on
# 2026-06-13) is swapped for a registry-live finish that renders warm. Narrow,
# additive, and a no-op for every cool/neutral mood and every honoring finish.
#
# IDs verified to render COOL (mean R < B) despite warm theme intent:
_COOL_RENDERING_WARM_ROLE = {
    "fm_inferno_veins", "fm_flame_wall", "fm_magma", "fm_flame_helix",
    "demon_forge", "cc_blood_orange",
}
# Warm-rendering replacements, ranked; first registry-live one wins. Each was
# verified to render warm (mean R > B) on a neutral swatch.
_WARM_FIRE_FINISHES = [
    "fractal_liquid_fire", "grad_copper_flame", "prizm_copper_flame",
    "spectrum_forge_heat", "cx_sunset_horizon", "grad_sunset",
    "candy_apple", "ember_glow",
]


def _mood_is_warm(mood: List[str]) -> bool:
    warm = {"fire", "ember", "molten", "sunset", "amber", "copper", "gold",
            "golden", "phoenix", "lava", "inferno", "blaze", "forge"}
    cool = {"ice", "frost", "arctic", "ocean", "deep", "abyss", "neon", "synthwave",
            "midnight", "blue", "cobalt", "teal", "emerald", "green", "viper"}
    ms = set(mood)
    return bool(ms & warm) and not bool(ms & cool)


def _reconcile_finish_temperature(zones: List[Dict], mood: List[str],
                                  mono_set, base_set) -> int:
    """Swap cool-rendering finishes out of body/feature zones when the photo mood
    is clearly WARM (fire/sunset). Returns the number of zones changed. NEVER
    raises and never touches non-color or accent/number zones."""
    if not _mood_is_warm(mood):
        return 0

    def _live(fid: str) -> bool:
        if mono_set is None and base_set is None:
            return True  # engine not booted: trust the curated list
        return (mono_set is not None and fid in mono_set) or \
               (base_set is not None and fid in base_set)

    repl = next((f for f in _WARM_FIRE_FINISHES if _live(f)), None)
    if repl is None:
        return 0
    repl_is_mono = (mono_set is None) or (repl in (mono_set or set()))

    changed = 0
    for z in zones:
        if not isinstance(z, dict) or z.get("colorMode") != "multi":
            continue
        name = str(z.get("name", "")).lower()
        # only the broad area zones — the body + the hero feature, not small accents
        if not ("body" in name or "feature" in name or "hood" in name or "roof" in name):
            continue
        cur = z.get("finish") or z.get("base")
        if cur not in _COOL_RENDERING_WARM_ROLE:
            continue
        if repl_is_mono:
            z["finish"] = repl
            z["base"] = None
        else:
            z["base"] = repl
            z["finish"] = None
        changed += 1
    return changed


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def design_from_image(image_bgr_or_path: Union[str, bytes, "_np.ndarray"],
                      seed: int = 51,
                      max_colors: int = 6,
                      car_colors=None) -> Dict:
    """Extract a palette + mood from an image and build a multi-zone livery.

    Args:
        image_bgr_or_path: a filesystem path, raw encoded image bytes, or a numpy
            HxWx3 (BGR, cv2 convention) / HxWx4 array.
        seed: deterministic seed.
        max_colors: max dominant colors to extract (clamped to 3..6).
        car_colors: OPTIONAL dominant colors of the LOADED car paint (same shape
            ``design_from_prompt`` accepts). When provided, the PHOTO-derived
            finishes are MAPPED onto the car's real regions so the livery covers
            and transforms the loaded car — the same coverage fix as the text
            feature. ``None`` keeps the legacy photo-palette-selector behavior.

    Returns:
        ``{"zones": [...], "explanation": "...", "palette": [...], "_meta": {...}}``

        * ``zones`` — shaped for ``shokker_engine_v2.build_multi_zone(...,
          preview_mode=True)``; real crown-jewel catalog finishes, colored by the
          photo's harmonized palette, plus the standard Number/Art/Sponsor +
          'Everything Else' safety-net zones.
        * ``palette`` — ``[{"hex","rgb","weight","name","salience","role"}, ...]``
          most-salient first.
    """
    try:
        seed_int = int(seed)
    except (TypeError, ValueError):
        seed_int = 51

    k = int(max(3, min(6, max_colors)))

    rgb01 = _load_rgb01(image_bgr_or_path)
    small = _downsample(rgb01, long_edge=160)
    stats = _image_stats(small)

    centers, weights = _kmeans_palette(small, k=k, seed=seed_int)
    centers, weights = _merge_near_duplicates(centers, weights, min_dist=0.06)

    # Drop trivially tiny clusters (<2.5% of pixels) but always keep at least 3.
    if centers.shape[0] > 3:
        mask = weights >= 0.025
        if int(mask.sum()) >= 3:
            centers, weights = centers[mask], weights[mask]
            weights = weights / max(1e-6, float(weights.sum()))

    # --- SALIENCE: which colors would a HUMAN name from this photo? Not the big
    # muddy average sky/asphalt, and not a one-pixel speckle either — the colors
    # that are both reasonably PRESENT and perceptually MEMORABLE (chromatic +
    # standing off the scene's average). We score in OKLab so "standout" is a
    # perceptual distance, and we weight CHROMA difference more than luminance
    # difference (a bright sky "stands out" by luminance, but the amber sun is the
    # color you'd name). A gentle sqrt on presence keeps a real hero REGION ahead
    # of incidental speckle without letting a big neutral background dominate. ---
    flat = small.reshape(-1, 3)
    mean_rgb = flat.mean(axis=0)
    mean_m = _swatch_metrics(mean_rgb)
    enriched: List[Dict] = []
    for c, w in zip(centers, weights):
        m = _swatch_metrics(c)
        # perceptual standout: chroma gap weighted 2x the lightness gap, plus the
        # hue's own distance from the (often-neutral) scene mean hue.
        dL = abs(m["L"] - mean_m["L"])
        dC = abs(m["C"] - mean_m["C"])
        # hue standout only counts when BOTH this swatch and the mean carry chroma.
        dH = 0.0
        if m["C"] > 0.05 and mean_m["C"] > 0.04:
            dH = abs(((m["H"] - mean_m["H"] + _np.pi) % (2 * _np.pi)) - _np.pi) / _np.pi
        standout = float(2.0 * dC + 0.6 * dL + 0.25 * dH)
        presence = float(_np.sqrt(max(0.0, w)))  # compress big neutrals' lead
        # chroma is the headline term — the photo's NAMED colors are its vivid
        # ones; presence keeps a hero region ahead of a single noisy speckle.
        salience = float(0.30 * presence + 1.05 * m["C"] + 0.55 * standout)
        rgb = _rgb255(c)
        enriched.append({
            "rgb01": _np.asarray(c, _np.float32),
            "rgb255": rgb,
            "hex": _hex(rgb),
            "weight": float(w),
            "L": m["L"], "C": m["C"], "H": m["H"],
            "salience": salience,
        })

    # Two orderings: dominant (by pixel weight) for the visible palette swatches,
    # salient (by salience) for which colors drive the livery roles.
    dominant = sorted(enriched, key=lambda e: -e["weight"])
    salient = sorted(enriched, key=lambda e: -e["salience"])

    mood = _mood_words(stats, salient)
    ranked = _rank_themes_by_words(mood)

    # Map the photo's finishes onto the LOADED car's REAL regions when the caller
    # passed the loaded paint's dominant colors (the coverage fix). Built once and
    # shared by both the theme path and the synthetic-prompt fallback.
    try:
        car_plan = _ld._car_color_plan(car_colors)
    except Exception:
        car_plan = None
    car_mapped = car_plan is not None

    # ---- PRIMARY PATH: map the photo palette onto a matched theme's roles. ----
    used_theme = None
    used_path = "theme"
    role_palette: List[Tuple[int, int, int]] = []
    if _themes is not None:
        if ranked:
            theme = ranked[0][1]
            theme_score = ranked[0][0]
        else:
            theme = _ld._default_theme()
            theme_score = 0.0
        if theme is not None:
            used_theme = theme
            mono_set, base_set = _ld._live_registries()
            role_palette = _theme_role_palette(theme, salient, stats)
            try:
                zones, descriptions, number_rgb = _ld._compose_design(
                    theme, role_palette, hints=[], mono_set=mono_set, base_set=base_set,
                    car_plan=car_plan)
            except TypeError:  # pragma: no cover - engine predates car_plan
                zones, descriptions, number_rgb = _ld._compose_design(
                    theme, role_palette, hints=[], mono_set=mono_set, base_set=base_set)
            # Guard: a fire/sunset photo must produce a WARM car even if the
            # matched theme assigned a finish that renders cool on the car.
            try:
                _reconcile_finish_temperature(zones, mood, mono_set, base_set)
            except Exception:
                pass
        else:
            used_path = "prompt"
    else:
        used_path = "prompt"

    # ---- FALLBACK PATH: legacy synthetic-prompt -> design_from_prompt. ----
    if used_path == "prompt":
        color_words = [_nearest_color_word(d["rgb255"]) for d in dominant[:4]]
        prompt = (" ".join(mood[:2]) + " " + " ".join(color_words) + " " + " ".join(mood[2:5])).strip()
        if not prompt:
            prompt = "gloss"
        try:
            designed = _ld.design_from_prompt(prompt, seed=seed_int, car_colors=car_colors)
        except TypeError:  # pragma: no cover - engine predates car_colors
            designed = _ld.design_from_prompt(prompt, seed=seed_int)
        zones = list(designed.get("zones", []))
        # Recolor body zones to the salient palette so the swatch still EVOKES the
        # photo. When the design was mapped onto the loaded car, the zone SELECTOR
        # (z["color"]) is now the car's region and MUST NOT be clobbered — only the
        # picker swatch is updated; otherwise we'd re-break coverage.
        body_idx = 0
        for z in zones:
            is_body = (isinstance(z, dict) and z.get("colorMode") == "multi"
                       and (z.get("finish") or z.get("base")) and isinstance(z.get("color"), list))
            if not is_body or body_idx >= len(salient):
                continue
            rgb = salient[body_idx]["rgb255"]
            hexv = salient[body_idx]["hex"]
            if not car_mapped:
                sel = [{"color_rgb": list(rgb), "tolerance": 40, "hex": hexv}]
                z["color"] = sel; z["colors"] = list(sel)
                z["pickerTolerance"] = 40
            z["pickerColor"] = hexv
            body_idx += 1
        descriptions = []
        number_rgb = designed.get("_meta", {}).get("number_color")
        used_theme = {"name": designed.get("_meta", {}).get("theme") or "Synthetic"}
        theme_score = float(designed.get("_meta", {}).get("match_score") or 0.0)

    # ---- VISIBLE PALETTE (most-dominant first, with role + salience tags). ----
    role_for: Dict[str, str] = {}
    if salient:
        role_for[salient[0]["hex"]] = "body"
    if len(salient) > 1:
        role_for.setdefault(salient[1]["hex"], "feature")
    if len(salient) > 2:
        role_for.setdefault(salient[2]["hex"], "accent")
    palette: List[Dict] = []
    for d in dominant:
        rgb = d["rgb255"]
        palette.append({
            "hex": d["hex"],
            "rgb": [rgb[0], rgb[1], rgb[2]],
            "weight": round(d["weight"], 4),
            "salience": round(d["salience"], 4),
            "name": _nearest_color_word(rgb),
            "role": role_for.get(d["hex"], ""),
        })

    temp_word = ("warm" if stats["temperature"] > 0.05
                 else "cool" if stats["temperature"] < -0.05 else "neutral")
    theme_name = used_theme.get("name", "Synthetic") if isinstance(used_theme, dict) else "Synthetic"
    theme_mood = used_theme.get("mood", "") if isinstance(used_theme, dict) else ""
    n_body = len([z for z in zones if isinstance(z, dict)
                  and z.get("colorMode") == "multi" and (z.get("finish") or z.get("base"))])
    explanation = (
        "Photo analyzed: %d color(s) [%s]; mood = %s (luma %.2f, saturation %.2f, "
        "%s, contrast %.2f, colorfulness %.2f). Matched art direction \"%s\"%s and "
        "colored its %d crown-jewel finish zone(s) from the photo's own palette so "
        "the livery EVOKES the image. Number/Art/Sponsor zones + a gloss "
        "'Everything Else' safety net were added automatically."
        % (
            len(palette),
            ", ".join(p["hex"] for p in palette),
            ", ".join(mood[:5]) if mood else "neutral",
            stats["luma"], stats["sat"], temp_word, stats["contrast"], stats["colorfulness"],
            theme_name,
            (" — %s" % theme_mood) if theme_mood else "",
            n_body,
        )
    )

    meta = {
        "source": "image",
        "path": used_path,
        "theme": theme_name,
        "theme_mood": theme_mood,
        "match_score": round(float(theme_score), 2),
        "mood_words": mood,
        "stats": {k2: round(v, 4) for k2, v in stats.items()},
        "number_color": _hex(number_rgb) if isinstance(number_rgb, (tuple, list)) else number_rgb,
        "finishes": [z.get("finish") or z.get("base") for z in zones
                     if isinstance(z, dict) and z.get("colorMode") == "multi"
                     and (z.get("finish") or z.get("base"))],
        "role_palette": [_hex(c) for c in role_palette],
        "descriptions": descriptions,
        "car_mapped": car_mapped,
        "car_mode": (car_plan or {}).get("mode") if car_mapped else None,
        "car_regions": [_ld._hex(rgb) for rgb, _t in (car_plan or {}).get("selectors", [])] if car_mapped else [],
    }

    return {
        "zones": zones,
        "explanation": explanation,
        "palette": palette,
        "_meta": meta,
    }


__all__ = ["design_from_image"]
