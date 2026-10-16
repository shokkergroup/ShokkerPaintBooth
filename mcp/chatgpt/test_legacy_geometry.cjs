'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),G=require('./geometry-authority.cjs');
const e=path.resolve(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910');
const receipt=JSON.parse(fs.readFileSync(path.join(e,'legacy-geometry-baseline-2026-10-11T00-37-30-892Z.json'),'utf8'));
for(const {tool,data} of receipt.calls){
 const before=JSON.stringify(data),out=G.qualifyLegacyTool(tool,data);
 assert.equal(JSON.stringify(data),before,'Read qualification never mutates received app data');
 const car=out.car||out;
 assert.equal(car.recognised_as,undefined);assert.ok(car.heuristic_layout);
 assert.ok(!car.parts||car.parts.length===0);assert.ok(!out.parts||out.parts.length===0);
 assert.equal(out.library_parts_withheld,8);assert.ok(out.parts_needing_confirmation.includes('hood'));
 if(out.car)assert.equal(out.car.geometry_verified,false);
 if(out.template_identity)assert.deepEqual(out.template_identity.source_reference,data.template_identity.source_reference,'Unavailable source proof stays unavailable');
 for(const key of ['layers','zones','convo','saved_design_brief','recent_changes'])if(data[key])assert.deepEqual(out[key],data[key]);
 if(out.key_parts_missing)assert.ok(out.key_parts_missing.includes('hood'));
 assert.deepEqual(G.qualifyLegacyTool(tool,out),out,'Qualification is idempotent');
 assert.equal(G.qualifyLegacyTool('spb_preview',data),data,'Unrelated tools are not intercepted');
}
const taught={name:'hood',bbox:[.1,.2,.3,.4],evidence:'buyer-taught box'};
const geometry={panel_locations:{status:'current',parts:[taught,{...taught,name:'bad',bbox:[0,0,2,1]},{...taught,name:'zero',bbox:[0,0,0,1]},{name:'library door',bbox:[0,0,.5,.5],evidence:'active car-library box'}]}};
const valid=G.qualifiedCapabilities(geometry);assert.deepEqual(valid.panel_locations.parts,[taught]);assert.equal(valid.panel_locations.withheld_library_parts,3);
geometry.panel_locations.status='stale';assert.deepEqual(G.qualifiedCapabilities(geometry).panel_locations.parts,[]);
const malformed={panel_locations:{status:'current',parts:[{...taught,bbox:[0,0,NaN,1]},{...taught,bbox:['0',0,.2,1]}]}};
assert.deepEqual(G.qualifiedCapabilities(malformed).panel_locations.parts,[]);
assert.equal(G.qualifyLegacyTool('spb_status',null),null);
console.log('PASS actual legacy tool receipts: eight library locations withheld; source/paint/discussion unchanged; idempotent; valid current confirmed extents retained; malformed/stale geometry rejected.');
