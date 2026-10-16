"""Bind tool delivery to the same document as the in-app conversation."""


def edits(source):
    if source == 'js/spb-ai-connect.js':
        return [("window.SpbAiConnect = { _sourceChanged:",
                 "window.SpbAiConnect = { documentScope: function () { return docScope; }, _sourceChanged:", 1),
                ("        if (relaying() && window.SpbMcpBridge) { try { window.SpbMcpBridge.setEnabled(true); } catch (e) {} }", """        if (relaying() && window.SpbMcpBridge) {
            // Explicit helper selection reclaims this document before tool polling.
            // A superseded page must not poll using its previously accepted scope.
            try { window.SpbMcpBridge.setEnabled(false); } catch (e) {}
            sourceChanged();
            var selectedScope = docScope, selectedMode = m;
            docReady.then(function () {
                if (docScope === selectedScope && mode() === selectedMode && relaying()) window.SpbMcpBridge.setEnabled(true);
            }).catch(function () { refreshStatus(); redraw(); });
        }""", 1)]
    if source == 'js/spb-mcp-bridge.js':
        return [
            ("    function handle(call) {", """    function documentScope() {
        return window.SpbAiConnect && window.SpbAiConnect.documentScope ? window.SpbAiConnect.documentScope() : '';
    }
    function handle(call) {
        if (call.document_scope && call.document_scope !== documentScope())
            return post(call.id, {ok:false,error:'The open paint changed before this call arrived. No action was run.'});""", 1),
            (" + (claimNext ? '&claim=1' : ''); claimNext = false;",
             " + '&document_scope=' + encodeURIComponent(documentScope()) + (claimNext ? '&claim=1' : ''); claimNext = false;", 1),
        ]
    if source == 'server_routes/mcp_bridge_routes.py':
        return [
            ("        pid = str(request.args.get('page') or '')[:40]", """        # The conversation's committed document owns tool delivery, too.
        # A second tab's claim must not steal calls for another document.
        poll_scope = request.args.get('document_scope') or ''
        if _DOC_SCOPE and poll_scope != _DOC_SCOPE:
            return jsonify({'ok': True, 'enabled': _STATE['enabled'], 'superseded': True})
        pid = str(request.args.get('page') or '')[:40]""", 1),
            ("if request.args.get('claim') == '1' or not owner_alive or _STATE.get('owner') == pid:",
             "if (_DOC_SCOPE and poll_scope == _DOC_SCOPE) or request.args.get('claim') == '1' or not owner_alive or _STATE.get('owner') == pid:", 1),
            ("            if pid and _STATE.get('owner') != pid:",
             "            if (_DOC_SCOPE and poll_scope != _DOC_SCOPE) or (pid and _STATE.get('owner') != pid):", 1),
            ("call = {'id': cid, 'tool': tool, 'args': body.get('args') if isinstance(body.get('args'), dict) else {}}",
             "call = {'id': cid, 'tool': tool, 'args': body.get('args') if isinstance(body.get('args'), dict) else {}, 'document_scope': _DOC_SCOPE or None}", 1),
        ]
    return []
