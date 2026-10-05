from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
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


def test_pass_100_sample_size_is_visible_for_eyedropper():
    mode_contract = CANVAS[CANVAS.index("// Wand/Eyedropper sample size") : CANVAS.index("// Selection feather", CANVAS.index("// Wand/Eyedropper sample size"))]
    assert "showWandExtras || mode === 'eyedropper'" in mode_contract
    assert "alpha-aware average around the cursor" in mode_contract
    assert "wandAntiAliasEl.style.display = showWandExtras" in mode_contract


def test_pass_100_every_primary_pick_route_uses_average_sampler():
    handler = CANVAS[CANVAS.index("function setupCanvasHandlers") : CANVAS.index("// ─────────────────────────────────────────────────────────────────────────\n    // [11] MAGIC WAND", CANVAS.index("function setupCanvasHandlers"))]
    assert handler.count("window.sampleEyedropperPixel(pos.x, pos.y)") >= 4
    assert "sampleLayerColorAt(srcLayer, pos.x, pos.y)" in handler
    assert "No visible color at this sample" in handler


def test_pass_100_layer_sampler_is_alpha_weighted_and_offset_aware():
    body = _function_body("sampleLayerColorAt")
    assert "getEyedropperSampleSize()" in body
    assert "getLayerCanvasOrigin(layer)" in body
    assert "pixels[i] * alpha" in body
    assert "red / alphaWeight" in body
    assert "alphaWeight > 0" in body


def test_pass_100_composite_sampler_ignores_transparent_rgb():
    start = CANVAS.index("window.sampleEyedropperPixel = function sampleEyedropperPixel")
    body = CANVAS[start : CANVAS.index("\n    };", start) + 7]
    assert "_spbCompositePickBuffer() : paintImageData" in body
    assert "_pid.data[idx + 3] === 0" in body
    assert "_pid.data[pi] * alpha" in body
    assert "alphaWeight > 0" in body
    assert "[1, 3, 5, 11]" in body


def test_pass_100_setter_and_shared_control_support_11x11():
    setter_start = CANVAS.index("window.setEyedropperSampleSize")
    setter = CANVAS[setter_start : CANVAS.index("window.sampleEyedropperPixel", setter_start)]
    assert "[1, 3, 5, 11]" in setter
    assert "select.value = String(n)" in setter


def test_pass_100_runtime_is_cache_busted():
    assert "spb93-eyedropper-sample-truth-20260717" in HTML
    assert "spb93-layer-transform-transactions-20260717" in HTML
