/* Exact existing-zone pattern requests; execution stays in the shared frame compiler. */
(function(root,factory){var api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SpbNamedPatternRefinement=api;}(typeof window!=='undefined'?window:null,function(){
    'use strict';
    function clarify(text){return {kind:'clarify',question:text};}
    function parse(text){
        var t=String(text||'').trim().replace(/[.!?]+$/,'');
        if(!/^(?:please\s+)?make\b/i.test(t)||!/\bpattern\b/i.test(t)||! /\b(?:finer|coarser|smaller|larger)\b/i.test(t))return null;
        var m=/^(?:please\s+)?make\s+(?:the\s+)?(.+?)\s+zone(?:['’]s)?\s+pattern\s+(?:(a little|a bit|slightly|much)\s+)?(finer|coarser|smaller|larger)(?:\s+again)?$/i.exec(t);
        if(!m)return null;
        var name=m[1].replace(/^["“](.*)["”]$/,'$1').trim();
        return {kind:'edit',zoneName:name,selected:/^(?:this(?: selected)?|selected)$/i.test(name),dir:/finer|smaller/i.test(m[3])?-1:1,amount:m[2]&&/much/i.test(m[2])?'lot':m[2]?'little':undefined};
    }
    function patternId(z){return z&&z.pattern&&typeof z.pattern==='object'?z.pattern.id:z&&z.pattern;}
    function resolve(zones,p,selected){
        var name=String(p.zoneName||'').toLowerCase(),found=p.selected?(Number.isInteger(selected)&&(zones||[])[selected]?[(zones||[])[selected]]:[]):(zones||[]).filter(function(z){return z&&String(z.name||'').trim().toLowerCase()===name;});
        if(found.length!==1)return clarify(found.length?'Several zones have that name. Give the intended zone a unique name first; nothing changed.':'I cannot find that exact zone. Use its current name from the zone list; nothing changed.');
        var z=found[0];if(z.id==null||z.muted||z.locked)return clarify('That zone is muted, locked or unavailable. Nothing changed.');
        if(!patternId(z)||patternId(z)==='none')return clarify('“'+z.name+'” has no existing paint pattern to resize. Choose a pattern for that zone first; nothing changed.');
        return {kind:'zone',zone:z};
    }
    function frame(z,p){return {v:1,act:'change',ops:[{verb:'adjust',target:{kind:'zone',zones:[String(z.id)]},relative:{prop:'scale',dir:p.dir,amount:p.amount}}],decals:'protect'};}
    function selectors(z){
        function mask(v){if(!v)return null;var h=2166136261;for(var i=0;i<v.length;i++)h=Math.imul(h^v[i],16777619);return {length:v.length,hash:h>>>0};}
        return JSON.stringify(['sourceLayers','sourceLayer','useRegion','color','colors','excludedColors','tolerance','applyArea','invertMask'].map(function(k){return z[k];}).concat([mask(z.regionMask),mask(z.spatialMask)]));
    }
    function receipt(r,entry,env){
        var m=r&&r.namedPattern,steps=r&&r.queue&&r.queue._s5plan&&r.queue._s5plan.steps;if(!m||!env||!env.current||!Array.isArray(steps)||steps.length!==1)return null;
        var z=m.target,found=(env.zones||[]).filter(function(v){return v&&String(v.id)===String(z&&z.id);});if(found.length!==1||found[0]!==z||z.muted||z.locked||patternId(z)!==m.patternId||selectors(z)!==m.selectors)return null;
        var ops=steps[0].ops;if(!Array.isArray(ops)||ops.length!==1)return null;var op=ops[0],spec=op.spec,p=spec&&spec.pattern;
        if(op.kind!=='edit'||String(op.zone)!==String(z.id)||!p||p.id!==m.patternId||Object.keys(p).some(function(k){return k!=='id'&&k!=='scale';})||Object.keys(spec).some(function(k){return k!=='pattern'&&k!=='_prevScale';}))return null;
        var scale=typeof z.pattern==='object'?z.pattern.scale:z.scale;if(!Number.isFinite(Number(p.scale))||Number(scale)!==Number(p.scale)||Number(p.scale)===m.beforeScale)return null;
        var diff=entry&&entry.zdiff;if(!diff||(diff.added||[]).length||(diff.edited||[]).length!==1||String(diff.edited[0].id)!==String(z.id))return null;
        return {zone_id:String(z.id),zone_name:z.name,pattern_id:m.patternId,before_scale:m.beforeScale,after_scale:Number(scale),source_layer_ids:Array.isArray(z.sourceLayers)?z.sourceLayers.slice():z.sourceLayer?[z.sourceLayer]:[]};
    }
    function captureFrame(frame,plan,env){
        if(!env||!env.current||!frame||frame.act!=='change'||(frame.keep||[]).length||frame.replace_last||frame.decals!=='protect'||!Array.isArray(frame.ops)||frame.ops.length!==1||!plan||!Array.isArray(plan.steps)||plan.steps.length!==1)return null;
        var f=frame.ops[0],t=f.target,rel=f.relative;
        if(f.verb!=='adjust'||!t||t.kind!=='zone'||!Array.isArray(t.zones)||t.zones.length!==1||Object.keys(t).some(function(k){return k!=='kind'&&k!=='zones';})||!rel||rel.prop!=='scale'||(rel.dir!==-1&&rel.dir!==1)||Object.keys(f.look||{}).length||f.except||f.ref||f.source||f.copy)return null;
        var found=(env.zones||[]).filter(function(z){return z&&String(z.id)===String(t.zones[0]);});
        if(found.length!==1)return null;
        var z=found[0],pid=patternId(z),before=Number(typeof z.pattern==='object'?z.pattern.scale:z.scale),ops=plan.steps[0].ops;
        if(z.locked||z.muted||!pid||pid==='none'||!Number.isFinite(before)||!Array.isArray(ops)||ops.length!==1)return null;
        var op=ops[0],spec=op.spec,p=spec&&spec.pattern;
        if(op.kind!=='edit'||String(op.zone)!==String(z.id)||!p||p.id!==pid||Object.keys(p).some(function(k){return k!=='id'&&k!=='scale';})||Object.keys(spec).some(function(k){return k!=='pattern'&&k!=='_prevScale';})||Number(spec._prevScale)!==before||!Number.isFinite(Number(p.scale))||Number(p.scale)===before)return null;
        return {namedPattern:{target:z,patternId:pid,beforeScale:before,selectors:selectors(z),documentStamp:env.documentStamp},queue:{_s5plan:plan}};
    }
    function followupShape(text){var m=/^(?:(?:make\s+(?:it|that)\s+)?(?:a little|a bit|slightly)\s+)?(finer|coarser|smaller|larger)(?:\s+again)?[.!?]*$/i.exec(String(text||'').trim());return m?{dir:/finer|smaller/i.test(m[1])?-1:1,amount:'little'}:null;}
    function adviceShape(text){
        var m=/^(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?make\s+(?:it|that(?:\s+pattern)?|this\s+pattern)\s+(?:(a little|a bit|slightly)\s+)?(finer|coarser|smaller|larger)\s*[.!?]*$/i.exec(String(text||'').trim());
        return m?{dir:/finer|smaller/i.test(m[2])?-1:1,amount:m[1]?'little':undefined}:null;
    }
    function advice(text,previous,env){
        var p=adviceShape(text),a=previous&&(previous.answer||previous);
        if(!p||!a||a.editor_topic!=='pattern')return null;
        var s=env&&env.snapshot;
        if(a.needs_pattern_target||!s||s.answer!==a)return clarify('Read the current pattern settings again before asking for that adjustment. Nothing changed.');
        if(!env.current||!env.unchanged)return clarify('The project or paint changed since that pattern answer. Ask about the current settings again; nothing changed.');
        var z=(env.zones||[])[env.selected];
        if(!z||z!==s.target||String(z.id)!==String(a.pattern_zone_id)||patternId(z)!==a.pattern_id)return clarify('The selected pattern zone changed since that answer. Select the pattern you mean and ask about its settings again; nothing changed.');
        var found=resolve(env.zones,{selected:true,zoneName:'selected'},env.selected);
        if(found.kind!=='zone')return found;
        p.kind='edit';p.zoneName='selected';p.selected=true;p.adviceSnapshot=s;return p;
    }
    function followup(text,entry,env){
        var p=followupShape(text),ctx=entry&&entry.editCtx&&entry.editCtx.named_pattern;if(!p||!ctx)return null;
        if(entry.undone||!entry.undoable||!(entry.lines||[]).length)return clarify('That pattern adjustment is no longer active. Name the zone and adjustment again; nothing changed.');
        if(!env||!env.current||!env.unchanged)return clarify('The project or paint changed since that adjustment. Name the current zone and adjustment again; nothing changed.');
        var found=resolve(env.zones,{zoneName:ctx.zoneName});if(found.kind!=='zone'||String(found.zone.id)!==ctx.zoneId||patternId(found.zone)!==ctx.patternId)return clarify('That exact pattern is no longer available for this follow-up. Name the current target; nothing changed.');
        p.kind='edit';p.zoneName=ctx.zoneName;return p;
    }
    return {parse:parse,patternId:patternId,resolve:resolve,frame:frame,selectors:selectors,receipt:receipt,captureFrame:captureFrame,followupShape:followupShape,followup:followup,adviceShape:adviceShape,advice:advice};
}));
