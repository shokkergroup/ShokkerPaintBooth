(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getSwatchUrl = deps.getSwatchUrl || function(id, color, large, size, type) {
      return typeof global.getSwatchUrl === 'function' ? global.getSwatchUrl(id, color, large, size, type) : '';
    };
    var normalizeSwatchTintHex = deps.normalizeSwatchTintHex || function(color, fallback) {
      return typeof global._normalizeSwatchTintHex === 'function' ? global._normalizeSwatchTintHex(color, fallback) : (fallback || '888888');
    };
    var getFinishQualityFlags = deps.getFinishQualityFlags || function(id) {
      return typeof global.getFinishQualityFlags === 'function' ? global.getFinishQualityFlags(id) : [];
    };
    var getBaseMetadata = deps.getBaseMetadata || function(id) {
      return typeof global.getBaseMetadata === 'function' ? global.getBaseMetadata(id) : {};
    };
    var isBaseSponsorSafe = deps.isBaseSponsorSafe || function(id) {
      return typeof global.isBaseSponsorSafe === 'function' ? global.isBaseSponsorSafe(id) : true;
    };
    var getBaseFamily = deps.getBaseFamily || function(id) {
      return typeof global.getBaseFamily === 'function' ? global.getBaseFamily(id) : '';
    };
    var getPatternMetadata = deps.getPatternMetadata || function(id) {
      return typeof global.getPatternMetadata === 'function' ? global.getPatternMetadata(id) : {};
    };
    var isRecommendedCombo = deps.isRecommendedCombo || function(baseId, patternId) {
      return typeof global.isRecommendedCombo === 'function' && global.isRecommendedCombo(baseId, patternId);
    };

    function attr(value) {
      return String(value == null ? '' : value).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function chip(onclick, label, count, tone, active, title) {
      return '<button onclick="' + onclick + '" title="' + attr(title || label) + '" style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid '
        + (active ? tone : '#333') + '; color:' + (active ? tone : '#bbb') + '; background:' + (active ? tone + '18' : '#1a1a1a') + ';">'
        + label + ' <span style="color:' + (active ? '#fff' : '#777') + ';">' + count + '</span></button>';
    }

    function _renderFinishLibraryPanelHtml(ctx) {
      ctx = ctx || {};
      var activeTab = ctx.activeLibraryTab;
      var browseMode = ctx.libraryBrowseMode;
      var modes = ctx.modes || [];
      var tabs = ctx.tabs || [];
      var html = '<div style="display:flex; gap:1px; margin-bottom:3px; flex-wrap:wrap;">'
        + modes.map(function(m) {
          var active = browseMode === m.id;
          return '<button onclick="_libraryBrowseMode=\'' + m.id + '\'; renderFinishLibrary();" style="flex:1; min-width:40px; font-size:7px; padding:3px 2px; border:1px solid '
            + (active ? m.color : '#333') + '; color:' + (active ? m.color : '#666') + '; background:' + (active ? m.color + '15' : 'transparent')
            + '; cursor:pointer; border-radius:3px; font-weight:' + (active ? '700' : '400') + ';" title="' + attr(m.desc) + '">' + m.label + '</button>';
        }).join('') + '</div>';

      html += '<div style="display:flex; gap:2px; margin-bottom:4px;">'
        + tabs.map(function(t) {
          var active = activeTab === t.id;
          return '<button class="btn btn-sm' + (active ? ' active' : '') + '" onclick="activeLibraryTab=\'' + t.id + '\'; renderFinishLibrary();" style="flex:1; font-size:10px; padding:4px 2px; '
            + (active ? 'background:var(--accent); color:#000; border-color:var(--accent);' : '') + '">' + t.label + '</button>';
        }).join('') + '</div>';

      html += '<div style="text-align:center; font-size:8px; color:var(--text-dim); margin-bottom:3px;">'
        + (browseMode === 'all' ? Number(ctx.totalAll || 0).toLocaleString() + ' finishes' : (ctx.totalFiltered || 0) + ' of ' + Number(ctx.totalAll || 0).toLocaleString() + ' finishes')
        + '</div>';

      if (activeTab === 'bases' && Array.isArray(ctx.heroBases) && ctx.heroBases.length > 0) {
        html += '<div class="material-quick-pick" style="margin-bottom:6px; padding:5px 4px; border:1px solid #00ff8830; background:rgba(0,255,136,0.04); border-radius:4px;">'
          + '<div style="font-size:8px; color:#00ff88; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">MATERIAL QUICK-PICK <span style="color:var(--text-dim); font-weight:400;">- what kind of paint?</span></div>'
          + '<div style="display:grid; grid-template-columns:repeat(6,1fr); gap:2px;">';
        ctx.heroBases.forEach(function(hero) {
          var baseEntry = (ctx.bases || []).find(function(base) { return base.id === hero.id; }) || null;
          var heroTint = normalizeSwatchTintHex(null, baseEntry && baseEntry.swatch);
          var swatchUrl = getSwatchUrl(hero.id, heroTint, true, 48, 'base');
          var swatchBg = baseEntry && baseEntry.swatch ? baseEntry.swatch : '#444';
          html += '<div onclick="assignFinishToSelected(\'' + hero.id + '\')" title="' + attr(hero.hint || '') + '" style="cursor:pointer; padding:3px; border:1px solid #333; border-radius:3px; background:#1a1a1a; text-align:center; transition:all 0.15s;" onmouseenter="this.style.borderColor=\'#00ff88\'; this.style.background=\'rgba(0,255,136,0.08)\';" onmouseleave="this.style.borderColor=\'#333\'; this.style.background=\'#1a1a1a\';">'
            + (swatchUrl ? '<img src="' + swatchUrl + '" loading="eager" style="width:100%; aspect-ratio:1; border-radius:2px; object-fit:cover; display:block; margin-bottom:2px;">' : '<div style="width:100%; aspect-ratio:1; border-radius:2px; background:' + swatchBg + '; margin-bottom:2px;"></div>')
            + '<div style="font-size:7px; color:#ddd; line-height:1.1; font-weight:600;">' + hero.label + '</div></div>';
        });
        html += '</div></div>';
      }

      if (activeTab === 'bases' && ctx.featuredCollections) {
        var featuredEntries = Object.keys(ctx.featuredCollections).map(function(name) {
          var ids = Array.isArray(ctx.featuredCollections[name]) ? ctx.featuredCollections[name] : [];
          var count = (ctx.browseModeBases || []).filter(function(base) {
            return ids.indexOf(base.id) >= 0 && getFinishQualityFlags(base.id).length === 0;
          }).length;
          return { name: name, count: count };
        }).filter(function(entry) { return entry.count > 0; });
        if (featuredEntries.length > 0) {
          html += '<div class="featured-collections-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffd70022; background:rgba(255,215,0,0.04); border-radius:4px;"><div style="font-size:8px; color:#ffd700; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">FEATURED COLLECTIONS <span style="color:var(--text-dim); font-weight:400;">- curated finish lanes</span></div><div style="display:flex; flex-wrap:wrap; gap:3px;">'
            + chip("_libraryFeaturedCollectionFilter='all'; renderFinishLibrary();", 'all', (ctx.browseModeBases || []).length, '#ffd700', ctx.libraryFeaturedCollectionFilter === 'all', 'all');
          featuredEntries.forEach(function(entry) {
            html += chip("_libraryFeaturedCollectionFilter='" + attr(entry.name) + "'; renderFinishLibrary();", entry.name, entry.count, '#ffd700', ctx.libraryFeaturedCollectionFilter === entry.name, entry.name);
          });
          html += '</div></div>';
        }
      }

      if (activeTab === 'bases') {
        var collectionBases = ctx.collectionBases || [];
        var qualityCounts = {
          all: collectionBases.length,
          sponsor_safe: collectionBases.filter(function(base) { return isBaseSponsorSafe(base.id) && !/^enh_/.test(base.id || ''); }).length,
          high_impact: collectionBases.filter(function(base) {
            var meta = getBaseMetadata(base.id) || {};
            var sponsorSafe = isBaseSponsorSafe(base.id);
            return !/^enh_/.test(base.id || '') && (!sponsorSafe || (typeof meta.aggression === 'number' && meta.aggression >= 4));
          }).length,
          reference_lab: collectionBases.filter(function(base) { return /^enh_/.test(base.id || ''); }).length,
          audit_flags: collectionBases.filter(function(base) { return getFinishQualityFlags(base.id).length > 0; }).length
        };
        html += '<div class="base-quality-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #8bd7ff22; background:rgba(139,215,255,0.04); border-radius:4px;"><div style="font-size:8px; color:#8bd7ff; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">QUALITY SIGNALS <span style="color:var(--text-dim); font-weight:400;">- practical, showcase, or lab</span></div><div style="display:flex; flex-wrap:wrap; gap:3px;">'
          + chip("_libraryBaseQualityFilter='all'; renderFinishLibrary();", 'All', qualityCounts.all, '#8bd7ff', ctx.libraryBaseQualityFilter === 'all')
          + chip("_libraryBaseQualityFilter='sponsor_safe'; renderFinishLibrary();", 'Sponsor Safe', qualityCounts.sponsor_safe, '#7ae29c', ctx.libraryBaseQualityFilter === 'sponsor_safe')
          + chip("_libraryBaseQualityFilter='high_impact'; renderFinishLibrary();", 'High Impact', qualityCounts.high_impact, '#ffbf7d', ctx.libraryBaseQualityFilter === 'high_impact')
          + chip("_libraryBaseQualityFilter='audit_flags'; renderFinishLibrary();", 'Audit Flags', qualityCounts.audit_flags, '#ff9f9f', ctx.libraryBaseQualityFilter === 'audit_flags')
          + chip("_libraryBaseQualityFilter='reference_lab'; renderFinishLibrary();", 'Reference / Lab', qualityCounts.reference_lab, '#c7c7c7', ctx.libraryBaseQualityFilter === 'reference_lab')
          + '</div></div>';
      }

      if (activeTab === 'specials') {
        var monos = ctx.browseModeMonos || [];
        var specialCounts = {
          all: monos.length,
          known_good: monos.filter(function(item) { return getFinishQualityFlags(item.id).length === 0; }).length,
          audit_flags: monos.filter(function(item) { return getFinishQualityFlags(item.id).length > 0; }).length,
          slow: monos.filter(function(item) { return getFinishQualityFlags(item.id).indexOf('slow') >= 0; }).length
        };
        html += '<div class="special-quality-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffcf7d22; background:rgba(255,207,125,0.04); border-radius:4px;"><div style="font-size:8px; color:#ffcf7d; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">SPECIALS HEALTH <span style="color:var(--text-dim); font-weight:400;">- surface audit flags honestly</span></div><div style="display:flex; flex-wrap:wrap; gap:3px;">'
          + chip("_librarySpecialQualityFilter='all'; renderFinishLibrary();", 'All', specialCounts.all, '#ffcf7d', ctx.librarySpecialQualityFilter === 'all')
          + chip("_librarySpecialQualityFilter='known_good'; renderFinishLibrary();", 'Known Good', specialCounts.known_good, '#7ae29c', ctx.librarySpecialQualityFilter === 'known_good')
          + chip("_librarySpecialQualityFilter='audit_flags'; renderFinishLibrary();", 'Audit Flags', specialCounts.audit_flags, '#ff9f9f', ctx.librarySpecialQualityFilter === 'audit_flags')
          + chip("_librarySpecialQualityFilter='slow'; renderFinishLibrary();", 'Heavy / Slow', specialCounts.slow, '#d5a7ff', ctx.librarySpecialQualityFilter === 'slow')
          + '</div></div>';
      }

      if (activeTab === 'bases' && ctx.familyDisplayNames) {
        var familiesPresent = {};
        (ctx.qualityBases || []).forEach(function(base) {
          var fam = getBaseFamily(base.id);
          familiesPresent[fam] = (familiesPresent[fam] || 0) + 1;
        });
        var order = ctx.libraryBaseFamilyOrder || [];
        var orderedFamilies = order.filter(function(fam) { return familiesPresent[fam]; })
          .concat(Object.keys(familiesPresent).filter(function(fam) { return order.indexOf(fam) < 0; }).sort());
        html += '<div class="finish-family-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #00e5ff22; background:rgba(0,229,255,0.04); border-radius:4px;"><div style="font-size:8px; color:#00e5ff; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">MATERIAL FAMILIES <span style="color:var(--text-dim); font-weight:400;">- filter by behavior</span></div><div style="display:flex; flex-wrap:wrap; gap:3px;">'
          + chip("_libraryBaseFamilyFilter='all'; renderFinishLibrary();", 'All', (ctx.browseModeBases || []).length, '#00e5ff', ctx.libraryBaseFamilyFilter === 'all');
        orderedFamilies.forEach(function(fam) {
          html += chip("_libraryBaseFamilyFilter='" + fam + "'; renderFinishLibrary();", ctx.familyDisplayNames[fam] || fam, familiesPresent[fam], '#00e5ff', ctx.libraryBaseFamilyFilter === fam);
        });
        html += '</div></div>';
      }

      var zoneCtx = ctx.libraryZoneContext;
      if (activeTab === 'bases' && zoneCtx) {
        var tone = zoneCtx.sponsorSafe ? '#6be28b' : '#ffb366';
        var similarHtml = zoneCtx.similarBases && zoneCtx.similarBases.length > 0
          ? zoneCtx.similarBases.map(function(base) {
            return '<button onclick="assignFinishToSelected(\'' + base.id + '\')" style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid #333; color:#ddd; background:#1a1a1a;" title="' + attr(base.desc || '') + '">' + base.name + '</button>';
          }).join('')
          : '<span style="font-size:8px; color:var(--text-dim);">No curated alternates yet</span>';
        html += '<div class="finish-context-card" style="margin-bottom:6px; padding:6px; border:1px solid ' + tone + '33; background:rgba(255,255,255,0.02); border-radius:4px;"><div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:4px;"><div style="font-size:9px; color:#ddd; font-weight:700;">CURRENT ZONE BASE: ' + zoneCtx.base.name + '</div><button onclick="_libraryBaseFamilyFilter=\'' + zoneCtx.familyId + '\'; renderFinishLibrary();" style="font-size:8px; padding:2px 6px; border-radius:999px; cursor:pointer; border:1px solid ' + tone + '; color:' + tone + '; background:transparent;">' + zoneCtx.familyLabel + '</button></div><div style="display:flex; gap:10px; flex-wrap:wrap; font-size:8px; color:var(--text-dim); margin-bottom:5px;"><span>Tier: <span style="color:#ddd;">' + (zoneCtx.meta.tier || 'n/a') + '</span></span><span>Intensity: <span style="color:#ddd;">' + (zoneCtx.meta.aggression || 'n/a') + '/5</span></span><span style="color:' + tone + ';">' + (zoneCtx.sponsorSafe ? 'Sponsor-safe' : 'High-impact / sponsor caution') + '</span></div><div style="font-size:8px; color:var(--text-dim); margin-bottom:3px;">Try these similar finishes:</div><div style="display:flex; flex-wrap:wrap; gap:4px;">' + similarHtml + '</div></div>';
      }

      if (activeTab === 'patterns') {
        var patternStyleCounts = {};
        var recommendedCount = 0;
        var textFriendlyCount = 0;
        (ctx.browseModePatterns || []).forEach(function(pattern) {
          var meta = getPatternMetadata(pattern.id) || {};
          if (meta.style) patternStyleCounts[meta.style] = (patternStyleCounts[meta.style] || 0) + 1;
          if (meta.readability === 'good') textFriendlyCount += 1;
          if (zoneCtx && zoneCtx.base && isRecommendedCombo(zoneCtx.base.id, pattern.id)) recommendedCount += 1;
        });
        var styleKeys = Object.keys(patternStyleCounts).sort(function(a, b) {
          if (patternStyleCounts[b] !== patternStyleCounts[a]) return patternStyleCounts[b] - patternStyleCounts[a];
          return a.localeCompare(b);
        });
        html += '<div class="pattern-guidance-filter" style="margin-bottom:6px; padding:5px 4px; border:1px solid #ffd70022; background:rgba(255,215,0,0.04); border-radius:4px;"><div style="font-size:8px; color:#ffd700; font-weight:700; margin-bottom:4px; padding-left:2px; letter-spacing:0.5px;">PATTERN FILTERS <span style="color:var(--text-dim); font-weight:400;">- readability and fit</span></div><div style="display:flex; flex-wrap:wrap; gap:3px;">'
          + chip("_libraryPatternFilter='all'; renderFinishLibrary();", 'All', (ctx.browseModePatterns || []).length, '#ffd700', ctx.libraryPatternFilter === 'all');
        if (zoneCtx && zoneCtx.base) html += chip("_libraryPatternFilter='recommended'; renderFinishLibrary();", 'Recommended', recommendedCount, '#ffd700', ctx.libraryPatternFilter === 'recommended');
        html += chip("_libraryPatternFilter='text_friendly'; renderFinishLibrary();", 'Text Friendly', textFriendlyCount, '#ffd700', ctx.libraryPatternFilter === 'text_friendly');
        styleKeys.forEach(function(styleId) {
          html += chip("_libraryPatternFilter='style:" + styleId + "'; renderFinishLibrary();", styleId.replace(/_/g, ' '), patternStyleCounts[styleId], '#ffd700', ctx.libraryPatternFilter === 'style:' + styleId);
        });
        html += '</div></div>';
      }

      if (activeTab === 'patterns' && zoneCtx && zoneCtx.currentPattern) {
        var currentMeta = zoneCtx.currentPatternMeta || {};
        var matchTone = zoneCtx.currentPatternRecommended ? '#6be28b' : '#ffb366';
        var readabilityTone = currentMeta.readability === 'good' ? '#6be28b' : (currentMeta.readability === 'fair' ? '#ece58c' : '#ff9f9f');
        html += '<div class="pattern-current-status" style="margin-bottom:6px; padding:6px; border:1px solid ' + matchTone + '33; background:rgba(255,255,255,0.02); border-radius:4px;"><div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:4px;"><div style="font-size:9px; color:#ddd; font-weight:700;">CURRENT PATTERN: ' + zoneCtx.currentPattern.name + '</div><span style="font-size:8px; padding:2px 6px; border-radius:999px; border:1px solid ' + matchTone + '; color:' + matchTone + ';">' + (zoneCtx.currentPatternRecommended ? 'Recommended Match' : 'Try a Better Match') + '</span></div><div style="display:flex; gap:10px; flex-wrap:wrap; font-size:8px; color:var(--text-dim);"><span>Readability: <span style="color:' + readabilityTone + ';">' + (currentMeta.readability || 'unknown') + '</span></span><span>Style: <span style="color:#ddd;">' + (currentMeta.style || 'n/a') + '</span></span><span>Density: <span style="color:#ddd;">' + (currentMeta.density || 'n/a') + '</span></span></div></div>';
      }

      if (activeTab === 'patterns' && zoneCtx && zoneCtx.recommendedPatterns && zoneCtx.recommendedPatterns.length > 0) {
        var recHtml = zoneCtx.recommendedPatterns.map(function(pattern) {
          var pmeta = getPatternMetadata(pattern.id) || {};
          var readability = pmeta.readability ? ' - ' + pmeta.readability + ' text' : '';
          return '<button onclick="assignFinishToSelected(\'' + pattern.id + '\')" title="' + attr(pattern.desc || '') + '" style="font-size:8px; padding:3px 6px; border-radius:999px; cursor:pointer; border:1px solid #333; color:#ddd; background:#1a1a1a;">' + pattern.name + readability + '</button>';
        }).join('');
        html += '<div class="pattern-advisor" style="margin-bottom:6px; padding:6px; border:1px solid #ffd70033; background:rgba(255,215,0,0.04); border-radius:4px;"><div style="font-size:9px; color:#ffd700; font-weight:700; margin-bottom:4px;">PATTERN ADVISOR</div><div style="font-size:8px; color:#ddd; margin-bottom:4px;">Recommended over <span style="color:#fff;">' + zoneCtx.base.name + '</span>:</div><div style="display:flex; flex-wrap:wrap; gap:4px;">' + recHtml + '</div></div>';
      }

      return html;
    }

    Object.assign(global, {
      _renderFinishLibraryPanelHtml: _renderFinishLibraryPanelHtml
    });
  }

  global.SPBZoneFinishLibraryPanelControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
