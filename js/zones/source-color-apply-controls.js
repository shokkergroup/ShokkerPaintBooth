(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = global.document;
    var getZones = deps.getZones || function() { return []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return 0; };
    var setSelectedZoneIndex = deps.setSelectedZoneIndex || function() {};
    var pushZoneUndo = deps.pushZoneUndo || function() {};
    var renderZones = deps.renderZones || function() {};
    var renderZoneDetail = deps.renderZoneDetail || function() {};
    var triggerPreviewRender = deps.triggerPreviewRender || function() {};
    var showToast = deps.showToast || function() {};
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };
    var getPsdLayers = deps.getPsdLayers || function() { return global._psdLayers || []; };
    var updateRegionStatus = deps.updateRegionStatus || function() {};
    var renderRegionOverlay = deps.renderRegionOverlay || function() {};
    var setCanvasMode = deps.setCanvasMode || function() {};
    var isLayerToolbarMode = deps.isLayerToolbarMode || function() { return false; };
    var getPaintCanvas = deps.getPaintCanvas || function() { return doc ? doc.getElementById('paintCanvas') : null; };

    function zoneAt(index) {
      return getZones()[index];
    }

    // [SPB apply-area layer-mode fix 2026-07-01] One-shot intent armed by the
    // APPLY AREA panel's Box/Lasso buttons. In layer toolbar mode a drawn rect
    // is normally a layer selection, so autoActivateZoneApplyArea bails there —
    // which silently dropped the owner's apply-area box on TGA/layer workflows
    // (box drawn + yellow overlay, but useRegion never set → finish rendered on
    // ALL matched pixels). When the draw was started from the APPLY AREA panel
    // the intent is unambiguous, so the next matching shape commit activates
    // the area regardless of toolbar mode.
    var _applyAreaDrawIntent = null; // {tool:'rect'|'lasso', zoneIndex}

    function _defaultZoneHardEdge(zone) {
      if (zone && zone.hardEdge === undefined) zone.hardEdge = true;
    }

    function _getPsdLayersForZoneUi() {
      var layers = getPsdLayers();
      return Array.isArray(layers) ? layers.filter(function(l) { return l && l.id && l.name; }) : [];
    }

    function buildZoneReactToLayerHtml(zoneIndex, zone) {
      // [SPB-MULTILAYER 2026-08-21] delegate to the shared multi-select box when
      // it exists so both Restrict-to-Layer UIs stay identical.
      if (typeof window._restrictToLayersBoxHtml === 'function'
          && typeof _psdLayers !== 'undefined' && _psdLayers.length) {
        return window._restrictToLayersBoxHtml(zoneIndex, zone);
      }
      var layers = _getPsdLayersForZoneUi();
      if (!layers.length) {
        return '<div class="restrict-to-layer-row" style="margin-bottom:8px;padding:6px 8px;background:rgba(0,229,255,0.04);border:1px dashed rgba(0,229,255,0.2);border-radius:6px;">'
          + '<div style="font-size:10px;color:var(--accent-cyan);font-weight:bold;margin-bottom:2px;">Restrict to Layer</div>'
          + '<div style="font-size:9px;color:var(--text-dim);">Import a PSD or add layers to marry this zone to a layer.</div></div>';
      }
      var layerOpts = layers.map(function(l) {
        var sel = zone.sourceLayer === l.id ? ' selected' : '';
        var grp = l.groupName ? ' (' + l.groupName + ')' : '';
        return '<option value="' + l.id + '"' + sel + '>' + escapeHtml(l.name + grp) + '</option>';
      }).join('');
      var linkedLayer = zone.sourceLayer ? layers.find(function(l) { return l.id === zone.sourceLayer; }) : null;
      var linked = linkedLayer ? linkedLayer.name : (zone.sourceLayer || null);
      var linkNote = linked
        ? '<div style="font-size:9px;color:var(--accent-green);margin-top:3px;">Restricted to: ' + escapeHtml(linked) + '</div>'
        : '<div style="font-size:9px;color:var(--text-dim);margin-top:3px;">No restriction - zone can match color on any layer</div>';
      return '<div class="restrict-to-layer-row" style="margin-bottom:8px;padding:6px 8px;background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:6px;">'
        + '<div style="font-size:10px;color:var(--accent-cyan);font-weight:bold;margin-bottom:4px;">Restrict to Layer</div>'
        + '<select style="width:100%;font-size:11px;padding:4px;background:var(--bg-dark);color:var(--text);border:1px solid var(--border);border-radius:4px;"'
        + ' onchange="setZoneSourceLayer(' + zoneIndex + ', this.value || null)" title="Only pixels on this layer can claim this zone">'
        + '<option value="">- All layers (no restriction) -</option>' + layerOpts + '</select>' + linkNote + '</div>';
    }

    function setZoneHardEdge(index, val) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('HARDEN ' + (val ? 'on' : 'off'));
      zone.hardEdge = !!val;
      renderZones();
      triggerPreviewRender();
    }

    function refreshZoneDetailIfOpen() {
      var selectedZoneIndex = getSelectedZoneIndex();
      var zones = getZones();
      if (typeof selectedZoneIndex !== 'number' || selectedZoneIndex < 0 || !zones[selectedZoneIndex]) return;
      var fp = doc && doc.getElementById('zoneEditorFloat');
      var dp = doc && doc.getElementById('zoneDetailPanel');
      var open = (fp && fp.classList.contains('active')) || (dp && dp.children && dp.children.length > 0);
      if (open) renderZoneDetail(selectedZoneIndex);
    }

    function setZoneSourceLayer(index, layerId) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Set source layer');
      zone.sourceLayer = layerId || null;
      zone.sourceLayers = layerId ? [layerId] : [];   // [SPB-MULTILAYER 2026-08-21] keep the canonical array in sync (this module copy OVERRIDES the state-zones one at install time)
      renderZones();
      renderZoneDetail(index);
      triggerPreviewRender();
      if (layerId) {
        var layer = _getPsdLayersForZoneUi().find(function(l) { return l.id === layerId; });
        showToast('Zone restricted to layer: ' + (layer ? layer.name : layerId));
      } else {
        showToast('Zone restriction removed - applies to all layers');
      }
    }

    function setQuickColor(index, value) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Set color');
      zone.color = value;
      zone.colorMode = 'quick';
      zone.colors = [];
      renderZones();
      triggerPreviewRender();
    }

    function setSpecialColor(index, value) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Set special color: ' + value);
      zone.color = value;
      zone.colorMode = 'special';
      zone.colors = [];
      renderZones();
      triggerPreviewRender();
    }

    function setTextColor(index, value) {
      var zone = zoneAt(index);
      if (!zone) return;
      var trimmed = String(value || '').trim();
      pushZoneUndo('Set text color: ' + (trimmed || '(cleared)'));
      if (!trimmed) {
        zone.color = null;
        zone.colorMode = 'none';
      } else {
        zone.color = trimmed;
        zone.colorMode = 'text';
      }
      zone.colors = [];
      renderZones();
      triggerPreviewRender();
    }

    function setPickerColor(index, hexValue) {
      var zone = zoneAt(index);
      if (!zone || !hexValue) return;
      pushZoneUndo('Switch to picker color');
      var r = parseInt(hexValue.substr(1, 2), 16);
      var g = parseInt(hexValue.substr(3, 2), 16);
      var b = parseInt(hexValue.substr(5, 2), 16);
      zone.pickerColor = hexValue;
      zone.color = { color_rgb: [r, g, b], tolerance: zone.pickerTolerance ?? 40 };
      zone.colorMode = 'picker';
      zone.colors = [];
      renderZones();
      triggerPreviewRender();
    }

    function setPickerTolerance(index, value) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Picker tolerance', true);
      var tol = parseInt(value);
      zone.pickerTolerance = tol;
      if (zone.colorMode === 'picker' && typeof zone.color === 'object' && zone.color !== null) {
        zone.color.tolerance = tol;
      }
      renderZones();
      triggerPreviewRender();
    }

    function setHexColor(index, hex) {
      var zone = zoneAt(index);
      if (!zone) return;
      hex = String(hex || '').trim();
      if (!hex) {
        if (zone.colorMode !== 'multi') {
          pushZoneUndo('Clear hex color');
          zone.color = null;
          zone.colorMode = 'none';
        }
        renderZones();
        triggerPreviewRender();
        return;
      }
      if (!hex.startsWith('#')) hex = '#' + hex;
      if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
        showToast('Enter a valid hex code like #FF3366', true);
        return;
      }
      pushZoneUndo('Set hex color ' + hex.toUpperCase());
      var r = parseInt(hex.substr(1, 2), 16);
      var g = parseInt(hex.substr(3, 2), 16);
      var b = parseInt(hex.substr(5, 2), 16);
      var tol = zone.pickerTolerance ?? 40;
      zone.pickerColor = hex;
      if (zone.colorMode === 'multi' && zone.colors.length > 0) {
        if (zone.colors.some(function(c) { return c.hex && c.hex.toUpperCase() === hex.toUpperCase(); })) {
          showToast('That color is already in this zone', true);
          return;
        }
        zone.colors.push({ color_rgb: [r, g, b], tolerance: tol, hex: hex });
        zone.color = zone.colors;
        renderZones();
        triggerPreviewRender();
        showToast('Added ' + hex.toUpperCase() + ' to ' + zone.name + ' (' + zone.colors.length + ' colors stacked)');
      } else {
        zone.color = { color_rgb: [r, g, b], tolerance: tol };
        zone.colorMode = 'picker';
        renderZones();
        triggerPreviewRender();
        showToast('Zone ' + (index + 1) + ': color set to ' + hex.toUpperCase());
      }
    }

    // 2026-07-30: this scanned all 4,194,304 mask entries every call, and the CPU
    // profile showed it running several times inside a single renderZones() —
    // 45ms of the ~335ms freeze. SPBMaskStats does one pass and memoises it for
    // the duration of the synchronous render, so repeat calls are free.
    function _zoneApplyAreaPixelCount(zone) {
      if (!zone || !zone.regionMask) return 0;
      if (window.SPBMaskStats) return window.SPBMaskStats.count(zone.regionMask);
      var n = 0;
      for (var i = 0; i < zone.regionMask.length; i++) if (zone.regionMask[i] > 0) n++;
      return n;
    }

    function _zoneApplyAreaSummary(zone) {
      var pc = getPaintCanvas();
      var total = pc ? pc.width * pc.height : 2048 * 2048;
      var regionPx = _zoneApplyAreaPixelCount(zone);
      var spatialPx = (zone && zone.spatialMask)
        ? (window.SPBMaskStats ? window.SPBMaskStats.count(zone.spatialMask)
                               : zone.spatialMask.reduce(function(s, v) { return s + (v > 0 ? 1 : 0); }, 0))
        : 0;
      if (zone && zone.useRegion && regionPx > 0) {
        var pct = ((regionPx / total) * 100).toFixed(1);
        return { active: true, label: 'Shape apply area - ' + pct + '% of canvas (' + regionPx.toLocaleString() + ' px)', regionPx: regionPx, pct: pct };
      }
      if (regionPx > 0) {
        var draftPct = ((regionPx / total) * 100).toFixed(1);
        return { active: false, label: 'Draft shape drawn (' + draftPct + '%) - click Activate below', regionPx: regionPx, pct: draftPct };
      }
      if (spatialPx > 0) {
        return { active: true, label: 'Color refine brush - ' + spatialPx.toLocaleString() + ' px marked', regionPx: 0, pct: '0' };
      }
      return { active: false, label: 'No apply area yet - draw a box on the car, or refine a color zone', regionPx: 0, pct: '0' };
    }

    function _zoneShouldFitIntoApplyArea(zone) {
      if (!zone || !zone.fitIntoApplyArea) return false;
      if (zone.finish && !zone.base) return false;
      return true;
    }

    function getZoneColorFilterRgb(zone) {
      if (!zone) return null;
      if (zone.colorMode === 'picker' && zone.pickerColor && /^#[0-9a-fA-F]{6}$/i.test(zone.pickerColor)) {
        return { r: parseInt(zone.pickerColor.slice(1, 3), 16), g: parseInt(zone.pickerColor.slice(3, 5), 16), b: parseInt(zone.pickerColor.slice(5, 7), 16) };
      }
      if (zone.colors && zone.colors.length > 0 && zone.colors[0].color_rgb) {
        var c = zone.colors[0].color_rgb;
        return { r: c[0], g: c[1], b: c[2] };
      }
      if (zone.pickerColor && /^#[0-9a-fA-F]{6}$/i.test(zone.pickerColor)) {
        return { r: parseInt(zone.pickerColor.slice(1, 3), 16), g: parseInt(zone.pickerColor.slice(3, 5), 16), b: parseInt(zone.pickerColor.slice(5, 7), 16) };
      }
      return null;
    }

    function _syncFitIntoApplyAreaFlags(zone) {
      if (!_zoneShouldFitIntoApplyArea(zone)) return;
      zone.baseColorFitZone = true;
      zone.patternPlacement = 'fit';
      zone.patternFitZone = true;
    }

    function setZoneFitIntoApplyArea(index, enabled) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Fit material into apply area', true);
      zone.fitIntoApplyArea = !!enabled;
      if (enabled) _syncFitIntoApplyAreaFlags(zone);
      renderZones();
      triggerPreviewRender();
      if (enabled && zone.finish && !zone.base) showToast('Fit is for base+pattern zones only - ignored for monolithic finishes.', 'info');
    }

    function activateZoneApplyArea(index) {
      var zone = zoneAt(index);
      if (!zone) return;
      if (!zone.regionMask || !zone.regionMask.some(function(v) { return v > 0; })) {
        showToast('Draw a box or lasso on the car first (Rect tool), then Activate.', true);
        return;
      }
      pushZoneUndo('Activate apply area');
      zone.useRegion = true;
      _syncFitIntoApplyAreaFlags(zone);
      setSelectedZoneIndex(index);
      renderZones();
      updateRegionStatus();
      triggerPreviewRender();
      var hasColor = !!getZoneColorFilterRgb(zone);
      showToast(hasColor
        ? 'Apply area ON - finish only on ' + zone.name + ' color inside your box.'
        : 'Apply area ON for ' + zone.name + ' - pick a color above to limit what gets filled.');
    }

    function clearZoneApplyArea(index) {
      var zone = zoneAt(index);
      if (!zone) return;
      pushZoneUndo('Clear apply area');
      zone.regionMask = null;
      zone.spatialMask = null;
      zone.useRegion = false;
      _applyAreaDrawIntent = null;
      renderZones();
      renderRegionOverlay();
      triggerPreviewRender();
      showToast('Apply area cleared');
    }

    function startZoneApplyAreaDraw(index, tool) {
      if (!zoneAt(index)) return;
      setSelectedZoneIndex(index);
      renderZones();
      var modeMap = { box: 'rect', lasso: 'lasso', refine: 'spatial-include' };
      var mode = modeMap[tool] || 'rect';
      _applyAreaDrawIntent = (mode === 'rect' || mode === 'lasso') ? { tool: mode, zoneIndex: index } : null;
      setCanvasMode(mode);
      var hints = {
        box: 'Draw a rectangle on the car. Tip: eyedrop a color first to fill only that color inside the box (e.g. yellow #55).',
        lasso: 'Click points around the area, double-click to close.',
        refine: 'Paint green on the car to keep only those pixels inside a color zone.'
      };
      showToast(hints[tool] || hints.box, 'info');
    }

    function autoActivateZoneApplyArea(index, sourceTool) {
      var intent = _applyAreaDrawIntent;
      _applyAreaDrawIntent = null; // one-shot: the next shape commit consumes it
      var intentMatches = !!(intent && intent.zoneIndex === index && (!sourceTool || intent.tool === sourceTool));
      if (isLayerToolbarMode() && !intentMatches) return false;
      var zone = zoneAt(index);
      // SPB-93 tools 2026-09-07: share the exact count with the status/panel
      // refresh below; a callback scan to the first selected pixel added work
      // proportional to its position on4096px documents.
      if (!zone || _zoneApplyAreaPixelCount(zone) === 0) return false;
      var wasActive = !!zone.useRegion;
      zone.useRegion = true;
      _syncFitIntoApplyAreaFlags(zone);
      updateRegionStatus();
      renderZones();
      if (!wasActive) {
        var hasColor = !!getZoneColorFilterRgb(zone);
        showToast(hasColor
          ? 'Apply area on ' + zone.name + ': box + zone color (yellow only inside box).'
          : 'Apply area on ' + zone.name + ': entire box - set a COLOR above to limit to yellow etc.', 'info');
      }
      return true;
    }

    function buildZoneApplyAreaSection(i, zone) {
      var sum = _zoneApplyAreaSummary(zone);
      var fitChecked = !!zone.fitIntoApplyArea;
      var statusColor = sum.active ? '#5dffb0' : (sum.regionPx > 0 ? '#ffd166' : '#8a9bb0');
      // SPB 2026-07-04 (owner): "make it a dropdown and make that box much smaller".
      // Starts COLLAPSED unless an apply area is drawn/active (state stays visible);
      // paddings/margins halved, the example footnote dropped, fit-checkbox one line.
      var startCollapsed = !sum.active && !(sum.regionPx > 0);
      var headerHint = sum.active ? ' &middot; ON' : (sum.regionPx > 0 ? ' &middot; drawn' : '');
      return '<div class="section-collapsible' + (startCollapsed ? ' collapsed' : '') + '" id="sectionApplyArea' + i + '" style="margin:4px 0;">'
        + '<div class="section-header" onclick="event.stopPropagation(); this.parentElement.classList.toggle(\'collapsed\')">'
        + '<span class="section-header-label">APPLY AREA<span style="font-size:8px;color:' + statusColor + ';text-transform:none;">' + headerHint + '</span></span>'
        + '<span class="collapse-arrow section-header-arrow">&#9660;</span></div>'
        + '<div class="apply-area-panel" style="padding:5px 8px; border:1px solid rgba(93,255,176,0.22); border-radius:5px; background:rgba(8,24,18,0.4);">'
        + '<div style="font-size:9px; color:' + statusColor + '; line-height:1.3; margin-bottom:4px;">' + escapeHtml(sum.label) + '</div>'
        + '<div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:4px;">'
        + '<button type="button" class="btn btn-sm" onclick="event.stopPropagation(); startZoneApplyAreaDraw(' + i + ',\'box\')" style="font-size:9px;padding:2px 7px;border-color:#5dffb0;color:#5dffb0;">Draw box</button>'
        + '<button type="button" class="btn btn-sm" onclick="event.stopPropagation(); startZoneApplyAreaDraw(' + i + ',\'lasso\')" style="font-size:9px;padding:2px 7px;">Lasso</button>'
        + '<button type="button" class="btn btn-sm" onclick="event.stopPropagation(); startZoneApplyAreaDraw(' + i + ',\'refine\')" style="font-size:9px;padding:2px 7px;" title="Keep color zone but limit to green brush">Refine color</button>'
        + '<button type="button" class="btn btn-sm" onclick="event.stopPropagation(); activateZoneApplyArea(' + i + ')" style="font-size:9px;padding:2px 8px;background:#1a4d3a;border-color:#5dffb0;color:#5dffb0;font-weight:bold;">Activate</button>'
        + '<button type="button" class="btn btn-sm" onclick="event.stopPropagation(); clearZoneApplyArea(' + i + ')" style="font-size:9px;padding:2px 7px;color:#ff8888;">Clear</button></div>'
        + '<label style="display:flex; align-items:center; gap:6px; font-size:9.5px; cursor:pointer; color:#c9d4e2;"'
        + ' title="Scales the base+pattern swatch into the drawn box. Leave OFF for monolithic finishes (prevents mini-car-in-box); ON for tiled patterns on panels.">'
        + '<input type="checkbox" ' + (fitChecked ? 'checked' : '') + ' onchange="setZoneFitIntoApplyArea(' + i + ', this.checked)">'
        + '<span>Fit pattern/base swatch into box <span style="color:#8a9bb0;">(base+pattern only)</span></span></label>'
        + '</div></div>';
    }

    Object.assign(global, {
      _defaultZoneHardEdge,
      _getPsdLayersForZoneUi,
      buildZoneReactToLayerHtml,
      setZoneHardEdge,
      refreshZoneDetailIfOpen,
      setZoneSourceLayer,
      setQuickColor,
      setSpecialColor,
      setTextColor,
      setPickerColor,
      setPickerTolerance,
      setHexColor,
      _zoneShouldFitIntoApplyArea,
      getZoneColorFilterRgb,
      setZoneFitIntoApplyArea,
      activateZoneApplyArea,
      clearZoneApplyArea,
      startZoneApplyAreaDraw,
      autoActivateZoneApplyArea,
      buildZoneApplyAreaSection
    });
  }

  global.SPBZoneSourceColorApplyControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
