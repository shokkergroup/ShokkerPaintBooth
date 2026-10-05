"""Build Ricky's second reference drop into 2048 spec overlay assets.

SPB-RATE10 2026-05-27 reference batch 2.
Owner verdict snippet: "10 more Dangerous Animals and 10 more Voodoo inspired
finishes... cutting off the names and numbers at the bottom and properly
sizing them for the 2048x2048 canvas size. SPEC OVERLAYS of course".
Metric movement is recorded by the generated manifest stats and RATE10
thumbnail pass after these reference-backed overlays are baked.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "reference_textures" / "spec_overlays" / "ricky_reference_batch2"
SIZE = 2048


SOURCES = [
    {
        "id": "king_cobra_coil",
        "name": "King Cobra Coil",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_02 PM (1).png",
        "metal": 1.05,
        "rough": 0.74,
        "clear": 1.12,
        "style": "scale_metal",
        "chromatic_shift": True,
    },
    {
        "id": "widow_web_venom",
        "name": "Widow Web Venom",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (2).png",
        "metal": 1.14,
        "rough": 0.66,
        "clear": 1.20,
        "style": "web_ruby",
        "chromatic_shift": True,
    },
    {
        "id": "tiger_fang_fracture",
        "name": "Tiger Fang Fracture",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (3).png",
        "metal": 1.00,
        "rough": 0.76,
        "clear": 0.98,
        "style": "claw_stripe",
        "chromatic_shift": False,
    },
    {
        "id": "scorpion_ember_hex",
        "name": "Scorpion Ember Hex",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (4).png",
        "metal": 1.08,
        "rough": 0.78,
        "clear": 1.10,
        "style": "ember_armor",
        "chromatic_shift": False,
    },
    {
        "id": "hornet_swarm_static",
        "name": "Hornet Swarm Static",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (5).png",
        "metal": 1.10,
        "rough": 0.62,
        "clear": 1.16,
        "style": "electric_wing",
        "chromatic_shift": True,
    },
    {
        "id": "croc_delta_armor",
        "name": "Croc Delta Armor",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (6).png",
        "metal": 0.78,
        "rough": 1.08,
        "clear": 0.78,
        "style": "mud_armor",
        "chromatic_shift": False,
    },
    {
        "id": "panther_shadow_claw",
        "name": "Panther Shadow Claw",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (7).png",
        "metal": 1.08,
        "rough": 0.68,
        "clear": 1.22,
        "style": "shadow_claw",
        "chromatic_shift": True,
    },
    {
        "id": "piranha_frenzy_current",
        "name": "Piranha Frenzy Current",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_03 PM (8).png",
        "metal": 1.06,
        "rough": 0.70,
        "clear": 1.18,
        "style": "current_teeth",
        "chromatic_shift": True,
    },
    {
        "id": "jellyshock_drift",
        "name": "Jellyshock Drift",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_04 PM (9).png",
        "metal": 0.92,
        "rough": 0.58,
        "clear": 1.32,
        "style": "bioelectric",
        "chromatic_shift": True,
    },
    {
        "id": "sharkbite_riptide",
        "name": "Sharkbite Riptide",
        "category": "Dangerous Animals",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 03_54_04 PM (10).png",
        "metal": 1.16,
        "rough": 0.64,
        "clear": 1.10,
        "style": "salt_teeth",
        "chromatic_shift": True,
    },
    {
        "id": "bayou_hex_burlap",
        "name": "Bayou Hex Burlap",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_13_58 PM (1).png",
        "metal": 0.58,
        "rough": 1.26,
        "clear": 0.58,
        "style": "burlap_moss",
        "chromatic_shift": False,
    },
    {
        "id": "candle_wax_veve",
        "name": "Candle Wax Veve",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_13_58 PM (2).png",
        "metal": 0.76,
        "rough": 0.84,
        "clear": 1.12,
        "style": "wax_veve",
        "chromatic_shift": False,
    },
    {
        "id": "pins_and_thread",
        "name": "Pins & Thread",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_13_58 PM (3).png",
        "metal": 0.92,
        "rough": 0.96,
        "clear": 0.84,
        "style": "thread_pins",
        "chromatic_shift": False,
    },
    {
        "id": "swamp_charm_patina",
        "name": "Swamp Charm Patina",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_13_59 PM (4).png",
        "metal": 0.98,
        "rough": 1.02,
        "clear": 0.78,
        "style": "oxidized_charm",
        "chromatic_shift": True,
    },
    {
        "id": "mojo_bag_grain",
        "name": "Mojo Bag Grain",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_13_59 PM (5).png",
        "metal": 0.70,
        "rough": 1.18,
        "clear": 0.64,
        "style": "leather_grain",
        "chromatic_shift": False,
    },
    {
        "id": "midnight_gris_gris",
        "name": "Midnight Gris-Gris",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_14_00 PM (6).png",
        "metal": 0.92,
        "rough": 0.86,
        "clear": 1.04,
        "style": "crystal_relic",
        "chromatic_shift": True,
    },
    {
        "id": "bayou_smoke_script",
        "name": "Bayou Smoke Script",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_14_00 PM (7).png",
        "metal": 0.82,
        "rough": 0.78,
        "clear": 1.14,
        "style": "smoke_script",
        "chromatic_shift": True,
    },
    {
        "id": "coffin_nail_rust",
        "name": "Coffin Nail Rust",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_14_00 PM (8).png",
        "metal": 0.98,
        "rough": 1.12,
        "clear": 0.66,
        "style": "rust_nail",
        "chromatic_shift": False,
    },
    {
        "id": "root_doctor_copper",
        "name": "Root Doctor Copper",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_14_01 PM (9).png",
        "metal": 1.12,
        "rough": 0.90,
        "clear": 0.92,
        "style": "copper_roots",
        "chromatic_shift": True,
    },
    {
        "id": "spanish_moss_static",
        "name": "Spanish Moss Static",
        "category": "Voodoo Inspired",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 01_14_01 PM (10).png",
        "metal": 0.60,
        "rough": 1.22,
        "clear": 0.76,
        "style": "moss_static",
        "chromatic_shift": False,
    },
    {
        "id": "seigaiha_chrome",
        "name": "Seigaiha Chrome",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (1).png",
        "metal": 1.24,
        "rough": 0.48,
        "clear": 1.30,
        "style": "chrome_wave",
        "chromatic_shift": True,
    },
    {
        "id": "sakura_static",
        "name": "Sakura Static",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (2).png",
        "metal": 0.82,
        "rough": 0.72,
        "clear": 1.26,
        "style": "sakura_gloss",
        "chromatic_shift": True,
    },
    {
        "id": "kintsugi_rift",
        "name": "Kintsugi Rift",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (3).png",
        "metal": 1.22,
        "rough": 0.64,
        "clear": 1.08,
        "style": "gold_rift",
        "chromatic_shift": True,
    },
    {
        "id": "torii_ember_lattice",
        "name": "Torii Ember Lattice",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (4).png",
        "metal": 1.04,
        "rough": 0.78,
        "clear": 1.06,
        "style": "ember_lattice",
        "chromatic_shift": False,
    },
    {
        "id": "oni_veil_mosaic",
        "name": "Oni Veil Mosaic",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (5).png",
        "metal": 0.94,
        "rough": 0.88,
        "clear": 0.96,
        "style": "oni_shadow",
        "chromatic_shift": True,
    },
    {
        "id": "shogun_scale_brocade",
        "name": "Shogun Scale Brocade",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (6).png",
        "metal": 1.08,
        "rough": 0.82,
        "clear": 0.92,
        "style": "samurai_armor",
        "chromatic_shift": False,
    },
    {
        "id": "kyoto_lantern_filigree",
        "name": "Kyoto Lantern Filigree",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_18 PM (7).png",
        "metal": 1.10,
        "rough": 0.70,
        "clear": 1.14,
        "style": "lantern_filigree",
        "chromatic_shift": True,
    },
    {
        "id": "bonsai_drift_circuit",
        "name": "Bonsai Drift Circuit",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_19 PM (8).png",
        "metal": 0.72,
        "rough": 1.06,
        "clear": 0.80,
        "style": "nature_circuit",
        "chromatic_shift": False,
    },
    {
        "id": "fuji_frost_crest",
        "name": "Fuji Frost Crest",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_19 PM (9).png",
        "metal": 0.88,
        "rough": 0.64,
        "clear": 1.32,
        "style": "frost_crest",
        "chromatic_shift": True,
    },
    {
        "id": "rising_sun_prismwave",
        "name": "Rising Sun Prismwave",
        "category": "Rising Sun Spec",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 05_06_19 PM (10).png",
        "metal": 1.12,
        "rough": 0.58,
        "clear": 1.24,
        "style": "sun_prism",
        "chromatic_shift": True,
    },
]


def _find_caption_top(rgb: np.ndarray) -> int:
    h, _w, _c = rgb.shape
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    row_mean = gray.mean(axis=1)
    row_std = gray.std(axis=1)
    edge_y = np.abs(np.diff(row_mean, prepend=row_mean[:1]))
    start = int(h * 0.80)
    candidates: list[int] = []
    for y in range(start, h - 12):
        slab_mean = float(row_mean[y : min(h, y + 18)].mean())
        slab_std = float(row_std[y : min(h, y + 18)].mean())
        if slab_mean < 0.21 and slab_std < 0.13 and float(edge_y[y]) > 0.015:
            candidates.append(y)
    if candidates:
        return max(1, candidates[0] - 2)
    for y in range(start, h - 12):
        slab_mean = float(row_mean[y : min(h, y + 18)].mean())
        slab_std = float(row_std[y : min(h, y + 18)].mean())
        if slab_mean < 0.18 and slab_std < 0.11:
            return max(1, y - 2)
    return int(h * 0.84)


def _load_clean_texture(path: Path) -> tuple[Image.Image, int]:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    crop_y = _find_caption_top(arr)
    art = img.crop((0, 0, img.width, crop_y))
    art = ImageOps.fit(art, (SIZE, SIZE), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return art, crop_y


def _norm01(a: np.ndarray, pct_low=1.0, pct_high=99.3) -> np.ndarray:
    lo = float(np.percentile(a, pct_low))
    hi = float(np.percentile(a, pct_high))
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0).astype(np.float32)


def _push_std(a: np.ndarray, target_std: float, lo: float, hi: float) -> np.ndarray:
    mean = float(np.mean(a))
    std = float(np.std(a))
    if std < 1e-6:
        return np.clip(a, lo, hi).astype(np.float32)
    gain = min(4.8, max(1.0, float(target_std) / std))
    return np.clip((a - mean) * gain + mean, lo, hi).astype(np.float32)


def _style_masks(tex: np.ndarray, gray: np.ndarray, sat: np.ndarray, edge: np.ndarray, detail: np.ndarray, style: str) -> dict[str, np.ndarray]:
    red = tex[:, :, 0]
    green = tex[:, :, 1]
    blue = tex[:, :, 2]
    warm = np.clip(red * 1.10 + green * 0.35 - blue * 0.55, 0.0, 1.0)
    cool = np.clip(blue * 1.08 + green * 0.42 - red * 0.42, 0.0, 1.0)
    yellow = np.clip(red * 0.65 + green * 0.72 - blue * 0.42, 0.0, 1.0)
    violet = np.clip(red * 0.55 + blue * 0.78 - green * 0.34, 0.0, 1.0)
    dark = np.clip((0.38 - gray) / 0.38, 0.0, 1.0)
    bright = np.clip((gray - 0.45) / 0.45, 0.0, 1.0)
    hot = np.maximum(warm, yellow) * (0.55 + 0.45 * sat)
    cold = cool * (0.45 + 0.55 * sat)
    relic = np.maximum(edge, detail) * (0.55 + 0.45 * bright)

    if style in {"ember_armor", "claw_stripe", "ember_lattice", "sun_prism"}:
        accent = np.maximum(hot, edge)
    elif style in {"bioelectric", "electric_wing", "current_teeth", "salt_teeth", "frost_crest", "chrome_wave"}:
        accent = np.maximum(cold, edge)
    elif style in {"web_ruby", "shadow_claw", "crystal_relic", "smoke_script", "oni_shadow"}:
        accent = np.maximum(violet, cold)
    elif style in {"copper_roots", "oxidized_charm", "wax_veve", "gold_rift", "lantern_filigree", "samurai_armor"}:
        accent = np.maximum(warm, yellow)
    elif style in {"burlap_moss", "moss_static", "leather_grain", "rust_nail", "nature_circuit", "sakura_gloss"}:
        accent = np.maximum(detail, edge * 0.65)
    else:
        accent = np.maximum(edge, sat)

    return {
        "warm": warm,
        "cool": cool,
        "yellow": yellow,
        "violet": violet,
        "dark": dark,
        "bright": bright,
        "hot": hot,
        "cold": cold,
        "relic": relic,
        "accent": np.clip(accent, 0.0, 1.0),
    }


def _bake_spec(rgb_u8: np.ndarray, meta: dict) -> tuple[np.ndarray, dict]:
    tex = rgb_u8.astype(np.float32) / 255.0
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.0

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm01(np.sqrt(gx * gx + gy * gy), 0.0, 99.55)
    edge = cv2.GaussianBlur(edge, (0, 0), 0.45)

    small_blur = cv2.GaussianBlur(gray, (0, 0), 0.8)
    big_blur = cv2.GaussianBlur(gray, (0, 0), 7.5)
    detail = _norm01(np.abs(small_blur - big_blur), 2.0, 99.65)
    high = np.clip((gray - 0.46) / 0.46, 0.0, 1.0)
    masks = _style_masks(tex, gray, sat, edge, detail, str(meta["style"]))

    metal_gain = float(meta["metal"])
    rough_gain = float(meta["rough"])
    clear_gain = float(meta["clear"])
    accent = masks["accent"]
    dark = masks["dark"]
    bright = masks["bright"]

    metallic = 0.08 + metal_gain * (0.34 * edge + 0.24 * accent + 0.18 * detail + 0.16 * bright + 0.10 * sat)
    roughness = 0.58 * rough_gain - 0.24 * accent - 0.18 * high + 0.26 * dark + 0.22 * detail
    clearcoat = 0.10 + clear_gain * (0.30 * edge + 0.25 * accent + 0.23 * high + 0.16 * sat + 0.14 * detail)

    style = str(meta["style"])
    if style in {"scale_metal", "mud_armor", "samurai_armor"}:
        metallic = np.maximum(metallic, 0.18 + edge * 0.34 + detail * 0.24)
        roughness = np.maximum(roughness, 0.43 + detail * 0.25 + dark * 0.16)
    elif style in {"shadow_claw", "current_teeth", "salt_teeth", "web_ruby", "gold_rift"}:
        blade = np.maximum(edge, high)
        metallic = np.maximum(metallic, 0.30 + blade * 0.58)
        roughness = np.minimum(roughness, 0.68 - blade * 0.28 + dark * 0.18)
        clearcoat = np.maximum(clearcoat, 0.22 + blade * 0.62)
    elif style in {"bioelectric", "electric_wing", "frost_crest"}:
        energy = np.maximum(masks["cold"], edge * high)
        metallic = np.maximum(metallic, 0.22 + energy * 0.52 + edge * 0.18)
        roughness = np.minimum(roughness, 0.60 - energy * 0.35 + detail * 0.12)
        clearcoat = np.maximum(clearcoat, 0.26 + energy * 0.66 + high * 0.16)
    elif style in {"burlap_moss", "leather_grain", "moss_static", "nature_circuit"}:
        weave = np.maximum(detail, dark * 0.45)
        metallic = np.minimum(metallic, 0.50 + edge * 0.18)
        roughness = np.maximum(roughness, 0.62 + weave * 0.24)
        clearcoat = np.minimum(clearcoat, 0.56 + edge * 0.16)
    elif style in {"copper_roots", "oxidized_charm", "wax_veve", "rust_nail", "lantern_filigree"}:
        relic = masks["relic"]
        metallic = np.maximum(metallic, 0.20 + relic * 0.54 + masks["warm"] * 0.22)
        roughness = np.maximum(roughness, 0.40 + detail * 0.20)
        clearcoat = np.maximum(clearcoat, 0.16 + high * 0.42 + edge * 0.24)
    elif style in {"smoke_script", "crystal_relic", "oni_shadow", "sakura_gloss"}:
        glow = np.maximum(masks["violet"], masks["cold"])
        metallic = np.maximum(metallic, 0.18 + edge * 0.36 + glow * 0.30)
        roughness = np.clip(roughness - glow * 0.18 + dark * 0.10, 0.06, 0.96)
        clearcoat = np.maximum(clearcoat, 0.18 + glow * 0.48 + high * 0.28)
    elif style in {"chrome_wave", "sun_prism"}:
        optics = np.maximum.reduce([edge, high, masks["hot"], masks["cold"]])
        metallic = np.maximum(metallic, 0.42 + optics * 0.48)
        roughness = np.minimum(roughness, 0.52 - optics * 0.30 + detail * 0.12)
        clearcoat = np.maximum(clearcoat, 0.34 + optics * 0.58)

    if bool(meta["chromatic_shift"]):
        hue_phase = np.sin((hsv[:, :, 0] / 180.0) * np.pi * 2.0)
        metallic = np.clip(metallic + hue_phase * sat * 0.055, 0.0, 1.0)
        clearcoat = np.clip(clearcoat - hue_phase * sat * 0.045, 0.0, 1.0)
        roughness = np.clip(roughness + np.cos((hsv[:, :, 0] / 180.0) * np.pi * 2.0) * sat * 0.040, 0.0, 1.0)

    target = {
        "bayou_hex_burlap": (0.100, 0.170, 0.095),
        "mojo_bag_grain": (0.105, 0.165, 0.095),
        "spanish_moss_static": (0.100, 0.160, 0.100),
        "coffin_nail_rust": (0.125, 0.160, 0.100),
        "jellyshock_drift": (0.110, 0.125, 0.135),
        "hornet_swarm_static": (0.130, 0.130, 0.125),
        "panther_shadow_claw": (0.125, 0.130, 0.130),
        "root_doctor_copper": (0.135, 0.140, 0.110),
        "seigaiha_chrome": (0.125, 0.120, 0.135),
        "sakura_static": (0.100, 0.120, 0.120),
        "kintsugi_rift": (0.140, 0.130, 0.120),
        "torii_ember_lattice": (0.130, 0.140, 0.115),
        "oni_veil_mosaic": (0.115, 0.140, 0.110),
        "shogun_scale_brocade": (0.130, 0.140, 0.105),
        "kyoto_lantern_filigree": (0.130, 0.125, 0.120),
        "bonsai_drift_circuit": (0.100, 0.155, 0.100),
        "fuji_frost_crest": (0.110, 0.115, 0.135),
        "rising_sun_prismwave": (0.125, 0.120, 0.135),
    }.get(meta["id"], (0.120, 0.135, 0.115))
    metallic = _push_std(metallic, target[0], 0.03, 0.98)
    roughness = _push_std(roughness, target[1], 0.06, 0.96)
    clearcoat = _push_std(clearcoat, target[2], 0.03, 0.98)

    alpha = np.full_like(metallic, 1.0)
    out = np.stack(
        [
            np.clip(metallic, 0.03, 0.98),
            np.clip(roughness, 0.06, 0.96),
            np.clip(clearcoat, 0.03, 0.98),
            alpha,
        ],
        axis=-1,
    )
    spec_u8 = np.round(out * 255.0).astype(np.uint8)
    stats = {
        "M_std": float(spec_u8[:, :, 0].std()),
        "R_std": float(spec_u8[:, :, 1].std()),
        "CC_std": float(spec_u8[:, :, 2].std()),
        "M_range": [int(spec_u8[:, :, 0].min()), int(spec_u8[:, :, 0].max())],
        "R_range": [int(spec_u8[:, :, 1].min()), int(spec_u8[:, :, 1].max())],
        "CC_range": [int(spec_u8[:, :, 2].min()), int(spec_u8[:, :, 2].max())],
    }
    return spec_u8, stats


def _make_contact_sheet(items: list[dict]) -> None:
    thumb = 256
    pad = 18
    label_h = 44
    cols = 4
    rows = int(np.ceil(len(items) / cols))
    sheet = Image.new("RGB", (cols * (thumb * 2 + pad) + pad, rows * (thumb + label_h + pad) + pad), (12, 12, 14))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, item in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = pad + col * (thumb * 2 + pad)
        y = pad + row * (thumb + label_h + pad)
        tex = Image.open(OUT_DIR / item["texture"]).convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
        spec = Image.open(OUT_DIR / item["spec"]).convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
        sheet.paste(tex, (x, y))
        sheet.paste(spec, (x + thumb, y))
        draw.text((x, y + thumb + 8), item["name"], fill=(232, 232, 232), font=font)
        draw.text((x + thumb, y + thumb + 8), "M/R/CC spec", fill=(180, 210, 255), font=font)
    sheet.save(OUT_DIR / "_contact_sheet.png")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 1,
        "generated_by": "scripts/build_ricky_reference_batch2_spec_overlays.py",
        "size": SIZE,
        "finishes": [],
    }

    for meta in SOURCES:
        src = Path(str(meta["source"]))
        if not src.exists():
            raise FileNotFoundError(src)
        clean, crop_y = _load_clean_texture(src)
        rgb_u8 = np.asarray(clean, dtype=np.uint8)
        spec_u8, stats = _bake_spec(rgb_u8, meta)

        texture_name = f"{meta['id']}.png"
        spec_name = f"{meta['id']}_spec.png"
        clean.save(OUT_DIR / texture_name)
        Image.fromarray(spec_u8, mode="RGBA").save(OUT_DIR / spec_name)

        manifest["finishes"].append(
            {
                "id": meta["id"],
                "name": meta["name"],
                "category": meta["category"],
                "texture": texture_name,
                "spec": spec_name,
                "style": meta["style"],
                "chromatic_shift": bool(meta["chromatic_shift"]),
                "metal": float(meta["metal"]),
                "rough": float(meta["rough"]),
                "clear": float(meta["clear"]),
                "caption_crop_y": int(crop_y),
                "source_original": str(src),
                "stats_2048": stats,
            }
        )
        print(
            f"built {meta['id']}: crop_y={crop_y} "
            f"std=({stats['M_std']:.1f},{stats['R_std']:.1f},{stats['CC_std']:.1f})"
        )

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _make_contact_sheet(manifest["finishes"])
    print(f"manifest: {OUT_DIR / 'manifest.json'}")
    print(f"contact: {OUT_DIR / '_contact_sheet.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
