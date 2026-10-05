/* SPB-105 v2 tick 4. SPEC OVERLAYS use the actual Bases popup and Finish Atlas. */
(function(g){
 'use strict';
 const P=g.SPBSpecOverlayPicker={context:null,legacy:false};
 const keys=['specPatternStack','overlaySpecPatternStack','thirdOverlaySpecPatternStack','fourthOverlaySpecPatternStack','fifthOverlaySpecPatternStack'];
 const labels=['Primary base','Second base','Third base','Fourth base','Fifth base'];
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 P.items=()=>typeof SPEC_PATTERNS!=='undefined'?SPEC_PATTERNS:[];
 P.find=id=>P.items().find(p=>p.id===id);
 P.modern=s=>s.render_version>=2||s.pattern?.startsWith('spov2_');
 P.draft=(id,c=P.context,overrides={})=>{const old=c&&zones[c.zone]?.[keys[c.tier]]?.[c.index],layer=JSON.parse(JSON.stringify(old?.pattern===id?old:_buildSpecPatternLayer(id)));if(Number.isFinite(overrides.opacity))layer.opacity=Math.max(0,Math.min(100,overrides.opacity));return layer;};
 P.neighbor=(stack,index,dir)=>{const lane=stack.map((s,i)=>i).filter(i=>P.modern(stack[i])===P.modern(stack[index]));return lane[lane.indexOf(index)+dir]??-1;};
 P.current=()=>{const c=P.context;return c&&zones[c.zone]?.[keys[c.tier]]?.[c.index]?.pattern||'';};
 P.open=function(trigger,zone,tier=0,index=-1){
   P.context={trigger,zone,tier,index};
   P.legacy=!!P.find(P.current())?.legacy;
   g.closeSwatchPicker();g.openSwatchPicker(trigger,'specOverlay',zone,index);
 };
 P.collection=function(legacy){const c=P.context;if(!c)return;P.legacy=legacy;g.closeSwatchPicker();g.openSwatchPicker(c.trigger,'specOverlay',c.zone,c.index);};
 P.mountToolbar=function(popup,type){
   popup.dataset.specOverlay=String(type==='specOverlay');
   popup.querySelector('.spec-v2-collection-bar')?.remove();
   if(type!=='specOverlay')return;
   const bar=document.createElement('div');bar.className='spec-v2-collection-bar';bar.setAttribute('role','group');bar.setAttribute('aria-label','Overlay collection');
   bar.innerHTML=`<button class="btn" aria-pressed="${!P.legacy}" onclick="SPBSpecOverlayPicker.collection(false)">Surface library · ${g.SPB_SPEC_OVERLAY_V2.items.length}</button><button class="btn" aria-pressed="${P.legacy}" onclick="SPBSpecOverlayPicker.collection(true)">Legacy collection</button><span>Material detail · preserves your paint</span>`;
   popup.querySelector('.swatch-popup-search')?.append(bar);
 };
 P.card=function(p,current){
   const quality=g.SPB_SPEC_OVERLAY_QUALITY?.[p.id],rank=quality?.shipReady?Number(quality.score):0;
   return `<div class="swatch-item swatch-catalog-card${p.id===current?' selected':''}" data-finish-id="${esc(p.id)}" data-finish-type="spec_pattern" data-rank-overall="${rank}" data-overlay-approved="${rank?'1':'0'}" data-sort-name="${esc(p.name.toLowerCase())}" data-name="${esc(p.name.toLowerCase())}" data-search="${esc([p.name,p.id,p.desc,p.family,'spec overlay material'].join(' ').toLowerCase())}" data-desc="${esc(p.desc)}" onclick="selectSwatchItem('${p.id}')">
    <button type="button" class="swatch-fav-btn${g.isFavorite?.(p.id)?' active':''}" onclick="toggleSwatchPickerFavorite('${p.id}',event)" aria-label="Favorite ${esc(p.name)}">${g.isFavorite?.(p.id)?'★':'☆'}</button>
    <div class="swatch-square spec-v2-split"><img class="deferred-swatch" loading="lazy" decoding="async" data-swatch-url="/api/spec-pattern-visual-preview/${p.id}" alt="Illustrative material study"><img class="deferred-swatch" loading="lazy" decoding="async" data-swatch-url="/api/spec-pattern-combined/${p.id}" alt="Applied M R Cc map"></div>
    <div class="swatch-label">${esc(p.name)}</div><div class="spec-v2-caption">Material study · M/R/Cc detail</div>
    <button type="button" class="btn btn-sm spec-v2-inspect" onclick="event.stopPropagation();SPBSpecOverlayPicker.inspect('${p.id}')">Inspect surface</button></div>`;
 };
 P.buildGrid=function(current){
   const catalog=g.SPB_SPEC_OVERLAY_V2,items=P.items().filter(p=>!!p.legacy===P.legacy);
   let html='';
   const families=P.legacy?Object.entries(SPEC_PATTERN_GROUPS).filter(([n,ids])=>ids.some(id=>items.some(p=>p.id===id))).map(([name,ids])=>({name,ids})):catalog.families.map(f=>({name:f.name,desc:f.desc,ids:items.filter(p=>p.family===f.id).map(p=>p.id)}));
   const favorites=items.filter(p=>g.isFavorite?.(p.id));
   if(favorites.length)html+=`<div class="swatch-group"><div class="swatch-group-label swatch-favorites-label">Favorites</div><div class="swatch-grid-row">${favorites.map(p=>P.card(p,current)).join('')}</div></div>`;
   families.forEach(f=>{const rows=f.ids.map(id=>items.find(p=>p.id===id)).filter(Boolean);if(!rows.length)return;
     html+=`<div class="swatch-group collapsed" data-picker-category="${esc(f.name)}" data-picker-types="spec_overlay"><div class="swatch-group-label">${esc(f.name)} <span class="swatch-group-count">${rows.length}</span></div><div class="swatch-group-desc">${esc(f.desc||'Fine spec-only surfaces. Select a construction, inspect its material channels, then layer it onto your paint.')}</div><div class="swatch-grid-row">${rows.map(p=>P.card(p,current)).join('')}</div></div>`;
   });return html;
 };
 P.apply=function(id,overrides={}){
   const c=P.context;if(!c||!P.find(id)||!zones[c.zone])return;
   const z=zones[c.zone],key=keys[c.tier],stack=z[key]||(z[key]=[]);
   if(c.index<0&&stack.length>=5){showToast('Maximum 5 spec overlays per base',true);return;}
   pushZoneUndo(c.index<0?'Add spec overlay':'Replace spec overlay');
   const layer=P.draft(id,c,overrides);
   const selected=P.find(id),family=g.SPB_SPEC_OVERLAY_V2.families.find(f=>f.id===selected.family);
   const category=family?.name||Object.entries(SPEC_PATTERN_GROUPS).find(([name,ids])=>ids.includes(id))?.[0];
   if(category)g._spbSetLastPickerCategory?.('specOverlay',category);
   if(c.index>=0)stack[c.index]=layer;else stack.push(layer);
   renderZones();triggerPreviewRender();
 };
 P.edit=function(zone,tier,index,prop,value){
   const stack=zones[zone]?.[keys[tier]],layer=stack?.[index];if(!layer)return;
   if(prop==='duplicate'&&stack.length>=5){showToast('Maximum 5 spec overlays per base',true);return;}
   pushZoneUndo('Edit spec overlay');
   if(prop==='remove')stack.splice(index,1);
   else if(prop==='duplicate')stack.splice(index+1,0,JSON.parse(JSON.stringify(layer)));
   else if(prop==='move'){const next=P.neighbor(stack,index,Number(value));if(next>=0)[stack[index],stack[next]]=[stack[next],stack[index]];}
   else if(prop==='channels'){layer.channels=value;layer.channelsCustomized=true;}
   else layer[prop]=value;
   renderZones();triggerPreviewRender();
 };
 P.channel=function(zone,tier,index,ch,checked){const layer=zones[zone][keys[tier]][index];const set=new Set((layer.channels??'MRC').split(''));checked?set.add(ch):set.delete(ch);P.edit(zone,tier,index,'channels','MRC'.split('').filter(c=>set.has(c)).join(''));};
 P.stack=function(zone,index,tier=0){
   const stack=zone[keys[tier]]||[];const mixed=stack.some(P.modern)&&stack.some(s=>!P.modern(s));
   let html=`<section class="spec-v2-stack spec-patterns-section ${tier===0?'section-collapsible':''}" ${tier===0?`id="sectionSpecPatterns${index}"`:''} aria-label="${labels[tier]} spec overlays"><button type="button" class="spec-v2-stack-heading section-header" aria-expanded="true" onclick="this.parentElement.classList.toggle('collapsed');this.setAttribute('aria-expanded',String(!this.parentElement.classList.contains('collapsed')))"><strong>SPEC OVERLAYS</strong><span>${labels[tier]} · ${stack.length}/5 ▾</span></button><div class="spec-v2-stack-content"><p>${mixed?'Saved legacy layers apply first, then the surface layers below.':'Material detail on your existing paint. Layers apply from top to bottom.'}</p>`;
   stack.map((s,i)=>({s,i})).sort((a,b)=>Number(P.modern(a.s))-Number(P.modern(b.s))).forEach(({s,i},position)=>{const p=P.find(s.pattern),v2=P.modern(s);const action=(prop,val)=>`SPBSpecOverlayPicker.edit(${index},${tier},${i},'${prop}',${val})`;
     html+=`<article class="spec-v2-layer${s.muted?' is-muted':''}"><div class="spec-v2-layer-head"><span>${position+1}</span><img src="/api/spec-pattern-combined/${s.pattern}" alt="Material detail"><button class="btn" onclick="SPBSpecOverlayPicker.open(this,${index},${tier},${i})">${esc(p?.name||s.pattern)} ▾</button><button class="btn" onclick="${action('remove','true')}" aria-label="Remove ${esc(p?.name||s.pattern)}">×</button></div>
      <div class="spec-v2-layer-actions"><button class="btn btn-sm" ${P.neighbor(stack,i,-1)<0?'disabled':''} onclick="${action('move',-1)}" aria-label="Move up">↑</button><button class="btn btn-sm" ${P.neighbor(stack,i,1)<0?'disabled':''} onclick="${action('move',1)}" aria-label="Move down">↓</button><button class="btn btn-sm" ${stack.length>=5?'disabled':''} onclick="${action('duplicate','true')}">Duplicate</button><button class="btn btn-sm" aria-pressed="${!!s.muted}" onclick="${action('muted',!s.muted)}">${s.muted?'Unmute':'Mute'}</button><button class="btn btn-sm" aria-pressed="${!!s.solo}" onclick="${action('solo',!s.solo)}">Solo</button><button class="btn btn-sm" onclick="SPBSpecOverlayPicker.inspect('${s.pattern}',${index},${tier},${i})">Inspect</button></div>
      <label class="spec-v2-control">Strength <input type="range" min="0" max="100" value="${s.opacity??50}" oninput="this.nextElementSibling.value=this.value+'%'" onchange="${action('opacity','Number(this.value)')}"><output>${s.opacity??50}%</output></label>
      <div class="spec-v2-channels">${[['M','Metallic'],['R','Roughness'],['C','Clearcoat']].map(([c,label])=>`<label><input type="checkbox" ${(s.channels??'MRC').includes(c)?'checked':''} onchange="SPBSpecOverlayPicker.channel(${index},${tier},${i},'${c}',this.checked)">${label}</label>`).join('')}</div>
      <div class="spec-v2-placement" role="group" aria-label="Size, placement and variations"><h4>Size, placement & variations${v2?'':' · legacy recipe'}</h4><label class="spec-v2-control">Size <input type="range" min="0.25" max="1" step="0.05" value="${s.scale??1}" oninput="this.nextElementSibling.value=Math.round(Number(this.value)*100)+'%'" onchange="${action('scale','Number(this.value)')}"><output>${Math.round((s.scale??1)*100)}%</output></label><p>Smaller size = finer detail, repeated across the surface.</p><label class="spec-v2-control">Rotation <input type="number" min="0" max="359" value="${s.rotation??0}" onchange="${action('rotation','Number(this.value)')}">°</label>
      ${['offsetX','offsetY'].map((key,k)=>`<label class="spec-v2-control">${k?'Y':'X'} position <input type="range" min="0" max="1" step="0.01" value="${s[key]??.5}" oninput="this.nextElementSibling.value=Math.round(Number(this.value)*100)+'%'" onchange="${action(key,'Number(this.value)')}"><output>${Math.round((s[key]??.5)*100)}%</output></label>`).join('')}
      ${!s.pattern.startsWith('spov2_')?`<label class="spec-v2-control">Legacy range <input type="number" min="0" max="100" value="${s.range??40}" onchange="${action('range','Number(this.value)')}"></label><label class="spec-v2-control">Blend <select onchange="${action('blendMode','this.value')}">${['normal','multiply','screen','overlay','hardlight','softlight'].map(mode=>`<option value="${mode}" ${mode===(s.blendMode||'normal')?'selected':''}>${mode.replace('_',' ')}</option>`).join('')}</select></label>`:''}
      <label class="spec-v2-control">Coverage box <input type="range" min="1" max="100" value="${s.boxSize??100}" oninput="this.nextElementSibling.value=this.value+'%'" onchange="${action('boxSize','Number(this.value)')}"><output>${s.boxSize??100}%</output></label>
      ${v2?`<label class="spec-v2-control">Variation <input type="number" min="0" max="2147483647" value="${s.seed??42}" onchange="${action('seed','Math.max(0,Math.min(2147483647,Math.floor(Number(this.value))))')}"></label>`:'<p>Saved legacy material behavior retained.</p>'}</div></article>`;
   });
   html+=`<button class="spb-zone-cta-bar spb-add-spec-pattern-cta" ${stack.length>=5?'disabled':''} onclick="SPBSpecOverlayPicker.open(this,${index},${tier},-1)">＋ ADD SPEC OVERLAY</button></div></section>`;return html;
 };
 P.inspect=function(id,zone,tier,index){
   document.getElementById('specOverlayInspector')?.remove();const p=P.find(id),context=zone==null?P.context:{zone,tier,index},layer=P.draft(id,context);
   const dialog=document.createElement('dialog');dialog.id='specOverlayInspector';dialog.className='spec-v2-inspector';
   dialog.innerHTML=`<form method="dialog"><button class="btn" aria-label="Close inspector">Close ×</button></form><h2>${esc(p?.name||id)}</h2><p>${esc(p?.desc||'Spec-only material surface.')}</p><div class="spec-v2-inspector-controls"><label>Reference material <select id="specOverlayReference"><option value="neutral">Neutral</option><option value="chrome">Chrome</option><option value="matte">Matte</option><option value="no_coat">No clearcoat</option></select></label><label>Strength <input id="specOverlayStrength" type="range" min="0" max="100" value="${layer?.opacity??p?.defaultOpacity??50}"><output>${layer?.opacity??p?.defaultOpacity??50}%</output></label></div><div class="spec-v2-inspector-images"><figure><img data-kind="whole" alt="Whole 2048 px applied spec"><figcaption>Whole surface · 2048 px</figcaption></figure><figure><img data-kind="combined" alt="512 px material detail"><figcaption>512 px detail · M/R/Cc</figcaption></figure><figure><img data-kind="visual" alt="Illustrative white-light study"><figcaption>Illustrative lighting · not an iRacing render</figcaption></figure></div><img class="spec-v2-channel-strip" data-kind="channels" alt="Separate metallic roughness and clearcoat channels"><p>Spec RGB encodes metallic, roughness and clearcoat. Source paint stays intact; its appearance responds to the new material.</p>`;
   document.body.appendChild(dialog);dialog.addEventListener('close',()=>dialog.remove());
   const actions=document.createElement('footer');actions.className='spec-v2-inspector-actions';dialog.appendChild(actions);
   const strengthDraft=()=>({opacity:Number(dialog.querySelector('#specOverlayStrength').value)});
   if(zone==null&&P.context){const use=document.createElement('button');use.type='button';use.className='btn';use.textContent=P.context.index<0?'Add this overlay':'Use this overlay';use.onclick=()=>{P.apply(id,strengthDraft());dialog.close();g.closeSwatchPicker();};actions.appendChild(use);}
   const onPaint=document.createElement('button');onPaint.type='button';onPaint.className='btn';onPaint.textContent='Preview in my paint';onPaint.onclick=()=>P.onPaint(id,dialog,context,strengthDraft());actions.appendChild(onPaint);
   const update=()=>{const strength=dialog.querySelector('#specOverlayStrength').value;dialog.querySelector('output').value=strength+'%';const query=new URLSearchParams({reference:dialog.querySelector('select').value,strength:Number(strength)/100,seed:layer?.seed??42,size:384,settings:JSON.stringify(layer?_mapSpecPatternEntry(layer):{})});dialog.querySelectorAll('[data-kind]').forEach(img=>img.src='/api/spec-overlay-inspect/'+encodeURIComponent(id)+'/'+img.dataset.kind+'?'+query);};
   dialog.querySelector('select').addEventListener('change',update);dialog.querySelector('input').addEventListener('change',update);update();dialog.showModal();
 };
 P.transient=function(id,c=P.context,overrides={}){
   if(!c||!zones[c.zone])throw new Error('Select a paint zone first.');
   const payload=[],apiKeys=['spec_pattern_stack','overlay_spec_pattern_stack','third_overlay_spec_pattern_stack','fourth_overlay_spec_pattern_stack','fifth_overlay_spec_pattern_stack'];
   let target;
   zones.forEach((z,i)=>{const rows=buildServerZonesForRender([z]);if(i===c.zone)target=rows[0];payload.push(...rows);});
   if(!target)throw new Error('Choose an enabled paint zone with a base finish.');
   const key=apiKeys[c.tier],stack=(zones[c.zone][keys[c.tier]]||[]).map(_mapSpecPatternEntry);
   const layer=_mapSpecPatternEntry(P.draft(id,c,overrides));
   if(c.index>=0)stack[c.index]=layer;else if(stack.length<5)stack.push(layer);else throw new Error('This base already has five overlays.');
   target[key]=stack;Object.defineProperty(payload,'overlayTarget',{value:target});return payload;
 };
 P.previewPayload=async function(id,c=P.context,overrides={}){
   const paint=document.getElementById('paintFile')?.value?.trim();
   const canvas=typeof g.buildLivePaintCompositeCanvas==='function'?g.buildLivePaintCompositeCanvas():document.getElementById('paintCanvas');
   if(!paint&&!canvas?.width)throw new Error('Load a source paint first.');
   const payload={paint_file:paint||'',zones:P.transient(id,c,overrides),seed:42,preview_scale:.5};
   // SPB-105 tick20: PSD source headers can name an unexported TGA. Preview
   // the loaded composite, as the normal full-render workflow already does.
   if(canvas?.width&&canvas?.height){payload.paint_image_base64=await canvasToBase64Async(canvas);payload.source_mode='live_flat_canvas';}
   return payload;
 };
 P.onPaint=async function(id,dialog,c=P.context,overrides={}){
   dialog.querySelector('.spec-v2-on-paint')?.remove();const output=document.createElement('div');output.className='spec-v2-on-paint';dialog.insertBefore(output,dialog.querySelector('.spec-v2-inspector-actions'));
   try{
     output.textContent='Rendering this overlay with your current paint, zones and material layers…';
     const body=await P.previewPayload(id,c,overrides),baseline={...body,zones:zones.flatMap(z=>buildServerZonesForRender([z]))};
     const request=async payload=>{const response=await fetch((g.ShokkerAPI?.baseUrl||'')+'/preview-render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(60000)});const data=await response.json();if(!response.ok||!data.success||!data.spec_preview)throw new Error(data.error||'Material preview failed.');return data;};
     const [before,data]=await Promise.all([request(baseline),request(body)]);
     output.replaceChildren();const note=document.createElement('p');note.textContent='Temporary preview with your current zones. Paint colors stay intact; the spec map shows the new surface placement. Your recipe has not changed.';output.appendChild(note);
     for(const [src,label] of [[data.paint_preview,'Current paint'],[before.spec_preview,'Spec before'],[data.spec_preview,'Spec with this overlay']]){if(!src)continue;const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=src;img.alt=label;caption.textContent=label;figure.append(img,caption);output.appendChild(figure);}
   }catch(error){output.textContent=error.message;}
 };
})(typeof window!=='undefined'?window:globalThis);
