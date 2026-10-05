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


def test_pass_124_blend_control_is_addressable_and_accessible():
    assert 'data-layer-blend-control="${l.id}" aria-label="Layer blend mode"' in CANVAS
    helper = _function_body("_syncLayerBlendModeControls")
    assert "data-layer-blend-control" in helper
    assert "el.value = applied" in helper


def test_pass_124_invalid_and_locked_modes_roll_back_before_history():
    body = _function_body("setLayerBlendMode")
    allowed = body.index("allowedModes")
    invalid = body.index("if (!allowedModes.includes(requestedMode))")
    lock = body.index("if (layer.locked)")
    history = body.index("_pushLayerStackUndo(`blend")
    mutation = body.index("layer.blendMode = requestedMode")
    assert allowed < invalid < lock < history < mutation
    assert body.count("_syncLayerBlendModeControls") >= 4


def test_pass_124_blend_setter_returns_truthful_result():
    body = _function_body("setLayerBlendMode")
    assert body.count("return false") >= 3
    assert body.count("return true") >= 2
    assert "Unsupported layer blend mode" in body


def test_pass_124_runtime_is_cache_busted():
    assert "spb93-layer-blend-refusal-20260717" in HTML
    assert "spb93-layer-opacity-refusal-20260717" in HTML
