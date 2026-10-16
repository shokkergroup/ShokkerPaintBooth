"""Completed read-only cards are answers; missing targets remain clarifications."""


def edits(relative):
    if relative != 'js/spb-pro-ai.js':
        return []
    return [
        ('    function composerPending() {', '    var _completedReadOnlyAnswers = new WeakSet(); // local producer identity; never restored from JSON\n    function composerPending() {', 1),
        ('            var adviceResult = finish({offline:true,design_proposals:', '''            var answerLifecycle = !window.SPB_CX3_OFF;
            var adviceNeedsTarget = !!(editorRead && editorRead.answer && editorRead.answer.needs_pattern_target);
            // These local producers already returned a non-executable answer.
            // Use the existing route completion: retire the legacy pending slot,
            // record the answer topic, and keep real target clarifications open.
            if (answerLifecycle) { try {
                if (window.SpbConvo && SpbConvo.on()) {
                    // Separate Send events may repeat identical words within
                    // the store's 3-second producer-dedup window.
                    send._answerTurnSeq = (send._answerTurnSeq || 0) + 1;
                    SpbConvo.turn(text, {producer:'offline',turn:'answer-' + Date.now() + '-' + send._answerTurnSeq});
                    SpbConvo.noteRoute({cls:adviceNeedsTarget?'ASK':'ANSWER',topic:designAdvice.answer && designAdvice.answer.id}, text);
                }
            } catch(eAnswerLifecycle) {} }
            var advicePayload = {offline:true,design_proposals:''', 1),
        ("builder:false,howto:false,asked:{options:[]},metaText:inventoryRead ? '✦ loaded layer reading · no AI used' : '✦ built-in guidance · no AI used'}, text, 'ask');", "builder:false,howto:false,asked:(!answerLifecycle || adviceNeedsTarget)?{question:adviceNeedsTarget?editorRead.answer.text:undefined,options:[]}:undefined,metaText:inventoryRead ? '✦ loaded layer reading · no AI used' : '✦ built-in guidance · no AI used'};\n            if (answerLifecycle && !adviceNeedsTarget) _completedReadOnlyAnswers.add(advicePayload);\n            var adviceResult = finish(advicePayload, text, (answerLifecycle && !adviceNeedsTarget)?'noaction':'ask');", 1),
        ("&& !r.advice) entry.noChange = true;", "&& !r.advice && !_completedReadOnlyAnswers.has(r)) entry.noChange = true;", 1),
    ]
