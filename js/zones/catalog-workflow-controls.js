'use strict';

(function () {
  function install(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function () { return window.zones || []; };
    const getSelectedZoneIndex = deps.getSelectedZoneIndex || function () { return window.selectedZoneIndex || 0; };
    const pushZoneUndo = deps.pushZoneUndo || window.pushZoneUndo || function () {};
    const renderZones = deps.renderZones || window.renderZones || function () {};
    const showToast = deps.showToast || window.showToast || function () {};
    const triggerPreviewRender = deps.triggerPreviewRender || window.triggerPreviewRender || function () {};
    const assignFinishToSelected = deps.assignFinishToSelected || window.assignFinishToSelected;
    const applyFinishToAllZones = deps.applyFinishToAllZones || window.applyFinishToAllZones;
    const selectZone = deps.selectZone || window.selectZone;
    const renderFinishLibrary = deps.renderFinishLibrary || window.renderFinishLibrary;
    const getMetadata = deps.getMetadata || window._getMetadata;
    const isFavorite = deps.isFavorite || window.isFavorite;
    const toggleFavorite = deps.toggleFavorite || window.toggleFavorite;
    const getRecentFinishes = deps.getRecentFinishes || function () { return window._recentFinishes || []; };
    const clearRecentFinishes = deps.clearRecentFinishes || function () {
      window._recentFinishes = [];
      try { localStorage.setItem('spb_recent_finishes', '[]'); } catch (e) {}
    };

    let cmdPaletteEl = null;
    let cmdPaletteSelectedIndex = 0;
    let cmdPaletteItems = [];
    if (typeof window._activeFilterChip === 'undefined') window._activeFilterChip = null;

    function findFinish(id) {
      const base = (typeof BASES !== 'undefined') ? BASES.find(b => b.id === id) : null;
      const pat = (typeof PATTERNS !== 'undefined') ? PATTERNS.find(p => p.id === id) : null;
      const mono = (typeof MONOLITHICS !== 'undefined') ? MONOLITHICS.find(m => m.id === id) : null;
      return base || pat || mono;
    }

    function allFinishes() {
      return [
        ...(typeof BASES !== 'undefined' ? BASES : []),
        ...(typeof PATTERNS !== 'undefined' ? PATTERNS : []),
        ...(typeof MONOLITHICS !== 'undefined' ? MONOLITHICS : []),
      ];
    }

    function fuzzyScore(target, query) {
      if (!query) return 100;
      target = target.toLowerCase();
      let tIndex = 0;
      let score = 0;
      for (let i = 0; i < query.length; i++) {
        const ch = query[i];
        const found = target.indexOf(ch, tIndex);
        if (found === -1) return 0;
        score += (100 - (found - tIndex) * 2);
        tIndex = found + 1;
      }
      return Math.max(1, Math.floor(score / query.length));
    }

    window.enhanceGuidedCatalogCards = function enhanceGuidedCatalogCards() {
      const catalog = document.querySelector('.finish-guided-catalog');
      if (!catalog) return;
      const cards = catalog.querySelectorAll('.finish-catalog-card');
      cards.forEach(card => {
        if (card.querySelector('.qa-actions')) return;
        const finishId = card.dataset.finishId || card.getAttribute('data-id') || card.getAttribute('data-finish-id');
        if (!finishId) return;

        const actions = document.createElement('div');
        actions.className = 'qa-actions';

        const star = document.createElement('button');
        star.className = 'qa-action-btn star';
        star.innerHTML = '&#9733;';
        star.title = 'Favorite';
        if (typeof isFavorite === 'function' && isFavorite(finishId)) star.classList.add('active');
        star.onclick = (e) => {
          e.stopPropagation();
          if (typeof toggleFavorite === 'function') toggleFavorite(finishId, e);
          star.classList.toggle('active');
        };

        const apply = document.createElement('button');
        apply.className = 'qa-action-btn apply-all';
        apply.innerHTML = 'ALL';
        apply.title = 'Apply to all zones';
        apply.onclick = (e) => {
          e.stopPropagation();
          if (typeof assignFinishToSelected === 'function') assignFinishToSelected(finishId);
          if (typeof applyFinishToAllZones === 'function') {
            setTimeout(() => {
              if (!confirm('Apply this finish to ALL zones?')) return;
              const src = getZones()[getSelectedZoneIndex()];
              if (!src || (!src.base && !src.finish)) return;
              pushZoneUndo('Apply finish to all zones');
              getZones().forEach(z => {
                if (src.base) { z.base = src.base; z.finish = null; }
                else if (src.finish) { z.finish = src.finish; z.base = null; }
                if (src.pattern) z.pattern = src.pattern;
              });
              renderZones();
              triggerPreviewRender();
              showToast('Applied to all zones');
            }, 60);
          }
        };

        actions.appendChild(star);
        actions.appendChild(apply);
        card.appendChild(actions);
      });
    };

    window.showCommandPalette = function showCommandPalette() {
      if (!cmdPaletteEl) {
        cmdPaletteEl = document.createElement('div');
        cmdPaletteEl.className = 'spb-command-palette';
        cmdPaletteEl.innerHTML = [
          '<div class="spb-command-palette-header">',
          '<input type="text" placeholder="Search finishes, zones, or actions..." />',
          '</div>',
          '<div class="spb-command-palette-results"></div>',
        ].join('');
        document.body.appendChild(cmdPaletteEl);

        const input = cmdPaletteEl.querySelector('input');
        const results = cmdPaletteEl.querySelector('.spb-command-palette-results');
        input.addEventListener('input', () => { window.renderCommandPaletteResults(input.value, results); });
        input.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            cmdPaletteSelectedIndex = Math.min(cmdPaletteSelectedIndex + 1, cmdPaletteItems.length - 1);
            window.highlightCommandPaletteSelection(results);
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            cmdPaletteSelectedIndex = Math.max(cmdPaletteSelectedIndex - 1, 0);
            window.highlightCommandPaletteSelection(results);
          } else if (e.key === 'Enter') {
            e.preventDefault();
            window.executeCommandPaletteSelection();
          } else if (e.key === 'Escape') {
            window.hideCommandPalette();
          }
        });
        cmdPaletteEl.addEventListener('click', (e) => {
          const item = e.target.closest('.spb-command-palette-item');
          if (item && item.dataset.index) {
            cmdPaletteSelectedIndex = parseInt(item.dataset.index, 10);
            window.executeCommandPaletteSelection();
          }
        });
      }

      cmdPaletteEl.style.display = 'block';
      cmdPaletteEl.classList.add('open');
      const input = cmdPaletteEl.querySelector('input');
      const results = cmdPaletteEl.querySelector('.spb-command-palette-results');
      input.value = '';
      cmdPaletteSelectedIndex = 0;
      window.renderCommandPaletteResults('', results);
      input.focus();
    };

    window.hideCommandPalette = function hideCommandPalette() {
      if (!cmdPaletteEl) return;
      cmdPaletteEl.classList.remove('open');
      cmdPaletteEl.style.display = 'none';
    };

    window.renderCommandPaletteResults = function renderCommandPaletteResults(query, resultsEl) {
      const q = (query || '').toLowerCase().trim();
      const recentSection = [];
      const recent = getRecentFinishes() || [];
      if (!q && recent.length > 0) {
        recent.slice(0, 5).forEach(id => {
          const item = findFinish(id);
          if (!item) return;
          recentSection.push({
            type: 'finish',
            id: item.id,
            label: item.name,
            meta: 'Recent',
            action: () => {
              if (typeof assignFinishToSelected === 'function') assignFinishToSelected(item.id);
              window.hideCommandPalette();
            },
          });
        });
      }

      const scored = [];
      allFinishes().forEach(f => {
        const score = q ? fuzzyScore(f.name + ' ' + f.id, q) : 50;
        if (q && score === 0) return;
        scored.push({
          type: 'finish',
          id: f.id,
          label: f.name,
          meta: f.id,
          score,
          action: () => {
            if (typeof assignFinishToSelected === 'function') assignFinishToSelected(f.id);
            window.hideCommandPalette();
          },
        });
      });

      getZones().forEach((z, i) => {
        const name = z.name || `Zone ${i + 1}`;
        const score = q ? fuzzyScore(name, q) : 50;
        if (q && score === 0) return;
        scored.push({
          type: 'zone',
          id: i,
          label: `Select ${name}`,
          meta: 'Zone',
          score,
          action: () => {
            if (typeof selectZone === 'function') selectZone(i);
            window.hideCommandPalette();
          },
        });
      });

      if (q) scored.sort((a, b) => b.score - a.score);
      const actions = [
        {
          type: 'action',
          id: 'apply-all',
          label: 'Apply current finish to ALL zones',
          meta: 'Action',
          action: () => {
            if (typeof applyFinishToAllZones === 'function') applyFinishToAllZones();
            window.hideCommandPalette();
          },
        },
        {
          type: 'action',
          id: 'select-current',
          label: 'Select current active zone',
          meta: 'Action',
          action: () => {
            if (typeof selectZone === 'function') selectZone(getSelectedZoneIndex());
            window.hideCommandPalette();
          },
        },
      ];
      if (recent.length > 0) {
        actions.push({
          type: 'action',
          id: 'clear-recents',
          label: 'Clear recently used finishes',
          meta: 'Action',
          action: () => {
            clearRecentFinishes();
            window.hideCommandPalette();
            showToast('Recently used list cleared');
          },
        });
      }

      cmdPaletteItems = [...recentSection, ...actions, ...scored].slice(0, 20);
      if (cmdPaletteItems.length === 0) {
        resultsEl.innerHTML = '<div class="spb-command-palette-empty">No matches. Try a finish name or zone.</div>';
        return;
      }

      resultsEl.innerHTML = cmdPaletteItems.map((item, idx) => {
        let icon = '&#127912;';
        if (item.type === 'zone') icon = '&#128205;';
        if (item.type === 'action') icon = '&#9889;';
        if (item.meta === 'Recent') icon = '&#128338;';
        return [
          `<div class="spb-command-palette-item ${idx === cmdPaletteSelectedIndex ? 'selected' : ''}" data-index="${idx}">`,
          `<span class="icon">${icon}</span>`,
          `<span class="label">${item.label}</span>`,
          `<span class="meta">${item.meta}</span>`,
          '</div>',
        ].join('');
      }).join('');
    };

    window.highlightCommandPaletteSelection = function highlightCommandPaletteSelection(resultsEl) {
      const nodes = resultsEl.querySelectorAll('.spb-command-palette-item');
      nodes.forEach((n, i) => n.classList.toggle('selected', i === cmdPaletteSelectedIndex));
    };

    window.executeCommandPaletteSelection = function executeCommandPaletteSelection() {
      const item = cmdPaletteItems[cmdPaletteSelectedIndex];
      if (item && typeof item.action === 'function') item.action();
      else window.hideCommandPalette();
    };

    document.addEventListener('keydown', (e) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      if ((isMac && e.metaKey && e.key.toLowerCase() === 'k') || (!isMac && e.ctrlKey && e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        if (cmdPaletteEl && cmdPaletteEl.classList.contains('open')) window.hideCommandPalette();
        else window.showCommandPalette();
      }
    });

    window.renderSmartFilterChips = function renderSmartFilterChips(container, activeTabId, onFilterChange) {
      if (!container) return;
      const existing = container.querySelector('.spb-filter-chips');
      if (existing) existing.remove();
      const chipsWrap = document.createElement('div');
      chipsWrap.className = 'spb-filter-chips';
      const chips = [
        { id: 'metallic', label: 'Metallic' },
        { id: 'pearl', label: 'Pearl' },
        { id: 'chrome', label: 'Chrome' },
        { id: 'matte', label: 'Matte' },
        { id: 'shift', label: 'Color-Shift' },
        { id: 'premium', label: 'Premium' },
      ];
      chips.forEach(chip => {
        const el = document.createElement('div');
        el.className = `spb-filter-chip ${window._activeFilterChip === chip.id ? 'active' : ''}`;
        el.textContent = chip.label;
        el.onclick = () => {
          window._activeFilterChip = (window._activeFilterChip === chip.id) ? null : chip.id;
          if (typeof renderFinishLibrary === 'function') renderFinishLibrary();
          if (onFilterChange) onFilterChange();
        };
        chipsWrap.appendChild(el);
      });
      const heading = container.querySelector('.finish-catalog-heading');
      if (heading && heading.parentNode) heading.parentNode.insertBefore(chipsWrap, heading.nextSibling);
      else container.prepend(chipsWrap);
    };

    window.applySmartFilterChips = function applySmartFilterChips(items) {
      if (!window._activeFilterChip) return items;
      const chip = window._activeFilterChip;
      return items.filter(item => {
        const meta = (typeof getMetadata === 'function') ? getMetadata(item.id) : null;
        const family = meta && meta.family ? meta.family : '';
        const hay = (item.name + ' ' + (item.desc || '') + ' ' + family).toLowerCase();
        if (chip === 'metallic') return hay.includes('metal') || hay.includes('flake') || hay.includes('chrome') || family.includes('metal');
        if (chip === 'pearl') return hay.includes('pearl') || hay.includes('iridescent');
        if (chip === 'chrome') return hay.includes('chrome') || hay.includes('mirror');
        if (chip === 'matte') return hay.includes('matte') || hay.includes('flat') || hay.includes('satin');
        if (chip === 'shift') return hay.includes('shift') || hay.includes('chameleon') || (item.swatch2 && item.swatch3);
        if (chip === 'premium') return (meta && (meta.tier === 'hero' || meta.featured)) || /colorshoxx|mortal|shokk|prizm|viva/i.test(hay);
        return true;
      });
    };

    window.enhanceZoneCardsMaterial = function enhanceZoneCardsMaterial() {
      const container = document.getElementById('zoneList');
      if (!container) return;
      const cards = container.querySelectorAll('.zone-card');
      cards.forEach((card, idx) => {
        const zone = getZones()[idx];
        if (!zone) return;
        let accent = '#334155';
        const finishId = zone.finish || zone.base;
        if (finishId) {
          const item = findFinish(finishId);
          if (item && item.swatch) accent = item.swatch;
        }
        card.style.setProperty('--zone-accent', accent);
        const header = card.querySelector('.zone-card-header');
        if (header) {
          let dot = header.querySelector('.zone-finish-dot');
          if (!dot) {
            dot = document.createElement('span');
            dot.className = 'zone-finish-dot';
            const num = header.querySelector('.zone-number');
            if (num && num.nextSibling) header.insertBefore(dot, num.nextSibling);
            else header.appendChild(dot);
          }
          dot.style.background = accent;
        }
        const num = card.querySelector('.zone-number');
        if (num && !card._numEnhanced) {
          card._numEnhanced = true;
          card.addEventListener('mouseenter', () => {
            if (card.classList.contains('selected')) num.style.transform = 'scale(1.08)';
          });
          card.addEventListener('mouseleave', () => { num.style.transform = ''; });
        }
      });
    };
  }

  window.SPBZoneCatalogWorkflowControls = { install };
})();
