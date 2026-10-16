/* [SPB-POLISH-D 2026-10-10] wave 4 of the "make it look like a real product" pass. Presentation helpers only; no behaviour changes.
   1. Engine status dot (#serverStatus): the app only toggles its class (online / offline / reconnecting) and a one-word title,
      so the dot had no meaning for a new user. Here its accessible name + tooltip are kept in step with the live state.
   2. Typed glyph icons. A dozen buttons carry a Unicode glyph in their caption ("↻ Refresh", "✓ Apply", "✎ Edit Big", "Actions ▾", "✕", "⛶").
      The glyphs come from different fonts, so next to the line icons they look like leftovers. Exactly like polish-C's Title Case labels this
      only TAGS the element (data-pld-i = icon name, data-pld-t = the words, data-pld-tr = icon goes after the words, data-pld-src = the original
      text); the stylesheet hides the glyph text (font-size:0) and paints the monochrome line icon + the words. textContent, ids and handlers
      are untouched, so anything that reads or rewrites a caption keeps working and the kill switch brings the original glyph straight back.
      Only a fixed list of app-chrome selectors is looked at (never layer names, zone names or anything the user typed).
   Kill switch: body.spb-polish-d-off (CSS), or body.spb-polish-off (all waves). */
(function () {
    'use strict';
    if (window.__spbPolishD) return;
    window.__spbPolishD = true;
    var doc = document;

    var ENGINE = {
        online: ['Render engine connected', 'Render engine connected. Previews and renders are painted by this local engine.'],
        // [S13 2026-10-12 owner: "lose this vibecoded look"] red dot = N failed health checks in a row (paint-booth-5-api-render.js ShokkerAPI._dotState); tooltip names the way out.
        offline: ['Render engine offline', 'Render engine not reachable. It restarts by itself; if it does not, use Fresh Start.'],
        reconnecting: ['Reconnecting to the render engine', 'Reconnecting to the render engine...']
    };

    function labelEngine() {
        var d = doc.getElementById('serverStatus');
        if (!d) return;
        var k = d.classList.contains('reconnecting') ? 'reconnecting' : (d.classList.contains('online') ? 'online' : 'offline');
        var t = ENGINE[k];
        if (d.getAttribute('aria-label') !== t[0]) d.setAttribute('aria-label', t[0]);
        if (d.getAttribute('title') !== t[1]) d.setAttribute('title', t[1]);
        if (d.getAttribute('data-engine-state') !== k) d.setAttribute('data-engine-state', k);
    }

    /* ---- typed glyph -> line icon ---- */
    var GLYPH = {
        '✓': 'check', '✔': 'check', '↻': 'refresh', '↺': 'undo', '✎': 'edit', '✕': 'x', '✖': 'x',
        '⛶': 'expand', '✦': 'sparkle', '☰': 'grip', '↳': 'corner', '▾': 'chevd', '▼': 'chevd', '🎯': 'target', '⋮': 'dotsv', '⇄': 'swap', '⇔': 'swap', '↶': 'undo', '⧉': 'copy', 'ⓘ': 'info',
        '📖': 'book', '📎': 'clip', '📋': 'clipboard', '❓': 'help', '▶': 'play', '🏁': 'flag', '⚙': 'gear', '📁': 'folder', '🎨': 'image'
    };
    var SEL = 'button, .swatch-arrow, .zone-drag-handle, .header-path-status, #drawZoneLabel, .layer-group-header > span, #toast > span, #spbCsCar, .spb-pai-head b, .spb-cs-strip-tg > span';

    function polishOn() {
        var b = doc.body;
        return !!b && !b.classList.contains('spb-polish-off') && !b.classList.contains('spb-polish-d-off');
    }
    function ownText(el) {
        var t = '';
        for (var i = 0; i < el.childNodes.length; i++) { var c = el.childNodes[i]; if (c.nodeType === 3) t += c.nodeValue; }
        return t.replace(/\s+/g, ' ').trim();
    }
    function untag(el) {
        el.removeAttribute('data-pld-i'); el.removeAttribute('data-pld-t'); el.removeAttribute('data-pld-tr'); el.removeAttribute('data-pld-src');
    }
    function tag(el) {
        if (!el || el.nodeType !== 1 || el.hasAttribute('data-pl')) return;       // polish-C already owns this caption
        var raw = ownText(el);
        var src = el.getAttribute('data-pld-src');
        if (src !== null && src === raw) return;                                  // unchanged since it was tagged
        var t = raw.replace(/️/g, '').trim();                                // emoji variation selector
        if (!t || t.length > 40) { if (src !== null) untag(el); return; }
        for (var k = 0; k < el.children.length; k++) { if (/[A-Za-z0-9]/.test(el.children[k].textContent || '')) { if (src !== null) untag(el); return; } }
        var icon = null, label = '', trailing = false, ch;
        ch = t.charAt(0);
        if (t.length > 1 && t.charCodeAt(0) >= 0xD800 && t.charCodeAt(0) <= 0xDBFF) ch = t.slice(0, 2);   // surrogate pair (emoji)
        if (GLYPH[ch]) {
            icon = GLYPH[ch]; label = t.slice(ch.length).trim();
        } else {
            var last = t.charAt(t.length - 1);
            if ((last === '▾' || last === '▼') && t.length > 2) { icon = 'chevd'; trailing = true; label = t.slice(0, -1).trim(); }
            else if (last === '→' && t.length > 3) { icon = 'arrowr'; trailing = true; label = t.slice(0, -1).trim(); }
        }
        if (!icon) { if (src !== null) untag(el); return; }
        el.setAttribute('data-pld-src', raw);
        // an element whose glyph is already hidden by another rule (font-size 0 + own mask icon) is only recorded, never restyled
        var fs = 0;
        try { fs = parseFloat(getComputedStyle(el).fontSize) || 0; } catch (e) { fs = 12; }
        if (fs < 1) { el.removeAttribute('data-pld-i'); el.removeAttribute('data-pld-tr'); el.removeAttribute('data-pld-t'); return; }
        el.setAttribute('data-pld-t', label);
        if (trailing) { el.setAttribute('data-pld-tr', icon); el.removeAttribute('data-pld-i'); }
        else { el.setAttribute('data-pld-i', icon); el.removeAttribute('data-pld-tr'); }
    }
    function scan(root) {
        if (!root) return;
        if (root.nodeType === 3) root = root.parentNode;
        if (!root || root.nodeType !== 1) return;
        if (root.matches && root.matches(SEL)) tag(root);
        var list = root.querySelectorAll ? root.querySelectorAll(SEL) : [];
        for (var i = 0; i < list.length; i++) tag(list[i]);
        var up = root.closest && root.closest(SEL);          // a caption rewritten inside a matching ancestor
        if (up && up !== root) tag(up);
    }

    /* [SPB-PERF2 2026-10-10] a queued node whose ancestor is also queued is covered by that ancestor's subtree scan (tagging is idempotent): scan each added subtree once. A bulk insert (the finish picker adds ~35k nodes) used to be scanned node by node. Kill switch window.SPB_PERF2_OFF = true. */
    function p2Roots(q) {
        if (window.SPB_PERF2_OFF === true || q.length < 64 || typeof Set !== 'function') return q;
        var set = new Set(q), out = [], i, n, p;
        for (i = 0; i < q.length; i++) { n = q[i]; p = n && n.parentNode; while (p && !set.has(p)) p = p.parentNode; if (!p) out.push(n); }
        return out;
    }
    var queue = [], scheduled = false;
    function flush() {
        scheduled = false;
        var q = queue; queue = [];
        if (!polishOn()) return;
        q = p2Roots(q);
        for (var i = 0; i < q.length; i++) { try { scan(q[i]); } catch (e) { /* presentation only */ } }
    }
    function enqueue(n) {
        queue.push(n);
        if (!scheduled) { scheduled = true; (window.requestAnimationFrame || setTimeout)(flush, 60); }
    }

    function init() {
        var d = doc.getElementById('serverStatus');
        if (d) {
            labelEngine();
            try {
                new MutationObserver(labelEngine).observe(d, { attributes: true, attributeFilter: ['class', 'title'] });
            } catch (e) { /* observer unavailable: the static label above still applies */ }
        }
        if (!doc.body) return;
        try { scan(doc.body); } catch (e) { /* presentation only */ }
        try {
            var mo = new MutationObserver(function (muts) {
                for (var i = 0; i < muts.length; i++) {
                    var m = muts[i];
                    if (m.type === 'characterData') { enqueue(m.target); continue; }
                    for (var j = 0; j < m.addedNodes.length; j++) {
                        var n = m.addedNodes[j];
                        if (n.nodeType === 1 || n.nodeType === 3) enqueue(n);
                    }
                }
            });
            mo.observe(doc.body, { childList: true, subtree: true, characterData: true });
        } catch (e) { /* the first scan above still applied */ }
        setTimeout(function () { try { scan(doc.body); } catch (e) { /* presentation only */ } }, 2500);
    }

    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init);
    else init();
})();
