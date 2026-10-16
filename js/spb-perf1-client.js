/* [SPB-PERF1 2026-10-10 PERF-BOOT lane] client-side speed fixes that must not touch other lanes' files.
 * ONE kill switch for everything in this file: window.SPB_PERF1_OFF === true (or localStorage SPB_PERF1_OFF = '1'; the inline <head> script folds both into the window flag).
 * Three independent modules, each with its own audit comment below:
 *   A. eyedropper dock class   - inline-style write 36.5 ms -> 0.06 ms of style recalc, cursor-like loop 16.8 -> 59.7 fps
 *   B. :has() -> tag classes   - renderZones 154 -> 39 ms, select zone 620 -> 106, modal toggle 77 -> 2.7, picker close 82 -> 2.6 (style recalc, interleaved medians)
 *   C. union-mask memo         - 4-layer getZoneSourceLayersUnionMask call 20.0 -> 5.7 ms (the rest is the 4 MB copy-on-return), byte-identical results
 * Numbers and method: _easy_claude_work/perf_boot/PROGRESS.md and BASELINE.md.
 *
 * A. Eyedropper dock class (replaces two costly CSS :has() rules).
 *    paint-booth-v2.css used to show the dock with
 *        .eyedropper-dock-top:has(#eyedropperInfo[style*="display: block"]),
 *        .eyedropper-dock-top:has(#eyedropperInfo:not([style*="display: none"])) { display:flex }
 *    A :has() that reads a style ATTRIBUTE makes the browser re-check it after EVERY inline-style write anywhere in the page, so each brush-cursor
 *    move, slider drag and HUD update paid a whole-page style recalc (REV-LENS lane measured ~50 ms per frame: 13 fps -> 60+ fps once avoided).
 *    Now this module mirrors the SAME test (the two attribute-substring checks, copied literally) onto a class on the dock, and the CSS keys on that class.
 *    No other file changes: every place that sets #eyedropperInfo.style.display keeps working because we watch that one element's style attribute
 *    (a MutationObserver on ONE node, attributeFilter style - it costs nothing on other elements).
 *    Audit: style recalc per inline write and brush-cursor fps, before -> after, are in _easy_claude_work/perf_boot/PROGRESS.md.
 */
