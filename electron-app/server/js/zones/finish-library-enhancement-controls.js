(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = global.document;
    var getZones = deps.getZones || function() { return []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return -1; };
    var renderFinishLibrary = deps.renderFinishLibrary || function() {
      if (typeof global.renderFinishLibrary === 'function') global.renderFinishLibrary();
    };
    var getFinishType = deps.getFinishType || function(id) {
      return typeof global.getFinishType === 'function' ? global.getFinishType(id) : null;
    };
    var getMetadata = deps.getMetadata || function(id) {
      return typeof global._getMetadata === 'function' ? global._getMetadata(id) : null;
    };
    var getSwatchUrl = deps.getSwatchUrl || function(id, color, large, size) {
      return typeof global.getSwatchUrl === 'function' ? global.getSwatchUrl(id, color, large, size) : null;
    };
    var getZoneColorHex = deps.getZoneColorHex || function(zone) {
      return typeof global.getZoneColorHex === 'function' ? global.getZoneColorHex(zone) : '888888';
    };

    function enhanceLibraryCards() {
      var grid = doc && doc.getElementById('shokkLibraryGrid');
      if (!grid) return;

      var cards = grid.querySelectorAll('.shokk-card');
      cards.forEach(function(card) {
        if (card.querySelector('.shokk-card-category')) return;

        var nameEl = card.querySelector('.shokk-card-name') || card.querySelector('span:last-child');
        if (!nameEl) return;

        var finishId = card.dataset.finishId || card.getAttribute('data-id');
        if (!finishId) return;

        var type = getFinishType(finishId);
        var meta = getMetadata(finishId);
        var category = type || (finishId.startsWith('mono:') ? 'monolithic' : 'base');
        var catLabel = category.charAt(0).toUpperCase() + category.slice(1);

        var metaWrap = doc.createElement('div');
        metaWrap.className = 'shokk-card-meta';

        var badge = doc.createElement('span');
        badge.className = 'shokk-card-category';
        badge.textContent = catLabel;
        badge.dataset.category = category;
        metaWrap.appendChild(badge);

        if (meta && meta.family) {
          var pers = doc.createElement('span');
          pers.className = 'shokk-card-personality';
          pers.textContent = meta.family;
          metaWrap.appendChild(pers);
        }

        var main = doc.createElement('div');
        main.className = 'shokk-card-main';
        while (card.firstChild) main.appendChild(card.firstChild);
        card.appendChild(main);
        card.appendChild(metaWrap);

        var swatchImg = card.querySelector('img');
        if (swatchImg && finishId) {
          var originalSrc = swatchImg.src;
          card.addEventListener('mouseenter', function() {
            var largeUrl = getSwatchUrl(finishId, null, true, 96) || originalSrc.replace(/size=\d+/, 'size=96');
            if (largeUrl) swatchImg.src = largeUrl;
            swatchImg.style.transform = 'scale(1.15)';
            swatchImg.style.transition = 'transform 0.15s ease';
          });
          card.addEventListener('mouseleave', function() {
            swatchImg.src = originalSrc;
            swatchImg.style.transform = '';
          });
        }

        card.addEventListener('click', function() {
          card.classList.add('library-choice-sent');
          var center = doc.getElementById('centerPanel');
          if (center) {
            center.classList.remove('library-preview-active');
            center.classList.remove('previewing-choice');
            center.classList.add('library-to-celebration');
            setTimeout(function() {
              if (center) center.classList.remove('library-to-celebration');
            }, 800);
          }
          setTimeout(function() {
            card.classList.remove('library-choice-sent');
          }, 900);
        }, { once: false });

        card.addEventListener('mouseenter', function() {
          if (getSelectedZoneIndex() >= 0) {
            card.style.boxShadow = '0 0 0 2px rgba(0,229,255,0.3), 0 10px 24px rgba(0,0,0,0.4)';
            var centerPanel = doc.getElementById('centerPanel');
            if (centerPanel) {
              centerPanel.classList.add('previewing-choice');
              centerPanel.classList.add('library-preview-active');
            }
          }
        });

        card.addEventListener('mouseleave', function() {
          card.style.boxShadow = '';
          var centerPanel = doc.getElementById('centerPanel');
          if (centerPanel) {
            centerPanel.classList.remove('previewing-choice');
            centerPanel.classList.remove('library-preview-active');
          }
        });
      });

      var selectedZoneIndex = getSelectedZoneIndex();
      var zones = getZones();
      if (selectedZoneIndex >= 0 && zones[selectedZoneIndex]) {
        var currentColor = zones[selectedZoneIndex].color || '#888888';
        cards.forEach(function(card) {
          var img = card.querySelector('img');
          var finishId = card.dataset.finishId || card.getAttribute('data-id');
          if (img && finishId) {
            var colorText = String(currentColor).replace('#', '');
            var syncedUrl = getSwatchUrl(finishId, colorText, true, 48) || img.src.replace(/color=[^&]+/, 'color=' + colorText);
            if (syncedUrl) img.src = syncedUrl;
          }
        });

        var indicator = grid.querySelector('.library-context-indicator');
        if (!indicator) {
          indicator = doc.createElement('div');
          indicator.className = 'library-context-indicator';
          indicator.style.cssText = 'position:absolute;top:8px;right:16px;font-size:9px;font-weight:700;letter-spacing:0.5px;background:rgba(0,229,255,0.15);color:#00e5ff;padding:2px 8px;border-radius:999px;border:1px solid #00e5ff;box-shadow:0 0 6px rgba(0,229,255,0.3);';
          indicator.textContent = 'Matching current zone color';
          var toolbar = doc.querySelector('.shokk-modal-toolbar');
          if (toolbar) toolbar.appendChild(indicator);
          else if (grid.parentNode) grid.parentNode.insertBefore(indicator, grid);
        }

        var inspiredId = grid.dataset.inspiredBy;
        if (inspiredId) {
          var inspiredType = getFinishType(inspiredId);
          var inspiredMeta = getMetadata(inspiredId);
          cards.forEach(function(card) {
            var cardId = card.dataset.finishId || card.getAttribute('data-id');
            if (!cardId) return;
            var cardType = getFinishType(cardId);
            var cardMeta = getMetadata(cardId);
            var typeMatch = inspiredType && cardType && inspiredType === cardType;
            var familyMatch = inspiredMeta && cardMeta && inspiredMeta.family && cardMeta.family === inspiredMeta.family;
            if (typeMatch || familyMatch) card.classList.add('inspired-highlight');
          });
        }
      } else {
        var oldIndicator = doc.querySelector('.library-context-indicator');
        if (oldIndicator) oldIndicator.remove();
        grid.querySelectorAll('.shokk-card.inspired-highlight').forEach(function(card) {
          card.classList.remove('inspired-highlight');
        });
      }
    }

    function addInspireButtonToActiveFinishRow(detailContainer) {
      if (!detailContainer) return;
      var activeRows = detailContainer.querySelectorAll('.zone-finish-row:focus-within, .zone-finish-row.active-choice');
      activeRows.forEach(function(row) {
        if (row.querySelector('.inspire-btn')) return;
        var inspireBtn = doc.createElement('button');
        inspireBtn.className = 'inspire-btn';
        inspireBtn.textContent = 'Inspire';
        inspireBtn.title = 'Find finishes similar to this one in the library';
        inspireBtn.style.cssText = 'margin-left:6px;font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(255,209,102,0.15);border:1px solid #ffd166;color:#ffd166;cursor:pointer;';
        inspireBtn.onclick = function(e) {
          e.stopImmediatePropagation();
          inspireFromCurrentZone();
        };
        row.appendChild(inspireBtn);
      });
    }

    function inspireFromCurrentZone() {
      var selectedZoneIndex = getSelectedZoneIndex();
      if (selectedZoneIndex < 0) return;
      var zone = getZones()[selectedZoneIndex];
      if (!zone) return;
      var inspireFromId = zone.finish || zone.pattern || zone.base;
      if (!inspireFromId || inspireFromId === 'none') return;

      var libraryModal = doc.getElementById('shokkLibraryModal');
      if (libraryModal) libraryModal.style.display = 'flex';

      var grid = doc.getElementById('shokkLibraryGrid');
      if (grid) {
        grid.dataset.inspiredBy = inspireFromId;
        grid.dataset.inspiredZone = String(selectedZoneIndex);
      }

      renderFinishLibrary();

      setTimeout(function() {
        enhanceLibraryCards();
        var inspiredType = getFinishType(inspireFromId);
        if (inspiredType && grid) {
          var sectionLabel = grid.querySelector('.shokk-section-label');
          if (sectionLabel) {
            sectionLabel.style.borderBottom = '2px solid #ffd166';
            setTimeout(function() {
              if (sectionLabel) sectionLabel.style.borderBottom = '';
            }, 2500);
          }
        }
      }, 80);
    }

    function attachZoneFinishHoverPreview() {
      var detailRoot = doc.getElementById('zoneEditorFloat') || doc.getElementById('zoneDetailPanel');
      if (!detailRoot || detailRoot.dataset.hoverPreviewWired === '1') return;
      detailRoot.dataset.hoverPreviewWired = '1';

      var previewEl = null;

      detailRoot.addEventListener('mouseenter', function(e) {
        var row = e.target.closest('.zone-finish-row');
        if (!row) return;
        if (row.querySelector('select[onchange^="setZoneBaseColorMode"]') || /Base Color/i.test(row.textContent || '')) {
          if (previewEl) {
            previewEl.classList.remove('visible');
            previewEl.style.display = 'none';
          }
          return;
        }

        var select = row.querySelector('select');
        if (!select || !select.value || select.value === 'none') return;

        var finishId = select.value;
        var zoneIndex = getSelectedZoneIndex();
        var colorHex = '888888';
        var zones = getZones();
        if (zones[zoneIndex]) colorHex = getZoneColorHex(zones[zoneIndex]);

        var largeUrl = getSwatchUrl(finishId, colorHex, true, 128);
        if (!largeUrl) return;

        if (!previewEl) {
          previewEl = doc.createElement('div');
          previewEl.className = 'zone-finish-hover-preview';
          previewEl.innerHTML = '<img class="preview-swatch" />'
            + '<div class="preview-label"></div>'
            + '<div class="preview-ekg"></div>'
            + '<button class="apply-btn">USE THIS FINISH</button>'
            + '<button class="more-like-btn">More like this</button>';
          doc.body.appendChild(previewEl);
        }

        var img = previewEl.querySelector('.preview-swatch');
        var label = previewEl.querySelector('.preview-label');
        var applyBtn = previewEl.querySelector('.apply-btn');
        img.src = largeUrl;
        var nameEl = row.querySelector('.zone-finish-name, .finish-name');
        label.textContent = nameEl ? nameEl.textContent : finishId;

        var rect = row.getBoundingClientRect();
        previewEl.style.left = (rect.right + 12) + 'px';
        previewEl.style.top = (rect.top + global.scrollY) + 'px';
        previewEl.style.display = 'flex';

        applyBtn.onclick = function(ev) {
          ev.stopImmediatePropagation();
          var activeSelect = row.querySelector('select');
          if (activeSelect) {
            activeSelect.value = finishId;
            activeSelect.dispatchEvent(new Event('change', { bubbles: true }));
          }
          previewEl.classList.remove('visible');
          setTimeout(function() { previewEl.style.display = 'none'; }, 120);
        };

        var moreLikeBtn = previewEl.querySelector('.more-like-btn');
        if (moreLikeBtn) {
          moreLikeBtn.onclick = function(ev) {
            ev.stopImmediatePropagation();
            var libraryModal = doc.getElementById('shokkLibraryModal');
            if (libraryModal) libraryModal.style.display = 'flex';
            var grid = doc.getElementById('shokkLibraryGrid');
            if (grid) {
              grid.dataset.inspiredBy = finishId;
              grid.dataset.inspiredFromZoneHover = 'true';
            }
            renderFinishLibrary();
            setTimeout(enhanceLibraryCards, 80);
            if (previewEl) {
              previewEl.classList.remove('visible');
              setTimeout(function() { if (previewEl) previewEl.style.display = 'none'; }, 120);
            }
          };
        }

        var centerPanel = doc.getElementById('centerPanel');
        if (centerPanel) centerPanel.classList.add('previewing-choice');
        requestAnimationFrame(function() {
          previewEl.classList.add('visible');
        });
      }, true);

      detailRoot.addEventListener('mouseleave', function() {
        var centerPanel = doc.getElementById('centerPanel');
        if (centerPanel) centerPanel.classList.remove('previewing-choice');
      }, true);

      detailRoot.addEventListener('mouseleave', function(e) {
        var row = e.target.closest('.zone-finish-row');
        if (!row && previewEl) {
          previewEl.classList.remove('visible');
          setTimeout(function() {
            if (previewEl) previewEl.style.display = 'none';
          }, 120);
        }
      }, true);
    }

    Object.assign(global, {
      enhanceLibraryCards: enhanceLibraryCards,
      addInspireButtonToActiveFinishRow: addInspireButtonToActiveFinishRow,
      inspireFromCurrentZone: inspireFromCurrentZone,
      attachZoneFinishHoverPreview: attachZoneFinishHoverPreview
    });
  }

  global.SPBZoneFinishLibraryEnhancementControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
