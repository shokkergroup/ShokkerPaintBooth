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
            params: 'w line width as a fraction of the sheet/4 (0.012 thin, 0.02 default, 0.035 thick)',
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
        }
    };

    function check(item) {
        if (!item || typeof item !== 'object') return 'a graphic needs to be an object';
        if (!KINDS[item.kind]) return 'unknown graphic kind "' + item.kind + '": use ' + Object.keys(KINDS).join(' | ');
        if (!colours(item).length) return 'a graphic needs colour (or colours) as #rrggbb';
        var bad = null; partList(item).forEach(function (pn) { if (!bad && car() && car().findIsland && !car().findIsland(pn)) bad = 'unknown part "' + pn + '"'; });
        return bad;
    }

    var _cv = null;
    function canvas(d) { if (!_cv || _cv.width !== d[0] || _cv.height !== d[1]) { _cv = document.createElement('canvas'); _cv.width = d[0]; _cv.height = d[1]; } return _cv; }

    // render one graphic item restricted to ONE colour (the colour a zone paints) into a full-sheet mask
    function maskFor(g) {
        var item = g && g.item ? g.item : g, only = lc(g && g.only), cols = colours(item), err = check(item); if (err) return null;
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
    function outlineMask(item, only, cols) {
        if (only && cols.indexOf(only) === -1) return null;
        var d = dims(), Wd = d[0], Hd = d[1], out = new Uint8Array(Wd * Hd), any = false, r = Math.max(3, Math.round(num(item.w, 0.02) * 512 * Wd / 2048));
        partList(item).forEach(function (pn) {
            var mm = null; try { mm = car().maskFor(pn); } catch (e) { mm = null; } var m = mm && mm.mask; if (!m) return;
            var F = frame(pn), b = F ? F.box : [0, 0, Wd, Hd], x0 = Math.max(0, Math.floor(b[0]) - 1), y0 = Math.max(0, Math.floor(b[1]) - 1), x1 = Math.min(Wd, Math.ceil(b[2]) + 1), y1 = Math.min(Hd, Math.ceil(b[3]) + 1), w = x1 - x0, h = y1 - y0, x, y, k;
            if (w <= 0 || h <= 0) return;
            var hz = new Uint8Array(w * h), row = new Int32Array(w + 1), col = new Int32Array(h + 1), full = 2 * r + 1;
            for (y = 0; y < h; y++) { row[0] = 0; for (x = 0; x < w; x++) row[x + 1] = row[x] + (m[(y0 + y) * Wd + x0 + x] ? 1 : 0); for (x = 0; x < w; x++) { var a = x - r, c = x + r + 1; if (a < 0 || c > w) continue; if (row[c] - row[a] === full) hz[y * w + x] = 1; } }
            for (x = 0; x < w; x++) { col[0] = 0; for (y = 0; y < h; y++) col[y + 1] = col[y] + hz[y * w + x]; for (y = 0; y < h; y++) { var gi = (y0 + y) * Wd + x0 + x; if (!m[gi]) continue; var a2 = y - r, c2 = y + r + 1, core = a2 >= 0 && c2 <= h && col[c2] - col[a2] === full; if (!core) { out[gi] = 255; any = true; } } }
        });
        if (!any) return { mask: out, empty: true, desc: 'outline' };
        return { mask: out, desc: 'a line along the edge of the ' + partList(item).join(' and ') };
    }
    W.SpbGraphics = { KINDS: KINDS, check: check, maskFor: maskFor, colours: colours, partList: partList, frame: frame };
})();
