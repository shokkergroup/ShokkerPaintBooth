from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STATE_JS = REPO / "paint-booth-2-state-zones.js"
BOOT_JS = REPO / "paint-booth-6-ui-boot.js"
CSS = REPO / "paint-booth-v2.css"
HTML = REPO / "paint-booth-v2.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_spec_pattern_picker_has_search_grouping_and_inline_toggle_hooks():
    src = _read(STATE_JS)

    assert "function _buildSpecPatternPickerCards(currentId)" in src
    assert "function _buildSpecPatternTabButtons(gridId, activeCat)" in src
    assert "function filterSpecPatternPicker(gridId)" in src
    assert "function toggleSpecPickerCategory(gridId, catName)" in src
    assert "function toggleInlineSpecPatternGrid(gridId, tabsId)" in src
    assert "function _positionSpecThumbPopup(popup, anchorRect)" in src

    expected_inline_grids = [
        "specPatternGrid${i}",
        "overlaySpecPatternGrid${i}",
        "thirdOverlaySpecPatternGrid${i}",
        "fourthOverlaySpecPatternGrid${i}",
        "fifthOverlaySpecPatternGrid${i}",
    ]
    for grid_id in expected_inline_grids:
        assert f"toggleInlineSpecPatternGrid('{grid_id}'" in src

    assert 'id="fifthOverlaySpecPatternGrid${i}_tabs"' in src
    assert 'class="spec-pattern-thumb-card" data-spid="${sp.id}" data-category="${_sg5}"' in src
    assert "function _setSpecPatternPickerPopout(gridId, open)" in src
    assert "function _portalSpecPickerChrome(gridId, open)" in src
    assert "document.body.appendChild(node)" in src
    assert "spb-spec-picker-portal:" in src
    assert "function _renderSpecPatternToolbar(gridId)" in src
    assert "function closeSpecPatternPickerPopout(gridId)" in src
    assert "function closeOpenSpecPatternPickers()" in src
    assert "window.closeSpecPatternPickerPopout = closeSpecPatternPickerPopout" in src
    assert "e.key !== 'Escape'" in src
    assert "closeOpenSpecPatternPickers()" in src
    assert 'class="spec-picker-title">Spec Overlay Patterns' in src
    assert 'class="spec-picker-close"' in src
    assert "function _closeSpecPatternPickerChrome(gridId, tabsId)" in src
    assert "_ensureSpecCurationLanes(gridId, grid)" in src
    assert "grid.dataset.expandedCategory = grid.dataset.expandedCategory || 'All'" in src
    assert "firstCard.dataset.category" not in src
    assert "data-expandedCategory" not in src
    assert "grid.dataset.expandedCategory" in src
    assert "width:960px;height:576px" in src
    assert 'src="/api/spec-pattern-visual-preview/${sp.id}"' in src
    assert 'src="/api/spec-pattern-visual-preview/${sp.pattern}"' in src
    assert 'loading="lazy" decoding="async"' in src
    assert 'src="/api/spec-pattern-preview/' not in src
    assert "/thumbnails/spec_patterns/" not in src
    assert "?v=live" not in src
    assert "window._SHOKKER_SWATCH_V = Date.now()" not in src
    assert "spb_swatch_cache_version" in src


def test_spec_pattern_clearcoat_channel_uses_engine_c_token():
    src = _read(STATE_JS)

    assert "includes('CC')" not in src
    assert "'CC', this.checked" not in src
    assert "includes('C')" in src
    assert "'C', this.checked" in src


