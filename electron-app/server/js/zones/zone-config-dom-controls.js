(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var getCurrentSourcePaintFile = deps.getCurrentSourcePaintFile || function() { return ''; };
    var getImportedSpecMapPath = deps.getImportedSpecMapPath || function() { return null; };
    var setImportedSpecMapPath = deps.setImportedSpecMapPath || function() {};
    var getActiveSpecChannel = deps.getActiveSpecChannel || function() { return 'all'; };
    var updateWearDisplay = deps.updateWearDisplay || function() {};
    var toggleNightBoostSlider = deps.toggleNightBoostSlider || function() {};
    var updateOutputPath = deps.updateOutputPath || function() {};
    var setSpecChannel = deps.setSpecChannel || function() {};
    var escapeHtml = deps.escapeHtml || function(value) { return String(value == null ? '' : value); };

    function byId(id) {
      return doc && doc.getElementById ? doc.getElementById(id) : null;
    }

    function valueOf(id, fallback) {
      var el = byId(id);
      return el ? el.value : fallback;
    }

    function checkedOf(id) {
      var el = byId(id);
      return !!(el && el.checked);
    }

    function getConfigShell() {
      var canonicalSourcePaintFile = getCurrentSourcePaintFile() || valueOf('paintFile', '');
      return {
        version: '3.0',
        driverName: valueOf('driverName', ''),
        carName: valueOf('carName', ''),
        iracingId: valueOf('iracingId', ''),
        paintFile: valueOf('paintFile', ''),
        sourcePaintFile: canonicalSourcePaintFile,
        outputDir: valueOf('outputDir', ''),
        helmetFile: valueOf('helmetFile', ''),
        suitFile: valueOf('suitFile', ''),
        wearLevel: parseInt(valueOf('wearSlider', '0') || '0', 10),
        exportZip: checkedOf('exportZipCheckbox'),
        dualSpec: checkedOf('dualSpecCheckbox'),
        nightBoost: parseFloat(valueOf('nightBoostSlider', '0.7') || '0.7'),
        importedSpecMapPath: getImportedSpecMapPath() || null,
        activeSpecChannel: getActiveSpecChannel() || 'all'
      };
    }

    function setValue(id, value) {
      if (value === undefined) return;
      var el = byId(id);
      if (el) el.value = value;
    }

    function applyConfigShell(cfg) {
      cfg = cfg || {};
      setValue('driverName', cfg.driverName);
      setValue('carName', cfg.carName);
      setValue('iracingId', cfg.iracingId);
      setValue('paintFile', cfg.paintFile);
      setValue('outputDir', cfg.outputDir);
      setValue('helmetFile', cfg.helmetFile);
      setValue('suitFile', cfg.suitFile);
      if (cfg.wearLevel !== undefined && byId('wearSlider')) {
        byId('wearSlider').value = cfg.wearLevel;
        updateWearDisplay(cfg.wearLevel);
      }
      if (cfg.exportZip !== undefined && byId('exportZipCheckbox')) byId('exportZipCheckbox').checked = cfg.exportZip;
      if (cfg.dualSpec !== undefined && byId('dualSpecCheckbox')) {
        byId('dualSpecCheckbox').checked = cfg.dualSpec;
        toggleNightBoostSlider();
      }
      if (cfg.nightBoost !== undefined && byId('nightBoostSlider')) {
        byId('nightBoostSlider').value = cfg.nightBoost;
        if (byId('nightBoostVal')) byId('nightBoostVal').textContent = parseFloat(cfg.nightBoost).toFixed(2);
      }
      updateOutputPath();
    }

    function restoreSpecMapUi(cfg) {
      cfg = cfg || {};
      if (cfg.importedSpecMapPath) {
        setImportedSpecMapPath(cfg.importedSpecMapPath);
        var fname = cfg.importedSpecMapPath.split('/').pop().split('\\').pop();
        var status = byId('importSpecMapStatus');
        if (status) {
          status.innerHTML = '<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active - Layer 0</span> - ' + escapeHtml(fname);
        }
        var btn = byId('btnClearSpecMap');
        if (btn) btn.disabled = false;
        var specBanner = byId('specFromShokkBanner');
        var specLabel = byId('specFromShokkLabel');
        if (specBanner) {
          specBanner.style.display = 'block';
          if (specLabel) specLabel.textContent = fname + ' - zones paint on top. Render uses this spec.';
        }
      }
      if (cfg.activeSpecChannel && cfg.activeSpecChannel !== 'all') {
        setSpecChannel(cfg.activeSpecChannel);
      }
    }

    Object.assign(global, {
      _getConfigShell: getConfigShell,
      _applyConfigShell: applyConfigShell,
      _restoreConfigSpecMapUi: restoreSpecMapUi
    });

    return {
      getConfigShell: getConfigShell,
      applyConfigShell: applyConfigShell,
      restoreSpecMapUi: restoreSpecMapUi
    };
  }

  global.SPBZoneConfigDomControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
