"""SPB-93 T45: a Zone color click immediately owns a swatch + tolerance control."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
ZONES = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, name
    depth = 0
    for index in range(match.start(), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return source[match.start() : index + 1]
    raise AssertionError(name)


def test_t45_first_source_click_uses_the_live_zone_stack_transaction():
    assert "typeof setEyedropperColorToZone" not in CANVAS
    assert "setEyedropperColorToZone();" not in CANVAS
    assert "const _pickCommitted = addEyedropperColorToZone()" in CANVAS
    assert "if (_pfc && _pickCommitted !== false) _pfc.picked++" in CANVAS


def test_t45_first_color_is_canonicalized_as_a_real_one_item_swatch_stack():
    add = _function_source(CANVAS, "addEyedropperColorToZone")
    assert "const nextColors = Array.isArray(zone.colors) ? zone.colors.slice() : []" in add
    assert "if (!duplicate) nextColors.push" in add
    assert "zone.colors = nextColors" in add
    assert "zone.colorMode = 'multi'" in add
    assert "zone.color = zone.colors" in add
    assert "renderZones()" in add
    assert "triggerPreviewRender()" in add


def test_t45_legacy_single_color_recovers_controls_without_a_ghost_duplicate():
    add = _function_source(CANVAS, "addEyedropperColorToZone")
    assert "let migratedSingle = false" in add
    assert "zone.colorMode === 'picker' && nextColors.length === 0" in add
    assert "const existTol = zone.color && typeof zone.color === 'object'" in add
    assert "if (duplicate && !migratedSingle)" in add
    assert "pushZoneUndo(duplicate ? 'Restore picked color controls'" in add


def test_t45_one_item_stack_renders_swatch_and_exact_loose_slider():
    chips = _function_source(ZONES, "renderMultiColorChips")
    assert "if (colors.length === 0 && zone.colorMode !== 'multi') return ''" in chips
    assert 'input type="range" min="0" max="100"' in chips
    assert "updateColorTolerance" in chips
    assert "Exact" in chips and "Loose" in chips
    detail = _function_source(ZONES, "renderZoneDetail")
    assert "${renderMultiColorChips(zone, i)}" in detail


def test_t45_live_preview_uses_the_same_armed_zone_commit_route():
    assert "LIVE PREVIEW must honor the same armed/direct Zone" in CANVAS
    assert "const committed = addEyedropperColorToZone()" in CANVAS
    assert "if (pfc && committed !== false) pfc.picked++" in CANVAS


def test_t49_selected_zone_is_the_only_source_and_live_picker_commit_authority():
    assert "const _pickTarget = selectedZoneIndex" in CANVAS
    assert "const targetIndex = selectedZoneIndex" in CANVAS
    assert "? _pfc.zone : selectedZoneIndex" not in CANVAS
    assert "? pfc.zone : selectedZoneIndex" not in CANVAS
    assert "if (_pfc) _pfc.zone = _pickTarget" in CANVAS
    assert "if (pfc) pfc.zone = targetIndex" in CANVAS


def test_t49_zone_switch_rebinds_armed_picker_and_repaints_its_visible_target():
    select = _function_source(ZONES, "selectZone")
    assert "window._spbPickFromCarZone.zone = index" in select
    assert 'visible "Pick colors for" target' in select
    assert "updateDrawZoneIndicator();" in select
    change = _function_source(CANVAS, "onEyedropperZoneChange")
    assert "window._spbPickFromCarZone.zone = newIndex" in change
    assert "updateDrawZoneIndicator();" in change


def test_t45_runtime_is_cache_busted_and_mirrored():
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in HTML
    assert "paint-booth-2-state-zones.js?v=spb93-zone-undo-public-preview-20260809b" in HTML
    assert "js/zones/zone-list-action-controls.js?v=spb93-zone-picker-target-20260808a" in HTML
    assert (ROOT / "electron-app/server/paint-booth-3-canvas.js").read_bytes() == (
        ROOT / "paint-booth-3-canvas.js"
    ).read_bytes()
    assert (ROOT / "electron-app/server/paint-booth-2-state-zones.js").read_bytes() == (
        ROOT / "paint-booth-2-state-zones.js"
    ).read_bytes()
    assert (ROOT / "electron-app/server/js/zones/zone-list-action-controls.js").read_bytes() == (
        ROOT / "js/zones/zone-list-action-controls.js"
    ).read_bytes()
    assert (ROOT / "electron-app/server/paint-booth-v2.html").read_bytes() == (
        ROOT / "paint-booth-v2.html"
    ).read_bytes()
