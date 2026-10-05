'use strict';

(function (global) {
  function noop() {}

  function install(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function () { return []; };
    const getBases = deps.getBases || function () { return []; };
    const getDocument = deps.getDocument || function () { return global.document || null; };
    const getPatternName = deps.getPatternName || function (id) { return id || 'None'; };
    const normalizeOverlayReactPatternValue = deps.normalizeOverlayReactPatternValue || function (value) { return value || ''; };
    const getLinkFinishProps = deps.getLinkFinishProps || function () { return global.LINK_FINISH_PROPS || []; };
    const pushZoneUndo = deps.pushZoneUndo || noop;
    const pushZoneUndoCoalesced = deps.pushZoneUndoCoalesced || pushZoneUndo;
    const applyPickedBaseToZone = deps.applyPickedBaseToZone || noop;
    const applyPickedMonolithicToZone = deps.applyPickedMonolithicToZone || noop;
    const propagateToLinkedZones = deps.propagateToLinkedZones || noop;
    const renderZones = deps.renderZones || noop;
    const triggerPreviewRender = deps.triggerPreviewRender || noop;
    const showToast = deps.showToast || noop;
    const logger = deps.console || global.console || { warn: noop };

    function isValidZoneIndex(index, label) {
      const zones = getZones();
      if (typeof index === 'number' && index >= 0 && index < zones.length) return true;
      logger.warn('[SPB] ' + label + ': invalid zone index', index);
      return false;
    }

    function resetHiddenSpecStrength(index, zone) {
      if ((zone.baseSpecStrength ?? 1) > 0.05) return;
      zone.baseSpecStrength = 1;
      const doc = getDocument();
      const label = doc && doc.getElementById ? doc.getElementById('detBaseSpecStrVal' + index) : null;
      if (label) label.textContent = '100%';
      showToast('Spec Strength was near 0%. Reset to 100% so metallic (R) is visible.');
    }

    function setZoneBase(index, value) {
      if (!isValidZoneIndex(index, 'setZoneBase')) return;
      if (value !== null && value !== undefined && typeof value !== 'string') {
        logger.warn('[SPB] setZoneBase: value must be a string or null, got', typeof value);
        return;
      }
      const zones = getZones();
      const zone = zones[index];
      pushZoneUndo('Set base: ' + (value || 'none'));
      resetHiddenSpecStrength(index, zone);
      if (value && value.startsWith('mono:')) {
        const monoId = value.replace('mono:', '');
        const isBase = getBases().find(function (base) { return base && base.id === monoId; });
        if (isBase) applyPickedBaseToZone(zone, monoId);
        else applyPickedMonolithicToZone(zone, monoId);
        if (!zone.pattern) zone.pattern = 'none';
      } else {
        applyPickedBaseToZone(zone, value || null);
      }
      propagateToLinkedZones(index, getLinkFinishProps());
      renderZones();
      triggerPreviewRender();
    }

    function setZonePattern(index, patternId) {
      if (!isValidZoneIndex(index, 'setZonePattern')) return;
      if (patternId !== null && patternId !== undefined && typeof patternId !== 'string') {
        logger.warn('[SPB] setZonePattern: patternId must be a string, got', typeof patternId);
        return;
      }
      const zones = getZones();
      pushZoneUndo('Set pattern: ' + (patternId || 'none'));
      zones[index].pattern = patternId || 'none';
      propagateToLinkedZones(index, ['pattern']);
      renderZones();
      triggerPreviewRender();
    }

    function setZoneWear(index, val) {
      if (!isValidZoneIndex(index, 'setZoneWear')) return;
      const zones = getZones();
      pushZoneUndoCoalesced('Set wear');
      const clamped = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
      zones[index].wear = clamped;
      const doc = getDocument();
      const label = doc && doc.getElementById
        ? (doc.getElementById('detWearVal' + index) || doc.getElementById('wearVal' + index))
        : null;
      if (label) label.textContent = clamped + '%';
      triggerPreviewRender();
    }

    function getZonePatternReactOptions(zone) {
      const opts = [{ value: '__none__', label: 'None (Independent)' }];
      const primaryId = zone.pattern && zone.pattern !== 'none' ? zone.pattern : null;
      opts.push({ value: '', label: 'Pattern 1 (' + (primaryId ? getPatternName(primaryId) : 'Primary - None') + ')' });
      (zone.patternStack || []).slice(0, 4).forEach(function (layer, idx) {
        if (layer && layer.id && layer.id !== 'none') {
          opts.push({ value: layer.id, label: 'Pattern ' + (idx + 2) + ' (' + getPatternName(layer.id) + ')' });
        }
      });
      return opts;
    }

    function getOverlayReactToSelectValue(zone, overlayPatternId) {
      if (overlayPatternId === '') return '';
      const normalized = normalizeOverlayReactPatternValue(overlayPatternId);
      if (normalized === '__none__') return '__none__';
      const stack = zone.patternStack || [];
      for (let i = 0; i < 4; i += 1) {
        if (stack[i] && normalized === stack[i].id) return normalized;
      }
      if (zone.pattern && normalized === zone.pattern) return '';
      return normalized;
    }

    Object.assign(global, {
      setZoneBase: setZoneBase,
      setZonePattern: setZonePattern,
      setZoneWear: setZoneWear,
      getZonePatternReactOptions: getZonePatternReactOptions,
      getOverlayReactToSelectValue: getOverlayReactToSelectValue
    });

    return {
      setZoneBase: setZoneBase,
      setZonePattern: setZonePattern,
      setZoneWear: setZoneWear,
      getZonePatternReactOptions: getZonePatternReactOptions,
      getOverlayReactToSelectValue: getOverlayReactToSelectValue
    };
  }

  global.SPBZoneMaterialAssignmentControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
