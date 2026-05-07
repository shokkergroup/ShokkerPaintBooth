from __future__ import annotations

import json
import re
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "assets" / "reference_textures" / "cultural" / "Viva Mexico"
OUT_DIR = ROOT / "assets" / "reference_textures" / "cultural" / "viva_mexico"
SIZE = 2048
SCRIPT_MTIME = Path(__file__).stat().st_mtime


NAMES = [
    "Aztec Sunfire",
    "Talavera Azul",
    "Quetzal Sunset",
    "Sacred Heart Eclipse",
    "Guadalupe Lowrider",
    "Rosa Corazon",
    "Mariachi Verde",
    "Calavera Violeta",
    "Serape Sunburst",
    "Riviera Lowrider",
    "Luchador Plata",
    "Luchador Rayo",
    "Cactus Sunset",
    "Sierra Verde",
    "Cenote Lace",
    "Agave Pearl",
    "Baja Horizon",
    "Pacific Coast Dawn",
    "Copper Canyon",
    "Sierra Niebla",
    "Oaxaca Moonwater",
    "Xolo Candy Desert",
    "Huichol Beadwork",
    "Sonora Blue Calavera",
    "Bajio Gold Calaveras",
    "Lucha Rosa",
    "Desert Marigold",
    "Zapata Jade",
    "Cinco Spark",
    "Mezcal Smoke",
    "Riviera Corazon",
    "Noche Buena",
    "Rosario Gold",
    "Pyramid Shadow",
    "Fiesta Chrome",
    "Maguey Pearl",
    "Cantina Neon",
    "Azulejo Storm",
    "Calavera Royal",
    "Talavera Muertos",
    "Tulum Candelaria",
    "Eclipse Ofrenda",
    "Charro Nocturne",
    "Cempasuchil Noir",
    "Sierra Madre",
    "Mole Negro",
    "Veracruz Carnival",
    "Jalisco Flash",
    "Mosaic Jaguar",
    "Milagro Silver",
    "Sacred Cenote",
    "Playa Dorada",
    "Adobe Sunset",
    "Zapotec Thunder",
    "Nopal Bloom",
    "Mayan Jade",
    "Neon Cantina",
    "Baja Cartografia",
]


STYLES = [
    "molten_aztec",
    "obsidian_gold",
    "quetzal_chrome",
    "jaguar_dark",
    "talavera_blue",
    "marigold",
    "neon_calavera",
    "chrome_mask",
    "woven_prism",
    "agave_green",
    "monarch",
    "floral_paint",
    "desert",
    "gold_brass",
    "paper_cut",
    "confetti",
    "muertos",
    "sunrise",
    "copper",
    "temple_gold",
    "ember",
    "black_dog",
    "beadwork",
    "heatwave",
    "aqua",
    "jade",
    "marigold",
    "bronze",
    "spark",
    "smoke",
    "aqua",
    "holiday_red",
    "rosary_gold",
    "shadow",
    "chrome",
    "pearl",
    "neon",
    "tile_storm",
    "royal",
    "volcanic",
    "reef",
    "ribbon",
    "leather",
    "cempasuchil",
    "mountain",
    "black_sauce",
    "carnival",
    "flash",
    "jaguar_mosaic",
    "silver",
    "cenote",
    "copper",
    "adobe",
    "thunder",
    "nopal",
    "jade",
    "chili",
    "cobalt",
]


def slug(name: str) -> str:
    text = name.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return "vm_" + text.strip("_")


def crop_art_area(img: Image.Image) -> tuple[Image.Image, int]:
    w, h = img.size
    # The generated poster cards carry numbers and wording in the bottom band.
    # Keep the authored art and discard the card/footer area before making SPB plates.
    crop_y = int(h * 0.795)
    return img.crop((0, 0, w, crop_y)), crop_y


def make_paint_plate(src: Path) -> tuple[Image.Image, int]:
    img = Image.open(src).convert("RGB")
    cropped, crop_y = crop_art_area(img)
    plate = cropped.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    plate = ImageEnhance.Color(plate).enhance(1.08)
    plate = ImageEnhance.Contrast(plate).enhance(1.08)
    plate = ImageEnhance.Sharpness(plate).enhance(1.18)
    plate = plate.filter(ImageFilter.UnsharpMask(radius=1.0, percent=75, threshold=2))
    return plate, crop_y


