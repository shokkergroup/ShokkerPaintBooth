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


def test_pass_118_merge_down_refusals_precede_all_mutation():
    body = _function_body("mergeLayerDown")
    hidden_guard = body.index("if (upper.visible === false)")
    lock_guard = body.index("if (upper.locked || lower.locked)")
    history = body.index("_pushLayerStackUndo('merge down')")
    source_migration = body.index("z.sourceLayer = lower.id")
    layer_removal = body.index("_psdLayers.splice(idx, 1)")
    assert hidden_guard < lock_guard < history < source_migration < layer_removal


def test_pass_118_merge_down_honors_both_lock_badges():
    body = _function_body("mergeLayerDown")
    assert "upper.locked || lower.locked" in body
    assert "unlock it before Merge Down" in body


def test_pass_118_stack_history_carries_zone_source_links_both_directions():
    push = _function_body("_pushLayerStackUndo")
    undo = _function_body("undoLayerEdit")
    redo = _function_body("redoLayerEdit")
    assert "zoneSourceLayers: _snapshotZoneSourceLayers()" in push
    assert "zoneSourceLayers: _snapshotZoneSourceLayers()" in undo
    assert "_restoreZoneSourceLayers(entry.zoneSourceLayers)" in undo
    assert "zoneSourceLayers: _snapshotZoneSourceLayers()" in redo
    assert "_restoreZoneSourceLayers(entry.zoneSourceLayers)" in redo


def test_pass_118_zone_history_is_metadata_only():
    snapshot = _function_body("_snapshotZoneSourceLayers")
    restore = _function_body("_restoreZoneSourceLayers")
    combined = snapshot + restore
    assert "sourceLayer" in combined
    assert "regionMask" not in combined
    assert "spatialMask" not in combined
    assert "strengthMap" not in combined


def test_pass_118_runtime_is_cache_busted():
    assert "spb93-merge-down-transaction-20260717" in HTML
    assert "spb93-overlay-opacity-truth-20260717" in HTML
