"""Hierarchy-safe PSD tree identities shared by import and rasterization.

Layer names are presentation text, not identifiers: PSDs may contain duplicate
names and arbitrarily deep groups.  Positional keys remain stable across the
two reads of the same cached document and cannot collide on slashes or names.
"""

from __future__ import annotations
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


def _is_group(layer) -> bool:
    checker = getattr(layer, "is_group", None)
    if callable(checker):
        try:
            return bool(checker())
        except Exception as _spb_ex:
            _spb_swallow('_is_group@L16', _spb_ex)
    return getattr(layer, "kind", None) == "group"


def _name(layer) -> str:
    value = getattr(layer, "name", None)
    return str(value) if value not in (None, "") else "Layer"


def _blend_mode(layer) -> str:
    value = getattr(layer, "blend_mode", "NORMAL")
    return str(value).replace("BlendMode.", "")


def _group_mode(layer) -> str:
    """Return the PSD compositing boundary carried by a group node."""

    value = _blend_mode(layer).strip().upper().replace("-", "_").replace(" ", "_")
    return "pass-through" if value == "PASS_THROUGH" else "isolated"


def _bbox(layer, width: int, height: int) -> list[int]:
    value = getattr(layer, "bbox", None)
    try:
        return [int(part) for part in value]
    except (TypeError, ValueError):
        return [0, 0, int(width), int(height)]


def _layer_key(index_path: tuple[int, ...]) -> str:
    return ".".join(str(index) for index in index_path)


def build_layer_tree(container, width: int, height: int) -> list[dict]:
    """Serialize a PSD tree with collision-free identities and full ancestry."""

    def walk(
        node,
        index_prefix=(),
        name_prefix=(),
        parent_visible=True,
        group_chain=(),
    ):
        result = []
        for index, layer in enumerate(node):
            index_path = index_prefix + (index,)
            name = _name(layer)
            name_path = name_prefix + (name,)
            own_visible = bool(getattr(layer, "visible", True))
            effective_visible = bool(parent_visible and own_visible)
            entry = {
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
                entry["group_mode"] = _group_mode(layer)
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
                entry["parent_group_key"] = (
                    group_chain[-1]["layer_key"] if group_chain else None
                )
            result.append(entry)
        return result

    return walk(container)


def iter_leaf_layers(container):
    """Yield ``(metadata, layer)`` for every leaf in deterministic PSD order."""

    def walk(
        node,
        index_prefix=(),
        name_prefix=(),
        parent_visible=True,
        group_chain=(),
    ):
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
                    "group_mode": _group_mode(layer),
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
                "parent_group_key": (
                    group_chain[-1]["layer_key"] if group_chain else None
                ),
            }, layer

    yield from walk(container)
