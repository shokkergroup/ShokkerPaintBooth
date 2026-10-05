"""Per-preset MATERIAL PROFILES for Spec Sculpt — the source of real diversity.

Background
----------
The original Spec Sculpt presets only differed by a global ``mrc=(M,R,Cc)``
multiplier applied on top of one shared, paint-derived scratch spec. Every preset
therefore produced the *same spatial structure* (it tracked the source paint's
luminance + edges) and merely scaled it — so "Vantablack" and "Show Chrome" looked
identical in the Shokk-the-World gallery.

This module gives every preset a genuine **material identity**:

* a **baseline reflectance** ``(m_base, r_base, cc_base)`` — the resting M / Roughness /
  Clearcoat level of the real material (chrome is bright+smooth, matte is dark+rough,
  candy is deep-clearcoat, etc.). This is paint-INDEPENDENT, so families diverge hard.
* a **spatial texture** chosen per family (uniform / flake / brushed / weave / forged /
  hammered / hex / crackle / bands / droplets / marble / scales / sparkle / micrograin),
  so chrome reads smooth, flake reads speckled, carbon reads woven, brushed reads
  directional — at a glance, in the thumbnail.
* an **assertiveness** ``assert_k`` controlling how strongly the profile dominates the
  paint-derived base, and a **relief** term that still lets the livery's graphics
  modulate the spec (it stays paint-aware, just not paint-DOMINATED).
* a **chroma** carrier for pearl / candy / holographic / oil-slick travel.

Channel convention matches the rest of the repo (see
``VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md``): index 0 = M (metallic), 1 = R
(roughness; LOWER = shinier), 2 = Cc (clearcoat). The shared engine
(``_scratch_spec_from_paint`` + Viva pre/post) is left completely untouched — all
per-preset character lives here, so the 1009 image/monolithic finishes are unaffected.
"""
from __future__ import annotations

import cv2
import numpy as np

from engine.spec_sculpt.presets import SPEC_SCULPT_PRESETS, _PRESET_MRC_BY_ID

# ---------------------------------------------------------------------------
# Profile schema (per preset id):
#   m_base, r_base, cc_base : 0..255 resting reflectance levels
#   texture   : spatial texture family name (see _apply_texture)
#   tex_amp   : 0..~1 amplitude of that texture's modulation
#   tex_scale : spatial frequency multiplier (bigger = finer)
#   assert_k  : 0..1 how strongly the profile target beats the paint-derived layer
#   lock_k    : 0..1 how strongly the final character-lock re-asserts identity post-VM
#   chroma    : 0..1 chromatic carrier strength (pearl/candy/holo travel)
#   relief    : 0..1 how much the source paint (edges/luma) still modulates the spec
# ---------------------------------------------------------------------------

_CATEGORY_BASE: dict[str, dict] = {
    "Gloss & chrome": dict(
        m_base=226, r_base=54, cc_base=120, texture="uniform", tex_amp=0.06,
        tex_scale=1.0, assert_k=0.82, lock_k=0.80, chroma=0.05, relief=0.30),
    "Pearl & candy": dict(
        m_base=120, r_base=82, cc_base=204, texture="uniform", tex_amp=0.05,
        tex_scale=1.0, assert_k=0.74, lock_k=0.66, chroma=0.50, relief=0.34),
    "Matte & velvet": dict(
        m_base=32, r_base=232, cc_base=16, texture="micrograin", tex_amp=0.05,
        tex_scale=1.4, assert_k=0.88, lock_k=0.86, chroma=0.0, relief=0.12),
    "Flake & interference": dict(
        m_base=150, r_base=124, cc_base=96, texture="flake", tex_amp=0.92,
        tex_scale=1.0, assert_k=0.62, lock_k=0.52, chroma=0.18, relief=0.34),
    "Brushed & machined": dict(
        m_base=168, r_base=132, cc_base=80, texture="brushed", tex_amp=0.55,
        tex_scale=1.0, assert_k=0.72, lock_k=0.64, chroma=0.06, relief=0.24),
    "Carbon & weave": dict(
        m_base=120, r_base=132, cc_base=110, texture="weave", tex_amp=0.70,
        tex_scale=1.0, assert_k=0.72, lock_k=0.64, chroma=0.05, relief=0.20),
    "Weathered & raw": dict(
        m_base=98, r_base=176, cc_base=70, texture="crackle", tex_amp=0.55,
        tex_scale=1.0, assert_k=0.62, lock_k=0.52, chroma=0.05, relief=0.55),
    "Liquid & exotic": dict(
        m_base=180, r_base=82, cc_base=150, texture="marble", tex_amp=0.55,
        tex_scale=1.0, assert_k=0.68, lock_k=0.56, chroma=0.42, relief=0.30),
    "Glow & neon": dict(
        m_base=142, r_base=110, cc_base=152, texture="uniform", tex_amp=0.10,
        tex_scale=1.0, assert_k=0.56, lock_k=0.46, chroma=0.48, relief=0.60),
    "Surface & organic": dict(
        m_base=120, r_base=128, cc_base=110, texture="hammered", tex_amp=0.55,
        tex_scale=1.0, assert_k=0.66, lock_k=0.56, chroma=0.08, relief=0.34),
    "Stealth & tactical": dict(
        m_base=26, r_base=236, cc_base=12, texture="micrograin", tex_amp=0.035,
        tex_scale=1.4, assert_k=0.90, lock_k=0.90, chroma=0.0, relief=0.08),
    "Show & specialty": dict(
        m_base=172, r_base=80, cc_base=176, texture="flake", tex_amp=0.50,
        tex_scale=1.0, assert_k=0.62, lock_k=0.52, chroma=0.40, relief=0.30),
}