def test_spec_pattern_picker_css_uses_readable_browser_cards():
    css = _read(CSS)

    assert ".spec-picker-search" in css
    assert ".spec-picker-count" in css
    assert ".spec-curation-lanes" in css
    assert ".spec-curation-lane" in css
    assert ".spec-group-health" in css
    assert ".spec-group-needs-surgery" in css
    assert ".spec-pattern-group-heading" in css
    assert ".spec-pattern-group-heading.expanded" in css
    assert ".spec-group-arrow" in css
    assert "repeat(auto-fill, minmax(148px, 1fr))" in css
    assert "-webkit-line-clamp: 2" in css
    assert "width: min(960px, calc(100vw - 32px)) !important" in css
    assert ".spec-fav-btn" in css
    assert ".spec-rank-chip" in css
    assert ".spec-picker-title" in css
    assert ".spec-picker-close" in css
    assert ".spec-pattern-grid.spec-picker-popout-open" in css
    assert "display: grid !important" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(154px, 1fr)) !important" in css
    assert ".spec-pattern-grid.spec-picker-popout-open .spec-pattern-group-heading" in css
    assert "grid-column: 1 / -1" in css
    assert ".spec-pattern-grid.spec-picker-popout-open .spec-pattern-thumb-card" in css
    assert "width: 100% !important" in css
    assert "height: 106px !important" in css


def test_spec_pattern_picker_has_favorites_alias_search_and_ranking_chips():
    src = _read(STATE_JS)

    assert "SPEC_PATTERN_FAVORITES_KEY = 'shokker_spec_pattern_favorites'" in src
    assert "function toggleSpecPatternFavorite(patternId, event)" in src
    assert "function _rankSpecPatternForPicker(p, cat)" in src
    assert "function _renderSpecPatternRankChips(p, cat)" in src
    assert "function _specCurationLaneMatch(card, lane)" in src
    assert "function _ensureSpecCurationLanes(gridId, beforeNode)" in src
    assert "function _ensureSpecActiveLaneStatus(gridId, beforeNode)" in src
    assert "function _updateSpecActiveLaneStatus(grid, visibleCount)" in src
    assert "function openSpecActiveLanePlan(gridId, event)" in src
    assert "window.openSpecActiveLanePlan = openSpecActiveLanePlan" in src
    assert "function _updateSpecGroupHealthBadges(grid)" in src
    assert "spec-group-plan" in src
    assert "heading.dataset.planBucket" in src
    assert "function activateSpecGroupPlanBadge(gridId, bucketId, event, context)" in src
    assert "window.activateSpecGroupPlanBadge = activateSpecGroupPlanBadge" in src
    assert "activateSpecGroupPlanBadge(grid.id, planBadge.dataset.planBucket, event, context)" in src
    assert "function setSpecPatternCurationLane(gridId, lane, context)" in src
    assert "window.setSpecPatternCurationLane = setSpecPatternCurationLane" in src
    assert "_updateSpecActiveLaneStatus(grid, visible)" in src
    assert "Clear the lane to return to every spec overlay group" in src
    assert "Open the matching Spec Plan row" in src
    assert "_setPickerActiveLaneContext('spec', gridId" in src
    assert "focusSpecPatternCategoryStrategyLane(gridId, lane, event, category)" in src
    assert "var categoryMatch = _pickerCardMatchesContextCategory(card, activeContext)" in src
    assert "data-rank-overall" in src
    assert "data-owner-status" in src
    assert "data-handoff" in src
    assert "Strong Measured" in src
    assert "Render Estimate" in src
    assert "scores.confidence" in src
    assert "spec-pattern-favorites-heading" in src
    assert "data-search" in src
    for alias in ["carbon fiber", "flake sparkle", "chrome metal", "oil slick", "old rust weather"]:
        assert alias in src


def test_finish_library_uses_guided_catalog_rail_and_alias_search():
    src = _read(STATE_JS)

    assert "function _renderGuidedFinishCatalog(activeTab, groupMap, groupNames, activeTabId, itemType)" in src
    assert "finish-guided-catalog" in src
    assert "finish-category-rail" in src
    assert "finish-catalog-grid" in src
    assert "FINISH_LIBRARY_SEARCH_ALIASES" in src
    for alias in ["old", "rust", "weather", "chrome", "flake", "carbon", "mexico", "sun", "ocean", "brushed"]:
        assert f"{alias}:" in src
    assert "loading=\"lazy\" decoding=\"async\"" in src
    assert "_libraryActiveGroupByTab[activeLibraryTab] = '__all__'" in src


