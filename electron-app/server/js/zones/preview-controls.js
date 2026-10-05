(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = global.document;
    if (!doc) return;
    var showToast = deps.showToast || function() {};
    var validatePaintPath = deps.validatePaintPath || function() {};
    var isTextEntryTarget = deps.isTextEntryTarget || function(target) {
      var tag = target && target.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };

    var RECENT_PATHS_KEY = 'shokker_recent_paths';
    var MAX_RECENT_PATHS = 8;
    var specExpanded = false;
    var activeSpecChannel = global.activeSpecChannel || 'all';
    var specMapInspectorChannel = 'all';
    var specMapInspectorImageData = null;
    var beforeAfterActive = !!global.beforeAfterActive;
    var beforeImageCaptured = !!global.beforeImageCaptured;

    function syncPreviewGlobals() {
      global.activeSpecChannel = activeSpecChannel;
      global.beforeAfterActive = beforeAfterActive;
      global.beforeImageCaptured = beforeImageCaptured;
    }

    function getRecentPaths() {
      try {
        return JSON.parse(global.localStorage.getItem(RECENT_PATHS_KEY) || '[]');
      } catch (e) {
        return [];
      }
    }

    function addRecentPath(path) {
      if (!path) return;
      var paths = getRecentPaths().filter(function(p) { return p.toLowerCase() !== path.toLowerCase(); });
      paths.unshift(path);
      if (paths.length > MAX_RECENT_PATHS) paths = paths.slice(0, MAX_RECENT_PATHS);
      global.localStorage.setItem(RECENT_PATHS_KEY, JSON.stringify(paths));
    }

    function showRecentPaths() {
      var paths = getRecentPaths();
      var dropdown = doc.getElementById('recentPathsDropdown');
      var paintFile = doc.getElementById('paintFile');
      var currentVal = paintFile ? paintFile.value.trim() : '';
      if (!dropdown || paths.length === 0) { if (dropdown) dropdown.style.display = 'none'; return; }
      var filtered = paths.filter(function(p) { return p.toLowerCase() !== currentVal.toLowerCase(); });
      if (filtered.length === 0) { dropdown.style.display = 'none'; return; }
      dropdown.innerHTML = filtered.map(function(p) {
        var shortName = p.split(/[/\\]/).pop();
        var folder = p.split(/[/\\]/).slice(-2, -1)[0] || '';
        var safePath = p.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        return '<div class="recent-path-item" onmousedown="selectRecentPath(\'' + safePath + '\')" title="' + p + '">' + (folder ? folder + '/' : '') + shortName + '</div>';
      }).join('');
      dropdown.style.display = '';
    }

    function hideRecentPaths() {
      var dropdown = doc.getElementById('recentPathsDropdown');
      if (dropdown) dropdown.style.display = 'none';
    }

    function selectRecentPath(path) {
      var paintFile = doc.getElementById('paintFile');
      if (paintFile) paintFile.value = path;
      hideRecentPaths();
      validatePaintPath();
    }

    function toggleSpecInset() {
      var specPane = doc.getElementById('previewSpecPane');
      var paintPane = doc.getElementById('previewPaintPane');
      if (!specPane || !paintPane) return;
      specExpanded = !specExpanded;
      specPane.classList.toggle('spec-expanded', specExpanded);
      paintPane.style.display = specExpanded ? 'none' : '';
    }

    function setSpecChannel(ch) {
      activeSpecChannel = ch || 'all';
      syncPreviewGlobals();
      doc.querySelectorAll('.spec-channel-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.ch === activeSpecChannel);
      });
      var labels = { all: 'SPEC MAP', r: 'METALLIC (R)', g: 'ROUGHNESS (G)', b: 'CLEARCOAT (B)', a: 'SPEC MASK (A)' };
      var label = doc.querySelector('#previewSpecPane .preview-dual-label');
      if (label) label.textContent = labels[activeSpecChannel] || 'SPEC MAP';
      renderSpecChannel();
    }

    function renderSpecChannel() {
      var img = doc.getElementById('livePreviewSpecImg');
      var canvas = doc.getElementById('specChannelCanvas');
      if (!img || !canvas || !img.src || !img.naturalWidth) return;
      if (activeSpecChannel === 'all') {
        img.style.display = '';
        canvas.style.display = 'none';
        return;
      }
      var w = img.naturalWidth;
      var h = img.naturalHeight;
      canvas.width = w;
      canvas.height = h;
      var ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(img, 0, 0, w, h);
      var imageData = ctx.getImageData(0, 0, w, h);
      var d = imageData.data;
      var chIndex = { r: 0, g: 1, b: 2, a: 3 }[activeSpecChannel];
      var tint = ({ r: [1.0, 0.3, 0.3], g: [0.3, 1.0, 0.3], b: [0.3, 0.5, 1.0], a: [1.0, 0.7, 0.3] }[activeSpecChannel]) || [1, 1, 1];
      for (var i = 0; i < d.length; i += 4) {
        var val = d[i + chIndex];
        d[i] = Math.min(255, Math.round(val * tint[0]));
        d[i + 1] = Math.min(255, Math.round(val * tint[1]));
        d[i + 2] = Math.min(255, Math.round(val * tint[2]));
        d[i + 3] = 255;
      }
      ctx.putImageData(imageData, 0, 0);
      img.style.display = 'none';
      canvas.style.display = '';
    }

    // Photoshop "Show Channels in Color" semantics — keep in lockstep with SPEC_DOCK_TINTS in
    // paint-booth-2-state-zones.js (the active dock renderer). Owner mandate 2026-06-07: dock
    // must match Photoshop channel colors; brightness = literal authored value.
    var SPEC_DOCK_TINTS = { r: [1.0, 0.0, 0.0], g: [0.0, 1.0, 0.0], b: [0.0, 0.0, 1.0] };
    // SPB-SIMPLIFY-2026-07-18b (owner): full-width dock cells — render at 192px for crispness.
    var SPEC_DOCK_THUMB = 192;

    function renderSpecChannelDock() {
      var img = doc.getElementById('livePreviewSpecImg');
      var dock = doc.getElementById('specChannelDock');
      if (!dock) return;
      if (!img || !img.src) {
        dock.style.display = 'none';
        return;
      }
      if (!img.naturalWidth) return;
      dock.style.display = '';

      // [SPB-SPECDOCK-SPEED 2026-08-24, owner: "spec sliders don't update the
      // combined/metal/rough/coat previews"] This used to read the spec at FULL
      // resolution (getImageData over ~1M px) and then run three separate
      // per-pixel loops over all 4M bytes before scaling each result down to a
      // 192px thumb. That cost is why the dock got parked behind the pure-idle
      // overlay pass — which during continuous slider tweaking never fires,
      // so the strip froze exactly when the painter was watching it.
      //
      // Point-sample to thumb size FIRST, then extract channels from ~36k px
      // instead of ~1M: same values (smoothing is OFF, so we are sampling real
      // pixels, never blending them — a blended downscale would invent channel
      // values that exist in no TGA), ~28x less work, cheap enough to run on
      // every preview without waiting for idle.
      var t = SPEC_DOCK_THUMB;
      var srcCanvas = doc.createElement('canvas');
      srcCanvas.width = t;
      srcCanvas.height = t;
      var srcCtx = srcCanvas.getContext('2d', { willReadFrequently: true });
      srcCtx.imageSmoothingEnabled = false;
      srcCtx.drawImage(img, 0, 0, t, t);
      var srcData = srcCtx.getImageData(0, 0, t, t);

      doc.querySelectorAll('.spec-channel-dock-cell').forEach(function(cell) {
        var ch = cell.dataset.ch || 'all';
        var canvas = cell.querySelector('.spec-channel-dock-canvas');
        if (!canvas) return;
        canvas.width = t;
        canvas.height = t;
        var ctx = canvas.getContext('2d');
        if (ch === 'all') {
          ctx.imageSmoothingEnabled = false;
          ctx.drawImage(img, 0, 0, t, t);
          return;
        }
        var chIndex = { r: 0, g: 1, b: 2 }[ch];
        var tint = SPEC_DOCK_TINTS[ch];
        if (chIndex === undefined || !tint) return;
        var out = ctx.createImageData(t, t);
        var d = srcData.data;
        var od = out.data;
        for (var i = 0; i < d.length; i += 4) {
          var val = d[i + chIndex];
          od[i] = Math.min(255, Math.round(val * tint[0]));
          od[i + 1] = Math.min(255, Math.round(val * tint[1]));
          od[i + 2] = Math.min(255, Math.round(val * tint[2]));
          od[i + 3] = 255;
        }
        ctx.putImageData(out, 0, 0);
      });
    }

    function hookSpecImageLoad() {
      var img = doc.getElementById('livePreviewSpecImg');
      if (!img || img.dataset.spbSpecChannelHooked === '1') return;
      img.dataset.spbSpecChannelHooked = '1';
      img.addEventListener('load', function() {
        if (activeSpecChannel !== 'all') renderSpecChannel();
        renderSpecChannelDock();
      });
    }

    function openSpecMapInspector() {
      var modal = doc.getElementById('specMapInspectorModal');
      var noData = doc.getElementById('specMapInspectorNoData');
      var content = doc.getElementById('specMapInspectorContent');
      var hint = doc.getElementById('specMapInspectorHint');
      if (!modal || !noData || !content || !hint) return;
      var specImg = doc.getElementById('livePreviewSpecImg');
      // SPB-93 09-08: full renders publish loaded PNG URLs, not only data URLs.
    if (!specImg || !specImg.src || !specImg.complete || !(specImg.naturalWidth > 0) || !(specImg.naturalHeight > 0)) {
        noData.style.display = '';
        content.style.display = 'none';
        hint.textContent = 'No spec map yet. Switch to CAR or SPLIT view, configure zones, and wait for the preview to render. Then open this again to see each channel and values.';
      } else {
        noData.style.display = 'none';
        content.style.display = '';
        hint.textContent = 'R=Metallic, G=Roughness, B=Clearcoat, A=Spec mask. Click any UV point to read or transfer its exact material values.';
        var inspectorImg = doc.getElementById('specMapInspectorImg');
        if (inspectorImg) inspectorImg.src = specImg.src;
        if (inspectorImg && inspectorImg.complete && inspectorImg.naturalWidth > 0) {
          refreshSpecMapInspectorData(inspectorImg);
        } else if (inspectorImg) {
          inspectorImg.onload = function() { refreshSpecMapInspectorData(inspectorImg); };
        }
      }
      modal.style.display = 'flex';
    }

    function closeSpecMapInspector() {
      var modal = doc.getElementById('specMapInspectorModal');
      if (modal) modal.style.display = 'none';
    }

    function setSpecMapInspectorChannel(ch) {
      specMapInspectorChannel = ch || 'all';
      doc.querySelectorAll('#specMapInspectorContent .spec-channel-btn').forEach(function(b) {
        b.classList.toggle('active', (b.dataset.ch || '') === specMapInspectorChannel);
      });
      renderSpecMapInspectorChannel();
    }

    async function refreshSpecMapInspectorData(img) {
        if (!img || img.naturalWidth === 0) return;
        const source = img.currentSrc || img.src;
        specMapInspectorImageData = null;
        if (typeof global.resetSpecMaterialSampleDisplay === 'function') global.resetSpecMaterialSampleDisplay();
        const hint = doc.getElementById('specMapInspectorHint');
        if (hint) hint.textContent = 'Loading exact material values…';
        try {
            const pixels = await global.SPBSpecPngPixels.load(source);
            if ((img.currentSrc || img.src) !== source) return;
            specMapInspectorImageData = pixels;
            updateSpecMapInspectorValues();
            renderSpecMapInspectorChannel();
            if (hint) hint.textContent = 'R=Metallic, G=Roughness, B=Clearcoat, A=Lighting. Click the map to read its exact stored material values.';
        } catch (error) {
            if ((img.currentSrc || img.src) === source && hint) hint.textContent = 'Could not read exact material values: ' + error.message;
        }
    }

    function updateSpecMapInspectorValues() {
      var d = specMapInspectorImageData ? specMapInspectorImageData.data : null;
      if (!d) return;
      var n = d.length >> 2;
      var mins = [255, 255, 255, 255];
      var maxs = [0, 0, 0, 0];
      var sums = [0, 0, 0, 0];
      for (var i = 0; i < d.length; i += 4) {
        for (var ch = 0; ch < 4; ch++) {
          var v = d[i + ch];
          if (v < mins[ch]) mins[ch] = v;
          if (v > maxs[ch]) maxs[ch] = v;
          sums[ch] += v;
        }
      }
      var ids = ['specValRMin', 'specValRMax', 'specValRMean', 'specValGMin', 'specValGMax', 'specValGMean', 'specValBMin', 'specValBMax', 'specValBMean', 'specValAMin', 'specValAMax', 'specValAMean'];
      var vals = [mins[0], maxs[0], Math.round(sums[0] / n), mins[1], maxs[1], Math.round(sums[1] / n), mins[2], maxs[2], Math.round(sums[2] / n), mins[3], maxs[3], Math.round(sums[3] / n)];
      ids.forEach(function(id, i) { var el = doc.getElementById(id); if (el) el.textContent = vals[i]; });
    }

    function renderSpecMapInspectorChannel() {
      var img = doc.getElementById('specMapInspectorImg');
      var canvas = doc.getElementById('specMapInspectorCanvas');
      if (!img || !canvas) return;
      if (specMapInspectorChannel === 'all' || !specMapInspectorImageData) {
        img.style.display = '';
        canvas.style.display = 'none';
        return;
      }
      var d = specMapInspectorImageData.data;
      var w = specMapInspectorImageData.width;
      var h = specMapInspectorImageData.height;
      canvas.width = w;
      canvas.height = h;
      var ctx = canvas.getContext('2d');
      var chIndex = { r: 0, g: 1, b: 2, a: 3 }[specMapInspectorChannel];
      var tint = ({ r: [1, 0.3, 0.3], g: [0.3, 1, 0.3], b: [0.3, 0.5, 1], a: [1, 0.7, 0.3] }[specMapInspectorChannel]) || [1, 1, 1];
      var out = ctx.createImageData(w, h);
      for (var i = 0; i < d.length; i += 4) {
        var v = d[i + chIndex];
        out.data[i] = Math.min(255, Math.round(v * tint[0]));
        out.data[i + 1] = Math.min(255, Math.round(v * tint[1]));
        out.data[i + 2] = Math.min(255, Math.round(v * tint[2]));
        out.data[i + 3] = 255;
      }
      ctx.putImageData(out, 0, 0);
      img.style.display = 'none';
      canvas.style.display = 'block';
    }

    function captureBeforeImage(srcOverride) {
      var livePreviewImg = doc.getElementById('livePreviewImg');
      var nextSrc = srcOverride || (livePreviewImg && livePreviewImg.src) || '';
      if (!nextSrc) return;
      var beforeImg = doc.getElementById('beforePreviewImg');
      if (!beforeImg) return;
      beforeImg.src = nextSrc;
      beforeImageCaptured = true;
      syncPreviewGlobals();
      if (typeof global.updatePreviewControlAvailability === 'function') global.updatePreviewControlAvailability();
    }

    function toggleBeforeAfter() {
      // 2026-05-30 owner UI fix: redundant "BEFORE (Original Paint)" pane removed (left SOURCE box
      // already shows the original). No-op so the legacy 'b' shortcut/buttons can't show it.
    }

    doc.addEventListener('keydown', function(e) {
      if (e.defaultPrevented) return;
      if (e.key === 'b' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.repeat) {
        if (isTextEntryTarget(e.target)) return;
        if (beforeImageCaptured && !beforeAfterActive) toggleBeforeAfter();
      }
    });
    doc.addEventListener('keyup', function(e) {
      if (e.key === 'b' && beforeAfterActive) toggleBeforeAfter();
    });

    global.getRecentPaths = getRecentPaths;
    global.addRecentPath = addRecentPath;
    global.showRecentPaths = showRecentPaths;
    global.hideRecentPaths = hideRecentPaths;
    global.selectRecentPath = selectRecentPath;
    global.toggleSpecInset = toggleSpecInset;
    global.setSpecChannel = setSpecChannel;
    global.renderSpecChannel = renderSpecChannel;
    global.renderSpecChannelDock = renderSpecChannelDock;
    global.openSpecMapInspector = openSpecMapInspector;
    global.closeSpecMapInspector = closeSpecMapInspector;
    global.setSpecMapInspectorChannel = setSpecMapInspectorChannel;
    global.refreshSpecMapInspectorData = refreshSpecMapInspectorData;
    global.getSpecMapInspectorImageData = function() { return specMapInspectorImageData; };
    global.updateSpecMapInspectorValues = updateSpecMapInspectorValues;
    global.renderSpecMapInspectorChannel = renderSpecMapInspectorChannel;
    global.captureBeforeImage = captureBeforeImage;
    global.toggleBeforeAfter = toggleBeforeAfter;
    syncPreviewGlobals();

    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', hookSpecImageLoad);
    } else {
      hookSpecImageLoad();
    }
  }

  global.SPBZonePreviewControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
