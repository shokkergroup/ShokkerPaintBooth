"""Small, bounded helpers for Easy Spec Sculpt color-by-color materials.

The original Spec Sculpt laboratory keeps its advanced color/tone systems.  The
guided app sends at most six simple RGB targets, each with one named look and a
linked material/spec scale.  This module owns validation, color masks and the
final mask composite so the server route does not grow another UI-specific
pipeline inside ``server.py``.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import numpy as np

MAX_EASY_COLOR_LAYERS = 6
MIN_MATERIAL_SCALE = 0.25
MAX_MATERIAL_SCALE = 1.0
MATERIAL_SCALE_STEP = 0.05
MATERIAL_IMPACT_FACTORS = {"subtle": 0.72, "balanced": 1.0, "bold": 1.28}
# Human-neutral painted satin: no metal, fairly rough, and no clearcoat.  The
# iRacing blue channel is inverted (255 = no coat), so using zero here would
# make the supposedly subtle setting wetter and more dramatic.
MATERIAL_IMPACT_NEUTRAL = np.asarray((0.0, 160.0, 255.0), dtype=np.float32)
_LOOK_KINDS = {"preset", "catalog", "mode"}
_MODE_IDS = {"zoned", "fracture", "candy_depth"}


def normalize_material_scale(value: Any, default: float = 1.0) -> float:
    """Clamp Easy Mode scale to the proven finer-than-source range.

    Main Paint Booth treats a base scale below 1 as a finer tiled material.  Easy
    Spec Sculpt deliberately exposes only that useful half of the contract: it
    avoids a second independent spec control and keeps base/spec detail matched.
    """

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = float(default)
    parsed = round(parsed / MATERIAL_SCALE_STEP) * MATERIAL_SCALE_STEP
    return float(max(MIN_MATERIAL_SCALE, min(MAX_MATERIAL_SCALE, round(parsed, 2))))


def pattern_tile_for_scale(scale: Any) -> float:
    """Convert Paint Booth base-scale semantics to Spec Sculpt pattern tiling."""

    linked = normalize_material_scale(scale)
    return float(round(1.0 / linked, 5))


def normalize_material_impact(value: Any, default: str = "balanced") -> str:
    """Return one of Easy Mode's three whole-plan response strengths."""

    parsed = str(value or "").strip().lower()
    return parsed if parsed in MATERIAL_IMPACT_FACTORS else default


def apply_material_impact(spec: np.ndarray, impact: Any) -> np.ndarray:
    """Quiet or amplify a finished material plan without changing its pattern.

    [SPB-SPEC-SCULPT headline 2026-07-20] Owner: make Spec Sculpt a
    "headlining feature" while keeping its core easy.  This is deliberately a
    post-composite response transform: every authored 8-32 px feature and its
    channel-to-channel color variation stays spatially identical.  ``balanced``
    is byte-for-byte unchanged; subtle/bold move the response toward/away from
    iRacing's neutral matte reference.  M7 is not applicable because no catalog
    renderer or baked finish is modified.
    """

    arr = np.asarray(spec)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError("spec must be HxWx3 or HxWx4")
    level = normalize_material_impact(impact)
    if level == "balanced":
        return arr.astype(np.uint8, copy=True)
    out = arr.astype(np.float32, copy=True)
    factor = MATERIAL_IMPACT_FACTORS[level]
    out[..., :3] = MATERIAL_IMPACT_NEUTRAL + (out[..., :3] - MATERIAL_IMPACT_NEUTRAL) * factor
    if out.shape[2] >= 4:
        out[..., 3] = 255.0
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def apply_material_impact_to_report(report: list[dict[str, Any]], impact: Any) -> list[dict[str, Any]]:
    """Keep selected-color response meters aligned with the transformed map."""

    level = normalize_material_impact(impact)
    factor = MATERIAL_IMPACT_FACTORS[level]
    adjusted: list[dict[str, Any]] = []
    for source in report:
        row = dict(source)
        means = row.get("material_means")
        if isinstance(means, (list, tuple)) and len(means) >= 3:
            values = np.asarray(means[:3], dtype=np.float32) * 255.0
            values = MATERIAL_IMPACT_NEUTRAL + (values - MATERIAL_IMPACT_NEUTRAL) * factor
            row["material_means"] = [round(float(value / 255.0), 5) for value in np.clip(values, 0.0, 255.0)]
        deviations = row.get("material_deviations")
        if isinstance(deviations, (list, tuple)) and len(deviations) >= 3:
            row["material_deviations"] = [
                round(float(max(0.0, min(1.0, float(value) * abs(factor)))), 5)
                for value in deviations[:3]
            ]
        adjusted.append(row)
    return adjusted


