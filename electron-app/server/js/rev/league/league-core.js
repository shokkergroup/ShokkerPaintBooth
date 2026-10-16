/* league-core.js - [SPB-REV-LEAGUE 2026-10-10] LEAGUE PACK: one livery, a whole grid of drivers.
 *
 * League painters paint the SAME car for 10-40 drivers, each with their own number, name and sometimes a sponsor or team colour. Today that is an hour of
 * repetitive work per car (Photoshop: swap the number three times, recolour, export, rename by customer ID, repeat). This module does it from a roster:
 *
 *   per driver:  Colourway team colour (optional)  ->  Number Kit (Replace Existing: same size / slant / place as the template's own number)
 *                ->  name text on the roof rails etc. (optional, Sponsor Kit slots)  ->  Sponsor Kit logo (optional)
 *                ->  THE APP'S OWN doRender()  into <folder>/<customer id>/  (so the files are exactly what a normal RENDER writes:
 *                    car_num_<id>.tga or car_<id>.tga per the project's own "use custom number" setting, plus car_spec_<id>.tga)
 *                ->  every kit session is cancelled again: the template (layers, zones, undo stack) is left exactly as it was.
 *   previews:    the same pipeline, but the composite goes to /preview-render at a low scale (the Live Preview path) for the grid.
 *   resume:      <folder>/league_manifest.json remembers {template hash, per-driver hash}; Render All skips drivers whose files are on disk with the same hashes.
 *   apply:       "Apply This Driver To The Project" runs the same stages but commits each kit session (normal undo steps).
 *
 * Nothing in the engine or any shared file changes: this file only calls the public APIs of SpbRevNumbers, SpbRevSponsor(+Clean), SPBRevColourway, the page's
 * doRender / buildServerZonesForRender, and the additive /api/rev-league/* routes (server_routes/rev_league_routes.py).
 * Kill switch: window.SPB_REV_LEAGUE_OFF = true (or localStorage SPB_REV_LEAGUE_OFF = '1').
 */
