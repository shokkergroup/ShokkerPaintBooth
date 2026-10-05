from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_concat(paths) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in paths if p.exists())


# SPB UI modernization styles were split out of the monolithic paint-booth-v2.css
# into css/*.css (ui-modernization-2026050{8,9,10}.css, ui-fixes-*.css,
# look-theme-prelude.css, look-overdrive.css, ...). Read the base sheet plus every
# split sheet so each marker/selector is still asserted at its NEW home.
def _read_css() -> str:
    return _read_concat([REPO / "paint-booth-v2.css", *sorted((REPO / "css").glob("*.css"))])


# Likewise, zone UI helpers/markup were extracted out of
# paint-booth-2-state-zones.js into js/zones/*.js modules (e.g. the base-overlay
# state controls in js/zones/zone-base-overlay-state-controls.js, the picker
# ranking explainer in js/zones/swatch-popup-ranking-controls.js, etc.). Read the
# monolith plus every zone module so relocated symbols are still asserted.
def _read_state_zones() -> str:
    return _read_concat(
        [REPO / "paint-booth-2-state-zones.js", *sorted((REPO / "js" / "zones").glob("*.js"))]
    )


# Back-compat shims: the helpers above replace the old `Path` constants. Tests below
# read via these so the source location is centralized.
CSS = REPO / "paint-booth-v2.css"
STATE_ZONES = REPO / "paint-booth-2-state-zones.js"


def test_zone_workflow_surface_has_modernized_layout_layer():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-08: Zone Workflow Surface" in css
    assert ".zone-toolbar" in css
    assert "position: sticky !important" in css
    # SPB-2026-05-19 (owner): zone toolbar moved to a 3-equal-column grid (search on
    # row 1, buttons share row 2) in css/ui-modernization-20260508.css.
    assert "grid-template-columns: repeat(3, minmax(0, 1fr)) !important" in css
    assert ".zone-toolbar #zoneSearchInput" in css
    assert ".zone-card-header" in css
    assert "grid-template-columns: 13px 24px auto 14px minmax(74px, 1fr) minmax(92px, 1.15fr) auto auto auto auto auto !important" in css
    assert ".zone-summary" in css
    assert "max-width: none !important" in css
    assert ".zone-editor-float .section-collapsible" in css
    assert ".zone-editor-float .section-header" in css
    assert "@media (max-width: 980px)" in css


def test_right_panel_workbench_has_modernized_layout_layer():
    css = _read_css()
    canvas = _read(REPO / "paint-booth-3-canvas.js")
    html = _read(REPO / "paint-booth-v2.html")

    assert "SPB UI MODERNIZATION 2026-05-08: Right Panel Workbench" in css
    assert "#rightPanelTabs" in css
    assert "grid-template-columns: 1fr 1fr !important" in css
    assert "#rightPanel .rp-tab.active" in css
    assert "#rpLayersContent > div:first-child" in css
    assert "#layerPanelContent .layer-row.selected" in css
    assert "#layerPanelContent .layer-row-hidden" in css
    assert "#layerPanelContent .layer-thumb" in css
    assert "#layerPanelContent .layer-row-details" in css
    assert "#rpFinishesContent .finish-search-bar" in css
    assert "#rpFinishesContent #btnFavoritesOnly" in css
    assert "SPB UI MODERNIZATION 2026-05-09: Right Panel Command Polish" in css
    assert "#rightPanel .right-panel-actionbar" in css
    assert "#rightPanel .right-panel-primary-action" in css
    assert "#layerPanelContent .layer-empty-state" in css
    assert "#layerPanelContent .layer-row[role=\"button\"]:focus-visible" in css
    assert "#rpFinishesContent .finish-search-bar:focus-within" in css
    assert "#rpFinishesContent .finish-header-meta" in css
    assert 'class="right-panel-actionbar"' in html
    assert 'class="btn btn-sm right-panel-primary-action"' in html
    assert 'class="right-panel-secondary-action"' in html
    assert 'class="right-panel-hint"' in html
    assert 'class="layer-empty-state"' in html
    assert 'class="finish-header-meta"' in html
    assert "class=\"layer-row${selected ? ' selected' : ''}${vis ? '' : ' layer-row-hidden'}\"" in canvas
    assert "role=\"button\" tabindex=\"0\" aria-label=\"Select layer ${_safeName}\"" in canvas
    assert "onkeydown=\"if(event.key==='Enter'||event.key===' '){event.preventDefault();selectPSDLayer('${l.id}')}\"" in canvas
    assert "class=\"layer-eye-toggle\"" in canvas
    assert "class=\"layer-name\"" in canvas
    assert "class=\"layer-row-details\"" in canvas


def test_picker_cards_explain_rankings_across_bases_and_spec_patterns():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI MODERNIZATION 2026-05-08: Picker Ranking Explainability" in css
    assert ".picker-rank-explain" in css
    assert ".picker-rank-explain-strong" in css
    assert ".picker-rank-explain-watch" in css
    assert ".picker-rank-explain-rework" in css
    assert ".swatch-rank-row" in css
    assert ".spec-rank-row" in css
    # Ranking explainer moved to js/zones/swatch-popup-ranking-controls.js. The
    # per-type call was unified into one generic _renderPickerRankingExplainer(r,
    # type, escapeHtml) that branches on type === 'spec_pattern' internally, so the
    # spec_pattern path is asserted via that branch rather than a dedicated call.
    assert "function _pickerRankingMetricSummary(rank, type)" in state_zones
    assert "function _renderPickerRankingExplainer(rank, type, escapeFn)" in state_zones
    assert "_renderPickerRankingExplainer(r, type, escapeHtml)" in state_zones
    assert "_rankTierForOverall(out.overall, type === 'spec_pattern' || type === 'spec-pattern')" in state_zones
    assert "Strongest:" in state_zones
    assert "Weakest:" in state_zones


