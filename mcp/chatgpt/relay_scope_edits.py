"""Narrow, anchor-checked private deltas against the source owner's relay."""


def backend_edits():
    return [
        ("""            while not any(e['seq'] > after for e in _CHAT) and time.time() < end:
                _COND.wait(timeout=min(2.0, max(0.05, end - time.time())))
            selected = request.args.get('helper') if _cx2() else None      # CX2: the page asks for the helper it shows""", """            selected = request.args.get('helper') if _cx2() else None
            def visible_chat_entry(e):
                return e['seq'] > after and (not selected or _matches(e, selected)) and (not _DOC_SCOPE or e.get('document_scope') == request.args.get('document_scope') == _DOC_SCOPE)
            # Wake only for entries this exact page/helper may receive; otherwise
            # filtered foreign history turns a long poll into a tight request loop.
            while not any(visible_chat_entry(e) for e in _CHAT) and time.time() < end:
                _COND.wait(timeout=min(2.0, max(0.05, end - time.time())))""", 1),
        ("_COND = threading.Condition()", "_DOC_SCOPE = ''\n_DOC_PAGES = {}\n_COND = threading.Condition()", 1),
        ("    # ------------------------------------------------------------------ APPCHAT 2026-10-09", '''    @app.route('/api/mcp/document', methods=['POST'])
    def mcp_document():
        """Page-owned opaque document boundary. No path, artwork, or credentials."""
        global _DOC_SCOPE
        g = page_guard()
        if g:
            return g
        body = request.get_json(silent=True) or {}
        page, epoch = body.get('page'), body.get('epoch')
        if not isinstance(page, str) or not re.fullmatch(r'[a-f0-9-]{36}', page) or type(epoch) is not int or not 0 <= epoch <= 1000000000:
            return jsonify({'ok': False, 'error': 'invalid_document_scope'}), 400
        scope = page + ':' + str(epoch)
        with _COND:
            if epoch < _DOC_PAGES.get(page, -1) or (epoch == _DOC_PAGES.get(page, -1) and scope != _DOC_SCOPE):
                return jsonify({'ok': False, 'error': 'stale_document_scope'}), 409
            _DOC_PAGES[page] = epoch
            if len(_DOC_PAGES) > 32:
                del _DOC_PAGES[next(iter(_DOC_PAGES))]
            if scope != _DOC_SCOPE:
                _DOC_SCOPE = scope
                _INBOX.clear()
                _INFLIGHT.clear()
                _fail_all('The open paint changed. Wait for a fresh buyer message before editing.')
                _COND.notify_all()
            return jsonify({'ok': True, 'document_scope': scope, 'seq': _CHAT_STATE['seq']})

    # ------------------------------------------------------------------ APPCHAT 2026-10-09''', 1),
        ("            e = _chat_add('user', text)", """            if _DOC_SCOPE and body.get('document_scope') != _DOC_SCOPE:
                return jsonify({'ok': False, 'error': 'stale_document_scope', 'message': 'The open paint changed. Send your request again.'}), 409
            e = _chat_add('user', text)
            if _DOC_SCOPE:
                e['document_scope'] = _DOC_SCOPE""", 1),
        ("                    w = _chat_add('status', 'working')", "                    w = _chat_add('status', 'working')\n                    if _DOC_SCOPE:\n                        w['document_scope'] = _DOC_SCOPE", 1),
        ("        if any(m.get('again') for m in out):", "        for row, original in zip(out, msgs):\n            if original.get('document_scope'):\n                row['document_scope'] = original['document_scope']\n        if any(m.get('again') for m in out):", 1),
        ("            e = _chat_add('assistant', text)", """            reply_to = body.get('reply_to')
            matched = next((m for m in _INFLIGHT if m['seq'] == reply_to and m.get('delivered_provider') == helper and m.get('document_scope') == _DOC_SCOPE), None)
            if _DOC_SCOPE and (type(reply_to) is not int or not matched):
                return jsonify({'ok': False, 'error': 'stale_or_missing_reply_to', 'message': 'This answer is not linked to a current buyer message. Wait for a fresh message; do not reuse earlier choices.'}), 409
            e = _chat_add('assistant', text)
            if _DOC_SCOPE:
                e['document_scope'] = _DOC_SCOPE
                e['reply_to'] = reply_to""", 1),
        ("m.get('delivered_provider') != helper]   # APPCHAT-REDELIVER", "(m.get('delivered_provider') != helper or (_DOC_SCOPE and m['seq'] > reply_to))]   # APPCHAT-REDELIVER", 1),
        ("and (not selected or _matches(e, selected))]", "and (not selected or _matches(e, selected)) and (not _DOC_SCOPE or e.get('document_scope') == request.args.get('document_scope') == _DOC_SCOPE)]", 1),
        ("e['role'] in ('user', 'assistant')]", "e['role'] in ('user', 'assistant') and (not _DOC_SCOPE or e.get('document_scope') == _DOC_SCOPE)]", 1),
        ("('seq', 'role', 'text', 'finishes', 'use_on')", "('seq', 'role', 'text', 'finishes', 'use_on', 'document_scope', 'reply_to')", 1),
        ("'scope': 'current server session'", "'scope': 'current committed document' if _DOC_SCOPE else 'current server session', 'document_scope': _DOC_SCOPE or None", 1),
        ("        tool = str(body.get('tool') or '')[:60]", """        originating_scope = request.headers.get('X-SPB-Document-Scope')
        if originating_scope and originating_scope != _DOC_SCOPE:
            return jsonify({'ok': False, 'error': 'stale_document_scope', 'message': 'The paint changed since your app-chat message. Wait for a fresh buyer message before using tools.'}), 409
        tool = str(body.get('tool') or '')[:60]""", 1),
    ]


