"""Crop COLORSHOXX AI poster cards, bake 2048 paint plates + paint-traced spec maps.

SPB-105 / owner batch 2026-05-27: ten AI-generated COLORSHOXX finishes with footer
banners removed, resized to 2048², paired with Viva-Mexico-style traced spec plates.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = 2048

# Cursor chat assets (owner drop); also copied into project source/ on first run.
CURSOR_ASSETS = Path(
    r"C:\Users\Ricky's PC\.cursor\projects\c-DRIVE-E-BACKUP-Shokker-Paint-Booth-Gold-to-Platinum\assets"
)
SOURCE_DIR = ROOT / "assets" / "reference_textures" / "colorshoxx" / "ai_reference_2026_05_27" / "source"
OUT_DIR = ROOT / "assets" / "reference_textures" / "colorshoxx" / "ai_reference_2026_05_27"

FINISHES: list[tuple[int, str, str, str]] = [
    (1, "cx_electric_storm", "Electric Storm", "electric_vein"),
    (2, "cx_hyperflip_crimson_prism", "Crimson Prism", "prismatic_flake"),
    (3, "cx_hyperflip_electric_blue_copper", "Electric Blue / Copper", "copper_vein"),
    (4, "cx_tropical_sunset", "Tropical Sunset", "sunburst_flake"),
    (5, "cx_emerald_city", "Emerald City", "emerald_gold"),
    (6, "cx_thunderstorm", "Thunderstorm", "lightning_rain"),
    (7, "cx_galaxy_dust", "Galaxy Dust", "star_nebula"),
    (8, "cx_red_green_chaos", "Red / Green Impossible", "chaos_flake"),
    (9, "cx_neon_dreams", "Neon Dreams", "neon_grid"),
    (10, "cx_volcanic_glass", "Volcanic Glass", "obsidian_crack"),
]


def _load_viva_module():
    path = ROOT / "scripts" / "build_cultural_viva_mexico.py"
    spec = importlib.util.spec_from_file_location("build_cultural_viva_mexico", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["build_cultural_viva_mexico"] = mod
    spec.loader.exec_module(mod)
    return mod


VM = _load_viva_module()


def find_source_image(card_num: int) -> Path | None:
    pattern = re.compile(rf"__{card_num}_-.*\.png$", re.IGNORECASE)
    for folder in (CURSOR_ASSETS, SOURCE_DIR):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() == ".png" and pattern.search(path.name):
                return path
    return None


def _row_stats(luma: np.ndarray, y: int) -> tuple[float, float, float, float, float]:
    row = luma[y, :]
    mean = float(np.mean(row))
    std = float(np.std(row))
    mx = float(np.max(row))
    bright120 = float(np.mean(row > 120.0))
    bright200 = float(np.mean(row > 200.0))
    return mean, std, mx, bright120, bright200


def _is_footer_row(rgb: np.ndarray, y: int, h: int) -> bool:
    row = rgb[y, :, :]
    luma = row @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mean = float(np.mean(luma))
    std = float(np.std(luma))
    mx = float(np.max(luma))
    b120 = float(np.mean(luma > 120.0))
    b200 = float(np.mean(luma > 200.0))
    rmean = float(np.mean(row[:, 0]))
    gmean = float(np.mean(row[:, 1]))
    bmean = float(np.mean(row[:, 2]))
    yf = y / h
    if yf < 0.78:
        return False
    # Bright neutral separator rule above the caption slab.
    if mean > 32.0 and std < 14.0:
        above = float(np.mean(rgb[max(y - 1, 0), :, :] @ [0.2126, 0.7152, 0.0722]))
        below = float(np.mean(rgb[min(y + 1, h - 1), :, :] @ [0.2126, 0.7152, 0.0722]))
        if above < 28.0 and below < 40.0:
            return True
    # Colored brand stripe (red/gold/cyan bar above footer text).
    if yf >= 0.82 and std < 16.0:
        if rmean > 110.0 and rmean > gmean * 1.30 and rmean > bmean * 1.30:
            return True
        if gmean > 95.0 and gmean > rmean * 1.15 and gmean > bmean * 1.15:
            return True
        if bmean > 95.0 and bmean > rmean * 1.10 and std < 12.0:
            return True
        if mean > 42.0 and max(rmean, gmean, bmean) > 90.0 and std < 12.0:
            return True
    # Flat black footer slab.
    if yf >= 0.84 and mean < 22.0 and std < 12.0 and b200 < 0.03:
        return True
    # Large number / title glyphs (sparse bright peaks on dark bar).
    if yf >= 0.85 and std > 32.0 and b120 > 0.05:
        return True
    if yf >= 0.85 and std > 45.0 and b120 > 0.04:
        return True
    # Residual caption text on the bottom bar.
    if yf >= 0.88 and mean < 45.0 and std > 10.0 and mx > 60.0 and b120 > 0.015:
        return True
    return False


def detect_footer_crop_y(img: Image.Image) -> int:
    """Return crop height that removes the COLORSHOXX card footer entirely."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, _w = rgb.shape[:2]
    search_lo = int(h * 0.76)
    footer_rows = [y for y in range(search_lo, h) if _is_footer_row(rgb, y, h)]
    if footer_rows:
        return max(int(h * 0.72), min(footer_rows))
    return int(h * 0.865)