def test_header_and_preview_command_surface_has_modernized_controls():
    css = _read_css()
    html = _read(REPO / "paint-booth-v2.html")

    assert "SPB UI MODERNIZATION 2026-05-08: Header and Preview Command Surface" in css
    assert ".header-brand" in css
    assert ".header-field.field-id" in css
    assert ".ui-scale-control" in css
    assert ".header-shortcut-btn" in css
    assert "#serverStatus" in css
    assert "#renderFloat .render-float-actions" in css
    assert "#renderFloat .render-shortcuts-btn" in css
    assert "SPB UI MODERNIZATION 2026-05-09: Command Shelf + Status Bar Polish" in css
    assert "height: calc(100vh - 48px - 20px) !important" in css
    assert "#renderFloat .primary-render-action" in css
    assert "left: clamp(168px, calc(50% - 180px), 50%) !important" in css
    assert "max-width: min(340px, calc(100vw - 40px)) !important" in css
    assert 'content: "Ctrl+R" !important' in css
    assert "#renderFloat .render-progress-bar" in css
    assert ".zoom-controls .zoom-level" in css
    assert ".canvas-display-mode-group" in css
    assert ".canvas-display-mode-group .zoom-btn[aria-pressed=\"true\"]" in css
    assert "#globalStatusBar.global-status-bar" in css
    assert "flex: 0 0 20px !important" in css
    assert "#globalStatusBar .status-chip" in css
    assert "#globalStatusBar .status-chip-tool" in css
    assert "#globalStatusBar .status-color-swatch" in css
    assert ".split-pane-label" in css
    assert 'class="ui-scale-control"' in html
    assert 'class="ui-scale-btn"' in html
    assert 'class="gear-btn header-shortcut-btn"' in html
    assert 'class="render-float-actions"' in html
    assert 'class="btn-render primary-render-action"' in html
    assert 'class="render-shortcuts-btn"' in html
    assert 'class="canvas-display-mode-group"' in html
    assert 'class="global-status-bar"' in html
    assert 'class="status-chip status-chip-tool"' in html
    assert 'class="status-chip status-chip-zone"' in html
    assert 'class="status-chip status-chip-layer"' in html
    assert 'class="status-color-swatch"' in html


def test_zone_rail_anti_clipping_keeps_zone_names_prioritized():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI FIX 2026-05-08: Zone Rail Anti-Clipping" in css
    assert "SPB UI MODERNIZATION 2026-05-08: Zone Rail Action Group" in css
    assert "SPB UI FIX 2026-05-08: Zone Rail Selected Row Breathing Room" in css
    assert "#zoneList .zone-card-header" in css
    assert "grid-template-columns: 14px 24px 14px minmax(96px, 1fr) auto auto !important" in css
    assert "grid-template-columns: 14px 24px 14px minmax(0, 1fr) auto !important" in css
    assert "#zoneList .zone-card-header .zone-name-input" in css
    assert "#zoneList .zone-card-header .zone-card-actions" in css
    assert "text-overflow: ellipsis !important" in css
    assert "#zoneList .zone-card:not(.selected):not(:hover) .zone-summary" in css
    assert "display: none !important" in css
    assert "#zoneList .zone-card.selected .zone-card-header" in css
    assert "#zoneList .zone-card:hover .zone-card-header" in css
    assert "grid-template-columns: 14px 24px 14px minmax(94px, 1fr) !important" in css
    assert "grid-row: 2 !important" in css
    assert "grid-row: 3 !important" in css
    assert "#zoneList .zone-card:not(.selected):not(:hover) .zone-card-actions" in css
    assert "grid-template-columns: 14px 24px 14px minmax(96px, 1fr) !important" in css
    # Zone card row markup moved to js/zones/zone-card-render-controls.js and now
    # builds the action group via string concatenation (var i loop) instead of a
    # template literal.
    assert 'class="zone-card-actions"' in state_zones
    assert 'aria-label="Zone \' + (i + 1) + \' actions"' in state_zones


def test_zone_detail_header_uses_identity_actions_and_window_groups():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI MODERNIZATION 2026-05-08: Zone Detail Header Workbench" in css
    assert ".zone-editor-float .zone-detail-identity" in css
    assert ".zone-editor-float .zone-detail-actions" in css
    assert ".zone-editor-float .zone-detail-window-actions" in css
    assert 'grid-template-areas:' in css
    assert '"identity window"' in css
    assert '"actions actions"' in css
    assert "overflow-x: auto !important" in css
    assert 'class="zone-detail-identity"' in state_zones
    assert 'class="zone-detail-actions"' in state_zones
    assert 'role="toolbar" aria-label="Zone ${i + 1} quick actions"' in state_zones
    assert 'class="zone-detail-window-actions"' in state_zones
    assert 'class="btn btn-sm zone-detail-action-btn zone-detail-shokk-btn"' in state_zones


def test_zone_detail_body_controls_have_modernized_density_and_fit():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-08: Zone Detail Control Polish" in css
    assert ".zone-editor-float .zone-detail-body" in css
    assert ".zone-editor-float .quick-colors" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(58px, 1fr)) !important" in css
    assert ".zone-editor-float .quick-color-btn" in css
    assert ".zone-editor-float .color-text-row" in css
    assert ".zone-editor-float .color-hex-row" in css
    assert ".zone-editor-float .color-tol-row" in css
    assert ".zone-editor-float .stack-control-group" in css
    assert ".zone-editor-float .color-text-input" in css
    assert ".zone-editor-float .hex-code-input" in css
    assert ".zone-editor-float .stack-val" in css
    assert ".zone-editor-float .swatch-trigger" in css
    assert "accent-color: #34d399 !important" in css
    assert "flex-wrap: wrap !important" in css


def test_zone_detail_finish_workflow_sections_are_vertical_and_legacy_panels_disabled():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "class=\"zone-workflow-panels\"" in state_zones
    assert "html += `<div class=\"zone-workflow-panels\">" in state_zones
    assert "pHtml += specPatternsHtml;" in state_zones
    assert "id=\"sectionSpecPatterns${i}\"" in state_zones
    assert "id=\"sectionPattern${i}\"" in state_zones
    assert "id=\"sectionOverlays${i}\"" in state_zones
    base_close = state_zones.index("html += `</div>`; // close section-collapsible BASE wrapper")
    workflow_start = state_zones.index("html += `<div class=\"zone-workflow-panels\">")
    overlays_start = state_zones.index("id=\"sectionOverlays${i}\"")
    assert base_close < workflow_start < overlays_start
    assert "BASE OVERLAY LAYERS" in state_zones
    assert ".zone-editor-float .zone-workflow-panels" in css
    assert "flex-direction: column !important" in css
    assert ".zone-editor-float .zone-workflow-panels > .section-collapsible" in css
    assert "Legacy V1 material overrides are no longer rendered in the zone popout." in state_zones
    assert "if (false) html += `<div class=\"zone-finish-row intensity-row-stacked\"" in state_zones
    assert "if (false && (zone.base || zone.finish))" in state_zones


