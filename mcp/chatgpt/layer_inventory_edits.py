"""Read current-layer inventories before legacy design/edit routing."""
def edits(relative):
    if relative == 'js/spb-offline-builder.js':
        return [("if (r && r.via === 'design-advice')", "if (r && (r.via === 'design-advice' || (r.answer && r.answer.id === 'assistant.template_layers')))", 1)]
    if relative == 'js/spb-pbn.js':
        return [('        if (W.SpbDesignIntent && W.SpbDesignIntent.classify(S.text).mode', '''        var readState = B && B.state ? B.state() : null;
        var readAnswer = readState && readState.answer && readState.answer.answer;
        if (readAnswer && (readAnswer.id === 'assistant.template_layers' || readAnswer.id === 'assistant.design_advice') && !String(readState.liveText || '').trim() && !(readState.steps || []).length) { CUR = null; off = true; }
        if (W.SpbDesignIntent && W.SpbDesignIntent.classify(S.text).mode''', 1)]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('        var adviceBuilder = window.SpbOfflineBuilder;', '''        var adviceBuilder = window.SpbOfflineBuilder;
        var inventoryRead = !_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && adviceBuilder && adviceBuilder.offlineMode() && !window.SPB_CARKB_OFF && window.SpbTemplateLayers && SpbTemplateLayers.inventoryQuestion(text) && window.SpbCarReferenceAnswer && SpbCarReferenceAnswer.readOnlyQuestion(text);''', 1),
            ('if (designAdvice && !window.SPB_CARKB_OFF', 'if (inventoryRead) designAdvice = inventoryRead;\n        if (!inventoryRead && designAdvice && !window.SPB_CARKB_OFF', 1),
            ("text:'The '+(designAdvice.answer.title || 'Design advice')+' card below discusses your colours and finishes. Nothing has been changed or queued.'", "text:inventoryRead ? 'The Loaded layers card below lists the current groups and name examples. Nothing has been changed or queued.' : 'The '+(designAdvice.answer.title || 'Design advice')+' card below discusses your colours and finishes. Nothing has been changed or queued.'", 1),
            ("metaText:'✦ built-in guidance · no AI used'", "metaText:inventoryRead ? '✦ loaded layer reading · no AI used' : '✦ built-in guidance · no AI used'", 1),
        ]
    if relative != 'js/spb-offline-answer.js':
        return []
    return [
        ("        h += '<div class=\"spb-ob-tsum\">' + esc(A.text) + '</div>';", "        h += '<div class=\"spb-ob-tsum\"' + ((A.id === 'assistant.template_layers' || A.id === 'assistant.design_advice') ? ' style=\"white-space:pre-line\"' : '') + '>' + esc(A.text) + '</div>';", 1),
        ('        var advice = W.SpbDesignIntent && W.SpbDesignIntent.answer(text); if (advice) {', '''        var inventoryRead = !W.SPB_CARKB_OFF && W.SpbTemplateLayers && W.SpbTemplateLayers.inventoryQuestion(text) && W.SpbCarReferenceAnswer && W.SpbCarReferenceAnswer.readOnlyQuestion(text);
        if (inventoryRead) return inventoryRead;
        var advice = W.SpbDesignIntent && W.SpbDesignIntent.answer(text); if (advice) {''', 1),
    ]
