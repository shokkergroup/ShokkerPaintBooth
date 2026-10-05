from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_extracted_zone_workflow_module_is_installed_once_with_lexical_state():
    source = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
    assert "window.SPBZoneWorkflowControls.install({" in source
    assert "!window.__spbZoneWorkflowInstalled" in source
    assert "getZones: () => zones" in source
    assert "cloneZoneState: (zone, options) => _cloneZoneState(zone, options)" in source
    assert "triggerPreviewRender: () => _requestZoneLivePreview()" in source
    assert "zoneHasAnyMaterial: (zone) => zoneHasAnyMaterial(zone)" in source
    assert "zoneHasMaterialStack: (zone) => zoneHasMaterialStack(zone)" in source
    assert "zoneMaterialMixDisplay: (zone) => zoneMaterialMixDisplay(zone)" in source
    assert "maskAny: (mask) => _maskAny(mask)" in source


def test_extracted_zone_workflow_preserves_material_mask_and_ui_semantics():
    script = r"""
global.window = global;
const listeners = [];
const intervals = [];
const toasts = [];
const autosaveBadge = {textContent:''};
global.document = {
  addEventListener(type, handler){listeners.push([type, handler.name]);},
  getElementById(id){return id === 'autosaveBadge' ? autosaveBadge : null;},
  querySelectorAll(){return [];}
};
global.localStorage = {
  getItem(key){return key === 'shokker_autosave' ? JSON.stringify({_autosave_time:Date.now()}) : null;}
};
global.setInterval = function(handler, ms){intervals.push([handler.name,ms]); return intervals.length;};
global.confirm = function(){return false;};
require('./js/zones/workflow-controls.js');

let activeZones = [{
  name:'Easy Mix',base:null,finish:null,color:'#224466',colorMode:'quick',muted:false,
  materialStack:[{id:'metal'},{id:'carbon'}],regionMask:{any:true}
}];
let maskCalls = 0;
SPBZoneWorkflowControls.install({
  getZones(){return activeZones;},
  getSelectedZoneIndex(){return 0;},
  setSelectedZoneIndex(){},
  pushZoneUndo(){},pushZoneUndoCoalesced(){},renderZones(){},triggerPreviewRender(){},
  showToast(message){toasts.push(message);},cloneZoneState(zone){return Object.assign({},zone);},
  maxZones:50,isTextEntryTarget(){return false;},validateZonesBeforeRender(){return [];},
  getPaintImageData(){return null;},getPsdLayers(){return [];},
  zoneHasMissingSourceLayer(){return false;},
  zoneHasMaterialStack(zone){return !!(zone.materialStack && zone.materialStack.length);},
  zoneHasAnyMaterial(zone){return !!(zone.base || zone.finish || (zone.materialStack && zone.materialStack.length));},
  zoneMaterialMixDisplay(){return [{name:'Metal'},{name:'Carbon'}];},
  maskAny(mask){maskCalls += 1; return !!mask.any;}
});

const statusPreserved = getZoneStatus(activeZones[0]) === 'ok';
const diagnosticPreserved = getZoneDiagnostic(activeZones[0]).startsWith('Material mix (Metal + Carbon)');
const badgePreserved = getZoneStatusBadgeHTML({base:'solid',finish:null,color:null,colorMode:'none',regionMask:{any:false}})
  .includes('No color/region ' + String.fromCharCode(0x2014) + ' zone targets nothing');
activeZones = [];
showCombinedWarnings();
const warningPreserved = toasts[toasts.length - 1].charCodeAt(toasts[toasts.length - 1].length - 1) === 0x2713;
const emptyGuide = getEmptyStateGuide();
const emptyGuidePreserved = emptyGuide.includes(String.fromCodePoint(0x1F3A8)) && emptyGuide.includes('+ Add First Zone');
markDirty();
const dirtyPreserved = autosaveBadge.textContent.charCodeAt(0) === 0x26A0;
markClean();
const cleanPreserved = autosaveBadge.textContent.charCodeAt(0) === 0x2713;
console.log(JSON.stringify({
  statusPreserved,diagnosticPreserved,badgePreserved,warningPreserved,emptyGuidePreserved,
  dirtyPreserved,cleanPreserved,maskCalls,listeners:listeners.length,intervals:intervals.length
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "statusPreserved": True,
        "diagnosticPreserved": True,
        "badgePreserved": True,
        "warningPreserved": True,
        "emptyGuidePreserved": True,
        "dirtyPreserved": True,
        "cleanPreserved": True,
        "maskCalls": 3,
        "listeners": 1,
        "intervals": 1,
    }
