"""PROMPT-TO-LIVERY — a real design engine that turns a vibe into a livery.

MEGA FEATURE 1.  Owner mandate: "NOTHING breaks what we have."  This module is
PURELY ADDITIVE — it boots no registry on import and edits no existing file.
``design_from_prompt(prompt, seed)`` parses the prompt locally (NO external LLM)
and returns ``{"zones": [...], "explanation": "...", "_meta": {...}}`` whose
``zones`` are shaped to render as-is by ``shokker_engine_v2.build_multi_zone(...)``.

This is also the SHARED BRAIN behind Photo->Livery: ``engine/photo_livery`` builds
a synthetic prompt + palette and calls ``design_from_prompt``, then recolors the
body zones. The public surface ``design_from_prompt``, ``_COLOR_NAMES`` and
``_KEYWORD_FAMILY`` are kept intact for that caller.

How it works (v2 — the intelligent rewrite)
-------------------------------------------
1. COLOR PARSE — a named-color table (+ modifiers dark/neon/matte/deep/...) maps
   phrases to RGB. ``engine.color_science`` (OKLab) pushes neon colors toward max
   perceptual chroma so "toxic green" reads electric, not muddy.
2. THEME MATCH — the prompt is scored against ~55 curated THEMES (see
   ``engine/livery_themes``). Each theme carries a harmonious palette + FINISH
   ROLES drawn from REAL crown-jewel catalog ids. Synonyms / mood words / racing
   terms route the vibe to the best theme(s). The top theme drives the design;
   secondary matches seed alternate VARIATIONS.
3. PALETTE — the theme palette is perceptually spaced via OKLab and ANY explicit
   colors the user named are blended in (so "toxic racer but in purple" honors the
   purple while keeping the theme's harmony + finishes). Colors always look good
   together because spacing/derivation happens in OKLab, never raw HSV.
4. COMPOSITION — an intentional multi-zone livery is assembled from the theme's
   roles: a body finish (largest area), optional secondary body / hero feature
   (hood or roof), an accent, plus the standard Number/Art/Sponsor zones and a
   gloss ``color:'remaining'`` safety net. The Car Number gets a readable,
   high-contrast color derived from the body in OKLab.
5. ZONE HINTS — "carbon hood", "chrome roof", etc. still carve dedicated zones and
   OVERRIDE the theme's feature for that part.
6. VARIATIONS — ``_meta["variations"]`` holds 1-2 alternate complete designs (the
   UI may offer them); ``design_from_prompt`` itself stays backward compatible.
"""
from __future__ import annotations

import colorsys
import re
from typing import Dict, List, Optional, Tuple

# color_science is optional — if the import fails for any reason we still work.
try:  # pragma: no cover - defensive
    from engine import color_science as _cs  # type: ignore
except Exception:  # pragma: no cover
    try:
        import color_science as _cs  # type: ignore
    except Exception:
        _cs = None  # type: ignore

# theme library (the curated design brain).  Defensive import: a layout change
# can never make this module fail to import — we fall back to a built-in default.
try:  # pragma: no cover - import shim
    from engine import livery_themes as _themes  # type: ignore
except Exception:  # pragma: no cover
    try:
        import livery_themes as _themes  # type: ignore
    except Exception:
        _themes = None  # type: ignore

import numpy as _np  # numpy is a hard engine dep, always present


# ---------------------------------------------------------------------------
# COLOR NAME TABLE  (sRGB 0-255).  Kept compact but covers race-livery vocab.
# (PUBLIC — photo_livery reads this to map extracted colors to color words.)
# ---------------------------------------------------------------------------
_COLOR_NAMES: Dict[str, Tuple[int, int, int]] = {
    "black": (16, 16, 18), "white": (245, 245, 245), "gray": (128, 128, 130),
    "grey": (128, 128, 130), "silver": (190, 192, 196), "gunmetal": (70, 76, 84),
    "charcoal": (45, 47, 52), "graphite": (58, 60, 66),
    "red": (210, 28, 28), "crimson": (170, 18, 36), "scarlet": (230, 36, 24),
    "maroon": (110, 22, 28), "burgundy": (96, 18, 40), "blood": (130, 10, 14),
    "orange": (245, 120, 20), "amber": (255, 170, 30), "rust": (160, 70, 28),
    "copper": (184, 96, 54), "bronze": (150, 102, 52), "tangerine": (255, 130, 28),
    "yellow": (245, 215, 24), "gold": (212, 168, 48), "lemon": (250, 232, 40),
    "green": (34, 170, 60), "lime": (140, 220, 30), "emerald": (24, 150, 90),
    "forest": (28, 90, 46), "olive": (110, 120, 40), "mint": (120, 220, 170),
    "teal": (20, 150, 150), "cyan": (30, 200, 210), "aqua": (40, 200, 200),
    "turquoise": (40, 200, 180), "jade": (20, 160, 120),
    "blue": (30, 80, 210), "navy": (22, 34, 90), "sky": (90, 170, 240),
    "cobalt": (28, 60, 200), "azure": (40, 120, 235), "sapphire": (24, 56, 170),
    "royal": (36, 60, 190), "indigo": (60, 40, 170),
    "purple": (130, 50, 200), "violet": (150, 70, 220), "magenta": (215, 30, 180),
    "lavender": (180, 150, 230), "plum": (110, 40, 110), "amethyst": (140, 80, 200),
    "pink": (240, 90, 170), "rose": (225, 90, 130), "fuchsia": (230, 40, 170),
    "salmon": (240, 130, 110), "coral": (245, 110, 90),
    "brown": (110, 70, 40), "tan": (190, 160, 110), "beige": (210, 195, 160),
    "cream": (240, 232, 205), "ivory": (245, 240, 220),
    "carbon": (28, 30, 34),  # used when "carbon" is named as a color
    "chrome": (200, 205, 212), "steel": (140, 148, 158),
    "toxic": (120, 240, 30), "neon": (50, 255, 120), "acid": (160, 255, 20),
    "venom": (90, 220, 40), "radioactive": (140, 255, 40), "uranium": (150, 240, 30),
    "midnight": (12, 16, 40), "ghost": (210, 214, 220),
}

# modifier word -> (lightness_mult, sat_mult, neon_boost_flag)
_MODS: Dict[str, Tuple[float, float, bool]] = {
    "dark": (0.55, 1.05, False), "deep": (0.50, 1.12, False),
    "darker": (0.42, 1.05, False), "midnight": (0.38, 1.05, False),
    "light": (1.35, 0.85, False), "pale": (1.45, 0.55, False),
    "bright": (1.18, 1.25, False), "vivid": (1.05, 1.35, False),
    "neon": (1.10, 1.6, True), "electric": (1.12, 1.55, True),
    "toxic": (1.08, 1.6, True), "fluorescent": (1.12, 1.6, True),
    "muted": (0.92, 0.55, False), "dusty": (0.9, 0.5, False),
    "pastel": (1.4, 0.45, False), "rich": (0.92, 1.2, False),
    "hot": (1.05, 1.4, True),
}


def _clamp8(v: float) -> int:
    return int(max(0, min(255, round(v))))


# ---------------------------------------------------------------------------
# LOADED-PAINT DOMINANT-COLOR DETECTION  (the make-or-break coverage fix)
# ---------------------------------------------------------------------------
# The OLD design used the DESIGN's own palette color as each zone's color
# SELECTOR (tol=40). On an arbitrary loaded car (e.g. the cyan/black SHOKKER
# demo) a candy-red selector matches ~0 px -> the body zone is empty -> the car
# never transforms. The cure: detect the LOADED PAINT's dominant colors and use
# THEM as the zone selectors, so the design's finishes actually cover the car's
# real regions. The theme still chooses the (vibe-accurate) FINISHES; only WHICH
# pixels each finish claims is driven by the loaded car. PURELY ADDITIVE — this
# runs only when a caller passes ``car_colors`` to ``design_from_prompt``.
def _dom_downsample(rgb01, long_edge: int = 128):
    """Cheap nearest-neighbour downsample so k-means runs on a few thousand px."""
    h, w = rgb01.shape[:2]
    if max(h, w) <= long_edge:
        return rgb01
    scale = long_edge / float(max(h, w))
    nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
    ys = (_np.linspace(0, h - 1, nh)).astype(_np.int64)
    xs = (_np.linspace(0, w - 1, nw)).astype(_np.int64)
    return rgb01[ys][:, xs]


