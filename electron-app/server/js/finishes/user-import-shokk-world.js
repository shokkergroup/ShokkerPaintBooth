// SHOKK THE WORLD + DNA Remix — SPB-109 explosion UI.
(function () {
    'use strict';

    var WORLD_TOTAL = 20;
    var _session = null;
    var _variants = [];
    var _selected = {};
    var _remixDebounce = null;
    var _dnaCatalog = [];
    var _streamActive = false;
    var _streamGeneration = 0;

    function toast(msg, kind) {
        if (typeof showToast === 'function') showToast(msg, kind);
        else console.log('[shokk-world]', msg);
    }

    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function _wildnessScale() {
        var el = document.getElementById('shokkWildness');
        var v = el ? parseFloat(el.value) : 50;
        if (isNaN(v)) v = 50;
        // Piecewise so 50 == 1.0 exactly: subtle 0.4 .. balanced 1.0 .. insane 1.7
        var scale = v <= 50 ? (0.4 + (v / 50) * 0.6) : (1.0 + ((v - 50) / 50) * 0.7);
        return Math.round(scale * 1000) / 1000;
    }

    function _wildnessLabel() {
        var el = document.getElementById('shokkWildness');
        var out = document.getElementById('shokkWildnessVal');
        if (!el || !out) return;
        var v = parseFloat(el.value);
        out.textContent = v < 28 ? 'Subtle' : (v < 45 ? 'Easy' : (v <= 58 ? 'Balanced' : (v < 80 ? 'Wild' : 'INSANE')));
    }

    function _remixEls() {
        return {
            a: document.getElementById('dnaRemixStyleA'),
            b: document.getElementById('dnaRemixStyleB'),
            t: document.getElementById('dnaRemixSlider'),
            tVal: document.getElementById('dnaRemixSliderVal'),
            preview: document.getElementById('dnaRemixPreviewImg'),
            row: document.getElementById('dnaRemixRow')
        };
    }

    // DNA Remix is a BLEND of two DIFFERENT styles. Pick a B that never equals A
    // (mirrors the backend resolve_remix_styles() guarantee). Falls through the
    // whole catalog so even a 1-item edge case degrades gracefully.
    function _differentStyle(items, a) {
        if (!items || !items.length) return '';
        for (var i = 0; i < items.length; i++) {
            if (items[i] && items[i].id && items[i].id !== a) return items[i].id;
        }
        return (items[0] && items[0].id) || '';
    }

    function fillRemixSelects(catalog, autoStyle) {
        var els = _remixEls();
        if (!els.a || !els.b) return;
        var items = catalog || [];
        function fill(sel, pick) {
            sel.innerHTML = '';
            items.forEach(function (s) {
                var opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.label || s.id;
                sel.appendChild(opt);
            });
            if (pick) sel.value = pick;
        }
        var styleA = autoStyle || (items[0] && items[0].id) || '';
        fill(els.a, styleA);
        // Style B must ALWAYS differ from A so the first World mix slot (and the
        // live blend preview) actually blends two distinct DNAs.
        fill(els.b, _differentStyle(items, styleA));
        if (els.row) els.row.style.display = items.length ? '' : 'none';
        if (typeof window.syncDnaStylePickButton === 'function') {
            window.syncDnaStylePickButton(els.a);
            window.syncDnaStylePickButton(els.b);
        }
    }

    // Keep A and B distinct after a manual change: if the user picks B==A (or A==B),
    // nudge the OTHER select to the next different style so the mix is never a no-op.
    function _enforceDifferentRemixStyles(changed) {
        var els = _remixEls();
        if (!els.a || !els.b) return;
        if (els.a.value !== els.b.value) return;
        var items = (_dnaCatalog || []).slice();
        var alt = _differentStyle(items, els.a.value);
        if (!alt) return;
        if (changed === 'b' && els.a) els.a.value = alt;
        else if (els.b) els.b.value = alt;
    }

    function fetchRemixPreview() {
        if (!_session || !_session.session_id) return Promise.resolve();
        var els = _remixEls();
        if (!els.a || !els.b || !els.t) return Promise.resolve();
        return fetch('/api/user-imports/dna-remix-preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _session.session_id,
                style_a: els.a.value,
                style_b: els.b.value,
                remix_t: parseFloat(els.t.value) / 100
            })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                if (els.preview && data.preview_spec) {
                    els.preview.src = data.preview_spec;
                    els.preview.style.display = '';
                }
            })
            .catch(function () { /* slider debounce — ignore transient */ });
    }

    function bindDnaRemix() {
        var els = _remixEls();
        if (!els.t) return;
        function onSlide() {
            if (els.tVal) els.tVal.textContent = els.t.value + '%';
            clearTimeout(_remixDebounce);
            _remixDebounce = setTimeout(fetchRemixPreview, 380);
        }
        els.t.addEventListener('input', onSlide);
        if (els.a) els.a.addEventListener('change', function () {
            _enforceDifferentRemixStyles('a');
            if (typeof window.syncDnaStylePickButton === 'function') {
                window.syncDnaStylePickButton(els.a);
                window.syncDnaStylePickButton(els.b);
            }
            onSlide();
        });
        if (els.b) els.b.addEventListener('change', function () {
            _enforceDifferentRemixStyles('b');
            if (typeof window.syncDnaStylePickButton === 'function') {
                window.syncDnaStylePickButton(els.a);
                window.syncDnaStylePickButton(els.b);
            }
            onSlide();
        });
    }

    function ensureOverlay() {
        var el = document.getElementById('shokkWorldOverlay');
        if (el) return el;
        el = document.createElement('div');
        el.id = 'shokkWorldOverlay';
        el.className = 'shokk-world-overlay';
        el.innerHTML =
            '<div class="shokk-world-panel">' +
            '<header class="shokk-world-head">' +
            '<div><h2>SHOKK THE WORLD</h2><p class="shokk-world-sub" id="shokkWorldSub">Generating spec universes…</p></div>' +
            '<div class="shokk-world-head-actions">' +
            '<label class="shokk-world-pick" style="margin-right:8px;" title="Try in Booth: apply your SHOKK DROP upload as zone paint + spec">' +
            '<input type="checkbox" id="shokkWorldUsePaintSource" checked />' +
            '<span class="shokk-world-pick-label">Drop as paint source</span></label>' +
            '<button type="button" class="btn" id="shokkWorldSelectAll">Select all</button>' +
            '<button type="button" class="btn" id="shokkWorldSelectNone">Select none</button>' +
            '<span id="shokkWorldKindChips" style="display:inline-flex;gap:4px;margin-right:6px;">' +
            '<button type="button" class="btn shokk-world-chip" data-chip="all" title="Show every slot">All</button>' +
            '<button type="button" class="btn shokk-world-chip" data-chip="standard" title="Single-style specs (8)">Standard</button>' +
            '<button type="button" class="btn shokk-world-chip" data-chip="remix" title="Two-style blends (7)">Mix</button>' +
            '<button type="button" class="btn shokk-world-chip" data-chip="insane" title="4-way INSANE blends (5)">INSANE</button>' +
            '<button type="button" class="btn shokk-world-chip" data-chip="picked" title="Only the slots you picked">✔ Picked</button>' +
            '</span>' +
            '<button type="button" class="btn primary" id="shokkWorldSaveBtn" disabled>Save selected (0)</button>' +
            '<button type="button" class="btn" id="shokkWorldCloseBtn">Close</button>' +
            '</div></header>' +
            '<div class="shokk-world-ekg-wrap"><canvas id="shokkWorldEkg" width="900" height="72"></canvas></div>' +
            '<div class="shokk-world-grid" id="shokkWorldGrid"></div>' +
            '</div>';
        document.body.appendChild(el);
        // Keyboard layer order: lightbox (top) → DNA picker/palette editor →
        // this overlay. Escape peels one layer at a time; ←/→/Space drive the
        // lightbox when it's up.
        document.addEventListener('keydown', function (e) {
            var lb = document.getElementById('shokkWorldLightbox');
            if (lb && lb.style.display === 'flex') {
                if (e.key === 'Escape') { closeWorldLightbox(); }
                else if (e.key === 'ArrowLeft') { e.preventDefault(); stepWorldLightbox(-1); }
                else if (e.key === 'ArrowRight') { e.preventDefault(); stepWorldLightbox(1); }
                else if (e.key === ' ') { e.preventDefault(); toggleWorldLightboxPick(); }
                return;
            }
            if (e.key !== 'Escape') return;
            var overlay = document.getElementById('shokkWorldOverlay');
            if (!overlay || !overlay.classList.contains('shokk-world-active')) return;
            var picker = document.getElementById('dnaStylePickerPanel');
            var palEd = document.getElementById('dnaPaletteEditor');
            if ((picker && !picker.hidden) || (palEd && !palEd.hidden)) return;
            closeShokkWorld();
        });
        el.querySelector('#shokkWorldCloseBtn').addEventListener('click', closeShokkWorld);
        el.querySelector('#shokkWorldSaveBtn').addEventListener('click', commitSelectedVariants);
        el.querySelector('#shokkWorldSelectAll').addEventListener('click', function () {
            // Only slots that actually baked — selecting failed/unbaked
            // indices sent dead slots to /commit and errored the whole save.
            for (var i = 0; i < WORLD_TOTAL; i++) {
                if (_variants[i]) _selected[i] = true;
            }
            _updateSaveBtn();
            _renderGridSelection();
        });
        el.querySelector('#shokkWorldSelectNone').addEventListener('click', function () {
            _selected = {};
            _updateSaveBtn();
            _renderGridSelection();
            if (_kindChip === 'picked') _applyKindChip();
        });
        el.querySelectorAll('.shokk-world-chip').forEach(function (chip) {
            chip.style.fontSize = '10px';
            chip.style.minHeight = '26px';
            chip.style.padding = '0 8px';
            chip.addEventListener('click', function () {
                _kindChip = chip.getAttribute('data-chip') || 'all';
                _applyKindChip();
            });
        });
        _syncKindChipUi();
        return el;
    }

    // ---- Kind chips: slice 20 slots down to the family you're judging ----
    var _kindChip = 'all';
    function _variantChipKind(v) {
        if (!v) return null;
        if (v.is_insane || v.kind === 'insane') return 'insane';
        if (v.kind === 'remix') return 'remix';
        return 'standard';
    }
    function _syncKindChipUi() {
        var host = document.getElementById('shokkWorldKindChips');
        if (!host) return;
        host.querySelectorAll('.shokk-world-chip').forEach(function (c) {
            var on = c.getAttribute('data-chip') === _kindChip;
            c.style.borderColor = on ? 'var(--accent, #f0c040)' : 'var(--line, #2b3645)';
            c.style.color = on ? 'var(--accent, #f0c040)' : 'var(--text, #eaf0f8)';
            c.style.fontWeight = on ? '800' : '640';
        });
    }
    function _applyKindChip() {
        _syncKindChipUi();
        var shown = 0;
        for (var i = 0; i < WORLD_TOTAL; i++) {
            var slot = document.querySelector('.shokk-world-slot[data-index="' + i + '"]');
            if (!slot) continue;
            var v = _variants[i];
            var vis;
            if (_kindChip === 'all') vis = true;
            else if (_kindChip === 'picked') vis = !!_selected[i];
            else vis = (_variantChipKind(v) === _kindChip);
            // Slots that haven't baked yet stay visible under 'all' only, so a
            // family filter never hides the fact that baking is still running.
            slot.style.display = vis ? '' : 'none';
            if (vis) shown++;
        }
        var sub = document.getElementById('shokkWorldSub');
        if (sub && _kindChip !== 'all' && !_streamActive) {
            sub.textContent = 'Filtered: ' + shown + ' ' + _kindChip + ' slot(s) — chips above switch families.';
        }
    }

    var _ekgAnim = null;
    function startEkg(canvas) {
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');
        var w = canvas.width;
        var h = canvas.height;
        var t0 = Date.now();
        var burst = 0;
        function draw() {
            var t = (Date.now() - t0) / 1000;
            ctx.fillStyle = '#060a10';
            ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = '#62d7ff';
            ctx.lineWidth = 2;
            ctx.shadowColor = '#f0c040';
            ctx.shadowBlur = burst > 0 ? 12 + burst * 4 : 4;
            ctx.beginPath();
            for (var x = 0; x < w; x += 3) {
                var phase = t * 6 + x * 0.04;
                var amp = (h * 0.35) * (0.4 + 0.6 * Math.abs(Math.sin(phase * 0.7)));
                if (burst > 0) amp *= 1 + burst * 0.35 * Math.sin(x * 0.2 + t * 20);
                var y = h / 2 + Math.sin(phase) * amp + Math.sin(phase * 2.3) * (h * 0.08);
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.shadowBlur = 0;
            if (burst > 0) burst = Math.max(0, burst - 0.04);
            _ekgAnim = requestAnimationFrame(draw);
        }
        draw();
        return function pulse() {
            burst = 1.2;
        };
    }

    function stopEkg() {
        if (_ekgAnim) cancelAnimationFrame(_ekgAnim);
        _ekgAnim = null;
    }

    var _ekgPulse = null;

    function buildGridSlots() {
        var grid = document.getElementById('shokkWorldGrid');
        if (!grid) return;
        grid.innerHTML = '';
        _variants = [];
        _kindChip = 'all'; // a fresh grid always starts unfiltered
        _syncKindChipUi();
        for (var i = 0; i < WORLD_TOTAL; i++) {
            _variants[i] = null;
            var slot = document.createElement('article');
            slot.className = 'shokk-world-slot';
            slot.dataset.index = String(i);
            slot.innerHTML =
                '<div class="shokk-world-slot-inner">' +
                '<div class="shokk-world-slot-wait">⚡ ' + (i + 1) + '</div>' +
                '</div>' +
                '<label class="shokk-world-pick">' +
                '<input type="checkbox" data-idx="' + i + '" disabled />' +
                '<span class="shokk-world-pick-label">Pick</span></label>' +
                '<div class="shokk-world-slot-actions" style="display:none;flex-wrap:wrap;gap:4px;">' +
                '<button type="button" class="btn btn-sm shokk-world-zoom" data-idx="' + i + '" title="Zoom full-size — browse with ← →, Space picks">🔍</button>' +
                '<button type="button" class="btn btn-sm shokk-world-ball" data-idx="' + i + '" title="Spin this finish on the Finish Viewer ball with iRacing-style lighting">🔮 View on Ball</button>' +
                '<button type="button" class="btn btn-sm shokk-world-try" data-idx="' + i + '">Try in Booth</button>' +
                '<button type="button" class="btn btn-sm shokk-world-reroll" data-idx="' + i + '" title="Rebake this slot with a fresh seed">↻ Reroll</button>' +
                '<button type="button" class="btn btn-sm shokk-world-save-recipe" data-idx="' + i + '">Save recipe</button>' +
                '</div>';
            grid.appendChild(slot);
        }
        grid.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
            cb.addEventListener('change', function () {
                var idx = parseInt(cb.dataset.idx, 10);
                if (cb.checked) _selected[idx] = true;
                else delete _selected[idx];
                _updateSaveBtn();
                if (_kindChip === 'picked') _applyKindChip();
            });
        });
        grid.querySelectorAll('.shokk-world-try').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                tryVariantInBooth(parseInt(btn.dataset.idx, 10));
            });
        });
        grid.querySelectorAll('.shokk-world-save-recipe').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                saveVariantRecipe(parseInt(btn.dataset.idx, 10));
            });
        });
        grid.querySelectorAll('.shokk-world-reroll').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                rerollVariant(parseInt(btn.dataset.idx, 10));
            });
        });
        grid.querySelectorAll('.shokk-world-ball').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                viewVariantOnBall(parseInt(btn.dataset.idx, 10));
            });
        });
        grid.querySelectorAll('.shokk-world-zoom').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                openWorldLightbox(parseInt(btn.dataset.idx, 10));
            });
        });
    }

    // ---- Lightbox: judge specs at full size instead of 160px tiles ----
    var _lightboxIdx = null;
    function ensureWorldLightbox() {
        var lb = document.getElementById('shokkWorldLightbox');
        if (lb) return lb;
        lb = document.createElement('div');
        lb.id = 'shokkWorldLightbox';
        lb.style.cssText = 'display:none;position:fixed;inset:0;z-index:10110;background:rgba(2,4,8,0.94);flex-direction:column;align-items:center;justify-content:center;padding:20px;cursor:zoom-out;';
        lb.innerHTML =
            '<img id="shokkWorldLbImg" style="max-width:min(88vw,900px);max-height:72vh;border-radius:8px;border:1px solid #2b3645;background:#0a0c10;cursor:default;" alt="World variant zoom">' +
            '<div id="shokkWorldLbCap" style="margin-top:10px;font-size:13px;color:#eaf0f8;cursor:default;"></div>' +
            '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;cursor:default;">' +
            '<button type="button" class="btn" id="shokkWorldLbPrev">← Prev</button>' +
            '<button type="button" class="btn primary" id="shokkWorldLbPick">Pick this one</button>' +
            '<button type="button" class="btn" id="shokkWorldLbNext">Next →</button>' +
            '<button type="button" class="btn" id="shokkWorldLbClose">Close</button>' +
            '</div>' +
            '<p style="margin:8px 0 0;font-size:10px;color:#9ba8b8;cursor:default;">← → browse baked slots · Space picks · Esc closes</p>';
        document.body.appendChild(lb);
        lb.addEventListener('click', function (e) { if (e.target === lb) closeWorldLightbox(); });
        lb.querySelector('#shokkWorldLbClose').addEventListener('click', closeWorldLightbox);
        lb.querySelector('#shokkWorldLbPrev').addEventListener('click', function () { stepWorldLightbox(-1); });
        lb.querySelector('#shokkWorldLbNext').addEventListener('click', function () { stepWorldLightbox(1); });
        lb.querySelector('#shokkWorldLbPick').addEventListener('click', toggleWorldLightboxPick);
        return lb;
    }
    function openWorldLightbox(index) {
        if (!_variants[index]) return;
        ensureWorldLightbox().style.display = 'flex';
        _lightboxIdx = index;
        renderWorldLightbox();
    }
    function renderWorldLightbox() {
        var lb = document.getElementById('shokkWorldLightbox');
        if (!lb || _lightboxIdx === null) return;
        var v = _variants[_lightboxIdx] || {};
        lb.querySelector('#shokkWorldLbImg').src = v.preview_spec || v.preview_combined || '';
        var picked = !!_selected[_lightboxIdx];
        lb.querySelector('#shokkWorldLbCap').textContent =
            'Slot ' + (_lightboxIdx + 1) + ' / ' + WORLD_TOTAL + ' — ' + (v.label || '') +
            (v.gauntlet_passed ? ' · gauntlet PASS' : '') + (picked ? ' · ✔ PICKED' : '');
        lb.querySelector('#shokkWorldLbPick').textContent = picked ? '✔ Picked — click to unpick' : 'Pick this one';
    }
    function stepWorldLightbox(dir) {
        if (_lightboxIdx === null) return;
        var i = _lightboxIdx;
        for (var n = 0; n < WORLD_TOTAL; n++) {
            i = (i + dir + WORLD_TOTAL) % WORLD_TOTAL;
            if (_variants[i]) { _lightboxIdx = i; renderWorldLightbox(); return; }
        }
    }
    function toggleWorldLightboxPick() {
        if (_lightboxIdx === null) return;
        var slot = document.querySelector('.shokk-world-slot[data-index="' + _lightboxIdx + '"]');
        var cb = slot && slot.querySelector('input[type=checkbox]');
        if (!cb || cb.disabled) return;
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change'));
        renderWorldLightbox();
    }
    function closeWorldLightbox() {
        var lb = document.getElementById('shokkWorldLightbox');
        if (lb) lb.style.display = 'none';
        _lightboxIdx = null;
    }

    function rerollVariant(index) {
        if (!_session || !_session.session_id) return;
        var slot = document.querySelector('.shokk-world-slot[data-index="' + index + '"]');
        if (slot) {
            var inner = slot.querySelector('.shokk-world-slot-inner');
            if (inner) inner.innerHTML = '<div class="shokk-world-slot-wait">↻ rerolling ' + (index + 1) + '…</div>';
            slot.classList.remove('shokk-world-slot-ready');
        }
        fetch('/api/user-imports/shokk-the-world/reroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: _session.session_id, index: index })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                revealVariant(index, data);
                toast('Rerolled slot ' + (index + 1), 'success');
            })
            .catch(function (err) {
                toast('Reroll failed: ' + err.message, 'error');
                if (_variants[index]) revealVariant(index, _variants[index]);
            });
    }

    function saveVariantRecipe(index) {
        if (!_session || !_variants[index]) {
            toast('Wait for this card to finish baking', 'info');
            return;
        }
        var label = window.prompt('Name this DNA recipe (optional):', _variants[index].label || '');
        if (label === null) return;
        fetch('/api/user-imports/dna-presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _session.session_id,
                index: index,
                label: label || undefined
            })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                toast('Saved recipe: ' + (data.preset && data.preset.label), 'success');
                if (typeof window.refreshDnaPresets === 'function') window.refreshDnaPresets();
            })
            .catch(function (err) { toast(err.message, 'error'); });
    }

    function revealVariant(index, data) {
        _variants[index] = data;
        var slot = document.querySelector('.shokk-world-slot[data-index="' + index + '"]');
        if (!slot) return;
        var passed = data.gauntlet_passed;
        var kindTag = '';
        if (data.is_insane || data.kind === 'insane') {
            kindTag = '<span class="drop-gauntlet-badge drop-gauntlet-pass" style="margin-left:4px;background:#6a1a8a;">INSANE</span>';
        } else if (data.kind === 'remix') {
            kindTag = '<span class="drop-gauntlet-badge drop-gauntlet-pass" style="margin-left:4px;background:#1a4a6a;">MIX</span>';
        } else if (data.exotic_amp || (data.dna && data.dna.exotic_amp)) {
            kindTag = '<span class="drop-gauntlet-badge drop-gauntlet-pass" style="margin-left:4px;">EXOTIC</span>';
        }
        var badge = passed
            ? '<span class="drop-gauntlet-badge drop-gauntlet-pass">PASS</span>' + kindTag
            : '<span class="drop-gauntlet-badge drop-gauntlet-fail">!</span>' + kindTag;
        var imgSrc = data.preview_spec || data.preview_combined || '';
        var innerEl = slot.querySelector('.shokk-world-slot-inner');
        innerEl.innerHTML =
            '<img src="' + esc(imgSrc) + '" alt="' + esc(data.label) + '">' +
            '<div class="shokk-world-slot-cap">' + esc(data.label) + ' ' + badge + '</div>';
        // The whole preview is the pick target — the bare checkbox was a
        // ~12px click target for the overlay's single most common action.
        // dataset guard: reroll re-runs revealVariant on the SAME inner div,
        // a second listener would toggle twice per click.
        if (!innerEl.dataset.pickBound) {
            innerEl.dataset.pickBound = '1';
            innerEl.style.cursor = 'pointer';
            innerEl.title = 'Click to pick / unpick';
            innerEl.addEventListener('click', function () {
                var pcb = slot.querySelector('input[type=checkbox]');
                if (!pcb || pcb.disabled) return;
                pcb.checked = !pcb.checked;
                pcb.dispatchEvent(new Event('change'));
            });
        }
        slot.classList.add('shokk-world-slot-ready');
        var cb = slot.querySelector('input[type=checkbox]');
        if (cb) {
            cb.disabled = false;
            cb.checked = !!_selected[index];
        }
        var acts = slot.querySelector('.shokk-world-slot-actions');
        if (acts) acts.style.display = '';
        // A slot that bakes while a family filter is active must respect it.
        if (_kindChip !== 'all') _applyKindChip();
        if (_ekgPulse) _ekgPulse();
    }

    function _updateSaveBtn() {
        var btn = document.getElementById('shokkWorldSaveBtn');
        var n = Object.keys(_selected).length;
        if (btn) {
            btn.disabled = n < 1;
            btn.textContent = 'Save selected (' + n + ')';
        }
    }

    function _renderGridSelection() {
        document.querySelectorAll('.shokk-world-slot input[type=checkbox]').forEach(function (cb) {
            var idx = parseInt(cb.dataset.idx, 10);
            cb.checked = !!_selected[idx];
        });
    }

    function fetchVariantWithRetry(sessionId, idx, attemptsLeft) {
        return fetch('/api/user-imports/shokk-the-world/' + encodeURIComponent(sessionId) + '/variant/' + idx)
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok || res.body.error) {
                    throw new Error((res.body && res.body.error) || 'Variant ' + (idx + 1) + ' failed');
                }
                return res.body;
            })
            .catch(function (err) {
                if (attemptsLeft > 0) {
                    return new Promise(function (resolve) {
                        setTimeout(resolve, 2500);
                    }).then(function () {
                        return fetchVariantWithRetry(sessionId, idx, attemptsLeft - 1);
                    });
                }
                throw err;
            });
    }

    function runVariantStream(sessionId) {
        var sub = document.getElementById('shokkWorldSub');
        var gen = ++_streamGeneration;
        _streamActive = true;

        function bakeOne(idx) {
            if (!_streamActive || gen !== _streamGeneration) return Promise.resolve();
            if (sub) sub.textContent = 'Baking spec ' + (idx + 1) + ' / ' + WORLD_TOTAL + '… (Try in Booth won\'t stop the queue)';
            return fetchVariantWithRetry(sessionId, idx, 6)
                .then(function (data) {
                    if (gen !== _streamGeneration) return;
                    revealVariant(idx, data);
                })
                .catch(function (err) {
                    if (gen !== _streamGeneration) return;
                    var slot = document.querySelector('.shokk-world-slot[data-index="' + idx + '"]');
                    if (slot) {
                        slot.querySelector('.shokk-world-slot-inner').innerHTML =
                            '<div class="shokk-world-slot-wait" style="color:#f0a8a8;">Failed — retrying later</div>';
                    }
                    console.warn('[shokk-world] variant', idx, err.message);
                })
                .then(function () {
                    if (idx + 1 < WORLD_TOTAL) return bakeOne(idx + 1);
                });
        }

        function retryFailedSlots(sessionId, genId) {
            var failed = [];
            for (var f = 0; f < WORLD_TOTAL; f++) {
                if (!_variants[f]) failed.push(f);
            }
            if (!failed.length || genId !== _streamGeneration) return Promise.resolve();
            if (sub) sub.textContent = 'Retrying ' + failed.length + ' failed slot(s)…';
            var chain = Promise.resolve();
            failed.forEach(function (idx) {
                chain = chain.then(function () {
                    if (genId !== _streamGeneration) return;
                    return fetchVariantWithRetry(sessionId, idx, 5)
                        .then(function (data) { revealVariant(idx, data); })
                        .catch(function (err) { console.warn('[shokk-world] retry', idx, err.message); });
                });
            });
            return chain;
        }

        return bakeOne(0).then(function () {
            return retryFailedSlots(sessionId, gen);
        }).then(function () {
            if (gen !== _streamGeneration) return;
            _streamActive = false;
            var nFail = 0;
            for (var f = 0; f < WORLD_TOTAL; f++) {
                if (!_variants[f]) {
                    nFail++;
                    _markSlotRetryable(f);
                }
            }
            if (sub) {
                sub.textContent = nFail
                    ? ('Done with ' + nFail + ' failure(s) — hit "↻ Retry" on the failed card(s).')
                    : 'Done — 8 standard · 7 mix · 5 INSANE. Save recipe or finish to library.';
            }
            stopEkg();
        });
    }

    // A slot that stayed empty after the automatic retry pass used to dead-end
    // ("run World again" = re-baking all 20). Give the failed card its own
    // Retry button that re-polls just that variant via the same endpoint.
    function _markSlotRetryable(index) {
        var slot = document.querySelector('.shokk-world-slot[data-index="' + index + '"]');
        if (!slot) return;
        var inner = slot.querySelector('.shokk-world-slot-inner');
        if (!inner) return;
        inner.innerHTML =
            '<div class="shokk-world-slot-wait" style="color:#f0a8a8;animation:none;">Spec ' + (index + 1) + ' failed</div>' +
            '<button type="button" class="btn btn-sm shokk-world-retry-one" style="width:100%;margin-top:4px;">↻ Retry</button>';
        var btn = inner.querySelector('.shokk-world-retry-one');
        if (btn) btn.addEventListener('click', function (e) {
            e.stopPropagation();
            manualRetrySlot(index);
        });
    }

    function manualRetrySlot(index) {
        if (!_session || !_session.session_id) return;
        var slot = document.querySelector('.shokk-world-slot[data-index="' + index + '"]');
        var inner = slot && slot.querySelector('.shokk-world-slot-inner');
        if (inner) inner.innerHTML = '<div class="shokk-world-slot-wait">↻ retrying ' + (index + 1) + '…</div>';
        fetchVariantWithRetry(_session.session_id, index, 3)
            .then(function (data) {
                revealVariant(index, data);
                toast('Spec ' + (index + 1) + ' recovered', 'success');
            })
            .catch(function (err) {
                toast('Spec ' + (index + 1) + ' still failing: ' + err.message, 'error');
                _markSlotRetryable(index);
            });
    }

    function openShokkWorldOverlay(session, keepSelection) {
        _session = session;
        if (!keepSelection) _selected = {};
        _streamActive = false;
        var overlay = ensureOverlay();
        overlay.classList.add('shokk-world-active');
        // Session exists now — light up the sidebar "Reopen World" button so
        // closing the overlay is no longer a one-way door.
        var rb = document.getElementById('btnResumeWorld');
        if (rb) rb.style.display = '';
        // Car template = always paint+spec for the whole car, so the
        // "Drop as paint source" toggle is meaningless: force it ON and hide it.
        var usePaintCb = document.getElementById('shokkWorldUsePaintSource');
        if (usePaintCb) {
            usePaintCb.checked = true;
            var usePaintLbl = usePaintCb.closest ? usePaintCb.closest('label') : usePaintCb.parentNode;
            if (usePaintLbl && usePaintLbl.style) {
                usePaintLbl.style.display = (session && session.is_car_template) ? 'none' : '';
            }
        }
        buildGridSlots();
        _updateSaveBtn();
        var canvas = document.getElementById('shokkWorldEkg');
        stopEkg();
        _ekgPulse = startEkg(canvas);
        runVariantStream(session.session_id).catch(function (err) {
            toast('SHOKK THE WORLD failed: ' + err.message, 'error');
            stopEkg();
        });
    }

    function closeShokkWorld() {
        _streamActive = false;
        _streamGeneration++;
        var overlay = document.getElementById('shokkWorldOverlay');
        if (overlay) overlay.classList.remove('shokk-world-active');
        closeWorldLightbox();
        stopEkg();
    }

    // Closing the overlay used to be a one-way door — the 20-spec session was
    // gone from the UI (though still cached server-side). Reopen re-runs the
    // stream; cached variants reveal instantly and picks survive.
    function reopenLastShokkWorld() {
        if (!_session || !_session.session_id) {
            toast('No World session yet this visit — hit ⚡ SHOKK THE WORLD first', 'info');
            return;
        }
        openShokkWorldOverlay(_session, true);
    }
    window.reopenLastShokkWorld = reopenLastShokkWorld;

    function commitSelectedVariants() {
        if (!_session) return;
        var indices = Object.keys(_selected).map(function (k) { return parseInt(k, 10); }).filter(function (n) {
            return !isNaN(n);
        });
        if (!indices.length) {
            toast('Select at least one variant', 'error');
            return;
        }
        var btn = document.getElementById('shokkWorldSaveBtn');
        if (btn) btn.disabled = true;
        toast('Saving ' + indices.length + ' drop(s)…', 'info');
        fetch('/api/user-imports/shokk-the-world/commit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _session.session_id,
                indices: indices,
                name_prefix: _session.name || 'Shokk World'
            })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                toast('Saved ' + (data.imported && data.imported.length) + ' to SHOKK DROP', 'success');
                closeShokkWorld();
                if (typeof loadUserImports === 'function') loadUserImports();
                if (typeof refreshGallery === 'function') refreshGallery(data.imported);
            })
            .catch(function (err) {
                toast(err.message, 'error');
                _updateSaveBtn();
            });
    }

    function tryVariantInBooth(index) {
        if (!_session) return;
        if (!_variants[index]) {
            toast('Wait for this card preview to finish loading first', 'info');
            return;
        }
        var label = (_variants[index] && _variants[index].label) || ('slot ' + (index + 1));
        var usePaint = document.getElementById('shokkWorldUsePaintSource');
        var asSource = !usePaint || usePaint.checked;
        toast('Staging “' + label + '” (' + (asSource ? 'paint+spec' : 'spec only') + ')…', 'info');
        fetch('/api/user-imports/shokk-the-world/stage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _session.session_id,
                index: index,
                use_paint_source: asSource
            })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                var id = data.entry && data.entry.id;
                if (!id) throw new Error('No staged id');
                var wholeCar = !!(_session && _session.is_car_template);
                var url = (window.location.origin || '') + '/?stagedMono=' + encodeURIComponent(id) +
                    (wholeCar ? '&wholeCar=1' : '');
                window.open(url, '_blank');
                toast(
                    asSource
                        ? 'Opened Booth — drop image is paint source + spec for slot ' + (index + 1)
                        : 'Opened Booth — spec only (truck paint unchanged) slot ' + (index + 1),
                    'success'
                );
            })
            .catch(function (err) { toast(err.message, 'error'); });
    }

    function viewVariantOnBall(index) {
        if (!_session) return;
        if (!_variants[index]) {
            toast('Wait for this card preview to finish loading first', 'info');
            return;
        }
        var label = (_variants[index] && _variants[index].label) || ('slot ' + (index + 1));
        var usePaint = document.getElementById('shokkWorldUsePaintSource');
        var asSource = !usePaint || usePaint.checked;
        toast('Sending “' + label + '” to the Finish Viewer ball…', 'info');
        fetch('/api/user-imports/shokk-the-world/stage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: _session.session_id,
                index: index,
                use_paint_source: asSource
            })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                var id = data.entry && data.entry.id;
                if (!id) throw new Error('No staged id');
                var url = (window.location.origin || '') +
                    '/finish-viewer.html?finish=' + encodeURIComponent(id) + '&source=api';
                window.open(url, '_blank');
                toast('Opened on the spinning ball — slot ' + (index + 1), 'success');
            })
            .catch(function (err) { toast('View on Ball failed: ' + err.message, 'error'); });
    }

    function startShokkTheWorld(fileList) {
        var files = Array.prototype.slice.call(fileList || []);
        if (!files.length) {
            toast('Drop an image first', 'error');
            return Promise.resolve();
        }
        var vibe = document.getElementById('userImportVibeRef');
        var kindSel = document.getElementById('userImportKind');
        var isCarTemplate = !!(kindSel && kindSel.value === 'car_template');
        var els = _remixEls();
        var fd = new FormData();
        fd.append('files', files[0]);
        var name = files[0].name.replace(/\.[^.]+$/, '');
        fd.append('name', name);
        if (vibe && vibe.value.trim()) fd.append('vibe_ref', vibe.value.trim());
        if (els.a && els.b && els.t) {
            fd.append('remix_style_a', els.a.value);
            fd.append('remix_style_b', els.b.value);
            fd.append('remix_t', String(parseFloat(els.t.value) / 100));
        }
        fd.append('chroma_scale', String(_wildnessScale()));
        if (typeof window.getDnaPaletteOverrides === 'function') {
            var ov = window.getDnaPaletteOverrides();
            if (ov && Object.keys(ov).length) fd.append('palette_overrides', JSON.stringify(ov));
        }
        toast('SHOKK THE WORLD — normalizing to 2048²…', 'info');
        return fetch('/api/user-imports/shokk-the-world/start', { method: 'POST', body: fd })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                _session = data;
                // Remember the "Car template" drop type so Try-in-Booth merges the
                // pick as a whole-car zone (covers the entire body). 2026-05-31.
                _session.is_car_template = isCarTemplate;
                fillRemixSelects(_dnaCatalog, data.auto_style);
                var prev = document.getElementById('dnaRemixPreviewImg');
                if (prev && data.preview_paint) {
                    prev.src = data.preview_paint;
                    prev.style.display = 'block';
                }
                fetchRemixPreview();
                toast('Explosion started — ' + data.total + ' specs incoming', 'success');
                openShokkWorldOverlay(data);
                return data;
            })
            .catch(function (err) {
                toast('SHOKK THE WORLD: ' + err.message, 'error');
                throw err;
            });
    }

    function initShokkWorldUi() {
        // While specs are actively baking, an accidental tab close / refresh
        // silently killed the whole run — ask first. No prompt once idle.
        window.addEventListener('beforeunload', function (e) {
            if (!_streamActive) return;
            e.preventDefault();
            e.returnValue = '';
        });
        // Shared catalog fetch (defined in user-imports.js) — avoids a second
        // identical /dna-styles round-trip on every page load.
        (window.fetchDnaStylesOnce
            ? window.fetchDnaStylesOnce()
            : fetch('/api/user-imports/dna-styles').then(function (r) { return r.json(); }))
            .then(function (data) {
                _dnaCatalog = data.catalog || [];
                fillRemixSelects(_dnaCatalog, '');
                if (typeof initDnaStylePickers === 'function') {
                    initDnaStylePickers(_dnaCatalog, data.spec_inks);
                }
            });
        bindDnaRemix();

        var wild = document.getElementById('shokkWildness');
        if (wild) {
            wild.addEventListener('input', _wildnessLabel);
            _wildnessLabel();
        }

        var btn = document.getElementById('btnShokkTheWorld');
        if (btn) {
            btn.addEventListener('click', function () {
                var input = document.getElementById('shokkWorldFileInput');
                if (input) input.click();
            });
        }
        var fin = document.getElementById('shokkWorldFileInput');
        if (fin) {
            fin.addEventListener('change', function () {
                if (fin.files && fin.files.length) startShokkTheWorld(fin.files);
                fin.value = '';
            });
        }
        var aside = document.querySelector('aside[aria-label*="Import sidebar"]');
        if (aside) {
            aside.addEventListener('drop', function (e) {
                if (!e.dataTransfer || !e.dataTransfer.files) return;
                var files = [];
                for (var i = 0; i < e.dataTransfer.files.length; i++) {
                    var f = e.dataTransfer.files[i];
                    if (/\.(png|jpe?g|webp|tga|bmp)$/i.test(f.name) || (f.type || '').indexOf('image/') === 0) {
                        files.push(f);
                    }
                }
                if (files.length && e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    startShokkTheWorld(files);
                }
            }, true);
        }
    }

    window.startShokkTheWorld = startShokkTheWorld;
    window.openShokkWorldOverlay = openShokkWorldOverlay;
    window.closeShokkWorld = closeShokkWorld;
    window.tryVariantInBooth = tryVariantInBooth;
    window.fillRemixSelects = fillRemixSelects;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initShokkWorldUi);
    } else {
        initShokkWorldUi();
    }
})();
