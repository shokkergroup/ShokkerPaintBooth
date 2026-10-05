"""SPB-93 Pass 67: Layer retouch keeps the full stack visible during a stroke."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_every_layer_pixel_flush_schedules_a_stack_preview():
    flush = _span("function _flushPaintImageDataToCurrentSurface", "window._flushPaintImageDataToCurrentSurface")
    assert "_activeLayerCtx.putImageData(paintImageData, 0, 0)" in flush
    assert "if (pc) _scheduleActiveLayerCompositePreview(dirty)" in flush
    assert flush.index("_scheduleActiveLayerCompositePreview(dirty)") < flush.index("pc.getContext('2d').putImageData")


def test_composite_preview_substitutes_active_surface_without_flattening_edit_buffer():
    helper = _span("function _refreshActiveLayerCompositePreviewNow", "function _scheduleActiveLayerCompositePreview")
    assert "_spbCompositeLayerStack(pctx, _psdLayers" in helper
    assert "candidate.id === layer.id ? _activeLayerCanvas : null" in helper
    assert "SPBPaintPreviewRegion.paint" in helper
    assert "paintImageData = pctx.getImageData" not in helper

    compositor = _span("function _spbCompositeLayerStack(ctx, layers, options)", "// [SPB-LAYER-GAUNTLET A4")
    script = f"""
const events = [];
const ctx = {{
  canvas: {{width:10,height:10}}, save() {{}}, restore() {{}}, clearRect() {{}}, drawImage(img, x, y) {{ events.push(['draw', img.name, x, y]); }},
  globalAlpha: 1, globalCompositeOperation: 'source-over'
}};
var window = {{SPBPaintPreviewRegion:require('./js/canvas/layer/paint-preview-region.js')}};
const _activeLayerCompositePreviewRegion = window.SPBPaintPreviewRegion.createQueue();
function _spbInspectLayerStack() {{ return {{ok:true}}; }}
function _spbReportGroupFidelityFailure() {{ throw Error('unexpected group failure'); }}
const pc = {{ width: 10, height: 10, getContext() {{ return ctx; }} }};
const document = {{ getElementById() {{ return pc; }} }};
const bottom = {{ id: 'bottom', visible: true, opacity: 255, img: {{name:'bottom-img'}}, bbox:[2,3] }};
const active = {{ id: 'active', visible: true, opacity: 255, img: {{name:'old-active'}}, bbox:[4,5] }};
const _psdLayers = [bottom, active];
const _activeLayerPaintLayerId = 'active';
const _activeLayerCanvas = {{ name: 'live-active' }};
const paintImageData = {{ name: 'layer-pixels' }};
function getSelectedLayer() {{ return active; }}
function renderLayerEffects(_ctx, layer, phase) {{ events.push(['fx', layer.id, phase]); }}
function _layerAtIndexCanComposite() {{ return true; }}
function _drawLayerPixelContent(target, layers, index, sourceOverride) {{
  const layer = layers[index];
  target.drawImage(sourceOverride || layer.img, sourceOverride ? 0 : layer.bbox[0], sourceOverride ? 0 : layer.bbox[1]);
  return true;
}}
{compositor}
{helper}
const before = paintImageData;
const ok = _refreshActiveLayerCompositePreviewNow();
console.log(JSON.stringify({{ok, same: before === paintImageData, events}}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["ok"] is True and payload["same"] is True
    assert ["draw", "bottom-img", 2, 3] in payload["events"]
    assert ["draw", "live-active", 0, 0] in payload["events"]


def test_pass_67_runtime_is_cache_busted_and_mirrored():
    import re
    assert re.search(r'<script src="paint-booth-3-canvas\.js\?v=[^"\s]+"></script>', HTML)
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
