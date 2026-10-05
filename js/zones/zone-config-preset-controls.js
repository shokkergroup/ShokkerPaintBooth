(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var getZones = deps.getZones || function () { return []; };
    var setZones = deps.setZones || function () {};
    var setSelectedZoneIndex = deps.setSelectedZoneIndex || function () {};
    var newZoneId = deps.newZoneId || function () { return 'zone_' + Date.now(); };
    var sanitizeZones = deps.sanitizeZones || function () {};
    var getConfig = deps.getConfig || global.getConfig;
    var loadConfigFromObj = deps.loadConfigFromObj || global.loadConfigFromObj;
    var showToast = deps.showToast || global.showToast || function () {};
    var renderZones = deps.renderZones || function () {};
    var triggerPreviewRender = deps.triggerPreviewRender || function () {};
    var autoSave = deps.autoSave || function () {};
    var updateWearDisplay = deps.updateWearDisplay || function () {};
    var toggleNightBoostSlider = deps.toggleNightBoostSlider || function () {};
    var getRegistries = deps.getRegistries || function () { return { bases: [], patterns: [], monolithics: [] }; };
    var promptFn = deps.prompt || global.prompt;
    var confirmFn = deps.confirm || global.confirm;
    var BlobCtor = deps.Blob || global.Blob;
    var URLApi = deps.URL || global.URL;
    var FileReaderCtor = deps.FileReader || global.FileReader;

    function cloneMaterialStack(zone) {
      var raw = Array.isArray(zone && zone.materialStack)
        ? zone.materialStack
        : (Array.isArray(zone && zone.material_stack) ? zone.material_stack : []);
      return raw.map(function(item) {
        return item && typeof item === 'object' ? Object.assign({}, item) : item;
      });
    }

    function byId(id) {
      return doc && doc.getElementById ? doc.getElementById(id) : null;
    }

    function downloadJson(data, filename) {
      var json = JSON.stringify(data, null, 2);
      var blob = new BlobCtor([json], { type: 'application/json' });
      var a = doc.createElement('a');
      a.href = URLApi.createObjectURL(blob);
      a.download = filename;
      a.click();
      URLApi.revokeObjectURL(a.href);
    }

    function getSessionConfig() {
      return getConfig();
    }

    function applySessionConfig(cfg) {
      if (cfg && (cfg.zones || cfg.driverName !== undefined)) loadConfigFromObj(cfg);
    }

    function saveConfig() {
      downloadJson(getConfig(), 'shokker_paintbooth_config_' + Date.now() + '.json');
      showToast('Config saved!');
    }

    function exportPreset() {
      var driverName = ((byId('driverName') && byId('driverName').value) || '').trim() || 'Unknown';
      var carName = ((byId('carName') && byId('carName').value) || '').trim() || 'Unknown Car';
      var presetName = promptFn && promptFn('Preset name:', driverName + ' - ' + carName);
      if (!presetName) return;
      var zones = getZones();
      var preset = {
        _shokker_preset: true,
        version: '1.0',
        name: presetName,
        author: driverName,
        car: carName,
        created: new Date().toISOString(),
        description: buildPresetDescription(),
        zones: zones.map(function (z) {
          return {
            name: z.name,
            renderSeedIndex: (global.SPBStableZoneSeeds && global.SPBStableZoneSeeds.validIndex(z.renderSeedIndex)) ? z.renderSeedIndex : undefined,
            base: z.base,
            pattern: z.pattern,
            finish: z.finish,
            materialStack: cloneMaterialStack(z),
            materialStackMode: z.materialStackMode ?? z.material_stack_mode ?? null,
            materialStackAmount: z.materialStackAmount ?? z.material_stack_amount ?? null,
            materialScale: z.materialScale ?? z.material_scale ?? 1,
            intensity: z.intensity,
            customSpec: z.customSpec != null ? z.customSpec : undefined,
            customPaint: z.customPaint != null ? z.customPaint : undefined,
            customBright: z.customBright != null ? z.customBright : undefined,
            color: z.color,
            colorMode: z.colorMode,
            pickerColor: z.pickerColor,
            pickerTolerance: z.pickerTolerance,
            colors: z.colors || [],
            zoneSpecMapPath: z.zoneSpecMapPath ?? null,
            zoneSpecMapName: z.zoneSpecMapName ?? null,
            zoneSpecMapResolution: z.zoneSpecMapResolution ?? null,
            zoneSpecMapStrength: z.zoneSpecMapStrength ?? 100,
            scale: z.scale ?? 1.0,
            rotation: z.rotation ?? 0,
            patternOpacity: z.patternOpacity ?? 100,
            patternOffsetX: z.patternOffsetX ?? 0.5,
            patternOffsetY: z.patternOffsetY ?? 0.5,
            patternStack: z.patternStack || [],
            patternInstances: Array.isArray(z.patternInstances) ? JSON.parse(JSON.stringify(z.patternInstances)) : [],
            specPatternStack: z.specPatternStack || [],
            overlaySpecPatternStack: z.overlaySpecPatternStack || [],
            thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
            fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
            fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
            wear: z.wear ?? 0,
            muted: z.muted ?? false
          };
        }),
        settings: {
          wearLevel: parseInt((byId('wearSlider') && byId('wearSlider').value) || '0', 10),
          dualSpec: (byId('dualSpecCheckbox') && byId('dualSpecCheckbox').checked) || false,
          nightBoost: parseFloat((byId('nightBoostSlider') && byId('nightBoostSlider').value) || '0.7')
        },
        finishCount: zones.filter(function (z) { return z.base || z.finish || cloneMaterialStack(z).length > 0; }).length,
        colorCount: zones.filter(function (z) { return z.color !== null || z.colorMode === 'multi'; }).length
      };
      var safeName = presetName.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_');
      downloadJson(preset, safeName + '.shokker');
      showToast('Preset exported: ' + presetName);
    }

    function buildPresetDescription() {
      var registries = getRegistries();
      return getZones().map(function (z) {
        var finish = '';
        if (z.finish) {
          var mono = registries.monolithics.find(function (m) { return m.id === z.finish; });
          finish = mono ? mono.name : z.finish;
        } else if (z.base) {
          var b = registries.bases.find(function (base) { return base.id === z.base; });
          var p = z.pattern && z.pattern !== 'none' ? registries.patterns.find(function (pat) { return pat.id === z.pattern; }) : null;
          finish = b ? b.name : z.base;
          if (p) finish += ' + ' + p.name;
        }
        return z.name + ': ' + (finish || 'No finish');
      }).join(' | ');
    }

    function importPreset() {
      openJsonFile('.shokker,.json', function (data) {
        if (data._shokker_preset) {
          applyPreset(data);
        } else if (data.zones) {
          loadConfigFromObj(data);
          showToast('Loaded as config (not a preset file)');
          throw new Error('Not a valid .shokker preset');
        }
      }, function (err) {
        showToast('Invalid preset file: ' + err.message, true);
      });
    }

    function applyPreset(arg) {
      if (global.applyPreset && typeof arg === 'string') return global.applyPreset(arg);
      return _applyPresetFromObject(arg);
    }

    function _applyPresetFromObject(preset) {
      if (!preset || !Array.isArray(preset.zones)) return;
      var info = '"' + preset.name + '"' + (preset.author ? ' by ' + preset.author : '') + '\n'
        + preset.zones.length + ' zones | ' + (preset.finishCount || '?') + ' finishes\n\n'
        + 'Apply this preset? (Your current zones will be replaced)';
      if (confirmFn && !confirmFn(info)) return;
      var nextZones = preset.zones.map(function (z) {
        return {
          id: newZoneId(),
          name: z.name || 'Zone',
          renderSeedIndex: (global.SPBStableZoneSeeds && global.SPBStableZoneSeeds.validIndex(z.renderSeedIndex)) ? z.renderSeedIndex : undefined,
          color: z.color,
          base: z.base || null,
          pattern: z.pattern || 'none',
          finish: z.finish || null,
          materialStack: cloneMaterialStack(z),
          materialStackMode: z.materialStackMode ?? z.material_stack_mode ?? null,
          materialStackAmount: z.materialStackAmount ?? z.material_stack_amount ?? null,
          materialScale: z.materialScale ?? z.material_scale ?? 1,
          intensity: z.intensity ?? '100',
          customSpec: z.customSpec != null ? z.customSpec : null,
          customPaint: z.customPaint != null ? z.customPaint : null,
          customBright: z.customBright != null ? z.customBright : null,
          colorMode: z.colorMode || 'none',
          pickerColor: z.pickerColor || '#3366ff',
          pickerTolerance: z.pickerTolerance ?? 40,
          colors: z.colors || [],
          zoneSpecMapPath: z.zoneSpecMapPath ?? null,
          zoneSpecMapName: z.zoneSpecMapName ?? null,
          zoneSpecMapResolution: z.zoneSpecMapResolution ?? null,
          zoneSpecMapStrength: z.zoneSpecMapStrength ?? 100,
          regionMask: null,
          lockBase: false,
          lockPattern: false,
          lockIntensity: false,
          lockColor: false,
          scale: z.scale ?? 1.0,
          patternOpacity: z.patternOpacity ?? 100,
          patternOffsetX: z.patternOffsetX ?? 0.5,
          patternOffsetY: z.patternOffsetY ?? 0.5,
          patternStack: z.patternStack || [],
            patternInstances: Array.isArray(z.patternInstances) ? JSON.parse(JSON.stringify(z.patternInstances)) : [],
          specPatternStack: z.specPatternStack || [],
          overlaySpecPatternStack: z.overlaySpecPatternStack || [],
          thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack || [],
          fourthOverlaySpecPatternStack: z.fourthOverlaySpecPatternStack || [],
          fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack || [],
          wear: z.wear ?? 0,
          muted: z.muted ?? false
        };
      });
      sanitizeZones(nextZones, 'imported preset: ' + (preset.name || 'unnamed'));
      setZones(nextZones);
      setSelectedZoneIndex(0);
      applyPresetSettings(preset.settings);
      renderZones();
      triggerPreviewRender();
      autoSave();
      showToast('Preset loaded: "' + preset.name + '" - ' + preset.zones.length + ' zones');
    }

    function applyPresetSettings(settings) {
      if (!settings) return;
      if (settings.wearLevel !== undefined && byId('wearSlider')) {
        byId('wearSlider').value = settings.wearLevel;
        updateWearDisplay(settings.wearLevel);
      }
      if (settings.dualSpec !== undefined && byId('dualSpecCheckbox')) {
        byId('dualSpecCheckbox').checked = settings.dualSpec;
        toggleNightBoostSlider();
      }
      if (settings.nightBoost !== undefined && byId('nightBoostSlider')) {
        byId('nightBoostSlider').value = settings.nightBoost;
        if (byId('nightBoostVal')) byId('nightBoostVal').textContent = parseFloat(settings.nightBoost).toFixed(2);
      }
    }

    function loadConfig() {
      openJsonFile('.json', function (cfg) {
        loadConfigFromObj(cfg);
        showToast('Config loaded!');
      }, function () {
        showToast('Invalid config file', true);
      });
    }

    function openJsonFile(accept, onData, onError) {
      var input = doc.createElement('input');
      input.type = 'file';
      input.accept = accept;
      input.onchange = function (e) {
        var file = e.target.files[0];
        if (!file) return;
        var reader = new FileReaderCtor();
        reader.onload = function (ev) {
          try { onData(JSON.parse(ev.target.result)); } catch (err) { onError(err); }
        };
        reader.readAsText(file);
      };
      input.click();
    }

    Object.assign(global, {
      getSessionConfig: getSessionConfig,
      applySessionConfig: applySessionConfig,
      saveConfig: saveConfig,
      exportPreset: exportPreset,
      buildPresetDescription: buildPresetDescription,
      importPreset: importPreset,
      _applyPresetFromObject: _applyPresetFromObject,
      loadConfig: loadConfig
    });
  }

  global.SPBZoneConfigPresetControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
