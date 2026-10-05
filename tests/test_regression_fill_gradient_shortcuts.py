"""SPB-93 Pass 66: Layer Fill/Gradient number keys target tool opacity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_layer_fill_and_gradient_are_contextual_opacity_tools():
    start = CANVAS.index("// Number keys: context-sensitive")
    shortcut = CANVAS[start : CANVAS.index("// Ctrl+D = deselect zone mask", start)]
    assert "canvasMode === 'fill' || canvasMode === 'gradient'" in shortcut
    assert "isLayerToolbarMode()" in shortcut
    assert "const isPaintTool = isLayerPixelOpacityTool ||" in shortcut
    assert "isFillGradient ? `${canvasMode === 'fill' ? 'Fill' : 'Gradient'} opacity`" in shortcut
    assert "const controlId" in shortcut and "'brushOpacity'" in shortcut


def test_layer_fill_and_gradient_engines_consume_the_routed_control():
    gradient_start = CANVAS.index("const layerAlpha = parseInt(document.getElementById('brushOpacity')")
    assert gradient_start > 0
    fill_start = CANVAS.index("function fillBucketOnLayer")
    fill = CANVAS[fill_start : CANVAS.index("window.fillGradientOnLayer", fill_start)]
    assert "getElementById('brushOpacity')" in fill


def test_pass_66_runtime_is_cache_busted_and_mirrored():
    assert "spb93-fill-gradient-shortcuts-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
