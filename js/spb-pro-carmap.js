/* ============================================================================
   SPB PRO CAR MAP — the copilot's understanding of THIS car's layout and layers   (SPB-AI 2026-09-30)
   Pro's paint is a flat 2048² UV sheet: the car's panels (sides, hood, roof, bumpers, ...) are separate ISLANDS. "The rear of each side" is meaningless
   on a grid alone. This module
     1. classifies every PSD layer by role (body / numbers / sponsors / tape / decal / template-to-switch-off-before-export),
     2. finds the islands of the body layer (connected components of its visible footprint, at 256², closed over hairline gaps),
     3. asks the vision model ONCE (cached per car signature, also in localStorage) to NAME each numbered island and say which end is the FRONT,
     4. serves exact masks:  maskFor('left side', 'rear half')  ->  Uint8Array(W*H)   (island ∩ portion),  used by SpbProZone regions {island, portion}.
   PARTS (2026-09-30 v3): the car's named regions (hood, roof, left side, ...) come from (a) the CAR LIBRARY (window.SPB_CAR_ATLAS, hand-checked layouts matched by
   the paintable-area fingerprint or the iRacing car folder), (b) what the buyer taught (tap an island OR drag a rectangle; remembered per layout).  Vision models
   cannot read UV sheets (measured: 5 models, best 9/22 boxes right), so names are NEVER guessed from a picture.
   SpbProCar.ensure() -> Promise<map>   SpbProCar.map()   SpbProCar.describe()   SpbProCar.maskFor(ref, portion)   SpbProCar.roles()
   ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var SERVERMASK = null, GRID = 256, LASTCI = null, CACHE = null, CACHE_SOURCE = null, PENDING = null, MASKS = null, LABELS = {}, LS = 'spb_carmap_v1', LASTBG = null, PAINT = null;
    function G(name) { try { return window[name]; } catch (e) { return undefined; } }
    function paintDims() { var c = document.getElementById('paintCanvas'); return c ? [c.width, c.height] : [2048, 2048]; }
    // Source identity is intentionally separate from signature(): geometry and deliberate layout teaching reuse keep their existing contract.
    function sourceDescriptor() {
        var path = '', canvas = null, dims = paintDims(), generation = null;
        try { path = String((window.getCurrentSourcePaintFile && window.getCurrentSourcePaintFile()) || ((typeof _psdPath !== 'undefined' && _psdPath) ? _psdPath : '') || ''); } catch (e) {}
        try { canvas = document.getElementById('paintCanvas'); } catch (e2) {}
        try { if (typeof _spbSourceLoadGeneration !== 'undefined') generation = Number(_spbSourceLoadGeneration); } catch (e3) {}
        if (generation === null || !isFinite(generation)) {
            try { var tx = window.SPBSourceLoadTransaction; if (tx && typeof tx.getGeneration === 'function') generation = Number(tx.getGeneration()); } catch (e4) {}
        }
        return { path: path, width: dims[0], height: dims[1], canvas: canvas, generation: (generation !== null && isFinite(generation)) ? generation : null };
    }
    function sameSource(a, b) {
        return !!a && !!b && a.path === b.path && a.width === b.width && a.height === b.height && a.canvas === b.canvas && a.generation === b.generation;
    }
    function currentSource(request) { return !!request && sameSource(request.source, sourceDescriptor()); }
    function publishCache(m, request) {
        if (!currentSource(request)) return false;
        CACHE = m; CACHE_SOURCE = request.source; return true;
    }
    function clearSourceCache() {
        CACHE = null; CACHE_SOURCE = null; MASKS = null; PAINT = null; LASTCI = null; LASTBG = null;
        if (SERVERMASK && !sameSource(SERVERMASK.source, sourceDescriptor())) SERVERMASK = null;
    }
    function layersArr() { try { return _psdLayers || []; } catch (e) { return []; } }
    function cellName(cx, cy) { return 'ABCDEFGH'.charAt(Math.max(0, Math.min(7, cx))) + (Math.max(0, Math.min(7, cy)) + 1); }
    function cellsOf(b) { return cellName(Math.floor(b[0] * 8), Math.floor(b[1] * 8)) + ':' + cellName(Math.min(7, Math.floor(b[2] * 8 - 1e-6)), Math.min(7, Math.floor(b[3] * 8 - 1e-6))); }
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }

    // ------------------------------------------------------------------ layer roles
    function roleOf(l) {
        var n = norm(l.name), g = norm(l.groupName || '');
        if (/turn off|export|template|guide/.test(g) || /(^| )(mask|wire|wireframe|mandatory|template|guide|outline|uv)( |$)/.test(n) || /mandatory/.test(n)) return 'template (switch off before exporting)';
        if (/number/.test(n)) return 'numbers';
        if (/sponsor/.test(n)) return 'sponsors';
        if (/tape/.test(n)) return 'tape / stripes';
        if (/car paint|body|base paint|livery|^paint$|(^| )base( |$)|base (coat|layer|colou?r)/.test(n)) return 'body paint';
        if (/logo|decal|banner|pitbox|windshield|sticker|badge/.test(n)) return 'decals / logos';
        return 'other art';
    }
    var ROLES_SIG = null, ROLES_OUT = null;
    function roles() {
        var sg = signature(); if (ROLES_SIG === sg && ROLES_OUT) return ROLES_OUT.map(function (r) { var o = {}; for (var k in r) o[k] = r[k]; o.visible = layerVisible(r.id); return o; });
        var out = layersArr().filter(function (l) { return l && l.img; }).map(function (l) { return { id: l.id, name: l.name, group: l.groupName || undefined, role: roleOf(l), visible: l.visible !== false, opacity: Math.round((l.opacity == null ? 255 : l.opacity) / 2.55), blend: (l.blendMode && l.blendMode !== 'source-over') ? l.blendMode : undefined }; });
        if (!out.some(function (r) { return r.role === 'body paint'; })) {      // nobody named the body layer ("Layer 16"): it is the BOTTOM-most art layer that covers a large part of the sheet
            for (var i = 0; i < out.length; i++) {
                if (out[i].role !== 'other art') continue;
                var l = layersArr().filter(function (x) { return x && x.id === out[i].id; })[0], g = l && layerAlphaGrid(l);
                if (g && g.frac > 0.3) { out[i].role = 'body paint'; out[i].guessed = true; break; }
            }
        }
        ROLES_SIG = sg; ROLES_OUT = out; return out.map(function (r) { var o = {}; for (var k in r) o[k] = r[k]; return o; });
    }
    function layerVisible(id) { var l = layersArr().filter(function (x) { return x && x.id === id; })[0]; return !l || l.visible !== false; }
    function bodyLayers() {
        var ids = roles().filter(function (r) { return r.role === 'body paint' && r.visible; }).map(function (r) { return r.id; });
        return layersArr().filter(function (l) { return l && l.img && ids.indexOf(l.id) !== -1; });
    }

    // ------------------------------------------------------------------ islands
    function signature() {
        var d = paintDims(), ls = layersArr().filter(function (l) { return l && l.img; }).map(function (l) { return l.name + ':' + (l.bbox ? [l.bbox.x || l.bbox[0] || 0, l.bbox.y || l.bbox[1] || 0, l.bbox.w || l.bbox.width || l.bbox[2] || 0, l.bbox.h || l.bbox.height || l.bbox[3] || 0].join(',') : ''); });
        var s = d[0] + 'x' + d[1] + '|' + ls.join('|'), h = 0; for (var i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
        return 'cm' + (h >>> 0).toString(36);
    }
    // alpha footprint of ONE layer at GRID x GRID, regardless of its visibility (template layers are usually hidden); bbox = [left, top, right, bottom] in canvas px
    function layerAlphaGrid(l) {
        try {
            var d = paintDims(), W = d[0], H = d[1], cv = document.createElement('canvas'); cv.width = cv.height = GRID; var cx = cv.getContext('2d', { willReadFrequently: true });
            var bb = l.bbox || [0, 0, l.img.width, l.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1];
            cx.drawImage(l.img, L * GRID / W, T * GRID / H, l.img.width * GRID / W, l.img.height * GRID / H);
            var px = cx.getImageData(0, 0, GRID, GRID).data, out = new Uint8Array(GRID * GRID), any = 0;
            for (var i = 0; i < GRID * GRID; i++) if (px[i * 4 + 3] > 40) { out[i] = 1; any++; }
            return { grid: out, frac: any / (GRID * GRID) };
        } catch (e) { return null; }
    }
    // The template's WIRE layer draws each UV island's outline in bright green (mesh lines are white/grey): those outlines are the real panel walls.
    function wallGrid() {
        var wl = null, ls = layersArr().filter(function (l) { return l && l.img; }), i;
        for (i = 0; i < ls.length; i++) if (/(^| )wire( |$)|wireframe|outline/.test(norm(ls[i].name))) { wl = ls[i]; break; }
        if (!wl) return null;
        try {
            var d = paintDims(), W = d[0], H = d[1], cv = document.createElement('canvas'); cv.width = W; cv.height = H; var cx = cv.getContext('2d', { willReadFrequently: true });
            var bb = wl.bbox || [0, 0, wl.img.width, wl.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1];
            cx.drawImage(wl.img, L, T);
            var px = cx.getImageData(0, 0, W, H).data, out = new Uint8Array(GRID * GRID), k = W / GRID, y, x, n = 0;
            for (y = 0; y < H; y++) { var row = y * W, gy = Math.floor(y / k) * GRID; for (x = 0; x < W; x++) { var o = (row + x) * 4; if (px[o + 3] > 120 && px[o + 1] > 140 && px[o] < 130 && px[o + 2] < 130 && px[o + 1] - px[o] > 60) { var gi = gy + Math.floor(x / k); if (!out[gi]) { out[gi] = 1; n++; } } }
            }
            return n > GRID * 0.5 ? out : null;
        } catch (e) { return null; }
    }
    // ---- raw Mask/Wire grids from the server, for PSDs whose imported Mask layer comes back empty (see server_routes/ai_car_routes.py)
    function maskLayerEmpty() {
        var ls = layersArr().filter(function (l) { return l && l.img; }), i, mk = null;
        for (i = 0; i < ls.length; i++) if (/(^| )mask( |$)/.test(norm(ls[i].name))) { mk = ls[i]; break; }
        if (!mk) return false; var g = layerAlphaGrid(mk); return !!(g && g.frac < 0.002);
    }
    function decodeGrid(b64) {
        return new Promise(function (res) {
            if (!b64) return res(null); var im = new Image(); im.onerror = function () { res(null); };
            im.onload = function () { try { var cv = document.createElement('canvas'); cv.width = cv.height = GRID; var cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(im, 0, 0, GRID, GRID); var d = cx.getImageData(0, 0, GRID, GRID).data, out = new Uint8Array(GRID * GRID), i; for (i = 0; i < GRID * GRID; i++) out[i] = d[i * 4] > 127 ? 1 : 0; res(out); } catch (e) { res(null); } };
            im.src = 'data:image/png;base64,' + b64;
        });
    }
    function prefetchServerMask(request) {
        var path = ''; try { path = (window.getCurrentSourcePaintFile && window.getCurrentSourcePaintFile()) || ((typeof _psdPath !== 'undefined' && _psdPath) ? _psdPath : ''); } catch (e) {}
        if (!currentSource(request)) return Promise.resolve();
        if (!path || !/\.psd$/i.test(path) || !maskLayerEmpty()) { SERVERMASK = null; return Promise.resolve(); }
        if (SERVERMASK && SERVERMASK.path === path && sameSource(SERVERMASK.source, request.source)) return Promise.resolve();
        SERVERMASK = null;
        return fetch((window.SPB_AI_BASE || '') + '/api/ai/template-mask?path=' + encodeURIComponent(path)).then(function (r) { return r.json(); }).then(function (j) {
            if (!currentSource(request)) return;
            if (!j || !j.ok || !j.found || !j.found.mask) { SERVERMASK = null; return; }
            return Promise.all([decodeGrid(j.mask), decodeGrid(j.wall)]).then(function (g) { if (currentSource(request)) SERVERMASK = g[0] ? { path: path, source: request.source, mask: g[0], wall: g[1] } : null; });
        }).catch(function () { if (currentSource(request)) SERVERMASK = null; });
    }
    function binaryGrid() {
        // 1) best source: the template MASK layer — opaque = not paintable, transparent = the paintable panels (islands are separated by the opaque borders)
        var ls = layersArr().filter(function (l) { return l && l.img; }), i, mk = null;
        for (i = 0; i < ls.length; i++) if (/(^| )mask( |$)/.test(norm(ls[i].name))) { mk = ls[i]; break; }
        if (mk) {
            var g = (SERVERMASK && maskLayerEmpty()) ? { grid: SERVERMASK.mask, frac: (function () { var n = 0, q; for (q = 0; q < SERVERMASK.mask.length; q++) n += SERVERMASK.mask[q]; return n / SERVERMASK.mask.length; })() } : layerAlphaGrid(mk);
            if (g) {
                var paintable = new Uint8Array(GRID * GRID), inv = g.frac < 0.12;     // a mask that is mostly transparent is drawn the other way round
                for (i = 0; i < GRID * GRID; i++) paintable[i] = (inv ? g.grid[i] : (g.grid[i] ? 0 : 1));
                var pf = 0; for (i = 0; i < GRID * GRID; i++) pf += paintable[i];
                if (pf / (GRID * GRID) > 0.08 && pf / (GRID * GRID) < 0.92) {
                    var wall = (SERVERMASK && SERVERMASK.wall && maskLayerEmpty()) ? SERVERMASK.wall : wallGrid(), seed = null, src = (SERVERMASK && maskLayerEmpty()) ? 'the template mask read from the PSD file' : 'the Mask layer (paintable area)';
                    if (wall) {      // walls = green outlines, thickened by one block on each side
                        var thick = new Uint8Array(GRID * GRID), yy, xx, ii;
                        for (yy = 1; yy < GRID - 1; yy++) for (xx = 1; xx < GRID - 1; xx++) { ii = yy * GRID + xx; if (wall[ii] || wall[ii - 1] || wall[ii + 1] || wall[ii - GRID] || wall[ii + GRID]) thick[ii] = 1; }
                        seed = new Uint8Array(GRID * GRID); for (ii = 0; ii < GRID * GRID; ii++) seed[ii] = (paintable[ii] && !thick[ii]) ? 1 : 0;
                        src = 'the Mask layer (paintable area) split by the Wire layer outlines';
                    }
                    return { bin: paintable, seed: seed, source: src, erode: !seed };
                }
            }
        }
        // 1b) a flat sheet that still shows the template's dead-space tone (or transparency): everything else is paintable
        var dz = deadSpaceGrid(); if (dz) return dz;
        // 2) fallback: the body-paint layer's footprint (only splits when panels are separated by empty space)
        var d = paintDims(), W = d[0], H = d[1], bl = bodyLayers(), union = null, used = '';
        if (bl.length && G('getZoneSourceLayersUnionMask')) {
            try { var r = G('getZoneSourceLayersUnionMask')({ sourceLayers: bl.map(function (l) { return l.id; }), sourceLayer: bl[0].id }, W, H); union = r && r.union; used = bl.map(function (l) { return l.name; }).join(', '); } catch (e) {}
        }
        var out = new Uint8Array(GRID * GRID), step = W / GRID, y, x, any = 0;
        if (union) {
            for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) { var sx = Math.floor((x + 0.5) * step), sy = Math.floor((y + 0.5) * step); if (union[sy * W + sx] > 40) { out[y * GRID + x] = 1; any++; } }
        }
        if (!any) return null;
        return { bin: out, source: used };
    }
    function label(bin, erode, seed) {
        var n = GRID * GRID, i, x, y, er = new Uint8Array(n);
        if (seed) { for (i = 0; i < n; i++) er[i] = seed[i]; erode = true; }
        else if (erode) {      // paintable panels: erode 2px so thin bridges split, label, then grow the labels back over the original paintable pixels
            var e1 = new Uint8Array(n), k;
            for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { i = y * GRID + x; if (bin[i] && bin[i - 1] && bin[i + 1] && bin[i - GRID] && bin[i + GRID]) e1[i] = 1; }
            for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { i = y * GRID + x; if (e1[i] && e1[i - 1] && e1[i + 1] && e1[i - GRID] && e1[i + GRID]) er[i] = 1; }
        } else {          // close 1px gaps (dilate then erode)
            var dil = new Uint8Array(n);
            for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { i = y * GRID + x; if (bin[i] || bin[i - 1] || bin[i + 1] || bin[i - GRID] || bin[i + GRID]) dil[i] = 1; }
            for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { i = y * GRID + x; if (dil[i] && dil[i - 1] && dil[i + 1] && dil[i - GRID] && dil[i + GRID]) er[i] = 1; }
            for (i = 0; i < n; i++) if (bin[i]) er[i] = 1;
        }
        var lab = new Int16Array(n), comps = [], cur = 0, stack = [];
        for (i = 0; i < n; i++) {
            if (!er[i] || lab[i]) continue;
            cur++; var minx = GRID, miny = GRID, maxx = 0, maxy = 0, area = 0, sx = 0, sy = 0; stack.length = 0; stack.push(i); lab[i] = cur;
            while (stack.length) {
                var p = stack.pop(), px = p % GRID, py = (p - px) / GRID; area++; sx += px; sy += py;
                if (px < minx) minx = px; if (px > maxx) maxx = px; if (py < miny) miny = py; if (py > maxy) maxy = py;
                if (px > 0 && er[p - 1] && !lab[p - 1]) { lab[p - 1] = cur; stack.push(p - 1); }
                if (px < GRID - 1 && er[p + 1] && !lab[p + 1]) { lab[p + 1] = cur; stack.push(p + 1); }
                if (py > 0 && er[p - GRID] && !lab[p - GRID]) { lab[p - GRID] = cur; stack.push(p - GRID); }
                if (py < GRID - 1 && er[p + GRID] && !lab[p + GRID]) { lab[p + GRID] = cur; stack.push(p + GRID); }
            }
            comps.push({ raw: cur, area: area, bbox: [minx / GRID, miny / GRID, (maxx + 1) / GRID, (maxy + 1) / GRID], cx: sx / area / GRID, cy: sy / area / GRID });
        }
        if (erode) {      // grow each label back over paintable pixels it touches
            for (var ring = 0; ring < (seed ? 4 : 3); ring++) {
                var nl = new Int16Array(lab);
                for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { i = y * GRID + x; if (!lab[i] && bin[i]) { var v = lab[i - 1] || lab[i + 1] || lab[i - GRID] || lab[i + GRID]; if (v) nl[i] = v; } }
                lab = nl;
            }
            comps.forEach(function (c) { c.area = 0; c.sx = 0; c.sy = 0; var mnx = GRID, mny = GRID, mxx = 0, mxy = 0; for (var q = 0; q < n; q++) if (lab[q] === c.raw) { var qx = q % GRID, qy = (q - qx) / GRID; c.area++; c.sx += qx; c.sy += qy; if (qx < mnx) mnx = qx; if (qx > mxx) mxx = qx; if (qy < mny) mny = qy; if (qy > mxy) mxy = qy; } if (c.area) { c.cx = c.sx / c.area / GRID; c.cy = c.sy / c.area / GRID; c.bbox = [mnx / GRID, mny / GRID, (mxx + 1) / GRID, (mxy + 1) / GRID]; } });
        }
        var minArea = n * 0.0035;
        comps = comps.filter(function (c) { return c.area >= minArea; });
        comps.sort(function (a, b) { return Math.abs(a.cy - b.cy) > 0.12 ? a.cy - b.cy : a.cx - b.cx; });
        var remap = {}; comps.forEach(function (c, k) { c.id = 'I' + (k + 1); c.share_pct = Math.round(c.area / n * 1000) / 10; c.cells = cellsOf(c.bbox); c.w = c.bbox[2] - c.bbox[0]; c.h = c.bbox[3] - c.bbox[1]; remap[c.raw] = k + 1; });
        var out = new Uint8Array(n); for (i = 0; i < n; i++) out[i] = lab[i] ? (remap[lab[i]] || 0) : 0;
        return { comps: comps, map: out };
    }

    // Wire layers drawn as a dense all-green mesh (Gen 6 / ARCA templates) make every mesh line a 'wall' and shatter the panels: if the wall-split keeps < 70% of the
    // paintable area, split by eroding thin bridges instead
    function labelBest(bg) {
        var ci = label(bg.bin, !!bg.erode, bg.seed);
        if (bg.seed) {
            var tot = 0, got = 0, i; for (i = 0; i < bg.bin.length; i++) tot += bg.bin[i]; ci.comps.forEach(function (c) { got += c.area; });
            if (tot && got / tot < 0.7) { var c2 = label(bg.bin, true, null), got2 = 0; c2.comps.forEach(function (c) { got2 += c.area; }); if (got2 > got) { c2.fallback = true; return c2; } }
        }
        return ci;
    }
    // ------------------------------------------------------------------ overlay image for the vision model
    function overlayImage(ci, minShare) {
        try {
            var src = document.getElementById('paintCanvas'); if (!src || src.width < 64) return null;
            var n = 768, cv = document.createElement('canvas'); cv.width = cv.height = n; var cx = cv.getContext('2d');
            cx.fillStyle = '#202028'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high';
            var tl = layersArr().filter(function (l) { return l && l.img && /(^| )(mask|wire|wireframe|mandatory)( |$)|car mandatory/.test(norm(l.name)); }), dW = paintDims()[0], dH = paintDims()[1];
            if (tl.length >= 2) { tl.sort(function (a, b) { return (/mask/.test(norm(a.name)) ? 0 : 1) - (/mask/.test(norm(b.name)) ? 0 : 1); }); tl.forEach(function (l) { var bb = l.bbox || [0, 0, l.img.width, l.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1]; cx.drawImage(l.img, L * n / dW, T * n / dH, l.img.width * n / dW, l.img.height * n / dH); }); }
            else cx.drawImage(src, 0, 0, n, n);
            var k = n / GRID, map = ci.map, y, x;
            cx.strokeStyle = '#ff2bd6'; cx.lineWidth = 2;
            cx.beginPath();
            for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { var v = map[y * GRID + x]; if (v && (map[y * GRID + x - 1] !== v || map[y * GRID + x + 1] !== v || map[(y - 1) * GRID + x] !== v || map[(y + 1) * GRID + x] !== v)) { cx.rect(x * k, y * k, k, k); } }
            cx.stroke();
            cx.font = 'bold 30px sans-serif'; cx.textBaseline = 'middle'; cx.textAlign = 'center';
            ci.comps.forEach(function (c) { if (minShare && c.share_pct < minShare) return; var tx = c.cx * n, ty = c.cy * n; cx.fillStyle = 'rgba(0,0,0,0.78)'; cx.fillRect(tx - 28, ty - 18, 56, 36); cx.fillStyle = '#ffe680'; cx.fillText(c.id, tx, ty + 1); });
            return cv.toDataURL('image/jpeg', 0.8);
        } catch (e) { return null; }
    }
    function overlayTemplate(cx, n) {
        var dW = paintDims()[0], dH = paintDims()[1];
        layersArr().forEach(function (l) {
            if (!l || !l.img) return; var nm = norm(l.name), isMask = /(^| )mask( |$)/.test(nm), isWire = /(^| )wire( |$)|wireframe/.test(nm); if (!isMask && !isWire) return;
            var bb = l.bbox || [0, 0, l.img.width, l.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1];
            cx.save(); cx.globalAlpha = isMask ? 0.9 : 0.5; cx.drawImage(l.img, L * n / dW, T * n / dH, l.img.width * n / dW, l.img.height * n / dH); cx.restore();
        });
    }
    function templateBase(n) {
        var cv = document.createElement('canvas'); cv.width = cv.height = n; var cx = cv.getContext('2d'), dW = paintDims()[0], dH = paintDims()[1];
        cx.fillStyle = '#202028'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high';
        var tl = layersArr().filter(function (l) { return l && l.img && /(^| )(mask|wire|wireframe|mandatory)( |$)|car mandatory/.test(norm(l.name)); });
        if (tl.length >= 2) { tl.sort(function (a, b) { return (/mask/.test(norm(a.name)) ? 0 : 1) - (/mask/.test(norm(b.name)) ? 0 : 1); }); tl.forEach(function (l) { var bb = l.bbox || [0, 0, l.img.width, l.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1]; cx.drawImage(l.img, L * n / dW, T * n / dH, l.img.width * n / dW, l.img.height * n / dH); }); }
        else cx.drawImage(document.getElementById('paintCanvas'), 0, 0, n, n);
        return cv;
    }
    function locatorImage(ci, comp, n) {
        var cv = templateBase(n), cx = cv.getContext('2d'), k = n / GRID, map = ci.map, id = Number(comp.id.substr(1)), y, x;
        cx.fillStyle = 'rgba(255,43,214,0.55)';
        for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) if (map[y * GRID + x] === id) cx.fillRect(x * k, y * k, k + 0.5, k + 0.5);
        return cv.toDataURL('image/jpeg', 0.78);
    }
    // ONE contact-sheet image: a grid of small template pictures, each with ONE island filled magenta and its id in the corner
    function locatorSheet(ci, comps) {
        var cell = 300, cols = 4, rows = Math.ceil(comps.length / cols), sheet = document.createElement('canvas'); sheet.width = cols * cell; sheet.height = rows * cell;
        var sx = sheet.getContext('2d'); sx.fillStyle = '#000'; sx.fillRect(0, 0, sheet.width, sheet.height);
        var base = templateBase(cell), k = cell / GRID, map = ci.map;
        comps.forEach(function (c, i) {
            var ox = (i % cols) * cell, oy = Math.floor(i / cols) * cell, id = Number(c.id.substr(1)), y, x;
            sx.drawImage(base, ox, oy);
            sx.fillStyle = 'rgba(255,43,214,0.62)';
            for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) if (map[y * GRID + x] === id) sx.fillRect(ox + x * k, oy + y * k, k + 0.5, k + 0.5);
            sx.strokeStyle = '#fff'; sx.lineWidth = 2; sx.strokeRect(ox + 1, oy + 1, cell - 2, cell - 2);
            sx.fillStyle = 'rgba(0,0,0,0.85)'; sx.fillRect(ox + 4, oy + 4, 62, 34); sx.fillStyle = '#ffe680'; sx.font = 'bold 26px sans-serif'; sx.textBaseline = 'middle'; sx.fillText(c.id, ox + 10, oy + 22);
        });
        return sheet.toDataURL('image/jpeg', 0.8);
    }
    var LOCATE_PROMPT = 'The picture is a contact sheet. Every cell shows the same flat UNWRAPPED template of ONE race car (a UV sheet: dark shapes with green outlines are paintable body panels, brown is not paintable) with ONE panel filled MAGENTA and its id (I6 ...) in the corner. Identify the magenta panel in each cell. Clues: a BODY SIDE is a long horizontal panel with semi-circular wheel-arch cut-outs (normally two, one per car side; one may be upside-down on the sheet); red lamp shapes = tail lights = the REAR end; headlights + grille = the FRONT end; HOOD = large curved panel next to the windshield/fenders; ROOF = panel with windshield/rear-glass shapes; TRUCK BED / trunk = big flat rear panel; small strips = rockers, splitters, spoilers, mirrors, wheels, handles. For each cell give the part name (one of: "left side", "right side", "hood", "roof", "trunk or bed", "front bumper", "rear bumper", "tailgate", "windshield", "spoiler", "door", "fender", "rocker", "mirror", "wheel", "unknown") and which END of the magenta panel is the FRONT of the car ("left", "right", "top" or "bottom" edge as drawn). Answer with ONLY a JSON array: [{"id":"I6","name":"left side","front":"right"}, ...].';
    function labelLocators(model, minShare) {
        if (!LASTCI) return Promise.resolve({ error: 'no islands yet' });
        var comps = LASTCI.comps.filter(function (c) { return c.share_pct >= (minShare || 1.2); }), t0 = Date.now();
        var img = locatorSheet(LASTCI, comps);
        return window.SpbAI.chat({ messages: [{ role: 'user', content: [{ type: 'text', text: LOCATE_PROMPT }, { type: 'image_url', image_url: { url: img } }] }], max_tokens: 1200, temperature: 0.1, vision: true, model: model, reasoning: { enabled: false } }).then(function (r) {
            return { model: model, ok: !!(r && r.ok), ms: Date.now() - t0, cost: r && r.usage ? r.usage.cost : 0, n: comps.length, labels: r && r.ok ? parseLabels(r.message && r.message.content) : null, raw: r && r.ok ? String(r.message && r.message.content || '').slice(0, 600) : (r && (r.message || r.error)) };
        });
    }
    var LABEL_PROMPT = 'This is the flat, UNWRAPPED template of ONE race car (a UV sheet): dark shapes with green outlines are the paintable body panels (islands), brown is not paintable. The numbered boxes (I1, I2, ...) mark the islands. For EACH numbered island say what car part it is and which END of the island is the FRONT of the car ("left", "right", "top" or "bottom" edge as drawn). Clues: a BODY SIDE is a long horizontal panel with semi-circular wheel-arch cut-outs (there are normally two, one per side of the car; one may be upside-down on the sheet); red lamp shapes = tail lights (REAR end); headlights + grille = FRONT end; the HOOD is a large curved panel next to the windshield/fenders; the ROOF is a large panel with windshield and rear-glass shapes; TRUCK BED / trunk / rear deck is a big flat panel at the rear; small strips are rocker panels, splitters, spoilers, mirrors, wheels or door handles. Name parts as: "driver side" / "passenger side" / "left side" / "right side", "hood", "roof", "trunk or bed", "front bumper", "rear bumper", "tailgate", "windshield", "spoiler", "door", "fender", "rocker", "mirror", "wheel", or "unknown". Answer with ONLY a JSON array like [{"id":"I1","name":"left side","front":"right"}], no other text.';
    function parseLabels(text) {
        var m = /\[[\s\S]*\]/.exec(String(text || '')); if (!m) return null;
        try { var a = JSON.parse(m[0]); if (!Array.isArray(a)) return null; var out = {}; a.forEach(function (e) { if (e && e.id) out[String(e.id).toUpperCase()] = { name: String(e.name || 'unknown').toLowerCase().slice(0, 40), front: (/^(left|right|top|bottom)$/i.test(e.front || '') ? String(e.front).toLowerCase() : null) }; }); return out; } catch (e) { return null; }
    }
    function loadCache() { try { return JSON.parse(window.localStorage.getItem(LS) || '{}'); } catch (e) { return {}; } }
    function sigEntry(sig) { var e = loadCache()[sig]; if (!e) return { l: null, b: {} }; if (e.l || e.b) return { l: e.l || null, b: e.b || {} }; return { l: e, b: {} }; }
    function saveCache(sig, labels, boxes) { try { var c = loadCache(), cur = sigEntry(sig); c[sig] = { l: labels != null ? labels : cur.l, b: boxes != null ? boxes : cur.b, ls: (CACHE && CACHE.layoutSig) || (c[sig] && c[sig].ls) || null }; var keys = Object.keys(c); if (keys.length > 16) delete c[keys[0]]; window.localStorage.setItem(LS, JSON.stringify(c)); } catch (e) {} }

    // ------------------------------------------------------------------ PARTS: dead-space detection, layout fingerprint, car library, names
    var PART_ALIASES = {
        'left side': ['left side', 'left', 'driver side', 'drivers side', 'driver', 'left door', 'left flank', 'left quarter', 'left doors'],
        'right side': ['right side', 'right', 'passenger side', 'passengers side', 'passenger', 'right door', 'right flank', 'right quarter', 'right doors'],
        'hood': ['hood', 'bonnet', 'engine hood', 'hood panel'],
        'roof': ['roof', 'roof panel', 'top of the car', 'cab roof'],
        'trunk': ['trunk', 'trunk lid', 'deck lid', 'decklid', 'rear deck', 'boot', 'trunk deck'],
        'bed': ['bed', 'truck bed', 'cargo bed', 'pickup bed'],
        'front bumper': ['front bumper', 'nose', 'front fascia', 'front end', 'front', 'front valance', 'front clip', 'nose piece'],
        'rear bumper': ['rear bumper', 'tail', 'rear fascia', 'rear end', 'rear', 'rear valance', 'tail end', 'tail piece'],
        'spoiler': ['spoiler', 'wing', 'rear wing', 'rear spoiler'],
        'windshield': ['windshield', 'windscreen', 'front glass', 'a pillar'],
        'rear window': ['rear window', 'back glass', 'rear glass']
    };
    function canonPart(ref) { var q = norm(ref), k; for (k in PART_ALIASES) { if (PART_ALIASES.hasOwnProperty(k) && PART_ALIASES[k].indexOf(q) !== -1) return k; } return q; }
    // The flat sheet may still show the template's dead-space: the standard brownish tone, or transparency. Returns the same shape as binaryGrid's other sources.
    function deadSpaceGrid() {
        try {
            var src = document.getElementById('paintCanvas'); if (!src || src.width < 64) return null;
            var cv = document.createElement('canvas'); cv.width = cv.height = GRID; var cx = cv.getContext('2d', { willReadFrequently: true }); cx.imageSmoothingEnabled = false; cx.drawImage(src, 0, 0, GRID, GRID);
            var px = cx.getImageData(0, 0, GRID, GRID).data, n = GRID * GRID, i, trans = 0, dead = new Uint8Array(n), nd = 0;
            for (i = 0; i < n; i++) if (px[i * 4 + 3] < 40) trans++;
            if (trans > n * 0.08 && trans < n * 0.6) { for (i = 0; i < n; i++) if (px[i * 4 + 3] < 40) { dead[i] = 1; nd++; } }
            else {
                var hist = {}, best = null, bestN = 0, k;
                for (i = 0; i < n; i += 3) { var r = px[i * 4], g = px[i * 4 + 1], b = px[i * 4 + 2]; if (r > 150 || r < g || g < b || r - b < 8 || r - b > 45) continue; k = (r >> 3) + ',' + (g >> 3) + ',' + (b >> 3); hist[k] = (hist[k] || 0) + 1; if (hist[k] > bestN) { bestN = hist[k]; best = k; } }
                if (!best || bestN * 3 < n * 0.08) return null;
                var c = best.split(',').map(function (v) { return Number(v) * 8 + 4; });
                for (i = 0; i < n; i++) if (Math.abs(px[i * 4] - c[0]) <= 20 && Math.abs(px[i * 4 + 1] - c[1]) <= 20 && Math.abs(px[i * 4 + 2] - c[2]) <= 20) { dead[i] = 1; nd++; }
                if (nd < n * 0.08 || nd > n * 0.65) return null;
            }
            var paint = new Uint8Array(n); for (i = 0; i < n; i++) paint[i] = dead[i] ? 0 : 1;
            return { bin: paint, seed: null, source: 'the dead-space tone of the paint file', erode: true };
        } catch (e) { return null; }
    }
    // 32x32 fingerprint of the paintable area (256 hex chars); same car template -> near-identical bits regardless of the livery
    var POP = [0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4];
    function layoutSigOf(paint) {
        if (!paint) return null; var out = '', by, bx, y, x, n, bits = 0, nb = 0;
        for (by = 0; by < 32; by++) for (bx = 0; bx < 32; bx++) {
            n = 0; for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) if (paint[(by * 8 + y) * GRID + bx * 8 + x]) n++;
            bits = (bits << 1) | (n >= 32 ? 1 : 0); nb++; if (nb === 4) { out += bits.toString(16); bits = 0; nb = 0; }
        }
        return out;
    }
    function sigSim(a, b) {
        if (!a || !b || a.length !== b.length) return 0; var inter = 0, uni = 0, i;
        for (i = 0; i < a.length; i++) { var x = parseInt(a.charAt(i), 16), y = parseInt(b.charAt(i), 16); inter += POP[x & y]; uni += POP[x | y]; }
        return uni ? inter / uni : 0;
    }
    function folderKey() {
        try {
            var v = String((document.getElementById('outputDir') || {}).value || '').replace(/[\\\/]+$/, ''), segs = v.split(/[\\\/]/), seg = segs.pop() || '';
            if (/\.(tga|png|psd|jpg)$/i.test(seg)) seg = segs.pop() || '';
            return seg.toLowerCase().replace(/[^a-z0-9]+/g, '');
        } catch (e) { return ''; }
    }
    function sigUsable(sig) { if (!sig) return false; var n = 0, i; for (i = 0; i < sig.length; i++) n += POP[parseInt(sig.charAt(i), 16)]; return n > 1024 * 0.12 && n < 1024 * 0.93; }
    // ---- which car is this paint?  js/spb-car-edge.js reads the panel outlines every paint of one car shares (about 7 in 10 real paints have no template dead-space left, so the layout
    // fingerprint above has nothing to read there). A recognition nothing else corroborates is only ever a PROPOSAL (10% of paints of cars the model never saw are wrongly accepted).
    var CURREC = null, REC_CONF = 'spb_rec_confirm_v1';
    function nk(f) { return String(f || '').toLowerCase().replace(/[^a-z0-9]+/g, ''); }
    // DRAFT library entries (guess: true = worked out from the template's own guides by an assistant, never confirmed by a person) are only ever a confirm-first PROPOSAL until a buyer says yes once
    function guessConfirmed() { try { return JSON.parse(localStorage.getItem('spb_guess_confirm_v1') || '{}') || {}; } catch (e) { return {}; } }
    function recConfirmed() { try { return JSON.parse(localStorage.getItem(REC_CONF) || '{}') || {}; } catch (e) { return {}; } }
    function recognizeCar() { try { var cv = document.getElementById('paintCanvas'); if (!cv || cv.width < 64 || !window.SpbCarEdge) return null; return window.SpbCarEdge.recognize(cv); } catch (e) { return null; } }
    function effFolderKey() {      // the iRacing folder box, or - when it is empty or stale - the car the paint itself says it is
        var f = folderKey(), r = CURREC; if (!r || !r.known || (CACHE && sigUsable(CACHE.layoutSig))) return f; if (!f) return r.key; if (r.twins.indexOf(f) !== -1) return f; return r.z >= 6 ? r.key : f;
    }
    function recCarMatch(c) { var r = CURREC; return !!(r && r.known && (c.folders || []).some(function (f) { return r.twins.indexOf(nk(f)) !== -1; })); }
    function recOk(c, sim) {       // recognised AND corroborated: the folder box agrees, somebody taught this car here, or the buyer already confirmed it once (a look-alike layout alone is a PROPOSAL)
        if (!recCarMatch(c)) return false; var f = folderKey(), conf = recConfirmed();
        return (!!c.learned && (!c.guess || !!guessConfirmed()[c.id])) || (!!f && CURREC.twins.indexOf(f) !== -1 && (!c.guess || !!guessConfirmed()[c.id])) || conf[CURREC.fam] === c.id;
    }
    function atlasMatch(sig) {
        var A = window.SPB_CAR_ATLAS; if (!A || !A.cars) return null; var fk = folderKey(), best = null; if (!sigUsable(sig)) sig = null;
        A.cars.forEach(function (c) {
            var sim = 0; if (sig) (c.sigs || (c.sig ? [c.sig] : [])).forEach(function (cs) { var v = sigSim(sig, cs); if (v > sim) sim = v; });
            var byFolder = !!(fk && (c.folders || []).some(function (f) { return fk === String(f).toLowerCase().replace(/[^a-z0-9]+/g, ''); }));
            var hasSigs = (c.sigs && c.sigs.length) || c.sig;      // the folder box keeps its last value when the buyer opens another car: it only counts with matching layout evidence, or for a car that has no fingerprint (folder_only)
            var viaRec = !sig && recOk(c, sim), ok = sim >= 0.9 || (byFolder && sim >= 0.8) || (byFolder && !sig && (!hasSigs || c.folder_only)) || viaRec;
            if (ok) { var sc = sim + (byFolder ? 0.1 : 0) + (viaRec ? 0.05 : 0); if (!best || sc > best.score) best = { car: c, score: sc, sim: sim, folder: byFolder, rec: viaRec && sim < 0.9 && !byFolder }; }
        });
        return best;
    }
    // taught parts are stored per layer-signature AND per layout fingerprint, so another PSD of the same car template finds them too
    function findTaught(sig, ls) {
        var all = loadCache(), e = all[sig], best = null, bs = 0;
        if (e && (e.b && Object.keys(e.b).length)) return e.b;
        if (ls) Object.keys(all).forEach(function (k) { var x = all[k]; if (x && x.ls && x.b && Object.keys(x.b).length) { var sm = sigSim(ls, x.ls); if (sm >= 0.92 && sm > bs) { bs = sm; best = x.b; } } });
        return best || {};
    }
    function withParts(m) {
        m.layoutSig = m.tpl ? null : layoutSigOf(PAINT);
        CURREC = recognizeCar(); m.rec = CURREC ? { name: CURREC.name, key: CURREC.key, fam: CURREC.fam, z: Math.round(CURREC.z * 10) / 10, known: CURREC.known, twins: CURREC.twins } : null;
        var hit = atlasMatch(m.layoutSig), lib = {}, merged = {}, taught = findTaught(m.sig, m.layoutSig), guessHit = null;
        if (hit && hit.car.guess && !guessConfirmed()[hit.car.id]) { guessHit = hit; hit = null; }       // a draft entry is a proposal, not knowledge
        if (hit) {
            var P = hit.car.parts || {};
            Object.keys(P).forEach(function (nm) { var p = P[nm]; if (p && p.box && p.box.length === 4) lib[nm] = { bbox: p.box.slice(), front: p.front || null, up: p.up || null, lib: !hit.car.learned }; });
            m.lib = { id: hit.car.id, name: hit.car.name, score: Math.round(hit.score * 100) / 100, by: hit.rec ? 'the panel outlines in your paint' : (hit.folder ? (hit.sim >= 0.9 ? 'layout + iRacing folder' : 'iRacing folder') : 'layout') };
        }
        m.libBoxes = lib;
        m.near = null; if (!hit) {
            var nr = null, rcCar = null; if (CURREC && CURREC.known && window.SPB_CAR_ATLAS) window.SPB_CAR_ATLAS.cars.forEach(function (c) { if (!rcCar && recCarMatch(c) && Object.keys(c.parts || {}).length >= 3) rcCar = c; });
            nr = atlasNear(m.layoutSig); if (!nr && guessHit) nr = { car: guessHit.car, sim: 0.8, rec: null }; if (!nr && rcCar) nr = { car: rcCar, sim: Math.min(0.99, 0.78 + Math.max(0, CURREC.z - 4) / 100), rec: { name: CURREC.name, z: Math.round(CURREC.z * 10) / 10, fam: CURREC.fam } };
            if (nr) { var nb = {}; Object.keys(nr.car.parts || {}).forEach(function (nm) { var q = nr.car.parts[nm]; if (q && q.box && q.box.length === 4) nb[nm] = { bbox: snapBox(q.box.slice()), front: q.front || null, up: q.up || null }; }); m.near = { id: nr.car.id, name: nr.car.name, sim: Math.round(nr.sim * 100) / 100, boxes: nb, rec: nr.rec || null, guess: !!(nr.car && nr.car.guess) }; } }
        Object.keys(lib).forEach(function (k) { merged[k] = lib[k]; });
        Object.keys(taught).forEach(function (k) { var t = taught[k]; if (t && t.bbox) merged[canonPart(k) === k ? k : k] = { bbox: t.bbox, front: t.front || null, up: t.up || null, taught: true }; });
        // a taught part replaces the library part of the same canonical name
        Object.keys(merged).forEach(function (k) { if (merged[k].lib) { Object.keys(taught).forEach(function (t) { if (canonPart(t) === canonPart(k) && t !== k) delete merged[k]; }); } });
        m.boxes = merged;
        return m;
    }
    function knownPartNames() {
        var out = {}; if (!CACHE) return [];
        (CACHE.islands || []).forEach(function (i) { if (i.confirmed && i.name) out[canonPart(i.name)] = 1; });
        Object.keys(CACHE.boxes || {}).forEach(function (k) { out[canonPart(k)] = 1; });
        return Object.keys(out);
    }
    // MCPSCEN 2026-10-05 (MCP run on the Chevy truck PSD: status said key_parts_missing ["trunk"] although the truck's BED is known, so an AI following the
    // instructions would ask the buyer to mark a part that does not exist): on a truck the bed / tailgate stands in for the trunk.
    function missingParts(names) { var have = knownPartNames(); return (names || []).filter(function (n) { var c = canonPart(n); if (have.indexOf(c) !== -1) return false; if (c === 'trunk' && have.some(function (h) { return /\b(bed|tailgate|deck)\b/.test(String(h)); })) return false; return true; }); }

    // ------------------------------------------------------------------ build / ensure
    // ------------------------------------------------------------------ LEARNING (SPB-AI 2026-10-02): the app learns every car it is shown
    // learned layouts live on the server (GET/POST /api/ai/learned-cars, %APPDATA%/ShokkerPaintBooth/ai/learned_cars.json) and are merged into window.SPB_CAR_ATLAS here, so a car
    // the buyer (or the team) taught once is simply KNOWN the next time its layout / iRacing folder shows up. A layout the library does not know but that is close to a known car
    // (>= NEAR_MIN similar) gets that car's parts as a PROPOSAL the buyer confirms with one click (never applied silently: a wrong guess paints the wrong panel).
    var NEAR_MIN = 0.78, LEARNED_P = null;
    function loadLearned() {
        if (LEARNED_P) return LEARNED_P;
        LEARNED_P = fetch((window.SPB_AI_BASE || '') + '/api/ai/learned-cars').then(function (r) { return r.json(); }).then(function (j) {
            if (!j || !j.ok || !j.cars) return 0;
            var A = window.SPB_CAR_ATLAS = window.SPB_CAR_ATLAS || { v: 1, cars: [] }; A.cars = (A.cars || []).filter(function (c) { return !c.serverLearned; });      // only the entries THIS machine's server added are refreshed: learned / owner / draft entries shipped inside the atlas stay
            j.cars.forEach(function (c) { if (c && c.parts && Object.keys(c.parts).length) A.cars.push({ id: c.id, name: c.name, folders: c.folders || [], sigs: c.sigs || [], parts: c.parts, learned: true, serverLearned: true, folder_only: !(c.sigs && c.sigs.length) }); });
            return j.cars.length;
        }).catch(function () { return 0; });
        return LEARNED_P;
    }
    function atlasNear(sig) {
        var A = window.SPB_CAR_ATLAS; if (!A || !A.cars || !sigUsable(sig)) return null; var best = null;
        A.cars.forEach(function (c) { var sim = 0; (c.sigs || (c.sig ? [c.sig] : [])).forEach(function (cs) { var v = sigSim(sig, cs); if (v > sim) sim = v; }); if (sim >= NEAR_MIN && Object.keys(c.parts || {}).length >= 3 && (!best || sim > best.sim)) best = { car: c, sim: sim }; });
        return best;
    }
    function learnPost(source) {
        try {
            var ex = exportTaught(); if (!ex) return Promise.resolve(false);
            var psd = ''; try { psd = String((window.getCurrentSourcePaintFile && window.getCurrentSourcePaintFile()) || ((typeof _psdPath !== 'undefined' && _psdPath) ? _psdPath : '')).split(/[\\\/]/).pop(); } catch (e0) {}
            var psdBase = psd.replace(/\.[a-z0-9]+$/i, '').replace(/[\s_-]*(psd|template|tpl)$/i, '').trim(), nearName = CACHE && CACHE.near && CACHE.near.name;
            // a layout adopted from a SIMILAR car is a new car of its own: name it after the sheet it came from, not after the look-alike
            var carName = /^adopted-near/.test(String(source)) && nearName ? ((psdBase || (ex.folder ? String(ex.folder).split(/[\\\/]/).pop() : '')) ? (psdBase || String(ex.folder).split(/[\\\/]/).pop()) + ' (layout like ' + nearName + ')' : nearName) : (ex.car || (CACHE && CACHE.rec && CACHE.rec.known ? CACHE.rec.name : null) || nearName || psd || null);
            var body = { source: source || 'taught', car: carName, folder: ex.folder, layoutSig: ex.layoutSig, sheet: ex.sheet, parts: ex.parts, psdName: psd || null };
            return fetch((window.SPB_AI_BASE || '') + '/api/ai/learned-cars', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) { return r.json(); }).then(function (j) { LEARNED_P = null; return !!(j && j.ok); }).catch(function () { return false; });
        } catch (e) { return Promise.resolve(false); }
    }
    // ------------------------------------------------------------------ iRacing 3D-viewer calibration
    // Vision cannot read the flat UV sheet, but it reads a 3D car with coloured panels easily. So: every big island of THIS sheet gets its own flat colour, that sheet goes into the car's iRacing paint folder
    // (scripts/ai_atlas/viewer_session.py), somebody looks at the car in iRacing's paint viewer and says "orange = hood, blue = roof ...", and viewerFindings() turns that into learned boxes for this layout.
    var CAL_COLOURS = [['red', '#e6194b'], ['orange', '#f58231'], ['yellow', '#ffe119'], ['lime', '#bfef45'], ['green', '#3cb44b'], ['cyan', '#42d4f4'], ['blue', '#4363d8'], ['purple', '#911eb4'], ['magenta', '#f032e6'], ['pink', '#fabed4'], ['white', '#ffffff'], ['brown', '#9a6324'], ['teal', '#469990'], ['navy', '#000075']], LASTCAL = null;
    function calibrationSheet(size, page) {
        if (!CACHE || !MASKS || !CACHE.islands || !CACHE.islands.length) return null;
        size = size || paintDims()[0]; page = Math.max(0, page | 0); var cv = document.createElement('canvas'); cv.width = cv.height = size; var g = cv.getContext('2d'), cell = size / GRID, x, y, v, c, key = {};
        g.fillStyle = '#1b1b1b'; g.fillRect(0, 0, size, size);
        var big = CACHE.islands.slice().sort(function (a, b) { return (b.share_pct || 0) - (a.share_pct || 0); }).slice(page * CAL_COLOURS.length, (page + 1) * CAL_COLOURS.length);
        if (!big.length) return null;
        big.forEach(function (i, k) { key[i.id] = CAL_COLOURS[k]; });
        for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) { v = MASKS[y * GRID + x]; if (!v) continue; c = key['I' + v]; g.fillStyle = c ? c[1] : '#4a4a4a'; g.fillRect(Math.floor(x * cell), Math.floor(y * cell), Math.ceil(cell) + 1, Math.ceil(cell) + 1); }
        var psd = ''; try { psd = String((window.getCurrentSourcePaintFile && window.getCurrentSourcePaintFile()) || ((typeof _psdPath !== 'undefined' && _psdPath) ? _psdPath : '')).split(/[\\\/]/).pop(); } catch (e0) {}
        LASTCAL = { canvas: cv, legend: big.map(function (i) { return { id: i.id, colour: key[i.id][0], hex: key[i.id][1], bbox: i.bbox, share_pct: i.share_pct }; }), page: page, pages: Math.ceil(CACHE.islands.length / CAL_COLOURS.length), unnamed_islands: Math.max(0, CACHE.islands.length - (page + 1) * CAL_COLOURS.length), layoutSig: CACHE.layoutSig || null, folder: folderKey() || null, psdName: psd || null, sheet: paintDims() };
        return LASTCAL;
    }
    // found: { orange: 'hood', blue: ['left side'], ... } (colour names from the legend; several colours may make one part) -> a box per part = the union of its islands; learned with source 'viewer'
    function viewerFindings(found, cal) {
        cal = cal || LASTCAL; if (!cal || !found) return 0; var per = {}, n = 0;
        Object.keys(found).forEach(function (cn) {
            var L = null; cal.legend.forEach(function (l) { if (l.colour === String(cn).toLowerCase()) L = l; }); if (!L) return;
            [].concat(found[cn]).forEach(function (nm) { var k = canonPart(nm); if (!k) return; var u = per[k] || (per[k] = [1, 1, 0, 0]); u[0] = Math.min(u[0], L.bbox[0]); u[1] = Math.min(u[1], L.bbox[1]); u[2] = Math.max(u[2], L.bbox[2]); u[3] = Math.max(u[3], L.bbox[3]); });
        });
        Object.keys(per).forEach(function (k) { var u = per[k]; if (u[2] > u[0] && u[3] > u[1] && setBox(k, [Math.max(0, u[0] - 0.004), Math.max(0, u[1] - 0.004), Math.min(1, u[2] + 0.004), Math.min(1, u[3] + 0.004)], null, null)) n++; });
        if (n) learnPost('viewer');
        return n;
    }
    function nearInfo() { return CACHE && CACHE.near ? { id: CACHE.near.id, name: CACHE.near.name, sim: CACHE.near.sim, rec: CACHE.near.rec || null, guess: !!CACHE.near.guess, parts: Object.keys(CACHE.near.boxes || {}), boxes: CACHE.near.boxes || {} } : null; }
    function snapBox(box) {
        if (!MASKS || !CACHE || !CACHE.islands) return box;
        var gx0 = Math.floor(box[0] * GRID), gx1 = Math.ceil(box[2] * GRID), gy0 = Math.floor(box[1] * GRID), gy1 = Math.ceil(box[3] * GRID), tot = {}, inn = {}, x, y, v;
        for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) { v = MASKS[y * GRID + x]; if (!v) continue; tot[v] = (tot[v] || 0) + 1; if (x >= gx0 && x < gx1 && y >= gy0 && y < gy1) inn[v] = (inn[v] || 0) + 1; }
        var ids = [], kept = 0, inBox = 0; Object.keys(inn).forEach(function (k) { inBox += inn[k]; if (inn[k] / tot[k] >= 0.55) { ids.push('I' + k); kept += inn[k]; } });
        if (!ids.length || !inBox || kept / inBox < 0.6) return box;
        var u = [1, 1, 0, 0]; CACHE.islands.forEach(function (i) { if (ids.indexOf(i.id) !== -1 && i.bbox) { u[0] = Math.min(u[0], i.bbox[0]); u[1] = Math.min(u[1], i.bbox[1]); u[2] = Math.max(u[2], i.bbox[2]); u[3] = Math.max(u[3], i.bbox[3]); } });
        return (u[2] > u[0] && u[3] > u[1]) ? [Math.max(0, u[0] - 0.004), Math.max(0, u[1] - 0.004), Math.min(1, u[2] + 0.004), Math.min(1, u[3] + 0.004)] : box;
    }
    function adoptNear() {
        if (!CACHE || !CACHE.near) return 0; var n = 0, P = CACHE.near.boxes || {};
        Object.keys(P).forEach(function (nm) { var b = P[nm]; if (setBox(nm, b.bbox, b.front || null, b.up || null)) n++; });
        if (n) {
            CACHE.near.adopted = true;
            if (CACHE.near.guess) { try { var gcf = guessConfirmed(); gcf[CACHE.near.id] = 1; localStorage.setItem('spb_guess_confirm_v1', JSON.stringify(gcf)); } catch (eg) {} }       // the buyer confirmed this draft: it is knowledge from now on
            if (CACHE.near.rec && CACHE.near.rec.fam) { try { var cf = recConfirmed(); cf[CACHE.near.rec.fam] = CACHE.near.id; localStorage.setItem(REC_CONF, JSON.stringify(cf)); } catch (er) {} }   // this car is now known by its outlines: the next paint of it needs no question
            else learnPost('adopted-near:' + CACHE.near.id);
        }
        return n;
    }
    function build0(withLabels, request) { return prefetchServerMask(request).then(loadLearned).then(function () { return currentSource(request) ? build00(withLabels, request) : null; }); }
    function noMask(m, request) { m.note = 'flat paint file (no template mask): panels are not detected; the buyer can drag a rectangle around a named part once (point_at)'; if (publishCache(m, request)) MASKS = null; return Promise.resolve(m); }
    // ---- panel map learned from other drivers' paints (js/spb-car-islands-data.js): label map 256x256, 0 = not paintable, 1..K = island in this file's own order
    var TPL_CACHE = {};
    function tplLabels(keys) {
        var D = window.SPB_CAR_ISLANDS; if (!D || !D.folders || !window.DecompressionStream) return Promise.resolve(null);
        var f = null; (keys || []).forEach(function (k) { if (!f) D.folders.forEach(function (x) { if (!f && x.k === k) f = x; }); }); if (!f) return Promise.resolve(null);
        if (!TPL_CACHE[f.k]) TPL_CACHE[f.k] = new Promise(function (res) {
            try {
                var bin = atob(f.z), u = new Uint8Array(bin.length), i; for (i = 0; i < u.length; i++) u[i] = bin.charCodeAt(i);
                var ds = new DecompressionStream('deflate'), w = ds.writable.getWriter(); w.write(u); w.close();
                new Response(ds.readable).arrayBuffer().then(function (b) { var a = new Uint8Array(b); res(a.length === GRID * GRID ? a : null); }, function () { res(null); });
            } catch (e) { res(null); }
        });
        return TPL_CACHE[f.k].then(function (lab) { return lab ? { lab: lab, key: f.k } : null; });
    }
    function ciFromLabels(lab) {
        var n = GRID * GRID, acc = {}, i, x, y, v, a;
        for (i = 0; i < n; i++) { v = lab[i]; if (!v) continue; x = i % GRID; y = (i - x) / GRID; a = acc[v] || (acc[v] = { v: v, area: 0, minx: GRID, miny: GRID, maxx: 0, maxy: 0, sx: 0, sy: 0 }); a.area++; a.sx += x; a.sy += y; if (x < a.minx) a.minx = x; if (x > a.maxx) a.maxx = x; if (y < a.miny) a.miny = y; if (y > a.maxy) a.maxy = y; }
        var comps = Object.keys(acc).map(function (k) { return acc[k]; }).sort(function (p, q) { return p.v - q.v; }).map(function (c) {
            var bb = [c.minx / GRID, c.miny / GRID, (c.maxx + 1) / GRID, (c.maxy + 1) / GRID];
            return { raw: c.v, id: 'I' + c.v, area: c.area, bbox: bb, cx: c.sx / c.area / GRID, cy: c.sy / c.area / GRID, share_pct: Math.round(c.area / n * 1000) / 10, cells: cellsOf(bb), w: bb[2] - bb[0], h: bb[3] - bb[1] };
        });
        return { comps: comps, map: lab };
    }
    function finishFromTemplate(m, lab, key, request) {
        if (!currentSource(request)) return Promise.resolve(m);
        var ci = ciFromLabels(lab), n = GRID * GRID, i, bin = new Uint8Array(n); for (i = 0; i < n; i++) bin[i] = lab[i] ? 1 : 0;
        LASTCI = ci; PAINT = bin; MASKS = lab; m.source = "the panel outlines learned from other drivers' paints of this car"; m.tpl = key;
        m.islands = ci.comps.map(function (c) { return { id: c.id, name: null, front: null, cells: c.cells, bbox: c.bbox.map(function (v) { return Math.round(v * 1000) / 1000; }), share_pct: c.share_pct }; });
        publishCache(m, request); return Promise.resolve(m);
    }
    function build00(withLabels, request) {
        var sig = signature();
        if (CACHE && sameSource(CACHE_SOURCE, request.source) && CACHE.sig === sig && (!withLabels || CACHE.labelled)) return Promise.resolve(CACHE);
        var bg = binaryGrid(); LASTBG = bg; PAINT = bg ? bg.bin : null;
        var m = { sig: sig, roles: roles(), islands: [], source: null, labelled: false, note: null };
        m.boxes = sigEntry(sig).b || {};
        if (!bg) {      // no template mask and no dead space left in this paint: the outline recogniser may still know the car, and then its panel map (learned from other drivers' paints) stands in
            var r0 = recognizeCar(); CURREC = r0;
            if (r0 && r0.known) return tplLabels(r0.twins).then(function (got) { return got ? finishFromTemplate(m, got.lab, got.key, request) : noMask(m, request); });
            return noMask(m, request);
        }
        var ci = labelBest(bg); LASTCI = ci; m.source = ci.fallback ? 'the Mask layer (paintable area)' : bg.source; MASKS = ci.map;
        m.islands = ci.comps.map(function (c) { return { id: c.id, name: null, front: null, cells: c.cells, bbox: c.bbox.map(function (v) { return Math.round(v * 1000) / 1000; }), share_pct: c.share_pct }; });
        var cached = sigEntry(sig).l;
        if (cached) { applyLabels(m, cached, true); }
        if (!withLabels || !window.SpbAI || cached) { publishCache(m, request); return Promise.resolve(m); }
        var img = overlayImage(ci, 0.6); if (!img) { publishCache(m, request); return Promise.resolve(m); }
        return window.SpbAI.chat({ messages: [{ role: 'user', content: [{ type: 'text', text: LABEL_PROMPT }, { type: 'image_url', image_url: { url: img } }] }], max_tokens: 700, temperature: 0.1, vision: true, reasoning: { enabled: false } }).then(function (r) {
            m.raw = r && r.ok ? String(r.message && r.message.content || '').slice(0, 1500) : (r && (r.message || r.error));
            var labels = r && r.ok ? parseLabels(r.message && r.message.content) : null;
            if (labels) { applyLabels(m, labels, false); }      // vision guesses are NOT trusted (measured 1-5 of 7 correct): kept as 'guess', never persisted
            else m.note = 'could not name the islands automatically';
            m.cost = r && r.usage ? r.usage.cost : 0; publishCache(m, request); return m;
        }, function () { publishCache(m, request); return m; });
    }
    function build(withLabels, request) { return build0(withLabels, request).then(function (m) { try { withParts(m); } catch (e) {} return m; }); }
    function applyLabels(m, labels, confirmed) { m.islands.forEach(function (isl) { var l = labels[isl.id]; if (l) { if (confirmed) { isl.name = l.name; isl.front = l.front || null; isl.confirmed = true; } else { isl.guess = l.name; } } }); m.labelled = true; }
    function ensure(withLabels) {
        var wantLabels = withLabels !== false, src = sourceDescriptor();
        if (CACHE && !sameSource(CACHE_SOURCE, src)) clearSourceCache();
        if (CACHE && sameSource(CACHE_SOURCE, src) && (!wantLabels || CACHE.labelled)) return Promise.resolve(CACHE);
        // A default vision request cannot satisfy ensure(false): start a distinct offline build.
        if (PENDING && sameSource(PENDING.source, src) && (wantLabels ? PENDING.labels : !PENDING.labels)) return PENDING.promise;
        var request = { source: src, labels: wantLabels }, record = { source: src, labels: wantLabels, promise: null };
        record.promise = build(wantLabels, request).then(function (m) {
            if (PENDING === record) PENDING = null;
            return currentSource(request) ? (CACHE && sameSource(CACHE_SOURCE, src) ? CACHE : m) : (CACHE && sameSource(CACHE_SOURCE, sourceDescriptor()) ? CACHE : null);
        }, function () {
            if (PENDING === record) PENDING = null;
            return CACHE && sameSource(CACHE_SOURCE, sourceDescriptor()) ? CACHE : null;
        });
        PENDING = record; return record.promise;
    }

    // ------------------------------------------------------------------ masks
    function mkBox(nm) {
        var b = CACHE.boxes[nm], a = Math.round((b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]) * 1000) / 10;
        return { id: 'B:' + nm, name: nm, bbox: b.bbox, front: b.front || null, up: b.up || null, confirmed: true, box: true, lib: !!b.lib, share_pct: a };
    }
    function findBox(ref) {
        if (!CACHE || !CACHE.boxes) return null; var q = canonPart(ref), best = null, keys = Object.keys(CACHE.boxes);
        keys.forEach(function (nm) { if (!best && canonPart(nm) === q) best = mkBox(nm); });
        if (!best && q.length > 3) keys.forEach(function (nm) { var n = norm(nm); if (!best && (n.indexOf(q) !== -1 || q.indexOf(n) !== -1)) best = mkBox(nm); });
        return best;
    }
    function findIsland(ref) {
        if (!CACHE) return null; var q = norm(ref), cq = canonPart(ref), best = null;
        CACHE.islands.forEach(function (i) { if (!best && (i.id.toLowerCase() === q || (i.confirmed && i.name && (norm(i.name) === q || canonPart(i.name) === cq)))) best = i; });
        if (!best) best = findBox(ref);
        if (!best) CACHE.islands.forEach(function (i) { if (!best && i.confirmed && i.name && q.length > 3 && (norm(i.name).indexOf(q) !== -1 || q.indexOf(norm(i.name)) !== -1)) best = i; });
        return best || null;
    }
    function portionBox(isl, portion) {
        // returns [x0,y0,x1,y1] in 0..1 of the canvas, inside the island bbox
        var b = isl.bbox, p = norm(portion), frac = /third/.test(p) ? 1 / 3 : (/quarter/.test(p) ? 0.25 : (/fifth/.test(p) ? 0.2 : 0.5));
        var w = b[2] - b[0], h = b[3] - b[1], out = b.slice();
        var front = isl.front || 'right';
        // "upper / lower" follow the car (roof-line side vs rocker side) when the panel's orientation is known
        if (isl.up && !/front|rear|back|nose|tail/.test(p)) {
            var isUp = /upper|roof ?line|belt ?line|shoulder|window|greenhouse/.test(p), isLow = /lower|rocker|skirt|sill/.test(p);
            if (isUp || isLow) { var edge = isUp ? (isl.up === 'bottom' ? 'bottom' : 'top') : (isl.up === 'bottom' ? 'top' : 'bottom'); if (edge === 'top') out[3] = b[1] + h * frac; else out[1] = b[3] - h * frac; return out; }
        }
        function alongX(which) { // 'front' or 'rear' -> x range
            var frontIsRight = (front === 'right');
            var atRight = (which === 'front') ? frontIsRight : !frontIsRight;
            return atRight ? [b[2] - w * frac, b[2]] : [b[0], b[0] + w * frac];
        }
        if (/rear|back|tail/.test(p)) { if (front === 'top' || front === 'bottom') { var atB = front === 'top'; out[1] = atB ? b[3] - h * frac : b[1]; out[3] = atB ? b[3] : b[1] + h * frac; } else { var r = alongX('rear'); out[0] = r[0]; out[2] = r[1]; } }
        else if (/front|nose/.test(p)) { if (front === 'top' || front === 'bottom') { var atT = front === 'top'; out[1] = atT ? b[1] : b[3] - h * frac; out[3] = atT ? b[1] + h * frac : b[3]; } else { var f = alongX('front'); out[0] = f[0]; out[2] = f[1]; } }
        else if (/left/.test(p)) { out[2] = b[0] + w * frac; }
        else if (/right/.test(p)) { out[0] = b[2] - w * frac; }
        else if (/top|upper/.test(p)) { out[3] = b[1] + h * frac; }
        else if (/bottom|lower/.test(p)) { out[1] = b[3] - h * frac; }
        else if (/middle|centre|center/.test(p)) { var m = (1 - frac) / 2; out[0] = b[0] + w * m; out[2] = b[2] - w * m; }
        return out;
    }
    // band: {axis:"height"|"length", from:0..1, to:0..1}. height = from the ROOF-LINE (0) down to the ROCKER (1); length = from the FRONT end (0) to the REAR end (1)
    function bandBox(isl, band) {
        var b = isl.bbox, w = b[2] - b[0], h = b[3] - b[1], f = Math.max(0, Math.min(1, Number(band.from) || 0)), t = Math.max(0, Math.min(1, band.to == null ? 1 : Number(band.to))), tmp;
        if (t < f) { tmp = f; f = t; t = tmp; }
        var out = b.slice(), axis = /len|long|along|front|rear/.test(String(band.axis || '')) ? 'length' : 'height';
        if (axis === 'height') { if (isl.up === 'bottom') { out[1] = b[3] - t * h; out[3] = b[3] - f * h; } else { out[1] = b[1] + f * h; out[3] = b[1] + t * h; } }
        else {
            var front = isl.front || 'right';
            if (front === 'right') { out[0] = b[2] - t * w; out[2] = b[2] - f * w; }
            else if (front === 'left') { out[0] = b[0] + f * w; out[2] = b[0] + t * w; }
            else if (front === 'top') { out[1] = b[1] + f * h; out[3] = b[1] + t * h; }
            else { out[1] = b[3] - t * h; out[3] = b[3] - f * h; }
        }
        return out;
    }
    // islands that live inside a library/taught box: those with >= 55% of their area in it. Returns null when that would select too little (islands unreliable) -> caller falls back to the plain box
    function boxIslandIds(isl, box) {
        if (!MASKS || !isl.box || !isl.lib || !CACHE || !CACHE.islands) return null;
        var gx0 = Math.floor(box[0] * GRID), gx1 = Math.ceil(box[2] * GRID), gy0 = Math.floor(box[1] * GRID), gy1 = Math.ceil(box[3] * GRID), tot = {}, inn = {}, x, y, v;
        for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) { v = MASKS[y * GRID + x]; if (!v) continue; tot[v] = (tot[v] || 0) + 1; if (x >= gx0 && x < gx1 && y >= gy0 && y < gy1) inn[v] = (inn[v] || 0) + 1; }
        var ids = {}, kept = 0, inBox = 0;
        Object.keys(inn).forEach(function (k) { inBox += inn[k]; if (inn[k] / tot[k] >= 0.55) { ids[k] = 1; kept += inn[k]; } });
        return (inBox && kept / inBox >= 0.6) ? ids : null;
    }
    function maskOne(ref, portion, band) {
        var isl = findIsland(ref); if (!isl) return null;
        if (!isl.box && !MASKS) return null;
        var d = paintDims(), W = d[0], H = d[1], id = isl.box ? 0 : Number(isl.id.substr(1)), box = band ? bandBox(isl, band) : (portion ? portionBox(isl, portion) : isl.bbox);
        var out = new Uint8Array(W * H), sc = GRID / W, y, x, x0 = Math.floor(box[0] * W), x1 = Math.ceil(box[2] * W), y0 = Math.floor(box[1] * H), y1 = Math.ceil(box[3] * H), only = isl.box ? boxIslandIds(isl, isl.bbox) : null;
        // MCPSCEN 2026-10-05 (DLM red->black gradient on "left side": the panel's diagonal edges were 8 px staircases, the 256 grid blown up cell by cell): the grid
        // membership is read bilinearly between cell centres and kept at >= 0.35, so diagonal edges are smooth lines and the part grows a hair (never shrinks) at its rim.
        var gin = new Uint8Array(GRID * GRID), gi; for (gi = 0; gi < GRID * GRID; gi++) gin[gi] = (isl.box ? (only ? only[MASKS ? MASKS[gi] : 0] : (!PAINT || PAINT[gi])) : (MASKS && MASKS[gi] === id)) ? 1 : 0;
        for (y = Math.max(0, y0); y < Math.min(H, y1); y++) {
            var fy = y * sc - 0.5 + sc / 2, gy0 = Math.floor(fy), ty = fy - gy0, ra = Math.max(0, Math.min(GRID - 1, gy0)) * GRID, rb = Math.max(0, Math.min(GRID - 1, gy0 + 1)) * GRID;
            for (x = Math.max(0, x0); x < Math.min(W, x1); x++) {
                var fx = x * sc - 0.5 + sc / 2, gx0 = Math.floor(fx), tx = fx - gx0, ca = Math.max(0, Math.min(GRID - 1, gx0)), cb = Math.max(0, Math.min(GRID - 1, gx0 + 1));
                var v00 = gin[ra + ca], v01 = gin[ra + cb], v10 = gin[rb + ca], v11 = gin[rb + cb];
                if (v00 === v01 && v00 === v10 && v00 === v11 ? v00 : ((1 - tx) * (1 - ty) * v00 + tx * (1 - ty) * v01 + (1 - tx) * ty * v10 + tx * ty * v11) >= 0.35) out[y * W + x] = 255;
            }
        }
        return { mask: out, island: isl, box: box };
    }
    // island/part ∩ portion/band as a full-canvas mask; null if unknown.  ref may be a list (union): ["left side","right side"]
    function maskFor(ref, portion, band) {
        if (!CACHE) return null;
        if (Array.isArray(ref)) {
            var res = ref.map(function (r) { return maskOne(r, portion, band); }).filter(Boolean); if (!res.length) return null;
            var un = res[0].mask; for (var q = 1; q < res.length; q++) { var mk = res[q].mask; for (var z = 0; z < un.length; z++) if (mk[z]) un[z] = 255; }
            return { mask: un, island: res[0].island, islands: res.map(function (r) { return r.island; }), box: res[0].box, union: true };
        }
        return maskOne(ref, portion, band);
    }
    function partCells(b) { return cellsOf(b.bbox); }
    // the whole paintable area of the car (template mask / dead-space tone) as a full-canvas mask; null when the sheet carries no such information
    // MCPSCEN 2026-10-04 (MCP Gulf livery on the owner's ARCA PSD: a yellow line survived along EVERY panel edge): the mask is a 256 grid blown up to 2048, so its edge is an
    // 8 px staircase and the body layer's last pixels fall outside it. bleed = grow it one grid cell (the zone's own layer / colour limit keeps the paint tight; a little paint past
    // the UV edge is what the sim needs at seams anyway).
    function paintableMask(bleed) {
        if (!PAINT) return null; var d = paintDims(), W = d[0], H = d[1], out = new Uint8Array(W * H), sc = GRID / W, y, x, G = PAINT;
        if (bleed) { G = new Uint8Array(GRID * GRID); var gy, gx, dy, dx; for (gy = 0; gy < GRID; gy++) for (gx = 0; gx < GRID; gx++) { if (!PAINT[gy * GRID + gx]) continue; for (dy = -1; dy <= 1; dy++) for (dx = -1; dx <= 1; dx++) { var ny = gy + dy, nx = gx + dx; if (ny >= 0 && nx >= 0 && ny < GRID && nx < GRID) G[ny * GRID + nx] = 1; } } }
        for (y = 0; y < H; y++) { var row = Math.min(GRID - 1, Math.floor(y * sc)) * GRID; for (x = 0; x < W; x++) if (G[row + Math.min(GRID - 1, Math.floor(x * sc))]) out[y * W + x] = 255; }
        return out;
    }
    // share / import what the buyer taught about this car (a small JSON; goes into the car library when sent to Shokker)
    function exportTaught() {
        if (!CACHE) return null; var parts = {}, n = 0;
        Object.keys(CACHE.boxes || {}).forEach(function (k) { var b = CACHE.boxes[k]; if (b.taught) { parts[k] = { box: b.bbox.map(function (v) { return Math.round(v * 10000) / 100; }), front: b.front || undefined, up: b.up || undefined }; n++; } });
        if (!n) return null;
        return { format: 'spb-car-map-v1', car: (CACHE.lib && CACHE.lib.name) || null, layoutSig: CACHE.layoutSig || null, folder: effFolderKey() || null, sheet: paintDims(), parts: parts, note: 'Boxes are percent of the sheet [x0,y0,x1,y1]; front = which side of the box is the car front; up = which edge of a side panel is the roof-line.' };
    }
    function importTaught(obj) {
        if (!CACHE || !obj || obj.format !== 'spb-car-map-v1' || !obj.parts) return 0; var n = 0;
        Object.keys(obj.parts).forEach(function (k) { var p = obj.parts[k]; if (p && p.box && p.box.length === 4) { if (setBox(k, p.box.map(function (v) { return Number(v) / 100; }), p.front || null, p.up || null)) n++; } });
        return n;
    }
    function describe() {
        if (!CACHE) return null;
        var parts = Object.keys(CACHE.boxes || {}).map(function (nm) { var b = CACHE.boxes[nm]; return { name: nm, cells: partCells(b), share_pct: Math.round((b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]) * 1000) / 10, front_end: b.front || undefined, roofline_edge: b.up || undefined, source: b.taught ? 'taught by the buyer' : (b.lib ? 'car library' : 'taught') }; });
        var islands = CACHE.islands.map(function (i) { return { id: i.id, name: i.confirmed ? i.name : undefined, cells: i.cells, share_pct: i.share_pct, front_end: i.front || undefined }; });
        var named = {}; parts.forEach(function (p) { named[canonPart(p.name)] = 1; }); islands.forEach(function (i) { if (i.name) named[canonPart(i.name)] = 1; });
        return {
            layers: CACHE.roles, car: CACHE.lib ? CACHE.lib.name + ' (recognised by ' + CACHE.lib.by + ')' : undefined, parts: parts,
            islands: islands.filter(function (i) { return !i.name; }).concat(islands.filter(function (i) { return i.name; })), islands_from: CACHE.source, note: CACHE.note || undefined,
            key_parts_missing: missingParts(['left side', 'right side', 'hood', 'roof', 'trunk']),
            how_to_use: 'region {part:"left side", portion:"rear half"} limits a zone to that part (and part of it); region {part:"left side", band:{axis:"height", from:0.55, to:0.8}} is a stripe from 55% to 80% of the way down from the roof-line to the rocker; {axis:"length", from:0, to:0.3} is the front 30%. part may be a list: ["left side","right side"]. Parts NOT listed under parts are unknown: call point_at to have the buyer show them (once per car). Never draw big boxes across the sheet.'
        };
    }
    // test hook: label the current islands with a specific vision model (no caching)
    function labelWith(model) {
        if (!LASTCI) return Promise.resolve({ error: 'no islands yet; call ensure() first' });
        var img = overlayImage(LASTCI, 0.6), t0 = Date.now();
        return window.SpbAI.chat({ messages: [{ role: 'user', content: [{ type: 'text', text: LABEL_PROMPT }, { type: 'image_url', image_url: { url: img } }] }], max_tokens: 900, temperature: 0.1, vision: true, model: model, reasoning: { enabled: false } }).then(function (r) {
            return { model: model, ok: !!(r && r.ok), ms: Date.now() - t0, cost: r && r.usage ? r.usage.cost : 0, labels: r && r.ok ? parseLabels(r.message && r.message.content) : null, raw: r && r.ok ? String(r.message && r.message.content || '').slice(0, 600) : (r && (r.message || r.error)) };
        });
    }
    // ------------------------------------------------------------------ buyer-confirmed names (persisted per car signature)
    function setLabel(id, name, front, up) {
        if (!CACHE) return false; var isl = null; CACHE.islands.forEach(function (i) { if (i.id === id) isl = i; }); if (!isl) return false;
        isl.name = String(name || '').toLowerCase().slice(0, 40); isl.front = front || null; isl.up = up || null; isl.confirmed = true;
        var labels = {}; CACHE.islands.forEach(function (i) { if (i.confirmed) labels[i.id] = { name: i.name, front: i.front || null, up: i.up || null }; });
        saveCache(CACHE.sig, labels); return true;
    }
    function setBox(name, bbox, front, up) {
        if (!CACHE) return false; name = String(name || '').toLowerCase().slice(0, 40); if (!name) return false;
        var x0 = Math.max(0, Math.min(bbox[0], bbox[2])), x1 = Math.min(1, Math.max(bbox[0], bbox[2])), y0 = Math.max(0, Math.min(bbox[1], bbox[3])), y1 = Math.min(1, Math.max(bbox[1], bbox[3]));
        if ((x1 - x0) * (y1 - y0) < 0.002) return false;
        var taught = {}; Object.keys(CACHE.boxes || {}).forEach(function (k) { if (CACHE.boxes[k].taught) taught[k] = CACHE.boxes[k]; });
        Object.keys(CACHE.boxes || {}).forEach(function (k) { if (canonPart(k) === canonPart(name)) { delete CACHE.boxes[k]; delete taught[k]; } });
        var entry = { bbox: [x0, y0, x1, y1], front: front || null, up: up || null, taught: true };
        CACHE.boxes = CACHE.boxes || {}; CACHE.boxes[name] = entry; taught[name] = entry;
        var store = {}; Object.keys(taught).forEach(function (k) { store[k] = { bbox: taught[k].bbox, front: taught[k].front || null, up: taught[k].up || null }; });
        saveCache(CACHE.sig, null, store); return true;
    }
    function forget() {
        if (!CACHE) return; CACHE.boxes = {}; Object.keys(CACHE.libBoxes || {}).forEach(function (k) { CACHE.boxes[k] = CACHE.libBoxes[k]; }); saveCache(CACHE.sig, {}, {});
        CACHE.islands.forEach(function (i) { i.name = null; i.front = null; i.up = null; i.confirmed = false; });
    }
    function islandAt(fx, fy) {
        if (!MASKS) return null; var x = Math.max(0, Math.min(GRID - 1, Math.floor(fx * GRID))), y = Math.max(0, Math.min(GRID - 1, Math.floor(fy * GRID))), v = MASKS[y * GRID + x];
        if (v) return 'I' + v;
        // click landed on a border / gap: nearest labelled cell within 4 cells
        var best = 0, bd = 99, dy, dx; for (dy = -4; dy <= 4; dy++) for (dx = -4; dx <= 4; dx++) { var yy = y + dy, xx = x + dx; if (yy < 0 || xx < 0 || yy >= GRID || xx >= GRID) continue; var vv = MASKS[yy * GRID + xx]; if (vv && Math.abs(dx) + Math.abs(dy) < bd) { bd = Math.abs(dx) + Math.abs(dy); best = vv; } }
        return best ? 'I' + best : null;
    }
    var PART_COLOURS = ['#ff9f1c', '#2ec4b6', '#e71d36', '#9b5de5', '#00bbf9', '#f15bb5', '#8ac926', '#ffca3a', '#ff595e', '#1982c4'];
    // what the picker draws: the buyer's paint with every panel outlined; highlightId fills one panel; every known part is boxed and named; rect = the rectangle being dragged
    // opts: {noIslands:true} for a clean "what I know about your car" picture
    function pickerImage(n, highlightId, rect, opts) {
        if (!CACHE) return null; opts = opts || {};
        try {
            var src = document.getElementById('paintCanvas'), cv = document.createElement('canvas'); cv.width = cv.height = n; var cx = cv.getContext('2d'), k = n / GRID, y, x;
            cx.fillStyle = '#15151c'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high'; if (src) cx.drawImage(src, 0, 0, n, n);
            try { overlayTemplate(cx, n); } catch (eo) {}
            if (MASKS && !opts.noIslands) {
                var hid = highlightId ? Number(String(highlightId).substr(1)) : 0;
                if (hid) { cx.fillStyle = 'rgba(255,43,214,0.42)'; for (y = 0; y < GRID; y++) for (x = 0; x < GRID; x++) if (MASKS[y * GRID + x] === hid) cx.fillRect(x * k, y * k, k + 0.5, k + 0.5); }
                cx.strokeStyle = 'rgba(255,255,255,0.9)'; cx.lineWidth = 1.5; cx.beginPath();
                for (y = 1; y < GRID - 1; y++) for (x = 1; x < GRID - 1; x++) { var v = MASKS[y * GRID + x]; if (v && (MASKS[y * GRID + x - 1] !== v || MASKS[y * GRID + x + 1] !== v || MASKS[(y - 1) * GRID + x] !== v || MASKS[(y + 1) * GRID + x] !== v)) cx.rect(x * k, y * k, k, k); }
                cx.stroke();
            } else if (!MASKS && !opts.noGrid) {
                cx.strokeStyle = 'rgba(255,255,255,0.3)'; cx.lineWidth = 1; cx.beginPath(); for (var g = 1; g < 8; g++) { cx.moveTo(g * n / 8, 0); cx.lineTo(g * n / 8, n); cx.moveTo(0, g * n / 8); cx.lineTo(n, g * n / 8); } cx.stroke();
            }
            var drawBoxes = {}; Object.keys(CACHE.boxes || {}).forEach(function (k) { drawBoxes[k] = CACHE.boxes[k]; }); if (opts.proposed) Object.keys(opts.proposed).forEach(function (k) { if (!drawBoxes[k]) drawBoxes[k] = opts.proposed[k]; });
            var nm = Object.keys(drawBoxes); cx.font = 'bold ' + Math.max(11, Math.round(n / 34)) + 'px sans-serif'; cx.textBaseline = 'top';
            nm.forEach(function (name, i) {
                var b = drawBoxes[name].bbox, col = PART_COLOURS[i % PART_COLOURS.length], bx = b[0] * n, by = b[1] * n, bw = (b[2] - b[0]) * n, bh = (b[3] - b[1]) * n;
                cx.strokeStyle = col; cx.lineWidth = 2.5; cx.setLineDash([7, 4]); cx.strokeRect(bx, by, bw, bh); cx.setLineDash([]);
                var tw = cx.measureText(name).width + 8; cx.fillStyle = 'rgba(0,0,0,0.78)'; cx.fillRect(bx, by, tw, Math.round(n / 34) + 5); cx.fillStyle = col; cx.fillText(name, bx + 4, by + 2);
                var fr = drawBoxes[name].front; if (fr) { var ax = bx + bw / 2, ay = by + bh / 2, dx = fr === 'left' ? -1 : (fr === 'right' ? 1 : 0), dy = fr === 'top' ? -1 : (fr === 'bottom' ? 1 : 0), L = Math.min(bw, bh) * 0.22; cx.strokeStyle = col; cx.lineWidth = 3; cx.beginPath(); cx.moveTo(ax - dx * L, ay - dy * L); cx.lineTo(ax + dx * L, ay + dy * L); cx.stroke(); cx.beginPath(); cx.arc(ax + dx * L, ay + dy * L, 5, 0, 6.3); cx.fillStyle = col; cx.fill(); }
            });
            if (rect) { var rx = Math.min(rect[0], rect[2]) * n, ry = Math.min(rect[1], rect[3]) * n, rw = Math.abs(rect[2] - rect[0]) * n, rh = Math.abs(rect[3] - rect[1]) * n; cx.fillStyle = 'rgba(255,43,214,0.35)'; cx.fillRect(rx, ry, rw, rh); cx.strokeStyle = '#ff2bd6'; cx.lineWidth = 2; cx.strokeRect(rx, ry, rw, rh); }
            return cv;
        } catch (e) { return null; }
    }
    function boxPickerImage(n, rect) { return pickerImage(n, null, rect); }
    window.SpbProCar = { recognized: function () { return CACHE ? CACHE.rec || null : null; }, effFolder: effFolderKey, calibrationSheet: calibrationSheet, viewerFindings: viewerFindings, near: nearInfo, adoptNear: adoptNear, learnPost: learnPost, loadLearned: loadLearned, exportTaught: exportTaught, importTaught: importTaught, setBox: setBox, hasIslands: function () { return !!(CACHE && MASKS && CACHE.islands.length); }, hasParts: function () { return knownPartNames().length > 0; }, parts: knownPartNames, missing: missingParts, canon: canonPart, library: function () { return CACHE && CACHE.lib || null; }, layoutSig: function () { return CACHE && CACHE.layoutSig || null; }, folderKey: folderKey, atlasMatch: atlasMatch, sigSim: sigSim, setLabel: setLabel, forget: forget, islandAt: islandAt, pickerImage: pickerImage, _labelLocators: labelLocators, _labelWith: labelWith, ensure: ensure, map: function () { return CACHE; }, describe: describe, maskFor: maskFor, roles: roles, roleOf: roleOf, findIsland: findIsland, signature: signature, _paintable: function () { return PAINT; }, paintableMask: paintableMask, _reset: function () { CACHE = null; MASKS = null; PENDING = null; PAINT = null; } };
})();