def test_finish_library_guided_catalog_css_is_responsive_and_card_based():
    css = _read(CSS)

    assert ".finish-guided-catalog" in css
    assert "grid-template-columns: minmax(118px, 32%) minmax(0, 1fr)" in css
    assert ".finish-rail-button" in css
    assert ".finish-catalog-grid" in css
    assert "repeat(auto-fit, minmax(218px, 1fr))" in css
    assert ".finish-catalog-card" in css
    assert "@media (max-width: 520px)" in css


def test_zone_dropdown_picker_is_large_readable_and_favorites_ranked():
    src = _read(STATE_JS)
    css = _read(CSS)
    html = _read(HTML)

    assert "function _enhanceSwatchPopupCards(currentId, pickerType)" in src
    assert "function _renderSwatchFavoritesGroup(kind, currentId)" in src
    assert 'data-swatch-contract="paint-left-spec-right"' in src
    assert 'swatch-split-frame' in src
    assert 'swatch-split-label-left">Paint' in src
    assert 'swatch-split-label-right">Spec' in src
    assert 'swatch-spec-unavailable' in src
    assert 'Preview unavailable' in src
    assert "function _catalogRankingForItem(item, type)" in src
    assert "function _getCatalogScorecardRow(itemId, type)" in src
    assert "function _catalogRankingFromScorecard(item, type, row, meta, patternMeta)" in src
    assert "function _getPickerOwnerRating(itemId, type)" in src
    assert "function _applyPickerOwnerRating(rank, item, type)" in src
    assert "function _rankKeywordScore(text, weights)" in src
    assert "confidence: 'Measured'" in src
    assert "out.confidence = 'Owner'" in src
    assert "confidence === 'Low'" in src
    assert "function setSwatchPopupFilter(filterName, context)" in src
    assert "function setSwatchPopupSort(sortName)" in src
    assert "function _applySwatchPopupSort(grid)" in src
    assert "function _renderSwatchPopupFilterControls(type)" in src
    assert "function _swatchCurationLaneMatch(card, lane)" in src
    assert "function _renderSwatchCurationLanes(type)" in src
    assert "function _updateSwatchCurationLaneCounts(grid)" in src
    assert "function _updateSwatchGroupHealthBadges(grid)" in src
    assert "function _pickerGroupHealthSummary(cards, matchFn)" in src
    assert "function _pickerCategoryStrategyForGroup(types, category)" in src
    assert "function _renderCategoryPlanBadgeElement(row, className)" in src
    assert "function _pickerLaneForStrategyBucket(bucketId)" in src
    assert "function _pickerLaneDisplay(lane, type, scope)" in src
    assert "let pickerActiveLaneContext = { main: null, spec: {} }" in src
    assert "function _pickerLaneContextFromStrategy(row, category, lane, scope)" in src
    assert "scopeMode: 'category'" in src
    assert "function _pickerContextUsesCategory(context)" in src
    assert "function _pickerCardMatchesContextCategory(card, context)" in src
    assert "function _setPickerActiveLaneContext(scope, gridId, context)" in src
    assert "function setMainPickerLaneScope(mode, event)" in src
    assert "window.setMainPickerLaneScope = setMainPickerLaneScope" in src
    assert "function resetSwatchPickerGuidedContext(event)" in src
    assert "window.resetSwatchPickerGuidedContext = resetSwatchPickerGuidedContext" in src
    assert "function setSpecPickerLaneScope(gridId, mode, event)" in src
    assert "window.setSpecPickerLaneScope = setSpecPickerLaneScope" in src
    assert "function resetSpecPickerGuidedContext(gridId, event)" in src
    assert "window.resetSpecPickerGuidedContext = resetSpecPickerGuidedContext" in src
    assert "function openSwatchActiveLanePlan(event)" in src
    assert "window.openSwatchActiveLanePlan = openSwatchActiveLanePlan" in src
    assert "function _updateSwatchActiveLaneStatus(grid, visibleCount)" in src
    assert "function _wireCategoryPlanBadgeAction(badge, handler)" in src
    assert "function activateSwatchGroupPlanBadge(bucketId, event, context)" in src
    assert "window.activateSwatchGroupPlanBadge = activateSwatchGroupPlanBadge" in src
    assert "badge.dataset.planLane = lane" in src
    assert "badge.dataset.planCategory = row.category || ''" in src
    assert "badge.setAttribute('role', 'button')" in src
    assert "setSwatchPopupFilter(lane, context || null)" in src
    assert "_updateSwatchActiveLaneStatus(grid, visibleCount)" in src
    assert "Clear the lane to return to the full grouped picker" in src
    assert "Reset guided context" in src
    assert "Search is scoped to this category lane" in src
    assert "Search covers this lane across all categories" in src
    assert "filterSwatchPopup(search ? search.value : '')" in src
    assert "This category" in src
    assert "All matching lane" in src
    assert "const categoryMatch = _pickerCardMatchesContextCategory(item, activeContext)" in src
    assert "Open the matching Category Plan row" in src
    assert "data-plan-category" in src
    assert "data-plan-lane" in src
    assert "data-picker-category" in src
    assert "data-picker-types" in src
    assert "swatch-group-plan" in src
    assert "Category health:" in src
    assert "Showcase" in src
    assert "Strong Measured" in src
    assert "Needs Owner Rating" in src
    assert "SPB-67 Surgery" in src
    assert "function collectPickerRankingRows(limit)" in src
    assert "window.collectPickerRankingRows = collectPickerRankingRows" in src
    assert "function collectPickerOwnerDisagreementRows(limit)" in src
    assert "window.collectPickerOwnerDisagreementRows = collectPickerOwnerDisagreementRows" in src
    assert "function collectPickerOwnerRatingReviewRows(scopeTypes, limit)" in src
    assert "window.collectPickerOwnerRatingReviewRows = collectPickerOwnerRatingReviewRows" in src
    assert "function exportPickerRatingReview(event, scopeName)" in src
    assert "function collectPickerCategoryStrategyRows(scopeTypes, limit)" in src
    assert "window.collectPickerCategoryStrategyRows = collectPickerCategoryStrategyRows" in src
    assert "function collectPickerConsolidatedCategoryProposal(scopeTypes)" in src
    assert "window.collectPickerConsolidatedCategoryProposal = collectPickerConsolidatedCategoryProposal" in src
    assert "function exportPickerConsolidatedCategoryProposal(event)" in src
    assert "spb-picker-consolidated-category-proposal-v1" in src
    assert "function toggleSwatchCategoryStrategyPanel(force)" in src
    assert "function exportPickerCategoryStrategy(event)" in src
    assert "spb-picker-category-strategy-v1" in src
    assert "proposal: collectPickerConsolidatedCategoryProposal(scopeTypes)" in src
    assert "Export All" in src
    assert "spb-picker-owner-rating-review-v1" in src
    assert "Owner / measured score gaps" in src
    assert "function _renderSwatchLowScorePanel(limit)" in src
    assert "function toggleSwatchLowScorePanel(force)" in src
    assert "function focusSwatchReviewCandidate(id, event)" in src
    assert "toggleSwatchPickerFavorite" in src
    assert "grid.insertAdjacentHTML('afterbegin', favHtml)" in src
    assert "popupW = Math.min(1500" in src
    assert "popupH = Math.min(1080" in src
    assert "data-search" in src
    assert "data-rank-overall" in src
    assert "data-sort-name" in src
    assert "sponsor_safe" in src
    assert "needs_review" in src
    assert "strong_measured" in src
    assert "needs_owner_rating" in src
    assert "spb67_surgery" in src
    assert "data-owner-status" in src
    assert "data-measured-overall" in src
    assert "data-handoff" in src
    assert "swatch-material-row" in src
    assert ".swatch-popup .swatch-catalog-card" in css
    assert ".swatch-split-frame" in css
    assert ".swatch-split-label-left" in css
    assert ".swatch-split-label-right" in css
    assert ".swatch-split-frame.swatch-spec-unavailable .swatch-split-error" in css
    assert ".swatch-picker-filter-row" in css
    assert ".swatch-filter-chip" in css
    assert ".swatch-picker-sort-buttons" in css
    assert ".swatch-sort-chip" in css
    assert ".swatch-review-chip" in css
    assert ".swatch-low-score-panel" in css
    assert ".swatch-low-score-row" in css
    assert ".swatch-category-strategy-panel" in css
    assert ".swatch-category-strategy-row" in css
    assert ".swatch-category-proposal-summary" in css
    assert ".swatch-category-proposal-card" in css
    assert ".swatch-category-plan-badge" in css
    assert ".swatch-owner-gap-panel" in css
    assert ".swatch-owner-gap-row" in css
    assert ".swatch-review-head-actions" in css
    assert ".swatch-material-chip" in css
    assert ".swatch-material-owner" in css
    assert ".swatch-picker-result-count" in css
    assert ".swatch-curation-lanes" in css
    assert ".swatch-curation-lane" in css
    assert ".swatch-active-lane-status" in css
    assert ".swatch-active-search-scope" in css
    assert ".swatch-active-lane-status .swatch-guided-reset" in css
    assert ".swatch-active-lane-metrics" in css
    assert ".swatch-active-lane-scope" in css
    assert ".swatch-active-lane-scope button.active" in css
    assert ".swatch-category-strategy-row-focus" in css
    assert ".swatch-group-health" in css
    assert ".swatch-group-plan" in css
    assert ".swatch-group-plan:focus-visible" in css
    assert ".swatch-group-plan-featurelanes" in css
    assert ".swatch-group-plan-mergearchive" in css
    assert ".swatch-group-needs-surgery" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(158px, 1fr))" in css
    assert ".swatch-rank-chip" in css
    assert ".swatch-fav-btn" in css
    assert "Split swatch: left paint finish, right spec finish" in html
    assert "swatchPopupFilterButtons" in html
    assert "swatchPopupSortButtons" in html
    assert "swatchPopupReviewBtn" in html
    assert "swatchCategoryStrategyBtn" in html
    assert "swatchLowScorePanel" in html
    assert "swatchCategoryStrategyPanel" in html
    assert "swatchCurationLanes" in html
    assert "swatchActiveLaneStatus" in html
    assert "swatchPopupResultCount" in html
    assert "paint-booth-0-catalog-scorecard.js" in html
    assert "paint-booth-0-picker-owner-ratings.js" in html


