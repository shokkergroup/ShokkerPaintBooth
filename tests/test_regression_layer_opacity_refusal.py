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


def test_pass_123_layer_opacity_normalizes_before_history_and_mutation():
    body = _function_body("setLayerOpacity")
    finite = body.index("Number.isFinite(parsedPct)")
    clamp = body.index("Math.max(0, Math.min(100, Math.round(parsedPct)))")
    history = body.index("_pushLayerStackUndo(`opacity")
    mutation = body.index("target.opacity = newOpacity")
    assert finite < clamp < history < mutation
    assert "const pct =" in body


def test_pass_123_locked_refusal_restores_visible_control_state():
    setter = _function_body("setLayerOpacity")
    preflight = _function_body("_preflightLayerOpacityTargets")
    assert "targets.filter(layer => layer.locked)" in preflight
    assert "_syncLayerOpacityControls(layer.id, pct)" in preflight
    assert "showToast('Opacity unchanged:" in preflight
    assert "return null" in preflight
    assert setter.index("_preflightLayerOpacityTargets(id)") < setter.index("_pushLayerStackUndo(`opacity")


def test_pass_123_success_syncs_the_applied_normalized_value():
    body = _function_body("setLayerOpacity")
    assert "_syncLayerOpacityControls(target.id, pct)" in body
    assert "Math.round(pctValue)" not in body


def test_pass_123_runtime_is_cache_busted():
    assert "spb93-layer-opacity-refusal-20260717" in HTML
    assert "spb93-dynamics-slider-commit-20260717" in HTML
