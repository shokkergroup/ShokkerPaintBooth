/* [SPB-TFX2 2026-10-09 TA-009] Per-tool brush HARDNESS memory + soft defaults for the retouch tools.
 *
 * Audit TA-009 (P3): the Size/Hardness/Opacity/Flow sliders are ONE shared set, so Smudge / Blur / Heal inherited the
 * Brush's hardness (default 100) and drew scalloped crescents at every dab edge (hardness 0 is clean). Photoshop / Affinity
 * start every retouch tool soft and remember each tool's own hardness.
 *
 * How (kept out of setCanvasMode on purpose - that function belongs to the TOOLS-FIX-1 lane): this module wraps
 * window.setCanvasMode from the outside. On leaving a paint-family tool it remembers that tool's hardness; on entering one it
 * restores the remembered value, or seeds a soft default for the retouch tools the first time. Brush / Eraser / Pencil etc.
 * are never given a default (only their own remembered value comes back), so "switching tools never changes the painter's
 * numbers" holds for hardness. Persisted in localStorage (spb_tfx2_tool_hardness).
 *
 * Kill switch: window.SPB_TFX2_OFF = true (or localStorage SPB_TFX2_OFF = '1') -> wrapper is a pass-through.
 *
 * [SPB-TFX1 2026-10-09 TA-007] ABSORBED: this is now THE single place for per-tool painter options (TOOLS-FIX-1 TA-007). The map is
 * {size, hardness, opacity, flow, spacing} per paint-family tool: saved on every slider input and on leaving the tool, restored on
 * entering it, persisted in localStorage 'spb_tfx1_tool_opts' (migrates the hardness memory above and the old global brush prefs of
 * js/spb-session-prefs.js, which no longer stores brush size / hardness / opacity). First visit to a tool with no memory: its seed
 * (eraser hard 100, pencil size 1 hard 100, smudge / blur / sharpen / dodge / burn soft, heal 25) else the factory numbers
 * (size 20, hardness 100, opacity 100, flow 100, spacing 25), so one tool's numbers never leak into another. Kill switch
 * window.SPB_TFX1_OFF = true (or localStorage SPB_TFX1_OFF = '1') -> only the hardness memory above, as before.
 */
