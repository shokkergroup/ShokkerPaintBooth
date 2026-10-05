"""Contracts for the complete, focused SPEC SCULPT look-library path."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from engine.spec_sculpt.generate import _build_protect_mask_from_psd, zoned_auto_spec


class _FakeLayer:
    def __init__(self, name, bbox, color=(255, 255, 255, 255), children=None):
        self.name = name
        self.bbox = bbox
        self.kind = "group" if children is not None else "pixel"
        self._children = children or []
        self._color = color

    def __iter__(self):
        return iter(self._children)

    def composite(self):
        width = max(1, self.bbox[2] - self.bbox[0])
        height = max(1, self.bbox[3] - self.bbox[1])
        return Image.new("RGBA", (width, height), self._color)


class _FakePsd(list):
    width = 32
    height = 16


def _synthetic_paint(size=128):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    tex = np.zeros((size, size, 3), np.float32)
    tex[..., 0] = np.where(x < size / 2, 0.83, 0.08)
    tex[..., 1] = np.where(y < size / 2, 0.16, 0.62)
    tex[..., 2] = 0.24 + 0.18 * np.sin(x / 5.0)
    return np.clip(tex, 0.0, 1.0)


def test_desktop_server_pins_python_hash_seed_for_restart_stable_materials():
    main = Path("electron-app/main.js").read_text(encoding="utf-8")
    legacy_main = Path("main.js").read_text(encoding="utf-8")
    launcher = Path("START_SERVER.bat").read_text(encoding="utf-8")
    dev_launcher = Path("START_V5_DEV.bat").read_text(encoding="utf-8")
    guardian = Path("tools/spb_python_guardian.ps1").read_text(encoding="utf-8")

    assert main.count("PYTHONHASHSEED: '0'") >= 2
    assert "PYTHONHASHSEED: '0'" in legacy_main
    assert "set PYTHONHASHSEED=0" in launcher
    assert "set PYTHONHASHSEED=0" in dev_launcher
    assert "$env:PYTHONHASHSEED = '0'" in guardian


def test_zoned_easy_drama_is_deterministic_iron_safe_and_materially_distinct():
    tex = _synthetic_paint()
    less = np.asarray(zoned_auto_spec(tex, 4242, drama=0.64))
    balanced = np.asarray(zoned_auto_spec(tex, 4242, drama=1.0))
    wild = np.asarray(zoned_auto_spec(tex, 4242, drama=1.38))

    assert less.shape == balanced.shape == wild.shape == (128, 128, 4)
    assert np.array_equal(wild, np.asarray(zoned_auto_spec(tex, 4242, drama=1.38)))
    for result in (less, balanced, wild):
        assert result.dtype == np.uint8
        assert np.all(result[..., 3] == 255)
        assert not np.any((result[..., 2] >= 1) & (result[..., 2] < 16))
        assert not np.any((result[..., 0] < 240) & (result[..., 1] < 15))

    satin = np.asarray((105.0, 110.0, 140.0), np.float32)
    less_distance = np.abs(less[..., :3].astype(np.float32) - satin).mean()
    balanced_distance = np.abs(balanced[..., :3].astype(np.float32) - satin).mean()
    wild_distance = np.abs(wild[..., :3].astype(np.float32) - satin).mean()
    assert less_distance < balanced_distance < wild_distance


def test_psd_protection_uses_positional_keys_when_duplicate_names_exist():
    fake = _FakePsd(
        [
            _FakeLayer(
                "Group",
                (0, 0, 32, 16),
                children=[
                    _FakeLayer("Logo", (0, 0, 16, 16)),
                    _FakeLayer("Logo", (16, 0, 32, 16)),
                ],
            )
        ]
    )
    mask = _build_protect_mask_from_psd(fake, set(), {"0.1"})

    assert mask is not None
    assert np.all(mask[:, :16] == 255), "The first duplicate must remain sculptable."
    assert np.all(mask[:, 16:] == 0), "Only positional key 0.1 should be protected."


def test_imported_spec_is_a_complete_zero_zone_material_plan(tmp_path):
    from shokker_engine_v2 import build_multi_zone

    height, width = 48, 64
    yy, xx = np.mgrid[0:height, 0:width]
    paint = np.stack(
        [40 + (xx % 80), 70 + (yy % 90), np.full_like(xx, 130)], axis=2
    ).astype(np.uint8)
    spec = np.stack(
        [100 + (xx % 50), 90 + (yy % 70), 40 + ((xx + yy) % 60), np.full_like(xx, 255)], axis=2
    ).astype(np.uint8)
    paint_path = tmp_path / "paint.png"
    spec_path = tmp_path / "sculpt_spec.tga"
    output_dir = tmp_path / "render"
    Image.fromarray(paint, mode="RGB").save(paint_path)
    Image.fromarray(spec, mode="RGBA").save(spec_path)

    rendered_paint, rendered_spec, masks = build_multi_zone(
        str(paint_path),
        str(output_dir),
        [],
        iracing_id="23371",
        import_spec_map=str(spec_path),
        car_prefix="car_num",
    )

    assert masks == []
    assert np.array_equal(rendered_paint, paint)
    assert np.array_equal(rendered_spec, spec), "Main Render must preserve the complete Sculpt map byte-for-byte."


def test_spec_sculpt_keeps_every_look_in_a_focused_guided_path():
    root = Path(__file__).resolve().parents[1]
    easy = (root / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")
    sculpt = (root / "js" / "features" / "spb-easy-sculpt.js").read_text(encoding="utf-8")
    guidance = (root / "js" / "features" / "spb-easy-sculpt-guidance.js").read_text(encoding="utf-8")
    sculpt_css = (root / "css" / "spb-easy-sculpt.css").read_text(encoding="utf-8")
    original = (root / "spec-sculpt.html").read_text(encoding="utf-8")
    html = (root / "paint-booth-v2.html").read_text(encoding="utf-8")
    main_render = (root / "paint-booth-5-api-render.js").read_text(encoding="utf-8")
    server = (root / "server.py").read_text(encoding="utf-8")

    assert "SPEC SCULPT" in easy
    assert "FULL LOOK LIBRARY" in easy
    assert "spbEasyForkWhole" in easy and "spbEasyForkByColor" in easy
    assert "SHOW_LEGACY_SPEC_LAB = true" in sculpt
    assert "easy_paint=" in sculpt and "_easyPaintHandoff" in original
    assert "easy_car=" in sculpt and "_easyCarHandoff" in original
    assert "easy_id=" in sculpt and "_easyIdHandoff" in original
    assert "easy_custom=" in sculpt and "_easyCustomHandoff" in original
    assert "state.pendingDeployCar = _easyCarHandoff" in original
    assert "discoveredPaths[c.name] = c.path" in original
    assert "state.carPaths = Object.assign({}, state.carPaths || {}, discoveredPaths)" in original
    assert "function readableCarName" in original
    assert 'id="deployCarSearch"' in original and "Find your iRacing car" in original
    assert 'id="deployCarSearchStatus" role="status" aria-live="polite"' in original
    for control_id in ("pathInput", "iracingId", "deployCarSearch", "outputDir", "fusionStrategy", "paintEmphasis", "hueFocusColor", "seed", "styleNotes"):
        assert f'for="{control_id}"' in original, f"Original Spec Sculpt must label {control_id} explicitly."
    assert 'id="deployCar" aria-label="Selected iRacing car folder"' in original
    assert 'id="apStrength"' in original and 'aria-label="Auto-protect detection strength"' in original
    assert "function deployCarMatches(query)" in original
    assert "function filterDeployCarOptions" in original
    assert "!option.selected" in original and "filterDeployCarOptions();" in original
    assert "event.key !== 'Enter'" in original and "matches[0].value" in original
    assert "Dirt Late Model 438" in original and "Exact iRacing folder:" in original
    assert "Acura ARX-06 GTP" in original and "Chevrolet Corvette Z06 GT3.R" in original
    for friendly_name in ("Chevrolet Corvette C8.R GTE", "Ford Fiesta RS WRC", "Nissan GTP ZX-T", "Spec Racer Ford", "Mazda MX-5 Roadster", "Indy Pro 2000 PM-18"):
        assert friendly_name in original
        assert friendly_name in sculpt
    assert "if ($('deployNow').checked || opts.force_deploy)" in original
    assert "if (dep) body.deploy_car_folder = dep" in original
    assert "else if (od) body.output_dir = od" in original
    assert original.index("if ($('deployNow').checked || opts.force_deploy)") < original.index("if (dep) body.deploy_car_folder = dep")
    assert "generate({ force_deploy: true })" in original
    assert 'id="btnGenerate" data-advanced-only' in original
    assert "generate(getUiMode() === 'simple' ? { force_deploy: true } : {})" in original
    assert "The primary handler above owns Ctrl+Enter" in original
    assert "Use <b>BUILD + INSTALL IN iRACING</b> in the Style Gallery" in original
    assert "var item = document.createElement('button'); item.type = 'button';" in original
    assert "item.tabIndex = 0; item.setAttribute('role', 'button');" in original
    assert "img.tabIndex = 0; img.setAttribute('role', 'button')" in original
    assert ".recent-item:focus-visible" in original
    assert "Save to the selected car automatically after each Generate" in original
    assert "fetchLivePreviewFast" in original and "preview_tex_size', '512'" in original
    assert "if (state.generateBusy) return;" in original
    assert "Cancel that queued preview before it can compete" in original
    assert "A carried/restored job is already past step 1" in original
    assert "if (hasPaint) return;" in original
    assert "(_easyPaintHandoff || _easyUploadHandoff) ? 'collapsed' : 'open'" in original
    assert 'id="btnSpotlight" data-advanced-only' in original
    assert 'id="btnHueMap" data-advanced-only' in original
    assert 'id="paintPreviewCard" data-advanced-only' in original
    assert 'id="surpriseStatus" role="status" aria-live="polite"' in original
    assert "STYLE_GALLERY.slice(0, 12).filter" in original
    assert "entry.name !== state.simpleLookName" in original
    assert "if (useCatalog) applyCatalogStyle(final.id, final.name);" in original
    assert "else applyStyle(final);" in original
    assert 'class="style-tile"' in original and 'aria-pressed="false"' in original
    assert "tile.setAttribute('aria-pressed', selected ? 'true' : 'false')" in original
    assert "receipt.textContent = state.simpleLookName ? state.simpleLookName + ' selected' : ''" in original
    assert "simple_look_kind: state.simpleLookKind" in original and "simple_look_name: state.simpleLookName" in original
    assert "function rememberSimpleLook" in original and "syncSimpleLookUi();" in original
    assert "12 GO-TO STYLES" in original and "Advanced reveals 60+ one-click styles" in original
    assert "index >= 12 ? ' data-advanced-only'" in original
    assert 'id="catalogGalleryGrid" data-advanced-only' in original
    assert 'id="lookBlendCard" data-step="2" data-advanced-only' in original
    assert 'data-beta-retired="smart-separate"' in original
    assert '<script src="js/features/spec-sculpt-layers.js' not in original
    assert "var c = $('autoSepCard'); if (c) c.style.display = 'none';" in original
    assert "s.blend_mode === 'fracture'" in original and "s.blend_mode === 'candy_depth'" in original
    assert 'id="btnGenerateSimple"' in original
    assert "simpleGenerate.disabled = disabled" in original
    assert "$('btnGenerateSimple').addEventListener('click', function () { generate({ force_deploy: true }); })" in original
    assert "BUILD + INSTALL IN iRACING" in original
    assert "Writes paint + spec to the selected car and verifies both files." in original
    assert "$('deployNow').checked || opts.force_deploy" in original
    assert "row(destinationOk, 'iRacing car destination')" in original
    assert "Paint carried in from Easy Spec Sculpt" in original
    assert "easy_upload=1" in sculpt
    assert "window.opener.spbEasySculpt" in original
    assert "window.opener.focus()" in original and "window.close()" in original
    assert "_acceptPaintFile(_easySourceState.file" in original
    assert "Capturing every visible edit from the paint already open" in sculpt
    assert "window.requestAnimationFrame(function () { window.setTimeout(resolve, 0); })" in sculpt
    assert "knownResolution: [canvas.width, canvas.height]" in sculpt and "sourcePreviewDataUrl: canvasPreviewDataUrl(canvas)" in sculpt
    assert "psdImportData: livePsdData" in sculpt and "options.psdImportData && options.psdImportData.success" in sculpt
    assert "psdImportData: null" in sculpt and "state.psdImportData = psd" in sculpt
    assert "function hydratePsdFromEasy" in original and "_easySourceState.psdImportData" in original
    assert "Reused from Easy — no second import" in original
    assert "if (_easyPsdHydrated) { scheduleLivePreview(); return; }" in original
    assert "var psdLoadSerial = 0" in original and "var psdLoadAbort = null" in original
    assert "loadSerial !== psdLoadSerial" in original and "e.name === 'AbortError'" in original
    assert "signal: psdLoadAbort && psdLoadAbort.signal" in original
    assert "var analyzeSerial = 0" in original and "var analyzeAbort = null" in original
    assert "checkSerial !== analyzeSerial" in original and "signal: analyzeAbort && analyzeAbort.signal" in original
    assert "Never let the delayed boot task resurrect that superseded PSD" in original
    assert "function currentPaintStillLoading" in sculpt and "window._spbPsdImportInFlight === true" in sculpt
    assert "FINISHING THE PSD LAYERS" in sculpt and "currentPaintAvailabilityKey()" in sculpt
    assert "openSpecSculptLab" in sculpt, "The internal legacy lab implementation must be preserved."
    assert "OPEN ORIGINAL SPEC SCULPT" in easy and "OPEN ORIGINAL SPEC SCULPT" in sculpt
    assert "SHOKK THE WORLD" in easy and "SHOKK THE WORLD" in sculpt
    assert "Shokk the World" in original and "Auto-Sculpt" in original
    assert "function _ensureWorldCatalogPool" in original
    assert "lookLabel + ' material preview'" in original
    assert "use.setAttribute('aria-label', 'Use ' + lookLabel)" in original
    assert "use.setAttribute('aria-pressed', 'true')" in original
    assert "BUILT · USE AGAIN" in original and "TRY THIS LOOK AGAIN" in original
    assert "Combined / Red / Green / Blue proof channels are ready below" in original
    assert "catalog: [[e.id, 1.0]]" in original
    assert "preview_url: API + '/api/swatch/'" in original
    assert "full-library choices instantly" in original
    assert "state.quickCatalogStack = cstack" in original
    assert "onBlendModeChange({ skipCatalogLoad: true })" in original
    assert "document.querySelectorAll('[data-spot]')" in original
    assert '"tile_only": tile_only' in server
    assert 'previews = {} if tile_only else spec_preview_png_data_urls(spec_u8)' in server
    assert "strict2048: true" in sculpt
    assert "protect_layer_keys" in sculpt
    assert "window._psdPath" in sculpt and "sourcePath" in sculpt
    assert "/api/spec-sculpt/presets" in sculpt
    assert "/api/spec-sculpt/catalog-index" in sculpt
    assert "catalog.complete !== false" in sculpt
    assert "Paint Booth base material" not in sculpt and "Paint Booth special finish" not in sculpt
    assert "title=\"' + esc(look.description || look.name)" in sculpt
    assert "preset_stack" in sculpt and "catalog_stack" in sculpt
    assert "SPECIAL_LOOKS" in sculpt
    assert "SPEC LOOKS" in sculpt and "PAINT BOOTH" in sculpt
    assert "SURPRISE ME" in sculpt
    assert "BACK TO " in sculpt and "restorePreviousLook" in sculpt
    assert "materialPlanSeed" in sculpt and "previewCacheKey" in sculpt and "rememberPreview" in sculpt
    assert "colorMaterialSeed" in sculpt and "re-seed or reshuffle the base" in sculpt
    assert 'seed: colorMaterialSeed(target, look)' in sculpt
    assert '_layer_seed = int(layer.get("seed")' in server
    assert "the same plan always returns" in sculpt
    assert "an already-resolving fetch must never overwrite an instant Back" in sculpt
    assert "TRY NEXT LOOK" in sculpt and "function nextLook" in sculpt
    assert "GO TO SAVE" in sculpt and "spbEasySculptGoSave" in sculpt and "advanceToInstallCard" in sculpt
    assert "if (current && lookKey(current) === lookKey(look)) return" in sculpt
    assert "captureLibraryView" in sculpt and "restoreLibraryView" in sculpt
    assert "libraryAnchorOffset" in sculpt and "currentOffset - anchorOffset" in sculpt
    assert "focus({ preventScroll: true })" in sculpt
    assert "body.scrollTop = top" in sculpt
    assert "state.libraryQuery = '';\n            state.libraryKind = 'recommended';\n            state.libraryCategory = '';\n            state.libraryLimit = LOOK_PAGE_SIZE;\n            persistRecoveryPlan();" in sculpt
    assert "ResizeObserver" in sculpt and "stopGuarding" in sculpt
    assert "TRY THIS LOOK AGAIN" in sculpt and "friendlyError" in sculpt
    assert "readJsonResponse" in sculpt and "Unexpected token <" in sculpt
    assert "256 MB Spec Sculpt upload limit" in sculpt
    assert "function responseError" in sculpt and "function isRetryableError" in sculpt
    assert "status === 429 || status >= 500" in sculpt
    assert "var directPsdUpload = isPsd(file) && !options.psdPath" in sculpt
    assert "var directPsdPath = directPsdUpload ? String(file.path || '').trim()" in sculpt
    assert "options.psdPath || directPsdPath" in sculpt
    assert "if (!directPsdUpload)" in sculpt and "state.resolution = [psd.width, psd.height]" in sculpt
    assert "Reading the PSD once" in sculpt
    assert "if (!isPsd())" in sculpt and "Reading the open PSD once" in sculpt
    assert "serverSourcePath" in sculpt
    assert "if (state.file && !state.serverSourcePath)" in sculpt
    assert "if (!state.file || state.serverSourcePath)" in sculpt
    assert "if (directPsdUpload) state.serverSourcePath = state.psdPath" in sculpt
    assert "(state.file || state.sourcePath) && state.selectedLook" in sculpt
    assert "Your paint is still here" in sculpt
    assert "FOR THIS PAINT" in sculpt and "recommendedLookKeys" in sculpt
    assert "paintProfileLabel" in sculpt and "hues.join(' + ')" in sculpt
    assert "loadPaintAwareRecommendations" in sculpt and "/api/spec-sculpt/batch" in sculpt
    assert "if (!state.looksLoaded || !state.cars.length) environmentPromise = null" in sculpt
    assert "async function ensureEnvironment" in sculpt and "if (!state.looksLoaded || !state.cars.length) await loadEnvironment()" in sculpt
    assert "Painting these picks onto your livery" in sculpt and "look.paintThumb" in sculpt
    assert "look.kind === 'mode'" in sculpt and "else row.mode = look.id" in sculpt
    assert "recommendationPlanSeed" in sculpt and "exact: true" in sculpt
    assert "recommendationContextSignature" in sculpt and "recommendationColorPlan" in sculpt
    assert "changes in these previews" in sculpt and "colorTargetName(previewTarget)" in sculpt
    assert "easy_base" in sculpt and "easy_color_layers" in sculpt
    assert "_render_exact_named_look" in server
    assert "composite_easy_color_layers" in server
    assert "replacement_color" in sculpt
    assert "KEEP ORIGINAL" in sculpt and "CHANGE COLOR" in sculpt
    assert "/api/spec-sculpt/sample-source-color" in sculpt
    assert "state.sourceToken = String(analyzed.source_token || '')" in sculpt
    assert "'X-Shokker-Internal': '1'" in sculpt
    assert "The 480px JPEG on screen is display-only" in sculpt
    assert "sampleSerial !== requestSerial || sampleIdentity !== sourceIdentity()" in sculpt
    assert "var editorColor = target.replacementColor || target.hex" in sculpt
    assert "target.replacementColor = target.replacementColor || target.hex" not in sculpt, (
        "Opening Change Color must preview the detected swatch without committing a repaint."
    )
    assert "PAINT BOOTH BASE COLOR" in sculpt and "CHOOSE FROM REAL THUMBNAILS" in sculpt
    assert "spbEasySculptBaseColorSearch" in sculpt and "function filterBaseColorOptions" in sculpt
    assert "real base thumbnail' + (visible === 1 ? '' : 's')" in sculpt
    assert "spbEasySculptHue" in sculpt and "spbEasySculptSaturation" in sculpt and "spbEasySculptBrightness" in sculpt
    assert "spbEasySculptColorNext" in sculpt and "PICK THIS COLOR\\'S FINISH" in sculpt
    assert "colorTargetPaintLabel" in sculpt
    assert "recolor_easy_paint" in server
    assert "paint_tex = recolor_easy_paint(tex, _easy_color_layers)" in server
    assert '_exact_plan = _parse_bool_form(var.get("exact")) is True' in server
    assert "pattern_tile_for_scale(var.get" in server
    assert 'mode not in {"zoned", "fracture", "candy_depth"}' in server
    assert "refreshRecommendationTiles" in sculpt
    assert "make a valid look click feel like it did nothing" in sculpt
    assert "realSwatchUrl" in sculpt and "spb-easy-sculpt-look-art" in sculpt
    assert "PREVIEW UNAVAILABLE" in sculpt
    assert 'onerror="this.remove()"' not in sculpt, "A failed thumbnail must state that the preview is unavailable."
    assert 'role="tab"' in sculpt and 'aria-selected=' in sculpt
    assert 'role="group" aria-label="Choose or drop a 2048 iRacing paint file"' in sculpt
    assert 'role="status" aria-live="polite" aria-busy="true"' in sculpt
    assert "progressStep: 'checking'" in sculpt and "step === 'protecting'" in sculpt
    assert 'class="spb-easy-sculpt-showing" role="status" aria-live="polite"' in sculpt
    assert 'class="spb-easy-sculpt-error" role="alert"' in sculpt
    assert "ArrowLeft" in sculpt and "ArrowRight" in sculpt
    assert "COLORS SHOKKER FOUND" in sculpt and "data-palette-index" in sculpt
    assert "AUTO-SCULPT " in sculpt and "function autoSculptColors" in sculpt
    assert "chooseAutoColors" in guidance and "autoLookForColor" in sculpt
    assert "CHOOSE A LOOK" in sculpt and "CHOOSE COLOR FIRST" in sculpt
    assert "The preview still shows the whole-paint material" in sculpt
    assert "MATERIAL PLAN READY" in sculpt and "data-material-meter" in sculpt
    assert "AUTO-SCULPTED STARTING POINT" in sculpt
    assert "beginSmartStartingPoint" in sculpt and "findLook('mode:zoned')" in sculpt
    assert sculpt.count("beginSmartStartingPoint();") >= 2
    assert "MATERIAL READOUT" in sculpt and "materialImpactWords" not in sculpt
    assert "clearcoatStrength = 1 - clearcoatRead" in sculpt
    assert "coat: responseMeans[2]" in sculpt
    assert "<figcaption>ORIGINAL</figcaption>" in sculpt
    assert sculpt.index("<figcaption>ORIGINAL</figcaption>") < sculpt.index("'SCULPTED PAINT'") < sculpt.index("<figcaption>SPEC OUTPUT</figcaption>")
    assert "SCULPTED PAINT" in sculpt and "<figcaption>SPEC OUTPUT</figcaption>" in sculpt
    assert "Sculpted paint preview: ' + esc(previewCaption)" in sculpt and "MATERIAL DATA &middot; OPEN FULL MAP" in sculpt
    assert "Generated light map" not in sculpt
    assert "Install renders this exact plan at 2048." in sculpt and "BACK TO ALL 3 VIEWS" in sculpt
    assert "analyzePixels" in guidance and "rankLooks" in guidance
    assert "matchesLookSearch" in guidance and "Try shiny, matte, sparkle, carbon, color shift, subtle, or wild" in sculpt
    assert "activeTargetLook" in sculpt and "WHAT iRACING READS" in sculpt
    assert "EDIT ONE AREA AT A TIME" in sculpt
    assert "ADD COLOR" in sculpt and "CLICK A COLOR ON YOUR PAINT" in sculpt
    assert '<div class="spb-easy-sculpt-pick-overlay"' in sculpt
    assert '<button type="button" class="spb-easy-sculpt-pick-overlay"' not in sculpt
    assert 'aria-label="Back to Easy Mode choices"' in sculpt
    assert "proButton.disabled = state.phase === 'saving'" in sculpt
    assert "Finish the verified iRacing install first" in sculpt
    assert "BASE SCALE" in sculpt and "SPEC SCALE: MATCHED" in sculpt
    assert "colorTargetName(target) + ' SCALE'" in sculpt and "Lower makes only " in sculpt
    assert "syncLinkedScale" in sculpt
    assert "base and spec matched" in sculpt
    assert "MATERIAL IMPACT" in sculpt and "SUBTLE" in sculpt and "BALANCED" in sculpt and "BOLD" in sculpt
    assert "data-material-impact" in sculpt and "material_impact: state.materialImpact" in sculpt
    assert "spbEasySculptImpact-" in sculpt and "spbEasySculptReach" in sculpt
    scope_wire = sculpt[sculpt.index("function wireTargetEditor"):sculpt.index("var add = $('spbEasySculptAddColor')")]
    assert "spbEasySculptScope-whole" in sculpt and "WHOLE CAR" in sculpt
    assert scope_wire.index("captureLibraryView();") < scope_wire.index("render();") < scope_wire.index("restoreLibraryView();")
    assert "state.focusReturnId = button.id" in scope_wire and "state.focusReturnLookKey = ''" in scope_wire
    assert "apply_material_impact" in server and "apply_material_impact_to_report" in server
    assert '"material_impact": material_impact' in server
    assert "state.materialImpact === 'balanced'" in sculpt and "state.materialImpact.toUpperCase()" in sculpt
    change_scale_start = sculpt.index("scale.addEventListener('change'")
    change_scale_body = sculpt[change_scale_start:sculpt.index("function wireSourceColorPicker", change_scale_start)]
    assert change_scale_body.index("syncLinkedScale();") < change_scale_body.index("generatePreview(")
    assert "easy_color_layers" in sculpt and "material_scale" in sculpt
    assert "fast_trace: true" in sculpt, "Guided Spec Sculpt must use the beta-safe one-pass paint trace."
    assert 'fast_trace = _parse_bool_form(gv("fast_trace"))' in server
    assert "fast_trace=fast_trace" in server
    assert "_schedule_spec_sculpt_purge()" in server, "Old job cleanup must not block the Save response."
    assert "MAX_COLOR_TARGETS = 6" in sculpt
    assert "OPEN EASY SPEC SCULPT" in original and "/?easy=spec-sculpt" in original
    assert "document.body.getAttribute('data-ui-mode') !== 'advanced'" in original
    assert "generate(_simpleAutoInstallOptions({ fast_trace: true }))" in original
    assert "if (getUiMode() === 'simple') out.force_deploy = true" in original
    assert "sourceValidation: 'unknown'" in original and "sourceValidation === 'invalid'" in original
    assert "sourceValidation === 'wrong-size'" in original
    assert "sourceValidation !== 'loading'" in original and "Reading PSD layers and protected regions" in original
    assert "sourceValidation !== 'checking'" in original and "Checking paint file and dimensions" in original
    assert "Simple mode needs a 2048×2048 iRacing template" in original
    assert "getUiMode() === 'simple' ? true : $('strict2048').checked" in original
    assert "/2048\\s*[x×]\\s*2048/i.test(generateError)" in original
    assert 'aria-label="Dismiss restored-session notice"' in original
    assert "min-height: 30px; padding: 6px 14px" in original
    assert 'input[type="search"], select, textarea' in original and 'input[type="range"] { width: 100%; min-height: 24px;' in original
    assert "new URLSearchParams(window.location.search).get('easy') === 'spec-sculpt'" in easy
    assert "isolateProAccessibility" in easy and "restoreProAccessibility" in easy
    assert "element.setAttribute('inert', '')" in easy
    assert "Keep modal/file-picker siblings available" in easy
    assert "Move focus out of Pro" in easy and "els.root.focus" in easy
    assert "Shokker Paint Booth Easy Mode" in easy
    assert "materialGain" in sculpt, "The material channels must visibly shape the painted preview."
    assert "materialLift" in sculpt
    assert "beamDistance" not in sculpt and "rimDistance" not in sculpt
    assert "spb-easy-sculpt-sheen" not in sculpt and "spbSculptSheen" not in sculpt_css
    assert "box-sizing: border-box" in sculpt_css
    assert "body.spb-easy-sculpt-on { overflow: hidden !important; }" in sculpt_css
    assert "#spbEasyRoot button:focus-visible" in sculpt_css
    assert ".spb-easy-sculpt-look-art img" in sculpt_css
    assert "body.spb-easy-sculpt-on #spbTopToolbar" in sculpt_css and "body.spb-easy-sculpt-on #undoHistoryPanel" in sculpt_css
    assert ".spb-easy-sculpt-compare canvas { height: 100%; max-height: 100%; object-fit: contain; }" in sculpt_css
    assert "body.spb-easy-sculpt-on #spbQuestChip" in sculpt_css
    assert "SAVE TO iRACING" in sculpt
    assert "incompleteColorTarget" in sculpt and "PICK A LOOK FOR " in sculpt
    assert "Finish ' + esc(colorTargetLabel(unfinished)) + ' above" in sculpt
    assert "No paint matched " in sculpt and "TRY WIDE OR REMOVE " in sculpt
    assert "function colorTargetName" in sculpt and "function colorTargetLabel" in sculpt
    assert "target.materialMeans" in sculpt and "responseTarget.materialMeans" in sculpt
    assert "Material response' + (activeTarget ? ' for '" in sculpt
    assert "targetNeedsLook ? '' : '<small id=\"spbEasySculptMaterialSummary\"" in sculpt
    assert "targetNeedsLook ? '' : '    <div class=\"spb-easy-sculpt-material-meters\"" in sculpt
    assert "FOR THIS COLOR" in sculpt and "SHOKKER PICKED FOR THIS COLOR" in sculpt
    assert "name: guidance.colorName(target.color)" in sculpt
    assert "lookSearchTimer" in sculpt and "}, 120);" in sculpt
    assert "spbEasySculptSearchClear" in sculpt and "Clear look search" in sculpt
    assert "event.key !== 'Escape'" in sculpt and "var nextSearch = $('spbEasySculptLookSearch')" in sculpt
    assert "before the 120ms search repaint" in sculpt
    assert "closest matches" in sculpt and "scoreLookSearch(look, q, true)" in sculpt
    assert "'SPEC SCULPT · ' + activeTargetLabel()" in sculpt
    assert "reachLabel" in sculpt and "only very close shades" in sculpt and "include more nearby shades" in sculpt
    assert "errorContext === 'install'" in sculpt and "errorContext !== 'install'" in sculpt
    assert "Enter your 4–7 digit iRacing Customer ID." in sculpt
    assert "Choose the iRacing car folder that should receive this paint." in sculpt
    assert "borrowDeploymentFromSource" in sculpt
    assert "inferredUseCustomNumber" in sculpt and "^car_(num_)?" in sculpt
    assert "state.inferredUseCustomNumber = !!idMatch[1]" in sculpt
    assert "state.iracingId = idMatch[2]" in sculpt
    assert "if (matchedCar) state.car = matchedCar.name" in sculpt
    assert "if (typeof state.inferredUseCustomNumber === 'boolean')" in sculpt
    assert "usefulCarFolder" in sculpt and "copy|backup|old" in sculpt
    assert "window.getCurrentSourcePaintFile" in sculpt
    assert "window.buildLivePaintCompositeCanvas" in sculpt
    assert "LIVE CANVAS" in sculpt and "acceptCurrentPaint" in sculpt
    assert "liveCanvasFingerprint" in sculpt and "canvasPngFile" in sculpt
    assert "A new material is a fresh decision" in sculpt
    assert "sourceLabel" in sculpt and "READY TO USE" in sculpt
    assert "state.psdPath || state.handoffPath || state.sourcePath" in sculpt
    assert "options.originalPath || file.path" in sculpt
    assert "WHICH iRACING CAR?" in sculpt and "both output files route there automatically" in sculpt
    assert "spbEasySculptCustomNumber" in sculpt and "spbEasySculptStampedNumber" in sculpt
    assert "SIM-STAMPED NUMBER" in sculpt and "CUSTOM NUMBER" in sculpt
    assert "useCustomNumber: liveUseCustomNumber()" in sculpt
    assert "typeof payload.useCustomNumber === 'boolean'" in sculpt
    assert ".spb-easy-sculpt-number-choice" in sculpt_css
    assert "FIND YOUR CAR FAST" in sculpt and "spbEasySculptCarSearch" in sculpt
    assert "function filterDestinationCars" in sculpt and "option.hidden" in sculpt
    assert "function destinationCarMatches(query)" in sculpt
    assert "event.key !== 'Enter'" in sculpt and "state.car = matches[0].name" in sculpt
    assert 'id="spbEasySculptCarSearchStatus"' in sculpt
    assert "var target = carReady ? esc(friendlyCarName(state.car))" in sculpt
    assert "(unfinished || !targetReady)" in sculpt
    assert "ENTER YOUR iRACING CUSTOMER ID ABOVE" in sculpt
    assert "CHOOSE AN iRACING CAR ABOVE" in sculpt
    assert "function friendlyCarName" in sculpt
    assert "'dirtlatemodel 438': 'Dirt Late Model 438'" in sculpt
    assert "'acuraarx06gtp': 'Acura ARX-06 GTP'" in sculpt
    assert "esc(friendlyCarName(state.car))" in sculpt
    assert "esc(friendlyCarName(car.name))" in sculpt and "folder: ' + esc(car.name)" in sculpt
    assert "Folder ' + esc(state.car)" in sculpt
    assert "No iRacing car folders found yet" in sculpt
    assert "Open iRacing once, then reopen Spec Sculpt" in sculpt
    assert "var carHelp = carCount" in sculpt and "esc(emptyCarLabel)" in sculpt
    assert sculpt.index("spb-easy-sculpt-car-field") < sculpt.index("spb-easy-sculpt-id-field")
    assert "values.deploy_car_folder = state.car" in sculpt
    assert "state.exportOpen = !state.exportOpen" in sculpt and "destinationControl.focus()" in sculpt
    assert "state.exportOpen && validId(state.iracingId)" in sculpt
    assert "var destinationButton = $('spbEasySculptEditTarget')" in sculpt
    assert "if (destinationButton) destinationButton.focus()" in sculpt
    assert "var filenameId = idReady ? state.iracingId : 'ID';" in sculpt
    assert "customName.textContent = 'car_num_' + filenameId + '.tga'" in sculpt
    assert "Save and the screen must promise the same files" in sculpt
    destination_start = sculpt.index("var id = $('spbEasySculptId')")
    destination_wire = sculpt[destination_start:sculpt.index("var save = $('spbEasySculptSave')", destination_start)]
    assert "wasReady !== isReady" in destination_wire and "nextId.setSelectionRange" in destination_wire
    assert destination_wire.index("state.car = car.value") < destination_wire.index("renderRail();", destination_wire.index("state.car = car.value"))
    assert "var nextCar = $('spbEasySculptCar')" in destination_wire and "nextCar.focus()" in destination_wire
    assert "(!state.car ? ' selected' : '')" in sculpt
    assert "(fields ? 'DONE' : 'SWITCH CAR')" in sculpt
    assert '"Try next" is a promise of visible change' in sculpt
    assert "lookMaterialKey(next) === current" in sculpt
    assert "function borrowDeploymentIdentity" in sculpt
    assert "$('iracingId')" in sculpt and "$('deployCarSelect')" in sculpt
    assert "state.cars.some" in sculpt, "A stale car folder must not look ready to install."
    assert sculpt.count("if (serial !== requestSerial) return;") >= 6, "Every awaited source boundary must reject a stale paint."
    assert "state.phase === 'error' && state.errorContext === 'source'" in sculpt
    assert "BACK TO THIS PAINT" in sculpt and "function continueEditing" in sculpt
    assert "RECOVERY_KEY" in sculpt and "persistRecoveryPlan" in sculpt and "restoreRecoveryPlan" in sculpt
    assert "function canonicalRecoverySource" in sculpt and "transient fingerprint together" in sculpt
    assert "sourcePathKey: recoveryPathKey()" in sculpt and "payload.sourcePathKey === recoveryPathKey()" in sculpt
    assert "var pathFallbackSafe" in sculpt and "/^(path:|live:)/" in sculpt
    assert "Never use a bare filename" in sculpt
    assert "state.sourcePath || state.handoffPath || (state.file && state.file.path)" in sculpt
    recovery_body = sculpt[sculpt.index("function persistRecoveryPlan"):sculpt.index("function materialPlanSignature")]
    assert "iracingId: state.iracingId" in recovery_body and "car: state.car" in recovery_body
    assert "validId(payload.iracingId)" in recovery_body and "car.name === payload.car" in recovery_body
    assert "state.car = car.value;" in sculpt and "persistRecoveryPlan();" in destination_wire
    assert "renderRail();" in destination_wire and "if (nextCar) nextCar.focus();" in destination_wire
    assert "window.localStorage.setItem(RECOVERY_KEY, serialized)" in sculpt
    assert "window.localStorage.getItem(RECOVERY_KEY)" in sculpt
    assert "window.localStorage.removeItem(RECOVERY_KEY)" in sculpt
    assert "LAST SCULPT RESTORED" in sculpt and "Restoring your last sculpt for this paint" in sculpt
    assert "paintDecision: ''" in sculpt
    assert "pendingPaintChoice" in sculpt and "!pendingPaintChoice ? lookPickerHtml()" in sculpt
    assert "FIRST QUESTION" in sculpt and "SECOND QUESTION" in sculpt and "PICK A FINISH" in sculpt
    assert "KEEP OR CHANGE THIS COLOR FIRST" in sculpt and "NOW CHOOSE ITS FINISH" in sculpt
    assert "target.paintDecision = 'keep'" in sculpt and "target.paintDecision = 'change'" in sculpt
    assert "function advanceToLookPicker()" in sculpt
    assert "state.focusReturnId = 'spbEasySculptLookSearch'" in sculpt
    assert "advanceToLookPicker();" in sculpt
    assert "aria-pressed=\"' + (target.paintDecision === 'keep'" in sculpt
    assert "function rgbToHsv(rgb)" in sculpt and "function hsvHex(hue, saturation, brightness)" in sculpt
    assert "function paintBaseLibraryHtml(selectedId)" in sculpt
    assert 'id="spbEasySculptSolidColor"' in sculpt
    assert 'id="spbEasySculptBaseColor"' in sculpt
    assert 'id="spbEasySculptBaseColorLibrary"' in sculpt
    assert 'id="spbEasySculptBaseColorSelect"' not in sculpt
    assert 'id="spbEasySculptHue"' in sculpt
    assert 'id="spbEasySculptSaturation"' in sculpt
    assert 'id="spbEasySculptBrightness"' in sculpt
    assert 'id="spbEasySculptColorNext"' in sculpt
    assert "colorNext.addEventListener('click', advanceToLookPicker)" in sculpt
    assert "function advanceToInstallCard()" in sculpt
    assert "state.advanceToSaveAfterPreview = !!target && !current" in sculpt
    assert "state.focusReturnId = 'spbEasySculptSave'" in sculpt
    assert "getBoundingClientRect().top - body.getBoundingClientRect().top - 10" in sculpt
    assert "data-palette-wired" in sculpt and "origin.closest('[data-palette-index]')" in sculpt
    assert "rail.addEventListener('click'" in sculpt and "addColorTarget(entry.color)" in sculpt
    assert ".spb-easy-sculpt-palette > div { display: flex; min-width: 0; justify-content: flex-start;" in sculpt_css
    assert 'tabindex="0" role="button" aria-label="Choose a color on the original paint.' in sculpt
    assert "if (event.key !== 'Enter' && event.key !== ' ') return;" in sculpt
    assert "var addColorButton = $('spbEasySculptAddColor')" in sculpt and "addColorButton.focus()" in sculpt
    assert "var targetButton = addedTarget && $('spbEasySculptScope-' + addedTarget.id)" in sculpt
    assert ".spb-easy-sculpt-source-figure img:focus-visible" in sculpt_css
    assert 'class="spb-easy-sculpt-scope-picker"' in sculpt
    assert ".spb-easy-sculpt-scope-picker > .spb-easy-sculpt-scope.add" in sculpt_css
    assert "if (state.showSpecMap)" in sculpt and "mapButton.focus()" in sculpt
    assert "nextMap.focus()" in sculpt, "Material-map disclosure must return keyboard focus to its opener."
    assert "spbEasySculptBigToggle" in sculpt and "state.showBigResult = !state.showBigResult" in sculpt
    assert "if (state.showBigResult)" in sculpt and "bigButton.focus()" in sculpt
    assert "is-big-result" in sculpt_css, "The real painted result needs a clutter-free large view."
    assert "spb-easy-sculpt-map-figure" in sculpt_css and "grid-column: 1 / 6" in sculpt_css
    for element_id in ("spbEasySculptSpecAll", "spbEasySculptSpecR", "spbEasySculptSpecG", "spbEasySculptSpecB"):
        assert element_id in sculpt
    for label in ("COMBINED", "RED &middot; METAL", "GREEN &middot; ROUGH", "BLUE &middot; COAT"):
        assert label in sculpt
    assert "function drawSpecProofChannels" in sculpt and "context.getImageData" in sculpt
    assert ".spb-easy-sculpt-channel-grid" in sculpt_css
    map_proof_css = sculpt_css[sculpt_css.index(".spb-easy-sculpt-map-proof {"):sculpt_css.index(".spb-easy-sculpt-map-proof:hover")]
    assert "justify-content: flex-start" in map_proof_css
    assert "Easy means readable at a glance" in sculpt_css
    assert "libraryScrollTop: state.libraryScrollTop" in sculpt and "state.focusReturnLookKey = lookKey(selected)" in sculpt
    assert "state.libraryScrollTop = 0;" in sculpt, "A recovered plan must reopen with its edit/install controls visible."
    assert "clearRecoveryPlan();" in sculpt, "Choosing a different paint must intentionally start clean."
    assert "spbEasySculptReplaceFile" in sculpt
    assert "Only a confirmed, supported" in sculpt and "change.addEventListener('click', function ()" in sculpt
    assert "Sculpt another paint" not in sculpt
    assert "useCustomNumberCheckbox" in sculpt and "function liveUseCustomNumber" in sculpt
    assert "INSTALLED + LOCKED IN" in sculpt and "deployed.verified !== true" in sculpt
    assert "function materialPlanName" in sculpt and "SAVE TO iRACING" in sculpt
    assert "colorTargetName(target) + (target.replacementColor ? ' → ' + target.replacementColor.toUpperCase() : '') + ' is ' + target.look.name" in sculpt
    assert "var lookName = materialPlanName();" in sculpt
    assert "_spbEasySculptSpecOverride" in sculpt and "activateSculptSpecOverride(durableSpecPath" in sculpt
    assert "deployedNames.length === 2" in sculpt and "verifiedNames.length === 2" in sculpt
    assert "deployed.car_folder" in sculpt and "deployed.iracing_id" in sculpt
    assert "payload.use_custom_number === expectedUseCustomNumber" in sculpt
    assert "Nothing will be called DONE" in sculpt
    assert "verified iRacing copy, not the temporary" in sculpt
    assert "dataset.spbEasySculptSpecPath" in sculpt and "dataset.spbEasySculptSpecPath" in main_render
    assert "Spec Sculpt lock active" in main_render and "serverZones.splice(0, serverZones.length)" in main_render
    assert '"verified": True' in server and "Copy verification failed" in server
    assert "TRY ANOTHER" not in sculpt
    assert "KEEP THIS LOOK" not in sculpt
    assert "state.accepted" not in sculpt
    assert "INSTALLING YOUR SPEC" not in sculpt
    picker_body = sculpt[sculpt.index("function lookPickerHtml"):sculpt.index("function progressReceipt")]
    assert "data-drama" not in picker_body, "Advanced numeric tuning must not crowd the guided library."
    assert "look.kind + ':' + look.id" in sculpt, "Named look identity must drive selection, not seed-only rerolls."
    assert "look.swatchType || 'material'" in sculpt, "Duplicate base/special IDs must remain individually selectable."
    assert "var LOOK_PAGE_SIZE = 60" in sculpt
    assert "content-visibility: auto" in sculpt_css and "contain-intrinsic-size: auto 70px" in sculpt_css
    assert ".spb-easy-sculpt-big-toggle," in sculpt_css and "#spbEasySculptEditTarget { min-height: 30px; }" in sculpt_css
    assert ".spb-easy-sculpt-library-tabs [data-look-kind]," in sculpt_css
    assert '.spb-easy-sculpt-linked-scale input[type="range"] { min-height: 24px; }' in sculpt_css
    assert "function lookCategoryDescription(name)" in sculpt
    assert 'data-look-category="' in sculpt and "spb-easy-sculpt-category-list" in sculpt
    assert "state.libraryCategory === category ? '' : category" in sculpt
    assert "libraryCategory: state.libraryCategory" in sculpt and "payload.libraryCategory" in sculpt
    assert ".spb-easy-sculpt-category-title" in sculpt_css and ".spb-easy-sculpt-category[open]" in sculpt_css
    assert "lookMaterialKey(look) !== current" in sculpt, "Surprise Me must exclude the currently selected material, including duplicate registry cards."
    assert "function lookMaterialKey" in sculpt
    assert "Registry type is part of the material identity" in sculpt
    assert "return lookKey(look);" in sculpt, "Registry-qualified catalog cards must remain distinct material choices."
    fork_body = easy[easy.index("function renderForkRail"):easy.index("function renderWholeRail")]
    assert "saveBlockHtml" not in fork_body, "Export identity must not appear before a path is chosen."
    assert "spbEasyForkOriginalSculpt" in fork_body
    assert "CURRENT MATERIAL PLAN READY" in fork_body and "CONTINUE SPEC SCULPT" in fork_body
    assert "Return without rebuilding anything" in fork_body
    assert "css/spb-easy-sculpt.css?v=" in html
    assert "js/features/spb-easy-sculpt.js?v=" in html
    assert "js/features/spb-easy-sculpt-guidance.js?v=" in html
    for control_name in (
        "Paint emphasis strength", "Hue match width", "Procedural seed",
        "Source paint hue shift", "Metallic channel gain", "Procedural detail intensity",
        "Interior flatten", "Void roughness floor", "Surface detail amount", "Style blend mix",
    ):
        assert 'aria-label="' + control_name + '"' in original
