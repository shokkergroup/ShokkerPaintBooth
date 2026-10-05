/* ============================================================================
 * SPB ERROR SURFACE — tell the painter when something broke
 *                                                        2026-08-05, Claude
 *
 * THE PROBLEM
 *   A thrown error in a tool handler kills that handler and nothing else. The
 *   button still highlights, the cursor still changes, and the tool simply does
 *   nothing. To the painter that is indistinguishable from "I clicked wrong",
 *   so they try again, then again, then conclude the app is flaky. Meanwhile the
 *   real message sat in a console nobody has open.
 *
 *   This has a specific cost in this app: an error mid-stroke can leave a zone
 *   mask half-written, and the painter keeps working on top of it.
 *
 * WHAT THIS DOES
 *   Catches window errors and unhandled promise rejections, shows ONE readable
 *   toast, and keeps the details in a ring buffer for diagnosis.
 *
 * WHAT IT DOES NOT DO
 *   - It does not swallow anything. The console still gets the full error;
 *     this only adds a visible signal.
 *   - It does not nag. The same message re-toasts at most once every 15s, and
 *     it stops toasting entirely after 5 distinct errors in a session — at that
 *     point something is badly wrong and more toasts do not help. The counter
 *     is in the badge instead.
 *   - It does not claim to know what broke. The message says which file and
 *     line, because "something went wrong" is not actionable.
 * ==========================================================================*/