def frontend_edits():
    return [
        ("    var LISTEN_LINE =", """    var docPage = window.crypto.randomUUID(), docEpoch = 0, docScope = docPage + ':0', docReady = null;
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
        docEpoch++; docScope = docPage + ':' + docEpoch; S.seq = -1; S.readyScope = ''; S.waiting = false; S.lastSent = 0;
        var expected = docScope;
        registerDocument().catch(function(){ if (docScope === expected) docReady = null; });
    }
    var LISTEN_LINE =""", 1),
        ("if (cx2() && /^\\/api\\/mcp\\/(status|chat)(\\?|$)/.test(path) && relaying()) path += (path.indexOf('?') < 0 ? '?' : '&') + 'helper=' + mode();", "if (cx2() && /^\\/api\\/mcp\\/(status|chat)(\\?|$)/.test(path) && relaying()) path += (path.indexOf('?') < 0 ? '?' : '&') + 'helper=' + mode() + '&document_scope=' + encodeURIComponent(docScope);", 1),
        ("        var requestedHelper = mode();", "        var requestedHelper = mode(), requestedScope = docScope;", 1),
        ("        if (S.polling || !relaying()) return;", "        if (!relaying()) return;\n        if (S.readyScope !== docScope) { if (!docReady) registerDocument().catch(function(){docReady=null;}); return; }\n        if (S.polling) return;", 1),
        ("requestedHelper !== mode())", "(requestedHelper !== mode() || requestedScope !== docScope))", 1),
        ("    function withCards(entry, e) {", "    function withCards(entry, e) {\n        entry.documentScope = docScope;", 1),
        ("function useCard(entry, i) { var c", "function useCard(entry, i) { if (!entry || entry.documentScope !== docScope) return; var c", 1),
        ("        S.waiting = 'sent'; S.lastSent", "        var expectedScope = docScope;\n        S.waiting = 'sent'; S.lastSent", 1),
        ("        return api('/api/mcp/inbox',", "        return (docReady || registerDocument()).then(function(scope) {\n            if (scope !== docScope || expectedScope !== docScope) throw new Error('The open paint changed. Send your request again.');\n            return api('/api/mcp/inbox',", 1),
        ("{ text: text, helper: mode() }", "{ text: text, helper: mode(), document_scope: expectedScope }", 1),
        ("}).then(function (j) {\n            if (!j || j.ok === false)", "}); }).then(function (j) {\n            if (expectedScope !== docScope) return;\n            if (!j || j.ok === false)", 1),
        ("}, function () { S.waiting = false; push({ role: 'err', text: 'Could not reach the Shokker server.' }); });", "}, function (error) { if (expectedScope !== docScope) return; docReady = null; S.waiting = false; push({ role: 'err', text: error.message || 'Could not reach the Shokker server.' }); });", 1),
        ("window.SpbAiConnect = { mode:", "window.SpbAiConnect = { _sourceChanged: sourceChanged, mode:", 1),
        ("function boot() { refreshStatus();", "function boot() { if (!docReady) registerDocument().catch(function(){docReady=null;}); refreshStatus();", 1),
    ]


