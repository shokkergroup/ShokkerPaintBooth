(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getRegisteredFinishes = deps.getRegisteredFinishes || function() { return null; };
    var setRegisteredFinishes = deps.setRegisteredFinishes || function() {};
    var getRegistryLoadAttempted = deps.getRegistryLoadAttempted || function() { return false; };
    var setRegistryLoadAttempted = deps.setRegistryLoadAttempted || function() {};
    var getApiBaseUrl = deps.getApiBaseUrl || function() { return global.ShokkerAPI && global.ShokkerAPI.baseUrl || ''; };
    var isFavorite = deps.isFavorite || function(id) { return typeof global.isFavorite === 'function' && global.isFavorite(id); };
    var getSwatchUrl = deps.getSwatchUrl || function(id, color, forceSplit, size, type) {
      return typeof global.getSwatchUrl === 'function' ? global.getSwatchUrl(id, color, forceSplit, size, type) : '';
    };
    var normalizeSwatchTintHex = deps.normalizeSwatchTintHex || function(colorHex, fallback) {
      return typeof global._normalizeSwatchTintHex === 'function' ? global._normalizeSwatchTintHex(colorHex, fallback) : (fallback || '888888');
    };
    var pickerSwatchFinishKey = deps.pickerSwatchFinishKey || function(id, finishType) {
      return typeof global._pickerSwatchFinishKey === 'function' ? global._pickerSwatchFinishKey(id, finishType) : id;
    };
    var getFinishLibraryZoneContext = deps.getFinishLibraryZoneContext || function() {
      return typeof global._getFinishLibraryZoneContext === 'function' ? global._getFinishLibraryZoneContext() : null;
    };
    var getBaseMetadata = deps.getBaseMetadata || function(id) {
      return typeof global.getBaseMetadata === 'function' ? global.getBaseMetadata(id) : null;
    };
    var getPatternMetadata = deps.getPatternMetadata || function(id) {
      return typeof global.getPatternMetadata === 'function' ? global.getPatternMetadata(id) : null;
    };
    var getBaseFamily = deps.getBaseFamily || function(id) {
      return typeof global.getBaseFamily === 'function' ? global.getBaseFamily(id) : '';
    };
    var getFamilyDisplayName = deps.getFamilyDisplayName || function(id) {
      return global.FAMILY_DISPLAY_NAMES && (global.FAMILY_DISPLAY_NAMES[id] || id) || id;
    };
    var isBaseSponsorSafe = deps.isBaseSponsorSafe || function(id) {
      return typeof global.isBaseSponsorSafe === 'function' ? global.isBaseSponsorSafe(id) : true;
    };
    var getFinishQualityFlags = deps.getFinishQualityFlags || function(id) {
      return typeof global.getFinishQualityFlags === 'function' ? global.getFinishQualityFlags(id) : [];
    };
    var isRecommendedCombo = deps.isRecommendedCombo || function(baseId, patternId) {
      return typeof global.isRecommendedCombo === 'function' && global.isRecommendedCombo(baseId, patternId);
    };
    var getPatterns = deps.getPatterns || function() { return global.PATTERNS || []; };
    var getBases = deps.getBases || function() { return global.BASES || []; };
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };
    var getLibrarySearchText = deps.getLibrarySearchText || function(item, type) {
      return typeof global._getLibrarySearchText === 'function' ? global._getLibrarySearchText(item, type) : ((item && (item.name || item.id)) || '');
    };

    function _loadRegistryStatus() {
      if (getRegisteredFinishes()) return;
      global.fetch(getApiBaseUrl() + '/api/finish-registry-status', { signal: AbortSignal.timeout(8000) })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.registered) {
            var registered = new Set(data.registered);
            setRegisteredFinishes(registered);
            console.log('[Registry] ' + registered.size + ' registered finishes loaded');
          }
        })
        .catch(function() { setRegisteredFinishes(null); });
    }

    function chipHtml(text, tone) {
      return '<span style="font-size:7px; padding:1px 5px; border-radius:999px; border:1px solid '
        + tone.border + '; color:' + tone.color + '; background:' + tone.bg + ';">' + escapeHtml(text) + '</span>';
    }

    function _renderFinishItem(item, type) {
      if (!getRegistryLoadAttempted()) {
        setRegistryLoadAttempted(true);
        _loadRegistryStatus();
      }
      var registeredFinishes = getRegisteredFinishes();
      var isRegistered = !registeredFinishes || registeredFinishes.has(item.id);
      var isFav = isFavorite(item.id);
      var starIcon = isFav ? '&#9733;' : '&#9734;';
      var starColor = isFav ? 'color:#ffaa00;' : 'color:var(--text-dim);';
      var libFt = type === 'mono' ? 'monolithic' : type;
      var libTint = normalizeSwatchTintHex(null, item.swatch);
      var libKey = pickerSwatchFinishKey(item.id, libFt);
      var swatchUrl = getSwatchUrl(libKey, libTint, true, 48, libFt);
      var zoneCtx = getFinishLibraryZoneContext();
      var baseMeta = type === 'base' ? getBaseMetadata(item.id) : null;
      var patternMeta = type === 'pattern' ? getPatternMetadata(item.id) : null;
      var familyId = baseMeta ? getBaseFamily(item.id) : '';
      var familyLabel = familyId ? getFamilyDisplayName(familyId) : '';
      var sponsorSafe = baseMeta ? isBaseSponsorSafe(item.id) : true;
      var isReferenceBase = type === 'base' && /^enh_/.test(item.id || '');
      var isEnhancedBase = type === 'base' && /^enh_/.test(item.id || '');
      var qualityFlags = getFinishQualityFlags(item.id) || [];
      var isRecommendedPattern = type === 'pattern' && zoneCtx && zoneCtx.base && isRecommendedCombo(zoneCtx.base.id, item.id);
      var inlineChips = [];

      if (type === 'base' && familyLabel) {
        inlineChips.push(chipHtml(familyLabel, { border: '#333', color: '#9ad9ff', bg: '#091722' }));
        if (baseMeta && baseMeta.tier) {
          var tierTone = baseMeta.tier === 'hero'
            ? { border: '#7a6214', color: '#ffd86a', bg: 'rgba(255,215,0,0.08)' }
            : baseMeta.tier === 'premium'
              ? { border: '#5a3c83', color: '#c9a7ff', bg: 'rgba(165,102,255,0.08)' }
              : { border: '#334', color: '#d7d7e8', bg: 'rgba(255,255,255,0.03)' };
          inlineChips.push(chipHtml(String(baseMeta.tier).toUpperCase(), tierTone));
        }
        if (baseMeta && typeof baseMeta.aggression === 'number') {
          var aggressionLabel = baseMeta.aggression >= 4 ? 'Wild' : (baseMeta.aggression <= 1 ? 'Subtle' : (baseMeta.aggression === 2 ? 'Balanced' : 'Bold'));
          var aggressionTone = baseMeta.aggression >= 4
            ? { border: '#7a2f14', color: '#ffb37d', bg: 'rgba(255,128,64,0.08)' }
            : baseMeta.aggression <= 1
              ? { border: '#245d35', color: '#7ae29c', bg: 'rgba(0,255,136,0.06)' }
              : { border: '#3f4b6e', color: '#c6d6ff', bg: 'rgba(96,128,255,0.08)' };
          inlineChips.push(chipHtml(aggressionLabel, aggressionTone));
        }
        inlineChips.push(chipHtml(sponsorSafe ? 'Sponsor Safe' : 'Sponsor Caution', sponsorSafe
          ? { border: '#245d35', color: '#7ae29c', bg: 'rgba(0,255,136,0.06)' }
          : { border: '#6b4922', color: '#ffbf7d', bg: 'rgba(255,170,68,0.06)' }));
        if (baseMeta && Array.isArray(baseMeta.best_with)) {
          var bestWithId = baseMeta.best_with.find(function(id) { return id && id !== 'none'; });
          var bestWithPattern = bestWithId ? getPatterns().find(function(pattern) { return pattern.id === bestWithId; }) : null;
          if (bestWithPattern) inlineChips.push(chipHtml('Best with ' + bestWithPattern.name, { border: '#2f4b67', color: '#9fd1ff', bg: 'rgba(64,128,255,0.08)' }));
        }
        if (baseMeta && Array.isArray(baseMeta.similar_to)) {
          var similarId = baseMeta.similar_to.find(function(id) { return id && id !== item.id; });
          var similarBase = similarId ? getBases().find(function(base) { return base.id === similarId; }) : null;
          if (similarBase) inlineChips.push(chipHtml('Similar to ' + similarBase.name, { border: '#4a4a68', color: '#d6d6f7', bg: 'rgba(160,160,255,0.05)' }));
        }
        if (isReferenceBase) inlineChips.push(chipHtml(isEnhancedBase ? 'Enhanced Lab' : 'Reference', { border: '#555', color: '#c7c7c7', bg: 'rgba(255,255,255,0.03)' }));
      }

      if (type === 'pattern' && patternMeta) {
        if (isRecommendedPattern) inlineChips.push(chipHtml('Recommended', { border: '#7a6214', color: '#ffd86a', bg: 'rgba(255,215,0,0.08)' }));
        if (patternMeta.readability) {
          var readabilityTone = patternMeta.readability === 'good'
            ? { border: '#245d35', color: '#7ae29c', bg: 'rgba(0,255,136,0.06)' }
            : patternMeta.readability === 'fair'
              ? { border: '#5f5f23', color: '#ece58c', bg: 'rgba(255,235,59,0.06)' }
              : { border: '#6b2b2b', color: '#ff9f9f', bg: 'rgba(255,82,82,0.06)' };
          var readabilityLabel = patternMeta.readability === 'good' ? 'Text Friendly' : (patternMeta.readability === 'fair' ? 'Medium Readability' : 'Busy / Low Readability');
          inlineChips.push(chipHtml(readabilityLabel, readabilityTone));
        }
      }

      if ((type === 'base' || type === 'mono') && qualityFlags.length > 0) {
        var qualityChips = {
          broken: { label: 'Audit: Broken', border: '#7a2b2b', color: '#ff9f9f', bg: 'rgba(255,82,82,0.08)' },
          ggx_risk: { label: 'Audit: GGX Risk', border: '#7a5a14', color: '#ffd36a', bg: 'rgba(255,193,7,0.08)' },
          spec_flat: { label: 'Audit: Flat Spec', border: '#4b4b4b', color: '#d8d8d8', bg: 'rgba(255,255,255,0.05)' },
          slow: { label: 'Audit: Slow', border: '#5f2f83', color: '#d5a7ff', bg: 'rgba(165,102,255,0.08)' }
        };
        qualityFlags.forEach(function(flag) {
          var chip = qualityChips[flag];
          if (chip) inlineChips.push(chipHtml(chip.label, chip));
        });
      }

      var safeId = escapeHtml(item.id);
      var safeJsId = JSON.stringify(item.id || '');
      var swatchHtml = swatchUrl
        ? '<img class="finish-swatch-canvas" src="' + swatchUrl + '" loading="eager" decoding="sync" style="width:40px;height:40px;border-radius:4px;object-fit:cover;flex-shrink:0;">'
        : '<div class="finish-swatch-canvas" style="width:40px;height:40px;border-radius:4px;background:' + (item.swatch || '#444') + ';flex-shrink:0;"></div>';
      return "<div class=\"finish-item finish-catalog-card\" onclick='assignFinishToSelected(" + safeJsId + ")'"
        + " onmouseenter='showFinishPopup(event, " + safeJsId + ")' onmouseleave='hideFinishPopup()'"
        + ' data-name="' + escapeHtml(item.name).toLowerCase() + '" data-desc="' + escapeHtml(item.desc).toLowerCase() + '"'
        + ' data-id="' + safeId + '" data-search="' + escapeHtml(getLibrarySearchText(item, type)).toLowerCase() + '">'
        + swatchHtml
        + '<div class="finish-item-info"><div class="finish-item-name">' + escapeHtml(item.name)
        + (!isRegistered ? ' <span style="font-size:7px;color:#ff8800;border:1px solid #ff8800;border-radius:2px;padding:0 2px;vertical-align:middle;" title="Preview - this finish uses a generic render path">PREVIEW</span>' : '')
        + '</div><div class="finish-item-desc">' + escapeHtml(item.desc) + '</div>'
        + (inlineChips.length > 0 ? '<div class="finish-item-chips" style="display:flex; flex-wrap:wrap; gap:3px; margin-top:3px;">' + inlineChips.join('') + '</div>' : '')
        + "</div><span onclick='toggleFavorite(" + safeJsId + ", event)' title=\"" + (isFav ? 'Remove from favorites' : 'Add to favorites') + '" style="cursor:pointer; font-size:14px; ' + starColor + ' padding:0 4px; flex-shrink:0; transition:color 0.15s;">' + starIcon + '</span>'
        + '<span class="finish-item-assign">' + (type === 'base' ? 'Set Base' : (type === 'pattern' ? 'Set Pattern' : 'Assign')) + '</span></div>';
    }

    Object.assign(global, {
      _loadRegistryStatus: _loadRegistryStatus,
      _renderFinishItem: _renderFinishItem
    });
  }

  global.SPBZoneFinishLibraryRenderItemControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
