/* [RESTRICT-PERF 2026-10-12] SOURCE coverage overlay for the selected zone.
 * Owner 2026-10-12: "I went to RESTRICT TO Numbers with that gray color and not having the box makes it hard to see for one but it also feels
 * like its lagging a little too."
 *
 * Restrict-to-layers + a picked colour decide which pixels a zone covers, but nothing on SOURCE showed WHICH pixels (only region-mask zones drew an
 * overlay). This module draws the selected zone's real coverage - the restricted layers' visible footprint AND the picked colour match, from
 * SPBZoneClip.coverage() - as a tint with a white/black double outline, a dashed bounding box and a one-line chip ("Zone 1 - Numbers - #000000 -
 * 51,105 px"), so a thin gray number is findable at any zoom.
 *
 * Cost control: display only (DOM sibling of the paint canvas; never read by paint/render/export); rebuilt ONLY when the coverage key changes
 * (zone, restricted layers, picked colours/tolerance, the layer stack structure, zoom bucket) and then deferred a tick so the interaction that
 * caused it paints first; the overlay bitmap is a max-pooled low-res grid (1 cell ~ 1-2 screen px) so the outline is thick enough to see at fit zoom
 * and a rebuild is a few ms of grid work after one pass over the mask. Polling is a 250 ms string compare. Pref: localStorage spb_zone_cov
 * (default on); the checkbox lives in the zone's COLOR section. Kill switch: window.SPB_ZONECOV_OFF = true.
 */