def test_base_overlay_layers_have_landmark_headers_and_client_picker_cleanup():
    css = _read_css()
    state_zones = _read_state_zones()
    html = _read(REPO / "paint-booth-v2.html")

    assert "SPB UI/UX 2026-05-13: Base Overlay Layer Landmarks + Client Picker Cleanup" in css
    for layer_class, layer_label in [
        ("base-overlay-layer-second", "2ND"),
        ("base-overlay-layer-third", "3RD"),
        ("base-overlay-layer-fourth", "4TH"),
        ("base-overlay-layer-fifth", "5TH"),
    ]:
        assert layer_class in state_zones
        assert layer_class in css
        assert f'content: "{layer_label}" !important' in css
    assert "position: sticky !important" in css
    assert "border-left: 4px solid var(--overlay-layer-accent) !important" in css
    assert "PICKER_INTERNAL_REVIEW_UI_ENABLED = false" in state_zones
    assert "swatch-client-cues" in state_zones
    assert "spec-client-cues" in state_zones
    assert "sorts.push(['needs_review', 'Needs Review']);" in state_zones
    assert "PICKER_INTERNAL_REVIEW_UI_ENABLED) {" in state_zones
    assert "group.classList.remove('swatch-group-underbuilt', 'swatch-group-needs-surgery');" in state_zones
    assert "heading.classList.remove('spec-group-underbuilt', 'spec-group-needs-surgery');" in state_zones
    assert "Release-facing picker cues hide internal scorecard details." in state_zones
    assert "Picker cues are simplified for release browsing." in state_zones
    assert ".swatch-popup #swatchPopupReviewBtn" in css
    assert ".spec-picker-toolbar .spec-strategy-chip" in css
    assert "display: none !important;" in css
    assert 'id="swatchPopupReviewBtn"\n                    onclick="toggleSwatchLowScorePanel()" hidden aria-hidden="true"' in html
    assert 'id="swatchCategoryStrategyBtn"\n                    onclick="toggleSwatchCategoryStrategyPanel()" hidden aria-hidden="true"' in html


def test_swatch_picker_catalog_shell_has_large_readable_panel_controls():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-08: Swatch Picker Catalog Shell" in css
    assert ".swatch-popup-search" in css
    assert "position: sticky !important" in css
    assert ".swatch-picker-filter-row" in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(160px, auto) auto auto auto !important" in css
    assert ".swatch-filter-chip" in css
    assert ".swatch-sort-chip" in css
    assert ".swatch-review-chip" in css
    assert ".swatch-preview-on-paint-row" in css
    assert ".swatch-curation-lanes" in css
    assert "grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)) !important" in css
    assert ".swatch-popup-grid" in css
    assert ".swatch-group-label" in css
    assert ".swatch-grid-row" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(178px, 1fr)) !important" in css
    assert ".swatch-popup .swatch-catalog-card" in css


def test_swatch_picker_live_fit_guard_preserves_grid_space():
    css = _read_css()

    assert "SPB UI FIX 2026-05-08: Swatch Picker Live Fit Guard" in css
    assert ".swatch-popup.active" in css
    assert "max-width: calc(100vw - 16px) !important" in css
    assert "max-height: calc(100vh - 16px) !important" in css
    assert ".swatch-popup-search," in css
    assert "flex: 0 0 auto !important" in css
    assert "max-height: 152px !important" in css
    assert ".swatch-curation-lanes" in css
    assert "max-height: 142px !important" in css
    assert ".swatch-popup-grid" in css
    assert "min-height: min(320px, 48vh) !important" in css
    assert "scrollbar-gutter: stable !important" in css
    assert "@media (max-height: 820px)" in css
    assert "min-height: 166px !important" in css


def test_zone_editor_emergency_followup_keeps_controls_contained():
    css = _read_css()
    state_zones = _read_state_zones()
    canvas = _read(REPO / "paint-booth-3-canvas.js")

    assert "SPB UI FIX 2026-05-08: Zone Placement + Spec Pattern Controls" in css
    assert ".zone-editor-float .zone-target-mode" in css
    assert "grid-template-columns: minmax(0, 1fr) !important" in css
    assert ".zone-editor-float .spec-picker-toolbar.spec-picker-inline-open" in css
    assert ".zone-editor-float .spec-pattern-grid.spec-picker-inline-open" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(108px, 1fr)) !important" in css
    assert "max-height: min(340px, 48vh) !important" in css
    assert "var isLayerChanger = _isZoneSpecLayerPicker(gridId);" in state_zones
    assert "spec-picker-inline-open" in state_zones
    assert ".spec-pattern-grid.spec-picker-popout-open, .spec-pattern-grid.spec-picker-inline-open" in state_zones
    assert "let previewWatchdogTimer = null;" in canvas
    assert "let previewRetryTimer = null;" in canvas
    assert "const PREVIEW_REQUEST_TIMEOUT_MS = 18000;" in canvas
    assert "const PREVIEW_MAX_AUTO_RETRIES = 2;" in canvas
    assert "function _finishPreviewRequest(state, text)" in canvas
    assert "function _schedulePreviewRecovery(zoneHash, reason)" in canvas
    assert "AbortSignal.any([previewAbortController.signal, AbortSignal.timeout(PREVIEW_REQUEST_TIMEOUT_MS)])" in canvas
    assert "resp.status === 429" in canvas
    assert "_finishPreviewRequest('retrying', 'Server busy - retrying')" in canvas
    assert "_schedulePreviewRecovery(zoneHash, 'busy')" in canvas
    assert "Preview timed out" in canvas
    assert "Preview reset" in canvas
    assert "previewTimedOutVersion === thisVersion" in canvas
    assert "badge.dataset.state = state || '';" in canvas
    assert "Preview failed or timed out. Click to reset and retry." in canvas
    assert ".preview-status.retrying" in css
    assert "const LIVE_PREVIEW_MAX_SCALE = 1.0;" in canvas
    assert "Math.min(previewScale || 0.25, LIVE_PREVIEW_MAX_SCALE)" in canvas
    assert "doPreviewRender(currentHash, LIVE_PREVIEW_MAX_SCALE)" in canvas
    assert "Rendering HD preview..." in canvas


