/* spb-online-kits.js - [OA2 2026-10-10 lane ONLINE-AI-2] online Claude (MCP tool spb_kit) drives the four tonight's kits through their PUBLIC APIs:
 *   Sponsor Kit (SpbRevSponsor + SpbRevSponsorClean), Number Kit (SpbRevNumbers), Spec Doctor (SPBRevDoctor), Spec Autopilot (SPBRevAutoSpec).
 * One page-side tool name: 'kit'  (MCP name spb_kit, mcp/server/index.js). It answers on window.spbProAI.mcpCall (wrapped here, so no other lane's file is touched).
 * HONEST + MEASURED: every result says what changed (layer names, parts, real size in cm, spec M / R / C for the material), how many opaque pixels each layer holds and how many of them are on the named part,
 * what was NOT touched, and how to undo. Never paints unasked: spb_kit is only called after an explicit request (server instruction); read-only actions (check, propose, list) change nothing; apply / fix need the
 * buyer's agreement. Undo: one step per kit (the kit's own layer-stack undo, same as Ctrl+Z); the server routes spb_undo here when the newest change was a kit.
 * KILL SWITCH: window.SPB_ONLINE_KITS_OFF = true (or localStorage SPB_ONLINE_KITS_OFF = '1') before load; the MCP server drops the tool with env SPB_ONLINE_KITS_OFF=1.
 * Metric: eval/oa2 (bank_kits.json) - see _easy_claude_work/eval/online_ai/PROGRESS.md OA2 section. */
