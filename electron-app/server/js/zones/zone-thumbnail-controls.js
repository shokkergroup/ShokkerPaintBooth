(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var storage = deps.localStorage || global.localStorage;
    var fetchFn = deps.fetch || global.fetch;
    var getApiBase = deps.getApiBase || function () { return 'http://localhost:' + ((global && global._SHOKKER_PORT) || 59876); };
    var getZones = deps.getZones || function () { return []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return -1; };
    var renderZones = deps.renderZones || function () {};
    var renderZoneDetail = deps.renderZoneDetail || function () {};
    var installLazyLoader = deps.installLazyLoader || function () {};
    var showToast = deps.showToast || function () {};

    async function refreshThumbnails() {
      var base = getApiBase();
      var serverCacheCleared = false;
      try {
        var clearResponse = await fetchFn(base + '/api/clear-cache', {
          method: 'POST',
          mode: 'cors',
          signal: AbortSignal.timeout(8000)
        });
        if (!clearResponse || !clearResponse.ok) {
          throw new Error('Server cache clear failed' + (clearResponse ? ' (HTTP ' + clearResponse.status + ')' : ''));
        }
        serverCacheCleared = true;
      } catch (e) {}

      var newV = Date.now();
      if (global) global._SHOKKER_SWATCH_V = String(newV);
      try { if (storage) storage.setItem('spb_swatch_cache_version', String(newV)); } catch (e) {}

      try {
        doc.querySelectorAll('img[src*="/api/swatch/"], img[data-swatch-url*="/api/swatch/"]').forEach(function (img) {
          var currentUrl = img.getAttribute('data-swatch-url') || img.getAttribute('src') || '';
          if (!currentUrl) return;
          var u = currentUrl.replace(/\bv=\d+\b/, 'v=' + newV);
          if (u.indexOf('nocache=') === -1) u += (u.indexOf('?') >= 0 ? '&' : '?') + 'nocache=1';
          if (img.getAttribute('data-swatch-url')) img.setAttribute('data-swatch-url', u);
          if (img.getAttribute('src')) img.src = u;
        });
      } catch (e) {}

      installLazyLoader();
      renderZones();
      var selectedZoneIndex = getSelectedZoneIndex();
      if (selectedZoneIndex >= 0 && selectedZoneIndex < getZones().length) renderZoneDetail(selectedZoneIndex);
      showToast(
        serverCacheCleared
          ? 'Thumbnails refreshed - cache cleared. Swatches will reload.'
          : 'Browser thumbnails refreshed, but the server cache could not be cleared.',
        !serverCacheCleared
      );
      checkThumbnailStatus();
    }

    async function checkThumbnailStatus() {
      var banner = doc && doc.getElementById ? doc.getElementById('thumbnailWarningBanner') : null;
      if (banner) banner.style.display = 'none';
    }

    global.refreshThumbnails = refreshThumbnails;
    global.checkThumbnailStatus = checkThumbnailStatus;
  }

  global.SPBZoneThumbnailControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
