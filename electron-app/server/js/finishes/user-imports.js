// SHOKK DROP — Import DNA + library merge (internal api: user-imports).
(function () {
    'use strict';

    var GROUP_NAME = 'SHOKK DROP';
    var DROP_PACK_EXT = '.spbdrop';
    var LEGACY_DROP_PACK_EXT = '.spbshokk';
    var _userImports = [];
    var _libThumbStamp = Date.now(); // cache-bust library thumbs per data refresh, not per render
    var _lastPreview = null;
    var _dnaStyleLabels = {};

    function _formatDnaStyle(styleId) {
        if (!styleId) return '';
        if (_dnaStyleLabels[styleId]) return _dnaStyleLabels[styleId];
        return String(styleId).replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    }

    function _gauntletChip(e) {
        var dna = e && e.import_dna;
        if (!dna || !dna.gauntlet_stats) return '';
        var passed = !!dna.gauntlet_passed;
        var color = passed ? '#8fd8a0' : '#f0a8a8';
        return ' <span style="color:' + color + ';font-weight:700;" title="Import DNA gauntlet ' +
            (passed ? 'PASS' : 'FAIL') + '">' + (passed ? '✓' : '!') + '</span>';
    }

    function _kindLabel(kind) {
        if (kind === 'pattern') return 'pattern';
        if (kind === 'spec_overlay') return 'spec overlay';
        return 'paint';
    }

    function _entrySpecStrengths(e) {
        var s = (e && e.spec_channel_strengths) || {};
        if (s.M != null || s.R != null || s.C != null) {
            return {
                M: s.M != null ? s.M : 1,
                R: s.R != null ? s.R : 1,
                C: s.C != null ? s.C : 1
            };
        }
        var ch = (e && e.spec_channel) || 'M';
        var out = { M: 0, R: 0, C: 0 };
        if (ch === 'R') out.R = 1;
        else if (ch === 'C' || ch === 'Cc') out.C = 1;
        else out.M = 1;
        return out;
    }

    function _specStrengthLabel(e) {
        var s = _entrySpecStrengths(e);
        return 'M ' + Math.round(s.M * 100) + '% · R ' + Math.round(s.R * 100) + '% · CC ' + Math.round(s.C * 100) + '%';
    }

    function _specStrengthsFromUi() {
        function read(id, fallback) {
            var el = document.getElementById(id);
            if (!el) return fallback;
            var pct = parseFloat(el.value);
            if (!isFinite(pct)) return fallback;
            return Math.max(0, Math.min(2, pct / 100));
        }
        return {
            spec_m: read('userImportSpecM', 1),
            spec_r: read('userImportSpecR', 1),
            spec_c: read('userImportSpecC', 1)
        };
    }

    function _setSpecStrengthUi(strengths) {
        var s = strengths || { M: 1, R: 1, C: 1 };
        function set(id, valId, v) {
            var el = document.getElementById(id);
            var lab = document.getElementById(valId);
            var pct = Math.round(Math.max(0, Math.min(2, Number(v) || 0)) * 100);
            if (el) el.value = String(pct);
            if (lab) lab.textContent = pct + '%';
        }
        set('userImportSpecM', 'userImportSpecMVal', s.M);
        set('userImportSpecR', 'userImportSpecRVal', s.R);
        set('userImportSpecC', 'userImportSpecCVal', s.C);
    }

    function _assignSpecialGroup(groupName, ids) {
        if (!groupName || !ids || !ids.length) return;
        if (typeof SPECIAL_GROUPS !== 'undefined') {
            SPECIAL_GROUPS[groupName] = ids.slice();
        }
        if (typeof MONOLITHIC_GROUPS !== 'undefined') {
            MONOLITHIC_GROUPS[groupName] = ids.slice();
        }
        if (typeof _expandedGroups !== 'undefined' && _expandedGroups.add) {
            _expandedGroups.add(groupName);
        }
    }

    function _mergeIntoPicker(entries) {
        if (!Array.isArray(entries)) return;
        _userImports = entries;
        _libThumbStamp = Date.now();

        var paintEntries = entries.filter(function (e) {
            return !e.kind || e.kind === 'paint_monolithic';
        });
        var patternEntries = entries.filter(function (e) { return e.kind === 'pattern'; });

        if (typeof MONOLITHICS !== 'undefined') {
            paintEntries.forEach(function (e) {
                var desc = (e.import_dna && e.import_dna.style)
                    ? ('Import DNA: ' + _formatDnaStyle(e.import_dna.style))
                    : 'Shokk Drop import';
                var existing = null;
                for (var i = 0; i < MONOLITHICS.length; i++) {
                    if (MONOLITHICS[i].id === e.id) { existing = MONOLITHICS[i]; break; }
                }
                if (existing) {
                    // The V5 finish-data sync pre-registers ui_* ids as bare
                    // auto-titled stubs ("Ui Groovy Waves", gray swatch, no
                    // desc) BEFORE this merge runs — skipping here left drops
                    // looking broken in the booth picker. Upgrade the stub in
                    // place with the drop's real name/swatch/DNA (same id,
                    // same render path — display metadata only).
                    if (e.name) existing.name = e.name;
                    if (!existing.desc) existing.desc = desc;
                    if (e.swatch) existing.swatch = e.swatch;
                    if (!existing.category) existing.category = GROUP_NAME;
                    if (!existing.tags || !existing.tags.length) existing.tags = ['user-import', 'shokk-drop'];
                } else {
                    MONOLITHICS.push({
                        id: e.id,
                        name: e.name || e.id,
                        desc: desc,
                        swatch: e.swatch || '#6688aa',
                        category: GROUP_NAME,
                        tags: ['user-import', 'shokk-drop']
                    });
                }
            });
            _assignSpecialGroup(GROUP_NAME, paintEntries.map(function (e) { return e.id; }));
        }

        if (typeof PATTERNS !== 'undefined') {
            patternEntries.forEach(function (e) {
                var existingP = null;
                for (var j = 0; j < PATTERNS.length; j++) {
                    if (PATTERNS[j].id === e.id) { existingP = PATTERNS[j]; break; }
                }
                if (existingP) {
                    // Same stub-upgrade as MONOLITHICS above (display only).
                    if (e.name) existingP.name = e.name;
                    if (!existingP.desc) existingP.desc = 'User import pattern';
                    if (e.swatch) existingP.swatch = e.swatch;
                    if (!existingP.category) existingP.category = GROUP_NAME;
                } else {
                    PATTERNS.push({
                        id: e.id,
                        name: e.name || e.id,
                        desc: 'User import pattern',
                        swatch: e.swatch || '#555566',
                        category: GROUP_NAME,
                        tags: ['user-import', 'shokk-drop']
                    });
                }
            });
            if (typeof PATTERN_GROUPS !== 'undefined' && patternEntries.length) {
                PATTERN_GROUPS[GROUP_NAME] = patternEntries.map(function (e) { return e.id; });
            }
            _assignSpecialGroup(GROUP_NAME + ' Patterns', patternEntries.map(function (e) { return e.id; }));
        }

        if (typeof SPEC_PATTERNS !== 'undefined') {
            entries.filter(function (e) { return e.kind === 'spec_overlay'; }).forEach(function (e) {
                var idx = SPEC_PATTERNS.findIndex(function (p) { return p.id === e.id; });
                var row = {
                    id: e.id,
                    name: e.name || e.id,
                    desc: 'User spec overlay · ' + _specStrengthLabel(e),
                    category: GROUP_NAME,
                    swatch: e.swatch || '#8899aa',
                    tags: ['user-import', 'spec-overlay'],
                    defaultChannels: 'MRC'
                };
                if (idx >= 0) SPEC_PATTERNS[idx] = Object.assign({}, SPEC_PATTERNS[idx], row);
                else SPEC_PATTERNS.push(row);
            });
            if (typeof SPEC_PATTERN_GROUPS !== 'undefined') {
                var ovIds = entries.filter(function (e) { return e.kind === 'spec_overlay'; }).map(function (e) { return e.id; });
                if (ovIds.length) SPEC_PATTERN_GROUPS[GROUP_NAME] = ovIds;
            }
        }

        if (typeof FINISH_TYPE_BY_ID !== 'undefined') {
            paintEntries.forEach(function (e) { FINISH_TYPE_BY_ID[e.id] = 'monolithic'; });
            patternEntries.forEach(function (e) { FINISH_TYPE_BY_ID[e.id] = 'pattern'; });
        }

        if (typeof renderFinishLibrary === 'function') renderFinishLibrary();
        if (typeof buildFinishBrowser === 'function') buildFinishBrowser();
        if (paintEntries.length && typeof _libraryActiveGroupByTab !== 'undefined') {
            _libraryActiveGroupByTab.specials = GROUP_NAME;
        }
        renderUserImportsList();
    }

    function renderUserImportsList() {
        var list = document.getElementById('userImportsList');
        if (!list) return;
        if (!_userImports.length) {
            list.innerHTML = '<div style="font-size:9px;color:var(--text-dim);">No imports yet.</div>';
            return;
        }
        list.innerHTML = _userImports.map(function (e) {
            var dna = e.import_dna && e.import_dna.style
                ? (' · ' + _formatDnaStyle(e.import_dna.style)) : '';
            var canReDna = (!e.kind || e.kind === 'paint_monolithic') &&
                (e.spec_mode || '').indexOf('auto') === 0;
            var specRow = '';
            if (e.kind === 'spec_overlay') {
                var s = _entrySpecStrengths(e);
                specRow = '<div style="display:grid;gap:3px;margin:4px 0 2px 0;font-size:8px;">' +
                    '<div style="color:var(--text-dim);">' + _specStrengthLabel(e) + '</div>' +
                    '<label style="display:flex;align-items:center;gap:4px;color:#f88;">M<input type="range" min="0" max="200" value="' + Math.round(s.M * 100) + '" style="flex:1;" onchange="updateSpecOverlayChannels(\'' + e.id + '\', {spec_m:this.value/100})"></label>' +
                    '<label style="display:flex;align-items:center;gap:4px;color:#8f8;">R<input type="range" min="0" max="200" value="' + Math.round(s.R * 100) + '" style="flex:1;" onchange="updateSpecOverlayChannels(\'' + e.id + '\', {spec_r:this.value/100})"></label>' +
                    '<label style="display:flex;align-items:center;gap:4px;color:#88f;">CC<input type="range" min="0" max="200" value="' + Math.round(s.C * 100) + '" style="flex:1;" onchange="updateSpecOverlayChannels(\'' + e.id + '\', {spec_c:this.value/100})"></label>' +
                    '</div>';
            }
            // Row name is clickable where the full channel preview exists
            // (SHOKK DROP page) — same preview the gallery cards open.
            var clickable = (typeof window.showShokkDropSavedPreview === 'function');
            return '<div style="margin:6px 0 8px;font-size:9px;border-bottom:1px solid var(--line,#2b3645);padding-bottom:6px;">' +
                '<div style="display:flex;align-items:center;gap:6px;">' +
                '<img src="/api/user-imports/preview-image/' + e.id + '?t=' + _libThumbStamp + '" loading="lazy" decoding="async" alt="" ' +
                'style="width:26px;height:26px;object-fit:cover;border-radius:3px;flex-shrink:0;background:#0a0c10;' + (clickable ? 'cursor:pointer;' : '') + '"' +
                (clickable ? ' onclick="showShokkDropSavedPreview(\'' + e.id + '\')"' : '') + '>' +
                '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;' + (clickable ? 'cursor:pointer;' : '') + '" ' +
                'title="' + e.id + (clickable ? ' — click to preview' : '') + '"' +
                (clickable ? ' onclick="showShokkDropSavedPreview(\'' + e.id + '\')"' : '') + '>' +
                (e.name || e.id) + ' <span style="color:var(--text-dim);">(' + _kindLabel(e.kind) + dna + ')</span>' +
                _gauntletChip(e) + '</span>' +
                (canReDna ? '<button type="button" class="btn btn-sm" style="font-size:8px;padding:1px 6px;" ' +
                'onclick="rebakeUserImportDna(\'' + e.id + '\')">Re-DNA</button>' : '') +
                '<a href="/api/user-imports/export/' + e.id + '" download style="font-size:8px;color:var(--accent-cyan);">' + DROP_PACK_EXT + '</a>' +
                '<button type="button" class="btn btn-sm" style="font-size:8px;padding:1px 6px;border-color:#f66;color:#f88;" ' +
                'onclick="deleteUserImport(\'' + e.id + '\')">Del</button></div>' +
                specRow + '</div>';
        }).join('');
    }

    function showPreviewPanel(data) {
        _lastPreview = data;
        var box = document.getElementById('userImportPreviewBox');
        var meta = document.getElementById('userImportPreviewMeta');
        var actions = document.getElementById('userImportPreviewActions');
        if (!box) return;
        if (data && (data.preview_paint || data.preview)) {
            if (typeof renderShokkDropPreviewPanel === 'function') {
                renderShokkDropPreviewPanel(box, data);
            } else {
                box.innerHTML =
                    '<img src="' + (data.preview || data.preview_paint) + '" alt="Import preview" style="width:100%;border-radius:4px;border:1px solid var(--border-color);">';
            }
            if (meta) {
                if (data.dna) {
                    meta.textContent = 'DNA style: ' + _formatDnaStyle(data.dna.style) +
                        (data.dna.material_hint && data.dna.material_hint !== 'generic'
                            ? ' · material: ' + data.dna.material_hint : '') +
                        ' · gauntlet ' + (data.dna.gauntlet_passed ? 'PASS' : ('pass ' + data.dna.gauntlet_passes)) +
                        ' · suggest: ' + (data.suggested_intent || 'paint');
                } else if (data.spec_channel_strengths) {
                    meta.textContent = (data.name || 'Preview') + ' · spec overlay · ' +
                        _specStrengthLabel({ spec_channel_strengths: data.spec_channel_strengths });
                } else {
                    meta.textContent = (data.name || 'Preview') + ' · suggest: ' + (data.suggested_intent || 'paint');
                }
            }
            if (actions) {
                // Restore the default DNA-commit handler in case a paint+spec SET
                // live preview repointed this shared button at importPaintSpecSet().
                var dnaBtn = actions.querySelector('button');
                if (dnaBtn) { dnaBtn.textContent = 'Commit drop'; dnaBtn.setAttribute('onclick', 'commitPendingUserImport()'); }
                actions.style.display = '';
            }
        } else {
            box.innerHTML = '';
            if (meta) meta.textContent = '';
            if (actions) actions.style.display = 'none';
        }
    }

    function loadUserImports() {
        return fetch('/api/user-imports')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                _mergeIntoPicker(data.entries || []);
                return data;
            })
            .catch(function () { return { entries: [] }; });
    }

    function _formFromFiles(fileList, extra) {
        var fd = new FormData();
        Object.keys(extra || {}).forEach(function (k) {
            if (extra[k] != null && extra[k] !== '') fd.append(k, extra[k]);
        });
        for (var i = 0; i < fileList.length; i++) fd.append('files', fileList[i]);
        return fd;
    }

    function _styleOverride() {
        var el = document.getElementById('userImportStyleOverride');
        return el ? el.value.trim() : '';
    }

    // One shared fetch of the DNA style catalog per page load. Three modules
    // (this one, shokk-world, dna-presets) each hit /dna-styles on boot —
    // identical payload, three server round-trips. They now share this promise.
    var _dnaStylesPromise = null;
    function fetchDnaStylesOnce() {
        if (!_dnaStylesPromise) {
            _dnaStylesPromise = fetch('/api/user-imports/dna-styles')
                .then(function (r) { return r.json(); })
                .catch(function (err) {
                    _dnaStylesPromise = null; // allow a retry next call
                    throw err;
                });
        }
        return _dnaStylesPromise;
    }
    window.fetchDnaStylesOnce = fetchDnaStylesOnce;

    function loadDnaStyleOptions() {
        var sel = document.getElementById('userImportStyleOverride');
        if (!sel || sel.options.length > 1) return Promise.resolve();
        return fetchDnaStylesOnce()
            .then(function (data) {
                var items = data.catalog || (data.styles || []).map(function (id) {
                    return { id: id, label: id.replace(/_/g, ' '), description: '' };
                });
                _dnaStyleLabels = {};
                var countEl = document.getElementById('dnaStyleCount');
                if (countEl) countEl.textContent = '(' + items.length + ')';
                items.forEach(function (s) {
                    if (s.id && s.label) _dnaStyleLabels[s.id] = s.label;
                    var opt = document.createElement('option');
                    opt.value = s.id;
                    var desc = s.description || '';
                    opt.textContent = desc ? (s.label + ' — ' + desc) : s.label;
                    opt.title = desc || s.label;
                    sel.appendChild(opt);
                });
                if (typeof fillRemixSelects === 'function') {
                    fillRemixSelects(items, '');
                }
                if (typeof initDnaStylePickers === 'function') {
                    initDnaStylePickers(items, data.spec_inks);
                }
            })
            .catch(function () { /* auto-only fallback */ });
    }

    function previewSpecOverlayFiles(fileList, displayName) {
        var strengths = _specStrengthsFromUi();
        return fetch('/api/user-imports/preview', {
            method: 'POST',
            body: _formFromFiles(fileList, Object.assign({
                name: displayName || '',
                kind: 'spec_overlay'
            }, strengths))
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Preview failed');
                showPreviewPanel(Object.assign({ preview_kind: 'spec_overlay' }, res.body));
                if (res.body.spec_channel_strengths) _setSpecStrengthUi(res.body.spec_channel_strengths);
                return res.body;
            });
    }

    function previewUserImportFiles(fileList, displayName) {
        var vibe = document.getElementById('userImportVibeRef');
        return fetch('/api/user-imports/preview', {
            method: 'POST',
            body: _formFromFiles(fileList, {
                name: displayName || '',
                vibe_ref: vibe ? vibe.value.trim() : '',
                style_override: _styleOverride()
            })
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Preview failed');
                showPreviewPanel(res.body);
                var kindSel = document.getElementById('userImportKind');
                if (kindSel && res.body.suggested_intent) {
                    kindSel.value = res.body.suggested_intent === 'pattern' ? 'pattern'
                        : (res.body.suggested_intent === 'spec_overlay' ? 'spec_overlay' : 'paint_monolithic');
                    updateUserImportsStatus();
                }
                return res.body;
            });
    }

    function importUserFinishFiles(fileList, displayName, kind) {
        var alsoPat = document.getElementById('userImportAlsoPattern');
        var vibe = document.getElementById('userImportVibeRef');
        var payload = {
            name: displayName || '',
            kind: kind || 'paint_monolithic',
            vibe_ref: vibe ? vibe.value.trim() : '',
            style_override: _styleOverride(),
            also_pattern: alsoPat && alsoPat.checked ? '1' : '0'
        };
        if ((kind || 'paint_monolithic') === 'spec_overlay') {
            Object.assign(payload, _specStrengthsFromUi());
        }
        return fetch('/api/user-imports/import', {
            method: 'POST',
            body: _formFromFiles(fileList, payload)
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Import failed');
                showPreviewPanel(null);
                return loadUserImports().then(function () { return res.body; });
            });
    }

    function importUserFinishPack(file) {
        var fd = new FormData();
        fd.append('pack', file);
        return fetch('/api/user-imports/import-pack', { method: 'POST', body: fd })
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Pack import failed');
                return loadUserImports().then(function () { return res.body; });
            });
    }

    function processUserImportInbox() {
        var alsoPat = document.getElementById('userImportAlsoPattern');
        // This button used to give ZERO feedback — success, empty inbox and
        // failure all looked identical (nothing happened on screen).
        var toast = (typeof showToast === 'function') ? showToast : function () {};
        toast('Checking the inbox folder…', 'info');
        return fetch('/api/user-imports/process-inbox', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ also_pattern: !!(alsoPat && alsoPat.checked) })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                var n = (data.imported || []).length;
                toast(n
                    ? ('Imported ' + n + ' image(s) from the inbox')
                    : 'Inbox is empty — put PNG/JPG/WebP files in ShokkerPaintBooth\\user_imports\\inbox first',
                    n ? 'success' : 'info');
                return loadUserImports().then(function () { return data; });
            })
            .catch(function (err) {
                toast('Inbox import failed: ' + err.message, 'error');
                throw err;
            });
    }

    function updateSpecOverlayChannels(id, partial) {
        var toast = (typeof showToast === 'function') ? showToast : function () {};
        return fetch('/api/user-imports/update-spec-channels', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Object.assign({ id: id }, partial || {}))
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Update failed');
                toast('Updated M/R/CC for ' + id, 'success');
                return loadUserImports().then(updateUserImportsStatus);
            })
            .catch(function (err) { toast('Failed: ' + err.message, 'error'); });
    }

    function rebakeUserImportDna(id) {
        var vibe = document.getElementById('userImportVibeRef');
        var toast = (typeof showToast === 'function') ? showToast : function () {};
        toast('Re-running Import DNA…', 'info');
        return fetch('/api/user-imports/rebake-dna', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id,
                vibe_ref: vibe ? vibe.value.trim() : '',
                style_override: _styleOverride()
            })
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Re-DNA failed');
                var entry = res.body.entry || {};
                var dna = entry.import_dna || {};
                toast('Re-DNA: ' + (dna.style || 'done') +
                    (dna.gauntlet_passed ? ' · gauntlet PASS' : ''), 'success');
                return loadUserImports().then(updateUserImportsStatus);
            })
            .catch(function (err) { toast('Failed: ' + err.message, 'error'); });
    }

    function deleteUserImport(id) {
        // Confirm with the drop's human name (the slug id alone reads like a
        // different item — "ui_x_1862_2" vs the card's "1862").
        var entry = null;
        for (var i = 0; i < _userImports.length; i++) {
            if (_userImports[i].id === id) { entry = _userImports[i]; break; }
        }
        var label = (entry && entry.name && entry.name !== id)
            ? ('"' + entry.name + '" (' + id + ')')
            : ('"' + id + '"');
        if (!confirm('Delete drop ' + label + '? This removes it from the library and the booth picker.')) return Promise.resolve();
        return fetch('/api/user-imports/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        }).then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) throw new Error(data.error);
                var toast = (typeof showToast === 'function') ? showToast : function () {};
                toast('Deleted ' + id, 'success');
                return loadUserImports().then(updateUserImportsStatus);
            });
    }

    function _isDropPackName(name) {
        var n = (name || '').toLowerCase();
        return n.endsWith(DROP_PACK_EXT) || n.endsWith(LEGACY_DROP_PACK_EXT);
    }

    function _isImportImageFile(file) {
        if (!file || !file.name) return false;
        if (_isDropPackName(file.name)) return true;
        if (/\.(png|jpe?g|webp|tga|bmp)$/i.test(file.name)) return true;
        return (file.type || '').indexOf('image/') === 0;
    }

    function processUserImportFileList(fileList, previewOnly, displayName) {
        var files = Array.prototype.slice.call(fileList || []);
        if (!files.length) return Promise.resolve();
        var kindSel = document.getElementById('userImportKind');
        var kind = kindSel ? kindSel.value : 'paint_monolithic';
        var pack = files.length === 1 && _isDropPackName(files[0].name);
        var name = displayName;
        if (name == null || name === '') {
            name = pack ? '' : files[0].name.replace(/\.[^.]+$/, '');
        }
        var toast = (typeof showToast === 'function') ? showToast : function (m) { console.log(m); };
        if (pack) {
            toast('Importing pack…', 'info');
            return importUserFinishPack(files[0]).then(function (body) {
                toast('Pack imported', 'success');
                return updateUserImportsStatus().then(function () { return body; });
            }).catch(function (err) { toast('Failed: ' + err.message, 'error'); throw err; });
        }
        toast(kind === 'spec_overlay' ? 'Analyzing spec overlay…' : 'Running Import DNA…', 'info');
        var chain = previewOnly !== false && (kind === 'paint_monolithic' || kind === 'spec_overlay')
            ? (kind === 'spec_overlay'
                ? previewSpecOverlayFiles(files, name)
                : previewUserImportFiles(files, name))
            : Promise.resolve(null);
        return chain.then(function (preview) {
            if (preview && (kind === 'paint_monolithic' || kind === 'spec_overlay')) {
                window._pendingUserImportFiles = files;
                window._pendingUserImportName = name;
                window._pendingUserImportKind = kind;
                toast('Preview ready — click Commit drop', 'success');
                return preview;
            }
            return importUserFinishFiles(files, name, kind).then(function () {
                toast('Imported to SHOKK DROP', 'success');
                return updateUserImportsStatus();
            });
        }).catch(function (err) { toast('Failed: ' + err.message, 'error'); throw err; });
    }

    function bindUserImportSidebarDropZone(el) {
        if (!el || el.dataset.sidebarDropBound) return;
        el.dataset.sidebarDropBound = '1';
        el.addEventListener('dragover', function (e) {
            e.preventDefault();
            el.classList.add('sidebar-drop-active');
        });
        el.addEventListener('dragleave', function (e) {
            if (!el.contains(e.relatedTarget)) el.classList.remove('sidebar-drop-active');
        });
        el.addEventListener('drop', function (e) {
            e.preventDefault();
            el.classList.remove('sidebar-drop-active');
            var files = [];
            if (e.dataTransfer && e.dataTransfer.files) {
                for (var i = 0; i < e.dataTransfer.files.length; i++) {
                    var f = e.dataTransfer.files[i];
                    if (_isImportImageFile(f)) files.push(f);
                }
            }
            if (!files.length) {
                var toast = (typeof showToast === 'function') ? showToast : function () {};
                toast('Drop PNG, JPG, WebP, or .spbdrop here', 'info');
                return;
            }
            processUserImportFileList(files, true);
        });
    }

    function openUserImportDialog(previewOnly) {
        var kindSel = document.getElementById('userImportKind');
        var kind = kindSel ? kindSel.value : 'paint_monolithic';
        var input = document.createElement('input');
        input.type = 'file';
        input.multiple = kind === 'paint_monolithic';
        input.accept = 'image/png,image/jpeg,image/webp,' + DROP_PACK_EXT + ',' + LEGACY_DROP_PACK_EXT;
        input.onchange = function () {
            if (!input.files || !input.files.length) return;
            var files = Array.prototype.slice.call(input.files);
            var pack = files.length === 1 && _isDropPackName(files[0].name);
            var name = '';
            if (!pack && files.length >= 1) {
                name = prompt('Name (optional):', files[0].name.replace(/\.[^.]+$/, ''));
                if (name === null) return;
            }
            processUserImportFileList(files, previewOnly !== false, name);
        };
        input.click();
    }

    function commitPendingUserImport() {
        var files = window._pendingUserImportFiles;
        if (!files || !files.length) {
            openUserImportDialog(false);
            return;
        }
        // Guard the in-flight window: the button stayed clickable during the
        // multi-second DNA bake, and a second click imported a duplicate.
        var actions = document.getElementById('userImportPreviewActions');
        var btn = actions ? actions.querySelector('button') : null;
        if (btn && btn.disabled) return;
        var prevLabel = btn ? btn.textContent : '';
        if (btn) { btn.disabled = true; btn.textContent = 'Committing…'; }
        function releaseBtn() {
            if (btn) { btn.disabled = false; btn.textContent = prevLabel; }
        }
        var toast = (typeof showToast === 'function') ? showToast : function () {};
        var kindSel = document.getElementById('userImportKind');
        var kind = window._pendingUserImportKind || (kindSel ? kindSel.value : 'paint_monolithic');
        toast('Committing import…', 'info');
        importUserFinishFiles(files, window._pendingUserImportName || '', kind)
            .then(function () {
                releaseBtn();
                window._pendingUserImportFiles = null;
                window._pendingUserImportKind = null;
                toast('Imported to SHOKK DROP', 'success');
                updateUserImportsStatus();
            }).catch(function (err) {
                releaseBtn();
                toast('Failed: ' + err.message, 'error');
            });
    }

    function updateUserImportsStatus() {
        var el = document.getElementById('userImportsStatus');
        if (el) {
            // On the SHOKK DROP page itself, "Open Shokk Drop…" is confusing —
            // the user is already here. Point at the actual next action instead.
            var onDropPage = (window.location.pathname || '').indexOf('shokk-drop') >= 0;
            el.textContent = _userImports.length
                ? (_userImports.length + ' drop(s) · Import DNA active')
                : (onDropPage
                    ? 'No drops yet — drag art onto this sidebar to start'
                    : 'Open Shokk Drop to import & share');
        }
        renderUserImportsList();
        var chRow = document.getElementById('userImportSpecChannelRow');
        var kindSel = document.getElementById('userImportKind');
        if (chRow && kindSel) chRow.style.display = kindSel.value === 'spec_overlay' ? '' : 'none';
        var patRow = document.getElementById('userImportAlsoPatternRow');
        if (patRow && kindSel) patRow.style.display = kindSel.value === 'paint_monolithic' ? '' : 'none';
        // style_override + vibe_ref only reach the backend for kinds routed to
        // import_paint_files() — paint_monolithic AND car_template (see
        // server_routes/user_import_routes.py api_user_imports_import else-branch).
        // Pattern / spec_overlay / paint_spec_set imports ignore both, so
        // showing the rows there was dead UI.
        var dnaKinds = { paint_monolithic: 1, car_template: 1 };
        var vibeRow = document.getElementById('userImportVibeRow');
        if (vibeRow && kindSel) vibeRow.style.display = dnaKinds[kindSel.value] ? '' : 'none';
        var styleRow = document.getElementById('userImportStyleRow');
        if (styleRow && kindSel) styleRow.style.display = dnaKinds[kindSel.value] ? '' : 'none';
        var ctHint = document.getElementById('userImportCarTemplateHint');
        if (ctHint && kindSel) ctHint.style.display = kindSel.value === 'car_template' ? '' : 'none';
    }

    window.formatUserImportDnaStyle = _formatDnaStyle;
    window.updateSpecOverlayChannels = updateSpecOverlayChannels;
    window.processUserImportFileList = processUserImportFileList;
    window.bindUserImportSidebarDropZone = bindUserImportSidebarDropZone;
    window.rebakeUserImportDna = rebakeUserImportDna;
    window.loadUserImports = loadUserImports;
    window.openUserImportDialog = openUserImportDialog;
    window.commitPendingUserImport = commitPendingUserImport;
    window.processUserImportInbox = processUserImportInbox;
    window.deleteUserImport = deleteUserImport;
    window.updateUserImportsStatus = updateUserImportsStatus;

    function applyStagedMonoFromUrl() {
        try {
            var params = new URLSearchParams(window.location.search);
            var monoId = params.get('stagedMono');
            if (!monoId) return;
            // wholeCar=1 (SHOKK DROP "Car template" type, 2026-05-31): the staged
            // finish is a COMPLETE car (paint + spec for the whole body). Merge it
            // as a full-body top zone instead of patching Zone 1, so it covers the
            // entire car without leaking through the painter's existing zones.
            var wholeCar = (params.get('wholeCar') === '1' || params.get('wholeCar') === 'true');
            loadUserImports().then(function () {
                if (typeof _libraryActiveGroupByTab !== 'undefined') {
                    _libraryActiveGroupByTab.specials = GROUP_NAME;
                }
                var toastFn = (typeof showToast === 'function') ? showToast : function () {};
                if (wholeCar && typeof window._spbMergeCarTemplateOnTop === 'function') {
                    window._spbMergeCarTemplateOnTop(monoId, null);
                    toastFn('Loaded car template as a full-body zone — your previous zones are preserved underneath (delete that zone to restore them). Hit RENDER.', 'success');
                } else {
                    if (typeof applyFinishFromBrowser === 'function') {
                        applyFinishFromBrowser(null, null, monoId);
                    } else if (typeof selectMonolithic === 'function') {
                        selectMonolithic(monoId);
                    }
                    toastFn('Staged finish ' + monoId + ' — hit RENDER (uncheck Drop as paint source in World for spec-only)', 'success');
                }
                if (typeof triggerPreviewRender === 'function') triggerPreviewRender();
            });
        } catch (e) { /* ignore */ }
    }

    function boot() {
        var kindSel = document.getElementById('userImportKind');
        if (kindSel) kindSel.addEventListener('change', updateUserImportsStatus);
        loadDnaStyleOptions().then(function () { return loadUserImports(); }).then(function () {
            updateUserImportsStatus();
            applyStagedMonoFromUrl();
        });
        bindUserImportSidebarDropZone(document.querySelector('aside'));
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') loadUserImports();
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
