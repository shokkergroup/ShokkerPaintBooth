/* SPB PRO FLAMES (2026-10-05, owner decision "Build real flame licks" before the beta): REAL flame-lick GEOMETRY placed on a named car PART.
   The Flames shelf (20 base finishes flame_*) are fire TEXTURES - blobs, clouds, rings - and a base finish cannot know which part it is on or where the
   front is. A flame job is a GRAPHIC: tapered tongues with curved tips that grow out of a solid base band at the FRONT of the part and reach back,
   optionally outlined (pinstripe) in a second colour. It is drawn in PART space by js/spb-pro-graphics.js (u = front -> rear, v = roof-line -> rocker,
   from the car library's front / up), so the same job lands correctly on the hood, the left side, the right side (180 deg on the sheet), the roof.
   Each colour role (fill, outline, true-fire layers) becomes an ordinary ZONE (region.graphic) through SpbProZone.batch: one undo step, its own finish
   (= its own SPEC: candy flames read glossy on a satin body in the sim), numbers / sponsors / logos kept on top (region.exclude), any car.
   Styles: hotrod (yellow -> orange -> red fade along the car, outlined), tribal (sharp hooked blades, one colour), ghost (body hue, low contrast, pearl
   spec), truefire (three nested layers of wispy licks, red / orange / yellow-white). Full design + measured results: docs/handoff_reports/FLAMES.md.

   API (window.SpbFlames) - the helper / MCP / encyclopedia call these; ES5, no state kept between calls:
     SpbFlames.STYLES                       -> { hotrod|tribal|ghost|truefire: { about, defaults } }
     SpbFlames.check(opts)                  -> error string | null
     SpbFlames.plan(opts)                   -> { ok, ops: [SpbProZone.batch ops], zones: [names], notes: [..] }   (no side effects)
     SpbFlames.apply(opts)                  -> { ok, applied: [..], warnings: [..], zones: [names], removed: [names] }  (ONE undo step, label opts.label || "Flames")
                                               ok:false when a part is unknown on this car (nothing landed) - say so, offer the car-map step
   opts: { part: 'hood' | 'left side' | ['left side','right side'] | 'sides' (default),  style: 'hotrod' (default) | 'tribal' | 'ghost' | 'truefire',
           colours: ['#rrggbb', ...]  (hotrod: fade stops front->tips; tribal: the one colour; ghost: the flame colour (default = body colour shifted);
                                       truefire: [outer, mid, core]),
           outline: '#rrggbb' | false  (hotrod default #1f4dff; others default none),  outline_w: px on a 2048 sheet (default 7),
           licks: 3..16 (count across the part),  length: 0.2..1 (how far back the longest lick reaches, fraction of the part length),
           base: 0..0.5 (depth of the solid band at the front),  scale: 0.5..2 (bigger = fewer, fatter licks),  curl: 0..2 (tip hook),
           band: [v0, v1] (0..1 across the part; default 0.06..0.94),  seed: integer (another variation),
           finish: 'base::<id>' for the flames (default per style),  keep_decals: true (default: numbers / sponsors / logos stay on top),
           replace: true (default: flames already on those parts are taken off in the same undo step), uv: true (clip to the PSD Mask layer's real panel edges),
           bleed: px past the coarse part outline (default 8), label: undo / history label,
           layers: 1..3 (truefire only, default 1 = ONE zone: the fire gradient colours nested tongues separated by thin body-colour channels; 2 = outer + inner zone;
                   3 = outer / mid / core zones, the pre-POLISH look, slowest),  gap: px of the truefire layers:1 channel (default 4) }
   Render budget (POLISH 1, 2026-10-05): every zone costs ~0.6 s of server time at 2048 (solid / gradient base colour forces the full-canvas paint path), so
   one colour role = one zone across ALL parts; fades are one sheet-percent gradient zone. Hood + both sides measured on 59879: hot rod (fill + outline) ~2.0 s,
   tribal / ghost / true fire ~1.2-1.4 s (docs/handoff_reports/FLAMES.md ## POLISH 1).
   Graphic kind 'flames' (also usable directly as region.graphic {kind:'flames', part, colours:[k0,k1,k2,k3], style, ...}):
     colour index 0 = fill (truefire: outer layer), 1 = outline ring (outside the flame, width outline_w), 2 = truefire mid layer, 3 = truefire core. */
