/* [SPB-RENDER-CARD 2026-10-10] The screen after RENDER: logo + QR codes, the PAINT and SPEC files once, and a RECIPE that is read from the
 * render payload that was really sent (not guessed from the zone UI).  Lane RENDER-CARD, owner 10:35: "too much shit to confuse people after we click Render ...
 * the logo much bigger ... paint and spec above the logo box so they are duplicated ... the recipe underneath the second box too small ... more accurate now".
 *
 * WHY THE OLD SCREEN BROKE (proved, _easy_claude_work/ui_polish/render_card/REPORT.md): js/ui/spb-nuq-fix.js (NUQ-FIX "#13 render result: the buyer's own car
 * first, the branded card smaller and below it", 2026-10-10 01:26) injects `#renderCarPreviews{display:flex!important}` (the raw PAINT + SPEC images, which the
 * page's own css hides because the card already carries them) and `.recipe-card-canvas{max-width:620px}` (was 1200).  Two copies of paint + spec, a logo box
 * half its old size, and the recipe text drawn at 12 px then scaled to 42 %.  This file does not edit that file: while this screen is on, `html.spb-rc-on`
 * out-ranks those rules.
 *
 * What it adds (all additive, nothing deleted):
 *   - ShokkerAPI.render() hands the request body to SpbRenderCard.capture(body) (one guarded line); the body is slimmed (big strings / mask arrays become
 *     sizes) and kept with a sidecar of names (layers, kits, wear, fades) that only LABEL payload entries - they never add one.
 *   - renderRecipeCardUI(result) is wrapped: new screen = bar (one primary + a ... menu) / one status line / [logo + QR, PAINT, SPEC] / recipe.  The shareable
 *     PNG/PDF/clipboard card (window._recipeCardCanvas) is drawn from the SAME model, so screen, PNG and the Trading Paints text always agree.
 *   - If the screen cannot be built the page's own card (R-1 table fallback behind it) is used, and `spb-rc-on` is removed.
 * Kill switch: window.SPB_RENDER_CARD_OFF = true (or localStorage SPB_RENDER_CARD_OFF = '1') -> exactly the previous modal.
 * Public: window.SpbRenderCard = { VER, off, capture, last, model, audit, words, rebuild }.
 */
