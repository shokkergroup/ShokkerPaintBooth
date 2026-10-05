(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getDocument = deps.getDocument || function () { return global.document; };
    var getStorage = deps.getStorage || function () { return global.localStorage; };
    var getAutosaveKey = deps.getAutosaveKey || function () { return 'spb_autosave'; };
    var getApiBase = deps.getApiBase || function () { return (global.ShokkerAPI && global.ShokkerAPI.baseUrl) ? global.ShokkerAPI.baseUrl : ''; };
    var fetchFn = deps.fetch || global.fetch;
    var setTimer = deps.setTimeout || global.setTimeout;
    var loadConfigFromObj = deps.loadConfigFromObj || global.loadConfigFromObj;
    var validatePaintPath = deps.validatePaintPath || global.validatePaintPath || function () {};
    var showToast = deps.showToast || global.showToast || function () {};
    var importPSDFromPath = deps.importPSDFromPath || function (path) { return global.importPSDFromPath && global.importPSDFromPath(path); };
    var loadPaintPreviewFromServer = deps.loadPaintPreviewFromServer || function (path) { return global.loadPaintPreviewFromServer && global.loadPaintPreviewFromServer(path); };
    var loadPaintImageFromPath = deps.loadPaintImageFromPath || function (path) { return global.loadPaintImageFromPath && global.loadPaintImageFromPath(path); };

    var SPB_LAST_FILE_KEY = 'spb_last_paint_file';
    var defaultAssetsPromise = null;

    function storage() {
      return getStorage();
    }

    function readStoredLastFile() {
      try {
        return (storage().getItem(SPB_LAST_FILE_KEY) || '').trim();
      } catch (e) {
        return '';
      }
    }

    function uniqueNonEmpty(items) {
      var out = [];
      var seen = new Set();
      items.forEach(function (item) {
        var value = (typeof item === 'string') ? item.trim() : '';
        if (!value || seen.has(value)) return;
        seen.add(value);
        out.push(value);
      });
      return out;
    }

    function getPreferredRestoreCandidates(cfg) {
      var cfgSource = (cfg && typeof cfg.sourcePaintFile === 'string') ? cfg.sourcePaintFile.trim() : '';
      var storedLastFile = readStoredLastFile();
      var uiPaintFile = (cfg && typeof cfg.paintFile === 'string') ? cfg.paintFile.trim() : '';
      return uniqueNonEmpty([cfgSource, storedLastFile, uiPaintFile]);
    }

    function getPreferredRestorePaintFile(cfg) {
      var candidates = getPreferredRestoreCandidates(cfg);
      return candidates[0] || '';
    }

    async function fetchDefaultAssets() {
      if (defaultAssetsPromise) return defaultAssetsPromise;
      defaultAssetsPromise = fetchFn(getApiBase() + '/api/default-assets', { cache: 'no-store', signal: AbortSignal.timeout(8000) })
        .then(async function (res) {
          var data = await res.json().catch(function () { return {}; });
          if (!res.ok || data.ok === false) throw new Error(data.error || ('default assets unavailable: ' + res.status));
          return data.assets || {};
        })
        .catch(function (e) {
          if (global.console && console.warn) console.warn('[autoRestore] default asset lookup failed:', e);
          return {};
        });
      return defaultAssetsPromise;
    }

    async function checkLocalPaintFile(path) {
      var normalizedPath = (path || '').trim();
      if (!normalizedPath) return false;
      try {
        var res = await fetchFn(getApiBase() + '/check-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: normalizedPath }),
          signal: AbortSignal.timeout(8000)
        });
        if (!res.ok) return false;
        var data = await res.json();
        return !!data.is_file;
      } catch (e) {
        if (global.console && console.warn) console.warn('[autoRestore] paint-file check failed:', e);
        return false;
      }
    }

    async function resolveRestorePaintFile(cfg) {
      var candidates = getPreferredRestoreCandidates(cfg);
      for (var i = 0; i < candidates.length; i += 1) {
        if (await checkLocalPaintFile(candidates[i])) return candidates[i];
        if (global.console && console.warn) console.warn('[autoRestore] saved paint file missing, trying fallback:', candidates[i]);
      }
      var assets = await fetchDefaultAssets();
      if (assets.starter_psd && await checkLocalPaintFile(assets.starter_psd)) return assets.starter_psd;
      return assets.starter_psd || candidates[0] || '';
    }

    function setPaintHeaderPath(path) {
      var doc = getDocument();
      var pathField = doc && doc.getElementById && doc.getElementById('paintFile');
      if (pathField && path) pathField.value = path;
    }

    function autoLoadPaintFile(filePath) {
      if (!filePath) return false;
      var ext = (filePath.split('.').pop() || '').toLowerCase();
      // SPB-93: keep delegated startup routing aligned with Open Layered.
      if (['psd', 'ora', 'xcf'].includes(ext)) {
        try { if (importPSDFromPath(filePath)) return true; } catch (e) {}
        return false;
      }
      try { if (loadPaintPreviewFromServer(filePath)) return true; } catch (e) {}
      try { if (loadPaintImageFromPath(filePath)) return true; } catch (e) {}
      return false;
    }

    function restorePaintFile(path) {
      var normalizedPath = (path || '').trim();
      if (!normalizedPath) return false;
      setPaintHeaderPath(normalizedPath);
      validatePaintPath();
      var ok = autoLoadPaintFile(normalizedPath);
      if (ok) {
        try { storage().setItem(SPB_LAST_FILE_KEY, normalizedPath); } catch (e) {}
      }
      return ok;
    }

    async function restorePreferredPaintFile(cfg, opts) {
      var options = opts || {};
      var path = await resolveRestorePaintFile(cfg);
      if (!path) {
        if (options.firstRun) showToast('Welcome - click Import PSD or Load TGA to get started', false);
        return false;
      }
      setPaintHeaderPath(path);
      var ok = restorePaintFile(path);
      if (options.firstRun) {
        showToast(ok ? 'First launch - loading default: ' + path.split(/[/\\]/).pop() : 'Welcome - click Import PSD or Load TGA to get started', false);
      }
      return ok;
    }

    function autoRestore() {
      try {
        var raw = storage().getItem(getAutosaveKey());
        if (!raw) {
          setTimer(function () { restorePreferredPaintFile(null, { firstRun: true }); }, 1500);
          return false;
        }
        var cfg = JSON.parse(raw);
        if (!cfg || !cfg.zones || cfg.zones.length === 0) {
          setTimer(function () { restorePreferredPaintFile(cfg); }, 1500);
          return false;
        }
        if (typeof loadConfigFromObj === 'function') loadConfigFromObj(cfg);
        var age = cfg._autosave_time ? Math.round((Date.now() - cfg._autosave_time) / 1000) : 0;
        var ageStr = age < 60 ? age + 's ago' : (age < 3600 ? Math.round(age / 60) + 'm ago' : Math.round(age / 3600) + 'h ago');
        showToast('Session restored (saved ' + ageStr + ') - ' + cfg.zones.length + ' zones, ' + (cfg.driverName || 'no driver') + ' - reloading paint...');
        setTimer(function () { restorePreferredPaintFile(cfg); }, 1500);
        return true;
      } catch (e) {
        if (global.console && console.warn) console.warn('[autoRestore] failed:', e);
        return false;
      }
    }

    Object.assign(global, {
      _spbFetchDefaultAssets: fetchDefaultAssets,
      _spbAutoLoadPaintFile: autoLoadPaintFile,
      autoRestore: autoRestore
    });
  }

  global.SPBZoneAutoRestoreControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
