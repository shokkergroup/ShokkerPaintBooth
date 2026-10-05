(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getLastLibraryTabForDefaults = deps.getLastLibraryTabForDefaults || function() { return null; };
    var setLastLibraryTabForDefaults = deps.setLastLibraryTabForDefaults || function() {};
    var getExpandedGroups = deps.getExpandedGroups || function() { return new Set(); };
    var renderGuidedFinishCatalog = deps.renderGuidedFinishCatalog || function(activeTab, groupMap, groupNames, activeTabId, itemType) {
      return typeof global._renderGuidedFinishCatalog === 'function'
        ? global._renderGuidedFinishCatalog(activeTab, groupMap, groupNames, activeTabId, itemType)
        : '';
    };
    var renderQuickAccessBar = deps.renderQuickAccessBar || function() {
      if (typeof global.renderQuickAccessBar === 'function') global.renderQuickAccessBar();
    };
    var enhanceGuidedCatalogCards = deps.enhanceGuidedCatalogCards || function() {
      if (typeof global.enhanceGuidedCatalogCards === 'function') global.enhanceGuidedCatalogCards();
    };
    var enhanceZoneCardsMaterial = deps.enhanceZoneCardsMaterial || function() {
      if (typeof global.enhanceZoneCardsMaterial === 'function') global.enhanceZoneCardsMaterial();
    };
    var renderSmartFilterChips = deps.renderSmartFilterChips || function(container) {
      if (typeof global.renderSmartFilterChips === 'function') global.renderSmartFilterChips(container);
    };
    var setLibrarySearchQuery = deps.setLibrarySearchQuery || function(value) { global._librarySearchQuery = value || ''; };
    var getActiveLibraryTab = deps.getActiveLibraryTab || function() { return global.activeLibraryTab || 'bases'; };
    var getLibraryActiveGroupByTab = deps.getLibraryActiveGroupByTab || function() { return {}; };
    var renderFinishLibrary = deps.renderFinishLibrary || function() { if (typeof global.renderFinishLibrary === 'function') global.renderFinishLibrary(); };
    var enhanceLibraryCards = deps.enhanceLibraryCards || function() { if (typeof global.enhanceLibraryCards === 'function') global.enhanceLibraryCards(); };
    var getCategoryCollapsed = deps.getCategoryCollapsed || function() { return global.categoryCollapsed || {}; };

    function _getFinishLibraryGroupNames(activeTabId, groupMap) {
      var groupNames = Object.keys(groupMap || {});
      if (activeTabId === 'bases') {
        var baseGroupOrder = { 'Foundation': 0, 'Foundation EFX': 1 };
        return groupNames.sort(function(a, b) {
          var ao = Object.prototype.hasOwnProperty.call(baseGroupOrder, a) ? baseGroupOrder[a] : 99;
          var bo = Object.prototype.hasOwnProperty.call(baseGroupOrder, b) ? baseGroupOrder[b] : 99;
          if (ao !== bo) return ao - bo;
          return a.localeCompare(b);
        });
      }
      if (activeTabId === 'patterns') {
        return groupNames.sort(function(a, b) {
          return a === 'Abstract & Experimental' ? -1 : b === 'Abstract & Experimental' ? 1 : a.localeCompare(b);
        });
      }
      return groupNames;
    }

    function _applyFinishLibraryDefaultGroups(activeTabId, groupNames) {
      if (getLastLibraryTabForDefaults() === activeTabId) return;
      var expandedGroups = getExpandedGroups();
      if (expandedGroups && typeof expandedGroups.clear === 'function') expandedGroups.clear();
      if (activeTabId === 'bases' && groupNames.indexOf('Foundation') >= 0) expandedGroups.add('Foundation');
      if (activeTabId === 'patterns' && groupNames.indexOf('Abstract & Experimental') >= 0) expandedGroups.add('Abstract & Experimental');
      setLastLibraryTabForDefaults(activeTabId);
    }

    function _finishLibraryFinalizeRender(ctx) {
      ctx = ctx || {};
      if (!ctx.container || !ctx.activeTab) return;
      ctx.container.innerHTML = (ctx.html || '') + renderGuidedFinishCatalog(ctx.activeTab, ctx.groupMap || {}, ctx.groupNames || [], ctx.activeTabId, ctx.itemType);
      try { renderQuickAccessBar(); } catch (_) {}
      try { enhanceGuidedCatalogCards(); } catch (_) {}
      try { enhanceZoneCardsMaterial(); } catch (_) {}
      var catalogResults = typeof document !== 'undefined' ? document.querySelector('.finish-catalog-results') : null;
      if (catalogResults) {
        try { renderSmartFilterChips(catalogResults); } catch (_) {}
      }
    }

    function filterFinishes(query) {
      setLibrarySearchQuery(String(query || ''));
      if (String(query || '').trim()) {
        getLibraryActiveGroupByTab()[getActiveLibraryTab()] = '__all__';
      }
      renderFinishLibrary();
      enhanceLibraryCards();
    }

    function toggleCategory(cat) {
      var collapsed = getCategoryCollapsed();
      collapsed[cat] = !collapsed[cat];
      renderFinishLibrary();
      enhanceLibraryCards();
    }

    Object.assign(global, {
      _getFinishLibraryGroupNames: _getFinishLibraryGroupNames,
      _applyFinishLibraryDefaultGroups: _applyFinishLibraryDefaultGroups,
      _finishLibraryFinalizeRender: _finishLibraryFinalizeRender,
      filterFinishes: filterFinishes,
      toggleCategory: toggleCategory
    });
  }

  global.SPBZoneFinishLibraryRenderFlowControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