(function (root) {
    'use strict';
    var doc = root && root.document;
    if (!doc) return;
    // dev-only hot reload (test harness sets window.__spbRcReload before re-injecting the file): put the page's own functions back, then install again
    if (root.SpbRenderCard) {
        if (!root.__spbRcReload) return;
        try { if (root.__spbRcPrev) root.renderRecipeCardUI = root.__spbRcPrev; if (root.__spbRcPrevTP) root.buildTPDescription = root.__spbRcPrevTP; } catch (e) {}
        root.SpbRenderCard = null;
    }
    var VER = 'rc1.0', TAG = '[SPB-RENDER-CARD]';

    function flagOn(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() {
        try { if (flagOn(root.SPB_RENDER_CARD_OFF)) return true; return flagOn(root.localStorage && root.localStorage.getItem('SPB_RENDER_CARD_OFF')); }
        catch (e) { return flagOn(root.SPB_RENDER_CARD_OFF); }
    }
    function warn() { try { console.warn.apply(console, [TAG].concat([].slice.call(arguments))); } catch (e) {} }
    function $(id) { return doc.getElementById(id); }
    function el(tag, cls, text) { var e = doc.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
    function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
    function pct(v) { return Math.round(num(v, 0) * 100) + '%'; }
    function sgn(v) { v = num(v, 0); return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(Math.round(v * 100) / 100); }
    function round2(v) { return Math.round(num(v, 0) * 100) / 100; }
    function hex2(n) { n = Math.max(0, Math.min(255, Math.round(n))); return (n < 16 ? '0' : '') + n.toString(16); }
    function rgbHex(a) { if (!Array.isArray(a) || a.length < 3) return null; var s = a.some(function (x) { return num(x, 0) > 1.0001; }) ? 1 : 255; return ('#' + hex2(a[0] * s) + hex2(a[1] * s) + hex2(a[2] * s)).toUpperCase(); }
    function human(k) { return String(k).replace(/^_+/, '').replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }

    // ------------------------------------------------------------------------------------------------ payload capture
    function slim(v, d) {
        d = d || 0;
        if (v == null) return v;
        var t = typeof v;
        if (t === 'string') return v.length > 240 ? '<' + v.length + ' chars>' : v;
        if (t !== 'object') return v;
        if (Array.isArray(v)) {
            if (v.length > 64) return { '<array>': v.length };
            var n = []; for (var i = 0; i < v.length; i++) n.push(slim(v[i], d + 1)); return n;
        }
        if (root.ArrayBuffer && ArrayBuffer.isView(v)) return { '<bytes>': v.length };
        if (d > 9) return '<deep>';
        var o = {}; for (var k in v) { if (Object.prototype.hasOwnProperty.call(v, k)) o[k] = slim(v[k], d + 1); } return o;
    }
    function psdLayers() { try { return Array.isArray(root._psdLayers) ? root._psdLayers : (typeof _psdLayers !== 'undefined' ? _psdLayers : []); } catch (e) { return []; } }
    function kitInfo(api, l) { try { return api && api.kitOf ? api.kitOf(l) : null; } catch (e) { return null; } }
    // sponsor slot id -> the car part it sits on (names from js/rev/sponsor/sponsor-core.js SLOTS)
    var SLOT = { door_l: ['Left Door', 'Left side'], door_r: ['Right Door', 'Right side'], quarter_l: ['Left Rear Quarter', 'Left side'], quarter_r: ['Right Rear Quarter', 'Right side'],
        tv_l: ['Left TV Panel', 'Left side'], tv_r: ['Right TV Panel', 'Right side'], hood: ['Hood', 'Hood'], deck: ['Trunk / Deck', 'Trunk / deck'], rail_l: ['Left Roof Rail', 'Roof'], rail_r: ['Right Roof Rail', 'Roof'], free: ['Sheet Centre', 'Elsewhere'] };
    var NUMPLACE = { left: ['Left Door', 'Left side'], right: ['Right Door', 'Right side'], roof: ['Roof', 'Roof'], free: ['Sheet Centre', 'Elsewhere'] };
    /** Names for what the composite contained at the moment of RENDER.  Labels only: a line is shown only if the payload carries the thing it names. */
    function layerSnap() {
        var out = [], LM = root.SPBRevLayerMat;
        psdLayers().forEach(function (l) {
            if (!l) return;
            var it = { id: l.id, name: l.name || String(l.id), visible: l.visible !== false };
            var nk = kitInfo(root.SpbRevNumbers, l), sk = kitInfo(root.SpbRevSponsor, l);
            if (nk) { it.kind = 'number'; it.kid = nk.kid; it.place = nk.place; it.number = nk.kit && nk.kit.number; }
            else if (sk) { it.kind = 'sponsor'; it.kid = sk.kid; it.slot = sk.slot; try { var lg = root.SpbRevSponsor.logoOf && root.SpbRevSponsor.logoOf(sk.kid); if (lg && lg.name) it.logo = String(lg.name).replace(/\.[a-z0-9]{2,4}$/i, ''); } catch (e) {} if (sk.kit && sk.kit.name) it.logo = sk.kit.name; }
            else if (/^symstripe_/.test(String(l.id || ''))) it.kind = 'stripe';
            if (l.spbMaterial && LM) {
                var m = l.spbMaterial, d = ''; try { d = LM.describe(m); } catch (e) {}
                it.material = { desc: d, kind: (function () { try { return LM.refKind(m); } catch (e) { return null; } })(), finishId: m.finishId || null, preset: m.preset || null };
            }
            out.push(it);
        });
        return out;
    }
    function brushSide() { try { var s = root.SPBRevMaterial && root.SPBRevMaterial.stats && root.SPBRevMaterial.stats(); return s ? { hasSpec: !!s.hasSpec, hasPaint: !!s.hasPaint, coats: (s.coats || []).length } : null; } catch (e) { return null; } }
    // [TICKETS-3 2026-10-10 item 2, IQ3-3] the card used to say 'Spec Brush: Hand-painted shine' + 'spec bbox [x,y,w,h]' for a Spec Sculpt look, and gave every Material Brush
    // coat the whole finish's numbers whatever its mode. Now: the Sculpt look by name with the material it gave each colour (read from SPBSculpt2's own undo entry + colour
    // analysis at RENDER time: the payload only carries the spec bytes), and one row per brush coat naming ITS mode (Paint + Spec / Spec only / Paint only), finish,
    // sliders and the spec it paints. Kill switch: window.SPB_T3_OFF or SPB_T3_2_OFF -> the rows are written as before.
    function t3off(n) { try { return !!(root.SPB_T3_OFF || root['SPB_T3_' + n + '_OFF']); } catch (e) { return false; } }
    function hexWord(h) {
        var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(h || '')); if (!m) return '';
        var r = parseInt(m[1], 16) / 255, g = parseInt(m[2], 16) / 255, b = parseInt(m[3], 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
        if (l < 0.12) return 'black'; if (l > 0.93 && d < 0.1) return 'white';
        if (d < 0.12) return l < 0.35 ? 'dark grey' : l > 0.7 ? 'light grey' : 'grey';
        var hh = mx === r ? ((g - b) / d + (g < b ? 6 : 0)) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; hh *= 60;
        var n = (hh < 15 || hh >= 345) ? 'red' : hh < 40 ? 'orange' : hh < 70 ? 'yellow' : hh < 165 ? 'green' : hh < 200 ? 'cyan' : hh < 260 ? 'blue' : hh < 295 ? 'purple' : 'pink';
        return (l < 0.3 ? 'dark ' : l > 0.72 ? 'light ' : '') + n;
    }
    function sculptSide() {
        try {
            var S2 = root.SPBSculpt2, RM = root.SPBRevMaterial;
            if (t3off(2) || !S2 || (typeof S2.off === 'function' && S2.off()) || !RM || !RM.state) return null;
            var U = S2.undoState && S2.undoState.undo, e = U && U.length ? U[U.length - 1] : null;
            if (!e || !Array.isArray(e.assign) || e.sv !== RM.state.sv) return null;          // newest kept look, and the spec layer on the car is still the one it wrote
            var A = S2.state && S2.state.A, M = (typeof S2.mats === 'function' && S2.mats()) || {};
            if (!A || !Array.isArray(A.cl) || A.cl.length !== e.assign.length) return null;    // colours not known any more (page reloaded): the generic spec row is shown
            var look = null;
            (S2.looks || []).forEach(function (l) { try { var a = l.fn(A); if (!look && a && a.length === e.assign.length && a.every(function (v, i) { return (v || null) === (e.assign[i] || null); })) look = l.name; } catch (x) {} });
            var cols = A.cl.map(function (c) { var id = e.assign[c.i] || null, m = id && M[id]; return { i: c.i, hex: c.hex, share: c.share, blend: !!c.blend, mat: id, name: m ? m.name : null, m: m ? m.m : null, r: m ? m.r : null, cc: m ? m.cc : null }; });
            return { look: look, cols: cols };
        } catch (e) { return null; }
    }
    function coatGroups(mb) {   // a Paint + Spec stroke is two coats (paint plane, spec plane): one row for the pair; a Paint only / Spec only coat is its own row
        var out = [], by = {};
        mb.forEach(function (o) {
            var bs = o.c && o.c.bs, pl = o.c && o.c.plane;
            if (!bs || (pl !== 'paint' && pl !== 'spec')) { out.push({ coats: [o], planes: { paint: !(o.c && o.c.keep_colour), spec: true }, bs: bs || null }); return; }
            var both = bs.mode === 'both', key = [bs.finish_id, JSON.stringify(bs.params || {}), both ? 'both' : pl, o.c.keep_colour ? 1 : 0].join('|'), g = both ? by[key] : null;
            if (!g) { g = { coats: [], planes: { paint: false, spec: false }, bs: bs }; out.push(g); if (both) by[key] = g; }
            g.coats.push(o); g.planes[pl] = true;
        });
        return out;
    }
    function slidersText(p, planes) {
        p = p || {}; var out = [];
        if (planes.paint && p.color) { var tint = p.colorMode !== 'solid'; out.push((tint ? 'tint ' : 'solid ') + String(p.color) + ' ' + Math.round(num(tint ? p.colorDepth : p.colorStrength, 1) * 100) + '%'); }
        if (num(p.scale, 1) !== 1) out.push('scale ' + Math.round(num(p.scale, 1) * 100) + '%');
        if (num(p.rotation, 0)) out.push('rotation ' + Math.round(num(p.rotation, 0)) + '\u00b0');
        if (num(p.strength, 1) !== 1) out.push('strength ' + Math.round(num(p.strength, 1) * 100) + '%');
        if (planes.spec && num(p.specStrength, 1) !== 1) out.push('spec strength ' + Math.round(num(p.specStrength, 1) * 100) + '%');
        return out.length ? out.join('  \u00b7  ') : 'sliders at their defaults';
    }
    function wearSide() {
        try {
            var st = root.SpbRevWearUI && root.SpbRevWearUI.state && root.SpbRevWearUI.state();
            var r = st && st.rec; if (!r) return null;
            var W = root.SpbRevWear, nm = null, lt = null;
            try { var p = W && W.preset && W.preset(r.preset); nm = p && p.name || null; lt = W && W.lapsText ? W.lapsText(r.preset, r.laps) : null; } catch (e) {}
            return { preset: r.preset || null, name: nm, laps: r.laps, lapsText: lt, op: r.op, seed: r.seed, visible: r.visible !== false, decals: !!r.decals };
        } catch (e) { return null; }
    }
    function fadeSide() {
        try {
            var S = root.SpbRevFadeUI && root.SpbRevFadeUI.state; var recs = S && S.recs; if (!Array.isArray(recs)) return [];
            return recs.map(function (r) { var d = ''; try { d = root.SpbRevFadeUI.describe(r) || ''; } catch (e) {} return { id: r.id, name: r.name || 'Fade', desc: d, parts: r.parts || null, paint: !!r.paintOn }; });
        } catch (e) { return []; }
    }
    var LAST = (root.__spbRcReload && root.__spbRenderPayload) || null;   // survives the dev hot reload only
    function capture(body) {
        if (off()) return null;
        try {
            LAST = { at: Date.now(), body: slim(body), side: { layers: layerSnap(), wear: wearSide(), fades: fadeSide(), brush: brushSide(), sculpt: sculptSide() } };
            root.__spbRenderPayload = LAST;
            return LAST;
        } catch (e) { warn('capture skipped', e); return null; }
    }

    // ------------------------------------------------------------------------------------------------ painter words
    function atlasItem(id, kind) {
        try {
            var A = root.SpbAIAtlas; if (!A || !A.ready || !A.ready()) return null;
            var raw = String(id || '').replace(/^mono:/, '');
            return A.lookup((kind === 'mono' ? 'mono::' : 'base::') + raw) || A.lookup(raw);
        } catch (e) { return null; }
    }
    function wordsOf(it) {
        if (!it) return '';
        var s = String(it.shine || ''), m = String(it.metal || ''), p = [];
        if (s === 'mirror' && m === 'full') return 'mirror chrome';
        if (s) p.push(s);
        if (m === 'full') p.push('full metal'); else if (m === 'high') p.push('very metallic'); else if (m === 'medium') p.push('metallic'); else if (m === 'low') p.push('a little metallic');
        if (it.sk === 1) p.push('sparkles');
        return p.join(', ');
    }
    function rawSpecOf(it) {
        if (!it || !it.M) return '';
        return 'Metal ' + Math.round(it.M[0]) + ' · Roughness ' + Math.round(it.R[0]) + ' · Clearcoat ' + Math.round(it.C[0]) + '  (measured on the real render; clearcoat 16 = max gloss, 255 = none)';
    }
    function finishName(id) {
        try { if (typeof root._spbResolveFinishName === 'function') return root._spbResolveFinishName(id); } catch (e) {}
        try { if (typeof _spbResolveFinishName === 'function') return _spbResolveFinishName(id); } catch (e) {}
        return human(String(id || '').replace(/^mono:/, ''));
    }
    function patName(id) {
        var s = String(id || '');
        try { if (typeof root.getPatternName === 'function') { var n = root.getPatternName(s); if (n && n !== s && n.indexOf('None') !== 0) return n; } } catch (e) {}
        try { var sp = root.SPEC_PATTERNS; if (Array.isArray(sp)) { var f = sp.filter(function (x) { return x && x.id === s; })[0]; if (f && f.name) return f.name; } } catch (e) {}
        return human(s);
    }
    function chName(ch) { return ({ M: 'metal', R: 'roughness', C: 'clearcoat', MR: 'metal + roughness', MC: 'metal + clearcoat', RC: 'roughness + clearcoat', MRC: 'metal + roughness + clearcoat' })[String(ch || '').toUpperCase()] || String(ch || ''); }

    // ------------------------------------------------------------------------------------------------ model from the payload
    var PLUMB_ZONE = { render_seed_index: 1, render_version: 1, source_layer_revision: 1, source_layer_size: 1, source_layer_bbox: 1, source_layer_mask: 1, source_layer_rgb_png: 1,
        region_mask: 1, spatial_mask: 1, base_color_explicit: 1, hard_edge: 1, texture_anchor: 1, priority_override: 1 };
    var DEF_ZONE = { pattern: 'none', pattern_paint_mode: 'overlay', pattern_hue_shift: 0, pattern_saturation: 0, pattern_spec_opacity: 0, base_color_strength: 1, base_spec_strength: 1,
        intensity: '100', base_strength: 1, pattern_intensity: '100', base_color_mode: 'source', base_scale: 1, scale: 1, rotation: 0, base_rotation: 0, wear_level: 0 };
    var PLUMB_BODY = { paint_file: 1, iracing_id: 1, seed: 1, live_link: 1, output_dir: 1, use_custom_number: 1, paint_image_base64: 1, source_mode: 1, decal_mask_base64: 1, zones: 1 };
    var DEF_BODY = { wear_level: 0, export_zip: false, dual_spec: false };

    function same(a, b) { return a === b || (typeof a === 'number' && typeof b === 'string' && String(a) === b) || (typeof a === 'string' && typeof b === 'number' && a === String(b)); }

    function readZone(z, ctx) {
        var used = {}, lines = [];
        function use() { for (var i = 0; i < arguments.length; i++) used[arguments[i]] = 1; }
        function has(k) { return z[k] !== undefined && z[k] !== null; }
        function add(label, text, raw, src, tone) { var s2 = (src || []).filter(function (k) { return k in z; }); s2.forEach(function (k) { used[k] = 1; }); lines.push({ label: label, text: text, raw: raw || '', src: s2, tone: tone || '' }); }
        var zname = z.name || 'Zone'; use('name');

        // --- area (where it lands)
        var areaTxt = '', areaSrc = [];
        if (has('source_layer_id')) { var ln = ctx.layerName(z.source_layer_id); areaTxt = 'On the layer “' + ln + '”'; areaSrc.push('source_layer_id'); use('source_layer_revision', 'source_layer_size', 'source_layer_bbox', 'source_layer_mask', 'source_layer_rgb_png'); }
        if (has('region_mask') || has('spatial_mask')) { areaTxt += (areaTxt ? ', inside' : 'Inside') + ' the shape you painted'; areaSrc.push(has('region_mask') ? 'region_mask' : 'spatial_mask'); use('region_mask', 'spatial_mask'); }
        var col = z.color; use('color');
        var pick = '';
        if (col === 'remaining') pick = areaTxt ? 'whatever the zones above did not claim' : 'Everything the zones above did not claim'; else if (typeof col === 'string' && col) pick = (areaTxt ? 'paint matching' : 'Paint matching') + ' “' + col + '”'; else if (col && typeof col === 'object') pick = areaTxt ? 'a picked colour range' : 'A picked colour range';
        var area = [areaTxt, pick].filter(Boolean).join(' — ');
        if (area) add('Where', area, 'color = ' + JSON.stringify(col) + (has('source_layer_id') ? '  ·  layer id ' + z.source_layer_id : ''), areaSrc.concat(['color']));

        // --- finish / base
        var fid = z.finish || z.base, isFin = !!z.finish, hasMaterialStack = has('material_stack');
        if (fid && fid !== 'none') {
            var it = atlasItem(fid, isFin ? 'mono' : 'base'), w = wordsOf(it), nm = finishName(fid);
            if (w && w.toLowerCase() === String(nm).toLowerCase()) w = '';
            add('Finish', nm + (w ? '  —  ' + w : ''), (rawSpecOf(it) || ('id: ' + fid)) + (isFin ? '  ·  finish id ' + fid : '  ·  base id ' + fid), [isFin ? 'finish' : 'base', 'finish_colors']);
        }
        if (hasMaterialStack) {
            var ms = z.material_stack, tot = ms.reduce(function (a, r) { return a + num(r.weight, 0); }, 0) || 1;
            add('Mix', ms.map(function (r) { return finishName(r.id) + ' ' + Math.round(num(r.weight, 0) / tot * 100) + '%'; }).join('  +  '), JSON.stringify(ms), ['material_stack']);
            use('material_stack_amount', 'material_stack_mode', 'material_scale');
        }
        // --- colour
        var cm = z.base_color_mode, hexc = rgbHex(z.base_color), ctext = '', craw = [];
        if (cm === 'solid' && hexc) ctext = 'Solid ' + hexc;
        else if (cm === 'source' || (!cm && !hexc)) ctext = (cm === 'source' && !has('gradient_stops')) ? '' : '';
        else if (hexc) ctext = (human(cm) + ' ' + hexc);
        else if (cm) ctext = human(cm);
        if (has('base_color_source')) ctext = (ctext ? ctext + ' · ' : '') + 'colours from ' + finishName(String(z.base_color_source));
        if (Array.isArray(z.gradient_stops) && z.gradient_stops.length) ctext = (ctext ? ctext + ' · ' : '') + 'gradient, ' + z.gradient_stops.length + ' colours' + (z.gradient_direction ? ' (' + z.gradient_direction + ')' : '');
        if (cm === 'source' && fid && ctext === '') ctext = 'Keeps your source paint colour';
        if (ctext) add('Colour', ctext, 'base_color_mode = ' + cm + (hexc ? '  ·  rgb ' + JSON.stringify(z.base_color) : ''), ['base_color_mode', 'base_color', 'base_color_source', 'gradient_stops', 'gradient_direction']);
        else use('base_color_mode', 'base_color');
        // --- pattern
        var pl = [];
        if (has('pattern') && z.pattern !== 'none') {
            var ptxt = patName(z.pattern);
            if (has('pattern_opacity') && num(z.pattern_opacity, 1) !== 1) ptxt += ' ' + pct(z.pattern_opacity);
            if (has('scale') && num(z.scale, 1) !== 1) ptxt += ' · ' + round2(z.scale) + '× size';
            pl.push(ptxt); use('pattern', 'pattern_opacity', 'scale', 'pattern_intensity', 'pattern_manual', 'pattern_fit_zone', 'pattern_flip_h', 'pattern_flip_v', 'pattern_offset_x', 'pattern_offset_y', 'pattern_spec_mult', 'pattern_strength_map');
        }
        if (Array.isArray(z.pattern_stack)) {
            z.pattern_stack.forEach(function (p) { var t = patName(p.id); if (num(p.opacity, 1) !== 1) t += ' ' + pct(p.opacity); if (p.blend_mode && p.blend_mode !== 'normal') t += ' (' + p.blend_mode + ')'; if (num(p.scale, 1) !== 1) t += ' · ' + round2(p.scale) + '×'; pl.push(t); });
            use('pattern_stack');
        }
        if (pl.length) add('Pattern', pl.join('  ·  '), JSON.stringify(z.pattern_stack || z.pattern), ['pattern', 'pattern_stack']);
        // --- spec overlays (how it shines)
        var tiers = (typeof root.SPEC_PATTERN_STACK_TIERS !== 'undefined' && root.SPEC_PATTERN_STACK_TIERS) ? root.SPEC_PATTERN_STACK_TIERS.map(function (x) { return x[1]; })
            : ['spec_pattern_stack', 'overlay_spec_pattern_stack', 'third_overlay_spec_pattern_stack', 'fourth_overlay_spec_pattern_stack', 'fifth_overlay_spec_pattern_stack'];
        var sl = [], sk = [];
        tiers.forEach(function (tk) {
            if (!Array.isArray(z[tk]) || !z[tk].length) return; sk.push(tk);
            z[tk].forEach(function (s) { var t = patName(s.pattern); if (num(s.opacity, 1) !== 1) t += ' ' + pct(s.opacity); if (s.channels) t += ' (' + chName(s.channels) + ')'; if (s.blend_mode && s.blend_mode !== 'normal') t += ' · ' + s.blend_mode; sl.push(t); });
        });
        if (sl.length) add('Shine texture', sl.join('  ·  '), 'spec pattern stacks: ' + sk.join(', '), sk);
        // --- overlay bases
        [['second_base', '2nd base'], ['third_base', '3rd base'], ['fourth_base', '4th base'], ['fifth_base', '5th base']].forEach(function (pr) {
            var key = pr[0], any = Object.keys(z).filter(function (k) { return k === key || k.indexOf(key + '_') === 0; });
            if (!any.length) return;
            var t = has(key) ? finishName(z[key]) : (has(key + '_color_source') ? 'colours from ' + finishName(String(z[key + '_color_source'])) : 'overlay');
            var bits = [];
            if (has(key + '_strength')) bits.push(pct(z[key + '_strength']));
            var hx = rgbHex(z[key + '_color']); if (hx && hx !== '#FFFFFF') bits.push(hx);
            if (has(key + '_blend_mode') && z[key + '_blend_mode'] !== 'noise') bits.push(z[key + '_blend_mode']);
            if (has(key + '_pattern') && z[key + '_pattern'] && z[key + '_pattern'] !== '__none__') bits.push(patName(z[key + '_pattern']));
            add(pr[1], t + (bits.length ? '  ·  ' + bits.join(' · ') : ''), any.map(function (k) { return k + ' = ' + JSON.stringify(z[k]); }).join('\n'), any);
        });
        // --- blend into another base
        if (has('blend_base')) { add('Blend', 'into ' + finishName(z.blend_base) + (has('blend_amount') ? ' · ' + pct(num(z.blend_amount, 0) > 1 ? num(z.blend_amount, 0) / 100 : z.blend_amount) : '') + (z.blend_dir ? ' · ' + z.blend_dir : ''), '', ['blend_base', 'blend_amount', 'blend_dir', 'blend_mode']); }
        // --- spec map
        if (has('zone_spec_map')) { add('Spec map', 'Imported spec map' + (has('zone_spec_map_strength') ? ' · ' + Math.round(num(z.zone_spec_map_strength, 100) > 1 ? num(z.zone_spec_map_strength, 100) : num(z.zone_spec_map_strength, 1) * 100) + '%' : ''), '', ['zone_spec_map', 'zone_spec_map_strength']); }
        // --- dials (only what differs from the default)
        var dials = [], draw = [], dkeys = [];
        function dial(k, label, f) { if (!has(k)) return; if (same(z[k], DEF_ZONE[k])) { use(k); return; } var t = f ? f(z[k]) : String(z[k]); if (t == null || t === '') { use(k); return; } dials.push(label + ' ' + t); draw.push(k + ' = ' + JSON.stringify(z[k])); dkeys.push(k); use(k); }
        dial('intensity', 'Strength', function (v) { return (num(v, 100)) + '%'; });
        dial('base_strength', 'Base', pct); dial('base_spec_strength', 'Shine', pct); dial('base_color_strength', 'Colour', pct);
        dial('base_color_depth', 'Colour depth', pct); dial('base_color_flip', 'Colour flip', function (v) { return Math.round(num(v, 0)) + '°'; }); dial('base_color_underglow', 'Underglow', pct);
        dial('base_scale', 'Size', function (v) { return round2(v) + '×'; }); dial('base_rotation', 'Turn', function (v) { return Math.round(num(v, 0)) + '°'; }); dial('rotation', 'Turn', function (v) { return Math.round(num(v, 0)) + '°'; });
        dial('spec_scale', 'Shine size', function (v) { return round2(v) + '×'; }); dial('spec_rotation', 'Shine turn', function (v) { return Math.round(num(v, 0)) + '°'; });
        dial('base_hue_offset', 'Hue', sgn); dial('base_saturation_adjust', 'Saturation', sgn); dial('base_brightness_adjust', 'Brightness', sgn);
        dial('cc_quality', 'Clearcoat', function (v) { return String(v); }); dial('wear_level', 'Wear', function (v) { return num(v, 0) + '%'; });
        dial('custom_intensity', 'Custom strength', function (v) { return typeof v === 'object' ? 'custom' : String(v); });
        if (has('spec_channel_shift') && Array.isArray(z.spec_channel_shift) && z.spec_channel_shift.some(function (x) { return num(x, 0) !== 0; })) {
            var sc = z.spec_channel_shift, parts = []; if (num(sc[0], 0)) parts.push('Metal ' + sgn(sc[0])); if (num(sc[1], 0)) parts.push('Roughness ' + sgn(sc[1])); if (num(sc[2], 0)) parts.push('Clearcoat ' + sgn(sc[2]));
            dials.push(parts.join(' · ')); draw.push('spec_channel_shift = ' + JSON.stringify(sc)); dkeys.push('spec_channel_shift'); use('spec_channel_shift');
        }
        dial('base_offset_x', 'Slide across', sgn); dial('base_offset_y', 'Slide down', sgn); dial('base_color_rotation', 'Colour turn', function (v) { return Math.round(num(v, 0)) + '°'; });
        dial('base_color_scale', 'Colour size', function (v) { return round2(v) + '×'; }); dial('base_color_fit_zone', 'Colour fits zone', function (v) { return v ? 'yes' : ''; }); dial('base_spec_blend_mode', 'Shine blend', String);
        dial('pattern_paint_mode', 'Pattern colouring', String); dial('pattern_hue_shift', 'Pattern hue', sgn); dial('pattern_saturation', 'Pattern saturation', sgn); dial('pattern_spec_opacity', 'Pattern shine', function (v) { return num(v, 0) + '%'; });
        if (has('base_flip_h') && z.base_flip_h) { dials.push('Flipped left-right'); dkeys.push('base_flip_h'); } if (has('base_flip_v') && z.base_flip_v) { dials.push('Flipped up-down'); dkeys.push('base_flip_v'); }
        use('base_flip_h', 'base_flip_v');
        if (dials.length) add('Dials', dials.join('  ·  '), draw.join('\n'), dkeys);
        // --- spec lighting / remap / override: named, never silently dropped
        ['spec_lighting_mask', 'spec_material_remap', 'spec_material_override'].forEach(function (k) { if (has(k)) add(human(k.replace(/^spec_/, 'spec ')), 'On', JSON.stringify(z[k]), [k]); });
        // --- anything else in the payload that is not a default and not plumbing: shown so nothing the render used goes missing
        var other = [], okeys = [];
        Object.keys(z).forEach(function (k) {
            if (used[k] || PLUMB_ZONE[k]) return;
            if (k === '_spb_rev_material') { used[k] = 1; return; }
            if (k in DEF_ZONE && same(z[k], DEF_ZONE[k])) return;
            var v = z[k]; var vs = (v && typeof v === 'object') ? (Array.isArray(v) ? v.length + ' items' : 'set') : String(v);
            other.push(human(k) + ': ' + vs); okeys.push(k); used[k] = 1;
        });
        if (other.length) add('Other', other.join('  ·  '), okeys.map(function (k) { return k + ' = ' + JSON.stringify(z[k]); }).join('\n'), okeys);
        var chip = (fid && fid !== 'none') ? finishName(fid) : (hasMaterialStack ? 'Material mix' : 'Keeps source paint');
        var swatch = hexc || (z.color && typeof z.color === 'string' && z.color.charAt(0) === '#' ? z.color : null);
        return { kind: 'zone', name: zname, chip: chip, swatch: swatch, lines: lines, used: Object.keys(used) };
    }

    function layerNameMap(snap) { var m = {}; (snap || []).forEach(function (l) { m[l.id] = l.name; }); return m; }

    function readExtras(body, side, ctx) {
        // whole-car effects: only entries that exist in the payload; the sidecar (layer / kit / wear names) only LABELS them
        var cards = [], zs = body.zones || [], snap = (side && side.layers) || [], brush = (side && side.brush) || {};
        var lay = zs[0] && zs[0]._spb_rev_material;
        var eff = [];
        function add(label, text, raw, src) { eff.push({ label: label, text: text, raw: raw || '', src: src || [] }); }
        var visMat = snap.filter(function (l) { return l.visible && l.material; });
        if (lay && typeof lay === 'object') {
            var lmCoats = [], mbCoats = [];
            (Array.isArray(lay.coats) ? lay.coats : []).forEach(function (c, i) {
                var zo = (c && c.zone) || {}, nm = String(zo.name || ''), isLM = /^Layer Material:/i.test(nm);
                (isLM ? lmCoats : mbCoats).push({ c: c, i: i, zo: zo });
            });
            var T3 = !t3off(2);
            if (T3) {   // [TICKETS-3 item 2] one row per brush coat (a Paint + Spec pair is one row), each with its OWN mode, finish, sliders and the spec it paints
                var grp = coatGroups(mbCoats);
                grp.forEach(function (g, n) {
                    var o = g.coats[0], fid = o.zo.finish || o.zo.base, it = atlasItem(fid, o.zo.finish ? 'mono' : 'base'), w = wordsOf(it), bs = g.bs, pp = bs && bs.params;
                    var mode = g.planes.paint && g.planes.spec ? 'Paint + Spec' : g.planes.paint ? 'Paint only' : 'Spec only';
                    var bits = [finishName(fid) + (w ? '  —  ' + w : ''), mode];
                    if (bs) bits.push(slidersText(pp, g.planes));
                    if (g.planes.paint && g.coats.some(function (x) { return x.c.keep_colour; })) bits.push('keeps the paint colour');
                    var raw = [];
                    if (g.planes.spec) raw.push(rawSpecOf(it) ? 'Spec this coat paints: ' + rawSpecOf(it) + (pp && num(pp.specStrength, 1) !== 1 ? ' at ' + Math.round(num(pp.specStrength, 1) * 100) + '% spec strength' : '') : 'finish id ' + fid);
                    else raw.push('Paint only: this coat does not change the spec  (finish id ' + fid + ')');
                    if (!g.planes.paint) raw.push('Spec only: the paint colour is not changed');
                    raw.push('coat zone: ' + g.coats.map(function (x) { return x.zo.name; }).join('  +  '));
                    add('Material Brush' + (grp.length > 1 ? ' ' + (n + 1) : ''), bits.join('  ·  '), raw.join('\n'), g.coats.map(function (x) { return '_spb_rev_material.coats[' + x.i + ']'; }));
                });
            } else mbCoats.forEach(function (o, n) {
                var fid = o.zo.finish || o.zo.base, it = atlasItem(fid, o.zo.finish ? 'mono' : 'base'), w = wordsOf(it);
                add('Material Brush' + (mbCoats.length > 1 ? ' ' + (n + 1) : ''), finishName(fid) + (w ? '  —  ' + w : '') + (o.c.keep_colour ? '  ·  keeps the paint colour' : ''), (rawSpecOf(it) || ('finish id ' + fid)) + '\ncoat zone: ' + o.zo.name, ['_spb_rev_material.coats[' + o.i + ']']);
            });
            if (lay.spec) {
                var b = lay.spec.bbox || [], boxTxt = b.length === 4 ? '  ·  inside a ' + b[2] + ' × ' + b[3] + ' px box' : '';
                var lmSpec = visMat.filter(function (l) { return l.material.kind === 'spec'; });
                var sc = T3 && side && side.sculpt && brush.hasSpec ? side.sculpt : null;
                if (sc) {   // Spec Sculpt: the look by name + the material it gave each colour of the paint
                    var cn = sc.cols.map(function (c) { var nm = c.blend ? 'colour fade' : (c.i === 0 ? 'body (' + hexWord(c.hex) + ')' : hexWord(c.hex)); return nm + ' ' + (c.name || 'left to the zones'); });
                    var shown = cn.slice(0, 6).join('  ·  ') + (cn.length > 6 ? '  ·  +' + (cn.length - 6) + ' more' : '');
                    add('Spec Sculpt', (sc.look ? sc.look + ' look' : 'Hand-picked materials') + '  —  ' + sc.cols.length + (sc.cols.length === 1 ? ' colour: ' : ' colours: ') + shown,
                        sc.cols.map(function (c) { var pc = c.share * 100; return c.hex + '  ' + (pc < 1 ? '<1' : Math.round(pc)) + '% of the body  ->  ' + (c.name ? c.name + ' (Metal ' + c.m + ' · Roughness ' + c.r + ' · Clearcoat ' + c.cc + ')' : 'left to the zones'); }).join('\n'), ['_spb_rev_material.spec']);
                } else if (brush.hasSpec || !lmSpec.length) {
                    if (T3) add('Spec Brush', 'Shine painted by hand or with Spec Sculpt (metal / roughness / clearcoat)', 'the spec layer sent with this render', ['_spb_rev_material.spec']);
                    else add('Spec Brush', 'Hand-painted shine (metal / roughness / clearcoat)', 'spec bbox ' + JSON.stringify(b) + boxTxt, ['_spb_rev_material.spec']);
                }
            }
            if (lay.paint) { var b2 = lay.paint.bbox || []; add('Brushed paint', 'Colour painted with the Material / Wear brush', T3 ? 'the paint layer sent with this render' : 'paint bbox ' + JSON.stringify(b2), ['_spb_rev_material.paint']); }
            // Layer Materials: finish-kind ones are coats named "Layer Material: <finish>" in the payload; spec-kind ones are merged into spec
            lmCoats.forEach(function (o) {
                var fid = o.zo.finish || o.zo.base, it = atlasItem(fid, o.zo.finish ? 'mono' : 'base'), w = wordsOf(it);
                var on = visMat.filter(function (l) { return l.material.kind === 'finish'; }).map(function (l) { return '“' + l.name + '”'; });
                add('Layer Material', finishName(fid) + (w ? '  —  ' + w : '') + (on.length ? '  ·  on ' + on.join(', ') : '') + (o.c.keep_colour ? '  ·  keeps the art colour' : ''), (rawSpecOf(it) || ('finish id ' + fid)) + '\ncoat zone: ' + o.zo.name, ['_spb_rev_material.coats[' + o.i + ']']);
            });
            if (lay.spec) {
                var byDesc = {}, descOrder = [];
                visMat.filter(function (l) { return l.material.kind === 'spec'; }).forEach(function (l) { var d = l.material.desc || 'material'; if (!byDesc[d]) { byDesc[d] = []; descOrder.push(d); } byDesc[d].push(l.name); });
                descOrder.forEach(function (d) {
                    var ls = byDesc[d];
                    add('Layer Material', d + '  \u00b7  on ' + (ls.length > 3 ? ls.length + ' layers' : ls.map(function (x) { return '\u201c' + x + '\u201d'; }).join(', ')), ls.join(', '), ['_spb_rev_material.spec']);
                });
            }
            if (lay.wear) {
                var wr = side && side.wear, wt = 'Race Wear is on';
                if (wr && wr.name) wt = wr.name + (wr.lapsText ? ', ' + wr.lapsText : '') + (wr.op != null && wr.op !== 100 ? '  ·  ' + wr.op + '% strength' : '') + (wr.decals ? '  ·  keeps decals clean' : '');
                add('Race Wear', wt, wr ? JSON.stringify(wr) : 'wear layer in the payload', ['_spb_rev_material.wear']);
            }
            if (Array.isArray(lay.fade) && lay.fade.length) {
                lay.fade.forEach(function (f, i) {
                    var sd = side && side.fades && side.fades[i], nst = f && f.stops ? f.stops.length : 0;
                    add('Car-Space Fade' + (lay.fade.length > 1 ? ' ' + (i + 1) : ''), (sd && sd.name ? sd.name : 'Fade') + (sd && sd.desc ? '  ·  ' + sd.desc : '') + (nst ? '  ·  ' + nst + ' stops' : '') + (f && f.paint ? '' : '  ·  shine only'), (sd ? JSON.stringify(sd) + '\n' : '') + 'stops ' + nst, ['_spb_rev_material.fade[' + i + ']']);
                });
            }
        }
        if (body.edge_bleed) add('Edge Bleed', 'On — each panel’s edge paint and shine is copied a few pixels into the gaps', 'edge_bleed field present', ['edge_bleed']);
        if (num(body.wear_level, 0) > 0) add('Wear slider', num(body.wear_level, 0) + '% scuffs and weathering over the whole car', 'wear_level = ' + body.wear_level, ['wear_level']);
        if (body.dual_spec) add('Night spec', 'On — extra reflective night map' + (body.night_boost != null ? ' · boost ' + pct(body.night_boost) : ''), 'dual_spec, night_boost', ['dual_spec', 'night_boost']);
        if (body.export_zip) add('Export', 'ZIP package', '', ['export_zip']);
        if (body.import_spec_map) add('Spec map', 'Imported spec map: ' + String(body.import_spec_map).split(/[\\/]/).pop(), String(body.import_spec_map), ['import_spec_map']);
        if (Array.isArray(body.decal_spec_finishes) && body.decal_spec_finishes.length) add('Decal shine', body.decal_spec_finishes.map(function (d) { return finishName(d.specFinish); }).join(', '), JSON.stringify(body.decal_spec_finishes), ['decal_spec_finishes']);
        if (body.stamp_image_base64 || body.stamp_spec_finish) add('Spec stamps', finishName(body.stamp_spec_finish || 'gloss'), '', ['stamp_image_base64', 'stamp_spec_finish']);
        if (eff.length) cards.push({ kind: 'effects', name: 'Whole-car effects', chip: eff.length + (eff.length === 1 ? ' effect' : ' effects'), swatch: null, lines: eff.map(function (e) { e.tone = ''; return e; }) });

        // kits and the stripe: they are layers baked into paint_image_base64, so the payload only proves "a paint was sent"; the layer
        // snapshot at RENDER time (visible layers only) names them.  Grouped by part of the car.
        var by = {}, order = ['Left side', 'Right side', 'Hood', 'Roof', 'Trunk / deck', 'Down the middle', 'Elsewhere'];
        function put(part, line) { (by[part] = by[part] || []).push(line); }
        var hidden = 0, plain = 0, numKits = {}, spKits = {}, stripes = 0;
        snap.forEach(function (l) {
            if (!l.visible) { hidden++; return; }
            if (l.kind === 'number') { var nk = numKits[l.kid] = numKits[l.kid] || { number: l.number, places: [] }; nk.places.push(l.place); }
            else if (l.kind === 'sponsor') { var sp = spKits[l.kid] = spKits[l.kid] || { logo: l.logo, slots: [] }; sp.slots.push(l.slot); }
            else if (l.kind === 'stripe') stripes++;
            else plain++;
        });
        Object.keys(numKits).forEach(function (k) { var nk = numKits[k]; nk.places.forEach(function (p) { var pp = NUMPLACE[p] || NUMPLACE.free; put(pp[1], { label: 'Number Kit', text: 'Number ' + (nk.number != null ? nk.number : '?') + ' — ' + pp[0], raw: 'number kit ' + k + ', place ' + p, src: ['layer:' + k] }); }); });
        Object.keys(spKits).forEach(function (k) { var sp = spKits[k]; sp.slots.forEach(function (s) { var pp = SLOT[s] || SLOT.free; put(pp[1], { label: 'Sponsor Kit', text: (sp.logo || 'Sponsor logo') + ' — ' + pp[0], raw: 'sponsor kit ' + k + ', slot ' + s, src: ['layer:' + k] }); }); });
        if (stripes) put('Down the middle', { label: 'Car Stripe', text: (stripes > 1 ? stripes + ' stripes' : 'Stripe') + ' along the middle of the car — bumper, hood, roof, trunk', raw: stripes + ' layer(s) named Car Stripe', src: ['layer:stripe'] });
        var lines = [];
        order.forEach(function (p) { (by[p] || []).forEach(function (ln) { ln.part = p; lines.push(ln); }); });
        if (lines.length) cards.push({ kind: 'car', name: 'On the car', chip: lines.length + (lines.length === 1 ? ' item' : ' items'), swatch: null, lines: lines, grouped: true });
        return { cards: cards, plain: plain, hidden: hidden, layerCount: snap.length };
    }

    function buildModel(result, cap) {
        cap = cap || LAST; if (!cap) return null;
        var body = cap.body || {}, side = cap.side || {}, ctx = { layerName: function (id) { return layerNameMap(side.layers)[id] || String(id); } };
        var zs = Array.isArray(body.zones) ? body.zones : [];
        var zoneCards = zs.map(function (z) { return readZone(z, ctx); });
        var ex = readExtras(body, side, ctx);
        var sections = [{ id: 'zones', title: 'Paint zones', cards: zoneCards }];
        ex.cards.forEach(function (c) { sections.push({ id: c.kind, title: c.name, cards: [c] }); });
        var pf = String(body.paint_file || ''); pf = pf.split(/[\\/]/).pop();
        var model = {
            title: 'RENDER RECIPE', elapsed: result && result.elapsed_seconds, zoneCount: (result && result.zone_count) || zoneCards.length, timestamp: cap.at || Date.now(),
            paintFile: pf, sections: sections, zones: zoneCards, facts: { layers: ex.layerCount, hidden: ex.hidden, plain: ex.plain, seed: body.seed, iracingId: body.iracing_id },
            version: VER, fromPayload: true
        };
        return model;
    }

    /** Proof helper: every payload key is shown, a default or plumbing; every line's source exists in the payload. */
    function audit(cap, model) {
        cap = cap || LAST; model = model || buildModel(null, cap); var body = cap.body, rep = { zones: [], body: {}, phantom: [] };
        (body.zones || []).forEach(function (z, i) {
            var card = model.zones[i], used = {}; card.used.forEach(function (k) { used[k] = 1; }); var sh = [], df = [], pl = [], un = [];
            Object.keys(z).forEach(function (k) { if (used[k]) sh.push(k); else if (PLUMB_ZONE[k]) pl.push(k); else if (k in DEF_ZONE && same(z[k], DEF_ZONE[k])) df.push(k); else if (k === '_spb_rev_material') sh.push(k); else un.push(k); });
            card.lines.forEach(function (ln) { if (!ln.src.length) rep.phantom.push(card.name + ': "' + ln.label + '" has no payload key'); ln.src.forEach(function (s) { if (!(s in z)) rep.phantom.push(card.name + ': ' + s); }); });
            rep.zones.push({ name: z.name, keys: Object.keys(z).length, shown: sh.length, defaults: df.length, plumbing: pl.length, unmapped: un });
        });
        var bk = Object.keys(body), bs = [], bd = [], bp = [], bu = [];
        var shownBody = { wear_level: 1, dual_spec: 1, night_boost: 1, export_zip: 1, import_spec_map: 1, decal_spec_finishes: 1, stamp_image_base64: 1, stamp_spec_finish: 1, edge_bleed: 1, decal_mask_base64: 0 };
        bk.forEach(function (k) { if (shownBody[k]) bs.push(k); else if (PLUMB_BODY[k]) bp.push(k); else if (k in DEF_BODY && same(body[k], DEF_BODY[k])) bd.push(k); else bu.push(k); });
        rep.body = { keys: bk.length, shown: bs, defaults: bd, plumbing: bp, unmapped: bu };
        var lay = body.zones && body.zones[0] && body.zones[0]._spb_rev_material; rep.rev = lay ? Object.keys(lay) : [];
        rep.revUnmapped = []; rep.revMissing = [];
        if (lay) { var KNOWN = { coats: 1, spec: 1, paint: 1, wear: 1, fade: 1 }, INFO = { layermat: 1 }, PLB = { v: 1, size: 1 }, srcAll = [];
            model.sections.forEach(function (sc) { sc.cards.forEach(function (c) { c.lines.forEach(function (l) { l.src.forEach(function (x) { srcAll.push(x); }); }); }); });
            Object.keys(lay).forEach(function (k) { if (KNOWN[k]) { if (!srcAll.some(function (x) { return x.indexOf('_spb_rev_material.' + k) === 0; })) rep.revMissing.push(k); } else if (!INFO[k] && !PLB[k]) rep.revUnmapped.push(k); }); }
        model.sections.forEach(function (s) { s.cards.forEach(function (c) { if (c.kind === 'zone') return; c.lines.forEach(function (ln) { ln.src.forEach(function (sr) {
            var m = /^_spb_rev_material\.([a-z]+)/.exec(sr); if (m && !(lay && lay[m[1]] != null)) rep.phantom.push(c.name + ': ' + sr);
            else if (!m && sr.indexOf('layer:') !== 0 && !(sr in body)) rep.phantom.push(c.name + ': ' + sr);
        }); }); }); });
        return rep;
    }

    // ------------------------------------------------------------------------------------------------ styles
    var CSS = [
        /* off-screen unless the screen is on; every rule is keyed on html.spb-rc-on so the kill switch is the previous modal */
        '#spbRcBar{display:none}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal{padding:0!important;background:#0b0905!important;border:1px solid rgba(255,200,80,.35)!important;border-top:2px solid #ffd142!important}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal .rc-oldbar,html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderCarPreviews,html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderLiveLinkMsg,html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderHelmetSuitRow{display:none!important}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #spbRcBar{display:flex!important;order:0}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderStatusBanner{order:1;margin:0!important;border-radius:0!important;border-width:0 0 1px 0!important;box-shadow:none!important;padding:7px 16px!important;font-size:12.5px!important;text-align:left!important;line-height:1.4!important;flex:0 0 auto}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderStatusBanner code{font-size:11.5px;display:inline-block;max-width:min(46vw,620px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderStatusBanner .rc-more{margin-top:5px}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderStatusBanner .rc-more>summary{cursor:pointer;font-size:11px;opacity:.85;list-style:none;display:inline-block}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderStatusBanner .rc-more>summary::-webkit-details-marker{display:none}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #recipeCardStage{order:2;display:block!important;overflow:auto!important;padding:0!important;border-radius:0!important;background:radial-gradient(1200px 420px at 10% -10%,rgba(255,190,60,.10),transparent 60%),#0b0905!important;flex:1 1 auto;min-height:0}',
        'html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderDeployRow,html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderZipRow,html.spb-rc-on body #renderResultsPanel.spb-render-modal #renderNightRow{order:4;margin:0 16px 8px!important}',
        '#spbRcBar{align-items:center;gap:8px;flex-wrap:wrap;padding:9px 16px;background:linear-gradient(90deg,rgba(255,190,60,.14),rgba(255,120,0,.04));border-bottom:1px solid rgba(255,200,80,.28);flex:0 0 auto;position:relative}',
        '#spbRcBar .rc-title{font:800 15px/1 "Segoe UI",system-ui,sans-serif;letter-spacing:1.2px;color:#ffd142}',
        '#spbRcBar .rc-chip{font:700 12px/1 "Segoe UI",system-ui,sans-serif;color:#e8d9a8;padding:4px 9px;border-radius:999px;background:rgba(255,200,80,.10);border:1px solid rgba(255,200,80,.25)}',
        '#spbRcBar .rc-grow{flex:1 1 auto}',
        '#spbRcBar button{font:700 12.5px/1 "Segoe UI",system-ui,sans-serif;padding:8px 14px;border-radius:7px;cursor:pointer;border:1px solid rgba(255,200,80,.45);background:rgba(255,200,80,.07);color:#f6efdc;white-space:nowrap}',
        '#spbRcBar button:hover{background:rgba(255,200,80,.18)}',
        '#spbRcBar button:focus-visible{outline:2px solid #63d8ff;outline-offset:2px}',
        '#spbRcBar button.rc-primary{background:linear-gradient(180deg,#ffd142,#e6a500);color:#1a1204;border-color:#ffd142}',
        '#spbRcBar button.rc-primary:hover{filter:brightness(1.08)}',
        '#spbRcBar button.rc-close{border-color:rgba(255,107,107,.7);color:#ff8a8a;background:transparent}',
        '#spbRcBar button[disabled]{opacity:.55;cursor:progress}',
        '#spbRcMenu{position:absolute;right:104px;top:100%;z-index:5;min-width:250px;background:#15100a;border:1px solid rgba(255,200,80,.45);border-radius:9px;box-shadow:0 14px 40px rgba(0,0,0,.65);padding:5px;display:none}',
        '#spbRcMenu.open{display:block}',
        '#spbRcMenu button{display:block;width:100%;text-align:left;border:0;background:transparent;padding:9px 12px;border-radius:6px;font-weight:600}',
        '#spbRcMenu button small{display:block;font-weight:500;opacity:.7;margin-top:3px;font-size:11px;white-space:normal}',
        '#spbRcScreen{display:grid;grid-template-columns:clamp(400px,min(40vw,63vh),780px) minmax(0,1fr);gap:22px;padding:18px 20px 24px;align-items:start;max-width:1800px;margin:0 auto}',
        '#spbRcScreen .rc-left{display:flex;flex-direction:column;gap:14px;min-width:0}',
        '#spbRcScreen .rc-brand{border-radius:14px;overflow:hidden;border:1px solid rgba(255,200,80,.35);background:#000;box-shadow:0 10px 36px rgba(0,0,0,.55)}',
        '#spbRcScreen .rc-brand img{display:block;width:100%;height:auto}',
        '#spbRcScreen .rc-shots{display:grid;grid-template-columns:1fr 1fr;gap:12px}',
        '#spbRcScreen .rc-shot{min-width:0}',
        '#spbRcScreen .rc-shot h4{margin:0 0 5px;font:800 12px/1.2 "Segoe UI",system-ui,sans-serif;letter-spacing:1px;color:#ffd142;display:flex;justify-content:space-between;gap:8px}',
        '#spbRcScreen .rc-shot h4 span{font:500 11px/1.2 Consolas,monospace;color:#9d916f;letter-spacing:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
        '#spbRcScreen .rc-shot .rc-img{border-radius:10px;border:1px solid rgba(255,200,80,.30);background:#05070e;aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;overflow:hidden}',
        '#spbRcScreen .rc-shot img{display:block;max-width:100%;max-height:100%;object-fit:contain}',
        '#spbRcScreen .rc-shot .rc-none{color:#8d7f5b;font:13px "Segoe UI",sans-serif}',
        '#spbRcScreen .rc-right{min-width:0}',
        '#spbRcScreen .rc-rh{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 10px}',
        '#spbRcScreen .rc-rh h3{margin:0;font:800 17px/1 "Segoe UI",system-ui,sans-serif;color:#ffd142;letter-spacing:.6px}',
        '#spbRcScreen .rc-rh .rc-sub{font:600 12.5px/1.2 "Segoe UI",system-ui,sans-serif;color:#c9b98d}',
        '#spbRcScreen .rc-rh label{margin-left:auto;font:600 12px "Segoe UI",system-ui,sans-serif;color:#c9b98d;cursor:pointer;display:flex;gap:6px;align-items:center}',
        '#spbRcScreen .rc-sec{margin:0 0 16px}',
        '#spbRcScreen .rc-sec>h5{margin:0 0 7px;font:800 11.5px/1 "Segoe UI",system-ui,sans-serif;letter-spacing:1.4px;text-transform:uppercase;color:#b8871f}',
        '#spbRcScreen .rc-card{background:rgba(26,20,10,.94);border:1px solid rgba(255,200,80,.24);border-left:5px solid var(--rc-sw,#5b4a22);border-radius:11px;padding:10px 14px 9px;margin:0 0 9px}',
        '#spbRcScreen .rc-ch{display:flex;align-items:center;gap:10px;margin:0 0 6px}',
        '#spbRcScreen .rc-sw{width:20px;height:20px;border-radius:5px;border:1px solid rgba(255,255,255,.3);flex:none;background:var(--rc-sw,#334)}',
        '#spbRcScreen .rc-cn{font:800 15.5px/1.2 "Segoe UI",system-ui,sans-serif;color:#f6efdc;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
        '#spbRcScreen .rc-fin{margin-left:auto;font:700 12px/1 "Segoe UI",system-ui,sans-serif;color:#171106;background:#ffd142;border-radius:999px;padding:5px 11px;white-space:nowrap;max-width:46%;overflow:hidden;text-overflow:ellipsis}',
        '#spbRcScreen .rc-fin.soft{background:rgba(255,200,80,.16);color:#f6efdc}',
        '#spbRcScreen .rc-l{display:grid;grid-template-columns:112px minmax(0,1fr);gap:10px;padding:3px 0;border-top:1px solid rgba(255,200,80,.07);font:13.5px/1.4 "Segoe UI",system-ui,sans-serif}',
        '#spbRcScreen .rc-l:first-of-type{border-top:0}',
        '#spbRcScreen .rc-lk{font:700 10.5px/1.9 "Segoe UI",system-ui,sans-serif;letter-spacing:.9px;text-transform:uppercase;color:#8d7f5b}',
        '#spbRcScreen .rc-lv{color:#f1e8cf;min-width:0;overflow-wrap:anywhere;cursor:help}',
        '#spbRcScreen .rc-lv b{font-weight:700;color:#ffe08a}',
        '#spbRcScreen .rc-raw{display:none;margin-top:2px;font:11px/1.4 Consolas,monospace;color:#9d916f;white-space:pre-wrap;overflow-wrap:anywhere}',
        '#spbRcScreen.rc-showraw .rc-raw{display:block}',
        '#spbRcScreen .rc-part{font:800 11px/1 "Segoe UI",sans-serif;letter-spacing:1px;text-transform:uppercase;color:#63d8ff;margin:8px 0 2px}',
        '#spbRcScreen .rc-foot{margin:6px 2px 0;font:12px/1.5 "Segoe UI",system-ui,sans-serif;color:#8d7f5b}',
        '#spbRcScreen .rc-empty{color:#c9b98d;font:13.5px "Segoe UI",sans-serif;padding:8px 2px}',
        '@media (min-height:760px) and (min-width:981px){#spbRcScreen .rc-left{position:sticky;top:0}}',
        '@media (max-width:980px){#spbRcScreen{grid-template-columns:minmax(0,1fr);max-width:760px}#spbRcScreen .rc-brand{max-width:560px;margin:0 auto}}',
        '@media (max-width:760px){#spbRcScreen .rc-shots{grid-template-columns:1fr}#spbRcScreen .rc-l{grid-template-columns:90px minmax(0,1fr)}}'
    ].join('\n');
    function ensureStyle() {
        var old = $('spbRcStyle');
        if (old) { if (old.textContent !== CSS) old.textContent = CSS; return; }
        var st = el('style'); st.id = 'spbRcStyle'; st.textContent = CSS; (doc.head || doc.documentElement).appendChild(st);
    }

    // ------------------------------------------------------------------------------------------------ screen
    var MODEL = null, BUSY = 0;
    function logoUrl() { return root.SPB_QR_LOGO_DATAURL || root.SPB_LOGO_DATAURL || ''; }
    function imgSrc(id) { var i = $(id); return (i && i.getAttribute('src')) ? i.src : ''; }

    function buildCard(c, grouped) {
        var card = el('div', 'rc-card');
        if (c.swatch) card.style.setProperty('--rc-sw', c.swatch);
        var h = el('div', 'rc-ch');
        if (c.kind !== 'zone') h.style.display = 'none';   // effects / on-the-car cards: the section heading already names them
        if (c.kind === 'zone') { var sw = el('span', 'rc-sw'); if (c.swatch) sw.style.setProperty('--rc-sw', c.swatch); h.appendChild(sw); }
        h.appendChild(el('div', 'rc-cn', c.name));
        if (c.chip) h.appendChild(el('span', 'rc-fin' + (c.kind === 'zone' && c.chip === 'Keeps source paint' ? ' soft' : (c.kind !== 'zone' ? ' soft' : '')), c.chip));
        card.appendChild(h);
        var lastPart = null;
        if (!c.lines.length) card.appendChild(el('div', 'rc-empty', 'No changes recorded for this zone.'));
        c.lines.forEach(function (ln) {
            if (grouped && ln.part !== lastPart) { lastPart = ln.part; card.appendChild(el('div', 'rc-part', ln.part)); }
            var row = el('div', 'rc-l'); row.appendChild(el('div', 'rc-lk', ln.label));
            var v = el('div', 'rc-lv'); v.textContent = ln.text; if (ln.raw) { v.title = ln.raw; var r = el('div', 'rc-raw', ln.raw); v.appendChild(r); }
            row.appendChild(v); card.appendChild(row);
        });
        return card;
    }

    function buildScreen(model) {
        var scr = el('div'); scr.id = 'spbRcScreen';
        var left = el('div', 'rc-left'), right = el('div', 'rc-right');
        var bn = el('div', 'rc-brand'); var lu = logoUrl();
        if (lu) { var im = el('img'); im.alt = 'Shokker Paint Booth — join the Discord, get the app'; im.src = lu; bn.appendChild(im); } else { bn.appendChild(el('div', 'rc-empty', 'SHOKKER PAINT BOOTH')); }
        left.appendChild(bn);
        var shots = el('div', 'rc-shots');
        [['Paint', 'renderPaintPreview', 'renderPaintPreviewLabel'], ['Spec map', 'renderSpecPreview', 'renderSpecPreviewLabel']].forEach(function (s) {
            var box = el('div', 'rc-shot'), h4 = el('h4', null, s[0]); var lab = ($(s[2]) || {}).textContent || ''; var fm = /\(([^)]+)\)/.exec(lab); if (fm) h4.appendChild(el('span', null, fm[1]));
            box.appendChild(h4); var w = el('div', 'rc-img'); var src = imgSrc(s[1]);
            if (src) { var im2 = el('img'); im2.alt = s[0] + ' file of this render'; im2.src = src; w.appendChild(im2); } else w.appendChild(el('span', 'rc-none', 'no image'));
            box.appendChild(w); shots.appendChild(box);
        });
        left.appendChild(shots);
        var rh = el('div', 'rc-rh'); rh.appendChild(el('h3', null, 'Recipe'));
        var zc = model.zones.length, ex = model.sections.filter(function (s) { return s.id !== 'zones'; }).reduce(function (a, s) { return a + s.cards[0].lines.length; }, 0);
        rh.appendChild(el('span', 'rc-sub', zc + (zc === 1 ? ' zone' : ' zones') + (ex ? '  ·  ' + ex + ' more ' + (ex === 1 ? 'item' : 'items') : '') + '  ·  read from what was sent to the render'));
        var lbl = el('label'); var cb = el('input'); cb.type = 'checkbox'; cb.id = 'spbRcRawToggle'; cb.addEventListener('change', function () { scr.classList.toggle('rc-showraw', cb.checked); });
        lbl.appendChild(cb); lbl.appendChild(doc.createTextNode('Show exact numbers')); lbl.title = 'Hover any line to see its exact numbers, or tick this to show them all'; rh.appendChild(lbl);
        right.appendChild(rh);
        model.sections.forEach(function (sec) {
            var s = el('div', 'rc-sec'); s.appendChild(el('h5', null, sec.title + (sec.id !== 'zones' && sec.cards[0] ? '  ·  ' + sec.cards[0].chip : '')));
            if (sec.id === 'zones' && !sec.cards.length) s.appendChild(el('div', 'rc-empty', 'No paint zones were sent: this render used the imported spec / source paint only.'));
            sec.cards.forEach(function (c) { s.appendChild(buildCard(c, !!c.grouped)); });
            right.appendChild(s);
        });
        var f = model.facts || {}; right.appendChild(el('div', 'rc-foot', (f.layers ? f.layers + ' layers in the paint' + (f.hidden ? ' (' + f.hidden + ' hidden, not in the render)' : '') + '  ·  ' : '') + 'Made with SHOKKER PAINT BOOTH  ·  discord.gg/GwXxyhwtDu'));
        scr.appendChild(left); scr.appendChild(right);
        return scr;
    }

    // ------------------------------------------------------------------------------------------------ bar + menu
    function call(name) { var a = [].slice.call(arguments, 1); try { var f = root[name]; if (typeof f === 'function') return f.apply(root, a); } catch (e) { warn(name, e); } return null; }
    function ensureBar() {
        var panel = $('renderResultsPanel'); if (!panel) return null;
        var bar = $('spbRcBar');
        if (!bar) {
            var old = panel.querySelector(':scope > div'); if (old && old.id !== 'spbRcBar') old.classList.add('rc-oldbar');
            bar = el('div'); bar.id = 'spbRcBar'; bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', 'Render recipe actions');
            bar.appendChild(el('span', 'rc-title', 'Render recipe')); // [S6/UI 2026-10-12] on-screen copy sentence case; the exported share card keeps its branded caps
            var c1 = el('span', 'rc-chip'); c1.id = 'spbRcElapsed'; bar.appendChild(c1);
            var c2 = el('span', 'rc-chip'); c2.id = 'spbRcZones'; bar.appendChild(c2);
            bar.appendChild(el('span', 'rc-grow'));
            function btn(label, fn, cls, title, id) { var b = el('button', cls || '', label); b.type = 'button'; if (title) b.title = title; if (id) b.id = id; b.addEventListener('click', function (ev) { ev.stopPropagation(); closeMenu(); fn(b); }); return b; }
            bar.appendChild(btn('Save Card', function () { call('exportRecipeCardPNG'); }, 'rc-primary', 'Save this recipe card as a PNG picture you can post (Discord, Facebook, a build thread)', 'spbRcSave'));
            bar.appendChild(btn('Copy Card', function () { call('copyRecipeCardToClipboard'); }, '', 'Copy the card picture, then paste it straight into Discord', 'spbRcCopy'));
            bar.appendChild(btn('Keep Render', function (b) {
                var t = b.textContent; b.disabled = true; b.textContent = 'Keeping…';
                Promise.resolve(call('saveRenderToKeep')).then(function () { b.disabled = false; b.textContent = t; }, function () { b.disabled = false; b.textContent = t; });
            }, '', 'Copy these files into a Shokker Paint Booth folder so the next render cannot overwrite them', 'spbRcKeep'));
            var more = btn('More ▾', function () { var m = $('spbRcMenu'); if (m) m.classList.toggle('open'); }, '', 'More: share the recipe file, Trading Paints text, recent renders, PDF', 'spbRcMore');
            more.setAttribute('aria-haspopup', 'menu'); bar.appendChild(more);
            bar.appendChild(btn('✕ Close', function () { call('closeRenderResults'); }, 'rc-close', 'Close this and go back to the car (Esc)', 'spbRcClose'));
            var menu = el('div'); menu.id = 'spbRcMenu'; menu.setAttribute('role', 'menu');
            [['Share Recipe File', 'Saves a .shokkerrecipe file with a picture. Anyone can load it with Import Recipe.', 'shareRecipeFile'],
             ['Copy Trading Paints Text', 'Copies the description for your Trading Paints page, written from this render.', 'copyTPDescription'],
             ['Recent Renders', 'Open one of your last 10 renders and put its zones back.', 'openRecentRendersPanel'],
             ['Save Card as PDF', 'The same card as a one-page PDF.', 'exportRecipeCardPDF']].forEach(function (m) {
                var b = el('button', '', m[0]); b.type = 'button'; b.setAttribute('role', 'menuitem'); b.appendChild(el('small', null, m[1]));
                b.addEventListener('click', function (ev) { ev.stopPropagation(); closeMenu(); call(m[2]); }); menu.appendChild(b);
            });
            bar.appendChild(menu);
            panel.insertBefore(bar, panel.firstChild);
            doc.addEventListener('click', function (e) { var m = $('spbRcMenu'); if (m && m.classList.contains('open') && !e.target.closest('#spbRcMenu') && !e.target.closest('#spbRcMore')) closeMenu(); });
            doc.addEventListener('keydown', function (e) { var m = $('spbRcMenu'); if (e.key === 'Escape' && m && m.classList.contains('open')) { e.stopPropagation(); e.preventDefault(); closeMenu(); } }, true);
        }
        return bar;
    }
    function closeMenu() { var m = $('spbRcMenu'); if (m) m.classList.remove('open'); }

    // ------------------------------------------------------------------------------------------------ status line (one quiet line; the rest behind "Details")
    function tidyStatus() {
        var b = $('renderStatusBanner'); if (!b || b.getAttribute('data-rc') === String(LAST && LAST.at)) return;
        var kids = [].slice.call(b.children).filter(function (c) { return c.tagName === 'DIV'; });
        if (kids.length) {
            var d = el('details', 'rc-more'); var s = el('summary', null, 'Details ▾'); d.appendChild(s);
            kids.forEach(function (k) { d.appendChild(k); }); b.appendChild(d);
        }
        [].slice.call(b.querySelectorAll('code')).forEach(function (c) { if (!c.title) c.title = c.textContent; });
        b.setAttribute('data-rc', String(LAST && LAST.at));
    }

    // ------------------------------------------------------------------------------------------------ shareable card (canvas)
    var P = { bg0: '#0b0905', bg1: '#161006', panel: 'rgba(26,20,10,0.94)', edge: 'rgba(255,200,80,0.26)', ink: '#f6efdc', dim: '#c9b98d', faint: '#8d7f5b', gold: '#ffd142', cyan: '#63d8ff' };
    function rr(ctx, x, y, w, h, r) { r = Math.max(0, Math.min(r, w / 2, h / 2)); ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
    function wrapLines(ctx, text, maxW) {
        var words = String(text).split(/(\s+)/), lines = [], cur = '';
        words.forEach(function (w) { var t = cur + w; if (ctx.measureText(t).width > maxW && cur.trim()) { lines.push(cur.trim()); cur = w.trim() ? w : ''; } else cur = t; });
        if (cur.trim()) lines.push(cur.trim()); return lines.length ? lines : [''];
    }
    function contain(ctx, img, x, y, w, h) { var s = Math.min(w / img.width, h / img.height), dw = img.width * s, dh = img.height * s; ctx.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh); }
    function layoutCard(ctx, model, imgs, draw) {
        var W = 1480, PAD = 46, y = PAD, FONT = "'Segoe UI',Arial,sans-serif";
        if (imgs.logo) {
            var bw = Math.min(W - 2 * PAD, 940), bh = Math.round(bw * imgs.logo.height / imgs.logo.width), bx = (W - bw) / 2;
            if (draw) { rr(ctx, bx, y, bw, bh, 16); ctx.save(); ctx.clip(); ctx.drawImage(imgs.logo, bx, y, bw, bh); ctx.restore(); ctx.strokeStyle = P.edge; ctx.lineWidth = 2; rr(ctx, bx, y, bw, bh, 16); ctx.stroke(); }
            y += bh + 24;
        }
        var headH = 96;
        if (draw) {
            rr(ctx, PAD, y, W - 2 * PAD, headH, 16); var g = ctx.createLinearGradient(PAD, y, W - PAD, y); g.addColorStop(0, 'rgba(255,190,60,0.18)'); g.addColorStop(1, 'rgba(255,120,0,0.05)'); ctx.fillStyle = g; ctx.fill(); ctx.strokeStyle = P.edge; ctx.lineWidth = 1; ctx.stroke();
            ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = P.gold; ctx.font = '800 38px ' + FONT; ctx.fillText('RENDER RECIPE', PAD + 26, y + 52);
            ctx.fillStyle = P.dim; ctx.font = '600 15px ' + FONT; ctx.fillText('SHOKKER PAINT BOOTH   ·   ' + new Date(model.timestamp).toLocaleDateString() + (model.paintFile ? '   ·   ' + model.paintFile : ''), PAD + 26, y + 78);
            ctx.textAlign = 'right'; ctx.fillStyle = P.gold; ctx.font = '800 32px ' + FONT; ctx.fillText((model.elapsed != null ? model.elapsed : '?') + 's', W - PAD - 26, y + 50);
            ctx.fillStyle = P.dim; ctx.font = '600 15px ' + FONT; ctx.fillText(model.zones.length + ' zones   ·   2048²', W - PAD - 26, y + 76); ctx.textAlign = 'left';
        }
        y += headH + 24;
        var gap = 22, bwid = (W - 2 * PAD - gap) / 2, bhei = bwid, lab = 26;
        if (draw) {
            [['PAINT', imgs.paint, PAD], ['SPEC MAP', imgs.spec, PAD + bwid + gap]].forEach(function (s) {
                ctx.font = '800 16px ' + FONT; ctx.fillStyle = P.gold; ctx.textAlign = 'left'; ctx.fillText(s[0], s[2] + 2, y + 16);
                var iy = y + lab; rr(ctx, s[2], iy, bwid, bhei, 12); ctx.fillStyle = '#05070e'; ctx.fill(); ctx.save(); rr(ctx, s[2], iy, bwid, bhei, 12); ctx.clip();
                if (s[1]) contain(ctx, s[1], s[2], iy, bwid, bhei); else { ctx.fillStyle = P.faint; ctx.font = '16px ' + FONT; ctx.textAlign = 'center'; ctx.fillText('no image', s[2] + bwid / 2, iy + bhei / 2); ctx.textAlign = 'left'; }
                ctx.restore(); ctx.strokeStyle = P.edge; ctx.lineWidth = 1.5; rr(ctx, s[2], iy, bwid, bhei, 12); ctx.stroke();
            });
        }
        y += lab + bhei + 32;
        model.sections.forEach(function (sec) {
            if (draw) { ctx.fillStyle = P.gold; ctx.font = '800 20px ' + FONT; ctx.textAlign = 'left'; var stt = (sec.title + (sec.id !== 'zones' && sec.cards[0] ? '  \u00b7  ' + sec.cards[0].chip : '')).toUpperCase(); ctx.fillText(stt, PAD, y + 16); ctx.strokeStyle = 'rgba(255,200,80,0.22)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(PAD + ctx.measureText(stt).width + 16, y + 11); ctx.lineTo(W - PAD, y + 11); ctx.stroke(); }
            y += 34;
            if (!sec.cards.length) { if (draw) { ctx.fillStyle = P.dim; ctx.font = '16px ' + FONT; ctx.fillText('No paint zones were sent: imported spec / source paint only.', PAD, y + 16); } y += 36; }
            sec.cards.forEach(function (c) { y += cardPanel(ctx, c, PAD, y, W - 2 * PAD, draw) + 12; });
            y += 8;
        });
        if (draw) { ctx.strokeStyle = 'rgba(255,200,80,0.20)'; ctx.beginPath(); ctx.moveTo(PAD, y + 4); ctx.lineTo(W - PAD, y + 4); ctx.stroke(); ctx.fillStyle = P.dim; ctx.font = '600 14px ' + FONT; ctx.textAlign = 'center'; ctx.fillText('Made with SHOKKER PAINT BOOTH   ·   payhip.com/b/AhgpV   ·   discord.gg/GwXxyhwtDu', W / 2, y + 32); ctx.textAlign = 'left'; }
        y += 52 + PAD;
        return y;
    }
    function cardPanel(ctx, c, x, y, w, draw) {
        var Pd = 16, FONT = "'Segoe UI',Arial,sans-serif", labW = 130, valX = x + Pd + labW, valW = w - 2 * Pd - labW - 4, headH = c.kind === 'zone' ? 42 : 4, lineH = 22;
        ctx.font = '15.5px ' + FONT;
        var rows = [], lastPart = null;
        c.lines.forEach(function (ln) { if (c.grouped && ln.part !== lastPart) { lastPart = ln.part; rows.push({ part: ln.part, h: 26 }); } var ls = wrapLines(ctx, ln.text, valW); rows.push({ ln: ln, ls: ls, h: ls.length * lineH + 4 }); });
        var rowsH = rows.reduce(function (a, r) { return a + r.h; }, 0), H = headH + 8 + (rows.length ? rowsH : 24) + 8;
        if (draw) {
            rr(ctx, x, y, w, H, 12); ctx.fillStyle = P.panel; ctx.fill(); ctx.strokeStyle = P.edge; ctx.lineWidth = 1; ctx.stroke();
            rr(ctx, x, y, 6, H, 3); ctx.fillStyle = c.swatch || '#5b4a22'; ctx.fill();
            var hy = y + 10; if (c.kind === 'zone') { rr(ctx, x + Pd, hy, 24, 24, 5); ctx.fillStyle = c.swatch || '#334'; ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,0.3)'; ctx.stroke(); }
            ctx.fillStyle = P.ink; ctx.font = '800 19px ' + FONT; ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; if (c.kind === 'zone') ctx.fillText(c.name, x + Pd + 34, hy + 13);
            if (c.chip && c.kind === 'zone') { ctx.font = '700 14px ' + FONT; var cw = Math.ceil(ctx.measureText(c.chip).width) + 22; rr(ctx, x + w - Pd - cw, hy, cw, 26, 13); ctx.fillStyle = (c.kind === 'zone' && c.chip !== 'Keeps source paint') ? P.gold : 'rgba(255,200,80,0.16)'; ctx.fill(); ctx.fillStyle = (c.kind === 'zone' && c.chip !== 'Keeps source paint') ? '#171106' : P.ink; ctx.textAlign = 'center'; ctx.fillText(c.chip, x + w - Pd - cw / 2, hy + 14); ctx.textAlign = 'left'; }
            ctx.textBaseline = 'alphabetic';
            var ry = y + headH + 8;
            rows.forEach(function (r) {
                if (r.part) { ctx.font = '800 12px ' + FONT; ctx.fillStyle = P.cyan; ctx.fillText(r.part.toUpperCase(), x + Pd, ry + 18); }
                else { ctx.font = '700 12px ' + FONT; ctx.fillStyle = P.faint; ctx.fillText(r.ln.label.toUpperCase(), x + Pd, ry + 17); ctx.font = '15.5px ' + FONT; ctx.fillStyle = P.ink; r.ls.forEach(function (l, i) { ctx.fillText(l, valX, ry + 17 + i * lineH); }); }
                ry += r.h;
            });
            if (!rows.length) { ctx.font = '15px ' + FONT; ctx.fillStyle = P.dim; ctx.fillText('No changes recorded.', x + Pd, y + headH + 24); }
        }
        return H;
    }
    function drawCardCanvas(model, imgs) {
        var cv = doc.createElement('canvas'); cv.width = 1480; cv.height = 200;
        var H = Math.ceil(layoutCard(cv.getContext('2d'), model, imgs, false)); cv.height = H;
        var ctx = cv.getContext('2d');
        var g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, P.bg0); g.addColorStop(0.5, P.bg1); g.addColorStop(1, P.bg0); ctx.fillStyle = g; ctx.fillRect(0, 0, 1480, H);
        ctx.strokeStyle = 'rgba(255,209,66,0.55)'; ctx.lineWidth = 3; rr(ctx, 5, 5, 1470, H - 10, 20); ctx.stroke();
        layoutCard(ctx, model, imgs, true);
        return cv;
    }
    function loadImg(src, retry) {
        return new Promise(function (res) {
            if (!src) { res(null); return; }
            var im = new Image(), done = false, fin = function (v) { if (!done) { done = true; res(v); } };
            if (!/^data:/i.test(src)) { try { im.crossOrigin = 'anonymous'; } catch (e) {} }
            im.onload = function () { fin(im); };
            im.onerror = function () { if (retry !== false && !/^data:/i.test(src)) loadImg(src, false).then(fin); else fin(null); };
            setTimeout(function () { fin(null); }, 6000);
            try { im.src = src; } catch (e) { fin(null); }
        });
    }

    // ------------------------------------------------------------------------------------------------ Trading Paints text (from the same model)
    function tpText(model) {
        var L = ['═══ MADE WITH SHOKKER PAINT BOOTH ═══', ''];
        model.sections.forEach(function (sec) {
            sec.cards.forEach(function (c) {
                if (c.kind === 'zone') {
                    if (!c.lines.length && c.chip === 'Keeps source paint') return;
                    var colour = (c.lines.filter(function (l) { return l.label === 'Colour'; })[0] || {}).text;
                    L.push('▸ ' + c.name + ' — ' + c.chip + (colour ? ' · ' + colour : ''));
                    c.lines.forEach(function (l) { if (l.label === 'Colour' || l.label === 'Finish' || l.label === 'Where' || l.label === 'Other') return; L.push('    ' + l.label + ': ' + l.text); });
                } else {
                    L.push('▸ ' + c.name);
                    c.lines.forEach(function (l) { L.push('    ' + (l.part ? l.part + ' — ' : '') + l.label + ': ' + l.text); });
                }
            });
        });
        L.push(''); L.push('─'.repeat(23));
        var cnt = 0; try { if (typeof root._spbCatalogCount === 'function') cnt = root._spbCatalogCount(); else if (typeof _spbCatalogCount === 'function') cnt = _spbCatalogCount(); } catch (e) {}
        L.push((cnt ? cnt.toLocaleString() + ' finishes · ' : '') + 'SHOKKER PAINT BOOTH'); L.push('Get the app → payhip.com/b/AhgpV'); L.push('Discord → discord.gg/GwXxyhwtDu');
        return L.join('\n');
    }

    // ------------------------------------------------------------------------------------------------ orchestration
    function html() { return doc.documentElement; }
    function turnOn() { html().classList.add('spb-rc-on'); }
    function turnOff() { html().classList.remove('spb-rc-on'); }
    async function build(result) {
        ensureStyle(); var bar = ensureBar(); if (!bar) throw new Error('modal missing');
        var stage = $('recipeCardStage'); if (!stage) throw new Error('stage missing');
        if (root.SPB_RENDER_CARD_TEST_FAIL) throw new Error('test failure (SPB_RENDER_CARD_TEST_FAIL)');   // test hook only: proves the fall-back to the page's own card
        var cap = LAST; if (!cap || !cap.body) throw new Error('no render payload captured');
        try { if (root.SpbAIAtlas && root.SpbAIAtlas.load && !root.SpbAIAtlas.ready()) await Promise.race([root.SpbAIAtlas.load(), new Promise(function (r) { setTimeout(r, 2500); })]); } catch (e) {}
        var model = buildModel(result, cap); if (!model) throw new Error('no model');
        MODEL = model; root.__spbRenderCardModel = model;
        turnOn();
        $('spbRcElapsed').textContent = (model.elapsed != null ? model.elapsed + ' s' : '');
        $('spbRcZones').textContent = model.zones.length + (model.zones.length === 1 ? ' zone' : ' zones');
        stage.innerHTML = ''; stage.scrollTop = 0;
        var scr = buildScreen(model); stage.appendChild(scr);
        tidyStatus();
        // the shareable picture, drawn from the same model (Save Card / Copy Card / PDF read window._recipeCardCanvas)
        var imgs = await Promise.all([loadImg(imgSrc('renderPaintPreview')), loadImg(imgSrc('renderSpecPreview')), loadImg(logoUrl())]);
        try {
            var cv = drawCardCanvas(model, { paint: imgs[0], spec: imgs[1], logo: imgs[2] });
            root._recipeCardCanvas = cv; root._recipeCardModel = model;
        } catch (e) { warn('share picture failed', e); root._recipeCardCanvas = null; root._recipeCardModel = model; }
        return true;
    }
    var installed = false;
    function install() {
        if (installed || off()) return;
        var prev = root.renderRecipeCardUI;
        if (typeof prev !== 'function' || prev.__rc) return;
        // [SPB-RENDER-CARD 2026-10-10] when the page's own card cannot draw it falls back to the zone table (R-1); say so in one line (R-1 only wrote the
        // note on a timeout/throw, not when the page swallowed the error itself)
        function noteIfTable() {
            try {
                var st = $('recipeCardStage'); if (!st || st.querySelector('canvas, .spb-tf-note, .spb-rc-note, #spbRcScreen')) return;
                var t = $('renderRecipeZones'); if (!t || t.parentNode !== st) return;
                var n = doc.createElement('div'); n.className = 'spb-rc-note'; n.style.cssText = 'padding:12px 16px;font-size:12px;color:#9aa4b2';
                n.textContent = 'The recipe picture could not be drawn. Your render is saved; the zone table is below.';
                st.insertBefore(n, st.firstChild);
            } catch (e) {}
        }
        var w = async function (result) {
            if (off()) { turnOff(); var r0 = await prev.apply(this, arguments); noteIfTable(); return r0; }
            var self = this, args = arguments;
            try { return await build(result); }
            catch (e) { warn('new screen failed, using the page card:', e && e.message || e); turnOff(); try { var st = $('recipeCardStage'); if (st) st.innerHTML = ''; } catch (x) {} var r1 = await prev.apply(self, args); noteIfTable(); return r1; }
        };
        w.__rc = true; root.__spbRcPrev = prev; root.renderRecipeCardUI = w; installed = true;
        // the Trading Paints text now describes THIS render (it used to be built from the live zone UI)
        var prevTP = root.buildTPDescription;
        if (typeof prevTP === 'function' && !prevTP.__rc) {
            var wt = function () { try { if (!off() && MODEL && html().classList.contains('spb-rc-on')) return tpText(MODEL); } catch (e) { warn('tp text', e); } return prevTP.apply(this, arguments); };
            wt.__rc = true; root.__spbRcPrevTP = prevTP; root.buildTPDescription = wt;
        }
    }
    function init() { try { ensureStyle(); install(); } catch (e) { warn('install', e); } }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
    root.addEventListener && root.addEventListener('load', init);

    root.SpbRenderCard = { VER: VER, off: off, capture: capture, last: function () { return LAST; }, model: function () { return MODEL; }, audit: audit, buildModel: buildModel, words: function (id, k) { return wordsOf(atlasItem(id, k)); }, tpText: tpText, slim: slim, install: install, _internal: { readZone: readZone, readExtras: readExtras, drawCardCanvas: drawCardCanvas, layerSnap: layerSnap } };
})(typeof window !== 'undefined' ? window : null);
