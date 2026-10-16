"""A cancelled poll must not consume a command or permit expired execution."""


def edits(source):
    if source == 'server_routes/mcp_bridge_routes.py':
        return [
            ("                c = _QUEUE.popleft()\n                return jsonify({'ok': True, 'call': c, 'build': _build_stamp()})", """                if request.args.get('ack') == '1':
                    c = dict(_QUEUE[0], delivery_ack=True)
                else:
                    c = _QUEUE.popleft()
                return jsonify({'ok': True, 'call': c, 'build': _build_stamp()})""", 1),
            ("    @app.route('/api/mcp/result', methods=['POST'])", """    @app.route('/api/mcp/ack', methods=['POST'])
    def mcp_ack():
        g = page_guard()
        if g:
            return g
        body = request.get_json(silent=True) or {}
        cid, page, scope = body.get('id'), body.get('page'), body.get('document_scope') or ''
        with _COND:
            if not _STATE['enabled'] or not page or page != _STATE.get('owner'):
                return jsonify({'ok': False, 'error': 'delivery_owner_changed'}), 409
            if _DOC_SCOPE and scope != _DOC_SCOPE:
                return jsonify({'ok': False, 'error': 'stale_document_scope'}), 409
            call = next((c for c in _QUEUE if c['id'] == cid), None)
            if not call or cid not in _PENDING or (call.get('document_scope') or '') != scope:
                return jsonify({'ok': False, 'error': 'expired_or_claimed_call'}), 409
            _QUEUE.remove(call)
            _COND.notify_all()
        return jsonify({'ok': True, 'execute': True})

    @app.route('/api/mcp/result', methods=['POST'])""", 1),
        ]
    if source == 'js/spb-mcp-bridge.js':
        return [
            ("    function handle(call) {", """    function acknowledge(call) {
        return new Promise(function(resolve, reject) {
            var done = false, timer;
            function finish(error, value) {
                if (done) return; done = true; clearTimeout(timer);
                if (error) reject(error); else resolve(value);
            }
            timer = setTimeout(function() { finish(new Error('Delivery receipt timed out; this page did not run the request.')); }, 15000);
            api('/api/mcp/ack', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:call.id,page:PAGE,document_scope:documentScope()})}).then(function(r) { finish(null,r); }, function(e) { finish(e); });
        });
    }
    function handle(call, epoch) {
        if (!call.delivery_ack) return runCall(call);
        if (epoch !== pollEpoch || !enabled || !running || (call.document_scope && call.document_scope !== documentScope())) return Promise.resolve();
        return acknowledge(call).then(function(receipt) {
            if (!receipt || !receipt.ok || receipt.execute !== true) return;
            if (epoch !== pollEpoch || !enabled || !running || (call.document_scope && call.document_scope !== documentScope()))
                return post(call.id, {ok:false,error:'The connection or open paint changed before this request started. No changes were applied.'});
            return runCall(call);
        });
    }
    function runCall(call) {""", 1),
            ("'/api/mcp/poll?wait=25&page='", "'/api/mcp/poll?wait=25&ack=1&page='", 1),
            ("return handle(j.call).then(function()", "return handle(j.call, epoch).then(function()", 1),
        ]
    return []
