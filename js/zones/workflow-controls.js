'use strict';

(function () {
  const perZoneUndoStacks = {};
  const perZoneRecentFinishes = {};
  const state = { autoRestorePrompted: false, dirty: false };

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const pushZoneUndoCoalesced = deps.pushZoneUndoCoalesced || pushZoneUndo;
    const renderZones = deps.renderZones || window.renderZones;
    const showToast = deps.showToast || window.showToast || function () {};
    const preview = deps.triggerPreviewRender || window.triggerPreviewRender || function () {};
    const getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return 0; };
    const setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
    const cloneZoneState = deps.cloneZoneState;
    const maxZones = deps.maxZones || 50;
    const addZone = deps.addZone || window.addZone;
    const deleteZone = deps.deleteZone || window.deleteZone;
    const duplicateZone = deps.duplicateZone || window.duplicateZone;
    const moveZoneUp = deps.moveZoneUp || window.moveZoneUp;
    const moveZoneDown = deps.moveZoneDown || window.moveZoneDown;
    const toggleZoneMute = deps.toggleZoneMute || window.toggleZoneMute;
    const isTextEntryTarget = deps.isTextEntryTarget || function () { return false; };
    const validateZonesBeforeRender = deps.validateZonesBeforeRender || window.validateZonesBeforeRender || function () { return []; };
    const setHexColor = deps.setHexColor || window.setHexColor;
    const loadConfigFromObj = deps.loadConfigFromObj || window.loadConfigFromObj;
    const getPaintImageData = deps.getPaintImageData || function () { return window.paintImageData || null; };
    const getPsdLayers = deps.getPsdLayers || function () { return window._psdLayers || []; };
    const zoneHasMissingSourceLayer = deps.zoneHasMissingSourceLayer || window.zoneHasMissingSourceLayer || function () { return false; };
    const maskAny = deps.maskAny || function (mask) { return !!(mask && mask.some(function (value) { return value > 0; })); };
    const zoneHasMaterialStack = deps.zoneHasMaterialStack || window.zoneHasMaterialStack || function (zone) { return !!(zone && ((Array.isArray(zone.materialStack) && zone.materialStack.length) || (Array.isArray(zone.material_stack) && zone.material_stack.length))); };
    const zoneHasAnyMaterial = deps.zoneHasAnyMaterial || window.zoneHasAnyMaterial || function (zone) { return !!(zone && (zone.base || zone.finish || zoneHasMaterialStack(zone))); };
    const zoneMaterialMixDisplay = deps.zoneMaterialMixDisplay || window.zoneMaterialMixDisplay || function (zone) {
      const stack = Array.isArray(zone && zone.materialStack) ? zone.materialStack
        : (Array.isArray(zone && zone.material_stack) ? zone.material_stack : []);
      return stack.map(function (row) {
        const id = (row && typeof row === 'object') ? (row.id || row.key || '') : row;
        return { name: String(id || '').replace(/^mono:/, '') || '?' };
      });
    };

    function zones() {
      return getZones();
    }

    function selectedIndexOr(index) {
      return (typeof index === 'number' && index >= 0 && index < zones().length) ? index : getSelectedZoneIndex();
    }

    window.getZoneStatus = function getZoneStatus(zone) {
      if (!zone) return 'no_finish';
      if (zone.muted) return 'muted';
      if (zoneHasMissingSourceLayer(zone)) return 'missing_source_layer';
      const hasFinish = zoneHasAnyMaterial(zone);
      const hasColor = zone.color !== null || zone.colorMode === 'multi' || zone.colorMode === 'special';
      const hasRegion = zone.regionMask && maskAny(zone.regionMask);
      if (!hasFinish && !hasColor && !hasRegion) return 'incomplete';
      if (!hasFinish) return 'no_finish';
      if (!hasColor && !hasRegion) return 'no_pixels';
      return 'ok';
    };

    window.getZoneStatusBadgeHTML = function getZoneStatusBadgeHTML(zone) {
      const s = window.getZoneStatus(zone);
      const emDash = String.fromCharCode(0x2014);
      const map = {
        ok: { color: '#22c55e', icon: '\\u2713', label: 'Will render' },
        missing_source_layer: { color: '#ff4444', icon: '\\u26A0', label: 'Missing source layer - zone will paint nothing' },
        no_finish: { color: '#ff8c1a', icon: '\\u26A0', label: 'No finish assigned' },
        no_pixels: { color: '#ff8c1a', icon: '\\u26A0', label: 'No color/region ' + emDash + ' zone targets nothing' },
        muted: { color: '#666', icon: 'x', label: 'Muted (excluded from render)' },
        incomplete: { color: '#888', icon: '.', label: 'Empty zone ' + emDash + ' set color & finish' },
      };
      const m = map[s] || map.incomplete;
      return '<span class="zone-status-badge" data-status="' + s + '" title="' + m.label +
        '" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + m.color +
        ';margin-right:3px;vertical-align:middle;box-shadow:0 0 4px ' + m.color + '88;"></span>';
    };

    window.getZoneDiagnostic = function getZoneDiagnostic(zone) {
      if (!zone) return 'Zone is missing.';
      if (zone.muted) return 'Zone is muted. Click the eye icon to unmute.';
      if (zoneHasMissingSourceLayer(zone)) return 'Zone is restricted to a missing PSD layer. Rebind the zone to an existing layer or clear the layer restriction before rendering.';
      const hasFinish = zoneHasAnyMaterial(zone);
      const hasColor = zone.color !== null || zone.colorMode === 'multi' || zone.colorMode === 'special';
      const hasRegion = zone.regionMask && maskAny(zone.regionMask);
      if (!hasFinish && !hasColor && !hasRegion) return 'Empty zone — pick a base finish AND a color (or draw a region).';
      if (!hasFinish) return 'No finish assigned. Pick a base material from the BASE row to make this zone visible.';
      if (!hasColor && !hasRegion) return 'No color or region defined — this zone will not affect any pixels. Use Pick Color or Draw Region.';
      if (!zone.base && !zone.finish && zoneHasMaterialStack(zone)) {
        const mixNames = zoneMaterialMixDisplay(zone).map(function (entry) { return entry.name; });
        return 'Material mix (' + mixNames.join(' + ') + ') — set in Easy Mode, renders as-is. Choose a Base Material here to replace the whole mix with one finish.';
      }
      return 'Zone is ready to render.';
    };

    window.pushPerZoneUndo = function pushPerZoneUndo(index, label) {
      index = selectedIndexOr(index);
      if (!perZoneUndoStacks[index]) perZoneUndoStacks[index] = [];
      perZoneUndoStacks[index].push({
        label,
        timestamp: Date.now(),
        snapshot: JSON.parse(JSON.stringify({ ...zones()[index], regionMask: null })),
      });
      if (perZoneUndoStacks[index].length > 20) perZoneUndoStacks[index].shift();
    };

    window.undoPerZone = function undoPerZone(index) {
      index = selectedIndexOr(index);
      const stack = perZoneUndoStacks[index];
      if (!stack || !stack.length) { showToast('No per-zone history for this zone', true); return; }
      const entry = stack.pop();
      const mask = zones()[index].regionMask;
      Object.assign(zones()[index], entry.snapshot);
      zones()[index].regionMask = mask;
      renderZones(); preview();
      showToast('Per-zone undo: ' + entry.label);
    };

    document.addEventListener('keydown', function zoneWorkflowCopyReorderShortcuts(e) {
      if (e.defaultPrevented || isTextEntryTarget(e.target)) return;
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === 'ArrowUp') {
        e.preventDefault();
        if (getSelectedZoneIndex() > 0 && typeof moveZoneUp === 'function') moveZoneUp(getSelectedZoneIndex());
      } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === 'ArrowDown') {
        e.preventDefault();
        if (getSelectedZoneIndex() < zones().length - 1 && typeof moveZoneDown === 'function') moveZoneDown(getSelectedZoneIndex());
      } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c')) {
        e.preventDefault();
        if (typeof window.copyZoneToClipboard === 'function') window.copyZoneToClipboard(getSelectedZoneIndex());
      } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'V' || e.key === 'v')) {
        e.preventDefault();
        if (typeof window.pasteZoneFromClipboard === 'function') window.pasteZoneFromClipboard(getSelectedZoneIndex());
      } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
        e.preventDefault();
        if (typeof duplicateZone === 'function') duplicateZone(getSelectedZoneIndex());
      } else if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const inp = document.getElementById('zoneSearchInput');
        if (inp) { e.preventDefault(); inp.focus(); inp.select(); }
      }
    });

    window.sortZoneColorsByHue = function sortZoneColorsByHue(index) {
      const z = zones()[index];
      if (!z || !Array.isArray(z.colors) || z.colors.length < 2) { showToast('Need 2+ colors to sort', true); return; }
      pushZoneUndo('Sort colors by hue');
      function rgbToHue(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const d = max - min;
        if (d === 0) return 0;
        let h = 0;
        if (max === r) h = ((g - b) / d) % 6;
        else if (max === g) h = (b - r) / d + 2;
        else h = (r - g) / d + 4;
        return ((h * 60) + 360) % 360;
      }
      z.colors.sort(function (a, b) {
        const ha = rgbToHue.apply(null, a.color_rgb || [0, 0, 0]);
        const hb = rgbToHue.apply(null, b.color_rgb || [0, 0, 0]);
        return ha - hb;
      });
      renderZones(); preview();
      showToast('Sorted ' + z.colors.length + ' colors by hue');
    };

    window.trackRecentFinishOnZone = function trackRecentFinishOnZone(index, finishId) {
      if (typeof index !== 'number' || !finishId) return;
      if (!perZoneRecentFinishes[index]) perZoneRecentFinishes[index] = [];
      const arr = perZoneRecentFinishes[index];
      const existing = arr.indexOf(finishId);
      if (existing >= 0) arr.splice(existing, 1);
      arr.unshift(finishId);
      if (arr.length > 6) arr.length = 6;
    };
    window.getRecentFinishesForZone = function getRecentFinishesForZone(index) {
      return (perZoneRecentFinishes[index] || []).slice();
    };

    window.getLocalStorageUsage = function getLocalStorageUsage() {
      let total = 0;
      try {
        for (const k in localStorage) {
          if (Object.prototype.hasOwnProperty.call(localStorage, k)) total += (localStorage[k].length + k.length) * 2;
        }
      } catch (e) {}
      return total;
    };
    window.checkLocalStorageQuota = function checkLocalStorageQuota() {
      const used = window.getLocalStorageUsage();
      const quotaWarn = 4 * 1024 * 1024;
      if (used > quotaWarn) {
        showToast('Warning: localStorage at ' + (used / 1024 / 1024).toFixed(2) + ' MB. Consider exporting and clearing presets.', true);
        return true;
      }
      return false;
    };

    window.buildExportFilename = function buildExportFilename(suffix) {
      const dateStr = new Date().toISOString().slice(0, 10);
      const driverField = document.getElementById('driverName');
      const driver = driverField && driverField.value ? driverField.value.replace(/[^a-z0-9_-]+/gi, '_') : 'unsigned';
      const carField = document.getElementById('paintFile');
      const carFile = carField && carField.value ? carField.value.split(/[/\\]/).pop().replace(/\.[^.]+$/, '') : 'car';
      const safeCar = carFile.replace(/[^a-z0-9_-]+/gi, '_').slice(0, 20);
      return ['shokker', dateStr, safeCar, driver, suffix || 'config'].filter(Boolean).join('_');
    };

    window.promptForAutoRestore = function promptForAutoRestore() {
      if (state.autoRestorePrompted) return;
      state.autoRestorePrompted = true;
      const raw = (function () { try { return localStorage.getItem('shokker_autosave'); } catch (e) { return null; } })();
      if (!raw) return false;
      try {
        const cfg = JSON.parse(raw);
        const ageSec = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        const ageStr = ageSec < 60 ? ageSec + 's' : ageSec < 3600 ? Math.round(ageSec / 60) + 'm' : Math.round(ageSec / 3600) + 'h';
        const zc = (cfg.zones || []).length;
        if (confirm('Restore last session?\n\n' + zc + ' zones, saved ' + ageStr + ' ago.\n\nClick OK to restore, Cancel to start fresh.')) {
          if (typeof loadConfigFromObj === 'function') loadConfigFromObj(cfg);
          return true;
        }
      } catch (e) {}
      return false;
    };

    window.detectZoneOverlaps = function detectZoneOverlaps() {
      const overlaps = [];
      for (let i = 0; i < zones().length; i++) {
        for (let j = i + 1; j < zones().length; j++) {
          const za = zones()[i];
          const zb = zones()[j];
          if (za.muted || zb.muted) continue;
          if (za.colorMode === 'quick' && zb.colorMode === 'quick' && za.color === zb.color) {
            overlaps.push({ a: i, b: j, reason: 'both target color "' + za.color + '"' });
          }
          if (za.regionMask && zb.regionMask && za.regionMask.length === zb.regionMask.length) {
            let overlapPx = 0;
            for (let k = 0; k < za.regionMask.length && overlapPx < 100; k++) {
              if (za.regionMask[k] > 0 && zb.regionMask[k] > 0) overlapPx++;
            }
            if (overlapPx >= 100) overlaps.push({ a: i, b: j, reason: 'region masks overlap' });
          }
        }
      }
      return overlaps;
    };
    window.checkOverlapsBeforeRender = function checkOverlapsBeforeRender() {
      const overlaps = window.detectZoneOverlaps();
      if (overlaps.length === 0) return true;
      const msg = overlaps.slice(0, 3).map(function (o) {
        return 'Zone ' + (o.a + 1) + ' "' + zones()[o.a].name + '" overlaps Zone ' + (o.b + 1) + ' "' + zones()[o.b].name + '" (' + o.reason + ')';
      }).join('\n') + (overlaps.length > 3 ? '\n... +' + (overlaps.length - 3) + ' more' : '');
      return confirm('Possible zone overlaps detected:\n\n' + msg + '\n\nLater zones will overwrite earlier ones. Continue rendering?');
    };

    window.getCombinedZoneWarnings = function getCombinedZoneWarnings() {
      const ws = validateZonesBeforeRender();
      window.detectZoneOverlaps().forEach(function (o) {
        ws.push('Overlap: Zone ' + (o.a + 1) + ' & Zone ' + (o.b + 1) + ' (' + o.reason + ')');
      });
      if (zones().length > 30) ws.push('Heavy load: ' + zones().length + ' zones (recommend < 30 for fast renders)');
      return ws;
    };
    window.showCombinedWarnings = function showCombinedWarnings() {
      const ws = window.getCombinedZoneWarnings();
      if (ws.length === 0) { showToast('All zones look good ' + String.fromCharCode(0x2713)); return false; }
      const summary = ws.length + ' warning' + (ws.length !== 1 ? 's' : '') + ': ' + ws.slice(0, 2).join(' | ') + (ws.length > 2 ? ' (+' + (ws.length - 2) + ' more)' : '');
      showToast(summary, true);
      console.warn('[SPB Validation] All warnings:\n' + ws.map(function (w, i) { return (i + 1) + '. ' + w; }).join('\n'));
      return true;
    };

    window.suggestClaimableColors = function suggestClaimableColors(maxColors) {
      maxColors = maxColors || 6;
      const paintImageData = getPaintImageData();
      if (!paintImageData) return [];
      const buckets = {};
      const data = paintImageData.data;
      const stride = 64;
      for (let i = 0; i < data.length; i += 4 * stride) {
        const a = data[i + 3]; if (a < 32) continue;
        const r = (data[i] >> 5) << 5;
        const g = (data[i + 1] >> 5) << 5;
        const b = (data[i + 2] >> 5) << 5;
        const key = r + ',' + g + ',' + b;
        buckets[key] = (buckets[key] || 0) + 1;
      }
      const sorted = Object.entries(buckets).sort(function (a, b) { return b[1] - a[1]; }).slice(0, maxColors * 2);
      const claimed = zones().filter(function (z) { return z.colorMode === 'picker' && z.pickerColor; }).map(function (z) {
        return [parseInt(z.pickerColor.substr(1, 2), 16), parseInt(z.pickerColor.substr(3, 2), 16), parseInt(z.pickerColor.substr(5, 2), 16)];
      });
      const out = [];
      for (let s = 0; s < sorted.length && out.length < maxColors; s++) {
        const rgb = sorted[s][0].split(',').map(Number);
        let tooClose = false;
        for (const c of claimed) {
          if (Math.abs(c[0] - rgb[0]) < 24 && Math.abs(c[1] - rgb[1]) < 24 && Math.abs(c[2] - rgb[2]) < 24) { tooClose = true; break; }
        }
        if (tooClose) continue;
        out.push({ hex: '#' + rgb.map(c => c.toString(16).padStart(2, '0')).join('').toUpperCase(), rgb, count: sorted[s][1] });
      }
      return out;
    };
    window.applySuggestedColorToZone = function applySuggestedColorToZone(index, hex) {
      index = selectedIndexOr(index);
      if (typeof setHexColor === 'function') setHexColor(index, hex);
    };

    window.setZoneIntensityNumeric = function setZoneIntensityNumeric(index, value) {
      index = selectedIndexOr(index);
      const z = zones()[index]; if (!z) return;
      const num = Math.max(0, Math.min(200, parseInt(value, 10) || 0));
      pushZoneUndoCoalesced('Set intensity ' + num);
      z.intensity = String(num);
      z.customSpec = null; z.customPaint = null; z.customBright = null;
      renderZones(); preview();
    };

    window.suggestColorHarmony = function suggestColorHarmony(hex, mode) {
      if (!hex || !/^#[0-9A-Fa-f]{6}$/.test(hex)) return [];
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
        return '#' + [
          Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
          Math.round(hue2rgb(p, q, h) * 255),
          Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
        ].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
      }
      const [h, s, l] = toHsl(hex);
      if (mode === 'complementary') return [fromHsl(h + 180, s, l)];
      if (mode === 'triad') return [fromHsl(h + 120, s, l), fromHsl(h + 240, s, l)];
      if (mode === 'analogous') return [fromHsl(h - 30, s, l), fromHsl(h + 30, s, l)];
      if (mode === 'split') return [fromHsl(h + 150, s, l), fromHsl(h + 210, s, l)];
      if (mode === 'tetrad') return [fromHsl(h + 90, s, l), fromHsl(h + 180, s, l), fromHsl(h + 270, s, l)];
      return [];
    };

    window.focusZone = function focusZone(index) {
      if (typeof index !== 'number' || index < 0 || index >= zones().length) return;
      setSelectedZoneIndex(index);
      renderZones();
      const card = document.getElementById('zone-card-' + index);
      if (card && card.scrollIntoView) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.animation = 'zoneFlash 0.6s ease';
        setTimeout(function () { card.style.animation = ''; }, 600);
      }
    };
    window.getEmptyStateGuide = function getEmptyStateGuide() {
      if (zones().length > 0) return '';
      return '<div class="empty-zones-guide" style="padding:18px 14px;text-align:center;color:#aaa;font-size:11px;border:1px dashed #333;border-radius:6px;margin:12px;">' +
        '<div style="font-size:20px;margin-bottom:8px;">' + String.fromCodePoint(0x1F3A8) + '</div>' +
        '<div style="font-weight:bold;color:#ddd;margin-bottom:6px;font-size:13px;">No zones yet</div>' +
        '<div style="margin-bottom:10px;line-height:1.5;">Zones tell SPB which pixels to paint with which finish.<br>Get started by adding your first zone.</div>' +
        '<button class="btn" onclick="addZone()" style="background:#E87A20;color:#fff;border:none;padding:7px 14px;border-radius:4px;cursor:pointer;font-weight:bold;">+ Add First Zone</button>' +
        "<div style=\"margin-top:10px;font-size:9px;color:#666;\">Or load a preset: <a href=\"#\" onclick=\"event.preventDefault();const p=listZonePresets();if(p.length===0){alert('No saved presets');return;}const n=prompt('Load which preset?\\n\\n'+p.map(p=>p.name).join('\\n'));if(n)loadZonePreset(n);\" style=\"color:#0af;\">Load Preset</a></div>" +
        '</div>';
    };

    window.markDirty = function markDirty() { state.dirty = true; window.updateAutoSaveBadge(); };
    window.markClean = function markClean() { state.dirty = false; window.updateAutoSaveBadge(); };
    window.getLastAutoSaveTime = function getLastAutoSaveTime() {
      try { return JSON.parse(localStorage.getItem('shokker_autosave') || '{}')._autosave_time || 0; } catch (e) { return 0; }
    };
    window.updateAutoSaveBadge = function updateAutoSaveBadge() {
      const badge = document.getElementById('autosaveBadge'); if (!badge) return;
      const t = window.getLastAutoSaveTime();
      if (!t) { badge.textContent = 'Not saved'; return; }
      const ago = Math.round((Date.now() - t) / 1000);
      const agoStr = ago < 60 ? ago + 's ago' : ago < 3600 ? Math.round(ago / 60) + 'm ago' : Math.round(ago / 3600) + 'h ago';
      badge.textContent = (state.dirty ? String.fromCharCode(0x26A0) + ' Unsaved | ' : String.fromCharCode(0x2713) + ' Auto-saved ') + agoStr;
    };
    setInterval(window.updateAutoSaveBadge, 60000);

    window.checkZoneLimitWarning = function checkZoneLimitWarning() {
      if (zones().length >= maxZones) { showToast('Hard limit (' + maxZones + ' zones) reached. Delete some to add more.', true); return 'hard'; }
      if (zones().length >= 30) { showToast('Heavy load: ' + zones().length + ' zones. Render performance will drop above 30.', true); return 'soft'; }
      if (zones().length >= 20) return 'caution';
      return 'ok';
    };
    window.getLayerThumbnailUrl = function getLayerThumbnailUrl(layerId) {
      const psdLayers = getPsdLayers();
      if (!psdLayers || !Array.isArray(psdLayers)) return '';
      const layer = psdLayers.find(l => l.id === layerId);
      if (!layer || !layer.img) return '';
      return layer.img.src || '';
    };
    window.soloZone = function soloZone(index) {
      index = selectedIndexOr(index);
      pushZoneUndo('Solo zone ' + (index + 1));
      zones().forEach(function (z, i) { z.muted = (i !== index); });
      renderZones(); preview();
      showToast('Solo: only "' + zones()[index].name + '" will render');
    };
    window.unmuteAllZones = function unmuteAllZones() {
      pushZoneUndo('Unmute all');
      zones().forEach(function (z) { z.muted = false; });
      renderZones(); preview();
      showToast('All zones unmuted');
    };
    window.resetZone = function resetZone(index) {
      index = selectedIndexOr(index);
      const z = zones()[index]; if (!z) return;
      if (!confirm('Reset "' + z.name + '" to defaults? (Color, finish, all overlays will be cleared)')) return;
      pushZoneUndo('Reset zone "' + z.name + '"');
      const preserveName = z.name;
      Object.keys(z).forEach(function (k) { delete z[k]; });
      Object.assign(z, {
        name: preserveName,
        color: null,
        base: null,
        pattern: 'none',
        finish: null,
        intensity: '100',
        colorMode: 'none',
        pickerColor: '#3366ff',
        pickerTolerance: 40,
        colors: [],
        regionMask: null,
        muted: false,
        patternStack: [],
        specPatternStack: [],
        zoneSpecMapPath: null,
        zoneSpecMapName: null,
        zoneSpecMapResolution: null,
        zoneSpecMapStrength: 100,
      });
      renderZones(); preview();
      showToast('Reset zone: ' + preserveName);
    };
    window.cloneZoneNTimes = function cloneZoneNTimes(index, n) {
      index = selectedIndexOr(index);
      if (!n) {
        const v = prompt('Clone how many copies?', '3');
        n = parseInt(v, 10);
        if (!n) return;
      }
      n = Math.min(n, maxZones - zones().length);
      if (n <= 0) { showToast('Not enough room (zone limit reached)', true); return; }
      pushZoneUndo('Clone zone x' + n);
      const src = zones()[index];
      for (let i = 0; i < n; i++) {
        const clone = cloneZoneState(src, {
          preserveId: false,
          includeRegionMask: false,
          includeSpatialMask: false,
          includePatternStrengthMap: true,
        });
        clone.name = src.name + ' (' + (i + 2) + ')';
        clone.regionMask = null;
        clone.spatialMask = null;
        zones().splice(index + 1 + i, 0, clone);
      }
      renderZones(); preview();
      showToast('Cloned ' + n + ' copies of "' + src.name + '"');
    };
    window.clearAllZones = function clearAllZones() {
      if (!confirm('Delete ALL ' + zones().length + ' zones and start fresh?')) return;
      pushZoneUndo('Clear all zones');
      zones().length = 0;
      if (typeof addZone === 'function') addZone(true);
      setSelectedZoneIndex(0);
      renderZones(); preview();
      showToast('All zones cleared. Started fresh with one empty zone.');
    };
    window.filterZonesByStatus = function filterZonesByStatus(status) {
      document.querySelectorAll('#zoneList .zone-card').forEach(function (card, i) {
        const z = zones()[i]; if (!z) return;
        const s = window.getZoneStatus(z);
        card.style.display = (status === 'all' || s === status) ? '' : 'none';
      });
      showToast('Filtered: ' + status);
    };
    window.showOnlyProblemZones = function showOnlyProblemZones() { window.filterZonesByStatus('no_finish'); };
    window.showAllZones = function showAllZones() { window.filterZonesByStatus('all'); };
  }

  window.SPBZoneWorkflowControls = { install, state, perZoneUndoStacks, perZoneRecentFinishes };
})();
