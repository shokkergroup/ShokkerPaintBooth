"""PSD import routes compatible with the Paint Booth layer client."""

from __future__ import annotations

import io
from pathlib import Path
import time
from typing import Any, Callable, Iterator
import uuid

from flask import Blueprint, current_app, jsonify, request

from .images import png_data_url


PSD_EXTENSIONS = {".psd", ".psb"}


def _is_group(layer: Any) -> bool:
    checker = getattr(layer, "is_group", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception:
            pass
    return getattr(layer, "kind", None) == "group"


def _name(layer: Any) -> str:
    value = getattr(layer, "name", None)
    return str(value) if value not in (None, "") else "Layer"


def _blend_mode(layer: Any) -> str:
    return str(getattr(layer, "blend_mode", "NORMAL")).replace("BlendMode.", "")


def _bbox(layer: Any, width: int, height: int) -> list[int]:
    try:
        return [int(part) for part in getattr(layer, "bbox")]
    except (TypeError, ValueError, AttributeError):
        return [0, 0, int(width), int(height)]


def _layer_key(index_path: tuple[int, ...]) -> str:
    return ".".join(str(index) for index in index_path)


def build_layer_tree(container: Any, width: int, height: int) -> list[dict[str, Any]]:
    def walk(
        node: Any,
        index_prefix: tuple[int, ...] = (),
        name_prefix: tuple[str, ...] = (),
        parent_visible: bool = True,
        group_chain: tuple[dict[str, Any], ...] = (),
    ) -> list[dict[str, Any]]:
        result = []
        for index, layer in enumerate(node):
            index_path = index_prefix + (index,)
            name = _name(layer)
            name_path = name_prefix + (name,)
            own_visible = bool(getattr(layer, "visible", True))
            effective_visible = bool(parent_visible and own_visible)
            entry: dict[str, Any] = {
                "layer_key": _layer_key(index_path),
                "name": name,
                "path": "/".join(name_path),
                "path_parts": list(name_path),
                "kind": getattr(layer, "kind", "pixel"),
                "visible": own_visible,
                "effective_visible": effective_visible,
                "opacity": int(getattr(layer, "opacity", 255)),
                "bbox": _bbox(layer, width, height),
                "blend_mode": _blend_mode(layer),
                "clipping": bool(getattr(layer, "clipping", False)),
            }
            if _is_group(layer):
                entry["group_mode"] = (
                    "pass-through"
                    if _blend_mode(layer).strip().upper().replace("-", "_") == "PASS_THROUGH"
                    else "isolated"
                )
                descriptor = {
                    key: entry[key]
                    for key in (
                        "layer_key",
                        "name",
                        "path",
                        "path_parts",
                        "visible",
                        "effective_visible",
                        "opacity",
                        "blend_mode",
                        "clipping",
                        "group_mode",
                    )
                }
                entry["children"] = walk(
                    layer,
                    index_path,
                    name_path,
                    effective_visible,
                    group_chain + (descriptor,),
                )
            else:
                entry["has_pixels"] = True
                entry["group_chain"] = [dict(group) for group in group_chain]
                entry["parent_group_key"] = group_chain[-1]["layer_key"] if group_chain else None
            result.append(entry)
        return result

    return walk(container)


def iter_leaf_layers(container: Any) -> Iterator[tuple[dict[str, Any], Any]]:
    def walk(
        node: Any,
        index_prefix: tuple[int, ...] = (),
        name_prefix: tuple[str, ...] = (),
        parent_visible: bool = True,
        group_chain: tuple[dict[str, Any], ...] = (),
    ) -> Iterator[tuple[dict[str, Any], Any]]:
        for index, layer in enumerate(node):
            index_path = index_prefix + (index,)
            name = _name(layer)
            name_path = name_prefix + (name,)
            own_visible = bool(getattr(layer, "visible", True))
            effective_visible = bool(parent_visible and own_visible)
            if _is_group(layer):
                descriptor = {
                    "layer_key": _layer_key(index_path),
                    "name": name,
                    "path": "/".join(name_path),
                    "path_parts": list(name_path),
                    "visible": own_visible,
                    "effective_visible": effective_visible,
                    "opacity": int(getattr(layer, "opacity", 255)),
                    "blend_mode": _blend_mode(layer),
                    "clipping": bool(getattr(layer, "clipping", False)),
                    "group_mode": (
                        "pass-through"
                        if _blend_mode(layer).strip().upper().replace("-", "_") == "PASS_THROUGH"
                        else "isolated"
                    ),
                }
                yield from walk(
                    layer,
                    index_path,
                    name_path,
                    effective_visible,
                    group_chain + (descriptor,),
                )
                continue
            yield {
                "layer_key": _layer_key(index_path),
                "name": name,
                "path": "/".join(name_path),
                "path_parts": list(name_path),
                "visible": own_visible,
                "effective_visible": effective_visible,
                "opacity": int(getattr(layer, "opacity", 255)),
                "blend_mode": _blend_mode(layer),
                "clipping": bool(getattr(layer, "clipping", False)),
                "group_chain": [dict(group) for group in group_chain],
                "parent_group_key": group_chain[-1]["layer_key"] if group_chain else None,
            }, layer

    yield from walk(container)


class PsdCache:
    def __init__(self) -> None:
        self._key: tuple[str, int] | None = None
        self._value: Any = None

    def open(self, path: Path) -> Any:
        try:
            from psd_tools import PSDImage
        except ImportError as exc:
            raise RuntimeError("psd-tools is required for PSD import") from exc
        key = (str(path), path.stat().st_mtime_ns)
        if key != self._key:
            self._value = PSDImage.open(path)
            self._key = key
        return self._value


def create_psd_blueprint(
    *,
    resolve_source_path: Callable[[str], Path],
    upload_dir: Path,
) -> Blueprint:
    blueprint = Blueprint("demo_psd", __name__)
    cache = PsdCache()

    def resolve_psd(raw: str) -> Path:
        path = resolve_source_path(raw)
        if path.suffix.lower() not in PSD_EXTENSIONS:
            raise ValueError("Only .psd and .psb files are allowed")
        if not path.is_file():
            raise FileNotFoundError("PSD file not found")
        return path

    @blueprint.post("/api/psd-import")
    def psd_import():
        started = time.perf_counter()
        try:
            uploaded = request.files.get("file") or request.files.get("psd_file") or request.files.get("paint_file")
            if uploaded is not None and uploaded.filename:
                suffix = Path(uploaded.filename).suffix.lower()
                if suffix not in PSD_EXTENSIONS:
                    return jsonify({"error": "Only .psd and .psb files are allowed"}), 400
                upload_dir.mkdir(parents=True, exist_ok=True)
                path = upload_dir / f"demo_psd_{uuid.uuid4().hex}{suffix}"
                uploaded.save(path)
            else:
                data = request.get_json(silent=True) or {}
                if not isinstance(data, dict):
                    return jsonify({"error": "Request body must be a JSON object"}), 400
                path = resolve_psd(str(data.get("psd_path") or data.get("paint_file") or ""))
            psd = cache.open(path)
            composite = psd.composite()
            return jsonify(
                {
                    "success": True,
                    "width": int(psd.width),
                    "height": int(psd.height),
                    "layers": build_layer_tree(psd, psd.width, psd.height),
                    "composite": png_data_url(composite.convert("RGBA")) if composite else None,
                    "psd_path": str(path),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                }
            )
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            current_app.logger.exception("PSD import failed")
            return jsonify({"error": str(exc)}), 500

    @blueprint.post("/api/psd-rasterize-all")
    def psd_rasterize_all():
        started = time.perf_counter()
        try:
            data = request.get_json(silent=True) or {}
            path = resolve_psd(str(data.get("psd_path") or ""))
            psd = cache.open(path)
            result: dict[str, Any] = {}
            for metadata, layer in iter_leaf_layers(psd):
                try:
                    image = layer.composite(force=True)
                    if image is None or image.width <= 0 or image.height <= 0:
                        continue
                    result[metadata["layer_key"]] = {
                        "image": png_data_url(image.convert("RGBA")),
                        "bbox": _bbox(layer, psd.width, psd.height),
                        "size": [image.width, image.height],
                        **metadata,
                    }
                except Exception:
                    current_app.logger.warning("Skipping PSD layer %s", metadata["layer_key"])
            return jsonify(
                {
                    "success": True,
                    "layers": result,
                    "count": len(result),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                }
            )
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            current_app.logger.exception("PSD rasterization failed")
            return jsonify({"error": str(exc)}), 500

    @blueprint.post("/api/psd-layer")
    def psd_layer():
        try:
            data = request.get_json(silent=True) or {}
            path = resolve_psd(str(data.get("psd_path") or ""))
            psd = cache.open(path)
            selected = None
            requested_key = str(data.get("layer_key") or "").strip()
            if requested_key:
                selected = next(
                    (layer for metadata, layer in iter_leaf_layers(psd) if metadata["layer_key"] == requested_key),
                    None,
                )
            else:
                current: Any = psd
                for name in data.get("layer_path", []):
                    current = next((child for child in current if _name(child) == str(name)), None)
                    if current is None:
                        break
                selected = current if current is not psd else None
            if selected is None:
                return jsonify({"error": "Layer not found"}), 404
            image = selected.composite(force=True)
            if image is None:
                return jsonify({"error": "Layer could not be rasterized"}), 500
            return jsonify(
                {
                    "success": True,
                    "image": png_data_url(image.convert("RGBA")),
                    "size": [image.width, image.height],
                    "bbox": _bbox(selected, psd.width, psd.height),
                }
            )
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            current_app.logger.exception("PSD layer rasterization failed")
            return jsonify({"error": str(exc)}), 500

    return blueprint

