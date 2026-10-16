/* Private review proposal: exact existing-zone material adjustments. No geometry guesses. */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SpbNamedZoneMaterial = api;
}(typeof window !== 'undefined' ? window : null, function () {
    'use strict';
    function clarify(text) { return {kind:'clarify', namedZone:true, question:text}; }
    function parse(text) {
        var t = String(text || '').trim();
        if (!/\bzone\b/i.test(t) || !/\b(?:rougher|smoother|roughness|metalness|clear\s*coat)\b/i.test(t)) return null;
        if (/^(?:what|why|how|explain|where|tell me)\b/i.test(t)) return null;
        if (!/^(?:please\s+)?(?:make|increase|raise|decrease|reduce|lower)\b/i.test(t)) return null;
        // Consume the entire request. Preserve clauses are allowed; extra edit clauses are not.
        t = t.replace(/[.!?]+$/, '').replace(/,?\s+(?:keeping|keep|without changing)\s+(?:(?:every|all|the)\s+)?paint\s+colou?rs?\s*(?:unchanged)?$/i, '').trim();
        var m = /^(?:please\s+)?make\s+(?:the\s+)?(.+?)\s+zone\s+(?:(a little|a bit|slightly|much)\s+)?(rougher|smoother)$/i.exec(t), name, channel, delta, amount;
        if (m) { name=m[1]; channel='roughness'; amount=m[2] ? (/much/i.test(m[2]) ? 40 : 10) : 20; delta=m[3].toLowerCase()==='rougher' ? amount : -amount; }
        else {
            m = /^(?:please\s+)?(increase|raise|decrease|reduce|lower)\s+(?:the\s+)?(roughness|metalness|clear\s*coat)\s+on\s+(?:the\s+)?(.+?)\s+zone(?:\s+by\s+(\d+)\s+points?)?$/i.exec(t);
            if (!m) return clarify('Name one existing zone and a relative change, for example “Make the Everything Else zone a little rougher”. Nothing was changed.');
            name=m[3];channel=m[2].toLowerCase().replace(/\s/g,'');amount=m[4]==null ? 20 : Number(m[4]);delta=/^(increase|raise)$/i.test(m[1]) ? amount : -amount;
        }
        name=name.replace(/^["“](.*)["”]$/, '$1').trim();
        if (!name || !Number.isSafeInteger(delta) || Math.abs(delta)>254) return clarify('Use a relative change from 0 to 254 points on one exact zone. Nothing was changed.');
        return {kind:'edit',namedZone:true,zoneName:name,channel:channel,delta:delta,amountSpecified:true};
    }
    function resolve(zones, parsed) {
        var name=String(parsed.zoneName || '').trim().toLowerCase();
        var matches=(zones || []).filter(function(z){return z && String(z.name || '').trim().toLowerCase()===name;});
        if (matches.length!==1) return clarify(matches.length ? 'More than one zone has that name. Give the intended zone a unique name first; nothing was changed.' : 'I cannot find that exact zone in this project. Use its name from the zone list; nothing was changed.');
        var z=matches[0];
        if (z.muted || z.locked || z.id==null) return clarify('That zone is muted, locked, or unavailable. Nothing was changed.');
        return {kind:'zone',zone:z};
    }
    function measure(A,B,SA,SB,channel,delta) {
        var c={metalness:0,roughness:1,clearcoat:2}[channel];
        if(c==null || !A || !B || !SA || !SB || !A.length || A.length%4 || A.length!==B.length || A.length!==SA.length || A.length!==SB.length) return null;
        var out={changed:0,paint:0,otherChannels:0,wrongDirection:0,maximumStep:0};
        for(var i=0;i<A.length;i+=4){
            var paint=false,other=false;
            for(var j=0;j<4;j++) { if(A[i+j]!==B[i+j]) paint=true; if(j!==c && SA[i+j]!==SB[i+j]) other=true; }
            if(paint)out.paint++;if(other)out.otherChannels++;
            var d=SB[i+c]-SA[i+c];if(d){out.changed++;out.maximumStep=Math.max(out.maximumStep,Math.abs(d));if(d*delta<0)out.wrongDirection++;}
        }
        out.verified=out.changed>0 && !out.paint && !out.otherChannels && !out.wrongDirection;
        return out;
    }
    function followupShape(text) {
        var t=String(text||'').trim().replace(/[.!?]+$/, '').toLowerCase();
        var m=/^(?:make\s+(?:it|that)\s+)?(?:(a little|a bit|slightly|much)\s+)?(more|less|rougher|smoother|less rough|more rough)(?:\s+again)?$/.exec(t);
        return m ? {step:m[1]==='much' ? 40 : 10,word:m[2]} : null;
    }
    function previous(log) {
        var rows=log||[],i=rows.length-1;
        // Native Send has already appended the current user message.
        if(i>=0 && rows[i].role==='user')i--;
        return i>=0 && rows[i].role==='ai' ? rows[i] : null;
    }
    function followup(text,entry,env) {
        var shape=followupShape(text),ctx=entry&&entry.editCtx&&entry.editCtx.named_material;
        if(!shape || !ctx)return null;
        if(entry.undone || !entry.undoable || !(entry.lines||[]).length) return clarify('That material edit is no longer an active change. Name the zone and adjustment again; nothing was changed.');
        if(!env || !env.current || !env.unchanged) return clarify('The project or paint changed since that material edit. Name the current zone and adjustment again; nothing was changed.');
        var matches=(env.zones||[]).filter(function(z){return z&&String(z.id)===ctx.zoneId;});
        if(matches.length!==1 || matches[0].name!==ctx.zoneName || matches[0].muted || matches[0].locked) return clarify('That exact zone is no longer available for this follow-up. Name the current target; nothing was changed.');
        var channel=/rough|smooth/.test(shape.word) ? 'roughness' : ctx.channel;
        var sign=shape.word==='rougher'||shape.word==='more rough' ? 1 : shape.word==='smoother'||shape.word==='less rough' ? -1 : (ctx.delta>0?1:-1)*(shape.word==='less'?-1:1);
        return {kind:'edit',namedZone:true,zoneName:ctx.zoneName,channel:channel,delta:sign*shape.step,amountSpecified:true};
    }
    return {parse:parse,resolve:resolve,measure:measure,followupShape:followupShape,previous:previous,followup:followup};
}));
