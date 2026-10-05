from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "reference_textures" / "cultural" / "rising_sun"
MANIFEST = ASSET_DIR / "manifest.json"
SIZE = 2048


def _normalize(a: np.ndarray, lo_pct: float = 1.0, hi_pct: float = 99.0) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(np.percentile(a, lo_pct))
    hi = float(np.percentile(a, hi_pct))
    if hi <= lo:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _soft(a: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(a.astype(np.float32), (0, 0), sigma)


def _spark(shape: tuple[int, int], seed: int, threshold: float, sigma: float = 0.45) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dots = (rng.random(shape, dtype=np.float32) > threshold).astype(np.float32)
    if sigma > 0:
        dots = _soft(dots, sigma)
    return _normalize(dots, 40.0, 99.98)


def _micro_mosaic(shape: tuple[int, int], seed: int, cell: int, threshold: float) -> np.ndarray:
    """Tiny clustered spec flecks: dense material events, not visible decals."""
    h, w = shape
    cell = max(2, int(cell))
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // cell), max(2, w // cell)), dtype=np.float32)
    fleck = (small > float(threshold)).astype(np.float32)
    shade = rng.random(small.shape, dtype=np.float32) * fleck
    fleck = cv2.resize(fleck * (0.50 + shade * 0.50), (w, h), interpolation=cv2.INTER_NEAREST)
    return _normalize(fleck, 35.0, 99.98)


def _xy(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _profile(finish_id: str, name: str, style: str = "") -> dict[str, float | str]:
    text = f"{finish_id} {name} {style}".lower()
    profile = {
        "kind": "lacquer",
        "metal": 0.72,
        "clear": 0.82,
        "rough": 0.62,
        "flake": 0.78,
        "line": 0.45,
        "glow": 0.52,
    }
    if any(k in text for k in ("kintsugi", "kinpaku", "gold", "temple", "lantern", "blaze", "mikan")):
        profile.update(kind="gold", metal=1.08, clear=0.92, rough=0.48, flake=1.02, line=0.62, glow=0.74)
    if any(k in text for k in ("sakura", "wisteria", "lotus", "peony", "iris", "camellia", "plum", "chrysanthemum", "hydrangea", "garden", "bloom")):
        profile.update(kind="floral", metal=0.62, clear=1.02, rough=0.54, flake=0.82, line=0.38, glow=0.56)
    if any(k in text for k in ("dragon", "oni", "tengu", "kitsune", "gashadokuro", "yurei", "jorogumo", "bakeneko", "hyakki", "damned", "nocturne")):
        profile.update(kind="myth", metal=0.88, clear=0.96, rough=0.45, flake=0.72, line=0.72, glow=0.78)
    if any(k in text for k in ("tsunami", "koi", "pond", "nure", "hakuryu", "fuji", "mist", "rain")):
        profile.update(kind="water", metal=0.58, clear=1.12, rough=0.38, flake=0.70, line=0.58, glow=0.64)
    if any(k in text for k in ("shibuya", "bosozoku", "wangan", "touge", "drift", "kaido", "dekotora", "time_attack", "pulse", "freight", "shock")):
        profile.update(kind="street", metal=0.92, clear=1.05, rough=0.42, flake=1.08, line=0.94, glow=0.88)
    if any(k in text for k in ("bamboo", "matcha", "ryokucha")):
        profile.update(kind="organic", metal=0.50, clear=0.82, rough=0.72, flake=0.48, line=0.52, glow=0.36)
    if any(k in text for k in ("sumi", "kuro", "kurogane", "eclipse")):
        profile.update(kind="ink", metal=0.72, clear=0.76, rough=0.58, flake=0.52, line=0.80, glow=0.42)
    return profile


def _sigmoid(a: np.ndarray, center: float, gain: float) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-(a.astype(np.float32) - center) * gain))).astype(np.float32)


def _ridge(axis: np.ndarray, scale: float, phase: float, sharp: float) -> np.ndarray:
    return np.clip(1.0 - np.abs(np.sin((axis * scale + phase) * np.pi)) * sharp, 0.0, 1.0).astype(np.float32)


def _detail_grade(channel: np.ndarray, mid: float, span: float, blend: float) -> np.ndarray:
    """Lift local detail back out of saturated M/R/CC channels."""
    detail = _normalize(channel, 0.8, 99.6)
    graded = mid + (detail - 0.5) * span
    return np.clip(channel * (1.0 - blend) + graded * blend, 0, 255).astype(np.float32)


