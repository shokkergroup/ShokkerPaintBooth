(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var getZones = deps.getZones || function() { return global.zones || []; };
        var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return -1; };
        var getBulkSelectedZones = deps.getBulkSelectedZones || function() { return null; };
        var getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
        var getBases = deps.getBases || function() { return global.BASES || []; };
        var getPatterns = deps.getPatterns || function() { return global.PATTERNS || []; };
        var getIntensityOptions = deps.getIntensityOptions || function() { return global.INTENSITY_OPTIONS || []; };
        var getQuickColors = deps.getQuickColors || function() { return global.QUICK_COLORS || []; };
        var getZoneStatusBadgeHTML = deps.getZoneStatusBadgeHTML || function() { return ''; };
        var getZoneDiagnostic = deps.getZoneDiagnostic || function() { return ''; };
        var escapeHtml = deps.escapeHtml || function(value) {
            return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
            });
        };

        function findName(items, id) {
            var item = (items || []).find(function(entry) { return entry && entry.id === id; });
            return (item && item.name) || id;
        }

        function zoneCardFinishName(zone) {
            var bases = getBases();
            var patterns = getPatterns();
            var stackCount = (zone.patternStack || []).filter(function(layer) { return layer.id && layer.id !== 'none'; }).length;
            if (zone.finish) {
                return findName(getMonolithics(), zone.finish)
                    + (zone.pattern && zone.pattern !== 'none' ? ' + ' + findName(patterns, zone.pattern) : '');
            }
            if (zone.base) {
                return findName(bases, zone.base)
                    + (zone.pattern && zone.pattern !== 'none' ? ' + ' + findName(patterns, zone.pattern) : '')
                    + (stackCount > 0 ? ' +' + stackCount : '');
            }
            return '(not set)';
        }

        function zoneCardDot(zone) {
            var quickColors = getQuickColors();
            if (zone.colorMode === 'picker' && zone.pickerColor) {
                return { color: zone.pickerColor, title: 'Zone color: ' + zone.pickerColor };
            }
            if (zone.colorMode === 'quick' && zone.color) {
                var qc = quickColors.find(function(c) { return c.value === zone.color; });
                return { color: qc ? qc.bg : '#888', title: 'Zone color: ' + zone.color };
            }
            if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
                var rgb = zone.colors[0].color_rgb || [128, 128, 128];
                return { color: 'rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')', title: 'Zone color: ' + zone.colors.length + ' color(s)' };
            }
            if (zone.colorMode === 'text' && zone.color) {
                var text = String(zone.color).toLowerCase();
                var textQc = quickColors.find(function(c) { return text.includes(c.value); });
                return { color: textQc ? textQc.bg : '#888', title: 'Zone color: "' + zone.color + '"' };
            }
            if (zone.colorMode === 'special' && zone.color === 'remaining') {
                return { color: '#555', title: 'Remainder (unclaimed pixels)' };
            }
            if (zone.colorMode === 'special' && zone.color === 'everything') {
                return { color: 'linear-gradient(135deg, #888, #ccc)', title: 'Everything (all pixels)' };
            }
            if (zone.regionMask && Array.prototype.some.call(zone.regionMask, function(v) { return v > 0; })) {
                return { color: '#cc88ff', title: 'Region-based zone (lasso/brush drawn)' };
            }
            return { color: 'NOCOLOR', title: 'No color selected - pick a color first' };
        }

        function regionBadgeHtml(zone) {
            if (!zone.regionMask || !Array.prototype.some.call(zone.regionMask, function(v) { return v > 0; })) return '';
            var pixels = Array.prototype.reduce.call(zone.regionMask, function(sum, v) { return sum + (v > 0 ? 1 : 0); }, 0);
            return '<span style="font-size:8px; color:#cc88ff; margin-left:2px; white-space:nowrap;" title="Region drawn (' + pixels.toLocaleString() + ' pixels)">&#127919;</span>';
        }

        function swatchStripHtml(zone, dotColor) {
            var swatches = '';
            if (zone.colorMode === 'multi' && zone.colors && zone.colors.length) {
                zone.colors.slice(0, 4).forEach(function(c) {
                    var rgb = c.color_rgb || [128, 128, 128];
                    swatches += '<div class="zone-swatch" style="background:rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')" title="Source color"></div>';
                });
            } else if (dotColor && dotColor !== 'NOCOLOR' && !dotColor.includes('gradient')) {
                swatches = '<div class="zone-swatch" style="background:' + dotColor + '" title="Zone color"></div>';
            } else {
                swatches = '<div class="zone-swatch" style="background:#555; border-style:dashed" title="No color source"></div>';
            }
            return swatches;
        }

        function renderZoneCardHtml(zone, i) {
            var zones = getZones();
            var selectedZoneIndex = getSelectedZoneIndex();
            var bulkSelectedZones = getBulkSelectedZones();
            var isSelected = i === selectedZoneIndex;
            var accordionClass = ' zone-card-collapsed' + (isSelected ? ' selected' : '');
            var finishName = zoneCardFinishName(zone);
            var intensity = (getIntensityOptions() || []).find(function(o) { return o && o.id === zone.intensity; });
            var intensityName = zone.customSpec != null ? 'Custom' : ((intensity && intensity.name) || zone.intensity || '');
            var specSourceBadge = zone.zoneSpecMapPath ? ' <span class="finish-badge" title="Zone has an imported spec source">Spec source</span>' : '';
            var summaryHtml = '<span class="zone-summary">' + escapeHtml(finishName)
                + (intensityName ? ' <span class="finish-badge">' + escapeHtml(intensityName) + '</span>' : '')
                + specSourceBadge + '</span>';
            var overlayCount = (zone.patternStack || []).filter(function(layer) { return layer.id && layer.id !== 'none'; }).length;
            var energy = overlayCount * 1.5 + (parseFloat(zone.intensity) || 0) * 2;
            var dot = zoneCardDot(zone);
            var mutedClass = zone.muted ? ' zone-muted' : '';
            var bulkSelectedClass = (bulkSelectedZones && bulkSelectedZones.has(i)) ? ' zone-bulk-selected' : '';
            var linkedNames = zone.linkGroup
                ? zones.filter(function(z) { return z.linkGroup === zone.linkGroup; }).map(function(z) { return z.name; }).join(' + ')
                : '';

            return '<div class="zone-card' + accordionClass + mutedClass + bulkSelectedClass + '" onclick="selectZone(' + i + ')" id="zone-card-' + i + '" '
                + 'ondragover="zoneDragOver(event,' + i + ')" ondragenter="zoneDragEnter(event,' + i + ')" ondragleave="zoneDragLeave(event)" ondrop="zoneDrop(event,' + i + ')" ondragend="zoneDragEnd(event)" '
                + 'title="' + escapeHtml(getZoneDiagnostic(zone)) + '">'
                + '<div class="zone-card-header">'
                + '<span class="zone-drag-handle" draggable="true" ondragstart="zoneDragStart(event,' + i + ')" title="Drag to reorder">&#x2630;</span>'
                + '<span class="zone-number">' + (i + 1) + '</span>'
                + getZoneStatusBadgeHTML(zone)
                + '<span class="zone-overlay-dot' + (dot.color === 'NOCOLOR' ? ' no-color' : '') + '" style="' + (dot.color !== 'NOCOLOR' ? 'background:' + dot.color + ';' : '') + '" title="' + escapeHtml(dot.title) + '">' + (dot.color === 'NOCOLOR' ? '&#9888;' : '') + '</span>'
                + '<input class="zone-name-input" type="text" value="' + escapeHtml(zone.name) + '" onclick="event.stopPropagation()" onchange="updateZoneName(' + i + ', this.value)">'
                + summaryHtml + regionBadgeHtml(zone)
                + '<div class="zone-card-actions" role="group" aria-label="Zone ' + (i + 1) + ' actions">'
                + '<button class="zone-mute-btn' + (zone.muted ? ' muted' : '') + '" onclick="event.stopPropagation(); toggleZoneMute(' + i + ')" title="Temporarily disable this zone without deleting it">' + (zone.muted ? '&#x1F6AB;' : '&#x1F441;') + '</button>'
                + '<button class="zone-move-btn" onclick="event.stopPropagation(); duplicateZone(' + i + ')" title="Duplicate this zone" style="font-size:12px; padding:1px 5px;">&#x29C9;</button>'
                + '<div class="zone-reorder-group">'
                + '<button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneUp(' + i + ')" title="Move zone up (higher priority)"' + (i === 0 ? ' disabled' : '') + '>&#9650;</button>'
                + '<button class="zone-move-btn" onclick="event.stopPropagation(); moveZoneDown(' + i + ')" title="Move zone down (lower priority)"' + (i === zones.length - 1 ? ' disabled' : '') + '>&#9660;</button>'
                + '</div>'
                + '<button class="zone-move-btn" onclick="event.stopPropagation(); promptLinkZone(' + i + ')" title="' + (zone.linkGroup ? 'Linked (click to unlink)' : 'Link this zone to another') + '" style="font-size:11px; padding:1px 4px;' + (zone.linkGroup ? ' color:var(--accent-gold); border-color:var(--accent-gold);' : '') + '">' + (zone.linkGroup ? '&#128279;' : '&#9741;') + '</button>'
                + '<button class="zone-delete-btn" onclick="event.stopPropagation(); deleteZone(' + i + ')" title="Delete zone">&times;</button>'
                + '</div></div>'
                + (zone.linkGroup ? '<div style="font-size:8px; color:var(--accent-gold); padding:0 8px 2px; letter-spacing:0.5px;">&#128279; LINKED: ' + escapeHtml(linkedNames) + '</div>' : '')
                + '<div class="zone-visual"><div class="zone-swatch-strip">' + swatchStripHtml(zone, dot.color) + '</div>'
                + '<div class="zone-mini-ekg ' + (energy > 5 ? 'high-energy' : energy > 2 ? '' : 'low-energy') + '"></div></div>'
                + '</div>';
        }

        Object.assign(global, {
            renderZoneCardHtml: renderZoneCardHtml
        });
    }

    global.SPBZoneCardRenderControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
