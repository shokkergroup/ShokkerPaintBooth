'use strict';

(function () {
  const bulkSelectedZones = new Set();
  const state = { searchQuery: '' };
  const ZONE_PRESETS_KEY = 'shokker_zone_presets';
  const LINK_INTENSITY_PROPS = ['intensity', 'patternOpacity', 'patternSpecMult', 'baseStrength', 'baseSpecStrength'];

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const renderZones = deps.renderZones || window.renderZones;
    const showToast = deps.showToast || window.showToast;
    const preview = deps.triggerPreviewRender || window.triggerPreviewRender || function () {};
    const getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return 0; };
    const setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
    const cloneZoneState = deps.cloneZoneState;
    const ensureZoneShape = deps.ensureZoneShape;
    const getPaintImageData = deps.getPaintImageData || function () { return window.paintImageData || null; };
    const maxZones = deps.maxZones || 50;

    function zones() {
      return getZones();
    }

    function selectedIndexOr(index) {
      return (typeof index === 'number' && index >= 0 && index < zones().length) ? index : getSelectedZoneIndex();
    }

    function getBases() {
      return (typeof BASES !== 'undefined' && Array.isArray(BASES)) ? BASES : [];
    }

    function getMonolithics() {
      return (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) ? MONOLITHICS : [];
    }

    function shiftHex(hex, hueShiftDeg) {
      if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) return hex;
      const r = parseInt(hex.substr(1, 2), 16) / 255;
      const g = parseInt(hex.substr(3, 2), 16) / 255;
      const b = parseInt(hex.substr(5, 2), 16) / 255;
      const max = Math.max(r, g, b);
      const min = Math.min(r, g, b);
      let h = 0;
      let s = 0;
      const l = (max + min) / 2;
      if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
          case r: h = (g - b) / d + (g < b ? 6 : 0); break;
          case g: h = (b - r) / d + 2; break;
          case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
      }
      h = ((h * 360 + hueShiftDeg + 360) % 360) / 360;
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
      const nr = Math.round(hue2rgb(p, q, h + 1 / 3) * 255);
      const ng = Math.round(hue2rgb(p, q, h) * 255);
      const nb = Math.round(hue2rgb(p, q, h - 1 / 3) * 255);
      return '#' + [nr, ng, nb].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
    }

    window.toggleLock = function toggleLock(index, propKey) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length) return;
      const allowed = { lockBase: 1, lockPattern: 1, lockIntensity: 1, lockColor: 1, lockOverlays: 1 };
      if (!allowed[propKey]) return;
      const zone = zones()[index];
      zone[propKey] = !zone[propKey];
      pushZoneUndo((zone[propKey] ? 'Lock ' : 'Unlock ') + propKey.replace('lock', '').toLowerCase());
      renderZones();
      showToast((zone[propKey] ? 'Locked: ' : 'Unlocked: ') + propKey.replace('lock', '').toLowerCase() + ' on ' + zone.name);
    };

    window.zoneCoverageEstimate = function zoneCoverageEstimate(index) {
      const zone = zones()[index];
      if (!zone) return 0;
      const pc = document.getElementById('paintCanvas');
      if (!pc) return 0;
      const totalPixels = pc.width * pc.height;
      if (!totalPixels) return 0;
      if (zone.regionMask) {
        let count = 0;
        for (let i = 0; i < zone.regionMask.length; i++) if (zone.regionMask[i] > 0) count++;
        return Math.round(count / totalPixels * 1000) / 10;
      }
      if (zone.colorMode === 'special' && zone.color === 'everything') return 100;
      const paintImageData = getPaintImageData();
      if (paintImageData && (zone.colorMode === 'picker' || zone.colorMode === 'multi')) {
        const data = paintImageData.data;
        const targets = zone.colorMode === 'multi'
          ? (zone.colors || [])
          : [{ color_rgb: (zone.color && zone.color.color_rgb) || [128, 128, 128], tolerance: zone.pickerTolerance ?? 40 }];
        let hits = 0;
        let sampled = 0;
        const stride = 16;
        for (let i = 0; i < data.length; i += 4 * stride) {
          sampled++;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const a = data[i + 3];
          if (a < 8) continue;
          for (let t = 0; t < targets.length; t++) {
            const tc = targets[t];
            const rgb = tc.color_rgb || [128, 128, 128];
            const tol = tc.tolerance ?? 40;
            if (Math.abs(r - rgb[0]) <= tol && Math.abs(g - rgb[1]) <= tol && Math.abs(b - rgb[2]) <= tol) {
              hits++;
              break;
            }
          }
        }
        return sampled > 0 ? Math.round(hits / sampled * 1000) / 10 : 0;
      }
      return 0;
    };

    window.toggleBulkSelect = function toggleBulkSelect(index) {
      if (bulkSelectedZones.has(index)) bulkSelectedZones.delete(index);
      else bulkSelectedZones.add(index);
      renderZones();
    };
    window.clearBulkSelection = function clearBulkSelection() { bulkSelectedZones.clear(); renderZones(); };
    window.bulkSelectAll = function bulkSelectAll() {
      bulkSelectedZones.clear();
      for (let i = 0; i < zones().length; i++) bulkSelectedZones.add(i);
      renderZones();
    };
    window.bulkApplyFinish = function bulkApplyFinish(finishId) {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected for bulk action', true); return; }
      pushZoneUndo('Bulk apply finish to ' + bulkSelectedZones.size + ' zones');
      const isBase = getBases().find(b => b.id === finishId);
      const isMono = getMonolithics().find(m => m.id === finishId);
      bulkSelectedZones.forEach(function (i) {
        const z = zones()[i]; if (!z || z.lockBase) return;
        if (isBase) { z.base = finishId; z.finish = null; }
        else if (isMono) { z.finish = finishId; z.base = null; }
      });
      renderZones(); preview();
      showToast('Bulk applied finish to ' + bulkSelectedZones.size + ' zones');
    };
    window.bulkSetIntensity = function bulkSetIntensity(value) {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
      pushZoneUndo('Bulk set intensity');
      bulkSelectedZones.forEach(function (i) { if (zones()[i] && !zones()[i].lockIntensity) zones()[i].intensity = value; });
      renderZones(); preview();
      showToast('Bulk set intensity = ' + value + ' on ' + bulkSelectedZones.size + ' zones');
    };
    window.bulkSetTolerance = function bulkSetTolerance(tolerance) {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
      pushZoneUndo('Bulk set tolerance');
      bulkSelectedZones.forEach(function (i) {
        const z = zones()[i]; if (!z) return;
        z.pickerTolerance = tolerance;
        if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tolerance;
        if (Array.isArray(z.colors)) z.colors.forEach(c => { c.tolerance = tolerance; });
      });
      renderZones(); preview();
      showToast('Bulk set tolerance = ' + tolerance + ' on ' + bulkSelectedZones.size + ' zones');
    };
    window.bulkMute = function bulkMute() {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
      pushZoneUndo('Bulk mute');
      bulkSelectedZones.forEach(function (i) { if (zones()[i]) zones()[i].muted = true; });
      renderZones(); preview();
    };
    window.bulkUnmute = function bulkUnmute() {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
      pushZoneUndo('Bulk unmute');
      bulkSelectedZones.forEach(function (i) { if (zones()[i]) zones()[i].muted = false; });
      renderZones(); preview();
    };
    window.bulkDelete = function bulkDelete() {
      if (bulkSelectedZones.size === 0) { showToast('No zones selected', true); return; }
      if (bulkSelectedZones.size >= zones().length) { showToast('Cannot delete all zones - keep at least one', true); return; }
      if (!confirm('Delete ' + bulkSelectedZones.size + ' selected zones?')) return;
      pushZoneUndo('Bulk delete ' + bulkSelectedZones.size + ' zones');
      const indices = Array.from(bulkSelectedZones).sort(function (a, b) { return b - a; });
      const selectedZoneIndex = getSelectedZoneIndex();
      const deletedBefore = indices.filter(i => i < selectedZoneIndex).length;
      indices.forEach(function (i) { zones().splice(i, 1); });
      bulkSelectedZones.clear();
      setSelectedZoneIndex(Math.max(0, Math.min(selectedZoneIndex - deletedBefore, zones().length - 1)));
      renderZones(); preview();
      showToast('Bulk deleted ' + indices.length + ' zones');
    };

    function loadZonePresets() {
      try { return JSON.parse(localStorage.getItem(ZONE_PRESETS_KEY) || '[]'); } catch (e) { return []; }
    }
    function saveZonePresetsList(arr) {
      try { localStorage.setItem(ZONE_PRESETS_KEY, JSON.stringify(arr)); } catch (e) {}
    }
    window.saveZonePreset = function saveZonePreset(presetName) {
      if (!presetName) presetName = prompt("Name this preset (e.g. \"Kyle's Setup\"):");
      if (!presetName || !presetName.trim()) return;
      const presets = loadZonePresets();
      const snapshot = JSON.parse(JSON.stringify(zones().map(z => ({ ...z, regionMask: null, spatialMask: null }))));
      const entry = { name: presetName.trim(), savedAt: Date.now(), zoneCount: zones().length, snapshot };
      const existingIdx = presets.findIndex(p => p.name === entry.name);
      if (existingIdx >= 0) {
        if (!confirm('Overwrite existing preset "' + entry.name + '"?')) return;
        presets[existingIdx] = entry;
      } else {
        presets.push(entry);
      }
      saveZonePresetsList(presets);
      showToast('Saved preset: ' + entry.name);
    };
    window.loadZonePreset = function loadZonePreset(presetName) {
      const preset = loadZonePresets().find(p => p.name === presetName);
      if (!preset) { showToast('Preset not found: ' + presetName, true); return; }
      if (!confirm('Replace current ' + zones().length + ' zones with preset "' + preset.name + '" (' + preset.zoneCount + ' zones)?')) return;
      pushZoneUndo('Load preset: ' + preset.name);
      zones().length = 0;
      preset.snapshot.forEach(function (z) {
        const restored = ensureZoneShape(z, { includeRegionMask: false, includeSpatialMask: false });
        restored.regionMask = null;
        restored.spatialMask = null;
        zones().push(restored);
      });
      setSelectedZoneIndex(0);
      renderZones(); preview();
      showToast('Loaded preset: ' + preset.name + ' (' + preset.zoneCount + ' zones)');
    };
    window.deleteZonePreset = function deleteZonePreset(presetName) {
      if (!confirm('Delete preset "' + presetName + '"?')) return;
      saveZonePresetsList(loadZonePresets().filter(p => p.name !== presetName));
      showToast('Deleted preset: ' + presetName);
    };
    window.listZonePresets = function listZonePresets() { return loadZonePresets(); };

    window.duplicateZoneWithHueOffset = function duplicateZoneWithHueOffset(index, hueShiftDeg) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length) return;
      if (typeof hueShiftDeg !== 'number') {
        const v = prompt('Hue shift in degrees (-180 to 180):', '60');
        if (v === null) return;
        hueShiftDeg = parseFloat(v);
        if (isNaN(hueShiftDeg)) { showToast('Invalid hue value', true); return; }
      }
      pushZoneUndo('Duplicate with hue offset ' + hueShiftDeg + 'deg');
      const src = zones()[index];
      const clone = cloneZoneState(src, {
        preserveId: false,
        includeRegionMask: true,
        includeSpatialMask: true,
        includePatternStrengthMap: true,
      });
      clone.name = src.name + ' (hue+' + Math.round(hueShiftDeg) + ')';
      if (window.SPBStableZoneSeeds) window.SPBStableZoneSeeds.assignFresh(zones(), clone, window._isSuppressedLegacyZone, window._zoneHasRenderableMaterial, window._renderMaskHasPixels);
      if (clone.pickerColor) clone.pickerColor = shiftHex(clone.pickerColor, hueShiftDeg);
      if (clone.color && typeof clone.color === 'object' && !Array.isArray(clone.color) && clone.color.color_rgb) {
        const newHex = shiftHex('#' + clone.color.color_rgb.map(c => c.toString(16).padStart(2, '0')).join(''), hueShiftDeg);
        clone.color = {
          color_rgb: [parseInt(newHex.substr(1, 2), 16), parseInt(newHex.substr(3, 2), 16), parseInt(newHex.substr(5, 2), 16)],
          tolerance: clone.color.tolerance ?? 40,
        };
      }
      if (Array.isArray(clone.colors)) {
        clone.colors = clone.colors.map(function (c) {
          const newHex = shiftHex(c.hex || '#888888', hueShiftDeg);
          return {
            color_rgb: [parseInt(newHex.substr(1, 2), 16), parseInt(newHex.substr(3, 2), 16), parseInt(newHex.substr(5, 2), 16)],
            tolerance: c.tolerance ?? 40,
            hex: newHex,
          };
        });
      }
      clone.baseHueOffset = ((clone.baseHueOffset || 0) + hueShiftDeg + 540) % 360 - 180;
      zones().splice(index + 1, 0, clone);
      setSelectedZoneIndex(index + 1);
      renderZones();
      showToast('Duplicated with hue +' + Math.round(hueShiftDeg) + 'deg');
    };

    window.propagateIntensityToLinked = function propagateIntensityToLinked(sourceIndex) {
      const z = zones()[sourceIndex]; if (!z || !z.linkGroup) return;
      zones().forEach(function (other, i) {
        if (i === sourceIndex || other.linkGroup !== z.linkGroup) return;
        LINK_INTENSITY_PROPS.forEach(function (p) { if (z[p] !== undefined) other[p] = z[p]; });
      });
    };
    window.unlinkAllZones = function unlinkAllZones() {
      if (!confirm('Unlink ALL zones from their groups?')) return;
      pushZoneUndo('Unlink all zones');
      zones().forEach(function (z) { delete z.linkGroup; });
      renderZones();
      showToast('All link groups removed');
    };

    let zoneClipboard = null;
    window.copyZoneToClipboard = function copyZoneToClipboard(index) {
      index = selectedIndexOr(index);
      const z = zones()[index];
      if (!z) { showToast('No zone to copy', true); return; }
      zoneClipboard = cloneZoneState({ ...z, colors: z.colors || [] }, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
      });
      zoneClipboard._copiedAt = Date.now();
      zoneClipboard._copiedFromName = z.name;
      showToast('Copied "' + z.name + '" settings - Ctrl+Shift+V to paste');
    };
    window.pasteZoneFromClipboard = function pasteZoneFromClipboard(index) {
      if (!zoneClipboard) { showToast('Nothing in zone clipboard - copy a zone first', true); return; }
      index = selectedIndexOr(index);
      const target = zones()[index];
      pushZoneUndo('Paste zone settings to "' + target.name + '"');
      const preserveName = target.name;
      const preserveId = target.id;
      const preserveMask = target.regionMask;
      const preserveSpatial = target.spatialMask;
      const preserveSeedSlot = target.renderSeedIndex;
      const hadSeedSlot = Object.prototype.hasOwnProperty.call(target, 'renderSeedIndex');
      const fresh = cloneZoneState(zoneClipboard, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
      });
      delete fresh._copiedAt; delete fresh._copiedFromName;
      Object.keys(fresh).forEach(function (k) { target[k] = fresh[k]; });
      target.id = preserveId;
      target.name = preserveName;
      target.regionMask = preserveMask;
      target.spatialMask = preserveSpatial;
      if (hadSeedSlot) target.renderSeedIndex = preserveSeedSlot; else delete target.renderSeedIndex;
      renderZones(); preview();
      showToast('Pasted settings from "' + zoneClipboard._copiedFromName + '" -> "' + target.name + '"');
    };
    window.pasteZoneAsNew = function pasteZoneAsNew() {
      if (!zoneClipboard) { showToast('Nothing in zone clipboard', true); return; }
      if (zones().length >= maxZones) { showToast('Zone limit reached', true); return; }
      pushZoneUndo('Paste as new zone');
      const fresh = cloneZoneState(zoneClipboard, {
        preserveId: false,
        includeRegionMask: false,
        includeSpatialMask: false,
        includePatternStrengthMap: true,
      });
      delete fresh._copiedAt;
      fresh.name = (zoneClipboard._copiedFromName || 'Zone') + ' (paste)';
      delete fresh._copiedFromName;
      if (window.SPBStableZoneSeeds) window.SPBStableZoneSeeds.assignFresh(zones(), fresh, window._isSuppressedLegacyZone, window._zoneHasRenderableMaterial, window._renderMaskHasPixels);
      fresh.regionMask = null;
      fresh.spatialMask = null;
      zones().push(fresh);
      setSelectedZoneIndex(zones().length - 1);
      renderZones(); preview();
      showToast('Pasted as new zone: ' + fresh.name);
    };

    window.exportSingleZone = function exportSingleZone(index) {
      index = selectedIndexOr(index);
      const z = zones()[index]; if (!z) return;
      const data = { __spbZone: 1, version: 1, exportedAt: Date.now(), zone: { ...z, regionMask: null, spatialMask: null } };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      const safeName = (z.name || 'zone').replace(/[^a-z0-9_-]+/gi, '_').toLowerCase();
      a.download = 'spb_zone_' + safeName + '_' + Date.now() + '.json';
      a.click(); URL.revokeObjectURL(a.href);
      showToast('Exported zone: ' + z.name);
    };
    window.importZoneFromFile = function importZoneFromFile() {
      const inp = document.createElement('input');
      inp.type = 'file'; inp.accept = '.json,application/json';
      inp.onchange = function (e) {
        const f = e.target.files && e.target.files[0]; if (!f) return;
        const reader = new FileReader();
        reader.onload = function (ev) {
          try {
            const data = JSON.parse(ev.target.result);
            if (!data || !data.__spbZone || !data.zone) { showToast('Not a valid SPB zone JSON', true); return; }
            if (zones().length >= maxZones) { showToast('Zone limit reached', true); return; }
            pushZoneUndo('Import zone');
            const z = cloneZoneState(data.zone, {
              preserveId: false,
              includeRegionMask: false,
              includeSpatialMask: false,
              includePatternStrengthMap: true,
            });
            z.regionMask = null;
            z.spatialMask = null;
            z.name = (z.name || 'Imported Zone') + ' (imported)';
            if (window.SPBStableZoneSeeds) window.SPBStableZoneSeeds.assignFresh(zones(), z, window._isSuppressedLegacyZone, window._zoneHasRenderableMaterial, window._renderMaskHasPixels);
            zones().push(z);
            setSelectedZoneIndex(zones().length - 1);
            renderZones(); preview();
            showToast('Imported zone: ' + z.name);
          } catch (err) { showToast('Import failed: ' + err.message, true); }
        };
        reader.readAsText(f);
      };
      inp.click();
    };

    window.setZoneSearchQuery = function setZoneSearchQuery(q) {
      state.searchQuery = (q || '').toLowerCase().trim();
      window._zoneSearchQuery = state.searchQuery;
      const cards = document.querySelectorAll('#zoneList .zone-card');
      cards.forEach(function (card, i) {
        if (!state.searchQuery) { card.style.display = ''; return; }
        const z = zones()[i]; if (!z) return;
        const haystack = [z.name, z.base, z.finish, z.pattern, z.color, z.colorMode, z.pickerColor].filter(Boolean).join(' ').toLowerCase();
        card.style.display = haystack.includes(state.searchQuery) ? '' : 'none';
      });
    };
    window.clearZoneSearch = function clearZoneSearch() {
      state.searchQuery = '';
      window._zoneSearchQuery = '';
      const inp = document.getElementById('zoneSearchInput');
      if (inp) inp.value = '';
      window.setZoneSearchQuery('');
    };
    window.collapseAllZones = function collapseAllZones() {
      document.querySelectorAll('#zoneList .zone-card').forEach(function (c) {
        c.classList.add('zone-card-collapsed'); c.classList.remove('expanded');
      });
      showToast('All zones collapsed');
    };
    window.expandAllZones = function expandAllZones() {
      document.querySelectorAll('#zoneList .zone-card').forEach(function (c) {
        c.classList.remove('zone-card-collapsed'); c.classList.add('expanded');
      });
      showToast('All zones expanded');
    };

    window.suggestZoneName = function suggestZoneName(zone) {
      if (!zone) return 'Zone';
      const finishId = zone.finish || zone.base || '';
      const lookup = getMonolithics().find(m => m.id === finishId) || getBases().find(b => b.id === finishId);
      const finishName = lookup ? lookup.name : finishId;
      const finishWord = (finishName || '').replace(/v\d+$/i, '').replace(/[_-]+/g, ' ').trim().split(/\s+/)[0] || '';
      const cap = finishWord ? (finishWord.charAt(0).toUpperCase() + finishWord.slice(1).toLowerCase()) : '';
      const colorWord = (function () {
        if (zone.colorMode === 'quick' && zone.color) return String(zone.color).charAt(0).toUpperCase() + String(zone.color).slice(1);
        if (zone.colorMode === 'special' && zone.color === 'remaining') return 'Remainder';
        if (zone.colorMode === 'picker' && zone.pickerColor) return zone.pickerColor.toUpperCase();
        return '';
      })();
      return [cap, colorWord, 'Zone'].filter(Boolean).slice(0, 2).join(' ') || 'Zone';
    };
    window.autoNameZone = function autoNameZone(index) {
      const z = zones()[index]; if (!z) return;
      const newName = window.suggestZoneName(z);
      if (!newName || newName === z.name) { showToast('No better name available', true); return; }
      pushZoneUndo('Auto-name zone');
      z.name = newName;
      renderZones();
      showToast('Renamed to "' + newName + '"');
    };
    window.autoNameAllZones = function autoNameAllZones() {
      pushZoneUndo('Auto-name all zones');
      let renamed = 0;
      zones().forEach(function (z) {
        const n = window.suggestZoneName(z);
        if (n && n !== z.name && (z.base || z.finish)) { z.name = n; renamed++; }
      });
      renderZones();
      showToast('Auto-renamed ' + renamed + ' zones');
    };
    window.setTolerancePreset = function setTolerancePreset(index, preset) {
      if (typeof index !== 'number') index = getSelectedZoneIndex();
      const z = zones()[index]; if (!z) return;
      const map = { exact: 0, tight: 5, default: 40, loose: 80 };
      if (!Object.prototype.hasOwnProperty.call(map, preset)) return;
      const tol = map[preset];
      pushZoneUndo('Set tolerance preset: ' + preset);
      z.pickerTolerance = tol;
      if (z.color && typeof z.color === 'object' && !Array.isArray(z.color)) z.color.tolerance = tol;
      if (Array.isArray(z.colors)) z.colors.forEach(function (c) { c.tolerance = tol; });
      renderZones(); preview();
      showToast('Tolerance: ' + preset + ' (+/-' + tol + ')');
    };
    window.renumberZones = function renumberZones() {
      pushZoneUndo('Renumber zones');
      let counter = 1;
      zones().forEach(function (z) {
        if (/^Zone \d+$/.test(z.name || '')) { z.name = 'Zone ' + counter; counter++; }
      });
      renderZones();
      showToast('Renumbered generic zones (' + (counter - 1) + ' updated)');
    };

    return { bulkSelectedZones, state };
  }

  window.SPBZoneProductivityControls = { install, selection: bulkSelectedZones, state };
})();