def _style_bias(finish_id: str, name: str, style: str, index: int) -> dict[str, float]:
    text = f"{finish_id} {name} {style}".lower()
    bias = {
        "metal_base": 30.0,
        "rough_base": 96.0,
        "clear_base": 42.0,
        "metal_gain": 168.0,
        "rough_gain": 82.0,
        "clear_gain": 184.0,
        "gold_push": 18.0,
        "cool_push": 22.0,
        "micro": 1.0,
        "engrave": 1.0,
    }
    if any(k in text for k in ("gold", "kinpaku", "kintsugi", "temple", "lantern", "blaze", "mikan", "sun")):
        bias.update(metal_base=48.0, rough_base=78.0, clear_base=54.0, metal_gain=190.0, rough_gain=64.0, clear_gain=176.0, gold_push=46.0, micro=1.18)
    if any(k in text for k in ("ice", "mist", "rain", "tide", "tsunami", "pond", "fuji", "hakuryu", "hydrangea")):
        bias.update(metal_base=22.0, rough_base=70.0, clear_base=70.0, metal_gain=132.0, rough_gain=58.0, clear_gain=214.0, cool_push=54.0, micro=0.92)
    if any(k in text for k in ("dragon", "oni", "tengu", "kitsune", "yurei", "gashadokuro", "jorogumo", "bakeneko", "hyakki", "damned")):
        bias.update(metal_base=40.0, rough_base=84.0, clear_base=48.0, metal_gain=188.0, rough_gain=74.0, clear_gain=196.0, engrave=1.22)
    if any(k in text for k in ("street", "shibuya", "bosozoku", "wangan", "touge", "drift", "kaido", "dekotora", "time_attack", "shock")):
        bias.update(metal_base=58.0, rough_base=62.0, clear_base=62.0, metal_gain=196.0, rough_gain=52.0, clear_gain=208.0, micro=1.35)
    if any(k in text for k in ("bamboo", "matcha", "ryokucha")):
        bias.update(metal_base=18.0, rough_base=128.0, clear_base=38.0, metal_gain=108.0, rough_gain=104.0, clear_gain=126.0, micro=0.74)
    if any(k in text for k in ("sumi", "kuro", "kurogane", "eclipse", "nocturne")):
        bias.update(metal_base=34.0, rough_base=108.0, clear_base=40.0, metal_gain=176.0, rough_gain=92.0, clear_gain=164.0, engrave=1.32)
    bias["phase"] = ((index * 41) % 360) / 360.0
    return bias


