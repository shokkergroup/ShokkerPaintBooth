'use strict';
// Read-response qualification only. This never routes tools or edits paint.
const LEGACY_READS=new Set(['spb_status','spb_get_state','spb_get_car_map']);
const CONFIRMED=new Set(['buyer-taught box','confirmed island label']);
const copy=x=>JSON.parse(JSON.stringify(x));
function validConfirmedPart(p){
  return p&&CONFIRMED.has(p.evidence)&&Array.isArray(p.bbox)&&p.bbox.length===4&&
    p.bbox.every(n=>Number.isFinite(n)&&n>=0&&n<=1)&&p.bbox[2]>p.bbox[0]&&p.bbox[3]>p.bbox[1];
}
function qualifiedCapabilities(evidence){
  if(!evidence||!evidence.panel_locations)return evidence;
  const result=copy(evidence),geometry=result.panel_locations;
  const parts=Array.isArray(geometry.parts)?geometry.parts:[];
  geometry.parts=parts.filter(p=>geometry.status==='current'&&validConfirmedPart(p));
  geometry.withheld_library_parts=(Number(geometry.withheld_library_parts)||0)+parts.length-geometry.parts.length;
  geometry.geometry_authority='buyer-confirmed current-source extents only';
  return result;
}
function qualifySnapshot(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))return raw;
  const data=copy(raw),missing=new Set(data.parts_needing_confirmation||[]);
  // The local broker consumes this binding. It includes a local path and is not model context.
  delete data.execution_source;
  const seen=new Set();
  let withheld=Number(data.library_parts_withheld)||0;
  function removeParts(parts){
    const kept=[];
    for(const p of parts||[]){
      // Untagged legacy grid cells do not carry a calibration receipt.
      if(validConfirmedPart(p))kept.push(p);
      else{
        const key=JSON.stringify([p&&p.name,p&&(p.at||p.cells||p.bbox||p.rect)]);
        if(!seen.has(key)){withheld++;seen.add(key);}
        if(p&&p.name)missing.add(p.name);
      }
    }
    return kept;
  }
  if(data.car&&(typeof data.car==='object'||typeof data.car==='string')){
    const car=data.car;
    if(typeof car==='object'&&Array.isArray(car.parts))removeParts(car.parts);
    data.car={heuristic_layout:typeof car==='string'?car:(car.heuristic_layout||car.recognised_as||car.car||null),
      identity_verified:false,geometry_verified:false,
      note:'Library recognition is a heuristic. Use exact source identity and current buyer-confirmed extents; no library geometry is supplied.'};
    if(typeof car==='object'&&car.layer_roles)data.car.layer_roles=car.layer_roles;
  }
  if(Array.isArray(data.parts))data.parts=removeParts(data.parts);
  if(data.recognised_as){data.heuristic_layout={label:data.recognised_as,identity_verified:false,geometry_verified:false};delete data.recognised_as;}
  if(data.template_identity&&data.template_identity.recognized_layout){
    data.template_identity.heuristic_layout={label:data.template_identity.recognized_layout,identity_verified:false,geometry_verified:false};
    delete data.template_identity.recognized_layout;
  }
  if(data.editor_capabilities)data.editor_capabilities=qualifiedCapabilities(data.editor_capabilities);
  if(withheld){
    data.library_parts_withheld=withheld;
    data.parts_needing_confirmation=Array.from(missing);
    if(Array.isArray(data.key_parts_missing))data.key_parts_missing=Array.from(new Set(data.key_parts_missing.concat(data.parts_needing_confirmation)));
    data.geometry_note='Withheld library/untagged part coordinates. A recognised layout is not calibrated geometry. Use spb_assistant_context include_paint:true for buyer-confirmed current-source extents, or ask the painter to identify the part.';
  }
  return data;
}
function qualifyLegacyTool(name,data){return LEGACY_READS.has(name)?qualifySnapshot(data):data;}
function toolDescription(name,original){
  if(!LEGACY_READS.has(name))return original;
  const purpose={spb_status:'Read current app status, paint, layers and zones.',spb_get_state:'Read current paint state, layers, zones and conversation.',spb_get_car_map:'Read car-role evidence and part confirmation status.'};
  return purpose[name]+' Library recognition is heuristic; untagged/library coordinates are withheld and are not confirmed paint targets. Use exact template_identity.source_reference evidence when available. Current buyer-confirmed source extents are available through spb_assistant_context include_paint:true; missing parts require painter confirmation. A car name or catalog template does not establish calibrated UV geometry.';
}
module.exports={qualifiedCapabilities,qualifySnapshot,qualifyLegacyTool,toolDescription};
