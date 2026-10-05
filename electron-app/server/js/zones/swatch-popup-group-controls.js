(function(global) {
    'use strict';

    function install(deps) {
        deps = deps || {};
        const internalReviewUiEnabled = !!deps.internalReviewUiEnabled;
        const pickerLaneForStrategyBucket = deps.pickerLaneForStrategyBucket || function() { return 'all'; };
        const setSwatchPopupFilter = deps.setSwatchPopupFilter || function() {};
        const pickerGroupHealthSummary = deps.pickerGroupHealthSummary || function() {
            return { total: 0, showcase: 0, strong: 0, surgery: 0 };
        };
        const swatchCurationLaneMatch = deps.swatchCurationLaneMatch || function() { return false; };
        const pickerCategoryStrategyForGroup = deps.pickerCategoryStrategyForGroup || function() { return null; };
        const pickerStrategyBucketId = deps.pickerStrategyBucketId || function(row) { return row && row.bucket || ''; };
        const renderGroupHealthBadge = deps.renderGroupHealthBadge || function() { return null; };
        const renderCategoryPlanBadgeElement = deps.renderCategoryPlanBadgeElement || function() { return null; };
        const wireCategoryPlanBadgeAction = deps.wireCategoryPlanBadgeAction || function() {};
        const pickerLaneContextFromStrategy = deps.pickerLaneContextFromStrategy || function() { return null; };

        function activateSwatchGroupPlanBadge(bucketId, event, context) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            const group = event && event.currentTarget ? event.currentTarget.closest('.swatch-group') : null;
            if (group) group.classList.remove('collapsed');
            const lane = pickerLaneForStrategyBucket(bucketId);
            setSwatchPopupFilter(lane, context || null);
        }

        function _updateSwatchGroupHealthBadges(grid) {
            if (!grid) return;
            grid.querySelectorAll('.swatch-group').forEach(function(group) {
                const label = group.querySelector('.swatch-group-label');
                if (!label) return;
                label.querySelectorAll('.swatch-group-health').forEach(function(node) { node.remove(); });
                label.querySelectorAll('.swatch-group-plan').forEach(function(node) { node.remove(); });
                if (!internalReviewUiEnabled) {
                    group.classList.remove('swatch-group-underbuilt', 'swatch-group-needs-surgery');
                    group.dataset.planBucket = '';
                    return;
                }
                const cards = group.querySelectorAll('.swatch-item[data-finish-id]');
                const summary = pickerGroupHealthSummary(cards, swatchCurationLaneMatch);
                group.classList.toggle('swatch-group-underbuilt', summary.total > 0 && summary.total <= 2);
                group.classList.toggle('swatch-group-needs-surgery', summary.surgery >= Math.max(2, summary.showcase + summary.strong));
                const category = group.dataset.pickerCategory || '';
                const types = String(group.dataset.pickerTypes || '').split(',').map(function(type) { return type.trim(); }).filter(Boolean);
                const strategyRow = pickerCategoryStrategyForGroup(types, category);
                group.dataset.planBucket = strategyRow ? pickerStrategyBucketId(strategyRow) : '';
                if (!summary.total) return;
                label.appendChild(renderGroupHealthBadge(summary, 'swatch-group-health'));
                const planBadge = renderCategoryPlanBadgeElement(strategyRow, 'swatch-group-plan');
                if (planBadge) {
                    wireCategoryPlanBadgeAction(planBadge, function(event) {
                        const context = pickerLaneContextFromStrategy(strategyRow, category, planBadge.dataset.planLane, 'main');
                        activateSwatchGroupPlanBadge(planBadge.dataset.planBucket, event, context);
                    });
                    label.appendChild(planBadge);
                }
            });
        }

        Object.assign(global, {
            activateSwatchGroupPlanBadge: activateSwatchGroupPlanBadge,
            _updateSwatchGroupHealthBadges: _updateSwatchGroupHealthBadges
        });
    }

    global.SPBSwatchPopupGroupControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
