"""Compact, public render-recipe data for the isolated SHOKK DEMO.

The paid application owns a much richer share-card implementation.  This
module intentionally describes only the controls that the demo can render;
it never imports the paid registry or serializes masks, source pixels, or
other large/private request fields.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RECIPE_SCHEMA = "spb-demo-render-recipe/1"
DEFAULT_LOGO_URL = "/assets/branding/shokker-paint-booth.png"
DEFAULT_STARTUP_LOGOS = (
    "/assets/branding/shokk-handmark.png",
    "/assets/branding/shokker-paint-booth.png",
    "/assets/branding/shokker-road.png",
)


def _first(value: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in value and value[key] is not None:
            return value[key]
    return default


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ui_percent(value: Any, default: float = 100.0) -> int:
    return round(max(0.0, min(100.0, _number(value, default))))


def _ratio_percent(value: Any, default: float = 1.0) -> int:
    amount = _number(value, default)
    if -1.0 <= amount <= 1.0:
        amount *= 100.0
    return round(max(0.0, min(100.0, amount)))


def _spec_ratio_percent(value: Any, default: float = 1.0) -> int:
    amount = _number(value, default)
    if -3.0 <= amount <= 3.0:
        amount *= 100.0
    return round(max(0.0, min(300.0, amount)))


def _channel_value(value: Any) -> int:
    return round(max(-127.0, min(127.0, _number(value, 0.0))))


def _color_text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first(value, "color", "color_rgb", "rgb", "hex")
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("#") and len(text) in {4, 7}:
            return text.upper()
        return text[:32]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        channels = [_number(value[index]) for index in range(3)]
        if max(channels) <= 1.0:
            channels = [channel * 255.0 for channel in channels]
        ints = [round(max(0.0, min(255.0, channel))) for channel in channels]
        return "#" + "".join(f"{channel:02X}" for channel in ints)
    return ""


def _coverage_colors(zone: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = zone.get("color")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    colors: list[dict[str, Any]] = []
    for entry in raw[:64]:
        if isinstance(entry, Mapping):
            color = _color_text(_first(entry, "color_rgb", "rgb", "color", "hex"))
            tolerance = round(max(0.0, min(100.0, _number(entry.get("tolerance"), 40.0))))
        else:
            color = _color_text(entry)
            tolerance = 40
        if color:
            colors.append({"color": color, "tolerance": tolerance})
    return colors


def _exclusions(zone: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = zone.get("exclusions")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw[:64]:
        color = _color_text(entry)
        if color:
            tolerance = round(
                max(0.0, min(100.0, _number(entry.get("tolerance"), 40.0)))
            ) if isinstance(entry, Mapping) else 40
            items.append({"color": color, "tolerance": tolerance})
    return items


def _layer_ids(zone: Mapping[str, Any]) -> list[str]:
    raw = _first(zone, "source_layers", "sourceLayers", default=[])
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = [raw] if raw else []
    result: list[str] = []
    for value in raw:
        if isinstance(value, Mapping):
            value = _first(value, "id", "layer_id", "layerId")
        text = str(value or "").strip()[:160]
        if text and text not in result:
            result.append(text)
    return result[:64]


def _gradient_stops(zone: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = _first(zone, "gradient_stops", "gradientStops", default=[])
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    result: list[dict[str, Any]] = []
    for entry in raw[:16]:
        if not isinstance(entry, Mapping):
            continue
        position = max(0.0, min(1.0, _number(_first(entry, "pos", "position", "offset"))))
        color = _color_text(_first(entry, "color", "color_rgb", "rgb"))
        if color:
            result.append({"position": round(position, 4), "color": color})
    return result


def _zone_recipe(zone: Mapping[str, Any], index: int, catalog: Any) -> dict[str, Any]:
    finish_id = str(zone.get("_demo_finish_id") or "")
    finish = catalog.get(finish_id)
    source_id = str(zone.get("_demo_color_finish_id") or "")
    color_source = catalog.get(source_id) if source_id else None
    layer_ids = _layer_ids(zone)
    coverage_mode = str(zone.get("_demo_coverage_mode") or "everything")
    requested_mode = str(
        zone.get("_demo_requested_base_color_mode")
        or zone.get("base_color_mode")
        or "finish"
    )
    base_color: dict[str, Any] = {
        "mode": requested_mode,
        "locked": bool(_first(zone, "lock_base_color", "lockBaseColor", default=False)),
        "strength": _ratio_percent(
            _first(zone, "base_color_strength", "baseColorStrength", default=1.0)
        ),
    }
    if requested_mode == "solid":
        base_color["color"] = _color_text(
            _first(zone, "base_color_hex", "baseColorHex", "base_color", "baseColor")
        )
    elif requested_mode == "special":
        base_color["source"] = {
            "id": source_id,
            "name": color_source.name if color_source else source_id or "Choose a source",
        }
    elif requested_mode == "gradient":
        base_color["direction"] = str(
            _first(zone, "gradient_direction", "gradientDirection", default="horizontal")
        )
        base_color["stops"] = _gradient_stops(zone)

    shifts = _first(zone, "spec_channel_shift", "specChannelShift", default=[0, 0, 0])
    if not isinstance(shifts, Sequence) or isinstance(shifts, (str, bytes)):
        shifts = [0, 0, 0]
    shifts = list(shifts) + [0, 0, 0]
    source_index = round(_number(zone.get("_demo_source_index"), index))
    return {
        "order": source_index + 1,
        "name": str(zone.get("name") or f"Zone {source_index + 1}")[:120],
        "coverage": {
            "mode": coverage_mode,
            "colors": _coverage_colors(zone),
            "exclusions": _exclusions(zone),
            "layer_scope": {
                "restricted": bool(layer_ids or zone.get("_demo_source_layer_restricted")),
                "count": len(layer_ids),
                "ids": layer_ids,
                "scope_id": str(zone.get("_demo_source_layer_scope_id") or "")[:128],
            },
        },
        "material": {
            "id": finish_id,
            "name": finish.name if finish else finish_id,
            "category": finish.category if finish else "",
            "kind": finish.kind if finish else "",
        },
        "base_color": base_color,
        "strengths": {
            "zone": _ui_percent(zone.get("intensity"), 100.0),
            "base": _ratio_percent(_first(zone, "base_strength", "baseStrength", default=1.0)),
            "spec": _spec_ratio_percent(
                _first(zone, "base_spec_strength", "baseSpecStrength", default=1.0)
            ),
        },
        "adjustments": {
            "color_lab_enabled": _first(zone, "base_color_lab_enabled", "baseColorLabEnabled") is True,
            "hue": round(_number(_first(zone, "base_hue_offset", "baseHueOffset"))),
            "saturation": round(
                _number(_first(zone, "base_saturation_adjust", "baseSaturationAdjust"))
            ),
            "brightness": round(
                _number(_first(zone, "base_brightness_adjust", "baseBrightnessAdjust"))
            ),
            "base_scale": round(
                _number(_first(zone, "base_scale", "baseScale", default=1.0), 1.0), 2
            ),
            "base_rotation": round(
                _number(_first(zone, "base_rotation", "baseRotation"))
            ),
            "color_scale": round(
                _number(_first(zone, "base_color_scale", "baseColorScale", default=1.0), 1.0), 2
            ),
            "color_rotation": round(
                _number(_first(zone, "base_color_rotation", "baseColorRotation"))
            ),
            "color_depth": _ratio_percent(
                _first(zone, "base_color_depth", "baseColorDepth", default=0.65), 0.65
            ),
            "color_flip": round(
                _number(_first(zone, "base_color_flip", "baseColorFlip"))
            ),
            "underglow": _ratio_percent(
                _first(zone, "base_color_underglow", "baseColorUnderglow", default=0.0), 0.0
            ),
            "spec_scale": round(
                _number(_first(zone, "spec_scale", "specScale", default=1.0), 1.0), 2
            ),
            "spec_rotation": round(
                _number(_first(zone, "spec_rotation", "specRotation"))
            ),
            "spec_blend": str(
                _first(zone, "base_spec_blend_mode", "baseSpecBlendMode", default="normal")
            ),
            "spec_channels": {
                "metal": _channel_value(shifts[0]),
                "rough": _channel_value(shifts[1]),
                "coat": _channel_value(shifts[2]),
            },
        },
    }


def build_render_recipe(
    *,
    request_data: Mapping[str, Any],
    zones: Sequence[Mapping[str, Any]],
    catalog: Any,
    job_id: str,
    elapsed_seconds: float,
    source_transport: str,
    output_status: Mapping[str, Any] | None,
    preview_urls: Mapping[str, str],
    download_urls: Mapping[str, str],
    use_custom_number: bool,
    iracing_id: str,
) -> dict[str, Any]:
    """Return the small, standalone recipe contract sent with a full render."""

    branding = catalog.raw.get("branding") or {}
    product = catalog.raw.get("product") or {}
    raw_source = str(
        request_data.get("paint_file") or request_data.get("source_path") or ""
    ).strip()
    source_name = Path(raw_source).name if raw_source else "Browser source image"
    output_path = str((output_status or {}).get("path") or "")
    car_number = str(request_data.get("car_number") or "").strip()[:12]
    return {
        "schema": RECIPE_SCHEMA,
        "product": {
            "id": "shokk-demo",
            "name": str(product.get("display_name") or "Shokker Paint Booth — SHOKK DEMO"),
            "version": str(product.get("version") or ""),
            "credit": str(branding.get("render_credit") or "Made with SHOKK DEMO"),
        },
        "branding": {
            "logo": str(branding.get("logo_url") or DEFAULT_LOGO_URL),
            "startup_logos": list(branding.get("startup_logos") or DEFAULT_STARTUP_LOGOS),
        },
        "render": {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "elapsed_seconds": round(float(elapsed_seconds), 2),
            "source": {
                "name": source_name,
                "path": raw_source[:1024],
                "transport": source_transport,
            },
            "output": {
                "path": output_path[:1024],
                "verified": bool((output_status or {}).get("verified")),
                "files": [str(item)[:180] for item in (output_status or {}).get("pushed_files", [])[:8]],
            },
            "number": {
                "mode": "custom" if use_custom_number else "sim-stamped",
                "value": car_number if use_custom_number else "iRacing stamped number",
                "iracing_id": iracing_id,
            },
        },
        "previews": dict(preview_urls),
        "downloads": dict(download_urls),
        "zones": [_zone_recipe(zone, index, catalog) for index, zone in enumerate(zones)],
        "links": {
            "full_version": str(branding.get("payhip_url") or ""),
            "payhip": str(branding.get("payhip_url") or ""),
            "discord": str(branding.get("discord_url") or ""),
        },
    }
