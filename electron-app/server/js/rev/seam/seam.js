/* [SPB-REV-SEAM 2026-10-10] Edge Bleed (client side): find the car's UV islands from its Wire template and hand them to the render.
 *
 * WHY: an iRacing paint is a 2048 sheet with the car cut into UV islands. The sim filters and mip-maps the sheet, so a panel's edge picks up
 * whatever the unused gutter holds (the catch-all zone's paint, a different spec: chrome dulled at its rim, dark art rimmed with base colour).
 * Painters bleed paint past every edge by hand. With the Settings > Options box ticked, the render does it for paint AND spec
 * (engine/rev_seam_bleed.py: every gutter pixel within 16 px of an island copies its nearest island pixel; island pixels are never touched).
 *
 * ISLANDS: the template's Wire layer carries pure-green (1,255,0) UV-island outlines + white mesh lines. Island = region enclosed by the green
 * outline (4-connected components of the non-green area), minus components the template's Mask layer marks unused (>= 50%: wheel arches),
 * minus the big exterior component and anything touching the sheet edge. Same algorithm as engine.rev_seam_bleed.island_mask_from_wire
 * (parity measured in _easy_claude_work/rev_tools/seam/). No Wire layer (flat TGA, odd template) = nothing to bleed: the box says so and the
 * render is unchanged.
 *
 * API: SpbRevSeam = { VER, off(), isOn(), setOn(b), ensure(), renderField(), status(), _internal }.  ShokkerAPI.render() calls renderField()
 * (one commented hook in paint-booth-5-api-render.js); no field = the request is exactly what it was.
 * KILL SWITCH: window.SPB_REV_SEAM_OFF = true or localStorage SPB_REV_SEAM_OFF = '1' -> no UI, renderField() is null (server env SPB_REV_SEAM_OFF=1 too).
 */
