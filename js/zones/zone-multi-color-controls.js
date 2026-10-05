(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var doc = deps.document || global.document;
        var getZones = deps.getZones || function() { return global.zones || []; };
        var getLastEyedropperColor = deps.getLastEyedropperColor || function() { return null; };
        var pushZoneUndo = deps.pushZoneUndo || function() {};
        var renderZones = deps.renderZones || function() {};
        var triggerPreviewRender = deps.triggerPreviewRender || function() {};
        var showToast = deps.showToast || function() {};
        var escapeHtml = deps.escapeHtml || function(value) {
            return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
            });
        };

        function getColorStatusText(zone) {
            zone = zone || {};
            var regionMask = zone.regionMask;
            var hasRegion = !!(regionMask && Array.prototype.some.call(regionMask, function(v) { return v > 0; }));
            var regionPixels = hasRegion
                ? Array.prototype.reduce.call(regionMask, function(sum, v) { return sum + v; }, 0)
                : 0;
            var regionNote = hasRegion
                ? '<br><span style="color: var(--accent-blue);">&#9998; Drawn region: <strong>' + regionPixels.toLocaleString() + ' pixels</strong> marked</span>'
                : '';

            if (zone.colorMode === 'multi' && zone.colors && zone.colors.length > 0) {
                return '&#10004; Multi-color zone: <strong>' + zone.colors.length + ' colors stacked</strong> - all pixels get the same finish' + regionNote;
            }
            if (hasRegion && (zone.colorMode === 'none' || zone.color === null)) {
                return '<span style="color: var(--accent-blue);">&#9998; Drawn region: <strong>' + regionPixels.toLocaleString() + ' pixels</strong> - zone applies only here (no color match). Assign base/finish and Render.</span>';
            }
            if (zone.colorMode === 'none' || zone.color === null) return '<span style="color: #ff6644;">&#9888; No color or region set - use Pick Color, Draw Region, or buttons</span>';
            if (zone.colorMode === 'quick') return '&#10004; Matching all <strong>' + zone.color + '</strong> pixels';
            if (zone.colorMode === 'special') {
                if (zone.color === 'everything') return '&#10004; Covers <strong>ALL</strong> pixels on the car';
                if (zone.color === 'remaining') return '&#10004; Catches anything <strong>not claimed</strong> by zones above';
                return '&#10004; Special: <strong>' + zone.color + '</strong>';
            }
            if (zone.colorMode === 'picker') {
                var c = zone.color || {};
                var hex = zone.pickerColor || '#???';
                return '&#10004; Matching pixels near <strong>' + hex.toUpperCase() + '</strong> (tolerance: ' + c.tolerance + ')';
            }
            if (zone.colorMode === 'text') return '&#10004; Matching: <strong>' + escapeHtml(String(zone.color)) + '</strong>';
            return '';
        }

        function renderMultiColorChips(zone, zoneIndex) {
            zone = zone || {};
            var colors = zone.colors || [];
            if (colors.length === 0 && zone.colorMode !== 'multi') return '';

            var chips = colors.map(function(c, ci) {
                var hex = c.hex || '#???';
                return '<div style="display: flex; flex-direction: column; gap: 2px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: 4px; padding: 3px 6px; font-size: 10px;">'
                    + '<div style="display: flex; align-items: center; gap: 3px;">'
                    + '<span style="width: 14px; height: 14px; border-radius: 3px; background: ' + hex + '; border: 1px solid var(--border); display: inline-block;"></span>'
                    + '<span style="font-family: \'Consolas\', monospace; color: var(--accent-green);">' + hex.toUpperCase() + '</span>'
                    + '<button onclick="event.stopPropagation(); removeColorFromZone(' + zoneIndex + ', ' + ci + ')" style="background:none; border:none; color:#ff4444; cursor:pointer; font-size:12px; padding:0 2px; line-height:1;" title="Remove this color">&times;</button>'
                    + '</div>'
                    + '<div style="display: flex; align-items: center; gap: 3px;">'
                    + '<span style="font-size:8px; color:var(--text-dim);">TOL:</span>'
                    + '<input type="range" min="0" max="100" value="' + (c.tolerance ?? 40) + '" style="width:60px; height:10px;" '
                    + 'oninput="updateColorTolerance(' + zoneIndex + ', ' + ci + ', parseInt(this.value, 10)); this.nextElementSibling.textContent=\'&plusmn;\'+this.value" '
                    + 'title="Tolerance for this specific color">'
                    + '<span style="font-size:8px; color:var(--text-dim); min-width:18px;">&plusmn;' + (c.tolerance ?? 40) + '</span>'
                    + '</div>'
                    + '</div>';
            }).join('');

            return '<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; align-items: center;">'
                + chips
                + '<button onclick="event.stopPropagation(); addColorToZoneFromPicker(' + zoneIndex + ')" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: var(--accent-green); color: var(--accent-green);" title="Add another color to this zone (use hex input or eyedropper first)">+ Add Color</button>'
                + (colors.length > 0 ? '<button onclick="event.stopPropagation(); clearZoneColors(' + zoneIndex + ')" class="quick-color-btn" style="font-size: 9px; padding: 2px 6px; border-color: #ff4444; color: #ff4444;" title="Clear all stacked colors">Clear All</button>' : '')
                + '</div>';
        }

        function addColorToZoneFromPicker(zoneIndex) {
            var zones = getZones();
            var zone = (typeof zoneIndex === 'number' && zoneIndex >= 0) ? zones[zoneIndex] : null;
            if (!zone) return;
            var hex = null;
            var eyedropperColor = getLastEyedropperColor();

            if (eyedropperColor) {
                hex = '#' + [eyedropperColor.r, eyedropperColor.g, eyedropperColor.b].map(function(c) {
                    return c.toString(16).padStart(2, '0');
                }).join('').toUpperCase();
            }
            if (!hex) {
                var hexInput = doc && doc.getElementById('hexInput');
                if (hexInput && hexInput.value && /^#[0-9A-Fa-f]{6}$/.test(hexInput.value)) {
                    hex = hexInput.value.toUpperCase();
                }
            }
            if (!hex) hex = zone.pickerColor || '#3366FF';

            var r = parseInt(hex.substr(1, 2), 16);
            var g = parseInt(hex.substr(3, 2), 16);
            var b = parseInt(hex.substr(5, 2), 16);
            var tol = zone.pickerTolerance ?? 40;

            if (!Array.isArray(zone.colors)) zone.colors = [];
            if (zone.colors.some(function(c) { return c.hex && c.hex.toUpperCase() === hex.toUpperCase(); })) {
                showToast('That color is already added to this zone', true);
                return;
            }

            zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
            zone.colorMode = 'multi';
            zone.color = zone.colors;
            zone.pickerColor = hex;
            renderZones();
            triggerPreviewRender();
            showToast('Added ' + hex + ' to ' + zone.name + ' (' + zone.colors.length + ' color' + (zone.colors.length !== 1 ? 's' : '') + ' stacked)');
        }

        function removeColorFromZone(zoneIndex, colorIndex) {
            var zones = getZones();
            var zone = (typeof zoneIndex === 'number' && zoneIndex >= 0) ? zones[zoneIndex] : null;
            if (!zone || !zone.colors || colorIndex < 0 || colorIndex >= zone.colors.length) return;
            var removedHex = zone.colors[colorIndex] && zone.colors[colorIndex].hex;
            pushZoneUndo('Remove multi-color: ' + (removedHex || ''));
            zone.colors.splice(colorIndex, 1);
            if (zone.colors.length === 0) {
                zone.colorMode = 'none';
                zone.color = null;
            } else {
                zone.color = zone.colors;
            }
            renderZones();
            triggerPreviewRender();
        }

        function updateColorTolerance(zoneIndex, colorIndex, value) {
            var zones = getZones();
            var zone = zones[zoneIndex];
            if (zone && zone.colors && zone.colors[colorIndex]) {
                pushZoneUndo('Multi-color tolerance', true);
                zone.colors[colorIndex].tolerance = value;
                zone.color = zone.colors;
                triggerPreviewRender();
            }
        }

        function clearZoneColors(zoneIndex) {
            var zones = getZones();
            if (!zones[zoneIndex]) return;
            pushZoneUndo('Clear zone colors');
            zones[zoneIndex].colors = [];
            zones[zoneIndex].colorMode = 'none';
            zones[zoneIndex].color = null;
            renderZones();
            triggerPreviewRender();
        }

        Object.assign(global, {
            getColorStatusText: getColorStatusText,
            renderMultiColorChips: renderMultiColorChips,
            addColorToZoneFromPicker: addColorToZoneFromPicker,
            removeColorFromZone: removeColorFromZone,
            updateColorTolerance: updateColorTolerance,
            clearZoneColors: clearZoneColors
        });
    }

    global.SPBZoneMultiColorControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
