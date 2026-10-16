/* CX3 2026-10-09 (CODEX-INTEGRATE-2): production copy of mcp/chatgpt/native-layer-colour.js (sha256 fbe8d9e31d0f0097, body unchanged).
   window.SpbNativeLayerColour whole-layer colour through the app's own non-destructive layer colour overlay (so grey control masks and layers above stay untouched); used by the spb_edit_layer colour field.
   Action-free helper: it never paints by itself. Callers are guarded by window.SPB_CX3_OFF (kill switch).
   Origin: Codex request REQUESTS_FOR_CLAUDE.md 'Shared layer intelligence' / 'Shared native-colour and Undo delta'. */
(function(W){
    'use strict';
    function hex(value){return typeof value==='string'&&/^#[0-9a-f]{6}$/i.test(value)?value.toLowerCase():null;}
    function group(l){return String(l.groupName||l.group||'');}
    function overlay(l){var c=l&&l.effects&&l.effects.colorOverlay;return c?{enabled:!!c.enabled,colour:hex(c.color),opacity:Math.round(Number(c.opacity||0)*100),blend:String(c.blendMode||'source-over')}:null;}
    function paintLayer(l){var c=W.SpbTemplateLayers&&W.SpbTemplateLayers.classify(l);return !(c&&(c.kind==='spec'||c.kind==='alpha'))&&!/^(?:custom\s+)?spec\s+map(?:\s*\/|$)/i.test(group(l));}
    function patch(colour,opacity){
        var h=hex(colour),v=opacity==null?100:opacity;
        if(!h)return {error:'Choose a six-digit hex colour for this layer.'};
        if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>100)return {error:'Layer colour amount must be from 0 to 100.'};
        return {colour:h,colourOpacity:v};
    }
    function queue(planned,env){
        if(!planned||planned.kind!=='ops'||!(planned.ops||[]).length)return null;
        var ops=planned.ops,full=ops.filter(function(o){return o&&o.target&&o.target.kind==='layer'&&o.colour;});
        if(!full.length)return null;
        if(full.length!==ops.length||ops.some(function(o){return o.look||o.rel||o.shade||o.keep||o.pop||o.recipe||o.sub||o.ext||o.texture||o.target.parts||o.target.object||(o.target.layers||[]).length!==1;}))return null;
        if((planned.unknown||[]).length||planned.prohibited_edit)return {error:'Clarify the complete layer change before applying it.'};
        var E=W.SpbProEdit,T=W.SpbLayerTargets,cm=E&&E.compile(planned,env||{}),out=[],ids=[];
        if(!T||!cm||cm.ask||(cm.missing||[]).length||(cm.zones||[]).length!==ops.length)return {error:'The layer colour could not be resolved. Nothing changed.'};
        for(var i=0;i<ops.length;i++){
            var r=T.resolve(ops[i].target.layers[0],(env||{}).layers),p=patch(cm.zones[i].color);
            if(!r.ok||p.error||ids.indexOf(r.row.id)!==-1)return {error:r.reason||p.error||'Choose one colour for each exact layer.'};
            if(Object.keys(cm.zones[i].region||{}).some(function(k){return k!=='layers';}))return null;
            if(!paintLayer(r.row))return {error:'That is a material or alpha map, not a paint-colour layer. Choose the body paint layer, or describe the material change you want.'};
            if(r.row.id==null)return {error:'This layer has no current ID. Choose the layer again.'};
            ids.push(r.row.id);out.push({kind:'layer',layer:r.row.id,name:r.label,colour:p.colour,colourOpacity:p.colourOpacity,_nativeGroup:group(r.row),_nativeName:r.row.name});
        }
        return {queue:out,text:'Ready to recolour '+out.map(function(o){return o.name;}).join(', ')+' using its native layer colour effect. Other layers and material settings stay unchanged.'};
    }
    function apply(op,l){
        var p=patch(op.colour,op.colourOpacity);if(p.error)return p;
        if(!l||l.id!==op.layer||l.locked)return {error:'The chosen layer changed or is locked. Nothing changed.'};
        if(!paintLayer(l))return {error:'Use material controls for this material or alpha map; this tool changes paint-layer colour.'};
        if(op._nativeName&&(l.name!==op._nativeName||group(l)!==op._nativeGroup))return {error:'The chosen group and layer changed. Choose it again.'};
        var co=overlay(l);if(co&&!/^(source-over|normal)$/.test(co.blend))return {error:'This layer uses a custom colour blend. Adjust that effect in the layer controls first.'};
        if(co&&co.enabled&&co.colour===p.colour&&co.opacity===p.colourOpacity)return {ok:true,unchanged:true};
        if(typeof W.beginLayerAdjustGesture!=='function'||typeof W.setLayerColorOverlay!=='function'||typeof W.endLayerAdjustGesture!=='function')return {error:'Native layer colour controls are not ready.'};
        if(W.beginLayerAdjustGesture(l.id)===false)return {error:'The layer colour change could not start.'};
        var ok;
        try{ok=W.setLayerColorOverlay(l.id,{enabled:true,color:p.colour,opacity:p.colourOpacity});}
        finally{W.endLayerAdjustGesture(l.id,'AI layer colour');}
        var actual=overlay(l);
        if(ok===false||!actual||!actual.enabled||actual.colour!==p.colour||actual.opacity!==Math.round(p.colourOpacity))return {error:'The native layer colour was not applied.'};
        return {ok:true};
    }
    function tool(t){
        if(!t||t.name!=='spb_edit_layer')return t;
        var c=JSON.parse(JSON.stringify(t));c.description+=' Whole-layer colour changes use the native colour overlay, preserving layers above it. Supply colour as #RRGGBB; colour_opacity is optional 0-100 (default100). This does not change material/spec channels.';
        c.inputSchema.properties.colour={type:'string',pattern:'^#[0-9a-fA-F]{6}$',description:'Native non-destructive layer colour overlay.'};
        c.inputSchema.properties.colour_opacity={type:'number',minimum:0,maximum:100};return c;
    }
    var api={hex:hex,overlay:overlay,patch:patch,queue:queue,apply:apply,tool:tool};
    if(typeof module!=='undefined'&&module.exports)module.exports=api;else W.SpbNativeLayerColour=api;
})(typeof window!=='undefined'?window:{});
