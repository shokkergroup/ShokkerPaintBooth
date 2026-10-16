/* ============================================================================
 * SPB PC COLOR RANGE  (lane PORT-W4, 2026-10-09)
 *
 * Algorithm ported from PhotoCraft crates/algo/src/selection.rs
 * (LabRange, lab_range_coverage, quantize_lab8, color_range_lab) and the
 * sampling logic of crates/engine/src/selection_cmds.rs (ColorRangeSamples:
 * eyedropper "+" grows the Lab box, "-" reshapes it, click order, Localized
 * Color Clusters) and crates/ui-egui/src/color_range_ui.rs (dialog controls).
 * (c) 2026 ArtCraft Team and the PhotoCraft contributors, MIT OR Apache-2.0
 * (MIT elected) - see THIRD_PARTY_NOTICES.md.
 * Modified: rewritten in JavaScript for SPB's 8-bit paint buffer. Colours are
 * compared on the 8-bit Lab grid (CIE Lab, D50 PCS, sRGB source) exactly as
 * PhotoCraft does for 8-bit documents: per axis distance outside the sample
 * box, a/b weighted x3, quadratic B-spline falloff of width fuzziness*256/255.
 * Lab is held as Uint8 L (L*2.55) and Int8 a,b, so a 2048x2048 Fuzziness drag
 * is one cheap pass over 4M pixels.
 *
 * Owner verdict 2026-10-09: "our tools basically SUCK". Select All Color is a
 * plain RGB-distance flood; Color Range gives Photoshop's Lab fuzziness with
 * additive/subtractive eyedroppers, Localized clusters and Invert.
 *
 * Disable with  window.SPB_PC_W4_OFF = true  (menu entry hides).
 * ==========================================================================*/
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPcColorRange = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    // ---------------------------------------------------------------- colour
    // sRGB (D65, gamma) -> XYZ D50 (Bradford-adapted, Lindbloom) -> CIE Lab with the D50 white.
    const LIN = new Float32Array(256);
    for (let i = 0; i < 256; i++) {
        const c = i / 255;
        LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }
    const XN = 0.9642, YN = 1.0, ZN = 0.8249;     // D50 PCS white as used by ICC Lab profiles
    const EPS = 216 / 24389, KAP = 24389 / 27;
    function f(t) { return t > EPS ? Math.cbrt(t) : (KAP * t + 16) / 116; }

    // Returns [L(0..100), a, b] floats for an sRGB triple (0..255).
    function rgbToLab(r, g, b) {
        const lr = LIN[r], lg = LIN[g], lb = LIN[b];
        const X = 0.4360747 * lr + 0.3850649 * lg + 0.1430804 * lb;
        const Y = 0.2225045 * lr + 0.7168786 * lg + 0.0606169 * lb;
        const Z = 0.0139322 * lr + 0.0971045 * lg + 0.7141733 * lb;
        const fx = f(X / XN), fy = f(Y / YN), fz = f(Z / ZN);
        return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
    }
    // 8-bit grid: L in 1/2.55 steps (stored as L*2.55 rounded), a/b whole units.
    function quant(lab) { return [Math.round(lab[0] * 2.55), Math.round(lab[1]), Math.round(lab[2])]; }

    // Whole image -> { Lq:Uint8Array, aq:Int8Array, bq:Int8Array } (alpha is read from rgba).
    function labGrid(rgba, w, h) {
        const n = w * h;
        const Lq = new Uint8Array(n), aq = new Int8Array(n), bq = new Int8Array(n);
        // tiny run cache: neighbouring pixels are often the same colour
        let pr = -1, pg = -1, pb = -1, cl = 0, ca = 0, cb = 0;
        for (let i = 0, o = 0; i < n; i++, o += 4) {
            const r = rgba[o], g = rgba[o + 1], b = rgba[o + 2];
            if (r !== pr || g !== pg || b !== pb) {
                const q = quant(rgbToLab(r, g, b));
                cl = q[0] < 0 ? 0 : (q[0] > 255 ? 255 : q[0]);
                ca = q[1] < -128 ? -128 : (q[1] > 127 ? 127 : q[1]);
                cb = q[2] < -128 ? -128 : (q[2] > 127 ? 127 : q[2]);
                pr = r; pg = g; pb = b;
            }
            Lq[i] = cl; aq[i] = ca; bq[i] = cb;
        }
        return { Lq: Lq, aq: aq, bq: bq, w: w, h: h };
    }

    // ------------------------------------------------------------- Lab range
    // Box in (Lq, a, b) 8-bit units. One sample is a box of size zero.
    function rangePoint(q) { return { lo: q.slice(), hi: q.slice() }; }
    function rangeGrow(r, q) {
        return { lo: [0, 1, 2].map(function (k) { return Math.min(r.lo[k], q[k]); }),
                 hi: [0, 1, 2].map(function (k) { return Math.max(r.hi[k], q[k]); }) };
    }
    // "Subtract from Sample" the way Photoshop does it (see PhotoCraft LabRange::subtract).
    // The L axis width is `fuzziness` Lq units (PC: fuzziness/2.55 L units); a/b: a third of fuzziness*256/255.
    function rangeSubtract(r0, q, fuzziness) {
        const fz = Number.isFinite(fuzziness) ? Math.max(0, fuzziness) : 0;
        const r = { lo: r0.lo.slice(), hi: r0.hi.slice() };
        for (let k = 0; k < 3; k++) {
            const m = q[k];
            const w = k === 0 ? fz : fz * 256 / 255 / 3;
            const lo = r.lo[k], hi = r.hi[k];
            if (m > lo && m < hi) {
                if (m - lo < hi - m) r.lo[k] = m; else r.hi[k] = m;
                continue;
            }
            const qq = w / 5;
            if (qq <= 0) continue;
            const d = m <= lo ? lo - m : m - hi;
            const n = Math.floor(d / qq) + 1;
            if (n > 5) continue;
            if (m <= lo) r.lo[k] = Math.min(m + n * qq, hi); else r.hi[k] = Math.max(m - n * qq, lo);
        }
        return r;
    }

    // Build the sample box from an ordered list of operations: [{op:'+'|'-', q:[Lq,a,b]}].
    function rangeFromOps(ops, fuzziness) {
        let range = null;
        for (let i = 0; i < ops.length; i++) {
            const o = ops[i];
            if (o.op === '+') range = range ? rangeGrow(range, o.q) : rangePoint(o.q);
            else if (range) range = rangeSubtract(range, o.q, fuzziness);
        }
        return range;
    }

    // Coverage (0..255, PC's floor(v*256) clamped) of one Lab pixel in the box at fuzziness.
    function coverageOne(Lq, a, b, range, fuzziness, fz) {
        const lo = range.lo, hi = range.hi;
        const dL = Math.max(lo[0] - Lq, Lq - hi[0], 0);
        if (!(fuzziness > 0)) {
            const da0 = Math.max(lo[1] - a, a - hi[1], 0), db0 = Math.max(lo[2] - b, b - hi[2], 0);
            return Math.max(dL, da0, db0) < 0.5 ? 255 : 0;
        }
        let da, db;
        if (a > hi[1]) da = a - hi[1] + 0.5; else if (a < lo[1]) { da = lo[1] - a - 0.5; if (da < 0) da = 0; } else da = 0;
        if (b > hi[2]) db = b - hi[2] + 0.5; else if (b < lo[2]) { db = lo[2] - b - 0.5; if (db < 0) db = 0; } else db = 0;
        const t = Math.max(dL, 3 * da, 3 * db) / fz;
        let v;
        if (t <= 0.5) v = 1 - 2 * t * t; else if (t < 1) v = 2 * (1 - t) * (1 - t); else v = 0;
        const q = Math.floor(v * 256);
        return q > 255 ? 255 : (q < 0 ? 0 : q);
    }

    // Coverage mask over the whole image. opts: {fuzziness, invert, localized:{radius, points:[[x,y]..]}}
    // rgba is read for alpha only (alpha 0 -> 0 coverage, as PC).
    function coverage(grid, rgba, range, opts) {
        const w = grid.w, h = grid.h, n = w * h;
        const out = new Uint8Array(n);
        if (!range) return out;
        const fuzz = opts.fuzziness, fz = fuzz * 256 / 255;
        const Lq = grid.Lq, aq = grid.aq, bq = grid.bq;
        const loc = opts.localized && opts.localized.points && opts.localized.points.length ? opts.localized : null;
        let nearRow = null;
        for (let y = 0; y < h; y++) {
            if (loc) {
                // Per-row precompute of the squared dy term for each sample.
                nearRow = loc.points.map(function (p) { return (y - p[1]) * (y - p[1]); });
            }
            const row = y * w;
            for (let x = 0; x < w; x++) {
                const i = row + x;
                if (rgba && rgba[i * 4 + 3] === 0) continue;
                let k = coverageOne(Lq[i], aq[i], bq[i], range, fuzz, fz);
                if (k > 0 && loc) {
                    const rad = Math.max(loc.radius, 1);
                    let near = 0;
                    for (let s = 0; s < loc.points.length; s++) {
                        const dx = x - loc.points[s][0];
                        const v = 1 - Math.sqrt(dx * dx + nearRow[s]) / rad;
                        if (v > near) near = v;
                    }
                    k = near <= 0 ? 0 : k * (near > 1 ? 1 : near);
                }
                out[i] = Math.round(k);
            }
        }
        if (opts.invert) for (let i = 0; i < n; i++) out[i] = 255 - out[i];
        return out;
    }

    // Convenience for tests / headless: sample colours at points with ordered +/- ops.
    // samples: [{op:'+'|'-', x, y}] in the click order.
    function select(rgba, w, h, samples, opts, gridIn) {
        const grid = gridIn || labGrid(rgba, w, h);
        const fuzz = opts.fuzziness;
        const ops = samples.map(function (s) {
            const o = (s.y * w + s.x) * 4;
            return { op: s.op, q: quant(rgbToLab(rgba[o], rgba[o + 1], rgba[o + 2])) };
        });
        const range = rangeFromOps(ops, fuzz);
        const pts = samples.filter(function (s) { return s.op === '+'; }).map(function (s) { return [s.x, s.y]; });
        const loc = opts.localized ? { radius: (opts.range == null ? 100 : opts.range) / 100 * Math.max(w, h), points: pts } : null;
        return coverage(grid, rgba, range, { fuzziness: fuzz, invert: !!opts.invert, localized: loc });
    }

    // ---------------------------------------------------------------- dialog
    const dlg = { el: null, state: null, over: null, raf: 0, host: null };

    function injectStyles() {
        if (typeof document === 'undefined' || document.getElementById('spbCrStyle')) return;
        const st = document.createElement('style');
        st.id = 'spbCrStyle';
        st.textContent = [
            '#spbColorRangeDlg{position:fixed;top:92px;right:18px;z-index:99990;width:272px;background:var(--bg-panel,#161b24);color:var(--text,#dbe3ef);',
            'border:1px solid var(--border,#34404f);border-radius:6px;box-shadow:0 8px 28px rgba(0,0,0,.55);font-size:11px;padding:10px 12px 10px;}',
            '#spbColorRangeDlg h4{margin:0 0 8px;font-size:12px;letter-spacing:.04em;color:var(--accent-gold,#e8b84a);}',
            '#spbColorRangeDlg .cr-row{display:flex;align-items:center;gap:6px;margin:6px 0;}',
            '#spbColorRangeDlg .cr-row label{white-space:nowrap;color:var(--text-dim,#9aa7b8);}',
            '#spbColorRangeDlg input[type=range]{flex:1;min-width:0;}',
            '#spbColorRangeDlg input[type=number]{width:44px;font-size:10px;padding:2px;}',
            '#spbColorRangeDlg .cr-btn{font-size:11px;padding:3px 9px;cursor:pointer;border:1px solid var(--border,#34404f);background:var(--bg-input,#1d2430);color:inherit;border-radius:4px;}',
            '#spbColorRangeDlg .cr-btn.on{border-color:var(--accent-gold,#e8b84a);color:var(--accent-gold,#e8b84a);}',
            '#spbColorRangeDlg .cr-hint{color:var(--text-dim,#9aa7b8);font-size:10px;line-height:1.35;margin-top:4px;}',
            // [SPB-TFX2 2026-10-09 TA-020] title bar = drag handle (grab it to move the panel off whatever it covers) + close button.
            '#spbColorRangeDlg h4.cr-title{display:flex;align-items:center;justify-content:space-between;margin:-10px -12px 8px;padding:7px 8px 7px 12px;cursor:move;user-select:none;touch-action:none;',
            'background:rgba(255,255,255,.05);border-bottom:1px solid var(--border,#34404f);border-radius:6px 6px 0 0;}',
            '#spbColorRangeDlg .cr-x{cursor:pointer;border:0;background:transparent;color:var(--text-dim,#9aa7b8);font-size:15px;line-height:1;padding:0 4px;border-radius:3px;}',
            '#spbColorRangeDlg .cr-x:hover{color:var(--text,#dbe3ef);background:rgba(255,255,255,.1);}',
        ].join('');
        document.head.appendChild(st);
    }

    function ensureOverlay() {
        const rc = document.getElementById('regionCanvas');
        const pc = document.getElementById('paintCanvas');
        if (!rc || !pc) return null;
        let ov = dlg.over;
        if (!ov || !ov.parentNode) {
            ov = document.createElement('canvas');
            ov.id = 'spbColorRangeOverlay';
            ov.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:3;';
            rc.parentNode.insertBefore(ov, rc.nextSibling);
            dlg.over = ov;
        }
        if (ov.width !== pc.width) ov.width = pc.width;
        if (ov.height !== pc.height) ov.height = pc.height;
        ov.style.width = rc.style.width || pc.style.width || (rc.offsetWidth + 'px');
        ov.style.height = rc.style.height || pc.style.height || (rc.offsetHeight + 'px');
        return ov;
    }

    function drawPreview() {
        const S = dlg.state;
        const ov = ensureOverlay();
        if (!ov || !S) return;
        const ctx = ov.getContext('2d');
        if (!S.mask) { ctx.clearRect(0, 0, ov.width, ov.height); return; }
        const img = ctx.createImageData(ov.width, ov.height);
        const d = img.data, m = S.mask, n = m.length;
        if (S.previewMode === 'mask') { // white = selected on black
            for (let i = 0, o = 0; i < n; i++, o += 4) { const v = m[i]; d[o] = v; d[o + 1] = v; d[o + 2] = v; d[o + 3] = 255; }
        } else { // red tint where selected
            for (let i = 0, o = 0; i < n; i++, o += 4) {
                const v = m[i];
                if (v) { d[o] = 255; d[o + 1] = 40; d[o + 2] = 70; d[o + 3] = v * 0.62; }
            }
        }
        ctx.putImageData(img, 0, 0);
    }

    function recompute() {
        const S = dlg.state;
        if (!S) return;
        const t0 = performance.now();
        const range = rangeFromOps(S.ops, S.fuzziness);
        const pts = S.ops.filter(function (o) { return o.op === '+'; }).map(function (o) { return o.at; });
        const loc = S.localized ? { radius: S.range / 100 * Math.max(S.grid.w, S.grid.h), points: pts } : null;
        S.mask = range ? coverage(S.grid, S.rgba, range, { fuzziness: S.fuzziness, invert: S.invert, localized: loc }) : null;
        S.computeMs = performance.now() - t0;
        let c = 0;
        if (S.mask) for (let i = 0; i < S.mask.length; i++) if (S.mask[i] > 127) c++;
        const info = document.getElementById('spbCrInfo');
        if (info) info.textContent = S.mask ? (c.toLocaleString() + ' px selected - ' + S.computeMs.toFixed(0) + ' ms') : 'Click the canvas to sample a colour.';
        drawPreview();
    }
    function schedule() {
        if (dlg.raf) return;
        dlg.raf = requestAnimationFrame(function () { dlg.raf = 0; recompute(); });
    }

    function onCanvasDown(e) {
        const S = dlg.state;
        if (!S || e.button !== 0 || !e.target || e.target.id !== 'paintCanvas') return;
        const pos = dlg.host.pixelAt(e);
        if (!pos) return;
        e.stopImmediatePropagation(); e.preventDefault();
        const o = (pos.y * S.grid.w + pos.x) * 4;
        const q = quant(rgbToLab(S.rgba[o], S.rgba[o + 1], S.rgba[o + 2]));
        let op = S.tool;
        if (e.shiftKey) op = '+'; else if (e.altKey) op = '-';
        if (op === 's') { S.ops = [{ op: '+', q: q, at: [pos.x, pos.y] }]; }
        else S.ops.push({ op: op, q: q, at: [pos.x, pos.y] });
        recompute();
    }

    function onKey(e) {
        if (e.key === 'Escape') { close(false); e.stopPropagation(); }
        else if (e.key === 'Enter' && !(e.target && /^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(e.target.tagName))) { close(true); e.stopPropagation(); }
    }

    function setTool(t) {
        if (!dlg.state) return;
        dlg.state.tool = t;
        ['s', '+', '-'].forEach(function (k) {
            const b = document.getElementById('spbCrTool' + (k === 's' ? 'S' : (k === '+' ? 'P' : 'M')));
            if (b) b.classList.toggle('on', k === t);
        });
    }

    function close(applyIt) {
        const S = dlg.state;
        if (!S) return false;
        window.removeEventListener('mousedown', onCanvasDown, true);
        if (dlg.raf) { cancelAnimationFrame(dlg.raf); dlg.raf = 0; }
        let ok = false;
        const mask = S.mask, mode = S.mode;
        document.removeEventListener('keydown', onKey, true);
        dlg.state = null;
        if (dlg.el && dlg.el.parentNode) dlg.el.parentNode.removeChild(dlg.el);
        dlg.el = null;
        if (dlg.over) { const c = dlg.over.getContext('2d'); c.clearRect(0, 0, dlg.over.width, dlg.over.height); }
        if (applyIt && mask) ok = dlg.host.commit(mask, mode);
        else if (applyIt) dlg.host.toast('Color Range: sample a colour first');
        return ok;
    }

    // [SPB-TFX2 2026-10-09 TA-020] The panel was position:fixed at top:92px/right:18px, i.e. ON the toolbar rows at 1100-1920 px wide (it hid
    // IMPORT RECIPE). It now opens inside the top-right corner of the canvas pane (below every toolbar row), remembers where the painter
    // dragged it this session, and can be dragged by its title bar; it is always clamped on screen.
    function clampPos(el, left, top) {
        const w = el.offsetWidth || 272, h = el.offsetHeight || 300;
        // never above the canvas pane (the toolbar rows live there); dragging far up parks the panel at the pane's top edge
        const pane = document.getElementById('canvasViewport'), floor = pane ? Math.max(8, Math.round(pane.getBoundingClientRect().top)) : 8;
        return {
            left: Math.max(8, Math.min(window.innerWidth - w - 8, left)),
            top: Math.max(floor, Math.min(window.innerHeight - Math.min(h, window.innerHeight - 16) - 8, top)),
        };
    }
    function placeDialog(el) {
        let left, top;
        if (dlg.pos) { left = dlg.pos.left; top = dlg.pos.top; }
        else {
            const pane = document.getElementById('canvasViewport') || (document.getElementById('paintCanvas') && document.getElementById('paintCanvas').parentElement);
            const r = pane ? pane.getBoundingClientRect() : { top: 130, right: window.innerWidth };
            left = r.right - (el.offsetWidth || 272) - 16; top = r.top + 8;
        }
        const p = clampPos(el, left, top);
        el.style.left = p.left + 'px'; el.style.top = p.top + 'px'; el.style.right = 'auto';
    }
    function wireDrag(el, handle) {
        handle.addEventListener('pointerdown', function (e) {
            if (e.button !== 0 || (e.target && e.target.closest && e.target.closest('.cr-x'))) return;
            const r = el.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
            try { handle.setPointerCapture(e.pointerId); } catch (_e) { }
            const move = function (ev) {
                const p = clampPos(el, ev.clientX - dx, ev.clientY - dy);
                el.style.left = p.left + 'px'; el.style.top = p.top + 'px'; el.style.right = 'auto';
                dlg.pos = p;
            };
            const up = function () {
                handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', up); handle.removeEventListener('pointercancel', up);
            };
            handle.addEventListener('pointermove', move); handle.addEventListener('pointerup', up); handle.addEventListener('pointercancel', up);
            e.preventDefault();
        });
    }

    function open(host) {
        if (typeof document === 'undefined') return false;
        if (dlg.state) return true;
        dlg.host = host;
        const img = host.getImage(true);
        if (!img) { host.toast('Color Range: load a paint image first'); return false; }
        injectStyles();
        const t0 = performance.now();
        const grid = labGrid(img.data, img.w, img.h);
        dlg.state = { grid: grid, rgba: img.data, ops: [], tool: 's', fuzziness: 40, localized: false, range: 100,
            invert: false, mode: 'replace', mask: null, previewMode: 'tint', prepMs: performance.now() - t0 };
        const el = document.createElement('div');
        el.id = 'spbColorRangeDlg';
        el.innerHTML = [
            window.SPB_TFX2_OFF ? '<h4>Color range</h4>' : '<h4 class="cr-title" id="spbCrTitle"><span>Color range</span><button class="cr-x" id="spbCrX" type="button" title="Cancel (Esc)" aria-label="Close Color Range">×</button></h4>',
            '<div class="cr-row"><label>Fuzziness</label><input id="spbCrFuzz" type="range" min="0" max="200" value="40"><input id="spbCrFuzzN" type="number" min="0" max="200" value="40"></div>',
            '<div class="cr-row"><label><input id="spbCrLoc" type="checkbox"> Localized Color Clusters</label></div>',
            '<div class="cr-row" id="spbCrRangeRow" style="display:none"><label>Range</label><input id="spbCrRange" type="range" min="0" max="100" value="100"><span id="spbCrRangeV">100%</span></div>',
            '<div class="cr-row"><label>Eyedropper</label>',
            '<button class="cr-btn on" id="spbCrToolS" title="Sample: the clicked colour replaces the sample">Sample</button>',
            '<button class="cr-btn" id="spbCrToolP" title="Add to Sample (or Shift+click)">+ Add</button>',
            '<button class="cr-btn" id="spbCrToolM" title="Subtract from Sample (or Alt+click)">- Sub</button></div>',
            '<div class="cr-row"><label>Apply as</label><select id="spbCrMode" style="font-size:10px;padding:2px;"><option value="replace">Replace</option><option value="add">Add (+)</option><option value="subtract">Subtract (-)</option></select></div>',
            '<div class="cr-row"><label><input id="spbCrInv" type="checkbox"> Invert</label>',
            '<label style="margin-left:auto"><input id="spbCrMask" type="checkbox"> Mask view</label></div>',
            '<div class="cr-hint" id="spbCrInfo">Click the canvas to sample a colour.</div>',
            '<div class="cr-row" style="margin-top:10px;justify-content:flex-end"><button class="cr-btn" id="spbCrReset">Reset</button><button class="cr-btn" id="spbCrCancel">Cancel</button><button class="cr-btn on" id="spbCrOk">OK</button></div>',
            '<div class="cr-hint">Shift+click adds, Alt+click subtracts. OK applies using the selection mode (Replace / Add / Subtract) with the Feather value. Esc cancels.</div>',
        ].join('');
        document.body.appendChild(el);
        dlg.el = el;
        if (!window.SPB_TFX2_OFF) placeDialog(el);
        const S = dlg.state;
        const q = function (id) { return document.getElementById(id); };
        q('spbCrFuzz').oninput = function () { S.fuzziness = +this.value; q('spbCrFuzzN').value = this.value; schedule(); };
        q('spbCrFuzzN').oninput = function () { const v = Math.max(0, Math.min(200, +this.value || 0)); S.fuzziness = v; q('spbCrFuzz').value = v; schedule(); };
        q('spbCrLoc').onchange = function () { S.localized = this.checked; q('spbCrRangeRow').style.display = this.checked ? 'flex' : 'none'; schedule(); };
        q('spbCrRange').oninput = function () { S.range = +this.value; q('spbCrRangeV').textContent = this.value + '%'; schedule(); };
        q('spbCrMode').onchange = function () { S.mode = this.value; };
        q('spbCrInv').onchange = function () { S.invert = this.checked; schedule(); };
        q('spbCrMask').onchange = function () { S.previewMode = this.checked ? 'mask' : 'tint'; drawPreview(); };
        q('spbCrToolS').onclick = function () { setTool('s'); };
        q('spbCrToolP').onclick = function () { setTool('+'); };
        q('spbCrToolM').onclick = function () { setTool('-'); };
        q('spbCrReset').onclick = function () { S.ops = []; S.mask = null; setTool('s'); recompute(); };
        q('spbCrCancel').onclick = function () { close(false); };
        if (q('spbCrX')) q('spbCrX').onclick = function () { close(false); };
        if (q('spbCrTitle')) wireDrag(el, q('spbCrTitle'));
        q('spbCrOk').onclick = function () { close(true); };
        document.addEventListener('keydown', onKey, true);
        // window capture: the canvas container's own capture handler runs the tool and stops propagation.
        window.addEventListener('mousedown', onCanvasDown, true);
        ensureOverlay();
        return true;
    }

    function isOpen() { return !!dlg.state; }
    function cancel() { return isOpen() ? (close(false), true) : false; }

    return {
        version: 'w4-2026-10-09',
        rgbToLab: rgbToLab, quant: quant, labGrid: labGrid,
        rangePoint: rangePoint, rangeGrow: rangeGrow, rangeSubtract: rangeSubtract, rangeFromOps: rangeFromOps,
        coverage: coverage, select: select,
        open: open, close: close, isOpen: isOpen, cancel: cancel, _dlg: dlg,
    };
});
