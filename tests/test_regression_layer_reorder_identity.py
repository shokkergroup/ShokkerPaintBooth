from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
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


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    depth = 1
    index = match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[match.start() : index]


def test_pass_128_panel_passes_real_stack_indices_without_double_reversal():
    start = _function_body("onLayerDragStart")
    over = _function_body("onLayerDragOver")
    assert "const layer = _psdLayers[arrayIdx]" in start
    assert "const targetLayer = _psdLayers[arrayIdx]" in over
    assert "_psdLayers.length - 1" not in start
    assert "_psdLayers.length - 1" not in over
    assert "sourceLayerId: layer.id" in start
    assert "targetLayerId = targetLayer.id" in over


def test_pass_128_locked_layers_are_not_drag_sources_in_ui_or_code():
    start = _function_body("onLayerDragStart")
    assert 'data-layer-reorder-locked="${reorderLocked ? \'true\' : \'false\'}"' in CANVAS
    assert 'draggable="${reorderLocked ? \'false\' : \'true\'}"' in CANVAS
    assert "if (!layer || layer.locked)" in start
    assert "e.preventDefault()" in start
    assert "effectAllowed = 'none'" in start
    assert "unlock to reorder" in start


def test_pass_128_drop_resolves_stable_ids_and_translates_visual_edge_once():
    body = _function_body("_commitLayerReorderDrop")
    lock = body.index("if (sourceLayer.locked)")
    remove = body.index("candidate.splice(sourceIdx, 1)")
    target = body.index("candidate.findIndex(l => l.id === targetLayerId)")
    insert = body.index("insertAbove ? targetAfterRemoval + 1 : targetAfterRemoval")
    no_op = body.index("const unchanged =")
    history = body.index("_pushLayerStackUndo('reorder layer')")
    mutation = body.index("_psdLayers.splice(0, _psdLayers.length, ...candidate)")
    assert lock < remove < target < insert < no_op < history < mutation


def test_pass_128_same_position_and_locked_drops_are_history_free():
    body = _function_body("_commitLayerReorderDrop")
    history = body.index("_pushLayerStackUndo('reorder layer')")
    assert body.index("sourceLayerId === targetLayerId") < history
    assert body.index("if (sourceLayer.locked)") < history
    assert body.index("if (unchanged) return false") < history


def test_pass_128_reorder_algorithm_moves_the_visible_source_to_each_drop_edge():
    source = _function_source("_commitLayerReorderDrop")
    script = f"""
let _psdLayers = [];
let history = 0;
const messages = [];
const window = {{}};
function _pushLayerStackUndo() {{ history++; }}
function recompositeFromLayers() {{}}
function renderLayerPanel() {{}}
function drawLayerBounds() {{}}
function triggerPreviewRender() {{}}
function showToast(message) {{ messages.push(message); }}
{source}
function reset(items) {{ _psdLayers = items.map(x => ({{ id:x, name:x, locked:false }})); history = 0; }}
function ids() {{ return _psdLayers.map(x => x.id).join(''); }}
function check(value, message) {{ if (!value) throw new Error(message); }}

reset(['A','B','C']);
check(_commitLayerReorderDrop('C','B',true) === false, 'same visual slot must be a no-op');
check(ids() === 'ABC' && history === 0, 'same slot changed state/history');
check(_commitLayerReorderDrop('C','B',false) === true, 'top layer did not move below B');
check(ids() === 'ACB' && history === 1, 'wrong order below B');

reset(['A','B','C']);
check(_commitLayerReorderDrop('A','C',true) === true, 'bottom layer did not move above C');
check(ids() === 'BCA' && history === 1, 'wrong order above C');

reset(['A','B','C']);
_psdLayers[1].locked = true;
check(_commitLayerReorderDrop('B','A',false) === false, 'locked source moved');
check(ids() === 'ABC' && history === 0 && messages.length > 0, 'locked refusal was not truthful');
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stderr


def test_pass_128_runtime_is_cache_busted():
    assert "spb93-layer-reorder-identity-20260717" in HTML
    assert "spb93-layer-opacity-gesture-20260717" in HTML