def parse_easy_color_layers(raw: Any) -> list[dict[str, Any]]:
    """Return a safe, compact list of guided color-target material layers."""

    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if not isinstance(raw, list):
        return []

    clean: list[dict[str, Any]] = []
    for index, item in enumerate(raw[:MAX_EASY_COLOR_LAYERS]):
        if not isinstance(item, dict):
            continue
        color = item.get("color") or item.get("color_rgb")
        if not isinstance(color, (list, tuple)) or len(color) < 3:
            continue
        try:
            rgb = [max(0, min(255, int(round(float(color[i]))))) for i in range(3)]
        except (TypeError, ValueError):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        look_id = str(item.get("look_id") or item.get("id") or "").strip()
        if kind not in _LOOK_KINDS or not look_id:
            continue
        if kind == "mode" and look_id not in _MODE_IDS:
            continue
        catalog_type = str(item.get("catalog_type") or item.get("registry_type") or "").strip().lower()
        if kind != "catalog" or catalog_type not in {"base", "monolithic"}:
            catalog_type = ""
        try:
            tolerance = float(item.get("tolerance", 30))
        except (TypeError, ValueError):
            tolerance = 30.0
        try:
            seed = int(item["seed"]) & 0xFFFFFFFF if item.get("seed") not in (None, "") else None
        except (TypeError, ValueError):
            seed = None
        replacement_raw = item.get("replacement_color")
        replacement = None
        if isinstance(replacement_raw, (list, tuple)) and len(replacement_raw) >= 3:
            try:
                replacement = [max(0, min(255, int(round(float(replacement_raw[i]))))) for i in range(3)]
            except (TypeError, ValueError):
                replacement = None
        clean.append(
            {
                "slot_id": str(item.get("slot_id") or f"color-{index + 1}")[:80],
                "color": rgb,
                "tolerance": float(max(6.0, min(90.0, tolerance))),
                "kind": kind,
                "look_id": look_id,
                "catalog_type": catalog_type,
                "seed": seed,
                "material_scale": normalize_material_scale(item.get("material_scale", 1.0)),
                "replacement_color": replacement,
            }
        )
    return clean


def recolor_easy_paint(paint_tex01: np.ndarray, layers: list[dict[str, Any]]) -> np.ndarray:
    """Repaint only guided color masks while preserving local livery shading."""

    from engine.core import analyze_paint_colors, build_zone_mask

    source = np.ascontiguousarray(np.asarray(paint_tex01, dtype=np.float32)[..., :3])
    out = source.copy()
    active = [layer for layer in layers[:MAX_EASY_COLOR_LAYERS] if layer.get("replacement_color") is not None]
    if not active:
        return out
    stats = analyze_paint_colors(source)
    feather = max(0.45, 1.5 * (max(source.shape[:2]) / 2048.0))
    luminance = source[..., 0] * 0.2126 + source[..., 1] * 0.7152 + source[..., 2] * 0.0722
    shade = np.clip(0.55 + 0.9 * luminance, 0.45, 1.45)[..., None]
    for layer in active:
        mask = build_zone_mask(
            source,
            stats,
            {"color_rgb": layer["color"], "tolerance": layer["tolerance"]},
            blur_radius=feather,
        ).astype(np.float32, copy=False)
        replacement = np.asarray(layer["replacement_color"], dtype=np.float32).reshape(1, 1, 3) / 255.0
        colored = np.clip(replacement * shade, 0.0, 1.0)
        alpha = np.clip(mask, 0.0, 1.0)[..., None]
        out = out * (1.0 - alpha) + colored * alpha
    return np.clip(out, 0.0, 1.0)

