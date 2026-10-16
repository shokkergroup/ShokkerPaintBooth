"""Live factual answers take precedence over generic design advice."""
def edits(relative):
    if relative == 'js/spb-pro-ai.js':
        return [
            ('        var adviceBuilder = window.SpbOfflineBuilder;', '''        var adviceBuilder = window.SpbOfflineBuilder;
        var editorRead = !_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && adviceBuilder && adviceBuilder.offlineMode() && window.SpbEditorCapabilities ? SpbEditorCapabilities.answer(text, SpbEditorCapabilities.previousFrom(adviceBuilder.state && adviceBuilder.state(), _log)) : null;''', 1),
            ('        if (inventoryRead) designAdvice = inventoryRead;', '        if (editorRead) designAdvice = editorRead;\n        else if (inventoryRead) designAdvice = inventoryRead;', 1),
            ('if (!inventoryRead && designAdvice &&', 'if (!editorRead && !inventoryRead && designAdvice &&', 1),
            ('            adviceBuilder.showAnswer(designAdvice, text);', '            if (editorRead) editorRead.in_chat = true;\n            adviceBuilder.showAnswer(designAdvice, text);', 1),
            ('text:inventoryRead ? (pixelRead ?', "text:editorRead ? editorRead.answer.text : inventoryRead ? (pixelRead ?", 1),
            ('            return finish({offline:true,design_proposals:SpbDesignIntent.discussion(designAdvice)', '            var adviceResult = finish({offline:true,design_proposals:SpbDesignIntent.discussion(designAdvice)', 1),
            ("builder:false,howto:false,asked:{options:[]},metaText:inventoryRead ? '✦ loaded layer reading · no AI used' : '✦ built-in guidance · no AI used'}, text, 'ask');", "builder:false,howto:false,asked:{options:[]},metaText:inventoryRead ? '✦ loaded layer reading · no AI used' : '✦ built-in guidance · no AI used'}, text, 'ask');\n            // Reconcile the suggestion panel after finish redraws the answer.\n            // Its normal input signature may otherwise retain the previous question.\n            if (window.SpbPbn && SpbPbn.draw) SpbPbn.draw();\n            return adviceResult;", 1),
        ]
    if relative == 'js/spb-offline-builder.js':
        return [
            ("r.answer.id === 'assistant.template_layers'", "r.answer.id === 'assistant.live_editor_capabilities' || r.answer.id === 'assistant.template_layers'", 1),
            ('        else if (S.answer && W.SpbOfflineAnswer && W.SpbOfflineAnswer.cardHtml)', '        else if (S.answer && S.answer.in_chat && S.answer.answer && S.answer.answer.id === "assistant.live_editor_capabilities") { /* Factual answer lives in its chat turn; retain the card state only for scoped follow-ups. */ }\n        else if (S.answer && W.SpbOfflineAnswer && W.SpbOfflineAnswer.cardHtml)', 1),
            ("else if (!(S.answer && S.answer.via === 'design-advice'))", "else if (!(S.answer && (S.answer.via === 'design-advice' || (S.answer.in_chat && S.answer.answer && S.answer.answer.id === 'assistant.live_editor_capabilities'))))", 1),
        ]
    if relative == 'js/spb-offline-answer.js':
        return [("A.id === 'assistant.design_advice'", "A.id === 'assistant.design_advice' || A.id === 'assistant.live_editor_capabilities'", 1)]
    if relative == 'js/spb-pbn.js':
        return [("readAns3.id === 'assistant.design_advice'", "readAns3.id === 'assistant.design_advice' || readAns3.id === 'assistant.live_editor_capabilities'", 1)]
    return []
