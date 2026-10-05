(function(global) {
  'use strict';

  function installSwatchPopupActionControls(deps) {
    deps = deps || {};
    const getDocument = deps.getDocument || function() { return global.document; };
    const getSwatchPopupState = deps.getSwatchPopupState || function() { return {}; };
    const setSwatchPopupFilter = deps.setSwatchPopupFilter || function(filterName) { getSwatchPopupState().filter = filterName; };
    const setSwatchPopupSort = deps.setSwatchPopupSort || function(sortName) { getSwatchPopupState().sort = sortName; };
    const getFavoriteFinishes = deps.getFavoriteFinishes || function() { return new Set(); };
    const getLocalStorage = deps.getLocalStorage || function() { return global.localStorage; };
    const renderFinishLibrary = deps.renderFinishLibrary || function() {};
    const openSwatchPicker = deps.openSwatchPicker || function() {};
    const renderSwatchPopupFilterControls = deps.renderSwatchPopupFilterControls || function() {};
    const filterSwatchPopup = deps.filterSwatchPopup || function() {};
    const renderSwatchLowScorePanel = deps.renderSwatchLowScorePanel || function() {};
    const renderSwatchFavoritesGroup = deps.renderSwatchFavoritesGroup || function() { return ''; };
    const isFavorite = deps.isFavorite || function(id) { return getFavoriteFinishes().has(id); };
    const getFinishType = deps.getFinishType || function() { return 'base'; };
    const getSwatchItemById = deps.getSwatchItemById || function() { return null; };
    const catalogRankingForItem = deps.catalogRankingForItem || function() {
      return { overall: 0, confidence: 'Low', specDetail: 0, intentFit: 0, renderTime: 0, sponsorSafety: 0 };
    };
    const swatchPickerSearchText = deps.swatchPickerSearchText || function(item) { return [item && item.name, item && item.id].filter(Boolean).join(' '); };
    const renderCatalogRankChips = deps.renderCatalogRankChips || function() { return ''; };
    const renderSwatchMaterialChips = deps.renderSwatchMaterialChips || function() { return ''; };

    function toggleSwatchLowScorePanel(force) {
      const documentRef = getDocument();
      const panel = documentRef ? documentRef.getElementById('swatchLowScorePanel') : null;
      const btn = documentRef ? documentRef.getElementById('swatchPopupReviewBtn') : null;
      if (!panel) return;
      const nextOpen = typeof force === 'boolean' ? force : panel.hidden;
      panel.hidden = !nextOpen;
      if (btn) {
        btn.classList.toggle('active', nextOpen);
        btn.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
      }
      if (nextOpen) renderSwatchLowScorePanel(18);
    }

    function focusSwatchReviewCandidate(id, event, filterName) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const documentRef = getDocument();
      const search = documentRef ? documentRef.getElementById('swatchSearchInput') : null;
      if (search) search.value = id || '';
      const state = getSwatchPopupState();
      const nextFilter = filterName || 'needs_review';
      setSwatchPopupFilter(nextFilter);
      setSwatchPopupSort(filterName === 'showcase' ? 'best' : 'needs_review');
      renderSwatchPopupFilterControls(state.type);
      filterSwatchPopup(id || '');
      const grid = documentRef ? documentRef.getElementById('swatchPopupGrid') : null;
      const card = grid ? grid.querySelector('.swatch-item[data-finish-id="' + String(id || '').replace(/"/g, '\\"') + '"]') : null;
      if (card && typeof card.scrollIntoView === 'function') card.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }

    function toggleSwatchPickerFavorite(finishId, event) {
      if (event) {
        event.stopPropagation();
        event.preventDefault();
      }
      if (!finishId) return;
      const favorites = getFavoriteFinishes();
      if (favorites.has(finishId)) favorites.delete(finishId);
      else favorites.add(finishId);
      try {
        const storage = getLocalStorage();
        if (storage) storage.setItem('shokker_favorites', JSON.stringify(Array.from(favorites)));
      } catch (_) {}
      if (global.SPBFinishPreferences) global.SPBFinishPreferences.favorite(finishId, favorites.has(finishId));
      if (global.SPBPickerDetail && global.SPBPickerDetail.refreshFavorite(finishId, favorites.has(finishId))) return;
      renderFinishLibrary();
      const state = getSwatchPopupState();
      if (state.open && state.triggerEl) {
        state.open = false;
        openSwatchPicker(state.triggerEl, state.type, state.zoneIndex, state.layerIndex);
      }
    }

    function _enhanceSwatchPopupCards(currentId, pickerType) {
      const documentRef = getDocument();
      const grid = documentRef ? documentRef.getElementById('swatchPopupGrid') : null;
      if (!grid) return;
      // Spec cards supply material metadata and their own scoped favorites.
      if (pickerType === 'specOverlay') return;
      const favKind = (pickerType === 'pattern' || pickerType === 'stackPattern' || pickerType === 'secondBasePattern' || pickerType === 'thirdBasePattern')
        ? 'pattern'
        : 'finish';
      const favHtml = renderSwatchFavoritesGroup(favKind, currentId);
      if (favHtml) grid.insertAdjacentHTML('afterbegin', favHtml);
      let idx = 0;
      grid.querySelectorAll('.swatch-item[data-finish-id]').forEach(function(card) {
        if (!card.dataset.originalIndex) card.dataset.originalIndex = String(idx++);
        const id = card.getAttribute('data-finish-id');
        const ft = card.getAttribute('data-finish-type') || getFinishType(id);
        const hit = getSwatchItemById(id, ft === 'pattern' ? 'pattern' : null);
        const item = hit ? hit.item : { id: id, name: id, desc: card.getAttribute('data-desc') || id, swatch: '#444' };
        const rank = catalogRankingForItem(item, ft);
        card.classList.add('swatch-catalog-card');
        card.setAttribute('data-search', swatchPickerSearchText(item, ft, card.closest('.swatch-group')?.querySelector('.swatch-group-label')?.textContent || '').toLowerCase());
        card.setAttribute('data-sort-name', String(item.name || id).toLowerCase());
        card.setAttribute('data-rank-overall', String(rank.overall));
        card.setAttribute('data-rank-confidence', rank.confidence || '');
        card.setAttribute('data-rank-spec', String(rank.specDetail));
        card.setAttribute('data-rank-fit', String(rank.intentFit));
        card.setAttribute('data-rank-render', String(rank.renderTime));
        card.setAttribute('data-rank-sponsor', String(rank.sponsorSafety));
        card.setAttribute('data-owner-status', rank.ownerStatus || '');
        card.setAttribute('data-measured-overall', String(rank.measuredOverall || rank.scorecardOverall || ''));
        card.setAttribute('data-handoff', (rank.overall < 70 || rank.confidence === 'Low' || rank.confidence === 'Broken' || rank.specDetail < 62 || rank.intentFit < 62 || /low_|slow_|flat_spec|macro_dominated|broken/.test(String(rank.reasonFlags || ''))) ? 'true' : 'false');
        if (!card.querySelector('.swatch-fav-btn')) {
          const favBtn = documentRef.createElement('button');
          favBtn.type = 'button';
          favBtn.className = 'swatch-fav-btn' + (isFavorite(id) ? ' active' : '');
          favBtn.title = isFavorite(id) ? 'Remove from favorites' : 'Add to favorites';
          favBtn.textContent = isFavorite(id) ? '*' : '+';
          favBtn.onclick = function(event) { toggleSwatchPickerFavorite(id, event); };
          card.insertBefore(favBtn, card.firstChild);
        }
        if (!card.querySelector('.swatch-rank-row')) {
          card.insertAdjacentHTML('beforeend', renderCatalogRankChips(item, ft, rank));
        }
        if (!card.querySelector('.swatch-material-row')) {
          const rankRow = card.querySelector('.swatch-rank-row');
          const chips = renderSwatchMaterialChips(item, ft, rank);
          if (chips && rankRow) rankRow.insertAdjacentHTML('beforebegin', chips);
          else if (chips) card.insertAdjacentHTML('beforeend', chips);
        }
      });
    }

    global.toggleSwatchLowScorePanel = toggleSwatchLowScorePanel;
    global.focusSwatchReviewCandidate = focusSwatchReviewCandidate;
    global.toggleSwatchPickerFavorite = toggleSwatchPickerFavorite;
    global._enhanceSwatchPopupCards = _enhanceSwatchPopupCards;
  }

  global.SPBSwatchPopupActionControls = {
    install: installSwatchPopupActionControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
