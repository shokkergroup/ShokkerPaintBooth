(function (W) {
    'use strict';
    // Stateless grammar repair: a complete trailing preservation sentence is
    // not a second recolour operation. No new target or permission is invented.
    function plan(text, env, parse, clause, norm) {
        var raw = String(text || ''), m = /^(.*?)(?:[.;]\s*|\s+(?:and|but)\s+)(?:keep|leave)\s+([^.;!?\n]{1,180}?)\s+(?:exactly\s+)?(?:unchanged|untouched|alone|as\s+is|as\s+they\s+are)[.!?]*\s*$/i.exec(raw);
        if (!m || !m[1].trim() || /\b(?:make|paint|repaint|change|recolou?r|add|apply|set|turn|use|remove)\b/i.test(m[2])) return null;
        var keep = clause(m[2]), words = [], leftover = norm(m[2]);
        if (!keep || (keep.targets || []).some(function (t) { return t.kind !== 'colour' || t.parts || t.layers || t.object; })) return null;
        (keep.targets || []).forEach(function(t) { if (t.word) words.push(norm(t.word)); });
        (keep.colours || []).forEach(function(c) { if (c.name) words.push(norm(c.name)); });
        words = words.filter(function(x,i,a) { return a.indexOf(x) === i; }).sort(function(a,b) {return b.length-a.length;});
        if (!words.length) return null;
        words.forEach(function(word) {leftover=leftover.replace(new RegExp('\\b'+word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b','g'),' ');});
        leftover=leftover.replace(/\b(?:the|my|and|or|all|both|existing|current|original|areas?|marks?|paint|colou?rs?|pixels?|sections?)\b/g,' ').replace(/[\s,&]+/g,'');
        if (leftover) return null;
        var out = parse(m[1].trim(), env), ops = out && out.ops;
        if (!out || out.kind !== 'ops' || !ops || ops.length !== 1 || (out.unknown || []).length) return null;
        var op=ops[0], target=op.target;
        if (!target || target.kind !== 'colour' || !target.word || target.object || target.layers || op.ext) return null;
        if (words.indexOf(norm(target.word)) >= 0) return {kind:'ask',prohibited_edit:true,text:'You asked to change and preserve the same colour. Which should stay unchanged?',chips:[]};
        out.preserved_colour_words=words.slice();
        out.preserved_clause=raw.slice(m[1].length).trim();
        return out;
    }
    function layerPlan(text, env, parse, norm) {
        var raw=String(text||''), m=/^(.*?)(?:[.;]\s*|\s+(?:and|but|while)\s+)(?:keep|leave)\s+([^.;!?\n]{1,180}?)\s+(?:exactly\s+)?(?:unchanged|untouched|alone|as\s+is|as\s+they\s+are)[.!?]*\s*$/i.exec(raw);
        function stop(message) {return {kind:'ask',prohibited_edit:true,text:message,chips:[],raw:raw};}
        if (!m) return /\b(?:keep|leave)\b[^.;!?\n]*\blayers?\b/i.test(raw) ? stop('I could not separate the layer changes from the layers to preserve. State the change, then name the layers that must stay unchanged.') : null;
        if (!/\blayers?\b/i.test(m[2])) return null;
        var tail=m[2].trim().replace(/\s+layers?$/i,''), names=tail.split(/\s+and\s+|\s*,\s*/i), kept=[], layers=(env.layers||[]);
        for(var i=0;i<names.length;i++) {
            var name=norm(names[i].replace(/^(?:the|my)\s+/i,'').replace(/\s+layers?$/i,''));
            var exact=W.SpbLayerTargets&&W.SpbLayerTargets.resolve(names[i].replace(/^(?:the|my)\s+/i,'').replace(/\s+layers?$/i,''),layers);
            var matches=exact?(exact.ok?[exact.row]:[]):layers.filter(function(l){return l&&norm(l.name)===name;});
            if(matches.length!==1) return stop('I need one exact, unique layer for each area you want to preserve. Check the layer names before applying a change.');
            kept.push(exact?exact.selector:matches[0].name);
        }
        if(!/\blayer\b/i.test(m[1])) return stop('You asked to preserve layers. Choose the specific layer to change so the rest can remain untouched.');
        var out=parse(m[1].trim(),env), ops=out&&out.ops;
        if(!out||out.kind!=='ops'||!ops||ops.length!==1||(out.unknown||[]).length) return stop('I could not resolve one layer change while preserving the named layers. Specify the layer and the change.');
        var target=ops[0].target, changed=target&&target.layers;
        if(!changed||!changed.length||! /^(?:layer|colour)$/.test(target.kind)||ops[0].ext) return stop('Choose an explicit layer target before applying this protected change.');
        if(changed.some(function(n){return kept.indexOf(n)>=0;})) return stop('You asked to change and preserve the same layer. Which layer should stay unchanged?');
        out.preserved_layers=kept.slice(); out.preserved_clause=raw.slice(m[1].length).trim(); out.raw=raw;
        return out;
    }
    W.SpbPreservedColours={plan:plan,layerPlan:layerPlan};
})(window);