(function (root) {
    'use strict';
    var VER = 'seam1.1';
    var LS_ON = 'spb_rev_seam_on';
    var DEFAULT_PX = 16;
    var C = { img: null, mask: null, png: null, info: null, busy: null, err: null };

    function off() {
        try { if (root.SPB_REV_SEAM_OFF) return true; } catch (e) { /* ignore */ }
        try { return !!(root.localStorage && root.localStorage.getItem('SPB_REV_SEAM_OFF') === '1'); } catch (e) { return false; }
    }
    function lsGet(k) { try { return root.localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { root.localStorage.setItem(k, v); } catch (e) { /* ignore */ } }
    function isOn() { return !off() && lsGet(LS_ON) === '1'; }
    function px() { var v = parseInt(root.SPB_REV_SEAM_PX, 10); return v >= 1 && v <= 64 ? v : DEFAULT_PX; }

    // ---------------------------------------------------------------- the car's template layers
    function layers() { try { return root._psdLayers || (typeof _psdLayers !== 'undefined' ? _psdLayers : []); } catch (e) { return []; } }
    function findLayer(re) { return layers().find(function (l) { return l && l.img && re.test(String(l.name || '').trim()); }) || null; }
    function wireLayer() { return findLayer(/^(wire|wireframe)$/i); }
    function maskLayer() { return findLayer(/^mask$/i); }
    function sheetWH() { var c = document.getElementById('paintCanvas'); return c && c.width ? [c.width, c.height] : [2048, 2048]; }
    function layerRGBA(L, W, H) {
        var c = document.createElement('canvas'); c.width = W; c.height = H;
        var x = c.getContext('2d', { willReadFrequently: true });
        x.drawImage(L.img, L.bbox ? L.bbox[0] : 0, L.bbox ? L.bbox[1] : 0);
        return x.getImageData(0, 0, W, H).data;
    }

    // ---------------------------------------------------------------- island finder
    function dilate3(a, W, H, iters) {                       // 3x3 binary dilation, `iters` times (separable)
        var cur = a, t = new Uint8Array(W * H), o = new Uint8Array(W * H);
        for (var it = 0; it < iters; it++) {
            var x, y, i;
            for (y = 0; y < H; y++) for (x = 0; x < W; x++) { i = y * W + x; t[i] = cur[i] | (x > 0 ? cur[i - 1] : 0) | (x < W - 1 ? cur[i + 1] : 0); }
            for (y = 0; y < H; y++) for (x = 0; x < W; x++) { i = y * W + x; o[i] = t[i] | (y > 0 ? t[i - W] : 0) | (y < H - 1 ? t[i + W] : 0); }
            cur = o; o = new Uint8Array(W * H);
        }
        return cur;
    }
    function findIslands(wireD, maskD, W, H) {
        var N = W * H, i, green = new Uint8Array(N), nGreen = 0, brownPx = new Uint8Array(N);
        for (i = 0; i < N; i++) {
            var j = i * 4;
            if (wireD[j + 3] > 16 && wireD[j] < 128 && wireD[j + 1] > 200) { green[i] = 1; nGreen++; }
            if (maskD && maskD[j + 3] > 128) brownPx[i] = 1;
        }
        if (nGreen < 500) return { mask: null, why: 'no green outline in the Wire layer' };
        var barrier = dilate3(green, W, H, 1);
        var lab = new Int32Array(N), stack = new Int32Array(N), area = [0], touch = [0], n = 0, s;
        for (s = 0; s < N; s++) {
            if (barrier[s] || lab[s]) continue;
            n++; var sp = 0, a = 0, t = 0; stack[sp++] = s; lab[s] = n;
            while (sp) {
                var p = stack[--sp], x = p % W, y = (p / W) | 0, q; a++;
                if (x === 0 || y === 0 || x === W - 1 || y === H - 1) t = 1;
                if (x > 0) { q = p - 1; if (!barrier[q] && !lab[q]) { lab[q] = n; stack[sp++] = q; } }
                if (x < W - 1) { q = p + 1; if (!barrier[q] && !lab[q]) { lab[q] = n; stack[sp++] = q; } }
                if (y > 0) { q = p - W; if (!barrier[q] && !lab[q]) { lab[q] = n; stack[sp++] = q; } }
                if (y < H - 1) { q = p + W; if (!barrier[q] && !lab[q]) { lab[q] = n; stack[sp++] = q; } }
            }
            area.push(a); touch.push(t);
        }
        var brown = new Float64Array(n + 1);
        if (maskD) for (i = 0; i < N; i++) if (lab[i] && brownPx[i]) brown[lab[i]]++;
        var big = 1; for (var k = 2; k <= n; k++) if (area[k] > area[big]) big = k;
        var isl = new Uint8Array(n + 1), nIsl = 0;
        for (k = 1; k <= n; k++) {
            if (k === big || touch[k] || area[k] < 30 || brown[k] / Math.max(area[k], 1) >= 0.5) continue;
            isl[k] = 1; nIsl++;
        }
        var inner = new Uint8Array(N), cnt = 0;
        for (i = 0; i < N; i++) if (lab[i] && isl[lab[i]]) inner[i] = 1;
        var grown = dilate3(inner, W, H, 2), out = new Uint8Array(N);
        for (i = 0; i < N; i++) { out[i] = (inner[i] || (barrier[i] && grown[i])) ? 1 : 0; cnt += out[i]; }
        return { mask: out, islands: nIsl, frac: cnt / N, components: n, green: nGreen };
    }
    function encodePNG(mask, W, H) {
        var c = document.createElement('canvas'); c.width = W; c.height = H;
        var x = c.getContext('2d'), id = x.createImageData(W, H), d = id.data;
        for (var i = 0, N = W * H; i < N; i++) { var v = mask[i] ? 255 : 0, j = i * 4; d[j] = v; d[j + 1] = v; d[j + 2] = v; d[j + 3] = 255; }
        x.putImageData(id, 0, 0);
        return c.toDataURL('image/png').split(',')[1];
    }

    // ---------------------------------------------------------------- build / cache per loaded car
    function ensure() {
        if (off()) return Promise.resolve(null);
        var L = wireLayer();
        if (!L) { C.err = 'This car has no Wire layer, so there is nothing to bleed'; C.img = null; C.png = null; C.info = null; return Promise.resolve(null); }
        if (C.img === L.img && C.png) return Promise.resolve(C);
        if (C.busy && C.busyImg === L.img) return C.busy;
        C.busyImg = L.img;
        C.busy = new Promise(function (resolve) {
            setTimeout(function () {                           // yield so the checkbox repaints first
                try {
                    var t0 = performance.now(), wh = sheetWH(), W = wh[0], H = wh[1];
                    var wd = layerRGBA(L, W, H), M = maskLayer(), md = M ? layerRGBA(M, W, H) : null;
                    var r = findIslands(wd, md, W, H);
                    if (!r.mask) { C.err = 'The Wire layer has no panel outlines, so there is nothing to bleed'; C.img = null; C.png = null; C.info = { why: r.why }; resolve(null); return; }
                    var png = encodePNG(r.mask, W, H);
                    C.img = L.img; C.mask = r.mask; C.png = png; C.err = null;
                    C.info = { islands: r.islands, frac: r.frac, ms: Math.round(performance.now() - t0), png_kb: Math.round(png.length * 0.75 / 1024), w: W, h: H, green: r.green };
                    resolve(C);
                } catch (e) { C.err = 'Could not read the Wire layer (' + (e && e.message || e) + ')'; C.png = null; resolve(null); }
                finally { C.busy = null; }
            }, 20);
        });
        return C.busy;
    }

    // ---------------------------------------------------------------- the render hook
    function renderField() {
        if (!isOn()) return Promise.resolve(null);
        return ensure().then(function (c) { paint(); return c ? { on: true, px: px(), mask_png: c.png, ver: VER } : null; });
    }

    // ---------------------------------------------------------------- Settings > Options box
    function statusText() {
        if (off()) return '';
        if (!isOn()) return 'Fixes seams in iRacing. Copies each panel\'s edge paint and spec a few pixels into the gaps.';
        if (C.busy) return 'Reading the car\'s panel outlines...';
        if (C.err) return C.err + '. Renders are unchanged.';
        if (C.info) return 'On: ' + C.info.islands + ' panels found. Their edges extend ' + px() + ' px into the gaps on every render.';
        return 'On. Reading the car\'s panel outlines.';
    }
    function paint() {
        var row = document.getElementById('spbSeamRow'), cb = document.getElementById('spbSeamBleedCheckbox'), hint = document.getElementById('spbSeamBleedHint');
        if (!row) return;
        if (off()) { row.style.display = 'none'; return; }
        row.style.display = '';
        if (cb) cb.checked = isOn();
        if (hint) hint.textContent = statusText();
    }
    function setOn(b) {
        if (off()) return false;
        lsSet(LS_ON, b ? '1' : '0');
        paint();
        if (b) ensure().then(paint);
        return isOn();
    }
    function bind() {
        var cb = document.getElementById('spbSeamBleedCheckbox');
        if (cb && !cb._seamBound) { cb._seamBound = true; cb.addEventListener('change', function () { setOn(cb.checked); }); }
        paint();
        if (isOn()) setTimeout(function () { ensure().then(paint); }, 2500);   // after the car has loaded
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind); else bind();

    root.SpbRevSeam = {
        VER: VER, off: off, isOn: isOn, setOn: setOn, ensure: ensure, renderField: renderField, px: px,
        status: function () { return { on: isOn(), off: off(), err: C.err, info: C.info, text: statusText() }; },
        _internal: { findIslands: findIslands, encodePNG: encodePNG, dilate3: dilate3, cache: C }
    };
})(window);
