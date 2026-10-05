from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "js" / "canvas" / "layer" / "clipping-mask.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_132_clipping_base_resolution_and_stack_normalization_are_functional():
    script = r"""
const api = require('./js/canvas/layer/clipping-mask.js');
const layers = [
  {id:'A', clippingMask:false}, {id:'B', clippingMask:true},
  {id:'C', clippingMask:true}, {id:'D', clippingMask:false},
  {id:'E', clippingMask:true}
];
function check(v,m){ if(!v) throw new Error(m); }
check(api.resolveBaseLayer(layers, 1).id === 'A', 'B base');
check(api.resolveBaseLayer(layers, 2).id === 'A', 'C chain base');
check(api.resolveBaseLayer(layers, 4).id === 'D', 'E base');
layers[0].clippingMask = true;
check(api.normalizeStack(layers) === true && layers[0].clippingMask === false, 'bottom normalize');
check(api.normalizeStack(layers) === false, 'stable normalize');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_pass_132_clipped_pixels_are_masked_in_document_coordinates():
    script = r"""
const api = require('./js/canvas/layer/clipping-mask.js');
const scratchCalls = [], targetCalls = [];
const scratchCtx = {
  globalAlpha:1, globalCompositeOperation:'source-over',
  setTransform(){}, clearRect(){},
  drawImage(img,x,y){ scratchCalls.push([img.id || 'scratch',x,y,this.globalCompositeOperation]); }
};
const scratchCanvas = {width:0,height:0,id:'scratch',getContext(){return scratchCtx;}};
global.document = {createElement(){return scratchCanvas;}};
const target = {
  canvas:{width:100,height:80}, globalAlpha:1, globalCompositeOperation:'source-over',
  save(){}, restore(){},
  drawImage(img,x,y){ targetCalls.push([img.id,x,y,this.globalAlpha,this.globalCompositeOperation]); }
};
const base = {id:'base',visible:true,img:{id:'baseImg'},bbox:[11,13,41,43]};
const clipped = {id:'clip',clippingMask:true,img:{id:'clipImg'},bbox:[5,7,25,27],opacity:128,blendMode:'multiply'};
if (!api.drawLayerPixels(target, clipped, base, null)) throw new Error('draw refused');
if (scratchCalls[0].join('|') !== 'clipImg|5|7|source-over') throw new Error('clip source placement');
if (scratchCalls[1].join('|') !== 'baseImg|11|13|destination-in') throw new Error('base alpha placement');
if (targetCalls.length !== 1 || targetCalls[0][0] !== 'scratch') throw new Error('masked result not composited');
if (Math.abs(targetCalls[0][3] - 128/255) > 1e-9 || targetCalls[0][4] !== 'multiply') throw new Error('layer blend/opacity lost');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_pass_132_every_live_layer_compositor_uses_the_shared_clipping_path():
    assert "function _drawLayerPixelContent" in CANVAS
    assert "function _layerAtIndexCanComposite" in CANVAS
    assert CANVAS.count("_drawLayerPixelContent(") >= 7
    assert "buildLivePaintCompositeCanvas" in CANVAS
    assert "_refreshActiveLayerCompositePreviewNow" in CANVAS
    assert "function recompositeFromLayers" in CANVAS
    assert "function mergeVisibleLayers" in CANVAS
    assert "_drawLayerPixelContent(mctx, _psdLayers, idx, null)" in _function_body("mergeLayerDown")
    ownership = _function_body("getLayerVisibleContributionMask")
    assert "_drawLayerPixelContent(ctx, ownershipLayers, layerIndex, null)" in ownership
    assert "renderLayerEffects(ctx, identityLayer, 'before')" in ownership
    assert "renderLayerEffects(ctx, identityLayer, 'after')" in ownership
    assert "Object.assign({}, layer, { blendMode: 'source-over' })" in ownership


def test_pass_132_panel_control_and_toggle_refusals_are_truthful():
    assert 'class="layer-clipping-toggle"' in CANVAS
    assert 'aria-pressed="${l.clippingMask ? \'true\' : \'false\'}"' in CANVAS
    assert "Clip this Layer inside" in CANVAS
    toggle_start = CANVAS.index("window.toggleClippingMask = function toggleClippingMask")
    toggle_end = CANVAS.index("window.rotateView90CW", toggle_start)
    toggle = CANVAS[toggle_start:toggle_end]
    history = toggle.index("_pushLayerStackUndo('Toggle clipping mask')")
    assert toggle.index("if (L.locked)") < history
    assert toggle.index("if (!L.clippingMask && !base)") < history
    assert toggle.index("L.clippingMask = !L.clippingMask") > history
    assert "return true" in toggle


def test_pass_132_stack_mutations_prevent_a_clipped_bottom_layer():
    reorder = _function_body("_commitLayerReorderDrop")
    delete = _function_body("deleteLayer")
    up = _function_body("moveLayerUp")
    down = _function_body("moveLayerDown")
    assert "normalizeStack(candidate)" in reorder
    assert "normalizeStack(_psdLayers)" in delete
    assert "normalizeStack(_psdLayers)" in up
    assert "normalizeStack(_psdLayers)" in down


def test_pass_132_runtime_module_is_ordered_cache_busted_and_manifested():
    module_match = re.search(r'js/canvas/layer/clipping-mask\.js\?v=[^"\']+', HTML)
    canvas_tag = "paint-booth-3-canvas.js?v="
    assert module_match, "clipping-mask runtime script must carry a cache token"
    assert HTML.index(module_match.group(0)) < HTML.index(canvas_tag)
    manifest = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")
    assert '"js/canvas/layer/clipping-mask.js"' in manifest