(function () {
    'use strict';
    var W = window;
    if (W.SPB_PERF1_OFF === true) return;
    if (W.__spbPerf1Client) return;
    W.__spbPerf1Client = { version: '2026-10-10-p1', dock: false };

    // ------------------------------------------------------------------ A. dock class
    (function dockClass() {
        var CLS = 'spb-perf1-info';
        var watched = null, attrObs = null, dockObs = null;

        function dockEl() { return document.getElementById('eyedropperDockTop'); }
        function infoEl() { return document.getElementById('eyedropperInfo'); }

        // literal copy of the old CSS test: flex if the info's style attribute says "display: block", or if it does NOT say "display: none"
        function wantShown(dock, info) {
            if (!dock || !info || !dock.contains(info)) return false;
            var a = info.getAttribute('style') || '';
            return a.indexOf('display: block') !== -1 || a.indexOf('display: none') === -1;
        }

        function sync() {
            if (W.SPB_PERF1_OFF === true) return;
            var dock = dockEl(), info = infoEl();
            if (!dock) return;
            // follow the info node if it was replaced or moved
            if (info !== watched) {
                if (attrObs) { try { attrObs.disconnect(); } catch (e) {} }
                watched = info;
                if (info && attrObs) { try { attrObs.observe(info, { attributes: true, attributeFilter: ['style'] }); } catch (e2) {} }
            }
            var want = wantShown(dock, info);
            if (dock.classList.contains(CLS) !== want) dock.classList.toggle(CLS, want);
        }

        function start() {
            var dock = dockEl();
            if (!dock || typeof MutationObserver !== 'function') return false;
            attrObs = new MutationObserver(sync);
            dockObs = new MutationObserver(sync);
            // the info node moves INTO the dock (dockEyedropperInfoToTopToolbar) and the dock moves into #previewBottomBar: watch the dock's own children only
            try { dockObs.observe(dock, { childList: true }); } catch (e) { return false; }
            sync();
            W.__spbPerf1Client.dock = true;
            return true;
        }

        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
        else start();
        W.__spbPerf1Client.syncDock = sync;
    })();

    // ------------------------------------------------------------------ B. :has() -> tag classes
    /* Every remaining static :has() rule made Blink re-check ancestors/siblings after each DOM insert/removal and class toggle: measured on the owner-sized page,
     * renderZones() 185 -> 32 ms of style recalc, renderZoneDetail() 90 -> 28, selecting a zone 512 -> 96, closing the finish picker 868 -> 2 (the
     * body:has(.modal-overlay.active) rule), any modal open/close ~45 -> <1 ms. Here ONE MutationObserver keeps a class on exactly the elements the old :has()
     * matched (each test below is the literal :has() argument), and the CSS keys on the class with the SAME specificity. The CSS rewrite lives in the stylesheets
     * (search "spb-pf-"); the original rules are in css/spb-perf1-legacy-has.css and load only under the SPB_PERF1_OFF kill switch.
     * Left as :has() on purpose: .intensity-control-group:has(input:active) and .shokk-tag-label:has(.shokk-tag-checkbox:checked) (state-driven, ~free). */
    (function hasTags() {
        var T = 'spb-pf-';
        var FAM = [   // [element selector, tag, test(el)]  - the test is the literal former :has() argument
            ['.stack-control-group', 'hr', function (e) { return !!e.querySelector('input[type="range"]'); }],
            ['.stack-control-group', 'hn', function (e) { return !!e.querySelector('input[type="number"]'); }],
            ['.zone-finish-row', 'hbm', function (e) { return !!e.querySelector(':scope > label[title^="BASE MATERIAL"]'); }],
            ['.zone-finish-row', 'hbcm', function (e) { return !!e.querySelector('select[onchange^="setZoneBaseColorMode"]'); }],
            ['.layer-row-details', 'hact', function (e) { return !!e.querySelector('.layer-act-btn'); }],
            ['.layer-row-details > div', 'hactc', function (e) { return !!e.querySelector(':scope > .layer-act-btn'); }],
            ['.layer-row-details > div', 'nokid', function (e) { return !e.firstElementChild; }],          // :not(:has(> *)) - tagged POSITIVELY so the rule stays inert when the tagger is off
            ['.spec-patterns-section div', 'hsls', function (e) { return !!e.querySelector(':scope > .spec-layer-stack'); }],
            ['.spb-easy-whole-stack', 'nomix', function (e) { return !e.querySelector('.spb-easy-mix-row'); }]          // :not(:has(.spb-easy-mix-row))
        ];
        var ALL = '.stack-control-group, .zone-finish-row, .layer-row-details, .layer-row-details > div, .spec-patterns-section div, .spb-easy-whole-stack';
        var SINGLE_Q = '.modal-overlay, #splitViewContainer, #vtModeBrush, #settingsImportSpecHeading';
        var obs = null, brushParent = null, sihSecs = [];

        // one pass = one callback: ev dedupes element evaluations, tr the subtrees already scanned, up the ancestor chains already walked
        function newPass() { return { ev: new Set(), tr: new Set(), up: new Set() }; }
        function evalEl(e, P) {
            if (P.ev.has(e)) return; P.ev.add(e);
            for (var i = 0; i < FAM.length; i++) {
                var f = FAM[i];
                if (e.matches(f[0])) {
                    var want = f[2](e), cl = T + f[1];
                    if (e.classList.contains(cl) !== want) e.classList.toggle(cl, want);
                }
            }
        }
        function evalTree(root, P) {
            if (P.tr.has(root)) return; P.tr.add(root);
            evalEl(root, P);
            if (root.firstElementChild) {
                var l = root.querySelectorAll(ALL);
                for (var i = 0; i < l.length; i++) evalEl(l[i], P);
            }
        }
        function evalUp(node, P) {          // the changed node and its ancestors: a family element above it may have gained / lost its range, button, ...
            for (var n = node; n && n.nodeType === 1 && n !== document.body; n = n.parentElement) { if (P.up.has(n)) break; P.up.add(n); evalEl(n, P); }
        }
        function singles() {
            var b = document.body; if (!b) return;
            var m = !!document.querySelector('.modal-overlay.active');            // body:has(.modal-overlay.active)
            if (b.classList.contains(T + 'modal') !== m) b.classList.toggle(T + 'modal', m);
            var sv = document.getElementById('splitViewContainer'), s = !!(sv && sv.classList.contains('spb-focus-source'));   // body:has(#splitViewContainer.spb-focus-source)
            if (b.classList.contains(T + 'split') !== s) b.classList.toggle(T + 'split', s);
            var vb = document.getElementById('vtModeBrush'), vp = vb ? vb.parentElement : null;   // .spb-tb-cluster:has(> #vtModeBrush)
            if (vp !== brushParent) { if (brushParent) brushParent.classList.remove(T + 'hvmb'); if (vp) vp.classList.add(T + 'hvmb'); brushParent = vp; }
            var h = document.getElementById('settingsImportSpecHeading'), secs = [];   // .settings-section:has(#settingsImportSpecHeading)
            for (var n = h && h.parentElement; n; n = n.parentElement) if (n.classList && n.classList.contains('settings-section')) secs.push(n);
            sihSecs.forEach(function (o) { if (secs.indexOf(o) === -1) o.classList.remove(T + 'hsih'); });
            secs.forEach(function (o) { if (!o.classList.contains(T + 'hsih')) o.classList.add(T + 'hsih'); });
            sihSecs = secs;
        }
        function inPicker(n) { try { return !!(n && n.closest && n.closest('.swatch-popup')); } catch (e) { return false; } }   // 2,800 finish cards: no :has() family lives there
        function onMut(records) {
            if (W.SPB_PERF1_OFF === true) return;
            try {
                var P = newPass(), needSingles = false;
                for (var r = 0; r < records.length; r++) {
                    var rec = records[r], t = rec.target;
                    if (rec.type === 'attributes') {
                        if (t.classList && (t.classList.contains('modal-overlay') || t.id === 'splitViewContainer')) needSingles = true;
                        evalEl(t, P);
                        continue;
                    }
                    if (inPicker(t)) continue;
                    evalUp(t, P);
                    var k, a;
                    for (k = 0; k < rec.addedNodes.length; k++) { a = rec.addedNodes[k]; if (a.nodeType === 1) { evalTree(a, P); if (!needSingles && (a.matches(SINGLE_Q) || (a.firstElementChild && a.querySelector(SINGLE_Q)))) needSingles = true; } }
                    for (k = 0; k < rec.removedNodes.length; k++) { a = rec.removedNodes[k]; if (a.nodeType === 1 && !needSingles && (a.matches(SINGLE_Q) || (a.firstElementChild && a.querySelector(SINGLE_Q)))) needSingles = true; }
                }
                if (needSingles) singles();
            } catch (e) { /* never break the page for a styling aid */ }
            try { obs.takeRecords(); } catch (e2) {}          // drop the records our own class writes just produced
        }
        function start() {
            if (!document.body || typeof MutationObserver !== 'function') return;
            obs = new MutationObserver(onMut);
            try {
                evalTree(document.body, newPass()); singles();
                obs.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
                obs.takeRecords();
                W.__spbPerf1Client.tags = true;
            } catch (e) {}
        }
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
        else start();
        W.__spbPerf1Client.retag = function () { try { evalTree(document.body, newPass()); singles(); obs.takeRecords(); return true; } catch (e) { return false; } };
    })();

    // ------------------------------------------------------------------ C. getZoneSourceLayersUnionMask memo
    /* getZoneSourceLayersUnionMask(zone, w, h, excludeId) (paint-booth-3-canvas.js) copies the first layer's 4 MB visible-contribution mask and then max-merges every
     * further layer with a 4-million-iteration JS loop - on EVERY call. With a car loaded the helper's environment scan and the render payload call it several
     * times a second for zones restricted to 3-4 layers: measured on the owner's car, 80 four-layer calls = 1,152 ms and 20 three-layer calls = 210 ms of main
     * thread per 15 s idle window (14.4 ms and 10.5 ms per call); the 220 single-layer calls cost 1.4 ms each and are left alone.
     * The union is a pure function of the per-layer mask ARRAYS (getLayerVisibleContributionMask already caches them per composite revision, so while nothing
     * changed it hands back the very same Uint8Array objects). This wrapper therefore keys the merged result on the identities of those arrays, in order:
     * same arrays -> same union, built once, and every call returns its OWN fresh copy (callers may mutate it, exactly as before). Any layer edit, visibility
     * toggle, resize or composite change makes getLayerVisibleContributionMask return new arrays -> a miss -> the original maths run again.
     * Safety: the wrapper re-implements the original body, so it installs ONLY if the original function's source (comments/whitespace stripped) still has the
     * fingerprint it was written against; if another lane edits that function the memo silently stays off (W.__spbPerf1Client.unionMemo.active === false).
     * Kill switch: SPB_PERF1_OFF is checked on every call. */
    (function unionMemo() {
        var FP = 'dbbfe9c7', FP_LEN = 773, MAXE = 4;
        var cache = [];                     // newest last: { rev, masks: [Uint8Array refs], union: Uint8Array }
        var st = W.__spbPerf1Client.unionMemo = { active: false, calls: 0, hits: 0, misses: 0, why: 'not installed' };

        function fingerprint(fn) {
            var n = Function.prototype.toString.call(fn).replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, '');
            var h = 0x811c9dc5;
            for (var i = 0; i < n.length; i++) { h ^= n.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
            return { h: h.toString(16), n: n.length };
        }
        function rev() { try { return typeof _layerCompositeRevision !== 'undefined' ? _layerCompositeRevision : -1; } catch (e) { return -1; } }

        function install() {
            var orig = W.getZoneSourceLayersUnionMask;
            if (typeof orig !== 'function') { st.why = 'no function'; return false; }
            if (orig.__spbPerf1) return true;
            if (typeof W.getLayerVisibleContributionMask !== 'function' || typeof _psdLayers === 'undefined') { st.why = 'deps missing'; return false; }
            var f = fingerprint(orig);
            if (f.h !== FP || f.n !== FP_LEN) { st.why = 'source changed (' + f.h + '/' + f.n + ')'; return false; }

            function memoUnion(zone, w, h, excludeLayerId) {
                if (W.SPB_PERF1_OFF === true) return orig.apply(this, arguments);
                var ids = (typeof W.zoneSourceLayerIds === 'function') ? W.zoneSourceLayerIds(zone) : (zone && zone.sourceLayer ? [zone.sourceLayer] : []);
                if (ids.length < 2) return orig.apply(this, arguments);          // single-layer: one 4 MB copy, nothing to save
                st.calls++;
                var masks = [], found = 0, hiddenCount = 0, i, j;
                for (i = 0; i < ids.length; i++) {          // the original loop, verbatim semantics
                    var id = ids[i];
                    var l = _psdLayers.find(function (x) { return x && x.id === id; });
                    if (!l || !l.img) continue;
                    if (l.visible === false) { hiddenCount++; continue; }
                    var m = W.getLayerVisibleContributionMask(l, w, h, excludeLayerId);
                    if (!m) continue;
                    found++;
                    masks.push(m);
                }
                var union = null;
                if (masks.length === 1) union = new Uint8Array(masks[0]);
                else if (masks.length > 1) {
                    var r = rev(), hit = null;
                    for (j = cache.length - 1; j >= 0; j--) {
                        var e = cache[j];
                        if (e.rev !== r) { cache.splice(j, 1); continue; }          // composite changed: its masks can never be returned again
                        if (!hit && e.masks.length === masks.length) {
                            var same = true;
                            for (i = 0; i < masks.length; i++) if (e.masks[i] !== masks[i]) { same = false; break; }
                            if (same) hit = e;
                        }
                    }
                    if (hit) { st.hits++; union = new Uint8Array(hit.union); }
                    else {
                        st.misses++;
                        var u = new Uint8Array(masks[0]);
                        for (i = 1; i < masks.length; i++) { var mm = masks[i]; for (j = 0; j < u.length; j++) { if (mm[j] > u[j]) u[j] = mm[j]; } }
                        cache.push({ rev: r, masks: masks, union: u });
                        if (cache.length > MAXE) cache.shift();
                        union = new Uint8Array(u);
                    }
                }
                return { union: union, found: found, hiddenCount: hiddenCount, requested: ids.length, firstLayer: ids.length ? _psdLayers.find(function (x) { return x && x.id === ids[0]; }) : null, ids: ids };
            }
            memoUnion.__spbPerf1 = true; memoUnion.__orig = orig;
            W.getZoneSourceLayersUnionMask = memoUnion;
            st.active = true; st.why = 'ok';
            return true;
        }
        function go() { try { install(); } catch (e) { st.why = 'error ' + String(e).slice(0, 80); } }
        go();
        if (!st.active) { document.addEventListener('DOMContentLoaded', go, { once: true }); W.addEventListener('load', go, { once: true }); }
        st.reset = function () { cache.length = 0; };
    })();
})();
