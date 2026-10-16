/* ============================================================================
   SPB PRO ZONE KIT — the copilot's hands and eyes for Pro Mode zones   (SPB-AI 2026-09-30)
   Everything an assistant (or a script, or a test) needs to READ and CHANGE Pro's zones the way the UI does — without ever
   touching the DOM. Uses the app's own zone model + setters; silences undo/toast noise so a whole command is ONE undo step.

     SpbProZone.describe(i) / describeAll()      plain-language state of a zone (only non-default settings), incl. where it sits on the paint
     SpbProZone.paintColours(n)                   the paint's dominant colours with share + where (grid cells)
     SpbProZone.paintMapImage(size)               the paint as a JPEG data URL with a labelled A-H x 1-8 grid (for a vision model)
     SpbProZone.validate(spec)                    errors/warnings for an edit spec BEFORE anything is changed
     SpbProZone.edit(i, spec) / add(spec)         apply a spec (see SCHEMA below) to a zone / a new zone
     SpbProZone.batch(ops, label)                 run many edit/add ops as ONE undo step and one repaint
     SpbProZone.searchSpecPatterns(q) / searchPatterns(q) / SCHEMA

   GRID: the paint canvas is split into 8 columns A..H (left to right) and 8 rows 1..8 (top to bottom); "B3:D5" is a rectangle of cells.
   ES5 only (old Electron).
   ========================================================================== */
