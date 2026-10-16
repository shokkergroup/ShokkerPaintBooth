/* ============================================================================
   SPB AI CONNECT — which helper answers the in-app chat box  (APPCHAT 2026-10-09)
   Owner (live playtest 2026-10-09): "take out the OpenRouter AI part and ONLY have Claude MCP, Codex/ChatGPT MCP and the Offline Helper. The AI button asks
   which one, shows HOW to connect, and once linked you chat INSIDE the app's chat box OR in Claude, either one."
     offline  = the built-in Offline Helper (no setup, default answer for anything typed while nothing is chosen)
     claude   = Claude Desktop / Claude Code through the Shokker MCP extension
     chatgpt  = ChatGPT / Codex through the same MCP server
   With claude / chatgpt chosen, a message typed in the app goes to POST /api/mcp/inbox; the assistant gets it at once (it is blocked on spb_wait_for_message,
   or Claude Code's background wait-inbox.js wakes it) and its spb_reply comes back on GET /api/mcp/chat (long-poll) as the AI bubble.
   Used by js/spb-pro-ai.js (render / send / click hooks). ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var KEY = 'spb_ai_helper', BASE = window.SPB_AI_BASE || '';
    var S = { seq: 0, polling: false, waiting: false, listening: false, client: '', lastSent: 0, lastReply: 0, status: null, step: false };
    var docPage = window.crypto.randomUUID(), docEpoch = 0, docScope = docPage + ':0', docReady = null;
    function registerDocument() {
        var expected = docScope;
        docReady = api('/api/mcp/document', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page:docPage,epoch:docEpoch})}).then(function(j) {
            if (expected !== docScope) throw new Error('The open paint changed. Send your request again.');
            if (!j || !j.ok || j.document_scope !== expected) throw new Error('Could not bind the assistant to the open paint. Send your request again.');
            S.seq = j.seq || -1; S.readyScope = expected; poll(); return expected;
        });
        return docReady;
    }
    function sourceChanged() {
        docEpoch++; docScope = docPage + ':' + docEpoch; if (cx2()) { S.status = null; S.listening = false; S.client = ''; S.lastReply = 0; } S.seq = -1; S.readyScope = ''; S.waiting = false; S.lastSent = 0;
        var expected = docScope;
        registerDocument().catch(function(){ if (docScope === expected) docReady = null; });
    }
    var transportRead = 0, transportSettled = 0;
    var LISTEN_LINE = 'Listen to my Shokker chat';
    function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    // CX2 2026-10-09 (lane CODEX-INTEGRATE; from the ChatGPT/Codex agent's candidate, reviewed): the server keeps a listener + chat PER assistant, so status / chat polls ask for the SELECTED
    // helper and the "connected and listening" badge only counts that assistant's client name. KILL SWITCH: window.SPB_CX2_OFF = true restores the old shared behaviour.
    function cx2() { return !window.SPB_CX2_OFF; }
    function api(path, opt) {
        if (cx2() && /^\/api\/mcp\/(status|chat)(\?|$)/.test(path) && relaying()) path += (path.indexOf('?') < 0 ? '?' : '&') + 'helper=' + mode() + '&document_scope=' + encodeURIComponent(docScope);
        // Only status/chat reads may time out and retry; inbox/tool writes never do.
        var isRead = /^\/api\/mcp\/(status|chat)(\?|$)/.test(path) && (!opt || !opt.method || String(opt.method).toUpperCase() === 'GET');
        if (window.SPB_RELAY_TRANSPORT_OFF || !isRead) return fetch(BASE + path, opt).then(function (r) { return r.json(); });
        var readHelper = mode(), readScope = docScope, readId = ++transportRead;
        var delay = /^\/api\/mcp\/chat\?/.test(path) && /(?:[?&])wait=25(?:&|$)/.test(path) ? 35000 : 8000;
        return new Promise(function (resolve, reject) {
            var done = false, controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
            var options = {}, timer;
            if (opt) Object.keys(opt).forEach(function (key) { options[key] = opt[key]; });
            if (controller) options.signal = controller.signal;
            function finish(error, value) {
                if (done) return; done = true; clearTimeout(timer);
                if (readHelper === mode() && readScope === docScope && readId >= transportSettled) {
                    transportSettled = readId;
                    if (error) { S.transportUnavailable = true; S.status = null; S.listening = false; S.client = ''; redraw(); }
                    else if (S.transportUnavailable) { S.transportUnavailable = false; redraw(); }
                }
                if (error) reject(error); else resolve(value);
            }
            timer = setTimeout(function () {
                finish(new Error('Connection check timed out.'));
                if (controller) controller.abort();
            }, delay);
            try { fetch(BASE + path, options).then(function (r) {
                if (r.ok === false) throw new Error('Connection check unavailable.');
                return r.json();
            }).then(function (j) {
                if (!j || typeof j !== 'object' || Array.isArray(j) || j.ok === false) throw new Error('Connection check unavailable.');
                if (readHelper === mode() && readScope === docScope && readId < transportSettled && S.transportUnavailable) throw new Error('Connection result superseded.');
                finish(null, j);
            }).catch(function (error) { finish(error); }); } catch (error) { finish(error); }
        });
    }
    function listeningFor(j) {
        if (!cx2()) return !!(j && j.listening);
        var client = String((j && j.client) || '').toLowerCase();
        return !!(j && j.listening && (mode() === 'chatgpt' ? /^(codex|chatgpt|openai)/.test(client) : /^(claude|local-agent-mode)/.test(client)));
    }
    function mode() { var m = lsGet(KEY); return (m === 'claude' || m === 'chatgpt' || m === 'offline') ? m : ''; }
    function name(m) { m = m || mode(); return m === 'claude' ? 'Claude' : m === 'chatgpt' ? 'ChatGPT' : 'Offline Helper'; }
    function relaying() { var m = mode(); return m === 'claude' || m === 'chatgpt'; }
    function P() { return window.spbProAI || {}; }
    function redraw() { try { if (P().refresh) P().refresh(); } catch (e) {} }
    function push(e) { try { if (P()._push) P()._push(e); } catch (er) {} }

    // CX3: connection notes are transient UI, not assistant answers or edit authority.
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

    function setMode(m) {
        lsSet(KEY, m); S.step = (m === 'claude' || m === 'chatgpt'); if (cx2()) { S.waiting = false; S.lastSent = 0; S.lastReply = 0; S.status = null; S.listening = false; S.client = ''; S.transportUnavailable = false; }
        if (relaying()) {
            // Explicit helper selection reclaims this document before tool polling.
            // A superseded page must not poll using its previously accepted scope.
            try { if (window.SpbMcpBridge) window.SpbMcpBridge.setEnabled(false); } catch (e) {}
            sourceChanged();
            var selectedScope = docScope, selectedMode = m;
            docReady.then(function () {
                if (docScope === selectedScope && mode() === selectedMode && relaying() && window.SpbMcpBridge) window.SpbMcpBridge.setEnabled(true);
            }).catch(function () { refreshStatus(); redraw(); });
        }
        refreshStatus(); poll(); redraw(); if (m === 'claude') ccDetect();          // [S22 2026-10-13 beta Claude setup]
    }
    function refreshStatus() {
        var requestedHelper = mode(), requestedScope = docScope;
        return api('/api/mcp/status').then(function (s) { if (cx2() && (requestedHelper !== mode() || requestedScope !== docScope)) return null; S.status = s; S.listening = listeningFor(s); S.client = (s && s.client) || ''; redraw(); return s; }, function () { return null; });
    }
    // the page side of the relay: long-poll the chat for the assistant's replies (only while Claude / ChatGPT is the helper)
    function poll() {
        if (!relaying()) return;
        if (S.readyScope !== docScope) { if (!docReady) registerDocument().catch(function(){docReady=null;}); return; }
        if (S.polling) return; S.polling = true;
        if (!S.seq) { var initialHelper = mode(), initialScope = docScope; api('/api/mcp/chat?after=999999999&wait=0').then(function (j) { S.polling = false; if (initialHelper !== mode() || initialScope !== docScope) { poll(); return; } S.seq = (j && j.seq) || 0; S.seq = S.seq || -1; poll(); }, function () { S.polling = false; setTimeout(poll, 4000); }); return; }
        (function loop() {
            if (!relaying()) { S.polling = false; return; }
            var requestedHelper = mode(), requestedScope = docScope;
            api('/api/mcp/chat?after=' + S.seq + '&wait=25').then(function (j) {
                if (cx2() && (requestedHelper !== mode() || requestedScope !== docScope)) { loop(); return; }          // CX2: stale answer for the other assistant: S.seq is not advanced, so nothing is lost
                if (j && j.ok) {
                    var was = S.listening; S.listening = listeningFor(j); S.client = j.client || S.client;
                    (j.entries || []).forEach(function (e) {
                        S.seq = Math.max(S.seq, e.seq);
                        if (e.role === 'status' && e.text === 'working') S.waiting = 'working';
                        else if (e.role === 'assistant') { retireRelayNotices(e, requestedHelper, requestedScope); S.waiting = false; S.lastSent = 0; S.lastReply = Date.now(); push(withCards({ role: 'ai', text: e.text, meta: '✦ ' + esc(name()) + ' (connected)', kind: 'noaction' }, e)); }
                    });
                    if (was !== S.listening || (j.entries || []).length) redraw();
                }
                loop();
            }, function () { setTimeout(loop, 4000); });
        })();
    }
    // APPCHAT-CARDS 2026-10-09 (owner: "when you suggest things it SHOULD popup the thumbnail images ... and then gave options to load more"): the assistant's
    // spb_reply finishes become the same thumbnail cards the built-in advisor shows; Use this / Show me more go back to the assistant as the buyer's next message
    function withCards(entry, e) {
        entry.documentScope = docScope; entry.relayHelper = mode();
        if (!e.finishes || !e.finishes.length || !P()._cards) return entry;
        var cards = [];
        e.finishes.forEach(function (f) { var c = (P()._cards([f.key], f.colour) || [])[0]; if (!c) return; if (f.why) c.why = f.why; c.hex = f.colour || ''; cards.push(c); });
        if (cards.length) { entry.fcards = cards; entry.fclabel = e.use_on || 'the body'; entry.relay = true; entry.aicMore = true; }
        return entry;
    }
    function say(text) { if (!relaying() || relayDelivering) return; push({ role: 'user', text: text }); return relay(text); }
    function useCard(entry, i) { if (!relaying() || !entry || entry.documentScope !== docScope || (cx2() && entry.relayHelper !== mode())) return; var c = entry && entry.fcards && entry.fcards[i]; if (c) say('Use ' + c.name + (c.hex ? ' (' + c.hex + ')' : '') + ' on ' + (entry.fclabel || 'the body')); }
    // the buyer pressed Send while Claude / ChatGPT is the helper
    var relayDelivering = false;
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
    function relay(text) {
        if (!relaying()) return Promise.resolve({ok:false,reason:'helper_changed'});
        if (relayDelivering) return Promise.resolve({ok:false,reason:'delivery_pending'});
        relayDelivering = true;
        var expectedScope = docScope, expectedHelper = mode();
        S.waiting = 'sent'; S.lastSent = Date.now(); poll(); redraw();
        return confirmDelivery(function(live){return (docReady || registerDocument()).then(function(scope) {
            if (!live()) throw new Error('Delivery confirmation expired; request was not sent.');
            if (scope !== docScope || expectedScope !== docScope || expectedHelper !== mode()) throw new Error('The open paint or selected helper changed. Send your request again.');
            return api('/api/mcp/inbox', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cx2() ? { text: text, helper: expectedHelper, document_scope: expectedScope } : { text: text }) }); }); }).then(function (j) {
            relayDelivering = false;
            if (expectedScope !== docScope || expectedHelper !== mode()) return {ok:false,reason:'scope_changed'};
            if (!j || j.ok === false || (cx2() && !noticeSeq(j.seq))) { S.waiting = false; push({ role: 'err', text: (j && j.message) || 'Could not confirm delivery to ' + name() + '. Your draft is kept; check the connected chat before sending again.' }); redraw(); return {ok:false,reason:'delivery_unconfirmed'}; }
            S.listening = !!j.listening;
            if (!j.listening) relayNotice(j, expectedHelper, expectedScope);
            redraw(); return {ok:true,seq:j.seq,helper:expectedHelper,document_scope:expectedScope};
        }, function (error) { relayDelivering = false; if (expectedScope !== docScope || expectedHelper !== mode()) return {ok:false,reason:'scope_changed'}; docReady = null; S.waiting = false; push({ role: 'err', text: (error.message || 'Could not reach the Shokker server.') + ' Your draft is kept; check the connected chat before sending again.' }); redraw(); return {ok:false,reason:'delivery_unconfirmed'}; });
    }

    // CONNECT-CLAUDE 2026-10-10 (orchestrator brief: "a fresh install must get Claude connected AND knowing the app with as few steps as possible"): the Claude card is a
    // short guided panel, one step per line with a button each: (a) add the connector (.mcpb) to Claude Desktop, (b) upload the Shokker skill in Claude Desktop / claude.ai,
    // (c) install the skill for Claude Code, (d) check what is done. Server side: server_routes/claude_connect_routes.py (/api/claude-connect/*). Results live in S.cc so the
    // panel's frequent redraws keep them. Menu names checked 2026-10-10 against support.claude.com/en/articles/12512180-use-skills-in-claude.
    // KILL SWITCH: window.SPB_CCON_OFF = true restores the old two-line Claude steps (and env SPB_CLAUDE_CONNECT_OFF=1 switches the routes off).
    S.cc = { a: '', b: '', c: '', check: null, busy: '' };
    S.cc.setup = null; S.cc.setupKey = ''; S.cc.setupMsg = ''; S.cc.poll = null; S.cc.detecting = false; S.cc.bannerKind = ''; S.cc.doneUntil = 0;          // [S22 2026-10-13 beta Claude setup] setup card + update banner state (see ccDetect below)
    function ccOn() { return !window.SPB_CCON_OFF; }
    function cc(path, body) {
        var opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
        return fetch(BASE + '/api/claude-connect/' + path, opt).then(function (r) {
            return r.json().then(function (j) { return j || {}; }, function () { return { ok: false, error: r.status === 404 ? 'noroute' : 'bad' }; });
        });
    }
    var CC_OLD = 'This needs the newest Shokker server: close and reopen Shokker Paint Booth, then try again.';
    function ccFail(j) { return (j && j.message) || (j && j.error === 'noroute' ? CC_OLD : 'Could not do that.'); }
    function ccMsg(k, html) { S.cc[k] = html; redraw(); }
    function ccPath(p) { return '<code class="spb-cc-path">' + esc(p) + '</code>'; }
    function ccSay(k) { return S.cc[k] ? '<span class="spb-aic-msg">' + S.cc[k] + '</span>' : ''; }
    function ccCheckHtml() {
        var c = S.cc.check; if (!c) return '';
        if (c.ok === false) return '<span class="spb-aic-msg">' + esc(ccFail(c)) + '</span>';
        var L = [], b = c.bundle || {}, d = c.desktop || {}, z = c.skillZip || {}, k = c.codeSkill || {}, n = c.codeConnector || {};
        function row(cls, t) { L.push('<li class="' + cls + '">' + t + '</li>'); }
        if (!b.found) row('no', '✗ The connector file is missing from this install.');
        else if (!d.claudeDesktop) row('todo', '○ Claude Desktop is not on this PC yet. Use the Get Claude Desktop button.');          // [S22 2026-10-13 beta Claude setup] no claude.ai in buyer text
        else if (!d.seen) row('todo', '○ Claude Desktop: Shokker connector not added yet (step 1).');
        else if (b.version && d.version && b.version !== d.version) row('warn', '! Claude Desktop has connector v' + esc(d.version) + ', this app has v' + esc(b.version) + '. Press <b>Add Shokker to Claude</b> to update.');
        else row(d.enabled === false ? 'warn' : 'ok', (d.enabled === false ? '! ' : '✓ ') + 'Claude Desktop has the Shokker connector' + (d.version ? ' (v' + esc(d.version) + ')' : '') + (d.enabled === false ? ', but it is turned off in Claude.' : '.'));
        if (!z.found) row('no', '✗ The skill file is missing from this install.');
        else row('unk', '? Skill uploaded to Claude: this can’t be seen from here. Look in Claude under Customize › Skills.');
        if (k.installed && k.upToDate) row('ok', '✓ Claude Code skill installed.');
        else if (k.installed) row('warn', '! Claude Code has an older Shokker skill. Press <b>Install the skill for Claude Code</b> to update.');
        else row('todo', '○ Claude Code skill not installed (only needed if you use Claude Code).');
        if (n.seen === true) row('ok', '✓ Claude Code has the Shokker connector.');
        else if (n.seen === false) row('todo', '○ Claude Code connector not added (use <b>Copy connector command</b>).');
        else if (n.claudeCode === false) row('todo', '○ Claude Code is not on this PC (only needed if you use it).');
        row(S.listening ? 'ok' : 'todo', S.listening ? '✓ Claude is connected and listening right now.' : '○ Claude is not listening to this chat yet (step 5).');
        return '<ul class="spb-cc-check">' + L.join('') + '</ul>';
    }
    function ccStepsHtml() {
        var busy = S.cc.busy;
        return '<ol class="spb-aic-steps spb-cc">' +
            '<li><b>Claude Desktop: add the Shokker connector.</b> <button type="button" class="spb-pai-act hot" data-act="aic-install">Add Shokker to Claude</button> <button type="button" class="spb-pai-act" data-act="aic-showmcpb">Show the file</button>' +
                '<span class="spb-aic-msg">Claude asks you to confirm. No Claude Desktop yet? It is free: <a href="https://claude.ai/download" target="_blank" rel="noopener">Get Claude Desktop</a></span>' + ccSay('a') + '</li>' +
            '<li><b>Teach Claude this app (the Shokker skill).</b> <button type="button" class="spb-pai-act" data-act="aic-showskill">Show the skill file</button>' +
                '<span class="spb-aic-msg">In Claude Desktop: <b>Customize › Skills › + › Create skill › Upload a skill</b>, then pick <code>shokker-paint-booth.zip</code>. <b>Settings › Capabilities › Code execution and file creation</b> must be on.</span>' + ccSay('b') + '</li>' +
            '<li><b>Using Claude Code?</b> <button type="button" class="spb-pai-act" data-act="aic-codeskill"' + (busy === 'c' ? ' disabled' : '') + '>Install the skill for Claude Code</button> <button type="button" class="spb-pai-act" data-act="aic-copycmd">Copy connector command</button>' +
                '<span class="spb-aic-msg">The skill goes in your Claude Code skills folder; an older copy is backed up first. Paste the command in a terminal once.</span>' + ccSay('c') + '</li>' +
            '<li><b>Check what is done.</b> <button type="button" class="spb-pai-act" data-act="aic-check"' + (busy === 'd' ? ' disabled' : '') + '>' + (busy === 'd' ? 'Checking…' : 'Check') + '</button>' + ccCheckHtml() + '</li>' +
            '<li>In Claude, type: <code>' + LISTEN_LINE + '</code> <button type="button" class="spb-pai-act" data-act="aic-copylisten">Copy</button></li>' +
            '<li>Then type what you want <b>right here</b>. Claude makes the changes and answers in this box. You can also keep talking to it in Claude.</li></ol>';
    }
    function ccClick(act, b) {
        if (act === 'aic-install') {
            ccMsg('a', 'Opening…');
            cc('open-bundle', {}).then(function (j) {
                if (j && j.error === 'noroute') return api('/api/mcp/open-bundle', { method: 'POST' }).then(function (o) { ccMsg('a', o && o.ok ? 'Confirm the install in Claude, then do step 2.' : esc((o && o.message) || 'Could not open it.')); });
                if (j && j.ok && j.test) return ccMsg('a', 'Test mode: would open ' + ccPath(j.path));
                ccMsg('a', j && j.ok ? 'Claude Desktop should now ask you to confirm' + (j.version ? ' Shokker v' + esc(j.version) : '') + '. Press Install there, then do step 2.' : esc(ccFail(j)));
            }, function () { ccMsg('a', 'Could not reach the Shokker server.'); });
        } else if (act === 'aic-showmcpb' || act === 'aic-showskill' || act === 'aic-showcode') {
            var k = act === 'aic-showmcpb' ? 'a' : act === 'aic-showskill' ? 'b' : 'c';
            cc('reveal', { what: act === 'aic-showmcpb' ? 'bundle' : act === 'aic-showskill' ? 'skill' : 'code-skill' }).then(function (j) {
                ccMsg(k, j && j.ok ? 'Shown in Explorer: ' + ccPath(j.path) + (k === 'b' ? ' Upload this file in Claude.' : '') : esc(ccFail(j)));
            }, function () { ccMsg(k, 'Could not reach the Shokker server.'); });
        } else if (act === 'aic-codeskill') {
            S.cc.busy = 'c'; ccMsg('c', 'Installing…');
            cc('install-code-skill', {}).then(function (j) {
                S.cc.busy = '';
                if (!j || !j.ok) return ccMsg('c', esc(ccFail(j)));
                if (j.status === 'up_to_date') return ccMsg('c', '✓ Already installed and up to date: ' + ccPath(j.target) + ' <button type="button" class="spb-pai-act" data-act="aic-showcode">Show it</button>');
                ccMsg('c', '✓ Installed: ' + ccPath(j.target) + (j.backup ? ' Your old copy was moved to ' + ccPath(j.backup) : '') +
                    (j.newSkillsFolder ? ' If Claude Code is already open, type <code>/reload-skills</code> in it.' : ' Claude Code picks it up by itself.') + ' <button type="button" class="spb-pai-act" data-act="aic-showcode">Show it</button>');
            }, function () { S.cc.busy = ''; ccMsg('c', 'Could not reach the Shokker server.'); });
        } else if (act === 'aic-check') {
            S.cc.busy = 'd'; redraw();
            refreshStatus().then(function () { return cc('status?deep=1'); }).then(function (j) { S.cc.busy = ''; S.cc.check = j || { ok: false }; redraw(); }, function () { S.cc.busy = ''; S.cc.check = { ok: false, message: 'Could not reach the Shokker server.' }; redraw(); });
        } else if (act === 'aic-setup') { ccSetupGo();          // [S22 2026-10-13 beta Claude setup]
        } else if (act === 'aic-getdesktop') { ccGetDesktop();
        } else if (act === 'aic-copyex') { copy(CC_EXAMPLE, b);
        } else return false;
        return true;
    }
    // [S22 2026-10-13 beta Claude setup] SETUP CARD + UPDATE BANNER (beta plan A). One server call (/api/claude-connect/desktop) says which of three things is true on this PC: Claude Desktop is missing, the Shokker connector in it is
    // missing / not the version this SPB ships, or all is well. The Claude card shows ONE big button for the first two and one example line for the third; after the button the card polls the same call every 3 s for up to 2 minutes and
    // turns green by itself (no Check press). The same call runs at every start: a connector that does not match the shipped one gets a small bottom-right banner with the one-click Update, once per shipped version (dismissible).
    // A buyer who has Claude Desktop but no connector and has not picked a helper yet gets the same banner once as an offer. Claude Desktop is the ONLY thing named in buyer text: the Claude website cannot use a local connector.
    // KILL SWITCH: window.SPB_CCON_OFF = true or env SPB_CLAUDE_CONNECT_OFF=1 (the old steps return, no banner, no calls). TEST ONLY: server env SPB_CLAUDE_CONNECT_DETECT_HOME + SPB_CLAUDE_CONNECT_NO_OPEN (routes file).
    var CC_EXAMPLE = 'Paint my roof matte black', CC_UPD_KEY = 'spb_cc_upd_dismissed', CC_OFFER_KEY = 'spb_cc_offer_dismissed', ccLastFocus = 0;
    function ccDetect() {
        if (!ccOn()) return Promise.resolve(null);
        return cc('desktop').then(function (j) {
            var good = !!(j && j.ok === true && j.state), key = good ? JSON.stringify(j) : 'bad';
            var changed = key !== S.cc.setupKey;
            S.cc.setupKey = key; S.cc.setup = good ? j : { ok: false };
            if (changed) { redraw(); ccBanner(); }
            return S.cc.setup;
        }, function () { if (!S.cc.setup) { S.cc.setup = { ok: false }; S.cc.setupKey = 'bad'; redraw(); } return null; });
    }
    function ccPollStop() { if (S.cc.poll) { clearInterval(S.cc.poll.timer); S.cc.poll = null; } }
    function ccPollStart() {
        ccPollStop();
        var p = S.cc.poll = { until: Date.now() + 120000, timer: 0 };
        p.timer = setInterval(function () {
            ccDetect().then(function (j) {
                if (S.cc.poll !== p) return;
                if (j && j.state === 'connected') { ccPollStop(); S.cc.setupMsg = ''; refreshStatus(); redraw(); ccBanner(); }
                else if (Date.now() > p.until) { ccPollStop(); S.cc.setupMsg = 'Still not showing in Claude Desktop. If it did not ask you to confirm, open Claude Desktop and press the button again.'; redraw(); ccBanner(); }
            });
        }, 3000);
    }
    function ccSetupGo() {
        S.cc.setupMsg = 'Opening…'; redraw(); ccBanner();
        return cc('open-bundle', {}).then(function (j) {
            if (j && j.error === 'noroute') return api('/api/mcp/open-bundle', { method: 'POST' }).then(function (o) { return o || {}; });
            return j || {};
        }).then(function (j) {
            if (j.ok) { S.cc.setupMsg = j.test ? 'Test mode: the connector file was not opened. Waiting for Claude Desktop…' : 'Claude Desktop should now ask you to confirm. Press Install there. This turns green by itself.'; ccPollStart(); }
            else S.cc.setupMsg = esc(ccFail(j));
            redraw(); ccBanner();
        }, function () { S.cc.setupMsg = 'Could not reach the Shokker server.'; redraw(); ccBanner(); });
    }
    function ccGetDesktop() {
        S.cc.setupMsg = 'Opening the download page…'; redraw();
        cc('open-download', {}).then(function (j) {
            if (j && j.error === 'noroute') { try { window.open('https://claude.ai/download', '_blank', 'noopener'); } catch (e) {} j = { ok: true }; }
            S.cc.setupMsg = j && j.ok ? 'The download page is open in your browser. Install Claude Desktop and sign in, then come back here: this box updates by itself.' : esc((j && j.message) || ccFail(j));
            redraw();
        }, function () { S.cc.setupMsg = 'Could not reach the Shokker server.'; redraw(); });
    }
    function ccSetupHtml() {
        var j = S.cc.setup;
        if (!ccOn() || (j && j.ok === false)) return '';
        if (!j) { if (!S.cc.detecting) { S.cc.detecting = true; ccDetect().then(function () { S.cc.detecting = false; }, function () { S.cc.detecting = false; }); } return '<div class="spb-ccs"><div class="spb-ccs-h">Looking for Claude Desktop on this PC…</div></div>'; }
        var st = j.state, con = j.connector || {}, ship = j.shipped || {}, msg = S.cc.setupMsg ? '<span class="spb-aic-msg">' + S.cc.setupMsg + '</span>' : '';
        function box(cls, h, t, btn) { return '<div class="spb-ccs' + (cls ? ' ' + cls : '') + '"><div class="spb-ccs-h">' + h + '</div>' + (t ? '<div class="spb-ccs-t">' + t + '</div>' : '') + (btn || '') + msg + '</div>'; }
        if (st === 'no_desktop') return box('', 'Step 1 of 2: get Claude Desktop', 'Claude Desktop is the free Claude app for Windows, and it is the one Shokker connects to (the Claude website cannot). Install it and sign in. This box updates by itself when you come back.',
            '<button type="button" class="spb-pai-act hot" data-act="aic-getdesktop">Get Claude Desktop (free)</button>');
        if (st === 'not_added') return box('', 'Step 2 of 2: add Shokker to Claude Desktop', 'Claude Desktop is on this PC. One click adds Shokker: Claude Desktop asks you to confirm, press Install there. This box turns green by itself.',
            '<button type="button" class="spb-pai-act hot" data-act="aic-setup">Add Shokker to Claude</button>');
        if (st === 'outdated') return box('', 'Update Shokker in Claude Desktop', 'Claude Desktop has Shokker connector v' + esc(con.version || '?') + '; this Shokker Paint Booth comes with v' + esc(ship.version || '?') + '. One click updates it: press Install when Claude Desktop asks.',
            '<button type="button" class="spb-pai-act hot" data-act="aic-setup">Update Shokker in Claude</button>');
        if (st === 'disabled') return box('no', 'Shokker is switched off in Claude Desktop', 'In Claude Desktop open Settings › Extensions, find Shokker Paint Booth and switch it on. Come back here afterwards: this box turns green by itself.', '');
        if (st === 'no_bundle') return box('no', 'The Claude connector file is missing', 'This copy of Shokker Paint Booth does not contain the connector for Claude Desktop. Reinstall Shokker Paint Booth, then come back here.', '');
        return box('ok', '✓ Shokker is set up in Claude Desktop' + (con.version ? ' (v' + esc(con.version) + ')' : ''),
            'Try it: in Claude Desktop type <code>' + esc(CC_EXAMPLE) + '</code> <button type="button" class="spb-pai-act" data-act="aic-copyex">Copy</button><br>To type here in this box instead, say <code>' + LISTEN_LINE + '</code> to Claude once <button type="button" class="spb-pai-act" data-act="aic-copylisten">Copy</button>', '');
    }
    function ccWrap(inner) {
        var card = ccSetupHtml();
        if (!card) return inner;
        return card + '<details class="spb-aic-more spb-cc-more"><summary>More setup: teach Claude this app, Claude Code, in-app chat</summary>' + inner + '</details>';
    }
    // the banner (not part of the AI panel, so it shows at start without any panel open); built from S.cc.setup, rebuilt whenever that changes
    function ccBannerKind() {
        var j = S.cc.setup;
        if (!ccOn() || !j || j.ok === false) return '';
        if (j.state === 'outdated' && lsGet(CC_UPD_KEY) !== String((j.shipped && j.shipped.version) || '')) return 'update';
        if (j.state === 'not_added' && !mode() && !lsGet(CC_OFFER_KEY)) return 'offer';
        return '';
    }
    function ccBannerOff() { var el = document.getElementById('spbCcBanner'); if (el && el.parentNode) el.parentNode.removeChild(el); S.cc.bannerKind = ''; S.cc.doneUntil = 0; }
    function ccBanner() {
        var j = S.cc.setup, kind = ccBannerKind(), el = document.getElementById('spbCcBanner');
        if (S.cc.bannerKind && !kind) { if (j && j.state === 'connected') { kind = 'done'; S.cc.doneUntil = Date.now() + 6000; } else if (S.cc.poll) kind = S.cc.bannerKind; }
        if (!kind && S.cc.doneUntil && Date.now() < S.cc.doneUntil) kind = 'done';          // it just worked: say so; or keep it up while we wait for Claude Desktop
        if (!kind) { ccBannerOff(); return; }
        var con = (j && j.connector) || {}, ship = (j && j.shipped) || {}, title, text, btn = '';
        if (kind === 'update') { title = 'Update Shokker in Claude Desktop'; text = 'Shokker Paint Booth was updated. The Shokker connector in Claude Desktop (v' + esc(con.version || '?') + ') should match it (v' + esc(ship.version || '?') + '). One click.'; btn = 'Update Shokker in Claude'; }
        else if (kind === 'offer') { title = 'Use Claude with Shokker'; text = 'Claude Desktop is on this PC. One click adds Shokker to it, then you can paint by chatting with Claude.'; btn = 'Add Shokker to Claude'; }
        else { title = '✓ Shokker is set up in Claude Desktop'; text = 'Try it in Claude Desktop: <code>' + esc(CC_EXAMPLE) + '</code>'; }
        if (!el) { el = document.createElement('div'); el.id = 'spbCcBanner'; el.setAttribute('role', 'status'); el.addEventListener('click', ccBannerClick); (document.body || document.documentElement).appendChild(el); }
        S.cc.bannerKind = kind === 'done' ? '' : kind;
        el.setAttribute('data-kind', kind);
        el.innerHTML = '<div class="spb-ccb-t">' + title + '</div><div class="spb-ccb-x">' + text + '</div>' + (S.cc.setupMsg && kind !== 'done' ? '<div class="spb-ccb-m">' + S.cc.setupMsg + '</div>' : '') +
            (kind === 'done' ? '' : '<div class="spb-ccb-b"><button type="button" class="spb-ccb-go" data-ccb="go">' + btn + '</button><button type="button" class="spb-ccb-no" data-ccb="no">Not now</button></div>');
        if (kind === 'done') setTimeout(function () { if (!S.cc.bannerKind && Date.now() >= S.cc.doneUntil) ccBannerOff(); }, 6200);
    }
    function ccBannerClick(ev) {
        var t = ev.target, a = t && t.getAttribute && t.getAttribute('data-ccb'), kind = (document.getElementById('spbCcBanner') || {}).getAttribute ? document.getElementById('spbCcBanner').getAttribute('data-kind') : '';
        if (a === 'go') { if (kind === 'offer') setMode('claude'); ccSetupGo(); }
        else if (a === 'no') {
            var j = S.cc.setup || {};
            if (kind === 'update') lsSet(CC_UPD_KEY, String((j.shipped && j.shipped.version) || '')); else lsSet(CC_OFFER_KEY, '1');
            ccPollStop(); ccBannerOff();
        }
    }
    // the buyer comes back from installing Claude Desktop / pressing Install: look again (cheap) instead of making them press Check
    function ccFocus() {
        if (!ccOn() || document.hidden || Date.now() - ccLastFocus < 1500) return;
        ccLastFocus = Date.now();
        var j = S.cc.setup;
        if (!j || j.ok === false || mode() === 'claude' || S.cc.bannerKind) { if (!j || j.ok === false || j.state !== 'connected' || S.cc.bannerKind) ccDetect(); }
    }
    function ccBoot() { if (!ccOn()) return; try { window.addEventListener('focus', ccFocus); } catch (e) {} ccDetect(); }
    function stepsHtml(m) {
        var claude = m === 'claude';
        if (claude && ccOn()) return ccWrap(ccStepsHtml());          // [S22 2026-10-13 beta Claude setup]
        return '<ol class="spb-aic-steps">' +
            (claude
                ? '<li><b>Get Claude Desktop</b> (free to install, uses your own Claude plan): <a href="https://claude.ai/download" target="_blank" rel="noopener">Get Claude Desktop</a></li>' +
                  '<li><button type="button" class="spb-pai-act hot" data-act="aic-install">Add Shokker to Claude</button> Claude asks you to confirm the install. <span class="spb-aic-msg" data-aic="instmsg"></span><details class="spb-aic-more"><summary>Using Claude Code instead?</summary>Run this once in a terminal, then start Claude Code: <button type="button" class="spb-pai-act" data-act="aic-copycmd">Copy command</button></details></li>'
                : '<li><b>Open ChatGPT’s Codex</b> (uses your own ChatGPT plan).</li>' +
                  '<li><button type="button" class="spb-pai-act hot" data-act="aic-codex">Set up Codex</button> adds Shokker to Codex (you confirm it). Restart Codex afterwards.</li>') +
            '<li>In ' + name(m) + ', type: <code>' + LISTEN_LINE + '</code> <button type="button" class="spb-pai-act" data-act="aic-copylisten">Copy</button></li>' +
            '<li>Then type what you want <b>right here</b>. ' + name(m) + ' makes the changes and answers in this box. You can also keep talking to it in ' + name(m) + '.</li></ol>';
    }
    function recentReply() { return !!(S.lastReply && Date.now() - S.lastReply < 120000); }
    function statusLine(m) {
        if (!window.SPB_RELAY_TRANSPORT_OFF && S.transportUnavailable)
            return '<div class="spb-aic-st">The connection to SPB could not be checked. Your draft is kept. A submitted request may still be waiting; check the connected chat before sending it again. We will check again without repeating your requests. <button class="spb-aic-link" data-act="aic-offline">Use Offline Helper</button></div>';
        var on = S.status && S.status.enabled;
        if (on && S.waiting === 'working') return '<div class="spb-aic-st">' + esc(name(m)) + ' received your message. Waiting for its answer.</div>';
        if (on && !S.waiting && recentReply()) return '<div class="spb-aic-st">Last answer received from ' + esc(name(m)) + '. You can send your next question here.</div>';
        if (S.listening) return '<div class="spb-aic-st ok">● ' + esc(name(m)) + ' is connected and listening. Type below.</div>';
        if (on) return '<div class="spb-aic-st">○ Waiting for ' + esc(name(m)) + '… (follow the steps, then type “' + LISTEN_LINE + '” in ' + esc(name(m)) + ')</div>';
        return '<div class="spb-aic-st">○ Not connected yet</div>';
    }
    // the card at the top of the chat: helper picker, or the chosen helper's connect steps
    function cardHtml(hasLog) {
        var m = mode();
        if (!m) return '<div class="spb-aic"><b>Who should answer you?</b><div class="spb-aic-meta">Pick once. You can switch any time with the ⚙ button.</div><div class="spb-aic-pick">' +
            '<button type="button" class="spb-aic-opt" data-act="aic-claude"><b>Claude</b><span>Connect your Claude app</span></button>' +
            '<button type="button" class="spb-aic-opt" data-act="aic-chatgpt"><b>ChatGPT</b><span>Connect ChatGPT (Codex)</span></button>' +
            '<button type="button" class="spb-aic-opt" data-act="aic-offline"><b>Offline Helper</b><span>Built in, no setup, works with no internet</span></button></div></div>';
        if (m === 'offline') return (hasLog && !cx2()) ? '' : '<div class="spb-aic small">Answering: <b>Offline Helper</b> (built in). <button type="button" class="spb-pai-opt" data-act="aic-switch">Connect Claude or ChatGPT instead</button></div>';
        var open = S.step || !S.listening;
        return '<div class="spb-aic"><div class="spb-aic-top"><b>' + esc(name(m)) + '</b> answers this chat <button type="button" class="spb-pai-opt" data-act="aic-switch">Switch</button></div>' + statusLine(m) +
            (open ? '<details class="spb-aic-how"' + (hasLog && (S.listening || S.waiting === 'working' || recentReply()) ? '' : ' open') + '><summary>How to connect ' + esc(name(m)) + '</summary>' + stepsHtml(m) + '</details>' : '') + '</div>';
    }
    // shown under the last message while the assistant works on what the buyer sent
    function tailHtml() {
        if (!relaying() || !S.waiting) return '';
        // APPCHAT-REDELIVER 2026-10-09 (owner: "stuck saying Claude is working but no chat happening"): after 90 s with no answer, no listener and no recent tool call,
        // say what to do instead of spinning forever (the server keeps the message and hands it to the next listener)
        var st = S.status || {}, quiet = st.lastCallAgo == null || st.lastCallAgo > 60;
        if (S.waiting === 'working' && S.lastSent && Date.now() - S.lastSent > 90000 && !S.listening && quiet)
            return '<div class="spb-pai-msg ai busy">' + esc(name()) + ' received your message, but its answer has not returned yet. Your message is kept. Check the connected assistant chat if you need to see its progress.</div>';
        if (S.lastSent && Date.now() - S.lastSent > 90000 && !S.listening && quiet)
            return '<div class="spb-pai-msg ai busy">' + esc(name()) + ' hasn’t answered yet. If ' + esc(name()) + ' was closed or restarted, type <code>' + LISTEN_LINE + '</code> in ' + esc(name()) + ': your message is kept and it will answer.</div>';
        var t = S.waiting === 'working' ? esc(name()) + ' is working on it…' : (S.listening ? 'Sent to ' + esc(name()) + '…' : 'Waiting for ' + esc(name()) + ' to connect…');
        return '<div class="spb-pai-msg ai busy"><span class="spb-tell-dots"><i></i><i></i><i></i></span> ' + t + '</div>';
    }
    function copy(text, btn) { try { navigator.clipboard.writeText(text); if (btn) { var o = btn.textContent; btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = o; }, 1500); } } catch (e) {} }
    function click(act, b, panel) {
        if (mode() === 'claude' && ccOn() && ccClick(act, b)) return true;          // CONNECT-CLAUDE
        if (act === 'aic-claude') setMode('claude');
        else if (act === 'aic-chatgpt') setMode('chatgpt');
        else if (act === 'aic-offline') setMode('offline');
        else if (act === 'aic-switch') { lsSet(KEY, ''); S.step = false; redraw(); }
        else if (act === 'aic-copylisten') copy(LISTEN_LINE, b);
        else if (act === 'aic-more') {
            var moreId = b && b.getAttribute('data-id'), moreLog = P().log ? P().log() : [];
            var moreEntry = moreLog.find(function(e){return e && String(e.id) === String(moreId);});
            if (relaying() && moreId && moreEntry && moreEntry.documentScope === docScope && (!cx2() || moreEntry.relayHelper === mode())) say('Show me more options like these');
        }
        else if (act === 'aic-copycmd') { var dir = (S.status && S.status.mcpDir) || ''; copy('claude mcp add shokker-paint-booth -- node "' + dir.replace(/\\/g, '/') + '/server/index.js"', b); }
        else if (act === 'aic-install') {
            var msg = panel && panel.querySelector('[data-aic="instmsg"]'); if (msg) msg.textContent = 'Opening…';
            api('/api/mcp/open-bundle', { method: 'POST' }).then(function (j) { if (msg) msg.textContent = j && j.ok ? 'Confirm the install in Claude, then do step 3.' : ((j && j.message) || 'Could not open it.'); }, function () { if (msg) msg.textContent = 'Could not reach the Shokker server.'; });
        } else if (act === 'aic-codex') { var g = panel && panel.querySelector('[data-act="gear"]'); if (g) g.click(); }
        else return false;
        return true;
    }
    function placeholder() {
        var m = mode();
        if (m === 'claude' || m === 'chatgpt') return 'Tell ' + name(m) + ' what you want… (Enter sends)';
        if (!m) return 'Pick who answers you above, then type here…';
        return '';
    }
    window.SpbAiConnect = { hideRelayNotice: hideRelayNotice, documentScope: function () { return docScope; }, _sourceChanged: sourceChanged, mode: mode, name: name, setMode: setMode, relaying: relaying, relay: relay, useCard: useCard, cardHtml: cardHtml, tailHtml: tailHtml, click: click, placeholder: placeholder, refresh: refreshStatus, listenLine: LISTEN_LINE };
    // styles live here so the panel CSS file (and its cache token) is untouched
    try { var st = document.createElement('style'); st.id = 'spbAiConnectCss'; st.textContent = '.spb-aic{margin:6px 0 8px;padding:12px;border-radius:12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.14);color:#d5d8ea;font-size:12.5px;line-height:1.45}.spb-aic>b,.spb-aic-top b{font-size:14px;color:#fff}.spb-aic.small{padding:8px 10px;font-size:12px}.spb-aic-meta{opacity:.75;margin:2px 0 8px}.spb-aic-pick{display:grid;gap:8px}.spb-aic-opt{display:flex;flex-direction:column;align-items:flex-start;gap:2px;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,0.18);background:rgba(255,255,255,0.04);color:#fff;font:inherit;cursor:pointer;text-align:left}.spb-aic-opt:hover{border-color:#ffd28a;background:rgba(255,210,138,0.08)}.spb-aic-opt b{font-size:14px}.spb-aic-opt span{font-size:12px;opacity:.75}.spb-aic-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.spb-aic-st{margin:6px 0 2px;opacity:.85}.spb-aic-st.ok{color:#7ee2a8;opacity:1;font-weight:600}.spb-aic-how{margin-top:6px}.spb-aic-how>summary{cursor:pointer;font-weight:700;color:#ffd28a}.spb-aic-steps{margin:8px 0 0 18px;padding:0;display:grid;gap:7px}.spb-aic-steps code{background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:5px;color:#fff}.spb-aic-steps a{color:#9ecbff}.spb-aic-more{margin-top:5px;opacity:.85}.spb-aic-more>summary{cursor:pointer}.spb-aic-msg{display:block;opacity:.8;margin-top:3px}.spb-aic-online .spb-pbn,.spb-aic-online .spb-ob{display:none!important}' +
        '.spb-cc>li{line-height:1.5}.spb-cc .spb-pai-act{margin:2px 4px 2px 0}.spb-cc .spb-aic-msg{font-size:12px}.spb-cc-path{word-break:break-all;font-size:11px}.spb-cc-check{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:3px;font-size:12px}.spb-cc-check .ok{color:#7ee2a8}.spb-cc-check .warn{color:#ffd28a}.spb-cc-check .no{color:#ff9b9b}.spb-cc-check .todo,.spb-cc-check .unk{opacity:.85}' +
        '.spb-ccs{margin:2px 0 8px;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,210,138,0.5);background:rgba(255,210,138,0.07)}.spb-ccs.ok{border-color:rgba(126,226,168,0.6);background:rgba(126,226,168,0.08)}.spb-ccs.no{border-color:rgba(255,155,155,0.55);background:rgba(255,155,155,0.07)}.spb-ccs-h{font-weight:700;font-size:13px;color:#fff;margin-bottom:3px}.spb-ccs.ok .spb-ccs-h{color:#7ee2a8}.spb-ccs-t{opacity:.92;margin:2px 0 7px;line-height:1.5}.spb-ccs .spb-pai-act{margin:2px 6px 2px 0}.spb-cc-more{margin-top:8px}' +
        '#spbCcBanner{position:fixed;right:16px;bottom:64px;z-index:99990;width:min(360px,calc(100vw - 32px));box-sizing:border-box;padding:12px 14px;border-radius:12px;background:#171a26;border:1px solid rgba(255,210,138,0.6);box-shadow:0 8px 28px rgba(0,0,0,0.55);color:#d5d8ea;font:12.5px/1.45 system-ui,"Segoe UI",sans-serif}#spbCcBanner[data-kind=done]{border-color:rgba(126,226,168,0.7)}.spb-ccb-t{font-weight:700;font-size:13.5px;color:#fff;margin-bottom:3px}#spbCcBanner[data-kind=done] .spb-ccb-t{color:#7ee2a8}.spb-ccb-x code{background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:5px;color:#fff}.spb-ccb-m{margin-top:6px;opacity:.85}.spb-ccb-b{display:flex;gap:8px;margin-top:9px;flex-wrap:wrap}.spb-ccb-go{padding:7px 12px;border-radius:8px;border:1px solid #ffd28a;background:#ffd28a;color:#14161f;font:inherit;font-weight:700;cursor:pointer}.spb-ccb-no{padding:7px 10px;border-radius:8px;border:1px solid rgba(255,255,255,0.25);background:transparent;color:#d5d8ea;font:inherit;cursor:pointer}'; (document.head || document.documentElement).appendChild(st); } catch (eS) {}
    function boot() { ccBoot(); if (!docReady) registerDocument().catch(function(){docReady=null;}); refreshStatus(); if (relaying()) poll(); setInterval(function () { if (relaying() && !S.polling) poll(); refreshStatus(); }, 20000); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 1800); }); else setTimeout(boot, 1800);
})();