def test_spec_pattern_picker_has_review_queue_and_owner_rating_layer():
    src = _read(STATE_JS)
    css = _read(CSS)
    owner = _read(REPO / "paint-booth-0-picker-owner-ratings.js")

    assert "const PICKER_OWNER_RATINGS" in owner
    assert "monolithic:solar_wind" in owner
    assert "monolithic:x_ray" in owner
    assert "function _collectSpecPatternReviewRows(limit)" in src
    assert "function _renderSpecPatternOwnerGapPanel(gridId, limit)" in src
    assert "function toggleSpecPatternReviewQueue(gridId, force)" in src
    assert "function _ensureSpecPatternCategoryStrategyPanel(gridId)" in src
    assert "function _renderSpecPatternCategoryStrategyPanel(gridId, limit)" in src
    assert "function toggleSpecPatternCategoryStrategyPanel(gridId, force)" in src
    assert "function exportSpecPatternCategoryStrategy(event)" in src
    assert "function focusSpecPatternReviewCandidate(gridId, patternId, event)" in src
    assert "exportPickerRatingReview(event,'spec_pattern')" in src
    assert "spb-picker-spec-category-strategy-v1" in src
    assert "collectPickerConsolidatedCategoryProposal(['spec_pattern'])" in src
    assert "Spec overlay category plan" in src
    assert "Spec overlay proposal" in src
    assert "Spec Plan" in src
    assert "Spec overlay owner / measured gaps" in src
    assert "Search is scoped to this spec overlay category lane" in src
    assert "Search covers this spec lane across all overlay categories" in src
    assert "resetSpecPickerGuidedContext" in src
    assert "spec-review-chip" in src
    assert "spec-strategy-chip" in src
    assert "Spec overlay review queue" in src
    assert ".spec-review-chip" in css
    assert ".spec-strategy-chip" in css
    assert ".spec-review-panel" in css
    assert ".spec-category-strategy-panel" in css
    assert ".spec-active-lane-status" in css
    assert ".spec-group-plan" in css
    assert ".spec-group-plan-spb67surgery" in css
    assert ".spec-owner-gap-panel" in css
    assert ".spec-rank-owner" in css


