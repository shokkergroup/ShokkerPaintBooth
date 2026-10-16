/* flake-studio.js - [SPB-REV-FLAKE 2026-10-10, lane REV-FLAKE] Flake Studio: metallic flake and pearl designed to read right IN iRacing.
 * Entry: Material / Spec > Flake Studio…   (also the Spec Brush source list: "Flake Studio…").
 * WHY: flake drawn too fine averages to flat grey once iRacing mips the texture at distance; drawn too coarse it looks like glitter. Painters guess.
 * This panel sizes flake in real centimetres (the car's own px-per-cm from the Sponsor Kit's measure), shows the flake at iRacing's mip levels
 * (2x2 box filter, the way the sim builds them) with a meter of how much flake signal survives each distance, and a Sim-Safe mode that FITS a
 * coarse flake band so the flake still reads at mip 2. The bars come from the owner's own verdicts (engine/rev_flake.py header, fit.json).
 * Apply: a zone (finish override: the zone keeps its colour, base -> Gloss foundation, the flake owns M/R/CC), the Material Brush (a Brush
 * Studio coat carrying the flake), or a layer material. ALL three render through ONE engine hook (zone field `spb_flake`), in the live preview
 * and in RENDER, and the preview tiles here come from the same Python code (/api/flake/preview).
 * State lives where the app already keeps it exact: the zone (zone undo / project / autosave) and the brush coat (REV-MATERIAL persistence).
 * Kill switch: window.SPB_FLAKE_OFF = true or localStorage SPB_FLAKE_OFF = '1' (no menu, no panel, no payload field); server env SPB_FLAKE_OFF=1.
 */
