'use strict';

(function () {
  const recentFinishesV2 = [];

  function install(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function () { return window.zones || []; };
    const getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return window.selectedZoneIndex || 0; };
    const pushZoneUndo = deps.pushZoneUndo || window.pushZoneUndo || function () {};
    const renderZones = deps.renderZones || window.renderZones || function () {};
    const showToast = deps.showToast || window.showToast || function () {};
    const preview = deps.triggerPreviewRender || window.triggerPreviewRender || function () {};
    const selectZone = deps.selectZone || window.selectZone;
    const soloZone = deps.soloZone || window.soloZone;
    const renderZoneDetail = deps.renderZoneDetail || window.renderZoneDetail;
    const getPsdLayers = deps.getPsdLayers || function () { return window._psdLayers || []; };

    function zones() { return getZones(); }

    window.validateZonesBeforeRender = function validateZonesBeforeRender() {
      const warnings = [];
      zones().forEach(function (z, i) {
        if (z.muted) return;
        if (!z.base && !z.finish) warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": no finish assigned');
        const hasColor = z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special';
        const hasRegion = z.regionMask && z.regionMask.some(function (v) { return v > 0; });
        if (!hasColor && !hasRegion) warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": no color or region defined (zone will not apply to any pixels)');
        if ((z.base || z.finish) && !hasColor && !hasRegion) warnings.push('Zone ' + (i + 1) + ' "' + z.name + '": finish set but no pixels targeted');
      });
      return warnings;
    };

    window.showZoneValidationWarnings = function showZoneValidationWarnings() {
      const warnings = window.validateZonesBeforeRender();
      if (warnings.length > 0) {
        const msg = warnings.length === 1 ? warnings[0] : warnings.length + ' zone warnings: ' + warnings.slice(0, 3).join('; ') + (warnings.length > 3 ? '...' : '');
        showToast(msg, true);
      }
      return warnings;
    };

    window.getZoneStatistics = function getZoneStatistics() {
      const pc = document.getElementById('paintCanvas');
      const totalPixels = pc ? (pc.width * pc.height) : 0;
      const stats = {
        totalZones: zones().length,
        activeZones: zones().filter(function (z) { return !z.muted; }).length,
        mutedZones: zones().filter(function (z) { return z.muted; }).length,
        zonesWithFinish: zones().filter(function (z) { return z.base || z.finish; }).length,
        zonesWithColor: zones().filter(function (z) { return z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special'; }).length,
        zonesWithRegion: 0,
        totalRegionPixels: 0,
        coveragePercent: 0,
        perZone: [],
      };
      zones().forEach(function (z, i) {
        const hasRegion = z.regionMask && z.regionMask.some(function (v) { return v > 0; });
        let regionPixels = 0;
        if (hasRegion) {
          stats.zonesWithRegion++;
          regionPixels = z.regionMask.reduce(function (sum, v) { return sum + (v > 0 ? 1 : 0); }, 0);
          stats.totalRegionPixels += regionPixels;
        }
        stats.perZone.push({
          name: z.name,
          index: i,
          muted: z.muted,
          hasFinish: !!(z.base || z.finish),
          hasColor: z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special',
          hasRegion,
          regionPixels,
          regionPercent: totalPixels > 0 ? Math.round(regionPixels / totalPixels * 10000) / 100 : 0,
        });
      });
      stats.coveragePercent = totalPixels > 0 ? Math.round(stats.totalRegionPixels / totalPixels * 10000) / 100 : 0;
      return stats;
    };

    window.zoneHasMissingSourceLayer = function zoneHasMissingSourceLayer(zone) {
      // [SPB-MULTILAYER 2026-08-21] multi-aware (mirror of state-zones copy).
      const _ids = (typeof window.zoneSourceLayerIds === 'function') ? window.zoneSourceLayerIds(zone) : (zone && zone.sourceLayer ? [zone.sourceLayer] : []);
      if (!zone || !_ids.length) return false;
      const layers = getPsdLayers();
      if (!Array.isArray(layers)) return true;
      return _ids.some(function (id) { return !layers.some(function (l) { return l && l.id === id; }); });
    };

    window._trackRecentFinishV2 = function _trackRecentFinishV2(finishId) {
      if (!finishId) return;
      const idx = recentFinishesV2.indexOf(finishId);
      if (idx >= 0) recentFinishesV2.splice(idx, 1);
      recentFinishesV2.unshift(finishId);
      if (recentFinishesV2.length > 12) recentFinishesV2.length = 12;
      try { localStorage.setItem('shokker_recent_finishes_v2', JSON.stringify(recentFinishesV2)); } catch (e) {}
      if (getSelectedZoneIndex() >= 0 && typeof window.trackRecentFinishOnZone === 'function') {
        window.trackRecentFinishOnZone(getSelectedZoneIndex(), finishId);
      }
    };
    window.getRecentFinishesV2 = function getRecentFinishesV2() { return recentFinishesV2.slice(); };

    window.isolateAndEditZone = function isolateAndEditZone(index) {
      if (typeof soloZone === 'function') soloZone(index);
      if (typeof selectZone === 'function') selectZone(index);
      if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
      const z = zones()[index] || {};
      showToast('Isolated "' + (z.name || ('Zone ' + (index + 1))) + '" - only this zone visible');
    };

    window._spbShouldAutoFillByName = function _spbShouldAutoFillByName(finishId) {
      if (!finishId) return false;
      const lower = finishId.toLowerCase();
      return lower.includes('colorshoxx') || lower.includes('mortal') || lower.includes('shokk') ||
        lower.includes('paradigm') || lower.includes('candy') || lower.includes('chameleon') ||
        lower.includes('atelier');
    };

    window.setAllZonesTolerance = function setAllZonesTolerance(tolerance) {
      if (typeof tolerance !== 'number' || tolerance < 1 || tolerance > 200) {
        const v = prompt('Tolerance for ALL zones (1-200):', '40');
        tolerance = parseInt(v, 10);
        if (isNaN(tolerance)) return;
      }
      pushZoneUndo('Set all tolerances to ' + tolerance);
      zones().forEach(function (z) {
        z.pickerTolerance = tolerance;
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tolerance;
        if (Array.isArray(z.colors)) z.colors.forEach(c => { c.tolerance = tolerance; });
      });
      renderZones(); preview();
      showToast('All ' + zones().length + ' zones now use +/-' + tolerance + ' tolerance');
    };

    window._enhanceUndoLabel = function _enhanceUndoLabel(action, zoneIndex, value) {
      const z = zones()[zoneIndex] || {};
      const zname = z.name ? '"' + z.name + '"' : 'Zone ' + (zoneIndex + 1);
      return action + ' on ' + zname + (value !== undefined ? ' -> ' + value : '');
    };

    window.getZoneEffectiveTargetCount = function getZoneEffectiveTargetCount(index) {
      const z = zones()[index]; if (!z) return 0;
      if (z.regionMask) {
        let c = 0;
        for (let i = 0; i < z.regionMask.length; i++) if (z.regionMask[i] > 0) c++;
        return c;
      }
      return -1;
    };

    window.getZoneColorPillHTML = function getZoneColorPillHTML(zone) {
      if (!zone) return '';
      let bg = '#444';
      if (zone.colorMode === 'picker' && zone.pickerColor) bg = zone.pickerColor;
      else if (zone.colorMode === 'multi' && zone.colors && zone.colors.length) {
        const colors = zone.colors.slice(0, 4).map(c => c.hex || '#888').join(',');
        bg = 'linear-gradient(90deg, ' + colors + ')';
      } else if (zone.colorMode === 'quick' && zone.color) {
        const qc = (typeof QUICK_COLORS !== 'undefined') ? QUICK_COLORS.find(c => c.value === zone.color) : null;
        bg = qc ? qc.bg : '#888';
      } else if (zone.colorMode === 'special') {
        bg = (zone.color === 'remaining') ? '#555' : 'linear-gradient(135deg,#888,#ccc)';
      }
      return '<span class="zone-color-pill" style="display:inline-block;width:22px;height:10px;border-radius:3px;background:' + bg + ';border:1px solid #333;vertical-align:middle;" title="Zone color"></span>';
    };

    window.getZoneWorkflowHelp = function getZoneWorkflowHelp() {
      return [
        { keys: 'N', action: 'Add new zone' },
        { keys: 'M', action: 'Mute / unmute selected zone' },
        { keys: 'Shift+Delete', action: 'Delete selected zone' },
        { keys: 'Ctrl+Up / Down', action: 'Reorder selected zone' },
        { keys: 'Ctrl+Shift+C / V', action: 'Copy / paste zone settings' },
        { keys: 'Ctrl+Shift+D', action: 'Duplicate selected zone' },
        { keys: '/', action: 'Focus zone search' },
        { keys: 'Ctrl+Z / Y', action: 'Undo / redo' },
        { keys: 'Esc', action: 'Cancel current canvas operation' },
      ];
    };
  }

  function restoreRecentFinishesV2() {
    try {
      const raw = localStorage.getItem('shokker_recent_finishes_v2');
      if (!raw) return;
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) recentFinishesV2.push.apply(recentFinishesV2, arr.slice(0, 12));
    } catch (e) {}
  }
  restoreRecentFinishesV2();

  window.SPBZoneDiagnosticWorkflowControls = { install, recentFinishesV2 };
})();