def test_zone_spec_overlay_repair_keeps_picker_and_sliders_readable():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI FIX 2026-05-09: Spec Pattern Picker Catalog Contract" in css
    assert "SPB UI FIX 2026-05-09: Zone Spec Overlay Repair Pass" in css
    assert "SPB UI FIX 2026-05-09: Overlay Spec Pattern Controls" in css
    assert ".zone-editor-float .spec-pattern-main-controls" in css
    assert "grid-template-columns: 66px minmax(118px, 1fr) 44px !important" in css
    assert ".zone-editor-float .overlay-spec-patterns div[style*=\"gap:6px 10px\"]" in css
    assert "grid-template-columns: 68px minmax(118px, 1fr) 44px !important" in css
    assert ".zone-editor-float .overlay-spec-pattern-layer-card" in css
    assert ".zone-editor-float .overlay-spec-pattern-header" in css
    assert "grid-template-columns: 22px 30px minmax(72px, 118px) minmax(0, 1fr) 24px !important" in css
    assert ".zone-editor-float .overlay-spec-pattern-name" in css
    assert ".zone-editor-float .overlay-spec-pattern-desc" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-opacity-control" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-range-control" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-scale-control" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-blend-control" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-channel-control" in css
    assert ".zone-editor-float .spec-pattern-transform-controls" in css
    assert "grid-template-columns: 44px 24px minmax(120px, 1fr) 24px 44px !important" in css
    assert ".zone-editor-float .spec-pattern-grid.spec-picker-inline-open" in css
    assert "repeat(auto-fill, minmax(148px, 1fr)) !important" in css
    assert ".zone-editor-float .zone-target-mode .btn" in css
    assert "manualLabel: 'Edit Template'" in state_zones
    assert "function _isZoneSpecLayerPicker(gridId)" in state_zones
    assert "overlaySpecPatternGrid|thirdOverlaySpecPatternGrid|fourthOverlaySpecPatternGrid|fifthOverlaySpecPatternGrid" in state_zones
    assert "isZoneLayerPicker || !PICKER_INTERNAL_REVIEW_UI_ENABLED ? '' : '<button type=\"button\" class=\"spec-review-chip\"" in state_zones
    assert "class=\"overlay-spec-pattern-layer-card\"" in state_zones
    assert "class=\"overlay-spec-pattern-header\"" in state_zones
    assert "class=\"overlay-spec-pattern-thumb\"" in state_zones
    assert "class=\"overlay-spec-pattern-name\"" in state_zones
    assert "class=\"overlay-spec-pattern-desc\"" in state_zones
    assert "class=\"btn btn-sm overlay-spec-pattern-remove\"" in state_zones
    assert "class=\"overlay-spec-pattern-controls\"" in state_zones
    assert "overlay-spec-pattern-opacity-control" in state_zones
    assert "overlay-spec-pattern-range-control" in state_zones
    assert "overlay-spec-pattern-scale-control" in state_zones
    assert "overlay-spec-pattern-blend-control" in state_zones
    assert "overlay-spec-pattern-channel-control" in state_zones
    assert "src=\"/api/spec-pattern-visual-preview/${sp.pattern}\"" in state_zones
    assert "class=\"spec-pattern-main-controls\"" in state_zones
    assert "class=\"spec-pattern-transform-controls\"" in state_zones


def test_fine_tuning_drawer_retargets_cloned_picker_ids_and_fits_overlay_controls():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI FIX 2026-05-09: Fine Tuning Drawer + Overlay Control Fit" in css
    assert ".fine-tuning-panel" in css
    assert "width: min(520px, calc(100vw - 420px)) !important" in css
    assert "#fineTuningBody .stack-control-group:has(input[type=\"range\"])" in css
    assert "grid-template-columns: 72px 24px minmax(104px, 1fr) 24px 44px !important" in css
    assert "#fineTuningBody .overlay-spec-pattern-controls > .overlay-spec-pattern-opacity-control" in css
    assert "grid-template-columns: 72px minmax(140px, 1fr) 44px !important" in css
    assert "#fineTuningBody .spec-pattern-grid.spec-picker-inline-open" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)) !important" in css
    assert "#fineTuningBody .spec-picker-toolbar.spec-picker-inline-open .spec-picker-search" in css
    assert "background: rgba(3, 6, 14, 0.78) !important" in css
    assert "#fineTuningBody .spec-pattern-grid.spec-picker-inline-open .spec-pattern-thumb-card" in css
    # Fine-tuning clone-id retargeting moved to js/zones/fine-tuning-controls.js
    # (var declarations in the extracted module).
    assert "function _retargetFineTuningCloneIds(root)" in state_zones
    assert "var newId = oldId + '_ft';" in state_zones
    assert "var attrs = ['for', 'aria-controls', 'aria-labelledby', 'name', 'onclick', 'oninput', 'onchange', 'onpointerdown', 'onmousedown'];" in state_zones
    assert "_retargetFineTuningCloneIds(clone);" in state_zones


def test_inline_spec_picker_parity_keeps_overlay_pickers_inside_zone_panel():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI FIX 2026-05-09: Inline Spec Picker Parity + Zone Rail Trim" in css
    assert "function _isZoneSpecLayerPicker(gridId)" in state_zones
    assert "var isLayerChanger = _isZoneSpecLayerPicker(gridId);" in state_zones
    assert "var laneFinal = _isZoneSpecLayerPicker(picker.id) ? null : _ensureSpecCurationLanes(picker.id, picker);" in state_zones
    assert "overlaySpecPatternGrid|thirdOverlaySpecPatternGrid|fourthOverlaySpecPatternGrid|fifthOverlaySpecPatternGrid" in state_zones
    assert ".zone-editor-float .spec-picker-toolbar.spec-picker-inline-open" in css
    assert ".zone-editor-float .spec-pattern-grid.spec-picker-inline-open" in css
    assert "width: 100% !important" in css
    assert "min-width: 0 !important" in css
    assert "grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)) !important" in css
    assert "max-height: min(360px, 48vh) !important" in css
    assert ".zone-editor-float .spec-curation-lanes.spec-picker-inline-open" in css
    assert ".zone-editor-float .spec-review-panel.spec-picker-inline-open" in css
    assert "#zoneList .zone-card-header .zone-number" in css
    assert "grid-template-columns: 10px 17px 8px minmax(0, 1fr) !important" in css


