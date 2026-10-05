"""SPB-93 Pass 61: Pencil and shortcut help must describe real runtime behavior."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_pencil_help_describes_size_control_instead_of_claiming_one_pixel():
    user_facing = HTML + CANVAS
    for stale_claim in ("1-pixel precise", "1px precise", "1px-precise"):
        assert stale_claim not in user_facing
    assert "Pencil (I) — hard-edged, size-controlled drawing" in HTML
    assert "Hard-edged, size-controlled · no anti-aliasing" in CANVAS
    assert "Hard-edged, size-controlled drawing on the selected layer" in CANVAS


def test_shortcut_legend_matches_context_sensitive_number_key_routing():
    assert "['B', 'Brush (Zone mask or selected Layer)']" in CANVAS
    assert "['R', 'Recolor (first click samples source)']" in CANVAS
    assert "['0–9', 'Paint: tool opacity/strength · Move: Layer opacity']" in CANVAS
    assert "['0 / 1 / 2', 'No paint/Layer target: Fit / 100% / 200% zoom']" in CANVAS

    numeric_handler = CANVAS[CANVAS.index("// Number keys: context-sensitive") :]
    numeric_handler = numeric_handler[: numeric_handler.index("// Ctrl+D = deselect zone mask")]
    assert "const isPaintTool" in numeric_handler
    assert "setLayerOpacity(_selectedLayerId, pct)" in numeric_handler
    assert "canvasZoom('fit')" in numeric_handler
    assert "canvasZoom('100')" in numeric_handler
    assert "canvasZoom('200')" in numeric_handler


def test_pass_61_runtime_is_cache_busted_and_mirrored():
    assert "spb93-pencil-shortcut-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
