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


def test_pass_119_locked_delete_is_a_true_no_op():
    body = _function_body("deleteLayer")
    lock = body.index("if (targetLayer && targetLayer.locked)")
    stroke_cancel = body.index("if (typeof isDrawing")
    history = body.index("_pushLayerStackUndo('delete layer')")
    removal = body.index("_psdLayers.splice(idx, 1)")
    assert lock < stroke_cancel < history < removal
    assert "unlock it before deleting" in body


def test_pass_119_delete_snapshots_before_clearing_zone_links():
    body = _function_body("deleteLayer")
    confirm = body.index("if (!confirm(_msg)) return")
    history = body.index("_pushLayerStackUndo('delete layer')")
    clear_link = body.index("_danglingZones.forEach")
    removal = body.index("_psdLayers.splice(idx, 1)")
    assert confirm < history < clear_link < removal


def test_pass_119_cancelled_delete_has_no_history_or_link_mutation():
    body = _function_body("deleteLayer")
    confirm = body.index("if (!confirm(_msg)) return")
    history = body.index("_pushLayerStackUndo('delete layer')")
    clear_link = body.index("z.sourceLayer = null")
    assert confirm < history < clear_link


def test_pass_119_runtime_is_cache_busted():
    assert "spb93-layer-delete-transaction-20260717" in HTML
    assert "spb93-merge-down-transaction-20260717" in HTML