def test_base_overlay_spec_picker_reuses_catalog_contract_and_stays_compact():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI FIX 2026-05-10: Base Overlay Spec Picker Parity" in css
    assert "function _getOverlaySpecPatternGridTarget(gridId)" in state_zones
    assert "overlaySpecPatternGrid: addOverlaySpecPatternLayer" in state_zones
    assert "thirdOverlaySpecPatternGrid: addThirdOverlaySpecPatternLayer" in state_zones
    assert "fourthOverlaySpecPatternGrid: addFourthOverlaySpecPatternLayer" in state_zones
    assert "fifthOverlaySpecPatternGrid: addFifthOverlaySpecPatternLayer" in state_zones
    assert "grid.innerHTML = _buildSpecPatternPickerCards('');" in state_zones
    assert "grid.dataset.overlayCatalogBuilt = '1';" in state_zones
    assert "activeOverlayTarget.addFn(activeOverlayTarget.zoneIdx, card.dataset.spid);" in state_zones
    assert ".zone-editor-float .overlay-spec-pattern-layer-card" in css
    assert ".zone-editor-float .overlay-spec-pattern-desc" in css
    assert "display: none !important" in css
    assert "grid-template-columns: 56px minmax(92px, 1fr) 38px !important" in css
    assert ".zone-editor-float .overlay-spec-patterns .spec-pattern-grid.spec-picker-inline-open" in css
    assert "max-height: min(340px, 46vh) !important" in css


def test_picker_cards_have_keyboard_and_premium_scan_polish():
    css = _read_css()
    state_zones = _read_state_zones()

    assert "SPB UI MODERNIZATION 2026-05-09: Picker Card Polish + Keyboard Scan" in css
    assert 'class="swatch-item swatch-catalog-card${isSelected ? \' selected\' : \'\'}" role="button" tabindex="0"' in state_zones
    assert "onkeydown=\"if(event.key==='Enter'||event.key===' '){event.preventDefault();selectSwatchItem('${safeSelect}');}\"" in state_zones
    assert "spec-pattern-thumb-card spec-pattern-catalog-card' + isActive + '\" role=\"button\" tabindex=\"0\"" in state_zones
    assert "aria-label=\"Choose spec overlay pattern " in state_zones
    assert "grid.addEventListener('keydown', function(e)" in state_zones
    assert "picker.addEventListener('keydown', function(e)" in state_zones
    assert "card.click();" in state_zones
    assert ".swatch-popup .swatch-catalog-card::before" in css
    assert "content: attr(data-finish-type) !important" in css
    assert ".spec-pattern-thumb-card.spec-pattern-catalog-card::before" in css
    assert "content: attr(data-category) !important" in css
    assert ".swatch-popup .swatch-catalog-card:focus-visible" in css
    assert ".spec-pattern-thumb-card.spec-pattern-catalog-card:focus-visible" in css
    assert ".swatch-popup .swatch-rank-row" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr)) !important" in css
    assert ".zone-editor-float .section-collapsible > .section-header" in css


def test_shokker_signature_visual_polish_adds_brand_depth_without_layout_rewrite():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-09: Shokker Signature Visual Polish" in css
    assert "--shokk-pulse: #ff7a18" in css
    assert ".header::after" in css
    assert ".header-brand::before" in css
    assert 'content: ":)" !important' in css
    assert ".header-brand::after" in css
    assert "clip-path: polygon(0 57%" in css
    assert "#zoneList::before" in css
    assert 'content: "SHOKK ZONES" !important' in css
    assert "#zoneList .zone-card.selected::after" in css
    assert ".zone-editor-float::before" in css
    assert ".zone-editor-float .zone-detail-title::after" in css
    assert 'content: "  / SHOKK" !important' in css
    assert ".zone-editor-float .section-collapsible > .section-header::before" in css
    assert ".preview-dual-label" in css
    assert "#renderFloat .primary-render-action::before" in css
    assert "#globalStatusBar::before" in css
    assert 'content: ":) SHOKKER SIGNATURE" !important' in css


def test_shokker_signature_boost_makes_branding_visibly_obvious():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-09: Shokker Signature Boost Pass" in css
    assert ".header-brand::before" in css
    assert "width: 31px !important" in css
    assert "border-width: 2px !important" in css
    assert "#centerPanel::before" in css
    assert 'content: "SHOKKER / PAINT BOOTH" !important' in css
    assert "font-size: clamp(48px, 7vw, 118px) !important" in css
    assert "#zoneList .zone-card.selected" in css
    assert "border-width: 2px !important" in css
    assert ".zone-editor-float::before" in css
    assert "height: 6px !important" in css
    assert ".zone-editor-float .section-collapsible > .section-header::after" in css
    assert ".preview-inner::after" in css
    assert "#rightPanel .layer-row:hover" in css


def test_picker_and_dense_control_premium_polish_is_visible_and_fit_safe():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-09: Picker + Dense Control Premium Polish" in css
    assert ".swatch-popup.active::before" in css
    assert ".spec-picker-toolbar.spec-picker-popout-open::before" in css
    assert ".spec-pattern-grid.spec-picker-popout-open::before" in css
    assert ".swatch-popup .swatch-catalog-card::after" in css
    assert ".spec-pattern-thumb-card.sp-thumb-active::after" in css
    assert 'content: "\\2713" !important' in css
    assert ".swatch-filter-chip.active" in css
    assert ".spec-strategy-chip.active" in css
    assert ".zone-editor-float .overlay-spec-patterns div[style*=\"gap:6px 10px\"]" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-opacity-control" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls > .overlay-spec-pattern-range-control" in css
    assert "grid-template-columns: 76px minmax(150px, 1fr) 48px !important" in css
    assert "flex: 0 0 100% !important" in css
    assert ".zone-editor-float .zone-base-rotate-row > div:first-child > .stack-control-group" in css
    assert ".zone-editor-float .base-position-controls > .stack-control-group" in css


def test_workbench_atmosphere_preview_stage_and_tool_rail_are_visibly_modernized():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-09: Workbench Atmosphere + Preview Stage" in css
    assert "body::before" in css
    assert ".main-container" in css
    assert ".center-panel," in css
    assert "#centerPanel" in css
    assert ".canvas-viewport::before" in css
    assert ".split-view-container" in css
    assert ".split-pane-label::before" in css
    assert ".preview-inner>#previewPaintPane img" in css
    assert ".preview-inner>#previewSpecPane img" in css
    assert ".spec-channel-bar," in css
    assert ".zoom-controls .zoom-level" in css
    assert ".vertical-toolbar" in css
    assert ".vtool-group" in css
    assert ".vtool-btn.active" in css
    assert "#renderFloat .primary-render-action" in css
    assert "#globalStatusBar.global-status-bar" in css
    assert "clip-path: polygon(0 55%, 18% 55%, 25% 8%, 34% 90%, 44% 55%, 100% 55%) !important" in css


