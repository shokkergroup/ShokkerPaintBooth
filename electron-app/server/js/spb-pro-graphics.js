/* SPB PRO GRAPHICS (2026-10-02): crisp DESIGN GRAPHICS the copilot can place on named car parts: concentric arcs ("sonic rings"), speed lines, angled stripes, waves, chevrons, checkers, dots, rays, lightning.
   Owner brief 2026-10-02: "tackle whatever people throw at it in terms of what they want on a car" + "make my ARCA look like THIS concept picture": the paint library could only place plain colour bands, so arcs / speed lines / rays were impossible.
   A graphic is drawn in PART space: u = 0..1 along the car from the FRONT to the REAR, v = 0..1 from the ROOF-LINE down to the ROCKER (top parts: across). The part's orientation (front / up from the car library) turns that into sheet pixels,
   so the same spec lands correctly on the left side, the right side (rotated 180 on the sheet), the hood, any car. Specs are plain JSON (portable in recipes).
   API: SpbGraphics.check(item) -> error string|null;  SpbGraphics.maskFor({ item, only }) -> { mask: Uint8Array(W*H), desc };  SpbGraphics.KINDS (id -> {about, params});  SpbGraphics.colours(item) -> ['#rrggbb', ...]
   ES5 only. Pure drawing on an offscreen canvas; no state kept. */
