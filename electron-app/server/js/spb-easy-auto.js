/* ============================================================================
   SPB EASY AUTO — "your car, built for you"  (SPB-EASY-AUTO 2026-09-19)
   ----------------------------------------------------------------------------
   Owner (2026-09-19): Easy Mode is still "too similar to the regular mode"; buyers
   need an SPB-for-dummies that keeps ALL the finishes and the same control —
   especially BASE STRENGTH (blend the new finish with the paint), BASE/SPEC SCALE
   and the H/S/B adjustments.

   Two inversions over the existing Easy workflow, same project underneath:
     1. ORDER — the app builds the whole zone set FROM the paint the moment it
        loads (dominant colours + dark + white + everything-else, the 8-zone
        PRESETS shape) and renders a curated recipe before the buyer decides
        anything. First screen = a finished car.
     2. SURFACE — the buyer taps the car, not a panel. The tap lights the part it
        belongs to and opens a popover with the SAME catalog (Top-50 shelf, the
        main app's categories with larger thumbnails, search) plus an ADJUST tab
        holding the three keepers as plain-English sliders that write the REAL
        zone fields Pro sends: baseStrength, baseScale/specScale, baseHueOffset /
        baseSaturationAdjust / baseBrightnessAdjust.

   Round 2 (owner, same day): parts rail on the LEFT like Pro, LAYERS on the right
   for layered PSDs (a layer becomes a part: zone.color='everything' +
   zone.sourceLayers=[id] → Pro's own source_layer_mask), SOURCE + LIVE always
   visible, compact spec chips that pop into LIVE on hover and pin on click,
   COLOR REACH (tolerance) in plain English with the catch shown live on the car,
   an apply scope (this part / every colour / whole car — shine only), and a
   hover hint on every control.

   HARD LAW (owner 2026-09-19, SPB-EASY-SEPARATE): Easy is its OWN project.
   This layer only ever runs inside the isolated full-screen Easy
   (js/spb-easy-mode.js + spb-easy-mode-isolation.js) and never writes Pro's
   zones. The 2026-09-02 shared-state shell host was removed here for good.

   Colour clustering mirrors the engine's own selector maths
   (shokker_engine_v2._build_plain_rgb_color_mask_fast: BT.601-weighted distance,
   mask = 1 - d/tol, first claim wins for the remainder). Probe + contact
   sheets: _easy_auto_work/autozone_probe.py (12/12 example TGAs, by eye).
   ========================================================================== */