def test_explicit_workbench_identity_strip_is_real_markup_not_only_background_polish():
    css = _read_css()
    html = _read(REPO / "paint-booth-v2.html")

    assert "SPB UI MODERNIZATION 2026-05-09: Explicit Workbench Identity Strip" in css
    assert "class=\"shokker-workbench-strip\"" in html
    assert "class=\"shokker-workbench-face\"" in html
    assert "class=\"shokker-workbench-pulse\"" in html
    assert "SHOKKER WORKBENCH" in html
    assert "Zone-first workflow" in html
    assert "Live paint + spec preview" in html
    assert "class=\"stage-kicker\">Template</span>" in html
    assert "class=\"stage-kicker\">Rendered</span>" in html
    assert "class=\"status-brand-chip\"" in html
    assert ".shokker-workbench-strip" in css
    assert ".shokker-workbench-brand" in css
    assert ".shokker-workbench-pulse" in css
    assert ".shokker-workbench-chip" in css
    assert ".stage-kicker" in css
    assert ".status-brand-chip::before" in css
    assert 'content: ":)" !important' in css


def test_workbench_command_bar_has_real_structure_and_modern_tool_context():
    css = _read_css()
    html = _read(REPO / "paint-booth-v2.html")

    assert "SPB UI MODERNIZATION 2026-05-09: Command Bar Visual Structure" in css
    assert "class=\"workbench-command-bar\"" in html
    assert "class=\"workbench-command-label\">Paint Source</span>" in html
    assert "class=\"paint-source-cluster paint-source-empty\"" in html
    assert "class=\"paint-source-cluster paint-source-loaded\"" in html
    assert "id=\"toolOptionsBar\" class=\"tool-options-bar\"" in html
    assert ".workbench-command-bar" in css
    assert ".workbench-command-label" in css
    assert ".paint-source-cluster .btn" in css
    assert "#paintPreviewStatus," in css
    assert "#toolOptionsBar.tool-options-bar" in css
    assert "#activeToolLabel::before" in css
    assert "#contextScopeChip" in css
    assert "#toolbarEditModeGroup .btn" in css
    assert "grid-template-columns: auto auto auto minmax(0, 1fr) !important" in css


def test_source_live_preview_workspace_is_protected_from_ui_chrome_growth():
    css = _read_css()

    assert "SPB UI GUARD 2026-05-10: Source Preview Workspace Protection" in css
    assert ".center-panel," in css
    assert "#centerPanel" in css
    assert "display: flex !important" in css
    assert "flex-direction: column !important" in css
    assert ".shokker-workbench-strip" in css
    assert "max-height: 44px !important" in css
    assert ".workbench-command-bar" in css
    assert "max-height: min(112px, 16vh) !important" in css
    assert "overflow-y: auto !important" in css
    assert "#toolOptionsBar.tool-options-bar" in css
    assert "max-height: 66px !important" in css
    assert ".canvas-viewport" in css
    assert "flex: 1 1 auto !important" in css
    assert "min-height: min(520px, calc(100vh - 206px)) !important" in css
    assert ".split-view-container" in css
    assert "min-height: min(720px, calc(100vh - 230px)) !important" in css
    assert "max-width: 100% !important" in css
    assert ".split-pane > .preview-inner" in css
    assert "max-width: calc(100% - 28px) !important" in css
    assert "#renderFloat," in css
    assert ".zoom-controls" in css
    assert "z-index: 24 !important" in css
    assert ".canvas-viewport #renderFloat" in css
    assert "inset-block-end: 14px !important" in css
    assert ".canvas-viewport .zoom-controls" in css
    assert "max-width: min(460px, calc(100% - 32px)) !important" in css
    assert ".swatch-popup," in css
    assert "z-index: 2600 !important" in css
    assert "@media (max-height: 820px)" in css


def test_guarded_visual_polish_makes_shell_more_current_without_expanding_workspace():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Guarded Visual Polish" in css
    assert ".header::after" in css
    assert "clip-path: polygon(0 62%, 11% 62%" in css
    assert ".header-command-btn.primary" in css
    assert "#zoneList .zone-card {" in css
    assert "min-height: 38px !important" in css
    assert "#zoneList .zone-card.selected {" in css
    assert "border-width: 1px !important" in css
    assert "grid-template-columns: 16px 8px minmax(0, 1fr) auto !important" in css
    assert "#zoneList .zone-card-header .zone-number" in css
    assert "width: 18px !important" in css
    assert ".zone-editor-float .zone-detail-body > .color-selector" in css
    assert ".fine-tuning-panel .fine-tuning-header" in css
    assert ".split-pane::after" in css


def test_support_chrome_polish_updates_right_rail_status_and_results_without_canvas_growth():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Support Chrome Polish" in css
    assert "#rightPanelTabs" in css
    assert "#rightPanel .rp-tab.active" in css
    assert "#rightPanel .right-panel-primary-action::before" in css
    assert 'content: "PSD" !important' in css
    assert "#rightPanel .right-panel-secondary-action::before" in css
    assert ".spec-channel-bar" in css
    assert ".spec-channel-btn.active" in css
    assert "#renderResultsPanel::before" in css
    assert "#renderHistoryStrip" in css
    assert "max-height: 74px !important" in css
    assert "#globalStatusBar .status-chip-zone" in css


def test_split_preview_rescue_keeps_chrome_compact_and_ekg_browser_safe():
    css = _read_css()

    assert "SPB UI FIX 2026-05-10: Split Preview Space Rescue" in css
    assert ".vertical-toolbar" in css
    assert "width: 96px !important" in css
    assert ".zone-editor-float" in css
    assert "left: 316px !important" in css
    assert "max-width: 350px !important" in css
    assert ".shokker-workbench-strip" in css
    assert "max-height: 30px !important" in css
    assert ".workbench-command-bar" in css
    assert "max-height: min(74px, 10vh) !important" in css
    assert ".shokker-workbench-pulse," in css
    assert "clip-path: none !important" in css
    assert "data:image/svg+xml" in css
    assert ".canvas-viewport" in css
    assert "min-height: min(600px, calc(100vh - 154px)) !important" in css


def test_safe_premium_surface_pass_polishes_without_preview_growth():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Safe Premium Surface Pass" in css
    assert "--spb-surface-glass" in css
    assert ".shokker-workbench-pulse," in css
    assert "background-image: none !important" in css
    assert "center / 100% 2px no-repeat !important" in css
    assert ".center-panel," in css
    assert "#centerPanel" in css
    assert ".split-pane > .preview-inner" in css
    assert "inset 0 0 44px rgba(34, 211, 238, 0.035) !important" in css
    assert ".preview-inner > #previewSpecPane" in css
    assert "border-color: rgba(255, 122, 24, 0.78) !important" in css
    assert ".zone-editor-float .section-collapsible > .section-header" in css
    assert "#zoneList .zone-card.selected" in css
    assert "inset 4px 0 0 var(--shokk-cyan, #22d3ee) !important" in css
    assert ".vtool-group" in css
    assert "#renderFloat.render-float" in css
    assert "backdrop-filter: blur(12px) !important" in css


