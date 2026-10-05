"""SPB-93 T42: Pick Item transform is a real modal History transaction."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
SERVER_CANVAS = (ROOT / "electron-app/server/paint-booth-3-canvas.js")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
SERVER_HTML = (ROOT / "electron-app/server/paint-booth-v2.html")


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


def test_t42_selection_lift_captures_before_preview_and_defers_undo():
    transform = _function_source("transformSelectedLayerRegion")
    capture_at = transform.index("const sessionBeforeCapture")
    lift_at = transform.index("liftSelectionToNewLayer")
    assert capture_at < lift_at
    assert "snapshot: _snapshotLayerStack()" in transform
    assert "zoneSourceLayers: _snapshotZoneSourceLayers()" in transform
    assert "sessionUndoMode: 'captured-stack'" in transform
    assert "{ skipUndo: true }" in transform

    lift = _function_source("liftSelectionToNewLayer")
    assert "if (!opts.skipUndo" in lift


def test_t42_capture_is_carried_into_active_transform():
    activate = _function_source("activateLayerTransform")
    assert "sessionBeforeCapture: meta.sessionBeforeCapture || null" in activate
    assert "sessionUndoPublished: false" in activate


def test_t42_apply_publishes_exactly_one_captured_stack_action():
    commit = _function_source("commitLayerTransform")
    branch_start = commit.index("if (s.sessionUndoMode === 'captured-stack')")
    branch_end = commit.index("if (s.sessionUndoMode === 'stack-restore')", branch_start)
    branch = commit[branch_start:branch_end]
    assert "if (s.sessionUndoPublished) return false" in branch
    assert "_pushCapturedLayerStackUndo(s.sessionBeforeCapture, 'transform selection')" in branch
    assert "s.sessionUndoPublished = true" in branch
    assert "_pushLayerUndo" not in branch


def test_t42_cancel_and_activation_failure_restore_privately():
    cancel = _function_source("cancelLayerTransform")
    branch_start = cancel.index("if (s.sessionUndoMode === 'captured-stack'")
    branch_end = cancel.index("if (s.sessionUndoMode === 'stack-restore')", branch_start)
    branch = cancel[branch_start:branch_end]
    assert "_restoreLayerStack(s.sessionBeforeCapture.snapshot" in branch
    assert "_restoreZoneSourceLayers(s.sessionBeforeCapture.zoneSourceLayers)" in branch
    assert "refreshActiveToolLabel()" in branch
    assert "undoLayerEdit" not in branch

    transform = _function_source("transformSelectedLayerRegion")
    failure = transform[transform.index("if (!activated)") :]
    assert "_restoreLayerStack(sessionBeforeCapture.snapshot" in failure
    assert "_restoreZoneSourceLayers(sessionBeforeCapture.zoneSourceLayers)" in failure
    assert "refreshActiveToolLabel()" in failure
    assert "undoLayerEdit" not in failure


def test_t42_runtime_is_cache_busted_and_two_copies_match():
    assert 'src="paint-booth-3-canvas.js?v=' in HTML
    assert SERVER_CANVAS.read_bytes() == (ROOT / "paint-booth-3-canvas.js").read_bytes()
    assert SERVER_HTML.read_bytes() == (ROOT / "paint-booth-v2.html").read_bytes()
