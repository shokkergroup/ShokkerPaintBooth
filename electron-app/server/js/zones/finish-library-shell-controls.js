(function(global) {
  'use strict';

  var LIBRARY_BASE_FAMILY_ORDER = [
    'chrome', 'satin_chrome', 'metallic', 'pearl', 'candy', 'gloss',
    'satin', 'matte', 'ceramic', 'weathered', 'brushed', 'vinyl',
    'carbon', 'industrial', 'optical', 'exotic'
  ];

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var getZones = deps.getZones || function() { return []; };
    var getSelectedZoneIndex = deps.getSelectedZoneIndex || function() { return -1; };
    var getBases = deps.getBases || function() { return []; };
    var getPatterns = deps.getPatterns || function() { return []; };
    var getMonolithics = deps.getMonolithics || function() { return []; };
    var getBaseGroups = deps.getBaseGroups || function() { return {}; };
    var getPatternGroups = deps.getPatternGroups || function() { return {}; };
    var getSpecialGroups = deps.getSpecialGroups || function() { return {}; };
    var getFinishMetadata = deps.getFinishMetadata || function() { return {}; };
    var getFeaturedCollections = deps.getFeaturedCollections || function() { return null; };
    var getFamilyDisplayNames = deps.getFamilyDisplayNames || function() { return null; };
    var getHeroBases = deps.getHeroBases || function() { return []; };
    var getActiveLibraryTab = deps.getActiveLibraryTab || function() { return 'bases'; };
    var getLibraryBrowseMode = deps.getLibraryBrowseMode || function() { return 'all'; };
    var getLibraryFeaturedCollectionFilter = deps.getLibraryFeaturedCollectionFilter || function() { return 'all'; };
    var getLibraryBaseQualityFilter = deps.getLibraryBaseQualityFilter || function() { return 'all'; };
    var getLibrarySpecialQualityFilter = deps.getLibrarySpecialQualityFilter || function() { return 'all'; };
    var getLibraryBaseFamilyFilter = deps.getLibraryBaseFamilyFilter || function() { return 'all'; };
    var getLibraryPatternFilter = deps.getLibraryPatternFilter || function() { return 'all'; };

    function getFinishQualityFlags(id) {
      var flags = deps.getFinishBrowserQualityFlags ? (deps.getFinishBrowserQualityFlags() || {}) : {};
      return flags[id] ? flags[id].slice() : [];
    }

    function getMetadata(id) {
      var metadata = getFinishMetadata() || {};
      return metadata[id] || null;
    }

    function getFinishLibraryZoneContext() {
      var zones = getZones();
      var selectedZoneIndex = getSelectedZoneIndex();
      if (!Array.isArray(zones) || selectedZoneIndex < 0 || selectedZoneIndex >= zones.length) return null;
      var zone = zones[selectedZoneIndex];
      if (!zone || !zone.base) return null;
      var bases = getBases();
      var patterns = getPatterns();
      var base = Array.isArray(bases) ? bases.find(function(b) { return b.id === zone.base; }) : null;
      if (!base) return null;
      var meta = deps.getBaseMetadata ? (deps.getBaseMetadata(base.id) || {}) : {};
      var familyId = deps.getBaseFamily ? deps.getBaseFamily(base.id) : (meta.family || 'other');
      var familyNames = getFamilyDisplayNames() || {};
      var recommendedPatterns = deps.getRecommendedPatterns
        ? deps.getRecommendedPatterns(base.id).map(function(id) {
          return Array.isArray(patterns) ? patterns.find(function(p) { return p.id === id; }) : null;
        }).filter(Boolean).slice(0, 6)
        : [];
      var currentPattern = zone.pattern && zone.pattern !== 'none' && Array.isArray(patterns)
        ? patterns.find(function(p) { return p.id === zone.pattern; }) || null
        : null;
      var currentPatternMeta = currentPattern && deps.getPatternMetadata ? deps.getPatternMetadata(currentPattern.id) : {};
      var similarBases = Array.isArray(meta.similar_to) ? meta.similar_to.slice() : [];
      if (similarBases.length === 0 && deps.getFamilyBases) {
        similarBases = deps.getFamilyBases(base.id).filter(function(id) { return id !== base.id; });
      }
      similarBases = similarBases.map(function(id) {
        return Array.isArray(bases) ? bases.find(function(b) { return b.id === id; }) : null;
      }).filter(Boolean).slice(0, 6);
      return {
        zone: zone,
        base: base,
        meta: meta,
        familyId: familyId,
        familyLabel: familyNames[familyId] || familyId || 'Other',
        sponsorSafe: deps.isBaseSponsorSafe ? deps.isBaseSponsorSafe(base.id) : true,
        recommendedPatterns: recommendedPatterns,
        similarBases: similarBases,
        currentPattern: currentPattern,
        currentPatternMeta: currentPatternMeta,
        currentPatternRecommended: !!(currentPattern && deps.isRecommendedCombo && deps.isRecommendedCombo(base.id, currentPattern.id))
      };
    }

    function renderFinishLibrary() {
      var container = doc && doc.getElementById ? doc.getElementById('finishLibrary') : null;
      if (!container) return;
      var activeLibraryTab = getActiveLibraryTab();
      var bases = getBases();
      var patterns = getPatterns();
      var monolithics = getMonolithics();
      var groupMaps = { bases: getBaseGroups(), patterns: getPatternGroups(), specials: getSpecialGroups() };
      var libraryZoneContext = getFinishLibraryZoneContext();
      var browseModeBases = deps.sortByMetadata(deps.filterByBrowseMode(bases, 'bases'));
      var collectionBases = deps.filterBasesByFeaturedCollection(browseModeBases);
      var qualityBases = deps.filterBasesByQuality(collectionBases);
      var filteredBases = deps.filterBasesByFamily(qualityBases);
      var browseModePatterns = deps.sortPatternsForZoneContext(deps.sortByMetadata(deps.filterByBrowseMode(patterns, 'patterns')), libraryZoneContext);
      var filteredPatterns = deps.filterPatternsByGuidance(browseModePatterns, libraryZoneContext);
      var browseModeMonos = deps.sortByMetadata(deps.filterByBrowseMode(monolithics, 'specials'));
      var filteredMonos = deps.filterSpecialsByQuality(browseModeMonos);
      var tabs = [
        { id: 'bases', label: 'Bases (' + filteredBases.length + ')', items: filteredBases, type: 'base' },
        { id: 'patterns', label: 'Patterns (' + filteredPatterns.length + ')', items: filteredPatterns, type: 'pattern' },
        { id: 'specials', label: 'Specials (' + filteredMonos.length + ')', items: filteredMonos, type: 'mono' }
      ];
      var html = deps.renderFinishLibraryPanelHtml({
        activeLibraryTab: activeLibraryTab,
        libraryBrowseMode: getLibraryBrowseMode(),
        modes: [
          { id: 'quick', label: 'Quick Start', color: '#00ff88', desc: 'Best picks, high confidence' },
          { id: 'materials', label: 'Materials', color: '#00e5ff', desc: 'Chrome, carbon, ceramic, pearl...' },
          { id: 'specials', label: 'Specials', color: '#ffd700', desc: 'Color shifts, prizm, micro-flake' },
          { id: 'events', label: 'Surface', color: '#ff8844', desc: 'Clearcoat, weathering, aging' },
          { id: 'all', label: 'All', color: '#aaa', desc: 'Full library' },
          { id: 'advanced', label: 'Adv', color: '#888', desc: 'Experimental and niche' }
        ],
        tabs: tabs,
        totalFiltered: filteredBases.length + filteredPatterns.length + filteredMonos.length,
        totalAll: bases.length + patterns.length + monolithics.length,
        heroBases: getHeroBases(),
        bases: bases,
        featuredCollections: getFeaturedCollections(),
        familyDisplayNames: getFamilyDisplayNames(),
        libraryBaseFamilyOrder: LIBRARY_BASE_FAMILY_ORDER,
        browseModeBases: browseModeBases,
        collectionBases: collectionBases,
        qualityBases: qualityBases,
        browseModeMonos: browseModeMonos,
        browseModePatterns: browseModePatterns,
        libraryFeaturedCollectionFilter: getLibraryFeaturedCollectionFilter(),
        libraryBaseQualityFilter: getLibraryBaseQualityFilter(),
        librarySpecialQualityFilter: getLibrarySpecialQualityFilter(),
        libraryBaseFamilyFilter: getLibraryBaseFamilyFilter(),
        libraryPatternFilter: getLibraryPatternFilter(),
        libraryZoneContext: libraryZoneContext
      });
      var activeTab = tabs.find(function(t) { return t.id === activeLibraryTab; });
      if (!activeTab) { container.innerHTML = html; return; }
      var groupMap = groupMaps[activeLibraryTab] || {};
      var groupNames = deps.getFinishLibraryGroupNames(activeLibraryTab, groupMap);
      deps.applyFinishLibraryDefaultGroups(activeLibraryTab, groupNames);
      deps.finishLibraryFinalizeRender({ container: container, html: html, activeTab: activeTab, groupMap: groupMap, groupNames: groupNames, activeTabId: activeLibraryTab, itemType: activeTab.type });
    }

    Object.assign(global, {
      getFinishQualityFlags: getFinishQualityFlags,
      _getMetadata: getMetadata,
      _getFinishLibraryZoneContext: getFinishLibraryZoneContext,
      renderFinishLibrary: renderFinishLibrary
    });

    return {
      getFinishQualityFlags: getFinishQualityFlags,
      getMetadata: getMetadata,
      getFinishLibraryZoneContext: getFinishLibraryZoneContext,
      renderFinishLibrary: renderFinishLibrary,
      libraryBaseFamilyOrder: LIBRARY_BASE_FAMILY_ORDER.slice()
    };
  }

  global.SPBZoneFinishLibraryShellControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
