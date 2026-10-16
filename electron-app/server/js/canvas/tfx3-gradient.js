/* [SPB-TFX3 2026-10-10 PORT-2 Gradient colour stops + live preview, lane TOOLS-FIX-3]
 * Port of PhotoCraft crates/compose/src/gradient_fill.rs (colour ramp: stops + per-stop opacity + midpoints, dither) and
 * crates/engine/src/presets/gradients.rs (preset library, "Foreground to Background / Transparent" style linked stops) to the SPB Gradient tool.
 *
 * BEFORE (measured, fix3/grad_before.json): the Gradient tool could only blend the foreground colour into the background colour (two colours,
 * one straight ramp). window.gradientPresets / saveCustomGradient were a stub with no editor and nothing read them. Nothing showed the result
 * until you let go of the mouse (a guide line only), so a 3-colour fade or a chrome sweep on a hood was impossible and every try was a blind
 * drag + undo.
 *
 * AFTER: a "Colours" button in the Gradient options bar opens a gradient editor: preset chips, a colour bar with draggable colour stops
 * (click the bar to add a stop, drag to move, colour + position + opacity + midpoint per stop, stops can be linked to the current Foreground /
 * Background colour), Reverse, Save as preset, Reset. While you drag, the real gradient is previewed live over the selection / layer; letting go
 * applies exactly that ramp (Linear, Radial, Angular, Diamond, Reflected, Conical, Spiral all use it), clipped to the active selection as before,
 * with PhotoCraft's dither noise so long fades do not band. Default stays Foreground -> Background through the old code path (zero change until
 * a preset / stop is chosen). Applies to LAYER gradients only (zone gradients fade a mask, they have no colours).
 *
 * Kill switch: window.SPB_TFX3_OFF = true (or localStorage SPB_TFX3_OFF='1') -> button hidden, no preview, old two-colour gradient byte for byte.
 */
