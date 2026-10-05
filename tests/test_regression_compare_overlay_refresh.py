from pathlib import Path


SOURCE = Path("paint-booth-6-ui-boot.js").read_text(encoding="utf-8")


def _body(signature: str, next_signature: str) -> str:
    start = SOURCE.index(signature)
    end = SOURCE.index(next_signature, start + len(signature))
    return SOURCE[start:end]


def test_new_compare_image_publishes_atomically_and_redraws_open_overlay():
    body = _body("function loadRenderedImageForCompare(url)", "// ===== PRESET GALLERY")
    assert "const nextImage = new Image()" in body
    assert "if (pendingRenderedImage !== nextImage)" in body
    assert "renderedImage = nextImage" in body
    assert "requestCompareRefresh()" in body
    assert body.index("renderedImage = nextImage") < body.index("requestCompareRefresh()")


def test_compare_refresh_is_frame_coalesced_and_mode_guarded():
    body = _body("function requestCompareRefresh()", "function installCompareRefreshObservers()")
    assert "if (!compareMode || !renderedImage)" in body
    assert "requestAnimationFrame" in body
    assert "drawCompareView()" in body


def test_paint_canvas_resize_invalidates_open_compare_overlay():
    body = _body("function installCompareRefreshObservers()", "function toggleCompareMode()")
    assert "new ResizeObserver(requestCompareRefresh)" in body
    assert "new MutationObserver(requestCompareRefresh)" in body
    assert "attributeFilter: ['width', 'height', 'style', 'class']" in body
    assert "window.addEventListener('resize', requestCompareRefresh)" in body


def test_compare_draw_resizes_and_clears_overlay_before_repaint():
    body = _body("function drawCompareView()", "function onCompareMouseDown(e)")
    assert "overlay.width = w; overlay.height = h" in body
    assert "ctx.clearRect(0, 0, w, h)" in body
