"""SPB-93 Pass 35: single-owner Escape and extracted Zone keyboard island."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return json.loads(result.stdout)


def test_lasso_escape_is_consumed_once_while_plain_escape_reaches_layer_owner():
    payload = run_node(r"""
const handlers=[];
const elements={};
global.document={
  addEventListener:(type,fn)=>{if(type==='keydown')handlers.push(fn);},
  getElementById:id=>elements[id]||null,
  __spbZoneKeyboardControlsInstalled:false
};
const api=require('./js/zones/zone-keyboard-controls.js');
let mode='lasso', active=true, points=[{x:1,y:1},{x:2,y:2}], layerActions=0, toast='';
api.install({
  isTextEntryTarget:()=>false,
  getCanvasMode:()=>mode,
  getLassoActive:()=>active,
  getLassoPoints:()=>points,
  setLassoActive:v=>{active=v;},
  setLassoPoints:v=>{points=v;},
  hideLassoPreview:()=>{}, showToast:v=>{toast=v;}
});
// Installing twice must not create duplicate owners.
api.install({isTextEntryTarget:()=>false});
handlers.push(e=>{if(!e.defaultPrevented)layerActions++;});
function event(key){return {
  key, target:{tagName:'DIV'}, defaultPrevented:false, immediate:false,
  ctrlKey:false,metaKey:false,altKey:false,shiftKey:false,
  preventDefault(){this.defaultPrevented=true;},
  stopImmediatePropagation(){this.immediate=true;}
};}
function dispatch(e){for(const fn of handlers){fn(e);if(e.immediate)break;}return e;}
const lassoEvent=dispatch(event('Escape'));
mode='brush'; const plainEvent=dispatch(event('Escape'));
process.stdout.write(JSON.stringify({
  active,points,toast,layerActions,
  lassoPrevented:lassoEvent.defaultPrevented,lassoStopped:lassoEvent.immediate,
  plainPrevented:plainEvent.defaultPrevented,handlerCount:handlers.length
}));
""")
    assert payload == {
        "active": False,
        "points": [],
        "toast": "Lasso cancelled",
        "layerActions": 1,
        "lassoPrevented": True,
        "lassoStopped": True,
        "plainPrevented": False,
        "handlerCount": 3,
    }


def test_overlay_escape_consumes_event_and_closes_only_the_owned_overlay():
    payload = run_node(r"""
const handlers=[]; let closed=0, layerActions=0;
const elements={finishBrowserOverlay:{classList:{contains:v=>v==='active'}}};
global.document={addEventListener:(t,f)=>{if(t==='keydown')handlers.push(f);},getElementById:id=>elements[id]||null};
const api=require('./js/zones/zone-keyboard-controls.js');
api.install({isTextEntryTarget:()=>false,closeFinishBrowser:()=>{closed++;}});
handlers.push(e=>{if(!e.defaultPrevented)layerActions++;});
const e={key:'Escape',target:{tagName:'DIV'},defaultPrevented:false,ctrlKey:false,metaKey:false,altKey:false,shiftKey:false,preventDefault(){this.defaultPrevented=true;}};
for(const fn of handlers)fn(e);
process.stdout.write(JSON.stringify({closed,layerActions,prevented:e.defaultPrevented}));
""")
    assert payload == {"closed": 1, "layerActions": 0, "prevented": True}


def test_shift_m_owns_zone_mute_while_plain_m_remains_ellipse_shortcut():
    payload = run_node(r"""
const handlers=[];
global.document={addEventListener:(t,f)=>{if(t==='keydown')handlers.push(f);},getElementById:()=>null};
const api=require('./js/zones/zone-keyboard-controls.js');
let muted=0;
api.install({isTextEntryTarget:()=>false,toggleZoneMute:()=>{muted++;},getSelectedZoneIndex:()=>2});
function fire(shiftKey){const e={key:'m',target:{tagName:'DIV'},defaultPrevented:false,ctrlKey:false,metaKey:false,altKey:false,shiftKey,preventDefault(){this.defaultPrevented=true;}};for(const fn of handlers)fn(e);return e.defaultPrevented;}
process.stdout.write(JSON.stringify({plain:fire(false),shift:fire(true),muted}));
""")
    assert payload == {"plain": False, "shift": True, "muted": 1}


def test_monster_uses_extracted_installer_and_has_no_duplicate_shortcut_listeners():
    source = read("paint-booth-2-state-zones.js")
    assert "SPBZoneKeyboardControls.install" in source
    assert "isTextEntryTarget: _isTextEntryTargetForGlobalUndo" in source
    assert "getLassoPoints: () =>" in source
    assert "setLassoPoints: (points) =>" in source
    assert "IMPROVEMENT 48: keyboard shortcut" not in source
    assert "ADDITIONAL KEYBOARD SHORTCUTS" not in source
    assert "Removed last vertex" not in source


def test_module_is_loaded_before_installer_and_runtime_guard_is_green():
    html = read("paint-booth-v2.html")
    assert html.index("js/zones/zone-keyboard-controls.js") < html.index("paint-booth-2-state-zones.js")
    result = subprocess.run(
        ["node", "scripts/spb_guard_zone_keyboard_controls.js"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    assert "guard passed" in result.stdout

