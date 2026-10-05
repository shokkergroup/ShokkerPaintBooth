(function(global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var getSwatchPopupState = deps.getSwatchPopupState || function() { return global.swatchPopupState || { filter: 'all', sort: 'default' }; };
    var escapeHtml = deps.escapeHtml || function(value) {
      return String(value || '').replace(/[&<>"']/g, function(ch) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] || ch;
      });
    };
    var internalReviewUiEnabled = !!deps.internalReviewUiEnabled;

    function _renderSwatchPopupFilterControls(type) {
      var row = document.getElementById('swatchPopupFilterRow');
      var wrap = document.getElementById('swatchPopupFilterButtons');
      var sortWrap = document.getElementById('swatchPopupSortButtons');
      if (!row || !wrap || !sortWrap) return;
      var state = getSwatchPopupState();
      var isPatternPicker = type === 'pattern' || type === 'stackPattern' || type === 'secondBasePattern' || type === 'thirdBasePattern';
      var filters = [
        ['all', 'All'],
        ['favorites', 'Favorites'],
        ['showcase', 'Showcase'],
        ['strong', isPatternPicker ? 'Strong Patterns' : 'Strong'],
        ['sponsor_safe', 'Sponsor Safe'],
        ['high_spec', 'High Spec'],
        ['fast', 'Fast']
      ];
      wrap.innerHTML = filters.map(function(pair) {
        var active = pair[0] === (state.filter || 'all');
        return '<button type="button" class="swatch-filter-chip' + (active ? ' active' : '') + '" data-filter="' + pair[0] + '" onclick="setSwatchPopupFilter(\'' + pair[0] + '\')" title="Filter picker to ' + pair[1] + '">' + pair[1] + '</button>';
      }).join('');
      if (!internalReviewUiEnabled && state.sort === 'needs_review') {
        state.sort = 'default';
      }
      var sorts = [['default', 'Grouped'], ['best', 'Best'], ['name', 'A-Z']];
      if (internalReviewUiEnabled) {
        sorts.push(['needs_review', 'Needs Review']);
      }
      sortWrap.innerHTML = sorts.map(function(pair) {
        var active = pair[0] === (state.sort || 'default');
        return '<button type="button" class="swatch-sort-chip' + (active ? ' active' : '') + '" data-sort="' + pair[0] + '" onclick="setSwatchPopupSort(\'' + pair[0] + '\')" title="Sort picker by ' + pair[1] + '">' + pair[1] + '</button>';
      }).join('');
      row.style.display = 'flex';
    }

    function _swatchCurationLaneMatch(card, lane) {
      if (!card || !lane) return false;
      var rank = Number(card.dataset.rankOverall || 0);
      var spec = Number(card.dataset.rankSpec || 0);
      var fit = Number(card.dataset.rankFit || 0);
      var render = Number(card.dataset.rankRender || 0);
      var confidence = card.dataset.rankConfidence || '';
      var ownerStatus = String(card.dataset.ownerStatus || '').toLowerCase();
      var handoff = card.dataset.handoff === 'true';
      if (lane === 'showcase') {
        return /keeper|featured|showcase/.test(ownerStatus) || (rank >= 88 && spec >= 76 && fit >= 76 && confidence !== 'Low' && confidence !== 'Broken');
      }
      if (lane === 'strong_measured') {
        return confidence === 'Measured' && rank >= 80 && spec >= 72 && fit >= 70;
      }
      if (lane === 'needs_owner_rating') {
        return !ownerStatus && confidence !== 'Owner' && ((rank >= 82 && spec >= 70) || (rank > 0 && rank < 68) || handoff);
      }
      if (lane === 'spb67_surgery') {
        return handoff || confidence === 'Broken' || confidence === 'Low' || (rank > 0 && (rank < 70 || spec < 62 || fit < 62 || render < 55));
      }
      return false;
    }

    function _swatchCurationLaneDefinitions(type) {
      var isPatternPicker = type === 'pattern' || type === 'stackPattern' || type === 'secondBasePattern' || type === 'thirdBasePattern';
      return [
        { id: 'showcase', label: 'Showcase', detail: isPatternPicker ? 'Best-looking pattern options' : 'Standout materials' },
        { id: 'strong_measured', label: 'Pro Picks', detail: 'Consistently strong paint behavior' }
      ];
    }

    function _renderSwatchCurationLanes(type) {
      var wrap = document.getElementById('swatchCurationLanes');
      if (!wrap) return;
      var state = getSwatchPopupState();
      var defs = _swatchCurationLaneDefinitions(type);
      wrap.innerHTML = defs.map(function(def) {
        var active = (state.filter || 'all') === def.id;
        return '<button type="button" class="swatch-curation-lane' + (active ? ' active' : '') + '" data-lane="' + def.id + '" onclick="setSwatchPopupFilter(\'' + def.id + '\')" title="' + escapeHtml(def.detail) + '">' +
          '<strong>' + escapeHtml(def.label) + '</strong>' +
          '<span>' + escapeHtml(def.detail) + '</span>' +
          '<em data-lane-count="' + def.id + '">0</em>' +
        '</button>';
      }).join('');
    }

    function _updateSwatchCurationLaneCounts(grid) {
      var wrap = document.getElementById('swatchCurationLanes');
      if (!wrap || !grid) return;
      var state = getSwatchPopupState();
      wrap.querySelectorAll('.swatch-curation-lane').forEach(function(btn) {
        var lane = btn.dataset.lane || '';
        var seen = new Set();
        grid.querySelectorAll('.swatch-item[data-finish-id]').forEach(function(card) {
          var id = card.dataset.finishId || '';
          var type = card.dataset.finishType || '';
          var key = type + ':' + id;
          if (!id || seen.has(key)) return;
          if (_swatchCurationLaneMatch(card, lane)) seen.add(key);
        });
        btn.classList.toggle('active', lane === (state.filter || 'all'));
        var count = btn.querySelector('[data-lane-count]');
        if (count) count.textContent = String(seen.size);
        btn.hidden = seen.size === 0;
      });
    }

    Object.assign(global, {
      _renderSwatchPopupFilterControls: _renderSwatchPopupFilterControls,
      _swatchCurationLaneMatch: _swatchCurationLaneMatch,
      _swatchCurationLaneDefinitions: _swatchCurationLaneDefinitions,
      _renderSwatchCurationLanes: _renderSwatchCurationLanes,
      _updateSwatchCurationLaneCounts: _updateSwatchCurationLaneCounts
    });
  }

  global.SPBSwatchPopupLaneControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