(function () {
    'use strict';
    function G(name) { try { return window[name]; } catch (e) { return undefined; } }
    // [SPB-PERF2 2026-10-10] read-only layer union: every caller below only READS the mask, so it skips the 4 MB copy getZoneSourceLayersUnionMask makes on each call (about 100 calls per helper-environment rebuild = 60 % of the 1.0-1.9 s idle main-thread freeze, profile_idle.py before -> after in _easy_claude_work/perf2/PROGRESS.md). Same maths (js/spb-perf2-client.js); kill switch window.SPB_PERF2_OFF = true.
    function unionRO(zl, W, H) { var P2 = window.__spbPerf2; if (P2 && P2.unionRO && window.SPB_PERF2_OFF !== true) { try { return P2.unionRO(zl, W, H); } catch (eP2) {} } return G('getZoneSourceLayersUnionMask')(zl, W, H); }
    function Zs() { try { return zones; } catch (e) { return []; } }
    function isHex(s) { return /^#[0-9a-f]{6}$/i.test(String(s || '')); }
    function clamp(v, lo, hi) { v = Number(v); if (!isFinite(v)) return lo; return Math.max(lo, Math.min(hi, v)); }
    function hexRgb(h) { return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)]; }
    function rgbHex(r) { return '#' + r.map(function (v) { return ('0' + Math.round(v).toString(16)).slice(-2); }).join(''); }
    function esc(s) { return String(s == null ? '' : s); }
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }

    // ------------------------------------------------------------------ SCHEMA (also the documentation the model reads)
    var SCHEMA = {
        name: 'string — rename the zone',
        muted: 'boolean — temporarily switch the zone off (or on)',
        intensity: 'number 0-100 — how strongly the FINISH acts (its spec / shine and its paint effect; 100 = full). It does NOT fade the zone colour: for that use base_strength',          /* MCPSCEN 2026-10-05: intensity 50 on a red gloss zone changed nothing visible; the old wording read as a colour fade */
        finish: 'string — a finish key from search_finishes: "base::<id>" (plain material) or "monolithic::<id>" (complete special look). Replaces the zone\'s base material / special.',
        color: 'string — "#rrggbb" (paint the zone this solid colour), "source" (keep the car\'s own paint colour, change only the spec/shine), or "finish" (use the finish\'s own colour)',
        gradient: 'object {stops:[{pos:0-100,color:"#rrggbb"},...2-10 stops], direction:"horizontal"|"vertical"|"diagonal_down"|"diagonal_up"|"radial"|"angular", fit:true|false} — colour the zone with a gradient (turns colour mode to gradient). A stop colour may be a colour name; stops without pos are spread evenly. fit (default: on for a zone limited to a part / box / element; linear directions) runs the gradient across the zone itself; off = across the whole sheet',
        hue: 'number -180..180 — rotate the base colour',
        saturation: 'number -100..100 — base colour saturation adjust',
        brightness: 'number -100..200 — base colour brightness adjust',
        base_strength: 'number 0-200 (%) — fade the finish over the original paint (0 = original paint, 100 = full finish)',
        spec_strength: 'number 0-200 (%) — overall strength of the spec (shine/metal) map',
        scale: 'number 0.05-5 — size of the base material texture (1 = normal)',
        rotation: 'number 0-359 — rotate the base material',
        pattern: 'object {id|"none", opacity:0-100, scale:0.05-5, rotation:0-359} — a paint PATTERN on top (ids from search_patterns); opacity 100 = the colours of the pattern itself cover the zone colour, 25-35 = the zone colour with the pattern texture (measured 2026-10-05: at 50+ the own (often darker) colours of the pattern take over, e.g. hot pink + camo 70 reads brown)',
        pattern_position: 'object {x:0-100, y:0-100 (absolute, 50 = centre)} and/or {dx:-100..100, dy:-100..100 (nudge from where it is now; + = right / down)} and/or {target:"base"} to move the zone Base picture instead — slides the zone PATTERN or picture inside its panel (same Position X / Y sliders as the UI, Ctrl+Z undoes it). Needs a pattern on the zone', // W13-NUDGE 2026-10-09 (kill window.SPB_W13N_OFF)
        spec_patterns: 'array (max 5) of {id, opacity:0-100, scale, rotation, channels:"M"|"R"|"C" letters (Metal/Rough/Clearcoat)} — SPEC pattern layers that change how the surface reflects (ids from search_spec_patterns). Replaces the existing spec pattern stack.',
        second_base: 'object {id|"none", color:"#rrggbb", strength:0-100} — a second material blended over the first (ids like finish keys)',
        spec_shift: 'object {metal:-127..127, rough:-127..127, clearcoat:-127..127} — push the zone\'s metallic / roughness / clearcoat channels up or down (added to the spec bytes: rough minus = sharper/glossier; clearcoat minus = glossier coat, stops at 16 = max gloss; clearcoat plus = duller coat)', // BUGFIX 2026-10-04: direction stated (engine adds b; 16 = max gloss)
        copy_look_from: 'zone index (0..), zone id or exact zone name — copy EVERY look setting of that zone onto this one exactly: finish, colour (solid / gradient / special), scale, rotation, base / spec strength, intensity, pattern, spec patterns, overlays, spec shift. The region (which pixels) is not copied. "the same colour and finish as the numbers" = copy_look_from the zone that paints the numbers',          // HELPER FIX PASS 8 2026-10-05 (owner live: the spray-can yellow "the same color and finish that's on the numbers": the copy lost the Saturday Chrome finish and its 0.15 scale)
        stroke_px: 'number 1-60 — the width in px (on a 2048 sheet) of a LINE zone (region.graphic outline / seam / stripes); the zone redraws its line at that width, nothing else changes. Thinner / thicker / "half that" edit this',          // HELPER V3 S5 2026-10-05 (additive)
        priority: 'for add_zone / move: "top" (default for a new zone; wins overlaps), "bottom", or a position number 0.. (0 = top). LOWER position wins where zones overlap, so a zone that must show on pixels other zones also select has to sit ABOVE them.',
        region: 'object — WHICH PIXELS the zone covers: {colors:["#rrggbb",...], tolerance:6-100, layers:["layer name or id",...], element:"numbers"|"sponsors"|"stripes" (the numbers / sponsors+logos / stripes the app FOUND on this paint from the picture: works on flat paints with no layers; call describe_paint first), exclude:["numbers","sponsors","stripes"] (the zone covers its selection EXCEPT these: "make the black matte but leave the numbers alone"), part:"left side" (or a list ["left side","right side"]: a NAMED PART of the car from get_car_map — the way to put anything on a specific place) with portion:"front third"|"rear half"|"lower third"|"upper half"... OR band:{axis:"height"|"length", from:0..1, to:0..1} (a stripe: height = measured from the ROOF-LINE (0) down to the ROCKER (1) of a side panel; length = from the FRONT (0) to the REAR (1)), cells:"B3:D5" or rect:{x0,y0,x1,y1 as 0-1 fractions} (ONLY for small details under ~12% of the sheet; a big box cuts across panels and is refused), clear_box:true, remaining:true (catch everything not claimed), everything:true, paintable:true (with everything: limits it to the car\'s paintable area; use it for a whole-car BASE colour)}'
    };

    // ------------------------------------------------------------------ paint access + grid
    function paintDims() { var c = document.getElementById('paintCanvas'); return c ? [c.width, c.height] : [2048, 2048]; }
    function paintPixels() { try { return (typeof paintImageData !== 'undefined' && paintImageData) ? paintImageData : null; } catch (e) { return null; } }
    // MCP named-color guard: this classifier intentionally follows the current visible composite, not BASE beneath an overlay. The engine still intersects its existing source-layer mask.
    function mcpFamilyMaskForPixels(pd, W, H, family, classify) {
        if (!pd || !pd.data || pd.data.length !== W * H * 4 || !W || !H) return { error: 'the current visible paint canvas is unavailable' };
        if (typeof classify !== 'function') return { error: 'the semantic color-family classifier is unavailable' };
        var allowed = { black: 1, white: 1, charcoal: 1, silver: 1, grey: 1, red: 1, pink: 1, brown: 1, tan: 1, orange: 1, yellow: 1, green: 1, teal: 1, blue: 1, purple: 1 };
        if (!allowed[family]) return { error: 'the requested semantic color family is unsupported' };
        var mask = new Uint8Array(W * H), d = pd.data, hits = 0, i, o, hex, got, key, familyCache = Object.create(null);
        for (i = 0; i < mask.length; i++) { o = i * 4; if (d[o + 3] < 1) continue; key = (d[o] << 16) | (d[o + 1] << 8) | d[o + 2]; got = familyCache[key]; if (got === undefined) { hex = '#' + ('0' + d[o].toString(16)).slice(-2) + ('0' + d[o + 1].toString(16)).slice(-2) + ('0' + d[o + 2].toString(16)).slice(-2); try { got = familyCache[key] = classify(hex); } catch (e) { return { error: 'visible paint color classification failed' }; } } if (got === family) { mask[i] = 255; hits++; } }
        if (!hits) return { error: 'no visible pixels belong to the requested ' + family + ' family; nothing was changed' };
        return { mask: mask, hits: hits };
    }
    function mcpFamilySourceTicket(pd, W, H) {
        var tx = window.SPBSourceLoadTransaction, c = null, generation, committedPath, committedFingerprint;
        try { c = document.getElementById('paintCanvas'); } catch (e) {}
        if (!tx || typeof tx.getGeneration !== 'function' || typeof tx.getCommittedPath !== 'function' || typeof tx.getCommittedFingerprint !== 'function' || !c || c.width !== W || c.height !== H || pd !== paintPixels() || !pd || !pd.data || pd.data.length !== W * H * 4) return null;
        try { generation = tx.getGeneration(); committedPath = tx.getCommittedPath(); committedFingerprint = tx.getCommittedFingerprint(); } catch (e2) { return null; }
        if (!isFinite(Number(generation)) || !String(committedPath || '').trim() || !String(committedFingerprint || '').trim()) return null;
        return { generation: generation, path: committedPath, fingerprint: committedFingerprint, revision: Number(window._spbLayerRev) || 0, pixels: pd, width: W, height: H };
    }
    function mcpFamilyTicketCurrent(t) {
        if (!t) return false; var tx = window.SPBSourceLoadTransaction, c = null; try { c = document.getElementById('paintCanvas'); } catch (e) {}
        try { return !!(tx && c && paintPixels() === t.pixels && c.width === t.width && c.height === t.height && tx.getGeneration() === t.generation && tx.getCommittedPath() === t.path && tx.getCommittedFingerprint() === t.fingerprint && (Number(window._spbLayerRev) || 0) === t.revision); } catch (e2) { return false; }
    }
    // MCPSCEN 2026-10-05 (ARCA, Wire layer visible: "make the yellow purple" then hide Wire for export -> a yellow wireframe grid stayed in the purple; hidden first = clean).
    // Template layers (Wire / Mask / Car Mandatory / guides) are switched off before export, so they do not count as covering the paint: a pixel under one takes
    // the verdict of the nearest uncovered pixels in 8 directions (within 16 px; at least 2 found, majority in the colour family).
    function fillTemplateHoles(mask, W, H) {
        var tm = null, R = 16;
        (typeof _psdLayers !== 'undefined' ? _psdLayers : []).forEach(function (l) {
            if (!l || l.visible === false || !/^\s*(wire|mask|car[ _]*mandatory|template|guides?)\b/i.test(String(l.name || ''))) return;
            var lu = null; try { lu = unionRO({ sourceLayers: [l.id], sourceLayer: l.id }, W, H); } catch (e) {}
            if (!lu || !lu.union || lu.union.length !== W * H) return; if (!tm) tm = new Uint8Array(W * H); var u = lu.union; for (var k = 0; k < u.length; k++) if (u[k] > 0) tm[k] = 1;
        });
        if (!tm) return 0; var add = [], x, y, k2, d, j, got, yes;
        for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
            k2 = y * W + x; if (!tm[k2] || mask[k2]) continue; got = 0; yes = 0;
            for (d = 1; d <= R && x - d >= 0; d++) { j = k2 - d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && x + d < W; d++) { j = k2 + d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && y - d >= 0; d++) { j = k2 - d * W; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && y + d < H; d++) { j = k2 + d * W; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && x - d >= 0 && y - d >= 0; d++) { j = k2 - d * W - d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && x + d < W && y - d >= 0; d++) { j = k2 - d * W + d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && x - d >= 0 && y + d < H; d++) { j = k2 + d * W - d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            for (d = 1; d <= R && x + d < W && y + d < H; d++) { j = k2 + d * W + d; if (!tm[j]) { got++; if (mask[j]) yes++; break; } }
            if (got >= 2 && yes * 2 >= got) add.push(k2);
        }
        for (j = 0; j < add.length; j++) mask[add[j]] = 1; return add.length;
    }
    // MCPSCEN 2026-10-05: zone names were cut at 40 characters mid-word ("Yellow shifted to purple, keeping the sh"); cut at the last comma (or word) instead
    // MCPSCEN 2026-10-05 (RAM: "Main colour (neon orange) shifted to red, keeping the shading" became "... shifted to": the comma sat at character 40): a comma up to
    // character 48 is the cut; otherwise the last space before 41.
    function zoneName(n) { n = String(n); if (n.length <= 40) return n; var c = n.slice(0, 49), k = c.lastIndexOf(', '); if (k < 12) { c = n.slice(0, 41); k = c.lastIndexOf(' '); } return (k >= 12 ? c.slice(0, k) : n.slice(0, 40)).replace(/[\s,;:(-]+$/, ''); }
    // the box a gradient runs across (a zone limited by a region); the caller keeps the sheet-wide gradient when the zone spans > 85% of the sheet along the gradient
    function gradientZoneBox(z, force) {
        if (!z || !z.useRegion || !z.regionMask) return null; var W = paintDims()[0], H = paintDims()[1], m = z.regionMask; if (m.length !== W * H) return null;
        var x0 = W, y0 = H, x1 = -1, y1 = -1, x, y; for (y = 0; y < H; y += 4) for (x = 0; x < W; x += 4) if (m[y * W + x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        if (x1 < 0) return null; x1 = Math.min(W, x1 + 4); y1 = Math.min(H, y1 + 4);
        return [x0, y0, x1, y1];
    }
    // M3 2026-10-07: a transient field on a caller-owned object that must never be serialised (JSON.stringify of a 2048x2048 Uint8Array = 4M keys)
    function hideProp(o, k, v) { try { Object.defineProperty(o, k, { value: v, enumerable: false, configurable: true, writable: true }); } catch (e) { o[k] = v; } }
    function prepareMcpFamilyRegion(r) {
        var W = paintDims()[0], H = paintDims()[1], pd = paintPixels(), ticket = mcpFamilySourceTicket(pd, W, H);
        if (!ticket) return { error: 'the committed source canvas identity is unavailable or stale; nothing was changed' };
        var E = window.SpbProEdit, result = mcpFamilyMaskForPixels(pd, W, H, r.mcpFamily, E && E.familyOf);
        if (result.error) return result;
        try { fillTemplateHoles(result.mask, W, H); } catch (eth) {}
        if (!mcpFamilyTicketCurrent(ticket)) return { error: 'the source document changed while the visible color mask was being prepared; nothing was changed' };
        return { mask: result.mask, ticket: ticket, hits: result.hits };
    }
    function mcpFamilyPreApplyError(z, r, W, H) {
        if (!r || !r.mcpFamily) return '';
        if (!r._mcpFamilyMask || r._mcpFamilyMask.length !== W * H) return 'the named-color mask is missing or has the wrong canvas size; nothing was changed';
        if (z && z.useRegion && z.regionMask && z.regionMask.length !== W * H) return 'the existing taught region mask has the wrong canvas size; nothing was changed';
        if (!mcpFamilyTicketCurrent(r._mcpFamilyTicket)) return 'the source document changed before the named-color edit could begin; nothing was changed';
        return '';
    }
    function intersectMcpFamilyRegion(z, r, applied) {
        if (!r || !r.mcpFamily) return '';
        if (!r._mcpFamilyMask || !r._mcpFamilyMask.length) return 'the named-color mask is missing; nothing was changed';
        if (z && z.useRegion && z.regionMask && z.regionMask.length !== r._mcpFamilyMask.length) return 'the existing taught region mask has the wrong canvas size; nothing was changed';
        var old = (z.regionMask && z.useRegion && z.regionMask.length === r._mcpFamilyMask.length) ? z.regionMask : null, out = new Uint8Array(r._mcpFamilyMask.length), i;
        for (i = 0; i < out.length; i++) out[i] = r._mcpFamilyMask[i] ? (old ? old[i] : 255) : 0;
        z.regionMask = out; z.useRegion = true; z._regionDesc = (z._regionDesc ? z._regionDesc + ', ' : '') + 'visible ' + r.mcpFamily + ' paint family';
        applied.push('restricted to visible ' + r.mcpFamily + ' pixels while keeping the existing region and layer restrictions');
        return '';
    }
    var COLS = 'ABCDEFGH';
    function cellName(cx, cy) { return COLS.charAt(cx) + (cy + 1); }
    function parseCells(s) {
        var m = /^\s*([A-Ha-h])\s*([1-8])\s*(?::|-|to)?\s*(?:([A-Ha-h])\s*([1-8]))?\s*$/.exec(String(s || ''));
        if (!m) return null;
        var c0 = COLS.indexOf(m[1].toUpperCase()), r0 = Number(m[2]) - 1, c1 = m[3] ? COLS.indexOf(m[3].toUpperCase()) : c0, r1 = m[4] ? Number(m[4]) - 1 : r0;
        return { x0: Math.min(c0, c1) / 8, y0: Math.min(r0, r1) / 8, x1: (Math.max(c0, c1) + 1) / 8, y1: (Math.max(r0, r1) + 1) / 8 };
    }
    function whereWords(bb) {
        if (!bb) return '';
        var cx = (bb[0] + bb[2]) / 2, cy = (bb[1] + bb[3]) / 2, w = bb[2] - bb[0], h = bb[3] - bb[1];
        if (w > 0.8 && h > 0.8) return 'across the whole paint';
        var hor = cx < 0.34 ? 'left' : (cx > 0.66 ? 'right' : 'middle'), ver = cy < 0.34 ? 'top' : (cy > 0.66 ? 'bottom' : 'middle');
        if (hor === 'middle' && ver === 'middle') return 'in the middle' + (w > 0.6 ? ' (wide)' : '');
        return ver + '-' + hor + (w > 0.6 ? ' (wide)' : '');
    }
    // sample every `step`-th pixel; test(r,g,b,a,index) -> bool. Returns {share, bbox, cells}
    function scan(test, step) {
        var pd = paintPixels(); if (!pd) return null;
        var W = pd.width, H = pd.height, d = pd.data, st = step || 16, hits = 0, n = 0, x0 = 1, y0 = 1, x1 = 0, y1 = 0, cells = {}, ix, iy;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) {
            var o = (iy * W + ix) * 4; n++;
            if (d[o + 3] < 8) continue;
            if (!test(d[o], d[o + 1], d[o + 2], d[o + 3], ix, iy, W, H)) continue;
            hits++; var fx = ix / W, fy = iy / H;
            if (fx < x0) x0 = fx; if (fy < y0) y0 = fy; if (fx > x1) x1 = fx; if (fy > y1) y1 = fy;
            var k = cellName(Math.min(7, Math.floor(fx * 8)), Math.min(7, Math.floor(fy * 8))); cells[k] = (cells[k] || 0) + 1;
        }
        var per = (n / 64), top = Object.keys(cells).filter(function (k) { return cells[k] > per * 0.06; }).sort(function (a, b) { return cells[b] - cells[a]; });
        return { share: n ? hits / n : 0, bbox: hits ? [Math.round(x0 * 100) / 100, Math.round(y0 * 100) / 100, Math.round(Math.min(1, x1 + st / W) * 100) / 100, Math.round(Math.min(1, y1 + st / H) * 100) / 100] : null, cells: top.slice(0, 10) };
    }
    function colourTest(targets) {                   // the ENGINE's rule (WP6 2026-10-03: was per-channel max, which under-reported the engine's selection 1.3x-3x): weighted distance sqrt(.30dR^2+.59dG^2+.11dB^2) < tolerance (shokker_engine_v2 _build_plain_rgb_color_mask_fast, hard_edge)
        return function (r, g, b) { for (var t = 0; t < targets.length; t++) { var c = targets[t].rgb, tol = targets[t].tol, dr = r - c[0], dg = g - c[1], db = b - c[2]; if (dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11 < tol * tol) return true; } return false; };
    }
    function zoneTargets(z) {
        var tol = z.pickerTolerance != null ? z.pickerTolerance : 40, out = [];
        if (z.colorMode === 'multi' && Array.isArray(z.colors)) z.colors.forEach(function (c) { if (c && c.color_rgb) out.push({ rgb: c.color_rgb, tol: c.tolerance != null ? c.tolerance : tol }); });
        else if (z.colorMode === 'picker') { var rgb = (z.color && z.color.color_rgb) || (isHex(z.pickerColor) ? hexRgb(z.pickerColor) : null); if (rgb) out.push({ rgb: rgb, tol: (z.color && z.color.tolerance != null) ? z.color.tolerance : tol }); }
        return out;
    }
    // Pro stores catch-all zones two ways: colorMode 'special' (via setSpecialColor) or colorMode 'none' with color 'remaining'/'everything' (older saves).
    function catchAll(z) { return (z.color === 'remaining' || z.color === 'everything') ? z.color : null; }
    // A pixel test for one zone's OWN selection (colour AND layer AND box). null = selects nothing yet. Memoised per describe pass (layer masks are costly).
    var _memoZ = null, _memoT = null;
    function ownTest(z, W, H) {
        if (_memoZ) { var mi = _memoZ.indexOf(z); if (mi >= 0) return _memoT[mi]; }
        var mask = null, layerUnion = null, ca = catchAll(z), out;
        try { if (z.regionMask && z.useRegion) mask = z.regionMask; } catch (e) {}
        var layerGone = false;
        try { var ids = G('zoneSourceLayerIds') ? G('zoneSourceLayerIds')(z) : []; if (ids.length && G('getZoneSourceLayersUnionMask')) { var lu = unionRO(z, W, H); layerUnion = lu && lu.union; if (!layerUnion) layerGone = true; } } catch (e2) {}
        var tg = zoneTargets(z), ct = tg.length ? colourTest(tg) : null;
        if (layerGone || (!ct && !mask && !ca)) out = null;      // engine rule: a layer restriction alone selects nothing
        else out = function (R, Gc, B, idx) {
            if (ct && !ct(R, Gc, B)) return false;
            if (mask && !(mask[idx] > 0)) return false;
            if (layerUnion && !(layerUnion[idx] > 0)) return false;
            return true;
        };
        if (_memoZ) { _memoZ.push(z); _memoT.push(out); }
        return out;
    }
    function withMemo(fn) { var own = !_memoZ; if (own) { _memoZ = []; _memoT = []; } try { return fn(); } finally { if (own) { _memoZ = null; _memoT = null; } } }
    // What a zone CLAIMS (its own selection; a catch-all "remaining" claims whatever nothing above it claims). Muted zones claim nothing.
    function claimTest(list, j, W, H) {
        var z = list[j]; if (!z || z.muted) return null;
        if (catchAll(z) === 'remaining') {
            var above = []; for (var k = 0; k < j; k++) { var t = claimTest(list, k, W, H); if (t) above.push(t); }
            var mine = ownTest(z, W, H);
            return function (R, Gc, B, idx) { if (mine && !mine(R, Gc, B, idx)) return false; for (var q = 0; q < above.length; q++) if (above[q](R, Gc, B, idx)) return false; return true; };
        }
        return ownTest(z, W, H);
    }
    // Where a zone really lands. share_pct = what it selects; visible_pct = what it actually WINS after zones above it (LOWER index = higher priority) take theirs.
    // MCPSCEN 2026-10-05: the paint pixels a zone really shows on (its own test, minus what zones above it claim), sampled every st px, for colour checks of zones
    // without a region mask (whole-car / layer zones). Returns {W, H, idx:[pixel index...]} or null.
    function visibleIdx(i, st) {
        try {
            var list = Zs(), z = list[i]; if (!z) return null; st = st || 16;
            var W = paintDims()[0], H = paintDims()[1], own = catchAll(z) === 'remaining' ? null : ownTest(z, W, H), pd = paintPixels(); if (!own || !pd) return null;
            var above = [], j, d = pd.data, out = [], ix, iy; for (j = 0; j < i; j++) { var t = claimTest(list, j, W, H); if (t) above.push(t); }
            for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) { var o = (iy * W + ix) * 4, idx = iy * W + ix; if (d[o + 3] < 8 || !own(d[o], d[o + 1], d[o + 2], idx)) continue; var hid = false; for (j = 0; j < above.length; j++) if (above[j](d[o], d[o + 1], d[o + 2], idx)) { hid = true; break; } if (!hid) out.push(idx); }
            return { W: W, H: H, idx: out };
        } catch (e) { return null; }
    }
    function footprint(i) {
        return withMemo(function () {
            var list = Zs(), z = list[i]; if (!z) return null;
            var W = paintDims()[0], H = paintDims()[1], own = catchAll(z) === 'remaining' ? claimTest([].concat(list.slice(0, i), [(function (c) { var q = {}; for (var k in z) q[k] = z[k]; q.muted = false; return q; })()]), i, W, H) : ownTest(z, W, H);
            if (!own) return { share_pct: 0, visible_pct: 0, bbox: null, cells: [], where: 'nothing selected yet' };
            var above = [], j, pd = paintPixels(); if (!pd) return null;
            for (j = 0; j < i; j++) { var t = claimTest(list, j, W, H); if (t) above.push({ j: j, t: t }); }
            var d = pd.data, st = 16, ix, iy, n = 0, hits = 0, vis = 0, blocked = {}, x0 = 1, y0 = 1, x1 = 0, y1 = 0, cells = {};
            for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) {
                var o = (iy * W + ix) * 4; n++;
                if (d[o + 3] < 8) continue;
                var idx = iy * W + ix;
                if (!own(d[o], d[o + 1], d[o + 2], idx)) continue;
                hits++;
                var by = -1; for (j = 0; j < above.length; j++) if (above[j].t(d[o], d[o + 1], d[o + 2], idx)) { by = above[j].j; break; }
                if (by >= 0) { blocked[by] = (blocked[by] || 0) + 1; continue; }
                vis++; var fx = ix / W, fy = iy / H;
                if (fx < x0) x0 = fx; if (fy < y0) y0 = fy; if (fx > x1) x1 = fx; if (fy > y1) y1 = fy;
                var k2 = cellName(Math.min(7, Math.floor(fx * 8)), Math.min(7, Math.floor(fy * 8))); cells[k2] = (cells[k2] || 0) + 1;
            }
            var per = n / 64, top = Object.keys(cells).filter(function (k) { return cells[k] > per * 0.06; }).sort(function (a, b) { return cells[b] - cells[a]; }).slice(0, 10);
            var bb = vis ? [Math.round(x0 * 100) / 100, Math.round(y0 * 100) / 100, Math.round(Math.min(1, x1 + st / W) * 100) / 100, Math.round(Math.min(1, y1 + st / H) * 100) / 100] : null;
            var out = { share_pct: Math.round(hits / n * 1000) / 10, visible_pct: Math.round(vis / n * 1000) / 10, bbox: bb, cells: top, where: whereWords(bb) };
            var bl = Object.keys(blocked).map(function (k) { return { zone: list[k].name, index: Number(k), pct_of_this_zone: Math.round(blocked[k] / Math.max(1, hits) * 100) }; }).filter(function (b) { return b.pct_of_this_zone >= 10; }).sort(function (a, b) { return b.pct_of_this_zone - a.pct_of_this_zone; });
            if (bl.length) out.blocked_by = bl.slice(0, 3);
            if (catchAll(z) === 'remaining') out.approximate = true;
            return out;
        });
    }
    function paintColours(n, mask) {       // mask (optional, full-canvas, non-zero = counts): the car's paintable area, so the template dead-space backdrop is not reported as a livery colour (2026-10-02)
        var pd = paintPixels(); if (!pd) return [];
        var W = pd.width, H = pd.height, d = pd.data, bins = {}, ix, iy, st = 16, total = 0;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) {
            var o = (iy * W + ix) * 4; if (d[o + 3] < 128) continue; if (mask && !mask[iy * W + ix]) continue; total++;
            var k = (d[o] >> 4) + ',' + (d[o + 1] >> 4) + ',' + (d[o + 2] >> 4), b = bins[k] || (bins[k] = { c: 0, r: 0, g: 0, b: 0 });
            b.c++; b.r += d[o]; b.g += d[o + 1]; b.b += d[o + 2];
        }
        var arr = Object.keys(bins).map(function (k) { var b = bins[k]; return { c: b.c, rgb: [Math.round(b.r / b.c), Math.round(b.g / b.c), Math.round(b.b / b.c)] }; }).sort(function (a, b) { return b.c - a.c; }), out = [];
        arr.forEach(function (e) {
            if (out.length >= (n || 10)) return;
            if (out.some(function (o) { var dr = o.rgb[0] - e.rgb[0], dg = o.rgb[1] - e.rgb[1], db = o.rgb[2] - e.rgb[2]; return dr * dr + dg * dg + db * db < 1800; })) return;
            out.push(e);
        });
        return out.map(function (e) {
            var f = scan(colourTest([{ rgb: e.rgb, tol: 26 }]), 16) || {};
            return { hex: rgbHex(e.rgb), share_pct: Math.round(e.c / Math.max(1, total) * 100), where: whereWords(f.bbox), cells: (f.cells || []).slice(0, 6) };
        });
    }
    // ------------------------------------------------------------------ WP6 2026-10-03 edge quality: adaptive per-colour tolerance for colour regions
    // The engine (shokker_engine_v2 _build_plain_rgb_color_mask_fast + hard_edge default) recolours a pixel FULLY when its weighted distance
    // d = sqrt(.30dR^2 + .59dG^2 + .11dB^2) to any listed colour is below THAT colour's tolerance, and not at all otherwise. A fixed tolerance
    // left a halo of the old colour on anti-aliased glyph / stripe edges and dropped the darker shades of shaded fills. edgeFit measures the paint:
    //  - per target: tolerance = clamp(p98 spread of the pixels nearest to it + 6, floor, half the distance to the nearest OTHER colour)
    //  - same-hue shades joined to a target by a continuous gradient (dense colour ramp) join the fill
    //  - the anti-alias ramp toward each neighbour the target really touches is covered by extra spheres whose radius is provably safe
    //    (triangle inequality: no pixel nearer to another paint colour than to the target can fall inside), kept only if their pixels sit on the target's edges.
    function wdist(a, b) { var dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2]; return Math.sqrt(dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11); }
    function hueOf(c) { var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0; if (!d) return 0; if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; return (h * 60 + 360) % 360; }
    function chromaOf(c) { return Math.max(c[0], c[1], c[2]) - Math.min(c[0], c[1], c[2]); }
    var _efMemo = { src: null, key: null, out: null };
    function edgeFit(hexes, opts) {
        opts = opts || {}; var pd = paintPixels(), family = typeof opts.family === 'string' ? opts.family : ''; hexes = (hexes || []).filter(isHex); if (!pd || !hexes.length) return null;
        function inFamily(rgb) { if (!family) return true; try { return !!(window.SpbProEdit && typeof window.SpbProEdit.familyOf === 'function' && window.SpbProEdit.familyOf(rgbHex(rgb)) === family); } catch (e) { return false; } }
        if (family) hexes = hexes.filter(function (h) { return inFamily(hexRgb(h)); }); if (!hexes.length) return null;
        var mk = hexes.map(function (h) { return h.toLowerCase(); }).join(',') + '|' + (opts.floor || 30) + '|' + family + (opts.siblings ? '|sib' : '');
        if (_efMemo.src === pd && _efMemo.key === mk) return JSON.parse(JSON.stringify(_efMemo.out));
        var W = pd.width, H = pd.height, d = pd.data, mask = null, floor = opts.floor || 30, i, j, k, ix, iy;
        try { mask = window.SpbProCar && window.SpbProCar.paintableMask ? window.SpbProCar.paintableMask() : null; } catch (e0) { mask = null; }
        if (mask && mask.length !== W * H) mask = null;
        // 1. samples (stride 2) + a 24-colour palette (same clustering as paintColours, finer)
        var st = 2, sx = [], sr = [], bins = {}, p;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) {
            var p = iy * W + ix, o = p * 4; if (d[o + 3] < 128) continue; if (mask && !mask[p]) continue;
            sx.push(p); sr.push(d[o], d[o + 1], d[o + 2]);
            if ((ix & 3) || (iy & 3)) continue;
            var bk = (d[o] >> 4) + ',' + (d[o + 1] >> 4) + ',' + (d[o + 2] >> 4), b = bins[bk] || (bins[bk] = { c: 0, r: 0, g: 0, b: 0 }); b.c++; b.r += d[o]; b.g += d[o + 1]; b.b += d[o + 2];
        }
        var N = sx.length; if (!N) return null;
        var pal = [];
        Object.keys(bins).map(function (q) { var b = bins[q]; return { c: b.c, rgb: [Math.round(b.r / b.c), Math.round(b.g / b.c), Math.round(b.b / b.c)] }; }).sort(function (a, b) { return b.c - a.c; }).forEach(function (e) {
            if (pal.length >= 24 || e.c < 3) return;
            if (pal.some(function (q) { var dr = q.rgb[0] - e.rgb[0], dg = q.rgb[1] - e.rgb[1], db = q.rgb[2] - e.rgb[2]; return dr * dr + dg * dg + db * db < 1800; })) return;
            pal.push(e);
        });
        var T = hexes.map(function (h) { return { rgb: hexRgb(h), hex: h, kind: 'target' }; });
        function segInfo(e, a, b) { var L = wdist(a, b); if (L < 1) return null; var best = 1e9, bf = 0, f; for (f = 0.04; f < 0.97; f += 0.02) { var dd = wdist(e, [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]); if (dd < best) { best = dd; bf = f; } } return { d: best, f: bf, L: L }; }
        var big = pal.filter(function (e) { return !family || inFamily(e.rgb); }).concat(T.map(function (t) { return { rgb: t.rgb, c: 1e9 }; }));
        function thin(e) {                      // share of this colour's pixels that have a clearly different colour within 3 px (an AA ramp is 1-3 px wide)
            var tot = 0, edge = 0, n0, stp = Math.max(1, Math.floor(N / 200000));
            for (n0 = 0; n0 < N && tot < 400; n0 += stp) {
                var e1 = sr[3 * n0] - e.rgb[0], e2 = sr[3 * n0 + 1] - e.rgb[1], e3 = sr[3 * n0 + 2] - e.rgb[2]; if (e1 * e1 * 0.30 + e2 * e2 * 0.59 + e3 * e3 * 0.11 >= 100) continue;
                tot++; var pp = sx[n0], x = pp % W, y = (pp - x) / W, hit = false, dd2;
                [[3, 0], [-3, 0], [0, 3], [0, -3]].forEach(function (v) { if (hit) return; var xx = x + v[0], yy = y + v[1]; if (xx < 0 || yy < 0 || xx >= W || yy >= H) return; var o2 = (yy * W + xx) * 4, f1 = d[o2] - e.rgb[0], f2 = d[o2 + 1] - e.rgb[1], f3 = d[o2 + 2] - e.rgb[2]; dd2 = f1 * f1 * 0.30 + f2 * f2 * 0.59 + f3 * f3 * 0.11; if (dd2 > 400) hit = true; });
                if (hit) edge++;
            }
            return tot >= 5 && edge >= 0.7 * tot;
        }
        function isRamp(e) { return thin(e) && big.some(function (a) { return a.c >= 4 * e.c && big.some(function (b) { if (b === a || b.c < 4 * e.c) return false; var si = segInfo(e.rgb, a.rgb, b.rgb); return si && si.f > 0.06 && si.f < 0.94 && si.d <= 0.08 * si.L + 5; }); }); }
        var O = pal.filter(function (e) { return T.every(function (t) { return wdist(t.rgb, e.rgb) >= 14; }) && (family && !inFamily(e.rgb) || !isRamp(e)); }).map(function (e) { return { rgb: e.rgb }; });
        function countNear(pts, r) { var out = pts.map(function () { return 0; }), r2 = r * r, n, q; for (n = 0; n < N; n++) { var R = sr[3 * n], G2 = sr[3 * n + 1], B = sr[3 * n + 2]; for (q = 0; q < pts.length; q++) { var dr = R - pts[q][0], dg = G2 - pts[q][1], db = B - pts[q][2]; if (dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11 < r2) out[q]++; } } return out; }
        function lerp(a, b, f) { return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]; }
        // 2. shades: a same-hue colour joined to a chromatic target by a DENSE ramp is part of the fill (gradient / shading), not a second livery colour
        var shades = [];
        T.slice().forEach(function (t) {
            if (chromaOf(t.rgb) < 40) return;
            O = O.filter(function (o) {
                if (family && !inFamily(o.rgb)) return true;
                if (chromaOf(o.rgb) < 30) return true;
                var dh = Math.abs(hueOf(o.rgb) - hueOf(t.rgb)); dh = Math.min(dh, 360 - dh); if (dh > 14) return true;
                var L = wdist(t.rgb, o.rgb), r = Math.max(8, L / 6), cn = countNear([t.rgb, lerp(t.rgb, o.rgb, 0.25), lerp(t.rgb, o.rgb, 0.5), lerp(t.rgb, o.rgb, 0.75), o.rgb], r);
                // MCPSCEN 2026-10-05 (RAM2 Monster High: "main colour (pink)" matte black left the big flat lighter-pink hood #fd7ed1, same hue, 21 away, no ramp to the camo pink):
                // on a FAMILY or named-colour request (opts.siblings, from the edit compiler) a flat same-hue sibling this close is that colour too, ramp or not.
                var famSib = (!!family || !!opts.siblings) && dh <= 12 && L <= 30;
                var lo = Math.min(cn[0], cn[4]); if (!famSib && (!lo || Math.min(cn[1], cn[2], cn[3]) < 0.08 * lo)) return true;
                var sh = { rgb: o.rgb, hex: rgbHex(o.rgb), kind: 'shade' }; T.push(sh); shades.push(sh.hex); return false;
            });
        });
        // 3. spread + cap per target colour
        var all = T.concat(O), near = new Int16Array(N), dn = new Float32Array(N), n, q;
        for (n = 0; n < N; n++) { var R0 = sr[3 * n], G0 = sr[3 * n + 1], B0 = sr[3 * n + 2], best = -1, bd = 1e12; for (q = 0; q < all.length; q++) { var a0 = all[q].rgb, e1 = R0 - a0[0], e2 = G0 - a0[1], e3 = B0 - a0[2], dd = e1 * e1 * 0.30 + e2 * e2 * 0.59 + e3 * e3 * 0.11; if (dd < bd) { bd = dd; best = q; } } near[n] = best; dn[n] = Math.sqrt(bd); }
        T.forEach(function (t, ti) {
            var ds = []; for (n = 0; n < N; n++) if (near[n] === ti) ds.push(dn[n]); ds.sort(function (a, b) { return a - b; });
            t.count = ds.length; t.p98 = ds.length ? ds[Math.min(ds.length - 1, Math.floor(ds.length * 0.98))] : 0;
        });
        O.forEach(function (o, oi) { var ds = []; for (n = 0; n < N; n++) if (near[n] === T.length + oi) ds.push(dn[n]); ds.sort(function (a, b) { return a - b; }); o.spread = ds.length ? ds[Math.min(ds.length - 1, Math.floor(ds.length * 0.95))] : 0; });
        T.forEach(function (t) {
            t.cap = O.length ? Math.min.apply(null, O.map(function (o) { var D = wdist(t.rgb, o.rgb); return Math.max(D / 2, D - o.spread - 4); })) : 100;
            t.tol = Math.round(Math.max(6, Math.min(t.cap - 1, Math.max(floor, t.p98 + 6), Math.round(floor * 1.25))));          // WP6 rev 10: <= 1.25x the floor (the ramp spheres do the AA; 49 on a red took orange logo pixels)
        });
        // MCPSCEN 2026-10-05 (RAM2 Monster High: "main colour (pink)" matte black left the big flat lighter-pink hood #fd7ed1, same hue, 21 away; it is merged into the
        // target's palette cluster so it is no 'other' colour, and a salmon 32 away the other way capped the target at 15): on a named-colour request (opts.siblings)
        // a big same-hue cluster just past the target's tolerance becomes a shade of its own, with a radius safe against every other colour.
        if (opts.siblings) T.filter(function (t) { return t.kind === 'target' && chromaOf(t.rgb) >= 40; }).forEach(function (t) {
            var ti = T.indexOf(t), ht = hueOf(t.rgb), c = 0, s0 = 0, s1 = 0, s2 = 0, rgb, dh2;
            for (n = 0; n < N; n++) { if (near[n] !== ti || dn[n] <= t.tol || dn[n] > 30) continue; rgb = [sr[3 * n], sr[3 * n + 1], sr[3 * n + 2]]; if (chromaOf(rgb) < 30) continue; dh2 = Math.abs(hueOf(rgb) - ht); if (Math.min(dh2, 360 - dh2) > 12) continue; c++; s0 += rgb[0]; s1 += rgb[1]; s2 += rgb[2]; }
            if (c < 0.004 * N) return;
            var m = [Math.round(s0 / c), Math.round(s1 / c), Math.round(s2 / c)], mc = O.length ? Math.min.apply(null, O.map(function (o) { var D = wdist(m, o.rgb); return Math.max(D / 2, D - o.spread - 4); })) : 100;
            if (mc < 9 || T.some(function (u) { return wdist(u.rgb, m) < 8; })) return;
            var sh = { rgb: m, hex: rgbHex(m), kind: 'shade', tol: Math.round(Math.max(6, Math.min(mc - 1, floor))) }; T.push(sh); shades.push(sh.hex);
        });
        // full-res membership of the target spheres (for the edge test of the ramp spheres)
        var tm = new Uint8Array(W * H);
        var tq = T.map(function (t) { return [t.rgb[0], t.rgb[1], t.rgb[2], t.tol * t.tol]; });
        for (p = 0; p < W * H; p++) { var oo = p * 4; if (d[oo + 3] < 128) continue; var R1 = d[oo], G1 = d[oo + 1], B1 = d[oo + 2]; for (q = 0; q < tq.length; q++) { var f1 = R1 - tq[q][0], f2 = G1 - tq[q][1], f3 = B1 - tq[q][2]; if (f1 * f1 * 0.30 + f2 * f2 * 0.59 + f3 * f3 * 0.11 < tq[q][3]) { tm[p] = 1; break; } } }
        function nearTarget(pix) { var x = pix % W, y = (pix - x) / W, a, bb; for (bb = -3; bb <= 3; bb++) for (a = -3; a <= 3; a++) { var xx = x + a, yy = y + bb; if (xx >= 0 && yy >= 0 && xx < W && yy < H && tm[yy * W + xx]) return true; } return false; }
        // 4. anti-alias ramps: target -> each neighbour it touches; spheres from the target's own tolerance out to the midpoint, radius safe against every other colour
        var edges = [], dbg = [];
        T.forEach(function (t) {
            if (t.kind !== 'target') return;
            O.map(function (o) { return { o: o, L: wdist(t.rgb, o.rgb) }; }).filter(function (nb) { return !family || inFamily(nb.o.rgb); }).sort(function (a, b) { return a.L - b.L; }).slice(0, 4).forEach(function (nb) {
                var L = nb.L, s = t.tol * 0.9, guard = 0, made = 0;
                function radAt(cp) { var c = lerp(t.rgb, nb.o.rgb, cp / L), rr = Math.min(L * 0.58 - cp, L - cp - (nb.o.spread || 0) - 4); O.forEach(function (o) { if (o !== nb.o) rr = Math.min(rr, wdist(c, o.rgb) - o.spread - 4); }); return { ctr: c, r: Math.floor(rr - 1) }; }
                while (s < L * 0.55 && guard++ < 8 && made < 4) {
                    var cpos = (s + L / 2) / 2, ra = radAt(cpos);
                    if (cpos - ra.r > s + 2) { var cp2 = s + Math.max(3, ra.r), rb = radAt(cp2); if (rb.r >= 3 && cp2 - rb.r <= s + 2) { cpos = cp2; ra = rb; } }
                    var ctr = ra.ctr, r = ra.r; if (opts.debug) dbg.push({ t: t.hex, toward: rgbHex(nb.o.rgb), L: Math.round(L), s: Math.round(s), c: Math.round(cpos), r: r });
                    if (r < 3) { s += Math.max(4, L * 0.05); continue; }          // too close to a third colour here: genuinely ambiguous pixels, skip past them
                    var rgbC = [Math.round(ctr[0]), Math.round(ctr[1]), Math.round(ctr[2])], hits = 0, onEdge = 0, shrink = 0;
                    for (;;) {
                        hits = 0; onEdge = 0; var r2c = r * r;
                        for (n = 0; n < W * H; n++) { if (tm[n] || (mask && !mask[n])) continue; var o4 = n * 4; if (d[o4 + 3] < 128) continue; var g1 = d[o4] - rgbC[0], g2 = d[o4 + 1] - rgbC[1], g3 = d[o4 + 2] - rgbC[2]; if (g1 * g1 * 0.30 + g2 * g2 * 0.59 + g3 * g3 * 0.11 < r2c) { hits++; if (nearTarget(n)) onEdge++; } }
                        if (hits - onEdge <= Math.floor(0.01 * hits) || shrink >= 4 || r < 4) break;          // WP6 rev 9: <= 1% off-edge (0.2% shrank every real-paint sphere to 5-7)
                        r = Math.floor(r * 0.7); shrink++;                 // pixels away from the target's edges (another colour's own AA rim): tighten
                    }
                    if (opts.debug) { dbg[dbg.length - 1].hits = hits; dbg[dbg.length - 1].onEdge = onEdge; dbg[dbg.length - 1].rFinal = r; }
                    if (hits >= 16 && hits - onEdge <= Math.floor(0.01 * hits) && r >= 3) { edges.push({ rgb: rgbC, hex: rgbHex(rgbC), tol: r, kind: 'edge', px: hits, toward: rgbHex(nb.o.rgb) }); made++; }
                    else if (hits >= 16 && onEdge < 0.6 * hits) break;   // that ramp is a real area colour, not an edge: stop walking toward it
                    s = cpos + r;
                }
            });
        });
        edges.sort(function (a, b) { return b.px - a.px; });
        var keep = T.concat(edges).slice(0, 12);
        var out = { colors: keep.map(function (e) { return e.hex; }), tols: keep.map(function (e) { return e.tol; }), tolerance: Math.max.apply(null, keep.map(function (e) { return e.tol; })),
            shades: shades, edges: edges.slice(0, 12 - T.length).map(function (e) { return { hex: e.hex, tol: e.tol, toward: e.toward, px: e.px }; }),
            targets: T.filter(function (t) { return t.kind === 'target'; }).map(function (t) { return { hex: t.hex, tol: t.tol, spread_p98: Math.round(t.p98), cap: Math.round(t.cap), px: t.count * st * st }; }) };
        if (opts.debug) { out.debug = { others: O.map(function (o) { return rgbHex(o.rgb) + ' s' + Math.round(o.spread || 0); }), palette: pal.map(function (e) { return rgbHex(e.rgb) + ' x' + e.c; }), steps: dbg }; return out; }
        _efMemo = { src: pd, key: mk, out: out };
        return JSON.parse(JSON.stringify(out));
    }
    function paintMapImage(size) {
        try {
            var src = document.getElementById('paintCanvas'); if (!src || src.width < 64) return null;
            var n = Math.max(384, Math.min(896, size || 640)), cv = document.createElement('canvas'); cv.width = cv.height = n;
            var cx = cv.getContext('2d'); cx.fillStyle = '#101018'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high'; cx.drawImage(src, 0, 0, n, n);
            cx.strokeStyle = 'rgba(255,255,255,0.55)'; cx.lineWidth = 1; cx.font = 'bold ' + Math.round(n / 34) + 'px sans-serif'; cx.textBaseline = 'top';
            var i, s = n / 8;
            for (i = 1; i < 8; i++) { cx.beginPath(); cx.moveTo(i * s, 0); cx.lineTo(i * s, n); cx.stroke(); cx.beginPath(); cx.moveTo(0, i * s); cx.lineTo(n, i * s); cx.stroke(); }
            var cx2, cy2;
            for (cy2 = 0; cy2 < 8; cy2++) for (cx2 = 0; cx2 < 8; cx2++) {
                var label = cellName(cx2, cy2), tx = cx2 * s + 3, ty = cy2 * s + 2;
                cx.fillStyle = 'rgba(0,0,0,0.65)'; cx.fillRect(tx - 2, ty - 1, Math.round(n / 17), Math.round(n / 30)); cx.fillStyle = '#ffe680'; cx.fillText(label, tx, ty);
            }
            return cv.toDataURL('image/jpeg', 0.78);
        } catch (e) { return null; }
    }

    // ------------------------------------------------------------------ describe
    function nameOfFinish(id, kind) {
        try { var list = kind === 'mono' ? MONOLITHICS : BASES; var f = list.filter(function (x) { return x.id === id; })[0]; return f ? f.name : id; } catch (e) { return id; }
    }
    function specName(id) { try { var f = SPEC_PATTERNS.filter(function (x) { return x.id === id; })[0]; return f ? f.name : id; } catch (e) { return id; } }
    function patName(id) { try { var f = PATTERNS.filter(function (x) { return x.id === id; })[0]; return f ? f.name : id; } catch (e) { return id; } }
    function layerName(id) { try { var l = _psdLayers.filter(function (q) { return q.id === id; })[0]; return l ? l.name : id; } catch (e) { return id; } }
    function regionText(z) {
        var b = [];
        var tg = zoneTargets(z);
        if (!catchAll(z) && (z.colorMode === 'picker' || z.colorMode === 'multi')) b.push('paint colour' + (tg.length > 1 ? 's ' : ' ') + tg.map(function (t) { return rgbHex(t.rgb) + '±' + t.tol; }).join(', '));
        else if (catchAll(z)) b.push(z.color === 'everything' ? 'everything' : 'everything not claimed by other zones (catch-all)');
        else if (z.colorMode === 'none' || !z.colorMode) b.push(z.regionMask ? 'a drawn area' : 'nothing selected yet');
        else b.push(String(z.colorMode));
        try { var ids = G('zoneSourceLayerIds') ? G('zoneSourceLayerIds')(z) : []; if (ids.length) b.push('only on layer' + (ids.length > 1 ? 's' : '') + ': ' + ids.map(layerName).join(', ')); } catch (e) {}
        if (z.regionMask && z.useRegion) b.push(z._regionDesc ? 'limited to the ' + z._regionDesc : 'limited to a drawn box/area');
        return b.join('; ');
    }
    function describe(i) {
        var z = Zs()[i]; if (!z) return null;
        var o = { index: i, id: z.id != null ? String(z.id) : undefined, name: z.name, muted: !!z.muted, priority: 'position ' + (i + 1) + ' of ' + Zs().length + ' (position 1 = top = wins overlaps)', covers: regionText(z) };
        try { o.where = footprint(i); } catch (e) {}
        if (z.base) o.base = z.base + ' (' + nameOfFinish(z.base, 'base') + ')';
        if (z.finish) o.special = z.finish + ' (' + nameOfFinish(z.finish, 'mono') + ')';
        if (!z.base && !z.finish) o.base = 'none';
        o.colour = z.baseColorMode === 'solid' ? ('solid ' + z.baseColor) : (z.baseColorMode === 'gradient' ? ('gradient ' + JSON.stringify(z.gradientStops) + ' ' + (z.gradientDirection || 'horizontal')) : (z.baseColorMode || 'finish'));
        if (z.intensity != null && String(z.intensity) !== '100') o.intensity = z.intensity;
        if (z.baseStrength != null && z.baseStrength !== 1) o.base_strength_pct = Math.round(z.baseStrength * 100);
        if (z.baseSpecStrength != null && z.baseSpecStrength !== 1) o.spec_strength_pct = Math.round(z.baseSpecStrength * 100);
        if (z.baseHueOffset) o.hue = z.baseHueOffset; if (z.baseSaturationAdjust) o.saturation = z.baseSaturationAdjust; if (z.baseBrightnessAdjust) o.brightness = z.baseBrightnessAdjust;
        if (z.baseScale && z.baseScale !== 1) o.scale = z.baseScale; if (z.baseRotation) o.rotation = z.baseRotation;
        if (z.pattern && z.pattern !== 'none') o.pattern = z.pattern + ' (' + patName(z.pattern) + ')' + (z.patternOpacity != null && z.patternOpacity !== 100 ? ' opacity ' + z.patternOpacity : '');
        if (Array.isArray(z.specPatternStack) && z.specPatternStack.length) o.spec_patterns = z.specPatternStack.map(function (l) { return l.pattern + ' (' + specName(l.pattern) + ') ' + (l.opacity != null ? 'opacity ' + l.opacity : ''); });
        if (z.secondBase) o.second_base = z.secondBase + ' (' + nameOfFinish(z.secondBase, 'base') + ')' + (z.secondBaseColor ? ' in ' + String(z.secondBaseColor).toLowerCase() : '') + ' strength ' + Math.round((z.secondBaseStrength == null ? 1 : z.secondBaseStrength) * 100) + '%';
        if (z.specShiftR || z.specShiftG || z.specShiftB) o.spec_shift = { metal: z.specShiftR || 0, rough: z.specShiftG || 0, clearcoat: z.specShiftB || 0 };
        return o;
    }
    function describeAll() { return withMemo(function () { return Zs().map(function (z, i) { return describe(i); }); }); }

    // ------------------------------------------------------------------ validate
    // CX3 2026-10-09 (Codex 'Shared layer intelligence' / layer-targets; owner rule: change ONLY the named part). The official ARCA template has four layers
    // named "Base Paint": the old first-name-match (then first substring match) could bind a paint change to a spec-map layer. Now: an exact layer id wins, then a
    // "Group / Layer" path (SpbLayerTargets), then a UNIQUE exact name, then a UNIQUE substring; a repeated name returns null (the caller asks) instead of guessing.
    // Kill switch window.SPB_CX3_OFF restores the first-match behaviour.
    function findLayer(x) {
        if (window.SPB_CX3_OFF) {
            try { var s0 = String(x).toLowerCase(); return _psdLayers.filter(function (l) { return l && l.img && (l.id === x || String(l.name).toLowerCase() === s0); })[0] || _psdLayers.filter(function (l) { return l && l.img && String(l.name).toLowerCase().indexOf(s0) !== -1; })[0] || null; } catch (e0) { return null; }
        }
        try {
            var rows = _psdLayers.filter(function (l) { return l && l.img; }), s = String(x).toLowerCase();
            var ids = rows.filter(function (l) { return l.id != null && (l.id === x || (typeof x === 'string' && String(l.id) === x)); });
            if (ids.length) return ids.length === 1 ? ids[0] : null;
            if (window.SpbLayerTargets && s.indexOf('/') !== -1) { var grouped = window.SpbLayerTargets.resolve(x, rows); return grouped.ok ? grouped.row : null; }
            var named = rows.filter(function (l) { return String(l.name).toLowerCase() === s; });
            if (named.length) return named.length === 1 ? named[0] : null;
            var fuzzy = rows.filter(function (l) { return String(l.name).toLowerCase().indexOf(s) !== -1; });
            return fuzzy.length === 1 ? fuzzy[0] : null;
        } catch (e) { return null; }
    }
    function layerNameHint(x) {          // CX3: say WHY a layer was not found when the name is shared by several layers
        try { if (window.SPB_CX3_OFF) return ''; var s = String(x).toLowerCase(), n = _psdLayers.filter(function (l) { return l && l.img && (String(l.name).toLowerCase() === s || String(l.name).toLowerCase().indexOf(s) !== -1); }).length; return n > 1 ? ' (' + n + ' layers match that name: use the full "Group / Layer" path or the layer id)' : ''; } catch (e) { return ''; }
    }
    function finishDoc(key) {
        var id = String(key || '').replace(/^[a-z]+::/, ''), kind = /^monolithic::/.test(key) ? 'mono' : (/^base::/.test(key) ? 'base' : null);
        try {
            if (kind === 'base' || !kind) { if (BASES.some(function (b) { return b.id === id; })) return { id: id, kind: 'base' }; }
            if (kind === 'mono' || !kind) { if (MONOLITHICS.some(function (m) { return m.id === id; })) return { id: id, kind: 'mono' }; }
        } catch (e) {}
        return null;
    }
    // MCPSCEN 2026-10-05: an unknown id in an MCP call gets the closest real ids in the error (an id that starts with the word first, then the shortest = most generic)
    function closestIds(list, q, prefix, n) { try { var fq = String(q || '').replace(/^[a-z]+::/, '').replace(/[_-]+/g, ' '), fid = norm(fq).replace(/ /g, '_'); return searchList((list || []).filter(function (x) { return !(x && x.retired); }), fq, 60).sort(function (x, y) { var rx = (x.id === fid ? 0 : (x.id.indexOf(fid) === 0 ? 1 : 2)) * 1000 + x.id.length, ry = (y.id === fid ? 0 : (y.id.indexOf(fid) === 0 ? 1 : 2)) * 1000 + y.id.length; return rx - ry; }).slice(0, n || 5).map(function (x) { return (prefix || '') + x.id; }); } catch (e) { return []; } }
    function validate(s, forNew) {
        var err = [], warn = [];
        if (!s || typeof s !== 'object') return { errors: ['spec must be an object'], warnings: [] };
        var allowed = Object.keys(SCHEMA), extra = Object.keys(s).filter(function (k) { return allowed.indexOf(k) === -1 && k !== 'zone'; });
        if (s.priority != null && !(s.priority === 'top' || s.priority === 'bottom' || (isFinite(Number(s.priority)) && Number(s.priority) >= 0))) err.push('priority must be "top", "bottom" or a position number');
        if (extra.length) err.push('unknown setting(s): ' + extra.join(', ') + '. Allowed: ' + allowed.join(', '));
        // MCPSCEN 2026-10-05 (MCP add_zone finish "carbon": a bare word got only "call search_finishes"): the closest real keys ride along in the error
        if (s.finish != null && !finishDoc(s.finish)) { var fsug = []; try { var fb = closestIds(BASES, s.finish, 'base::', 4), fm = closestIds(MONOLITHICS, s.finish, 'monolithic::', 3); fsug = fb.slice(0, 3).concat(fm.slice(0, 2)).concat(fb.slice(3)).slice(0, 5); } catch (efs) {} err.push('unknown finish "' + s.finish + '"' + (fsug.length ? ' — closest keys: ' + fsug.join(', ') + ' (or call search_finishes)' : ' — call search_finishes and copy a key')); }
        // MCPSCEN 2026-10-05 (DLM: color {gradient:{from,to}} got only "color must be #rrggbb": the error now names the gradient field)
        if (s.color != null && !(s.color === 'source' || s.color === 'finish' || isHex(s.color))) err.push('color must be "#rrggbb", "source" or "finish"' + ((s.color && typeof s.color === 'object') || /gradient|fade|→|->/i.test(String(s.color)) ? '. For a gradient leave color out and use the separate gradient field: {stops:[{pos:0,color:"#rrggbb"},{pos:100,color:"#rrggbb"}], direction:"vertical"}' : ''));
        if (s.gradient != null) {
            var g = s.gradient;
            if (!g || !Array.isArray(g.stops) || g.stops.length < 2 || g.stops.length > 10) err.push('gradient.stops needs 2-10 stops like {pos:0,color:"#0a3fd6"}');
            else if (!g.stops.every(function (t) { return t && isFinite(Number(t.pos)) && isHex(t.color); })) err.push('every gradient stop needs pos 0-100 and color "#rrggbb"');
            if (g && g.direction && ['horizontal', 'vertical', 'diagonal_down', 'diagonal_up', 'radial', 'angular'].indexOf(g.direction) === -1) err.push('gradient.direction must be horizontal|vertical|diagonal_down|diagonal_up|radial|angular');
        }
        if (s.pattern_position != null) { var pp0 = s.pattern_position; if (!pp0 || typeof pp0 !== 'object' || ['x', 'y', 'dx', 'dy'].every(function (k) { return pp0[k] == null; })) err.push('pattern_position needs x / y (0-100, 50 = centre) or dx / dy (a nudge)'); else if (['x', 'y', 'dx', 'dy'].some(function (k) { return pp0[k] != null && !isFinite(Number(pp0[k])); })) err.push('pattern_position x / y / dx / dy must be numbers'); }          // W13-NUDGE 2026-10-09
        if (s.pattern != null) { var p = s.pattern; if (typeof p === 'string') p = { id: p }; if (!p || !p.id) err.push('pattern needs an id'); else if (p.id !== 'none') { var okp = false; try { okp = PATTERNS.some(function (q) { return q.id === p.id; }); } catch (e) {} if (!okp) { var psug = closestIds(PATTERNS, p.id, '', 5); err.push('unknown pattern id "' + p.id + '"' + (psug.length ? ' — closest ids: ' + psug.join(', ') + ' (or call search_patterns)' : ' — call search_patterns')); } } }
        if (s.spec_patterns != null) {
            if (!Array.isArray(s.spec_patterns) || s.spec_patterns.length > 5) err.push('spec_patterns must be an array of at most 5 layers');
            else s.spec_patterns.forEach(function (l) { var okl = false; try { okl = l && SPEC_PATTERNS.some(function (q) { return q.id === l.id; }); } catch (e) {} if (!okl) { var ssug = closestIds(SPEC_PATTERNS, l && l.id, '', 5); err.push('unknown spec pattern id "' + (l && l.id) + '"' + (ssug.length ? ' — closest ids: ' + ssug.join(', ') + ' (or call search_spec_patterns)' : ' — call search_spec_patterns')); } });
        }
        if (s.second_base != null) { var sb = s.second_base; if (typeof sb === 'string') sb = { id: sb }; if (!sb || !sb.id) err.push('second_base needs an id'); else if (sb.id !== 'none' && !finishDoc(sb.id)) err.push('unknown second_base id "' + sb.id + '"'); }
        if (s.region != null) {
            var r = s.region = normRegion(s.region);
            if (r.colors && !(Array.isArray(r.colors) && r.colors.every(isHex))) err.push('region.colors must be a list of "#rrggbb"');
            if (r.cells && !parseCells(r.cells)) err.push('region.cells must look like "B3:D5" (columns A-H, rows 1-8)');
            if (r.island) {
                partNames(r.island).forEach(function (pn) {
                    if (!(window.SpbProCar && window.SpbProCar.findIsland(pn))) { var known = []; try { known = window.SpbProCar.parts(); } catch (e) {} err.push('unknown part "' + pn + '": ' + (known.length ? 'the parts I know on this car are: ' + known.join(', ') + '. Use one of those, or call point_at to have the buyer show "' + pn + '" (once per car)' : 'no parts are known on this car yet: call point_at so the buyer can show them (once per car)')); }
                });
            }
            if (r.island && (r.portion || r.band) && window.SpbProCar) {
                var lenBand = r.band && /len|long|along|front|rear/.test(String(r.band.axis || '')), nF = (r.portion && /front|rear|back|nose|tail/i.test(r.portion)) || lenBand;
                var nU = (r.portion && /upper|lower|rocker|skirt|sill|roof ?line|belt ?line|shoulder/i.test(r.portion)) || (r.band && !lenBand);
                partNames(r.island).forEach(function (pn) {
                    var isl = window.SpbProCar.findIsland(pn); if (!isl) return;
                    if (nF && !isl.front) err.push('the FRONT end of "' + pn + '" is not known, so "front / rear / along the length" would be a guess: call point_at with parts ["' + pn + '"] and need_front_for ["' + pn + '"]');
                    else if (nU && !isl.up && /side/.test(window.SpbProCar.canon(pn))) err.push('which edge of the "' + pn + '" is the ROOF-LINE is not known, so "upper / lower / down from the roof-line" would be a guess: call point_at with parts ["' + pn + '"] and need_up_for ["' + pn + '"]');
                });
            }
            // HELPER FIX PASS 7 2026-10-05: a kept car PART ("leave the hood alone") may be excluded too (excludedUnion cuts out its car-map mask)
            if (r.exclude != null && !(Array.isArray(r.exclude) && r.exclude.every(function (x) { var k = String(x).toLowerCase(); if (['numbers', 'sponsors', 'stripes'].indexOf(k) !== -1) return true; try { return !!(window.SpbProCar && window.SpbProCar.findIsland && window.SpbProCar.findIsland(k)); } catch (eX) { return false; } }))) err.push('region.exclude must be a list of "numbers", "sponsors", "stripes" or named car parts (what to leave alone)');
            if (r.element) { var ek = String(r.element).split(':')[0]; if (['numbers', 'sponsors', 'stripes'].indexOf(ek) === -1) err.push('region.element must be "numbers", "sponsors" or "stripes"'); else if (!(window.SpbProElements && window.SpbProElements.maskFor(r.element))) err.push('the app has not found the ' + ek + ' on this paint yet (call describe_paint first: it looks at the picture) or found none: select them by colour or layer instead'); }
            if (r.graphic) { var ge = window.SpbGraphics ? window.SpbGraphics.check(r.graphic.item || r.graphic) : 'the graphics library is not loaded'; if (ge) err.push('region.graphic: ' + ge); }
            if ((r.portion || r.band) && !r.island) err.push('region.portion / region.band only work together with region.part');
            if (r.band && !(typeof r.band === 'object' && isFinite(Number(r.band.from)) && (r.band.to == null || isFinite(Number(r.band.to))))) err.push('region.band must be {axis:"height"|"length", from:0..1, to:0..1}');
            var bigBox = r.rect || (r.cells ? parseCells(r.cells) : null);
            if (bigBox && !r.island) { var bArea = Math.abs(bigBox.x1 - bigBox.x0) * Math.abs(bigBox.y1 - bigBox.y0); if (bArea > 0.12) err.push('that box covers ' + Math.round(bArea * 100) + '% of the whole sheet: a box that big cuts across roof, hood, doors and bumpers and will NOT sit on the car the way you mean. Put it on a named part instead (region.part + portion/band from get_car_map), or select by paint colour / layer / remaining. Boxes are only for small details.'); }
            if (r.layers) (Array.isArray(r.layers) ? r.layers : [r.layers]).forEach(function (l) { if (!findLayer(l)) err.push('no PSD layer named "' + l + '"' + layerNameHint(l)); });
            if (forNew && !(r.colors && r.colors.length) && !(r.layers && r.layers.length) && !r.cells && !r.rect && !r.island && !r.graphic && !r.element && !r.remaining && !r.everything && !r.paintable) err.push('a new zone must cover something: give region.colors, region.layers, region.cells/rect, or region.remaining');
        } else if (forNew) err.push('a new zone needs a region (what it covers)');
        if (s.intensity != null && !(Number(s.intensity) >= 0 && Number(s.intensity) <= 100)) warn.push('intensity is 0-100');
        return { errors: err, warnings: warn };
    }

    // part / island are the same thing; accept a string, a list, or a comma list
    function normRegion(r) {
        if (!r || typeof r !== 'object') return r;
        if (r.part != null && r.island == null) r.island = r.part; delete r.part;
        if (typeof r.island === 'string' && /\s*(,|&|\band\b|\+)\s*/i.test(r.island) && !(window.SpbProCar && window.SpbProCar.findIsland(r.island))) r.island = r.island.split(/\s*(?:,|&|\band\b|\+)\s*/i).filter(Boolean);
        if (Array.isArray(r.island) && r.island.length === 1) r.island = r.island[0];
        return r;
    }
    function partNames(ref) { return Array.isArray(ref) ? ref : [ref]; }
    function regionDesc(r, mm) {
        var names = (mm.islands || [mm.island]).map(function (q) { return q.name || q.id; }), t = names.join(' + ');
        if (r.band) { var f = Math.round((Number(r.band.from) || 0) * 100), e = Math.round((r.band.to == null ? 1 : Number(r.band.to)) * 100); t += ', ' + f + '-' + e + '% of the way ' + (/len|long|along|front|rear/.test(String(r.band.axis || '')) ? 'from the front to the rear' : 'down from the roof-line'); }
        else if (r.portion) t += ' (' + r.portion + ')';
        return t;
    }
    // ------------------------------------------------------------------ edit
    function quiet(fn) {
        var op = window.pushZoneUndo, ot = window.showToast;
        try { window.pushZoneUndo = function () {}; window.showToast = function () {}; return fn(); } finally { window.pushZoneUndo = op; window.showToast = ot; }
    }
    // pixels that must NOT change: the numbers / sponsors / stripes as layers when the paint has them, else as found from the picture (js/spb-pro-elements.js)
    var EX_ROLE = { numbers: /^numbers$/i, sponsors: /logo|sponsor|decal/i, stripes: /tape|stripe/i };
    function regionMaskHash(mask) {
        if (!mask || typeof mask.length !== 'number') return '';
        var h = 2166136261, i; for (i = 0; i < mask.length; i++) h = Math.imul(h ^ (Number(mask[i]) & 255), 16777619);
        return mask.length + ':' + (h >>> 0).toString(36);
    }
    function rememberPartRegion(z, r, partMask) {
        if (!r || !r.island) { delete z._aiPartProv; return; }
        var layout = '', element = '';
        try { layout = window.SpbProCar && window.SpbProCar.layoutSig ? String(window.SpbProCar.layoutSig() || '') : ''; } catch (e) {}
        try { element = window.SpbProElements && window.SpbProElements.sig ? String(window.SpbProElements.sig() || '') : ''; } catch (e2) {}
        z._aiPartProv = { r: JSON.stringify(r), z: regionMaskHash(z.regionMask), p: regionMaskHash(partMask), l: layout, e: element };
    }
    function excludedUnion(list, W, H) {
        var out = null, i;
        (Array.isArray(list) ? list : [list]).forEach(function (kind) {
            kind = String(kind || '').toLowerCase();
            if (!EX_ROLE[kind]) {          // HELPER FIX PASS 7 2026-10-05: a kept PART ("the doors stay as they are") is left out by its car-map mask, no extra pick needed
                var pm0 = null; try { pm0 = window.SpbProCar && window.SpbProCar.maskFor ? window.SpbProCar.maskFor(kind) : null; } catch (eP) { pm0 = null; }
                if (!pm0 || !pm0.mask) return; if (!out) out = new Uint8Array(W * H); for (i = 0; i < pm0.mask.length; i++) if (pm0.mask[i] > 0) out[i] = 255; return;
            }
            var m = null, rl = []; try { rl = (window.SpbProCar && window.SpbProCar.roles) ? window.SpbProCar.roles() : []; } catch (e) {}
            var ids = rl.filter(function (x) { return x.visible !== false && EX_ROLE[kind].test(String(x.role || '')); }).map(function (x) { return x.id; });
            if (ids.length) { try { var lu = unionRO({ sourceLayers: ids, sourceLayer: ids[0] }, W, H); m = lu && lu.union; } catch (e2) {} }
            if (!m && window.SpbProElements) { var em = window.SpbProElements.maskFor(kind); m = em && em.mask; }
            if (!m) return;
            if (!out) out = new Uint8Array(W * H);
            for (i = 0; i < m.length; i++) if (m[i] > 0) out[i] = 255;
        });
        return out;
    }
    // W2-ACCENT 2026-10-09 (orchestrator W2 lane; Haiku harm theme #1: a part / side repaint covering the livery's ACCENT ART -- painted shapes and stripe blocks that are part of the
    // design, not decal layers). accentMask(): within one part, cut the paint into regions by CRISP colour edges; the biggest region is the base; a smaller region is an ACCENT when it is
    // a flat colour (not a gradient), clearly different from what surrounds it, and big enough not to be grain. Edits that name a part (not "everything / including the stripes") leave
    // these pixels alone. Kill switch: window.SPB_ACCENT_OFF = true. DEFAULT ON since W5-ACCENT2 2026-10-09 (full 30 x 3 cars gate passed); window.SPB_ACCENT_OFF = true is the kill switch. Probe (arca V5 / SSL / NG City): 17-57% of a side is accent art; flat colour bases are untouched.
    var ACC_G = 512, ACC_WALL = 10, ACC_DE = 25, ACC_FLAT = 14, ACC_MINFRAC = 0.0025, ACC_MAXFRAC = 0.12, ACC_CAP = 0.3;          // w2a4: a region over 12% of the part is a BASE area (NG City: the yellow half of the side was protected = half the side unpainted), and accents together never exceed 30% of it
    var _accLin = null;
    function accLab(rgb, n, out) {
        if (!_accLin) { _accLin = new Float32Array(256); for (var i = 0; i < 256; i++) { var c = i / 255; _accLin[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); } }
        var f = function (t) { return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; };
        for (var p = 0; p < n; p++) {
            var r = _accLin[rgb[p * 4]], g = _accLin[rgb[p * 4 + 1]], b = _accLin[rgb[p * 4 + 2]];
            var x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, y = 0.2126 * r + 0.7152 * g + 0.0722 * b, z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
            var fy = f(y); out[p * 3] = 116 * fy - 16; out[p * 3 + 1] = 500 * (f(x) - fy); out[p * 3 + 2] = 200 * (fy - f(z));
        }
    }
    // partMask: Uint8Array over the paint canvas (W x H, side = sqrt(length)). Returns { mask: Uint8Array(W*H) 255 on accents, share: accent cells / part cells (0..1) } or null.
    function accentMask(partMask, W, H) {
        if ((window.SPB_ACCENT_OFF === true) || !partMask) return null;
        var src = null; try { src = document.getElementById('paintCanvas'); } catch (e) { src = null; }
        if (!src || src.width < 64) return null;
        var Gs = ACC_G, cv = document.createElement('canvas'); cv.width = cv.height = Gs; var cx = cv.getContext('2d', { willReadFrequently: true });
        cx.imageSmoothingEnabled = true; cx.imageSmoothingQuality = 'high'; cx.drawImage(src, 0, 0, Gs, Gs);
        var rgb; try { rgb = cx.getImageData(0, 0, Gs, Gs).data; } catch (e2) { return null; }
        var side = Math.round(Math.sqrt(partMask.length)), NN = Gs * Gs, pm = new Uint8Array(NN), N = 0, x, y, i;
        for (y = 0; y < Gs; y++) { var sy = Math.min(side - 1, Math.floor((y + 0.5) * side / Gs)); for (x = 0; x < Gs; x++) { if (partMask[sy * side + Math.min(side - 1, Math.floor((x + 0.5) * side / Gs))]) { pm[y * Gs + x] = 1; N++; } } }
        if (N < 400) return null;
        var lab = new Float32Array(NN * 3); accLab(rgb, NN, lab);
        var wall = new Uint8Array(NN), de = function (a, b) { var d0 = lab[a * 3] - lab[b * 3], d1 = lab[a * 3 + 1] - lab[b * 3 + 1], d2 = lab[a * 3 + 2] - lab[b * 3 + 2]; return Math.sqrt(d0 * d0 + d1 * d1 + d2 * d2); };
        for (y = 0; y < Gs; y++) for (x = 0; x < Gs; x++) { i = y * Gs + x; if (!pm[i]) continue; if (x + 1 < Gs && de(i, i + 1) >= ACC_WALL) { wall[i] = 1; wall[i + 1] = 1; } if (y + 1 < Gs && de(i, i + Gs) >= ACC_WALL) { wall[i] = 1; wall[i + Gs] = 1; } }
        var lbl = new Int32Array(NN), n = 0, stack = new Int32Array(NN), area = [0], sL = [0], sa = [0], sb = [0], qL = [0], qa = [0], qb = [0];
        for (i = 0; i < NN; i++) {
            if (!pm[i] || wall[i] || lbl[i]) continue;
            n++; var sp = 0, ar = 0, a0 = 0, a1 = 0, a2 = 0, b0 = 0, b1 = 0, b2 = 0; stack[sp++] = i; lbl[i] = n;
            while (sp) {
                var c = stack[--sp], L = lab[c * 3], A = lab[c * 3 + 1], B = lab[c * 3 + 2]; ar++; a0 += L; a1 += A; a2 += B; b0 += L * L; b1 += A * A; b2 += B * B;
                var cxp = c % Gs, nb;
                if (cxp > 0 && (nb = c - 1, pm[nb] && !wall[nb] && !lbl[nb])) { lbl[nb] = n; stack[sp++] = nb; }
                if (cxp < Gs - 1 && (nb = c + 1, pm[nb] && !wall[nb] && !lbl[nb])) { lbl[nb] = n; stack[sp++] = nb; }
                if (c >= Gs && (nb = c - Gs, pm[nb] && !wall[nb] && !lbl[nb])) { lbl[nb] = n; stack[sp++] = nb; }
                if (c < NN - Gs && (nb = c + Gs, pm[nb] && !wall[nb] && !lbl[nb])) { lbl[nb] = n; stack[sp++] = nb; }
            }
            area.push(ar); sL.push(a0); sa.push(a1); sb.push(a2); qL.push(b0); qa.push(b1); qb.push(b2);
        }
        if (n < 2) return { mask: new Uint8Array(W * H), share: 0 };
        var base = 1; for (i = 2; i <= n; i++) if (area[i] > area[base]) base = i;
        // colour of what surrounds each candidate region: sample 3 cells out (the other side of the edge) in the four directions
        var rs = new Float64Array((n + 1) * 3), rc = new Int32Array(n + 1), d = 3;
        var cand = new Uint8Array(n + 1), minA = Math.max(10, ACC_MINFRAC * N);
        for (i = 1; i <= n; i++) if (i !== base && area[i] >= minA && area[i] <= ACC_MAXFRAC * N) { var m0 = sL[i] / area[i], m1 = sa[i] / area[i], m2 = sb[i] / area[i], v = Math.max(0, qL[i] / area[i] - m0 * m0) + Math.max(0, qa[i] / area[i] - m1 * m1) + Math.max(0, qb[i] / area[i] - m2 * m2); if (Math.sqrt(v) <= ACC_FLAT) cand[i] = 1; }
        var offs = [-d, d, -d * Gs, d * Gs];
        for (y = d; y < Gs - d; y++) for (x = d; x < Gs - d; x++) {
            i = y * Gs + x; var k = lbl[i]; if (!k || !cand[k]) continue;
            for (var o = 0; o < 4; o++) { var q = i + offs[o]; if (pm[q] && lbl[q] !== k) { rs[k * 3] += lab[q * 3]; rs[k * 3 + 1] += lab[q * 3 + 1]; rs[k * 3 + 2] += lab[q * 3 + 2]; rc[k]++; } }
        }
        var acc = new Uint8Array(NN), accN = 0;
        for (i = 1; i <= n; i++) {
            if (!cand[i] || rc[i] < 4) continue;
            var e0 = sL[i] / area[i] - rs[i * 3] / rc[i], e1 = sa[i] / area[i] - rs[i * 3 + 1] / rc[i], e2 = sb[i] / area[i] - rs[i * 3 + 2] / rc[i];
            if (Math.sqrt(e0 * e0 + e1 * e1 + e2 * e2) >= ACC_DE) cand[i] = 2;
        }
        var accIds = []; for (i = 1; i <= n; i++) if (cand[i] === 2) accIds.push(i);
        accIds.sort(function (a, b) { return area[b] - area[a]; }); var accTot = 0; accIds.forEach(function (id) { accTot += area[id]; });
        while (accIds.length && accTot > ACC_CAP * N) { var big = accIds.shift(); accTot -= area[big]; cand[big] = 1; }          // too much "accent" = the part is mostly art: protect only the smaller shapes
        for (i = 0; i < NN; i++) if (lbl[i] && cand[lbl[i]] === 2) acc[i] = 1;
        // W5-ACCENT2 2026-10-09 (B-0045 on the owner car: the thin pink heartbeat line INSIDE the white chevrons was too small to count as an accent and turned black): close the accent mask (dilate 4, erode 4 cells) so
        // lines / holes narrower than ~8 cells inside accent art are protected with it. Kill switch: window.SPB_ACCENT_NOCLOSE = true.
        if (!window.SPB_ACCENT_NOCLOSE) {
            var boxPass = function (src, r, dil) { var tmp = new Uint8Array(NN), dst = new Uint8Array(NN), xx, yy, kk, v; for (yy = 0; yy < Gs; yy++) for (xx = 0; xx < Gs; xx++) { v = dil ? 0 : 1; for (kk = -r; kk <= r; kk++) { var x2 = xx + kk; var b = (x2 < 0 || x2 >= Gs) ? (dil ? 0 : 1) : src[yy * Gs + x2]; if (dil ? b : !b) { v = dil ? 1 : 0; break; } } tmp[yy * Gs + xx] = v; }
                for (yy = 0; yy < Gs; yy++) for (xx = 0; xx < Gs; xx++) { v = dil ? 0 : 1; for (kk = -r; kk <= r; kk++) { var y2 = yy + kk; var b2 = (y2 < 0 || y2 >= Gs) ? (dil ? 0 : 1) : tmp[y2 * Gs + xx]; if (dil ? b2 : !b2) { v = dil ? 1 : 0; break; } } dst[yy * Gs + xx] = v; } return dst; };
            var clo = boxPass(boxPass(acc, 4, true), 4, false);
            for (i = 0; i < NN; i++) if (clo[i] && pm[i]) acc[i] = 1;
        }
        // grow 2 cells (the anti-aliased rim + the wall cells between the regions), inside the part
        var g1 = acc;
        for (var it = 0; it < 2; it++) { var g2 = new Uint8Array(g1); for (y = 1; y < Gs - 1; y++) for (x = 1; x < Gs - 1; x++) { i = y * Gs + x; if (!g1[i] && pm[i] && (g1[i - 1] || g1[i + 1] || g1[i - Gs] || g1[i + Gs])) g2[i] = 1; } g1 = g2; }
        for (i = 0; i < NN; i++) if (g1[i]) accN++;
        var out = new Uint8Array(W * H);
        for (y = 0; y < H; y++) { var gy = Math.min(Gs - 1, Math.floor(y * Gs / H)); for (x = 0; x < W; x++) if (g1[gy * Gs + Math.min(Gs - 1, Math.floor(x * Gs / W))]) out[y * W + x] = 255; }
        return { mask: out, share: accN / N };
    }
    function accentShareFor(part, portion) {          // for the edit brain: how much of this named part is accent art (0..1), or 0
        try {
            if ((window.SPB_ACCENT_OFF === true) || !window.SpbProCar || !window.SpbProCar.maskFor) return 0;
            var mm = window.SpbProCar.maskFor(part, portion); if (!mm || !mm.mask) return 0;
            var ac = accentMask(mm.mask, paintDims()[0], paintDims()[1]);
            return ac ? ac.share : 0;
        } catch (e) { return 0; }
    }
    // W2-ACCENT 2026-10-09: ANY helper path that paints a named part (offline edit, design composer, flames, textures) keeps the accent art unless the buyer's own words say to cover it.
    // The buyer's latest message is read from the AI panel log; no message (a hand edit, an online tool call without the text) = no default (region.keepAccents:true still works explicitly).
    var ACCENT_ALL_RE = /\b(everything|every ?thing|all of it|all over|including|even the|whole (?:car|truck|body|thing|livery|design|paint)|entire (?:car|truck|body|livery|design|paint)|completely|solid|wipe|cover (?:all|it all)|(?:and|with|plus) (?:all )?the (?:stripes?|accents?|graphics?|art)|stripes (?:too|and all)|accents? too|paint over)\b/, ACCENT_NAMED_RE = /\b(stripes?|pinstripes?|accents?|graphics?|trim|shapes?|swoosh(?:es)?|blocks?|artwork|lines?|bands?|tape|decals?)\b/;
    // W5-ACCENT2 2026-10-09 (MCP B-0045 "flames down the side": spb_add_zone repainted the white chevron stripes black): an MCP call has no chat-log message, so the default never ran. The call's own buyer_said / spb_do text is now
    // the buyer's words for the length of that call (wrapper on spbProAI.mcpCall, installed lazily; no edit to spb-pro-ai.js). Kill switch: window.SPB_ACCENT_MCP_OFF = true.
    var _mcpSaidText = '';
    function installMcpSaid() {
        var tries = 0, t = setInterval(function () {
            tries++; var A = window.spbProAI;
            if (A && typeof A.mcpCall === 'function') {
                clearInterval(t); if (A.mcpCall.__accSaid) return;
                var orig = A.mcpCall;
                var wrapped = function (tool, args) {
                    var said = ''; try { if (!window.SPB_ACCENT_MCP_OFF && args) said = String(args.buyer_said || args.text || ''); } catch (e) { said = ''; }
                    _mcpSaidText = said; var done = function (r) { _mcpSaidText = ''; return r; };
                    try { return Promise.resolve(orig.call(A, tool, args)).then(done, function (e) { _mcpSaidText = ''; throw e; }); } catch (e2) { _mcpSaidText = ''; throw e2; }
                };
                wrapped.__accSaid = true; A.mcpCall = wrapped;
            } else if (tries > 240) clearInterval(t);
        }, 500);
    }
    installMcpSaid();
    function lastBuyerText() { if (_mcpSaidText) return _mcpSaidText; try { var lg = window.spbProAI && window.spbProAI.log ? window.spbProAI.log() : null; if (!lg) return ''; for (var k = lg.length - 1; k >= 0; k--) if (lg[k] && lg[k].role === 'user') return String(lg[k].text || ''); } catch (e) {} return ''; }
    function onlyBodyLayers(ls) { try { var rl = window.SpbProCar && window.SpbProCar.roles ? window.SpbProCar.roles() : []; var a = Array.isArray(ls) ? ls : [ls]; return a.length > 0 && a.every(function (n) { return rl.some(function (x) { return (x.name === n || x.id === n) && x.role === 'body paint'; }); }); } catch (e) { return false; } }
    function accentDefault(r) {
        if ((window.SPB_ACCENT_OFF === true) || r.keepAccents === false || !r.island || r.colors || (r.layers && !onlyBodyLayers(r.layers)) || r.element || r.graphic || r.everything || r.remaining || r.rect || r.cells || r.clear_box) return false;
        var t = lastBuyerText().toLowerCase(); if (!t) return false;
        return !ACCENT_ALL_RE.test(t) && !ACCENT_NAMED_RE.test(t);
    }
    function setRegion(z, i, r, applied) {
        var W = paintDims()[0], H = paintDims()[1], tol = clamp(r.tolerance != null ? r.tolerance : (z.pickerTolerance != null ? z.pickerTolerance : 40), 6, 100);
        var mcpFamilyGuard = mcpFamilyPreApplyError(z, r, W, H); if (mcpFamilyGuard) return mcpFamilyGuard;
        if (r.remaining) { z.color = 'remaining'; z.colorMode = 'special'; z.colors = []; applied.push('covers everything not claimed by other zones'); }
        else if (r.everything) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; applied.push('covers everything'); }
        else if (r.colors && r.colors.length) {
            z.pickerTolerance = tol;
            var tolAt = function (n) { return (Array.isArray(r.tols) && r.tols[n] != null && isFinite(r.tols[n])) ? clamp(Math.round(r.tols[n]), 3, 100) : tol; };          // WP6 2026-10-03: per-colour tolerance (edgeFit)
            if (r.colors.length === 1) { var rgb = hexRgb(r.colors[0]); z.pickerColor = r.colors[0]; z.color = { color_rgb: rgb, tolerance: tolAt(0) }; z.colorMode = 'picker'; z.colors = []; }
            else { z.colorMode = 'multi'; z.pickerColor = r.colors[0]; z.colors = r.colors.map(function (h, n) { return { color_rgb: hexRgb(h), tolerance: tolAt(n), hex: h }; }); }
            applied.push('covers paint colour' + (r.colors.length > 1 ? 's ' : ' ') + r.colors.join(', ') + ' (tolerance ' + tol + ')');
        } else if (r.tolerance != null) {
            z.pickerTolerance = tol; if (z.color && typeof z.color === 'object') z.color.tolerance = tol; if (Array.isArray(z.colors)) z.colors.forEach(function (c) { c.tolerance = tol; });
            applied.push('tolerance ' + tol);
        }
        if (r.layers) {
            var ls = Array.isArray(r.layers) ? r.layers : [r.layers], ids = ls.map(findLayer).filter(Boolean).map(function (l) { return l.id; });
            try { G('setZoneSourceLayer')(i, null); ids.forEach(function (id) { G('toggleZoneSourceLayer')(i, id, true); }); applied.push('limited to layer' + (ids.length > 1 ? 's ' : ' ') + ids.map(layerName).join(', ')); } catch (e) {}
            // Pro's engine treats a layer restriction WITHOUT a selection as "selects nothing" (verified 2026-09-30: layers-only zones rendered no change).
            // "restrict to layer X" alone means "everything on layer X", so give it the Everything selector unless a colour selection already exists.
            if (ids.length && !catchAll(z) && !zoneTargets(z).length) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; applied.push('covers everything on that layer'); }
        }
        var islandMask = null, partMask = null;
        if (r.paintable && !r.island && window.SpbProCar && window.SpbProCar.paintableMask) {      // SPB leaves pure-white source pixels alone for a mask-less 'everything' zone; a mask over the car's paintable area makes a base colour reliable
            var pm = window.SpbProCar.paintableMask(true); if (pm && r.colors && r.colors.length) { try { pm = withoutBackdrop(pm, r.colors); } catch (eB) {} }
            if (pm) { z.regionMask = pm; z.useRegion = true; z._regionDesc = 'the whole paintable area of the car'; applied.push('limited to the paintable area of the car'); }
        }
        if (r.island && window.SpbProCar) {
            var mm = window.SpbProCar.maskFor(r.island, r.portion, r.band);
            if (mm) {
                islandMask = mm.mask; partMask = mm.mask; z.regionMask = mm.mask; z.useRegion = true; z._regionDesc = regionDesc(r, mm);
                if (!catchAll(z) && !zoneTargets(z).length) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; }
                applied.push('limited to the ' + z._regionDesc);
            }
        }
        if (r.graphic) z._graphicExclude = (r.exclude && r.exclude.length) ? [].concat(r.exclude) : null;          // HELPER V3 S5 2026-10-05: a stroke_px edit redraws the line with the same cut-outs
        if (r.graphic && window.SpbGraphics) {      // a drawn design graphic (arcs, speed lines, stripes...): rendered per colour into a sheet mask on the named parts
            var gm = window.SpbGraphics.maskFor(r.graphic);
            if (gm) { islandMask = gm.mask; z.regionMask = gm.mask; z.useRegion = true; z._regionDesc = gm.desc; z._graphic = JSON.parse(JSON.stringify(r.graphic)); if (!catchAll(z) && !zoneTargets(z).length) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; } applied.push('drawn as ' + gm.desc + (gm.empty ? ' (nothing landed on the car: check the part)' : '')); }
        }
        if (r.element && window.SpbProElements) {       // the numbers / sponsors / stripes the app found on a flat paint (js/spb-pro-elements.js)
            var em = window.SpbProElements.maskFor(r.element);
            if (em) { islandMask = em.mask; z.regionMask = em.mask; z.useRegion = true; z._regionDesc = em.desc; if (!catchAll(z) && !zoneTargets(z).length) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; } applied.push('limited to ' + em.desc + ' (found from the picture)'); }
        }
        var box = r.rect || (r.cells ? parseCells(r.cells) : null);
        if (r.clear_box) { z.regionMask = null; z.useRegion = false; z._regionDesc = null; applied.push('box removed'); }
        else if (box) {
            var x0 = clamp(box.x0, 0, 1), y0 = clamp(box.y0, 0, 1), x1 = clamp(box.x1, 0, 1), y1 = clamp(box.y1, 0, 1), m = new Uint8Array(W * H), px0 = Math.round(Math.min(x0, x1) * W), px1 = Math.round(Math.max(x0, x1) * W), py0 = Math.round(Math.min(y0, y1) * H), py1 = Math.round(Math.max(y0, y1) * H), y, x;
            for (y = py0; y < py1; y++) for (x = px0; x < px1; x++) m[y * W + x] = (islandMask ? (islandMask[y * W + x] ? 255 : 0) : 255);
            z.regionMask = m; z.useRegion = true; if (!islandMask) z._regionDesc = null;
            applied.push('limited to a box (' + Math.round(x0 * 100) + '-' + Math.round(x1 * 100) + '% across, ' + Math.round(y0 * 100) + '-' + Math.round(y1 * 100) + '% down)');
        }
        if (r.exclude && r.exclude.length) {
            var ex = excludedUnion(r.exclude, W, H);
            if (ex) {
                var bm = (z.regionMask && z.useRegion) ? z.regionMask : null, km = new Uint8Array(W * H), q;
                for (q = 0; q < km.length; q++) km[q] = (!ex[q] && (!bm || bm[q])) ? 255 : 0;
                z.regionMask = km; z.useRegion = true; z._regionDesc = (z._regionDesc ? z._regionDesc + ', ' : '') + 'everything except the ' + (Array.isArray(r.exclude) ? r.exclude : [r.exclude]).join(' and the ');
                if (!catchAll(z) && !zoneTargets(z).length) { z.color = 'everything'; z.colorMode = 'special'; z.colors = []; }
                applied.push('NOT touching the ' + (Array.isArray(r.exclude) ? r.exclude : [r.exclude]).join(' and the '));
            } else applied.push('(could not find the ' + (Array.isArray(r.exclude) ? r.exclude : [r.exclude]).join(' / ') + ' to leave alone)');
        }
        if ((r.keepAccents === true || (r.keepAccents == null && accentDefault(r))) && partMask && !(window.SPB_ACCENT_OFF === true) && !r.graphic && !r.element) {          // W2-ACCENT 2026-10-09: leave the design's accent art (stripe blocks, painted shapes) inside this part alone
            var ac = accentMask(partMask, W, H);
            if (ac && ac.share > 0.01) {
                var bm2 = (z.regionMask && z.useRegion) ? z.regionMask : null, km2 = new Uint8Array(W * H), q2, kept = 0;
                for (q2 = 0; q2 < km2.length; q2++) { var on = (!bm2 || bm2[q2]) && !ac.mask[q2]; km2[q2] = on ? 255 : 0; if (on) kept++; }
                if (kept > 0) { z.regionMask = km2; z.useRegion = true; z._accentKept = Math.round(ac.share * 100); z._regionDesc = (z._regionDesc ? z._regionDesc + ', ' : '') + 'keeping the accent art (' + z._accentKept + '%)'; applied.push('keeping the accent art (stripes / painted shapes, ' + z._accentKept + '% of it) as it is'); }
            }
        }
        var familyError = intersectMcpFamilyRegion(z, r, applied); if (familyError) return familyError;
        rememberPartRegion(z, r, partMask);
        return '';
    }
    function place(z, where) {
        var list = Zs(), from = list.indexOf(z); if (from < 0) return from;
        var caIdx = -1; list.forEach(function (q, k) { if (q !== z && catchAll(q) === 'remaining') caIdx = k; });
        var to = (where === 'bottom') ? (caIdx >= 0 ? (from < caIdx ? caIdx - 1 : caIdx) : list.length - 1) : ((where != null && where !== 'top' && isFinite(Number(where))) ? Math.max(0, Math.min(list.length - 1, Math.round(Number(where)))) : 0);
        if (to !== from) { list.splice(from, 1); list.splice(to, 0, z); }
        return to;
    }
    // HELPER FIX PASS 8 2026-10-05 (owner live 11:45: "make the yellow on the spray can the same color and finish that's on the numbers now - the purple with Saturday chrome crushed down"):
    // copy a zone's LOOK exactly (every field the zone panel sets) and never its selection (region / colours / layers / masks / name / id / seed).
    var COPY_SKIP_RE = /^(id|name|color|colors|colorMode|pickerColor|pickerTolerance|tolerance|tols|regionMask|spatialMask|useRegion|hint|muted|hardEdge|renderSeedIndex|render_seed_index)$|^(source|region|lock|_)/;
    function zoneRef(x) {
        var list = Zs(); if (x == null) return null; if (typeof x === 'object') return list.indexOf(x) !== -1 ? x : null;
        if (typeof x === 'number' || /^\d+$/.test(String(x))) return list[Number(x)] || null;
        var s = String(x), sl = s.toLowerCase(); return list.filter(function (q) { return q && String(q.id) === s; })[0] || list.filter(function (q) { return q && String(q.name || '').toLowerCase() === sl; })[0] || null;
    }
    function copyLook(dst, src) {
        var c = null; try { c = G('_cloneZoneState') ? G('_cloneZoneState')(src, { preserveId: false, includeRegionMask: false, includeSpatialMask: false, includePatternStrengthMap: true }) : null; } catch (e) { c = null; }
        if (!c) c = JSON.parse(JSON.stringify(src)); var n = 0;
        Object.keys(c).forEach(function (k) { if (COPY_SKIP_RE.test(k)) return; dst[k] = c[k]; n++; });
        return n;
    }
    function lookLine(z) { var b = []; if (z.finish) b.push(nameOfFinish(z.finish, 'mono')); else if (z.base) b.push(nameOfFinish(z.base, 'base')); b.push(z.baseColorMode === 'solid' ? String(z.baseColor) : (z.baseColorMode || 'finish') + ' colour'); if (z.baseScale != null && Number(z.baseScale) !== 1) b.push('scale ' + z.baseScale); if (Array.isArray(z.specPatternStack) && z.specPatternStack.length) b.push(z.specPatternStack.length + ' spec pattern' + (z.specPatternStack.length > 1 ? 's' : '')); return b.join(', '); }
    // ===== W13-NUDGE 2026-10-09 (lane W13-NUDGE): which zone does "move the camo on the hood left" mean? Only zones that HAVE a pattern (or, for target base, a base) count. Kill window.SPB_W13N_OFF.
    var LAST_PAT = null;
    var NUDGE_PART = { hood: /\b(?:hood|bonnet)\b/, roof: /\broof\b/, trunk: /\b(?:trunk|boot|deck ?lid|rear deck)\b/, door: /\b(?:doors?|sides?|flanks?|rockers?|quarters?|panels?)\b/, fender: /\bfenders?\b|\bwings?\b/, bumper: /\bbumpers?\b|\bsplitter\b|\bdiffuser\b/, spoiler: /\bspoiler\b/, nose: /\bnose\b|\bfront\b/, tail: /\btail\b|\brear\b/ };
    function patternZoneFor(hint, opts) {
        var list = Zs(), base = !!(opts && opts.base), has = function (z) { return !!z && !z.muted && (base ? !!(z.base || z.finish) : (z.pattern && z.pattern !== 'none')); };
        var txt = function (z) { return (String(z.name || '') + ' ' + String(z._regionDesc || '')).toLowerCase(); };
        var part = hint && hint.part ? String(hint.part) : '', side = hint && hint.side ? String(hint.side) : '', re = NUDGE_PART[part] || null;
        if (re) {
            var m = [];
            list.forEach(function (z, i) { if (!z || !re.test(txt(z))) return; var t = txt(z); if (side && (side === 'left' ? /\b(?:right|passenger)\b/.test(t) && !/\b(?:left|driver)\b/.test(t) : /\b(?:left|driver)\b/.test(t) && !/\b(?:right|passenger)\b/.test(t))) return; m.push(i); });
            if (!m.length) return { status: 'nozone', part: part };
            var mp = m.filter(function (i) { return has(list[i]); });
            if (!mp.length) return { status: 'nopattern', part: part, name: list[m[0]].name };
            var pick = mp.filter(function (i) { return list[i] === LAST_PAT; })[0]; if (pick == null) pick = mp[0];
            return { status: 'ok', index: pick, name: list[pick].name, many: mp.length };
        }
        var li = LAST_PAT ? list.indexOf(LAST_PAT) : -1; if (li >= 0 && has(list[li])) return { status: 'ok', index: li, name: list[li].name, how: 'last' };
        var si = -1; try { si = selectedZoneIndex; } catch (e) { si = -1; } if (si >= 0 && has(list[si])) return { status: 'ok', index: si, name: list[si].name, how: 'selected' };
        var all = []; list.forEach(function (z, i) { if (has(z)) all.push(i); });
        if (all.length === 1) return { status: 'ok', index: all[0], name: list[all[0]].name, how: 'only' };
        return { status: all.length ? 'ambiguous' : 'nopattern', names: all.slice(0, 4).map(function (i) { return list[i].name; }) };
    }
    function edit(target, s) {
        var list = Zs(), z = (target && typeof target === 'object') ? target : list[target], applied = [], warnings = [], i = list.indexOf(z);
        if (!z || i < 0) return { ok: false, applied: [], warnings: ['no zone ' + (target && target.name || target)] };
        var v = validate(s, false); if (v.errors.length) return { ok: false, applied: [], warnings: v.errors };
        if (s.region != null) { var regionError = setRegion(z, i, s.region, applied); if (regionError) return { ok: false, applied: [], warnings: [regionError] }; }
        if (s.name != null) { z.name = zoneName(s.name); applied.push('renamed "' + z.name + '"'); }
        // HELPER FIX PASS 8 2026-10-05: the copied look goes on FIRST; a finish / colour in the same change that only repeats it is skipped (re-assigning the finish would reset its scale,
        // a repeated solid colour would clear a copied hue shift); a different colour / any other setting in the same change still applies on top ("the same finish as the numbers, but red")
        var copied = null;
        if (s.stroke_px != null) {          // HELPER V3 S5 2026-10-05: "thinner" / "half that" on a line zone = the same graphic redrawn at the new width (same colour, finish, cut-outs)
            if (!z._graphic) warnings.push('stroke_px: this zone is not a line (no graphic): nothing to make thinner or thicker');
            else { var sg = JSON.parse(JSON.stringify(z._graphic)), sgi = sg.item || sg, spx = Math.round(clamp(s.stroke_px, 1, (window.SPB_W31_OFF || (window.SPB_OF_CFG && (window.SPB_OF_CFG.noW31 || window.SPB_OF_CFG.noW31_5))) ? 60 : 150) * 10) / 10; /* W31-5 2026-10-10: same ceiling as the planner (kill noW31_5) */ sgi.stroke_px = spx; var sre = setRegion(z, i, { graphic: sg, exclude: z._graphicExclude || undefined }, []); if (sre) warnings.push('stroke_px: ' + sre); else applied.push('line width ' + spx + ' px'); }
        }
        if (s.copy_look_from != null) { var csrc = zoneRef(s.copy_look_from); if (!csrc || csrc === z) warnings.push('copy_look_from: no zone ' + s.copy_look_from); else { var ncp = copyLook(z, csrc); copied = csrc; applied.push('copied the whole look of "' + csrc.name + '" (' + ncp + ' settings: ' + lookLine(csrc) + ')'); } }
        if (copied && s.finish != null) { var cfd = finishDoc(s.finish); if (cfd && (cfd.kind === 'mono' ? copied.finish === cfd.id : (copied.base === cfd.id && !copied.finish))) s = Object.assign({}, s, { finish: null }); }
        if (copied && s.color != null && (!isHex(s.color) || (copied.baseColorMode === 'solid' && String(copied.baseColor).toLowerCase() === String(s.color).toLowerCase()))) s = Object.assign({}, s, { color: null });          // only a DIFFERENT exact colour overrides the copied one
        if (s.finish != null) {
            var fd = finishDoc(s.finish);
            // OWNTURN 2026-10-04 (owner replay: "Give the spec on the Yellow Base layer a Fractured finish ..." -> finish base::f_chrome with no colour; assigning the
            // foundation switched the zone back to the source paint and the hot pink body turned YELLOW again). A plain base finish changes the material only: a zone that
            // was an explicit solid colour / gradient keeps it unless this same change sets a colour. Monolithics are left alone (they are complete looks).
            var keepCol = (s.color == null && s.gradient == null && fd.kind !== 'mono' && (z.baseColorMode === 'solid' || z.baseColorMode === 'gradient')) ? { m: z.baseColorMode, c: z.baseColor, g: z.gradientStops ? JSON.parse(JSON.stringify(z.gradientStops)) : null, d: z.gradientDirection, st: z.baseColorStrength, ex: z.baseColorModeExplicit, h: z.baseHueOffset, sa: z.baseSaturationAdjust, b: z.baseBrightnessAdjust } : null;
            try { var prevSel = selectedZoneIndex; selectedZoneIndex = i; G('assignFinishToSelected')(fd.id); selectedZoneIndex = prevSel; applied.push('finish ' + nameOfFinish(fd.id, fd.kind)); } catch (e) { warnings.push('finish failed: ' + e.message); }
            if (keepCol && (z.baseColorMode !== keepCol.m || z.baseColor !== keepCol.c)) { z.baseColorMode = keepCol.m; z.baseColor = keepCol.c; if (keepCol.g) z.gradientStops = keepCol.g; if (keepCol.d) z.gradientDirection = keepCol.d; z.baseColorStrength = keepCol.st != null ? keepCol.st : 1; z.baseColorModeExplicit = keepCol.ex != null ? keepCol.ex : true; z.baseHueOffset = keepCol.h; z.baseSaturationAdjust = keepCol.sa; z.baseBrightnessAdjust = keepCol.b; z.baseColorSource = null; applied.push('kept the zone colour'); }
        }
        if (s.color != null) {
            if (isHex(s.color)) { z.baseColorMode = 'solid'; z.baseColor = String(s.color).toLowerCase(); z.baseColorSource = null; if (z.baseColorStrength == null) z.baseColorStrength = 1; z.baseColorModeExplicit = true; applied.push('colour ' + s.color); }
            else if (s.color === 'source') { z.baseColorMode = 'source'; z.baseColorSource = null; z.baseColorModeExplicit = true; applied.push('keeps the car\'s own colour'); }
            else { z.baseColorMode = 'finish'; z.baseColorModeExplicit = true; try { if (s.finish && typeof _spbDefaultBaseColorToFinish === 'function') _spbDefaultBaseColorToFinish(z, String(s.finish).replace(/^[a-z]+::/, '')); } catch (e2) {} applied.push('finish\'s own colour'); }
        }
        // OWNTURN 2026-10-04 (owner: "make the purple solid hot pink" -> "Done", the car turned SKY BLUE in the replay): a zone made by "shift the yellow to purple, keeping
        // the shading" carries baseHueOffset -136; a new solid colour / gradient kept that offset, so #ff2d95 rendered at hue 194. A new exact colour clears the old shift
        // unless the same change sets hue / saturation / brightness itself.
        if ((isHex(s.color) || s.gradient) && s.hue == null && s.saturation == null && s.brightness == null && (z.baseHueOffset || z.baseSaturationAdjust || z.baseBrightnessAdjust)) { z.baseHueOffset = 0; z.baseSaturationAdjust = 0; z.baseBrightnessAdjust = 0; applied.push('cleared the old colour shift'); }
        if (s.gradient != null) {
            var stops = s.gradient.stops.map(function (t) { return { pos: Math.round(clamp(t.pos, 0, 100)), color: String(t.color).toLowerCase() }; }).sort(function (a, b) { return a.pos - b.pos; });
            z.baseColorMode = 'gradient'; z.gradientStops = stops; z.gradientDirection = s.gradient.direction || z.gradientDirection || 'horizontal'; z.baseColorSource = null; z.baseColorModeExplicit = true; if (z.baseColorStrength == null) z.baseColorStrength = 1;
            // MCPSCEN 2026-10-05 (truck: a blue -> orange gradient on the carbon HOOD zone came out all orange-brown: the gradient spanned the whole 2048 sheet and the hood
            // only saw its orange end). A zone limited to a part / box / element (under 85% of the sheet along the gradient) now runs the gradient across ITSELF: the stops are remapped into
            // the zone's range on the sheet (exact for the linear directions). Not the engine's base_color_fit_zone: that also squeezes the finish's spec texture into the box.
            var bb = (s.gradient.fit === false) ? null : gradientZoneBox(z, s.gradient.fit === true), gd = z.gradientDirection, tr = null;
            if (bb) { var W0 = paintDims()[0], H0 = paintDims()[1], X0 = bb[0] / W0, X1 = bb[2] / W0, Y0 = bb[1] / H0, Y1 = bb[3] / H0; tr = gd === 'horizontal' ? [X0, X1] : (gd === 'vertical' ? [Y0, Y1] : (gd === 'diagonal_down' ? [(X0 + Y0) / 2, (X1 + Y1) / 2] : (gd === 'diagonal_up' ? [(X0 + 1 - Y1) / 2, (X1 + 1 - Y0) / 2] : null))); }
            if (tr && s.gradient.fit !== true && tr[1] - tr[0] > 0.85) tr = null;          // the zone already spans (almost) the whole sheet along the gradient: keep it sheet-wide
            if (tr) { z.gradientStops = stops.map(function (t) { return { pos: Math.round((tr[0] + t.pos / 100 * (tr[1] - tr[0])) * 100), color: t.color }; }); }
            applied.push('gradient ' + stops.map(function (t) { return t.color + '@' + t.pos; }).join(' → ') + ' (' + gd + (tr ? ', across this zone: sheet positions ' + z.gradientStops[0].pos + '-' + z.gradientStops[z.gradientStops.length - 1].pos : ', across the whole sheet') + ')');
        }
        if (s.hue != null) { z.baseHueOffset = Math.round(clamp(s.hue, -180, 180)); applied.push('hue ' + z.baseHueOffset); }
        if (s.saturation != null) { z.baseSaturationAdjust = Math.round(clamp(s.saturation, -100, 100)); applied.push('saturation ' + z.baseSaturationAdjust); }
        if (s.brightness != null) { z.baseBrightnessAdjust = Math.round(clamp(s.brightness, -100, 200)); applied.push('brightness ' + z.baseBrightnessAdjust); }
        if (s.base_strength != null) { z.baseStrength = clamp(s.base_strength, 0, 200) / 100; applied.push('base strength ' + Math.round(z.baseStrength * 100) + '%'); }
        if (s.spec_strength != null) { z.baseSpecStrength = clamp(s.spec_strength, 0, 200) / 100; applied.push('spec strength ' + Math.round(z.baseSpecStrength * 100) + '%'); }
        if (s.scale != null) { z.baseScale = clamp(s.scale, 0.05, 5); applied.push('base scale ' + z.baseScale); }
        if (s.rotation != null) { z.baseRotation = Math.round(clamp(s.rotation, 0, 359)); applied.push('base rotation ' + z.baseRotation); }
        if (s.intensity != null) { z.intensity = String(Math.round(clamp(s.intensity, 0, 100))); applied.push('intensity ' + z.intensity); }
        if (s.muted != null) { z.muted = !!s.muted; applied.push(z.muted ? 'muted' : 'unmuted'); }
        if (s.pattern != null) {
            var p = typeof s.pattern === 'string' ? { id: s.pattern } : s.pattern;
            if (p.id === 'none') { z.pattern = 'none'; applied.push('pattern removed'); }
            else {
                if (!z.base && !z.finish) z.base = 'gloss';
                LAST_PAT = z;                 z.pattern = p.id; if (p.opacity != null) z.patternOpacity = Math.round(clamp(p.opacity, 0, 100)); if (p.scale != null) z.scale = clamp(p.scale, 0.05, 5); if (p.rotation != null) z.rotation = Math.round(clamp(p.rotation, 0, 359));
                applied.push('pattern ' + patName(p.id));
            }
        }
        if (s.pattern_position != null) {          // W13-NUDGE 2026-10-09 (lane W13-NUDGE; real tester: "is there a way to adjust using an x/y axis"): slide a zone's pattern / picture through the SAME setters as the Position X / Y sliders (undo step + slider labels), clamp 0-100. Kill window.SPB_W13N_OFF.
            if (window.SPB_W13N_OFF) warnings.push('pattern_position: switched off');
            else {
                var pq = s.pattern_position, pbase = pq.target === 'base', fx = pbase ? G('setZoneBaseOffsetX') : G('setZonePatternOffsetX'), fy = pbase ? G('setZoneBaseOffsetY') : G('setZonePatternOffsetY');
                var hasPat = pbase ? !!(z.base || z.finish) : ((z.pattern && z.pattern !== 'none') || (s.pattern && s.pattern.id && s.pattern.id !== 'none'));
                if (typeof fx !== 'function' || typeof fy !== 'function') warnings.push('pattern_position: the position controls are not loaded');
                else if (!hasPat) warnings.push('pattern_position: "' + (z.name || 'this zone') + '" has no pattern or picture to move');
                else {
                    var curX = Math.round((pbase ? (z.baseOffsetX != null ? z.baseOffsetX : 0.5) : (z.patternOffsetX != null ? z.patternOffsetX : 0.5)) * 100), curY = Math.round((pbase ? (z.baseOffsetY != null ? z.baseOffsetY : 0.5) : (z.patternOffsetY != null ? z.patternOffsetY : 0.5)) * 100), nx = curX, ny = curY, mv = [];
                    if (pq.x != null) nx = pq.x; else if (pq.dx != null) nx = curX + Number(pq.dx);
                    if (pq.y != null) ny = pq.y; else if (pq.dy != null) ny = curY + Number(pq.dy);
                    nx = Math.round(clamp(nx, 0, 100)); ny = Math.round(clamp(ny, 0, 100));
                    LAST_PAT = z;
                    if (!pbase && z.patternPlacement === 'fit') { z.patternPlacement = 'normal'; applied.push('placement switched from Fit to Zone to Full Canvas (Fit locks the position sliders)'); }
                    if (nx !== curX) { fx(i, nx); mv.push('X ' + curX + ' -> ' + nx); }
                    if (ny !== curY) { fy(i, ny); mv.push('Y ' + curY + ' -> ' + ny); }
                    applied.push(mv.length ? ((pbase ? 'base picture' : 'pattern') + ' position ' + mv.join(', ') + ' (50 = centre)') : ((pbase ? 'base picture' : 'pattern') + ' already at that position (X ' + curX + ', Y ' + curY + ')'));
                }
            }
        }
        if (s.spec_patterns != null) {
            var stack = [];
            s.spec_patterns.forEach(function (l) {
                var layer = null; try { layer = _buildSpecPatternLayer(l.id); } catch (e3) { layer = { pattern: l.id, opacity: 50, blendMode: 'normal', channels: 'MRC', range: 40, params: {}, offsetX: 0.5, offsetY: 0.5, scale: 1, rotation: 0, placement: 'normal', render_version: 2, seed: 42, muted: false, solo: false }; }
                if (l.opacity != null) layer.opacity = Math.round(clamp(l.opacity, 0, 100)); if (l.scale != null) layer.scale = clamp(l.scale, 0.05, 5); if (l.rotation != null) layer.rotation = Math.round(clamp(l.rotation, 0, 359));
                if (l.channels) { var ch = String(l.channels).toUpperCase().replace(/[^MRC]/g, ''); if (ch) { layer.channels = ch; layer.channelsCustomized = true; } }
                stack.push(layer);
            });
            z.specPatternStack = stack; applied.push('spec pattern' + (stack.length > 1 ? 's ' : ' ') + stack.map(function (l) { return specName(l.pattern); }).join(' + '));
        }
        if (s.second_base != null) {
            var sb = typeof s.second_base === 'string' ? { id: s.second_base } : s.second_base;
            try {
                if (sb.id === 'none') { G('setZoneSecondBase')(i, ''); applied.push('overlay base removed'); }
                else {
                    var sd = finishDoc(sb.id); G('setZoneSecondBase')(i, sd.id);
                    if (sb.color && isHex(sb.color)) G('setZoneSecondBaseColor')(i, sb.color);
                    if (sb.strength != null) G('setZoneSecondBaseStrength')(i, Math.round(clamp(sb.strength, 0, 100)));
                    applied.push('overlay ' + nameOfFinish(sd.id, sd.kind) + (sb.color && isHex(sb.color) ? ' in ' + String(sb.color).toLowerCase() : '') + (sb.strength != null ? ' at ' + Math.round(clamp(sb.strength, 0, 100)) + '%' : ''));          // MCPSCEN 2026-10-05: the overlay colour + strength were applied but never reported
                }
            } catch (e4) { warnings.push('second base failed: ' + e4.message); }
        }
        if (s.spec_shift != null) {
            // MCPSCEN 2026-10-05 (DLM: spec_shift {metallic:60, roughness:-30} was applied as "metal 0, rough 0, clearcoat 0"): the spelled-out channel names count too
            var ss = s.spec_shift; if (ss && typeof ss === 'object') { ss = Object.assign({}, ss); [['metallic', 'metal'], ['metalness', 'metal'], ['r', 'metal'], ['roughness', 'rough'], ['g', 'rough'], ['clear', 'clearcoat'], ['clear_coat', 'clearcoat'], ['clearcoat_level', 'clearcoat'], ['b', 'clearcoat']].forEach(function (pr) { if (ss[pr[1]] == null && ss[pr[0]] != null) ss[pr[1]] = Number(ss[pr[0]]); }); }
            if (ss.metal != null) z.specShiftR = Math.round(clamp(ss.metal, -127, 127)); if (ss.rough != null) z.specShiftG = Math.round(clamp(ss.rough, -127, 127)); if (ss.clearcoat != null) z.specShiftB = Math.round(clamp(ss.clearcoat, -127, 127));
            applied.push('spec shift metal ' + (z.specShiftR || 0) + ', rough ' + (z.specShiftG || 0) + ', clearcoat ' + (z.specShiftB || 0));          // MCPSCEN 2026-10-05: the values, so the model can report them
        }
        if (s.priority != null) { var np = place(z, s.priority); applied.push('moved: now zone ' + np + (np === 0 ? ' (top)' : '') + ' (0 = top)');          /* MCPSCEN 2026-10-05: was position np+1 (1-based) while every other zone number is 0-based */ }
        // MCPSCEN 2026-10-05 (MCP: "carbon trunk" #1a1a1a + carbon_fiber came out blue-grey; then colour #d01818 under it changed NOTHING): a paint pattern at full opacity
        // lays its OWN colours over the zone colour. Say so when the colour or pattern changed, so the AI lowers the opacity instead of telling the buyer it is red.
        if ((s.color != null || s.gradient != null || s.pattern) && z.pattern && z.pattern !== 'none' && (z.patternOpacity == null ? 100 : Number(z.patternOpacity)) >= 85 && (z.baseColorMode === 'solid' || z.baseColorMode === 'gradient')) warnings.push('the ' + patName(z.pattern) + ' pattern is at opacity ' + (z.patternOpacity == null ? 100 : z.patternOpacity) + ': its own colours cover most of the zone colour. For a coloured ' + patName(z.pattern) + ' (e.g. red carbon) set pattern opacity 40-60 so the colour shows.');
        return { ok: true, applied: applied, warnings: warnings };
    }
    function add(s) {
        var v = validate(s, true); if (v.errors.length) return { ok: false, applied: [], warnings: v.errors };
        var before = Zs().length;
        try { G('addZone')(true); } catch (e) { return { ok: false, applied: [], warnings: ['addZone failed: ' + e.message] }; }
        if (Zs().length <= before) return { ok: false, applied: [], warnings: ['zone limit reached'] };
        var idx = Zs().length - 1, z = Zs()[idx];
        z.name = zoneName(s.name || 'AI zone');
        if (!s.finish && !z.base) z.base = 'gloss';
        var r = edit(z, s);
        if (s.priority == null) { var pp = place(z, (s.region && (s.region.remaining)) ? 'bottom' : 'top'); r.applied.push(pp === 0 ? 'placed at the top of the stack (wins overlaps)' : 'placed at the bottom of the stack'); }
        r.zone = z; return r;
    }
    function duplicate(target, s) {
        var list = Zs(), i = (target && typeof target === 'object') ? list.indexOf(target) : target, src = list[i];
        if (!src) return { ok: false, applied: [], warnings: ['no zone to duplicate'] };
        var anchor = !!(s && s.textureAnchor === 'canvas'); if (anchor) { s = Object.assign({}, s); delete s.textureAnchor; }
        var before = list.length; G('duplicateZone')(i);
        if (Zs().length <= before) return { ok: false, applied: [], warnings: ['zone limit reached'] };
        var z = Zs()[i + 1];
        // ENGINE TEXTURE ANCHOR 2026-10-06 (ENGINE_TEXTURE_ANCHOR.md): a part-limited copy of a zone renders the SAME grain as the original only when both
        // are canvas-anchored AND share the seed (verified 22/22 bit-exact in scripts/spb_texture_anchor_check.py --roof). Opt-in via spec.textureAnchor.
        if (anchor && z) { z.textureAnchor = 'canvas'; src.textureAnchor = 'canvas'; if (src.renderSeedIndex != null) z.renderSeedIndex = src.renderSeedIndex; }
        var r = s ? edit(z, s) : { ok: true, applied: [], warnings: [] };
        r.applied.unshift('duplicated "' + src.name + '" (copy sits just below it)'); r.zone = z; return r;
    }
    // ===== W3-HONEST 2026-10-09 (lane W3-HONEST; owner rule #1 "be honest"; MCP A-0196 "left side candy blue" painted only the exposed 8% while the reply claimed the side) =====
    // Visible coverage = of the pixels a zone SELECTS (its part / layers / exclusions / colours), the share it actually WINS after the zones above it (LOWER index wins) take theirs.
    // In-app repro (arcav5): "left side seafoam" -> "whole car matte black" -> "left side candy blue" edited the OLD left-side zone, now buried under the black body zone: 8% showed,
    // reply said "the left side changed to blue candy". After every batch, each part zone that shows under 85% of what it selects is either (a) lifted above the older PLAIN recolour zones
    // that cover it (a reorder inside the same undo step; nothing is deleted; refused if it would repaint a non-plain zone's pixels) or (b) reported in one honest sentence.
    // Kill switch: window.SPB_HONEST_OFF = true (SPB_HONEST_NOLIFT = report only). Tunable: SPB_HONEST_MIN (default 0.85).
    function honestOff() { return window.SPB_HONEST_OFF === true; }
    function plainRecolour(q) {          // a zone that only recolours / refinishes its area: no pattern, spec pattern, gradient, second base, drawn shape or element
        if (!q || q.muted) return false; var m = q.baseColorMode;
        if (m === 'gradient' || m === 'source') return false;
        if (q.pattern && q.pattern !== 'none') return false;
        if (Array.isArray(q.specPatternStack) && q.specPatternStack.length) return false;
        if (q.secondBase && q.secondBase !== 'none') return false;
        if (/graphic|shape|outline|element|stripe|line|gradient/i.test(String(q._regionDesc || ''))) return false;
        return true;
    }
    function provOf(z) { try { var p = z && z._aiPartProv && JSON.parse(z._aiPartProv.r); return p && p.island ? p : null; } catch (e) { return null; } }
    function partWords(p) { return p ? (p.portion ? p.portion + ' of the ' : 'the ') + p.island : 'the car'; }
    // -> { n, vis, share, blockers:[{index, zone, count, pct, plain}], samples, claims:{j: Uint8Array}, owner:Int32Array } or null
    function analyseZone(list, i, st) {
        var z = list[i]; if (!z || z.muted) return null; var W = paintDims()[0], H = paintDims()[1], pd = paintPixels(); if (!pd || !pd.data || pd.data.length !== W * H * 4) return null;
        if (catchAll(z) === 'remaining') return null;
        var own = ownTest(z, W, H); if (!own) return null; st = st || 8;
        var d = pd.data, samples = [], ix, iy, o, idx;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) { idx = iy * W + ix; o = idx * 4; if (d[o + 3] < 8) continue; if (own(d[o], d[o + 1], d[o + 2], idx)) samples.push(idx); }
        var n = samples.length, claims = {}, owner = new Int32Array(n), j, t, s;
        for (s = 0; s < n; s++) owner[s] = i;
        for (j = 0; j < i; j++) { t = claimTest(list, j, W, H); if (!t) continue; var cj = new Uint8Array(n), any = 0; for (s = 0; s < n; s++) { o = samples[s] * 4; if (t(d[o], d[o + 1], d[o + 2], samples[s])) { cj[s] = 1; any++; if (owner[s] === i) owner[s] = j; } } if (any) claims[j] = cj; }
        var cnt = {}, vis = 0; for (s = 0; s < n; s++) { if (owner[s] === i) vis++; else cnt[owner[s]] = (cnt[owner[s]] || 0) + 1; }
        var bl = Object.keys(cnt).map(function (k2) { var q = list[k2]; return { index: Number(k2), zone: q.name, count: cnt[k2], pct: Math.round(cnt[k2] / Math.max(1, n) * 100), plain: plainRecolour(q) }; }).sort(function (a, b) { return b.count - a.count; });
        return { n: n, vis: vis, share: n ? vis / n : 1, blockers: bl, samples: samples, claims: claims, owner: owner };
    }
    // public: SpbProZone.visibleShare(zone | index | id | name | "left side" [, {portion}])  ->  { zone, index, part, share (0..1), visible_pct, intended_samples, blocked_by:[{zone,index,pct,plain_recolour}], note }
    // A part name (a string that is not a zone name) answers for the TOPMOST zone that was placed on that part.
    function visibleShare(x, opts) {
        try {
            return withMemo(function () {
                var list = Zs(), z = null, i = -1;
                if (x != null && typeof x === 'object') z = list.indexOf(x) !== -1 ? x : null; else if (x != null) z = zoneRef(x);
                if (!z && typeof x === 'string') { var pn = x.toLowerCase().trim(), po = opts && opts.portion ? String(opts.portion).toLowerCase() : null; for (var q = 0; q < list.length; q++) { var pv = provOf(list[q]); if (pv && !list[q].muted && String(pv.island).toLowerCase() === pn && (!po || String(pv.portion || '').toLowerCase() === po)) { z = list[q]; break; } } }
                if (!z) return { error: 'no zone or part "' + x + '" is on the car' };
                i = list.indexOf(z); var a = analyseZone(list, i, (opts && opts.step) || 8); if (!a) return { zone: z.name, index: i, share: 1, visible_pct: 100, intended_samples: 0, blocked_by: [], note: 'this zone selects nothing (or is muted / the catch-all)' };
                var pv2 = provOf(z), out = { zone: z.name, index: i, part: pv2 ? partWords(pv2).replace(/^the /, '') : null, share: Math.round(a.share * 1000) / 1000, visible_pct: Math.round(a.share * 100), intended_samples: a.n, blocked_by: a.blockers.slice(0, 4).map(function (b) { return { zone: b.zone, index: b.index, pct: b.pct, plain_recolour: b.plain }; }) };
                if (a.share < 0.85) out.note = 'only about ' + out.visible_pct + '% of what this zone selects shows; zones above it cover the rest';
                return out;
            });
        } catch (e) { return { error: String(e && e.message || e) }; }
    }
    // after a batch: lift part zones above the plain recolours that bury them, or say so honestly. kinds[k] / specs[k] = op kind / spec of results[k]
    function honestPass(results, kinds, specs) {
        if (honestOff()) return; var MIN = Number(window.SPB_HONEST_MIN) > 0 ? Number(window.SPB_HONEST_MIN) : 0.85;
        withMemo(function () {
            results.forEach(function (r, k) {
                try {
                    var z = r && r._z, list = Zs(), i = z ? list.indexOf(z) : -1;
                    if (!r || !r.ok || !z || i <= 0 || (kinds[k] !== 'add' && kinds[k] !== 'edit')) return;
                    if (specs[k] && specs[k].priority != null) return;          // the caller placed it on purpose (VISIBLE_COLOUR puts a zone BELOW a recolour so only the visible colour changes)
                    var pv = provOf(z); if (!pv || z.muted) return;
                    var a = analyseZone(list, i, 8); if (!a || a.n < 150 || a.share >= MIN) { if (a) r.visible_share = Math.round(a.share * 100) / 100; return; }
                    r.visible_share = Math.round(a.share * 100) / 100; r.warnings = r.warnings || []; r.applied = r.applied || [];
                    var sig = a.blockers.filter(function (b) { return b.pct >= 2; }), words = partWords(pv), before = Math.round(a.share * 100);
                    var names = sig.slice(0, 2).map(function (b) { return '“' + b.zone + '”'; }).join(' and ');
                    var allPlain = sig.length && sig.every(function (b) { return b.plain; });
                    if (allPlain && !window.SPB_HONEST_NOLIFT) {
                        var tgt = Math.min.apply(null, sig.map(function (b) { return b.index; })), s, n = a.n, now = 0, stolen = 0;
                        for (s = 0; s < n; s++) { var blockedAbove = false; for (var j in a.claims) { if (Number(j) < tgt && a.claims[j][s]) { blockedAbove = true; break; } } if (!blockedAbove) { now++; var ow = a.owner[s]; if (ow !== i && !plainRecolour(list[ow])) stolen++; } }
                        var after = now / n;
                        if (stolen / n <= 0.02 && after >= Math.min(MIN, a.share + 0.15)) {
                            place(z, tgt); r.index = list.indexOf(z); r.visible_share = Math.round(after * 100) / 100; r.lifted = { above: sig.map(function (b) { return b.zone; }), from: before, to: Math.round(after * 100) };
                            r.applied.push('lifted above the older plain recolour' + (sig.length > 1 ? 's ' : ' ') + names + ' that covered ' + (100 - before) + '% of ' + words + ' (now ' + Math.round(after * 100) + '% of it shows)');
                            r.warnings.push('An earlier layer (' + names + ') was covering ' + (before <= 5 ? 'almost all' : 'about ' + (100 - before) + '%') + ' of ' + words + ', so I put this on top of it (' + Math.round(after * 100) + '% of ' + words + ' now shows). Undo puts it back; nothing was deleted.');
                            return;
                        }
                    }
                    r.warnings.push('Only about ' + before + '% of ' + words + ' shows this change: ' + (names ? 'an earlier layer (' + names + ') is covering the rest' : 'other layers cover the rest') + (allPlain ? '' : ' and I did not want to paint over it') + '. Move this zone above ' + (names || 'those layers') + ' in the zone list to see it fully.');
                    r.hidden_by = sig.slice(0, 3).map(function (b) { return { zone: b.zone, index: b.index, pct: b.pct }; });
                } catch (eH) { try { console.warn('[PRO HONEST]', eH); } catch (e2) {} }
            });
        });
    }
    // one-click fix for the (b) case: lift a zone above EVERY zone that covers part of it (one undo step, nothing deleted). -> { ok, from, to, visible_pct } (the caller says it in words)
    function putOnTop(x) {
        try {
            var list = Zs(), z = (x != null && typeof x === 'object') ? x : zoneRef(x), i = z ? list.indexOf(z) : -1; if (i < 0) return { ok: false, error: 'no such zone' };
            var a = withMemo(function () { return analyseZone(list, i, 8); }); if (!a || !a.blockers.length) return { ok: true, from: i, to: i, visible_pct: a ? Math.round(a.share * 100) : 100, note: 'nothing covers it' };
            var tgt = Math.min.apply(null, a.blockers.filter(function (b) { return b.pct >= 2; }).map(function (b) { return b.index; })); if (!isFinite(tgt)) tgt = 0;
            try { if (typeof window.pushZoneUndo === 'function') window.pushZoneUndo('Put "' + z.name + '" on top'); } catch (eU) {}
            quiet(function () { place(z, tgt); }); try { G('renderZones')(); } catch (e6) {} try { G('triggerPreviewRender')(); } catch (e7) {}
            var vs = visibleShare(z); return { ok: true, from: i, to: Zs().indexOf(z), visible_pct: vs.visible_pct, covered_before: a.blockers.slice(0, 3).map(function (b) { return b.zone; }) };
        } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
    }
    // one undo step, one repaint, no toasts. Zone refs are resolved to objects UP FRONT so earlier ops (adds, moves) cannot shift later refs.
    function batch(ops, label, opts) {
        var results = [], op = window.pushZoneUndo, selObj = null, resolved;
        try { selObj = Zs()[selectedZoneIndex]; } catch (e) {}
        resolved = (ops || []).map(function (o) { return { kind: o.kind, spec: o.spec || {}, ref: o.kind === 'add' ? null : ((o.zone && typeof o.zone === 'object') ? o.zone : Zs()[o.zone]) }; });
        var familyPreparationError = '';
        resolved.forEach(function (o) { var r = o.spec && o.spec.region; if (!r || !r.mcpFamily || familyPreparationError) return; var prepared = prepareMcpFamilyRegion(r); if (prepared.error) familyPreparationError = prepared.error; else { hideProp(r, '_mcpFamilyMask', prepared.mask); hideProp(r, '_mcpFamilyTicket', prepared.ticket); } });          // M3 2026-10-07 (class APP FREEZE, train A-0417 via MCP spb_refinish {target colour, part}): the 4M-entry mask sat on the caller's spec.region as an ENUMERABLE field, and spb-pro-ai.js registerAppliedPartZones -> editKey -> partRegionKey JSON.stringify'd it (4M keys) = the page froze > 10 min. Transient fields are now non-enumerable (JSON / Object.keys skip them; direct reads still work).
        if (familyPreparationError) return resolved.map(function (o, i) { return { ok: false, applied: [], warnings: [familyPreparationError], index: o.ref ? Zs().indexOf(o.ref) : -1, name: o.spec && o.spec.name }; });
        try { if (typeof op === 'function' && !(opts && opts.noUndo)) op(label || 'AI edit'); } catch (e2) {}
        quiet(function () {
            resolved.forEach(function (o) {
                var r;
                try {
                    if (o.kind === 'add') r = add(o.spec);
                    else if (!o.ref) r = { ok: false, applied: [], warnings: ['that zone no longer exists'] };
                    else if (o.kind === 'duplicate') r = duplicate(o.ref, o.spec);
                    else if (o.kind === 'move') r = edit(o.ref, { priority: o.spec.to != null ? o.spec.to : o.spec.priority });
                    else r = edit(o.ref, o.spec);
                } catch (e3) { r = { ok: false, applied: [], warnings: [String(e3 && e3.message || e3)] }; try { console.warn('[PRO ZONE KIT]', e3); } catch (e4) {} }
                r._z = r.zone || o.ref; delete r.zone; results.push(r);
            });
        });
        try { honestPass(results, resolved.map(function (o) { return o.kind; }), resolved.map(function (o) { return o.spec; })); } catch (eHn) {}          // W3-HONEST 2026-10-09: visible-coverage check (kill switch SPB_HONEST_OFF)
        try { var si = selObj ? Zs().indexOf(selObj) : -1; if (si >= 0) selectedZoneIndex = si; } catch (e5) {}
        results.forEach(function (r) { r.index = r._z ? Zs().indexOf(r._z) : -1; r.name = r._z ? r._z.name : undefined; delete r._z; });
        try { G('renderZones')(); } catch (e6) {} try { G('triggerPreviewRender')(); } catch (e7) {}
        return results;
    }

    // The car's own BODY colour(s) inside a region ({part,portion,band} or the whole sheet): so a design zone on a flat paint file recolours the body, not the numbers / sponsors / logos on it
    // MCPSCEN 2026-10-05 (flat SS: "main colour matte" put its spec on the template's brown dead space: the backdrop #5a4f48 is within the weighted tolerance of the
    // yellow's dark-olive shade #646001, and the SS paintable mask is coarse). A colour zone limited to the paintable area also leaves out the backdrop colour itself
    // (the most common dead-space tone, >= 3% of the sheet), unless a target colour IS that tone.
    function withoutBackdrop(pm, colors) {
        var pd = paintPixels(); if (!pd) return pm; var W = paintDims()[0], H = paintDims()[1]; if (pm.length !== W * H) return pm; var d = pd.data, bins = {}, tot = 0, x, y, o;
        for (y = 0; y < H; y += 4) for (x = 0; x < W; x += 4) { o = (y * W + x) * 4; tot++; var R = d[o], Gc = d[o + 1], B = d[o + 2]; if (d[o + 3] < 128 || !(R >= Gc && Gc >= B && R < 140 && R - B > 8 && R - B < 52)) continue; var k = (R >> 3) + ',' + (Gc >> 3) + ',' + (B >> 3), bn = bins[k] || (bins[k] = { n: 0, r: 0, g: 0, b: 0 }); bn.n++; bn.r += R; bn.g += Gc; bn.b += B; }
        var best = null; Object.keys(bins).forEach(function (k) { if (!best || bins[k].n > best.n) best = bins[k]; }); if (!best || best.n < tot * 0.03) return pm;
        var br = best.r / best.n, bg = best.g / best.n, bb = best.b / best.n;
        if (colors.some(function (h) { var c = hexRgb(h); if (!c) return false; var e1 = c[0] - br, e2 = c[1] - bg, e3 = c[2] - bb; return e1 * e1 + e2 * e2 + e3 * e3 < 1600; })) return pm;
        var out = new Uint8Array(pm.length), n; for (n = 0; n < pm.length; n++) { if (!pm[n]) continue; o = n * 4; var f1 = d[o] - br, f2 = d[o + 1] - bg, f3 = d[o + 2] - bb; out[n] = (f1 * f1 + f2 * f2 + f3 * f3 < 196) ? 0 : pm[n]; }
        return out;
    }
    function bodyColours(r) {
        var pd = paintPixels(); if (!pd) return []; var W = paintDims()[0], H = paintDims()[1], mask = null;
        if (r && r.island && window.SpbProCar) { var mm = window.SpbProCar.maskFor(r.island, r.portion, r.band); if (mm) mask = mm.mask; }
        // MCPSCEN 2026-10-05 (owner SS PSD in safe-fallback import: the composite's dead space is WHITE, so white became a second "body colour" and a scheme repainted
        // the white sponsor lettering; 78% of that white lay outside the car). The whole-car count only looks inside the car's paintable area when the template has one.
        if (!mask && window.SpbProCar && window.SpbProCar.paintableMask) { try { var pmk = window.SpbProCar.paintableMask(); if (pmk && pmk.length === W * H) mask = pmk; } catch (epm) {} }
        var d = pd.data, bins = {}, tot = 0, x, y;
        for (y = 0; y < H; y += 3) for (x = 0; x < W; x += 3) {
            var idx = y * W + x; if (mask && !mask[idx]) continue; var o = idx * 4, R = d[o], Gc = d[o + 1], B = d[o + 2]; if (d[o + 3] < 40) continue;
            if (R >= Gc && Gc >= B && R < 140 && R - B > 8 && R - B < 52) continue;      // the template's dead-space tone
            var k = (R >> 4) + ',' + (Gc >> 4) + ',' + (B >> 4), b = bins[k] || (bins[k] = { n: 0, r: 0, g: 0, b: 0 }); b.n++; b.r += R; b.g += Gc; b.b += B; tot++;
        }
        var arr = Object.keys(bins).map(function (k) { var b = bins[k]; return { n: b.n, rgb: [b.r / b.n, b.g / b.n, b.b / b.n] }; }).sort(function (p, q) { return q.n - p.n; }), out = [];
        arr.forEach(function (c) { if (out.length >= 2 || c.n < tot * 0.12 || (out.length && c.n < arr[0].n * 0.6)) return; if (out.some(function (o2) { var dr = o2.rgb[0] - c.rgb[0], dg = o2.rgb[1] - c.rgb[1], db = o2.rgb[2] - c.rgb[2]; return Math.sqrt(dr * dr + dg * dg + db * db) < 60; })) return; out.push(c); });
        return out.map(function (c) { return rgbHex(c.rgb); });
    }
    // ------------------------------------------------------------------ probes (look BEFORE changing anything)
    // What would this region select? -> share of the paint, where, and which existing zones it would take pixels from.
    function probeRegion(r, exceptZone) {
        r = r || {}; var W = paintDims()[0], H = paintDims()[1], pd = paintPixels(); if (!pd) return null;
        var tol = clamp(r.tolerance != null ? r.tolerance : 40, 6, 100), tg = (r.colors || []).map(function (h, n) { return isHex(h) ? { rgb: hexRgb(h), tol: (Array.isArray(r.tols) && r.tols[n] != null) ? clamp(r.tols[n], 3, 100) : tol } : null; }).filter(Boolean), ct = tg.length ? colourTest(tg) : null;
        var ctWide = tg.length ? colourTest(tg.map(function (t) { return { rgb: t.rgb, tol: t.tol + 12 }; })) : null, fringe = 0;          // WP6 2026-10-03
        var box = r.rect || (r.cells ? parseCells(r.cells) : null), layerUnion = null, layerMissing = false, imask = null;
        if (r.graphic && window.SpbGraphics) { var gq = window.SpbGraphics.maskFor(r.graphic); if (!gq) return { share_pct: 0, note: 'that graphic could not be drawn (unknown part or kind)' }; imask = gq.mask; }
        if (r.island) { var im = window.SpbProCar && window.SpbProCar.maskFor(r.island, r.portion, r.band); if (!im) return { share_pct: 0, note: 'that part is unknown' }; imask = im.mask; }
        if (r.element && window.SpbProElements) { var eq = window.SpbProElements.maskFor(r.element); if (!eq) return { share_pct: 0, note: 'the ' + String(r.element).split(':')[0] + ' have not been found on this paint (call describe_paint first)' }; imask = eq.mask; }
        if (r.layers && r.layers.length) {
            var ids = (Array.isArray(r.layers) ? r.layers : [r.layers]).map(findLayer).filter(Boolean).map(function (l) { return l.id; });
            if (ids.length) { try { var lu = unionRO({ sourceLayers: ids, sourceLayer: ids[0] }, W, H); layerUnion = lu && lu.union; layerMissing = !layerUnion; } catch (e) { layerMissing = true; } } else layerMissing = true;
        }
        if (r.exclude && r.exclude.length) { var exm = excludedUnion(r.exclude, W, H); if (exm) { var kp = new Uint8Array(W * H), kq; for (kq = 0; kq < kp.length; kq++) kp[kq] = (!exm[kq] && (!imask || imask[kq])) ? 255 : 0; imask = kp; } }
        if (!ct && !box && !layerUnion && !imask && !r.everything && !r.remaining) return { share_pct: 0, note: 'nothing selected' };
        if (layerMissing) return { share_pct: 0, note: 'that layer is hidden or has no pixels' };
        return withMemo(function () {
            var list = Zs(), claims = [];
            list.forEach(function (z, j) { if (z !== exceptZone) { var t = claimTest(list, j, W, H); if (t) claims.push({ z: z, j: j, t: t }); } });
            var d = pd.data, st = (r.element || ct) ? 4 : 16, n = 0, hits = 0, ix, iy, x0 = 1, y0 = 1, x1 = 0, y1 = 0, cells = {}, stolen = {}, owners = {};
            for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) {
                var o = (iy * W + ix) * 4; n++;
                if (d[o + 3] < 8) continue;
                var fx = ix / W, fy = iy / H, idx = iy * W + ix;
                if (box && (fx < box.x0 || fx >= box.x1 || fy < box.y0 || fy >= box.y1)) continue;
                if (ct && !ct(d[o], d[o + 1], d[o + 2])) {
                    if (ctWide && ctWide(d[o], d[o + 1], d[o + 2]) && (!layerUnion || layerUnion[idx] > 0) && (!imask || imask[idx] > 0)) {
                        var touch = false, nv, nx, ny; for (nv = 0; nv < 8 && !touch; nv++) { nx = ix + [1, -1, 0, 0, 2, -2, 0, 0][nv]; ny = iy + [0, 0, 1, -1, 0, 0, 2, -2][nv]; if (nx >= 0 && ny >= 0 && nx < W && ny < H) { var o3 = (ny * W + nx) * 4; if (ct(d[o3], d[o3 + 1], d[o3 + 2])) touch = true; } }
                        if (touch) fringe++;
                    }
                    continue;
                }
                if (layerUnion && !(layerUnion[idx] > 0)) continue;
                if (imask && !(imask[idx] > 0)) continue;
                hits++;
                if (fx < x0) x0 = fx; if (fy < y0) y0 = fy; if (fx > x1) x1 = fx; if (fy > y1) y1 = fy;
                var k = cellName(Math.min(7, Math.floor(fx * 8)), Math.min(7, Math.floor(fy * 8))); cells[k] = (cells[k] || 0) + 1;
                for (var q = 0; q < claims.length; q++) if (claims[q].t(d[o], d[o + 1], d[o + 2], idx)) { stolen[claims[q].z.name] = (stolen[claims[q].z.name] || 0) + 1; owners[claims[q].j] = (owners[claims[q].j] || 0) + 1; break; }
            }
            var per = n / 64, top = Object.keys(cells).filter(function (k) { return cells[k] > per * 0.06; }).sort(function (a, b) { return cells[b] - cells[a]; }).slice(0, 10);
            var bb = hits ? [Math.round(x0 * 100) / 100, Math.round(y0 * 100) / 100, Math.round(Math.min(1, x1 + st / W) * 100) / 100, Math.round(Math.min(1, y1 + st / H) * 100) / 100] : null;
            var out = { share_pct: hits ? Math.max(0.01, Math.round(hits / n * 1000) / 10) : 0, where: whereWords(bb), cells: top };          // a real but tiny selection (one glyph) must not round to "nothing"
            var sf = Object.keys(stolen).map(function (k) { return { zone: k, pct_of_region: Math.round(stolen[k] / Math.max(1, hits) * 100) }; }).filter(function (e) { return e.pct_of_region >= 10; }).sort(function (a, b) { return b.pct_of_region - a.pct_of_region; });
            if (sf.length) out.takes_pixels_from = sf.slice(0, 4);
            var ow = Object.keys(owners).map(function (k) { return { i: Number(k), pct: Math.round(owners[k] / Math.max(1, hits) * 1000) / 10 }; }); if (ow.length) Object.defineProperty(out, 'owners', { value: ow, enumerable: false });          // MCPSCEN: EVERY zone that wins pixels of this region now (by index; not sent to the model)
            if (ct) { out.covers_px = hits * st * st; out.tolerance = tg.length === 1 ? tg[0].tol : tg.map(function (t) { return t.tol; }); out.fringe_estimate = fringe * st * st; out.fringe_pct_of_region = hits ? Math.round(fringe / hits * 1000) / 10 : 0; }          // WP6: pixels just outside the tolerance = the halo that would remain
            if (!hits) out.note = 'selects nothing on the paint';
            return out;
        });
    }
    // MCPSCEN 2026-10-05 (Next Gen bookends scheme: the rocker pinstripe "selects nothing" because the car's rocker is its own "Rocker Panel" art layer): which
    // visible layers have pixels under a region mask, so an empty zone can say WHY it is empty.
    function layersUnder(mask) {
        if (!mask) return []; var W = paintDims()[0], H = paintDims()[1], st = 8, out = [], tot = 0, ix, iy;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) if (mask[iy * W + ix]) tot++;
        if (!tot) return [];
        (typeof _psdLayers !== 'undefined' ? _psdLayers : []).forEach(function (l) {
            if (!l || l.visible === false || /^(wire|mask|car[ _]?mandatory)$/i.test(String(l.name || ''))) return;
            var lu = null; try { lu = unionRO({ sourceLayers: [l.id], sourceLayer: l.id }, W, H); } catch (e) {}
            if (!lu || !lu.union) return; var m = lu.union, n = 0;
            for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) { var k = iy * W + ix; if (mask[k] && m[k] > 0) n++; }
            if (n / tot >= 0.05) out.push({ layer: l.name, pct: Math.round(n / tot * 100) });
        });
        return out.sort(function (x, y) { return y.pct - x.pct; });
    }
    // lane R3-EDIT 2026-10-07 H1b (sealed: "make the hood the same red as the logo" -> hood BLUE): the colours the paint shows where the named layers have pixels, most first [{hex, share_pct}]
    function layerColours(names, n) {
        var pd = paintPixels(); if (!pd) return []; var W = paintDims()[0], H = paintDims()[1], ids = []; if (pd.width !== W || pd.height !== H) return [];
        [].concat(names || []).forEach(function (nm) { var l = findLayer(nm); if (l && l.visible !== false && ids.indexOf(l.id) === -1) ids.push(l.id); }); if (!ids.length) return [];
        var lu = null; try { lu = unionRO({ sourceLayers: ids, sourceLayer: ids[0] }, W, H); } catch (e) {} if (!lu || !lu.union) return [];
        var m = lu.union, d = pd.data, bins = {}, tot = 0, x, y;
        for (y = 0; y < H; y += 2) for (x = 0; x < W; x += 2) { var i = y * W + x; if (!(m[i] > 0)) continue; var o = i * 4; if (d[o + 3] < 128) continue; tot++;
            var k = (d[o] >> 4) + ',' + (d[o + 1] >> 4) + ',' + (d[o + 2] >> 4), b = bins[k] || (bins[k] = { c: 0, r: 0, g: 0, b: 0 }); b.c++; b.r += d[o]; b.g += d[o + 1]; b.b += d[o + 2]; }
        var arr = Object.keys(bins).map(function (k) { var b = bins[k]; return { c: b.c, rgb: [b.r / b.c, b.g / b.c, b.b / b.c] }; }).sort(function (a, b) { return b.c - a.c; }), out = [];
        arr.forEach(function (e) { if (out.length >= (n || 8)) return; var hit = out.filter(function (o) { var dr = o.rgb[0] - e.rgb[0], dg = o.rgb[1] - e.rgb[1], db = o.rgb[2] - e.rgb[2]; return dr * dr + dg * dg + db * db < 1800; })[0]; if (hit) { hit.c += e.c; return; } out.push({ c: e.c, rgb: e.rgb }); });
        return out.filter(function (e) { return e.c >= Math.max(3, tot * 0.01); }).map(function (e) { return { hex: rgbHex(e.rgb), share_pct: Math.round(e.c / Math.max(1, tot) * 1000) / 10 }; });
    }
    function layerFootprint(name) {
        var l = findLayer(name); if (!l) return { error: 'no PSD layer named "' + name + '"' + layerNameHint(name) };
        var W = paintDims()[0], H = paintDims()[1], lu = null;
        try { lu = unionRO({ sourceLayers: [l.id], sourceLayer: l.id }, W, H); } catch (e) {}
        if (!lu || !lu.union) return { layer: l.name, note: l.visible === false ? 'the layer is hidden' : 'the layer has no visible pixels' };
        var m = lu.union, st = 16, n = 0, hits = 0, cells = {}, ix, iy, x0 = 1, y0 = 1, x1 = 0, y1 = 0;
        for (iy = 0; iy < H; iy += st) for (ix = 0; ix < W; ix += st) { n++; if (m[iy * W + ix] > 0) { hits++; var fx = ix / W, fy = iy / H; if (fx < x0) x0 = fx; if (fy < y0) y0 = fy; if (fx > x1) x1 = fx; if (fy > y1) y1 = fy; var k = cellName(Math.min(7, Math.floor(fx * 8)), Math.min(7, Math.floor(fy * 8))); cells[k] = (cells[k] || 0) + 1; } }
        var per = n / 64, top = Object.keys(cells).filter(function (k) { return cells[k] > per * 0.06; }).sort(function (a, b) { return cells[b] - cells[a]; }).slice(0, 12);
        var bb = hits ? [Math.round(x0 * 100) / 100, Math.round(y0 * 100) / 100, Math.round(Math.min(1, x1 + st / W) * 100) / 100, Math.round(Math.min(1, y1 + st / H) * 100) / 100] : null;
        return { layer: l.name, share_pct: Math.round(hits / n * 1000) / 10, where: whereWords(bb), cells: top };
    }
    // the buyer's LIVE render as a small JPEG data URL (or null)
    function previewImage(size) {
        try {
            var img = document.getElementById('livePreviewImg'); if (!img || !(img.naturalWidth > 32) || !img.complete) return null;
            var n = Math.max(384, Math.min(896, size || 640)), cv = document.createElement('canvas'); cv.width = cv.height = n;
            var cx = cv.getContext('2d'); cx.fillStyle = '#101018'; cx.fillRect(0, 0, n, n); cx.imageSmoothingQuality = 'high';
            var w = img.naturalWidth, h = img.naturalHeight, k = Math.min(n / w, n / h); cx.drawImage(img, (n - w * k) / 2, (n - h * k) / 2, w * k, h * k);
            return cv.toDataURL('image/jpeg', 0.78);
        } catch (e) { return null; }
    }
    // the spec-map preview beside the live preview (R=metal G=rough B=clearcoat shown as colour) as a small JPEG data URL
    function specPreviewImage(size) {
        try {
            var img = document.getElementById('livePreviewSpecImg'); if (!img || !(img.naturalWidth > 32) || !img.complete) return null;
            var n = Math.max(256, Math.min(640, size || 512)), cv = document.createElement('canvas'); cv.width = cv.height = n;
            var cx = cv.getContext('2d'); cx.fillStyle = '#000'; cx.fillRect(0, 0, n, n); var w = img.naturalWidth, h = img.naturalHeight, k = Math.min(n / w, n / h); cx.drawImage(img, (n - w * k) / 2, (n - h * k) / 2, w * k, h * k);
            return cv.toDataURL('image/jpeg', 0.8);
        } catch (e) { return null; }
    }
    // compact per-zone state for a model (only what matters; ~150 chars per zone)
    function zonesForModel() {
        return withMemo(function () {
            return Zs().map(function (z, i) {
                var d = describe(i), o = { i: i, id: z.id != null ? String(z.id) : undefined, name: d.name, covers: d.covers };
                if (d.muted) o.muted = true;
                var w = d.where; if (w) { o.share_pct = w.share_pct; o.visible_pct = w.visible_pct; if (w.cells && w.cells.length) o.cells = w.cells.slice(0, 8).join(','); if (w.blocked_by) o.blocked_by = w.blocked_by.map(function (b) { return b.zone + ' ' + b.pct_of_this_zone + '%'; }).join(', '); }
                try { if (!honestOff() && w && w.share_pct > 0 && w.visible_pct < w.share_pct * 0.85 && provOf(z)) { var hv = analyseZone(Zs(), i, 16); if (hv && hv.n >= 40) o.shows_pct_of_its_area = Math.round(hv.share * 100); } } catch (eHv) {}          // W3-HONEST 2026-10-09: how much of the zone's own area really shows (MCP reads this from get_zones)
                var look = []; if (d.base) look.push(d.base); if (d.special) look.push('special ' + d.special); look.push('colour ' + d.colour);
                if (d.pattern) look.push('pattern ' + d.pattern); if (d.spec_patterns) look.push('spec patterns ' + d.spec_patterns.join('; ')); if (d.second_base) look.push('overlay ' + d.second_base);
                if (d.intensity != null) look.push('intensity ' + d.intensity); if (d.base_strength_pct) look.push('base ' + d.base_strength_pct + '%'); if (d.spec_shift) look.push('spec shift ' + JSON.stringify(d.spec_shift));
                if (d.scale != null) look.push('scale ' + d.scale + (d.scale < 1 ? ' (texture crushed to ' + Math.round(d.scale * 100) + '%)' : '')); if (d.rotation) look.push('rotation ' + d.rotation); if (d.spec_strength_pct) look.push('spec ' + d.spec_strength_pct + '%'); if (d.hue) look.push('hue ' + d.hue); if (d.saturation) look.push('saturation ' + d.saturation); if (d.brightness) look.push('brightness ' + d.brightness);          // HELPER FIX PASS 8 2026-10-05: the model could not copy "crushed down" (scale) because the state never said it
                try { var zz = Zs()[i]; if (zz && zz.specScaleMode === 'independent' && zz.specScale != null) look.push('spec scale ' + zz.specScale); } catch (eSS) {}
                o.look = look.join(' | ');
                return o;
            });
        });
    }

    // ------------------------------------------------------------------ catalog search
    function searchList(list, q, limit, fields) {
        var ts = norm(q).split(' ').filter(function (t) { return t.length > 1; }), out = [];
        (list || []).forEach(function (p) {
            var name = norm(p.name), id = norm(p.id), desc = norm(p.desc || ''), cat = norm(p.category || ''), s = 0;
            ts.forEach(function (t) { if (name.indexOf(t) !== -1) s += 4; else if (id.indexOf(t) !== -1) s += 3; else if (cat.indexOf(t) !== -1) s += 2; else if (desc.indexOf(t) !== -1) s += 1; });
            if (s) out.push({ s: s, p: p });
        });
        out.sort(function (a, b) { return b.s - a.s; });
        return out.slice(0, limit || 8).map(function (x) { return { id: x.p.id, name: x.p.name, about: esc(x.p.desc || '').slice(0, 110), group: x.p.category || undefined }; });
    }
    function searchSpecPatterns(q, limit) { try { return searchList(SPEC_PATTERNS, q, limit); } catch (e) { return []; } }
    function searchPatterns(q, limit) { try { return searchList(PATTERNS, q, limit); } catch (e) { return []; } }
    function specGroups() { try { var g = {}; SPEC_PATTERNS.forEach(function (p) { g[p.category || 'Other'] = (g[p.category || 'Other'] || 0) + 1; }); return g; } catch (e) { return {}; } }

    // MCP-SPEED 2026-10-09 (owner live demo: every MCP preview / edit took 61-104 s and the Claude client timed out at ~60 s; a preview with NOTHING changed took 61 s).
    // Cause: a browser tab hidden > 5 min gets "intensive wake-up throttling" — chained main-thread timers (whenSettled's 400 ms poll) fire once a MINUTE. Electron sets
    // backgroundThrottling:false, so only the browser (Edge dev) path was hit. later(fn, ms) = setTimeout, but while the tab is hidden in a plain browser the delay runs
    // in a tiny Web Worker (worker timers are not throttled) and fires back as a message. Any worker failure falls back to setTimeout for good.
    var _tw = null, _twBroken = false, _twSeq = 0, _twWait = {};
    function later(fn, ms) {
        var useWorker = !_twBroken && typeof document !== 'undefined' && document.hidden && typeof Worker !== 'undefined' && !/Electron/i.test(navigator.userAgent || '');
        if (useWorker) {
            try {
                if (!_tw) {
                    _tw = new Worker(URL.createObjectURL(new Blob(['onmessage=function(e){setTimeout(function(){postMessage(e.data.id)},e.data.ms)}'], { type: 'text/javascript' })));
                    _tw.onmessage = function (e) { var f = _twWait[e.data]; delete _twWait[e.data]; if (f) f(); };
                    _tw.onerror = function () { _twBroken = true; var w = _twWait; _twWait = {}; Object.keys(w).forEach(function (k) { setTimeout(w[k], 0); }); };
                }
                var id = ++_twSeq; _twWait[id] = fn; _tw.postMessage({ id: id, ms: ms || 0 }); return;
            } catch (e) { _twBroken = true; }
        }
        setTimeout(fn, ms);
    }

    // Resolve when Pro's live preview has caught up with the zones (or after timeoutMs). Used so a look/self-check never judges a stale image.
    function whenSettled(timeoutMs) {
        var t0 = Date.now(), limit = timeoutMs || 45000, calm = 0;
        return new Promise(function (resolve) {
            (function poll() {
                var badge = document.getElementById('previewStatus'), st = badge ? (badge.dataset.state || '') : '', synced = false;
                try { synced = (typeof lastPreviewZoneHash !== 'undefined' && typeof getZoneConfigHash === 'function' && lastPreviewZoneHash && lastPreviewZoneHash === getZoneConfigHash()); } catch (e) {}
                var busy = st === 'stale' || st === 'rendering' || st === 'retrying' || st === 'loading' || st === 'pending';
                calm = (!busy && (synced || !badge)) ? calm + 1 : 0;
                if (calm >= 3) return resolve(true);
                if (Date.now() - t0 > limit) return resolve(false);
                later(poll, 400);
            })();
        });
    }
    window.SpbProZone = { positionOf: function (i, base) { var z = Zs()[i]; if (!z) return null; return base ? { x: Math.round((z.baseOffsetX != null ? z.baseOffsetX : 0.5) * 100), y: Math.round((z.baseOffsetY != null ? z.baseOffsetY : 0.5) * 100) } : { x: Math.round((z.patternOffsetX != null ? z.patternOffsetX : 0.5) * 100), y: Math.round((z.patternOffsetY != null ? z.patternOffsetY : 0.5) * 100), fit: z.patternPlacement === 'fit', op100: (z.patternOpacity == null ? 100 : Number(z.patternOpacity)) >= 100 }; }, patternZoneFor: patternZoneFor, visibleShare: visibleShare, putOnTop: putOnTop, accentShare: accentShareFor, accentMask: accentMask, layerColours: layerColours, lookLine: lookLine, zoneRef: zoneRef, zoneName: zoneName, visibleIdx: visibleIdx, layersUnder: layersUnder, mcpFamilyMaskForPixels: mcpFamilyMaskForPixels, bodyColours: bodyColours, findLayer: findLayer, specPreviewImage: specPreviewImage, probeRegion: probeRegion, layerFootprint: layerFootprint, previewImage: previewImage, zonesForModel: zonesForModel, whenSettled: whenSettled, later: later, catchAll: catchAll, SCHEMA: SCHEMA, describe: describe, describeAll: describeAll, footprint: footprint, paintColours: paintColours, edgeFit: edgeFit, paintMapImage: paintMapImage, validate: validate, edit: edit, add: add, duplicate: duplicate, place: place, batch: batch, searchSpecPatterns: searchSpecPatterns, searchPatterns: searchPatterns, specGroups: specGroups, parseCells: parseCells, quiet: quiet, withMemo: withMemo /* [SPB-PERF2 2026-10-10] one claim-test memo scope across a whole helper-environment build */ };
})();
