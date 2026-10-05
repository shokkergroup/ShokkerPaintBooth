'use strict';

(function () {
  const BASE_PATTERN_SUGGESTIONS = {
    matte: ['none', 'matte_grain', 'hex_mesh'],
    gloss: ['none', 'flake_fine', 'metallic_subtle'],
    chrome: ['none', 'brushed_horizontal', 'mirror_distort'],
    metallic: ['flake_fine', 'flake_medium', 'flake_coarse'],
    pearl: ['pearl_shimmer', 'pearl_fine'],
    candy: ['flake_medium', 'candy_drift'],
    flake: ['flake_fine', 'flake_medium', 'flake_coarse'],
  };

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const renderZones = deps.renderZones || window.renderZones;
    const showToast = deps.showToast || window.showToast || function () {};
    const preview = deps.triggerPreviewRender || window.triggerPreviewRender || function () {};
    const getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return 0; };
    const setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
    const cloneZoneState = deps.cloneZoneState;
    const getPaintImageData = deps.getPaintImageData || function () { return window.paintImageData || null; };

    function zones() {
      return getZones();
    }

    function selectedIndexOr(index) {
      return (typeof index === 'number' && index >= 0 && index < zones().length) ? index : getSelectedZoneIndex();
    }

    function shiftRgbHue(rgb, deg) {
      const hex = '#' + rgb.map(c => c.toString(16).padStart(2, '0')).join('');
      function toHsl(h) {
        const r = parseInt(h.substr(1, 2), 16) / 255;
        const g = parseInt(h.substr(3, 2), 16) / 255;
        const b = parseInt(h.substr(5, 2), 16) / 255;
        const mx = Math.max(r, g, b);
        const mn = Math.min(r, g, b);
        let hh = 0;
        let s = 0;
        const l = (mx + mn) / 2;
        if (mx !== mn) {
          const d = mx - mn;
          s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
          switch (mx) {
            case r: hh = (g - b) / d + (g < b ? 6 : 0); break;
            case g: hh = (b - r) / d + 2; break;
            case b: hh = (r - g) / d + 4; break;
          }
          hh /= 6;
        }
        return [hh * 360, s, l];
      }
      function fromHsl(h, s, l) {
        h = (((h % 360) + 360) % 360) / 360;
        function hue2rgb(p, q, t) {
          if (t < 0) t += 1;
          if (t > 1) t -= 1;
          if (t < 1 / 6) return p + (q - p) * 6 * t;
          if (t < 1 / 2) return q;
          if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
          return p;
        }
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        return [
          Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
          Math.round(hue2rgb(p, q, h) * 255),
          Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
        ];
      }
      const [h, s, l] = toHsl(hex);
      return fromHsl(h + deg, s, l);
    }

    window.getZoneSummary = function getZoneSummary(index) {
      const z = zones()[index]; if (!z) return '';
      const parts = [];
      if (z.muted) parts.push('MUTED');
      if (z.base) parts.push('Base: ' + z.base);
      if (z.finish) parts.push('Finish: ' + z.finish);
      if (z.pattern && z.pattern !== 'none') parts.push('Pattern: ' + z.pattern);
      if (z.colorMode === 'picker' && z.pickerColor) parts.push('Color: ' + z.pickerColor);
      if (z.colorMode === 'multi') parts.push((z.colors || []).length + ' colors');
      if (z.colorMode === 'special') parts.push('Special: ' + z.color);
      if (z.regionMask && z.regionMask.some(v => v > 0)) parts.push('Has region');
      if (z.linkGroup) parts.push('Linked');
      if (z.zoneSpecMapPath) parts.push('Spec source');
      if ((z.patternStack || []).length) parts.push((z.patternStack || []).length + ' pattern layers');
      if ((z.specPatternStack || []).length) parts.push((z.specPatternStack || []).length + ' spec patterns');
      return parts.join(' | ') || 'Empty zone';
    };

    window.previewImportedConfig = function previewImportedConfig(json) {
      try {
        const cfg = typeof json === 'string' ? JSON.parse(json) : json;
        if (!cfg || !cfg.zones) return null;
        return {
          zoneCount: cfg.zones.length,
          driver: cfg.driverName || cfg.driver_name || 'unknown',
          zoneNames: cfg.zones.map(z => z.name).slice(0, 10),
          hasMore: cfg.zones.length > 10,
          saveTime: cfg._autosave_time ? new Date(cfg._autosave_time).toLocaleString() : 'unknown',
        };
      } catch (e) { return null; }
    };

    window.showConfigImportPreview = function showConfigImportPreview(json) {
      const previewInfo = window.previewImportedConfig(json);
      if (!previewInfo) { showToast('Invalid config JSON', true); return false; }
      const msg = 'Import this config?\n\n' +
        'Zones: ' + previewInfo.zoneCount + '\n' +
        'Driver: ' + previewInfo.driver + '\n' +
        'Saved: ' + previewInfo.saveTime + '\n\n' +
        'First zones:\n' + previewInfo.zoneNames.map((n, i) => (i + 1) + '. ' + n).join('\n') +
        (previewInfo.hasMore ? '\n... +' + (previewInfo.zoneCount - 10) + ' more' : '');
      return confirm(msg);
    };

    window.bringZoneToFront = function bringZoneToFront(index) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length || index === 0) return;
      pushZoneUndo('Bring zone to front');
      const moved = zones().splice(index, 1)[0];
      zones().unshift(moved);
      setSelectedZoneIndex(0);
      renderZones(); preview();
    };

    window.sendZoneToBack = function sendZoneToBack(index) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length || index === zones().length - 1) return;
      pushZoneUndo('Send zone to back');
      const moved = zones().splice(index, 1)[0];
      zones().push(moved);
      setSelectedZoneIndex(zones().length - 1);
      renderZones(); preview();
    };

    window.getSpecialColorExplanation = function getSpecialColorExplanation(value) {
      if (value === 'remaining') return 'Catches every pixel NOT already claimed by a zone above this one. Use as a safety net for unclaimed body paint.';
      if (value === 'everything') return 'Targets ALL pixels on the car (overrides other zones). Use sparingly - typically for a base monolithic finish covering the whole car.';
      return value;
    };

    window.getZoneRenderOrder = function getZoneRenderOrder() {
      return zones().map(function (z, i) {
        return {
          order: i + 1,
          name: z.name,
          status: typeof window.getZoneStatus === 'function' ? window.getZoneStatus(z) : 'unknown',
          muted: !!z.muted,
          specialFlag: z.colorMode === 'special' ? z.color : null,
        };
      });
    };

    window.invertAllZoneMutes = function invertAllZoneMutes() {
      pushZoneUndo('Invert all mutes');
      zones().forEach(function (z) { z.muted = !z.muted; });
      renderZones(); preview();
      showToast('Inverted all mute states');
    };

    window.setZoneTag = function setZoneTag(index, tag) {
      index = selectedIndexOr(index);
      const z = zones()[index]; if (!z) return;
      pushZoneUndo('Set tag: ' + tag);
      z.tag = tag;
      renderZones();
    };
    window.getZonesByTag = function getZonesByTag(tag) { return zones().filter(z => z.tag === tag); };

    window.suggestSmartTolerance = function suggestSmartTolerance(hex) {
      const paintImageData = getPaintImageData();
      if (!hex || !paintImageData) return 40;
      const r0 = parseInt(hex.substr(1, 2), 16);
      const g0 = parseInt(hex.substr(3, 2), 16);
      const b0 = parseInt(hex.substr(5, 2), 16);
      const data = paintImageData.data;
      let nearMatches = 0;
      let totalSamples = 0;
      const stride = 32;
      for (let i = 0; i < data.length; i += 4 * stride) {
        if (data[i + 3] < 32) continue;
        totalSamples++;
        const dr = Math.abs(data[i] - r0);
        const dg = Math.abs(data[i + 1] - g0);
        const db = Math.abs(data[i + 2] - b0);
        if (dr < 80 && dg < 80 && db < 80) nearMatches++;
      }
      if (totalSamples === 0) return 40;
      const ratio = nearMatches / totalSamples;
      if (ratio > 0.4) return 15;
      if (ratio > 0.2) return 25;
      if (ratio > 0.1) return 40;
      return 60;
    };

    window.duplicateZoneWithColor = function duplicateZoneWithColor(index) {
      index = selectedIndexOr(index);
      const newHex = prompt('New hex color for the duplicate (e.g. #FF3366):', '#FFFFFF');
      if (!newHex) return;
      if (!/^#?[0-9A-Fa-f]{6}$/.test(newHex)) { showToast('Invalid hex', true); return; }
      pushZoneUndo('Duplicate with new color');
      const src = zones()[index];
      const clone = cloneZoneState(src, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
      });
      const norm = newHex.startsWith('#') ? newHex : '#' + newHex;
      clone.name = src.name + ' (' + norm.toUpperCase() + ')';
      if (window.SPBStableZoneSeeds) window.SPBStableZoneSeeds.assignFresh(zones(), clone, window._isSuppressedLegacyZone, window._zoneHasRenderableMaterial, window._renderMaskHasPixels);
      clone.regionMask = null;
      clone.pickerColor = norm.toUpperCase();
      clone.colorMode = 'picker';
      clone.colors = [];
      clone.color = {
        color_rgb: [parseInt(norm.substr(1, 2), 16), parseInt(norm.substr(3, 2), 16), parseInt(norm.substr(5, 2), 16)],
        tolerance: clone.pickerTolerance ?? 40,
      };
      zones().splice(index + 1, 0, clone);
      setSelectedZoneIndex(index + 1);
      renderZones(); preview();
      showToast('Duplicated with color ' + norm.toUpperCase());
    };

    window.getSuggestedPatternsForBase = function getSuggestedPatternsForBase(baseId) {
      const cat = (baseId || '').toLowerCase();
      for (const key in BASE_PATTERN_SUGGESTIONS) if (cat.includes(key)) return BASE_PATTERN_SUGGESTIONS[key];
      return ['none'];
    };

    (function injectZoneFlashCSS() {
      if (document.getElementById('spbZoneFlashCSS')) return;
      const style = document.createElement('style');
      style.id = 'spbZoneFlashCSS';
      style.textContent = '@keyframes zoneFlash { 0%{box-shadow:0 0 0 2px #ffaa00;} 50%{box-shadow:0 0 16px 4px #ffaa00aa;} 100%{box-shadow:0 0 0 2px transparent;} }' +
        ' .zone-bulk-selected { outline: 2px dashed #00ccff; outline-offset: 2px; }' +
        ' .zone-status-badge { transition: all 0.2s ease; }' +
        ' .zone-warn { color:#ff8c1a; font-weight:bold; }' +
        ' #zoneSearchInput { background:#1a1a2e; color:#fff; border:1px solid #333; padding:4px 8px; border-radius:4px; font-size:11px; width:140px; }' +
        ' #zoneSearchInput:focus { border-color:#E87A20; outline:none; }';
      document.head.appendChild(style);
    })();

    window.getUnrenderableZoneCount = function getUnrenderableZoneCount() {
      return zones().filter(function (z) {
        if (z.muted) return true;
        const hasFinish = !!(z.base || z.finish);
        const hasColor = z.color !== null || z.colorMode === 'multi' || z.colorMode === 'special';
        const hasRegion = z.regionMask && z.regionMask.some(v => v > 0);
        return !hasFinish || (!hasColor && !hasRegion);
      }).length;
    };

    window.touchZoneTimestamp = function touchZoneTimestamp(index) {
      index = selectedIndexOr(index);
      if (zones()[index]) zones()[index]._lastModified = Date.now();
    };
    window.getZoneAge = function getZoneAge(index) {
      index = selectedIndexOr(index);
      const t = (zones()[index] && zones()[index]._lastModified) || 0;
      if (!t) return 'never';
      const ago = Math.round((Date.now() - t) / 1000);
      return ago < 60 ? ago + 's ago' : ago < 3600 ? Math.round(ago / 60) + 'm ago' : Math.round(ago / 3600) + 'h ago';
    };

    window.bulkShiftMultiColors = function bulkShiftMultiColors(index, hueShift) {
      index = selectedIndexOr(index);
      const z = zones()[index];
      if (!z || !Array.isArray(z.colors) || z.colors.length === 0) { showToast('No multi-color stack', true); return; }
      pushZoneUndo('Shift all colors hue ' + hueShift + 'deg');
      z.colors.forEach(function (c) {
        c.color_rgb = shiftRgbHue(c.color_rgb, hueShift);
        c.hex = '#' + c.color_rgb.map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase();
      });
      renderZones(); preview();
      showToast('Shifted ' + z.colors.length + ' colors by ' + hueShift + 'deg');
    };

    window.previewImportedZone = function previewImportedZone(jsonStr) {
      try {
        const data = JSON.parse(jsonStr);
        if (!data || !data.__spbZone || !data.zone) return null;
        return {
          name: data.zone.name,
          base: data.zone.base,
          finish: data.zone.finish,
          pattern: data.zone.pattern,
          exportedAt: data.exportedAt ? new Date(data.exportedAt).toLocaleString() : 'unknown',
        };
      } catch (e) { return null; }
    };
  }

  window.SPBZoneAdvancedWorkflowControls = { install, BASE_PATTERN_SUGGESTIONS };
})();