(function (root) {
    'use strict';
    if (root.SpbRevLeague) return;
    var doc = root.document;
    var VER = 'lg1.1', TAG = '[SPB-REV-LEAGUE]';
    var LS_ROSTER = 'spb_rev_league_roster_v1';

    // ------------------------------------------------------------------ plumbing
    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_REV_LEAGUE_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_REV_LEAGUE_OFF')); }
        catch (e) { return flagOn(root.SPB_REV_LEAGUE_OFF); }
    }
    function warn(where, e) { try { console.warn(TAG, where, e && e.message || e); } catch (_) {} }
    function psdLayers() { try { return (typeof _psdLayers !== 'undefined') ? _psdLayers : root._psdLayers; } catch (e) { return root._psdLayers; } }
    function zoneList() { try { return (typeof zones !== 'undefined') ? zones : root.zones; } catch (e) { return root.zones; } }
    function toast(msg, kind) { try { if (typeof root.showToast === 'function') root.showToast(msg, kind); } catch (e) {} }
    function call(name) { try { var f = root[name]; if (typeof f === 'function') return f.apply(root, Array.prototype.slice.call(arguments, 1)); } catch (e) { warn(name, e); } return undefined; }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function now() { return (root.performance || Date).now(); }
    function el(id) { return doc.getElementById(id); }
    function clone(o) { return JSON.parse(JSON.stringify(o)); }
    function fnvStr(s, h) { h = h == null ? 0x811c9dc5 : h; s = String(s); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
    function fnvBytes(d, h) { h = h == null ? 0x811c9dc5 : h; for (var i = 0; i < d.length; i++) { h ^= d[i]; h = Math.imul(h, 16777619); } return h >>> 0; }
    function hx(n) { return ('00000000' + (n >>> 0).toString(16)).slice(-8); }
    function baseUrl() { try { return (root.ShokkerAPI && root.ShokkerAPI.baseUrl) || ''; } catch (e) { return ''; } }

    // ------------------------------------------------------------------ colours
    var NAMED = { red: '#d62828', blue: '#1d4ed8', green: '#15803d', yellow: '#f5c518', orange: '#f77f00', purple: '#7e22ce', pink: '#ec4899', white: '#ffffff', black: '#111111',
        gray: '#808080', grey: '#808080', silver: '#c0c0c0', gold: '#d4af37', navy: '#1e3a8a', teal: '#0d9488', cyan: '#06b6d4', lime: '#84cc16', maroon: '#7f1d1d', brown: '#78350f',
        lightblue: '#38bdf8', skyblue: '#38bdf8', darkblue: '#1e3a8a', darkgreen: '#14532d', burgundy: '#7f1d1d', magenta: '#d946ef', violet: '#7c3aed', crimson: '#dc143c', tan: '#d2b48c' };
    function toHex(s) {
        s = String(s == null ? '' : s).trim().toLowerCase().replace(/\s+/g, '');
        if (!s) return null;
        if (NAMED[s]) return NAMED[s];
        var m = /^#?([0-9a-f]{6})$/.exec(s); if (m) return '#' + m[1];
        m = /^#?([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(s); if (m) return '#' + m[1] + m[1] + m[2] + m[2] + m[3] + m[3];
        return null;
    }
    /** "red", "#ff0000", "#ff0000/#ffffff" (up to three: main / accent / trim) -> ['#..', ...] or null when any part is unknown */
    function parseTeam(s) {
        s = String(s == null ? '' : s).trim(); if (!s) return [];
        var parts = s.split(/[\/+|;]|\s+(?:and|&)\s+/i).map(function (x) { return x.trim(); }).filter(Boolean);
        if (parts.length === 1 && /\s/.test(parts[0]) && !toHex(parts[0])) parts = parts[0].split(/\s+/);
        var out = []; for (var i = 0; i < parts.length && i < 3; i++) { var h = toHex(parts[i]); if (!h) return null; out.push(h); }
        return out;
    }

    // ------------------------------------------------------------------ the roster: parse + validate
    var HEAD = {
        name: /^(driver|driver ?name|name|pilot|racer)$/i,
        custid: /^(cust(omer)?[ _-]?(id|#|no\.?|num(ber)?)?|iracing[ _-]?(cust(omer)?[ _-]?)?(id|#|no\.?|num(ber)?)|id|member ?id)$/i,
        number: /^(car[ _-]?)?(no\.?|num(ber)?|#)$/i,
        team: /^(team[ _-]?)?(colou?r|colou?rs|hex)$|^team$/i,
        sponsor: /^(sponsor|sponsor[ _-]?(logo|file)?|logo|logo[ _-]?file)$/i,
        text: /^((roof|windshield|banner|name)[ _/-]*(or[ _/-]*)?(roof|windshield|banner|name)?[ _-]*(text)?|text|roof ?\/ ?windshield ?text|windshield ?text|roof ?text)$/i
    };
    var ORDER = ['name', 'custid', 'number', 'team', 'sponsor', 'text'];
    function splitLine(line, d) {
        var out = [], cur = '', q = false;
        for (var i = 0; i < line.length; i++) {
            var ch = line.charAt(i);
            if (q) { if (ch === '"') { if (line.charAt(i + 1) === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
            else if (ch === '"' && !cur.trim()) { q = true; cur = ''; }
            else if (ch === d) { out.push(cur); cur = ''; }
            else cur += ch;
        }
        out.push(cur); return out.map(function (s) { return s.trim(); });
    }
    function detectDelim(line) {
        var best = ',', bc = -1; ['\t', ',', ';', '|'].forEach(function (d) { var c = line.split(d).length - 1; if (c > bc || (d === '\t' && c > 0 && c >= bc)) { if (c > bc) { best = d; bc = c; } } });
        return bc > 0 ? best : ',';
    }
    /** text (CSV / TSV / pasted rows) -> {rows:[{name,custid,number,team,sponsor,text}], header:bool, delim} */
    function parseRoster(text) {
        var lines = String(text == null ? '' : text).replace(/\r\n?/g, '\n').split('\n').filter(function (l) { return l.trim().length; });
        if (!lines.length) return { rows: [], header: false, delim: ',' };
        var d = detectDelim(lines[0]), cells = lines.map(function (l) { return splitLine(l, d); });
        var map = null, hits = 0, c0 = cells[0], found = {};
        c0.forEach(function (c, i) { var t = c.replace(/[()]/g, ' ').replace(/\s+/g, ' ').trim(); for (var k in HEAD) if (!found[k] && HEAD[k].test(t)) { found[k] = i; hits++; break; } });
        var header = hits >= 2 && (found.custid != null || found.name != null || found.number != null);
        if (header) { map = found; cells = cells.slice(1); }
        var rows = cells.map(function (r) {
            var o = { name: '', custid: '', number: '', team: '', sponsor: '', text: '' };
            if (map) { for (var k in map) o[k] = r[map[k]] == null ? '' : r[map[k]]; }
            else {
                var ord = ORDER.slice();
                if (/^\d{4,9}$/.test(r[0] || '') && !/^\d{4,9}$/.test(r[1] || '')) ord = ['custid', 'name', 'number', 'team', 'sponsor', 'text'];   // "123456, Alex Rivera, 48"
                ord.forEach(function (k, i) { o[k] = r[i] == null ? '' : r[i]; });
            }
            o.number = String(o.number || '').replace(/^#/, '').trim(); o.custid = String(o.custid || '').replace(/\s+/g, '');
            return o;
        }).filter(function (o) { return o.name || o.custid || o.number; });
        return { rows: rows, header: header, delim: d };
    }
    function baseName(f) { return String(f || '').replace(/^.*[\\\/]/, '').replace(/\.[a-z0-9]{2,5}$/i, '').trim().toLowerCase(); }
    /** adds errs / warns / hex / logoKey to every row, in place; returns {errors, warnings, ok} */
    function validate(rows, logos) {
        var seenId = {}, seenNo = {}, errs = 0, warns = 0;
        rows.forEach(function (r) {
            r.errs = []; r.warns = []; r.hex = [];
            if (!r.name) r.warns.push('No driver name.');
            if (!/^\d+$/.test(r.custid)) r.errs.push('Customer ID must be digits only.');
            else if (!/^\d{4,7}$/.test(r.custid)) r.errs.push('iRacing customer IDs are 4 to 7 digits.');
            if (!/^\d{1,3}$/.test(r.number) || parseInt(r.number, 10) > 999) r.errs.push('Number must be 0 to 999.');
            var t = parseTeam(r.team); if (t === null) r.errs.push('Unknown team colour "' + r.team + '".'); else r.hex = t;
            r.logoKey = null;
            if (r.sponsor) { var k = baseName(r.sponsor); if (logos && logos[k]) r.logoKey = k; else r.warns.push('Sponsor logo "' + r.sponsor + '" is not loaded (Add Sponsor Logos).'); }
        });
        rows.forEach(function (r) {
            if (/^\d+$/.test(r.custid)) { if (seenId[r.custid]) { r.errs.push('Duplicate customer ID (same as row ' + seenId[r.custid] + ').'); } else seenId[r.custid] = rows.indexOf(r) + 1; }
            if (/^\d{1,3}$/.test(r.number)) { var n = String(parseInt(r.number, 10)); if (seenNo[n] != null && seenNo[n] !== rows.indexOf(r)) { r.warns.push('Number ' + r.number + ' is also on row ' + (seenNo[n] + 1) + '.'); rows[seenNo[n]].warns.push('Number ' + r.number + ' is also on row ' + (rows.indexOf(r) + 1) + '.'); } else seenNo[n] = rows.indexOf(r); }
        });
        rows.forEach(function (r) { r.ok = !r.errs.length; errs += r.errs.length; warns += r.warns.length; });
        return { errors: errs, warnings: warns, ok: errs === 0 && rows.length > 0 };
    }

    // ------------------------------------------------------------------ state
    var ST = {
        rows: [], logos: {}, folder: '', busy: false, cancel: false, results: {}, tmpl: null, lastRun: null, hooks: [],
        opts: { places: { left: true, right: true, roof: true }, allNumbers: true, font: '', fill: '#ffffff', ring: '#000000', shadow: true, size: 100,
            teamOn: true, nameOn: false, nameSlot: 'rails', nameFrom: 'auto', nameCaps: true, nameFill: '#ffffff', nameLine: '#000000', nameSize: 100,
            logoOn: true, logoSlots: { hood: false, quarters: true, tv: false, deck: false, doors: false }, logoSize: 100, thumb: 0.125 }
    };
    function emit(ev, data) { ST.hooks.forEach(function (f) { try { f(ev, data); } catch (e) { warn('hook', e); } }); }
    function on(f) { if (typeof f === 'function') ST.hooks.push(f); }
    function numKit() {                                  // the Number Kit style: the painter's last Number Kit (so the pack matches what they already chose), else its defaults
        var NK = root.SpbRevNumbers, last = null, o = ST.opts;
        try { last = JSON.parse(root.localStorage.getItem('spb_rev_numbers_last_v1') || 'null'); } catch (e) {}
        var k = Object.assign(JSON.parse(JSON.stringify(NK.DEFAULTS || {})), last || {});   // [SPB-REV-LEAGUE 2026-10-10] defaults first: a painter who never used the Number Kit still gets a defined fill / outline (the panel swatches read them)
        if (o.styleSet) {                                // the League panel's own style controls win once the painter touched them
            if (o.font) k.font = o.font;
            k.fill = o.fill; k.ring1 = Object.assign({}, (k.ring1 || NK.DEFAULTS.ring1), { color: o.ring });
            k.shadow = Object.assign({}, (k.shadow || NK.DEFAULTS.shadow), { on: !!o.shadow });
        }
        k.places = Object.assign({}, o.places); k.size = o.size; k.material = k.material || 'none';
        return k;
    }
    function templatePaintFile() { var e = el('paintFile'); return e ? e.value.trim() : ''; }
    function customNumberOn() { var e = el('useCustomNumberCheckbox'); return e ? !!e.checked : true; }
    function prefixName() { return customNumberOn() ? 'car_num' : 'car'; }

    // ------------------------------------------------------------------ a fingerprint of the project "as the painter left it" (before / after a run must be equal)
    function sampleHash(cv) {
        try {
            var c = doc.createElement('canvas'); c.width = 128; c.height = 128; var g = c.getContext('2d', { willReadFrequently: true });
            g.drawImage(cv, 0, 0, 128, 128); return fnvBytes(g.getImageData(0, 0, 128, 128).data);
        } catch (e) { return 0; }
    }
    function projectSig() {
        var L = psdLayers() || [], h = 0x811c9dc5, parts = [];
        L.forEach(function (l) {
            var bb = (l.bbox || []).join(','), im = l.img, w = im ? (im.naturalWidth || im.width) : 0;
            parts.push([l.id, l.name, l.visible === false ? 0 : 1, l.opacity, l.blendMode, bb, w, l.pcAdj ? 1 : 0, l.spbMaterial ? JSON.stringify(l.spbMaterial).length : 0].join('|'));
            if (im) h = fnvStr(sampleHash(im), h);
        });
        h = fnvStr(parts.join('\n'), h);
        try { h = fnvStr(JSON.stringify((zoneList() || []).map(function (z) { return [z.name, z.base, z.finish, z.color, z.colorMode, z.pattern, z.intensity, z.muted ? 1 : 0, z.regionMask ? z.regionMask.length : 0]; })), h); } catch (e) {}
        var u = (typeof _layerUndoStack !== 'undefined') ? _layerUndoStack.length : -1, r = (typeof _layerRedoStack !== 'undefined') ? _layerRedoStack.length : -1;
        return hx(h) + ':' + L.length + ':u' + u + ':r' + r;
    }
    function compositeHash() {
        var cv = root._nuqPreviewComposite ? root._nuqPreviewComposite() : (root.buildLivePaintCompositeCanvas ? root.buildLivePaintCompositeCanvas() : el('paintCanvas'));
        var g = cv.getContext('2d', { willReadFrequently: true });
        return hx(fnvBytes(g.getImageData(0, 0, cv.width, cv.height).data));
    }
    function templateHash() {
        var h = fnvStr(compositeHash());
        try { h = fnvStr(JSON.stringify(root.buildServerZonesForRender(zoneList())), h); } catch (e) { warn('template zones', e); }
        var wear = el('wearSlider'); h = fnvStr(['wear', wear ? wear.value : 0, 'cn', customNumberOn() ? 1 : 0, 'dual', el('dualSpecCheckbox') && el('dualSpecCheckbox').checked ? 1 : 0].join('|'), h);
        return hx(h);
    }
    function driverHash(d, tmpl) {
        var o = ST.opts, lg = d.logoKey && ST.logos[d.logoKey];
        var spec = { n: d.number, name: d.name, team: d.hex, sp: d.sponsor ? [d.logoKey, lg ? lg.hash : 0] : null, tx: d.text, nk: numKit(), nameOn: o.nameOn, nameSlot: o.nameSlot, nameFrom: o.nameFrom, nameCaps: o.nameCaps, nameFill: o.nameFill, nameLine: o.nameLine, nameSize: o.nameSize,
            logoOn: o.logoOn, logoSlots: o.logoSlots, logoSize: o.logoSize, teamOn: o.teamOn, allNo: o.allNumbers !== false ? 2 : 0, fg: 1 };   // allNo / fg: follow-up 2026-10-10 (every number replaced; the number keeps its own finish) - old pack hashes no longer match, so Resume re-renders
        return hx(fnvStr(JSON.stringify(spec), fnvStr(tmpl || '')));
    }

    // ------------------------------------------------------------------ sponsor logos
    function addLogoFiles(files) {
        var CL = root.SpbRevSponsorClean; if (!CL) return Promise.resolve([]);
        var list = Array.prototype.slice.call(files || []), out = [];
        return list.reduce(function (p, f) {
            return p.then(function () {
                return CL.decode(f).then(function (rec) {
                    var res = CL.cleanCanvas(rec.canvas, { tol: 0, halo: 2, enclosed: false });
                    var info = res.info || {}, key = baseName(f.name);
                    if (info.mode === 'none') { out.push({ key: key, name: f.name, ok: false, why: info.reason || 'No plain background found.' }); return; }
                    var cv = res.canvas, h = 0x811c9dc5;
                    try { var s = doc.createElement('canvas'); s.width = 64; s.height = 64; var g = s.getContext('2d', { willReadFrequently: true }); g.drawImage(cv, 0, 0, 64, 64); h = fnvBytes(g.getImageData(0, 0, 64, 64).data); h = fnvStr(cv.width + 'x' + cv.height, h); } catch (e) {}
                    ST.logos[key] = { canvas: cv, name: f.name, key: key, hash: hx(h), mode: info.mode, w: cv.width, h: cv.height };
                    out.push({ key: key, name: f.name, ok: true, mode: info.mode });
                }, function (e) { out.push({ key: baseName(f.name), name: f.name, ok: false, why: (e && e.message) || 'Could not open that picture.' }); });
            });
        }, Promise.resolve()).then(function () { validate(ST.rows, ST.logos); emit('roster'); return out; });
    }

    // ------------------------------------------------------------------ one driver on the car (every stage is a normal kit session; nothing is committed in render / preview mode)
    function slotsFor(group) {
        var m = { hood: ['hood'], quarters: ['quarter_l', 'quarter_r'], tv: ['tv_l', 'tv_r'], deck: ['deck'], doors: ['door_l', 'door_r'], rails: ['rail_l', 'rail_r'] };
        return m[group] || [];
    }
    function logoSlotMap() {
        var o = {}; Object.keys(ST.opts.logoSlots).forEach(function (g) { if (ST.opts.logoSlots[g]) slotsFor(g).forEach(function (s) { o[s] = true; }); }); return o;
    }
    function textCanvas(str, o) {
        var px = 200, f = (o.font || 'Impact'), c = doc.createElement('canvas'), g = c.getContext('2d');
        str = o.caps ? String(str).toUpperCase() : String(str);
        g.font = 'bold ' + px + 'px "' + f + '", Impact, "Arial Black", sans-serif'; var tw = Math.ceil(g.measureText(str).width), lw = Math.round(px * 0.14), pad = lw + 8;
        c.width = tw + pad * 2; c.height = Math.round(px * 1.25) + pad * 2; g = c.getContext('2d');
        g.font = 'bold ' + px + 'px "' + f + '", Impact, "Arial Black", sans-serif'; g.textBaseline = 'alphabetic'; g.lineJoin = 'round'; g.miterLimit = 2;
        var y = pad + px * 0.95;
        if (lw > 0) { g.lineWidth = lw * 2; g.strokeStyle = o.line || '#000'; g.strokeText(str, pad, y); }
        g.fillStyle = o.fill || '#fff'; g.fillText(str, pad, y);
        // trim to the ink
        var d = g.getImageData(0, 0, c.width, c.height).data, x0 = c.width, y0 = c.height, x1 = -1, y1 = -1;
        for (var i = 3, p = 0; i < d.length; i += 4, p++) if (d[i] > 8) { var xx = p % c.width, yy = (p / c.width) | 0; if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (yy < y0) y0 = yy; if (yy > y1) y1 = yy; }
        if (x1 < 0) return null;
        var out = doc.createElement('canvas'); out.width = x1 - x0 + 1; out.height = y1 - y0 + 1; out.getContext('2d').drawImage(c, x0, y0, out.width, out.height, 0, 0, out.width, out.height);
        return out;
    }
    function bumpRev() { root._spbLayerRev = (root._spbLayerRev | 0) + 1; call('invalidateLayerVisibleContributionCache'); call('recompositeFromLayers'); }
    function insertAtTemplate(layers) {
        var L = psdLayers(), Sp = root.SpbRevSponsor, at = Sp && Sp.templateIndex ? Sp.templateIndex(L) : L.length;
        layers.forEach(function (l, i) { L.splice(Math.min(at + i, L.length), 0, l); });
    }
    function removeByRef(layers) { var L = psdLayers(); layers.forEach(function (l) { var i = L.indexOf(l); if (i >= 0) L.splice(i, 1); }); }

    /** which stages does this driver need? */
    function stagesOf(d) {
        var o = ST.opts, st = { colour: false, number: true, name: false, logo: false };
        st.colour = !!(o.teamOn && d.hex && d.hex.length && root.SPBRevColourway && !root.SPBRevColourway.isOff());
        var nameStr = o.nameFrom === 'name' ? d.name : (d.text || d.name);          // 'auto' (default): the row's own text when it has one, else the driver name
        d._nameStr = nameStr;
        st.name = !!(o.nameOn && nameStr && root.SpbRevSponsor && !root.SpbRevSponsor.off());
        st.logo = !!(o.logoOn && d.logoKey && ST.logos[d.logoKey] && root.SpbRevSponsor && !root.SpbRevSponsor.off());
        return st;
    }


    // ------------------------------------------------------------------ [SPB-REV-LEAGUE 2026-10-10 follow-up] EVERY number on the car
    // The Number Kit swaps the numbers at its three places (doors + roof) and leaves a small fender / bumper / nose number alone on purpose. A league car must
    // carry the DRIVER'S number everywhere, so after the kit's own apply, every number-sized blob still left on the template's Numbers layer(s) is erased and the
    // same number is drawn in its place: the kit's style (slant included), sized to the old number's ink box, turned like the car-map part it sits on
    // (door / roof: that place's own turn; anywhere else: along the long side of the old number). The erase is recorded in the kit session (S.numbersBefore) and
    // the new layers carry the kit's id, so Cancel / Undo / the end of the run put every old number back with the rest of the kit.
    var EX = { minSide: 36, maxAspect: 4.5, pad: 0.2, near: 0.25 };
    function eraseBlobs(layer, lb, ids) {
        var cv = doc.createElement('canvas'); cv.width = lb.w; cv.height = lb.h; var g = cv.getContext('2d'); g.drawImage(layer.img, 0, 0);
        var set = {}; ids.forEach(function (i) { set[i] = 1; });
        g.globalCompositeOperation = 'destination-out'; g.fillStyle = '#000';
        for (var cy = 0; cy < lb.gh; cy++) for (var cx = 0; cx < lb.gw; cx++) if (set[lb.lab[cy * lb.gw + cx]]) g.fillRect(cx * 4, cy * 4, 4, 4);
        return cv;
    }
    function joinBlobs(blobs) {                              // digits further apart than the labeller's 12 px join belong to one number when their boxes nearly touch
        var cl = blobs.map(function (b) { return { ids: [b.id], box: b.box.slice() }; }), again = true;
        while (again) {
            again = false;
            for (var i = 0; i < cl.length && !again; i++) for (var j = i + 1; j < cl.length && !again; j++) {
                var a = cl[i].box, b = cl[j].box, pad = EX.pad * Math.max(a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1]);
                if (a[0] < b[2] + pad && a[2] > b[0] - pad && a[1] < b[3] + pad && a[3] > b[1] - pad) {
                    cl[i] = { ids: cl[i].ids.concat(cl[j].ids), box: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])] }; cl.splice(j, 1); again = true;
                }
            }
        }
        return cl;
    }
    function otherNumbers(S) {
        var NK = root.SpbRevNumbers, I = NK && NK._internal, out = { n: 0, boxes: [], skipped: 0, layers: [] };
        if (!S || S.closed || !I || !I.labelBlobs || !I.fitMatched || !I.renderArt || !I.turnArt || !I.tightBox) return out;
        var Lx = psdLayers(), C = I.regCur(), geo = S.geo, prim = NK.kitLayers(S.kid);
        if (!prim.length) return out;                        // the kit placed nothing (no car map / no room): there is no style to copy
        var kit = clone(NK.kitOf(prim[0]).kit), byPlace = {}, areas = [], F = (root.SPBRevLayerMat && root.SPBRevLayerMat.FIELD) || 'spbMaterial', added = [];
        prim.forEach(function (l) { var p = NK.kitOf(l); if (p) { byPlace[p.place] = p; areas.push(l.bbox.slice()); } });
        NK.numberLayers().forEach(function (layer) {
            var lb; try { lb = I.labelBlobs(layer); } catch (e) { warn('blobs', e); return; } if (!lb || !lb.blobs.length) return;
            joinBlobs(lb.blobs.filter(function (b) { return b.n >= 40; })).forEach(function (c) {
                var bx = c.box, w = bx[2] - bx[0], h = bx[3] - bx[1], cx = (bx[0] + bx[2]) / 2, cy = (bx[1] + bx[3]) / 2;
                if (Math.max(w, h) < EX.minSide || Math.max(w, h) / Math.max(1, Math.min(w, h)) > EX.maxAspect) { out.skipped++; return; }          // a speck / a stripe, not a number
                for (var a = 0; a < areas.length; a++) {                                                                                         // a leftover of a number the kit just replaced
                    var A = areas[a], ex = (A[2] - A[0]) * EX.near, ey = (A[3] - A[1]) * EX.near;
                    if (cx > A[0] - ex && cx < A[2] + ex && cy > A[1] - ey && cy < A[3] + ey) { out.skipped++; return; }
                }
                var theta = null;                                                                                                                // which part is it on? its place's own reading direction
                ['left', 'right', 'roof'].forEach(function (pl) {
                    if (theta !== null) return; var p = geo && geo.ok && geo.places && geo.places[pl]; if (!p || !C || !C.masks) return; var m = C.masks[p.part]; if (!m) return;
                    var xi = Math.round(cx), yi = Math.round(cy); if (xi < 0 || yi < 0 || xi >= C.W || yi >= C.H || !m[yi * C.W + xi]) return;
                    theta = byPlace[pl] ? byPlace[pl].at.theta * Math.PI / 180 : Math.atan2(p.r[1], p.r[0]);
                });
                var how = theta === null ? 'long side' : 'part'; if (theta === null) theta = w >= h ? 0 : Math.PI / 2;
                var q90 = Math.abs(Math.sin(theta)) > 0.7, uw = q90 ? h : w, uh = q90 ? w : h;
                var S0 = I.fitMatched(kit, uw, uh) * kit.size / 100, art = I.renderArt(kit, S0), tb = I.tightBox(art.canvas), off = tb ? [(tb[0] + tb[2]) / 2 - art.aw / 2, (tb[1] + tb[3]) / 2 - art.ah / 2] : [0, 0];
                var img = I.turnArt(art, theta), ct = Math.cos(theta), st = Math.sin(theta);
                var px = Math.round(cx - (ct * off[0] - st * off[1])), py = Math.round(cy - (st * off[0] + ct * off[1]));
                var nl = { id: 'numkit_' + S.kid + '_x' + (out.n + 1), name: 'Number ' + kit.number + ' - Small Number ' + (out.n + 1), path: '', visible: true, opacity: 255, blendMode: 'source-over', locked: false, alphaLock: false,
                    clippingMask: false, effects: null, bbox: [px - img.width / 2, py - img.height / 2, px + img.width / 2, py + img.height / 2], img: img };
                if (!NK.deserialize(nl, { kid: S.kid, place: 'free', kit: kit, at: { cx: px, cy: py, theta: Math.round(theta * 1800 / Math.PI) / 10, em: Math.round(S0 * 10) / 10, tw: Math.round(uw), th: Math.round(uh), m: 1 } })) return;
                if (!S.numbersBefore) S.numbersBefore = [];
                if (!S.numbersBefore.some(function (n) { return n.layer === layer; })) S.numbersBefore.push({ layer: layer, img: layer.img });   // cancel / commit / undo put the old numbers back
                layer.img = eraseBlobs(layer, lb, c.ids);
                ['groupName', 'groupChain', 'parentGroupKey'].forEach(function (k) { if (prim[0][k] !== undefined) nl[k] = clone(prim[0][k]); });
                if (prim[0][F]) nl[F] = clone(prim[0][F]);
                var at = 0; prim.concat(added).forEach(function (l) { at = Math.max(at, Lx.indexOf(l) + 1); });
                Lx.splice(at, 0, nl); added.push(nl);
                out.n++; out.boxes.push({ old: bx.map(Math.round), at: [px, py], turn: Math.round(theta * 180 / Math.PI), how: how, em: Math.round(S0) }); out.layers.push(nl);
            });
        });
        if (out.n) bumpRev();
        return out;
    }

    // ------------------------------------------------------------------ [SPB-REV-LEAGUE 2026-10-10 follow-up] the driver's art keeps its OWN finish when a team colour lands on it
    // Colourway Studio re-aims the colour-picked zones at the team colours ("this zone owns the red"). A white number fill that never belonged to any zone then falls
    // into the zone re-aimed at a white team accent, and takes that zone's finish (matte). The team colour must only recolour ITS zone, so while a driver is on the
    // car, the driver's art pixels (number / name / sponsor layers, fully opaque ones, judged by the colour the engine sees) are marked "exclude" on every re-aimed zone
    // that would NEWLY own them (owned now, not owned by the zone's pick before the Colourway). They fall to the zone that owned them before - for the white fill that is
    // Everything Else. Painter masks stay (only unset pixels are marked), the marks are taken off again after the render / preview.
    function rgbOfHex(h) { var m = /^#?([0-9a-f]{6})$/i.exec(String(h || '')); if (!m) return null; var n = parseInt(m[1], 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    function picksOf(z) {
        var out = []; if (!z) return out;
        if (z.colorMode === 'picker') { var c = rgbOfHex(z.pickerColor); if (c) out.push({ rgb: c, tol: z.pickerTolerance == null ? 40 : +z.pickerTolerance }); }
        else if (z.colorMode === 'multi' && Array.isArray(z.colors)) z.colors.forEach(function (e) { if (e && e.color_rgb) out.push({ rgb: e.color_rgb.slice(0, 3), tol: e.tolerance == null ? 40 : +e.tolerance }); });
        return out;
    }
    function zoneSnapPicks() { return (zoneList() || []).map(function (z) { return { name: z && z.name, picks: picksOf(z) }; }); }
    function ownedBy(picks, r, g, b) {                       // the engine's rule: BT.601-weighted distance inside 0.85 x tolerance (soft edge, then hardened at 0.15)
        for (var i = 0; i < picks.length; i++) { var p = picks[i], dr = p.rgb[0] - r, dg = p.rgb[1] - g, db = p.rgb[2] - b; if (Math.sqrt(0.30 * dr * dr + 0.59 * dg * dg + 0.11 * db * db) < 0.85 * p.tol) return true; }
        return false;
    }
    function samePicks(a, b) { return a.length === b.length && a.every(function (p, i) { var q = b[i]; return p.tol === q.tol && p.rgb[0] === q.rgb[0] && p.rgb[1] === q.rgb[1] && p.rgb[2] === q.rgb[2]; }); }
    function guardFinish(layers) {
        var info = { zones: [], px: 0 }, undo = [];
        function restore() { undo.forEach(function (u) { try { if (u.had) u.z.spatialMask = u.prev; else delete u.z.spatialMask; } catch (e) { warn('guard restore', e); } }); undo = []; }
        try {
            if (flagOn(root.SPB_REV_LEAGUE_GUARD_OFF) || !RUN || !RUN.zbase || !RUN.cw || !layers || !layers.length) return { info: info, restore: restore };   // SPB_REV_LEAGUE_GUARD_OFF: only this guard off
            var zs = zoneList() || [], moved = [];
            zs.forEach(function (z, i) {
                var b = RUN.zbase[i]; if (!b || b.name !== (z && z.name)) return;
                var cur = picksOf(z); if (!cur.length || samePicks(cur, b.picks)) return;
                if (z.useRegion && z.regionMask) return;       // a drawn-region zone is not colour-matched
                moved.push({ z: z, cur: cur, base: b.picks });
            });
            if (!moved.length) return { info: info, restore: restore };
            var pc = el('paintCanvas'), W = pc.width, H = pc.height;
            var cv = root._nuqPreviewComposite ? root._nuqPreviewComposite() : (root.buildLivePaintCompositeCanvas ? root.buildLivePaintCompositeCanvas() : pc);
            if (!cv || cv.width !== W || cv.height !== H) return { info: info, restore: restore };
            var cd = cv.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, W, H).data, masks = moved.map(function () { return null; }), cnt = moved.map(function () { return 0; });
            layers.forEach(function (l) {
                var im = l && l.img, bb = l && l.bbox; if (!im || !bb) return;
                var w = im.width || im.naturalWidth, h = im.height || im.naturalHeight; if (!w || !h) return;
                var c = doc.createElement('canvas'); c.width = w; c.height = h; var g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0);
                var d = g.getImageData(0, 0, w, h).data, x0 = Math.round(bb[0]), y0 = Math.round(bb[1]);
                for (var y = 0; y < h; y++) {
                    var yy = y0 + y; if (yy < 0 || yy >= H) continue;
                    for (var x = 0; x < w; x++) {
                        if (d[(y * w + x) * 4 + 3] < 250) continue;
                        var xx = x0 + x; if (xx < 0 || xx >= W) continue;
                        var p = (yy * W + xx) * 4, r = cd[p], gg = cd[p + 1], b = cd[p + 2];
                        for (var m = 0; m < moved.length; m++) {
                            if (!ownedBy(moved[m].cur, r, gg, b) || ownedBy(moved[m].base, r, gg, b)) continue;
                            if (!masks[m]) { var pv = moved[m].z.spatialMask; masks[m] = pv && pv.length === W * H ? (ArrayBuffer.isView(pv) ? pv.slice() : Uint8Array.from(pv)) : new Uint8Array(W * H); }
                            if (!masks[m][yy * W + xx]) { masks[m][yy * W + xx] = 2; cnt[m]++; }
                        }
                    }
                }
            });
            moved.forEach(function (mv, m) {
                if (!masks[m] || !cnt[m]) return;
                undo.push({ z: mv.z, had: Object.prototype.hasOwnProperty.call(mv.z, 'spatialMask'), prev: mv.z.spatialMask });
                mv.z.spatialMask = masks[m]; info.zones.push(mv.z.name); info.px += cnt[m];
            });
        } catch (e) { warn('finish guard', e); restore(); }
        return { info: info, restore: restore };
    }

    var RUN = null;     // { cw: colourway session or null, sig0, zbase }
    function colourStage(d, st, notes) {
        var CW = root.SPBRevColourway; if (!RUN || !RUN.cw) return;
        if (st.colour) {
            CW.setTeam(d.hex);
            var v = CW.variantById('team');
            if (!v) { notes.push('The team colour is (almost) the livery\'s own colour: nothing to change.'); if (RUN.cwAct !== 'orig') { CW.setVariant('orig'); RUN.cwAct = 'orig'; } return; }
            CW.setVariant('team'); RUN.cwAct = 'team';
        } else if (RUN.cwAct !== 'orig') { CW.setVariant('orig'); RUN.cwAct = 'orig'; }
    }
    function numberSession(d, commitMode) {
        var NK = root.SpbRevNumbers, kit = Object.assign({}, numKit(), { number: String(d.number) });
        var S = NK.begin({ kit: kit }); if (!S) return null;
        S.setReplace('replace'); S.measure(); S.scanExisting(); S.apply();
        if (ST.opts.allNumbers !== false) { try { S.extra = otherNumbers(S); } catch (e) { warn('other numbers', e); } }
        return S;
    }
    function nameSession(d) {
        var Sp = root.SpbRevSponsor, o = ST.opts, cv = textCanvas(d._nameStr, { font: o.font || 'Impact', caps: o.nameCaps, fill: o.nameFill, line: o.nameLine });
        if (!cv) return null;
        var slots = {}; Object.keys(Sp.DEFAULTS.slots).forEach(function (k) { slots[k] = false; }); slotsFor(o.nameSlot === 'rails' ? 'rails' : o.nameSlot).forEach(function (s) { slots[s] = true; });
        var S = Sp.begin({ kit: { name: d._nameStr, size: o.nameSize, material: 'none', slots: slots, clean: { on: false } }, logo: { canvas: cv, name: d._nameStr, kind: 'text' } });
        if (!S) return null; S.measure(); S.apply(); return S;
    }
    function logoSession(d) {
        var Sp = root.SpbRevSponsor, lg = ST.logos[d.logoKey], o = ST.opts, slots = {};
        Object.keys(Sp.DEFAULTS.slots).forEach(function (k) { slots[k] = false; });
        var m = logoSlotMap(); Object.keys(m).forEach(function (s) { slots[s] = true; });
        var S = Sp.begin({ kit: { name: lg.name, size: o.logoSize, material: 'none', slots: slots, clean: { on: false } }, logo: { canvas: lg.canvas, name: lg.name, kind: 'png', cleaned: true } });
        if (!S) return null; S.measure(); S.apply(); return S;
    }

    /** run fn() with the driver on the car; afterwards every live layer / session is taken off again. mode 'render' | 'preview' */
    async function withDriver(d, fn) {
        var st = stagesOf(d), notes = [], nk = null, sp = null, harvest = [], gd = null;
        try {
            colourStage(d, st, notes);
            nk = numberSession(d);
            if (!nk) notes.push('Number Kit could not place the number.');
            else if (!(nk.liveIds && nk.liveIds.length)) notes.push('No door / roof places found for the number.');
            if (st.name) {
                var ns = nameSession(d);
                if (ns) {
                    var Sp = root.SpbRevSponsor, L = psdLayers(), ks = Sp.kitLayers(ns.kid).slice();
                    ks.forEach(function (l) { var i = L.indexOf(l); if (i >= 0) L.splice(i, 1); });      // keep the layers, end the session (Sponsor Kit allows one session at a time)
                    try { ns.cancel(); } catch (e) { warn('name cancel', e); }
                    harvest = ks; if (!ks.length) notes.push('The name found no room on that part.');
                } else notes.push('The name text could not be built.');
            }
            if (st.logo) { sp = logoSession(d); if (!sp) notes.push('The sponsor logo could not be placed.'); else if (!(sp.liveIds && sp.liveIds.length)) notes.push('The sponsor logo found no room.'); }
            if (harvest.length) insertAtTemplate(harvest);
            bumpRev();
            try {                                                // follow-up 2026-10-10: the driver's art keeps its own finish
                var art = []; if (nk && root.SpbRevNumbers) art = art.concat(root.SpbRevNumbers.kitLayers(nk.kid)); if (sp && root.SpbRevSponsor) art = art.concat(root.SpbRevSponsor.kitLayers(sp.kid)); art = art.concat(harvest);
                gd = guardFinish(art); ST.lastGuard = gd.info;
            } catch (e) { warn('guard', e); }
            return await fn(notes);
        } finally {
            try { if (gd) gd.restore(); } catch (e) { warn('guard restore', e); }
            try { removeByRef(harvest); } catch (e) { warn('remove name', e); }
            try { if (sp && !sp.closed) sp.cancel(); } catch (e) { warn('sponsor cancel', e); }
            try { if (nk && !nk.closed) nk.cancel(); } catch (e) { warn('number cancel', e); }
            bumpRev();
        }
    }

    // ------------------------------------------------------------------ run-level setup: sessions that live for the whole grid
    function sessionsBusy() {
        var busy = [];
        try { if (root.SpbRevNumbers && root.SpbRevNumbers.session()) busy.push('Number Kit'); } catch (e) {}
        try { if (root.SpbRevSponsor && root.SpbRevSponsor.session()) busy.push('Sponsor Kit'); } catch (e) {}
        try { if (root.SPBRevColourway && root.SPBRevColourway.active()) busy.push('Colourway Studio'); } catch (e) {}
        return busy;
    }
    async function beginRun(rows) {
        var busy = sessionsBusy(); if (busy.length) throw new Error('Close ' + busy.join(' and ') + ' first (League Pack uses them).');
        if (!root.SpbRevNumbers || root.SpbRevNumbers.off()) throw new Error('The Number Kit is off, League Pack needs it.');
        var T = root.SpbRevSymTools; if (T && T.ensureBuilt) await T.ensureBuilt(false);
        RUN = { cw: null, cwAct: 'orig', sig0: projectSig(), saved: {}, t0: now(), zbase: zoneSnapPicks() };
        RUN.saved.preview = root.triggerPreviewRender; root.triggerPreviewRender = function () {};      // the grid owns the preview server while it runs (kits call this on every cancel)
        if (rows.some(function (d) { return ST.opts.teamOn && d.hex && d.hex.length; }) && root.SPBRevColourway && !root.SPBRevColourway.isOff()) {
            RUN.cw = root.SPBRevColourway.open({}); if (!RUN.cw) throw new Error('Colourway Studio could not read this paint (it needs a layered paint).');
        }
        doc.body.classList.add('spb-lg-busy');
    }
    function endRun() {
        var rep = { unchanged: null };
        try { if (RUN && RUN.cw && root.SPBRevColourway.active()) root.SPBRevColourway.close(false); } catch (e) { warn('colourway close', e); }
        try { bumpRev(); call('renderLayerPanel'); } catch (e) {}
        if (RUN) { var sig1 = projectSig(); rep = { before: RUN.sig0, after: sig1, unchanged: RUN.sig0 === sig1 }; }
        try { if (RUN && RUN.saved && RUN.saved.preview) root.triggerPreviewRender = RUN.saved.preview; } catch (e) { warn('restore preview', e); }
        RUN = null; doc.body.classList.remove('spb-lg-busy');
        return rep;
    }

    // ------------------------------------------------------------------ previews (the Live Preview path: /preview-render at a low scale)
    async function postPreview(b64, scale) {
        var pf = (typeof _psdPath !== 'undefined' && _psdPath) || templatePaintFile();
        var zs = root.buildServerZonesForRender(zoneList()), body = { paint_file: pf, paint_image_base64: b64, zones: zs, seed: 51, preview_scale: scale, force_refresh: true, preview_nonce: Date.now() + Math.floor(Math.random() * 1000) };
        try { var ap = root._getActiveImportedSpecMapPath ? root._getActiveImportedSpecMapPath() : (root.importedSpecMapPath || null); if (ap) body.import_spec_map = ap; } catch (e) {}
        for (var tries = 0; tries < 6; tries++) {
            var resp = await fetch(baseUrl() + '/preview-render', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            if (resp.status === 429 || resp.status === 409) { await sleep(500 + tries * 400); continue; }
            var j = await resp.json(); if (!j.success) throw new Error(j.error || 'The preview failed.');
            return j;
        }
        throw new Error('The preview server stayed busy.');
    }
    async function previewOf(d, scale) {
        var t0 = now();
        return withDriver(d, async function (notes) {
            var cv = root._nuqPreviewComposite ? root._nuqPreviewComposite() : root.buildLivePaintCompositeCanvas();
            var b64 = await root.canvasToBase64Async(cv, 'image/png');
            var j = await postPreview(b64, scale);
            return { paint: j.paint_preview, spec: j.spec_preview, ms: Math.round(now() - t0), notes: notes };
        });
    }
    var QUEUE = Promise.resolve();
    function lock(fn) { var p = QUEUE.then(fn, fn); QUEUE = p.then(function () {}, function () {}); return p; }
    /** thumbnails for the rows (only those that are valid and whose settings changed since the last tile). */
    function previewAll(rowsIn, opts) {
        opts = opts || {};
        return lock(async function () {
            var rows = (rowsIn || ST.rows).filter(function (d) { return d.ok; }); if (!rows.length) return { n: 0 };
            ST.busy = true; ST.cancel = false; emit('busy', { kind: 'preview' });
            var t0 = now(), tmpl = null, done = 0;
            try {
                await beginRun(rows);
                tmpl = templateHash(); ST.tmpl = tmpl;
                for (var i = 0; i < rows.length; i++) {
                    if (ST.cancel) break;
                    var d = rows[i], h = driverHash(d, tmpl), res = ST.results[d.custid];
                    if (!opts.force && res && res.thumbHash === h && res.thumb) { continue; }
                    emit('tile', { d: d, state: 'working' });
                    try { var r = await previewOf(d, ST.opts.thumb); ST.results[d.custid] = Object.assign(res || {}, { thumb: r.paint, thumbSpec: r.spec, thumbHash: h, thumbMs: r.ms, notes: r.notes }); done++; emit('tile', { d: d, state: 'ready' }); }
                    catch (e) { ST.results[d.custid] = Object.assign(res || {}, { thumbErr: String(e && e.message || e) }); emit('tile', { d: d, state: 'error', error: String(e && e.message || e) }); }
                }
            } catch (e) { emit('error', { error: String(e && e.message || e) }); throw e; }
            finally { var rep = endRun(); ST.busy = false; ST.lastPreview = { sec: Math.round((now() - t0) / 100) / 10, n: done, check: rep }; emit('idle', { kind: 'preview', check: rep }); }
            return ST.lastPreview;
        });
    }
    /** one driver's bigger preview (scale 0.5, paint + spec) */
    function previewOne(d) {
        return lock(async function () {
            ST.busy = true; emit('busy', { kind: 'one' });
            try { await beginRun([d]); var r = await previewOf(d, 0.5); ST.results[d.custid] = Object.assign(ST.results[d.custid] || {}, { big: r.paint, bigSpec: r.spec }); return r; }
            finally { var rep = endRun(); ST.busy = false; emit('idle', { kind: 'one', check: rep }); }
        });
    }

    // ------------------------------------------------------------------ render all
    function api(path, body) {
        return fetch(baseUrl() + '/api/rev-league/' + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) { return r.json(); });
    }
    function isIracingPath(p) { return /[\\\/]iracing[\\\/]paint/i.test(String(p || '')); }
    var STUBS = ['showRenderResults', 'notifyRenderComplete', 'playRenderDing'];
    async function renderDoRender(custid, dir) {
        var saved = {}, dom = {}, res = null, t0 = Date.now();
        function setDom(id, prop, v) { var e = el(id); if (!e) return; dom[id] = dom[id] || {}; if (!(prop in dom[id])) dom[id][prop] = e[prop]; e[prop] = v; }
        setDom('iracingId', 'value', custid); setDom('outputDir', 'value', dir); setDom('liveLinkCheckbox', 'checked', false); setDom('exportZipCheckbox', 'checked', false); setDom('skipDuplicateRenders', 'checked', false);
        STUBS.forEach(function (n) { saved[n] = root[n]; root[n] = function () {}; });
        var RN = (typeof RenderNotify !== 'undefined') ? RenderNotify : null, rnSaved = RN && RN.onRenderComplete; if (RN) RN.onRenderComplete = function () {};
        var toastSaved = root.showToast, errToast = ''; root.showToast = function (m, isErr) { if (isErr === true || isErr === 'error' || isErr === 'warn') errToast = String(m); try { return toastSaved && toastSaved.apply(root, arguments); } catch (e) {} };
        root._spbLastDoRenderAt = 0; root._spbRenderOutcome = null;
        try {
            await root.doRender();
            res = root._spbRenderOutcome;
        } finally {
            STUBS.forEach(function (n) { root[n] = saved[n]; }); if (RN) RN.onRenderComplete = rnSaved; root.showToast = toastSaved;
            Object.keys(dom).forEach(function (id) { var e = el(id); if (e) Object.keys(dom[id]).forEach(function (p) { e[p] = dom[id][p]; }); });
        }
        if (!res || res.at < t0) return { ok: false, error: errToast || 'The render did not start (check Source Paint and the zones).' };
        return res.ok ? { ok: true, seconds: res.elapsed, saved: res.saved } : { ok: false, error: res.error || 'The render failed.' };
    }
    /** Render every valid driver into <folder>/<custid>/. resume = skip drivers already done with the same hashes. */
    function renderAll(opts) {
        opts = opts || {};
        return lock(async function () {
            var rows = ST.rows.filter(function (d) { return d.ok; }), folder = String(ST.folder || '').trim();
            if (!rows.length) throw new Error('No valid drivers in the roster.');
            if (!folder) throw new Error('Pick a folder for the pack first.');
            if (!/^[a-zA-Z]:[\\\/]|^\\\\/.test(folder)) throw new Error('The folder must be a full path (like D:\\League\\Round 5).');
            var r0 = await api('prepare', { root: folder, custids: rows.map(function (d) { return d.custid; }) });
            if (!r0.ok) throw new Error(r0.error || 'The folders could not be made.');
            ST.busy = true; ST.cancel = false; emit('busy', { kind: 'render' });
            var T0 = now(), summary = { done: 0, skipped: 0, failed: 0, secs: [], failures: [] }, prefix = prefixName();
            try {
                await beginRun(rows);
                var tmpl = templateHash(); ST.tmpl = tmpl;
                var hashes = {}; rows.forEach(function (d) { hashes[d.custid] = driverHash(d, tmpl); });
                var stt = opts.fresh ? { ok: true, done: {} } : await api('status', { root: folder, template: tmpl, hashes: hashes, prefix: prefix });
                var doneMap = (stt && stt.done) || {};
                for (var i = 0; i < rows.length; i++) {
                    var d = rows[i], res = ST.results[d.custid] = ST.results[d.custid] || {};
                    if (ST.cancel) { res.state = res.state === 'done' || res.state === 'skipped' ? res.state : 'pending'; continue; }
                    if (doneMap[d.custid]) { res.state = 'skipped'; res.seconds = doneMap[d.custid].seconds; summary.skipped++; emit('tile', { d: d, state: 'skipped' }); continue; }
                    res.state = 'working'; emit('tile', { d: d, state: 'working', index: i, total: rows.length });
                    var t0 = now();
                    try {
                        var out = await withDriver(d, async function (notes) { var rr = await renderDoRender(d.custid, folder.replace(/[\\\/]+$/, '') + '\\' + d.custid); rr.notes = notes; return rr; });
                        if (!out.ok) throw new Error(out.error);
                        var secs = Math.round((now() - t0) / 100) / 10;
                        var mk = await api('mark', { root: folder, custid: d.custid, hash: hashes[d.custid], template: tmpl, prefix: prefix, meta: { seconds: secs, name: d.name, number: d.number, team: d.hex.join('/'), order: i + 1 } });
                        if (!mk.ok) throw new Error(mk.error || 'The files were not found after the render.');
                        res.state = 'done'; res.seconds = secs; res.renderSeconds = out.seconds; res.error = null; res.notes = out.notes; summary.done++; summary.secs.push(secs); emit('tile', { d: d, state: 'done', seconds: secs });
                    } catch (e) {
                        var msg = String(e && e.message || e);
                        if (ST.cancel || /abort|cancel/i.test(msg)) { res.state = 'pending'; res.error = 'Cancelled.'; emit('tile', { d: d, state: 'pending' }); continue; }
                        res.state = 'error'; res.error = msg; summary.failed++; summary.failures.push(d.custid + ': ' + msg); emit('tile', { d: d, state: 'error', error: msg });
                    }
                }
                if (!ST.cancel || summary.done + summary.skipped > 0) {
                    try { var fin = await api('finish', { root: folder, prefix: prefix, title: (opts.title || 'League Pack') }); summary.sheet = fin && fin.sheet; summary.readme = fin && fin.readme; summary.finishError = fin && !fin.ok ? fin.error : null; } catch (e) { warn('finish', e); }
                }
            } catch (e) { emit('error', { error: String(e && e.message || e) }); throw e; }
            finally {
                var rep = endRun(); ST.busy = false; summary.check = rep; summary.cancelled = ST.cancel; summary.total = rows.length; summary.wall = Math.round((now() - T0) / 100) / 10;
                summary.avg = summary.secs.length ? Math.round(summary.secs.reduce(function (a, b) { return a + b; }, 0) / summary.secs.length * 10) / 10 : null;
                ST.lastRun = summary; emit('idle', { kind: 'render', summary: summary });
            }
            return summary;
        });
    }
    function cancel() { ST.cancel = true; try { if (root.ShokkerAPI && root.ShokkerAPI._renderInProgress && root.ShokkerAPI.cancelRender) root.ShokkerAPI.cancelRender(); } catch (e) {} emit('cancel'); }

    // ------------------------------------------------------------------ Apply This Driver To The Project (normal undo steps, one per kit)
    function applyDriver(d) {
        return lock(async function () {
            var busy = sessionsBusy(); if (busy.length) throw new Error('Close ' + busy.join(' and ') + ' first.');
            var T = root.SpbRevSymTools; if (T && T.ensureBuilt) await T.ensureBuilt(false);
            var st = stagesOf(d), done = [];
            if (st.colour) {
                var CW = root.SPBRevColourway, s = CW.open({});
                if (s) { CW.setTeam(d.hex); if (CW.variantById('team')) { CW.setVariant('team'); done.push('team colour'); } var r = CW.close(true); }
            }
            var nk = numberSession(d); if (nk && nk.liveIds && nk.liveIds.length) { nk.commit(); done.push('number ' + d.number); } else if (nk) nk.cancel();
            if (st.name) { var ns = nameSession(d); if (ns && ns.liveIds && ns.liveIds.length) { ns.commit(); done.push('name'); } else if (ns) ns.cancel(); }
            if (st.logo) { var sp = logoSession(d); if (sp && sp.liveIds && sp.liveIds.length) { sp.commit(); done.push('sponsor'); } else if (sp) sp.cancel(); }
            toast('Applied ' + (d.name || d.custid) + ' to the project (' + done.join(', ') + '). Each step has its own Undo.', 'success');
            emit('applied', { d: d, done: done });
            return done;
        });
    }

    // ------------------------------------------------------------------ roster storage (project file via SPB_PERSIST, plus a local fallback)
    function setRoster(rows, folder) {
        ST.rows = (rows || []).map(function (r) { return { name: r.name || '', custid: r.custid || '', number: r.number || '', team: r.team || '', sponsor: r.sponsor || '', text: r.text || '' }; });
        if (folder != null) ST.folder = folder;
        validate(ST.rows, ST.logos); emit('roster'); saveLocal(); return ST.rows;
    }
    function rosterText() { return ORDER.join('\t') + '\n' + ST.rows.map(function (r) { return ORDER.map(function (k) { return String(r[k] || '').replace(/[\t\n]/g, ' '); }).join('\t'); }).join('\n'); }
    function saveLocal() { try { root.localStorage.setItem(LS_ROSTER, JSON.stringify({ rows: ST.rows.map(function (r) { var o = {}; ORDER.forEach(function (k) { o[k] = r[k]; }); return o; }), folder: ST.folder, opts: ST.opts })); } catch (e) {} }
    function loadLocal() { try { var j = JSON.parse(root.localStorage.getItem(LS_ROSTER) || 'null'); return j && Array.isArray(j.rows) ? j : null; } catch (e) { return null; } }
    function serialize() { return ST.rows.length || ST.folder ? { v: 1, rows: ST.rows.map(function (r) { var o = {}; ORDER.forEach(function (k) { o[k] = r[k]; }); return o; }), folder: ST.folder, opts: clone(ST.opts) } : undefined; }
    function restore(o) {
        if (!o || !Array.isArray(o.rows)) return { ok: true };
        if (o.opts) ST.opts = Object.assign({}, ST.opts, o.opts, { places: Object.assign({}, ST.opts.places, o.opts.places), logoSlots: Object.assign({}, ST.opts.logoSlots, o.opts.logoSlots) });
        setRoster(o.rows, o.folder || ''); return { ok: true };
    }
    function registerPersist() {
        var P = root.SPB_PERSIST; if (!P || typeof P.register !== 'function' || ST.persisted) return !!ST.persisted;
        ST.persisted = P.register('league', { label: 'League roster', project: true, save: serialize, load: restore, empty: function () { return !ST.rows.length; }, listen: function (f) { on(function (ev) { if (/^(roster|opts)/.test(ev)) f(); }); } });
        return ST.persisted;
    }
    function boot(n) {
        if (off()) return;
        if (!registerPersist() && (n || 0) < 60) setTimeout(function () { boot((n || 0) + 1); }, 1000);
        if (!ST.rows.length && !ST.booted) { ST.booted = true; var l = loadLocal(); if (l) { restore(l); } }
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { boot(0); }); else boot(0);

    root.SpbRevLeague = {
        version: VER, off: off, state: ST, on: on, emit: emit,
        parseRoster: parseRoster, validate: validate, toHex: toHex, parseTeam: parseTeam, setRoster: setRoster, rosterText: rosterText, saveLocal: saveLocal,
        addLogoFiles: addLogoFiles, numKit: numKit, textCanvas: textCanvas, stagesOf: stagesOf, driverHash: driverHash, templateHash: templateHash, projectSig: projectSig,
        previewAll: previewAll, previewOne: previewOne, renderAll: renderAll, cancel: cancel, applyDriver: applyDriver, withDriver: withDriver, beginRun: beginRun, endRun: endRun,
        isIracingPath: isIracingPath, prefixName: prefixName, sessionsBusy: sessionsBusy, serialize: serialize, restore: restore, api: api,
        _internal: { otherNumbers: otherNumbers, guardFinish: guardFinish, picksOf: picksOf, colourStage: colourStage, numberSession: numberSession, nameSession: nameSession, logoSession: logoSession, renderDoRender: renderDoRender, splitLine: splitLine }
    };
})(typeof window !== 'undefined' ? window : globalThis);
