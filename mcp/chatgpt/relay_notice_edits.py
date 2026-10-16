"""Retire only locally created waiting notes acknowledged by this relay's answer."""

HELPERS = '''    // CX3: connection notes are transient UI, not assistant answers or edit authority.
    // Keep object identity local: a saved/restored note cannot acquire this lifecycle.
    var relayNotices = [], answeredNotice = null;
    function noticeOn() { return cx2() && !window.SPB_CX3_OFF; }
    function noticeSeq(seq) { return typeof seq === 'number' && isFinite(seq) && seq > 0 && Math.floor(seq) === seq; }
    function pruneRelayNotices() {
        if (!P().log) return;
        var log = P().log();
        relayNotices = relayNotices.filter(function(n) { return log.indexOf(n.entry) >= 0; });
    }
    function retireRelayNotices(e, helper, scope) {
        if (!noticeOn() || !e || !noticeSeq(e.reply_to) || e.document_scope !== scope || (e.helper && e.helper !== helper)) return;
        pruneRelayNotices();
        relayNotices.forEach(function(n) {
            if (n.helper === helper && n.scope === scope && n.seq <= e.reply_to) n.retired = true;
        });
        if (!answeredNotice || answeredNotice.helper !== helper || answeredNotice.scope !== scope)
            answeredNotice = {helper:helper, scope:scope, seq:e.reply_to};
        else answeredNotice.seq = Math.max(answeredNotice.seq, e.reply_to);
    }
    function relayNotice(j, helper, scope) {
        if (noticeOn() && noticeSeq(j.seq) && answeredNotice && answeredNotice.helper === helper && answeredNotice.scope === scope && answeredNotice.seq >= j.seq) return;
        var entry = {role:'note', text:name(helper) + ' is not listening yet, so your message is waiting for it. In ' + name(helper) + ' type: “' + LISTEN_LINE + '”. It will pick this message up straight away.'};
        if (noticeOn() && noticeSeq(j.seq)) {
            pruneRelayNotices();
            relayNotices.push({entry:entry, helper:helper, scope:scope, seq:j.seq, retired:false});
        }
        push(entry);
    }
    function hideRelayNotice(entry) {
        if (!noticeOn()) return false;
        return relayNotices.some(function(n) { return n.entry === entry && n.retired; });
    }
'''


def edits(relative):
    if relative == 'js/spb-ai-connect.js':
        return [
            ('    function setMode(m) {', HELPERS + '\n    function setMode(m) {', 1),
            ("else if (e.role === 'assistant') { S.waiting = false;", "else if (e.role === 'assistant') { retireRelayNotices(e, requestedHelper, requestedScope); S.waiting = false;", 1),
            ('        var expectedScope = docScope;\n        S.waiting', '        var expectedScope = docScope, expectedHelper = mode();\n        S.waiting', 1),
            ("            if (scope !== docScope || expectedScope !== docScope) throw new Error('The open paint changed. Send your request again.');", "            if (scope !== docScope || expectedScope !== docScope || expectedHelper !== mode()) throw new Error('The open paint or selected helper changed. Send your request again.');", 1),
            ("{ text: text, helper: mode(), document_scope: expectedScope }", "{ text: text, helper: expectedHelper, document_scope: expectedScope }", 1),
            ('            if (expectedScope !== docScope) return;', '            if (expectedScope !== docScope || expectedHelper !== mode()) return;', 1),
            ("            if (!j.listening) push({ role: 'note', text: name() + ' is not listening yet, so your message is waiting for it. In ' + name() + ' type: “' + LISTEN_LINE + '”. It will pick this message up straight away.' });", '            if (!j.listening) relayNotice(j, expectedHelper, expectedScope);', 1),
            ('function (error) { if (expectedScope !== docScope) return;', 'function (error) { if (expectedScope !== docScope || expectedHelper !== mode()) return;', 1),
            ('window.SpbAiConnect = { documentScope:', 'window.SpbAiConnect = { hideRelayNotice: hideRelayNotice, documentScope:', 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        return [
            ("        _log.forEach(function (m) {\n            if (m.role === 'user')", "        _log.forEach(function (m) {\n            if (window.SpbAiConnect && SpbAiConnect.hideRelayNotice && SpbAiConnect.hideRelayNotice(m)) return;\n            if (m.role === 'user')", 1),
        ]
    return []