(function () {
    'use strict';
    var W = window;
    function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function hexOk(h) { return /^#[0-9a-f]{6}$/i.test(String(h || '')); }
    function hexRgb(h) { return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)]; }
    function rgbHex(r) { return '#' + r.map(function (v) { return ('0' + Math.round(clamp(v, 0, 255)).toString(16)).slice(-2); }).join(''); }
    function rng(seed) { var a = (num(seed, 1) * 2654435761) >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; var t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function smooth(a, b, t) { var x = clamp((t - a) / (b - a), 0, 1); return x * x * (3 - 2 * x); }

    // ------------------------------------------------------------------ styles (look + default colours / finishes). Finishes are real BASE ids.
    var STYLES = {
        hotrod: {
            about: 'classic hot-rod flames: a solid front that breaks into long licks with hooked tips, yellow -> orange -> red along the car, thin pinstripe outline',
            d: { licks: 7, length: 0.62, base: 0.12, curl: 1.0, wave: 0.30, freq: 1.0, taper: 0.95, belly: 0.30, width: 1.0, colours: ['#ffd400', '#ff8a00', '#e3260f'], outline: '#1f4dff', outline_w: 7, finish: 'base::f_candy', outline_finish: 'base::wet_look' }
        },
        tribal: {
            about: 'tribal flames: separate sickle blades - thin root, thick shoulder, a long taper to a crisp hooked point, 1-2 barbs on the outer edge - with body colour between every blade; one solid colour',
            d: { licks: 5, length: 0.66, base: 0.10, curl: 1.9, wave: 0.12, freq: 0.8, taper: 1.3, belly: 0.10, width: 1.05, barbs: 1, colours: null, outline: false, outline_w: 6, finish: 'base::wet_look', outline_finish: 'base::wet_look' }
        },
        ghost: {
            about: 'ghost flames: the hot-rod shape in the body\'s own hue, a few shades off, pearl spec - shows up in the light, quiet in the shade',
            d: { licks: 8, length: 0.70, base: 0.10, curl: 1.1, wave: 0.32, freq: 1.1, taper: 1.0, belly: 0.25, width: 0.9, colours: null, outline: false, outline_w: 4, finish: 'base::f_pearl', outline_finish: 'base::f_pearl' }
        },
        truefire: {
            about: 'true fire: wispy, forking licks with nested inner tongues - yellow-white at the front through orange to deep red tips (one zone; layers:2/3 for separate layer zones)',
            d: { licks: 10, length: 0.74, base: 0.08, curl: 0.8, wave: 0.45, freq: 1.4, taper: 1.2, belly: 0.25, width: 1.0, colours: ['#c41300', '#ff6a00', '#ffe27a'], outline: false, outline_w: 5, finish: 'base::f_candy', outline_finish: 'base::wet_look' }
        }
    };
    function styleOf(o) { var s = String((o && o.style) || 'hotrod').toLowerCase().replace(/[^a-z]/g, ''); if (s === 'hotrodflames' || s === 'classic' || s === 'traditional') s = 'hotrod'; if (s === 'realfire' || s === 'realistic' || s === 'fire') s = 'truefire'; return STYLES[s] ? s : null; }
    function P(o, k) { var st = STYLES[styleOf(o) || 'hotrod'].d; return o && o[k] != null ? o[k] : st[k]; }

    // ------------------------------------------------------------------ one lick: integrate a heading along the centre line, taper the width, hook the tip.
    // returns a closed polygon [[x,y],...] in part-local pixels (x along the car front -> rear, y across)
    function lick(x0, y0, len, hw0, th0, o) {
        var N = 64, ds = len / N, x = x0, y = y0, i, cl = [], left = [], right = [];
        for (i = 0; i <= N; i++) {
            var t = i / N, hook = smooth(o.cs, 1, t);
            var a = th0 + o.wave * Math.sin(6.2832 * o.freq * t + o.ph) * (0.25 + 0.75 * t) + o.curl * hook * hook;
            if (i) { x += Math.cos(a) * ds; y += Math.sin(a) * ds; }
            var w = o.prof ? hw0 * o.prof(t) : hw0 * Math.pow(1 - t, o.taper) * (1 + o.belly * Math.sin(Math.PI * Math.min(1, t * 1.7)));
            cl.push([x, y, a, w]);
        }
        // POLISH 1 (2026-10-05, tribal blades): o.asym > 0 makes the blade a SICKLE - the convex (outer) side of the hook bulges, the concave side runs flatter.
        // Heading grows with +curl = turns toward +normal, so the convex side is -normal ("right") when curl > 0.
        var s = o.asym ? (o.curl > 0 ? 1 : (o.curl < 0 ? -1 : 0)) : 0, kl = 1 - (o.asym || 0) * s, kr = 1 + (o.asym || 0) * s;
        for (i = 0; i <= N; i++) { var c = cl[i], nx = -Math.sin(c[2]), ny = Math.cos(c[2]); left.push([c[0] + nx * c[3] * kl, c[1] + ny * c[3] * kl]); right.push([c[0] - nx * c[3] * kr, c[1] - ny * c[3] * kr]); }
        if (o.noCap) return { poly: left.concat(right.reverse()), cl: cl };
        // round the root a little behind its start so it melts into the base band
        var r0 = cl[0], back = [];
        for (i = 1; i < 8; i++) { var aa = r0[2] + Math.PI / 2 + Math.PI * i / 8; back.push([r0[0] + Math.cos(aa) * r0[3], r0[1] + Math.sin(aa) * r0[3]]); }
        return { poly: left.concat(right.reverse(), back), cl: cl };
    }

    // ------------------------------------------------------------------ the whole job for one part: { fill:[polys], mid:[polys], core:[polys] }
    // the solid band at the front, trailing edge a convex arc (its corners never stick out between the licks); x from beyond the front edge
    // 2026-10-05 second pass (1:1 hood: the band's flat trailing edge showed as a straight vertical cut in every gap between two licks): the trailing edge is now
    // SCALLOPED, a rounded arc behind each lick root that falls back to a shallow floor in the gaps, so each crotch between licks is a curved U, never a straight cut
    // POLISH 1: sharp = true (tribal) makes each crotch a pointed V (a triangle behind each root) instead of a rounded U
    function bandPoly(depth, yTop, yBot, roots, sharp) {
        var bp = [[-60, yTop], [-60, yBot]], k, K = 160, floor = depth * (sharp ? 0.15 : 0.35);
        for (k = 0; k <= K; k++) {
            var t = k / K, y = yBot - (yBot - yTop) * t, x = roots && roots.length ? floor : depth * (0.9 + 0.1 * Math.sin(Math.PI * t));
            if (roots) roots.forEach(function (r) { var u = (y - r.y) / (r.hw * 1.6); if (u > -1 && u < 1) x = Math.max(x, r.x + r.hw * 1.2 * (sharp ? 1 - Math.abs(u) : Math.sqrt(1 - u * u))); });
            bp.push([x, y]);
        }
        return bp;
    }
    function geometry(F, p) {
        if (styleOf(p) === 'tribal') return tribalGeometry(F, p);
        var sty = styleOf(p) || 'hotrod', R = rng(num(p.seed, 7)), L = F.L, H = F.H, asp = L / Math.max(1, H);
        var band = Array.isArray(p.band) && p.band.length === 2 ? p.band : [0.06, 0.94];
        var v0 = clamp(num(band[0], 0.06), 0, 1) * H, v1 = clamp(num(band[1], 0.94), 0, 1) * H; if (v1 - v0 < 8) { v0 = 0.06 * H; v1 = 0.94 * H; }
        // a long thin panel (a side: ~4x longer than tall) wants fewer, fatter licks; a squat one (hood, roof) wants them to reach further back
        var nDef = num(P(p, 'licks'), 7); if (p.licks == null && asp > 2.4) nDef = Math.max(3, Math.round(nDef * (sty !== 'tribal' ? 0.7 : 0.86)));
        var lenDef = num(P(p, 'length'), 0.62); if (p.length == null && asp < 1.6) lenDef = Math.min(0.9, lenDef * 1.22); if (p.length == null && asp > 2.4) lenDef = Math.min(0.9, lenDef * 1.12);
        var scale = clamp(num(P(p, 'scale'), 1), 0.4, 2.5), n = clamp(Math.round(nDef / scale), 2, 24);
        var reach = clamp(lenDef, 0.15, 1) * L, baseL = clamp(num(P(p, 'base'), 0.1), 0, 0.6) * L;
        // 2026-10-05 second pass (1:1 left side, every style: the front read as a solid slab ~27% of the panel with a few hairs off its top): on a long panel the band is
        // shorter and the licks part sooner (thinner roots, less belly), so the side reads as licks, not as a painted block
        var longP = asp > 2.4; if (longP && p.base == null) baseL *= ((sty === 'hotrod' || sty === 'ghost') ? 0.35 : 0.55);
        // POLISH 1 (2026-10-05, orchestrator 1:1 on sides_v6: hot rod / ghost sides were a solid block over the front ~35% with long thin tentacles behind it):
        // on a long panel a flowing job is now sized in LICK SPACINGS, like the hood (the reference look): the longest lick reaches ~7.5 spacings past the base
        // (~40% of a side), 5 licks (hood: 7), widths / hooks / belly exactly as on the hood: fat bodies, crotches open right behind a base of ~7% of the panel.
        var flowLong = longP && (sty === 'hotrod' || sty === 'ghost' || sty === 'truefire');      // true fire joined after its 1:1 side read as crossed tentacles
        var curl = clamp(num(P(p, 'curl'), 1), 0, 2.5), sp = (v1 - v0) / n, wmul = num(P(p, 'width'), 1);
        if (flowLong && p.length == null) reach = Math.min(reach, baseL + (sty === 'truefire' ? 9.5 : 7.5) * sp);      // true fire: a bigger blaze (~50% of a side)
        var o0 = { wave: num(P(p, 'wave'), 0.3), freq: num(P(p, 'freq'), 1), taper: num(P(p, 'taper'), 1), belly: num(P(p, 'belly'), 0.3) };
        if (longP && !flowLong) o0.belly *= 0.45;
        if (flowLong && p.belly == null) o0.belly = 0.45;          // narrow root, fat body: the crotch opens right behind the base, the body swells, then tapers to the hook
        var out = { fill: [], mid: [], core: [] }, licks = [], i, yTop = 1e9, yBot = -1e9;
        var lens = [], ph0 = R() * 6.2832, phj = sty === 'truefire' ? 1.8 : 0.7;
        for (i = 0; i < n; i++) lens.push(0.55 + 0.45 * R());
        // a classic job alternates long and short licks; the longest sit in the middle of the band
        for (i = 0; i < n; i++) { var mid = 1 - Math.abs((i + 0.5) / n - 0.5) * 0.7; lens[i] = clamp(lens[i] * (i % 2 ? 0.74 : 1) * mid / 0.9, 0.32, 1); }
        for (i = 0; i < n; i++) {
            var y = v0 + sp * (i + 0.5) + (R() - 0.5) * sp * 0.3, x = baseL * ((i === 0 || i === n - 1) ? 0.82 + 0.1 * R() : 0.4 + 0.4 * R()), len = Math.max(baseL * 0.5 + 24, reach * lens[i] - x * 0.3);
            var side = (i % 2 ? 1 : -1) * (R() < 0.2 ? -1 : 1), flip = R();
            // a long panel with LONG licks (true fire): the hooks all sweep the same way (up, toward the roof-line) so neighbours nest instead of crossing (measured 2026-10-05:
            // a lone down-hook crossed its neighbour). Hot rod / ghost sides now use hood-length licks (POLISH 1) and alternate their hooks like the hood.
            if (asp > 2.4 && !flowLong) side = -1;
            if (flowLong) side = (i + 0.5) < n / 2 ? -1 : 1;          // POLISH 1: a fan - upper half hooks up, lower half hooks down, so no hook closes an 'eye' over a neighbour
            // 2026-10-05 second pass (1:1 left side: big hooks swept up across two neighbours into a tangle): long licks on a long panel curl less
            var lc = asp > 2.4 && !flowLong ? 0.85 : 1;
            var th = (R() - 0.5) * 0.16 + (y < (v0 + v1) / 2 ? 0.04 : -0.04);
            // width follows the lick's own length (a fat body that tapers to a hooked point), never thinner than the spacing needs to close the mass
            var hw = Math.max(sp * (flowLong ? 0.42 : (longP ? 0.5 : 0.56)), len * (sty === 'truefire' ? 0.05 : 0.06)) * wmul * (0.88 + 0.24 * R());
            hw = Math.min(hw, sp * 0.82);
            // keep the sideways swing of a long lick inside about half a spacing so neighbours flow together instead of crossing
            var amax = 0.55 * sp * 6.2832 * o0.freq / Math.max(1, len) * 1.6;
            var o = { wave: Math.min(o0.wave * (0.7 + 0.6 * R()), Math.max(0.08, amax)), freq: o0.freq * (0.8 + 0.4 * R()), ph: ph0 + (R() - 0.5) * phj, curl: side * curl * lc * (0.75 + 0.5 * R()), cs: 0.5 + 0.15 * R(), taper: o0.taper, belly: o0.belly };
            licks.push({ x: x, y: y, len: len, hw: hw, th: th, o: o, side: side });
            yTop = Math.min(yTop, y - hw * 1.02); yBot = Math.max(yBot, y + hw * 1.02);
        }
        yTop = Math.max(yTop, v0 - sp * 0.5); yBot = Math.min(yBot, v1 + sp * 0.5);
        if (baseL > 2) out.fill.push(bandPoly(baseL, yTop, yBot, licks));
        var midR = [], coreR = [];
        licks.forEach(function (q) {
            var lk = lick(q.x, q.y, q.len, q.hw, q.th, q.o), b;
            out.fill.push(lk.poly);
            if (sty === 'truefire') {          // wisps: thin forks peeling off each lick; then the two inner layers (shorter, thinner, own phase)
                var nf = R() < 0.7 ? (R() < 0.4 ? 2 : 1) : 0, f;
                for (f = 0; f < nf; f++) { var tf = 0.3 + 0.35 * R(), cf = lk.cl[Math.round(tf * (lk.cl.length - 1))], sf = R() < 0.5 ? 1 : -1; out.fill.push(lick(cf[0], cf[1], q.len * (0.25 + 0.25 * R()), cf[3] * 0.7, cf[2] + sf * 0.22, { wave: 0.5, freq: 1.6 + R(), ph: R() * 6.28, curl: sf * 1.0, cs: 0.45, taper: 1.35, belly: 0.15 }).poly); }
                var om = { wave: q.o.wave * 1.1, freq: q.o.freq * 1.15, ph: q.o.ph + 1.3, curl: q.o.curl * 0.8, cs: 0.55, taper: 1.2, belly: 0.3 };
                var my = q.y + (R() - 0.5) * sp * 0.2; midR.push({ x: q.x * 0.8, y: my, hw: q.hw * 0.72 });
                out.mid.push(lick(q.x * 0.8, my, q.len * (0.58 + 0.12 * R()), q.hw * 0.72, q.th, om).poly);
                var oc = { wave: q.o.wave * 0.9, freq: q.o.freq * 1.3, ph: q.o.ph + 2.6, curl: q.o.curl * 0.6, cs: 0.6, taper: 1.1, belly: 0.3 };
                var cy = q.y + (R() - 0.5) * sp * 0.15; coreR.push({ x: q.x * 0.5, y: cy, hw: q.hw * 0.5 });
                out.core.push(lick(q.x * 0.5, cy, q.len * (0.3 + 0.1 * R()), q.hw * 0.5, q.th, oc).poly);
            }
        });
        if (sty === 'truefire' && baseL > 2) {
            var hh = (yBot - yTop);
            out.mid.push(bandPoly(baseL * 0.8, yTop + hh * 0.04, yBot - hh * 0.04, midR));
            out.core.push(bandPoly(baseL * 0.38, yTop + hh * 0.1, yBot - hh * 0.1, coreR));
        }
        return out;
    }
    // ------------------------------------------------------------------ TRIBAL (POLISH 1, 2026-10-05). Orchestrator at 1:1 (v7_check / hoods_v5 column 2): the hood tribal was a
    // blobby mass with little hooks. Tribal = separate SICKLE BLADES: thin at the root, thickest about a quarter of the way out, then a long taper to a crisp
    // point that hooks over; the convex side bulges (asym) and carries 1-2 BARBS (short sharp thorns leaning back toward the tip). Blades are ~0.6 spacing
    // wide at most, so a channel of body colour runs between every pair; the front is a thin band whose trailing edge is a row of pointed V crotches.
    function tribalGeometry(F, p) {
        var R = rng(num(p.seed, 7)), L = F.L, H = F.H, asp = L / Math.max(1, H), longP = asp > 2.4;
        var band = Array.isArray(p.band) && p.band.length === 2 ? p.band : [0.06, 0.94];
        var v0 = clamp(num(band[0], 0.06), 0, 1) * H, v1 = clamp(num(band[1], 0.94), 0, 1) * H; if (v1 - v0 < 8) { v0 = 0.06 * H; v1 = 0.94 * H; }
        var scale = clamp(num(P(p, 'scale'), 1), 0.4, 2.5), n = clamp(Math.round(num(P(p, 'licks'), 5) / scale), 2, 24), sp = (v1 - v0) / n;
        var curl = clamp(num(P(p, 'curl'), 1.9), 0, 2.5), wmul = num(P(p, 'width'), 1);
        var baseL = p.base == null ? 0 : clamp(num(p.base, 0), 0, 0.6) * L;          // no band by default: the thick blade roots make the front, V notches between them
        var reach = clamp(num(P(p, 'length'), 0.66), 0.15, 1) * L * (asp < 1.6 ? 1.15 : 1);
        if (p.length == null) reach = Math.min(reach, baseL + (longP ? 5.2 : 3.9) * sp);
        var x0 = -sp * 0.15;
        var out = { fill: [], mid: [], core: [] }, roots = [], i, yTop = 1e9, yBot = -1e9, mid = (v0 + v1) / 2, blades = [];
        function blade(t) { return (0.5 + 0.5 * smooth(0, 0.22, t)) * Math.pow(1 - t, 1.45) * 1.3; }        // thin root -> thickest ~1/4 out -> fast taper -> needle point (a blade, not a strap)
        function thorn(t) { return Math.pow(1 - t, 1.15); }
        for (i = 0; i < n; i++) {
            var y = v0 + sp * (i + 0.5) + (R() - 0.5) * sp * 0.16, x = x0 + baseL * 0.3 * R();
            var len = Math.max(baseL + 2.4 * sp, reach * (i % 2 ? 0.72 + 0.12 * R() : 0.9 + 0.1 * R())) - x;
            // hooks: alternate on a squat part; on a long side all sweep up toward the roof-line so they nest (a down-hook crossed its neighbour at 1:1)
            var side = longP ? -1 : (i % 2 ? 1 : -1);
            var th = (y - mid) / Math.max(1, v1 - v0) * 0.22 + (R() - 0.5) * 0.08;      // a slight fan: outer blades lean outward
            var hw = sp * 0.31 * wmul * (0.92 + 0.16 * R());
            var o = { wave: 0.05 + 0.04 * R(), freq: 0.6, ph: R() * 6.2832, curl: side * curl * 0.5 * (0.85 + 0.3 * R()), cs: 0.25 + 0.1 * R(), prof: blade, asym: 0.3, noCap: true };
            blades.push({ x: x, y: y, len: len, hw: hw, th: th, o: o, side: side });
            roots.push({ x: x, y: y, hw: hw * 0.9 });
            yTop = Math.min(yTop, y - hw * 1.1); yBot = Math.max(yBot, y + hw * 1.1);
        }
        yTop = Math.max(yTop, v0 - sp * 0.3); yBot = Math.min(yBot, v1 + sp * 0.3);
        if (baseL > 2) out.fill.push(bandPoly(baseL, yTop, yBot, roots, true));
        blades.forEach(function (q) {
            var lk = lick(q.x, q.y, q.len, q.hw, q.th, q.o), s = q.side, nb = clamp(Math.round(num(P(p, 'barbs'), 1) + (R() < 0.55 ? 1 : 0)), 0, 3), b;
            out.fill.push(lk.poly);
            for (b = 0; b < nb; b++) {          // thorns on the CONVEX side (-normal * side), leaning out then hooking back toward the blade's tip
                var tb = 0.32 + 0.18 * b + 0.06 * R(), c = lk.cl[Math.min(lk.cl.length - 1, Math.round(tb * (lk.cl.length - 1)))], wv = c[3] * 1.35;
                var bx = c[0] + Math.sin(c[2]) * wv * 0.4 * s, by = c[1] - Math.cos(c[2]) * wv * 0.4 * s;
                out.fill.push(lick(bx, by, q.len * (0.22 + 0.05 * R()) * (b ? 0.8 : 1), c[3] * 0.85, c[2] - s * (0.62 + 0.15 * R()), { wave: 0, freq: 0, ph: 0, curl: s * 0.45, cs: 0.3, prof: thorn, noCap: true }).poly);
            }
        });
        return out;
    }
    function path(c, polys) { c.beginPath(); polys.forEach(function (pl) { c.moveTo(pl[0][0], pl[0][1]); for (var i = 1; i < pl.length; i++) c.lineTo(pl[i][0], pl[i][1]); c.closePath(); }); }
    function fillPolys(c, polys, col) { c.fillStyle = col; polys.forEach(function (pl) { path(c, [pl]); c.fill(); }); }

    var KIND = {
        about: 'real flame licks (hot rod / tribal / ghost / true fire): a solid band at the FRONT of the part, tapered licks with hooked tips reaching back; colour 0 = flames, colour 1 = outline ring',
        params: 'style hotrod|tribal|ghost|truefire; licks count; length 0.2..1 of the part; base 0..0.5 solid front band; curl 0..2; scale; band [v0,v1]; outline_w px; seed. colours: [flames, outline, (truefire) mid, core]',
        draw: function (c, F, p) {
            var g = geometry(F, p), pick = arguments[3], ow = clamp(num(p.outline_w, 7), 1, 40);
            var cFill = pick(0), cOut = pick(1), cMid = pick(2), cCore = pick(3);
            if (cOut) {                        // the ring OUTSIDE the union of the flames: stroke every lick, then cut the union back out
                c.save(); c.lineJoin = 'round'; c.lineCap = 'round'; c.lineWidth = ow * 2; c.strokeStyle = cOut;
                g.fill.forEach(function (pl) { path(c, [pl]); c.stroke(); });
                c.globalCompositeOperation = 'destination-out'; fillPolys(c, g.fill, '#000'); c.restore();
            }
            if (cFill) fillPolys(c, g.fill, cFill);
            // POLISH 1, true fire in ONE zone (layers:1): the mid tongues stay readable as nested flames - a thin channel of body colour (gap px) is cut
            // around each mid tongue and the tongue refilled, so the fire gradient (yellow-white front -> orange -> red -> deep red tips) colours three nested shapes
            if (p.fire_contour && cFill) [g.mid].forEach(function (ly) {
                ly = ly.filter(function (pl) { return pl[0][0] !== -60; });      // tongues only: a channel along the scalloped band edge read as scribble at 1:1
                if (!ly.length) return; var gap = clamp(num(p.gap, 4), 1, 30);
                c.save(); c.lineJoin = 'round'; c.lineWidth = gap * 2; c.globalCompositeOperation = 'destination-out'; c.strokeStyle = '#000';
                ly.forEach(function (pl) { path(c, [pl]); c.stroke(); }); c.restore(); fillPolys(c, ly, cFill);
                fillPolys(c, g.mid.filter(function (pl) { return pl[0][0] === -60; }), cFill);   // re-close the channels inside the front band: tongues open out of the solid front
            });
            if (cMid) fillPolys(c, g.mid, cMid);
            if (cCore) fillPolys(c, g.core, cCore);
            else if (p.core_in_mid && cMid) fillPolys(c, g.core, cMid);      // POLISH 1: true fire's core shares the inner zone (one zone less to render)
        }
    };

    // ------------------------------------------------------------------ the sheet mask of a flames graphic. Same contract as SpbGraphics.maskFor, one difference:
    // the part mask that clips the flames is GROWN by `bleed` px (default 8). The car map's part mask is a 256 grid blown up to 2048, so clipping a crisp flame
    // with it left an 8 px staircase along every panel edge and wheel arch (seen at 1:1 on the owner's ARCA, 2026-10-05). Grown, the flame runs a few px past
    // the UV edge (invisible in the sim, the same bleed SpbProCar.paintableMask(true) uses) and the real body edge does the cutting.
    var _cv = null;
    function canvas(Wd, Hd) { if (!_cv || _cv.width !== Wd || _cv.height !== Hd) { _cv = document.createElement('canvas'); _cv.width = Wd; _cv.height = Hd; } return _cv; }
    // 2026-10-05 second pass (1:1 contact sheet: the grown clip still showed the staircase wherever a solid base band met the panel edge): the clip is now SOFTENED,
    // a (2r+1)^2 box blur of the part mask thresholded so a straight edge moves out by `bleed` px and the 8 px stairs round off into a smooth line.
    function soften(m, Wd, x0, y0, x1, y1, bleed) {
        var r = Math.max(4, Math.round(bleed * 1.5)), n = 2 * r + 1, thr = Math.max(1, Math.round(Math.max(0.05, (r + 1 - bleed) / n) * n * n));
        var w = x1 - x0, h = y1 - y0, hz = new Uint16Array(w * h), out = new Uint8Array(w * h), row = new Int32Array(w + 1), col = new Int32Array(h + 1), x, y;
        for (y = 0; y < h; y++) { row[0] = 0; for (x = 0; x < w; x++) row[x + 1] = row[x] + (m[(y0 + y) * Wd + x0 + x] ? 1 : 0); for (x = 0; x < w; x++) hz[y * w + x] = row[Math.min(w, x + r + 1)] - row[Math.max(0, x - r)]; }
        for (x = 0; x < w; x++) { col[0] = 0; for (y = 0; y < h; y++) col[y + 1] = col[y] + hz[y * w + x]; for (y = 0; y < h; y++) if (col[Math.min(h, y + r + 1)] - col[Math.max(0, y - r)] >= thr) out[y * w + x] = 1; }
        return out;
    }
    // the car's real panel edges at FULL resolution, read from the PSD's template Mask layer (opaque = not paintable; drawn the other way round when mostly
    // transparent, the same reading SpbProCar uses at 256 grid). null when there is no usable Mask layer (flat paints): then the softened clip alone cuts.
    var _uv = { key: null, m: null };
    function uvMask(Wd, Hd) {
        var ls = []; try { ls = (typeof _psdLayers !== 'undefined' && _psdLayers) || []; } catch (e) { ls = []; }
        var mk = null, i; for (i = 0; i < ls.length; i++) { var nm = String((ls[i] && ls[i].name) || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); if (ls[i] && ls[i].img && /(^| )mask( |$)/.test(nm)) { mk = ls[i]; break; } }
        if (!mk) return null;
        var bb = mk.bbox || [0, 0, mk.img.width, mk.img.height], L = bb.x != null ? bb.x : bb[0], T = bb.y != null ? bb.y : bb[1], key = [mk.id, Wd, Hd, L, T, mk.img.width, mk.img.height].join(':');
        if (_uv.key === key) return _uv.m;
        var m = null;
        try {
            var cv = document.createElement('canvas'); cv.width = Wd; cv.height = Hd; var cx = cv.getContext('2d', { willReadFrequently: true });
            var sx = Wd / Math.max(1, (document.getElementById('paintCanvas') || { width: Wd }).width), sy = Hd / Math.max(1, (document.getElementById('paintCanvas') || { height: Hd }).height);
            cx.drawImage(mk.img, L * sx, T * sy, mk.img.width * sx, mk.img.height * sy);
            var px = cx.getImageData(0, 0, Wd, Hd).data, op = 0, N = Wd * Hd; for (i = 0; i < N; i++) if (px[i * 4 + 3] > 40) op++;
            var fr = op / N;
            if (fr >= 0.002) {
                var inv = fr < 0.12, pf = 0; m = new Uint8Array(N);
                for (i = 0; i < N; i++) { var o = px[i * 4 + 3] > 40; if (inv ? o : !o) { m[i] = 1; pf++; } }
                if (pf / N <= 0.08 || pf / N >= 0.92) m = null;
            }
        } catch (e2) { m = null; }
        _uv.key = key; _uv.m = m; return m;
    }
    // 8-connected islands smaller than minA px are cleared in place (scan-line flood fill, one pass)
    function despeck(m, w, h, minA) {
        if (minA < 2) return;
        var seen = new Uint8Array(w * h), st = new Int32Array(w * h), comp = [], i, k;
        for (i = 0; i < w * h; i++) {
            if (!m[i] || seen[i]) continue;
            var sp = 0, n = 0; st[sp++] = i; seen[i] = 1; comp.length = 0;
            while (sp) {
                var p = st[--sp], px = p % w, py = (p - px) / w, dy, dx; if (n < minA) comp.push(p); n++;
                for (dy = -1; dy <= 1; dy++) { var yy = py + dy; if (yy < 0 || yy >= h) continue; for (dx = -1; dx <= 1; dx++) { var xx = px + dx; if (xx < 0 || xx >= w) continue; var q = yy * w + xx; if (m[q] && !seen[q]) { seen[q] = 1; st[sp++] = q; } } }
            }
            if (n < minA) for (k = 0; k < comp.length; k++) m[comp[k]] = 0;
        }
    }
    function flamesMask(g) {
        var G = W.SpbGraphics, item = g && g.item ? g.item : g, only = String((g && g.only) || '').toLowerCase(), err = G.check(item); if (err) return null;
        var cols = G.colours(item), c = document.getElementById('paintCanvas'), Wd = c ? c.width : 2048, Hd = c ? c.height : 2048, out = new Uint8Array(Wd * Hd), any = false;
        var cv = canvas(Wd, Hd), ctx = cv.getContext('2d', { willReadFrequently: true }), bleed = clamp(Math.round(num(item.bleed, 8) * Wd / 2048), 0, 40);
        var uv = item.uv === false ? null : uvMask(Wd, Hd);
        G.partList(item).forEach(function (pn) {
            var F = G.frame(pn); if (!F) return;
            var b = F.box, x0 = Math.max(0, Math.floor(b[0]) - bleed - 2), y0 = Math.max(0, Math.floor(b[1]) - bleed - 2), x1 = Math.min(Wd, Math.ceil(b[2]) + bleed + 2), y1 = Math.min(Hd, Math.ceil(b[3]) + bleed + 2);
            ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, Wd, Hd);
            ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip(); ctx.setTransform(F.m[0], F.m[1], F.m[2], F.m[3], F.m[4], F.m[5]);
            var pick = function (k) { var cc = cols[k % cols.length]; return (!only || cc === only) ? cc : null; };
            try { KIND.draw(ctx, F, item, pick); } catch (e) { ctx.restore(); return; }
            ctx.restore(); ctx.setTransform(1, 0, 0, 1, 0, 0);
            var im = ctx.getImageData(x0, y0, x1 - x0, y1 - y0).data, clip = null, mm = null, w = x1 - x0, y, x;
            try { mm = W.SpbProCar.maskFor(pn); } catch (e2) { mm = null; }
            if (mm && mm.mask) clip = bleed > 0 ? soften(mm.mask, Wd, x0, y0, x1, y1, bleed) : null;
            var uc = uv ? soften(uv, Wd, x0, y0, x1, y1, 2) : null;          // the real panel edge (+2 px seam bleed) when the PSD has a Mask layer
            var h = y1 - y0, loc = new Uint8Array(w * h);
            for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
                if (im[(y * w + x) * 4 + 3] <= 127) continue;
                var gi = (y0 + y) * Wd + (x0 + x);
                if (mm && mm.mask && !(clip ? clip[y * w + x] : mm.mask[gi])) continue;
                if (uc && !uc[y * w + x]) continue;
                loc[y * w + x] = 1;
            }
            // POLISH 1 (2026-10-05): drop SPECKS - islands under ~250 px (at 2048) left where a wisp tip / hook crosses a panel edge. They read as dirt at 1:1 and
            // each one is a separate render region for the engine (true fire outer: 52 islands, 35 of them < 400 px -> the engine gave up on its cropped spec path).
            despeck(loc, w, h, Math.round(250 * (Wd / 2048) * (Wd / 2048)));
            for (y = 0; y < h; y++) for (x = 0; x < w; x++) if (loc[y * w + x]) { out[(y0 + y) * Wd + (x0 + x)] = 255; any = true; }
        });
        var desc = (styleOf(item) || 'hotrod') + ' flames on the ' + G.partList(item).join(' and ');
        return any ? { mask: out, desc: desc } : { mask: out, empty: true, desc: desc };
    }
    function register() {
        var G = W.SpbGraphics; if (!(G && G.KINDS)) return false;
        if (!G.KINDS.flames) G.KINDS.flames = KIND;
        if (!G._flamesWrapped && typeof G.maskFor === 'function') {     // zone-kit calls SpbGraphics.maskFor at apply time: route kind 'flames' to the bleed-clipped mask
            var orig = G.maskFor; G.maskFor = function (g) { var it = g && g.item ? g.item : g; return it && it.kind === 'flames' ? flamesMask(g) : orig.apply(this, arguments); }; G._flamesWrapped = true;
        }
        return !!G.KINDS.flames;
    }
    register();

    // ------------------------------------------------------------------ plan / apply: flames -> zones
    function partsOf(o) { var p = o && o.part; if (p == null || p === '' || p === 'sides' || p === 'both sides') return ['left side', 'right side']; if (typeof p === 'string') p = p.split(/\s*(?:,|&|\band\b|\+)\s*/i).filter(Boolean); return p.map(function (s) { return String(s).trim().toLowerCase(); }); }
    function frameOf(part) { try { return W.SpbGraphics && W.SpbGraphics.frame ? W.SpbGraphics.frame(part) : null; } catch (e) { return null; } }
    // a gradient that runs front -> rear on the sheet: direction + whether the stops must be mirrored
    function orient(F) { var fr = (F && F.isl && F.isl.front) || 'left'; if (fr === 'left') return ['horizontal', false]; if (fr === 'right') return ['horizontal', true]; if (fr === 'top') return ['vertical', false]; return ['vertical', true]; }
    function stops(cols, rev) { var n = cols.length; return cols.map(function (c, i) { var pos = n === 1 ? 0 : Math.round(i / (n - 1) * 100); return { pos: rev ? 100 - pos : pos, color: c }; }).sort(function (a, b) { return a.pos - b.pos; }); }
    function lum(rgb) { return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]; }
    // the colour the buyer SEES on the part: the top-most solid zone that repaints the body there (a catch-all zone, or a colour pick of the paint's own body
    // colour), else the paint file's dominant colour. 2026-10-05 second pass: ghost flames on a navy Body zone came out the SOURCE paint's yellow (#dbc200).
    function bodyColour(parts) {
        var src = null, m = null;
        try {
            var C = W.SpbProCar, Z = W.SpbProZone; m = C && C.maskFor ? C.maskFor(parts.length > 1 ? parts : parts[0]) : null;
            var pc = Z && Z.paintColours ? Z.paintColours(3, m && m.mask) : []; src = pc && pc[0] && hexOk(pc[0].hex) ? pc[0].hex.toLowerCase() : null;
        } catch (e) { src = null; }
        try {
            var zs = (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : [], s0 = src ? hexRgb(src) : null, pm = m && m.mask, i, k;
            for (i = 0; i < zs.length; i++) {
                var z = zs[i]; if (!z || z._flames || z.hidden || z.enabled === false || z.muted) continue;
                if (!(String(z.baseColorMode || 'solid') === 'solid' && hexOk(z.baseColor))) continue;
                var catchAll = z.color === 'everything' || z.color === 'remaining', picks = [];
                if (z.color && z.color.color_rgb) picks.push(z.color.color_rgb); if (Array.isArray(z.colors)) z.colors.forEach(function (c) { if (c && c.color_rgb) picks.push(c.color_rgb); });
                if (!catchAll && !(s0 && picks.some(function (p) { return Math.abs(p[0] - s0[0]) + Math.abs(p[1] - s0[1]) + Math.abs(p[2] - s0[2]) < 90; }))) continue;
                if (z.useRegion && z.regionMask && pm && z.regionMask.length === pm.length) { var inP = 0, both = 0; for (k = 0; k < pm.length; k += 13) if (pm[k]) { inP++; if (z.regionMask[k]) both++; } if (!inP || both / inP < 0.4) continue; }
                return String(z.baseColor).toLowerCase();
            }
        } catch (e2) {}
        return src;
    }
    function ghostOf(body) { var c = hexRgb(body), l = lum(c), k = l < 110 ? 0.16 : -0.14; return rgbHex(c.map(function (v) { return k > 0 ? v + (255 - v) * k + 6 : v * (1 + k); })); }
    // classic tribal: black on any strong colour (a red car gets black blades, 1:1 2026-10-05: white blades on red vanished into the white decal bars); white only on dark, dull bodies
    function contrastOf(body) { var c = hexRgb(body), l = lum(c), ch = Math.max(c[0], c[1], c[2]) - Math.min(c[0], c[1], c[2]); return (l < 45 || (l < 120 && ch < 90)) ? '#f2f2f2' : '#0e0e10'; }
    function uniq(list) { var seen = {}; return list.map(function (h) { h = String(h).toLowerCase(); var c = hexRgb(h), k = 0; while (seen[h] && k < 40) { c[2] = c[2] < 255 ? c[2] + 1 : c[2] - 1; h = rgbHex(c); k++; } seen[h] = 1; return h; }); }

    function check(o) {
        if (!o || typeof o !== 'object') return 'flames need an options object';
        if (!styleOf(o)) return 'unknown flame style "' + o.style + '": use hotrod | tribal | ghost | truefire';
        if (!W.SpbGraphics || !register()) return 'the graphics library is not loaded';
        if (!W.SpbProZone || !W.SpbProZone.batch) return 'the zone kit is not loaded';
        var bad = null; partsOf(o).forEach(function (pn) { if (!bad && !frameOf(pn)) bad = 'unknown part "' + pn + '" (this car\'s map does not have it: show it in the Shokker panel first)'; });
        if (bad) return bad;
        if (o.colours != null && !(Array.isArray(o.colours) ? o.colours : [o.colours]).every(hexOk)) return 'colours must be "#rrggbb"';
        if (o.outline != null && o.outline !== false && !hexOk(o.outline)) return 'outline must be "#rrggbb" or false';
        return null;
    }

    function plan(o) {
        var err = check(o); if (err) return { ok: false, ops: [], zones: [], notes: [err] };
        var sty = styleOf(o), d = STYLES[sty].d, parts = partsOf(o), notes = [], ops = [], names = [];
        var cols = o.colours != null ? (Array.isArray(o.colours) ? o.colours : [o.colours]).map(function (h) { return h.toLowerCase(); }) : null;
        var body = (sty === 'ghost' || sty === 'tribal') && !cols ? bodyColour(parts) : null;
        if (!cols) cols = sty === 'ghost' ? [ghostOf(body || '#202024')] : (sty === 'tribal' ? [contrastOf(body || '#d0d0d0')] : d.colours.slice());
        if (sty === 'ghost' && body && !o.colours) notes.push('ghost colour ' + cols[0] + ' from the body colour ' + body);
        // true fire layers: 1 (default) = ONE zone, nested tongues cut apart by thin channels, one fire gradient; 2 = outer + inner zones; 3 (or core:true) = outer + mid + core
        var fireLayers = sty !== 'truefire' ? 0 : clamp(Math.round(num(o.layers, o.core === true ? 3 : 1)), 1, 3);
        var outline = o.outline === false ? null : (hexOk(o.outline) ? o.outline.toLowerCase() : (d.outline || null));
        var fin = o.finish || d.finish, ofin = o.outline_finish || d.outline_finish, ow = clamp(num(o.outline_w, d.outline_w), 1, 40);
        var excl = o.keep_decals === false ? null : ['numbers', 'sponsors'];
        // one set of zones per sheet orientation (a fade must run front -> rear on every part it covers)
        var groups = {}, order = [];
        parts.forEach(function (pn) { var F = frameOf(pn), oi = orient(F), k = oi.join(':'); if (!groups[k]) { groups[k] = { o: oi, parts: [] }; order.push(k); } groups[k].parts.push(pn); });
        var label = { hotrod: 'Hot rod flames', tribal: 'Tribal flames', ghost: 'Ghost flames', truefire: 'True fire' }[sty];
        var keys = uniq([cols[0], outline || '#000001', cols[1] || '#000002', cols[2] || '#000003']);
        function where(list) { var l = list.slice(), i = l.indexOf('left side'), j = l.indexOf('right side'); if (i !== -1 && j !== -1) { l = l.filter(function (x) { return x !== 'left side' && x !== 'right side'; }); l.push('sides'); } return l.join(', '); }
        function itemFor(list) {
            var it = { kind: 'flames', part: list.length === 1 ? list[0] : list.slice(), colours: keys, style: sty, seed: num(o.seed, 7), outline_w: ow };
            if (sty === 'truefire' && fireLayers === 2) it.core_in_mid = true;
            if (sty === 'truefire' && fireLayers === 1) { it.fire_contour = true; if (o.gap != null) it.gap = o.gap; }
            ['licks', 'length', 'base', 'curl', 'scale', 'band', 'wave', 'width', 'bleed'].forEach(function (q) { if (o[q] != null) it[q] = o[q]; });
            return it;
        }
        function zone(list, role, idx, look) {
            var nm = label + ' ' + role + ' (' + where(list) + ')', spec = { name: nm, region: { graphic: { item: itemFor(list), only: keys[idx] } } };
            if (excl) spec.region.exclude = excl.slice();
            for (var q in look) spec[q] = look[q];
            ops.push({ kind: 'add', spec: spec }); names.push(nm);
        }
        // ZONE BUDGET. POLISH 1 (2026-10-05, CLAUDE.md render law <= 3 s at 2048): a solid / gradient zone renders its PAINT over the full 2048 canvas whatever its size
        // (engine: "paint full path: base color mode is adjusted"), measured ~0.6-0.8 s per flame zone even for a 1% hood zone; a body-only car is ~1.6-2.1 s on the
        // test server. So every style is ONE zone by default:
        //   - a front -> rear FADE over parts that face opposite ways on the sheet (hood front = right, sides front = left) is ONE horizontal gradient with stops at
        //     SHEET positions (fit:false): the flames on each part occupy their own stretch of x, so each stretch gets its own fade. Falls back to one zone per sheet
        //     orientation only when two stretches overlap (e.g. length 1.0 on the sides reaching the hood's x range).
        //   - true fire: ONE zone by default (layers:1): the three nested layers are kept as SHAPES (thin body-colour channels cut around the mid tongues, re-closed inside the front band)
        //     and coloured by one 5-stop fire gradient. layers:2 = outer + inner zones (+~0.7 s), layers:3 / core:true = the original outer + mid + core (+~1.4 s).
        //   - hot rod pinstripe outline: its own zone (+~0.6 s); kept ON by default (STYLES.hotrod.d.outline) - hood + both sides measured 1.9-2.0 s on 59879.
        function sheetRange(pn, it, roles, axis) {          // [lo, hi] in sheet px of this job's shapes on one part, along x (axis 0) or y (axis 1)
            var F = frameOf(pn); if (!F) return null; var g = null; try { g = geometry(F, it); } catch (e) { return null; }
            var m = F.m, lo = 1e9, hi = -1e9, bx = F.box;
            roles.forEach(function (r) { (g[r] || []).forEach(function (pl) { pl.forEach(function (pt) { var v = axis ? m[1] * pt[0] + m[3] * pt[1] + m[5] : m[0] * pt[0] + m[2] * pt[1] + m[4]; if (v < lo) lo = v; if (v > hi) hi = v; }); }); });
            lo = Math.max(lo, axis ? bx[1] : bx[0]); hi = Math.min(hi, axis ? bx[3] : bx[2]); return hi > lo ? [lo, hi] : null;
        }
        // fade = [[t 0..1 front -> tips, '#hex'], ...]
        function fadeZones(role, idx, fade, look, roles) {
            var dims = [2048, 2048]; try { var pc = document.getElementById('paintCanvas'); if (pc && pc.width) dims = [pc.width, pc.height]; } catch (e) {}
            var segs = [], axis0 = null, merged = true;
            order.forEach(function (k) {
                var g = groups[k], axis = g.o[0] === 'vertical' ? 1 : 0, lo = 1e9, hi = -1e9;
                if (axis0 == null) axis0 = axis; else if (axis !== axis0) merged = false;
                g.parts.forEach(function (pn) { var r = sheetRange(pn, itemFor([pn]), roles, axis); if (r) { lo = Math.min(lo, r[0]); hi = Math.max(hi, r[1]); } });
                if (hi <= lo) merged = false; else segs.push({ lo: lo / dims[axis] * 100, hi: hi / dims[axis] * 100, rev: g.o[1], g: g });
            });
            segs.sort(function (a, b) { return a.lo - b.lo; });
            for (var i = 1; i < segs.length; i++) if (segs[i].lo < segs[i - 1].hi + 1) merged = false;
            function spec() { var o = {}; for (var q in look) o[q] = look[q]; return o; }
            if (merged && segs.length > 1) {
                var st = []; segs.forEach(function (sg) { fade.forEach(function (f) { st.push({ pos: Math.round(sg.rev ? sg.hi - f[0] * (sg.hi - sg.lo) : sg.lo + f[0] * (sg.hi - sg.lo)), color: f[1] }); }); });
                st.sort(function (a, b) { return a.pos - b.pos; });
                var lk = spec(); lk.gradient = { stops: st, direction: axis0 ? 'vertical' : 'horizontal', fit: false }; zone(parts, role, idx, lk); return 1;
            }
            order.forEach(function (k) { var g = groups[k], lk = spec(); lk.gradient = { stops: fade.map(function (f) { var pp = Math.round(f[0] * 100); return { pos: g.o[1] ? 100 - pp : pp, color: f[1] }; }).sort(function (a, b) { return a.pos - b.pos; }), direction: g.o[0], fit: true }; zone(g.parts, role, idx, lk); });
            return order.length;
        }
        if (outline) zone(parts, 'outline', 1, { finish: ofin, color: outline });
        if (sty === 'truefire' && fireLayers === 1) {
            var cO = cols[0], cM = cols[1] || '#ff6a00', cC = cols[2] || '#ffe27a';
            fadeZones('flames', 0, [[0, cC], [0.1, cC], [0.34, cM], [0.62, cO], [1, shade(cO, -0.38)]], { finish: fin }, ['fill']);
        } else if (sty === 'truefire') {
            fadeZones('outer', 0, [[0, cols[0]], [1, shade(cols[0], -0.38)]], { finish: fin }, ['fill']);
            if (fireLayers === 3) {
                zone(parts, 'mid', 2, { finish: fin, color: cols[1] || '#ff6a00' });
                zone(parts, 'core', 3, { finish: 'base::wet_look', color: cols[2] || '#ffe27a' });
            } else fadeZones('inner', 2, [[0, cols[2] || '#ffe27a'], [0.1, cols[2] || '#ffe27a'], [0.42, cols[1] || '#ff6a00'], [1, cols[1] || '#ff6a00']], { finish: fin }, ['mid', 'core']);
        } else if (cols.length > 1) fadeZones('fill', 0, cols.map(function (c, i) { return [cols.length === 1 ? 0 : i / (cols.length - 1), c]; }), { finish: fin }, ['fill']);
        else zone(parts, 'fill', 0, { finish: fin, color: cols[0] });
        notes.push(STYLES[sty].about);
        return { ok: true, ops: ops, zones: names, notes: notes, style: sty, parts: parts };
    }
    function shade(h, k) { var c = hexRgb(h); return rgbHex(c.map(function (v) { return k > 0 ? v + (255 - v) * k : v * (1 + k); })); }

    function apply(o) {
        var pl = plan(o); if (!pl.ok) return { ok: false, applied: [], warnings: pl.notes, zones: [] };
        // replace (default): flames already on any of these parts are taken off in the SAME undo step, so "make them tribal instead" swaps, never stacks
        var label = (o && o.label) || 'Flames', removed = [], noUndo = false;
        if (o.replace !== false) {
            try {
                var zs = (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : [], mine = {}, i;
                pl.parts.forEach(function (p) { mine[p] = 1; if (/side/.test(p)) mine.sides = 1; });
                var old = zs.filter(function (z) {
                    if (!z) return false;
                    var ps = z._flames && z._flames.parts ? z._flames.parts : null, m = !ps && /^(Hot rod flames|Tribal flames|Ghost flames|True fire) [a-z]+ \(([^)]*)\)$/.exec(String(z.name || ''));
                    if (m) ps = m[2].split(/,\s*/);
                    return !!(ps && ps.some(function (p) { return mine[p]; }));
                });
                if (old.length) {
                    if (typeof W.pushZoneUndo === 'function') { W.pushZoneUndo(label); noUndo = true; }
                    for (i = zs.length - 1; i >= 0; i--) if (old.indexOf(zs[i]) !== -1) { removed.push(zs[i].name); zs.splice(i, 1); }
                    try { if (typeof selectedZoneIndex !== 'undefined' && selectedZoneIndex >= zs.length) selectedZoneIndex = Math.max(0, zs.length - 1); } catch (eS) {}
                }
            } catch (eR) {}
        }
        var res = W.SpbProZone.batch(pl.ops, label, noUndo ? { noUndo: true } : undefined) || [], applied = [], warnings = [], ok = true;
        (Array.isArray(res) ? res : [res]).forEach(function (r) { if (!r) return; if (r.ok === false) ok = false; (r.applied || []).forEach(function (a) { applied.push(a); if (/nothing landed on the car/.test(a)) { ok = false; warnings.push('nothing landed on the ' + pl.parts.join(' / ') + ': the app does not know where that part is on this car yet'); } }); (r.warnings || []).forEach(function (w) { warnings.push(w); }); if (r.zone) r.zone._flames = { style: pl.style, parts: pl.parts }; });
        if (removed.length) applied.unshift('replaced the flames already there: ' + removed.join(', '));
        return { ok: ok, applied: applied, warnings: warnings, zones: pl.zones, notes: pl.notes, removed: removed };
    }

    // CLAUDE.md 0b (Coverage + Fine-Detail law): DELIBERATE, DOCUMENTED opt-out. A flame job is a part-placed GRAPHIC (solid base at the front of a part, licks
    // reaching back, empty body paint behind them), not a full-canvas finish/pattern/spec: covering the whole 2048 canvas or crushing it into 8-32 px detail would
    // destroy what a flame job IS. It adds NO catalogue finish (its zones use existing finishes: f_candy, wet_look, f_pearl), so the Finish Law / uniqueness gates
    // have nothing new to score; the look was judged by eye at 1:1 on the owner's ARCA (docs/handoff_reports/FLAMES.md).
    var COVERAGE_EXEMPT = { flames: 'part-placed flame-job graphic (hot rod / tribal / ghost / true fire): fills one named part from its front, never the whole canvas, by design (owner decision 2026-10-05 "Build real flame licks")' };
    var FINE_DETAIL_EXEMPT = { flames: 'solid sign-painter licks with a pinstripe: clean shapes are the look; fine detail comes from the finish each flame zone carries' };
    W.SpbFlames = { VERSION: '2026-10-05', STYLES: STYLES, KIND: KIND, check: check, plan: plan, apply: apply, geometry: geometry, register: register, COVERAGE_EXEMPT: COVERAGE_EXEMPT, FINE_DETAIL_EXEMPT: FINE_DETAIL_EXEMPT };
})();
