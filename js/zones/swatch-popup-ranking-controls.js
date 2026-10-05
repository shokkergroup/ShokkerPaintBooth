(function(global) {
  'use strict';

  function installSwatchPopupRankingControls(deps) {
    deps = deps || {};
    const getBases = deps.getBases || function() { return []; };
    const getMonolithics = deps.getMonolithics || function() { return []; };
    const getPatterns = deps.getPatterns || function() { return []; };
    const getCatalogScorecardMetrics = deps.getCatalogScorecardMetrics || function() { return {}; };
    const getPickerOwnerRatings = deps.getPickerOwnerRatings || function() { return {}; };
    const getMetadata = deps.getMetadata || function() { return null; };
    const getPatternMetadata = deps.getPatternMetadata || function() { return null; };
    const getFinishQualityFlags = deps.getFinishQualityFlags || function() { return []; };
    const getLibrarySearchText = deps.getLibrarySearchText || function() { return ''; };
    const getFinishLibrarySearchAliases = deps.getFinishLibrarySearchAliases || function() { return {}; };
    const getFavoriteFinishes = deps.getFavoriteFinishes || function() { return new Set(); };
    const getPickerInternalReviewUiEnabled = deps.getPickerInternalReviewUiEnabled || function() { return false; };
    const isFavorite = deps.isFavorite || function() { return false; };
    const getFinishType = deps.getFinishType || function() { return 'base'; };
    const renderSwatchSquare = deps.renderSwatchSquare || function() { return ''; };
    const escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };

    function _getSwatchItemById(id, typeHint) {
      const cleanId = String(id || '').replace(/^mono:/, '');
      if (!cleanId) return null;
      const patterns = getPatterns();
      if (typeHint === 'pattern') {
        const pattern = patterns.find(function(p) { return p.id === cleanId; });
        if (pattern) return { item: pattern, type: 'pattern', selectValue: pattern.id };
      }
      const base = getBases().find(function(b) { return b.id === cleanId; });
      if (base) return { item: base, type: 'base', selectValue: base.id };
      const mono = getMonolithics().find(function(m) { return m.id === cleanId; });
      if (mono) return { item: mono, type: 'monolithic', selectValue: 'mono:' + mono.id };
      const pattern = patterns.find(function(p) { return p.id === cleanId; });
      if (pattern) return { item: pattern, type: 'pattern', selectValue: pattern.id };
      return null;
    }

    function _rankClamp(value, min, max) {
      const lo = typeof min === 'number' ? min : 30;
      const hi = typeof max === 'number' ? max : 96;
      const n = Number(value);
      if (!Number.isFinite(n)) return lo;
      return Math.round(Math.max(lo, Math.min(hi, n)));
    }

    function _rankKeywordScore(text, weights) {
      const q = String(text || '').toLowerCase();
      return Object.keys(weights || {}).reduce(function(sum, key) {
        return q.indexOf(key) >= 0 ? sum + Number(weights[key] || 0) : sum;
      }, 0);
    }

    function _catalogScorecardTable() {
      return getCatalogScorecardMetrics() || {};
    }

    function _catalogScorecardKey(itemId, type) {
      const id = String(itemId || '').replace(/^mono:/, '');
      const t = type === 'mono' ? 'monolithic' : type;
      if (t === 'spec-pattern') return 'spec_pattern:' + id;
      return String(t || 'base') + ':' + id;
    }

    function _getCatalogScorecardRow(itemId, type) {
      const table = _catalogScorecardTable();
      const id = String(itemId || '').replace(/^mono:/, '');
      const candidates = [
        _catalogScorecardKey(id, type),
        'base:' + id,
        'monolithic:' + id,
        'pattern:' + id,
        'spec_pattern:' + id
      ];
      for (let i = 0; i < candidates.length; i += 1) {
        if (table[candidates[i]]) return table[candidates[i]];
      }
      return null;
    }

    function _pickerOwnerRatingTable() {
      return getPickerOwnerRatings() || {};
    }

    function _pickerRatingType(type) {
      if (type === 'mono') return 'monolithic';
      if (type === 'spec-pattern') return 'spec_pattern';
      return type || 'base';
    }

    function _getPickerOwnerRating(itemId, type) {
      const id = String(itemId || '').replace(/^mono:/, '');
      if (!id) return null;
      const table = _pickerOwnerRatingTable();
      const t = _pickerRatingType(type);
      const keys = [t + ':' + id, id, 'monolithic:' + id, 'base:' + id, 'pattern:' + id, 'spec_pattern:' + id];
      for (let i = 0; i < keys.length; i += 1) {
        if (table[keys[i]]) return table[keys[i]];
      }
      return null;
    }

    function _rankTierForOverall(score, specStyle) {
      const n = _rankClamp(score, 0, 100);
      if (specStyle) return n >= 86 ? 'Elite' : (n >= 78 ? 'Strong' : (n >= 66 ? 'Watch' : 'Rework'));
      return n >= 88 ? 'S' : n >= 80 ? 'A' : n >= 70 ? 'B' : n >= 60 ? 'C' : 'Fix';
    }

    function _applyPickerOwnerRating(rank, item, type) {
      if (!rank || !item) return rank;
      const owner = _getPickerOwnerRating(item.id, type);
      if (!owner || !owner.scores) return rank;
      const scores = owner.scores || {};
      const out = Object.assign({}, rank);
      const fields = ['patternDesign', 'specDetail', 'renderTime', 'intentFit', 'sponsorSafety'];
      fields.forEach(function(field) {
        if (typeof scores[field] === 'number') out[field] = _rankClamp(scores[field], 0, 100);
      });
      if (typeof scores.uniqueness === 'number') {
        out.distinctness = _rankClamp(scores.uniqueness, 0, 100);
        out.uniqueness = out.distinctness;
      }
      if (typeof scores.distinctness === 'number') {
        out.distinctness = _rankClamp(scores.distinctness, 0, 100);
        out.uniqueness = out.distinctness;
      }
      if (typeof scores.overall === 'number') {
        out.overall = _rankClamp(scores.overall, 0, 100);
      } else {
        out.overall = _rankClamp(
          out.patternDesign * 0.18 +
          (out.distinctness || out.uniqueness || 60) * 0.16 +
          out.specDetail * 0.22 +
          out.renderTime * 0.14 +
          out.intentFit * 0.18 +
          out.sponsorSafety * 0.12,
          0,
          100
        );
      }
      out.measuredOverall = rank.overall;
      out.confidence = 'Owner';
      out.source = 'owner';
      out.ownerStatus = owner.status || 'rated';
      out.ownerNote = owner.notes || '';
      out.ownerSource = owner.source || '';
      out.priority = owner.status || out.priority || '';
      out.reasonFlags = [rank.reasonFlags, 'owner_' + String(out.ownerStatus).replace(/[^a-z0-9]+/gi, '_').toLowerCase()].filter(Boolean).join(', ');
      out.tier = _rankTierForOverall(out.overall, type === 'spec_pattern' || type === 'spec-pattern');
      return out;
    }

    function _scorecardSmooth(value, low, high) {
      if (high <= low) return 0;
      const t = Math.max(0, Math.min(1, (Number(value || 0) - low) / (high - low)));
      return (3 * t * t - 2 * t * t * t) * 100;
    }

    function _descriptionIntentScore(item, meta, row, type) {
      const desc = String((item && item.desc) || '');
      const name = String((item && item.name) || (item && item.id) || '');
      const q = (name + ' ' + desc + ' ' + String((row && row.category) || '') + ' ' + String((meta && meta.family) || '')).toLowerCase();
      let score = desc ? 56 : 36;
      const nameWords = name.toLowerCase().split(/[^a-z0-9]+/).filter(function(w) {
        return w.length > 3 && ['finish', 'paint', 'base', 'pattern', 'special'].indexOf(w) < 0;
      });
      const descLower = desc.toLowerCase();
      score += Math.min(24, nameWords.filter(function(w) { return descLower.indexOf(w) >= 0; }).length * 6);
      if (desc.length > 100) score += 10;
      else if (desc.length > 55) score += 6;
      const flags = String((row && row.reasonFlags) || '').toLowerCase();
      if (/low_paint_quality|low_fine_detail|low_micro_detail|macro_dominated/.test(flags)) score -= 10;
      if (/low_spec_quality|flat_spec_finish/.test(flags)) score -= 8;
      if (/broken_render/.test(flags) || (row && row.status && row.status !== 'OK')) score -= 30;
      if (/chrome|metal|metallic|flake|pearl|candy|clearcoat|gloss|matte|satin|weather|rust|carbon|weave|fiber|prism|holo|chameleon|brushed|machined/.test(q)) score += 6;
      if (type === 'pattern' && /pattern|overlay|stripe|weave|grid|circuit|mesh|flag|flame|texture/.test(q)) score += 5;
      return _rankClamp(score, 8, 96);
    }

    function _scorecardUniqueness(row, meta, item, type) {
      const distinctness = typeof meta.distinctness === 'number' ? meta.distinctness : row.overallQuality;
      const colorScore = _scorecardSmooth(row.paintColorPopulation, type === 'pattern' ? 2 : 3, type === 'pattern' ? 18 : 24);
      const fineScore = _scorecardSmooth(row.paintResidualEnergy, 0.004, 0.034);
      const channelScore = _scorecardSmooth(row.specChannelIndependence, 0.05, 0.45);
      const blockPenalty = _scorecardSmooth(row.paintBlockEnergy, 0.18, 0.42) * 0.14;
      return _rankClamp(distinctness * 0.38 + colorScore * 0.18 + fineScore * 0.24 + channelScore * 0.12 + row.paintQuality * 0.08 - blockPenalty, 6, 98);
    }

    function _scorecardSponsorSafety(row, meta, item, type) {
      const readability = typeof meta.readability === 'number' ? meta.readability : 64;
      const q = String([item && item.id, item && item.name, item && item.desc, row.category, type].filter(Boolean).join(' ')).toLowerCase();
      const busyPenalty = _scorecardSmooth(row.paintMacroEnergy, 0.045, 0.115) * (row.paintMicroMacroRatio < 0.42 ? 0.18 : 0.08);
      const blockPenalty = _scorecardSmooth(row.paintBlockEnergy, 0.18, 0.42) * 0.14;
      const readabilityBoost = _rankKeywordScore(q, {
        racing: 5, stripe: 7, carbon: 6, satin: 5, matte: 5, gloss: 3, foundation: 8,
        skull: -10, horror: -10, chaos: -10, grunge: -7, lightning: -7, plasma: -7
      });
      return _rankClamp(readability * 0.48 + row.paintQuality * 0.22 + row.speedScore * 0.10 + 16 + readabilityBoost - busyPenalty - blockPenalty, 8, 96);
    }

    function _catalogRankingFromScorecard(item, type, row, meta, patternMeta) {
      if (!row) return null;
      if (row.status && row.status !== 'OK') {
        return {
          overall: 12,
          tier: 'Broken',
          patternDesign: 10,
          distinctness: 10,
          specDetail: 10,
          renderTime: 10,
          intentFit: 8,
          sponsorSafety: 12,
          confidence: 'Broken',
          source: 'scorecard',
          priority: row.priority || 'BROKEN',
          reasonFlags: row.reasonFlags || 'broken_render',
          estimated2048Ms: row.estimated2048Ms || 0
        };
      }
      const paintQuality = _rankClamp(row.paintQuality, 0, 100);
      const specQuality = _rankClamp(row.specQuality, 0, 100);
      const speedScore = _rankClamp(row.speedScore, 0, 100);
      const patternDesign = _rankClamp(type === 'pattern' || type === 'spec_pattern'
        ? paintQuality * 0.70 + _scorecardSmooth(row.paintResidualEnergy, 0.004, 0.034) * 0.18 + _scorecardSmooth(row.paintColorPopulation, 2, 18) * 0.12
        : paintQuality * 0.78 + (typeof meta.score === 'number' ? meta.score : paintQuality) * 0.12 + _scorecardSmooth(row.paintFineEnergy, 0.004, 0.045) * 0.10,
        4, 98);
      const distinctness = _scorecardUniqueness(row, meta || {}, item, type);
      const specDetail = _rankClamp(specQuality * 0.76 + _scorecardSmooth(row.specMRange + row.specRRange + row.specCcRange, 40, 360) * 0.14 + _scorecardSmooth(row.specChannelIndependence, 0.05, 0.45) * 0.10, 4, 98);
      const intentFit = _descriptionIntentScore(item, meta || {}, row, type);
      const sponsorSafety = _scorecardSponsorSafety(row, meta || {}, item, type);
      const overall = _rankClamp(
        patternDesign * 0.18 +
        distinctness * 0.16 +
        specDetail * 0.22 +
        speedScore * 0.14 +
        intentFit * 0.18 +
        sponsorSafety * 0.12,
        4,
        98
      );
      const tier = overall >= 88 ? 'S' : overall >= 80 ? 'A' : overall >= 70 ? 'B' : overall >= 60 ? 'C' : 'Fix';
      return {
        overall,
        tier,
        patternDesign,
        distinctness,
        specDetail,
        renderTime: speedScore,
        intentFit,
        sponsorSafety,
        confidence: 'Measured',
        source: 'scorecard',
        priority: row.priority || '',
        reasonFlags: row.reasonFlags || '',
        estimated2048Ms: row.estimated2048Ms || 0,
        paintQuality,
        scorecardOverall: row.overallQuality
      };
    }

    function _catalogRankingForItem(item, type) {
      const meta = getMetadata(item.id) || {};
      const patternMeta = type === 'pattern' ? (getPatternMetadata(item.id) || {}) : {};
      const scorecardRow = _getCatalogScorecardRow(item.id, type);
      const measuredRank = _catalogRankingFromScorecard(item, type, scorecardRow, meta, patternMeta);
      if (measuredRank) return _applyPickerOwnerRating(measuredRank, item, type);
      const qualityFlags = getFinishQualityFlags(item.id) || [];
      const hasAudit = typeof meta.score === 'number' || typeof meta.readability === 'number' || typeof meta.distinctness === 'number';
      const hasPatternEvidence = !!(patternMeta.style || patternMeta.density || patternMeta.readability);
      const desc = String(item.desc || '');
      const q = (String(item.id || '') + ' ' + String(item.name || '') + ' ' + desc + ' ' + String(meta.family || '') + ' ' + String(meta.browserSection || '') + ' ' + String(item.category || '')).toLowerCase();
      const readability = _rankClamp(typeof meta.readability === 'number'
        ? meta.readability
        : (patternMeta.readability === 'good' ? 84 : patternMeta.readability === 'fair' ? 70 : patternMeta.readability === 'poor' ? 48 : 62));
      const distinctness = _rankClamp(typeof meta.distinctness === 'number' ? meta.distinctness : (hasAudit ? meta.score : 60));
      const auditScore = _rankClamp(typeof meta.score === 'number' ? meta.score : ((readability + distinctness) / 2));
      const patternDesign = _rankClamp(type === 'pattern'
        ? (readability * 0.50 + distinctness * 0.30 + (patternMeta.style ? 10 : 0) + (patternMeta.density ? 5 : 0) + ((Number(patternMeta.aggression || 0) || 0) * 2))
        : (auditScore * 0.55 + distinctness * 0.25 + _rankKeywordScore(q, {
          premium: 8, hero: 8, chrome: 6, pearl: 6, candy: 6, flake: 5, brushed: 5, weathered: 4,
          foundation: -8, plain: -8, simple: -5, basic: -5
        })));
      const nameWords = String(item.name || '').toLowerCase().split(/[^a-z0-9]+/).filter(function(w) { return w.length > 3; });
      const descLower = desc.toLowerCase();
      const nameHits = nameWords.filter(function(w) { return descLower.indexOf(w) >= 0; }).length;
      const intentFit = _rankClamp((desc ? 56 : 42) + Math.min(24, nameHits * 7) + (desc.length > 70 ? 10 : desc.length > 35 ? 5 : 0) + (meta.family && q.indexOf(String(meta.family).toLowerCase()) >= 0 ? 6 : 0));
      const specDetail = qualityFlags.indexOf('spec_flat') >= 0 ? 35 : _rankClamp(
        auditScore * 0.38 + distinctness * 0.22 + 24 + _rankKeywordScore(q, {
          chrome: 10, metallic: 9, metal: 8, flake: 9, pearl: 8, candy: 7, clearcoat: 8, gloss: 6,
          roughness: 8, satin: 6, matte: 4, spec: 6, carbon: 5, weathered: 5, plain: -10, flat: -8
        })
      );
      const renderTime = qualityFlags.indexOf('slow') >= 0 ? 38 : _rankClamp(
        (meta.fastRender || meta.fast_render ? 90 : 76) + _rankKeywordScore(q, {
          fractal: -10, gravity: -8, particle: -6, constellation: -6, holographic: -5, complex: -8,
          simple: 6, stripe: 4, solid: 6, foundation: 8, carbon: 4
        })
      );
      const sponsorSafety = _rankClamp(readability + _rankKeywordScore(q, {
        racing: 6, stripe: 8, carbon: 8, satin: 6, matte: 6, gloss: 4, foundation: 8,
        skull: -12, horror: -12, chaos: -12, busy: -10, grunge: -8, lightning: -8, plasma: -8
      }));
      const overall = Math.round(
        patternDesign * 0.18 +
        distinctness * 0.18 +
        specDetail * 0.20 +
        renderTime * 0.12 +
        intentFit * 0.20 +
        sponsorSafety * 0.12
      );
      const evidencePoints = (hasAudit ? 2 : 0) + (hasPatternEvidence ? 1 : 0) + (desc.length > 40 ? 1 : 0) - (qualityFlags.length ? 1 : 0);
      const confidence = evidencePoints >= 3 ? 'Audit' : evidencePoints >= 1 ? 'Est' : 'Low';
      const adjustedOverall = _rankClamp(confidence === 'Low' ? Math.min(overall, 72) : overall);
      const tier = adjustedOverall >= 88 ? 'S' : adjustedOverall >= 80 ? 'A' : adjustedOverall >= 70 ? 'B' : adjustedOverall >= 60 ? 'C' : 'Fix';
      return _applyPickerOwnerRating({ overall: adjustedOverall, tier, patternDesign, distinctness, specDetail, renderTime, intentFit, sponsorSafety, confidence }, item, type);
    }

    function _pickerRankingMetricSummary(rank, type) {
      var metrics = [
        { key: 'patternDesign', short: type === 'spec_pattern' ? 'Design' : 'Look', label: type === 'spec_pattern' ? 'Pattern design' : 'Visual design', value: Number(rank && rank.patternDesign) || 0 },
        { key: 'distinctness', short: 'Unique', label: 'Uniqueness', value: Number(rank && (rank.distinctness || rank.uniqueness)) || 0 },
        { key: 'specDetail', short: 'Spec', label: 'Spec detail', value: Number(rank && rank.specDetail) || 0 },
        { key: 'renderTime', short: 'Speed', label: 'Render speed', value: Number(rank && rank.renderTime) || 0 },
        { key: 'intentFit', short: 'Fit', label: 'Name/description fit', value: Number(rank && rank.intentFit) || 0 },
        { key: 'sponsorSafety', short: 'Text', label: 'Sponsor/text safety', value: Number(rank && rank.sponsorSafety) || 0 }
      ].filter(function(m) { return m.value > 0; });
      if (!metrics.length) {
        return {
          tone: 'watch',
          headline: 'Needs evidence',
          detail: 'No usable ranking signals yet.',
          title: 'No scorecard, metadata, or description evidence was available.'
        };
      }
      metrics.sort(function(a, b) { return b.value - a.value; });
      var top = metrics[0];
      var weak = metrics[metrics.length - 1];
      var overall = Number(rank && rank.overall) || 0;
      var confidence = String(rank && rank.confidence || 'Est');
      var reasonFlags = String(rank && rank.reasonFlags || '').replace(/_/g, ' ');
      var ownerStatus = String(rank && rank.ownerStatus || '');
      var tone = overall >= 82 && confidence !== 'Low' && confidence !== 'Broken' ? 'strong' : (overall < 70 || weak.value < 62 || confidence === 'Low' || confidence === 'Broken' ? 'rework' : 'watch');
      var headline = tone === 'strong' ? 'Best: ' + top.short + ' ' + Math.round(top.value) : 'Watch: ' + weak.short + ' ' + Math.round(weak.value);
      var detail = tone === 'strong'
        ? top.label + ' is carrying this pick.'
        : weak.label + ' is the weakest signal.';
      if (ownerStatus) {
        detail = 'Owner: ' + ownerStatus + '.';
      } else if (reasonFlags) {
        detail = reasonFlags + '.';
      } else if (confidence === 'Low') {
        detail = 'Low evidence; needs owner review.';
      } else if (confidence === 'Broken') {
        detail = 'Blocked by broken catalog evidence.';
      }
      return {
        tone: tone,
        headline: headline,
        detail: detail,
        title: 'Strongest: ' + top.label + ' ' + Math.round(top.value) + '. Weakest: ' + weak.label + ' ' + Math.round(weak.value) + '.'
      };
    }

    function _renderPickerRankingExplainer(rank, type, escapeFn) {
      if (!getPickerInternalReviewUiEnabled()) return '';
      var esc = typeof escapeFn === 'function' ? escapeFn : escapeHtml;
      var summary = _pickerRankingMetricSummary(rank, type);
      return '<div class="picker-rank-explain picker-rank-explain-' + esc(summary.tone) + '" title="' + esc(summary.title) + '">' +
        '<span class="picker-rank-explain-head">' + esc(summary.headline) + '</span>' +
        '<span class="picker-rank-explain-detail">' + esc(summary.detail) + '</span>' +
        '</div>';
    }

    function _renderCatalogRankChips(item, type, precomputedRank) {
      const r = precomputedRank || _catalogRankingForItem(item, type);
      if (getPickerInternalReviewUiEnabled()) {
        const ownerTitle = r.ownerNote ? ' Owner note: ' + r.ownerNote : '';
        const ownerChip = r.confidence === 'Owner' ? '<span class="swatch-rank-chip swatch-rank-owner">' + escapeHtml(r.ownerStatus || 'Owner') + '</span>' : '';
        return '<div class="swatch-rank-row" title="Catalog ranking (' + r.confidence + '): Design ' + r.patternDesign + ', Unique ' + r.distinctness + ', Spec Detail ' + r.specDetail + ', Render Estimate ' + r.renderTime + ', Intent Fit ' + r.intentFit + ', Sponsor Safety ' + r.sponsorSafety + '.' + escapeHtml(ownerTitle) + '">' +
          '<span class="swatch-rank-chip swatch-rank-main">' + r.confidence + ' ' + r.tier + r.overall + '</span>' +
          '<span class="swatch-rank-chip">Spec ' + r.specDetail + '</span>' +
          '<span class="swatch-rank-chip">Fit ' + r.intentFit + '</span>' +
          ownerChip +
          '</div>' + _renderPickerRankingExplainer(r, type, escapeHtml);
      }
      const chips = [];
      if ((r.overall || 0) >= 86) chips.push('Showcase');
      if ((r.specDetail || 0) >= 76) chips.push('Rich Spec');
      if ((r.renderTime || 0) >= 82) chips.push('Fast');
      if ((r.sponsorSafety || 0) >= 78) chips.push('Clean Layout');
      if (!chips.length) chips.push(type === 'pattern' ? 'Pattern' : 'Material');
      return '<div class="swatch-rank-row swatch-client-cues" title="Picker cues are simplified for release browsing.">' +
        chips.slice(0, 3).map(function(label, idx) {
          return '<span class="swatch-rank-chip' + (idx === 0 ? ' swatch-rank-main' : '') + '">' + escapeHtml(label) + '</span>';
        }).join('') +
        '</div>';
    }

    function _swatchMaterialChipsForItem(item, type, rank) {
      const q = String([
        item && item.id,
        item && item.name,
        item && item.desc,
        item && item.category,
        type
      ].filter(Boolean).join(' ')).toLowerCase();
      const chips = [];
      function add(label, key) {
        if (chips.length >= 4) return;
        if (!chips.some(function(c) { return c.key === key; })) chips.push({ label, key });
      }
      if (type === 'pattern') add('Pattern', 'pattern');
      if (/chrome|mirror|polish/.test(q)) add('Chrome', 'chrome');
      if (/metal|metallic|flake|brushed|machined|forged/.test(q)) add('Metal', 'metal');
      if (/pearl|mica|iridescent/.test(q)) add('Pearl', 'pearl');
      if (/candy|tinted clear|transparent/.test(q)) add('Candy', 'candy');
      if (/matte|flat|low gloss/.test(q)) add('Matte', 'matte');
      if (/satin|silk/.test(q)) add('Satin', 'satin');
      if (/gloss|clearcoat|wet|glass/.test(q)) add('Gloss', 'gloss');
      if (/carbon|weave|composite|fiber/.test(q)) add('Carbon', 'carbon');
      if (/weather|aged|rust|patina|worn|grunge|dust/.test(q)) add('Weathered', 'weathered');
      if (/color.?shift|chameleon|prizm|prism|holographic|iridescent/.test(q)) add('Shift', 'shift');
      if (rank && rank.confidence === 'Owner' && /keeper|featured|showcase/i.test(String(rank.ownerStatus || ''))) add('Owner Pick', 'owner');
      if (rank && rank.confidence === 'Owner' && /watch|rework/i.test(String(rank.ownerStatus || ''))) add('Owner Watch', 'owner-watch');
      if (rank && rank.sponsorSafety >= 76) add('Text Safe', 'safe');
      if (rank && (rank.confidence === 'Low' || rank.confidence === 'Broken')) add('Review', 'review');
      return chips;
    }

    function _renderSwatchMaterialChips(item, type, rank) {
      const chips = _swatchMaterialChipsForItem(item, type, rank);
      if (!chips.length) return '';
      return '<div class="swatch-material-row">' + chips.map(function(chip) {
        return '<span class="swatch-material-chip swatch-material-' + chip.key + '">' + escapeHtml(chip.label) + '</span>';
      }).join('') + '</div>';
    }

    function _swatchPickerSearchText(item, type, groupName) {
      const base = [
        item.id,
        item.name,
        item.desc,
        item.category,
        groupName,
        type,
        getLibrarySearchText(item, type === 'monolithic' ? 'mono' : type)
      ];
      const q = base.join(' ').toLowerCase();
      const aliasPieces = [];
      const aliasMap = getFinishLibrarySearchAliases() || {};
      Object.keys(aliasMap).forEach(function(alias) {
        const words = aliasMap[alias] || [];
        if (q.indexOf(alias) >= 0 || words.some(function(word) { return q.indexOf(word) >= 0; })) {
          aliasPieces.push(alias);
          aliasPieces.push(words.join(' '));
        }
      });
      return (q + ' ' + aliasPieces.join(' ')).trim();
    }

    function _renderSwatchPickerCard(item, type, currentId, selectValue, groupName) {
      const normalizedSelect = selectValue || item.id;
      const cleanId = item.id;
      const isSelected = currentId === normalizedSelect || currentId === cleanId || currentId === ('mono:' + cleanId);
      const isFav = isFavorite(cleanId);
      const ft = type || getFinishType(cleanId);
      const name = escapeHtml(item.name || cleanId);
      const desc = escapeHtml(item.desc || item.name || cleanId);
      const search = escapeHtml(_swatchPickerSearchText(item, ft, groupName || ''));
      const safeSelect = String(normalizedSelect).replace(/'/g, "\\'");
      const safeCleanId = cleanId.replace(/'/g, "\\'");
      const rank = _catalogRankingForItem(item, ft);
      const ownerStatus = escapeHtml(rank.ownerStatus || '');
      const handoff = (rank.overall < 70 || rank.confidence === 'Low' || rank.confidence === 'Broken' || rank.specDetail < 62 || rank.intentFit < 62 || /low_|slow_|flat_spec|macro_dominated|broken/.test(String(rank.reasonFlags || ''))) ? 'true' : 'false';
      // SPB-SIMPLIFY-2026-07-19h (owner): the Review/Est/Spec/Fit + material pill rows are
      // GONE — replaced by the always-visible description and the 0-100 FINISH RATING slider
      // (default 50, persisted via spbSetFinishRating; drives per-category order + Best sort).
      const rating = (typeof global.spbGetFinishRating === 'function') ? global.spbGetFinishRating(cleanId) : 50;
      return '<div class="swatch-item swatch-catalog-card' + (isSelected ? ' selected' : '') + '" role="button" tabindex="0" aria-label="Choose ' + name + '" data-name="' + search.toLowerCase() + '" data-search="' + search.toLowerCase() + '" data-sort-name="' + name.toLowerCase() + '" data-finish-id="' + cleanId + '" data-finish-type="' + (ft || 'base') + '" data-desc="' + desc + '" data-rating="' + rating + '" data-rank-overall="' + rank.overall + '" data-rank-confidence="' + rank.confidence + '" data-rank-spec="' + rank.specDetail + '" data-rank-fit="' + rank.intentFit + '" data-rank-render="' + rank.renderTime + '" data-rank-sponsor="' + rank.sponsorSafety + '" data-owner-status="' + ownerStatus + '" data-measured-overall="' + (rank.measuredOverall || rank.scorecardOverall || '') + '" data-handoff="' + handoff + '" onclick="selectSwatchItem(\'' + safeSelect + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();selectSwatchItem(\'' + safeSelect + '\');}">' +
        '<button type="button" class="swatch-fav-btn' + (isFav ? ' active' : '') + '" onclick="toggleSwatchPickerFavorite(\'' + safeCleanId + '\', event)" title="' + (isFav ? 'Remove from favorites' : 'Add to favorites') + '">' + (isFav ? '*' : '+') + '</button>' +
        renderSwatchSquare(cleanId, item.swatch, item.desc, null, ft) +
        '<div class="swatch-label">' + name + '</div>' +
        '<div class="swatch-card-desc">' + desc + '</div>' +
        '<div class="swatch-rate-row" title="Finish Rating — drag 0-100. Your highest-rated finishes sort to the top of each category; the Best sort uses this order." onclick="event.stopPropagation()" onmousedown="event.stopPropagation()">' +
          '<input type="range" class="swatch-rate-slider" min="0" max="100" step="1" value="' + rating + '"' +
            ' oninput="spbSetFinishRating(\'' + safeCleanId + '\', this.value, this)"' +
            ' onclick="event.stopPropagation()" onmousedown="event.stopPropagation()">' +
          '<span class="swatch-rate-val">' + rating + '</span>' +
        '</div>' +
        '</div>';
    }

    function _renderSwatchFavoritesGroup(kind, currentId) {
      const favIds = Array.from(getFavoriteFinishes() || []);
      if (favIds.length === 0) return '';
      const seen = new Set();
      const entries = [];
      favIds.forEach(function(id) {
        const hit = _getSwatchItemById(id, kind === 'pattern' ? 'pattern' : null);
        if (!hit || seen.has(hit.item.id)) return;
        if (kind === 'pattern' && hit.type !== 'pattern') return;
        if (kind === 'finish' && hit.type === 'pattern') return;
        entries.push(hit);
        seen.add(hit.item.id);
      });
      if (entries.length === 0) return '';
      let html = '<div class="swatch-group swatch-favorites-group">' +
        '<div class="swatch-group-label swatch-favorites-label" onclick="this.parentElement.classList.toggle(\'collapsed\')">Favorites <span class="swatch-group-count">(' + entries.length + ')</span></div>' +
        '<div class="swatch-grid-row">';
      entries.forEach(function(entry) {
        html += _renderSwatchPickerCard(entry.item, entry.type, currentId, entry.selectValue, 'Favorites');
      });
      html += '</div></div>';
      return html;
    }

    global._getSwatchItemById = _getSwatchItemById;
    global._rankClamp = _rankClamp;
    global._rankKeywordScore = _rankKeywordScore;
    global._catalogScorecardTable = _catalogScorecardTable;
    global._catalogScorecardKey = _catalogScorecardKey;
    global._getCatalogScorecardRow = _getCatalogScorecardRow;
    global._pickerOwnerRatingTable = _pickerOwnerRatingTable;
    global._pickerRatingType = _pickerRatingType;
    global._getPickerOwnerRating = _getPickerOwnerRating;
    global._rankTierForOverall = _rankTierForOverall;
    global._applyPickerOwnerRating = _applyPickerOwnerRating;
    global._scorecardSmooth = _scorecardSmooth;
    global._descriptionIntentScore = _descriptionIntentScore;
    global._scorecardUniqueness = _scorecardUniqueness;
    global._scorecardSponsorSafety = _scorecardSponsorSafety;
    global._catalogRankingFromScorecard = _catalogRankingFromScorecard;
    global._catalogRankingForItem = _catalogRankingForItem;
    global._pickerRankingMetricSummary = _pickerRankingMetricSummary;
    global._renderPickerRankingExplainer = _renderPickerRankingExplainer;
    global._renderCatalogRankChips = _renderCatalogRankChips;
    global._swatchMaterialChipsForItem = _swatchMaterialChipsForItem;
    global._renderSwatchMaterialChips = _renderSwatchMaterialChips;
    global._swatchPickerSearchText = _swatchPickerSearchText;
    global._renderSwatchPickerCard = _renderSwatchPickerCard;
    global._renderSwatchFavoritesGroup = _renderSwatchFavoritesGroup;
  }

  global.SPBSwatchPopupRankingControls = {
    install: installSwatchPopupRankingControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
