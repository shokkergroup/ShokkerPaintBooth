"""SPB-93 Pass 115: Pencil Size 1 paints exactly the clicked pixel."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _pencil():
    start = CANVAS.index("function paintPencil(x, y, useBG, skipFlush)")
    return CANVAS[start : CANVAS.index("window.paintPencil", start)]


def test_size_one_bypasses_the_radius_one_three_pixel_footprint():
    source = _pencil()
    assert "const requestedSize = Math.max(1" in source
    assert "_resolveBrushDynamics(requestedSize, opacityBase, flow)" in source
    assert "const radius = requestedSize === 1 ? 0 : pencilDynamics.radius" in source
    assert "for (let dy = -radius; dy <= radius; dy++)" in source
    assert "for (let dx = -radius; dx <= radius; dx++)" in source


def test_larger_pencil_sizes_keep_pressure_and_existing_shape_contract():
    source = _pencil()
    assert "const footprint = _createBrushFootprint(radius)" in source
    assert "footprint.contains(dx, dy" in source
    assert "pencilDynamics.opacity" in source


def test_pass_115_runtime_token_and_mirror_are_current():
    assert "spb93-pencil-one-pixel-endpoint-20260717" in HTML
    server = ROOT / "electron-app/server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