(function () {
    'use strict';

    const RING_MAX = 40;
    const REPEAT_MS = 15000;
    const MAX_TOASTS = 5;

    const ring = [];
    const lastShown = Object.create(null);
    let toastCount = 0;

    function shortSource(src, line) {
        if (!src) return '';
        let f = String(src).split('/').pop() || '';
        f = f.split('?')[0];
        return line ? (f + ':' + line) : f;
    }

    function record(kind, message, source, line, error) {
        const entry = {
            kind: kind,
            message: String(message || 'unknown error').slice(0, 300),
            where: shortSource(source, line),
            stack: error && error.stack ? String(error.stack).slice(0, 1200) : '',
            at: new Date().toISOString()
        };
        ring.push(entry);
        if (ring.length > RING_MAX) ring.shift();
        return entry;
    }

    function notify(entry) {
        const key = entry.message + '|' + entry.where;
        const now = Date.now();
        if (lastShown[key] && (now - lastShown[key]) < REPEAT_MS) return;
        lastShown[key] = now;

        if (toastCount >= MAX_TOASTS) { updateBadge(); return; }
        toastCount++;

        const where = entry.where ? (' — ' + entry.where) : '';
        const text = 'Something went wrong' + where +
                     '. That action may not have completed. Details: Ctrl+Shift+E';
        try {
            if (typeof window.showToast === 'function') window.showToast(text, 'error');
            else console.warn('[SPB]', text);
        } catch (e) {
            console.warn('[SPB]', text);
        }
        updateBadge();
    }

    // [10.0.0 2026-08-10 — owner: "a persistent ERROR message that WILL NOT EVER go away.
    //  It doesn't say what the error is but it's annoying and in a bad location covering
    //  up text"] Four separate defects, all mine, all fixed here:
    //
    //  1. RESOURCE FAILURES WERE BADGED. The comment in the window.error handler says a
    //     404'd image is "not worth interrupting a painter" — then it called updateBadge()
    //     anyway. One <img src=""> in paint-booth-v2.html (since fixed) resolved to the
    //     page URL, failed on every boot, and pinned the badge at "1 error" forever. The
    //     badge now counts ONLY real code errors; resource failures are still recorded and
    //     still visible in the report, they just do not raise an alarm.
    //  2. NO WAY TO DISMISS. There is an explicit x now, and it stays dismissed until a
    //     NEW error arrives (dismissing does not blind you to the next one).
    //  3. IT NEVER SAID WHAT BROKE. Clicking used to print to a console the owner does not
    //     have open and toast "printed to the console". It now opens a readable panel with
    //     the actual message, file:line and time, plus one-click copy.
    //  4. BAD POSITION. bottom-LEFT sat on top of the zone panel's own footer controls.
    //     Moved to bottom-right, below the toast lane (toast is bottom:118px right:16px).
    function badgeWorthy() {
        return ring.filter(function (e) { return e.kind !== 'resource'; });
    }
    let dismissedAt = 0;

    function updateBadge() {
        const real = badgeWorthy();
        let el = document.getElementById('spbErrorBadge');
        if (!real.length || real.length <= dismissedAt) {
            if (el) el.style.display = 'none';
            return;
        }
        if (!el) {
            el = document.createElement('div');
            el.id = 'spbErrorBadge';
            el.style.cssText = 'position:fixed; bottom:10px; right:16px; z-index:99998;' +
                'display:flex; align-items:center; gap:6px;' +
                'padding:3px 6px 3px 9px; border-radius:10px; font-size:11px; font-weight:600;' +
                'background:#7f1d1d; color:#fecaca; user-select:none;' +
                'box-shadow:0 2px 8px rgba(0,0,0,0.35);';
            const label = document.createElement('span');
            label.id = 'spbErrorBadgeLabel';
            label.style.cursor = 'pointer';
            label.title = 'Click to see what went wrong (Ctrl+Shift+E)';
            label.onclick = showReport;
            const x = document.createElement('span');
            x.textContent = '×';
            x.title = 'Dismiss (comes back if a new error happens)';
            x.style.cssText = 'cursor:pointer; font-weight:700; font-size:13px;' +
                'line-height:1; padding:0 3px; opacity:0.75;';
            x.onmouseover = function () { x.style.opacity = '1'; };
            x.onmouseout = function () { x.style.opacity = '0.75'; };
            x.onclick = function (ev) {
                ev.stopPropagation();
                dismissedAt = badgeWorthy().length;
                updateBadge();
            };
            el.appendChild(label);
            el.appendChild(x);
            document.body.appendChild(el);
        }
        el.style.display = 'flex';
        const lbl = document.getElementById('spbErrorBadgeLabel');
        if (lbl) {
            lbl.textContent = '⚠ ' + real.length + (real.length === 1 ? ' error' : ' errors');
        }
    }

    function showReport() {
        const lines = ring.slice().reverse().map(function (e, i) {
            return (i + 1) + '. [' + e.kind + '] ' + e.message +
                   (e.where ? '\n   at ' + e.where : '') +
                   '\n   ' + e.at;
        });
        const text = lines.join('\n\n') || 'No errors recorded.';
        console.group('%cSPB errors this session', 'color:#f87171;font-weight:bold');
        ring.forEach(function (e) { console.log(e); });
        console.groupEnd();
        showReportPanel(text);
        return text;
    }

    // Show the actual error ON SCREEN. "Details are in the console" is useless to
    // someone painting a car; they will never open F12, so the badge was effectively
    // saying "something broke, good luck".
    function showReportPanel(text) {
        let panel = document.getElementById('spbErrorPanel');
        if (panel) { panel.remove(); }
        panel = document.createElement('div');
        panel.id = 'spbErrorPanel';
        panel.style.cssText = 'position:fixed; inset:0; z-index:99999;' +
            'background:rgba(4,8,14,0.88); display:flex; align-items:center;' +
            'justify-content:center; padding:20px;';
        const box = document.createElement('div');
        box.style.cssText = 'width:min(760px,94vw); max-height:82vh; display:flex;' +
            'flex-direction:column; background:#0e1319; color:#eaf0f8;' +
            'border:1px solid #2b3645; border-radius:10px; overflow:hidden;' +
            'font:12px/1.5 system-ui,Segoe UI,sans-serif;';
        const head = document.createElement('div');
        head.style.cssText = 'display:flex; align-items:center; justify-content:space-between;' +
            'gap:10px; padding:10px 12px; border-bottom:1px solid #2b3645; background:#0a0e14;';
        head.innerHTML = '<strong style="font-size:13px;color:#f0a8a8;">What went wrong</strong>';
        const btns = document.createElement('div');
        btns.style.cssText = 'display:flex; gap:6px;';
        function mkBtn(label, fn) {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = label;
            b.style.cssText = 'font:11px system-ui; padding:4px 10px; border-radius:6px;' +
                'border:1px solid #2b3645; background:#141c28; color:#eaf0f8; cursor:pointer;';
            b.onclick = fn;
            return b;
        }
        btns.appendChild(mkBtn('Copy', function () {
            const done = function () {
                if (typeof window.showToast === 'function') window.showToast('Error details copied', 'success');
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(done).catch(function () {});
            } else {
                const ta = document.createElement('textarea');
                ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
                document.body.appendChild(ta); ta.select();
                try { document.execCommand('copy'); done(); } catch (e) {}
                ta.remove();
            }
        }));
        btns.appendChild(mkBtn('Clear all', function () {
            ring.length = 0; toastCount = 0; dismissedAt = 0; updateBadge(); panel.remove();
        }));
        btns.appendChild(mkBtn('Close', function () { panel.remove(); }));
        head.appendChild(btns);
        const body = document.createElement('pre');
        body.textContent = text;
        body.style.cssText = 'margin:0; padding:12px; overflow:auto; white-space:pre-wrap;' +
            'word-break:break-word; font:11px/1.55 Consolas,monospace; color:#cbd5e1;';
        const foot = document.createElement('div');
        foot.style.cssText = 'padding:8px 12px; border-top:1px solid #2b3645; color:#9ba8b8; font-size:10.5px;';
        foot.textContent = 'Newest first. "resource" entries are failed image/script loads — ' +
            'usually harmless. Copy this if you report a bug.';
        box.appendChild(head); box.appendChild(body); box.appendChild(foot);
        panel.appendChild(box);
        panel.addEventListener('click', function (e) { if (e.target === panel) panel.remove(); });
        document.body.appendChild(panel);
    }

    window.addEventListener('error', function (ev) {
        // Resource load failures (img/script 404) also fire here with no `error`
        // object; they are worth recording but not worth interrupting a painter.
        if (ev && ev.target && ev.target !== window && ev.target.tagName) {
            record('resource', (ev.target.tagName + ' failed to load: ' +
                   (ev.target.src || ev.target.href || '?')), '', 0, null);
            updateBadge();
            return;
        }
        notify(record('error', ev && ev.message, ev && ev.filename, ev && ev.lineno,
                      ev && ev.error));
    }, true);

    window.addEventListener('unhandledrejection', function (ev) {
        const r = ev && ev.reason;
        const msg = (r && (r.message || r)) || 'promise rejected';
        notify(record('promise', msg, (r && r.fileName) || '', (r && r.lineNumber) || 0, r));
    });

    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.shiftKey && (e.key === 'E' || e.key === 'e')) {
            e.preventDefault();
            showReport();
        }
    });

    window.SPBErrors = {
        recent: function () { return ring.slice(); },
        report: showReport,
        clear: function () { ring.length = 0; toastCount = 0; dismissedAt = 0; updateBadge(); },
        // Exposed so a regression test can assert the resource/real split without
        // having to synthesise a browser error event.
        _badgeWorthy: badgeWorthy
    };
})();
