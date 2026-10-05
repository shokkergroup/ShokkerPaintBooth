#!/usr/bin/env python3
"""Build GRUNGE & FUN cultural monolithics (2048 paint + spectacular spec plates).

Uses the same spec-sculpt stack as Viva Mexico (see VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md
and scripts/build_cultural_viva_mexico.py). Runtime polish is applied via
engine/paint_v2/cultural_grunge_fun.py (_pre/_post_adjust_viva_mexico_spec).

Sources: assets/reference_textures/grunge_fun/*.{jpg,jpeg,png} raw uploads
Outputs:  assets/reference_textures/grunge_fun/{id}.png + {id}_spec.png + manifest.json
"""
from __future__ import annotations

import importlib.util
import json
import re
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def _load_viva_mexico_builder():
    path = ROOT / "scripts" / "build_cultural_viva_mexico.py"
    spec = importlib.util.spec_from_file_location("build_cultural_viva_mexico", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_bcm = _load_viva_mexico_builder()
OUT_DIR = ROOT / "assets" / "reference_textures" / "grunge_fun"
SOURCE_DIR = OUT_DIR
LEGACY_SOURCE_DIR = ROOT / "assets" / "reference_textures" / "grunge_&_fun"
SIZE = _bcm.SIZE
SCRIPT_MTIME = Path(__file__).stat().st_mtime

_ORIG_HIDDEN = _bcm.hidden_cultural_motif
_ORIG_PERSONALITY = _bcm.spec_personality

_GRUNGE_STYLES = (
    "halftone_hex",
    "casino_neon",
    "grunge_scratch",
    "abstract_gradient",
    "punk_checker",
    "worn_rust",
    "disco_glitter",
    "comic_pop",
    "acid_wash",
    "metal_flake",
)


def slug_from_stem(stem: str) -> str:
    text = stem.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "finish"
    if text[0].isdigit():
        text = "x_" + text
    return "gf_" + text[:48]


_STYLE_DISPLAY = {
    "halftone_hex": "Halftone Hex",
    "casino_neon": "Casino Neon",
    "grunge_scratch": "Grunge Scratch",
    "abstract_gradient": "Abstract Gradient",
    "punk_checker": "Punk Checker",
    "worn_rust": "Worn Rust",
    "disco_glitter": "Disco Glitter",
    "comic_pop": "Comic Pop",
    "acid_wash": "Acid Wash",
    "metal_flake": "Metal Flake",
}

_CURATED_CATALOG = {
    "gf_x_1024293_6391": ("Blacktop Neon Rain", "casino_neon", ("neon", "rain", "blacktop", "dots")),
    "gf_x_1024294_6392": ("Electric Green Scanline", "grunge_scratch", ("scanline", "green", "glitch", "digital")),
    "gf_x_1152842_or6ilf0": ("Midnight Blue Mesh", "halftone_hex", ("blue", "mesh", "halftone", "depth")),
    "gf_x_1195794_6247": ("Broken Glass Mosaic", "punk_checker", ("mosaic", "glass", "black-white", "cells")),
    "gf_x_1292": ("Golden Circuit Lace", "disco_glitter", ("gold", "circuit", "lace", "ornate")),
    "gf_x_13845": ("Rainbow Audio Shockwave", "casino_neon", ("rainbow", "wave", "audio", "neon")),
    "gf_x_1434947_595": ("Sunburst Polygon Pop", "comic_pop", ("yellow", "polygon", "sunburst", "pop")),
    "gf_x_16302407_yellow_hexagon_halftone_pattern_backg": ("Hazard Honeycomb Glow", "halftone_hex", ("yellow", "honeycomb", "hex", "halftone")),
    "gf_x_18677": ("Matrix Asphalt Rain", "grunge_scratch", ("matrix", "green", "rain", "asphalt")),
    "gf_x_18914258_casino_2021_11": ("Lucky Dice Blackout", "casino_neon", ("casino", "dice", "cards", "black")),
    "gf_x_19034947_en9y_pjge_210709": ("Gilded Mermaid Scales", "metal_flake", ("scales", "gold", "white", "mermaid")),
    "gf_x_19516529_casino_2021_17": ("Vegas Chip Nightfall", "casino_neon", ("casino", "chips", "dots", "night")),
    "gf_x_20216645_6276400": ("Bronze Maze Circuit", "metal_flake", ("bronze", "maze", "circuit", "geometric")),
    "gf_x_20771417_v6t9_6fpy_210512": ("Blue Koi Scale Pop", "acid_wash", ("blue", "scales", "koi", "pop")),
    "gf_x_2149635369": ("Molten Mustard Marble", "worn_rust", ("marble", "molten", "red", "yellow")),
    "gf_x_22587040_6656535": ("Monochrome Pixel Snow", "grunge_scratch", ("pixel", "snow", "black-white", "static")),
    "gf_x_22587046_6656517": ("Silver Pixel Gravel", "grunge_scratch", ("pixel", "gravel", "silver", "static")),
    "gf_x_2311": ("Cotton Candy Halftone Fade", "acid_wash", ("gradient", "pastel", "halftone", "fade")),
    "gf_x_237560942_1f15d9a7_672f_4b74_9792_9a0daae8fbe2": ("Red Checker Burnout", "punk_checker", ("checker", "red", "burnout", "punk")),
    "gf_x_2425": ("Purple Reptile Circuit", "halftone_hex", ("purple", "scale", "reptile", "circuit")),
    "gf_x_2474": ("Lava Honeycomb Split", "halftone_hex", ("lava", "honeycomb", "yellow", "red")),
    "gf_x_26323837_blue_hexagon_pattern_background": ("Blue Honeycomb Haze", "halftone_hex", ("blue", "honeycomb", "hex", "soft")),
    "gf_x_283511752_c9a714fc_a791_4c92_a2af_e3b8537ecaef": ("Deep Blue Dot Fade", "halftone_hex", ("blue", "dots", "halftone", "fade")),
    "gf_x_29035": ("Torn Poster Static", "grunge_scratch", ("poster", "torn", "orange", "static")),
    "gf_x_30330639_lightabstrback14gradientd": ("Rainbow Hex Tunnel", "halftone_hex", ("rainbow", "hex", "tunnel", "optical")),
    "gf_x_31587230_7837300": ("Warped Arcade Checker", "punk_checker", ("checker", "arcade", "warp", "purple")),
    "gf_x_3521": ("Electric Scribble Storm", "casino_neon", ("electric", "scribble", "storm", "neon")),
    "gf_x_391161788_673b312d_2817_44f1_bfa5_bc51bf8df42d": ("Peach Stone Scuff", "worn_rust", ("peach", "stone", "scuff", "weathered")),
    "gf_x_3946420_524": ("Python Scale Armor", "metal_flake", ("python", "scale", "armor", "brown")),
    "gf_x_4004": ("Solar Mesh Fade", "acid_wash", ("solar", "mesh", "gradient", "green")),
    "gf_x_417665166_62a76dd6_56af_4a68_b801_92f5967beda0": ("Black White Decay Wall", "grunge_scratch", ("decay", "wall", "black-white", "scratch")),
    "gf_x_420841114_17c7c800_04f4_4c25_8844_09134f10d3a7": ("Frosted Vertical Smear", "grunge_scratch", ("frost", "vertical", "smear", "silver")),
    "gf_x_426098859_bfe8ddbc_e982_4a17_b396_d362c3e1e12f": ("Redline Audio Pulse", "casino_neon", ("red", "audio", "pulse", "wave")),
    "gf_x_426203826_fc914006_6101_4668_8c1d_3322a73a9319": ("Rainbow Sonar Sweep", "casino_neon", ("rainbow", "sonar", "wave", "sweep")),
    "gf_x_6090": ("Sunset Mesh Burst", "acid_wash", ("sunset", "mesh", "orange", "red")),
    "gf_x_6113": ("Toxic Green Mesh Fade", "acid_wash", ("green", "toxic", "mesh", "fade")),
    "gf_x_69": ("Blue Digital Drizzle", "grunge_scratch", ("blue", "digital", "drizzle", "rain")),
    "gf_x_819188_26851_nwdlx0": ("Champagne Bubble Grid", "disco_glitter", ("champagne", "bubbles", "grid", "dots")),
    "gf_x_850287_o4yijt0": ("Carnival Dot Burst", "disco_glitter", ("carnival", "dots", "burst", "red")),
    "gf_x_850288_o4yijy0": ("Blue Starburst Marquee", "disco_glitter", ("blue", "starburst", "marquee", "dots")),
    "gf_x_8514125_3910277": ("Magenta Static Weave", "grunge_scratch", ("magenta", "static", "weave", "noise")),
    "gf_x_9121": ("Toxic Diagonal Beam", "acid_wash", ("toxic", "diagonal", "beam", "green")),
    "gf_x_9169": ("Cherry Sunrise Halftone", "acid_wash", ("cherry", "sunrise", "halftone", "orange")),
    "gf_x_9338": ("Purple Blue Dot Mesh", "halftone_hex", ("purple", "blue", "dots", "mesh")),
    "gf_x_946728_oe3t1y0": ("Blacklight Wireframe", "punk_checker", ("blacklight", "wireframe", "grid", "neon")),
    "gf_x_947419_oe46fw0": ("Prism Triangle Confetti", "comic_pop", ("prism", "triangle", "confetti", "rainbow")),
    "gf_x_9819736_12811_1": ("Dry Brush Carbon Scratch", "grunge_scratch", ("scratch", "carbon", "dry-brush", "black-white")),
    "gf_magnific_digital_illustration_a_dark_background_": ("Radiant Dark Matter Burst", "abstract_gradient", ("radiant", "dark", "burst", "halftone")),
}


def title_from_stem(stem: str, style: str, index: int, finish_id: str | None = None) -> str:
    if finish_id in _CURATED_CATALOG:
        return _CURATED_CATALOG[str(finish_id)][0]

    text = stem.replace("-", "_")
    parts = [p for p in text.split("_") if p]
    meaningful: list[str] = []
    for part in parts:
        low = part.lower()
        if len(part) > 10 and part.isdigit():
            continue
        if re.fullmatch(r"[a-f0-9]{8,32}", low):
            continue
        if part.isdigit() and len(part) >= 4:
            continue
        if len(part) <= 2:
            continue
        meaningful.append(part)

    if not meaningful:
        base = _STYLE_DISPLAY.get(style, "Grunge")
        return f"{base} {index:02d}"

    words: list[str] = []
    for w in meaningful:
        if w.isdigit():
            continue
        if len(w) <= 3 and w.isalpha():
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    title = " ".join(words).strip()
    if len(title) < 4:
        base = _STYLE_DISPLAY.get(style, "Grunge")
        return f"{base} {index:02d}"
    return title[:64]


def infer_style(stem: str, index: int) -> str:
    t = stem.lower()
    if any(k in t for k in ("hexagon", "hex", "honeycomb", "grid")):
        return "halftone_hex"
    if any(k in t for k in ("casino", "vegas", "neon", "arcade")):
        return "casino_neon"
    if any(k in t for k in ("grunge", "scratch", "distress", "worn", "rust")):
        return "grunge_scratch"
    if any(k in t for k in ("gradient", "abstract", "light", "back")):
        return "abstract_gradient"
    if any(k in t for k in ("checker", "check", "plaid", "stripe")):
        return "punk_checker"
    if any(k in t for k in ("yellow", "gold", "sun", "daffodil")):
        return "disco_glitter"
    if any(k in t for k in ("comic", "pop", "cartoon", "fun")):
        return "comic_pop"
    if any(k in t for k in ("blue", "aqua", "teal", "cyan")):
        return "acid_wash"
    return _GRUNGE_STYLES[index % len(_GRUNGE_STYLES)]


def curated_style(finish_id: str, stem: str, index: int) -> str:
    if finish_id in _CURATED_CATALOG:
        return _CURATED_CATALOG[finish_id][1]
    return infer_style(stem, index)


def tags_for_finish(finish_id: str, style: str) -> list[str]:
    base = ["grunge", "fun", "dynamic-spec", style.replace("_", "-")]
    if finish_id in _CURATED_CATALOG:
        base.extend(_CURATED_CATALOG[finish_id][2])
    seen: set[str] = set()
    return [tag for tag in base if not (tag in seen or seen.add(tag))]


def desc_for_finish(name: str, finish_id: str, style: str) -> str:
    tags = tags_for_finish(finish_id, style)
    human_tags = ", ".join(f"#{tag}" for tag in tags)
    return (
        f"{name} is a Grunge & Fun image-authored lacquer with a matched dynamic "
        f"M/R/Cc spec map that follows the artwork's pattern edges, dots, scratches, "
        f"and gradients. Search tags: {human_tags}."
    )


def source_files() -> list[Path]:
    files = sorted(
        p
        for p in SOURCE_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and not p.stem.lower().startswith("gf_")
    )
    if files:
        return files
    if LEGACY_SOURCE_DIR.exists():
        return sorted(
            p
            for p in LEGACY_SOURCE_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
    return []


def grunge_hidden_motif(name, style, index, hue, sat, val, edge, broad):
    """Spec-only grunge motifs — halftone cells, worn streaks, casino sparkle."""
    text = f"{name} {style}".lower()
    shape = val.shape
    x, y = _bcm.xy(shape)
    phase = index * 0.041

    if any(k in text for k in ("hexagon", "halftone", "hex", "grid", "pattern")):
        cell = _bcm.ridge(x, 118.0 + index % 17, phase, 46.0) * _bcm.ridge(y, 104.0 + index % 13, phase * 1.2, 44.0)
        dots = _bcm.micro_mosaic(shape, 40100 + index * 149, 4 + index % 3, 0.972)
        motif = np.clip(cell * 0.48 + dots * 0.42 + edge * 0.34, 0, 1)
        polish = np.clip(dots * 0.36 + cell * 0.22, 0, 1)
        satin = np.clip(cell * 0.38 + broad * 0.28, 0, 1)
        return motif.astype(np.float32), polish.astype(np.float32), satin.astype(np.float32)

    if any(k in text for k in ("casino", "neon", "arcade", "glitter", "disco")):
        scan = _bcm.ridge(x * 1.4 - y * 0.6, 128.0 + index % 23, phase * 1.6, 48.0)
        spark = _bcm.spark(shape, 41100 + index * 151, 0.992, 0.22)
        motif = np.clip(scan * 0.52 + spark * 0.44 + edge * 0.28, 0, 1)
        polish = np.clip(scan * 0.40 + spark * 0.32, 0, 1)
        satin = np.clip(broad * 0.30, 0, 1)
        return motif.astype(np.float32), polish.astype(np.float32), satin.astype(np.float32)

    if any(k in text for k in ("grunge", "scratch", "rust", "worn", "distress")):
        scratch = _bcm.ridge(x * 0.9 + y * 1.1 + broad * 0.2, 96.0 + index % 19, phase, 40.0)
        grit = _bcm.micro_mosaic(shape, 42100 + index * 157, 5 + index % 4, 0.978)
        motif = np.clip(scratch * 0.46 + grit * 0.48 + (1.0 - val) * 0.18, 0, 1)
        polish = np.clip(scratch * 0.28 + grit * 0.22, 0, 1)
        satin = np.clip((1.0 - val) * 0.42 + broad * 0.30, 0, 1)
        return motif.astype(np.float32), polish.astype(np.float32), satin.astype(np.float32)

    return _ORIG_HIDDEN(name, style, index, hue, sat, val, edge, broad)


def grunge_spec_personality(name: str, style: str) -> dict:
    text = f"{name} {style}".lower()
    p = dict(_ORIG_PERSONALITY(name, style))
    if any(k in text for k in ("hexagon", "halftone", "pattern", "grid")):
        p.update(kind="tile", metal_base=40.0, rough_base=82.0, clear_base=72.0, flake=1.15, line=1.38)
    if any(k in text for k in ("casino", "neon", "arcade", "glitter")):
        p.update(kind="neon", metal_base=68.0, rough_base=54.0, clear_base=74.0, flake=1.32, line=1.30)
    if any(k in text for k in ("grunge", "scratch", "rust", "worn")):
        p.update(kind="muertos", metal_base=50.0, rough_base=118.0, clear_base=42.0, flake=1.08, line=1.40)
    if any(k in text for k in ("gradient", "abstract", "light")):
        p.update(kind="water", metal_base=32.0, rough_base=70.0, clear_base=78.0, flake=0.95, line=1.12)
    return p


def make_paint_plate(src: Path) -> tuple[Image.Image, int]:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    cropped = img.crop((left, top, left + side, top + side))
    plate = cropped.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    plate = ImageEnhance.Color(plate).enhance(1.12)
    plate = ImageEnhance.Contrast(plate).enhance(1.14)
    plate = ImageEnhance.Sharpness(plate).enhance(1.22)
    plate = plate.filter(ImageFilter.UnsharpMask(radius=1.1, percent=82, threshold=2))
    return plate, top


def outputs_current(src: Path, *outputs: Path) -> bool:
    if not all(path.exists() for path in outputs):
        return False
    newest_input = max(src.stat().st_mtime, SCRIPT_MTIME)
    return min(path.stat().st_mtime for path in outputs) >= newest_input


def main() -> None:
    _bcm.hidden_cultural_motif = grunge_hidden_motif
    _bcm.spec_personality = grunge_spec_personality
    try:
        files = source_files()
        if not files:
            raise RuntimeError(f"No source images in {SOURCE_DIR}")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        finishes = []
        rebuilt = 0
        reused = 0
        for index, src in enumerate(files, start=1):
            stem = src.stem
            finish_id = slug_from_stem(stem)
            style = curated_style(finish_id, stem, index)
            name = title_from_stem(stem, style, index, finish_id)
            texture_path = OUT_DIR / f"{finish_id}.png"
            spec_path = OUT_DIR / f"{finish_id}_spec.png"
            t0 = time.perf_counter()
            if outputs_current(src, texture_path, spec_path):
                plate = Image.open(texture_path).convert("RGB")
                reused += 1
                action = "reused"
            else:
                plate, crop_y = make_paint_plate(src)
                spec = _bcm.make_spec_plate(plate, index, name, style)
                _bcm.save_png_fast(plate, texture_path)
                _bcm.save_png_fast(spec, spec_path)
                rebuilt += 1
                action = "rebuilt"
            rel = f"assets/reference_textures/grunge_fun/{finish_id}"
            finishes.append(
                {
                    "id": finish_id,
                    "name": name,
                    "source": str(src.relative_to(ROOT)).replace("\\", "/"),
                    "texture": f"{rel}.png",
                    "spec": f"{rel}_spec.png",
                    "desc": desc_for_finish(name, finish_id, style),
                    "tags": tags_for_finish(finish_id, style),
                    "crop_y": 0,
                    "style": style,
                    "size": [SIZE, SIZE],
                    "swatch": _bcm.swatch_hex(plate),
                }
            )
            print(f"{index:02d}/{len(files)} {action} {finish_id} {time.perf_counter() - t0:.2f}s")
        manifest = {
            "set": "GRUNGE & FUN",
            "family": "Material World",
            "pipeline": "viva_mexico_spec_masterclass",
            "size": [SIZE, SIZE],
            "finishes": finishes,
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            f"generated={len(finishes)} rebuilt={rebuilt} reused={reused} "
            f"elapsed={time.perf_counter() - started:.2f}s out={OUT_DIR}"
        )
    finally:
        _bcm.hidden_cultural_motif = _ORIG_HIDDEN
        _bcm.spec_personality = _ORIG_PERSONALITY


if __name__ == "__main__":
    main()
