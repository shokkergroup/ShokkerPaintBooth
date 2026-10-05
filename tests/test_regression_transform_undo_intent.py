"""SPB-93 Pass 142: Ctrl+Z cancels previews and undo coalescing is session-local."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(CANVAS):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return CANVAS[start : index + 1]
        index += 1
    raise AssertionError(name)


def test_pass_142_ctrl_z_cancels_active_transform_instead_of_applying_it():
    listener_start = CANVAS.index("// Keyboard: Enter = commit, Escape = cancel, Ctrl+T = activate")
    listener_end = CANVAS.index("// Wire transform canvas mouse events", listener_start)
    listener = CANVAS[listener_start:listener_end]
    undo_start = listener.index("e.key.toLowerCase() === 'z'")
    undo_end = listener.index("} else if (['ArrowLeft'", undo_start)
    undo_branch = listener[undo_start:undo_end]
    assert "cancelActiveTransformSession();" in undo_branch
    assert "commitLayerTransform();" not in undo_branch
    assert "hadRealChange" not in undo_branch


def test_pass_142_each_successful_transform_activation_starts_fresh_undo_scope():
    source = _function_source("activateLayerTransform")
    lock_gate = source.index("if (layer.locked)")
    reset = source.index("window._spbLastElementUndo = null")
    state = source.index("freeTransformState = {")
    assert lock_gate < reset < state


def test_pass_142_runtime_is_cache_busted_and_mirrored_after_sync():
    assert "spb93-transform-undo-intent-20260717" in HTML
    assert re.search(r'src="paint-booth-3-canvas\.js\?v=[^"\s]+', HTML)
    assert "spb93-layer-copy-stack-position-20260717" in HTML