def _semantic_relief(
    finish_id: str,
    name: str,
    style: str,
    index: int,
    shape: tuple[int, int],
    hue: np.ndarray,
    sat: np.ndarray,
    val: np.ndarray,
    luma: np.ndarray,
    edge: np.ndarray,
    broad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Paint-driven focal masks for spec storytelling.

    These are not generic extra glitter. They bias the spec toward the actual
    design intent: suns and lanterns get hot cores/rays, mythic creatures get
    traced edges and glowing focal marks, water gets glossy foam/ripples, and
    florals get petal-vein lacquer.
    """
    text = f"{finish_id} {name} {style}".lower()
    x, y = _xy(shape)
    cx = 0.5 + np.sin(index * 1.73) * 0.10
    cy = 0.5 + np.cos(index * 1.11) * 0.10
    dx = x - cx
    dy = y - cy
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.03), np.abs(hue - 0.98)) * 6.0, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.028) + np.exp(-((hue - 0.72) ** 2) / 0.035)) * sat, 0, 1)
    bright_hot = _sigmoid(val * 0.70 + sat * 0.30, 0.56, 10.0)
    contour = np.clip(edge * 0.62 + _soft(edge, 1.0) * 0.22 + broad * 0.20, 0, 1)

    if any(k in text for k in ("sun", "blaze", "flare", "lantern", "gold", "mikan", "temple", "inferno")):
        ray = _ridge(theta / np.pi + r * (3.4 + index % 5), 18.0 + index % 7, index * 0.037, 22.0)
        core = np.exp(-(r * (4.1 + (index % 4) * 0.45)) ** 2).astype(np.float32)
        focal = np.clip((warm * bright_hot) * 0.58 + ray * 0.32 + core * 0.44 + contour * warm * 0.22, 0, 1)
        trace = np.clip(contour * (0.40 + warm * 0.60) + ray * 0.30, 0, 1)
        recess = np.clip((1.0 - focal) * broad * 0.44 + (1.0 - val) * 0.24, 0, 1)
    elif any(k in text for k in ("dragon", "oni", "tengu", "kitsune", "yurei", "gashadokuro", "jorogumo", "bakeneko", "hyakki", "damned")):
        claw = _ridge(x * 0.8 - y * 1.3 + broad * 0.35, 78.0 + index % 19, index * 0.021, 34.0)
        ember = _spark(shape, 15100 + index * 79, 0.9945, 0.24)
        focal = np.clip(contour * 0.52 + claw * 0.34 + ember * 0.72 + warm * bright_hot * 0.26, 0, 1)
        trace = np.clip(edge * 0.78 + claw * 0.46 + ember * 0.46, 0, 1)
        recess = np.clip((1.0 - val) * 0.42 + broad * 0.34 + contour * 0.12, 0, 1)
    elif any(k in text for k in ("tsunami", "koi", "pond", "rain", "mist", "fuji", "tide", "hakuryu", "hydrangea")):
        ripple = _ridge(x * 1.2 + np.sin((y + broad * 0.18) * np.pi * 3.0) * 0.12, 66.0 + index % 17, index * 0.029, 26.0)
        foam = _spark(shape, 16100 + index * 83, 0.9932, 0.32)
        focal = np.clip(cool * 0.46 + ripple * 0.36 + foam * 0.54 + bright_hot * 0.16, 0, 1)
        trace = np.clip(contour * 0.46 + ripple * 0.54 + foam * 0.28, 0, 1)
        recess = np.clip((1.0 - cool) * broad * 0.34 + (1.0 - val) * 0.24, 0, 1)
    elif any(k in text for k in ("sakura", "wisteria", "lotus", "peony", "iris", "camellia", "plum", "chrysanthemum", "hydrangea", "bloom", "garden")):
        petal = _ridge(x * 0.9 + y * 0.7 + sat * 0.20, 54.0 + index % 23, index * 0.033, 24.0)
        dew = _spark(shape, 17100 + index * 89, 0.9950, 0.26)
        focal = np.clip(sat * bright_hot * 0.36 + petal * 0.34 + dew * 0.66 + contour * 0.30, 0, 1)
        trace = np.clip(contour * 0.58 + petal * 0.34 + dew * 0.30, 0, 1)
        recess = np.clip((1.0 - sat) * broad * 0.26 + (1.0 - val) * 0.22, 0, 1)
    elif any(k in text for k in ("shibuya", "bosozoku", "wangan", "touge", "drift", "kaido", "dekotora", "time_attack", "shock")):
        neon = _ridge(x * 1.6 - y * 0.55 + edge * 0.18, 96.0 + index % 31, index * 0.041, 38.0)
        pixel = _spark(shape, 18100 + index * 97, 0.9910, 0.18)
        focal = np.clip(neon * 0.58 + pixel * 0.64 + sat * bright_hot * 0.32, 0, 1)
        trace = np.clip(contour * 0.42 + neon * 0.60 + pixel * 0.28, 0, 1)
        recess = np.clip((1.0 - val) * 0.30 + broad * 0.30, 0, 1)
    else:
        sparkle = _spark(shape, 19100 + index * 101, 0.9940, 0.28)
        focal = np.clip(contour * 0.38 + bright_hot * sat * 0.34 + sparkle * 0.48, 0, 1)
        trace = np.clip(contour * 0.62 + sparkle * 0.26, 0, 1)
        recess = np.clip((1.0 - val) * 0.34 + broad * 0.34, 0, 1)

    return focal.astype(np.float32), trace.astype(np.float32), recess.astype(np.float32)


def _hidden_rising_motif(
    finish_id: str,
    name: str,
    style: str,
    index: int,
    shape: tuple[int, int],
    hue: np.ndarray,
    sat: np.ndarray,
    val: np.ndarray,
    edge: np.ndarray,
    broad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Spec-only Japanese motif reveals buried in M/R/CC channel response."""
    text = f"{finish_id} {name} {style}".lower()
    x, y = _xy(shape)
    cx = 0.5 + np.sin(index * 1.19) * 0.115
    cy = 0.5 + np.cos(index * 1.47) * 0.105
    dx = x - cx
    dy = y - cy
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    phase = index * 0.041
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.035), np.abs(hue - 0.985)) * 6.0, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.030) + np.exp(-((hue - 0.72) ** 2) / 0.036)) * sat, 0, 1)

    if any(k in text for k in ("sun", "flare", "blaze", "lantern", "temple", "torii", "mikan", "kinpaku")):
        ray = _ridge(theta / np.pi + radius * (3.2 + index % 5), 32.0 + index % 13, phase, 36.0)
        torii = np.maximum(
            _ridge(y + broad * 0.075, 70.0 + index % 17, phase * 0.9, 48.0),
            _ridge(np.floor(x * 42.0) / 42.0 + broad * 0.11, 54.0 + index % 11, phase * 1.4, 42.0),
        )
        core = np.exp(-(radius * (4.6 + index % 4)) ** 2).astype(np.float32)
        motif = np.clip(ray * 0.54 + torii * warm * 0.34 + core * 0.40 + edge * warm * 0.25, 0, 1)
        polish = np.clip(ray * 0.40 + core * 0.34 + edge * warm * 0.36, 0, 1)
        satin = np.clip((1.0 - warm) * broad * 0.40 + torii * 0.24, 0, 1)
    elif any(k in text for k in ("dragon", "hakuryu", "oni", "tengu", "kitsune", "yurei", "gashadokuro", "jorogumo", "bakeneko", "hyakki", "damned")):
        eye_l = np.exp(-(((x - (cx - 0.092)) / 0.026) ** 2 + ((y - (cy - 0.025)) / 0.017) ** 2)).astype(np.float32)
        eye_r = np.exp(-(((x - (cx + 0.092)) / 0.026) ** 2 + ((y - (cy - 0.025)) / 0.017) ** 2)).astype(np.float32)
        scale = _ridge(x * 1.10 - y * 0.84 + np.sin(y * np.pi * 6.0 + phase) * 0.034, 88.0 + index % 29, phase * 1.3, 42.0)
        claw = _ridge(x * 0.64 + y * 1.42 + broad * 0.18, 102.0 + index % 31, phase * 1.8, 46.0)
        ember = _micro_mosaic(shape, 30100 + index * 113, 4 + index % 3, 0.981)
        motif = np.clip((eye_l + eye_r) * 0.58 + scale * 0.36 + claw * 0.28 + ember * 0.30 + edge * 0.30, 0, 1)
        polish = np.clip((eye_l + eye_r) * 0.42 + scale * 0.28 + ember * 0.20, 0, 1)
        satin = np.clip(claw * 0.34 + broad * 0.28 + (1.0 - val) * 0.32, 0, 1)
    elif any(k in text for k in ("tsunami", "koi", "pond", "rain", "mist", "fuji", "tide", "nure", "hydrangea")):
        tide = _ridge(radius + np.sin(theta * 7.0 + phase) * 0.016, 34.0 + index % 11, phase, 36.0)
        current = _ridge(x * 1.52 + np.sin((y + broad * 0.16) * np.pi * 7.0 + phase) * 0.074, 94.0 + index % 23, phase * 1.6, 40.0)
        foam = _micro_mosaic(shape, 31100 + index * 127, 3 + index % 3, 0.988)
        motif = np.clip(tide * 0.38 + current * 0.50 + foam * 0.34 + cool * edge * 0.30, 0, 1)
        polish = np.clip(current * 0.42 + cool * 0.42 + foam * 0.22, 0, 1)
        satin = np.clip((1.0 - cool) * broad * 0.34 + tide * 0.22, 0, 1)
    elif any(k in text for k in ("sakura", "wisteria", "lotus", "peony", "iris", "camellia", "plum", "chrysanthemum", "bloom", "garden", "hanami")):
        petal = _ridge(theta / np.pi + radius * 1.4, 22.0 + index % 7, phase, 34.0) * np.exp(-(radius * 1.95) ** 2)
        vein = _ridge(x * 0.76 + y * 1.22 + sat * 0.16, 84.0 + index % 29, phase * 1.2, 38.0)
        pollen = _micro_mosaic(shape, 32100 + index * 131, 3 + index % 4, 0.979)
        motif = np.clip(petal * 0.50 + vein * 0.34 + pollen * 0.34 + edge * sat * 0.28, 0, 1)
        polish = np.clip(petal * 0.32 + pollen * 0.26 + edge * sat * 0.24, 0, 1)
        satin = np.clip(vein * 0.26 + broad * 0.30 + (1.0 - sat) * 0.20, 0, 1)
    elif any(k in text for k in ("shibuya", "bosozoku", "wangan", "touge", "drift", "kaido", "dekotora", "time_attack", "pulse", "shock")):
        pulse = _ridge(x * 1.70 - y * 0.52 + edge * 0.16, 138.0 + index % 31, phase * 1.7, 50.0)
        scan = _ridge(y + np.sin(x * np.pi * 5.0 + phase) * 0.016, 112.0 + index % 29, phase, 44.0)
        kanji_ghost = _ridge(np.floor(x * 34.0) / 34.0 - np.floor(y * 28.0) / 36.0 + broad * 0.18, 76.0 + index % 19, phase * 1.1, 44.0)
        motif = np.clip(pulse * 0.52 + scan * 0.32 + kanji_ghost * 0.28 + sat * edge * 0.26, 0, 1)
        polish = np.clip(pulse * 0.44 + kanji_ghost * 0.22, 0, 1)
        satin = np.clip(scan * 0.28 + broad * 0.24, 0, 1)
    elif any(k in text for k in ("bamboo", "matcha", "ryokucha")):
        joint = _ridge(y + broad * 0.08, 52.0 + index % 13, phase, 34.0)
        fiber = _ridge(x * 0.52 + y * 1.42 + edge * 0.10, 116.0 + index % 31, phase * 1.6, 42.0)
        dew = _micro_mosaic(shape, 33100 + index * 137, 5 + index % 4, 0.985)
        motif = np.clip(joint * 0.36 + fiber * 0.42 + dew * 0.26 + edge * 0.26, 0, 1)
        polish = np.clip(dew * 0.26 + fiber * 0.20, 0, 1)
        satin = np.clip(joint * 0.36 + fiber * 0.30 + broad * 0.34, 0, 1)
    elif any(k in text for k in ("sumi", "kuro", "kurogane", "eclipse", "nocturne", "kintsugi")):
        crack = _ridge(x * 1.18 + y * 0.77 + np.sin(y * np.pi * 9.0 + phase) * 0.038 + broad * 0.14, 108.0 + index % 37, phase, 48.0)
        brush = _ridge(x * -0.36 + y * 1.64 + edge * 0.12, 88.0 + index % 23, phase * 1.5, 38.0)
        dust = _micro_mosaic(shape, 34100 + index * 139, 4 + index % 4, 0.986)
        motif = np.clip(crack * 0.48 + brush * 0.34 + dust * 0.24 + edge * 0.28, 0, 1)
        polish = np.clip(crack * 0.34 + dust * 0.20, 0, 1)
        satin = np.clip(brush * 0.34 + broad * 0.34 + (1.0 - val) * 0.26, 0, 1)
    else:
        shard = _micro_mosaic(shape, 35100 + index * 149, 4 + index % 3, 0.982)
        ribbon = _ridge(x * 0.86 + y * 1.14 + broad * 0.16, 96.0 + index % 23, phase, 40.0)
        motif = np.clip(shard * 0.44 + ribbon * 0.34 + edge * 0.28, 0, 1)
        polish = np.clip(shard * 0.28 + ribbon * 0.20, 0, 1)
        satin = np.clip(broad * 0.34 + ribbon * 0.22, 0, 1)

    return motif.astype(np.float32), polish.astype(np.float32), satin.astype(np.float32)