def index_edits(original=''):
    edits = [
        ("function httpJson(method, p, body, timeoutMs) {", "let APP_CHAT_SCOPE = null, APP_CHAT_ADVICE = false;\nfunction httpJson(method, p, body, timeoutMs) {", 1),
        ("'X-SPB-MCP-Client': String(CLIENT.name || '').slice(0, 60)", "'X-SPB-MCP-Client': String(CLIENT.name || '').slice(0, 60), ...(p === '/api/mcp/call' && APP_CHAT_SCOPE ? {'X-SPB-Document-Scope': APP_CHAT_SCOPE} : {})", 1),
        ("properties: { text: { type: 'string' }, finishes:", "properties: { text: { type: 'string' }, reply_to: {type:'integer',description:'Copy the seq of the latest buyer message returned by spb_wait_for_message. Required for document-scoped app chat; an earlier paint reply is refused.'}, finishes:", 1),
        ("{ text: t, finishes: Array.isArray(args.finishes)", "{ text: t, reply_to: args.reply_to, finishes: Array.isArray(args.finishes)", 1),
        ("  return { content: [{ type: 'text', text: JSON.stringify({ messages: r.json.messages", "  const newest = (r.json.messages || []).at(-1);\n  if (newest) { APP_CHAT_SCOPE = newest.document_scope || null; APP_CHAT_ADVICE = require('../chatgpt/design-intent.js').classify(newest.text).mode === 'advice'; }\n  return { content: [{ type: 'text', text: JSON.stringify({ reply_to: newest && newest.seq, request_intent: newest ? require('../chatgpt/design-intent.js').classify(newest.text) : undefined, messages: r.json.messages", 1),
        ("then spb_reply with your short answer (questions", "then spb_reply with reply_to equal to the latest message seq and your short answer (questions", 1),
        ("async function callTool(name, args) {", "async function callTool(name, args) {\n  if (APP_CHAT_ADVICE && !READ_ONLY.has(name) && name !== 'spb_reply') return {isError:true,content:[{type:'text',text:'The current buyer message is advice only. Discuss the design; wait for an explicit editing request before changing or rendering it.'}]};", 1),
    ]
    if 'let NATIVE_LAYER_COLOUR = null, DESIGN_INTENT = null, APP_CHAT_ADVICE = false, APP_CHAT_ADVICE_AT = 0;' in original:
        # OA2 1.4.4 already owns advice classification, including read-only kit
        # check/propose exceptions and its kill switch. Add document/reply scope.
        edits[0] = (edits[0][0], 'let APP_CHAT_SCOPE = null;\nfunction httpJson(method, p, body, timeoutMs) {', 1)
        edits[4] = ("  if (DESIGN_INTENT && newest3) {", "  if (newest3) APP_CHAT_SCOPE = newest3.document_scope || null;\n  if (DESIGN_INTENT && newest3) {", 1)
        edits.pop()  # Preserve the source owner's installed advice-only guard.
        edits.append(('JSON.stringify({ request_intent: DESIGN_INTENT && newest3', 'JSON.stringify({ reply_to: newest3 && newest3.seq, request_intent: DESIGN_INTENT && newest3', 1))
    return edits
