"""SPB-93 Pass 64: Healing must participate in every brush drag/view route."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _line_containing(marker: str) -> str:
    return next(line for line in CANVAS.splitlines() if marker in line)


def test_healing_drag_is_not_stolen_by_native_drag_or_zoomed_pan():
    native_drag_guard = _line_containing("Prevent native canvas image drag for draw tools")
    # The explanatory comment precedes the actual route by two lines.
    native_drag_area = CANVAS[CANVAS.index(native_drag_guard) :]
    native_drag_area = native_drag_area[: native_drag_area.index("const pos = getPixelAt(e)")]
    assert "'heal'" in native_drag_area

    zoomed_pan_guard = _line_containing("const drawToolActive =")
    assert "'heal'" in zoomed_pan_guard


def test_healing_gets_layer_target_feedback_and_alt_wheel_size():
    target_start = CANVAS.index("function canvasToolUsesTargetLabel")
    target_contract = CANVAS[target_start : CANVAS.index("window.canvasToolUsesTargetLabel", target_start)]
    assert "'clone','heal'" in target_contract

    alt_wheel = _line_containing("var BRUSH_MODES =")
    assert "'clone', 'heal'" in alt_wheel


def test_pass_64_runtime_is_cache_busted_and_mirrored():
    assert "spb93-healing-drag-routing-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