def _paint_path(item: dict) -> Path:
    for key in ("texture", "paint"):
        value = item.get(key)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            if path.parts and path.parts[0] == "assets":
                path = ROOT / path
            else:
                path = ASSET_DIR / path
        if path.exists():
            return path
    return ASSET_DIR / f"{item['id']}.png"


def _spec_path(item: dict) -> Path:
    value = item.get("spec") or f"{item['id']}_spec.png"
    path = Path(value)
    if not path.is_absolute():
        if path.parts and path.parts[0] == "assets":
            path = ROOT / path
        else:
            path = ASSET_DIR / path
    return path


def _load_paint(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    return np.asarray(img, dtype=np.float32) / 255.0


def _rising_sun_spec(rgb: np.ndarray, finish_id: str, name: str, index: int, style: str = "") -> Image.Image:
    shape = rgb.shape[:2]
    bgr = (rgb[:, :, ::-1] * 255).astype(np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue = hsv[:, :, 0] / 179.0
    sat = hsv[:, :, 1] / 255.0
    val = hsv[:, :, 2] / 255.0
    luma = np.clip(rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), 0.0, 1.0)

    blur1 = _soft(luma, 1.15)
    blur4 = _soft(luma, 4.25)
    blur12 = _soft(luma, 12.0)
    high = _normalize(np.abs(luma - blur1), 1, 99.7)
    mid = _normalize(np.abs(blur1 - blur4), 1, 99.5)
    broad = _normalize(np.abs(blur4 - blur12), 1, 99.2)
    lap = _normalize(np.abs(cv2.Laplacian(luma, cv2.CV_32F, ksize=3)), 1, 99.7)
    sx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    edge = _normalize(np.sqrt(sx * sx + sy * sy), 1, 99.7)
    direction = _normalize(np.abs(sx) * 0.58 + np.abs(sy) * 0.42, 1, 99.5)

    # Paint-aware masks: bright ink/gold, saturated color, shadow lacquer, and cool/warm zones.
    bright = _normalize(val * 0.72 + sat * 0.28, 4, 97)
    color = _normalize(sat * 0.80 + high * 0.30, 2, 98.8)
    shadow = np.clip((0.54 - luma) * 2.2, 0.0, 1.0)
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.03), np.abs(hue - 0.98)) * 6.0, 0.0, 1.0)
    gold = np.clip((warm * 0.62 + sat * 0.20 + val * 0.28 - 0.34) * 2.2, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.028) + np.exp(-((hue - 0.72) ** 2) / 0.035)) * sat, 0, 1)

    profile = _profile(finish_id, name, style)
    bias = _style_bias(finish_id, name, style, index)
    x, y = _xy(shape)
    line_angle = ((index * 37) % 180) * np.pi / 180.0
    axial = x * np.cos(line_angle) + y * np.sin(line_angle)
    lacquer_lines = np.clip(1.0 - np.abs(np.sin((axial * (44 + index % 17) + high * 0.35) * np.pi)) * 18.0, 0, 1)
    wave_ridges = _normalize(np.sin((x * (7 + index % 5) + y * (5 + index % 7) + broad * 1.7) * np.pi) * 0.5 + 0.5, 4, 96)
    micro = _spark(shape, 7700 + index * 31, 0.9810 - min(float(profile["flake"]) * 0.004, 0.008), 0.34)
    pin = _spark(shape, 9100 + index * 47, 0.9934, 0.24)
    nano = _spark(shape, 13100 + index * 61, 0.9890, 0.18)

    art_relief = np.clip(edge * 0.48 + lap * 0.38 + high * 0.38 + mid * 0.24 + broad * 0.16, 0, 1)
    raised_ink = np.clip(art_relief * (0.42 + color * 0.54) + direction * 0.18, 0, 1)
    glow = np.clip((bright * 0.42 + gold * 0.28 + cool * 0.18 + wave_ridges * 0.18) * float(profile["glow"]), 0, 1)
    line_detail = np.clip(lacquer_lines * (0.38 + edge * 0.62) * float(profile["line"]), 0, 1)
    focal_hot, design_trace, recess_shadow = _semantic_relief(
        finish_id, name, style, index, shape, hue, sat, val, luma, edge, broad
    )
    hidden, hidden_polish, hidden_satin = _hidden_rising_motif(
        finish_id, name, style, index, shape, hue, sat, val, edge, broad
    )
    candy_cell = _micro_mosaic(
        shape,
        21100 + index * 163,
        3 + index % 3,
        0.9735 - min(float(profile["flake"]) * 0.003, 0.008),
    )
    lacquer_dot = _micro_mosaic(shape, 22100 + index * 167, 5 + index % 4, 0.9815)
    satin_pore = _micro_mosaic(shape, 23100 + index * 173, 7 + index % 5, 0.9875)

    # Independent channel carriers. This is the key distinction from the flat
    # green/yellow pass: each M/R/CC channel now follows a different physical
    # idea while still being driven by the same paint art.
    hue_spin = np.mod(hue + bias["phase"], 1.0)
    pearl_band = np.clip(
        np.sin((hue_spin * (7.0 + index % 5) + broad * 0.85 + x * 1.4 - y * 0.7) * np.pi) * 0.5 + 0.5,
        0.0,
        1.0,
    )
    diag_a = _ridge(x * 1.35 + y * 0.68 + broad * 0.42, 72.0 + index % 13, bias["phase"], 30.0)
    diag_b = _ridge(x * -0.72 + y * 1.55 + mid * 0.38, 94.0 + index % 17, bias["phase"] * 1.7, 34.0)
    silk = np.clip(diag_a * 0.52 + diag_b * 0.36 + wave_ridges * 0.24, 0, 1)
    hammered = _normalize(
        _soft(_spark(shape, 11200 + index * 53, 0.975, 0.52), 0.35) * 0.45
        + _spark(shape, 12100 + index * 71, 0.992, 0.18) * 0.80
        + high * 0.35,
        2,
        99.7,
    )
    carved = np.clip(edge * 0.64 + lap * 0.42 + line_detail * 0.36 + _soft(edge, 0.7) * 0.20, 0, 1)
    glass_pool = np.clip(bright * 0.28 + cool * 0.42 + pearl_band * 0.30 + raised_ink * 0.34, 0, 1)
    matte_recess = np.clip(shadow * 0.42 + broad * 0.38 + (1.0 - sat) * 0.24 - carved * 0.18, 0, 1)
    metallic_inlay = np.clip(
        gold * 0.44
        + color * 0.22
        + carved * 0.35
        + hammered * 0.46 * float(bias["micro"])
        + micro * 0.22
        + nano * 0.28
        + pin * 0.58
        + focal_hot * 0.34
        + design_trace * 0.26
        + silk * 0.22,
        0,
        1,
    )
    clear_lacquer = np.clip(
        glass_pool * 0.48
        + raised_ink * 0.42
        + silk * 0.26
        + pin * 0.48
        + nano * 0.22
        + focal_hot * 0.42
        + design_trace * 0.30
        + cool * 0.18
        + gold * 0.10,
        0,
        1,
    )
    rough_engrave = np.clip(
        matte_recess * 0.52
        + (1.0 - glass_pool) * 0.18
        + broad * 0.18
        + _soft(carved, 1.1) * 0.20 * float(bias["engrave"])
        + recess_shadow * 0.36
        - silk * 0.22
        - pin * 0.22
        - focal_hot * 0.18,
        0,
        1,
    )
    metallic_inlay = np.clip(
        metallic_inlay
        + hidden * 0.34
        + hidden_polish * 0.26
        + candy_cell * 0.34
        + lacquer_dot * 0.18,
        0,
        1,
    )
    clear_lacquer = np.clip(
        clear_lacquer
        + hidden * 0.42
        + hidden_polish * 0.50
        + candy_cell * 0.22
        + lacquer_dot * 0.30,
        0,
        1,
    )
    rough_engrave = np.clip(
        rough_engrave
        + hidden_satin * 0.42
        + satin_pore * 0.28
        - hidden_polish * 0.18,
        0,
        1,
    )

    kind = str(profile["kind"])
    if kind == "floral":
        metallic_energy = np.clip(metallic_inlay * 0.62 + pearl_band * color * 0.24 + hammered * 0.18, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.74 + carved * 0.18 + pin * 0.28, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.72 + shadow * 0.20 + broad * 0.14, 0, 1)
    elif kind == "myth":
        metallic_energy = np.clip(metallic_inlay * 0.72 + carved * 0.30 + shadow * 0.10 + silk * 0.18, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.58 + glow * 0.32 + line_detail * 0.32 + pin * 0.30, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.78 + shadow * 0.25 - carved * 0.12, 0, 1)
    elif kind == "water":
        metallic_energy = np.clip(metallic_inlay * 0.38 + cool * 0.44 + hammered * 0.18 + pin * 0.20, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.82 + wave_ridges * 0.34 + silk * 0.24, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.52 + (1 - cool) * 0.16 + broad * 0.20, 0, 1)
    elif kind == "street":
        metallic_energy = np.clip(metallic_inlay * 0.74 + line_detail * 0.40 + hammered * 0.24 + pin * 0.30, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.66 + silk * 0.36 + glow * 0.22 + pin * 0.28, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.58 + shadow * 0.18 - line_detail * 0.16, 0, 1)
    elif kind == "gold":
        metallic_energy = np.clip(metallic_inlay * 0.82 + gold * 0.28 + hammered * 0.18 + pin * 0.28, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.56 + gold * 0.24 + line_detail * 0.22 + pin * 0.22, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.46 + shadow * 0.18 + (1 - gold) * 0.10, 0, 1)
    elif kind == "organic":
        metallic_energy = np.clip(metallic_inlay * 0.36 + carved * 0.14 + hammered * 0.10, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.44 + broad * 0.22 + silk * 0.16, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.84 + shadow * 0.18 + (1 - val) * 0.16, 0, 1)
    else:
        metallic_energy = np.clip(metallic_inlay * 0.68 + color * 0.16 + hammered * 0.16, 0, 1)
        clear_energy = np.clip(clear_lacquer * 0.68 + bright * 0.12 + line_detail * 0.24 + pin * 0.20, 0, 1)
        rough_energy = np.clip(rough_engrave * 0.68 + shadow * 0.18 + broad * 0.16, 0, 1)

    metal_gain = float(profile["metal"])
    clear_gain = float(profile["clear"])
    rough_gain = float(profile["rough"])
    metallic = np.clip(
        float(bias["metal_base"])
        + metallic_energy * float(bias["metal_gain"]) * metal_gain
        + art_relief * 34
        + warm * float(bias["gold_push"])
        + cool * float(bias["cool_push"]) * 0.36
        + micro * 54 * float(bias["micro"])
        + nano * 44
        + design_trace * 42
        + focal_hot * 62
        + pin * 116
        + hidden * 48
        + hidden_polish * 32
        + candy_cell * 58
        + lacquer_dot * 28,
        0,
        255,
    )
    roughness = np.clip(
        float(bias["rough_base"])
        - clear_energy * (62 * clear_gain)
        - metallic_energy * 18
        - line_detail * 22
        - focal_hot * 34
        + rough_energy * float(bias["rough_gain"]) * rough_gain
        + broad * 34
        + shadow * 24
        + recess_shadow * 44
        + nano * 16
        + hidden_satin * 38
        + satin_pore * 24
        - hidden_polish * 26,
        18,
        228,
    )
    clearcoat = np.clip(
        float(bias["clear_base"])
        + clear_energy * float(bias["clear_gain"]) * clear_gain
        + glow * 66
        + cool * float(bias["cool_push"])
        + gold * float(bias["gold_push"]) * 0.55
        + design_trace * 54
        + focal_hot * 88
        + nano * 42
        + pin * 96
        + hidden * 50
        + hidden_polish * 72
        + lacquer_dot * 46,
        16,
        255,
    )

    # Faux emboss phase shifts: tiny channel offsets create dimensional M/R/CC
    # disagreement instead of a flat two-color spec plate.
    metallic = np.clip(
        metallic
        + np.roll(carved, 1 + index % 3, axis=1) * 30
        + pearl_band * 20
        + np.roll(focal_hot, 2, axis=0) * 38
        + np.roll(hidden, 1 + index % 2, axis=1) * 54
        + candy_cell * 62
        + lacquer_dot * 26,
        0,
        255,
    )
    roughness = np.clip(
        roughness
        - np.roll(line_detail, 1 + index % 4, axis=0) * 38
        - np.roll(hidden_polish, 1 + index % 3, axis=0) * 34
        + np.roll(matte_recess, 2, axis=1) * 20
        + np.roll(recess_shadow, 3, axis=1) * 34
        + np.roll(hidden_satin, 2 + index % 2, axis=1) * 54
        + satin_pore * 28,
        18,
        235,
    )
    clearcoat = np.clip(
        clearcoat
        + np.roll(edge, -(1 + index % 5), axis=1) * 46
        + silk * 24
        + np.roll(design_trace, -2, axis=0) * 58
        + np.roll(hidden_polish, -(1 + index % 4), axis=1) * 74
        + lacquer_dot * 48,
        16,
        255,
    )

    # Per-finish channel rotation, kept subtle enough to remain valid M/R/CC,
    # but strong enough that all 52 finishes do not preview as the same green
    # and yellow material.
    rot = index % 6
    if rot == 1:
        metallic = np.clip(metallic + cool * 30, 0, 255)
        clearcoat = np.clip(clearcoat + gold * 18 + focal_hot * 32, 16, 255)
    elif rot == 2:
        roughness = np.clip(roughness + hammered * 36 + recess_shadow * 22 - clear_energy * 22, 18, 235)
        clearcoat = np.clip(clearcoat + pin * 38 + design_trace * 24, 16, 255)
    elif rot == 3:
        metallic = np.clip(metallic + silk * 40 + nano * 32, 0, 255)
        roughness = np.clip(roughness - silk * 32 + recess_shadow * 18, 18, 235)
    elif rot == 4:
        clearcoat = np.clip(clearcoat + pearl_band * 46 + focal_hot * 28, 16, 255)
        metallic = np.clip(metallic + pin * 34 + design_trace * 20, 0, 255)
    elif rot == 5:
        roughness = np.clip(roughness + matte_recess * 34 + recess_shadow * 30, 18, 235)
        clearcoat = np.clip(clearcoat + carved * 30 + nano * 24, 16, 255)

    metallic = _detail_grade(metallic, 130.0 + float(bias["metal_base"]) * 0.10, 238.0, 0.34)
    roughness = _detail_grade(roughness, 104.0 + float(bias["rough_base"]) * 0.06, 206.0, 0.30)
    clearcoat = _detail_grade(clearcoat, 150.0 + float(bias["clear_base"]) * 0.08, 242.0, 0.36)

    spec = np.zeros((*shape, 4), dtype=np.uint8)
    spec[:, :, 0] = metallic.astype(np.uint8)
    spec[:, :, 1] = roughness.astype(np.uint8)
    spec[:, :, 2] = clearcoat.astype(np.uint8)
    spec[:, :, 3] = 255
    return Image.fromarray(spec, "RGBA")


def main() -> None:
    started = time.perf_counter()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    finishes = data.get("finishes", [])
    rebuilt = 0
    for index, item in enumerate(finishes, start=1):
        finish_id = item["id"]
        name = item.get("name", finish_id)
        paint_path = _paint_path(item)
        spec_path = _spec_path(item)
        rgb = _load_paint(paint_path)
        spec = _rising_sun_spec(rgb, finish_id, name, index, item.get("style", ""))
        spec.save(spec_path, compress_level=1, optimize=False)
        rebuilt += 1
        print(f"{index:02d}/{len(finishes)} rebuilt {finish_id}")
    print(f"rising_sun_specs={rebuilt} elapsed={time.perf_counter() - started:.2f}s")


if __name__ == "__main__":
    main()
