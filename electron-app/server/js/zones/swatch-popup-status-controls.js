(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const getSwatchPopupState = deps.getSwatchPopupState || function() { return {}; };
        const getPickerActiveLaneContext = deps.getPickerActiveLaneContext || function() { return { main: null, spec: {} }; };
        const setMainPickerActiveLaneContext = deps.setMainPickerActiveLaneContext || function() {};
        const setSpecPickerActiveLaneContext = deps.setSpecPickerActiveLaneContext || function() {};
        const swatchCurationLaneDefinitions = deps.swatchCurationLaneDefinitions || function() { return []; };
        const specCurationLaneDefinitions = deps.specCurationLaneDefinitions || function() { return []; };
        const pickerStrategyBucketId = deps.pickerStrategyBucketId || function(row) { return row && row.bucket || ''; };
        const filterSwatchPopup = deps.filterSwatchPopup || function() {};
        const toggleSwatchCategoryStrategyPanel = deps.toggleSwatchCategoryStrategyPanel || function() {};
        const escapeHtml = deps.escapeHtml || function(value) {
            return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
            });
        };

        function _pickerLaneDisplay(lane, type, scope) {
            const value = lane || 'all';
            if (value === 'all') return { id: 'all', label: 'All', detail: 'Full catalog' };
            const defs = scope === 'spec' ? specCurationLaneDefinitions() : swatchCurationLaneDefinitions(type);
            const found = defs.find(function(def) { return def.id === value; });
            if (found) return found;
            return { id: value, label: value.replace(/_/g, ' '), detail: 'Filtered catalog lane' };
        }

        function _pickerLaneContextFromStrategy(row, category, lane, scope) {
            if (!row) return null;
            return {
                scope: scope || 'main',
                scopeMode: 'category',
                category: category || row.category || '',
                lane: lane || 'all',
                bucket: pickerStrategyBucketId(row),
                recommendation: row.recommendation || 'Keep and monitor',
                reason: row.reason || 'No category plan reason recorded yet.',
                total: row.total || 0,
                strong: (row.showcase || 0) + (row.strongMeasured || 0),
                surgery: row.surgery || 0,
                needsOwnerRating: row.needsOwnerRating || 0,
                ownerRated: row.ownerRated || 0
            };
        }

        function _pickerContextUsesCategory(context) {
            return !!(context && context.scopeMode === 'category' && context.category);
        }

        function _pickerCardMatchesContextCategory(card, context) {
            if (!card || !_pickerContextUsesCategory(context)) return true;
            const wanted = String(context.category || '').trim().toLowerCase();
            const group = card.closest ? card.closest('.swatch-group') : null;
            const groupCat = group ? String(group.dataset.pickerCategory || '').trim().toLowerCase() : '';
            const cardCat = String(card.dataset.category || card.dataset.homeCategory || '').trim().toLowerCase();
            return groupCat === wanted || cardCat === wanted;
        }

        function _setPickerActiveLaneContext(scope, gridId, context) {
            if (scope === 'spec') {
                setSpecPickerActiveLaneContext(gridId || 'spec', context || null);
                return;
            }
            setMainPickerActiveLaneContext(context || null);
        }

        function setMainPickerLaneScope(mode, event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            const pickerContext = getPickerActiveLaneContext();
            const context = pickerContext.main;
            if (!context) return;
            context.scopeMode = mode === 'all' ? 'all' : 'category';
            const search = document.getElementById('swatchSearchInput');
            filterSwatchPopup(search ? search.value : '');
        }

        function resetSwatchPickerGuidedContext(event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            getSwatchPopupState().filter = 'all';
            _setPickerActiveLaneContext('main', null, null);
            const buttons = document.getElementById('swatchPopupFilterButtons');
            if (buttons) {
                buttons.querySelectorAll('.swatch-filter-chip').forEach(function(btn) {
                    btn.classList.toggle('active', btn.dataset.filter === 'all');
                });
            }
            const search = document.getElementById('swatchSearchInput');
            filterSwatchPopup(search ? search.value : '');
        }

        function _pickerFindPlanRow(panel, category, lane) {
            if (!panel) return null;
            const wantedCategory = String(category || '').trim().toLowerCase();
            const wantedLane = String(lane || '').trim();
            const rows = Array.prototype.slice.call(panel.querySelectorAll('.swatch-category-strategy-row'));
            return rows.find(function(row) {
                const catMatch = !wantedCategory || String(row.dataset.planCategory || '').trim().toLowerCase() === wantedCategory;
                const laneMatch = !wantedLane || String(row.dataset.planLane || '') === wantedLane;
                return catMatch && laneMatch;
            }) || rows.find(function(row) {
                return wantedCategory && String(row.dataset.planCategory || '').trim().toLowerCase() === wantedCategory;
            }) || null;
        }

        function _highlightPickerPlanRow(row) {
            if (!row) return;
            row.classList.add('swatch-category-strategy-row-focus');
            row.setAttribute('tabindex', '-1');
            row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            try { row.focus({ preventScroll: true }); } catch (_) {}
            setTimeout(function() {
                if (row) row.classList.remove('swatch-category-strategy-row-focus');
            }, 1800);
        }

        function openSwatchActiveLanePlan(event) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            const pickerContext = getPickerActiveLaneContext();
            const context = pickerContext.main;
            toggleSwatchCategoryStrategyPanel(true);
            const panel = document.getElementById('swatchCategoryStrategyPanel');
            const row = _pickerFindPlanRow(panel, context && context.category, context && context.lane);
            _highlightPickerPlanRow(row);
        }

        function _updateSwatchActiveLaneStatus(grid, visibleCount) {
            const status = document.getElementById('swatchActiveLaneStatus');
            if (!status) return;
            const state = getSwatchPopupState();
            const lane = state.filter || 'all';
            const popup = document.getElementById('swatchPopup');
            if (popup) popup.dataset.activeLane = lane;
            if (lane === 'all') {
                status.hidden = true;
                status.innerHTML = '';
                return;
            }
            const type = grid ? (grid.dataset.pickerType || state.type || 'base') : (state.type || 'base');
            const info = _pickerLaneDisplay(lane, type, 'main');
            const pickerContext = getPickerActiveLaneContext();
            const context = pickerContext.main;
            const hasContext = context && context.lane === lane;
            const categoryScoped = _pickerContextUsesCategory(context);
            const scopeCopy = hasContext
                ? (categoryScoped ? 'Search is scoped to this category lane; reset returns to the full grouped picker.' : 'Search covers this lane across all categories; reset returns to the full grouped picker.')
                : 'Search is filtered by this guided lane; reset returns to the full grouped picker.';
            const visible = Number.isFinite(visibleCount) ? visibleCount : 0;
            status.hidden = false;
            status.dataset.activeLane = lane;
            status.innerHTML =
                '<div class="swatch-active-lane-copy">' +
                    '<strong>Viewing ' + escapeHtml(info.label) + (hasContext && context.category ? ' in ' + escapeHtml(context.category) : '') + '</strong>' +
                    '<span>' + escapeHtml(hasContext ? (context.recommendation + ': ' + context.reason) : info.detail) + ' - ' + escapeHtml(String(visible)) + ' visible.</span>' +
                    '<span class="swatch-active-search-scope">' + escapeHtml(scopeCopy) + '</span>' +
                    (hasContext ? '<div class="swatch-active-lane-metrics"><em>Total ' + escapeHtml(String(context.total)) + '</em><em>Strong ' + escapeHtml(String(context.strong)) + '</em><em>Surgery ' + escapeHtml(String(context.surgery)) + '</em><em>Rate ' + escapeHtml(String(context.needsOwnerRating)) + '</em></div>' : '') +
                    (hasContext ? '<div class="swatch-active-lane-scope" role="group" aria-label="Active lane scope"><button type="button" class="' + (categoryScoped ? 'active' : '') + '" onclick="setMainPickerLaneScope(\'category\',event)" title="Show this lane only inside the source category">This category</button><button type="button" class="' + (!categoryScoped ? 'active' : '') + '" onclick="setMainPickerLaneScope(\'all\',event)" title="Show this lane across every category">All matching lane</button></div>' : '') +
                '</div>' +
                (hasContext ? '<button type="button" onclick="openSwatchActiveLanePlan(event)" title="Open the matching Category Plan row">Open plan</button>' : '') +
                '<button type="button" class="swatch-guided-reset" onclick="resetSwatchPickerGuidedContext(event)" title="Clear the lane to return to the full grouped picker without changing search, favorites, or sort">Reset guided context</button>';
        }

        Object.assign(global, {
            _pickerLaneDisplay: _pickerLaneDisplay,
            _pickerLaneContextFromStrategy: _pickerLaneContextFromStrategy,
            _pickerContextUsesCategory: _pickerContextUsesCategory,
            _pickerCardMatchesContextCategory: _pickerCardMatchesContextCategory,
            _setPickerActiveLaneContext: _setPickerActiveLaneContext,
            setMainPickerLaneScope: setMainPickerLaneScope,
            resetSwatchPickerGuidedContext: resetSwatchPickerGuidedContext,
            _pickerFindPlanRow: _pickerFindPlanRow,
            _highlightPickerPlanRow: _highlightPickerPlanRow,
            openSwatchActiveLanePlan: openSwatchActiveLanePlan,
            _updateSwatchActiveLaneStatus: _updateSwatchActiveLaneStatus
        });
    }

    global.SPBSwatchPopupStatusControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
