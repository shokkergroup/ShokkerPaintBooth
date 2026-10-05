(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getBases = deps.getBases || function() { return global.BASES || []; };
        const getPatterns = deps.getPatterns || function() { return global.PATTERNS || []; };
        const getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
        const getBaseGroups = deps.getBaseGroups || function() { return global.BASE_GROUPS || {}; };
        const getPatternGroups = deps.getPatternGroups || function() { return global.PATTERN_GROUPS || {}; };
        const getSpecialGroups = deps.getSpecialGroups || function() { return global.SPECIAL_GROUPS || {}; };
        const getSpecialsSectionOrder = deps.getSpecialsSectionOrder || function() { return global.SPECIALS_SECTION_ORDER || []; };
        const getSpecialsSections = deps.getSpecialsSections || function() { return global.SPECIALS_SECTIONS || {}; };
        const getFinishType = deps.getFinishType || function(id) { return global.getFinishType ? global.getFinishType(id) : null; };
        const pickerCatalogItemType = deps.pickerCatalogItemType || function(id) { return global._pickerCatalogItemType ? global._pickerCatalogItemType(id) : null; };
        const pickerSelectValueForItem = deps.pickerSelectValueForItem || function(id, finishType) { return global._pickerSelectValueForItem ? global._pickerSelectValueForItem(id, finishType) : id; };
        const renderSwatchSquare = deps.renderSwatchSquare || function() { return ''; };
        const escapeHtml = deps.escapeHtml || function(value) {
            return String(value || '').replace(/[&<>"']/g, function(ch) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] || ch;
            });
        };

        function nameSort(a, b) {
            // SPB-SIMPLIFY-2026-07-19h (owner): the user's Finish Rating (0-100, default 50)
            // floats their highest-rated finishes to the top of every category; A-Z on ties.
            const rate = (typeof global.spbGetFinishRating === 'function')
                ? global.spbGetFinishRating : null;
            if (rate) {
                const rd = rate(b.id) - rate(a.id);
                if (rd) return rd;
            }
            return (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
        }

        function buildBaseSwatchItem(item, currentId) {
            const ft = getFinishType(item.id) || 'base';
            const search = [item.id, item.name, item.desc || '', item.subsection || '', item.sourceShelf || ''].join(' ').toLowerCase().replace(/"/g, '');
            return `<div class="swatch-item${currentId === item.id ? ' selected' : ''}" data-name="${item.name.toLowerCase()}" data-search="${search.replace(/"/g, '&quot;')}" data-finish-id="${item.id}" data-finish-type="${ft}" data-desc="${(item.desc || item.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${item.id}')">
                    ${renderSwatchSquare(item.id, item.swatch, item.desc)}
                    <div class="swatch-label">${item.colorSafe ? '<span style="color:#22c55e;font-size:8px;margin-right:2px;" title="Color-safe: won\'t change your car\'s base color">&#9679;</span>' : ''}${item.name}</div></div>`;
        }

        function buildBaseSections(currentId) {
            let html = `<div class="swatch-item${currentId === '' ? ' selected' : ''}" data-name="not set none clear" onclick="selectSwatchItem('')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">(not set)</div></div>`;
            const bases = getBases();
            const baseGroups = getBaseGroups();
            const baseGroupedIds = new Set();
            Object.keys(baseGroups).sort((a, b) => a === 'Foundation' ? -1 : b === 'Foundation' ? 1 : a.localeCompare(b)).forEach(function(groupName) {
                const ids = baseGroups[groupName];
                if (!ids || ids.length === 0) return;
                const groupBases = ids.map(function(id) { return bases.find(function(b) { return b.id === id; }); }).filter(Boolean).sort(nameSort);
                if (groupBases.length === 0) return;
                groupBases.forEach(function(b) { baseGroupedIds.add(b.id); });
                const collapsed = groupName !== 'Foundation';
                html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}" data-picker-category="${escapeHtml(groupName)}" data-picker-types="base">`;
                html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupBases.length})</span></div>`;
                const chapters = (global.BASE_GROUP_SUBSECTIONS || {})[groupName];
                if (chapters && chapters.length) {
                    // SPB-105 / SHOKK WORKS: each chapter owns its row so rating/
                    // name sorting cannot mix the subsections or duplicate cards.
                    const chapterIds = new Set();
                    chapters.forEach(function(chapter) {
                        const members = groupBases.filter(function(b) { return chapter.ids.indexOf(b.id) >= 0; }).sort(nameSort);
                        if (!members.length) return;
                        html += `<section class="spb-finish-subsection" data-finish-subsection="${escapeHtml(chapter.name)}"><div class="spb-finish-subsection-label">${escapeHtml(chapter.name)} <span>${members.length} finishes</span></div><p class="spb-finish-subsection-desc">${escapeHtml(chapter.description)}</p><div class="swatch-grid-row">`;
                        members.forEach(function(b) { chapterIds.add(b.id); html += buildBaseSwatchItem(b, currentId); });
                        html += '</div></section>';
                    });
                    const rest = groupBases.filter(function(b) { return !chapterIds.has(b.id); });
                    if (rest.length) { html += '<div class="swatch-grid-row">'; rest.forEach(function(b) { html += buildBaseSwatchItem(b,currentId); }); html += '</div>'; }
                } else {
                    html += '<div class="swatch-grid-row">';
                    groupBases.forEach(function(b) { html += buildBaseSwatchItem(b, currentId); });
                    html += '</div>';
                }
                html += '</div>';
            });

            const specialIds = new Set();
            const specialGroups = getSpecialGroups();
            Object.values(specialGroups).forEach(function(ids) {
                if (Array.isArray(ids)) ids.forEach(function(id) { specialIds.add(id); });
            });
            const ungroupedBases = bases.filter(function(b) { return !baseGroupedIds.has(b.id) && !specialIds.has(b.id); });
            if (ungroupedBases.length > 0) {
                html += `<div class="swatch-group" data-picker-category="Other Bases" data-picker-types="base"><div class="swatch-group-label">Other Bases <span class="swatch-group-count">(${ungroupedBases.length})</span></div><div class="swatch-grid-row">`;
                ungroupedBases.forEach(function(b) { html += buildBaseSwatchItem(b, currentId); });
                html += '</div></div>';
            }
            return html;
        }

        function buildSpecialSections(currentId) {
            let html = '';
            const bases = getBases();
            const monolithics = getMonolithics();
            const specialGroups = getSpecialGroups();
            const groupedIds = new Set();
            const colorChangingGroups = new Set(['Chameleon Classic', 'Prizm Series']);
            const sectionIcons = { 'Color-Changing': '&#127912;', 'Effects & Aesthetic': '&#10024;', 'PARADIGM': '&#9671;', 'Shokk Series': '&#9889;', 'Weather & Element': '&#127780;', 'Gradients': '&#12336;', 'Multi': '&#128256;', 'FUSIONS': '&#9670;' };

            function renderGroupSection(groups, sectionLabel, sectionIcon) {
                if (!groups || groups.length === 0) return '';
                let sectionHtml = `<div class="swatch-section-divider" style="margin:10px 0 6px; padding:6px 8px; background:var(--bg-dark); border:1px solid var(--border); border-radius:6px; display:flex; align-items:center; gap:6px;">
                <span style="font-size:12px;">${sectionIcon || '&#8226;'}</span>
                <span style="font-size:11px; font-weight:700; color:var(--accent-green); text-transform:uppercase; letter-spacing:1px;">${sectionLabel}</span>
                <span style="font-size:9px; color:var(--text-dim); margin-left:auto;">${groups.reduce((n, g) => n + (specialGroups[g] || []).length, 0)} finishes</span>
            </div>`;
                groups.forEach(function(groupName) {
                    const ids = specialGroups[groupName];
                    if (!ids) return;
                    const groupMonos = ids.map(function(id) {
                        return monolithics.find(function(m) { return m.id === id; }) || bases.find(function(b) { return b.id === id; });
                    }).filter(Boolean);
                    if (groupMonos.length === 0) return;
                    groupMonos.forEach(function(m) { groupedIds.add(m.id); });
                    const hasSelected = groupMonos.some(function(m) {
                        const ft = pickerCatalogItemType(m.id) || 'monolithic';
                        const sel = pickerSelectValueForItem(m.id, ft);
                        return currentId === sel || currentId === m.id;
                    });
                    const isColorGroup = groupName.startsWith('Solid') || groupName.startsWith('Gradient') || groupName.startsWith('Multi');
                    const collapsed = isColorGroup && !hasSelected;
                    const groupPickerTypes = groupMonos.every(function(m) { return (pickerCatalogItemType(m.id) || 'monolithic') === 'base'; })
                        ? 'base'
                        : (groupMonos.every(function(m) { return (pickerCatalogItemType(m.id) || 'monolithic') === 'monolithic'; }) ? 'monolithic' : 'base,monolithic');
                    sectionHtml += `<div class="swatch-group${collapsed ? ' collapsed' : ''}" data-picker-category="${escapeHtml(groupName)}" data-picker-types="${groupPickerTypes}">`;
                    sectionHtml += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupMonos.length})</span></div>`;
                    sectionHtml += '<div class="swatch-grid-row">';
                    groupMonos.forEach(function(m) {
                        const ft = pickerCatalogItemType(m.id) || 'monolithic';
                        const selectedValue = pickerSelectValueForItem(m.id, ft);
                        const onClick = "selectSwatchItem('" + selectedValue.replace(/'/g, "\\'") + "')";
                        sectionHtml += `<div class="swatch-item${(currentId === selectedValue || currentId === m.id) ? ' selected' : ''}" data-name="${m.name.toLowerCase()}" data-finish-id="${m.id}" data-finish-type="${ft}" data-desc="${(m.desc || m.name).replace(/"/g, '&quot;')}" onclick="${onClick}">
                        ${renderSwatchSquare(m.id, m.swatch, m.desc, null, ft)}
                        <div class="swatch-label">${m.name}</div></div>`;
                    });
                    sectionHtml += '</div></div>';
                });
                return sectionHtml;
            }

            const specialsSectionOrder = getSpecialsSectionOrder();
            const specialsSections = getSpecialsSections();
            if (specialsSectionOrder.length > 0 && Object.keys(specialsSections).length > 0) {
                const renderedGroups = new Set();
                specialsSectionOrder.forEach(function(sectionKey) {
                    const groupNames = specialsSections[sectionKey];
                    const list = Array.isArray(groupNames) ? groupNames : [];
                    list.forEach(function(g) { renderedGroups.add(g); });
                    html += renderGroupSection(list, sectionKey, sectionIcons[sectionKey]);
                });
                const remaining = Object.keys(specialGroups).filter(function(g) { return !renderedGroups.has(g); });
                if (remaining.length > 0) html += renderGroupSection(remaining, 'Solid & Gradients', '&#12336;');
            } else {
                const allGroupNames = Object.keys(specialGroups).sort();
                html += renderGroupSection(allGroupNames.filter(function(g) { return colorChangingGroups.has(g); }), 'Color-Changing Finishes', '&#127912;');
                html += renderGroupSection(allGroupNames.filter(function(g) { return !colorChangingGroups.has(g); }), 'Effect Finishes (keeps paint color)', '&#10024;');
            }
            return html;
        }

        function buildPatternSections(type, currentId) {
            let html = '';
            const noneLabel = (type === 'secondBasePattern' || type === 'thirdBasePattern') ? '- Zone primary -' : 'None';
            const noneValue = (type === 'secondBasePattern' || type === 'thirdBasePattern') ? '' : 'none';
            html += `<div class="swatch-item${(currentId === 'none' || currentId === '') ? ' selected' : ''}" data-name="none not set clear" onclick="selectSwatchItem('${noneValue}')" style="margin-bottom:4px;">
            <div class="swatch-square" style="background:#333;display:flex;align-items:center;justify-content:center;color:var(--text-dim);font-size:10px;">&#8709;</div>
            <div class="swatch-label">${noneLabel}</div></div>`;
            const patterns = getPatterns();
            const patternGroups = getPatternGroups();
            Object.keys(patternGroups).sort((a, b) => a === 'Abstract & Experimental' ? -1 : b === 'Abstract & Experimental' ? 1 : a.localeCompare(b)).forEach(function(groupName) {
                const ids = patternGroups[groupName];
                if (!ids || ids.length === 0) return;
                const groupPats = ids.map(function(id) { return patterns.find(function(p) { return p.id === id; }); }).filter(Boolean).sort(nameSort);
                if (groupPats.length === 0) return;
                const collapsed = groupName !== 'Abstract & Experimental';
                html += `<div class="swatch-group${collapsed ? ' collapsed' : ''}" data-picker-category="${escapeHtml(groupName)}" data-picker-types="pattern">`;
                html += `<div class="swatch-group-label" onclick="this.parentElement.classList.toggle('collapsed')">${groupName} <span class="swatch-group-count">(${groupPats.length})</span></div>`;
                html += '<div class="swatch-grid-row">';
                groupPats.forEach(function(p) {
                    const search = [p.id, p.name, p.desc || ''].join(' ').toLowerCase().replace(/"/g, '');
                    html += `<div class="swatch-item${currentId === p.id ? ' selected' : ''}" data-name="${p.name.toLowerCase()}" data-search="${search.replace(/"/g, '&quot;')}" data-finish-id="${p.id}" data-finish-type="pattern" data-desc="${(p.desc || p.name).replace(/"/g, '&quot;')}" onclick="selectSwatchItem('${p.id}')">
                    ${renderSwatchSquare(p.id, p.swatch, p.desc)}
                    <div class="swatch-label">${p.name}</div></div>`;
                });
                html += '</div></div>';
            });
            return html;
        }

        function buildSwatchPickerGridHtml(args) {
            args = args || {};
            const type = args.type;
            const currentId = args.currentId || '';
            if (type === 'specOverlay') return global.SPBSpecOverlayPicker.buildGrid(currentId);
            const isOverlaySpecialSourcePicker = (type === 'secondBaseColorSource' || type === 'thirdBaseColorSource' || type === 'fourthBaseColorSource' || type === 'fifthBaseColorSource');
            const isOverlayBaseColorPicker = (type === 'overlayBaseColor');
            const isLayerSpecialPaintPicker = (type === 'layerSpecialPaint');
            let html = '';
            if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker || isOverlayBaseColorPicker || isLayerSpecialPaintPicker) {
                if (!isOverlaySpecialSourcePicker && !isLayerSpecialPaintPicker) html += buildBaseSections(currentId);
                if (type === 'base' || type === 'secondBase' || type === 'thirdBase' || type === 'fourthBase' || type === 'fifthBase' || type === 'baseColorSource' || isOverlaySpecialSourcePicker || isLayerSpecialPaintPicker) html += buildSpecialSections(currentId);
            }
            if (type === 'pattern' || type === 'stackPattern' || type === 'secondBasePattern' || type === 'thirdBasePattern') html += buildPatternSections(type, currentId);
            return html;
        }

        Object.assign(global, { buildSwatchPickerGridHtml: buildSwatchPickerGridHtml });
    }

    global.SPBSwatchPopupGridBuilderControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
