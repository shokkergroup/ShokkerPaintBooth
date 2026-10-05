(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getSwatchPopupState = deps.getSwatchPopupState || function() { return global.swatchPopupState || { filter: 'all', sort: 'default' }; };
    var getPickerActiveLaneContext = deps.getPickerActiveLaneContext || function() { return global.pickerActiveLaneContext || {}; };
    var setPickerActiveLaneContext = deps.setPickerActiveLaneContext || function() {};
    var isFavorite = deps.isFavorite || function(id) { return typeof global.isFavorite === 'function' && global.isFavorite(id); };
    var smartSearchTokens = deps.smartSearchTokens || function(q) {
      return typeof global._smartSearchTokens === 'function' ? global._smartSearchTokens(q) : String(q || '').split(/\s+/).filter(Boolean);
    };
    var smartSearchWordMatches = deps.smartSearchWordMatches || function(hay, word, id) {
      return typeof global._smartSearchWordMatches === 'function' && global._smartSearchWordMatches(hay, word, id);
    };
    var smartSearchScore = deps.smartSearchScore || function(hay, query, id, label) {
      return typeof global._smartSearchScore === 'function' ? global._smartSearchScore(hay, query, id, label) : 0;
    };
    var swatchCurationLaneMatch = deps.swatchCurationLaneMatch || function() { return false; };
    var pickerCardMatchesContextCategory = deps.pickerCardMatchesContextCategory || function() { return true; };
    var updateSwatchCurationLaneCounts = deps.updateSwatchCurationLaneCounts || function() {};
    var updateSwatchActiveLaneStatus = deps.updateSwatchActiveLaneStatus || function() {};
    var updateSwatchGroupHealthBadges = deps.updateSwatchGroupHealthBadges || function() {};
    var installSwatchPopupLazyLoader = deps.installSwatchPopupLazyLoader || function() {};

    function _swatchPopupHayMatchesQuery(hay, query, finishId) {
      var q = String(query || '').trim().toLowerCase();
      if (!q) return true;
      var words = smartSearchTokens(q);
      return words.every(function(w) { return smartSearchWordMatches(hay, w, finishId); });
    }

    function _applySwatchPopupSort(grid) {
      if (!grid) return;
      var mode = getSwatchPopupState().sort || 'default';
      grid.querySelectorAll('.swatch-grid-row').forEach(function(row) {
        var cards = Array.prototype.slice.call(row.querySelectorAll('.swatch-item'));
        if (cards.length < 2) return;
        cards.sort(function(a, b) {
          var ai = Number(a.dataset.originalIndex || 0);
          var bi = Number(b.dataset.originalIndex || 0);
          if (mode === 'name') {
            return String(a.dataset.sortName || a.textContent || '').localeCompare(String(b.dataset.sortName || b.textContent || ''));
          }
          var ar = Number(a.dataset.rankOverall || 0);
          var br = Number(b.dataset.rankOverall || 0);
          // SPB-SIMPLIFY-2026-07-19h (owner): Best = the USER's Finish Rating sliders in
          // ranked order (unrated = the default 50); internal rank only breaks ties. The
          // default Grouped view also floats the owner's highest-rated to the top of each
          // category (rating first, then search relevance, then original order).
          var aRate = (a.dataset.rating !== undefined) ? Number(a.dataset.rating) : 50;
          var bRate = (b.dataset.rating !== undefined) ? Number(b.dataset.rating) : 50;
          var alow = a.dataset.rankConfidence === 'Low' ? 1 : 0;
          var blow = b.dataset.rankConfidence === 'Low' ? 1 : 0;
          if (mode === 'best') {
            if (bRate !== aRate) return bRate - aRate;
            if (br !== ar) return br - ar;
            return ai - bi;
          }
          if (mode === 'needs_review') {
            if (blow !== alow) return blow - alow;
            if (ar !== br) return ar - br;
            return ai - bi;
          }
          var as = Number(a.dataset.searchScore || 0);
          var bs = Number(b.dataset.searchScore || 0);
          if (bs !== as) return bs - as;
          if (bRate !== aRate) return bRate - aRate;
          return ai - bi;
        });
        cards.forEach(function(card) { row.appendChild(card); });
      });
    }

    function filterSwatchPopup(query) {
      var grid = document.getElementById('swatchPopupGrid');
      var countEl = document.getElementById('swatchPopupResultCount');
      if (!grid) return;
      var state = getSwatchPopupState();
      var items = grid.querySelectorAll('.swatch-item');
      var q = String(query || '').toLowerCase().trim();
      var activeFilter = state.filter || 'all';
      var activeContext = activeFilter === 'all' ? null : getPickerActiveLaneContext().main;
      var visibleCount = 0;
      var totalRanked = 0;
      items.forEach(function(item) {
        var name = ((item.getAttribute('data-name') || '') + ' ' + (item.getAttribute('data-search') || '')).toLowerCase();
        var desc = (item.getAttribute('data-desc') || '').toLowerCase();
        var idRaw = item.getAttribute('data-finish-id') || '';
        var hay = (name + ' ' + desc + ' ' + idRaw.toLowerCase()).replace(/\s+/g, ' ');
        var rank = Number(item.getAttribute('data-rank-overall') || 0);
        var spec = Number(item.getAttribute('data-rank-spec') || 0);
        var fit = Number(item.getAttribute('data-rank-fit') || 0);
        var render = Number(item.getAttribute('data-rank-render') || 0);
        var sponsor = Number(item.getAttribute('data-rank-sponsor') || 0);
        var confidence = item.getAttribute('data-rank-confidence') || '';
        var laneMatch = swatchCurationLaneMatch(item, activeFilter);
        if (rank > 0) totalRanked += 1;
        var textMatch = _swatchPopupHayMatchesQuery(hay, q, idRaw);
        item.dataset.searchScore = q ? String(smartSearchScore(hay, q, idRaw, item.textContent || '')) : '0';
        var filterMatch = activeFilter === 'all'
          || (activeFilter === 'favorites' && isFavorite(idRaw))
          || (activeFilter === 'strong' && rank >= 80 && confidence !== 'Low')
          || (activeFilter === 'sponsor_safe' && sponsor >= 76)
          || (activeFilter === 'high_spec' && spec >= 78)
          || (activeFilter === 'fast' && render >= 80)
          || (activeFilter === 'needs_review' && (rank > 0 && (rank < 70 || confidence === 'Low' || spec < 62 || fit < 62)))
          || laneMatch;
        var categoryMatch = pickerCardMatchesContextCategory(item, activeContext);
        var show = textMatch && filterMatch && categoryMatch;
        item.style.display = show ? '' : 'none';
        if (show) visibleCount += 1;
      });
      grid.querySelectorAll('.swatch-group').forEach(function(grp) {
        var visibleItems = grp.querySelectorAll('.swatch-item:not([style*="display: none"])');
        grp.style.display = ((q || activeFilter !== 'all') && visibleItems.length === 0) ? 'none' : '';
        if (q || activeFilter !== 'all') grp.classList.remove('collapsed');
        else if (visibleItems.length > 0 && !grp.querySelector('.swatch-item.selected')) grp.classList.add('collapsed');
      });
      _applySwatchPopupSort(grid);
      if (countEl) {
        var filterLabel = activeFilter === 'all' ? '' : ' - ' + activeFilter.replace(/_/g, ' ');
        var sortLabel = state.sort && state.sort !== 'default' ? ' - sort ' + state.sort.replace(/_/g, ' ') : '';
        countEl.textContent = visibleCount + ' shown' + (totalRanked ? ' - ' + totalRanked + ' ranked' : '') + filterLabel + sortLabel;
      }
      var emptyEl = document.getElementById('swatchPopupEmpty');
      if (emptyEl) {
        if (visibleCount === 0) {
          emptyEl.hidden = false;
          emptyEl.style.display = '';
        } else {
          emptyEl.hidden = true;
          emptyEl.style.display = 'none';
        }
      }
      updateSwatchCurationLaneCounts(grid);
      updateSwatchActiveLaneStatus(grid, visibleCount);
      updateSwatchGroupHealthBadges(grid);
      installSwatchPopupLazyLoader();
    }

    function setSwatchSmartSearch(query) {
      var input = document.getElementById('swatchSearchInput');
      if (!input) return;
      setSwatchPopupFilter('all');
      input.value = query || '';
      filterSwatchPopup(input.value);
      input.focus();
    }

    function setSwatchPopupFilter(filterName, context) {
      var state = getSwatchPopupState();
      state.filter = filterName || 'all';
      setPickerActiveLaneContext('main', null, state.filter === 'all' ? null : (context || null));
      var buttons = document.getElementById('swatchPopupFilterButtons');
      if (buttons) {
        buttons.querySelectorAll('.swatch-filter-chip').forEach(function(btn) {
          btn.classList.toggle('active', btn.dataset.filter === state.filter);
        });
      }
      var search = document.getElementById('swatchSearchInput');
      filterSwatchPopup(search ? search.value : '');
    }

    function setSwatchPopupSort(sortName) {
      var state = getSwatchPopupState();
      state.sort = sortName || 'default';
      var buttons = document.getElementById('swatchPopupSortButtons');
      if (buttons) {
        buttons.querySelectorAll('.swatch-sort-chip').forEach(function(btn) {
          btn.classList.toggle('active', btn.dataset.sort === state.sort);
        });
      }
      var search = document.getElementById('swatchSearchInput');
      filterSwatchPopup(search ? search.value : '');
    }

    Object.assign(global, {
      _swatchPopupHayMatchesQuery: _swatchPopupHayMatchesQuery,
      _applySwatchPopupSort: _applySwatchPopupSort,
      filterSwatchPopup: filterSwatchPopup,
      setSwatchSmartSearch: setSwatchSmartSearch,
      setSwatchPopupFilter: setSwatchPopupFilter,
      setSwatchPopupSort: setSwatchPopupSort
    });
  }

  global.SPBSwatchPopupFilterControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
