(function(global) {
  'use strict';

  function installSwatchPopupCategoryStrategyControls(deps) {
    deps = deps || {};
    const collectPickerRankingRows = deps.collectPickerRankingRows || function() { return []; };
    const swatchReviewAllowedTypes = deps.swatchReviewAllowedTypes || function() { return ['base', 'monolithic']; };
    const setPickerActiveLaneContext = deps.setPickerActiveLaneContext || function() {};
    const pickerLaneContextFromStrategy = deps.pickerLaneContextFromStrategy || function() { return null; };
    const getSwatchPopupState = deps.getSwatchPopupState || function() { return {}; };
    const renderSwatchPopupFilterControls = deps.renderSwatchPopupFilterControls || function() {};
    const filterSwatchPopup = deps.filterSwatchPopup || function() {};
    const getDocument = deps.getDocument || function() { return global.document; };
    const getBlob = deps.getBlob || function() { return global.Blob; };
    const getUrlApi = deps.getUrlApi || function() { return global.URL; };
    const escapeHtml = deps.escapeHtml || function(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
      });
    };

    function collectPickerCategoryStrategyRows(scopeTypes, limit) {
      const allowedTypes = Array.isArray(scopeTypes) && scopeTypes.length ? scopeTypes : ['base', 'monolithic', 'pattern', 'spec_pattern'];
      const groups = {};
      collectPickerRankingRows().filter(function(row) {
        return allowedTypes.indexOf(row.type) >= 0;
      }).forEach(function(row) {
        const key = (row.type || 'finish') + '::' + (row.category || 'Uncategorized');
        if (!groups[key]) {
          groups[key] = {
            key: key,
            type: row.type || '',
            category: row.category || 'Uncategorized',
            total: 0,
            showcase: 0,
            strongMeasured: 0,
            surgery: 0,
            needsOwnerRating: 0,
            ownerRated: 0,
            ids: [],
            candidates: []
          };
        }
        const g = groups[key];
        g.total += 1;
        g.ids.push(row.id);
        const ownerStatus = String(row.ownerStatus || '').toLowerCase();
        const handoff = !!row.handoff || /low_|slow_|flat_spec|macro_dominated|broken/.test(String(row.reasonFlags || ''));
        g.candidates.push({
          id: row.id,
          name: row.name || row.id,
          overall: Number(row.overall || 0),
          specDetail: Number(row.specDetail || 0),
          intentFit: Number(row.intentFit || 0),
          renderTime: Number(row.renderTime || 0),
          handoff: handoff,
          confidence: row.confidence || '',
          ownerStatus: row.ownerStatus || ''
        });
        if (/keeper|featured|showcase/.test(ownerStatus) || (row.overall >= 88 && row.specDetail >= 76 && row.intentFit >= 76 && row.confidence !== 'Low' && row.confidence !== 'Broken')) g.showcase += 1;
        if (row.confidence === 'Measured' && row.overall >= 80 && row.specDetail >= 72 && row.intentFit >= 70) g.strongMeasured += 1;
        if (!ownerStatus && row.confidence !== 'Owner' && ((row.overall >= 82 && row.specDetail >= 70) || (row.overall > 0 && row.overall < 68) || handoff)) g.needsOwnerRating += 1;
        if (handoff || row.confidence === 'Broken' || row.confidence === 'Low' || (row.overall > 0 && (row.overall < 70 || row.specDetail < 62 || row.intentFit < 62 || row.renderTime < 55))) g.surgery += 1;
        if (ownerStatus) g.ownerRated += 1;
      });
      const rows = Object.keys(groups).map(function(key) {
        const g = groups[key];
        if (g.total <= 2) {
          g.recommendation = 'Merge or archive';
          g.reason = 'Underbuilt group with too few visible choices.';
          g.priority = 95;
        } else if (g.surgery >= Math.max(2, g.showcase + g.strongMeasured)) {
          g.recommendation = 'SPB-67 surgery';
          g.reason = 'Weak/spec/fit candidates outweigh strong entries.';
          g.priority = 90;
        } else if (g.showcase + g.strongMeasured >= 3) {
          g.recommendation = 'Feature lane';
          g.reason = 'Enough strong evidence to surface as buyer-facing.';
          g.priority = 62;
        } else if (g.needsOwnerRating >= Math.max(2, Math.ceil(g.total * 0.45))) {
          g.recommendation = 'Owner rating pass';
          g.reason = 'Promising or risky unrated entries need taste review.';
          g.priority = 72;
        } else {
          g.recommendation = 'Keep and monitor';
          g.reason = 'No urgent UI merge/archive signal yet.';
          g.priority = 32;
        }
        const candidates = (g.candidates || []).slice();
        g.reviewExamples = candidates.sort(function(a, b) {
          const ah = a.handoff ? 1 : 0;
          const bh = b.handoff ? 1 : 0;
          if (bh !== ah) return bh - ah;
          if (a.overall !== b.overall) return a.overall - b.overall;
          if (a.specDetail !== b.specDetail) return a.specDetail - b.specDetail;
          return String(a.name || a.id).localeCompare(String(b.name || b.id));
        }).slice(0, 3);
        g.showcaseExamples = candidates.filter(function(candidate) {
          const status = String(candidate.ownerStatus || '').toLowerCase();
          return /keeper|featured|showcase/.test(status)
            || (candidate.overall >= 86 && candidate.specDetail >= 72 && candidate.intentFit >= 70);
        }).sort(function(a, b) {
          if (b.overall !== a.overall) return b.overall - a.overall;
          return String(a.name || a.id).localeCompare(String(b.name || b.id));
        }).slice(0, 3);
        g.sampleIds = (g.reviewExamples || []).map(function(candidate) { return candidate.id; });
        delete g.candidates;
        return g;
      });
      rows.sort(function(a, b) {
        if (b.priority !== a.priority) return b.priority - a.priority;
        if (a.total !== b.total) return a.total - b.total;
        return String(a.category).localeCompare(String(b.category));
      });
      return typeof limit === 'number' ? rows.slice(0, Math.max(0, limit)) : rows;
    }

    function _renderCategoryStrategyExamples(row) {
      const bucket = _pickerStrategyBucketId(row);
      const examples = bucket === 'featureLanes'
        ? (row.showcaseExamples || row.reviewExamples || [])
        : (row.reviewExamples || []);
      if (!examples.length) return '';
      const label = bucket === 'featureLanes' ? 'Feature first' : 'Start with';
      return '<div class="swatch-category-strategy-examples">' +
        '<span>' + escapeHtml(label) + '</span>' +
        examples.slice(0, 3).map(function(candidate) {
          const safeId = String(candidate.id || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
          const title = String(candidate.name || candidate.id || '').trim();
          const score = Number(candidate.overall || 0);
          const filterName = bucket === 'featureLanes' ? 'showcase' : 'needs_review';
          return '<button type="button" onclick="focusSwatchReviewCandidate(\'' + safeId + '\', event, \'' + filterName + '\')" title="Find ' + escapeHtml(title) + ' in this picker">' +
            escapeHtml(title) + (score ? ' ' + escapeHtml(String(score)) : '') +
          '</button>';
        }).join('') +
      '</div>';
    }

    function _pickerStrategyBucketId(row) {
      const recommendation = String(row && row.recommendation || '');
      if (recommendation === 'Feature lane') return 'featureLanes';
      if (recommendation === 'Owner rating pass') return 'ownerRating';
      if (recommendation === 'Merge or archive') return 'mergeArchive';
      if (recommendation === 'SPB-67 surgery') return 'spb67Surgery';
      return 'monitor';
    }

    function _pickerStrategyBucketLabel(bucketId) {
      const labels = {
        featureLanes: 'Feature',
        ownerRating: 'Rate',
        mergeArchive: 'Merge',
        spb67Surgery: 'Surgery',
        monitor: 'Monitor'
      };
      return labels[bucketId] || 'Monitor';
    }

    function _pickerLaneForStrategyBucket(bucketId) {
      const bucket = String(bucketId || '');
      if (bucket === 'featureLanes') return 'showcase';
      if (bucket === 'ownerRating') return 'needs_owner_rating';
      if (bucket === 'mergeArchive' || bucket === 'spb67Surgery') return 'spb67_surgery';
      return 'all';
    }

    function collectPickerConsolidatedCategoryProposal(scopeTypes) {
      const allowedTypes = Array.isArray(scopeTypes) && scopeTypes.length ? scopeTypes : ['base', 'monolithic', 'pattern', 'spec_pattern'];
      const rows = collectPickerCategoryStrategyRows(allowedTypes);
      const buckets = {
        featureLanes: [],
        ownerRating: [],
        mergeArchive: [],
        spb67Surgery: [],
        monitor: []
      };
      rows.forEach(function(row) {
        buckets[_pickerStrategyBucketId(row)].push(row);
      });
      return {
        format: 'spb-picker-consolidated-category-proposal-v1',
        generatedAt: new Date().toISOString(),
        scopeTypes: allowedTypes,
        totals: {
          categories: rows.length,
          entries: rows.reduce(function(total, row) { return total + (row.total || 0); }, 0),
          featureLanes: buckets.featureLanes.length,
          ownerRating: buckets.ownerRating.length,
          mergeArchive: buckets.mergeArchive.length,
          spb67Surgery: buckets.spb67Surgery.length,
          monitor: buckets.monitor.length
        },
        buckets: buckets,
        rows: rows
      };
    }

    function _renderCategoryStrategySummary(scopeTypes, label) {
      const proposal = collectPickerConsolidatedCategoryProposal(scopeTypes);
      const cards = [
        { key: 'featureLanes', title: 'Feature lanes', detail: 'Strong enough to sell from the top' },
        { key: 'ownerRating', title: 'Owner rating', detail: 'Taste review before trusting rank' },
        { key: 'mergeArchive', title: 'Merge/archive', detail: 'Underbuilt or noisy as standalone' },
        { key: 'spb67Surgery', title: 'SPB-67 surgery', detail: 'Quality/intent/spec repair lane' }
      ];
      return '<div class="swatch-category-proposal-summary" data-format="' + escapeHtml(proposal.format) + '">' +
        '<div class="swatch-category-proposal-head">' +
          '<strong>' + escapeHtml(label || 'Category proposal') + '</strong>' +
          '<span>' + escapeHtml(String(proposal.totals.categories)) + ' groups / ' + escapeHtml(String(proposal.totals.entries)) + ' entries</span>' +
        '</div>' +
        '<div class="swatch-category-proposal-cards">' + cards.map(function(card) {
          const count = proposal.totals[card.key] || 0;
          return '<div class="swatch-category-proposal-card swatch-category-plan-' + card.key.toLowerCase() + '">' +
            '<strong>' + escapeHtml(String(count)) + '</strong>' +
            '<span>' + escapeHtml(card.title) + '</span>' +
            '<em>' + escapeHtml(card.detail) + '</em>' +
          '</div>';
        }).join('') + '</div></div>';
    }

    function _downloadPickerJson(payload, filename) {
      const json = JSON.stringify(payload, null, 2);
      const documentRef = getDocument();
      const BlobCtor = getBlob();
      const urlApi = getUrlApi();
      if (typeof BlobCtor !== 'undefined' && typeof urlApi !== 'undefined' && documentRef && documentRef.body) {
        const blob = new BlobCtor([json], { type: 'application/json' });
        const url = urlApi.createObjectURL(blob);
        const link = documentRef.createElement('a');
        link.href = url;
        link.download = filename;
        documentRef.body.appendChild(link);
        link.click();
        setTimeout(function() {
          urlApi.revokeObjectURL(url);
          if (link && link.parentNode) link.parentNode.removeChild(link);
        }, 0);
      }
      return payload;
    }

    function _renderSwatchCategoryStrategyPanel(limit) {
      const documentRef = getDocument();
      const panel = documentRef ? documentRef.getElementById('swatchCategoryStrategyPanel') : null;
      if (!panel) return;
      const rows = collectPickerCategoryStrategyRows(swatchReviewAllowedTypes(), limit || 16);
      const label = (swatchReviewAllowedTypes().indexOf('pattern') >= 0) ? 'Pattern category plan' : 'Finish category plan';
      if (!rows.length) {
        panel.innerHTML = '<div class="swatch-low-score-empty">No category strategy rows found for this picker.</div>';
        return;
      }
      panel.innerHTML = `<div class="swatch-low-score-head">
        <div><strong>${label}</strong><span>UI-only category strategy. Preserve IDs; use these to merge, rename, feature, or hand off weak groups.</span></div>
        <div class="swatch-review-head-actions">
            <button type="button" onclick="exportPickerCategoryStrategy(event)" title="Export category strategy JSON">Export</button>
            <button type="button" onclick="exportPickerConsolidatedCategoryProposal(event)" title="Export all picker category strategy JSON">Export All</button>
            <button type="button" onclick="toggleSwatchCategoryStrategyPanel(false)" title="Close category plan">Close</button>
        </div>
      </div>
      ${_renderCategoryStrategySummary(swatchReviewAllowedTypes(), label)}
      <div class="swatch-category-strategy-list">` + rows.map(function(row) {
        const lane = row.recommendation === 'SPB-67 surgery' || row.recommendation === 'Merge or archive' ? 'spb67_surgery'
          : row.recommendation === 'Feature lane' ? 'showcase'
          : row.recommendation === 'Owner rating pass' ? 'needs_owner_rating'
          : 'all';
        const bucket = _pickerStrategyBucketId(row);
        const safeCategoryArg = String(row.category || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        return `<div class="swatch-category-strategy-row swatch-category-plan-${bucket.toLowerCase()}" data-plan-bucket="${escapeHtml(bucket)}" data-plan-category="${escapeHtml(row.category)}" data-plan-lane="${escapeHtml(lane)}">
          <div class="swatch-category-strategy-title">${escapeHtml(row.category)} <span class="swatch-category-plan-badge">${escapeHtml(_pickerStrategyBucketLabel(bucket))}</span></div>
          <div class="swatch-category-strategy-meta">${escapeHtml(row.type)} &middot; ${escapeHtml(String(row.total))} entries &middot; ${escapeHtml(row.recommendation)}</div>
          <div class="swatch-category-strategy-bars">
              <span>Strong ${escapeHtml(String(row.showcase + row.strongMeasured))}</span>
              <span>Surgery ${escapeHtml(String(row.surgery))}</span>
              <span>Rate ${escapeHtml(String(row.needsOwnerRating))}</span>
              <span>Owner ${escapeHtml(String(row.ownerRated))}</span>
          </div>
          <div class="swatch-low-score-reason">${escapeHtml(row.reason)}</div>
          ${_renderCategoryStrategyExamples(row)}
          <button type="button" class="swatch-low-score-action" onclick="focusSwatchCategoryStrategyLane('${lane}', event, '${escapeHtml(safeCategoryArg)}')" title="Filter the picker to the matching curation lane">Open lane</button>
        </div>`;
      }).join('') + '</div>';
    }

    function toggleSwatchCategoryStrategyPanel(force) {
      const documentRef = getDocument();
      const panel = documentRef ? documentRef.getElementById('swatchCategoryStrategyPanel') : null;
      const btn = documentRef ? documentRef.getElementById('swatchCategoryStrategyBtn') : null;
      if (!panel) return;
      const nextOpen = typeof force === 'boolean' ? force : panel.hidden;
      panel.hidden = !nextOpen;
      if (btn) {
        btn.classList.toggle('active', nextOpen);
        btn.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
      }
      if (nextOpen) _renderSwatchCategoryStrategyPanel(16);
    }

    function focusSwatchCategoryStrategyLane(lane, event, category) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const rows = collectPickerCategoryStrategyRows(swatchReviewAllowedTypes());
      const wanted = String(category || '').trim().toLowerCase();
      const row = rows.find(function(item) {
        return wanted && String(item.category || '').trim().toLowerCase() === wanted;
      }) || null;
      const state = getSwatchPopupState();
      setPickerActiveLaneContext('main', null, pickerLaneContextFromStrategy(row, category || '', lane || 'all', 'main'));
      state.filter = lane || 'all';
      renderSwatchPopupFilterControls(state.type);
      const documentRef = getDocument();
      const search = documentRef ? documentRef.getElementById('swatchSearchInput') : null;
      if (search) search.value = '';
      filterSwatchPopup('');
    }

    function exportPickerCategoryStrategy(event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const scopeTypes = swatchReviewAllowedTypes();
      const payload = {
        format: 'spb-picker-category-strategy-v1',
        generatedAt: new Date().toISOString(),
        scopeTypes: scopeTypes,
        proposal: collectPickerConsolidatedCategoryProposal(scopeTypes),
        rows: collectPickerCategoryStrategyRows(scopeTypes)
      };
      return _downloadPickerJson(payload, 'spb-picker-category-strategy.json');
    }

    function exportPickerConsolidatedCategoryProposal(event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const payload = collectPickerConsolidatedCategoryProposal(['base', 'monolithic', 'pattern', 'spec_pattern']);
      return _downloadPickerJson(payload, 'spb-picker-consolidated-category-proposal.json');
    }

    global.collectPickerCategoryStrategyRows = collectPickerCategoryStrategyRows;
    global._renderCategoryStrategyExamples = _renderCategoryStrategyExamples;
    global._pickerStrategyBucketId = _pickerStrategyBucketId;
    global._pickerStrategyBucketLabel = _pickerStrategyBucketLabel;
    global._pickerLaneForStrategyBucket = _pickerLaneForStrategyBucket;
    global.collectPickerConsolidatedCategoryProposal = collectPickerConsolidatedCategoryProposal;
    global._renderCategoryStrategySummary = _renderCategoryStrategySummary;
    global._downloadPickerJson = _downloadPickerJson;
    global._renderSwatchCategoryStrategyPanel = _renderSwatchCategoryStrategyPanel;
    global.toggleSwatchCategoryStrategyPanel = toggleSwatchCategoryStrategyPanel;
    global.focusSwatchCategoryStrategyLane = focusSwatchCategoryStrategyLane;
    global.exportPickerCategoryStrategy = exportPickerCategoryStrategy;
    global.exportPickerConsolidatedCategoryProposal = exportPickerConsolidatedCategoryProposal;
  }

  global.SPBSwatchPopupCategoryStrategyControls = {
    install: installSwatchPopupCategoryStrategyControls
  };
})(typeof window !== 'undefined' ? window : globalThis);