def crop_art_area(img: Image.Image) -> tuple[Image.Image, int]:
    w, h = img.size
    crop_y = detect_footer_crop_y(img)
    crop_y = max(int(h * 0.72), min(crop_y, h))
    return img.crop((0, 0, w, crop_y)), crop_y


def _crop_is_valid(img: Image.Image, crop_y: int) -> bool:
    """True when crop_y cuts above the footer and removes caption rows below."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, _w = rgb.shape[:2]
    crop_y = max(1, min(int(crop_y), h))
    removed = [_is_footer_row(rgb, y, h) for y in range(crop_y, h)]
    if not any(removed):
        return False
    if _is_footer_row(rgb, crop_y - 1, h):
        return False
    return True


def make_paint_plate(src: Path) -> tuple[Image.Image, int]:
    img = Image.open(src).convert("RGB")
    w, full_h = img.size
    crop_y = detect_footer_crop_y(img)
    for _ in range(8):
        crop_y = max(int(full_h * 0.72), min(crop_y, full_h))
        if _crop_is_valid(img, crop_y):
            break
        crop_y = max(int(full_h * 0.72), int(crop_y - full_h * 0.012))
    else:
        raise RuntimeError(f"Could not find footer-safe crop: {src.name}")

    cropped = img.crop((0, 0, w, crop_y))
    side = min(cropped.size[0], cropped.size[1])
    square = cropped.crop((0, 0, side, side))
    plate = square.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    plate = ImageEnhance.Contrast(plate).enhance(1.04)
    plate = ImageEnhance.Sharpness(plate).enhance(1.08)
    plate = plate.filter(ImageFilter.UnsharpMask(radius=0.8, percent=55, threshold=3))
    return plate, crop_y


def colorshoxx_spec_personality(finish_id: str) -> dict[str, float | str]:
    profiles: dict[str, dict[str, float | str]] = {
        "cx_electric_storm": dict(
            kind="neon", metal_base=58.0, rough_base=62.0, clear_base=68.0,
            metal_gain=208.0, rough_gain=58.0, clear_gain=228.0, flake=1.42, line=1.52,
        ),
        "cx_hyperflip_crimson_prism": dict(
            kind="neon", metal_base=72.0, rough_base=54.0, clear_base=74.0,
            metal_gain=222.0, rough_gain=48.0, clear_gain=236.0, flake=1.55, line=1.18,
        ),
        "cx_hyperflip_electric_blue_copper": dict(
            kind="neon", metal_base=58.0, rough_base=66.0, clear_base=76.0,
            metal_gain=224.0, rough_gain=64.0, clear_gain=242.0, flake=1.38, line=1.58,
        ),
        "cx_tropical_sunset": dict(
            kind="sun", metal_base=64.0, rough_base=68.0, clear_base=70.0,
            metal_gain=204.0, rough_gain=64.0, clear_gain=214.0, flake=1.38, line=1.08,
        ),
        "cx_emerald_city": dict(
            kind="tile", metal_base=52.0, rough_base=78.0, clear_base=66.0,
            metal_gain=210.0, rough_gain=72.0, clear_gain=220.0, flake=1.12, line=1.56,
        ),
        "cx_thunderstorm": dict(
            kind="glyph", metal_base=46.0, rough_base=82.0, clear_base=62.0,
            metal_gain=212.0, rough_gain=76.0, clear_gain=218.0, flake=1.22, line=1.62,
        ),
        "cx_galaxy_dust": dict(
            kind="neon", metal_base=44.0, rough_base=66.0, clear_base=74.0,
            metal_gain=196.0, rough_gain=56.0, clear_gain=232.0, flake=1.48, line=1.24,
        ),
        "cx_red_green_chaos": dict(
            kind="neon", metal_base=68.0, rough_base=58.0, clear_base=68.0,
            metal_gain=216.0, rough_gain=52.0, clear_gain=228.0, flake=1.62, line=1.10,
        ),
        "cx_neon_dreams": dict(
            kind="neon", metal_base=70.0, rough_base=52.0, clear_base=76.0,
            metal_gain=214.0, rough_gain=46.0, clear_gain=240.0, flake=1.36, line=1.68,
        ),
        "cx_volcanic_glass": dict(
            kind="muertos", metal_base=50.0, rough_base=98.0, clear_base=58.0,
            metal_gain=200.0, rough_gain=96.0, clear_gain=206.0, flake=1.08, line=1.48,
        ),
    }
    return profiles.get(finish_id, VM.spec_personality("festival", "colorshoxx"))


def colorshoxx_semantic_masks(
    finish_id: str,
    index: int,
    hue: np.ndarray,
    sat: np.ndarray,
    val: np.ndarray,
    luma: np.ndarray,
    edge: np.ndarray,
    lap: np.ndarray,
    broad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shape = luma.shape
    x, y = VM.xy(shape)
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.04), np.abs(hue - 0.98)) * 5.8, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.035) + np.exp(-((hue - 0.70) ** 2) / 0.032)) * sat, 0, 1)
    bright = VM.sigmoid(val * 0.70 + sat * 0.30, 0.56, 9.5)
    contour = np.clip(edge * 0.62 + lap * 0.32 + broad * 0.22, 0, 1)
    high = VM.normalize01(np.abs(luma - cv2.GaussianBlur(luma, (0, 0), 1.15)))

    if finish_id == "cx_electric_storm":
        veins = VM.ridge(x * 1.18 + y * 0.92 + edge * 0.22, 118.0 + index, index * 0.029, 22.0)
        sparks = VM.spark(shape, 30100 + index * 71, 0.9936, 0.20)
        hot = np.clip(high * 0.58 + bright * 0.42 + sparks * 0.72 + cool * 0.34, 0, 1)
        trace = np.clip(edge * 0.74 + veins * 0.58 + sparks * 0.46 + contour * 0.28, 0, 1)
        recess = np.clip((1.0 - val) * 0.48 + broad * 0.32, 0, 1)
    elif finish_id == "cx_hyperflip_crimson_prism":
        facets = VM.micro_mosaic(shape, 31100 + index * 73, 4 + index % 3, 0.978)
        prism = VM.spark(shape, 32100 + index * 79, 0.9924, 0.14)
        hot = np.clip(facets * 0.62 + prism * 0.86 + bright * warm * 0.28, 0, 1)
        trace = np.clip(edge * 0.68 + facets * 0.52 + lap * 0.36, 0, 1)
        recess = np.clip((1.0 - bright) * 0.44 + broad * 0.28, 0, 1)
    elif finish_id == "cx_hyperflip_electric_blue_copper":
        copper = warm * bright * sat
        blue_flake = VM.spark(shape, 33100 + index * 83, 0.9940, 0.18)
        vein = VM.ridge(x * 0.96 + y * 1.08 + copper * 0.18, 96.0 + index, index * 0.031, 26.0)
        hot = np.clip(copper * 0.72 + vein * 0.58 + blue_flake * 0.68 + cool * 0.32 + high * 0.24, 0, 1)
        trace = np.clip(edge * 0.78 + vein * 0.72 + copper * 0.44 + lap * 0.28, 0, 1)
        recess = np.clip(cool * broad * 0.36 + (1.0 - val) * 0.28, 0, 1)
    elif finish_id == "cx_tropical_sunset":
        cx, cy = 0.82, 0.82
        dx, dy = x - cx, y - cy
        radius = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)
        rays = VM.ridge(theta / np.pi + radius * 4.2, 28.0 + index, index * 0.037, 20.0)
        flake = VM.spark(shape, 34100 + index * 89, 0.9932, 0.22)
        hot = np.clip(warm * bright * 0.58 + rays * 0.52 + flake * 0.64, 0, 1)
        trace = np.clip(rays * 0.62 + edge * warm * 0.38 + flake * 0.28, 0, 1)
        recess = np.clip((1.0 - hot) * broad * 0.36 + (1.0 - val) * 0.22, 0, 1)
    elif finish_id == "cx_emerald_city":
        vertical = VM.ridge(y * 1.0 + x * 0.08, 54.0 + index % 13, index * 0.019, 30.0)
        gold = warm * bright * edge
        gem = cool * sat * val
        hot = np.clip(gold * 0.58 + gem * 0.34 + vertical * 0.28 + contour * 0.24, 0, 1)
        trace = np.clip(vertical * 0.66 + edge * 0.58 + gold * 0.32, 0, 1)
        recess = np.clip((1.0 - gem) * broad * 0.38 + (1.0 - val) * 0.24, 0, 1)
    elif finish_id == "cx_thunderstorm":
        rain = VM.ridge(x * 0.18 + y * 1.42, 140.0 + index, index * 0.021, 18.0)
        bolt = VM.ridge(x * 1.06 + y * 0.84 + edge * 0.24, 88.0 + index, index * 0.033, 24.0)
        flash = VM.spark(shape, 35100 + index * 97, 0.9948, 0.16)
        hot = np.clip(flash * 0.88 + bolt * 0.52 + cool * bright * 0.28, 0, 1)
        trace = np.clip(bolt * 0.68 + rain * 0.42 + edge * 0.48, 0, 1)
        recess = np.clip((1.0 - val) * 0.46 + rain * 0.22 + broad * 0.24, 0, 1)
    elif finish_id == "cx_galaxy_dust":
        stars = VM.spark(shape, 36100 + index * 101, 0.9958, 0.12)
        nebula = VM.ridge(x * 1.08 + y * 0.76 + sat * 0.12, 76.0 + index, index * 0.027, 32.0)
        hot = np.clip(stars * 0.96 + nebula * cool * 0.42 + bright * 0.24, 0, 1)
        trace = np.clip(nebula * 0.58 + edge * 0.44 + stars * 0.36, 0, 1)
        recess = np.clip((1.0 - val) * 0.52 + broad * 0.28, 0, 1)
    elif finish_id == "cx_red_green_chaos":
        red = np.clip(np.exp(-((hue - 0.98) ** 2) / 0.018) * sat, 0, 1)
        green = np.clip(np.exp(-((hue - 0.33) ** 2) / 0.022) * sat, 0, 1)
        flake = VM.micro_mosaic(shape, 37100 + index * 107, 5 + index % 4, 0.976)
        pin = VM.spark(shape, 38100 + index * 109, 0.9920, 0.16)
        hot = np.clip((red + green) * bright * 0.48 + flake * 0.58 + pin * 0.82, 0, 1)
        trace = np.clip(edge * 0.66 + flake * 0.54 + lap * 0.32, 0, 1)
        recess = np.clip((1.0 - bright) * 0.40 + broad * 0.30, 0, 1)
    elif finish_id == "cx_neon_dreams":
        grid_a = VM.ridge(x * 1.0, 64.0 + index % 11, index * 0.017, 26.0)
        grid_b = VM.ridge(y * 1.0, 64.0 + index % 13, index * 0.023, 26.0)
        grid = np.clip(np.maximum(grid_a, grid_b) * sat, 0, 1)
        glow = VM.spark(shape, 39100 + index * 113, 0.9934, 0.24)
        hot = np.clip(grid * bright * 0.62 + glow * 0.72 + cool * 0.28 + warm * 0.22, 0, 1)
        trace = np.clip(grid * 0.72 + edge * 0.58 + glow * 0.34, 0, 1)
        recess = np.clip((1.0 - grid) * (1.0 - val) * 0.62, 0, 1)
    elif finish_id == "cx_volcanic_glass":
        crack = VM.ridge(x * 1.14 + y * 0.88 + edge * 0.30, 102.0 + index, index * 0.035, 28.0)
        ember = VM.spark(shape, 40100 + index * 127, 0.9944, 0.20)
        glass = np.clip((1.0 - broad) * (1.0 - sat * 0.4) * val, 0, 1)
        hot = np.clip(ember * 0.92 + warm * bright * 0.48 + crack * warm * 0.36, 0, 1)
        trace = np.clip(crack * 0.72 + edge * 0.64 + glass * 0.18, 0, 1)
        recess = np.clip(glass * 0.52 + (1.0 - val) * 0.36 + broad * 0.22, 0, 1)
    else:
        return VM.semantic_masks("festival", "colorshoxx", index, hue, sat, val, luma, edge, lap, broad)

    return hot.astype(np.float32), trace.astype(np.float32), recess.astype(np.float32)


def make_spec_plate(plate: Image.Image, index: int, finish_id: str, name: str, style: str) -> Image.Image:
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
    high = VM.normalize01(np.abs(luma - blur))
    mid = VM.normalize01(np.abs(blur - blur4))
    broad = VM.normalize01(np.abs(blur4 - blur12))
    lap = VM.normalize01(np.abs(cv2.Laplacian(luma, cv2.CV_32F, ksize=3)))
    sobel_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    edge = VM.normalize01(np.sqrt(sobel_x * sobel_x + sobel_y * sobel_y))
    p = colorshoxx_spec_personality(finish_id)
    x, y = VM.xy((SIZE, SIZE))
    phase = ((index * 37) % 360) / 360.0
    warm = np.clip(1.0 - np.minimum(np.abs(hue - 0.04), np.abs(hue - 0.98)) * 5.8, 0.0, 1.0)
    cool = np.clip((np.exp(-((hue - 0.58) ** 2) / 0.035) + np.exp(-((hue - 0.70) ** 2) / 0.032)) * sat, 0, 1)
    bright = VM.sigmoid(val * 0.70 + sat * 0.30, 0.56, 9.5)
    contour = np.clip(edge * 0.58 + lap * 0.40 + high * 0.36 + mid * 0.24 + broad * 0.14, 0, 1)
    hot, trace, recess = colorshoxx_semantic_masks(finish_id, index, hue, sat, val, luma, edge, lap, broad)
    grain = VM.spark((SIZE, SIZE), 9100 + index * 137, 0.9815 - min(float(p["flake"]) * 0.004, 0.008), 0.32)
    flakes = VM.spark((SIZE, SIZE), 10100 + index * 149, 0.9928, 0.20)
    pin = VM.spark((SIZE, SIZE), 11100 + index * 157, 0.9960, 0.16)
    silk_a = VM.ridge(x * 1.24 + y * 0.68 + broad * 0.36, 74.0 + index % 19, phase, 32.0)
    silk_b = VM.ridge(x * -0.72 + y * 1.52 + mid * 0.28, 92.0 + index % 23, phase * 1.7, 36.0)
    silk = np.clip(silk_a * 0.46 + silk_b * 0.36 + trace * 0.20, 0, 1)
    pearl = np.clip(np.sin((hue * (8.0 + index % 5) + broad * 0.74 + x * 1.2 - y * 0.6) * np.pi) * 0.5 + 0.5, 0, 1)
    hidden, hidden_polish, hidden_satin = VM.hidden_cultural_motif(name, style, index, hue, sat, val, edge, broad)
    candy_cell = VM.micro_mosaic((SIZE, SIZE), 12100 + index * 163, 3 + index % 3, 0.974 - min(float(p["flake"]) * 0.003, 0.008))
    enamel_dot = VM.micro_mosaic((SIZE, SIZE), 13100 + index * 167, 5 + index % 4, 0.982)
    shadow_pore = VM.micro_mosaic((SIZE, SIZE), 14100 + index * 173, 7 + index % 5, 0.988)
    metal_energy = np.clip(
        sat * 0.18 + contour * 0.34 + trace * 0.40 * float(p["line"]) + hot * 0.36
        + grain * 0.34 + flakes * 0.72 + pin * 0.92,
        0, 1,
    )
    clear_energy = np.clip(
        bright * 0.24 + edge * 0.26 + trace * 0.36 + hot * 0.46 + silk * 0.28
        + pearl * 0.20 + flakes * 0.42 + pin * 0.86,
        0, 1,
    )
    rough_energy = np.clip(
        recess * 0.56 + (1.0 - val) * 0.24 + broad * 0.26 + mid * 0.16 - hot * 0.20 - silk * 0.18,
        0, 1,
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

    metallic = np.clip(float(p["metal_base"]) + metal_energy * float(p["metal_gain"]) + trace * 38 + warm * 28 + cool * 18, 0, 255)
    rough = np.clip(float(p["rough_base"]) + rough_energy * float(p["rough_gain"]) - clear_energy * 64 - hot * 30 + recess * 28, 18, 235)
    clearcoat = np.clip(float(p["clear_base"]) + clear_energy * float(p["clear_gain"]) + hot * 68 + trace * 44 + cool * 30 + warm * 18, 16, 255)

    metallic = np.clip(
        metallic + np.roll(trace, 1 + index % 3, axis=1) * 36 + np.roll(hidden, 1 + index % 2, axis=1) * 52
        + candy_cell * 54 + flakes * 70 + pin * 120,
        0, 255,
    )
    rough = np.clip(
        rough - np.roll(hot, 1 + index % 4, axis=0) * 42 - np.roll(hidden_polish, 1 + index % 3, axis=0) * 36
        + np.roll(hidden_satin, 2 + index % 2, axis=1) * 56 + np.roll(recess, 2, axis=1) * 46
        + shadow_pore * 28 + grain * 18,
        18, 235,
    )
    clearcoat = np.clip(
        clearcoat + np.roll(edge, -(1 + index % 5), axis=1) * 48 + np.roll(trace, -2, axis=0) * 62
        + np.roll(hidden_polish, -(1 + index % 4), axis=1) * 72 + enamel_dot * 44 + pin * 92,
        16, 255,
    )

    metallic = VM.detail_grade(metallic, 132.0 + float(p["metal_base"]) * 0.08, 234.0, 0.32)
    rough = VM.detail_grade(rough, 104.0 + float(p["rough_base"]) * 0.06, 204.0, 0.30)
    clearcoat = VM.detail_grade(clearcoat, 154.0 + float(p["clear_base"]) * 0.06, 238.0, 0.36)

    if finish_id == "cx_hyperflip_electric_blue_copper":
        # Dark navy plate — rebuild M/R/CC from traced structure instead of energy stack.
        vein = np.clip(edge * 0.62 + high * 0.58 + lap * 0.28, 0, 1)
        copper = np.clip(warm * (val * 0.72 + sat * 0.58 + vein * 0.40), 0, 1)
        blue = np.clip(cool * (val * 0.48 + high * 0.52 + vein * 0.24), 0, 1)
        metallic = np.clip(48 + vein * 142 + copper * 96 + blue * 52 + pin * 38, 0, 255)
        clearcoat = np.clip(56 + vein * 118 + copper * 82 + blue * 46 + hot * 42, 16, 255)
        rough = np.clip(118 - vein * 58 - copper * 36 + recess * 32 + blue * 12, 18, 235)

    spec = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    spec[:, :, 0] = metallic.astype(np.uint8)
    spec[:, :, 1] = rough.astype(np.uint8)
    spec[:, :, 2] = clearcoat.astype(np.uint8)
    spec[:, :, 3] = 255
    return Image.fromarray(spec, "RGBA")


def swatch_hex(plate: Image.Image) -> str:
    arr = np.asarray(plate.resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
    weights = np.clip(arr.max(axis=2) - 38.0, 0, 255)
    if float(weights.sum()) < 1.0:
        rgb = arr.mean(axis=(0, 1))
    else:
        rgb = (arr * weights[:, :, None]).sum(axis=(0, 1)) / weights.sum()
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"set": "COLORSHOXX AI Reference", "family": "COLORSHOXX", "finishes": []}

    for card_num, finish_id, name, style in FINISHES:
        src = find_source_image(card_num)
        if src is None:
            print(f"MISSING source for #{card_num} {name}")
            continue
        local_src = SOURCE_DIR / f"{finish_id}_card.png"
        if not local_src.exists() or local_src.stat().st_mtime < src.stat().st_mtime:
            local_src.write_bytes(src.read_bytes())

        plate, crop_y = make_paint_plate(local_src)
        spec = make_spec_plate(plate, card_num, finish_id, name, style)
        tex_path = OUT_DIR / f"{finish_id}.png"
        spec_path = OUT_DIR / f"{finish_id}_spec.png"
        VM.save_png_fast(plate, tex_path)
        VM.save_png_fast(spec, spec_path)
        print(f"OK  {finish_id}: paint + spec -> {tex_path.name}")

        manifest["finishes"].append(
            {
                "id": finish_id,
                "name": name,
                "source": str(local_src),
                "texture": f"assets/reference_textures/colorshoxx/ai_reference_2026_05_27/{finish_id}.png",
                "spec": f"assets/reference_textures/colorshoxx/ai_reference_2026_05_27/{finish_id}_spec.png",
                "crop_y": crop_y,
                "style": style,
                "size": [SIZE, SIZE],
                "swatch": swatch_hex(plate),
            }
        )

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(manifest['finishes'])} finishes to {OUT_DIR}")


if __name__ == "__main__":
    main()