def _dom_kmeans(pixels, k: int, seed: int):
    """Tiny dependency-free k-means++ (Lloyd). Returns (centers Kx3, labels)."""
    rng = _np.random.default_rng(int(seed) & 0x7FFFFFFF)
    n = pixels.shape[0]
    k = int(max(1, min(k, n)))
    centers = _np.empty((k, 3), _np.float32)
    centers[0] = pixels[rng.integers(0, n)]
    d2 = _np.sum((pixels - centers[0]) ** 2, axis=1)
    for c in range(1, k):
        total = float(d2.sum())
        if total <= 1e-12:
            centers[c] = pixels[rng.integers(0, n)]
        else:
            centers[c] = pixels[rng.choice(n, p=d2 / total)]
        d2 = _np.minimum(d2, _np.sum((pixels - centers[c]) ** 2, axis=1))
    for _ in range(16):
        dists = _np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        lab = _np.argmin(dists, axis=1)
        for c in range(k):
            sel = pixels[lab == c]
            if sel.shape[0]:
                centers[c] = sel.mean(axis=0)
    dists = _np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2)
    return centers.astype(_np.float32), _np.argmin(dists, axis=1).astype(_np.int64)


def extract_dominant_colors(paint, max_colors: int = 5, seed: int = 51,
                            drop_white_bg: bool = True):
    """Return the loaded paint's dominant colors, most-area first.

    Args:
        paint: an HxWx3/HxWx4 numpy array (uint8 0..255 or float 0..1), or a path.
        max_colors: how many dominant clusters to return (clamped 1..6).
        seed: deterministic seed.
        drop_white_bg: when True, near-white pixels (UV background / blank canvas)
            are excluded from the analysis so they don't dominate the result —
            this matters because an unpainted iRacing template is mostly white.

    Returns:
        ``[{"rgb": (r,g,b), "weight": frac}, ...]`` most-dominant first, weights
        summing to ~1 over the analysed (non-background) pixels. Empty list if the
        image can't be read. NEVER raises — this is a best-effort helper.
    """
    try:
        arr = paint
        if isinstance(arr, str):
            from PIL import Image  # PIL is an engine dep
            with Image.open(arr) as im:
                arr = _np.asarray(im.convert("RGB"))
        arr = _np.asarray(arr)
        if arr.ndim == 2:
            arr = _np.stack([arr] * 3, axis=-1)
        if arr.ndim == 3 and arr.shape[2] == 4:
            # respect alpha: drop fully transparent pixels later via a mask
            alpha = arr[:, :, 3]
            arr = arr[:, :, :3]
        else:
            alpha = None
        if arr.ndim != 3 or arr.shape[2] != 3:
            return []
        if arr.dtype.kind in "ui":
            rgb01 = arr.astype(_np.float32) / 255.0
        else:
            rgb01 = arr.astype(_np.float32)
            if float(rgb01.max() if rgb01.size else 0.0) > 1.5:
                rgb01 = rgb01 / 255.0
        rgb01 = _np.clip(rgb01[:, :, :3], 0.0, 1.0)
        small = _dom_downsample(rgb01, long_edge=128)
        px = small.reshape(-1, 3)
        if alpha is not None:
            a_small = _dom_downsample(alpha[:, :, None].astype(_np.float32), 128)[:, :, 0].reshape(-1)
            px = px[a_small > 8.0] if a_small.size == px.shape[0] else px
        if drop_white_bg and px.shape[0] > 32:
            mx = px.max(axis=1)
            mn = px.min(axis=1)
            # near-white (bright + low chroma) is template background, not paint.
            keep = ~((mx > 0.90) & ((mx - mn) < 0.06))
            if int(keep.sum()) >= 32:
                px = px[keep]
        if px.shape[0] == 0:
            return []
        k = int(max(1, min(6, max_colors)))
        centers, labels = _dom_kmeans(px, k, seed)
        counts = _np.bincount(labels, minlength=centers.shape[0]).astype(_np.float32)
        # merge near-duplicate clusters so a near-solid car returns ONE dominant.
        keep_c, keep_w = [], []
        for c, w in sorted(zip(centers, counts), key=lambda t: -t[1]):
            merged = False
            for i, kc in enumerate(keep_c):
                if float(_np.sqrt(_np.sum((kc - c) ** 2))) < 0.10:
                    tot = keep_w[i] + float(w)
                    keep_c[i] = (kc * keep_w[i] + c * float(w)) / max(1e-6, tot)
                    keep_w[i] = tot
                    merged = True
                    break
            if not merged:
                keep_c.append(_np.asarray(c, _np.float32))
                keep_w.append(float(w))
        total = max(1.0, float(sum(keep_w)))
        out = []
        for c, w in sorted(zip(keep_c, keep_w), key=lambda t: -t[1]):
            r, g, b = (_clamp8(c[0] * 255), _clamp8(c[1] * 255), _clamp8(c[2] * 255))
            out.append({"rgb": (r, g, b), "weight": float(w) / total})
        return out
    except Exception:  # pragma: no cover - best-effort, never break the design
        return []


# ---------------------------------------------------------------------------
# OKLab helpers — all palette math runs perceptually so colors always sit well.
# ---------------------------------------------------------------------------
def _to01(rgb) -> "_np.ndarray":
    return _np.asarray([c / 255.0 for c in rgb], dtype=_np.float32)


def _rgb255(arr01) -> Tuple[int, int, int]:
    a = _np.clip(_np.asarray(arr01, _np.float32), 0.0, 1.0)
    return (_clamp8(a[0] * 255), _clamp8(a[1] * 255), _clamp8(a[2] * 255))


def _oklch_of(rgb) -> Optional["_np.ndarray"]:
    """sRGB255 triple -> OKLCh (L, C, H) or None if color_science unavailable."""
    if _cs is None:
        return None
    try:
        lab = _cs.srgb_to_oklab(_to01(rgb).reshape(1, 3))
        return _cs.oklab_to_oklch(lab)[0]
    except Exception:
        return None


def _from_oklch(lch) -> Tuple[int, int, int]:
    lab = _cs.oklch_to_oklab(_np.asarray(lch, _np.float32).reshape(1, 3))
    out = _cs.oklab_to_srgb(lab)[0]
    return _rgb255(out)


