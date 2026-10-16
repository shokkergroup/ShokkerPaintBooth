/* SPB-TOOLROW 2026-10-09 (owner): "when I click BRUSH there's a bunch of tools that load across the very
   bottom ... you have to kind of scroll to see all of them. Can we try to use the area ABOVE SOURCE/LIVE
   PREVIEW for SOME of the tools and the bottom for the others? ... In all of the tool usages?"

   What this does: it RE-PARENTS the primary controls of the active tool (size / strength / opacity /
   hardness / flow / tolerance / selection mode / feather / text+shape basics ...) out of the bottom
   #toolOptionsBar into a new band #spbToolRowTop that sits between the spec-channel thumbnail strip and the
   SOURCE / LIVE PREVIEW row. The existing DOM nodes are MOVED (never rebuilt), so every id, inline handler,
   keyboard shortcut and setCanvasMode() show/hide keeps working untouched. A comment placeholder is left
   where each node lived so the kill switch can put everything back.

   Containers that mix primary and secondary controls (text / shape options) are split with a "mirror"
   span in the band whose visibility follows the source container.

   KILL SWITCH: set window.SPB_TOOLROW_OFF = true BEFORE this script loads (or call SPBToolRow.off() at
   runtime) and the single bottom bar is exactly as it was. SPBToolRow.on() re-applies. */