_DEFAULT_BASE = dict(
    m_base=140, r_base=120, cc_base=110, texture="uniform", tex_amp=0.1,
    tex_scale=1.0, assert_k=0.6, lock_k=0.5, chroma=0.1, relief=0.4)


def _tagset(preset: dict) -> set[str]:
    return {str(t).lower() for t in preset.get("tags", [])}


def _refine_with_tags(prof: dict, preset: dict) -> dict:
    """Tag-driven within-family specialization so presets in one family still diverge."""
    p = dict(prof)
    tags = _tagset(preset)
    label = str(preset.get("label", "")).lower()
    pid = str(preset.get("id", "")).lower()

    def has(*keys):
        return any(k in tags or k in pid or k in label for k in keys)

    # ---- texture overrides by motif tag (cross-family) ----
    if has("weave", "carbon", "kevlar", "aramid"):
        p["texture"] = "weave"
    if has("forged", "marble", "vein"):
        p["texture"] = "marble" if has("marble", "vein") else "forged"
    if has("honeycomb", "hex", "cell") and not has("snake", "croc", "scale"):
        p["texture"] = "hex"
    if has("scale", "snake", "croc", "reptile"):
        p["texture"] = "scales"
    if has("hammered", "dimple"):
        p["texture"] = "hammered"
    if has("brushed", "hairline", "directional", "machined", "billet", "cnc",
            "scratched", "wear", "bare", "wood", "grain"):
        p["texture"] = "brushed"
    if has("knurled", "cross", "mesh", "perforated", "holes", "grip"):
        p["texture"] = "weave"
        p["tex_scale"] = 1.6
    if has("water", "beads", "droplet", "bead"):
        p["texture"] = "droplets"
    if has("crackle", "fracture", "ice", "frost", "crystal", "crack", "rust", "patina",
            "oxide", "worn", "chips", "combat", "mud", "rally"):
        p["texture"] = "crackle"
    if has("stars", "sparse", "night", "galaxy", "space", "starlight"):
        p["texture"] = "sparkle"
    if has("circuit", "trace", "digital", "camo", "data"):
        p["texture"] = "bands"
    if has("static", "noise", "grain", "concrete", "stone", "chalk", "dust", "primer",
            "suede", "leather", "nap", "powder", "dry"):
        p["texture"] = "micrograin"

    # ---- flake sizing ----
    if p["texture"] == "flake":
        if has("coarse", "chunky", "show", "storm"):
            p["tex_scale"] = 0.55
        elif has("micro", "fine", "oem", "diamond", "crisp"):
            p["tex_scale"] = 1.7
        if has("glitter", "diamond", "dense"):
            p["tex_amp"] = min(1.0, p["tex_amp"] + 0.1)

    # ---- baseline nudges by descriptive tag ----
    if has("candy", "lacquer", "wet", "rain", "deep", "glass", "resin", "liquid glass"):
        p["cc_base"] = min(235, p["cc_base"] + 36)
        p["r_base"] = max(40, p["r_base"] - 14)
    if has("mirror", "max"):
        p["m_base"] = min(244, p["m_base"] + 14)
        p["r_base"] = max(34, p["r_base"] - 12)
    if has("black", "dark", "stealth", "piano", "void", "vanta", "night"):
        p["m_base"] = max(18, int(p["m_base"] * 0.72))
        if has("piano", "glass") and not has("chrome"):
            p["m_base"] = 70  # piano black: low metal, deep gloss
            p["cc_base"] = 200
            p["r_base"] = 58
    if has("metal", "metallic", "chrome", "steel", "billet") and p["m_base"] < 110:
        p["m_base"] = max(p["m_base"], 150)  # matte-metallic / matte-chrome keep real metal
    if has("warm", "gold", "copper", "bronze", "rose", "champagne", "ember", "infrared", "rootbeer", "brown"):
        p["_warm"] = 1.0
    if has("cool", "blue", "ice", "titanium", "snow", "cyan", "teal"):
        p["_cool"] = 1.0
    if has("green", "toxic", "acid", "lime"):
        p["_green"] = 1.0
    # chroma boosts
    if has("flip", "travel", "chameleon", "holo", "holographic", "diffraction", "rainbow",
            "iridescent", "oil", "prism", "aurora", "colorshift", "thermal", "shift"):
        p["chroma"] = max(p["chroma"], 0.62)
    if has("pearl", "opal", "ghost"):
        p["chroma"] = max(p["chroma"], 0.40)

    # ---- liquid/exotic motif specials ----
    if has("mercury", "molten", "ferro", "spiky", "magnetic", "mercury"):
        p["texture"] = "marble"
        p["m_base"] = min(238, p["m_base"] + 30)
        p["r_base"] = max(46, p["r_base"] - 10)
    if has("neon", "edge", "glow", "uv", "blacklight", "emissive"):
        p["relief"] = max(p["relief"], 0.6)

    return p


