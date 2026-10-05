(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value || '').replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] || ch;
      });
    };
    var collectPickerCategoryStrategyRows = deps.collectPickerCategoryStrategyRows || function() { return []; };
    var pickerStrategyBucketId = deps.pickerStrategyBucketId || function() { return 'KEEP'; };
    var pickerStrategyBucketLabel = deps.pickerStrategyBucketLabel || function(bucket) { return String(bucket || 'Keep'); };
    var pickerLaneForStrategyBucket = deps.pickerLaneForStrategyBucket || function() { return 'all'; };

    function _pickerGroupHealthSummary(cards, matchFn) {
      var seen = new Set();
      var summary = { total: 0, showcase: 0, strong: 0, surgery: 0, needsOwner: 0 };
      Array.prototype.slice.call(cards || []).forEach(function(card) {
        var id = card.dataset.finishId || card.dataset.spid || '';
        var type = card.dataset.finishType || (card.dataset.spid ? 'spec_pattern' : '');
        var key = type + ':' + id;
        if (!id || seen.has(key)) return;
        seen.add(key);
        summary.total += 1;
        if (matchFn(card, 'showcase')) summary.showcase += 1;
        if (matchFn(card, 'strong_measured')) summary.strong += 1;
        if (matchFn(card, 'needs_owner_rating')) summary.needsOwner += 1;
        if (matchFn(card, 'spb67_surgery')) summary.surgery += 1;
      });
      return summary;
    }

    function _groupHealthLabel(summary) {
      if (!summary || !summary.total) return 'Empty';
      if (summary.total <= 2) return 'Underbuilt';
      if (summary.surgery >= Math.max(2, summary.showcase + summary.strong)) return 'Surgery';
      if (summary.showcase || summary.strong >= 3) return 'Strong';
      if (summary.needsOwner >= Math.max(2, Math.ceil(summary.total * 0.45))) return 'Needs rating';
      return 'Balanced';
    }

    function _renderGroupHealthBadge(summary, className) {
      var label = _groupHealthLabel(summary);
      var badge = document.createElement('span');
      badge.className = className + ' ' + className + '-' + label.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      badge.title = 'Category health: ' + label + '. Showcase ' + summary.showcase + ', strong measured ' + summary.strong + ', owner rating ' + summary.needsOwner + ', SPB-67 surgery ' + summary.surgery + '.';
      badge.innerHTML = '<strong>' + escapeHtml(label) + '</strong>' +
        (summary.showcase || summary.strong ? '<span>' + escapeHtml(String(summary.showcase + summary.strong)) + ' strong</span>' : '') +
        (summary.surgery ? '<span>' + escapeHtml(String(summary.surgery)) + ' surgery</span>' : '') +
        (summary.needsOwner ? '<span>' + escapeHtml(String(summary.needsOwner)) + ' rate</span>' : '');
      return badge;
    }

    function _pickerCategoryStrategyForGroup(types, category) {
      var allowedTypes = Array.isArray(types) && types.length ? types : ['base', 'monolithic', 'pattern', 'spec_pattern'];
      var wanted = String(category || '').trim().toLowerCase();
      if (!wanted) return null;
      var rows = collectPickerCategoryStrategyRows(allowedTypes);
      var matches = rows.filter(function(row) {
        return String(row.category || '').trim().toLowerCase() === wanted;
      });
      if (!matches.length) return null;
      matches.sort(function(a, b) {
        return (b.priority || 0) - (a.priority || 0);
      });
      return matches[0];
    }

    function _renderCategoryPlanBadgeElement(row, className) {
      if (!row) return null;
      var bucket = pickerStrategyBucketId(row);
      var lane = pickerLaneForStrategyBucket(bucket);
      var label = pickerStrategyBucketLabel(bucket);
      var badge = document.createElement('span');
      badge.className = className + ' ' + className + '-' + bucket.toLowerCase();
      badge.title = row.recommendation + ': ' + row.reason + ' Strong ' + ((row.showcase || 0) + (row.strongMeasured || 0)) + ', surgery ' + (row.surgery || 0) + ', owner rating ' + (row.needsOwnerRating || 0) + '. Click to filter this picker to ' + lane.replace(/_/g, ' ') + '.';
      badge.dataset.planBucket = bucket;
      badge.dataset.planLane = lane;
      badge.dataset.planCategory = row.category || '';
      badge.setAttribute('role', 'button');
      badge.setAttribute('tabindex', '0');
      badge.innerHTML = '<strong>' + escapeHtml(label) + '</strong>' +
        (row.recommendation === 'Feature lane' ? '<span>Feature lane</span>' : '') +
        (row.recommendation === 'Merge or archive' ? '<span>Merge candidate</span>' : '') +
        (row.recommendation === 'SPB-67 surgery' ? '<span>SPB-67</span>' : '') +
        (row.recommendation === 'Owner rating pass' ? '<span>Owner review</span>' : '');
      return badge;
    }

    function _wireCategoryPlanBadgeAction(badge, handler) {
      if (!badge || typeof handler !== 'function') return;
      badge.addEventListener('click', handler);
      badge.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') handler(event);
      });
    }

    Object.assign(global, {
      _pickerGroupHealthSummary: _pickerGroupHealthSummary,
      _groupHealthLabel: _groupHealthLabel,
      _renderGroupHealthBadge: _renderGroupHealthBadge,
      _pickerCategoryStrategyForGroup: _pickerCategoryStrategyForGroup,
      _renderCategoryPlanBadgeElement: _renderCategoryPlanBadgeElement,
      _wireCategoryPlanBadgeAction: _wireCategoryPlanBadgeAction
    });
  }

  global.SPBSwatchPopupHealthControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
