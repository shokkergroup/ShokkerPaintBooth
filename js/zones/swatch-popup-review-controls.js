(function(global) {
  'use strict';

  function installSwatchPopupReviewControls(deps) {
    deps = deps || {};
    const getBases = deps.getBases || function() { return []; };
    const getMonolithics = deps.getMonolithics || function() { return []; };
    const getPatterns = deps.getPatterns || function() { return []; };
    const getSpecPatterns = deps.getSpecPatterns || function() { return []; };
    const getBaseGroups = deps.getBaseGroups || function() { return {}; };
    const getPatternGroups = deps.getPatternGroups || function() { return {}; };
    const getSpecPatternGroups = deps.getSpecPatternGroups || function() { return {}; };
    const getSpecialGroups = deps.getSpecialGroups || function() { return {}; };
    const getSwatchPopupState = deps.getSwatchPopupState || function() { return {}; };
    const rankSpecPatternForPicker = deps.rankSpecPatternForPicker || function() {
      return { overall: 0, confidence: 'Low', specDetail: 0, intentFit: 0, renderTime: 0, sponsorSafety: 0 };
    };
    const catalogRankingForItem = deps.catalogRankingForItem || function() {
      return { overall: 0, confidence: 'Low', specDetail: 0, intentFit: 0, renderTime: 0, sponsorSafety: 0 };
    };
    const escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };
    const getDocument = deps.getDocument || function() { return global.document; };
    const getNavigator = deps.getNavigator || function() { return global.navigator; };
    const getBlob = deps.getBlob || function() { return global.Blob; };
    const getUrlApi = deps.getUrlApi || function() { return global.URL; };

    function _fillGroupLookup(groups) {
      const out = {};
      Object.keys(groups || {}).forEach(function(group) {
        (groups[group] || []).forEach(function(id) { out[id] = group; });
      });
      return out;
    }

    function collectPickerRankingRows(limit) {
      const rows = [];
      function addItem(type, item, category) {
        if (!item || !item.id) return;
        const rank = type === 'spec_pattern'
          ? rankSpecPatternForPicker(item, category || '')
          : catalogRankingForItem(item, type);
        rows.push({
          id: item.id,
          type: type,
          name: item.name || item.id,
          category: category || item.category || '',
          overall: rank.overall,
          confidence: rank.confidence || 'Est',
          patternDesign: rank.patternDesign,
          uniqueness: rank.distinctness || rank.uniqueness,
          specDetail: rank.specDetail,
          renderTime: rank.renderTime,
          intentFit: rank.intentFit,
          sponsorSafety: rank.sponsorSafety,
          measuredOverall: typeof rank.measuredOverall === 'number' ? rank.measuredOverall : (typeof rank.scorecardOverall === 'number' ? rank.scorecardOverall : null),
          scorecardOverall: typeof rank.scorecardOverall === 'number' ? rank.scorecardOverall : null,
          ownerStatus: rank.ownerStatus || '',
          ownerNote: rank.ownerNote || '',
          ownerSource: rank.ownerSource || '',
          priority: rank.priority || '',
          reasonFlags: rank.reasonFlags || '',
          estimated2048Ms: rank.estimated2048Ms || 0,
          handoff: (rank.overall < 70 || rank.confidence === 'Low' || rank.confidence === 'Broken' || rank.specDetail < 62 || rank.intentFit < 62 || /low_|slow_|flat_spec|macro_dominated|broken/.test(String(rank.reasonFlags || ''))) ? 'SPB-67 candidate' : ''
        });
      }
      const baseCat = _fillGroupLookup(getBaseGroups());
      const patternCat = _fillGroupLookup(getPatternGroups());
      const specCat = _fillGroupLookup(getSpecPatternGroups());
      const specialCat = _fillGroupLookup(getSpecialGroups());
      getBases().forEach(function(item) { addItem('base', item, baseCat[item.id] || item.category || ''); });
      getMonolithics().forEach(function(item) { addItem('monolithic', item, specialCat[item.id] || item.category || ''); });
      getPatterns().forEach(function(item) { addItem('pattern', item, patternCat[item.id] || item.category || ''); });
      getSpecPatterns().forEach(function(item) { addItem('spec_pattern', item, specCat[item.id] || item.category || ''); });
      rows.sort(function(a, b) {
        if (a.overall !== b.overall) return a.overall - b.overall;
        if (a.confidence !== b.confidence) return String(a.confidence).localeCompare(String(b.confidence));
        return String(a.name).localeCompare(String(b.name));
      });
      return typeof limit === 'number' ? rows.slice(0, Math.max(0, limit)) : rows;
    }

    function collectPickerOwnerDisagreementRows(limit) {
      const rows = collectPickerRankingRows().filter(function(row) {
        return row.confidence === 'Owner'
          && typeof row.measuredOverall === 'number'
          && Number.isFinite(row.measuredOverall);
      }).map(function(row) {
        const measured = Math.round(row.measuredOverall);
        const delta = Math.round(row.overall - measured);
        return Object.assign({}, row, {
          measuredOverall: measured,
          ownerMeasuredDelta: delta,
          disagreementType: delta >= 0 ? 'owner_over_measured' : 'measured_over_owner',
          disagreementLabel: delta >= 0 ? 'Owner sees more value than metrics' : 'Metrics rate higher than owner signal'
        });
      }).filter(function(row) {
        return Math.abs(row.ownerMeasuredDelta) >= 8;
      });
      rows.sort(function(a, b) {
        const deltaDiff = Math.abs(b.ownerMeasuredDelta) - Math.abs(a.ownerMeasuredDelta);
        if (deltaDiff !== 0) return deltaDiff;
        return String(a.name || a.id).localeCompare(String(b.name || b.id));
      });
      return typeof limit === 'number' ? rows.slice(0, Math.max(0, limit)) : rows;
    }

    function collectPickerOwnerRatingReviewRows(scopeTypes, limit) {
      const allowedTypes = Array.isArray(scopeTypes) && scopeTypes.length ? scopeTypes : ['base', 'monolithic', 'pattern', 'spec_pattern'];
      const rows = collectPickerRankingRows().filter(function(row) {
        return allowedTypes.indexOf(row.type) >= 0;
      });
      const ownerIds = new Set(rows.filter(function(row) { return !!row.ownerStatus; }).map(function(row) { return row.type + ':' + row.id; }));
      const unrated = rows.filter(function(row) {
        return !ownerIds.has(row.type + ':' + row.id);
      });
      const gaps = collectPickerOwnerDisagreementRows().filter(function(row) {
        return allowedTypes.indexOf(row.type) >= 0;
      });
      const low = unrated.slice().sort(function(a, b) {
        if (a.overall !== b.overall) return a.overall - b.overall;
        if (a.specDetail !== b.specDetail) return a.specDetail - b.specDetail;
        return String(a.name || a.id).localeCompare(String(b.name || b.id));
      });
      const top = unrated.slice().sort(function(a, b) {
        if (a.overall !== b.overall) return b.overall - a.overall;
        if (a.specDetail !== b.specDetail) return b.specDetail - a.specDetail;
        return String(a.name || a.id).localeCompare(String(b.name || b.id));
      });
      const n = Math.max(1, limit || 12);
      return {
        scopeTypes: allowedTypes.slice(),
        ownerMeasuredGaps: gaps.slice(0, n),
        lowestUnrated: low.slice(0, n),
        strongestUnrated: top.slice(0, n),
        candidateCount: rows.length,
        unratedCount: unrated.length,
        ownerRatedCount: rows.length - unrated.length
      };
    }

    function exportPickerRatingReview(event, scopeName) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const scopeTypes = scopeName === 'spec_pattern' ? ['spec_pattern'] : _swatchReviewAllowedTypes();
      const payload = collectPickerOwnerRatingReviewRows(scopeTypes, 18);
      payload.generatedAt = new Date().toISOString();
      payload.scopeName = scopeName || (scopeTypes.indexOf('pattern') >= 0 ? 'pattern_dropdown' : 'finish_dropdown');
      payload.format = 'spb-picker-owner-rating-review-v1';
      const json = JSON.stringify(payload, null, 2);
      const fileName = 'spb-picker-rating-review-' + payload.scopeName.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.json';
      const documentRef = getDocument();
      const BlobCtor = getBlob();
      const urlApi = getUrlApi();
      if (typeof BlobCtor !== 'undefined' && typeof urlApi !== 'undefined' && documentRef && documentRef.body) {
        const blob = new BlobCtor([json], { type: 'application/json' });
        const url = urlApi.createObjectURL(blob);
        const link = documentRef.createElement('a');
        link.href = url;
        link.download = fileName;
        documentRef.body.appendChild(link);
        link.click();
        setTimeout(function() {
          urlApi.revokeObjectURL(url);
          if (link && link.parentNode) link.parentNode.removeChild(link);
        }, 0);
      }
      const navigatorRef = getNavigator();
      if (navigatorRef && navigatorRef.clipboard && navigatorRef.clipboard.writeText) {
        navigatorRef.clipboard.writeText(json).catch(function() {});
      }
      return payload;
    }

    function _swatchReviewAllowedTypes() {
      const type = getSwatchPopupState().type || '';
      if (type === 'pattern' || type === 'stackPattern' || type === 'secondBasePattern' || type === 'thirdBasePattern') {
        return ['pattern'];
      }
      if (type === 'layerSpecialPaint') return ['monolithic'];
      return ['base', 'monolithic'];
    }

    function _lowScoreReason(row) {
      const reasons = [];
      if (!row) return 'Owner review';
      const flags = String(row.reasonFlags || '').split(',').map(function(flag) { return flag.trim(); }).filter(Boolean);
      if (row.confidence === 'Measured' && row.priority) reasons.push(String(row.priority).toLowerCase());
      if (row.confidence === 'Broken') reasons.push('broken renderer');
      if (row.confidence === 'Low') reasons.push('low confidence');
      if (Number(row.overall || 0) < 70) reasons.push('low overall');
      if (Number(row.specDetail || 0) < 62) reasons.push('weak spec detail');
      if (Number(row.intentFit || 0) < 62) reasons.push('intent/name fit');
      if (Number(row.sponsorSafety || 0) < 62) reasons.push('text safety risk');
      flags.slice(0, 3).forEach(function(flag) {
        const pretty = flag.replace(/_/g, ' ');
        if (reasons.indexOf(pretty) < 0) reasons.push(pretty);
      });
      return reasons.slice(0, 3).join(', ') || 'lowest-ranked in this picker';
    }

    function _collectSwatchLowScoreRows(limit) {
      const allowedTypes = _swatchReviewAllowedTypes();
      const rows = collectPickerRankingRows().filter(function(row) {
        return allowedTypes.indexOf(row.type) >= 0;
      });
      const flagged = rows.filter(function(row) {
        return row.handoff || row.confidence === 'Low' || row.overall < 74 || row.specDetail < 66 || row.intentFit < 66;
      });
      return (flagged.length ? flagged : rows).slice(0, Math.max(1, limit || 18));
    }

    function _renderSwatchOwnerGapPanel(limit) {
      const allowedTypes = _swatchReviewAllowedTypes();
      const gaps = collectPickerOwnerDisagreementRows(limit || 6).filter(function(row) {
        return allowedTypes.indexOf(row.type) >= 0;
      });
      if (!gaps.length) return '';
      return '<div class="swatch-owner-gap-panel">' +
        '<div class="swatch-owner-gap-head">' +
        '<strong>Owner / measured score gaps</strong>' +
        '<span>These are taste-vs-metric conflicts. Review before trusting the rank.</span>' +
        '</div>' +
        '<div class="swatch-owner-gap-list">' + gaps.map(function(row) {
          const safeId = String(row.id || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          const delta = row.ownerMeasuredDelta > 0 ? '+' + row.ownerMeasuredDelta : String(row.ownerMeasuredDelta);
          return '<div class="swatch-owner-gap-row" data-owner-gap-id="' + escapeHtml(row.id) + '">' +
            '<div class="swatch-owner-gap-title">' + escapeHtml(row.name || row.id) + '</div>' +
            '<div class="swatch-owner-gap-meta">' + escapeHtml(row.type) + ' &middot; ' + escapeHtml(row.category || 'Uncategorized') + '</div>' +
            '<div class="swatch-owner-gap-scores">' +
            '<span>Owner ' + escapeHtml(String(row.overall)) + '</span>' +
            '<span>Measured ' + escapeHtml(String(row.measuredOverall)) + '</span>' +
            '<strong>' + escapeHtml(delta) + '</strong>' +
            '</div>' +
            '<div class="swatch-owner-gap-note">' + escapeHtml(row.ownerNote || row.disagreementLabel || 'Owner/auditor signal disagrees with measured score.') + '</div>' +
            '<button type="button" class="swatch-low-score-action" onclick="focusSwatchReviewCandidate(\'' + safeId + '\', event)" title="Filter this picker to the candidate">Find in dropdown</button>' +
            '</div>';
        }).join('') + '</div></div>';
    }

    function _renderSwatchLowScorePanel(limit) {
      const documentRef = getDocument();
      const panel = documentRef ? documentRef.getElementById('swatchLowScorePanel') : null;
      if (!panel) return;
      const rows = _collectSwatchLowScoreRows(limit || 18);
      const label = (_swatchReviewAllowedTypes().indexOf('pattern') >= 0) ? 'Pattern review queue' : 'Finish review queue';
      if (!rows.length) {
        panel.innerHTML = '<div class="swatch-low-score-empty">No ranked candidates found for this picker.</div>';
        return;
      }
      panel.innerHTML = '<div class="swatch-low-score-head">' +
        '<div><strong>' + label + '</strong><span>Lowest scores first. Use this to find finishes that need naming, spec, or catalog surgery.</span></div>' +
        '<div class="swatch-review-head-actions">' +
        '<button type="button" onclick="exportPickerRatingReview(event)" title="Export owner rating review JSON">Export</button>' +
        '<button type="button" onclick="toggleSwatchLowScorePanel(false)" title="Close review queue">Close</button>' +
        '</div>' +
        '</div>' +
        _renderSwatchOwnerGapPanel(6) +
        '<div class="swatch-low-score-list">' + rows.map(function(row) {
          const safeId = String(row.id || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          const reason = _lowScoreReason(row);
          return '<div class="swatch-low-score-row" data-review-id="' + escapeHtml(row.id) + '">' +
            '<div class="swatch-low-score-title">' + escapeHtml(row.name || row.id) + '</div>' +
            '<div class="swatch-low-score-meta">' + escapeHtml(row.type) + ' &middot; ' + escapeHtml(row.category || 'Uncategorized') + ' &middot; ' + escapeHtml(row.confidence) + ' ' + escapeHtml(String(row.overall)) + '</div>' +
            '<div class="swatch-low-score-bars">' +
            '<span title="Pattern design">Design ' + escapeHtml(String(row.patternDesign || 0)) + '</span>' +
            '<span title="Spec map detail">Spec ' + escapeHtml(String(row.specDetail || 0)) + '</span>' +
            '<span title="Intent and description fit">Fit ' + escapeHtml(String(row.intentFit || 0)) + '</span>' +
            '<span title="Render time estimate">Render ' + escapeHtml(String(row.renderTime || 0)) + '</span>' +
            '</div>' +
            '<div class="swatch-low-score-reason">' + escapeHtml(reason) + '</div>' +
            '<button type="button" class="swatch-low-score-action" onclick="focusSwatchReviewCandidate(\'' + safeId + '\', event)" title="Filter this picker to the candidate">Find in dropdown</button>' +
            '</div>';
        }).join('') + '</div>';
    }

    global.collectPickerRankingRows = collectPickerRankingRows;
    global.collectPickerOwnerDisagreementRows = collectPickerOwnerDisagreementRows;
    global.collectPickerOwnerRatingReviewRows = collectPickerOwnerRatingReviewRows;
    global.exportPickerRatingReview = exportPickerRatingReview;
    global._swatchReviewAllowedTypes = _swatchReviewAllowedTypes;
    global._lowScoreReason = _lowScoreReason;
    global._collectSwatchLowScoreRows = _collectSwatchLowScoreRows;
    global._renderSwatchOwnerGapPanel = _renderSwatchOwnerGapPanel;
    global._renderSwatchLowScorePanel = _renderSwatchLowScorePanel;
  }

  global.SPBSwatchPopupReviewControls = {
    install: installSwatchPopupReviewControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
