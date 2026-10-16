/* [SPB-TFX3 2026-10-10 PORT-4 Brush dynamics, lane TOOLS-FIX-3]
 * Port of PhotoCraft crates/paint/src/dynamics.rs (DabBuilder: Shape Dynamics size jitter with a minimum diameter, Scattering with count and count jitter,
 * Transfer flow jitter, Colour Dynamics foreground/background + hue / saturation / brightness jitter, per-dab or per-stroke colour) to the SPB Brush.
 *
 * BEFORE (measured, fix3/dyn_before_1920.json): every dab of the Brush was identical and sat exactly on the stroke line: spacing, smoothing, stabilizer, hardness,
 * flow and pen pressure existed, but there was no way to paint speckle, mud, dust, overspray, flecks or confetti except by hand-dotting thousands of
 * clicks. (A vestigial window.brushJitter global had no control and nothing read it.)
 *
 * AFTER: a "Dynamics" button in the Brush options opens a panel: size jitter + minimum size, scatter (0-400 % of the brush radius) with count and
 * count jitter, flow jitter, foreground/background mix, hue / saturation / brightness jitter (per dab or once per stroke), seven presets (Natural hand,
 * Speckle, Mud splatter, Dust and overspray, Confetti, Two-tone flecks, Off) and a live preview of the stroke. Every extra dab goes through the SAME layer
 * dab path as a normal dab (selection clip, alpha lock, stroke opacity cap, undo), so one stroke is still ONE undo step and the opacity cap still holds.
 * Layer brush, and (TFX4 2026-10-10) the zone brush too: a zone is a mask, so the colour group does nothing there. Eraser, pencil and every other tool are untouched.
 *
 * Kill switch: window.SPB_TFX3_OFF = true (or localStorage SPB_TFX3_OFF='1') -> button hidden, wrapper passes straight through, old behaviour byte for byte.
 */
