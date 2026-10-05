'use strict';

(function(global) {
  function install(deps) {
    deps = deps || {};
    var getZones = deps.getZones || function() { return []; };
    var pushZoneUndo = deps.pushZoneUndo || function() {};
    var renderZones = deps.renderZones || function() {};
    var renderZoneDetail = deps.renderZoneDetail || function() {};
    var refreshFineTuningIfOpen = deps.refreshFineTuningIfOpen || function() {};
    var triggerPreviewRender = deps.triggerPreviewRender || function() {};
    var showToast = deps.showToast || function() {};

    function zoneAt(index) {
      return getZones()[index];
    }

    function markUserEdit(index) {
      var zone = zoneAt(index);
      if (zone) zone._scopedBrushAutoBaseColor = false;
    }

    function getBaseOverlayPrefix(layer) {
      if (layer === 'second' || layer === 2 || layer === '2') return 'secondBase';
      if (layer === 'third' || layer === 3 || layer === '3') return 'thirdBase';
      if (layer === 'fourth' || layer === 4 || layer === '4') return 'fourthBase';
      if (layer === 'fifth' || layer === 5 || layer === '5') return 'fifthBase';
      return null;
    }

    function layerHasSettings(zone, layer) {
      var prefix = getBaseOverlayPrefix(layer);
      return !!(zone && prefix && (zone[prefix] || zone[prefix + 'ColorSource']));
    }

    function isLayerEnabled(zone, layer) {
      var prefix = getBaseOverlayPrefix(layer);
      return !zone || !prefix || zone[prefix + 'Enabled'] !== false;
    }

    function layerStateLabel(zone, layer) {
      if (!layerHasSettings(zone, layer)) return 'Empty';
      return isLayerEnabled(zone, layer) ? 'Active' : 'Muted';
    }

    function layerStateColor(zone, layer) {
      if (!layerHasSettings(zone, layer)) return '#6f8494';
      return isLayerEnabled(zone, layer) ? '#33ff66' : '#ffb84d';
    }

    function renderEnableToggle(zone, zoneIndex, layer, label) {
      var hasSettings = layerHasSettings(zone, layer);
      var checked = isLayerEnabled(zone, layer) ? 'checked' : '';
      var status = hasSettings ? (checked ? 'On' : 'Off') : 'Empty';
      var emptyClass = hasSettings ? '' : ' base-overlay-empty';
      var title = hasSettings
        ? label + ' overlay preview/render toggle. Settings stay saved when off.'
        : label + ' overlay has no base selected yet. Pick a ' + label + ' base to make this affect preview/render.';
      return '<label class="base-overlay-enable-toggle' + emptyClass + '" title="' + title + '" onclick="event.stopPropagation();">'
        + '<input type="checkbox" ' + checked + ' aria-label="' + label + ' base overlay preview render toggle" onchange="setZoneBaseOverlayEnabled(' + zoneIndex + ', \'' + layer + '\', this.checked)">'
        + '<span class="base-overlay-toggle-track" aria-hidden="true"></span>'
        + '<span class="base-overlay-toggle-text">' + status + '</span>'
        + '</label>';
    }

    function setZoneBaseOverlayEnabled(index, layer, enabled) {
      var zone = zoneAt(index);
      var prefix = getBaseOverlayPrefix(layer);
      if (!zone || !prefix) return;
      pushZoneUndo((enabled ? 'Enable' : 'Disable') + ' base overlay', true);
      markUserEdit(index);
      zone[prefix + 'Enabled'] = !!enabled;
      renderZones();
      renderZoneDetail(index);
      refreshFineTuningIfOpen();
      triggerPreviewRender();
      var label = layer ? String(layer).charAt(0).toUpperCase() + String(layer).slice(1) : 'Base';
      showToast(label + ' base overlay ' + (enabled ? 'enabled' : 'muted') + ' (settings preserved)');
    }

    function normalizeOverlayReactPatternValue(val) {
      if (val === '' || val == null) return '';
      var raw = String(val).trim();
      var normalized = raw.toLowerCase().replace(/[\s-]+/g, '_');
      if (
        normalized === 'none' ||
        normalized === '_none_' ||
        normalized === '__none__' ||
        normalized === 'none_(base_only)' ||
        normalized === 'none_(independent)' ||
        normalized === 'base_only'
      ) return '__none__';
      return raw;
    }

    function defaultOverlayReactPatternToIndependent(index, prop) {
      var zone = zoneAt(index);
      if (zone && normalizeOverlayReactPatternValue(zone[prop]) === '__none__') zone[prop] = '__none__';
    }

    function overlayBlendModeRequiresPattern(mode) {
      var normalized = String(mode || '').trim().toLowerCase().replace(/[\s_]+/g, '-');
      return [
        'pattern', 'pattern-reactive', 'pattern-vivid', 'pattern-pop', 'pattern-edges',
        'pattern-peaks', 'pattern-contour', 'pattern-screen', 'pattern-stream', 'pattern-threshold'
      ].indexOf(normalized) >= 0;
    }

    function preferredOverlayReactPatternValue(zone) {
      if (!zone) return '__none__';
      if (zone.pattern && zone.pattern !== 'none') return '';
      var first = (zone.patternStack || []).find(function(entry) { return entry && entry.id && entry.id !== 'none'; });
      return first ? first.id : '__none__';
    }

    function autoAttachOverlayPatternForBlend(index, prop, blendMode) {
      var zone = zoneAt(index);
      if (!zone || !overlayBlendModeRequiresPattern(blendMode)) return;
      if (normalizeOverlayReactPatternValue(zone[prop]) === '__none__') {
        zone[prop] = preferredOverlayReactPatternValue(zone);
      }
    }

    function allocateUnusedPatternForOverlay(zone) {
      if (!zone) return '';
      var used = new Set([zone.secondBasePattern, zone.thirdBasePattern, zone.fourthBasePattern, zone.fifthBasePattern].filter(function(id) { return id && id !== 'none'; }));
      var available = [''];
      (zone.patternStack || []).slice(0, 2).forEach(function(entry) {
        if (entry && entry.id && entry.id !== 'none') available.push(entry.id);
      });
      return available.find(function(id) { return !used.has(id); }) || '';
    }

    Object.assign(global, {
      setZoneBaseOverlayEnabled: setZoneBaseOverlayEnabled,
      isBaseOverlayLayerEnabled: isLayerEnabled
    });

    return {
      markUserEdit: markUserEdit,
      getBaseOverlayPrefix: getBaseOverlayPrefix,
      layerHasSettings: layerHasSettings,
      isLayerEnabled: isLayerEnabled,
      layerStateLabel: layerStateLabel,
      layerStateColor: layerStateColor,
      renderEnableToggle: renderEnableToggle,
      setZoneBaseOverlayEnabled: setZoneBaseOverlayEnabled,
      normalizeOverlayReactPatternValue: normalizeOverlayReactPatternValue,
      defaultOverlayReactPatternToIndependent: defaultOverlayReactPatternToIndependent,
      overlayBlendModeRequiresPattern: overlayBlendModeRequiresPattern,
      preferredOverlayReactPatternValue: preferredOverlayReactPatternValue,
      autoAttachOverlayPatternForBlend: autoAttachOverlayPatternForBlend,
      allocateUnusedPatternForOverlay: allocateUnusedPatternForOverlay
    };
  }

  global.SPBZoneBaseOverlayStateControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