def _profile_for(preset: dict) -> dict:
    base = _CATEGORY_BASE.get(str(preset.get("category", "")), _DEFAULT_BASE)
    prof = _refine_with_tags(base, preset)
    # Fold the existing per-preset mrc in as a gentle ±15% baseline nudge so the curated
    # mrc ordering still differentiates presets within a family (mirror vs polished, etc.).
    mrc = _PRESET_MRC_BY_ID.get(str(preset.get("id", "")), (1.0, 1.0, 1.0))
    sm = lambda v, mult: float(np.clip(v * (0.78 + 0.22 * mult), 0, 255))
    prof["m_base"] = sm(prof["m_base"], mrc[0])
    prof["r_base"] = float(np.clip(prof["r_base"] * (0.86 + 0.14 * mrc[1]), 15, 255))
    prof["cc_base"] = sm(prof["cc_base"], mrc[2])
    return prof


MATERIAL_PROFILE_BY_ID: dict[str, dict] = {
    str(p["id"]): _profile_for(p) for p in SPEC_SCULPT_PRESETS
}


# ===========================================================================
# Spatial texture generators — each returns a float field in roughly [-1, 1]
# (or [0, 1] for additive sparkle types), deterministic per seed.
# ===========================================================================

def _coords(h: int, w: int):
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    return xs, ys


def _warped_coords(seed: int, h: int, w: int, amt: float = 0.03):
    """Coords nudged by low-freq noise so geometric textures read hand-made, not CG-perfect."""
    xs, ys = _coords(h, w)
    wx = _lowfreq_cloud(seed ^ 0x1A2B, h, w, octaves=2) * amt
    wy = _lowfreq_cloud(seed ^ 0x3C4D, h, w, octaves=2) * amt
    return (xs + wx).astype(np.float32), (ys + wy).astype(np.float32)


