/* Behavior checks of the production serializer and shared overlay controller. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const catalogContext={console:{log(){},warn(){}},setTimeout(){}};vm.createContext(catalogContext);
vm.runInContext(fs.readFileSync('paint-booth-0-finish-data.js','utf8'),catalogContext);
const legacyGroups=JSON.parse(vm.runInContext('JSON.stringify(SPEC_PATTERN_GROUPS)',catalogContext));
for(const file of ['catalog-data.js','catalog-install.js'])vm.runInContext(fs.readFileSync('js/spec-overlays/'+file,'utf8'),catalogContext);
const installedGroups=JSON.parse(vm.runInContext('JSON.stringify(SPEC_PATTERN_GROUPS)',catalogContext));
for(const [family,ids] of Object.entries(legacyGroups))for(const id of ids)assert(installedGroups[family].includes(id),'Installing a same-named surface family must preserve legacy '+id);
const source=fs.readFileSync('paint-booth-5-api-render.js','utf8');
const serializer=source.slice(source.indexOf('function _mapSpecPatternEntry('),source.indexOf("if (typeof window !== 'undefined') window._mapSpecPatternEntry"));
const keys=['specPatternStack','overlaySpecPatternStack','thirdOverlaySpecPatternStack','fourthOverlaySpecPatternStack','fifthOverlaySpecPatternStack'];
const apiKeys=['spec_pattern_stack','overlay_spec_pattern_stack','third_overlay_spec_pattern_stack','fourth_overlay_spec_pattern_stack','fifth_overlay_spec_pattern_stack'];
const sample={pattern:'spov2_example',opacity:37,channels:'',range:0,offsetX:0,offsetY:1,scale:.6,rotation:72,boxSize:40,seed:517,render_version:2,muted:true,solo:true};
const c={SPEC_PATTERNS:[{id:'spov2_example'}],zones:[{name:'Target',base:'metallic'}],pushZoneUndo(){},renderZones(){},triggerPreviewRender(){},showToast(){}};c.window=c;vm.createContext(c);vm.runInContext(serializer,c);
const mapped=JSON.parse(JSON.stringify(c._mapSpecPatternEntry(sample)));
assert.equal(mapped.opacity,.37);assert.equal(mapped.range,0);assert.equal(mapped.channels,'');assert.equal(mapped.offset_x,0);assert.equal(mapped.seed,517);assert.equal(mapped.render_version,2);assert.equal(mapped.muted,true);assert.equal(mapped.solo,true);
c.buildServerZonesForRender=rows=>JSON.parse(JSON.stringify(rows));c._buildSpecPatternLayer=id=>({...sample,pattern:id});
vm.runInContext(fs.readFileSync('js/spec-overlays/picker.js','utf8'),c);
for(let tier=0;tier<5;tier++){
 c.zones[0][keys[tier]]=[{...sample,opacity:0},{...sample,opacity:37}];
 const before=JSON.stringify(c.zones),result=c.SPBSpecOverlayPicker.transient('spov2_example',{zone:0,tier,index:1});
 assert.equal(JSON.stringify(c.zones),before,'Transient previews cannot change the recipe');
 assert.equal(result[0][apiKeys[tier]].length,2);assert.equal(result[0][apiKeys[tier]][1].opacity,.37);
 assert.equal(result.overlayTarget,result[0]);
 const saved=JSON.parse(JSON.stringify(result));assert.equal(saved[0][apiKeys[tier]][1].seed,517);
 assert.equal(saved[0][apiKeys[tier]][1].scale,.6);assert.equal(saved[0][apiKeys[tier]][1].box_size,40);
 assert.equal(saved[0][apiKeys[tier]][1].offset_x,0);assert.equal(saved[0][apiKeys[tier]][1].offset_y,1);
 const adjusted=c.SPBSpecOverlayPicker.transient('spov2_example',{zone:0,tier,index:1},{opacity:18});
 assert.equal(adjusted[0][apiKeys[tier]][1].opacity,.18);assert.equal(adjusted[0][apiKeys[tier]][1].rotation,72);assert.equal(JSON.stringify(c.zones),before);
}
const stack=[{pattern:'old'},{pattern:'spov2_example'},{pattern:'old2'},{pattern:'spov2_other'}];
// A real edit rebuilds the panel: placement must never return to a closed disclosure.
for(let tier=0;tier<5;tier++){
 c.SPBSpecOverlayPicker.edit(0,tier,1,'scale',.4);
 const html=c.SPBSpecOverlayPicker.stack(c.zones[0],0,tier);
 assert(html.includes('class="spec-v2-placement"'));
 assert(!html.includes('<details>'));assert(html.includes('value="0.4"'));
 const payload=c._mapSpecPatternEntry(c.zones[0][keys[tier]][1]);assert.equal(payload.scale,.4);
}
assert.equal(c.SPBSpecOverlayPicker.neighbor(stack,1,1),3);assert.equal(c.SPBSpecOverlayPicker.neighbor(stack,0,1),2);
c.document={getElementById:id=>id==='paintFile'?{value:'not-exported-yet.tga'}:null};
c.buildLivePaintCompositeCanvas=()=>({width:2048,height:2048});
c.canvasToBase64Async=async()=> 'data:image/png;base64,loaded-psd-composite';
(async()=>{
 const before=JSON.stringify(c.zones),body=await c.SPBSpecOverlayPicker.previewPayload('spov2_example',{zone:0,tier:0,index:1});
 assert.equal(body.paint_image_base64,'data:image/png;base64,loaded-psd-composite');
 assert.equal(body.source_mode,'live_flat_canvas');assert.equal(JSON.stringify(c.zones),before);
 console.log('UI contract: serialization, persistence, five stacks, zero-layer indices, effective ordering and loaded PSD preview source pass.');
})().catch(e=>{console.error(e);process.exitCode=1;});
