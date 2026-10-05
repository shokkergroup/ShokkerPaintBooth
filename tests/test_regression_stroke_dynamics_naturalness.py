"""SPB-93 Passes 45/47: bounded, event-independent brush-family strokes."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/stroke-dynamics.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_mouse_is_exact_and_pen_curve_is_bounded_monotonic_and_tapered():
    data = _node(
        r"""
const api=require('./js/canvas/stroke-dynamics.js');
const opts={baseRadius:40,baseOpacity:.8,flow:.5};
const mouse=api.resolveDynamics({...opts,pointerType:'mouse',pressure:.01});
const pen=[0,.1,.25,.5,.75,1].map(pressure=>api.resolveDynamics({...opts,pointerType:'pen',pressure}));
process.stdout.write(JSON.stringify({mouse,pen,mousePressure:api.normalizePressure(.02,'mouse')}));
"""
    )
    assert data["mouse"] == {"pressure": 1, "radius": 40, "opacity": 0.4}
    assert data["mousePressure"] == 1
    radii = [row["radius"] for row in data["pen"]]
    opacity = [row["opacity"] for row in data["pen"]]
    assert radii == sorted(radii)
    assert opacity == sorted(opacity)
    assert 1 <= radii[0] < radii[-1] == 40
    assert 0 < opacity[0] < opacity[-1] == 0.4


def test_distance_resampling_is_event_frequency_independent_and_interpolates_pressure():
    data = _node(
        r"""
const api=require('./js/canvas/stroke-dynamics.js');
function run(points){
  let state=api.beginStroke(points[0]); const out=[];
  for(const point of points.slice(1)){
    const result=api.sampleSegment(state,point,10); state=result.state; out.push(...result.points);
  }
  return {points:out.map(p=>({x:Number(p.x.toFixed(4)),pressure:Number(p.pressure.toFixed(4))})),carry:Number(state.carry.toFixed(4))};
}
process.stdout.write(JSON.stringify({
  sparse:run([{x:0,y:0,pressure:0},{x:100,y:0,pressure:1}]),
  dense:run([{x:0,y:0,pressure:0},{x:37,y:0,pressure:.37},{x:58,y:0,pressure:.58},{x:100,y:0,pressure:1}])
}));
"""
    )
    assert data["sparse"] == data["dense"]
    assert [row["x"] for row in data["sparse"]["points"]] == list(range(10, 101, 10))
    assert [row["pressure"] for row in data["sparse"]["points"]] == [i / 10 for i in range(1, 11)]
    assert data["sparse"]["carry"] == 0


def test_canvas_seeds_opening_dab_and_resamples_zone_and_layer_strokes():
    assert "function _forEachContinuousBrushDab" in CANVAS
    assert CANVAS.count("_seedBrushSpacing(") >= 3  # declaration + Layer + Zone starts
    move_start = CANVAS.index("// SPB-93 tick 45: distance-resample every segment")
    move_end = CANVAS.index("} else if ((canvasMode === 'spatial-include'", move_start)
    move = CANVAS[move_start:move_end]
    assert "_forEachContinuousBrushDab" in move
    assert "if (_activeLayerCanvas)" in move
    assert "paintRegionCircle(dab.x, dab.y" in move
    assert "_paintOnLayerAt(dab.x, dab.y" in move
    assert "0.6 + _pressure * 0.8" not in CANVAS
    assert "0.7 + _pressure * 0.6" not in CANVAS


def test_all_continuous_retouch_tools_share_filtered_distance_resampling():
    move_start = CANVAS.index("} else if (canvasMode === 'clone' && isDrawing")
    move_end = CANVAS.index("} else if (canvasMode === 'ellipse-marquee'", move_start)
    move = CANVAS[move_start:move_end]
    for mode in (
        "clone",
        "heal",
        "colorbrush",
        "recolor",
        "smudge",
        "history-brush",
        "dodge",
        "burn",
        "blur-brush",
        "sharpen-brush",
    ):
        assert mode in move
    assert move.count("_forEachContinuousBrushDab(") == 8
    assert move.count("_filterContinuousBrushPoint(") == 9  # pencil filters but owns interpolation
    assert "_checkBrushSpacing(" not in move
    assert "_paintContinuousBrushDabs(result.points, paintDab)" in CANVAS
    assert "window._lastPointerPressure = Number.isFinite" in CANVAS


def test_retouch_stroke_starts_reset_filters_seed_spacing_and_batch_surface_flushes():
    down_start = CANVAS.index("if (canvasMode === 'clone')")
    down_end = CANVAS.index("// === END NEW TOOLS ===", down_start)
    down = CANVAS[down_start:down_end]
    assert down.count("_beginContinuousBrushStroke(pos)") == 9
    assert "window.resetBrushSmoothing" in CANVAS
    assert "window.resetBrushStabilizer" in CANVAS
    assert "_seedBrushSpacing(filtered.x, filtered.y, _currentBrushPressure())" in CANVAS
    assert "window._spbPaintFlushBatchDepth" in CANVAS
    assert "window._spbPaintFlushPending = true" in CANVAS


def test_pointer_contract_prevents_mouse_inheriting_stylus_pressure():
    assert "window._lastPointerType = pointerType" in CANVAS
    assert "normalizePressure(sample?.pressure, pointerType)" in CANVAS
    assert "window._lastPointerType = 'mouse'" in CANVAS
    assert "window._lastPointerPressure = 1" in CANVAS
    assert "getCoalescedEvents" in CANVAS


def test_stroke_dynamics_loads_before_canvas_is_manifested_and_mirrored():
    tag = f"{MODULE}?v=spb93-natural-stroke-dynamics-20260716"
    assert tag in HTML
    assert HTML.index(tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert MODULE in MANIFEST["files"]
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js", "js/canvas/layer/healing-brush.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
