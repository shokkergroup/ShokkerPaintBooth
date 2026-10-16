/* HELPER V3 S3 2026-10-06 (owner GO on S1-S9, docs/handoff_reports/HELPER_ARCHITECTURE_V3.md §S3): the RENDERED verifier + the honest reporter.
 *
 * S2 (js/spb-intent-verify.js onQueue) checks each zone's SCOPE before it is applied. This file checks the RESULT after the render settles:
 *   the live preview (paint + spec, 256 grid, the same cells and thresholds as the in-app gate _easy_claude_work/pw/convo_inapp.py) before vs after,
 *   classified against what the buyer allowed (the parts / layers they named, else the plan's own parts / layers) and the protected decal layers
 *   (numbers / sponsors / logos they did not name).
 *   - spill (changed outside the allowed area > max(120, 12% of the change), or on an unnamed decal layer): trim it (new zones: carve the outside back out;
 *     edited zones: restore the before-state and add the new look as a copy limited to the allowed area). If almost nothing is left inside, undo and ask ONCE.
 *   - gradient: a fade that reads as one flat colour is reported as such.  outline: a "line around" that filled the part is undone and asked once.
 *   - the reply's claim line is rebuilt from the measurement (parts / layers that changed, share of the car, a typed hex shown exactly as typed,
 *     the colour named only when the render shows it), never from the plan. Every change keeps its Undo chip.
 * Modes: SPB_AI_REPORT = enforce | warn | off (window var or localStorage; default below). warn = measure + log only, reply untouched.
 * Off with SPB_AI_FRAME=0 too (the legacy loop). Logged to the turn log as {src:'report', report:{...}} (additive key).
 */
