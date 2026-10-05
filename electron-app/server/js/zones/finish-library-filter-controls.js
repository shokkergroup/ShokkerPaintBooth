(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getLibraryBaseFamilyFilter = deps.getLibraryBaseFamilyFilter || function() { return 'all'; };
    var getBaseFamily = deps.getBaseFamily || function(id) {
      return typeof global.getBaseFamily === 'function' ? global.getBaseFamily(id) : '';
    };
    var getLibraryFeaturedCollectionFilter = deps.getLibraryFeaturedCollectionFilter || function() { return 'all'; };
    var getFeaturedCollections = deps.getFeaturedCollections || function() { return global.FEATURED_COLLECTIONS || {}; };
    var getFinishQualityFlags = deps.getFinishQualityFlags || function(id) {
      return typeof global.getFinishQualityFlags === 'function' ? global.getFinishQualityFlags(id) : [];
    };
    var getLibraryBaseQualityFilter = deps.getLibraryBaseQualityFilter || function() { return 'all'; };
    var getBaseMetadata = deps.getBaseMetadata || function(id) {
      return typeof global.getBaseMetadata === 'function' ? global.getBaseMetadata(id) : {};
    };
    var isBaseSponsorSafe = deps.isBaseSponsorSafe || function(id) {
      return typeof global.isBaseSponsorSafe === 'function' ? global.isBaseSponsorSafe(id) : true;
    };
    var getLibrarySpecialQualityFilter = deps.getLibrarySpecialQualityFilter || function() { return 'all'; };
    var getLibraryPatternFilter = deps.getLibraryPatternFilter || function() { return 'all'; };
    var getPatternMetadata = deps.getPatternMetadata || function(id) {
      return typeof global.getPatternMetadata === 'function' ? global.getPatternMetadata(id) : {};
    };
    var isRecommendedCombo = deps.isRecommendedCombo || function(baseId, patternId) {
      return typeof global.isRecommendedCombo === 'function' && global.isRecommendedCombo(baseId, patternId);
    };
    var getLibraryBrowseMode = deps.getLibraryBrowseMode || function() { return 'all'; };
    var getMetadata = deps.getMetadata || function(id) {
      return typeof global._getMetadata === 'function' ? global._getMetadata(id) : null;
    };
    var getHeroBases = deps.getHeroBases || function() { return global.HERO_BASES || []; };

    function _isUserPickerItem(item) {
      if (!item || !item.id) return false;
      var id = String(item.id);
      if (id.indexOf('ui_') === 0 || id.indexOf('gd_') === 0) return true;
      if (item.category === 'SHOKK DROP') return true;
      if (item.category && String(item.category).indexOf('Guest Designer') >= 0) return true;
      if (Array.isArray(item.tags)) {
        return item.tags.some(function(tag) {
          return tag === 'user-import' || tag === 'shokk-drop' || tag === 'guest-designer' || tag === 'spec-overlay';
        });
      }
      return false;
    }

    function _filterBasesByFamily(items) {
      if (getLibraryBaseFamilyFilter() === 'all') return items;
      return items.filter(function(item) {
        return getBaseFamily(item.id) === getLibraryBaseFamilyFilter();
      });
    }

    function _filterBasesByFeaturedCollection(items) {
      var filter = getLibraryFeaturedCollectionFilter();
      var collections = getFeaturedCollections();
      if (filter === 'all') return items;
      if (!collections || !collections[filter]) return items;
      var allowed = new Set(collections[filter]);
      return items.filter(function(item) {
        var hasQualityFlags = getFinishQualityFlags(item.id).length > 0;
        return allowed.has(item.id) && !hasQualityFlags;
      });
    }

    function _filterBasesByQuality(items) {
      var filter = getLibraryBaseQualityFilter();
      if (filter === 'all') return items;
      return items.filter(function(item) {
        var meta = getBaseMetadata(item.id) || {};
        var sponsorSafe = isBaseSponsorSafe(item.id);
        var isReference = /^enh_/.test(item.id || '');
        var qualityFlags = getFinishQualityFlags(item.id);
        if (filter === 'sponsor_safe') return sponsorSafe && !isReference;
        if (filter === 'high_impact') {
          return !isReference && (!sponsorSafe || (typeof meta.aggression === 'number' && meta.aggression >= 4));
        }
        if (filter === 'reference_lab') return isReference;
        if (filter === 'audit_flags') return qualityFlags.length > 0;
        return true;
      });
    }

    function _filterSpecialsByQuality(items) {
      var filter = getLibrarySpecialQualityFilter();
      if (filter === 'all') return items;
      return items.filter(function(item) {
        var flags = getFinishQualityFlags(item.id);
        if (filter === 'audit_flags') return flags.length > 0;
        if (filter === 'slow') return flags.indexOf('slow') >= 0;
        if (filter === 'known_good') return flags.length === 0;
        return true;
      });
    }

    function _filterPatternsByGuidance(items, zoneCtx) {
      var filter = getLibraryPatternFilter();
      if (filter === 'all') return items;
      return items.filter(function(item) {
        var meta = getPatternMetadata(item.id) || {};
        if (filter === 'recommended') return !!(zoneCtx && zoneCtx.base && isRecommendedCombo(zoneCtx.base.id, item.id));
        if (filter === 'text_friendly') return meta.readability === 'good';
        if (filter.indexOf('style:') === 0) return meta.style === filter.split(':', 2)[1];
        return true;
      });
    }

    function _filterByBrowseMode(items, tabId) {
      var browseMode = getLibraryBrowseMode();
      if (browseMode === 'all') return items;
      return items.filter(function(item) {
        if (_isUserPickerItem(item)) return true;
        var meta = getMetadata(item.id);
        var hasQualityFlags = getFinishQualityFlags(item.id).length > 0;
        if (!meta) return browseMode === 'all';
        switch (browseMode) {
          case 'quick':
            if (tabId === 'bases' && Array.isArray(getHeroBases()) && getHeroBases().length > 0) {
              return getHeroBases().some(function(hero) { return hero.id === item.id; }) && !hasQualityFlags;
            }
            return (meta.hero || (meta.featured && meta.readability >= 75)) && !hasQualityFlags;
          case 'materials': return meta.browserGroup === 'Materials' || meta.browserGroup === 'Utility';
          case 'specials': return meta.browserGroup === 'Specials';
          case 'events': return meta.browserGroup === 'Surface Events';
          case 'advanced': return meta.advanced || meta.browserGroup === 'Advanced';
          default: return true;
        }
      });
    }

    function _sortByMetadata(items) {
      return items.slice().sort(function(a, b) {
        var ma = getMetadata(a.id), mb = getMetadata(b.id);
        var aFlags = getFinishQualityFlags(a.id);
        var bFlags = getFinishQualityFlags(b.id);
        if (!!aFlags.length !== !!bFlags.length) return aFlags.length - bFlags.length;
        var pa = ma ? ma.sortPriority : 50, pb = mb ? mb.sortPriority : 50;
        return pb - pa;
      });
    }

    function _sortPatternsForZoneContext(items, zoneCtx) {
      if (!zoneCtx || !zoneCtx.base) return items;
      var readabilityRank = { good: 0, fair: 1, poor: 2 };
      return items.slice().sort(function(a, b) {
        var aRecommended = isRecommendedCombo(zoneCtx.base.id, a.id) ? 0 : 1;
        var bRecommended = isRecommendedCombo(zoneCtx.base.id, b.id) ? 0 : 1;
        if (aRecommended !== bRecommended) return aRecommended - bRecommended;
        var aMeta = getPatternMetadata(a.id) || {};
        var bMeta = getPatternMetadata(b.id) || {};
        var aReadability = Object.prototype.hasOwnProperty.call(readabilityRank, aMeta.readability) ? readabilityRank[aMeta.readability] : 3;
        var bReadability = Object.prototype.hasOwnProperty.call(readabilityRank, bMeta.readability) ? readabilityRank[bMeta.readability] : 3;
        if (aReadability !== bReadability) return aReadability - bReadability;
        return (a.name || '').localeCompare((b.name || ''), undefined, { sensitivity: 'base' });
      });
    }

    Object.assign(global, {
      _filterBasesByFamily: _filterBasesByFamily,
      _filterBasesByFeaturedCollection: _filterBasesByFeaturedCollection,
      _filterBasesByQuality: _filterBasesByQuality,
      _filterSpecialsByQuality: _filterSpecialsByQuality,
      _filterPatternsByGuidance: _filterPatternsByGuidance,
      _filterByBrowseMode: _filterByBrowseMode,
      _isUserPickerItem: _isUserPickerItem,
      _sortByMetadata: _sortByMetadata,
      _sortPatternsForZoneContext: _sortPatternsForZoneContext
    });
  }

  global.SPBZoneFinishLibraryFilterControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
