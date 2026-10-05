"""SPB-93 Pass 133: Layer visibility and Alt+eye isolation are transactional."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.end(), 1, match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_133_alt_eye_is_accessible_and_routes_to_reversible_solo():
    assert 'class="layer-eye-toggle"' in CANVAS
    assert 'aria-pressed="${vis ? \'true\' : \'false\'}"' in CANVAS
    assert "event.altKey ? toggleLayerSolo" in CANVAS
    assert "Alt+click to isolate/restore" in CANVAS


def test_pass_133_solo_restore_and_noop_history_are_functional():
    start = CANVAS.index("var _layerSoloVisibilitySnapshot = null;")
    end = CANVAS.index("// SPB-93 Pass 56", start)
    implementation = CANVAS[start:end]
    script = f"""
const events = [];
const _psdLayers = [
  {{id:'A',name:'Base',visible:true}},
  {{id:'B',name:'Stripe',visible:false}},
  {{id:'C',name:'Shade',visible:true}}
];
const _psdLayersLoaded = true;
function _pushLayerStackUndo(label) {{ events.push(['history', label]); }}
function recompositeFromLayers() {{ events.push(['composite']); }}
function renderLayerPanel() {{ events.push(['panel']); }}
function triggerPreviewRender() {{ events.push(['preview']); }}
function refreshActiveToolLabel() {{ events.push(['label']); }}
function showToast(message) {{ events.push(['toast', message]); }}
{implementation}
function visible() {{ return _psdLayers.map(layer => layer.visible); }}
const isolated = toggleLayerSolo('B');
const afterIsolate = visible();
const restored = toggleLayerSolo('B');
const afterRestore = visible();
const noOpSolo = soloLayer('A');
const afterSolo = visible();
const noOpRepeat = soloLayer('A');
const afterRepeat = visible();
console.log(JSON.stringify({{isolated,afterIsolate,restored,afterRestore,noOpSolo,afterSolo,noOpRepeat,afterRepeat,events}}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["isolated"] is True
    assert payload["afterIsolate"] == [False, True, False]
    assert payload["restored"] is True
    assert payload["afterRestore"] == [True, False, True]
    assert payload["noOpSolo"] is True and payload["afterSolo"] == [True, False, False]
    assert payload["noOpRepeat"] is False and payload["afterRepeat"] == [True, False, False]
    histories = [event for event in payload["events"] if event[0] == "history"]
    assert [event[1] for event in histories] == ["isolate layer", "restore layer visibility", "solo layer"]
    assert len([event for event in payload["events"] if event[0] == "preview"]) == 3


def test_pass_133_visibility_commands_share_one_commit_path_and_history_restore_clears_solo():
    toggle = _function_body("toggleLayerVisible")
    solo = _function_body("soloLayer")
    show_all = _function_body("showAllLayers")
    restore = _function_body("_restoreLayerStack")
    assert "_applyLayerVisibilityMap" in toggle
    assert "_applyLayerVisibilityMap" in solo
    assert "_applyLayerVisibilityMap" in show_all
    assert "_layerSoloVisibilitySnapshot = null" in restore
    apply_body = _function_body("_applyLayerVisibilityMap")
    assert apply_body.index("if (!changes.length) return false") < apply_body.index("_pushLayerStackUndo")
    assert apply_body.index("_pushLayerStackUndo") < apply_body.index("changes.forEach")


def test_pass_133_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-visibility-solo-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
