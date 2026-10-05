"""Right-click drag pan must not open the context menu.

Painter-reported UX bug class: when zoomed in, right-click drag is the
canonical pan gesture, but a naive implementation lets the browser's
contextmenu fire at the end of the drag (or immediately on mouseup),
popping the menu over the freshly-panned view. The Source pane in
`paint-booth-3-canvas.js` defends with a 5-layer suppression mesh
(see comments at line 7430+).

This file pins the entire suppression mesh so a future refactor can't
silently remove one layer.
"""

from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_right_click_drag_has_explicit_context_menu_suppression_guard():
    src = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")

    assert "let rightButtonDownForCanvas = false;" in src
    assert "let rightButtonDragExceeded = false;" in src
    assert "e.button === 2 && e.target.id === 'paintCanvas'" in src
    assert "rightButtonDragExceeded = true;" in src
    assert "const rdx = e.clientX - rightButtonStartX;" in src
    assert "if (isPanning || rightButtonDragExceeded" in src
    assert "rightButtonDragExceeded = false;" in src


def test_right_click_drag_threshold_and_grace_window_present():
    """The full suppression mesh has 4 components beyond the basic flag:
       (a) `lastRightButtonPanAt` timestamp + `rightPanJustEnded` 1500ms
           grace window — the OS sometimes fires contextmenu AFTER
           mouseup, so the flag-based suppression alone races.
       (b) 5px drag threshold (distance² > 25) — single-pixel jitter
           on right-click must NOT count as a drag, or every right-click
           gets its menu suppressed.
       (c) `suppressNextCanvasContextMenu` flag — second independent
           suppression channel, layered with the dragExceeded flag.
       (d) `clearCanvasContextMenuSuppressTimer` — cleans up the 1500ms
           grace state so it can't leak into the NEXT right-click."""
    src = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "let lastRightButtonPanAt = 0;" in src, (
        "lastRightButtonPanAt timestamp removed — the post-mouseup grace "
        "window is the backstop against late-firing OS contextmenu events."
    )
    assert "rightPanJustEnded" in src, (
        "rightPanJustEnded grace check removed — context menu can race "
        "after right-button mouseup completes."
    )
    assert "rdx * rdx + rdy * rdy > 25" in src, (
        "5px right-button drag threshold removed — every right-click would "
        "now suppress its own menu (single-pixel mouse jitter counts as drag)."
    )
    assert "suppressNextCanvasContextMenu = true;" in src
    assert "clearCanvasContextMenuSuppressTimer" in src, (
        "Suppress-state cleanup timer removed — grace state could leak "
        "across distinct right-click events."
    )


def test_right_click_drag_mouseup_rearms_suppression():
    """When the painter completes a right-button drag (mouseup with
    `rightButtonDragExceeded`), the mouseup handler MUST re-arm the
    1500ms grace window. Otherwise the OS contextmenu firing AFTER
    mouseup races past the now-cleared dragExceeded flag and the menu
    pops over the freshly-panned view.

    The rearm pattern lives in the pan-system mouseup branch around
    line 7627. We verify the structural pattern exists by counting
    distinct co-located occurrences of (a) the `rightButtonDragExceeded`
    check, (b) the `lastRightButtonPanAt = Date.now()` rearm. Both
    must appear at least once with the rearm appearing within ~200
    chars after a dragExceeded check (proves they're paired in the
    same branch, not stranded in unrelated handlers)."""
    src = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    drag_check = "if (rightButtonDragExceeded)"
    rearm = "lastRightButtonPanAt = Date.now()"
    # Both must exist somewhere
    assert drag_check in src, (
        "Pan mouseup no longer checks rightButtonDragExceeded — late OS "
        "contextmenu after right-drag will pop the menu."
    )
    assert rearm in src, (
        "1500ms grace window rearm pattern (`lastRightButtonPanAt = Date.now()`) "
        "removed entirely — late OS contextmenu after right-drag will pop."
    )
    # Verify pairing: at least one rearm appears within 250 chars after a
    # dragExceeded check (proves same branch).
    paired = False
    pos = 0
    while True:
        idx = src.find(drag_check, pos)
        if idx < 0:
            break
        window = src[idx:idx + 250]
        if rearm in window:
            paired = True
            break
        pos = idx + 1
    assert paired, (
        "Pan-mouseup rearm broken: `rightButtonDragExceeded` check and "
        "`lastRightButtonPanAt = Date.now()` rearm are no longer co-located. "
        "The rearm sequence may have been split across handlers."
    )
