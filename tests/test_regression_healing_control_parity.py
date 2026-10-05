"""SPB-93 Pass 63: Healing's visible controls must match its consumed dynamics."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HEALING = (ROOT / "js/canvas/layer/healing-brush.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_healing_exposes_every_shared_brush_control_it_consumes():
    visibility_start = CANVAS.index("const showBrushAdvanced")
    visibility = CANVAS[visibility_start : CANVAS.index("// Symmetry toggle", visibility_start)]
    assert "mode === 'heal'" in visibility
    for control in (
        "brushFlowLabel",
        "brushSpacingLabel",
        "brushSmoothingLabel",
        "'brushShape'",
    ):
        assert control in visibility

    for consumed in (
        "getElementById('brushSize')",
        "getElementById('brushHardness')",
        "getElementById('brushOpacity')",
        "getElementById('brushFlow')",
        "getElementById('brushShape')",
        "window._resolveBrushDynamics",
    ):
        assert consumed in HEALING


def test_pass_63_runtime_is_cache_busted_and_mirrored():
    assert "spb93-healing-control-parity-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
