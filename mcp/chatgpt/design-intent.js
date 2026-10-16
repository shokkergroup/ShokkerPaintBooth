(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.SpbDesignIntent = factory();
})(typeof window !== 'undefined' ? window : this, function () {
    'use strict';
    // Finite offline guidance and a common request contract. This is not a model,
    // a visual inspection, or permission to apply a proposed design.
    function classify(text) {
        var t = String(text || '').trim(), low = t.toLowerCase().replace(/[\u2018\u2019\u02bc\uff07]/g, "'");
        if (typeof window !== 'undefined' && window.SPB_CX3_OFF) return { mode: 'unspecified', explicit: false, mutation_allowed: null, rule: 'CX3 off' };
        var explicit = /\b(?:advice\s+only|(?:just|only)\s+(?:discuss|discussing|compare|comparing|brainstorm|brainstorming)|(?:do\s+not|don't|dont)\s+(?:apply\s+(?:it|this|that|anything|yet)|(?:edit|paint|change)\s+anything|change\s+the\s+paint)|without\s+(?:applying|editing|changing\s+anything)|nothing\s+(?:changed|applied)\s+yet)\b/.test(low);
        // Native app chat Oct10: a design wish followed by "let's discuss before
        // changing anything" is a discussion boundary, not a paint approval.
        explicit = explicit || /\b(?:discuss|brainstorm|compare|explain|plan|talk\s+(?:about|through))\b[^.!?;]{0,100}\bbefore\s+(?:(?:you|we)\s+)?(?:changing|change|editing|edit|painting|paint|applying|apply)\s+(?:anything|it|this|that|the\s+paint)\b/.test(low) || /\b(?:do\s+not|don't|dont)\s+do\s+anything\b|\b(?:just|only)\s+(?:talk|talking|explain|explaining|plan|planning)\b|\bno\s+(?:edits?|changes?)\s+(?:yet|for\s+now)\b/.test(low);
        // Native follow-up Oct10: "Please explain only." is a request boundary.
        // The clause ending matters: "explain only the roof, then paint" is not
        // the same boundary, and should still reach ordinary command handling.
        explicit = explicit || /\b(?:explain|explanation|discuss|discussion|compare|comparison|brainstorm|brainstorming|plan|planning)\s+only(?=\s*(?:[.!?;,:]|$))|\bjust\s+(?:an?\s+)?(?:explanation|discussion|comparison|advice)\b|\bno\s+(?:edits?|changes?)(?=\s*(?:[.!?;]|$))/.test(low);
        // A later concrete command wins over a general question, but never over
        // an explicit "advice only" boundary in the same message.
        var command = /(?:^|[.;!?]\s*|\bthen\s+|\band\s+)(?:(?:could|would|can)\s+you\s+)?(?:please\s+)?(?:apply|paint|recolou?r|change|make|set|add|remove|undo|use)\b/.test(low);
        var design = /\b(?:matte|satin|gloss|pearl|chrome|glitter|scheme|livery|palette|colou?r|contrast|accent|black|white|blue|gold|red|green|silver|stripes?)\b/.test(low);
        var question = /^(?:would|should|could|what|which|how|do\s+you\s+think|does|is|will)\b/.test(low) && /\b(?:work|look|better|suit|pair|match|recommend|suggest|think|difference|versus|vs|compare|choose|contrast|combine|go\s+(?:with|together))\b/.test(low);
        // Asking for alternatives is a proposal request even when phrased as
        // an imperative. A later paint command must still reach the planner.
        var proposals = /\b(?:give|show|suggest|offer|propose|sketch|brainstorm|compare)\b/.test(low) &&
            /\b(?:ideas?|options?|directions?|concepts?|schemes?|looks?|palettes?|approaches|variations)\b/.test(low);
        var advice = explicit || (design && (question || proposals) && !command);
        return { mode: advice ? 'advice' : 'unspecified', explicit: explicit,
            proposal_request: advice && proposals,
            mutation_allowed: advice ? false : null,
            rule: advice ? 'Discuss and compare only. Do not apply, queue an edit, render, or treat a proposal as approval. Keep the buyer\'s quoted constraints. Read the actual current paint before claiming what it looks like.' : 'Resolve intent from the buyer\'s words and current state; this classification grants no edit approval.' };
    }
    function discussion(previous) {
        var data = previous && previous.answer && previous.answer.design_proposals;
        if (!data || data.schema !== 'spb-design-proposals/1' || data.executable !== false || !Array.isArray(data.items) || data.items.length < 2 || data.items.length > 3) return null;
        if (!data.constraints || typeof data.constraints.no_glitter !== 'boolean' || !Array.isArray(data.constraints.protected_artwork) || data.constraints.protected_artwork.some(function(x){return typeof x !== 'string';})) return null;
        if (data.items.some(function(item){return !item || ['id','title','description','rationale'].some(function(key){return typeof item[key] !== 'string' || !item[key].trim();});})) return null;
        // Persist/reuse only descriptive fields, even if an imported envelope adds
        // target IDs, queues or approval flags alongside otherwise valid proposals.
        var safe={schema:data.schema,executable:false,source:String(data.source||'').slice(0,300),request:String(data.request||'').slice(0,1000),
            constraints:{no_glitter:data.constraints.no_glitter,protected_artwork:data.constraints.protected_artwork.slice(0,12).map(function(x){return x.slice(0,100);})},
            items:data.items.map(function(item){return {id:item.id,title:item.title,description:item.description,rationale:item.rationale};})};
        try { var encoded=JSON.stringify(safe); return encoded.length <= 6000 ? JSON.parse(encoded) : null; } catch(e) { return null; }
    }
    function proposals(text) {
        var low = text.toLowerCase(), lead = low.split(/[.;]/)[0];
        var colours = Array.from(new Set(lead.match(/\b(?:black|white|blue|gold|red|green|silver|orange|purple|yellow|pink|grey|gray)\b/g) || []));
        if (colours.length !== 2) return null;
        var primary = colours[0], accent = colours[1];
        var protectedArt = ['numbers', 'sponsors', 'logos'].filter(function (name) { return new RegExp('\\b(?:keep|preserve|leave|protect)\\b[^.;]{0,100}\\b'+name+'\\b').test(low); });
        var items = [
            {id:'quiet-base', title:'Quiet '+primary+' base, fine '+accent+' accents',
                description:'Keep '+primary+' dominant and use '+accent+' sparingly as fine trim around existing design areas. Leave breathing room around numbers and sponsors.',
                rationale:'A small accent area keeps the scheme restrained and gives the important marks room to read. Fine trim follows an existing design without making a new large graphic.'},
            {id:'soft-contrast', title:'Soft '+primary+' base, muted '+accent+' panels',
                description:'Use a softer '+primary+' appearance with a few muted '+accent+' blocks on existing, separately editable design areas. Keep their edges simple and the sheen gentle.',
                rationale:'Larger, simpler accent areas can be easier to read at a distance than thin trim. Muted colour and gentle sheen keep those areas from competing with the protected marks.'}
        ];
        if (/\b(?:three|3)\b/.test(lead)) items.push({id:'material-contrast',title:primary+' and '+accent+' with subtle material contrast',description:'Keep the colour shapes simple and distinguish the '+accent+' accent through a soft sheen rather than sparkle.',rationale:'Material contrast adds interest without adding a busy pattern. It needs an actual spec preview or simulator view to judge the result.'});
        return {schema:'spb-design-proposals/1',executable:false,source:'Offline design principles from the buyer description; not a visual assessment or a compiled paint plan',request:text.slice(0,1000),constraints:{no_glitter:/\b(?:no|without)\s+glitter\b/.test(low),protected_artwork:protectedArt},items:items};
    }
    function answer(text, previous) {
        var intent = classify(text), prior = discussion(previous), follow = String(text || '').trim().toLowerCase();
        // Resolve explanation questions against the displayed structured proposal,
        // not a finish list, an old paint step or an inferred colour command.
        var which = /\b(first|second|third|last)\b/.exec(follow);
        var explain = prior && which && /^(?:why|how|what|would|could|does|is|explain|tell me)\b/.test(follow) && !/^(?:could|would|can)\s+you\s+(?:please\s+)?(?:apply|paint|make|change|use|set)\b|\b(?:then|and|also)\s+(?:apply|paint|make|change|use|set)\b|[.;!?]\s*(?:apply|paint|make|change|use|set)\b/.test(follow);
        if (intent.mode !== 'advice' && !explain) return null;
        var t = String(text || ''), low = t.toLowerCase(), lines = [];
        var options = explain ? prior : (intent.proposal_request ? proposals(t) : null);
        if (explain) {
            var index = which[1] === 'last' ? prior.items.length - 1 : ['first','second','third'].indexOf(which[1]);
            var chosen = prior.items[index];
            if (!chosen) return null;
            lines.push('Option '+(index+1)+' — '+chosen.title+'. '+chosen.rationale);
            lines.push('That explains how it serves your design brief. I have not visually assessed this car or verified where those accents would go.');
        } else if (options) {
            options.items.forEach(function (item, index) { lines.push((index+1)+'. '+item.title+'\n'+item.description); });
            lines.push('These are design directions, not ready-to-run paint steps. Applying one needs the actual editable areas for its base and accents.');
        }
        if (!options && /\bblack\b/.test(low) && /\bgold\b/.test(low)) {
            lines.push('Black and gold can work as a restrained pairing: black provides the quiet base and gold works well as a smaller accent. Too much gold can compete with the numbers and sponsor marks.');
            if (/\bblue\b/.test(low)) lines.push('If you keep blue, let it remain one deliberate part of the scheme rather than scattering blue and gold accents everywhere.');
            if (/\bwhite\b/.test(low)) lines.push('Keep the white marks clear against a dark background, and leave space around them so the gold does not reduce their contrast.');
        }
        if (/\bmatte\b/.test(low) && /\bsatin\b/.test(low)) lines.push('Matte gives a flatter, quieter appearance; satin keeps a softer sheen. Satin gold against matte black can separate the accent through both colour and sheen. Check the actual preview lighting before settling the balance.');
        if (/\b(?:no|without)\s+glitter\b/.test(low) || (options && options.constraints.no_glitter)) lines.push('Your no-glitter constraint rules out sparkle effects; a gold colour does not require a glitter finish.');
        if (options && options.constraints.protected_artwork.length) lines.push('Keep unchanged: '+options.constraints.protected_artwork.join(', ')+'.');
        if (!lines.length) lines.push('For a readable scheme, choose one main colour, a smaller accent, and enough contrast around numbers and sponsor marks. The Offline Helper can give these basic principles; connect ChatGPT or Claude for a fuller discussion of your specific design.');
        lines.push('This is advice from your description, not a visual assessment of the loaded paint. Nothing has been changed or queued.');
        var body = lines.join('\n\n');
        return { cls: 'ANSWER', via: 'design-advice', hits: [{id:'assistant.design_advice', title:'Design advice', score:0}],
            answer: {id:'assistant.design_advice', project_discussion:true, title:options?'Design options':'Design advice', design_proposals:options||undefined, text:body, summary:body, how:[], actions:[], related:[], faq:null, shot:null} };
    }
    return {classify: classify, answer: answer, discussion:discussion};
});
