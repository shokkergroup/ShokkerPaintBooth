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
    function hintScore(h,question){var q=norm(question),alias={metallic:/\bred channel\b/,roughness:/\bgreen channel\b/,clearcoat:/\bblue channel\b|\bclear coat\b/};return (h.alpha_label||h.kind==='alpha')&&/\balpha\b/.test(q)?10:h.channel&&(new RegExp('\\b'+h.channel+'\\b').test(q)||(alias[h.channel]&&alias[h.channel].test(q)))?10:h.kind==='export-guide'&&/\bexport\b/.test(q)?10:0;}
    function materialGuide(){
        return {schema:'spb-material-guide/1',basis:'Official iRacing exported spec-map channel rules; not a measurement of these layers or an SPB slider conversion.',
            channels:[
                {channel:'red',property:'metallic',low:0,high:255,meaning:'Red/metallic: 0 is nonmetal; 255 is metal. This changes lighting response, not the paint colour. Metallic paint can appear darker; inspect the paint colour and material together.',source:0},
                {channel:'green',property:'roughness',low:0,high:255,meaning:'Green/roughness: 0 is smooth and reflective; 255 is rough and less reflective. Increasing green does not increase gloss.',source:0},
                {channel:'blue',property:'clearcoat',off_range:[0,15],maximum_reflectivity:16,minimum_reflectivity:255,meaning:'Blue/clearcoat adds a separate coating response. iRacing’s 2023 update defines 0–15 as coat off, 16 as strongest coat reflection, and 255 as no coat shine. Higher blue is not more glossy. Older leave-blue-white advice predates this change.',source:1},
                {channel:'alpha',property:'lighting-mask',meaning:'Spec-map alpha masks lighting response. An Alpha layer name alone does not verify its contents or exported alpha channel.',source:0}
            ],sources:[{url:'https://www.iracing.com/custom-paint-textures/',label:'iRacing: spec-map material channels'},{url:'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-',label:'iRacing 2023 S1: clearcoat encoding'}],actions:[]};
    }
    function focusedLayers(question,rows){
        var q=norm(question),list=Array.isArray(rows)?rows:[],bounded=list.slice(0,300),labels=[];
        function contains(label){return label&&(' '+q+' ').indexOf(' '+label+' ')>=0;}
        // Read-only explanations may use a quoted layer name without saying “layer”.
        q=q.replace(/[“”"'‘’?!.,:;]/g,' ').replace(/\s+/g,' ').trim();
        bounded.forEach(function(r){if(r&&typeof r.name==='string'&&contains(norm(r.name)))labels.push(norm(r.name));});
        labels=Array.from(new Set(labels)).sort(function(a,b){return b.length-a.length;});
        var label=labels[0],byId=bounded.filter(function(r){return r&&r.id!=null&&contains(norm(String(r.id)));});
        if(!label&&!byId.length)return null;
        var matched=byId.length?byId:bounded.filter(function(r){return r&&norm(r.name)===label;});
        var paths=matched.filter(function(r){return contains(norm((r.groupName||r.group||'')+' / '+r.name));});
        if(paths.length)matched=paths;
        var choices=matched.slice(0,12).map(function(r){
            var h=classify(r),group=text(r.groupName||r.group),visible=typeof r.visible==='boolean'?r.visible:typeof r.hidden==='boolean'?!r.hidden:null;
            if((r.groupChain||[]).some(function(g){return g&&(g.visible===false||g.ownVisible===false);}))visible=false;
            var artwork=!h&&/\bpaintable area\b/.test(norm(group))&&/^(?:base paint|body paint)$/.test(norm(r.name));
            return {id:typeof r.id==='number'&&Number.isFinite(r.id)||typeof r.id==='string'&&r.id.length>0&&r.id.length<=180?r.id:null,name:text(r.name),group:group||null,visible:visible,kind:h?h.kind:artwork?'artwork':'unknown',role:h?h.role:artwork?'base artwork (label hint)':'purpose unverified',channel:h&&h.channel||null};
        });
        return {schema:'spb-focused-layers/1',read_only:true,matched_name:choices[0]&&choices[0].name,observed_matches:matched.length,choices:choices,omitted_matches:Math.max(0,matched.length-choices.length),unread_records:Math.max(0,list.length-300),basis:'Exact observed names, optional group path or ID; labels do not establish pixel contents or authorize an edit.',actions:[]};
    }
    function focusedQuestion(question,rows){
        var q=String(question||'').trim();
        if(/\b(?:move|resize|rotate|duplicate|merge|delete|hide|render|export)\b/i.test(q)&&!/\b(?:mean|meaning|purpose|difference|why|should)\b/i.test(q))return false;
        if(/\b(?:colou?rs?|palette|pixels?)\b/i.test(q)&&!/\b(?:should|use|for|mean|purpose|difference)\b/i.test(q)&&!/^(?:please\s+)?(?:what is|what does|explain)\b/i.test(q))return false;
        return /^(?:please\s+)?(?:what|which|why|explain|help me understand|how does|how do .*? work)\b/i.test(q)&&!hasEditTail(q)&&!!focusedLayers(q,rows);
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
        return {schema:'spb-template-layers/1',available:groups.size>0,source:source||'Observed live layer names and groups',basis:'Label hints only; pixel contents and UV positions have not been inspected.',observed_records:count,records_omitted:Math.max(0,rows.length-count),groups:important.slice(0,12),groups_omitted:Math.max(0,important.length-12),spec_label_records:spec,material_guide:spec?materialGuide():null,duplicate_names:duplicate_names,focused_layers:focusedLayers(question,rows),can_target_panels:false,actions:[],guidance:'Use the full group and exact layer identity when names repeat. A spec-group Base Paint is not the livery body layer. An export label is advice to inspect before exporting, not permission to hide or delete layers. Alpha/control-pixel purposes remain unverified.'};
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
        if(referenceExportQuestion(question,metadata))sheet.export_guidance=referenceExportAnswer(question,metadata);
        return sheet;
    }
    function inventoryQuestion(question){
        var q=String(question||'').replace(/\b(?:do not|don't|dont)\s+(?:change|edit|paint|apply)\s+(?:anything|the paint|my paint)\b[.!?]*/ig,'').trim();
        return /^(?:please\s+)?(?:show|list|display)\s+(?:me\s+)?(?:(?:my|this|the\s+(?:open|current)|current|open|loaded|all)\s+)?(?:layers|groups|layer\s+list)\s*[.!?]*$/i.test(q);
    }
    function exportQuestion(question){
        var q=String(question||'').trim();
        return /^(?:what|which|how|should|do|are|is)\b/i.test(q)&&/\bexport(?:ing)?\b/i.test(q)&&/\b(?:layers?|guides?|hide|hidden|off|visible|on)\b/i.test(q)&&!hasEditTail(q)&&!/(?:[;.!?]|\b(?:and|then|also)\b)\s*(?:then\s+)?(?:please\s+)?(?:hide|turn|switch|remove|delete|export|render)\b/i.test(q);
    }
    function exportGuides(rows){
        var list=Array.isArray(rows)?rows:[],found=[],shown=0,hidden=0,unknown=0;
        list.slice(0,1000).forEach(function(r){
            if(!r)return;var paths=[r.groupName||r.group,r.path].concat((r.groupChain||[]).map(function(g){return g&&(g.name||g.path);}));
            var group=paths.find(function(p){return /turn\s*off\s*before\s*export/i.test(String(p||''));});if(!group)return;
            var visible=typeof r.visible==='boolean'?r.visible:typeof r.hidden==='boolean'?!r.hidden:null;
            if((r.groupChain||[]).some(function(g){return g&&(g.visible===false||g.ownVisible===false);}))visible=false;
            if(visible===true)shown++;else if(visible===false)hidden++;else unknown++;
            if(found.length<24)found.push({id:r.id==null?null:String(r.id),name:text(r.name),group:text(group),visible:visible});
        });
        return {schema:'spb-export-guides/1',read_only:true,records:found,shown:shown,hidden:hidden,unknown:unknown,omitted_matches:Math.max(0,shown+hidden+unknown-found.length),unread_records:Math.max(0,list.length-1000),basis:'Explicit Turn Off Before Export group/path labels and stored layer/group visibility; no pixel or UV inference.',actions:[]};
    }
    function exportAnswer(question,report,policy){
        if(!exportQuestion(question))return null;
        report=report||exportGuides([]);var lines=[],p=policy||{};
        if(!report.records.length)lines.push('I do not see an explicitly labelled “Turn Off Before Export” group in the loaded layer records. A layer named Mask or Wire alone does not establish that it should be excluded. Check this template’s instructions before hiding artwork.');
        else {
            var groups=Array.from(new Set(report.records.map(function(r){return r.group;})));
            lines.push('Your loaded template labels '+groups.map(function(g){return '“'+g+'”';}).join(', ')+' as export guides.');
            [['Currently shown',true],['Already hidden',false],['Visibility not available',null]].forEach(function(pair){var rows=report.records.filter(function(r){return r.visible===pair[1];});if(rows.length)lines.push(pair[0]+': '+rows.map(function(r){return r.name+(r.id!==null?' ['+r.id+']':'');}).join(', ')+'.');});
            lines.push(p.known&&p.enabled?'SPB’s guide filtering is enabled for Render. You can keep these guides while editing; hiding the shown ones is optional for a cleaner Source view. Do not toggle the already-hidden ones back on.':p.known?'Automatic guide filtering is disabled. Hide this labelled guide group before rendering, and check the output.':'I cannot confirm automatic export filtering in this build. Hide the labelled guide group before rendering, and check the output.');
            lines.push('Keep artwork outside that group as it is. Check the Render result: stored visibility and an enabled filter alone do not prove the exported pixels.');
        }
        if(report.omitted_matches||report.unread_records)lines.push('This is a bounded list; check the layer panel for additional records.');
        lines.push('Nothing has been changed.');
        var body=lines.join('\n\n');return {cls:'ANSWER',via:'design-advice',answer:{id:'assistant.live_export_guides',title:'Your template’s export guides',live_context:true,text:body,summary:body,chat_summary:body,export_guides:report,export_filter:p,how:[],actions:[],related:[],sources:[],faq:null,shot:null}};
    }
    function hasEditTail(question){return /(?:\b(?:then|also|and)\s+|[;.!?]\s*)(?:(?:then|also|please)\s+)*(?:(?:can|could|would)\s+you\s+)?(?:make|change|apply|hide|delete|set|paint|recolou?r|colou?r|tint|fill|add|save|render|export|remove|turn|switch)\b/i.test(String(question||''));}
    function materialQuestion(question){
        var q=String(question||'');
        return /^(?:\s*please\s+)?\s*(?:what|which|why|explain|help)\b/i.test(q)&&/\b(?:template|spec(?:ular)?\s*map)\b/i.test(q)&&/\b(?:metallic|roughness|clear\s*coat|alpha|blue\s+channel|green\s+channel|red\s+channel)\b/i.test(q)&&!hasEditTail(q);
    }
    function answer(question,rows,metadata){
        if(hasEditTail(question))return null;
        var inventory=inventoryQuestion(question);
        if(!inventory&&focusedQuestion(question,rows))return focusedAnswer(question,rows,metadata);
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
        var concise=[];
        if(!inventory){
            concise.push(metadata?'From the inspected '+text(metadata.file)+' reference (not a verification of your open paint):':'From the labels in your loaded template:');
            var properties=Array.from(explained),shortMeaning={metallic:'Metallic (red) controls metal versus nonmetal lighting response.',roughness:'Roughness (green) controls smooth versus rough reflection; higher values are less glossy.',clearcoat:'Clearcoat (blue) controls a separate coating response; higher values do not mean more gloss.','lighting-mask':'Spec alpha masks lighting response; a layer name does not verify exported alpha.'};
            properties.forEach(function(property){var rule=sheet.material_guide.channels.find(function(c){return c.property===property;});concise.push('- '+(properties.length===1?rule.meaning:shortMeaning[property]));});
            if(hinted.some(function(g){return g.hints.some(function(h){return h.kind==='export-guide';});}))concise.push('- The export-guide group is labelled to be switched off before export; inspect those layers first.');
            if(!properties.length&&!concise.some(function(l){return l.indexOf('- ')===0;}))concise.push('The listed guide/alpha layers need their purpose confirmed before editing.');
            if(sheet.duplicate_names.length)concise.push('Use the full group and layer name when names repeat.');
            concise.push('These are label-based facts, not verified UV positions or measured pixels. No paint changed. Layer details and sources are below.');
        }
        return {id:'assistant.template_layers',title:inventory?(metadata?'Inspected template layers':'Your loaded layers'):'Understand this template’s layers',live_context:!metadata,reference_context:!!metadata,text:lines.join('\n\n'),summary:lines.join('\n'),chat_summary:concise.length?concise.join('\n'):null,sources:sources,how:[],actions:[],related:[],faq:null,shot:null};
    }
    function focusedAnswer(question,rows,metadata){
        var report=focusedLayers(question,rows);if(!report)return null;
        var lines=[],sources=[],guide=materialGuide(),properties=new Set();
        lines.push((metadata?'In the inspected '+text(metadata.file)+' reference':'In your loaded layers')+', '+report.observed_matches+' '+(report.observed_matches===1?'record matches':'records match')+' “'+report.matched_name+'”:');
        report.choices.forEach(function(c){
            lines.push('- '+(c.group?c.group+' / ':'')+c.name+(!metadata&&c.id!==null?' ['+c.id+']':'')+' — '+c.role+(!metadata?'; '+(c.visible===true?'shown':c.visible===false?'hidden':'visibility unavailable'):'')+'.');
            if(c.channel)properties.add(c.channel);
        });
        if(report.choices.some(function(c){return c.kind==='artwork';})&&report.choices.some(function(c){return c.kind==='spec';}))lines.push('For the livery’s base colour, the Paintable Area / Base Paint label is the artwork candidate. The spec-group copies control material response, not the livery body colour. Confirm the artwork in the preview before changing it; a name alone does not measure its pixels.');
        var concise=lines.slice();
        properties.forEach(function(property){var rule=guide.channels.find(function(c){return c.property===property;});if(rule){lines.push(rule.meaning);var s=guide.sources[rule.source];if(!sources.some(function(x){return x.url===s.url;}))sources.push(s);}});
        if(report.choices.every(function(c){return c.kind==='unknown';}))lines.push('These labels do not tell me what the layer contains. Inspect it in the layer panel and preview before choosing a change.');
        if(report.observed_matches>1)lines.push('Names repeat; choose the full group and exact layer before requesting a change.');
        if(report.omitted_matches||report.unread_records||metadata&&metadata.more_labels_omitted)lines.push('This is a bounded list; additional matching layers may exist. Inspect the complete layer panel or template.');
        lines.push(metadata?'This reference does not verify your open file. Labels do not establish UV positions or measured pixels. Nothing has been changed.':'This reads your current labels and stored visibility. It does not establish UV positions or measured pixels. Nothing has been changed.');
        concise.push(lines[lines.length-1]);
        if(report.omitted_matches||report.unread_records||metadata&&metadata.more_labels_omitted)concise.push('This list is bounded; check the complete layer panel or template.');
        var body=lines.join('\n\n');return {id:'assistant.template_layers',title:'Choose the exact '+report.matched_name+' layer',live_context:!metadata,reference_context:!!metadata,text:body,summary:body,chat_summary:concise.join('\n\n'),layer_choices:report,sources:sources,how:[],actions:[],related:[],faq:null,shot:null};
    }
    function referenceExportQuestion(question,metadata){
        if(hasEditTail(question))return false;
        if(exportQuestion(question))return true;
        var q=norm(question).replace(/[“”"'‘’?!.,:;]/g,' ').replace(/\s+/g,' ').trim();
        return /^(?:please\s+)?(?:what|why|explain|help me understand)\b/.test(q)&&metadata&&Array.isArray(metadata.layer_groups)&&metadata.layer_groups.some(function(g){var label=norm(g);return /turn\s*off\s*before\s*export/.test(label)&&(' '+q+' ').indexOf(' '+label+' ')>=0;});
    }
    function referenceExportAnswer(question,metadata){
        if(!referenceExportQuestion(question,metadata))return null;
        var rows=referenceRows(metadata);if(!rows)return null;
        var report=exportGuides(rows),groups=Array.isArray(metadata.layer_groups)?metadata.layer_groups.filter(function(g){return /turn\s*off\s*before\s*export/i.test(g);}):[];
        var lines=['From the inspected '+text(metadata.file)+' reference; this does not verify your open paint:'];
        if(groups.length){
            lines.push(groups.map(function(g){return '“'+text(g)+'”';}).join(', ')+' explicitly instructs that template group to be switched off before TGA export.');
            if(report.records.length)lines.push('Selected labels in that group: '+report.records.map(function(r){return r.name;}).join(', ')+'.');
            lines.push('This is a group-label instruction. A name such as Car Mandatory does not establish a forced-decal rule. Keep artwork outside the labelled group as it is.');
        }else lines.push('The selected reference labels do not include an explicit Turn Off Before Export group. Mask or Wire alone does not establish what should be excluded; check this template’s instructions.');
        lines.push('I have not checked current layer/group visibility or whether SPB’s Render filter excludes these guides. Check the actual rendered/exported result before accepting it.');
        if(metadata.more_labels_omitted||report.omitted_matches||report.unread_records)lines.push('This is a selected, bounded label list; inspect the complete template for additional records.');
        lines.push('No pixels or UV positions are verified, and nothing has been changed.');
        var body=lines.join('\n\n');return {id:'assistant.template_export_reference',title:'Understand this template’s export group',reference_context:true,live_context:false,current_file_verified:false,text:body,summary:body,chat_summary:body,export_guides:report,reference_file:text(metadata.file),reference_sha256:metadata.sha256,sources:[],how:[],actions:[],related:[],faq:null,shot:null};
    }
    function focusedReferenceQuestion(question,metadata){var rows=referenceRows(metadata);return referenceExportQuestion(question,metadata)||!!rows&&focusedQuestion(question,rows);}
    function answerReference(question,metadata){var exported=referenceExportAnswer(question,metadata);if(exported)return exported;var rows=referenceRows(metadata);return rows?answer(question,rows,metadata):null;}
    return {focusedReferenceQuestion:focusedReferenceQuestion,classify:classify,read:read,answer:answer,reference:reference,answerReference:answerReference,inventoryQuestion:inventoryQuestion,materialGuide:materialGuide,materialQuestion:materialQuestion,focusedLayers:focusedLayers,focusedQuestion:focusedQuestion,exportQuestion:exportQuestion,exportGuides:exportGuides,exportAnswer:exportAnswer};
});
