(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getZones = typeof deps.getZones === 'function' ? deps.getZones : function() { return []; };
    var renderZones = typeof deps.renderZones === 'function' ? deps.renderZones : function() {};
    var showToast = typeof deps.showToast === 'function' ? deps.showToast : function() {};
    var getSpecPatternLayerDefaults = typeof deps.getSpecPatternLayerDefaults === 'function'
      ? deps.getSpecPatternLayerDefaults
      : function() { return { channels: 'MR' }; };

    // 2026-04-19 HEENAN HP-MIGRATE: saved-config legacy-ID migration.
    // Saved zone configs, autosaves, and presets created before collision
    // renames need deterministic rewrites so prior painter work still resolves.
    var _SPB_LEGACY_ID_MIGRATIONS = Object.freeze({
      monolithic: Object.freeze({
        acid_rain: 'acid_rain_drip',
        crystal_lattice: 'crystal_lattice_mono'
      }),
      pattern: Object.freeze({
        shokk_cipher: 'shokk_cipher_pattern',
        dragonfly_wing: 'dragonfly_wing_pattern',
        carbon_weave: 'carbon_weave_pattern'
      }),
      specPattern: Object.freeze({
        carbon_weave: 'spec_carbon_weave',
        diffraction_grating: 'spec_diffraction_grating_cd',
        oil_slick: 'spec_oil_slick',
        gravity_well: 'spec_gravity_well',
        sparkle_constellation: 'spec_sparkle_constellation',
        sparkle_firefly: 'spec_sparkle_firefly',
        sparkle_champagne: 'spec_sparkle_champagne'
      })
    });

    function _migrateZoneFinishIds(zone) {
      if (!zone) return 0;
      var changed = 0;
      var M = _SPB_LEGACY_ID_MIGRATIONS;
      if (zone.finish && M.monolithic[zone.finish]) {
        zone.finish = M.monolithic[zone.finish];
        changed++;
      }
      if (zone.pattern && M.pattern[zone.pattern]) {
        zone.pattern = M.pattern[zone.pattern];
        changed++;
      }
      if (Array.isArray(zone.patternStack)) {
        zone.patternStack.forEach(function(entry) {
          if (entry && entry.id && M.pattern[entry.id]) {
            entry.id = M.pattern[entry.id];
            changed++;
          }
        });
      }
      ['specPatternStack', 'overlaySpecPatternStack',
        'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack',
        'fifthOverlaySpecPatternStack'].forEach(function(stackKey) {
        var stack = zone[stackKey];
        if (!Array.isArray(stack)) return;
        stack.forEach(function(entry) {
          if (entry && entry.id && M.specPattern[entry.id]) {
            entry.id = M.specPattern[entry.id];
            changed++;
          }
        });
      });
      return changed;
    }

    function _normalizeLegacySpecPatternChannels(zone) {
      if (!zone) return 0;
      var changed = 0;
      ['specPatternStack', 'overlaySpecPatternStack',
        'thirdOverlaySpecPatternStack', 'fourthOverlaySpecPatternStack',
        'fifthOverlaySpecPatternStack'].forEach(function(stackKey) {
        var stack = zone[stackKey];
        if (!Array.isArray(stack)) return;
        stack.forEach(function(entry) {
          if (!entry || !entry.pattern) return;
          if (entry.render_version >= 2 && entry.channels === '') return;
          var defaults = getSpecPatternLayerDefaults(entry.pattern);
          var currentChannels = String(entry.channels || '').trim().toUpperCase();
          if (!currentChannels) {
            entry.channels = defaults.channels;
            entry.channelsCustomized = false;
            changed++;
            return;
          }
          if (entry.channelsCustomized == null) {
            if (currentChannels === 'MR' && defaults.channels !== 'MR') {
              entry.channels = defaults.channels;
              entry.channelsCustomized = false;
              changed++;
              return;
            }
            entry.channelsCustomized = currentChannels !== defaults.channels;
          }
        });
      });
      return changed;
    }

    function repairZoneData() {
      var fixed = 0;
      var migrated = 0;
      var specDefaultsFixed = 0;
      var zones = getZones();
      zones.forEach(function(z) {
        if (typeof z.name !== 'string' || !z.name.trim()) { z.name = 'Zone'; fixed++; }
        if (typeof z.intensity !== 'string' && typeof z.intensity !== 'number') { z.intensity = '100'; fixed++; }
        if (!Array.isArray(z.colors)) { z.colors = []; fixed++; }
        if (!Array.isArray(z.patternStack)) { z.patternStack = []; fixed++; }
        if (!Array.isArray(z.specPatternStack)) { z.specPatternStack = []; fixed++; }
        if (z.pickerTolerance == null || isNaN(z.pickerTolerance)) { z.pickerTolerance = 40; fixed++; }
        if (z.pickerColor && !/^#[0-9A-Fa-f]{6}$/.test(z.pickerColor)) { z.pickerColor = '#3366ff'; fixed++; }
        if (typeof z.muted !== 'boolean') { z.muted = false; fixed++; }
        if (z.zoneSpecMapStrength == null || isNaN(Number(z.zoneSpecMapStrength))) { z.zoneSpecMapStrength = 100; fixed++; }
        if (!z.zoneSpecMapPath) {
          if (z.zoneSpecMapName != null) { z.zoneSpecMapName = null; fixed++; }
          if (z.zoneSpecMapResolution != null) { z.zoneSpecMapResolution = null; fixed++; }
        }
        migrated += _migrateZoneFinishIds(z);
        specDefaultsFixed += _normalizeLegacySpecPatternChannels(z);
      });
      if (fixed > 0 || migrated > 0 || specDefaultsFixed > 0) {
        renderZones();
        var parts = [];
        if (fixed > 0) parts.push('Repaired ' + fixed + ' zone fields');
        if (migrated > 0) parts.push('Migrated ' + migrated + ' legacy finish id(s)');
        if (specDefaultsFixed > 0) parts.push('Normalized ' + specDefaultsFixed + ' spec pattern channel default(s)');
        showToast(parts.join(' - '));
      }
      return fixed + migrated + specDefaultsFixed;
    }

    global._SPB_LEGACY_ID_MIGRATIONS = _SPB_LEGACY_ID_MIGRATIONS;
    global._migrateZoneFinishIds = _migrateZoneFinishIds;
    global._normalizeLegacySpecPatternChannels = _normalizeLegacySpecPatternChannels;
    global.repairZoneData = repairZoneData;

    setTimeout(function() {
      try {
        repairZoneData();
      } catch (e) {}
    }, 2000);
  }

  global.SPBZoneDataRepairControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
