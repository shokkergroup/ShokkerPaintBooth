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


def test_pass_125_locked_effects_dialog_is_read_only_and_explained():
    body = _function_body("openLayerEffects")
    assert "var locked = !!layer.locked" in body
    assert "'.fx-section input, .fx-section select'" in body
    assert "control.disabled = locked" in body
    assert "Layer is locked — unlock it to edit or clear effects." in body
    assert 'id="layerEffectsLockNotice" role="status"' in HTML


def test_pass_125_clear_all_disabled_for_locked_or_empty_layer():
    body = _function_body("openLayerEffects")
    assert "clearButton.disabled = locked || !layer.effects" in body
    assert "data-layer-effects-clear" in HTML
    assert "This Layer has no effects to clear" in body


def test_pass_125_runtime_is_cache_busted():
    assert "spb93-effects-lock-readonly-20260717" in HTML
    assert "spb93-layer-blend-refusal-20260717" in HTML
