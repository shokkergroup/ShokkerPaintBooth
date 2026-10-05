(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var autosaveKey = deps.autosaveKey || 'shokker_autosave';
    var getConfig = deps.getConfig || function () { return null; };
    var getDocument = deps.getDocument || function () { return global.document; };
    var getStorage = deps.getStorage || function () { return global.localStorage; };
    var showToast = deps.showToast || function () {};
    var consoleApi = deps.console || global.console || { warn: function () {} };
    var setTimeoutFn = deps.setTimeout || global.setTimeout;
    var clearTimeoutFn = deps.clearTimeout || global.clearTimeout;
    var setIntervalFn = deps.setInterval || global.setInterval;
    var autosaveTimer = null;
    var pendingChanges = 0;

    function writeConfigNow(silentQuota) {
      var cfg = getConfig();
      if (!cfg || !cfg.zones || cfg.zones.length === 0) return false;
      cfg._autosave_time = Date.now();
      var json = JSON.stringify(cfg);
      if (json.length > 4 * 1024 * 1024) {
        if (!silentQuota && consoleApi && typeof consoleApi.warn === 'function') {
          consoleApi.warn('[SPB] Auto-save payload too large (' + Math.round(json.length / 1024) + 'KB), skipping');
        }
        return false;
      }
      var storage = getStorage();
      if (!storage || typeof storage.setItem !== 'function') return false;
      storage.setItem(autosaveKey, json);
      return true;
    }

    function updateBadge() {
      var doc = getDocument();
      var badge = doc && typeof doc.getElementById === 'function' ? doc.getElementById('autosaveBadge') : null;
      if (!badge) return;
      badge.textContent = 'Auto-saved (' + pendingChanges + ' changes)';
      badge.style.opacity = '1';
      setTimeoutFn(function () { badge.style.opacity = '0.4'; }, 1500);
    }

    function autoSave() {
      pendingChanges++;
      if (autosaveTimer) clearTimeoutFn(autosaveTimer);
      autosaveTimer = setTimeoutFn(function () {
        try {
          if (writeConfigNow(false)) {
            updateBadge();
            pendingChanges = 0;
          }
        } catch (e) {
          if (e && e.name === 'QuotaExceededError') {
            showToast('Auto-save failed: localStorage full. Export your config to free space.', true);
          }
        }
      }, 500);
    }

    function flushAutoSave() {
      try {
        if (autosaveTimer) {
          clearTimeoutFn(autosaveTimer);
          autosaveTimer = null;
        }
        if (writeConfigNow(true)) pendingChanges = 0;
      } catch (_) {}
    }

    if (typeof setIntervalFn === 'function') {
      setIntervalFn(function () {
        try { writeConfigNow(true); } catch (_) {}
      }, 60000);
    }

    var api = {
      autosaveKey: autosaveKey,
      autoSave: autoSave,
      flushAutoSave: flushAutoSave,
      writeConfigNow: writeConfigNow
    };
    global.autoSave = autoSave;
    global.flushAutoSave = flushAutoSave;
    return api;
  }

  global.SPBZoneAutosaveControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
