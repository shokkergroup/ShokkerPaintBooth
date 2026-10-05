from pathlib import Path
import json
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")
CSS = (ROOT / "css" / "spb-easy-mode-20260716.css").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
STATE_JS = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
SCULPT_JS = (ROOT / "js" / "features" / "spb-easy-sculpt.js").read_text(encoding="utf-8")
SCULPT_CSS = (ROOT / "css" / "spb-easy-sculpt.css").read_text(encoding="utf-8")
SWATCH_ROUTES = (ROOT / "server_routes" / "swatch_routes.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def by_color_live_recolor_runtime() -> dict:
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; By Color live-recolor harness requires Node 18+")
    harness = ROOT / "tests" / "_runtime_harness" / "easy_by_color_live_recolor.mjs"
    proc = subprocess.run(
        ["node", str(harness)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.fail(
            "By Color live-recolor runtime harness failed "
            f"(exit {proc.returncode})\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def test_change_color_entry_is_passive_until_the_user_chooses_a_color(
    by_color_live_recolor_runtime: dict,
) -> None:
    passive = by_color_live_recolor_runtime["passiveEntry"]
    assert passive["zone"]["baseColorMode"] is None
    assert passive["zone"]["baseColor"] is None
    assert passive["zone"]["baseColorSource"] is None
    assert passive["repaintRequests"] == 0
    assert passive["liveCanvasHidden"] is False
    assert passive["previewImageHidden"] is True


def test_explicit_replacement_color_repaints_live_without_waiting_for_a_base(
    by_color_live_recolor_runtime: dict,
) -> None:
    chosen = by_color_live_recolor_runtime["explicitChoice"]
    assert chosen["zone"]["base"] is None
    assert chosen["zone"]["finish"] is None
    assert chosen["zone"]["baseColorMode"] == "solid"
    assert chosen["zone"]["baseColor"] == "#33cc88"
    assert chosen["zone"]["_easyPendingColorPreview"] is True
    assert chosen["repaintRequests"] == 1
    assert chosen["liveCanvasHidden"] is True
    assert chosen["previewImageHidden"] is False
    assert chosen["proofSurfaceOn"] is True


def test_pending_recolor_gets_a_neutral_render_anchor_only_until_material_exists(
    by_color_live_recolor_runtime: dict,
) -> None:
    anchor = by_color_live_recolor_runtime["neutralAnchor"]
    assert anchor == {
        "pendingOnly": True,
        "pendingWithBase": False,
        "pendingWithFinish": False,
        "noMarker": False,
    }


def test_pending_preview_marker_cannot_complete_or_leak_past_the_color_flow(
    by_color_live_recolor_runtime: dict,
) -> None:
    assert (
        by_color_live_recolor_runtime["unfinishedSaveReason"]
        == "FINISH OR REMOVE THE UNFINISHED COLOR"
    )

    cleared = by_color_live_recolor_runtime["clearedChoice"]["zone"]
    assert "_easyPendingColorPreview" not in cleared
    assert cleared["baseColorMode"] is None
    assert cleared["baseColor"] is None

    finished = by_color_live_recolor_runtime["finishedChoice"]["zone"]
    assert "_easyPendingColorPreview" not in finished
    assert finished["base"] == "gloss"
    assert finished["finish"] is None


def test_marker_only_recolor_survives_the_canonical_payload_beside_completed_work(
    by_color_live_recolor_runtime: dict,
) -> None:
    payload = by_color_live_recolor_runtime["canonicalPayload"]
    assert len(payload) == 2

    completed, pending = payload
    assert completed["name"] == "Existing completed color"
    assert completed["base"] == "chrome"

    assert pending["name"] == "New pending recolor"
    assert pending["base"] == "gloss"
    assert pending["base_color_mode"] == "solid"
    assert pending["base_color"] == [0.2, 0.4, 0.6]


def test_immediate_finish_kick_cancels_any_queued_color_preview(
    by_color_live_recolor_runtime: dict,
) -> None:
    race = by_color_live_recolor_runtime["immediateKickRace"]
    assert race["queuedCallbackType"] == "function"
    assert race["clearedTimers"] == [race["queuedTimerId"]]
    assert race["timerAfterImmediateKick"] is None
    assert race["immediateKicks"] == 1


def test_by_color_is_color_choice_first_then_finish():
    add_zone = JS[JS.index("function addColorZone"):JS.index("function removeColorZone")]
    assert "bc.phase = 'color'" in add_zone
    assert JS.index("FIRST QUESTION") < JS.index("SECOND QUESTION")
    assert "KEEP MY COLOR" in JS
    assert "CHANGE THE COLOR" in JS
    assert "NEXT: PICK SPEC / FINISH STYLE" in JS


def test_color_power_is_visible_without_pro_mode():
    for contract in (
        "SOLID COLOR",
        "COLOR BY BASE TYPE",
        "spbEasyRecolorHex",
        "spbEasyChooseBaseColor",
        "baseColorChoiceHtml",
        "bc.pickerFor = 'borrow'",
        "spbEasyHue",
        "spbEasySat",
        "spbEasyBrt",
        "spbEasyColorScale",
        "z.baseColorSource = 'base:' + f.id",
    ):
        assert contract in JS
    assert "spbEasyBaseColorSelect" not in JS
    assert "<select id=\"spbEasyBaseColor" not in JS


def test_base_colors_and_spec_finishes_use_real_full_split_thumbnails():
    for contract in (
        "window.getSwatchUrl(info.id, info.swatch || '888888', true, 48)",
        "&size=48&mode=split&prefer=live&v=",
        'data-swatch-contract="paint-left-spec-right"',
        "real Paint Booth preview: paint on the left, spec on the right",
        "REAL PAINT + SPEC THUMBNAIL",
        "Every card below is the real authored thumbnail already used by Paint Booth",
        "These are real Paint Booth paint + spec thumbnails, not made-up color dots",
        "f.type !== 'base'",
    ):
        assert contract in JS
    assert "object-fit: contain" in CSS
    assert "complete 96x48 authored PAINT | SPEC tile, never cropped" in CSS
    assert "object-position: left center" not in CSS


def test_visual_base_library_lazy_loads_and_fails_honestly():
    assert "_lazyContainers" in JS
    assert "lazyThumbPass(container)" in JS
    assert "data-thumb-failed" in JS
    assert "PREVIEW UNAVAILABLE" in JS
    assert "spbEasyBasePickerBack" in JS
    assert 'aria-label="Paint Booth base color thumbnail library"' in JS
    assert "details.addEventListener('toggle'" in JS


def test_sculpt_base_type_picker_is_visual_not_a_blind_select():
    assert "paintBaseOptionsHtml" not in SCULPT_JS
    assert "spbEasySculptBaseColorSelect" not in SCULPT_JS
    assert '<select id="spbEasySculptBaseColor' not in SCULPT_JS
    assert 'data-sculpt-base-id="' in SCULPT_JS
    assert 'aria-label="Paint Booth base color thumbnail library"' in SCULPT_JS
    assert "CHOOSE FROM REAL THUMBNAILS" in SCULPT_JS


def test_sculpt_base_and_finish_cards_use_real_shipping_previews():
    for contract in (
        "/thumbnails/spec_sculpt_presets/",
        "/api/swatch/",
        "mode=split",
        "prefer=live",
        "look.swatchType",
        'data-swatch-contract="paint-left-spec-right"',
        "REAL PAINT + SPEC THUMBNAIL",
        "PREVIEW UNAVAILABLE",
    ):
        assert contract in SCULPT_JS
    assert "look.thumb || (paintAware ? look.paintThumb : '')" in SCULPT_JS
    assert "look.thumb || look.paintThumb" not in SCULPT_JS


def test_sculpt_cards_show_complete_tiles_and_fail_honestly():
    assert "img[data-src]:not([src]):not([data-thumb-failed])" in SCULPT_JS
    assert "data-thumb-failed" in SCULPT_JS
    assert 'onerror="this.remove()"' not in SCULPT_JS
    assert ".spb-easy-sculpt-look-art img" in SCULPT_CSS
    look_image_rule = SCULPT_CSS.split(".spb-easy-sculpt-look-art img", 1)[1].split("}", 1)[0]
    assert "object-fit: contain" in look_image_rule
    assert "object-fit: cover" not in look_image_rule
    assert ".spb-easy-sculpt-base-thumb img" in SCULPT_CSS


def test_real_thumbnails_do_not_hide_synthetic_or_mismatched_work():
    assert "look && !look.thumb && look.kind === 'mode'" in SCULPT_JS
    assert ").slice(0, 3);" in SCULPT_JS
    assert "catalog_type: look.kind === 'catalog'" in SCULPT_JS
    assert "registry_type: look.swatchType || ''" in SCULPT_JS
    assert "real_swatch_render_failed" in SWATCH_ROUTES
    real_failure = SWATCH_ROUTES.index('"error": "real_swatch_render_failed"')
    fake_fallback = SWATCH_ROUTES.index("render_fast_split_swatch_bytes", real_failure)
    assert real_failure < fake_fallback


def test_finish_families_are_collapsed_and_described():
    assert '<details class="spb-easy-finish-section"' in JS
    assert "categoryDescription(sec.title)" in JS
    assert "var open = !!_searchText || ids.some(function (key) { return selectedList.indexOf(key) !== -1; })" in JS
    assert ".spb-easy-finish-section > summary" in CSS


def test_source_live_and_all_spec_channels_are_always_named():
    for element_id in (
        "spbEasySourceCanvas",
        "spbEasyLiveCanvas",
        "spbEasyPreviewImg",
        "spbEasySpecAll",
        "spbEasySpecR",
        "spbEasySpecG",
        "spbEasySpecB",
    ):
        assert element_id in JS
    for label in ("SOURCE", "LIVE PREVIEW", "COMBINED SPEC", "RED · METAL", "GREEN · ROUGH", "BLUE · COAT"):
        assert label in JS


    assert "var wholeProof" in JS and "var proofMode = byColor || wholeProof" in JS
    assert "classList.toggle('spb-easy-proof-on', proofMode)" in JS
    assert "if (proofMode) syncSpecProof();" in JS


def test_whole_car_first_finish_immediately_promotes_the_full_proof_surface():
    apply_whole = JS[JS.index("function applyWholeStack"):JS.index("function surprise")]
    assert "syncStage();" in apply_whole
    assert apply_whole.index("else kickPreview();") < apply_whole.index("syncStage();")
    assert "var wholeProof = _active && state.view === 'whole' && paintLoaded() && !!detectWholeApplied();" in JS
    assert ".spb-easy-proof-on .spb-easy-source-card, .spb-easy-proof-on .spb-easy-live-card { display:flex" in CSS
    assert ".spb-easy-proof-on .spb-easy-channel-strip { display:grid; }" in CSS
    assert "spec.addEventListener('load', syncSpecProof)" in JS


def test_easy_save_skips_the_pro_recipe_modal_and_lands_on_verified_result():
    wrapper = JS[JS.index("function installRenderWraps"):JS.index("function finallyEasySuccess")]
    assert "easySaveInFlight = _active && _saving" in wrapper
    assert "origShow.apply(this, arguments)" in wrapper, "Keep Pro preview/history side effects."
    assert "window.closeRenderResults()" in wrapper
    assert wrapper.index("window.closeRenderResults()") < wrapper.index("finallyEasySuccess(result)")
    assert "renderResultsPanel" in wrapper and "renderResultsBackdrop" in wrapper
    assert "if (proPanel) proPanel.style.display = 'none'" in wrapper
    assert "if (proBackdrop) proBackdrop.style.display = 'none'" in wrapper
    assert "body.spb-easy-on #renderResultsBackdrop { display: none !important; }" in CSS
    assert "Verified in iRacing!" in JS
    easy_token = re.search(r'js/spb-easy-mode\.js\?v=([^"\']+)', HTML)
    css_token = re.search(r'css/spb-easy-mode-20260716\.css\?v=([^"\']+)', HTML)
    assert easy_token and css_token
    assert easy_token.group(1) == css_token.group(1)
    assert easy_token.group(1).startswith("spb-easy-materialmix-")


def test_live_render_uses_material_canvas_for_whole_car_and_image_for_by_color():
    assert "var sourceOnly" in JS
    assert "els.liveCanvas.hidden = !(wholeProof || sourceOnly || (byColor && !byColorHasMaterial))" in JS
    assert "els.previewImg.hidden = wholeProof || sourceOnly || !byColorHasMaterial" in JS
    assert "#spbEasyLiveCanvas[hidden]" in CSS
    hidden_rule = CSS.split("#spbEasySourceCanvas[hidden]", 1)[1].split("}", 1)[0]
    assert "#spbEasyPreviewImg[hidden]" in hidden_rule
    assert "display:none !important" in hidden_rule


def test_easy_and_guided_spec_proofs_share_the_pro_channel_renderer():
    assert "function spbRenderSpecProofSet" in STATE_JS
    assert "window.spbRenderSpecProofSet = spbRenderSpecProofSet" in STATE_JS
    assert "const SPEC_DOCK_TINTS = { r: [1.0, 0.0, 0.0], g: [0.0, 1.0, 0.0], b: [0.0, 0.0, 1.0] }" in STATE_JS
    assert "spbRenderSpecProofSet(img, targets, SPEC_DOCK_THUMB)" in STATE_JS
    assert "window.spbRenderSpecProofSet(spec" in JS
    assert "window.spbRenderSpecProofSet(image" in SCULPT_JS


def test_easy_save_requires_exact_car_path_and_both_expected_files():
    assert "spbEasyCarSelect" in JS
    assert "CUSTOM NUMBER" in JS and "SIM-STAMPED" in JS
    assert "_saveExpected = { path: route.path, car: route.name, names: expectedOutputNames() }" in JS
    assert "normalizePath(out.path) === normalizePath(expected.path)" in JS
    assert "expected.names.every" in JS
    assert "out.success === true" in JS
    assert "Easy Mode will not call this DONE" in JS
    assert "Verified in iRacing!" in JS


def test_easy_save_is_blocked_until_every_color_and_destination_are_complete():
    assert "function saveBlockReason" in JS
    assert "FINISH OR REMOVE THE UNFINISHED COLOR" in JS
    assert "NEEDS A FINISH" in JS
    assert "CHOOSE AN iRACING CAR" in JS
    assert "ENTER YOUR CUSTOMER ID" in JS
    assert "els.save.disabled = !!reason" in JS
    assert "Finish or remove the color marked NEEDS A FINISH first." in JS
    assert "bc.phase = (chosen.base || chosen.finish) ? 'options' : 'color'" in JS


def test_easy_destination_has_plain_english_search_without_losing_selection():
    assert "FIND YOUR CAR FAST" in JS
    assert "function filterEasyCarOptions" in JS
    assert "option.hidden = !!query" in JS
    assert "!option.selected" in JS
    assert "_carFilterQuery = ''" in JS
    assert "_carFilterQuery = ''; state.view = 'whole'" in JS
    assert "function enterByColor() {\n        _carFilterQuery = '';" in JS
    assert '.spb-easy-destination input[type="search"]' in CSS


def test_easy_navigation_and_color_removal_have_plain_english_names():
    assert 'aria-label="Back to Easy Mode choices"' in JS
    assert "aria-label=\"Remove ' + esc(f ? f.name : 'unfinished color')" in JS


def test_shipping_runtime_mirrors_match():
    assert (ROOT / "electron-app" / "server" / "js" / "spb-easy-mode.js").read_bytes() == (ROOT / "js" / "spb-easy-mode.js").read_bytes()
    assert (ROOT / "electron-app" / "server" / "css" / "spb-easy-mode-20260716.css").read_bytes() == (ROOT / "css" / "spb-easy-mode-20260716.css").read_bytes()
    assert (ROOT / "electron-app" / "server" / "js" / "features" / "spb-easy-sculpt.js").read_bytes() == (ROOT / "js" / "features" / "spb-easy-sculpt.js").read_bytes()
    assert (ROOT / "electron-app" / "server" / "css" / "spb-easy-sculpt.css").read_bytes() == (ROOT / "css" / "spb-easy-sculpt.css").read_bytes()
    assert (ROOT / "electron-app" / "server" / "paint-booth-2-state-zones.js").read_bytes() == (ROOT / "paint-booth-2-state-zones.js").read_bytes()