(function () {
    'use strict';
    var W = window;
    function car() { return W.SpbProCar; }
    function dims() { var c = document.getElementById('paintCanvas'); return c ? [c.width, c.height] : [2048, 2048]; }
    function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function rng(seed) { var a = (num(seed, 1) * 2654435761) >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; var t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function hexOk(h) { return /^#[0-9a-f]{6}$/i.test(String(h || '')); }
    function lc(h) { return String(h || '').toLowerCase(); }

    // ------------------------------------------------------------------ part frame: part-local (lx along the car front->rear, ly roof-line->rocker) -> sheet pixels
    function frame(part) {
        var C = car(); if (!C || !C.findIsland) return null; var isl = C.findIsland(part); if (!isl || !isl.bbox) return null;
        // LIVE PLAYTEST 2026-10-09: ghost flames on the ARCA Chevy started at the REAR (library front 'left', owner taught 'rear of the sides' at the left end). A trusted nose (owner / taught / atlas, js/spb-door-data.js) now wins over the library box's front.
        if (C.nose && (isl.front || 'left') !== 'top' && (isl.front || 'left') !== 'bottom') { var ns = C.nose(part); if (ns && ns.trusted && (ns.end === 'left' || ns.end === 'right') && ns.end !== (isl.front || 'left')) isl = Object.assign({}, isl, { front: ns.end }); }
        var d = dims(), b = isl.bbox, x0 = b[0] * d[0], y0 = b[1] * d[1], x1 = b[2] * d[0], y1 = b[3] * d[1], bw = x1 - x0, bh = y1 - y0, fr = isl.front || 'left', up = isl.up || 'top', alongX = (fr === 'left' || fr === 'right'), m;
        if (alongX) { m = [fr === 'left' ? 1 : -1, 0, 0, up === 'bottom' ? -1 : 1, fr === 'left' ? x0 : x1, up === 'bottom' ? y1 : y0]; }
        else { m = [0, fr === 'top' ? 1 : -1, up === 'right' ? -1 : 1, 0, up === 'right' ? x1 : x0, fr === 'top' ? y0 : y1]; }
        return { name: part, isl: isl, box: [x0, y0, x1, y1], L: alongX ? bw : bh, H: alongX ? bh : bw, m: m };
    }
    function partList(item) {
        var p = item.part; if (p == null || p === '' || p === 'sides') p = ['left side', 'right side'];
        if (typeof p === 'string') p = /\s*(,|&|\band\b|\+)\s*/i.test(p) && !(car() && car().findIsland(p)) ? p.split(/\s*(?:,|&|\band\b|\+)\s*/i).filter(Boolean) : [p];
        return p;
    }
    function colours(item) {
        var cs = item.colours || item.colors || (item.colour ? [item.colour] : []); if (typeof cs === 'string') cs = [cs];
        return cs.filter(hexOk).map(lc);
    }

    // ------------------------------------------------------------------ the strokes. ctx is already transformed to part-local pixels (lx along the car, ly down); every painter calls pick(k) for a stroke's colour and draws only when it returns a colour
    var KINDS = {
        outline: {          // HELPER FIX PASS 7 2026-10-05: a line along the part's own edge ("a thin red line around the roof", "gold trim around the trunk"); drawn from the car map's part mask in maskFor, not in part space
            about: 'a line that follows the outer edge of the part (trim / border / outline)',
            params: 'w line width as a fraction of the sheet/4 (0.012 thin, 0.02 default, 0.035 thick); HELPER V3 S5: stroke_px line width in px on a 2048 sheet (wins over w); sides inner|outer|both; element numbers|sponsors (a line around that art); zone <zone id> (a line around that zone); gap_px space between the art and an outer line',
            draw: function () {}
        },
        seam: {          // HELPER V3 S5 2026-10-05 (b6-042 "fine silver pinline between the red and white" recoloured BOTH colours): a line ONLY where two regions meet
            about: 'a thin line along the boundary where two regions meet (a pinline between two colours, parts or layers); it paints neither region',
            params: 'a, b: {part} | {parts:[..]} | {layer} | {zone} | {element} | {colour:"#rrggbb", tol} | {family:"red"} | {rest:[parts]} (the car minus those parts); stroke_px width in px on a 2048 sheet (default 6); part: limit the line to these parts',
            draw: function () {}
        },
        rings: {
            about: 'concentric arcs ("sonic rings", radar rings, ripples) around a centre point, optionally dashed and with straight tails',
            params: 'cu,cv centre (0..1 of the part: cu front->rear, cv roof-line->rocker); r0,r1 first/last radius as a fraction of the part HEIGHT; n rings; w0,w1 ring width (fraction of height); facing front|rear|up|down|all; span degrees (default 160); gap 0..1 dashed; tail 0..1 straight tail (fraction of length) at both arc ends; seed',
            draw: function (c, F, p, pick, R) {
                var H = F.H, L = F.L, cx = clamp(num(p.cu, 0.4), -0.5, 1.5) * L, cy = clamp(num(p.cv, 0.55), -0.5, 1.5) * H, k, list = [];
                var face = { rear: 0, front: Math.PI, down: Math.PI / 2, up: -Math.PI / 2, all: 0 }[String(p.facing || 'front')]; if (face == null) face = Math.PI;
                var span0 = clamp(num(p.span, 160), 10, 360) * Math.PI / 180; if (p.facing === 'all') span0 = Math.PI * 2;
                if (Array.isArray(p.radii) && p.radii.length) {       // measured rings: explicit radius / width / span / colour per ring
                    p.radii.slice(0, 40).forEach(function (r, i) { list.push({ r: num(r, 0.3) * H, w: num((p.widths || [])[i], 0.025) * H, span: p.spans && p.spans[i] != null ? clamp(num(p.spans[i], 160), 10, 360) * Math.PI / 180 : span0, ci: p.seq && p.seq[i] != null ? num(p.seq[i], i) : i }); });
                } else {
                    var n = clamp(Math.round(num(p.n, 7)), 1, 40), r0 = num(p.r0, 0.12) * H, r1 = num(p.r1, 0.9) * H, w0 = num(p.w0, 0.018) * H, w1 = num(p.w1, 0.04) * H;
                    for (k = 0; k < n; k++) { var t = n === 1 ? 0 : k / (n - 1); list.push({ r: r0 + (r1 - r0) * t, w: w0 + (w1 - w0) * (0.5 + 0.5 * Math.sin(Math.PI * (t - 0.25) * 1.3)), span: span0, ci: k }); }
                }
                var gap = clamp(num(p.gap, 0), 0, 0.9), tail = clamp(num(p.tail, 0), 0, 1) * L;
                list.forEach(function (rg) {
                    var col = pick(rg.ci); if (!col) return; var r = rg.r, w = Math.max(1, rg.w), a0 = face - rg.span / 2, a1 = face + rg.span / 2, segs = [[a0, a1]];
                    if (gap > 0 && p.facing !== 'all') { segs = []; var q = a0; while (q < a1) { var len = (0.25 + R() * 0.75) * rg.span * 0.6, e = Math.min(a1, q + len); segs.push([q, e]); q = e + gap * (0.04 + R() * 0.12) * rg.span * 2; } }
                    c.fillStyle = col;
                    segs.forEach(function (sg) { c.beginPath(); c.arc(cx, cy, r + w / 2, sg[0], sg[1], false); c.arc(cx, cy, Math.max(0.1, r - w / 2), sg[1], sg[0], true); c.closePath(); c.fill(); });
                    if (tail > 0 && p.facing !== 'all') {
                        [a0, a1].forEach(function (ang) { var ex = cx + r * Math.cos(ang), ey = cy + r * Math.sin(ang); c.beginPath(); c.moveTo(ex, ey - w / 2); c.lineTo(ex + tail * (0.5 + 0.5 * R()), ey - w * 0.05); c.lineTo(ex + tail * (0.5 + 0.5 * R()), ey + w * 0.05); c.lineTo(ex, ey + w / 2); c.closePath(); c.fill(); });
                    }
                });
            }
        },
        speed_lines: {
            about: 'speed lines: thin tapered streaks running along the car (or at an angle), fading out',
            params: 'u0,u1 where they start (0..1 along the part, front->rear); v0,v1 vertical range (roof-line->rocker); n lines; wmin,wmax width (fraction of height); lenmin,lenmax length (fraction of the part length); taper tail|head|both|none; angle degrees; seed',
            draw: function (c, F, p, pick, R) {
                var n = clamp(Math.round(num(p.n, 14)), 1, 120), H = F.H, L = F.L, u0 = num(p.u0, 0.3), u1 = num(p.u1, 0.9), v0 = num(p.v0, 0.15), v1 = num(p.v1, 0.9), wmin = num(p.wmin, 0.006) * H, wmax = num(p.wmax, 0.022) * H, lmin = num(p.lenmin, 0.12) * L, lmax = num(p.lenmax, 0.5) * L, ang = num(p.angle, 0) * Math.PI / 180, taper = String(p.taper || 'tail'), k;
                for (k = 0; k < n; k++) {
                    var col = pick(k); var uu = (u0 + (u1 - u0) * R()) * L, vv = (v0 + (v1 - v0) * (n === 1 ? 0.5 : (k + R() * 0.6) / n)) * H, len = lmin + (lmax - lmin) * R(), w = wmin + (wmax - wmin) * R(); if (!col) continue;
                    c.save(); c.translate(uu, vv); c.rotate(ang); c.fillStyle = col; c.beginPath();
                    if (taper === 'both') { c.moveTo(0, 0); c.lineTo(len / 2, -w / 2); c.lineTo(len, 0); c.lineTo(len / 2, w / 2); }
                    else if (taper === 'head') { c.moveTo(0, 0); c.lineTo(len, -w / 2); c.lineTo(len, w / 2); }
                    else if (taper === 'none') { c.moveTo(0, -w / 2); c.lineTo(len, -w / 2); c.lineTo(len, w / 2); c.lineTo(0, w / 2); }
                    else { c.moveTo(0, -w / 2); c.lineTo(len, -w * 0.04); c.lineTo(len, w * 0.04); c.lineTo(0, w / 2); }
                    c.closePath(); c.fill(); c.restore();
                }
            }
        },
        strokes: {
            about: 'an explicit list of tapered strokes (measured speed lines or hand-placed streaks)',
            params: 'items: [{u0,u1,v,w0,w1,c}] u0..u1 along the part (front->rear), v across (roof-line->rocker), w0 = width at the start and w1 = at the end (fractions of height), c = colour index',
            draw: function (c, F, p, pick) {
                var H = F.H, L = F.L, items = Array.isArray(p.items) ? p.items.slice(0, 200) : [];
                items.forEach(function (it, i) {
                    var col = pick(it.c != null ? num(it.c, 0) : i); if (!col) return; var x0 = num(it.u0, 0) * L, x1 = num(it.u1, 0.3) * L, y = num(it.v, 0.5) * H, w0 = Math.max(0.5, num(it.w0, 0.01) * H), w1 = Math.max(0.3, num(it.w1, it.w0 != null ? it.w0 : 0.01) * H);
                    c.fillStyle = col; c.beginPath(); c.moveTo(x0, y - w0 / 2); c.lineTo(x1, y - w1 / 2); c.lineTo(x1, y + w1 / 2); c.lineTo(x0, y + w0 / 2); c.closePath(); c.fill();
                });
            }
        },
        stripes: {
            about: 'a set of parallel stripes at an angle (racing stripes, pinstripe packs, diagonal slashes), optionally curved',
            params: 'angle degrees (0 = along the car); n stripes; w stripe width and gap spacing (fractions of the part height); at centre offset 0..1 across the part; curve -1..1 bends them; from,to limit along the length (0..1)',
            draw: function (c, F, p, pick) {
                var n = clamp(Math.round(num(p.n, 3)), 1, 60), H = F.H, L = F.L, w = num(p.w, 0.06) * H, gap = num(p.gap, 0.08) * H, at = num(p.at, 0.5) * H, ang = num(p.angle, 0) * Math.PI / 180, curve = num(p.curve, 0) * H, from = num(p.from, 0) * L, to = num(p.to, 1) * L, k;
                if (p.stroke_px != null) w = clamp(num(p.stroke_px, 6), 1, 400) * dims()[0] / 2048; if (p.gap_px != null) gap = clamp(num(p.gap_px, 6), 0, 400) * dims()[0] / 2048;          // HELPER V3 S5 2026-10-05: absolute stripe width / gap in px on a 2048 sheet (stored on the zone, so "thinner" / "half that" can edit it)
                c.save(); c.translate((from + to) / 2, at); c.rotate(ang);
                for (k = 0; k < n; k++) {
                    var col = pick(k); if (!col) continue; var off = (k - (n - 1) / 2) * (w + gap), half = Math.hypot(L, H); c.fillStyle = col; c.beginPath();
                    c.moveTo(-half, off - w / 2); c.quadraticCurveTo(0, off - w / 2 + curve, half, off - w / 2); c.lineTo(half, off + w / 2); c.quadraticCurveTo(0, off + w / 2 + curve, -half, off + w / 2); c.closePath(); c.fill();
                }
                c.restore();
            }
        },
        waves: {
            about: 'wavy bands that run along the car (flow lines, water, flame-like ripples)',
            params: 'n bands; w band width and spacing (fractions of height); amp wave height (fraction of height); wavelength (fraction of length); v0 first band position 0..1; phase degrees',
            draw: function (c, F, p, pick) {
                var n = clamp(Math.round(num(p.n, 4)), 1, 40), H = F.H, L = F.L, w = num(p.w, 0.04) * H, sp = num(p.spacing, 0.1) * H, amp = num(p.amp, 0.05) * H, wl = Math.max(0.03, num(p.wavelength, 0.25)) * L, v0 = num(p.v0, 0.3) * H, ph = num(p.phase, 0) * Math.PI / 180, k, x;
                for (k = 0; k < n; k++) {
                    var col = pick(k); if (!col) continue; c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'butt'; c.lineJoin = 'round'; c.beginPath();
                    for (x = -10; x <= L + 10; x += Math.max(4, L / 400)) { var y = v0 + k * sp + amp * Math.sin(2 * Math.PI * x / wl + ph + k * 0.5); if (x <= -10) c.moveTo(x, y); else c.lineTo(x, y); }
                    c.stroke();
                }
            }
        },
        chevrons: {
            about: 'repeating V / arrow shapes across the part (speed arrows, hazard V, rally arrows)',
            params: 'n chevrons; w thickness and spacing (fractions of the part length); depth point depth (fraction of height); u0,u1 range; direction front|rear (which way the points face)',
            draw: function (c, F, p, pick) {
                var n = clamp(Math.round(num(p.n, 6)), 1, 60), H = F.H, L = F.L, u0 = num(p.u0, 0.1) * L, u1 = num(p.u1, 0.9) * L, th = num(p.w, 0.03) * L, depth = num(p.depth, 0.4) * H, dir = String(p.direction || 'rear') === 'front' ? -1 : 1, k, step = (u1 - u0) / n;
                for (k = 0; k < n; k++) {
                    var col = pick(k); if (!col) continue; var x = u0 + k * step; c.fillStyle = col; c.beginPath();
                    c.moveTo(x, 0); c.lineTo(x + dir * depth, H / 2); c.lineTo(x, H); c.lineTo(x + th, H); c.lineTo(x + th + dir * depth, H / 2); c.lineTo(x + th, 0); c.closePath(); c.fill();
                }
            }
        },
        checker: {
            about: 'a checkered flag field (racing checks), usually fading out toward one end',
            params: 'size check size (fraction of the part height); u0,u1,v0,v1 the block it fills (0..1); rows limits the rows',
            draw: function (c, F, p, pick) {
                var H = F.H, L = F.L, s = Math.max(0.01, num(p.size, 0.07)) * H, u0 = num(p.u0, 0.8) * L, u1 = num(p.u1, 1) * L, v0 = num(p.v0, 0) * H, v1 = num(p.v1, 1) * H, i, j, col = pick(0);
                if (!col) return; c.fillStyle = col;
                for (j = 0; v0 + j * s < v1; j++) for (i = 0; u0 + i * s < u1; i++) if ((i + j) % 2 === 0) c.fillRect(u0 + i * s, v0 + j * s, Math.min(s, u1 - u0 - i * s), Math.min(s, v1 - v0 - j * s));
            }
        },
        dots: {
            about: 'a halftone dot field (dots shrink toward one end)',
            params: 'spacing dot grid spacing and size max dot size (fractions of the part height); u0,u1,v0,v1 the block it fills; fade front|rear|none',
            draw: function (c, F, p, pick) {
                var H = F.H, L = F.L, sp = Math.max(0.015, num(p.spacing, 0.07)) * H, mx = num(p.size, 0.055) * H, u0 = num(p.u0, 0) * L, u1 = num(p.u1, 1) * L, v0 = num(p.v0, 0) * H, v1 = num(p.v1, 1) * H, fade = String(p.fade || 'rear'), i, j, col = pick(0);
                if (!col) return; c.fillStyle = col;
                for (j = 0; v0 + j * sp < v1; j++) for (i = 0; u0 + i * sp < u1; i++) {
                    var x = u0 + (i + (j % 2 ? 0.5 : 0)) * sp, y = v0 + j * sp, t = (x - u0) / Math.max(1, u1 - u0), f = fade === 'rear' ? 1 - t : (fade === 'front' ? t : 1), r = mx * clamp(f, 0, 1) / 2;
                    if (r > 0.8) { c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); }
                }
            }
        },
        rays: {
            about: 'a sunburst / radiating rays from a point (starburst, light rays)',
            params: 'cu,cv centre; n rays; duty ray share of each slice 0..1; from,to angle range in degrees (default full circle); seed',
            draw: function (c, F, p, pick) {
                var n = clamp(Math.round(num(p.n, 18)), 2, 120), H = F.H, L = F.L, cx = num(p.cu, 0.5) * L, cy = num(p.cv, 0.5) * H, duty = clamp(num(p.duty, 0.5), 0.05, 0.95), a0 = num(p.from, 0) * Math.PI / 180, a1 = num(p.to, 360) * Math.PI / 180, R = Math.hypot(L, H) * 1.2, k, slice = (a1 - a0) / n;
                for (k = 0; k < n; k++) {
                    var col = pick(k); if (!col) continue; var s = a0 + k * slice; c.fillStyle = col; c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + R * Math.cos(s), cy + R * Math.sin(s)); c.lineTo(cx + R * Math.cos(s + slice * duty), cy + R * Math.sin(s + slice * duty)); c.closePath(); c.fill();
                }
            }
        },
        lightning: {
            about: 'a jagged lightning bolt (one or several)',
            params: 'u0,v0 start and u1,v1 end (0..1); w bolt width (fraction of height); jag zig-zag size; bolts count; seed',
            draw: function (c, F, p, pick, R) {
                var H = F.H, L = F.L, w = num(p.w, 0.035) * H, jag = num(p.jag, 0.12) * H, bolts = clamp(Math.round(num(p.bolts, 1)), 1, 8), b, i;
                for (b = 0; b < bolts; b++) {
                    var col = pick(b); if (!col) continue; var x0 = num(p.u0, 0.2) * L, y0 = num(p.v0, 0.1) * H + b * H * 0.12, x1 = num(p.u1, 0.8) * L, y1 = num(p.v1, 0.9) * H - b * H * 0.1, segs = 7;
                    c.strokeStyle = col; c.lineWidth = w; c.lineJoin = 'miter'; c.lineCap = 'butt'; c.miterLimit = 6; c.beginPath(); c.moveTo(x0, y0);
                    for (i = 1; i < segs; i++) { var t = i / segs; c.lineTo(x0 + (x1 - x0) * t + (R() - 0.5) * jag * 2, y0 + (y1 - y0) * t + (R() - 0.5) * jag * 2); }
                    c.lineTo(x1, y1); c.stroke();
                }
            }
        }          // flames live in js/spb-pro-flames.js (SpbFlames registers KINDS.flames; a duplicate here on 2026-10-09 pre-empted it and was removed)
    };

    function check(item) {
        if (!item || typeof item !== 'object') return 'a graphic needs to be an object';
        if (!KINDS[item.kind]) return 'unknown graphic kind "' + item.kind + '": use ' + Object.keys(KINDS).join(' | ');
        if (!colours(item).length) return 'a graphic needs colour (or colours) as #rrggbb';
        if (item.kind === 'outline' && item.layer) return layerMask(item.layer) ? null : 'unknown layer "' + item.layer + '"';          // HELPER FIX PASS 8 2026-10-05
        if (item.kind === 'outline' && item.element) return elementMask(item.element) ? null : 'the ' + item.element + ' were not found on this paint';          // HELPER V3 S5 2026-10-05
        if (item.kind === 'outline' && item.zone != null) return zoneMask(item.zone) ? null : 'no zone "' + item.zone + '" with a shape to outline';          // HELPER V3 S5
        if (item.kind === 'seam') return seamCheck(item);          // HELPER V3 S5
        var bad = null; partList(item).forEach(function (pn) { if (!bad && car() && car().findIsland && !car().findIsland(pn)) bad = 'unknown part "' + pn + '"'; });
        return bad;
    }

    var _cv = null;
    function canvas(d) { if (!_cv || _cv.width !== d[0] || _cv.height !== d[1]) { _cv = document.createElement('canvas'); _cv.width = d[0]; _cv.height = d[1]; } return _cv; }

    // render one graphic item restricted to ONE colour (the colour a zone paints) into a full-sheet mask
    function maskFor(g) {
        var item = g && g.item ? g.item : g, only = lc(g && g.only), cols = colours(item), err = check(item); if (err) return null;
        if (item.kind === 'outline' && (item.sides || item.element || item.zone != null || item.stroke_px != null)) return ringMask(item, only, cols);          // HELPER V3 S5 2026-10-05: stroke px / sides / element / zone outlines (old items without these fields keep the exact old pixels below)
        if (item.kind === 'seam') return seamMask(item, only, cols);          // HELPER V3 S5
        if (item.kind === 'outline') return outlineMask(item, only, cols);          // HELPER FIX PASS 7 2026-10-05
        var d = dims(), Wd = d[0], Hd = d[1], out = new Uint8Array(Wd * Hd), cv = canvas(d), ctx = cv.getContext('2d', { willReadFrequently: true }), kind = KINDS[item.kind], any = false;
        partList(item).forEach(function (pn) {
            var F = frame(pn); if (!F) return;
            ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, Wd, Hd);
            var b = F.box, x0 = Math.max(0, Math.floor(b[0]) - 2), y0 = Math.max(0, Math.floor(b[1]) - 2), x1 = Math.min(Wd, Math.ceil(b[2]) + 2), y1 = Math.min(Hd, Math.ceil(b[3]) + 2);
            ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip(); ctx.setTransform(F.m[0], F.m[1], F.m[2], F.m[3], F.m[4], F.m[5]);
            var R = rng(item.seed), pick = function (k) { var c = cols[k % cols.length]; return (!only || c === only) ? c : null; };
            try { kind.draw(ctx, F, item, pick, R); } catch (e) { ctx.restore(); return; }
            ctx.restore(); ctx.setTransform(1, 0, 0, 1, 0, 0);
            var im = ctx.getImageData(x0, y0, x1 - x0, y1 - y0).data, clip = null; try { var mm = car().maskFor(pn); clip = mm && mm.mask; } catch (e2) {}
            var w = x1 - x0, y, x;
            for (y = 0; y < y1 - y0; y++) for (x = 0; x < w; x++) { if (im[(y * w + x) * 4 + 3] > 127) { var gi = (y0 + y) * Wd + (x0 + x); if (!clip || clip[gi]) { out[gi] = 255; any = true; } } }
        });
        if (!any) return { mask: out, empty: true, desc: item.kind.replace('_', ' ') };
        return { mask: out, desc: item.kind.replace('_', ' ') + ' on the ' + partList(item).join(' and ') };
    }

    // HELPER FIX PASS 7 2026-10-05: outline = part mask AND NOT (part mask eroded by r px), r = w * 512 (thin 6 px, default 10, thick 18 on a 2048 sheet). Separable box erosion with prefix sums, inside the part box only.
    // HELPER FIX PASS 8 2026-10-05: a PSD layer's own art as a sheet mask (alpha > 0), for "<layer> ... with a silver accent" = a line along the edges of that art
    function layerMask(name) {
        try {
            var L = (typeof _psdLayers !== 'undefined' && _psdLayers) ? _psdLayers : [], n = String(name || '').trim().toLowerCase(), l = L.filter(function (x) { return x && String(x.name || '').trim().toLowerCase() === n; })[0]; if (!l) return null;
            var d = dims(), u = getZoneSourceLayersUnionMask({ sourceLayers: [l.id], sourceLayer: l.id }, d[0], d[1]); return u && u.union ? u.union : null;
        } catch (e) { return null; }
    }
    function outlineMask(item, only, cols) {
        if (only && cols.indexOf(only) === -1) return null;
        var d = dims(), Wd = d[0], Hd = d[1], out = new Uint8Array(Wd * Hd), any = false, r = Math.max(3, Math.round(num(item.w, 0.02) * 512 * Wd / 2048));
        (item.layer ? ['@layer'] : partList(item)).forEach(function (pn) {
            var mm = null; try { mm = pn === '@layer' ? { mask: layerMask(item.layer) } : car().maskFor(pn); } catch (e) { mm = null; } var m = mm && mm.mask; if (!m) return;
            var F = pn === '@layer' ? null : frame(pn), b = F ? F.box : [0, 0, Wd, Hd], x0 = Math.max(0, Math.floor(b[0]) - 1), y0 = Math.max(0, Math.floor(b[1]) - 1), x1 = Math.min(Wd, Math.ceil(b[2]) + 1), y1 = Math.min(Hd, Math.ceil(b[3]) + 1), w = x1 - x0, h = y1 - y0, x, y, k;
            if (w <= 0 || h <= 0) return;
            var hz = new Uint8Array(w * h), row = new Int32Array(w + 1), col = new Int32Array(h + 1), full = 2 * r + 1;
            for (y = 0; y < h; y++) { row[0] = 0; for (x = 0; x < w; x++) row[x + 1] = row[x] + (m[(y0 + y) * Wd + x0 + x] ? 1 : 0); for (x = 0; x < w; x++) { var a = x - r, c = x + r + 1; if (a < 0 || c > w) continue; if (row[c] - row[a] === full) hz[y * w + x] = 1; } }
            for (x = 0; x < w; x++) { col[0] = 0; for (y = 0; y < h; y++) col[y + 1] = col[y] + hz[y * w + x]; for (y = 0; y < h; y++) { var gi = (y0 + y) * Wd + x0 + x; if (!m[gi]) continue; var a2 = y - r, c2 = y + r + 1, core = a2 >= 0 && c2 <= h && col[c2] - col[a2] === full; if (!core) { out[gi] = 255; any = true; } } }
        });
        if (!any) return { mask: out, empty: true, desc: 'outline' };
        return { mask: out, desc: 'a line along the edge of the ' + (item.layer ? item.layer + ' art' : partList(item).join(' and ')) };
    }
    // ------------------------------------------------------------------ HELPER V3 S5 2026-10-05 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md 2.2, stage S5): stroke px, ring sides,
    // element / zone outlines and the SEAM (pinline between two regions). Additive only: an item without stroke_px / sides / element / zone keeps the exact old outline pixels.
    function pxOf(item, d, dflt) { var v = (item && item.stroke_px != null) ? num(item.stroke_px, dflt) : ((item && item.w != null) ? num(item.w, 0.02) * 512 : dflt); return clamp(v, 1, 200) * d[0] / 2048; }
    function bboxOf(m, Wd, Hd) { var x0 = Wd, y0 = Hd, x1 = -1, y1 = -1, x, y; for (y = 0; y < Hd; y++) { var row = y * Wd, any = false; for (x = 0; x < Wd; x++) if (m[row + x]) { any = true; if (x < x0) x0 = x; if (x > x1) x1 = x; } if (any) { if (y < y0) y0 = y; y1 = y; } } return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1]; }
    function morph(m, Wd, Hd, r, bb, erodeIt) {          // square dilation (any pixel in the (2r+1)^2 window) or erosion (all of them), separable running counts, only around the mask's box
        var out = new Uint8Array(Wd * Hd); r = Math.max(0, Math.round(r)); if (!bb) bb = bboxOf(m, Wd, Hd); if (!bb) return out;
        var x0 = erodeIt ? bb[0] : Math.max(0, bb[0] - r), y0 = erodeIt ? bb[1] : Math.max(0, bb[1] - r), x1 = erodeIt ? bb[2] : Math.min(Wd, bb[2] + r), y1 = erodeIt ? bb[3] : Math.min(Hd, bb[3] + r), w = x1 - x0, h = y1 - y0, full = 2 * r + 1, hz = new Uint8Array(w * h), x, y, c, row, ad, rm;
        for (y = 0; y < h; y++) { row = (y0 + y) * Wd + x0; c = 0; for (x = -r; x < w; x++) { ad = x + r; if (ad < w && m[row + ad]) c++; rm = x - r - 1; if (rm >= 0 && m[row + rm]) c--; if (x >= 0 && (erodeIt ? c === full : c > 0)) hz[y * w + x] = 1; } }
        for (x = 0; x < w; x++) { c = 0; for (y = -r; y < h; y++) { ad = y + r; if (ad < h && hz[ad * w + x]) c++; rm = y - r - 1; if (rm >= 0 && hz[rm * w + x]) c--; if (y >= 0 && (erodeIt ? c === full : c > 0)) out[(y0 + y) * Wd + x0 + x] = 255; } }
        return out;
    }
    function dilate(m, Wd, Hd, r, bb) { return morph(m, Wd, Hd, r, bb, false); }
    function erode(m, Wd, Hd, r, bb) { return morph(m, Wd, Hd, r, bb, true); }
    function paintable() { try { var C = car(); var pm = C && C.paintableMask ? C.paintableMask(true) : null; return pm && pm.length ? pm : null; } catch (e) { return null; } }
    function elementMask(kind) {          // the numbers / sponsors ART: their PSD layers (by role) on a layered file, else what SpbProElements found on a flat paint
        kind = String(kind || '').toLowerCase().split(':')[0]; var re = kind === 'numbers' ? /^numbers$/i : (kind === 'sponsors' || kind === 'logos' ? /logo|sponsor|decal/i : (kind === 'stripes' ? /tape|stripe/i : null)); if (!re) return null;
        try {
            var rl = (car() && car().roles) ? car().roles() : [], ids = rl.filter(function (x) { return x.visible !== false && re.test(String(x.role || '')); }).map(function (x) { return x.id; });
            if (ids.length && typeof getZoneSourceLayersUnionMask === 'function') { var d = dims(), u = getZoneSourceLayersUnionMask({ sourceLayers: ids, sourceLayer: ids[0] }, d[0], d[1]); if (u && u.union) return u.union; }
        } catch (e) {}
        try { var em = W.SpbProElements && W.SpbProElements.maskFor(kind); return em && em.mask ? em.mask : null; } catch (e2) { return null; }
    }
    function zoneMask(ref) {          // the pixels a zone is limited to: its region mask (parts, graphics, boxes) or its PSD layers
        try {
            var Z = (typeof zones !== 'undefined' && zones) ? zones : [], s = String(ref), z = Z.filter(function (q) { return q && (String(q.id) === s || String(q.name || '') === s); })[0] || (/^\d+$/.test(s) ? Z[Number(s)] : null); if (!z) return null;
            if (z.useRegion && z.regionMask && z.regionMask.length) return z.regionMask;
            var ids = Array.isArray(z.sourceLayers) && z.sourceLayers.length ? z.sourceLayers : (z.sourceLayer ? [z.sourceLayer] : []);
            if (ids.length && typeof getZoneSourceLayersUnionMask === 'function') { var d = dims(), u = getZoneSourceLayersUnionMask({ sourceLayers: ids, sourceLayer: ids[0] }, d[0], d[1]); return u && u.union ? u.union : null; }
        } catch (e) {}
        return null;
    }
    function ring(m, Wd, Hd, sides, r, gap) {
        var bb = bboxOf(m, Wd, Hd), out = new Uint8Array(Wd * Hd), k, a, b; if (!bb) return out;
        if (sides === 'outer') { a = dilate(m, Wd, Hd, gap + r, bb); b = gap > 0 ? dilate(m, Wd, Hd, gap, bb) : m; for (k = 0; k < out.length; k++) if (a[k] && !b[k]) out[k] = 255; }
        else if (sides === 'both') { a = dilate(m, Wd, Hd, Math.ceil(r / 2), bb); b = erode(m, Wd, Hd, Math.floor(r / 2), bb); for (k = 0; k < out.length; k++) if (a[k] && !b[k]) out[k] = 255; }
        else { b = erode(m, Wd, Hd, r, bb); for (k = 0; k < out.length; k++) if (m[k] && !b[k]) out[k] = 255; }
        return out;
    }
    function ringMask(item, only, cols) {
        if (only && cols.indexOf(only) === -1) return null;
        var d = dims(), Wd = d[0], Hd = d[1], r = Math.max(1, Math.round(pxOf(item, d, 10))), gap = Math.max(0, Math.round(num(item.gap_px, item.element ? 2 : 0) * Wd / 2048)), srcs = [], out = new Uint8Array(Wd * Hd), any = false, k, what;
        if (item.element) { srcs.push(elementMask(item.element)); what = 'the ' + String(item.element).split(':')[0]; }
        else if (item.zone != null) { srcs.push(zoneMask(item.zone)); what = 'that zone'; }
        else if (item.layer) { srcs.push(layerMask(item.layer)); what = 'the ' + item.layer + ' art'; }
        else { partList(item).forEach(function (pn) { var mm = null; try { mm = car().maskFor(pn); } catch (e) {} srcs.push(mm && mm.mask); }); what = 'the ' + partList(item).join(' and '); }
        var sides = item.sides || ((item.element || item.zone != null) ? 'outer' : 'inner'), clip = (sides === 'inner') ? null : paintable();
        srcs.forEach(function (m) { if (!m) return; var rg = ring(m, Wd, Hd, sides, r, gap); for (k = 0; k < out.length; k++) if (rg[k] && (!clip || clip[k])) { out[k] = 255; any = true; } });
        var px = Math.round(r * 2048 / Wd), desc = 'a ' + px + ' px line ' + (sides === 'outer' ? 'around ' : 'along the edge of ') + what;
        return any ? { mask: out, desc: desc, px: px } : { mask: out, empty: true, desc: desc, px: px };
    }
    // the visible paint (what the buyer sees, zones applied): the live preview, else the source paint
    function visiblePaint() {
        try { var img = document.getElementById('livePreviewImg'); if (img && img.complete && img.naturalWidth > 32) { var cv = document.createElement('canvas'); cv.width = img.naturalWidth; cv.height = img.naturalHeight; var cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(img, 0, 0); return { d: cx.getImageData(0, 0, cv.width, cv.height).data, w: cv.width, h: cv.height, src: 'preview' }; } } catch (e) {}
        try { if (typeof paintImageData !== 'undefined' && paintImageData) return { d: paintImageData.data, w: paintImageData.width, h: paintImageData.height, src: 'paint' }; } catch (e2) {}
        return null;
    }
    var _famCache = {};
    function famOfRgb(r, g, b) {
        var key = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3); if (_famCache[key] !== undefined) return _famCache[key];
        var hx = '#' + [r, g, b].map(function (v) { return ('0' + ((v >> 3) * 8 + 4).toString(16)).slice(-2); }).join(''), f = null;
        try { f = W.SpbProEdit && W.SpbProEdit.familyOf ? W.SpbProEdit.familyOf(hx) : null; } catch (e) { f = null; }
        _famCache[key] = f; return f;
    }
    var _seamSides = {};
    // HELPER V3 S5 2026-10-05 (in-app check on the owner's ARCA): colour sides read from the 1024 live preview were blocky and wrong (the white bars on the pink
    // panel got the pinline, the pink/seafoam edge did not). A colour a ZONE paints is now that zone's VISIBLE pixels at full size: the top visible PSD layer
    // at each pixel (decals above win), limited to the zone's layers / region mask. Only colours no zone paints fall back to the source paint, then the preview.
    var _own = { key: null, own: null };
    function layerOwners(Wd, Hd) {          // index (in _psdLayers, bottom -> top) of the top visible non-template layer at each pixel, -1 = none
        var L = (typeof _psdLayers !== 'undefined' && _psdLayers) ? _psdLayers : [], rev = ''; try { rev = String(typeof _layerCompositeRevision !== 'undefined' ? _layerCompositeRevision : '') + ':' + String(W._spbLayerRev || 0); } catch (e) {}
        var key = rev + ':' + Wd + 'x' + Hd + ':' + L.map(function (l) { return l ? (l.id + (l.visible === false ? 'h' : 'v')) : '-'; }).join(','); if (_own.key === key) return _own.own;
        if (typeof getLayerVisibleContributionMask !== 'function' || !L.length) return null;
        var own = new Int16Array(Wd * Hd), i, any = false; for (i = 0; i < own.length; i++) own[i] = -1;
        L.forEach(function (l, li) {
            if (!l || !l.img || l.visible === false || /^(wire|mask|car[ _]?mandatory)$/i.test(String(l.name || '').trim())) return;
            var m = null; try { m = getLayerVisibleContributionMask(l, Wd, Hd); } catch (e) { m = null; } if (!m || m.length !== own.length) return;
            for (i = 0; i < own.length; i++) if (m[i] > 127) { own[i] = li; any = true; }
        });
        _own.key = key; _own.own = any ? own : null; return _own.own;
    }
    function zoneColourSide(s, Wd, Hd) {
        var Z = []; try { Z = zones; } catch (e) { return null; } var t = s.colour && hexOk(s.colour) ? s.colour.toLowerCase() : null, fams = s.family ? [].concat(s.family).map(lc) : null, hits = [];
        Z.forEach(function (z) {
            if (!z || z.muted || z.baseColorMode !== 'solid' || !hexOk(z.baseColor) || z._graphic) return; var c = String(z.baseColor).toLowerCase(), m = false;
            if (t) { var a = [parseInt(c.substr(1, 2), 16), parseInt(c.substr(3, 2), 16), parseInt(c.substr(5, 2), 16)], b = [parseInt(t.substr(1, 2), 16), parseInt(t.substr(3, 2), 16), parseInt(t.substr(5, 2), 16)]; m = (a[0] - b[0]) * (a[0] - b[0]) * 0.3 + (a[1] - b[1]) * (a[1] - b[1]) * 0.59 + (a[2] - b[2]) * (a[2] - b[2]) * 0.11 < 900; }
            else if (fams) m = fams.indexOf(famOfRgb(parseInt(c.substr(1, 2), 16), parseInt(c.substr(3, 2), 16), parseInt(c.substr(5, 2), 16))) !== -1;
            if (m) hits.push(z);
        });
        if (!hits.length) return null; var own = layerOwners(Wd, Hd); if (!own) return null;
        var L = _psdLayers, out = new Uint8Array(Wd * Hd), any = false, i;
        hits.forEach(function (z) {
            var ids = []; try { ids = W.zoneSourceLayerIds ? W.zoneSourceLayerIds(z) : (z.sourceLayers || []); } catch (e) {} if (!ids || !ids.length) return;
            var body = {}; try { (car() && car().roles ? car().roles() : []).forEach(function (r) { if (/body paint/i.test(String(r.role || ''))) body[r.id] = 1; }); } catch (e1) {} if (Object.keys(body).length && ids.some(function (id) { return !body[id]; })) return;          // a colour on the BODY: a zone on decal / number layers (e.g. a pink number fill) is not a side
            var set = {}; ids.forEach(function (id) { for (var k = 0; k < L.length; k++) if (L[k] && L[k].id === id) set[k] = 1; });
            var rm = z.useRegion && z.regionMask && z.regionMask.length === out.length ? z.regionMask : null;
            for (i = 0; i < out.length; i++) if (own[i] >= 0 && set[own[i]] && (!rm || rm[i])) { out[i] = 255; any = true; }
        });
        return any ? out : null;
    }
    function sourceColourSide(s, Wd, Hd) {          // the colour in the SOURCE paint, only where the top layer is not recoloured by a solid / gradient zone (there the source colour is not what shows)
        var sp = sourcePaint(); if (!sp || sp.w !== Wd || sp.h !== Hd) return colourMask(s, Wd, Hd, sp);
        var cm = colourMask(s, Wd, Hd, sp); if (!cm) return null; var own = layerOwners(Wd, Hd); if (!own) return cm;
        var L = _psdLayers, rec = {}, i, any = false; try { zones.forEach(function (z) { if (!z || z.muted || z._graphic || (z.baseColorMode !== 'solid' && z.baseColorMode !== 'gradient')) return; var ids = W.zoneSourceLayerIds ? W.zoneSourceLayerIds(z) : []; (ids || []).forEach(function (id) { for (var k = 0; k < L.length; k++) if (L[k] && L[k].id === id) rec[k] = 1; }); }); } catch (e) {}
        for (i = 0; i < cm.length; i++) { if (cm[i] && (own[i] < 0 || rec[own[i]])) cm[i] = 0; else if (cm[i]) any = true; }
        return any ? cm : null;
    }
    function sourcePaint() { try { if (typeof paintImageData !== 'undefined' && paintImageData) return { d: paintImageData.data, w: paintImageData.width, h: paintImageData.height, src: 'paint' }; } catch (e) {} return null; }
    function colourMask(s, Wd, Hd, vpIn) {
        var vp = vpIn || visiblePaint(); if (!vp) return null;
        var pw = vp.w, ph = vp.h, dd = vp.d, small = new Uint8Array(pw * ph), i, fams = s.family ? [].concat(s.family).map(lc) : null, t = s.colour && hexOk(s.colour) ? [parseInt(s.colour.substr(1, 2), 16), parseInt(s.colour.substr(3, 2), 16), parseInt(s.colour.substr(5, 2), 16)] : null, tol = num(s.tol, 48), t2 = tol * tol, any = false, famT = t ? famOfRgb(t[0], t[1], t[2]) : null;
        for (i = 0; i < pw * ph; i++) {
            var R = dd[i * 4], G = dd[i * 4 + 1], B = dd[i * 4 + 2]; if (dd[i * 4 + 3] < 128) continue;
            if (t) { var dr = R - t[0], dg = G - t[1], db = B - t[2]; if (dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11 < t2 && (!famT || famOfRgb(R, G, B) === famT)) { small[i] = 1; any = true; } }          // HELPER V3 S5: same colour family too (the grey anti-aliased edge of a white bar on black is 'near' a pastel seafoam by distance alone)
            else if (fams && fams.indexOf(famOfRgb(R, G, B)) !== -1) { small[i] = 1; any = true; }
        }
        if (!any) return null;
        var out = new Uint8Array(Wd * Hd), x, y; for (y = 0; y < Hd; y++) { var sy = Math.min(ph - 1, Math.floor(y * ph / Hd)) * pw; for (x = 0; x < Wd; x++) if (small[sy + Math.min(pw - 1, Math.floor(x * pw / Wd))]) out[y * Wd + x] = 255; }
        return out;
    }
    function sideMask(s, Wd, Hd) {
        if (!s) return null; var u = null, i;
        if (s.part || s.parts) { [].concat(s.part || s.parts).forEach(function (pn) { var mm = null; try { mm = car().maskFor(pn); } catch (e) {} if (mm && mm.mask) { if (!u) u = new Uint8Array(Wd * Hd); for (i = 0; i < u.length; i++) if (mm.mask[i]) u[i] = 255; } }); return u; }
        if (s.layer) return layerMask(s.layer);
        if (s.element) return elementMask(s.element);
        if (s.zone != null) return zoneMask(s.zone);
        if (s.rest) { var pm = paintable(); if (!pm) return null; var ex = sideMask({ parts: [].concat(s.rest) }, Wd, Hd), o = new Uint8Array(Wd * Hd); for (i = 0; i < o.length; i++) if (pm[i] && !(ex && ex[i])) o[i] = 255; return o; }
        if (s.colour || s.family) {          // colour sides come from the VISIBLE paint once, then are kept for this session: the line itself must not move them when it is redrawn thinner / thicker
            var key = JSON.stringify(s) + '|' + Wd; if (_seamSides[key] && !s.fresh) return _seamSides[key];
            var zs = zoneColourSide(s, Wd, Hd), sp = sourceColourSide(s, Wd, Hd), cm = null, q;
            if (zs && sp) { cm = zs; for (q = 0; q < cm.length; q++) if (sp[q]) cm[q] = 255; } else cm = zs || sp || colourMask(s, Wd, Hd);
            if (cm) _seamSides[key] = cm; return cm;          // HELPER V3 S5: zone-painted colour first (crisp, visible), then the source paint, then the preview
        }
        return null;
    }
    function sideName(s) { if (!s) return '?'; if (s.part || s.parts) return [].concat(s.part || s.parts).join(' + '); if (s.layer) return s.layer + ' art'; if (s.element) return s.element; if (s.rest) return 'rest of the car'; if (s.family) return [].concat(s.family).join('/'); if (s.colour) return s.colour; if (s.zone != null) return 'zone ' + s.zone; return '?'; }
    function seamCheck(item) {
        if (!item.a || !item.b) return 'a seam needs both sides: a and b ({part} | {layer} | {zone} | {element} | {colour} | {family} | {rest})';
        var bad = null; if (item.part) partList(item).forEach(function (pn) { if (!bad && car() && car().findIsland && !car().findIsland(pn)) bad = 'unknown part "' + pn + '"'; });
        [item.a, item.b].forEach(function (s) { [].concat(s.part || s.parts || []).forEach(function (pn) { if (!bad && car() && car().findIsland && !car().findIsland(pn)) bad = 'unknown part "' + pn + '"'; }); if (!bad && s.layer && !layerMask(s.layer)) bad = 'unknown layer "' + s.layer + '"'; });
        return bad;
    }
    function seamMask(item, only, cols) {
        if (only && cols.indexOf(only) === -1) return null;
        var d = dims(), Wd = d[0], Hd = d[1], w = Math.max(1, pxOf(item, d, 6)), h = Math.max(1, Math.ceil(w / 2)), A = sideMask(item.a, Wd, Hd), B = sideMask(item.b, Wd, Hd), out = new Uint8Array(Wd * Hd), any = false, k;
        var desc = 'a ' + Math.round(w * 2048 / Wd) + ' px line where the ' + sideName(item.a) + ' meets the ' + sideName(item.b);
        if (!A || !B) return { mask: out, empty: true, desc: desc + ' (' + (!A ? sideName(item.a) : sideName(item.b)) + ' not found on the paint)' };
        var dA = dilate(A, Wd, Hd, h), dB = dilate(B, Wd, Hd, h), clip = null, pm = paintable();
        if (item.part) clip = sideMask({ parts: partList(item) }, Wd, Hd);
        for (k = 0; k < out.length; k++) if (dA[k] && dB[k] && (!clip || clip[k]) && (!pm || pm[k])) { out[k] = 255; any = true; }
        return any ? { mask: out, desc: desc } : { mask: out, empty: true, desc: desc + ' (they do not touch on this car)' };
    }
    W.SpbGraphics = { KINDS: KINDS, check: check, maskFor: maskFor, colours: colours, partList: partList, frame: frame,
        S5: { layerOwners: layerOwners, zoneColourSide: zoneColourSide, pxOf: pxOf, bboxOf: bboxOf, dilate: dilate, erode: erode, ring: ring, ringMask: ringMask, seamMask: seamMask, sideMask: sideMask, elementMask: elementMask, zoneMask: zoneMask, visiblePaint: visiblePaint, famOfRgb: famOfRgb, forgetSeams: function () { _seamSides = {}; return true; } } };          // HELPER V3 S5 2026-10-05: S5 helpers (additive)
})();
