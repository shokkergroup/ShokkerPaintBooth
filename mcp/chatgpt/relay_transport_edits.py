"""Bound read polling and recover availability without replaying writes."""

BEFORE_API = """        return fetch(BASE + path, opt).then(function (r) { return r.json(); });"""
AFTER_API = r"""        // Only status/chat reads may time out and retry; inbox/tool writes never do.
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
        });"""

def edits(relative):
    if relative != 'js/spb-ai-connect.js':
        return []
    return [
        ('    var LISTEN_LINE =', '    var transportRead = 0, transportSettled = 0;\n    var LISTEN_LINE =', 1),
        (BEFORE_API, AFTER_API, 1),
        ('S.status = null; S.listening = false; S.client = \'\'; }',
         "S.status = null; S.listening = false; S.client = ''; S.transportUnavailable = false; }", 1),
        ("        if (!S.seq) { api('/api/mcp/chat?after=999999999&wait=0').then(function (j) { S.seq = (j && j.seq) || 0; S.polling = false; S.seq = S.seq || -1; poll(); }, function () { S.polling = false; setTimeout(poll, 4000); }); return; }",
         "        if (!S.seq) { var initialHelper = mode(), initialScope = docScope; api('/api/mcp/chat?after=999999999&wait=0').then(function (j) { S.polling = false; if (initialHelper !== mode() || initialScope !== docScope) { poll(); return; } S.seq = (j && j.seq) || 0; S.seq = S.seq || -1; poll(); }, function () { S.polling = false; setTimeout(poll, 4000); }); return; }", 1),
        ('        var on = S.status && S.status.enabled;', '''        if (!window.SPB_RELAY_TRANSPORT_OFF && S.transportUnavailable)
            return '<div class="spb-aic-st">The connection to SPB could not be checked. Your draft is kept. A submitted request may still be waiting; check the connected chat before sending it again. We will check again without repeating your requests. <button class="spb-aic-link" data-act="aic-offline">Use Offline Helper</button></div>';
        var on = S.status && S.status.enabled;''', 1),
    ]
