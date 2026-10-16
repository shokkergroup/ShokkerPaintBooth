"""Preserve drafts until scoped inbox acknowledgement; no automatic retry."""


def edits(relative):
    if relative == 'js/spb-ai-connect.js':
        return [
            ('    function relay(text) {', '''    var relayDelivering = false;
    function confirmDelivery(start) {
        return new Promise(function(resolve,reject) {
            var live = true, timer;
            function finish(error,receipt) {
                if (!live) return; live = false; clearTimeout(timer);
                if (error) reject(error); else resolve(receipt);
            }
            timer = setTimeout(function(){finish(new Error('Delivery confirmation timed out.'));},15000);
            try { Promise.resolve(start(function(){return live;})).then(function(r){finish(null,r);},function(e){finish(e);}); }
            catch(e) { finish(e); }
        });
    }
    function relay(text) {''', 1),
            ('    function refreshStatus() {\n        return api', '    function refreshStatus() {\n        var requestedHelper = mode(), requestedScope = docScope;\n        return api', 1),
            ("then(function (s) { S.status = s;", "then(function (s) { if (cx2() && (requestedHelper !== mode() || requestedScope !== docScope)) return null; S.status = s;", 1),
            ("docEpoch++; docScope = docPage + ':' + docEpoch; S.seq = -1;", "docEpoch++; docScope = docPage + ':' + docEpoch; if (cx2()) { S.status = null; S.listening = false; S.client = ''; S.lastReply = 0; } S.seq = -1;", 1),
            ("if (cx2()) { S.waiting = false; S.lastSent = 0; S.lastReply = 0; }", "if (cx2()) { S.waiting = false; S.lastSent = 0; S.lastReply = 0; S.status = null; S.listening = false; S.client = ''; }", 1),
            ('if (relaying() && window.SpbMcpBridge) {', 'if (relaying()) {', 1),
            ('try { window.SpbMcpBridge.setEnabled(false); }', 'try { if (window.SpbMcpBridge) window.SpbMcpBridge.setEnabled(false); }', 1),
            ('if (docScope === selectedScope && mode() === selectedMode && relaying()) window.SpbMcpBridge.setEnabled(true);', 'if (docScope === selectedScope && mode() === selectedMode && relaying() && window.SpbMcpBridge) window.SpbMcpBridge.setEnabled(true);', 1),
            ('entry.documentScope = docScope;', 'entry.documentScope = docScope; entry.relayHelper = mode();', 1),
            ('function useCard(entry, i) { if (!entry || entry.documentScope !== docScope) return;', 'function useCard(entry, i) { if (!relaying() || !entry || entry.documentScope !== docScope || (cx2() && entry.relayHelper !== mode())) return;', 1),
            ("else if (act === 'aic-more') say('Show me more options like these');", """else if (act === 'aic-more') {
            var moreId = b && b.getAttribute('data-id'), moreLog = P().log ? P().log() : [];
            var moreEntry = moreLog.find(function(e){return e && String(e.id) === String(moreId);});
            if (relaying() && moreId && moreEntry && moreEntry.documentScope === docScope && (!cx2() || moreEntry.relayHelper === mode())) say('Show me more options like these');
        }""", 1),
            ('    function relay(text) {\n        var expectedScope', "    function relay(text) {\n        if (!relaying()) return Promise.resolve({ok:false,reason:'helper_changed'});\n        var expectedScope", 1),
            ("    function say(text) { push({ role: 'user', text: text }); relay(text); }", "    function say(text) { if (!relaying() || relayDelivering) return; push({ role: 'user', text: text }); return relay(text); }", 1),
            ("if (!relaying()) return Promise.resolve({ok:false,reason:'helper_changed'});", "if (!relaying()) return Promise.resolve({ok:false,reason:'helper_changed'});\n        if (relayDelivering) return Promise.resolve({ok:false,reason:'delivery_pending'});\n        relayDelivering = true;", 1),
            ('        return (docReady || registerDocument()).then(function(scope) {', '        return confirmDelivery(function(live){return (docReady || registerDocument()).then(function(scope) {\n            if (!live()) throw new Error(\'Delivery confirmation expired; request was not sent.\');', 1),
            ("{ text: text }) }); }).then(function (j) {", "{ text: text }) }); }); }).then(function (j) {", 1),
            ("}).then(function (j) {\n            if (expectedScope", "}).then(function (j) {\n            relayDelivering = false;\n            if (expectedScope", 1),
            ('if (expectedScope !== docScope || expectedHelper !== mode()) return;\n            if (!j || j.ok === false)', "if (expectedScope !== docScope || expectedHelper !== mode()) return {ok:false,reason:'scope_changed'};\n            if (!j || j.ok === false || (cx2() && !noticeSeq(j.seq)))", 1),
            ("(j && j.message) || 'Could not send that to ' + name() + '.' }); return;", "(j && j.message) || 'Could not confirm delivery to ' + name() + '. Your draft is kept; check the connected chat before sending again.' }); redraw(); return {ok:false,reason:'delivery_unconfirmed'};", 1),
            ("if (!j.listening) relayNotice(j, expectedHelper, expectedScope);\n            redraw();", "if (!j.listening) relayNotice(j, expectedHelper, expectedScope);\n            redraw(); return {ok:true,seq:j.seq,helper:expectedHelper,document_scope:expectedScope};", 1),
            ("function (error) { if (expectedScope !== docScope || expectedHelper !== mode()) return; docReady = null; S.waiting = false; push({ role: 'err', text: error.message || 'Could not reach the Shokker server.' }); });", "function (error) { relayDelivering = false; if (expectedScope !== docScope || expectedHelper !== mode()) return {ok:false,reason:'scope_changed'}; docReady = null; S.waiting = false; push({ role: 'err', text: (error.message || 'Could not reach the Shokker server.') + ' Your draft is kept; check the connected chat before sending again.' }); redraw(); return {ok:false,reason:'delivery_unconfirmed'}; });", 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('data-act="aic-more">Show me more', '''data-act="aic-more" data-id="' + m.id + '">Show me more''', 1),
            ('    var _composerFinishing = 0, _composerHeldDraft = false;', '    var _composerFinishing = 0, _composerHeldDraft = false, _relaySending = false;', 1),
            ('return !!(_busy || _composerFinishing || composerSourceLoading());', 'return !!(_busy || _composerFinishing || _relaySending || composerSourceLoading());', 1),
            ("button.textContent = pending ? (sourceLoading ? 'Loading paint…' : (checking ? 'Checking…' : 'Working…')) : 'Send';", "button.textContent = pending ? (sourceLoading ? 'Loading paint…' : (_relaySending ? 'Sending…' : (checking ? 'Checking…' : 'Working…'))) : 'Send';", 1),
            ("button.title = pending ? (sourceLoading ? 'Your draft stays here. Send it when the paint finishes loading.' : 'Your message stays here. Send it when this change finishes.') : 'Send your message';", "button.title = pending ? (sourceLoading ? 'Your draft stays here. Send it when the paint finishes loading.' : (_relaySending ? 'Your draft stays here until delivery is confirmed.' : 'Your message stays here. Send it when this change finishes.')) : 'Send your message';", 1),
            ("status.textContent = pending ? (sourceLoading ? 'The paint is loading. You can write your question; send it when loading finishes.' : (checking ? 'Checking the change. You can write your next message.' : 'Working. You can write your next message.')) : '';", "status.textContent = pending ? (sourceLoading ? 'The paint is loading. You can write your question; send it when loading finishes.' : (_relaySending ? 'Confirming delivery. Your draft stays here; nothing is resent automatically.' : (checking ? 'Checking the change. You can write your next message.' : 'Working. You can write your next message.'))) : '';", 1),
            ("if (window.SpbAiConnect && SpbAiConnect.relaying()) { text = String(text || '').trim(); if (!text) return; _log.push({ role: 'user', text: text }); var inpR = _panel && _panel.querySelector('.spb-pai-input'); if (inpR) inpR.value = ''; render(); SpbAiConnect.relay(text); return; }", """if (window.SpbAiConnect && SpbAiConnect.relaying()) {
            text = String(text || '').trim(); if (!text || _relaySending) return;
            _log.push({ role: 'user', text: text });
            var inpR = _panel && _panel.querySelector('.spb-pai-input'), sentDraft = inpR ? inpR.value : null;
            _relaySending = true; composerSync(); render();
            function relayDone(receipt) {
                var inputNow = _panel && _panel.querySelector('.spb-pai-input');
                if (receipt && receipt.ok && inputNow && sentDraft !== null && String(sentDraft).trim() === text && inputNow.value === sentDraft) inputNow.value = '';
                else if (!receipt || !receipt.ok) _log.push({role:'note',text:'Delivery was not confirmed for the selected helper and paint. Your draft is kept. Check the connected chat before sending again.'});
                _relaySending = false; _composerHeldDraft = !!(inputNow && String(inputNow.value || '').trim()); composerSync(); render();
                return receipt;
            }
            return Promise.resolve().then(function(){return SpbAiConnect.relay(text);}).then(relayDone,function(){return relayDone({ok:false,reason:'delivery_unconfirmed'});});
        }""", 1),
        ]
    return []