(function () {
    'use strict';

    var E = null;                                   // spb-easy-mode.js internals (lazy)
    var LS_LEFT = 'spb_easy_auto_left_v1';          // paintKey the buyer explicitly left AUTO for
    var LS_BUILT = 'spb_easy_auto_built_v3';        // paintKey AUTO already built once (so an UNDO is never fought)
    var LS_PLAN = 'spb_easy_auto_plan_v3';          // { paintKey: {parts:[lite], layers:[lite]} } — Easy's own plan survives reloads
    var LS_HINTS = 'spb_easy_auto_hints_v1';        // '0' = hide the helper hints
    var N = 512;                                    // [SPB-EASY-PBN] analysis + highlight grid: every 4th pixel of the 2048 paint, true colours
    var LAYER_IDX = 100;                            // layer parts live at idx >= 100 (colour parts are 0..n-1)
    var PICK_IDX = 50;                              // [SPB-EASY-R6] colours the buyer picked off the car: idx 50..99
    var _pickParts = [], _picking = false;
    var RECIPE_COLORS = ['metallic', 'candy', 'pearl', 'chrome', 'satin', 'metallic'];
    var RECIPE_KIND = { white: 'gloss', dark: 'gloss', remaining: 'gloss' };
    var LABELS = { dark: 'Dark areas', white: 'White & logos', remaining: 'Everything else' };
    var PALETTE = [[255, 122, 24], [80, 200, 255], [255, 210, 60], [120, 255, 120], [255, 120, 255],
                   [255, 160, 60], [160, 120, 255], [60, 255, 220], [200, 200, 200], [255, 255, 255]];
    var KICK_MS = 320;
    var PLAN_FIELDS = ['base', 'finish', 'pattern', 'baseStrength', 'baseSpecStrength', 'baseScale', 'specScale', 'baseHueOffset', 'baseSaturationAdjust', 'baseBrightnessAdjust', 'baseColorMode', 'baseColor', 'baseColorSource', 'baseColorStrength', '_easyAutoOwnColor', '_easyAutoColorChosen', '_easyAutoMerged', '_easyAuto'];
    var CHANNEL_NAMES = { all: 'COMBINED SPEC', r: 'RED · METAL', g: 'GREEN · ROUGH', b: 'BLUE · COAT' };

    var _builtFor = null, _analysis = null, _layerParts = [], _layerMaskCache = {}, _hosts = [];
    var _pop = null, _popPart = -1, _popTab = 'finish', _popAnchor = null, _scope = 'part';
    // [SPB-EASY-PRO 2026-09-22] Pro's default: a picked finish brings its OWN colour. 'mine' keeps the car's colour.
    var _colorPick = 'finish', _colorPref = 'finish', _colorPrefSet = false;              // 'finish' | 'mine' | 'pick' — what colour the next finish lands in
    var _cat = { mode: 'shelf', section: null };
    var _kickTimer = null, _flashTimer = null, _pollTimer = null, _search = '', _hoverPart = -1;
    var _layersPanel = null, _specView = null, _specPinned = null, _specHover = null, _specCache = { src: null, canvases: null }, _liveSubtitleOrig = null, _stripWired = false;
    var LS_LIVE = 'spb_easy_auto_live_v2';           // [SPB-EASY-PRO] 'light' = the lit material view; default = AS PAINTED (Pro's own live preview)
    var _liveTog = null, _matCache = { key: null, canvas: null }, _imgObs = null, _hoverTimer = null, _matTimer = null;
    var _imgStamp = { paint: 0, spec: 0 }, _buildAt = 0, _freshTimers = [];
    // After a build (or a paint switch) the app's own paint-load preview races ours and can leave the
    // PREVIOUS car on LIVE (seen in QA: PSD → flat TGA). Re-kick until a spec newer than the build lands.
    var _matchCache = { key: null, ok: true }, _hoverMask = null, _lightDefaulted = false;
    function bcOf(x) { try { return (x.bcRef ? x.bcRef() : x.bc) || {}; } catch (e) { return x.bc || {}; } }   // Easy reassigns `bc = {…}`; never write into a stale copy
    function previewMatchesSource() {
        // Is Pro's live paint render a render of THIS paint? (QA: after a paint switch the app's own
        // load-preview can answer with the PREVIOUS car.) Coarse 16×16 mean-colour compare vs SOURCE.
        var pi = $('livePreviewImg'), src = $('spbEasySourceCanvas');
        if (!pi || !pi.complete || !pi.naturalWidth || !pi.getAttribute('src') || !src || src.width < 512) return true;
        var key = (pi.src || '').slice(-96) + '|' + (pi.src || '').length + '|' + _imgStamp.paint + '|' + src.width + '|' + _builtFor;   // never the bare length (RENDER_paint.png?v= is constant-length)
        if (_matchCache.key === key) return _matchCache.ok;
        try {
            var n = 16, a = document.createElement('canvas'), b = document.createElement('canvas'); a.width = a.height = b.width = b.height = n;
            var ac = a.getContext('2d'), bc = b.getContext('2d'); ac.drawImage(pi, 0, 0, n, n); bc.drawImage(src, 0, 0, n, n);
            var da = ac.getImageData(0, 0, n, n).data, db = bc.getImageData(0, 0, n, n).data, sum = 0;
            for (var i = 0; i < da.length; i += 4) sum += Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2]);
            var mean = sum / (n * n * 3);
            _matchCache = { key: key, ok: mean < 48 };                // same car with finishes ≈ 5–25; a different livery ≈ 60+
            return _matchCache.ok;
        } catch (e) { return true; }
    }
    function previewIsStale() {
        // Time-boxed on purpose (review finding): a legitimately colour-changing recipe (solid recolour,
        // hue −180, an own-colour finish on every part) differs from SOURCE forever and must NOT read as stale.
        var now = performance.now();
        if (_buildAt && _imgStamp.spec < _buildAt && (now - _buildAt) < 12000) return true;
        if ((now - _pkChangedAt) < 20000 && _imgStamp.paint < _pkChangedAt && !previewMatchesSource()) return true;   // once a paint render landed after the switch, trust it
        return false;
    }
    function ensureFreshPreview(x) {
        _freshTimers.forEach(clearTimeout); _freshTimers = [];
        [1800, 4200, 7500, 11000, 15000].forEach(function (ms) {
            _freshTimers.push(setTimeout(function () {
                if (!X() || !previewIsStale()) return;
                try { x.refreshZonesUI(); x.kickPreview(); } catch (e) {}
            }, ms));
        });
    }

    // [SPB-EASY-TELL2 2026-09-30] a spoken command may touch many parts: inside batch() every undoPush after the first is dropped,
    // so ONE UNDO takes back the whole command. _applyColor lets TELL say which colour a finish arrives in.
    var _batch = null, _applyColor = null, _lastPart = -1;
    function wrapUndo(x) {
        if (!x || x._tellWrapped) return;
        var up = x.undoPush;
        x.undoPush = function (label) { if (_batch) { if (_batch.pushed) return; _batch.pushed = true; if (_batch.label) label = _batch.label; } return up(label); };
        var kp = x.kickPreview, ru = x.refreshZonesUI;                // inside a batch, repaint ONCE at the end (a 9-part command is 1 render, not 9)
        x.kickPreview = function () { if (_batch) { _batch.kick = true; return; } return kp.apply(this, arguments); };
        x.refreshZonesUI = function () { if (_batch) { _batch.ui = true; return; } return ru.apply(this, arguments); };
        x._tellWrapped = true;
    }
    function I() {
        if (E) return E;
        try { if (window.spbEasy && typeof window.spbEasy._internals === 'function') E = window.spbEasy._internals(); } catch (e) {}
        wrapUndo(E);
        return E;
    }
    function X() { var x = I(); return (x && x.isActive()) ? x : null; }
    function $(id) { return document.getElementById(id); }
    function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
    // "Left AUTO" is a THIS-SESSION choice only (owner 2026-09-19: a permanent flag kept resuming the
    // old by-colour rail after every restart — "still showing the old layout"). A fresh launch or reload
    // always lands in Built-for-you; the other flows stay one click away.
    function leftGet() { try { return sessionStorage.getItem(LS_LEFT); } catch (e) { return null; } }
    function leftSet(v) { try { if (v) sessionStorage.setItem(LS_LEFT, v); else sessionStorage.removeItem(LS_LEFT); } catch (e) {} }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]; }); }
    function hexOf(rgb) { return '#' + rgb.map(function (v) { return ('0' + Math.max(0, Math.min(255, Math.round(v))).toString(16)).slice(-2); }).join(''); }
    function toast(msg, kind) { try { if (typeof window.showToast === 'function') window.showToast(msg, kind === 'error'); } catch (e) {} }
    function hintsOn() { return lsGet(LS_HINTS) !== '0'; }
    function zonesRef() { var x = I(); return x ? x.zones() : []; }
    function inAutoView() { var x = X(); return !!(x && x.state.view === 'auto'); }
    function psdLayers() {
        // Paintable layers only: the template's guide layers (Wire, Mask, anything grouped under
        // "Turn Off Before Exporting TGA") are not something a buyer should finish.
        try {
            return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers.filter(function (l) {
                if (!l || !l.id || !l.name) return false;
                if (/^flattened$/i.test(l.name) || /^(wire|mask|wireframe|template)$/i.test(String(l.name).trim())) return false;
                if (/turn\s*off|before\s*export|do\s*not\s*paint|guide/i.test(String(l.groupName || '') + ' ' + String(l.path || '').replace(l.name, ''))) return false;
                return true;
            }) : [];
        } catch (e) { return []; }
    }

    // [SPB-EASY-R5 2026-09-22] Template guides (Wire / Mask / Car Mandatory, the "Turn Off Before Exporting TGA"
    // group) left ON are baked into the paint and the iRacing TGA: the truck's Wire layer drew a repeating UV grid
    // over every panel, and ARCA V6's Mask became a fake "Taupe" colour part. Pro leaves this to the painter;
    // Easy says so and fixes it in one click (Pro's own visibility path: undo + recomposite + preview).
    function guideLayersOn() {
        try {
            return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers.filter(function (l) {
                if (!l || !l.id || l.visible === false) return false;
                return /^(wire|wireframe|mask|car[\s_]*mandatory)$/i.test(String(l.name || '').trim()) || /turn\s*off|before\s*export/i.test(String(l.groupName || ''));
            }) : [];
        } catch (e) { return []; }
    }
    function guidesNoticeHtml() {
        var g = guideLayersOn(); if (!g.length) return '';
        return '<div class="spb-easy-auto-guides" role="status" title="' + esc(g.map(function (l) { return l.name; }).join(', ')) + ' — your template says “Turn Off Before Exporting TGA”. Left on, they are painted into your car (grid lines, grey masks).">' +
            '<b>⚠ Template guides are on</b><span>They would be painted into your car.</span>' +
            '<button type="button" id="spbEasyAutoGuidesOff" title="Hide these template guide layers. You can show them again any time from the Layers panel in Pro.">Turn off</button></div>';
    }
    function remirrorSource() {
        // Easy mirrors #paintCanvas into its SOURCE / pick / live canvases only when a paint loads; a recomposite inside
        // Easy (template guides off) left SOURCE showing the old picture while the parts were built from the new one.
        var pc = $('paintCanvas'), xx = I();
        if (!pc || pc.width < 512 || !xx || !xx.els) return;
        [xx.els.pickCanvas, xx.els.sourceCanvas, xx.els.liveCanvas].forEach(function (cv) { if (!cv) return; try { cv.width = pc.width; cv.height = pc.height; cv.getContext('2d').drawImage(pc, 0, 0); } catch (e) {} });
    }
    function guidesOff() {
        var g = guideLayersOn(); if (!g.length) return;
        var m = new Map(); g.forEach(function (l) { m.set(l.id, false); });
        var ok = false;
        try { if (typeof _applyLayerVisibilityMap === 'function') ok = _applyLayerVisibilityMap(m, 'Easy: hide template guides'); } catch (e) {}
        if (!ok) { g.forEach(function (l) { l.visible = false; }); try { if (typeof _finishLayerVisibilityChange === 'function') _finishLayerVisibilityChange(); } catch (e) {} }
        toast('Template guides hidden — rebuilding your parts from the clean paint');
        setTimeout(function () {
            try { window._spbLayerRev = (window._spbLayerRev | 0) + 1; window.__spbPreviewBodyMemo = null; } catch (e) {}
            _layerMaskCache = {};
            remirrorSource();                                       // SOURCE showed the stale composite (grey Mask) after the recomposite
            if (buildZones('template guides off')) { renderRail(); renderLayersPanel(); flashAll(1400); }
        }, 900);
    }

    // ------------------------------------------------------------ paint access
    function srcCanvas() {
        var c = $('paintCanvas');                                  // the only universal source (TGA, PSD, blank)
        if (c && c.width >= 512) return c;
        var s = $('spbEasySourceCanvas');
        if (s && s.width >= 512) return s;
        return null;
    }
    function paintKey() {
        var c = srcCanvas();
        if (!c) return null;
        var name = '';
        try { name = String((typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || ($('paintFile') && $('paintFile').value) || ''); } catch (e) {}
        return name + '|' + c.width + 'x' + c.height;
    }
    function downsample(src, n) {
        var mid = document.createElement('canvas'); mid.width = mid.height = 512;
        var mc = mid.getContext('2d'); mc.imageSmoothingEnabled = true; mc.imageSmoothingQuality = 'high';
        mc.drawImage(src, 0, 0, 512, 512);
        var out = document.createElement('canvas'); out.width = out.height = n;
        var oc = out.getContext('2d'); oc.imageSmoothingEnabled = true; oc.imageSmoothingQuality = 'high';
        oc.drawImage(mid, 0, 0, n, n);
        return oc.getImageData(0, 0, n, n).data;
    }

    // ------------------------------------------------------- colour analysis
    // [SPB-EASY-PBN 2026-09-22] (+ SPB-EASY-R7/R8/R9 review fixes, SPB-EASY-MERGE 2026-09-22) Paint-by-numbers logic rebuilt (owner: "the LOGIC it's picking colors by").
    // The old pass blurred the paint to 128x128 and k-means'd it: anti-aliased edges and wireframe lines
    // became fake colours ("Cyan 2", "Lime 2"), the dominant pink could go missing, gradients split at random,
    // and two builds of one paint disagreed (owner's two saves 2026-09-22 14:51 / 14:52 found different colours).
    // Now (prototype _easy_auto_work/replay/proto_palette.py, judged by eye on 10 real paints; "everything
    // else" 0-3% on flat liveries, was 4-9%):
    //   1. sample every 4th pixel of the 2048 paint, never blended — true colours only;
    //   2. only FLAT samples vote, so outlines, anti-aliasing and 1-px template lines never become a colour;
    //   3. colours = density peaks with suppression — deterministic: same paint, same parts, every time;
    //   4. chromatic colours joined by a real gradient become ONE fade part (black/white/grey never join);
    //   5. each part is a few colour stops (its colour + its own shading/edge shades), each held back from
    //      the neighbouring colours. Engine maths (BT.601 weighted RGB, first zone wins, owned when d < tol),
    //      so the highlight on SOURCE is exactly what the render paints.
    function GRAD_REL() { var v = window.__spbPbnGradRel; return (typeof v === "number" && v >= 0) ? v : 0.03; }   // tunable for QA
    var FLAT2 = 100, SUPP = 36, MIN_DENS = 0.0012, GRAD_MIN = 0.00035, MAX_PARTS = 8, MIN_SHARE = 0.005;
    function sampleTrue(src) {
        var c = document.createElement('canvas'); c.width = c.height = N;
        var x = c.getContext('2d', { willReadFrequently: true }); x.imageSmoothingEnabled = false;
        x.drawImage(src, 0, 0, N, N);
        return x.getImageData(0, 0, N, N).data;
    }
    function wd(r, g, b, t) { var dr = r - t[0], dg = g - t[1], db = b - t[2]; return Math.sqrt(dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11); }   // engine BT.601 distance
    function wdc(a, t) { return wd(a[0], a[1], a[2], t); }
    function lerp3(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
    // [SPB-EASY-R7] dull / dark colours never join a fade: a shadow ramp (colour -> dark slate) glued the ARCA grey-brown base onto "Yellow -> Red"
    function achro(c) { var mx = Math.max(c[0], c[1], c[2]), mn = Math.min(c[0], c[1], c[2]); return mx < 70 || (mx - mn) < 0.35 * Math.max(mx, 1) || (mn > 200 && mx - mn < 40); }
    function hitSel(data, i, sel) {
        var o = i * 4, r = data[o], g = data[o + 1], b = data[o + 2];
        for (var s = 0; s < sel.length; s++) { var t = sel[s]; if (wd(r, g, b, t.rgb) < 0.99 * t.tol) return true; }
        return false;
    }
    function binDensity(counts, bins) {                             // 3x3x3 box sum at the given bins (sparse)
        var out = new Float32Array(bins.length);
        for (var k = 0; k < bins.length; k++) {
            var bk = bins[k], R = bk >> 10, G = (bk >> 5) & 31, B = bk & 31, s = 0;
            for (var a = -1; a <= 1; a++) { var rr = R + a; if (rr < 0 || rr > 31) continue;
                for (var c = -1; c <= 1; c++) { var gg = G + c; if (gg < 0 || gg > 31) continue;
                    for (var e = -1; e <= 1; e++) { var b3 = B + e; if (b3 < 0 || b3 > 31) continue; s += counts[(rr << 10) | (gg << 5) | b3]; } } }
            out[k] = s;
        }
        return out;
    }
    function analyze(src) {
        var data = sampleTrue(src), NN = N * N, i, x, y, k, t0 = Date.now();
        var flat = new Uint8Array(NN), q = new Uint16Array(NN);
        for (y = 0; y < N; y++) for (x = 0; x < N; x++) {
            i = y * N + x; var o = i * 4, r = data[o], g = data[o + 1], b = data[o + 2], m = 0;
            var nb = [x < N - 1 ? i + 1 : i, y < N - 1 ? i + N : i, x > 0 ? i - 1 : i, y > 0 ? i - N : i];
            for (k = 0; k < 4; k++) { var p2 = nb[k] * 4, dr = r - data[p2], dg = g - data[p2 + 1], db = b - data[p2 + 2], d2 = dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11; if (d2 > m) m = d2; }
            flat[i] = m < FLAT2 ? 1 : 0;
            q[i] = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
        }
        var cnt = new Float32Array(32768), sr = new Float32Array(32768), sg = new Float32Array(32768), sb = new Float32Array(32768);
        for (i = 0; i < NN; i++) if (flat[i]) { k = q[i]; cnt[k]++; sr[k] += data[i * 4]; sg[k] += data[i * 4 + 1]; sb[k] += data[i * 4 + 2]; }
        var bins = []; for (k = 0; k < 32768; k++) if (cnt[k] > 0) bins.push(k);
        var bd = binDensity(cnt, bins), dens = new Float32Array(32768);
        bins.forEach(function (bk, j) { dens[bk] = bd[j]; });
        function densAt(c) { var R = Math.max(0, Math.min(31, Math.floor(c[0] / 8))), G = Math.max(0, Math.min(31, Math.floor(c[1] / 8))), B = Math.max(0, Math.min(31, Math.floor(c[2] / 8))), s = 0;
            for (var a = -1; a <= 1; a++) { var rr = R + a; if (rr < 0 || rr > 31) continue; for (var e = -1; e <= 1; e++) { var gg = G + e; if (gg < 0 || gg > 31) continue; for (var f = -1; f <= 1; f++) { var b3 = B + f; if (b3 < 0 || b3 > 31) continue; s += cnt[(rr << 10) | (gg << 5) | b3]; } } }
            return s; }
        var cand = bins.filter(function (bk) { return dens[bk] >= MIN_DENS * NN; });
        cand.sort(function (a, b) { return (dens[b] - dens[a]) || (a - b); });
        var P = [];
        for (k = 0; k < cand.length && P.length < 16; k++) {
            var bk = cand[k], c0 = [sr[bk] / cnt[bk], sg[bk] / cnt[bk], sb[bk] / cnt[bk]];
            if (P.some(function (p) { return wdc(c0, p) < SUPP; })) continue;
            P.push(c0);
        }
        if (!P.length) { var mr = 0, mg = 0, mb = 0; for (i = 0; i < NN; i++) { mr += data[i * 4]; mg += data[i * 4 + 1]; mb += data[i * 4 + 2]; } P.push([mr / NN, mg / NN, mb / NN]); }
        // one Lloyd refinement on flat samples within 20 of their nearest peak
        var acc = P.map(function () { return [0, 0, 0, 0]; });
        for (i = 0; i < NN; i++) {
            if (!flat[i]) continue;
            var o2 = i * 4, best = Infinity, bi = 0;
            for (k = 0; k < P.length; k++) { var dd = wd(data[o2], data[o2 + 1], data[o2 + 2], P[k]); if (dd < best) { best = dd; bi = k; } }
            if (best < 20) { acc[bi][0] += data[o2]; acc[bi][1] += data[o2 + 1]; acc[bi][2] += data[o2 + 2]; acc[bi][3]++; }
        }
        P = P.map(function (p, j) { return acc[j][3] > 8 ? [acc[j][0] / acc[j][3], acc[j][1] / acc[j][3], acc[j][2] / acc[j][3]] : p; });
        // fades: chromatic colours joined by a populated gradient
        var K = P.length, adj = P.map(function () { return []; }), j2;
        for (i = 0; i < K; i++) for (j2 = i + 1; j2 < K; j2++) {
            var dij = wdc(P[i], P[j2]); if (dij > 110 || achro(P[i]) || achro(P[j2])) continue;   // real fades hop through intermediate colours
            var ok = true;
            // a real fade carries mass all along, relative to the colours it joins: a thin shadow ramp must not glue a big flat
            // background onto a gradient (ARCA V6: the grey-brown base joined "Yellow → Red" through the wave shadows)
            var need = Math.max(GRAD_MIN * NN, GRAD_REL() * Math.min(densAt(P[i]), densAt(P[j2])));
            for (k = 0; k < 7 && ok; k++) if (densAt(lerp3(P[i], P[j2], 0.125 + k * 0.125)) < need) ok = false;
            if (ok) { adj[i].push(j2); adj[j2].push(i); }
        }
        var comp = P.map(function () { return -1; }), comps = [];
        for (i = 0; i < K; i++) {
            if (comp[i] >= 0) continue;
            var st = [i], mem = []; comp[i] = comps.length;
            while (st.length) { var u = st.pop(); mem.push(u); adj[u].forEach(function (v) { if (comp[v] < 0) { comp[v] = comp[i]; st.push(v); } }); }
            comps.push(mem.sort(function (a, b) { return a - b; }));
        }
        function foreign(c, mem) { var m2 = 999; for (var j = 0; j < K; j++) if (mem.indexOf(j) < 0) { var dj = wdc(c, P[j]); if (dj < m2) m2 = dj; } return m2; }
        function mst(mem) {                                         // spanning tree over the fade: no redundant chords (each stop = a full-canvas pass in the engine)
            if (mem.length < 2) return [];
            var inT = [mem[0]], edges = [];
            while (inT.length < mem.length) {
                var best = null;
                inT.forEach(function (a) { adj[a].forEach(function (b) { if (inT.indexOf(b) >= 0 || mem.indexOf(b) < 0) return; var d = wdc(P[a], P[b]); if (!best || d < best[0]) best = [d, a, b]; }); });
                if (!best) break;
                edges.push([best[1], best[2]]); inT.push(best[2]);
            }
            return edges;
        }
        var parts = comps.map(function (mem) {
            var sel = mem.map(function (pi) { return { rgb: P[pi].slice(), tol: Math.max(12, Math.min(64, 0.55 * foreign(P[pi], mem))) }; });
            mst(mem).forEach(function (e) {
                var a = e[0], b = e[1], d = wdc(P[a], P[b]), n = Math.ceil(d / 32);
                for (var s = 1; s < n; s++) { var c = lerp3(P[a], P[b], s / n), want = Math.max(20, 0.72 * d / n); sel.push({ rgb: c, tol: Math.max(12, Math.min(0.55 * foreign(c, mem), want)) }); }
            });
            return { mem: mem, sel: sel };
        });
        // assign every sample to its nearest colour; extra stops cover each part's own shading / edges
        var palPart = []; parts.forEach(function (p, pi) { p.mem.forEach(function (m) { palPart[m] = pi; }); });
        var assigned = new Int16Array(NN);
        for (i = 0; i < NN; i++) {
            var o3 = i * 4, bb = Infinity, bj = 0;
            for (k = 0; k < K; k++) { var d3 = wd(data[o3], data[o3 + 1], data[o3 + 2], P[k]); if (d3 < bb) { bb = d3; bj = k; } }
            assigned[i] = bb < 100 ? palPart[bj] : -1;
        }
        parts.forEach(function (p, pi) {
            var resid = [];
            for (i = 0; i < NN; i++) if (assigned[i] === pi && !hitSel(data, i, p.sel)) resid.push(i);
            for (var it = 0; it < 2; it++) {
                if (resid.length < 0.003 * NN) break;
                var rc = new Float32Array(32768), rb = [];
                resid.forEach(function (ri) { if (!rc[q[ri]]) rb.push(q[ri]); rc[q[ri]]++; });
                var rd = binDensity(rc, rb), top = 0;
                for (k = 1; k < rb.length; k++) if (rd[k] > rd[top] || (rd[k] === rd[top] && rb[k] < rb[top])) top = k;
                var tb = rb[top], nbs = resid.filter(function (ri) { return q[ri] === tb; });
                if (nbs.length < 4) break;
                var cc = [0, 0, 0]; nbs.forEach(function (ri) { cc[0] += data[ri * 4]; cc[1] += data[ri * 4 + 1]; cc[2] += data[ri * 4 + 2]; });
                cc = [cc[0] / nbs.length, cc[1] / nbs.length, cc[2] / nbs.length];
                var tt = Math.min(0.5 * foreign(cc, p.mem), 30); if (tt < 8) break;
                var stop = { rgb: cc, tol: Math.max(10, tt) }; p.sel.push(stop);
                resid = resid.filter(function (ri) { return wd(data[ri * 4], data[ri * 4 + 1], data[ri * 4 + 2], stop.rgb) >= 0.99 * stop.tol; });
            }
        });
        function shares(list) {
            var cov = list.map(function () { return 0; });
            for (i = 0; i < NN; i++) for (var z = 0; z < list.length; z++) if (hitSel(data, i, list[z].sel)) { cov[z]++; break; }
            return cov.map(function (c) { return c / NN; });
        }
        var sh = shares(parts); parts.forEach(function (p, pi) { p.share = sh[pi]; });
        parts = parts.map(function (p, pi) { p._o = pi; return p; }).sort(function (a, b) { return (b.share - a.share) || (a._o - b._o); });
        var keep = parts.filter(function (p) { return p.share >= MIN_SHARE; }).slice(0, MAX_PARTS);
        if (!keep.length) keep = parts.slice(0, 1);
        // stop budget (24 per car): every stop is a full-canvas pass in the engine — 56 stops made a finish change take ~2 s.
        // Shading stops go first, from the smallest parts.
        for (var guard = 0; guard < 200 && keep.reduce(function (n, p) { return n + p.sel.length; }, 0) > 24; guard++) {
            var cands = keep.filter(function (p) { return p.sel.length > p.mem.length; });
            if (!cands.length) break;
            cands[cands.length - 1].sel.pop();
        }
        var out = keep.map(function (p) {
            var main = P[p.mem[0]], rgb = main.map(Math.round), ends = null;
            if (p.mem.length > 1) {
                var far = -1; p.mem.forEach(function (a) { p.mem.forEach(function (b) { var d = wdc(P[a], P[b]); if (d > far) { far = d; ends = [P[a].map(Math.round), P[b].map(Math.round)]; } }); });
            }
            var sel = p.sel.map(function (s) { var r3 = s.rgb.map(Math.round), tl = Math.round(s.tol); return { rgb: r3, tol: tl, tol0: tl }; });
            var w = colorWord(rgb), tone = (w === 'Black') ? 'dark' : ((w === 'White' || (w === 'Silver' && Math.min(rgb[0], rgb[1], rgb[2]) > 200)) ? 'white' : null);
            return { kind: 'color', tone: tone, rgb: rgb, hex: hexOf(rgb), sel: sel, sel0: sel.map(function (q) { return { rgb: q.rgb.slice(), tol: q.tol, tol0: q.tol0 }; }), tol: sel[0].tol, tol0: sel[0].tol, fade: p.mem.length > 1, ends: ends,
                     stops: p.mem.map(function (m) { return hexOf(P[m]); }) };
        });
        out.push({ kind: 'remaining', rgb: null, tol: null, sel: null });
        var A = { n: N, data: data, parts: out, owner: new Uint8Array(NN), coverage: out.map(function () { return 0; }), ms: Date.now() - t0 };
        computeOwner(A);
        return A;
    }
    // Owner map = the engine's order: layer / autopart parts FIRST (a layer the buyer picked wins its own
    // pixels — owner's 2026-09-22 save left jagged blue islands in a hue-shifted gradient because the colour
    // parts claimed them first), then colour parts, then "Everything else".
    function computeOwner(A) {
        A = A || _analysis; if (!A) return;
        var NN = A.n * A.n, own = A.owner, data = A.data, parts = A.parts, cov = parts.map(function () { return 0; });
        var lps = [];
        zonesRef().forEach(function (z) { if (!z || (z._easyAuto !== 'layer' && z._easyAuto !== 'autopart') || !(z.base || z.finish)) return; var lp = null; _layerParts.forEach(function (p) { if (p.idx === z._easyAutoIdx) lp = p; }); if (lp && lp.mask) lps.push(lp); });   // no finish = not rendered = no priority
        var picks = [];
        zonesRef().forEach(function (z) { if (!z || z._easyAuto !== 'pick' || !(z.base || z.finish)) return; _pickParts.forEach(function (p) { if (p.idx === z._easyAutoIdx) picks.push(p); }); });
        var pcov = picks.map(function () { return 0; });
        var remAt = -1; parts.forEach(function (p, z) { if (p.kind === 'remaining') remAt = z; });
        for (var i = 0; i < NN; i++) {
            own[i] = 255;
            var hit = false;
            for (var l = 0; l < lps.length; l++) if (lps[l].mask[i]) { own[i] = lps[l].idx; hit = true; break; }
            if (hit) continue;
            for (var pq = 0; pq < picks.length; pq++) if (hitSel(data, i, picks[pq].sel)) { own[i] = picks[pq].idx; pcov[pq]++; hit = true; break; }
            if (hit) continue;
            for (var z = 0; z < parts.length; z++) {
                var p = parts[z];
                if (p.mergedInto != null) continue;
                if (p.kind === 'color' ? hitSel(data, i, p.sel) : p.kind === 'remaining') { own[i] = z; cov[z]++; break; }
            }
        }
        A.coverage = cov.map(function (c) { return c / NN; });
        parts.forEach(function (p, z) { p.share = A.coverage[z]; });
        picks.forEach(function (p, k) { p.share = pcov[k] / NN; });
        if (remAt >= 0) parts[remAt].share = A.coverage[remAt];
    }
    function recomputeOwner() { computeOwner(_analysis); }
    // ---------------------------------------------------------------- merge (SPB-EASY-MERGE 2026-09-22)
    function partByFp(fp, notIdx) {
        if (!_analysis || !/^#[0-9a-fA-F]{6}$/.test(fp || '')) return -1;
        var c = [parseInt(fp.slice(1, 3), 16), parseInt(fp.slice(3, 5), 16), parseInt(fp.slice(5, 7), 16)], best = -1, bd = 12;
        _analysis.parts.forEach(function (p, i) { if (i === notIdx || p.kind !== 'color' || !p.rgb) return; var d = wdc(c, p.rgb); if (d < bd) { bd = d; best = i; } });
        return best;
    }
    function applyMergesFromZones(zf) {
        zf = zf || zoneFor;
        // Reset every analysis part to its own stops, then fold in what the zones say was merged.
        if (!_analysis) return;
        _analysis.parts.forEach(function (p) { if (p.kind !== 'color' || !p.sel0) return; delete p.mergedInto; p.mergedFps = []; });
        var fresh = {};
        _analysis.parts.forEach(function (p, i) {
            if (p.kind !== 'color' || !p.sel0) return;
            var z = zf(i), list = (z && Array.isArray(z._easyAutoMerged)) ? z._easyAutoMerged : [];
            var sel = p.sel0.map(function (q) { return { rgb: q.rgb.slice(), tol: q.tol, tol0: q.tol0 }; });
            list.forEach(function (fp) {
                var j = partByFp(fp, i); if (j < 0) return;
                var q = _analysis.parts[j]; if (!q || q.mergedInto != null) return;
                q.mergedInto = i; p.mergedFps.push(q.hex);
                q.sel0.forEach(function (st) { sel.push({ rgb: st.rgb.slice(), tol: st.tol, tol0: st.tol0 }); });
            });
            var zr = zoneReach(z), sc = (zr && p.tol0) ? zr / p.tol0 : 1;
            sel.forEach(function (st) { st.tol = reachTol(st, sc); });
            p.sel = sel; fresh[i] = true;
        });
    }
    function mergeParts(ia, ib) {
        var x = X(), pa = partById(ia), pb = partById(ib), za = zoneFor(ia), zb = zoneFor(ib);
        if (!x || !pa || !pb || !za || !zb || ia === ib || pa.kind !== 'color' || pb.kind !== 'color' || pa.pick || pb.pick) return false;
        x.undoPush('Easy: merged ' + partLabel(pb) + ' into ' + partLabel(pa));
        var list = (Array.isArray(za._easyAutoMerged) ? za._easyAutoMerged.slice() : []).concat([pb.hex], Array.isArray(zb._easyAutoMerged) ? zb._easyAutoMerged : []);
        za._easyAutoMerged = list;
        var Z = x.zones(), at = Z.indexOf(zb); if (at >= 0) Z.splice(at, 1);
        applyMergesFromZones();
        selToZone(za, pa);
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Z, 'easy-auto merge'); } catch (e) {}
        recomputeOwner(); x.refreshZonesUI(); x.kickPreview(); savePlan(); renderRail(); renderPop(); redrawAll();
        toast(partLabel(pb) + ' is now part of ' + partLabel(pa) + ' — UNDO splits them again');
        return true;
    }
    function mergeHtml(p, idx) {
        if (!_analysis || p.kind !== 'color' || p.pick || idx >= PICK_IDX) return '';
        var opts = _analysis.parts.map(function (q, j) { return (j === idx || q.kind !== 'color' || q.mergedInto != null || !zoneFor(j)) ? '' : '<option value="' + j + '">' + esc(partLabel(q)) + ' (' + Math.round((q.share || 0) * 100) + '%)</option>'; }).join('');
        if (!opts) return '';
        return '<label class="spb-easy-auto-merge" title="Fold another colour part into this one: one finish for both (e.g. Black + Charcoal). UNDO splits them again.">' +
            '<span>Merge with</span><select id="spbEasyAutoMerge" aria-label="Merge another colour into this part"><option value="">another colour…</option>' + opts + '</select></label>';
    }         // after a COLOR REACH change or a layer part
    function reachTol(st, s) { return Math.max(6, Math.min(120, Math.round((st.tol0 || st.tol) * s))); }   // one formula for preview + applied
    function setReach(p, v) {                                       // COLOR REACH: scale every stop of the part together
        if (!p || !p.sel) return;
        var s = v / Math.max(1, p.tol0 || p.tol || v);
        p.sel.forEach(function (st) { st.tol = reachTol(st, s); });
        p.tol = v;
    }
    function selToZone(z, p) {                                      // Pro's own zone colour shapes: picker (one) / multi (several)
        if (!z || !p || !p.sel) return;
        if (p.sel.length === 1) {
            var s0 = p.sel[0];
            z.colorMode = 'picker'; z.pickerColor = hexOf(s0.rgb); z.pickerTolerance = s0.tol;
            z.color = { color_rgb: s0.rgb.slice(), tolerance: s0.tol }; z.colors = [];
        } else {
            var cs = p.sel.map(function (s) { return { color_rgb: s.rgb.slice(), tolerance: s.tol, hex: hexOf(s.rgb) }; });
            z.colorMode = 'multi'; z.colors = cs; z.color = cs; z.pickerColor = p.hex; z.pickerTolerance = p.tol;
        }
    }
    function zoneMainRgb(z) {                                        // [SPB-EASY-R8] a zone's OWN main colour (not its part index)
        if (!z) return null;
        if (z.colorMode === 'multi' && Array.isArray(z.colors) && z.colors.length && z.colors[0].color_rgb) return z.colors[0].color_rgb.slice();
        if (/^#[0-9a-fA-F]{6}$/.test(z.pickerColor || '')) return [parseInt(z.pickerColor.slice(1, 3), 16), parseInt(z.pickerColor.slice(3, 5), 16), parseInt(z.pickerColor.slice(5, 7), 16)];
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color) && z.color.color_rgb) return z.color.color_rgb.slice();
        return null;
    }
    function zonesMatchAnalysis() {
        // true when every automatic colour zone sits on the analysis part with the same main colour
        if (!_analysis) return false;
        var ok = true;
        zonesRef().forEach(function (z) {
            if (!ok || !z || z._easyAuto !== 'color') return;
            var p = _analysis.parts[z._easyAutoIdx], m = zoneMainRgb(z);
            if (!p || p.kind !== 'color' || !m) { ok = false; return; }
            var own = (p.sel0 && p.sel0[0]) ? p.sel0[0].rgb : p.rgb;
            if (wdc(m, own) > 12) ok = false;
        });
        return ok;
    }
    function zoneReach(z) {                                         // the main-stop tolerance a zone carries now
        if (!z) return null;
        if (z.colorMode === 'multi' && Array.isArray(z.colors) && z.colors.length) return Number(z.colors[0].tolerance) || null;
        if (z.pickerTolerance) return Number(z.pickerTolerance);
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) return Number(z.color.tolerance) || null;
        return null;
    }

    // --------------------------------------------------------------- layers
    function layerMask(layer) {
        // [SPB-EASY-R5 2026-09-22] layer.img is CROPPED to the layer's bbox; drawing it over the whole canvas stretched
        // every layer (the truck's "Numbers" claimed a warped 17.5%). Use Pro's own visible-ownership mask — the exact
        // mask the render restricts to — and fall back to the placed alpha.
        if (!layer || !layer.id) return null;
        var c = _layerMaskCache[layer.id]; if (c) return c;
        try {
            var pc = $('paintCanvas'), W = (pc && pc.width) || 2048, H = (pc && pc.height) || 2048, m = new Uint8Array(N * N), cnt = 0, i, x, y, full = null;
            try { if (typeof window.getLayerVisibleContributionMask === 'function') full = window.getLayerVisibleContributionMask(layer, W, H); } catch (e0) { full = null; }
            if (full && full.length === W * H) {
                for (y = 0; y < N; y++) { var fy = Math.min(H - 1, Math.floor((y + 0.5) * H / N)) * W; for (x = 0; x < N; x++) { if (full[fy + Math.min(W - 1, Math.floor((x + 0.5) * W / N))] > 8) { m[y * N + x] = 1; cnt++; } } }
            } else {
                var img = layer.img; if (!img) return null;
                var o = (typeof getLayerCanvasOrigin === 'function') ? getLayerCanvasOrigin(layer) : { x: (layer.bbox && layer.bbox[0]) || 0, y: (layer.bbox && layer.bbox[1]) || 0 };
                var cv = document.createElement('canvas'); cv.width = cv.height = N;
                var ctx = cv.getContext('2d', { willReadFrequently: true }); ctx.imageSmoothingEnabled = false;
                ctx.drawImage(img, o.x * N / W, o.y * N / H, img.width * N / W, img.height * N / H);
                var d = ctx.getImageData(0, 0, N, N).data;
                for (i = 0; i < N * N; i++) if (d[i * 4 + 3] > 24) { m[i] = 1; cnt++; }
            }
            c = { mask: m, share: cnt / (N * N) };
            _layerMaskCache[layer.id] = c;
            return c;
        } catch (e) { return null; }
    }
    var _layerThumbCache = {};
    function layerThumb(layer) {
        if (!layer || !layer.id) return '';
        if (_layerThumbCache[layer.id]) return _layerThumbCache[layer.id];
        try {
            var img = layer.img; if (!img || !img.width || !img.height) return '';
            var cv = document.createElement('canvas'); cv.width = cv.height = 40;
            var ctx = cv.getContext('2d'); ctx.fillStyle = '#1b1e24'; ctx.fillRect(0, 0, 40, 40); ctx.imageSmoothingEnabled = true;
            var k = Math.min(36 / img.width, 36 / img.height), w = img.width * k, h = img.height * k;   // the layer's own art, fitted (was stretched)
            ctx.drawImage(img, (40 - w) / 2, (40 - h) / 2, w, h);
            var u = cv.toDataURL('image/png'); _layerThumbCache[layer.id] = u; return u;
        } catch (e) { return ''; }
    }
    function partById(idx) {
        if (idx == null || idx < 0) return null;
        if (idx >= PICK_IDX && idx < LAYER_IDX) { for (var k = 0; k < _pickParts.length; k++) if (_pickParts[k].idx === idx) return _pickParts[k]; return null; }
        if (idx < LAYER_IDX) return _analysis ? _analysis.parts[idx] : null;
        for (var i = 0; i < _layerParts.length; i++) if (_layerParts[i].idx === idx) return _layerParts[i];
        return null;
    }
    function rebuildLayerParts() {
        _layerParts = [];
        var layers = psdLayers();
        zonesRef().forEach(function (z) {
            if (!z || (z._easyAuto !== 'layer' && z._easyAuto !== 'autopart')) return;
            if (z._easyAuto === 'autopart') {                       // flat-TGA numbers / sponsor text (see runAutoDetect)
                var am = _layerMaskCache[z._easyAutoLayer] || null;
                _layerParts.push({ kind: 'autopart', idx: z._easyAutoIdx, layerId: z._easyAutoLayer, name: z.name, hex: null, share: am ? am.share : (z._easyAutoShare || 0), mask: am ? am.mask : null });
                return;
            }
            var lay = null;
            for (var i = 0; i < layers.length; i++) if (layers[i].id === z._easyAutoLayer) { lay = layers[i]; break; }
            var lm = lay ? layerMask(lay) : null;
            _layerParts.push({ kind: 'layer', idx: z._easyAutoIdx, layerId: z._easyAutoLayer, name: z.name, hex: null, share: lm ? lm.share : 0, mask: lm ? lm.mask : null, missing: !lay, multi: lm ? layerIsMulti(lm) : false });
        });
        rebuildPickParts();
        if (_analysis) computeOwner(_analysis);                    // [SPB-EASY-PBN] layer parts own their pixels first
    }
    function layerIsMulti(lm) {
        // [SPB-EASY-R7] a layer carrying several colours (the owner's BASE01 gradient) keeps its colours by default — a finish's own colour would wipe the design
        if (lm._multi != null) return lm._multi;
        if (!_analysis || !lm.mask) return false;
        var d = _analysis.data, m = lm.mask, n = 0, sr = 0, sg = 0, sb = 0, i;
        for (i = 0; i < m.length; i += 3) if (m[i]) { sr += d[i * 4]; sg += d[i * 4 + 1]; sb += d[i * 4 + 2]; n++; }
        if (n < 50) { lm._multi = false; return false; }
        var mc = [sr / n, sg / n, sb / n], acc = 0;
        for (i = 0; i < m.length; i += 3) if (m[i]) acc += wd(d[i * 4], d[i * 4 + 1], d[i * 4 + 2], mc);
        lm._multi = (acc / n) > 38;
        return lm._multi;
    }
    function rebuildPickParts() {
        _pickParts = [];
        zonesRef().forEach(function (z) {
            if (!z || z._easyAuto !== 'pick' || !z._easyAutoPick) return;
            var pk0 = z._easyAutoPick, cur = zoneReach(z) || pk0.tol0;
            var p = { kind: 'color', pick: true, idx: z._easyAutoIdx, rgb: pk0.rgb.slice(), hex: hexOf(pk0.rgb), label: colorWord(pk0.rgb) + ' · your pick',
                      name: z.name, sel: [{ rgb: pk0.rgb.slice(), tol: cur, tol0: pk0.tol0 }], tol: cur, tol0: pk0.tol0, share: 0 };
            _pickParts.push(p);
        });
    }

    // ------------------------------------------- flat TGA: numbers & sponsor text
    // A flat paint has no layers to point at. The server's auto-separate (OCR + strokes) can propose a
    // NUMBERS mask and a SPONSOR TEXT mask; it takes ~40 s and numbers are hit-and-miss (agent report
    // 2026-09-19), so it is opt-in and every proposal is shown with its overlay for a YES / NO.
    var _autoDet = { pk: null, running: false, result: null, error: null };
    var _autopartMaskUrl = {};                                   // id -> 768px mask PNG data URL (persisted in the plan)
    var _pendingAutoparts = null;
    function maskDataUrlToGrid(dataUrl, cb) {
        var img = new Image();
        img.onload = function () {
            try {
                var cv = document.createElement('canvas'); cv.width = cv.height = N;
                var ctx = cv.getContext('2d'); ctx.imageSmoothingEnabled = true; ctx.drawImage(img, 0, 0, N, N);
                var d = ctx.getImageData(0, 0, N, N).data, m = new Uint8Array(N * N), cnt = 0;
                for (var i = 0; i < N * N; i++) { if (d[i * 4] > 96 || d[i * 4 + 3] > 96 && d[i * 4] > 40) { m[i] = 1; cnt++; } }
                cb({ mask: m, share: cnt / (N * N) });
            } catch (e) { cb(null); }
        };
        img.onerror = function () { cb(null); };
        img.src = dataUrl;
    }
    function runAutoDetect() {
        var x = X(); if (!x || !window.spbEasyAutoParts) return;
        var pk = paintKey(), path = '';
        try { path = (typeof window.getCurrentSourcePaintFile === 'function' && window.getCurrentSourcePaintFile()) || ($('paintFile') || {}).value || ''; } catch (e) {}
        if (!path) { toast('Save or open a paint file first — the finder needs the file on disk'); return; }
        _autoDet = { pk: pk, running: true, result: null, error: null, started: performance.now() };
        renderLayersPanel();
        window.spbEasyAutoParts.detect(path, { previewSize: 768 }).then(function (res) {
            if (_autoDet.pk !== pk) return;
            _autoDet.running = false; _autoDet.result = res || null;
            if (!res || !res.detected) _autoDet.error = (res && res.message) || 'Nothing found';
            renderLayersPanel();
        }).catch(function (e) { if (_autoDet.pk !== pk) return; _autoDet.running = false; _autoDet.error = String(e && e.message || e); renderLayersPanel(); });
    }
    function useAutoPart(kind) {
        var x = X(), res = _autoDet.result; if (!x || !res || !res[kind] || !res[kind].maskDataUrl) return;
        var pc = $('paintCanvas'); if (!pc || pc.width < 512) return;
        var pk = paintKey(), id = 'autopart:' + kind, name = kind === 'numbers' ? 'Numbers' : 'Sponsor text';
        var Z = x.zones();
        for (var i = 0; i < Z.length; i++) if (Z[i] && Z[i]._easyAuto === 'autopart' && Z[i]._easyAutoLayer === id) { openPop(Z[i]._easyAutoIdx, null); return; }
        toast('Cutting out ' + name.toLowerCase() + '…');
        _autopartMaskUrl[id] = res[kind].maskDataUrl;
        window.spbEasyAutoParts.maskToBytes(res[kind].maskDataUrl, pc.width, pc.height).then(function (bytes) {
            if (!bytes || paintKey() !== pk) return;
            maskDataUrlToGrid(res[kind].maskDataUrl, function (grid) {
                if (grid) _layerMaskCache[id] = grid;
                var idx = nextLayerIdx();
                var z = { id: newId(idx), name: name, color: 'everything', regionMask: bytes, useRegion: true,
                          base: null, finish: null, pattern: 'none', intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], patternStack: [],
                          _easyAuto: 'autopart', _easyAutoIdx: idx, _easyAutoLayer: id, _easyAutoShare: res[kind].coverage || 0, _easyAutoPaint: pk };
                x.undoPush('Easy: ' + name + ' part');
                var Zc = x.zones(), at = layerInsertAt(Zc);
                Zc.splice(at, 0, z);
                try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Zc, 'easy-auto autopart'); } catch (e) {}
                rebuildLayerParts(); x.refreshZonesUI(); renderRail(); renderLayersPanel();
                openPop(idx, null);
            });
        }).catch(function () { toast('Could not cut that part out — try again'); });
    }
    function restorePendingAutoparts(pk) {
        if (!_pendingAutoparts || !_pendingAutoparts.length || !window.spbEasyAutoParts) return;
        var pc = $('paintCanvas'); if (!pc || pc.width < 512) return;
        var list = _pendingAutoparts; _pendingAutoparts = null;
        list.forEach(function (sv) {
            if (!sv || !sv.maskDataUrl || !sv._easyAutoLayer) return;
            var id = sv._easyAutoLayer; _autopartMaskUrl[id] = sv.maskDataUrl;
            window.spbEasyAutoParts.maskToBytes(sv.maskDataUrl, pc.width, pc.height).then(function (bytes) {
                var x = X(); if (!x || !bytes || paintKey() !== pk) return;
                if (x.zones().some(function (z) { return z && z._easyAuto === 'autopart' && z._easyAutoLayer === id; })) return;
                maskDataUrlToGrid(sv.maskDataUrl, function (grid) {
                    if (grid) _layerMaskCache[id] = grid;
                    var idx = sv._easyAutoIdx || nextLayerIdx();
                    var z = { id: newId(idx), name: sv.name || 'Part', color: 'everything', regionMask: bytes, useRegion: true,
                              base: null, finish: null, pattern: 'none', intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], patternStack: [],
                              _easyAuto: 'autopart', _easyAutoIdx: idx, _easyAutoLayer: id, _easyAutoShare: sv._easyAutoShare || 0, _easyAutoPaint: pk };
                    PLAN_FIELDS.forEach(function (k) { if (k !== '_easyAuto' && sv[k] !== undefined) z[k] = sv[k]; });
                    var Zc = x.zones(), at = layerInsertAt(Zc);
                    Zc.splice(at, 0, z);
                    try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Zc, 'easy-auto restore autopart'); } catch (e) {}
                    rebuildLayerParts(); x.refreshZonesUI(); x.kickPreview(); renderRail(); renderLayersPanel(); savePlan();
                });
            }).catch(function () {});
        });
    }
    function autoPartsPanelHtml() {
        var res = _autoDet.result, pk = paintKey();
        var head = '<div class="spb-easy-auto-layers-head"><b>NUMBERS & SPONSORS</b><small>A flat paint has no layers, but Shokker can look for your numbers and sponsor text so they can take their own finish.</small></div>';
        if (_autoDet.running && _autoDet.pk === pk) return head + '<div class="spb-easy-auto-detect running">🔎 Looking for numbers and sponsor text… about 40 seconds. You can keep working.</div>';
        if (!res || _autoDet.pk !== pk) return head + '<button type="button" class="spb-easy-auto-act spb-easy-auto-detect-btn" id="spbEasyAutoDetect" title="Runs the server\'s text and number finder on this paint (about 40 seconds). Nothing changes until you say yes to a proposal.">🔎 Find my numbers & sponsors <small>about 40 s</small></button>' + (_autoDet.error && _autoDet.pk === pk ? '<div class="spb-easy-auto-detect err">' + esc(_autoDet.error) + '</div>' : '');
        var html = head;
        if (res.overlayDataUrl) html += '<img class="spb-easy-auto-overlay" alt="What the finder saw: red = numbers, blue = sponsor text" title="What the finder saw: red = numbers, blue = sponsor text" src="' + esc(res.overlayDataUrl) + '">';
        var any = false;
        [['numbers', 'Numbers'], ['sponsors', 'Sponsor text']].forEach(function (k) {
            var r = res[k[0]]; if (!r || !r.maskDataUrl || (r.coverage || 0) < 0.002) return;
            any = true;
            var have = zonesRef().some(function (z) { return z && z._easyAuto === 'autopart' && z._easyAutoLayer === 'autopart:' + k[0]; });
            html += '<div class="spb-easy-auto-propose"><span class="spb-easy-auto-row-text"><b>' + k[1] + '</b><small>~' + Math.round((r.coverage || 0) * 1000) / 10 + '% of your car · ' + (k[0] === 'numbers' ? 'red' : 'blue') + ' in the picture</small></span>' +
                (have ? '<span class="spb-easy-auto-layer-badge">✓ in use</span>' : '<button type="button" class="spb-easy-auto-use" data-use="' + k[0] + '" title="Make this a part you can give its own finish">USE IT</button>') + '</div>';
        });
        if (!any) html += '<div class="spb-easy-auto-detect err">No numbers or sponsor text found on this paint.</div>';
        html += '<button type="button" class="spb-easy-auto-act" id="spbEasyAutoDetectAgain" title="Run the finder again">↻ Look again</button>';
        return html;
    }
    function pickInsertAt(Z) { var at = 0; while (at < Z.length && Z[at] && (Z[at]._easyAuto === 'layer' || Z[at]._easyAuto === 'autopart' || Z[at]._easyAuto === 'pick')) at++; return at; }
    function layerInsertAt(Z) { var at = 0; while (at < Z.length && Z[at] && (Z[at]._easyAuto === 'layer' || Z[at]._easyAuto === 'autopart')) at++; return at; }   // [SPB-EASY-PBN] after the other layer parts, before every colour part
    function nextLayerIdx() { var m = LAYER_IDX - 1; _layerParts.forEach(function (p) { if (p.idx > m) m = p.idx; }); zonesRef().forEach(function (z) { if (z && z._easyAuto === 'layer' && z._easyAutoIdx > m) m = z._easyAutoIdx; }); return m + 1; }
    function ensureLayerPart(layer) {
        var x = X(); if (!x || !layer) return -1;
        var Z = x.zones();
        for (var i = 0; i < Z.length; i++) if (Z[i] && Z[i]._easyAuto === 'layer' && Z[i]._easyAutoLayer === layer.id) return Z[i]._easyAutoIdx;
        var idx = nextLayerIdx();
        var z = { id: newId(idx), name: String(layer.name || 'Layer').slice(0, 40), color: 'everything', sourceLayers: [layer.id], sourceLayer: layer.id,
                  base: null, finish: null, pattern: 'none', intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], regionMask: null, patternStack: [],
                  _easyAuto: 'layer', _easyAutoIdx: idx, _easyAutoLayer: layer.id, _easyAutoPaint: paintKey() };
        x.undoPush('Easy: layer part ' + z.name);
        var at = layerInsertAt(Z);
        Z.splice(at, 0, z);                                        // [SPB-EASY-PBN] top of the order: the layer wins its own pixels
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Z, 'easy-auto layer part'); } catch (e) {}
        rebuildLayerParts();
        x.refreshZonesUI();
        savePlan();
        return idx;
    }

    var _pendingLayers = null;                                   // saved layer parts waiting for _psdLayers to rasterize
    function layerZoneFromLite(s, pk) {
        var z = { id: newId(s._easyAutoIdx || 0), name: s.name || 'Layer', color: 'everything', sourceLayers: s.sourceLayers || [s._easyAutoLayer], sourceLayer: s._easyAutoLayer,
                  base: null, finish: null, pattern: 'none', intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], regionMask: null, patternStack: [],
                  _easyAuto: 'layer', _easyAutoIdx: s._easyAutoIdx || LAYER_IDX, _easyAutoLayer: s._easyAutoLayer, _easyAutoPaint: pk };
        PLAN_FIELDS.forEach(function (k) { if (k !== '_easyAuto' && s[k] !== undefined) z[k] = s[k]; });
        return z;
    }
    function restorePendingLayers(pk, returnOnly) {
        if (!_pendingLayers || !_pendingLayers.length) return null;
        var live = psdLayers(); if (!live.length) return null;     // not rasterized yet — keep waiting
        var made = [];
        _pendingLayers.forEach(function (s) { if (live.some(function (l) { return l.id === s._easyAutoLayer; })) made.push(layerZoneFromLite(s, pk)); });
        _pendingLayers = null;
        if (returnOnly) return made;
        var x = X(); if (!x || !made.length) return made;
        var Z = x.zones(), at = layerInsertAt(Z);
        made.forEach(function (z, i) { Z.splice(at + i, 0, z); });
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Z, 'easy-auto restore layer parts'); } catch (e) {}
        rebuildLayerParts(); x.refreshZonesUI(); x.kickPreview(); renderRail(); savePlan();
        try { console.info('[EASY AUTO] restored ' + made.length + ' layer part(s) once the PSD layers arrived'); } catch (e) {}
        return made;
    }

    // ------------------------------------------------------- colour words
    // Beginners think "the teal" and "the orange", not "Color 3". Zone names stay "Color N"
    // (Easy's by-colour view and isEasyColorZone key off that), the LABEL is the colour word.
    function colorWord(rgb) {
        // [SPB-EASY-PBN] HSV saturation (the HSL one blew up near white: off-white read "Red" / "Gold").
        var r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0;
        if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
        var sv = mx > 0 ? d / mx : 0;
        if (mx < 0.16) return 'Black';
        if (sv < 0.07) return mx < 0.35 ? 'Charcoal' : (mx < 0.7 ? 'Gray' : (mx < 0.9 ? 'Silver' : 'White'));
        if (mx < 0.32 && sv < 0.4) return 'Charcoal';
        if (mn > 0.72 && sv < 0.3) return (h < 20 || h >= 300) ? 'Pink' : (h < 70 ? 'Cream' : (h < 170 ? 'Mint' : (h < 250 ? 'Ice Blue' : 'Lavender')));
        if (sv < 0.2) return (h >= 180 && h < 260) ? 'Slate' : (h < 70 ? 'Taupe' : 'Gray');
        var dark = mx < 0.36;
        if (h >= 180 && h < 250 && !dark) {                         // the blue family, by how people say it
            if (sv < 0.36 && mx < 0.66) return 'Slate';
            if (h < 196) return 'Cyan';
            if (h < 232 && mx > 0.78 && mn > 0.2) return 'Sky Blue';
            return 'Blue';
        }
        if (h >= 12 && h < 50 && !dark && mx < 0.72) return 'Bronze';
        var T = [[12, 'Red', 'Maroon'], [38, 'Orange', 'Brown'], [50, 'Gold', 'Brown'], [68, 'Yellow', 'Olive'], [95, (mx < 0.6 ? 'Green' : 'Lime'), 'Olive'],
            [150, 'Green', 'Dark Green'], [175, 'Teal', 'Dark Teal'], [200, 'Cyan', 'Dark Teal'], [250, (mn > 0.42 ? 'Sky Blue' : 'Blue'), 'Navy'],
            [282, 'Purple', 'Dark Purple'], [322, (mn > 0.45 ? 'Pink' : 'Magenta'), 'Plum'], [345, (mn > 0.45 ? 'Pink' : (mx < 0.85 ? 'Crimson' : 'Hot Pink')), 'Maroon']];
        for (var i = 0; i < T.length; i++) if (h < T[i][0]) return dark ? T[i][2] : T[i][1];
        return dark ? 'Maroon' : 'Red';
    }
    function labelParts(parts) {
        var used = {};
        parts.forEach(function (p) {
            if (p.kind !== 'color' || !p.rgb) { p.label = p.name; return; }
            var w = colorWord(p.rgb);
            if (p.fade && p.ends) { var w1 = colorWord(p.ends[0]), w2 = colorWord(p.ends[1]); w = (w1 === w2) ? w1 + ' fade' : w1 + ' → ' + w2; }
            var n = (used[w] || 0) + 1; used[w] = n;
            p.label = n > 1 ? w + ' ' + n : w;
        });
    }
    function partLabel(p) { return (p && (p.label || p.name)) || ''; }

    // ------------------------------------------------------------- zone build
    function pickBase(id) {
        try { if (typeof BASES_BY_ID !== 'undefined') { if (BASES_BY_ID[id]) return id; var ks = Object.keys(BASES_BY_ID); if (ks.length) return ks[0]; } } catch (e) {}
        return id;
    }
    function newId(i) { try { if (typeof _newZoneId === 'function') return _newZoneId(); } catch (e) {} return 'easya_' + Date.now().toString(36) + '_' + i; }
    function readPlans() { try { var o = JSON.parse(lsGet(LS_PLAN) || '{}'); return (o && typeof o === 'object') ? o : {}; } catch (e) { return {}; } }
    function lite(z, extra) { var o = {}; PLAN_FIELDS.concat(extra || []).forEach(function (k) { if (z[k] !== undefined && z[k] !== null) o[k] = z[k]; }); return o; }
    function savePlan() {
        var x = X(); if (!x) return;
        var pk = paintKey(); if (!pk || pk !== _builtFor) return;
        var Z = x.zones().filter(function (z) { return z && (!z._easyAuto || !z._easyAutoPaint || z._easyAutoPaint === pk); });   // [SPB-EASY-R7] never save another car's zones
        var parts = Z.filter(function (z) { return z && (z._easyAuto === 'color' || z._easyAuto === 'remaining'); }).map(function (z) {
            var o = lite(z), ap = partById(z._easyAutoIdx), zm = zoneMainRgb(z);
            var same = !!(ap && zm && ap.rgb && wdc(zm, (ap.sel0 && ap.sel0[0]) ? ap.sel0[0].rgb : ap.rgb) <= 12);
            if (zm) o._fp = hexOf(zm); else if (ap && ap.hex) o._fp = ap.hex;   // [SPB-EASY-R8] the zone's own colour: right even if indices drifted
            var zr = zoneReach(z);
            if (same && ap.tol0 && zr && zr !== ap.tol0) o._reach = zr;   // only the buyer's COLOR REACH edits travel
            return o;
        });   // [SPB-EASY-R6] analysis parts only (autoparts broke the count)
        var picks = Z.filter(function (z) { return z && z._easyAuto === 'pick' && z._easyAutoPick; }).map(function (z) { return lite(z, ['name', '_easyAutoIdx', '_easyAutoPick', 'color', 'colors', 'colorMode', 'pickerColor', 'pickerTolerance']); });
        var layers = Z.filter(function (z) { return z && z._easyAuto === 'layer'; }).map(function (z) { return lite(z, ['name', 'color', 'sourceLayers', 'sourceLayer', '_easyAutoLayer', '_easyAutoIdx']); });
        if (!layers.length && _pendingLayers && _pendingLayers.length) layers = _pendingLayers.slice();   // never lose parked layer parts
        var autoparts = Z.filter(function (z) { return z && z._easyAuto === 'autopart' && _autopartMaskUrl[z._easyAutoLayer]; }).map(function (z) { var o = lite(z, ['name', '_easyAutoLayer', '_easyAutoIdx', '_easyAutoShare']); o.maskDataUrl = _autopartMaskUrl[z._easyAutoLayer]; return o; });
        if (!autoparts.length && _pendingAutoparts && _pendingAutoparts.length) autoparts = _pendingAutoparts.slice();
        if (!parts.length && !layers.length) return;
        var plans = readPlans();
        plans[pk] = { parts: parts, layers: layers, autoparts: autoparts, picks: picks, tols: null };
        var keys = Object.keys(plans);
        while (keys.length > 8) { delete plans[keys.shift()]; }
        lsSet(LS_PLAN, JSON.stringify(plans));
    }
    function loadPlan(pk) { var p = readPlans()[pk]; return (p && typeof p === 'object') ? p : null; }

    function buildZones(reason, opts) {
        var x = X(); if (!x) return false;
        var src = srcCanvas(); if (!src) return false;
        var t0 = Date.now(), pk = paintKey();
        var saved = loadPlan(pk);
        var A = analyze(src);
        // [SPB-EASY-R7] restore by colour fingerprint (nearest saved part within 12), not by position.
        var usedSaved = [];
        var anyFp = !!(saved && Array.isArray(saved.parts) && saved.parts.some(function (sv) { return sv && sv._fp; }));
        function savedFor(p, idx) {
            if (!saved || !Array.isArray(saved.parts)) return null;
            if (!anyFp) {                                           // [SPB-EASY-R9] a plan saved before fingerprints: the old positional rule, once
                var sv0 = saved.parts[idx];
                return (saved.parts.length === A.parts.length && sv0 && sv0._easyAuto === p.kind) ? sv0 : null;
            }
            if (p.kind === 'remaining') { for (var r = 0; r < saved.parts.length; r++) if (saved.parts[r] && saved.parts[r]._easyAuto === 'remaining') return saved.parts[r]; return null; }
            var best = null, bd = 12;
            saved.parts.forEach(function (sv) {
                if (!sv || sv._easyAuto !== 'color' || !sv._fp || usedSaved.indexOf(sv) >= 0 || !/^#[0-9a-fA-F]{6}$/.test(sv._fp)) return;
                var d = wdc([parseInt(sv._fp.slice(1, 3), 16), parseInt(sv._fp.slice(3, 5), 16), parseInt(sv._fp.slice(5, 7), 16)], p.rgb);
                if (d < bd) { bd = d; best = sv; }
            });
            if (best) usedSaved.push(best);
            return best;
        }
        labelParts(A.parts);
        var Z = x.zones();
        // Layer parts belong to ONE paint: a PSD's "Numbers" must not follow a flat TGA loaded next (seen in QA).
        var keepLayers = Z.filter(function (z) { return z && z._easyAuto === 'layer' && z._easyAutoPaint === pk; });
        _pendingLayers = null;
        var keepAuto = Z.filter(function (z) { return z && z._easyAuto === 'autopart' && z._easyAutoPaint === pk; });
        _pendingAutoparts = (!keepAuto.length && saved && Array.isArray(saved.autoparts) && saved.autoparts.length) ? saved.autoparts.slice() : null;
        if (!keepLayers.length && saved && Array.isArray(saved.layers) && saved.layers.length) {
            // PSD layers rasterize AFTER the paint shows (the "11/11 layers loaded" toast), so at
            // build time the list may still be empty: park the saved layer parts and re-create
            // them the moment the layers exist (tick → restorePendingLayers).
            _pendingLayers = saved.layers.slice();
            keepLayers = restorePendingLayers(pk, true) || [];
        }
        var out = [], ci = 0, cc = 0, restored = 0;
        A.parts.forEach(function (p, idx) {
            var sv = savedFor(p, idx);
            if (sv && sv._reach && p.kind === 'color') setReach(p, sv._reach);
            var z = { id: newId(idx), pattern: 'none', finish: null, intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], regionMask: null, patternStack: [],
                      _easyAuto: p.kind, _easyAutoIdx: idx, _easyAutoShare: p.share || 0, _easyAutoPaint: pk };
            if (p.kind === 'color') {
                ci++; z.name = 'Color ' + ci;
                selToZone(z, p);                                   // [SPB-EASY-PBN] one stop = picker zone, several = Pro's multi zone
                z.base = pickBase(p.tone ? RECIPE_KIND[p.tone] : RECIPE_COLORS[(cc++) % RECIPE_COLORS.length]);
            } else { z.name = LABELS[p.kind]; z.color = p.kind; z.base = pickBase(RECIPE_KIND[p.kind]); }
            p.name = z.name;
            if (sv) {
                PLAN_FIELDS.forEach(function (k) { if (k === '_easyAuto') return; if (sv[k] === undefined) delete z[k]; else z[k] = sv[k]; });
                restored++;
            }
            out.push(z);
        });
        // [SPB-EASY-PBN 2026-09-22] layer parts FIRST: a layer the buyer picked wins its own pixels. After the
        // colour parts (old order) the owner's hue-shifted BASE01 layer kept jagged islands the colour parts had claimed.
        var keepPicks = Z.filter(function (z) { return z && z._easyAuto === 'pick' && z._easyAutoPaint === pk; });
        if (!keepPicks.length && saved && Array.isArray(saved.picks)) keepPicks = saved.picks.filter(function (sv) { return sv && sv._easyAutoPick; }).map(function (sv) {
            var z = { id: newId(sv._easyAutoIdx), pattern: 'none', finish: null, intensity: '100', customSpec: null, customPaint: null, customBright: null, colors: [], regionMask: null, patternStack: [],
                      _easyAuto: 'pick', _easyAutoIdx: sv._easyAutoIdx, _easyAutoPaint: pk, _easyAutoPick: sv._easyAutoPick, name: sv.name || 'Your pick' };
            ['color', 'colors', 'colorMode', 'pickerColor', 'pickerTolerance'].forEach(function (k) { if (sv[k] !== undefined) z[k] = sv[k]; });
            PLAN_FIELDS.forEach(function (k) { if (k !== '_easyAuto' && sv[k] !== undefined) z[k] = sv[k]; });
            return z;
        });
        (function () {                                              // [SPB-EASY-MERGE] restored merges: drop the merged-away zones
            _analysis = A;
            var tmpZ = out, byIdx = {}; tmpZ.forEach(function (z) { byIdx[z._easyAutoIdx] = z; });
            applyMergesFromZones(function (i) { return byIdx[i] || null; });
            out = tmpZ.filter(function (z) { var q = A.parts[z._easyAutoIdx]; return !(q && q.mergedInto != null); });
            out.forEach(function (z) { var q = A.parts[z._easyAutoIdx]; if (q && q.kind === 'color' && q.mergedFps && q.mergedFps.length) selToZone(z, q); });
        })();
        out = keepLayers.concat(keepAuto, keepPicks, out);          // [SPB-EASY-R6] layers, then your picks, then the automatic colours
        if (!(opts && opts.noUndo)) x.undoPush('Easy: built your car automatically');   // START OVER already holds the old design
        Z.splice(0, Z.length);
        out.forEach(function (z) { Z.push(z); });
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Z, 'easy-auto build'); } catch (e) {}
        _analysis = A; _builtFor = pk;
        rebuildLayerParts();
        lsSet(LS_BUILT, pk);
        savePlan();
        try { console.info('[EASY AUTO] built ' + out.length + ' parts in ' + (Date.now() - t0) + ' ms (' + (reason || 'paint loaded') + (restored ? ', ' + restored + ' restored' : '') + ')'); } catch (e) {}
        _buildAt = performance.now(); _matCache = { key: null, canvas: null }; _matchCache = { key: null, ok: true };
        x.refreshZonesUI(); x.kickPreview();
        ensureFreshPreview(x);
        return true;
    }
    // A paint switch inside Easy: the app's own load-preview is still in flight for a few seconds.
    // Kicking our render into that window produced renders of the PREVIOUS car (QA 2026-09-19); in
    // Pro, where nothing kicks, the new car lands in ~3 s. So: let the app's preview land first.
    var _lastPk = null, _pkChangedAt = 0;
    function appPreviewSettled() {
        if (previewMatchesSource()) return true;
        return (performance.now() - _pkChangedAt) > 1500;            // with the rev bump our own render is correct; only dodge the load burst
    }
    function reanalyze() {
        var src = srcCanvas(); if (!src) return false;
        _analysis = analyze(src); _builtFor = paintKey();
        if (!zonesMatchAnalysis()) {                                // [SPB-EASY-R8] the composite changed since these zones were built
            savePlan();
            return buildZones('paint changed since these parts were built', { noUndo: true });
        }
        var tolChanged = false;
        _analysis.parts.forEach(function (p, idx) {
            var z = zoneFor(idx); if (!z) return;
            p.name = z.name;
            var zr = p.kind === 'color' ? zoneReach(z) : null;
            if (zr && zr !== p.tol) { setReach(p, zr); tolChanged = true; }
            if (z && Array.isArray(z._easyAutoMerged) && z._easyAutoMerged.length) tolChanged = true;   // the buyer's COLOR REACH wins
        });
        applyMergesFromZones();                                     // [SPB-EASY-MERGE] merges live on the zones
        if (tolChanged) recomputeOwner();
        labelParts(_analysis.parts);
        rebuildLayerParts();
        return true;
    }
    function zoneFor(partIdx) { var Z = zonesRef(); for (var i = 0; i < Z.length; i++) if (Z[i] && Z[i]._easyAutoIdx === partIdx) return Z[i]; return null; }
    function zoneIndexFor(partIdx) { var Z = zonesRef(); for (var i = 0; i < Z.length; i++) if (Z[i] && Z[i]._easyAutoIdx === partIdx) return i; return -1; }
    function owns() {
        var x = I(); if (!x) return false;
        if (!x.zones().some(function (z) { return z && z._easyAuto; })) return false;
        var pk = paintKey();
        return !(pk && leftGet() === pk);
    }
    function finishNameOf(z) {
        var x = I(); if (!z || !x) return '';
        var f = z.finish ? x.finishInfo(x.finishKey('monolithic', z.finish)) : (z.base ? x.finishInfo(x.finishKey('base', z.base)) : null);
        return f ? f.name : (z.base || z.finish || 'no finish yet');
    }
    function finishKeyOf(z) { var x = I(); if (!z || !x) return null; return z.finish ? x.finishKey('monolithic', z.finish) : (z.base ? x.finishKey('base', z.base) : null); }

    // ------------------------------------------------------- highlight hosts
    function ensureHosts() {
        ['spbEasyLiveCanvas', 'spbEasyPreviewImg', 'spbEasySourceCanvas'].forEach(function (id) {
            var cv = $(id); if (!cv) return;
            if (_hosts.some(function (h) { return h.cv === cv; })) return;
            var parent = cv.parentElement; if (!parent) return;
            if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';
            var ov = document.createElement('canvas');
            ov.className = 'spb-easy-auto-hilite'; ov.width = N; ov.height = N;
            ov.setAttribute('role', 'button'); ov.tabIndex = 0;
            ov.setAttribute('aria-label', 'Tap a part of your car to change its finish');
            ov.title = 'Tap any part of your car to change it';
            parent.appendChild(ov);
            ov.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); if (_picking) { pickAt(ev, ov); return; } var p = partAt(ev, ov); if (p >= 0) openPop(p, { x: ev.clientX, y: ev.clientY }); });
            ov.addEventListener('mousemove', function (ev) { var p = partAt(ev, ov); if (p !== _hoverPart) { _hoverPart = p; redrawAll(); } showTip(ev, p); });
            ov.addEventListener('mouseleave', function () { _hoverPart = -1; redrawAll(); showTip(null, -1); });
            ov.addEventListener('keydown', function (ev) {          // keyboard: Enter/Space opens the hovered part, else the biggest one
                if (ev.key !== 'Enter' && ev.key !== ' ') return;
                ev.preventDefault(); var p = _hoverPart >= 0 ? _hoverPart : 0; if (partById(p)) openPop(p, null);
            });
            _hosts.push({ cv: cv, ov: ov });
        });
    }
    function layoutHosts() {
        var on0 = inAutoView() && !!_analysis;
        document.body.classList.toggle('spb-easy-auto-view', on0);
        _hosts.forEach(function (h) {
            var on = on0 && !h.cv.hidden && h.cv.offsetParent !== null && h.cv.getBoundingClientRect().width > 40;
            h.ov.classList.toggle('on', on);
            if (!on) return;
            var host = h.ov.offsetParent, pr = host ? host.getBoundingClientRect() : { left: 0, top: 0 }, r = h.cv.getBoundingClientRect();
            h.ov.style.left = (r.left - pr.left) + 'px'; h.ov.style.top = (r.top - pr.top) + 'px';
            h.ov.style.width = r.width + 'px'; h.ov.style.height = r.height + 'px';
        });
    }
    var _tip = null;
    function showTip(ev, partIdx) {
        // A small label that follows the cursor: "Orange · Pearl" — discoverability without a click.
        if (!_tip) { _tip = document.createElement('div'); _tip.className = 'spb-easy-auto-tip'; _tip.hidden = true; document.body.appendChild(_tip); }
        var p = partIdx >= 0 ? partById(partIdx) : null;
        if (!ev || !p) { _tip.hidden = true; return; }
        var z = zoneFor(partIdx);
        _tip.textContent = partLabel(p) + ' · ' + finishNameOf(z) + ' — click to change';
        _tip.style.left = Math.min(window.innerWidth - 240, ev.clientX + 16) + 'px';
        _tip.style.top = Math.max(8, ev.clientY - 30) + 'px';
        _tip.hidden = false;
    }
    function partAt(ev, ov) {
        if (!_analysis) return -1;
        var r = ov.getBoundingClientRect(), u = (ev.clientX - r.left) / r.width, v = (ev.clientY - r.top) / r.height;
        if (u < 0 || v < 0 || u >= 1 || v >= 1) return -1;
        var o = _analysis.owner[Math.floor(v * _analysis.n) * _analysis.n + Math.floor(u * _analysis.n)];
        return o === 255 ? -1 : o;
    }
    function setPicking(on) {
        _picking = !!on; document.body.classList.toggle('spb-easy-auto-picking', _picking);
        var b = $('spbEasyAutoPick'); if (b) { b.classList.toggle('on', _picking); b.textContent = _picking ? '✕ Cancel — click a colour on the car' : '🎯 Pick a color off the car'; }
        if (_picking) toast('Click any colour on SOURCE or LIVE — it becomes its own part');
    }
    function pickAt(ev, ov) {
        var x = X(), src = srcCanvas(); if (!x || !src) { setPicking(false); return; }
        var r = ov.getBoundingClientRect(), u = (ev.clientX - r.left) / r.width, v = (ev.clientY - r.top) / r.height;
        if (u < 0 || v < 0 || u >= 1 || v >= 1) return;
        var px = Math.min(src.width - 2, Math.max(1, Math.floor(u * src.width))), py = Math.min(src.height - 2, Math.max(1, Math.floor(v * src.height)));
        var d; try { d = src.getContext('2d', { willReadFrequently: true }).getImageData(px - 1, py - 1, 3, 3).data; } catch (e) { setPicking(false); return; }
        var c = [d[16], d[17], d[18]], acc = [0, 0, 0], n = 0;                          // centre pixel, smoothed by its like-coloured neighbours
        for (var k = 0; k < 9; k++) { var q = [d[k * 4], d[k * 4 + 1], d[k * 4 + 2]]; if (wdc(q, c) < 12) { acc[0] += q[0]; acc[1] += q[1]; acc[2] += q[2]; n++; } }
        var rgb = [Math.round(acc[0] / n), Math.round(acc[1] / n), Math.round(acc[2] / n)];
        var near = 999;
        (_analysis ? _analysis.parts : []).forEach(function (p) { if (p.rgb) { var dd = wdc(rgb, p.rgb); if (dd > 6 && dd < near) near = dd; } });
        _pickParts.forEach(function (p) { var dd = wdc(rgb, p.rgb); if (dd > 6 && dd < near) near = dd; });
        var tol = Math.max(12, Math.min(40, Math.round(0.5 * near)));
        var idx = PICK_IDX; zonesRef().forEach(function (z) { if (z && z._easyAuto === 'pick' && z._easyAutoIdx >= idx) idx = z._easyAutoIdx + 1; });
        if (idx >= LAYER_IDX) { toast('That is a lot of picks — remove one first'); setPicking(false); return; }
        x.undoPush('Easy: picked ' + hexOf(rgb) + ' off the car');
        var z = { id: newId(idx), name: colorWord(rgb) + ' (your pick)', pattern: 'none', base: null, finish: null, intensity: '100', customSpec: null, customPaint: null, customBright: null,
                  colors: [], regionMask: null, patternStack: [], _easyAuto: 'pick', _easyAutoIdx: idx, _easyAutoPaint: paintKey(), _easyAutoPick: { rgb: rgb, tol0: tol } };
        selToZone(z, { sel: [{ rgb: rgb, tol: tol }], hex: hexOf(rgb), tol: tol });
        var Z = x.zones(); Z.splice(pickInsertAt(Z), 0, z);
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(Z, 'easy-auto pick'); } catch (e) {}
        setPicking(false);
        rebuildLayerParts(); x.refreshZonesUI(); renderRail(); savePlan();
        openPop(idx, { x: ev.clientX, y: ev.clientY });
    }
    function removePick(idx) {
        var x = X(); if (!x) return;
        var Z = x.zones(), at = -1; for (var i = 0; i < Z.length; i++) if (Z[i] && Z[i]._easyAuto === 'pick' && Z[i]._easyAutoIdx === idx) at = i;
        if (at < 0) return;
        x.undoPush('Easy: removed a picked colour');
        Z.splice(at, 1); _popPart = -1; closePop();
        rebuildLayerParts(); x.refreshZonesUI(); x.kickPreview(); renderRail(); savePlan();
    }
    function hiliteColorFor(partIdx) {
        // Orange on an orange part is invisible (bpierce QA): light a colour part with its complement.
        var p = partById(partIdx);
        if (!p || !p.rgb) return PALETTE[0];
        var r = p.rgb[0] / 255, g = p.rgb[1] / 255, b = p.rgb[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0;
        if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
        if (d < 0.12) return PALETTE[0];                            // greys: orange reads fine
        h = (h + 180) % 360;
        var c = 1, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = 0.05, rr, gg, bb;
        if (h < 60) { rr = c; gg = x; bb = 0; } else if (h < 120) { rr = x; gg = c; bb = 0; } else if (h < 180) { rr = 0; gg = c; bb = x; } else if (h < 240) { rr = 0; gg = x; bb = c; } else if (h < 300) { rr = x; gg = 0; bb = c; } else { rr = c; gg = 0; bb = x; }
        return [Math.round((rr + m) * 255), Math.round((gg + m) * 255), Math.round((bb + m) * 255)];
    }
    function selMask(sel) {                                          // samples a stop list catches (squared distances, no sqrt)
        var data = _analysis.data, NN = N * N, m = new Uint8Array(NN), k = sel.length, T = sel.map(function (st) { var t = 0.99 * st.tol; return t * t; });
        for (var i = 0; i < NN; i++) {
            var o = i * 4, r = data[o], g = data[o + 1], b = data[o + 2];
            for (var s = 0; s < k; s++) { var c = sel[s].rgb, dr = r - c[0], dg = g - c[1], db = b - c[2]; if (dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11 < T[s]) { m[i] = 1; break; } }
        }
        return m;
    }
    function computeFocus(mode) {
        // [SPB-EASY-R7] once per redraw (was once per visible pane, with a sqrt per stop per sample)
        if (!_analysis) return null;
        if (mode.all) return { all: true };
        var own = _analysis.owner, NN = N * N, m = null, i;
        var reach = mode.reach, sel = mode.part >= 0;
        if (reach) {
            var rp = partById(reach.part);                          // picks (50..99) too — review: the reach preview dimmed the whole car on a pick
            if (rp && rp.sel) {
                var rs = reach.tol / Math.max(1, rp.tol0 || rp.tol); m = selMask(rp.sel.map(function (st) { return { rgb: st.rgb, tol: reachTol(st, rs) }; }));
                // [SPB-EASY-R9] first wins, like the render: layers, picks (for a colour part) and earlier colour parts keep their pixels
                var k = reach.part, isPick = k >= PICK_IDX && k < LAYER_IDX;
                for (i = 0; i < NN; i++) if (m[i]) { var o = own[i]; if (o !== 255 && o !== k && (o >= LAYER_IDX || (!isPick && o >= PICK_IDX) || (!isPick && o < k))) m[i] = 0; }
            }
            return { mask: m || new Uint8Array(NN), dimA: 175 };
        }
        var fp = sel ? mode.part : mode.hover;
        if (!sel && _hoverMask) return { mask: _hoverMask, dimA: 150 };   // layer row hover in the LAYERS panel
        if (fp == null || fp < 0) return null;
        var p = partById(fp);
        if (fp >= LAYER_IDX && p && p.mask) m = p.mask;
        else if (fp >= PICK_IDX && fp < LAYER_IDX && p && p.sel) { m = selMask(p.sel); for (i = 0; i < NN; i++) if (m[i] && own[i] !== 255 && own[i] >= LAYER_IDX) m[i] = 0; }   // a pick: its own catch, minus layer parts (they win)
        else { m = new Uint8Array(NN); for (i = 0; i < NN; i++) if (own[i] === fp) m[i] = 1; }
        return { mask: m, dimA: sel ? 175 : 150 };
    }
    function drawHilite(ov, fc) {
        // [SPB-EASY-R5 2026-09-22] Hover, selection and COLOR REACH dim everything ELSE: the part shows in its
        // true colour on SOURCE (and in context on LIVE). The old white alpha-70 tint vanished on yellow.
        var ctx = ov.getContext('2d'); ctx.clearRect(0, 0, N, N);
        if (!_analysis || !fc) return;
        var img = ctx.createImageData(N, N), d = img.data, own = _analysis.owner, NN = N * N, i;
        if (fc.all) {                                               // "here are your parts" flash after a build
            for (i = 0; i < NN; i++) { var o = own[i]; if (o === 255) continue; var col = PALETTE[o % PALETTE.length]; d[i * 4] = col[0]; d[i * 4 + 1] = col[1]; d[i * 4 + 2] = col[2]; d[i * 4 + 3] = 150; }
        } else {
            var m = fc.mask, a0 = fc.dimA;
            for (i = 0; i < NN; i++) if (!m[i]) d[i * 4 + 3] = a0;  // black, so the part's own colour pops
        }
        ctx.putImageData(img, 0, 0);
    }
    var _reachPreview = null;
    function redrawAll() {
        var mode = _flashTimer ? { all: true } : (_reachPreview ? { reach: _reachPreview } : { part: _popPart, hover: _hoverPart });
        var fc = null, done = false;
        _hosts.forEach(function (h) { if (!h.ov.classList.contains('on')) return; if (!done) { fc = computeFocus(mode); done = true; } drawHilite(h.ov, fc); });
    }
    function flashAll(ms) {
        if (_flashTimer) clearTimeout(_flashTimer);
        _flashTimer = setTimeout(function () { _flashTimer = null; redrawAll(); }, ms || 1600);
        redrawAll();
    }

    // ------------------------------------- LIVE pane: in the light / channels
    // Owner QA 2026-09-19: "the live previews aren't updating". For source-colour finishes the
    // PAINT render is byte-identical (the server answers paint_unchanged) — only the SPEC map moves,
    // and it lands in ~1 s. A paint-only LIVE therefore never changes when you swap chrome for candy.
    // LIVE now shows the rendered paint LIT BY the live spec map (Easy's own whole-car "REAL MATERIAL"
    // model, same LIGHT_MODES), refreshed the instant either image arrives; "AS PAINTED" is one click.
    function specSourceImg() {
        var img = $('livePreviewSpecImg');
        if (img && img.complete && img.naturalWidth > 0 && img.getAttribute('src')) return img;
        return null;
    }
    function paintSourceImg() {
        var img = $('livePreviewImg');
        if (img && img.complete && img.naturalWidth > 0 && img.getAttribute('src')) return img;
        var c = $('spbEasySourceCanvas');
        return (c && c.width >= 512) ? c : null;
    }
    function specCanvases() {
        var img = specSourceImg(); if (!img) return null;
        if (_specCache.src === img.src && _specCache.canvases) return _specCache.canvases;
        var t = { all: document.createElement('canvas'), r: document.createElement('canvas'), g: document.createElement('canvas'), b: document.createElement('canvas') };
        var size = Math.min(2048, Math.max(256, img.naturalWidth || 512));
        try { if (typeof window.spbRenderSpecProofSet === 'function' && window.spbRenderSpecProofSet(img, t, size)) { _specCache = { src: img.src, canvases: t }; return t; } } catch (e) {}
        return null;
    }
    function liveMode() { return lsGet(LS_LIVE) === 'light' ? 'light' : 'paint'; }
    function lightKey() { var x = I(); return (x && x.state && x.state.light) || 'studio'; }
    function lightModes() { var x = I(); return (x && x.LIGHT_MODES) || { studio: { label: 'GARAGE', m: 0.38, r: 0.34, c: 0.18, shade: 0.72, hi: 52, hiPow: 1.0, hiCut: 0.0, amb: 1.0, alb: 0.0 } }; }
    function materialCanvas() {
        var spec = specSourceImg(), paint = paintSourceImg(); if (!spec || !paint) return null;
        var L = lightModes()[lightKey()] || lightModes().studio;
        var key = (spec.src || '').length + '|' + (paint.src || paint.width) + '|' + lightKey();
        if (_matCache.key === key && _matCache.canvas) return _matCache.canvas;
        var w = Math.min(1024, spec.naturalWidth || 1024), h = Math.min(1024, spec.naturalHeight || 1024);
        var out = document.createElement('canvas'); out.width = w; out.height = h;
        var ctx = out.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(paint, 0, 0, w, h);
        var px = ctx.getImageData(0, 0, w, h), d = px.data;
        var sc = document.createElement('canvas'); sc.width = w; sc.height = h;
        var sctx = sc.getContext('2d', { willReadFrequently: true }); sctx.drawImage(spec, 0, 0, w, h);
        var sd = sctx.getImageData(0, 0, w, h).data;
        for (var i = 0; i < d.length; i += 4) {                      // Easy's REAL MATERIAL model (renderWholeMaterialPreview)
            var metal = sd[i] / 255, rough = sd[i + 1] / 255, coat = sd[i + 2] / 255;
            var response = metal * L.m + ((160 / 255) - rough) * L.r + (coat - 1) * L.c;
            var shade = (1 + response * L.shade) * L.amb;
            var lum = (d[i] + d[i + 1] + d[i + 2]) / 765;
            var albW = 1 - L.alb + L.alb * lum;
            var highlight = Math.pow(Math.max(0, response - L.hiCut), L.hiPow) * L.hi * albW;
            d[i] = Math.max(0, Math.min(255, d[i] * shade + highlight));
            d[i + 1] = Math.max(0, Math.min(255, d[i + 1] * shade + highlight));
            d[i + 2] = Math.max(0, Math.min(255, d[i + 2] * shade + highlight));
        }
        ctx.putImageData(px, 0, 0);
        _matCache = { key: key, canvas: out };
        return out;
    }
    function ensureSpecView() {
        if (_specView && _specView.isConnected) return _specView;
        var live = $('spbEasyPreviewImg') || $('spbEasyLiveCanvas'); if (!live || !live.parentElement) return null;
        _specView = document.createElement('canvas');
        _specView.className = 'spb-easy-auto-specview'; _specView.hidden = true;
        live.parentElement.appendChild(_specView);
        return _specView;
    }
    function liveCap() { return _liveTog ? _liveTog.querySelector('.spb-easy-auto-livecap') : null; }
    function showOnLive(canvas, subtitle) {
        var view = ensureSpecView(); if (!view) return;
        var cap = liveCap();                                        // our own caption: Easy's syncStage owns #spbEasyLiveSubtitle
        if (!canvas) { view.hidden = true; if (cap) cap.textContent = 'AS PAINTED — the same live render Pro shows, exactly as it will be written'; return; }
        if (view.width !== canvas.width || view.height !== canvas.height) { view.width = canvas.width; view.height = canvas.height; }
        view.getContext('2d').drawImage(canvas, 0, 0);
        view.hidden = false;
        if (cap) cap.textContent = subtitle;
    }
    // [SPB-EASY-R6 2026-09-22] A material-only change (keep my colours, a LOOK, shine-only) leaves the painted car
    // identical — AS PAINTED (Pro's preview) cannot show it, and the owner read that as "not updating". When the new
    // spec map lands, LIVE shows it for ~3 s with a caption, then the car again.
    var _shine = null;
    function flashShine(caption) { var img = specSourceImg(); _shine = { armed: img ? img.src : '', until: 0, t0: performance.now(), caption: caption }; }
    function syncLiveView() {
        if (!inAutoView()) { if (_specView) _specView.hidden = true; syncLiveToggle(); return; }
        var ch = _specPinned || _specHover;
        if (!ch && _shine) {
            var si0 = specSourceImg(), now0 = performance.now();
            if (now0 - _shine.t0 > 15000) _shine = null;
            else if (si0 && si0.src !== _shine.armed) {
                if (!_shine.until) { _shine.until = now0 + 2800; setTimeout(syncLiveView, 2900); }
                if (now0 < _shine.until) { var cs0 = specCanvases(); if (cs0 && cs0.all) { showOnLive(cs0.all, _shine.caption); syncLiveToggle(); return; } }
                else _shine = null;
            }
        }
        if (ch) {
            var cs = specCanvases();
            if (cs && cs[ch]) showOnLive(cs[ch], 'Showing ' + CHANNEL_NAMES[ch] + (_specPinned ? ' — click the chip again for the car' : ' — click the chip to keep it'));
        } else if (previewIsStale()) {
            // The render for THIS build has not landed yet: show the buyer's own paint, never the previous car.
            var srcC = $('spbEasySourceCanvas');
            if (srcC && srcC.width >= 512) showOnLive(srcC, 'Rendering your finishes… (a second or two)');
            else showOnLive(null);
        } else if (liveMode() === 'light') {
            var m = materialCanvas();
            if (m) showOnLive(m, 'IN THE LIGHT · ' + ((lightModes()[lightKey()] || {}).label || 'GARAGE') + ' — how the shine will read on track');
            else showOnLive(null);
        } else showOnLive(null);
        document.querySelectorAll('.spb-easy-channel').forEach(function (el) { el.classList.toggle('spb-easy-auto-pinned', !!_specPinned && chanOf(el) === _specPinned); el.classList.toggle('spb-easy-auto-hover', !_specPinned && !!_specHover && chanOf(el) === _specHover); });
        syncLiveToggle();
    }
    function syncSpecView() { syncLiveView(); }
    function scheduleLiveRefresh() { if (_matTimer) clearTimeout(_matTimer); _matTimer = setTimeout(function () { _matTimer = null; _matCache = { key: null, canvas: null }; syncLiveView(); }, 60); }
    // Pro anchors every toast bottom-LEFT with inline !important (above "+ Add Zone"); in this view
    // the rail lives there, so re-anchor each toast to bottom-centre the moment it shows.
    var _toastObs = null, _toastWrapped = false;
    function reanchorToast() {
        var t = $('toast'); if (!t || !inAutoView() || !t.classList.contains('show')) return;
        if (/Press \? or F1/i.test(String(t.textContent || ''))) { t.classList.remove('show'); return; }   // Pro's keyboard-shortcut tip means nothing in Easy (it also sat clipped at the left edge)
        var set = function (p, v) { try { t.style.setProperty(p, v, 'important'); } catch (e) {} };
        // [SPB-EASY-TELL2 2026-09-30] the TELL bar owns the top of the stage now (a toast there sat ON the input and swallowed clicks).
        // Toasts float in the free band just above the spec-channel strip, centred on the stage; pointer-events are off in CSS.
        var strip = $('spbEasyChannelStrip'), r = strip ? strip.getBoundingClientRect() : null;
        if (r && r.width > 100 && r.top > 200) { set('left', Math.round(r.left + r.width / 2) + 'px'); set('right', 'auto'); set('top', 'auto'); set('bottom', Math.round(window.innerHeight - r.top + 10) + 'px'); }
        else { set('left', '50%'); set('right', 'auto'); set('top', 'auto'); set('bottom', '12px'); }
        set('transform', 'translateX(-50%)'); set('max-width', '560px');
    }
    function wireToastAnchor() {
        if (!_toastWrapped && typeof window.showToast === 'function') {
            // Pro re-anchors the toast bottom-left AFTER it shows (inline !important, sometimes a frame later);
            // wrap the entry point and re-anchor a few times after each show — the observer alone lost the race (QA).
            _toastWrapped = true;
            var orig = window.showToast;
            window.showToast = function () { var r; try { r = orig.apply(this, arguments); } finally { if (inAutoView()) [0, 60, 260, 600].forEach(function (ms) { setTimeout(reanchorToast, ms); }); } return r; };
        }
        if (_toastObs || !window.MutationObserver) return;
        var t = $('toast'); if (!t) return;
        _toastObs = new MutationObserver(function () {
            if (!inAutoView() || !t.classList.contains('show')) return;
            reanchorToast();
        });
        _toastObs.observe(t, { attributes: true, attributeFilter: ['class', 'style'] });
    }
    function wireImageObservers() {
        if (_imgObs || !window.MutationObserver) return;
        var pi = $('livePreviewImg'), si = $('livePreviewSpecImg'); if (!pi || !si) return;
        _imgObs = new MutationObserver(function (records) {          // no 800 ms poll: refresh the moment a render lands
            records.forEach(function (m) { if (m.target && m.target.id === 'livePreviewImg') _imgStamp.paint = performance.now(); else _imgStamp.spec = performance.now(); });
            scheduleLiveRefresh();                                    // Easy mirrors #livePreviewImg itself (installPreviewMirror) — no second writer here
        });
        _imgObs.observe(pi, { attributes: true, attributeFilter: ['src'] });
        _imgObs.observe(si, { attributes: true, attributeFilter: ['src'] });
        [pi, si].forEach(function (img) { img.addEventListener('load', scheduleLiveRefresh); });
    }
    function ensureLiveToggle() {
        var card = document.querySelector('.spb-easy-live-card'); if (!card) return;
        if (_liveTog && _liveTog.isConnected) return;
        var media = card.querySelector('.spb-easy-proof-media'); if (!media) return;
        _liveTog = document.createElement('div');
        _liveTog.className = 'spb-easy-auto-livetog'; _liveTog.setAttribute('role', 'group'); _liveTog.setAttribute('aria-label', 'Live preview mode');
        var modes = lightModes(), opts = '';
        Object.keys(modes).forEach(function (k) { opts += '<option value="' + esc(k) + '">' + esc(modes[k].label || k) + '</option>'; });
        _liveTog.innerHTML =
            '<button type="button" data-live="paint" title="The live render, exactly as Pro shows it and as it will be written to your TGA.">AS PAINTED</button>' +
            '<button type="button" data-live="light" title="The same render lit by its spec map — a quick feel for how the shine reads on track.">IN THE LIGHT</button>' +
            '<select class="spb-easy-auto-lightsel" title="Which light to judge the shine under" aria-label="Light">' + opts + '</select>' +
            '<small class="spb-easy-auto-livecap" aria-live="polite"></small>';
        card.insertBefore(_liveTog, media);
        _liveTog.querySelectorAll('[data-live]').forEach(function (b) { b.addEventListener('click', function () { lsSet(LS_LIVE, b.getAttribute('data-live')); _specPinned = null; syncLiveView(); }); });
        var sel = _liveTog.querySelector('select');
        sel.value = lightKey();
        sel.addEventListener('change', function () { var x = I(); if (x && x.state) x.state.light = sel.value; lsSet('spb_easy_auto_light_v1', sel.value); try { x.persistState(); } catch (e) {} _matCache = { key: null, canvas: null }; syncLiveView(); });
        syncLiveToggle();
    }
    function syncLiveToggle() {
        if (!_liveTog) return;
        _liveTog.hidden = !inAutoView();                             // dead controls in the whole-car / by-colour views otherwise
        var mode = liveMode();
        _liveTog.querySelectorAll('[data-live]').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-live') === mode); });
        var sel = _liveTog.querySelector('select'); if (sel) { sel.hidden = mode !== 'light'; if (sel.value !== lightKey()) sel.value = lightKey(); }
    }
    function chanOf(el) { var cv = el.querySelector('canvas'); var id = cv ? cv.id : ''; return id === 'spbEasySpecAll' ? 'all' : id === 'spbEasySpecR' ? 'r' : id === 'spbEasySpecG' ? 'g' : id === 'spbEasySpecB' ? 'b' : null; }
    function wireSpecStrip() {
        if (_stripWired) return;
        var chips = document.querySelectorAll('.spb-easy-channel'); if (!chips.length) return;
        _stripWired = true;
        chips.forEach(function (el) {
            var ch = chanOf(el); if (!ch) return;
            el.title = 'Hover: see ' + CHANNEL_NAMES[ch] + ' big on the car. Click: keep it there (click again to go back).';
            el.style.cursor = 'pointer';
            el.addEventListener('mouseenter', function () { if (_hoverTimer) clearTimeout(_hoverTimer); _hoverTimer = setTimeout(function () { _hoverTimer = null; _specHover = ch; syncLiveView(); }, 140); });   // intent delay: passing over the strip must not flicker LIVE
            el.addEventListener('mouseleave', function () { if (_hoverTimer) { clearTimeout(_hoverTimer); _hoverTimer = null; } _specHover = null; syncLiveView(); });
            el.addEventListener('click', function (ev) { ev.preventDefault(); ev.stopPropagation(); _specPinned = (_specPinned === ch) ? null : ch; syncLiveView(); });
        });
    }

    // ---------------------------------------------------------- lists: rail
    function rowSwatchCss(p, z) {
        // [SPB-EASY-R7] the dot tells you what the part BECOMES: your colour on the left, its new colour on the right
        var base = swatchCss(p), to = null, x = I();
        if (z && z.baseColorMode === 'solid' && /^#[0-9a-fA-F]{6}$/.test(z.baseColor || '')) to = z.baseColor;
        else if (z && z.baseColorMode === 'special' && x) { var f = z.finish ? x.finishInfo(x.finishKey('monolithic', z.finish)) : (z.base ? x.finishInfo(x.finishKey('base', z.base)) : null); if (f && /^#[0-9a-fA-F]{6}$/.test(f.swatch || '')) to = f.swatch; }
        if (!to) return base;
        var from = (p && p.hex) ? p.hex : '#888888';
        return 'background:linear-gradient(135deg,' + from + ' 0 48%,' + to + ' 52% 100%)';
    }
    function swatchCss(p) {
        if (!p) return '';
        if (p.kind === 'color') return (p.fade && p.stops && p.stops.length > 1) ? 'background:linear-gradient(135deg,' + p.stops.join(',') + ')' : 'background:' + p.hex;
        if (p.kind === 'dark') return 'background:linear-gradient(135deg,#0a0a0a,#3a3a3a)';
        if (p.kind === 'white') return 'background:linear-gradient(135deg,#ffffff,#d8d8d8)';
        if (p.kind === 'layer') return 'background:linear-gradient(135deg,#2a6cff,#9bd1ff)';
        if (p.kind === 'autopart') return 'background:linear-gradient(135deg,#ff4d6d,#ffd166)';
        return 'background:repeating-linear-gradient(45deg,#666 0 4px,#999 4px 8px)';
    }
    function partTitle(p, z) {
        if (p.kind === 'layer') return 'Just this PSD layer (' + esc(p.name) + '), whatever colours it holds. Click to pick its finish.';
        if (p.kind === 'autopart') return 'Just the ' + esc(p.name).toLowerCase() + ' the finder cut out, whatever colours they hold. Click to pick their finish.';
        if (p.kind === 'remaining') return 'Every pixel no other part claimed — edges, tiny details, gradients. Click to pick its finish.';
        return 'All paint that matches this colour (COLOR REACH decides how many shades). Click to pick its finish.';
    }
    function finishThumbHtml(z) {
        var x = I(), k = finishKeyOf(z), f = k && x ? x.finishInfo(k) : null;
        if (!f) return '<span class="spb-easy-auto-fin none" title="No finish yet">—</span>';
        var u = ''; try { u = x.thumbUrl(f); } catch (e) {}
        return u ? '<img class="spb-easy-auto-fin" alt="" src="' + esc(u) + '" title="' + esc(f.name) + ' — paint on the left, shine on the right">' : '';
    }
    // ---------------------------------------------------------- one-tap looks
    // Four recipes over the parts the build found — instant variety before anyone opens a picker.
    // Each is real bases on real zones; UNDO steps back in one go.
    var LOOKS = [
        { id: 'show', label: 'Show car', title: 'Chrome on your main colour, candy and pearl on the rest — the look that turns heads in the pits.', colors: ['chrome', 'candy', 'pearl', 'chrome', 'candy', 'pearl'], white: 'gloss', dark: 'piano_black', rest: 'gloss' },
        { id: 'oem', label: 'Subtle OEM', title: 'Factory metallic on every colour, gloss on the rest — clean and believable.', colors: ['metallic', 'metallic', 'metallic', 'metallic', 'metallic', 'metallic'], white: 'gloss', dark: 'gloss', rest: 'gloss' },
        { id: 'candy', label: 'Candy shop', title: 'Deep candy on every colour, pearl on the white — wet, glossy, loud.', colors: ['candy', 'candy', 'candy', 'candy', 'candy', 'candy'], white: 'pearl', dark: 'wet_look', rest: 'gloss' },
        { id: 'matte', label: 'Matte & chrome', title: 'Matte on every colour, chrome on the white and logos — the modern contrast look.', colors: ['matte', 'matte', 'matte', 'matte', 'matte', 'matte'], white: 'chrome', dark: 'matte', rest: 'matte' }
    ];
    function applyLook(id) {
        var x = X(), look = null; if (!x || !_analysis) return;
        LOOKS.forEach(function (l) { if (l.id === id) look = l; }); if (!look) return;
        x.undoPush('Easy: look "' + look.label + '"');
        var ci = 0, lookParts = _analysis.parts.map(function (p, idx) { return [p, idx]; }).concat(_pickParts.map(function (p) { return [p, p.idx]; }));   // picks take the look too
        lookParts.forEach(function (pair) {
            var p = pair[0], idx = pair[1];
            var z = zoneFor(idx); if (!z) return;
            var base = p.kind === 'remaining' ? look.rest : (p.tone === 'white' ? look.white : (p.tone === 'dark' ? look.dark : look.colors[(ci++) % look.colors.length]));
            var f = x.finishInfo(x.finishKey('base', pickBase(base))); if (!f) return;
            proPick(z, f);
            // [SPB-EASY-R6 2026-09-22] a look is materials over YOUR colours and a clean slate: the old colour source
            // survived (a python pick's 'mono:slt_reticulated' spread scales over the whole fade after "Matte & chrome").
            setColorOn(z, f, 'mine'); z._easyAutoColorChosen = false;
            z.baseStrength = 1; delete z.baseSpecStrength; z.baseScale = 1; delete z.specScale;
            delete z.baseHueOffset; delete z.baseSaturationAdjust; delete z.baseBrightnessAdjust;
        });
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(x.zones(), 'easy-auto look'); } catch (e) {}
        x.refreshZonesUI(); x.kickPreview(); refreshLists(); savePlan();
        document.querySelectorAll('.spb-easy-auto-look').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-look') === id); });
        toast('Look "' + look.label + '" on the whole car — UNDO steps back');
        flashShine('WHAT CHANGED: the shine — "' + look.label + '" keeps your colours and changes every material. Back to the car in a moment…');
    }
    function looksHtml() {
        return '<div class="spb-easy-auto-looks" role="group" aria-label="Try a look"><span title="One tap puts a whole recipe on every part. Tap a part afterwards to change any of it.">TRY A LOOK</span>' +
            LOOKS.map(function (l) { return '<button type="button" class="spb-easy-auto-look" data-look="' + l.id + '" title="' + esc(l.title) + '">' + esc(l.label) + '</button>'; }).join('') + '</div>';
    }
    function rowHtml(p, idx) {
        var z = zoneFor(idx), pct = Math.round((p.share || 0) * 100);
        return '<button type="button" class="spb-easy-auto-row' + (idx === _popPart ? ' on' : '') + '" data-part="' + idx + '" role="listitem" title="' + partTitle(p, z) + '">' +
            '<span class="spb-easy-auto-sw" style="' + rowSwatchCss(p, z) + '"></span>' +
            '<span class="spb-easy-auto-row-text"><b>' + esc(partLabel(p)) + '</b><small>' + esc(finishNameOf(z)) + ' · ' + pct + '% of your car</small></span>' +
            finishThumbHtml(z) +
            '<span class="spb-easy-auto-row-go" aria-hidden="true">›</span></button>';
    }
    function renderRail() {
        var x = I(); if (!x || !x.els || !x.els.rail) return;
        if (!x.paintLoaded()) {
            // Nothing to build yet: say so plainly and offer the one action that matters.
            x.els.rail.innerHTML = x.railHeader('YOUR CAR', 'Open your paint and Shokker builds it for you — every colour gets a part and a finish, then you tap the car to change anything.', false) +
                '<div class="spb-easy-auto-actions"><button type="button" class="spb-easy-auto-act" id="spbEasyAutoOpenPaint" title="Choose your iRacing paint file (TGA, PNG or PSD)">📂 Open my paint</button></div>';
            var ob = $('spbEasyAutoOpenPaint');
            if (ob) ob.addEventListener('click', function () { var b = $('spbEasyOpenPaint'); if (b) b.click(); else if (typeof window.openPaintFilePicker === 'function') { try { window.openPaintFilePicker(); } catch (e) {} } });
            return;
        }
        if (!_analysis) {
            var pkNow = paintKey();
            var ok = zonesRef().some(function (z) { return z && z._easyAuto && z._easyAutoPaint === pkNow; }) ? reanalyze() : buildZones('rail');   // re-entry keeps the buyer's zones
            if (!ok || !_analysis) { x.els.rail.innerHTML = x.railHeader('BUILDING YOUR CAR…', 'Reading your paint — one moment.', false); return; }
        }
        if (_analysis && _analysis.parts.some(function (p) { return p.kind === 'color'; }) && !zonesRef().some(function (z) { return z && z._easyAuto === 'color'; })) {
            // Easy's START OVER clears the colour zones (keeps the token ones): for Built-for-you the
            // clean slate IS a fresh build — rows pointing at missing zones are what the owner saw as "clunky".
            if (buildZones('start over')) { toast('Started over — the parts were rebuilt from your paint'); flashAll(1400); }
        }
        if (!zonesRef().some(function (z) { return z && z._easyAuto; })) {
            // UNDO past the build (or Start Over) leaves the parts list pointing at nothing: offer the way back.
            x.els.rail.innerHTML = x.railHeader('YOUR CAR', 'The automatic parts were undone.', false) +
                '<div class="spb-easy-auto-actions"><button type="button" class="spb-easy-auto-act" id="spbEasyAutoRebuild" title="Read the paint again and build the parts">✨ Build my car again</button></div>' + x.saveBlockHtml(null);
            try { x.wireSaveBlock(); } catch (e) {}
            var rb0 = $('spbEasyAutoRebuild'); if (rb0) rb0.addEventListener('click', function () { if (buildZones('rebuild')) { renderRail(); flashAll(); } });
            layoutHosts(); return;
        }
        var parts = _analysis.parts, nc = parts.filter(function (p) { return p.kind === 'color'; }).length;
        var intro = lsGet('spb_easy_auto_intro_v1') === '1' ? '' :
            '<div class="spb-easy-auto-intro" id="spbEasyAutoIntro"><b>HOW THIS WORKS</b>' +
            '<ol><li><b>✦ Tell Shokker what you want</b> in the bar above the car — or <b>tap any part</b> of the car.</li><li>Pick a look or a finish. Keep your colours, or take the finish\'s own.</li><li>Hit <b>SAVE TO iRACING</b>. That\'s it.</li></ol>' +
            '<button type="button" id="spbEasyAutoIntroOk" title="Hide this card">Got it</button></div>';
        var html = intro + x.railHeader('YOUR CAR · BUILT FOR YOU',
            'We found ' + nc + ' colors and gave each part a finish. <b>Tap any part of the car</b> — or a row here — to change it.', false) +
            guidesNoticeHtml() +
            looksHtml() +
            '<div class="spb-easy-auto-parts" role="list">' + parts.map(function (q, i) { return q.mergedInto != null ? '' : rowHtml(q, i); }).join('') + '</div>' +
            '<button type="button" class="spb-easy-auto-pickbtn' + (_picking ? ' on' : '') + '" id="spbEasyAutoPick" title="Paint by numbers your way: click any colour on the car and it becomes its own part, with its own finish.">' + (_picking ? '✕ Cancel — click a colour on the car' : '🎯 Pick a color off the car') + '</button>' +
            (_pickParts.length ? '<div class="spb-easy-auto-sub">YOUR PICKS <small>they win their pixels</small></div><div class="spb-easy-auto-parts" role="list">' + _pickParts.map(function (p) { return rowHtml(p, p.idx); }).join('') + '</div>' : '') +
            (_layerParts.length ? '<div class="spb-easy-auto-sub">LAYER PARTS <small>from the layers on the right</small></div><div class="spb-easy-auto-parts" role="list">' + _layerParts.map(function (p) { return rowHtml(p, p.idx); }).join('') + '</div>' : '') +
            '<div id="spbEasyAutoTellMount"></div>' +
            '<div class="spb-easy-auto-actions">' +
            '  <button type="button" class="spb-easy-auto-act" id="spbEasyAutoRebuild" title="Look at the paint again and rebuild the colour parts. Your finish choices for matching parts are kept.">↻ Find the parts again</button>' +
            '  <button type="button" class="spb-easy-auto-act spb-easy-auto-hintbtn" id="spbEasyAutoHints" title="Every control has a hover hint. This also shows or hides the written hints under the sliders.">' + (hintsOn() ? 'Hide the helper hints' : 'Show the helper hints') + '</button>' +
            '</div>' +
            x.saveBlockHtml(null);
        x.els.rail.innerHTML = html;
        try { x.wireSaveBlock(); } catch (e) {}
        (function () {                                              // [SPB-EASY-SAVEGUARD 2026-09-22] guides on = baked into the TGA
            var svb = $('spbEasySave'), gl = guideLayersOn();
            if (!svb || !gl.length || !svb.parentElement) return;
            var warn = document.createElement('div');
            warn.className = 'spb-easy-auto-guides spb-easy-auto-guides-save'; warn.setAttribute('role', 'status');
            warn.innerHTML = '<b>⚠ Template guides are still on</b><span>' + esc(gl.map(function (l) { return l.name; }).join(', ')) + ' would be saved into your car.</span><button type="button" title="Hide the template guide layers, then save">Turn them off first</button>';
            svb.parentElement.insertBefore(warn, svb);
            warn.querySelector('button').addEventListener('click', function () { closePop(); guidesOff(); });
        })();
        x.els.rail.querySelectorAll('.spb-easy-auto-row').forEach(function (btn) {
            btn.addEventListener('click', function () { var r = btn.getBoundingClientRect(); openPop(Number(btn.getAttribute('data-part')), { x: r.right, y: r.top, fromRail: true }); });
            btn.addEventListener('mouseenter', function () { _hoverPart = Number(btn.getAttribute('data-part')); redrawAll(); });
            btn.addEventListener('mouseleave', function () { _hoverPart = -1; redrawAll(); });
        });
        var gOff = $('spbEasyAutoGuidesOff'); if (gOff) gOff.addEventListener('click', function () { closePop(); guidesOff(); });
        var pkb = $('spbEasyAutoPick'); if (pkb) pkb.addEventListener('click', function () { closePop(); setPicking(!_picking); });
        var ok = $('spbEasyAutoIntroOk'); if (ok) ok.addEventListener('click', function () { lsSet('spb_easy_auto_intro_v1', '1'); var c = $('spbEasyAutoIntro'); if (c) c.remove(); });
        x.els.rail.querySelectorAll('[data-look]').forEach(function (b) { b.addEventListener('click', function () { closePop(); applyLook(b.getAttribute('data-look')); }); });
        var rb = $('spbEasyAutoRebuild'), hb = $('spbEasyAutoHints');
        if (rb) rb.addEventListener('click', function () { closePop(); if (buildZones('rebuild')) { renderRail(); renderLayersPanel(); flashAll(); toast('Rebuilt from your paint — tap any part to change it'); } });
        if (hb) hb.addEventListener('click', function () { lsSet(LS_HINTS, hintsOn() ? '0' : '1'); document.body.classList.toggle('spb-easy-auto-nohints', !hintsOn()); renderRail(); if (_pop && !_pop.hidden) renderPop(); });
        document.body.classList.toggle('spb-easy-auto-nohints', !hintsOn());
        try { document.body.classList.remove('spb-easy-browse'); } catch (e) {}
        renderLayersPanel();
        layoutHosts(); redrawAll(); ensureLiveToggle(); syncLiveView();
        _railHooks.forEach(function (fn) { try { fn(x.els.rail, $('spbEasyAutoTellMount')); } catch (e) { try { console.warn('[EASY AUTO] rail hook', e); } catch (e2) {} } });
    }
    // ROUND 4 (owner 2026-09-19): leaveAuto() is gone. The old whole-car / by-colour stages had none of
    // this layout (rail on the right, no layers, tiny tiles, no reach, no ADJUST) and the owner walked
    // straight into them. Built-for-you IS Easy Mode; "every colour" and "whole car · shine only" cover
    // what those stages did.

    // -------------------------------------------------------- layers panel
    function ensureLayersPanel() {
        var x = I(); if (!x || !x.els || !x.els.root) return null;
        if (_layersPanel && _layersPanel.isConnected) return _layersPanel;
        var main = x.els.root.querySelector('.spb-easy-main'); if (!main) return null;
        _layersPanel = document.createElement('aside');
        _layersPanel.className = 'spb-easy-auto-layers'; _layersPanel.id = 'spbEasyAutoLayers'; _layersPanel.hidden = true;
        _layersPanel.setAttribute('aria-label', 'Layers of your paint');
        main.appendChild(_layersPanel);
        return _layersPanel;
    }
    function renderLayersPanel() {
        var panel = ensureLayersPanel(); if (!panel) return;
        var layers = psdLayers();
        if (!inAutoView()) { panel.hidden = true; return; }
        if (!layers.length) {
            // Flat TGA: no layers — offer the numbers / sponsor-text finder instead (opt-in, ~40 s).
            var x0 = X();
            if (!x0 || !x0.paintLoaded() || !window.spbEasyAutoParts) { panel.hidden = true; return; }
            panel.innerHTML = autoPartsPanelHtml() + (_layerParts.length ? '<div class="spb-easy-auto-sub">IN USE</div>' + _layerParts.map(function (p) { return rowHtml(p, p.idx); }).join('') : '');
            panel.hidden = false;
            var db = $('spbEasyAutoDetect'), da = $('spbEasyAutoDetectAgain');
            if (db) db.addEventListener('click', runAutoDetect);
            if (da) da.addEventListener('click', function () { _autoDet = { pk: null, running: false, result: null, error: null }; runAutoDetect(); });
            panel.querySelectorAll('[data-use]').forEach(function (b) { b.addEventListener('click', function () { useAutoPart(b.getAttribute('data-use')); }); });
            panel.querySelectorAll('.spb-easy-auto-row').forEach(function (btn) {
                btn.addEventListener('click', function () { openPop(Number(btn.getAttribute('data-part')), null); });
                btn.addEventListener('mouseenter', function () { _hoverPart = Number(btn.getAttribute('data-part')); redrawAll(); });
                btn.addEventListener('mouseleave', function () { _hoverPart = -1; redrawAll(); });
            });
            return;
        }
        // [SPB-EASY-TELL2 2026-09-30] layers you can SAY: each row has a ✦ that opens the TELL bar on "make the <layer> …",
        // shows what it wears now (finish thumb + name) and dims hidden layers. The row itself still opens the editor.
        var html = '<div class="spb-easy-auto-layers-head"><b>LAYERS</b><small>' + layers.length + ' layers. Tap one to style <i>just that layer</i>, or hit its <span class="spb-easy-auto-star">✦</span> to say what you want.</small></div><div class="spb-easy-auto-layer-list" role="list">';
        layers.forEach(function (l) {
            var part = null; for (var i = 0; i < _layerParts.length; i++) if (_layerParts[i].layerId === l.id) part = _layerParts[i];
            var z = part ? zoneFor(part.idx) : null;
            var st = z ? { blend: (z.baseStrength == null) ? 1 : Number(z.baseStrength) } : null;
            var sub = z ? (esc(finishNameOf(z)) + (st && st.blend < 0.995 ? ' · ' + Math.round(st.blend * 100) + '%' : '')) : 'tap to style this layer';
            var say = String(l.name).replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
            html += '<div class="spb-easy-auto-layer-row" role="listitem"><button type="button" class="spb-easy-auto-layer' + (part && part.idx === _popPart ? ' on' : '') + (l.visible === false ? ' off' : '') + (z ? ' styled' : '') + '" data-layer="' + esc(l.id) + '" title="' + (l.visible === false ? 'This layer is hidden in your paint. ' : '') + 'Click to pick a finish for only this layer.">' +
                '<span class="spb-easy-auto-layer-art"><img class="spb-easy-auto-layer-thumb" alt="" src="' + esc(layerThumb(l)) + '">' + (z ? finishThumbHtml(z) : '') + '</span>' +
                '<span class="spb-easy-auto-row-text"><b>' + esc(l.name) + '</b><small>' + sub + '</small></span>' +
                (z ? '<span class="spb-easy-auto-layer-badge">✓</span>' : '') + '</button>' +
                '<button type="button" class="spb-easy-auto-layer-tell" data-say="' + esc(say) + '" data-layer-say="' + esc(l.id) + '" title="Tell Shokker what you want for the ' + esc(l.name) + ' layer">✦</button></div>';
        });
        html += '</div>';
        panel.innerHTML = html; panel.hidden = false;
        panel.querySelectorAll('.spb-easy-auto-layer-tell').forEach(function (tb) {
            var lid = tb.getAttribute('data-layer-say'), lay2 = null; for (var q = 0; q < layers.length; q++) if (layers[q].id === lid) lay2 = layers[q];
            tb.addEventListener('click', function (ev) {
                ev.stopPropagation();
                try { if (window.spbEasyTell && window.spbEasyTell.prefill) window.spbEasyTell.prefill('make the ' + tb.getAttribute('data-say') + ' '); } catch (e) {}
            });
            tb.addEventListener('mouseenter', function () { var lm = lay2 ? layerMask(lay2) : null; _hoverMask = lm ? lm.mask : null; _hoverPart = -1; redrawAll(); });
            tb.addEventListener('mouseleave', function () { _hoverMask = null; redrawAll(); });
        });
        panel.querySelectorAll('.spb-easy-auto-layer').forEach(function (btn) {
            var id = btn.getAttribute('data-layer');
            var lay = null; for (var i = 0; i < layers.length; i++) if (layers[i].id === id) lay = layers[i];
            btn.addEventListener('click', function () {
                var r = btn.getBoundingClientRect();               // measure BEFORE re-rendering (a detached button reads 0,0)
                var idx = ensureLayerPart(lay); if (idx < 0) return;
                renderRail(); renderLayersPanel();
                openPop(idx, { x: r.left, y: r.top, fromLayers: true });
            });
            btn.addEventListener('mouseenter', function () { var lm = layerMask(lay); _hoverMask = lm ? lm.mask : null; _hoverPart = -1; redrawAll(); });
            btn.addEventListener('mouseleave', function () { _hoverMask = null; redrawAll(); });
        });
    }

    // ----------------------------------------------------------- the popover
    function ensurePop() {
        var x = I(), host = (x && x.els && x.els.root) || document.body;
        if (_pop) { if (_pop.parentElement !== host) host.appendChild(_pop); return _pop; }
        _pop = document.createElement('div');
        _pop.className = 'spb-easy-auto-pop'; _pop.id = 'spbEasyAutoPop'; _pop.hidden = true;
        _pop.setAttribute('role', 'dialog'); _pop.setAttribute('aria-label', 'Change this part of your car');
        host.appendChild(_pop);
        _pop.addEventListener('click', function (ev) { ev.stopPropagation(); });
        document.addEventListener('click', function (ev) {
            if (_pop.hidden || _pop.contains(ev.target)) return;
            if (ev.target && ev.target.closest && ev.target.closest('.spb-easy-auto-hilite, .spb-easy-auto-row, .spb-easy-auto-layer')) return;
            closePop();
        }, true);
        document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && _picking) { setPicking(false); ev.stopPropagation(); return; } if (ev.key === 'Escape' && !_pop.hidden) { closePop(); ev.stopPropagation(); } }, true);
        window.addEventListener('resize', function () { layoutHosts(); if (!_pop.hidden) placePop(); });
        return _pop;
    }
    function placePop() {
        if (!_pop || _pop.hidden) return;
        // Owner QA 2026-09-19: a floating popover covered the SOURCE pane. The part editor now docks
        // over the LEFT column (where Pro keeps its zone detail) — it can never sit on the car.
        var x = I(), rail = x && x.els && x.els.rail;
        if (rail && rail.isConnected && inAutoView()) {
            var rr = rail.getBoundingClientRect();
            if (rr.width > 200) {
                _pop.classList.add('docked');
                _pop.style.left = (rr.left + 4) + 'px'; _pop.style.top = (rr.top + 4) + 'px';
                _pop.style.width = (rr.width - 8) + 'px'; _pop.style.height = (rr.height - 8) + 'px'; _pop.style.maxHeight = 'none';
                return;
            }
        }
        _pop.classList.remove('docked'); _pop.style.width = ''; _pop.style.height = ''; _pop.style.maxHeight = '';
        var W = _pop.offsetWidth || 400, H = _pop.offsetHeight || 420;
        var x = (_popAnchor ? _popAnchor.x : 40) + 14, y = (_popAnchor ? _popAnchor.y : 40) - 20;
        if (_popAnchor && _popAnchor.fromLayers) { x = _popAnchor.x - W - 16; if (x < 8) x = _popAnchor.x + 8; }
        if (x + W > window.innerWidth - 8) x = Math.max(8, window.innerWidth - W - 8);
        if (y + H > window.innerHeight - 8) y = Math.max(8, window.innerHeight - H - 8);
        if (y < 8) y = 8;
        _pop.style.left = x + 'px'; _pop.style.top = y + 'px';
    }
    function closePop() {
        if (_pop) _pop.hidden = true;
        // A layer part opened and closed without a finish is nothing: drop it (no "no finish yet" leftovers).
        try {
            var lp = partById(_popPart), lz = zoneFor(_popPart), x0 = X();
            if (x0 && lp && (lp.kind === 'layer' || lp.kind === 'autopart' || lp.pick) && lz && !lz.base && !lz.finish) {
                var Z0 = x0.zones(), at0 = Z0.indexOf(lz); if (at0 >= 0) Z0.splice(at0, 1);
                rebuildLayerParts(); savePlan(); setTimeout(function () { renderRail(); renderLayersPanel(); }, 0);
            }
        } catch (e) {}
        _popPart = -1; _search = ''; _reachPreview = null; _cat = { mode: 'shelf', section: null };
        redrawAll();
        document.querySelectorAll('.spb-easy-auto-row.on, .spb-easy-auto-layer.on').forEach(function (b) { b.classList.remove('on'); });
    }
    function openPop(partIdx, anchor) {
        var p = partById(partIdx), z = zoneFor(partIdx);
        if (!p || !z) return;
        ensurePop();
        _popPart = partIdx; _lastPart = partIdx; _popAnchor = anchor || _popAnchor; _search = ''; _cat = { mode: 'shelf', section: null };
        if (p.kind === 'layer' && _scope !== 'part') _scope = 'part';
        _colorPick = (z._easyAutoColorChosen || z.baseColorMode) ? colorModeOf(z) : ((p.fade || p.multi) && !_colorPrefSet ? 'mine' : _colorPref);   // [SPB-EASY-PRO] Pro's default until the buyer chooses; a fade keeps its gradient unless told otherwise
        renderPop();
        _pop.hidden = false; placePop(); redrawAll();
        document.querySelectorAll('.spb-easy-auto-row, .spb-easy-auto-layer').forEach(function (b) { b.classList.remove('on'); });
        document.querySelectorAll('.spb-easy-auto-row[data-part="' + partIdx + '"]').forEach(function (b) { b.classList.add('on'); });
        if (p.kind === 'layer') document.querySelectorAll('.spb-easy-auto-layer[data-layer="' + p.layerId + '"]').forEach(function (b) { b.classList.add('on'); });
    }
    function headHtml(p, z) {
        var pct = Math.round((p.share || 0) * 100);
        var kindNote = p.kind === 'layer' ? 'this PSD layer' : (p.kind === 'remaining' ? 'everything no other part claimed' : (p.kind === 'color' ? (p.fade ? 'the whole fade and every shade in between' : 'all paint close to ' + esc(p.hex)) : p.name.toLowerCase()));
        return '<div class="spb-easy-auto-pop-head">' +
            '<button type="button" class="spb-easy-auto-backbtn" id="spbEasyAutoPopBack" title="Back to all parts (Esc)">‹ PARTS</button>' +
            '<span class="spb-easy-auto-sw big" style="' + swatchCss(p) + '"></span>' +
            '<div class="spb-easy-auto-pop-title"><b>' + esc(partLabel(p)) + '</b><small id="spbEasyAutoNow">now: <em>' + esc(finishNameOf(z)) + '</em> · ' + pct + '% of your car · ' + kindNote + '</small></div>' +
            '<button type="button" class="spb-easy-auto-x" id="spbEasyAutoClose" aria-label="Close" title="Close (Esc)">×</button>' +
            '</div>' +
            (p.pick ? '<div class="spb-easy-auto-pickhead"><span>A colour you picked off the car. It wins its pixels over the automatic parts.</span><button type="button" id="spbEasyAutoRemovePick" title="Remove this picked colour — its pixels go back to the automatic parts">Remove this pick</button></div>' : '') +
            (p.kind === 'color' ? reachHtml(p) : '') +
            mergeHtml(p, _popPart) +
            '<div class="spb-easy-auto-tabs" role="tablist">' +
            '<button type="button" role="tab" data-tab="finish" class="' + (_popTab === 'finish' ? 'on' : '') + '" title="Choose what this part is made of — chrome, candy, flake, matte… the same catalog as Pro.">FINISH</button>' +
            '<button type="button" role="tab" data-tab="adjust" class="' + (_popTab === 'adjust' ? 'on' : '') + '" title="Blend the finish with your paint, resize its pattern and shine map, shift its colour.">ADJUST <small>blend · size · color</small></button>' +
            '</div>';
    }
    function reachWord(v) { return v < 25 ? 'tight — just this shade' : v < 45 ? 'normal' : v < 60 ? 'wide — nearby shades too' : 'very wide'; }
    function reachHtml(p) {
        return '<label class="spb-easy-auto-reach" for="spbEasyAutoReach" title="How many shades of this colour count as this part. Drag it and watch the highlight on the car grow or shrink.">' +
            '<span class="spb-easy-auto-sl-head"><b>COLOR REACH</b><output id="spbEasyAutoReachOut">' + p.tol + ' · ' + reachWord(p.tol) + '</output></span>' +
            '<input type="range" id="spbEasyAutoReach" min="6" max="100" step="1" value="' + p.tol + '">' +
            '<small class="spb-easy-auto-hint">Slide right to catch more shades of this colour (shadows, gradients, anti-aliased edges). The orange highlight on the car shows exactly what it catches.</small></label>';
    }
    function colorModeOf(z) {
        if (!z || !z.baseColorMode || z.baseColorMode === 'source') return 'mine';
        if (z.baseColorMode === 'special') return 'finish';
        if (z.baseColorMode === 'solid') return (z._easyAutoOwnColor ? 'finish' : 'pick');
        return 'mine';
    }
    function proFinishColor(z, f) {
        // "The finish's color" = what the COLOR half of its tile shows (QA 2026-09-22, truck + ARCA renders):
        //  - plain material bases (colorSafe: Candy, Pearl, Metallic, Chrome, the Foundation cells, the EFX shelf) take the
        //    painter's colour; their tile is rendered in their swatch colour, so the render gets the swatch as a solid colour.
        //    Pro's special source ('mono:candy') renders these a washed-out neutral grey — not what the tile promises.
        //  - art bases and specials carry their own paint: Pro's special source (_spbDefaultBaseColorToFinish) shows it.
        if (!z || !f) return false;
        var sw = /^#[0-9a-fA-F]{6}$/.test(f.swatch || '') ? f.swatch.toLowerCase() : null, b = null;
        try { if (f.type === 'base' && typeof BASES !== 'undefined') b = BASES.find(function (q) { return q && q.id === f.id; }) || null; } catch (e) {}
        if (b && b.colorSafe && sw) {
            z.baseColorMode = 'solid'; z.baseColor = sw; z.baseColorSource = null; if (z.baseColorStrength == null) z.baseColorStrength = 1;
            z._easyAutoOwnColor = true; return true;
        }
        try {
            if (typeof _spbDefaultBaseColorToFinish === 'function') _spbDefaultBaseColorToFinish(z, f.id);
            else { z.baseColorMode = 'special'; z.baseColorSource = 'mono:' + f.id; z.baseColor = sw || z.baseColor || '#ffffff'; if (z.baseColorStrength == null) z.baseColorStrength = 1; }
        } catch (e) { return false; }
        z._easyAutoOwnColor = true;
        return z.baseColorMode === 'special';
    }
    function setColorOn(z, f, mode, hex) {
        z._easyAutoOwnColor = false;
        if (mode === 'finish' && f && proFinishColor(z, f)) return;
        if (mode === 'pick' && hex && /^#[0-9a-fA-F]{6}$/.test(hex)) { z.baseColorMode = 'solid'; z.baseColor = hex.toLowerCase(); z.baseColorSource = null; if (z.baseColorStrength == null) z.baseColorStrength = 1; return; }
        z.baseColorMode = null; z.baseColor = null; z.baseColorSource = null;      // absent = the car's own colour
    }
    function proPick(q, f) {
        // Pro's own pick (assignFinishToSelected): same zone fields + guardrails. lockBaseColor makes Pro's helper
        // skip ITS colour default — Easy's COLOR row applies the colour right after (Pro's default unless changed).
        var lock = q.lockBaseColor; q.lockBaseColor = true;
        try {
            if (f.type === 'monolithic' && typeof _spbApplyPickedMonolithicToZone === 'function') _spbApplyPickedMonolithicToZone(q, f.id);
            else if (f.type === 'base' && typeof _spbApplyPickedBaseToZone === 'function') _spbApplyPickedBaseToZone(q, f.id);
            else setFinishOn(q, f);
        } catch (e) { setFinishOn(q, f); }
        if (lock === undefined) delete q.lockBaseColor; else q.lockBaseColor = lock;
        delete q._easyPendingColorPreview; if (!q.pattern) q.pattern = 'none';
    }
    function colorHtml(p, z) {
        var mode = _colorPick, mineWord = p.kind === 'color' ? ('my ' + (partLabel(p) || 'color').replace(/\s\d+$/, '').toLowerCase()) : 'its colors';
        var pickHex = (z.baseColorMode === 'solid' && z.baseColor) ? z.baseColor : (p.hex || '#2255cc');
        return '<div class="spb-easy-auto-color" role="group" aria-label="Which colour the finish is in">' +
            '<span title="A finish is a colour AND a shine. Same as Pro: a finish brings its own colour (the COLOR half of every tile). Or keep the colour on your car now, or pick one.">COLOR</span>' +
            '<button type="button" data-color="finish" class="' + (mode === 'finish' ? 'on' : '') + '" title="Same as Pro: the finish brings its own colour — what you see in the COLOR half of the tile. Hue / saturation / brightness in ADJUST shift it.">Finish\'s color</button>' +
            '<button type="button" data-color="mine" class="' + (mode === 'mine' ? 'on' : '') + '" title="Keep the colour that is on your car now — only the shine and material change.">Keep ' + esc(mineWord.replace(/^my /, '')) + '</button>' +
            '<label class="spb-easy-auto-pickcol' + (mode === 'pick' ? ' on' : '') + '" title="Pick any colour for this part. The material and shine come from the finish."><input type="color" data-color="pick" value="' + esc(pickHex) + '"><span>Pick…</span></label>' +
            '</div>';
    }
    function scopeHtml(p) {
        if (p.kind === 'layer') return '';
        return '<div class="spb-easy-auto-scope" role="group" aria-label="Put the finish on">' +
            '<span title="What the finish you click next applies to.">PUT IT ON</span>' +
            '<button type="button" data-scope="part" class="' + (_scope === 'part' ? 'on' : '') + '" title="Only this part.">This part</button>' +
            '<button type="button" data-scope="every" class="' + (_scope === 'every' ? 'on' : '') + '" title="Every colour part on the car gets this finish, in the colour the COLOR row says (Keep my colours = every part keeps its own colour).">Every color</button>' +
            '<button type="button" data-scope="shine" class="' + (_scope === 'shine' ? 'on' : '') + '" title="The whole car keeps its paint exactly as painted and only takes this finish\'s shine (spec map). Great for \'my base paint in one material\'.">Shine only · whole car</button>' +
            '</div>';
    }
    function tileHtml(f, applied, big) {
        var x = I();
        big = true;                                                 // ROUND 4: every tile is Pro-size (owner: "tiny in the bottom")
        var thumb = x.splitThumbHtml(f, '').replace(/size=48/g, 'size=96').replace('<i>PAINT</i>', '<i>COLOR</i>');
        return '<span class="spb-easy-rowli" role="listitem">' +
            '<button type="button" class="spb-easy-finish' + (applied ? ' selected' : '') + (big ? ' spb-easy-auto-big' : '') + '" data-akey="' + esc(f.key) + '" title="' + esc(f.desc || f.name) + '">' +
            thumb +
            '<span class="spb-easy-finish-text"><span class="spb-easy-finish-name">' + esc(f.name) + (applied ? ' <em>on this part</em>' : '') + '</span>' +
            '<span class="spb-easy-finish-desc">' + esc(f.desc || '') + '</span></span>' +
            '</button></span>';
    }
    function searchKeys(text) {
        var x = I(), toks = String(text || '').toLowerCase().split(/\s+/).filter(Boolean), out = [];
        if (!toks.length) return null;
        var seenName = {};
        function scan(map, type) {
            if (typeof map === 'undefined' || !map) return;
            Object.keys(map).forEach(function (id) {
                if (out.length >= 80) return;
                try { if (type === 'base' && typeof spbResolveBaseId === 'function' && spbResolveBaseId(id) !== id) return; } catch (e) {}   // retired alias ids
                var m = map[id] || {}, hay = (String(m.name || id) + ' ' + String(m.desc || '') + ' ' + id).toLowerCase();
                if (!toks.every(function (t) { return hay.indexOf(t) !== -1; })) return;
                var nm = String(m.name || id).trim().toLowerCase(); if (seenName[nm]) return; seenName[nm] = true;   // one look, one tile
                out.push(x.finishKey(type, id));
            });
        }
        try { scan(typeof BASES_BY_ID !== 'undefined' ? BASES_BY_ID : null, 'base'); } catch (e) {}
        try { scan(typeof MONOLITHICS_BY_ID !== 'undefined' ? MONOLITHICS_BY_ID : null, 'monolithic'); } catch (e) {}
        return out;
    }
    function catalogTotal() {
        var n = 0;
        try { n += Object.keys(typeof BASES_BY_ID !== 'undefined' ? BASES_BY_ID : {}).length; } catch (e) {}
        try { n += Object.keys(typeof MONOLITHICS_BY_ID !== 'undefined' ? MONOLITHICS_BY_ID : {}).length; } catch (e) {}
        return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    function sections() { var x = I(); try { return x.buildCatalogSections ? x.buildCatalogSections() : []; } catch (e) { return []; } }
    function finishTabHtml(p, z) {
        return '<div class="spb-easy-auto-tab" data-tab="finish"' + (_popTab === 'finish' ? '' : ' hidden') + '>' +
            colorHtml(p, z) +
            scopeHtml(p) +
            '<div class="spb-easy-auto-next" id="spbEasyAutoNext" hidden><span></span><button type="button" title="Blend the finish with your paint, resize its pattern and shine map, or shift hue / saturation / brightness.">ADJUST ›</button></div>' +
            '<div class="spb-easy-auto-browse">' +
            '<button type="button" data-cat="shelf" class="' + (_cat.mode === 'shelf' ? 'on' : '') + '" title="Fifty finishes that look great on almost any car — the fastest way to a wow.">★ Top picks</button>' +
            '<button type="button" data-cat="cats" class="' + (_cat.mode !== 'shelf' ? 'on' : '') + '" title="The whole catalog by family, the same groups as the main app, with bigger previews.">☰ Categories</button>' +
            '<input type="search" class="spb-easy-auto-search" placeholder="Search ' + catalogTotal() + ' finishes… chrome, candy, carbon, flake" value="' + esc(_search) + '" aria-label="Search finishes" title="Type a word — chrome, candy, carbon, flake, matte, gold…">' +
            '</div>' +
            '<div class="spb-easy-auto-tiles"><div class="spb-easy-rowlist" role="list" id="spbEasyAutoTiles"></div></div>' +
            // [SPB-EASY-R6] owner: "Those HSB sliders are integral" — the three people reach for most, always in view.
            '<div class="spb-easy-auto-quick" title="Blend, size and hue — always here. Saturation, brightness and the shine map size are on ADJUST.">' +
            '<label class="spb-easy-auto-qrow" title="BASE STRENGTH — mix the new finish with your paint (100% = all finish)."><span>Blend</span><input type="range" data-proxy="spbEasyAutoBlend" aria-label="Blend"><output data-proxy-out="spbEasyAutoBlend"></output></label>' +
            '<label class="spb-easy-auto-qrow" title="BASE SCALE — smaller = finer detail, bigger = broader pattern."><span>Size</span><input type="range" data-proxy="spbEasyAutoSize" aria-label="Pattern size"><output data-proxy-out="spbEasyAutoSize"></output></label>' +
            '<label class="spb-easy-auto-qrow" title="HUE — spin the finish around the colour wheel."><span>Hue</span><input type="range" data-proxy="spbEasyAutoHue" aria-label="Hue"><output data-proxy-out="spbEasyAutoHue"></output></label>' +
            '<button type="button" class="spb-easy-auto-quickmore" title="Saturation, brightness, the shine map size and reset">More: saturation · brightness · shine size ›</button>' +
            '</div>' +
            '</div>';
    }
    function sliderRow(id, label, hint, min, max, step, val, fmt, title) {
        return '<label class="spb-easy-auto-slider" for="' + id + '" title="' + esc(title || hint) + '"><span class="spb-easy-auto-sl-head"><b>' + label + '</b><output id="' + id + 'Out">' + esc(fmt) + '</output></span>' +
            '<input type="range" id="' + id + '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + val + '">' +
            '<small class="spb-easy-auto-hint">' + hint + '</small></label>';
    }
    function scaleToPos(s) { return Math.round(100 * Math.log(Math.max(0.25, Math.min(4, s)) / 0.25) / Math.log(16)); }
    function posToScale(v) { return Math.round(0.25 * Math.pow(16, v / 100) * 100) / 100; }
    function fmtBlend(v) { return v >= 100 ? 'all new finish' : (v <= 0 ? 'just your paint' : v + '% new finish'); }
    function fmtScale(s) { return '×' + Number(s).toFixed(2); }
    function fmtSigned(v, unit) { return (v > 0 ? '+' : '') + v + (unit || ''); }
    function adjustTabHtml(z) {
        var blend = Math.round(((z.baseStrength == null) ? 1 : Number(z.baseStrength)) * 100);
        var bs = (z.baseScale == null) ? 1 : Number(z.baseScale), specOwn = z.specScale != null, ss = specOwn ? Number(z.specScale) : bs;
        var hue = Number(z.baseHueOffset || 0), sat = Number(z.baseSaturationAdjust || 0), bri = Number(z.baseBrightnessAdjust || 0);
        return '<div class="spb-easy-auto-tab" data-tab="adjust"' + (_popTab === 'adjust' ? '' : ' hidden') + '>' +
            '<div class="spb-easy-auto-group"><h4 title="Mix the new finish with the paint that is already there.">BLEND</h4>' +
            sliderRow('spbEasyAutoBlend', 'How much of the new finish', 'Slide left to mix the finish with your original paint. 100% = the finish takes over completely.', 0, 100, 1, blend, fmtBlend(blend), 'BASE STRENGTH — 100% is all finish, 0% is just your paint; anything between blends the two.') +
            '</div>' +
            '<div class="spb-easy-auto-group"><h4 title="How big the finish\'s pattern and shine map read on the car.">SIZE</h4>' +
            sliderRow('spbEasyAutoSize', 'Pattern size', 'Smaller = finer, busier detail. Bigger = broader flakes and shapes. The shine map follows unless you unlink it.', 0, 100, 1, scaleToPos(bs), fmtScale(bs), 'BASE SCALE — resizes the finish\'s pattern. ×1 is as authored.') +
            '<label class="spb-easy-auto-check" title="Linked: the spec (shine) map resizes with the pattern. Unlinked: set the shine map\'s size on its own."><input type="checkbox" id="spbEasyAutoSpecLink"' + (specOwn ? '' : ' checked') + '> Shine map follows the pattern size</label>' +
            '<div id="spbEasyAutoSpecWrap"' + (specOwn ? '' : ' hidden') + '>' +
            sliderRow('spbEasyAutoSpec', 'Shine map size', 'Only the spec (shine) map — the paint pattern keeps its own size.', 0, 100, 1, scaleToPos(ss), fmtScale(ss), 'SPEC SCALE — resizes only the shine map.') +
            '</div></div>' +
            '<div class="spb-easy-auto-group"><h4 title="Shift the finish\'s colour without changing its material.">COLOR</h4>' +
            sliderRow('spbEasyAutoHue', 'Hue', 'Spin the finish around the color wheel.', -180, 180, 1, hue, fmtSigned(hue, '°'), 'HUE — rotates the finish\'s colour; 0° is as authored.') +
            sliderRow('spbEasyAutoSat', 'Saturation', 'Left = calmer, right = punchier color.', -100, 100, 1, sat, fmtSigned(sat), 'SATURATION — how vivid the finish\'s colour is.') +
            sliderRow('spbEasyAutoBri', 'Brightness', 'Left = deeper, right = lighter.', -100, 200, 1, bri, fmtSigned(bri), 'BRIGHTNESS — darker or lighter finish colour.') +
            '</div>' +
            '<button type="button" class="spb-easy-auto-reset" id="spbEasyAutoReset" title="Put blend, size and colour back to how the finish was authored.">Reset this part\'s adjustments</button>' +
            '</div>';
    }
    function renderPop() {
        var x = I(), p = partById(_popPart), z = zoneFor(_popPart);
        if (!p || !z) { closePop(); return; }
        _pop.innerHTML = headHtml(p, z) + finishTabHtml(p, z) + adjustTabHtml(z);
        $('spbEasyAutoClose').addEventListener('click', closePop);
        var bk = $('spbEasyAutoPopBack'); if (bk) bk.addEventListener('click', closePop);
        var rmp = $('spbEasyAutoRemovePick'); if (rmp) rmp.addEventListener('click', function () { removePick(p.idx); });
        var mg = $('spbEasyAutoMerge'); if (mg) mg.addEventListener('change', function () { var j = Number(mg.value); if (mg.value !== '' && !isNaN(j)) mergeParts(_popPart, j); });
        _pop.querySelectorAll('[role="tab"]').forEach(function (t) {
            t.addEventListener('click', function () {
                _popTab = t.getAttribute('data-tab');
                _pop.querySelectorAll('[role="tab"]').forEach(function (b) { b.classList.toggle('on', b === t); });
                _pop.querySelectorAll('.spb-easy-auto-tab').forEach(function (s) { s.hidden = s.getAttribute('data-tab') !== _popTab; });
                placePop();
                if (_popTab === 'finish') { try { x.lazyThumbPassSoon(); } catch (e) {} loadThumbsFallback(); }
            });
        });
        var search = _pop.querySelector('.spb-easy-auto-search'), sTimer = null;
        search.addEventListener('input', function () { _search = search.value; if (sTimer) clearTimeout(sTimer); sTimer = setTimeout(renderTiles, 120); });
        _pop.querySelectorAll('[data-cat]').forEach(function (b) {
            b.addEventListener('click', function () { _cat = { mode: b.getAttribute('data-cat') === 'shelf' ? 'shelf' : 'cats', section: null }; _search = ''; search.value = ''; _pop.querySelectorAll('[data-cat]').forEach(function (o) { o.classList.toggle('on', o === b); }); renderTiles(); });
        });
        _pop.querySelectorAll('[data-scope]').forEach(function (b) {
            b.addEventListener('click', function () { _scope = b.getAttribute('data-scope'); _pop.querySelectorAll('[data-scope]').forEach(function (o) { o.classList.toggle('on', o === b); }); });
        });
        _pop.querySelectorAll('button[data-color]').forEach(function (b) {
            b.addEventListener('click', function () { applyColorMode(_popPart, b.getAttribute('data-color'), null); });
        });
        var pickEl = _pop.querySelector('input[data-color="pick"]');
        if (pickEl) {
            var pickUndone = false;                                  // [SPB-EASY-R7] one undo per gesture (pointer or keyboard)
            pickEl.addEventListener('input', function () { if (!pickUndone) { pickUndone = true; try { x.undoPush('Easy: colour on ' + ((zoneFor(_popPart) || {}).name || 'part')); } catch (e) {} } applyColorMode(_popPart, 'pick', pickEl.value, true); });
            pickEl.addEventListener('change', function () { if (!pickUndone) { try { x.undoPush('Easy: colour on ' + ((zoneFor(_popPart) || {}).name || 'part')); } catch (e) {} } pickUndone = false; applyColorMode(_popPart, 'pick', pickEl.value, true); try { x.refreshZonesUI(); } catch (e) {} savePlan(); refreshLists(); });
        }
        var nx = $('spbEasyAutoNext');
        if (nx) nx.querySelector('button').addEventListener('click', function () { var t = _pop.querySelector('[role="tab"][data-tab="adjust"]'); if (t) t.click(); });
        var reach = $('spbEasyAutoReach');
        if (reach) {
            reach.addEventListener('pointerdown', function () { try { x.undoPush('Easy: color reach on ' + ((zoneFor(_popPart) || {}).name || 'part')); } catch (e) {} });
            reach.addEventListener('input', function () {
                var v = Number(reach.value); $('spbEasyAutoReachOut').textContent = v + ' · ' + reachWord(v);
                _reachPreview = { part: _popPart, tol: v }; redrawAll();
            });
            reach.addEventListener('change', function () { applyReach(_popPart, Number(reach.value)); });
            reach.addEventListener('pointerup', function () { setTimeout(function () { if (_reachPreview) applyReach(_popPart, Number(reach.value)); }, 0); });
        }
        renderTiles();
        wireAdjust(z);
        wireQuick();
    }
    function applyColorMode(partIdx, mode, hex, silent) {
        var x = X(), p = partById(partIdx), z = zoneFor(partIdx); if (!x || !p || !z) return;
        var f = finishKeyOf(z) ? x.finishInfo(finishKeyOf(z)) : null;
        _colorPick = mode; z._easyAutoColorChosen = true; if (mode !== 'pick') { _colorPref = mode; _colorPrefSet = true; }
        if (!silent) { try { x.undoPush('Easy: colour on ' + (z.name || 'part')); } catch (e) {} }
        setColorOn(z, f, mode, hex);
        if (_pop && !_pop.hidden) {
            var m = colorModeOf(z);
            _pop.querySelectorAll('button[data-color]').forEach(function (o) { o.classList.toggle('on', o.getAttribute('data-color') === mode); });
            var pl = _pop.querySelector('.spb-easy-auto-pickcol'); if (pl) pl.classList.toggle('on', mode === 'pick');
        }
        if (silent) { kickSoon(); return; }
        x.refreshZonesUI(); x.kickPreview(); savePlan(); refreshLists();
        if (!f) toast('Pick a finish and it will land in ' + (mode === 'mine' ? 'your own colour' : (mode === 'finish' ? "the finish's own colour" : 'the colour you picked')));
    }
    function wireQuick() {
        if (!_pop) return;
        _pop.querySelectorAll('input[data-proxy]').forEach(function (q) {
            var id = q.getAttribute('data-proxy'), t = $(id), out = _pop.querySelector('output[data-proxy-out="' + id + '"]');
            if (!t) return;
            q.min = t.min; q.max = t.max; q.step = t.step; q.value = t.value;
            function mirror() { var o = $(id + 'Out'); if (out && o) out.textContent = o.textContent; }
            mirror();
            q.addEventListener('pointerdown', function () { try { t.dispatchEvent(new Event('pointerdown')); } catch (e) {} });
            q.addEventListener('input', function () { t.value = q.value; t.dispatchEvent(new Event('input')); mirror(); });
            t.addEventListener('input', function () { if (q.value !== t.value) q.value = t.value; mirror(); });
        });
        var more = _pop.querySelector('.spb-easy-auto-quickmore');
        if (more) more.addEventListener('click', function () { var tb = _pop.querySelector('[role="tab"][data-tab="adjust"]'); if (tb) tb.click(); });
    }
    function applyReach(partIdx, v) {
        var x = X(), p = partById(partIdx), z = zoneFor(partIdx);
        _reachPreview = null;
        if (!x || !p || !z || p.kind !== 'color') { redrawAll(); return; }
        setReach(p, v); selToZone(z, p);                            // [SPB-EASY-PBN] every stop of the part moves together
        recomputeOwner(); redrawAll(); refreshLists();
        kickSoon();
        var now = $('spbEasyAutoNow'); if (now) now.innerHTML = 'now: <em>' + esc(finishNameOf(z)) + '</em> · ' + Math.round((p.share || 0) * 100) + '% of your car · all paint close to ' + esc(p.hex);
    }
    function loadThumbsFallback() {
        setTimeout(function () { if (!_pop || _pop.hidden) return; _pop.querySelectorAll('img[data-src]:not([src])').forEach(function (img) { try { img.src = img.getAttribute('data-src'); } catch (e) {} }); }, 350);
    }
    function miniThumbs(keys) {
        var x = I(), html = '';
        keys.slice(0, 4).forEach(function (k) { var f = x.finishInfo(k); if (!f) return; var u = x.thumbUrl(f); html += '<img class="spb-easy-auto-mini" alt="" src="' + esc(u) + '">'; });
        return html;
    }
    function renderTiles() {
        var x = I(), host = $('spbEasyAutoTiles'); if (!host) return;
        var z = zoneFor(_popPart), cur = finishKeyOf(z), html = '';
        var found = searchKeys(_search);
        if (found) {
            found.forEach(function (k) { var f = x.finishInfo(k); if (f) html += tileHtml(f, k === cur, true); });
            host.innerHTML = html ? '<div class="spb-easy-auto-grid">' + html + '</div>' : '<div class="spb-easy-auto-none">No finish matches "' + esc(_search) + '". Try one word — chrome, candy, carbon, flake, matte.</div>';
        } else if (_cat.mode === 'shelf') {
            x.buildTopShelf().forEach(function (k) { var f = x.finishInfo(k); if (f) html += tileHtml(f, k === cur, true); });
            host.innerHTML = '<div class="spb-easy-auto-grid">' + html + '</div>';
        } else if (_cat.mode === 'cats') {
            sections().forEach(function (s, i) {
                html += '<button type="button" class="spb-easy-auto-catrow" data-section="' + i + '" title="Open ' + esc(s.title) + ' — ' + s.ids.length + ' finishes"><span class="spb-easy-auto-cat-thumbs">' + miniThumbs(s.ids) + '</span><span class="spb-easy-auto-row-text"><b>' + esc(s.title) + '</b><small>' + s.ids.length + ' finishes</small></span><span class="spb-easy-auto-row-go">›</span></button>';
            });
            host.innerHTML = html || '<div class="spb-easy-auto-none">No categories available.</div>';
            host.querySelectorAll('[data-section]').forEach(function (b) { b.addEventListener('click', function () { _cat = { mode: 'section', section: Number(b.getAttribute('data-section')) }; renderTiles(); }); });
        } else {
            var s = sections()[_cat.section];
            html += '<button type="button" class="spb-easy-auto-back" id="spbEasyAutoCatBack" title="Back to all categories">‹ All categories</button><div class="spb-easy-auto-cat-title">' + esc(s ? s.title : '') + ' <small>' + (s ? s.ids.length : 0) + '</small></div><div class="spb-easy-auto-grid">';
            (s ? s.ids : []).forEach(function (k) { var f = x.finishInfo(k); if (f) html += tileHtml(f, k === cur, true); });
            html += '</div>';
            host.innerHTML = html;
            var back = $('spbEasyAutoCatBack'); if (back) back.addEventListener('click', function () { _cat = { mode: 'cats', section: null }; renderTiles(); });
        }
        host.querySelectorAll('[data-akey]').forEach(function (b) { b.addEventListener('click', function () { applyFinish(_popPart, b.getAttribute('data-akey')); }); });
        try { x.armLazyThumbs(host.parentElement); x.lazyThumbPassSoon(); } catch (e) {}
        loadThumbsFallback();
        placePop();
    }
    function setFinishOn(z, f) {
        if (f.type === 'monolithic') { z.finish = f.id; z.base = null; } else { z.base = f.id; z.finish = null; }
        delete z._easyPendingColorPreview; z.pattern = 'none';
    }
    function applyFinish(partIdx, key) {
        var x = X(), p = partById(partIdx), z = zoneFor(partIdx), f = x && x.finishInfo(key);
        if (!x || !z || !f || !p) return false;
        var scope = p.kind === 'layer' ? 'part' : _scope, targets = [];
        if (scope === 'part') targets = [z];
        else targets = x.zones().filter(function (q) { return q && q._easyAuto && q._easyAuto !== 'layer'; });
        x.undoPush('Easy: ' + (scope === 'part' ? (z.name || 'part') : (scope === 'every' ? 'every color' : 'whole car shine')) + ' → ' + f.name);
        var pickHex = (z.baseColorMode === 'solid' && z.baseColor && !z._easyAutoOwnColor) ? z.baseColor : null;
        // [SPB-EASY-R7 2026-09-22] the COLOR row belongs to the open editor. TELL / looks / other API callers set the colour
        // first (recolor) and then apply: they keep each zone's own colour state (review H1: "in blue" became chrome's colour).
        var fromPop = !!(_pop && !_pop.hidden && _popPart === partIdx);
        targets.forEach(function (q) {
            var qMode = fromPop ? _colorPick : colorModeOf(q), qHex = fromPop ? pickHex : ((q.baseColorMode === 'solid' && q.baseColor && !q._easyAutoOwnColor) ? q.baseColor : null);
            proPick(q, f);                                          // [SPB-EASY-PRO] Pro's own pick path
            if (scope === 'shine') { q.baseStrength = 0; q.baseSpecStrength = 1; setColorOn(q, f, 'mine'); }   // paint untouched, only the finish's spec (the whole-car lever)
            else {
                if (q.baseStrength === 0) { q.baseStrength = 1; delete q.baseSpecStrength; }
                var cm = qMode;                                     // the open editor's COLOR row, or the zone's own state for API callers
                if (_applyColor === 'finish' || _applyColor === 'mine') cm = _applyColor;      // [SPB-EASY-TELL2] TELL names the colour explicitly
                else if (/^#[0-9a-fA-F]{6}$/.test(_applyColor || '')) { cm = 'pick'; qHex = _applyColor; }
                if (cm === 'pick' && !qHex) cm = 'finish';
                setColorOn(q, f, cm, qHex);
            }
        });
        try { if (typeof _sanitizeZonesInPlace === 'function') _sanitizeZonesInPlace(x.zones(), 'easy-auto finish'); } catch (e) {}
        x.refreshZonesUI(); x.kickPreview();
        var now = $('spbEasyAutoNow'); if (now) now.innerHTML = 'now: <em>' + esc(f.name) + '</em> · ' + Math.round((p.share || 0) * 100) + '% of your car';
        var host = $('spbEasyAutoTiles'); if (host) host.querySelectorAll('[data-akey]').forEach(function (b) { b.classList.toggle('selected', b.getAttribute('data-akey') === key); });
        if (p.pick || p.kind === 'layer' || p.kind === 'autopart') recomputeOwner();   // [SPB-EASY-R6] a finished pick / layer now wins its pixels
        if (scope === 'shine' || colorModeOf(z) === 'mine') flashShine('WHAT CHANGED: the shine — ' + f.name + ' is on and your colours stay. Back to the car in a moment…');
        var nx = $('spbEasyAutoNext'); if (nx && _pop && !_pop.hidden && _popPart === partIdx) { nx.hidden = false; nx.querySelector('span').innerHTML = '<b>' + esc(f.name) + '</b> is on. Blend it with your paint, resize the pattern and shine, or shift hue / saturation / brightness:'; }
        refreshLists(); savePlan();
        if (fromPop) syncAdjustInputs();                            // [SPB-EASY-R7] Pro's guardrail / shine scope can reset blend
        if (scope !== 'part') toast(f.name + ' → ' + (scope === 'every' ? 'every color part' : 'the whole car (shine only)'));
        return true;
    }
    function syncAdjustInputs() {
        if (!_pop || _pop.hidden) return;
        var z = zoneFor(_popPart); if (!z) return;
        function setv(id, v, txt) {
            var el = $(id); if (el) el.value = v; var o = $(id + 'Out'); if (o) o.textContent = txt;
            var q = _pop.querySelector('input[data-proxy="' + id + '"]'); if (q) q.value = v;
            var qo = _pop.querySelector('output[data-proxy-out="' + id + '"]'); if (qo) qo.textContent = txt;
        }
        var blend = Math.round(((z.baseStrength == null) ? 1 : Number(z.baseStrength)) * 100), bs = (z.baseScale == null) ? 1 : Number(z.baseScale);
        var hue = Number(z.baseHueOffset || 0), sat = Number(z.baseSaturationAdjust || 0), bri = Number(z.baseBrightnessAdjust || 0);
        setv('spbEasyAutoBlend', blend, fmtBlend(blend)); setv('spbEasyAutoSize', scaleToPos(bs), fmtScale(bs));
        setv('spbEasyAutoHue', hue, fmtSigned(hue, '°')); setv('spbEasyAutoSat', sat, fmtSigned(sat)); setv('spbEasyAutoBri', bri, fmtSigned(bri));
    }
    function refreshLists() {
        document.querySelectorAll('.spb-easy-auto-row').forEach(function (b) {
            var idx = Number(b.getAttribute('data-part')), p = partById(idx), z = zoneFor(idx), sm = b.querySelector('small');
            if (p && z && sm) sm.textContent = finishNameOf(z) + ' · ' + Math.round((p.share || 0) * 100) + '% of your car';
            var sw = b.querySelector('.spb-easy-auto-sw'); if (p && z && sw) sw.setAttribute('style', rowSwatchCss(p, z));   // [SPB-EASY-R7] dot + thumb follow the finish
            var fin = b.querySelector('.spb-easy-auto-fin'); if (z && fin) { var tmp = document.createElement('span'); tmp.innerHTML = finishThumbHtml(z); if (tmp.firstChild) fin.replaceWith(tmp.firstChild); }
            b.classList.toggle('on', idx === _popPart);
        });
        renderLayersPanel();
    }
    function kickSoon() {
        var x = X(); if (!x) return;
        if (_kickTimer) clearTimeout(_kickTimer);
        _kickTimer = setTimeout(function () { _kickTimer = null; try { x.refreshZonesUI(); } catch (e) {} x.kickPreview(); savePlan(); }, KICK_MS);
    }
    function wireAdjust(z0) {
        var x = I(), part = _popPart;
        // Resolve the zone LATE: Easy's UNDO/REDO and a rebuild replace zone objects, so a handler that
        // closed over the object captured at render time would write into a dead copy (review finding).
        function zz() { return zoneFor(part) || z0; }
        function out(id, txt) { var o = $(id + 'Out'); if (o) o.textContent = txt; }
        // One UNDO point per drag (not per pixel of movement): pushed on pointerdown.
        [['spbEasyAutoBlend', 'blend'], ['spbEasyAutoSize', 'size'], ['spbEasyAutoSpec', 'shine size'], ['spbEasyAutoHue', 'hue'], ['spbEasyAutoSat', 'saturation'], ['spbEasyAutoBri', 'brightness']].forEach(function (pair) {
            var el = $(pair[0]); if (!el) return;
            el.addEventListener('pointerdown', function () { try { if (x) x.undoPush('Easy: ' + pair[1] + ' on ' + (zz().name || 'part')); } catch (e) {} });
        });
        var blend = $('spbEasyAutoBlend');
        blend.addEventListener('input', function () { var z = zz(), v = Number(blend.value); out('spbEasyAutoBlend', fmtBlend(v)); z.baseStrength = (v >= 100) ? 1 : Math.round(v) / 100; if (v >= 100) delete z.baseSpecStrength; kickSoon(); });
        var size = $('spbEasyAutoSize'), link = $('spbEasyAutoSpecLink'), specWrap = $('spbEasyAutoSpecWrap'), spec = $('spbEasyAutoSpec');
        size.addEventListener('input', function () { var z = zz(), s = posToScale(Number(size.value)); out('spbEasyAutoSize', fmtScale(s)); z.baseScale = s; if (link.checked) { delete z.specScale; spec.value = size.value; out('spbEasyAutoSpec', fmtScale(s)); } kickSoon(); });
        link.addEventListener('change', function () { var z = zz(); specWrap.hidden = link.checked; if (link.checked) { delete z.specScale; spec.value = size.value; out('spbEasyAutoSpec', fmtScale(posToScale(Number(size.value)))); } else { z.specScale = posToScale(Number(spec.value)); } placePop(); kickSoon(); });
        spec.addEventListener('input', function () { var z = zz(), s = posToScale(Number(spec.value)); out('spbEasyAutoSpec', fmtScale(s)); z.specScale = s; kickSoon(); });
        [['spbEasyAutoHue', 'baseHueOffset', '°'], ['spbEasyAutoSat', 'baseSaturationAdjust', ''], ['spbEasyAutoBri', 'baseBrightnessAdjust', '']].forEach(function (row) {
            var el = $(row[0]);
            el.addEventListener('input', function () { var z = zz(), v = Math.round(Number(el.value)); out(row[0], fmtSigned(v, row[2])); if (v === 0) delete z[row[1]]; else z[row[1]] = v; kickSoon(); });
        });
        $('spbEasyAutoReset').addEventListener('click', function () {
            var z = zz();
            if (x) x.undoPush('Easy: reset adjustments on ' + (z.name || 'part'));
            z.baseStrength = 1; z.baseScale = 1; delete z.baseSpecStrength; delete z.specScale; delete z.baseHueOffset; delete z.baseSaturationAdjust; delete z.baseBrightnessAdjust;
            setColorOn(z, null, 'mine'); _colorPick = 'mine';
            _popTab = 'adjust'; renderPop(); placePop(); kickSoon();
        });
    }

    // ------------------------------------------------ back into Built-for-you
    var _backChip = null;
    function enterAuto() {
        var x = X(); if (!x) return;
        leftSet(null);
        closePop();
        var hasAuto = x.zones().some(function (z) { return z && z._easyAuto; });
        if (!hasAuto || !_analysis) { if (!buildZones('back to built-for-you')) { toast('Load your car first — then Built-for-you can read it'); return; } }
        x.state.view = 'auto'; bcOf(x).phase = 'options';
        x.renderRail(); layoutHosts(); flashAll(1400);
    }
    function syncBackChip() {
        var x = X();
        var show = !!(x && x.paintLoaded() && x.state.view !== 'auto' && x.state.view !== 'sculpt');
        if (!_backChip || !_backChip.isConnected) {
            var host = x && x.els && x.els.root ? x.els.root.querySelector('.spb-easy-history') : null;
            if (!host) return;
            _backChip = document.createElement('button');
            _backChip.type = 'button'; _backChip.className = 'spb-easy-histbtn spb-easy-auto-backchip'; _backChip.id = 'spbEasyAutoBack';
            _backChip.title = 'Back to Built-for-you: the parts we found on your paint, tap the car to change any of them.';
            _backChip.textContent = '✨ BUILT FOR YOU';
            _backChip.addEventListener('click', enterAuto);
            host.insertBefore(_backChip, host.firstChild);
        }
        _backChip.hidden = !show;
    }

    // ------------------------------------------------------------- the poll
    function untouchedEasySlot() { var x = I(); if (!x) return false; try { return !x.detectWholeApplied() && x.easyColorZones().length === 0; } catch (e) { return false; } }
    function announce() {
        var nc = _analysis ? _analysis.parts.filter(function (p) { return p.kind === 'color'; }).length : 0;
        toast('Your car is built — we found ' + nc + ' color' + (nc === 1 ? '' : 's') + '. Tap any part of the car to change it.');
    }
    function tick() {
        var x = X();
        if (!x) {
            if (_pop && !_pop.hidden) closePop();
            if (_layersPanel) _layersPanel.hidden = true;
            if (_specView) _specView.hidden = true;
            _builtFor = null; _analysis = null; _layerParts = []; _hoverMask = null;
            _freshTimers.forEach(clearTimeout); _freshTimers = [];   // no re-kicks after leaving Easy
            if (_liveTog) _liveTog.hidden = true;
            document.body.classList.remove('spb-easy-auto-view');
            layoutHosts(); return;
        }
        ensureHosts(); wireSpecStrip(); wireImageObservers(); wireToastAnchor();
        try { reanchorToast(); } catch (eT) {}                        // a toast raised BEFORE Easy opened (Pro's welcome tip) is still on screen at Pro's position
        if (inAutoView()) {
            ensureLiveToggle();
            // SUNLIGHT is the light that makes a finish swap visible at a glance (chrome measured +32
            // luminance vs +8 under GARAGE); the buyer's own pick is kept once they touch the selector.
            if (!_lightDefaulted && x.state && !lsGet('spb_easy_auto_light_v1') && x.state.light === 'studio') { x.state.light = 'sun'; _matCache = { key: null, canvas: null }; }
            _lightDefaulted = true;                                    // once per session, never on every tick
        }
        if (!x.paintLoaded()) { layoutHosts(); return; }
        var pk = paintKey(); if (!pk) { layoutHosts(); return; }
        if (pk !== _lastPk) {
            _lastPk = pk; _pkChangedAt = performance.now(); _matchCache = { key: null, ok: true };
            // Pro memoizes the uploaded paint PNG for 30 s keyed on window._spbLayerRev; inside Easy a
            // paint switch does not bump it, so every render in that window re-sent the PREVIOUS car
            // (measured: stale for ~40 s, then fresh). Bump it ourselves the moment the paint changes.
            try { window._spbLayerRev = (window._spbLayerRev | 0) + 1; window.__spbPreviewBodyMemo = null; } catch (e) {}
            _layerMaskCache = {}; _layerThumbCache = {};              // PSD layer ids are 'psd_<index>' — car B must not show car A's layers
        }
        if (pk !== _builtFor) {
            if (!appPreviewSettled()) {                                // let the app's own load-preview land before we build + render
                if (x.state.view === 'auto' && x.els && x.els.rail && !x.els.rail.querySelector('.spb-easy-auto-parts')) x.els.rail.innerHTML = x.railHeader('BUILDING YOUR CAR…', 'Reading your paint — one moment.', false);
                layoutHosts(); syncLiveView(); return;
            }
            var Z = x.zones();
            var hasAuto = Z.some(function (z) { return z && z._easyAuto; });
            var left = leftGet() === pk, builtBefore = lsGet(LS_BUILT) === pk;
            if (hasAuto && Z.some(function (z) { return z && z._easyAuto && z._easyAutoPaint === pk; })) {
                reanalyze();                                       // resumed: the zones survived, only the owner map is missing
                if (!left) { x.state.view = 'auto'; bcOf(x).phase = 'options'; x.renderRail(); }
            } else if (!left && (hasAuto || untouchedEasySlot() || !builtBefore)) {
                var hadOldPlan = !hasAuto && !untouchedEasySlot();
                if (buildZones('paint loaded')) {
                    x.state.view = 'auto'; bcOf(x).phase = 'options'; x.renderRail();
                    flashAll(1800);
                    if (hadOldPlan) setTimeout(function () { toast('Your earlier Easy plan was replaced by the automatic build — UNDO brings it back'); }, 2600);
                    announce();
                }
            } else { _builtFor = pk; }
        }
        layoutHosts(); syncLiveView(); syncBackChip();
        if (_pendingLayers && _builtFor === pk && psdLayers().length) restorePendingLayers(pk, false);
        if (_pendingAutoparts && _builtFor === pk) restorePendingAutoparts(pk);
        if (_layersPanel && _layersPanel.hidden && inAutoView() && (psdLayers().length || window.spbEasyAutoParts)) renderLayersPanel();
        // [SPB-EASY-R5] PSD layers finish loading AFTER the build (the ARCA panel kept saying "a flat paint has no
        // layers" with 9 paintable layers loaded): refresh the layers panel, layer parts and guides card on change.
        var lsig = psdLayers().length + ':' + guideLayersOn().length;
        if (_builtFor === pk && lsig !== _lastLayerSig) {
            _lastLayerSig = lsig; _layerMaskCache = {};
            rebuildLayerParts(); renderLayersPanel();
            if (inAutoView() && !(_pop && !_pop.hidden)) renderRail();
        }
    }
    var _lastLayerSig = null;
    function boot() {
        if (_pollTimer) return;
        leftSet(null);                                            // ROUND 4: the old stages are unreachable; never stay "left"
        _pollTimer = setInterval(function () { try { tick(); } catch (e) { try { console.warn('[EASY AUTO]', e); } catch (e2) {} } }, 600);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 1500); });
    else setTimeout(boot, 1500);

    // Public API for sibling Easy modules (e.g. js/spb-easy-tell.js). Stable shapes; no DOM assumptions.
    var _railHooks = [];
    function partsPublic() {
        var out = [];
        if (_analysis) _analysis.parts.forEach(function (p, idx) { if (p.mergedInto != null) return; var z = zoneFor(idx); out.push({ idx: idx, name: p.name, label: partLabel(p), kind: p.kind, tone: p.tone || null, fade: !!p.fade, hex: p.hex || null, share: p.share || 0, finish: finishNameOf(z), finishKey: finishKeyOf(z), tol: p.tol || null }); });
        _pickParts.forEach(function (p) { var z = zoneFor(p.idx); out.push({ idx: p.idx, name: p.name, label: p.label, kind: 'color', pick: true, tone: null, fade: false, hex: p.hex, share: p.share || 0, finish: finishNameOf(z), finishKey: finishKeyOf(z), tol: p.tol }); });
        _layerParts.forEach(function (p) { if (p.ghost || p.missing) return; var z = zoneFor(p.idx); out.push({ idx: p.idx, name: p.name, label: p.name, kind: p.kind || 'layer', hex: null, share: p.share || 0, finish: finishNameOf(z), finishKey: finishKeyOf(z), layerId: p.layerId }); });
        return out;
    }
    function recolorPart(idx, hexOrNull) {
        var x = X(), z = zoneFor(idx); if (!x || !z) return false;
        x.undoPush('Easy: ' + (z.name || 'part') + (hexOrNull ? ' → ' + hexOrNull : ' → its own color'));
        if (hexOrNull && /^#[0-9a-fA-F]{6}$/.test(hexOrNull)) { z.baseColorMode = 'solid'; z.baseColor = hexOrNull; z.baseColorSource = null; if (z.baseColorStrength == null) z.baseColorStrength = 1; }
        else { z.baseColorMode = null; z.baseColor = null; z.baseColorSource = null; }
        z._easyAutoOwnColor = false; z._easyAutoColorChosen = true;  // [SPB-EASY-R7] a colour the buyer asked for
        x.refreshZonesUI(); x.kickPreview(); savePlan(); refreshLists();
        return true;
    }
    function layerPartFor(layerId) {
        var layers = psdLayers(), lay = null;
        for (var i = 0; i < layers.length; i++) if (layers[i].id === layerId) lay = layers[i];
        if (!lay) return -1;
        var idx = ensureLayerPart(lay); renderRail(); renderLayersPanel(); return idx;
    }
    function resyncAuto() {
        // [SPB-EASY-R7 2026-09-22] after UNDO / REDO (Easy's _reconcileAfterHistory): zone objects were swapped for clones.
        var x = X(); if (!x || !_analysis) return;
        var pk = paintKey(), Z = x.zones();
        var foreign = Z.some(function (z) { return z && z._easyAuto && z._easyAutoPaint && z._easyAutoPaint !== pk; });
        var mine = Z.some(function (z) { return z && z._easyAuto && z._easyAutoPaint === pk; });
        if (foreign && !mine) {                                     // UNDO crossed a paint switch: never put car A's parts on car B
            if (buildZones('undo crossed a paint switch', { noUndo: true })) { renderRail(); renderLayersPanel(); toast('That UNDO step belonged to your previous paint — parts rebuilt for this one'); }
            // [SPB-EASY-R9] the rest of the undo stack is the previous car's history: drop it, or every further UNDO rebuilds again
            try { if (typeof zoneUndoStack !== 'undefined' && Array.isArray(zoneUndoStack)) zoneUndoStack.length = 0; } catch (e) {}
            return;
        }
        if (foreign) for (var i = Z.length - 1; i >= 0; i--) if (Z[i] && Z[i]._easyAuto && Z[i]._easyAutoPaint && Z[i]._easyAutoPaint !== pk) Z.splice(i, 1);
        if (!zonesMatchAnalysis()) {                                // [SPB-EASY-R8] zones from another build of this paint (e.g. before guides off)
            savePlan();                                             // finishes keyed by each zone's own colour
            if (buildZones('history restored another build', { noUndo: true })) { renderRail(); renderLayersPanel(); }
            return;
        }
        _analysis.parts.forEach(function (p, idx) { if (p.kind !== 'color') return; var zr = zoneReach(zoneFor(idx)); if (zr && zr !== p.tol) setReach(p, zr); });
        applyMergesFromZones();                                     // [SPB-EASY-MERGE] UNDO of a merge splits the parts again
        rebuildLayerParts();                                        // picks + layer parts + owner map
        if (_pop && !_pop.hidden) { if (zoneFor(_popPart) && partById(_popPart)) renderPop(); else closePop(); }
        redrawAll();
        savePlan();                                                 // [SPB-EASY-R8] the plan follows the history (a reload must not bring the undone state back)
    }
    function startOverAuto() {
        var x = X(); if (!x) return;
        closePop(); setPicking(false);
        var Z = x.zones();
        for (var i = Z.length - 1; i >= 0; i--) if (Z[i] && Z[i]._easyAuto) Z.splice(i, 1);
        _pendingLayers = null; _pendingAutoparts = null; _colorPref = 'finish'; _colorPrefSet = false;
        try { var plans = readPlans(), pk = paintKey(); if (pk && plans[pk]) { delete plans[pk]; lsSet(LS_PLAN, JSON.stringify(plans)); } } catch (e) {}
        if (buildZones('start over', { noUndo: true })) { rebuildLayerParts(); renderRail(); renderLayersPanel(); flashAll(1400); toast('Started over — fresh parts from your paint (UNDO brings the old ones back)'); }
    }
    window.spbEasyAuto = {
        parts: partsPublic,
        layers: function () { return psdLayers().map(function (l) { return { id: l.id, name: l.name, group: l.groupName || '', visible: l.visible !== false }; }); },
        layerPart: layerPartFor,
        startOver: startOverAuto,
        resync: resyncAuto,
        apply: function (idx, key, scope, opts) { var prev = _scope, prevC = _applyColor, ok = false; if (scope) _scope = scope; _applyColor = (opts && opts.color) || null; try { ok = applyFinish(idx, key); } finally { _scope = prev; _applyColor = prevC; } return ok; },
        recolor: recolorPart,
        blend: function (idx, strength) {                        // BASE STRENGTH on one part (0..1), one undo point
            var x = X(), z = zoneFor(idx); if (!x || !z) return false;
            var v = Math.max(0, Math.min(1, Number(strength)));
            x.undoPush('Easy: blend ' + Math.round(v * 100) + '% on ' + (z.name || 'part'));
            z.baseStrength = v; if (v >= 1) delete z.baseSpecStrength;
            x.refreshZonesUI(); x.kickPreview(); savePlan(); refreshLists();
            if (_pop && !_pop.hidden && _popPart === idx) renderPop();   // the editor may never have been opened
            return true;
        },
        // ---- [SPB-EASY-TELL2 2026-09-30] hooks for js/spb-easy-tell.js
        batch: function (label, fn) {
            var prev = _batch, b = _batch = { label: label || null, pushed: false, kick: false, ui: false };
            try { return fn(); }
            finally { _batch = prev; if (!prev) { var x = I(); if (x) { try { if (b.ui) x.refreshZonesUI(); } catch (e) {} try { if (b.kick) x.kickPreview(); } catch (e2) {} } } }
        },
        thumb: function (key) { var x = I(); try { var f = x && x.finishInfo(key); return f ? (x.thumbUrl(f) || '') : ''; } catch (e) { return ''; } },
        adjust: function (idx, o) {                              // blend / size / hue / sat / bri on one part; absolute (blend, scale, hue, sat, bri) or relative (scaleMul, dHue, dSat, dBri)
            var x = X(), z = zoneFor(idx); if (!x || !z || !o) return false;
            x.undoPush('Easy: adjust ' + (z.name || 'part'));
            function clampN(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
            if (o.blend != null) { var bv = clampN(Number(o.blend), 0, 1); z.baseStrength = bv; if (bv >= 1) delete z.baseSpecStrength; }
            if (o.scale != null || o.scaleMul != null) { var s0 = (z.baseScale == null) ? 1 : Number(z.baseScale), sv = o.scale != null ? Number(o.scale) : s0 * Number(o.scaleMul); sv = Math.round(clampN(sv, 0.25, 4) * 100) / 100; z.baseScale = sv; if (z.specScale == null) delete z.specScale; }
            var rows = [['hue', 'dHue', 'baseHueOffset', -180, 180], ['sat', 'dSat', 'baseSaturationAdjust', -100, 100], ['bri', 'dBri', 'baseBrightnessAdjust', -100, 200]];
            rows.forEach(function (r) {
                if (o[r[0]] == null && o[r[1]] == null) return;
                var cur = Number(z[r[2]] || 0), v = o[r[0]] != null ? Number(o[r[0]]) : cur + Number(o[r[1]]);
                v = Math.round(clampN(v, r[3], r[4])); if (v === 0) delete z[r[2]]; else z[r[2]] = v;
            });
            x.refreshZonesUI(); x.kickPreview(); savePlan(); refreshLists();
            if (_pop && !_pop.hidden && _popPart === idx) renderPop();
            return true;
        },
        partState: function (idx) {
            var z = zoneFor(idx); if (!z) return null;
            return { blend: (z.baseStrength == null) ? 1 : Number(z.baseStrength), scale: (z.baseScale == null) ? 1 : Number(z.baseScale), hue: Number(z.baseHueOffset || 0), sat: Number(z.baseSaturationAdjust || 0), bri: Number(z.baseBrightnessAdjust || 0),
                colorMode: colorModeOf(z), pickHex: (z.baseColorMode === 'solid' && z.baseColor && !z._easyAutoOwnColor) ? z.baseColor : null, finishKey: finishKeyOf(z), finish: finishNameOf(z) };
        },
        selected: function () { return (_pop && !_pop.hidden && _popPart != null && _popPart >= 0 && partById(_popPart)) ? _popPart : -1; },
        lastPart: function () { return (_lastPart >= 0 && partById(_lastPart)) ? _lastPart : -1; },
        hover: function (idx) { _hoverMask = null; _hoverPart = (idx == null ? -1 : idx); redrawAll(); },
        hoverLayer: function (layerId) {
            var layers = psdLayers(), lay = null; for (var i = 0; i < layers.length; i++) if (layers[i].id === layerId) lay = layers[i];
            var lm = lay ? layerMask(lay) : null; _hoverMask = lm ? lm.mask : null; _hoverPart = -1; redrawAll();
        },
        unhover: function () { _hoverMask = null; _hoverPart = -1; redrawAll(); },
        look: function (id) { applyLook(id); },
        // [SPB-AI 2026-09-30] the buyer's LIVE render as a small JPEG data URL (for the optional "look & refine"); null when there is nothing to see
        liveSnapshot: function (size) {
            try {
                var img = paintSourceImg(); if (!img) return null;
                var n = Math.max(256, Math.min(768, size || 512)), cv = document.createElement('canvas'); cv.width = cv.height = n;
                var cx = cv.getContext('2d'); cx.fillStyle = '#101018'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high';
                var w = img.naturalWidth || img.width, h = img.naturalHeight || img.height, k = Math.min(n / w, n / h);
                cx.drawImage(img, (n - w * k) / 2, (n - h * k) / 2, w * k, h * k);
                return cv.toDataURL('image/jpeg', 0.72);
            } catch (e) { return null; }
        },
        // resolves true when the live render has stopped repainting (or false after timeoutMs)
        whenSettled: function (timeoutMs) {
            return new Promise(function (resolve) {
                var t0 = Date.now(), quiet = 0, st = $('spbEasyStage');
                (function poll() {
                    var busy = !!(st && st.classList.contains('spb-easy-painting')) || (typeof previewIsStale === 'function' && previewIsStale());
                    quiet = busy ? 0 : quiet + 1;
                    if (quiet >= 3) return resolve(true);
                    if (Date.now() - t0 > (timeoutMs || 30000)) return resolve(false);
                    setTimeout(poll, 700);
                })();
            });
        },
        findNumbers: function () { if (typeof runAutoDetect === 'function' && window.spbEasyAutoParts) runAutoDetect(); },
        undo: function () { var x = I(); return (x && x.easyUndo) ? x.easyUndo() : false; },
        redo: function () { var x = I(); return (x && x.easyRedo) ? x.easyRedo() : false; },
        historyTop: function () { var x = I(); return (x && x.historyTop) ? x.historyTop() : null; },
        search: function (text) { var x = I(); var k = searchKeys(text); return k || (x ? x.buildTopShelf().slice() : []); },
        sections: sections,
        finishInfo: function (key) { var x = I(); return x ? x.finishInfo(key) : null; },
        onRail: function (fn) { if (typeof fn === 'function' && _railHooks.indexOf(fn) === -1) _railHooks.push(fn); },
        kick: function () { var x = X(); if (x) x.kickPreview(); },
        toast: toast,
        renderRail: renderRail,
        owns: owns,
        rebuild: function () { closePop(); if (buildZones('api')) { renderRail(); flashAll(); } },
        open: function (partIdx) { openPop(partIdx, null); },
        close: closePop,
        analysis: function () { return _analysis; },
        layerParts: function () { return _layerParts; },
        showSpec: function (ch) { _specPinned = ch || null; syncSpecView(); },
        _analyze: analyze
    };
})();
