(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var getZones = typeof deps.getZones === 'function' ? deps.getZones : function() { return []; };
        var showToast = typeof deps.showToast === 'function' ? deps.showToast : function() {};
        var updateZonePanel = typeof deps.updateZonePanel === 'function' ? deps.updateZonePanel : function() {};

        // FINISH MIXER - Blend 2-3 finishes at custom ratios
        // ================================================================
        
        var _mixerState = {
            zoneIndex: 0,
            slots: [
                { id: 'chrome', weight: 50 },
                { id: 'candy_burgundy', weight: 50 }
            ],
            previewImg: null,
            panelOpen: false,
            mixMode: 'both',      // 'both', 'color', 'spec'
            activeSlot: -1,      // which slot is picking a base (-1 = none)
            pickerFilter: '',     // search filter text
            pickerCategory: ''    // category filter
        };
        
        function openFinishMixer(zoneIndex) {
            _mixerState.zoneIndex = zoneIndex;
            _mixerState.panelOpen = true;
            _mixerState.activeSlot = -1;
            var zones = getZones();
            var z = (zones && zones[zoneIndex]) ? zones[zoneIndex] : null;
            if (z && z.base) {
                _mixerState.slots[0].id = z.base;
            }
            _renderMixerPanel();
        }
        
        function closeMixerPanel() {
            _mixerState.panelOpen = false;
            _mixerState.activeSlot = -1;
            var el = document.getElementById('finishMixerOverlay');
            if (el) el.remove();
        }
        
        function _mixerGetBaseName(baseId) {
            if (typeof BASES !== 'undefined') {
                for (var i = 0; i < BASES.length; i++) {
                    if (BASES[i].id === baseId) return BASES[i].name;
                }
            }
            if (typeof MONOLITHICS !== 'undefined') {
                for (var i = 0; i < MONOLITHICS.length; i++) {
                    if (MONOLITHICS[i].id === baseId) return MONOLITHICS[i].name;
                }
            }
            if (typeof _customMixFinishes !== 'undefined') {
                for (var j = 0; j < _customMixFinishes.length; j++) {
                    if (_customMixFinishes[j].id === baseId) return _customMixFinishes[j].name;
                }
            }
            return baseId;
        }
        
        function _mixerGetBaseSwatch(baseId) {
            if (typeof BASES !== 'undefined') {
                for (var i = 0; i < BASES.length; i++) {
                    if (BASES[i].id === baseId) return BASES[i].swatch || '#444';
                }
            }
            if (typeof MONOLITHICS !== 'undefined') {
                for (var i = 0; i < MONOLITHICS.length; i++) {
                    if (MONOLITHICS[i].id === baseId) return MONOLITHICS[i].swatch || '#666';
                }
            }
            return '#e844e8';
        }
        
        function _normalizeMixerWeights() {
            var total = 0;
            for (var i = 0; i < _mixerState.slots.length; i++) total += _mixerState.slots[i].weight;
            if (total <= 0) {
                var eq = Math.round(100 / _mixerState.slots.length);
                for (var j = 0; j < _mixerState.slots.length; j++) _mixerState.slots[j].weight = eq;
            }
        }
        
        function _mixerSlotChange(idx, newId) {
            _mixerState.slots[idx].id = newId;
            _mixerState.activeSlot = -1;
            _renderMixerPanel();
        }
        
        function _mixerWeightChange(idx, val) {
            _mixerState.slots[idx].weight = Math.max(0, Math.min(100, parseInt(val) || 0));
            var lbl = document.getElementById('mixerWtLabel' + idx);
            if (lbl) lbl.textContent = _mixerState.slots[idx].weight + '%';
        }
        
        function _mixerAddSlot() {
            if (_mixerState.slots.length >= 3) return;
            _mixerState.slots.push({ id: 'carbon_base', weight: 33 });
            _renderMixerPanel();
        }
        
        function _mixerRemoveSlot(idx) {
            if (_mixerState.slots.length <= 2) return;
            _mixerState.slots.splice(idx, 1);
            _renderMixerPanel();
        }
        
        function _mixerOpenPicker(slotIdx) {
            _mixerState.activeSlot = slotIdx;
            _mixerState.pickerFilter = '';
            _mixerState.pickerCategory = '';
            _renderMixerPanel();
        }
        
        function _mixerClosePicker() {
            _mixerState.activeSlot = -1;
            _renderMixerPanel();
        }
        
        function _mixerFilterBases(text) {
            _mixerState.pickerFilter = text.toLowerCase();
            _renderMixerBasePicker();
        }
        
        function _mixerSetCategory(cat) {
            _mixerState.pickerCategory = cat;
            _renderMixerBasePicker();
        }
        
        function _renderMixerBasePicker() {
            var container = document.getElementById('mixerBasePickerGrid');
            if (!container) return;
            var filter = _mixerState.pickerFilter;
            var cat = _mixerState.pickerCategory;
            var baseGroups = (typeof BASE_GROUPS !== 'undefined') ? BASE_GROUPS : {};
            var specialGroups = (typeof SPECIAL_GROUPS !== 'undefined') ? SPECIAL_GROUPS : {};
            // Merge base + special groups for the mixer (specials are valid mix components)
            var groups = {};
            var bKeys = Object.keys(baseGroups);
            for (var bk = 0; bk < bKeys.length; bk++) groups[bKeys[bk]] = baseGroups[bKeys[bk]];
            var sKeys = Object.keys(specialGroups);
            for (var sk = 0; sk < sKeys.length; sk++) {
                // Don't double-prefix keys that already have the star marker.
                var sKey = sKeys[sk].charAt(0) === '\u2605' ? sKeys[sk] : '\u2605 ' + sKeys[sk];
                groups[sKey] = specialGroups[sKeys[sk]];
            }
            var html = '';
        
            // Build list of finishes to show (bases + specials)
            var basesToShow = [];
            if (cat && groups[cat]) {
                // Specific category
                var catIds = groups[cat];
                for (var i = 0; i < catIds.length; i++) {
                    basesToShow.push(catIds[i]);
                }
            } else {
                // All categories
                var groupKeys = Object.keys(groups);
                for (var g = 0; g < groupKeys.length; g++) {
                    var gIds = groups[groupKeys[g]];
                    for (var j = 0; j < gIds.length; j++) {
                        if (basesToShow.indexOf(gIds[j]) < 0) basesToShow.push(gIds[j]);
                    }
                }
            }
        
            // Apply text filter
            if (filter) {
                basesToShow = basesToShow.filter(function(bid) {
                    var name = _mixerGetBaseName(bid).toLowerCase();
                    return name.indexOf(filter) >= 0 || bid.toLowerCase().indexOf(filter) >= 0;
                });
            }
        
            // Add custom mixes
            if (!cat && typeof _customMixFinishes !== 'undefined' && _customMixFinishes.length) {
                for (var c = 0; c < _customMixFinishes.length; c++) {
                    var cid = _customMixFinishes[c].id;
                    if (!filter || _customMixFinishes[c].name.toLowerCase().indexOf(filter) >= 0) {
                        basesToShow.push(cid);
                    }
                }
            }
        
            // Render thumbnail grid - use actual split-view swatch images (same as main picker)
            for (var b = 0; b < basesToShow.length; b++) {
                var bid = basesToShow[b];
                var bname = _mixerGetBaseName(bid);
                var swatchUrl = (typeof getSwatchUrl === 'function') ? getSwatchUrl(bid, '888888', true, 48) : null;
                var fallbackColor = _mixerGetBaseSwatch(bid) || '#444';
                var thumbHtml;
                if (swatchUrl) {
                    thumbHtml = '<img src="' + swatchUrl + '" style="width:48px;height:48px;border-radius:4px;border:1px solid #555;object-fit:cover;background:' + fallbackColor + ';" loading="lazy" onerror="this.style.background=\'' + fallbackColor + '\';this.src=\'\';">';
                } else {
                    thumbHtml = '<div style="width:48px;height:48px;border-radius:4px;border:1px solid #555;background:' + fallbackColor + ';"></div>';
                }
                html += '<div onclick="_mixerSlotChange(' + _mixerState.activeSlot + ', \'' + bid + '\')" '
                    + 'style="cursor:pointer;width:56px;text-align:center;padding:2px;" '
                    + 'title="' + bname + '">'
                    + thumbHtml
                    + '<div style="color:#bbb;font-size:8px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:56px;">' + bname + '</div>'
                    + '</div>';
            }
        
            if (basesToShow.length === 0) {
                html = '<div style="color:#666;padding:20px;text-align:center;">No bases match filter</div>';
            }
        
            container.innerHTML = html;
        }
        
        function _mixerGetZoneColor() {
            // Get the current zone's hex color for the preview (fallback to '888888')
            var zi = _mixerState.zoneIndex;
            var zones = getZones();
            var z = (zones && zones[zi]) ? zones[zi] : null;
            if (z) {
                // pickerColor is always a string hex like '#3366ff'
                if (z.pickerColor && typeof z.pickerColor === 'string') {
                    return z.pickerColor.replace('#', '');
                }
                // z.color can be a string OR an object { color_rgb: [...], tolerance: N }
                if (z.color && typeof z.color === 'string') {
                    return z.color.replace('#', '');
                }
                // If z.color is an object with color_rgb, convert to hex
                if (z.color && z.color.color_rgb) {
                    var rgb = z.color.color_rgb;
                    var r = Math.round(rgb[0] * 255).toString(16).padStart(2, '0');
                    var g = Math.round(rgb[1] * 255).toString(16).padStart(2, '0');
                    var b = Math.round(rgb[2] * 255).toString(16).padStart(2, '0');
                    return r + g + b;
                }
            }
            return '888888';
        }
        
        function _mixerPreview() {
            var ids = [];
            var weights = [];
            for (var i = 0; i < _mixerState.slots.length; i++) {
                ids.push(_mixerState.slots[i].id);
                weights.push(_mixerState.slots[i].weight / 100.0);
            }
            var previewEl = document.getElementById('mixerPreviewImg');
            var statusEl = document.getElementById('mixerStatus');
            var specEl = document.getElementById('mixerSpecInfo');
            if (statusEl) statusEl.textContent = 'Generating paint preview...';
        
            fetch('/api/mix-paint-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ finish_ids: ids, weights: weights, seed: 51, color: _mixerGetZoneColor() }),
                signal: AbortSignal.timeout(30000)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    if (statusEl) statusEl.textContent = 'Error: ' + data.error;
                    return;
                }
                if (previewEl) {
                    previewEl.src = data.image;
                    previewEl.style.display = 'block';
                }
                _mixerState.previewImg = data.image;
                if (statusEl) statusEl.textContent = 'Preview ready';
                if (specEl && data.spec_summary) {
                    specEl.textContent = 'M:' + data.spec_summary.M_avg + '  R:' + data.spec_summary.R_avg + '  CC:' + data.spec_summary.CC_avg;
                    specEl.style.display = 'block';
                }
            })
            .catch(function(err) {
                if (statusEl) statusEl.textContent = 'Error: ' + err.message;
            });
        }
        
        function _mixerApplyDirect() {
            // Apply the mix recipe directly to the active zone without saving
            var zi = _mixerState.zoneIndex;
            var ids = [];
            var weights = [];
            for (var i = 0; i < _mixerState.slots.length; i++) {
                ids.push(_mixerState.slots[i].id);
                weights.push(_mixerState.slots[i].weight / 100.0);
            }
            // Generate a temp name
            var tempName = ids.map(function(id) { return _mixerGetBaseName(id); }).join(' + ');
        
            // Save as temp custom finish, then apply to zone
            var statusEl = document.getElementById('mixerStatus');
            if (statusEl) statusEl.textContent = 'Applying mix...';
        
            fetch('/api/save-custom-finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: tempName, finish_ids: ids, weights: weights, mix_mode: _mixerState.mixMode }),
                signal: AbortSignal.timeout(30000)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    if (statusEl) statusEl.textContent = 'Error: ' + data.error;
                    return;
                }
                // Apply to zone
                var zones = getZones();
                if (zones && zones[zi]) {
                    zones[zi].base = data.id;
                    updateZonePanel(zi);
                }
                _loadCustomFinishes();
                if (statusEl) statusEl.textContent = 'Applied!';
                if (typeof showToast === 'function') showToast('Mix applied: ' + tempName);
                setTimeout(function() { closeMixerPanel(); }, 600);
            })
            .catch(function(err) {
                if (statusEl) statusEl.textContent = 'Error: ' + err.message;
            });
        }
        
        function _mixerSave() {
            var nameInput = document.getElementById('mixerSaveName');
            var name = nameInput ? nameInput.value.trim() : '';
            if (!name) {
                if (typeof showToast === 'function') showToast('Enter a name for your custom finish');
                return;
            }
            var ids = [];
            var weights = [];
            for (var i = 0; i < _mixerState.slots.length; i++) {
                ids.push(_mixerState.slots[i].id);
                weights.push(_mixerState.slots[i].weight / 100.0);
            }
            var statusEl = document.getElementById('mixerStatus');
            if (statusEl) statusEl.textContent = 'Saving...';
        
            fetch('/api/save-custom-finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, finish_ids: ids, weights: weights, mix_mode: _mixerState.mixMode }),
                signal: AbortSignal.timeout(30000)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    if (statusEl) statusEl.textContent = 'Error: ' + data.error;
                    return;
                }
                if (statusEl) statusEl.textContent = 'Saved as ' + data.id + '!';
                if (typeof showToast === 'function') showToast('Custom finish saved: ' + data.name);
                _loadCustomFinishes();
            })
            .catch(function(err) {
                if (statusEl) statusEl.textContent = 'Error: ' + err.message;
            });
        }
        
        function _mixerDeleteCustom(customId) {
            if (!confirm('Delete custom finish "' + customId + '"?')) return;
            fetch('/api/delete-custom-finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: customId }),
                signal: AbortSignal.timeout(8000)
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    if (typeof showToast === 'function') showToast('Error: ' + data.error);
                    return;
                }
                if (typeof showToast === 'function') showToast('Deleted: ' + customId);
                // Remove from BASES array
                if (typeof BASES !== 'undefined') {
                    for (var i = BASES.length - 1; i >= 0; i--) {
                        if (BASES[i].id === customId) { BASES.splice(i, 1); break; }
                    }
                }
                _loadCustomFinishes();
                _renderMixerPanel();
            })
            .catch(function(err) {
                if (typeof showToast === 'function') showToast('Error: ' + err.message);
            });
        }
        
        function _renderMixerPanel() {
            var existing = document.getElementById('finishMixerOverlay');
            if (existing) existing.remove();
        
            var overlay = document.createElement('div');
            overlay.id = 'finishMixerOverlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:10000;display:flex;align-items:center;justify-content:center;';
            overlay.onclick = function(e) { if (e.target === overlay) closeMixerPanel(); };
        
            var picking = _mixerState.activeSlot >= 0;
        
            // === BUILD SLOT CARDS ===
            var slotsHtml = '';
            for (var i = 0; i < _mixerState.slots.length; i++) {
                var s = _mixerState.slots[i];
                var slotSwatchUrl = (typeof getSwatchUrl === 'function') ? getSwatchUrl(s.id, '888888', true, 40) : null;
                var slotFallback = _mixerGetBaseSwatch(s.id) || '#444';
                var slotThumbHtml = slotSwatchUrl
                    ? '<img src="' + slotSwatchUrl + '" style="width:40px;height:40px;border-radius:4px;border:1px solid #555;flex-shrink:0;object-fit:cover;background:' + slotFallback + ';" onerror="this.style.background=\'' + slotFallback + '\';this.src=\'\';">'
                    : '<div style="width:40px;height:40px;border-radius:4px;border:1px solid #555;flex-shrink:0;background:' + slotFallback + ';"></div>';
                var removeBtn = _mixerState.slots.length > 2
                    ? '<button onclick="event.stopPropagation();_mixerRemoveSlot(' + i + ')" style="position:absolute;top:-4px;right:-4px;background:#c0392b;border:none;color:#fff;width:16px;height:16px;border-radius:50%;font-size:10px;line-height:16px;text-align:center;cursor:pointer;" title="Remove">x</button>'
                    : '';
                var activeBorder = (_mixerState.activeSlot === i) ? 'border-color:#e844e8;box-shadow:0 0 8px #e844e8;' : '';
                slotsHtml += '<div style="position:relative;display:flex;align-items:center;gap:8px;background:#1a1a2e;border:1px solid #444;border-radius:6px;padding:8px;margin-bottom:6px;cursor:pointer;' + activeBorder + '" onclick="_mixerOpenPicker(' + i + ')">'
                    + removeBtn
                    + slotThumbHtml
                    + '<div style="flex:1;min-width:0;">'
                    + '<div style="color:#eee;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + _mixerGetBaseName(s.id) + '</div>'
                    + '<div style="display:flex;align-items:center;gap:6px;margin-top:4px;">'
                    + '<span id="mixerWtLabel' + i + '" style="color:#aaa;font-size:10px;min-width:28px;">' + s.weight + '%</span>'
                    + '<input type="range" min="0" max="100" value="' + s.weight + '" oninput="event.stopPropagation();_mixerWeightChange(' + i + ', this.value)" onclick="event.stopPropagation()" style="flex:1;height:4px;accent-color:#e844e8;">'
                    + '</div></div></div>';
            }
        
            var addBtn = _mixerState.slots.length < 3
                ? '<button onclick="_mixerAddSlot()" style="background:none;border:1px dashed #555;color:#888;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:11px;width:100%;margin-bottom:8px;">+ Add 3rd Finish</button>'
                : '';
        
            // === BUILD CATEGORY TABS (for picker) ===
            var categoryTabsHtml = '';
            if (picking) {
                // Merge BASE_GROUPS + SPECIAL_GROUPS for category tabs
                var allGroups = {};
                if (typeof BASE_GROUPS !== 'undefined') { var bk = Object.keys(BASE_GROUPS); for (var bi = 0; bi < bk.length; bi++) allGroups[bk[bi]] = BASE_GROUPS[bk[bi]]; }
                if (typeof SPECIAL_GROUPS !== 'undefined') { var sk = Object.keys(SPECIAL_GROUPS); for (var si = 0; si < sk.length; si++) { var sKey = sk[si].charAt(0) === '\u2605' ? sk[si] : '\u2605 ' + sk[si]; allGroups[sKey] = SPECIAL_GROUPS[sk[si]]; } }
                var groupKeys = Object.keys(allGroups);
                categoryTabsHtml += '<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:6px;">';
                var allActive = !_mixerState.pickerCategory ? 'background:#e844e8;color:#fff;' : 'background:#222;color:#aaa;';
                categoryTabsHtml += '<button onclick="_mixerSetCategory(\'\')" style="border:none;padding:2px 8px;border-radius:3px;font-size:9px;cursor:pointer;' + allActive + '">All</button>';
                for (var g = 0; g < groupKeys.length; g++) {
                    var isActive = _mixerState.pickerCategory === groupKeys[g] ? 'background:#e844e8;color:#fff;' : 'background:#222;color:#aaa;';
                    categoryTabsHtml += '<button onclick="_mixerSetCategory(\'' + groupKeys[g].replace(/'/g, "\\'") + '\')" style="border:none;padding:2px 8px;border-radius:3px;font-size:9px;cursor:pointer;' + isActive + '">' + groupKeys[g] + '</button>';
                }
                categoryTabsHtml += '</div>';
            }
        
            // === BUILD PICKER PANEL ===
            var pickerHtml = '';
            if (picking) {
                pickerHtml = '<div style="border:1px solid #444;border-radius:6px;padding:8px;margin-bottom:10px;max-height:480px;overflow:hidden;display:flex;flex-direction:column;">'
                    + '<div style="display:flex;gap:6px;margin-bottom:6px;align-items:center;">'
                    + '<span style="color:#e844e8;font-size:11px;font-weight:bold;">Pick for Slot ' + (_mixerState.activeSlot + 1) + '</span>'
                    + '<button onclick="_mixerClosePicker()" style="margin-left:auto;background:none;border:1px solid #555;color:#aaa;padding:1px 8px;border-radius:3px;cursor:pointer;font-size:10px;">Done</button>'
                    + '</div>'
                    + '<input type="text" placeholder="Search bases + specials..." oninput="_mixerFilterBases(this.value)" style="background:#111;color:#eee;border:1px solid #444;padding:4px 8px;border-radius:4px;font-size:11px;margin-bottom:4px;width:100%;box-sizing:border-box;">'
                    + '<div style="max-height:60px;overflow-y:auto;margin-bottom:4px;flex-shrink:0;">' + categoryTabsHtml + '</div>'
                    + '<div id="mixerBasePickerGrid" style="display:flex;flex-wrap:wrap;gap:4px;overflow-y:auto;flex:1;min-height:150px;align-content:flex-start;padding:4px 0;"></div>'
                    + '</div>';
            }
        
            // === BUILD PREVIEW AREA ===
            var previewImgHtml = _mixerState.previewImg
                ? '<img id="mixerPreviewImg" src="' + _mixerState.previewImg + '" style="width:100%;max-width:400px;height:auto;border:1px solid #444;border-radius:4px;image-rendering:auto;">'
                  + '<div style="display:flex;justify-content:space-around;font-size:9px;color:#666;margin-top:2px;"><span>PAINT</span><span>SPEC MAP</span></div>'
                : '<img id="mixerPreviewImg" style="display:none;width:100%;max-width:400px;height:auto;border:1px solid #444;border-radius:4px;image-rendering:auto;">';
        
            // === BUILD SAVED MIXES LIST ===
            var savedHtml = '';
            if (typeof _customMixFinishes !== 'undefined' && _customMixFinishes.length > 0) {
                savedHtml = '<div style="margin-top:8px;max-height:80px;overflow-y:auto;">';
                for (var s = 0; s < _customMixFinishes.length; s++) {
                    var cm = _customMixFinishes[s];
                    savedHtml += '<div style="display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid #222;">'
                        + '<span style="color:#ccc;font-size:10px;flex:1;">' + cm.name + '</span>'
                        + '<button onclick="_mixerDeleteCustom(\'' + cm.id + '\')" style="background:none;border:1px solid #c0392b;color:#e74c3c;padding:1px 6px;border-radius:3px;cursor:pointer;font-size:9px;">Del</button>'
                        + '</div>';
                }
                savedHtml += '</div>';
            }
        
            // === ASSEMBLE FULL PANEL ===
            var html = '<div style="background:#12122a;border:1px solid #e844e8;border-radius:10px;padding:18px 20px;width:520px;max-height:92vh;overflow-y:auto;box-shadow:0 8px 32px rgba(232,68,232,0.3);" onclick="event.stopPropagation();">'
                + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
                + '<h3 style="margin:0;color:#e844e8;font-size:15px;letter-spacing:1px;">&#129514; FINISH MIXER</h3>'
                + '<button onclick="closeMixerPanel()" style="background:none;border:none;color:#888;font-size:18px;cursor:pointer;">&times;</button>'
                + '</div>'
                // Slot cards
                + '<div style="margin-bottom:8px;">' + slotsHtml + '</div>'
                + addBtn
                // Base picker (shown when picking)
                + pickerHtml
                // Action buttons
                + '<div style="display:flex;gap:6px;margin-bottom:10px;">'
                + '<button onclick="_mixerPreview()" style="background:linear-gradient(135deg,#7c3aed,#e844e8);color:#fff;border:none;padding:7px 14px;border-radius:5px;cursor:pointer;font-size:11px;font-weight:bold;flex:1;">&#128065; Preview</button>'
                + '<button onclick="_mixerApplyDirect()" style="background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;border:none;padding:7px 14px;border-radius:5px;cursor:pointer;font-size:11px;font-weight:bold;flex:1;">&#9889; Apply to Zone</button>'
                + '</div>'
                // Mix mode selector
                + '<div style="display:flex;gap:4px;margin-bottom:10px;justify-content:center;">'
                + '<span style="color:#888;font-size:10px;align-self:center;margin-right:4px;">Apply:</span>'
                + '<button onclick="_mixerState.mixMode=\'both\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'both' ? '#e844e8' : '#444') + ';background:' + (_mixerState.mixMode === 'both' ? '#e844e822' : 'none') + ';color:' + (_mixerState.mixMode === 'both' ? '#e844e8' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'both' ? 'bold' : 'normal') + ';">Color + Spec</button>'
                + '<button onclick="_mixerState.mixMode=\'color\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'color' ? '#22c55e' : '#444') + ';background:' + (_mixerState.mixMode === 'color' ? '#22c55e22' : 'none') + ';color:' + (_mixerState.mixMode === 'color' ? '#22c55e' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'color' ? 'bold' : 'normal') + ';">Color Only</button>'
                + '<button onclick="_mixerState.mixMode=\'spec\';_renderMixerPanel()" style="border:1px solid ' + (_mixerState.mixMode === 'spec' ? '#3b82f6' : '#444') + ';background:' + (_mixerState.mixMode === 'spec' ? '#3b82f622' : 'none') + ';color:' + (_mixerState.mixMode === 'spec' ? '#3b82f6' : '#888') + ';padding:3px 10px;border-radius:3px;cursor:pointer;font-size:10px;font-weight:' + (_mixerState.mixMode === 'spec' ? 'bold' : 'normal') + ';">Spec Only</button>'
                + '</div>'
                // Preview image + spec info
                + '<div style="text-align:center;">' + previewImgHtml
                + '<div id="mixerSpecInfo" style="display:none;color:#888;font-size:10px;margin-top:4px;font-family:monospace;"></div>'
                + '</div>'
                + '<div id="mixerStatus" style="color:#888;font-size:10px;margin-top:6px;text-align:center;min-height:14px;"></div>'
                // Save section
                + '<hr style="border-color:#333;margin:10px 0;">'
                + '<div style="display:flex;gap:6px;align-items:center;">'
                + '<input id="mixerSaveName" type="text" placeholder="My Chrome Candy Carbon" style="flex:1;background:#1a1a2e;color:#eee;border:1px solid #444;padding:6px 8px;border-radius:4px;font-size:11px;">'
                + '<button onclick="_mixerSave()" style="background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:bold;white-space:nowrap;">&#128190; Save</button>'
                + '</div>'
                // Saved custom mixes with delete
                + savedHtml
                + '</div>';
        
            overlay.innerHTML = html;
            document.body.appendChild(overlay);
        
            // If picker is open, render the thumbnail grid
            if (picking) {
                _renderMixerBasePicker();
            }
        }
        
        // ================================================================
        // CUSTOM FINISHES LOADER
        // ================================================================
        
        var _customMixFinishes = [];
        
        function _loadCustomFinishes() {
            fetch('/api/custom-finishes', { signal: AbortSignal.timeout(8000) })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!Array.isArray(data)) return;
                _customMixFinishes = data;
                global._customMixFinishes = _customMixFinishes;
                if (typeof BASES !== 'undefined') {
                    for (var i = 0; i < data.length; i++) {
                        var exists = false;
                        for (var j = 0; j < BASES.length; j++) {
                            if (BASES[j].id === data[i].id) { exists = true; break; }
                        }
                        if (!exists) {
                            var recipe = data[i].finish_ids.join(' + ');
                            BASES.push({
                                id: data[i].id,
                                name: data[i].name,
                                desc: 'Custom mix: ' + recipe,
                                swatch: '#e844e8'
                            });
                        }
                    }
                }
                if (typeof BASE_GROUPS !== 'undefined' && data.length > 0) {
                    var customIds = [];
                    for (var k = 0; k < data.length; k++) customIds.push(data[k].id);
                    BASE_GROUPS["\u2605 CUSTOM MIXES"] = customIds;
                }
            })
            .catch(function() { /* silent fail */ });
        }
        
        if (typeof window !== 'undefined') {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', _loadCustomFinishes);
            } else {
                _loadCustomFinishes();
            }
        }
        
        

        global._mixerState = _mixerState;
        global.openFinishMixer = openFinishMixer;
        global.closeMixerPanel = closeMixerPanel;
        global._mixerGetBaseName = _mixerGetBaseName;
        global._mixerGetBaseSwatch = _mixerGetBaseSwatch;
        global._normalizeMixerWeights = _normalizeMixerWeights;
        global._mixerSlotChange = _mixerSlotChange;
        global._mixerWeightChange = _mixerWeightChange;
        global._mixerAddSlot = _mixerAddSlot;
        global._mixerRemoveSlot = _mixerRemoveSlot;
        global._mixerOpenPicker = _mixerOpenPicker;
        global._mixerClosePicker = _mixerClosePicker;
        global._mixerFilterBases = _mixerFilterBases;
        global._mixerSetCategory = _mixerSetCategory;
        global._renderMixerBasePicker = _renderMixerBasePicker;
        global._mixerGetZoneColor = _mixerGetZoneColor;
        global._mixerPreview = _mixerPreview;
        global._mixerApplyDirect = _mixerApplyDirect;
        global._mixerSave = _mixerSave;
        global._mixerDeleteCustom = _mixerDeleteCustom;
        global._renderMixerPanel = _renderMixerPanel;
        global._loadCustomFinishes = _loadCustomFinishes;
        global._customMixFinishes = _customMixFinishes;
    }

    global.SPBZoneFinishMixerControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
