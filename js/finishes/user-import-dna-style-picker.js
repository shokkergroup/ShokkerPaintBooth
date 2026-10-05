// DNA style thumbnail picker + spec-palette editor — SPB-109 SHOKK DROP.
(function () {
    'use strict';

    var _catalog = [];
    var _byId = {};
    var _labels = {};
    var _specInks = {};
    var _overrides = {};
    try {
        _overrides = JSON.parse(localStorage.getItem('spbDnaPaletteOverrides') || '{}') || {};
    } catch (e) {
        _overrides = {};
    }

    var _activeSelect = null;
    var _panel = null;
    var _grid = null;
    var _filter = null;
    var _editor = null;
    var _editStyle = null;

    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    }

    function thumbUrl(item) {
        if (item && item.thumb_url) return item.thumb_url;
        var id = item && item.id ? item.id : item;
        return '/api/user-imports/dna-style-thumb/' + encodeURIComponent(id) + '.png?v=2';
    }

    function inkCss(name) {
        var c = _specInks[name];
        return c ? 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')' : '#444';
    }

    function defaultPalette(id) {
        var it = _byId[id];
        return (it && it.palette) ? it.palette.slice() : [];
    }

    function currentPalette(id) {
        return _overrides[id] ? _overrides[id].slice() : defaultPalette(id);
    }

    function persistOverrides() {
        try {
            localStorage.setItem('spbDnaPaletteOverrides', JSON.stringify(_overrides));
        } catch (e) { /* quota — ignore */ }
    }

    // ---- main picker grid ----
    function ensurePanel() {
        if (_panel) return _panel;
        _panel = document.createElement('div');
        _panel.id = 'dnaStylePickerPanel';
        _panel.className = 'dna-style-picker-panel';
        _panel.hidden = true;
        _panel.innerHTML =
            '<div class="dna-style-picker-dialog">' +
            '<header class="dna-style-picker-head">' +
            '<strong id="dnaStylePickerTitle">Choose DNA style</strong>' +
            '<button type="button" class="btn" id="dnaStylePickerClose" aria-label="Close">×</button>' +
            '</header>' +
            '<input type="search" id="dnaStylePickerFilter" class="dna-style-picker-filter" placeholder="Filter styles…" autocomplete="off" />' +
            '<div class="dna-style-picker-grid" id="dnaStylePickerGrid"></div>' +
            '</div>';
        document.body.appendChild(_panel);
        _grid = _panel.querySelector('#dnaStylePickerGrid');
        _filter = _panel.querySelector('#dnaStylePickerFilter');
        _panel.querySelector('#dnaStylePickerClose').addEventListener('click', closePanel);
        _panel.addEventListener('click', function (e) { if (e.target === _panel) closePanel(); });
        _filter.addEventListener('input', renderGrid);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (_editor && !_editor.hidden) closeEditor();
                else if (_panel && !_panel.hidden) closePanel();
            }
        });
        return _panel;
    }

    function closePanel() {
        if (_panel) _panel.hidden = true;
        _activeSelect = null;
    }

    function openPanel(selectEl, title) {
        if (!selectEl || !_catalog.length) return;
        ensurePanel();
        _activeSelect = selectEl;
        var t = document.getElementById('dnaStylePickerTitle');
        if (t) t.textContent = title || 'Choose DNA style';
        if (_filter) { _filter.value = ''; _filter.focus(); }
        renderGrid();
        _panel.hidden = false;
    }

    function renderGrid() {
        if (!_grid) return;
        var q = (_filter && _filter.value || '').trim().toLowerCase();
        var html = '';
        _catalog.forEach(function (s) {
            if (!s.id) return;
            var label = s.label || s.id;
            var desc = s.description || '';
            if (q && label.toLowerCase().indexOf(q) < 0 && s.id.indexOf(q) < 0 &&
                desc.toLowerCase().indexOf(q) < 0) return;
            var sel = _activeSelect && _activeSelect.value === s.id ? ' dna-style-tile-active' : '';
            var tuned = _overrides[s.id] ? '<span class="dna-style-tile-tuned" title="Custom spec palette">●</span>' : '';
            html +=
                '<div class="dna-style-tile' + sel + '" data-style-id="' + esc(s.id) + '" title="' + esc(desc || label) + '">' +
                '<img src="' + esc(thumbUrl(s)) + '" alt="" loading="lazy" />' +
                '<span class="dna-style-tile-label">' + esc(label) + '</span>' +
                '<button type="button" class="dna-style-tile-pal" data-edit="' + esc(s.id) + '" title="Edit spec palette">🎨</button>' +
                tuned + '</div>';
        });
        _grid.innerHTML = html || '<p class="hint" style="padding:12px;">No styles match filter.</p>';
        _grid.querySelectorAll('.dna-style-tile').forEach(function (tile) {
            tile.addEventListener('click', function () {
                var id = tile.getAttribute('data-style-id');
                if (_activeSelect && id) {
                    _activeSelect.value = id;
                    _activeSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    syncPickButton(_activeSelect);
                }
                closePanel();
            });
        });
        _grid.querySelectorAll('.dna-style-tile-pal').forEach(function (b) {
            b.addEventListener('click', function (e) {
                e.stopPropagation();
                openEditor(b.getAttribute('data-edit'));
            });
        });
    }

    // ---- spec palette editor ----
    function ensureEditor() {
        if (_editor) return _editor;
        _editor = document.createElement('div');
        _editor.id = 'dnaPaletteEditor';
        _editor.className = 'dna-pal-editor';
        _editor.hidden = true;
        _editor.innerHTML =
            '<div class="dna-pal-dialog">' +
            '<header class="dna-style-picker-head">' +
            '<strong id="dnaPalTitle">Spec palette</strong>' +
            '<button type="button" class="btn" id="dnaPalClose" aria-label="Close">×</button>' +
            '</header>' +
            '<p class="hint" style="margin:8px 12px 0;">Pick which colors appear in this style\u2019s SPEC MAP. These are spec-channel inks (M/R/CC), so each is a real material shade.</p>' +
            '<div class="dna-pal-chips" id="dnaPalChips"></div>' +
            '<footer class="dna-pal-foot">' +
            '<button type="button" class="btn" id="dnaPalReset">Reset to default</button>' +
            '<button type="button" class="btn primary" id="dnaPalSave">Save palette</button>' +
            '</footer></div>';
        document.body.appendChild(_editor);
        _editor.addEventListener('click', function (e) { if (e.target === _editor) closeEditor(); });
        _editor.querySelector('#dnaPalClose').addEventListener('click', closeEditor);
        _editor.querySelector('#dnaPalReset').addEventListener('click', function () {
            if (_editStyle) { delete _overrides[_editStyle]; persistOverrides(); renderEditorChips(); }
        });
        _editor.querySelector('#dnaPalSave').addEventListener('click', saveEditor);
        return _editor;
    }

    function openEditor(styleId) {
        if (!styleId) return;
        ensureEditor();
        _editStyle = styleId;
        var t = _editor.querySelector('#dnaPalTitle');
        if (t) t.textContent = 'Spec palette · ' + (_labels[styleId] || styleId);
        renderEditorChips();
        _editor.hidden = false;
    }

    function closeEditor() { if (_editor) _editor.hidden = true; _editStyle = null; }

    function renderEditorChips() {
        var box = _editor.querySelector('#dnaPalChips');
        if (!box) return;
        var active = currentPalette(_editStyle);
        var html = '';
        Object.keys(_specInks).forEach(function (name) {
            var on = active.indexOf(name) >= 0 ? ' dna-pal-chip-on' : '';
            html += '<button type="button" class="dna-pal-chip' + on + '" data-ink="' + esc(name) + '" ' +
                'style="background:' + inkCss(name) + ';">' + esc(name) +
                '<span class="dna-pal-check">✓</span></button>';
        });
        box.innerHTML = html;
        box.querySelectorAll('.dna-pal-chip').forEach(function (c) {
            c.addEventListener('click', function () { c.classList.toggle('dna-pal-chip-on'); });
        });
    }

    function saveEditor() {
        var picked = [];
        _editor.querySelectorAll('.dna-pal-chip-on').forEach(function (c) {
            picked.push(c.getAttribute('data-ink'));
        });
        if (picked.length < 2) {
            if (typeof showToast === 'function') showToast('Pick at least 2 inks', 'error');
            return;
        }
        var def = defaultPalette(_editStyle).slice().sort().join(',');
        if (picked.slice().sort().join(',') === def) delete _overrides[_editStyle];
        else _overrides[_editStyle] = picked;
        persistOverrides();
        if (typeof showToast === 'function') showToast('Spec palette saved for ' + (_labels[_editStyle] || _editStyle), 'success');
        closeEditor();
        renderGrid();
    }

    // ---- compact picker buttons wrapping the native <select> ----
    function syncPickButton(selectEl) {
        var wrap = selectEl && selectEl.closest('.dna-style-pick');
        if (!wrap) return;
        var btn = wrap.querySelector('.dna-style-pick-btn');
        var img = wrap.querySelector('.dna-style-pick-thumb');
        var lab = wrap.querySelector('.dna-style-pick-label');
        if (!btn) return;
        var id = selectEl.value;
        if (!id) {
            if (lab) lab.textContent = 'Auto (analyze image)';
            if (img) { img.removeAttribute('src'); img.style.display = 'none'; }
            return;
        }
        var item = _byId[id];
        if (lab) lab.textContent = (item && item.label) || _labels[id] || id;
        if (img) { img.src = thumbUrl(item || id); img.style.display = ''; img.alt = lab ? lab.textContent : id; }
    }

    function wrapSelect(selectEl, labelText) {
        if (!selectEl || selectEl.dataset.dnaPickWrapped) return;
        selectEl.dataset.dnaPickWrapped = '1';
        var wrap = document.createElement('div');
        wrap.className = 'dna-style-pick';
        selectEl.parentNode.insertBefore(wrap, selectEl);
        wrap.appendChild(selectEl);
        selectEl.classList.add('dna-style-pick-native');

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'dna-style-pick-btn';
        btn.innerHTML =
            '<img class="dna-style-pick-thumb" alt="" style="display:none;" />' +
            '<span class="dna-style-pick-label">Choose style…</span>' +
            '<span class="dna-style-pick-chevron">▾</span>';
        btn.addEventListener('click', function () {
            openPanel(selectEl, labelText ? ('Choose ' + labelText) : 'Choose DNA style');
        });

        if (labelText) {
            var lbl = document.createElement('span');
            lbl.className = 'dna-style-pick-field-label';
            lbl.textContent = labelText;
            wrap.insertBefore(lbl, selectEl);
        }
        wrap.insertBefore(btn, selectEl);
        selectEl.addEventListener('change', function () { syncPickButton(selectEl); });
        syncPickButton(selectEl);
    }

    function setCatalog(items, specInks) {
        _catalog = items || [];
        _byId = {};
        _labels = {};
        _catalog.forEach(function (s) {
            if (s.id) { _byId[s.id] = s; _labels[s.id] = s.label || s.id; }
        });
        if (specInks) _specInks = specInks;
    }

    function initDnaStylePickers(catalog, specInks) {
        setCatalog(catalog, specInks);
        wrapSelect(document.getElementById('dnaRemixStyleA'), '');
        wrapSelect(document.getElementById('dnaRemixStyleB'), '');
        wrapSelect(document.getElementById('userImportStyleOverride'), '');
        if (!specInks) {
            // Fetch ink swatches once if the caller didn't pass them
            // (shared catalog promise from user-imports.js when available).
            (window.fetchDnaStylesOnce
                ? window.fetchDnaStylesOnce()
                : fetch('/api/user-imports/dna-styles').then(function (r) { return r.json(); }))
                .then(function (d) { if (d && d.spec_inks) _specInks = d.spec_inks; })
                .catch(function () {});
        }
    }

    window.setDnaStylePickerCatalog = setCatalog;
    window.initDnaStylePickers = initDnaStylePickers;
    window.syncDnaStylePickButton = syncPickButton;
    window.openDnaStylePicker = openPanel;
    window.getDnaPaletteOverrides = function () { return JSON.parse(JSON.stringify(_overrides)); };
})();
