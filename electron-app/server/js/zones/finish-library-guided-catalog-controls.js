(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getMetadata = deps.getMetadata || function(id) { return typeof global._getMetadata === 'function' ? global._getMetadata(id) : {}; };
    var getBaseMetadata = deps.getBaseMetadata || function(id) { return typeof global.getBaseMetadata === 'function' ? global.getBaseMetadata(id) : {}; };
    var getPatternMetadata = deps.getPatternMetadata || function(id) { return typeof global.getPatternMetadata === 'function' ? global.getPatternMetadata(id) : {}; };
    var getSearchAliases = deps.getSearchAliases || function() { return global.FINISH_LIBRARY_SEARCH_ALIASES || {}; };
    var getSearchKeywords = deps.getSearchKeywords || function() { return global.SEARCH_KEYWORDS || {}; };
    var smartSearchTokens = deps.smartSearchTokens || function(q) { return String(q || '').split(/\s+/).filter(Boolean); };
    var smartSearchWordMatches = deps.smartSearchWordMatches || function() { return false; };
    var getLibrarySearchQueryState = deps.getLibrarySearchQuery || function() { return ''; };
    var setLibrarySearchQueryState = deps.setLibrarySearchQuery || function() {};
    var getHeroBases = deps.getHeroBases || function() { return global.HERO_BASES || []; };
    var getFavoriteFinishes = deps.getFavoriteFinishes || function() { return new Set(); };
    var getRecentFinishes = deps.getRecentFinishes || function() { return []; };
    var getActiveLibraryTab = deps.getActiveLibraryTab || function() { return global.activeLibraryTab || 'bases'; };
    var getLibraryActiveGroupByTab = deps.getLibraryActiveGroupByTab || function() { return {}; };
    var setLibraryActiveGroup = deps.setLibraryActiveGroup || function(tabId, groupId) { getLibraryActiveGroupByTab()[tabId] = groupId; };
    var renderFinishLibrary = deps.renderFinishLibrary || function() { if (typeof global.renderFinishLibrary === 'function') global.renderFinishLibrary(); };
    var enhanceLibraryCards = deps.enhanceLibraryCards || function() { if (typeof global.enhanceLibraryCards === 'function') global.enhanceLibraryCards(); };
    var getActiveFilterChip = deps.getActiveFilterChip || function() { return global._activeFilterChip; };
    var applySmartFilterChips = deps.applySmartFilterChips || function(items) {
      return typeof global.applySmartFilterChips === 'function' ? global.applySmartFilterChips(items) : items;
    };
    var renderFinishItem = deps.renderFinishItem || function(item, itemType) {
      return typeof global._renderFinishItem === 'function' ? global._renderFinishItem(item, itemType) : '';
    };
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };

    function _cleanLibraryGroupLabel(label) {
      return String(label || '').replace(/^[^A-Za-z0-9]+/, '').replace(/\s+/g, ' ').trim();
    }

    function _getLibrarySearchText(item, type) {
      if (!item) return '';
      var meta = getMetadata(item.id) || {};
      var baseMeta = type === 'base' ? getBaseMetadata(item.id) : {};
      var patternMeta = type === 'pattern' ? getPatternMetadata(item.id) : {};
      var pieces = [
        item.id, item.name, item.desc, item.category,
        meta.family, meta.browserGroup, meta.browserSection, meta.tier,
        baseMeta && baseMeta.family, baseMeta && baseMeta.substrate, baseMeta && baseMeta.coating,
        patternMeta && patternMeta.style, patternMeta && patternMeta.readability, patternMeta && patternMeta.density
      ];
      if (item.tags && Array.isArray(item.tags)) pieces.push(item.tags.join(' '));
      return pieces.filter(Boolean).join(' ').toLowerCase();
    }

    function _libraryItemMatchesSearch(item, type, query) {
      var q = String(query || '').trim().toLowerCase();
      if (!q) return true;
      var hay = _getLibrarySearchText(item, type);
      var words = smartSearchTokens(q);
      var aliasesByWord = getSearchAliases();
      var searchKeywords = getSearchKeywords();
      return words.every(function(word) {
        if (smartSearchWordMatches(hay, word, item.id)) return true;
        if (hay.indexOf(word) >= 0) return true;
        var aliases = aliasesByWord[word] || [];
        if (aliases.some(function(alias) { return hay.indexOf(alias) >= 0; })) return true;
        if (searchKeywords[word] && searchKeywords[word].indexOf(item.id) >= 0) return true;
        return false;
      });
    }

    function _getLibrarySearchQuery() {
      var input = typeof document !== 'undefined' ? document.getElementById('finishSearch') : null;
      return input ? input.value || '' : getLibrarySearchQueryState() || '';
    }

    function _getLibraryGroupPurpose(groupName, tabId, count) {
      var clean = _cleanLibraryGroupLabel(groupName);
      var lower = clean.toLowerCase();
      if (count <= 2) return { strength: 'Thin', purpose: 'Merge or feature carefully' };
      if (/foundation|metallic standard|satin|chrome|candy|pearl|oem/.test(lower)) return { strength: 'Core', purpose: 'Everyday paint behavior' };
      if (/colorshoxx|mortal|neon|shokk|rising sun|viva mexico|chromatic|prizm/.test(lower)) return { strength: 'Showcase', purpose: 'Premium discovery lane' };
      if (/weather|aged|rust|patina|road|salt/.test(lower)) return { strength: 'Weathered', purpose: 'Age, damage, and grime' };
      if (/reactive|vision|fractal|spectral|depth|ghost|halo|physics|effect/.test(lower)) return { strength: 'Advanced', purpose: 'Expressive material effects' };
      if (/brushed|machined|grain|gradient|standalone/.test(lower)) return { strength: 'Review', purpose: 'Buyer-facing category candidate' };
      if (tabId === 'patterns') return { strength: 'Overlay', purpose: 'Graphics and texture layer' };
      return { strength: 'Category', purpose: 'Curated finish family' };
    }

    function _getLibraryFeaturedItems(tabId, items, groupMap) {
      var byId = new Map(items.map(function(item) { return [item.id, item]; }));
      var featured = [];
      function add(id) {
        if (byId.has(id) && !featured.some(function(item) { return item.id === id; })) featured.push(byId.get(id));
      }
      if (tabId === 'bases' && Array.isArray(getHeroBases())) getHeroBases().forEach(function(hero) { add(hero.id); });
      items.forEach(function(item) {
        var meta = getMetadata(item.id) || {};
        if (meta.featured || meta.hero || meta.tier === 'hero') add(item.id);
      });
      if (tabId === 'specials' && groupMap) {
        // [2026-09-05 RETIRED LEDGER] 'Chromatic Flake' and 'Atmosphere' removed from the featured
        // list: both are retired groups (scripts/retired_catalog.json) and must never be surfaced.
        ['\u2605 COLORSHOXX', '\u2605 MORTAL SHOKK', 'RISING SUN', 'VIVA MEXICO', 'Standalone Effects'].forEach(function(groupName) {
          var ids = groupMap[groupName] || [];
          ids.slice(0, 2).forEach(add);
        });
      }
      return featured.slice(0, 18);
    }

    function _setLibraryActiveGroup(groupId) {
      setLibraryActiveGroup(getActiveLibraryTab(), groupId || '__all__');
      renderFinishLibrary();
      enhanceLibraryCards();
    }

    function _renderLibraryRailButton(entry, activeGroup) {
      var active = activeGroup === entry.id;
      var count = typeof entry.count === 'number' ? entry.count : 0;
      return '<button type="button" class="finish-rail-button' + (active ? ' active' : '') + '" data-group="' + escapeHtml(entry.id)
        + '" onclick="_setLibraryActiveGroup(this.dataset.group)" title="' + escapeHtml(entry.label) + '">'
        + '<span class="finish-rail-main"><span class="finish-rail-label">' + escapeHtml(entry.label) + '</span><span class="finish-rail-count">' + count + '</span></span>'
        + '<span class="finish-rail-meta"><span>' + escapeHtml(entry.strength || 'Catalog') + '</span><span>' + escapeHtml(entry.purpose || '') + '</span></span></button>';
    }

    function _renderGuidedFinishCatalog(activeTab, groupMap, groupNames, activeTabId, itemType) {
      var query = _getLibrarySearchQuery();
      setLibrarySearchQueryState(query);
      var featuredItems = _getLibraryFeaturedItems(activeTabId, activeTab.items, groupMap);
      var favorites = getFavoriteFinishes();
      var favoriteItems = activeTab.items.filter(function(item) { return favorites.has(item.id); });
      var recentItems = getRecentFinishes().map(function(id) {
        return activeTab.items.find(function(item) { return item.id === id; });
      }).filter(Boolean);
      var groupEntries = groupNames.map(function(groupName) {
        var ids = new Set(groupMap[groupName] || []);
        var count = activeTab.items.filter(function(item) { return ids.has(item.id); }).length;
        var info = _getLibraryGroupPurpose(groupName, activeTabId, count);
        return { id: groupName, label: _cleanLibraryGroupLabel(groupName), count: count, strength: info.strength, purpose: info.purpose };
      }).filter(function(entry) { return entry.count > 0; });
      var railEntries = [
        { id: '__featured__', label: 'Featured', count: featuredItems.length, strength: 'Showcase', purpose: 'Best first clicks' },
        { id: '__all__', label: 'All', count: activeTab.items.length, strength: 'Catalog', purpose: 'Everything visible' },
        { id: '__favorites__', label: 'Favorites', count: favoriteItems.length, strength: 'Saved', purpose: 'Starred finishes' },
        { id: '__recent__', label: 'Recent', count: recentItems.length, strength: 'History', purpose: 'Last applied' }
      ].filter(function(entry) { return entry.id === '__all__' || entry.count > 0; }).concat(groupEntries);

      var activeGroups = getLibraryActiveGroupByTab();
      var activeGroup = activeGroups[activeTabId];
      if (query) activeGroup = '__all__';
      if (!activeGroup || !railEntries.some(function(entry) { return entry.id === activeGroup; })) activeGroup = featuredItems.length > 0 ? '__featured__' : '__all__';
      setLibraryActiveGroup(activeTabId, activeGroup);

      var visibleItems;
      if (activeGroup === '__featured__') visibleItems = featuredItems;
      else if (activeGroup === '__favorites__') visibleItems = favoriteItems;
      else if (activeGroup === '__recent__') visibleItems = recentItems;
      else if (activeGroup === '__all__') visibleItems = activeTab.items;
      else {
        var activeIds = new Set(groupMap[activeGroup] || []);
        visibleItems = activeTab.items.filter(function(item) { return activeIds.has(item.id); });
      }
      visibleItems = visibleItems.filter(function(item) { return _libraryItemMatchesSearch(item, itemType, query); });
      if (getActiveFilterChip()) visibleItems = applySmartFilterChips(visibleItems);

      var activeEntry = railEntries.find(function(entry) { return entry.id === activeGroup; })
        || { label: 'All', strength: 'Catalog', purpose: 'Everything visible', count: activeTab.items.length };
      var queryNote = query ? '<span class="finish-catalog-query">Search: ' + escapeHtml(query) + '</span>' : '';
      var html = '<div class="finish-guided-catalog" data-active-tab="' + escapeHtml(activeTabId) + '"><div class="finish-category-rail" aria-label="Finish categories">'
        + railEntries.map(function(entry) { return _renderLibraryRailButton(entry, activeGroup); }).join('')
        + '</div><div class="finish-catalog-results"><div class="finish-catalog-heading"><div><div class="finish-catalog-title">'
        + escapeHtml(activeEntry.label) + '</div><div class="finish-catalog-purpose">' + escapeHtml(activeEntry.strength || 'Catalog') + ' - '
        + escapeHtml(activeEntry.purpose || '') + '</div></div><div class="finish-catalog-stats">' + visibleItems.length + ' shown' + queryNote + '</div></div>';
      if (visibleItems.length === 0) {
        html += '<div class="finish-library-empty"><div style="font-size:12px; color:#ddd; margin-bottom:4px;">No finishes match this view.</div>'
          + '<div>Try All, Featured, or a broader search term like chrome, carbon, old, ocean, matte, or vision.</div></div>';
      } else {
        html += '<div class="finish-catalog-grid">' + visibleItems.map(function(item) { return renderFinishItem(item, itemType); }).join('') + '</div>';
      }
      return html + '</div></div>';
    }

    Object.assign(global, {
      _cleanLibraryGroupLabel: _cleanLibraryGroupLabel,
      _getLibrarySearchText: _getLibrarySearchText,
      _libraryItemMatchesSearch: _libraryItemMatchesSearch,
      _getLibrarySearchQuery: _getLibrarySearchQuery,
      _getLibraryGroupPurpose: _getLibraryGroupPurpose,
      _getLibraryFeaturedItems: _getLibraryFeaturedItems,
      _setLibraryActiveGroup: _setLibraryActiveGroup,
      _renderLibraryRailButton: _renderLibraryRailButton,
      _renderGuidedFinishCatalog: _renderGuidedFinishCatalog
    });
  }

  global.SPBZoneFinishLibraryGuidedCatalogControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
