'use strict';
// Broker preflight only: current source confirmation is necessary, not a UV calibration.
const geometry=require('./geometry-authority.cjs');
const norm=s=>String(s||'').toLowerCase().trim().replace(/^(?:the|my)\s+/,'').replace(/\s+/g,' ');
// These aliases do not broaden a door/fender into a whole side or a rail into a roof.
const synonyms={bonnet:'hood','engine hood':'hood','hood panel':'hood',
  'driver side':'left side','drivers side':'left side','passenger side':'right side','passengers side':'right side',
  'roof panel':'roof','trunk lid':'trunk','deck lid':'trunk',decklid:'trunk',boot:'trunk'};
const canonical=s=>synonyms[norm(s)]||norm(s);
const pairs={'both sides':['left side','right side'],sides:['left side','right side'],
  'both doors':['left door','right door'],doors:['left door','right door'],
  'both fenders':['left fender','right fender'],fenders:['left fender','right fender']};
function requiredParts(app,a){
  if(!a)return [];
  const out=[];
  const add=p=>(Array.isArray(p)?p:[p]).forEach(x=>{if(typeof x==='string'&&norm(x))out.push(norm(x));});
  if(a.region)add(a.region.part);
  add(a.part);
  if(app==='do'&&a.frame){
    const target=t=>{
      if(Array.isArray(t)){t.forEach(target);return;}
      if(!t||typeof t!=='object')return;
      if(t.kind==='part'||t.parts||t.part)add(t.parts||t.part);
      if(t.between)target(t.between);
    };
    for(const op of a.frame.ops||[]){
      if(op)for(const t of [op.target,op.source,op.keep,op.except])target(t);
    }
    target(a.frame.keep);target(a.frame.except);
  }
  if(app==='kit'&&String(a.action||'place').toLowerCase()==='place'&&/^(sponsor|number)$/i.test(a.kit||'')){
    add(a.parts);add(a.places);
    // Kit slots are resolved by a different registry, not the confirmed-box reader.
    if(!out.length)out.push('kit placement');
  }
  return Array.from(new Set(out));
}
function check(app,args,state){
  const named=requiredParts(app,args);
  if(!named.length)return null;
  const caps=geometry.qualifiedCapabilities(state&&state.editor_capabilities);
  const panel=caps&&caps.panel_locations;
  const parts=panel&&panel.status==='current'&&Array.isArray(panel.parts)?panel.parts:[];
  const known=Array.from(new Set(parts.map(p=>norm(p.name)).filter(Boolean)));
  const bad=named.filter(p=>{
    const needs=pairs[p]||[p];
    return !needs.every(n=>{
      const matches=parts.filter(q=>canonical(q.name)===canonical(n));
      // Several separate pieces cannot silently become one rectangular target.
      return new Set(matches.map(q=>JSON.stringify(q.bbox))).size===1;
    });
  });
  const kit=app==='kit'&&/^(sponsor|number)$/i.test((args||{}).kit||'')&&String((args||{}).action||'place').toLowerCase()==='place';
  if(!bad.length&&!kit)return null;
  return {changed:false,refused:true,unknown_part:bad,
    geometry_status:panel&&panel.status||'unavailable',known_parts:known,
    reason:kit?'kit_geometry_unverified':'part_geometry_unconfirmed',
    rule:kit?'Nothing was placed. Sponsor and number kits use a separate placement registry whose geometry has not been verified against this source. Offer the manual kit preview so the painter can inspect placement before applying it.':
      'Nothing was changed. Confirm the '+bad.join(' / ')+' on the current sheet first. Use spb_request_parts to let the painter mark it, or ask them to identify the area in the Car parts view. A library match, whole-side box or old document does not confirm this target.',
    scope:'Fresh broker preflight; downstream target consumption and atomic source-switch protection still require verification.'};
}
async function refusal(app,args,readState){
  if(!requiredParts(app,args).length)return null;
  let state=null;
  try{const r=await readState();if(r&&r.status<400&&r.json&&r.json.ok!==false)state=r.json.result;}catch(_){/* named requests fail closed */}
  return check(app,args,state);
}
function toolDescription(name,original){
  return name==='spb_kit'?original+' Automatic sponsor/number placement is withheld until the placement registry is verified for the current source. Offer the manual kit preview for painter inspection. Spec proposals/checks and existing kit removal retain their own rules.':original;
}
module.exports={requiredParts,check,refusal,toolDescription};