def normalize01(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo = float(np.percentile(a, 1.0))
    hi = float(np.percentile(a, 99.0))
    if hi <= lo:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def spark(shape: tuple[int, int], seed: int, threshold: float, sigma: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dots = (rng.random(shape, dtype=np.float32) > threshold).astype(np.float32)
    if sigma > 0:
        dots = cv2.GaussianBlur(dots, (0, 0), sigma)
    return normalize01(dots)


def micro_mosaic(shape: tuple[int, int], seed: int, cell: int, threshold: float) -> np.ndarray:
    """Tiny clustered flake pixels inspired by owner reference specs."""
    h, w = shape
    cell = max(2, int(cell))
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // cell), max(2, w // cell)), dtype=np.float32)
    fleck = (small > float(threshold)).astype(np.float32)
    shade = rng.random(small.shape, dtype=np.float32) * fleck
    fleck = cv2.resize(fleck * (0.55 + shade * 0.45), (w, h), interpolation=cv2.INTER_NEAREST)
    return normalize01(fleck)


def xy(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def ridge(axis: np.ndarray, scale: float, phase: float, sharp: float) -> np.ndarray:
    return np.clip(1.0 - np.abs(np.sin((axis * scale + phase) * np.pi)) * sharp, 0.0, 1.0).astype(np.float32)


def sigmoid(a: np.ndarray, center: float, gain: float) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-(a.astype(np.float32) - center) * gain))).astype(np.float32)


