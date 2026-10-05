(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var cryptoApi = deps.crypto || global.crypto;
    var consoleApi = deps.console || global.console || { warn: function () {} };

    function newZoneId() {
      if (cryptoApi && typeof cryptoApi.randomUUID === 'function') return 'zone_' + cryptoApi.randomUUID();
      return 'zone_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
    }

    function cloneUint8ArrayLike(value) {
      if (!value) return null;
      if (value instanceof Uint8Array) return new Uint8Array(value);
      if (Array.isArray(value)) return new Uint8Array(value);
      if (typeof value === 'object') {
        var numericKeys = Object.keys(value)
          .filter(function (k) { return /^\d+$/.test(k); })
          .sort(function (a, b) { return Number(a) - Number(b); });
        if (numericKeys.length) return new Uint8Array(numericKeys.map(function (k) { return value[k] || 0; }));
      }
      return null;
    }

    function clonePatternStrengthMap(map) {
      if (!map || !map.data || !map.width || !map.height) return null;
      var data = cloneUint8ArrayLike(map.data);
      return data ? { width: map.width, height: map.height, data: data } : null;
    }

    function cloneZoneState(zone, options) {
      var opts = options || {};
      var baseClone = JSON.parse(JSON.stringify(Object.assign({}, zone, {
        regionMask: null,
        spatialMask: null,
        patternStrengthMap: null,
      })));
      baseClone.id = (opts.preserveId === false || baseClone.id == null || baseClone.id === '') ? newZoneId() : baseClone.id;
      baseClone.regionMask = opts.includeRegionMask ? cloneUint8ArrayLike(zone && zone.regionMask) : null;
      baseClone.spatialMask = opts.includeSpatialMask ? cloneUint8ArrayLike(zone && zone.spatialMask) : null;
      if (opts.includePatternStrengthMap !== false) baseClone.patternStrengthMap = clonePatternStrengthMap(zone && zone.patternStrengthMap);
      return baseClone;
    }

    function ensureZoneShape(zone, options) {
      var opts = options || {};
      var next = cloneZoneState(zone || {}, {
        preserveId: true,
        includeRegionMask: !!opts.includeRegionMask,
        includeSpatialMask: !!opts.includeSpatialMask,
        includePatternStrengthMap: true,
      });
      if (next.id == null || next.id === '') next.id = newZoneId();
      return next;
    }

    function ensureAllZonesHaveIds(zoneList) {
      if (!Array.isArray(zoneList)) return;
      zoneList.forEach(function (z) { if (z && (z.id == null || z.id === '')) z.id = newZoneId(); });
    }

    function hasAnyMaskPixels(mask) {
      if (!mask) return false;
      try {
        if (typeof mask.some === 'function') return mask.some(function (v) { return v > 0; });
        if (Array.isArray(mask) || typeof mask.length === 'number') {
          for (var i = 0; i < mask.length; i++) if (mask[i] > 0) return true;
        }
      } catch (_) {}
      return false;
    }

    function zoneHasAuthoredLayerWork(zone) {
      if (!zone) return false;
      if (zone.sourceLayer || zone.zoneSpecMapPath) return true;
      var stackKeys = ['patternStack', 'specPatternStack', 'overlaySpecPatternStack', 'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack', 'fifthOverlaySpecPatternStack'];
      for (var i = 0; i < stackKeys.length; i++) if (Array.isArray(zone[stackKeys[i]]) && zone[stackKeys[i]].length > 0) return true;
      var overlayKeys = ['secondBase', 'thirdBase', 'fourthBase', 'fifthBase'];
      for (var j = 0; j < overlayKeys.length; j++) if (zone[overlayKeys[j]]) return true;
      return false;
    }

    function isZone9MatteCarbonZombie(zone, index) {
      if (!zone) return false;
      var name = String(zone.name || '').trim().toLowerCase();
      var looksLikeZone9 = index === 8 || name === 'zone 9' || name === 'open zone 9' || /\bzone\s*9\b/.test(name);
      return looksLikeZone9 && zone.base === 'matte' && zone.pattern === 'carbon_fiber' && !zone.finish
        && !hasAnyMaskPixels(zone.regionMask) && !hasAnyMaskPixels(zone.spatialMask) && !zoneHasAuthoredLayerWork(zone);
    }

    function sanitizeZone9MatteCarbonZombie(zone, index, source) {
      if (!isZone9MatteCarbonZombie(zone, index)) return false;
      zone.base = null;
      zone.pattern = 'none';
      zone.finish = null;
      if (zone.color == null || zone.color === 'dark') {
        zone.color = null;
        zone.colorMode = 'none';
      }
      zone.hint = 'Empty by default. Legacy matte carbon auto-fill was removed.';
      try { consoleApi.warn('[SPB][zone-sanitize] stripped legacy Zone 9 matte/carbon zombie from ' + (source || 'zone state')); } catch (_) {}
      return true;
    }

    function sanitizeZonesInPlace(zoneList, source) {
      if (!Array.isArray(zoneList)) return 0;
      var fixed = 0;
      zoneList.forEach(function (zone, index) { if (sanitizeZone9MatteCarbonZombie(zone, index, source)) fixed++; });
      return fixed;
    }

    var api = {
      newZoneId: newZoneId,
      cloneUint8ArrayLike: cloneUint8ArrayLike,
      clonePatternStrengthMap: clonePatternStrengthMap,
      cloneZoneState: cloneZoneState,
      ensureZoneShape: ensureZoneShape,
      ensureAllZonesHaveIds: ensureAllZonesHaveIds,
      hasAnyMaskPixels: hasAnyMaskPixels,
      zoneHasAuthoredLayerWork: zoneHasAuthoredLayerWork,
      isZone9MatteCarbonZombie: isZone9MatteCarbonZombie,
      sanitizeZone9MatteCarbonZombie: sanitizeZone9MatteCarbonZombie,
      sanitizeZonesInPlace: sanitizeZonesInPlace,
    };
    global._sanitizeZonesInPlace = sanitizeZonesInPlace;
    global._isZone9MatteCarbonZombie = isZone9MatteCarbonZombie;
    return api;
  }

  global.SPBZoneStateShapeControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