(function (root, factory) {
    var api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;       // node tests import the pure ramp math
    if (root && root.document) root.SPBTfx3Gradient = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';
    var isBrowser = !!(root && root.document);
    if (isBrowser) { try { if (root.SPB_TFX3_OFF !== true && root.localStorage.getItem('SPB_TFX3_OFF') === '1') root.SPB_TFX3_OFF = true; } catch (_e) { } }
    var api = {};
    function off() { return !!(root && root.SPB_TFX3_OFF === true); }
    var N = 2048;                                                                   // ramp lookup resolution

    // ------------------------------------------------------------------ pure ramp math (port of gradient_fill.rs)
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
    // where a segment position u lands once its midpoint is m (0.5 = unchanged): the colour is half-way at m, linear on either side
    function midpointRemap(u, m) {
        m = clamp(m == null ? 0.5 : m, 0.05, 0.95);
        if (Math.abs(m - 0.5) < 1e-6) return u;
        return u <= m ? 0.5 * u / m : 0.5 + 0.5 * (u - m) / (1 - m);
    }
    // stops: [{p, rgba:[r,g,b,a(0..1)], m}] sorted by p; m = midpoint of the segment that starts at this stop
    function sampleStops(stops, t) {
        var n = stops.length;
        if (!n) return [0, 0, 0, 0];
        if (t <= stops[0].p) return stops[0].rgba.slice();
        for (var i = 0; i < n - 1; i++) {
            var a = stops[i], b = stops[i + 1];
            if (t <= b.p) {
                var u = b.p > a.p ? (t - a.p) / (b.p - a.p) : 0, k = midpointRemap(u, a.m);
                return [a.rgba[0] + (b.rgba[0] - a.rgba[0]) * k, a.rgba[1] + (b.rgba[1] - a.rgba[1]) * k, a.rgba[2] + (b.rgba[2] - a.rgba[2]) * k, a.rgba[3] + (b.rgba[3] - a.rgba[3]) * k];
            }
        }
        return stops[n - 1].rgba.slice();
    }
    function buildLut(stops, reverse) {
        var lut = new Float32Array(N * 4);
        for (var i = 0; i < N; i++) {
            var t = i / (N - 1); if (reverse) t = 1 - t;
            var c = sampleStops(stops, t), o = i * 4;
            lut[o] = c[0]; lut[o + 1] = c[1]; lut[o + 2] = c[2]; lut[o + 3] = c[3];
        }
        return lut;
    }
    // t (0..1) of a pixel for each gradient type: the SAME math the app's per-pixel gradient code has used (so the dropdown stays honest)
    function makeT(type, gx1, gy1, gx2, gy2) {
        var dx = gx2 - gx1, dy = gy2 - gy1, len = Math.sqrt(dx * dx + dy * dy) || 1, nx = dx / len, ny = dy / len, ang = Math.atan2(dy, dx), TAU = 2 * Math.PI;
        var c01 = function (t) { return t < 0 ? 0 : (t > 1 ? 1 : t); };
        switch (type) {
            case 'radial': return function (px, py) { var x = px - gx1, y = py - gy1; return c01(Math.sqrt(x * x + y * y) / len); };
            case 'angular': return function (px, py) { return c01((((Math.atan2(py - gy1, px - gx1) - ang) + Math.PI) / TAU) % 1.0); };
            case 'diamond': return function (px, py) { var x = px - gx1, y = py - gy1; return c01(Math.abs(x * nx + y * ny) / len + Math.abs(-x * ny + y * nx) / len); };
            case 'reflected': return function (px, py) { var t = Math.abs(((px - gx1) * nx + (py - gy1) * ny) / len); return c01(t > 1 ? 2 - t : t); };
            case 'spiral-cw': return function (px, py) { var x = px - gx1, y = py - gy1, a = Math.atan2(y, x) - ang, d = Math.sqrt(x * x + y * y) / len; return c01(((a / TAU + d) % 1.0 + 1.0) % 1.0); };
            case 'spiral-ccw': return function (px, py) { var x = px - gx1, y = py - gy1, a = Math.atan2(y, x) - ang, d = Math.sqrt(x * x + y * y) / len; return c01(((-a / TAU + d) % 1.0 + 1.0) % 1.0); };
            case 'conical': return function (px, py) { var a = Math.atan2(py - gy1, px - gx1) - ang; return c01(((a / TAU) % 1.0 + 1.0) % 1.0); };
            default: return function (px, py) { return c01(((px - gx1) * nx + (py - gy1) * ny) / len); };      // linear
        }
    }
    // one level of deterministic dither noise (-0.5..0.5 of an 8-bit step), as PhotoCraft's gradient tool does against banding
    function noise(x, y) {
        var h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0;
        h = Math.imul(h ^ (h >>> 13), 1274126177);
        return (((h ^ (h >>> 16)) & 255) / 255) - 0.5;
    }
    // source-over the ramp onto straight-alpha RGBA bytes `od` (layer-local coords), inside rect [x0,y0,x1,y1)
    function paintRamp(od, lw, lh, gx1, gy1, gx2, gy2, type, layerAlpha, lut, rect) {
        var tf = makeT(type || 'linear', gx1, gy1, gx2, gy2), x0 = 0, y0 = 0, x1 = lw, y1 = lh;
        if (rect) { x0 = Math.max(0, rect[0]); y0 = Math.max(0, rect[1]); x1 = Math.min(lw, rect[2]); y1 = Math.min(lh, rect[3]); }
        var A = layerAlpha == null ? 1 : layerAlpha, M = N - 1;
        for (var py = y0; py < y1; py++) {
            for (var px = x0; px < x1; px++) {
                var li = ((tf(px + 0.5, py + 0.5) * M + 0.5) | 0) * 4, sa = lut[li + 3] * A;
                if (sa <= 0) continue;
                var nz = noise(px, py), sr = lut[li] + nz, sg = lut[li + 1] + nz, sb = lut[li + 2] + nz;
                var idx = (py * lw + px) * 4, da = od[idx + 3] / 255, outA = sa + da * (1 - sa);
                if (outA > 0) {
                    od[idx] = (sr * sa + od[idx] * da * (1 - sa)) / outA;
                    od[idx + 1] = (sg * sa + od[idx + 1] * da * (1 - sa)) / outA;
                    od[idx + 2] = (sb * sa + od[idx + 2] * da * (1 - sa)) / outA;
                    od[idx + 3] = Math.round(outA * 255);
                }
            }
        }
    }
    api.midpointRemap = midpointRemap; api.sampleStops = sampleStops; api.buildLut = buildLut; api.makeT = makeT; api.paintRamp = paintRamp; api.noise = noise; api.N = N;
    if (!isBrowser) return api;

    // ================================================================== browser part
    var STORE = 'spb_tfx3_gradient_v1', USER = 'spb_tfx3_user_gradients_v1';
    var DEFAULT_NAME = 'Foreground to Background';
    function mk(p, c, a, m) { return { p: p, c: c, a: a == null ? 1 : a, m: m == null ? 0.5 : m }; }
    var state = { custom: false, name: DEFAULT_NAME, stops: [mk(0, 'fg'), mk(1, 'bg')] };
    var sel = 0, toolGesture = false;
    function cloneStops(s) { return s.map(function (x) { return mk(x.p, x.c, x.a, x.m); }); }
    function load() {
        try {
            var j = JSON.parse(root.localStorage.getItem(STORE) || 'null');
            if (j && Array.isArray(j.stops) && j.stops.length >= 2) state = { custom: !!j.custom, name: j.name || 'Custom', stops: j.stops.map(function (x) { return mk(clamp(+x.p || 0, 0, 1), String(x.c || '#000000'), clamp(x.a == null ? 1 : +x.a, 0, 1), clamp(x.m == null ? 0.5 : +x.m, 0.05, 0.95)); }) };
            state.stops.sort(function (a, b) { return a.p - b.p; });
        } catch (_e) { }
    }
    function save() { try { root.localStorage.setItem(STORE, JSON.stringify(state)); } catch (_e) { } }
    function hexRgb(h) { var m = /^#?([0-9a-f]{6})$/i.exec(String(h || '')); if (!m) return [0, 0, 0]; var v = parseInt(m[1], 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; }
    function rgbHex(r) { var f = function (v) { v = Math.max(0, Math.min(255, Math.round(v))); return (v < 16 ? '0' : '') + v.toString(16); }; return '#' + f(r[0]) + f(r[1]) + f(r[2]); }
    function colourOf(s) {      // resolve fg / bg links at paint time
        if (s.c === 'fg') return hexRgb(typeof root._foregroundColor === 'string' ? root._foregroundColor : '#000000');
        if (s.c === 'bg') return hexRgb(typeof root._backgroundColor === 'string' ? root._backgroundColor : '#ffffff');
        return hexRgb(s.c);
    }
    function resolved() { return state.stops.map(function (s) { var c = colourOf(s); return { p: s.p, rgba: [c[0], c[1], c[2], s.a], m: s.m }; }); }
    function lutNow(reverse) { return buildLut(resolved(), !!reverse); }
    function isCustom() { return !off() && state.custom; }
    function ftChecked() { var e = document.getElementById('gradientFgToTransparent'); return !!(e && e.checked); }
    function revChecked() { var e = document.getElementById('gradientReverse'); return !!(e && e.checked); }
    function inLayerMode() { try { return typeof isLayerToolbarMode === 'function' && isLayerToolbarMode(); } catch (_e) { return false; } }

    // hook used by fillGradientOnLayer (paint-booth-3-canvas.js): only the interactive tool drag uses the ramp, never a programmatic caller
    api.rampFor = function () { return (isCustom() && toolGesture && !ftChecked()) ? { lut: lutNow(revChecked()) } : null; };
    api.paint = function (od, lw, lh, gx1, gy1, gx2, gy2, type, layerAlpha, reverse, opts) {
        paintRamp(od, lw, lh, gx1, gy1, gx2, gy2, type, layerAlpha, lutNow(reverse), (opts && opts.rect) || selRectLocal(lw, lh, opts && opts.lx, opts && opts.ly));
    };
    function selBounds(W, H) {
        try {
            if (typeof _activeSelectionMask !== 'function') return null;
            var m = _activeSelectionMask(W, H, true); if (!m) return null;
            var x0 = W, y0 = H, x1 = -1, y1 = -1;
            for (var y = 0; y < H; y++) {
                var o = y * W, a = -1, b = -1;
                for (var x = 0; x < W; x++) if (m[o + x]) { a = x; break; }
                if (a < 0) continue;
                for (var x2 = W - 1; x2 >= a; x2--) if (m[o + x2]) { b = x2; break; }
                if (a < x0) x0 = a; if (b > x1) x1 = b; if (y < y0) y0 = y; y1 = y;
            }
            return { mask: m, rect: x1 < 0 ? [0, 0, 0, 0] : [Math.max(0, x0 - 1), Math.max(0, y0 - 1), Math.min(W, x1 + 2), Math.min(H, y1 + 2)] };
        } catch (_e) { return null; }
    }
    function selRectLocal(lw, lh, lx, ly) {
        var pc = document.getElementById('paintCanvas'); if (!pc) return null;
        var b = selBounds(pc.width, pc.height); if (!b) return null;
        return [b.rect[0] - (lx || 0), b.rect[1] - (ly || 0), b.rect[2] - (lx || 0), b.rect[3] - (ly || 0)];
    }

    // ------------------------------------------------------------------ presets (PhotoCraft presets/gradients.rs style)
    function P(name, hexes) { return { name: name, stops: hexes.map(function (h, i) { return mk(hexes.length > 1 ? i / (hexes.length - 1) : 0, h); }) }; }
    function builtins() {
        var fgT = { name: 'Foreground to Transparent', stops: [mk(0, 'fg', 1), mk(1, 'fg', 0)] };
        var hard = { name: 'Red, White, Blue bands', stops: [mk(0, '#c8102e'), mk(0.333, '#c8102e'), mk(0.333, '#ffffff'), mk(0.667, '#ffffff'), mk(0.667, '#0a3161'), mk(1, '#0a3161')] };
        var chrome = { name: 'Chrome sweep', stops: [mk(0, '#6b7280'), mk(0.22, '#f3f4f6'), mk(0.45, '#4b5563'), mk(0.62, '#e5e7eb'), mk(0.82, '#9ca3af'), mk(1, '#374151')] };
        return [
            { name: DEFAULT_NAME, stops: [mk(0, 'fg'), mk(1, 'bg')], isDefault: true }, fgT, P('Black to White', ['#000000', '#ffffff']),
            chrome, hard,
            P('Sunset', ['#ff4e50', '#f9d423', '#fc913a']), P('Ocean', ['#0093e9', '#80d0c7']), P('Carbon Heat', ['#1a1a1a', '#ff6b00', '#ffd700']),
            P('Fire', ['#7f1d1d', '#ef4444', '#fbbf24', '#fff7ae']), P('Gunmetal Fade', ['#0b0d10', '#4b5563', '#0b0d10']),
            P('Midnight Candy', ['#1e1b4b', '#7c3aed', '#f0abfc']), P('Lime Pop', ['#052e16', '#22c55e', '#ecfccb']),
            P('Cobalt', ['#0b3d91', '#4fa3e0']), P('Hot Pink', ['#c9184a', '#ff8fab', '#fff0f5']), P('Gold', ['#7a4f01', '#f5c542', '#fff1b8', '#b8860b'])
        ];
    }
    function userPresets() {
        var out = [];
        try { JSON.parse(root.localStorage.getItem(USER) || '[]').forEach(function (g) { if (g && g.name && Array.isArray(g.stops) && g.stops.length >= 2) out.push({ name: g.name, stops: g.stops.map(function (x) { return mk(+x.p, String(x.c), x.a, x.m); }), user: true }); }); } catch (_e) { }
        try { (root.gradientPresets || []).forEach(function (g) { if (g && g.name && Array.isArray(g.stops) && Array.isArray(g.stops[0]) && !out.some(function (o) { return o.name === g.name; })) out.push({ name: g.name, stops: g.stops.map(function (s) { return mk(+s[0], String(s[1])); }), user: true }); }); } catch (_e) { }
        return out;
    }
    function chipCss(stops) {
        var parts = stops.map(function (s) { var c = colourOf(s); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + s.a + ') ' + Math.round(s.p * 100) + '%'; });
        return 'linear-gradient(to right,' + parts.join(',') + ')';
    }

    // ------------------------------------------------------------------ editor UI
    var pop = null, btn = null, barCv = null, markers = null, ui = {};
    function toast(m, k) { try { if (typeof showToast === 'function') showToast(m, k); } catch (_e) { } }
    function ensureStyle() {
        if (document.getElementById('spbTfx3GradStyle')) return;
        var st = document.createElement('style'); st.id = 'spbTfx3GradStyle';
        st.textContent = [
            '#spbTfx3GradBtn{display:none;align-items:center;gap:5px;height:22px;padding:0 6px;border:1px solid var(--border,#3a3d45);border-radius:4px;background:var(--bg-input,#1c1e24);color:var(--text,#d7d9de);font-size:10px;cursor:pointer;white-space:nowrap}',
            '#spbTfx3GradBtn:hover{border-color:var(--accent,#6ea8fe)}',
            '#spbTfx3GradBtn .sw{display:inline-block;width:54px;height:12px;border-radius:2px;border:1px solid rgba(255,255,255,.25);background-image:linear-gradient(45deg,#777 25%,transparent 25%,transparent 75%,#777 75%),linear-gradient(45deg,#777 25%,#aaa 25%,#aaa 75%,#777 75%);background-size:6px 6px;background-position:0 0,3px 3px;position:relative;overflow:hidden}',
            '#spbTfx3GradBtn .sw i{position:absolute;inset:0}',
            '#spbTfx3GradPop{position:fixed;z-index:100050;width:318px;padding:10px;border:1px solid var(--border,#3a3d45);border-radius:8px;background:var(--bg-panel,#16181d);color:var(--text,#d7d9de);box-shadow:0 10px 30px rgba(0,0,0,.55);font-size:11px;display:none}',
            '#spbTfx3GradPop .row{display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap}',
            '#spbTfx3GradPop .chips{display:flex;flex-wrap:wrap;gap:5px;max-height:86px;overflow:auto}',
            '#spbTfx3GradPop .chip{position:relative;overflow:hidden;width:44px;height:16px;border-radius:3px;border:1px solid rgba(255,255,255,.22);cursor:pointer;padding:0;background:transparent}',
            '#spbTfx3GradPop .chip i{position:absolute;inset:0;display:block}',
            '#spbTfx3GradPop .chip:hover,#spbTfx3GradPop .chip.on{border-color:var(--accent,#6ea8fe);box-shadow:0 0 0 1px var(--accent,#6ea8fe)}',
            '#spbTfx3GradPop .barwrap{position:relative;margin-top:10px;height:44px}',
            '#spbTfx3GradPop .barwrap canvas{position:absolute;left:8px;top:0;width:290px;height:22px;border:1px solid rgba(255,255,255,.3);border-radius:3px;cursor:copy;background-image:linear-gradient(45deg,#777 25%,transparent 25%,transparent 75%,#777 75%),linear-gradient(45deg,#777 25%,#aaa 25%,#aaa 75%,#777 75%);background-size:8px 8px;background-position:0 0,4px 4px}',
            '#spbTfx3GradPop .mk{position:absolute;top:24px;width:14px;height:18px;margin-left:-7px;cursor:grab;touch-action:none}',
            '#spbTfx3GradPop .mk b{position:absolute;left:0;top:0;width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-bottom:7px solid #cfd3da}',
            '#spbTfx3GradPop .mk u{position:absolute;left:1px;top:7px;width:12px;height:11px;border:2px solid #cfd3da;border-radius:2px;box-sizing:border-box;text-decoration:none}',
            '#spbTfx3GradPop .mk.on b{border-bottom-color:var(--accent,#6ea8fe)}#spbTfx3GradPop .mk.on u{border-color:var(--accent,#6ea8fe)}',
            '#spbTfx3GradPop input[type=number]{width:46px;font-size:11px;padding:1px 3px;background:var(--bg-input,#1c1e24);color:inherit;border:1px solid var(--border,#3a3d45);border-radius:3px}',
            '#spbTfx3GradPop input[type=text]{width:120px;font-size:11px;padding:1px 4px;background:var(--bg-input,#1c1e24);color:inherit;border:1px solid var(--border,#3a3d45);border-radius:3px}',
            '#spbTfx3GradPop input[type=color]{width:34px;height:22px;padding:0;border:1px solid var(--border,#3a3d45);border-radius:3px;background:none;cursor:pointer}',
            '#spbTfx3GradPop button.b{font-size:11px;padding:2px 8px;border:1px solid var(--border,#3a3d45);border-radius:4px;background:var(--bg-input,#1c1e24);color:inherit;cursor:pointer}',
            '#spbTfx3GradPop button.b:hover{border-color:var(--accent,#6ea8fe)}#spbTfx3GradPop button.b[disabled]{opacity:.4;cursor:default}',
            '#spbTfx3GradPop h4{margin:0 0 6px;font-size:11px;font-weight:600;opacity:.85}',
            '#spbTfx3GradPop .hint{margin-top:8px;opacity:.6;font-size:10px;line-height:1.35}'
        ].join('\n');
        document.head.appendChild(st);
    }
    function drawBar() {
        if (!barCv) return;
        var w = barCv.width, h = barCv.height, g = barCv.getContext('2d'), lut = lutNow(false), img = g.createImageData(w, 1), d = img.data;
        for (var x = 0; x < w; x++) { var li = Math.round(x / (w - 1) * (N - 1)) * 4; d[x * 4] = lut[li]; d[x * 4 + 1] = lut[li + 1]; d[x * 4 + 2] = lut[li + 2]; d[x * 4 + 3] = Math.round(lut[li + 3] * 255); }
        g.clearRect(0, 0, w, h);
        var row = document.createElement('canvas'); row.width = w; row.height = 1; row.getContext('2d').putImageData(img, 0, 0);
        g.imageSmoothingEnabled = false; g.drawImage(row, 0, 0, w, h);
    }
    function drawMarkers() {
        if (!markers) return;
        markers.innerHTML = '';
        state.stops.forEach(function (s, i) {
            var m = document.createElement('div'); m.className = 'mk' + (i === sel ? ' on' : ''); m.dataset.i = i;
            m.style.left = (8 + s.p * 290) + 'px'; m.title = 'Colour stop ' + (i + 1) + ' - drag to move, select to edit';
            var c = colourOf(s); m.innerHTML = '<b></b><u style="background:rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',1)"></u>';
            markers.appendChild(m);
        });
    }
    function refreshBtn() {
        if (!btn) return;
        var sw = btn.querySelector('.sw i');
        if (sw) sw.style.background = chipCss(state.custom ? state.stops : [mk(0, 'fg'), mk(1, 'bg')]);
        btn.title = 'Gradient colours: ' + (state.custom ? state.name : DEFAULT_NAME) + ' - click to pick a preset or edit colour stops';
    }
    function refreshPop() {
        if (!pop) return;
        drawBar(); drawMarkers(); refreshBtn();
        var s = state.stops[sel] || state.stops[0];
        if (ui.col) { var c = colourOf(s); ui.col.value = rgbHex(c); ui.pos.value = Math.round(s.p * 100); ui.op.value = Math.round(s.a * 100); ui.mid.value = Math.round(s.m * 100); ui.mid.disabled = sel >= state.stops.length - 1; ui.del.disabled = state.stops.length <= 2; ui.fgb.classList.toggle('on', s.c === 'fg'); ui.bgb.classList.toggle('on', s.c === 'bg'); }
        if (ui.rev) ui.rev.checked = revChecked();
        if (ui.chips) Array.prototype.forEach.call(ui.chips.children, function (ch) { ch.classList.toggle('on', ch.dataset.name === (state.custom ? state.name : DEFAULT_NAME)); });
    }
    function edited(name) { state.custom = true; state.name = name || 'Custom'; var ft = document.getElementById('gradientFgToTransparent'); if (ft && ft.checked) { ft.checked = false; try { ft.dispatchEvent(new Event('change', { bubbles: true })); } catch (_e) { } } save(); refreshPop(); syncBtn(); }
    function choose(preset) {
        if (preset.isDefault) { state = { custom: false, name: DEFAULT_NAME, stops: [mk(0, 'fg'), mk(1, 'bg')] }; sel = 0; save(); refreshPop(); syncBtn(); return; }
        state.stops = cloneStops(preset.stops); state.stops.sort(function (a, b) { return a.p - b.p; }); sel = 0; edited(preset.name);
    }
    function fillChips() {
        if (!ui.chips) return;
        ui.chips.innerHTML = '';
        var seenNames = {};
        builtins().concat(userPresets()).forEach(function (pr) {
            if (seenNames[pr.name]) return; seenNames[pr.name] = 1;   // the old window.gradientPresets stub shares names with the built-ins
            var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.dataset.name = pr.name; b.title = pr.name; b.setAttribute('aria-label', 'Gradient preset ' + pr.name);
            var ci = document.createElement('i'); ci.style.background = chipCss(pr.isDefault ? [mk(0, 'fg'), mk(1, 'bg')] : pr.stops); b.appendChild(ci);
            b.addEventListener('click', function () { choose(pr); });
            ui.chips.appendChild(b);
        });
    }
    function addStopAt(p) {
        var c = sampleStops(resolved(), p), s = mk(p, rgbHex(c), c[3], 0.5);
        state.stops.push(s); state.stops.sort(function (a, b) { return a.p - b.p; }); sel = state.stops.indexOf(s); edited('Custom');
    }
    function build() {
        if (pop) return;
        ensureStyle();
        pop = document.createElement('div'); pop.id = 'spbTfx3GradPop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', 'Gradient colours');
        pop.innerHTML = '<h4>Gradient colours</h4><div class="chips" id="spbTfx3GradChips"></div>' +
            '<div class="barwrap"><canvas width="580" height="44" id="spbTfx3GradBar" title="Click to add a colour stop"></canvas><div id="spbTfx3GradMk"></div></div>' +
            '<div class="row"><span>Stop colour</span><input type="color" id="spbTfx3GradCol" aria-label="Stop colour"><button class="b" type="button" id="spbTfx3GradFg" title="Use whatever the Foreground colour is when you paint">Foreground</button><button class="b" type="button" id="spbTfx3GradBg" title="Use whatever the Background colour is when you paint">Background</button></div>' +
            '<div class="row"><span>Position</span><input type="number" id="spbTfx3GradPos" min="0" max="100" step="1"><span>%</span><span style="margin-left:6px">Opacity</span><input type="number" id="spbTfx3GradOp" min="0" max="100" step="1"><span>%</span></div>' +
            '<div class="row"><span>Midpoint to next stop</span><input type="number" id="spbTfx3GradMid" min="5" max="95" step="1"><span>%</span><button class="b" type="button" id="spbTfx3GradDel" style="margin-left:auto" title="Delete this colour stop (two stay)">Delete stop</button></div>' +
            '<div class="row"><label style="display:flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" id="spbTfx3GradRev">Reverse</label><input type="text" id="spbTfx3GradName" placeholder="Preset name" aria-label="Preset name"><button class="b" type="button" id="spbTfx3GradSave">Save preset</button><button class="b" type="button" id="spbTfx3GradReset" title="Back to Foreground to Background">Reset</button></div>' +
            '<div class="hint">Drag on the canvas to paint it: the gradient previews live and applies when you let go. Foreground / Background stops follow the colours you have selected.</div>';
        document.body.appendChild(pop);
        ui.chips = pop.querySelector('#spbTfx3GradChips'); barCv = pop.querySelector('#spbTfx3GradBar'); markers = pop.querySelector('#spbTfx3GradMk');
        ui.col = pop.querySelector('#spbTfx3GradCol'); ui.pos = pop.querySelector('#spbTfx3GradPos'); ui.op = pop.querySelector('#spbTfx3GradOp'); ui.mid = pop.querySelector('#spbTfx3GradMid');
        ui.del = pop.querySelector('#spbTfx3GradDel'); ui.fgb = pop.querySelector('#spbTfx3GradFg'); ui.bgb = pop.querySelector('#spbTfx3GradBg'); ui.rev = pop.querySelector('#spbTfx3GradRev');
        ui.name = pop.querySelector('#spbTfx3GradName');
        fillChips();
        ui.col.addEventListener('input', function () { var s = state.stops[sel]; if (!s) return; s.c = ui.col.value; edited('Custom'); });
        ui.fgb.addEventListener('click', function () { var s = state.stops[sel]; if (!s) return; s.c = 'fg'; edited('Custom'); });
        ui.bgb.addEventListener('click', function () { var s = state.stops[sel]; if (!s) return; s.c = 'bg'; edited('Custom'); });
        ui.pos.addEventListener('change', function () { var s = state.stops[sel]; if (!s) return; s.p = clamp((+ui.pos.value || 0) / 100, 0, 1); state.stops.sort(function (a, b) { return a.p - b.p; }); sel = state.stops.indexOf(s); edited('Custom'); });
        ui.op.addEventListener('change', function () { var s = state.stops[sel]; if (!s) return; s.a = clamp((+ui.op.value) / 100, 0, 1); edited('Custom'); });
        ui.mid.addEventListener('change', function () { var s = state.stops[sel]; if (!s) return; s.m = clamp((+ui.mid.value || 50) / 100, 0.05, 0.95); edited('Custom'); });
        ui.del.addEventListener('click', function () { if (state.stops.length <= 2) return; state.stops.splice(sel, 1); sel = Math.max(0, sel - 1); edited('Custom'); });
        ui.rev.addEventListener('change', function () { var e = document.getElementById('gradientReverse'); if (e) { e.checked = ui.rev.checked; try { e.dispatchEvent(new Event('change', { bubbles: true })); } catch (_e) { } } });
        pop.querySelector('#spbTfx3GradReset').addEventListener('click', function () { choose(builtins()[0]); });
        pop.querySelector('#spbTfx3GradSave').addEventListener('click', function () {
            var nm = String(ui.name.value || '').trim(); if (!nm) { ui.name.focus(); toast('Type a name for the preset first', 'info'); return; }
            try { var arr = JSON.parse(root.localStorage.getItem(USER) || '[]').filter(function (g) { return g && g.name !== nm; }); arr.push({ name: nm, stops: cloneStops(state.stops) }); root.localStorage.setItem(USER, JSON.stringify(arr)); } catch (_e) { }
            state.name = nm; state.custom = true; save(); fillChips(); refreshPop(); toast('Saved gradient preset: ' + nm, 'success');
        });
        // colour bar: click = new stop; stop markers: drag = move
        var wrap = pop.querySelector('.barwrap'), drag = null;
        function posFromEvent(e) { var r = barCv.getBoundingClientRect(); return clamp((e.clientX - r.left) / r.width, 0, 1); }
        wrap.addEventListener('pointerdown', function (e) {
            var mk_ = e.target.closest && e.target.closest('.mk');
            if (mk_) { sel = +mk_.dataset.i; drag = state.stops[sel]; } else if (e.target === barCv) { addStopAt(posFromEvent(e)); drag = state.stops[sel]; } else return;
            try { wrap.setPointerCapture(e.pointerId); } catch (_e) { }
            refreshPop(); e.preventDefault();
        });
        wrap.addEventListener('pointermove', function (e) {
            if (!drag) return;
            drag.p = Math.round(posFromEvent(e) * 1000) / 1000; state.stops.sort(function (a, b) { return a.p - b.p; }); sel = state.stops.indexOf(drag);
            state.custom = true; if (state.name === DEFAULT_NAME) state.name = 'Custom'; refreshPop();
        });
        function endDrag() { if (drag) { drag = null; edited(state.name); } }
        wrap.addEventListener('pointerup', endDrag); wrap.addEventListener('pointercancel', endDrag);
        pop.addEventListener('keydown', function (e) {
            if ((e.key === 'Delete' || e.key === 'Backspace') && e.target.tagName !== 'INPUT') { if (state.stops.length > 2) { state.stops.splice(sel, 1); sel = Math.max(0, sel - 1); edited('Custom'); e.preventDefault(); e.stopPropagation(); } }
            if (e.key === 'Escape') { closePop(); e.stopPropagation(); }
        });
        document.addEventListener('mousedown', function (e) { if (pop && pop.style.display !== 'none' && !pop.contains(e.target) && !(btn && btn.contains(e.target))) closePop(); }, true);
    }
    function openPop() {
        build(); fillChips(); refreshPop();
        pop.style.display = 'block';
        var r = btn.getBoundingClientRect(), w = 318, left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left)), top = r.bottom + 6;
        if (top + pop.offsetHeight > window.innerHeight - 8) top = Math.max(8, r.top - pop.offsetHeight - 6);
        pop.style.left = left + 'px'; pop.style.top = top + 'px';
    }
    function closePop() { if (pop) pop.style.display = 'none'; }
    function ensureBtn() {
        if (btn || off()) return;
        var anchor = document.getElementById('gradientFgTransLabel') || document.getElementById('gradientReverseLabel') || document.getElementById('gradientType');
        if (!anchor || !anchor.parentNode) return;
        ensureStyle();
        btn = document.createElement('button'); btn.type = 'button'; btn.id = 'spbTfx3GradBtn'; btn.setAttribute('aria-label', 'Gradient colours');
        btn.innerHTML = '<span class="sw"><i></i></span><span>Colours</span><span aria-hidden="true">▾</span>';
        anchor.parentNode.insertBefore(btn, anchor.nextSibling);
        btn.addEventListener('click', function (e) { e.stopPropagation(); if (pop && pop.style.display === 'block') closePop(); else openPop(); });
        refreshBtn();
    }
    function syncBtn() {
        try {
            if (off()) { if (btn) btn.style.display = 'none'; return; }
            ensureBtn(); if (!btn) return;
            var anc = document.getElementById('gradientFgTransLabel') || document.getElementById('gradientReverseLabel') || document.getElementById('gradientType');
            if (anc && anc.parentNode && (btn.parentNode !== anc.parentNode || anc.nextSibling !== btn)) anc.parentNode.insertBefore(btn, anc.nextSibling);   // keep it next to Linear / Reverse wherever the options row lives
            var show = (typeof canvasMode !== 'undefined' && canvasMode === 'gradient') && inLayerMode();
            btn.style.display = show ? 'inline-flex' : 'none';
            if (!show) closePop();
            var fl = document.getElementById('gradientFgTransLabel'); if (fl && show && state.custom) fl.style.display = 'none';
            refreshBtn();
        } catch (_e) { }
    }
    load();
    if (!off()) setInterval(syncBtn, 350);

    // ------------------------------------------------------------------ live preview while dragging (layer gradients)
    var ov = null, small = null, smallData = null, pvRaf = 0, pvEv = null, pvKey = '', pvMask = null;
    function overlay() {
        var pc = document.getElementById('paintCanvas'); if (!pc) return null;
        if (!ov) {
            var tc = document.getElementById('transformCanvas'), host = (tc && tc.parentNode) || pc.parentNode; if (!host) return null;
            ov = document.createElement('canvas'); ov.id = 'spbTfx3GradPrev'; ov.setAttribute('aria-hidden', 'true');
            ov.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:14;display:none;';
            host.appendChild(ov);
        }
        if (ov.width !== pc.width) ov.width = pc.width; if (ov.height !== pc.height) ov.height = pc.height;
        ov.style.width = pc.style.width; ov.style.height = pc.style.height;
        return ov;
    }
    function hidePreview() { pvEv = null; pvKey = ''; pvMask = null; if (ov) { ov.style.display = 'none'; try { ov.getContext('2d').clearRect(0, 0, ov.width, ov.height); } catch (_e) { } } }
    function drawPreview() {
        pvRaf = 0;
        var e = pvEv; if (!e || off()) return;
        var st = root._gradientStart, tg = root._gradientTarget, pc = document.getElementById('paintCanvas');
        if (!st || !tg || tg.kind !== 'layer' || !pc || typeof canvasMode === 'undefined' || canvasMode !== 'gradient' || !isCustom() || ftChecked()) return hidePreview();
        var layer = null; try { layer = _psdLayers.find(function (l) { return l && l.id === tg.layerId; }); } catch (_e) { }
        if (!layer || !layer.img) return hidePreview();
        var W = pc.width, H = pc.height, r = pc.getBoundingClientRect();
        var end = { x: clamp((e.clientX - r.left) * W / r.width, 0, W), y: clamp((e.clientY - r.top) * H / r.height, 0, H) };
        try { if (root.SPBGradient && root.SPBGradient.constrainEndpoint) end = root.SPBGradient.constrainEndpoint(st, end, e.shiftKey) || end; } catch (_e) { }
        var dx = end.x - st.x, dy = end.y - st.y; if (dx * dx + dy * dy < 4) return hidePreview();
        var o = overlay(); if (!o) return;
        var key = tg.layerId + '|' + st.x + ',' + st.y;
        if (key !== pvKey) { pvKey = key; var b = selBounds(W, H); pvMask = b ? b.mask : null; }
        var origin = { x: 0, y: 0 }; try { origin = getLayerCanvasOrigin(layer) || origin; } catch (_e) { }
        var lw = layer.img.width || layer.img.naturalWidth, lh = layer.img.height || layer.img.naturalHeight;
        var s = Math.max(1, Math.ceil(Math.max(W, H) / 512)), pw = Math.ceil(W / s), ph = Math.ceil(H / s);
        if (!small || small.width !== pw || small.height !== ph) { small = document.createElement('canvas'); small.width = pw; small.height = ph; smallData = small.getContext('2d').createImageData(pw, ph); }
        var d = smallData.data, lut = lutNow(revChecked()), tf = makeT((document.getElementById('gradientType') || {}).value || 'linear', st.x, st.y, end.x, end.y);
        var A = clamp(parseInt((document.getElementById('brushOpacity') || {}).value || 100, 10) / 100, 0, 1), M = N - 1, m = pvMask;
        for (var qy = 0; qy < ph; qy++) {
            var cy = qy * s + (s >> 1);
            for (var qx = 0; qx < pw; qx++) {
                var cx = qx * s + (s >> 1), o4 = (qy * pw + qx) * 4;
                if (cx < origin.x || cy < origin.y || cx >= origin.x + lw || cy >= origin.y + lh) { d[o4 + 3] = 0; continue; }
                var cov = m ? m[(cy < H ? cy : H - 1) * W + (cx < W ? cx : W - 1)] / 255 : 1;
                if (cov <= 0) { d[o4 + 3] = 0; continue; }
                var li = ((tf(cx + 0.5, cy + 0.5) * M + 0.5) | 0) * 4;
                d[o4] = lut[li]; d[o4 + 1] = lut[li + 1]; d[o4 + 2] = lut[li + 2]; d[o4 + 3] = lut[li + 3] * A * cov * 255;
            }
        }
        small.getContext('2d').putImageData(smallData, 0, 0);
        var g = o.getContext('2d'); g.clearRect(0, 0, W, H); g.imageSmoothingEnabled = true; g.drawImage(small, 0, 0, W, H);
        o.style.display = 'block';
    }
    document.addEventListener('mousemove', function (e) {
        if (off() || !(e.buttons & 1) || typeof canvasMode === 'undefined' || canvasMode !== 'gradient' || !root._gradientStart) { if (pvEv) hidePreview(); return; }
        pvEv = { clientX: e.clientX, clientY: e.clientY, shiftKey: e.shiftKey };
        if (!pvRaf) pvRaf = requestAnimationFrame(drawPreview);
    }, true);
    document.addEventListener('mouseup', function () {
        // the app's own mouseup handler (bubble phase) runs right after this capture listener inside the same event: flag the call as the interactive tool drag
        if (typeof canvasMode !== 'undefined' && canvasMode === 'gradient' && root._gradientStart) { toolGesture = true; setTimeout(function () { toolGesture = false; }, 0); }
        if (pvRaf) { cancelAnimationFrame(pvRaf); pvRaf = 0; }
        hidePreview();
    }, true);

    api.state = function () { return { custom: state.custom, name: state.name, stops: cloneStops(state.stops), off: off() }; };
    api.setStops = function (stops, name) { state.stops = stops.map(function (x) { return mk(x.p, x.c, x.a, x.m); }); state.stops.sort(function (a, b) { return a.p - b.p; }); sel = 0; edited(name || 'Custom'); };
    api.reset = function () { choose(builtins()[0]); };
    api.open = function () { syncBtn(); if (btn) openPop(); };
    api.close = closePop;
    return api;
});
