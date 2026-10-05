"""SPB-93 Pass 38: every advertised brush tip uses one footprint contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/brush-footprint.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def _span(function_name: str) -> str:
    start = CANVAS.index(f"function {function_name}")
    next_function = CANVAS.find("\nfunction ", start + 10)
    return CANVAS[start : next_function if next_function >= 0 else len(CANVAS)]


def test_pure_footprints_have_exact_bounds_metrics_and_deterministic_noise():
    data = _node(
        r"""
const api = require('./js/canvas/brush-footprint.js');
function points(shape, random) {
  const tip = api.create(shape, 2, random);
  const hits = [];
  for (let y=-2;y<=2;y++) for (let x=-2;x<=2;x++) {
    if (tip.contains(x,y,x*x+y*y)) hits.push([x,y]);
  }
  return hits;
}
const fake = {ops:[], beginPath(){this.ops.push('begin')}, rect(){this.ops.push('rect')},
  moveTo(){this.ops.push('move')}, lineTo(){this.ops.push('line')}, closePath(){this.ops.push('close')},
  arc(){this.ops.push('arc')}};
api.create('diamond',2).tracePath(fake,4,5);
process.stdout.write(JSON.stringify({
  shapes: api.VALID_SHAPES,
  counts: {
    round: points('round').length,
    square: points('square').length,
    diamond: points('diamond').length,
    slash: points('slash').length,
    noisePass: points('noise',()=>0.6).length,
    noiseSkip: points('noise',()=>0.6001).length
  },
  metrics: {
    squareCorner: api.create('square',2).distanceSquared(2,2),
    diamondDiagonal: api.create('diamond',2).distanceSquared(1,1),
    slashAlong: api.create('slash',2).distanceSquared(2,2)
  },
  invalid: api.normalizeShape('hexagon'),
  current: api.currentShape({getElementById(){return {value:'SQUARE'}}}),
  path: fake.ops
}));
"""
    )
    assert data["shapes"] == ["round", "square", "diamond", "slash", "noise"]
    assert data["counts"] == {
        "round": 13,
        "square": 25,
        "diamond": 13,
        "slash": 5,
        "noisePass": 13,
        "noiseSkip": 0,
    }
    assert data["metrics"] == {
        "squareCorner": 4,
        "diamondDiagonal": 4,
        "slashAlong": 4,
    }
    assert data["invalid"] == "round"
    assert data["current"] == "square"
    assert data["path"] == ["begin", "move", "line", "line", "line", "close"]


def test_every_visible_brush_family_kernel_consumes_the_shared_footprint():
    pixel_kernels = (
        "_paintRegionCircleAt",
        "_paintScopedSpatialCircle",
        "paintCloneStroke",
        "_paintColorBrushAt",
        "paintRecolor",
        "paintSmudge",
        "paintPencil",
        "_paintDodgeBurn",
        "paintBlurBrush",
        "paintSharpenBrush",
        "paintPatternBrushAt",
        "paintHistoryBrush",
    )
    for function_name in pixel_kernels:
        source = _span(function_name)
        assert "_createBrushFootprint" in source, function_name
        assert "footprint.contains" in source, function_name

    layer_brush = _span("_paintOnLayerAt")
    assert "_createBrushFootprint" in layer_brush
    assert "footprint.tracePath" in layer_brush
    assert "footprint.shape === 'noise'" in layer_brush
    assert "hardness >= 0.99 && opacity >= 0.99" not in layer_brush
    special = _span("_drawLayerSpecialStamp")
    assert "footprint.tracePath" in special
    assert "_drawLayerNoiseStamp" in special


def test_shared_module_loads_before_canvas_and_is_packaged():
    tag = f"{MODULE}?v=spb93-radial-hardness-parity-20260717"
    assert tag in HTML
    assert HTML.index(tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "spb93-brush-footprint-20260716" in HTML
    assert MODULE in MANIFEST["files"]


def test_root_and_packaged_brush_runtime_are_byte_identical():
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