(function (root, factory) {
    var api = factory(root);
    if (typeof module === 'object' && module.exports) module.exports = api;       // node tests import the pure dab maths
    if (root && root.document) root.SPBTfx3Dynamics = api;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
    'use strict';
    var isBrowser = !!(root && root.document);
    if (isBrowser) { try { if (root.SPB_TFX3_OFF !== true && root.localStorage.getItem('SPB_TFX3_OFF') === '1') root.SPB_TFX3_OFF = true; } catch (_e) { } }
    var api = {};
    function off() { return !!(root && root.SPB_TFX3_OFF === true); }
    // [SPB-TFX4 2026-10-10 lane TOOLS-FIX-4] kill switch for the TFX4 changes in this file (zone-brush dynamics, Mirror Paint single jitter, stroke identity for the taper):
    // window.SPB_TFX4_OFF = true or localStorage SPB_TFX4_OFF = '1' -> the TFX3 behaviour byte for byte.
    if (isBrowser) { try { if (root.SPB_TFX4_OFF !== true && root.localStorage.getItem('SPB_TFX4_OFF') === '1') root.SPB_TFX4_OFF = true; } catch (_e) { } }
    function off4() { return !!(root && root.SPB_TFX4_OFF === true); }
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

    // ------------------------------------------------------------------ pure maths (port of DabBuilder)
    var DEF = { sizeJit: 0, sizeMin: 20, scatter: 0, count: 1, countJit: 0, flowJit: 0, fgbg: 0, hueJit: 0, satJit: 0, briJit: 0, perDab: true, taperLen: 0, taperEnd: 0, taperGrow: false, taperFlow: false };
    var BOOL = { perDab: 1, taperGrow: 1, taperFlow: 1 };
    var LIM = { sizeJit: [0, 100], sizeMin: [1, 100], scatter: [0, 400], count: [1, 8], countJit: [0, 100], flowJit: [0, 100], fgbg: [0, 100], hueJit: [0, 100], satJit: [0, 100], briJit: [0, 100], taperLen: [0, 3000], taperEnd: [0, 100] };
    function norm(p) {
        var o = {}; p = p || {};
        for (var k in DEF) {
            if (BOOL[k]) { o[k] = p[k] === undefined ? DEF[k] : !!p[k]; continue; }
            var v = Number(p[k]); if (!isFinite(v)) v = DEF[k];
            o[k] = clamp(k === 'count' ? Math.round(v) : v, LIM[k][0], LIM[k][1]);
        }
        return o;
    }
    function isActive(p) { return !!(p && (p.sizeJit > 0 || p.scatter > 0 || p.count > 1 || p.flowJit > 0 || p.fgbg > 0 || p.hueJit > 0 || p.satJit > 0 || p.briJit > 0 || p.taperLen > 0)); }
    function colourActive(p) { return !!(p && (p.fgbg > 0 || p.hueJit > 0 || p.satJit > 0 || p.briJit > 0)); }
    function mulberry32(a) { a = a >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; var t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function hexToRgb(h) {
        h = String(h || '#000000'); if (h.charAt(0) === '#') h = h.slice(1);
        if (h.length === 3) h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2);
        var n = parseInt(h.slice(0, 6), 16); if (!isFinite(n)) n = 0;
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    function rgbToHex(c) { return '#' + [0, 1, 2].map(function (i) { var s = clamp(Math.round(c[i]), 0, 255).toString(16); return s.length < 2 ? '0' + s : s; }).join(''); }
    function rgbToHsv(c) {
        var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0;
        if (d > 0) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
        return [h, mx === 0 ? 0 : d / mx, mx];
    }
    function hsvToRgb(h, s, v) {
        h = ((h % 360) + 360) % 360; var c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c, r = 0, g = 0, b = 0;
        if (h < 60) { r = c; g = x; } else if (h < 120) { r = x; g = c; } else if (h < 180) { g = c; b = x; } else if (h < 240) { g = x; b = c; } else if (h < 300) { r = x; b = c; } else { r = c; b = x; }
        return [(r + m) * 255, (g + m) * 255, (b + m) * 255];
    }
    function rolls(rnd) { return { t: rnd(), h: rnd() * 2 - 1, s: rnd() * 2 - 1, v: rnd() * 2 - 1 }; }
    // colour of one dab: foreground mixed towards the background by fgbg, then hue / saturation / brightness jitter (PhotoCraft dynamic_color)
    function dabColour(p, fg, bg, ro) {
        var c = fg;
        if (p.fgbg > 0 && bg) { var t = ro.t * p.fgbg / 100; c = [fg[0] + (bg[0] - fg[0]) * t, fg[1] + (bg[1] - fg[1]) * t, fg[2] + (bg[2] - fg[2]) * t]; }
        if (p.hueJit > 0 || p.satJit > 0 || p.briJit > 0) {
            var hsv = rgbToHsv(c);
            var h = hsv[0] + ro.h * p.hueJit / 100 * 180, s = clamp(hsv[1] + ro.s * p.satJit / 100, 0, 1), v = clamp(hsv[2] + ro.v * p.briJit / 100, 0, 1);
            if (hsv[1] < 0.02 && p.hueJit > 0 && p.satJit <= 0) s = 0;        // a grey stays grey unless saturation is allowed to vary
            c = hsvToRgb(h, s, v);
        }
        return [clamp(Math.round(c[0]), 0, 255), clamp(Math.round(c[1]), 0, 255), clamp(Math.round(c[2]), 0, 255)];
    }
    // Taper (PhotoCraft Control::Fade): size (and optionally flow) runs from full to the end size over taperLen canvas px of stroke length; Grow runs it backwards
    function taperK(p, dist) {
        if (!(p.taperLen > 0)) return 1;
        var t = clamp((dist || 0) / p.taperLen, 0, 1), e = p.taperEnd / 100;
        return p.taperGrow ? e + t * (1 - e) : 1 - t * (1 - e);
    }
    // One brush step -> the dabs to paint. radius = nominal dab radius; strokeRolls = the colour rolls of this stroke (used when perDab is false)
    function dabsFor(p, rnd, x, y, radius, fg, bg, fx, fy, strokeRolls, dist) {
        p = norm(p); var tk = taperK(p, dist);
        var n = Math.max(1, Math.round(p.count * (1 - rnd() * p.countJit / 100))), out = [], minK = p.sizeMin / 100;
        for (var i = 0; i < n; i++) {
            var k = (1 - rnd() * (p.sizeJit / 100) * (1 - minK)) * tk;
            var ox = p.scatter > 0 ? (rnd() * 2 - 1) * p.scatter / 100 * radius : 0, oy = p.scatter > 0 ? (rnd() * 2 - 1) * p.scatter / 100 * radius : 0;
            var fl = (1 - rnd() * p.flowJit / 100) * (p.taperFlow ? tk : 1);
            var ro = (p.perDab || !strokeRolls) ? rolls(rnd) : strokeRolls;
            out.push({ x: x + ox, y: y + oy, fx: isFinite(fx) ? fx + ox : NaN, fy: isFinite(fy) ? fy + oy : NaN, r: Math.max(0.5, radius * k), flowK: fl, rgb: colourActive(p) ? dabColour(p, fg, bg, ro) : fg });
        }
        return out;
    }
    api.DEF = DEF; api.norm = norm; api.isActive = isActive; api.dabsFor = dabsFor; api.dabColour = dabColour; api.taperK = taperK; api.mulberry32 = mulberry32; api.hexToRgb = hexToRgb; api.rgbToHex = rgbToHex;
    api.rgbToHsv = rgbToHsv; api.hsvToRgb = hsvToRgb; api.rolls = rolls;
    if (!isBrowser) return api;

    // ------------------------------------------------------------------ state
    var KEY = 'spb_tfx3_dyn_v1';
    var state = { p: norm(), preset: 'Off' };
    function load() { try { var j = JSON.parse(root.localStorage.getItem(KEY) || 'null'); if (j && j.p) { state.p = norm(j.p); state.preset = j.preset || 'Custom'; } } catch (_e) { } }
    function save() { try { root.localStorage.setItem(KEY, JSON.stringify(state)); } catch (_e) { } }
    var rng = mulberry32((Date.now() ^ 0x5bd1e995) >>> 0), strokeRolls = null, lastDabAt = 0;
    var lastX = NaN, lastY = NaN, lastFx = NaN, lastFy = NaN, strokeDist = 0;                                    // stroke length so far (canvas px), for the taper
    var fixedSeed = null;                                                           // tests: the same seed for every stroke
    var seenKey = null;                                                             // [TFX4] identity of the stroke the app announced (window._spbZoneKey, new at every brush/erase mousedown)
    var zoneRound = true;                                                           // [TFX4] zone brush: round tip -> fractional dab radius is fine, other tips need whole pixels
    function newStroke() { rng = mulberry32(fixedSeed != null ? fixedSeed : (((Date.now() * 2654435761) ^ (Math.random() * 4294967296)) >>> 0)); strokeRolls = rolls(rng); lastX = NaN; lastY = NaN; lastFx = NaN; lastFy = NaN; strokeDist = 0; }
    newStroke();
    function mode() { try { return (typeof canvasMode !== 'undefined') ? canvasMode : root.canvasMode; } catch (_e) { return root.canvasMode; } }
    function inLayerMode() { try { return typeof isLayerToolbarMode === 'function' && isLayerToolbarMode(); } catch (_e) { return false; } }
    function fgHex() { try { return (typeof _foregroundColor === 'string') ? _foregroundColor : '#000000'; } catch (_e) { return '#000000'; } }
    function bgHex() { try { return (typeof _backgroundColor === 'string') ? _backgroundColor : '#ffffff'; } catch (_e) { return '#ffffff'; } }
    // [SPB-TFX4 2026-10-10 item 1] a zone is a mask: no colour. Same settings minus the colour group, active when any shape / count / flow / taper control is set.
    function zoneParams(p) { var o = Object.assign({}, p); o.fgbg = 0; o.hueJit = 0; o.satJit = 0; o.briJit = 0; return o; }
    function isActiveZone(p) { return isActive(zoneParams(p)); }
    // [SPB-TFX4 2026-10-10 item 3] when does a new stroke start? BEFORE: any 600 ms gap between two dabs (a slow host / a heavy first event / a held pause) reset the
    // stroke length, so 'Taper in' restarted from a point ~30 px after its start (the end of the first slow mouse event): a visible break, thickness back to ~0.
    // AFTER: the app's own stroke identity (window._spbZoneKey is replaced by _resetBrushSpacing() at every brush / erase mousedown, layer AND zone) decides;
    // the time gap is only a safety net for strokes the app never announced (and a very long one: 8 s).  SPB_TFX4_OFF restores the 600 ms rule.
    function strokeCheck(now) {
        var k = root._spbZoneKey;
        if (!off4() && k !== undefined && k !== null) {
            if (k !== seenKey) { seenKey = k; newStroke(); }
            else if (now - lastDabAt > 8000) newStroke();
        } else if (now - lastDabAt > 600) newStroke();
        lastDabAt = now;
    }

    // ------------------------------------------------------------------ one brush step -> dabs (shared by the layer brush and the zone brush)
    // paint(d) draws ONE dab d = {x, y, fx, fy, r, flowK, rgb}; it returns false when the dab could not be painted.
    var stats = { dabsIn: 0, dabsOut: 0 };
    function runStep(pp, x, y, radius, fg, bg, fxIn, fyIn, paint) {
        strokeCheck(Date.now());
        var px = lastX, py = lastY, pfx = lastFx, pfy = lastFy, d0 = strokeDist, seg = isFinite(px) ? Math.hypot(x - px, y - py) : 0, any = false;
        strokeDist += seg; lastX = x; lastY = y; lastFx = isFinite(fxIn) ? fxIn : x; lastFy = isFinite(fyIn) ? fyIn : y;
        // PORT-4c (TOOLS-FIX-3 2026-10-10): the engine spaces dabs by the NOMINAL radius, so once a taper has shrunk the dab below ~1/8 of it the stroke
        // fell apart into dots (a 'point' ended as a dotted line). Insert the missing dabs along the segment so spacing follows the shrunk size.
        var fills = [];
        if (pp.taperLen > 0 && seg > 0) {
            var sp = 25; try { sp = parseInt(document.getElementById('brushSpacing').value, 10) || 25; } catch (_e) { }
            var tkMin = Math.min(taperK(pp, d0), taperK(pp, strokeDist)), step = Math.max(1, radius * tkMin * sp / 100);
            if (seg > step * 1.5) { var n = Math.min(24, Math.ceil(seg / step)); for (var q = 1; q < n; q++) fills.push(q / n); }
        }
        function emit(ex, ey, dist, efx, efy) {
            var dabs = dabsFor(pp, rng, ex, ey, radius, fg, bg, efx, efy, strokeRolls, dist);
            stats.dabsIn++;
            for (var i = 0; i < dabs.length; i++) { stats.dabsOut++; if (paint(dabs[i]) !== false) any = true; }
        }
        for (var f = 0; f < fills.length; f++) {
            var t = fills[f];
            emit(Math.round(px + (x - px) * t), Math.round(py + (y - py) * t), d0 + seg * t, pfx + (lastFx - pfx) * t, pfy + (lastFy - pfy) * t);
        }
        emit(x, y, strokeDist, fxIn, fyIn);
        return any;
    }

    // ------------------------------------------------------------------ the hooks
    var chain = { busy: false };                       // [TFX4] true while ONE of our dabs travels through the wrappers below it (Mirror Paint's wrapper re-calls us for the mirrored dab)
    var layerTop = null, zoneTop = null, beginDone = false;
    function wrapLayer() {
        var cur = root._paintOnLayerAt;
        if (typeof cur !== 'function') return false;
        if (cur === layerTop) return true;
        if (layerTop && off4()) return true;           // kill switch: keep the TFX3 shape (wrap once, never re-wrap)
        var inner = cur;
        // [SPB-TFX4 2026-10-10 item 2] MIRROR PAINT x DYNAMICS.  BEFORE: when js/rev/symmetry wrapped _paintOnLayerAt AFTER us, its mirrored dab re-entered THIS
        // wrapper, which jittered it again (own random size / scatter / colour) and counted the mirrored call in the taper length; the mirrored stroke was a different
        // stroke.  AFTER: we are always the OUTERMOST wrapper (re-wrapped at every stroke start, see stroke begin below): the dynamics are computed ONCE per dab here and
        // each finished dab then goes down through the other wrappers (Mirror Paint mirrors exactly that dab: same size, colour, flow, scatter offset); any wrapper of ours
        // re-entered from below (chain.busy) is a plain pass-through.  The taper length only sees the real pointer.  No change needed in js/rev/symmetry.
        var W = function _tfx3DynPaintOnLayerAt(x, y, radius, color, opacity, hardness, eraseMode, pcOpts) {
            if (!off4() && chain.busy) return inner.apply(this, arguments);
            if (off() || eraseMode || !isActive(state.p) || mode() !== 'brush') return inner.apply(this, arguments);
            var fg = hexToRgb(color), bg = hexToRgb(bgHex()), self = this, colour = colourActive(state.p);
            return runStep(state.p, x, y, radius, fg, bg, pcOpts ? pcOpts.fx : NaN, pcOpts ? pcOpts.fy : NaN, function (d) {
                var po = null;
                if (pcOpts) { po = Object.assign({}, pcOpts); po.flow = clamp((pcOpts.flow == null ? 1 : pcOpts.flow) * d.flowK, 0, 1); if (isFinite(d.fx)) { po.fx = d.fx; po.fy = d.fy; } }
                var prev = chain.busy; chain.busy = true;
                try { return inner.call(self, d.x, d.y, d.r, colour ? rgbToHex(d.rgb) : color, clamp((opacity == null ? 1 : opacity) * d.flowK, 0, 1), hardness, false, po); }
                finally { chain.busy = prev; }
            });
        };
        layerTop = W; root._paintOnLayerAt = W;
        return true;
    }
    // [SPB-TFX4 2026-10-10 item 1] ZONE brush: window._zoneBrushDab(x, y, radius, val, opacity, meta) (paint-booth-3-canvas.js) = mask dab + overlay arc.  Size jitter, scatter,
    // dabs per step + count jitter, flow jitter (= mask strength) and the taper work on it exactly like on the layer brush; the colour group does not (a mask has no colour).
    // Every extra dab goes through the same function, so the zone clip (scoped-selector refinement, canvas edge), the symmetry mirror inside paintRegionCircle (same radius and
    // strength: one jittered dab, mirrored) and the one-snapshot undo (pushUndo at mousedown) apply unchanged.  Eraser (val 0) and meta.open passes straight through.
    var zoneInner = null;
    function wrapZone() {
        if (off4()) return typeof root._zoneBrushDab === 'function';
        if (zoneTop) return true;
        // the accessor goes in at once (canvas setup may run before OR long after this file: it only needs to be in place before the first stroke)
        zoneInner = (typeof root._zoneBrushDab === 'function') ? root._zoneBrushDab : null;
        zoneTop = function _tfx4DynZoneDab(x, y, radius, val, opacity, meta) {
            var inner = zoneInner;
            if (typeof inner !== 'function') return undefined;
            if (off() || off4() || val !== 1 || !isActiveZone(state.p) || mode() !== 'brush') return inner.apply(this, arguments);
            var pp = zoneParams(state.p), self = this, sub = root._spbDabSub, prevSub = sub;
            var bx = (sub && Math.round(sub.x) === x) ? sub.x : x, by = (sub && Math.round(sub.y) === y) ? sub.y : y;   // exact pointer centre (sub-pixel) when the app gave one
            try { zoneRound = !root._createBrushFootprint || root._createBrushFootprint(Math.max(1, radius)).shape === 'round'; } catch (_e) { zoneRound = true; }
            var res = runStep(pp, x, y, radius, [0, 0, 0], null, bx, by, function (d) {
                var ix = Math.round(d.fx), iy = Math.round(d.fy);                               // whole-pixel centre + the exact (sub-pixel) one, consistent for _pcSubCentre()
                root._spbDabSub = { x: d.fx, y: d.fy };
                var r = zoneRound ? d.r : Math.max(1, Math.round(d.r));
                return inner.call(self, ix, iy, r, val, clamp((opacity == null ? 1 : opacity) * d.flowK, 0, 1), meta);
            });
            root._spbDabSub = prevSub;
            return res;
        };
        // setupCanvasHandlers() re-runs (every canvas / car setup) and re-assigns window._zoneBrushDab with a fresh closure: keep our wrapper in front by turning the property
        // into an accessor whose setter only swaps the function underneath.
        try { Object.defineProperty(root, '_zoneBrushDab', { configurable: true, enumerable: true, get: function () { return zoneTop; }, set: function (fn) { if (typeof fn === 'function' && fn !== zoneTop) zoneInner = fn; } }); }
        catch (_e) { root._zoneBrushDab = zoneTop; }
        return true;
    }
    function install() {
        var a = wrapLayer(), b = wrapZone();
        if (!beginDone) {
            var origBegin = root._beginLayerPixelStroke;
            if (typeof origBegin === 'function') {
                beginDone = true;
                root._beginLayerPixelStroke = function _tfx3DynBegin() {
                    try { if (!off4()) { wrapLayer(); seenKey = root._spbZoneKey; } newStroke(); } catch (_e) { }   // [TFX4] stay the outermost wrapper before the first dab of the stroke
                    return origBegin.apply(this, arguments);
                };
            }
        }
        install.done = !!(a && b && beginDone);
        return install.done;
    }
    var tries = 0, installTimer = setInterval(function () { if (install() || ++tries > 120) clearInterval(installTimer); }, 250);
    install();
    // [TFX4] if a wrapper from another module lands on top of ours later, re-wrap (cheap identity check; the stroke-begin hook above does the same right before each layer stroke)
    setInterval(function () { try { if (!off4() && root._paintOnLayerAt !== layerTop) wrapLayer(); } catch (_e) { } }, 700);

    // ------------------------------------------------------------------ presets
    var PRESETS = [
        { name: 'Natural hand', p: { sizeJit: 15, sizeMin: 70, flowJit: 25 }, tip: 'Tiny random changes in size and flow, so long strokes look hand-painted' },
        { name: 'Speckle', p: { sizeJit: 100, sizeMin: 3, scatter: 180, count: 3, countJit: 20 }, spacing: 140, hint: 'works best with a small brush (size 6 to 14)', tip: 'Fine random dots around the stroke: flecks, paint chips, sparkle. Use a small brush' },
        { name: 'Mud splatter', p: { sizeJit: 100, sizeMin: 6, scatter: 280, count: 4, countJit: 50, flowJit: 30 }, spacing: 180, tip: 'Big and small blobs thrown wide: mud, dirt, bug splatter' },
        { name: 'Dust and overspray', p: { sizeJit: 50, sizeMin: 20, scatter: 300, count: 4, countJit: 50, flowJit: 80 }, spacing: 200, hardness: 35, tip: 'A soft cloud of faint dots: dust, overspray, tyre smoke (sets a soft brush)' },
        { name: 'Confetti', p: { sizeJit: 40, sizeMin: 40, scatter: 220, count: 2, hueJit: 100, satJit: 15, briJit: 15 }, spacing: 170, tip: 'Dots in random colours' },
        { name: 'Two-tone flecks', p: { sizeJit: 100, sizeMin: 4, scatter: 180, count: 2, countJit: 30, fgbg: 100 }, spacing: 160, tip: 'Every dab is a random mix between your Foreground and Background colour' },
        { name: 'Taper out', p: { taperLen: 500, taperEnd: 0 }, tip: 'The stroke gets thinner and ends in a point after about 500 px: swooshes, claw marks, speed lines. Hold Shift and click for a straight tapered line' },
        { name: 'Taper in', p: { taperLen: 400, taperEnd: 0, taperGrow: true }, tip: 'The stroke starts as a point and grows to full size over about 400 px' },
        { name: 'Off', p: {}, tip: 'Every dab identical, exactly on the stroke (the normal brush)' }
    ];
    var SLIDERS = [
        { k: 'sizeJit', sec: 'Size', label: 'Size jitter', min: 0, max: 100, unit: '%', tip: 'Each dab gets a random size between the minimum and full size' },
        { k: 'sizeMin', label: 'Smallest dab', min: 1, max: 100, unit: '%', tip: 'How small a jittered dab can get (percent of the full size)' },
        { k: 'scatter', sec: 'Scatter', label: 'Scatter', min: 0, max: 400, unit: '%', tip: 'Throws dabs off the stroke line: 100% = up to one brush radius away' },
        { k: 'count', label: 'Dabs per step', min: 1, max: 8, unit: '', tip: 'How many dabs are laid down at every step of the stroke' },
        { k: 'countJit', label: 'Count jitter', min: 0, max: 100, unit: '%', tip: 'Randomly drops some of the dabs' },
        { k: 'flowJit', sec: 'Flow', label: 'Flow jitter', min: 0, max: 100, unit: '%', tip: 'Each dab gets a random strength, so some are faint' },
        { k: 'taperLen', sec: 'Taper', label: 'Taper length', min: 0, max: 3000, unit: 'px', tip: 'Over this many pixels of stroke the brush shrinks to a point (0 = no taper)' },
        { k: 'taperEnd', label: 'Taper end size', min: 0, max: 100, unit: '%', tip: 'How small it gets at the end of the taper (0 = a point)' },
        { k: 'fgbg', sec: 'Colour', label: 'FG / BG mix', min: 0, max: 100, unit: '%', tip: 'Each dab is a random mix between your Foreground and Background colour' },
        { k: 'hueJit', label: 'Hue jitter', min: 0, max: 100, unit: '%', tip: 'Random shift round the colour wheel (100% = any hue)' },
        { k: 'satJit', label: 'Saturation jitter', min: 0, max: 100, unit: '%', tip: 'Random change of colour strength' },
        { k: 'briJit', label: 'Brightness jitter', min: 0, max: 100, unit: '%', tip: 'Random lighter / darker dabs' }
    ];
    var CHECKS = [
        { k: 'taperGrow', after: 'taperEnd', label: 'Grow instead of shrink', tip: 'The stroke starts small and grows to full size', active: function (p) { return p.taperLen > 0; } },
        { k: 'taperFlow', after: 'taperEnd', label: 'Fade the paint too', tip: 'The paint also gets fainter along the taper', active: function (p) { return p.taperLen > 0; } },
        { k: 'perDab', after: 'briJit', label: 'New colour for every dab', tip: 'Off: one random colour for the whole stroke', active: colourActive }
    ];
    function setSpacing(v) {
        try { var s = document.getElementById('brushSpacing'); if (!s) return; s.value = v; s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); } catch (_e) { }
    }
    function setHardness(v) {
        try { var s = document.getElementById('brushHardness'); if (!s) return; s.value = v; s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); } catch (_e) { }
    }
    function spacingNow() { try { return parseInt(document.getElementById('brushSpacing').value, 10) || 25; } catch (_e) { return 25; } }
    function hardnessNow() { try { return parseInt(document.getElementById('brushHardness').value, 10) || 100; } catch (_e) { return 100; } }
    // [SPB-TFX4 2026-10-10 item 5 finding, lane TOOLS-FIX-4] presets such as Mud splatter set the brush Spacing (180 %) and some the Hardness; choosing Off / Reset left them
    // there, so 'the normal brush' stayed dotted.  Remember the values from before the first preset that changed them and give them back on Off / Reset, but only if the
    // painter has not moved the slider since (a hand-set value is never overwritten).  SPB_TFX4_OFF = the old behaviour.
    var presetBase = null;
    function applyPresetBrush(pr) {
        if (!(pr.spacing || pr.hardness)) return;
        if (!off4() && !presetBase) presetBase = { sp: spacingNow(), hd: hardnessNow(), setSp: null, setHd: null };
        if (pr.spacing) setSpacing(pr.spacing);
        if (pr.hardness) setHardness(pr.hardness);
        if (presetBase) { if (pr.spacing) presetBase.setSp = spacingNow(); if (pr.hardness) presetBase.setHd = hardnessNow(); }
    }
    function restoreBrushBase() {
        var b = presetBase; presetBase = null; if (!b || off4()) return;
        var back = [];
        if (b.setSp != null && b.sp !== b.setSp && spacingNow() === b.setSp) { setSpacing(b.sp); back.push('Spacing ' + b.sp + '%'); }
        if (b.setHd != null && b.hd !== b.setHd && hardnessNow() === b.setHd) { setHardness(b.hd); back.push('Hardness ' + b.hd + '%'); }
        if (back.length) toast('Dynamics off: ' + back.join(', ') + ' back to what it was before the preset', 'info');
    }

    // ------------------------------------------------------------------ UI
    var pop = null, btn = null, ui = { rows: {} }, pvCv = null;
    function toast(m, k) { try { if (typeof showToast === 'function') showToast(m, k); } catch (_e) { } }
    function ensureStyle() {
        if (document.getElementById('spbTfx3DynStyle')) return;
        var st = document.createElement('style'); st.id = 'spbTfx3DynStyle';
        st.textContent = [
            '#spbTfx3DynBtn{display:none;align-items:center;gap:4px;height:22px;padding:0 7px;border:1px solid var(--border,#3a3d45);border-radius:4px;background:var(--bg-input,#1c1e24);color:var(--text,#d7d9de);font-size:10px;cursor:pointer;white-space:nowrap;flex-shrink:0}',
            '#spbTfx3DynBtn:hover{border-color:var(--accent,#6ea8fe)}',
            '#spbTfx3DynBtn.on{border-color:var(--accent,#6ea8fe);color:var(--accent,#6ea8fe)}',
            '#spbTfx3DynBtn .dot{display:none;width:6px;height:6px;border-radius:50%;background:var(--accent,#6ea8fe)}#spbTfx3DynBtn.on .dot{display:inline-block}',
            '#spbTfx3DynPop{position:fixed;z-index:100050;width:318px;max-height:calc(100vh - 20px);overflow:auto;padding:10px;border:1px solid var(--border,#3a3d45);border-radius:8px;background:var(--bg-panel,#16181d);color:var(--text,#d7d9de);box-shadow:0 10px 30px rgba(0,0,0,.55);font-size:11px;display:none}',
            '#spbTfx3DynPop h4{margin:0 0 6px;font-size:11px;font-weight:600;opacity:.85}',
            '#spbTfx3DynPop .sec{margin:9px 0 2px;font-size:10px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.55}',
            '#spbTfx3DynPop .chips{display:flex;flex-wrap:wrap;gap:5px}',
            '#spbTfx3DynPop .chip{font-size:10px;padding:2px 7px;border:1px solid var(--border,#3a3d45);border-radius:10px;background:var(--bg-input,#1c1e24);color:inherit;cursor:pointer}',
            '#spbTfx3DynPop .chip:hover,#spbTfx3DynPop .chip.on{border-color:var(--accent,#6ea8fe);color:var(--accent,#6ea8fe)}',
            '#spbTfx3DynPop .sl{display:grid;grid-template-columns:112px 1fr 38px;align-items:center;gap:6px;margin-top:4px}',
            '#spbTfx3DynPop .sl label{font-size:10.5px;opacity:.9;white-space:nowrap}',
            '#spbTfx3DynPop .sl input[type=range]{width:100%;margin:0}',
            '#spbTfx3DynPop .sl output{font-size:10px;text-align:right;opacity:.75}',
            '#spbTfx3DynPop .sl.dim{opacity:.4}',
            '#spbTfx3DynPop canvas{display:block;width:296px;height:64px;margin-top:6px;border:1px solid rgba(255,255,255,.18);border-radius:4px;background:#2a2d34}',
            '#spbTfx3DynPop .row{display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap}',
            '#spbTfx3DynPop button.b{font-size:11px;padding:2px 8px;border:1px solid var(--border,#3a3d45);border-radius:4px;background:var(--bg-input,#1c1e24);color:inherit;cursor:pointer}',
            '#spbTfx3DynPop button.b:hover{border-color:var(--accent,#6ea8fe)}',
            '#spbTfx3DynPop .hint{margin-top:8px;opacity:.6;font-size:10px;line-height:1.35}'
        ].join('\n');
        document.head.appendChild(st);
    }
    function drawPreview() {
        if (!pvCv) return;
        var w = pvCv.width, h = pvCv.height, g = pvCv.getContext('2d');
        g.clearRect(0, 0, w, h);
        var R = 7, hard = 1, realR = 26; try { realR = Math.max(1, parseInt(document.getElementById('brushSize').value, 10) || 26); } catch (_e) { } try { hard = clamp((parseInt(document.getElementById('brushHardness').value, 10) || 100) / 100, 0, 1); } catch (_e) { }
        var fg = hexToRgb(fgHex()), bg = hexToRgb(bgHex()), r = mulberry32(20261010), sr = rolls(r), step = Math.max(1, R * spacingNow() / 100), len = w - 24, n = Math.max(2, Math.floor(len * 1.15 / step));
        for (var i = 0; i <= n; i++) {
            var t = i / n, x = 12 + t * len, y = h / 2 + Math.sin(t * Math.PI * 2) * (h * 0.22);
            var dabs = isActive(state.p) ? dabsFor(state.p, r, x, y, R, fg, bg, NaN, NaN, sr, (t * len) * (realR / R)) : [{ x: x, y: y, r: R, flowK: 1, rgb: fg }];
            dabs.forEach(function (d) {
                var gr = g.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r), c = d.rgb, a = d.flowK;
                gr.addColorStop(0, 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')');
                gr.addColorStop(Math.max(0.01, Math.min(0.999, hard)), 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')');
                gr.addColorStop(1, 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',0)');
                g.fillStyle = gr; g.beginPath(); g.arc(d.x, d.y, d.r, 0, Math.PI * 2); g.fill();
            });
        }
    }
    function refreshAll() {
        var act = inLayerMode() ? isActive(state.p) : isActiveZone(state.p);   // [TFX4] in Zone mode the colour group does not count
        if (btn) { btn.classList.toggle('on', act); btn.title = 'Brush dynamics: ' + (act ? state.preset : 'off') + ' - make every dab a little different (random size, scatter, flow' + (inLayerMode() ? ' and colour' : '') + ') for speckle, mud, dust and confetti'; }
        if (!pop) return;
        SLIDERS.forEach(function (s) {
            var r = ui.rows[s.k]; if (!r) return;
            r.inp.value = state.p[s.k]; r.out.textContent = state.p[s.k] + s.unit;
        });
        if (ui.rows.sizeMin) ui.rows.sizeMin.row.classList.toggle('dim', state.p.sizeJit <= 0);
        if (ui.rows.countJit) ui.rows.countJit.row.classList.toggle('dim', state.p.count <= 1);
        var zoneNow = !inLayerMode();   // [TFX4] Zone brush: a mask has no colour, so the colour group is greyed out
        ['fgbg', 'hueJit', 'satJit', 'briJit'].forEach(function (k) { if (ui.rows[k]) { ui.rows[k].row.classList.toggle('dim', zoneNow); ui.rows[k].inp.disabled = zoneNow; } });
        if (ui.checks && ui.checks.perDab) ui.checks.perDab.disabled = zoneNow;
        if (ui.note) ui.note.textContent = zoneNow ? 'Zone brush: size, scatter, flow and taper shape the zone mask. Colour needs the layer brush (a zone has no colour).' : 'Layer brush. Preview shows the effect, not the real size. Wider Spacing suits scatter.';
        CHECKS.forEach(function (c) { var e = ui.checks && ui.checks[c.k]; if (!e) return; e.checked = !!state.p[c.k]; e.parentNode.style.opacity = (c.active(state.p) && !(zoneNow && c.k === 'perDab')) ? '1' : '.4'; });
        Array.prototype.forEach.call(ui.chips.children, function (c) { c.classList.toggle('on', c.dataset.name === (act ? state.preset : 'Off')); });
        drawPreview();
    }
    function build() {
        if (pop) return;
        ensureStyle();
        pop = document.createElement('div'); pop.id = 'spbTfx3DynPop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', 'Brush dynamics');
        var h = '<h4>Brush dynamics</h4><div class="chips"></div>';
        SLIDERS.forEach(function (s) {
            if (s.sec) h += '<div class="sec">' + s.sec + '</div>';
            h += '<div class="sl" data-k="' + s.k + '" title="' + s.tip + '"><label for="spbDyn_' + s.k + '">' + s.label + '</label><input type="range" id="spbDyn_' + s.k + '" min="' + s.min + '" max="' + s.max + '" step="1"><output></output></div>';
            CHECKS.forEach(function (c) { if (c.after === s.k) h += '<div class="row" style="margin-top:4px"><label title="' + c.tip + '"><input type="checkbox" data-k="' + c.k + '"> ' + c.label + '</label></div>'; });
        });
        h += '<canvas width="592" height="128" aria-label="Preview of the stroke"></canvas>';
        h += '<div class="row"><button type="button" class="b" data-act="reset">Reset</button><span class="hint" id="spbDynNote" style="margin:0;flex:1"></span></div>';
        pop.innerHTML = h; document.body.appendChild(pop);
        ui.chips = pop.querySelector('.chips'); pvCv = pop.querySelector('canvas'); ui.note = pop.querySelector('#spbDynNote');
        PRESETS.forEach(function (pr) {
            var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.dataset.name = pr.name; b.textContent = pr.name; b.title = pr.tip; ui.chips.appendChild(b);
        });
        SLIDERS.forEach(function (s) {
            var row = pop.querySelector('.sl[data-k="' + s.k + '"]'); ui.rows[s.k] = { row: row, inp: row.querySelector('input'), out: row.querySelector('output') };
            ui.rows[s.k].inp.addEventListener('input', function () { state.p[s.k] = Number(this.value); state.p = norm(state.p); state.preset = 'Custom'; save(); refreshAll(); });
        });
        ui.checks = {};
        CHECKS.forEach(function (c) { var e = pop.querySelector('input[data-k="' + c.k + '"]'); ui.checks[c.k] = e; e.addEventListener('change', function () { state.p[c.k] = !!this.checked; state.preset = 'Custom'; save(); refreshAll(); }); });
        ui.chips.addEventListener('click', function (e) {
            var c = e.target.closest && e.target.closest('.chip'); if (!c) return;
            var pr = PRESETS.filter(function (x) { return x.name === c.dataset.name; })[0]; if (!pr) return;
            state.p = norm(pr.p); state.preset = pr.name === 'Off' ? 'Off' : pr.name; if (pr.name === 'Off') restoreBrushBase(); else applyPresetBrush(pr); save(); refreshAll();
            if (pr.spacing) toast(pr.name + ': Spacing set to ' + pr.spacing + '%' + (pr.hardness ? ', Hardness ' + pr.hardness + '%' : '') + (pr.hint ? ' - ' + pr.hint : ' - change them in the brush bar if you like'), 'info');
        });
        pop.querySelector('[data-act=reset]').addEventListener('click', function () { state.p = norm(); state.preset = 'Off'; restoreBrushBase(); save(); refreshAll(); });
        pop.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closePop(); e.stopPropagation(); } });
        document.addEventListener('mousedown', function (e) { if (pop && pop.style.display !== 'none' && !pop.contains(e.target) && !(btn && btn.contains(e.target))) closePop(); }, true);
    }
    function openPop() {
        build(); refreshAll();
        pop.style.display = 'block';
        var r = btn.getBoundingClientRect(), w = 318, left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left)), top = r.bottom + 6;
        if (top + pop.offsetHeight > window.innerHeight - 8) top = Math.max(8, window.innerHeight - 8 - pop.offsetHeight);
        pop.style.left = left + 'px'; pop.style.top = top + 'px';
        drawPreview();
    }
    function closePop() { if (pop) pop.style.display = 'none'; }
    function anchorEl() { return document.getElementById('brushFlowVal') || document.getElementById('brushFlow') || document.getElementById('brushHardnessVal'); }
    function ensureBtn() {
        if (btn || off()) return;
        var anchor = anchorEl(); if (!anchor || !anchor.parentNode) return;
        ensureStyle();
        btn = document.createElement('button'); btn.type = 'button'; btn.id = 'spbTfx3DynBtn'; btn.setAttribute('aria-label', 'Brush dynamics');
        btn.innerHTML = '<span class="dot"></span><span>Dynamics</span><span aria-hidden="true">▾</span>';
        anchor.parentNode.insertBefore(btn, anchor.nextSibling);
        btn.addEventListener('click', function (e) { e.stopPropagation(); if (pop && pop.style.display === 'block') closePop(); else openPop(); });
        refreshAll();
    }
    function syncBtn() {
        try {
            if (off()) { if (btn) btn.style.setProperty('display', 'none', 'important'); return; }
            ensureBtn(); if (!btn) return;
            var anc = anchorEl();
            if (anc && anc.parentNode && (btn.parentNode !== anc.parentNode || anc.nextSibling !== btn)) anc.parentNode.insertBefore(btn, anc.nextSibling);
            var show = mode() === 'brush' && (inLayerMode() || !off4());   // [TFX4] the Zone brush has Dynamics too (colour group greyed out)
            if (show) btn.style.setProperty('display', 'inline-flex', 'important'); else { btn.style.setProperty('display', 'none', 'important'); closePop(); }
            btn.classList.toggle('on', inLayerMode() ? isActive(state.p) : isActiveZone(state.p));
        } catch (_e) { }
    }
    load();
    if (!off()) setInterval(syncBtn, 350);

    api.state = function () { return { p: Object.assign({}, state.p), preset: state.preset, active: isActive(state.p), off: off(), stats: Object.assign({}, stats), installed: !!install.done }; };
    api.set = function (p, name) { state.p = norm(Object.assign({}, state.p, p || {})); state.preset = name || 'Custom'; save(); refreshAll(); return api.state(); };
    api.preset = function (name) { if (off()) return false; var pr = PRESETS.filter(function (x) { return x.name === name; })[0]; if (!pr) return false; state.p = norm(pr.p); state.preset = pr.name; applyPresetBrush(pr); save(); refreshAll(); return true; };
    api.reset = function () { state.p = norm(); state.preset = 'Off'; restoreBrushBase(); save(); refreshAll(); };
    api.seed = function (n) { fixedSeed = (n == null) ? null : (n >>> 0); newStroke(); };
    api.open = function () { syncBtn(); if (btn) openPop(); };
    api.close = closePop;
    api.PRESETS = PRESETS;
    return api;
});
