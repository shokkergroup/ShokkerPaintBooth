/* ============================================================================
   HELPER V3 S5 2026-10-05 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md 2.2, stage S5): the PLANNER.
   An intent FRAME (js/spb-intent-frame.js, schema v1) goes in; concrete zone-kit / graphics / flames STEPS come out. Deterministic, no model.
   Wiring into the readers is S6 (offline) / S7 (DeepSeek): nothing calls this module yet except the S5 harnesses.
   Global: window.SpbIntentPlan
     plan(frame, env)        -> { ok, act, steps:[Step], ask, notes, errors }      pure (Node + app); env = live() in the app, a fixture in Node
     run(plan, opts)         -> { ok, applied, warnings, ids, added }              app only: ONE undo step for all zone ops (flames: their own step)
     toQueue(plan)           -> the zone ops as a js/spb-pro-ai.js applyQueue queue ({kind, zone:index, spec}) for S6/S7
     simulate(plan, env)     -> env after the plan (symbolic zones + last change): Node harness / spb_check dry runs
     live()                  -> the app env (layers, body layers, zones, last change, owner / colour lookups)
     last() / forget()       -> the last change this module committed (refs: "thinner", "flip it", "same on the right", "on the hood instead")
   Step = { prim, label, ops:[{kind:'add'|'edit'|'duplicate', zone?:<zone id>, spec, _above?:<zone id>, _aboveAdd?:true (place above the step's added zone), _intersect?:true}], flames?, undo?, scope, expect, notes }
   PRIMITIVES (the S5 row of the plan):
     finishOnly   spec-only Foundation finish (base::f_*) with colour "source" on a scope minus except, decals kept (b6-040 "everything except the roof gets pearl")
     seam         a pinline only where two regions meet; paints neither (graphics kind "seam", b6-042)
     outline      a line around a part / layer / element (number panel) / zone, stroke px stored on the zone (graphics outline + stroke_px)
     relative     thinner / thicker / half that / finer / bigger / lighter / shinier ... on the last change's zones (fixed steps, below)
     gradientEdit flip / less X / more X keeping the gradient (b6-010)
     moveChange   "put that on the hood instead" (the same zones re-placed, one undo step); "same on the right" = mirror the last op (b6-020)
     copyLook     one entry point: zone-kit copy_look_from (or the source part's own paint colour when no zone paints it)
     flames       SpbFlames.apply (js/spb-pro-flames.js, FLAMES.md 5)
     accent ask   "silver accent" / "trim" with no shape named: OWNER DECISION 2026-10-05 = ask every time (outline vs band, with a picture)
   Fixed steps: thinner = px x 0.6, thicker = px / 0.6, "half that" = x 0.5, a little = sqrt(step), a lot = step^2; finer = scale x 0.6, bigger = scale / 0.6;
   less X on a gradient = the other stops move 25% of the gap TOWARD X (X's share shrinks); more X = the X stop moves 25% toward its neighbour (X's share grows).
   ES5 only (old Electron).
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-05-s5';
    var STROKE = { hairline: 3, fine: 4, thin: 6, medium: 10, normal: 10, thick: 18, wide: 18, bold: 18 };
    var CANON = ['hood', 'roof', 'trunk', 'spoiler', 'front bumper', 'rear bumper', 'left side', 'right side'];
    var OPP = { 'left side': 'right side', 'right side': 'left side', 'front bumper': 'rear bumper', 'rear bumper': 'front bumper' };
    var FAMILY_KEY = { chrome: 'f_chrome', mirror: 'f_chrome', 'mirror chrome': 'f_chrome', 'satin chrome': 'f_satin_chrome', 'dark chrome': 'f_dark_chrome', 'black chrome': 'f_dark_chrome', metallic: 'f_metallic', metal: 'f_metallic', pearl: 'f_pearl', pearlescent: 'f_pearl', 'satin pearl': 'f_satin_pearl', candy: 'f_candy', brushed: 'f_brushed', matte: 'f_soft_matte', flat: 'f_soft_matte', satin: 'f_clear_satin', gloss: 'f_soft_gloss', glossy: 'f_soft_gloss', shiny: 'f_soft_gloss', shine: 'f_soft_gloss', wet: 'f_soft_gloss', ceramic: 'f_soft_gloss', clear: 'f_soft_gloss', 'matte metallic': 'f_matte_metallic', frozen: 'f_frozen', 'powder coat': 'f_powder_coat', anodized: 'f_anodized', 'gel coat': 'f_gel_coat', vinyl: 'f_vinyl_wrap', 'bead blast': 'f_bead_blast', enamel: 'f_baked_enamel', carbon: 'f_carbon_fiber' };
    var NAMED = { red: '#d01818', white: '#ffffff', black: '#0a0a0a', blue: '#1f4dff', 'light blue': '#5fb4ff', 'dark blue': '#0b2a6b', navy: '#0b1f4d', green: '#1fa83a', 'neon green': '#39ff14', yellow: '#ffd400', orange: '#ff7a00', purple: '#7a2bd6', pink: '#ff3fa4', gold: '#d4af37', silver: '#c0c0c0', 'dark silver': '#8a8d91', grey: '#808080', gray: '#808080', gunmetal: '#2c3539', bronze: '#a8702a', copper: '#b87333', tan: '#d2b48c', brown: '#6b4423', teal: '#008080', cyan: '#00e5ff', magenta: '#ff00ff', maroon: '#800000', charcoal: '#333333', cream: '#fffdd0', chrome: '#d8d8d8' };
    var METALLIC_WORD = /\b(gold|silver|chrome|gunmetal|bronze|copper|platinum|steel|metal)/i;

    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function low(t) { return String(t == null ? '' : t).toLowerCase(); }
    function isHex(h) { return /^#[0-9a-f]{6}$/i.test(String(h || '')); }
    function num(v, d) { v = Number(v); return isFinite(v) ? v : d; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function arr(x) { return x == null ? [] : (Array.isArray(x) ? x : [x]); }
    function hexOf(c) {
        if (!c) return null; if (typeof c === 'string') c = { word: c };
        if (isHex(c.hex)) return c.hex.toLowerCase(); if (isHex(c.word)) return c.word.toLowerCase();
        var w = low(c.word).replace(/^(?:a |the )/, '').trim(); return NAMED[w] || NAMED[w.split(' ').pop()] || null;
    }
    function rgb(h) { return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)]; }
    function famOf(hex) {
        if (!isHex(hex)) return null;
        try { if (W.SpbProEdit && W.SpbProEdit.familyOf) return W.SpbProEdit.familyOf(hex); } catch (e) {}
        var c = rgb(hex), mx = Math.max(c[0], c[1], c[2]), mn = Math.min(c[0], c[1], c[2]), l = (mx + mn) / 510, ch = (mx - mn) / 255, h = 0;
        if (l < 0.09) return 'black'; if (l > 0.88 && ch < 0.14) return 'white'; if (ch < 0.12) return 'grey';
        var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, d = (mx - mn) / 255; if (mx === c[0]) h = ((g - b) / d) % 6; else if (mx === c[1]) h = (b - r) / d + 2; else h = (r - g) / d + 4; h = (h * 60 + 360) % 360;
        return h < 15 || h >= 340 ? 'red' : h < 40 ? 'orange' : h < 70 ? 'yellow' : h < 165 ? 'green' : h < 200 ? 'teal' : h < 255 ? 'blue' : h < 290 ? 'purple' : 'pink';
    }
    function famWord(c) { if (!c) return null; var h = hexOf(c); var w = low(c.word || ''); var f = h ? famOf(h) : null; if (!f && w) { var k = Object.keys(NAMED).filter(function (n) { return w.indexOf(n) !== -1; })[0]; f = k ? famOf(NAMED[k]) : w; } return f; }
    function strokePx(st, dflt) {
        if (!st) return dflt; if (st.px != null && isFinite(Number(st.px))) return clamp(Number(st.px), 1, 60);
        var w = low(st.width); return STROKE[w] || dflt;
    }
    function finishKey(fin, wantKeep) {          // the Foundation key for a finish family / key; keep-colour work NEVER uses base::chrome / metallic / candy (they repaint)
        if (!fin) return null; var k = String(fin.key || ''), id = k.replace(/^[a-z]+::/, '');
        if (/^base::f_/.test(k)) return k;
        // M2 2026-10-07 (lane M2 hunk for V4-G, folded in by IA1; MCP spb_do frame finish {key:'efx_holo_scan'} / family 'holo' became base::f_soft_gloss under keep-colour, reported as done): an explicit catalogue key that is
        // not one of the repainting bases (base::chrome / metallic / candy ...) is honoured as given; an unknown family under keep returns null (the caller asks) instead of Soft Gloss.
        if (k && !/^base::/.test(k)) return k;
        var fam = low(fin.family || fin.label || id).replace(/_/g, ' ').trim();
        if (wantKeep || !k) { var hit = FAMILY_KEY[fam]; if (!hit) Object.keys(FAMILY_KEY).sort(function (a, b) { return b.length - a.length; }).some(function (w) { if (fam.indexOf(w) !== -1) { hit = FAMILY_KEY[w]; return true; } return false; }); return hit ? 'base::' + hit : (wantKeep && /^(|plain|normal|default|paint)$/.test(fam) ? 'base::f_soft_gloss' : null); }
        return k;
    }

    // ------------------------------------------------------------------ env (pure data; live() builds it in the app)
    function normEnv(env) {
        env = env || {}; var L = env.layers || [];
        var body = env.bodyLayers || L.filter(function (l) { return l && /body paint/i.test(String(l.role || '')) && l.visible !== false && !l.hidden; }).map(function (l) { return l.name; });
        return { history: env.history || [], layers: L, body: body, parts: (env.parts && env.parts.length) ? env.parts : CANON.slice(), zones: env.zones || [], last: env.last || null, offer: env.offer || null,
            ownersIn: typeof env.ownersIn === 'function' ? env.ownersIn : function () { return null; },
            owner: typeof env.owner === 'function' ? env.owner : function (T) { var o = env.owners || {}; return o[tkey(T)] || null; },
            colourOf: typeof env.colourOf === 'function' ? env.colourOf : function (T) { var p = env.paintOf || {}; if (p[tkey(T)]) return p[tkey(T)]; var pc = env.partColours; return (pc && T && T.kind === 'part' && [].concat(pc[arr(T.parts)[0]] || [])[0]) || null; },          // V3 S6b 2026-10-07 G1b: + env.partColours (Node tests: the bare-PSD part measure)
            visibleOf: typeof env.visibleOf === 'function' ? env.visibleOf : function (T) {          // V4-G J2a: the colour a part shows now = the first (top) solid zone painting it (Node: symbolic zones)
                if (!T || T.kind !== 'part') return null; var ps = arr(T.parts), Z = env.zones || [];
                for (var i = 0; i < Z.length; i++) { var z = Z[i]; if (!z || z.muted || (z.catchAll && W.SPB_PLAN_NOJ4V) || z.graphic) continue; var zp = arr(z.parts); if (zp.length && !ps.every(function (q) { return zp.indexOf(q) !== -1; })) continue; if (!zp.length && !(z.whole || (z.layers && z.layers.length))) continue; if (z.mode === 'solid' && isHex(z.colour)) return z.colour; return null; }
                return null; },
            dominantOf: typeof env.dominantOf === 'function' ? env.dominantOf : null,          // V4-G J2b (live: colour-select data for a part with accent art)
            dominantBody: typeof env.dominantBody === 'function' ? env.dominantBody : null, numFill: typeof env.numFill === 'function' ? env.numFill : null,          // IA1 J2W 2026-10-07 (live: the same for the whole car's body paint layers)
            colourLayers: typeof env.colourLayers === 'function' ? env.colourLayers : function () { return []; },
            seamProbe: typeof env.seamProbe === 'function' ? env.seamProbe : null, flat: !!env.flat,
            artLayers: typeof env.artLayers === 'function' ? env.artLayers : (env.partLayers ? function (ps) { var d = env.partLayers, out = []; ps = arr(ps); if (!ps.length) return (d.all || []).slice(); ps.forEach(function (p) { (d.parts && d.parts[p] || []).forEach(function (a) { var h = out.filter(function (x) { return x.name === a.name; })[0]; if (h) h.pct += a.pct; else out.push({ name: a.name, role: a.role, pct: a.pct }); }); }); return out; } : null),          // V4-E 2026-10-07: art layers per part (live(): probed; Node: the measured ARCA data)
            hiddenColour: typeof env.hiddenColour === 'function' ? env.hiddenColour : (env.hidden ? function (r) { return env.hidden[String((r.colors || [])[0]) + '@' + [].concat(r.island || []).join('+')] || null; } : null) };          // V3 S6b 2026-10-07 H2 (+ a data stub for Node tests)
    }
    function tkey(T) { if (!T) return ''; if (T.kind === 'part') return 'part:' + arr(T.parts).join('+'); if (T.kind === 'element') return 'element:' + T.element; if (T.kind === 'layer') return 'layer:' + arr(T.layers).join('+'); if (T.kind === 'zone') return 'zone:' + (T.zone || ''); if (T.kind === 'colour') return 'colour:' + (hexOf(T.colour) || low(T.colour && T.colour.word)); return T.kind || ''; }
    function zoneById(E, id) { var s = String(id); return E.zones.filter(function (z) { return String(z.id) === s || z.name === s; })[0] || null; }
    function layerRole(E, name) { var hit = W.SpbLayerTargets && W.SpbLayerTargets.resolve(name, E.layers); var l = hit ? (hit.ok ? hit.row : null) : E.layers.filter(function (x) { return x && x.name === name; })[0]; return l ? String(l.role || '') : ''; }
    function isDecalLayer(E, name) { return /numbers|logo|sponsor|decal|tape|stripe/i.test(layerRole(E, name)); }

    // ------------------------------------------------------------------ Target -> zone-kit region (+ the symbolic scope the harness and the verifier read)
    function exceptBits(list) {
        var parts = [], elements = [], layers = [], objects = [];
        arr(list).forEach(function (x) {
            if (!x) return; if (typeof x === 'string') x = CANON.indexOf(x) !== -1 ? { kind: 'part', parts: [x] } : { kind: 'element', element: x };
            if (x.kind === 'part' || (x.parts && x.kind !== 'element')) arr(x.parts).forEach(function (p) { parts.push(p); });
            else if (x.kind === 'element') elements.push(x.element === 'logos' ? 'sponsors' : x.element);
            else if (x.kind === 'layer') arr(x.layers).forEach(function (l) { layers.push(l); });
            else if (x.kind === 'object') { if (x.layers && x.layers.length) arr(x.layers).forEach(function (l) { layers.push(l); }); else objects.push(x.object); }
        });
        return { parts: uniq(parts), elements: uniq(elements), layers: uniq(layers), objects: uniq(objects) };
    }
    // IA1 J2W 2026-10-07 (orchestrator round 2; owner R-005 "you covered up some of the white stripes"; in-app A-0143 'whole car candy orange' painted over the pink accent panels and the
    // white heartbeat blocks): a whole-car / body RECOLOUR changes the dominant body colour(s) only, as J2b does for a part; the accent art (other colours on the body layers) stays.
    // The buyer can still ask for everything: SOLID_RE on what was said. Kill switch: window.SPB_PLAN_NOJ2W = true.
    var SOLID_RE = /\b(?:everything|every\s*thing|all of it|every bit|one (?:solid |single |flat )?colou?r|(?:a )?solid colou?r|single colou?r|plain colou?r|all (?:one|the same) colou?r|including (?:the |all (?:the )?)?(?:stripes?|accents?|art|artwork|graphics?|pink|white|black|blocks?|panels?|shapes?|details?)|cover (?:up )?(?:the |all (?:the )?)?(?:stripes?|accents?|art|artwork|graphics?|pink|white|black|blocks?|panels?|shapes?|details?)|(?:stripes?|accents?|graphics?|pink|white)\s+too|paint over (?:the )?(?:stripes?|accents?|art|graphics?)|wipe (?:it|the car|everything)|blank (?:it|the car|out))\b/i, CUR_SAID = '';
    function regionFor(T, E, ex, decals, o5) {
        var r = {}, sc = { kind: T.kind, parts: null, layers: [], elements: [], colours: [], whole: false, except: ex, decals: 'protect' }, named = false;
        if (T.kind === 'body') { sc.whole = true; if (E.body.length) r.layers = E.body.slice(); else r.paintable = true;
            if (o5 && o5.recolour && !T.portion && decals !== 'include' && !W.SPB_PLAN_NOJ2W && E.dominantBody && !SOLID_RE.test(String(CUR_SAID || ''))) { var dmb = null; try { dmb = E.dominantBody(r.layers || null); } catch (eDB) { dmb = null; } if (dmb && arr(dmb.colors).length) { r.colors = arr(dmb.colors).slice(); r.tolerance = dmb.tol || 48; sc.keepAccent = { colours: r.colors.slice(), share: dmb.frac, whole: true }; } }          // IA1 J2W
        }
        else if (T.kind === 'part' || T.kind === 'graphic') { var ps = arr(T.parts); if (!ps.length) return { err: 'which part?' }; sc.parts = ps.slice(); r.island = ps.length > 1 ? ps.slice() : ps[0]; if (T.portion) r.portion = T.portion;
            if (T.kind === 'part' && !T.portion && decals !== 'include' && !W.SPB_PLAN_NOJ2B && E.dominantOf && (W.SPB_PLAN_NOH1A || !SOLID_RE.test(String(CUR_SAID || '')))) { /* lane R3-EDIT 2026-10-07 H1a: 'one solid red, cover everything' on a part covers the art as asked (probe h1c_ss kept the logo) */ var dm = null; try { dm = E.dominantOf(ps); } catch (eD) { dm = null; } if (dm && arr(dm.colors).length) { r.colors = arr(dm.colors).slice(); r.tolerance = dm.tol || 48; sc.keepAccent = { colours: r.colors.slice(), share: dm.frac }; } }          // V4-G J2b: accent art on the part (white stripe blocks) stays unless named
        }
        else if (T.kind === 'layer') { sc.layers = arr(T.layers).slice(); r.layers = sc.layers.slice(); named = sc.layers.some(function (n) { return isDecalLayer(E, n); }); }
        else if (T.kind === 'element') {
            sc.elements = [T.element]; named = true; var rl = T.element === 'numbers' ? /^numbers$/i : /logo|sponsor|decal/i, ls = E.layers.filter(function (l) { return l && rl.test(String(l.role || '')) && l.visible !== false; }).map(function (l) { return l.name; });
            if (ls.length && !E.flat) { r.layers = ls; sc.layers = ls.slice(); } else r.element = T.element;
        } else if (T.kind === 'colour') {
            var hx = hexOf(T.colour); if (!hx) return { err: 'which colour?' }; r.colors = [hx]; r.tolerance = 40; sc.colours = [hx];
            if (T.layers && T.layers.length) { r.layers = arr(T.layers).slice(); sc.layers = r.layers.slice(); named = r.layers.some(function (n) { return isDecalLayer(E, n); }); }
            if (T.parts && T.parts.length) { r.island = T.parts.length > 1 ? T.parts.slice() : T.parts[0]; sc.parts = T.parts.slice(); }
        } else return { err: 'unsupported target ' + T.kind };
        if ((T.kind === 'layer' || T.kind === 'element') && arr(T.parts).length) { r.island = arr(T.parts).length > 1 ? arr(T.parts).slice() : arr(T.parts)[0]; sc.parts = arr(T.parts).slice(); if (T.portion) r.portion = T.portion; }
        if (decals === 'include') { sc.decals = 'include'; if (T.kind === 'body') { delete r.layers; r.everything = true; } }
        else if (named) sc.decals = 'named';
        else if (!r.layers) { if (E.body.length) { r.layers = E.body.slice(); sc.layers = E.body.slice(); } else r.exclude = ['numbers', 'sponsors']; }          // decals stay: limited to the body paint layers (layered file) or the found numbers / sponsors cut out (flat)
        if (ex.parts.length) r.exclude = uniq(arr(r.exclude).concat(ex.parts));
        if (ex.elements.length && !(r.layers && E.body.length && r.layers.every(function (n) { return E.body.indexOf(n) !== -1; }))) r.exclude = uniq(arr(r.exclude).concat(ex.elements.filter(function (e) { return e !== 'logos'; })));
        if (ex.layers.length && r.layers) { r.layers = r.layers.filter(function (n) { return ex.layers.indexOf(n) === -1; }); sc.layers = r.layers.slice(); if (!r.layers.length) return { err: 'nothing left after the layers you kept' }; }
        return { region: r, scope: sc };
    }
    function protectGraphic(region, E, decals) { if (decals === 'include') return region; if (E.body.length) region.layers = E.body.slice(); else region.exclude = uniq(arr(region.exclude).concat(['numbers', 'sponsors'])); return region; }
    function nameOfT(T) {
        if (!T) return 'that'; if (T.between && arr(T.between).length === 2) return 'the line between ' + nameOfT(T.between[0]) + ' and ' + nameOfT(T.between[1]); if (T.kind === 'body') return 'the car'; if (T.kind === 'part' || T.kind === 'graphic') return 'the ' + arr(T.parts).join(' and ');
        if (T.kind === 'layer') return 'the ' + arr(T.layers).join(' and ') + ' layer'; if (T.kind === 'element') return 'the ' + T.element; if (T.kind === 'colour') return 'the ' + (T.colour && (T.colour.word || T.colour.hex)) + (T.layers ? ' in ' + T.layers.join(', ') : ''); return 'that';
    }
    function cap(s) { s = String(s || ''); return s.charAt(0).toUpperCase() + s.slice(1); }

    // ------------------------------------------------------------------ refs (earlier turns): the last change's zones / target / op
    function lastOf(E) { return E.last || null; }
    function ownersOf(T, E) {          // the existing zones a target means when nothing earlier is referenced ("the carbon on the hood", "the flames", "the camo")
        var w = low(T.graphic || T.object || (T.kind === 'element' && /^(stripes?|flames?|pinstripes?|pinlines?|outlines?|bands?|lines?)$/.test(low(T.element)) ? T.element : '') || ''), out = [];          // V4-E 2026-10-07: + graphic-like elements ("make the stripes thinner": the stripe zones, was an ask)
        if (/[^s]s$/.test(w)) w = w.slice(0, -1);          // V4-E 2026-10-07: "stripes" finds a stripe zone
        if (w) E.zones.forEach(function (z) { if (z.catchAll || z.muted) return; var hay = low([z.name, z.pattern, z.base, z.finish, z.graphic && (z.graphic.item || z.graphic).kind].join(' ')); if (hay.indexOf(w) !== -1 || (w === 'stripe' && /stripe/.test(hay))) { if (!T.parts || !z.parts || z.parts.some(function (p) { return arr(T.parts).indexOf(p) !== -1; })) out.push(z.id); } });
        if (!out.length && T.kind === 'part') { E.zones.forEach(function (z) { if (z.catchAll || z.muted || !z.parts) return; if (z.parts.some(function (p) { return arr(T.parts).indexOf(p) !== -1; }) && ((z.pattern && z.pattern !== 'none') || z.graphic || z.mode === 'gradient' || (z.base && !/^(gloss|f_)/.test(z.base)))) out.push(z.id); }); }
        if (!out.length && T.kind === 'part') { var o = E.owner(T); if (o != null) { var oz = zoneById(E, o); if (oz && ((oz.pattern && oz.pattern !== 'none') || oz.mode === 'gradient')) out.push(oz.id); } }
        return uniq(out);
    }
    function resolveRef(op, E, frame) {
        var ref = op.ref || (op.target && op.target.ref ? (typeof op.target.ref === 'string' ? { to: op.target.ref } : op.target.ref) : null); if (!ref) return { op: op };
        var L = (ref.to === 'turn' && E.history && E.history[ref.turn]) || lastOf(E); if (!L) return { err: 'no earlier change to refer to' };
        var o = clone(op); o._last = L;
        if (frame && frame.replace_last && ref.to === 'last_change' && L.target && L.target.kind !== 'zone' && arr(L.added).length && arr(L.ids).every(function (id) { return arr(L.added).indexOf(id) !== -1; }) && (!op.target || op.target.ref || op.target.kind === 'zone') && hasLook(op.look)) {          // V4-E 2026-10-07: "no, pearl" / "keep the 2nd": the undo takes the added zones away, so the new look goes on the last TARGET (was: edits of zones the undo had removed)
            o.target = clone(L.target); if (!o.verb || o.verb === 'adjust') o.verb = L.op && L.op.verb && L.op.verb !== 'adjust' ? L.op.verb : 'recolour'; if (!o.except && L.op && L.op.except) o.except = clone(L.op.except); delete o.ref; return { op: o };
        }
        if (ref.to === 'opposite_side') {
            var lp = arr(L.target && L.target.parts), mp = lp.map(function (p) { return OPP[p] || null; }).filter(Boolean);
            if (!mp.length) return { err: 'the last change was not on a side I can mirror' };
            o.target = { kind: 'part', parts: mp, portion: L.target.portion };
            if (!o.verb || o.verb === 'adjust') o.verb = L.op && L.op.verb || 'recolour';
            o.look = Object.assign({}, clone(L.look || (L.op && L.op.look)) || {}, o.look || {}); if (L.op && L.op.except && !o.except) o.except = clone(L.op.except); delete o.ref; return { op: o, mirror: true };
        }
        if (ref.to === 'last_target') { o.target = clone(L.target); delete o.ref; return { op: o }; }
        if (op.target && op.target.colour) o._colour = clone(op.target.colour); o._zones = (L.ids || []).slice(); o._lastTarget = clone(L.target); if (!o.target || o.target.ref || o.target.kind === 'zone') o.target = { kind: 'zone', zones: o._zones };
        return { op: o };
    }

    // ------------------------------------------------------------------ primitives (each returns a Step or { ask })
    function step(prim, label, ops, scope, extra) { var s = { prim: prim, label: label, ops: ops || [], scope: scope || null, expect: {}, notes: [] }; if (extra) Object.keys(extra).forEach(function (k) { s[k] = extra[k]; }); return s; }

    // FINISH ONLY: a Foundation finish + colour "source" on the scope; zones that already paint inside the scope get a copy limited to the scope with the new finish
    // (a "source" zone on top would put the ORIGINAL paint back over a recolour: b6-040 turned the car pink because of exactly that kind of scope slip)
    function finishOnly(T, ex, look, E, decals) {
        var key = finishKey(look && look.finish || { family: 'gloss' }, true), rr = regionFor(T, E, ex, decals); if (rr.err) return { ask: askTarget(rr.err, E) };
        if (!key) return { ask: { q: 'Which finish should that be (for example gloss, satin, matte, chrome or metallic)?', chips: [] } };          // IA1 2026-10-07: M2's finishKey returns null for an unknown family under keep (was Soft Gloss)
        var fam = key.replace(/^base::f_/, '').replace(/_/g, ' '), ops = [], notes = [], sc = rr.scope;
        sc.spec_only = true; sc.finish = key;
        ops.push({ kind: 'add', spec: { name: cap(fam) + ' finish on ' + nameOfT(T).replace(/^the /, '') + (ex.parts.length ? ' except ' + ex.parts.join(', ') : ''), finish: key, color: 'source', region: rr.region, priority: 'bottom' } });
        var scopeLayers = rr.region.layers || null;
        var whole = T.kind === 'body' && !ex.parts.length && !ex.elements.length && !ex.layers.length && !T.portion;
        var inverse = T.kind === 'body' && ex.parts.length && !ex.elements.length && !ex.layers.length && !T.portion;
        if (whole || inverse) {          // the whole car (minus kept parts): the paint zones get the finish IN PLACE; a kept part gets a copy of each zone that paints it, with the zone's OWN look, limited to that part
            var keepOwners = inverse ? E.ownersIn(ex.parts) : null;          // (S5 in-app: per-zone copies of everything but the roof cost ~0.85 s each at 2048; copies on the kept roof are 1-2 zones)N PLACE (no extra zones = no extra render cost, undo-safe: no mask changes); the F zone catches the rest
            // S5 in-app (owner ARCA): with a body-layer F zone that skips the roof, the engine's "remaining" catch-all LOST its roof pixels (they rendered with no zone:
            // flat brown spec on 35% of the roof). Editing the catch-all in place instead changed the decals' spec (985k px: the catch-all owns the numbers/sponsors).
            // So the catch-all keeps its look and gets a copy on the kept part placed ABOVE the F zone (_aboveAdd), which takes its kept-part pixels back.
            var rest = inverse ? E.zones.filter(function (z) { return z && !z.muted && z.catchAll === 'remaining' && !z.graphic; })[0] : null;
            if (rest) ops.push({ kind: 'duplicate', zone: rest.id, spec: { name: (rest.name + ' (kept on ' + ex.parts.join(', ') + ')').slice(0, 60), region: { island: ex.parts.length > 1 ? ex.parts.slice() : ex.parts[0] }, textureAnchor: 'canvas' }, _aboveAdd: true, _keepLook: true });
            E.zones.forEach(function (z) {
                if (!z || z.muted || z.catchAll || z.s5spec || z.graphic) return; if (z.finish) { notes.push('"' + z.name + '" has its own complete look (a special finish), so it keeps it'); return; }
                if (scopeLayers && arr(z.layers).length && !arr(z.layers).every(function (n) { return scopeLayers.indexOf(n) !== -1; })) return;          // a zone on decal layers keeps its finish (decals untouched)
                if (inverse && (!keepOwners || keepOwners.indexOf(z.id) !== -1)) ops.push({ kind: 'duplicate', zone: z.id, spec: { name: (z.name + ' (kept on ' + ex.parts.join(', ') + ')').slice(0, 60), region: { island: ex.parts.length > 1 ? ex.parts.slice() : ex.parts[0] }, textureAnchor: 'canvas' }, _above: z.id, _intersect: true, _keepLook: true });          // copied BEFORE the in-place edit, so the kept part keeps the zone's old look
                ops.push({ kind: 'edit', zone: z.id, spec: { finish: key } });
            });
            var sw = step('finishOnly', cap(fam) + ' finish on ' + (inverse ? 'the car except the ' + ex.parts.join(' and ') : 'the whole car') + ', colours kept', ops, sc, { notes: notes }); sw.expect = { paint_diff_max: 0.005, decal_px_max: 0, spec_changes: true }; return sw;
        }
        E.zones.forEach(function (z) {
            // IA1 2026-10-07 (in-app A-0295 'hood and roof gloss' then 'no keep hood flat' = nothing changed): the earlier shine zone on the hood (a finish-only copy) was skipped, so the
            // new flat copy went UNDER it. A finish-only copy that paints the named part is copied again (above itself) with the new finish.
            var ia1S = !W.SPB_PLAN_NOIA1 && !!z && !z.muted && !z.catchAll && z.s5spec && !!sc.parts && arr(z.parts).some(function (p) { return sc.parts.indexOf(p) !== -1; }) && (z.mode === 'solid' || z.mode === 'gradient');
            if (!z || z.muted || z.catchAll || (z.s5spec && !ia1S)) return;
            var paints = z.mode === 'solid' || z.mode === 'gradient' || !!z.finish || (z.base && !/^f_/.test(z.base) && z.base !== 'gloss') || (z.base && z.base !== key.replace(/^base::/, ''));
            if (!paints) return;
            if (z.finish && !ia1S) { notes.push('"' + z.name + '" has its own complete look (a special finish), so it keeps it'); return; }
            var zl = arr(z.layers), lay = null;
            if (scopeLayers) { if (zl.length) { lay = zl.filter(function (n) { return scopeLayers.indexOf(n) !== -1; }); if (!lay.length) return; if (lay.length === zl.length) lay = null; } else lay = scopeLayers.slice(); }
            if (z.parts && z.parts.length && sc.parts && !z.parts.some(function (p) { return sc.parts.indexOf(p) !== -1; })) return;
            if (z.parts && z.parts.length && !sc.parts && ex.parts.length && z.parts.every(function (p) { return ex.parts.indexOf(p) !== -1; })) return;
            var reg = {}; if (lay) reg.layers = lay; if (sc.parts) { reg.island = sc.parts.length > 1 ? sc.parts.slice() : sc.parts[0]; if (T.portion) reg.portion = T.portion; } if (ex.parts.length) reg.exclude = ex.parts.slice();
            var spec = { name: z.name + ' (' + fam + ')', finish: key }; if (Object.keys(reg).length) spec.region = reg;
            ops.push({ kind: 'duplicate', zone: z.id, spec: spec, _above: z.id, _intersect: !!(sc.parts && z.useRegion) });
        });
        var s = step('finishOnly', cap(fam) + ' finish on ' + nameOfT(T) + (ex.parts.length ? ' except the ' + ex.parts.join(' and ') : '') + ', colours kept', ops, sc, { notes: notes });
        s.expect = { paint_diff_max: 0.005, decal_px_max: 0, spec_changes: true };
        return s;
    }
    function paintOp(op, T, ex, E, decals) {          // recolour / refinish / restyle with a colour, gradient, finish or pattern
        var L = op.look || {}, rr = regionFor(T, E, ex, decals, { recolour: !!(hexOf(L.colour) || L.gradient) && !L.pattern }); if (rr.err) return { ask: askTarget(rr.err, E) };          // IA1 J2W
        var spec = { name: '', region: rr.region }, what = [], hx = hexOf(L.colour);
        if (!W.SPB_W28_NUMFILL_OFF && hx && (T.kind === 'element' && T.element === 'numbers' || T.kind === 'layer' && arr(T.layers).length && arr(T.layers).every(function (n9) { return /^numbers$/i.test(layerRole(E, n9)); })) && !L.gradient && !L.pattern && rr.region && arr(rr.region.layers).length && !rr.region.colors && typeof E.numFill === 'function') {          // [SPB-W28 2026-10-10 coordinator item 6a] "make the numbers white" painted the black outline / shadow white too (the whole Numbers layer): only the FILL colour is recoloured now (kill window.SPB_W28_NUMFILL_OFF)
            try { var nf28 = E.numFill(rr.region.layers); if (nf28) { rr.region.colors = [nf28.hex]; rr.region.tolerance = nf28.tol; rr.scope.keepOutline = nf28.others; } } catch (eNF) {}
        }
        if (T.kind === 'colour' && arr(T.parts).length && rr.scope.decals !== 'named' && rr.scope.decals !== 'include' && typeof E.hiddenColour === 'function') {          // V3 S6b 2026-10-07 H2 (A-0054): that colour does not SHOW on the part (another zone paints over it there)
            var hv = null; try { hv = E.hiddenColour(rr.region); } catch (eH) { hv = null; }
            if (hv && hv.hits > 0 && hv.hidden >= 0.6) {
                var cw = (T.colour && (T.colour.word || T.colour.hex)) || 'that colour', pn = nameOfT({ kind: 'part', parts: T.parts }), dl = [];
                try { dl = (E.colourLayers(cw) || []).filter(function (n) { return isDecalLayer(E, n) && !/numbers/i.test(layerRole(E, n)); }); } catch (eD) { dl = []; }
                var chips = [chipFrame(cap(pn.replace(/^the /, '')) + ': all of it', op, { target: { kind: 'part', parts: arr(T.parts).slice() } })];
                if (dl.length) chips.push(chipFrame('The ' + cw + ' in the logos on ' + pn, op, { target: { kind: 'colour', colour: clone(T.colour), layers: dl.slice(0, 2), parts: arr(T.parts).slice() } }));
                return { ask: { q: 'No ' + cw + ' paint shows on ' + pn + ' now: “' + hv.by + '” paints over it there' + (dl.length ? ', so the ' + cw + ' you see is in the logos (' + dl.slice(0, 2).join(', ') + '), and logos stay untouched unless you name them' : '') + '. Which one did you mean?', chips: chips, hidden: true } };
            }
        }
        if (L.gradient) { var g = gradientSpec(L.gradient, T, E); if (!g) return { ask: { q: 'Which two colours for the fade?', chips: [] } }; spec.gradient = g; what.push('a ' + arr(L.gradient.stops).map(function (s) { s = (s && typeof s === 'object') ? (s.word || s.color || s.hex) : s; return /^(clear|nothing|none|source|transparent|body|own)$/i.test(String(s)) ? 'its own colour' : s; }).join(' to ') + ' fade' + (/bottom|top|up|down/.test(low(L.gradient.axis)) ? ' (' + low(L.gradient.axis).replace(/_/g, ' ') + ')' : '')); }
        else if (hx) { spec.color = hx; what.push(L.colour.word || hx); }
        if (L.finish) { var fk = L.finish.key && /::/.test(L.finish.key) ? L.finish.key : finishKey(L.finish, false); if (fk) { spec.finish = fk; what.push(L.finish.family || fk.replace(/^[a-z]+::/, '')); } if (!hx && !L.gradient && /^base::f_/.test(fk || '')) spec.color = 'source'; if (!hx && !L.gradient && !spec.color && !W.SPB_PLAN_NOR13P) { if (fk === 'base::primer') spec.color = '#8c8f91'; else if (/^base::(?:ceramic|gloss|wet_look|semi_gloss|satin|silk|eggshell|ceramic_matte|tempered_glass|orange_peel_gloss|living_matte|oxidized|chalky_base|crumbling_clear|destroyed_coat)$/.test(fk || '')) spec.color = 'source'; } /* R13-CONVO2 2026-10-08 A-0200: a colourless paint_none base (primer) on a part left the zone without a colour, so the hidden source paint (yellow block / mint) showed through; primer = raw grey, other finish-only bases keep the car's own colour. Kill: window.SPB_PLAN_NOR13P */ }
        if (L.pattern && L.pattern.id) { spec.pattern = { id: L.pattern.id }; if (L.pattern.opacity != null) spec.pattern.opacity = L.pattern.opacity; if (L.pattern.scale != null) spec.pattern.scale = L.pattern.scale; what.push(L.pattern.concept || L.pattern.id); }
        if (L.scale != null) spec.scale = clamp(num(L.scale, 1), 0.05, 5);
        if (!spec.color && !spec.gradient && !spec.finish && !spec.pattern && spec.scale == null) return { ask: { q: 'What should ' + nameOfT(T) + ' become (a colour, a finish or a pattern)?', chips: [] } };
        spec.name = cap(what.join(' ') + ' ' + nameOfT(T).replace(/^the /, '')).slice(0, 48);
        var s = step(L.gradient ? 'gradient' : 'paint', cap(what.join(' ')) + ' on ' + nameOfT(T), [{ kind: 'add', spec: spec }], rr.scope);
        if (L.finish && L.finish.r8 && (L.finish.r8.alts || []).length && !(W.SPB_OF_CFG && W.SPB_OF_CFG.noR8g)) s.label += ' (closest to “' + L.finish.r8.label + '”; other options: ' + L.finish.r8.alts.map(function (x) { return x.name; }).join(', ') + ')';          // R8-FIN 2026-10-08: say what was picked and offer 1-2 alternatives after
        s.scope.colour = hx; s.scope.finish = spec.finish || null; if (L.finish && L.finish.r8 && !W.SPB_PLAN_NOR12) s.scope.r8 = { label: L.finish.r8.label, pick: L.finish.r8.pick, alts: (L.finish.r8.alts || []).map(function (x) { return x.name; }) }; /* R12-REPLY 2026-10-08: the pick rides to the reply (spb-intent-report.js r12Of) */ return s;
    }
    function isleOf(part) { try { return W.SpbProCar && W.SpbProCar.findIsland ? W.SpbProCar.findIsland(part) : null; } catch (e) { return null; } }
    function gradientSpec(g, T, E) {          // frame gradient -> zone-kit gradient (part orientation from the car map, as js/spb-pro-edit.js partGradient)
        var own = null; function stopHex(c) { if (/^(clear|nothing|none|source|transparent|body|own)$/i.test(String(c || ''))) { if (own == null) { own = ''; try { if (!W.SPB_PLAN_NOJ2A && T && E && E.visibleOf) own = E.visibleOf(T) || ''; } catch (eV) { own = ''; } if (!own) own = (T && E && E.colourOf(T)) || ''; } /* V4-G J2a: 'clear' = the colour visible on the part (the top zone), then the source colour */ return own || null; } return hexOf(c); }
        var st = arr(g.stops).map(function (s) { return typeof s === 'string' ? { color: stopHex(s) } : { color: stopHex(s.color || s.hex || s.word || s), pos: s.pos }; }).filter(function (s) { return s.color; });
        if (st.length < 2) return null; var n = st.length; st.forEach(function (s, i) { if (s.pos == null) s.pos = Math.round(i / (n - 1) * 100); });
        var axis = low(g.axis || 'front_to_rear'), part = T && arr(T.parts)[0], isl = part ? isleOf(part) : null, dir = 'horizontal', rev = false;
        if (axis === 'radial') return { stops: st, direction: 'radial', fit: true };
        if (/top|bottom|height|up|down/.test(axis)) { var up = (isl && isl.up) || 'top'; dir = (up === 'left' || up === 'right') ? 'horizontal' : 'vertical'; rev = (up === 'bottom' || up === 'right'); if (/bottom_to_top|up$/.test(axis)) rev = !rev; }
        else { var fr = (isl && isl.front) || 'left'; dir = (fr === 'left' || fr === 'right') ? 'horizontal' : 'vertical'; rev = (fr === 'right' || fr === 'bottom'); if (/rear_to_front/.test(axis)) rev = !rev; }
        if (rev) st = st.map(function (s) { return { pos: 100 - s.pos, color: s.color }; }).reverse();
        return { stops: st, direction: dir, fit: true };
    }
    function lineLook(L, colourHex) { var sp = {}; if (L.finish) { var fk = L.finish.key && /::/.test(L.finish.key) ? L.finish.key : finishKey(L.finish, false); if (fk) sp.finish = fk; } else if (METALLIC_WORD.test(String((L.colour && L.colour.word) || ''))) sp.finish = 'base::f_metallic'; sp.color = colourHex; return sp; }          // S5 in-app 2026-10-05: base::metallic cost ~2 s per line zone at 2048; the Foundation f_metallic (solid spec) is cheap
    function graphicZones(item, cols, L, label, scopeBase, E, decals, extraRegion) {          // one zone per colour of a graphic (zone-kit paints one colour per zone)
        var ops = [], us = uniq(cols);
        us.forEach(function (c) {
            var g = us.length > 1 ? { item: item, only: c } : item, reg = protectGraphic(Object.assign({ graphic: g }, extraRegion || {}), E, decals), sp = lineLook(L, c);
            sp.region = reg; sp.name = (label + (us.length > 1 ? ' ' + c : '')).slice(0, 48); ops.push({ kind: 'add', spec: sp });
        });
        return ops;
    }
    // OUTLINE of a part / layer / element (number panel) / zone; the stroke width is stored on the zone (stroke_px)
    function outline(op, T, ex, E, decals) {
        var L = op.look || {}, hx = hexOf(L.colour); if (!hx) return { ask: { q: 'What colour should the line around ' + nameOfT(T) + ' be?', chips: ['white', 'black', 'gold', 'silver'].map(function (c) { return chipFrame(c, op, { look: Object.assign({}, L, { colour: { word: c, hex: NAMED[c] } }) }); }) } };
        var px = strokePx(L.stroke, 6), sides = L.stroke && L.stroke.sides && L.stroke.sides !== 'both' ? L.stroke.sides : (L.stroke && L.stroke.sides === 'both' ? 'both' : null), item = { kind: 'outline', colour: hx, stroke_px: px }, sc = { kind: T.kind, parts: null, layers: [], elements: [], whole: false, except: ex, decals: 'protect', line_px: px };
        if (T.kind === 'part') { item.part = arr(T.parts).length > 1 ? arr(T.parts).slice() : arr(T.parts)[0]; sc.parts = arr(T.parts).slice(); }
        else if (T.kind === 'layer') { item.layer = arr(T.layers)[0]; item.sides = 'outer'; sc.layers = [item.layer]; }
        else if (T.kind === 'element') { item.element = T.element; item.sides = 'outer'; sc.elements = [T.element]; sc.around = true; }
        else if (T.kind === 'zone') { var zid = arr(T.zones || T.zone)[0]; if (zid == null) return { ask: askTarget('outline what?', E) }; item.zone = zid; item.sides = 'outer'; sc.zones = [zid]; var zz = zoneById(E, zid); if (zz && zz.parts) sc.parts = zz.parts.slice(); }
        else if (T.kind === 'object') { if (T.layers && T.layers.length) { item.layer = T.layers[0]; item.sides = 'outer'; sc.layers = [item.layer]; } else return { ask: askLayerFor(T, op, E) }; }
        else return { ask: askTarget('outline what?', E) };
        if (sides) item.sides = sides;
        var ops = graphicZones(item, [hx], L, cap((L.colour && L.colour.word) || hx) + ' outline ' + nameOfT(T).replace(/^the /, ''), sc, E, decals, ex.parts.length ? { exclude: ex.parts.slice() } : null);
        var s = step('outline', 'a ' + px + ' px ' + ((L.colour && L.colour.word) || hx) + ' line ' + (item.sides === 'outer' ? 'around ' : 'along the edge of ') + nameOfT(T), ops, sc); s.scope.colour = hx; s.expect = { line_px: px }; return s;
    }
    // SEAM: a pinline only where A meets B (graphics kind "seam"), never a recolour of A or B
    function sideOf(T) {
        if (!T) return null; if (T.kind === 'part') return { parts: arr(T.parts).slice() }; if (T.kind === 'layer') return { layer: arr(T.layers)[0] };
        if (T.kind === 'element') return { element: T.element }; if (T.kind === 'zone') return { zone: arr(T.zones || T.zone)[0] }; if (T.kind === 'body') return { rest: [] };
        if (T.kind === 'colour') { var hx = hexOf(T.colour); return hx && isHex(T.colour && T.colour.hex) ? { colour: hx } : { family: famWord(T.colour) }; }
        return null;
    }
    function seam(op, T, ex, E, decals) {
        var L = op.look || {}, bt = arr(T.between), hx = hexOf(L.colour); if (bt.length !== 2) return { ask: { q: 'Between which two colours or parts should the line go?', chips: [] } };
        if (!hx) return { ask: { q: 'What colour should the pinline be?', chips: ['white', 'black', 'gold', 'silver'].map(function (c) { return chipFrame(c, op, { look: Object.assign({}, L, { colour: { word: c, hex: NAMED[c] } }) }); }) } };
        var px = strokePx(L.stroke, 6), A = bt[0], B = bt[1];
        if ((A.kind === 'part' && B.kind === 'body') || (B.kind === 'part' && A.kind === 'body')) {          // "between the body and the roof": the roof's own edge (it is where the roof meets the body)
            var P = A.kind === 'part' ? A : B, s0 = outline({ verb: 'outline', look: Object.assign({}, L, { stroke: { px: px } }) }, { kind: 'part', parts: arr(P.parts) }, ex, E, decals); if (s0.ask) return s0;
            s0.prim = 'seam'; s0.label = 'a ' + px + ' px ' + ((L.colour && L.colour.word) || hx) + ' pinline where ' + nameOfT(P) + ' meets the body'; s0.scope.seam = [sideOf(A), sideOf(B)]; return s0;
        }
        var a = sideOf(A), b = sideOf(B); if (!a || !b) return { ask: { q: 'Between which two colours or parts should the line go?', chips: [] } };
        var item = { kind: 'seam', a: a, b: b, colour: hx, stroke_px: px }, clipParts = arr(T.parts).length ? arr(T.parts) : null; if (clipParts) item.part = clipParts.length > 1 ? clipParts.slice() : clipParts[0];
        if (E.seamProbe) { var pr = E.seamProbe(item); if (pr && pr.empty) {
            var nm = [nameOfT(A), nameOfT(B)], chips = [];
            if (A.kind === 'part') chips.push(chipFrame('A line around ' + nm[0], op, { verb: 'outline', target: A, look: Object.assign({}, L, { stroke: { px: px } }) }));
            if (B.kind === 'part') chips.push(chipFrame('A line around ' + nm[1], op, { verb: 'outline', target: B, look: Object.assign({}, L, { stroke: { px: px } }) }));
            return { ask: { q: nm[0].charAt(0).toUpperCase() + nm[0].slice(1) + ' and ' + nm[1] + ' do not touch on this car' + (pr.desc && /not found/.test(pr.desc) ? ' (' + pr.desc.replace(/^.*\(/, '').replace(/\)$/, '') + ')' : '') + ', so a pinline between them has nowhere to go. A line around one of them instead?', chips: chips } };
        } }
        var sc = { kind: 'seam', parts: clipParts ? clipParts.slice() : (A.kind === 'part' || B.kind === 'part' ? uniq(arr(A.parts).concat(arr(B.parts))) : null), layers: [], elements: [], whole: false, except: ex, decals: 'protect', seam: [a, b], line_px: px, colour: hx, recolours: [] };
        var ops = graphicZones(item, [hx], L, cap((L.colour && L.colour.word) || hx) + ' pinline', sc, E, decals, ex.parts.length ? { exclude: ex.parts.slice() } : null);
        var s = step('seam', 'a ' + px + ' px ' + ((L.colour && L.colour.word) || hx) + ' pinline where ' + nameOfT(A) + ' meets ' + nameOfT(B), ops, sc); s.expect = { line_px: px, fill_ratio_max: 0.05 }; return s;
    }
    // STRIPE (graphics "stripes"): racing stripes / pinstripes on parts, absolute px widths
    var AT_WORD = [[/\b(low|lower|bottom|rocker|skirt)/, 0.82], [/\b(belt ?line|high|upper|top|shoulder)/, 0.3], [/\b(cent(?:er|re)|middle|mid)/, 0.5]];
    function stripe(op, T, ex, E, decals) {
        var L = op.look || {}, cols = arr(L.colours).map(hexOf).filter(Boolean); if (!cols.length && hexOf(L.colour)) cols = [hexOf(L.colour)];
        if (!cols.length) return { ask: { q: 'What colour should the stripe be?', chips: ['white', 'black', 'red', 'gold'].map(function (c) { return chipFrame(c, op, { look: Object.assign({}, L, { colour: { word: c, hex: NAMED[c] } }) }); }) } };
        var parts = arr(T.parts); if (!parts.length) return { ask: askTarget('which part should the stripe go on?', E) };
        var thin = L.stroke && /thin|fine|hairline|pin/.test(low(L.stroke.width)), px = strokePx(L.stroke, thin ? 6 : 60), n = num(L.stroke && L.stroke.n, cols.length), at = 0.5;
        if (!W.SPB_PLAN_NOES1 && op.verb !== 'pinline' && L.stroke && L.stroke.px == null && /^(thin|narrow|slim|skinny)$/.test(low(L.stroke.width))) { px = ES_PX[low(L.stroke.width)]; thin = false; }          // ESTRIPE 2026-10-08: a thin / narrow racing stripe is 20 px, not a 6 px pinstripe (pinstripe / pin line keep 6)
        if (!W.SPB_W29_STRIPEW_OFF && op.verb !== 'pinline' && L.stroke && L.stroke.px == null && /^(thick|wide|fat|broad|bold)$/.test(low(L.stroke.width))) px = 90;          // W29 2026-10-10 (new-stripe order class): STROKE.thick is 18 px, so "a thick black racing stripe" came out THINNER than a plain stripe (default 60 px); thick / wide / fat / broad / bold = 90 px (kill: window.SPB_W29_STRIPEW_OFF)
        AT_WORD.forEach(function (aw) { if (aw[0].test(low(T.portion || (L.stroke && L.stroke.at) || ''))) at = aw[1]; }); if (L.stroke && isFinite(Number(L.stroke.at))) at = Number(L.stroke.at);
        var seq = []; for (var i = 0; i < n; i++) seq.push(cols[i % cols.length]);
        var item = { kind: 'stripes', part: parts.length > 1 ? parts.slice() : parts[0], colours: seq, n: n, stroke_px: px, gap_px: num(L.stroke && L.stroke.gap_px, Math.max(2, Math.round(px * 0.5))), at: at, angle: num(L.rotation, 0) };
        var sc = { kind: 'part', parts: parts.slice(), layers: [], elements: [], whole: false, except: ex, decals: 'protect', line_px: px, colour: cols[0] };
        var ops = graphicZones(item, seq, L, (n > 1 ? n + ' stripes ' : 'Stripe ') + parts.join('+'), sc, E, decals, ex.parts.length ? { exclude: ex.parts.slice() } : null);
        var cw = (arr(L.colours).length ? arr(L.colours) : [L.colour]).map(function (c) { return c && (c.word || hexOf(c)); }).filter(Boolean);          // V3 S6 2026-10-06 G8b: the colour WORD in the label (was the hex)
        return step('stripe', (n > 1 ? n + ' ' : 'a ') + (thin ? px + ' px ' : '') + (cw.length ? cw : cols).join('/') + ' stripe' + (n > 1 ? 's' : '') + ' on ' + nameOfT(T), ops, sc);
    }
    // FLAMES: the shipped js/spb-pro-flames.js (FLAMES.md 5). One SpbFlames.apply call = its own undo step.
    var FLAME_STYLE = [[/tribal/, 'tribal'], [/ghost/, 'ghost'], [/real|true ?fire|realistic|fire/, 'truefire'], [/hot ?rod|classic|traditional/, 'hotrod']];
    function flames(op, T, ex, E) {
        var L = op.look || {}, P = L.pattern || L.graphic || {}, said = low((P.style || '') + ' ' + (P.concept || '') + ' ' + (op.said || '')), style = 'hotrod';
        FLAME_STYLE.some(function (f) { if (f[0].test(said)) { style = f[1]; return true; } return false; });
        var parts = arr(T.parts); if (T.kind === 'body') parts = ['hood', 'left side', 'right side']; if (!parts.length) parts = ['left side', 'right side'];
        var o = { part: parts.length === 1 ? parts[0] : parts.slice(), style: style, keep_decals: true, label: 'Flames' };
        if (T.portion && !W.SPB_PLAN_NOJ5P) { var bd5 = { 'lower half': [0.5, 0.94], 'lower third': [0.62, 0.94], 'lower quarter': [0.7, 0.96], 'upper half': [0.06, 0.5], 'upper third': [0.06, 0.38], 'upper quarter': [0.04, 0.3] }[String(T.portion)]; if (bd5) o.band = bd5; }          // IA1 J5p 2026-10-07: flames on the lower / upper part of a panel (band = fraction of its height, roof-line 0 -> rocker 1)
        var cols = arr(L.colours).map(hexOf).filter(Boolean); if (!cols.length && hexOf(L.colour)) cols = [hexOf(L.colour)]; if (cols.length) o.colours = cols;
        if (L.stroke && L.stroke.colour) o.outline = hexOf(L.stroke.colour);
        try { var chk = W.SpbFlames && W.SpbFlames.check ? W.SpbFlames.check(o) : null; if (chk) return { ask: { q: chk, chips: [] } }; } catch (e) {}
        return step('flames', style + ' flames on ' + parts.join(', '), [], { kind: 'part', parts: parts, layers: [], elements: [], whole: false, except: ex, decals: 'protect' }, { flames: o });
    }
    // COPY LOOK: one entry point (zone-kit copy_look_from), or the source part's own paint colour when no zone paints it
    // lane R3-EDIT 2026-10-07 J7c: a copy_look_from that points at a zone the same plan takes back (replace_last) -> the zone's colour / finish / pattern written into the spec
    function inlineLook(st, z) {
        arr(st && st.ops).forEach(function (o) { var sp = o && o.spec; if (!sp || sp.copy_look_from == null || String(sp.copy_look_from) !== String(z.id)) return; delete sp.copy_look_from;
            if (sp.color == null) { if (z.mode === 'solid' && isHex(z.colour)) sp.color = z.colour; else if (z.mode === 'gradient' && z.gradient && arr(z.gradient.stops).length) sp.gradient = { stops: clone(z.gradient.stops), direction: z.gradient.direction, fit: true }; }
            if (sp.finish == null && (z.finish || z.base)) sp.finish = z.finish ? 'monolithic::' + z.finish : 'base::' + z.base;
            if (sp.pattern == null && z.pattern && z.pattern !== 'none') sp.pattern = { id: z.pattern, scale: z.patternScale || 1 };
            if (st.scope) st.scope.copy_inlined = true; });
        return st;
    }
    function copyLook(op, T, ex, E, decals) {
        var S = op.source || (op.look && op.look.copy_from) || null, srcZ = null;
        if (S && S.ref) { var L0 = lastOf(E); srcZ = L0 && L0.ids && L0.ids[0]; }
        else if (S && S.kind === 'zone') srcZ = arr(S.zones || S.zone)[0];
        else if (S && S.kind === 'part' && E.last && E.last.target && E.last.target.kind === 'part' && arr(S.parts).slice().sort().join('+') === arr(E.last.target.parts).slice().sort().join('+') && arr(E.last.ids).length) { srcZ = arr(E.last.added).concat(arr(E.last.ids)).filter(function (id) { var z = zoneById(E, id); return z && !z.graphic; })[0]; if (srcZ == null) srcZ = E.owner(S); }          // V4-E 2026-10-07: "copy it to the right" right after painting the left side = THAT change is the source (in-app owner() missed the fresh zone and copied the bare template colour)
        else if (S) srcZ = E.owner(S);
        if (!S && op._zones) srcZ = op._zones[0];
        var rr = regionFor(T, E, ex, decals); if (rr.err) return { ask: askTarget(rr.err, E) };
        var copy = arr(op.copy).length ? arr(op.copy) : ['colour', 'finish', 'spec', 'scale', 'pattern'], spec = { region: rr.region }, sc = rr.scope;
        if (srcZ != null && zoneById(E, srcZ) && zoneById(E, srcZ).catchAll && S && !S.ref && S.kind === 'part' && E.colourOf(S) && (W.SPB_PLAN_NOH2 || !(T.kind === 'part' && /\b(?:finish(?:es)?|shine|sheen|spec|gloss(?:iness)?|matte|satin|texture|clear ?coat|metal(?:lic)?ness|roughness)\b/i.test(CUR_SAID) && !/\b(?:colou?rs?|paint ?job|whole look|everything|same look)\b/i.test(CUR_SAID)))) srcZ = null;          /* lane R3-EDIT 2026-10-07 H2b: 'copy the roof finish to the hood' with a catch-all roof copied its COLOUR (MCP probe h1d trunk pink -> seafoam); a finish-only copy keeps the zone */          // V3 S6 2026-10-06 P1: a base zone's look = nothing visible on the target
        if (srcZ != null && zoneById(E, srcZ)) {
            var z = zoneById(E, srcZ); sc.copy_from = z.id;
            // lane R3-EDIT 2026-10-07 H2 (orchestrator sealed class: "copy the <part> finish to <other parts>" painted the targets as solid bright-yellow slabs): copy_look_from carries the
            // source zone's COLOUR too, and a finish-only source zone ('source' colour) shows the hidden source paint (the yellow under the seafoam) on the targets. A finish-only copy
            // (copy list without colour, or finish / shine / spec words and no colour word) or a source-colour zone keeps each target part's own visible colour: one zone per part,
            // the look copied, the part's shown colour on top (J2b keeps its art). Kill switch: window.SPB_PLAN_NOH2.
            var finOnlyH2 = !W.SPB_PLAN_NOH2 && T.kind === 'part' && ((arr(op.copy).length && arr(op.copy).indexOf('colour') === -1) || (/\b(?:finish(?:es)?|shine|sheen|spec|gloss(?:iness)?|matte|satin|texture|clear ?coat|metal(?:lic)?ness|roughness)\b/i.test(CUR_SAID) && !/\b(?:colou?rs?|paint ?job|whole look|everything|same look)\b/i.test(CUR_SAID)) || z.mode === 'source');
            if (finOnlyH2) {
                var opsH2 = [], keptH2 = [];
                arr(T.parts).forEach(function (pp) { var TP = { kind: 'part', parts: [pp] }, vis = E.colourOf ? E.colourOf(TP) : null, rrP = regionFor(TP, E, ex, decals); if (rrP.err) return; var spP = { region: rrP.region, copy_look_from: z.id, name: ('Finish of ' + z.name).slice(0, 40) + ' (' + pp + ')' }; if (vis && isHex(vis)) { spP.color = vis; keptH2.push(pp + ' ' + vis); } else if (z.mode !== 'source') spP.color = 'source'; opsH2.push({ kind: 'add', spec: spP }); });
                if (opsH2.length) { sc.copy_finish_only = true; sc.kept_colour = keptH2; return step('copyLook', 'the finish of "' + z.name + '" on ' + nameOfT(T) + ' (each part keeps its own colour)', opsH2, sc); }
            }
            if (copy.length === 1 && copy[0] === 'colour' && (z.mode === 'solid' || z.mode === 'gradient')) { if (z.mode === 'solid') spec.color = z.colour; else spec.gradient = { stops: clone(z.gradient.stops), direction: z.gradient.direction, fit: true }; }
            else spec.copy_look_from = z.id;
            spec.name = ('Same look as ' + z.name).slice(0, 48) + ' (' + nameOfT(T).replace(/^the /, '') + ')';
            return step('copyLook', 'the look of "' + z.name + '" on ' + nameOfT(T), [{ kind: 'add', spec: spec }], sc);
        }
        var hx = S ? E.colourOf(S, op.look && op.look.colour && op.look.colour.word ? op.look.colour.word : null) : null;          // W26U: the colour WORD ("the red in the logo layer") picks that colour family of the layer's own pixels
        if (!hx && S && !W.SPB_W26_OFF && !W.SPB_PLAN_NOW26L && op.look && op.look.colour && op.look.colour.word && NAMED[low(op.look.colour.word)]) hx = NAMED[low(op.look.colour.word)];          // W26U 2026-10-10 (bank W26_C7-001 vs W25): 'the red in our logo layer' with no layer pixels to sample (empty / hidden layer) = plain red, as before the layer sampling existed; was: 'Which zone should the spoiler copy its look from?'
        if (hx) { spec.color = hx; spec.name = ('Same colour as ' + nameOfT(S).replace(/^the /, '')).slice(0, 40) + ' (' + nameOfT(T).replace(/^the /, '') + ')'; sc.copy_colour = hx; return step('copyLook', 'the colour of ' + nameOfT(S) + ' (' + hx + ') on ' + nameOfT(T), [{ kind: 'add', spec: spec }], sc); }
        return { ask: { q: 'Which zone should ' + nameOfT(T) + ' copy its look from?', chips: E.zones.filter(function (z) { return !z.catchAll; }).slice(0, 6).map(function (z) { return chipFrame(z.name, op, { source: { kind: 'zone', zones: [z.id] } }); }) } };
    }
    // RELATIVE edits on zones (stroke width, scale, lightness, saturation, hue, gloss, metal, strength, stops)
    function factor(rel, base) {
        var a = rel.amount; if (a === 'half') return 0.5; if (a === 'double' || a === 'twice') return 2; if (a === 'little') return Math.pow(base, 0.5); if (a === 'lot') return Math.pow(base, 2);
        if (a != null && isFinite(Number(a)) && Number(a) > 0) return Number(a); return base;
    }
    // ESTRIPE 2026-10-08 (in-app ES-1 'I want red and blue stripe' / 'on the hood' / 'thin' / 'red first then blue'): 'thin' asked "what should change: colour, finish, pattern or size?" and 'red first then blue'
    // recoloured BOTH stripes red. A follow-up that names a stripe WIDTH word ("thin", "narrow", "wide") and/or a colour ORDER ("red first then blue", "blue last") on stripes just drawn edits those stripe zones:
    // thin = narrow (20 px; pin / hairline 6), colours keep their zones and only swap place. One question at most, never twice. Kill switch: window.SPB_PLAN_NOES1.
    var ES_PX = { hairline: 6, pin: 6, fine: 6, pinstripe: 6, thin: 20, narrow: 24, slim: 18, skinny: 16, thick: 60, wide: 60, fat: 60, broad: 60, bold: 60 };
    function stripeFollow(op, E) {
        if (W.SPB_PLAN_NOES1) return null;
        var ids = arr(op._zones), zs = ids.map(function (id) { return zoneById(E, id); }).filter(function (z) { return z && z.graphic && (z.graphic.item || z.graphic).kind === 'stripes'; });
        if (!zs.length || zs.length !== ids.filter(function (id) { return zoneById(E, id); }).length) return null;
        var said = low(String(op.said || op._frameSaid || CUR_SAID || '')), wm = /\b(hairline|pin|fine|pinstripe|thin|narrow|slim|skinny|thick|wide|fat|broad|bold)\b/.exec(said), px = wm ? ES_PX[wm[1]] : null, ops = [], why = [];
        if (px == null && L0(op) && L0(op).stroke && L0(op).stroke.width && ES_PX[low(L0(op).stroke.width)] != null) px = ES_PX[low(L0(op).stroke.width)];
        if (px == null && /^\W*(?:(?:just |only )?(?:a )?(?:touch|bit|little|tad|hair|notch)|slightly|somewhat|much|way|a lot|even|still)?\s*(more|less|bigger|smaller|wider|narrower|thinner|thicker)(?: of (?:that|it|them|this))?\W*$/.test(said)) { var mm = /(more|less|bigger|smaller|wider|narrower|thinner|thicker)/.exec(said)[1], up = /more|bigger|wider|thicker/.test(mm), cpx = num((zs[0].graphic.item || zs[0].graphic).stroke_px, 20); px = Math.round(clamp(cpx * (up ? 1.4 : 0.7), 4, 60)); if (px === Math.round(cpx)) px = Math.round(clamp(cpx + (up ? 4 : -4), 4, 60)); }          // 'a touch more of that' / 'a bit less' after a stripe change = the stripes a step wider / narrower (x1.4 / x0.7)
        var names = Object.keys(NAMED).sort(function (a, b) { return b.length - a.length; }), seen = [], rest = said;
        names.forEach(function (n) { var m = new RegExp(String.fromCharCode(92) + 'b' + n.replace(/ /g, String.fromCharCode(92) + 's+') + String.fromCharCode(92) + 'b').exec(rest); if (m) { seen.push({ i: m.index, w: n }); rest = rest.slice(0, m.index) + new Array(n.length + 1).join(' ') + rest.slice(m.index + n.length); } });
        seen.sort(function (a, b) { return a.i - b.i; });
        var it0 = zs[0].graphic.item || zs[0].graphic, cur = arr(it0.colours).filter(isHex), curU = uniq(cur.map(function (c) { return c.toLowerCase(); }));
        var wantFam = uniq(seen.map(function (x) { return famOf(NAMED[x.w]); }).filter(Boolean)), order = null;
        if (curU.length > 1 && wantFam.length >= 1 && /\b(f(?:irst|isrt|rist|irts)|then|last|second|before|after|followed|on top|outside|inside|top|bottom)\b/.test(said)) {
            var byFam = {}; curU.forEach(function (h) { byFam[famOf(h)] = h; });
            var fams = Object.keys(byFam);
            if (wantFam.every(function (f) { return byFam[f]; })) {
                var lastM = /\b([a-z]+(?: [a-z]+)?) (?:last|second)\b/.exec(said), lf = lastM ? famOf(NAMED[(names.filter(function (n) { return lastM[1].indexOf(n) !== -1; })[0]) || '']) : null;
                var d = wantFam.slice(); fams.forEach(function (f) { if (d.indexOf(f) === -1) d.push(f); }); if (lf && d.indexOf(lf) !== -1 && /\blast\b|\bsecond\b/.test(said)) { d = d.filter(function (f) { return f !== lf; }); d.push(lf); }
                order = d.map(function (f) { return byFam[f]; });
            }
        }
        if (px == null && !order) return null;
        zs.forEach(function (z) {
            if (order) { var gi = clone(z.graphic), it = gi.item || gi, n = Math.max(arr(it.colours).length, order.length), seq = []; for (var i = 0; i < n; i++) seq.push(order[i % order.length]); it.colours = seq; ops.push({ kind: 'edit', zone: z.id, spec: { region: { graphic: gi } } }); }
            if (px != null) ops.push({ kind: 'edit', zone: z.id, spec: { stroke_px: px } });
        });
        if (order) why.push('colour order ' + order.map(function (h) { return famOf(h); }).join(' then ')); if (px != null) why.push('stripe width ' + px + ' px');
        var st = step('adjust', 'stripes: ' + why.join(', '), ops, { kind: 'zone', zones: ids.slice(), parts: op._lastTarget && op._lastTarget.parts || null, layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect', edits_only: true });
        st.notes = (st.notes || []).concat(['the stripes of the last change']); return st;
    }
    function L0(op) { return op && op.look; }
    function relativeEdit(op, E) {
        var rel = op.relative || {}, prop = low(rel.prop), dir = num(rel.dir, -1), ids = op._zones || [], ops = [], why = [], L = op.look || {}, flm = null, splitS = [];
        if (!ids.length) return null;
        if (prop === 'stops' || (prop === 'hue' && ids.some(function (id) { var z = zoneById(E, id); return z && z.mode === 'gradient'; }))) return gradientEdit(op, E);
        if (prop === 'scale' && !W.SPB_PLAN_NOAI4 && typeof document !== 'undefined' && !!W.SpbProCar) { var plain = ids.map(function (id) { return zoneById(E, id); }).filter(Boolean); if (plain.length && plain.every(function (z) { return !(z.pattern && z.pattern !== 'none') && !z.graphic && (!z.mode || z.mode === 'solid') && (!z.base || /^(gloss|matte|satin|f_|paint_none)/.test(String(z.base))); })) return { ask: { q: 'The ' + String(plain[0].name || 'zone').replace(/^the /i, '') + ' is a plain colour, so there is no pattern to make ' + (dir < 0 ? 'smaller' : 'bigger') + '. Want a pattern on it first (carbon, hex, camo...)?', chips: [] } }; }          // AITER 2026-10-08: honest, nothing changed
        ids.forEach(function (id) {
            var z = zoneById(E, id); if (!z) return; var sp = {};
            if (prop === 'scale' && z.graphic && (z.graphic.item || z.graphic).kind === 'flames') { var fg = z.graphic.item || z.graphic, fsc = num(fg.scale, 1), nf = Math.round(clamp(fsc * factor(rel, dir < 0 ? 0.6 : 1 / 0.6), 0.5, 2) * 100) / 100; if (!flm) { flm = { part: fg.part, style: fg.style || 'hotrod', scale: nf, keep_decals: true, label: 'Flames ' + (dir < 0 ? 'smaller' : 'bigger') }; if (fg.colours) flm.colours = fg.colours.filter(function (c) { return isHex(c); }).slice(0, 3); why.push('flame size ' + fsc + ' -> ' + nf + (nf === fsc ? ' (the limit)' : '')); } return; }
            if (prop === 'width') {
                var cur = num(z.graphic && (z.graphic.item || z.graphic).stroke_px, z.graphic && (z.graphic.item || z.graphic).w != null ? num((z.graphic.item || z.graphic).w, 0.02) * 512 : 10);
                var nx = (L.stroke && L.stroke.px != null) ? Number(L.stroke.px) : cur * factor(rel, dir < 0 ? 0.6 : 1 / 0.6); if (rel.amount === 'half') nx = cur * 0.5;
                if (!z.graphic) { why.push('"' + z.name + '" is not a line'); return; } sp.stroke_px = Math.round(clamp(nx, 1, (W.SPB_W31_OFF || (W.SPB_OF_CFG && (W.SPB_OF_CFG.noW31 || W.SPB_OF_CFG.noW31_5))) ? 60 : 150) * 10) / 10; /* W31-5 2026-10-10: ceiling 60 -> 150 (a default stripe is already 60 px, so wider never grew; kill noW31_5) */ why.push('line ' + Math.round(cur * 10) / 10 + ' -> ' + sp.stroke_px + ' px');
            } else if (prop === 'scale') {
                var hasPat = z.pattern && z.pattern !== 'none', cs = num(hasPat ? z.patternScale : z.scale, 1), back = rel.amount === 'back' && z.s5 && z.s5.lastScale, ns = back ? z.s5.lastScale : cs * factor(rel, dir < 0 ? 0.6 : 1 / 0.6); ns = Math.round(clamp(ns, 0.05, 5) * 1000) / 1000;
                if (hasPat) sp.pattern = { id: z.pattern, scale: ns }; else sp.scale = ns; sp._prevScale = cs; why.push('scale ' + cs + ' -> ' + ns);
            } else if (prop === 'rotation' && !W.SPB_PLAN_NOAI1) {          // AITER 2026-10-08 ('rotate it 45 degrees' / 'turn the pattern a bit'): the pattern angle (or the finish angle) moves by the degrees said, default 30
                var hpR = z.pattern && z.pattern !== 'none', r0 = num(hpR ? z.patternRotation : z.baseRotation, 0), dg = isFinite(Number(rel.amount)) && Number(rel.amount) > 0 ? Number(rel.amount) : (/^(?:a lot|much|way|big|lot)/.test(low(rel.amount)) ? 90 : (/^(?:a bit|little|touch|tad|slight)/.test(low(rel.amount)) ? 15 : 30)), r1 = ((Math.round(r0 + (dir > 0 ? dg : -dg)) % 360) + 360) % 360;
                if (hpR) sp.pattern = { id: z.pattern, rotation: r1 }; else sp.rotation = r1; why.push('rotation ' + r0 + ' -> ' + r1 + ' degrees');
            } else if ((prop === 'opacity' || prop === 'intensity') && !W.SPB_PLAN_NOAI1) {          // AITER: more / less intense = the pattern's opacity (a zone with a pattern) else the finish intensity
                var hpO = z.pattern && z.pattern !== 'none' && prop === 'opacity' || (z.pattern && z.pattern !== 'none' && num(z.patternOpacity, 100) < 100 || false), st6 = Math.round(25 * factor(rel, 1));
                var absPct = (!W.SPB_W26_OFF && rel.to != null && isFinite(Number(rel.to)) && Number(rel.to) > 0) ? clamp(Math.round(Number(rel.to)), 5, 100) : null;          // W26U 2026-10-10 (class 1): "now try 40%" / "set it to 60%" = an ABSOLUTE percent (the frame emits relative.to); was: a +/-25 step whatever the number said
                if (hpO || (z.pattern && z.pattern !== 'none' && prop === 'opacity')) { var o0 = num(z.patternOpacity, 100), o1 = absPct != null ? absPct : clamp(o0 + (dir > 0 ? st6 : -st6), 5, 100); if (o1 === o0) { why.push('already at ' + o0 + '% opacity'); return; } sp.pattern = { id: z.pattern, opacity: o1 }; why.push('pattern opacity ' + o0 + ' -> ' + o1); }
                else { var i0 = num(z.intensity, 100), i1 = absPct != null ? absPct : clamp(i0 + (dir > 0 ? st6 : -st6), 5, 100); if (i1 === i0) { why.push('already at ' + i0 + '% intensity'); return; } sp.intensity = i1; why.push('intensity ' + i0 + ' -> ' + i1); }
            } else if (prop === 'lightness' && !W.SPB_PLAN_NOR13L && (z.mode === 'solid' || z.mode == null) && /^#[0-9a-f]{6}$/i.test(String(z.colour || '')) && (!z.pattern || z.pattern === 'none') && !z.graphic) {
                /* R13-CONVO2 2026-10-08 (in-app BL6-101 'a little more lighter green', probe 'make the roof blue' -> 'a little lighter' = 'nothing visible changed on the car'): the brightness knob multiplies the VALUE of a
                   saturated colour (blue #1f4dff, green #1fa83a are already at full value, black has none), so +25 is invisible. A solid zone's own colour is moved in HSL lightness instead (about 13 points a step). Kill: SPB_PLAN_NOR13L. */
                var hx = String(z.colour).replace('#', ''), rr0 = parseInt(hx.slice(0, 2), 16) / 255, gg0 = parseInt(hx.slice(2, 4), 16) / 255, bb0 = parseInt(hx.slice(4, 6), 16) / 255, mx0 = Math.max(rr0, gg0, bb0), mn0 = Math.min(rr0, gg0, bb0), l0 = (mx0 + mn0) / 2, d0 = mx0 - mn0, s0h = d0 === 0 ? 0 : d0 / (1 - Math.abs(2 * l0 - 1)), h0 = 0;
                if (d0) { if (mx0 === rr0) h0 = ((gg0 - bb0) / d0 + 6) % 6; else if (mx0 === gg0) h0 = (bb0 - rr0) / d0 + 2; else h0 = (rr0 - gg0) / d0 + 4; }
                var l1 = clamp(l0 + (dir > 0 ? 1 : -1) * 0.13 * factor(rel, 1), 0.04, 0.96), c1 = (1 - Math.abs(2 * l1 - 1)) * s0h, x1 = c1 * (1 - Math.abs(h0 % 2 - 1)), m1 = l1 - c1 / 2, q = [[c1, x1, 0], [x1, c1, 0], [0, c1, x1], [0, x1, c1], [x1, 0, c1], [c1, 0, x1]][Math.min(5, Math.floor(h0))];
                var nh = '#' + q.map(function (v) { var n = Math.round((v + m1) * 255); return (n < 16 ? '0' : '') + clamp(n, 0, 255).toString(16); }).join('');
                sp.color = nh; why.push('colour ' + z.colour + ' -> ' + nh + ' (' + (dir > 0 ? 'lighter' : 'darker') + ')');
            } else if (prop === 'lightness') { var b0 = num(z.brightness, 0), st = Math.round(25 * factor(rel, 1)); /* IA1 2026-10-07: 15 -> 25 (in-app 'the hood, to gray' then 'more dark gray' = 'nothing visible changed on the car': a -15 step on mid grey stays under the visible-change bar) */ sp.brightness = clamp(b0 + (dir > 0 ? st : -st), -100, 200); why.push('brightness ' + b0 + ' -> ' + sp.brightness); }
            else if (prop === 'saturation') { var s0 = num(z.saturation, 0), st2 = Math.round(20 * factor(rel, 1)); sp.saturation = clamp(s0 + (dir > 0 ? st2 : -st2), -100, 100); why.push('saturation ' + s0 + ' -> ' + sp.saturation); }
            else if (prop === 'hue') { var s1 = num(z.saturation, 0); sp.saturation = clamp(s1 + (dir > 0 ? 20 : -25), -100, 100); why.push('saturation ' + s1 + ' -> ' + sp.saturation); }
            else if (prop === 'gloss') { var g0 = arr(z.specShift)[1] || 0, st3 = Math.round(30 * factor(rel, 1)); sp.spec_shift = { rough: clamp(g0 + (dir > 0 ? -st3 : st3), -127, 127) }; why.push('roughness shift ' + g0 + ' -> ' + sp.spec_shift.rough); }
            else if (prop === 'metal') { var m0 = arr(z.specShift)[0] || 0, st4 = Math.round(40 * factor(rel, 1)); sp.spec_shift = { metal: clamp(m0 + (dir > 0 ? st4 : -st4), -127, 127) }; why.push('metal shift ' + m0 + ' -> ' + sp.spec_shift.metal); }
            else if (prop === 'strength') { var k0 = num(z.baseStrength, 1) * 100, st5 = Math.round(25 * factor(rel, 1)); sp.base_strength = clamp(k0 + (dir > 0 ? st5 : -st5), 0, 200); why.push('strength ' + Math.round(k0) + ' -> ' + sp.base_strength + '%'); }
            else return;
            // IA1 2026-10-07 (in-app train A-0491 'triple carbon: hood roof trunk' -> 'scale up the roof only' changed the hood too: ONE zone covered all three parts): a named part that
            // is only PART of the zone = a copy of that zone's look on the named part with the tweak on top (the other parts keep the old look)
            var tpS = (op.target && op.target.kind === 'part') ? arr(op.target.parts).filter(function (q) { return arr(z.parts).indexOf(q) !== -1; }) : [];
            if (!W.SPB_PLAN_NOIA1 && tpS.length && arr(z.parts).some(function (q) { return tpS.indexOf(q) === -1; }) && !z.graphic) {
                var rrS = regionFor({ kind: 'part', parts: tpS }, E, { parts: [], elements: [], layers: [] }, 'protect');
                if (!rrS.err) { var adS = Object.assign({ name: (z.name + ' (' + tpS.join(', ') + ')').slice(0, 60), region: rrS.region, copy_look_from: z.id }, sp); delete adS._prevScale; ops.push({ kind: 'add', spec: adS }); splitS = splitS.concat(tpS); return; }
            }
            ops.push({ kind: 'edit', zone: z.id, spec: sp });
        });
        if (flm && !ops.length) return step('relative', 'flames ' + (dir < 0 ? 'smaller' : 'bigger') + ' (' + why.join(', ') + ')', [], { kind: 'part', parts: arr(flm.part), layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect' }, { flames: flm });
        if (!ops.length) return { ask: { q: why.length ? why.join('; ') + ': nothing I can make ' + (dir < 0 ? 'less' : 'more') + ' there. Which zone did you mean?' : 'What should change: the width, the size, the colour or the shine?', chips: [] } };
        var aiL = []; ids.forEach(function (id) { var zq = zoneById(E, id); if (zq) arr(zq.layers).forEach(function (l) { if (isDecalLayer(E, l)) aiL.push(l); }); });          // AITER: a tweak of a zone that lives on the Numbers / Logos layer names that layer (the verifier otherwise calls it a change to unnamed decals)
        var s = step('relative', prop + (dir < 0 ? ' down' : ' up') + ' on the last change (' + why.join(', ') + ')', ops, { kind: 'zone', zones: ids.slice(), parts: op._lastTarget && op._lastTarget.parts || null, layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect', edits_only: true });
        if (aiL.length && !W.SPB_PLAN_NOAI5) { s.scope.layers = uniq(aiL); s.scope.decals = 'named'; }
        if (splitS.length && ops.every(function (o) { return o.kind === 'add'; })) s.scope = { kind: 'part', parts: uniq(splitS), layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect' };          // IA1 2026-10-07: the split copy is a new zone on the named part
        if (op._lastTarget && op._lastTarget.kind === 'element' && !arr(op._lastTarget.parts).length) { s.scope.kind = 'element'; s.scope.elements = [op._lastTarget.element]; }          // V4-E 2026-10-07: "make the stripes thinner" = the stripe zones only; the scope says so (the next follow-up refers to the stripes, not the whole theme)
        return s;
    }
    // GRADIENT EDIT: flip it / less X / more X, the gradient stays a gradient
    function gradientEdit(op, E) {
        var rel = op.relative || {}, ids = op._zones || [], ops = [], why = [], L = op.look || {}, wantFam = famWord(op._colour || (op.target && op.target.colour) || rel.colour || L.colour), dir = num(rel.dir, -1);
        ids.forEach(function (id) {
            var z = zoneById(E, id); if (!z || z.mode !== 'gradient' || !z.gradient || arr(z.gradient.stops).length < 2) return;
            var st = clone(z.gradient.stops).sort(function (a, b) { return a.pos - b.pos; }), n = st.length, i;
            if (/^(soft|softer|feather|harder|hard|sharper)$/.test(low(rel.amount))) { var soft = /soft|feather/.test(low(rel.amount)), c0 = (st[0].pos + st[n - 1].pos) / 2, chg = false; st.forEach(function (s) { var np = Math.round(clamp(c0 + (s.pos - c0) * (soft ? 1.35 : 0.7), 0, 100)); if (np !== s.pos) chg = true; s.pos = np; }); if (!chg) { why.push('the fade in "' + z.name + '" already runs over the whole area, so it cannot get softer'); return; } why.push(soft ? 'softer fade' : 'harder fade'); }
            else if ((low(rel.prop) === 'stops' && !wantFam) || rel.reverse) { var cs = st.map(function (s) { return s.color; }).reverse(); st.forEach(function (s, k) { s.color = cs[k]; }); why.push('flipped'); }
            else {
                var xi = []; st.forEach(function (s, k) { if (famOf(s.color) === wantFam) xi.push(k); }); if (!xi.length) { why.push(wantFam ? 'no ' + wantFam + ' in "' + z.name + '"' : 'I could not tell which colour of "' + z.name + '" to change (say it, for example "the red to orange")'); return; }          // V3 S6 2026-10-06 (in-app A-0578 auto: "No null in ...")
                var mv = 0.25 * factor(rel, 1); if (mv > 0.9) mv = 0.9;
                if (dir < 0) { for (i = 0; i < n; i++) { if (xi.indexOf(i) !== -1) continue; var nb = xi.reduce(function (b, k) { return Math.abs(k - i) < Math.abs(b - i) ? k : b; }, xi[0]); st[i].pos = st[i].pos + (st[nb].pos - st[i].pos) * mv; } why.push('less ' + wantFam); }
                else { xi.forEach(function (k) { var nb2 = k + 1 < n && xi.indexOf(k + 1) === -1 ? k + 1 : (k - 1 >= 0 && xi.indexOf(k - 1) === -1 ? k - 1 : null); if (nb2 == null) return; st[k].pos = st[k].pos + (st[nb2].pos - st[k].pos) * mv; }); why.push('more ' + wantFam); }
                st.forEach(function (s) { s.pos = Math.round(clamp(s.pos, 0, 100)); });
            }
            ops.push({ kind: 'edit', zone: z.id, spec: { gradient: { stops: st, direction: z.gradient.direction || 'horizontal', fit: false } } });
        });
        if (!ops.length) return { ask: { q: why.length ? cap(why.join('; ')) + '.' + (/^no /.test(why[0]) ? ' Which colour should change?' : '') : 'The last change is not a gradient. Which gradient did you mean?', chips: [] } };
        return step('gradientEdit', why.join(', ') + ' (still a gradient)', ops, { kind: 'zone', zones: ids.slice(), parts: op._lastTarget && op._lastTarget.parts || null, layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect', edits_only: true, keeps_gradient: true });
    }
    // ADJUST with an absolute look on the last change ("make it white instead", "gold instead"): the SAME zones, never a wider scope (rule 3)
    function adjustAbs(op, E) {
        var L = op.look || {}, ids = op._zones || [], hx = hexOf(L.colour), ops = [];
        // IA1 2026-10-07 (train A-0345 'make it a gulf' -> 'no not that blue, more powder' recoloured the orange STRIPES blue too): a new colour for a last change that was a base + graphics
        // goes on the base zones; the graphics keep theirs unless the turn names them
        if (!W.SPB_PLAN_NOIA1 && hx && !L.gradient) { var nonG = ids.filter(function (id) { var z = zoneById(E, id); return z && !z.graphic; }); if (nonG.length && nonG.length < ids.length && !/\b(?:stripes?|lines?|pin ?stripes?|pin ?lines?|outlines?|flames?|bands?|graphics?|accents?)\b/i.test(String(op.said || (op._frameSaid || '')))) ids = nonG; }
        // lane R4-CONVO 2026-10-08 (in-app train A-0136 'flames on the hood' -> 'make them blue flames'): a colour edit on SpbFlames zones rewrote region.graphic.only to the new hex on the
        // fill zone too -> no flame pixel has that colour -> no mask -> the zone painted the WHOLE car (report: 119%, taken back). Flames are redrawn by SpbFlames.apply (replace: same undo step) in the new colour. Kill switch window.SPB_PLAN_NOFLAMERECOL
        if (!W.SPB_PLAN_NOFLAMERECOL && hx && !L.gradient) {
            var flz = ids.map(function (id) { return zoneById(E, id); }).filter(function (z) { return z && z.graphic && (z.graphic.item || z.graphic).kind === 'flames'; });
            if (flz.length && flz.length === ids.filter(function (id) { return zoneById(E, id); }).length) {
                var fg0 = flz[0].graphic.item || flz[0].graphic, fo = { part: fg0.part, style: fg0.style || 'hotrod', keep_decals: true, label: 'Flames', colours: [hx] }; if (fg0.scale != null) fo.scale = fg0.scale; if (fg0.band) fo.band = fg0.band;
                var fchk = null; try { fchk = W.SpbFlames && W.SpbFlames.check ? W.SpbFlames.check(fo) : null; } catch (eFc) { fchk = null; }
                if (!fchk) return step('flames', (fo.style === 'hotrod' ? 'hot rod' : fo.style) + ' flames redrawn in ' + (L.colour && L.colour.word || hx) + ' on ' + arr(fo.part).join(', '), [], { kind: 'part', parts: arr(fo.part), layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect' }, { flames: fo });
            }
        }
        ids.forEach(function (id) {
            var z = zoneById(E, id); if (!z) return; var sp = {};
            if (L.gradient) { var g = gradientSpec(L.gradient, op._lastTarget, E); if (g) sp.gradient = g; }
            else if (hx) { if (z.graphic) { var gi = clone(z.graphic), it = gi.item || gi; if (gi.only) gi.only = hx; else it.colour = hx; if (it.colours) it.colours = it.colours.map(function (c) { return String(c).toLowerCase() === String(z.colour).toLowerCase() ? hx : c; }); sp.region = { graphic: gi }; } sp.color = hx; }
            if (L.finish) { var fk = L.finish.keep_colour ? finishKey(L.finish, true) : (L.finish.key && /::/.test(L.finish.key) ? L.finish.key : finishKey(L.finish, false)); if (fk) sp.finish = fk; }
            if (L.stroke && L.stroke.px != null && z.graphic) sp.stroke_px = clamp(num(L.stroke.px, 6), 1, 60);
            if (L.scale != null) sp.scale = clamp(num(L.scale, 1), 0.05, 5);
            if (Object.keys(sp).length) ops.push({ kind: 'edit', zone: z.id, spec: sp });
        });
        if (!ops.length) return null;
        var aiL2 = []; ids.forEach(function (id) { var zq = zoneById(E, id); if (zq) arr(zq.layers).forEach(function (l) { if (isDecalLayer(E, l)) aiL2.push(l); }); });
        var aiS = step('adjust', 'changed ' + ops.length + ' zone' + (ops.length > 1 ? 's' : '') + ' of the last change (' + Object.keys(ops[0].spec).join(', ') + ')', ops, { kind: 'zone', zones: ids.slice(), parts: op._lastTarget && op._lastTarget.parts || null, layers: [], elements: [], whole: false, except: { parts: [], elements: [], layers: [] }, decals: 'protect', edits_only: true, colour: hx });
        if (aiL2.length && !W.SPB_PLAN_NOAI5) { aiS.scope.layers = uniq(aiL2); aiS.scope.decals = 'named'; }
        return aiS;
    }
    // MOVE CHANGE: the last change's zones re-placed on the new target (one undo step); an edit of zones that already existed = undo + re-plan
    function moveChange(op, E, frame) {
        var L = op._last || lastOf(E); if (!L || !L.op) return { ask: { q: 'Which change should move?', chips: [] } };
        var T = op.target && op.target.kind !== 'zone' ? op.target : null; if (!T && op.except && L.target) T = clone(L.target); if (!T) return { ask: askTarget('where should it go instead?', E) };
        var o2 = clone(L.op); delete o2.ref; var ot = clone(L.op.target || { kind: 'body' }); if (T.parts && /^(colour|layer|element)$/.test(ot.kind)) { ot.parts = arr(T.parts).slice(); if (T.portion) ot.portion = T.portion; o2.target = ot; } else o2.target = Object.assign({}, ot, T); if (T.parts && !/^(colour|layer|element)$/.test(ot.kind)) { o2.target.kind = 'part'; delete o2.target.layers; }
        if (T.kind === 'body') o2.target = { kind: 'body' };          // V4-E 2026-10-07: "the whole car instead" = the body, not body+the old part
        if (op.except) o2.except = arr(o2.except).concat(arr(op.except));
        var sub = planOp(o2, frame, normEnv(Object.assign({}, E, { zones: E.zones.filter(function (z) { return (L.added || []).indexOf(z.id) === -1; }), last: null, owner: E.owner, colourOf: E.colourOf, colourLayers: E.colourLayers, seamProbe: E.seamProbe, hiddenColour: E.hiddenColour /* V3 S6b */, layers: E.layers, bodyLayers: E.body, parts: E.parts })));
        if (sub.ask) return sub; var ns = sub.steps || [], adds = [], other = [];
        ns.forEach(function (s) { (s.ops || []).forEach(function (q) { if (q.kind === 'add') adds.push(q); else other.push(q); }); });
        var added = (L.added || []).slice(), ops = [];
        if (added.length && added.length === adds.length && !other.length && !ns.some(function (s) { return s.flames; }) && T.kind !== 'body') {          // V4-E 2026-10-07: not for a body move (the edit kept the zone's old part island in the app)
            adds.forEach(function (q, k) { var sp = clone(q.spec); delete sp.priority; ops.push({ kind: 'edit', zone: added[k], spec: { region: sp.region, name: sp.name } }); });
            var mv = step('moveChange', (op.except && tkey(T) === tkey(L.target) ? 'the last change now leaves out ' + exceptBits(arr(o2.except)).parts.map(function (p) { return 'the ' + p; }).join(' and ') : 'moved the last change to ' + nameOfT(T)), ops, Object.assign({}, ns[0].scope, { moved_from: L.target })); mv._rootOps = [o2]; mv._rootTarget = clone(o2.target); return { steps: [mv] };
        }
        var st = step('moveChange', 'took the last change back and made it on ' + nameOfT(T) + ' instead', [], ns[0] && ns[0].scope, { undo: 1 }); st._rootOps = [o2];
        return { steps: [st].concat(ns) };
    }
    // ASKS
    function chipFrame(label, op, patch) { var o = clone(op) || {}; delete o._last; delete o._zones; Object.keys(patch || {}).forEach(function (k) { o[k] = clone(patch[k]); }); return { label: label, frame: { v: 1, act: 'change', ops: [o], decals: 'protect', keep: [], missing: [], alts: [] } }; }
    function askTarget(q, E) { return { q: cap(q), chips: [] }; }
    // V4-E 2026-10-07 (task 1): an OBJECT that is not a car part ("the skull on the hood", "the spray can in the art") = one of the paint's real layers.
    //   A specific noun in a layer NAME ("Skull", "dragon_hood") and that layer has art there = ONE confident match: act on that layer (on the named parts).
    //   A generic word (logo / sticker / stripe / panel), only a side word in the name, or only ART on the named part (E.artLayers) = named choices (chips).
    //   Nothing = say so and offer the closest (the art on that part / on the car, the part itself, or a box). NEVER the whole body.
    var OBJ_STOP = { the: 1, and: 1, art: 1, artwork: 1, layer: 1, layr: 1, thing: 1, little: 1, big: 1, small: 1, car: 1, one: 1, only: 1, base: 1, colour: 1, color: 1, colors: 1, colours: 1, change: 1 };
    var OBJ_GENERIC = /^(logo|sponsor|decal|sticker|stripe|line|number|badge|emblem|lettering|letter|text|name|panel|shape|graphic|design|tape|thing|pattern|backing)$/;
    function objWords(s) { return low(s).replace(/['\u2019]s\b/g, '').split(/[^a-z0-9]+/).filter(function (w) { return w.length > 2 && !OBJ_STOP[w]; }).map(function (w) { return w.length > 4 && /ies$/.test(w) ? w.replace(/ies$/, 'y') : (w.length > 3 && /[^s]s$/.test(w) ? w.slice(0, -1) : w); }); }
    function guessLayer(T, E) {
        var obj = String(T.object || ''), headW = objWords(obj.split(/\s+(?:on|in|of|at|from|near|by|behind|under)\s+/i)[0]), hw = headW[headW.length - 1] || null, allW = objWords(obj), num = /number/.test(low(obj));
        var cand = E.layers.filter(function (l) { return l && l.name && l.visible !== false && !/template/i.test(String(l.role || '')) && (num || !/^numbers$/i.test(String(l.role || ''))); });
        var art = null; if (typeof E.artLayers === 'function') { try { art = E.artLayers(arr(T.parts)); } catch (e) { art = null; } }
        art = art ? art.filter(function (a) { return cand.some(function (l) { return l.name === a.name; }); }).sort(function (a, b) { return (b.pct || 0) - (a.pct || 0); }) : null;
        function hasArt(n) { return !art || art.some(function (a) { return a.name === n; }); }
        function byName(w) { return cand.filter(function (l) { return objWords(l.name).indexOf(w) !== -1 && hasArt(l.name); }).map(function (l) { return l.name; }); }
        var sure = hw && !OBJ_GENERIC.test(hw) ? byName(hw) : [];
        if (sure.length === 1) return { sure: sure[0], cands: [], art: art };
        var c = sure.slice(); allW.forEach(function (w) { byName(w).forEach(function (n) { if (c.indexOf(n) === -1) c.push(n); }); });
        var cw = T.colour && (T.colour.word || T.colour.hex); if (cw) { try { (E.colourLayers(cw) || []).forEach(function (n) { if (c.indexOf(n) === -1 && cand.some(function (l) { return l.name === n; })) c.push(n); }); } catch (e) {} }
        if (!(!W.SPB_W26_OFF && !c.length && /\bmirrors?\b/i.test(obj))) (art || []).forEach(function (a) { if (c.indexOf(a.name) === -1 && !E.body.some(function (b) { return b === a.name; })) c.push(a.name); });          // W26U 2026-10-10 (class 5, in-app K8 "chrome the mirrors" = "I could not find a layer for the mirror ... The art on the left side and right side is in Logos, Contingency Decals, Car_Decal. Which one is it?"): a mirror is never decal art; with no layer named for it the sponsor art on the sides is NOT a candidate, so the ask is the honest one (no mirror on this paint map: all of the sides instead, or draw a box)
        return { sure: null, cands: c.slice(0, 3), art: art };
    }
    function objectAsk(T, op, E, g, chipPatch) {          // V4-E 2026-10-07: the ask when the object is not ONE confident layer (named choices; nothing = say so + the closest)
        var obj = String(T.object || 'thing'), pn = arr(T.parts).length ? nameOfT({ kind: 'part', parts: arr(T.parts) }) : null, chips;
        chipPatch = chipPatch || function (n) { var t = clone(T); t.kind = 'layer'; t.layers = [n]; delete t.object; return { target: t }; };
        chips = g.cands.map(function (n) { return chipFrame(n + (pn ? ' (' + pn.replace(/^the /, '') + ')' : ''), op, chipPatch(n)); });
        var q;
        if (g.cands.length) q = 'I could not find a layer for the ' + obj + ' on this paint. ' + (g.art && g.art.length && pn ? 'The art on ' + pn + ' is in ' : 'It could be in ') + g.cands.join(', ') + '. Which one is it?';
        else { q = 'I could not find the ' + obj + ' on this paint: no layer is named for it' + (pn ? ' and there is no art on ' + pn : '') + '.' + (pn ? ' I can change all of ' + pn + ' instead, or you can draw a box around it.' : ' Draw a box around it, or tell me the layer it is on.'); if (pn && !chipPatch._except) chips.push(chipFrame(cap(pn.replace(/^the /, '')) + ': all of it', op, { target: { kind: 'part', parts: arr(T.parts).slice() } })); }
        if (!W.SPB_W26_OFF && pn && /\bmirrors?\b/i.test(obj)) q = "There is no separate mirror on this car's paint map (the mirrors are painted as part of " + pn + '). I can change all of ' + pn + ' instead, or you can draw a box around the mirror.';          // W26U 2026-10-10 (class 5): say so once, offer the nearest part
        chips.push({ label: 'Draw a box', frame: null, tool: 'box' });
        return { q: q, chips: chips, object: obj };
    }
    function askLayerFor(T, op, E) {
        var w = T.colour && (T.colour.word || T.colour.hex), ls = w ? E.colourLayers(w) : [];
        return { q: 'Which layer is the ' + (T.object || 'thing') + ' on?' + (ls.length ? ' The ' + w + ' is in ' + ls.join(', ') + '.' : ''), chips: ls.slice(0, 5).map(function (n) { var t = clone(T); t.layers = [n]; return chipFrame(n, op, { target: t }); }).concat([{ label: 'Draw a box', frame: null, tool: 'box' }]) };
    }
    var ACCENT_PIC = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="240" height="96" viewBox="0 0 240 96"><rect width="240" height="96" fill="#1b1d22"/><rect x="14" y="14" width="96" height="58" rx="10" fill="#2a63c9" stroke="#d9dde3" stroke-width="5"/><text x="62" y="88" fill="#e8e8e8" font-family="sans-serif" font-size="11" text-anchor="middle">Outline</text><rect x="130" y="14" width="96" height="58" rx="10" fill="#2a63c9"/><rect x="130" y="36" width="96" height="14" fill="#d9dde3"/><text x="178" y="88" fill="#e8e8e8" font-family="sans-serif" font-size="11" text-anchor="middle">Band</text></svg>');
    function accentAsk(op, T, E) {          // OWNER DECISION 2026-10-05: "silver accent" / "trim" with no shape named = ask EVERY time, outline vs band, with a picture
        var L = op.look || {}, c = (L.colour && (L.colour.word || L.colour.hex)) || 'silver', hx = hexOf(L.colour) || NAMED.silver, Lc = Object.assign({}, L, { colour: { word: (L.colour && L.colour.word) || 'silver', hex: hx } }); delete Lc.accent;
        if (!Lc.finish && METALLIC_WORD.test(c)) Lc.finish = { family: 'metallic', key: 'base::f_metallic' };          // the cheap Foundation metallic (see lineLook)
        return { q: 'A ' + c + ' accent on ' + nameOfT(T) + ': a thin line around its edge, or a band across it?', chips: [chipFrame('Thin ' + c + ' outline', op, { verb: 'outline', target: T, look: Object.assign({}, Lc, { stroke: { width: 'thin', px: 6 } }) }), chipFrame(cap(c) + ' band across it', op, { verb: 'stripe', target: T, look: Object.assign({}, Lc, { stroke: { width: 'medium', px: 90, n: 1, at: 0.5 } }) })], hint: { picture: ACCENT_PIC, alt: 'left: a line around the edge; right: a band across the middle' }, owner_rule: 'accent = ask each time (2026-10-05)' };
    }

    // ------------------------------------------------------------------ one op -> steps
    function hasLook(L) { return !!(L && (L.colour || L.gradient || L.finish || L.pattern || L.scale != null || L.stroke || L.layer || L.colours)); }
    function keepColour(op) {
        var L = op.look || {}, f = L.finish; if (!f) return false;
        if (f.keep_colour === true) return true; if (f.keep_colour === false) return false;
        if (L.colour || L.gradient || L.pattern) return false;
        return /^base::f_/.test(String(f.key || '')) || !f.key || ['part', 'body', 'layer'].indexOf(op.target && op.target.kind) !== -1;          // plan rule 4: a finish without a colour on a part / the body keeps the colour
    }
    function planOp(op0, frame, E) {
        if (op0 && !op0.ref && !op0.source && !op0.relative && E.last && op0.target && op0.target.kind === 'part' && !hasLook(op0.look) && !(op0.look && op0.look.spec) && /^(recolour|refinish|restyle|adjust|pattern|paint)$/.test(op0.verb || 'recolour')) { op0 = clone(op0); op0.ref = { to: 'last_change' }; }          // V4-E 2026-10-07 (task 2): a follow-up that names only a part ("and the hood", "do the roof too") = the last change's look on that part
        var rr = resolveRef(op0, E, frame); if (rr.err) return { ask: { q: cap(rr.err) + '. What should I change?', chips: [] } };
        var op = rr.op, verb = op.verb || 'recolour', T = op.target || { kind: 'body' }, decals = frame.decals || 'protect';
        if (!W.SPB_PLAN_NOAI2 && T.kind === 'zone' && !T.ref && !op._zones && arr(T.zones || T.zone).length) {          // AITER 2026-10-08: tweak THIS zone (named by id / name): relative / absolute edits on exactly it, never a wider scope
            var xz = arr(T.zones || T.zone).map(function (id) { return zoneById(E, id); }).filter(Boolean);
            if (!xz.length) return { ask: { q: 'I cannot find that zone any more. Which part or layer should change?', chips: [] } };
            op = clone(op); op._zones = xz.map(function (z) { return z.id; }); var xpp = []; xz.forEach(function (z) { if (z.parts) xpp = xpp.concat(z.parts); }); op._lastTarget = xpp.length ? { kind: 'part', parts: uniq(xpp) } : null; op._last = op._last || null;
        }
        var ex = exceptBits(arr(op.except).concat(arr(frame.keep)));
        if (T.kind === 'element' && ex.elements.indexOf(T.element) !== -1) ex.elements = ex.elements.filter(function (e) { return e !== T.element; });
        if (T.kind === 'body' && decals === 'include' && !W.SPB_PLAN_NOJ2W2 && ex.elements.length && !ex.parts.length && !ex.layers.length && ex.elements.every(function (e) { return /^(?:numbers|sponsors|logos)$/.test(e); })
            && !SOLID_RE.test(String(frame.said || '')) && !(/\blogos?\b|\bdecals?\b|\bstickers?\b/i.test(String(frame.said || '')) && ex.elements.indexOf('logos') === -1)) decals = 'protect';          // IA1 J2W2 2026-10-07 (orchestrator sealed harm class 1: all-but-X recolours painted the accent art + logo halos): kept numbers / sponsors / logos on a body job = the default protection (body paint layers only) + J2W
        if (T.kind === 'body' && decals === 'protect' && !W.SPB_PLAN_NOJ1P) ex.elements = ex.elements.filter(function (e) { return e !== 'numbers' && e !== 'sponsors'; });          // V4-G round 3 J1p: kept numbers / sponsors on a body job = the default decal protection (keeps the inverse path)
        var L = op.look || {}, P = L.pattern || L.graphic || {}, r;
        var badP = arr(T.parts).concat(arr(op.except).filter(function (x) { return x && x.kind === 'part'; }).reduce(function (a, x) { return a.concat(arr(x.parts)); }, [])).filter(function (p) { return E.parts.indexOf(p) === -1; });
        if (badP.length) return { ask: { q: 'This car has no ' + badP.join(' or ') + ' on its paint map. Which part did you mean?', chips: E.parts.slice(0, 6).map(function (p) { var t = clone(T); t.parts = [p]; return chipFrame(p, op, { target: t }); }) } };
        var objNote = [];          // V4-E 2026-10-07 (task 1): objects -> the paint's layers (guessLayer); one confident match = act, else named choices / say so
        while (ex.objects && ex.objects.length) {
            var xo = ex.objects[0], gx = guessLayer({ kind: 'object', object: xo, parts: T.parts }, E);
            if (!gx.sure) { var xp = function (n) { var ev = arr(op.except).map(function (e) { return (e && e.kind === 'object' && e.object === xo) ? { kind: 'layer', layers: [n] } : e; }); return { except: ev }; }; xp._except = true; return { ask: objectAsk({ kind: 'object', object: xo, parts: T.parts }, op, E, gx, xp) }; }
            ex.objects = ex.objects.slice(1); if (ex.layers.indexOf(gx.sure) === -1) ex.layers.push(gx.sure); objNote.push('kept out: the ' + xo + ' = the layer \u201c' + gx.sure + '\u201d');
        }
        if (T.kind === 'object' && !arr(T.layers).length && verb !== 'outline') { var go = guessLayer(T, E); if (!go.sure) return { ask: objectAsk(T, op, E, go) }; T = clone(T); T.layers = [go.sure]; op.target = T; objNote.push('the ' + T.object + ' = the layer \u201c' + go.sure + '\u201d' + (arr(T.parts).length ? ' on ' + nameOfT({ kind: 'part', parts: arr(T.parts) }) : '')); }
        if (T.kind === 'object' && arr(T.layers).length) { T = { kind: 'layer', layers: arr(T.layers).slice(), parts: T.parts }; op.target = T; }
        if (objNote.length) { var rO = planOp2(op, frame, E, T, verb, ex, L, P, decals); (rO.steps || []).forEach(function (s) { s.notes = (s.notes || []).concat(objNote); }); return rO; }
        return planOp2(op, frame, E, T, verb, ex, L, P, decals);
    }
    function aiFromWord(said) { var m = /\b(?:change|swap|switch|turn|make)\s+(?:the\s+|my\s+)?([a-z]+)\s+(?:to|into|for|with)\s+(?:a\s+|an\s+)?[a-z]+/i.exec(String(said || '')); if (!m) return null; return /^(?:red|orange|yellow|gold|green|teal|cyan|blue|navy|purple|violet|pink|magenta|white|black|grey|gray|silver|brown|bronze|lime|mint|olive|maroon|burgundy|cream|tan|turquoise)$/i.test(m[1]) ? m[1].toLowerCase() : null; }          // AITER: 'change gold to silver' -> gold
    function planOp2(op, frame, E, T, verb, ex, L, P, decals) {          // V4-E 2026-10-07: the rest of planOp (split so the object notes ride on every step)
        var r;
        if (L.spec && !L.finish && !L.colour && !L.gradient && !L.pattern) { var sv = L.spec, mt = num(sv.metal, null), rg = num(sv.rough, null), cc = num(sv.clearcoat, null), fam = null;          // V4-E 2026-10-07: spec numbers (R metal / G rough / B clearcoat) = the nearest Foundation finish, colours kept (was an ask)
            if (mt != null && mt >= 180) fam = (rg != null && rg > 90) ? 'brushed' : 'chrome'; else if (mt != null && mt >= 90) fam = (rg != null && rg > 140) ? 'matte metallic' : 'metallic';
            else if (rg != null) fam = rg <= 60 ? 'gloss' : (rg >= 170 ? 'matte' : 'satin'); else if (cc != null) fam = cc >= 100 ? 'satin' : 'gloss';
            if (fam) { L = Object.assign({}, L, { finish: { family: fam, keep_colour: true } }); op.look = L; if (!verb || verb === 'adjust' || verb === 'recolour') verb = op.verb = 'refinish'; }
        }
        if (verb === 'retarget') return moveChange(op, E, frame);
        if (!W.SPB_PLAN_NOES1 && !op._zones && E.last && arr(E.last.ids).length && !/^(stripe|pinline|outline|graphic)$/.test(verb || '') && /^(zone|colour)$/.test(T.kind || '') && (!op.relative || /^(intensity|opacity|amount|strength|more|less|)$/.test(low(op.relative.prop || '')))) {          // ESTRIPE 2026-10-08: 'gold first' / 'a touch more of that' on stripes just drawn must not reach the colour-swap / intensity paths below
            var esq = { _zones: arr(E.last.ids).slice(), said: op.said, _frameSaid: op._frameSaid, look: op.look, _lastTarget: E.last.target ? clone(E.last.target) : null }, esf0 = null; try { esf0 = stripeFollow(esq, E); } catch (eEs0) { esf0 = null; } if (esf0) return { steps: [esf0] };
        }
        if (!W.SPB_PLAN_NOAI3 && !op._zones && !op.relative && (T.kind === 'colour' || (T.kind === 'body' && aiFromWord(frame && frame.said))) && E.last && arr(E.last.ids).length && hexOf(L.colour) && !L.finish && !L.pattern && !L.gradient && /^(?:recolour|restyle|adjust|paint)$/.test(verb || 'recolour')) {          // AITER 2026-10-08 (in-app 'make the hood pink' -> 'change the pink to blue' added a NEW zone picking source pixels = nothing changed): the named colour is the colour of a zone of the last change = edit that zone
            var wF = T.kind === 'colour' ? famWord(T.colour) : famWord({ word: aiFromWord(frame && frame.said) }), swz = wF ? arr(E.last.ids).map(function (id) { return zoneById(E, id); }).filter(function (z) { return z && !z.catchAll && !z.muted && !z.graphic && (!z.mode || z.mode === 'solid') && hexOf(z.colour) && famOf(z.colour) === wF && (!arr(T.parts).length || !z.parts || z.parts.some(function (p) { return arr(T.parts).indexOf(p) !== -1; })); }) : [];
            if (swz.length) { op._zones = swz.map(function (z) { return z.id; }); var sp3 = []; swz.forEach(function (z) { if (z.parts) sp3 = sp3.concat(z.parts); }); op._lastTarget = sp3.length ? { kind: 'part', parts: uniq(sp3) } : (E.last.target ? clone(E.last.target) : null); var rsw = adjustAbs(op, E); if (rsw) { rsw.notes = (rsw.notes || []).concat(['the ' + wF + ' of the last change']); return { steps: [rsw] }; } op._zones = null; }
        }
        if (!op._zones && verb !== 'copy_look' && ((op.relative && /^(scale|width|stops)$/.test(low(op.relative.prop))) || (verb === 'adjust' && L.scale != null && !L.colour && !L.pattern && !L.finish) || (T.kind === 'graphic' && T.graphic && (verb === 'adjust' || verb === 'recolour' || (!L.colour && !L.gradient))))) { var oz = ownersOf(T, E); if (oz.length) { op._zones = oz; var opp = []; oz.forEach(function (id) { var zz = zoneById(E, id); if (zz && zz.parts) opp = opp.concat(zz.parts); }); op._lastTarget = (T.kind === 'graphic' && !arr(T.parts).length) ? (opp.length ? { kind: 'part', parts: uniq(opp) } : null) : clone(T); if (op._lastTarget && op._lastTarget.kind === 'graphic') op._lastTarget.kind = 'part'; } }
        if (op._zones && op._zones.length && verb !== 'copy_look' && !op.relative && !hasLook(L) && T.kind !== 'zone' && op._last && op._last.ops && op._last.ops.length) {          // "same on the roof" / "extend it to the trunk" / "and the hood too": the last change replayed on the new target, ADDED (the old one stays)
            var outP = [], pT = clone(T), LL = op._last, gz = (LL.added && LL.added.length ? LL.added : LL.ids).map(function (id) { return zoneById(E, id); }).filter(Boolean), copied = false, E0 = Object.assign({}, E, { last: null });
            var gOnly = /\b(stripes?|pinstripes?|pinlines?|lines?|outlines?|flames?)\b/.test(low(frame && frame.said)) && LL.ops.some(function (o) { return /^(outline|pinline|stripe|graphic)$/.test(o.verb) || /flame/.test(low(JSON.stringify(o.look || {}))); });          // V4-E 2026-10-07: "same stripes on the spoiler" = only the stripes of the last change
            for (var pi = 0; pi < LL.ops.length; pi++) {
                var po = clone(LL.ops[pi]); delete po.ref; if (po.verb === 'retarget' || (po.verb === 'adjust' && !hasLook(po.look) && !po.relative)) continue;
                if (gOnly && !(/^(outline|pinline|stripe|graphic)$/.test(po.verb) || /flame/.test(low(JSON.stringify(po.look || {}))))) continue;          /* V4-E 2026-10-07 */ po.target = (po.target && /^(colour|layer|element)$/.test(po.target.kind) && pT.parts) ? Object.assign(po.target, { parts: pT.parts }) : clone(pT);
                var isG = /^(outline|pinline|stripe|graphic)$/.test(po.verb) || /flame/.test(low(JSON.stringify(po.look || {})));
                if (!isG && LL.prim !== 'finishOnly') { var pz = gz.filter(function (z) { return !z.graphic; })[0]; if (pz && !copied) { copied = true; var cs = copyLook({ verb: 'copy_look', target: po.target, source: { kind: 'zone', zones: [pz.id] } }, po.target, exceptBits(arr(po.except)), E0, frame.decals || 'protect'); if (cs.ask) return cs; if (frame && frame.replace_last && !W.SPB_PLAN_NOJ7C) inlineLook(cs, pz); outP.push(cs); }          /* lane R3-EDIT 2026-10-07 J7c: the UNDO that runs first removes pz, so its look is written out now (in-app X-N01 'no, only the hood' hood went yellow -> blue) */ if (pz) continue; }
                if (isG) { var gzz = gz.filter(function (z) { return z.graphic; })[0]; if (gzz) { po.look = po.look || {}; if (isHex(gzz.colour)) po.look.colour = { word: gzz.colour, hex: gzz.colour }; var gpx = (gzz.graphic.item || gzz.graphic).stroke_px; if (gpx != null) po.look.stroke = Object.assign({}, po.look.stroke || {}, { px: gpx }); } }
                var pr = planOp(po, frame, E0); if (pr.ask) return pr; (pr.steps || []).forEach(function (s) { s.notes = (s.notes || []).concat(['the last change, also on ' + nameOfT(pT)]); outP.push(s); });
            }
            outP.forEach(function (s) { s.notes = s.notes || []; if (s.prim === 'copyLook') s.notes.push('the last change, also on ' + nameOfT(pT)); });
            if (outP.length) outP[0]._rootOps = LL.ops.map(function (o) { var c = clone(o); delete c.ref; if (c.verb !== 'retarget') c.target = (c.target && /^(colour|layer|element)$/.test(c.target.kind) && pT.parts) ? Object.assign(c.target, { parts: pT.parts }) : clone(pT); return c; });
            if (outP.length) return { steps: outP };
        }
        if (op._zones && op._zones.length && verb !== 'copy_look') {          // a follow-up on the last change: the same zones, never a wider scope
            if (!op.relative || /^(intensity|opacity|amount|strength|more|less|)$/.test(low(op.relative.prop || ''))) { var esf = null; try { esf = stripeFollow(op, E); } catch (eEs) { esf = null; } if (esf) return { steps: [esf] }; }          // ESTRIPE 2026-10-08
            if (op.relative) { r = relativeEdit(op, E); return r && r.ask ? r : (r ? { steps: [r] } : { ask: { q: 'There is nothing to adjust from the last change.', chips: [] } }); }
            if (verb === 'outline' || verb === 'pinline') { var so = outline(op, { kind: 'zone', zones: op._zones }, ex, E, decals); return so.ask ? so : { steps: [so] }; }
            r = adjustAbs(op, E); if (r) return { steps: [r] };
            if (T.kind === 'zone' && op._lastTarget && op._lastTarget.kind !== 'zone' && !op._lastTarget.ref && hasLook(L)) { T = clone(op._lastTarget); op.target = T; }          // V4-E 2026-10-07: a look the zones cannot take as an edit (a pattern) = painted on the last change's target (was "unsupported target zone")
            else if (T.kind === 'zone' && !hasLook(L)) return { ask: { q: 'What should change on the last change' + (op._lastTarget ? ' (' + nameOfT(op._lastTarget) + ')' : '') + ': the colour, the finish, the pattern or the size?', chips: [] } };          // V4-E 2026-10-07: was "Unsupported target zone"
        }
        if (L.accent && !L.stroke && !L.band) return { ask: accentAsk(op, T, E) };
        if (/flame/.test(low(P.concept || P.kind || P.id || '')) || (verb === 'graphic' && /flame/.test(low(P.kind || P.concept || op.said || '')))) { r = flames(op, T, ex, E); return r.ask ? r : { steps: [r] }; }
        if (verb === 'pinline' && T.between) { r = seam(op, T, ex, E, decals); return r.ask ? r : { steps: [r] }; }
        if (verb === 'outline' || (verb === 'pinline' && T.kind !== 'part')) { r = outline(op, T, ex, E, decals); return r.ask ? r : { steps: [r] }; }
        if (verb === 'stripe' || verb === 'pinline') { if (verb === 'pinline' && !(L.stroke && L.stroke.width)) L.stroke = Object.assign({ width: 'thin' }, L.stroke || {}); op.look = L; r = stripe(op, T, ex, E, decals); return r.ask ? r : { steps: [r] }; }
        if (verb === 'copy_look') { r = copyLook(op, T, ex, E, decals); return r.ask ? r : { steps: [r] }; }
        if (verb === 'adjust' && op.relative && !Array.isArray(op.relative) && /^(gloss|metal)$/.test(low(op.relative.prop))) {          // "shinier" / "more metallic" with nothing earlier to adjust = a Foundation finish on that target, colours kept
            var d = num(op.relative.dir, 1), fam = low(op.relative.prop) === 'metal' ? (d > 0 ? 'metallic' : 'satin') : (d > 0 ? 'gloss' : 'satin');
            r = finishOnly(T, ex, { finish: { family: fam, keep_colour: true } }, E, decals); return r.ask ? r : { steps: [r] };
        }
        if (verb === 'adjust' && op.relative) {          // hue / saturation / brightness / scale on a target with no earlier zone: a new zone on it, its own paint colour kept
            var rr2 = regionFor(T, E, ex, decals); if (rr2.err) return { ask: askTarget(rr2.err, E) };
            var spa = { name: '', color: 'source', region: rr2.region }, nm = [], bad = null;
            if (!W.SPB_PLAN_NOJ6L && T.kind === 'part' && typeof E.owner === 'function') { var ow6 = null; try { ow6 = E.owner(T); } catch (e6) { ow6 = null; } var oz6 = ow6 != null ? zoneById(E, ow6) : null;          // IA1 J6l 2026-10-07: start from what the part shows now
                if (!oz6 && typeof E.ownersIn === 'function') { var oi6 = null; try { oi6 = E.ownersIn(arr(T.parts)); } catch (e7) { oi6 = null; } arr(oi6).map(function (id) { return zoneById(E, id); }).filter(function (z) { return z && !z.catchAll && !z.muted && (!z.mode || z.mode === 'solid') && hexOf(z.colour) && !arr(z.layers).some(function (n) { return isDecalLayer(E, n); }); }).sort(function (x, y) { return num(x.idx, 99) - num(y.idx, 99); }).slice(0, 1).forEach(function (z) { oz6 = z; }); }          // IA1 J6l2: owner() skips layer-limited 'everything' zones
                if (oz6 && !oz6.catchAll && !oz6.muted && (!oz6.mode || oz6.mode === 'solid') && !(oz6.pattern && oz6.pattern !== 'none') && !oz6.graphic && hexOf(oz6.colour)) spa.color = hexOf(oz6.colour); }
            arr(op.relative).forEach(function (R) { var pr = low(R.prop), dd = num(R.dir, -1), amt = isFinite(Number(R.amount)) ? Math.abs(Number(R.amount)) : null; nm.push(pr + (dd < 0 ? ' down' : ' up'));
                if (pr === 'saturation') spa.saturation = (dd < 0 ? -1 : 1) * (amt || 20); else if (pr === 'lightness') spa.brightness = (dd < 0 ? -1 : 1) * (amt || 15); else if (pr === 'hue') spa.hue = (dd < 0 ? -1 : 1) * (amt || 15); else if (pr === 'scale') bad = bad || { ask: { q: 'Which texture should be ' + (dd < 0 ? 'finer' : 'bigger') + '?', chips: [] } }; else bad = bad || { ask: { q: 'What should change on ' + nameOfT(T) + '?', chips: [] } }; });
            if (bad) return bad; spa.name = cap(nm.join(', ') + ' ' + nameOfT(T).replace(/^the /, '')).slice(0, 48);
            return { steps: [step('adjustNew', spa.name, [{ kind: 'add', spec: spa }], rr2.scope)] };
        }
        if ((verb === 'refinish' || verb === 'restyle' || verb === 'adjust') && keepColour(op)) { r = finishOnly(T, ex, L, E, decals); return r.ask ? r : { steps: [r] }; }
        if (L.layer && (T.kind === 'layer' || op._lastTarget && op._lastTarget.kind === 'layer')) { var tl = arr((T.kind === 'layer' ? T : op._lastTarget).layers); return { steps: [step('layer', 'layer ' + tl.join(', ') + ': ' + JSON.stringify(L.layer).replace(/[{}"]/g, ''), [], { kind: 'layer', layers: tl, parts: null, elements: [], whole: false, except: ex, decals: 'named' }, { layerOps: tl.map(function (n) { var lo = { kind: 'layer', name: n, layer: n /* IA1 2026-10-07 (in-app A-0529 'set it to multiply' = "Car_Decal: layer is gone"): applyLayerOps finds the layer by .layer */ }; ['visible', 'opacity', 'opacity_delta', 'blend'].forEach(function (k) { if (L.layer[k] != null) lo[k] = L.layer[k]; }); return lo; }) })] }; }
        if (verb === 'hide' || verb === 'show') { var lay = arr(T.layers); if (!lay.length) return { ask: { q: 'Which layer?', chips: [] } }; return { steps: [step('layer', (verb === 'hide' ? 'hide ' : 'show ') + lay.join(', '), [], { kind: 'layer', layers: lay, parts: null, elements: [], whole: false, except: ex, decals: 'named' }, { layerOps: lay.map(function (n) { return { kind: 'layer', name: n, layer: n, visible: verb === 'show' }; }) })] }; }
        if (verb === 'graphic' && op.tool) return { steps: [step('graphic', 'graphic ' + op.tool, [{ kind: 'add', spec: { name: 'Graphic', color: hexOf(L.colour) || '#ffffff', region: protectGraphic({ graphic: Object.assign({ kind: op.tool }, op.args || {}) }, E, decals) } }], { kind: 'part', parts: arr(op.args && op.args.part), layers: [], elements: [], whole: false, except: ex, decals: 'protect' })] };
        r = paintOp(op, T, ex, E, decals); return r.ask ? r : { steps: [r] };
    }
    // V4-E 2026-10-07 (task 2/3): frame.missing slots the frame already answers. target: an op that refers to the last change (ref / target.ref) or names a
    // non-body target; a lost target on a ref follow-up = the parts the buyer SAID ("same stripes on the rear spoiler"). layer: a target that already has
    // layers, or an object (the planner guesses it from the paint's layers and asks with named choices itself). A body target the model doubted still asks.
    var SAID_PART = [[/\b(hood|bonnet)\b/, 'hood'], [/\b(roof|roofline)\b/, 'roof'], [/\b(trunk|deck ?lid|boot)\b/, 'trunk'], [/\b(spoiler|wing)\b/, 'spoiler'], [/\b(front bumper|nose|splitter|front fascia)\b/, 'front bumper'], [/\b(rear bumper|back bumper|tail|rear fascia)\b/, 'rear bumper'], [/\b(left side|left door|driver'?s? side)\b/, 'left side'], [/\b(right side|right door|passenger'?s? side)\b/, 'right side'], [/\b(doors|both sides|the sides)\b/, 'left side+right side']];
    function saidParts(said, E) { var s = low(said), out = []; SAID_PART.forEach(function (sp) { if (sp[0].test(s)) sp[1].split('+').forEach(function (p) { if (out.indexOf(p) === -1 && E.parts.indexOf(p) !== -1) out.push(p); }); }); return out; }
    function fillMissing(frame, E) {
        var f = clone(frame), ops = f.ops || [], o0 = ops[0] || null, keep = [];
        if (!o0 && f.said && E.last && arr(E.last.ops).length) {          // V4-E 2026-10-07 (task 3): an empty follow-up frame = what was SAID applied to the last change
            var s4 = low(f.said), sp4 = saidParts(f.said, E), kw4 = /\b(leave|keep|except|but not|not the|skip|without)\b/.test(s4), only4 = /\b(only|just)\b/.test(s4), LT = E.last.target || null, rs = null;
            if (kw4 && sp4.length) rs = { verb: 'retarget', target: null, ref: { to: 'last_change' }, except: [{ kind: 'part', parts: sp4 }] };
            else if (!sp4.length && /\b(whole|entire) (car|thing)\b|\beverything\b|\ball over\b/.test(s4)) rs = { verb: 'retarget', target: { kind: 'body' }, ref: { to: 'last_change' } };
            else if (sp4.length && only4) rs = { verb: 'retarget', target: LT && /^(layer|element|colour)$/.test(LT.kind) ? Object.assign(clone(LT), { parts: sp4 }) : { kind: 'part', parts: sp4 }, ref: { to: 'last_change' } };
            else if (sp4.length && !kw4) rs = { verb: 'adjust', target: { kind: 'part', parts: sp4 }, look: {}, ref: { to: 'last_change' } };
            if (rs) { ops = f.ops = [rs]; o0 = rs; f.missing = f.missing.filter(function (m) { return !/^(target|what|look|colour|where)$/.test(m); }); }
        }
        f.missing.forEach(function (m) {
            if (!o0) { keep.push(m); return; }
            var T0 = o0.target || null, hasRef = !!(o0.ref || (T0 && T0.ref)) && !!E.last;
            if (m === 'target') {
                if (hasRef && T0 && !T0.ref && T0.kind !== 'zone' && T0.kind !== 'body') return;
                if (!T0 || T0.ref || T0.kind === 'zone') { var sp = f.said ? saidParts(f.said, E) : []; var lp = E.last && E.last.target ? arr(E.last.target.parts) : [];
                    if (sp.length && hasRef && sp.join('+') !== lp.join('+')) { ops.forEach(function (o) { if (o.ref || (o.target && o.target.ref) || !o.target) { o.target = { kind: 'part', parts: sp.slice() }; if (!o.ref) o.ref = { to: 'last_change' }; } }); return; }
                    if (hasRef && hasLook(o0.look)) return; }
                if (T0 && /^(part|layer|element|colour|graphic|object)$/.test(T0.kind) && (arr(T0.parts).length || arr(T0.layers).length || T0.element || T0.colour || T0.object || T0.graphic)) return;
            }
            if ((m === 'what' || m === 'look') && !w3sOff('noW3Sf') && T0 && T0.kind === 'part' && arr(T0.parts).length && !hasLook(o0.look) && E.last && arr(E.last.ops).length && /\b(?:also|too|as well|same|include|that one|there|yes|again|likewise|and)\b/.test(low(f.said || ''))) return;          // W3-SCOPE 2026-10-09 (kill noW3S): 'bonnet also, yes, include' = the last look on that part (planOp's last_change ref), not a question
            if (m === 'layer' && T0 && (arr(T0.layers).length || T0.kind === 'object')) return;
            keep.push(m);
        });
        f.missing = keep; return f;
    }
    function w3sOff(k) { try { var c = W.SPB_OF_CFG; return !!(c && (c.noW3S || (k && c[k]))); } catch (e) { return false; } }
    function plan(frame, env) {
        var E = normEnv(env), out = { v: 1, ok: true, act: 'nothing', steps: [], ask: null, notes: [], errors: [], said: frame && frame.said || '' }; CUR_SAID = String(frame && frame.said || '');          // IA1 J2W
        if (!frame || frame.v !== 1) { out.ok = false; out.errors.push('not a v1 frame'); return out; }
        if (frame.act === 'undo' || frame.act === 'redo') { out.act = 'change'; for (var u = 0; u < Math.max(1, Math.min(10, num(frame.n, 1))); u++) out.steps.push(step(frame.act, frame.act, [], null, frame.act === 'undo' ? { undo: 1 } : { redo: 1 })); return out; }
        if (frame.act !== 'change') { out.act = frame.act === 'ask_back' ? 'ask_back' : frame.act; return out; }          // rule 5: a question / list / nothing never produces ops
        if ((frame.missing || []).length) frame = fillMissing(frame, E);          // V4-E 2026-10-07
        if ((frame.missing || []).length) {          // one question for the first missing slot (rule 6: alts are never applied)
            var m = frame.missing[0], o0 = (frame.ops || [])[0] || {}, T0 = o0.target || {};
            out.act = 'ask_back';
            if (m === 'layer') out.ask = askLayerFor(T0, o0, E);
            else if (m === 'colour') out.ask = { q: 'Which colour for ' + nameOfT(T0) + '?', chips: ['white', 'black', 'red', 'gold', 'silver'].map(function (c) { return chipFrame(c, o0, { look: Object.assign({}, o0.look || {}, { colour: { word: c, hex: NAMED[c] } }) }); }) };
            else if (m === 'target') out.ask = { q: 'Where should that go?', chips: CANON.slice(0, 5).map(function (p) { return chipFrame(p, o0, { target: { kind: 'part', parts: [p] } }); }) };
            if (m === 'target' && !w3sOff('noW3Sh') && !(E.last && arr(E.last.ops).length) && !/\b(?:idk|dunno|maybe|mybe|perhaps|something|anything|kinda|sorta|vibes?|feels?|theme|style|surprise|whatever|ideas?|suggest\w*|any|some)\b/.test(low(frame.said || '')) && !/\b(?:it|that|this|them|those|these|its|there|same|again)\b/.test(low(frame.said || ''))) out.ask.hidden = true;          // W3-SCOPE 2026-10-09 (kill SPB_OF_CFG.noW3S): a target the parser could not read is ASKED, never handed to the regex reader that falls back to the whole body ('nums black pls' / 'top part chrome' repainted the car)
            else out.ask = { q: 'Can you say a bit more (' + m + ')?', chips: [] };
            return out;
        }
        var ops = frame.ops || [];
        for (var i = 0; i < ops.length; i++) {
            var r = planOp(ops[i], frame, E);
            if (r.ask && ops.length > 1 && ops[i].target && ops[i].target.kind === 'object') { out.notes.push('skipped "' + (ops[i].target.object || 'object') + '": ' + r.ask.q); continue; }
            if (r.ask) { out.act = 'ask_back'; out.ask = r.ask; out.steps = []; if (ops[i].target && ops[i].target.kind === 'object' && !w3sOff('noW3Sh') && !/\b(?:more|less|bigger|smaller|again|another|it|that|them)\b/.test(low(frame.said || ''))) out.ask.hidden = true; /* W3-SCOPE 2026-10-09: a named art object that is not found asks, never the whole body */ return out; }
            (r.steps || []).forEach(function (s) { s.op = i; out.steps.push(s); });
            if (!W.SPB_PLAN_NOAI6 && i < ops.length - 1) (r.steps || []).forEach(function (s) { (s.ops || []).forEach(function (o) { if (o && o.kind === 'edit' && o.spec && /^#[0-9a-f]{6}$/i.test(String(o.spec.color || ''))) { var zz = zoneById(E, o.zone); if (zz) { var zi = E.zones.indexOf(zz); if (zi >= 0) { E.zones = E.zones.slice(); zz = E.zones[zi] = clone(zz); } zz.colour = o.spec.color; zz.mode = 'solid'; } } }); });          // AITER 2026-10-08: 'brighten it and change pink to blue': the later relative tweak starts from the colour the earlier op just set (kill: SPB_PLAN_NOAI6)
        }
        var lastIds4 = E.last ? arr(E.last.ids).concat(arr(E.last.added)).map(String) : [], allOps4 = [].concat.apply([], out.steps.map(function (s) { return s.ops || []; }));
        var editsLast4 = allOps4.length && allOps4.every(function (o) { return o.kind === 'edit' && lastIds4.indexOf(String(o.zone)) !== -1; });          // V4-E 2026-10-07: the plan only edits the last change's zones = the edit replaces it; an undo first would delete the zones it edits (in-app: "that zone no longer exists")
        if (frame.replace_last && out.steps.length && !editsLast4 && !out.steps.some(function (s) { return s.undo; })) out.steps.unshift(step('undo', 'took the last change back first', [], null, { undo: 1 }));
        out.act = out.steps.length ? 'change' : 'nothing';
        return out;
    }

    // ------------------------------------------------------------------ simulate (Node harness, dry runs): apply a plan to a symbolic env
    var _sid = 0;
    function zoneFromSpec(sp, id) {
        var r = sp.region || {}, g = r.graphic || null, parts = r.island ? arr(r.island) : (g ? arr((g.item || g).part) : null);
        if (sp.copy_look_from != null && zoneFromSpec._Z) { var cz = zoneFromSpec._Z.filter(function (z) { return String(z.id) === String(sp.copy_look_from); })[0]; if (cz) { var cp = clone(cz); cp.id = id; cp.name = sp.name || id; cp.catchAll = undefined; cp.layers = arr(r.layers); cp.parts = parts; cp.graphic = g ? clone(g) : cp.graphic; cp.region = clone(r); return cp; } }          // V4-E 2026-10-07
        return { id: id, name: sp.name || id, mode: sp.gradient ? 'gradient' : (isHex(sp.color) ? 'solid' : (sp.color === 'source' ? 'source' : 'finish')), colour: isHex(sp.color) ? sp.color : null, gradient: sp.gradient ? { stops: clone(sp.gradient.stops), direction: sp.gradient.direction } : null,
            base: sp.finish ? String(sp.finish).replace(/^[a-z]+::/, '') : 'gloss', finish: null, scale: sp.scale != null ? sp.scale : 1, pattern: sp.pattern ? sp.pattern.id : null, patternScale: sp.pattern && sp.pattern.scale != null ? sp.pattern.scale : 1, layers: arr(r.layers), parts: parts, graphic: g ? clone(g) : null, region: clone(r), s5spec: sp.color === 'source' && /^base::f_/.test(String(sp.finish || '')) };
    }
    function simulate(pl, env) {
        var E = Object.assign({}, env || {}), Z = (E.zones || []).map(function (z) { return clone(z); }), ids = [], added = [];
        E.zones = Z; zoneFromSpec._Z = Z;          // V4-E 2026-10-07: copy_look_from sources
        (pl.steps || []).forEach(function (s) {
            if (s.undo && E.last) { Z = Z.filter(function (z) { return (E.last.added || []).indexOf(z.id) === -1; }); E.zones = Z; E.last = null; }
            if (s.flames) { var nid = 's5z' + (++_sid); Z.unshift({ id: nid, name: 'Flames', mode: 'solid', parts: arr(s.flames.part), graphic: { kind: 'flames', part: s.flames.part } }); ids.push(nid); added.push(nid); }
            (s.ops || []).forEach(function (q) {
                if (q.kind === 'add') { var id = 's5z' + (++_sid), z = zoneFromSpec(q.spec, id); Z.unshift(z); ids.push(id); added.push(id); }
                else if (q.kind === 'duplicate') { var src = Z.filter(function (z) { return z.id === q.zone; })[0]; if (!src) return; var id2 = 's5z' + (++_sid), d = clone(src); d.id = id2; d.name = q.spec.name || d.name; if (q.spec.finish) d.base = String(q.spec.finish).replace(/^[a-z]+::/, ''); if (q.spec.region) { d.region = clone(q.spec.region); if (q.spec.region.island) d.parts = arr(q.spec.region.island); } Z.splice(Z.indexOf(src), 0, d); ids.push(id2); added.push(id2); }
                else if (q.kind === 'edit') {
                    var t = Z.filter(function (z) { return z.id === q.zone; })[0]; if (!t) return; var sp = q.spec; ids.push(t.id);
                    if (sp.stroke_px != null && t.graphic) (t.graphic.item || t.graphic).stroke_px = sp.stroke_px;
                    if (sp.gradient) { t.mode = 'gradient'; t.gradient = { stops: clone(sp.gradient.stops), direction: sp.gradient.direction }; }
                    if (isHex(sp.color)) { t.mode = 'solid'; t.colour = sp.color; }
                    if (sp.region) { t.region = clone(sp.region); if (sp.region.graphic) t.graphic = clone(sp.region.graphic); t.parts = sp.region.island ? arr(sp.region.island) : (sp.region.graphic ? arr((sp.region.graphic.item || sp.region.graphic).part) : t.parts); }
                    if (sp.scale != null) { t.s5 = Object.assign({}, t.s5 || {}, { lastScale: t.scale }); t.scale = sp.scale; }
                    if (sp.pattern && sp.pattern.scale != null) { t.s5 = Object.assign({}, t.s5 || {}, { lastScale: t.patternScale }); t.patternScale = sp.pattern.scale; } if (sp.pattern && sp.pattern.rotation != null) t.patternRotation = sp.pattern.rotation; if (sp.pattern && sp.pattern.opacity != null) t.patternOpacity = sp.pattern.opacity; if (sp.rotation != null) t.baseRotation = sp.rotation; if (sp.intensity != null) t.intensity = sp.intensity;
                    if (sp.finish) t.base = String(sp.finish).replace(/^[a-z]+::/, ''); if (sp.saturation != null) t.saturation = sp.saturation; if (sp.brightness != null) t.brightness = sp.brightness;
                    if (sp.spec_shift) { var ss = arr(t.specShift).length ? t.specShift.slice() : [0, 0, 0]; if (sp.spec_shift.metal != null) ss[0] = sp.spec_shift.metal; if (sp.spec_shift.rough != null) ss[1] = sp.spec_shift.rough; t.specShift = ss; }
                    if (sp.name) t.name = sp.name;
                }
            });
        });
        if (ids.length) { var s0 = pl.steps.filter(function (s) { return s.ops && s.ops.length || s.flames; })[0] || pl.steps[0]; var prevL = E.last, editsOnly = !added.length && prevL; E.history = (E.history || []).slice(); E.last = { ops: editsOnly ? (pl._rootOps || prevL.ops) : (pl._rootOps || pl._frameOps || null), ids: uniq(ids), added: uniq(added), prim: s0 && s0.prim, op: (s0 && s0._op) || null, target: s0 && s0.scope ? scopeTarget(s0.scope) : null, look: s0 && s0._look || null }; }
        if (E.last && pl._rootOps && pl._rootOps[0] && pl._rootOps[0].target) { E.last.target = clone(pl._rootOps[0].target); E.last.op = clone(pl._rootOps[0]); }
        if (E.last && editsOnly) { E.last.added = prevL.added; E.last.prim = pl._rootOps ? E.last.prim : prevL.prim; if (!pl._rootOps) E.last.target = prevL.target; }
        if (E.last && E.history && (!E.history.length || E.history[E.history.length - 1] !== E.last)) E.history.push(E.last);
        return E;
    }
    function scopeTarget(sc) { if (!sc) return null; if (sc.parts && sc.parts.length) return { kind: 'part', parts: sc.parts.slice() }; if (sc.whole) return { kind: 'body' }; if (sc.layers && sc.layers.length && sc.kind === 'layer') return { kind: 'layer', layers: sc.layers.slice() }; if (sc.elements && sc.elements.length) return { kind: 'element', element: sc.elements[0] }; return null; }
    function withOps(pl, frame) { if (frame && frame.act === 'change') pl._frameOps = clone(frame.ops || []); (pl.steps || []).forEach(function (s) { if (s._rootOps) { pl._rootOps = s._rootOps; pl._rootTarget = s._rootTarget || null; } }); (pl.steps || []).forEach(function (s) { var o = (frame.ops || [])[s.op || 0]; if (o) { s._op = clone(o); delete s._op._last; delete s._op._zones; s._look = clone(o.look || null); } }); return pl; }

    // ------------------------------------------------------------------ the app: live env, run, toQueue
    var _last = null, _hist = [];
    function zoneRec(z, i) {
        var Zk = W.SpbProZone, ids = Array.isArray(z.sourceLayers) && z.sourceLayers.length ? z.sourceLayers : (z.sourceLayer ? [z.sourceLayer] : []), Ls = (typeof _psdLayers !== 'undefined' && _psdLayers) ? _psdLayers : [];
        var parts = null; try { if (z._aiPartProv && z._aiPartProv.r) { var pr = JSON.parse(z._aiPartProv.r); parts = pr.island ? arr(pr.island) : null; } } catch (e) {} if (!parts && z._graphic) parts = arr((z._graphic.item || z._graphic).part); if (!parts && z._s5 && z._s5.parts) parts = z._s5.parts.slice();
        var ca = Zk && Zk.catchAll ? Zk.catchAll(z) : null; if (ca && ca !== 'remaining' && (ids.length || z.useRegion)) ca = null;          // a layer-limited "everything" zone is a real paint zone, not the catch-all
        return { id: String(z.id), name: z.name, idx: i, catchAll: ca, muted: !!z.muted, mode: z.baseColorMode, colour: z.baseColor, gradient: z.baseColorMode === 'gradient' ? { stops: clone(z.gradientStops), direction: z.gradientDirection } : null,
            base: z.base || null, finish: z.finish || null, scale: z.baseScale != null ? z.baseScale : 1, pattern: z.pattern || null, patternScale: z.scale != null ? z.scale : 1, layers: ids.map(function (id) { var l = Ls.filter(function (q) { return q.id === id; })[0]; return l ? l.name : id; }),
            useRegion: !!z.useRegion, graphic: z._graphic ? clone(z._graphic) : null, parts: parts, s5: z._s5 || null, s5spec: !!(z._s5 && z._s5.prim === 'finishOnly'), specShift: [z.specShiftR || 0, z.specShiftG || 0, z.specShiftB || 0], saturation: z.baseSaturationAdjust || 0, brightness: z.baseBrightnessAdjust || 0, baseStrength: z.baseStrength != null ? z.baseStrength : 1, patternRotation: z.rotation || 0, baseRotation: z.baseRotation || 0, patternOpacity: z.patternOpacity != null ? z.patternOpacity : 100, intensity: z.intensity != null ? Number(z.intensity) : 100 };
    }
    function visLive(T, Zk, Z) {          // V4-G J2a/J2c: the colour a part shows in the app = the solid zone that owns most of it (null = a catch-all / source / gradient owns it)
        try { if (!T || T.kind !== 'part' || !Zk) return null; var pr = Zk.probeRegion({ island: arr(T.parts).length > 1 ? arr(T.parts) : arr(T.parts)[0] }), ow = (pr && pr.owners) || [], best = null;
            ow.forEach(function (o) { var z = Z[o.i]; if (!z || z.muted) return; if (!best || o.pct > best.pct) best = o; }); var bz = best ? Z[best.i] : null;
            return bz && (W.SPB_PLAN_NOJ4V ? !Zk.catchAll(bz) : true) && bz.baseColorMode === 'solid' && isHex(bz.baseColor) ? bz.baseColor : null; } catch (e) { return null; }          // V4-G round 4 J4v: a solid catch-all ('Seafoam Chalk' over everything) IS the colour you see (in-app R4-1 faded to the source yellow)
    }
    function live() {
        var C = W.SpbProCar, Zk = W.SpbProZone, rl = []; try { rl = C && C.roles ? C.roles() : []; } catch (e) {}
        var Z = []; try { Z = (typeof zones !== 'undefined' && zones) ? zones : []; } catch (e2) {}
        var flat = !rl.length;
        return {
            layers: rl.map(function (r) { return { id: r.id, name: r.name, group: r.group, role: r.role, visible: r.visible }; }), parts: (function () { try { return C.parts(); } catch (e) { return []; } })(), zones: Z.map(zoneRec), last: _last, history: _hist.concat(_last ? [_last] : []), flat: flat,
            dominantOf: function (ps) {          // V4-G J2b: the part's dominant body colour(s) when distinct accent art shares the part (1.5-40% of it); null = paint the whole part
                try { var isl = ps.length > 1 ? ps : ps[0], cs = Zk.bodyColours({ island: isl }); if (!cs || !cs.length) return null;
                    var all = Zk.probeRegion({ island: isl, layers: rl.filter(function (x) { return /body paint/i.test(String(x.role || '')) && x.visible !== false; }).map(function (x) { return x.name; }) }), sel = Zk.probeRegion({ island: isl, colors: cs, tolerance: 48 });
                    var a = all && all.share_pct, b = sel && sel.share_pct; if (!a || !b) return null; var f = b / a;
                    if (ps.length > 1 && !W.SPB_PLAN_NOR13M) { var bad13 = false; ps.forEach(function (q) { try { var ai = Zk.probeRegion({ island: q, layers: rl.filter(function (x) { return /body paint/i.test(String(x.role || '')) && x.visible !== false; }).map(function (x) { return x.name; }) }), si = Zk.probeRegion({ island: q, colors: cs, tolerance: 48 }); if (!ai || !ai.share_pct || !si || si.share_pct / ai.share_pct < 0.6) bad13 = true; } catch (eq) { bad13 = true; } }); if (bad13) return null; }          // R13-CONVO2 2026-10-08: 'make all three red' after the trunk was already repainted blue: a named part that does not share the dominant colour = paint every named part whole. Kill: window.SPB_PLAN_NOR13M
                    if (f >= 0.6 && f <= 0.985 && cs.length > 1 && !W.SPB_PLAN_NOH1A) { var s1 = Zk.probeRegion({ island: isl, colors: [cs[0]], tolerance: 48 }), f1 = s1 && s1.share_pct ? s1.share_pct / a : 0; if (f1 >= 0.35) return { colors: [cs[0]], tol: 48, frac: Math.round(f1 * 1000) / 1000, artKept: cs.slice(1) }; }          // lane R3-EDIT 2026-10-07 H1a: flat ss "make the hood red" recoloured yellow AND the black logo backing (logo art turned red) -> top colour only, logo kept. Kill switch: window.SPB_PLAN_NOH1A
                    return f >= 0.6 && f <= 0.985 ? { colors: cs, tol: 48, frac: Math.round(f * 1000) / 1000 } : null; } catch (e) { return null; }
            },
            dominantBody: function (bl) {          // IA1 J2W 2026-10-07: the car's dominant body colour(s) when other art shares the body paint layers (1.5-40% of them); null = paint it all
                try { var lays = arr(bl).length ? arr(bl) : rl.filter(function (x) { return /body paint/i.test(String(x.role || '')) && x.visible !== false; }).map(function (x) { return x.name; }); if (!lays.length) return null;
                    var cs = Zk.bodyColours({}); if (!cs || !cs.length) return null;
                    var all = Zk.probeRegion({ layers: lays }), sel = Zk.probeRegion({ layers: lays, colors: cs, tolerance: 48 });
                    var a = all && all.share_pct, b = sel && sel.share_pct; if (!a || !b) return null; var f = b / a; return f >= 0.6 && f <= 0.985 ? { colors: cs, tol: 48, frac: Math.round(f * 1000) / 1000 } : null; } catch (e) { return null; }
            },
            numFill: function (names) {          // [SPB-W28 2026-10-10 coordinator item 6a] the FILL colour of the numbers layer(s) when the art also holds an outline / shadow colour: {hex, tol}; null = one colour only (recolour all of it)
                try { if (W.SPB_W28_NUMFILL_OFF) return null; var cs = (Zk.layerColours(arr(names), 6) || []).filter(function (c) { return c && /^#[0-9a-f]{6}$/i.test(String(c.hex)) && c.share_pct >= 2; }); if (cs.length < 2 || cs[0].share_pct >= 97) return null;
                    var rg = function (h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }, f = rg(cs[0].hex), md = 999;
                    cs.slice(1).forEach(function (q) { var o = rg(q.hex), dr = o[0] - f[0], dg = o[1] - f[1], db = o[2] - f[2]; md = Math.min(md, Math.sqrt(dr * dr * 0.30 + dg * dg * 0.59 + db * db * 0.11)); });
                    return { hex: String(cs[0].hex).toLowerCase(), tol: Math.max(12, Math.min(36, Math.round(md * 0.5))), others: cs.slice(1).map(function (q) { return String(q.hex).toLowerCase(); }) }; } catch (e) { return null; }
            },
            visibleOf: function (T) { return visLive(T, Zk, Z); },          // V4-G J2a
            owner: function (T) {          // the zone that paints most of a part / element / layer now (never the catch-all)
                try {
                    var r = T.kind === 'part' ? { island: arr(T.parts).length > 1 ? arr(T.parts) : arr(T.parts)[0] } : (T.kind === 'element' ? (flat ? { element: T.element } : { layers: rl.filter(function (x) { return (T.element === 'numbers' ? /^numbers$/i : /logo|sponsor|decal/i).test(x.role || ''); }).map(function (x) { return x.name; }) }) : (T.kind === 'layer' ? { layers: arr(T.layers) } : null));
                    if (!r) return null; var p = Zk.probeRegion(r), ow = (p && p.owners) || [], best = null;
                    ow.forEach(function (o) { var z = Z[o.i]; if (!z || Zk.catchAll(z) || o.pct < 20) return; if (!best || o.pct > best.pct) best = o; });
                    return best ? String(Z[best.i].id) : null;
                } catch (e) { return null; }
            },
            ownersIn: function (parts) { try { var p = Zk.probeRegion({ island: parts.length > 1 ? parts : parts[0] }), ow = (p && p.owners) || []; return ow.filter(function (o) { return o.pct >= 0.5 && Z[o.i]; }).map(function (o) { return String(Z[o.i].id); }); } catch (e) { return null; } },
            colourOf: function (T, word26) { if (!W.SPB_PLAN_NOJ2A && T && T.kind === 'part') { var v0 = visLive(T, Zk, Z); if (v0) return v0; }
                // W26U 2026-10-10 (class 7, "make the hood match the colour in the Logos layer" / "the trunk needs to be the exact colour of the numbers"): a LAYER / element source is sampled from that layer's OWN pixels
                // (Zk.layerColours, most common first; the colour family of `word26` when the buyer named one: "the red in our logo layer"). Before: Zk.bodyColours ignores the layer names and returned the CAR's body colour.
                // Kill: window.SPB_W26_OFF or window.SPB_PLAN_NOW26L.
                if (!W.SPB_W26_OFF && !W.SPB_PLAN_NOW26L && T && (T.kind === 'layer' || (T.kind === 'element' && !flat)) && Zk && typeof Zk.layerColours === 'function') {
                    try { var nm26 = T.kind === 'layer' ? arr(T.layers) : rl.filter(function (x) { return (T.element === 'numbers' ? /^numbers$/i : /logo|sponsor|decal/i).test(x.role || ''); }).map(function (x) { return x.name; });
                        var lc26 = nm26.length ? (Zk.layerColours(nm26, 8) || []) : [], fam26 = word26 ? famWord({ word: word26 }) : null, hit26 = null;
                        if (fam26) lc26.forEach(function (c) { if (!hit26 && c && isHex(c.hex) && famOf(c.hex) === fam26) hit26 = c; });
                        if (!hit26 && !fam26) hit26 = lc26[0];
                        if (hit26 && isHex(hit26.hex)) return hit26.hex; } catch (eW26) {}
                }
                try { var r = T.kind === 'part' ? { island: arr(T.parts)[0] } : (T.kind === 'layer' ? { layers: arr(T.layers) } : (T.kind === 'element' && !flat ? { layers: rl.filter(function (x) { return (T.element === 'numbers' ? /^numbers$/i : /logo|sponsor|decal/i).test(x.role || ''); }).map(function (x) { return x.name; }) } : null)); var c = r ? Zk.bodyColours(r) : []; return c && c[0] || null; } catch (e) { return null; } },
            hiddenColour: function (region) {          // V3 S6b 2026-10-07 H2: share of the region's matching source pixels that another zone paints a far-off colour over (what the buyer does NOT see)
                var p = Zk.probeRegion(region), ow = (p && p.owners) || [], hx = arr(region.colors)[0], hid = 0, best = null; if (!p || !hx) return null;
                var rgb = function (h) { h = String(h || '').replace('#', ''); return h.length === 6 ? [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)] : null; }, a = rgb(hx);
                ow.forEach(function (o) { var z = Z[o.i]; if (!z || z.muted || z.baseColorMode !== 'solid') return; var b = rgb(z.baseColor); if (!a || !b) return; var d = Math.sqrt((a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) + (a[2] - b[2]) * (a[2] - b[2])); if (d > 90) { hid += o.pct; if (!best || o.pct > best.pct) best = { pct: o.pct, name: z.name || 'a zone' }; } });
                return { hits: p.share_pct || 0, hidden: hid / 100, by: best ? best.name : null };
            },
            colourLayers: function (word) { var hx = hexOf({ word: word }) || (isHex(word) ? word : null), out = []; if (!hx) return out; rl.forEach(function (x) { if (!x.visible || /template/.test(x.role || '')) return; try { var p = Zk.probeRegion({ colors: [hx], tolerance: 40, layers: [x.name] }); if (p && p.share_pct >= 0.05) out.push(x.name); } catch (e) {} }); return out; },
            seamProbe: function (item) { try { var G = W.SpbGraphics; return G && G.S5 ? G.S5.seamMask(item, null, [item.colour]) : null; } catch (e) { return null; } },
            artLayers: function (parts) {          // V4-E 2026-10-07: visible non-body, non-template layers with art on those parts (or anywhere), share of the canvas in %
                var out = [], ps = arr(parts); rl.forEach(function (x) { if (x.visible === false || /template|body paint/i.test(x.role || '')) return; try { var q = { layers: [x.name] }; if (ps.length) q.island = ps.length > 1 ? ps : ps[0]; var p = Zk.probeRegion(q); if (p && p.share_pct >= 0.02) out.push({ name: x.name, role: x.role, pct: p.share_pct }); } catch (e) {} }); return out;
            }
        };
    }
    function zIdx(id) { var Z = (typeof zones !== 'undefined' && zones) ? zones : []; for (var i = 0; i < Z.length; i++) if (Z[i] && String(Z[i].id) === String(id)) return i; return -1; }
    function toQueue(pl) {          // S6/S7: the zone ops in js/spb-pro-ai.js applyQueue form (zone = index now); layer ops pass through
        var q = []; (pl && pl.steps || []).forEach(function (s) { (s.layerOps || []).forEach(function (l) { q.push(l); }); (s.ops || []).forEach(function (o) { var it = { kind: o.kind, spec: clone(o.spec) }; if (it.spec) delete it.spec._prevScale; /* IA1 2026-10-07: planner-private key (the zone setter refuses unknown settings) */ if (o.zone != null) it.zone = zIdx(o.zone); q.push(it); }); }); return q;
    }
    function asQueue(pl) {          // S6/S7: the applyQueue form that keeps the post hooks: only the layer ops as queue items, the plan rides along as queue._s5plan and applyQueue runs it whole with run(pl, {apply: Z.batch ...}) inside its own undo snapshot
        var q = []; (pl && pl.steps || []).forEach(function (s) { (s.layerOps || []).forEach(function (l) { q.push(clone(l)); }); }); q._s5plan = pl; return q;
    }
    function run(pl, opts) {
        opts = opts || {}; var res = { ok: true, applied: [], warnings: [], ids: [], added: [], steps: [] }; if (!pl || pl.act !== 'change') { res.ok = false; res.warnings.push('nothing to run (' + (pl && pl.act) + ')'); return res; }
        var Zk = W.SpbProZone, label = opts.label || ('AI: ' + (pl.steps[0] && pl.steps[0].label || 'change')).slice(0, 60), batchOps = [], meta = [], before = {}, firstAdd = null;
        try { zones.forEach(function (z) { before[String(z.id)] = 1; }); } catch (e) {}
        function flush() {
            if (!batchOps.length) return; var ops = batchOps.map(function (o) { var c = { kind: o.kind, spec: clone(o.spec) }; if (c.spec) delete c.spec._prevScale; /* IA1 2026-10-07 (in-app 'now the trunk smaller': 'Nothing was changed: unknown setting(s): _prevScale'): planner-private, kept on batchOps for _s5.lastScale */ if (o.zone != null) { var zi = zIdx(o.zone); c.zone = zi >= 0 ? zones[zi] : -1; } return c; });
            var rs = (opts.apply || Zk.batch)(ops, label) || [];
            rs.forEach(function (r, k) {
                var o = batchOps[k], m = meta[k], z = r && r.index >= 0 ? zones[r.index] : null; (r.applied || []).forEach(function (a) { res.applied.push(a); }); (r.warnings || []).forEach(function (w) { res.warnings.push(w); }); if (r.ok === false) res.ok = false; if (!z) return;
                res.ids.push(String(z.id)); if (!before[String(z.id)]) res.added.push(String(z.id));
                z._s5 = Object.assign({}, z._s5 || {}, { prim: m.prim, parts: m.parts, t: Date.now() }); if (o.spec && o.spec._prevScale != null) z._s5.lastScale = o.spec._prevScale;
                if (o.kind === 'add' && !firstAdd && !before[String(z.id)]) firstAdd = String(z.id);
                if (o._aboveAdd && firstAdd) { var fi = zIdx(firstAdd), ci = zones.indexOf(z); if (fi >= 0 && ci > fi) { zones.splice(ci, 1); zones.splice(fi, 0, z); } }
                if (o._above) { var ai = zIdx(o._above), di = zones.indexOf(z); if (ai >= 0 && di > ai) { zones.splice(di, 1); zones.splice(ai, 0, z); } }
                if (o._intersect) { var src = zones[zIdx(o._above)]; if (src && src.useRegion && src.regionMask && z.regionMask && src.regionMask.length === z.regionMask.length) { for (var q = 0; q < z.regionMask.length; q++) if (!src.regionMask[q]) z.regionMask[q] = 0; } }
            });
            batchOps = []; meta = [];
            try { renderZones(); triggerPreviewRender(); } catch (e3) {}
        }
        pl.steps.forEach(function (s) {
            if (s.undo) { flush(); try { if (typeof undoZoneChange === 'function') undoZoneChange(); res.applied.push('took the last change back'); res.undid = true; /* lane R4-CONVO 2026-10-08 A-0233: the report knows this turn took the last change back (js/spb-intent-report.js) */ _last = null; } catch (e) { res.warnings.push('undo failed'); } }
            if (s.redo) { flush(); try { if (typeof redoZoneChange === 'function') redoZoneChange(); } catch (e) {} }
            if (s.flames) {
                flush(); var fr = null; try { fr = W.SpbFlames.apply(s.flames); } catch (e) { fr = { ok: false, warnings: [String(e.message || e)] }; }
                if (!fr || !fr.ok) res.ok = false; (fr && fr.applied || []).forEach(function (a) { res.applied.push(a); }); (fr && fr.warnings || []).forEach(function (w) { res.warnings.push(w); });
                try { zones.forEach(function (z) { if ((fr.zones || []).indexOf(z.name) !== -1) { res.ids.push(String(z.id)); if (!before[String(z.id)]) res.added.push(String(z.id)); z._s5 = { prim: 'flames', parts: arr(s.flames.part) }; } }); } catch (e) {}
            }
            if (s.layerOps && s.layerOps.length) res.warnings.push('layer changes are committed by the host (applyQueue): ' + s.layerOps.map(function (l) { return l.name; }).join(', '));
            (s.ops || []).forEach(function (o) { batchOps.push(o); meta.push({ prim: s.prim, parts: s.scope && s.scope.parts }); });
            res.steps.push(s.prim);
        });
        flush();
        if (res.ids.length) { var s0 = pl.steps.filter(function (s) { return (s.ops && s.ops.length) || s.flames; })[0] || pl.steps[0]; var prevL = _last, editsOnly = !res.added.length && prevL; if (_last) _hist.push(_last); if (_hist.length > 12) _hist.shift(); _last = { ops: editsOnly ? (pl._rootOps || prevL.ops) : (pl._rootOps || pl._frameOps || null), ids: uniq(res.ids), added: uniq(res.added), prim: s0.prim, op: s0._op || null, target: s0._op && s0._op.target && s0._op.target.kind !== 'zone' ? clone(s0._op.target) : (s0.scope ? scopeTarget(s0.scope) : (_last && _last.target)), look: s0._look || null, t: Date.now() }; if (_last.op && _last.op.target && _last.op.target.kind === 'zone' && _last.target) _last.op.target = clone(_last.target); if (pl._rootOps && pl._rootOps[0] && pl._rootOps[0].target) { _last.target = clone(pl._rootOps[0].target); _last.op = clone(pl._rootOps[0]); } if (editsOnly) { _last.added = prevL.added; if (!pl._rootOps) { _last.prim = prevL.prim; _last.target = prevL.target; _last.op = prevL.op; } } }
        return res;
    }
    function planW(frame, env) { return withOps(plan(frame, env), frame); }
    // exact zone state incl. region masks (the app's global zone undo restores masks from the CURRENT zones by id, so an in-place region / stroke_px edit is not
    // undone by it). The AI panel's own Undo (js/spb-pro-ai.js UNDO-FIX entries) keeps exact before-states: S6/S7 apply plans through applyQueue for that reason.
    // These two are for harnesses / MCP dry runs.
    function snapshot() { try { return { zones: zones.map(function (z) { return _cloneZoneState(z, { preserveId: true, includeRegionMask: true, includeSpatialMask: true, includePatternStrengthMap: true }); }), sel: selectedZoneIndex, last: _last, hist: _hist.slice() }; } catch (e) { return null; } }
    function restore(sn) { if (!sn) return false; try { zones.length = 0; sn.zones.forEach(function (z) { zones.push(_cloneZoneState(z, { preserveId: true, includeRegionMask: true, includeSpatialMask: true, includePatternStrengthMap: true })); }); selectedZoneIndex = Math.min(sn.sel || 0, zones.length - 1); _last = sn.last; _hist = sn.hist.slice(); renderZones(); triggerPreviewRender(); return true; } catch (e) { return false; } }

    W.SpbIntentPlan = { VERSION: VERSION, STROKE: STROKE, NAMED: NAMED, plan: planW, run: run, toQueue: toQueue, asQueue: asQueue, snapshot: snapshot, restore: restore, simulate: simulate, live: live, last: function () { return _last; }, forget: function () { _last = null; return true; }, forgetAll: function () { _last = null; _hist = []; return true; } /* IA1 2026-10-07: a NEW conversation (SpbOfflineAnswer._resetConvo) forgets the planner's last change + history too */, setLast: function (l) { _last = l; return true; },
        finishKey: finishKey, strokePx: strokePx, hexOf: hexOf, famOf: famOf, _normEnv: normEnv, _regionFor: regionFor };
})();
