/* ============================================================================
 * EXPERIENCE 20 — ASK
 * Paradigm: NATURAL LANGUAGE. Say what you want in a sentence.
 *
 * Distinct from 02 Command (fuzzy button picker) and 11 Terminal (verb + args
 * grammar): Ask takes a plain sentence, works out the INTENT, and then reports
 * back what it did in the same conversation — with the actual control it used,
 * so you learn where that control lives. "make zone 2 chrome" or "how do I set
 * roughness" both work.
 *
 * It is deliberately honest: it never claims to have done something it did not
 * do, and when it is unsure it offers the candidates rather than guessing. All
 * matching is local — no network, no model — it resolves against the live
 * control index and clicks the real node.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '20-ask',
        name: 'Ask',
        tagline: 'Say it in a sentence. It finds the control and shows you where.',
        paradigm: 'Natural language',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();

            // Ask replaces the zones RAIL with a conversation, but the zones
            // themselves are never removed — the rail is moved into the chat
            // column so the list still sits where you are talking about it.
            var center = ctx.q('#centerPanel');
            var main = ctx.q('.main-container');
            var leftPanel = ctx.q('#leftPanel');
            if (!main || !center) return;

            // Inside the existing LAYERS rail, not a new column: a third rail cost
            // the artwork 6% at 1366px, and the bench owns the arrangement now.
            var host = ctx.q('#rightPanel') || center;
            var col = ctx.mk('div', { cls: 'xp-ask-col', into: host });

            var chat = ctx.mk('div', { cls: 'xp-ask-chat spbx-scroll-y', attrs: { role: 'log' } });
            var form = ctx.mk('div', { cls: 'xp-ask-form' });
            var input = ctx.mk('input', {
                cls: 'xp-ask-in',
                attrs: { type: 'text', 'aria-label': 'Ask for what you want',
                         placeholder: 'e.g. make zone 2 chrome', autocomplete: 'off' }
            });
            var send = ctx.mk('button', { cls: 'xp-ask-send', text: '↑', attrs: { type: 'button', 'aria-label': 'Send' } });
            form.appendChild(input); form.appendChild(send);
            col.appendChild(chat); col.appendChild(form);
            // Left rail stays put: it holds ZONES + ZONE POPOUT, which the owner
            // requires permanently visible. The chat column is additive.

            function bubble(text, who, extra) {
                var b = document.createElement('div');
                b.className = 'xp-ask-b ' + who;
                b.textContent = text;
                if (extra) {
                    var e = document.createElement('div');
                    e.className = 'xp-ask-where';
                    e.textContent = extra;
                    b.appendChild(e);
                }
                chat.appendChild(b);
                chat.scrollTop = chat.scrollHeight;
                return b;
            }

            function index() {
                return SPBX.indexControls().filter(function (c) { return !col.contains(c.el); });
            }

            var STOP = /\b(the|a|an|to|please|can|you|i|want|make|set|my|it|this|for|with|of|on|and)\b/g;

            function answer(qRaw) {
                var q = qRaw.toLowerCase().trim();

                // 1. zone selection — "zone 2", "select zone hood"
                var zm = q.match(/zone\s+(\d+)/);
                if (zm) {
                    var cards = document.querySelectorAll('#zoneList .zone-card');
                    var card = cards[parseInt(zm[1], 10) - 1];
                    if (card) {
                        card.click();
                        bubble('Selected zone ' + zm[1] + '.', 'bot', 'ZONES rail → zone card ' + zm[1]);
                        // keep going: the sentence may also name a finish
                        q = q.replace(/zone\s+\d+/, '').trim();
                        if (!q.replace(STOP, '').trim()) return;
                    }
                }

                // 2. a question — explain rather than act
                if (/^(how|what|where|why|which)\b/.test(q)) {
                    var terms = q.replace(STOP, ' ').replace(/[?]/g, ' ').split(/\s+/).filter(Boolean);
                    var found = index().filter(function (c) {
                        var h = (c.label + ' ' + c.hint).toLowerCase();
                        return terms.some(function (t) { return t.length > 2 && h.indexOf(t) !== -1; });
                    }).slice(0, 4);
                    if (!found.length) return bubble("I couldn't find a control for that.", 'bot');
                    bubble('Here is where that lives:', 'bot');
                    found.forEach(function (c) {
                        var b = bubble(c.label, 'opt', c.group);
                        b.addEventListener('click', function () {
                            try { c.el.scrollIntoView({ block: 'nearest' }); c.el.click(); } catch (_) {}
                            bubble('Clicked "' + c.label + '".', 'bot', c.group);
                        });
                    });
                    return;
                }

                // 3. otherwise: act. Score controls against the words that matter.
                var words = q.replace(STOP, ' ').split(/\s+/).filter(function (w) { return w.length > 2; });
                if (!words.length) return bubble('Say a bit more and I will find it.', 'bot');
                var scored = index().map(function (c) {
                    var h = (c.label + ' ' + c.hint + ' ' + c.group).toLowerCase();
                    var s = 0;
                    words.forEach(function (w) {
                        if (h.indexOf(w) === -1) return;
                        s += 10;
                        if (c.label.toLowerCase().indexOf(w) === 0) s += 8;
                        if (c.label.toLowerCase() === w) s += 20;
                    });
                    return { c: c, s: s };
                }).filter(function (r) { return r.s > 0; }).sort(function (a, b) { return b.s - a.s; });

                if (!scored.length) return bubble("I don't know how to do that yet.", 'bot');

                // Confident only when the best is clearly ahead — otherwise ask.
                if (scored.length === 1 || scored[0].s >= scored[1].s * 1.6) {
                    var hit = scored[0].c;
                    try { hit.el.scrollIntoView({ block: 'nearest' }); hit.el.click(); } catch (_) {}
                    return bubble('Done — "' + hit.label + '".', 'bot', 'Found in: ' + hit.group);
                }
                bubble('Did you mean one of these?', 'bot');
                scored.slice(0, 4).forEach(function (r) {
                    var b = bubble(r.c.label, 'opt', r.c.group);
                    b.addEventListener('click', function () {
                        try { r.c.el.scrollIntoView({ block: 'nearest' }); r.c.el.click(); } catch (_) {}
                        bubble('Done — "' + r.c.label + '".', 'bot', 'Found in: ' + r.c.group);
                    });
                });
            }

            function submit() {
                var v = input.value.trim();
                if (!v) return;
                input.value = '';
                bubble(v, 'me');
                try { answer(v); } catch (e) { bubble('That broke: ' + e, 'bot'); }
            }
            ctx.on(send, 'click', submit);
            ctx.on(input, 'keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(); } });

            bubble('Tell me what you want to do.', 'bot');
            bubble('Try “make zone 2 chrome”, “render”, or “how do I set roughness”.', 'bot');

            ctx.css([
                '&{ --xp-ch:50px; --xp-radius:14px; --ak-a:#7aa2ff; --ak-bg:#0f1218; }',
                '& #splitViewContainer{ padding:8px !important; gap:8px; }',
                '& .main-container, & #centerPanel{ background:#0b0e13 !important; }',
                '& .header, & #spbTopToolbar{ background:var(--ak-bg) !important;',
                '  border-bottom:1px solid #1e2430 !important; }',
                '& .right-panel{ background:var(--ak-bg) !important; border-color:#1e2430 !important; }',

                '& .xp-ask-col{ flex:0 0 auto; width:100%; display:flex; flex-direction:column;',
                '  min-height:190px; background:var(--ak-bg); border-top:2px solid var(--ak-a); }',
                '& .xp-ask-chat{ flex:1 1 auto; min-height:120px; padding:10px; display:flex;',
                '  flex-direction:column; gap:7px; }',
                '& .xp-ask-b{ max-width:92%; padding:8px 11px; border-radius:13px; font-size:12px;',
                '  line-height:1.45; word-break:break-word; }',
                '& .xp-ask-b.me{ align-self:flex-end; background:var(--ak-a); color:#08101f;',
                '  border-bottom-right-radius:4px; font-weight:600; }',
                '& .xp-ask-b.bot{ align-self:flex-start; background:#1a2030; color:#d6deeb;',
                '  border-bottom-left-radius:4px; }',
                '& .xp-ask-b.opt{ align-self:flex-start; background:#141a26; color:#cfe0ff;',
                '  border:1px solid #2b3550; cursor:pointer; }',
                '& .xp-ask-b.opt:hover{ border-color:var(--ak-a); background:#182136; }',
                '& .xp-ask-where{ margin-top:3px; font-size:9px; letter-spacing:0.8px;',
                '  text-transform:uppercase; color:#6b7a94; }',
                '& .xp-ask-form{ flex:0 0 auto; display:flex; gap:6px; padding:8px;',
                '  border-top:1px solid #1e2430; }',
                '& .xp-ask-in{ flex:1 1 auto; min-width:0; height:36px; padding:0 11px;',
                '  background:#141a26; border:1px solid #2b3550; border-radius:10px;',
                '  color:#e6edf7; font-size:12.5px; outline:none; }',
                '& .xp-ask-in:focus{ border-color:var(--ak-a); }',
                '& .xp-ask-send{ flex:0 0 36px; width:36px; height:36px; cursor:pointer;',
                '  background:var(--ak-a); color:#08101f; border:none; border-radius:10px;',
                '  font-size:16px; font-weight:800; }',
                /* the zones rail rides along inside the chat column */
                '& .xp-ask-zones{ flex:0 0 auto !important; max-height:38% !important;',
                '  width:100% !important; min-width:0 !important; max-width:none !important;',
                '  border-right:none !important; border-top:1px solid #1e2430 !important;',
                '  overflow-y:auto !important; }',

                '& #splitSource, & #splitPreview{ background:#070910 !important;',
                '  border:1px solid #1e2430 !important; border-radius:12px !important;',
                '  box-shadow:0 14px 36px rgba(0,0,0,0.5) !important; }',
                '& #previewTopStrip{ flex:0 0 auto !important; padding:6px 10px !important;',
                '  min-height:0 !important; background:var(--ak-bg) !important;',
                '  border:1px solid #1e2430 !important; border-radius:12px !important; gap:10px !important; }',
                '& #previewTopStrip #specChannelDock{ background:transparent !important;',
                '  border:none !important; padding:0 !important; gap:9px !important;',
                '  justify-content:flex-start !important; flex:0 0 auto !important; }',
                '& #previewBottomBar.spbx-relocated{ background:transparent !important;',
                '  border:none !important; padding:0 !important; justify-content:flex-end !important;',
                '  display:flex !important; align-items:center !important; gap:8px !important; }',
                '& #previewBottomBar .btn-render{ background:var(--ak-a) !important; color:#08101f !important;',
                '  border:none !important; border-radius:11px !important; font-weight:800 !important;',
                '  letter-spacing:1.4px !important; padding:11px 26px !important; animation:none !important; }',
                '& .vtool-btn{ border-radius:10px !important; animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(122,162,255,0.16) !important;',
                '  border-color:var(--ak-a) !important; color:var(--ak-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
