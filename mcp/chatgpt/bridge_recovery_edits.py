"""Private recovery delta; never interrupts or retries a delivered paint call."""
def edits():
    return [
        ("    function loop() {", """    // SPB-93 private acceptance 2026-10-09: stalled poll prevented native
    // read receipts; off/on could not restart it. Bound only transport polling.
    var pollEpoch = 0, pollAbort = null, retryTimer = null, handling = false;
    function stopPolling() {
        pollEpoch++; running = false;
        if (retryTimer != null) { clearTimeout(retryTimer); retryTimer = null; }
        if (pollAbort) { pollAbort(); pollAbort = null; }
    }
    function pollFetch(url) {
        return new Promise(function (resolve, reject) {
            var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
            var done = false, timer;
            function finish(error, value) {
                if (done) return; done = true; clearTimeout(timer);
                if (pollAbort === cancel) pollAbort = null;
                if (error) reject(error); else resolve(value);
            }
            function cancel() { if (controller) controller.abort(); finish(new Error('Poll cancelled')); }
            pollAbort = cancel;
            timer = setTimeout(cancel, 45000);
            fetch(url, controller ? {signal: controller.signal} : {}).then(function(r) {
                return r.json();
            }).then(function(j) { finish(null, j); }, function(e) { finish(e); });
        });
    }
    function loop() {""", 1),
        ("        fetch(BASE + q).then(function (r) { return r.json(); }).then(function (j) {", """        var epoch = pollEpoch;
        pollFetch(BASE + q).then(function (j) {
            if (epoch !== pollEpoch || !enabled || !running) return;""", 1),
        ("            if (j && j.call) return handle(j.call).then(loop);", """            if (j && j.call) {
                handling = true;
                return handle(j.call).then(function() {
                    handling = false;
                    if (epoch === pollEpoch) loop(); else start();
                }, function() { handling = false; running = false; start(); });
            }""", 1),
        ("        }).catch(function () { setTimeout(loop, 3000); });", """        }).catch(function () {
            if (epoch !== pollEpoch || !enabled || !running) return;
            stats.connected = false; emit();
            retryTimer = setTimeout(function() { retryTimer = null; loop(); }, 3000);
        });""", 1),
        ("function start() { if (running || !enabled) return;", "function start() { if (running || !enabled || handling) return;", 1),
        ("last = s; enabled = !!s.enabled; if (enabled) start(); emit(); return s;", "last = s; enabled = !!s.enabled; stopPolling(); if (enabled) start(); emit(); return s;", 1),
    ]
