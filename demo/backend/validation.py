"""Fail-closed validation for the deliberately small demo feature surface."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence


NONE_SENTINELS = {"", "none", "null", "undefined", "__none__", "_none_"}
EXTRA_BASE_PREFIXES = ("second_base", "third_base", "fourth_base", "fifth_base")
SPEC_STACK_KEYS = (
    "spec_pattern",
    "specPattern",
    "spec_pattern_stack",
    "specPatternStack",
    "overlay_spec_pattern_stack",
    "overlaySpecPatternStack",
    "third_overlay_spec_pattern_stack",
    "thirdOverlaySpecPatternStack",
    "fourth_overlay_spec_pattern_stack",
    "fourthOverlaySpecPatternStack",
    "fifth_overlay_spec_pattern_stack",
    "fifthOverlaySpecPatternStack",
)
BASE_COLOR_MODE_ALIASES = {
    "finish": "finish",
    "finish-own": "finish",
    "finish_own": "finish",
    "own": "finish",
    "material": "finish",
    "source": "source",
    "source-paint": "source",
    "source_paint": "source",
    "spec-only": "source",
    "spec_only": "source",
    "solid": "solid",
    "special": "special",
    "from-special": "special",
    "from_special": "special",
    "mono": "special",
    "gradient": "gradient",
    "custom-gradient": "gradient",
    "custom_gradient": "gradient",
}
COVERAGE_MODE_ALIASES = {
    "all": "everything",
    "everything": "everything",
    "full": "everything",
    "colors": "colors",
    "colours": "colors",
    "color": "colors",
    "multi": "colors",
    "picker": "colors",
    "remaining": "remaining",
    "remainder": "remaining",
    "rest": "remaining",
    "everything-else": "remaining",
    "everything_else": "remaining",
    "none": "none",
    "off": "none",
    "disabled": "none",
    "": "none",
}
GRADIENT_DIRECTIONS = {
    "horizontal",
    "vertical",
    "diagonal_down",
    "diagonal_up",
    "radial",
    "angular",
}
MAX_SOURCE_LAYER_SCOPES = 64
MAX_SOURCE_LAYER_SCOPE_ID_LENGTH = 128
MAX_SOURCE_LAYER_SCOPE_PIXELS = 4096 * 4096
MAX_SOURCE_LAYER_SCOPE_RUNS = 4 * 1024 * 1024
MAX_SOURCE_LAYER_RGB_CHARS = (64 * 1024 * 1024 * 4 // 3) + 128
MAX_SOURCE_LAYER_TABLE_RGB_CHARS = 128 * 1024 * 1024
MAX_BASE_SPEC_STRENGTH_RATIO = 3.0
NAMED_COLOR_NAMES = {
    "black",
    "white",
    "red",
    "green",
    "blue",
    "yellow",
    "cyan",
    "magenta",
    "orange",
    "purple",
    "pink",
    "gray",
    "grey",
}


@dataclass(frozen=True)
class DemoRequestError(ValueError):
    message: str
    code: str = "demo_capability_denied"
    field: str | None = None

    def payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error": self.message,
            "error_code": self.code,
            "product": "shokk-demo",
        }
        if self.field:
            result["field"] = self.field
        return result


def _is_active(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in NONE_SENTINELS
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    if isinstance(value, (int, float)):
        return value != 0
    return True


def _finish_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.lower() in NONE_SENTINELS:
        return None
    lowered = normalized.lower()
    if lowered.startswith("mono:") or lowered.startswith("base:"):
        normalized = normalized[5:]
    return normalized or None


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _number(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _normalize_base_spec_strength(zone: dict[str, Any], index: int) -> None:
    """Canonicalize ratio or legacy percentage input to the 0.0-3.0 renderer ratio."""

    aliases = [
        (key, zone[key])
        for key in ("base_spec_strength", "baseSpecStrength")
        if key in zone and zone[key] is not None
    ]
    if not aliases:
        zone["base_spec_strength"] = 1.0
        return

    normalized: list[float] = []
    for key, raw in aliases:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise DemoRequestError(
                "Spec Strength must be a number from 0% through 300%",
                "invalid_spec_strength",
                f"zones[{index}].{key}",
            ) from None
        if not math.isfinite(value):
            raise DemoRequestError(
                "Spec Strength must be finite",
                "invalid_spec_strength",
                f"zones[{index}].{key}",
            )
        # The shipped client sends ratios (1.0 = 100%, 3.0 = 300%).  Accept
        # older/direct clients that send UI percentages as well.
        if value > MAX_BASE_SPEC_STRENGTH_RATIO * 100.0:
            raise DemoRequestError(
                "Spec Strength cannot exceed 300%",
                "invalid_spec_strength",
                f"zones[{index}].{key}",
            )
        if value > MAX_BASE_SPEC_STRENGTH_RATIO:
            value /= 100.0
        normalized.append(max(0.0, min(MAX_BASE_SPEC_STRENGTH_RATIO, value)))
    if len(normalized) > 1 and not math.isclose(normalized[0], normalized[1]):
        raise DemoRequestError(
            "Spec Strength aliases disagree",
            "invalid_spec_strength",
            f"zones[{index}].base_spec_strength",
        )
    zone["base_spec_strength"] = normalized[0]
    zone.pop("baseSpecStrength", None)


def _looks_like_rgb(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return False
    try:
        return all(math.isfinite(float(value[index])) for index in range(3))
    except (TypeError, ValueError):
        return False


def _valid_color(value: Any) -> bool:
    if isinstance(value, Mapping):
        value = value.get("color_rgb") or value.get("rgb") or value.get("color")
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in NAMED_COLOR_NAMES:
            return True
        if value.startswith("#"):
            value = value[1:]
        return len(value) in {3, 6} and all(char in "0123456789abcdefABCDEF" for char in value)
    return _looks_like_rgb(value)


def _normalized_color_candidates(
    value: Any,
    *,
    default_tolerance: float,
    field: str,
) -> list[dict[str, Any]]:
    if _looks_like_rgb(value) or isinstance(value, (str, Mapping)):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = list(value)
    else:
        values = []
    if not values:
        raise DemoRequestError("Colors coverage needs at least one picked color", "invalid_coverage", field)
    if len(values) > 64:
        raise DemoRequestError("Colors coverage is limited to 64 picked colors", "invalid_coverage", field)

    result: list[dict[str, Any]] = []
    for candidate in values:
        if isinstance(candidate, Mapping):
            color = candidate.get("color_rgb") or candidate.get("rgb") or candidate.get("color")
            tolerance = _number(candidate.get("tolerance"), default_tolerance)
        else:
            color = candidate
            tolerance = default_tolerance
        if not _valid_color(color):
            raise DemoRequestError("Coverage color is invalid", "invalid_coverage", field)
        result.append(
            {
                "color_rgb": color,
                "tolerance": max(0.0, min(441.7, tolerance)),
            }
        )
    return result


def _has_mask_restriction(zone: Mapping[str, Any]) -> bool:
    return any(
        _is_active(zone.get(key))
        for key in (
            "region_mask",
            "regionMask",
            "spatial_mask",
            "spatialMask",
            "source_layer_mask",
            "sourceLayerMask",
            "source_layer_masks",
            "sourceLayerMasks",
            "source_layer",
            "sourceLayer",
            "source_layers",
            "sourceLayers",
        )
    )


def _normalize_source_layer_restrictions(zone: dict[str, Any]) -> None:
    """Collect one-or-many source layer masks without broadening missing IDs.

    The paid frontend normally sends a pre-unioned ``source_layer_mask``.  The
    demo frontend may instead send each selected layer's RLE.  Runtime unions
    those masks, then intersects the union with the zone coverage.  A request
    that names source layers but supplies no resolvable mask is marked as an
    explicit empty restriction (fail closed instead of painting the canvas).
    """

    masks: list[Any] = []
    explicitly_restricted = False
    singular = next(
        (zone[key] for key in ("source_layer_mask", "sourceLayerMask") if _is_active(zone.get(key))),
        None,
    )
    if singular is not None:
        explicitly_restricted = True
        masks.append(singular)
    plural = next(
        (zone[key] for key in ("source_layer_masks", "sourceLayerMasks") if _is_active(zone.get(key))),
        None,
    )
    if plural is not None:
        explicitly_restricted = True
        if isinstance(plural, Sequence) and not isinstance(plural, (str, bytes)):
            masks.extend(plural)
        else:
            masks.append(plural)
    source_layers = next(
        (zone[key] for key in ("source_layers", "sourceLayers") if _is_active(zone.get(key))),
        None,
    )
    if source_layers is not None:
        explicitly_restricted = True
        if not isinstance(source_layers, Sequence) or isinstance(source_layers, (str, bytes)):
            source_layers = [source_layers]
        for item in source_layers:
            if not isinstance(item, Mapping):
                continue
            mask = _first(
                item,
                "mask",
                "rle",
                "source_layer_mask",
                "sourceLayerMask",
                "region_mask",
                "regionMask",
            )
            if mask is not None:
                masks.append(mask)
    zone["_demo_source_layer_restricted"] = explicitly_restricted
    zone["_demo_source_layer_masks"] = masks


def _validate_scope_mask(value: Any, field: str) -> int:
    if not isinstance(value, Mapping) or not isinstance(value.get("runs"), list):
        raise DemoRequestError(
            "Source layer scope needs an RLE source_layer_mask",
            "invalid_source_layer_scope",
            field,
        )
    try:
        width = int(value.get("width"))
        height = int(value.get("height"))
    except (TypeError, ValueError):
        raise DemoRequestError(
            "Source layer scope mask dimensions must be integers",
            "invalid_source_layer_scope",
            field,
        )
    pixels = width * height
    if width <= 0 or height <= 0 or pixels > MAX_SOURCE_LAYER_SCOPE_PIXELS:
        raise DemoRequestError(
            "Source layer scope mask dimensions are invalid",
            "invalid_source_layer_scope",
            field,
        )
    runs = value["runs"]
    if not runs or len(runs) > MAX_SOURCE_LAYER_SCOPE_RUNS:
        raise DemoRequestError(
            "Source layer scope RLE exceeds the demo limit",
            "source_layer_scope_too_large",
            field,
        )
    covered = 0
    for run in runs:
        if not isinstance(run, (list, tuple)) or len(run) != 2:
            raise DemoRequestError(
                "Source layer scope RLE runs must be [value, count] pairs",
                "invalid_source_layer_scope",
                field,
            )
        try:
            run_value = int(run[0])
            run_count = int(run[1])
        except (TypeError, ValueError):
            raise DemoRequestError(
                "Source layer scope RLE values must be integers",
                "invalid_source_layer_scope",
                field,
            )
        if run_value < 0 or run_value > 255 or run_count <= 0:
            raise DemoRequestError(
                "Source layer scope RLE contains an invalid run",
                "invalid_source_layer_scope",
                field,
            )
        covered += run_count
        if covered > pixels:
            raise DemoRequestError(
                "Source layer scope RLE exceeds its declared dimensions",
                "invalid_source_layer_scope",
                field,
            )
    if covered != pixels:
        raise DemoRequestError(
            "Source layer scope RLE does not cover its declared dimensions",
            "invalid_source_layer_scope",
            field,
        )
    return len(runs)


def _source_layer_scope_table(data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_table = _first(data, "source_layer_scopes", "sourceLayerScopes")
    if raw_table is None:
        return {}
    if not isinstance(raw_table, Mapping):
        raise DemoRequestError(
            "source_layer_scopes must be an object keyed by scope id",
            "invalid_source_layer_scopes",
            "source_layer_scopes",
        )
    if len(raw_table) > MAX_SOURCE_LAYER_SCOPES:
        raise DemoRequestError(
            f"source_layer_scopes is limited to {MAX_SOURCE_LAYER_SCOPES} entries",
            "too_many_source_layer_scopes",
            "source_layer_scopes",
        )

    table: dict[str, dict[str, Any]] = {}
    total_runs = 0
    total_rgb_chars = 0
    for raw_id, raw_scope in raw_table.items():
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise DemoRequestError(
                "Source layer scope ids must be non-empty text",
                "invalid_source_layer_scope_id",
                "source_layer_scopes",
            )
        scope_id = raw_id.strip()
        if len(scope_id) > MAX_SOURCE_LAYER_SCOPE_ID_LENGTH:
            raise DemoRequestError(
                f"Source layer scope ids are limited to {MAX_SOURCE_LAYER_SCOPE_ID_LENGTH} characters",
                "source_layer_scope_id_too_long",
                f"source_layer_scopes.{scope_id[:32]}",
            )
        if scope_id in table:
            raise DemoRequestError(
                f"Duplicate source layer scope id {scope_id!r}",
                "invalid_source_layer_scope_id",
                "source_layer_scopes",
            )
        if not isinstance(raw_scope, Mapping):
            raise DemoRequestError(
                f"Source layer scope {scope_id!r} must be an object",
                "invalid_source_layer_scope",
                f"source_layer_scopes.{scope_id}",
            )
        mask = raw_scope.get("source_layer_mask")
        total_runs += _validate_scope_mask(
            mask, f"source_layer_scopes.{scope_id}.source_layer_mask"
        )
        if total_runs > MAX_SOURCE_LAYER_SCOPE_RUNS:
            raise DemoRequestError(
                "Combined source layer scope RLE data exceeds the demo limit",
                "source_layer_scope_table_too_large",
                "source_layer_scopes",
            )
        sanitized: dict[str, Any] = {"source_layer_mask": mask}
        rgb_png = raw_scope.get("source_layer_rgb_png")
        if rgb_png is not None:
            if not isinstance(rgb_png, str):
                raise DemoRequestError(
                    "source_layer_rgb_png must be base64 text",
                    "invalid_source_layer_scope",
                    f"source_layer_scopes.{scope_id}.source_layer_rgb_png",
                )
            if len(rgb_png) > MAX_SOURCE_LAYER_RGB_CHARS:
                raise DemoRequestError(
                    "source_layer_rgb_png exceeds the demo limit",
                    "source_layer_scope_too_large",
                    f"source_layer_scopes.{scope_id}.source_layer_rgb_png",
                )
            total_rgb_chars += len(rgb_png)
            if total_rgb_chars > MAX_SOURCE_LAYER_TABLE_RGB_CHARS:
                raise DemoRequestError(
                    "Combined source layer RGB data exceeds the demo limit",
                    "source_layer_scope_table_too_large",
                    "source_layer_scopes",
                )
            sanitized["source_layer_rgb_png"] = rgb_png
        # Do not copy arbitrary scope properties into a render zone.  Only the
        # two reviewed data fields above cross this boundary.
        table[scope_id] = sanitized
    return table


def _resolve_source_layer_scope_reference(
    zone: dict[str, Any],
    table: Mapping[str, Mapping[str, Any]],
    index: int,
) -> None:
    raw_id = _first(zone, "source_layer_scope_id", "sourceLayerScopeId")
    if not _is_active(raw_id):
        return
    field = f"zones[{index}].source_layer_scope_id"
    if not isinstance(raw_id, str):
        raise DemoRequestError(
            "source_layer_scope_id must be text",
            "invalid_source_layer_scope_ref",
            field,
        )
    scope_id = raw_id.strip()
    if not scope_id or len(scope_id) > MAX_SOURCE_LAYER_SCOPE_ID_LENGTH:
        raise DemoRequestError(
            "source_layer_scope_id is invalid",
            "invalid_source_layer_scope_ref",
            field,
        )
    scope = table.get(scope_id)
    if scope is None:
        raise DemoRequestError(
            f"Source layer scope {scope_id!r} was not supplied",
            "source_layer_scope_not_found",
            field,
        )

    # A table reference is authoritative.  Remove inline aliases so a stale or
    # modified client cannot mix a different mask/RGB source with the id.
    for key in (
        "source_layer_mask",
        "sourceLayerMask",
        "source_layer_masks",
        "sourceLayerMasks",
        "source_layer_rgb_png",
        "sourceLayerRgbPng",
        "source_layer_rgb",
        "sourceLayerRgb",
    ):
        zone.pop(key, None)
    zone["source_layer_mask"] = scope["source_layer_mask"]
    if "source_layer_rgb_png" in scope:
        zone["source_layer_rgb_png"] = scope["source_layer_rgb_png"]
    zone["source_layer_scope_id"] = scope_id
    zone["_demo_source_layer_scope_id"] = scope_id


def _normalize_coverage(zone: dict[str, Any], index: int) -> bool:
    """Normalize the new Coverage control and legacy Pick/Remaining fields.

    Returns ``False`` for a five-zone placeholder with no selected coverage.
    A drawn/source-layer mask is itself an apply area, so a legacy ``none``
    color with one of those masks means "everything inside the mask".
    """

    field = f"zones[{index}].coverage"
    raw_mode = _first(zone, "coverage_mode", "coverageMode")
    legacy_mode = _first(zone, "color_mode", "colorMode")
    raw_color = zone.get("color")
    mask_restriction = _has_mask_restriction(zone)

    if raw_mode is not None:
        mode_key = str(raw_mode).strip().lower().replace(" ", "-")
        mode = COVERAGE_MODE_ALIASES.get(mode_key)
        if mode is None:
            raise DemoRequestError(
                f"Unsupported coverage mode {raw_mode!r}", "invalid_coverage_mode", field
            )
    elif isinstance(raw_color, str) and raw_color.strip().lower() == "remaining":
        mode = "remaining"
    elif isinstance(raw_color, str) and raw_color.strip().lower() in {"everything", "all"}:
        mode = "everything"
    elif legacy_mode is not None:
        legacy_key = str(legacy_mode).strip().lower().replace(" ", "-")
        if legacy_key == "special":
            mode = "remaining" if str(raw_color).strip().lower() == "remaining" else (
                "everything" if mask_restriction else "none"
            )
        else:
            mode = COVERAGE_MODE_ALIASES.get(legacy_key)
            if mode is None:
                raise DemoRequestError(
                    f"Unsupported coverage mode {legacy_mode!r}",
                    "invalid_coverage_mode",
                    field,
                )
    elif raw_color is not None:
        mode = "colors"
    else:
        mode = "everything" if mask_restriction else "none"

    if mode == "remaining":
        zone["color"] = "remaining"
    elif mode == "everything":
        zone["color"] = "everything"
    elif mode == "colors":
        candidates = _first(zone, "coverage_colors", "coverageColors", "colors")
        if not _is_active(candidates):
            candidates = raw_color
        if not _is_active(candidates) and str(legacy_mode or "").strip().lower() == "picker":
            candidates = _first(zone, "picker_color", "pickerColor")
        tolerance = _number(
            _first(
                zone,
                "coverage_tolerance",
                "coverageTolerance",
                "picker_tolerance",
                "pickerTolerance",
                "tolerance",
            ),
            40.0,
        )
        zone["color"] = _normalized_color_candidates(
            candidates, default_tolerance=tolerance, field=field
        )
    elif mask_restriction:
        mode = "everything"
        zone["color"] = "everything"
    else:
        zone["_demo_coverage_mode"] = "none"
        return False
    zone["_demo_coverage_mode"] = mode
    return True


def _normalize_base_color_mode(zone: dict[str, Any], index: int) -> str:
    raw_mode = _first(zone, "base_color_mode", "baseColorMode")
    # Legacy direct API requests supplied base_color without a mode.  Keep that
    # compatibility while making the new-zone default explicitly finish-own.
    if raw_mode is None:
        raw_mode = "solid" if _first(zone, "base_color", "baseColor") is not None else "finish"
    key = str(raw_mode).strip().lower().replace(" ", "-")
    mode = BASE_COLOR_MODE_ALIASES.get(key)
    if mode is None:
        raise DemoRequestError(
            f"Unsupported base color mode {raw_mode!r}",
            "invalid_base_color_mode",
            f"zones[{index}].base_color_mode",
        )
    zone["base_color_mode"] = mode
    return mode


def _normalize_gradient(zone: dict[str, Any], index: int) -> None:
    raw_stops = _first(zone, "gradient_stops", "gradientStops")
    field = f"zones[{index}].gradient_stops"
    if not isinstance(raw_stops, Sequence) or isinstance(raw_stops, (str, bytes)):
        raise DemoRequestError("Custom gradient needs at least two stops", "invalid_gradient", field)
    if len(raw_stops) < 2 or len(raw_stops) > 16:
        raise DemoRequestError(
            "Custom gradient needs between 2 and 16 stops", "invalid_gradient", field
        )
    stops: list[dict[str, Any]] = []
    for stop in raw_stops:
        if not isinstance(stop, Mapping):
            raise DemoRequestError("Gradient stops must be objects", "invalid_gradient", field)
        position = _number(_first(stop, "pos", "position", "offset"), math.nan)
        color = _first(stop, "color", "color_rgb", "rgb")
        if not math.isfinite(position) or not _valid_color(color):
            raise DemoRequestError("Gradient stop is invalid", "invalid_gradient", field)
        if position > 1.0:
            position /= 100.0
        stops.append({"pos": max(0.0, min(1.0, position)), "color": color})
    stops.sort(key=lambda item: item["pos"])
    direction = str(
        _first(zone, "gradient_direction", "gradientDirection", default="horizontal")
    ).strip().lower().replace("-", "_").replace(" ", "_")
    direction_aliases = {
        "diagonal": "diagonal_down",
        "diagonal_reverse": "diagonal_up",
        "diagonal_upward": "diagonal_up",
    }
    direction = direction_aliases.get(direction, direction)
    if direction not in GRADIENT_DIRECTIONS:
        raise DemoRequestError(
            f"Unsupported gradient direction {direction!r}", "invalid_gradient", field
        )
    zone["gradient_stops"] = stops
    zone["gradient_direction"] = direction


def validate_render_request(data: Any, allowlist: set[str] | frozenset[str]) -> list[dict[str, Any]]:
    """Validate and return zone objects without mutating caller data.

    The demo never silently discards paid-product payload fields.  A forbidden
    feature gets an explicit 400 response so a stale or modified client cannot
    accidentally widen the shipped product surface.
    """

    if not isinstance(data, Mapping):
        raise DemoRequestError("Request body must be a JSON object", "invalid_request")
    zones = data.get("zones")
    if not isinstance(zones, Sequence) or isinstance(zones, (str, bytes)) or not zones:
        raise DemoRequestError("At least one zone is required", "invalid_zones", "zones")
    if len(zones) > 64:
        raise DemoRequestError("Zone count exceeds the SHOKK DEMO limit of 64", "too_many_zones")
    source_layer_scopes = _source_layer_scope_table(data)

    # Top-level spec/pattern import and authoring paths are not part of the demo.
    for field in (
        "pattern",
        "pattern_stack",
        "patternStack",
        "spec_pattern_stack",
        "specPatternStack",
        "import_spec_map",
        "importSpecMap",
        "spec_stack",
        "specStack",
        "material_stack",
        "materialStack",
    ):
        if _is_active(data.get(field)):
            raise DemoRequestError(f"{field} is unavailable in SHOKK DEMO", field=field)

    checked: list[dict[str, Any]] = []
    for index, raw_zone in enumerate(zones):
        if not isinstance(raw_zone, Mapping):
            raise DemoRequestError(
                f"Zone {index + 1} must be an object", "invalid_zone", f"zones[{index}]"
            )
        zone = dict(raw_zone)
        _resolve_source_layer_scope_reference(zone, source_layer_scopes, index)

        pattern = zone.get("pattern")
        if _is_active(pattern):
            raise DemoRequestError(
                "Regular patterns are unavailable in SHOKK DEMO",
                field=f"zones[{index}].pattern",
            )
        if _is_active(_first(zone, "pattern_stack", "patternStack")):
            raise DemoRequestError(
                "Pattern stacks are unavailable in SHOKK DEMO",
                field=f"zones[{index}].pattern_stack",
            )
        if _is_active(_first(zone, "material_stack", "materialStack")):
            raise DemoRequestError(
                "Finish stacks are unavailable in SHOKK DEMO",
                field=f"zones[{index}].material_stack",
            )

        for field in SPEC_STACK_KEYS:
            if _is_active(zone.get(field)):
                raise DemoRequestError(
                    "SPEC patterns are unavailable in SHOKK DEMO",
                    field=f"zones[{index}].{field}",
                )

        for key, value in zone.items():
            lowered = str(key).lower().replace("-", "_")
            compact = lowered.replace("_", "")
            if (
                lowered.startswith(EXTRA_BASE_PREFIXES)
                or compact.startswith(("secondbase", "thirdbase", "fourthbase", "fifthbase"))
            ) and _is_active(value):
                raise DemoRequestError(
                    "Second through fifth base overlays are unavailable in SHOKK DEMO",
                    field=f"zones[{index}].{key}",
                )
        if _is_active(_first(zone, "base_overlays", "baseOverlays")) or _is_active(
            _first(zone, "extra_base_overlays", "extraBaseOverlays")
        ):
            raise DemoRequestError(
                "Extra base overlays are unavailable in SHOKK DEMO",
                field=f"zones[{index}].base_overlays",
            )
        if _is_active(_first(zone, "blend_base", "blendBase")):
            raise DemoRequestError(
                "Blended secondary bases are unavailable in SHOKK DEMO",
                field=f"zones[{index}].blend_base",
            )

        selected: list[tuple[str, Any]] = [
            ("finish", zone.get("finish")),
            ("finish_id", zone.get("finish_id")),
            ("finishId", zone.get("finishId")),
            ("base", zone.get("base")),
            ("monolithic", zone.get("monolithic")),
            ("base_material", zone.get("base_material")),
            ("baseMaterial", zone.get("baseMaterial")),
            ("material_id", zone.get("material_id")),
            ("materialId", zone.get("materialId")),
        ]
        resolved: list[str] = []
        for field, value in selected:
            if _is_active(value) and not isinstance(value, str):
                raise DemoRequestError(
                    f"Zone {index + 1} finish id must be text",
                    "invalid_finish",
                    f"zones[{index}].{field}",
                )
            finish_id = _finish_id(value)
            if finish_id is None:
                continue
            if finish_id not in allowlist:
                raise DemoRequestError(
                    f"Finish {finish_id!r} is not included in SHOKK DEMO",
                    "finish_not_allowed",
                    f"zones[{index}].{field}",
                )
            resolved.append(finish_id)
        if len(set(resolved)) > 1:
            raise DemoRequestError(
                f"Zone {index + 1} selects multiple finishes",
                "finish_stack_not_allowed",
                f"zones[{index}]",
            )

        raw_color_source = _first(
            zone,
            "base_color_source",
            "baseColorSource",
            "color_finish",
            "colorFinish",
            "special_source",
            "specialSource",
        )
        color_finish_id = _finish_id(raw_color_source)
        if _is_active(raw_color_source) and color_finish_id is None:
            raise DemoRequestError(
                "Base color source must be a finish id",
                "invalid_color_source",
                f"zones[{index}].base_color_source",
            )
        if color_finish_id is not None and color_finish_id not in allowlist:
            raise DemoRequestError(
                f"Finish {color_finish_id!r} is not included in SHOKK DEMO",
                "finish_not_allowed",
                f"zones[{index}].base_color_source",
            )

        # The paid app ships five rows by default: four intentionally empty
        # setup slots plus the Everything Else fallback.  Accept those rows as
        # payload placeholders rather than turning them into finish errors.
        if not resolved:
            continue
        if zone.get("muted") is True or zone.get("enabled") is False:
            continue

        _normalize_source_layer_restrictions(zone)
        if not _normalize_coverage(zone, index):
            continue

        mode = _normalize_base_color_mode(zone, index)
        if mode == "special" and color_finish_id is None:
            # The picker opens in two UI steps: select From Special, then pick
            # its source.  Keep live preview healthy during that brief empty
            # state by showing the material's own paint for this render.
            zone["_demo_requested_base_color_mode"] = "special"
            zone["base_color_mode"] = "finish"
            mode = "finish"
        if color_finish_id is not None:
            zone["_demo_color_finish_id"] = color_finish_id
        if mode == "solid" and not _valid_color(_first(zone, "base_color", "baseColor")):
            raise DemoRequestError(
                "Solid base color is invalid",
                "invalid_base_color",
                f"zones[{index}].base_color",
            )
        if mode == "gradient":
            _normalize_gradient(zone, index)

        _normalize_base_spec_strength(zone, index)

        zone["_demo_finish_id"] = resolved[0]
        # Retain only the original priority number for the post-render recipe.
        # Empty setup rows are intentionally omitted from rendering, but an
        # active "Everything Else" row must still read as Zone 5, not Zone 1.
        zone["_demo_source_index"] = index
        checked.append(zone)
    if not checked:
        raise DemoRequestError(
            "At least one active zone with coverage and a demo finish is required",
            "invalid_zones",
            "zones",
        )
    return checked