def _lowfreq_cloud(seed: int, h: int, w: int, octaves: int = 3) -> np.ndarray:
    """Smooth value-noise cloud in [-1, 1] for organic large-scale variation.

    Built at a bounded working resolution then upscaled once — the cloud is
    intentionally low-frequency so this is visually identical to full-res synthesis
    but far cheaper at 2048 (the owner cares about render time)."""
    rng = np.random.default_rng((seed ^ 0x9E37) & 0xFFFFFFFF)
    big = max(h, w)
    rr = min(big, 384)
    bw = max(8, int(round(rr * w / big)))
    bh = max(8, int(round(rr * h / big)))
    acc = np.zeros((bh, bw), dtype=np.float32)
    amp = 1.0
    tot = 0.0
    cells = 3
    for _ in range(octaves):
        g = rng.random((cells, cells), dtype=np.float32)
        up = cv2.resize(g, (bw, bh), interpolation=cv2.INTER_CUBIC)
        acc += (up - 0.5) * 2.0 * amp
        tot += amp
        amp *= 0.5
        cells *= 2
    acc /= max(tot, 1e-6)
    if (bh, bw) != (h, w):
        acc = cv2.resize(acc, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(acc, -1.0, 1.0)


# Global pattern-density multiplier. These 2048² maps cover an ENTIRE car body, so
# what looks fine in a thumbnail is huge on the vehicle — frequencies are kept
# frame-relative (so a 320px preview matches the 2048 render cell-for-cell) and
# scaled UP here so cells stay small on the car. Bump this for finer patterns globally.
_TEX_DENSITY = 3.0


def _tex_flake(seed, h, w, scale):
    """Sparse bright metal-flake specks (0..1, additive). Fine on the car body."""
    rng = np.random.default_rng((seed ^ 0xC0FFEE) & 0xFFFFFFFF)
    dens = _TEX_DENSITY * scale
    gw = max(8, int(h * dens / 9.0))
    gh = max(8, int(w * dens / 9.0))
    thresh = 0.965 - 0.02 * np.clip(scale - 1.0, -0.5, 1.0)
    grid = rng.random((gw, gh), dtype=np.float32)
    flake = cv2.resize((grid > thresh).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    # secondary finer dust
    grid2 = rng.random((gw * 2, gh * 2), dtype=np.float32)
    dust = cv2.resize((grid2 > 0.986).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    return np.clip(flake + dust * 0.6, 0.0, 1.0)


def _tex_sparkle(seed, h, w, scale):
    """Very sparse bright pinpoints on an otherwise dark field (0..1, additive)."""
    rng = np.random.default_rng((seed ^ 0x57A4) & 0xFFFFFFFF)
    dens = _TEX_DENSITY * scale
    gw = max(12, int(h * dens / 4.0))
    gh = max(12, int(w * dens / 4.0))
    grid = rng.random((gw, gh), dtype=np.float32)
    pts = cv2.resize((grid > 0.991).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(pts, (0, 0), 0.6)


def _tex_brushed(seed, h, w, scale):
    """Directional brushed-metal streaks along X, varying in Y (-1..1)."""
    rng = np.random.default_rng((seed ^ 0xB5) & 0xFFFFFFFF)
    rows = rng.random(h).astype(np.float32)
    rows = cv2.GaussianBlur(rows.reshape(h, 1), (0, 0), 1.5).reshape(h)
    field = np.repeat((rows - 0.5).reshape(h, 1), w, axis=1) * 2.0
    xs, ys = _coords(h, w)
    fine = np.sin(ys * (220.0 * scale) + rng.random() * 6.28).astype(np.float32) * 0.35
    streak = np.tile(rng.random((h, 1)).astype(np.float32), (1, w))
    field = field * 0.8 + (fine) + (streak - 0.5) * 0.2
    return np.clip(field, -1.0, 1.0)


def _tex_weave(seed, h, w, scale):
    """2x2 twill carbon weave — fine over/under tow pattern (-1..1).
    Frequency is deliberately high: real carbon tows are tiny on a full car body."""
    xs, ys = _warped_coords(seed, h, w, 0.012)
    n = max(16.0, 18.0 * _TEX_DENSITY * scale)
    # soft (tanh) tows instead of hard sign → far less moire when downscaled
    fx = np.tanh(np.sin(xs * np.pi * n) * 1.6)
    fy = np.tanh(np.sin(ys * np.pi * n) * 1.6)
    twill = np.sin((xs + ys) * np.pi * n * 0.5)
    weave = fx * 0.5 + fy * 0.5
    weave = weave * 0.72 + twill * 0.28
    return np.clip(weave, -1.0, 1.0)


def _tex_forged(seed, h, w, scale):
    """Marbled forged-carbon chunks — thresholded low-freq noise (-1..1)."""
    c = _lowfreq_cloud(seed ^ 0x1234, h, w, octaves=4)
    chunk = np.tanh(c * 2.4)
    return np.clip(chunk, -1.0, 1.0)


def _tex_hammered(seed, h, w, scale):
    """Hand-hammered dimples — rounded cell domes (-1..1)."""
    xs, ys = _warped_coords(seed, h, w, 0.035)
    n = max(9.0, 9.0 * _TEX_DENSITY * scale)
    d = np.cos(xs * np.pi * n) * np.cos(ys * np.pi * n)
    d2 = np.cos((xs + 0.5 / n) * np.pi * n) * np.cos((ys + 0.5 / n) * np.pi * n)
    dome = np.maximum(d, d2 * 0.7)
    return np.clip(dome, -1.0, 1.0)


def _tex_hex(seed, h, w, scale):
    """Honeycomb hex cells (-1..1)."""
    xs, ys = _warped_coords(seed, h, w, 0.016)
    n = max(11.0, 11.0 * _TEX_DENSITY * scale)
    a = np.sin(xs * np.pi * n)
    b = np.sin((xs * 0.5 + ys * 0.866) * np.pi * n)
    c = np.sin((xs * 0.5 - ys * 0.866) * np.pi * n)
    hexf = (np.abs(a) + np.abs(b) + np.abs(c)) / 3.0
    return np.clip((hexf - 0.5) * 2.0, -1.0, 1.0)


def _tex_crackle(seed, h, w, scale):
    """Organic crack lines / patchy oxidation — gradient of noise (-1..1)."""
    c = _lowfreq_cloud(seed ^ 0xCAFE, h, w, octaves=4)
    gx = cv2.Sobel(c, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(c, cv2.CV_32F, 0, 1, ksize=3)
    cracks = np.sqrt(gx * gx + gy * gy)
    den = float(np.percentile(cracks, 96)) + 1e-4
    cracks = np.clip(cracks / den, 0.0, 1.0)
    # blend patchy field with crack lines
    return np.clip(c * 0.5 + (cracks - 0.4) * 1.4, -1.0, 1.0)


def _tex_bands(seed, h, w, scale):
    """Tech/circuit-style traces — fine grid of lines (-1..1)."""
    rng = np.random.default_rng((seed ^ 0xBA2D) & 0xFFFFFFFF)
    xs, ys = _warped_coords(seed, h, w, 0.015)
    n = max(11.0, 11.0 * _TEX_DENSITY * scale)
    # soft tow lines (tanh) so dense traces don't moire when downscaled
    b1 = np.tanh(np.sin(xs * np.pi * n + rng.random() * 6.28) * 2.2)
    b2 = np.tanh(np.sin(ys * np.pi * n * 1.3 + rng.random() * 6.28) * 2.2)
    return np.clip(b1 * 0.6 + b2 * 0.4, -1.0, 1.0)


def _tex_droplets(seed, h, w, scale):
    """Beaded water droplets — sparse high domes (0..1, additive)."""
    rng = np.random.default_rng((seed ^ 0xD0D0) & 0xFFFFFFFF)
    dens = _TEX_DENSITY * scale
    gw = max(14, int(h * dens / 6.0))
    gh = max(14, int(w * dens / 6.0))
    grid = rng.random((gw, gh), dtype=np.float32)
    beads = cv2.resize((grid > 0.97).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    return cv2.GaussianBlur(beads, (0, 0), max(0.8, w / 360.0))


def _tex_marble(seed, h, w, scale):
    """Turbulent flowing veins (-1..1)."""
    turb = _lowfreq_cloud(seed ^ 0x7777, h, w, octaves=5)
    xs, ys = _coords(h, w)
    n = max(8.0, 8.0 * _TEX_DENSITY * 0.7 * scale)
    vein = np.sin((xs + ys + turb * 0.8) * np.pi * n)
    return np.clip(vein * 0.7 + turb * 0.3, -1.0, 1.0)


def _tex_scales(seed, h, w, scale):
    """Reptile-scale cells (-1..1)."""
    xs, ys = _warped_coords(seed, h, w, 0.02)
    n = max(12.0, 12.0 * _TEX_DENSITY * scale)
    row = np.floor(ys * n)
    offset = (row % 2) * (0.5 / n)
    sc = np.cos((xs + offset) * np.pi * n) * np.cos(ys * np.pi * n)
    return np.clip(np.abs(sc) * 2.0 - 1.0, -1.0, 1.0)


def _tex_micrograin(seed, h, w, scale):
    """Fine even matte grain (-1..1)."""
    rng = np.random.default_rng((seed ^ 0x6A11) & 0xFFFFFFFF)
    g = rng.random((h, w), dtype=np.float32)
    g = cv2.GaussianBlur(g, (0, 0), max(0.5, 0.8 / max(scale, 0.5)))
    return np.clip((g - 0.5) * 2.0, -1.0, 1.0)


def _tex_uniform(seed, h, w, scale):
    return np.zeros((h, w), dtype=np.float32)


_TEXTURE_FNS = {
    "uniform": _tex_uniform,
    "flake": _tex_flake,
    "sparkle": _tex_sparkle,
    "brushed": _tex_brushed,
    "weave": _tex_weave,
    "forged": _tex_forged,
    "hammered": _tex_hammered,
    "hex": _tex_hex,
    "crackle": _tex_crackle,
    "bands": _tex_bands,
    "droplets": _tex_droplets,
    "marble": _tex_marble,
    "scales": _tex_scales,
    "micrograin": _tex_micrograin,
}

# Texture types that ADD energy (specks/beads) vs MODULATE around the baseline.
_ADDITIVE_TEX = {"flake", "sparkle", "droplets"}


def _paint_cues(tex_rgb_hwc: np.ndarray):
    tex = np.asarray(tex_rgb_hwc[:, :, :3], dtype=np.float32)
    r, g, b = tex[..., 0], tex[..., 1], tex[..., 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.clip((mx - mn) / (mx + 1e-6), 0.0, 1.0)
    gu8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    lap = np.abs(cv2.Laplacian(gu8, cv2.CV_32F, ksize=3))
    den = float(np.percentile(lap, 99.0)) + 1e-3
    edge = cv2.GaussianBlur(np.clip(lap / den, 0.0, 1.0), (0, 0), 1.0)
    return gray, sat, edge


def _hue_radians(tex_rgb_hwc: np.ndarray) -> np.ndarray:
    u8 = np.clip(tex_rgb_hwc[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    return hsv[:, :, 0].astype(np.float32) * (np.pi / 90.0)  # 0..2pi


def build_profile_target(prof: dict, tex_rgb_hwc: np.ndarray, seed: int,
                         cues=None) -> np.ndarray:
    """Return HxWx3 float target field (M, R, Cc) for a material profile."""
    h, w = tex_rgb_hwc.shape[:2]
    gray, sat, edge = cues if cues is not None else _paint_cues(tex_rgb_hwc)

    m_base = float(prof["m_base"])
    r_base = float(prof["r_base"])
    cc_base = float(prof["cc_base"])

    cloud = _lowfreq_cloud(seed, h, w)
    Mt = np.full((h, w), m_base, dtype=np.float32) + cloud * (m_base * 0.06)
    Rt = np.full((h, w), r_base, dtype=np.float32) + cloud * (r_base * 0.04)
    Cct = np.full((h, w), cc_base, dtype=np.float32) + cloud * (cc_base * 0.05)

    # ---- family spatial texture ----
    tex_name = str(prof.get("texture", "uniform"))
    amp = float(prof.get("tex_amp", 0.0))
    scale = float(prof.get("tex_scale", 1.0))
    if amp > 1e-4 and tex_name != "uniform":
        fn = _TEXTURE_FNS.get(tex_name, _tex_uniform)
        t = fn(seed, h, w, scale)
        if tex_name in _ADDITIVE_TEX:
            # bright metal specks: push M up + R down + Cc catch up
            Mt = Mt + t * (150.0 * amp)
            Rt = Rt - t * (70.0 * amp)
            Cct = Cct + t * (60.0 * amp)
        elif tex_name == "weave":
            # over/under: alternate metallic vs rough cells (strong read)
            Mt = Mt + t * (70.0 * amp)
            Rt = Rt - t * (60.0 * amp)
            Cct = Cct + np.abs(t) * (20.0 * amp)
        elif tex_name == "brushed":
            Mt = Mt + t * (55.0 * amp)
            Rt = Rt - t * (48.0 * amp)
        elif tex_name in ("hammered", "hex", "scales"):
            Mt = Mt + t * (52.0 * amp)
            Rt = Rt - t * (40.0 * amp)
            Cct = Cct + np.maximum(t, 0.0) * (40.0 * amp)
        elif tex_name in ("forged", "marble", "crackle", "bands"):
            Mt = Mt + t * (60.0 * amp)
            Rt = Rt - t * (44.0 * amp)
            Cct = Cct - t * (24.0 * amp)
        elif tex_name == "micrograin":
            Mt = Mt + t * (14.0 * amp)
            Rt = Rt + t * (26.0 * amp)
        else:
            Mt = Mt + t * (40.0 * amp)
            Rt = Rt - t * (30.0 * amp)

    # ---- chromatic carrier (pearl / candy / holo travel) ----
    chroma = float(prof.get("chroma", 0.0))
    if chroma > 1e-3:
        hue = _hue_radians(tex_rgb_hwc)
        xs, ys = _coords(h, w)
        ph = float(seed % 257) * (np.pi / 128.0)
        carrier = np.sin(hue * 2.3 + xs * 26.0 + ys * 19.0 + ph) * np.cos(hue * 1.5 - xs * 15.0 + ys * 31.0)
        carrier2 = np.sin(hue * 3.1 - ys * 34.0 + ph * 1.7)
        cw = (0.35 + 0.65 * sat) * chroma
        Cct = Cct + carrier * (78.0 * cw) + carrier2 * (30.0 * cw)
        Mt = Mt + carrier * (46.0 * cw)
        Rt = Rt - np.abs(carrier) * (26.0 * cw)

    # ---- warm/cool/green steering (paint-coupled, family-flagged) ----
    if prof.get("_warm"):
        warm = np.clip((tex_rgb_hwc[..., 0] - np.maximum(tex_rgb_hwc[..., 1], tex_rgb_hwc[..., 2]) * 0.9), 0, 1)
        Mt = Mt + warm * 30.0
        Cct = Cct + warm * 18.0
    if prof.get("_cool"):
        cool = np.clip((tex_rgb_hwc[..., 2] - np.maximum(tex_rgb_hwc[..., 0], tex_rgb_hwc[..., 1]) * 0.9), 0, 1)
        Cct = Cct + cool * 26.0
        Rt = Rt + cool * 12.0
    if prof.get("_green"):
        gdom = np.clip((tex_rgb_hwc[..., 1] - np.maximum(tex_rgb_hwc[..., 0], tex_rgb_hwc[..., 2])), 0, 1)
        Rt = Rt - gdom * 24.0
        Mt = Mt + gdom * 18.0

    # ---- paint relief: keep the livery's graphics readable in the spec ----
    relief = float(prof.get("relief", 0.0))
    if relief > 1e-3:
        bright = np.clip((gray - 0.42) / 0.5, -1.0, 1.0)
        Mt = Mt + relief * (edge * 70.0 + bright * 30.0 * sat)
        Cct = Cct + relief * (edge * 34.0 + np.maximum(bright, 0.0) * 26.0)
        Rt = Rt - relief * (edge * 40.0)

    out = np.empty((h, w, 3), dtype=np.float32)
    out[..., 0] = np.clip(Mt, 0.0, 255.0)
    out[..., 1] = np.clip(Rt, 15.0, 255.0)
    out[..., 2] = np.clip(Cct, 0.0, 255.0)
    return out


def reshape_layer_with_profile(layer: np.ndarray, preset_id: str,
                               tex_rgb_hwc: np.ndarray, seed: int, cues=None):
    """Return ``(reshaped_layer, target_rgb_or_None)``.

    Blends the paint-derived ``layer`` toward the profile target by ``assert_k`` —
    high for chrome/matte (identity dominates), lower for flake/pearl (paint + scratch
    detail kept). The target is returned so the caller can reuse it for the character
    lock instead of rebuilding it (saves a full synthesis at 2048)."""
    prof = MATERIAL_PROFILE_BY_ID.get(preset_id)
    if prof is None:
        return layer, None
    arr = np.asarray(layer, dtype=np.float32)
    target = build_profile_target(prof, tex_rgb_hwc, seed, cues=cues)
    k = float(prof.get("assert_k", 0.6))
    out = arr.copy()
    out[..., 0] = np.clip(target[..., 0] * k + arr[..., 0] * (1.0 - k), 0.0, 255.0)
    out[..., 1] = np.clip(target[..., 1] * k + arr[..., 1] * (1.0 - k), 15.0, 255.0)
    out[..., 2] = np.clip(target[..., 2] * k + arr[..., 2] * (1.0 - k), 0.0, 255.0)
    if arr.shape[2] > 3:
        out[..., 3] = arr[..., 3]
    return out, target


def apply_preset_material_profile(layer: np.ndarray, preset_id: str,
                                  tex_rgb_hwc: np.ndarray, seed: int,
                                  cues=None) -> np.ndarray:
    """Back-compat wrapper returning just the reshaped layer."""
    out, _ = reshape_layer_with_profile(layer, preset_id, tex_rgb_hwc, seed, cues=cues)
    return out


def blended_profile_for_stack(stack: list[tuple[str, float]]):
    """Weighted-average profile fields + the max lock_k for the character-lock pass.
    Returns (prof_or_None, lock_k)."""
    if not stack:
        return None, 0.0
    keys = ["m_base", "r_base", "cc_base", "tex_amp", "tex_scale", "assert_k", "chroma", "relief"]
    acc = {k: 0.0 for k in keys}
    lock_k = 0.0
    tw = 0.0
    tex_weight: dict[str, float] = {}
    warm = cool = green = 0.0
    for pid, wt in stack:
        prof = MATERIAL_PROFILE_BY_ID.get(pid)
        if prof is None:
            continue
        tw += wt
        for k in keys:
            acc[k] += float(prof.get(k, 0.0)) * wt
        lock_k = max(lock_k, float(prof.get("lock_k", 0.0)))
        tn = str(prof.get("texture", "uniform"))
        tex_weight[tn] = tex_weight.get(tn, 0.0) + wt
        warm += float(prof.get("_warm", 0.0)) * wt
        cool += float(prof.get("_cool", 0.0)) * wt
        green += float(prof.get("_green", 0.0)) * wt
    if tw <= 0:
        return None, 0.0
    blended = {k: acc[k] / tw for k in keys}
    blended["texture"] = max(tex_weight, key=tex_weight.get) if tex_weight else "uniform"
    if warm / tw > 0.4:
        blended["_warm"] = 1.0
    if cool / tw > 0.4:
        blended["_cool"] = 1.0
    if green / tw > 0.4:
        blended["_green"] = 1.0
    return blended, lock_k


def apply_character_lock(spec_u8: np.ndarray, target_rgb: np.ndarray, lock_k: float) -> np.ndarray:
    """Final re-assertion of material identity AFTER the Viva pre/post pass.

    Viva's edge 'pop' + its NEAREST-upscaled dot/flake/interference grids leave a fine
    square *mesh* across the whole spec. Once the per-preset baselines are clean, that mesh
    reads as a spurious "boxes/ladder" artifact on EVERY preset — even ones that should be
    dead smooth (mirror chrome). So instead of preserving that high-frequency residual, we
    **smooth it out** and blend toward the clean profile target. The intentional family
    texture lives in ``target`` (added at full sharpness via the ``k`` term), so weave /
    flake / hex etc. stay crisp while the unwanted sub-cell mesh is removed.
    """
    if lock_k <= 1e-3 or target_rgb is None:
        return spec_u8
    s = spec_u8.astype(np.float32)
    tgt = np.asarray(target_rgb, dtype=np.float32)
    k = float(np.clip(lock_k, 0.0, 0.95))
    h, w = s.shape[:2]
    # sigma sized to erase the Viva grid (≈ a few px) at any render resolution
    sigma = max(1.1, (max(h, w) / 512.0) * 1.8)
    for c in range(3):
        cur_s = cv2.GaussianBlur(s[:, :, c], (0, 0), sigma)  # kill sub-cell VM mesh
        s[:, :, c] = tgt[:, :, c] * k + cur_s * (1.0 - k)
    s[:, :, 0] = np.clip(s[:, :, 0], 0, 255)
    s[:, :, 1] = np.clip(s[:, :, 1], 15, 255)
    s[:, :, 2] = np.clip(s[:, :, 2], 8, 255)
    if s.shape[2] > 3:
        s[:, :, 3] = 255
    return np.clip(np.round(s), 0, 255).astype(np.uint8)
