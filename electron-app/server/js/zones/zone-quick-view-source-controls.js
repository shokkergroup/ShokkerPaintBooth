(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        var documentRef = deps.document || global.document;
        var getZones = deps.getZones || function() { return global.zones || []; };
        var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return -1; };
        var getOverlayColors = deps.getOverlayColors || function() { return global.ZONE_OVERLAY_COLORS || []; };
        var getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
        var getBases = deps.getBases || function() { return global.BASES || []; };
        var getActiveImportedSpecMapPath = deps.getActiveImportedSpecMapPath || function() { return ''; };
        var escapeHtml = deps.escapeHtml || function(value) {
            return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
            });
        };

        var fallbackOverlayColors = [
            [255, 50, 50, 200], [50, 255, 50, 200], [50, 100, 255, 200], [255, 255, 50, 200],
            [255, 50, 255, 200], [50, 255, 255, 200], [255, 150, 50, 200], [150, 50, 255, 200],
            [255, 100, 100, 200], [100, 255, 200, 200], [200, 150, 255, 200]
        ];

        function findName(items, id) {
            var item = (items || []).find(function(entry) { return entry && entry.id === id; });
            return (item && item.name) || id;
        }

        function renderZoneQuickView() {
            var bar = documentRef ? documentRef.getElementById('zoneQuickViewBar') : null;
            if (!bar) return;
            var overlayColors = getOverlayColors();
            if (!overlayColors || !overlayColors.length) overlayColors = fallbackOverlayColors;
            var selectedZoneIndex = getSelectedZoneIndex();
            var monolithics = getMonolithics();
            var bases = getBases();
            var chips = '';

            getZones().forEach(function(zone, i) {
                if (!zone.base && !zone.finish) return;
                var c = overlayColors[i % overlayColors.length];
                var bg = 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',0.7)';
                var baseName = zone.finish ? findName(monolithics, zone.finish) : findName(bases, zone.base);
                var shortName = baseName.length > 16 ? baseName.substring(0, 14) + '..' : baseName;
                var sel = i === selectedZoneIndex ? ' selected' : '';
                chips += '<span class="zone-qv-chip' + sel + '" style="background:' + bg + ';" onclick="selectZone(' + i + ')" title="' + escapeHtml(zone.name + ': ' + baseName) + '">' + (i + 1) + ': ' + escapeHtml(shortName) + '</span>';
            });
            bar.innerHTML = chips;
        }

        function zoneSpecSourceDisplayName(zone) {
            if (!zone || !zone.zoneSpecMapPath) return 'No imported spec source';
            var rawName = zone.zoneSpecMapName || String(zone.zoneSpecMapPath).split(/[\\/]/).pop() || 'Imported spec';
            var res = Array.isArray(zone.zoneSpecMapResolution)
                ? ' (' + zone.zoneSpecMapResolution[0] + 'x' + zone.zoneSpecMapResolution[1] + ')'
                : '';
            return rawName + res;
        }

        function renderZoneSpecSourceSection(i, zone) {
            var hasSpecSource = !!(zone && zone.zoneSpecMapPath);
            var strengthPct = Math.max(0, Math.min(100, Math.round(Number(zone.zoneSpecMapStrength == null ? 100 : zone.zoneSpecMapStrength))));
            var globalAvailable = getActiveImportedSpecMapPath();
            var useGlobalDisabled = globalAvailable ? '' : ' disabled';
            var clearDisabled = hasSpecSource ? '' : ' disabled';
            var activeTone = hasSpecSource ? 'var(--accent-green,#00ff88)' : 'var(--text-dim,#888)';
            return `<div class="section-collapsible" id="sectionZoneSpecSource${i}">
    <div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle('collapsed')">
        <span class="section-header-label">SPEC SOURCE</span>
        <span class="collapse-arrow section-header-arrow">&#9660;</span>
    </div>
    <div class="pattern-stack-section" style="border-left:2px solid #00c8ff; padding:6px 8px; margin-top:6px; background:rgba(0,200,255,0.04);">
        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span class="stack-label-mini" style="min-width:78px;">Imported Spec</span>
            <span id="zoneSpecSourceStatus${i}" style="flex:1; min-width:160px; color:${activeTone}; font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml((zone && zone.zoneSpecMapPath) || '')}">${escapeHtml(zoneSpecSourceDisplayName(zone))}</span>
            <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); importZoneSpecMapFromFile(${i})" title="Import a TGA spec map for this zone" style="padding:2px 8px;font-size:10px;border-color:#00c8ff;color:#bff7ff;">Import</button>
            <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); copyImportedSpecMapToZone(${i})" title="Use the global imported Layer 0 spec map on this zone"${useGlobalDisabled} style="padding:2px 8px;font-size:10px;">Use Layer 0</button>
            <button type="button" class="btn btn-sm" onclick="event.stopPropagation(); clearZoneSpecMap(${i})" title="Clear this zone spec source"${clearDisabled} style="padding:2px 8px;font-size:10px;color:#ff9a9a;">Clear</button>
        </div>
        <div class="stack-control-group" style="margin-top:6px;">
            <span class="stack-label-mini">Source Strength</span>
            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSpecMapStrength(${i}, -1)" title="-5%" style="padding:0 4px;font-size:10px;"${clearDisabled}>-</button>
            <input type="range" min="0" max="100" step="5" value="${strengthPct}" oninput="setZoneSpecMapStrength(${i}, this.value)" class="stack-slider" title="Blend imported spec with this zone's generated spec"${clearDisabled}>
            <button class="btn btn-sm stack-step-btn" onclick="event.stopPropagation(); stepZoneSpecMapStrength(${i}, 1)" title="+5%" style="padding:0 4px;font-size:10px;"${clearDisabled}>+</button>
            <span class="stack-val" id="detZoneSpecMapStrengthVal${i}">${strengthPct}%</span>
        </div>
    </div>
    </div>`;
        }

        Object.assign(global, {
            renderZoneQuickView: renderZoneQuickView,
            renderZoneSpecSourceSection: renderZoneSpecSourceSection
        });
    }

    global.SPBZoneQuickViewSourceControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
