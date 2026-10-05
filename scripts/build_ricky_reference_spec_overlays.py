"""Build Ricky-authored reference art into 2048 spec overlay assets.

SPB-RATE10 2026-05-27 WWRD reference pass:
owner asked to remove bottom text from ten reference cards, keep their names,
and turn the artwork itself into dynamic M/R/CC spec overlays.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "reference_textures" / "spec_overlays" / "ricky_reference"
SIZE = 2048

SOURCES = [
    {
        "id": "viper_pit_hex",
        "name": "Viper Pit Hex",
        "category": "Predator / Armor",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_17 AM (1).png",
        "metal": 1.05,
        "rough": 0.82,
        "clear": 1.10,
        "chromatic_shift": True,
    },
    {
        "id": "wave_ripple",
        "name": "Wave Ripple",
        "category": "Water / Pearl",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_18 AM (2).png",
        "metal": 0.82,
        "rough": 0.72,
        "clear": 1.18,
        "chromatic_shift": True,
    },
    {
        "id": "samhain_ritual",
        "name": "Samhain Ritual",
        "category": "Occult / Fire",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_19 AM (3).png",
        "metal": 0.92,
        "rough": 0.92,
        "clear": 0.88,
        "chromatic_shift": False,
    },
    {
        "id": "ouija_mystic",
        "name": "Ouija Mystic",
        "category": "Occult / Spirit Board",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_19 AM (4).png",
        "metal": 0.88,
        "rough": 0.86,
        "clear": 0.96,
        "chromatic_shift": True,
    },
    {
        "id": "stardust_fine",
        "name": "Stardust Fine",
        "category": "Cosmic / Sparkle",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_19 AM (5).png",
        "metal": 0.98,
        "rough": 0.70,
        "clear": 1.28,
        "chromatic_shift": True,
    },
    {
        "id": "spec_terrain_erosion",
        "name": "Terrain Erosion",
        "category": "Terrain / Strata",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_20 AM (6).png",
        "metal": 0.64,
        "rough": 1.18,
        "clear": 0.62,
        "chromatic_shift": False,
    },
    {
        "id": "spec_stress_fractures",
        "name": "Stress Fractures",
        "category": "Fracture / Energy",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_21 AM (7).png",
        "metal": 1.10,
        "rough": 0.78,
        "clear": 1.12,
        "chromatic_shift": True,
    },
    {
        "id": "spec_snake_scales",
        "name": "Snake Scales",
        "category": "Predator / Scales",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_21 AM (8).png",
        "metal": 1.00,
        "rough": 0.82,
        "clear": 1.04,
        "chromatic_shift": True,
    },
    {
        "id": "spec_liquid_metal",
        "name": "Liquid Metal",
        "category": "Chrome / Liquid",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_22 AM (9).png",
        "metal": 1.22,
        "rough": 0.48,
        "clear": 1.26,
        "chromatic_shift": True,
    },
    {
        "id": "spec_fresnel_gradient",
        "name": "Fresnel Gradient",
        "category": "Optical / Fresnel",
        "source": r"C:/Users/Ricky's PC/Downloads/ChatGPT Image May 27, 2026, 10_06_23 AM (10).png",
        "metal": 1.18,
        "rough": 0.54,
        "clear": 1.30,
        "chromatic_shift": True,
    },
]


def _find_caption_top(rgb: np.ndarray) -> int:
    h, _w, _c = rgb.shape
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    row_mean = gray.mean(axis=1)
    start = int(h * 0.72)
    for y in range(start, h - 12):
        slab = row_mean[y : min(h, y + 18)]
        if float(slab.mean()) < 0.18 and float(slab.std()) < 0.10:
            return max(1, y - 2)
    return int(h * 0.93)


def _load_clean_texture(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img)
    crop_y = _find_caption_top(arr)
    art = img.crop((0, 0, img.width, crop_y))
    art = ImageOps.fit(art, (SIZE, SIZE), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    return art


def _norm01(a: np.ndarray, pct_low=1.0, pct_high=99.3) -> np.ndarray:
    lo = float(np.percentile(a, pct_low))
    hi = float(np.percentile(a, pct_high))
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0).astype(np.float32)


def _push_std(a: np.ndarray, target_std: float, lo: float, hi: float) -> np.ndarray:
    mean = float(np.mean(a))
    std = float(np.std(a))
    if std < 1e-6:
        return np.clip(a, lo, hi).astype(np.float32)
    gain = min(4.0, max(1.0, float(target_std) / std))
    return np.clip((a - mean) * gain + mean, lo, hi).astype(np.float32)


def _bake_spec(rgb_u8: np.ndarray, meta: dict) -> np.ndarray:
    tex = rgb_u8.astype(np.float32) / 255.0
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.0

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm01(np.sqrt(gx * gx + gy * gy), 0.0, 99.4)
    edge = cv2.GaussianBlur(edge, (0, 0), 0.55)

    small_blur = cv2.GaussianBlur(gray, (0, 0), 1.0)
    big_blur = cv2.GaussianBlur(gray, (0, 0), 9.0)
    detail = _norm01(np.abs(small_blur - big_blur), 2.0, 99.5)
    high = np.clip((gray - 0.48) / 0.48, 0.0, 1.0)
    dark = np.clip((0.34 - gray) / 0.34, 0.0, 1.0)

    metal_gain = float(meta["metal"])
    rough_gain = float(meta["rough"])
    clear_gain = float(meta["clear"])
    chromatic = bool(meta["chromatic_shift"])

    chroma_edge = edge * (0.42 + 0.58 * sat)
    glossy_peak = np.maximum(high, chroma_edge)
    metallic = 0.10 + metal_gain * (0.43 * chroma_edge + 0.28 * high + 0.19 * detail + 0.14 * sat)
    roughness = 0.72 * rough_gain - 0.36 * glossy_peak + 0.28 * dark + 0.20 * detail
    clearcoat = 0.12 + clear_gain * (0.34 * edge + 0.30 * high + 0.26 * sat + 0.16 * detail)

    if "liquid_metal" in meta["id"]:
        metallic = np.maximum(metallic, 0.64 + high * 0.28 + edge * 0.18)
        roughness = np.minimum(roughness, 0.32 - high * 0.15 + dark * 0.12)
        clearcoat = np.maximum(clearcoat, 0.50 + high * 0.34 + edge * 0.20)
    elif "fresnel" in meta["id"]:
        metallic = np.maximum(metallic, 0.48 + edge * 0.38 + sat * 0.22)
        roughness = np.minimum(roughness, 0.44 - high * 0.18 + detail * 0.10)
        clearcoat = np.maximum(clearcoat, 0.42 + edge * 0.34 + sat * 0.22)
    elif "terrain" in meta["id"]:
        metallic = np.minimum(metallic, 0.62)
        roughness = np.maximum(roughness, 0.56 + detail * 0.24 + dark * 0.12)
        clearcoat = np.minimum(clearcoat, 0.50 + edge * 0.15)
    elif "stardust" in meta["id"]:
        spark = _norm01(high * edge, 80.0, 99.98)
        metallic = np.maximum(metallic, 0.30 + spark * 0.66)
        roughness = np.minimum(roughness, 0.62 - spark * 0.44)
        clearcoat = np.maximum(clearcoat, 0.30 + spark * 0.70)
    elif "stress" in meta["id"]:
        energy = np.clip((tex[:, :, 0] - tex[:, :, 1] * 0.78) + (tex[:, :, 2] - tex[:, :, 0] * 0.74), 0.0, 1.0)
        metallic = np.maximum(metallic, 0.25 + energy * 0.62 + edge * 0.28)
        roughness = np.minimum(roughness, 0.62 - energy * 0.34 + dark * 0.22)
        clearcoat = np.maximum(clearcoat, 0.24 + energy * 0.68 + edge * 0.22)

    if chromatic:
        hue_phase = np.sin((hsv[:, :, 0] / 180.0) * np.pi * 2.0)
        metallic = np.clip(metallic + hue_phase * sat * 0.055, 0.0, 1.0)
        clearcoat = np.clip(clearcoat - hue_phase * sat * 0.045, 0.0, 1.0)
        roughness = np.clip(roughness + np.cos((hsv[:, :, 0] / 180.0) * np.pi * 2.0) * sat * 0.045, 0.0, 1.0)

    target = {
        "spec_terrain_erosion": (0.115, 0.165, 0.110),
        "stardust_fine": (0.105, 0.105, 0.120),
        "wave_ripple": (0.095, 0.120, 0.105),
        "ouija_mystic": (0.105, 0.125, 0.105),
        "spec_fresnel_gradient": (0.115, 0.130, 0.115),
    }.get(meta["id"], (0.115, 0.125, 0.115))
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
    return np.round(out * 255.0).astype(np.uint8)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 1,
        "generated_by": "scripts/build_ricky_reference_spec_overlays.py",
        "size": SIZE,
        "finishes": [],
    }

    for meta in SOURCES:
        src = Path(meta["source"])
        if not src.exists():
            raise FileNotFoundError(src)
        clean = _load_clean_texture(src)
        rgb_u8 = np.asarray(clean, dtype=np.uint8)
        spec_u8 = _bake_spec(rgb_u8, meta)

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
                "chromatic_shift": bool(meta["chromatic_shift"]),
                "metal": float(meta["metal"]),
                "rough": float(meta["rough"]),
                "clear": float(meta["clear"]),
                "source_original": str(src),
            }
        )
        print(f"built {meta['id']}: {texture_name}, {spec_name}")

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest: {OUT_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
