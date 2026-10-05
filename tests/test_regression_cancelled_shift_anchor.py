"""SPB-93 Pass 111: cancelled paint never seeds a future Shift-line."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_shared_release_discards_only_the_pending_endpoint():
    release = _span(
        "function _releaseActiveBrushStrokeState()",
        "function _finishActiveBrushStroke()",
    )
    assert "_brushStrokeEndpoint = null" in release
    assert "_lastBrushStrokeAnchor = null" not in release


def test_finish_commits_before_release_while_cancel_only_releases():
    finish = _span(
        "function _finishActiveBrushStroke()",
        "window._finishActiveBrushStroke",
    )
    cancel = _span(
        "function _cancelActiveLayerBrushStroke()",
        "window._cancelActiveLayerBrushStroke",
    )
    assert finish.index("_commitBrushStrokeAnchor()") < finish.index(
        "_releaseActiveBrushStrokeState()"
    )
    assert "_commitBrushStrokeAnchor" not in cancel
    assert "_releaseActiveBrushStrokeState()" in cancel


def test_pass_111_runtime_token_and_mirror_are_current():
    assert "spb93-cancel-shift-anchor-20260717" in HTML
    assert (ROOT / "paint-booth-3-canvas.js").read_bytes() == (
        ROOT / "electron-app/server/paint-booth-3-canvas.js"
    ).read_bytes()
