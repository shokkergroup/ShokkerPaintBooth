/* Shared live editor facts. No assignments, render calls or history writes. */
(function (root, factory) {
    var api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.SpbEditorCapabilities = api;
})(typeof window !== 'undefined' ? window : {}, function (W) {
    'use strict';
    function liveLayers() { try { return typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers) ? _psdLayers : []; } catch (_) { return []; } }
    function observedVisibility(layer) {
        var value=typeof layer.visible==='boolean'?layer.visible:typeof layer.hidden==='boolean'?!layer.hidden:null;
        if(Array.isArray(layer.groupChain)&&layer.groupChain.some(function(g){return g&&(g.visible===false||g.ownVisible===false);}))return false;
        return value;
    }
    function visibilityNote(value) { return value===false?' (hidden; no material contribution)':value===null?' (visibility unknown; material contribution unverified)':''; }
    function materialTarget(query) {
        var q=String(query||'').trim().replace(/[\u2018\u2019]/g,"'").replace(/\s*(?:[.!?]\s*)?(?:please\s+)?(?:explain only|advice only|do not change anything)\s*[.!?]*$/i,'').trim();
        if(q.length>1000||/(?:[.!?;]\s*|\b(?:and|then|also)\s+)(?:please\s+)?(?:make|set|apply|assign|change|remove|clear|turn|hide|show|recolou?r|paint|delete|undo|redo|run|scan|fix|enable|disable|render|export|move|resize|duplicate|add|save)\b/i.test(q))return null;
        var m=/^(?:what|which)\s+(?:layer\s+)?materials?\s+(?:is|are)\s+(?:on|assigned to|attached to|set on|used on)\s+(.+?)\s*[?.!]*$/i.exec(q)||/^(?:what|which)\s+(?:layer\s+)?materials?\s+(?:is|are)\s+(.+?)\s+using\s*[?.!]*$/i.exec(q)||/^what\s+(?:layer\s+)?material\s+does\s+(.+?)\s+have\s*[?.!]*$/i.exec(q);
        if(!m)return null;
        var target=m[1].trim().replace(/^(?:the|my)\s+/i,'').replace(/\s+layers?$/i,'').replace(/^["“”']|["“”']$/g,'').trim();
        if(!target||/^(?:selected|active|chosen)(?:\s+layers?)?$|^(?:each|all|my)\s+layers?$|^layers?$/i.test(target))return null;
        return target;
    }
    function namedMaterials(query,layers,api,installed) {
        var target=materialTarget(query);if(!target)return null;
        function norm(v){return String(v==null?'':v).trim().toLowerCase().replace(/\s*\/\s*/g,' / ').replace(/\s+/g,' ');}
        var label=norm(target),scan=layers.slice(0,1000),matches=scan.filter(function(l){return l&&(norm(l.id)===label||norm(l.name)===label||norm((l.groupName||l.group||'')+' / '+l.name)===label);});
        var rows=[],unresolved=[],bytes=0;
        matches.slice(0,12).forEach(function(l){
            var id=String(l.id==null?'':l.id),same=scan.filter(function(r){return r&&String(r.id==null?'':r.id)===id;});
            if(!id||id.length>120||same.length!==1||layers.length>1000){unresolved.push(text(id,120));return;}
            var state=installed?'none':'unavailable',rec=null,description=null;
            if(installed)try{var raw=api.get(l);if(raw){rec=typeof api.normalize==='function'?api.normalize(raw):null;if(!rec)throw Error('Unreadable material');state='assigned';description=text(api.describe(rec),300);}}catch(_){state='unreadable';}
            var row={id:text(id,120),name:text(l.name),group:text(l.groupName||l.group,300),visible:observedVisibility(l),locked:typeof l.locked==='boolean'?l.locked:null,state:state,description:description};
            var size=JSON.stringify(row).length;if(bytes+size>4000)return;bytes+=size;rows.push(row);
        });
        return {schema:'spb-named-layer-materials/1',read_only:true,target:text(target,300),matched_layers:matches.length,records:rows,unresolved_ids:unresolved,omitted_matches:Math.max(0,matches.length-rows.length-unresolved.length),unread_layers:Math.max(0,layers.length-1000),ambiguous:matches.length>1,scope:'Exact observed layer name, group path or ID in the current document only.',limits:'Stored Layer Material settings and observed visibility; not composited spec, rendered pixels or edit permission. No assignment can still receive spec from zones or imported spec. Names do not verify panel geometry.',actions:[]};
    }
    function namedMaterialAnswer(query) {
        if(!materialTarget(query)||(W.SpbCarReferenceAnswer&&W.SpbCarReferenceAnswer.namesCar(query)))return null;
        var live=read(query),m=live.layer_materials,n=m.named_layers,lines=[];
        if(!n)return null;
        if(!n.matched_layers)lines.push('I cannot find an exact loaded layer named “'+n.target+'”. Use its full group path or exact layer ID from this document; I have not substituted the selected layer.');
        else if(n.ambiguous)lines.push('That name matches '+n.matched_layers+' current layers. Their stored material settings are listed separately; specify the full group path or exact ID to choose one.');
        if(n.unresolved_ids.length||n.unread_layers||n.omitted_matches)lines.push('This bounded inventory is incomplete or contains unresolved identities. I cannot establish every matching layer.');
        if(!m.installed)lines.push('Layer Materials is unavailable on this page, so I cannot read its stored assignments.');
        else if(!m.enabled)lines.push('Layer Materials is currently disabled; any listed assignment is stored and does not establish an active contribution.');
        n.records.forEach(function(r){lines.push((r.group?r.group+' / ':'')+(r.name||'Unnamed layer')+(n.ambiguous?' ['+r.id+']':'')+': '+(r.state==='assigned'?r.description:r.state==='none'?'None (zones decide); no stored Layer Material assignment':r.state==='unreadable'?'stored material could not be read':'Layer Materials unavailable')+visibilityNote(r.visible)+(r.locked===true?' (locked)':'')+'.');});
        if(n.records.some(function(r){return r.state==='none';}))lines.push('No stored Layer Material assignment does not mean there is no spec: zones or imported spec can still supply it.');
        lines.push('These are stored settings in the current document, not a measurement of the final spec or rendered pixels. Nothing was selected, assigned, rendered or changed.');
        var body=lines.join('\n\n'),stamp=W.SpbConversationScope&&W.SpbConversationScope.stamp?W.SpbConversationScope.stamp():null;
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.live_editor_capabilities',live_context:true,editor_topic:'material',document_stamp:stamp,named_layer_materials:n,title:n.ambiguous?'Choose the exact material layer':'Named layer material settings',text:body,summary:body,how:[],actions:[],related:[],faq:null,shot:null}};
    }
    function patternSpecContract() {
        return {scope:'Primary pattern only',source:['paint-booth-5-api-render.js: zoneObj.pattern_spec_opacity','engine/pattern_material.py: apply_zone_pattern_spec'],
            behavior:'The primary pattern\'s spec amount blends its own material effect into the underlying spec map within the zone\'s coverage. 0% leaves that contribution off; 100% fully replaces the underlying RGB material channels there. Values between them blend the two. This does not switch off the underlying spec map or mean the whole car has no shine.',
            paint_and_alpha:'Pattern paint opacity and paint strength are separate controls. A painted checker can still be visible at spec amount 0%. The spec alpha lighting mask stays separate; these settings do not prove the rendered appearance.',
            limits:'Current renderer contract, not output verification. Secondary pattern amounts and calibrated UV geometry are not inspected.'};
    }
    function patternName(pid) { try { var rows=typeof PATTERNS!=='undefined'&&Array.isArray(PATTERNS)?PATTERNS:[],hit=rows.slice(0,5000).find(function(p){return p&&p.id===pid;});return hit&&hit.name?text(hit.name):null; } catch(_){return null;} }
    function patternControls() {
        var list=[],selected=-1;
        try { if(typeof zones!=='undefined'&&Array.isArray(zones))list=zones;if(typeof selectedZoneIndex!=='undefined'&&Number.isInteger(selectedZoneIndex))selected=selectedZoneIndex; } catch(_){}
        function number(v){return v!=null&&v!==''&&Number.isFinite(Number(v))?Number(v):null;}
        function id(z){return z&&typeof z.pattern==='object'?z.pattern&&z.pattern.id:z&&z.pattern;}
        var active=list.slice(0,1000).map(function(z,i){return {z:z,i:i};}).filter(function(r){return r.z&&id(r.z)&&id(r.z)!=='none';});
        active.sort(function(a,b){return (b.i===selected?1:0)-(a.i===selected?1:0);});
        var current=list[selected],records=active.slice(0,12).map(function(r){var z=r.z,p=typeof z.pattern==='object'?z.pattern:{},layers=Array.isArray(z.sourceLayers)?z.sourceLayers:z.sourceLayer?[z.sourceLayer]:[];
            return {zone_id:text(z.id,120),zone_name:text(z.name),selected:r.i===selected,muted:!!z.muted,locked:!!z.locked,pattern_id:text(id(z),120),pattern_name:patternName(id(z)),scale:number(p.scale!=null?p.scale:z.scale),rotation_degrees:number(p.rotation!=null?p.rotation:z.rotation),opacity_percent:number(p.opacity!=null?p.opacity:z.patternOpacity),paint_strength_multiplier:number(z.patternSpecMult),spec_amount_percent:number(z.patternSpecOpacity),paint_mode:text(z.patternPaintMode,40),source_layer_ids:layers.slice(0,8).map(function(v){return text(v,120);}),omitted_source_layers:Math.max(0,layers.length-8),secondary_pattern_count:Array.isArray(z.patternStack)?z.patternStack.length:0};
        });
        return {schema:'spb-pattern-controls/1',read_only:true,spec_amount_contract:patternSpecContract(),selected_zone:current?{id:text(current.id,120),name:text(current.name),pattern_id:id(current)&&id(current)!=='none'?text(id(current),120):null}:null,records:records,omitted_patterns:Math.max(0,active.length-records.length),unread_zones:Math.max(0,list.length-1000),limits:'Stored primary-pattern settings and selectors only. Missing numbers remain unknown; secondary patterns are counted, not inspected. Selection is a current UI fact, not edit approval or verified car geometry. No preview, rendering or changes performed.'};
    }
    function text(v, n) { return String(v == null ? '' : v).slice(0, n || 200); }
    // Historical IDs are evidence, never a target resolver for write tools.
    // Names/selectors come from the current document; the log has no deltas.
    function recentChange() {
        var scope;
        try { scope=W.SpbConversationScope&&W.SpbConversationScope.status(); } catch (_) {}
        if (W.SPB_CX3_OFF || !scope || !scope.available) return {available:false,reason:'Current-document conversation binding is unavailable. No historical target is inferred.'};
        var convo;
        try {
            if(!W.SpbConvo||!W.SpbConvo.on())return {available:false,reason:'Current-document change history is unavailable or disabled.'};
            convo=W.SpbConvo.view();
        } catch (_) { return {available:false,reason:'Current-document change history could not be read.'}; }
        if (!convo || !convo.last_change) return {available:false,reason:'No change is recorded in the current document conversation.'};
        var change=convo.last_change,list=[];
        try { if(typeof zones!=='undefined'&&Array.isArray(zones))list=zones; } catch (_) {}
        var layers=liveLayers(),zoneScan=list.slice(0,1000),layerScan=layers.slice(0,1000);
        var ids=Array.isArray(change.zone_ids)?change.zone_ids:[],seen=Object.create(null);
        var records=ids.slice(0,6).filter(function(id){if(typeof id!=='string'||!id||id.length>120||seen[id])return false;seen[id]=true;return true;}).map(function(id){
            var hits=zoneScan.filter(function(z){return z&&String(z.id)===id;});
            if(hits.length!==1)return {zone_id:id,resolution:hits.length?'ambiguous':list.length>1000?'not_found_in_bounded_inventory':'missing'};
            var z=hits[0],source=Array.isArray(z.sourceLayers)?z.sourceLayers:z.sourceLayer?[z.sourceLayer]:[],p=typeof z.pattern==='object'&&z.pattern?z.pattern:null,pid=p?p.id:z.pattern;
            function number(v){return v!=null&&v!==''&&Number.isFinite(Number(v))?Number(v):null;}
            var selectors=source.slice(0,8).map(function(lid){
                var matches=layerScan.filter(function(l){return l&&String(l.id)===String(lid);});
                if(matches.length!==1)return {layer_id:text(lid,120),resolution:matches.length?'ambiguous':layers.length>1000?'not_found_in_bounded_inventory':'missing'};
                return {layer_id:text(lid,120),resolution:'matched',current_name:text(matches[0].name,100),current_group:text(matches[0].groupName,100),current_visible:matches[0].visible!==false};
            });
            return {zone_id:id,resolution:'matched',current_name:text(z.name),current_muted:!!z.muted,current_locked:!!z.locked,current_source_layers:selectors,omitted_source_layers:Math.max(0,source.length-8),current_primary_pattern:pid&&pid!=='none'?{id:text(pid,120),name:patternName(pid),scale:number(p&&p.scale!=null?p.scale:z.scale)}:null};
        });
        var used=0,exposed=records.length;
        records=records.filter(function(record){var bytes=JSON.stringify(record).length;if(used+bytes>5000)return false;used+=bytes;return true;});
        return {schema:'spb-recent-change/1',available:true,read_only:true,document_epoch:scope.epoch,record:{turn:text(change.turn,120),request:text(change.said,200),target_description:text(change.targets,400),marked_undone:change.undone===true,undo_id:change.undo_id==null?null:text(change.undo_id,120)},zones:records,omitted_zone_records:exposed-records.length,
            omitted_exposed_zone_ids:Math.max(0,ids.length-6),unread_zones:Math.max(0,list.length-1000),unread_layers:Math.max(0,layers.length-1000),
            limits:'At most six zone IDs exposed by the current conversation view. Names, layer selectors and pattern scale are current observations, not historical before/after values. Missing or ambiguous IDs are unresolved. The record does not verify rendered pixels, calibrated UV geometry, complete affected scope or edit approval. Saved design discussion is not live change evidence.'};
    }
    function changeAnswer(query) {
        if(W.SPB_CX3_OFF)return null;
        var q=String(query||'').trim().replace(/[\u2018\u2019]/g,"'").replace(/\s*(?:[.!?]\s*)?(?:please\s+)?(?:explain only|advice only|do not change anything)\s*[.!?]*$/i,'').trim();
        if(!/^(?:(?:what|which zone|which zones) did (?:you|i|we) (?:just |last )?change|what (?:was|is) (?:the |my |your )?(?:last|latest|most recent) (?:edit|change)|what did (?:that|the last edit|the latest edit) (?:change|affect)|which zones? did (?:that|the last edit|the latest edit) affect|was (?:that|the last edit|the latest edit) undone|did (?:i|you|we) undo (?:that|the last edit|the latest edit))\s*[.!?]*$/i.test(q))return null;
        var evidence=recentChange(),body;
        if(!evidence.available)body=evidence.reason+' I cannot reconstruct a previous edit or its values from the saved design discussion.';
        else {
            var r=evidence.record,parts=['The latest recorded edit'+(r.request?' was “'+r.request.replace(/[.!?]+$/,'')+'”.':'.')+(r.marked_undone?' It is marked undone.':' It is not marked undone in the conversation record.')];
            evidence.zones.forEach(function(z){
                if(z.resolution!=='matched'){parts.push('A recorded zone is '+z.resolution.replace(/_/g,' ')+' in the current inventory; I cannot name its target.');return;}
                var line='That record refers to the current '+(z.current_name?'“'+z.current_name+'” zone':'unnamed zone')+'.';
                if(z.current_muted||z.current_locked)line+=' It is currently '+[z.current_muted?'muted':null,z.current_locked?'locked':null].filter(Boolean).join(' and ')+'.';
                if(z.current_source_layers.length)line+=' It is currently restricted to '+z.current_source_layers.map(function(l){return l.resolution==='matched'?(l.current_group?l.current_group+' / ':'')+(l.current_name||'an unnamed layer')+(l.current_visible?'':' (currently hidden)'):'an unresolved layer ('+l.resolution.replace(/_/g,' ')+')';}).join('; ')+(z.omitted_source_layers?' (more selectors omitted)':'')+'.';
                if(z.current_primary_pattern)line+=' Current primary pattern: '+(z.current_primary_pattern.name||'an unnamed pattern')+(z.current_primary_pattern.scale!=null?', scale '+z.current_primary_pattern.scale:'; scale is unknown')+'.';
                parts.push(line);
            });
            if(!evidence.zones.length)parts.push(r.target_description?'The recorded target description is “'+r.target_description+'”; no exact zone IDs are exposed.':'The record exposes no exact zone IDs or target description.');
            if(evidence.omitted_zone_records||evidence.omitted_exposed_zone_ids)parts.push('Further exposed zone records were omitted from this bounded answer.');
            parts.push('These names and settings describe the current document. The record does not supply before/after values, verify rendered pixels or establish car-panel geometry.');body=parts.join('\n\n');
        }
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.live_editor_capabilities',live_context:true,editor_topic:'recent_change',recent_change:evidence,title:'Latest recorded edit',text:body,summary:body,how:[],actions:[],related:[],faq:null,shot:null}};
    }
    function kits() {
        function menuControl(attribute, name) {
            try {
                var button = W.document.querySelector('#spbSymMenu ['+attribute+'], #spbNumMenu ['+attribute+'], #spbSponsorMenu ['+attribute+']');
                var menu = button && button.closest('details'), heading = menu && menu.querySelector('summary');
                var label = heading && heading.textContent.replace(/[\s\u25be]+/g,' ').trim();
                if (/^(?:Car|Symmetry|Sponsors|Numbers)$/.test(label)) return label+' > '+name;
            } catch (_) {}
            return null;
        }
        function availability(core, ui, dependency) {
            var installed = !!(core && typeof core.begin === 'function' && typeof core.measure === 'function');
            var r = {installed:installed,enabled:null,dialog_available:!!(ui && typeof ui.open === 'function'),placement_verified:false};
            try { r.enabled = installed && dependency && typeof core.off === 'function' ? !core.off() : installed && dependency ? null : false; } catch (_) {}
            return r;
        }
        var sponsor = availability(W.SpbRevSponsor,W.SpbRevSponsorUI,!!W.SpbRevSponsorClean);
        var numbers = availability(W.SpbRevNumbers,W.SpbRevNumbersUI,true);
        sponsor.editor_control = menuControl('data-skit','Sponsor Kit');
        numbers.editor_control = menuControl('data-nkit','Number Kit');
        return {sponsor:sponsor,numbers:numbers,limits:'Placement has not been measured or verified by this answer. Automatic locations depend on this paint\'s car map and measured shape. A catalog match is not verified UV geometry. No kit was opened, measured, added or edited.'};
    }
    function diagnostics() {
        var doctor = W.SPBRevDoctor, seam = W.SpbRevSeam;
        var d = {installed:!!doctor,enabled:null,editor_control:'Material > Spec Doctor (also under Spec Tools when present).',
            checks:['chrome over near-black paint','clearcoat settings','decals inheriting body chrome','flat spec','paint/spec alignment','mip shimmer'],
            limits:'Availability is not a diagnosis. Run a fresh check for this project, inspect each finding and its overlay before choosing a fix. No scan, fix or render was run for this answer. A clean check is not proof of every pixel or an in-simulator result.'};
        try { d.enabled = !!doctor && (typeof doctor.off === 'function' ? !doctor.off() : doctor.off === true ? false : null); } catch (_) {}
        var e = {installed:!!seam,enabled:null,on:null,extension_px:null,error:null,
            editor_control:'Settings > Options > Bleed Paint Past Panel Edges.',
            behavior:'When enabled and panel outlines can be read, render-time Edge Bleed extends panel-edge paint and spec into nearby gaps to reduce seam fringes at lower texture resolutions. It does not align a stripe across separate panels.',
            limits:'Requires usable template outlines. Availability and the switch state do not prove successful panel detection or corrected output. No setting, panel scan or render was changed for this answer.'};
        try {
            if (seam && typeof seam.off === 'function') e.enabled = !seam.off();
            if (seam && typeof seam.isOn === 'function') e.on = !!seam.isOn();
            if (seam && typeof seam.px === 'function') { var px = seam.px(); if (Number.isFinite(px) && px >= 1 && px <= 64) e.extension_px = px; }
            // status() reads cached state only. Do not call ensure/renderField/setOn.
            if (seam && typeof seam.status === 'function') { var status = seam.status(); e.error = status && status.err ? text(status.err,300) : null; }
        } catch (_) { e.on = null; e.error = 'Current Edge Bleed status could not be read.'; }
        return {spec_doctor:d,edge_bleed:e};
    }
    function exportGuides() {
        var policy={known:typeof W._nuqRenderComposite==='function'&&typeof W._nuqOff==='function',enabled:false};
        try{policy.enabled=policy.known&&!W._nuqOff();}catch(_){policy.known=false;}
        var report=W.SpbTemplateLayers&&W.SpbTemplateLayers.exportGuides?W.SpbTemplateLayers.exportGuides(W._psdLayers||[]):null;
        return {report:report,filter:policy};
    }
    function selectedMaterials(layers, api, installed) {
        var set=W._selectedLayerIds, ids=[], total=0;
        if (!set || typeof set.forEach!=='function') return {known:false,records:[],unresolved_ids:[],omitted:0};
        set.forEach(function(id){total++;if(ids.length<12)ids.push(String(id));});
        var rows=[], unresolved=[], scan=layers.slice(0,1000);
        ids.forEach(function(id){
            var matches=scan.filter(function(l){return l&&String(l.id)===id;});
            if(matches.length!==1||layers.length>1000){unresolved.push(text(id,120));return;}
            var l=matches[0], rec=null, state=installed?'none':'unavailable', description=null;
            if(installed)try{
                var raw=api.get(l);
                if(raw){rec=typeof api.normalize==='function'?api.normalize(raw):null;if(!rec)throw Error('Unreadable material');state='assigned';description=text(api.describe(rec),500);}
            }catch(_){state='unreadable';}
            rows.push({id:text(id,120),name:text(l.name),group:text(l.groupName,300),visible:observedVisibility(l),locked:!!l.locked,state:state,description:description,material:rec?JSON.parse(JSON.stringify(rec)):null});
        });
        return {known:true,records:rows,unresolved_ids:unresolved,omitted:Math.max(0,total-ids.length),scope:'Current selected layer IDs only; stored material is not rendered output or edit authority.'};
    }
    function read(query) {
        var api = W.SPBRevLayerMat, layers = liveLayers(), installed = !!(api && typeof api.get === 'function' && typeof api.describe === 'function'), enabled = false;
        try { enabled = installed && typeof api.off === 'function' && !api.off(); } catch (_) {}
        var assigned = [], errors = [], total = 0;
        if (installed) layers.forEach(function (l) {
            try {
                var rec = api.get(l);
                if (!rec) return;
                rec = typeof api.normalize === 'function' ? api.normalize(rec) : null;
                if (!rec) throw new Error('Unreadable stored material');
                total++;
                if (assigned.length >= 40) return;
                assigned.push({id:text(l.id,120), name:text(l.name), group:text(l.groupName,300), visible:observedVisibility(l),
                    description:text(api.describe(rec),500), material:JSON.parse(JSON.stringify(rec))});
            } catch (_) { errors.push(text(l.id,120)); }
        });
        var presets = installed && Array.isArray(api.PRESETS) ? api.PRESETS.slice(0,30).map(function (p) {
            return {id:text(p.id,80), name:text(p.name), kind:text(p.kind,40), finish_id:p.finishId ? text(p.finishId,120) : undefined};
        }) : [];
        var filtered = false, filterKnown = typeof W._nuqPreviewComposite === 'function' && typeof W._nuqOff === 'function';
        try { filtered = filterKnown && !W._nuqOff(); } catch (_) { filterKnown = false; }
        var diagnostic = diagnostics();
        return {schema:'spb-editor-capabilities/1', read_only:true,recent_change:recentChange(),pattern_controls:patternControls(),export_guides:exportGuides(),panel_locations:W.SpbPanelLocation ? W.SpbPanelLocation.read() : null,kits:kits(),spec_doctor:diagnostic.spec_doctor,edge_bleed:diagnostic.edge_bleed,
            layer_materials:{installed:installed,enabled:enabled,layer_count:layers.length,assigned_count:total,assignments:assigned,selection:selectedMaterials(layers,api,installed),named_layers:namedMaterials(query,layers,api,installed),
                omitted_assignments:Math.max(0,total-assigned.length),unreadable_layer_ids:errors,presets:presets,
                editor_control:'Select a layer, then open its Material row or material chip.',
                behavior:'Material coverage follows the layer artwork, opacity, masks and clipping. Hidden layers contribute no material; higher layers take precedence. Keep Art Colour preserves paint colour for finish-based materials. Edge and Vinyl Edge Lip are optional.',
                limits:'These are current stored assignments and editor availability, not rendered-pixel proof or an advertised MCP write tool. Check the current tool schema before promising to apply a material. Source alpha is coverage; spec-map alpha controls lighting.'},
            preview:{guide_filter_known:filterKnown,guide_filter_enabled:filtered,
                contract:filtered ? 'Live Preview is set to hide the Turn Off Before Exporting group. Source and saved layers keep those guides. If SPB cannot build that preview, it can show Source as a fallback.' : 'Guide filtering is disabled or unavailable; guides may appear in the preview.',
                limits:'Live Preview does not confirm a finished full-resolution render or export. Compare previews from the same project state when checking a change.'}};
    }
    function previousFrom(state, log) {
        if (!state || !state.answer || !Array.isArray(log)) return null;
        // The visible card can outlive its conversation turn. Reuse only the
        // card answering the immediately preceding buyer message.
        for (var i = log.length - 1; i >= Math.max(0, log.length - 20); i--) {
            if (log[i] && log[i].role === 'user') return String(log[i].text || '') === String(state.text || '') ? state.answer : null;
        }
        return null;
    }
    function patternEnvelope(body, selected, record, needsTarget) {
        var stamp=W.SpbConversationScope&&W.SpbConversationScope.stamp?W.SpbConversationScope.stamp():null;
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.live_editor_capabilities',live_context:true,editor_topic:'pattern',pattern_zone_id:selected&&selected.id,pattern_id:record&&record.pattern_id,needs_pattern_target:!!needsTarget,document_stamp:stamp,title:needsTarget?'Choose the pattern again':'Selected pattern settings',text:body,summary:body,how:[],actions:[],related:[],faq:null,shot:null}};
    }
    function patternAnswer(query, previous) {
        if (W.SPB_CX3_OFF) return null;
        var q=String(query||'').trim().replace(/[\u2018\u2019]/g,"'"),prior=previous&&(previous.answer||previous);
        var refinementFollow=/^(?:and\s+)?(?:what if i go (?:finer|coarser)|if i go (?:finer|coarser)|would (?:finer|coarser) help|what about (?:finer|coarser)|if i make it (?:finer|coarser))\s*[?.!]*$/i.test(q);
        // Fully consumed question tied to the immediately preceding live card.
        var settingFollow=/^(?:and\s+)?(?:what does|what is|explain|tell me about)\s+(?:the\s+)?(?:spec amount|paint strength|rotation|opacity)(?:\s+(?:of\s+)?\d+(?:\.\d+)?\s*%?)?(?:\s+mean)?\s*[?.!]*(?:\s*(?:please\s+)?(?:explain only|advice only|do not change anything)\s*[?.!]*)?$/i.test(q);
        var follow=refinementFollow||settingFollow;
        if (!follow && (!/^(?:what|which|how|why|is|are|does|do|would|should|could|can|explain|tell me)\b/i.test(q) || !/\b(?:patterns?|checkers?|checkerboard|texture)\b/i.test(q) || !/\b(?:settings?|scale|size|big|large|small|fine|finer|coarse|coarser|repeat|rotation|opacity|strength|amount|layers?|use|have|selected|current|mean)\b/i.test(q))) return null;
        if (/^(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:apply|make|set|change|paint|recolou?r|colou?r|add|remove|adjust|edit|render|undo|redo|hide|show|place|resize|move|duplicate|delete|open|export|enable|disable|scan|fix|run|clear|turn|assign|use)\b|(?:[.!?;]\s*|\b(?:and|then|also)\s+)(?:please\s+)?(?:apply|make|set|change|paint|recolou?r|colou?r|add|remove|adjust|edit|render|undo|redo|hide|show|place|resize|move|duplicate|delete|open|export|enable|disable|scan|fix|run|clear|turn|assign|use)\b/i.test(q)) return null;
        if (/\b(?:hood|roof|doors?|sides?|trunk|spoiler|fenders?|front|rear)\b/i.test(q) || (W.SpbCarReferenceAnswer&&W.SpbCarReferenceAnswer.namesCar&&W.SpbCarReferenceAnswer.namesCar(q))) return null;
        var controls=patternControls(),selected=controls.selected_zone,r=controls.records.filter(function(x){return selected&&x.zone_id===selected.id&&x.selected;})[0];
        if (follow) {
            if (!prior||prior.editor_topic!=='pattern') return null;
            var reason=prior.needs_pattern_target?'Choose a zone with the pattern you mean, then ask about that selected pattern.':!W.SpbConversationScope||!W.SpbConversationScope.current(prior.document_stamp)?'The open paint changed since that answer. Ask about the pattern in your current paint so I can read it again.':!selected||prior.pattern_zone_id!==selected.id?'The selected zone changed since that answer.'+ (selected?' You are now on '+selected.name+(selected.pattern_id?'.':' which has no primary pattern.'):' No zone is selected.')+' Select the pattern zone you mean and ask again.':!r||prior.pattern_id!==r.pattern_id?'The selected pattern changed since that answer. Ask about its current settings before we compare finer or coarser.':null;
            if (reason) return patternEnvelope(reason+' Nothing has been changed or queued.',null,null,true);
        }
        var lines=[],all=/\bsettings?\b/i.test(q),scale=all||refinementFollow||/\b(?:scale|size|big|large|small|fine|finer|coarse|coarser|repeat)\b/i.test(q);
        if (!selected) lines.push('Select a zone first so I can read its existing pattern. I will not choose a different zone for you.');
        else if (!selected.pattern_id) lines.push('The selected zone '+selected.name+' has no primary pattern. Base material scale is a different control; I have not added a pattern.');
        else if (!r) lines.push('The selected pattern settings could not be read. I will not substitute another zone or guess default values.');
        else {
            lines.push('Selected zone: '+r.zone_name+'. Pattern: '+(r.pattern_name||'existing pattern (catalog name unavailable)')+(r.muted?' (zone is muted)':r.locked?' (zone is locked)':'')+'.');
            if (scale) {
                lines.push('Pattern scale: '+(r.scale===null?'unreadable':String(r.scale))+'. Smaller values repeat the pattern more; larger values zoom it in. This is separate from base-material scale.');
                if (/\bcoarser\b/i.test(q)) lines.push('Coarser makes the marks larger. For bold checks that can help; going too far can compete with the number. Review the preview before keeping it.');
                else if (/\bfiner\b/i.test(q)) lines.push('Finer gives more, smaller repetitions. That can quiet the background around numbers, but very fine checks may read as a texture at a distance.');
                else lines.push('Scale does not give one universal mark size in pixels. Whether it is too large depends on this pattern and the actual preview; these settings alone are not a visual assessment.');
            }
            function setting(label,value,suffix){lines.push(label+': '+(value===null?'unreadable':String(value)+(suffix||''))+'.');}
            if (all||/\brotation\b/i.test(q)) setting('Pattern rotation',r.rotation_degrees,' degrees');
            if (all||/\bopacity\b/i.test(q)) setting('Pattern opacity',r.opacity_percent,'%');
            if (all||/\b(?:strength|spec|amount)\b/i.test(q)) {setting('Pattern paint strength multiplier',r.paint_strength_multiplier);setting('Pattern spec amount',r.spec_amount_percent,'%');lines.push('These are pattern controls, not a measurement of the base material or the final spec map.');
                if (/\b(?:spec|amount)\b/i.test(q)) {
                    lines.push(controls.spec_amount_contract.behavior);
                    lines.push(controls.spec_amount_contract.paint_and_alpha);
                }
            }
            var names=r.source_layer_ids.map(function(id){var hits=liveLayers().filter(function(l){return l&&String(l.id)===id;});return hits.length===1?text(hits[0].name):'unresolved layer';});
            lines.push(names.length?'Stored layer restriction: '+names.join(', ')+(r.omitted_source_layers?' and '+r.omitted_source_layers+' more':'')+'.':'No stored layer restriction. Colour or region selectors may still limit the zone; this does not prove whole-car coverage.');
            if(r.secondary_pattern_count)lines.push(r.secondary_pattern_count+' additional pattern(s) are present but their settings are not inspected here.');
        }
        lines.push('Nothing has been changed or queued.');
        return patternEnvelope(lines.join('\n\n'),selected,r,false);
    }
    function answer(query, previous) {
        var q = String(query || '').trim();
        var change=changeAnswer(q); if(change)return change;
        var pattern=patternAnswer(q,previous); if(pattern)return pattern;
        var panelAnswer = W.SpbPanelLocation && W.SpbPanelLocation.answer(q);
        if (panelAnswer) return panelAnswer;
        var prior = previous && (previous.answer || previous);
        if (/^(?:which (?:of (?:those|them) )?(?:are|is) (?:still )?(?:on|visible)|are (?:they|those) (?:already )?hidden)\s*[?.!]*$/i.test(q)) {
            if(!prior||prior.id!=='assistant.live_export_guides'||!W.SpbConversationScope||!W.SpbConversationScope.current(prior.document_stamp))return null;
            q='Which export guide layers are visible?';
        }
        var topicNames = {doctor:'Spec Doctor',seam:'Edge Bleed',material:'Layer Materials',sponsor:'Sponsor Kit',numbers:'Number Kit'};
        if (/^(?:where (?:is|do i find) (?:that|it)|how do i (?:find|open|use) (?:that|it))\s*[?.!]*$/i.test(q)) {
            if (!prior || prior.id !== 'assistant.live_editor_capabilities' || !topicNames[prior.editor_topic] || !W.SpbConversationScope || prior.document_stamp == null || !W.SpbConversationScope.current(prior.document_stamp)) return null;
            q = q.replace(/\b(?:that|it)\b/i,topicNames[prior.editor_topic]);
        }
        if (!/^(?:what|which|where|how|why|can|does|do|is|are|explain|tell me)\b/i.test(q)) return null;
        if (/^(?:can|could|would|will)\s+you\s+(?:add|place|insert|replace|resize|move|duplicate|delete|open)\b/i.test(q) || /(?:[.!?;]\s*|\b(?:and|then)\s+)(?:please\s+)?(?:add|place|insert|replace|resize|move|duplicate|open)\b/i.test(q)) return null;
        // Mixed requests still belong to the shared intent/router, not a factual shortcut.
        if (/^(?:can|could|would|will)\s+you\s+(?:apply|assign|make|set|change|remove|clear|turn|hide|show|paint|undo|redo|run|scan|fix|enable|disable|render|export)\b/i.test(q) || /(?:[.!?;]\s*|\b(?:and|then)\s+)(?:please\s+)?(?:make|set|apply|assign|change|remove|clear|turn|hide|show|recolou?r|paint|delete|undo|redo|run|scan|fix|enable|disable|render|export)\b/i.test(q)) return null;
        if (/^can\s+you\s+(?:keep|leave)\b/i.test(q)) return null;
        var named=namedMaterialAnswer(q);if(named)return named;
        var connectionQuestion = /\b(?:chatgpt|codex|offline helper|ai helper)\b/i.test(q) && /\b(?:api|subscription|credits?|plan|internet|connect|billing|allowance|limits?|resets?)\b/i.test(q);
        if(connectionQuestion){
            // Explain setup/billing boundaries; this does not inspect credentials,
            // establish entitlement, connect a client or consume a reset.
            if(/^(?:can|could|would|will)\s+you\s+(?:connect|sign|use|spend|buy|activate|reset)\b/i.test(q)||/(?:[.!?;]\s*|\b(?:and|then)\s+)(?:please\s+)?(?:connect|sign in|use my|spend|buy|activate|reset)\b/i.test(q))return null;
            var connectionText = 'Offline Helper is built in and works without an AI subscription or model API key. It can explain SPB controls and supported workflows while the online assistant is unavailable.'+
                '\n\nFor the ChatGPT connection, use installed Codex signed in with ChatGPT to use eligible plan allowance. API-key sign-in uses separate API billing. Your plan limits still apply. A successful login or MCP setup does not prove that the selected model works or that the assistant is actively listening.'+
                '\n\nIf online usage is unavailable, keep your question and switch to Offline Helper. This built-in answer cannot inspect account allowance, confirm model access, spend credits or apply a banked reset. It has not connected or changed anything.';
            return {cls:'ANSWER',hits:[],answer:{id:'assistant.subscription_connection',live_context:false,title:'AI connection and subscription usage',text:connectionText,summary:connectionText,how:[],actions:[],related:[],faq:null,shot:null,
                sources:[{title:'OpenAI authentication',url:'https://learn.chatgpt.com/docs/auth'},{title:'Codex non-interactive mode',url:'https://learn.chatgpt.com/docs/non-interactive-mode'}]}};
        }
        var selectedMaterial = /\b(?:selected|active|chosen)\s+layers?\b/i.test(q)&&/\bmaterial\b/i.test(q);
        var separateMaterial = !/^why\b/i.test(q)&&!/^can\s+you\s+(?:keep|leave)\b/i.test(q)&&/\b(?:sponsors?|logos?|decals?|numbers?|artwork)\b/i.test(q)&&/\b(?:body|background)\b/i.test(q)&&/\b(?:matte|chrome|gloss|satin|metallic)\b/i.test(q)&&/\b(?:keep|stays?|while|without|separate|different|independent)\b/i.test(q);
        var material = selectedMaterial || separateMaterial || /\blayer materials?\b|\bmaterials?\b.{0,35}\b(?:assigned|attached|my layers?|each layer|follow)\b|\b(?:my layers?|each layer)\b.{0,35}\bmaterials?\b/i.test(q);
        if(W.SpbTemplateLayers&&W.SpbTemplateLayers.exportQuestion&&W.SpbTemplateLayers.exportQuestion(q)&&!(W.SpbCarReferenceAnswer&&W.SpbCarReferenceAnswer.namesCar(q))){
            var eg=exportGuides(),ea=W.SpbTemplateLayers.exportAnswer(q,eg.report,eg.filter);
            if(ea){ea.answer.document_stamp=W.SpbConversationScope?W.SpbConversationScope.stamp():null;return ea;}
        }
        var preview = /\b(?:source|live preview)\b/i.test(q) && /\b(?:guides?|mask|wire|mandatory|different|differ|missing|disappear)\b/i.test(q);
        var doctor = /\bspec doctor\b/i.test(q) || (!separateMaterial && /\b(?:numbers?|sponsors?|decals?)\b.{0,35}\b(?:chrome|metallic|shiny)\b|\b(?:spec|paint)\b.{0,25}\b(?:shimmer|halo)\b/i.test(q));
        var seam = /\bedge bleed\b|\bbleed paint past panel edges\b|\b(?:seams?|panel edges?)\b.{0,35}\b(?:fringes?|gaps?|bleed)\b|\b(?:fringes?|gaps?)\b.{0,35}\b(?:seams?|panel edges?)\b/i.test(q);
        var sponsor = /\bsponsor kit\b/i.test(q) || /^how (?:do|can) i (?:add|place|put)\b.{0,45}\b(?:sponsors?|logos?)\b.{0,35}\b(?:doors?|hood|car)\b/i.test(q);
        var numbers = /\bnumber kit\b/i.test(q) || /^how (?:do|can) i (?:add|place|put)\b.{0,45}\b(?:car )?numbers?\b.{0,35}\b(?:doors?|roof|car)\b/i.test(q);
        if (!material && !preview && !doctor && !seam && !sponsor && !numbers) return null;
        var s = read(), m = s.layer_materials, paragraphs = [];
        var location = /^(?:where|how do i (?:find|open))\b/i.test(q);
        if (sponsor || numbers) {
            [['sponsor',sponsor,'Sponsor Kit'],['numbers',numbers,'Number Kit']].forEach(function (item) {
                if (!item[1]) return;
                var k = s.kits[item[0]], available = k.installed && k.enabled === true && k.dialog_available;
                paragraphs.push(!k.installed ? item[2]+' is unavailable on this page.' : k.enabled === false ? item[2]+' is installed but disabled or missing a required component.' : available && k.editor_control ? 'Open '+k.editor_control+'.' : available ? item[2]+' is available, but its current menu location could not be read.' : item[2]+' is installed, but its dialog availability could not be confirmed.');
                if (!available || location) return;
                if (item[0] === 'sponsor') paragraphs.push('Choose File or Use Selected Layer to supply the logo. Compare Before and After when using Remove Box; Clear Inside can also remove matching areas inside letters, so inspect those details. Choose the available locations, size and material, then inspect the live placements before Add Sponsor Kit.');
                else paragraphs.push('Enter the car number, choose its font, colours, outlines and optional panel, then select the available Left Door, Right Door and Roof locations. Review existing numbers before adding another set. Inspect the live placements before committing; Add Number Kit creates a new kit, while an existing kit opens for editing.');
                paragraphs.push('Dialog changes preview as real layers. Cancel or Esc cancels that dialog session; a committed kit is one Undo step. Check every placement for orientation, overlap and readability.');
            });
            if (!location) paragraphs.push('If a location is unavailable, check the kit\'s placement message: the current template may lack that part or a measured shape. A car-catalog match is not verified UV geometry. This answer does not check placement or change your paint.');
        }
        if (material) {
            paragraphs.push(!m.installed ? 'Layer Materials is unavailable on this page.' : !m.enabled ? 'Layer Materials is installed but currently disabled on this page.' : 'Layer Materials is available in this editor. '+m.editor_control);
            if(selectedMaterial && m.selection){
                var selection=m.selection;
                if(!selection.known)paragraphs.push('The selected layer could not be read. Select the intended artwork layer and check its Material row.');
                else if(!selection.records.length&&!selection.unresolved_ids.length)paragraphs.push('No layer is selected. Select the intended artwork layer first.');
                else paragraphs.push(selection.records.map(function(a){return (a.group?a.group+' / ':'')+a.name+': '+(a.state==='assigned'?a.description:a.state==='none'?'None (zones decide); no stored Layer Material assignment':a.state==='unreadable'?'material could not be read':'Layer Materials unavailable')+visibilityNote(a.visible)+(a.locked?' (locked)':'');}).join('; ')+'.');
                if(selection.unresolved_ids.length||selection.omitted)paragraphs.push('Some selected layers could not be uniquely read; this selection inventory is incomplete.');
                if(selection.records.some(function(a){return a.state==='none';}))paragraphs.push('No Layer Material assignment does not mean there is no spec: zones or imported spec can still supply it.');
            }
            if(separateMaterial && m.enabled){
                paragraphs.push('Give the actual sponsor, logo or number layer its own Material setting and leave the body settings alone. Matte Vinyl supplies a matte material; Chrome Foil supplies chrome. Choose the preset matching the artwork you want.');
                paragraphs.push('Spec presets change material channels without repainting the artwork. An SPB finish can also change paint colour: use Keep Art Colour when you want to preserve it. Coverage follows the layer artwork, masks, opacity and clipping; hidden layers contribute none and higher layers take precedence.');
                paragraphs.push('This does not confirm that the body is currently chrome or that a rendered result will match your intent. Check the preview and final render after a change.');
            }
            if (m.installed && !location && !selectedMaterial && !separateMaterial) {
                paragraphs.push(m.behavior);
                paragraphs.push(m.layer_count ? (m.assigned_count ? m.assigned_count+' layer(s) have readable stored material assignments: '+m.assignments.slice(0,12).map(function (a) { return (a.group ? a.group+' / ' : '')+a.name+' ['+a.id+']: '+a.description+visibilityNote(a.visible); }).join('; ')+(m.assigned_count>12 ? '. Only the first 12 are listed here.' : '.') : (m.unreadable_layer_ids.length ? 'No valid material assignments could be read; the inventory is incomplete.' : 'None of the '+m.layer_count+' loaded layers has a stored Layer Material assignment. This does not mean the car has no spec map: zones or imported spec layers can still supply it.')) : 'No live layers are loaded to inspect.');
                if (m.unreadable_layer_ids.length) paragraphs.push('Some layer assignments could not be read; this inventory is incomplete.');
                paragraphs.push('Available presets: '+m.presets.map(function (p) { return p.name; }).join(', ')+'.');
            }
            paragraphs.push('This answer makes no changes. It reports stored settings, not a verified rendered result.');
        }
        if (preview) paragraphs.push(s.preview.contract+' '+s.preview.limits);
        if (doctor) {
            var d = s.spec_doctor;
            if (/\b(?:numbers?|sponsors?|decals?)\b/i.test(q)) paragraphs.push('The artwork may have its own material, or be picking up the body\'s shine underneath. Select the affected layer and check its Material setting first.');
            paragraphs.push(!d.installed ? 'Spec Doctor is unavailable on this page.' : d.enabled === false ? 'Spec Doctor is installed but currently disabled on this page.' : d.enabled === true ? 'Spec Doctor is available. Open '+d.editor_control : 'Spec Doctor is installed, but its current availability could not be confirmed.');
            if (location) paragraphs.push('No scan or fix was run for this answer.');
            else if (/\b(?:numbers?|sponsors?|decals?)\b/i.test(q)) paragraphs.push('Run a fresh check, review the highlighted artwork, then choose a fix if it matches the problem. No scan or fix was run for this answer; the symptom alone does not identify the cause.');
            else paragraphs.push('It checks '+d.checks.join(', ')+'. Run a fresh check and review its highlighted areas before choosing a fix. No scan or fix was run for this answer.');
        }
        if (seam) {
            var e = s.edge_bleed;
            paragraphs.push(!e.installed ? 'Edge Bleed is unavailable on this page.' : e.enabled === false ? 'Edge Bleed is installed but currently disabled on this page.' : 'Edge Bleed is installed. '+e.editor_control+' Its switch is '+(e.on === null ? 'unreadable' : e.on ? 'on' : 'off')+(e.extension_px === null ? '.' : '; extension: '+e.extension_px+' pixels.'));
            paragraphs.push(e.behavior+' '+e.limits);
            if (e.error) paragraphs.push('The latest cached status reports: '+e.error+' Check the current project before relying on that result.');
        }
        var body = paragraphs.join('\n\n');
        var topic = (+material + +doctor + +seam + +sponsor + +numbers) === 1 && !preview ? (material ? 'material' : doctor ? 'doctor' : seam ? 'seam' : sponsor ? 'sponsor' : 'numbers') : null;
        var stamp = W.SpbConversationScope && W.SpbConversationScope.stamp ? W.SpbConversationScope.stamp() : null;
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.live_editor_capabilities',live_context:true,editor_topic:topic,document_stamp:stamp,title:sponsor && numbers ? 'Sponsor and Number Kits' : sponsor ? 'Sponsor Kit guidance' : numbers ? 'Number Kit guidance' : material ? 'Layer Materials in this project' : doctor && seam ? 'Spec Doctor and Edge Bleed' : doctor ? (location ? 'Find Spec Doctor' : 'Check unexpected shine or spec artifacts') : seam ? 'Help with panel-edge fringes' : 'Source and Live Preview',text:body,summary:body,how:[],actions:[],related:[],faq:null,shot:null}};
    }
    return {read:read,answer:answer,previousFrom:previousFrom};
});
