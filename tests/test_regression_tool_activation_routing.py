import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_owned_tools_align_toolbar_on_activation_without_changing_exclude():
    script = r"""
global.window = { toolbarEditMode: 'layer' };
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => ({ id: 'L1' });
require('./js/canvas/dispatch.js');
const rect = window.alignToolbarModeForToolActivation('rect');
window.toolbarEditMode = 'layer';
const exclude = window.alignToolbarModeForToolActivation('spatial-exclude');
window.toolbarEditMode = 'layer';
const grab = window.alignToolbarModeForToolActivation('grab-object');
window.toolbarEditMode = 'layer';
const zonePick = window.alignToolbarModeForToolActivation('zone-pick');
window.toolbarEditMode = 'zone';
const clone = window.alignToolbarModeForToolActivation('clone');
process.stdout.write(JSON.stringify({ rect, exclude, grab, zonePick, clone }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "rect": "zone",
        "exclude": "zone",
        "grab": "zone",
        "zonePick": "zone",
        "clone": "layer",
    }


def test_easy_eight_tools_have_truthful_activation_targets_in_zone_and_layer_modes():
    script = r"""
global.window = { toolbarEditMode: 'zone' };
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => ({ id: 'editable' });
require('./js/canvas/dispatch.js');
const tools = ['eyedropper', 'spatial-exclude', 'wand', 'lasso', 'rect', 'brush', 'fill', 'erase'];
const inZone = Object.fromEntries(tools.map((tool) => [tool, window.getToolbarToolActivation(tool)]));
window.toolbarEditMode = 'layer';
const inLayer = Object.fromEntries(tools.map((tool) => [tool, window.getToolbarToolActivation(tool)]));
process.stdout.write(JSON.stringify({ inZone, inLayer }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    verdicts = json.loads(result.stdout.splitlines()[-1])
    assert verdicts["inZone"]["eyedropper"] == {"allowed": True, "mode": "zone"}
    assert verdicts["inLayer"]["eyedropper"] == {"allowed": True, "mode": "layer"}
    for tool in ("spatial-exclude", "wand", "lasso", "rect"):
        assert verdicts["inZone"][tool]["allowed"] is True
        assert verdicts["inZone"][tool]["mode"] == "zone"
        assert verdicts["inLayer"][tool]["allowed"] is True
        assert verdicts["inLayer"][tool]["mode"] == "zone"
    for tool in ("brush", "fill", "erase"):
        assert verdicts["inZone"][tool] == {"allowed": True, "mode": "zone"}
        assert verdicts["inLayer"][tool] == {"allowed": True, "mode": "layer"}


def test_layer_only_tool_without_editable_target_refuses_before_arming():
    script = r"""
global.window = { toolbarEditMode: 'zone' };
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => null;
require('./js/canvas/dispatch.js');
const clone = window.getToolbarToolActivation('clone');
const text = window.getToolbarToolActivation('text');
const rect = window.getToolbarToolActivation('rect');
process.stdout.write(JSON.stringify({ clone, text, rect }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    verdicts = json.loads(result.stdout.splitlines()[-1])
    assert verdicts["clone"]["allowed"] is False
    assert verdicts["clone"]["mode"] == "zone"
    assert "editable Layer" in verdicts["clone"]["reason"]
    assert verdicts["text"]["allowed"] is True
    assert verdicts["text"]["mode"] == "layer"
    assert verdicts["rect"]["allowed"] is True
    assert verdicts["rect"]["mode"] == "zone"


def test_dual_paint_tools_refuse_missing_layer_target_but_still_work_in_zone_mode():
    script = r"""
global.window = { toolbarEditMode: 'layer' };
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => null;
require('./js/canvas/dispatch.js');
window.toolbarEditMode = 'layer';
const refused = ['brush', 'erase', 'fill', 'gradient'].map((mode) => window.getToolbarToolActivation(mode));
window.toolbarEditMode = 'zone';
const zoneBrush = window.getToolbarToolActivation('brush');
window.toolbarEditMode = 'layer';
global.getSelectedEditableLayer = () => ({ id: 'editable' });
const layerBrush = window.getToolbarToolActivation('brush');
process.stdout.write(JSON.stringify({ refused, zoneBrush, layerBrush }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    verdicts = json.loads(result.stdout.splitlines()[-1])
    assert all(verdict["allowed"] is False for verdict in verdicts["refused"])
    assert all("editable Layer" in verdict["reason"] for verdict in verdicts["refused"])
    assert verdicts["zoneBrush"] == {"allowed": True, "mode": "zone"}
    assert verdicts["layerBrush"] == {"allowed": True, "mode": "layer"}


def test_manual_mode_switch_hands_off_incompatible_active_tool():
    script = r"""
const armed = [];
global.window = {
  toolbarEditMode: 'zone',
  canvasMode: 'rect',
  setCanvasMode(mode){ armed.push(mode); this.canvasMode = mode; }
};
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => ({ id: 'L1' });
require('./js/canvas/dispatch.js');
const layer = window.setToolbarEditMode('layer', { silent: true });
window.canvasMode = 'clone';
const zone = window.setToolbarEditMode('zone', { silent: true });
process.stdout.write(JSON.stringify({ layer, zone, armed }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "layer": "layer",
        "zone": "zone",
        "armed": ["layer-move", "brush"],
    }


def test_manual_layer_switch_cannot_leave_spatial_exclude_armed():
    script = r"""
const armed = [];
global.window = {
  toolbarEditMode: 'zone',
  canvasMode: 'spatial-exclude',
  setCanvasMode(mode){ armed.push(mode); this.canvasMode = mode; }
};
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => ({ id: 'L1' });
require('./js/canvas/dispatch.js');
const mode = window.setToolbarEditMode('layer', { silent: true });
process.stdout.write(JSON.stringify({ mode, active: window.canvasMode, armed }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "mode": "layer",
        "active": "layer-move",
        "armed": ["layer-move"],
    }


def test_manual_layer_mode_refuses_without_editable_target_but_creator_route_can_enter():
    script = r"""
global.window = { toolbarEditMode: 'zone', canvasMode: 'rect' };
global.localStorage = { getItem(){ return null; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => null;
require('./js/canvas/dispatch.js');
const refused = window.setToolbarEditMode('layer', { silent: true });
const creator = window.alignToolbarModeForToolActivation('text');
process.stdout.write(JSON.stringify({ refused, creator, current: window.toolbarEditMode }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "refused": "zone",
        "creator": "layer",
        "current": "layer",
    }


def test_flat_startup_does_not_restore_a_stale_layer_mode_preference():
    script = r"""
global.window = { toolbarEditMode: 'layer' };
global.localStorage = { getItem(){ return 'layer'; }, setItem(){} };
global.document = { readyState: 'complete' };
global.getSelectedEditableLayer = () => null;
require('./js/canvas/dispatch.js');
process.stdout.write(JSON.stringify({ current: window.toolbarEditMode }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == {"current": "zone"}


def test_canvas_routes_before_arming_the_new_tool():
    body = CANVAS[
        CANVAS.index("function setCanvasMode(mode)") :
        CANVAS.index("window.setCanvasMode = setCanvasMode;")
    ]
    preflight = body.index("window.getToolbarToolActivation(mode)")
    refusal = body.index("if (!activation.allowed)")
    route = body.index("window.alignToolbarModeForToolActivation(mode)")
    arm = body.index("canvasMode = mode")
    assert preflight < refusal < route < arm
    assert "return false;" in body[refusal:route]
    assert "dispatch.js?v=spb93-easy-eight-20260903a" in HTML
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in HTML
