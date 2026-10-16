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
        for(var guardIndex=0;guardIndex<planned.ops.length;guardIndex++){
            if(!planned.ops[guardIndex]._nativeColourRefinement)continue;
            var failure=W.SpbLayerColourFollowup?W.SpbLayerColourFollowup.validate(planned.ops[guardIndex],env):'Layer colour refinement is unavailable. Nothing changed.';
            if(failure)return {error:failure};
        }
        if(planned.ops.some(function(o){return o._box;}))return null;
        var ops=planned.ops,full=ops.filter(function(o){return o&&o.target&&o.target.kind==='layer'&&o.colour;});
        if(!full.length)return queueRegion(planned,env);
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
        return {queue:out,text:'Layer colour results:'};
    }
    // Oct10 native lossless fixture: a flattened zone recolour changes artwork edges.
    // Reuse the same native colour path as Offline, only for a complete simple frame.
    function frameQueue(frame,text,env){
        var ops=frame&&frame.ops||[], E=W.SpbProEdit;
        if(!frame||frame.act!=='change'||!ops.length||(frame.keep||[]).length||frame.scope||!E)return null;
        if(ops.some(function(o){return !o||o.verb!=='recolour'||!o.target||o.target.kind!=='layer'||
            Object.keys(o.target).some(function(k){return k!=='kind'&&k!=='layers';})||
            !o.look||Object.keys(o.look).some(function(k){return k!=='colour';})||
            !o.look.colour||!hex(o.look.colour.hex)||Object.keys(o.look.colour).some(function(k){return k!=='hex';})||
            Object.keys(o).some(function(k){return k!=='verb'&&k!=='target'&&k!=='look';});}))return null;
        var planned={kind:'ops',ops:ops.map(function(o){return {target:o.target,colour:{hex:o.look.colour.hex,exact:true}};})};
        var native=queue(planned,env);if(!native||native.error)return native;
        for(var i=0;i<native.queue.length;i++){
            var hit=W.SpbLayerTargets.resolve(native.queue[i].layer,env.layers);
            if(!hit.ok||hit.row.locked)return {error:'The exact layer is missing or locked. Nothing changed.'};
        }
        if(text){
            var words=E.plan(text,env), wordQueue=words&&queue(words,env);
            if(words&&words.prohibited_edit)return {error:words.text||'The requested change conflicts with a layer to preserve. Nothing changed.'};
            if(!wordQueue||wordQueue.error)return {error:wordQueue&&wordQueue.error||'Clarify the complete layer colour request before applying this frame. Nothing changed.'};
            function signature(q){return q.map(function(o){return [o.layer,o.colour,o.colourOpacity,o.sourceColour||''].join('|');}).sort().join(';');}
            if(signature(native.queue)!==signature(wordQueue.queue))return {error:'The frame does not match the layers and colours in the request. Nothing changed.'};
        }
        return native;
    }
    function queueRegion(planned,env){
        var ops=planned&&planned.ops||[],E=W.SpbProEdit,T=W.SpbLayerTargets;
        if(!ops.length||ops.some(function(o){return !o||!o.target||o.target.kind!=='colour'||(o.target.layers||[]).length!==1||!o.colour||o.colour.exact!==true||!hex(o.colour.hex)||o.colour.qual&&Object.keys(o.colour.qual).length||o.look||o.rel||o.shade||o.keep||o.pop||o.recipe||o.sub||o.ext||o.texture||o.copy||o.target.parts||o.target.object;}))return null;
        if((planned.unknown||[]).length||planned.prohibited_edit)return {error:'Clarify the complete colour replacement before applying it.'};
        var out=[];
        if(!T||!E||!env||typeof env.sourceLayerPixels!=='function')return {error:'Read the exact layer pixels before replacing a source colour. Nothing changed.'};
        for(var i=0;i<ops.length;i++){
            var r=T.resolve(ops[i].target.layers[0],env.layers);
            if(!r.ok)return {error:r.reason};
            if(!paintLayer(r.row))return {error:'Choose a paint-colour layer, not a material or alpha map.'};
            var pixels=env.sourceLayerPixels(r.row.id);
            if(!pixels||pixels.error||pixels.status!=='pixels-present'||!pixels.layer||pixels.layer.id!==r.row.id)return {error:pixels&&pixels.error||'This exact layer has no readable source pixels. Nothing changed.'};
            if((ops[i].exclude||[]).length||(planned.exclude||[]).length)return {error:'This replacement needs its excluded areas resolved first. Nothing changed.'};
            // The zone compiler calls flattened-image edgeFit even with a raw palette.
            // Reuse its colour vocabulary directly, then use native Color Replace's tolerance.
            var palette=E.prepPalette((pixels.palette||[]).map(function(c){return {hex:c.colour,share_pct:c.share_of_nontransparent_pixels_pct};}));
            var tg=ops[i].target,match=E.resolveColour(E.wantFor(tg.word,tg.hex,tg.qual),palette);
            if(!match||!match.entries||!match.entries.length)return {error:'The requested source colour is not present in this layer. Nothing changed.'};
            if(r.row.id==null||match.entries.length!==1)return {error:'This layer needs a more precise source colour or selection before replacement. Nothing changed.'};
            var p=replacement(ops[i].colour.hex,match.entries[0].hex,40);if(p.error)return p;
            out.push({kind:'layer',layer:r.row.id,name:r.label,colour:p.colour,sourceColour:p.sourceColour,replaceTolerance:p.replaceTolerance,_nativeGroup:group(r.row),_nativeName:r.row.name});
        }
        return {queue:out,text:'Source colour replacement results:'};
    }
    // Native commit evidence is distinct from a check of the rendered artwork.
    // The kernel count precedes selection clipping: never call it changed pixels.
    function outcome(op,result){
        result=result||{};
        var status=result.error||result.ok!==true?'failed':result.unchanged?'unchanged':'applied';
        var label=String(op.name||op.layer||'Layer');
        var line=status==='failed'?label+': '+(result.error||'The colour change did not complete.'):
            status==='unchanged'?label+': no colour change was made.':
            label+': '+(op.sourceColour?'replaced '+op.sourceColour+' with '+op.colour:'applied colour '+op.colour)+'.';
        var out={layer:op.layer,name:label,operation:op.sourceColour?'source_colour_replace':'colour_overlay',status:status,line:line,render_verified:false};
        if(op.sourceColour&&Number.isInteger(result.pixels)&&result.pixels>=0)out.matched_pixels_before_selection=result.pixels;
        return out;
    }
    function apply(op,l){
        var p=patch(op.colour,op.colourOpacity);if(p.error)return p;
        if(!l||l.id!==op.layer||l.locked)return {error:'The chosen layer changed or is locked. Nothing changed.'};
        if(!paintLayer(l))return {error:'Use material controls for this material or alpha map; this tool changes paint-layer colour.'};
        if(op._nativeName&&(l.name!==op._nativeName||group(l)!==op._nativeGroup))return {error:'The chosen group and layer changed. Choose it again.'};
        if(op.sourceColour!=null)return replace(op,l);
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
    function replacement(colour,source,tolerance){
        var p=patch(colour),from=hex(source),tol=tolerance==null?40:tolerance;
        if(p.error||!from)return {error:'Choose exact six-digit source and replacement colours.'};
        if(typeof tol!=='number'||!Number.isFinite(tol)||tol<0||tol>255)return {error:'Colour tolerance must be from 0 to 255.'};
        return {colour:p.colour,sourceColour:from,replaceTolerance:tol};
    }
    function replace(op,l){
        var p=replacement(op.colour,op.sourceColour,op.replaceTolerance);if(p.error)return p;
        if(op.colourOpacity!=null&&op.colourOpacity!==100)return {error:'Source-colour replacement uses the native colour-distance blend; colour_opacity must be 100 or omitted.'};
        if(typeof W._getAdjustmentTarget!=='function'||typeof W.autoColorReplace!=='function'||!W.SPB_AI_EXPLICIT_COLOR_REPLACE)return {error:'Exact-layer native Color Replace is not available in this build.'};
        var target=W._getAdjustmentTarget('AI layer colour replace',l.id);
        if(!target||!target.isLayer||target.layer!==l)return {error:'The exact editable layer could not be prepared. Nothing changed.'};
        var result=W.autoColorReplace(p.sourceColour,p.colour,p.replaceTolerance,target);
        if(!result||!result.ok)return {error:'The native colour replacement could not commit.'};
        return result;
    }
    function tool(t){
        if(!t||t.name!=='spb_edit_layer')return t;
        var c=JSON.parse(JSON.stringify(t));c.description+=' Whole-layer colour changes use the native colour overlay, preserving layers above it. Supply colour as #RRGGBB; colour_opacity is optional 0-100 (default100). This does not change material/spec channels. Read layer_colour_outcomes for applied, unchanged or failed results. An unchanged result made no colour change. Native commit results do not verify rendered artwork; matched_pixels_before_selection is not a count of changed pixels.';
        c.inputSchema.properties.colour={type:'string',pattern:'^#[0-9a-fA-F]{6}$',description:'Native non-destructive layer colour overlay.'};
        c.inputSchema.properties.colour_opacity={type:'number',minimum:0,maximum:100};
        c.inputSchema.properties.source_colour={type:'string',pattern:'^#[0-9a-fA-F]{6}$',description:'When supplied with colour, replace only this source RGB family inside the exact layer using native Color Replace, retaining artwork above. Uses active selection if present. Changes raw layer pixels; Undo restores them. Omit for a whole-layer overlay.'};
        c.inputSchema.properties.replace_tolerance={type:'number',minimum:0,maximum:255,description:'Native colour distance tolerance, default40; 0 matches exact RGB only. Requires source_colour.'};
        return c;
    }
    function analysePixels(data,width,height){
        if(!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||width*height>16777216||!data||data.length!==width*height*4)return {error:'The layer raster is unavailable or too large to inspect safely.'};
        var total=width*height,nonzero=0,opaque=0,bins=new Map(),minX=width,minY=height,maxX=-1,maxY=-1;
        for(var i=0;i<data.length;i+=4){
            var a=data[i+3];if(!a)continue;
            nonzero++;if(a===255)opaque++;var pos=i/4,x=pos%width,y=Math.floor(pos/width);
            minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
            var key=(data[i]>>4)*256+(data[i+1]>>4)*16+(data[i+2]>>4),b=bins.get(key);
            if(!b){b={n:0,r:0,g:0,b:0};bins.set(key,b);}b.n++;b.r+=data[i];b.g+=data[i+1];b.b+=data[i+2];
        }
        function hx(n){return Math.round(n).toString(16).padStart(2,'0');}
        return {status:nonzero?'pixels-present':'empty',width:width,height:height,nontransparent_pixels:nonzero,fully_opaque_pixels:opaque,total_pixels:total,
            alpha_bounds:nonzero?[minX,minY,maxX+1,maxY+1]:null,
            palette_quantization_bits:4,palette:Array.from(bins.values()).sort(function(a,b){return b.n-a.n;}).slice(0,8).map(function(b){return {colour:'#'+hx(b.r/b.n)+hx(b.g/b.n)+hx(b.b/b.n),share_of_nontransparent_pixels_pct:Math.round(b.n/nonzero*10000)/100};})};
    }
    function inspect(ref,env,includeImage){
        env=env||{};var T=W.SpbLayerTargets,r=T&&T.resolve(ref,env.layers);
        if(!r||!r.ok)return {error:r?r.reason:'Exact layer lookup is not ready.',choices:r&&r.choices};
        if(env.busy)return {error:'Finish the current stroke or transform before inspecting committed layer pixels.'};
        var l=r.row,im=l.img,width=im&&(im.naturalWidth||im.width),height=im&&(im.naturalHeight||im.height),cv;
        if(!im||im.complete===false||!width||!height||width*height>16777216)return {error:'This layer raster is not loaded or is too large to inspect. No pixels were changed.'};
        try{
            cv=W.document.createElement('canvas');cv.width=width;cv.height=height;
            var ctx=cv.getContext('2d',{willReadFrequently:true});ctx.drawImage(im,0,0);
            var result=analysePixels(ctx.getImageData(0,0,width,height).data,width,height);if(result.error)return result;
            result.layer={id:l.id,name:l.name,group:group(l),hidden:l.visible===false};
            result.basis='Complete committed source raster before layer effects, group compositing and zones; hidden layers can be inspected without showing them.';
            result.colour_overlay=overlay(l);result.geometry_verified=false;
            var paint=W.document.getElementById('paintCanvas'),bb=l.bbox||[0,0];
            result.opaque_full_canvas=!!(paint&&width===paint.width&&height===paint.height&&Number(bb[0])===0&&Number(bb[1])===0&&result.fully_opaque_pixels===result.total_pixels);
            result.guidance=result.status==='empty'?'This raster has no paint pixels. A colour overlay or visibility toggle cannot create its design. Inspect/recover the original source deliberately; do not overwrite a blank layer automatically.':result.opaque_full_canvas?'This layer is opaque over the full canvas. A solid whole-layer colour overlay replaces all its colour regions. Inspect the palette and choose the intended regions before preserving a multi-colour design.':'A colour overlay affects every nontransparent pixel of this layer; palette shares describe its raw raster, not how much shows in the final paint.';
            if(includeImage){var thumb=W.document.createElement('canvas'),scale=Math.min(1,512/Math.max(width,height));thumb.width=Math.max(1,Math.round(width*scale));thumb.height=Math.max(1,Math.round(height*scale));thumb.getContext('2d').drawImage(cv,0,0,thumb.width,thumb.height);result.images=[{name:'raw_layer_before_effects',data_url:thumb.toDataURL('image/png')}];thumb.width=thumb.height=0;}
            return result;
        }catch(e){return {error:'The current layer pixels could not be read. No pixels were changed.'};}
        finally{if(cv)cv.width=cv.height=0;}
    }
    function inspectionQuestion(text){
        var s=String(text||'').trim().replace(/[?.!]$/,''),m=/^(?:please\s+)?inspect\s+(?:the\s+)?layer\s+(.+)$/i.exec(s)||/^what\s+colou?rs\s+(?:are\s+)?in\s+(?:the\s+)?(.+?)\s+layer$/i.exec(s)||/^is\s+(?:the\s+)?(.+?)\s+layer\s+empty$/i.exec(s);
        return m?m[1].trim():null;
    }
    function offlineInspection(text,env){
        var ref=inspectionQuestion(text);if(!ref)return null;
        var r=inspect(ref,env,false),message=r.error?(r.error+(r.choices&&r.choices.length?' Choose: '+r.choices.join('; '):'')):
            r.layer.group+' / '+r.layer.name+'\n'+r.width+' × '+r.height+' source pixels; '+r.nontransparent_pixels+' nontransparent.'+(r.layer.hidden?' The layer is currently hidden.':'')+'\n'+(r.palette.length?'Source colours: '+r.palette.map(function(p){return p.colour+' ('+p.share_of_nontransparent_pixels_pct+'%)';}).join(', ')+'.\n':'')+r.guidance+'\n'+r.basis;
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.layer_pixels',title:'Layer pixels',text:message+'\nNothing has been changed or queued.',actions:[],quick:true,live_context:true}};
    }
    var INSPECT_TOOL={name:'spb_inspect_layer',description:'Inspect one exact current layer ID or full group/name before recolouring it. Returns complete raw alpha coverage, bounded actual palette and optional raw-layer image, including hidden layers. Distinguishes missing/empty pixels from visibility. Read-only; does not establish UV panel geometry.',inputSchema:{type:'object',properties:{layer:{type:'string'},image:{type:'boolean',description:'Include a raw-layer thumbnail, default true.'}},required:['layer']},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false}};
    var api={hex:hex,overlay:overlay,patch:patch,replacement:replacement,queue:queue,frameQueue:frameQueue,queueRegion:queueRegion,apply:apply,outcome:outcome,tool:tool,analysePixels:analysePixels,inspect:inspect,inspectionQuestion:inspectionQuestion,offlineInspection:offlineInspection,INSPECT_TOOL:INSPECT_TOOL};
    if(typeof module!=='undefined'&&module.exports)module.exports=api;else W.SpbNativeLayerColour=api;
})(typeof window!=='undefined'?window:{});
