"""Concise template answers and current-document reference follow-ups."""

def edits(relative):
    if relative == 'js/spb-offline-answer.js':
        return [
            ("if (r.cls === 'ANSWER') { Bb.showAnswer(r, text); var at", "if (r.cls === 'ANSWER') { Bb.showAnswer(r, text); if (!W.SPB_CX3_OFF && r.answer.chat_summary) return reply(r,r.answer.chat_summary); var at", 1),
            ("        if (!r) return '';\n        if (r.cls === 'ONLINE')", "        if (!r) return '';\n        var referenceCard = !W.SPB_CX3_OFF && !W.SPB_CARKB_OFF && W.SpbCarReferenceAnswer && W.SpbCarReferenceAnswer.cardHtml && W.SpbCarReferenceAnswer.cardHtml(r);\n        if (referenceCard) return referenceCard;\n        if (r.cls === 'ONLINE')", 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('        if (editorRead) designAdvice = editorRead;', '''        var referenceRead = !_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && adviceBuilder && adviceBuilder.offlineMode() && !window.SPB_CARKB_OFF && !window.SPB_CX3_OFF && window.SpbCarReferenceAnswer && SpbCarReferenceAnswer.followup && window.SpbEditorCapabilities ? SpbCarReferenceAnswer.followup(text,SpbEditorCapabilities.previousFrom(adviceBuilder.state && adviceBuilder.state(),_log)) : null;
        if (referenceRead) designAdvice = referenceRead;
        if (editorRead) designAdvice = editorRead;''', 1),
            ('if (!editorRead && !inventoryRead && designAdvice &&', 'if (!referenceRead && !editorRead && !inventoryRead && designAdvice &&', 1),
            ('text:editorRead ? editorRead.answer.text : inventoryRead ?', 'text:editorRead ? editorRead.answer.text : referenceRead ? (referenceRead.answer.chat_summary || referenceRead.answer.text) : inventoryRead ?', 1),
        ]
    if relative == 'js/spb-offline-builder.js':
        return [("S.answer.via === 'design-advice' || (S.answer.in_chat", "S.answer.via === 'design-advice' || (S.answer.answer && S.answer.answer.chat_summary) || (S.answer.in_chat", 1)]
    if relative == 'js/spb-pbn.js':
        return [("readAns3.id === 'assistant.design_advice'", "readAns3.chat_summary || readAns3.id === 'assistant.design_advice'", 1)]
    return []