def hidden_cultural_motif(
    name: str,
    style: str,
    index: int,
    hue: np.ndarray,
    sat: np.ndarray,
    val: np.ndarray,
    edge: np.ndarray,
    broad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Spec-only motif reveals: subtle M/R/CC events, not painted decals."""
    text = f"{name} {style}".lower()
    shape = val.shape
    x, y = xy(shape)
    cx = 0.5 + np.sin(index * 1.13) * 0.12
    cy = 0.5 + np.cos(index * 1.61) * 0.10
    dx = x - cx
    dy = y - cy
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    phase = index * 0.037
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.04), np.abs(hue - 0.98)) * 5.8, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.035) + np.exp(-((hue - 0.70) ** 2) / 0.032)) * sat, 0, 1)

    if any(k in text for k in ("sun", "sunfire", "sunburst", "marigold", "dawn", "gold", "cempasuchil", "flash")):
        ray = ridge(theta / np.pi + radius * (3.4 + index % 4), 30.0 + index % 11, phase, 34.0)
        temple_step = ridge(np.floor(x * 44.0) / 44.0 + np.floor(y * 30.0) / 38.0 + broad * 0.16, 52.0, phase * 1.7, 38.0)
        core = np.exp(-(radius * (4.4 + index % 3)) ** 2).astype(np.float32)
        motif = np.clip(ray * 0.54 + temple_step * warm * 0.40 + core * 0.42 + edge * warm * 0.24, 0, 1)
        polish = np.clip(ray * 0.38 + warm * edge * 0.42, 0, 1)
        satin = np.clip((1.0 - warm) * broad * 0.46 + temple_step * 0.22, 0, 1)
    elif any(k in text for k in ("calavera", "muertos", "eclipse", "nocturne", "shadow", "xolo", "mole")):
        eye_l = np.exp(-(((x - (cx - 0.105)) / 0.030) ** 2 + ((y - (cy - 0.025)) / 0.020) ** 2)).astype(np.float32)
        eye_r = np.exp(-(((x - (cx + 0.105)) / 0.030) ** 2 + ((y - (cy - 0.025)) / 0.020) ** 2)).astype(np.float32)
        flower = ridge(radius + np.sin(theta * 8.0 + phase) * 0.012, 24.0 + index % 9, phase, 36.0)
        tooth = ridge(x + y * 0.08, 92.0 + index % 17, phase * 1.9, 44.0) * np.exp(-((y - (cy + 0.115)) / 0.035) ** 2)
        motif = np.clip((eye_l + eye_r) * 0.64 + flower * 0.36 + tooth * 0.40 + edge * 0.28, 0, 1)
        polish = np.clip((eye_l + eye_r) * 0.50 + flower * 0.24, 0, 1)
        satin = np.clip((1.0 - val) * 0.40 + tooth * 0.36 + broad * 0.22, 0, 1)
    elif any(k in text for k in ("talavera", "azulejo", "tile", "lace", "mosaic")):
        rosette = ridge(radius + np.sin(theta * 10.0 + phase) * 0.014, 32.0 + index % 7, phase, 40.0)
        grout = np.maximum(ridge(x, 58.0 + index % 11, phase * 0.7, 46.0), ridge(y, 54.0 + index % 13, phase * 1.1, 46.0))
        petal = ridge(theta / np.pi, 18.0 + index % 5, phase, 32.0) * np.exp(-(radius * 2.2) ** 2)
        motif = np.clip(rosette * 0.44 + petal * 0.50 + grout * cool * 0.40 + edge * 0.30, 0, 1)
        polish = np.clip(rosette * 0.36 + cool * edge * 0.42, 0, 1)
        satin = np.clip(grout * 0.50 + broad * 0.28, 0, 1)
    elif any(k in text for k in ("quetzal", "jaguar", "mayan", "zapotec", "aztec", "pyramid", "thunder")):
        stepped = ridge(np.floor(x * 36.0) / 36.0 - np.floor(y * 28.0) / 34.0 + broad * 0.20, 68.0 + index % 17, phase, 42.0)
        serpent = ridge(x * 1.28 + y * 0.72 + np.sin(y * np.pi * 6.0 + phase) * 0.045, 74.0 + index % 23, phase * 1.3, 38.0)
        spots = micro_mosaic(shape, 30100 + index * 113, 5, 0.982)
        motif = np.clip(stepped * 0.46 + serpent * 0.42 + spots * 0.30 + edge * 0.36, 0, 1)
        polish = np.clip(serpent * 0.38 + warm * edge * 0.32 + spots * 0.18, 0, 1)
        satin = np.clip(stepped * 0.32 + (1.0 - val) * 0.30 + broad * 0.26, 0, 1)
    elif any(k in text for k in ("cenote", "playa", "riviera", "pacific", "coast", "aqua", "blue", "water")):
        tide = ridge(radius + np.sin(theta * 6.0 + phase) * 0.018, 32.0 + index % 11, phase, 34.0)
        current = ridge(x * 1.55 + np.sin(y * np.pi * 7.0 + broad * 1.2) * 0.08, 86.0 + index % 19, phase * 1.5, 36.0)
        foam = micro_mosaic(shape, 31100 + index * 127, 4, 0.988)
        motif = np.clip(tide * 0.42 + current * 0.48 + foam * 0.34 + cool * edge * 0.28, 0, 1)
        polish = np.clip(current * 0.42 + cool * 0.40 + foam * 0.24, 0, 1)
        satin = np.clip((1.0 - cool) * broad * 0.34 + tide * 0.18, 0, 1)
    elif any(k in text for k in ("lowrider", "luchador", "cantina", "neon", "fiesta", "carnival", "spark")):
        pulse = ridge(x * 1.65 - y * 0.55 + edge * 0.18, 132.0 + index % 29, phase * 1.7, 48.0)
        scan = ridge(y + np.sin(x * np.pi * 5.0 + phase) * 0.018, 104.0 + index % 31, phase, 44.0)
        star = ridge(theta / np.pi + radius * 2.4, 24.0 + index % 7, phase * 1.4, 36.0) * np.exp(-(radius * 2.8) ** 2)
        motif = np.clip(pulse * 0.54 + scan * 0.34 + star * 0.46 + sat * edge * 0.24, 0, 1)
        polish = np.clip(pulse * 0.46 + star * 0.40, 0, 1)
        satin = np.clip(scan * 0.26 + broad * 0.24, 0, 1)
    elif any(k in text for k in ("serape", "woven", "beadwork", "huichol", "rosario", "charro")):
        warp = ridge(x + broad * 0.10, 116.0 + index % 23, phase, 42.0)
        weft = ridge(y + edge * 0.08, 126.0 + index % 29, phase * 1.3, 44.0)
        beads = micro_mosaic(shape, 32100 + index * 131, 4, 0.976)
        motif = np.clip(warp * 0.30 + weft * 0.30 + beads * 0.54 + edge * 0.28, 0, 1)
        polish = np.clip(beads * 0.38 + warp * 0.18, 0, 1)
        satin = np.clip(warp * 0.30 + weft * 0.34 + broad * 0.30, 0, 1)
    elif any(k in text for k in ("agave", "nopal", "verde", "jade", "cactus", "maguey")):
        blade = ridge(theta / np.pi + radius * 1.4, 20.0 + index % 7, phase, 30.0) * np.exp(-(radius * 1.75) ** 2)
        thorn = micro_mosaic(shape, 33100 + index * 137, 6, 0.984)
        vein = ridge(x * 0.68 + y * 1.38 + broad * 0.20, 76.0 + index % 19, phase * 1.2, 36.0)
        motif = np.clip(blade * 0.52 + vein * 0.38 + thorn * 0.28 + edge * 0.30, 0, 1)
        polish = np.clip(blade * 0.30 + vein * 0.24 + thorn * 0.18, 0, 1)
        satin = np.clip((1.0 - sat) * broad * 0.38 + vein * 0.28, 0, 1)
    else:
        confetti = micro_mosaic(shape, 34100 + index * 139, 4, 0.982)
        ribbon = ridge(x * 0.92 + y * 1.16 + broad * 0.18, 90.0 + index % 23, phase, 38.0)
        motif = np.clip(confetti * 0.46 + ribbon * 0.36 + edge * 0.26, 0, 1)
        polish = np.clip(confetti * 0.30 + ribbon * 0.20, 0, 1)
        satin = np.clip(broad * 0.36 + ribbon * 0.20, 0, 1)

    return motif.astype(np.float32), polish.astype(np.float32), satin.astype(np.float32)


def spec_personality(name: str, style: str) -> dict[str, float | str]:
    text = f"{name} {style}".lower()
    p = {
        "metal_base": 42.0,
        "rough_base": 96.0,
        "clear_base": 54.0,
        "metal_gain": 174.0,
        "rough_gain": 88.0,
        "clear_gain": 184.0,
        "flake": 1.0,
        "line": 1.0,
        "kind": "festival",
    }
    if any(k in text for k in ("sun", "sunfire", "sunburst", "marigold", "dawn", "gold", "cempasuchil", "flash")):
        p.update(kind="sun", metal_base=62.0, rough_base=74.0, clear_base=64.0, metal_gain=198.0, rough_gain=66.0, clear_gain=206.0, flake=1.25, line=1.12)
    if any(k in text for k in ("calavera", "muertos", "nocturne", "eclipse", "shadow", "mole", "xolo")):
        p.update(kind="muertos", metal_base=46.0, rough_base=112.0, clear_base=44.0, metal_gain=190.0, rough_gain=104.0, clear_gain=174.0, flake=1.05, line=1.34)
    if any(k in text for k in ("talavera", "azulejo", "tile", "lace", "mosaic")):
        p.update(kind="tile", metal_base=36.0, rough_base=86.0, clear_base=70.0, metal_gain=154.0, rough_gain=74.0, clear_gain=218.0, flake=0.88, line=1.42)
    if any(k in text for k in ("quetzal", "jaguar", "mayan", "zapotec", "aztec", "pyramid", "thunder")):
        p.update(kind="glyph", metal_base=54.0, rough_base=88.0, clear_base=54.0, metal_gain=204.0, rough_gain=82.0, clear_gain=196.0, flake=0.98, line=1.48)
    if any(k in text for k in ("cenote", "playa", "riviera", "pacific", "coast", "aqua", "blue", "water")):
        p.update(kind="water", metal_base=30.0, rough_base=68.0, clear_base=76.0, metal_gain=138.0, rough_gain=58.0, clear_gain=232.0, flake=0.92, line=1.10)
    if any(k in text for k in ("lowrider", "luchador", "cantina", "neon", "fiesta", "carnival", "spark")):
        p.update(kind="neon", metal_base=66.0, rough_base=58.0, clear_base=70.0, metal_gain=210.0, rough_gain=54.0, clear_gain=220.0, flake=1.35, line=1.36)
    if any(k in text for k in ("serape", "woven", "beadwork", "huichol", "rosario", "charro")):
        p.update(kind="woven", metal_base=44.0, rough_base=118.0, clear_base=48.0, metal_gain=168.0, rough_gain=112.0, clear_gain=172.0, flake=1.10, line=1.28)
    if any(k in text for k in ("agave", "nopal", "verde", "jade", "cactus", "maguey")):
        p.update(kind="organic", metal_base=34.0, rough_base=124.0, clear_base=46.0, metal_gain=150.0, rough_gain=116.0, clear_gain=158.0, flake=0.82, line=1.06)
    return p


def semantic_masks(name: str, style: str, index: int, hue: np.ndarray, sat: np.ndarray, val: np.ndarray, luma: np.ndarray, edge: np.ndarray, lap: np.ndarray, broad: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    text = f"{name} {style}".lower()
    shape = luma.shape
    x, y = xy(shape)
    cx = 0.5 + np.sin(index * 1.31) * 0.11
    cy = 0.5 + np.cos(index * 1.77) * 0.10
    dx = x - cx
    dy = y - cy
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.04), np.abs(hue - 0.98)) * 5.8, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.035) + np.exp(-((hue - 0.70) ** 2) / 0.032)) * sat, 0, 1)
    bright = sigmoid(val * 0.70 + sat * 0.30, 0.56, 9.5)
    contour = np.clip(edge * 0.62 + lap * 0.32 + broad * 0.22, 0, 1)

    if any(k in text for k in ("sun", "sunfire", "sunburst", "marigold", "dawn", "gold", "cempasuchil", "flash")):
        rays = ridge(theta / np.pi + radius * (3.0 + index % 5), 20.0 + index % 9, index * 0.041, 24.0)
        core = np.exp(-(radius * (3.8 + index % 4)) ** 2).astype(np.float32)
        hot = np.clip(warm * bright * 0.60 + rays * 0.44 + core * 0.58 + contour * warm * 0.22, 0, 1)
        trace = np.clip(contour * 0.46 + rays * 0.38 + edge * warm * 0.34, 0, 1)
        recess = np.clip((1.0 - hot) * broad * 0.40 + (1.0 - val) * 0.26, 0, 1)
    elif any(k in text for k in ("calavera", "muertos", "eclipse", "nocturne", "shadow", "xolo", "mole")):
        eyes = spark(shape, 23100 + index * 61, 0.9954, 0.18)
        bone_trace = ridge(x * 0.84 - y * 1.18 + broad * 0.24, 88.0 + index % 21, index * 0.034, 36.0)
        hot = np.clip(contour * 0.54 + eyes * 0.86 + warm * bright * 0.28, 0, 1)
        trace = np.clip(edge * 0.70 + bone_trace * 0.46 + eyes * 0.42, 0, 1)
        recess = np.clip((1.0 - val) * 0.52 + broad * 0.34 + contour * 0.10, 0, 1)
    elif any(k in text for k in ("talavera", "azulejo", "tile", "lace", "mosaic")):
        grout = ridge(x * 1.0 + y * 0.0, 42.0 + index % 11, index * 0.017, 28.0)
        grout = np.maximum(grout, ridge(y * 1.0 + x * 0.0, 42.0 + index % 13, index * 0.023, 28.0))
        hot = np.clip(cool * 0.38 + bright * sat * 0.22 + grout * 0.34 + contour * 0.32, 0, 1)
        trace = np.clip(contour * 0.62 + grout * 0.52, 0, 1)
        recess = np.clip((1.0 - cool) * broad * 0.34 + (1.0 - val) * 0.22, 0, 1)
    elif any(k in text for k in ("quetzal", "jaguar", "mayan", "zapotec", "aztec", "pyramid", "thunder")):
        glyph = ridge(x * 1.24 + y * 0.72 + edge * 0.18, 74.0 + index % 29, index * 0.031, 34.0)
        flash = spark(shape, 24100 + index * 67, 0.9942, 0.22)
        hot = np.clip(contour * 0.52 + glyph * 0.46 + flash * 0.54 + warm * bright * 0.20, 0, 1)
        trace = np.clip(edge * 0.66 + glyph * 0.56 + flash * 0.28, 0, 1)
        recess = np.clip((1.0 - val) * 0.36 + broad * 0.42, 0, 1)
    elif any(k in text for k in ("cenote", "playa", "riviera", "pacific", "coast", "aqua", "blue", "water")):
        ripple = ridge(x * 1.42 + np.sin(y * np.pi * 5.0 + broad) * 0.12, 70.0 + index % 17, index * 0.027, 28.0)
        foam = spark(shape, 25100 + index * 71, 0.9938, 0.28)
        hot = np.clip(cool * 0.48 + ripple * 0.38 + foam * 0.48, 0, 1)
        trace = np.clip(contour * 0.42 + ripple * 0.58 + foam * 0.24, 0, 1)
        recess = np.clip((1.0 - cool) * broad * 0.34 + (1.0 - val) * 0.22, 0, 1)
    elif any(k in text for k in ("lowrider", "luchador", "cantina", "neon", "fiesta", "carnival", "spark")):
        neon = ridge(x * 1.55 - y * 0.58 + edge * 0.18, 110.0 + index % 27, index * 0.047, 42.0)
        sparks = spark(shape, 26100 + index * 73, 0.9908, 0.16)
        hot = np.clip(neon * 0.62 + sparks * 0.66 + bright * sat * 0.34, 0, 1)
        trace = np.clip(contour * 0.42 + neon * 0.64 + sparks * 0.24, 0, 1)
        recess = np.clip((1.0 - val) * 0.28 + broad * 0.30, 0, 1)
    elif any(k in text for k in ("serape", "woven", "beadwork", "huichol", "rosario", "charro")):
        weave_a = ridge(x + broad * 0.16, 86.0 + index % 19, index * 0.019, 30.0)
        weave_b = ridge(y + edge * 0.12, 96.0 + index % 23, index * 0.025, 32.0)
        beads = spark(shape, 27100 + index * 79, 0.9898, 0.20)
        hot = np.clip(beads * 0.54 + weave_a * 0.30 + weave_b * 0.26 + sat * bright * 0.24, 0, 1)
        trace = np.clip(contour * 0.38 + weave_a * 0.46 + weave_b * 0.46 + beads * 0.22, 0, 1)
        recess = np.clip((1.0 - val) * 0.30 + broad * 0.38, 0, 1)
    else:
        shimmer = spark(shape, 28100 + index * 83, 0.9938, 0.22)
        hot = np.clip(contour * 0.38 + shimmer * 0.50 + bright * sat * 0.30, 0, 1)
        trace = np.clip(contour * 0.64 + shimmer * 0.24, 0, 1)
        recess = np.clip((1.0 - val) * 0.34 + broad * 0.34, 0, 1)
    return hot.astype(np.float32), trace.astype(np.float32), recess.astype(np.float32)


def detail_grade(channel: np.ndarray, mid: float, span: float, blend: float) -> np.ndarray:
    detail = normalize01(channel)
    graded = mid + (detail - 0.5) * span
    return np.clip(channel * (1.0 - blend) + graded * blend, 0, 255).astype(np.float32)


def make_spec_plate(plate: Image.Image, index: int, name: str, style: str) -> Image.Image:
    rgb = np.asarray(plate, dtype=np.float32) / 255.0
    bgr = (rgb[:, :, ::-1] * 255).astype(np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue = hsv[:, :, 0] / 179.0
    sat = hsv[:, :, 1] / 255.0
    val = hsv[:, :, 2] / 255.0
    luma = np.clip(rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), 0, 1)
    blur = cv2.GaussianBlur(luma, (0, 0), 1.15)
    blur4 = cv2.GaussianBlur(luma, (0, 0), 4.2)
    blur12 = cv2.GaussianBlur(luma, (0, 0), 12.0)
    high = normalize01(np.abs(luma - blur))
    mid = normalize01(np.abs(blur - blur4))
    broad = normalize01(np.abs(blur4 - blur12))
    lap = normalize01(np.abs(cv2.Laplacian(luma, cv2.CV_32F, ksize=3)))
    sobel_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    edge = normalize01(np.sqrt(sobel_x * sobel_x + sobel_y * sobel_y))
    p = spec_personality(name, style)
    x, y = xy((SIZE, SIZE))
    phase = ((index * 37) % 360) / 360.0
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.04), np.abs(hue - 0.98)) * 5.8, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.035) + np.exp(-((hue - 0.70) ** 2) / 0.032)) * sat, 0, 1)
    bright = sigmoid(val * 0.70 + sat * 0.30, 0.56, 9.5)
    contour = np.clip(edge * 0.58 + lap * 0.40 + high * 0.36 + mid * 0.24 + broad * 0.14, 0, 1)
    hot, trace, recess = semantic_masks(name, style, index, hue, sat, val, luma, edge, lap, broad)
    grain = spark((SIZE, SIZE), 9100 + index * 137, 0.9815 - min(float(p["flake"]) * 0.004, 0.008), 0.32)
    flakes = spark((SIZE, SIZE), 10100 + index * 149, 0.9928, 0.20)
    pin = spark((SIZE, SIZE), 11100 + index * 157, 0.9960, 0.16)
    silk_a = ridge(x * 1.24 + y * 0.68 + broad * 0.36, 74.0 + index % 19, phase, 32.0)
    silk_b = ridge(x * -0.72 + y * 1.52 + mid * 0.28, 92.0 + index % 23, phase * 1.7, 36.0)
    silk = np.clip(silk_a * 0.46 + silk_b * 0.36 + trace * 0.20, 0, 1)
    pearl = np.clip(np.sin((hue * (8.0 + index % 5) + broad * 0.74 + x * 1.2 - y * 0.6) * np.pi) * 0.5 + 0.5, 0, 1)
    hidden, hidden_polish, hidden_satin = hidden_cultural_motif(name, style, index, hue, sat, val, edge, broad)
    candy_cell = micro_mosaic((SIZE, SIZE), 12100 + index * 163, 3 + index % 3, 0.974 - min(float(p["flake"]) * 0.003, 0.008))
    enamel_dot = micro_mosaic((SIZE, SIZE), 13100 + index * 167, 5 + index % 4, 0.982)
    shadow_pore = micro_mosaic((SIZE, SIZE), 14100 + index * 173, 7 + index % 5, 0.988)
    metal_energy = np.clip(
        sat * 0.18
        + contour * 0.34
        + trace * 0.40 * float(p["line"])
        + hot * 0.36
        + grain * 0.34
        + flakes * 0.72
        + pin * 0.92,
        0,
        1,
    )
    clear_energy = np.clip(
        bright * 0.24
        + edge * 0.26
        + trace * 0.36
        + hot * 0.46
        + silk * 0.28
        + pearl * 0.20
        + flakes * 0.42
        + pin * 0.86,
        0,
        1,
    )
    rough_energy = np.clip(
        recess * 0.56
        + (1.0 - val) * 0.24
        + broad * 0.26
        + mid * 0.16
        - hot * 0.20
        - silk * 0.18,
        0,
        1,
    )
    metal_energy = np.clip(metal_energy + hidden * 0.34 + hidden_polish * 0.26 + candy_cell * 0.34 + enamel_dot * 0.16, 0, 1)
    clear_energy = np.clip(clear_energy + hidden * 0.42 + hidden_polish * 0.48 + candy_cell * 0.22 + enamel_dot * 0.28, 0, 1)
    rough_energy = np.clip(rough_energy + hidden_satin * 0.42 + shadow_pore * 0.26 - hidden_polish * 0.18, 0, 1)
    kind = str(p["kind"])
    if kind == "sun":
        metal_energy = np.clip(metal_energy + warm * 0.28 + hot * 0.24, 0, 1)
        clear_energy = np.clip(clear_energy + hot * 0.28 + trace * 0.16, 0, 1)
        rough_energy = np.clip(rough_energy - hot * 0.20 + recess * 0.18, 0, 1)
    elif kind == "muertos":
        metal_energy = np.clip(metal_energy + trace * 0.28 + flakes * 0.18, 0, 1)
        clear_energy = np.clip(clear_energy + hot * 0.34 + pin * 0.28, 0, 1)
        rough_energy = np.clip(rough_energy + recess * 0.28 + (1.0 - bright) * 0.16, 0, 1)
    elif kind == "tile":
        clear_energy = np.clip(clear_energy + cool * 0.34 + trace * 0.28, 0, 1)
        rough_energy = np.clip(rough_energy + broad * 0.18 - trace * 0.10, 0, 1)
    elif kind == "glyph":
        metal_energy = np.clip(metal_energy + trace * 0.36 + warm * 0.18, 0, 1)
        clear_energy = np.clip(clear_energy + hot * 0.20, 0, 1)
    elif kind == "water":
        metal_energy = np.clip(metal_energy * 0.78 + cool * 0.36 + flakes * 0.20, 0, 1)
        clear_energy = np.clip(clear_energy + cool * 0.42 + silk * 0.28, 0, 1)
        rough_energy = np.clip(rough_energy * 0.70 + broad * 0.18, 0, 1)
    elif kind == "neon":
        metal_energy = np.clip(metal_energy + hot * 0.34 + flakes * 0.26, 0, 1)
        clear_energy = np.clip(clear_energy + hot * 0.40 + pin * 0.32, 0, 1)
        rough_energy = np.clip(rough_energy - hot * 0.22 + recess * 0.12, 0, 1)
    elif kind == "woven":
        rough_energy = np.clip(rough_energy + silk * 0.30 + broad * 0.18, 0, 1)
        metal_energy = np.clip(metal_energy + flakes * 0.22, 0, 1)
    elif kind == "organic":
        rough_energy = np.clip(rough_energy + (1.0 - sat) * 0.20 + broad * 0.22, 0, 1)
        clear_energy = np.clip(clear_energy * 0.82 + silk * 0.16, 0, 1)

    metallic = np.clip(float(p["metal_base"]) + metal_energy * float(p["metal_gain"]) + trace * 38 + warm * 28 + cool * 18, 0, 255)
    rough = np.clip(float(p["rough_base"]) + rough_energy * float(p["rough_gain"]) - clear_energy * 64 - hot * 30 + recess * 28, 18, 235)
    clearcoat = np.clip(float(p["clear_base"]) + clear_energy * float(p["clear_gain"]) + hot * 68 + trace * 44 + cool * 30 + warm * 18, 16, 255)

    # Spec-only embossed depth: tiny per-channel offsets make hot edges and
    # recessed shadows pop in sim instead of previewing as flat green/yellow.
    metallic = np.clip(
        metallic
        + np.roll(trace, 1 + index % 3, axis=1) * 36
        + np.roll(hidden, 1 + index % 2, axis=1) * 52
        + candy_cell * 54
        + flakes * 70
        + pin * 120,
        0,
        255,
    )
    rough = np.clip(
        rough
        - np.roll(hot, 1 + index % 4, axis=0) * 42
        - np.roll(hidden_polish, 1 + index % 3, axis=0) * 36
        + np.roll(hidden_satin, 2 + index % 2, axis=1) * 56
        + np.roll(recess, 2, axis=1) * 46
        + shadow_pore * 28
        + grain * 18,
        18,
        235,
    )
    clearcoat = np.clip(
        clearcoat
        + np.roll(edge, -(1 + index % 5), axis=1) * 48
        + np.roll(trace, -2, axis=0) * 62
        + np.roll(hidden_polish, -(1 + index % 4), axis=1) * 72
        + enamel_dot * 44
        + pin * 92,
        16,
        255,
    )

    rot = index % 6
    if rot == 1:
        metallic = np.clip(metallic + cool * 36 + silk * 18, 0, 255)
    elif rot == 2:
        clearcoat = np.clip(clearcoat + pearl * 54 + hot * 24, 16, 255)
    elif rot == 3:
        rough = np.clip(rough + recess * 42 - silk * 26, 18, 235)
    elif rot == 4:
        metallic = np.clip(metallic + warm * 42 + pin * 30, 0, 255)
        clearcoat = np.clip(clearcoat + trace * 28, 16, 255)
    elif rot == 5:
        rough = np.clip(rough + broad * 38 + recess * 24, 18, 235)
        clearcoat = np.clip(clearcoat + flakes * 40, 16, 255)

    metallic = detail_grade(metallic, 132.0 + float(p["metal_base"]) * 0.08, 234.0, 0.32)
    rough = detail_grade(rough, 104.0 + float(p["rough_base"]) * 0.06, 204.0, 0.30)
    clearcoat = detail_grade(clearcoat, 154.0 + float(p["clear_base"]) * 0.06, 238.0, 0.36)

    spec = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    spec[:, :, 0] = metallic.astype(np.uint8)
    spec[:, :, 1] = rough.astype(np.uint8)
    spec[:, :, 2] = clearcoat.astype(np.uint8)
    spec[:, :, 3] = 255
    return Image.fromarray(spec, "RGBA")


def save_png_fast(img: Image.Image, path: Path) -> None:
    # optimize=True is brutally slow on 2048 texture batches; low compression keeps rebuilds responsive.
    img.save(path, compress_level=1, optimize=False)


def outputs_current(src: Path, *outputs: Path) -> bool:
    if not all(path.exists() for path in outputs):
        return False
    newest_input = max(src.stat().st_mtime, SCRIPT_MTIME)
    return min(path.stat().st_mtime for path in outputs) >= newest_input


def swatch_hex(plate: Image.Image) -> str:
    arr = np.asarray(plate.resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
    weights = np.clip(arr.max(axis=2) - 38.0, 0, 255)
    if float(weights.sum()) <= 0.0:
        color = arr.reshape(-1, 3).mean(axis=0)
    else:
        color = (arr * weights[:, :, None]).reshape(-1, 3).sum(axis=0) / weights.sum()
    color = np.clip(color, 0, 255).astype(np.uint8)
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def main() -> None:
    started = time.perf_counter()
    files = sorted(SOURCE_DIR.glob("*.png"))
    if len(files) != len(NAMES):
        raise RuntimeError(f"Expected {len(NAMES)} Viva Mexico sources, found {len(files)}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    finishes = []
    rebuilt = 0
    reused = 0
    for index, (src, name) in enumerate(zip(files, NAMES), start=1):
        item_started = time.perf_counter()
        finish_id = slug(name)
        texture_path = OUT_DIR / f"{finish_id}.png"
        spec_path = OUT_DIR / f"{finish_id}_spec.png"
        with Image.open(src) as probe:
            crop_y = int(probe.size[1] * 0.795)
        if outputs_current(src, texture_path, spec_path):
            plate = Image.open(texture_path).convert("RGB")
            reused += 1
            action = "reused"
        else:
            plate, crop_y = make_paint_plate(src)
            spec = make_spec_plate(plate, index, name, STYLES[index - 1])
            save_png_fast(plate, texture_path)
            save_png_fast(spec, spec_path)
            rebuilt += 1
            action = "rebuilt"
        finishes.append(
            {
                "id": finish_id,
                "name": name,
                "source": str(src),
                "texture": f"assets/reference_textures/cultural/viva_mexico/{finish_id}.png",
                "spec": f"assets/reference_textures/cultural/viva_mexico/{finish_id}_spec.png",
                "crop_y": crop_y,
                "style": STYLES[index - 1],
                "size": [SIZE, SIZE],
                "swatch": swatch_hex(plate),
            }
        )
        print(f"{index:02d}/{len(files)} {action} {finish_id} {time.perf_counter() - item_started:.2f}s")
    manifest = {
        "set": "VIVA MEXICO",
        "family": "Cultural",
        "finishes": finishes,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"generated={len(finishes)} rebuilt={rebuilt} reused={reused} elapsed={time.perf_counter() - started:.2f}s out={OUT_DIR}")


if __name__ == "__main__":
    main()
