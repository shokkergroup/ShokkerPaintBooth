(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = global.document;
    var getRecentFinishes = deps.getRecentFinishes || function() { return []; };
    var setRecentFinishes = deps.setRecentFinishes || function() {};
    var getFavoriteFinishes = deps.getFavoriteFinishes || function() { return new Set(); };
    var getShowFavoritesOnly = deps.getShowFavoritesOnly || function() { return false; };
    var setShowFavoritesOnly = deps.setShowFavoritesOnly || function() {};
    var getExpandedGroups = deps.getExpandedGroups || function() { return new Set(); };
    var getActiveLibraryTab = deps.getActiveLibraryTab || function() { return 'bases'; };
    var renderFinishLibrary = deps.renderFinishLibrary || function() {};
    var enhanceLibraryCards = deps.enhanceLibraryCards || function() {};
    var assignFinishToSelected = deps.assignFinishToSelected || function() {};
    var getBases = deps.getBases || function() { return global.BASES || []; };
    var getPatterns = deps.getPatterns || function() { return global.PATTERNS || []; };
    var getMonolithics = deps.getMonolithics || function() { return global.MONOLITHICS || []; };
    var getGroupMaps = deps.getGroupMaps || function() {
      return {
        bases: global.BASE_GROUPS || {},
        patterns: global.PATTERN_GROUPS || {},
        specials: global.SPECIAL_GROUPS || {}
      };
    };

    function saveJson(key, value) {
      try { global.localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
    }

    function _trackRecentFinish(id) {
      var recent = getRecentFinishes().filter(function(f) { return f !== id; });
      recent.unshift(id);
      if (recent.length > 12) recent.pop();
      setRecentFinishes(recent);
      saveJson('spb_recent_finishes', recent);
    }

    function findFinishItem(id) {
      var base = getBases().find(function(b) { return b.id === id; });
      var pat = getPatterns().find(function(p) { return p.id === id; });
      var mono = getMonolithics().find(function(m) { return m.id === id; });
      return base || pat || mono || null;
    }

    function renderQuickAccessBar() {
      var container = doc && doc.getElementById('finishLibrary');
      if (!container) return;

      var existing = container.querySelector('.spb-quick-access-bar');
      if (existing) existing.remove();

      var favorites = getFavoriteFinishes();
      var recent = getRecentFinishes().slice(0, 8);
      var favs = Array.from(favorites || []).slice(0, 6);
      var seen = new Set();
      var items = [];
      recent.concat(favs).forEach(function(id) {
        if (!id || seen.has(id)) return;
        seen.add(id);
        var item = findFinishItem(id);
        if (item) items.push({ id: id, name: item.name || id, isFav: favorites && favorites.has(id) });
      });

      if (items.length === 0) return;

      var bar = doc.createElement('div');
      bar.className = 'spb-quick-access-bar';
      bar.innerHTML = '<div class="spb-quick-access-header">'
        + '<div class="spb-quick-access-title">Quick Access</div>'
        + '<div class="spb-quick-access-meta">' + items.length + ' recent - ' + Array.from(favorites || []).length + ' fav</div>'
        + '</div><div class="spb-quick-access-scroller"></div>';

      var scroller = bar.querySelector('.spb-quick-access-scroller');
      items.forEach(function(entry) {
        var item = findFinishItem(entry.id) || {};
        var sw = doc.createElement('div');
        sw.className = 'spb-qa-swatch';
        sw.title = entry.name + (entry.isFav ? ' favorite' : '');
        var c1 = item.swatch || '#3a4556';
        var c2 = item.swatch2 || null;
        var c3 = item.swatch3 || null;
        if (c2 && c3) sw.style.background = 'linear-gradient(135deg, ' + c1 + ' 0%, ' + c2 + ' 50%, ' + c3 + ' 100%)';
        else if (c2) sw.style.background = 'linear-gradient(135deg, ' + c1 + ' 0%, ' + c2 + ' 100%)';
        else sw.style.background = 'linear-gradient(145deg, ' + c1 + ', color-mix(in srgb, ' + c1 + ' 82%, black))';
        sw.style.borderColor = entry.isFav ? 'rgba(255,204,102,0.65)' : 'rgba(255,255,255,0.18)';
        if (entry.isFav) {
          var star = doc.createElement('div');
          star.className = 'qa-star';
          star.textContent = '*';
          sw.appendChild(star);
        }
        var label = doc.createElement('div');
        label.className = 'qa-label';
        label.textContent = entry.name.length > 18 ? entry.name.slice(0, 17) + '...' : entry.name;
        sw.appendChild(label);
        sw.onclick = function(e) {
          e.stopPropagation();
          assignFinishToSelected(entry.id);
          sw.style.transition = 'none';
          sw.style.boxShadow = '0 0 0 3px rgba(0,229,255,0.6)';
          setTimeout(function() {
            if (sw && sw.parentNode) {
              sw.style.transition = '';
              sw.style.boxShadow = '';
            }
          }, 220);
        };
        scroller.appendChild(sw);
      });

      container.insertBefore(bar, container.firstChild);
    }

    function toggleFavorite(finishId, event) {
      if (event) { event.stopPropagation(); event.preventDefault(); }
      var favorites = getFavoriteFinishes();
      if (favorites.has(finishId)) favorites.delete(finishId);
      else favorites.add(finishId);
      saveJson('shokker_favorites', Array.from(favorites));
      if (global.SPBFinishPreferences) global.SPBFinishPreferences.favorite(finishId, favorites.has(finishId));
      renderFinishLibrary();
      enhanceLibraryCards();
    }

    function isFavorite(finishId) {
      return getFavoriteFinishes().has(finishId);
    }

    function toggleFavoritesOnly() {
      var next = !getShowFavoritesOnly();
      setShowFavoritesOnly(next);
      var btn = doc && doc.getElementById('btnFavoritesOnly');
      if (btn) {
        btn.textContent = next ? '*' : '+';
        btn.style.color = next ? '#ffaa00' : '';
        btn.style.borderColor = next ? '#ffaa00' : '';
      }
      renderFinishLibrary();
      enhanceLibraryCards();
      enhanceLibraryCards();
    }

    function toggleLibraryGroup(groupName) {
      var expandedGroups = getExpandedGroups();
      if (expandedGroups.has(groupName)) expandedGroups.delete(groupName);
      else expandedGroups.add(groupName);
      renderFinishLibrary();
      enhanceLibraryCards();
      enhanceLibraryCards();
    }

    function expandAllLibraryGroups() {
      var groupMaps = getGroupMaps();
      var groupMap = groupMaps[getActiveLibraryTab()] || {};
      var expandedGroups = getExpandedGroups();
      Object.keys(groupMap).forEach(function(gn) { expandedGroups.add(gn); });
      renderFinishLibrary();
      enhanceLibraryCards();
      enhanceLibraryCards();
    }

    function collapseAllLibraryGroups() {
      getExpandedGroups().clear();
      renderFinishLibrary();
      enhanceLibraryCards();
      enhanceLibraryCards();
    }

    Object.assign(global, {
      _trackRecentFinish: _trackRecentFinish,
      renderQuickAccessBar: renderQuickAccessBar,
      toggleFavorite: toggleFavorite,
      isFavorite: isFavorite,
      toggleFavoritesOnly: toggleFavoritesOnly,
      toggleLibraryGroup: toggleLibraryGroup,
      expandAllLibraryGroups: expandAllLibraryGroups,
      collapseAllLibraryGroups: collapseAllLibraryGroups
    });
  }

  global.SPBZoneFinishLibraryStateControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