(function (W) {
    'use strict';
    if (W.SpbOnlineKits) return;
    var VER = 'ok1.4', TAG = '[SPB-ONLINE-KITS]';
    function flag(v) { if (typeof v === 'string') { v = v.trim().toLowerCase(); return !(v === '' || v === '0' || v === 'false' || v === 'off' || v === 'no'); } return !!v; }
    function off() { try { if (flag(W.SPB_ONLINE_KITS_OFF)) return true; return flag(W.localStorage && W.localStorage.getItem('SPB_ONLINE_KITS_OFF')); } catch (e) { return flag(W.SPB_ONLINE_KITS_OFF); } }
    function warn(where, e) { try { console.warn(TAG, where, e && e.message || e); } catch (_) {} }
    function layers() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (e) { return []; } }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
    function sheet() { var c = W.document.getElementById('paintCanvas'); return [c && c.width || 2048, c && c.height || 2048]; }
    function R1(v) { return Math.round(v * 10) / 10; }
    function out(o) { return { ok: true, result: o }; }
    function refuse(msg, extra) { return out(Object.assign({ changed: false, refused: true, note: msg }, extra || {})); }
    function ask(q, extra) { return out(Object.assign({ changed: false, ask: q }, extra || {})); }
    function hex(v) { v = String(v == null ? '' : v).trim(); if (/^#?[0-9a-f]{3}$/i.test(v)) v = v.replace('#', '').split('').map(function (c) { return c + c; }).join(''); v = v.replace('#', ''); return /^[0-9a-f]{6}$/i.test(v) ? '#' + v.toLowerCase() : null; }

    // ------------------------------------------------------------------ layers: find by name / id, say which are candidates
    function roleOf(l) { try { var rs = W.SpbProCar && W.SpbProCar.roles ? W.SpbProCar.roles() : []; for (var i = 0; i < rs.length; i++) if (String(rs[i].id) === String(l.id)) return rs[i].role || ''; } catch (e) {} return ''; }
    function isTemplate(l) { return /^(wire|mask|car[ _]*mandatory)$/i.test(String(l && l.name || '').trim()); }
    function findLayer(q) {
        var Ls = layers().filter(function (l) { return l && l.img && !isTemplate(l); }), s = String(q == null ? '' : q).trim().toLowerCase(), i;
        if (!s) return { error: 'no layer named' };
        for (i = 0; i < Ls.length; i++) if (String(Ls[i].id).toLowerCase() === s) return { layer: Ls[i] };
        var ex = Ls.filter(function (l) { return String(l.name || '').trim().toLowerCase() === s; }); if (ex.length === 1) return { layer: ex[0] }; if (ex.length > 1) return { error: 'several layers are named "' + q + '"', candidates: ex.map(function (l) { return { id: l.id, name: l.name, path: l.path || '' }; }) };
        var part = Ls.filter(function (l) { return String(l.name || '').toLowerCase().indexOf(s) >= 0; }); if (part.length === 1) return { layer: part[0] };
        if (part.length > 1) return { error: 'more than one layer matches "' + q + '"', candidates: part.slice(0, 8).map(function (l) { return { id: l.id, name: l.name, path: l.path || '' }; }) };
        return { error: 'no layer called "' + q + '"' };
    }
    function logoCandidates() {
        var K = W.SpbRevSponsor, c = layers().filter(function (l) { return l && l.img && !isTemplate(l) && !(K && K.isKitLayer && K.isKitLayer(l)) && (/logo|sponsor|decal|badge|brand|emblem/i.test(String(l.name || '')) || /sponsor|logo|decal/i.test(roleOf(l))); });
        return c.slice(0, 8).map(function (l) { return { id: l.id, name: l.name }; });
    }

    // ------------------------------------------------------------------ measuring: opaque pixels of a layer, how many sit on a named part
    function layerPixels(l) {
        var sz = sheet(), W2 = sz[0], H2 = sz[1], cv = W.document.createElement('canvas'); cv.width = W2; cv.height = H2;
        var g = cv.getContext('2d', { willReadFrequently: true }); var b = l.bbox || [0, 0, W2, H2];
        try { g.drawImage(l.img, Math.round(b[0]), Math.round(b[1])); } catch (e) { return null; }
        return { data: g.getImageData(0, 0, W2, H2).data, W: W2, H: H2 };
    }
    function footprint(l, partName) {
        var px = layerPixels(l); if (!px) return { opaque_px: null, on_part_pct: null, measured: false };
        var d = px.data, n = 0, on = 0, mask = null;
        try { var P = W.SpbProCar; var m = partName && P && P.maskFor ? P.maskFor(partName) : null; if (m && m.mask && m.mask.length === px.W * px.H) mask = m.mask; } catch (e) {}
        for (var i = 0, j = 3; i < d.length; i += 4, j += 4) { if (d[j] > 16) { n++; if (mask && mask[i >> 2]) on++; } }
        return { opaque_px: n, on_part_pct: mask && n ? Math.round(1000 * on / n) / 10 : null, measured: true };
    }
    var TABLE = null;
    function matTable() { if (TABLE) return TABLE; TABLE = {}; try { (W.SPBAutoSpecCore && W.SPBAutoSpecCore.MATERIALS || []).forEach(function (m) { if (m.cc != null) TABLE[m.id] = { M: m.m, R: m.r, C: m.cce != null ? m.cce : m.cc, name: m.name }; }); } catch (e) {} return TABLE; }
    var MAT_PRESET = { chrome: 'chrome', matte: 'matte', gloss: 'gloss', satin: 'satin' };
    function specOfKitMaterial(m) {      // honest: numbers only where the Auto Spec table (read from the engine registry) has them
        if (!m || m === 'none') return { material: 'none', spec: null, note: 'no layer material: the zones decide the spec under this layer' };
        var t = matTable()[MAT_PRESET[m]];
        if (t) return { material: t.name, spec: { M: t.M, R: t.R, C: t.C }, note: 'M metallic, R roughness (0 = mirror), C clearcoat (16 = max gloss)' };
        if (m === 'gold') return { material: 'Gold Leaf (finish efx_gold_leaf, clipped to the logo)', spec: null, note: 'spec comes from the finish: read it with spb_finish_details efx_gold_leaf; not typed from memory' };
        if (m === 'goldfoil') return { material: 'Gold Foil (finish electroplated_gold, clipped to the logo)', spec: null, note: 'spec comes from the finish: read it with spb_finish_details electroplated_gold; not typed from memory' };
        return { material: String(m), spec: null };
    }
    function undoDepth() { try { return Array.isArray(W._layerUndoStack) ? W._layerUndoStack.length : -1; } catch (e) { return -1; } }
    function world() {          // fingerprint of what an undo would touch: layer ids + zones + layer-undo depth (a kit undo is refused when it differs from the one taken right after the kit)
        try {
            var z = ''; try { z = JSON.stringify(typeof zones !== 'undefined' ? zones : []); } catch (e) { z = 'z?'; }
            var h = 5381, str = layers().map(function (l) { return String(l.id) + (l.visible === false ? '-' : '+'); }).join(',') + '|' + z.length + '|' + undoDepth();
            for (var i = 0; i < z.length; i += 7) h = ((h << 5) + h + z.charCodeAt(i)) | 0;
            for (var j = 0; j < str.length; j++) h = ((h << 5) + h + str.charCodeAt(j)) | 0;
            return str.length + ':' + h;
        } catch (e) { return ''; }
    }
    var LAST_KIT = null;          // { label, depth } of the newest kit write this module made (undo target)

    // ------------------------------------------------------------------ SPONSOR KIT
    var SLOT_WORDS = [
        ['door_l', /\bleft\b.*\bdoor|\bdoor.*\bleft\b|driver.?s? door/], ['door_r', /\bright\b.*\bdoor|\bdoor.*\bright\b|passenger.?s? door/],
        ['quarter_l', /\bleft\b.*\bquarter|\bquarter.*\bleft\b/], ['quarter_r', /\bright\b.*\bquarter|\bquarter.*\bright\b/],
        ['tv_l', /\bleft\b.*\btv\b|\btv\b.*\bleft\b/], ['tv_r', /\bright\b.*\btv\b|\btv\b.*\bright\b/],
        ['rail_l', /\bleft\b.*\brail|\brail.*\bleft\b/], ['rail_r', /\bright\b.*\brail|\brail.*\bright\b/],
        ['hood', /\bhood\b|\bbonnet\b/], ['deck', /\btrunk\b|\bdeck\b|\btailgate\b|\bbed\b/]
    ];
    var PAIR_WORDS = [['door_l,door_r', /\b(both )?doors\b/], ['quarter_l,quarter_r', /\b(both )?(rear )?quarters?\b(?!.*\b(left|right)\b)/], ['tv_l,tv_r', /\b(both )?tv panels?\b/], ['rail_l,rail_r', /\b(roof )?rails?\b/]];
    function slotsOf(parts) {
        var ids = {}, unknown = [];
        (Array.isArray(parts) ? parts : [parts]).forEach(function (p) {
            var s = String(p == null ? '' : p).toLowerCase().replace(/[_-]/g, ' ').trim(), hit = false;
            if (!s) return;
            if (/^(door_l|door_r|quarter_l|quarter_r|tv_l|tv_r|rail_l|rail_r|hood|deck)$/.test(String(p))) { ids[String(p)] = 1; return; }
            SLOT_WORDS.forEach(function (w) { if (w[1].test(s)) { ids[w[0]] = 1; hit = true; } });
            if (!hit) PAIR_WORDS.forEach(function (w) { if (w[1].test(s)) { w[0].split(',').forEach(function (x) { ids[x] = 1; }); hit = true; } });
            if (!hit) unknown.push(String(p));
        });
        return { ids: Object.keys(ids), unknown: unknown };
    }
    // OA2 2026-10-10: both kits need the measured car (SpbRevSym registry). The panels' own "measure" step is a read-only analysis (cached in localStorage), so it is done here before the first placement.
    async function ensureCar() {
        try { var Y = W.SpbRevSym; if (Y && !(Y.off && Y.off()) && !(Y.ready && Y.ready()) && Y.build) await Y.build(false); } catch (e) { warn('car measure', e); }
    }
    function dataUrlFile(url, name) {
        var m = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(String(url || '')); if (!m) return null;
        var bin = m[2] ? atob(m[3]) : decodeURIComponent(m[3]), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
        return new File([u], name || 'logo', { type: m[1] || 'image/png' });
    }
    async function sponsorPlace(a) {
        var K = W.SpbRevSponsor, CL = W.SpbRevSponsorClean;
        if (!K || (K.off && K.off()) || !CL) return refuse('The Sponsor Kit is switched off or not loaded in this app build.');
        if (!layers().length) return refuse('This car is a flat picture with no layers: the Sponsor Kit places its logos as layers. Nothing was changed.');
        var sl = slotsOf(a.parts);
        if (!sl.ids.length) return ask('Which parts should the logo go on? Name them (left door, right door, hood, trunk, left/right rear quarter, left/right TV panel, left/right roof rail).' + (sl.unknown.some(function (u) { return /roof/i.test(u); }) ? ' The Sponsor Kit has roof RAILS, not a roof panel.' : ''), sl.unknown.length ? { not_understood: sl.unknown } : {});
        var rec = null, source = '';
        if (a.logo_layer != null && String(a.logo_layer) !== '') {
            var f = findLayer(a.logo_layer); if (f.error) return ask('Which layer is the logo? ' + f.error + '.', { candidates: f.candidates || logoCandidates() });
            if (K.isKitLayer(f.layer)) return refuse('That layer already belongs to a Sponsor Kit. Pick another layer, or remove the old kit first.');
            rec = CL.fromLayer(f.layer); if (!rec) return refuse('The layer "' + f.layer.name + '" is empty: there is no logo in it.'); source = 'layer "' + f.layer.name + '"';
        } else if (a.logo_data) {
            var file = dataUrlFile(a.logo_data, a.logo_name); if (!file) return refuse('The logo file could not be read.');
            try { rec = await CL.decode(file); } catch (e) { return refuse((e && e.message) || 'That picture could not be opened.'); } source = 'file ' + (a.logo_name || 'logo');
        } else return ask('Which logo? I need a layer that already holds it (name it) or a picture file path.', { candidates: logoCandidates() });
        var kit = { slots: {}, size: a.size == null ? 100 : Number(a.size), material: ['none', 'chrome', 'gold', 'goldfoil', 'matte', 'gloss'].indexOf(a.material) >= 0 ? a.material : 'none', extraTurn: Number(a.extra_turn) || 0, clean: { on: a.clean_box !== false, tol: 0, halo: 2, enclosed: false, bg: null } };
        ['door_l', 'door_r', 'quarter_l', 'quarter_r', 'tv_l', 'tv_r', 'hood', 'deck', 'rail_l', 'rail_r'].forEach(function (id) { kit.slots[id] = sl.ids.indexOf(id) >= 0; });
        await ensureCar();
        var S = K.begin({ kit: kit }); if (!S) return refuse('The Sponsor Kit could not start (no car paint open).');
        try {
            var res = kit.clean.on ? CL.cleanCanvas(rec.canvas, { tol: 0, halo: 2, enclosed: false }) : { canvas: rec.canvas, info: { mode: 'off' } };
            if (res.info && res.info.mode === 'none') { S.cancel(); return refuse('The logo has a box around it that could not be removed (' + (res.info.reason || 'no plain background found') + '). Nothing was changed. Use a logo with a transparent or plain background.'); }
            S.setLogo(res.canvas, { name: rec.name, kind: rec.kind, cleaned: !!kit.clean.on && res.info.mode !== 'off', info: res.info });
            if (a.size_cm != null && Number(a.size_cm) > 0) {          // wanted real width in cm: size is area-based, so bisect on the kit's own physical()
                var lo = 20, hi = 300, want = Number(a.size_cm), aspect = S.aspect();
                for (var it = 0; it < 18; it++) { var mid = (lo + hi) / 2, p = K.physical(Object.assign({}, S.kit, { size: mid }), aspect); if (p.wcm < want) lo = mid; else hi = mid; }
                S.set({ size: Math.round((lo + hi) / 2 * 10) / 10 });
            } else S.set({});
            var geo = S.geo || S.measure(), rep = S.report();
            if (!geo || !geo.ok) { S.cancel(); return refuse('The app cannot find the car parts on this paint (' + ((geo && geo.why) || 'no car map') + '), so it cannot place a logo on a named part. Nothing was changed. Teach the car in SPB or ask for the parts with spb_request_parts.'); }
            var placedIds = rep.map(function (r) { return r.slot; }), notPlaced = sl.ids.filter(function (id) { return placedIds.indexOf(id) < 0; }).map(function (id) { var d = K.SLOT_BY[id]; return { part: d ? d.label : id, why: 'this car has no room or no part that matches it' }; });
            // OA4 2026-10-10 (lane ONLINE-AI-4; bank item KO-07 "logo on the roof and the hood": 'roof' was dropped without a word because 'hood' was known; the model had to infer it from placed[]): every named part that got no logo is listed. Kill switch window.SPB_KIT_NOTPLACED_OFF.
            if (!W.SPB_KIT_NOTPLACED_OFF) sl.unknown.forEach(function (u) { notPlaced.push({ part: u, why: /roof/i.test(u) ? 'the Sponsor Kit has roof RAILS, not a roof panel: no logo went on the roof (name the left / right roof rail, or tell the buyer the roof was not done)' : 'not a part the Sponsor Kit sits on (doors, hood, trunk, rear quarters, TV panels, roof rails): no logo went there' }); });
            if (!rep.length) { S.cancel(); return refuse('None of the named parts could be found on this car, so no logo was placed. Nothing was changed.', { not_placed: notPlaced }); }
            var depth0 = undoDepth();
            var committed = S.commit();
            if (!committed) return refuse('The Sponsor Kit could not finish. Nothing was changed.');
            var matInfo = specOfKitMaterial(S.kit.material), placed = [];
            for (var i = 0; i < rep.length; i++) {
                var r = rep[i], layer = layers().filter(function (l) { return l && l.id === ('sponsor_' + S.kid + '_' + r.slot); })[0], fp = layer ? footprint(layer, r.part) : { opaque_px: null, on_part_pct: null, measured: false };
                placed.push({ slot: K.SLOT_BY[r.slot] ? K.SLOT_BY[r.slot].label : r.slot, part: r.part, layer: layer ? layer.name : null, real_size_cm: [R1(r.wcm), R1(r.hcm)], size_px: [r.wpx, r.hpx], turn_deg: Math.round(((r.theta * 180 / Math.PI) % 360 + 360) % 360), centre_px: [Math.round(r.cx), Math.round(r.cy)],
                    opaque_px: fp.opaque_px, on_part_pct: fp.on_part_pct, room_fit: typeof r.fit === 'number' ? Math.round(r.fit * 100) / 100 : undefined, room_warning: (typeof r.fit === 'number' && r.fit < 0.98) ? ('the logo is bigger than the free room on this part: only ' + Math.round(r.fit * 100) + '% of it fits, so it may run over an edge') : undefined });
            }
            LAST_KIT = { world: world(), label: 'sponsor kit', depth: undoDepth(), before: depth0 };
            var low = placed.filter(function (p) { return p.on_part_pct != null && p.on_part_pct < 95; }).map(function (p) { return p.slot + ' ' + p.on_part_pct + '% on the ' + p.part; });
            return out({ changed: true, kit: 'sponsor', logo: { source: source, box_removed: !!(res.info && res.info.mode && res.info.mode !== 'off' && res.info.mode !== 'alpha'), clean_mode: res.info && res.info.mode }, placed: placed, not_placed: notPlaced.length ? notPlaced : undefined, not_placed_note: notPlaced.length && !W.SPB_KIT_NOTPLACED_OFF ? 'Part(s) the buyer named got NO logo (see not_placed): tell the buyer which, and why.' : undefined,
                same_real_size_note: 'Every part carries the same real-world size (' + R1(placed[0].real_size_cm[0]) + ' x ' + R1(placed[0].real_size_cm[1]) + ' cm), turned to read right on the car.', material: matInfo,
                measured: { layers_added: placed.length, opaque_px_total: placed.reduce(function (s, p) { return s + (p.opaque_px || 0); }, 0), logo_over_the_edge: low.length ? low : 'none: every logo pixel is on its part', measured_from: 'the layer pixels against the car-map part masks (not a render)' },
                not_changed: 'zones, paint colours, other layers and the spec of everything else are untouched; the logos are new layers above the paint', undo_with: "spb_undo (or spb_kit action:'undo'): one step removes the whole kit" });
        } catch (e) { warn('sponsor', e); try { S.cancel(); } catch (e2) {} return out({ changed: false, error: 'The Sponsor Kit failed: ' + (e && e.message || e) + '. Nothing was kept.' }); }
    }
    function kitRemove(kind, a) {
        var K = kind === 'sponsor' ? W.SpbRevSponsor : W.SpbRevNumbers; if (!K || (K.off && K.off())) return refuse('That kit is switched off in this app build.');
        var seen = {}, kids = [], keys = {}; layers().forEach(function (l) { var p = K.kitOf && K.kitOf(l); if (p && p.kid) { if (!seen[p.kid]) { seen[p.kid] = 1; kids.push(p.kid); keys[p.kid] = []; } var sk = kind === 'sponsor' ? p.slot : p.place; if (sk && keys[p.kid].indexOf(sk) < 0) keys[p.kid].push(sk); } });
        if (!kids.length) return out({ changed: false, note: 'There is no ' + kind + ' kit on this car, so nothing was removed.' });
        // OA3 2026-10-10 (lane ONLINE-AI-3; bank item KO-11 "logo on the left door" then "take that logo off again": 1.4.4 removed EVERY sponsor kit incl. an older hood sponsor, one undo brought one back; 0 of 1 -> target 1 of 1): remove honours the named parts. Kill switch window.SPB_KIT_REMOVE_SCOPE_OFF.
        if (!W.SPB_KIT_REMOVE_SCOPE_OFF) {
            var listing = kids.map(function (kid) { return { layers: K.kitLayers(kid).map(function (l) { return l.name; }), slots: keys[kid].slice() }; });
            var pa = a && (a.parts != null ? a.parts : a.places), hasParts = Array.isArray(pa) ? pa.length > 0 : (pa != null && String(pa).trim() !== ''), pick = kids;
            if (!hasParts) {
                if (kids.length > 1) return ask('There are ' + kids.length + ' ' + kind + ' kits on this car (' + listing.map(function (x) { return x.layers.join(' + '); }).join('; ') + '). Which one should come off? Name its part. Nothing was removed.', { kits: listing });
            } else {
                var rs = kind === 'sponsor' ? slotsOf(pa) : placesOf(pa), want = rs.ids;
                if (!want.length) return ask('Which ' + kind + ' kit should come off? The named part is not one a kit sits on (' + String(Array.isArray(pa) ? pa.join(', ') : pa) + '). Existing kits: ' + listing.map(function (x) { return x.layers.join(' + '); }).join('; ') + '. Nothing was removed.', { kits: listing });
                pick = kids.filter(function (kid) { return keys[kid].some(function (sk) { return want.indexOf(sk) >= 0; }); });
                if (!pick.length) return out({ changed: false, note: 'No ' + kind + ' kit sits on the named part, so nothing was removed.', kits: listing });
                var split = pick.filter(function (kid) { return keys[kid].some(function (sk) { return want.indexOf(sk) < 0; }); });
                if (split.length) return ask('The ' + kind + ' kit on that part is ONE kit that also covers ' + keys[split[0]].filter(function (sk) { return want.indexOf(sk) < 0; }).join(', ') + ', and a kit comes off as a whole. Ask the buyer whether the whole kit should go; to remove it, call remove again naming all of: ' + keys[split[0]].join(', ') + '. Nothing was removed.', { kits: listing, name_all_of: keys[split[0]].slice() });
            }
            kids = pick;
        }
        var removed = 0, names = [];
        kids.forEach(function (kid) { var ls = K.kitLayers(kid); ls.forEach(function (l) { names.push(l.name); }); var S = K.begin({ kid: kid }); if (S && S.remove()) removed++; });
        LAST_KIT = { world: world(), label: 'remove ' + kind + ' kit', depth: undoDepth() };
        return out({ changed: removed > 0, kit: kind, removed_kits: removed, removed_layers: names, not_changed: 'zones, paint and every other layer (incl. other ' + kind + ' kits) are untouched', undo_with: removed > 1 ? "spb_undo steps:" + removed + " brings the " + removed + " kits back (one step each)" : "spb_undo (or spb_kit action:'undo') brings the kit back" });
    }

    // ------------------------------------------------------------------ NUMBER KIT
    var PLACE_WORDS = [['left', /\bleft\b.*\bdoor|\bdoor.*\bleft\b|\bleft\b/], ['right', /\bright\b.*\bdoor|\bdoor.*\bright\b|\bright\b/], ['roof', /\broof\b/]];
    function placesOf(list) {
        var ids = {}, unknown = [];
        (Array.isArray(list) ? list : [list]).forEach(function (p) {
            var s = String(p == null ? '' : p).toLowerCase().replace(/[_-]/g, ' ');
            if (!s.trim()) return;
            if (/\b(both|doors)\b/.test(s) && !/roof/.test(s)) { ids.left = 1; ids.right = 1; return; }
            var hit = false; PLACE_WORDS.forEach(function (w) { if (w[1].test(s)) { ids[w[0]] = 1; hit = true; } });
            if (!hit) unknown.push(String(p));
        });
        return { ids: Object.keys(ids), unknown: unknown };
    }
    function ringOf(o, dflt) { if (o == null) return dflt; if (typeof o === 'string') return { color: hex(o) || dflt.color, w: dflt.w || 5 }; var c = hex(o.color || o.colour); return { color: c || dflt.color, w: o.width != null ? Number(o.width) : (o.w != null ? Number(o.w) : (dflt.w || 5)) }; }
    async function numberPlace(a) {
        var N = W.SpbRevNumbers; if (!N || (N.off && N.off())) return refuse('The Number Kit is switched off or not loaded in this app build.');
        if (!layers().length) return refuse('This car is a flat picture with no layers: the Number Kit places its numbers as layers. Nothing was changed.');
        var num = String(a.number == null ? '' : a.number).replace(/[^A-Za-z0-9]/g, '').slice(0, 4);
        if (!num) return ask('What number (1 to 4 digits or letters)?');
        var pl = placesOf(a.places);
        if (!pl.ids.length) return ask('Where should the number go: left door, right door, roof (or all three)?', pl.unknown.length ? { not_understood: pl.unknown } : {});
        var kit = { number: num, places: { left: pl.ids.indexOf('left') >= 0, right: pl.ids.indexOf('right') >= 0, roof: pl.ids.indexOf('roof') >= 0 } };
        if (a.fill != null) { var fc = hex(a.fill); if (!fc) return refuse('"' + a.fill + '" is not a colour hex like #ffffff. Nothing was changed.'); kit.fill = fc; }
        if (a.outline != null) kit.ring1 = ringOf(a.outline, { color: '#000000', w: 5 });
        if (a.outline2 != null) kit.ring2 = ringOf(a.outline2, { color: '#ffffff', w: 5 });
        if (a.shadow != null) kit.shadow = a.shadow === false ? { on: false } : Object.assign({ on: true }, typeof a.shadow === 'object' ? a.shadow : {});
        ['font', 'bold', 'italic', 'slant', 'spacing', 'size'].forEach(function (k) { if (a[k] != null) kit[k] = a[k]; });
        if (a.roof_from === 'passenger' || a.roof_from === 'driver') kit.roofFrom = a.roof_from;
        if (['none', 'chrome', 'gloss', 'matte', 'satin'].indexOf(a.material) >= 0) kit.material = a.material;
        await ensureCar();
        var S = N.begin({ kit: kit }); if (!S) return refuse('The Number Kit could not start (no car paint open).');
        try {
            S.measure(); if (!S.geo || !S.geo.ok) { S.cancel(); return refuse('The app cannot find the car parts on this paint (' + ((S.geo && S.geo.why) || 'no car map') + '), so it cannot place a number on a door or the roof. Nothing was changed.'); }
            var hits = S.scanExisting(), exNames = [];
            if (hits && hits.length) {
                hits.forEach(function (e) { if (e.layer && exNames.indexOf(e.layer.name) < 0) exNames.push(e.layer.name); });
                if (a.existing !== 'replace' && a.existing !== 'alongside') { S.cancel(); return ask('This paint already has numbers (on the layer "' + exNames.join('", "') + '"). Replace them with the new number, or add the new one alongside? Nothing has changed.', { existing_numbers: exNames, options: ['replace', 'alongside'] }); }
                S.setReplace(a.existing === 'alongside' ? 'add' : 'replace');
            }
            var depth0 = undoDepth(); S.set({});
            var placedIds = Object.keys(S.at || {}), want = pl.ids.slice();
            if (!placedIds.length) { S.cancel(); return refuse('None of the named places exist on this car. Nothing was changed.'); }
            var matched = S.matched || {}, committed = S.commit();
            if (!committed) return refuse('The Number Kit could not finish. Nothing was changed.');
            var K2 = S.kit, mat = specOfKitMaterial(K2.material), placed = [];
            placedIds.forEach(function (p) {
                var layer = layers().filter(function (l) { return l && l.id === ('numkit_' + S.kid + '_' + p); })[0], geoP = S.geo && S.geo.places && S.geo.places[p], part = geoP && geoP.part || (p === 'roof' ? 'roof' : (p === 'left' ? 'left side' : 'right side')), fp = layer ? footprint(layer, part) : { opaque_px: null, on_part_pct: null, measured: false };
                placed.push({ place: N.PLACE_LABEL[p] || p, part: part, layer: layer ? layer.name : null, turn_deg: S.at[p] ? Math.round(((S.at[p].theta * 180 / Math.PI) % 360 + 360) % 360) : null, centre_px: S.at[p] ? [Math.round(S.at[p].cx), Math.round(S.at[p].cy)] : null, opaque_px: fp.opaque_px, on_part_pct: fp.on_part_pct, matched_old_number: matched[p] ? true : undefined });
            });
            LAST_KIT = { world: world(), label: 'number kit', depth: undoDepth(), before: depth0 };
            var notPlaced = want.filter(function (p) { return placedIds.indexOf(p) < 0; }).map(function (p) { return { place: N.PLACE_LABEL[p] || p, why: 'this car has no such place' }; });
            if (!W.SPB_KIT_NOTPLACED_OFF) pl.unknown.forEach(function (u) { notPlaced.push({ place: u, why: 'the Number Kit only knows left door, right door and roof: no number went there' }); });          // OA4 2026-10-10: named-but-unknown places are no longer dropped silently
            return out({ changed: true, kit: 'number', number: K2.number, placed: placed, not_placed: notPlaced.length ? notPlaced : undefined,
                style: { font: K2.font + (K2.bold ? ' bold' : '') + (K2.italic ? ' italic' : ''), fill: K2.fill, outline: K2.ring1.w > 0 ? { colour: K2.ring1.color, width_pct: K2.ring1.w } : 'none', outline2: K2.ring2.w > 0 ? { colour: K2.ring2.color, width_pct: K2.ring2.w } : 'none', shadow: K2.shadow.on ? 'on (app default unless you set it)' : 'off', slant: S.effSlant != null ? S.effSlant : K2.slant, size_pct: K2.size, roof_reads_from: K2.roofFrom, unspecified_style_is_the_app_default: true },
                material: mat, existing_numbers: exNames.length ? { layers: exNames, handled: a.existing === 'alongside' ? 'kept alongside' : 'replaced where the new number goes (the new number takes their height and centre)' } : 'none found',
                measured: { layers_added: placed.length, opaque_px_total: placed.reduce(function (s, p) { return s + (p.opaque_px || 0); }, 0), measured_from: 'the layer pixels against the car-map part masks (not a render)' },
                not_changed: 'zones, paint colours and every other layer are untouched' + (exNames.length ? ' (except the old numbers listed above)' : ''), undo_with: "spb_undo (or spb_kit action:'undo'): one step removes the whole kit" });
        } catch (e) { warn('number', e); try { S.cancel(); } catch (e2) {} return out({ changed: false, error: 'The Number Kit failed: ' + (e && e.message || e) + '. Nothing was kept.' }); }
    }

    // ------------------------------------------------------------------ SPEC DOCTOR (read) + fixes (on request)
    function whereOf(f, Wd, Hd) {
        var names = [], boxes = null; try { var m = W.SpbProCar && W.SpbProCar.map ? W.SpbProCar.map() : null; boxes = m && m.boxes; } catch (e) {}
        (f.regions || []).slice(0, 4).forEach(function (r) {
            var fx = r.cx / Wd, fy = r.cy / Hd, nm = null, ar = 9;
            if (boxes) Object.keys(boxes).forEach(function (k) { var b = boxes[k] && boxes[k].bbox; if (!b) return; if (fx >= b[0] && fx <= b[2] && fy >= b[1] && fy <= b[3]) { var q = (b[2] - b[0]) * (b[3] - b[1]); if (q < ar) { ar = q; nm = k; } } });
            if (!nm) nm = (fy < 0.34 ? 'top' : fy > 0.66 ? 'bottom' : 'middle') + ' ' + (fx < 0.34 ? 'left' : fx > 0.66 ? 'right' : 'centre') + ' of the sheet';
            if (names.indexOf(nm) < 0) names.push(nm);
        });
        if (f.check === 'decal-chrome' && f.layers) return f.layers.map(function (h) { return h.name; });
        if (f.check === 'flat') return ['the whole car'];
        return names.length ? names : ['the whole car'];
    }
    function findingOut(f, Wd, Hd) { return { key: f.key, check: f.check, severity: f.severity, title: f.title, where: whereOf(f, Wd, Hd), area_px: f.check === 'flat' ? undefined : Number(f.area || 0), why_it_matters: f.why, fixes: (f.fixes || []).map(function (x) { return { id: x.id, label: x.label }; }) }; }
    async function specCheck() {
        var D = W.SPBRevDoctor; if (!D || (typeof D.off === 'function' ? D.off() : D.off) || typeof D.run !== 'function') return refuse('The Spec Doctor is switched off or not loaded in this app build.');
        var t0 = Date.now(), r = await D.run(); if (!r) return out({ changed: false, error: 'The Spec Doctor could not run a check (it was busy or the render failed). Nothing was changed.' });
        var Wd = r.W || (D.state && D.state.input && D.state.input.W) || 2048, Hd = r.H || (D.state && D.state.input && D.state.input.H) || 2048;
        var fs = (r.findings || []).map(function (f) { return findingOut(f, Wd, Hd); });
        return out({ changed: false, kit: 'spec', action: 'check', findings: fs, counts: { high: fs.filter(function (f) { return f.severity === 'high'; }).length, medium: fs.filter(function (f) { return f.severity === 'medium'; }).length, tip: fs.filter(function (f) { return f.severity === 'tip'; }).length },
            clean: fs.length === 0, checked_full_size: r.sameSize !== false, seconds: Math.round((Date.now() - t0) / 100) / 10, measured_from: 'a full-size render of the spec map (the one RENDER writes), checked by the Spec Doctor; it gives no score',
            note: fs.length ? 'These are mistakes the Doctor found. Nothing was changed. Offer a fix per finding; apply only when the buyer asks (spb_kit action:"fix", finding = key, fix = id).' : 'Nothing to fix: the Doctor found no mistake. Nothing was changed.' });
    }
    async function specFix(a) {
        var D = W.SPBRevDoctor; if (!D || (typeof D.off === 'function' ? D.off() : D.off) || typeof D.fix !== 'function') return refuse('The Spec Doctor is switched off or not loaded in this app build.');
        var cur = D.result && D.result(); if (!cur) return refuse('Run a check first (spb_kit kit:"spec" action:"check"), so there is a finding to fix. Nothing was changed.');
        var key = String(a.finding || ''), f = (cur.findings || []).filter(function (x) { return x.key === key || x.check === key; })[0];
        if (!f) return refuse('No finding "' + key + '" in the last check. Findings: ' + (cur.findings || []).map(function (x) { return x.key; }).join(', ') + '. Nothing was changed.');
        var fxid = String(a.fix || ''), fx = (f.fixes || []).filter(function (x) { return x.id === fxid; })[0];
        if (!fx) return ask('Which fix? ' + (f.fixes || []).map(function (x) { return x.id + ' = ' + x.label; }).join('; ') + '. Nothing has changed.', { fixes: (f.fixes || []).map(function (x) { return { id: x.id, label: x.label }; }) });
        var d0 = undoDepth(), rec = await D.fix(f.key, fx.id);
        if (!rec || !rec.ok) return out({ changed: false, error: 'The Doctor could not apply that fix' + (rec && rec.why ? ': ' + rec.why : '') + '. Nothing was changed.' });
        var after = D.result && D.result(), left = after ? (after.findings || []).map(function (x) { return x.key; }) : null;
        LAST_KIT = { world: world(), label: 'spec fix', depth: undoDepth(), before: d0, unified: true };
        return out({ changed: true, kit: 'spec', action: 'fix', fixed: f.title, fix: fx.label, problem_gone: rec.gone, still_found_after: left, note: rec.gone === true ? 'The re-check no longer sees this problem.' : (rec.gone === false ? 'Applied, but the re-check still sees part of it.' : 'Applied; the re-check could not confirm it (partial check). Run spb_kit check again.'), not_changed: 'artwork, zones and colours are untouched; only the spec was changed', undo_with: "spb_undo: one step per fix" });
    }

    // ------------------------------------------------------------------ SPEC AUTOPILOT: propose (read-only) / apply (needs the buyer's agreement)
    function rowOut(r) {
        var C = W.SPBAutoSpecCore, id = r.pick || r.material || null, mt = id && C && C.MAT ? C.MAT[id] : null;
        return { layer_id: r.id, layer: r.name, kind: r.kindName || r.kind, parts: r.parts ? Object.keys(r.parts) : undefined, proposed: mt ? mt.name : (id || null), proposed_spec: mt && mt.cc != null ? { M: mt.m, R: mt.r, C: mt.cce != null ? mt.cce : mt.cc } : null,
            now_spec: r.now ? { M: r.now.m, R: r.now.r, C: r.now.cc } : undefined, confidence_pct: r.conf != null ? Math.round(r.conf * 100) : undefined, why: r.why || r.sentence, included: r.include !== false, already_right: r.same ? true : undefined };
    }
    async function autoScan(a) {
        var A = W.SPBRevAutoSpec; if (!A || (typeof A.off === 'function' ? A.off() : A.off) || typeof A.scan !== 'function') return { err: refuse('Spec Autopilot is switched off or not loaded in this app build.') };
        var prevPreview = A.state ? A.state.preview : undefined, prevFix = A.state ? A.state.autoFix : undefined;
        if (A.state) { A.state.preview = false; A.state.autoFix = false; }          // propose = read-only: no live trial on the layers (the panel's own switches are put back after the call)
        var before = layers().map(function (l) { return String(l.id) + ':' + JSON.stringify(W.SPBRevLayerMat && W.SPBRevLayerMat.get ? W.SPBRevLayerMat.get(l) : null); }).join('|');
        await A.scan({}); if (a && a.style != null && A.setStyle) A.setStyle(Math.max(0, Math.min(1, Number(a.style))), true);
        try { if (a && a.measure_now !== false && A.baseline) await A.baseline(); } catch (e) { warn('baseline', e); }
        return { A: A, before: before, restore: function () { try { if (A.state) { if (prevPreview !== undefined) A.state.preview = prevPreview; if (prevFix !== undefined) A.state.autoFix = prevFix; } } catch (e) {} } };
    }
    async function autoPropose(a) {
        var s = await autoScan(a); if (s.err) return s.err; var A = s.A, rows = (A.rows() || []);
        if (!rows.length) { s.restore(); return out({ changed: false, kit: 'spec', action: 'propose', rows: [], note: (A.state && A.state.status) || 'No printed layers to read (a flat picture has none). Nothing was changed.' }); }
        var after = layers().map(function (l) { return String(l.id) + ':' + JSON.stringify(W.SPBRevLayerMat && W.SPBRevLayerMat.get ? W.SPBRevLayerMat.get(l) : null); }).join('|'); s.restore();
        return out({ changed: false, kit: 'spec', action: 'propose', style: A.state && A.state.style, proposal: rows.map(rowOut), skipped: (A.state && A.state.skipped || []).slice(0, 12).map(function (x) { return { layer: x.name || x.id, why: x.why || x.reason }; }),
            layers_untouched_by_this_call: after === s.before, note: 'This is a PROPOSAL. Nothing was changed. Read it out (layer, material, M/R/C), then apply ONLY if the buyer agrees (spb_kit kit:"spec" action:"apply" buyer_agreed:true). It assigns existing materials only; artwork, zones and colours are never touched.' });
    }
    async function autoApply(a) {
        if (a.buyer_agreed !== true) return ask('Apply only after the buyer agrees. Show the proposal (action:"propose"), then call apply with buyer_agreed:true. Nothing has changed.');
        var s = await autoScan(a); if (s.err) return s.err;
        try { return await autoApplyCore(a, s); } finally { s.restore(); }
    }
    async function autoApplyCore(a, s) {
        var A = s.A, rows = A.rows() || [];
        if (!rows.length) return refuse('No printed layers to assign a material to. Nothing was changed.');
        if (Array.isArray(a.only_layers) && a.only_layers.length) { var keep = a.only_layers.map(function (q) { return String(q).toLowerCase(); }); rows.forEach(function (r) { A.setInclude(r.id, keep.indexOf(String(r.name).toLowerCase()) >= 0 || keep.indexOf(String(r.id).toLowerCase()) >= 0); }); }
        var inc = rows.filter(function (r) { return r.include !== false; }); if (!inc.length) return refuse('Nothing is ticked to apply. Nothing was changed.');
        var d0 = undoDepth(), res = await A.apply();
        if (!res) return out({ changed: false, error: 'Spec Autopilot could not apply (busy or no layers). Nothing was changed.' });
        LAST_KIT = { world: world(), label: 'auto spec', depth: undoDepth(), before: d0 };
        var lm = W.SPBRevLayerMat, now = inc.map(function (r) { var L = layers().filter(function (l) { return String(l.id) === String(r.id); })[0], rec = L && lm && lm.get ? lm.get(L) : null; return Object.assign(rowOut(r), { layer_material_now: rec && lm.describe ? lm.describe(rec) : 'none' }); });
        return out({ changed: !!res.changed, kit: 'spec', action: 'apply', layers_changed: res.count, materials: now, undone_with: undefined, doctor_after: res.doctor, note: 'Layer materials were assigned (spec only). The Doctor re-checked the whole spec: report doctor_after honestly (counts + items). Doctor fixes were NOT run; offer them.', not_changed: 'artwork, zones and colours are untouched', undo_with: "spb_undo: one step undoes every layer" });
    }

    // ------------------------------------------------------------------ undo (the newest kit write)
    function kitUndo() {
        if (!LAST_KIT) return refuse('There is no kit change from this bridge to undo.');
        var before = undoDepth(), nl0 = layers().length;
        if (LAST_KIT.world && world() !== LAST_KIT.world) return refuse('Something else in the app changed after the kit (zones, layers or undo steps), so the kit was NOT undone: undoing now could take back the wrong thing. Undo the newest change first (spb_undo), or use Ctrl+Z in the app.');
        try { if (typeof W.undoDrawStroke === 'function') W.undoDrawStroke(); else if (typeof W.undoLayerEdit === 'function') W.undoLayerEdit(); else return refuse('The app has no undo hook here.'); } catch (e) { return out({ changed: false, error: 'Undo failed: ' + (e && e.message || e) }); }
        var lab = LAST_KIT.label; LAST_KIT = null;
        return out({ changed: true, undone: lab, layer_count: [nl0, layers().length], layer_undo_depth: [before, undoDepth()], note: 'The ' + lab + ' was undone (one step). Zones and paint were not touched.' });
    }

    // ------------------------------------------------------------------ dispatch
    var BUSY = false;
    async function run(a) {
        a = a || {};
        var kind = String(a.kit || '').toLowerCase(), act = String(a.action || '').toLowerCase();
        if (off()) return { ok: false, error: 'spb_kit is switched off in this app build (SPB_ONLINE_KITS_OFF).' };
        if (!kind && act !== 'undo') return { ok: false, error: 'kit is required: sponsor, number or spec.' };
        // OA3 2026-10-10: Undo is an EDIT. It used to run before the BUSY / lease guards (reproduced by the ChatGPT lane: undone while another AI owned editing and while a check was running). Now it takes the same lease and busy lock (kill switch window.SPB_KIT_UNDO_GUARD_OFF restores the old early return).
        if (act === 'undo' && W.SPB_KIT_UNDO_GUARD_OFF) return kitUndo();
        var read = (act !== 'undo' && kind === 'spec' && (act === 'check' || act === 'propose' || act === 'list'));
        if (BUSY) return { ok: false, error: 'A kit call is still running. Wait for it.' };
        var lease = read ? null : W.SpbAiLease;
        if (lease && !lease.begin('external')) return { ok: false, error: 'Another AI owns editing. Wait two minutes after its last call, or use Take over in SPB in the bridge settings.' };
        BUSY = true;
        try {
            if (act === 'undo') return kitUndo();
            if (kind === 'sponsor') return act === 'remove' ? kitRemove('sponsor', a) : (act === '' || act === 'place' ? await sponsorPlace(a) : { ok: false, error: 'sponsor action must be place or remove.' });
            if (kind === 'number') return act === 'remove' ? kitRemove('number', a) : (act === '' || act === 'place' ? await numberPlace(a) : { ok: false, error: 'number action must be place or remove.' });
            if (kind === 'spec') {
                if (act === 'check') return await specCheck();
                if (act === 'fix') return await specFix(a);
                if (act === 'propose' || act === 'list') return await autoPropose(a);
                if (act === 'apply') return await autoApply(a);
                return { ok: false, error: 'spec action must be check, fix, propose or apply.' };
            }
            return { ok: false, error: 'kit must be sponsor, number or spec.' };
        } catch (e) { warn('run', e); return { ok: false, error: 'spb_kit failed: ' + (e && e.message || e) }; }
        finally { BUSY = false; try { if (lease) lease.end(); } catch (e) {} }
    }

    // ------------------------------------------------------------------ hook into the bridge host's tool executor
    function wrap() {
        var P = W.spbProAI; if (!P || typeof P.mcpCall !== 'function') return false;
        if (P.mcpCall.__oaKits === VER) return true;
        var orig = P.mcpCall, w = function (tool, args) { if (tool === 'kit') return off() ? { ok: false, error: 'spb_kit is switched off in this app build (SPB_ONLINE_KITS_OFF). Nothing was changed.' } : (W.SpbOnlineKits && W.SpbOnlineKits.run ? W.SpbOnlineKits.run : run)(args || {}); return orig.apply(this, arguments); };          // dispatch through window.SpbOnlineKits so a re-injected newer copy (dev) takes over without re-wrapping
        w.__oaKits = VER; P.mcpCall = w; return true;
    }
    W.SpbOnlineKits = { VERSION: VER, run: run, wrap: wrap, off: off, _internal: { slotsOf: slotsOf, placesOf: placesOf, findLayer: findLayer, footprint: footprint, specOfKitMaterial: specOfKitMaterial } };
    if (!wrap()) { var tries = 0, iv = setInterval(function () { if (wrap() || ++tries > 120) clearInterval(iv); }, 500); }
})(typeof window !== 'undefined' ? window : globalThis);
