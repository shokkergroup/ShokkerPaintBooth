// spb-design-intent.js -- CX3 2026-10-09 (CODEX-INTEGRATE-2; source: mcp/chatgpt/design-intent.js, 'Shared factual routing' + the advice-only gate).
// WHY: the Offline Helper read "Would matte black and satin gold work here ... Advice only." as an ORDER (steps + a Run button, and "Advice only" listed as "Not done").
// An explicit boundary ("advice only", "don't apply", "just discuss", "nothing applied yet") or a plain design question ("would X work / which looks better") is a QUESTION: the helper answers
// in words, changes nothing, queues nothing. Owner rules: never paint unasked; questions change nothing. Consumers: js/spb-offline-answer.js route() (cx3Layer), js/spb-pbn.js draw().
// Kill switch: window.SPB_CX3_OFF (classify() then always says 'unspecified', so every caller falls through to the old path).
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
    function answer(text) {
        var intent = classify(text); if (intent.mode !== 'advice') return null;
        var t = String(text || ''), low = t.toLowerCase(), lines = [];
        if (/\bblack\b/.test(low) && /\bgold\b/.test(low)) {
            lines.push('Black and gold can work as a restrained pairing: black provides the quiet base and gold works well as a smaller accent. Too much gold can compete with the numbers and sponsor marks.');
            if (/\bblue\b/.test(low)) lines.push('If you keep blue, let it remain one deliberate part of the scheme rather than scattering blue and gold accents everywhere.');
            if (/\bwhite\b/.test(low)) lines.push('Keep the white marks clear against a dark background, and leave space around them so the gold does not reduce their contrast.');
        }
        if (/\bmatte\b/.test(low) && /\bsatin\b/.test(low)) lines.push('Matte gives a flatter, quieter appearance; satin keeps a softer sheen. Satin gold against matte black can separate the accent through both colour and sheen. Check the actual preview lighting before settling the balance.');
        if (/\b(?:no|without)\s+glitter\b/.test(low)) lines.push('Your no-glitter constraint rules out sparkle effects; a gold colour does not require a glitter finish.');
        if (!lines.length) lines.push('I will not change anything. For a readable scheme, choose one main colour, a smaller accent, and enough contrast around numbers and sponsor marks. When you want something built, name the part and the colour. For a fuller design discussion, connect ChatGPT or Claude.');          // CX3: the fallback now also says nothing is changed (it is also the answer to a command that carried an explicit advice-only boundary)
        lines.push('This is advice from your description, not a visual assessment of the loaded paint. Nothing has been changed or queued.');
        var body = lines.join('\n\n');
        return { cls: 'ANSWER', via: 'design-advice', hits: [{id:'assistant.design_advice', title:'Design advice', score:0}],
            answer: {id:'assistant.design_advice', project_discussion:true, title:'Design advice', text:body, summary:body, how:[], actions:[], related:[], faq:null, shot:null} };
    }
    return {classify: classify, answer: answer};
});
