"""SPB-93 Pass 137: picked-element commits retain the full Layer surface."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.end(), 1, match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_137_activation_keeps_image_dimensions_separate_from_element_box():
    activate = _function_body("activateLayerTransform")
    assert "origImageW: Number(layer.img && (layer.img.naturalWidth || layer.img.width)) || sw" in activate
    assert "origImageH: Number(layer.img && (layer.img.naturalHeight || layer.img.height)) || sh" in activate
    assert "freeTransformState.origBoxW = freeTransformState.boxW" in activate
    # The glyph box may change; the full image dimensions must never be reassigned.
    assert "freeTransformState.origImageW =" not in activate
    assert "freeTransformState.origImageH =" not in activate


def test_pass_137_element_commit_uses_full_image_dimensions_for_destination_and_clamps():
    commit = _function_body("commitLayerTransform")
    assert "const origFullW = s.origImageW" in commit
    assert "const origFullH = s.origImageH" in commit
    assert "const layerW = s.origImageW" in commit
    assert "const layerH = s.origImageH" in commit
    assert "const origFullW = s.origBoxW" not in commit
    assert "const layerW = s.origBoxW" not in commit


def test_pass_137_runtime_is_cache_busted_and_mirrored():
    assert "spb93-element-full-surface-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
