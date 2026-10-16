/* More adjustment layers for the SPB layer stack (ticket TL-18, TOOLS-LAYERS lane, 2026-10-10): Curves, Color Balance, Black & White,
 * Photo Filter, Threshold, Gradient Map. Loaded after pc-adjust.js, which owns the model, the compositor hook, the WebGL path, the history
 * and the card; this file only registers the types.
 * Maths follow PhotoCraft (crates/compose/src/adjust.rs: curve_lut natural cubic spline, Color Balance tone weights, Black & White hue-part
 * weights, Photo Filter D50 matrix + Luminosity restore, Threshold on the 8-bit grid, Gradient Map) - (c) 2026 ArtCraft Team and the PhotoCraft
 * contributors, MIT OR Apache-2.0 (THIRD_PARTY_NOTICES.md). Modified: rewritten in JavaScript for Shokker Paint Booth (8-bit RGBA, WebGL branch ids,
 * immutable parameters, hand-made canvas editors for the curve and the gradient). Kill switch: window.SPB_TLAY_OFF = true (same as pc-adjust.js).
 */
(function () {
    'use strict';
    var A = window.SPBPcAdjust;
    if (!A || typeof A.registerType !== 'function' || A.__more) return;
    A.__more = 'pcm-2';
    var U = A.util, clamp = U.clamp, SRGB_DEC = U.SRGB_DEC;

    function hex2rgb(h) { var n = parseInt(String(h).slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    function rgb2hex(r, g, b) { return '#' + [r, g, b].map(function (v) { return ('0' + Math.round(clamp(v, 0, 255)).toString(16)).slice(-2); }).join(''); }
    function isHex(h) { return /^#[0-9a-f]{6}$/i.test(String(h)); }
    // generic per-pixel loop: fn(r, g, b, out) fills out[0..2] with 0..255 (floats), d = unpremultiplied RGBA bytes, sa = per-pixel strength bytes, k0 = constant factor
    function perPixel(d, n, sa, k0, fn) {
        var out = [0, 0, 0];
        for (var i = 0, o = 0; i < n; i++, o += 4) {
            if (d[o + 3] === 0) continue;
            var k = sa ? k0 * sa[i] / 255 : k0;
            if (k <= 0) continue;
            var R = d[o], G = d[o + 1], B = d[o + 2];
            fn(R, G, B, out);
            if (k >= 0.9999) { d[o] = out[0]; d[o + 1] = out[1]; d[o + 2] = out[2]; }
            else { d[o] = R + (out[0] - R) * k; d[o + 1] = G + (out[1] - G) * k; d[o + 2] = B + (out[2] - B) * k; }
        }
    }
    var BTN = U.BTN, el = U.el;
    function chip(label, on, extra) { return 'flex:0 0 auto;font-size:9px;line-height:1.2;padding:3px 8px;border-radius:4px;user-select:none;border:1px solid ' + (on ? '#ffd86b' : '#4a4a52') + ';background:' + (on ? '#3a3320' : '#26262d') + ';color:' + (on ? '#ffd86b' : '#d8d8d8') + ';' + (extra || ''); }
    // a bare canvas inside the card's grid lands in one 69 px column; a div around it gets the full row like every other card row
    function wrapCv(cv) { var d = el('div', 'min-width:0;'); d.appendChild(cv); return d; }
    // an <i>, not a button (the app's global button CSS overrides inline backgrounds with !important, which hid the colour swatches) and not a span
    // (".layer-row-details > div > span:first-child" forces 46 px on the first one)
    function mkBtn(text, css, attrs, fn) {
        var b = el('i', 'font-style:normal;display:inline-block;box-sizing:border-box;cursor:pointer;' + css, text, Object.assign({ role: 'button', tabindex: '0' }, attrs || {}));
        function go(ev) { ev.stopPropagation(); ev.preventDefault(); if (b.getAttribute('aria-disabled') === 'true') return; fn(ev); }
        b.addEventListener('click', go);
        b.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') go(ev); });
        return b;
    }

    // ================================================================== Histogram + Levels markers (TL-20)
    // The compositor hook (pc-adjust.js drawAdj) calls histSample(ctx, layer) with the picture BELOW the adjustment layer; for the selected Levels /
    // Curves layer it is sampled onto a 256 x 256 grid (at most every 350 ms), so the card can draw the tones the layer is working on, like Photoshop.
    var HIST = {}, histAt = 0, histRedraw = {}, histScratch = null, histAsked = 0;
    function selectedId() { try { return typeof _selectedLayerId !== 'undefined' ? _selectedLayerId : null; } catch (_e) { return null; } }
    function histSample(ctx, L) {
        if (window.SPB_TLAY_OFF === true || !L || !L.pcAdj) return;
        var ty = L.pcAdj.type;
        if (ty !== 'levels' && ty !== 'curves') return;
        if (L.id !== selectedId()) return;
        var now = performance.now();
        if (HIST[L.id] && now - histAt < 350) return;
        histAt = now;
        var cv = ctx.canvas; if (!cv || !cv.width || !cv.height) return;
        if (!histScratch) { histScratch = document.createElement('canvas'); histScratch.width = 256; histScratch.height = 256; }
        var g = histScratch.getContext('2d', { willReadFrequently: true }), d;
        g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'copy'; g.imageSmoothingEnabled = false;
        g.drawImage(cv, 0, 0, cv.width, cv.height, 0, 0, 256, 256);
        try { d = g.getImageData(0, 0, 256, 256).data; } catch (_e) { return; }
        var lum = new Uint32Array(256), r = new Uint32Array(256), gg = new Uint32Array(256), b = new Uint32Array(256), n = 0;
        for (var o = 0; o < d.length; o += 4) {
            if (d[o + 3] < 8) continue;
            n++; r[d[o]]++; gg[d[o + 1]]++; b[d[o + 2]]++;
            lum[Math.round(0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2])]++;
        }
        HIST[L.id] = { lum: lum, r: r, g: gg, b: b, n: n, t: now };
        var fn = histRedraw[L.id]; if (fn) requestAnimationFrame(fn);
    }
    function askHist() {   // a card opened before any composite saw this layer: ask for one composite so the histogram appears
        var t = performance.now(); if (t - histAsked < 1500) return; histAsked = t;
        setTimeout(function () { try { if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers(); } catch (_e) {} }, 30);
    }
    function drawHist(g, h, x0, y0, w, hgt, which, color, alpha) {
        if (!h || !h.n) return;
        var bins = h[which || 'lum'], mx = 1, i;
        for (i = 1; i < 255; i++) if (bins[i] > mx) mx = bins[i];   // the pure black / white spikes (empty canvas, flat fills) do not set the scale
        g.save(); g.globalAlpha = alpha; g.fillStyle = color;
        var bw = w / 256;
        for (i = 0; i < 256; i++) {
            if (!bins[i]) continue;
            var v = Math.min(1, Math.sqrt(bins[i] / mx));
            g.fillRect(x0 + i * bw, y0 + hgt - v * hgt, Math.max(bw, 1), v * hgt);
        }
        g.restore();
    }
    A.hist = function (id) { return HIST[id] || null; };
    A.histStats = function () { return { layers: Object.keys(HIST).length }; };
    if (typeof A.setHistHook === 'function') A.setHistHook(histSample);

    function levelsWidget(L, rows, c) {
        var ui = c.ui, W = 340, PAD = 12, HH = 96, TH = HH + 36, drag = null, endTimer = 0, T = A.TYPES.levels;
        var cv = el('canvas', 'display:block;width:100%;max-width:210px;aspect-ratio:' + W + '/' + TH + ';background:#101014;border:1px solid #333;border-radius:3px;cursor:ew-resize;touch-action:none;margin:0 0 3px;', null,
            { width: W, height: TH, 'data-pca-levels': L.id, tabindex: '0', role: 'slider', 'aria-label': 'Levels: histogram with black, gamma and white markers. Drag a marker, or press the arrow keys on the selected one.' });
        var info = el('div', 'font-size:8px;color:#999;margin:0 0 6px;min-height:11px;');
        if (!ui.lm) ui.lm = 'b';
        var g = cv.getContext('2d');
        function P() { return L.pcAdj.p; }
        function X(v) { return PAD + v / 255 * (W - 2 * PAD); }
        function midOf(p) {
            var bk = p.inBlack || 0, wh = p.inWhite == null ? 255 : p.inWhite;
            return bk + Math.pow(0.5, U.gammaOf(p.gamma || 0)) * (wh - bk);   // the input level that comes out at 50 %
        }
        function draw() {
            var p = P(), bk = p.inBlack || 0, wh = p.inWhite == null ? 255 : p.inWhite, md = midOf(p), i;
            g.clearRect(0, 0, W, TH); g.fillStyle = '#101014'; g.fillRect(0, 0, W, TH);
            g.strokeStyle = '#26262d'; g.lineWidth = 1;
            for (i = 0; i <= 4; i++) { g.beginPath(); g.moveTo(X(i * 255 / 4), 4); g.lineTo(X(i * 255 / 4), HH); g.stroke(); }
            var h = HIST[L.id];
            if (h && h.n) drawHist(g, h, X(0), 4, X(255) - X(0), HH - 4, 'lum', '#9aa0ad', 0.9);
            else { g.fillStyle = '#666'; g.font = '11px sans-serif'; g.textAlign = 'center'; g.fillText('histogram appears when the layers below are drawn', W / 2, HH / 2); g.textAlign = 'left'; }
            g.fillStyle = 'rgba(0,0,0,0.55)';   // tones that the black / white points clip
            g.fillRect(X(0), 4, X(bk) - X(0), HH - 4); g.fillRect(X(wh), 4, X(255) - X(wh), HH - 4);
            var gr = g.createLinearGradient(X(0), 0, X(255), 0); gr.addColorStop(0, '#000'); gr.addColorStop(1, '#fff');
            g.fillStyle = gr; g.fillRect(X(0), HH + 3, X(255) - X(0), 8);
            g.strokeStyle = '#444'; g.strokeRect(X(0) + 0.5, HH + 3.5, X(255) - X(0), 8);
            [['b', bk, '#000', '#fff'], ['m', md, '#808080', '#fff'], ['w', wh, '#fff', '#000']].forEach(function (m) {
                var x = X(m[1]), y = HH + 13, on = ui.lm === m[0];
                g.beginPath(); g.moveTo(x, y); g.lineTo(x - 8, y + 16); g.lineTo(x + 8, y + 16); g.closePath();
                g.fillStyle = m[2]; g.fill(); g.lineWidth = on ? 2.5 : 1.5; g.strokeStyle = on ? '#ffd86b' : '#aab'; g.stroke();
            });
            info.textContent = 'Black ' + Math.round(bk) + '   Gamma ' + U.gammaOf(p.gamma || 0).toFixed(2) + '   White ' + Math.round(wh);
        }
        function pos(ev) { var r = cv.getBoundingClientRect(); return (ev.clientX - r.left) / r.width * W; }
        function val(px) { return clamp(Math.round((px - PAD) / (W - 2 * PAD) * 255), 0, 255); }
        function nearest(px) {
            var p = P(), cand = [['b', X(p.inBlack || 0)], ['m', X(midOf(p))], ['w', X(p.inWhite == null ? 255 : p.inWhite)]], best = null, bd = 1e9;
            cand.forEach(function (m) { var dd = Math.abs(px - m[1]); if (dd < bd - 0.01 || (Math.abs(dd - bd) <= 0.01 && m[0] === ui.lm)) { bd = dd; best = m[0]; } });
            return best;
        }
        function syncSlider(k, v) {
            var q = null; T.params.forEach(function (x) { if (x.k === k) q = x; });
            var s = document.querySelector('input[data-pca-range="' + k + '"][data-pca-id="' + L.id + '"]'); if (s) s.value = v;
            var t = document.querySelector('[data-pca-val="' + k + '"]'); if (t && q && c.fmt) t.textContent = c.fmt(q, v);
        }
        function put(which, v, final) {
            var p = P(), bk = p.inBlack || 0, wh = p.inWhite == null ? 255 : p.inWhite, key, nv;
            if (which === 'b') { key = 'inBlack'; nv = clamp(v, 0, wh - 2); }
            else if (which === 'w') { key = 'inWhite'; nv = clamp(v, bk + 2, 255); }
            else {
                var u = clamp((v - bk) / Math.max(wh - bk, 1), 0.02, 0.98);
                key = 'gamma'; nv = clamp(Math.round(100 * Math.log(Math.log(u) / Math.log(0.5)) / Math.LN10), -100, 100);   // 0.5^gamma = u (the inverse of midOf)
            }
            c.set(L.id, key, nv, !!final); syncSlider(key, nv); draw();
        }
        cv.addEventListener('pointerdown', function (ev) {
            if (ev.button !== 0) return;
            ev.preventDefault(); ev.stopPropagation();
            try { cv.setPointerCapture(ev.pointerId); } catch (_e) {}
            try { cv.focus({ preventScroll: true }); } catch (_e) {}
            var px = pos(ev); drag = nearest(px); ui.lm = drag; put(drag, val(px), false);
        });
        cv.addEventListener('pointermove', function (ev) { if (drag) put(drag, val(pos(ev)), false); });
        function up() { if (!drag) return; drag = null; c.end(); }
        cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
        cv.addEventListener('keydown', function (ev) {
            var st = ev.shiftKey ? 10 : 1, dx = 0;
            if (ev.key === 'ArrowLeft') dx = -st; else if (ev.key === 'ArrowRight') dx = st;
            else if (ev.key === 'b' || ev.key === 'B') { ui.lm = 'b'; draw(); return; } else if (ev.key === 'm' || ev.key === 'M') { ui.lm = 'm'; draw(); return; } else if (ev.key === 'w' || ev.key === 'W') { ui.lm = 'w'; draw(); return; }
            else return;
            ev.preventDefault(); ev.stopPropagation();
            var p = P(), cur = ui.lm === 'b' ? (p.inBlack || 0) : ui.lm === 'w' ? (p.inWhite == null ? 255 : p.inWhite) : midOf(p);
            put(ui.lm, Math.round(cur) + dx, false);
            clearTimeout(endTimer); endTimer = setTimeout(function () { c.end(); }, 450);
        });
        histRedraw[L.id] = draw;
        if (!HIST[L.id]) askHist();
        draw();
        rows.push(wrapCv(cv)); rows.push(info);
    }
    if (A.TYPES.levels) {
        A.TYPES.levels.uiTop = levelsWidget;
        A.TYPES.levels.hint = 'Set the black point, white point and midtone gamma of everything below. The grey bars are the tones that sit below this layer; drag the triangles under them.';
    }

    // ================================================================== Curves
    var CH = [['m', 'RGB', '#e6e6e6'], ['r', 'R', '#ff6b6b'], ['g', 'G', '#5fe07a'], ['b', 'B', '#6aa8ff']];
    function cleanCurve(v) {
        if (!Array.isArray(v) || v.length < 2 || v.length > 19) return null;
        var pts = [], i;
        for (i = 0; i < v.length; i++) {
            var a = v[i]; if (!Array.isArray(a) || a.length < 2) return null;
            var x = Number(a[0]), y = Number(a[1]); if (!isFinite(x) || !isFinite(y)) return null;
            pts.push([clamp(Math.round(x), 0, 255), clamp(Math.round(y), 0, 255)]);
        }
        pts.sort(function (a, b) { return a[0] - b[0]; });
        var out = [pts[0]];
        for (i = 1; i < pts.length; i++) if (pts[i][0] !== out[out.length - 1][0]) out.push(pts[i]);
        return out.length < 2 ? null : out;
    }
    function curveTable(pts, N) {   // PhotoCraft curve_lut: natural cubic spline through the points, constant outside, clamped to 0..1
        var P = pts.map(function (p) { return [p[0] / 255, p[1] / 255]; }).sort(function (a, b) { return a[0] - b[0]; }), n, i, k, out = new Float64Array(N);
        var Q = [];
        for (i = 0; i < P.length; i++) if (!Q.length || Math.abs(P[i][0] - Q[Q.length - 1][0]) >= 1e-6) Q.push(P[i]);
        P = Q; n = P.length;
        if (n < 2) { for (k = 0; k < N; k++) out[k] = k / (N - 1); return out; }
        var m2 = new Float64Array(n);
        if (n > 2) {
            var c = new Float64Array(n), d = new Float64Array(n);
            for (i = 1; i < n - 1; i++) {
                var h0 = P[i][0] - P[i - 1][0], h1 = P[i + 1][0] - P[i][0], a = h0 / 6, b = (h0 + h1) / 3, cc = h1 / 6;
                var r = (P[i + 1][1] - P[i][1]) / h1 - (P[i][1] - P[i - 1][1]) / h0, den = b - a * c[i - 1];
                c[i] = cc / den; d[i] = (r - a * d[i - 1]) / den;
            }
            for (i = n - 2; i >= 1; i--) m2[i] = d[i] - c[i] * m2[i + 1];
        }
        for (k = 0; k < N; k++) {
            var xv = k / (N - 1);
            if (xv <= P[0][0]) { out[k] = clamp(P[0][1], 0, 1); continue; }
            if (xv >= P[n - 1][0]) { out[k] = clamp(P[n - 1][1], 0, 1); continue; }
            var s = n - 2;
            for (i = 0; i < n - 1; i++) if (xv <= P[i + 1][0]) { s = i; break; }
            var x0 = P[s][0], y0 = P[s][1], x1 = P[s + 1][0], y1 = P[s + 1][1], h = x1 - x0, aa = (x1 - xv) / h, bb = (xv - x0) / h;
            out[k] = clamp(aa * y0 + bb * y1 + ((aa * aa * aa - aa) * m2[s] + (bb * bb * bb - bb) * m2[s + 1]) * h * h / 6, 0, 1);
        }
        return out;
    }
    function interp(tab, v) { var N = tab.length, x = clamp(v, 0, 1) * (N - 1), i = Math.floor(x), j = Math.min(i + 1, N - 1), f = x - i; return tab[i] * (1 - f) + tab[j] * f; }
    var curveCache = { key: '', luts: null };
    function curveLuts(p) {
        var key = JSON.stringify([p.m, p.r, p.g, p.b]);
        if (curveCache.key === key) return curveCache.luts;
        var N = 256, M = curveTable(p.m, N);
        function row(pts) { var t = curveTable(pts, N), o = new Uint8Array(N); for (var i = 0; i < N; i++) o[i] = Math.round(clamp(interp(M, t[i]), 0, 1) * 255); return o; }
        curveCache = { key: key, luts: { r: row(p.r), g: row(p.g), b: row(p.b) } };
        return curveCache.luts;
    }
    function curveIdentity(pts) { for (var i = 0; i < pts.length; i++) if (Math.abs(pts[i][0] - pts[i][1]) > 0.5) return false; return true; }
    var LINE = [[0, 0], [255, 255]];
    function curveWidget(L, rows, c) {
        var ui = c.ui, ch = ui.ch || 'm', P = L.pcAdj.p, W = 340, PAD = 12, drag = -1, endTimer = 0;
        var tabs = el('div', 'display:flex;gap:3px;margin-bottom:4px;align-items:center;flex-wrap:wrap;');
        CH.forEach(function (x) {
            tabs.appendChild(mkBtn(x[1], chip(x[1], x[0] === ch, 'color:' + (x[0] === ch ? '#ffd86b' : x[2]) + ';'), { 'data-pca-ctab': x[0], title: x[0] === 'm' ? 'Curve of all three channels' : 'Curve of the ' + x[1] + ' channel only' }, function () { ui.ch = x[0]; ui.sel = null; c.rerender(); }));
        });
        tabs.appendChild(mkBtn('Reset', chip('Reset', false, 'margin-left:auto;'), { 'data-pca-creset': '1', title: 'Straighten this curve' }, function () { ui.sel = null; c.set(L.id, ch, LINE, true); }));
        rows.push(tabs);
        var cv = el('canvas', 'display:block;width:100%;max-width:210px;aspect-ratio:1/1;background:#101014;border:1px solid #333;border-radius:3px;cursor:crosshair;touch-action:none;margin:0 0 3px;', null,
            { width: W, height: W, 'data-pca-curve': L.id, tabindex: '0', role: 'img', 'aria-label': 'Curve editor: click to add a point, drag to move it, double-click a point to remove it, arrow keys nudge the selected point' });
        var info = el('div', 'font-size:8px;color:#999;margin:0 0 6px;min-height:11px;', 'Click the line to add a point, drag it, double-click to remove.');
        var pts = (P[ch] || LINE).map(function (a) { return [a[0], a[1]]; });
        var g = cv.getContext('2d');
        function X(v) { return PAD + v / 255 * (W - 2 * PAD); }
        function Y(v) { return W - PAD - v / 255 * (W - 2 * PAD); }
        function draw() {
            var i;
            g.clearRect(0, 0, W, W); g.fillStyle = '#101014'; g.fillRect(0, 0, W, W);
            var hcol = '#9aa0ad'; CH.forEach(function (x) { if (x[0] === ch) hcol = x[2]; });
            drawHist(g, HIST[L.id], X(0), Y(255), X(255) - X(0), Y(0) - Y(255), ch === 'm' ? 'lum' : ch, hcol, 0.28);   // [TL-20] the tones below, behind the curve
            g.lineWidth = 1; g.strokeStyle = '#26262d';
            for (i = 0; i <= 4; i++) { var t = i * 255 / 4; g.beginPath(); g.moveTo(X(t), Y(0)); g.lineTo(X(t), Y(255)); g.moveTo(X(0), Y(t)); g.lineTo(X(255), Y(t)); g.stroke(); }
            g.strokeStyle = '#3a3a44'; g.setLineDash([4, 4]); g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(255), Y(255)); g.stroke(); g.setLineDash([]);
            CH.forEach(function (x) {   // the other channels, faint
                if (x[0] === ch || !P[x[0]] || curveIdentity(P[x[0]])) return;
                var tb = curveTable(P[x[0]], 128); g.strokeStyle = x[2]; g.globalAlpha = 0.35; g.lineWidth = 1.5; g.beginPath();
                for (var k = 0; k < 128; k++) { var px = X(k / 127 * 255), py = Y(tb[k] * 255); if (k) g.lineTo(px, py); else g.moveTo(px, py); }
                g.stroke(); g.globalAlpha = 1;
            });
            var col = '#e6e6e6'; CH.forEach(function (x) { if (x[0] === ch) col = x[2]; });
            var tab = curveTable(pts, 256); g.strokeStyle = col; g.lineWidth = 2.5; g.beginPath();
            for (i = 0; i < 256; i++) { var qx = X(i), qy = Y(tab[i] * 255); if (i) g.lineTo(qx, qy); else g.moveTo(qx, qy); }
            g.stroke();
            pts.forEach(function (p, j) {
                var on = j === ui.sel; g.fillStyle = on ? '#fff' : '#101014'; g.strokeStyle = on ? '#ffd86b' : col; g.lineWidth = 2;
                g.beginPath(); g.rect(X(p[0]) - 6, Y(p[1]) - 6, 12, 12); g.fill(); g.stroke();
            });
            var sp = pts[ui.sel];
            info.textContent = sp ? 'Input ' + sp[0] + '   Output ' + sp[1] + '   (' + pts.length + ' points)' : 'Click the line to add a point, drag it, double-click to remove.';
        }
        function pos(ev) { var r = cv.getBoundingClientRect(); return [(ev.clientX - r.left) / r.width * W, (ev.clientY - r.top) / r.height * W]; }
        function val(px, py) { return [clamp(Math.round((px - PAD) / (W - 2 * PAD) * 255), 0, 255), clamp(Math.round((W - PAD - py) / (W - 2 * PAD) * 255), 0, 255)]; }
        function hitTest(px, py) { var hit = -1, best = 16; pts.forEach(function (p, i) { var dd = Math.hypot(X(p[0]) - px, Y(p[1]) - py); if (dd < best) { best = dd; hit = i; } }); return hit; }
        function commit(final) { c.set(L.id, ch, pts, !!final); }
        cv.addEventListener('pointerdown', function (ev) {
            if (ev.button !== 0) return;
            ev.preventDefault(); ev.stopPropagation();
            try { cv.setPointerCapture(ev.pointerId); } catch (_e) {}
            try { cv.focus({ preventScroll: true }); } catch (_e) {}
            var p = pos(ev), hit = hitTest(p[0], p[1]);
            if (hit < 0) {
                if (pts.length >= 19) return;
                var v = val(p[0], p[1]); pts.push(v); pts.sort(function (a, b) { return a[0] - b[0]; });
                for (var i = 1; i < pts.length; i++) if (pts[i][0] === pts[i - 1][0]) { pts.splice(pts.indexOf(v), 1); return; }   // same input value already has a point
                hit = pts.indexOf(v);
            }
            drag = hit; ui.sel = hit; draw(); commit(false);
        });
        cv.addEventListener('pointermove', function (ev) {
            if (drag < 0) return;
            var p = pos(ev), v = val(p[0], p[1]);
            var lo = drag > 0 ? pts[drag - 1][0] + 1 : 0, hi = drag < pts.length - 1 ? pts[drag + 1][0] - 1 : 255;
            pts[drag] = [clamp(v[0], lo, hi), v[1]]; draw(); commit(false);
        });
        function up() { if (drag < 0) return; drag = -1; commit(false); c.end(); }
        cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
        function removeAt(ev) {
            var p = pos(ev), hit = hitTest(p[0], p[1]);
            if (hit < 0 || pts.length <= 2) return;
            ev.preventDefault(); ev.stopPropagation(); pts.splice(hit, 1); ui.sel = null; draw(); commit(true);
        }
        cv.addEventListener('dblclick', removeAt); cv.addEventListener('contextmenu', removeAt);
        cv.addEventListener('keydown', function (ev) {
            var s = ui.sel; if (s == null || !pts[s]) return;
            var st = ev.shiftKey ? 10 : 1, dx = 0, dy = 0;
            if (ev.key === 'ArrowLeft') dx = -st; else if (ev.key === 'ArrowRight') dx = st; else if (ev.key === 'ArrowUp') dy = st; else if (ev.key === 'ArrowDown') dy = -st;
            else if ((ev.key === 'Delete' || ev.key === 'Backspace') && pts.length > 2) { ev.preventDefault(); ev.stopPropagation(); pts.splice(s, 1); ui.sel = null; draw(); commit(true); return; }
            else return;
            ev.preventDefault(); ev.stopPropagation();
            var lo = s > 0 ? pts[s - 1][0] + 1 : 0, hi = s < pts.length - 1 ? pts[s + 1][0] - 1 : 255;
            pts[s] = [clamp(pts[s][0] + dx, lo, hi), clamp(pts[s][1] + dy, 0, 255)]; draw(); commit(false);
            clearTimeout(endTimer); endTimer = setTimeout(function () { c.end(); }, 450);
        });
        histRedraw[L.id] = draw;
        if (!HIST[L.id]) askHist();
        draw();
        rows.push(wrapCv(cv)); rows.push(info);
    }
    A.registerType('curves', {
        label: 'Curves', glyph: 'C',
        hint: 'Bend the tones of everything below with a curve, like Photoshop. RGB moves all three channels, R / G / B tint the shadows or highlights.',
        params: [
            { k: 'm', label: 'RGB', type: 'json', hidden: true, def: LINE, clean: cleanCurve },
            { k: 'r', label: 'Red', type: 'json', hidden: true, def: LINE, clean: cleanCurve },
            { k: 'g', label: 'Green', type: 'json', hidden: true, def: LINE, clean: cleanCurve },
            { k: 'b', label: 'Blue', type: 'json', hidden: true, def: LINE, clean: cleanCurve }],
        identity: function (p) { return curveIdentity(p.m) && curveIdentity(p.r) && curveIdentity(p.g) && curveIdentity(p.b); },
        cpu: function (d, n, p, sa, k0) { U.lutLoop(d, n, curveLuts(p), sa, k0); },
        gpu: { id: 2, lut: function (p) { var l = curveLuts(p), o = new Uint8Array(256 * 4); for (var i = 0; i < 256; i++) { o[i * 4] = l.r[i]; o[i * 4 + 1] = l.g[i]; o[i * 4 + 2] = l.b[i]; o[i * 4 + 3] = 255; } return o; } },
        uiTop: curveWidget
    }, 'levels');

    // ================================================================== Color Balance
    var TONES = [['s', 'Shadows'], ['m', 'Midtones'], ['h', 'Highlights']];
    var CB = [];
    TONES.forEach(function (t) {
        [['r', 'Cyn↔Red'], ['g', 'Mag↔Grn'], ['b', 'Yel↔Blu']].forEach(function (x) {
            CB.push({ k: t[0] + '_' + x[0], label: x[1], min: -100, max: 100, step: 1, def: 0, show: function (p, ui) { return (ui.tone || 's') === t[0]; } });
        });
    });
    CB.push({ k: 'lum', label: 'Preserve', type: 'bool', def: true });
    function cbVals(p, t) { return [p[t + '_r'] || 0, p[t + '_g'] || 0, p[t + '_b'] || 0]; }
    A.registerType('colorBalance', {
        label: 'Color Balance', glyph: 'K',
        hint: 'Push the shadows, midtones or highlights toward cyan / red, magenta / green or yellow / blue. Preserve keeps the brightness steady.',
        params: CB,
        identity: function (p) { return TONES.every(function (t) { return cbVals(p, t[0]).every(function (v) { return !v; }); }); },
        cpu: function (d, n, p, sa, k0) {
            var S = cbVals(p, 's'), M = cbVals(p, 'm'), H = cbVals(p, 'h'), keep = p.lum !== false;
            perPixel(d, n, sa, k0, function (R, G, B, out) {
                var r = R / 255, g = G / 255, b = B / 255, l = 0.299 * r + 0.587 * g + 0.114 * b;
                var ws = clamp(1 - l * 2, 0, 1), wh = clamp(l * 2 - 1, 0, 1), wm = 1 - ws - wh;
                var o0 = clamp(r + (S[0] * ws + M[0] * wm + H[0] * wh) / 100 * 0.5, 0, 1), o1 = clamp(g + (S[1] * ws + M[1] * wm + H[1] * wh) / 100 * 0.5, 0, 1), o2 = clamp(b + (S[2] * ws + M[2] * wm + H[2] * wh) / 100 * 0.5, 0, 1);
                if (keep) { var l1 = Math.max(0.299 * o0 + 0.587 * o1 + 0.114 * o2, 1e-6), f = l / l1; o0 = clamp(o0 * f, 0, 1); o1 = clamp(o1 * f, 0, 1); o2 = clamp(o2 * f, 0, 1); }
                out[0] = o0 * 255; out[1] = o1 * 255; out[2] = o2 * 255;
            });
        },
        gpu: { id: 4, uniforms: function (p) { var S = cbVals(p, 's'), M = cbVals(p, 'm'), H = cbVals(p, 'h'); return { A: [S[0], S[1], S[2], 0], B: [M[0], M[1], M[2], 0], C: [H[0], H[1], H[2], 0], D: [p.lum !== false ? 1 : 0, 0, 0, 0] }; } },
        uiTop: function (L, rows, c) {
            var cur = c.ui.tone || 's', bar = el('div', 'display:flex;gap:3px;margin-bottom:5px;flex-wrap:wrap;');
            TONES.forEach(function (t) { bar.appendChild(mkBtn(t[1], chip(t[1], t[0] === cur), { 'data-pca-tone': t[0], title: 'Edit the ' + t[1].toLowerCase() }, function () { c.ui.tone = t[0]; c.rerender(); })); });
            rows.push(bar);
        }
    }, 'vibrance');

    // ================================================================== Black & White
    var BWK = [['reds', 'Reds', 40], ['yellows', 'Yellows', 60], ['greens', 'Greens', 40], ['cyans', 'Cyans', 60], ['blues', 'Blues', 20], ['magentas', 'Magentas', 80]];
    var BWP = BWK.map(function (x) { return { k: x[0], label: x[1], min: -200, max: 300, step: 1, def: x[2] }; });
    BWP.push({ k: 'tint', label: 'Tint', type: 'bool', def: false });
    BWP.push({ k: 'tintColor', label: 'Colour', type: 'color', def: '#e1d3b3', show: function (p) { return !!p.tint; } });
    function bwGray(r, g, b, w) {
        var mx = Math.max(r, g, b), mn = Math.min(r, g, b), md = r + g + b - mx - mn;
        var pi = (r >= g && r >= b) ? 0 : (g >= b ? 2 : 4), si = (b <= r && b <= g) ? 1 : (r <= g ? 3 : 5);
        return clamp(mn + (md - mn) * w[si] / 100 + (mx - md) * w[pi] / 100, 0, 1);
    }
    A.registerType('blackWhite', {
        label: 'Black & White', glyph: 'W',
        hint: 'Turn everything below to greys, and choose how light each colour comes out (a red filter lightens reds). Tint paints the grey in one colour.',
        params: BWP,
        identity: function () { return false; },
        cpu: function (d, n, p, sa, k0) {
            var w = BWK.map(function (x) { return p[x[0]] == null ? x[2] : p[x[0]]; }), tint = !!p.tint, t = hex2rgb(isHex(p.tintColor) ? p.tintColor : '#e1d3b3').map(function (v) { return v / 255; });
            perPixel(d, n, sa, k0, function (R, G, B, out) {
                var gr = bwGray(R / 255, G / 255, B / 255, w);
                if (tint) { out[0] = (clamp(gr * t[0] * 2, 0, 1) * 0.5 + gr * 0.5) * 255; out[1] = (clamp(gr * t[1] * 2, 0, 1) * 0.5 + gr * 0.5) * 255; out[2] = (clamp(gr * t[2] * 2, 0, 1) * 0.5 + gr * 0.5) * 255; }
                else out[0] = out[1] = out[2] = gr * 255;
            });
        },
        gpu: { id: 5, uniforms: function (p) { var w = BWK.map(function (x) { return p[x[0]] == null ? x[2] : p[x[0]]; }), t = hex2rgb(isHex(p.tintColor) ? p.tintColor : '#e1d3b3').map(function (v) { return v / 255; }); return { A: [w[0], w[1], w[2], w[3]], B: [w[4], w[5], p.tint ? 1 : 0, 0], C: [t[0], t[1], t[2], 0] }; } }
    }, 'colorBalance');

    // ================================================================== Photo Filter
    var PF = [['Warming 85', '#ec8a00'], ['Warming LBA', '#fa9600'], ['Warming 81', '#ebb113'], ['Cooling 80', '#006dff'], ['Cooling LBB', '#005dff'], ['Cooling 82', '#00b5ff'],
        ['Red', '#ea1a1a'], ['Orange', '#f38417'], ['Yellow', '#f9e31c'], ['Green', '#19c919'], ['Cyan', '#1dcbea'], ['Blue', '#1d35ea'], ['Violet', '#9b1dea'], ['Magenta', '#e318e3'],
        ['Sepia', '#ac7a33'], ['Deep Red', '#ff0000'], ['Deep Blue', '#0022cd'], ['Deep Emerald', '#008c00'], ['Deep Yellow', '#ffd500'], ['Underwater', '#00c2b1']];
    var X2 = [[0.4360747, 0.3850649, 0.1430804], [0.2225045, 0.7168786, 0.0606169], [0.0139322, 0.0971045, 0.7141733]], D50 = [0.96422, 1, 0.82521];
    function inv3(m) {
        var a = m[0][0], b = m[0][1], c = m[0][2], d = m[1][0], e = m[1][1], f = m[1][2], g = m[2][0], h = m[2][1], i = m[2][2];
        var A0 = e * i - f * h, B0 = -(d * i - f * g), C0 = d * h - e * g, det = a * A0 + b * B0 + c * C0;
        return [[A0 / det, -(b * i - c * h) / det, (b * f - c * e) / det], [B0 / det, (a * i - c * g) / det, -(a * f - c * d) / det], [C0 / det, -(a * h - b * g) / det, (a * e - b * d) / det]];
    }
    var X2I = inv3(X2);
    var pfCache = { key: '', M: null };
    function pfMatrix(color, density) {   // linear sRGB -> linear sRGB, Photo Filter colour mixed in by density (PhotoCraft photo_filter_matrix)
        var key = color + '|' + density; if (pfCache.key === key) return pfCache.M;
        var dn = clamp(density / 100, 0, 1), c = hex2rgb(color).map(function (v) { return SRGB_DEC[v]; }), xyz = [0, 1, 2].map(function (r) { return X2[r][0] * c[0] + X2[r][1] * c[1] + X2[r][2] * c[2]; });
        var s = [0, 1, 2].map(function (i) { return 1 - dn + dn * xyz[i] / D50[i]; });
        var M = [0, 1, 2].map(function (r) { return [0, 1, 2].map(function (cc) { return X2I[r][0] * s[0] * X2[0][cc] + X2I[r][1] * s[1] * X2[1][cc] + X2I[r][2] * s[2] * X2[2][cc]; }); });
        pfCache = { key: key, M: M }; return M;
    }
    function encU(l) { return l <= 0 ? 0 : (l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055); }
    function setLum(c, l) {   // PhotoCraft blend.rs set_lum + clip_color
        var d = l - (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]), r = c[0] + d, g = c[1] + d, b = c[2] + d;
        var L = 0.3 * r + 0.59 * g + 0.11 * b, n = Math.min(r, g, b), x = Math.max(r, g, b), o = [r, g, b], i, dd;
        if (n < 0) { dd = L - n; for (i = 0; i < 3; i++) o[i] = Math.abs(dd) < 1e-12 ? L : L + (o[i] - L) * L / dd; }
        if (x > 1) { dd = x - L; for (i = 0; i < 3; i++) o[i] = Math.abs(dd) < 1e-12 ? L : L + (o[i] - L) * (1 - L) / dd; }
        return o;
    }
    A.registerType('photoFilter', {
        label: 'Photo Filter', glyph: 'F',
        hint: 'Tint everything below with a colour filter, like a lens filter. Warming and Cooling are the classic photographer filters.',
        params: [
            { k: 'color', label: 'Colour', type: 'color', def: '#ec8a00' },
            { k: 'density', label: 'Density', min: 0, max: 100, step: 1, def: 25, unit: '%' },
            { k: 'lum', label: 'Preserve', type: 'bool', def: true }],
        identity: function (p) { return !p.density; },
        cpu: function (d, n, p, sa, k0) {
            var M = pfMatrix(isHex(p.color) ? p.color : '#ec8a00', p.density == null ? 25 : p.density), keep = p.lum !== false;
            perPixel(d, n, sa, k0, function (R, G, B, out) {
                var l0 = SRGB_DEC[R], l1 = SRGB_DEC[G], l2 = SRGB_DEC[B];
                var f = [encU(M[0][0] * l0 + M[0][1] * l1 + M[0][2] * l2), encU(M[1][0] * l0 + M[1][1] * l1 + M[1][2] * l2), encU(M[2][0] * l0 + M[2][1] * l1 + M[2][2] * l2)];
                if (keep) f = setLum(f, 0.3 * R / 255 + 0.59 * G / 255 + 0.11 * B / 255);
                out[0] = clamp(f[0], 0, 1) * 255; out[1] = clamp(f[1], 0, 1) * 255; out[2] = clamp(f[2], 0, 1) * 255;
            });
        },
        gpu: { id: 6, uniforms: function (p) { var M = pfMatrix(isHex(p.color) ? p.color : '#ec8a00', p.density == null ? 25 : p.density); return { D: [p.lum !== false ? 1 : 0, 0, 0, 0], M: [M[0][0], M[1][0], M[2][0], M[0][1], M[1][1], M[2][1], M[0][2], M[1][2], M[2][2]] }; } },
        uiTop: function (L, rows, c) {
            var cur = String(L.pcAdj.p.color).toLowerCase(), box = el('div', 'display:flex;flex-wrap:wrap;gap:3px;margin:0 0 6px;');
            PF.forEach(function (x) {
                var on = x[1] === cur;
                box.appendChild(mkBtn('', 'width:17px;height:17px;padding:0;border-radius:3px;cursor:pointer;background:' + x[1] + ';border:' + (on ? '2px solid #fff' : '1px solid #555') + ';', { 'data-pca-pf': x[1], title: x[0], 'aria-label': 'Photo filter ' + x[0] }, function () { c.set(L.id, 'color', x[1], true); }));
            });
            rows.push(box);
        }
    }, 'blackWhite');

    // ================================================================== Threshold
    A.registerType('threshold', {
        label: 'Threshold', glyph: 'T',
        hint: 'Pure black and white: everything lighter than the level turns white, everything darker black. Handy as a mask source.',
        params: [{ k: 'level', label: 'Level', min: 1, max: 255, step: 1, def: 128 }],
        identity: function () { return false; },
        cpu: function (d, n, p, sa, k0) {
            var lv = p.level == null ? 128 : p.level;
            perPixel(d, n, sa, k0, function (R, G, B, out) { out[0] = out[1] = out[2] = Math.round(0.299 * R + 0.587 * G + 0.114 * B) >= lv ? 255 : 0; });
        },
        gpu: { id: 3, lut: function (p) { var lv = p.level == null ? 128 : p.level, o = new Uint8Array(256 * 4); for (var i = 0; i < 256; i++) { var v = i >= lv ? 255 : 0; o[i * 4] = o[i * 4 + 1] = o[i * 4 + 2] = v; o[i * 4 + 3] = 255; } return o; } }
    }, 'posterize');

    // ================================================================== Gradient Map
    function cleanStops(v) {
        if (!Array.isArray(v) || v.length < 2 || v.length > 16) return null;
        var o = [], i;
        for (i = 0; i < v.length; i++) {
            var s = v[i]; if (!Array.isArray(s) || s.length < 2 || !isHex(s[1])) return null;
            var loc = Number(s[0]); if (!isFinite(loc)) return null;
            o.push([Math.round(clamp(loc, 0, 1) * 1000) / 1000, String(s[1]).toLowerCase()]);
        }
        o.sort(function (a, b) { return a[0] - b[0]; });
        return o;
    }
    function gradAt(st, t) {
        var n = st.length, i;
        if (t <= st[0][0]) return hex2rgb(st[0][1]);
        for (i = 0; i < n - 1; i++) if (t <= st[i + 1][0]) {
            var a = hex2rgb(st[i][1]), b = hex2rgb(st[i + 1][1]), k = st[i + 1][0] > st[i][0] ? (t - st[i][0]) / (st[i + 1][0] - st[i][0]) : 0;
            return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
        }
        return hex2rgb(st[n - 1][1]);
    }
    var GM = {
        'B&W': [[0, '#000000'], [1, '#ffffff']], 'Sepia': [[0, '#1c0f05'], [0.55, '#a0723f'], [1, '#f6e7c8']], 'Sunset': [[0, '#1b0b3a'], [0.4, '#b3205a'], [0.75, '#ff8a2b'], [1, '#ffe9a8']],
        'Ice': [[0, '#04122e'], [0.5, '#2a7fd6'], [1, '#e8fbff']], 'Heat': [[0, '#000000'], [0.33, '#b01010'], [0.66, '#ffa500'], [1, '#ffffe0']], 'Neon': [[0, '#10002b'], [0.5, '#ff2bd6'], [1, '#2bfff0']],
        'Gold': [[0, '#1a1203'], [0.5, '#c9951c'], [1, '#fff3c4']], 'Racing': [[0, '#0a0a12'], [1, '#ffd86b']]
    };
    function gradLut(p) {
        var st = cleanStops(p.stops) || GM['B&W'], N = 1024, o = new Uint8Array(N * 4);
        for (var i = 0; i < N; i++) { var t = i / (N - 1); if (p.reverse) t = 1 - t; var c = gradAt(st, t); o[i * 4] = Math.round(c[0]); o[i * 4 + 1] = Math.round(c[1]); o[i * 4 + 2] = Math.round(c[2]); o[i * 4 + 3] = 255; }
        return o;
    }
    function css(st) { return 'linear-gradient(90deg,' + st.map(function (s) { return s[1] + ' ' + Math.round(s[0] * 100) + '%'; }).join(',') + ')'; }
    function gradWidget(L, rows, c) {
        var ui = c.ui, W = 340, H = 44, PAD = 12, BAR = 26, drag = -1;
        var st = (cleanStops(L.pcAdj.p.stops) || GM['B&W']).map(function (s) { return [s[0], s[1]]; });
        if (ui.gs == null || !st[ui.gs]) ui.gs = 0;
        var pre = el('div', 'display:flex;flex-wrap:wrap;gap:3px;margin:0 0 5px;');
        Object.keys(GM).forEach(function (name) {
            pre.appendChild(mkBtn('', 'width:34px;height:16px;padding:0;border-radius:3px;cursor:pointer;border:1px solid #555;background:' + css(GM[name]) + ';', { 'data-pca-gpre': name, title: name + ' gradient', 'aria-label': 'Gradient preset ' + name }, function () { ui.gs = 0; c.set(L.id, 'stops', GM[name], true); }));
        });
        rows.push(pre);
        var cv = el('canvas', 'display:block;width:100%;max-width:210px;aspect-ratio:' + W + '/' + H + ';background:#101014;border:1px solid #333;border-radius:3px;cursor:pointer;touch-action:none;margin:0 0 3px;', null,
            { width: W, height: H, 'data-pca-grad': L.id, tabindex: '0', role: 'img', 'aria-label': 'Gradient editor: click the bar to add a colour stop, drag a stop to move it' });
        var g = cv.getContext('2d');
        var line = el('div', 'display:flex;align-items:center;gap:5px;margin:0 0 6px;');
        var pick = el('input', 'width:34px;height:18px;padding:0;border:1px solid #444;background:none;cursor:pointer;flex:0 0 34px;', null, { type: 'color', 'data-pca-gcolor': '1', 'aria-label': 'Selected stop colour', title: 'Colour of the selected stop' });
        var lab = el('span', 'font-size:8px;color:#999;flex:1 1 0%;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;', '');
        var rm = mkBtn('Remove', chip('Remove', false), { 'data-pca-gremove': '1', title: 'Remove the selected stop' }, function () { if (st.length > 2) { st.splice(ui.gs, 1); ui.gs = Math.max(0, ui.gs - 1); c.set(L.id, 'stops', st, true); } });
        line.appendChild(pick); line.appendChild(lab); line.appendChild(rm);
        function X(loc) { return PAD + loc * (W - 2 * PAD); }
        function draw() {
            g.clearRect(0, 0, W, H); g.fillStyle = '#101014'; g.fillRect(0, 0, W, H);
            var gr = g.createLinearGradient(X(0), 0, X(1), 0), rev = !!L.pcAdj.p.reverse;
            var show = st.map(function (s) { return rev ? [1 - s[0], s[1]] : s; }).sort(function (a, b) { return a[0] - b[0]; });
            show.forEach(function (s) { gr.addColorStop(clamp(s[0], 0, 1), s[1]); });
            g.fillStyle = gr; g.fillRect(PAD, 3, W - 2 * PAD, BAR - 3); g.strokeStyle = '#444'; g.lineWidth = 1; g.strokeRect(PAD + 0.5, 3.5, W - 2 * PAD - 1, BAR - 4);
            st.forEach(function (s, i) {
                var x = X(rev ? 1 - s[0] : s[0]), on = i === ui.gs;
                g.beginPath(); g.moveTo(x, BAR - 1); g.lineTo(x - 8, H - 3); g.lineTo(x + 8, H - 3); g.closePath();
                g.fillStyle = s[1]; g.fill(); g.lineWidth = on ? 3 : 1.5; g.strokeStyle = on ? '#ffd86b' : '#cfcfcf'; g.stroke();
            });
            var cur = st[ui.gs]; if (cur) { pick.value = cur[1]; lab.textContent = 'Stop ' + (ui.gs + 1) + ' of ' + st.length + ' at ' + Math.round(cur[0] * 100) + '%'; }
            rm.setAttribute('aria-disabled', st.length <= 2 ? 'true' : 'false'); rm.style.opacity = st.length <= 2 ? '0.4' : '1';
        }
        function pos(ev) { var r = cv.getBoundingClientRect(); return [(ev.clientX - r.left) / r.width * W, (ev.clientY - r.top) / r.height * H]; }
        function locOf(px) { var l = clamp((px - PAD) / (W - 2 * PAD), 0, 1); return L.pcAdj.p.reverse ? 1 - l : l; }
        function commit(final) { c.set(L.id, 'stops', st, !!final); }
        cv.addEventListener('pointerdown', function (ev) {
            if (ev.button !== 0) return;
            ev.preventDefault(); ev.stopPropagation();
            try { cv.setPointerCapture(ev.pointerId); } catch (_e) {}
            try { cv.focus({ preventScroll: true }); } catch (_e) {}
            var p = pos(ev), rev = !!L.pcAdj.p.reverse, hit = -1, best = 18;
            st.forEach(function (s, i) { var dd = Math.abs(X(rev ? 1 - s[0] : s[0]) - p[0]); if (dd < best) { best = dd; hit = i; } });
            if (hit < 0 || p[1] < BAR - 6) {
                if (hit < 0 || p[1] < BAR - 6) {
                    if (st.length >= 16) return;
                    var loc = Math.round(locOf(p[0]) * 1000) / 1000, col = gradAt(cleanStops(st), loc);
                    st.push([loc, rgb2hex(col[0], col[1], col[2])]); var ns = st[st.length - 1]; st.sort(function (a, b) { return a[0] - b[0]; }); hit = st.indexOf(ns);
                }
            }
            drag = hit; ui.gs = hit; draw(); commit(false);
        });
        cv.addEventListener('pointermove', function (ev) {
            if (drag < 0) return;
            var p = pos(ev), cur = st[drag], loc = Math.round(locOf(p[0]) * 1000) / 1000;
            cur[0] = loc; st.sort(function (a, b) { return a[0] - b[0]; }); drag = st.indexOf(cur); ui.gs = drag; draw(); commit(false);
        });
        function up() { if (drag < 0) return; drag = -1; commit(false); c.end(); }
        cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
        cv.addEventListener('keydown', function (ev) {
            if ((ev.key === 'Delete' || ev.key === 'Backspace') && st.length > 2) { ev.preventDefault(); ev.stopPropagation(); st.splice(ui.gs, 1); ui.gs = Math.max(0, ui.gs - 1); c.set(L.id, 'stops', st, true); }
        });
        pick.addEventListener('input', function (ev) { ev.stopPropagation(); if (st[ui.gs]) { st[ui.gs][1] = pick.value; draw(); commit(false); } }, true);
        pick.addEventListener('change', function (ev) { ev.stopPropagation(); commit(false); c.end(); }, true);
        draw();
        rows.push(wrapCv(cv)); rows.push(line);
    }
    A.registerType('gradientMap', {
        label: 'Gradient Map', glyph: 'G',
        hint: 'Recolour everything below by brightness: the darkest tones take the first stop, the lightest the last. Click the bar to add colours.',
        params: [
            { k: 'stops', label: 'Stops', type: 'json', hidden: true, def: GM['B&W'], clean: cleanStops },
            { k: 'reverse', label: 'Reverse', type: 'bool', def: false }],
        identity: function () { return false; },
        cpu: function (d, n, p, sa, k0) {
            var st = cleanStops(p.stops) || GM['B&W'], rev = !!p.reverse;
            perPixel(d, n, sa, k0, function (R, G, B, out) { var t = (0.299 * R + 0.587 * G + 0.114 * B) / 255; if (rev) t = 1 - t; var c = gradAt(st, t); out[0] = c[0]; out[1] = c[1]; out[2] = c[2]; });
        },
        gpu: { id: 3, lut: gradLut },
        uiTop: gradWidget
    }, 'threshold');

    A.cleanCurve = cleanCurve; A.cleanStops = cleanStops; A.curveTable = curveTable; A.gradAt = gradAt; A.pfMatrix = pfMatrix;
})();