(function (root) {
    'use strict';
    const doc = root.document;
    if (!doc) return;

    // Primary controls, in the order they appear in the band. Each id is a node that is moved as-is.
    // A nested array is a GROUP: its nodes go into one no-wrap unit so a slider never gets split from its label
    // when the band wraps on a narrow window. The unit hides itself when none of its members is showing.
    const PRIMARY = [
        'selectionMode', 'eraserMode', 'gradientType', 'gradientReverseLabel', 'gradientFgTransLabel',
        ['brushSizeLabel', 'brushSize', 'brushSizeVal'],
        ['smudgeStrengthLabel', 'smudgeStrength', 'smudgeStrengthVal'],
        'dodgeBurnOptions', 'blurSharpenOptions',
        ['brushOpacityLabel', 'brushOpacity', 'brushOpacityVal'],
        ['brushHardnessLabel', 'brushHardness', 'brushHardnessVal'],
        ['brushFlowLabel', 'brushFlow', 'brushFlowVal'],
        'strokeHlLabel', // [STROKE-HL 2026-10-12] "Highlight [colour] x" - live footprint highlight on SOURCE (js/canvas/pc-strokehl.js); static markup in paint-booth-v2.html
        'spbZoneClipLabel', // PORT-W5B 2026-10-09: "Clip to <zone>" checkbox (js/canvas/pc-zoneclip.js); hidden unless the selected zone has an area
        ['wandToleranceLabel', 'wandTolerance', 'wandTolVal'],
        'wandContiguousLabel',
        'spbQuickLabel', 'selectionFeatherLabel',
        'cloneToolOptions',
        ['spatialSizeLabel', 'spatialBrushSize', 'spatialSizeVal']
    ];
    // Mixed containers: [source container id, mirror id, child ids moved up (labels w/o ids use the input's parent label)]
    const SPLITS = [
        ['textToolOptions', 'spbTextPrimary', ['textFont', 'textSize', 'textFillColor', '<textBold', '<textItalic']],
        ['shapeToolOptions', 'spbShapePrimary', ['shapeType', 'shapeFillColor', 'shapeFilledLabel', 'shapeStrokeColor', 'shapeStrokeWidth']]
    ];

    const state = { on: false, band: null, moved: [], mirrors: [], groups: [], mo: null, ro: null, mos: [], keep: null };

    function placeholderFor(node) {
        const ph = doc.createComment('spb-toolrow:' + (node.id || 'node'));
        node.parentNode.insertBefore(ph, node);
        return ph;
    }
    function move(node, dest) {
        if (!node || !node.parentNode) return;
        state.moved.push({ node: node, ph: placeholderFor(node) });
        dest.appendChild(node);
    }
    function sizeSquares() {
        try { if (typeof root._sizePreviewSquares === 'function') root._sizePreviewSquares(); } catch (_) {}
    }
    function refresh() {
        const band = state.band;
        if (!band) return;
        const loaded = doc.getElementById('paintPreviewLoaded');
        let loadedOk = true;
        try { loadedOk = !loaded || root.getComputedStyle(loaded).display !== 'none'; } catch (_) {}
        let any = false;
        state.groups.forEach(function (g) {
            let vis = false;
            for (const c of g.children) {
                let d = 'none';
                try { d = root.getComputedStyle(c).display; } catch (_) {}
                if (d !== 'none') { vis = true; break; }
            }
            const want = vis ? 'inline-flex' : 'none';
            if (g.style.display !== want) g.style.display = want;
        });
        if (loadedOk) {
            for (const c of band.children) {
                let d = 'none';
                try { d = root.getComputedStyle(c).display; } catch (_) {}
                if (d !== 'none') { any = true; break; }
            }
        }
        band.classList.toggle('spb-tr-empty', !any);
    }
    function syncMirror(src, mirror) {
        let d = 'none';
        try { d = root.getComputedStyle(src).display; } catch (_) {}
        const want = d === 'none' ? 'none' : 'flex';
        if (mirror.style.display !== want) mirror.style.display = want;
    }
    function ensureBand() {
        const row = doc.getElementById('previewSquaresRow');
        if (!row || !row.parentNode) return false;
        if (state.band && state.band.parentNode === row.parentNode && state.band.nextSibling === row) return true;
        if (!state.band) return false;
        row.parentNode.insertBefore(state.band, row);
        return true;
    }
    function apply() {
        if (state.on) return true;
        const bar = doc.getElementById('toolSpecificOptions');
        const row = doc.getElementById('previewSquaresRow');
        if (!bar || !row || !row.parentNode) return false;
        const band = doc.createElement('div');
        band.id = 'spbToolRowTop';
        band.className = 'spb-tr-empty';
        band.setAttribute('role', 'toolbar');
        band.setAttribute('aria-label', 'Active tool primary options');
        row.parentNode.insertBefore(band, row);
        state.band = band;
        PRIMARY.forEach(function (entry) {
            if (typeof entry === 'string') { move(doc.getElementById(entry), band); return; }
            const g = doc.createElement('span');
            g.className = 'spb-tr-group';
            g.style.display = 'none';
            band.appendChild(g);
            state.groups.push(g);
            entry.forEach(function (id) { move(doc.getElementById(id), g); });
        });
        SPLITS.forEach(function (s) {
            const src = doc.getElementById(s[0]);
            if (!src) return;
            const mirror = doc.createElement('span');
            mirror.id = s[1];
            mirror.setAttribute('style', 'display:none; gap:4px; align-items:center;');
            band.appendChild(mirror);
            s[2].forEach(function (cid) {
                let n;
                if (cid.charAt(0) === '<') { const i = doc.getElementById(cid.slice(1)); n = i && i.parentElement !== src ? i.parentElement : i; }
                else n = doc.getElementById(cid);
                move(n, mirror);
            });
            const mo = new MutationObserver(function () { syncMirror(src, mirror); refresh(); });
            mo.observe(src, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
            state.mos.push(mo);
            state.mirrors.push({ src: src, mirror: mirror });
            syncMirror(src, mirror);
        });
        doc.body.classList.add('spb-toolrow-on');
        state.mo = new MutationObserver(function (recs) {
            for (const r of recs) if (r.target !== band) { refresh(); return; }
        });
        state.mo.observe(band, { attributes: true, subtree: true, attributeFilter: ['style', 'class', 'hidden'] });
        const loaded = doc.getElementById('paintPreviewLoaded');
        if (loaded) {
            state.mos.push((function () {
                const m = new MutationObserver(refresh);
                m.observe(loaded, { attributes: true, attributeFilter: ['style', 'class'] });
                return m;
            })());
        }
        if (typeof root.ResizeObserver === 'function') {
            let last = -1, t = null;
            state.ro = new root.ResizeObserver(function () {
                const h = band.offsetHeight;
                if (h === last) return;
                last = h;
                clearTimeout(t);
                t = setTimeout(sizeSquares, 60);
            });
            state.ro.observe(band);
        }
        // the squares module can rebuild its container; keep the band glued above the squares row
        state.keep = root.setInterval(function () { if (state.on) { ensureBand(); refresh(); } }, 1500);
        state.on = true;
        refresh();
        sizeSquares();
        return true;
    }
    function off() {
        if (!state.on) return;
        state.on = false;
        root.clearInterval(state.keep);
        state.mos.forEach(function (m) { m.disconnect(); });
        state.mos = [];
        if (state.mo) state.mo.disconnect();
        if (state.ro) state.ro.disconnect();
        for (let i = state.moved.length - 1; i >= 0; i--) {
            const m = state.moved[i];
            if (m.ph.parentNode) { m.ph.parentNode.insertBefore(m.node, m.ph); m.ph.parentNode.removeChild(m.ph); }
        }
        state.moved = [];
        state.mirrors.forEach(function (m) { if (m.mirror.parentNode) m.mirror.parentNode.removeChild(m.mirror); });
        state.mirrors = [];
        state.groups = [];
        if (state.band && state.band.parentNode) state.band.parentNode.removeChild(state.band);
        state.band = null;
        doc.body.classList.remove('spb-toolrow-on');
        sizeSquares();
    }
    function on() {
        root.SPB_TOOLROW_OFF = false;
        let tries = 0;
        (function go() {
            if (apply()) return;
            if (++tries < 100) root.setTimeout(go, 300);
        })();
    }

    root.SPBToolRow = { on: on, off: function () { root.SPB_TOOLROW_OFF = true; off(); }, state: state };
    if (root.SPB_TOOLROW_OFF) return;
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', on);
    else on();
})(typeof window === 'object' ? window : globalThis);
