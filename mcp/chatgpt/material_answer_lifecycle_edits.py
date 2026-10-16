"""Exact proposal: a completed local material fact is not a missing-look prompt."""


def edits(relative):
    if relative == 'js/spb-convo-state.js':
        return [
            ('    // noteRoute: js/spb-offline-answer.js', '''    // ChatGPT review proposal Oct10: completed factual material answers must
    // not infer one material/target from a comparison or leave a soft ask.
    // Caller is the local completed producer, after its actual entry was noted.
    // This retires conversation inference only; it grants no execution target.
    function completeReadOnly(text, entryId, topic) {
        var tr=curTurn();
        if(!on()||!tr||tr.act!=='answer'||tr.change||tr.offer||
            tr.said!==String(text||'').slice(0,300)||S.byEntry[String(entryId)]!=='note')return false;
        tr.targets=[];tr.look=null;S.pending=null;S.lastRes=null;
        if(topic)S.topic={id:String(topic).slice(0,200),turn:tr.turn};
        return true;
    }
    // noteRoute: js/spb-offline-answer.js''', 1),
            ('fromEntry: fromEntry, noteRoute: noteRoute, resolve: resolve, view: view,',
             'fromEntry: fromEntry, noteRoute: noteRoute, completeReadOnly: completeReadOnly, resolve: resolve, view: view,', 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('    function composerPending() {', '''    var _completedMaterialFacts = new WeakMap();
    function completeMaterialAnswer(entry, r, text) {
        var fact=_completedMaterialFacts.get(r);
        if(window.SPB_CX3_OFF||!_completedReadOnlyAnswers.has(r)||!fact)return;
        if(fact.stamp!=null&&(!window.SpbConversationScope||!SpbConversationScope.current(fact.stamp)))return;
        if(window.SpbConvo&&SpbConvo.on()&&SpbConvo.completeReadOnly)SpbConvo.completeReadOnly(text,entry.id,fact.topic);
    }
    function composerPending() {''', 1),
            ('            if (answerLifecycle && !adviceNeedsTarget) _completedReadOnlyAnswers.add(advicePayload);',
             "            if (answerLifecycle && !adviceNeedsTarget) _completedReadOnlyAnswers.add(advicePayload);\n            if (answerLifecycle && !adviceNeedsTarget && editorRead && editorRead.answer && editorRead.answer.editor_topic==='material') {\n                _completedMaterialFacts.set(advicePayload,{topic:editorRead.answer.id,stamp:editorRead.answer.document_stamp});\n                if(editorRead.answer.document_stamp!=null)advicePayload.documentStamp=editorRead.answer.document_stamp;\n            }", 1),
            ('} catch (eCV4) {}', '} catch (eCV4) {} completeMaterialAnswer(entry,r,text);', 1),
            ('} catch (eCV5) {}', '} catch (eCV5) {} completeMaterialAnswer(entry,r,text);', 1),
        ]
    return []
