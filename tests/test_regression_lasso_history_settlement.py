from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")


def test_lasso_builds_candidate_before_snapshot_and_settles_every_mask_consumer():
    source = CANVAS[CANVAS.index("function closeLasso(e)"):CANVAS.index("window.closeLasso = closeLasso")]
    previous = source.index("const previousMask")
    candidate = source.index("let nextMask")
    compare = source.index("if (!changedPixels)")
    history = source.index("pushUndo(selectedZoneIndex)")
    commit = source.index("zone.regionMask = finalMask")
    settle = source.index("_refreshZoneMaskHistoryUI()")
    assert previous < candidate < compare < history < commit < settle
    assert "zone.regionMask = new Uint8Array(w * h)" not in source
    assert "zone.regionMask[y * w + x] = fillVal" not in source
    assert "Lasso skipped: selection already matches this result" in source
    assert "window.SPBPenPath.featherMask(nextMask" in source


def test_lasso_runtime_is_identical_in_packaged_server():
    relative = Path("paint-booth-3-canvas.js")
    assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()


def test_polygon_lasso_refreshes_live_vertex_count_after_add_remove_and_close():
    assert "function _updateLassoPointHint()" in CANVAS
    add = CANVAS[CANVAS.index("function addLassoPoint"):CANVAS.index("// Shared by Magic Wand")]
    undo = CANVAS[CANVAS.index("function undoLassoPoint"):CANVAS.index("// Expose for Escape key")]
    hide = CANVAS[CANVAS.index("function hideLassoPreview"):CANVAS.index("function undoLassoPoint")]
    assert "_updateLassoPointHint();" in add
    assert "_updateLassoPointHint();" in undo
    assert "_updateLassoPointHint();" in hide
    assert "count === 1 ? 'point' : 'points'" in CANVAS
