from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, f"missing {name}"
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_96_selection_helper_does_not_disable_layer_mode():
    body = _function_body("_activeSelectionMask")
    assert "isLayerPaintMode" not in body
    assert "regionMask.length !== expectedLength" in body
    assert "return regionMask" in body


def test_pass_96_layer_surface_and_selection_share_canvas_coordinates():
    body = _function_body("_initLayerPaintCanvas")
    assert "_activeLayerCanvas.width = pc.width" in body
    assert "_activeLayerCanvas.height = pc.height" in body
    assert "getImageData(0, 0, pc.width, pc.height)" in body


def test_pass_96_every_pixel_brush_uses_the_shared_selection_gate():
    required = {
        "paintCloneStroke": "const selection = _activeSelectionMask(w, h)",
        "paintColorBrush": "const _rmask = _activeSelectionMask(w, h)",
        "paintRecolor": "const _rmask = _activeSelectionMask(w, h)",
        "paintSmudge": "const _rmask = _activeSelectionMask(w, h)",
        "paintPencil": "const _rmask = _activeSelectionMask(w, h)",
        "_paintDodgeBurn": "const _rmask = _activeSelectionMask(w, h)",
        "paintBlurBrush": "const _rmask = _activeSelectionMask(w, h)",
        "paintSharpenBrush": "const _rmask = _activeSelectionMask(w, h)",
        "paintHistoryBrush": "const selection = _activeSelectionMask(w, h)",
    }
    for function_name, contract in required.items():
        assert contract in _function_body(function_name), function_name
    healing = (ROOT / "js/canvas/layer/healing-brush.js").read_text(encoding="utf-8")
    assert "_activeSelectionMask(w, h)" in healing


def test_pass_96_fill_gradient_and_delayed_fill_intent_use_selection():
    assert "const selectionMask = paintCanvas ? _activeSelectionMask" in _function_body("fillGradientOnLayer")
    assert "_getLayerFillSelectionFingerprint()" in _function_body("_getLayerFillIntentKey")
    assert "? _activeSelectionMask(paintCanvas.width, paintCanvas.height)" in _function_body("fillBucketOnLayer")


def test_pass_96_runtime_is_cache_busted():
    assert "spb93-layer-selection-clip-20260717" in HTML
    assert "spb93-fill-selection-clip-20260717" in HTML
