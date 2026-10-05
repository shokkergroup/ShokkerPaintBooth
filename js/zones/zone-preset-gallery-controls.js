(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var getPresets = deps.getPresets || function() { return {}; };
    var getSpecialColors = deps.getSpecialColors || function() { return []; };
    var getQuickColors = deps.getQuickColors || function() { return []; };
    var setZones = deps.setZones || function() {};
    var setSelectedZoneIndex = deps.setSelectedZoneIndex || function() {};
    var newZoneId = deps.newZoneId || function() { return Date.now() + '-' + Math.random(); };
    var sanitizeZonesInPlace = deps.sanitizeZonesInPlace || function() {};
    var renderZones = deps.renderZones || function() {};
    var showToast = deps.showToast || function() {};
    var consoleObj = deps.console || global.console || { warn: function() {} };

    function cloneMaterialStack(zone) {
      var raw = Array.isArray(zone && zone.materialStack)
        ? zone.materialStack
        : (Array.isArray(zone && zone.material_stack) ? zone.material_stack : []);
      return raw.map(function(item) {
        return item && typeof item === 'object' ? Object.assign({}, item) : item;
      });
    }

    function toggleSection(id) {
      var body = doc && doc.getElementById ? doc.getElementById(id + '-body') : null;
      var toggle = doc && doc.getElementById ? doc.getElementById(id + '-toggle') : null;
      var header = toggle && toggle.closest ? toggle.closest('.section-header') : null;
      if (!body || !header) return;
      if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        header.classList.remove('collapsed');
      } else {
        body.classList.add('collapsed');
        header.classList.add('collapsed');
      }
    }

    function applyPreset(arg) {
      if (typeof arg === 'string') {
        return applyPresetById(arg);
      }
      if (arg && typeof arg === 'object' && Array.isArray(arg.zones)) {
        return (typeof global._applyPresetFromObject === 'function') ? global._applyPresetFromObject(arg) : null;
      }
      if (consoleObj && typeof consoleObj.warn === 'function') {
        consoleObj.warn('[SPB] applyPreset called with unsupported arg:', arg);
      }
      return null;
    }

    function applyPresetById(presetId) {
      var presets = getPresets() || {};
      if (!presetId || !presets[presetId]) return null;
      var preset = presets[presetId];
      var specialColors = getSpecialColors() || [];
      var quickColors = getQuickColors() || [];
      var nextZones = (preset.zones || []).map(function(z) {
        return {
          id: newZoneId(),
          name: z.name,
          color: z.color,
          base: z.base || null,
          pattern: z.pattern || 'none',
          finish: z.finish || null,
          materialStack: cloneMaterialStack(z),
          materialStackMode: z.materialStackMode ?? z.material_stack_mode ?? null,
          materialStackAmount: z.materialStackAmount ?? z.material_stack_amount ?? null,
          materialScale: z.materialScale ?? z.material_scale ?? 1,
          intensity: z.intensity,
          customSpec: null,
          customPaint: null,
          customBright: null,
          hint: z.hint || '',
          colorMode: z.color === null ? 'none'
            : specialColors.some(function(sc) { return sc.value === z.color; }) ? 'special'
            : quickColors.some(function(qc) { return qc.value === z.color; }) ? 'quick'
            : 'text',
          pickerColor: '#3366ff',
          pickerTolerance: 40,
          colors: [],
          regionMask: null,
          lockBase: false,
          lockPattern: false,
          lockIntensity: false,
          lockColor: false,
          patternStack: []
        };
      });
      sanitizeZonesInPlace(nextZones, 'built-in preset: ' + presetId);
      setZones(nextZones);
      setSelectedZoneIndex(0);
      renderZones();
      showToast('Loaded preset: ' + (preset.name || presetId) + ' - set colors using the eyedropper!');
      return preset;
    }

    Object.assign(global, {
      toggleSection: toggleSection,
      applyPreset: applyPreset,
      _applyPresetById: applyPresetById
    });

    return {
      toggleSection: toggleSection,
      applyPreset: applyPreset,
      applyPresetById: applyPresetById
    };
  }

  global.SPBZonePresetGalleryControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
