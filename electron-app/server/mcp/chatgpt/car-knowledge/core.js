(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SpbCarKnowledge=factory();})(typeof window==='undefined'?this:window,function(){
'use strict';
// Pure shared lookup: source data in, bounded reference out. No IO or edits.
const TOOL = {
  name: 'spb_car_knowledge',
  description: 'Read the shared iRacing car/template reference: exact variants, official template links, inspected file metadata, documented quirks and explicit unknowns. This does not recognize UV islands or authorize panel edits. Supply the car name, official paint folder or reference car_id; partial names return candidates.',
  inputSchema: {type:'object', properties:{
    query:{type:'string', maxLength:1000, description:'Car name or question about its template'},
    car_id:{type:'string', maxLength:150, description:'Exact reference ID returned by a previous lookup'},
    paint_folder:{type:'string', maxLength:250, description:'Exact iRacing paint folder, not an inferred model'}
  }, additionalProperties:false},
  annotations:{readOnlyHint:true, destructiveHint:false, openWorldHint:false}
};
function norm(s){return String(s||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();}
function referenceText(text){return String(text||'').replace(/([a-z])[-\u2010-\u2015](?=[a-z])/gi,'$1 ').trim();}
function firstPaintRequest(text){return /^(?:please\s+)?(?:(?:how do i (?:start|begin) painting|what should i edit first)\b|(?:(?:can|could) you\s+)?help me (?:get started|start painting|begin painting)\b)/i.test(referenceText(text));}
function referenceIntent(text,knownNamedCar){
  const q=referenceText(text).replace(/[\u2018\u2019]/g,"'");
  const naturalOverview=/^(?:please\s+)?(?:tell me about|what (?:do you know|can you tell me) about)\s+.+[?.!]*$/i.test(q);
  const overview=naturalOverview||/\b(?:unusual|quirks?|gotchas?|exceptions?|pitfalls?|watch out|special considerations)\b|\bwhat (?:should i|do i need to) know\b/i.test(q);
  const auxiliaryHistory=knownNamedCar&&/^(?:was|were|has|have|had|did)\b/i.test(q)&&/\b(?:changed?|updated?)\b/i.test(q)&&!/\b(?:you|i)\b/i.test(q);
  const start=/^(?:what|which|why|how|where|explain|compare|help|tell me|is|are|does|do|can (?:i|this|that)|could (?:i|this|that)|anything|any)\b/i.test(q);
  const command='(?:apply|assign|make|set|change|remove|clear|turn|hide|show|recolou?r|repaint|paint|delete|undo|redo|run|scan|fix|enable|disable|render|export|add|place|insert|replace|resize|move|duplicate|open)';
  const mixed=new RegExp('(?:[.!?;]\\s*|\\b(?:and|then)\\s+|\\bplease\\s+)'+command+'\\b','i').test(q)||new RegExp('^(?:can|could|would|will)\\s+you\\s+'+command+'\\b','i').test(q);
  const template=/\b(?:templates?|psds?|uv|revisions?|dimensions?|alpha)\b|\b(?:which|what)\s+(?:car|vehicle|model)\b/i.test(q);
  const layers=/\b(?:layers?|groups?)\b/i.test(q)&&/\b(?:spec|base paint|metallic|roughness|clearcoat|export|wire|groups?)\b/i.test(q);
  const carOverview=overview&&(/\b(?:car|vehicle|model)\b/i.test(q)||knownNamedCar);
  const controls=knownNamedCar&&/^(?:can|could|how do) i\b/i.test(q)&&/\b(?:customi[sz]e|custom (?:paint|livery)|sponsors?|wheel rims?)\b/i.test(q);
  const artworkHistory=knownNamedCar&&/\b(?:body vinyl|artwork|vehicle art|paint patterns?|window banners?|contingency (?:decals?|logos?)|imsa decals?|paint\s*shop|preview|flicker(?:ing)?)\b/i.test(q)&&/\b(?:changed|changes?|updated?|revisions?|history)\b/i.test(q);
  const design=/\b(?:look|suit|palette|recommend|suggest)\b/i.test(q)&&!layers&&!/\b(?:revision|dimensions?|alpha|uv)\b/i.test(q)&&!overview;
  const firstPaint=firstPaintRequest(q)&&(knownNamedCar||/\b(?:this|my|current|open)\s+(?:(?:current|open)\s+)?(?:car|template|vehicle|model)\b/i.test(q));
  const question=q.length<=1000&&(start||naturalOverview||auxiliaryHistory||firstPaint)&&!mixed&&!(naturalOverview&&new RegExp('\\b'+command+'\\b','i').test(q))&&!design&&(template||layers||carOverview||controls||artworkHistory||firstPaint||(knownNamedCar&&/\bwhich (?:variant|decal) layers?\b/i.test(q)));
  return {question:!!question,current_context:!!question&&/\b(?:this|my|current|open)\b/i.test(q)&&(/\b(?:template|uv|islands?|revision|car|vehicle|model)\b/i.test(q)),overview:!!question&&overview,mixed_or_edit:!!mixed,read_only:true};
}
function tokens(s){return norm(s).split(' ').filter(x=>x && !new Set(['the','my','a','an','for','of','what','where','how','can','do','i','is','on','template','paint','car','iracing','racing','look','style','scheme']).has(x));}
function labels(c){const list=[c.name,...(c.aliases||[]),c.paint_folder].filter(Boolean).map(norm);return c.id.endsWith('-superspeedway')?list.concat(list.map(s=>s.replace(/\bss$/,'superspeedway'))):list;}
function familyExpansion(data,matches,label){
  // An old short alias can now name several bodies (e.g. Formula Vee).
  if(matches.some(c=>norm(c.name)===label))return matches;
  const family=data.cars.filter(c=>labels(c).some(name=>name===label||name.startsWith(label+' ')));
  return family.length>matches.length?family:matches;
}
function brief(c){return {id:c.id,name:c.name,paint_folder:c.paint_folder,status:c.status};}
function valid(args){
  for(const [key,max] of [['query',1000],['car_id',150],['paint_folder',250]]){
    if(args[key]!==undefined && (typeof args[key]!=='string'||args[key].length>max))throw new Error(key+' must be text of at most '+max+' characters');
    if(key!=='query' && args[key]!==undefined && !args[key].trim())throw new Error(key+' must not be blank');
  }
}
function comparisonSelection(data,args){
  if(args.car_id||args.paint_folder)return null;
  const q=norm(args.query);
  if(!/\b(?:vs|versus|compare|compared|comparison|between|both|same|shared?|different|differences?|identical|copy|borrow|transfer|reuse)\b/.test(q))return null;
  let parts=q.split(/\b(?:vs|versus|compared to|compared with)\b/);
  if(parts.length<2)parts=q.split(/\b(?:and|with)\b/);
  if(parts.length<2&&/\b(?:copy|borrow|transfer|reuse)\b/.test(q))parts=q.split(/\b(?:to|onto|on)\b/);
  if(parts.length<2||parts.length>5||parts.some(p=>!p.trim()))return null;
  const mentions=parts.map(p=>{
    const query=p.trim(),choice=selectSingle(data,{query});
    const unsupported=choice.matches.some(car=>['dirt','superspeedway','non winged','wingless','evo'].some(mod=>(' '+query+' ').includes(' '+mod+' ')&&!labels(car).some(label=>(' '+label+' ').includes(' '+mod+' '))));
    const evidence=choice.matches.length||choice.retired_matches?.length||choice.excluded_ids?.length||choice.reason==='unknown-model-code'||/\b(?:unknown|mystery|car|model|variant|evo)\b/.test(query);
    return {query,choice,evidence:!!evidence,resolved:!unsupported&&choice.definite&&choice.matches.length===1,unsupported};
  });
  // Colour/material comparisons on one named car keep their existing route.
  if(mentions.filter(m=>m.evidence).length<2)return null;
  const matches=[...new Map(mentions.flatMap(m=>m.unsupported?[]:m.choice.matches).map(c=>[c.id,c])).values()].slice(0,5);
  const retired=[...new Map(mentions.flatMap(m=>m.choice.retired_matches||[]).map(r=>[r.name,r])).values()];
  const complete=mentions.every(m=>m.resolved);
  return {matches,definite:false,reason:complete?'explicit-car-comparison':'comparison-needs-exact-identities',
    ...(retired.length?{retired_matches:retired}:{}),
    comparison:{schema:'spb-car-comparison/1',complete,mentions:mentions.map(m=>({query:m.query.slice(0,250),
      resolved:m.resolved,reason:m.unsupported?'unsupported-variant-modifier':m.choice.reason,
      car_ids:m.unsupported?[]:m.choice.matches.map(c=>c.id).slice(0,5)}))}};
}
function select(data,args){return comparisonSelection(data,args)||selectSingle(data,args);}
function selectSingle(data,args){
  if(args.car_id && args.paint_folder){const c=data.cars.find(c=>c.id===args.car_id);if(!c||norm(c.paint_folder)!==norm(args.paint_folder))return {matches:[],reason:'conflicting-explicit-identifiers',definite:false};}
  if(args.car_id){const found=data.cars.filter(c=>c.id===args.car_id);return {matches:found,reason:found.length?'exact-car-id':'unknown-car-id',definite:true};}
  if(args.paint_folder){const folder=norm(args.paint_folder);const found=data.cars.filter(c=>norm(c.paint_folder)===folder);return {matches:found,reason:found.length?'exact-paint-folder':'unknown-paint-folder',definite:true};}
  const rawQuery=norm(args.query), q=rawQuery.replace(/^(?:please )?(?:tell me about|what (?:do you know|can you tell me) about) (?:the )?/,''), qt=tokens(q);
  if(!q)return {matches:[],reason:'car-identity-required'};
  const retired=[...new Map([...(data.retired_context||[]),...data.cars.flatMap(c=>c.predecessor_context||[])].map(r=>[r.name,r])).values()];
  const retiredMatches=retired.filter(r=>{
    const base=norm(r.name.replace(/\([^)]*\)/g,''));
    return base&&(' '+q+' ').includes(' '+base+' ')&&!/\b(?:gen 4|gen4|2003|superspeedway)\b/.test(q);
  });
  if(retiredMatches.length)return {matches:[],retired_matches:retiredMatches,reason:'retired-model-mentioned',definite:false};
  const exact=data.cars.filter(c=>labels(c).includes(q));
  if(exact.length){const family=familyExpansion(data,exact,q);return {matches:family,reason:family.length>exact.length?'family-alias-needs-variant':'exact-car-name',definite:true};}
  const phrase=[];
  for(const car of data.cars){
    const compatible=!['dirt','superspeedway','non winged','wingless','evo'].some(mod=>(' '+q+' ').includes(' '+mod+' ')&&!labels(car).some(label=>(' '+label+' ').includes(' '+mod+' ')));
    const lengths=labels(car).filter(label=>compatible && (label.length>=5 || label.length>=3&&label===norm(car.name)&&(' '+q+' ').includes(' '+label+' template ')) && (' '+q+' ').includes(' '+label+' ')).map(label=>label.length);
    if(lengths.length)phrase.push({car,label:labels(car).filter(label=>label.length===Math.max(...lengths) && (' '+q+' ').includes(' '+label+' '))[0]});
  }
  if(phrase.length){
    // A longer exact variant mention wins over its contained family name.
    let specific=phrase.filter(p=>!phrase.some(other=>other!==p && other.label.length>p.label.length && (' '+other.label+' ').includes(' '+p.label+' ')));
    const positive=specific.filter(p=>!/\b(?:not|isnt|isn t|is not|dont|don t)\s+(?:(?:asking|talking)\s+about\s+|for\s+|about\s+)?(?:(?:the|a|my|this)\s+)?$/.test(q.slice(0,q.indexOf(p.label))));
    if(!positive.length)return {matches:[],excluded_ids:specific.map(p=>p.car.id),reason:'negated-car-name-needs-context',definite:false};
    specific=positive;
    if(specific.length===1){const family=familyExpansion(data,[specific[0].car],specific[0].label);if(family.length>1)return {matches:family,reason:'family-alias-needs-variant',definite:false};}
    if(specific.length===1 && /\b(?:same|different|difference|versus|vs|identical)\b/.test(q)){
      const primary=specific[0].car,primaryWords=new Set(labels(primary).flatMap(tokens));
      const others=data.cars.filter(c=>c.id!==primary.id && labels(c).some(label=>{
        const shared=tokens(label).filter(t=>qt.includes(t));
        return shared.length>=3 && shared.some(t=>!primaryWords.has(t));
      }));
      if(others.length)return {matches:[primary,...others].slice(0,5),reason:'comparison-of-models',definite:false};
    }
    return {matches:specific.map(p=>p.car),reason:'explicit-name-in-question',definite:true};
  }
  const scored=data.cars.map(car=>{let count=0;return {car,get count(){return count;},score:Math.max(...labels(car).map(label=>{
    const lt=tokens(label),shared=qt.filter(t=>lt.includes(t));
    if(shared.length<2 && !(q===shared[0] || shared.some(t=>/^(?=.*[a-z])(?=.*\d)[a-z0-9]{3,}$/.test(t))))return 0;
    count=Math.max(count,shared.length);
    return shared.length/Math.max(1,lt.length);
  }))};}).filter(x=>x.score>0).sort((a,b)=>b.count-a.count || b.score-a.score || a.car.id.localeCompare(b.car.id));
  const uniqueToken=scored.length===1 && qt.some(t=>/^(?=.*[a-z])(?=.*\d)[a-z0-9]{3,}$/.test(t) && tokens(scored[0].car.name).includes(t));
  const qualified=scored.length && scored[0].count>=2 && (scored.length===1||scored[0].count>scored[1].count);
  const unknownCode=!scored.length && qt.some(t=>/^[a-z]{1,5}\d+[a-z0-9]*$/.test(t));
  const definite=(uniqueToken||qualified)&&!/\bnot\b/.test(q);
  const cohort=scored.filter(x=>x.count===scored[0].count);
  return {matches:cohort.slice(0,definite?1:5).map(x=>x.car),reason:uniqueToken?'unique-model-code':qualified?'unique-qualified-model':scored.length?'partial-name-needs-choice':unknownCode?'unknown-model-code':'no-car-match',definite:!!definite};
}
function templateDownloadGuide(car){
  const t=car&&car.template||{},url=typeof t.url==='string'?t.url:'';
  const allowed=/^https:\/\/ir-core-sites\.iracing\.com\/members\/member_images\/cars\/car_templates\/[a-z0-9_.-]+\.zip$/i.test(url);
  const available=allowed&&t.http_verified===true&&t.http_metadata?.status===200;
  const rows=(car&&car.template_metadata||[]).slice(0,5).map(m=>({file:m.file,sha256:m.sha256,applicability:m.applicability,width:m.width,height:m.height}));
  return {available,car_id:car&&car.id,url:available?url:null,
    checked_at:available?t.http_metadata.checked_at||null:null,
    verification:'Recorded official archive HTTP check and separately inspected PSD metadata; no fresh network check.',
    latest_revision_verified:false,loaded_file_verified:false,can_target_panels:false,
    inspected_documents:rows,more_documents_omitted:(car&&car.template_metadata||[]).length>rows.length,
    guidance:!available&&car.status==='retired'&&t.status==='painting-unavailable-retired-official-release-note'?'This exact Rookie Legends car was retired from painting and other simulator activities in '+t.restriction_release+'. No supported template download is recorded for it. Preserve the old file; verify the regular Legends car and its own template for current racing. The replacement does not establish paint-file conversion or matching UVs.':available?'Open the official ZIP link when online, extract it, and choose the exact PSD document for this car/variant. Open that source in SPB to inspect its layers. Keep an existing painted project before replacing its source; old paint/masks are not proved compatible. HTTP dates and a catalogue entry do not certify the latest installed-build template or UV locations.':'No verified official template ZIP link is recorded for this exact car. Check its documented availability/custom-paint restrictions; do not substitute another model.'};
}
function variantReference(car,query){
  const requested=referenceIntent(query,true).question&&/\bwhich (?:variant|decal) layers?\b/i.test(query||'');
  const pathById={"dirtmodified-358":["Paintable Area/Car_decal 358"],"dirtmodified-bigblock":["Paintable Area/Car_decal Big Block"],"dirtmicrosprint-winged":["Turn Off Before Exporting TGA/Number Blocks Winged","Turn Off Before Exporting TGA/Sponsor Blocks Winged"],"dirtmicrosprint-nonwinged":["Turn Off Before Exporting TGA/Number Blocks No Wing","Turn Off Before Exporting TGA/Sponsor Blocks No Wing"],"dirtmicrosprint-winged-outlaw":["Turn Off Before Exporting TGA/Number Blocks Winged","Turn Off Before Exporting TGA/Sponsor Blocks Winged"],"dirtmicrosprint-nonwinged-outlaw":["Turn Off Before Exporting TGA/Number Blocks No Wing","Turn Off Before Exporting TGA/Sponsor Blocks No Wing"],"dirtsprint-winged-305":["Paintable Area/Car_decal 305, 360 winged sprint"],"dirtsprint-winged-360":["Paintable Area/Car_decal 305, 360 winged sprint"],"dirtsprint-nonwinged-360":["Paintable Area/Car_decal Non Winged Sprints","Turn Off Before Exporting TGA/Sponsor Locations Wingless","Turn Off Before Exporting TGA/Number Locations Wingless"],"dirtsprint-winged-410":["Paintable Area/Car_decal 410 Sprint winged sprint"],"dirtsprint-nonwinged-410":["Paintable Area/Car_decal Non Winged Sprints","Turn Off Before Exporting TGA/Sponsor Locations Wingless","Turn Off Before Exporting TGA/Number Locations Wingless"]};
  const expected=pathById[car.id]||[],normalize=s=>String(s).replace(/\s*\/\s*/g,'/');
  const labels=new Set((car.template_metadata||[]).flatMap(m=>(m.layer_labels||[]).map(normalize)));
  const facts=(car.facts||[]).filter(f=>f.topic==='variant_reference_layers'&&expected.length&&expected.every(p=>String(f.text||'').includes(p)&&labels.has(p)));
  const guides=expected.some(p=>p.startsWith('Turn Off Before Exporting TGA/'));
  return {requested:!!requested,status:requested&&facts.length?'documented-label-to-inspect':'unverified',layer_path_to_inspect:requested&&facts.length?expected[0]:null,...(requested&&facts.length&&expected.length>1?{layer_paths_to_inspect:expected}:{}),source_fact_ids:requested?facts.map(f=>f.id):[],read_only:true,loaded_file_verified:false,visibility_verified:false,can_target_panels:false,guidance:'Inspect the matching variant label in your actual template and preview. No layer has been selected or toggled; labels do not prove pixels, decal restrictions or UV placement.'+(requested&&facts.length&&guides?' Paths under Turn Off Before Exporting TGA are reference guides; follow that group’s export instruction before exporting.':'')};
}
function firstPaintWorkflow(car,query){
  const requested=referenceIntent(query,true).question&&firstPaintRequest(query);
  if(!requested)return {requested:false};
  const restrictions=(car.facts||[]).filter(f=>f.topic==='custom-paint-restriction'&&f.actionable_paint_restriction!==false);
  if((car.availability||{}).simulator_painting_available===false||restrictions.length)return {requested:true,status:'painting-restricted',guidance:restrictions.length?restrictions.map(f=>f.text).join(' '):templateDownloadGuide(car).guidance,source_fact_ids:restrictions.map(f=>f.id),steps:[],read_only:true,can_target_panels:false};
  const variant=variantReference(car,'Which variant layers should I use for the '+car.name+' template?');
  const paths=variant.layer_paths_to_inspect||(variant.layer_path_to_inspect?[variant.layer_path_to_inspect]:[]);
  const groups=[...new Set((car.template_metadata||[]).flatMap(m=>m.layer_groups||[]).filter(g=>/turn\s*off\s*before\s*export/i.test(g)))];
  return {requested:true,status:'general-spb-starting-workflow',steps:[
    'Use Open Layered for the exact car’s PSD, XCF or ORA and wait until its layer list is ready.',
    'Read the layer list and inspect what each layer contributes. Select the artwork layer you intend to change, or use + Layer for new artwork outside any guide group. Keep numbers, sponsors and other artwork you want to preserve.',
    'Choose Layer editing for layer artwork; Zone editing targets zone coverage and finishes. Check the active target before painting.',
    'Use the guide group’s eye to judge the artwork without outlines. Follow its export instruction, inspect the RENDER result and then check the paint in iRacing.'
  ],help_article_ids:['layers.open_psd','layers.panel','layers.roles','layers.turn_off_before_export'],variant_paths_to_inspect:paths,variant_source_fact_ids:variant.source_fact_ids,export_reference_groups:groups,knowledge_scope:'General documented SPB workflow plus exact-car inspected labels. Labels do not verify loaded pixels, material settings, decal restrictions, template compatibility or UV placement.',read_only:true,loaded_file_verified:false,visibility_verified:false,can_target_panels:false};
}
function historyEvidence(car,query){
  const intent=referenceIntent(query,true),q=norm(query),features=['window banner','imsa decal','contingency decal','contingency logo','paint pattern','body vinyl','rear sponsor'];
  const terms=s=>norm(s).split(' ').map(t=>t.length>4?t.replace(/s$/,''):t),asked=new Set(terms(query));
  const requested=intent.question&&/\b(?:changed|changes|change|updated|update|revisions|revision|history|latest|recently)\b/.test(q)&&/\b(?:artwork|vehicle art|body vinyl|paint patterns?|window banners?|contingency (?:decals?|logos?)|imsa decals?|rear sponsors?|paint shop|preview|flickering)\b/.test(q);
  const wanted=requested?features.filter(f=>terms(f).every(t=>asked.has(t))):[];
  const preview=/\b(?:paint shop|preview|flickering)\b/.test(q);
  const candidates=requested?(car.facts||[]).filter(f=>f.topic===(preview?'paint-preview-history':'paint-artwork-history')):[];
  const matches=candidates.filter(f=>!wanted.length||wanted.some(feature=>{const claim=new Set(terms(String(f.text||'').split(' This ')[0]+' '+(f.helper_implication||'')));return terms(feature).every(t=>claim.has(t));}));
  return {schema:'spb-history-evidence-focus/1',requested,status:!requested?'not-requested':matches.length?'documented-history':'unrecorded-history',requested_features:wanted,
    matched_fact_ids:matches.slice(0,8).map(f=>f.id),more_matches_omitted:matches.length>8,read_only:true,
    authority:'Dated reference history only; no current editing, forced-decals, template compatibility or UV authority.',
    guidance:requested?'Use matched fact IDs for this history question; other reference facts and template labels are background. If no matched fact is recorded, explain the evidence gap. Do not substitute current-template or geometry claims.':'No explicit read-only artwork-history focus requested.'};
}
function report(data,car,query){
  const qt=tokens(query),score=f=>qt.filter(t=>norm(f.text).includes(t)).length;
  const focus=historyEvidence(car,query),focused=new Set(focus.matched_fact_ids);
  const facts=[...(car.facts||[])].sort((a,b)=>Number(focused.has(b.id))-Number(focused.has(a.id))||score(b)-score(a)).slice(0,8);
  const variant=variantReference(car,query);
  const workflow=firstPaintWorkflow(car,query);
  const metadata=(car.template_metadata||[]).slice(0,3);
  const layerReader=typeof module==='object'&&module.exports?require('./layer-reading.js'):(typeof window!=='undefined'?window.SpbTemplateLayers:null);
  const layerGuides=!focus.requested&&!variant.requested&&layerReader&&(/\b(?:layers?|groups?|alpha|metallic|roughness|clearcoat)\b/i.test(query||'')||metadata.some(m=>layerReader.focusedReferenceQuestion&&layerReader.focusedReferenceQuestion(query,m)))?metadata.map(m=>layerReader.reference(m,query)).filter(Boolean):[];
  const general=(data.general_facts||[]).filter(f=>score(f)>=2).slice(0,3);
  const ids=new Set([...(car.source_ids||[]),...facts.flatMap(f=>f.source_ids||[]),...metadata.flatMap(m=>m.source_ids||[]),...general.flatMap(f=>f.source_ids||[])]);
  return {...brief(car),checked_date:car.checked_date,discipline:car.discipline,
    template:car.template,template_download:templateDownloadGuide(car),official_catalog:car.official_catalog,manuals:car.manuals,availability:car.availability,status_basis:car.status_basis,notes:car.notes,facts,
    ...(workflow.requested?{first_paint_workflow:workflow}:{}),...(variant.requested?{variant_reference:variant}:{}),history_focus:focus,general_guidance:general, general_guidance_scope:'General iRacing guidance; not evidence that this model exposes a particular part or control.',
    more_facts_omitted:(car.facts||[]).length>facts.length,
    template_metadata:metadata,template_layer_guides:layerGuides,more_template_files_omitted:(car.template_metadata||[]).length>metadata.length,
    local_layout_references:car.local_layout_references,unknowns:car.unknowns,
    can_target_panels:false,
    sources:Object.fromEntries([...ids].filter(id=>data.sources[id]).map(id=>[id,data.sources[id]]))};
}
function lookup(args={},data){
  valid(args);
  if(!data)return {schema:'spb-car-knowledge-result/1',available:false,error:'Car reference bundle unavailable. Do not infer vehicle geometry.'};
  const choice=select(data,args),resolved=choice.definite && choice.matches.length===1;
  return {schema:'spb-car-knowledge-result/1',available:true,checked_date:data.checked_date,
    resolved:!!resolved,match_reason:choice.reason,read_only:true,
    ...(resolved?{car:report(data,choice.matches[0],args.query)}:{candidates:choice.matches.slice(0,5).map(brief)}),
    ...(choice.retired_matches?{retired_context:choice.retired_matches}:{}),
    ...(choice.comparison?{comparison:comparisonReport(choice,data,args.query)}:{}),
    guidance:resolved?'Reference facts do not verify this open file. Read live state and use existing part confirmation before editing.':
      'Use the exact car/variant or paint folder to choose a reference. Do not infer panel locations from a candidate.',
    reference_coverage:data.coverage};
}
function comparisonReport(choice,data,query){
  return {...choice.comparison,references:choice.matches.slice(0,3).map(car=>{
    const r=report(data,car,query),facts=(r.facts||[]).slice(0,3).map(f=>({...f,text:f.text.slice(0,700)}));
    const sourceIds=new Set(facts.flatMap(f=>f.source_ids||[]));
    return {...brief(car),template:{url:templateDownloadGuide(car).url,latest_revision_verified:false},
      inspected_documents:(car.template_metadata||[]).slice(0,3).map(m=>({file:m.file,width:m.width,height:m.height})),
      facts,sources:Object.fromEntries([...sourceIds].slice(0,6).filter(id=>data.sources[id]).map(id=>[id,data.sources[id]])),
      loaded_file_verified:false,can_target_panels:false,compatibility_verified:false};
  }),limits:['Independent named references; neither verifies the open template.',
    'Shared archive URLs or document names do not prove paint/mask/UV compatibility.',
    'Up to three reference summaries; ambiguous or unknown mentions require exact identities.']};
}
function templateSource(observed,data){
  const proofs=observed.map(x=>x.source_reference).filter(p=>p&&p.schema==='spb-template-source/1'&&/^[a-f0-9]{64}$/i.test(p.sha256||''));
  if(!proofs.length)return null;
  const hashes=[...new Set(proofs.map(p=>p.sha256.toLowerCase()))];
  if(hashes.length!==1)return {matches:[],definite:false,reason:'source-reference-changed-between-reads',identity_conflict:true,identity_evidence:{configured_paint_folders:[],recognized_layouts:[],current_file_verified:false},template_match:{matched:false,reason:'different verified source snapshots'}};
  const rows=[];for(const car of data.cars||[])for(const m of car.template_metadata||[])if(m.sha256===hashes[0])rows.push({car,document:m});
  const matches=[...new Map(rows.map(r=>[r.car.id,r.car])).values()];
  const exact=matches.length===1&&rows.every(r=>r.document.applicability==='exact-variant');
  return {matches,definite:exact,reason:exact?'verified-source-template':'shared-source-template-needs-variant',
    identity_source:'Original source bytes verified during native project Open; saved artwork may differ',
    identity_evidence:{configured_paint_folders:observed.map(x=>x.configured_paint_folder).filter(Boolean),recognized_layouts:observed.map(x=>x.recognized_layout).filter(Boolean),current_file_verified:false,source_reference_verified:true,source_name:proofs[0].source_name,source_sha256:hashes[0],uv_geometry_verified:false},
    template_match:{matched:rows.length>0,sha256:hashes[0],source_name:proofs[0].source_name,verified_at:proofs[0].verified_at,documents:[...new Set(rows.map(r=>r.document.file))].slice(0,6),car_ids:matches.map(c=>c.id),exact_variant:exact,can_target_panels:false,saved_artwork_may_differ:true,uv_geometry_verified:false,
      reason:rows.length?(exact?'Exact inspected source document and variant':'Source document is shared or its variant attribution is unverified'):'Verified source snapshot is absent from the inspected reference corpus'}};
}
function selectContext(query,status,state,data){
  const named=select(data,{query});
  if(named.comparison)return {...named,identity_source:'independent comparison mentions; do not substitute the open paint identity'};
  if(named.retired_matches)return {...named,identity_source:'retired model named; do not substitute a current car or template'};
  if(named.definite&&named.matches.length===1)return {...named,identity_source:'explicit car name in question; may differ from open paint'};
  if(named.reason==='unknown-model-code')return {...named,identity_source:'unrecognized explicit model; do not substitute the open car'};
  if(named.matches.length)return {...named,identity_source:'question names possible cars; resolve the variant before using the open paint identity'};
  const observed=[state&&state.template_identity,status&&status.template_identity].filter(Boolean);
  const source=templateSource(observed,data);
  if(source && (source.identity_conflict||source.matches.length)){
    if((named.excluded_ids||[]).some(id=>source.matches.some(c=>c.id===id)))return {...named,identity_source:'buyer excludes the matched source reference; confirm the current template',identity_conflict:true,template_match:source.template_match};
    const folders=observed.map(x=>x.configured_paint_folder).filter(Boolean);
    const conflict=folders.some(folder=>{const choice=select(data,{paint_folder:folder});return choice.matches.length&&!choice.matches.some(c=>source.matches.some(s=>s.id===c.id));});
    return {...source,...(conflict?{definite:false,identity_conflict:true,reason:'source-template-destination-conflict'}:{})};
  }
  const folders=[...new Set(observed.map(x=>x.configured_paint_folder).filter(Boolean))];
  const hints=[state&&state.car&&state.car.recognised_as,status&&status.car,...observed.map(x=>x.recognized_layout)];
  const recognised=[...new Set(hints.map(h=>typeof h==='string'?h:h&&(h.name||h.id)).filter(Boolean))];
  if(folders.length){
    const selections=folders.map(folder=>select(data,{paint_folder:folder}));
    if(selections.some(s=>s.matches.some(c=>(named.excluded_ids||[]).includes(c.id))))return {...named,reason:'excluded-configured-car',identity_source:'buyer excludes the configured car; verify the loaded template',identity_conflict:true,identity_evidence:{configured_paint_folders:folders,recognized_layouts:recognised,current_file_verified:false}};
    const current=selections[0],contradiction=selections.some(s=>s.matches.length&&recognised.some(n=>{
      const r=select(data,{query:n});return r.definite&&r.matches.length===1&&!s.matches.some(c=>c.id===r.matches[0].id);
    }));
    return {...current,...(folders.length>1?{definite:false,reason:'live-folder-changed-between-reads',matches:[...new Map(selections.flatMap(s=>s.matches).map(c=>[c.id,c])).values()]}:{}),
      identity_source:'configured iRacing destination; this does not verify the loaded template',
      template_match:source&&source.template_match,
      identity_evidence:{configured_paint_folders:folders,recognized_layouts:recognised,source_paint_name:observed[0].source_paint_name||null,current_file_verified:false},
      identity_conflict:contradiction||folders.length>1};
  }
  const recognizedChoices=recognised.map(name=>select(data,{query:name})).filter(s=>s.matches.length);
  if(recognizedChoices.length){
    const first=recognizedChoices[0],all=[...new Map(recognizedChoices.flatMap(s=>s.matches).map(c=>[c.id,c])).values()];
    // A filename cannot establish identity, but a qualified conflicting name
    // invalidates silent reliance on a broad layout recognizer (native ARCA case).
    const sourceNames=[...new Set(observed.map(x=>x.source_paint_name).filter(n=>typeof n==='string'&&n.length<=240))];
    const filenameChoices=sourceNames.map(name=>select(data,{query:name})).filter(s=>s.definite&&s.matches.length===1);
    const filenameConflict=filenameChoices.some(s=>!all.some(c=>c.id===s.matches[0].id));
    if(filenameConflict)return {matches:[...new Map([...all,...filenameChoices.flatMap(s=>s.matches)].map(c=>[c.id,c])).values()],definite:false,reason:'source-name-recognition-conflict',identity_conflict:true,
      identity_source:'Source filename and live layout recognition suggest different variants; neither verifies the current template',
      identity_evidence:{configured_paint_folders:[],recognized_layouts:recognised,source_paint_names:sourceNames,current_file_verified:false},template_match:source&&source.template_match};
    const conflict=recognizedChoices.some(s=>s.matches.map(c=>c.id).sort().join('|')!==first.matches.map(c=>c.id).sort().join('|'));
    if(conflict)return {matches:all,definite:false,reason:'conflicting-live-recognition',identity_conflict:true,identity_source:'live recognition disagrees between observations',identity_evidence:{configured_paint_folders:[],recognized_layouts:recognised,current_file_verified:false}};
    if((named.excluded_ids||[]).some(id=>first.matches.some(c=>c.id===id)))return {...named,identity_source:'buyer excludes the recognized car; verify the loaded template'};
    return {...first,template_match:source&&source.template_match,identity_source:'live app recognition; verify exact variant and current template'};
  }
  return source ? {...named,template_match:source.template_match,identity_evidence:source.identity_evidence,identity_source:source.identity_source} : named;
}
function identitySummary(choice){
  const names=(choice.matches||[]).slice(0,3).map(c=>c.name),match=choice.template_match;
  let status='unknown',text='Tell me the car and version for car-specific advice. I can still help explain the loaded layer groups.';
  if(choice.identity_conflict){
    status='conflict';
    text=choice.reason==='source-name-recognition-conflict'?'The source filename and suggested layout disagree. Confirm the car and version before using car-specific advice.':'The source reference and current car settings disagree. Confirm the loaded template and iRacing destination before using car-specific advice.';
  }else if(match&&match.matched&&match.exact_variant&&names.length===1){
    status='verified-source';text='Original template: '+names[0]+'. Its source matches the inspected template reference. Saved artwork may differ; I will check the actual layer or marked area before placing changes.';
  }else if(match&&!match.matched){
    status='unmatched-source';text='The saved source is verified, but it has no match in the inspected template references. Confirm the car and version for car-specific advice; I can still explain the loaded layer groups.';
  }else if(match&&match.matched){
    status='shared-template';text='This source template is shared or its exact variant is unverified'+(names.length?': '+names.join(' / '):'')+'. Confirm the car and version before using car-specific advice.';
  }else if(names.length){
    status='suggested-reference';text='Suggested car reference: '+names.join(' / ')+'. This does not verify the loaded template. Confirm the car and version before placing car-specific changes.';
  }
  return {status,text,source_verified:status==='verified-source',can_target_panels:false};
}
function fromContext(query,status,state,data){
  if(!data)return lookup({query},data);
  const choice=selectContext(query,status,state,data),resolved=choice.definite&&choice.matches.length===1;
  const found=resolved?lookup({query,car_id:choice.matches[0].id},data):{...lookup({query:''},data),candidates:choice.matches.slice(0,5).map(brief)};
  return {...found,match_reason:choice.reason,retired_context:choice.retired_matches,identity_source:choice.identity_source,identity_evidence:choice.identity_evidence,identity_conflict:choice.identity_conflict,template_match:choice.template_match,
    ...(choice.comparison?{comparison:comparisonReport(choice,data,query)}:{}),
    live_identity_summary:identitySummary(selectContext('',status,state,data))};
}
return {TOOL,lookup,fromContext,norm,referenceText,select,selectContext,templateSource,identitySummary,referenceIntent,templateDownloadGuide,historyEvidence,variantReference,firstPaintWorkflow};

});
