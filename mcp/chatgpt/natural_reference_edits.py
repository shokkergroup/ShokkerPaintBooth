"""First factual car question waits for local evidence, then answers in chat."""


def edits(relative):
    if relative == 'js/spb-offline-builder.js':
        return [('function showAnswer(r, text) { if (!W.SPB_CX3_OFF && r && (r.via === \'design-advice\' || (r.answer && (', 'function showAnswer(r, text) { if (!W.SPB_CX3_OFF && r && (r.via === \'design-advice\' || (r.answer && (r.answer.reference_context || ', 1)]
    if relative != 'js/spb-pro-ai.js':
        return []
    return [
        ('        // Advice is handled before option-pick / complaint / edit parsers.', '''        // A cold car index cannot answer a named template question yet.
        // Wait once using the existing local loader; retain a newly typed draft.
        var carReader = window.SpbCarReferenceAnswer, carBuilder = window.SpbOfflineBuilder;
        var carReadWanted = !window.SPB_CX3_OFF && !window.SPB_CARKB_OFF && !_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && carBuilder && carBuilder.offlineMode() && carReader && carReader.isReferenceQuestion(text);
        var carReadWait = carReadWanted && window.SpbOfflineReady ? SpbOfflineReady.wait(window.SpbOfflineAnswer) : null;
        if (carReadWait) {
            var carReadEpoch = window.SpbConversationScope ? SpbConversationScope.stamp() : null;
            _cancelOpts = false; _busy = true; _progress = 'Loading car template reference…'; render(); composerSync();
            return carReadWait.then(function () {
                _busy = false; _progress = '';
                if (_cancelOpts || window.SPB_CX3_OFF || window.SPB_CARKB_OFF || !carBuilder.offlineMode() || (window.SpbAiConnect && SpbAiConnect.relaying()) || (carReadEpoch !== null && SpbConversationScope.stamp() !== carReadEpoch)) {
                    _log.push({role:'note',text:'The helper or open document changed while the car reference loaded. Please send your question again.'}); render(); composerSync(); return;
                }
                var draftInput = _panel && _panel.querySelector('.spb-pai-input'), nextDraft = draftInput && String(draftInput.value || '');
                var keepDraft = nextDraft && nextDraft !== String(text || '');
                var answered = send(text, o);
                if (keepDraft) {
                    draftInput = _panel && _panel.querySelector('.spb-pai-input');
                    if (draftInput && !draftInput.value) draftInput.value = nextDraft;
                    _composerHeldDraft = true; composerSync();
                }
                return answered;
            }, function (error) { _busy = false; _progress = ''; _log.push({role:'note',text:error.message}); render(); composerSync(); });
        }
        // Advice is handled before option-pick / complaint / edit parsers.''', 1),
        ('? SpbCarReferenceAnswer.followup(text,SpbEditorCapabilities.previousFrom(adviceBuilder.state && adviceBuilder.state(),_log)) : null;', '? (SpbCarReferenceAnswer.followup(text,SpbEditorCapabilities.previousFrom(adviceBuilder.state && adviceBuilder.state(),_log)) || SpbCarReferenceAnswer.readOnlyQuestion(text)) : null;', 1),
    ]