(function () {
    'use strict';
    var W = window, N = 256, SMALL = 120, DEFAULT = 'enforce', LOG = [], PEND = 0, ASKED = {};
    var PARTS = ['hood', 'roof', 'trunk', 'front bumper', 'rear bumper', 'left side', 'right side', 'spoiler'];
    var COLW = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'silver', 'grey', 'gray', 'gold', 'teal', 'cyan', 'navy', 'maroon', 'lime', 'magenta', 'brown', 'bronze', 'copper', 'charcoal', 'cream', 'beige', 'tan', 'turquoise', 'violet', 'burgundy', 'crimson', 'aqua'];
    var FAMW = { red: 'red', crimson: 'red', maroon: 'red', burgundy: 'red', blue: 'blue', navy: 'blue', green: 'green', lime: 'green', yellow: 'yellow', orange: 'orange', purple: 'purple', violet: 'purple', magenta: 'pink', pink: 'pink', black: 'black', white: 'white', grey: 'grey', gray: 'grey', silver: 'silver', charcoal: 'charcoal', teal: 'teal', cyan: 'teal', aqua: 'teal', turquoise: 'teal' };
    var NEAR = [['black', 'charcoal'], ['white', 'silver', 'grey'], ['grey', 'silver', 'charcoal'], ['red', 'pink', 'orange'], ['yellow', 'orange'], ['blue', 'teal', 'purple'], ['teal', 'green'], ['purple', 'pink']];
    var FINW = /\b(chrome|matte?|satin|gloss(?:y)?|metallic|pearl(?:escent)?|candy|carbon|brushed|flake|holo\w*|chameleon|mirror)\b/i;
    function IF() { return W.SpbIntentFrame; }
    function flag(n, d) { try { if (W[n] != null) return String(W[n]); } catch (e) {} try { var v = W.localStorage && W.localStorage.getItem(n); if (v != null) return String(v); } catch (e2) {} return d; }
    function mode() { var F = IF(); if (F && F.on && !F.on()) return 'off'; var m = flag('SPB_AI_REPORT', DEFAULT).toLowerCase(); return /^(off|warn|enforce)$/.test(m) ? m : DEFAULT; }
    function C() { return W.SpbProCar; }
    function Zk() { return W.SpbProZone; }
    function zl() { try { return W.zones || (typeof zones !== 'undefined' ? zones : []); } catch (e) { return []; } }
    function dims() { var c = document.getElementById('paintCanvas'); return c ? [c.width, c.height] : [2048, 2048]; }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function logR(v) { v.t = Date.now(); LOG.push(v); if (LOG.length > 40) LOG.shift(); return v; }
    function postLog(text, rep) { try { if (W.fetch) W.fetch('/api/ai/turn-log', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ src: 'report', text: String(text || '').slice(0, 400), report: rep }), keepalive: true }).catch(function () {}); } catch (e) {} }

    // ---------------------------------------------------------------- shots (the in-app gate's own capture: drawImage of the <img> to 256 x 256)
    function cap(id) {
        var img = document.getElementById(id); if (!img || !img.complete || !(img.naturalWidth > 32)) return null;
        try { var cv = document.createElement('canvas'); cv.width = cv.height = N; var cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(img, 0, 0, N, N); return cx.getImageData(0, 0, N, N).data; } catch (e) { return null; }
    }
    function snapSpec() { return cap('livePreviewSpecImg'); }
    // the live preview the buyer is looking at right now (paint + spec). Taken at apply time ONLY when the preview is synced with the zones: the app's own
    // rshot cache is keyed by the zone hash, and a layer-visibility change (Wire / Mask hidden) re-renders without changing that hash, so a cached shot can be stale
    // ONLINE-AI 2026-10-09 P7 (orchestrator, owner request "render the car for me when you make those changes"; probe in _easy_claude_work/eval/online_ai/PAGE_PROPOSAL.md P7):
    // a FULL render is pushed into #livePreviewImg (paint-booth-5-api-render.js LIVE-PANE SYNC, which tags W.__spbFullPane = {p, s} with the pane URLs). Taken as the "before" shot, that 2048 render differs from the
    // live pipeline's picture everywhere, so the first write after a render reported ~100k px of false outside / logo change (116,544 / 74,432 vs 0 / 576 control) and the app even trimmed the write.
    // Now snap() remembers the last LIVE-pipeline shot (every live <img> load + every check()'s after shot) and, while the pane still holds the full render, hands that one back. No live shot yet = null (skip), never a wrong diff.
    // Kill switch: window.SPB_P7_OFF = 1 (or localStorage SPB_P7_OFF) restores the old snap().
    var LASTLIVE = null;
    function p7off() { var v = flag('SPB_P7_OFF', ''); return !!v && !/^(0|false|no|off)$/i.test(v); }
    function paneFull(id) { try { var f = W.__spbFullPane, img = document.getElementById(id); if (!f || !img) return false; var u = id === 'livePreviewImg' ? f.p : f.s; return !!u && (img.src === u || img.currentSrc === u); } catch (e) { return false; } }
    // P7b/c (fullR run, M-T25: the model rendered BEFORE the live preview had loaded the picture of its write; the pane went live -> full render and LASTLIVE still held the pre-write picture, so the next write was diffed against it = 864k px of false change).
    // Every remembered shot carries the signatures of the live pictures it shows (window.__spbPaintSig / __spbSpecSig, set by doPreviewRender when a preview response is applied; they do NOT move when the server answers paint_unchanged, e.g. after a spec-only tweak).
    // A shot is handed back only while those signatures are still the current ones; otherwise snap() returns null (no measure) instead of a wrong diff. The spec shot alone is dropped (null) when only the spec side is stale.
    function sigNow() { try { return { p: String(W.__spbPaintSig || ''), s: String(W.__spbSpecSig || '') }; } catch (e) { return { p: '', s: '' }; } }
    function rememberLive() { if (p7off() || paneFull('livePreviewImg')) return; var p = cap('livePreviewImg'); if (p) LASTLIVE = { p: p, s: paneFull('livePreviewSpecImg') ? (LASTLIVE && LASTLIVE.g && LASTLIVE.g.s && LASTLIVE.g.s === sigNow().s ? LASTLIVE.s : null) : cap('livePreviewSpecImg'), g: sigNow(), t: Date.now(), documentStamp: W.SpbConversationScope ? W.SpbConversationScope.stamp() : null }; }
    try { document.addEventListener('load', function (e) { if (e && e.target && e.target.id === 'livePreviewImg') rememberLive(); }, true); } catch (eL) {}
    function snap() {
        var p = cap('livePreviewImg'); if (!p) return null;
        if (!p7off()) {
            if (paneFull('livePreviewImg')) { var L = LASTLIVE, g = sigNow(); return L && L.g && L.g.p && L.g.p === g.p && (!W.SpbConversationScope || (L.documentStamp != null && W.SpbConversationScope.current(L.documentStamp))) ? { p: L.p, s: (L.g.s === g.s ? L.s : null), t: Date.now(), documentStamp: L.documentStamp, p7: 'last-live' } : null; }
            var s0 = paneFull('livePreviewSpecImg') ? (LASTLIVE && LASTLIVE.g && LASTLIVE.g.s && LASTLIVE.g.s === sigNow().s ? LASTLIVE.s : null) : cap('livePreviewSpecImg');          // P7d: signature-checked like the paint shot
            LASTLIVE = { p: p, s: s0, g: sigNow(), t: Date.now(), documentStamp: W.SpbConversationScope ? W.SpbConversationScope.stamp() : null };
            return { p: p, s: s0, t: Date.now(), documentStamp: W.SpbConversationScope ? W.SpbConversationScope.stamp() : null };
        }
        return { p: p, s: cap('livePreviewSpecImg'), t: Date.now(), documentStamp: W.SpbConversationScope ? W.SpbConversationScope.stamp() : null };
    }

    // ---------------------------------------------------------------- masks on the 256 grid
    function grid(full, Wd, Hd, mode2) {          // full-res mask -> 256 grid. mode2 'centre' (part masks, like the gate) | 'any' (layer: any pixel in the cell) | 'core' (>= 90% of the cell)
        var g = new Uint8Array(N * N), x, y;
        if (!full) return g;
        for (y = 0; y < N; y++) for (x = 0; x < N; x++) {
            if (mode2 === 'centre') { var px = Math.floor((x + 0.5) * Wd / N), py = Math.floor((y + 0.5) * Hd / N); if (full[py * Wd + px]) g[y * N + x] = 1; continue; }
            var x0 = Math.floor(x * Wd / N), x1 = Math.floor((x + 1) * Wd / N), y0 = Math.floor(y * Hd / N), y1 = Math.floor((y + 1) * Hd / N), n = 0, h = 0, qx, qy;
            for (qy = y0; qy < y1; qy += mode2 === 'solid' ? 1 : 2) for (qx = x0; qx < x1; qx += mode2 === 'solid' ? 1 : 2) { n++; if (mode2 === 'solid' ? full[qy * Wd + qx] === 255 : full[qy * Wd + qx] > 0) { h++; if (mode2 === 'any') { qy = y1; break; } } }
            if (mode2 === 'any' ? h > 0 : (n && (mode2 === 'solid' ? h === n : h >= 0.9 * n))) g[y * N + x] = 1;
        }
        return g;
    }
    function dilate(g, R) { var o = new Uint8Array(N * N), x, y, dx, dy; for (y = 0; y < N; y++) for (x = 0; x < N; x++) if (g[y * N + x]) for (dy = -R; dy <= R; dy++) for (dx = -R; dx <= R; dx++) { var yy = y + dy, xx = x + dx; if (yy >= 0 && yy < N && xx >= 0 && xx < N) o[yy * N + xx] = 1; } return o; }
    function erode(g, R) { var o = new Uint8Array(N * N), x, y, dx, dy; for (y = 0; y < N; y++) for (x = 0; x < N; x++) { if (!g[y * N + x]) continue; var all = 1; for (dy = -R; dy <= R && all; dy++) for (dx = -R; dx <= R; dx++) { var yy = y + dy, xx = x + dx; if (yy < 0 || yy >= N || xx < 0 || xx >= N || !g[yy * N + xx]) { all = 0; break; } } if (all) o[y * N + x] = 1; } return o; }
    function partFull(p) { try { var m = C() && C().maskFor(p); return m && m.mask ? m.mask : null; } catch (e) { return null; } }
    function layerObj(name) { try { return Zk() && Zk().findLayer ? Zk().findLayer(name) : null; } catch (e) { return null; } }
    // CX3 2026-10-09 (Codex layer-targets): the measured reply names a layer by its full "Group / Layer" label, so "Base Paint" (x4 on ARCA) is never ambiguous. Kill switch window.SPB_CX3_OFF.
    function layerLabel(ref) { var row = layerObj(ref); return row ? (!W.SPB_CX3_OFF && W.SpbLayerTargets ? W.SpbLayerTargets.label(row) : row.name) : String(ref); }
    function opaqueArtworkGrid(name, Wd, Hd) {
        if (W.SPB_AI_OPAQUE_CHECK_OFF || typeof W.getLayerOpaqueContributionMask !== 'function') return null;
        try {
            var l = layerObj(name), f = l && W.getLayerOpaqueContributionMask(l, Wd, Hd);
            if (!f || f.length !== Wd * Hd) return null;
            // Full-alpha cells with a two-cell filter margin. Never call a
            // >=50% ownership mask an opaque artwork preservation check.
            var g = erode(grid(f, Wd, Hd, 'solid'), 2), count = 0;
            for (var i = 0; i < g.length; i++) count += g[i] ? 1 : 0;
            return count ? {mask:g,cells:count} : null;
        } catch (e) { return null; }
    }
    function layerFull(name, Wd, Hd) { var l = layerObj(name); if (!l) return null; try { var lu = W.getZoneSourceLayersUnionMask({ sourceLayers: [l.id], sourceLayer: l.id }, Wd, Hd); return lu && lu.union ? lu.union : null; } catch (e) { return null; } }
    function roleOf(r) { var ro = String(r.role || '').toLowerCase(), n = String(r.name || '').toLowerCase(); if (/number/.test(ro) || /^numbers?$/.test(n)) return 'numbers'; if (/decal|logo|sponsor/.test(ro) || /logo|decal|sponsor|contingenc/.test(n)) return 'sponsors'; if (/body/.test(ro)) return 'body'; return 'other'; }
    function cleanPart(p) { return String(p || '').split('@')[0].trim().toLowerCase(); }

    // ---------------------------------------------------------------- what the buyer allowed
    // HELPER V3 S3 2026-10-06: parts named only as the SOURCE of a look ("like the hood", "same as the roof", "match the bumper") are not targets.
    var REFW = /\b(?:like|as|matching|matches|to match|copy(?:ing)?(?:\s+(?:of|from))?|from)\s+(?:the\s+|my\s+|that\s+)?((?:left|right|front|rear|back)?\s*[a-z]+)/gi;
    function partNoun(p) { var w = String(p).split(' '); return w[w.length - 1]; }
    function nounRe(n) { var al = { side: 'sides?|doors?', hood: 'hood|bonnet', trunk: 'trunk|deck ?lid|boot', bumper: 'bumpers?', roof: 'roof', spoiler: 'spoiler|wing' }[n] || (n + 's?'); return new RegExp('\\b(?:' + al + ')\\b', 'gi'); }
    function refParts(said, parts) {
        var t = String(said || '').toLowerCase().replace(/ as well as /g, ' and '), refs = [], m; REFW.lastIndex = 0;
        while ((m = REFW.exec(t))) refs.push(m[1].trim());
        if (!refs.length) return [];
        return parts.filter(function (p) { var n = partNoun(p), all = (t.match(nounRe(n)) || []).length, inRef = refs.filter(function (x) { return nounRe(n).test(x); }).length; return all > 0 && inRef >= all; });
    }
    var KEEPV16 = '(?:protect(?:ing|ed)?|keep(?:ing)?|leave|leaving|preserve|don\'?t\\s+touch|dont\\s+touch|do\\s+not\\s+touch|never\\s+touch|without\\s+touching|not\\s+touching|except(?:\\s+for)?)';
    function keptByWords(said, name, role) {          // V3 S6b 2026-10-07 G16 (B): "protect the Logos and Numbers layers" -> Logos / Numbers are KEPT
        var nm = String(name || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[_\s]+/g, '[\\s_]+'), rw = role === 'numbers' ? 'numbers?' : (role === 'sponsors' ? '(?:logos?|sponsors?|decals?)' : null);
        var alts = [nm].concat(rw ? [rw] : []).join('|'), re = new RegExp('\\b' + KEEPV16 + '\\s+(?:the\\s+|my\\s+|both\\s+|all\\s+)?(?:[\\w-]+\\s+(?:and|&|,)\\s+)*(?:[\\w-]+\\s+){0,3}?(?:' + alts + ')\\b', 'i');
        var m = re.exec(String(said || '')); if (!m) return false;
        return !/\b(?:make|paint|turn|change|colou?r|recolou?r)\b/i.test(m[0]);
    }
    var SIMC16 = /\b(?:in|on|inside)\s+(?:the\s+|my\s+)?(?:sim|game|iracing|replay|session|garage)\b|\biracing\b|\b(?:it|app)\s+(?:said|says)\s+(?:it\s+)?(?:was\s+)?saved\b|\bafter\s+(?:i\s+)?(?:sav(?:e|ed|ing)|export(?:ed|ing)?)\b/i;
    var KP25_PART = { 'hood': 'hood', 'bonnet': 'hood', 'roof': 'roof', 'trunk': 'trunk', 'boot': 'trunk', 'front bumper': 'front bumper', 'nose': 'front bumper', 'rear bumper': 'rear bumper', 'back bumper': 'rear bumper', 'tail': 'rear bumper', 'left side': 'left side', 'right side': 'right side', 'spoiler': 'spoiler', 'wing': 'spoiler' };
    function keptParts25(said) {          // V3 S6b 2026-10-07 G25: the parts a keep / except clause names
        var out = [], re = /\b(?:keep(?:ing)?|leave|leaving|protect(?:ing)?|preserve|except(?:\s+for)?|besides|apart\s+from|other\s+than|but\s+not|not|don'?t\s+touch|dont\s+touch|do\s+not\s+touch|never\s+touch|without\s+touching)\s+(?:the\s+|my\s+)?((?:front bumper|rear bumper|back bumper|left side|right side|bumpers|sides|hood|bonnet|roof|trunk|boot|spoiler|wing|nose|tail)(?:\s*(?:,|and|&|or)\s*(?:the\s+)?(?:front bumper|rear bumper|back bumper|left side|right side|bumpers|sides|hood|bonnet|roof|trunk|boot|spoiler|wing|nose|tail))*)/gi, m;
        while ((m = re.exec(String(said || '')))) String(m[1]).toLowerCase().split(/\s*(?:,|\band\b|&|\bor\b)\s*/).forEach(function (w) { w = w.replace(/^the\s+/, '').trim(); var ps = w === 'bumpers' ? ['front bumper', 'rear bumper'] : (w === 'sides' ? ['left side', 'right side'] : [KP25_PART[w]]); ps.forEach(function (p) { if (p && out.indexOf(p) === -1) out.push(p); }); });
        return out;
    }
    function scopeOf(text, r, entry) {
        var F = IF(), env = { layers: [] }, roles = [];
        try { roles = C() && C().roles ? C().roles() : []; env.layers = roles.map(function (x) { return W.SPB_CX3_OFF ? { name: x.name, role: x.role } : { id: x.id, name: x.name, group: x.group, role: x.role }; }); } catch (e) {}
        var rd = null; try { rd = F && F.read ? F.read(String(text || ''), env) : null; } catch (e2) {}
        rd = rd || { parts: [], layers: [], elements: [], keep: { parts: [] }, whole: false, decals: 'protect' };
        var said = W.SPB_OA_NOR4TYPO ? String(text || '') : String(text || '').replace(/\b(?:evrything|everythin|evrythng|everyting|eveything|evertyhing)\b/gi, 'everything').replace(/\b(?:xcept|exept|excpet|excetp)\b/gi, 'except'), /* lane R4-CONVO 2026-10-08 BL6-145 in-app 'make evrything pink!! xcept my number': the scope must read the same typo fix as the router, else 'number' becomes the only target and the whole-car change is taken back (kill SPB_OA_NOR4TYPO) */ sc = { src: null, whole: false, parts: [], layers: [], keep: (rd.keep && rd.keep.parts) || [], decalNamed: [], protect: [] };
        var patternReport = r&&r.namedPattern ? r : entry&&entry._cxPatternReport;
        var patternScope = !W.SPB_CX3_OFF && W.SpbNamedPatternRefinement && W.SpbNamedPatternRefinement.receipt(patternReport,entry,{zones:typeof zones==='undefined'?[]:zones,current:!!(patternReport&&patternReport.namedPattern&&W.SpbConversationScope&&W.SpbConversationScope.current(patternReport.namedPattern.documentStamp))});
        if(patternScope){sc.src='plan';sc.layers=patternScope.source_layer_ids.map(function(id){var layer=roles.find(function(l){return String(l.id)===String(id);});return layer&&layer.name;}).filter(Boolean);sc.existing_pattern=patternScope;}
        var decals = roles.filter(function (x) { var k = roleOf(x); return (k === 'numbers' || k === 'sponsors') && x.visible !== false; });
        var elNamed = (rd.elements || []).filter(function (e) { return e === 'numbers' || e === 'sponsors'; });
        sc.keptLayers = [];
        decals.forEach(function (x) { var k = roleOf(x), kw = keptByWords(said, x.name, k), named = !kw && (rd.decals === 'include' || (rd.layers || []).indexOf(x.name) !== -1 || elNamed.indexOf(k) !== -1); if (kw) sc.keptLayers.push(x.name); (named ? sc.decalNamed : sc.protect).push(x.name); });          // V3 S6b 2026-10-07 G16 (B)
        var kp25 = keptParts25(said); if (kp25.length) { sc.keep = uniq((sc.keep || []).concat(kp25)); rd.parts = (rd.parts || []).filter(function (p) { return kp25.indexOf(cleanPart(p)) === -1; }); }          // V3 S6b 2026-10-07 G25
        // CX3: an exactly parsed layer scope ("the Paintable Area / Base Paint layer") outranks a body/base word inside the layer's own name.
        var explicit3 = null;
        if (!W.SPB_CX3_OFF) { try { var ep3 = W.SpbProEdit && W.SpbProEdit.plan(said, { layers: env.layers, palette: [], zoneColours: [] }); if (ep3 && ep3.kind === 'ops' && ep3.layerScope && ep3.ops.length && ep3.ops.every(function (op3) { return op3.target && /^(?:layer|colour)$/.test(op3.target.kind) && op3.target.layers && op3.target.layers.length; })) { explicit3 = uniq(ep3.ops.reduce(function (a3, op3) { return a3.concat(op3.target.layers); }, [])); rd.layers = explicit3; rd.parts = []; rd.whole = false; } } catch (e3) {} }
        var wholeW = !explicit3 && (rd.whole || /\b(?:body|base|livery|scheme|whole car|entire car|every ?thing|all over|the car)\b/i.test(said) || (kp25.length && !(rd.parts || []).length && /\b(?:paint|make|turn|spray|do)\s+it\b|\bit\s+all\b/i.test(said)));
        if (!wholeW && ((rd.parts || []).length || (rd.layers || []).length || elNamed.length)) {
            sc.src = 'said'; sc.parts = (rd.parts || []).map(cleanPart).filter(function (p) { return PARTS.indexOf(p) !== -1; }); sc.layers = uniq((rd.layers || []).concat(sc.decalNamed));
            if ((rd.parts || []).length && !sc.parts.length && !sc.layers.length) sc.src = null;          // a part the car map does not know: no spill check
            sc.ref = refParts(said, sc.parts); if (sc.ref.length && sc.ref.length < sc.parts.length) sc.parts = sc.parts.filter(function (p) { return sc.ref.indexOf(p) === -1; });          // HELPER V3 S3 2026-10-06: "doors same like the hood" names the hood as the SOURCE, not a target (bank A-0094 t3 painted the hood)
        }
        if (!sc.src && wholeW) { sc.src = 'said'; sc.whole = true; }
        if (!sc.src) {          // a follow-up ("lighter", "do the bumper too"): the plan's own parts / layers
            var q = (r && r.queue) || [], ok = q.length > 0, ps = [], ls = [], wh = false;
            q.forEach(function (o) {
                if (!ok) return;
                if (o.kind === 'layer') {
                    // MCP edit_layer need not include buyer_said. Retain its exact executed target.
                    if (o.colour != null) {
                        var targetLayer = W.SpbLayerTargets && W.SpbLayerTargets.resolve(o.layer, env.layers);
                        if (!targetLayer || !targetLayer.ok || targetLayer.row.id == null) { ok = false; return; }
                        ls.push(targetLayer.row.id);
                    }
                    return;
                }
                if (o.kind === 'restore' || o.kind === 'carve') return;
                var rg = o.spec && o.spec.region; if (!rg) { if (o.kind === 'edit') return; ok = false; return; }
                if (rg.everything || rg.remaining || rg.paintable) { wh = true; return; }
                var isl = rg.island || rg.part; if (isl) { [].concat(isl).forEach(function (p) { ps.push(cleanPart(p)); }); return; }
                if (rg.graphic && (rg.graphic.parts || rg.graphic.part)) { [].concat(rg.graphic.parts || rg.graphic.part).forEach(function (p) { ps.push(cleanPart(p)); }); return; }
                if (rg.layers && rg.layers.length && !(rg.colors && rg.colors.length)) { [].concat(rg.layers).forEach(function (l) { ls.push(l); }); return; }
                ok = false;
            });
            ps = uniq(ps).filter(function (p) { return PARTS.indexOf(p) !== -1; });
            if (ok && (ps.length || ls.length) && !wh) { sc.src = 'plan'; sc.parts = ps; sc.layers = uniq(ls); sc.nativeColourScope = q.every(function (op) { return op.kind === 'layer' && op.colour != null; }); }
            else if (ok && wh && !ps.length && !ls.length) { sc.src = 'plan'; sc.whole = true; }
        }
        if (!sc.src && !W.SPB_REP_NOAI5) {          // AITER 2026-10-08 ('make it brighter' on the Numbers layer zone = 'changed your numbers / logos, took it back'): an edit step of the plan that names a decal layer (scope.decals 'named') is that layer's own change
            var stq = (r && r.queue && r.queue._s5plan && r.queue._s5plan.steps) || [], lq = [];
            stq.forEach(function (s0) { var c0 = s0 && s0.scope; if (c0 && c0.decals === 'named' && c0.layers && c0.layers.length) c0.layers.forEach(function (l) { if (lq.indexOf(l) === -1) lq.push(l); }); });
            if (lq.length) { sc.src = 'plan'; sc.layers = lq; sc.parts = []; }
            else if (!W.SPB_REP_NOAI7 && stq.length && stq.every(function (s0) { return s0 && s0.scope && s0.scope.edits_only && s0.scope.parts && s0.scope.parts.length; })) { var pq = []; stq.forEach(function (s0) { s0.scope.parts.forEach(function (p) { p = cleanPart(p); if (PARTS.indexOf(p) !== -1 && pq.indexOf(p) === -1) pq.push(p); }); }); if (pq.length) { sc.src = 'plan'; sc.parts = pq; sc.layers = []; } }          // AITER 2026-10-08: a compound tweak ('brighten it and change pink to blue') = two edit steps of the last change's zone: its parts are the scope (kill: SPB_REP_NOAI7)
        }
        if (sc.src === 'plan' && sc.layers.length) { sc.protect = sc.protect.filter(function (l) { return sc.layers.indexOf(l) === -1; }); sc.decalNamed = uniq(sc.decalNamed.concat(sc.layers.filter(function (l) { return decals.some(function (x) { return x.name === l; }); }))); }          // a follow-up refining the chat's own decal layer ("reduce the chrome 50%" after "In the Numbers layer: gold chrome") is not a decal spill
        sc.protectKinds = uniq(decals.filter(function (x) { return sc.protect.indexOf(x.name) !== -1; }).map(function (x) { return roleOf(x) === 'numbers' ? 'numbers' : 'logos'; }));
        var kindOf = function (x) { return roleOf(x) === 'numbers' ? 'numbers' : 'logos'; }, chKinds = uniq(decals.filter(function (x) { return sc.layers.indexOf(x.name) !== -1 || sc.decalNamed.indexOf(x.name) !== -1; }).map(kindOf));
        sc.protectKinds = sc.protectKinds.filter(function (k) { return chKinds.indexOf(k) === -1; });          // HELPER V3 S3 2026-10-06: never "your logos are untouched" on a turn that changed a logos layer (bank A-0236 t2)
        sc.rd = rd; return sc;
    }

    // ---------------------------------------------------------------- the measurement
    // ===== SPB_W28 BEGIN (W28 2026-10-10, lane W28 U1 + U4: hood orders refused as "That changed your numbers / logos ... I took it back") ===========================================
    // Cause (W26 in-app, template "SPB ARCA Chevy": the hood island is a Logos-layer rectangle = yellow base colour + the logo art on top): M.decal is the whole 'core' footprint of the protected layers, so the island's BASE colour cells count as
    // "logo"; a plain "hood green" (3,368 of 5,708 changed cells) or "make the hood matte" (spec 3,488 cells, 3,288 in the footprint, paint 0) crossed the 150-cell / 3% floor and was undone + asked, although the art itself never changed.
    // Now a footprint cell counts as a changed numbers / logos cell only when (1) its PAINT changed in the composite (a spec-only shift under the art is not the art changing) and (2) it is not the base colour of the named part
    // (before-colour within 30/channel of the part's dominant colour, taken from the same before shot). Art that is a different colour from the part (numbers, sponsors, logos) still counts, so a recolour that repaints them is caught as before.
    // Before refusing, the reading is CONFIRMED once: wait until the preview stops changing (two equal shots 400 ms apart, max 6 s) and the zone kit is settled, then measure again; a render still in flight under load no longer turns into "I took it back".
    // Kill switch: window.SPB_W28_SPILL_OFF = 1 (or localStorage SPB_W28_SPILL_OFF = 1) restores the old count and the single measurement. Before -> after: eval/w28/PROGRESS.md.
    function w28off() { try { return !!W.SPB_W28_SPILL_OFF || W.localStorage.getItem('SPB_W28_SPILL_OFF') === '1'; } catch (e) { return !!W.SPB_W28_SPILL_OFF; } }
    function w28BaseOf(A, M, sc) {          // the dominant before-colour of the named part(s): the surface the logo art sits on (null = no clear base colour / no named part)
        if (w28off() || !A || !sc || sc.whole || !sc.parts || !sc.parts.length) return null;
        var hist = {}, tot = 0, i, pi, key, h, k, g, inPart;
        for (i = 0; i < N * N; i++) {
            inPart = false; for (pi = 0; pi < sc.parts.length; pi++) { g = M.part[sc.parts[pi]]; if (g && g[i]) { inPart = true; break; } }
            if (!inPart) continue;
            k = i * 4; key = (A[k] >> 4) * 256 + (A[k + 1] >> 4) * 16 + (A[k + 2] >> 4); h = hist[key] || (hist[key] = { n: 0, r: 0, g: 0, b: 0 }); h.n++; h.r += A[k]; h.g += A[k + 1]; h.b += A[k + 2]; tot++;
        }
        var best = null; for (key in hist) if (!best || hist[key].n > best.n) best = hist[key];
        if (!best || tot < 150 || best.n < 0.2 * tot) return null;
        return [best.r / best.n, best.g / best.n, best.b / best.n];
    }
    function w28Sum(a) { if (!a) return 0; var s = 0; for (var i = 0; i < a.length; i += 61) s = (s * 31 + a[i]) | 0; return s; }
    function w28Stable(Z) {          // the preview has stopped changing (two equal shots 400 ms apart; max 6 s) and the zone kit is settled
        return new Promise(function (res) {
            var t0 = Date.now(), prev = null, same = 0;
            (function tick() {
                var key = '';
                try { var sg = sigNow(); key = w28Sum(cap('livePreviewImg')) + ':' + w28Sum(cap('livePreviewSpecImg')) + ':' + sg.p + ':' + sg.s; } catch (e) { key = 'x'; }
                if (key === prev) same++; else { same = 0; prev = key; }
                if (same >= 2 || Date.now() - t0 > 6000) return res();
                setTimeout(tick, 400);
            })();
        }).then(function () { return Z.whenSettled(60000); });
    }
    // ===== SPB_W28 END ==================================================================================================================================================================

    function measure(A, B, SA, SB, M) {
        var o = { changed: 0, paint: 0, surfacePaint: 0, surfaceChanged: 0, surfaceOutside: 0, spec: 0, outside: 0, kept: 0, keptPaint: 0, decal: 0, decalAll: 0, inside: 0, parts: {}, layers: {}, sum: [0, 0, 0], sn: 0, cells: [] };
        PARTS.forEach(function (p) { o.parts[p] = 0; }); (M.layerNames || []).forEach(function (l) { o.layers[l] = 0; });
        for (var i = 0; i < N * N; i++) {
            var k = i * 4, dp = 0, ds = 0, c;
            for (c = 0; c < 3; c++) { dp = Math.max(dp, Math.abs(A[k + c] - B[k + c])); if (SA && SB) ds = Math.max(ds, Math.abs(SA[k + c] - SB[k + c])); }
            if (!(dp > 28 || ds > 28)) continue;
            o.changed++; if (!M.surface || M.surface[i]) {o.surfaceChanged++; if (dp > 28) o.surfacePaint++; if (M.allow && !M.allow[i]) o.surfaceOutside++;} if (dp > 28) o.paint++; if (ds > 28) o.spec++; o.cells.push(i);
            if (M.allow && !M.allow[i]) o.outside++; else if (M.allow) o.inside++;
            if (M.keep && M.keep[i]) { o.kept++; if (dp > 28) o.keptPaint++; }          // V4-G round 4: a kept part whose colour stayed but whose shine (spec) moved is told apart
            if (M.decal && M.decal[i]) { o.decalAll++; if (!M.w28 || (dp > 28 && !(M.w28Base && Math.abs(A[k] - M.w28Base[0]) + Math.abs(A[k + 1] - M.w28Base[1]) + Math.abs(A[k + 2] - M.w28Base[2]) < 90))) o.decal++; }          // W28 2026-10-10: only footprint cells whose PAINT changed and that are not the part's own base colour count as numbers / logos (see SPB_W28 block)
            PARTS.forEach(function (p) { if (M.part[p] && M.part[p][i]) o.parts[p]++; });
            (M.layerNames || []).forEach(function (l) { if (M.layer[l] && M.layer[l][i]) o.layers[l]++; });
            if (dp > 28 && (!M.allow || M.allow[i])) { o.sum[0] += B[k]; o.sum[1] += B[k + 1]; o.sum[2] += B[k + 2]; o.sn++; }
        }
        return o;
    }
    function hex2(r, g, b) { return '#' + [r, g, b].map(function (v) { var s = Math.round(v).toString(16); return s.length < 2 ? '0' + s : s; }).join(''); }
    function rgbOf(h) { h = String(h || '').replace('#', ''); if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join(''); return [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)]; }
    function fam(h) { try { return W.SpbProEdit && W.SpbProEdit.familyOf ? W.SpbProEdit.familyOf(h) : ''; } catch (e) { return ''; } }
    var PART_W = /\b(?:doors?|sides?|hood|bonnet|roof|trunk|deck ?lid|bumpers?|spoiler|wing|numbers?|logos?|sponsors?|stripes?|mirrors?|pillars?|skirts?|fenders?)\b/;
    var WHOLE_PREV = /\b(?:car|cars|whole|entire|everything|all over|body|livery)\b/;          // an EARLIER turn counts only when it plainly named the whole car ("colour the car"), never "fix it"
    var WHOLE_ASK = /\b(?:it|car|cars|everything|all over|livery|scheme|whole|entire|body|base|flames?|flams|camo|wrap|theme|look|paint ?job|colou?r ?scheme|kit|package)\b/;
    var W19_THEME = /\b(?:vibes?|styled?|themed?|inspired|aesthetic|(?:look|looks|feel|feels) like|like an?|surprise (?:me|us)|go wild|(?:your|ur) (?:call|choice|pick)|you (?:choose|pick|decide)|up to you|do your thing|whatever you (?:want|like))\b/;          // [SPB-W19I 2026-10-09] cause: a theme order ("school bus vibes", "ambulance style", "taxi inspired") IS a whole-car ask, but none of WHOLE_ASK's words are in it, so the whole-car repaint it plans was reverted as 'you did not ask for the whole car' (in-app W17-TH3: painted 89% yellow, then taken back, changed 0). before: undo + ask -> after: the theme stays (only when the text names no part); 'surprise me' / 'your call' are free-choice whole-car asks too (final live run: the first 'surprise me' painted 64% then was taken back). Kill switch window.SPB_W19I_OFF / localStorage SPB_W19I_OFF='1'.
    function w19iOffR() { try { return !!W.SPB_W19I_OFF || W.localStorage.getItem('SPB_W19I_OFF') === '1'; } catch (e) { return !!W.SPB_W19I_OFF; } }
    function hexShare(o, B, h) { var r = parseInt(h.substr(1, 2), 16), g = parseInt(h.substr(3, 2), 16), b = parseInt(h.substr(5, 2), 16), n = 0, t = 0; for (var j = 0; j < o.cells.length; j++) { var k = o.cells[j] * 4; t++; if (Math.abs(B[k] - r) + Math.abs(B[k + 1] - g) + Math.abs(B[k + 2] - b) < 110) n++; } return t ? n / t : 0; }          // HELPER V3 S3: share of the changed cells that render near a typed hex
    function near(a, b) { if (!a || !b || a === b) return true; return NEAR.some(function (g) { return g.indexOf(a) !== -1 && g.indexOf(b) !== -1; }); }

    // gradient: the changed paint inside the allowed area, mean colour of the first vs last third along its longer axis
    function gradientShows(o, B) {
        var xs = [], ys = []; o.cells.forEach(function (i) { xs.push(i % N); ys.push(Math.floor(i / N)); });
        if (xs.length < 30) return null;
        var mm = function (a) { var lo = 1e9, hi = -1e9; a.forEach(function (v) { if (v < lo) lo = v; if (v > hi) hi = v; }); return [lo, hi]; };
        var bx = mm(xs), by = mm(ys), best = 0;
        [[xs, bx], [ys, by]].forEach(function (ax) {
            var lo = ax[1][0], hi = ax[1][1], span = hi - lo; if (span < 6) return; var s1 = [0, 0, 0, 0], s2 = [0, 0, 0, 0];
            o.cells.forEach(function (i, j) { var v = ax[0][j], k = i * 4, t = (v - lo) / span; var s = t < 0.33 ? s1 : (t > 0.67 ? s2 : null); if (!s) return; s[0] += B[k]; s[1] += B[k + 1]; s[2] += B[k + 2]; s[3]++; });
            if (!s1[3] || !s2[3]) return; var d = Math.sqrt(Math.pow(s1[0] / s1[3] - s2[0] / s2[3], 2) + Math.pow(s1[1] / s1[3] - s2[1] / s2[3], 2) + Math.pow(s1[2] / s1[3] - s2[2] / s2[3], 2)); if (d > best) best = d;
        });
        return Math.round(best);
    }

    // ---------------------------------------------------------------- the trim (enforce)
    function trim(entry, allowFull, Wd, Hd, sc) {
        var Z = zl(), cut = 0, did = [], i;
        var idx = function (id) { for (var q = 0; q < Z.length; q++) if (Z[q] && String(Z[q].id) === String(id)) return q; return -1; };
        var carve = function (z) {
            var old = (z.regionMask && z.useRegion && z.regionMask.length === Wd * Hd) ? z.regionMask : null, nm = new Uint8Array(Wd * Hd), kept = 0;
            for (var k = 0; k < nm.length; k++) { var on = (old ? old[k] > 0 : true) && allowFull[k]; if (on) { nm[k] = 255; kept++; } else if (!old || old[k] > 0) cut++; }
            z.regionMask = nm; z.useRegion = true; z._regionDesc = (z._regionDesc ? z._regionDesc + ', ' : '') + 'kept to ' + scopeWords(sc);
            return kept;
        };
        var zd = entry.zdiff || { added: [], edited: [] };
        (zd.added || []).slice().forEach(function (a) { var q = idx(a.id); if (q < 0 || Z[q].muted) return; var nm0 = Z[q].name; if (carve(Z[q]) > 0) { did.push(nm0); return; } Z.splice(q, 1); did.push('removed: ' + nm0); });          // HELPER V3 S3 2026-10-06: a zone with NOTHING left inside the named parts is removed: an all-zero regionMask renders as NO region = the whole car (bank A-0094 t3 painted the car yellow)
        (zd.edited || []).forEach(function (e) {
            var q = idx(e.id); if (q < 0 || !e.before || typeof W._cloneZoneState !== 'function') return;
            var opt = { preserveId: true, includeRegionMask: true, includeSpatialMask: true, includePatternStrengthMap: true };
            var now = W._cloneZoneState(Z[q], { preserveId: false, includeRegionMask: true, includeSpatialMask: true, includePatternStrengthMap: true }), back = W._cloneZoneState(e.before, opt);
            if (!now || !back) return; if (now.id == null || String(now.id) === String(back.id)) now.id = 'z' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
            now.name = String(back.name || 'zone') + ' (' + scopeWords(sc) + ')'; if (!(carve(now) > 0)) { Z.splice(q, 1, back); did.push('restored: ' + back.name); return; }
            Z.splice(q, 1, now, back); did.push(now.name);
            if (zd.added) zd.added.push({ id: String(now.id), name: now.name });
        });
        try { if (typeof W.renderZones === 'function') W.renderZones(); } catch (e1) {} try { if (typeof W.triggerPreviewRender === 'function') W.triggerPreviewRender(); } catch (e2) {}
        return { cut: cut, zones: did };
    }
    function partsWords(ps) {
        ps = ps.slice(); var out = [];
        if (ps.indexOf('left side') !== -1 && ps.indexOf('right side') !== -1) { out.push('both sides'); ps = ps.filter(function (p) { return !/ side$/.test(p); }); }
        if (ps.indexOf('front bumper') !== -1 && ps.indexOf('rear bumper') !== -1) { out.push('both bumpers'); ps = ps.filter(function (p) { return !/ bumper$/.test(p); }); }
        out = ps.map(function (p) { return 'the ' + p; }).concat(out.map(function (w) { return w; }));
        return out.length > 1 ? out.slice(0, -1).join(', ') + ' and ' + out[out.length - 1] : (out[0] || '');
    }
    function scopeWords(sc) {
        if (sc.whole) return 'the body paint';
        var w = []; if (sc.parts.length) w.push(partsWords(sc.parts)); sc.layers.forEach(function (l) { w.push('the ' + layerLabel(l) + ' layer'); });
        return w.join(' and ') || 'what you named';
    }

    // ---------------------------------------------------------------- the reply, from the measurement
    // R6-READ3 R6i / R6k helpers (kill: SPB_OF_CFG.noR6i / noR6k / noR6j)
    function r6Cfg(k) { try { var c = W.SPB_OF_CFG; return !!(c && c[k]); } catch (e) { return false; } }
    var R6_XCOL = /\b(olive drab|olive|khaki|army green|forest green|sky blue|baby blue|hot pink|mint|lavender|burgundy|turquoise)\b/;
    function r6Strip(low) {          // the buyer's keep / decal clauses are not the look
        if (r6Cfg('noR6i')) return low;
        return String(low || '').replace(/\b(?:non[- ]?|not |no |without (?:the |any )?)(?:metallic|metal ?flakes?|flakes?|matte|gloss|chrome)\b/g, ' ').replace(/\b(?:but\s+|and\s+|while\s+|also\s+)?(?:keep|keeping|leave|leaving|protect|preserve|dont touch|don't touch|do not touch)\s+(?:the\s+|my\s+|our\s+|all\s+)?(?:race\s+|car\s+)?(?:numbers?|logos?|sponsors?|decals?|stickers?|stripes?)\b[^,.;]*/g, ' ')
            .replace(/\b(?:numbers?|logos?|sponsors?|decals?|stickers?)\s+(?:stay|stays|remain|remains|in|are|is|should be|as|to be)\s+(?:the\s+)?[a-z]+/g, ' ')
            .replace(/\b(?:race\s+)?(?:numbers?|logos?|sponsors?|decals?)\s+(?:in\s+)?(?:white|black|red|blue|yellow|orange|green|silver|grey|gray|gold)\b/g, ' ')
            .replace(/\b(?:white|black|red|blue|yellow|orange|green|silver|grey|gray|gold)\s+(?:race\s+)?(?:numbers?|logos?|sponsors?|decals?)\b/g, ' ');
    }
    function r6Multi(text) {          // R6k: the sentence gives different parts different looks: no single colour / finish can be claimed
        if (r6Cfg('noR6k')) return false;
        var low = r6Strip(String(text || '').toLowerCase()), seen = {}, n = 0, fin = {}, nf = 0;
        COLW.concat(['olive drab', 'khaki']).forEach(function (w) { if (new RegExp('\\b' + w + '\\b').test(low) && !seen[FAMW[w] || w]) { seen[FAMW[w] || w] = 1; n++; } });
        if (/\bolive\b(?! drab)/.test(low) && !seen.olive) { seen.olive = 1; n++; }
        (low.match(/\b(?:chrome|matte?|flat|satin|gloss(?:y)?|metallic|pearl(?:escent)?|candy|carbon|brushed|flake|holo\w*|chameleon|mirror)\b/g) || []).map(function (w) { return /^(?:flat|matt)$/.test(w) ? 'matte' : (w === 'glossy' ? 'gloss' : w); }).forEach(function (w) { if (!fin[w]) { fin[w] = 1; nf++; } });
        return n >= 2 || nf >= 2;
    }
    function lookOf(text) {
        var t = String(text || ''), hm = /#[0-9a-f]{6}\b|#[0-9a-f]{3}\b/i.exec(t), out = { hex: hm ? hm[0] : null, word: null, finish: null };
        if (!out.hex) {          // the first colour word the buyer said that is not negated ("not red" is not the look)
            var low = r6Strip(t.toLowerCase()), best = -1;          // R6-READ3 R6i
            if (!r6Cfg('noR6i')) { var xc = R6_XCOL.exec(low); if (xc) { out.word = xc[1]; best = xc.index; } }
            COLW.forEach(function (w) { var re = new RegExp('(\\b(?:not|no|without|never|instead of|from) (?:the )?)?\\b' + w + '\\b', 'g'), m; while ((m = re.exec(low))) { if (!m[1] && (best < 0 || m.index < best)) { best = m.index; out.word = w; } } });
            COLW.forEach(function (w) { if (new RegExp('\\b(?:to|into|turn(?:ed)? it|make it) (?:a |an |some )?(?:\\w+ )?' + w + '\\b').test(low)) out.word = w; });          // "swap the red to blue": the look is after "to"
        }
        var f = FINW.exec(r6Cfg('noR6i') ? t : r6Strip(t.toLowerCase())); if (f) out.finish = f[1].toLowerCase().replace(/^matt$/, 'matte').replace(/^glossy$/, 'gloss');
        return out;
    }
    function shareOf(n, paintable) { var p = n / Math.max(1, paintable) * 100; return p < 1 ? '<1%' : Math.round(p) + '%'; }
    function tweakOf(r) { try { if (W.SPB_REP_NOAI1) return null; var st = (r && r.queue && r.queue._s5plan && r.queue._s5plan.steps) || []; for (var i = 0; i < st.length; i++) if (st[i] && /^relative$/.test(st[i].prim) && st[i].label) return String(st[i].label); } catch (e) {} return null; }          // AITER 2026-10-08: the follow-up tweak (relative / adjust) that ran this turn, in words
    function swapOf(r) { try { if (W.SPB_REP_NOAI1) return false; var st = (r && r.queue && r.queue._s5plan && r.queue._s5plan.steps) || []; for (var i = 0; i < st.length; i++) if (st[i] && st[i].prim === 'adjust' && st[i].scope && st[i].scope.colour) return true; } catch (e) {} return false; }          // AITER: a colour swap inside the last change's zone
    function r12Of(r) { try { var st = (r && r.queue && r.queue._s5plan && r.queue._s5plan.steps) || []; for (var i = 0; i < st.length; i++) if (st[i] && st[i].scope && st[i].scope.r8) return st[i].scope.r8; } catch (e) {} return null; }          // R12-REPLY 2026-10-08: the catalogue pick R8-FIN made, read from the plan this turn ran
    var R12_MULTI = /\b(?:colou?r ?(?:shift\w*|flip\w*|chang\w*)|chameleon|chrom[ae] ?flair|multi ?chrome|flip ?flop|rainbow|iridescent|prism\w*|opal\w*|duo ?chrome|tri ?chrome)\b/i;          // R12-REPLY: finishes whose colour moves with the angle: the mean of the render is not "the colour"
    var R12_METAL = /\b(?:chrome|chromy|mirror|metallic|liquid metal|candy|pearl\w*|holo\w*|hologra\w*)\b/i;
    var R12_NUMSTART = /(?:^|[,;]\s*|\s)(?:and\s+)?(?:(?:i\s+)?(?:need|want|would like)\s+|make\s+|put\s+|give\s+|add\s+)?(?:the\s+|my\s+)?(?:race\s+)?numbers?\b/i;
    function r12Comp(t) { var s = String(t || ''), m = R12_NUMSTART.exec(s); if (!m || m.index < 6) return null; var tail = s.slice(m.index); if (!/\b(?:outline|outlined|stroke|border|edge line)\b/i.test(tail)) return null; var first = s.slice(0, m.index).replace(/[\s,;]+(?:and\s*)?$/i, '').trim(); if (!first || /\b(?:numbers?|sponsors?|logos?)\b/i.test(first) || !/\b(?:hood|bonnet|roof|trunk|boot|deck|spoiler|wing|bumpers?|doors?|sides?|fenders?|quarters?|nose|splitter|mirrors?|car|body)\b/i.test(first)) return null; var cw = /\b(white|black|red|yellow|blue|orange|green|silver|gold|pink|purple)\b/i.exec(tail); return { first: first, ask: (cw ? cw[1].toLowerCase() + ' ' : '') + 'outline on the numbers' }; }          // R12-REPLY: "doors flat black, ... white outline on the number": the colour claim is about the doors; the outline is a second, undone change
    var R12_SCENE = [[/\bsunsets?\b/i, 'sunset', 'orange into purple', ['orange into pink', 'red into purple']], [/\bsunrise\b/i, 'sunrise', 'orange into yellow', ['pink into yellow', 'orange into blue']], [/\b(?:dusk|twilight)\b/i, 'dusk', 'purple into navy', ['orange into purple', 'purple into black']], [/\b(?:ocean|sea|underwater)\b/i, 'ocean', 'teal into navy', ['cyan into blue', 'blue into white']]];
    function claimLine(o, sc, M, text, extra) { try { if (!W.SPB_REP_NOR12) { var OFc = W.SpbIntentOfflineFrame, ct = OFc && OFc.correct ? OFc.correct(String(text || '')) : null; if (ct && ct !== String(text || '')) text = ct; var cm = r12Comp(text); if (cm) { extra = extra || {}; extra.r12num = cm.ask; text = cm.first; } } } catch (eR12) {} /* R12-REPLY: a changed mind inside the message = its last choice; a compound clause = the first clause */
        if (o.changed < 30 && extra && extra.tweak && !extra.why) return 'I applied it (' + String(extra.tweak).replace(/ on the last change/, '').replace(/^(\w+) (up|down) \(/, '$1 $2: ').replace(/\)$/, '') + '), but the render shows almost no visible change at this size (fine detail or a small step). Zoom in to check, or say “a lot” for a bigger step.';          // AITER 2026-10-08: honest, not alarming: the edit really ran (numbers named); the measure just cannot see it
        if (o.changed < 30) return 'I ran it, but nothing visible changed on the car (measured on the render)' + (extra.why ? ': ' + extra.why : '.') ;
        var ps = PARTS.filter(function (p) { return M.partCells[p] && o.parts[p] >= Math.max(30, 0.05 * M.partCells[p]); });
        var ls = Object.keys(o.layers).filter(function (l) { return o.layers[l] >= 30; });
        var whole = o.surfaceChanged >= 0.6 * M.paintable, where;
        if (sc.colour) where = 'the ' + sc.colour.word + ' areas';
        else if (sc.layers.length && ls.length) where = ls.map(function(l){return 'the ' + layerLabel(l) + ' layer';}).join(' and ');
        else if (!sc.src) where = 'the preview';
        else if (whole) { where = M.coverageUnit === 'preview' ? 'most of the preview' : 'the whole car'; var ex6 = new RegExp('\\b(?:except|but not|apart from|other than|besides|minus|not the' + (r6Cfg('noR6j') ? '' : '|leave|leaving|keep|keeping|dont touch|don\'t touch|do not touch|untouched') + ')\\b(.*)$', 'i').exec(String(text || ''));          /* R6-READ3 R6j */ if (ex6) { var exP = PARTS.filter(function (p) { return new RegExp('\\b' + p.replace(/ side$/, '(?: side)?') + 's?\\b', 'i').test(ex6[1]) || (/\bsides?\b/i.test(ex6[1]) && / side$/.test(p)); }); if (exP.length) where += ' except ' + partsWords(exP); } }          // V3 S6 2026-10-06 R1
        else if (sc.layers.length && ls.length && (!sc.parts.length || !ps.length)) where = ls.map(function (l) { return 'the ' + layerLabel(l) + ' layer'; }).join(' and ');
        else if (ps.length) where = partsWords(ps);
        else if (ls.length) where = ls.map(function (l) { return 'the ' + layerLabel(l) + ' layer'; }).join(' and ');
        else where = 'part of the car';
        var lk = lookOf(text), r12 = extra && extra.r8 && !W.SPB_REP_NOR12 ? extra.r8 : null, r12m = !W.SPB_REP_NOR12 && R12_MULTI.exec(String(text || '')), r12k = !W.SPB_REP_NOR12 && R12_METAL.test(String(text || '')), r12sn = null, col = '', grad6 = /\b(?:fade[sd]?|fading|gradient|ombre|blend(?:ed|ing)?|transition)\b/i.test(String(text || ''));          // V3 S6 2026-10-06 R1: a fade has no single colour
        var mean = o.sn ? hex2(o.sum[0] / o.sn, o.sum[1] / o.sn, o.sum[2] / o.sn) : null, mf = mean ? fam(mean) : '';
        if (!W.SPB_REP_NOR12 && grad6 && !/#[0-9a-f]{3,6}\b/i.test(String(text || ''))) { for (var i12 = 0; i12 < R12_SCENE.length; i12++) if (R12_SCENE[i12][0].test(String(text || '')) && !COLW.some(function (w) { return new RegExp('\\b' + w + '\\b', 'i').test(String(text || '')); })) { r12sn = R12_SCENE[i12]; break; } }          // R12-REPLY: a named-scene fade (sunset ...)
        if (r12 && r12.pick && o.paint >= 30) col = ' to ' + r12.pick + ' (my closest match to “' + r12.label + '”)';          // R12-REPLY: name the catalogue finish that was really painted
        else if (grad6 && r12sn && o.paint >= 30) col = ' as an ' + r12sn[2] + ' fade (my reading of “' + r12sn[1] + '”)';
        else if (r12m && !grad6 && !r6Multi(text) && o.paint >= 30) { var r12c = []; COLW.forEach(function (w) { if (r12c.length < 3 && new RegExp('\\b' + w + '\\b', 'i').test(String(text || '')) && r12c.indexOf(FAMW[w] || w) === -1) r12c.push(FAMW[w] || w); }); col = ' to a ' + (r12c.length ? r12c.join('/') + ' ' : '') + r12m[0].toLowerCase().replace('color', 'colour') + ' (the colour moves with the angle, so no single colour is measured)'; }
        else if (sc.colour && o.paint >= 30) col = ' to ' + (mf || 'a different colour');
        else if (r6Multi(text) && !(extra && extra.swap) && !grad6 && o.paint >= 30) col = ' (each part with its own look)'; else if (grad6 && o.paint >= 30) col = ' as a fade';
        else if (o.paint >= 30 && lk.hex) {
            var a = rgbOf(lk.hex), b = rgbOf(mean), d = Math.sqrt(Math.pow(a[0] - b[0], 2) + Math.pow(a[1] - b[1], 2) + Math.pow(a[2] - b[2], 2));
            col = (d < 90 || near(fam(lk.hex), mf) || (r12k && /^(?:grey|silver|white|black)$/.test(mf))) ? ' to ' + lk.hex + (r12k && lk.finish ? ' ' + lk.finish : '') : ' (you asked for ' + lk.hex + '; on the render it reads as ' + (mf || 'a different colour') + ')';
        } else if (o.paint >= 30 && lk.word && !lk.finish && FAMW[lk.word]) {
            col = (near(FAMW[lk.word], mf) || (r12k && /^(?:grey|silver|white|black)$/.test(mf))) ? ' to ' + lk.word : ' (you asked for ' + lk.word + '; on the render it reads as ' + (mf || 'a different colour') + ')';
        } else if (lk.word || lk.hex) col = ' to ' + (lk.hex || lk.word) + (lk.finish ? ' ' + lk.finish : '');
        else if (lk.finish) col = ' to ' + lk.finish;
        var only = o.paint < 30 && o.spec >= 30 ? ' (only the shine changed: the paint colours are untouched)' : '';
        if (extra && extra.undid && sc.parts && sc.parts.length && !W.SPB_REP_NOUNDOSPILL) { var s7 = 'Done — I took the last change back, so now only ' + partsWords(sc.parts).replace(/^both /, 'the ') + (lk.hex || lk.word ? ' ' + (sc.parts.length > 1 || / sides?$/.test(sc.parts[0]) ? 'are' : 'is') + ' ' + (lk.hex || lk.word) : ' ' + (sc.parts.length > 1 || / sides?$/.test(sc.parts[0]) ? 'keep' : 'keeps') + ' the new look') + '; the rest of the car is back as it was.'; if (M.protect.length && o.decal < M.decalMin && sc.protectKinds && sc.protectKinds.length) s7 += o.decal > 0 ? ' The preview check detected small differences in protected artwork; preservation is unverified. Review the result or use Undo.' : (M.decalCoreLayers && M.decalCoreLayers.length ? ' The preview check found no change in the checked solid artwork interiors; translucent edges and every source pixel are not verified.' : ' The preview check found no change in protected artwork; it does not verify every pixel.'); return s7; }          // lane R4-CONVO 2026-10-08 A-0233: 'No, only the side' read back as 'the hood, the roof and the front bumper changed' (the undo) -> say what the narrowing did
        if (extra && extra.undid && !W.SPB_REP_NOUNDOSPILL) return 'Done — I took the last change back and kept the new look only where you said; the rest of the car is back as it was.';          // lane R4-CONVO 2026-10-08 in-app train80 A-0233 ('No, the car is not all, only side' reads as whole, no parts): the measured parts are the ones the undo restored, so never list them as 'changed'
        var s = (extra && extra.honest != null && !W.SPB_REP_NOW5H) ? 'Applied to ' + where + ', but only about ' + extra.honest + '% of it shows' + col + ' (' + shareOf(o.surfaceChanged, M.paintable) + ' of the ' + M.coverageUnit + ' changed, measured on the render)' + only + '.' : 'Done — ' + where + ' changed' + col + ' (' + shareOf(o.surfaceChanged, M.paintable) + ' of the ' + M.coverageUnit + ', measured on the render)' + only + '.';          // W5-CONVO 2026-10-09: no 'Done - changed' claim when only N% shows
        if (r12 && r12.alts && r12.alts.length) s += ' Other options if you want a different look: ' + r12.alts.join(', ') + '.';          // R12-REPLY
        if (r12sn) s += ' Other options: ' + r12sn[3].join(', ') + '.';
        if (extra && extra.r12num) s += ' Not done yet: the number outline (one change at a time). Say “' + extra.r12num + '” next and I will add it.';
        if (M.protect.length && o.decal < M.decalMin && sc.protectKinds && sc.protectKinds.length) s += o.decal > 0 ? ' The preview check detected small differences in protected artwork; preservation is unverified. Review the result or use Undo.' : (M.decalCoreLayers && M.decalCoreLayers.length ? ' The preview check found no change in the checked solid artwork interiors; translucent edges and every source pixel are not verified.' : ' The preview check found no change in protected artwork; it does not verify every pixel.');
        return s;
    }

    // ---------------------------------------------------------------- the check
    function check(entry, text, r, ctx, w28conf) {
        try { var sd28 = W.__w28said; if (sd28 && !w28off() && (Date.now() - sd28.t) < 180000 && String(text || '').trim().toLowerCase() === sd28.orig) text = sd28.cmd; } catch (eSd) {}          // W28 2026-10-10 (coordinator item 6b): a turn the helper REWROTE ("use the logo one" -> "make the hood red") is measured against the rewritten command: the buyer's own words named the Logos layer, so the hood paint counted as spill and was trimmed to 43 px
        var m = mode(); if (m === 'off' || !entry || entry.undone) return Promise.resolve(null);
        if (!entry.lines || !entry.lines.length) {          // nothing was applied: a templated "Done — ..." claim must not stand (bank A-0236: "Done — the Logos layer is now metallic" + "Could not apply")
            var fl = (entry.notes || []).filter(function (n) { return /^Could not apply/.test(String(n)); });
            if (r && r.offline && fl.length && /^Done\b/.test(String(entry.text || ''))) { var rp0 = logR({ v: 1, mode: m, verdict: m === 'enforce' ? 'nothing-applied' : 'warn', changed: 0, findings: [{ code: 'nothing-applied' }] }); if (m === 'enforce') { var tx0 = String(entry.text || '').split('\n'); tx0[0] = 'Nothing was changed: ' + String(fl[0]).replace(/^Could not apply\s*[—-]\s*/, '') + '.'; entry.text = tx0.join('\n'); entry.notes = entry.notes.filter(function (n) { return fl.indexOf(n) === -1; }); rp0.line = tx0[0]; try { ctx.render(); } catch (eR0) {} } postLog(text, rp0); }
            return Promise.resolve(null);
        }
        if (!entry.zdiff) return Promise.resolve(null);
        var Z = Zk(); if (!Z || !Z.whenSettled) return Promise.resolve(null);
        var s3b = entry.zdiff.s3b, A = s3b && s3b.p, SA = (s3b && s3b.s) || null; if (!A) return Promise.resolve(logR({ verdict: 'skip', why: 'no before shot (preview not synced at apply time)' }));
        var documentStamp = s3b.documentStamp;
        function currentDocument() { return !W.SpbConversationScope || (documentStamp != null && W.SpbConversationScope.current(documentStamp)); }
        if (!currentDocument()) return Promise.resolve({verdict:'skip',why:'source document changed'});
        PEND++;
        var done = function (v) { if (currentDocument()) PEND = Math.max(0, PEND - 1); return v; };
        return Z.whenSettled(60000).then(function () {
            if (!currentDocument()) return done({verdict:'skip',why:'source document changed'});
            if (entry.undone || (ctx.synced && !ctx.synced())) return done(logR({ verdict: 'skip', why: entry.undone ? 'undone' : 'preview not synced' }));
            var B = cap('livePreviewImg'), SB = snapSpec(); if (!B) return done(logR({ verdict: 'skip', why: 'no after shot' }));
            // ONLINE-AI 2026-10-10 P7d (fullR run, 23 post-render turns: spec_px 103,680 + decal_px 61,248 on every paint-only write after a render; the same writes with no render before them measured spec 0 / decal 0):
            // a paint-only write answers spec_unchanged, so the SPEC pane keeps the full-render spec picture (paneFull spec) while the before shot (snap) used the remembered LIVE spec: the full render's spec differs from the live pipeline's in 1,620 cells (957 of them under the numbers / logos).
            // The after spec shot now takes the same remembered live spec (only while the spec signature is still the one it was taken at), else null = no spec measure; never the full-render pane.
            if (!p7off() && paneFull('livePreviewSpecImg')) { var Ls = LASTLIVE; SB = (Ls && Ls.g && Ls.g.s && Ls.g.s === sigNow().s) ? Ls.s : null; }
            if (!p7off()) { if (paneFull('livePreviewImg')) return done(logR({ verdict: 'skip', why: 'the pane still holds a full render (live preview did not redraw), nothing to compare (P7)' })); LASTLIVE = { p: B, s: SB, g: sigNow(), t: Date.now(), documentStamp: W.SpbConversationScope ? W.SpbConversationScope.stamp() : null }; }       // ONLINE-AI 2026-10-09 P7 (P7d: SB is already the live spec or null)
            // Exact named-zone channel operations use their declared channel,
            // not the generic >28 visual-difference threshold (a +10 step is real).
            if (!W.SPB_CX3_OFF && r && r.namedMaterial && W.SpbNamedZoneMaterial) {
                var nm = r.namedMaterial, measured = W.SpbNamedZoneMaterial.measure(A,B,SA,SB,nm.channel,nm.delta);
                var nmLine = measured && measured.verified ? 'Measured in the spec preview: ' + nm.channel + ' changed; paint colours and the other channels are unchanged.' : !measured ? 'The channel adjustment ran, but a current before-and-after spec preview was unavailable for verification.' : measured.paint || measured.otherChannels || measured.wrongDirection ? 'The preview differs beyond the requested material change. Use Undo to take it back.' : 'The setting changed, but no spec-preview difference was measured. The zone may be covered by another zone or the channel may already be clipped.';
                var nmRep = {v:1,mode:m,verdict:measured && measured.verified ? 'ok' : 'reported',line:nmLine,channel:nm.channel,measurement:measured,scope:'Channel-level preview check; exact zone targeting uses the native edit_zone kernel.'};
                entry.text += '\n' + nmLine; entry.s3=nmRep; logR(nmRep); postLog(text,nmRep); try{ctx.render();}catch(eNM){} return done(nmRep);
            }
            var dm = dims(), Wd = dm[0], Hd = dm[1], sc = scopeOf(text, r, entry), M = { part: {}, partCells: {}, layer: {}, layerNames: [], protect: sc.protect, paintable: 0 };
            PARTS.forEach(function (p) { var f = partFull(p); if (f) { var g = grid(f, Math.round(Math.sqrt(f.length)), Math.round(Math.sqrt(f.length)), 'centre'); M.part[p] = g; var n = 0; for (var i = 0; i < g.length; i++) n += g[i]; M.partCells[p] = n; } });
            try { var pm = C() && C().paintableMask ? C().paintableMask(false) : null; if (pm) { var gp = grid(pm, Wd, Hd, 'centre'); M.surface = gp; for (var i2 = 0; i2 < gp.length; i2++) M.paintable += gp[i2]; } } catch (ep) {}
            M.coverageUnit = M.paintable ? 'car' : 'preview';
            if (!M.paintable) { M.paintable = N * N; M.surface = null; }
            sc.colour = W.SpbColourReportScope ? W.SpbColourReportScope.read(text, A) : null;
            if (sc.colour && !sc.src) sc.src = 'said-colour';
            var layFull = {};
            M.layerNames = uniq(sc.layers.concat(sc.decalNamed)); M.layerNames.forEach(function (l) { var f = layerFull(l, Wd, Hd); if (f) { layFull[l] = f; M.layer[l] = grid(f, Wd, Hd, 'any'); } });
            // decals the buyer did not name: their solid cells must not change
            M.decalCoreCells = 0; M.decalCoreLayers = []; M.decalFallbackLayers = []; M.decalMin = 150; if (sc.protect.length) { var dg = new Uint8Array(N * N), dn = 0; sc.protect.forEach(function (l) { var f = layerFull(l, Wd, Hd); if (!f) return; var core = opaqueArtworkGrid(l, Wd, Hd), g = core ? core.mask : grid(f, Wd, Hd, 'core'); if (core) { M.decalCoreCells += core.cells; M.decalCoreLayers.push(l); } else M.decalFallbackLayers.push(l); for (var i = 0; i < g.length; i++) if (g[i] && !dg[i]) { dg[i] = 1; dn++; } }); M.decal = dg; M.decalMin = Math.max(150, Math.round(0.03 * dn)); }          // 150 cells / 3% of the decal cells: edge cells of a solid decal pick up a body colour change through anti-aliasing (A-0374: 147 cells, decals visibly untouched)
            // allowed = the named parts / layers (+3 cells, like the gate); whole car = everything but the protected decals
            var allowG = null, allowFull = null;
            if (sc.src && !sc.whole && (sc.parts.length || Object.keys(M.layer).length)) {
                allowG = new Uint8Array(N * N); allowFull = new Uint8Array(Wd * Hd);
                sc.parts.forEach(function (p) { var g = M.part[p]; if (g) for (var i = 0; i < g.length; i++) if (g[i]) allowG[i] = 1; var f = partFull(p); if (f && f.length === Wd * Hd) for (var k = 0; k < f.length; k++) if (f[k]) allowFull[k] = 1; });
                Object.keys(M.layer).forEach(function (l) { var g = M.layer[l]; for (var i = 0; i < g.length; i++) if (g[i]) allowG[i] = 1; var f = layFull[l]; for (var k = 0; k < f.length; k++) if (f[k] > 0) allowFull[k] = 1; });
                allowG = dilate(allowG, 3);
            }
            if (sc.keep.length) { var kg = new Uint8Array(N * N); sc.keep.forEach(function (p) { var g = M.part[cleanPart(p)]; if (g) for (var i = 0; i < g.length; i++) if (g[i]) kg[i] = 1; }); M.keep = erode(kg, 3); }
            if (sc.colour && !allowG) allowG = dilate(sc.colour.mask, 3); // same preview anti-alias allowance as named parts
            M.allow = allowG;
            M.w28 = !w28off(); M.w28Base = M.w28 ? w28BaseOf(A, M, sc) : null;
            var o = measure(A, B, SA, SB, M);
            if (M.w28 && !w28conf && m === 'enforce' && ctx && !(r && r.w13nMove) && !/\b(?:kit|package|preset|recipe|scheme)\b/i.test(String(text || '')) && ((M.decal && o.decal >= M.decalMin) || (allowG && o.outside > (sc.colour ? SMALL : Math.max(SMALL, 0.12 * o.changed))))) {          // W28: a refusal-grade reading is measured AGAIN on a settled, unchanging preview before anything is taken back
                return w28Stable(Z).then(function () { done(null); return check(entry, text, r, ctx, true); });
            }
            var rep = { v: 1, mode: m, src: sc.src, whole: sc.whole, parts: sc.parts, ref: sc.ref || [], layers: sc.layers, protect: sc.protect, coverage_unit: M.coverageUnit, coverage_cells: M.paintable, surface_paint: o.surfacePaint, colour_target: sc.colour ? sc.colour.word : null, changed: o.changed, paint: o.paint, spec: o.spec, outside: o.outside, inside: o.inside, kept: o.kept, decal: o.decal, artwork_check: {basis:M.decalCoreLayers.length ? 'opaque interiors with filter margin' : 'binary ownership estimate',checked_core_cells:M.decalCoreCells,core_layers:M.decalCoreLayers,fallback_layers:M.decalFallbackLayers,edges_verified:false}, findings: [] };
            var kitW = !!(r && r.w13nMove && !W.SPB_W13N_OFF) /* W13-NUDGE 2026-10-09: a pattern slide changes pixels under logos in its own zone */ || /\b(?:kit|package|preset|recipe|scheme)\b/i.test(String(text || ''));          // HELPER V3 S3 2026-10-06: "Use the Classic kit" recolours body + stripes + numbers BY DESIGN (undo_inapp: the trim cut the kit's numbers)
            var spill = !kitW && allowG && o.outside > (sc.colour ? SMALL : Math.max(SMALL, 0.12 * o.changed)), decalHit = !kitW && M.decal && o.decal >= M.decalMin, keptHit = M.keep && o.kept > SMALL;
            if (spill && entry.zdiff && entry.zdiff.undid && !W.SPB_REP_NOUNDOSPILL) { spill = false; rep.findings.push({ code: 'narrowed', outside: o.outside }); }          // lane R4-CONVO 2026-10-08 A-0233 / X-N01: this turn's plan ran an UNDO step first (a narrowing 'no, only the hood' after a whole-car change): the pixels outside the part going back = that undo, not a spill. In-app X-N01 before: report took the hood back (whole car stayed blue). Kill switch window.SPB_REP_NOUNDOSPILL
            if (spill) rep.findings.push({ code: 'spill', outside: o.outside, inside: o.inside });
            if (decalHit) rep.findings.push({ code: 'decal', cells: o.decal });
            if (keptHit) rep.findings.push({ code: 'kept', cells: o.kept });
            // gradient / outline (only what the buyer said)
            var said = String(text || ''), gradW = /\b(fade|fading|gradient|ombre|blend(?:ing)? (?:in)?to|from \w+ to \w+)\b/i.test(said), lineW = /\b(outline|outlined|pin ?stripe|pin ?line|border|edge line|line around)\b/i.test(said);
            if (gradW && o.paint >= 30) { var gs = gradientShows(o, B); rep.gradient = gs; if (gs != null && gs < 40) rep.findings.push({ code: 'flat-fade', delta: gs }); }
            if (lineW && sc.parts.length === 1 && M.partCells[sc.parts[0]]) { var fr = o.parts[sc.parts[0]] / M.partCells[sc.parts[0]]; rep.outline = Math.round(fr * 100); if (fr > 0.85) rep.findings.push({ code: 'filled', pct: rep.outline }); }
            // HELPER V3 S3 2026-10-06: an UNASKED whole-car repaint (dev-harm A-0012 "tint the windshield blue chrome", A-0354 "chrome on the star", A-0096 "white one down the middle" -> 90%+ of the car) and typed colours that never show (A-0566 "left #FFFFFF and right #0B3D91" -> all white)
            var big = o.surfacePaint >= 0.5 * M.paintable, saidL = (W.SPB_OA_NOR4TYPO ? said : said.replace(/\b(?:evrything|everythin|evrythng|everyting|eveything|evertyhing)\b/gi, 'everything')).toLowerCase().replace(/\bnot (?:the )?whole \w+/g, ' ');
            var wholeAsk = (sc.whole && sc.src === 'said' && !/\bnot (?:the )?whole\b/i.test(said) || WHOLE_ASK.test(saidL) || (!w19iOffR() && W19_THEME.test(saidL) && !PART_W.test(saidL) && !(sc.parts && sc.parts.length))) && !SIMC16.test(said);          // V3 S6b 2026-10-07 G16 (A): a sim / saved complaint never asks for the whole car
            try { var CVt = W.SpbConvo, tv = CVt && CVt.turns ? CVt.turns() : []; for (var ti = Math.max(0, tv.length - 3); ti < tv.length; ti++) { var ts = String((tv[ti] && tv[ti].said) || '').toLowerCase(); if (ts && ts !== said.toLowerCase() && !PART_W.test(ts) && WHOLE_PREV.test(ts.replace(/\bnot (?:the )?whole \w+/g, ' '))) wholeAsk = true; } } catch (eWT) {}          // HELPER V3 S3 2026-10-06: specs b4-158 "colour the car" -> "blue" asked for the whole car one turn earlier
            var prevBig = false; try { var CVb = W.SpbConvo; prevBig = !!(CVb && CVb.changes && CVb.changes().some(function (c) { return !c.undone && c.entry_id != null && c.entry_id !== entry.id && LOG.some(function (v) { return v && v.big && v.eid === c.entry_id && v.verdict === 'ok'; }); })); } catch (ePB) {}          // a follow-up on a whole-car change of THIS chat ("darker") is fine
            rep.big = big; rep.eid = entry.id;
            if (big && !sc.colour && !(sc.nativeColourScope && allowG && o.outside <= SMALL) && !wholeAsk && !prevBig && !sc.existing_pattern && !(entry.zdiff && entry.zdiff.undid && !W.SPB_REP_NOUNDOSPILL)) rep.findings.push({ code: 'unasked-whole', pct: Math.round(100 * o.surfacePaint / M.paintable) });
            var hx = uniq((said.match(/#[0-9a-f]{6}\b/gi) || []).map(function (h) { return h.toUpperCase(); }));
            if (hx.length >= 2 && o.paint >= 300) { var miss = hx.filter(function (h) { return hexShare(o, B, h) < 0.01; }); if (miss.length) rep.findings.push({ code: 'colour-missing', hex: miss }); }
            var key = String(text || '').toLowerCase().replace(/\s+/g, ' ').trim();
            var res = { o: o, rep: rep };
            if (m !== 'enforce' || !ctx) { rep.verdict = rep.findings.length ? 'warn' : 'ok'; rep.would = claimLine(o, sc, M, text, { undid: !!(entry.zdiff && entry.zdiff.undid), r8: r12Of(r), tweak: tweakOf(r), swap: swapOf(r) }); logR(rep); postLog(text, rep); return done(rep); }
            // ---- enforce
            var askOnce = function (q, chips) {
                if (!currentDocument() || ASKED[key]) return false; ASKED[key] = 1;
                try { entry.undoneByCheck = true; ctx.undo(); } catch (eu) {}
                entry.text = q; entry.next = chips; entry.s3 = rep; rep.verdict = 'undo-ask'; rep.line = q; return true;
            };
            if (rep.findings.some(function (f) { return f.code === 'filled'; })) {
                if (askOnce('That filled the whole ' + sc.parts[0] + ' instead of drawing a line along its edge, so I took it back. Do you want a thin outline along the edge of the ' + sc.parts[0] + ', or a band across it?', ['Thin outline on the ' + sc.parts[0], 'A band across the ' + sc.parts[0]])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            }
            // A colour target may cover most of the sheet; pixels outside that
            // named before-picture family are still an unauthorized spill.
            if (sc.colour && spill && askOnce('That changed areas outside the ' + sc.colour.word + ' paint you named, so I took it back. Nothing stayed changed. Shall we isolate that colour more carefully?', ['Try again', 'Show me the paint'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            var fUW = rep.findings.filter(function (f) { return f.code === 'unasked-whole'; })[0], fCM = rep.findings.filter(function (f) { return f.code === 'colour-missing'; })[0];
            if (fUW && askOnce('That repainted the whole car (' + fUW.pct + '% of it), but you did not ask for the whole car, so I took it back. Which part should change?', ['Yes, the whole car', 'Show me the parts'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            if (fCM && big && askOnce('The ' + fCM.hex.join(' and ') + ' you asked for does not show anywhere on the car, so I took it back. Which part should be ' + fCM.hex[0] + '?', ['Show me the parts', 'Try again'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            var keptL = (sc.keptLayers || []).length > 0;          // V3 S6b 2026-10-07 G16 (B): a protected layer changed / decal pixels changed with no named scope or as most of the change = wrong: undo + ask
            if (decalHit && (keptL || !allowFull || o.decal >= 0.5 * Math.max(1, o.changed))) {
                var dn = keptL ? sc.keptLayers.join(' and ') + ' layer' + (sc.keptLayers.length > 1 ? 's' : '') : 'numbers / logos';
                if (askOnce('That changed your ' + dn + (keptL ? ', which you asked me to keep as ' + (sc.keptLayers.length > 1 ? 'they are' : 'it is') : ', which you did not name') + ', so I took it back. Nothing else stayed changed. Which part should change?', ['Only the body paint', 'Show me the parts'])) { rep.findings.push({ code: 'decal-undo', kept: sc.keptLayers || [] }); logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            }
            var p2 = Promise.resolve(o);
            if ((spill || decalHit || keptHit) && allowFull && !keptHit) {
                if (o.inside < Math.max(30, 0.15 * o.changed)) {          // almost nothing inside the named parts (A-0094 t3: 130 edge cells of 2013): take it back + ask, never keep a sliver
                    var refHit = (sc.ref || []).filter(function (p) { return o.parts && o.parts[p] >= 30; });          // HELPER V3 S3 2026-10-06: the part named as the look to copy is the one that changed (bank A-0094 t3)
                    if (refHit.length && askOnce('That changed the ' + refHit[0] + ' instead of ' + scopeWords(sc) + ', so I took it back. Do you want ' + scopeWords(sc) + ' to get the same colour and finish as the ' + refHit[0] + '?', ['Yes: ' + scopeWords(sc) + ' like the ' + refHit[0], 'No, leave it'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
                    if (askOnce('That would have changed ' + (o.outside >= 0.6 * M.paintable ? 'the whole car' : 'other parts of the car') + ' instead of ' + scopeWords(sc) + ', so I took it back. Say exactly which part you mean (for example “only the ' + (sc.parts[0] || 'hood') + '”).', ['Only ' + scopeWords(sc), 'The whole car'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
                } else {
                    var t = trim(entry, allowFull, Wd, Hd, sc); rep.trim = { cut_px: t.cut, zones: t.zones.slice(0, 6) };
                    try { ctx.reseal(); } catch (er) {}
                    p2 = Z.whenSettled(60000).then(function () { if (!currentDocument()) return o; var B2 = cap('livePreviewImg'), SB2 = snapSpec(); if (!B2) return o; B = B2; var o2 = measure(A, B2, SA, SB2, M); rep.after_trim = { changed: o2.changed, outside: o2.outside, decal: o2.decal }; return o2; });
                }
            } else if (decalHit && !allowFull) {
                rep.note = 'decal change without a known scope: reported';
            }
            return p2.then(function (o2) {
                if (!currentDocument()) return done({verdict:'skip',why:'source document changed'});
                var w28Nothing = false;
                if (!w28off() && !W.SPB_W28_ZKEEP && m === 'enforce' && o2.changed < 30 && entry.zdiff && (entry.zdiff.added || []).length && !entry.zdiff.undid && !entry.undone && typeof ctx.undo === 'function' && !(r && r.w13nMove) && typeof entry.w27undo !== 'function') {          // W28 2026-10-10 (IQ3-4: truck, Shokk Drop zone on top, 'make the roof chrome' = zones 6 -> 9 and nothing visible): confirm on a settled preview, then take the entry's own zones back (kill window.SPB_W28_ZKEEP)
                    if (!w28conf) return w28Stable(Z).then(function () { done(null); return check(entry, text, r, ctx, true); });
                    try { entry.undoneByCheck = true; ctx.undo(); w28Nothing = true; rep.zkeep = (entry.zdiff.added || []).length; } catch (eNu) {}
                }
                var hn5 = null; try { if (!W.SPB_REP_NOW5H) (entry.notes || []).forEach(function (n) { var mh = /Only about (\d+)% of [^:]{2,60} shows this change/.exec(String(n)); if (mh && hn5 == null) hn5 = +mh[1]; }); } catch (eH5) {}          // W5-CONVO 2026-10-09 (kill SPB_REP_NOW5H): the zone kit's honest note (W3-HONEST) must not sit under a 'Done - the <part> changed' lead
                var line0w28 = null; var line = claimLine(o2, sc, M, text, { honest: hn5, undid: !!(entry.zdiff && entry.zdiff.undid), r8: r12Of(r), tweak: tweakOf(r), swap: swapOf(r) });
                if (w28Nothing) line += ' I took it back, so no extra zones were left behind. Tell me what you want to see and I will try another way.';
                if (rep.trim) line += ' It had also changed ' + (o.decal >= 60 ? 'your numbers / logos' : 'parts you did not name') + ', so I kept it to ' + scopeWords(sc) + '.';
                else if (spill && !allowFull) line += ' Heads up: it also changed ' + shareOf(o.surfaceOutside, M.paintable) + ' of the ' + M.coverageUnit + ' outside ' + scopeWords(sc) + '.';
                if (decalHit && !rep.trim) line += ' Heads up: it changed your numbers / logos too (Undo takes it back).';
                if (keptHit) line += o.keptPaint > SMALL ? ' Heads up: it also changed the ' + sc.keep.join(' and ') + ' you asked me to keep (Undo takes it back).' : ' The ' + sc.keep.join(' and ') + ' kept ' + (sc.keep.length > 1 ? 'their' : 'its') + ' colour; only the shine there shifted a little (Undo takes it back).';          // V4-G round 4
                if (rep.findings.some(function (f) { return f.code === 'flat-fade'; }) && (W.SPB_REP_NOAI8 || /fade|gradient|ombre|blend|to\s+\w+\s+(?:fade|gradient)/i.test(String(said || '')))) line += ' The fade does not show on the render: it reads as one flat colour.';
                if (fCM) line += ' Heads up: ' + fCM.hex.join(' and ') + ' does not show on the car.';
                var rest = String(entry.text || '').split('\n'), first = rest[0] || '';
                if (r && r.offline && /^(?:Done|I could not do that)\b/.test(first)) { rest[0] = line; entry.text = rest.join('\n'); }
                else if (!/What changed:/.test(entry.text || '')) entry.text = (entry.text ? entry.text + '\n' : '') + line;
                if (o2.changed >= 30) { entry.next = (entry.next || []).slice(); if (!entry.next.some(function (c) { return /^undo\b/i.test(String(c)); })) { if (entry.next.length > 2) entry.next = entry.next.slice(0, 2); entry.next.push('Undo'); } }          // every change keeps its Undo chip
                rep.verdict = rep.findings.length ? (rep.trim ? 'trimmed' : 'reported') : 'ok'; rep.line = line; entry.s3 = rep;
                logR(rep); postLog(text, rep); try { ctx.render(); } catch (e) {} return done(rep);
            });
        }).catch(function (e) { done(null); if (!currentDocument()) return {verdict:'skip',why:'source document changed'}; return logR({ verdict: 'error', why: String(e && e.message || e).slice(0, 160) }); });
    }

    W.SpbIntentReport = { mode: mode, check: check, snap: snap, snapSpec: snapSpec, scopeOf: scopeOf, lookOf: lookOf, pending: function () { return PEND; }, since: function (t0) { return LOG.filter(function (v) { return (v.t || 0) >= (t0 || 0); }); }, _reset: function () { LOG = []; ASKED = {}; PEND = 0; LASTLIVE = null; return true; } };
})();
