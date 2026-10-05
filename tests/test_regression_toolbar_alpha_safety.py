import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CHANGELOG = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
HTML = (REPO / "paint-booth-v2.html").read_text(encoding="utf-8")
WIKI_HTML = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")
DATA_JS = (REPO / "paint-booth-1-data.js").read_text(encoding="utf-8")
CANVAS_JS = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
CSS = (REPO / "paint-booth-v2.css").read_text(encoding="utf-8")
LAYER_FLOW_JS = (REPO / "paint-booth-layer-flow.js").read_text(encoding="utf-8")
STATE_JS = (REPO / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
API_JS = (REPO / "paint-booth-5-api-render.js").read_text(encoding="utf-8")
UI_BOOT_JS = (REPO / "paint-booth-6-ui-boot.js").read_text(encoding="utf-8")
SHOKK_JS = (REPO / "paint-booth-7-shokk.js").read_text(encoding="utf-8")
FINISH_DATA_JS = (REPO / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
SMART_SEPARATE_JS = (REPO / "js" / "features" / "smart-separate.js").read_text(encoding="utf-8")
SERVER_PY = (REPO / "server.py").read_text(encoding="utf-8")
SERVER_PHOTOSHOP_EXPORT_PY = (
    REPO / "server_routes" / "photoshop_export_routes.py"
).read_text(encoding="utf-8")
SERVER_SHOKK_ROUTES_PY = (
    REPO / "server_routes" / "shokk_routes.py"
).read_text(encoding="utf-8")
SERVER_V5_PY = (REPO / "server_v5.py").read_text(encoding="utf-8")
ENGINE_PY = (REPO / "shokker_engine_v2.py").read_text(encoding="utf-8")
ENGINE_COMPOSE_PY = (REPO / "engine" / "compose.py").read_text(encoding="utf-8")


def _slice_between(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


def _finish_group_ids(group_name: str) -> list[str]:
    marker = f'"{group_name}": ['
    start = FINISH_DATA_JS.index(marker)
    end = FINISH_DATA_JS.index("]", start)
    return re.findall(r'"([^"]+)"', FINISH_DATA_JS[start + len(marker):end])


def test_zoom_controls_stack_above_render_float():
    zoom_css = _slice_between(CSS, ".zoom-controls {", ".eyedropper-dock-top")
    render_css = _slice_between(CSS, "#renderFloat {", "#renderFloat > *")

    assert "z-index: 20;" in zoom_css
    assert "z-index: 12 !important;" in render_css
    assert "pointer-events: none;" in render_css


def test_base_color_fit_to_selection_reaches_render_payload():
    api_mode = _slice_between(
        API_JS,
        "function _applyBaseColorMode(zoneObj, z) {",
        "if (typeof window !== 'undefined') window._applyBaseColorMode = _applyBaseColorMode;",
    )
    assert "baseColorFitZone" in STATE_JS
    assert "function setZoneBaseColorFitZone" in STATE_JS
    assert "baseColorFitZone: z.baseColorFitZone" in CANVAS_JS
    assert "z.baseColorFitZone" in CANVAS_JS and "_zoneShouldFitIntoApplyArea(z)" in CANVAS_JS
    assert "z.baseColorFitZone || _zoneShouldFitIntoApplyArea(z)" in api_mode
    assert "base_color_fit_zone" in ENGINE_PY
    assert "def _fit_paint_source_to_mask_bbox(" in ENGINE_COMPOSE_PY
    assert "_base_fit_mask = (" in ENGINE_COMPOSE_PY
    assert "if (base_color_fit_zone or _base_placement_for_material)" in ENGINE_COMPOSE_PY
    assert "paint = _fit_paint_source_to_mask_bbox(paint, _paint_before_base_fn, hard_mask)" in ENGINE_COMPOSE_PY
    assert "_base_fit_mask_stk = (" in ENGINE_COMPOSE_PY
    assert "if (base_color_fit_zone or _base_placement_for_material_stk)" in ENGINE_COMPOSE_PY
    assert "paint = _fit_paint_source_to_mask_bbox(paint, _paint_before_base_fn_stk, hard_mask)" in ENGINE_COMPOSE_PY
    assert "Fit to Selection for Zones" in WIKI_HTML
    assert "A full base finish, base color source, custom gradient, pattern/spec source, and base spec response are compressed" in WIKI_HTML


def test_base_custom_gradient_stops_are_normalized_for_engine_payload():
    state_gradient = _slice_between(
        STATE_JS,
        "function _normalizeBaseGradientStopColorForPayload(color) {",
        "function _buildGradientEditorHTML(zoneIdx, zone) {",
    )
    api_branch = _slice_between(
        API_JS,
        "function _applyBaseColorBranch(zoneObj, z, baseMode) {",
        "if (typeof window !== 'undefined') window._applyBaseColorBranch = _applyBaseColorBranch;",
    )
    preview_builder = _slice_between(
        CANVAS_JS,
        "if (z.base || z.finish) {",
        "if (z.base || (z.finish && z.pattern && z.pattern !== 'none')) {",
    )

    assert "function normalizeBaseGradientStopsForPayload(stops) {" in STATE_JS
    assert "parseInt(hex.slice(1, 3), 16) / 255" in state_gradient
    assert "const pos = rawPos > 1 ? rawPos / 100 : rawPos;" in state_gradient
    assert "window.normalizeBaseGradientStopsForPayload = normalizeBaseGradientStopsForPayload;" in STATE_JS

    assert "const normalizedStops = (typeof normalizeBaseGradientStopsForPayload === 'function')" in api_branch
    assert "zoneObj.gradient_stops = normalizedStops;" in api_branch
    assert "zoneObj.gradient_stops = z.gradientStops;" not in api_branch

    assert "const normalizedStops = (typeof normalizeBaseGradientStopsForPayload === 'function')" in preview_builder
    assert "zoneObj.gradient_stops = normalizedStops;" in preview_builder
    assert "zoneObj.gradient_stops = z.gradientStops;" not in preview_builder


def test_preview_zone_hash_tracks_advanced_base_overlay_fields():
    preview_hash = _slice_between(
        CANVAS_JS,
        "body.zone_hashes = zones.filter",
        "// Include imported spec map",
    )

    assert "const overlayHash = {};" in preview_hash
    assert "['second', 'third', 'fourth', 'fifth'].forEach(prefix => {" in preview_hash
    assert "const baseKey = prefix + 'Base';" in preview_hash
    assert "overlayHash[baseKey] = z[baseKey];" in preview_hash
    for suffix in (
        "Strength", "SpecStrength", "ColorSource", "BlendMode",
        "Pattern", "PatternOpacity", "PatternScale", "PatternRotation",
        "PatternStrength", "PatternInvert", "PatternHarden",
        "PatternOffsetX", "PatternOffsetY", "PatternHueShift",
        "PatternSaturation", "PatternBrightness", "PatternFlipH",
        "PatternFlipV", "FitZone",
    ):
        assert f"'{suffix}'" in preview_hash
    assert "baseColorFitZone: z.baseColorFitZone" in preview_hash
    assert "gradientStops: z.gradientStops" in preview_hash
    assert "thirdOverlaySpecPatternStack: z.thirdOverlaySpecPatternStack" in preview_hash
    assert "fifthOverlaySpecPatternStack: z.fifthOverlaySpecPatternStack" in preview_hash
    assert "secondBase: z.secondBase, secondBaseStrength: z.secondBaseStrength" not in preview_hash


def test_engine_preview_cache_mask_fingerprint_is_position_aware():
    cache_block = _slice_between(
        ENGINE_PY,
        "# ---- Zone-level cache (preview_mode only) ----",
        "# Snapshot paint before this zone renders",
    )

    assert "_zm_quantized = np.ascontiguousarray" in cache_block
    assert "_hashlib.blake2b(_zm_quantized.tobytes(), digest_size=16).hexdigest()" in cache_block
    assert "_zm_digest" in cache_block
    assert "{h}x{w}:{_zm_digest}" in cache_block
    assert '_zm_sig = f"{zone_mask.shape}:{zone_mask.sum():.4f}:{zone_mask.max():.4f}:{h}x{w}"' not in cache_block


def test_viva_mexico_specials_stay_grouped_and_discoverable():
    viva_group_ids = _finish_group_ids("VIVA MEXICO")
    viva_monolithic_ids = set(re.findall(r'\{\s*id:\s*"(vm_[^"]+)"', FINISH_DATA_JS))

    assert len(viva_group_ids) == 58
    assert all(finish_id.startswith("vm_") for finish_id in viva_group_ids)
    assert set(viva_group_ids) == viva_monolithic_ids

    assert '"Cultural": ["RISING SUN", "VIVA MEXICO", "UNION JACKED", "FORBIDDEN DRAGON"]' in FINISH_DATA_JS
    assert "_renderGuidedFinishCatalog(activeTab, groupMap, groupNames, activeLibraryTab, activeTab.type)" in STATE_JS
    assert "const count = activeTab.items.filter(function(item) { return ids.has(item.id); }).length;" in STATE_JS
    assert "if (groupedSpecialMonoIds.size && !groupedSpecialMonoIds.has(m.id)) continue;" in UI_BOOT_JS
    assert 'if f.startswith("vm_"):' in SERVER_V5_PY
    assert '"VIVA MEXICO": [fid for fid in MONOLITHIC_REGISTRY.keys() if str(fid).startswith("vm_")]' in SERVER_V5_PY


def test_zone_imported_spec_source_reaches_ui_payload_server_and_engine():
    assert "SPEC SOURCE" in STATE_JS
    assert "function importZoneSpecMapFromFile" in STATE_JS
    assert "zoneSpecMapPath: null" in STATE_JS
    assert "zoneObj.zone_spec_map = z.zoneSpecMapPath.trim();" in API_JS
    assert "_zoneHasImportedSpecSource(z)" in API_JS
    assert "zone_spec_map" in SERVER_PY
    assert "def _blend_zone_spec_source" in ENGINE_PY
    assert "PATH ZSPEC" in ENGINE_PY


def test_canvas_mode_window_mirror_stays_synced_for_toolbar_polish():
    set_mode = _slice_between(
        CANVAS_JS,
        "function setCanvasMode(mode) {",
        "// Update active tool label in tool options bar",
    )
    spatial_mode = _slice_between(
        CANVAS_JS,
        "function toggleSpatialMode(mode) {",
        "function hasSpatialMask(zone) {",
    )
    expose_block = _slice_between(
        CANVAS_JS,
        "window.hideRectPreview = hideRectPreview;",
        "// Expose for Photoshop round-trip: Import from Photoshop loads paint from URL",
    )

    assert "canvasMode = mode;" in set_mode
    assert "window.canvasMode = mode;" in set_mode
    assert "window.canvasMode = canvasMode;" in spatial_mode
    assert "window.setCanvasMode = setCanvasMode;" in expose_block
    assert "window.canvasMode = canvasMode;" in expose_block


def test_import_spec_clear_clears_window_fallback_and_shokk_indicators():
    spec_source_section = _slice_between(
        STATE_JS,
        "function renderZoneSpecSourceSection(i, zone) {",
        "// ===== ZONE DETAIL PANEL",
    )
    shokk_banner_clear = _slice_between(
        STATE_JS,
        "function clearImportedSpec() {",
        "// Scale slider:",
    )
    manual_import = _slice_between(
        STATE_JS,
        "function importSpecMapFromFile() {",
        "function importSpecMapFromDrop(file) {",
    )
    drop_import = _slice_between(
        STATE_JS,
        "function importSpecMapFromDrop(file) {",
        "function clearImportedSpecMap() {",
    )
    clear_handler = _slice_between(
        STATE_JS,
        "function clearImportedSpecMap() {",
        "function _setZoneSpecMap(index, path, meta) {",
    )
    copy_layer_zero = _slice_between(
        STATE_JS,
        "function copyImportedSpecMapToZone(index) {",
        "function clearZoneSpecMap(index) {",
    )
    ps_import = _slice_between(
        API_JS,
        "async function importSpecFromLastExport() {",
        "/**\n * Main render pipeline.",
    )

    assert "function _getActiveImportedSpecMapPath() {" in STATE_JS
    assert "if (!_getActiveImportedSpecMapPath())" in shokk_banner_clear
    assert "const globalAvailable = _getActiveImportedSpecMapPath();" in spec_source_section
    assert "const activeSpecPath = _getActiveImportedSpecMapPath();" in clear_handler
    assert "const activeSpecPath = _getActiveImportedSpecMapPath();" in copy_layer_zero
    assert "_setZoneSpecMap(index, activeSpecPath" in copy_layer_zero
    assert "activeSpecPath.split('/').pop().split('\\\\').pop()" in copy_layer_zero
    assert "window.importedSpecMapPath = data.temp_path;" in manual_import
    assert "window.importedSpecMapPath = data.temp_path;" in drop_import
    assert "window.importedSpecMapPath = data.temp_path;" in ps_import

    assert "window.importedSpecMapPath = null;" in clear_handler
    assert "document.getElementById('specFromShokkBanner')" in clear_handler
    assert "document.getElementById('shokkSpecStateChip')" in clear_handler
    assert "specChip.textContent = 'SPEC: none';" in clear_handler
    assert "renderZones();" in clear_handler

    stale_path = clear_handler.split("if (!activeSpecPath)", 1)[0]
    assert "if (!importedSpecMapPath)" not in stale_path


def test_spec_only_render_guard_uses_imported_spec_window_fallback():
    do_render_start = _slice_between(
        API_JS,
        "async function doRender() {",
        "// Gather extras (wear, export, output folder)",
    )
    active_spec_decl = "const activeSpecPath = (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath)"

    assert active_spec_decl in do_render_start
    assert "((typeof window !== 'undefined' && window.importedSpecMapPath) ? window.importedSpecMapPath : null)" in do_render_start
    assert "if (serverZones.length === 0 && !activeSpecPath)" in do_render_start
    assert "if (serverZones.length === 0 && activeSpecPath)" in do_render_start
    assert do_render_start.index(active_spec_decl) < do_render_start.index("if (serverZones.length === 0 && !activeSpecPath)")
    assert "serverZones.length === 0 && !importedSpecMapPath" not in do_render_start


def test_imported_spec_window_fallback_reaches_banner_config_and_preview():
    render_zones_start = _slice_between(
        STATE_JS,
        "function renderZones() {",
        "try {\n        zones.forEach",
    )
    get_config = _slice_between(
        STATE_JS,
        "function getConfig() {",
        "function loadConfigFromObj",
    )
    preview_request = _slice_between(
        CANVAS_JS,
        "function triggerPreviewRender() {",
        "// Include decal composited paint",
    )

    assert "const activeImportedSpecMapPath = _getActiveImportedSpecMapPath();" in render_zones_start
    assert "if (activeImportedSpecMapPath) {" in render_zones_start
    assert "const fname = activeImportedSpecMapPath.split('/').pop().split('\\\\').pop();" in render_zones_start
    assert "if (importedSpecMapPath) {" not in render_zones_start

    assert "importedSpecMapPath: _getActiveImportedSpecMapPath() || null" in get_config
    assert "importedSpecMapPath: importedSpecMapPath || null" not in get_config

    assert "const activeImportedSpecMapPath = (typeof _getActiveImportedSpecMapPath === 'function')" in preview_request
    assert "body.import_spec_map = activeImportedSpecMapPath;" in preview_request
    assert "body.import_spec_map = importedSpecMapPath;" not in preview_request


def test_symmetry_toolbar_control_removed_and_runtime_forced_off():
    assert 'id="symmetryMode"' not in HTML
    helper = _slice_between(
        CANVAS_JS,
        "function getEffectiveSymmetryMode() {",
        "window.getEffectiveSymmetryMode = getEffectiveSymmetryMode;",
    )
    assert "return 'off';" in helper
    assert "document.getElementById('symmetryMode')?.value" not in CANVAS_JS


def test_eraser_shortcut_truth_is_consistent_across_toolbar_overlay_and_handlers():
    assert 'id="vtModeErase"' in HTML
    assert 'title="Eraser (E) — erase mask strokes"' in HTML
    assert 'title="Edge Detect — find boundaries between colors"' in HTML
    assert 'title="Edge Detect (E)' not in HTML
    assert 'title="Eraser (X)' not in HTML

    assert "else if (key === 'e' && !e.shiftKey) { setCanvasMode('erase'); e.preventDefault(); }" in CANVAS_JS
    assert "else if (key === 'x') { swapForegroundBackground(); e.preventDefault(); }" in CANVAS_JS
    assert "else if (key === 'e' && !e.shiftKey) { setCanvasMode('edge'); e.preventDefault(); }" not in CANVAS_JS

    assert "['W', 'Magic Wand'], ['A', 'Select All Color'], ['E', 'Eraser']" in CANVAS_JS
    assert "['Button', 'Edge Detect']" in CANVAS_JS
    assert "['X', 'Swap FG/BG Colors']" in CANVAS_JS

    assert "if (k === 'e') { if (typeof setCanvasMode === 'function') { setCanvasMode('erase'); e.preventDefault(); } return; }" in UI_BOOT_JS
    assert "if (k === 'x') { if (typeof setCanvasMode === 'function') { setCanvasMode('erase'); e.preventDefault(); } return; }" not in UI_BOOT_JS


def test_slash_shortcut_targets_real_finish_search_when_chat_bar_is_absent():
    assert 'id="finishSearch"' in HTML
    assert 'id="finishSearchInput"' not in HTML

    assert "document.getElementById('chatInput') || document.getElementById('finishSearch')" in UI_BOOT_JS
    assert "document.getElementById('finishSearch') || document.getElementById('chatInput')" not in UI_BOOT_JS
    assert "document.activeElement.id === 'finishSearch'" in UI_BOOT_JS

    assert "document.getElementById('finishSearchInput')" not in UI_BOOT_JS
    assert "document.activeElement.id === 'finishSearchInput'" not in UI_BOOT_JS
    assert "{ keys: '/', desc: 'Focus chat / finish search' }" in UI_BOOT_JS
    assert "Finish search</td><td>Filters candidate finishes by name, ID, group, and searchable text." in WIKI_HTML


def test_move_shortcut_truth_beats_split_view_conflict():
    assert 'id="vtModeLayerMove"' in HTML
    assert 'title="Move (V)' in HTML
    assert 'title="Split View (Shift+V)' in HTML
    assert 'title="Split View (V)' not in HTML
    assert '>V</kbd> Move<' in HTML
    assert '>Shift+V</kbd> Split View<' in HTML

    assert "if ((e.key === 'V' || e.key === 'v') && e.shiftKey && !e.ctrlKey && !e.altKey)" in UI_BOOT_JS
    assert "toggleSplitView();" in UI_BOOT_JS
    assert "if (e.key === 'v' && !e.ctrlKey && !e.altKey)" not in UI_BOOT_JS
    assert "if (k === 'v') { if (typeof setCanvasMode === 'function') { setCanvasMode('layer-move'); e.preventDefault(); } return; }" in UI_BOOT_JS

    assert "['V', 'Move Layer']" in CANVAS_JS
    assert "['Shift+V', 'Toggle Split View']" in CANVAS_JS
    assert "['V', 'Toggle Split View']" not in CANVAS_JS
    assert "{ keys: 'V', desc: 'Move Layer' }" in UI_BOOT_JS
    assert "{ keys: 'P / W / A / B / E / G / K / F / O / L / V', desc: 'Pick / Wand / All / Brush / Erase / Gradient / Fill / Blur / Rect / Lasso / Move', conflictCheck: false }" in UI_BOOT_JS
    assert "if (s.conflictCheck === false) return;" in UI_BOOT_JS
    assert "{ keys: 'Up / Down', desc: 'Cycle zones' }" in UI_BOOT_JS
    assert "{ keys: 'Ctrl+Up / Ctrl+Down', desc: 'Reorder zone priority' }" in UI_BOOT_JS
    assert "{ keys: 'Ctrl+Up/Down', desc: 'Reorder zone priority' }" not in UI_BOOT_JS


def test_fill_and_blur_shortcut_truth_is_consistent_across_overlays_and_handlers():
    assert 'id="vtModeFill"' in HTML
    assert 'title="Fill Bucket (K) — Zone: flood-fill mask; Layer: paint selected layer"' in HTML
    assert '>K</kbd> Fill Bucket<' in HTML
    assert '>F</kbd> Blur Brush<' in HTML
    assert '>F</kbd> Fill<' not in HTML

    assert "else if (key === 'k') { setCanvasMode('fill'); e.preventDefault(); }" in CANVAS_JS
    assert "else if (key === 'f') { setCanvasMode('blur-brush'); e.preventDefault(); }" in CANVAS_JS
    assert "['F', 'Blur Brush']" in CANVAS_JS
    assert "['G', 'Gradient'], ['K', 'Fill Bucket']" in CANVAS_JS
    assert "['F (×2)', 'Fit to window']" not in CANVAS_JS
    assert "F is reserved for Blur Brush" in CANVAS_JS

    assert "if (k === 'k') { if (typeof setCanvasMode === 'function') { setCanvasMode('fill'); e.preventDefault(); } return; }" in UI_BOOT_JS
    assert "if (k === 'f') { if (typeof setCanvasMode === 'function') { setCanvasMode('blur-brush'); e.preventDefault(); } return; }" in UI_BOOT_JS


def test_wiki_explains_zone_vs_layer_fill_bucket_targets():
    assert "Fill Bucket target rule" in WIKI_HTML
    assert "in <strong>ZONE</strong> mode, Fill Bucket edits the selected zone's mask" in WIKI_HTML
    assert "It does not paint RGB pixels into an existing rectangle" in WIKI_HTML
    assert "In <strong>LAYER</strong> mode, Fill Bucket paints the selected editable layer" in WIKI_HTML
    assert "enable Fit to Selection instead of trying to paint the rectangle with the zone bucket" in WIKI_HTML
    assert 'title="Fill Bucket (K) — Zone: flood-fill mask; Layer: paint selected layer"' in HTML


def test_selection_command_shortcuts_are_wired_before_ctrl_combo_bailout():
    keydown = _slice_between(
        CANVAS_JS,
        "document.addEventListener('keydown', (e) => {",
        "document.addEventListener('keyup', (e) => {",
    )
    ctrl_gate = "if (e.ctrlKey || e.metaKey || e.altKey) return; // Don't intercept other Ctrl combos"

    assert "['Ctrl+D', 'Deselect'], ['Ctrl+A', 'Select All']" in CANVAS_JS
    assert "['Ctrl+Shift+I', 'Invert Selection']" in CANVAS_JS
    assert ">Ctrl+D</kbd> Deselect<" in HTML
    assert ">Ctrl+Shift+I</kbd> Invert Selection<" in HTML

    for snippet in [
        "e.key.toLowerCase() === 'a'",
        "if (typeof _ctxSelectAll === 'function') _ctxSelectAll();",
        "e.key.toLowerCase() === 'd'",
        "if (typeof deselectRegion === 'function') deselectRegion();",
        "e.key.toLowerCase() === 'i'",
        "if (typeof invertRegionMask === 'function') invertRegionMask();",
    ]:
        assert snippet in keydown
        assert keydown.index(snippet) < keydown.index(ctrl_gate)


def test_clipboard_selection_shortcuts_are_wired_before_ctrl_combo_bailout():
    keydown = _slice_between(
        CANVAS_JS,
        "document.addEventListener('keydown', (e) => {",
        "document.addEventListener('keyup', (e) => {",
    )
    ctrl_gate = "if (e.ctrlKey || e.metaKey || e.altKey) return; // Don't intercept other Ctrl combos"

    assert "['Ctrl+C', 'Copy selected pixels']" in CANVAS_JS
    assert "['Ctrl+X', 'Cut selected pixels']" in CANVAS_JS
    assert "['Ctrl+V', 'Paste as new layer']" in CANVAS_JS
    assert "['Ctrl+J', 'New Layer via Copy']" in CANVAS_JS
    assert ">Ctrl+C</kbd> Copy<" in HTML
    assert ">Ctrl+X</kbd> Cut<" in HTML
    assert ">Ctrl+V</kbd> Paste<" in HTML
    assert ">Ctrl+J</kbd> New Layer via Copy<" in HTML

    for key, fn in [
        ("c", "copySelection"),
        ("x", "cutSelection"),
        ("v", "pasteAsLayer"),
        ("j", "newLayerViaCopy"),
    ]:
        key_check = f"e.key.toLowerCase() === '{key}'"
        call = f"if (typeof {fn} === 'function') {fn}();"
        assert key_check in keydown
        assert call in keydown
        assert keydown.index(key_check) < keydown.index(ctrl_gate)


def test_layer_stack_shortcuts_are_wired_before_ctrl_combo_bailout():
    keydown = _slice_between(
        CANVAS_JS,
        "document.addEventListener('keydown', (e) => {",
        "document.addEventListener('keyup', (e) => {",
    )
    ctrl_gate = "if (e.ctrlKey || e.metaKey || e.altKey) return; // Don't intercept other Ctrl combos"

    assert "['Ctrl+E', 'Merge Layer Down']" in CANVAS_JS
    assert "['Ctrl+Shift+E', 'Merge Visible Layers']" in CANVAS_JS
    assert "['Ctrl+Shift+N', 'New Blank Layer']" in CANVAS_JS
    assert "['Ctrl+L', 'Lock active zone to selected layer']" in CANVAS_JS
    assert ">Ctrl+E</kbd> Merge Down<" in HTML
    assert ">Ctrl+Shift+E</kbd> Merge Visible<" in HTML
    assert ">Ctrl+Shift+N</kbd> New Blank Layer<" in HTML
    assert ">Ctrl+L</kbd> Lock Zone to Layer<" in HTML
    assert "lockActiveZoneToSelectedLayer();" in LAYER_FLOW_JS
    assert "e.key === 'l' || e.key === 'L'" in LAYER_FLOW_JS

    merge_key = "e.key.toLowerCase() === 'e'"
    merge_call = "if (typeof mergeLayerDown === 'function') mergeLayerDown(_selectedLayerId);"
    flatten_call = "if (typeof flattenAllLayers === 'function') flattenAllLayers();"
    blank_call = "if (typeof addBlankLayer === 'function') addBlankLayer();"
    assert merge_call in keydown
    assert flatten_call in keydown
    assert blank_call in keydown
    assert keydown.index(merge_call) < keydown.index(ctrl_gate)
    assert keydown.index(flatten_call) < keydown.index(ctrl_gate)
    assert keydown.index(blank_call) < keydown.index(ctrl_gate)
    assert keydown.index("!e.shiftKey && !e.altKey && " + merge_key) < keydown.index(merge_call)
    assert keydown.index("e.shiftKey && !e.altKey && " + merge_key) < keydown.index(flatten_call)
    assert keydown.index("e.shiftKey && !e.altKey && e.key.toLowerCase() === 'n'") < keydown.index(blank_call)


def test_deselect_does_not_push_noop_undo_when_no_selection_exists():
    clear_helper = _slice_between(
        CANVAS_JS,
        "function clearZoneRegions(zoneIndex, noToast) {",
        "function clearAllRegions() {",
    )
    deselect_helper = _slice_between(
        CANVAS_JS,
        "function deselectRegion() {",
        "// --- COPY MASK BETWEEN ZONES ---",
    )

    assert "if (!zone.regionMask) {" in clear_helper
    assert clear_helper.index("if (!zone.regionMask)") < clear_helper.index("pushUndo(zoneIndex);")
    assert clear_helper.index("if (!zone.regionMask)") < clear_helper.index("return false;", clear_helper.index("if (!zone.regionMask)")) < clear_helper.index("pushUndo(zoneIndex);")
    assert "return true;" in clear_helper

    assert "if (!clearZoneRegions(selectedZoneIndex, true)) {" in deselect_helper
    assert "showToast('No selection to clear');" in deselect_helper
    assert deselect_helper.index("if (!clearZoneRegions(selectedZoneIndex, true))") < deselect_helper.index("return false;") < deselect_helper.index("renderContextActionBar();")
    assert "showToast('Cleared selection');" in deselect_helper
    assert "return true;" in deselect_helper


def test_select_all_and_invert_refresh_context_actions_after_mask_change():
    select_all_helper = _slice_between(
        CANVAS_JS,
        "function _ctxSelectAll() {",
        "function _ctxTransform()",
    )
    invert_helper = _slice_between(
        CANVAS_JS,
        "function invertRegionMask() {",
        "function _selectionRefineContext",
    )

    for helper in (select_all_helper, invert_helper):
        assert "renderRegionOverlay();" in helper
        assert "renderContextActionBar();" in helper
        assert "triggerPreviewRender();" in helper
        assert helper.index("renderRegionOverlay();") < helper.index("renderContextActionBar();")
        assert helper.index("renderContextActionBar();") < helper.index("triggerPreviewRender();")
        assert "return true;" in helper


def test_selection_refine_is_candidate_first_single_undo_not_nested_history():
    commit_helper = _slice_between(
        CANVAS_JS,
        "function _commitSelectionRefine",
        "function growRegionMask(px",
    )
    smooth_helper = _slice_between(
        CANVAS_JS,
        "function smoothRegionMask() {",
        "// --- DESELECT ---",
    )

    assert commit_helper.index("result.changedPixels <= 0") < commit_helper.index("pushUndo(context.zoneIndex);")
    assert commit_helper.index("pushUndo(context.zoneIndex);") < commit_helper.index("context.zone.regionMask = result.mask;")
    assert commit_helper.count("pushUndo(") == 1
    assert commit_helper.count("triggerPreviewRender();") == 1
    assert "renderContextActionBar();" in commit_helper
    assert "window.SPBSelectionRefine.smooth" in smooth_helper
    assert "shrinkRegionMask(" not in smooth_helper
    assert "growRegionMask(" not in smooth_helper


def test_selection_move_records_undo_only_after_real_drag_delta():
    move_preview = _slice_between(
        CANVAS_JS,
        "function updateSelectionMovePreview(pos) {",
        "function _getFastOverlayContext()",
    )
    move_mousedown = _slice_between(
        CANVAS_JS,
        "} else if (canvasMode === 'selection-move') {",
        "canvas.onmouseup = function (e) {",
    )

    assert "const dx = pos.x - _selectionMoveDrag.startX;" in move_preview
    assert "const dy = pos.y - _selectionMoveDrag.startY;" in move_preview
    assert "if ((dx !== 0 || dy !== 0) && !_selectionMoveDrag.undoPushed) {" in move_preview
    assert "pushZoneUndo('move selection', true);" in move_preview
    assert "_selectionMoveDrag.undoPushed = true;" in move_preview

    setup_block = move_mousedown.split("_selectionMoveDrag = {", 1)[1].split("};", 1)[0]
    assert "undoPushed: false," in setup_block
    assert "pushZoneUndo('move selection', true);" not in move_mousedown.split("_selectionMoveDrag = {", 1)[0]


def test_selection_move_mouseup_refreshes_preview_only_after_actual_move():
    move_mouseup = _slice_between(
        CANVAS_JS,
        "if (canvasMode === 'selection-move' && _selectionMoveDrag) {",
        "if (canvasMode === 'rect' && isDrawing && rectStart) {",
    )

    assert "const drag = _selectionMoveDrag;" in move_mouseup
    assert "const didMove = !!(drag && drag.undoPushed);" in move_mouseup
    assert "if (!didMove && drag && zones && zones[selectedZoneIndex]) {" in move_mouseup
    assert "zones[selectedZoneIndex].regionMask = new Uint8Array(drag.baseMask);" in move_mouseup
    assert "if (didMove && typeof triggerPreviewRender === 'function') triggerPreviewRender();" in move_mouseup
    assert "if (didMove && typeof renderZones === 'function') renderZones();" in move_mouseup
    assert "if (typeof updateRegionStatus === 'function') updateRegionStatus();" in move_mouseup


def test_rectangle_tool_second_click_commits_active_drag_before_starting_over():
    rect_mousedown = _slice_between(
        CANVAS_JS,
        "} else if (canvasMode === 'rect') {",
        "} else if (canvasMode === 'wand' || canvasMode === 'selectall') {",
    )

    assert "if (isDrawing && rectStart) {" in rect_mousedown
    assert "let endPos = pos;" in rect_mousedown
    assert "if (e.shiftKey) endPos = constrainRectToSquare(rectStart, endPos);" in rect_mousedown
    assert "commitRectSelection(endPos, e);" in rect_mousedown
    assert "isDrawing = false;" in rect_mousedown
    assert "e.preventDefault();" in rect_mousedown
    assert "return;" in rect_mousedown
    assert rect_mousedown.index("if (isDrawing && rectStart) {") < rect_mousedown.index("pushUndo(selectedZoneIndex);")

    rect_commit = _slice_between(
        CANVAS_JS,
        "function commitRectSelection(endPos, eventLike) {",
        "window.commitRectSelection = commitRectSelection;",
    )
    assert "typeof window !== 'undefined' ? window.paintRegionRect : null" in rect_commit
    assert "rectPainter(rectStart.x, rectStart.y, endPos.x, endPos.y, fillVal);" in rect_commit


def test_wiki_explains_rectangle_commit_behavior():
    assert 'id="vtModeRect"' in HTML
    assert 'title="Rectangle Select (O) — drag/release or click again to commit; Shift constrains square"' in HTML
    assert "Rectangle Select commit rule" in WIKI_HTML
    assert "drag and release to commit the rectangle" in WIKI_HTML
    assert "click once more to commit the active rectangle if the drag is still live" in WIKI_HTML
    assert "Hold <kbd>Shift</kbd> while drawing or committing to force a square" in WIKI_HTML
    assert "keep the target in <strong>ZONE</strong> mode and watch the zone mask overlay" in WIKI_HTML
    assert "['O', 'Rectangle Select']" in CANVAS_JS
    assert "['O', 'Marquee']" not in CANVAS_JS


def test_toolbar_brush_label_and_layer_transform_failure_are_specific():
    mode_body = _slice_between(
        CANVAS_JS,
        "function setCanvasMode(mode) {",
        "// Track E #107",
    )
    transform_body = _slice_between(
        CANVAS_JS,
        "function activateLayerContextTransform() {",
        "window.activateLayerContextTransform = activateLayerContextTransform;",
    )
    require_layer_body = _slice_between(
        CANVAS_JS,
        "function requireLayerToolbarTarget(toolName) {",
        "window.requireLayerToolbarTarget = requireLayerToolbarTarget;",
    )

    assert "['brush','colorbrush','recolor','smudge','erase','clone'," in mode_body
    assert "'history-brush','fill','gradient'].indexOf(mode) >= 0;" in mode_body
    assert "var layerAware = ['brush','colorbrush'," in CANVAS_JS
    assert "'history-brush','fill','gradient'].indexOf(canvasMode) >= 0;" in CANVAS_JS
    assert "label.textContent = _baseLabel + '" in mode_body
    assert "+ _target;" in mode_body
    refresh_body = _slice_between(
        CANVAS_JS,
        "function refreshActiveToolLabel() {",
        "window.refreshActiveToolLabel = refreshActiveToolLabel;",
    )
    assert "'layer-move': 'MOVE LAYER (drag selected layer)'" in refresh_body
    assert "'layer-pick': 'PICK ITEM (click layer or logo)'" in refresh_body
    assert "var modeLabel = isLayerToolbarMode() ? 'LAYER' : 'ZONE';" not in refresh_body
    assert ": baseLabel;" in refresh_body
    assert "const reason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;" in transform_body
    assert "showToast(reason || 'Select an editable layer first', true);" in transform_body
    assert "const reason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;" in require_layer_body
    assert "showToast(reason || `${toolName} needs an editable selected layer in LAYER mode`, 'warn');" in require_layer_body


def test_spatial_mode_legacy_helper_uses_real_erase_mode():
    helper_body = _slice_between(
        CANVAS_JS,
        "function toggleSpatialMode(mode) {",
        "function hasSpatialMask(zone) {",
    )

    assert "setCanvasMode('spatial-include');" in helper_body
    assert "setCanvasMode('spatial-exclude');" in helper_body
    assert "setCanvasMode('spatial-erase');" in helper_body
    assert "canvasMode = 'spatial-include'; // reuse include but with value=0" not in helper_body
    assert "'spatial-erase': 'vtModeSpatialErase'" in CANVAS_JS
    assert "const val = canvasMode === 'spatial-include' ? 1 : (canvasMode === 'spatial-exclude' ? 2 : 0);" in CANVAS_JS


def test_zone_card_spatial_erase_is_a_real_active_drawing_mode():
    spatial_panel = _slice_between(
        STATE_JS,
        "// ===== SPATIAL SELECTION - Include/Exclude refinement =====",
        "// \u2500\u2500 FINISH DNA SECTION \u2500\u2500",
    )

    assert "canvasMode === 'spatial-erase'" in spatial_panel
    assert "toggleSpatialMode('erase-spatial')" in spatial_panel
    assert "Erase spatial brush: remove include/exclude marks without clearing the whole zone" in spatial_panel
    assert "canvasMode === 'spatial-include' || canvasMode === 'spatial-exclude';" not in spatial_panel


def test_toolbar_global_escape_listener_respects_consumed_shortcuts():
    listener = _slice_between(
        UI_BOOT_JS,
        "document.addEventListener('keydown', function(e) {\n            if (e.defaultPrevented) return;\n            if (e.key === 'Escape') closeWebCommandMenu();",
        "function mountWebCommandLauncher()",
    )
    assert "if (e.defaultPrevented) return;" in listener


def test_vertical_toolbar_buttons_have_callable_handlers_and_active_mode_mapping():
    import re

    script_surface = "\n".join([HTML, CANVAS_JS, STATE_JS, API_JS, UI_BOOT_JS, FINISH_DATA_JS])
    function_defs = set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", script_surface))
    function_defs.update(re.findall(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=", script_surface))
    function_defs.update(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function\b", script_surface))
    ignored_inline_helpers = {"if", "typeof", "var", "const", "let", "document", "this", "event"}

    toolbar_buttons = re.findall(r"<button\b(?=[^>]*\bvtool-btn\b)([^>]*)>", HTML)
    assert len(toolbar_buttons) >= 54

    missing = []
    set_mode_buttons = []
    vt_map = _slice_between(CANVAS_JS, "const vtBtnId = {", "}[mode];")
    for attrs in toolbar_buttons:
        id_match = re.search(r'id="([^"]+)"', attrs)
        onclick_match = re.search(r'onclick="([^"]+)"', attrs)
        if not onclick_match:
            continue
        btn_id = id_match.group(1) if id_match else ""
        onclick = onclick_match.group(1)
        mode_match = re.search(r"setCanvasMode\('([^']+)'\)", onclick)
        if mode_match:
            mode = mode_match.group(1)
            set_mode_buttons.append((btn_id, mode))
            assert btn_id and btn_id in vt_map, f"{mode} toolbar button is not represented in vtBtnId active-state map"
        for call in re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", onclick):
            if call in ignored_inline_helpers or call in {"getElementById", "add", "remove"}:
                continue
            if call not in function_defs:
                missing.append((btn_id, call, onclick))

    assert len(set_mode_buttons) >= 25
    assert not missing


def test_repair_tool_shortcut_truth_is_consistent_across_overlay_and_fallback():
    expected_overlay = {
        'P': 'Eyedropper',
        'I': 'Pencil',
        'C': 'Color Brush',
        'S': 'Clone Stamp',
        'Q': 'Smudge',
        'R': 'Recolor',
        'D': 'Dodge',
        'J': 'Burn',
        'U': 'Shape',
    }
    for key, label in expected_overlay.items():
        assert f'>{key}</kbd> {label}<' in HTML

    stale_overlay_labels = [
        '>I</kbd> Eyedropper<',
        '>P</kbd> Pencil<',
        '>C</kbd> Clone Stamp<',
        '>O</kbd> Dodge/Burn<',
        '>S</kbd> Smudge<',
    ]
    for stale in stale_overlay_labels:
        assert stale not in HTML

    expected_fallback = {
        'c': 'colorbrush',
        's': 'clone',
        'q': 'smudge',
        'r': 'recolor',
        'd': 'dodge',
        'j': 'burn',
        'i': 'pencil',
        'u': 'shape',
        't': 'text',
        'n': 'pen',
        'm': 'ellipse-marquee',
        'g': 'gradient',
        'h': 'sharpen-brush',
    }
    for key, mode in expected_fallback.items():
        assert f"if (k === '{key}') {{ if (typeof setCanvasMode === 'function') {{ setCanvasMode('{mode}'); e.preventDefault(); }} return; }}" in UI_BOOT_JS

    assert "else if (key === 'c') { if (typeof setCanvasMode === 'function') setCanvasMode('colorbrush'); e.preventDefault(); }" in CANVAS_JS
    assert "else if (key === 's') { if (typeof setCanvasMode === 'function') setCanvasMode('clone'); e.preventDefault(); }" in CANVAS_JS
    assert "else if (key === 'i') { setCanvasMode('pencil'); e.preventDefault(); }" in CANVAS_JS


def test_wiki_m_shortcut_matches_elliptical_marquee_and_w_owns_magic_wand():
    shortcut_section = _slice_between(
        WIKI_HTML,
        "<h3>Shortcut Muscle Memory</h3>",
        "<div class=\"callout warning\">",
    )
    assert "<tr><td><kbd>W</kbd></td><td>Magic Wand</td><td>Select same-color regions before a zone or mask cleanup.</td></tr>" in shortcut_section
    assert "<tr><td><kbd>M</kbd></td><td>Elliptical Marquee</td><td>Make oval and circular selections for badges, panels, and masks.</td></tr>" in shortcut_section
    assert "<tr><td><kbd>M</kbd></td><td>Magic Wand</td>" not in WIKI_HTML
    assert "if (k === 'w') { if (typeof setCanvasMode === 'function') { setCanvasMode('wand'); e.preventDefault(); } return; }" in UI_BOOT_JS
    assert "if (k === 'm') { if (typeof setCanvasMode === 'function') { setCanvasMode('ellipse-marquee'); e.preventDefault(); } return; }" in UI_BOOT_JS
    assert "else if (key === 'm') { if (typeof setCanvasMode === 'function') setCanvasMode('ellipse-marquee'); e.preventDefault(); }" in CANVAS_JS


def test_d_key_is_dodge_not_reset_colors_in_visible_shortcut_surfaces():
    wiki = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")

    assert 'title="Dodge (D) — lighten pixels under brush"' in HTML
    assert "else if (key === 'd' && !e.shiftKey) { setCanvasMode('dodge'); e.preventDefault(); }" in CANVAS_JS
    assert "if (k === 'd') { if (typeof setCanvasMode === 'function') { setCanvasMode('dodge'); e.preventDefault(); } return; }" in UI_BOOT_JS

    assert '>D</kbd> Dodge<' in HTML
    assert '>D</kbd> Reset Colors<' not in HTML
    assert "if (e.shiftKey && (e.key === 'D' || e.key === 'd'))" not in CANVAS_JS
    assert "['Shift+D', 'Reset FG/BG colors']" not in CANVAS_JS
    assert "['Button', 'Reset FG/BG colors']" in CANVAS_JS
    assert "if (e.key === 'D' && e.shiftKey && !e.ctrlKey && !e.altKey)" in UI_BOOT_JS
    assert "{ keys: 'Shift+D', desc: 'Duplicate zone' }" in UI_BOOT_JS
    assert '>Shift+D</kbd> Duplicate Zone<' in HTML
    assert 'Reset foreground/background colors to default black/white (button only)' in HTML
    assert 'aria-label="Reset foreground and background colors">↺</button>' in HTML

    assert "Fix 057" in wiki
    assert "removes the stale <kbd>D</kbd> = Reset Colors claim" in wiki


def test_shift_h_and_shift_t_zone_shortcut_overlay_matches_handlers():
    assert ">Shift+H</kbd> History Gallery<" in HTML
    assert ">Shift+T</kbd> Template Library<" in HTML
    assert ">Shift+H</kbd> Mute/Unmute Zone<" not in HTML

    assert "// Shift+H: Open history gallery (bare H = sharpen tool)" in UI_BOOT_JS
    assert "if (e.key === 'H' && e.shiftKey && !e.ctrlKey && !e.altKey)" in UI_BOOT_JS
    assert "openHistoryGallery();" in UI_BOOT_JS
    assert "{ keys: 'Shift+H', desc: 'History gallery' }" in UI_BOOT_JS
    assert "['Shift+H', 'History Gallery']" in CANVAS_JS

    assert "// Shift+T: Open template library (bare T = text tool)" in UI_BOOT_JS
    assert "if (e.key === 'T' && e.shiftKey && !e.ctrlKey && !e.altKey)" in UI_BOOT_JS
    assert "openTemplateLibrary();" in UI_BOOT_JS
    assert "{ keys: 'Shift+T', desc: 'Template library' }" in UI_BOOT_JS
    assert "['Shift+T', 'Template Library']" in CANVAS_JS


def test_r_key_family_separates_recolor_randomize_render_reload_truth():
    wiki = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")

    assert 'title="Recolor Tool (R)' in HTML
    assert '>R</kbd> Recolor<' in HTML
    assert "else if (key === 'r' && !e.shiftKey) { setCanvasMode('recolor'); e.preventDefault(); }" in CANVAS_JS
    assert "if (k === 'r') { if (typeof setCanvasMode === 'function') { setCanvasMode('recolor'); e.preventDefault(); } return; }" in UI_BOOT_JS

    assert 'Rotate View CCW (R)' not in HTML
    assert 'Rotate View CCW — rotate 15 degrees counter-clockwise (button only)' in HTML

    assert '<kbd>Shift+R</kbd> Randomize' in HTML
    assert '<kbd>R</kbd> Randomize' not in HTML
    assert '>Ctrl+R</kbd> Render<' in HTML
    assert '>Shift+R</kbd> Randomize Zone<' in HTML
    assert '>Shift+R</kbd> Render<' not in HTML

    assert "if (e.ctrlKey && !e.shiftKey && e.key === 'r')" in UI_BOOT_JS
    assert "Ctrl+Shift+R reload-last-paint shortcut" in UI_BOOT_JS
    assert UI_BOOT_JS.index("if (e.ctrlKey && !e.shiftKey && e.key === 'r')") < UI_BOOT_JS.index("Ctrl+Shift+R reload-last-paint shortcut")
    assert "{ keys: 'Ctrl+R', desc: 'Render' }" in UI_BOOT_JS
    assert "{ keys: 'Shift+R', desc: 'Randomize selected zone' }" in UI_BOOT_JS
    assert "['Ctrl+Shift+R', 'Reload last paint file']" in CANVAS_JS
    assert "['Shift+R', 'Randomize Zone']" in CANVAS_JS
    assert "['R', 'Recolor (BG to FG color)']" in CANVAS_JS

    assert "Fix 061" in wiki
    assert "<kbd>R</kbd> is Recolor" in wiki
    assert "<kbd>Shift</kbd> + <kbd>R</kbd> randomizes the selected zone" in wiki
    assert "<kbd>Ctrl</kbd> + <kbd>R</kbd> renders" in wiki
    assert "<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> reloads the last paint file" in wiki
    assert "Rotate View buttons are button-only" in wiki


def test_number_keys_prioritize_opacity_and_zone_selection_uses_alt_modifier():
    assert 'Press 1-9 keys for quick opacity (1=10%, 5=50%, 0=100%).' in HTML
    assert '>1-9</kbd> Brush/Layer Opacity<' in HTML

    assert "// Number keys: context-sensitive (Photoshop standard)" in CANVAS_JS
    assert "else if (key >= '0' && key <= '9') {" in CANVAS_JS
    assert "setLayerOpacity(_selectedLayerId, pct);" in CANVAS_JS
    assert "showToast(`Layer opacity: ${pct}%`);" in CANVAS_JS
    assert "document.getElementById('brushOpacity')" in CANVAS_JS
    assert "showToast(`Brush opacity: ${pct}%`);" in CANVAS_JS

    assert "// Alt+1-9: Select zone." in UI_BOOT_JS
    assert "if (e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.key >= '1' && e.key <= '9')" in UI_BOOT_JS
    assert "// 1-9: Select zone" not in UI_BOOT_JS
    assert "{ keys: 'Alt+1-9', desc: 'Select zone' }" in UI_BOOT_JS
    assert "{ keys: '1-9', desc: 'Select zone' }" not in UI_BOOT_JS

    assert "['1-9', 'Brush/Layer Opacity']" in CANVAS_JS
    assert "['Alt+1-9', 'Select Zone 1-9']" in CANVAS_JS
    assert "['1-9', 'Select Zone 1-9']" not in CANVAS_JS


def test_reload_last_paint_shortcut_has_real_loader_and_recent_paint_source():
    load_helper = _slice_between(
        CANVAS_JS,
        "async function loadPaintByPath(path) {",
        "window.loadPaintByPath = loadPaintByPath;",
    )
    source_setter = _slice_between(
        CANVAS_JS,
        "function setCurrentSourcePaintFile(path, options) {",
        "window.setCurrentSourcePaintFile = setCurrentSourcePaintFile;",
    )
    recent_reload = _slice_between(
        UI_BOOT_JS,
        "SPB.reloadLastPaint = function() {",
        "// Improvement 26: Network error wrapper",
    )
    recent_menu = _slice_between(
        UI_BOOT_JS,
        "SPB.renderRecentPaintsMenu = function() {",
        "// Improvement 65: Expose recent-paint helpers globally",
    )

    assert "window.loadPaintByPath = loadPaintByPath;" in CANVAS_JS
    assert 'onchange="handlePaintPathCommit()"' in HTML
    assert "handlePaintPathCommit();}" in HTML
    assert "async function handlePaintPathCommit()" in CANVAS_JS
    assert "await validatePaintPath();" in CANVAS_JS
    assert "if (!_isFullTgaPaintPath(path)) return;" in CANVAS_JS
    assert "loadPaintByPath(path);" in CANVAS_JS
    assert 'data-testid="smart-tga-auto-build"' in SMART_SEPARATE_JS
    assert "SmartSep.enabled=true;SmartSep.layers.run()" in SMART_SEPARATE_JS
    assert "function autoLayersRequestJson()" in SMART_SEPARATE_JS
    assert "function shouldUseDiskTgaForAutoLayers(path)" in SMART_SEPARATE_JS
    assert "var SMART_TGA_BUILD_PREFIX = 'smart-tga-cycle';" in SMART_SEPARATE_JS
    assert "function requireSmartTgaHandshake(j)" in SMART_SEPARATE_JS
    assert "stale Smart TGA server response" in SMART_SEPARATE_JS
    assert "return requireSmartTgaHandshake(j);" in SMART_SEPARATE_JS
    assert "}).then(function (r) { return r.json(); }).then(requireSmartTgaHandshake);" in SMART_SEPARATE_JS
    assert "function currentAutoLayerCarHint(sourcePath)" in SMART_SEPARATE_JS
    assert "document.getElementById('outputDir')" in SMART_SEPARATE_JS
    assert "'X-Shokker-Internal': '1'" in SMART_SEPARATE_JS
    assert "paint_file: hint" in SMART_SEPARATE_JS
    assert "paint_file_hint: hint" in SMART_SEPARATE_JS
    assert "car_hint_path: carHint" in SMART_SEPARATE_JS
    assert "if (shouldUseDiskTgaForAutoLayers(hint))" in SMART_SEPARATE_JS
    assert "not whatever" in SMART_SEPARATE_JS
    assert "the visible layer stack currently recomposes after a previous sort" in SMART_SEPARATE_JS
    assert "if (isFullTgaPath(hint) && !liveFlat)" not in SMART_SEPARATE_JS
    assert "source path auto-layers failed; falling back to canvas upload" in SMART_SEPARATE_JS
    assert '"source": {"mode": _source_mode' in SERVER_PY
    assert "Source: <strong" in SMART_SEPARATE_JS
    assert "src.mode === 'paint_file' ? 'path'" in SMART_SEPARATE_JS
    assert "brand_graphics_merge" in SMART_SEPARATE_JS
    assert "Lyr.brandMerge = 'sponsors';" in SMART_SEPARATE_JS
    assert "brand_graphics_merge: Lyr.brandMerge || 'sponsors'" in SMART_SEPARATE_JS
    assert "gv(\"brand_graphics_merge\") or \"sponsors\"" in SERVER_PY
    assert "SPB_SMART_TGA_COMPANION_DECALS" in SERVER_PY
    assert r"car_num_(\d+)\.tga" in SERVER_PY
    assert "source_kind = \"car_num\"" in SERVER_PY
    assert r"car_team_(\d+)\.tga" in SERVER_PY
    assert "car_num_team_{team_m.group(1)}.tga" in SERVER_PY
    assert "\"source_kind\": source_kind" in SERVER_PY
    assert r"car(?:_num)?_(\d+)\.tga" in SERVER_PY
    assert "\"companion_decals\": companion_decal_info" in SERVER_PY
    assert "\"overrode_number_pixels\"" in SERVER_PY
    assert "companion_decal_info[\"number_priority\"] = \"decal_override\"" in SERVER_PY
    assert "Companion decals:" in SMART_SEPARATE_JS
    assert "paint-booth-3-canvas.js?v=spb-transactional-loader-20260822a" in HTML
    assert "spb-smarttga-rescue-banner-20260629" in HTML
    assert "spb-smarttga-ctrlzundo-20260630" in HTML
    assert "_pushLayerStackUndo('Smart TGA auto-build layers')" in SMART_SEPARATE_JS
    assert SMART_SEPARATE_JS.index("_pushLayerStackUndo('Smart TGA auto-build layers')") < SMART_SEPARATE_JS.index("window._psdLayers = layers;")
    assert "hasSmartTgaAutoLayers" in CANVAS_JS
    assert "Undo Smart TGA Auto-build" in CANVAS_JS
    assert "Generated stack - use this rescue button if the split is wrong." in CANVAS_JS
    assert "Restore the layer stack from before Smart TGA Auto-build" in CANVAS_JS
    assert "_maybeSmartTgaFlatCanvasForStackUndo(entry.label)" in CANVAS_JS
    assert "entry.smartTgaFlatCanvas = smartTgaFlatCanvas;" in CANVAS_JS
    assert "_restoreSmartTgaFlatCanvasFromStackEntry(entry);" in CANVAS_JS
    assert "const flatCanvasUndoSnapshot = _snapshotSmartTgaFlatCanvas();" in CANVAS_JS
    assert "undoEntry.smartTgaFlatCanvas = flatCanvasUndoSnapshot;" in CANVAS_JS
    assert "_psdLayersLoaded = _psdLayers.length > 0;" in CANVAS_JS
    assert "setCurrentSourcePaintFile" not in load_helper
    assert "return await loadPaintPreviewFromServer(normalizedPath);" in load_helper
    assert "showToast('Reloading source paint...');" in load_helper

    assert "window.spbAddRecentPaint(normalizedPath, { source: isPSDPath ? 'psd' : 'paint' });" in source_setter
    assert "if (typeof window.loadPaintByPath === 'function')" in recent_reload
    assert "try { window.loadPaintByPath(last.path); return; }" in recent_reload
    assert "Reload helper not wired" not in recent_reload
    assert "Recent paint reload is not ready" in recent_reload
    assert "if (e.ctrlKey && !e.shiftKey && e.key === 'r')" in UI_BOOT_JS
    assert UI_BOOT_JS.index("if (e.ctrlKey && !e.shiftKey && e.key === 'r')") < UI_BOOT_JS.index("Ctrl+Shift+R reload-last-paint shortcut")

    assert "function _spbEscapeRecentPaintHtml(value) {" in UI_BOOT_JS
    assert "const path = String((p && p.path) || '');" in recent_menu
    assert "_spbEscapeRecentPaintHtml(path)" in recent_menu
    assert "_spbEscapeRecentPaintHtml(name || '(unnamed)')" in recent_menu
    assert "title=\"' + (p.path || '') + '\"" not in recent_menu
    assert "window.loadPaintByPath(p.path);" in recent_menu
    assert "Recent paint reload is not ready" in recent_menu
    assert "Recent: ' + p.path" not in recent_menu


def test_source_file_picker_escapes_server_paths_and_uses_delegated_navigation():
    picker_state = _slice_between(
        CANVAS_JS,
        "// ===== SERVER-POWERED FILE PICKER =====",
        "function openFilePicker(options) {",
    )
    picker_open = _slice_between(
        CANVAS_JS,
        "function openFilePicker(options) {",
        "function closeFilePicker() {",
    )
    picker_nav = _slice_between(
        CANVAS_JS,
        "async function filePickerNavigate(dirPath) {",
        "function filePickerSelectItem(el, path) {",
    )

    assert "function _spbEscapeFilePickerHtml(value) {" in picker_state
    assert "function _spbEscapeFilePickerAttr(value) {" in picker_state
    assert "function _spbBindFilePickerNavigateDelegation(el) {" in picker_state
    assert "filePickerNavigate(item.dataset.fpPath || '');" in picker_state

    assert "_spbBindFilePickerNavigateDelegation(_fpBreadcrumb);" in picker_open
    assert "_spbBindFilePickerNavigateDelegation(_fpQuick);" in picker_open
    assert "_fpList.addEventListener('click'" in picker_open

    assert "${_spbEscapeFilePickerHtml(data.error)}" in picker_nav
    assert 'data-fp-action="navigate" data-fp-path=""' in picker_nav
    assert 'data-fp-path="${escapedPath}"' in picker_nav
    assert "${_spbEscapeFilePickerHtml(parts[i])}" in picker_nav
    assert "const ep = _spbEscapeFilePickerAttr(q.path || '');" in picker_nav
    assert "const ep = _spbEscapeFilePickerAttr(d.path || '');" in picker_nav
    assert "title=\"${_spbEscapeFilePickerAttr(q.path || '')}\"" in picker_nav
    assert "title=\"${_spbEscapeFilePickerAttr(d.path || '')}\"" in picker_nav
    assert "${_spbEscapeFilePickerHtml(q.name || 'Shortcut')}" in picker_nav
    assert "${_spbEscapeFilePickerHtml(d.name || 'Drive')}" in picker_nav
    assert 'data-fp-path="${_spbEscapeFilePickerAttr(data.parent)}"' in picker_nav
    assert "const safeP = _spbEscapeFilePickerAttr(item.path || '');" in picker_nav
    assert "const safeName = _spbEscapeFilePickerHtml(rawName);" in picker_nav
    assert "const safeSize = _spbEscapeFilePickerHtml(item.size_human || '');" in picker_nav
    assert '<span class="fp-name">${safeName}</span>' in picker_nav
    assert '<span class="fp-size">${safeSize}</span>' in picker_nav
    assert "${_spbEscapeFilePickerHtml(msg)}" in picker_nav

    assert "onclick=\"filePickerNavigate('" not in picker_nav
    assert "${data.error}" not in picker_nav
    assert "${item.name}</span>" not in picker_nav
    assert "${item.size_human || ''}" not in picker_nav
    assert "item.path.replace(/\"/g, '&quot;')" not in picker_nav


def test_custom_dual_shift_apply_updates_zone_preview_and_undo_contract():
    assert "function openDualShiftModal(zoneIndex)" in FINISH_DATA_JS
    assert "function applyCustomDualShift()" in FINISH_DATA_JS
    assert "fetch('/api/dual-shift-register'" in FINISH_DATA_JS
    assert "if (typeof pushZoneUndo === 'function') pushZoneUndo('Apply custom dual color shift');" in FINISH_DATA_JS
    assert "z.finish = data.finish_id;" in FINISH_DATA_JS
    assert "z.base = null;" in FINISH_DATA_JS
    assert "z.pattern = 'none';" in FINISH_DATA_JS
    assert "z.baseColorMode = 'special';" in FINISH_DATA_JS
    assert "z.baseColorSource = 'mono:' + data.finish_id;" in FINISH_DATA_JS
    assert "z._customDualShift = { colorA: ca, colorB: cb, intensity: intensity };" in FINISH_DATA_JS
    assert "if (typeof renderZones === 'function') renderZones();" in FINISH_DATA_JS
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in FINISH_DATA_JS
    assert "if (typeof triggerPreview === 'function') triggerPreview();" not in FINISH_DATA_JS
    assert "Custom Dual Shift applied - preview updating" in FINISH_DATA_JS

    assert "if (typeof openDualShiftModal === 'function') openDualShiftModal(finishBrowserTargetZone);" in UI_BOOT_JS
    assert "if (typeof openDualShiftModal === 'function') openDualShiftModal(zoneIndex);" in STATE_JS


def test_fill_delete_shortcuts_prioritize_pixels_before_zone_deletion():
    assert '>Delete</kbd> Delete Selected Pixels<' in HTML
    assert '>Shift+Delete</kbd> Delete Selected Zone<' in HTML
    assert '>Delete</kbd> Clear Selection<' not in HTML

    assert "if (e.altKey && e.key === 'Backspace')" in UI_BOOT_JS
    assert "fillSelectionWithColor(false)" in UI_BOOT_JS
    assert "if ((e.ctrlKey || e.metaKey) && e.key === 'Backspace')" in UI_BOOT_JS
    assert "fillSelectionWithColor(true)" in UI_BOOT_JS
    assert "if (e.key === 'Delete' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey)" in UI_BOOT_JS
    assert "typeof hasActivePixelSelection === 'function' && hasActivePixelSelection()" in UI_BOOT_JS
    assert "if (typeof deleteSelection === 'function') deleteSelection();" in UI_BOOT_JS
    assert "Use Shift+Delete to delete the selected zone." in UI_BOOT_JS
    assert "if (e.key === 'Delete' && e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey)" in UI_BOOT_JS
    assert "if (e.key === 'Delete' || e.key === 'Backspace')" not in UI_BOOT_JS
    assert "{ keys: 'Delete', desc: 'Delete selected pixels when a pixel selection exists' }" in UI_BOOT_JS
    assert "{ keys: 'Shift+Delete', desc: 'Delete selected zone' }" in UI_BOOT_JS

    assert "window.hasActivePixelSelection = hasActivePixelSelection;" in CANVAS_JS
    assert "window.fillSelectionWithColor = fillSelectionWithColor;" in CANVAS_JS
    assert "window.deleteSelection = deleteSelection;" in CANVAS_JS


def test_fill_delete_refuse_blocked_selected_layer_before_composite_fallback():
    fill_helper = _slice_between(
        CANVAS_JS,
        "function fillSelectionWithColor(useBG) {",
        "window.fillSelectionWithColor = fillSelectionWithColor;",
    )
    delete_helper = _slice_between(
        CANVAS_JS,
        "function deleteSelection() {",
        "window.deleteSelection = deleteSelection;",
    )

    for helper in (fill_helper, delete_helper):
        assert "const layerBlockReason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;" in helper
        assert "if (layerBlockReason) {" in helper
        assert "showToast(layerBlockReason, 'warn');" in helper
        assert "return;" in helper.split("if (layerBlockReason) {", 1)[1].split("}", 1)[0]

    assert fill_helper.index("if (layerBlockReason)") < fill_helper.index("if (typeof isLayerEditTarget === 'function' && isLayerEditTarget())")
    assert delete_helper.index("if (layerBlockReason)") < delete_helper.index("if (typeof isLayerEditTarget === 'function' && isLayerEditTarget())")


def test_selection_modifier_tools_refresh_preview_after_mask_edits():
    selection_modifiers = _slice_between(
        CANVAS_JS,
        "function refreshSelectionModifierResult() {",
        "window.selectColorRange = selectColorRange;",
    )

    helper = _slice_between(
        selection_modifiers,
        "function refreshSelectionModifierResult() {",
        "function growSelection(px) {",
    )
    assert "renderRegionOverlay();" in helper
    assert "renderContextActionBar();" in helper
    assert "triggerPreviewRender();" in helper

    assert "return growRegionMask(px);" in selection_modifiers
    assert "return shrinkRegionMask(px);" in selection_modifiers
    assert "return smoothRegionMask();" in selection_modifiers
    assert "pushZoneUndo(" not in selection_modifiers
    assert "pushUndo(selectedZoneIndex);" in selection_modifiers
    assert "mode === 'add'" in selection_modifiers
    assert "mode === 'subtract'" in selection_modifiers
    assert "Number.isFinite(parsedTolerance)" in selection_modifiers

    assert selection_modifiers.count("refreshSelectionModifierResult();") >= 1


def test_copy_cut_selection_respect_selected_layer_target_before_composite():
    source_helper = _slice_between(
        CANVAS_JS,
        "function _getSelectionSourceData(selectionInfo) {",
        "function _captureSelectionClipboardData() {",
    )
    cut_helper = _slice_between(
        CANVAS_JS,
        "function cutSelection() {",
        "function pasteAsLayer() {",
    )

    assert "typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()" in source_helper
    assert "typeof getSelectedLayer === 'function'" in source_helper
    assert "typeof isLayerEditTarget === 'function' && isLayerEditTarget()" not in source_helper
    assert "if (layer && layer.img) {" in source_helper
    assert "sourceTarget: 'layer'," in source_helper
    assert "const layerBlockReason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;" in source_helper
    assert "sourceTarget: 'blocked-layer'," in source_helper
    assert source_helper.index("if (layer && layer.img)") < source_helper.index("sourceTarget: 'composite'")

    assert "typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()" in cut_helper
    assert "typeof _diagnoseLayerPaintFail === 'function'" in cut_helper
    assert "showToast(layerBlockReason, 'warn');" in cut_helper
    assert cut_helper.index("if (layerBlockReason)") < cut_helper.index("const data = _storeClipboardFromSelection(true);")


def test_layer_transform_refuses_locked_layer_at_selection_and_commit_edges():
    selection_transform = _slice_between(
        CANVAS_JS,
        "function transformSelectedLayerRegion() {",
        "window.transformSelectedLayerRegion = transformSelectedLayerRegion;",
    )
    commit_transform = _slice_between(
        CANVAS_JS,
        "function commitLayerTransform() {",
        "// Cancel layer transform",
    )

    assert "const layerBlockReason = (typeof _diagnoseLayerPaintFail === 'function') ? _diagnoseLayerPaintFail() : null;" in selection_transform
    assert "showToast(layerBlockReason, 'warn');" in selection_transform
    assert selection_transform.index("if (layerBlockReason)") < selection_transform.index("const layer = (typeof isLayerEditTarget === 'function' && isLayerEditTarget())")

    assert "if (layer.locked) {" in commit_transform
    assert "is locked — transform was cancelled" in commit_transform
    assert "cancelLayerTransform();" in commit_transform
    assert commit_transform.index("if (layer.locked)") < commit_transform.index("// Workstream 17 #327")


def test_ctrl_s_copy_makes_local_autosave_not_portable_shokk_claims():
    wiki = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")

    assert "Autosave snapshot saved locally" in UI_BOOT_JS
    assert "Config saved" not in UI_BOOT_JS
    assert "{ keys: 'Ctrl+S', desc: 'Save local autosave snapshot' }" in UI_BOOT_JS

    assert "<kbd>Ctrl+S</kbd> Local Snapshot" in HTML
    assert "<kbd>Ctrl+S</kbd> Save Config" not in HTML

    assert "Ctrl+S is not Save SHOKK" in wiki
    assert "Ctrl+S refreshes the local autosave snapshot" in wiki
    assert "does not create a portable <code>.shokk</code>" in wiki


def test_fill_and_gradient_route_by_explicit_toolbar_mode():
    fill_branch = _slice_between(
        CANVAS_JS,
        "} else if (canvasMode === 'fill') {",
        "} else if (canvasMode === 'gradient') {",
    )
    gradient_branch = _slice_between(
        CANVAS_JS,
        "} else if (canvasMode === 'gradient') {",
        "} else if (canvasMode === 'selection-move') {",
    )
    gradient_mouseup = _slice_between(
        CANVAS_JS,
        "if (canvasMode === 'gradient' && isDrawing && window._gradientStart) {",
        "// === NEW TOOLS MOUSEUP ===",
    )

    assert "isLayerToolbarMode()" in fill_branch
    assert "fillBucketOnLayer(" in fill_branch
    assert "fillBucketAtPoint(" in fill_branch
    assert "requireLayerToolbarTarget('Fill Bucket')" in fill_branch
    assert "requireZoneToolbarMode('Fill Bucket')" in fill_branch
    assert "pushUndo(selectedZoneIndex);" not in fill_branch
    assert "const filled = fillBucketAtPoint(pos.x, pos.y);" in fill_branch
    assert "if (filled) {" in fill_branch

    assert "requireLayerToolbarTarget('Gradient')" in gradient_branch
    assert "_pushLayerUndo" not in gradient_branch
    assert "window._gradientTargetLayerId = null;" in gradient_branch
    assert "window._gradientTargetLayerId = _selectedLayerId || null;" in gradient_branch
    assert "window._gradientTarget = { kind: 'layer', layerId: window._gradientTargetLayerId };" in gradient_branch
    assert "window._gradientTarget = { kind: 'zone', zoneIndex: selectedZoneIndex };" in gradient_branch
    assert "_pushLayerUndo(targetLayer, 'gradient on layer');" not in gradient_mouseup
    assert "target && target.kind === 'layer'" in gradient_mouseup
    assert "target && target.kind === 'zone'" in gradient_mouseup
    assert "fillGradientOnLayer(" in gradient_mouseup
    assert "fillGradientMask(" in gradient_mouseup


def test_layer_gradient_honors_custom_fg_bg_and_transparent_option():
    layer_gradient = _slice_between(
        CANVAS_JS,
        "function _hexToGradientRgba(hex, alpha) {",
        "function _applyBakedSpecialFloodFill(",
    )

    assert "function fillGradientOnLayer(" in layer_gradient
    assert "const fg = typeof _foregroundColor === 'string' ? _foregroundColor : '#000000';" in layer_gradient
    assert "const bg = typeof _backgroundColor === 'string' ? _backgroundColor : '#ffffff';" in layer_gradient
    assert "document.getElementById('gradientFgToTransparent')?.checked" in layer_gradient
    assert "c0 = reverse ? _gradQuad(fg, 0) : _gradQuad(fg, 1);" in layer_gradient
    assert "c1 = reverse ? _gradQuad(fg, 1) : _gradQuad(fg, 0);" in layer_gradient
    assert "c0 = reverse ? _gradQuad(bg, 1) : _gradQuad(fg, 1);" in layer_gradient
    assert "c1 = reverse ? _gradQuad(fg, 1) : _gradQuad(bg, 1);" in layer_gradient
    assert "grad.addColorStop(0, `rgba(${c0[0]}, ${c0[1]}, ${c0[2]}, ${c0[3] / 255})`);" in layer_gradient
    assert "grad.addColorStop(1, `rgba(${c1[0]}, ${c1[1]}, ${c1[2]}, ${c1[3] / 255})`);" in layer_gradient
    assert "_pushLayerUndo(layer, 'gradient on layer');" in layer_gradient
    assert "Gradient skipped: layer pixels already match this result" in layer_gradient


def test_gradient_map_canvas_pick_restores_dialog_when_click_misses_canvas():
    picker_helper = _slice_between(
        CANVAS_JS,
        "function _pickCanvasColorOnce(label, onPick, onCancel) {",
        "function _wireAdjustmentDialogColorField(",
    )
    dialog_helper = _slice_between(
        CANVAS_JS,
        "if (action === 'canvas') {",
        "});",
    )

    miss_branch = _slice_between(
        picker_helper,
        "if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {",
        "return;",
    )
    assert "e.preventDefault();" in miss_branch
    assert "e.stopPropagation();" in miss_branch
    assert "cleanup();" in miss_branch
    assert "if (typeof onCancel === 'function') onCancel();" in miss_branch
    assert "showToast('Canvas color pick cancelled', 'info');" in miss_branch
    assert "if (overlay) overlay.style.visibility = 'hidden';" in dialog_helper
    assert "if (overlay) overlay.style.visibility = '';" in dialog_helper


def test_layer_adjustment_commit_refreshes_layer_panel_and_bounds():
    commit_helper = _slice_between(
        CANVAS_JS,
        "function _commitAdjustment(target) {",
        "function adjustBrightnessContrast(",
    )
    layer_branch = commit_helper.split("if (target.isLayer && target.layer) {", 1)[1].split("} else {", 1)[0]

    assert "target.layer.img = target.canvas;" in layer_branch
    assert "recompositeFromLayers();" in layer_branch
    assert "renderLayerPanel();" in layer_branch
    assert "drawLayerBounds();" in layer_branch
    assert "triggerPreviewRender();" in layer_branch
    assert layer_branch.index("recompositeFromLayers();") < layer_branch.index("renderLayerPanel();")
    assert layer_branch.index("renderLayerPanel();") < layer_branch.index("drawLayerBounds();")
    assert layer_branch.index("drawLayerBounds();") < layer_branch.index("triggerPreviewRender();")


def test_live_paint_capture_uses_composite_helper_everywhere():
    assert "function buildLivePaintCompositeCanvas()" in CANVAS_JS
    preview_attach = _slice_between(
        CANVAS_JS,
        "function _attachLivePaintCanvasToPreviewBody(body, fallbackPaintFile) {",
        "async function doPreviewRender(zoneHash, previewScale, options) {",
    )
    assert "buildLivePaintCompositeCanvas()" in preview_attach
    assert "window.buildLivePaintCompositeCanvas === 'function'" in API_JS


def test_quick_export_png_uses_live_layer_composite_helper():
    quick_export = _slice_between(
        CANVAS_JS,
        "function quickExportPNG() {",
        "window.quickExportPNG = quickExportPNG;",
    )

    assert 'onclick="quickExportPNG()"' in HTML
    assert "Quick Export — save canvas as PNG file" in HTML
    assert "typeof buildLivePaintCompositeCanvas === 'function'" in quick_export
    assert "buildLivePaintCompositeCanvas()" in quick_export
    assert "document.getElementById('paintCanvas')" in quick_export
    assert "link.href = pc.toDataURL('image/png');" in quick_export


def test_layer_transform_tool_active_state_tracks_transform_session():
    active_helper = _slice_between(
        CANVAS_JS,
        "function _setLayerTransformToolActive(active) {",
        "function rotateActiveLayerTransformBy(",
    )
    layer_transform = _slice_between(
        CANVAS_JS,
        "function activateLayerTransform() {",
        "// Commit layer transform",
    )
    commit_transform = _slice_between(
        CANVAS_JS,
        "function commitLayerTransform() {",
        "// Cancel layer transform",
    )
    cancel_transform = _slice_between(
        CANVAS_JS,
        "function cancelLayerTransform() {",
        "// ═══ EXPOSE",
    )

    assert 'id="vtModeLayerTransform"' in HTML
    assert "document.getElementById('vtModeLayerTransform')" in active_helper
    assert "document.querySelectorAll('.vtool-btn').forEach(el => el.classList.remove('active'))" in active_helper
    assert "btn.classList.add('active');" in active_helper
    assert "btn.classList.remove('active');" in active_helper
    assert "_setLayerTransformToolActive(true);" in layer_transform
    assert "_setLayerTransformToolActive(false);" in commit_transform
    assert "_setLayerTransformToolActive(false);" in cancel_transform


def test_render_validation_suppresses_tga_warning_for_live_canvas_payloads():
    validator = _slice_between(
        API_JS,
        "function validateRenderPayload(paintFile, zones, extras) {",
        "// [IMP-18] Toast helper",
    )

    assert "const hasLivePaintPayload = !!(extras && extras.paint_image_base64);" in validator
    assert "if (!hasLivePaintPayload) {" in validator
    assert "else if (!/\\.tga$/i.test(paintFile))" in validator
    assert "Paint file does not end in .tga" in validator


def test_change_file_live_flat_source_renders_visible_canvas_not_stale_path():
    load_input = _slice_between(
        CANVAS_JS,
        "function loadPaintImage(input) {",
        "// SHOKK / programmatic load: from URL",
    )
    source_setter = _slice_between(
        CANVAS_JS,
        "function setCurrentSourcePaintFile(path, options) {",
        "window.setCurrentSourcePaintFile = setCurrentSourcePaintFile;",
    )
    render_body = _slice_between(
        API_JS,
        "async function doRender() {",
        "// [IMP-28] Smart deduplication",
    )

    assert "function markFlatPaintLiveSource(file, source)" in CANVAS_JS
    assert "window._spbFlatPaintLiveSource" in CANVAS_JS
    assert "markFlatPaintLiveSource(file, 'change-file-tga');" in load_input
    assert "markFlatPaintLiveSource(file, 'change-file-flat');" in load_input
    assert "Full Render will use the live canvas" in load_input
    assert "clearFlatPaintLiveSource('set source paint file');" in source_setter

    assert "let hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);" in render_body
    assert "if (!paintFile && !hasLiveFlatSource)" in render_body
    assert "if (paintFile && !hasLiveFlatSource && !paintFile.includes('/') && !paintFile.includes('\\\\'))" in render_body
    assert "if (hasLiveFlatSource && !extras.paint_image_base64)" in render_body
    assert "extras.paint_image_base64 = await canvasToBase64Async(flatCanvas);" in render_body
    assert "extras.source_mode = 'live_flat_canvas';" in render_body


def test_change_file_live_flat_source_exports_visible_canvas_to_photoshop_round_trip():
    export_body = _slice_between(
        API_JS,
        "async function doExportToPhotoshop() {",
        "    const btn = document.getElementById('btnDoExportToPs');",
    )

    assert "const hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);" in export_body
    assert "if (!paintFile && !hasLiveFlatSource)" in export_body
    assert "if (hasLiveFlatSource && !extras.paint_image_base64)" in export_body
    assert "extras.paint_image_base64 = await canvasToBase64Async(_flatPcExp);" in export_body
    assert "extras.source_mode = 'live_flat_canvas';" in export_body
    assert "[doExportToPhotoshop] Live flat image source" in export_body


def test_change_file_live_flat_source_save_shokk_bundles_visible_canvas_payload():
    save_body = _slice_between(
        SHOKK_JS,
        "async function confirmSaveShokk() {",
        "async function deleteShokkFile(filename, event) {",
    )
    shokk_save_endpoint = _slice_between(
        SERVER_SHOKK_ROUTES_PY,
        "@app.route('/api/shokk/save', methods=['POST'])",
        "@app.route('/api/shokk/open', methods=['POST'])",
    )

    assert "const hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);" in save_body
    assert "if (includePaint && hasLiveFlatSource)" in save_body
    assert "const liveCanvas = buildLivePaintCompositeCanvas();" in save_body
    assert "savePayload.paint_image_base64 = await canvasToBase64Async(liveCanvas);" in save_body
    assert "savePayload.source_mode = 'live_flat_canvas';" in save_body
    assert "data.paint_source === 'live_canvas'" in save_body

    assert 'paint_image_base64 = data.get("paint_image_base64")' in shokk_save_endpoint
    assert "live_paint_path = None" in shokk_save_endpoint
    assert "prefix=\"shokk_live_paint_\"" in shokk_save_endpoint
    assert "paint_path = live_paint_path" in shokk_save_endpoint
    assert '"paint_source": paint_source if include_paint and paint_path is not None else None' in shokk_save_endpoint
    assert "os.remove(live_paint_path)" in shokk_save_endpoint


def test_shokk_library_grid_escapes_manifest_metadata_and_paths():
    html_helper = _slice_between(
        SHOKK_JS,
        "function _shokkEscapeHtml(value) {",
        "function _shokkEscapeSingleQuotedAttr(value) {",
    )
    attr_helper = _slice_between(
        SHOKK_JS,
        "function _shokkEscapeSingleQuotedAttr(value) {",
        "/**\n * Updates the \"SPEC: loaded/missing/none\" status chip",
    )
    library_loader = _slice_between(
        SHOKK_JS,
        "async function _loadShokkLibraryContents() {",
        "/**\n * Renders the SHOKK library grid.",
    )
    grid_renderer = _slice_between(
        SHOKK_JS,
        "function _renderShokkGrid(entries, filter = '') {",
        "let _selectedShokkPath = '';",
    )
    card_renderer = _slice_between(
        SHOKK_JS,
        "function _shokkCard(e) {",
        "/**\n * Marks the given SHOKK card as selected",
    )

    for needle in (
        ".replace(/&/g, '&amp;')",
        ".replace(/</g, '&lt;')",
        ".replace(/>/g, '&gt;')",
        ".replace(/\"/g, '&quot;')",
        ".replace(/'/g, '&#39;')",
    ):
        assert needle in html_helper

    assert "_shokkEscapeHtml(String(value == null ? '' : value)" in attr_helper
    assert ".replace(/\\\\/g, '\\\\\\\\')" in attr_helper
    assert ".replace(/'/g, \"\\\\'\")" in attr_helper
    assert ".replace(/\\r/g, '\\\\r')" in attr_helper
    assert ".replace(/\\n/g, '\\\\n')" in attr_helper

    assert "${_shokkEscapeHtml(e.message)}" in library_loader
    assert "${_shokkEscapeHtml(filter)}" in grid_renderer
    assert "${_shokkEscapeHtml(t)}" in card_renderer
    assert "by ${_shokkEscapeHtml(e.author)}" in card_renderer
    assert "${_shokkEscapeHtml(e.size_mb)}MB" in card_renderer
    assert "const safePath = _shokkEscapeSingleQuotedAttr(e.path || '');" in card_renderer
    assert "const safeFilename = _shokkEscapeSingleQuotedAttr(e.filename || '');" in card_renderer
    assert 'src="${_shokkEscapeHtml(previewUrl)}"' in card_renderer
    assert "${_shokkEscapeHtml(displayName)}" in card_renderer
    assert "${_shokkEscapeHtml(displayDesc.substring(0, 80))}" in card_renderer

    assert "${e.message}" not in library_loader
    assert "${filter}" not in grid_renderer
    assert "${t}</span>" not in card_renderer
    assert "by ${e.author}" not in card_renderer
    assert "${e.name || e.filename}" not in card_renderer
    assert "previewUrl.replace(/\"/g, '&quot;')" not in card_renderer


def test_source_and_output_header_copy_matches_current_source_modes():
    assert 'placeholder="Drop/paste a source path, browse TGA, or import PSD..."' in HTML
    assert "live layered canvas source" in HTML
    assert "Use the folder button for TGA files, or the PSD button for Photoshop layers." in HTML
    assert "Browse TGA Source" in HTML
    assert "original paint TGA file path" not in HTML

    assert "Diffuse naming follows the custom-number setting: car_num_XXXXX.tga or car_XXXXX.tga." in HTML
    assert "Exact iRacing car folder where rendered car_num_XXXXX.tga or car_XXXXX.tga plus car_spec_XXXXX.tga files will be saved" in HTML
    assert "Output files will be named car_num_XXXXX.tga." not in HTML


def test_render_results_show_live_link_status_independent_of_output_save():
    render_results = _slice_between(
        API_JS,
        "function showRenderResults(result) {",
        "panel.style.display = 'block';",
    )
    assert "const requestedLiveLink = !!(result.live_link || document.getElementById('liveLinkCheckbox')?.checked);" in render_results
    assert "Live Link pushed" in render_results
    assert "Live Link Error:" in render_results
    assert "no deployment status returned" in render_results
    assert "result.live_link?.error && !result.live_link?.success && !result.output_dir?.success" not in render_results
    assert 'Set the "iRacing Car Folder" path in the header' in render_results


def test_one_click_iracing_deploy_row_reappears_after_render_and_escapes_cars():
    deploy_panel = _slice_between(
        HTML,
        '<!-- One-Click Deploy to iRacing -->',
        '<!-- Render History Strip -->',
    )
    render_results = _slice_between(
        API_JS,
        "function showRenderResults(result) {",
        "    // Show paint + spec previews",
    )
    car_loader = _slice_between(
        API_JS,
        "async function loadIracingCars() {",
        "/**\n * Deploy the last render result to an iRacing car folder.",
    )

    assert 'id="renderDeployRow"' in deploy_panel
    assert 'display:none !important' not in deploy_panel
    assert 'onclick="deployToIracing()"' in deploy_panel

    assert "lastRenderedJobId = result.job_id || null;" in render_results
    assert "const deployRow = document.getElementById('renderDeployRow');" in render_results
    assert "deployRow.style.display = 'block';" in render_results
    assert "loadIracingCars();" in render_results
    assert "deployRow.style.display = 'none';" in render_results
    assert "Deploy row removed - render button handles everything" not in render_results

    assert "const name = _spbEscapeRenderHtml(c.name || '');" in car_loader
    assert "const path = _spbEscapeRenderHtml(c.path || '');" in car_loader
    assert "const count = _spbEscapeRenderHtml(c.tga_count ?? 0);" in car_loader
    assert '<option value="${name}" title="${path}">${name} (${count} files)</option>' in car_loader
    assert '<option value="${c.name}" title="${c.path}">${c.name} (${c.tga_count} files)</option>' not in car_loader


def test_zone_status_warns_when_source_layer_reference_is_missing():
    status_block = _slice_between(
        STATE_JS,
        "function zoneHasMissingSourceLayer(zone) {",
        "// ---------- IMPROVEMENT 04: toggleLock",
    )
    assert "window.zoneHasMissingSourceLayer = zoneHasMissingSourceLayer;" in status_block
    assert "if (zoneHasMissingSourceLayer(zone)) return 'missing_source_layer';" in status_block
    assert "missing_source_layer: { color: '#ff4444'" in status_block
    assert "Zone is restricted to a missing PSD layer." in status_block
    assert "Missing source layer restriction:" in STATE_JS


def test_global_ctrl_z_only_yields_to_text_entry_fields():
    assert "function _isTextEntryTargetForGlobalUndo(target)" in STATE_JS
    assert "if (_isTextEntryTargetForGlobalUndo(e.target)) return;" in STATE_JS
    assert "tag === 'input' || tag === 'textarea' || tag === 'select'" not in STATE_JS


def test_toolbar_and_canvas_view_modes_are_explicit_and_preview_aware():
    assert 'id="btnToolbarModeZone"' in HTML
    assert 'id="btnToolbarModeLayer"' in HTML
    assert 'id="layerPaintSourceOptions"' in HTML
    assert 'id="layerPaintSourceMode"' in HTML
    assert 'id="layerSpecialPickerBtn"' in HTML
    assert 'id="btnCanvasViewSource"' in HTML
    assert 'id="btnCanvasViewRendered"' in HTML
    assert 'id="canvasRenderedViewImg"' in HTML
    assert 'id="btnPreviewRefreshSource"' in HTML
    assert 'id="btnBeforeAfterSource"' in HTML

    assert "var toolbarEditMode = (typeof window.toolbarEditMode !== 'undefined')" in CANVAS_JS
    assert "function setToolbarEditMode(mode, options)" in CANVAS_JS
    assert "function setCanvasDisplayMode(mode, options)" in CANVAS_JS
    assert "function isPreviewSurfaceVisible()" in CANVAS_JS
    assert "function syncRenderedCanvasPreview()" in CANVAS_JS
    assert "function updatePreviewControlAvailability()" in CANVAS_JS
    assert "isPreviewSurfaceVisible()" in CANVAS_JS
    assert "placementLayer === 'none'" in CANVAS_JS
    assert "setCanvasDisplayMode('rendered', { skipPreview: true })" in CANVAS_JS
    assert "captureBeforeImage(paintImg.src);" in CANVAS_JS
    assert "Switch to CAR or SPLIT view" in STATE_JS


def test_reset_all_view_button_resets_zoom_rotation_and_flips():
    reset_view = _slice_between(
        CANVAS_JS,
        "function resetAllView() {",
        "window.rotateView = rotateView;",
    )

    assert 'onclick="resetAllView()"' in HTML
    assert 'Reset All View — reset rotation, flip, and zoom' in HTML
    assert "viewRotation = 0; viewFlippedH = false; viewFlippedV = false; currentZoom = 1;" in reset_view
    assert "applyZoom();" in reset_view
    assert "_updateViewTransform();" in reset_view
    assert "View reset to 100%" in reset_view
    assert "window.resetAllView = resetAllView;" in CANVAS_JS


def test_layer_fill_and_brush_now_expose_baked_special_controls():
    assert "function setLayerPaintSourceMode(mode, options)" in CANVAS_JS
    assert "function setLayerPaintSpecial(id, options)" in CANVAS_JS
    assert "function openLayerSpecialPicker(triggerEl)" in CANVAS_JS
    assert "function _drawLayerSpecialStamp(ctx, x, y, radius, opacity, hardness)" in CANVAS_JS
    assert "function _applyBakedSpecialFloodFill(data, visited, lw, lh, minX, minY, maxX, maxY, opacity)" in CANVAS_JS
    assert "isLayerPaintSourceSpecial()" in CANVAS_JS
    assert "((mode === 'fill' || mode === 'gradient') && !layerToolbarActive)" in CANVAS_JS
    assert "type === 'layerSpecialPaint'" in STATE_JS


def test_scoped_zone_fill_surfaces_foreground_picker_in_toolbar():
    assert "function _shouldShowForegroundPickerForZoneFill(mode, layerToolbarActive)" in CANVAS_JS
    assert "const showZoneFillForeground = _shouldShowForegroundPickerForZoneFill(mode, layerToolbarActive);" in CANVAS_JS
    assert "showZoneFillForeground || (layerToolbarActive && (mode === 'fill' || mode === 'gradient'))" in CANVAS_JS
    assert "the FG color picker now drives the local preview/base tint here" in CANVAS_JS
    assert "if (typeof refreshToolbarModeSensitiveUi === 'function') refreshToolbarModeSensitiveUi();" in STATE_JS


def test_zone_brush_and_fill_scope_to_existing_selector_before_overriding_region_mask():
    assert "function _zoneBrushUsesScopedRefinement(zone)" in CANVAS_JS
    assert "function _buildZoneScopedSelectorMask(zone, w, h)" in CANVAS_JS
    assert "function _paintScopedSpatialCircle(zone, scopeMask, w, h, cx, cy, radius, value)" in CANVAS_JS
    assert "function _maybeAdoptForegroundAsScopedZoneBaseColor(zoneIndex)" in CANVAS_JS
    assert "function _normalizeScopedZoneAutoBaseColor(zoneIndex)" in CANVAS_JS

    brush_helper = _slice_between(
        CANVAS_JS,
        "function paintRegionCircle(x, y, radius, value, opacityArg) {",
        "function fillGradientMask(x1, y1, x2, y2, gradientType) {",
    )
    fill_helper = _slice_between(
        CANVAS_JS,
        "function fillBucketAtPoint(startX, startY) {",
        "function constrainRectToSquare(start, end) {",
    )
    rect_helper = _slice_between(
        CANVAS_JS,
        "function paintRegionRect(x1, y1, x2, y2, value) {",
        "canvas.onmousemove = function (e) {",
    )

    assert "const useScopedRefinement = _zoneBrushUsesScopedRefinement(zone);" in brush_helper
    assert "_buildZoneScopedSelectorMask(zone, w, h)" in brush_helper
    assert "const touched = _paintScopedSpatialCircle(zone, scopeMask, w, h, x, y, radius, spatialValue);" in brush_helper
    assert "if (value) _maybeAdoptForegroundAsScopedZoneBaseColor(selectedZoneIndex);" in brush_helper
    assert "else _normalizeScopedZoneAutoBaseColor(selectedZoneIndex);" in brush_helper
    assert "return 'spatial';" in brush_helper

    assert "const useScopedRefinement = _zoneBrushUsesScopedRefinement(zone);" in fill_helper
    assert "showToast('Click inside this zone’s current color/layer selection'" in fill_helper
    assert "zone.spatialMask[idx] = fillVal;" in fill_helper
    assert "const fillVal = (selMode === 'subtract') ? 2 : 1;" in fill_helper
    assert "let filledScoped = 0;" in fill_helper
    assert "if (fillVal === 1 && filledScoped > 0) _maybeAdoptForegroundAsScopedZoneBaseColor(selectedZoneIndex);" in fill_helper
    invalid_scope_branch = _slice_between(
        fill_helper,
        "showToast('Click inside this zone’s current color/layer selection'",
        "if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);",
    )
    assert "return false;" in invalid_scope_branch
    assert fill_helper.index("return false;") < fill_helper.index(
        "if (typeof pushUndo === 'function') pushUndo(selectedZoneIndex);"
    )
    assert "return filledScoped > 0;" in fill_helper
    assert "return true;" in fill_helper
    assert "window.paintRegionRect = paintRegionRect;" in rect_helper


def test_zone_indicator_copy_explains_scoped_refinement():
    indicator = _slice_between(
        CANVAS_JS,
        "function updateDrawZoneIndicator() {",
        "// ===== BRUSH CURSOR CIRCLE - visible radius indicator =====",
    )
    assert "paint to KEEP this zone only inside its current color/layer selection" in indicator
    assert "typeof window._zoneBrushUsesScopedRefinement === 'function'" in indicator
    assert "bucket only inside this zone’s current color/layer selection" in indicator
    assert "this paints raw layer pixels across the layer — switch to ZONE to stay inside the current zone selector" in indicator


def test_scoped_zone_exact_color_repaints_skip_hidden_blend_overlays():
    preview_payload = _slice_between(
        CANVAS_JS,
        "if (z.wear && z.wear > 0) zoneObj.wear_level = z.wear;",
        "const hasSpatialRefinement = z.spatialMask && z.spatialMask.some(v => v > 0);",
    )

    assert "function _zoneShouldPreserveScopedBrushExactColor(zone)" in CANVAS_JS
    assert "function _zoneHasActiveBaseOverlayClient(zone)" in CANVAS_JS
    assert "if (_zoneHasActiveBaseOverlayClient(zone)) return false;" in CANVAS_JS
    assert "window._zoneShouldPreserveScopedBrushExactColor = _zoneShouldPreserveScopedBrushExactColor;" in CANVAS_JS
    assert "function _zoneShouldPreserveScopedBrushExactColorPayload(z) {" in API_JS
    assert "window._zoneShouldPreserveScopedBrushExactColor === 'function'" in API_JS
    assert "if (_zoneHasActiveBaseOverlay(z)) return false;" in API_JS
    assert "Array.isArray(z.spatialMask) &&" in API_JS
    assert "function _applyBlendBaseOverlay(zoneObj, z) {" in API_JS
    assert "if (_zoneShouldPreserveScopedBrushExactColorPayload(z)) return;" in API_JS
    assert "_applyBlendBaseOverlay(zoneObj, z);" in API_JS
    assert "const suppressScopedExactColorOverlays = _zoneShouldPreserveScopedBrushExactColor(z);" in preview_payload
    assert "if (!suppressScopedExactColorOverlays && z.blendBase" in preview_payload
    assert "if (!suppressScopedExactColorOverlays && z.secondBaseEnabled !== false && (z.secondBase || z.secondBaseColorSource)" in preview_payload


def test_brush_drag_uses_fast_arc_preview_for_spatial_zone_paths():
    assert "function _fastSpatialOverlayArc(cx, cy, radius, value) {" in CANVAS_JS
    move_branch = _slice_between(
        CANVAS_JS,
        "} else if ((canvasMode === 'brush' || canvasMode === 'erase') && isDrawing) {",
        "} else if (canvasMode === 'lasso' && isDrawing && lassoMouseDownPos) {",
    )

    assert "if (strokeTarget === 'spatial') _fastSpatialOverlayArc(pos.x, pos.y, _bRadius, val);" in move_branch
    assert "else _fastOverlayArc(pos.x, pos.y, _bRadius, val);" in move_branch
    assert "paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);" in move_branch
    assert "_fastSpatialOverlayArc(pos.x, pos.y, spatialBrushRadius, val);" in move_branch
    assert "paintSpatialCircle(pos.x, pos.y, spatialBrushRadius, val);\n                    renderRegionOverlay();" not in move_branch


def test_scoped_zone_priority_override_is_plumbed_from_toolbar_to_engine():
    assert "function _zoneShouldRequestPriorityOverride(zone)" in CANVAS_JS
    assert "if (_zoneShouldRequestPriorityOverride(z)) zoneObj.priority_override = true;" in CANVAS_JS
    assert "window._zoneShouldRequestPriorityOverride === 'function'" in API_JS
    assert "if (shouldPriorityOverride) zoneObj.priority_override = true;" in API_JS
    assert 'zone_obj["priority_override"] = bool(z.get("priority_override"))' in SERVER_PY
    assert "priority_override_masks = [None] * len(zone_masks)" in ENGINE_PY
    assert "future_priority_override = [None] * len(zone_masks)" in ENGINE_PY


def test_zone_mask_undo_tracks_auto_scoped_base_color_changes():
    undo_helper = _slice_between(
        CANVAS_JS,
        "function pushUndo(zoneIndex) {",
        "// Unified pixel undo stack (for ALL paint/pixel tools)",
    )
    undo_draw = _slice_between(
        CANVAS_JS,
        "function undoDrawStroke() {",
        "function redoDrawStroke() {",
    )
    redo_draw = _slice_between(
        CANVAS_JS,
        "function redoDrawStroke() {",
        "// ===== MAGIC WAND / FLOOD FILL =====",
    )

    assert "prevBaseColorMode: zone.baseColorMode" in undo_helper
    assert "prevScopedBrushAutoBaseColor: zone._scopedBrushAutoBaseColor" in undo_helper
    assert "zone.baseColorMode = entry.prevBaseColorMode;" in undo_draw
    assert "zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;" in undo_draw
    assert "zone.baseColorMode = entry.prevBaseColorMode;" in redo_draw
    assert "zone._scopedBrushAutoBaseColor = entry.prevScopedBrushAutoBaseColor;" in redo_draw


def test_unified_undo_routes_by_recorded_action_order_instead_of_stack_priority():
    undo_draw = _slice_between(
        CANVAS_JS,
        "function undoDrawStroke() {",
        "function redoDrawStroke() {",
    )
    redo_draw = _slice_between(
        CANVAS_JS,
        "function redoDrawStroke() {",
        "// ===== MAGIC WAND / FLOOD FILL =====",
    )

    assert "var _undoActionTrail = [];" in CANVAS_JS
    assert "var _redoActionTrail = [];" in CANVAS_JS
    assert "function _popLatestTrackedUndoKind()" in CANVAS_JS
    assert "function _popLatestTrackedRedoKind()" in CANVAS_JS
    assert "_recordUndoAction('zone-mask');" in CANVAS_JS
    assert "_recordUndoAction('pixel');" in CANVAS_JS
    assert "_recordUndoAction('layer');" in CANVAS_JS
    assert "_recordUndoAction('decal');" in UI_BOOT_JS
    assert "window._recordUndoAction('zone-config');" in STATE_JS
    assert "if (zoneUndoStack.length === 0) { showToast('Nothing to undo — no zone changes recorded yet'); return false; }" in STATE_JS
    assert "if (zoneRedoStack.length === 0) { showToast('Nothing to redo — make a change and undo it first'); return false; }" in STATE_JS
    assert "showToast('Undo: ' + entry.label);\n    return true;" in STATE_JS
    assert "showToast('Redo: ' + entry.label);\n    return true;" in STATE_JS

    assert "const trackedKind = _popLatestTrackedUndoKind();" in undo_draw
    assert "const trackedKind = _popLatestTrackedRedoKind();" in redo_draw
    assert "if (trackedKind === 'pixel')" in undo_draw
    assert "if (trackedKind === 'decal')" in undo_draw
    assert "if (trackedKind === 'zone-mask')" in undo_draw
    assert "if (trackedKind === 'pixel')" in redo_draw
    assert "if (trackedKind === 'decal')" in redo_draw
    assert "if (trackedKind === 'zone-mask')" in redo_draw
    assert "_layerUndoStack.length > 0" not in undo_draw.split("const trackedKind = _popLatestTrackedUndoKind();", 1)[0]
    assert "_pixelUndoStack.length > 0" not in undo_draw.split("const trackedKind = _popLatestTrackedUndoKind();", 1)[0]


def test_zone_mask_undo_redraw_does_not_reference_stale_pointer_event_state():
    undo_draw = _slice_between(
        CANVAS_JS,
        "function undoDrawStroke() {",
        "function redoDrawStroke() {",
    )
    zone_mask_branch = _slice_between(
        undo_draw,
        "if (trackedKind === 'zone-mask') {",
        "// Legacy single-snapshot undo",
    )

    assert "renderRegionOverlay();" in zone_mask_branch
    assert "_fastSpatialOverlayArc(pos.x, pos.y, spatialBrushRadius, val);" not in zone_mask_branch
    assert "pos.x" not in zone_mask_branch
    assert "spatialBrushRadius" not in zone_mask_branch
    assert "val);" not in zone_mask_branch


def test_redo_shortcut_truth_is_visible_where_undo_redo_is_taught():
    wiki = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")
    global_undo = _slice_between(
        STATE_JS,
        "// Keyboard shortcuts: Ctrl+Z = undo, Ctrl+Y / Ctrl+Shift+Z = redo",
        "// Zone colors for region overlay visualization",
    )

    assert "const undoRedoKey = typeof e.key === 'string' ? e.key.toLowerCase() : '';" in global_undo
    assert "undoRedoKey === 'z' && !e.shiftKey" in global_undo
    assert "(undoRedoKey === 'y' || (undoRedoKey === 'z' && e.shiftKey))" in global_undo
    assert "Redo (Ctrl+Y / Ctrl+Shift+Z)" in HTML
    assert "Undo History (Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z)" in HTML
    assert "Redo last undone action (Ctrl+Y / Ctrl+Shift+Z)" in HTML
    assert "Redo zone change (Ctrl+Y / Ctrl+Shift+Z)" in HTML
    assert "Ctrl+Y</kbd> / <kbd" in HTML
    assert "Ctrl+Shift+Z</kbd> Redo" in HTML
    assert "if (rb) rb.title = window.getRedoLabel() + ' (Ctrl+Y / Ctrl+Shift+Z)';" in CANVAS_JS
    assert "if (rb) rb.title = window.getRedoLabel() + ' (Ctrl+Shift+Z)';" not in CANVAS_JS
    assert "{l:'Redo',k:'Ctrl+Y / Ctrl+Shift+Z',fn:'redoDrawStroke'}" in CANVAS_JS
    assert "{l:'Redo',k:'Ctrl+Y',fn:'redoDrawStroke'}" not in CANVAS_JS
    assert "<kbd>Ctrl</kbd> + <kbd>Z</kbd> / <kbd>Ctrl</kbd> + <kbd>Y</kbd> / <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Z</kbd>" in wiki
    assert "the running app accepts both <kbd>Ctrl</kbd> + <kbd>Y</kbd> and <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Z</kbd> for redo" in wiki


def test_zone_mask_redo_reseeds_undo_stack():
    helper = _slice_between(
        CANVAS_JS,
        "function pushZoneMaskUndoSnapshotForRedo(zoneIndex) {",
        "// Unified pixel undo stack",
    )
    redo_body = _slice_between(
        CANVAS_JS,
        "function redoDrawStroke() {",
        "// ===== MAGIC WAND / FLOOD FILL =====",
    )

    assert "undoStack.push({" in helper
    assert "_clearAllRedos()" not in helper
    assert "if (undoStack.length > MAX_UNDO) undoStack.shift();" in helper
    assert redo_body.count("pushZoneMaskUndoSnapshotForRedo(entry.zoneIndex);") >= 2


def test_layer_brush_live_composite_refresh_is_raf_batched_per_frame():
    paint_helper = _slice_between(
        CANVAS_JS,
        "function _paintOnLayerAt(x, y, radius, color, opacity, hardness, eraseMode) {",
        "// Workstream 6 #119",
    )
    commit_helper = _slice_between(
        CANVAS_JS,
        "function _commitLayerPaint() {",
        "function _cancelLayerPaintStroke() {",
    )

    assert "var _activeLayerCompositePreviewRaf = 0;" in CANVAS_JS
    assert "function _refreshActiveLayerCompositePreviewNow() {" in CANVAS_JS
    assert "function _scheduleActiveLayerCompositePreview(dirty) {" in CANVAS_JS
    assert "function _cancelPendingActiveLayerCompositePreview() {" in CANVAS_JS
    assert "_scheduleActiveLayerCompositePreview();" in paint_helper
    assert "_cancelPendingActiveLayerCompositePreview();" in commit_helper
    assert "paintImageData = pctx.getImageData(0, 0, pc.width, pc.height);" not in paint_helper


def test_layer_special_picker_lazy_loads_popup_swatches_instead_of_eager_fetching_everything():
    square_helper = _slice_between(
        STATE_JS,
        "function renderSwatchSquare(finishId, fallbackColor, title, colorHex) {",
        "function renderSwatchDot(finishId, fallbackColor, colorHex) {",
    )
    open_picker = _slice_between(
        STATE_JS,
        "function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {",
        "function closeSwatchPicker() {",
    )
    filter_picker = _slice_between(
        STATE_JS,
        "function filterSwatchPopup(query) {",
        "function selectSwatchItem(id) {",
    )
    close_picker = _slice_between(
        STATE_JS,
        "function closeSwatchPicker() {",
        "// ----- Swatch Preview Modal: see exactly what a finish does on your paint -----",
    )

    assert "function _installSwatchPopupLazyLoader()" in STATE_JS
    assert "function _hydrateDeferredSwatchImage(img)" in STATE_JS
    assert 'data-swatch-url="${url}"' in square_helper
    assert "loading=\"eager\"" not in square_helper
    assert "_installSwatchPopupLazyLoader();" in open_picker
    assert "_installSwatchPopupLazyLoader();" in filter_picker
    assert "_disconnectSwatchPopupLazyLoader();" in close_picker


def test_special_finish_surfaces_no_longer_render_ungrouped_other_buckets():
    assert 'No ungrouped monolithic "Other" bucket in Alpha UX.' in STATE_JS
    assert 'const ungrouped = MONOLITHICS.filter(m => !groupedIds.has(m.id));' not in STATE_JS
    assert 'Legacy / Unsorted' not in STATE_JS
    assert "if (ungrouped.length > 0 && activeLibraryTab !== 'patterns' && activeLibraryTab !== 'specials') {" in STATE_JS


def test_finish_browser_monolithics_are_limited_to_grouped_shipping_specials():
    assert "const monolithicIdSet = new Set(MONOLITHICS.map(m => m.id));" in UI_BOOT_JS
    assert "function _fbGroupedMonoIds() {" in UI_BOOT_JS
    assert "const grouped = new Set();" in UI_BOOT_JS
    assert "return grouped;" in UI_BOOT_JS
    assert "const groupedSpecialMonoIds = _fbGroupedMonoIds();" in UI_BOOT_JS
    assert "if (groupedSpecialMonoIds.size && !groupedSpecialMonoIds.has(m.id)) continue;" in UI_BOOT_JS


def test_top_changelog_entry_reads_as_closed_run_metadata():
    top_entry = CHANGELOG.split("\n---\n\n### 2026-04-22", 1)[0]
    assert "run still in progress" not in top_entry
    assert "8 iterations completed at time of writing" not in top_entry
    assert "9 of 12 real Family members used in lane-appropriate work so far" not in top_entry
    assert "Trust-restoring fixes landed (4 real bugs)" in top_entry


def test_startup_restore_prefers_canonical_source_file_over_display_path():
    auto_restore = _slice_between(
        STATE_JS,
        "function autoRestore() {",
        "// ===== ZONE VALIDATION BEFORE RENDER =====",
    )
    candidate_helper = _slice_between(
        STATE_JS,
        "function _spbGetPreferredRestoreCandidates(cfg) {",
        "function _spbGetPreferredRestorePaintFile(cfg) {",
    )
    resolve_helper = _slice_between(
        STATE_JS,
        "async function _spbResolveRestorePaintFile(cfg) {",
        "function _spbSetPaintHeaderPath(path) {",
    )
    restore_helper = _slice_between(
        STATE_JS,
        "function _spbRestorePaintFile(path) {",
        "// Smart auto-loader:",
    )

    assert "sourcePaintFile: canonicalSourcePaintFile," in STATE_JS
    assert "function _spbGetPreferredRestorePaintFile(cfg) {" in STATE_JS
    assert "return _spbUniqueNonEmpty([cfgSource, storedLastFile, uiPaintFile]);" in candidate_helper
    assert "if (await _spbCheckLocalPaintFile(candidate)) return candidate;" in resolve_helper
    assert "console.warn('[autoRestore] saved paint file missing, trying fallback:', candidate);" in resolve_helper
    assert "if (assets.starter_psd && await _spbCheckLocalPaintFile(assets.starter_psd))" in resolve_helper
    assert "return assets.starter_psd || candidates[0] || '';" in resolve_helper
    assert "function _spbRestorePaintFile(path) {" in STATE_JS
    assert "_spbSetPaintHeaderPath(normalizedPath);" in restore_helper
    assert "const ok = _spbAutoLoadPaintFile(normalizedPath);" in restore_helper
    assert "localStorage.setItem(SPB_LAST_FILE_KEY, normalizedPath);" in restore_helper
    assert "_spbRestorePreferredPaintFile(null, { firstRun: true });" in auto_restore
    assert "_spbRestorePreferredPaintFile(cfg);" in auto_restore
    assert "localStorage.setItem(SPB_LAST_FILE_KEY, savedPath);" not in auto_restore


def test_plain_paint_loads_clear_active_psd_source_marker_only_after_success():
    decoded_loader = _slice_between(
        DATA_JS,
        "function loadDecodedImageToCanvas(width, height, rgbaData, fileName, options) {",
        "// =============================================================================",
    )
    psd_import = _slice_between(
        CANVAS_JS,
        "async function _doPSDImport(psdPath) {",
        "function countLayers(layers)",
    )
    tga_loader = _slice_between(
        CANVAS_JS,
        "async function loadPaintPreviewFromServer(tgaPath) {",
        "window.loadPaintPreviewFromServer = loadPaintPreviewFromServer;",
    )
    file_loader = _slice_between(
        CANVAS_JS,
        "function loadPaintImageFromFile(file) {",
        "window.markFlatPaintLiveSource = markFlatPaintLiveSource;",
    )

    assert "function getCurrentSourcePaintFile() {" in CANVAS_JS
    assert "window.getCurrentSourcePaintFile = getCurrentSourcePaintFile;" in CANVAS_JS
    assert "function clearPSDDocumentState(reason, options) {" in CANVAS_JS
    assert "window.clearPSDDocumentState = clearPSDDocumentState;" in CANVAS_JS
    assert "_psdLayers = [];" in CANVAS_JS
    assert "_psdLayersLoaded = false;" in CANVAS_JS
    assert "if (z && z.sourceLayer) z.sourceLayer = null;" in CANVAS_JS
    assert "const opts = options || {};" in decoded_loader
    assert "if (opts.clearPSD !== false && typeof clearPSDDocumentState === 'function')" in decoded_loader
    assert "clearPSDDocumentState('load decoded flat paint image', { clearZoneSourceLayers: true });" in decoded_loader
    assert "clearPSDDocumentState('load TGA preview', { clearZoneSourceLayers: true });" in tga_loader
    assert "clearPSDDocumentState('load TGA file', { clearZoneSourceLayers: true });" in file_loader
    assert "clearPSDDocumentState('load flat image file', { clearZoneSourceLayers: true });" in file_loader
    assert "clearPSDDocumentState('set source paint file', { clearZoneSourceLayers: true });" in CANVAS_JS
    assert "_spbCaptureSourceDocumentState()" in psd_import
    assert "_spbRestoreSourceDocumentState(previous)" in psd_import
    assert "loadDecodedImageToCanvas" not in psd_import


def test_shokk_programmatic_paint_loader_waits_until_canvas_is_ready():
    path_loader = _slice_between(
        CANVAS_JS,
        "function loadPaintImageFromPath(urlOrPath) {",
        "function loadPaintImageFromFile(file) {",
    )
    ready_loader = _slice_between(
        CANVAS_JS,
        "function loadPaintImageFromFileAsync(file) {",
        "window.markFlatPaintLiveSource = markFlatPaintLiveSource;",
    )
    shokk_open = _slice_between(
        SHOKK_JS,
        "async function loadShokkFile(shokkPath, mode = 'full') {",
        "/** Update the main canvas area",
    )

    assert "return loadPaintImageFromFileAsync(file);" in path_loader
    assert "return new Promise(function (resolve, reject)" in ready_loader
    assert "loadDecodedImageToCanvas(tga.width, tga.height, tga.rgba, fileName);" in ready_loader
    assert "finishLoad(tga.width, tga.height);" in ready_loader
    assert "finishLoad(img.width, img.height);" in ready_loader
    assert "reader.onerror = function ()" in ready_loader
    assert "img.onerror = function ()" in ready_loader
    assert "window.loadPaintImageFromFile = loadPaintImageFromFileAsync;" in ready_loader
    assert "await loadPaintImageFromPath(paintUrl);" in shokk_open


def test_adjustment_slider_zero_values_are_not_replaced_by_defaults():
    adjustment_block = _slice_between(
        CANVAS_JS,
        "function applyVignette(strength) {",
        "function toggleLayerVisible(layerId) {",
    )

    assert "const t = Math.max(0, Math.min(255, level ?? 128));" in adjustment_block
    assert "const t = Math.max(0, Math.min(255, level || 128));" not in adjustment_block
    assert "const a = Math.max(-100, Math.min(100, amount ?? 25));" in adjustment_block
    assert "const a = Math.max(-100, Math.min(100, amount || 25));" not in adjustment_block
    assert "if (vals && !isNaN(vals[0])) applyThreshold(vals[0]);" in adjustment_block
    assert "if (vals && !isNaN(vals[0])) adjustVibrance(vals[0]);" in adjustment_block


def test_exact_match_picker_tolerance_survives_live_eyedropper_and_script_paths():
    script_color_formatter = _slice_between(
        CANVAS_JS,
        "function formatColorForPython(color, zone) {",
        "function _zoneHasRenderableMaterialClient(z) {",
    )
    eyedropper_assigners = _slice_between(
        CANVAS_JS,
        "function quickAssignAll() {",
        "// ===== USE REGION - commit drawn region",
    )
    zone_coverage = _slice_between(
        STATE_JS,
        "function zoneCoverageEstimate(index) {",
        "if (typeof window !== 'undefined') { window.zoneCoverageEstimate = zoneCoverageEstimate; }",
    )
    hue_duplicate = _slice_between(
        STATE_JS,
        "function duplicateZoneWithHueOffset(index, hueShiftDeg) {",
        "if (typeof window !== 'undefined') { window.duplicateZoneWithHueOffset = duplicateZoneWithHueOffset; }",
    )

    assert "c.tolerance ?? 40" in script_color_formatter
    assert "color.tolerance ?? 40" in script_color_formatter
    assert "c.tolerance || 40" not in script_color_formatter
    assert "color.tolerance || 40" not in script_color_formatter

    assert "const tol = zone.pickerTolerance ?? 40;" in eyedropper_assigners
    assert "const tol = zones[targetIndex].pickerTolerance ?? 40;" in eyedropper_assigners
    assert "tolerance: zone.pickerTolerance ?? 40" in eyedropper_assigners
    assert "zone.pickerTolerance || 40" not in eyedropper_assigners
    assert "zones[targetIndex].pickerTolerance || 40" not in eyedropper_assigners

    assert "const tol = tc.tolerance ?? 40;" in zone_coverage
    assert "const tol = tc.tolerance || 40;" not in zone_coverage
    assert "tolerance: clone.color.tolerance ?? 40" in hue_duplicate
    assert "tolerance: c.tolerance ?? 40" in hue_duplicate
    assert "tolerance: clone.color.tolerance || 40" not in hue_duplicate
    assert "tolerance: c.tolerance || 40" not in hue_duplicate


def test_zone_tolerance_ui_exposes_real_exact_match_control():
    multi_color_ui = _slice_between(
        STATE_JS,
        "function renderMultiColorChips(zone, zoneIndex) {",
        "function addColorToZoneFromPicker(zoneIndex) {",
    )
    zone_detail_ui = _slice_between(
        STATE_JS,
        "        <div class=\"color-tol-row\"",
        "        ${renderMultiColorChips(zone, i)}",
    )
    preset_helper = _slice_between(
        STATE_JS,
        "function setTolerancePreset(index, preset) {",
        "if (typeof window !== 'undefined') { window.setTolerancePreset = setTolerancePreset; }",
    )

    assert 'type="range" min="0" max="100" value="${c.tolerance ?? 40}"' in multi_color_ui
    assert "c.tolerance || 40" not in multi_color_ui
    assert 'class="tolerance-slider" type="range" min="0" max="100" value="${zone.pickerTolerance ?? 40}"' in zone_detail_ui
    assert "setTolerancePreset(${i},'exact')" in zone_detail_ui
    assert "Exact: ±0" in zone_detail_ui
    assert "Tight: ±5 — near-exact color match" in zone_detail_ui
    assert "Tight: ±5 — exact color match" not in zone_detail_ui
    assert "const map = { exact: 0, tight: 5, default: 40, loose: 80 };" in preset_helper
    assert "Object.prototype.hasOwnProperty.call(map, preset)" in preset_helper
    assert "const tol = map[preset]; if (!tol) return;" not in preset_helper


def test_fleet_and_season_modes_are_retired_in_this_booth_build():
    fleet_toggle = _slice_between(
        API_JS,
        "function toggleFleetMode() {",
        "function addFleetCar() {",
    )
    fleet_render = _slice_between(
        API_JS,
        "async function doFleetRender() {",
        "// ===== SEASON MODE =====",
    )
    season_toggle = _slice_between(
        API_JS,
        "function toggleSeasonMode() {",
        "function addSeasonRace() {",
    )

    assert "function _showRetiredBatchModeToast(modeLabel) {" in API_JS
    assert "fleetModeActive = false;" in fleet_toggle
    assert "panel.style.display = 'none';" in fleet_toggle
    assert "_showRetiredBatchModeToast('Fleet mode');" in fleet_toggle
    assert "return false;" in fleet_toggle
    assert "_showRetiredBatchModeToast('Fleet mode');" in fleet_render
    assert "return;" in fleet_render.split("_showRetiredBatchModeToast('Fleet mode');", 1)[1]

    assert "seasonModeActive = false;" in season_toggle
    assert "panel.style.display = 'none';" in season_toggle
    assert "_showRetiredBatchModeToast('Season mode');" in season_toggle
    assert "return false;" in season_toggle
    assert "async function doSeasonRender() {\n    _showRetiredBatchModeToast('Season mode');\n    return;" in API_JS


def test_main_render_no_longer_threads_helmet_or_suit_extras():
    render_api = _slice_between(
        API_JS,
        "async render(paintFile, zones, iracingId, seed, liveLink, extras) {",
        "this.resetStatusInterval(); // Reset polling backoff on every render",
    )
    do_render = _slice_between(
        API_JS,
        "async function doRender() {",
        "    // Import spec map (merge mode)",
    )
    render_result = _slice_between(
        API_JS,
        "    // Helmet + Suit previews are retired in this booth build.",
        "    // Night spec preview",
    )

    assert "body.helmet_paint_file" not in render_api
    assert "body.suit_paint_file" not in render_api
    assert "const helmetFile = document.getElementById('helmetFile')" not in do_render
    assert "const suitFile = document.getElementById('suitFile')" not in do_render
    assert "helmetImg.removeAttribute('src');" in render_result
    assert "suitImg.removeAttribute('src');" in render_result
    assert "helmetSuitRow.style.display = 'none';" in render_result


def test_main_render_threads_spec_stamp_payload_to_server():
    render_api = _slice_between(
        API_JS,
        "async render(paintFile, zones, iracingId, seed, liveLink, extras) {",
        "this.resetStatusInterval(); // Reset polling backoff on every render",
    )
    stamp_builder = _slice_between(
        API_JS,
        "    // Spec Stamps: composite stamp images and send to server",
        "    // [IMP-27] Pre-render validation",
    )

    assert "extras.stamp_image_base64 = await canvasToBase64Async(stampCanvas);" in stamp_builder
    assert "extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';" in stamp_builder
    assert "if (extras.stamp_image_base64) body.stamp_image_base64 = extras.stamp_image_base64;" in render_api
    assert "if (extras.stamp_spec_finish) body.stamp_spec_finish = extras.stamp_spec_finish;" in render_api
    assert 'stamp_image_base64 = data.get("stamp_image_base64")' in SERVER_PY
    assert 'stamp_spec_finish = data.get("stamp_spec_finish", "gloss")' in SERVER_PY
    assert "stamp_image=stamp_image_path," in SERVER_PY
    assert "if stamp_image and os.path.exists(stamp_image):" in ENGINE_PY


def test_photoshop_export_threads_decal_and_stamp_spec_payload_to_server():
    export_api = _slice_between(
        API_JS,
        "async exportToPhotoshop(carFileName, exchangeFolder, paintFile, zones, extras) {",
        "try { // [5] try/catch around fetch",
    )
    export_builder = _slice_between(
        API_JS,
        "    // Spec Stamps for PS export",
        "    // Match Full Render: Change File/browser-selected flat images are live",
    )
    export_server = _slice_between(
        SERVER_PHOTOSHOP_EXPORT_PY,
        "@app.route('/api/export-to-photoshop', methods=['POST'])",
        "            # Generate channel TGAs in job_dir",
    )

    assert "extras.stamp_image_base64 = await canvasToBase64Async(stampCanvas);" in export_builder
    assert "extras.stamp_spec_finish = window.stampSpecFinish || 'gloss';" in export_builder
    assert "if (extras.decal_mask_base64) body.decal_mask_base64 = extras.decal_mask_base64;" in export_api
    assert "if (extras.decal_spec_finishes && extras.decal_spec_finishes.length) body.decal_spec_finishes = extras.decal_spec_finishes;" in export_api
    assert "if (extras.stamp_image_base64) body.stamp_image_base64 = extras.stamp_image_base64;" in export_api
    assert "if (extras.stamp_spec_finish) body.stamp_spec_finish = extras.stamp_spec_finish;" in export_api
    assert 'stamp_image_base64 = data.get("stamp_image_base64")' in export_server
    assert 'decal_spec_finishes = data.get("decal_spec_finishes", [])' in export_server
    assert 'decal_mask_base64 = data.get("decal_mask_base64")' in export_server
    assert "stamp_image=stamp_image_path," in export_server
    assert "decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None," in export_server
    assert "decal_paint_path=decal_paint_path," in export_server
    assert "decal_mask_base64=decal_mask_base64," in export_server


def test_render_results_labels_follow_actual_download_filenames():
    render_panel = _slice_between(
        HTML,
        '<section id="renderResultsPanel"',
        '<!-- One-Click Deploy to iRacing -->',
    )
    render_result = _slice_between(
        API_JS,
        "function showRenderResults(result) {",
        "    const cacheBust = '?v=' + (window.APP_SESSION_ID || Date.now());",
    )

    assert 'id="renderPaintPreviewLabel"' in render_panel
    assert 'id="renderSpecPreviewLabel"' in render_panel
    assert "PAINT (car_num)" not in render_panel

    assert "const downloadKeys = Object.keys(result.download_urls || {});" in render_result
    assert "const paintDownloadKey = downloadKeys.find(k => /^car_num_\\d+$/.test(k))" in render_result
    assert "|| downloadKeys.find(k => /^car_\\d+$/.test(k));" in render_result
    assert "const specDownloadKey = downloadKeys.find(k => /^car_spec_\\d+$/.test(k));" in render_result
    assert "paintLabel.textContent = paintDownloadKey ? `PAINT (${paintDownloadKey}.tga)` : 'PAINT';" in render_result
    assert "specLabel.textContent = specDownloadKey ? `SPEC MAP (${specDownloadKey}.tga)` : 'SPEC MAP';" in render_result


def test_render_results_escape_output_and_live_link_dynamic_html():
    escape_helper = _slice_between(
        API_JS,
        "function _spbEscapeRenderHtml(value) {",
        "// BOIL THE OCEAN deep core:",
    )
    render_status = _slice_between(
        API_JS,
        "// Output directory + live link combined status",
        "    panel.style.display = 'block';",
    )

    assert ".replace(/&/g, '&amp;')" in escape_helper
    assert ".replace(/</g, '&lt;')" in escape_helper
    assert ".replace(/>/g, '&gt;')" in escape_helper
    assert ".replace(/\"/g, '&quot;')" in escape_helper
    assert ".replace(/'/g, '&#39;')" in escape_helper
    assert "${_spbEscapeRenderHtml(result.output_dir.path)}" in render_status
    assert "${_spbEscapeRenderHtml(result.output_dir.error)}" in render_status
    assert "${_spbEscapeRenderHtml(livePath)}" in render_status
    assert "${_spbEscapeRenderHtml(result.live_link.error)}" in render_status
    assert "${result.output_dir.path}" not in render_status
    assert "${result.output_dir.error}" not in render_status
    assert "${livePath}" not in render_status
    assert "${result.live_link.error}" not in render_status


def test_photoshop_export_surfaces_distinguish_png_channels_from_tga_round_trip():
    left_panel = _slice_between(
        HTML,
        '<button class="template-btn ps-export-section" onclick="exportSpecChannels(false)"',
        '<!-- Placeholder banner removed for Alpha release -->',
    )
    shokk_library = _slice_between(
        HTML,
        '<button class="btn btn-sm" id="shokkPsExportBtn" onclick="exportSpecChannels(true)"',
        '<div id="shokkLibraryGrid"></div>',
    )
    export_modal = _slice_between(
        HTML,
        '<div class="modal-overlay" id="exportToPhotoshopModal"',
        '<!-- (Import from Photoshop: simplified to one-click spec import, no modal needed) -->',
    )
    channel_exporter = _slice_between(
        (REPO / "paint-booth-7-shokk.js").read_text(encoding="utf-8"),
        "async function exportSpecChannels(fromLibrary) {",
        "// ─── BLANK CANVAS MODE",
    )

    assert "Channel PNG Export" in left_panel
    assert "paint_base.png, spec_full.png" in left_panel
    assert "This is not the TGA round-trip import path." in left_panel

    assert "Channel PNG Export" in shokk_library
    assert "This does not create final iRacing TGAs." in shokk_library
    assert "Select + Channel PNG Export to extract Photoshop inspection PNGs" in shokk_library

    assert "Export to Photoshop (TGA Round Trip)" in export_modal
    assert "named TGA exchange files plus manifest.json" in export_modal
    assert "Use Channel PNG Export when you want separated PNG inspection files instead." in export_modal

    assert "Exporting SHOKK channel PNGs for Photoshop inspection" in channel_exporter
    assert "Exporting channel PNGs for Photoshop inspection" in channel_exporter
    assert "channel PNG files exported" in channel_exporter


def test_generated_script_no_longer_exports_helmet_or_suit_workflow():
    script_generator = _slice_between(
        CANVAS_JS,
        "function generateScript() {",
        "        // ===== SOURCE PAINT FILE BROWSER =====",
    )
    generated_body = _slice_between(
        CANVAS_JS,
        "function generateFullPythonScript(paintFile, outputDir, iracingId, zonesStr, regionMasks, extras) {",
        "        // ===== SOURCE PAINT FILE BROWSER =====",
    )

    forbidden = [
        "HELMET_PAINT",
        "SUIT_PAINT",
        "helmet_paint_file",
        "suit_paint_file",
        "Helmet spec generated",
        "Suit spec generated",
        "scriptExtras.helmetFile",
        "scriptExtras.suitFile",
    ]
    for needle in forbidden:
        assert needle not in script_generator
        assert needle not in generated_body


def test_change_file_live_flat_source_blocks_path_only_script_and_backup_tools():
    script_generator = _slice_between(
        CANVAS_JS,
        "function generateScript() {",
        "function generateFullPythonScript(paintFile, outputDir, iracingId, zonesStr, regionMasks, extras) {",
    )
    backup_helper = _slice_between(
        CANVAS_JS,
        "async function resetSourceBackup() {",
        "function openPaintFilePicker() {",
    )

    assert "const hasLiveFlatSource = !!(typeof window !== 'undefined' && window._spbFlatPaintLiveSource);" in script_generator
    assert "if (hasLiveFlatSource) {" in script_generator
    assert "Python script export needs a real disk TGA Source Paint" in script_generator
    assert script_generator.index("if (hasLiveFlatSource)") < script_generator.index("if (!paintFile)")

    assert "window._spbFlatPaintLiveSource" in backup_helper
    assert "Reset Source Backup needs a real disk Source Paint path" in backup_helper
    assert backup_helper.index("window._spbFlatPaintLiveSource") < backup_helper.index("if (!paintFile)")


def test_decal_spec_finish_changes_refresh_live_preview_contract():
    decal_mutators = _slice_between(
        UI_BOOT_JS,
        "function setDecalScale(idx, val) {",
        "function toggleDecalVisibility(idx) {",
    )

    assert "function setDecalSpecFinish(idx, val) {" in decal_mutators
    assert "decalLayers[idx].specFinish = val || 'none';" in decal_mutators
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in decal_mutators
    assert 'onchange="setDecalSpecFinish(${idx}, this.value)"' in UI_BOOT_JS
    assert 'onchange="decalLayers[${idx}].specFinish = this.value; renderDecalOverlay();"' not in UI_BOOT_JS
    assert "extras.decal_spec_finishes = decalSpecs;" in API_JS


def test_import_logo_receipts_distinguish_layer_vs_legacy_decal_and_refresh_preview():
    add_image_helper = _slice_between(
        UI_BOOT_JS,
        "function addImageToUnifiedLayerStack(options) {",
        "function getDecalBounds(d) {",
    )
    import_decal = _slice_between(
        UI_BOOT_JS,
        "function importDecal() {",
        "function removeDecal(idx) {",
    )
    add_number = _slice_between(
        UI_BOOT_JS,
        "function addNumberDecal() {",
        "/** Hit-test decals:",
    )

    assert "let toastMessage = opts.successToast || '';" in add_image_helper
    assert "toastMessage = opts.layerSuccessToast || ('Added as layer: ' + newLayer.name" in add_image_helper
    assert "toastMessage = opts.legacySuccessToast || toastMessage || ('Added as decal object: '" in add_image_helper
    assert "_pushLayerStackUndo('add imported layer: ' + newLayer.name);" in add_image_helper
    assert add_image_helper.index("_pushLayerStackUndo('add imported layer: ' + newLayer.name);") < add_image_helper.index("_psdLayers.push(newLayer);")

    legacy_branch = _slice_between(
        add_image_helper,
        "} else {",
        "if (toastMessage && typeof showToast === 'function') showToast(toastMessage);",
    )
    assert "decalLayers.push({" in legacy_branch
    assert "renderDecalOverlay();" in legacy_branch
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in legacy_branch

    assert "layerSuccessToast: 'Added as layer: '" in import_decal
    assert "use Move (V) or Transform Layer; use a layer-restricted zone for material." in import_decal
    assert "legacySuccessToast: 'Added as decal object: '" in import_decal
    assert "drag to move, use handles to scale/rotate." in import_decal
    assert "Decal added: " not in import_decal

    assert "layerSuccessToast: 'Number layer added: #'" in add_number
    assert "legacySuccessToast: 'Number decal added: #'" in add_number
    assert 'successToast: \'Number decal "' not in add_number


def test_legacy_decal_object_edits_are_undoable_and_refresh_after_gestures():
    decal_state = _slice_between(
        UI_BOOT_JS,
        "let decalLayers = [];",
        "function getPaintCanvasSize() {",
    )
    decal_mutators = _slice_between(
        UI_BOOT_JS,
        "function removeDecal(idx) {",
        "function renderDecalList() {",
    )
    decal_drag = _slice_between(
        UI_BOOT_JS,
        "function checkDecalDrag(x, y) {",
        "// ===== TEMPLATE LIBRARY",
    )
    undo_helpers = _slice_between(
        CANVAS_JS,
        "function _hasUndoEntriesForKind(kind) {",
        "function pushUndo(zoneIndex) {",
    )
    undo_draw = _slice_between(
        CANVAS_JS,
        "function undoDrawStroke() {",
        "function redoDrawStroke() {",
    )
    redo_draw = _slice_between(
        CANVAS_JS,
        "function redoDrawStroke() {",
        "// ===== MAGIC WAND / FLOOD FILL =====",
    )

    assert "let decalUndoStack = [];" in decal_state
    assert "let decalRedoStack = [];" in decal_state
    assert "function pushDecalUndo(label)" in decal_state
    assert "window.undoDecalEdit = undoDecalEdit;" in decal_state
    assert "window.redoDecalEdit = redoDecalEdit;" in decal_state
    assert "window.hasDecalUndo = function () { return decalUndoStack.length > 0; };" in decal_state
    assert "window.hasDecalRedo = function () { return decalRedoStack.length > 0; };" in decal_state
    assert "case 'decal':" in undo_helpers
    assert "window.clearDecalRedo();" in undo_helpers
    assert "window.undoDecalEdit" in undo_draw
    assert "window.redoDecalEdit" in redo_draw

    for label in [
        "remove decal",
        "flip decal horizontal",
        "flip decal vertical",
        "snap decal to canvas",
        "scale decal",
        "opacity decal",
        "rotate decal",
        "decal spec finish",
        "toggle decal visibility",
    ]:
        assert f"pushDecalUndo('{label}')" in decal_mutators

    assert "pushDecalUndo('add decal object');" in UI_BOOT_JS
    assert "pushDecalUndo('move decal');" in decal_drag
    assert "pushDecalUndo('scale decal');" in decal_drag
    assert "pushDecalUndo('rotate decal');" in decal_drag
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in _slice_between(decal_drag, "function endDecalDrag() {", "function updateDecalScaleFromMouse")
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in _slice_between(decal_drag, "function endDecalScale() {", "function updateDecalRotateFromMouse")
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in _slice_between(UI_BOOT_JS, "function endDecalRotate() {", "// ===== TEMPLATE LIBRARY")


def test_legacy_decal_list_escapes_imported_names_urls_and_finish_options():
    decal_state = _slice_between(
        UI_BOOT_JS,
        "let decalLayers = [];",
        "function snapshotDecalLayers() {",
    )
    decal_list = _slice_between(
        UI_BOOT_JS,
        "function renderDecalList() {",
        "function renderDecalOverlay() {",
    )

    assert "function _spbEscapeDecalHtml(value) {" in decal_state
    assert "if (typeof escapeHtml === 'function') return escapeHtml(value);" in decal_state
    for needle in (
        ".replace(/&/g, '&amp;')",
        ".replace(/</g, '&lt;')",
        ".replace(/>/g, '&gt;')",
        ".replace(/\"/g, '&quot;')",
        ".replace(/'/g, '&#39;')",
    ):
        assert needle in decal_state

    assert "const decalName = _spbEscapeDecalHtml(d.name || 'Decal');" in decal_list
    assert "const decalSrc = _spbEscapeDecalHtml(d.img && d.img.src ? d.img.src : '');" in decal_list
    assert '<img class="decal-thumb" src="${decalSrc}" alt="${decalName}">' in decal_list
    assert '<span class="decal-name" title="${decalName}">${decalName}</span>' in decal_list
    assert "const optionId = _spbEscapeDecalHtml(b.id || '');" in decal_list
    assert "const optionName = _spbEscapeDecalHtml(b.name || b.id || '');" in decal_list
    assert '<option value="${optionId}" ${d.specFinish === b.id ? \'selected\' : \'\'}>${optionName}</option>' in decal_list

    assert 'src="${d.img.src}"' not in decal_list
    assert 'alt="${d.name}"' not in decal_list
    assert 'title="${d.name}">${d.name}' not in decal_list
    assert '<option value="${b.id}" ${d.specFinish === b.id ? \'selected\' : \'\'}>${b.name}</option>' not in decal_list


def test_spec_stamp_import_contract_matches_png_only_loader():
    stamp_panel = _slice_between(
        HTML,
        '<details class="combo-section" id="specStampsSection">',
        '<!-- REMOVED FOR ALPHA',
    )
    stamp_importer = _slice_between(
        UI_BOOT_JS,
        "function importStamp() {",
        "// 2026-04-18 MARATHON bug #20: stamp ops didn't fire preview refresh.",
    )
    wiki = (REPO / "SPB_WIKI.html").read_text(encoding="utf-8")

    assert "Import transparent PNG" in stamp_panel
    assert "Import a transparent PNG." in stamp_panel
    assert "PNG/TGA" not in stamp_panel

    assert "input.accept = '.png,.PNG,image/png';" in stamp_importer
    assert "Spec stamps currently support transparent PNG files only." in stamp_importer
    assert "Import a transparent PNG for spec stamps." in stamp_importer
    assert "Use PNG format for best results." not in stamp_importer
    stamp_onload = _slice_between(
        stamp_importer,
        "img.onload = function() {",
        "img.onerror = function() {",
    )
    assert "renderStampList();" in stamp_onload
    assert "if (typeof triggerPreviewRender === 'function') triggerPreviewRender();" in stamp_onload
    assert "Stamps are full-canvas transparent PNG masks, not movable sponsor decals." in UI_BOOT_JS
    stamp_renderer = _slice_between(
        UI_BOOT_JS,
        "function renderStampList() {",
        "/**\n         * Composite all visible stamps into a single RGBA canvas for server rendering.",
    )
    assert "function _spbEscapeStampHtml(value) {" in UI_BOOT_JS
    assert "var stampName = _spbEscapeStampHtml(s && s.name ? s.name : 'Spec stamp');" in stamp_renderer
    assert " title=\"' + stampName + '\">' + stampName + '</span>'" in stamp_renderer
    assert "' title=\"' + s.name + '\">'" not in stamp_renderer
    assert "+ s.name + '</span>'" not in stamp_renderer

    assert "Re-export a transparent PNG with clean alpha" in wiki
    assert "Re-export a transparent PNG/TGA with clean alpha" not in wiki


def test_base_overlay_react_to_pattern_defaults_to_independent():
    overlay_payload = _slice_between(
        API_JS,
        "function _applyExtraBaseOverlay(zoneObj, z, prefix, key) {",
        "function _applyAllExtraBaseOverlays(zoneObj, z) {",
    )
    overlay_state = _slice_between(
        STATE_JS,
        "function _markZoneBaseOverlayUserEdit(index) {",
        "function setZoneSecondBaseColorSource(index, val) {",
    )
    react_picker = _slice_between(
        STATE_JS,
        "function getOverlayReactToSelectValue(zone, overlayPatternId) {",
        "function openSwatchPicker(triggerEl, type, zoneIndex, layerIndex) {",
    )
    later_overlay_setters = _slice_between(
        STATE_JS,
        "function setZoneThirdBase(index, val) {",
        "function setZoneThirdBaseColorSource(index, val) {",
    ) + _slice_between(
        STATE_JS,
        "function setZoneFourthBase(index, val) {",
        "function setZoneFourthBaseColorSource(index, val) {",
    ) + _slice_between(
        STATE_JS,
        "function setZoneFifthBase(index, val) {",
        "function setZoneFifthBaseColorSource(index, val) {",
    )

    assert "function _normalizeExtraBaseOverlayPatternValue(value)" in API_JS
    assert "const reactPattern = _normalizeExtraBaseOverlayPatternValue(z[prefix + 'Pattern']);" in overlay_payload
    assert "zoneObj[key + '_pattern'] = reactPattern;" in overlay_payload
    assert "function _normalizeOverlayReactPatternValue(val)" in overlay_state
    assert "if (val === '') return '';" in overlay_state
    assert "normalized === '_none_'" in overlay_state
    assert "normalized === 'none_(base_only)'" in overlay_state
    assert "const normalized = _normalizeOverlayReactPatternValue(overlayPatternId);" in react_picker
    assert "if (overlayPatternId === '') return '';" in react_picker
    assert "sel = '__none__'" in STATE_JS
    assert "if (!opts.some(o => o.value === sel)) sel = ''" not in STATE_JS
    assert "_defaultOverlayReactPatternToIndependent(index, 'secondBasePattern');" in overlay_state
    assert "function _autoAttachOverlayPatternForBlend(index, prop, blendMode) {" in overlay_state
    assert "_autoAttachOverlayPatternForBlend(index, 'secondBasePattern', zones[index].secondBaseBlendMode);" in overlay_state
    assert "_defaultOverlayReactPatternToIndependent(index, 'thirdBasePattern');" in later_overlay_setters
    assert "_defaultOverlayReactPatternToIndependent(index, 'fourthBasePattern');" in later_overlay_setters
    assert "_defaultOverlayReactPatternToIndependent(index, 'fifthBasePattern');" in later_overlay_setters
    assert "_autoAttachOverlayPatternForBlend(index, 'thirdBasePattern', zones[index].thirdBaseBlendMode);" in later_overlay_setters
    assert "_autoAttachOverlayPatternForBlend(index, 'fourthBasePattern', zones[index].fourthBaseBlendMode);" in later_overlay_setters
    assert "_autoAttachOverlayPatternForBlend(index, 'fifthBasePattern', zones[index].fifthBaseBlendMode);" in later_overlay_setters
    assert "allocateUnusedPatternForOverlay(zones[index])" not in later_overlay_setters