(function () {
    'use strict';
    try { if (window.SPB_TFX2_OFF !== true && localStorage.getItem('SPB_TFX2_OFF') === '1') window.SPB_TFX2_OFF = true; } catch (_e) { }
    try { if (window.SPB_TFX2_OFF) document.documentElement.setAttribute('data-spb-tfx2-off', ''); } catch (_e) { } // CSS kill-switch hook (layers-panel bottom padding)

    const FAMILY = ['brush', 'erase', 'clone', 'heal', 'colorbrush', 'recolor', 'smudge', 'history-brush', 'dodge', 'burn',
        'blur-brush', 'sharpen-brush', 'pencil'];
    // first-visit defaults (hardness %): retouch tools start soft (Photoshop smudge/blur/sharpen/dodge/burn), heal keeps a little body.
    const SEED = { smudge: 0, 'blur-brush': 0, 'sharpen-brush': 0, dodge: 0, burn: 0, heal: 25 };
    const KEY = 'spb_tfx2_tool_hardness';
    let mem = {};
    try { mem = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (_e) { mem = {}; }

    function slider() { return document.getElementById('brushHardness'); }
    function save() { try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch (_e) { } }

    // [SPB-TFX1 2026-10-09 TA-007] full per-tool options map
    const OPT_IDS = { size: 'brushSize', hardness: 'brushHardness', opacity: 'brushOpacity', flow: 'brushFlow', spacing: 'brushSpacing' };
    const OPT_KEYS = Object.keys(OPT_IDS);
    const FACTORY = { size: 20, hardness: 100, opacity: 100, flow: 100, spacing: 25 };
    const SEED_ALL = { erase: { hardness: 100 }, pencil: { size: 1, hardness: 100 }, smudge: { hardness: 0 }, 'blur-brush': { hardness: 0 },
        'sharpen-brush': { hardness: 0 }, dodge: { hardness: 0 }, burn: { hardness: 0 }, heal: { hardness: 25 } };
    const KEY2 = 'spb_tfx1_tool_opts';
    let all = null;
    try { all = JSON.parse(localStorage.getItem(KEY2) || 'null'); } catch (_e) { all = null; }
    if (!all || typeof all !== 'object') {
        all = {};
        Object.keys(mem).forEach(function (t) { if (isFinite(mem[t])) all[t] = { hardness: +mem[t] }; });   // FIX-2 hardness memory
        try {   // the old global brush numbers (js/spb-session-prefs.js) become the Brush's own memory
            const p = JSON.parse(localStorage.getItem('spb_tool_prefs_v1') || 'null');
            if (p) {
                const b = all.brush = all.brush || {};
                [['brushSize', 'size'], ['brushHardness', 'hardness'], ['brushOpacity', 'opacity']].forEach(function (m) {
                    const n = p[m[0]] && p[m[0]].v != null ? parseInt(p[m[0]].v, 10) : NaN;
                    if (isFinite(n) && b[m[1]] == null) b[m[1]] = n;
                });
            }
        } catch (_e) { }
    }
    function tfx1On() { return !window.SPB_TFX1_OFF; }
    function readOpts() {
        const o = {};
        OPT_KEYS.forEach(function (k) { const e = document.getElementById(OPT_IDS[k]); const n = e ? parseInt(e.value, 10) : NaN; if (isFinite(n)) o[k] = n; });
        return o;
    }
    function setSliderById(id, v) {
        const el = document.getElementById(id);
        if (!el || !isFinite(v)) return;
        v = Math.max(+el.min || 0, Math.min(+el.max || 100, Math.round(v)));
        if (String(el.value) === String(v)) return;
        el.value = v;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function saveAll() { try { localStorage.setItem(KEY2, JSON.stringify(all)); } catch (_e) { } }
    let _saveT = 0;
    function saveSoon() { clearTimeout(_saveT); _saveT = setTimeout(saveAll, 250); }
    function restoreFor(mode) {
        const rec = all[mode], seed = SEED_ALL[mode];
        OPT_KEYS.forEach(function (k) {
            const v = (rec && rec[k] != null) ? rec[k] : ((seed && seed[k] != null) ? seed[k] : FACTORY[k]);
            setSliderById(OPT_IDS[k], v);
        });
    }
    // every slider edit lands in the ACTIVE tool's entry (the exit snapshot below also covers programmatic changes)
    document.addEventListener('input', function (e) {
        if (window.SPB_TFX2_OFF || !tfx1On()) return;
        const id = e.target && e.target.id; if (!id) return;
        const k = OPT_KEYS.filter(function (x) { return OPT_IDS[x] === id; })[0];
        const m = window.canvasMode;
        if (!k || FAMILY.indexOf(m) < 0) return;
        const n = parseInt(e.target.value, 10); if (!isFinite(n)) return;
        (all[m] = all[m] || {})[k] = n; saveSoon();
    }, true);
    // boot: a family tool already active when the page loads gets its remembered numbers too
    window.addEventListener('load', function () { setTimeout(function () { try { if (!window.SPB_TFX2_OFF && tfx1On() && FAMILY.indexOf(window.canvasMode) >= 0) restoreFor(window.canvasMode); } catch (_e) { } }, 1500); });
    function setHardness(v) {
        const el = slider();
        if (!el || !isFinite(v)) return;
        v = Math.max(+el.min || 0, Math.min(+el.max || 100, Math.round(v)));
        if (String(el.value) === String(v)) return;
        el.value = v;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // [SPB-TFX2 2026-10-09 TA-002] The Size slider's VALUE is the brush RADIUS (presets, AI/MCP and every reader depend on that), but Photoshop /
    // Affinity users read a DIAMETER. Only the displayed number converts (value x 2); this keeps the label right after programmatic changes
    // (presets, tool switches) that set the slider without firing its inline oninput.
    function syncSizeLabel() {
        const s = document.getElementById('brushSize'), l = document.getElementById('brushSizeVal');
        if (!s || !l) return;
        const v = parseInt(s.value, 10) || 0, want = String(window.SPB_TFX2_OFF ? v : v * 2);
        if (l.textContent !== want) l.textContent = want;
        const tip = window.SPB_TFX2_OFF ? ('Brush / eraser size: ' + v + 'px (range 1-300). Use [ and ] keys to decrease/increase.')
            : ('Brush / eraser diameter: ' + (v * 2) + 'px (range 2-600). Use [ and ] keys to decrease/increase.');
        if (s.title !== tip) s.title = tip;
    }

    // [SPB-TFX2 2026-10-09 TA-019] The tool-name hint (#platinumToolFlash, fixed at top:11%, z-index 100000, ~4.5 s) sat ON TOP of any menu
    // opened right after a tool switch and hid its first entries (SELECT menu after WAND: hint covered Select All Color / Color Range /
    // Select Object). The menu panel itself is already opaque (UI-POLISH-B). The hint now hides the moment a toolbar menu opens, and is
    // not shown while one is open. Before -> after: hint covers menu at 300 ms = true -> false (t_hint.py).
    function menuOpen() { return !!document.querySelector('details.spb-tb-menu[open]'); }
    function hideHint() {
        const h = document.getElementById('platinumToolFlash');
        if (h && h.style.opacity !== '0') { clearTimeout(h._t); h.style.opacity = '0'; }
    }
    document.addEventListener('toggle', function (e) {
        if (window.SPB_TFX2_OFF) return;
        const d = e.target;
        if (d && d.classList && d.classList.contains('spb-tb-menu') && d.open) hideHint();
    }, true);

    function install() {
        if (typeof window.setCanvasMode !== 'function' || window._spbToolDefaultsWrapped) return false;
        window._spbToolDefaultsWrapped = true;
        const prevFn = window.setCanvasMode;
        window.setCanvasMode = function (mode) {
            if (window.SPB_TFX2_OFF) { const r0 = prevFn.apply(this, arguments); try { syncSizeLabel(); } catch (_e) { } return r0; }
            const from = window.canvasMode;
            const el = slider();
            const before = el ? parseInt(el.value, 10) : NaN;
            const full = tfx1On(), snap = full ? readOpts() : null;   // [SPB-TFX1 2026-10-09 TA-007]
            const r = prevFn.apply(this, arguments);
            try { if (menuOpen()) hideHint(); } catch (_e) { }
            try {
                if (r !== false && window.canvasMode === mode && mode !== from) {
                    if (full) {   // [SPB-TFX1 2026-10-09 TA-007] whole per-tool map
                        if (from && FAMILY.indexOf(from) >= 0) { all[from] = Object.assign(all[from] || {}, snap); saveSoon(); }
                        if (FAMILY.indexOf(mode) >= 0) restoreFor(mode);
                    } else {
                        if (from && FAMILY.indexOf(from) >= 0 && isFinite(before)) { mem[from] = before; save(); }
                        if (FAMILY.indexOf(mode) >= 0) {
                            const v = (mem[mode] != null) ? mem[mode] : SEED[mode];
                            if (v != null) setHardness(v);
                        }
                    }
                }
            } catch (_e) { }
            try { syncSizeLabel(); } catch (_e) { }
            return r;
        };
        return true;
    }
    if (!install()) window.addEventListener('DOMContentLoaded', install);
    window.addEventListener('DOMContentLoaded', function () { try { syncSizeLabel(); } catch (_e) { } });
    window.addEventListener('load', function () { try { syncSizeLabel(); } catch (_e) { } });
    document.addEventListener('input', function (e) { if (e.target && e.target.id === 'brushSize') { try { syncSizeLabel(); } catch (_e) { } } }, true);
    window.SPBToolDefaults = { syncSizeLabel: syncSizeLabel, mem: function () { return Object.assign({}, mem); }, seed: SEED,
        opts: function () { return JSON.parse(JSON.stringify(all)); }, restoreFor: restoreFor, FAMILY: FAMILY,
        reset: function () { all = {}; try { localStorage.removeItem(KEY2); } catch (_e) { } } };   // [SPB-TFX1 2026-10-09 TA-007]
})();
