/* [SPB-POLISH-C 2026-10-09] UI polish wave 3 - the one thing CSS cannot do.
   Some labels are TYPED in ALL CAPS in the markup ("SPEC SCULPT", "DUPE", "RESTRICT TO LAYERS"); text-transform cannot lower-case them.
   This tags those few static labels with data-pl="Title Case" and data-pl-src="<original>"; the stylesheet hides the original glyphs
   (font-size:0) and paints the tag instead. textContent / ids / handlers are NOT touched, so nothing that reads a label breaks, and the
   kill switch (body.spb-polish-off or body.spb-polish-c-off) brings the original text straight back.
   Only a fixed list of app-chrome classes is looked at (never layer names, zone names or anything the user typed).
   Pure presentation; no behaviour. */
(function () {
    'use strict';
    if (window.__spbPolishC) return;
    window.__spbPolishC = true;
    var doc = document;

    var SEL = [
        '.header-command-btn', '.frac-lbl', '.frac-lbl-long', '.spb-mode-opt', '.spb-rh-label', '#btnToolbarModeZone', '#btnToolbarModeLayer',
        '.studio-label', '.spb-zone-popout-title', '.section-header-label', '.hex-label', '.layer-act-btn', '.zoom-btn', '.spec-channel-dock-label',
        '.color-selector-label', '#zoneEditorFloat .color-selector div', '#zoneEditorFloat .color-selector button', '#zoneEditorFloat .quick-color-btn', '#advancedToolbar > span', '.atlas-zoom-back', '.atlas-tag-lucky'
    ].join(',');
    var KEEP = { 'RGB': 1, 'PNG': 1, 'TGA': 1, 'PSD': 1, 'RENDER': 1, 'TGA/PNG/JPEG': 1, 'PSD/XCF/ORA': 1, 'HEX': 0 };
    var SMALL = { to: 1, from: 1, of: 1, the: 1, and: 1, or: 1, for: 1, in: 1, on: 1, a: 1, an: 1, at: 1, by: 1 };

    function titleCase(s) {
        var words = s.split(/(\s+)/);
        var first = true;
        for (var i = 0; i < words.length; i++) {
            var w = words[i];
            if (!w || /^\s+$/.test(w)) continue;
            var letters = w.replace(/[^A-Za-z]/g, '');
            var keepCaps = letters.length <= 2 && /[A-Z]/.test(letters) && letters.length > 0 && /^(H|V|FX|PX|UV|ID|AI)$/.test(letters);
            if (keepCaps) { words[i] = w; first = false; continue; }
            var low = w.toLowerCase();
            if (!first && SMALL[low]) { words[i] = low; continue; }
            // capitalise the first letter, keep any leading punctuation / trailing colon or arrow
            words[i] = low.replace(/[a-z]/, function (c) { return c.toUpperCase(); });
            first = false;
        }
        return words.join('');
    }

    function polishOn() {
        var b = doc.body;
        return !!b && !b.classList.contains('spb-polish-off') && !b.classList.contains('spb-polish-c-off');
    }

    function ownText(el) {
        var t = '';
        for (var i = 0; i < el.childNodes.length; i++) { var c = el.childNodes[i]; if (c.nodeType === 3) t += c.nodeValue; }
        return t.replace(/\s+/g, ' ').trim();
    }
    function tag(el) {
        if (!el || el.nodeType !== 1) return;
        for (var k = 0; k < el.children.length; k++) { if (/[A-Za-z]/.test(el.children[k].textContent || '')) return; }   // a label with real words inside children is left alone (icon-only children are fine)
        var t = ownText(el);
        var src = el.getAttribute('data-pl-src');
        if (src !== null && src === t) return;                       // already tagged and unchanged
        if (!t || t.length > 30 || KEEP[t] === 1 || t !== t.toUpperCase() || !/[A-Z]{2}/.test(t)) {   // not typed in caps (any more)
            if (src !== null) { el.removeAttribute('data-pl'); el.removeAttribute('data-pl-src'); }
            return;
        }
        el.setAttribute('data-pl-src', t);
        el.setAttribute('data-pl', titleCase(t));
    }

    function scan(root) {
        if (!root) return;
        if (root.nodeType === 3) root = root.parentNode;
        if (!root || root.nodeType !== 1) return;
        if (root.matches && root.matches(SEL)) tag(root);
        var list = root.querySelectorAll ? root.querySelectorAll(SEL) : [];
        for (var i = 0; i < list.length; i++) tag(list[i]);
        // a label may have changed text inside a matching ancestor (e.g. a button whose caption is rewritten)
        var up = root.closest && root.closest(SEL);
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
        for (var i = 0; i < q.length; i++) { try { scan(q[i]); } catch (e) {} }
    }
    function enqueue(n) {
        queue.push(n);
        if (!scheduled) { scheduled = true; (window.requestAnimationFrame || setTimeout)(flush, 60); }
    }

    function start() {
        if (!doc.body) return;
        try { scan(doc.body); } catch (e) {}
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
        } catch (e) {}
        // late-built panels (zone popout, layer cards) are caught by the observer; one more sweep after boot settles
        setTimeout(function () { try { scan(doc.body); } catch (e) {} }, 2500);
    }
    // The bottom tool-options bar is now one fixed-height row that scrolls sideways when a tool has more options than fit.
    // A mouse wheel over its empty/label areas scrolls it (inputs, selects and sliders keep their own wheel behaviour).
    doc.addEventListener('wheel', function (e) {
        try {
            if (!polishOn() || e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
            var t = e.target; if (!t || !t.closest) return;
            var bar = t.closest('#toolOptionsBar'); if (!bar || bar.scrollWidth <= bar.clientWidth + 1) return;
            if (t.closest('select, textarea, input[type="range"], input[type="number"]')) return;
            bar.scrollLeft += e.deltaY; e.preventDefault();
        } catch (er) {}
    }, { passive: false });
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
})();