def test_split_swatch_right_side_uses_spec_finish_visualization():
    server = _read(REPO / "server.py")

    assert "def _render_spec_swatch_bytes(finish_type, finish_key, size, seed):" in server
    assert "Right panel: actual spec behavior visualization" in server
    assert "png_right = _render_spec_swatch_bytes(finish_type, finish_key, size, seed)" in server
    assert "left=paint/material preview, right=spec-map behavior preview" in _read(STATE_JS)


def test_fullscreen_finish_browser_defaults_to_guided_catalog_lanes():
    boot = _read(BOOT_JS)
    html = _read(HTML)
    css = _read(CSS)

    assert 'let finishBrowserLane = \'featured\'' in boot
    assert "FINISH_BROWSER_LANES" in boot
    assert "function setFinishBrowserLane(lane)" in boot
    assert "function renderFinishBrowserRail(counts)" in boot
    assert "100k+ generated combinations" in boot
    assert "finishBrowserLane = 'featured'" in boot
    assert "finishBrowserRail" in html
    assert "finish-browser-guided" in html
    assert ".finish-browser-rail" in css
    assert "grid-template-columns: 172px minmax(0, 1fr)" in css


def test_spec_pattern_picker_changes_are_synced_to_runtime_mirrors():
    state_src = _read(STATE_JS)
    css_src = _read(CSS)
    html_src = _read(HTML)
    scorecard_src = _read(REPO / "paint-booth-0-catalog-scorecard.js")
    owner_src = _read(REPO / "paint-booth-0-picker-owner-ratings.js")

    mirror_state_paths = [
        REPO / "electron-app/server/paint-booth-2-state-zones.js",
        REPO / "electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js",
    ]
    mirror_css_paths = [
        REPO / "electron-app/server/paint-booth-v2.css",
        REPO / "electron-app/server/pyserver/_internal/paint-booth-v2.css",
    ]
    mirror_html_paths = [
        REPO / "electron-app/server/paint-booth-v2.html",
        REPO / "electron-app/server/pyserver/_internal/paint-booth-v2.html",
    ]
    mirror_scorecard_paths = [
        REPO / "electron-app/server/paint-booth-0-catalog-scorecard.js",
        REPO / "electron-app/server/pyserver/_internal/paint-booth-0-catalog-scorecard.js",
    ]
    mirror_owner_paths = [
        REPO / "electron-app/server/paint-booth-0-picker-owner-ratings.js",
        REPO / "electron-app/server/pyserver/_internal/paint-booth-0-picker-owner-ratings.js",
    ]

    for path in mirror_state_paths:
        assert _read(path) == state_src
    for path in mirror_css_paths:
        assert _read(path) == css_src
    for path in mirror_html_paths:
        assert _read(path) == html_src
    for path in mirror_scorecard_paths:
        assert _read(path) == scorecard_src
    for path in mirror_owner_paths:
        assert _read(path) == owner_src
