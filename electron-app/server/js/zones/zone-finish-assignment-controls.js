(function (global) {
  'use strict';

  var NO_AUTO_COLOR_GROUPS = new Set([
    'Foundation', 'Foundation EFX',
    'Candy & Pearl', 'Candy and Pearl', 'Ceramic & Glass', 'Ceramic and Glass',
    'Chrome & Mirror', 'Chrome and Mirror', 'Exotic Metal',
    'Extreme & Experimental', 'Extreme and Experimental',
    'Industrial & Tactical', 'Industrial and Tactical', 'Metallic Standard',
    'OEM Automotive', 'Premium Luxury', 'Racing Heritage',
    'Satin & Wrap', 'Satin and Wrap', 'Weathered & Aged', 'Weathered and Aged',
    'Carbon & Composite', 'Iridescent Insects', 'PARADIGM', 'Textile-Inspired',
    'Stone & Mineral', 'Paint Technique'
  ]);

  function install(deps) {
    deps = deps || {};
    var localStorageApi = deps.localStorage || global.localStorage;
    var baseGroupLookup = null;
    var albedoHintKey = deps.albedoHintKey || '_spb_albedo_hint_shown_count';
    var albedoHintMaxShows = deps.albedoHintMaxShows || 3;
    function bases() { return deps.getBases ? (deps.getBases() || []) : []; }
    function patterns() { return deps.getPatterns ? (deps.getPatterns() || []) : []; }
    function monolithics() { return deps.getMonolithics ? (deps.getMonolithics() || []) : []; }
    function specialGroups() { return deps.getSpecialGroups ? (deps.getSpecialGroups() || {}) : {}; }
    function baseGroups() { return deps.getBaseGroups ? (deps.getBaseGroups() || {}) : {}; }
    function zones() { return deps.getZones ? (deps.getZones() || []) : []; }
    function selectedIndex() { return deps.getSelectedZoneIndex ? deps.getSelectedZoneIndex() : -1; }
    function showToast() { if (deps.showToast) deps.showToast.apply(null, arguments); }

    function getBaseGroup(baseId) {
      if (!baseGroupLookup) {
        baseGroupLookup = {};
        var groups = baseGroups();
        Object.keys(groups).forEach(function (groupName) {
          (groups[groupName] || []).forEach(function (id) {
            if (!(id in baseGroupLookup)) baseGroupLookup[id] = groupName;
          });
        });
      }
      return baseGroupLookup[baseId] || null;
    }

    function normalizeFinishId(id) {
      return (!id || typeof id !== 'string') ? '' : id.replace(/^mono:/, '');
    }

    function isShippingSpecialLikeFinishId(id) {
      var raw = normalizeFinishId(id);
      if (!raw) return false;
      if (monolithics().some(function (m) { return m && m.id === raw; })) return true;
      var groups = specialGroups();
      return Object.keys(groups).some(function (groupName) {
        var ids = groups[groupName];
        return Array.isArray(ids) && ids.indexOf(raw) >= 0;
      });
    }

    function findFinishDisplay(id) {
      var raw = normalizeFinishId(id);
      if (!raw) return null;
      return monolithics().find(function (m) { return m && m.id === raw; })
        || bases().find(function (b) { return b && b.id === raw; }) || null;
    }

    function extractSwatchHex(swatch, fallback) {
      var fb = /^#[0-9a-fA-F]{6}$/.test(fallback || '') ? fallback : '#ffffff';
      if (typeof swatch !== 'string') return fb;
      var six = swatch.match(/#[0-9a-fA-F]{6}\b/);
      if (six) return six[0];
      var three = swatch.match(/#[0-9a-fA-F]{3}\b/);
      return three ? '#' + three[0].slice(1).split('').map(function (ch) { return ch + ch; }).join('') : fb;
    }

    function defaultBaseColorToFinish(zone, finishId) {
      if (!zone) return;
      var raw = normalizeFinishId(finishId);
      if (!raw) return;
      var display = findFinishDisplay(raw);
      zone.baseColorMode = 'special';
      zone.baseColorSource = 'mono:' + raw;
      zone.baseColor = extractSwatchHex(display && display.swatch, zone.baseColor || '#ffffff');
      if (zone.baseColorStrength == null) zone.baseColorStrength = 1;
      zone._autoBaseColorFill = true;
    }

    function shouldAutoFillBaseColor(baseId) {
      var group = getBaseGroup(baseId);
      return isShippingSpecialLikeFinishId(baseId) && NO_AUTO_COLOR_GROUPS.has(group) === false;
    }

    function preserveBaseColorOnBaseChange(zone) {
      return !!(zone && zone.alignBaseColorWithBase === false && zone.baseColorMode === 'special' && zone.baseColorSource);
    }

    function applyPickedMonolithicToZone(zone, monoId) {
      if (!zone) return;
      var raw = normalizeFinishId(monoId);
      zone.baseSpecStrength = 1;
      zone.baseStrength = 1;
      zone.patternSpecMult = 1;
      zone.baseSpecBlendMode = 'normal';
      zone.finish = raw || null;
      zone.base = null;
      if (!zone.pattern) zone.pattern = 'none';
      zone._scopedBrushAutoBaseColor = false;
      if (preserveBaseColorOnBaseChange(zone)) return;
      if (raw && isShippingSpecialLikeFinishId(raw)) defaultBaseColorToFinish(zone, raw);
      else if (zone._autoBaseColorFill) {
        zone.baseColorMode = 'source';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = false;
      }
    }

    function applyPickedBaseToZone(zone, baseId) {
      if (!zone) return;
      zone.base = baseId || null;
      zone.finish = null;
      if (!zone.pattern) zone.pattern = 'none';
      zone._scopedBrushAutoBaseColor = false;
      if (preserveBaseColorOnBaseChange(zone)) return;
      var base = bases().find(function (b) { return b && b.id === baseId; }) || null;
      if (baseId && isShippingSpecialLikeFinishId(baseId)) {
        defaultBaseColorToFinish(zone, baseId);
      } else if (base && base.swatch && shouldAutoFillBaseColor(baseId)) {
        zone.baseColor = base.swatch;
        zone.baseColorMode = 'solid';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = true;
      } else if (zone._autoBaseColorFill) {
        zone.baseColorMode = 'source';
        zone.baseColorSource = null;
        zone._autoBaseColorFill = false;
      }
    }

    function hexLooksDark(hex) {
      if (!hex || typeof hex !== 'string' || hex.length < 7) return false;
      try {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return (0.299 * r + 0.587 * g + 0.114 * b) < 140;
      } catch (_) { return false; }
    }

    function finishNeedsAlbedoHint(finishId) {
      if (!finishId || typeof finishId !== 'string') return false;
      try {
        if (deps.isChromeLikeBase) return !!deps.isChromeLikeBase(finishId);
        var meta = deps.getBaseMetadata ? deps.getBaseMetadata(finishId) : null;
        if (meta && (meta.family === 'chrome' || meta.family === 'satin_chrome')) return true;
        var base = bases().find(function (b) { return b && b.id === finishId; }) || {};
        return /\b(chrome|mirror)\b/.test((finishId + ' ' + (base.name || '') + ' ' + (base.desc || '')).toLowerCase());
      } catch (_) { return false; }
    }

    function maybeShowAlbedoHint(finishId, zone) {
      if (!localStorageApi || !finishNeedsAlbedoHint(finishId)) return;
      var hex = (zone && (zone.baseColor || (typeof zone.color === 'string' && zone.color.startsWith('#') ? zone.color : null))) || null;
      if (!hex || !hexLooksDark(hex)) return;
      var shown = 0;
      try { shown = parseInt(localStorageApi.getItem(albedoHintKey) || '0', 10) || 0; } catch (_) {}
      if (shown >= albedoHintMaxShows) return;
      try { localStorageApi.setItem(albedoHintKey, String(shown + 1)); } catch (_) {}
      showToast('Chrome reads best on light/white albedo. Your color is dark; iRacing PBR may render it nearly black. Try a near-white base for a true mirror look.', 'warn');
    }

    function assignFinishToSelected(finishId) {
      var index = selectedIndex();
      var list = zones();
      if (index < 0 || index >= list.length) return;
      if (deps.trackRecentFinish) deps.trackRecentFinish(finishId);
      if (deps.pushZoneUndo) deps.pushZoneUndo('Assign finish: ' + finishId);
      var zone = list[index];
      var base = bases().find(function (b) { return b && b.id === finishId; });
      var pattern = patterns().find(function (p) { return p && p.id === finishId; });
      var mono = monolithics().find(function (m) { return m && m.id === finishId; });
      if (base) {
        applyPickedBaseToZone(zone, finishId);
        if (deps.renderZones) deps.renderZones();
        if (deps.triggerPreviewRender) deps.triggerPreviewRender();
        showToast('Base: ' + base.name + ' => ' + zone.name);
        try { maybeShowAlbedoHint(finishId, zone); } catch (_) {}
      } else if (pattern) {
        if (!zone.finish && !zone.base) zone.base = 'gloss';
        zone.pattern = finishId;
        if (deps.renderZones) deps.renderZones();
        if (deps.triggerPreviewRender) deps.triggerPreviewRender();
        var monoName = zone.finish ? ((monolithics().find(function (m) { return m && m.id === zone.finish; }) || {}).name || zone.finish) : '';
        showToast(zone.finish ? ('Pattern: ' + pattern.name + ' over ' + monoName + ' => ' + zone.name) : ('Pattern: ' + pattern.name + ' => ' + zone.name));
      } else if (mono) {
        applyPickedMonolithicToZone(zone, finishId);
        if (deps.renderZones) deps.renderZones();
        if (deps.triggerPreviewRender) deps.triggerPreviewRender();
        var currentPattern = (patterns().find(function (p) { return p && p.id === zone.pattern; }) || {}).name || zone.pattern;
        var patLabel = (zone.pattern && zone.pattern !== 'none') ? ' (keeping ' + currentPattern + ' overlay)' : '';
        showToast('Special: ' + mono.name + patLabel + ' => ' + zone.name);
      } else {
        zone.finish = finishId;
        zone.base = null;
        zone.pattern = null;
        if (deps.renderZones) deps.renderZones();
        if (deps.triggerPreviewRender) deps.triggerPreviewRender();
        showToast('Assigned ' + finishId + ' to ' + zone.name);
      }
    }

    var api = {
      assignFinishToSelected: assignFinishToSelected,
      getBaseGroup: getBaseGroup,
      normalizeFinishId: normalizeFinishId,
      applyPickedBaseToZone: applyPickedBaseToZone,
      applyPickedMonolithicToZone: applyPickedMonolithicToZone,
      hexLooksDark: hexLooksDark,
      finishNeedsAlbedoHint: finishNeedsAlbedoHint,
      maybeShowAlbedoHint: maybeShowAlbedoHint
    };
    global.assignFinishToSelected = assignFinishToSelected;
    global._spbApplyPickedBaseToZone = applyPickedBaseToZone;
    global._spbApplyPickedMonolithicToZone = applyPickedMonolithicToZone;
    global._maybeShowAlbedoHint = maybeShowAlbedoHint;
    global._hexLooksDark = hexLooksDark;
    global._finishNeedsAlbedoHint = finishNeedsAlbedoHint;
    return api;
  }

  global.SPBZoneFinishAssignmentControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
