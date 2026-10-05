// Saved Import DNA recipes — apply to sidebar or rebake. SPB-109
(function () {
    'use strict';

    function toast(msg, kind) {
        if (typeof showToast === 'function') showToast(msg, kind);
        else console.log('[dna-presets]', msg);
    }

    function loadPresets() {
        return fetch('/api/user-imports/dna-presets')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                return data.presets || [];
            });
    }

    function applyRecipe(recipe) {
        if (!recipe) return;
        var kind = recipe.kind || 'style';
        var styleSel = document.getElementById('userImportStyleOverride');
        var els = {
            a: document.getElementById('dnaRemixStyleA'),
            b: document.getElementById('dnaRemixStyleB'),
            t: document.getElementById('dnaRemixSlider'),
            tVal: document.getElementById('dnaRemixSliderVal')
        };
        if (kind === 'remix' && els.a && els.b) {
            els.a.value = recipe.style_a;
            els.b.value = recipe.style_b;
            var pct = Math.round(parseFloat(recipe.remix_t || 0.5) * 100);
            if (els.t) els.t.value = String(pct);
            if (els.tVal) els.tVal.textContent = pct + '%';
            if (typeof syncDnaStylePickButton === 'function') {
                syncDnaStylePickButton(els.a);
                syncDnaStylePickButton(els.b);
            }
            toast('Applied remix recipe to DNA Remix', 'success');
            return;
        }
        if (kind === 'insane') {
            toast('INSANE quad saved — run SHOKK THE WORLD to roll new 4-way blends; recipe stored for reference.', 'info');
            return;
        }
        if (styleSel && recipe.style) {
            styleSel.value = recipe.style;
            if (typeof syncDnaStylePickButton === 'function') {
                syncDnaStylePickButton(styleSel);
            }
            toast('Applied style: ' + recipe.style, 'success');
        }
    }

    function renderPresetsList(presets) {
        var box = document.getElementById('dnaPresetsList');
        if (!box) return;
        if (!presets.length) {
            box.innerHTML = '<p class="hint">No saved recipes yet. Use <strong>Save recipe</strong> on a World card you like.</p>';
            return;
        }
        box.innerHTML = presets.map(function (p) {
            var rec = p.recipe || {};
            var k = rec.kind || '?';
            // Style thumbnails make a saved recipe identifiable at a glance —
            // the list was label-only, so "remix" rows all looked alike. A mix
            // shows BOTH parent styles; the mix % is the useful detail.
            function thumb(styleId) {
                if (!styleId) return '';
                return '<img src="/api/user-imports/dna-style-thumb/' + encodeURIComponent(styleId) + '.png?v=2" ' +
                    'alt="" loading="lazy" decoding="async" title="' + styleId + '" ' +
                    'style="width:22px;height:22px;border-radius:3px;object-fit:cover;background:#0a0c10;flex-shrink:0;">';
            }
            var thumbs = (k === 'remix')
                ? (thumb(rec.style_a) + thumb(rec.style_b))
                : thumb(rec.style);
            var detail = (k === 'remix' && rec.remix_t != null)
                ? (' · mix ' + Math.round(parseFloat(rec.remix_t) * 100) + '%')
                : '';
            return '<div class="dna-preset-row" style="display:flex;gap:5px;align-items:center;margin:4px 0;flex-wrap:wrap;">' +
                thumbs +
                '<span style="font-size:10px;flex:1;min-width:100px;">' + (p.label || p.id) +
                ' <span class="hint">(' + k + detail + ')</span></span>' +
                '<button type="button" class="btn btn-sm" data-preset-apply="' + p.id + '" title="Load this recipe back into the sidebar controls">Apply</button>' +
                '<button type="button" class="btn btn-sm" data-preset-del="' + p.id + '" title="Delete this recipe">×</button>' +
                '</div>';
        }).join('');
        box.querySelectorAll('[data-preset-apply]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-preset-apply');
                var row = presets.find(function (x) { return x.id === id; });
                if (row) applyRecipe(row.recipe);
            });
        });
        box.querySelectorAll('[data-preset-del]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-preset-del');
                var row = presets.find(function (x) { return x.id === id; });
                var label = (row && row.label) || id;
                // Saved recipes are not recoverable — one misclick on × used
                // to delete permanently with zero warning.
                if (!window.confirm('Delete DNA recipe "' + label + '"? This can\'t be undone.')) return;
                fetch('/api/user-imports/dna-presets/' + encodeURIComponent(id), { method: 'DELETE' })
                    .then(function (r) { return r.json(); })
                    .then(function () { refreshDnaPresets(); })
                    .catch(function (err) { toast(err.message, 'error'); });
            });
        });
    }

    function refreshDnaPresets() {
        return loadPresets().then(renderPresetsList).catch(function (err) {
            var box = document.getElementById('dnaPresetsList');
            if (box) box.innerHTML = '<p class="hint" style="color:#f88;">' + err.message + '</p>';
        });
    }

    window.refreshDnaPresets = refreshDnaPresets;

    document.addEventListener('DOMContentLoaded', function () {
        refreshDnaPresets();
        // Shared catalog fetch (defined in user-imports.js) — third consumer.
        (window.fetchDnaStylesOnce
            ? window.fetchDnaStylesOnce()
            : fetch('/api/user-imports/dna-styles').then(function (r) { return r.json(); }))
            .then(function (data) {
                var el = document.getElementById('dnaStyleCount');
                if (el && data.styles) {
                    var lay = data.world_layout || {};
                    el.textContent = '(' + data.styles.length + ' styles · World: ' +
                        (lay.standard || 8) + '+' + (lay.remix || 7) + '+' + (lay.insane || 5) + ')';
                }
            })
            .catch(function () { /* optional */ });
    });
})();