def _apply_neon(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Push a color toward max perceptual chroma (electric look) via OKLCh."""
    if _cs is None:
        r, g, b = (c / 255.0 for c in rgb)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s = min(1.0, s * 1.6 + 0.25)
        v = min(1.0, v * 1.12 + 0.12)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (_clamp8(r * 255), _clamp8(g * 255), _clamp8(b * 255))
    try:
        lch = _oklch_of(rgb)
        if lch is None:
            return rgb
        lch = lch.copy()
        lch[1] = min(0.37, lch[1] * 1.7 + 0.10)            # boost chroma
        lch[0] = float(_np.clip(lch[0] * 1.05 + 0.04, 0.0, 0.98))
        return _from_oklch(lch)
    except Exception:
        return rgb


def _apply_mods(rgb: Tuple[int, int, int], mods: List[str]) -> Tuple[int, int, int]:
    r, g, b = (c / 255.0 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    neon = False
    for m in mods:
        lm, sm, nb = _MODS[m]
        v = min(1.0, max(0.0, v * lm))
        s = min(1.0, max(0.0, s * sm))
        neon = neon or nb
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    out = (_clamp8(r * 255), _clamp8(g * 255), _clamp8(b * 255))
    if neon:
        out = _apply_neon(out)
    return out


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])


def _harmonize_palette(palette255: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """Perceptually space a palette so its colors stay distinct yet related.

    Runs in OKLab: hues are nudged apart only if two anchors collide, and we keep
    a healthy spread of lightness so the livery reads as layered, not flat. If
    color_science is unavailable the palette passes through unchanged (it was
    hand-authored to look good already).
    """
    if _cs is None or len(palette255) < 2:
        return list(palette255)
    try:
        lchs = []
        for rgb in palette255:
            lch = _oklch_of(rgb)
            lchs.append(lch.copy() if lch is not None else None)
        # ensure neighboring anchors differ enough in L OR H to read as separate.
        for i in range(1, len(lchs)):
            a, b = lchs[i - 1], lchs[i]
            if a is None or b is None:
                continue
            dH = abs(((b[2] - a[2] + _np.pi) % (2 * _np.pi)) - _np.pi)
            dL = abs(b[0] - a[0])
            if dH < 0.18 and dL < 0.12:           # too similar -> push apart
                b[0] = float(_np.clip(b[0] + (0.16 if b[0] < a[0] + 0.01 else -0.16), 0.05, 0.95))
        out = []
        for rgb, lch in zip(palette255, lchs):
            out.append(_from_oklch(lch) if lch is not None else rgb)
        return out
    except Exception:
        return list(palette255)


def _lightness_floor(rgb: Tuple[int, int, int], floor: float = 0.30,
                     keep_chroma: bool = True) -> Tuple[int, int, int]:
    """Lift a color to a minimum OKLab lightness so a finish painted over it has
    luminance to reveal its structure — WITHOUT changing the hue or killing the
    "dark" mood (a deep jewel-tone still reads dark, just not crushed to black).

    Near-neutral colors (very low chroma) are lifted gently and given a hair of
    chroma so they don't read as flat gray. If color_science is unavailable we
    fall back to a luma-based lift."""
    if _cs is None:
        lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0
        if lum >= floor:
            return rgb
        k = (floor * 255.0) / max(1.0, 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])
        return tuple(_clamp8(c * k + floor * 40) for c in rgb)
    try:
        lch = _oklch_of(rgb)
        if lch is None:
            return rgb
        if lch[0] >= floor:
            return rgb
        lch = lch.copy()
        lch[0] = floor
        if keep_chroma and lch[1] < 0.03:
            lch[1] = 0.05                       # avoid a lifted muddy gray
        return _from_oklch(lch)
    except Exception:
        return rgb


def _readable_number_color(body_rgb: Tuple[int, int, int],
                           accent_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Pick a high-contrast number color off the BODY in OKLab lightness.

    Dark body -> bright number; light body -> dark number. We bias toward the
    accent hue so the number still belongs to the livery, then force enough
    lightness contrast to stay legible at race distance.
    """
    if _cs is None:
        lum = 0.2126 * body_rgb[0] + 0.7152 * body_rgb[1] + 0.0722 * body_rgb[2]
        return (245, 245, 248) if lum < 110 else (18, 18, 22)
    try:
        body = _oklch_of(body_rgb)
        acc = _oklch_of(accent_rgb)
        if body is None:
            return (245, 245, 248)
        target_L = 0.93 if body[0] < 0.55 else 0.16
        H = acc[2] if acc is not None else body[2]
        C = min(0.10, (acc[1] if acc is not None else 0.04))   # keep it crisp
        return _from_oklch([target_L, C, H])
    except Exception:
        return (245, 245, 248)


def _parse_colors(prompt: str, exclude_pos=None) -> List[Dict]:
    """Return a list of {rgb, hex, words, pos} explicit color picks, in order."""
    exclude_pos = exclude_pos or set()
    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    picks: List[Dict] = []
    i = 0
    pending_mods: List[str] = []
    while i < len(words):
        w = words[i]
        if i in exclude_pos:
            pending_mods = []
            i += 1
            continue
        if w in _MODS and w not in _COLOR_NAMES:
            pending_mods.append(w)
            i += 1
            continue
        if w in _COLOR_NAMES:
            base_rgb = _COLOR_NAMES[w]
            mods = list(pending_mods)
            if w in _MODS:  # self-modifying color keyword (toxic/neon/midnight)
                mods.append(w)
            rgb = _apply_mods(base_rgb, mods) if mods else base_rgb
            picks.append({"rgb": rgb, "hex": _hex(rgb), "words": (mods + [w]), "pos": i})
            pending_mods = []
        elif w not in _MODS:
            pending_mods = []
        i += 1
    return picks


# ---------------------------------------------------------------------------
# LEGACY FAMILY MAP — retained so any external caller / fallback still resolves
# a single finish from a keyword.  The THEME path is primary; this is the
# safety net for keywords no theme caught.
# (PUBLIC — photo_livery reads _KEYWORD_FAMILY to know which words are styles.)
# ---------------------------------------------------------------------------
_FAMILIES: Dict[str, Dict] = {
    "aggressive": {"kind": "mono", "ids": ["fm_inferno_veins", "fm_flame_wall", "ghost_fracture", "fs_shatter_glass"]},
    "fracture":   {"kind": "mono", "ids": ["ghost_fracture", "fs_shatter_glass", "fs_shattered_prism", "spectrum_fracture_polarized"]},
    "carbon":     {"kind": "base", "ids": ["carbon_weave", "carbon_base", "enh_carbon_fiber", "f_carbon_fiber"]},
    "stealth":    {"kind": "base", "ids": ["flat_black", "matte", "gunmetal_satin", "black_chrome"]},
    "matte":      {"kind": "base", "ids": ["matte", "flat_black", "satin", "enh_matte"]},
    "elegant":    {"kind": "base", "ids": ["pearl", "deep_pearl", "tri_coat_pearl", "midnight_pearl"]},
    "chrome":     {"kind": "base", "ids": ["chrome", "black_chrome", "candy_chrome", "satin_chrome"]},
    "ghost":      {"kind": "mono", "ids": ["fs_wraith_veil", "fs_ghost_silk", "fs_phantom_lattice", "phantom"]},
    "toxic":      {"kind": "mono", "ids": ["neon_toxic_green", "radioactive", "cc_radioactive", "prizm_toxic_waste"]},
    "neon":       {"kind": "mono", "ids": ["neon_toxic_green", "neon_orange_hazard", "reactive_plasma", "radioactive"]},
    "fire":       {"kind": "mono", "ids": ["fm_inferno_veins", "fm_magma", "ember_glow", "fractal_liquid_fire"]},
    "ice":        {"kind": "mono", "ids": ["fm_frost_lace", "fm_glacier_core", "black_ice", "cs_fire_ice"]},
    "ocean":      {"kind": "mono", "ids": ["cs_deepocean", "cs_ocean_shift", "bioluminescent_wave", "depth_wave"]},
    "cosmic":     {"kind": "mono", "ids": ["galaxy", "cs_nebula", "chameleon_galaxy", "prizm_deep_space"]},
    "aurora":     {"kind": "mono", "ids": ["aurora", "aurora_glow", "chameleon_aurora", "fable_aurora_travel"]},
    "luxury":     {"kind": "mono", "ids": ["fd_imperial_gold", "baroque_scrollwork", "cs_black_gold", "cs_goldrush"]},
    "iridescent": {"kind": "mono", "ids": ["prizm_spectrum", "spectral", "prizm_aurora_shift", "chameleon_aurora"]},
    "pearl":      {"kind": "base", "ids": ["pearl", "deep_pearl", "tri_coat_pearl", "midnight_pearl"]},
    "gloss":      {"kind": "base", "ids": ["gloss", "race_day_gloss", "semi_gloss", "cerakote_gloss"]},
    "sparkle":    {"kind": "mono", "ids": ["sparkle_galaxy", "sparkle_starfield", "living_twinkle_stars"]},
}

# keyword -> family.  (PUBLIC — photo_livery reads the keys as the style vocab.)
_KEYWORD_FAMILY: Dict[str, str] = {
    "menacing": "aggressive", "aggressive": "aggressive", "angry": "aggressive",
    "brutal": "aggressive", "savage": "aggressive", "fierce": "aggressive",
    "evil": "aggressive", "demon": "aggressive", "war": "aggressive",
    "fracture": "fracture", "fractured": "fracture", "crack": "fracture",
    "cracked": "fracture", "shatter": "fracture", "shattered": "fracture",
    "broken": "fracture", "split": "fracture",
    "carbon": "carbon", "fiber": "carbon", "fibre": "carbon", "weave": "carbon",
    "stealth": "stealth", "stealthy": "stealth", "tactical": "stealth",
    "military": "stealth", "matte": "matte", "flat": "matte", "satin": "matte",
    "elegant": "elegant", "classy": "elegant", "refined": "elegant",
    "sophisticated": "elegant", "smooth": "elegant", "premium": "elegant",
    "chrome": "chrome", "mirror": "chrome", "polished": "chrome",
    "metallic": "chrome", "shiny": "chrome",
    "ghost": "ghost", "ghostly": "ghost", "phantom": "ghost", "spectral": "ghost",
    "wraith": "ghost", "haunted": "ghost", "spooky": "ghost", "spirit": "ghost",
    "toxic": "toxic", "acid": "toxic", "venom": "toxic", "venomous": "toxic",
    "radioactive": "toxic", "hazard": "toxic", "poison": "toxic", "biohazard": "toxic",
    "neon": "neon", "electric": "neon", "glowing": "neon", "luminous": "neon",
    "fire": "fire", "fiery": "fire", "flame": "fire", "flaming": "fire",
    "lava": "fire", "magma": "fire", "ember": "fire", "inferno": "fire",
    "molten": "fire", "blaze": "fire", "hot": "fire",
    "ice": "ice", "icy": "ice", "frost": "ice", "frozen": "ice", "frosty": "ice",
    "glacier": "ice", "arctic": "ice", "cold": "ice", "winter": "ice",
    "ocean": "ocean", "sea": "ocean", "water": "ocean", "wave": "ocean",
    "aquatic": "ocean", "deep": "ocean", "marine": "ocean", "tide": "ocean",
    "cosmic": "cosmic", "galaxy": "cosmic", "galactic": "cosmic", "space": "cosmic",
    "nebula": "cosmic", "stellar": "cosmic", "star": "cosmic", "universe": "cosmic",
    "void": "cosmic", "interstellar": "cosmic",
    "aurora": "aurora", "borealis": "aurora", "northern": "aurora",
    "luxury": "luxury", "luxurious": "luxury", "royal": "luxury", "regal": "luxury",
    "imperial": "luxury", "opulent": "luxury", "gold": "luxury", "golden": "luxury",
    "rich": "luxury", "baroque": "luxury",
    "iridescent": "iridescent", "holographic": "iridescent", "holo": "iridescent",
    "prismatic": "iridescent", "rainbow": "iridescent", "oilslick": "iridescent",
    "chameleon": "iridescent", "colorshift": "iridescent", "colorshifting": "iridescent",
    "pearl": "pearl", "pearlescent": "pearl",
    "gloss": "gloss", "glossy": "gloss", "wet": "gloss",
    "sparkle": "sparkle", "sparkly": "sparkle", "glitter": "sparkle",
    "metalflake": "sparkle", "flake": "sparkle",
}

# Guaranteed-present fallbacks if a candidate list is somehow dead.
_SAFE_MONO = "phantom"
_SAFE_BASE = "gloss"

# ---------------------------------------------------------------------------
# ZONE HINTS — "<color/style> hood/roof/wing/..." carve out a dedicated zone.
# ---------------------------------------------------------------------------
_ZONE_PART_WORDS = {
    "hood": "Hood", "bonnet": "Hood", "roof": "Roof", "wing": "Wing",
    "spoiler": "Wing", "bumper": "Bumper", "splitter": "Splitter",
    "mirror": "Mirrors", "mirrors": "Mirrors", "door": "Doors",
    "doors": "Doors", "stripe": "Stripes", "stripes": "Stripes",
    "fender": "Fenders", "nose": "Nose", "tail": "Tail",
    "sidepod": "Sidepods", "sidepods": "Sidepods",
}


def _live_registries():
    """Return (mono_set, base_set) from the booted engine, or (None, None)."""
    try:
        import shokker_engine_v2 as eng  # type: ignore
        mono = set(getattr(eng, "MONOLITHIC_REGISTRY", {}).keys())
        base = set(getattr(eng, "BASE_REGISTRY", {}).keys())
        if not mono and not base:
            return None, None
        return mono, base
    except Exception:
        return None, None


def _resolve_id(candidates: List[str], kind: str, mono_set, base_set) -> Tuple[str, str]:
    """First live id from a candidate list. Returns (kind, id) with fallback."""
    for cand in candidates:
        if kind == "mono":
            if mono_set is None or cand in mono_set:
                return ("mono", cand)
        else:
            if base_set is None or cand in base_set:
                return ("base", cand)
    return ("mono", _SAFE_MONO) if kind == "mono" else ("base", _SAFE_BASE)


def _resolve_family(fam: str, mono_set, base_set) -> Tuple[str, str]:
    spec = _FAMILIES.get(fam)
    if not spec:
        return ("base", _SAFE_BASE)
    return _resolve_id(spec["ids"], spec["kind"], mono_set, base_set)


# ---------------------------------------------------------------------------
# THEME MATCHING — score a prompt against every curated theme.
# ---------------------------------------------------------------------------
def _theme_list() -> List[Dict]:
    if _themes is None:
        return []
    try:
        return list(_themes.all_themes())
    except Exception:
        return []


def _default_theme() -> Optional[Dict]:
    if _themes is None:
        return None
    try:
        return _themes.DEFAULT_THEME
    except Exception:
        return None


def _tokenize(prompt: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", (prompt or "").lower())


def _score_theme(theme: Dict, tokens: List[str], joined: str,
                 demoted: set = None) -> float:
    """Score how well a theme matches the prompt. Higher = better.

    ``demoted`` is a set of tokens that were CONSUMED by a zone hint (e.g.
    "carbon" in "carbon hood"). Those words still count, but only weakly — so a
    hood material can't hijack the WHOLE-BODY theme away from the real vibe.
    The phrase "menacing matte black with toxic-green fracture and a CARBON HOOD"
    should pick a menace/toxic body theme and put carbon on the hood, NOT make
    the whole car carbon. Bigrams ("blade runner") and adjacent-token synonyms
    ("rising sun", "neon city") are matched against the joined string too.
    """
    demoted = demoted or set()
    score = 0.0
    syns = set(theme.get("synonyms", []))
    name_words = set(re.findall(r"[a-z0-9]+", theme["name"].lower()))
    tokset = set(tokens)
    # whole-word synonym hits (strong; demoted hint-words count only a little)
    for t in tokens:
        w_syn = 0.6 if t in demoted else 3.0
        w_name = 0.4 if t in demoted else 2.0
        if t in syns:
            score += w_syn
        if t in name_words:
            score += w_name
    # multi-word / spaced synonyms (e.g. "fireandice", "blade runner", "neon city")
    # matched against the joined string AND a single-spaced phrase form.
    spaced = " ".join(tokens)
    for s in syns:
        if s in tokset:
            continue
        if " " in s:                       # multi-word synonym phrase
            if s in spaced:
                score += 3.2
        elif len(s) > 6 and s in joined:   # glued compound (synthwave/cottoncandy)
            score += 1.5
    # mood-text soft overlap (a couple of shared descriptive words)
    mood_words = set(re.findall(r"[a-z]+", theme.get("mood", "").lower()))
    score += 0.4 * len(tokset & mood_words)
    return score


def _rank_themes(prompt: str, demoted: set = None) -> List[Tuple[float, Dict]]:
    tokens = _tokenize(prompt)
    joined = "".join(tokens)
    scored = [(_score_theme(t, tokens, joined, demoted), t) for t in _theme_list()]
    scored = [s for s in scored if s[0] > 0.0]
    scored.sort(key=lambda x: -x[0])
    return scored


# ---------------------------------------------------------------------------
# VARIATION SELECTION — pick 2 alternates that are DISTINCT yet on-vibe.
# ---------------------------------------------------------------------------
def _theme_finish_family(theme: Dict) -> str:
    """A coarse 'finish family' fingerprint for a theme's BODY role — used to
    guarantee the 3 offered options don't all wear the same kind of finish."""
    roles = theme.get("roles", [])
    body = next((r for r in roles if r[0] == "body"), None)
    fid = (body[1][0] if body and body[1] else "") or ""
    for pref in ("fs_", "fm_", "chameleon_", "prizm_", "spectrum_", "cs_", "cx_",
                 "rs_", "grad_", "candy", "chrome", "pearl", "carbon", "gunmetal",
                 "neon", "matte", "flat_", "glitch", "datamosh", "metal_flake"):
        if pref in fid or fid.startswith(pref):
            return pref.strip("_")
    return fid[:6] or "misc"


def _theme_body_hue(theme: Dict) -> Optional[float]:
    """Hue (0..1) of a theme's most-saturated palette anchor — its color identity.
    Used to keep an alternate from fighting an explicitly-named color (a 'crimson
    and gold' dragon shouldn't surface a GREEN serpent alternate)."""
    pal = theme.get("palette", [])
    best_h, best_s = None, -1.0
    for rgb in pal:
        r, g, b = (c / 255.0 for c in rgb)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s * v > best_s:
            best_s, best_h = s * v, h
    return best_h if best_s > 0.12 else None  # None = neutral theme, never clashes


def _hue_clash(theme: Dict, named_hues: List[float]) -> bool:
    """True if the theme's color identity is far from EVERY user-named color hue
    (only meaningful when the user named saturated colors)."""
    if not named_hues:
        return False
    th = _theme_body_hue(theme)
    if th is None:
        return False
    def dist(a, b):
        d = abs(a - b) % 1.0
        return min(d, 1.0 - d)
    return min(dist(th, nh) for nh in named_hues) > 0.18  # >~65° off all named hues


# Words that live in _COLOR_NAMES but read as a VIBE, not a literal paint color
# (they also drive theme MATCHING). They must NOT impose a "named hue" on the
# variation picker — "neon"/"toxic" cyberpunk should still get neon/cyber
# alternates, not be forced to a green color story.
_VIBE_NOT_COLOR = {
    "neon", "toxic", "acid", "venom", "radioactive", "uranium", "midnight",
    "ghost", "carbon", "chrome", "steel", "silver",
}


def _named_hues(colors: List[Dict]) -> List[float]:
    out = []
    for c in colors or []:
        words = set(w.lower() for w in c.get("words", []))
        if words and words <= _VIBE_NOT_COLOR:
            continue                # vibe word (neon/toxic/...), not a real color
        r, g, b = (v / 255.0 for v in c["rgb"])
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s * v > 0.18:            # only chromatic picks define a hue to honor
            out.append(h)
    return out


def _select_variations(primary: Dict, ranked: List[Tuple[float, Dict]],
                       want: int = 2, colors: List[Dict] = None) -> List[Dict]:
    """Choose up to ``want`` alternate themes that are (a) genuinely DIFFERENT
    from the primary and each other (different finish family), and (b) still
    ON-VIBE — preferring themes that either matched the prompt or share a vibe
    TAG with the primary. An opposite-vibe wildcard (no shared tag, no match) is
    used only as a last resort to guarantee the viral "3 options" always fills.

    Ordering of the candidate pool by desirability:
      1. ranked alternates that ALSO share a tag with the primary  (best: matched + related)
      2. ranked alternates that matched the prompt at all
      3. unmatched themes that share a tag with the primary        (on-vibe siblings)
      4. the DEFAULT show-stopper / any remaining theme            (wildcard floor)
    """
    p_tags = set(primary.get("tags", []))
    p_name = primary["name"]
    ranked_names = {t["name"] for _s, t in ranked}
    ranked_by_name = {t["name"]: s for s, t in ranked}

    tier1, tier2, tier3, tier4 = [], [], [], []
    for _s, t in ranked:
        if t["name"] == p_name:
            continue
        if p_tags & set(t.get("tags", [])):
            tier1.append(t)
        else:
            tier2.append(t)
    for t in _theme_list():
        if t["name"] == p_name or t["name"] in ranked_names:
            continue
        if p_tags & set(t.get("tags", [])):
            tier3.append(t)
    # On-vibe ordering for the unmatched-but-related siblings (tier3): a theme's
    # tags are authored specific->general (Inferno = ["fire","aggressive"]), so a
    # FIRE primary should surface FIRE siblings (Phoenix Rising / Solar Forge /
    # Tangerine Heat) ahead of merely-"aggressive" ones (Midnight Menace). Rank by
    # (shares the primary's DEFINING first tag, then total shared-tag count). Stable
    # within ties (Python sort) so file order still breaks exact ties.
    p_primary_tag = (primary.get("tags") or [None])[0]
    def _vibe_key(t):
        tt = set(t.get("tags", []))
        return (-int(p_primary_tag in tt), -len(p_tags & tt))
    tier3.sort(key=_vibe_key)
    dft = _default_theme()
    if dft is not None and dft["name"] != p_name:
        tier4.append(dft)
    # any other theme as the absolute floor (kept stable / deterministic order)
    for t in _theme_list():
        if t["name"] != p_name and t not in tier1 + tier2 + tier3:
            tier4.append(t)

    pool = tier1 + tier2 + tier3 + tier4
    # When the user NAMED saturated colors, prefer alternates whose color identity
    # honors them — push hue-clashing siblings to the back (still available as a
    # floor) so "crimson and gold dragon" doesn't lead with a GREEN serpent.
    nh = _named_hues(colors)
    if nh:
        pool = [t for t in pool if not _hue_clash(t, nh)] + \
               [t for t in pool if _hue_clash(t, nh)]
    chosen: List[Dict] = []
    used_families = {_theme_finish_family(primary)}
    used_names = {p_name}
    # First pass: enforce distinct finish families (the strong distinctness rule).
    for t in pool:
        if len(chosen) >= want:
            break
        if t["name"] in used_names:
            continue
        fam = _theme_finish_family(t)
        if fam in used_families:
            continue
        chosen.append(t)
        used_names.add(t["name"])
        used_families.add(fam)
    # Second pass: if we still need more (rare — few distinct families), relax the
    # family rule but never repeat a theme name, so we always offer 3 total looks.
    if len(chosen) < want:
        for t in pool:
            if len(chosen) >= want:
                break
            if t["name"] in used_names:
                continue
            chosen.append(t)
            used_names.add(t["name"])
    return chosen


# ---------------------------------------------------------------------------
# ZONE SCHEMA BUILDERS — match the recipe.json zoneSnapshot shape closely.
# ---------------------------------------------------------------------------
def _color_selector(rgb: Tuple[int, int, int], tol: int = 40) -> List[Dict]:
    return [{"color_rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])], "tolerance": tol, "hex": _hex(rgb)}]


def _make_body_zone(idx: int, name: str, rgb, kind: str, fid: str,
                    intensity: str = "100", hint: str = "",
                    select_rgb=None, select_tol: int = 40,
                    remaining: bool = False) -> Dict:
    """Build one body/feature/accent zone.

    ``rgb`` is the DESIGN's intended color for this role (shown as the picker
    swatch + used to derive a readable number color). The zone's color SELECTOR
    — which pixels of the LOADED paint this finish actually claims — defaults to
    ``rgb`` (legacy behavior) but can be overridden via ``select_rgb`` /
    ``select_tol`` so the design's finish lands on the car's REAL region (its
    dominant color) instead of a color the loaded car may not contain. When
    ``remaining`` is True the zone claims every still-unclaimed pixel (the broad
    hero-coverage fallback for a near-solid car).
    """
    sel_rgb = select_rgb if select_rgb is not None else rgb
    sel_tol = int(select_tol)
    if remaining:
        color_field = "remaining"
        colors_field = []
        color_mode = "special"
    else:
        color_field = _color_selector(sel_rgb, tol=sel_tol)
        colors_field = _color_selector(sel_rgb, tol=sel_tol)
        color_mode = "multi"
    return {
        "name": name,
        "color": color_field,
        "base": fid if kind == "base" else None,
        "pattern": "none",
        "finish": fid if kind == "mono" else None,
        "intensity": str(intensity),
        "colorMode": color_mode,
        "pickerColor": _hex(rgb),
        "pickerTolerance": sel_tol,
        "colors": colors_field,
        "hint": hint or "Pick this body color on the paint",
        "id": "zone_ld_%d" % idx,
        "hardEdge": True,
    }


def _non_color_zones(start_idx: int, number_rgb: Tuple[int, int, int]) -> List[Dict]:
    """Standard non-color zones + the remaining safety net (last).

    The Car Number zone is seeded with a readable, livery-matched picker color.
    """
    def base(name, picker, tol, hint, idx):
        return {
            "name": name, "color": None, "base": None, "pattern": "none",
            "finish": None, "intensity": "100", "colorMode": "none",
            "pickerColor": picker, "pickerTolerance": tol, "colors": [],
            "hint": hint, "id": "zone_ld_%d" % idx, "hardEdge": True,
        }
    z = []
    z.append(base("Car Number", _hex(number_rgb), 35,
                  "Suggested high-contrast number color. Magic Wand each number, or Draw Region/Rectangle.", start_idx))
    z.append(base("Custom Art 1", "#ff3366", 40,
                  "Use Magic Wand to click artwork or Draw Region manually. Delete if not needed.", start_idx + 1))
    z.append(base("Sponsors / Logos", "#ffffff", 30,
                  "Draw regions over sponsor areas, or pick a color if sponsors share one color", start_idx + 2))
    z.append(base("Open Zone", "#777777", 40,
                  "Empty by default. Use this only if you need another custom zone before Remaining.", start_idx + 3))
    z.append({
        "name": "Everything Else", "color": "remaining", "base": "gloss",
        "pattern": "none", "finish": None, "intensity": "50", "colorMode": "special",
        "pickerColor": "#888888", "pickerTolerance": 40, "colors": [],
        "hint": "Safety net - catches any pixels not claimed by zones above",
        "id": "zone_ld_%d" % (start_idx + 4), "hardEdge": True,
    })
    return z


def _detect_zone_hints(prompt: str) -> Tuple[List[Dict], set]:
    """Find '<color?> <style?> <part>' hints -> dedicated part zones."""
    tokens = re.findall(r"[a-zA-Z]+", (prompt or "").lower())
    hints: List[Dict] = []
    seen_parts = set()
    consumed: set = set()
    for idx, tok in enumerate(tokens):
        part = _ZONE_PART_WORDS.get(tok)
        if not part or part in seen_parts:
            continue
        seen_parts.add(part)
        consumed.add(idx)
        color_rgb = None
        fam = None
        for back in range(1, 4):
            j = idx - back
            if j < 0:
                break
            t = tokens[j]
            if color_rgb is None and t in _COLOR_NAMES:
                base_rgb = _COLOR_NAMES[t]
                mods = []
                k = j - 1
                while k >= 0 and tokens[k] in _MODS:
                    mods.insert(0, tokens[k]); consumed.add(k); k -= 1
                if t in _MODS:
                    mods.append(t)
                color_rgb = _apply_mods(base_rgb, mods) if mods else base_rgb
                consumed.add(j)
            if fam is None and t in _KEYWORD_FAMILY:
                fam = _KEYWORD_FAMILY[t]
                consumed.add(j)
        hints.append({"part": part, "rgb": color_rgb, "family": fam})
    return hints, consumed


# ---------------------------------------------------------------------------
# CAR-COLOR ROLE PLAN — map the design's roles onto the LOADED car's regions.
# ---------------------------------------------------------------------------
def _normalize_car_colors(car_colors) -> List[Tuple[Tuple[int, int, int], float]]:
    """Coerce a caller-supplied ``car_colors`` into [( (r,g,b), weight ), ...]
    most-dominant first. Accepts the ``extract_dominant_colors`` shape
    ([{"rgb","weight"}]), bare RGB triples, or hex strings. Returns []."""
    out: List[Tuple[Tuple[int, int, int], float]] = []
    if not car_colors:
        return out
    try:
        for i, c in enumerate(car_colors):
            w = None
            if isinstance(c, dict):
                rgb = c.get("rgb") or c.get("color_rgb")
                w = c.get("weight")
            else:
                rgb = c
            if isinstance(rgb, str):
                s = rgb.lstrip("#")
                if len(s) == 6:
                    rgb = (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
                else:
                    continue
            if rgb is None:
                continue
            rgb_t = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            out.append((rgb_t, float(w) if w is not None else max(0.01, 1.0 - 0.15 * i)))
    except Exception:
        return []
    # already expected most-dominant first; keep order but stabilize by weight.
    return out


def _car_color_plan(car_colors) -> Optional[Dict]:
    """Decide how to drive zone SELECTORS from the loaded car's dominant colors.

    Returns a plan dict, or None if no usable car colors were supplied (which
    keeps the legacy palette-selector behavior). The plan tells ``_compose_design``
    which car color each role's finish should claim, and whether to fall back to
    a single broad/remaining body for a near-solid car.

    Plan shape::

        {"mode": "multi"|"solo",
         "selectors": [ (rgb, tol), ... ],  # per significant region, dom-first
         }
    """
    norm = _normalize_car_colors(car_colors)
    if not norm:
        return None
    # Keep regions that actually cover meaningful area (>=6%); always keep >=1.
    sig = [(rgb, w) for rgb, w in norm if w >= 0.06] or norm[:1]
    sig = sig[:4]
    # SOLO fallback: a near-solid car (one region carrying the vast majority, or
    # only one distinct color) -> put the hero body finish on a BROAD selector so
    # it dominates the whole car instead of matching a sliver.
    solo = (len(sig) == 1) or (sig[0][1] >= 0.82)
    selectors: List[Tuple[Tuple[int, int, int], int]] = []
    for i, (rgb, _w) in enumerate(sig):
        # Body (#0) gets a generous tolerance so anti-aliased/shaded variants of
        # the region come along; secondary regions a touch tighter so they don't
        # eat the body. SOLO body goes very broad to blanket the whole car.
        tol = (150 if solo else 60) if i == 0 else 44
        selectors.append((rgb, tol))
    return {"mode": "solo" if solo else "multi", "selectors": selectors}


# ---------------------------------------------------------------------------
# THE COMPOSER — turn a theme + parsed colors into a complete livery.
# ---------------------------------------------------------------------------
def _blend_palette(theme: Dict, explicit_colors: List[Dict]) -> List[Tuple[int, int, int]]:
    """Start from the theme palette, fold in any explicit colors the user named,
    then perceptually space the result so it always reads as a designed set."""
    palette = [tuple(c) for c in theme["palette"]]
    # Replace palette slots with explicit colors, most-dominant first, but never
    # clobber EVERY slot (keep at least the theme's accent so harmony survives).
    n_replace = min(len(explicit_colors), max(1, len(palette) - 1))
    for i in range(n_replace):
        palette[i] = tuple(explicit_colors[i]["rgb"])
    return _harmonize_palette(palette)


def _compose_design(theme: Dict, palette: List[Tuple[int, int, int]],
                    hints: List[Dict], mono_set, base_set,
                    name_suffix: str = "", car_plan: Optional[Dict] = None
                    ) -> Tuple[List[Dict], List[str], Tuple[int, int, int]]:
    """Build the zones for ONE complete design. Returns (zones, descriptions, number_rgb).

    When ``car_plan`` is supplied (from ``_car_color_plan`` on the loaded paint's
    dominant colors) the body/feature/accent zone SELECTORS are mapped onto the
    car's REAL regions so the design's finishes actually cover the loaded car —
    the make-or-break coverage fix. ``car_plan=None`` keeps the legacy behavior
    (selector == the design's own palette color), so callers that don't pass a
    loaded paint are byte-for-byte unchanged.
    """
    zones: List[Dict] = []
    descriptions: List[str] = []
    idx = 1

    def pal(i):
        return palette[i % len(palette)] if palette else (24, 24, 28)

    # --- car-region selector dispenser: each role-zone, in placement order,
    # claims the next dominant car region; the FIRST (body) optionally goes broad
    # (solo) so a near-solid car is fully blanketed by the hero finish. ---
    _car_selectors = list(car_plan.get("selectors", [])) if car_plan else []
    _car_solo = bool(car_plan and car_plan.get("mode") == "solo")
    _car_state = {"i": 0}

    def _sel_for_role(is_body: bool):
        """Return (select_rgb, select_tol, remaining) for the next role zone, or
        (None, 40, False) to keep the legacy palette-color selector."""
        if not _car_selectors:
            return None, 40, False
        if is_body and _car_solo:
            # one broad body claims the whole near-solid car (after any tighter
            # secondary regions subtract their slivers — but with one color there
            # are none, so it blankets everything). Use a 'remaining' is risky
            # because the standard gloss net is last; instead use a very wide tol.
            rgb, tol = _car_selectors[0]
            _car_state["i"] = max(_car_state["i"], 1)
            return rgb, tol, False
        i = _car_state["i"]
        if i < len(_car_selectors):
            rgb, tol = _car_selectors[i]
            _car_state["i"] = i + 1
            return rgb, tol, False
        # ran out of distinct car regions: reuse the dominant region with a
        # tighter tolerance so an extra role still lands on the car (it competes
        # for the same region but FIRST-WINS means earlier zones keep their pixels).
        rgb, _t = _car_selectors[0]
        return rgb, 40, False

    roles = list(theme.get("roles", []))
    body_role = next((r for r in roles if r[0] == "body"), None)
    body2_role = next((r for r in roles if r[0] == "body2"), None)
    feature_role = next((r for r in roles if r[0] == "feature"), None)
    accent_role = next((r for r in roles if r[0] == "accent"), None)

    body_rgb = pal(body_role[3]) if body_role else pal(0)
    accent_rgb = pal(accent_role[3]) if accent_role else pal(len(palette) - 1)

    def _reveal(rgb, role) -> Tuple[int, int, int]:
        """Give structured finishes (color-shift / circuit / fracture / iridescent)
        a body color with enough OKLab lightness to show their geometry. Additive
        sparkle/star finishes read fine on black, so we leave those dark."""
        kind = role[2] if role else "base"
        fid0 = (role[1][0] if role and role[1] else "")
        structured = any(fid0.startswith(p) for p in (
            "fs_", "fm_", "chameleon_", "prizm_", "spectrum_", "cs_", "cx_",
            "grad_", "ghost_circuit", "fm_circuit", "fractal_"))
        sparkly = any(s in fid0 for s in ("galaxy", "star", "sparkle", "twinkle",
                                          "nebula", "void", "deep_space", "aurora"))
        if structured and not sparkly:
            return _lightness_floor(rgb, floor=0.34)
        return rgb

    def _car_hint(default_hint: str, srgb) -> str:
        """When the design is mapped onto the loaded car, the picker is PRE-FILLED
        with the car's own region color, so the painter just confirms — say so."""
        if srgb is None:
            return default_hint
        return ("Auto-mapped to the car's region %s — already selected; "
                "tweak the picker only if you want a different region." % _hex(srgb))

    # ---- BODY (largest area) ----
    if body_role:
        kind, fid = _resolve_id(body_role[1], body_role[2], mono_set, base_set)
        body_rgb = _reveal(body_rgb, body_role)
        s_rgb, s_tol, s_rem = _sel_for_role(is_body=True)
        zones.append(_make_body_zone(idx, "Body Color 1", body_rgb, kind, fid,
                                     intensity="100",
                                     hint=_car_hint("Use Pick Color mode - click your PRIMARY body color on the paint", s_rgb),
                                     select_rgb=s_rgb, select_tol=s_tol, remaining=s_rem))
        descriptions.append("Body 1 %s -> %s%s" % (_hex(body_rgb), fid,
                            (" @car %s" % _hex(s_rgb)) if s_rgb is not None else ""))
        idx += 1

    # ---- SECONDARY BODY (two-tone split) ----
    if body2_role:
        kind, fid = _resolve_id(body2_role[1], body2_role[2], mono_set, base_set)
        rgb = _reveal(pal(body2_role[3]), body2_role)
        # In SOLO mode the body already blankets the car; keep this as a
        # user-deletable suggestion (legacy palette selector) so it doesn't fight
        # the hero. In MULTI mode it claims the next real car region.
        s_rgb, s_tol, s_rem = (None, 40, False) if _car_solo else _sel_for_role(is_body=False)
        zones.append(_make_body_zone(idx, "Body Color 2", rgb, kind, fid,
                                     intensity="100",
                                     hint=_car_hint("Click the secondary body color (the two-tone split). Delete if unused.", s_rgb),
                                     select_rgb=s_rgb, select_tol=s_tol, remaining=s_rem))
        descriptions.append("Body 2 %s -> %s%s" % (_hex(rgb), fid,
                            (" @car %s" % _hex(s_rgb)) if s_rgb is not None else ""))
        idx += 1

    # ---- FEATURE (hero hood/roof) — unless a zone hint overrides the same part ----
    hinted_parts = {h["part"] for h in hints}
    feature_is_hinted = bool(hinted_parts & {"Hood", "Roof"})
    if feature_role and not feature_is_hinted:
        kind, fid = _resolve_id(feature_role[1], feature_role[2], mono_set, base_set)
        rgb = _reveal(pal(feature_role[3]), feature_role)
        s_rgb, s_tol, s_rem = (None, 40, False) if _car_solo else _sel_for_role(is_body=False)
        zones.append(_make_body_zone(idx, "Hood / Roof Feature", rgb, kind, fid,
                                     intensity="100",
                                     hint=_car_hint("Magic Wand / Draw Region over the hood or roof for the hero panel. Delete if unused.", s_rgb),
                                     select_rgb=s_rgb, select_tol=s_tol, remaining=s_rem))
        descriptions.append("Feature %s -> %s%s" % (_hex(rgb), fid,
                            (" @car %s" % _hex(s_rgb)) if s_rgb is not None else ""))
        idx += 1

    # ---- ACCENT (small area: stripes/mirrors/wing) ----
    if accent_role and len(zones) < 6:
        kind, fid = _resolve_id(accent_role[1], accent_role[2], mono_set, base_set)
        s_rgb, s_tol, s_rem = (None, 40, False) if _car_solo else _sel_for_role(is_body=False)
        zones.append(_make_body_zone(idx, "Accent", accent_rgb, kind, fid,
                                     intensity="100",
                                     hint=_car_hint("Stripes, mirrors, wing or splitter accent. Delete if unused.", s_rgb),
                                     select_rgb=s_rgb, select_tol=s_tol, remaining=s_rem))
        descriptions.append("Accent %s -> %s%s" % (_hex(accent_rgb), fid,
                            (" @car %s" % _hex(s_rgb)) if s_rgb is not None else ""))
        idx += 1

    # ---- ZONE HINTS (carbon hood, chrome roof...) override / add dedicated parts ----
    for hn in hints:
        if len(zones) >= 8:
            break
        part = hn["part"]
        if hn["family"]:
            kind, fid = _resolve_family(hn["family"], mono_set, base_set)
        elif feature_role and part in ("Hood", "Roof"):
            kind, fid = _resolve_id(feature_role[1], feature_role[2], mono_set, base_set)
        else:
            kind, fid = _resolve_family("carbon", mono_set, base_set)
        rgb = hn["rgb"] if hn["rgb"] is not None else pal(1)
        zones.append(_make_body_zone(idx, part, rgb, kind, fid, intensity="100",
                                     hint="Magic Wand / Draw Region over the %s." % part.lower()))
        descriptions.append("%s -> %s" % (part, fid))
        idx += 1

    # ---- Number color (readable, livery-matched) ----
    number_rgb = theme.get("number") or _readable_number_color(body_rgb, accent_rgb)

    # ---- Standard non-color zones + remaining safety net ----
    zones.extend(_non_color_zones(idx, number_rgb))
    return zones, descriptions, number_rgb


# ---------------------------------------------------------------------------
# FALLBACK COMPOSER — used when no theme is available (themes module missing) or
# nothing matched: builds from explicit colors + legacy keyword families so the
# module is still useful and ALWAYS returns a renderable, non-flat design.
# ---------------------------------------------------------------------------
def _detect_families(prompt: str, exclude_pos=None) -> List[Tuple[str, int]]:
    exclude_pos = exclude_pos or set()
    fams: List[Tuple[str, int]] = []
    seen = set()
    for i, w in enumerate(re.findall(r"[a-zA-Z]+", (prompt or "").lower())):
        if i in exclude_pos:
            continue
        fam = _KEYWORD_FAMILY.get(w)
        if fam and fam not in seen:
            seen.add(fam)
            fams.append((fam, i))
    return fams


def _compose_fallback(prompt: str, colors: List[Dict], hints: List[Dict],
                      consumed: set, mono_set, base_set,
                      car_plan: Optional[Dict] = None):
    families = _detect_families(prompt, exclude_pos=consumed)
    resolved: List[Tuple[str, str, str, int]] = []
    seen_ids = set()
    for fam, fpos in families:
        kind, fid = _resolve_family(fam, mono_set, base_set)
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        resolved.append((fam, kind, fid, fpos))
        if len(resolved) >= 4:
            break
    if not resolved:
        if colors:
            resolved = [("gloss", "base", _resolve_family("gloss", mono_set, base_set)[1], 0)]
        else:
            resolved = [("ghost", "mono", _resolve_family("ghost", mono_set, base_set)[1], 0)]
    if not colors:
        colors = [{"rgb": (24, 24, 28), "hex": "#18181c", "words": ["default-black"], "pos": -1}]

    n_body = max(1, min(4, max(len(colors), len(resolved))))
    zones: List[Dict] = []
    idx = 1
    descriptions: List[str] = []
    used_styles = set()
    pairs: List[Tuple[Dict, Optional[Tuple]]] = []
    for col in colors[:n_body]:
        cpos = col.get("pos", 0)
        best = min(resolved, key=lambda r: abs(r[3] - cpos)) if resolved else None
        pairs.append((col, best))
        if best is not None:
            used_styles.add(best[2])
    leftover = [r for r in resolved if r[2] not in used_styles]
    palette_default = colors[0]["rgb"] if colors else (24, 24, 28)
    for r in leftover:
        if len(pairs) >= 4:
            break
        pairs.append(({"rgb": palette_default, "hex": _hex(palette_default),
                       "words": ["(style)"], "pos": r[3]}, r))

    # Car-region selectors (same coverage fix as the theme path): drive each
    # body zone's SELECTOR from the loaded car's dominant colors when supplied.
    _fb_sel = list(car_plan.get("selectors", [])) if car_plan else []
    _fb_solo = bool(car_plan and car_plan.get("mode") == "solo")

    body_rgb = pairs[0][0]["rgb"] if pairs else (24, 24, 28)
    for b, (col, sty) in enumerate(pairs[:4]):
        if sty is None:
            kind, fid = "base", _resolve_family("gloss", mono_set, base_set)[1]
        else:
            _fam, kind, fid, _fp = sty
        nm = "Body Color %d" % (b + 1)
        s_rgb = s_tol = None
        if _fb_sel:
            if b == 0 and _fb_solo:
                s_rgb, s_tol = _fb_sel[0]
            elif _fb_solo:
                s_rgb, s_tol = None, None  # solo: keep extras as suggestions
            elif b < len(_fb_sel):
                s_rgb, s_tol = _fb_sel[b]
            else:
                s_rgb, s_tol = _fb_sel[0][0], 40
        zones.append(_make_body_zone(idx, nm, col["rgb"], kind, fid, intensity="100",
                                     hint=("Use Pick Color mode - click your PRIMARY body color on the paint"
                                           if b == 0 else "Click body color %d (delete if unused)" % (b + 1)),
                                     select_rgb=s_rgb, select_tol=(s_tol if s_tol is not None else 40)))
        descriptions.append("%s -> %s%s" % (" ".join(col["words"]), fid,
                            (" @car %s" % _hex(s_rgb)) if s_rgb is not None else ""))
        idx += 1

    for hn in hints:
        if len(zones) >= 8:
            break
        part = hn["part"]
        if hn["family"]:
            kind, fid = _resolve_family(hn["family"], mono_set, base_set)
        else:
            kind, fid = _resolve_family("carbon", mono_set, base_set)
        rgb = hn["rgb"] if hn["rgb"] is not None else (28, 30, 34)
        zones.append(_make_body_zone(idx, part, rgb, kind, fid, intensity="100",
                                     hint="Magic Wand / Draw Region over the %s." % part.lower()))
        descriptions.append("%s -> %s" % (part, fid))
        idx += 1

    number_rgb = _readable_number_color(body_rgb, body_rgb)
    zones.extend(_non_color_zones(idx, number_rgb))
    return zones, descriptions, [r[0] for r in resolved], [r[2] for r in resolved]


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
def design_from_prompt(prompt: str, seed: int = 51, car_colors=None) -> Dict:
    """Turn a natural-language vibe prompt into a renderable multi-zone livery.

    Args:
        prompt: free text, e.g. "menacing matte black with toxic-green fracture
            and a carbon hood".
        seed: deterministic seed (echoed in the result). Used to make tie-breaks
            stable and to pick which secondary theme seeds a variation.
        car_colors: OPTIONAL list of the LOADED paint's dominant colors, most-
            area first — either the ``extract_dominant_colors`` shape
            (``[{"rgb":(r,g,b), "weight":frac}, ...]``), bare RGB triples, or
            hex strings. When provided, the design's body/feature/accent FINISHES
            are mapped onto the car's REAL regions (body finish -> largest region,
            feature -> 2nd, accent -> 3rd) so the design actually COVERS and
            transforms the loaded car. A near-solid car routes the hero body
            finish onto a broad selector so it dominates the whole car. When
            ``None`` (the default) the legacy palette-color selector behavior is
            used unchanged — fully backward compatible.

    Returns:
        ``{"zones": [...], "explanation": "...", "_meta": {...}}`` — ``zones`` is
        shaped for ``shokker_engine_v2.build_multi_zone(..., preview_mode=True)``.
        ``_meta["variations"]`` holds 0-2 alternate complete designs (UI-optional;
        the top-level shape is unchanged for backward compatibility).
    """
    prompt = str(prompt or "").strip()
    try:
        seed_int = int(seed)
    except (TypeError, ValueError):
        seed_int = 51
    mono_set, base_set = _live_registries()

    # Map the design's roles onto the LOADED car's dominant regions (coverage fix).
    car_plan = _car_color_plan(car_colors)

    # Part-hints first so their tokens don't double as body colors.
    hints, consumed = _detect_zone_hints(prompt)
    colors = _parse_colors(prompt, exclude_pos=consumed)

    # WORDS consumed by a zone hint (e.g. "carbon" in "carbon hood") are DEMOTED
    # in theme scoring so a hood material can't steal the whole-body vibe.
    _hint_words = re.findall(r"[a-zA-Z]+", prompt.lower())
    demoted = {_hint_words[i] for i in consumed if 0 <= i < len(_hint_words)}
    # the PART word itself ("hood"/"roof") never names a theme vibe — demote it too.
    demoted |= {w.lower() for w in _ZONE_PART_WORDS}

    ranked = _rank_themes(prompt, demoted=demoted)
    theme_path = bool(ranked) or (_themes is not None and not prompt) or (_themes is not None and not ranked and colors)

    if _themes is None:
        # No theme library available — fall back to the legacy family composer.
        zones, body_desc, fams, finishes = _compose_fallback(
            prompt, colors, hints, consumed, mono_set, base_set, car_plan=car_plan)
        explanation = ("Prompt parsed into %d body/feature zone(s). %s. Number/Art/"
                       "Sponsor zones and a gloss 'Everything Else' safety net were "
                       "added automatically."
                       % (len(body_desc), "; ".join(body_desc) or "default look"))
        return {"zones": zones, "explanation": explanation,
                "_meta": {"seed": seed_int, "theme": None, "match_score": 0.0,
                          "colors": [c["hex"] for c in colors], "families": fams,
                          "finishes": finishes, "hints": [h["part"] for h in hints],
                          "car_mapped": car_plan is not None,
                          "car_mode": (car_plan or {}).get("mode"),
                          "variations": []}}

    # Pick the primary theme: best match, else (if explicit colors only) the
    # default show-stopper, else the default.
    if ranked:
        primary = ranked[0][1]
        primary_score = ranked[0][0]
    else:
        primary = _default_theme()
        primary_score = 0.0

    palette = _blend_palette(primary, colors)
    zones, descriptions, number_rgb = _compose_design(
        primary, palette, hints, mono_set, base_set, car_plan=car_plan)

    # ---- VARIATIONS — 2 alternate complete designs that are DISTINCT + on-vibe.
    # _select_variations enforces a different finish FAMILY per option and prefers
    # themes that share a vibe tag with the primary (so all 3 read on-theme), with
    # the default show-stopper only as a last-resort floor. This is the core of the
    # viral "pick one of 3 stunning, genuinely different looks" moment. ----
    variations: List[Dict] = []
    for alt in _select_variations(primary, ranked, want=2, colors=colors):
        alt_palette = _blend_palette(alt, colors)
        v_zones, v_desc, v_num = _compose_design(alt, alt_palette, hints, mono_set, base_set,
                                                 car_plan=car_plan)
        variations.append({
            "name": alt["name"],
            "zones": v_zones,
            "palette": [_hex(c) for c in alt_palette],
            "mood": alt.get("mood", ""),
            "explanation": "Alternate: %s — %s." % (alt["name"], alt.get("mood", "")),
        })

    # ---- Human-readable explanation ----
    pal_hex = ", ".join(_hex(c) for c in palette)
    explicit = (" Honored your color(s): %s." % ", ".join(c["hex"] for c in colors)) if colors else ""
    hint_txt = (" Dedicated %s zone(s)." % ", ".join(h["part"] for h in hints)) if hints else ""
    explanation = (
        "Matched theme “%s” (%s). Palette %s.%s%s Composition: %s. "
        "Car Number color suggested for contrast; Art/Sponsor zones and a gloss "
        "'Everything Else' safety net were added automatically."
        % (primary["name"], primary.get("mood", ""), pal_hex, explicit, hint_txt,
           "; ".join(descriptions))
    )

    return {
        "zones": zones,
        "explanation": explanation,
        "_meta": {
            "seed": seed_int,
            "theme": primary["name"],
            "match_score": round(float(primary_score), 2),
            "mood": primary.get("mood", ""),
            "palette": [_hex(c) for c in palette],
            "colors": [c["hex"] for c in colors],
            "finishes": [z.get("finish") or z.get("base") for z in zones
                         if z.get("colorMode") == "multi" and (z.get("finish") or z.get("base"))],
            "hints": [h["part"] for h in hints],
            "number_color": _hex(number_rgb),
            "car_mapped": car_plan is not None,
            "car_mode": (car_plan or {}).get("mode"),
            "car_regions": [_hex(rgb) for rgb, _t in (car_plan or {}).get("selectors", [])],
            "variations": variations,
            "alternates": [v["name"] for v in variations],
        },
    }


__all__ = ["design_from_prompt", "extract_dominant_colors"]
