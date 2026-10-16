/* CX3 2026-10-09 (CODEX-INTEGRATE-2): production copy of mcp/chatgpt/car-knowledge/layer-reading.js (sha256 7ae99176aec9936f, body unchanged).
   window.SpbTemplateLayers reads the layer NAMES/GROUPS of a loaded template and tells the body paint layer apart from spec-map / alpha / export-guide layers (ARCA has four layers named Base Paint, three of them spec maps).
   Action-free helper: it never paints by itself. Callers are guarded by window.SPB_CX3_OFF (kill switch).
   Origin: Codex request REQUESTS_FOR_CLAUDE.md 'Shared layer intelligence' / 'Shared native-colour and Undo delta'. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SpbTemplateLayers=factory();})(typeof window==='undefined'?this:window,function(){
    'use strict';
    function text(s){return typeof s==='string'?s.replace(/[\u0000-\u001f]/g,' ').slice(0,180):'';}
    function norm(s){return text(s).toLowerCase().replace(/[_-]+/g,' ').replace(/\s+/g,' ').trim();}
    function classify(row){
        var name=norm(row&&row.name),group=norm(row&&(row.groupName||row.group)),path=group+' / '+name;
        // A named material group outranks the generic names Base Paint, Parts or Mask.
        if(/\bspec(?:ular)?\s*map\b/.test(path)||/(?:^|\/)\s*spec(?:ular)?\s*(?:\/|$)/.test(group)||/\b(?:red channel metallic|green channel roughness|blue channel clearcoat)\b/.test(path)){
            if(/\balpha\b/.test(name))return {kind:'spec',role:'spec map alpha (purpose unverified)',alpha_label:true};
            var channel=/\bmetallic\b|\bred channel\b/.test(path)?'metallic':/\broughness\b|\bgreen channel\b/.test(path)?'roughness':/\bclear\s*coat\b|\bblue channel\b/.test(path)?'clearcoat':null;
            return {kind:'spec',role:'spec map'+(channel?' ('+channel+')':''),channel:channel};
        }
        if(/\bturn off before (?:export|exporting)\b/.test(path))return {kind:'export-guide',role:'template (switch off before exporting)',explicit_export_label:true};
        if(/\b(?:wireframe|wire|uv|guide|outline)\b/.test(name))return {kind:'guide',role:'template guide'};
        if(/\balpha\b/.test(name))return {kind:'alpha',role:'alpha layer (purpose unverified)'};
        return null;
    }
    function hintScore(h,question){var q=norm(question);return (h.alpha_label||h.kind==='alpha')&&/\balpha\b/.test(q)?10:h.channel&&new RegExp('\\b'+h.channel+'\\b').test(q)?10:h.kind==='export-guide'&&/\bexport\b/.test(q)?10:0;}
    function materialGuide(){
        return {schema:'spb-material-guide/1',basis:'Official iRacing exported spec-map channel rules; not a measurement of these layers or an SPB slider conversion.',
            channels:[
                {channel:'red',property:'metallic',low:0,high:255,meaning:'Red/metallic: 0 is nonmetal; 255 is metal. This changes lighting response, not the paint colour. Metallic paint can appear darker; inspect the paint colour and material together.',source:0},
                {channel:'green',property:'roughness',low:0,high:255,meaning:'Green/roughness: 0 is smooth and reflective; 255 is rough and less reflective. Increasing green does not increase gloss.',source:0},
                {channel:'blue',property:'clearcoat',off_range:[0,15],maximum_reflectivity:16,minimum_reflectivity:255,meaning:'Blue/clearcoat adds a separate coating response. iRacing’s 2023 update defines 0–15 as coat off, 16 as strongest coat reflection, and 255 as no coat shine. Higher blue is not more glossy. Older leave-blue-white advice predates this change.',source:1},
                {channel:'alpha',property:'lighting-mask',meaning:'Spec-map alpha masks lighting response. An Alpha layer name alone does not verify its contents or exported alpha channel.',source:0}
            ],sources:[{url:'https://www.iracing.com/custom-paint-textures/',label:'iRacing: spec-map material channels'},{url:'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-',label:'iRacing 2023 S1: clearcoat encoding'}],actions:[]};
    }
    function read(rows,source,question){
        if(!Array.isArray(rows)||!rows.length)return {schema:'spb-template-layers/1',available:false,reason:'No live layer records supplied.',actions:[]};
        var groups=new Map(),dupes=new Map(),count=Math.min(rows.length,300),spec=0;
        for(var i=0;i<count;i++){
            var r=rows[i];if(!r||typeof r.name!=='string')continue;
            var name=text(r.name),group=text(r.groupName||r.group),hint=classify(r),key=group||'(ungrouped)';
            var item=groups.get(key)||{group:key,observed_layers:0,examples:[],hints:[],visible_examples:[]};
            item.observed_layers++;if(item.examples.length<4)item.examples.push(name);
            if((r.visible===true||r.hidden===false)&&item.visible_examples.length<4)item.visible_examples.push(name);
            if(hint){var saved=item.hints.find(function(h){return h.role===hint.role;});if(!saved){saved=Object.assign({},hint,{examples:[]});item.hints.push(saved);}if(saved.examples.length<4)saved.examples.push(name);}
            if(hint&&hint.kind==='spec')spec++;
            groups.set(key,item);var names=dupes.get(norm(name))||[];names.push({name:name,group:group||null,id:typeof r.id==='number'&&Number.isFinite(r.id)||typeof r.id==='string'&&r.id.length>0&&r.id.length<=180?r.id:undefined});dupes.set(norm(name),names);
        }
        function score(g){return g.hints.length?Math.max.apply(null,g.hints.map(function(h){return hintScore(h,question);})):0;}
        var important=Array.from(groups.values()).sort(function(a,b){return score(b)-score(a)||Number(!!b.hints.length)-Number(!!a.hints.length);});
        var duplicate_names=Array.from(dupes.values()).filter(function(v){return v.length>1;}).slice(0,8).map(function(v){return {name:v[0].name,occurrences:v.length,groups:v.slice(0,6).map(function(x){return x.group;}),current_matches:v.filter(function(x){return x.id!==undefined;}).slice(0,6).map(function(x){return {id:x.id,name:x.name,group:x.group};})};});
        return {schema:'spb-template-layers/1',available:groups.size>0,source:source||'Observed live layer names and groups',basis:'Label hints only; pixel contents and UV positions have not been inspected.',observed_records:count,records_omitted:Math.max(0,rows.length-count),groups:important.slice(0,12),groups_omitted:Math.max(0,important.length-12),spec_label_records:spec,material_guide:spec?materialGuide():null,duplicate_names:duplicate_names,can_target_panels:false,actions:[],guidance:'Use the full group and exact layer identity when names repeat. A spec-group Base Paint is not the livery body layer. An export label is advice to inspect before exporting, not permission to hide or delete layers. Alpha/control-pixel purposes remain unverified.'};
    }
    function referenceRows(metadata){
        if(!metadata||!Array.isArray(metadata.layer_labels)||!Array.isArray(metadata.layer_groups))return null;
        var groups=new Set(metadata.layer_groups);
        return metadata.layer_labels.filter(function(path){return typeof path==='string'&&!groups.has(path);}).map(function(path){var bits=path.split(' / ');return {name:bits.pop(),group:bits.join(' / ')};});
    }
    function reference(metadata,question){
        var rows=referenceRows(metadata);if(!rows)return null;
        var sheet=read(rows,'Inspected official template labels: '+text(metadata.file),question);
        sheet.reference_file=text(metadata.file);sheet.reference_sha256=metadata.sha256;
        sheet.label_subset=metadata.more_labels_omitted===true;
        sheet.current_file_verified=false;
        sheet.basis='Selected labels from an inspected official template; not an observation of the currently loaded file. Pixel contents and UV positions have not been inspected.';
        return sheet;
    }
    function inventoryQuestion(question){
        var q=String(question||'').replace(/\b(?:do not|don't|dont)\s+(?:change|edit|paint|apply)\s+(?:anything|the paint|my paint)\b[.!?]*/ig,'').trim();
        return /^(?:please\s+)?(?:show|list|display)\s+(?:me\s+)?(?:(?:my|this|the\s+(?:open|current)|current|open|loaded|all)\s+)?(?:layers|groups|layer\s+list)\s*[.!?]*$/i.test(q);
    }
    function hasEditTail(question){return /\b(?:then|also|and)\s+(?:make|change|apply|hide|delete|set|paint|recolou?r)\b|[.!?]\s*(?:make|change|apply|hide|delete|set|paint|recolou?r)\b/i.test(String(question||''));}
    function materialQuestion(question){
        var q=String(question||'');
        return /^(?:\s*please\s+)?\s*(?:what|which|why|explain|help)\b/i.test(q)&&/\b(?:template|spec(?:ular)?\s*map)\b/i.test(q)&&/\b(?:metallic|roughness|clear\s*coat|alpha|blue\s+channel|green\s+channel|red\s+channel)\b/i.test(q)&&!hasEditTail(q);
    }
    function answer(question,rows,metadata){
        if(hasEditTail(question))return null;
        var inventory=inventoryQuestion(question);
        if(!inventory&&!materialQuestion(question)&&(!/\b(?:layers?|groups?)\b/i.test(question)||!/\b(?:what|which|why|explain|difference|mean|understand|should|help)\b/i.test(question)||!/\b(?:template|spec|base paint|groups?|metallic|roughness|clearcoat|export|wire|alpha)\b/i.test(question)))return null;
        var sheet=read(rows,undefined,question),lines=[],sources=[],explained=new Set();
        if(!sheet.available)return inventory?{id:'assistant.template_layers',title:metadata?'Inspected template layers':'Your loaded layers',live_context:!metadata,reference_context:!!metadata,text:metadata?'No inspected layer labels are available for this reference.':'No loaded raster layer records are available. Open a layered PSD, XCF or ORA file to inspect its layers. Nothing has been changed.',summary:metadata?'No inspected layer labels available.':'No loaded raster layer records available.',how:[],actions:[],related:[],faq:null,shot:null}:null;
        function score(h){return hintScore(h,question);}
        var hinted=sheet.groups.filter(function(g){return g.hints.length;}).sort(function(a,b){return Math.max.apply(null,b.hints.map(score))-Math.max.apply(null,a.hints.map(score));});
        if(!inventory&&hinted.some(function(g){return g.hints.some(function(h){return score(h)>0;});}))hinted=hinted.filter(function(g){return g.hints.some(function(h){return score(h)>0;});});
        if(inventory){
            lines.push('I can read '+sheet.observed_records+' '+(metadata?'inspected template':'loaded')+' layer records. Here are their groups, with up to four name examples per group:');
            sheet.groups.forEach(function(g){lines.push(g.group+' — '+g.observed_layers+' layer'+(g.observed_layers===1?'':'s')+': '+g.examples.join(', ')+'.');});
            if(sheet.groups_omitted||sheet.records_omitted)lines.push('This is a bounded overview; additional groups or records are present. Inspect the layer panel for the full loaded list.');
        }
        else hinted.slice(0,5).forEach(function(g){
            var h=g.hints.slice().sort(function(a,b){return score(b)-score(a);})[0];lines.push(g.group+': '+(h.alpha_label||h.kind==='alpha'?'contains an alpha-labelled layer; its actual purpose needs confirmation.':h.kind==='spec'?'labelled as '+h.role+'; this controls material appearance, not the livery body colour.':h.kind==='export-guide'?'its label says to switch these guides off before exporting; check the actual visible layers before export.':'contains guide-labelled layers; confirm their purpose before editing.')+' Examples: '+h.examples.join(', ')+'.');
            var rule=sheet.material_guide&&sheet.material_guide.channels.find(function(c){return c.property===(h.alpha_label?'lighting-mask':h.channel);});
            if(rule&&!explained.has(rule.property)){explained.add(rule.property);lines.push(rule.meaning);var source=sheet.material_guide.sources[rule.source];if(!sources.some(function(s){return s.url===source.url;}))sources.push(source);}
        });
        if(!inventory&&(hinted.length>5||sheet.groups_omitted))lines.push('This short explanation shows '+Math.min(5,hinted.length)+' groups; additional groups are present in the layer panel.');
        if(sheet.duplicate_names.length)lines.push('Names repeat ('+sheet.duplicate_names.slice(0,3).map(function(x){return x.name;}).join(', ')+'); specify the full group and exact layer rather than a bare name.');
        if(!lines.length)return null;
        lines.push(metadata?'These are selected label hints from the inspected '+text(metadata.file)+' reference. They do not verify your loaded file, UV positions or authorize a paint change.':'These are label hints from the loaded layers. They do not establish UV positions or authorize a paint change.');
        if(metadata&&metadata.more_labels_omitted)lines.push('The reference keeps a limited selection of labels; inspect the complete template for other layers.');
        if(sources.length)lines.push('These are exported spec-map values; this answer does not measure your current pixels or convert SPB controls. Nothing has been changed.');
        return {id:'assistant.template_layers',title:inventory?(metadata?'Inspected template layers':'Your loaded layers'):'Understand this template’s layers',live_context:!metadata,reference_context:!!metadata,text:lines.join('\n'),summary:lines.join('\n'),sources:sources,how:[],actions:[],related:[],faq:null,shot:null};
    }
    function answerReference(question,metadata){var rows=referenceRows(metadata);return rows?answer(question,rows,metadata):null;}
    return {classify:classify,read:read,answer:answer,reference:reference,answerReference:answerReference,inventoryQuestion:inventoryQuestion,materialGuide:materialGuide,materialQuestion:materialQuestion};
});
