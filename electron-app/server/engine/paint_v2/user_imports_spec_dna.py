"""Import DNA — analyze uploaded art and bake Viva-grade spec plates.

SPB-USER-IMPORTS: Owner mandate — one AI/user PNG in → spec that sells the demo.
Routes image statistics to Grunge & Fun / Viva Mexico personalities (not generic abstract).
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter

from engine.paint_v2.user_imports_paths import CANVAS_SIZE

GAUNTLET_MIN_STD = 20.0
GAUNTLET_MIN_RANGE = 150.0
MAX_GAUNTLET_PASSES = 5

from engine.paint_v2.import_dna_style_catalog import (
    DNA_STYLES,
    DNA_STYLE_DESCRIPTIONS,
    SPEC_INKS,
    STYLE_PERSONALITY,
    STYLE_SPEC_PALETTE,
    is_exotic_style,
    spec_palette_weights,
)

_STYLES = DNA_STYLES


def dna_style_label(style_id: str) -> str:
    return style_id.replace("_", " ").title()


def get_dna_style_catalog() -> list[dict]:
    from engine.paint_v2.dna_style_swatches import dna_style_thumb_url

    return [
        {
            "id": style_id,
            "label": dna_style_label(style_id),
            "description": DNA_STYLE_DESCRIPTIONS.get(style_id, ""),
            "thumb_url": dna_style_thumb_url(style_id),
            "palette": list(STYLE_SPEC_PALETTE.get(style_id, [])),
        }
        for style_id in _STYLES
    ]


def get_spec_ink_swatches() -> dict:
    """name -> [R,G,B] for the spec-palette editor (spec channels view as RGB)."""
    return {name: list(rgb) for name, rgb in SPEC_INKS.items()}

_PASS_BOOST = (
    {"flake": 1.0, "line": 1.0, "metal_delta": 0, "rough_delta": 0, "clear_delta": 0},
    {"flake": 1.12, "line": 1.15, "metal_delta": 6, "rough_delta": -8, "clear_delta": 4},
    {"flake": 1.22, "line": 1.28, "metal_delta": 12, "rough_delta": -14, "clear_delta": 8},
    {"flake": 1.30, "line": 1.38, "metal_delta": 18, "rough_delta": -18, "clear_delta": 12},
    {"flake": 1.38, "line": 1.45, "metal_delta": 22, "rough_delta": -22, "clear_delta": 16},
)


@dataclass
class ImageAnalysis:
    style: str
    intent: str
    edge_density: float
    saturation: float
    dark_fraction: float
    bright_fraction: float
    alpha_coverage: float
    photo_like: bool
    material_hint: str
    confidence: float


@dataclass
class DnaBakeResult:
    spec: Image.Image
    analysis: ImageAnalysis
    gauntlet_passes: int
    gauntlet_stats: Dict[str, float]
    gauntlet_passed: bool
    vibe_ref: Optional[str] = None


def _load_viva_builder():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "build_cultural_viva_mexico.py"
    spec = importlib.util.spec_from_file_location("build_cultural_viva_mexico", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load spec builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_grunge_hooks():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "build_cultural_grunge_fun.py"
    spec = importlib.util.spec_from_file_location("build_cultural_grunge_fun", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load grunge builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _downsample_rgb(img: Image.Image, size: int = 512) -> np.ndarray:
    s = img.convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(s, dtype=np.float32) / 255.0


def _edge_density(gray: np.ndarray) -> float:
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return float(gx + gy)


def _high_freq_energy(gray: np.ndarray) -> float:
    """Proxy for halftone / fine cell content."""
    small = gray[::2, ::2]
    lap = np.abs(
        -4 * small[1:-1, 1:-1]
        + small[:-2, 1:-1]
        + small[2:, 1:-1]
        + small[1:-1, :-2]
        + small[1:-1, 2:]
    ).mean()
    return float(lap)


def _directional_anisotropy(gray: np.ndarray) -> float:
    """Brushed metal / directional grain proxy."""
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return float(abs(gx - gy) / (gx + gy + 1e-6))


def _carbon_weave_score(gray: np.ndarray) -> float:
    """Regular micro-grid + low saturation typical of carbon fiber photos."""
    hf = _high_freq_energy(gray)
    # Autocorrelation-ish: checker energy on subsampled grid
    s = gray[::4, ::4]
    check = np.abs(s - s[::-1, :]).mean() + np.abs(s - s[:, ::-1]).mean()
    return float(hf * 1.4 + check * 0.8)


def detect_material_from_pixels(rgb: np.ndarray, gray: np.ndarray) -> Tuple[str, float]:
    """Return (material_hint, confidence) from image statistics."""
    edge = _edge_density(gray)
    sat = float(rgb.std(axis=2).mean())
    dark = float((gray < 0.14).mean())
    bright = float((gray > 0.86).mean())
    hf = _high_freq_energy(gray)
    aniso = _directional_anisotropy(gray)
    carbon = _carbon_weave_score(gray)

    # Carbon fiber weave — fine regular grid, usually dark/desaturated
    if carbon > 0.12 and sat < 0.16 and dark > 0.2:
        return "carbon", min(0.92, 0.65 + carbon)

    # Brushed aluminum / directional metal
    if aniso > 0.28 and sat < 0.18 and edge > 0.06:
        return "brushed_metal", min(0.88, 0.55 + aniso)

    # Chrome / mirror / holo — bright peaks + color variance
    ch_var = float(rgb.std(axis=(0, 1)).mean())
    if bright > 0.12 and ch_var > 0.14 and sat > 0.12:
        return "chrome_holo", min(0.90, 0.5 + bright + ch_var * 0.5)

    # Leather / organic — warm midtones, moderate texture, not halftone
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    warm = float(((r > g) & (g >= b * 0.85)).mean())
    if warm > 0.35 and 0.08 < edge < 0.14 and hf < 0.05 and sat < 0.20:
        return "leather", min(0.84, 0.5 + warm)

    # Worn rust / distress
    if dark > 0.32 and edge > 0.11 and sat > 0.08:
        return "worn", min(0.82, dark + edge)

    return "generic", 0.0


_MATERIAL_STYLE = {
    "carbon": "metal_flake",
    "brushed_metal": "metal_flake",
    "chrome_holo": "disco_glitter",
    "leather": "worn_rust",
    "worn": "worn_rust",
}

_MATERIAL_PERSONALITY = {
    "carbon": {"kind": "tile", "metal_base": 62.0, "rough_base": 95.0, "clear_base": 48.0, "flake": 1.28, "line": 1.35},
    "brushed_metal": {"kind": "water", "metal_base": 78.0, "rough_base": 72.0, "clear_base": 58.0, "flake": 1.18, "line": 1.42},
    "chrome_holo": {"kind": "neon", "metal_base": 88.0, "rough_base": 38.0, "clear_base": 82.0, "flake": 1.45, "line": 1.38},
    "leather": {"kind": "muertos", "metal_base": 28.0, "rough_base": 128.0, "clear_base": 22.0, "flake": 0.95, "line": 1.22},
    "worn": {"kind": "muertos", "metal_base": 44.0, "rough_base": 132.0, "clear_base": 28.0, "flake": 1.05, "line": 1.40},
}

# SPB-109: Viva semantic_masks / grunge_hidden_motif keyword-match English title tokens,
# not DNA style ids — most styles fell through to the same default branch.
_KIND_ROUTE_BOOST: Dict[str, str] = {
    "sun": "sunburst marigold gold flash dawn solar",
    "muertos": "muertos calavera shadow rust worn grunge scratch distress battle",
    "tile": "talavera tile mosaic halftone hex grid pattern carbon weave",
    "glyph": "aztec pyramid thunder jaguar quetzal circuit tribal chrome scale",
    "water": "cenote aqua water blue river pearl aurora oil slick flow",
    "neon": "neon fiesta carnival spark casino glitter disco electric plasma laser",
    "woven": "serape woven beadwork mesh denim argyle",
    "organic": "agave nopal verde moss volcanic obsidian patina frost",
    "festival": "fiesta spark carnival candy clear holo",
}


def _style_route_text(style: str) -> str:
    prof = STYLE_PERSONALITY.get(style, {})
    kind = str(prof.get("kind", "festival"))
    spoken = style.replace("_", " ")
    boost = _KIND_ROUTE_BOOST.get(kind, "fiesta spark")
    return f"{spoken} {style} {boost}"


def _style_plate_index(style: str, plate_index: int) -> int:
    return int(plate_index) + (sum(ord(c) for c in style) % 97) + 1


def _wrap_viva_routers(bcm, grunge):
    orig_semantic = bcm.semantic_masks
    orig_hidden = grunge.grunge_hidden_motif
    orig_grunge_hidden = bcm.hidden_cultural_motif

    def _semantic(name, style, index, hue, sat, val, luma, edge, lap, broad):
        route = _style_route_text(style)
        idx = _style_plate_index(style, index)
        return orig_semantic(route, style, idx, hue, sat, val, luma, edge, lap, broad)

    def _hidden(name, style, index, hue, sat, val, edge, broad):
        route = _style_route_text(style)
        idx = _style_plate_index(style, index)
        return orig_hidden(route, style, idx, hue, sat, val, edge, broad)

    bcm.semantic_masks = _semantic
    bcm.hidden_cultural_motif = _hidden
    return orig_semantic, orig_hidden, orig_grunge_hidden


def _apply_material_personality(personality: dict, material_hint: str) -> dict:
    override = _MATERIAL_PERSONALITY.get(material_hint)
    if not override:
        return personality
    p = dict(personality)
    p.update(override)
    return p


def classify_style_from_image(img: Image.Image, name: str = "") -> Tuple[str, ImageAnalysis]:
    rgb = _downsample_rgb(img)
    gray = rgb.mean(axis=2)
    edge = _edge_density(gray)
    sat = float(rgb.std(axis=2).mean())
    dark = float((gray < 0.14).mean())
    bright = float((gray > 0.86).mean())
    hf = _high_freq_energy(gray)
    alpha_cov = 1.0
    if img.mode == "RGBA":
        a = np.asarray(img.convert("RGBA").resize((512, 512)).split()[3], dtype=np.float32) / 255.0
        alpha_cov = float((a > 0.08).mean())

    photo_like = sat > 0.11 and edge < 0.11 and dark < 0.5
    material_hint, mat_conf = detect_material_from_pixels(rgb, gray)
    style = "abstract_gradient"
    confidence = 0.55

    name_l = (name or "").lower()
    if mat_conf >= 0.72:
        style = _MATERIAL_STYLE.get(material_hint, style)
        confidence = mat_conf
    elif any(k in name_l for k in ("carbon", "fiber", "weave")):
        style, material_hint, confidence = "metal_flake", "carbon", 0.85
    elif any(k in name_l for k in ("chrome", "mirror", "holo")):
        style, material_hint, confidence = "disco_glitter", "metal", 0.82
    elif any(k in name_l for k in ("rust", "worn", "scratch")):
        style, material_hint, confidence = "worn_rust", "worn", 0.80
    elif hf > 0.045 and sat < 0.22:
        style, material_hint, confidence = "halftone_hex", "halftone", 0.78
    elif edge > 0.13 and dark > 0.28:
        style, material_hint, confidence = "grunge_scratch", "distress", 0.80
    elif sat > 0.22 and (bright > 0.08 or edge > 0.09):
        style, material_hint, confidence = "casino_neon", "neon", 0.76
    elif photo_like:
        style, material_hint, confidence = "abstract_gradient", "photo", 0.70
    elif hf > 0.035:
        style, material_hint, confidence = "punk_checker", "geometric", 0.65
    elif sat > 0.18:
        style, material_hint, confidence = "acid_wash", "color", 0.62
    elif edge > 0.08:
        style, material_hint, confidence = "comic_pop", "graphic", 0.60
    elif material_hint == "generic" and mat_conf > 0.5:
        style = _MATERIAL_STYLE.get(material_hint, style)
        confidence = max(confidence, mat_conf)

    intent = suggest_import_intent(img, alpha_cov, edge, dark)
    analysis = ImageAnalysis(
        style=style,
        intent=intent,
        edge_density=edge,
        saturation=sat,
        dark_fraction=dark,
        bright_fraction=bright,
        alpha_coverage=alpha_cov,
        photo_like=photo_like,
        material_hint=material_hint,
        confidence=confidence,
    )
    return style, analysis


def suggest_import_intent(
    img: Image.Image,
    alpha_coverage: Optional[float] = None,
    edge: Optional[float] = None,
    dark: Optional[float] = None,
) -> str:
    if img.mode == "RGBA":
        if alpha_coverage is None:
            a = np.asarray(img.split()[3], dtype=np.float32) / 255.0
            alpha_coverage = float((a > 0.08).mean())
        if alpha_coverage < 0.62:
            return "pattern"
    rgb = _downsample_rgb(img)
    gray = rgb.mean(axis=2)
    if edge is None:
        edge = _edge_density(gray)
    if dark is None:
        dark = float((gray < 0.14).mean())
    if edge > 0.15 and float(gray.std()) < 0.14:
        return "spec_overlay"
    return "paint_monolithic"


def content_aware_square(img: Image.Image, void_rgb: Tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    """Crop to content bbox then pad to square (2048 target applied later)."""
    working = img.convert("RGBA") if img.mode == "RGBA" else img.convert("RGB")
    if working.mode == "RGBA":
        alpha = np.asarray(working.split()[3])
        coords = np.argwhere(alpha > 20)
        if coords.size > 64:
            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0) + 1
            working = working.crop((x0, y0, x1, y1))
    else:
        arr = np.asarray(working, dtype=np.float32) / 255.0
        gray = arr.mean(axis=2)
        mask = gray > 0.04
        if mask.sum() > 64:
            ys, xs = np.where(mask)
            working = working.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    w, h = working.size
    side = max(w, h)
    canvas = Image.new("RGBA" if working.mode == "RGBA" else "RGB", (side, side), (*void_rgb, 0) if working.mode == "RGBA" else void_rgb)
    ox = (side - w) // 2
    oy = (side - h) // 2
    canvas.paste(working, (ox, oy))
    return canvas


def spec_channel_stats(spec: Image.Image) -> Dict[str, float]:
    arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    out: Dict[str, float] = {}
    for i, ch in enumerate(("M", "R", "C")):
        band = arr[:, :, i]
        out[f"{ch}_std"] = float(band.std())
        out[f"{ch}_range"] = float(band.max() - band.min())
    out["passed"] = float(
        all(out[f"{c}_std"] >= GAUNTLET_MIN_STD for c in ("M", "R", "C"))
        and all(out[f"{c}_range"] >= GAUNTLET_MIN_RANGE for c in ("M", "R", "C"))
    )
    return out


def _reference_spec_profile(vibe_ref: str) -> Optional[Dict[str, float]]:
    """Load mean/std per M/R/C from a shipped cultural spec plate if available."""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "assets" / "reference_textures" / "grunge_fun" / f"{vibe_ref}_spec.png",
        root / "assets" / "reference_textures" / "cultural" / "viva_mexico" / f"{vibe_ref}_spec.png",
        root / "assets" / "reference_textures" / "cultural" / "rising_sun" / f"{vibe_ref}_spec.png",
        root / "assets" / "reference_textures" / "cultural" / "union_jacked" / f"{vibe_ref}_spec.png",
    ]
    for path in candidates:
        if not path.exists():
            continue
        arr = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)
        return {
            f"{c}_mean": float(arr[:, :, i].mean())
            for i, c in enumerate(("M", "R", "C"))
        } | {
            f"{c}_std": float(arr[:, :, i].std())
            for i, c in enumerate(("M", "R", "C"))
        }
    return None


def _apply_vibe_to_personality(personality: dict, vibe_ref: str) -> dict:
    prof = _reference_spec_profile(vibe_ref)
    if not prof:
        return personality
    p = dict(personality)
    # Nudge bake personality toward reference spec statistics.
    if prof.get("M_std", 0) > 35:
        p["metal_base"] = float(p.get("metal_base", 50)) + 8
        p["flake"] = float(p.get("flake", 1.0)) * 1.08
    if prof.get("R_std", 0) > 35:
        p["rough_base"] = float(p.get("rough_base", 80)) + 6
    if prof.get("C_std", 0) > 25:
        p["clear_base"] = float(p.get("clear_base", 60)) + 10
        p["line"] = float(p.get("line", 1.0)) * 1.12
    return p


# ── SPB-109 spec chroma engine (owner mandate 2026-05-28) ────────────────────
# Wide color gamut IN the spec map. The old amp ramped M & CC up together (R
# inverse) so every finish collapsed to magenta/green. These passes drive the
# three channels from INDEPENDENT palette inks, so one plate spans
# red->orange->yellow->green->cyan->blue->violet with hundreds of per-feature
# shades. Fully vectorized (no per-cell Python loop) -> faster than the old amp,
# stays inside the 2-3s render budget.

def _stretch01(x: np.ndarray, lo_p: float = 2.0, hi_p: float = 98.0) -> np.ndarray:
    lo = float(np.percentile(x, lo_p))
    hi = float(np.percentile(x, hi_p))
    if hi - lo < 1e-4:
        return np.clip(x, 0.0, 1.0)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def _cell_field01(h: int, w: int, cell: int, seed: int, *, smooth: bool = False) -> np.ndarray:
    """Random scalar field with ~`cell` px features, upscaled to (h,w) in [0,1]."""
    gh, gw = max(1, h // max(1, cell)), max(1, w // max(1, cell))
    rng = np.random.default_rng(seed & 0x7FFFFFFF)
    grid = rng.random((gh, gw), dtype=np.float32)
    interp = Image.Resampling.BILINEAR if smooth else Image.Resampling.NEAREST
    return np.asarray(
        Image.fromarray((grid * 255).astype(np.uint8), "L").resize((w, h), interp),
        dtype=np.float32,
    ) / 255.0


def _ink_color_field(
    h: int,
    w: int,
    inks: np.ndarray,
    weights: np.ndarray,
    cell: int,
    seed: int,
    *,
    smooth: bool = False,
    bright: Tuple[float, float] = (0.62, 1.26),
) -> np.ndarray:
    """(h,w,3) field of palette inks at ~`cell` px, with per-cell shade jitter."""
    gh, gw = max(1, h // max(1, cell)), max(1, w // max(1, cell))
    rng = np.random.default_rng(seed & 0x7FFFFFFF)
    idx = rng.choice(len(inks), size=(gh, gw), p=weights)
    cells = inks[idx].astype(np.float32)
    jit = rng.uniform(bright[0], bright[1], size=(gh, gw, 1)).astype(np.float32)
    cells = cells * jit
    # small per-channel decorrelated jitter -> no two cells share an exact shade
    cells = cells + rng.uniform(-16, 16, size=(gh, gw, 3)).astype(np.float32)
    cells = np.clip(cells, 0, 255).astype(np.uint8)
    interp = Image.Resampling.BILINEAR if smooth else Image.Resampling.NEAREST
    return np.asarray(
        Image.fromarray(cells, "RGB").resize((w, h), interp),
        dtype=np.float32,
    )


_DEFAULT_INK_NAMES = ["red", "orange", "yellow", "green", "cyan", "blue", "violet", "magenta"]


def _palette_arrays(styles, overrides=None):
    """Build (inks, weights) for one style or a union of styles (INSANE quads).

    `overrides` (optional) maps style_id -> list of ink names, letting the user
    retune a style's spec gamut from the picker (SPB-109 color steering).
    """
    if isinstance(styles, str):
        styles = [styles]
    names: list = []
    for s in styles:
        ov = overrides.get(s) if isinstance(overrides, dict) else None
        names.extend(list(ov) if ov else (STYLE_SPEC_PALETTE.get(s, []) or []))
    seen: set = set()
    uniq = [n for n in names if n in SPEC_INKS and not (n in seen or seen.add(n))]
    if not uniq:
        uniq = list(_DEFAULT_INK_NAMES)
    inks = np.asarray([SPEC_INKS[n] for n in uniq], dtype=np.float32)
    weights = np.asarray(spec_palette_weights(len(inks)), dtype=np.float64)
    weights = weights / weights.sum()
    return inks, weights


def spec_chroma_spread(
    spec: Image.Image,
    style: str,
    *,
    paint: Optional[Image.Image] = None,
    seed: int = 88001,
    intensity: float = 0.6,
    mix_styles=None,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> Image.Image:
    """Inject a decorrelated, full-spectrum palette that TRACES the design.

    SPB-109 (2026-05-29): color placement is keyed to the uploaded paint, not
    random noise. Palette inks are chosen per-pixel from the paint's luminance +
    hue, so color regions snap to the artwork's graphics/edges; brightness is
    shaded by the baked spec structure (which already follows the design); and
    bright flecks cluster on the paint's edges. This keeps the wide color gamut
    while restoring the smart edge-tracing the old pipeline had.

    `chroma_scale` is the user Wildness dial (subtle<1<insane); `palette_overrides`
    lets the picker retune a style's spec gamut.
    """
    intensity = float(np.clip(intensity * float(chroma_scale), 0.0, 1.6))
    arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    h, w = arr.shape[:2]
    base = arr[:, :, :3]
    inks, weights = _palette_arrays(mix_styles or style, palette_overrides)
    k = len(inks)
    short = max(h, w)

    # Baked-plate structure (Viva + edge_lock already traced the design into here).
    lum = (0.42 * base[:, :, 0] + 0.22 * base[:, :, 1] + 0.36 * base[:, :, 2]) / 255.0
    lum_n = _stretch01(lum)

    if paint is not None:
        import cv2

        paint_rgb = np.asarray(
            paint.convert("RGB").resize((w, h), Image.Resampling.LANCZOS),
            dtype=np.float32,
        ) / 255.0
        pl = (
            0.299 * paint_rgb[:, :, 0]
            + 0.587 * paint_rgb[:, :, 1]
            + 0.114 * paint_rgb[:, :, 2]
        )
        bgr = (paint_rgb[:, :, ::-1] * 255).astype(np.uint8)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        hue = hsv[:, :, 0] / 179.0
        sat = hsv[:, :, 1] / 255.0
        from engine.paint_v2.cultural_viva_mexico import _viva_mexico_paint_luma_edge

        _, edge_n = _viva_mexico_paint_luma_edge(paint_rgb, np.ones((h, w), dtype=np.float32))
        # Slow drift lets big flat panels still get gentle color movement without
        # crossing a design boundary (boundaries come from sharp pl/hue).
        drift = _cell_field01(h, w, max(64, short // 12), seed ^ 0xD1F7, smooth=True)
        # Fine structure nudges the ink index WITHIN a region so each design area
        # shows several related shades (not one flat ink) — still tracing, because
        # the region border still comes from sharp pl/hue.
        micro = _cell_field01(h, w, max(6, short // 240), seed ^ 0xB1A5)
        # Design-driven zone key -> palette index. Sat-gated hue so gray areas key
        # off luminance. Sharp pl/hue make zone borders land on the artwork.
        key = np.clip(0.50 * pl + 0.30 * (hue * sat) + 0.10 * sat + 0.16 * drift, 0.0, 1.0)
        key = np.clip(key + (lum_n - 0.5) * 0.10 + (micro - 0.5) * 0.06, 0.0, 1.0)
        idx = np.clip((key * k).astype(np.int32), 0, k - 1)
        zone = inks[idx].astype(np.float32)
        tone = pl
        edge_strong = np.clip(edge_n * 2.0, 0.0, 1.0)
    else:
        edge_n = np.zeros((h, w), dtype=np.float32)
        edge_strong = np.zeros((h, w), dtype=np.float32)
        tone = lum_n
        zone = _ink_color_field(
            h, w, inks, weights, max(40, short // 22), seed ^ 0x1110, smooth=True, bright=(0.84, 1.08)
        )

    # Shade the zone color by the baked structure so flakes/lines/graphics show.
    shade = (0.5 + 0.72 * lum_n)[:, :, None]
    target = np.clip(zone * shade, 0, 255)

    # Tonal depth keyed to the design: deepen dark graphics into rich shadow shades
    # and lift bright graphics (numbers/logos/whites) into bright highlights. Adds
    # many shades + wide channel range (owner spec-driven bar) and traces the art.
    shadow = np.clip((0.42 - tone) / 0.42, 0.0, 1.0)[:, :, None]
    target = target * (1.0 - 0.5 * shadow)
    hi = np.clip((tone - 0.72) / 0.28, 0.0, 1.0)[:, :, None]
    target = target * (1.0 - 0.55 * hi) + np.array([232.0, 232.0, 240.0], np.float32) * (0.55 * hi)
    target = np.clip(target, 0, 255)

    # Fine bright flecks (8-32 px) clustered on the DESIGN — edges + structure —
    # rather than uniform random, so the sparkle traces the graphics.
    rnd = _cell_field01(h, w, max(8, short // 150), seed ^ 0x4440)
    structure_bias = np.clip(0.6 * edge_strong + 0.7 * lum_n, 0.0, 1.0)
    fleck_mask = (rnd > 0.72) & (structure_bias > 0.34)
    contrast = _ink_color_field(
        h, w, inks, weights, max(8, short // 150), seed ^ 0x8880, bright=(0.95, 1.4)
    )
    fleck = np.where((rnd > 0.87)[:, :, None], contrast, np.clip(zone * 1.5 + 34.0, 0, 255))
    target = np.where(fleck_mask[:, :, None], fleck, target)

    # Blend: preserve base structure in flat areas (lower a), push color on the
    # design edges + flecks. Color still appears everywhere (zone), but the
    # artwork's lines stay legible.
    a = np.clip(intensity * (0.40 + 0.34 * lum_n), 0.0, 0.84)
    a = np.maximum(a, np.clip(edge_strong * 1.05 * intensity, 0.0, 0.9))
    a = np.where(fleck_mask, np.clip(a + 0.2, 0.0, 0.95), a)
    a3 = a[:, :, None]
    out = base * (1.0 - a3) + target * a3

    # Guarantee the owner's spec-driven variance bar (M/R/CC std >= ~22): gently
    # expand contrast on any channel that came out too flat (monochrome palettes)
    # without shifting its mean, so even single-hue styles read as many shades.
    for ch in range(3):
        s = float(out[:, :, ch].std())
        if 1.0 < s < 23.0:
            mean = float(out[:, :, ch].mean())
            out[:, :, ch] = mean + (out[:, :, ch] - mean) * min(2.0, 23.0 / s)

    arr[:, :, 0] = np.clip(out[:, :, 0], 6, 252)
    arr[:, :, 1] = np.clip(out[:, :, 1], 16, 236)
    arr[:, :, 2] = np.clip(out[:, :, 2], 10, 252)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def exotic_chromatic_amp(
    spec: Image.Image,
    paint: Image.Image,
    style: str,
    *,
    seed: int = 88001,
    intensity: float = 1.0,
    mix_styles=None,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> Image.Image:
    """Extra punch for exotic styles: brighter palette flecks + multicolor edge corridors.

    SPB-109 (2026-05-28): replaced the correlated 8-tier M/CC ramp (which forced
    every exotic to magenta) with palette-keyed, decorrelated coloring. The broad
    spectrum spread lives in spec_chroma_spread; this layer adds vividness.
    """
    intensity = float(np.clip(intensity * float(chroma_scale), 0.0, 1.6))
    spec = spec_chroma_spread(
        spec,
        style,
        paint=paint,
        seed=seed ^ 0x515E,
        intensity=min(1.1, 0.7 + 0.35 * intensity),
        mix_styles=mix_styles,
        palette_overrides=palette_overrides,
    )
    spec_arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    h, w = spec_arr.shape[:2]
    paint_rgb = np.asarray(
        paint.convert("RGB").resize((w, h), Image.Resampling.LANCZOS),
        dtype=np.float32,
    ) / 255.0
    inks, weights = _palette_arrays(mix_styles or style, palette_overrides)
    short = max(h, w)

    # Multicolor edge corridors: tint paint ink-boundaries with palette inks
    # (each channel can move any direction -> not just magenta). This is the main
    # design-tracer — vivid color rides the artwork's edges.
    from engine.paint_v2.cultural_viva_mexico import _viva_mexico_paint_luma_edge

    _, edge_n = _viva_mexico_paint_luma_edge(paint_rgb, np.ones((h, w), dtype=np.float32))
    edge_strong = np.clip(edge_n * 2.0, 0.0, 1.0)
    edge_ink = _ink_color_field(h, w, inks, weights, max(12, short // 70), seed ^ 0x6660, smooth=True)
    et = np.clip(edge_n * 1.0 * intensity, 0.0, 0.9)[:, :, None]
    spec_arr[:, :, :3] = spec_arr[:, :, :3] * (1 - et) + edge_ink * et

    # Bright vivid flecks — clustered on the design (edges + bright base structure),
    # not uniform, so exotic punch still respects the artwork.
    lum_now = _stretch01(
        (0.42 * spec_arr[:, :, 0] + 0.22 * spec_arr[:, :, 1] + 0.36 * spec_arr[:, :, 2]) / 255.0
    )
    spark_rnd = _cell_field01(h, w, max(8, short // 170), seed ^ 0x7770)
    spark_mask = (spark_rnd > 0.84) & (np.clip(0.6 * edge_strong + 0.6 * lum_now, 0, 1) > 0.32)
    spark_ink = _ink_color_field(
        h, w, inks, weights, max(8, short // 170), seed ^ 0x8880, bright=(0.9, 1.35)
    )
    sm = (spark_mask.astype(np.float32) * (0.6 + 0.35 * intensity))[:, :, None]
    spec_arr[:, :, :3] = spec_arr[:, :, :3] * (1 - sm) + spark_ink * sm

    spec_arr[:, :, 0] = np.clip(spec_arr[:, :, 0], 6, 252)
    spec_arr[:, :, 1] = np.clip(spec_arr[:, :, 1], 16, 236)
    spec_arr[:, :, 2] = np.clip(spec_arr[:, :, 2], 10, 252)
    spec_arr[:, :, 3] = 255
    return Image.fromarray(spec_arr.astype(np.uint8), "RGBA")


def _bake_once(
    paint: Image.Image,
    name: str,
    style: str,
    index: int,
    pass_idx: int,
    vibe_ref: Optional[str],
    material_hint: str = "generic",
) -> Image.Image:
    bcm = _load_viva_builder()
    grunge = _load_grunge_hooks()
    orig_semantic, orig_hidden, orig_grunge_hidden = _wrap_viva_routers(bcm, grunge)
    orig_personality = bcm.spec_personality
    boost = _PASS_BOOST[min(pass_idx, len(_PASS_BOOST) - 1)]
    plate_idx = _style_plate_index(style, index)
    route_name = _style_route_text(style)
    try:
        bcm.spec_personality = grunge.grunge_spec_personality

        def _import_personality(n: str, s: str) -> dict:
            p = dict(grunge.grunge_spec_personality(route_name, s))
            if s in STYLE_PERSONALITY:
                p.update(STYLE_PERSONALITY[s])
            return p

        def _boosted_personality(n, s):
            p = _import_personality(n, s)
            p["flake"] = float(p.get("flake", 1.0)) * boost["flake"]
            p["line"] = float(p.get("line", 1.0)) * boost["line"]
            p["metal_base"] = float(p.get("metal_base", 50)) + boost["metal_delta"]
            p["rough_base"] = float(p.get("rough_base", 80)) + boost["rough_delta"]
            p["clear_base"] = float(p.get("clear_base", 60)) + boost["clear_delta"]
            if vibe_ref:
                p = _apply_vibe_to_personality(p, vibe_ref)
            p = _apply_material_personality(p, material_hint)
            return p

        bcm.spec_personality = _boosted_personality
        return bcm.make_spec_plate(paint, plate_idx, route_name, style)
    finally:
        bcm.semantic_masks = orig_semantic
        bcm.hidden_cultural_motif = orig_grunge_hidden
        bcm.spec_personality = orig_personality


def viva_alive_enhance(
    spec: Image.Image,
    paint: Image.Image,
    style: str,
    *,
    seed: int = 88001,
    intensity: float = 1.0,
) -> Image.Image:
    """SPB-109: Viva-grade paint-locked edge corridors + fine sparkle (elevated import DNA)."""
    intensity = float(np.clip(intensity, 0.0, 1.5))
    spec_arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    h, w = spec_arr.shape[:2]
    paint_rgb = np.asarray(
        paint.convert("RGB").resize((w, h), Image.Resampling.LANCZOS),
        dtype=np.float32,
    ) / 255.0
    from engine.paint_v2.cultural_viva_mexico import _viva_mexico_paint_luma_edge

    _, edge_n = _viva_mexico_paint_luma_edge(paint_rgb, np.ones((h, w), dtype=np.float32))
    # SPB-109 (2026-05-28): keep this pass hue-neutral (structure/brightness only).
    # spec_chroma_spread now owns finish color, so edges no longer bias to magenta.
    trace = np.clip(edge_n * 0.55 * intensity, 0.0, 1.0)
    spec_arr[:, :, 0] = np.clip(spec_arr[:, :, 0] + trace * 17.0, 0, 255)
    spec_arr[:, :, 1] = np.clip(spec_arr[:, :, 1] + trace * 9.0, 18, 235)
    spec_arr[:, :, 2] = np.clip(spec_arr[:, :, 2] + trace * 15.0, 0, 255)

    rng = np.random.default_rng(seed ^ 0xA11FE)
    for band, pitch in enumerate((10, 12, 8, 14)):
        gh, gw = max(1, h // pitch), max(1, w // pitch)
        noise = rng.random((gh, gw), dtype=np.float32)
        from PIL import Image as PILImage

        n_up = np.asarray(
            PILImage.fromarray((noise * 255).astype(np.uint8), "L").resize((w, h), PILImage.Resampling.NEAREST),
            dtype=np.float32,
        ) / 255.0
        spark = np.clip((n_up - 0.68) * 4.2, 0.0, 1.0) * (0.22 + band * 0.06) * intensity
        spec_arr[:, :, 0] = np.clip(spec_arr[:, :, 0] + spark * 13.0, 0, 255)
        spec_arr[:, :, 1] = np.clip(spec_arr[:, :, 1] + spark * 9.0, 18, 235)
        spec_arr[:, :, 2] = np.clip(spec_arr[:, :, 2] + spark * 12.0, 0, 255)

    return Image.fromarray(spec_arr.astype(np.uint8), "RGBA")


def blend_spec_plates(
    spec_a: Image.Image, spec_b: Image.Image, remix_t: float, *, seed: int = 0
) -> Image.Image:
    """SPB-109: DNA remix blend.

    2026-05-28: mostly SPATIAL (dithered fine-cell selection) so each plate keeps
    its own palette colors intermixed, instead of channel-averaging two vivid
    fields into mud. A 30% linear term softens the seams.
    """
    t = float(np.clip(remix_t, 0.0, 1.0))
    a = np.asarray(spec_a.convert("RGBA"), dtype=np.float32)
    b_img = spec_b.convert("RGBA")
    if b_img.size != (a.shape[1], a.shape[0]):
        b_img = b_img.resize((a.shape[1], a.shape[0]), Image.Resampling.LANCZOS)
    b = np.asarray(b_img, dtype=np.float32)
    h, w = a.shape[:2]
    m = _cell_field01(h, w, max(10, max(h, w) // 110), seed ^ 0x9991)
    sel_b = (m < t)[:, :, None]
    spatial = np.where(sel_b, b, a)
    linear = a * (1.0 - t) + b * t
    out = spatial * 0.7 + linear * 0.3
    out[:, :, 3] = 255
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def blend_spec_plates_multi(
    specs: list,
    weights: list,
    *,
    seed: int = 0,
) -> Image.Image:
    """SPB-109: Weighted blend of N spec plates (INSANE quad).

    2026-05-28: weighted SPATIAL patchwork (per-pixel argmax of weighted cell
    fields) keeps each plate's palette vivid; 30% linear term softens seams. The
    old pure weighted-average grayed four colorful plates into one muddy mean.
    """
    if not specs:
        raise ValueError("blend_spec_plates_multi requires at least one spec")
    ws = [float(x) for x in weights[: len(specs)]]
    if len(ws) < len(specs):
        ws.extend([1.0] * (len(specs) - len(ws)))
    total = sum(ws) or 1.0
    ws = [x / total for x in ws]
    base = np.asarray(specs[0].convert("RGBA"), dtype=np.float32)
    h, w = base.shape[0], base.shape[1]
    arrs = [base]
    for spec_img in specs[1:]:
        arr = np.asarray(spec_img.convert("RGBA"), dtype=np.float32)
        if arr.shape[:2] != (h, w):
            arr = np.asarray(
                spec_img.convert("RGBA").resize((w, h), Image.Resampling.LANCZOS),
                dtype=np.float32,
            )
        arrs.append(arr)

    cell = max(12, max(h, w) // 90)
    fields = np.stack(
        [_cell_field01(h, w, cell, seed ^ (0x7000 + i * 0x111)) * ws[i] for i in range(len(arrs))],
        axis=0,
    )
    sel = np.argmax(fields, axis=0)
    spatial = np.zeros_like(base)
    for i, arr in enumerate(arrs):
        spatial = np.where((sel == i)[:, :, None], arr, spatial)
    linear = np.zeros_like(base)
    for arr, x in zip(arrs, ws):
        linear += arr * x
    out = spatial * 0.7 + linear * 0.3
    out[:, :, 3] = 255
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def bake_import_spec_dna(
    paint: Image.Image,
    name: str,
    *,
    vibe_ref: Optional[str] = None,
    style_override: Optional[str] = None,
    run_gauntlet: bool = True,
    max_gauntlet_passes: Optional[int] = None,
    micro_seed: Optional[int] = None,
    exotic: bool = False,
    bake_index: int = 1,
    alive: bool = True,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> DnaBakeResult:
    """Analyze paint plate and bake spec with DNA routing + optional gauntlet."""
    style, analysis = classify_style_from_image(paint, name)
    if style_override and style_override in _STYLES:
        style = style_override
        analysis.style = style

    cap = MAX_GAUNTLET_PASSES if run_gauntlet else 1
    if max_gauntlet_passes is not None:
        cap = max(1, min(MAX_GAUNTLET_PASSES, int(max_gauntlet_passes)))
    # SPB-109 (2026-05-29): spec_chroma_spread + the per-channel variance floor now
    # guarantee the std/range bar, so the old exotic "force >=3 gauntlet passes"
    # retry is wasted compute. Honor the caller's pass count instead (commit still
    # requests a full 5-pass refinement). Big World-bake speedup.

    plate_index = max(1, int(bake_index))
    best_spec = None
    best_stats: Dict[str, float] = {}
    passes = 0
    for pass_idx in range(cap):
        passes = pass_idx + 1
        spec = _bake_once(
            paint,
            name,
            style,
            plate_index + pass_idx,
            pass_idx,
            vibe_ref,
            analysis.material_hint,
        )
        stats = spec_channel_stats(spec)
        best_spec, best_stats = spec, stats
        if stats.get("passed", 0) >= 1.0:
            break

    assert best_spec is not None
    best_spec = edge_lock_spec_plate(best_spec, paint)
    flake_seed = micro_seed if micro_seed is not None else (hash(name) & 0xFFFF)
    best_spec = micro_flake_post_pass(best_spec, seed=flake_seed, material_hint=analysis.material_hint)
    if alive:
        best_spec = viva_alive_enhance(
            best_spec, paint, style, seed=flake_seed ^ 0xA11FE, intensity=0.85 if exotic else 0.72
        )
        best_stats = spec_channel_stats(best_spec)
    # SPB-109 (2026-05-28): EVERY style gets the full-spectrum spec palette so the
    # spec map carries many colors/shades (owner mandate). Exotic styles get the
    # higher-energy amp (which spreads internally + adds vivid flecks/edges).
    if exotic or is_exotic_style(style):
        best_spec = exotic_chromatic_amp(
            best_spec,
            paint,
            style,
            seed=flake_seed ^ 0xE011EC,
            intensity=0.92 if exotic else 0.72,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
    else:
        best_spec = spec_chroma_spread(
            best_spec,
            style,
            paint=paint,
            seed=flake_seed ^ 0x5EEDC0,
            intensity=0.85,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
    best_stats = spec_channel_stats(best_spec)
    return DnaBakeResult(
        spec=best_spec,
        analysis=analysis,
        gauntlet_passes=passes,
        gauntlet_stats=best_stats,
        gauntlet_passed=bool(best_stats.get("passed", 0) >= 1.0),
        vibe_ref=vibe_ref,
    )


def bake_import_spec_dna_remix(
    paint: Image.Image,
    name: str,
    style_a: str,
    style_b: str,
    remix_t: float,
    *,
    vibe_ref: Optional[str] = None,
    max_gauntlet_passes: int = 2,
    micro_seed: Optional[int] = None,
    exotic: bool = False,
    bake_index: int = 1,
    alive: bool = True,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> DnaBakeResult:
    """SPB-109: Bake two DNA styles and blend — powers DNA Remix slider + SHOKK THE WORLD."""
    if style_a not in _STYLES:
        style_a = "abstract_gradient"
    if style_b not in _STYLES:
        style_b = "metal_flake"
    r_a = bake_import_spec_dna(
        paint,
        name + "_a",
        vibe_ref=vibe_ref,
        style_override=style_a,
        max_gauntlet_passes=max_gauntlet_passes,
        micro_seed=(micro_seed or 8801) ^ 0xA5A5,
        exotic=exotic,
        bake_index=bake_index,
        alive=alive,
        chroma_scale=chroma_scale,
        palette_overrides=palette_overrides,
    )
    r_b = bake_import_spec_dna(
        paint,
        name + "_b",
        vibe_ref=vibe_ref,
        style_override=style_b,
        max_gauntlet_passes=max_gauntlet_passes,
        micro_seed=(micro_seed or 8801) ^ 0x5A5A,
        exotic=exotic,
        bake_index=bake_index + 17,
        alive=alive,
        chroma_scale=chroma_scale,
        palette_overrides=palette_overrides,
    )
    blended = blend_spec_plates(r_a.spec, r_b.spec, remix_t, seed=(micro_seed or 8801) ^ 0x8E0D)
    blended = edge_lock_spec_plate(blended, paint)
    blended = micro_flake_post_pass(
        blended,
        seed=micro_seed if micro_seed is not None else int(remix_t * 1000) ^ (hash(style_a) & 0xFFFF),
        material_hint=r_a.analysis.material_hint,
    )
    if alive:
        blend_style = style_a if remix_t < 0.5 else style_b
        blended = viva_alive_enhance(
            blended, paint, blend_style, seed=(micro_seed or 8801) ^ 0xB1EED, intensity=0.9
        )
    # Remix gets the spectrum spread across BOTH styles' palettes (vivid mix).
    blend_lead = style_a if remix_t < 0.5 else style_b
    blended = exotic_chromatic_amp(
        blended,
        paint,
        blend_lead,
        seed=(micro_seed or 8801) ^ 0xE11E,
        intensity=0.82 if exotic else 0.66,
        mix_styles=[style_a, style_b],
        chroma_scale=chroma_scale,
        palette_overrides=palette_overrides,
    )
    stats = spec_channel_stats(blended)
    analysis = r_a.analysis
    analysis.style = f"{style_a}+{style_b}"
    return DnaBakeResult(
        spec=blended,
        analysis=analysis,
        gauntlet_passes=max(r_a.gauntlet_passes, r_b.gauntlet_passes),
        gauntlet_stats=stats,
        gauntlet_passed=bool(stats.get("passed", 0) >= 1.0),
        vibe_ref=vibe_ref,
    )


def bake_import_spec_dna_insane(
    paint: Image.Image,
    name: str,
    styles: list,
    weights: list,
    *,
    vibe_ref: Optional[str] = None,
    micro_seed: Optional[int] = None,
    bake_index: int = 1,
    preview_fast: bool = False,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> DnaBakeResult:
    """SPB-109: INSANE — bake four DNA styles and weighted-blend into one spec plate."""
    from engine.paint_v2.import_dna_style_catalog import DNA_STYLES

    # Viva make_spec_plate always builds 2048² grids — never downscale paint here (broadcast crash).
    quad = [s for s in styles if s in _STYLES]
    if len(quad) < 2:
        quad = ["disco_glitter", "holo_prism", "electric_storm", "oil_slick"]
    while len(quad) < 4:
        quad.append(DNA_STYLES[len(quad) % len(DNA_STYLES)])
    quad = quad[:4]
    ws = list(weights[:4]) if weights else [0.25, 0.25, 0.25, 0.25]
    if len(ws) < 4:
        ws.extend([0.25] * (4 - len(ws)))
    specs = []
    for i, st in enumerate(quad):
        passes = 1 if preview_fast else 1
        sub = bake_import_spec_dna(
            paint,
            f"{name}_q{i}",
            vibe_ref=vibe_ref,
            style_override=st,
            max_gauntlet_passes=passes,
            micro_seed=(micro_seed or 8801) ^ (i * 0x1337),
            exotic=False,
            bake_index=bake_index + i * 23,
            alive=not preview_fast,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
        specs.append(sub.spec)
    blended = blend_spec_plates_multi(specs, ws, seed=(micro_seed or 8801) ^ 0x1A5A)
    blended = edge_lock_spec_plate(blended, paint)
    lead = quad[int(np.argmax(ws))]
    flake_seed = micro_seed if micro_seed is not None else (hash(name) & 0xFFFF)
    blended = micro_flake_post_pass(
        blended, seed=flake_seed ^ 0x1A5A1E, material_hint="generic"
    )
    blended = viva_alive_enhance(blended, paint, lead, seed=flake_seed ^ 0x1A5A1E, intensity=1.1)
    # INSANE: spread across ALL four styles' palettes -> maximum-gamut rainbow spec.
    blended = exotic_chromatic_amp(
        blended,
        paint,
        lead,
        seed=flake_seed ^ 0x1A54EE,
        intensity=0.85,
        mix_styles=quad,
        chroma_scale=chroma_scale,
        palette_overrides=palette_overrides,
    )
    stats = spec_channel_stats(blended)
    style, analysis = classify_style_from_image(paint, name)
    analysis.style = "+".join(quad)
    return DnaBakeResult(
        spec=blended,
        analysis=analysis,
        gauntlet_passes=1,
        gauntlet_stats=stats,
        gauntlet_passed=bool(stats.get("passed", 0) >= 1.0),
        vibe_ref=vibe_ref,
    )


def edge_lock_spec_plate(spec: Image.Image, paint: Image.Image) -> Image.Image:
    """Align spec highlights with paint edges (Import DNA edge corridor pass)."""
    from engine.paint_v2.cultural_viva_mexico import _viva_mexico_paint_luma_edge

    spec_arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    paint_arr = np.asarray(paint.convert("RGB"), dtype=np.float32) / 255.0
    h, w = spec_arr.shape[:2]
    if paint_arr.shape[:2] != (h, w):
        from PIL import Image as PILImage
        paint_arr = np.asarray(
            paint.convert("RGB").resize((w, h), PILImage.Resampling.LANCZOS),
            dtype=np.float32,
        ) / 255.0
    mask = np.ones((h, w), dtype=np.float32)
    _, edge_n = _viva_mexico_paint_luma_edge(paint_arr, mask)
    # Fine edge corridors: boost M and Cc on ink boundaries (owner 8-32px fidelity intent).
    spec_arr[:, :, 0] = np.clip(spec_arr[:, :, 0] + edge_n * 28.0, 0, 255)
    spec_arr[:, :, 2] = np.clip(spec_arr[:, :, 2] + edge_n * 22.0, 0, 255)
    return Image.fromarray(spec_arr.astype(np.uint8), "RGBA")


def micro_flake_post_pass(spec: Image.Image, seed: int = 88001, material_hint: str = "generic") -> Image.Image:
    """Fine 8–12px sparkle layer on M/Cc (owner fine-feature doctrine)."""
    spec_arr = np.asarray(spec.convert("RGBA"), dtype=np.float32)
    h, w = spec_arr.shape[:2]
    rng = np.random.default_rng(seed)
    tile = 10
    gh, gw = max(1, h // tile), max(1, w // tile)
    coarse = rng.random((gh, gw), dtype=np.float32)
    from PIL import Image as PILImage
    flake = np.asarray(
        PILImage.fromarray((coarse * 255).astype(np.uint8), "L").resize((w, h), PILImage.Resampling.NEAREST),
        dtype=np.float32,
    ) / 255.0
    sparkle = np.clip((flake - 0.78) * 6.0, 0.0, 1.0)
    m_boost = {"chrome_holo": 24.0, "carbon": 20.0, "brushed_metal": 16.0, "leather": 8.0, "worn": 10.0}.get(
        material_hint, 18.0
    )
    c_boost = {"chrome_holo": 22.0, "carbon": 12.0, "brushed_metal": 14.0, "leather": 6.0, "worn": 8.0}.get(
        material_hint, 14.0
    )
    spec_arr[:, :, 0] = np.clip(spec_arr[:, :, 0] + sparkle * m_boost, 0, 255)
    spec_arr[:, :, 2] = np.clip(spec_arr[:, :, 2] + sparkle * c_boost, 0, 255)
    return Image.fromarray(spec_arr.astype(np.uint8), "RGBA")


def make_preview_combined(paint: Image.Image, spec: Image.Image, width: int = 640) -> Image.Image:
    """Side-by-side paint | spec visualization for import preview."""
    h = width // 2
    p = paint.convert("RGB").resize((h, h), Image.Resampling.LANCZOS)
    s = spec.convert("RGBA").resize((h, h), Image.Resampling.LANCZOS)
    s_arr = np.asarray(s, dtype=np.uint8)
    spec_rgb = Image.fromarray(np.stack([s_arr[:, :, 0], s_arr[:, :, 1], s_arr[:, :, 2]], axis=-1), "RGB")
    combo = Image.new("RGB", (width, h))
    combo.paste(p, (0, 0))
    combo.paste(spec_rgb, (h, 0))
    return combo


_CHANNEL_TINTS = {
    "r": (1.0, 0.3, 0.3),
    "g": (0.3, 1.0, 0.3),
    "b": (0.3, 0.5, 1.0),
    "a": (1.0, 0.7, 0.3),
}


def spec_to_rgb_preview(spec: Image.Image) -> Image.Image:
    """Full RGB spec map (M/R/CC channels) for ALL view."""
    s_arr = np.asarray(spec.convert("RGBA"), dtype=np.uint8)
    return Image.fromarray(np.stack([s_arr[:, :, 0], s_arr[:, :, 1], s_arr[:, :, 2]], axis=-1), "RGB")


def render_spec_channel_rgb(spec: Image.Image, channel: str) -> Image.Image:
    """Tinted single-channel view — matches live preview setSpecChannel in Paint Booth."""
    ch = channel.lower()
    if ch not in _CHANNEL_TINTS:
        raise ValueError(f"Unknown spec channel: {channel}")
    ch_idx = {"r": 0, "g": 1, "b": 2, "a": 3}[ch]
    tint = _CHANNEL_TINTS[ch]
    arr = np.asarray(spec.convert("RGBA"), dtype=np.uint8)
    val = arr[:, :, ch_idx].astype(np.float32)
    out = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    out[:, :, 0] = np.clip(val * tint[0], 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(val * tint[1], 0, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(val * tint[2], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def make_paint_channel_split(paint: Image.Image, spec: Image.Image, channel: str, width: int = 640) -> Image.Image:
    """Side-by-side paint | tinted channel — spatial correspondence vs upload."""
    h = width // 2
    p = paint.convert("RGB").resize((h, h), Image.Resampling.LANCZOS)
    ch = render_spec_channel_rgb(spec, channel).resize((h, h), Image.Resampling.LANCZOS)
    combo = Image.new("RGB", (width, h))
    combo.paste(p, (0, 0))
    combo.paste(ch, (h, 0))
    return combo


def pil_to_data_url(img: Image.Image) -> str:
    import base64
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def make_import_preview_payload(paint: Image.Image, spec: Image.Image, *, thumb: int = 384) -> dict:
    """SHOKK DROP import preview: upload, blended spec, paint|channel splits for R/G/B."""
    sq = thumb
    p_sq = paint.convert("RGB").resize((sq, sq), Image.Resampling.LANCZOS)
    s_sq = spec_to_rgb_preview(spec).resize((sq, sq), Image.Resampling.LANCZOS)
    split_w = sq * 2
    return {
        "preview": pil_to_data_url(make_preview_combined(paint, spec, width=split_w)),
        "preview_paint": pil_to_data_url(p_sq),
        "preview_spec": pil_to_data_url(s_sq),
        "preview_channels": {
            "r": pil_to_data_url(make_paint_channel_split(paint, spec, "r", width=split_w)),
            "g": pil_to_data_url(make_paint_channel_split(paint, spec, "g", width=split_w)),
            "b": pil_to_data_url(make_paint_channel_split(paint, spec, "b", width=split_w)),
        },
    }


def dna_metadata(result: DnaBakeResult) -> Dict[str, Any]:
    a = result.analysis
    return {
        "pipeline": "import_dna_viva_grunge",
        "style": a.style,
        "intent": a.intent,
        "material_hint": a.material_hint,
        "confidence": round(a.confidence, 3),
        "edge_density": round(a.edge_density, 4),
        "saturation": round(a.saturation, 4),
        "gauntlet_passes": result.gauntlet_passes,
        "gauntlet_passed": result.gauntlet_passed,
        "gauntlet_stats": {k: round(v, 2) if isinstance(v, float) else v for k, v in result.gauntlet_stats.items()},
        "vibe_ref": result.vibe_ref,
    }