(function (root) {
    'use strict';
    if (!root || !root.document || root.SpbFlakeStudio) return;
    var doc = root.document, TAG = '[REV-FLAKE]', VER = 'flake-ui-1.0';
    function off() { try { if (root.SPB_FLAKE_OFF) return true; return root.localStorage.getItem('SPB_FLAKE_OFF') === '1'; } catch (_) { return !!root.SPB_FLAKE_OFF; } }
    function warn(w, e) { try { console.warn(TAG, w, e && e.message || e); } catch (_) {} }
    function toast(m, k) { try { if (typeof root.showToast === 'function') root.showToast(m, k); } catch (_) {} }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function clamp(v, lo, hi, d) { v = Number(v); return isFinite(v) ? Math.max(lo, Math.min(hi, v)) : d; }
    function hex2rgb(h) { var m = /^#?([0-9a-f]{6})$/i.exec(String(h || '')); if (!m) return null; var n = parseInt(m[1], 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
    function rgb2hex(c) { if (!c) return '#ffffff'; return '#' + c.slice(0, 3).map(function (v) { return ('0' + Math.round(v).toString(16)).slice(-2); }).join(''); }
    function api(path, body) {
        var base = (root.ShokkerAPI && root.ShokkerAPI.baseUrl) || '';
        return fetch(base + path, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined })
            .then(function (r) { return r.json(); });
    }

    // ------------------------------------------------------------------ the six starting looks (size in REAL cm on the car)
    var LOOKS = [
        { id: 'fine_silver', name: 'Fine Silver', tip: 'Fine silver metallic: tiny bright flake in a silver base', p: { size_cm: 0.25, density: 0.85, sparkle: 0.5, base_m: 170, base_r: 55, flake_m: 235, flake_r: 25, cc: 16, flake_rgb: [235, 238, 242], flake_mix: 0.15, pearl_rgb: null, pearl_mix: 0, bright: 0.3 } },
        { id: 'bass_boat', name: 'Bass-Boat', tip: 'Coarse bass-boat metal flake: big mirror platelets that throw sparkle', p: { size_cm: 1.2, density: 0.9, sparkle: 0.9, base_m: 200, base_r: 40, flake_m: 255, flake_r: 15, cc: 16, flake_rgb: [255, 250, 235], flake_mix: 0.35, pearl_rgb: null, pearl_mix: 0, bright: 0.5 } },
        { id: 'candy_flake', name: 'Candy Over Flake', tip: 'Candy over flake: the zone colour stays deep, bright flake glints under it', p: { size_cm: 0.6, density: 0.8, sparkle: 0.7, base_m: 210, base_r: 30, flake_m: 250, flake_r: 18, cc: 16, flake_rgb: [255, 255, 255], flake_mix: 0.1, pearl_rgb: null, pearl_mix: 0, bright: 0.45 } },
        { id: 'white_pearl', name: 'White Pearl', tip: 'White pearl: soft low-metal pearl with a warm second tone', p: { size_cm: 0.4, density: 0.7, sparkle: 0.35, base_m: 40, base_r: 45, flake_m: 140, flake_r: 30, cc: 16, flake_rgb: [250, 250, 250], flake_mix: 0.2, pearl_rgb: [255, 236, 214], pearl_mix: 0.45, bright: 0.2 } },
        { id: 'shift_pearl', name: 'Colour-Shift Pearl', tip: 'Colour-shift pearl: every flake carries some of a second colour', p: { size_cm: 0.5, density: 0.85, sparkle: 0.55, base_m: 120, base_r: 35, flake_m: 220, flake_r: 22, cc: 16, flake_rgb: null, flake_mix: 0, pearl_rgb: [40, 200, 255], pearl_mix: 0.6, bright: 0.3 } },
        { id: 'satin_metallic', name: 'Satin Metallic', tip: 'Satin metallic: fine flake under a satin (dull) clearcoat', p: { size_cm: 0.3, density: 0.75, sparkle: 0.4, base_m: 150, base_r: 120, flake_m: 210, flake_r: 80, cc: 90, flake_rgb: null, flake_mix: 0, pearl_rgb: null, pearl_mix: 0, bright: 0.2 } }
    ];
    var LOOK_BY = {}; LOOKS.forEach(function (l) { LOOK_BY[l.id] = l; });
    var LS = 'spbFlakeStudio.v1';
    var S = { look: 'fine_silver', p: JSON.parse(JSON.stringify(LOOKS[0].p)), sim: false, coarse_px: 6, coarse_mix: 0, fitSig: '', fit: null, mip: 2, target: 'zone', seed: 7, last: null, pxcm: null, pxSrc: '', busy: 0 };
    try { var sv = JSON.parse(root.localStorage.getItem(LS) || 'null'); if (sv && sv.p) { ['look', 'p', 'sim', 'coarse_px', 'coarse_mix', 'fitSig', 'mip', 'target', 'seed'].forEach(function (k) { if (sv[k] !== undefined) S[k] = sv[k]; }); } } catch (_) {}
    function saveLocal() { try { root.localStorage.setItem(LS, JSON.stringify({ look: S.look, p: S.p, sim: S.sim, coarse_px: S.coarse_px, coarse_mix: S.coarse_mix, fitSig: S.fitSig, mip: S.mip, target: S.target, seed: S.seed })); } catch (_) {} }

    // ------------------------------------------------------------------ car scale (cm -> px): the Sponsor Kit's own measure (read only)
    function dims() { var c = doc.getElementById('paintCanvas'); return c && c.width ? [c.width, c.height] : [2048, 2048]; }
    function carScale() {
        var d = dims(), key = d.join('x') + ':' + ((root.SpbRevSponsor && root.SpbRevSponsor.version) || '');
        if (S.pxcm && S._sk === key) return S.pxcm;
        var vals = [], src = '';
        try {
            var m = root.SpbRevSponsor && root.SpbRevSponsor.measure && root.SpbRevSponsor.measure();
            if (m && m.ok && m.slots) Object.keys(m.slots).forEach(function (k) { var v = m.slots[k] && m.slots[k].pxcm; if (isFinite(v) && v > 0.5 && v < 40) vals.push(v); });
        } catch (e) { warn('measure', e); }
        if (vals.length) { vals.sort(function (a, b) { return a - b; }); S.pxcm = vals[vals.length >> 1]; src = 'measured from this car (' + vals.length + ' parts)'; }
        else {
            S.pxcm = 4.2 * d[0] / 2048; src = 'typical 4.2 px/cm on a 2048 sheet';
            // the car shape is not measured yet: measure it once (the Sponsor Kit's own path: SpbRevSym.build), then re-read the scale
            if (!S._measuring && root.SpbRevSym && typeof root.SpbRevSym.build === 'function' && !(root.SpbRevSym.ready && root.SpbRevSym.ready())) {
                S._measuring = true; src += ', measuring this car…';
                Promise.resolve(root.SpbRevSym.build(false)).then(function () { S._sk = null; S.pxcm = null; carScale(); if (panel) { syncVals(); schedule(false); } }).catch(function (e) { warn('measure car', e); });
            }
        }
        S.pxSrc = src; S._sk = key;
        return S.pxcm;
    }

    // ------------------------------------------------------------------ params (what the zone / coat carries; the engine reads exactly this)
    function fitSig() { var p = S.p; return [p.size_cm, p.density, p.sparkle, p.base_m, p.base_r, p.flake_m, p.flake_r, S.seed, carScale().toFixed(3)].join('|'); }
    function params() {
        var p = S.p, d = dims(), px = carScale();
        var o = { v: 1, look: S.look, canvas: d, size_cm: +p.size_cm, pxcm: +px.toFixed(3), size_px: +(p.size_cm * px).toFixed(3), density: +p.density, sparkle: +p.sparkle,
            base_m: Math.round(p.base_m), base_r: Math.round(Math.max(15, p.base_r)), flake_m: Math.round(p.flake_m), flake_r: Math.round(Math.max(15, p.flake_r)), cc: Math.round(Math.max(16, p.cc)),
            flake_rgb: p.flake_rgb ? p.flake_rgb.slice(0, 3) : null, flake_mix: +p.flake_mix, pearl_rgb: p.pearl_rgb ? p.pearl_rgb.slice(0, 3) : null, pearl_mix: +p.pearl_mix,
            bright: +p.bright, sim_safe: !!S.sim, coarse_px: +S.coarse_px, coarse_mix: S.sim ? +S.coarse_mix : 0, seed: S.seed | 0 };
        return o;
    }
    function loadFrom(f) {
        if (!f || typeof f !== 'object') return;
        Object.keys(S.p).forEach(function (k) { if (f[k] !== undefined) S.p[k] = Array.isArray(f[k]) ? f[k].slice() : f[k]; });
        S.look = f.look || 'custom'; S.sim = !!f.sim_safe;
        if (f.coarse_px) S.coarse_px = f.coarse_px;
        S.coarse_mix = +f.coarse_mix || 0; S.seed = f.seed == null ? S.seed : (f.seed | 0);
        S.fit = null; S.fitSig = '';   // the fit is deterministic: open() refits and gets the same band
        saveLocal();
    }
    function lookName(id) { return (LOOK_BY[id] && LOOK_BY[id].name) || 'Custom Flake'; }

    // ------------------------------------------------------------------ panel
    var ICON = {
        flake: '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/><path d="M18.5 14.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/><path d="M5.5 15.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z"/>',
        x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    };
    function svg(k, sz) { return '<svg viewBox="0 0 24 24" width="' + (sz || 14) + '" height="' + (sz || 14) + '" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[k] + '</svg>'; }
    var CSS = '#spbFlakeStudio{position:fixed;display:flex;flex-direction:column;overflow:hidden;color:var(--pl-tx,#e8e8ea);font:12px/1.35 system-ui,Segoe UI,sans-serif}' +
        '#spbFlakeStudio .spb-fl-body{overflow-y:auto;overflow-x:hidden;padding:8px 10px;flex:1 1 auto;min-height:0}' +
        '#spbFlakeStudio .spb-fl-looks{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-bottom:8px}' +
        '#spbFlakeStudio .spb-fl-look{padding:5px 4px;border:1px solid var(--pl-bd,#3a3a42);border-radius:6px;background:transparent;color:inherit;font:inherit;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
        '#spbFlakeStudio .spb-fl-look.on{border-color:var(--ph-teal,#2fb8ac);box-shadow:inset 0 0 0 1px var(--ph-teal,#2fb8ac)}' +
        '#spbFlakeStudio .spb-fl-row{display:grid;grid-template-columns:92px 1fr 62px;align-items:center;gap:6px;margin:3px 0}' +
        '#spbFlakeStudio .spb-fl-row input[type=range]{width:100%;min-width:0}' +
        '#spbFlakeStudio .spb-fl-v{text-align:right;font-variant-numeric:tabular-nums;color:var(--pl-tx2,#b8b8c0);white-space:nowrap}' +
        '#spbFlakeStudio .spb-fl-col{display:flex;gap:4px;align-items:center}#spbFlakeStudio .spb-fl-col input[type=color]{width:26px;height:20px;padding:0;border:1px solid var(--pl-bd,#3a3a42);background:none}' +
        '#spbFlakeStudio .spb-fl-sec{margin:8px 0 4px;font-weight:600;color:var(--pl-tx2,#b8b8c0);display:flex;justify-content:space-between;align-items:center}' +
        '#spbFlakeStudio .spb-fl-view{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px}' +
        '#spbFlakeStudio .spb-fl-tile{position:relative;aspect-ratio:1/1;background:#111;border:1px solid var(--pl-bd,#3a3a42);border-radius:4px;overflow:hidden}' +
        '#spbFlakeStudio .spb-fl-tile img{width:100%;height:100%;display:block;image-rendering:pixelated}' +
        '#spbFlakeStudio .spb-fl-tile span{position:absolute;left:3px;bottom:2px;font-size:10px;background:rgba(0,0,0,.6);padding:0 3px;border-radius:3px}' +
        '#spbFlakeStudio .spb-fl-meter{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;align-items:end;height:64px;position:relative;margin-top:4px;border-bottom:1px solid var(--pl-bd,#3a3a42)}' +
        '#spbFlakeStudio .spb-fl-bar{background:var(--pl-tx2,#8a8a94);border-radius:3px 3px 0 0;position:relative;min-height:2px;cursor:pointer}' +
        '#spbFlakeStudio .spb-fl-bar.ok{background:var(--ph-teal,#2fb8ac)}#spbFlakeStudio .spb-fl-bar.sel{outline:1px solid #fff}' +
        '#spbFlakeStudio .spb-fl-bar b{position:absolute;top:-14px;left:0;right:0;text-align:center;font-weight:500;font-size:10px}' +
        '#spbFlakeStudio .spb-fl-line{position:absolute;left:0;right:0;border-top:1px dashed #fff;opacity:.55;pointer-events:none}' +
        '#spbFlakeStudio .spb-fl-mlab{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;font-size:10px;text-align:center;color:var(--pl-tx2,#b8b8c0)}' +
        '#spbFlakeStudio .spb-fl-note{color:var(--pl-tx2,#b8b8c0);font-size:11px;margin:4px 0}' +
        '#spbFlakeStudio .spb-fl-warn{color:#e8b04a}' +
        '#spbFlakeStudio .spb-fl-seg{display:grid;grid-template-columns:1fr 1.5fr 1fr;gap:4px;margin:0 0 8px}#spbFlakeStudio .spb-fl-foot{gap:6px}';
    var panel = null, moved = false, pvT = 0, fitT = 0, pvSeq = 0;
    function $(s) { return panel && panel.querySelector(s); }
    function row(key, label, min, max, step, title) {
        return '<div class="spb-fl-row" title="' + esc(title) + '"><span>' + label + '</span><input type="range" data-k="' + key + '" min="' + min + '" max="' + max + '" step="' + step + '"><span class="spb-fl-v" data-v="' + key + '"></span></div>';
    }
    function build() {
        if (panel) return panel;
        if (!doc.getElementById('spbFlakeCss')) { var st = doc.createElement('style'); st.id = 'spbFlakeCss'; st.textContent = CSS; doc.head.appendChild(st); }
        panel = doc.createElement('div'); panel.id = 'spbFlakeStudio'; panel.className = 'spb-ph-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Flake Studio'); panel.style.display = 'none';
        panel.innerHTML =
            '<div class="spb-ph-head"><span class="spb-ph-ttl">' + svg('flake', 16) + '<span>Flake Studio</span></span><button type="button" class="spb-ph-x" data-act="close" title="Close (Esc)" aria-label="Close">' + svg('x') + '</button></div>' +
            '<div class="spb-fl-body">' +
            '<div class="spb-fl-looks">' + LOOKS.map(function (l) { return '<button type="button" class="spb-fl-look" data-look="' + l.id + '" title="' + esc(l.tip) + '">' + esc(l.name) + '</button>'; }).join('') + '</div>' +
            '<div class="spb-fl-sec" style="margin-top:0"><span>Put It On</span></div>' +
            '<div class="spb-fl-seg" role="radiogroup" aria-label="Where the flake goes">' +
            '<button type="button" class="spb-fl-look" data-tg="zone" title="The selected zone: its colour stays, the flake sets metal, roughness and clearcoat">Zone</button>' +
            '<button type="button" class="spb-fl-look" data-tg="brush" title="Load the Material Brush with this flake and paint it where you want it">Material Brush</button>' +
            '<button type="button" class="spb-fl-look" data-tg="layer" title="The selected layer (sponsor, number, logo): the flake follows the art">Layer</button></div>' +
            row('size_cm', 'Flake Size', 0.05, 3, 0.05, 'Flake size in real centimetres on this car (converted with the car’s own px-per-cm)') +
            row('density', 'Density', 0, 1, 0.01, 'How much of the surface is flake (the rest is the base coat between flakes)') +
            row('sparkle', 'Sparkle', 0, 1, 0.01, 'Per-flake spec variation: how differently each flake catches the light (metal + roughness per flake)') +
            '<div class="spb-fl-row" title="Flake colour mixed into the zone’s own colour on each flake"><span>Flake Colour</span><span class="spb-fl-col"><input type="checkbox" data-on="flake"><input type="color" data-c="flake"><input type="range" data-k="flake_mix" min="0" max="1" step="0.01"></span><span class="spb-fl-v" data-v="flake_mix"></span></div>' +
            '<div class="spb-fl-row" title="Pearl / colour shift: a second colour carried by the flakes (each flake a different amount)"><span>Pearl Colour</span><span class="spb-fl-col"><input type="checkbox" data-on="pearl"><input type="color" data-c="pearl"><input type="range" data-k="pearl_mix" min="0" max="1" step="0.01"></span><span class="spb-fl-v" data-v="pearl_mix"></span></div>' +
            '<div class="spb-fl-sec"><span>Spec</span><span class="spb-fl-note">R metal · G rough · B clearcoat</span></div>' +
            row('base_m', 'Base Metal', 0, 255, 1, 'Metallic (R) of the base coat between the flakes') +
            row('base_r', 'Base Rough', 15, 255, 1, 'Roughness (G) of the base coat; never below 15 (iron rule)') +
            row('flake_m', 'Flake Metal', 0, 255, 1, 'Metallic (R) of a flake that faces the light') +
            row('flake_r', 'Flake Rough', 15, 255, 1, 'Roughness (G) of a flake that faces the light (edge-on flakes are rougher by Sparkle)') +
            row('cc', 'Clearcoat', 16, 255, 1, 'Clearcoat (B): 16 = max gloss, higher = duller. Never 1-15 (iron rule)') +
            '<div class="spb-fl-sec"><span>Seen In iRacing</span><label title="Mix a coarse flake band with the fine one so the flake still reads at mip 2 (fitted to the owner’s flat / glitter verdicts)"><input type="checkbox" data-sim> Sim-Safe</label></div>' +
            '<div class="spb-fl-note" data-fitline></div>' +
            '<div class="spb-fl-row" title="Up close = mip 0 (the full 2048 sheet); each step is one iRacing mip level (2x2 box filter)"><span>Distance</span><input type="range" data-mip min="0" max="4" step="1"><span class="spb-fl-v" data-mipv></span></div>' +
            '<div class="spb-fl-view"><div class="spb-fl-tile"><img data-t="paint" alt=""><span>Paint</span></div><div class="spb-fl-tile"><img data-t="metal" alt=""><span>R Metal</span></div><div class="spb-fl-tile"><img data-t="rough" alt=""><span>G Rough</span></div></div>' +
            '<div class="spb-fl-meter" data-meter title="Flake signal left at each distance (texel-to-texel spec variation, levels). Dashed line = the owner-fitted flat bar."></div>' +
            '<div class="spb-fl-mlab"><span>Close</span><span>Mip 1</span><span>Mip 2</span><span>Mip 3</span><span>Track</span></div>' +
            '<div class="spb-fl-note" data-status></div>' +
            '</div>' +
            '<div class="spb-ph-foot spb-fl-foot">' +
            '' + /* [SHINE-OFF 2026-10-11] owner: artificial shine never works; Shine Lens button removed */
            '<button type="button" data-act="remove" title="Take the flake off the selected zone (its old finish comes back)">Remove</button>' +
            '<button type="button" data-act="apply" class="spb-ph-primary">Apply To Zone</button></div>';
        doc.body.appendChild(panel);
        wire();
        return panel;
    }
    function wire() {
        panel.addEventListener('click', function (e) {
            var b = e.target.closest && e.target.closest('button'); if (!b) return;
            var lk = b.getAttribute('data-look'), act = b.getAttribute('data-act');
            if (lk) { setLook(lk); return; }
            var tg = b.getAttribute('data-tg'); if (tg) { S.target = tg; saveLocal(); syncFoot(); schedule(false); return; }
            if (act === 'close') close();
            else if (act === 'apply') apply();
            else if (act === 'remove') removeFromZone();
            else if (act === 'shine') shine();
        });
        panel.addEventListener('input', function (e) {
            var t = e.target, k = t.getAttribute('data-k');
            if (k) { S.p[k] = +t.value; S.look = 'custom'; syncVals(); schedule(false); return; }
            if (t.hasAttribute('data-mip')) { S.mip = +t.value | 0; saveLocal(); showMip(); return; }
            var c = t.getAttribute('data-c');
            if (c) { S.p[c + '_rgb'] = hex2rgb(t.value); var on = $('[data-on="' + c + '"]'); if (on) on.checked = true; S.look = 'custom'; schedule(false); }
        });
        panel.addEventListener('change', function (e) {
            var t = e.target;
            if (t.hasAttribute('data-sim')) { S.sim = !!t.checked; schedule(true); return; }
            var on = t.getAttribute('data-on');
            if (on) { S.p[on + '_rgb'] = t.checked ? hex2rgb($('[data-c="' + on + '"]').value) : null; S.look = 'custom'; schedule(false); return; }
            if (t.getAttribute('data-k')) schedule(true);
        });
        panel.addEventListener('keydown', function (e) { if (e.key === 'Escape') { e.stopPropagation(); close(); } else e.stopPropagation(); });
        panel.addEventListener('dblclick', function (e) { if (e.target.closest && e.target.closest('.spb-ph-head') && !e.target.closest('button')) { moved = false; dock(); } });
        panel.addEventListener('pointerdown', function (e) {
            var h = e.target.closest && e.target.closest('.spb-ph-head'); if (!h || e.target.closest('button')) return;
            var r = panel.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
            function mv(ev) { panel.style.left = Math.max(0, Math.min(root.innerWidth - 120, ev.clientX - dx)) + 'px'; panel.style.top = Math.max(0, Math.min(root.innerHeight - 60, ev.clientY - dy)) + 'px'; moved = true; }
            function up() { doc.removeEventListener('pointermove', mv); doc.removeEventListener('pointerup', up); }
            doc.addEventListener('pointermove', mv); doc.addEventListener('pointerup', up);
        });
        root.addEventListener('resize', function () { if (isOpen() && !moved) dock(); });
        try { if (root.__spbPolishH && root.__spbPolishH.onLayout) root.__spbPolishH.onLayout(function () { if (isOpen() && !moved) dock(); }); } catch (e) { warn('onLayout', e); }
    }
    function dock() {
        if (!panel) return;
        var H = root.__spbPolishH;
        if (H && typeof H.applyDock === 'function' && !(H.isOff && H.isOff())) { try { H.applyDock(panel); return; } catch (e) { warn('dock', e); } }
        panel.style.left = '8px'; panel.style.top = '120px'; panel.style.maxHeight = Math.max(260, (root.innerHeight || 800) - 128) + 'px';
    }
    function fmt(k, v) {
        if (k === 'size_cm') { var px = v * carScale(); return v.toFixed(2) + ' cm'; }
        if (k === 'density' || k === 'sparkle' || k === 'flake_mix' || k === 'pearl_mix') return Math.round(v * 100) + '%';
        return String(Math.round(v));
    }
    function syncVals() {
        if (!panel) return;
        Array.prototype.forEach.call(panel.querySelectorAll('[data-k]'), function (i) { var k = i.getAttribute('data-k'); if (document.activeElement !== i) i.value = S.p[k]; var o = $('[data-v="' + k + '"]'); if (o) o.textContent = fmt(k, +S.p[k]); });
        var sz = $('[data-v="size_cm"]'); if (sz) { sz.textContent = (+S.p.size_cm).toFixed(2) + ' cm'; sz.title = (S.p.size_cm * carScale()).toFixed(1) + ' px on this car (' + carScale().toFixed(2) + ' px/cm, ' + S.pxSrc + ')'; }
        ['flake', 'pearl'].forEach(function (c) { var on = $('[data-on="' + c + '"]'), col = $('[data-c="' + c + '"]'), rgb = S.p[c + '_rgb']; if (on) on.checked = !!rgb; if (col && rgb) col.value = rgb2hex(rgb); });
        Array.prototype.forEach.call(panel.querySelectorAll('[data-look]'), function (b) { b.classList.toggle('on', b.getAttribute('data-look') === S.look); });
        var sim = $('[data-sim]'); if (sim) sim.checked = !!S.sim;
        var mp = $('[data-mip]'); if (mp) mp.value = S.mip;
        syncFoot();
    }
    function syncFoot() {
        Array.prototype.forEach.call(panel.querySelectorAll('[data-tg]'), function (b) { var on = b.getAttribute('data-tg') === S.target; b.classList.toggle('on', on); b.setAttribute('aria-checked', on ? 'true' : 'false'); });
        var a = $('[data-act="apply"]'), rm = $('[data-act="remove"]');
        if (a) a.textContent = S.target === 'brush' ? 'Load The Brush' : (S.target === 'layer' ? 'Apply To Layer' : 'Apply To Zone');
        if (rm) rm.hidden = S.target !== 'zone';
    }
    function setLook(id) {
        var l = LOOK_BY[id]; if (!l) return;
        S.look = id; S.p = JSON.parse(JSON.stringify(l.p)); saveLocal(); syncVals(); schedule(true);
    }

    // ------------------------------------------------------------------ preview (server: the same engine code the render runs)
    function schedule(refit) {
        saveLocal();
        if (refit && S.sim) { clearTimeout(fitT); fitT = setTimeout(runFit, 60); return; }
        clearTimeout(pvT); pvT = setTimeout(runPreview, 110);
    }
    function runFit() {
        var sig = fitSig();
        if (!S.sim || (S.fit && S.fitSig === sig)) { runPreview(); return; }
        var t0 = performance.now(), p = params(); p.sim_safe = true;
        api('/api/flake/fit', { params: p }).then(function (r) {
            if (!r || !r.fitted) throw new Error((r && r.error) || 'fit failed');
            S.fit = r; S.fitSig = sig; S.coarse_px = r.coarse_px; S.coarse_mix = r.ok ? r.coarse_mix : 0; saveLocal();
            S.fitMs = Math.round(performance.now() - t0);
            runPreview();
        }).catch(function (e) { warn('fit', e); runPreview(); });
    }
    function fitLine() {
        var el = $('[data-fitline]'); if (!el) return;
        if (!S.sim) { el.textContent = 'Sim-Safe off: the flake is drawn exactly as set.'; return; }
        var f = S.fit;
        if (!f || S.fitSig !== fitSig()) { el.textContent = 'Fitting the coarse band…'; return; }
        if (!f.ok) { el.textContent = 'Sim-Safe could not fit: ' + f.why + '. Make the flake bigger or the sparkle stronger.'; return; }
        el.textContent = f.coarse_mix > 0 ? ('Fitted: coarse ' + f.coarse_px + ' px flake at ' + Math.round(f.coarse_mix * 100) + '% keeps mip 2 at ' + f.S + ' (bar ' + f.bar + '; fine alone ' + f.fine_S + ').') : ('Fitted: ' + f.why + ' (' + f.fine_S + ' ≥ bar ' + f.bar + '), no coarse band needed.');
    }
    function cropFor() {
        var d = dims(), cx = d[0] / 2, cy = d[1] / 2, z = curZone();
        try {
            if (S.target === 'brush' && root.SpbRevSponsor && root.SpbRevSponsor.measure) { var m = root.SpbRevSponsor.measure(); if (m && m.slots && m.slots.hood) { cx = m.slots.hood.cx; cy = m.slots.hood.cy; } }
            else if (z && z.regionMask && z.regionMask.length === d[0] * d[1]) {
                var sx = 0, sy = 0, n = 0, rm = z.regionMask, W = d[0];
                for (var i = 0; i < rm.length; i += 97) if (rm[i]) { sx += i % W; sy += (i / W) | 0; n++; }
                if (n > 20) { cx = sx / n; cy = sy / n; }
            }
        } catch (_) {}
        var w = 256, x = Math.max(0, Math.min(d[0] - w, Math.round(cx - w / 2))), y = Math.max(0, Math.min(d[1] - w, Math.round(cy - w / 2)));
        return [x - (x % 16), y - (y % 16), w, w];
    }
    function paintCrop(cr) {
        try {
            var c = doc.getElementById('paintCanvas'); if (!c) return null;
            var t = doc.createElement('canvas'); t.width = cr[2]; t.height = cr[3];
            t.getContext('2d').drawImage(c, cr[0], cr[1], cr[2], cr[3], 0, 0, cr[2], cr[3]);
            return t.toDataURL('image/png');
        } catch (e) { warn('paint crop', e); return null; }
    }
    function runPreview() {
        if (!isOpen()) return;
        var seq = ++pvSeq, t0 = performance.now(), cr = cropFor(), p = params();
        if (S.sim && !(S.fit && S.fitSig === fitSig())) p.coarse_mix = 0;
        fitLine();
        api('/api/flake/preview', { params: p, crop: cr, paint_png: paintCrop(cr), levels: 4 }).then(function (r) {
            if (seq !== pvSeq) return;
            if (!r || !r.ok) { status((r && r.off) ? 'Flake Studio is switched off on the server.' : 'Preview failed: ' + ((r && r.error) || '?'), true); return; }
            S.last = r; S.lastMs = Math.round(performance.now() - t0);
            showMip(); meter();
        }).catch(function (e) { if (seq === pvSeq) status('Preview failed: ' + (e && e.message), true); });
    }
    function showMip() {
        var r = S.last, k = S.mip | 0;
        var mv = $('[data-mipv]'); if (mv) mv.textContent = k === 0 ? 'Up Close' : (k === 4 ? 'Across Track' : 'Mip ' + k);
        if (!r || !r.mips || !r.mips[k]) return;
        ['paint', 'metal', 'rough'].forEach(function (t) { var im = $('[data-t="' + t + '"]'); if (im) im.src = r.mips[k][t]; });
        Array.prototype.forEach.call(panel.querySelectorAll('.spb-fl-bar'), function (b, i) { b.classList.toggle('sel', i === k); });
    }
    function meter() {
        var r = S.last, el = $('[data-meter]'); if (!r || !el) return;
        var S5 = r.meter.S, bar = r.meter.bar, top = Math.max(bar * 1.6, Math.max.apply(null, S5)) || 1;
        el.innerHTML = S5.map(function (v, i) { return '<div class="spb-fl-bar' + (v >= bar ? ' ok' : '') + (i === (S.mip | 0) ? ' sel' : '') + '" data-i="' + i + '" style="height:' + Math.max(2, Math.round(56 * v / top)) + 'px" title="Mip ' + i + ': ' + v + ' levels, ' + r.meter.survive_pct[i] + '% of up close — reads as ' + r.meter.reads[i] + '"><b>' + r.meter.survive_pct[i] + '%</b></div>'; }).join('') +
            '<div class="spb-fl-line" style="bottom:' + Math.round(56 * bar / top) + 'px"></div>';
        Array.prototype.forEach.call(el.querySelectorAll('.spb-fl-bar'), function (b) { b.addEventListener('click', function () { S.mip = +b.getAttribute('data-i'); saveLocal(); syncVals(); showMip(); }); });
        var px = (S.p.size_cm * carScale()), k2 = r.meter.S[2], gl = r.glitter;
        status('Flake ' + (+S.p.size_cm).toFixed(2) + ' cm = ' + px.toFixed(1) + ' px (' + carScale().toFixed(2) + ' px/cm, ' + S.pxSrc + '). Mip 2: ' + k2 + ' levels, ' + r.meter.survive_pct[2] + '% survives — ' +
            (k2 >= r.meter.bar ? 'reads as flake' : 'goes flat grey') + '. ' + (gl ? 'Flakes this big read as glitter (bar ' + r.big_px + ' px). ' : '') + 'Preview ' + S.lastMs + ' ms.', !!gl || k2 < r.meter.bar);
    }
    function status(t, w) { var el = $('[data-status]'); if (el) { el.textContent = t; el.classList.toggle('spb-fl-warn', !!w); } }

    // ------------------------------------------------------------------ apply
    function zonesArr() { try { return (typeof zones !== 'undefined' && Array.isArray(zones)) ? zones : null; } catch (_) { return null; } }
    function curZone() { var zs = zonesArr(); var i = (typeof selectedZoneIndex !== 'undefined') ? selectedZoneIndex : -1; return zs && zs[i] ? zs[i] : null; }
    function refresh() {
        try { if (typeof root.renderZones === 'function') root.renderZones(); else if (typeof renderZones === 'function') renderZones(); } catch (_) {}
        try { if (typeof root.renderZoneDetail === 'function') root.renderZoneDetail(selectedZoneIndex); } catch (_) {}
        try { if (typeof root.spbKickLivePreview === 'function') root.spbKickLivePreview(); } catch (_) {}
    }
    function ready() {
        if (!S.sim || (S.fit && S.fitSig === fitSig())) return Promise.resolve(true);
        return new Promise(function (res) { var p = params(); p.sim_safe = true; api('/api/flake/fit', { params: p }).then(function (r) { if (r && r.fitted) { S.fit = r; S.fitSig = fitSig(); S.coarse_px = r.coarse_px; S.coarse_mix = r.ok ? r.coarse_mix : 0; saveLocal(); } res(true); }).catch(function () { res(true); }); });
    }
    function apply() {
        if (off()) return Promise.resolve(false);
        return ready().then(function () {
            if (S.target === 'brush') return toBrush();
            if (S.target === 'layer') return toLayer();
            return toZone();
        });
    }
    /** Zone: finish override that keeps the zone's colour (Gloss foundation keeps the paint; the flake owns M/R/CC). One zone undo step. */
    function toZone(z) {
        z = z || curZone();
        if (!z) { toast('Select a zone first, then Apply To Zone.', 'warn'); return false; }
        try { if (typeof pushZoneUndo === 'function') pushZoneUndo('Flake Studio: ' + lookName(S.look)); } catch (e) { warn('undo', e); }
        if (!z.spbFlake) z.spbFlakePrev = { base: z.base == null ? null : z.base, finish: z.finish == null ? null : z.finish };
        try { if (typeof _spbApplyPickedBaseToZone === 'function') _spbApplyPickedBaseToZone(z, 'gloss'); else { z.base = 'gloss'; z.finish = null; } } catch (e) { z.base = 'gloss'; z.finish = null; }
        z.spbFlake = params();
        refresh();
        toast(lookName(S.look) + ' on ' + (z.name || 'the zone') + ': the zone keeps its colour, the flake sets metal, roughness and clearcoat.', 'success');
        return true;
    }
    function removeFromZone(z) {
        z = z || curZone();
        if (!z || !z.spbFlake) { toast('The selected zone has no Flake Studio flake.', 'info'); return false; }
        try { if (typeof pushZoneUndo === 'function') pushZoneUndo('Remove Flake Studio flake'); } catch (_) {}
        var pv = z.spbFlakePrev; delete z.spbFlake; delete z.spbFlakePrev;
        if (pv) { if (pv.finish) { z.finish = pv.finish; z.base = pv.base; } else { try { if (typeof _spbApplyPickedBaseToZone === 'function') _spbApplyPickedBaseToZone(z, pv.base); else z.base = pv.base; } catch (_) { z.base = pv.base; } } }
        refresh(); return true;
    }
    /** Material Brush: a Brush Studio coat (Gloss + the flake) - strokes cut one car-space flake texture, paint + spec. */
    function toBrush(mode) {
        var U = root.SPBRevMaterialUI, M = root.SPBRevMaterial;
        if (!U || !U.settings || !M || typeof M.normParams !== 'function') { toast('The Material Brush is not available.', 'warn'); return false; }
        if (U.studioOn && !U.studioOn()) { toast('The Material Brush studio is switched off.', 'warn'); return false; }
        var T = U.settings, md = mode || S.brushMode || (T.mode === 'spec' ? 'spec' : 'both');
        T.finishId = 'gloss';
        var np = M.normParams(T.params); np.flake = params(); T.params = np;
        try { if (U.setStudioMode) U.setStudioMode(md); else T.mode = md; } catch (_) { T.mode = md; }   // setStudioMode saves the brush settings
        try { if (typeof root.setCanvasMode === 'function') root.setCanvasMode('rev-material'); } catch (e) { warn('mode', e); }
        try { if (U.buildBand) U.buildBand(); } catch (_) {}
        toast('Material Brush loaded with ' + lookName(S.look) + ' (' + (+S.p.size_cm).toFixed(2) + ' cm flake). Paint it on.', 'success');
        return true;
    }
    /** Layer: the layer's material becomes a Flake Studio coat (Layer Materials' own finish coat path, masked by the layer's alpha). */
    function selLayerIds() {
        try { var sel = root._selectedLayerIds; if (sel && typeof sel.has === 'function' && sel.size > 1) return Array.from(sel).map(String); } catch (_) {}
        try { if (typeof _selectedLayerId !== 'undefined' && _selectedLayerId != null) return [String(_selectedLayerId)]; } catch (_) {}
        return [];
    }
    function toLayer(ids) {
        var LM = root.SPBRevLayerMat;
        if (!LM || typeof LM.assign !== 'function' || (LM.off && LM.off())) { toast('Layer Materials are switched off; use a zone or the Material Brush.', 'warn'); return false; }
        ids = ids || selLayerIds();
        if (!ids.length) { toast('Select a layer first (sponsor, number, logo), then Apply To Layer.', 'warn'); return false; }
        // the layer's material = a Gloss coat carrying the flake (its paint = the art underneath, so the art keeps its colour)
        var r = LM.assign(ids, { finishId: 'gloss', flake: params() }, { label: 'Flake Studio: ' + lookName(S.look) + ' on layer' });
        if (r && r.ok) toast(lookName(S.look) + ' on ' + ids.length + ' layer' + (ids.length > 1 ? 's' : '') + ': the flake follows the art.', 'success');
        else toast('Could not set the layer material (' + ((r && r.why) || '?') + ').', 'warn');
        return !!(r && r.ok);
    }
    function shine() {
        var L = root.SPBRevLens;
        try { if (L && L.setMode && !L.off) { L.setMode(L.getMode && L.getMode() !== 'off' ? 'off' : 'full'); return; } } catch (_) {}
        toast('Shine Lens lives on the Live Preview: switch to Split or Preview to use it.', 'info');
    }

    // ------------------------------------------------------------------ open / close / menu
    function isOpen() { return !!(panel && panel.style.display !== 'none'); }
    function open(opts) {
        if (off()) return false;
        build();
        if (opts && opts.target) S.target = opts.target;
        S.brushMode = (opts && opts.brushMode) || null;
        // reopen on something that already carries flake -> start from that recipe
        try {
            var have = null;
            if (S.target === 'brush') { var U = root.SPBRevMaterialUI; have = U && U.settings && U.settings.params && U.settings.params.flake; }
            else if (S.target === 'zone') { var z0 = curZone(); have = z0 && z0.spbFlake; }
            if (have) loadFrom(have);
        } catch (_) {}
        panel.style.display = ''; panel.classList.add('spb-ph-front'); if (!moved) dock();
        carScale(); syncVals(); schedule(true);
        return true;
    }
    function close() { if (panel) panel.style.display = 'none'; }
    function addMenuItem() {
        if (off()) return false;
        var pop = doc.querySelector('#spbRevMatMenu .spb-tb-pop'); if (!pop) return false;
        if (pop.querySelector('[data-flake]')) return true;
        var b = doc.createElement('button'); b.type = 'button'; b.className = 'vtool-btn'; b.setAttribute('data-flake', 'open');
        b.title = 'Flake Studio: metallic flake and pearl sized in real centimetres, checked at iRacing’s mip distances, for a zone, the Material Brush or a layer';
        b.innerHTML = '<span class="spb-mi-ico">' + svg('flake') + '</span> Flake Studio…';
        pop.appendChild(b);
        b.addEventListener('click', function (e) { e.preventDefault(); var m = pop.closest('details'); if (m) m.removeAttribute('open'); open(); });
        return true;
    }
    function boot(n) {
        if (off()) return;
        var m = addMenuItem();
        if (!m && (n || 0) < 80) setTimeout(function () { boot((n || 0) + 1); }, 500);
        else if (m) setInterval(function () { if (!off()) addMenuItem(); }, 3000);
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', function () { boot(0); }); else boot(0);

    root.SpbFlakeStudio = { version: VER, off: off, LOOKS: LOOKS, open: open, close: close, isOpen: isOpen, params: params, setLook: setLook, carScale: carScale, toZone: toZone, removeFromZone: removeFromZone,
        toBrush: toBrush, toLayer: toLayer, apply: apply, ready: ready, state: S, panel: function () { return panel; }, preview: runPreview, fit: runFit, dock: dock, set: function (o) { Object.keys(o || {}).forEach(function (k) { if (k in S.p) S.p[k] = o[k]; else S[k] = o[k]; }); S.look = o.look || S.look; saveLocal(); if (panel) syncVals(); } };
})(typeof window !== 'undefined' ? window : globalThis);