def composite_easy_color_layers(
    base_spec: np.ndarray,
    paint_tex01: np.ndarray,
    layers: list[dict[str, Any]],
    render_layer: Callable[[dict[str, Any]], np.ndarray],
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Composite named material looks into soft color masks, in slot order.

    Later slots win only where their soft masks overlap.  Unmatched pixels keep
    the whole-paint look.  ``render_layer`` is supplied by the route so this
    helper stays independent of registry/bootstrap state and is straightforward
    to regression-test.
    """

    from engine.core import analyze_paint_colors, build_zone_mask

    tex = np.ascontiguousarray(np.asarray(paint_tex01, dtype=np.float32)[..., :3])
    out = np.asarray(base_spec, dtype=np.float32).copy()
    if out.ndim != 3 or out.shape[2] < 3:
        raise ValueError("base_spec must be HxWx3 or HxWx4")
    h, w = tex.shape[:2]
    if out.shape[:2] != (h, w):
        raise ValueError("base_spec and paint_tex01 must share dimensions")

    stats = analyze_paint_colors(tex)
    feather = max(0.45, 1.5 * (max(h, w) / 2048.0))
    report: list[dict[str, Any]] = []
    for layer in layers[:MAX_EASY_COLOR_LAYERS]:
        mask = build_zone_mask(
            tex,
            stats,
            {"color_rgb": layer["color"], "tolerance": layer["tolerance"]},
            blur_radius=feather,
        ).astype(np.float32, copy=False)
        coverage = float(np.count_nonzero(mask > 0.15) / max(1, h * w))
        row = {
            "slot_id": layer["slot_id"],
            "color": list(layer["color"]),
            "look_id": layer["look_id"],
            "kind": layer["kind"],
            "catalog_type": layer.get("catalog_type", ""),
            "material_scale": layer["material_scale"],
            "coverage_pct": round(coverage * 100.0, 2),
        }
        if coverage <= 0.00001:
            row["matched"] = False
            report.append(row)
            continue
        local = np.asarray(render_layer(layer), dtype=np.float32)
        if local.shape[:2] != (h, w) or local.ndim != 3 or local.shape[2] < 3:
            raise ValueError("render_layer must return a matching HxWx3/4 spec")
        # Report the material response inside this color's own mask. Easy Mode
        # uses this for its selected-color meters; a 5% accent should not look
        # weak merely because 95% of the car belongs to another material. Sample
        # large install renders down to <=512 per edge so this proof stays cheap.
        sample_step = max(1, max(h, w) // 512)
        sample_values = np.clip(local[::sample_step, ::sample_step, :3], 0.0, 255.0)
        sample_weights = mask[::sample_step, ::sample_step][..., None]
        weight_sum = float(sample_weights[..., 0].sum())
        if weight_sum > 1e-6:
            means = (sample_values * sample_weights).sum(axis=(0, 1)) / weight_sum
            variance = (((sample_values - means) ** 2) * sample_weights).sum(axis=(0, 1)) / weight_sum
            row["material_means"] = [round(float(value / 255.0), 5) for value in means]
            row["material_deviations"] = [round(float(np.sqrt(max(0.0, value)) / 255.0), 5) for value in variance]
        alpha = np.clip(mask, 0.0, 1.0)[..., None]
        out[..., :3] = out[..., :3] * (1.0 - alpha) + local[..., :3] * alpha
        row["matched"] = True
        report.append(row)

    if out.shape[2] >= 4:
        out[..., 3] = 255.0
    return np.clip(np.round(out), 0, 255).astype(np.uint8), report