def test_browser_safe_heartbeat_motion_is_actually_animated():
    css = _read_css()

    assert "SPB UI FIX 2026-05-10: Restore Browser-Safe Heartbeat Motion" in css
    assert "animation: shokkerHeaderHeartbeatSweep 4.8s linear infinite !important" in css
    assert "animation: shokkerWorkbenchPulseTravel 1.75s linear infinite, shokkerPulseGlow 1.75s ease-in-out infinite !important" in css
    assert "animation: shokkerBrandPulseBeat 1.75s ease-in-out infinite !important" in css
    assert "@keyframes shokkerHeaderHeartbeatSweep" in css
    assert "@keyframes shokkerWorkbenchPulseTravel" in css
    assert "@keyframes shokkerPulseGlow" in css
    assert "@keyframes shokkerBrandPulseBeat" in css
    assert "will-change: background-position !important" in css
    assert "will-change: transform, opacity !important" in css


def test_shokker_energy_shock_pass_is_intense_and_preview_safe():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Shokker Energy Shock Pass" in css
    assert "--shokker-electric: #00e5ff" in css
    assert "--shokker-pink-hot: #ff2d6f" in css
    assert "animation: shokkerAmbientVoltage 8s linear infinite !important" in css
    assert "animation: shokkerFaceIgnite 2.2s ease-in-out infinite !important" in css
    assert "animation: shokkerTitleCharge 5.2s ease-in-out infinite !important" in css
    assert "animation: shokkerToolPop 2.6s ease-in-out infinite !important" in css
    assert "animation: shokkerSpecTileCharge 3.8s ease-in-out infinite !important" in css
    assert "animation: shokkerRenderHeat 2.1s ease-in-out infinite !important" in css
    assert ".split-pane > .preview-inner::before" in css
    assert "pointer-events: none !important" in css
    assert ".preview-inner > #previewPaintPane," in css
    assert ".preview-inner > #previewBeforePane," in css
    assert ".preview-inner > #previewSpecPane" in css
    assert "#renderFloat .primary-render-action" in css
    assert "@keyframes shokkerRenderHeat" in css


def test_shokker_nitro_visible_pass_hits_actual_surfaces():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Shokker Nitro Visible Pass" in css
    assert "animation: shokkerNitroSweep 5.5s linear infinite !important" in css
    assert "animation: shokkerNitroScan 3.2s linear infinite !important" in css
    assert ".split-view-container::before," in css
    assert ".split-view-container::after" in css
    assert "border: 2px solid rgba(0, 229, 255, 0.40) !important" in css
    assert "min-height: 48px !important" in css
    assert "font-size: 13px !important" in css
    assert "#zoneList .zone-card.selected" in css
    assert "linear-gradient(135deg, #ff7a18, #ff2d6f) !important" in css
    assert ".zone-editor-float .section-collapsible > .section-header" in css
    assert "min-height: 36px !important" in css
    assert "@keyframes shokkerNitroSweep" in css
    assert "@keyframes shokkerNitroScan" in css


def test_shokker_stage_lights_pass_makes_brand_energy_browser_safe():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Shokker Stage Lights Pass" in css
    assert ".header-brand::after" in css
    assert ".shokker-workbench-pulse" in css
    assert "data:image/svg+xml" in css
    assert "animation: shokkerStageEkgRun 2.35s linear infinite !important" in css
    assert "animation: shokkerStageEkgRun 2.1s linear infinite !important" in css
    assert ".left-panel::before," in css
    assert "#rightPanel::before" in css
    assert "animation: shokkerStageRailPulse 2.8s ease-in-out infinite !important" in css
    assert ".canvas-viewport::before" in css
    assert "pointer-events: none !important" in css
    assert "@keyframes shokkerStageEkgRun" in css
    assert "@keyframes shokkerStageFaceKick" in css
    assert "@keyframes shokkerStageRailPulse" in css


def test_pit_wall_visual_upgrade_polishes_empty_state_finish_and_layer_surfaces():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Pit Wall Visual Upgrade Pass" in css
    assert ".onboarding-empty::before" in css
    assert ".onboarding-empty::after" in css
    assert "max-width: min(780px, calc(100% - 72px)) !important" in css
    assert ".finish-category-rail" in css
    assert ".finish-item.finish-catalog-card" in css
    assert "#rpFinishesContent .finish-item::before" in css
    assert ".finish-item-assign" in css
    assert "#layerPanelContent .layer-row" in css
    assert "#rpLayersContent .layer-row:hover" in css
    assert ".split-pane-label" in css
    assert "min-height: 34px !important" in css


def test_control_deck_readability_pass_modernizes_dense_zone_controls():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Control Deck Readability Pass" in css
    assert ".zone-editor-float .zone-detail-body" in css
    assert ".zone-editor-float .stack-control-group" in css
    assert ".zone-editor-float .zone-base-rotate-row" in css
    assert ".zone-editor-float .overlay-spec-pattern-controls" in css
    assert ".zone-editor-float input[type=\"range\"]::-webkit-slider-runnable-track" in css
    assert ".zone-editor-float input[type=\"range\"]::-webkit-slider-thumb" in css
    assert ".zone-editor-float .stack-val" in css
    assert ".zone-editor-float select:focus" in css
    assert ".fine-tuning-panel .fine-tuning-header" in css
    assert ".swatch-popup .swatch-catalog-card:hover" in css
    assert "min-height: 32px !important" in css


def test_gallery_runway_picker_pass_polishes_picker_and_render_review_surfaces():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Gallery Runway Picker Pass" in css
    assert ".swatch-popup.active," in css
    assert ".spec-pattern-grid.spec-picker-popout-open" in css
    assert ".swatch-popup.active::after" in css
    assert ".spec-pattern-grid.spec-picker-popout-open::after" in css
    assert ".swatch-popup-search input" in css
    assert ".swatch-popup-grid" in css
    assert ".spec-pattern-thumb-card.spec-pattern-catalog-card" in css
    assert ".zone-editor-float .spec-pattern-grid.spec-picker-inline-open .spec-pattern-thumb-card.sp-thumb-active" in css
    assert ".swatch-rank-chip" in css
    assert "#renderResultsPanel" in css
    assert "#renderHistoryStrip img" in css
    assert "min-height: 46px !important" in css