(function (root) {
    'use strict';
    var doc = root.document;
    if (!doc) return;
    var LS_ON = 'spb_zone_cov';
    function lsGet(k) { try { return root.localStorage.getItem(k); } catch (_) { return null; } }
    function lsSet(k, v) { try { root.localStorage.setItem(k, v); } catch (_) {} }
    var st = { on: lsGet(LS_ON) !== '0', wrap: null, cv: null, box: null, chip: null, fast: '', slow: '', due: 0, timer: null, poll: null,
        stats: { builds: 0, lastMs: 0, lastScanMs: 0, covered: 0 }, shown: false };

    function off() { return !!root.SPB_ZONECOV_OFF; }
    function selZone() {
        try { return (typeof zones !== 'undefined' && typeof selectedZoneIndex === 'number' && selectedZoneIndex >= 0) ? (zones[selectedZoneIndex] || null) : null; } catch (_) { return null; }
    }
    function selIdx() { try { return selectedZoneIndex; } catch (_) { return -1; } }
    function clipApi() { return root.SPBZoneClip && root.SPBZoneClip.coverage ? root.SPBZoneClip : null; }

    // ---- DOM ------------------------------------------------------------------------------------------------------------
    function ensureDom() {
        if (st.wrap && st.wrap.parentNode) return true;
        var inner = doc.getElementById('canvasInner'), region = doc.getElementById('regionCanvas');
        if (!inner || !region || region.parentNode !== inner) return false;
        var wrap = doc.createElement('div');
        wrap.id = 'zoneCovWrap';
        wrap.setAttribute('aria-hidden', 'true');
        wrap.setAttribute('style', 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;display:none;z-index:2;');
        var cv = doc.createElement('canvas');
        cv.id = 'zoneCovCanvas';
        cv.setAttribute('style', 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;');
        var box = doc.createElement('div');
        box.id = 'zoneCovBox';
        box.setAttribute('style', 'position:absolute;box-sizing:border-box;border:2px dashed #fff;box-shadow:0 0 0 1px #000,inset 0 0 0 1px #000;pointer-events:none;display:none;');
        var chip = doc.createElement('div');
        chip.id = 'zoneCovChip';
        chip.setAttribute('style', 'position:absolute;pointer-events:none;white-space:nowrap;font:600 10px/1.25 Inter,system-ui,sans-serif;color:#fff;background:rgba(8,10,18,0.9);border:1px solid rgba(255,255,255,0.55);border-radius:3px;padding:2px 6px;display:none;');
        wrap.appendChild(cv); wrap.appendChild(box); wrap.appendChild(chip);
        inner.insertBefore(wrap, region.nextSibling);
        st.wrap = wrap; st.cv = cv; st.box = box; st.chip = chip;
        return true;
    }
    function hide() {
        if (st.wrap) st.wrap.style.display = 'none';
        st.shown = false;
    }

    // ---- geometry: one grid cell ~ 1-2 screen pixels ---------------------------------------------------------------------
    function zoomShift() {
        var pc = doc.getElementById('paintCanvas');
        if (!pc || !pc.width) return 0;
        var cssW = parseFloat(pc.style.width) || pc.width, sc = cssW / pc.width;
        if (!(sc > 0) || sc >= 1) return 0;
        return Math.max(0, Math.min(4, Math.ceil(Math.log(1 / sc) / Math.LN2)));
    }

    function describe(zone, count) {
        var api = clipApi(), bits = [];
        bits.push(String(zone.name || ('Zone ' + (selIdx() + 1))));
        try {
            var ids = api.layerIds(zone);
            if (ids.length) {
                var names = ids.map(function (id) { var l = (typeof _psdLayers !== 'undefined') ? _psdLayers.find(function (x) { return x && x.id === id; }) : null; return l ? String(l.name || id) : String(id); });
                bits.push(names.length > 2 ? names.slice(0, 2).join(' + ') + ' +' + (names.length - 2) : names.join(' + '));
            }
            var tg = api.colorTargets(zone);
            if (tg.length) bits.push(tg.length === 1 ? ('#' + tg[0].color_rgb.map(function (v) { return (v | 0).toString(16).padStart(2, '0'); }).join('')) : tg.length + ' colors');
        } catch (_) {}
        bits.push(count.toLocaleString('en-US') + ' px');
        return bits.join(' · ');
    }

    // ---- build ----------------------------------------------------------------------------------------------------------
    function build() {
        st.timer = null;
        var zone = selZone(), api = clipApi(), pc = doc.getElementById('paintCanvas');
        if (off() || !st.on || !zone || !api || !pc || !pc.width || !api.hasArea(zone) || !ensureDom()) { hide(); return; }
        var t0 = performance.now(), w = pc.width, h = pc.height;
        var mask = api.coverage(zone, w, h);
        if (!mask) { hide(); return; }
        var t1 = performance.now();
        var s = zoomShift(), sw = (w + (1 << s) - 1) >> s, sh = (h + (1 << s) - 1) >> s;
        var small = new Uint8Array(sw * sh), count = 0, minX = w, minY = h, maxX = -1, maxY = -1;
        for (var y = 0, row = 0; y < h; y++, row += w) {
            var sy = (y >> s) * sw, any = false, rx0 = -1, rx1 = -1;
            for (var x = 0; x < w; x++) {
                if (mask[row + x]) { small[sy + (x >> s)] = 1; count++; if (rx0 < 0) rx0 = x; rx1 = x; any = true; }
            }
            if (any) { if (y < minY) minY = y; if (y > maxY) maxY = y; if (rx0 < minX) minX = rx0; if (rx1 > maxX) maxX = rx1; }
        }
        var t2 = performance.now();
        st.stats.builds++; st.stats.covered = count; st.stats.lastScanMs = t2 - t1;
        var chip = st.chip, box = st.box, cv = st.cv;
        st.wrap.style.display = 'block'; st.shown = true;
        if (!count) {
            cv.style.display = 'none'; box.style.display = 'none';
            chip.textContent = (zone.name || 'This zone') + ' covers 0 pixels — check the restricted layers and the picked colors / tolerance';
            chip.style.left = '6px'; chip.style.top = '6px'; chip.style.transform = 'none'; chip.style.display = 'block';
            st.stats.lastMs = performance.now() - t0;
            return;
        }
        cv.style.display = 'block';
        if (cv.width !== sw || cv.height !== sh) { cv.width = sw; cv.height = sh; }
        var ctx = cv.getContext('2d'), img = ctx.createImageData(sw, sh), d = img.data;
        var col = (typeof ZONE_OVERLAY_COLORS !== 'undefined' && ZONE_OVERLAY_COLORS.length) ? ZONE_OVERLAY_COLORS[selIdx() % ZONE_OVERLAY_COLORS.length] : [255, 50, 255, 200];
        var tr = col[0], tg2 = col[1], tb = col[2];
        for (var cy = 0, ci = 0; cy < sh; cy++) {
            for (var cx = 0; cx < sw; cx++, ci++) {
                var p = ci * 4;
                if (small[ci]) {
                    var edge = cx === 0 || cy === 0 || cx === sw - 1 || cy === sh - 1 || !small[ci - 1] || !small[ci + 1] || !small[ci - sw] || !small[ci + sw];
                    if (edge) { d[p] = 255; d[p + 1] = 255; d[p + 2] = 255; d[p + 3] = 255; }
                    else { d[p] = tr; d[p + 1] = tg2; d[p + 2] = tb; d[p + 3] = 120; }
                } else if ((cx > 0 && small[ci - 1]) || (cx < sw - 1 && small[ci + 1]) || (cy > 0 && small[ci - sw]) || (cy < sh - 1 && small[ci + sw])) {
                    d[p] = 0; d[p + 1] = 0; d[p + 2] = 0; d[p + 3] = 235;   // outer black line so the white ring reads on white / light paint too
                }
            }
        }
        ctx.putImageData(img, 0, 0);
        // dashed bounding box + chip, in % of the canvas so they follow zoom for free
        var bl = minX / w * 100, bt = minY / h * 100, bw = (maxX - minX + 1) / w * 100, bh = (maxY - minY + 1) / h * 100;
        box.style.left = bl.toFixed(3) + '%'; box.style.top = bt.toFixed(3) + '%'; box.style.width = bw.toFixed(3) + '%'; box.style.height = bh.toFixed(3) + '%'; box.style.display = 'block';
        chip.textContent = describe(zone, count);
        chip.style.borderColor = 'rgb(' + tr + ',' + tg2 + ',' + tb + ')';
        chip.style.left = bl.toFixed(3) + '%'; chip.style.top = bt.toFixed(3) + '%';
        chip.style.transform = bt < 5 ? 'translate(2px,2px)' : 'translateY(calc(-100% - 3px))';
        chip.style.display = 'block';
        st.stats.lastMs = performance.now() - t0;
    }

    // ---- change detection -----------------------------------------------------------------------------------------------
    // fast key = what the owner just did (zone / restricted layers / picked colours / tolerance / zoom): redraw within ~30 ms.
    // slow key = pixels of layers changed by painting (a stroke commit): debounced until painting pauses and never run mid-stroke.
    var down = false, lastUp = 0;
    function wantKeys() {
        if (off() || !st.on) return null;
        var zone = selZone(), api = clipApi(), pc = doc.getElementById('paintCanvas');
        if (!zone || !api || !pc || !pc.width || !api.hasArea(zone)) return null;
        var p = api.coverageKey(zone, pc.width, pc.height).split('~');   // ids ~ targets ~ WxH ~ layerSig ~ stackSig
        return { fast: selIdx() + '~' + p[0] + '~' + p[1] + '~' + p[2] + '~' + p[4] + '~z' + zoomShift(), slow: p[3] };
    }
    function schedule(delay) {
        var due = performance.now() + delay;
        if (st.timer) { if (st.due <= due) return; root.clearTimeout(st.timer); }
        st.due = due;
        st.timer = root.setTimeout(function () {
            st.timer = null;
            if (down) { schedule(300); return; }   // never rebuild mid-stroke
            build();
        }, delay);
    }
    function tick() {
        var k = wantKeys();
        if (!k) {
            if (st.fast !== '') { st.fast = ''; st.slow = ''; if (st.timer) { root.clearTimeout(st.timer); st.timer = null; } hide(); }
            return;
        }
        if (k.fast !== st.fast) { st.fast = k.fast; st.slow = k.slow; schedule(30); }   // let the interaction that changed the zone paint first
        else if (k.slow !== st.slow) { st.slow = k.slow; schedule(450); }
    }
    function setOn(v) {
        st.on = !!v; lsSet(LS_ON, st.on ? '1' : '0');
        st.fast = '__changed__';
        tick();
        try { var cb = doc.querySelectorAll('input.spb-zonecov-toggle'); for (var i = 0; i < cb.length; i++) cb[i].checked = st.on; } catch (_) {}
    }
    function boot() {
        if (off()) return;
        st.poll = root.setInterval(tick, 250);
        doc.addEventListener('pointerdown', function () { down = true; }, true);
        doc.addEventListener('pointerup', function () { down = false; lastUp = performance.now(); }, true);
        doc.addEventListener('pointercancel', function () { down = false; }, true);
        // react quickly to the usual triggers (pick, tick a layer, tolerance slider) without waiting for the poll
        var evT = null;
        ['click', 'pointerup', 'keyup', 'input', 'change'].forEach(function (ev) { doc.addEventListener(ev, function () { if (evT) return; evT = root.setTimeout(function () { evT = null; tick(); }, 60); }, true); });
        tick();
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot); else boot();

    root.SPBZoneCoverage = { isOn: function () { return st.on; }, setOn: setOn, refresh: function () { st.fast = '__changed__'; tick(); }, build: build, state: st };
})(typeof window === 'object' ? window : globalThis);
