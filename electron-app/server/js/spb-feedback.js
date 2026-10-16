/* HELPER V3 S9 (local half) 2026-10-06: "this didn't do what I asked" -> output/ai_logs/feedback.jsonl on THIS machine.
 *
 *   window.SpbFeedback.send({ seq, text, reply, comment, undo:{available,done}, convo:[{role,text}] })  -> Promise<{ok,id}|{ok:false}>
 *
 * Everything but `text` is optional: the server finds the matching turn in copilot_turns.jsonl (frame / verify / v3 / report / zones)
 * and fills the rest in. Posts ONLY to this app's own server (a relative URL, /api/ai/feedback); nothing here can leave the machine.
 * Where opt-in feedback may be SENT later is an open owner decision: no sharing code exists in this file.
 * Fire-and-forget safe: send() never throws and never touches the panel. The bubble button is a patch plan (see
 * docs/handoff_reports/HELPER_V3_STAGES.md, "S9 local"), not applied here.
 */
(function (W) {
    'use strict';
    var sent = {};                                   // one report per turn seq per page load (a second tap just updates the note locally)

    function lastTurn() { try { return W.__spbTurnLog || null; } catch (e) { return null; } }       // set by spb-offline-builder.js tlFlush
    function frameNow() { try { var F = W.SpbIntentFrame; return F && F.last ? F.slim(F.last()) : null; } catch (e) { return null; } }
    function undoState(o) {
        o = o || {};
        var avail = o.available;
        if (avail == null) { try { avail = !!(W.spbProAI && W.spbProAI.log && W.spbProAI.log().some(function (m) { return m.role === 'ai' && m.undoable && !m.undone; })); } catch (e) { avail = null; } }
        return { offered: true, available: avail, done: !!o.done, undone_by_button: !!o.undone_by_button };
    }
    function convoNow() {
        try {
            var L = (W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []) || [];
            return L.filter(function (m) { return m.role === 'user' || m.role === 'ai'; }).slice(-6).map(function (m) { return { role: m.role, text: String(m.text || '').slice(0, 1500) }; });
        } catch (e) { return []; }
    }
    function lastUser() { try { var L = (W.spbProAI && W.spbProAI.log ? W.spbProAI.log() : []) || []; for (var i = L.length - 1; i >= 0; i--) if (L[i].role === 'user' && L[i].text) return String(L[i].text); } catch (e) {} return ''; }
    function version() { try { return String((W.SPB_VERSION || (W.__SPB && W.__SPB.version) || '')).slice(0, 40); } catch (e) { return ''; } }

    function send(o) {
        o = o || {};
        try {
            var t = lastTurn(), body = {
                seq: o.seq != null ? o.seq : (t ? t.seq : null),
                text: String(o.text != null ? o.text : (lastUser() || (t ? t.text : ''))).slice(0, 4000),          // the buyer's own words, not the synthetic "Run: ..." text some turn records carry
                reply: o.reply != null ? String(o.reply).slice(0, 6000) : undefined,
                comment: o.comment ? String(o.comment).slice(0, 600) : undefined,
                rating: 'down', source: o.source || 'bubble',
                undo: undoState(o.undo),
                convo: o.convo || convoNow(),
                frame: o.frame || undefined,
                app_version: version() || undefined
            };
            if (body.frame === undefined && t && t.frame) body.frame = t.frame;
            if (!body.text && !body.reply) return Promise.resolve({ ok: false, error: 'nothing_to_report' });
            if (body.seq != null && sent[body.seq] && !o.force) return Promise.resolve({ ok: true, id: sent[body.seq], again: true });
            if (!W.fetch) return Promise.resolve({ ok: false, error: 'no_fetch' });
            return W.fetch('/api/ai/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
                .then(function (r) { return r.json(); })
                .then(function (j) { if (j && j.ok && body.seq != null) sent[body.seq] = j.id; return j; })
                .catch(function (e) { return { ok: false, error: 'network', message: String(e && e.message || e).slice(0, 120) }; });
        } catch (e) { return Promise.resolve({ ok: false, error: 'exception' }); }
    }

    W.SpbFeedback = { send: send, _lastTurn: lastTurn, _sent: function () { return Object.assign({}, sent); } };
})(typeof window !== 'undefined' ? window : globalThis);