def test_command_chrome_ignition_pass_modernizes_always_visible_controls():
    css = _read_css()

    assert "SPB UI MODERNIZATION 2026-05-10: Command Chrome Ignition Pass" in css
    assert ".header-field::before" in css
    assert ".header-field:focus-within" in css
    assert ".header-command-btn.primary" in css
    assert ".ui-mode-option.active" in css
    assert ".vertical-toolbar" in css
    assert ".vtool-group::before" in css
    assert ".vtool-btn.active" in css
    assert "#globalStatusBar.global-status-bar::after" in css
    assert "#globalStatusBar .status-brand-chip" in css
    assert ".btn-zone-action" in css
    assert "#toolbarEditModeGroup .btn:hover" in css


def test_zone_hover_actions_and_render_dock_are_layout_guarded():
    css = _read_css()

    assert "SPB UI FIX 2026-05-11: Zone Hover + Render Dock Anchoring" in css
    assert "#zoneList .zone-card.selected .zone-card-header .zone-card-actions" in css
    assert "#zoneList .zone-card:hover .zone-card-header .zone-card-actions" in css
    assert "grid-row: 2 !important" in css
    assert "flex-wrap: wrap !important" in css
    assert "#zoneList .zone-card-header .zone-summary" in css
    assert "#renderFloat.render-float," in css
    assert ".canvas-viewport #renderFloat.render-float" in css
    assert "position: fixed !important" in css
    assert "bottom: 38px !important" in css
    assert "width: clamp(340px, 34vw, 520px) !important" in css
    assert "z-index: 2400 !important" in css


def test_ekg_text_clearance_and_section_color_rails():
    css = _read_css()

    assert "SPB UI FIX 2026-05-11: EKG Text Clearance + Section Color Rails" in css
    assert ".shokker-workbench-title" in css
    assert "order: 2 !important" in css
    assert ".shokker-workbench-pulse" in css
    assert "order: 3 !important" in css
    assert "flex: 0 0 128px !important" in css
    assert "--section-rail: #00e5ff" in css
    assert "--section-rail: #ff7a18" in css
    assert "--section-rail: #ff2d6f" in css
    assert ".zone-editor-float [id^=\"sectionBase\"]" in css
    assert ".zone-editor-float [id^=\"sectionSpecPatterns\"]" in css
    assert ".zone-editor-float [id^=\"sectionPattern\"]" in css
    assert ".zone-editor-float [id^=\"sectionOverlays\"]" in css
    assert ".zone-editor-float .section-collapsible > .section-header::before" in css
    assert ".zone-editor-float .section-collapsible > .section-header::after" in css
    assert "top: 4px !important" in css
    assert "bottom: 4px !important" in css
    assert "@keyframes shokkerSectionEkgRail" in css


def test_spec_overlay_picker_popout_is_constrained_like_base_picker():
    css = _read_css()

    # Moved to css/ui-fixes-20260511.css. The popout now anchors with
    # left/right clamps + a min-width floor (instead of a fixed width), the wide
    # toolbar grid widened its two flexible columns, and the narrow (<=1320px)
    # breakpoint dropped to a 3-column grid.
    assert "SPB UI FIX 2026-05-11: Spec Overlay Picker Parity Panel" in css
    assert ".spec-picker-toolbar.spec-picker-popout-open," in css
    assert ".spec-pattern-grid.spec-picker-popout-open {" in css
    assert "min-width: min(900px, calc(100vw - 36px)) !important" in css
    assert "grid-template-columns: minmax(170px, auto) minmax(280px, 1fr) auto auto auto auto !important" in css
    assert "grid-template-columns: minmax(156px, auto) minmax(170px, 1fr) auto auto !important" in css
    assert ".spec-curation-lanes.spec-picker-popout-open" in css
    assert ".spec-category-strategy-panel.spec-picker-popout-open" in css
    assert "display: none !important" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr)) !important" in css
    assert ".spec-pattern-grid.spec-picker-popout-open .spec-pattern-thumb-card" in css
    assert "height: 82px !important" in css
    assert "-webkit-line-clamp: 2 !important" in css
    assert ".spec-pattern-grid.spec-picker-popout-open::before" in css
    assert "@media (max-width: 1320px)" in css


def test_settings_dropdown_has_clickable_top_layer_contract():
    css = _read_css()
    data_js = _read(REPO / "paint-booth-1-data.js")

    assert "SPB UI FIX 2026-05-12: Header Settings Dropdown Stack Guard" in css
    assert ".header {" in css
    assert "z-index: 5200 !important" in css
    assert "overflow: visible !important" in css
    assert ".settings-dropdown {" in css
    assert "position: fixed !important" in css
    assert "z-index: 5400 !important" in css
    assert ".settings-dropdown.open" in css
    assert "display: block !important" in css
    assert "#settingsGearBtn[aria-expanded=\"true\"]" in css
    assert ".web-command-menu" in css
    assert "z-index: 5350 !important" in css
    assert "function toggleSettingsDropdown()" in data_js
    assert "if (!dd) return;" in data_js
    assert "webMenu.classList.remove('open')" in data_js
    assert "dd.classList.toggle('open', isOpen)" in data_js
    assert "btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false')" in data_js
    assert "window.toggleSettingsDropdown = toggleSettingsDropdown;" in data_js


def test_empty_base_overlay_layers_do_not_look_active():
    css = _read_css()
    state_zones = _read_state_zones()

    # Base-overlay enable/empty logic was extracted to
    # js/zones/zone-base-overlay-state-controls.js, where the helper was renamed
    # _baseOverlayLayerHasSettings -> layerHasSettings, declarations switched
    # const -> var, and the markup is built via string concatenation instead of a
    # template literal. Same behaviour: an overlay with no base shows "Empty".
    assert "if (!layerHasSettings(zone, layer)) return 'Empty';" in state_zones
    assert "var hasSettings = layerHasSettings(zone, layer);" in state_zones
    assert "var status = hasSettings ? (checked ? 'On' : 'Off') : 'Empty';" in state_zones
    assert "base-overlay-empty" in state_zones
    assert "base to make this affect preview/render." in state_zones
    assert "aria-label=\"' + label + ' base overlay preview render toggle\"" in state_zones
    assert ".base-overlay-enable-toggle.base-overlay-empty" in css
    assert "transform: translateX(6px)" in css
    assert "min-width: 34px" in css
