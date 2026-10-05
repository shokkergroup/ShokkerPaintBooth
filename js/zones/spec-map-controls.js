'use strict';

(function () {
  function preview() {
    if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
  }

  function fileName(path) {
    return String(path || '').split('/').pop().split('\\').pop();
  }

  function setSpecStatus(text, html) {
    const status = document.getElementById('importSpecMapStatus');
    if (!status) return;
    if (html) status.innerHTML = html;
    else status.textContent = text;
  }

  function install(deps) {
    const getZones = deps.getZones;
    const pushZoneUndo = deps.pushZoneUndo;
    const renderZones = deps.renderZones || window.renderZones;
    const renderZoneDetail = deps.renderZoneDetail || window.renderZoneDetail;
    const showToast = deps.showToast || window.showToast;
    const openFilePicker = deps.openFilePicker || window.openFilePicker;
    const escapeHtml = deps.escapeHtml || (value => String(value == null ? '' : value));
    const getActiveImportedSpecMapPath = deps.getActiveImportedSpecMapPath || function getActiveSpec() {
      return window.importedSpecMapPath || null;
    };
    const setImportedSpecMapPath = deps.setImportedSpecMapPath || function setImportedSpec(path) {
      window.importedSpecMapPath = path;
    };
    window._getActiveImportedSpecMapPath = getActiveImportedSpecMapPath;

    function setGlobalSpec(path, name, resolution) {
      setImportedSpecMapPath(path);
      const size = Array.isArray(resolution) ? ` (${resolution[0]}x${resolution[1]})` : '';
      setSpecStatus('', `<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active &middot; Layer 0</span> - ${escapeHtml(name)}${size}`);
      const clearBtn = document.getElementById('btnClearSpecMap');
      if (clearBtn) clearBtn.disabled = false;
    }

    function uploadSpec(body, onSuccess, errorPrefix) {
      fetch('/upload-spec-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(30000),
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) onSuccess(data);
          else if (typeof showToast === 'function') showToast(errorPrefix + ': ' + (data.error || 'unknown'), true);
        })
        .catch(err => { if (typeof showToast === 'function') showToast(errorPrefix + ': ' + err, true); });
    }

    function setZoneSpecMap(index, path, meta) {
      if (index < 0 || index >= getZones().length) return;
      const zone = getZones()[index];
      const normalizedPath = path ? String(path).replace(/\\/g, '/') : null;
      zone.zoneSpecMapPath = normalizedPath;
      zone.zoneSpecMapName = meta && meta.name ? meta.name : (normalizedPath ? fileName(normalizedPath) : null);
      zone.zoneSpecMapResolution = meta && meta.resolution ? meta.resolution : null;
      if (zone.zoneSpecMapStrength == null) zone.zoneSpecMapStrength = 100;
      if (typeof renderZones === 'function') renderZones();
      if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
      preview();
    }

    window.importSpecMapFromFile = function importSpecMapFromFile() {
      let startPath = '';
      const currentPaint = document.getElementById('paintFile')?.value.trim() || '';
      if (currentPaint) startPath = currentPaint.replace(/[/\\][^/\\]+$/, '');
      openFilePicker({
        title: 'Select Spec Map TGA to Import',
        filter: '.tga',
        mode: 'file',
        startPath,
        onSelect(filePath) {
          if (!filePath) return;
          uploadSpec({ spec_path: filePath }, data => {
            setGlobalSpec(data.temp_path, fileName(filePath), data.resolution);
            if (typeof showToast === 'function') showToast('Spec map imported - Layer 0 active');
            preview();
          }, 'Failed to import spec map');
        },
      });
    };

    window.importSpecMapFromDrop = function importSpecMapFromDrop(file) {
      const reader = new FileReader();
      reader.onload = function onSpecDropLoad(e) {
        uploadSpec({ spec_data: e.target.result }, data => {
          setGlobalSpec(data.temp_path, file.name, data.resolution);
          if (typeof showToast === 'function') showToast('Spec map imported - Layer 0 active');
          preview();
        }, 'Failed to import spec map');
      };
      reader.readAsDataURL(file);
    };

    function clearImportedSpecMap() {
      if (!getActiveImportedSpecMapPath()) {
        if (typeof showToast === 'function') showToast('Nothing to clear - no spec map is loaded');
        return;
      }
      if (typeof confirm === 'function' &&
          !confirm('Clear the imported spec map? You will need to re-import or re-load from SHOKK to restore it.')) {
        return;
      }
      setImportedSpecMapPath(null);
      setSpecStatus('No spec map - zones render on default base');
      const clearBtn = document.getElementById('btnClearSpecMap');
      if (clearBtn) clearBtn.disabled = true;
      const specBanner = document.getElementById('specFromShokkBanner');
      if (specBanner) specBanner.style.display = 'none';
      const specChip = document.getElementById('shokkSpecStateChip');
      if (specChip) {
        specChip.textContent = 'SPEC: none';
        specChip.style.color = 'var(--text-dim)';
        specChip.style.borderColor = 'var(--border)';
        specChip.style.background = 'rgba(255,255,255,0.03)';
      }
      if (typeof renderZones === 'function') renderZones();
      if (typeof showToast === 'function') showToast('Spec cleared - zones render on default base');
      preview();
    }
    window.clearImportedSpecMap = clearImportedSpecMap;
    window.clearImportedSpec = clearImportedSpecMap;

    window.importZoneSpecMapFromFile = function importZoneSpecMapFromFile(index) {
      if (index < 0 || index >= getZones().length) return;
      let startPath = '';
      const currentPaint = document.getElementById('paintFile')?.value.trim() || '';
      if (currentPaint) startPath = currentPaint.replace(/[/\\][^/\\]+$/, '');
      openFilePicker({
        title: 'Select Spec Map for Zone',
        filter: '.tga',
        mode: 'file',
        startPath,
        onSelect(filePath) {
          if (!filePath) return;
          uploadSpec({ spec_path: filePath }, data => {
            pushZoneUndo('Import zone spec source');
            setZoneSpecMap(index, data.temp_path, { name: fileName(filePath), resolution: data.resolution || null });
            if (typeof showToast === 'function') showToast('Zone spec source imported');
          }, 'Failed to import zone spec source');
        },
      });
    };

    window.copyImportedSpecMapToZone = function copyImportedSpecMapToZone(index) {
      if (index < 0 || index >= getZones().length) return;
      const activeSpecPath = getActiveImportedSpecMapPath();
      if (!activeSpecPath) {
        if (typeof showToast === 'function') showToast('No Layer 0 imported spec map is active', true);
        return;
      }
      pushZoneUndo('Use Layer 0 spec on zone');
      setZoneSpecMap(index, activeSpecPath, { name: fileName(activeSpecPath), resolution: null });
      if (typeof showToast === 'function') showToast('Layer 0 spec assigned to zone');
    };

    window.clearZoneSpecMap = function clearZoneSpecMap(index) {
      const zone = getZones()[index];
      if (!zone) return;
      if (!zone.zoneSpecMapPath) {
        if (typeof showToast === 'function') showToast('No zone spec source to clear');
        return;
      }
      pushZoneUndo('Clear zone spec source');
      zone.zoneSpecMapPath = null;
      zone.zoneSpecMapName = null;
      zone.zoneSpecMapResolution = null;
      zone.zoneSpecMapStrength = 100;
      if (typeof renderZones === 'function') renderZones();
      if (typeof renderZoneDetail === 'function') renderZoneDetail(index);
      preview();
      if (typeof showToast === 'function') showToast('Zone spec source cleared');
    };

    window.setZoneSpecMapStrength = function setZoneSpecMapStrength(index, val) {
      const zone = getZones()[index];
      if (!zone) return;
      const pct = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
      pushZoneUndo('Set zone spec source strength', true);
      zone.zoneSpecMapStrength = pct;
      const el = document.getElementById('detZoneSpecMapStrengthVal' + index);
      if (el) el.textContent = pct + '%';
      preview();
    };

    window.stepZoneSpecMapStrength = function stepZoneSpecMapStrength(index, delta) {
      const zone = getZones()[index];
      if (!zone) return;
      const cur = Math.round(Number(zone.zoneSpecMapStrength ?? 100));
      window.setZoneSpecMapStrength(index, Math.max(0, Math.min(100, cur + delta * 5)));
    };
  }

  window.SPBZoneSpecMapControls = { install };
})();
