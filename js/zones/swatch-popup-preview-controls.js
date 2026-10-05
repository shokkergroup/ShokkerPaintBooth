(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var showToast = deps.showToast || function() {};
    var getFinishType = deps.getFinishType || function(id) {
      return typeof global.getFinishType === 'function' ? global.getFinishType(id) : 'base';
    };
    var getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
    var getBases = deps.getBases || function() { return global.BASES || []; };
    var getServerBase = deps.getServerBase || function() {
      return (typeof global.ShokkerAPI !== 'undefined' && global.ShokkerAPI.baseUrl)
        ? global.ShokkerAPI.baseUrl
        : 'http://localhost:' + (global._SHOKKER_PORT || 59876);
    };

    var swatchPopupObserver = null;
    var hydrateFrame = null;
    var swatchPreviewState = { finishType: null, finishId: null, label: '' };

    function _disconnectSwatchPopupLazyLoader() {
      if (swatchPopupObserver) {
        try { swatchPopupObserver.disconnect(); } catch (_) {}
        swatchPopupObserver = null;
      }
    }

    function _hydrateDeferredSwatchImage(img) {
      if (!img || img.dataset.swatchLoaded === '1') return;
      var url = img.getAttribute('data-swatch-url');
      if (!url) return;
      img.dataset.swatchLoaded = '1';
      // Swatch PNGs are pre-warmed on disk (rebuild_picker_swatches.py --warm-cache)
      // and served immutable, so the thumbnail is a guaranteed instant cache HIT.
      // Load eagerly + decode sync so it is present on open instead of streaming in.
      img.loading = 'eager';
      img.decoding = 'sync';
      img.src = url;
    }

    function _scrollSwatchPickerToSelection() {
      var grid = document.getElementById('swatchPopupGrid');
      if (!grid) return;
      var selected = grid.querySelector('.swatch-item.selected');
      if (!selected) return;
      var group = selected.closest('.swatch-group');
      if (group && group.classList.contains('collapsed')) {
        group.classList.remove('collapsed');
      }
      requestAnimationFrame(function() {
        try {
          selected.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
        } catch (_) {
          selected.scrollIntoView(true);
        }
      });
    }

    function _installSwatchPopupLazyLoader() {
      var grid = document.getElementById('swatchPopupGrid');
      if (!grid) return;
      var imgs = Array.prototype.slice.call(grid.querySelectorAll('img.deferred-swatch[data-swatch-url]'));
      _disconnectSwatchPopupLazyLoader();
      if (imgs.length === 0) return;

      var visibleImgs = imgs.filter(function(img) {
        var item = img.closest('.swatch-item');
        var group = img.closest('.swatch-group');
        return (!item || item.style.display !== 'none') &&
          (!group || !group.classList.contains('collapsed')) && img.getClientRects().length > 0;
      });
      // Cache is pre-warmed, so hydrate EVERY visible thumbnail immediately instead
      // of streaming the first 24 + IntersectionObserver-on-scroll. This makes the
      // whole grid present on open with no fade/lazy-in. Each src is an instant
      // disk-cache HIT so this does not stall paint or block scrolling.
      // Atlas collapses/reorders the grid AFTER the stock open call. Hydrate
      // its final visible category, never thousands of hidden cards at once.
      if (hydrateFrame !== null) global.cancelAnimationFrame(hydrateFrame);
      hydrateFrame = global.requestAnimationFrame(function() {
        hydrateFrame = null;
        imgs.forEach(function(img) {
          var group = img.closest('.swatch-group');
          if ((!group || !group.classList.contains('collapsed')) && img.getClientRects().length) {
            _hydrateDeferredSwatchImage(img);
          }
        });
      });

      // Safety net only: any thumbnail still deferred (e.g. inside a collapsed
      // group that is expanded later, or revealed by a search filter) hydrates the
      // moment it scrolls into view. Already-hydrated images are never re-observed.
      var deferredImgs = visibleImgs.filter(function(img) { return img.dataset.swatchLoaded !== '1'; });
      if (deferredImgs.length === 0) return;

      if (typeof global.IntersectionObserver !== 'function') {
        deferredImgs.forEach(_hydrateDeferredSwatchImage);
        return;
      }

      swatchPopupObserver = new global.IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (!entry.isIntersecting) return;
          _hydrateDeferredSwatchImage(entry.target);
          try { swatchPopupObserver && swatchPopupObserver.unobserve(entry.target); } catch (_) {}
        });
      }, { root: grid, rootMargin: '240px 0px' });

      deferredImgs.forEach(function(img) {
        if (img.dataset.swatchLoaded === '1') return;
        swatchPopupObserver.observe(img);
      });
    }

    function openSwatchPreviewFromPicker() {
      var grid = document.getElementById('swatchPopupGrid');
      var selected = grid ? grid.querySelector('.swatch-item.selected') : null;
      if (!selected) {
        showToast('Select a finish first (click one in the list).', true);
        return;
      }
      var id = selected.getAttribute('data-finish-id');
      var ft = selected.getAttribute('data-finish-type');
      if (!ft) ft = getFinishType(id);
      if (!id || id === 'none' || id === '') {
        showToast('Select a specific finish to preview.', true);
        return;
      }
      var labelEl = selected.querySelector('.swatch-label');
      var label = labelEl ? labelEl.textContent : id;
      openSwatchPreviewModal(ft || 'base', id, label);
    }

    function openSwatchPreviewModal(finishType, finishId, label) {
      swatchPreviewState = { finishType: finishType || 'base', finishId: finishId, label: label || finishId };
      var modal = document.getElementById('swatchPreviewModal');
      var titleEl = document.getElementById('swatchPreviewModalTitle');
      var imgEl = document.getElementById('swatchPreviewLargeImg');
      var wrap = document.getElementById('swatchPreviewOnPaintWrap');
      if (!modal || !imgEl || !wrap) return;
      if (titleEl) titleEl.textContent = label || finishId;
      imgEl.src = getServerBase() + '/api/swatch/' + finishType + '/' + finishId + '?color=888888&size=256&v=' + Date.now();
      imgEl.onerror = function() { this.style.background = '#333'; this.alt = 'Swatch failed to load'; };
      wrap.innerHTML = '<span style="color:var(--text-dim); font-size:11px;">Click &quot;Preview on paint&quot; to see this finish on your loaded paint.</span>';
      modal.style.display = 'flex';
      modal.onclick = function(e) { if (e.target === modal) closeSwatchPreviewModal(); };
      var btn = document.getElementById('swatchPreviewOnPaintBtn');
      if (btn) btn.onclick = runSwatchPreviewOnPaint;
    }

    function closeSwatchPreviewModal() {
      var modal = document.getElementById('swatchPreviewModal');
      if (modal) modal.style.display = 'none';
    }

    async function runSwatchPreviewOnPaint() {
      var finishType = swatchPreviewState.finishType;
      var finishId = swatchPreviewState.finishId;
      var paintFileEl = document.getElementById('paintFile');
      var paintFile = paintFileEl ? paintFileEl.value.trim() : '';
      if (!paintFile || (!paintFile.includes('/') && !paintFile.includes('\\'))) {
        showToast('Load a paint file first (Car Info / Source Paint).', true);
        return;
      }
      var zone = { name: 'Preview', color: 'remaining', intensity: '100' };
      if (finishType === 'base') {
        zone.base = finishId;
        zone.pattern = 'none';
      } else if (finishType === 'pattern') {
        zone.base = 'living_matte';
        zone.pattern = finishId;
      } else {
        zone.finish = finishId;
        var allFinishes = getMonolithics().concat(getBases());
        var m = allFinishes.find(function(item) { return item && item.id === finishId; });
        if (m && (m.swatch || m.swatch2 || m.swatch3)) {
          zone.finish_colors = { c1: m.swatch, c2: m.swatch2 || null, c3: m.swatch3 || null, ghost: m.ghostPattern || null };
        }
      }
      var wrap = document.getElementById('swatchPreviewOnPaintWrap');
      var btn = document.getElementById('swatchPreviewOnPaintBtn');
      if (wrap) wrap.innerHTML = '<span style="color:var(--text-dim);">Rendering...</span>';
      if (btn) btn.disabled = true;
      try {
        var resp = await fetch(getServerBase() + '/preview-render', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paint_file: paintFile, zones: [zone], seed: 51, preview_scale: 0.25 }),
          signal: AbortSignal.timeout(30000)
        });
        var data = await resp.json();
        if (data.success && data.paint_preview && wrap) {
          wrap.innerHTML = '';
          var img = document.createElement('img');
          img.src = data.paint_preview;
          img.style.width = '100%';
          img.style.height = '100%';
          img.style.objectFit = 'contain';
          img.style.borderRadius = '6px';
          wrap.appendChild(img);
        } else if (wrap) {
          wrap.innerHTML = '<span style="color:#cc6666;">Preview failed</span>';
        }
      } catch (_) {
        if (wrap) wrap.innerHTML = '<span style="color:#cc6666;">Request failed</span>';
        showToast('Preview failed. Is the server running?', true);
      }
      if (btn) btn.disabled = false;
    }

    Object.assign(global, {
      _disconnectSwatchPopupLazyLoader: _disconnectSwatchPopupLazyLoader,
      _hydrateDeferredSwatchImage: _hydrateDeferredSwatchImage,
      _scrollSwatchPickerToSelection: _scrollSwatchPickerToSelection,
      _installSwatchPopupLazyLoader: _installSwatchPopupLazyLoader,
      openSwatchPreviewFromPicker: openSwatchPreviewFromPicker,
      openSwatchPreviewModal: openSwatchPreviewModal,
      closeSwatchPreviewModal: closeSwatchPreviewModal,
      runSwatchPreviewOnPaint: runSwatchPreviewOnPaint
    });
  }

  global.SPBSwatchPopupPreviewControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
