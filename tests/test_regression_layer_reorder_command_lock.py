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


def test_pass_129_move_commands_refuse_locked_layer_before_history_or_swap():
    for name, history_text in (("moveLayerUp", "move up"), ("moveLayerDown", "move down")):
        body = _function_body(name)
        lock = body.index("if (layer.locked)")
        history = body.index(f"_pushLayerStackUndo('{history_text}')")
        swap = body.index("[_psdLayers[idx], _psdLayers[idx")
        assert lock < history < swap
        assert "unlock to reorder" in body
        assert "return false" in body[:history]


def test_pass_129_move_commands_report_success_and_boundary_no_op():
    up = _function_body("moveLayerUp")
    down = _function_body("moveLayerDown")
    assert "idx < 0 || idx >= _psdLayers.length - 1) return false" in up
    assert "if (idx <= 0) return false" in down
    assert up.rstrip().endswith("return true;")
    assert down.rstrip().endswith("return true;")


def test_pass_129_runtime_is_cache_busted():
    assert "spb93-layer-reorder-command-lock-20260717" in HTML
    assert "spb93-layer-reorder-identity-20260717" in HTML
