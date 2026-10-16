(function (W) {
    'use strict';
    // The request, rather than coverage size or a generated plan, authorizes a
    // colour change. The verifier still checks every changed before-picture cell.
    function read(text, before) {
        var E = W.SpbProEdit, t = String(text || ''), p;
        if (!E || !E.plan || !E.wantFor || !E.familyOf || !/^\s*(?:change|make|turn|recolou?r|paint)\b/i.test(t)) return null;
        if (W.SpbDesignIntent && W.SpbDesignIntent.classify(t).mode === 'advice') return null;
        try { p = E.plan(t, {palette:[],layers:[],zoneColours:[]}); } catch (e) { return null; }
        if (!p || p.kind !== 'ops' || p.prohibited_edit || (p.unknown || []).length || !p.ops || p.ops.length !== 1) return null;
        var op = p.ops[0], tg = op.target;
        if (!tg || tg.kind !== 'colour' || !tg.word || tg.parts || tg.layers || tg.object || op.ext || (!op.colour && !op.look && !op.adjust)) return null;
        var want = E.wantFor(tg.word, tg.hex, tg.qual), exact = /^#[0-9a-f]{6}$/i.test(tg.word) ? tg.word.toLowerCase() : null;
        var mask = new Uint8Array(before.length / 4), count = 0;
        for (var i = 0; i < mask.length; i++) {
            var k = i * 4, rgb = [before[k], before[k+1], before[k+2]], h = '#' + rgb.map(function(v) {return ('0'+v.toString(16)).slice(-2);}).join('');
            var light = (Math.max.apply(null,rgb) + Math.min.apply(null,rgb)) / 510;
            var allowed = exact ? h === exact : E.familyOf(h) === want.fam && (!want.band || (want.band === 'dark' ? light < 0.4 : light > 0.58));
            if (allowed && before[k+3] > 0) {mask[i]=1;count++;}
        }
        if (!count) return null;
        return {word:tg.word,mask:mask,cells:count,preserved:(p.preserved_colour_words || []).slice()};
    }
    W.SpbColourReportScope={read:read};
})(window);
