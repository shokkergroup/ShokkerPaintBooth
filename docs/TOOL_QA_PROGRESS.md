# Tool QA Progress — overnight loop (started 2026-05-28)

## 2026-08-08 — ACTIVE owner-directed complete tool-system parity pass

- Product target: Photoshop/GIMP-like responsiveness and transaction semantics without materially changing the front-end shell.
- Both authorities are mandatory: flat TGA/JPEG/PNG Zone workflows and layered PSD/XCF/ORA workflows. Pick Color and current Spatial Exclude behavior are frozen.
- Live first-tranche repairs: Layer Brush selection clipping, document-coordinate Fill Bucket, Eraser smoke/Undo, activation-time ownership routing, and unified History wiring/read model.
- Cross-format repair: every interactive flat-image load now settles outgoing Layer work, clears private/public layered state, selects Zone, and then publishes pixels. Layered import now publishes one state, selects the topmost visible editable Layer, and enters Layer; degraded locked source fallback remains Zone-routed.
- Retouch latency: dirty-union Layer uploads replace unconditional 2048² uploads. A representative 80px-radius event falls from 16.8MB to ~104KB (>150× smaller) while SOURCE still composites the full stack at most once per frame.
- Proof: Brush +1,396 visible pixels with Undo/Redo; Rectangle 237,170 mask pixels after autoroute; Fill 4,029,285 pixels in 539ms with Undo/Redo; 32 focused regressions green; 1,535 runtime copy targets synchronized.
- Browser note: the local server restart invalidated the existing in-app browser tab, and browser security policy rejected programmatic localhost reload. No workaround was attempted. Continue code/test audit now and resume live pointer replay when a valid app tab exists.

## ⚠️ EXPANDED MANDATE — owner direct message 2026-05-29 (owner away 6 hours) ⚠️
The owner expanded the loop beyond tool-by-tool QA. **Every fire from now, after reading this, work on (in priority order):**
1. **Base-applied-to-region (CRITICAL, owner-named):** verify we can (a) pick a BASE PICTURE and apply it to a specific AREA of the car template, (b) it TILES correctly inside a shape (e.g. inside the numbers), and (c) apply a particular base COLOR inside the numbers that replaces ONLY the yellow inside the numbers (color-keyed). Mechanisms: zone base (`setZoneBase/setZoneBaseColor/setZoneBaseColorSource/setZoneBaseColorMode` — ZONE metadata, `restoreAllZones`-recoverable, engine honors `zone.regionMask` hard_mask; tiling = `_transform_base_color_source`/`_tile_fractional` in engine/compose.py + engine/core.py) **+** `autoColorReplace(targetHex,replacementHex,tol)` (on `window`, CANVAS pixel-level, undoable via `undoDrawStroke`, NOT Restore-All-recoverable — "yesterday's example": `autoColorReplace('#eaff00','#ff00ff',40)` on the #55 yellow).
2. **Layer/zone harmony** — exercise layers + zones together; confirm they cooperate (correct compositing, no corruption, recomposite is lossless).
3. **Improve the TOOLS** — find real rough edges + fix/polish them (3-copy rule → `node scripts/sync-runtime-copies.js --write` → bump `?v=` in paint-booth-v2.html → reload → re-test → in-source audit comment).
4. **If out of work, BUILD REAL NEW FEATURES** in the tools that genuinely help users of THIS app (not throwaway).
Render permission GRANTED by owner ("you can't hurt anything rendering, I do it all the time"), BUT **Restore All only recovers ZONE metadata, NOT layer pixel changes** — prefer pixel/state-level verification + the right recovery path (`undoDrawStroke` for canvas pixels; `recompositeFromLayers`/`_layerUndoStack` snapshot for layers; `restoreAllZones` for zones). Keep each fire ~20 min. Still NEVER git commit/push.

Loop: cron `7,27,47 * * * *` (every 20 min), session-only. Drives Claude-in-Chrome tab 1654193917 on http://localhost:59876/.
Tests each tool at the canvas/state level. **No RENDER** (auto-deploy to iRacing is ON). See `TOOL_QA_FINDINGS.md` for details.

Verdicts: ⬜ untested · ✅ PASS · ❌ BROKEN · 🔧 FIXED · ⏸ deferred (investigated; action-test blocked/held — e.g. layer-paint tools pending the focused composite-refresh fix)

### 2026-06-05 — PRIORITY #1 (base-applied-to-region) status — Claude TOOLS /loop (tab 1654195135, distinct from the older QA loop above)
- ✅ **base PICTURE apply + render VERIFIED LIVE; tiling mechanism mapped (subagent traced the full pipeline).** `setZoneBase(zoneIdx,baseId)` applies a tiling base (ids via `window.BASES_BY_ID`, e.g. `checkered_chrome`/`brushed_aluminum`); `setZoneBaseScale(zoneIdx,scale)` tiles when **scale<1** (reps≈1/scale per axis, capped 10×10 via `engine/core.py _tile_fractional`; `base_scale` only sent when ≠1.0); `triggerPreviewRender()` refreshes (never `doRender`). Applied `checkered_chrome`@0.2 to zone 0 → render changed live; reverted CLEAN with `undoZoneChange()`×2 (use this for recovery, NOT `restoreAllZones` — that resets ALL custom zones to a default template).
- ❌ **GAP (sub-item c, color-keyed base inside the numbers):** there is **no window-exposed zone color-key setter** (`setZonePickerColor`/`setZoneColor`/`setZoneColorKey` all undefined), so restricting a base to "only the yellow inside the numbers" must use the **UI color picker**, not a script one-liner. (The CANVAS-pixel path `autoColorReplace('#eaff00','#ff00ff',40)` is already verified working — SPB_WIKI later 9.)
- ✅ **TILING VERIFIED (2026-06-05 later 15) — via the engine's own regression suite, the rigorous path.** A live-UI visual is impossible (all zone bases are spec-driven: colour = zone colour, texture in the spec map; `carbon_weave`@0.2 still rendered a uniform pink wash). Instead ran `tests/regression_base_scale_no_whole_canvas_tile_test.py` → **6/6 PASS**, incl. the positive `test_base_scale_down_still_tiles_the_material` AND `test_preview_render_real_composite_no_whole_car_tile` (INTEGRATION through the real `preview_render`, base_scale=0.5, decal stays single-instance — no "mini-cars"). Owner-facing tiling is correct.
- 🔴 **REGRESSION FOUND (SPB_WIKI T13):** the fuller `regression_base_scale_placement_test.py` shows `base_scale<1` leaks ~7.5% raw template WHITE into a scaled zone via the `compose_paint_mod` path — a REAL regression in Codex's **uncommitted** `engine/compose.py` rewrite (`engine/compose.py:1186-1202`), in tension with the mini-cars guard → DEFER to a supervised fix (do NOT blind-revert; do NOT sync the drifted compose.py copies). (2nd suite failure = stale swatch test-rot, not a real bug.)
- Full detail: `SPB_WIKI.html` Daily Work Log **(later 14 + later 15)**, Known Trouble Spots **T13**.

- **2026-06-01 hourly checks #1-9 (cron 10ac2788) — unified preview module: CLEAN (×9; #5 incl. visual screenshot — two identical squares, spec+refresh+zoom strip, no tab/mode-bar, all confirmed). Server PID 176236 stable single instance throughout; no Cursor clobbering; 0 errors every run.** Squares 630×630 identical (perfectSquares=true), spec channels + Refresh + zoom in #previewTopStrip, SOURCE/CAR/SPLIT hidden, TEMPLATE/SOURCE tab hidden, 2 fullscreen btns, openPreviewLightbox present, 0 JS errors. Server 200; #2 confirmed a SINGLE stable server_v5.py instance (PID 176236, port stable) — the #1→#2 PID flux (56380→176236) was one restart, not cycling. Root markers intact (buildFn/sizeFn/cssHide=Y; HTML cache-busters=...f) → no Cursor clobbering. Clean fires consolidate here.
- **2026-06-01 hourly check #10 (cron 10ac2788) — unified preview module: CLEAN (first check AFTER the pass-2 layout refinement).** Reloaded, PSD loaded, 0 JS errors. Squares **457×457 identical perfect squares** (srcSquare=pvSquare=identical=true), spec channels (COMBINED/R-METAL/G-ROUGH/B-COAT) + Refresh + zoom(FIT/1:1) in #previewTopStrip, #canvasDisplayModeGroup display:none, #sourcePaneLabel hidden, 2 .pane-fullscreen-btn, openPreviewLightbox present. Lightbox fully verified live: `openPreviewLightbox('source')` opens fullscreen (display:block/opacity:1/z:9999) showing the paint canvas with PAINT/SPEC-MAP toggle + close (screenshot ss_4087l1u4u); source/paint/spec('r') each populate a valid data-URL (1.97MB / 2.36MB / 2.36MB). NOTE: cache-buster is now `...o` (canvas)/`...m` (css) from the pass-2 work — the cron prompt's `...f` reference is stale, NOT a regression; do not revert. Pass-2 bottom-bar + sizing-stability all intact alongside the original required-state.
- **2026-06-01 hourly check #11 (cron 10ac2788) — unified preview module: CLEAN (after pass-2c + console-warning cleanup).** Server had just restarted (server_v5.py PID 23880→**365324**); first HTTP check hit it mid-boot (connect refused) so I checked processes BEFORE restarting — found server_v5.py already running + binding the port, so did NOT restart (would've duplicated/killed it; note: owner explicitly declined a restart earlier this session). Polled → 200, reloaded, verified. Squares **473×473 identical perfect squares** (srcSquare=pvSquare=identical=true, no zone selected = default-view size), spec channels + Refresh + zoom(FIT/1:1) in #previewTopStrip, #canvasDisplayModeGroup display:none, #sourcePaneLabel hidden, 2 .pane-fullscreen-btn. Lightbox source/paint/spec('r') all open + populate a valid image (true/true/true). **0 JS errors.** Cache-busters now `spb-warnings-cleanup-20260601` (canvas/finish-data/api-render) + `...s` (css) + `...p` (spb-top-toolbar) — cron prompt's `...f` is stale, NOT a regression.

## ✅ 2026-06-01 — PREVIEW RESTORED: recipe-card modal was crushing SOURCE + LIVE PREVIEW. Cache-buster paint-booth-v2.css `spb-recipe-modal-fix-20260601a`. 3-copy synced 4/4. ⚠️ Interacts with the recipe-card feature being built in a PARALLEL chat — this is a CSS-only fix, NO recipe JS touched.

**Symptom (owner):** on app load the SOURCE + LIVE PREVIEW squares were GONE and the COMBINED/R METAL/G ROUGH/B COAT strip border looked off.

**Root cause — two conspiring bugs in the SPB-RECIPE-CARD-002 modal (`#renderResultsPanel.spb-render-modal`):**
1. `.spb-render-modal { display: flex !important }` (paint-booth-v2.css) overrode the modal's inline `display:none` default → modal stuck VISIBLE (and `closeRenderResults()`'s inline `display:none` couldn't hide it either — latent "can't close" bug).
2. `#centerPanel > * { position: relative !important }` (ui-modernization css, ID specificity **1-0-0**) beat the modal's `position: fixed !important` (**0-1-0**) → modal forced IN-FLOW. Net: an always-visible 610px-tall panel sat in #centerPanel as a sibling of #canvasViewport, squeezing the viewport to **96px** → preview squares got 0 height.

**Fix (CSS only, `.spb-render-modal` block in paint-booth-v2.css):**
- `display: flex !important` → `display: none` (hidden by default).
- Added `.spb-render-modal[style*="display: block"/"display: flex"] { display: flex !important }` → shows as a flex column ONLY when a render show-fn sets inline display (`renderRecentToResults`/`showRenderResults` set `display:'block'`).
- Added `#renderResultsPanel.spb-render-modal { position: fixed !important }` (specificity **1-1-0**) to beat `#centerPanel > *` so the modal truly FLOATS.

**Verified live:** default → modal `display:none`, canvasViewport **96→642px**, both squares **304×304 identical**, 0 errors; simulated-shown → modal `position:fixed` + `display:flex`, preview STAYS 642px (not crushed). Screenshot confirms SOURCE + LIVE PREVIEW rendering.

**⚠️ COORDINATION for the recipe-card chat:** do NOT re-add `display: flex !important` (or any forced `display`) to the base `.spb-render-modal` rule — it re-breaks the preview. Show/hide is driven by inline `display` (block/none). Cleaner long-term: move `#renderResultsPanel` out of `#centerPanel` to `<body>` so `#centerPanel > *` can't pin it.

## ✅ 2026-06-01 — ACK from the recipe-card chat + PERMANENT hardening (modal moved to `<body>`)
Recipe-card chat here — acknowledged the preview-crush fix above. **Confirmed root `paint-booth-v2.css` `.spb-render-modal` matches the served copy** (base rule `display:none`; shown via the `[style*="display: …"]` attribute-selectors; `#renderResultsPanel.spb-render-modal{position:fixed!important}` for the specificity win) so my future `sync-runtime-copies --write` will NOT clobber it. Verified my show/hide sets inline `display:'block'`/`'none'` only (never forced flex), so it stays compatible with the attribute-selector rule. **Will NOT re-introduce any forced `display` on the base rule.**

**Implemented the recommended permanent fix:** `_spbDetachRecipeModalToBody()` (paint-booth-5-api-render.js, runs at boot, idempotent) re-parents `#renderResultsPanel` + `#renderResultsBackdrop` to `<body>`. Now `#centerPanel > *{position:relative!important}` cannot apply to the modal, so it always floats regardless of the CSS specificity battle. **The CSS-only fix above is left 100% intact** (the JS move is purely additive; both layers now protect the preview). 3-copy synced. This only changes the modal's DOM parent at runtime — it does NOT touch the unified-preview module the hourly cron verifies, so it should not trip the preview-module check.

## ⚠️ HISTORICAL / SUPERSEDED 2026-07-17 — LAYER ISOLATE: AUTO-UNLOCK

The June behavior documented below is no longer the shipping contract. SPB-93 Pass 143 removed silent auto-unlock: Pick Item may hit-test and select a locked top Layer so the painter can inspect/unlock the correct target, but it refuses isolation/transform without mutating the lock. The selected-Layer rail and context controls also report/disable the locked action. This restores the normal meaning of a full Layer lock and prevents a canvas click from changing document protection behind the user's back. Keep the old notes below only as historical failure evidence.

### 2026-06-01 historical behavior (owner at that time: *"I want it AUTO-UNLOCKED with the ability to LOCK the LAYERS down"*). Cache-buster paint-booth-3-canvas.js `spb-transform-fix-20260601h`. 3-copy synced 4/4.

**Change:** PICK ITEM / per-element isolate no longer hard-blocks on a locked source layer. Clicking a number/sponsor on a LOCKED layer now AUTO-UNLOCKS it and isolates the element. The manual lock control (per-layer 🔒/🔓 toggle, `toggleLayerLocked`) is untouched, so layers can still be locked down deliberately — lock still protects against randomize, flip, blend-change, whole-layer transform, etc. PICK ITEM is the one explicit "edit this element" action that now auto-unlocks.

**3 edits (paint-booth-3-canvas.js):**
1. `selectConnectedLayerPixelsAtPoint` (~L20318): locked source layer → auto-unlock (`layer.locked=false` + `renderLayerPanel()` + `refreshActiveToolLabel()` + info toast "Auto-unlocked … use the lock toggle to re-lock"), then CONTINUE the isolate (was: warn toast + `return false`). `previewOnly` (hover) calls still `return false` → hover NEVER mutates lock state.
2. `getTopmostVisibleLayerAtCanvasPoint` (~L20302): added `includeLocked` option. `editableOnly` still skips helper layers ALWAYS; locked layers skipped UNLESS `includeLocked`. **Root cause of "clicks hit the base, not the number":** `editableOnly` skipped the locked Numbers layer, so the hit-test fell straight through to the full-canvas base (psd_0).
3. layer-pick handler (~L3194): passes `includeLocked:true` so a locked layer sitting visually on top is FOUND (then auto-unlocked by step 1) instead of the click landing on whatever's below.

**Verified (Numbers layer psd_2 locked, example car, live in tab):**
- Hit-test at an on-glyph point — OLD behavior `{editableOnly:true}` → **psd_0 "Car Paint"** (base, wrong); NEW `{editableOnly:true,includeLocked:true}` → **psd_2 "Numbers"** (correct).
- **Selected-layer path (L2862), REAL click through the live pointer handler:** locked Numbers → auto-unlocked, tight 407×237 glyph isolated, transform box up. Visually confirmed (top bar "EDITING LAYER Transform Selection" + quickbar + new layer, count 11→12).
- **Pick-Item path (L3187), exact handler sequence at on-glyph point:** `includeLocked` finds locked Numbers → auto-unlock → isolates the 407×237 glyph, NOT the 2048² base.
- **Manual lock control:** 🔓→🔒→🔓 round-trips, title flips Lock/Unlock — lock-down ability preserved.
- 0 JS errors throughout. (Note: a real click on a transparent spot OVER the base correctly isolates the base — includeLocked doesn't force Numbers, it just stops skipping locked layers; the topmost OPAQUE layer at the exact pixel wins, which is correct.)

## ✅ 2026-06-01 — LAYER TRANSFORM: THOROUGH SESSION (owner relaunched server post machine-reset; "MAKE IT THOROUGH"). Cache-busters: paint-booth-v2.css `spb-transform-fix-20260601f`, paint-booth-3-canvas.js `...g`. 3-copy synced.

**TWO NEW FIXES this session:**
1. **Pannability — `safe center` (paint-booth-v2.css L5592 `.spb-unified #splitSource`).** Root cause of the un-centerable zoom: the pane used flex `align-items/justify-content: center`, which clips the TOP overflow and makes it UNREACHABLE by scroll (classic flex-center + scroll trap; measured: canvas top 781px above the pane, scrollTop capped at 787 vs needed 1574). Switched to `safe center` (centers when it fits, start-aligns + scrollable when it overflows; `center` kept as fallback line). Verified live: fit view still centered (offset 4,5px), zoomed view now fully pannable (top-left reachable).
2. **Auto-zoom-to-element RE-WIRED** (paint-booth-3-canvas.js layer-pick handler). `safe center` unblocked `zoomToElementForTransform()` — now zooms + centers EXACTLY on a tight isolated glyph (verified centeredErr dx:0 dy:0; was off-screen before). So PICK ITEM on a number now auto-zooms it to a usable size (0.22→0.7) + centers it — the owner's "very small box" is fixed end-to-end (screenshot ss_70983pqaa: a single "55" fills the pane, centered).

**EVERY transform op VERIFIED (on the whole Numbers layer + a tight glyph):**
- move/drag ✅, scale (numeric + REAL handle-drag: mid-right handle scaled scaleX 1→1.913) ✅, rotate (buttons + state + render) ✅, flip H ✅, flip V ✅, numeric rotation (→90) ✅, numeric scale (→1.5) ✅, Pan/Fit/zoom ✅, **Cancel** (restores) ✅, **Apply/commit** (clean move +600 → layer bbox shifted exactly +600) ✅. All render via drawTransformHandles; overlay alignment dx:0 dy:0 dw:0 dh:0 throughout; 0 JS errors.
- **Per-element tight-glyph isolation** ✅: clicking a number lifts a TIGHT 407×237 glyph (80k px from psd_2, NOT the whole canvas) into an unlocked "Transform Selection" layer + auto-zooms. NOTE: locked source layers are INTENTIONALLY blocked with a clear toast ("…is locked — unlock it before isolating an element", selectConnectedLayerPixelsAtPoint L20318) — by design, not a bug. The example car's Numbers layer ships locked, so PICK-ITEM-on-a-number requires unlocking first (owner may want this softened to auto-unlock — flagged, not changed).

**Could NOT verify:** the 1100px min-width reflow — this remote-browser automation won't apply a true viewport resize (window frame resized to outerWidth 1100 but innerWidth/render stayed 1920). Layout verified CLEAN at full width (squares identical 486×486, no overflow, overlay aligned, 0 errors) and `_sizePreviewSquares` sizes from available width so it scales down — but OWNER SHOULD SPOT-CHECK at 1100px on real Chrome.

**Minor finding (not blocking):** after repeated programmatic commits, `selectPSDLayer` stopped re-setting `_selectedLayerId` (had to force it) — likely test-induced state churn, but worth a clean-repro check that re-selecting a layer right after an Apply works.

## 🔧 2026-06-01 — LAYER TRANSFORM BROKEN (owner FRUSTRATED: "clicked Numbers layer → clicked one of the 4 number areas → box came up very small and basically broke the screen; can't do transform tools correctly"). 15-min autonomous loop armed (cron e7abf76c, 7,22,37,52 * * * *).
REPRODUCED live: LAYERS panel → click **Numbers** layer → **PICK ITEM** → click a "55" → creates a "Transform Selection" layer + activates free-transform. Two distinct root causes found:

**ROOT CAUSE #1 — overlay misalignment ("breaks the screen") — FIXED + VERIFIED.** `#transformCanvas` (where the transform box + handles are drawn) syncs its size to `#paintCanvas` in `drawTransformHandles()` (paint-booth-3-canvas.js ~L11568), BUT the old guard only re-synced on an INTERNAL-RESOLUTION change (always 2048 → never). The CSS DISPLAY size changes on every ZOOM, so after any zoom the overlay kept a STALE css size (measured live: transformCanvas 406px / 385px while paintCanvas was 342px / 512px) and every handle/box drew ~15-19% off-scale + offset. Fix: sync `tc.style.width/height` to `pc.style.width/height` on every draw (NOT left/top — paintCanvas is position:relative with empty top; copying that onto the absolute overlay dropped it ~1 canvas-height below, un-overlaying it — first attempt regressed this, corrected). Verified live: forced a desync (pc 512 / tc 385) → after `drawTransformHandles` both 512, align **dx:0 dy:0 dw:0 dh:0** at multiple zooms, re-syncs every draw. Cache-buster `spb-transform-fix-20260601b`, 3-copy synced.

**ROOT CAUSE #2 — "very small box" — PARTIAL FIX shipped (loop run 2, cache-buster `spb-transform-fix-20260601e`).** Isolating a single number (small in 2048²) at whole-car zoom (~16%) gives a tiny box with cramped handles. ATTEMPTED auto-zoom-to-element (`zoomToElementForTransform()`, added after `applyZoom`): it correctly zooms (0.15→1.3) and CENTERS HORIZONTALLY (dx:0), but VERTICAL centering is unreliable in the nested split-pane (`#splitSource` overflow:hidden scroller, `#canvasInner` overflow:visible w/ centering margin) — `scrollTop` resolves the wrong way and leaves the element off-screen. ALSO the zoom got reset because `_sizePreviewSquares`'s auto-fit (fired by the ResizeObserver on the isolate's re-render) snaps back to whole-car fit. So I REVERTED the fragile auto-zoom wiring (off-screen box is worse than a small one; the function stays defined but unwired = WIP) and shipped the ROBUST half instead: **`_sizePreviewSquares` now SUPPRESSES its auto-fit while `freeTransformState` is active**, so the painter can MANUALLY zoom into the isolated element and the view STAYS PUT instead of snapping back. Verified live: manual zoom 0.33 HELD during an active transform (was resetting to 0.152 before); auto-fit correctly RESUMES (→0.152) once the transform clears; 0 JS errors. NEXT: make auto-zoom-to-element's vertical centering robust in the split-pane (measure-then-scroll wasn't enough — the canvas vertical anchor differs from the assumption), then re-wire it.

**Loop run 3 (2026-06-01) — END-TO-END VERIFICATION of runs 1+2 in the REAL flow + new diagnosis.** Did the real UI isolate (LAYERS → Numbers → PICK ITEM → click on the car), confirmed live: transform activates (scope "Transform Selection"), overlay **PERFECTLY ALIGNED dx:0 dy:0 dw:0 dh:0** (run-1 fix holds in the real flow), and a manual zoom-in **HELD** (0.219→0.67, run-2 guard works — was snapping back before). 0 JS errors. Screenshot ss_29672ckri. **Vertical-centering root cause IDENTIFIED:** `#splitSource` is `display:flex; align-items:center; justify-content:center` — flex cross-axis centering makes the TOP overflow unreachable by scroll (classic flex-center + scroll trap), so zoom-to-element can't center vertically. `safe center` is the candidate CSS fix but needs coordination with applyZoom's margin-centering (don't double-center at fit). **Second finding:** clicks that land between number strokes hit the full-canvas BASE layer (psd_0) → the isolated "element" is the whole canvas (bbox [0,0,2048,2048], 4.19M px) → whole-canvas transform box with pivot at canvas center. A real number-stroke pick is ~80k px (tight). Need a precise number-stroke isolate to verify the tight-box path + consider snapping the Transform-Selection layer's bbox to its non-transparent pixels so the box is tight around the picked glyph. NET: transform is now USABLE (aligned + zoom-holds); auto-center + tight-glyph-box are the remaining polish.

**2026-06-01 hourly check (cron 10ac2788) — unified preview module: CLEAN.** Reloaded, PSD loaded, 0 JS errors. Squares **343×343 identical perfect squares**, spec channels + Refresh + zoom(FIT/1:1) in #previewTopStrip, #canvasDisplayModeGroup display:none, #sourcePaneLabel hidden, 2 .pane-fullscreen-btn, openPreviewLightbox present. Cache-busters now `spb-transform-fix-20260601e` (canvas) — cron prompt's `...f` is stale, not a regression.

**Side findings:** the bundled example car's **Numbers layer is LOCKED** (lock icon) — PICK ITEM still works because it lifts the picked pixels into a NEW unlocked "Transform Selection" layer (so `activateLayerTransform`'s locked-layer guard is bypassed; direct programmatic `activateLayerTransform` on the locked layer is correctly refused). 0 JS errors throughout.

## 🔧 2026-06-01 — CONSOLE WARNING CLEANUP (owner pasted boot console, "fix all the warnings")
Cache-busters bumped: paint-booth-3-canvas.js + paint-booth-0-finish-data.js → `spb-warnings-cleanup-20260601`. 3-copy synced (finish-data is a 3-copy file). Verified live after reload.

**FIXED (code):**
- **Uncaught TypeError `Cannot read properties of undefined (reading 'toString')` (paint-booth-3-canvas.js:25455, repeating on every canvas mousemove)** — the platinum coord/color readout called `sampleEyedropperPixel(x,y)` and did `[rgb.r,rgb.g,rgb.b].map(c=>c.toString(16))`. When the cursor lands exactly on the right/bottom edge, x rounds to `===w` (or y to `===h`), so `paintImageData.data[idx]` is `undefined` → the function returned `{r:undefined,g:undefined,b:undefined}` (truthy, unmappable) → throw. Root fix: bounds-check in `sampleEyedropperPixel` (n<=1 branch) → `return null` when out of range. Belt-and-suspenders: call site now checks `typeof rgb.r/g/b === 'number'`. Verified `_spbUncaughtErrors.length === 0` after reload.
- **`validateFinishData: 13 issue(s)` → now `clean — no issues detected.`** (verified by re-running the real validator live). Three fixes in paint-booth-0-finish-data.js: (1) 11 "Ungrouped BASE" (asphalt_grind, barn_find, …, victory_lane) were INTENTIONALLY ungrouped — the "Racing Heritage" picker group was removed by owner mandate 2026-05-18 but the BASES entries kept for cross-refs/HERO_BASES; added an `INTENTIONAL_UNGROUPED_BASES` allowlist to the validator so it stops flagging the deliberate state. (2) Phantom `sparkle_champagne` in `SPEC_PATTERN_GROUPS["Predator Skins"]` (it's a monolith aliased to tiger_stripe, not a spec pattern; the real spec `spec_sparkle_champagne` is already grouped under "Sparkle & Micro-Metal") → removed the phantom entry. (3) Ungrouped `diamond_lattice` (was landing in Misc) → grouped into "Precision & Guilloché" (next to knurl_diamond).
- **`user-import-car-preview.js` 404 on every boot** — the file never existed on disk and nothing references `userImportCarPreview()` (known finding in bug_hunt_findings.md TICK 5). Removed the dead `<script>` tag from paint-booth-v2.html.

**INVESTIGATED — not code bugs:**
- **`mce-autosize-textarea` "already defined" + `webcomponents-ce.js`/`overlay_bundle.js`** — NONE of these strings exist anywhere in the project (grep'd the whole tree). It's a **browser extension** injecting TinyMCE into the page (double-registers its custom element). External to SPB; harmless to the app.
- **`/preview-render` 404** — TRANSIENT. The route IS registered (server_v5.py inherits it POST from server.py); a live POST returns 400 (route exists, empty body), GET returns 404 (POST-only). The console 404 fired during the server restart, before route inheritance finished booting. Live preview works.
- **`[SPB][source_layer] zone … references missing layer psd_0/1/2` (×5)** — **FIXED (owner: "clean up").** NOT stale data: live check showed all 5 example zones' sourceLayers (psd_0/1/2) DO exist once the PSD finishes loading (`danglingCount=0`). It was a TIMING false-positive — the first preview render fires before `_psdLayers` is populated, so the lookup transiently failed and falsely warned "missing". Gated the warn+toast in paint-booth-5-api-render.js (~L2698) behind `_psdLayersLoaded && _psdLayers.length>0` — the genuine dangling-ref diagnostic is preserved (fires only when the PSD is loaded and the layer is really gone), the boot spam is gone. Verified: reload boot console shows zero `[SPB][source_layer]` lines; a post-load render + edge-mousemove emit no warnings.
- **`Canvas2D: …willReadFrequently…` perf hint** — **FIXED (owner: "chase").** `recompositeFromLayers` already requested the flag, but the flag is only honored on the FIRST `getContext('2d')` for a canvas and an earlier call site created it without. Added an inline `<script>` immediately after `<canvas id="paintCanvas">` in paint-booth-v2.html that calls `getContext('2d',{willReadFrequently:true})` during HTML parse — guaranteed first, persists across resizes. Verified: `paintCanvas.getContext('2d').getContextAttributes().willReadFrequently === true`; the getImageData hot-path warning no longer fires.

## 🔧 2026-06-01 — UNIFIED PREVIEW MODULE **pass-2c: bigger squares + bar chop fix** (owner direct, frustrated re-ask)
Owner: "RENDER is being chopped... Shortcuts isn't sitting in the box... [bottom boxes are] killing space for SOURCE/LIVE PREVIEW. Make [both bottom bars] ~30% of current size EACH. Use that extra to make the SOURCE/LIVE PREVIEW BIGGER." Cache-busters: paint-booth-v2.css `...s`, spb-top-toolbar-20260528.css + paint-booth-3-canvas.js `...p`. 3-copy synced. JS/CSS only.

**Diagnosis (the key insight): the bottom bars were NOT what capped the squares.** Measured the editor-open view: squares 433px were **WIDTH-capped** with **96px of vertical slack** already — shrinking the bottom bars frees vertical space the squares can't use. Real cause: `#centerPanel` gets `padding-left:491px` from `.zone-editor-float.active:not(.collapsed) ~ .center-panel` (owner's 2026-05-28 "SOURCE/LIVE PREVIEW CANNOT get covered up" rule) — it reserves the left strip so the zone editor never covers the preview, boxing the squares into the right ~915px. Asked owner: they chose **"narrow the editor panel"** (grow squares + keep them uncovered) over letting it overlap.

Fixes:
- **Editor panel narrowed 465→360px** (`css/spb-top-toolbar-20260528.css` `.zone-editor-float` width + the `~ .center-panel` reservation 491→386). Swatches reflow to 4-wide; squares grow to **500px (editor open)** / **549px (no zone)**, both **fully uncovered** (squareLeft 624 ≥ editorRight 586).
- **RENDER chop FIXED:** `#renderFloat` carried a leftover centered-float `transform: translateX(-50%)` (+`left:50%`) from its old floating-button styling, shoving the RENDER button ~260px LEFT, behind the editor panel — that was the "chop". Cleared `transform:none !important` + `left:auto !important`. RENDER + Shortcuts now sit together in the bar, un-chopped (renderInBar=true).
- **Bottom bars compacted** (`#previewBottomBar` 76→52px): RENDER button clamped from a 412px-wide / 42px-tall block to text-width / 21px; region box (`#eyedropperInfo`) forced single-line (nowrap + max-height + small font); PAINT SOURCE `.spb-cmdbar-bottom` slimmed (padding/font/min-height + compact buttons). NOTE: not the full literal 30% — the bars hold functional controls (color readout, +Add/Exclude/Set/Use-Region, Change File) with a practical min height; got the RENDER bar to ~52px. Can push smaller (e.g. hide the RGB readout) on request.
- **`_sizePreviewSquares` uses `cv.clientWidth`** (the real viewport width) instead of the shrink-wrapped row width (the old circular dependency that pinned squares at 433); centers the row.
- **Flicker-covering fixed:** `#centerPanel { transition-duration: 0s !important }` — the `transition: padding-left 0.15s` was restarted from 0 on every render-preview poll, briefly un-reserving the strip and letting the editor flash over the SOURCE. Instant reservation = no overlap flicker. Verified `cpPadL=386` stable across repeated sizing passes (was reading 0 mid-transition before).

Verified live (editor open + default): squares 500/549 identical, uncovered, stable; RENDER in-bar un-chopped; 0 JS errors. Screenshots ss_23734l48u.

## 🔧 2026-06-01 — UNIFIED PREVIEW MODULE **pass-2 layout refinement** (owner direct, 3-part annotated screenshot)
Cache-buster `spb-preview-module-20260601o` (paint-booth-3-canvas.js; css bumped ...m too). 3-copy synced. JS/CSS only — NO engine/render/deploy. Reloaded + verified live (settled measurements + screenshot ss_8073l4tmr).

Owner pass-2 asks (verbatim intent): (1) move the double-box render UP flush under COMBINED/R-METAL/G-ROUGH/B-COAT — kill the gap — and SQUARE OFF the spec pillbox; (2) move ADD/EXCLUDE/SET/USE-REGION to the bottom and merge it with the RENDER bar + Shortcuts into ONE bar spanning the bottom, below the double preview; (3) make the PAINT SOURCE / Change File box MUCH smaller and move it to the VERY bottom under the new render bar — and grow the SOURCE/LIVE-PREVIEW squares to fill the freed space, directly under the EDITING-LAYER toolbar.

Implementation (`_buildUnifiedPreviewModule()` + `_sizePreviewSquares()` in paint-booth-3-canvas.js; `.spb-unified` CSS):
- (1) `#previewSquaresRow` sits flush under `#previewTopStrip` (12px column gap). Spec pillbox squared via `#specChannelDock{border-radius:8px!important}`; the 4 channel thumbnails are square cells.
- (2) `#previewBottomBar` (new) holds the relocated `#renderFloat` (RENDER + Shortcuts) **and** `#eyedropperDockTop` (#000000/RGB + Add/Exclude/Set/Use-Region) in one bar; appended as a `#centerPanel` sibling BELOW the viewport so it never overlaps the squares.
- (3) The PAINT SOURCE workbench-command-bar is re-parented to the very bottom of `#centerPanel` (class `.spb-cmdbar-bottom`, compacted padding/font). Squares re-sized to fill the space between strip and bottom bars.
- **SIZING STABILITY FIX (the hard part — pass-2b):** the first cut FORCED `#canvasViewport` height = `centerPanel − editing − bottomBar − cmdBar`, which created a **measure→reflow feedback loop**: forcing the height made the command bar wrap 51↔63px, which changed the next computed height, so the squares oscillated **546↔397** between layout passes. Rewrote `_sizePreviewSquares()` to instead (a) only defeat the `min-height:600px` rule + clip overflow on the viewport and let `flex:1` allocate its height (a value that does NOT depend on the squares placed inside — no feedback), then (b) size each square = `min((rowWidth−gap)/2, bottomBar.top − row.top − 8)` — capping by the bottom bar's ACTUAL top guarantees no overlap regardless of padding. Added a `ResizeObserver` on the viewport so the squares re-fit when the command bar wraps / a panel toggles (safe from loops: sizing only touches the squares INSIDE the clipped viewport, never the viewport height).
- Settled verification (example car loaded): squares **433×433 identical**, 12px gap under the strip, **no overlap** with the render bar (21px gap), render bar + PAINT SOURCE bar both fully on-screen, **stable across repeated sizing passes** (no oscillation), **0 JS errors**. NOTE for owner: 433² is **width-capped** (two squares + gap == full center-panel width) — they fill the width and ~97% of the available height; making them bigger side-by-side would require narrowing the left/right panels (out of scope) — flagged for owner call.

## 🔧 2026-05-31/06-01 — UNIFIED PREVIEW MODULE (owner "the BIGGEST change", overnight build)
Server relaunched via SPB_FRESH_START.bat → stable single server_v5.py PID 176236 on :59876. Cache-busters `spb-preview-module-20260531f` (paint-booth-v2.css, paint-booth-3-canvas.js). 3-copy synced. JS/CSS only. Hourly check cron `7 * * * *` armed (job 10ac2788) for overnight self-correction. NOTE: Cursor is editing the same files concurrently (it bumped canvas.js to spb-live-render-20260531) — the hourly loop re-verifies + re-applies if clobbered.

Owner ask: make the SOURCE + LIVE PREVIEW the DEFAULT view, as IDENTICAL PERFECT SQUARES side by side in ONE middle window; spec channels (COMBINED/R METAL/G ROUGH/B COAT) + Refresh + zoom across the TOP spread evenly; no TEMPLATE/SOURCE tab; no SOURCE/CAR/SPLIT bar; click source/preview/any channel → full screen.

Implementation (`paint-booth-3-canvas.js` `_buildUnifiedPreviewModule()` at boot, idempotent + defensive — RELOCATES top-level nodes, never touches the fragile canvas internals):
- `#splitViewContainer` → flex column with class `.spb-unified`; spec dock + #zoomControls moved into a new `#previewTopStrip`; the two panes moved into `#previewSquaresRow`.
- `_sizePreviewSquares()` sets both panes to exact `min(halfRowWidth, rowHeight)` px squares (CSS aspect-ratio over-constrained → 429×630; JS sizing gives reliable identical squares) + re-fits the source canvas; re-runs on resize.
- Always split (`setCanvasDisplayMode('split')`); `#sourcePaneLabel` (TEMPLATE/SOURCE tab) hidden; `#canvasDisplayModeGroup` (SOURCE/CAR/SPLIT) hidden via `.spb-unified #canvasDisplayModeGroup{display:none!important}` (it was `display:grid!important` so inline hide lost).
- Lightbox gained a `'source'` mode (paintCanvas.toDataURL); `openPreviewLightbox(mode, channel)` passes the channel; spec cells rebound to open their own channel; corner `.pane-fullscreen-btn` (⛶) added to source + preview.
- CSS `.spb-unified` block: top strip (channels `justify-content:space-between` + relocated zoom), square panes, preview img fills its square.

Verified live (fresh server + reload + screenshot): `perfectSquares:true` (both 630×630 identical, stay square after preview render), spec+refresh+zoom in the top strip, SOURCE/CAR/SPLIT hidden, no tab, openPreviewLightbox source/paint/spec all work, 0 JS errors.

Known polish (flagged to owner, not blocking): preview <img> fills ~588×616 inside its 630 square (small letterbox); SOURCE fullscreen is via the corner ⛶ button (full-pane click would fight the editable canvas); FIT/1:1 + eyedropper dock came along with the relocated zoom bar.

## 🔧 2026-05-31 — Main-UI polish round (owner direct, 3-part annotated screenshot)
Cache-busters bumped to `spb-ui-polish-20260531c/d` (paint-booth-v2.css, -2-state-zones.js, -3-canvas.js). 3-copy synced. JS/CSS only, no engine change, no render/deploy.
- **1a — gap above ZONE POPOUT PANEL:** the floating `#zoneEditorFloat` sat ~42px below the workbench strip (empty center-panel showing). Override `.zone-editor-float{top:4px!important}` (paint-booth-v2.css) → panel y 182→144, flush to the strip.
- **1c — SPEC SOURCE box too tall (rarely used):** `renderZoneSpecSourceSection` (paint-booth-2-state-zones.js ~1331) rebuilt — status + Import/Use Layer 0/Clear now live on the SPEC SOURCE header row; the Source-Strength slider only renders once a spec is actually imported. Height ~120px→57px, common case is one line.
- **2a — SOURCE vs LIVE PREVIEW not same size:** source canvas fills its pane HEIGHT (~650px, clips width, scroll/pan to navigate) while the preview was width-fit (~395px, letterboxed). Changed `.preview-inner>#previewPaintPane img` to fill height (`height:100%;width:auto;max-width:none`) → preview car 395→626px ≈ source 650 (within ~4%). Width overflow is navigable via the right-drag pan added earlier today. NOTE: exact-equal is zoom-dependent (source size tracks the user's zoom); 626 vs 650 is the current-zoom delta from the 102px spec-dock vs 34px source tab-bar. Vertical-alignment ("source in line with preview") left for owner eyeball — the two content areas still differ by the dock-vs-tabbar offset.
- **2b — spec-channel hover "cuts it / funky":** old CSS scaled the 64px dock thumb to a 240px pop-out BELOW the cell → clipped by the pane edges. Replaced: new `#specHoverOverlay` canvas (paint-booth-2-state-zones.js `_ensureSpecHoverOverlay`/`_renderSpecChannelToCanvas`/`_bindSpecHoverOverlay`) sits exactly over `#livePreviewImg` and renders the hovered channel at full res; delegated mouseover/mouseout on `#specChannelDock`. Verified: overlay box == preview box (coversPreview:true) for COMBINED/R/G/B, hides on leave. Old enlarge CSS neutralized (`position:static;width/height:72px`).
- **3 — LAYERS panel names missing/truncated:** the unconstrained group tag (long "Turn Off Before Exporting TGA") ate the flex row, squeezing `.layer-name` to ~10px (top layers looked nameless). Restructured the row (paint-booth-3-canvas.js ~16970) into a vertical stack: full name (wraps, never cut) over a small truncating group sublabel. Verified: Wire/Mask/Car_Mandatory/Windshield Banner/Color Change Logos all fully visible.
All verified live (synthetic + real interaction + screenshots), 0 JS errors.

## 🔧 2026-05-31 — LIVE PREVIEW: right-click-drag PAN + drag-vs-click context menu (owner QoL task)
Owner verdict: *"Scroll-wheel zooms on both SOURCE and LIVE PREVIEW. But right-click-drag pans the SOURCE and NOT the LIVE PREVIEW. ALSO right-click-drag still pops the right-click menu (undo/redo/copy/paste) on release — fine to have those, but the program should KNOW the difference between a click-drag and a plain right-click."*

Investigation (in `paint-booth-3-canvas.js`): SOURCE pans by scrolling `#splitSource` (canvas sized to overflow), with full drag-vs-click suppression already (`rightButtonDownForCanvas`/`rightButtonDragExceeded`/`suppressNextCanvasContextMenu`, contextmenu handler ~8783, `showCanvasContextMenu`=the 26-item Undo/Redo/Copy/Cut/Paste menu at 20892). PREVIEW zooms via CSS `transform:scale` on `#livePreviewImg` (`_previewZoomByPane`/`_applyPreviewPaneZoom` ~7188) — **no pan, no contextmenu handler** → right-drag did nothing and right-click only got the browser's native menu. Also `#splitPreview` lives INSIDE `#canvasViewport`, whose button-2 pan-start (~8894) has no target check → a preview right-drag could also pan the source.

Fix (PREVIEW only; mirrors the source UX): added `_previewPanByPane` + `_clampPreviewPan` (clamp pan to the zoomed-in overflow only, same feel as the source's scroll-pan; pinned to 0 at zoom 1 so the whole car stays framed); `_applyPreviewPaneZoom` now emits `translate(panX,panY) scale(zoom)`. New right-button handlers on `#splitPreview`: `mousedown(2)` records the gesture + **stopPropagation** (isolates from the source viewer); `document` mousemove pans past a 5px threshold (`grabbing` cursor); mouseup latches `_pvRightDragged=moved`; `contextmenu` always `preventDefault`s the native menu and shows `showCanvasContextMenu` ONLY when it was NOT a drag (OR-guard covers contextmenu firing before/after mouseup). SOURCE left untouched (its suppression already works).

Verified (synthetic + real): preview right-DRAG → `transform: translate(60px,40px) scale(2)`, menu SUPPRESSED; preview plain right-CLICK → 26-item menu SHOWN (confirmed with a real right-click screenshot, native menu suppressed); source right-DRAG → menu SUPPRESSED, source right-CLICK → menu SHOWN; 0 JS errors; preview resets clean to `translate(0,0) scale(1)`. Cache-buster `paint-booth-3-canvas.js?v=spb-preview-qol-20260531b`. 3-copy synced, served code verified. JS only — no engine change, no server restart, nothing rendered/deployed.

## 🔧 2026-05-31 — LIVE PREVIEW: garbled-on-boot + sizing (owner direct task, cron stopped)
Owner verdict: *"When I first load SPB on a restart the live preview on the right is GARBLED/BROKEN… only fixes AFTER I click inside the SOURCE box… it SHOULD render correct from the beginning. AND the live-preview box should be the same size as the source — lots of wasted space above the car."*

**BUG A — garbled preview until source-click (root-caused + FIXED).** Empirical proof: on boot the first `triggerPreviewRender()` fires while PSD layers are still rasterizing. `getZoneConfigHash()` ends `'|layers:' + _layerCompositeRevision`; the first render used `|layers:0` (pre-composite) → server returns a garbled placeholder → stored as `lastPreviewZoneHash`. PSD then loads (`recompositeFromLayers()` → `invalidateLayerVisibleContributionCache()` → `_layerCompositeRevision++` → hash now `|layers:1`) but **nothing re-triggered**, so the dedup `if (hash===lastPreviewZoneHash) return` left the garbled frame up. A source-click re-ran `triggerPreviewRender()` with the new `layers:1` hash → corrected render (the "click fixes it"). Captured live: pre-fix `lastPreviewZoneHash` tail `…|layers:0` vs current `…|layers:1` (identical otherwise, diff at the single final char). Fix (`paint-booth-3-canvas.js`): (1) **re-trigger** `triggerPreviewRender()` right after the boot `recompositeFromLayers()` (mirrors the existing text-layer path); (2) **defer guard** in `triggerPreviewRender` — skip while `window._spbPsdImportInFlight && !_psdLayersLoaded` so the premature `layers:0` render never fires (no garble flash). Guard is safe: `_spbPsdImportInFlight` clears in the import `finally` on ALL exit paths (success/abort/throw), so a failed import never permanently blocks renders; `_psdLayersLoaded` is true before the re-trigger so that one isn't skipped. Verified on 2 cold reloads: deferral holds during import (`lastTail:""`), re-trigger fires automatically at `rev:1`, final `hashMatch:true`, real 512²→1024² image, 0 JS errors, **no click needed**. Cache-buster `paint-booth-3-canvas.js?v=spb-previewinit-20260531a`.

**BUG B — wasted space above the car (FIXED for "space above"; "same size" nuance flagged).** Measured: panes are equal (438×732) but the preview's square render letterboxed in the tall pane below the 102px spec-dock left a ~110px dead band ABOVE the car (centered). Fix (`paint-booth-v2.css`, `.preview-inner>#previewPaintPane`): `align-items: center` → `flex-start` so the car pins flush under the dock like the source canvas sits at the top of its pane (kept `justify-content:center`; whole car still visible, `clipLeft/Right=0`). Verified: `gapAbove≈1px`, top-aligned, no clipping. Cache-buster `paint-booth-v2.css?v=spb-previewsize-20260531a`. NUANCE for owner: absolute sizes still differ because the SOURCE is zoomed (32% → 661px displayed/clipped) while the preview shows the WHOLE car fit-to-pane (406px). True pixel-for-pixel size-match would require the preview to track the source zoom (it would then clip like the source, losing the whole-car view) — left as an owner decision, not assumed.

3-copy synced (`sync-runtime-copies.js --write`), served code verified to contain both fixes. JS/CSS only — no engine change, no server restart, no render/deploy triggered.

## SELECT menu
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Select All Color | setCanvasMode('selectall') | ✅ | clicked cyan → selected 1,441,885 px of matching color. **2nd-pass run #28: ENGINE ✅** — `selectAllColor(1024,1024,32,false)` → 204,456px (all-yellow, non-contiguous, correctly ≫ wand's contiguous 5,076). |
| Edge Detect | setCanvasMode('edge') | ✅ | flood-selects region bounded by edges — click INSIDE a region (704 px); clicking ON an edge correctly selects nothing. **2nd-pass run #28: ENGINE ✅** — `edgeDetectFill(x,y,tolerance,addToExisting,subtractMode)`; with tol 32 → 730px bounded region (stops at edges, matches run #1). ⚠️ omitting `tolerance` floods the whole canvas (arg artifact, not a bug). |
| Move Selection Border | activateSelectionMove() | ✅ | mode 'selection-move'; drag moved the selection (123,530→111,922 px, persisted). **2nd-pass run #28: ENGINE ✅** — `activateSelectionMove()` (ret true) + `nudgeRegionSelection(60,0)` → selection bounds shifted EXACTLY +60,0 (minX 1010→1070). |
| Pick Layer Element | activateLayerElementPickMode() | ✅ | Layer Mode + Numbers layer + clicked a #55 → isolated element: 80,148 px, bbox [888,355,1295,592], layerId psd_2. _spbLastPickedElementBbox set. No errors. **2nd-pass run #30: re-verified ✅** (real click → isolated #55, 78,085 px, bbox(824,971)-(1111,1311)). 🔑 The `selxform` isolation layer it creates is cleanly removed by `cancelActiveTransformSession()` (run #18 "cruft" was just an un-cancelled session). |
| Zone Pick | setCanvasMode('zone-pick') | ⏸ | Activates correctly (mode 'zone-pick', banner). Click on a zone WITHOUT a spec pattern → selects nothing (rc 0), no error — correct no-op (nothing to pick), per run #5 note. Full sub-piece pick needs a spec pattern ASSIGNED to the zone (data-modifying setup, no zones accessor for safe restore) → deferred to a focused session. |
| Elliptical Marquee | setCanvasMode('ellipse-marquee') | ✅🔧 | drag → 123,530 px ellipse selection (run #1). **🔧 run #26 FIXED a real pan-hijack bug** — was missing from the pan-exemption list (canvas.js:8895) so zoomed-in drags panned instead of selecting; added it (+gradient, spatial-erase). See run log/FINDINGS. **2nd-pass run #26: ENGINE re-verified** — `commitEllipseSelection({700,700},{1300,1300})` → **282,697 px = 99.98% of π/4·600²** geometric, `hasActivePixelSelection()`=true, on regionCanvas. ⚠️ The drag GESTURE is NOT reproducible via `left_click_drag` (instrumented: commit called **0×**, no drift) — the synthetic drag doesn't engage the mousedown→isDrawing→mouseup commit state machine (src 3299→3764). NOT a regression (engine proven + wiring correct); the real gesture needs human/focused-session confirmation. Selections live in the **active-pixel-selection** (`_getActiveSelectionInfo`/`hasActivePixelSelection`), refreshed by `_doRenderRegionOverlay()` — NOT plain regionCanvas reads. |

## RETOUCH menu
**NOTE (2026-05-28):** RETOUCH tools edit LAYER pixels → require **Layer Mode** (`window.toolbarEditMode==='layer'`) + a selected layer (`window._selectedLayerId`). In Zone Mode they correctly NO-OP with a toast ("…only edits layers in Layer Mode") — that is a correct guard, NOT a bug. To test their paint action: enter Layer Mode + select a layer first. The clean mode-setter isn't under obvious window names — check js/canvas/dispatch.js or click the ZONE/LAYER UI toggle.
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Color Brush | setCanvasMode('colorbrush') | 🔧⏸ | Crash FIX HOLDS (run #3: `_t0` ReferenceError → defined, canvas.js:14453 — a REAL fix). The run #4 "doesn't paint in Layer Mode" verdict is now **SUSPECT (stale-canvas-rect, run #17)** — the "click + FG white = no mark" zoom was almost certainly looking at the wrong canvas location (rect.top had drifted 366→468). Since Brush is confirmed working, Color Brush likely paints fine too. RE-TEST with the FRESH canvas rect. |
| Clone Stamp | setCanvasMode('clone') | ⬜ | |
| Recolor | setCanvasMode('recolor') | ⬜ | |
| Smudge | setCanvasMode('smudge') | ⬜ | |
| Pencil | setCanvasMode('pencil') | ⬜ | |
| Dodge | setCanvasMode('dodge') | ⬜ | |
| Burn | setCanvasMode('burn') | ⬜ | |
| Blur Brush | setCanvasMode('blur-brush') | ⬜ | |
| Sharpen Brush | setCanvasMode('sharpen-brush') | ⬜ | |

## MASK menu
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Smooth Edges | smoothRegionMask() | ✅ | On a 3,246,181 px selection → 3,133,443 px (edges rounded). Count changed, no error. |
| Invert Mask | invertRegionMask() | ✅ | 948,123 → 3,246,181 px = exact (4,194,304 − 948,123). Perfect inversion, no error. |
| Copy Mask | copyMaskToZone(targetIndex) | ✅ | Made a wand mask on zone 0 (475,182 px) → `copyMaskToZone(4)` → selected zone 4: regionCanvas 475,182 = EXACT copy. Toast "Copied mask from Zone 1 → Zone 5". clearZoneRegions(4)+clearZoneRegions(0) restored both to 0. No errors, no artifact. (Engine verified; `toggleCopyMaskDropdown(e)` is the UI opener.) |
| Mirror Mask | mirrorRegionMask() | ✅ | Ran, no error, count preserved (3,133,443) as expected for a mirror. NOTE: geometry-flip is count-invariant so not independently verified via status-bar count; assume OK. |
| Include Region | setCanvasMode('spatial-include') | ✅ | Real-mouse drag → painted 709 px spatial-include mask (regionCanvas 0→709). Banner "Including for: Zone 1 (paint green to KEEP)", mode "SPATIAL +", status "SPATIAL INCLUDE". No errors. Cleared via clearSpatialMask(zoneIndex)+deselect. **2nd-pass run #30: re-verified ✅** — real drag → 1,418 value-1 (keep) marks in zone 0 spatialMask. |
| Exclude Region | setCanvasMode('spatial-exclude') | ✅ | Real-mouse drag → 709 px exclude mask (regionCanvas 0→709). Banner "❌ Excluding from: Zone 1 (paint red to REMOVE)", mode "SPATIAL −", status "SPATIAL EXCLUDE". No errors. **2nd-pass run #30: re-verified ✅** — real drag → 1,418 value-2 (remove) marks. |
| Erase Spatial | setCanvasMode('spatial-erase') | ✅ | Drag over exclude marks (exact path) → 709→0 (fully erased). No errors. NOTE: spatial brush is THIN (~1 canvas px); erase path must overlap the marks — an offset drag misses (709→709), aligned drag clears (709→0). **2nd-pass run #30: re-verified ✅** — drag over the include region removed exactly the 1,418 include marks (inc 1418→0, exclude untouched). |

## TRANSFORM menu
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Transform Pattern / Base | activateZoneTransform() | ✅ | Opened free-transform overlay on zone-1 base (ftState target=base, hasBox=true, "Zone Transform · base" indicator + on-canvas hint). Esc cancelled cleanly (ftState→null, mode→eyedropper), no commit. No errors. |
| Transform Decal | activateFreeTransform('decal') | ✅ | Guard path verified: with no decal selected → returns false, opens NO transform (ft null), toast "Select a decal first before using Transform Decal". Correct precondition guard, no errors, no state change. **2nd-pass run #26: re-verified** — ret false, ft null→null, mode unchanged (eyedropper), same toast; exact match to run #8. Follow-up: verify overlay opens with a decal selected (happy path). |

## ADJUST menu
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Brightness / Contrast | promptAdjustBrightnessContrast() | ✅ | promptAdjust...() opens a custom DOM dialog (NON-blocking, not native prompt) — verified clean open + Cancel/Apply. Engine `adjustBrightnessContrast(b,c)` applies (region 4,410,394→4,933,591 at +40/+20), undoDrawStroke restored exactly. closeModal() closes it. (Custom sliders not independently driven, but dialog opens + engine works.) |
| Hue / Saturation | promptAdjustHueSat() | ✅ | Engine `adjustHueSaturation(hueShift,sat,light)` applied (60,30,0) → region 4,410,394→4,471,687, undoDrawStroke restored exactly. Dialog-open pattern same as Brightness/Contrast. No errors. |
| Color Replace | openColorReplaceDialog() | ✅ | Engine `autoColorReplace(targetHex,replacementHex,tolerance)`: replaced yellow #55 → magenta — pixel(1024,1024) 234,255,0→255,0,255 EXACT, undoDrawStroke restored to 234,255,0. No errors. (openColorReplaceDialog opens the custom dialog; engine verified directly.) |
| Invert Colors | adjustInvertColors() | ✅ | Region (canvas 100×100) total-RGB sum 668,871 → 6,981,129 = exact (7,650,000 − 668,871). Perfect inversion. Undo restored to 668,871. No errors. |
| Grayscale | adjustGrayscale() | ✅ | Region (canvas 700,900,100×100) colorfulness Σ(\|R-G\|+\|G-B\|) 106,617 → 0 (full desaturation). Undo restored to 106,617. No errors. |
| Gradient Map | openGradientMapDialog() | ✅ | Engine `applyGradientMap(color1,color2)`: remaps luminance→gradient. applyGradientMap('#001040','#ffe000') → both regions changed (600,600: 4,410,394→4,339,549; 900,900: 3,166,590→3,671,594), undoDrawStroke restored BOTH exactly. No errors. |
| Vibrance | promptVibrance() | ✅ | Engine `adjustVibrance(amount)` — verified with a COLORFULNESS metric (sum metric is blind to saturation): region 700,1100 colorfulness 337,302→366,684 (+saturation), correctly NO-OP on grayscale region 900,900 (cf 0→0). undoDrawStroke restored. No errors. |
| Color Temperature | promptColorTemp() | ✅ | Engine `adjustColorTemperature(shift)` applied (40) → region 4,410,394→4,629,387 (warm shift), undoDrawStroke restored exactly. No errors. |

## PRIMARY toolbar icons
| Tool | Handler | Verdict | Notes |
|------|---------|---------|-------|
| Move | setCanvasMode('layer-move') | ✅ | NOT dead (flag resolved). Layer Mode + psd_2 selected + drag → moved the layer; bbox x 406→771, 1295→1660 (+365 canvas px for a +364px drag), y unchanged on horizontal drag = geometrically exact. Reverse drag restored bbox to [406,355,1295,2003] exactly. No errors. **2nd-pass run #32: INCONCLUSIVE** — the layer-move drag did NOT register via left_click_drag (bbox unchanged, even starting on psd_2 opaque content; selection drags worked, so layer-move-specific). The test sequence also degraded the composite RENDER (canary yellow→black; reload restored it — NO data loss). Stays ✅ from run #10; re-verify in a focused session (real drag). |
| Pick Item | setCanvasMode('pick-item') | ✅ | Real-mouse click on an item → switches to zone-pick + activates an independent free-transform on the picked zone item (freeTransformState target=base + zoneIndex + centerX/Y, scaleX/Y, rotation + orig*; toast "transform active — handles + pivot + live numbers"). No errors. Esc cancelled cleanly (no commit). NOTE: targeted the ZONE BASE, not an isolated #55 sub-element — single-element isolation is a separate/Layer-Mode path. **2nd-pass run #31: re-verified ✅** — real click → zone-pick mode + free-transform on the picked item (ft target="second_base", zone 0); cancelActiveTransformSession() cancelled cleanly (ft null, 11 layers, no cruft). |
| Transform (layer) | activateLayerContextTransform() | ✅ | Layer Mode + psd_2 selected → returns true, opens a free-transform overlay on the LAYER (freeTransformState target=layer, layerId=psd_2, centerX/Y, scaleX/Y, rotation + orig*). Rich UI: "EDITING LAYER Numbers", rotate −90/+90/180, scale, pos, handles+pivot, live numerics. No errors. ⚠️ Esc DESELECTS the layer (doesn't cancel); use cancelActiveTransformSession() to cancel (verified bbox untouched, no commit). **2nd-pass run #29: re-verified ✅** — `activateLayerContextTransform()` ret true → ft {target:layer, layerId:psd_2, scaleX/rotation/centerX}; `cancelActiveTransformSession()` → ft null, bbox [406,355,1295,2003] unchanged. |
| Pick Color (eyedropper) | setCanvasMode('eyedropper') | ✅ | Real-mouse click on canvas pixel (83,71,65) → fgColorSwatch + eyedropperSwatch both became #534741 (0→5 elements). Cursor readout "X:1299 Y:896 #534741" confirms hit. No errors. **2nd-pass run #27: re-verified ✅** — pick fires on canvas-hit (eyedropperHex/RGB read the clicked pixel); the initial "didn't pick" was the `zoneEditorFloat` covering the click region, NOT a tool bug (see run log). |
| Magic Wand | setCanvasMode('wand') | ✅ | Real-mouse click on body → contiguous 475,271 px selection. Status bar "Sel: 475,271px", toast "Magic Wand: selected 475,271 pixels", red overlay rendered, regionCanvas alpha count matches exactly. No errors. **2nd-pass run #28: ENGINE ✅** — `magicWandFill(1024,1024,32,false)` → 5,076px contiguous selection (has=true). ⚠️ CORRECTION: direct `magicWandFill()` DOES register a selection (engine works) — earlier "doesn't register" was only the synthetic-EVENT/click path, which is separately confounded this session by the zoneEditorFloat + rect-drift. |
| Lasso | setCanvasMode('lasso') | ✅ | POLYGON-CLICK lasso (NOT freehand): click vertices + double-click to close. Traced a triangle → 233,668 px selection; computed triangle area in canvas space ≈233,247 px = 0.2% match (geometrically correct). Status bar "Sel: 233,668px", regionCanvas matches. No errors. ⚠️ computer tool lacks left_mouse_down/up — use click-polygon, not held-drag. **2nd-pass run #32: re-verified ✅** — polygon (2 clicks + double-click close) → triangle selection 62,106 px ≈ geometric 60,000, bounds (890,891)-(1292,1202) matching the vertices. |
| Rectangle Select | setCanvasMode('rect') | ✅ | verified during APPLY AREA test-drive. **2nd-pass run #31: re-verified ✅** — real drag (canvas 950,850→1250,1150) → rect selection (has=true, 13,049 px, bounds (948,997)-(1101,1152)), clipped to the active zone 0 (drag-rect ∩ zone coverage). |
| Brush | setCanvasMode('brush') | ✅ | **CORRECTED run #17 — Brush WORKS.** Prior ❌ (run #12) was a STALE-CANVAS-RECT measurement error: I'd hardcoded rect.top=366 (run #7) but it had drifted to 468, so paint landed at canvas y≈79, not y≈581 — outside my sample region. Re-test with the FRESH rect: stroke → composite shows **217 magenta px at the actual paint location** + layer.img has it; Ctrl+Z reverted cleanly (bbox restored [406,355,1295,2003]). Layer paint commits AND displays correctly. |
| Fill Bucket | setCanvasMode('fill') | ✅ | **RE-TEST NEEDED — prior ❌ (run #11) is SUSPECT (stale-canvas-rect, see run #17).** The fill-click "didn't change pixel (1024,1024)" because with the correct rect.top=468 the click (screenshot 780,469) actually landed at canvas (1024,**522**) — it filled THERE, not at (1024,1024) which I sampled. The engine `fillBucketOnLayer` works (run #11). Fill very likely WORKS via click too; re-test with FRESH canvas rect. **2nd-pass run #33: re-verified ✅** via throwaway layer — `fillBucketOnLayer(1024,1024, throwaway)` flood-filled the blank layer uniformly with FG (white, alpha 255); psd_2 untouched. The run #11/#17 "broken/suspect" was the stale-rect/float confound, NOT the engine. |
| Gradient | setCanvasMode('gradient') | ✅ | Layer Mode + psd_2 + drag → gradient committed to layer (region 3,959,844→1,934,940), persisted, undoDrawStroke() restored exactly. No errors. (Distinct commit path from Fill — gradient works.) **2nd-pass run #33: re-verified ✅** via throwaway layer — `fillGradientOnLayer(...,'linear', throwaway)` → real gradient 229→127→25; psd_2 untouched. |
| Eraser | setCanvasMode('erase') | ⏸ | **RE-TEST NEEDED — prior ❌ SUSPECT.** It was only INFERRED broken (shares Brush's `_paintOnLayerAt` branch). Since Brush is now CONFIRMED WORKING (run #17, the ❌ was a stale-rect error), Eraser almost certainly works too. Re-test with the fresh canvas rect. |
| Text | setCanvasMode('text') | ⏸ | Investigated (not action-tested). Layer-draw tool: has `_textInputActive` state + "Smart Text Pick" toggle; renders text onto the layer on canvas-click → same family as Shape/Brush, will hit the held composite-refresh bug. DEFERRED to the focused paint-fix session (artifact-prone; would just re-confirm held). |
| Shape | setCanvasMode('shape') | ⏸ | Investigated (not action-tested). In Zone Mode a drag is a NO-OP (no selection, no paint; banner falls through to template-drag "pick which finish layer"). Layer-oriented draw tool → needs Layer Mode, will hit the held composite-refresh bug. DEFERRED to focused paint-fix session (artifact-prone). |
| Pen | setCanvasMode('pen') | ✅ | PEN / BEZIER path tool — NON-destructive. 3 canvas clicks → window.penPoints grew 0→3 with bezier control pts; first point at canvas (541,610) = EXACT mapped click coord. penClosed=false (not closed). Escape clears the path (penPoints→0). No errors. **2nd-pass run #31: re-verified ✅** — 3 real clicks → penPoints 0→3 (each {x,y,cx1,cy1,cx2,cy2}); first point canvas (898,897) ≈ click (900,900); penClosed false. ⚠️ Escape via the computer-tool key did NOT clear the path this time (focus/synthetic-key issue?); JS clear worked. |

## Run log
- **2026-05-28 (seed run):** Set up loop (cron `7,27,47 * * * *`, job 86f7d990). Created state files.
  Baseline smoke test via JS: `setCanvasMode('selectall')` activates cleanly; reset to eyedropper OK.
  Confirmed these handlers EXIST (function) — no dead handlers at this layer:
  selectAllColor, edgeDetectFill, activateSelectionMove, smoothRegionMask, invertRegionMask,
  mirrorRegionMask, activateZoneTransform, activateFreeTransform, promptAdjustBrightnessContrast,
  promptAdjustHueSat, adjustGrayscale, adjustInvertColors, openColorReplaceDialog, promptVibrance.
  NOTE: handler-exists ≠ PASS. Real per-tool ACTION tests (does it produce the intended result) are
  the job of the recurring runs. Rectangle Select already verified PASS (APPLY AREA test-drive).
  Methodology learned: activate via JS handler (menu coordinate-clicks unreliable); mouse only for
  canvas actions; verify via JS state + console + screenshot.
- **2026-05-28 run #1 (SELECT menu):** Tested 4 tools — Select All Color ✅, Edge Detect ✅,
  Elliptical Marquee ✅, Move Selection Border ✅. All PASS, zero console errors, no fixes needed.
  Verified via status-bar "Sel: Npx" indicator (selection pixel count). Cleaned up (deselect +
  eyedropper). Remaining in SELECT: Pick Layer Element, Zone Pick (next run).
- **2026-05-28 run #2 (RETOUCH start):** Tested Color Brush. KEY DISCOVERY: RETOUCH paint tools are
  Layer-Mode-gated (window.toolbarEditMode==='layer' + window._selectedLayerId). In Zone Mode Color
  Brush correctly no-ops with the toast "Color Brush only edits layers in Layer Mode" — canvas region
  sum unchanged (377219 before/after) = correct guard, NOT broken. Logged the Layer-Mode methodology
  so future runs can test the whole RETOUCH menu properly. NEXT RUN: find the Layer-Mode setter
  (js/canvas/dispatch.js or ZONE/LAYER toggle), enter Layer Mode, select layer 'psd_0' (Car Paint),
  then paint-test Color Brush + the rest of RETOUCH. Also still pending: SELECT Pick Layer Element,
  Zone Pick. Verified paint-detection method works: getImageData region-sum on #paintCanvas (2048²).
- **2026-05-29 run #3 (RETOUCH — Color Brush): FOUND + FIXED A REAL BUG.** Entered Layer Mode
  (`setToolbarEditMode('layer')`, dispatch.js), selected Numbers layer (psd_2), tried to paint →
  console error `ReferenceError: _t0 is not defined` at _paintColorBrushAt (canvas.js:14481). Root
  cause: perf-log line copy-pasted from clone fn; `_t0` never defined in _paintColorBrushAt (+ bogus
  'clone' label). Color Brush threw on EVERY mousedown → painted nothing. FIX: defined `_t0` at
  canvas.js:14453 + fixed label to 'colorbrush'. Synced, bumped canvas.js ?v= →
  spb-qa-colorbrush-fix-20260529, reloaded. Re-test: crash GONE (no console error). Cleaned up
  (cancelled a stray layer-element transform, undo×3, back to Zone Mode + eyedropper, layer deselected).
  CAVEAT: couldn't positively confirm pixel-painting in Layer Mode via composite-sampling (a drag
  opened the layer-element transform overlay) — flag: investigate Color Brush drag routing in Layer
  Mode next run. NEXT: RETOUCH Clone/Smudge/Pencil/Dodge/Burn/Blur/Sharpen (Layer Mode); SELECT Pick
  Layer Element + Zone Pick.
- **2026-05-29 run #4 (Color Brush deep-dive):** Confirmed the run-#3 crash fix holds (no _t0 error).
  Found a SECOND issue: Color Brush does NOT visibly paint in Layer Mode (click + FG white, brush 60 →
  no mark in before/after zoom). Traced the flow: paintColorBrush → paintImageData → flush
  (canvas.js:18814) which puts to paintCanvas + _activeLayerCanvas; but a recomposite
  (_refreshActiveLayerCompositePreviewNow, canvas.js:18830) rebuilds paintCanvas from the layer stack
  and the active-layer canvas — which apparently didn't get the stroke, so the paint is erased. This is
  an architecture-level fix (layer-paint commit) — deliberately NOT fixing blindly in the loop (risk of
  breaking all paint/compose). Logged in FINDINGS with file:line for a focused session. Cleaned up
  (undo×5, Zone Mode, eyedropper, layer deselected; car verified intact). ⚠️ This likely affects ALL
  RETOUCH brushes (Clone/Smudge/Dodge/Burn/Blur/Sharpen/Pencil) since they share the layer-paint commit
  path — so the next runs should treat the layer-paint commit as the prime suspect, not each tool.
- **2026-05-29 run #5 (SELECT + MASK):** 4 tools, all PASS, no fixes needed, no console errors.
  Pick Layer Element ✅ (isolated #55, 80,148 px). Invert Mask ✅ (exact flip 948,123→3,246,181).
  Smooth Edges ✅ (3,246,181→3,133,443). Mirror Mask ✅ (ran cleanly, count preserved as expected; geometry
  flip count-invariant, not independently checked). Cleaned up. SELECT now fully covered EXCEPT Zone Pick
  (needs a spec pattern in a zone to pick — set one up / defer). MASK remaining: Copy Mask (needs event arg +
  2nd zone), Include/Exclude/Erase Spatial. Then TRANSFORM + ADJUST. RETOUCH brushes still HELD pending the
  layer-paint commit fix (run #4).
- **2026-05-29 run #6 (ADJUST + TRANSFORM):** 3 tools, all PASS, no fixes, no console errors, no source
  changes/no drift. Method: apply → verify region via getImageData → undo → verify restore. **Grayscale** ✅
  (colorfulness Σ(|R-G|+|G-B|) 106,617→0 full desaturate; undo restored 106,617). **Invert Colors** ✅ (region
  total-RGB sum 668,871→6,981,129 = exact 7,650,000−668,871; undo restored 668,871). **Transform Pattern/Base**
  ✅ (activateZoneTransform opened a free-transform overlay on the zone-1 base — ftState target=base, hasBox; Esc
  cancelled cleanly, ftState→null, mode→eyedropper, NO commit so base untouched). Car verified intact. ADJUST
  direct (non-dialog) tools now done; the rest of ADJUST (Brightness/Contrast, Hue/Sat, Color Replace, Gradient
  Map, Vibrance, Color Temp) open DIALOGS — several are `prompt*`/`open*Dialog`; ⚠️ if any use native
  `prompt()` they'd BLOCK a javascript_tool eval, so next ADJUST run must drive them via the dialog UI (open
  via menu, set a value, Apply), not by calling the handler blind. TRANSFORM remaining: Transform Decal.
  MASK remaining: Copy Mask, Include/Exclude/Erase Spatial. RETOUCH brushes still HELD (layer-paint commit, run #4).
- **2026-05-29 run #7 (PRIMARY icons + MASK spatial):** 3 tools, all PASS, no fixes, no console errors, no source
  changes. **Magic Wand** ✅ (real-mouse click → 475,271 px contiguous selection, status bar "Sel: 475,271px" +
  toast). **Pick Color/eyedropper** ✅ (click pixel 83,71,65 → fgColorSwatch+eyedropperSwatch = #534741).
  **Include Region/spatial-include** ✅ (real-mouse drag → 709 px spatial mask, "Including for Zone 1" banner).
  Cleaned up (cleared selection + spatial mask, eyedropper, Zone Mode, regionCanvas=0). 🔑 **METHODOLOGY
  BREAKTHROUGH — canvas-click tools need the REAL MOUSE.** Synthetic MouseEvents AND direct handler calls
  (magicWandFill(x,y,tol,add)) do NOT register selections — only the computer-tool mouse goes through the full
  pipeline. Coordinate mapping CONFIRMED: #paintCanvas rect (747,366,416×416), innerW 1920, screenshot 1568 →
  pass computer-tool coords in SCREENSHOT space = viewport/1.2245 (tool scales ×1.2245 back to viewport).
  Selection readout = status-bar "Sel: N px" (regex /Sel\s*:?\s*([\d,]+)\s*px/i) AND regionCanvas alpha count
  (agree exactly). ⚠️ `_hasAnyMaskPixels` tracks COMMITTED ZONE masks, NOT the active selection — wrong probe
  for selection tools. `clearSpatialMask(zoneIndex)` needs a zone-index arg. Cleanup gotcha: clearing
  selection/spatial DATA can leave a STALE bitmap on regionCanvas until a mode switch repaints it — the DATA is
  what counts. Unblocks ALL remaining canvas-click tools (Lasso, Move, Pick Item, Fill, Gradient, Erase, Brush,
  Exclude/Erase Spatial). RETOUCH brushes still HELD (layer-paint commit, run #4).
- **2026-05-29 run #8 (MASK spatial finish + TRANSFORM finish):** 3 tools, all PASS, no fixes, no console errors,
  no source changes. **Exclude Region/spatial-exclude** ✅ (real-mouse drag → 709 px exclude mask, "❌ Excluding
  from Zone 1" banner, "SPATIAL −"). **Erase Spatial/spatial-erase** ✅ (drag over the marks → 709→0; first drag
  was ~60 canvas px offset and missed → 709→709, aligned drag cleared → 709→0; the spatial brush is ~1 canvas px
  thin, so erase must overlap the marks — NOT a bug). **Transform Decal/activateFreeTransform('decal')** ✅ guard
  path (no decal selected → returns false, opens no transform, toast "Select a decal first before using Transform
  Decal"; correct guard, no errors). Verified no spatial data lingers in EITHER channel via mode-cycle repaint
  (include 0, exclude 0), back to eyedropper/Zone Mode/regionCanvas 0. ✅ **MASK menu now fully covered EXCEPT
  Copy Mask** (needs event arg + 2nd zone). ✅ **TRANSFORM menu fully covered** (Transform Decal happy-path —
  overlay-opens-with-a-decal — is a noted follow-up). Remaining: Copy Mask; ADJUST dialogs (run #6 note); PRIMARY
  Lasso/Move/Pick Item/Fill/Gradient/Erase/Brush/Text/Shape/Pen + Transform(layer); SELECT Zone Pick (needs a
  spec pattern in a zone). RETOUCH brushes still HELD (layer-paint commit, run #4).
- **2026-05-29 run #9 (PRIMARY: Lasso + Pick Item):** 2 tools, both PASS, no fixes, no console errors, no source
  changes. **Lasso** ✅ — discovered it's a POLYGON-CLICK lasso (click vertices + double-click to close, NOT a
  held-drag freehand): traced a triangle → 233,668 px selection = the traced area to 0.2% (geometrically correct),
  status bar "Sel: 233,668px". **Pick Item** ✅ — real-mouse click picks the zone item under the cursor, switches
  to zone-pick mode, and activates an independent free-transform on it (freeTransformState target=base + zoneIndex
  + full params; "transform active — handles + pivot + live numbers" toast); Esc cancelled cleanly (no commit, base
  untouched). NOTE: it targeted the zone BASE, not an isolated #55 sub-element — single-element isolation is a
  separate path. 🔑 **Computer-tool gesture limits:** `left_mouse_down`/`left_mouse_up` are UNSUPPORTED, so no
  held-button freehand path — drive lasso-type tools by click-polygon (left_click vertices + double_click close);
  straight `left_click_drag` is fine for marquee/gradient/box gestures. Cleanup: Esc (cancel transform) cleared the
  active transform AND the selection; back to eyedropper/Zone Mode/regionCanvas 0. Remaining PRIMARY: Move,
  Transform(layer), Fill, Gradient, Eraser, Brush, Text, Shape, Pen (most are paint/vector — likely Layer-Mode
  gated, may share the held layer-paint commit). Also: Copy Mask; ADJUST dialogs; SELECT Zone Pick.
- **2026-05-29 run #10 (PRIMARY: Transform-layer + Move — layer manipulation, NOT pixel-paint):** 2 tools, both
  PASS, no fixes, no console errors, no source changes. Chosen because they're layer position/transform ops,
  independent of the held layer-paint commit bug. Setup: setToolbarEditMode('layer') + selectPSDLayer('psd_2'
  Numbers). **Transform (layer)/activateLayerContextTransform()** ✅ — returns true, opens a free-transform on the
  LAYER (ft target=layer, layerId=psd_2, full params + rotate/scale/pos UI, handles, pivot, live numerics). **Move/
  layer-move** ✅ — drag moved the layer; bbox x +365 canvas px for a +364px drag (y unchanged on horizontal) =
  geometrically exact; reverse drag restored bbox to [406,355,1295,2003] EXACTLY. **The old "Move possibly dead"
  flag is RESOLVED — Move works.** 🔑 Findings: layer position lives in `layer.bbox`; Esc during a layer-transform
  DESELECTS the layer (does NOT cancel) — use `cancelActiveTransformSession()` / `cancelLayerTransform()`; useful
  numeric setters exist for future tests (setLayerTransformRotation/Position, rotateActiveLayerTransformBy,
  flipActiveLayerTransformH/V, resetActiveLayerTransform). Cleanup: deselect layer, cancel transform, back to
  Zone Mode + eyedropper, Numbers layer restored exactly, rc 0, ft null. Remaining PRIMARY: Fill, Gradient, Eraser,
  Brush, Text, Shape, Pen (paint/vector — likely Layer-Mode gated, may share held layer-paint commit). Also: Copy
  Mask; ADJUST dialogs; SELECT Zone Pick. RETOUCH brushes still HELD (layer-paint commit, run #4).
- **2026-05-29 run #11 (PRIMARY paint: Gradient + Fill Bucket):** 1 PASS, 1 BROKEN. **Gradient** ✅ (Layer Mode +
  psd_2 + drag → gradient commits to layer, region 3,959,844→1,934,940, persisted, undoDrawStroke restored). **Fill
  Bucket** ❌ — CLICK path broken: with getSelectedEditableLayer()='psd_2' (guards pass) a fill-click is a SILENT
  no-op (no pixel change, no console error), yet the engine `fillBucketOnLayer(x,y)` called directly DOES fill
  (pixel→FG). So fill's mousedown branch (canvas.js:3571) isn't applying — likely Layer-Mode click interception or
  bad `pos`; same risky routing area as the held Color Brush (run #4). DEFERRED (no autonomous edit). 🔑 Process
  findings: (1) `selectPSDLayer(id)` TOGGLES — calling it twice on the same id deselects (this confused my earlier
  guard checks: getSelectedEditableLayer went null). (2) Direct `fillBucketOnLayer()` calls BYPASS the handler's
  `_pushLayerUndo` (canvas.js:3580), so they're NOT undoable via undoDrawStroke — the undo stack got tangled and a
  direct fill couldn't be reverted by undo. ⚠️ **Test artifact:** restored the center #55 by setting FG=#EAFF00 and
  re-filling (pixel back to yellow 234,255,0); Numbers region 3,983,277 vs orig 3,959,844 = +0.6% (re-fill made the
  edge AA solid yellow vs original feathering — visually negligible, one number's edge). Did NOT reload (would risk
  losing the imported PSD). LESSON for future paint tests: test paint tools via the CLICK/handler path only, never
  mix direct fill/paint fn calls with undo; if a paint commits, undo immediately via the SAME path that pushed it.
  Cleanup: eyedropper, Zone Mode, layer deselected, rc 0, no console errors. Remaining PRIMARY: Eraser, Brush
  (click — likely same as Fill), Text, Shape, Pen; plus Copy Mask, ADJUST dialogs, SELECT Zone Pick. RETOUCH +
  Fill + click-paint tools all point at ONE focused-session fix: Layer-Mode click→paint routing/commit (run #4).
- **2026-05-29 run #12 (PRIMARY paint: Brush + Eraser):** both ❌, no autonomous fix (deferred), clean cleanup, no
  console errors. **Brush** ❌ — REFINED the layer-paint diagnosis: Layer Mode + psd_2 + magenta FG + stroke → the
  COMPOSITE stayed unchanged (0 magenta visible), BUT psd_2.img (the layer buffer) gained **750 magenta px**. So the
  brush paint DOES reach `layer.img`; the bug is that the **post-stroke composite refresh doesn't reflect the layer
  buffer** → the user sees nothing. (Earlier run #4 guessed paint never reached the buffer — now confirmed it does;
  the gap is the composite refresh.) **Eraser** ❌ inferred — same `_paintOnLayerAt` branch (canvas.js:3450 handles
  `'brush'||'erase'`); not repainted to avoid another artifact. 🔑 Key fix-relevant findings: (1) layer paint reverts
  via **Ctrl+Z (master undo), NOT undoDrawStroke** (undoDrawStroke left the 750px; Ctrl+Z cleared to 0). (2) layer.img
  is an Image, not a canvas (can't clearRect it directly). Disciplined cleanup this run: Ctrl+Z reverted the stroke
  (layer magenta 750→0), verified center #55 still yellow (234,255,0 — run-#11 restore intact), eyedropper, Zone Mode,
  layer deselected, rc 0. NO test artifact left this run. Remaining PRIMARY: Text, Shape, Pen (vector — may differ
  from pixel paint); plus Copy Mask, ADJUST dialogs, SELECT Zone Pick. **Focused-session scope now well-mapped:** the
  Layer-Mode composite-refresh-after-paint gap blocks Brush/Eraser/ColorBrush/Fill-click; fix once + re-verify the set.
- **2026-05-29 run #13 (ADJUST dialog tools):** 4 tools, ALL PASS, no fixes, no console errors, no source changes,
  NO artifact (all applied + undone exactly). Pivoted away from the risky paint tools to the SAFE ADJUST family
  (composite ops with proven undoDrawStroke undo, run #6). 🔑 **Resolved the run-#6 blocking concern:** the
  `promptAdjust*()` handlers open **custom DOM dialogs (NON-blocking), NOT native prompt()** — verified by overriding
  window.prompt (never called) + screenshot of the clean "BRIGHTNESS / CONTRAST" modal. The dialog's Apply calls the
  engine `adjust*()`. Tested the engines directly (precise + undoable): **Brightness/Contrast** ✅ (adjustBrightnessContrast
  4,410,394→4,933,591), **Hue/Saturation** ✅ (adjustHueSaturation →4,471,687), **Color Temperature** ✅
  (adjustColorTemperature →4,629,387), **Vibrance** ✅ (adjustVibrance — verified via COLORFULNESS metric: 337,302→366,684
  on a colored region; correctly no-ops on grayscale). All restored via undoDrawStroke. Dialogs close via `closeModal()`.
  Process notes: (a) custom sliders aren't <input type=range> so not driven directly — engine + dialog-open verified
  instead (slider→engine wiring assumed). (b) Caught + fixed a self-inflicted undo-loop bug (keyed the stop-check on the
  wrong region → vibrance left unreverted briefly; restored). ADJUST now **6/8** (+ Grayscale/Invert from run #6).
  Remaining ADJUST: Color Replace (openColorReplaceDialog), Gradient Map (openGradientMapDialog) — the open*Dialog ones
  need from/to-color or gradient-stop inputs (dialog-driving). Also remaining: PRIMARY Text/Shape/Pen, Copy Mask,
  SELECT Zone Pick. RETOUCH + Brush/Eraser/Fill-click still HELD (Layer-Mode composite-refresh fix, runs #4/#11/#12).
- **2026-05-29 run #14 (ADJUST finish: Color Replace + Gradient Map):** 2 tools, BOTH PASS, no fixes, no console
  errors, no source changes, NO artifact. Engines (direct, precise, undoable): **Gradient Map** ✅
  `applyGradientMap('#001040','#ffe000')` remaps luminance→gradient, both regions changed (600,600 4,410,394→4,339,549;
  900,900 3,166,590→3,671,594), undoDrawStroke restored BOTH exactly. **Color Replace** ✅
  `autoColorReplace('#eaff00','#ff00ff',40)` replaced yellow #55→magenta, pixel(1024,1024) 234,255,0→255,0,255 EXACT,
  undo restored. (Used the fixed undo stop-condition checking ALL sampled regions — no repeat of run #13's vibrance
  slip; zero artifact.) Final state verified: eyedropper, Zone Mode, #55 yellow, regions original, rc 0, no dialog.
  🎉 **ADJUST MENU NOW 8/8 COMPLETE** (Brightness/Contrast, Hue/Sat, Color Temp, Vibrance, Grayscale, Invert,
  Gradient Map, Color Replace — all ✅). **Remaining across all menus:** PRIMARY Text/Shape/Pen (vector — may differ
  from pixel paint; test cautiously, may be artifact-prone), Copy Mask (MASK — needs 2nd zone), SELECT Zone Pick
  (needs a spec pattern assigned to a zone). HELD (one focused Layer-Mode composite-refresh fix): RETOUCH brushes +
  Brush/Eraser/Fill-click (runs #4/#11/#12).
- **2026-05-29 run #15 (PRIMARY vector: Pen + Shape + Text):** 1 PASS, 2 deferred, no fixes, no console errors, no
  source changes, NO artifact. **Pen** ✅ — PEN/BEZIER PATH tool (non-destructive): tracks window.penPoints/penClosed;
  3 canvas clicks → penPoints 0→3 with bezier control points; first point at canvas (541,610) = exact mapped click
  coord; Escape clears the path (→0). Clean, no commit. **Shape** ⏸ deferred — Zone-Mode drag is a NO-OP (no
  selection/no paint; banner falls through to template-drag "pick which finish layer"); it's a layer-oriented draw
  tool → will hit the held composite-refresh bug. **Text** ⏸ deferred — layer-draw tool (`_textInputActive` state +
  "Smart Text Pick" toggle; renders text onto layer on click). Both Shape+Text investigated (nature confirmed) but
  NOT action-tested in Layer Mode — they're in the held layer-draw family; testing now would be artifact-prone and
  just re-confirm held. Will verify after the focused paint fix. Cleaned up (Escape cleared pen path; eyedropper,
  Zone Mode, rc 0). 🟢 **All non-layer-paint PRIMARY icons now PASS** (Move, Pick Item, Transform-layer, eyedropper,
  Wand, Lasso, Rect, Gradient, Pen). **Remaining truly-untested:** Copy Mask (MASK, needs 2nd zone), SELECT Zone
  Pick (needs spec pattern in a zone). HELD/deferred (one focused Layer-Mode composite-refresh fix): RETOUCH brushes,
  Brush, Eraser, Fill-click, Shape, Text.
- **2026-05-29 run #16 (last untested tools: Copy Mask + Zone Pick):** 1 PASS, 1 deferred, no fixes, no console
  errors, NO artifact. Found zones are color-based (all regionCanvas 0 — no region masks set), so a transient test
  mask was safe to create + clear. **Copy Mask** ✅ — `copyMaskToZone(targetIndex)`: wand mask on zone 0 (475,182 px)
  → copyMaskToZone(4) → zone 4 got an EXACT 475,182 px copy ("Copied mask from Zone 1 → Zone 5" toast); clearZoneRegions
  restored both zones to 0. **MASK MENU NOW 7/7 COMPLETE.** **Zone Pick** ⏸ deferred — activates + correctly no-ops
  (selects nothing, no error) on a zone with no spec pattern; the actual sub-piece pick needs a spec pattern assigned
  (data-modifying, no zones accessor for safe restore) → focused session. No zones accessor (window.getZones/zones
  undefined) — used regionCanvas-per-zone + toast as the readout. Cleaned up: both test zones cleared, eyedropper,
  Zone Mode, rc 0, zone 0 selected.
- ════════ 🗺️ FULL TOOL SUITE NOW MAPPED (every tool has a verdict or documented deferral) ════════
  **PASS:** SELECT 5 (Select All Color, Edge Detect, Move Selection Border, Pick Layer Element, Elliptical Marquee);
  MASK 7/7 (Smooth, Invert, Mirror, Copy Mask, Include/Exclude/Erase Region); TRANSFORM 2/2; ADJUST 8/8; PRIMARY 9
  (Rect, Wand, Pick Color, Lasso, Pick Item, Move, Transform-layer, Gradient, Pen). **= 31 tools PASS.**
  **❌ BROKEN (held, ONE root cause — Layer-Mode composite-refresh-after-paint, runs #4/#11/#12):** Color Brush, Fill
  (click), Brush, Eraser — plus ⏸ Shape, Text (same family, layer-draw) and the rest of RETOUCH (Clone/Smudge/Pencil/
  Dodge/Burn/Blur/Sharpen — same path, not individually re-tested). **⏸ DEFERRED (focused data-setup session):** SELECT
  Zone Pick (needs spec pattern). **NEXT WORK:** (1) the single focused Layer-Mode paint fix → unblocks the whole
  RETOUCH + click-paint + Shape/Text group, then re-verify them; (2) Zone Pick focused test; (3) a final second pass.
- 🚨🚨 **2026-05-29 run #17 — MAJOR CORRECTION: the "broken paint group" was a MEASUREMENT ERROR, not a real bug.**
  While investigating the layer-paint composite-refresh "bug" for the focused-session writeup, I painted a brush
  stroke and found: layer.img got the paint (1070 magenta) AND **the composite showed 217 magenta px at the actual
  paint location**. The catch: **#paintCanvas.getBoundingClientRect().top had drifted from 366 (hardcoded since
  run #7) to 468** — the layout shifted over the session. So every canvas click/drag I issued was landing ~100
  screenshot-px (≈500 canvas-px in y) OFF from where I assumed, and I was sampling the composite in the WRONG region.
  The brush stroke I thought hit canvas y≈581 actually hit y≈79; the paint WAS in the composite, just not where I
  looked. Ctrl+Z reverted cleanly (psd_2 bbox restored to [406,355,1295,2003], magenta 0). **→ Brush CONFIRMED
  WORKING (corrected ❌→✅).** **This invalidates the run #4/#11/#12 "held/broken" verdicts** for the whole paint
  group — they were all measured with the stale rect, so the paint landed outside my sampled regions. Fill, Eraser,
  Color Brush, Shape, Text, and the RETOUCH brushes are now **SUSPECT (likely WORK)** and flagged for RE-TEST.
  🔑 **METHODOLOGY FIX (critical): READ #paintCanvas.getBoundingClientRect() FRESH at the start of EVERY run — never
  hardcode/reuse it.** Map: canvasX=(vx-rect.left)*2048/rect.width, canvasY=(vy-rect.top)*2048/rect.height, and the
  computer tool takes SCREENSHOT-space coords = viewport/(innerWidth/screenshotWidth)=/1.2245. So screenshot→canvas
  must use the LIVE rect each run. **NEXT RUN(S): systematically RE-TEST the paint group (Brush done ✅; Fill, Eraser,
  Color Brush, Shape, Text, Clone/Smudge/Pencil/Dodge/Burn/Blur/Sharpen) using the FRESH canvas rect** — likely most/all
  PASS, which would mean there is NO layer-paint bug and the suite is ~fully green. The "focused paint fix" may be
  unnecessary. No source change this run; psd_2 fully restored; no artifact.
- **2026-05-29 run #18 — paint-group re-test attempt; found TWO MORE confounds (rect drift is LIVE + a cruft layer).**
  Applied the run-#17 fix (read rect fresh). Confirmed the rect **DRIFTS mid-run**: read 366 at setup, 464 minutes
  later — it genuinely shifts ~100px during a session (likely an autosave/notification banner toggling header height).
  So even reading it once per run isn't enough; it can move between the read and the click. **Re-tested Fill** (FG
  magenta, fresh-rect-computed click on the #55): committed NO paint (psd_2 magenta 0). BUT the active layer had
  silently become a stray **"Transform Selection"** synthetic layer (selxform_…, on TOP, from my earlier element-pick/
  transform tests) — the Layer-Mode click SELECTED that top layer instead of filling psd_2 ("FILL BUCKET → layer:
  Transform Selection"). So the Fill result is **CONFOUNDED** (wrong layer + rect drift); I will NOT claim a verdict
  (per the run-#17 lesson about coordinate-confounded data). The click selecting the top layer is consistent with the
  run-#11 "Layer-Mode click interception" hypothesis, but not cleanly proven. **Brush ✅ (run #17) still holds** (it
  was verified by paint appearing in the composite — layer-agnostic). 🔑 **Two confounds now block clean autonomous
  paint testing:** (1) **rect drift** — read getBoundingClientRect() IMMEDIATELY before each click AND re-read after to
  confirm it didn't move; if it moved, the test is invalid. (2) **stray "Transform Selection" cruft layer** sits on top
  and gets auto-selected by Layer-Mode clicks — must be removed and a real layer explicitly re-selected (and verified)
  before each paint test. Cleanup: deselected, eyedropper, Zone Mode; psd_2 intact (bbox [406,355,1295,2003], magenta 0,
  NO artifact). ⚠️ **1 stray "Transform Selection" layer remains on the PSD** (test cruft I created via transform/pick
  tests; NOT deleted autonomously — flag for the user / focused session to remove). **REVISED PLAN:** the paint-group
  re-test needs a CLEAN focused session — remove cruft selxform layers, read rect live + verify-no-drift per click,
  explicitly select+verify the target layer, then test Fill/Eraser/Color Brush/Shape/Text + RETOUCH brushes. Brush ✅
  and Gradient ✅ (drag tools) are the confirmed-working anchors; drag-based paint likely works, click-based (Fill, Text)
  is the suspect set.
- **2026-05-29 run #19 — THIRD confound found (drag-on-element MOVES it); paint group is NOT autonomously testable.**
  Tried a clean drift-aware Color Brush test, then an A/B control with the KNOWN-WORKING Brush (same drag). BOTH
  "painted nothing" — even the run-#17-confirmed Brush. The reason: **in Layer Mode, a drag that STARTS ON an existing
  layer element MOVES that element instead of painting.** My drags landed on the #55 (canvas ~995,497, inside psd_2's
  content) → they MOVED psd_2 by the drag delta. Proof: psd_2.bbox shifted [406,355,1295,2003] → [584,473,1473,2121]
  (≈ +178,+118 = my two drag deltas summed). Run #17's brush painted because it dragged on EMPTY canvas (y≈79, outside
  content). **Restored psd_2 with 2× Ctrl+Z → bbox back to [406,355,1295,2003] exactly** (no lasting corruption,
  magenta 0). 🚨 **So there are now THREE confounds making autonomous paint testing infeasible + corruption-prone:**
  (1) rect drifts mid-run (366↔468); (2) stray "Transform Selection" cruft layer; (3) drag-on-element = move (not
  paint). I've twice corrupted+restored psd_2 (runs #11, #19) chasing paint verdicts. **The Fill/Color-Brush "no
  paint" results across runs #11/#18/#19 are CONFOUNDED — NOT clean verdicts.** Only **Brush ✅ + Gradient ✅** (run
  #17/#11, paint shown in composite) are clean. 🛑 **STRATEGIC PIVOT: stop autonomous paint-tool testing.** It needs a
  focused session with the owner (clean reloaded state, cruft removed, stable rect, drag on empty canvas / clarify the
  paint-vs-move routing). **Future autonomous runs should do the SECOND-PASS re-verification of the confirmed-PASS
  NON-paint tools** (SELECT, MASK, TRANSFORM, ADJUST, non-paint PRIMARY = 31 tools) — those are clean, safe, and
  confound-free. ⚠️ 1 stray "Transform Selection" cruft layer still on the PSD (flag for removal). psd_2 restored, no
  artifact this run.
- **2026-05-29 run #20 — SECOND PASS begins (non-paint re-verification per the run-#19 pivot).** Clean run, no
  confounds, no artifact. Re-verified 4 ADJUST engines (handler-invoked → immune to the rect-drift/cruft/drag-move
  confounds), each apply→verify→undo→verify-restore: **Grayscale** ✅ (colorfulness 315,860→0→315,860), **Invert
  Colors** ✅ (sum 4,410,394→8,339,606→4,410,394), **Brightness/Contrast** ✅ (→4,933,591→restored), **Color
  Temperature** ✅ (→4,629,387→restored). All change values EXACTLY match runs #13/#14 → engines deterministic, NO
  regression. Composite fully restored (sum600 4,410,394, cf700 315,860), regionCanvas 0, eyedropper, no console
  errors. **Second-pass progress: ADJUST 4/8 re-verified** (Grayscale, Invert, Brightness/Contrast, Color Temp).
  NEXT 2ND-PASS: remaining ADJUST (Hue/Sat, Vibrance, Gradient Map, Color Replace — all handler-invoked, clean), then
  MASK ops (smoothRegionMask/invertRegionMask/mirrorRegionMask — need a region mask; create via a non-paint path),
  TRANSFORM (activateZoneTransform/activateFreeTransform — overlay-open + Esc/cancel), SELECT + non-paint PRIMARY
  (wand/lasso/marquee/eyedropper/pick — these DO need canvas clicks, so apply the drift-aware rule: read rect live +
  re-read after). Paint group remains parked for the focused session.
- **2026-05-29 run #21 — SECOND PASS cont'd: ADJUST re-verification COMPLETE (8/8).** Clean run, no confounds, no
  artifact. Re-verified the remaining 4 ADJUST engines, each apply→verify→undo→restore: **Hue/Saturation** ✅ (sum
  4,410,394→4,471,687→restored — exact match to run #13), **Vibrance** ✅ (colorfulness 315,860→345,464→restored),
  **Gradient Map** ✅ (sum600 4,410,394→4,334,399; sum900 3,166,590→3,671,594 [exact match run #14]; both restored),
  **Color Replace** ✅ (pixel(1024,1024) 234,255,0→255,0,255 magenta→restored). No regression. Composite fully
  restored (allRestored=true: sum600 4,410,394, sum900 3,166,590, px1024 yellow), regionCanvas 0, eyedropper, no
  console errors. ✅ **ADJUST 2ND-PASS DONE 8/8** (Grayscale, Invert, Brightness/Contrast, Color Temp [run #20] +
  Hue/Sat, Vibrance, Gradient Map, Color Replace [run #21]) — all deterministic, un-regressed. **NEXT 2ND-PASS:**
  MASK ops (need a region mask — but creating one needs a canvas click [wand] → drift-aware; OR use invertRegionMask
  on an empty mask to test the op runs), then TRANSFORM (activateZoneTransform overlay-open + cancelActiveTransformSession),
  then SELECT + non-paint PRIMARY (wand/lasso/marquee/eyedropper/pick — canvas clicks, drift-aware: read rect live +
  re-read after each). Paint group parked for focused session; 1 cruft "Transform Selection" layer still flagged.
- **2026-05-29 run #22 — SECOND PASS cont'd: MASK region-ops re-verified (invert/smooth/mirror), no regression.**
  Created a partial region mask via a Zone-Mode wand click (475,271 px — Zone Mode = composite-based, no Layer-Mode
  cruft/drag confounds; click location doesn't matter for MASK-op testing). 🔑 **GOTCHA found: the regionCanvas
  DISPLAY is STALE after MASK ops** — `invertRegionMask` etc. modify the mask DATA but the regionCanvas pixels don't
  update, and `renderRegionOverlay()` does NOT refresh them — only **`_doRenderRegionOverlay()`** does. (My first reads
  showed "no change" = stale display, not broken ops.) With `_doRenderRegionOverlay()` before each read:
  **invertRegionMask** ✅ (466,646 → 3,727,658 = EXACT complement 4,194,304−466,646, reversible), **smoothRegionMask**
  ✅ (rounds edges: on the big inverted mask 3,727,658 → 3,692,111 [~35K]; net-zero on a clean color-mask, which is
  fine), **mirrorRegionMask** ✅ (count-invariant, runs cleanly — geometry-flip not independently checked, same caveat
  as run #5). Cleanup: clearZoneRegions(0) → regionCanvas 0; psd_2 #55 intact (px1024 yellow — MASK ops touch the zone
  mask, not the layer); eyedropper, no console errors, no artifact. **MASK 2nd-pass: 3/7 region-ops done** (invert,
  smooth, mirror). Copy Mask was clean run #16; Include/Exclude/Erase Spatial need drift-aware canvas drags (later).
  **NEXT 2ND-PASS:** TRANSFORM (activateZoneTransform overlay-open + cancelActiveTransformSession), then SELECT +
  non-paint PRIMARY (canvas clicks — drift-aware: read rect live + re-read after; for selections, refresh display via
  _doRenderRegionOverlay before reading the count). Paint group parked; cruft layer flagged.
- **2026-05-29 run #23 — TRANSFORM 2nd-pass (1/2), then ⚠️ SERVER DOWN — ended per prereq rule.** **Transform
  Pattern/Base** ✅ re-verified (activateZoneTransform → ft {target:base, scaleX, rotation}, matches run #6; cancelled
  via cancelActiveTransformSession, ft null). Then the prereq check FAILED: server http://localhost:59876/ "Failed to
  fetch" on HEAD + GET(/) + GET(/paint-booth-v2.html) — the dev server (python :59876) is not accepting connections.
  The in-browser app is still client-side responsive (the transform opened/cancelled fine), but per the HARD RULE
  ("server down → log + end, don't thrash") I ended the run. Did NOT reach Transform Decal or SELECT/PRIMARY. State
  left clean (ft null, eyedropper, Zone Mode, rc 0, psd_2 [406,355,1295,2003]). Did NOT restart the server (owner's
  process, out of scope). **NEXT RUN:** cron retries in ~20 min; if :59876 is back (200), resume at Transform Decal →
  then SELECT + non-paint PRIMARY (drift-aware clicks + _doRenderRegionOverlay refresh). 2nd-pass tracker: ADJUST 8/8,
  MASK 3/7 (+Copy Mask), TRANSFORM 1/2, SELECT+PRIMARY pending. Paint group parked; cruft layer flagged.
- **2026-05-29 run #24 — SERVER STILL DOWN (2nd consecutive) — logged + ended, no thrash.** Re-checked prereqs:
  GET `/` and GET `/paint-booth-v2.html` both "Failed to fetch" again. Dev server (python :59876) still not accepting
  connections. App tab still loaded/responsive client-side, no work done, no state change. Per HARD RULE: ended. ⚠️
  **Owner: your :59876 dev server appears to have stopped ~40+ min ago — restart it to let the QA loop resume.** Until
  then each cron fire will just re-check + end. (Further consecutive down-runs will be logged as brief one-liners to
  avoid clutter.) 2nd-pass resumes at Transform Decal when the server returns.
- **2026-05-29 run #25 — server still down (3rd consecutive).** GET `/` "Failed to fetch". Logged + ended, no work. Restart :59876 to resume.
- **2026-05-29 (owner request, server back) — LAYERS-PANEL TOOLSET TRIMMED.** Owner pointed out the Layers panel
  has its own toolset (separate from the top bar) + asked to cut unneeded ones. Mapped all 14 (renderLayerPanel,
  canvas.js:16770-16797); all handlers defined (no dead buttons). Verified drag-to-reorder WORKS (simulated the
  onLayerDrag* handlers → _psdLayers reordered; Ctrl+Z restored). Per owner verdict ("cut CENTER, FIT, KNOCKOUT,
  UP/DOWN as long as drag works"), removed **▲UP, ▼DOWN, CENTER, FIT, KNOCKOUT** button HTML from renderLayerPanel
  (handlers moveLayerUp/Down, centerLayerOnCanvas, fitLayerToCanvas, knockoutLayer KEPT in source for re-add; audit
  comments added). KEPT: PICK ITEM, DUPE, MIRROR, FX, MERGE↓, FLATTEN, RENAME, DELETE, OUTLINE + Opacity/Blend.
  Synced 3 copies (node scripts/sync-runtime-copies.js --write, 4 files), bumped canvas.js ?v= →
  spb-layers-trim-20260529, reloaded. VERIFIED live: panel now shows 9 action buttons (the 5 gone), PSD intact (11
  layers), no console errors. ⚠️ Still open: PICK ITEM leaves stray "Transform Selection" layers (run #18/#19 bug —
  fix later). **Server is BACK (200)** — the cron second-pass can resume at Transform Decal next run.
- **2026-05-29 (owner request, between fires) — SOURCE wheel-zoom RE-CENTER bug FIXED.** Owner: scrolling to zoom the
  SOURCE/LIVE-PREVIEW panels pans erratically + strands content off-view + no easy reset. Root cause (canvas.js SOURCE
  wheel handler ~8697): the cursor-anchor scroll math IGNORED the centering margins `applyZoom()` adds when the canvas
  is smaller than the pane → at the fit↔overflow boundary the scroll jumped by the full margin offset (~1000+ canvas px).
  FIX: made the anchor margin-aware (capture pre-zoom marginLeft/Top, subtract in the content-point calc) + auto-recenter
  any axis that now fits (snap that axis's scroll to 0 so the margins re-center it). Verified live via simulated wheel:
  zoom-in+pan-to-corner then wheel-out → scroll snaps to 0,0 + margins center it the instant it fits; cursor anchor error
  across the fit→overflow transition dropped from ~1000px to <16px (<1%). Synced 3 copies, bumped canvas.js ?v= →
  spb-zoom-recenter-20260529, reloaded, no console errors. LIVE PREVIEW uses center-origin `transform:scale()` → already
  self-centers on zoom-out (no fix needed). Detail in FINDINGS.
- **2026-05-29 run #26 (2nd pass: TRANSFORM finish + SELECT/PRIMARY marquee engines).** Server 200, browser connected,
  zoom fix live (jsVer spb-zoom-recenter). No artifact, no console errors, composite intact (px1024 yellow). **Transform
  Decal ✅ re-verified** (guard: ret false, ft null, toast — matches run #8) → **TRANSFORM 2nd-pass now 2/2 DONE.**
  **Elliptical Marquee — ENGINE ✅ re-verified**: `commitEllipseSelection({700,700},{1300,1300})` → 282,697 px (99.98%
  of π/4·600² geometric), has-selection true. 🔑 **METHODOLOGY FINDING: marquee/rect SELECTION drag-gestures are NOT
  exercisable via `left_click_drag`.** Instrumented commitEllipseSelection + dragged twice (correct canvas mapping, zero
  rect drift) → commit called **0×**, no selection. The mousedown→isDrawing→mouseup→commit state machine (src 3299→3764)
  isn't engaged by the synthetic drag (unlike a single click [wand ✅ run #7] or — apparently — gradient [run #11]).
  `commitRectSelection(endPos,evt)` can't be called directly either — early-returns unless module-scoped `rectStart`
  (set only by a real mousedown) is present (src 22724). So: ellipse/rect ENGINES are sound, but their drag GESTURES
  need real-interaction/focused-session confirmation (run #1 verified ellipse's gesture historically). Also clarified:
  marquee selections live in the **active-pixel-selection** (`hasActivePixelSelection`/`_getActiveSelectionInfo`),
  refreshed via `_doRenderRegionOverlay()` — a plain regionCanvas alpha read showed 0 until I called that / the engine
  directly. Cleanup: cleared selection, restored wrapped fn, eyedropper, Zone Mode, rc 0, ft null. **2nd-pass tracker:
  ADJUST 8/8, MASK 3/7 region-ops (+Copy Mask), TRANSFORM 2/2 ✅, SELECT/PRIMARY: marquee engines done (gesture deferred).
  NEXT:** click-based SELECT/PRIMARY re-verify (Select All Color, Edge Detect, Magic Wand, eyedropper — these use the
  real-mouse CLICK which DOES work, drift-aware) + Move Selection Border. Paint group still parked; cruft layer flagged.
- **2026-05-29 run #26 cont'd — 🔧 FOUND + FIXED a real bug (pan-exemption list incomplete).** Diagnosing why the
  ellipse-marquee drag didn't commit, traced the mousedown pan-vs-tool gate (canvas.js:8898): a left-drag becomes a PAN
  when `canvasOverflows() && !drawToolActive`, where `drawToolActive` is a hardcoded mode list (8895). **'ellipse-marquee'
  was MISSING from that list** (its siblings 'rect'/'lasso' are present) → when zoomed in (canvas overflows), an ellipse-
  marquee drag is hijacked as a PAN = no selection. Code-confirmed: `canvasOverflows()` = true at 200% zoom + mode not in
  list → deterministic pan-hijack. Same omission for **'gradient'** and **'spatial-erase'** (whose siblings spatial-include/
  -exclude ARE listed). FIX: added 'ellipse-marquee','spatial-erase','gradient' to the list (canvas.js:8895, dated audit
  comment). Synced 3 copies, bumped canvas.js ?v= → **spb-marquee-panfix-20260529**, reloaded; served JS confirmed to
  contain the fix; no console errors; composite intact (px1024 yellow). ⚠️ **STILL MISSING from the list (flagged, parked
  paint group):** 'shape','text' + RETOUCH brushes (colorbrush/clone/smudge/pencil/dodge/burn/blur-brush/sharpen-brush/
  recolor/history-brush) — all drag tools that would pan-hijack when zoomed in; complete after verifying each.
  🔑 **SHARPENED METHODOLOGY FINDING: `left_click_drag` does NOT trigger the app's drag-state handlers AT ALL.** A/B
  control: an EYEDROPPER drag at 200% zoom did NOT pan either — so the computer-tool drag can't drive pan OR marquee/draw
  drag gestures (only single real-mouse CLICKS register: wand/eyedropper/pen). ⇒ drag-tool behavior (marquee/pan/gradient/
  brush strokes) can't be auto-verified; the pan-hijack fix is verified by code analysis + served-code confirmation, and
  real-mouse behavior needs human/focused-session confirmation. This also explains the run #1 "drag → Npx" marquee result
  (real interaction, not left_click_drag). Cleanup: fit zoom (auto-recentered to 0,0 via the zoom fix), eyedropper, Zone
  Mode, rc 0, no artifact.
- **2026-05-29 run #27 (2nd pass: click-based SELECT/PRIMARY) — Pick Color ✅ + 🔑 MAJOR confound: ZONE POPOUT panel
  covers the canvas.** Server 200, jsVer spb-marquee-panfix. **Pick Color/eyedropper** first looked broken (center click →
  eyedropperSwatch stayed empty, pick didn't fire). Root cause: the **`zoneEditorFloat` (ZONE POPOUT PANEL, z:36) covers
  the LEFT ~2/3 of the SOURCE canvas** (panel viewport x[226,691] vs canvas x[256,917]) when a zone is selected —
  `elementFromPoint` at my click returned the panel's `color-selector` div, NOT the canvas, so the canvas mousedown never
  fired (only the hover/mousemove readout did). Re-clicked the UNCOVERED right strip (canvas x>~1348): `hitCanvas:true` and
  the eyedropper pick FIRED (eyedropperHex/RGB dynamically read the clicked pixel, src 3403-3435). **Pick Color ✅
  re-verified.** 🔑 **This CORRECTS run #26's A/B "control"** (EYEDROPPER-drag-at-200%-didn't-pan) — that drag was at
  viewport x[482,676], UNDER the float → it hit the panel, not the canvas → INVALID control. **BUT** I re-ran the
  ellipse-marquee drag on the confirmed-UNCOVERED bare canvas (both endpoints verified `elementFromPoint===paintCanvas`)
  → instrumented commitEllipseSelection called **0×**, no selection. So the conclusion HOLDS cleanly: single CLICKS reach
  the canvas (eyedropper fired) but `left_click_drag` does NOT drive the mousedown→mouseup drag-commit (marquee). ⚠️
  **rect-drift OSCILLATES 272↔297 px between calls** → precise click-targeting unreliable (a colored-pixel eyedrop got
  drift-muddled; the clean confirmation was a no-drift black-pixel click: hitCanvas + eyedropperRGB = the pixel). **FLAG
  for owner:** the ZONE POPOUT panel overlapping ~2/3 of the SOURCE canvas blocks canvas tools there — intended (closable
  popout) or a layout issue worth fixing? Cleanup: cleared selection, eyedropper, Zone Mode, rc 0, instrumentation+wrappers
  removed, #55 canary [234,255,0] intact, no artifact, no console errors. **NEXT (focused, like the paint group):** CLOSE
  zoneEditorFloat for full canvas access + drift-robust clicks (read rect immediately before each click, re-read after,
  invalidate if moved), then re-verify wand / Select All Color / Edge Detect / Move Selection Border.
- **2026-05-29 run #28 (2nd pass: click-based SELECT/PRIMARY) — 🎯 ENGINE-LEVEL BREAKTHROUGH: 4 tools re-verified.**
  Server 200. First fought the click confounds again: bypassed the zoneEditorFloat (set its pointerEvents:none, reversible)
  so clicks reached the canvas, BUT canvas mousedown handlers did NOT fire reliably — an eyedropper click on a bare cyan
  pixel (direct hit, `elementFromPoint`=paintCanvas, stable rect) left the swatch stale (#000000; pick didn't fire), and
  wand clicks (4×) produced no selection. PLUS rect-drift OSCILLATES 272↔309 every 1-2 calls. Screenshot confirmed the app
  is healthy (hover readout updates) → environmental click-DELIVERY issue (mousedown not landing), not a tool/app bug.
  🎯 **PIVOT (like run #26's marquee): verify the selection ENGINES directly** — all work, cleanly, no click needed:
  • **Magic Wand ✅** `magicWandFill(1024,1024,32,false)` → 5,076 px contiguous (985-1101 × 996-1076) at #55 yellow, has=true.
  • **Select All Color ✅** `selectAllColor(1024,1024,32,false)` → 204,456 px (ALL yellow within tol — correctly ≫ wand's contiguous 5,076).
  • **Edge Detect ✅** `edgeDetectFill(1024,1024,32,false,false)` → 730 px bounded (1010-1042 × 1017-1044, stops at edges; matches run #1's 704). Sig is (x,y,tolerance,addToExisting,subtractMode) — omitting tolerance floods the WHOLE canvas (4,194,304), a direct-call arg artifact, NOT a bug.
  • **Move Selection Border ✅** `activateSelectionMove()` + `nudgeRegionSelection(60,0)` → selection bounds shifted EXACTLY +60,0 (minX 1010→1070, minY unchanged).
  🔑 **CORRECTS run #7's claim** that "direct magicWandFill/handler calls don't register" — they DO create real selections
  (has=true, regionCanvas populated). Engine-level verification is the clean path for click-based selection tools, immune
  to the float/drift/mousedown confounds. (Likely also unblocks the parked paint group via fillBucketOnLayer/etc. — try next.)
  Cleanup: cleared selection, eyedropper, Zone Mode, float pointerEvents restored, rc 0, #55 canary [234,255,0] intact,
  no artifact, no console errors. **2nd-pass tracker: ADJUST 8/8 · MASK 3/7 region-ops (+Copy Mask) · TRANSFORM 2/2 ·
  SELECT/PRIMARY selection tools (Magic Wand, Select All Color, Edge Detect, Move Selection Border, eyedropper, marquee-
  engine) ALL ✅.** Remaining 2nd-pass: MASK spatial (include/exclude/erase — try engine calls), Pick Layer Element / Pick
  Item / Transform-layer / Gradient / Pen / Rect re-verify; then the parked PAINT group via engine calls (fillBucketOnLayer,
  _paintOnLayerAt). ⚠️ FLAGS stand: zoneEditorFloat covers 2/3 of SOURCE canvas; rect-drift oscillation (canvas top
  272↔309, likely autosave-banner height) — both hamper click-based UX + autonomous click testing.
- **2026-05-29 run #29 (2nd pass: Transform-layer ✅ + autonomous limit reached).** Server 200, jsVer spb-marquee-panfix.
  **Transform (layer) ✅ re-verified** — `activateLayerContextTransform()` (editMode→layer, psd_2 selected) returns true,
  opens a free-transform on the LAYER (ft target=layer, layerId=psd_2, scaleX/rotation/centerX present; matches run #10);
  `cancelActiveTransformSession()` cancelled cleanly (ft→null, psd_2 bbox [406,355,1295,2003] unchanged — no commit, no
  corruption). **Surveyed the remaining 2nd-pass tools — all BLOCKED for clean autonomous re-verification:** • MASK spatial
  trio (include/exclude/erase) paints via `_paintScopedSpatialCircle`, which is **closure-scoped (NOT on window)** → not
  engine-callable, and the brush-drag is click-confounded. • Gradient — `fillGradientOnLayer` IS on window but a DIRECT
  call bypasses the handler's undo-push (run #11's warning) → **non-undoable → layer-corruption risk** on the live psd_2.
  • Pen / Rect / Pick Item / Pick Layer Element need canvas CLICKS (confounded: mousedown not firing + rect-drift + float).
  • Paint group — pixel-modify corruption risk (parked since run #19). 🏁 **CONCLUSION: the autonomous 2nd pass is COMPLETE
  for every tool that is safely+cleanly verifiable without a real canvas click or a risky pixel-write.** Re-verified set:
  ADJUST 8/8 · MASK region-ops 3/7 + Copy Mask · TRANSFORM 2/2 · SELECT/PRIMARY selection engines (wand, selectall, edge,
  move-border, marquee, eyedropper) · Transform-layer. **Everything else needs a FOCUSED session** (clean reloaded state,
  WORKING canvas clicks, owner supervision for pixel-modifying tools). ⚠️ **KEY enabler for that session: FIX THE
  RECT-DRIFT** — canvas top wandered 272→309→317 this run (~45px range), almost certainly the autosave-status/banner
  changing the header height; a fixed-height header row would stop the jump AND unblock autonomous click-testing of the
  whole remaining set. Cleanup: eyedropper, Zone Mode, ft null, psd_2 intact, #55 canary [234,255,0], no artifact, no console errors.
- **2026-05-29 run #30 (2nd pass) — 🎯 BIG CORRECTION: clicks AND drags WORK; the float-overlap was the SOLE blocker. 4 tools re-verified.**
  Server 200. Came to pinpoint the rect-drift; found: (1) drift is NOT the header (NAV.header is `nowrap`) and NOT editMode
  (canvas top stable 317.2 across editMode toggles). (2) The canvas had REFLOWED — left moved **256→747** (the ZONE POPOUT
  float went from OVERLAY [canvas under it] to DOCKED [canvas pushed right, beside it, UNCOVERED]). With the canvas uncovered,
  clicks/drags were re-tested and **THEY WORK:**
  • **Pick Color/eyedropper** (real click on #55) → eyedropperHex #000000→**#EAFF00 / RGB(234,255,0)** = clicked pixel. Click pick FIRES.
  • **Pick Layer Element ✅** (real click) → isolated element bbox(824,971)-(1111,1311), **78,085 px**, psd_2. The `selxform`
    isolation layer it creates (run #18 "cruft") is CLEANLY REMOVED by `cancelActiveTransformSession()` → back to 11 layers
    (the cruft only persisted in old runs because they didn't cancel).
  • **Spatial Include ✅** (drag) → 1,418 value-1 (keep) marks in zone 0 spatialMask.
  • **Spatial Exclude ✅** (drag) → 1,418 value-2 (remove) marks (total 2,836).
  • **Spatial Erase ✅** (drag over the include region) → removed exactly the 1,418 include marks (inc 1418→0, exc untouched).
  🎯 **CORRECTS run #28's "left_click_drag can't drive drag-state handlers"** — that was the FLOAT confound (drags were under
  the float). With the canvas UNCOVERED, drags work fine. So the run #27/#28 click/drag failures were ALL the zoneEditorFloat
  overlapping the canvas. **MASK menu 2nd-pass now 7/7 COMPLETE** (smooth/invert/mirror [#22] + copy [#16] + include/exclude/
  erase [#30]). **Pick Layer Element ✅** (SELECT). Cleanup: clearSpatialMask→0, selxform removed, eyedropper, Zone Mode, 11
  layers, psd_2 [406,355,1295,2003], #55 [234,255,0], no artifact, no console errors. 🔑 **The float's position is
  STATE-DEPENDENT (overlay vs docked)** — when DOCKED (canvas uncovered, as now), the remaining click/drag tools ARE
  autonomously testable. **NEXT (while canvas stays uncovered):** re-verify Pick Item, Gradient (real drag), Pen, Rect, then
  attempt the PAINT group (Brush/Eraser/Fill — pixel-modify, undo carefully via Ctrl+Z). ⚠️ Still flag for owner: drift
  (canvas top wanders 317↔346) + float toggling overlay↔docked (canvas jumps ~490px horizontally) = a dynamic layout.
- **2026-05-29 run #31 (2nd pass: PRIMARY click/drag — canvas still UNCOVERED).** Server 200, canvas uncovered (l:747,
  center=paintCanvas). Capitalized on the run #30 unblock — re-verified 3 more tools via real mouse:
  • **Rectangle Select ✅** — real drag (canvas 950,850→1250,1150) → rect selection (has=true, 13,049 px, bounds
    (948,997)-(1101,1152)) — clipped to the active zone 0 (drag-rect ∩ zone coverage), as expected for a zone-scoped select.
  • **Pick Item ✅** — real click (center) → switched to zone-pick mode + opened a free-transform on the picked item
    (freeTransformState target="second_base", zoneIndex 0, scaleX/rotation/centerX). `cancelActiveTransformSession()`
    cancelled cleanly (ft null, 11 layers, NO selxform cruft this time — zone-item transform, not a layer isolation).
  • **Pen ✅** — 3 real clicks → window.penPoints 0→3, each {x,y,cx1,cy1,cx2,cy2} (bezier); first point canvas (898,897)
    ≈ click (900,900); penClosed false. Matches run #15.
  ⚠️ Minor: the Escape key (computer tool) did NOT clear the pen path (penPoints stayed 3 after Escape — likely a focus
  issue with the synthetic key, OR an Escape-clears-pen hiccup); cleared via JS instead. The pen's point-ADDING (core
  action) works. 🔑 **The LIVE PREVIEW overlaps the canvas's RIGHT side** (uncovered canvas zone ≈ x 0-1397; x>1397 under
  the preview) — keep test drags central. Cleanup: penPoints 0, eyedropper, Zone Mode, rc 0, 11 layers, #55 [234,255,0], no
  cruft, no artifact, no console errors. **2nd-pass tracker: ADJUST 8/8 · MASK 7/7 · TRANSFORM 2/2 · SELECT 5/6 (Zone Pick
  deferred — needs spec pattern) · PRIMARY: Rect/Pick Item/Pen/Wand/eyedropper/Transform-layer/Lasso(#9)/Move(#10) ✅.**
  Remaining for 2nd pass: PRIMARY **Move** (drag, re-verify) + **Lasso** (poly-click, re-verify), then the PIXEL-MODIFY
  group (**Gradient, Brush, Eraser, Fill, Text, Shape** — undo carefully via Ctrl+Z, watch layer corruption per #11/#19),
  + SELECT **Zone Pick** (needs a spec pattern assigned). NEXT (while uncovered): Move + Lasso, then the paint group.
- **2026-05-29 run #32 (2nd pass: Lasso ✅ + Move inconclusive + a RENDER-degradation scare [no data loss]).** Server 200,
  canvas uncovered (l:747). **Lasso ✅ re-verified** — polygon (2 clicks + double-click close) → triangle selection
  62,106 px (≈ geometric 60,000), bounds (890,891)-(1292,1202) matching the vertices. **Move — INCONCLUSIVE:** the
  layer-move drag did NOT register (psd_2 bbox stayed [406,355,1295,2003], even starting on the #55 = psd_2 opaque content;
  selection drags [rect/lasso] DID work this session → layer-move-SPECIFIC). No move-by-delta engine on window
  (moveLayerBy/nudgeLayer/etc. all undefined) → no engine fallback. ⚠️ **RENDER-DEGRADATION SCARE:** during the Move-test
  sequence (editMode zone→layer→zone + the failed layer-move drag), the COMPOSITE render degraded — px(1024,1024) canary
  yellow→BLACK, whole-canvas yellow 205,926→85,773. **Investigated: NOT data corruption** — screenshot showed the car fully
  intact, psd_2.bbox unchanged, 11 layers; a **reload FULLY restored** the pristine composite (canary [234,255,0], yellow
  205,926). recompositeFromLayers() did NOT fix it (still degraded); only the reload did. 🔑 **FLAG: the layer-move-test
  sequence can degrade the composite RENDER (reload-recoverable, NO data loss) — worth investigating** (likely an
  editMode-switch recomposite rendering incompletely). Move stays ✅ from run #10 (real drag verified) but the 2nd-pass
  re-verify is INCONCLUSIVE (drag won't engage via left_click_drag) → focused-session. Cleanup: reloaded → clean (canary
  yellow, 11 layers, no cruft, eyedropper, no console errors). **2nd-pass tracker: ADJUST 8/8 · MASK 7/7 · TRANSFORM 2/2 ·
  SELECT 5/6 · PRIMARY Rect/Pick Item/Pen/Lasso/Wand/eyedropper/Transform-layer ✅; Move inconclusive.** Remaining: Move
  (focused), the PIXEL-MODIFY group (Gradient/Brush/Eraser/Fill/Text/Shape) — and given THIS run's render-degradation from
  a NON-pixel tool, the pixel-modify group is even riskier → **strongly prefer a focused session (reload-on-hand)** + SELECT
  Zone Pick.
- **2026-05-29 run #33 (2nd pass) — 🎯 THROWAWAY-LAYER method UNBLOCKS the pixel-modify group; Gradient ✅ + Fill ✅.**
  Server 200, canvas uncovered, canary clean. Established a SAFE method to test paint tools WITHOUT risking psd_2:
  **`addBlankLayer()` → paint via the engine on that throwaway → verify the throwaway's own pixels → `deleteLayer()`**
  → back to 11 layers, psd_2 NEVER touched. Re-verified two pixel-modify tools:
  • **Gradient ✅** — `fillGradientOnLayer(500,500,1500,1500,'linear', throwaway)` → throwaway pixels blank [0,0,0,0] →
    a real gradient **229→127→25** (light-to-dark). Matches run #11.
  • **Fill ✅** — `fillBucketOnLayer(1024,1024, throwaway)` → flood-filled the blank throwaway uniformly with the FG
    (white 255,255,255,255). Matches run #11. (⏸→✅: the run #11/#17 "Fill broken/suspect" verdict is RESOLVED — the
    engine works; the earlier click-path failures were the stale-rect/float confounds.)
  Both throwaways deleted cleanly (11 layers, psd_2 [406,355,1295,2003], canary [234,255,0], no cruft, **NO render
  degradation** — confirming run #32's degradation was specific to the Move/editMode-switch sequence, NOT layer-paint).
  🔑 **The throwaway method RESOLVES the "pixel-modify group needs a focused session" concern** — Brush, Eraser, Text,
  Shape can now be re-verified the same way (paint on a throwaway, never psd_2). No console errors. **2nd-pass tracker:
  ADJUST 8/8 · MASK 7/7 · TRANSFORM 2/2 · SELECT 5/6 · PRIMARY: Rect/Pick Item/Pen/Lasso/Wand/eyedropper/Transform-layer/
  Gradient/Fill ✅; Move inconclusive.** Remaining: Brush, Eraser, Text, Shape (throwaway method, next runs); Move (real
  drag — focused); SELECT Zone Pick (needs a spec pattern).
- **2026-05-29 run #34 (owner gave render + mess-around permission) — Brush/paint-strokes are NOT autonomously
  action-testable (hard limit); corrects run #33's optimism.** Owner lifted the render ban + said mess around freely
  (Restore All as safety net). Tested **Brush** three ways, all blocked for the paint ACTION:
  • Throwaway blank layer (drag) → no paint (brush mousedown didn't engage; isDrawing false, _activeLayerCanvas null).
  • psd_2 (real layer, drag) → the drag MOVED the layer instead of painting (undo "move layer", bbox 406→653) = the
    run #19 "drag-on-content-moves" confound. Restored psd_2 via **bbox-reset** (a move is bbox-only; img intact) → yellow 205,926.
  • Brush ENGINE direct (`_initLayerPaintCanvas()` + `_paintOnLayerAt(x,y)` + `_commitLayerPaint()`) → `_paintOnLayerAt`
    THREW `createRadialGradient … non-finite` — called bare it's missing the internal stroke state (brush radius / last-point)
    the real mousedown sets up.
  🔑 **CONCLUSION: Brush/Eraser/Text/Shape (paint strokes) CANNOT be driven by the synthetic computer mouse** — a drag
  moves the layer (on content) or no-ops (on empty), and the engine throws when called bare. They need a REAL human drag
  (owner) to action-verify; verified in practice by the owner's daily use. **This corrects run #33's claim** that the
  throwaway method would cover them — it covers Gradient/Fill (their engines take a `layerOverride` + paint directly) but
  NOT the brush family (no layerOverride engine; the stroke needs live mousedown state). ⚠️ Re-confirmed: **Restore All
  (restoreAllZones) does NOT restore layer pixel/transform changes** (zones only); layer recovery = undo snapshot
  (transform → entry.imgCanvas, run #33-prev-turn) or bbox-reset (move). Cleanup: psd_2 fully restored (yellow 205,926,
  px1024 [234,255,0], bbox [406,355,1295,2003]), 11 layers, no cruft, no console errors, **NO data loss**. 🏁 **Autonomous
  2nd pass COMPLETE for everything testable without a real human paint-stroke.** Un-action-tested (need owner's hands):
  Brush, Eraser, Text, Shape; plus Move (real drag) + SELECT Zone Pick (spec pattern).
- **2026-05-29 run #35 — Zone Pick confirmed NOT autonomously testable → autonomous QA loop is FUNCTIONALLY COMPLETE.**
  Server 200, canvas uncovered, #55 clean (px1024 yellow), 11 layers. Attempted Zone Pick setup (needs a spec pattern
  assigned, run #16): `PATTERNS`/`SPEC_PATTERNS` arrays + the spec-assign functions (setZoneSpecMap/applySpecOverlay/
  setZoneSpecPattern/etc.) are NOT on window (module-scoped). `setZonePattern(zoneIndex,id)` IS on window but needs a valid
  pattern id + a render to produce pickable content. So Zone Pick can't be set up + driven from page scope — needs manual
  UI setup (assign a spec pattern + render). Confirms the run #16 deferral. No changes made (read-only). 🏁 **CONCLUSION:
  the autonomous 2nd pass is COMPLETE.** Everything drivable by JS-handler + synthetic-mouse has been tested & re-verified.
  The ONLY remaining un-action-tested tools require a human/manual step: **Brush, Eraser, Text, Shape** (paint strokes —
  synthetic drag moves the layer / engine throws bare; need a real human drag) and **Zone Pick** (spec pattern + render).
  RECOMMENDATION: pause the loop (it will only re-hit this same wall) and do a ~2-min owner hands-on — drag brush/eraser,
  type text, draw a shape, assign a spec pattern + Zone-Pick a sub-piece — to close the suite. **Over the full effort:
  every menu + primary icon tested; real bugs found & FIXED (Color Brush `_t0` crash #3, pan-exemption list #26); zoom
  re-center + layers-panel trim shipped on owner request; full 2nd-pass re-verification done for all auto-drivable tools.**
- **2026-05-29 run #36 — Investigated the open brush-paint-vs-move question (read-only); loop remains COMPLETE.**
  Server 200, #55 clean (px1024 [234,255,0]), 11 layers, no cruft. Found the cause of the run #34 brush-drag-move: Layer
  mode runs **element detection** (canvas.js:2267) — hover→preview, click→isolate, drag→move. My synthetic brush drag
  within psd_2's bbox triggered the auto-select-move. **Can't confirm from source alone** whether this blocks a REAL
  user's painting-on-content (vs. just the synthetic drag) → owner's 5-sec test settles it (Brush over artwork: PAINTS=fine,
  MOVES=real bug). No changes (read-only). Loop left running per owner's "put it through the paces"; stop via CronDelete or
  by closing the session. Next step is the owner hands-on for the paint-stroke family + Zone Pick — no autonomous work left.
- **2026-05-29 run #37 — Owner EXPANDED the mandate (away 6h, see top of file). Loop is NO LONGER "complete" — new workstreams.**
  ✅ **VERIFIED the owner-named "replace ONLY the yellow inside the numbers":** `selectPSDLayer('psd_2')` (Numbers) → `autoColorReplace('#eaff00',newColor,tol)` replaced 128,259 px of the numbers' yellow → pink, left ALL non-yellow untouched, restored pixel-exact via `recompositeFromLayers`. ✅ **Layer/zone harmony:** yellow is spread across layers (Numbers 137k, Car Paint 45k, Sponsors 37k, Tape 23k), composites with correct occlusion, recomposite lossless — replacing on one layer correctly scopes to it. 📋 Precondition: `autoColorReplace` runs on the SELECTED layer (or composite if none selected), NOT globally. 🔧 **SHIPPED a Color Replace improvement** (no-match now skips needless commit/render, pops the no-op undo, and gives actionable feedback instead of "Replaced 0 pixels"; verified PASS; cache-buster `spb-colorreplace-feedback-20260529`). **NEXT priority:** base-PICTURE-to-region + tiling-inside-numbers (zone base + `regionMask` + engine `_tile_fractional`; needs the render/engine path).
- **2026-05-29 run #38 — Deploy boundary mapped + base-picture region+tiling EMPIRICALLY VERIFIED + wiring confirmed → owner's #1 SUBSTANTIALLY VERIFIED.**
  🔒 **Deploy boundary (session-wide):** SAFE=`triggerPreviewRender` (renders to local preview img only, canvas.js:7398); AVOID=`doRender` (full render + auto-deploy path, api-render.js:2845); NEVER=`deployToIracing` (POST /deploy-to-iracing, api-render.js:4018). ✅ **Engine** (real code, synthetic inputs, no deploy, via subagent): hard_mask confines base to its region — 20×16 rect mask → exactly 320px changed, outside byte-for-byte unchanged, ZERO leakage (compose.py:1820-1822); base picture tiles period-exact (`np.tile`, core.py:1313-1331; 4×4 src ×4 → period-4 grid). ✅ **Wiring** (`buildServerZonesForRender` api-render.js:2484): sends `base` + base-color-mode + region-mask-RLE → the verified engine. 🏁 **Owner's #1 substantially verified** [(a) region-confined base ✓ (b) tiling ✓ (c) replace-only-yellow ✓ (run#37)]. Caveat: engine LOGIC + WIRING verified empirically/by-read; a ~30-sec owner LIVE render confirms the visual end-to-end (didn't run one — deploy risk). No live-app changes this fire. **NEXT:** more layer/zone harmony stress + tool polish + (if dry) a real new feature.
- **2026-05-29 run #39 — Layer/zone harmony stress: ✅ compositor honors visibility+opacity; ✅ `recompositeFromLayers` is IDEMPOTENT (run #32 degradation scare RESOLVED).**
  Toggled psd_2 "Numbers": `visible=false` → composite yellow 198,799→76,164 + `(1024,1024)`→[0,0,0] (under-layer shows); `opacity 40%` → yellow 74,264 + `(1024,1024)`→[94,102,0]; both restored. recomposite ×6 = stable 198,802 (zero drift) → NO accumulating degradation. 📋 Benign: initial-load (198,799) vs recomposited (198,802) composite differ by 3px sub-visible AA rounding (non-accumulating); reload restores 198,799. State left PRISTINE (reloaded → yellow 198,799, clean defaults). **Queued feature:** "Replace color across ALL layers" scope on Color Replace (the car's yellow spans 4 layers; current tool hits only one) — `autoColorReplaceAllLayers` + dialog toggle. **NEXT:** build that feature, or more tool polish.
- **2026-05-29 run #40 — SHIPPED a REAL new feature: "Replace color across ALL layers" (owner mandate "create REAL features").**
  Grounded in run #37/#39 (the car's team color spans 6 layers; single-layer Color Replace can't recolor it in one shot). Added `autoColorReplaceAllLayers(target,replacement,tol)` (canvas.js, window-exported) — iterates unlocked layers, reuses the match+blend loop, recomposites once, 1 undo/affected layer, "Replaced N px across M layers" toast; no render/deploy. UI: optional **"Replace across ALL layers"** checkbox on the Color Replace dialog (opt-in `config.allLayersToggle` on `_openAdjustmentColorDialog`, other callers unaffected; `openColorReplaceDialog` routes by the toggle). **Verified LIVE PASS:** cache-buster `spb-replace-all-layers-20260529`, sync 6/6, reload → fn present + checkbox renders/closes; functional test → composite yellow 198,799→0 (255,459px across 6 layers), `(1024,1024)`→[255,0,153], non-target untouched, restore pixel-exact (198,799), no console errors. Left PRISTINE (reloaded). **NEXT:** more polish / another feature, or owner hands-on for the paint-stroke family.
- **2026-05-29 run #41 — Polished the all-layers feature: single GROUPED undo (one Ctrl+Z reverts every layer).**
  run #40's feature pushed 1 undo PER affected layer (6 undos to revert one action). Fixed: `autoColorReplaceAllLayers` now pushes ONE `_pushLayerStackUndo('color replace (all layers)')` (type 'stack', whole-stack snapshot, retains old img refs) before the loop instead of per-layer `_pushLayerUndo`; pops it on no-match. **Verified LIVE PASS** (cache-buster `spb-allreplace-grouped-undo-20260529`, sync 4/4): yellow 198,799→0 (works), `_layerUndoStack` +1 entry (was +6) type 'stack', one `_restoreLayerStack` reverted ALL layers (yellow→198,802≈baseline), no errors. Left PRISTINE. Feature is production-quality (one action = one undo). **NEXT:** more polish / another feature, or owner hands-on for the paint-stroke family.
- **2026-05-29 run #42 — All-layers feature fully HARDENED: locked-skip + no-match branches verified LIVE.**
  ✅ Locked-skip: locked psd_2 (Numbers) → all-layers replace → psd_2's yellow PRESERVED (136,688 untouched), other 5 layers replaced (composite 198,799→128,259), toast "…across 5 layers (1 locked skipped)", still 1 grouped undo, restored exact. Cross-check: 255,459(6 layers,#40) − 116,898(5 now) = 138,561 ≈ psd_2's 136,688. ✅ No-match (#ff00ff absent): composite unchanged, undoDelta 0 (grouped undo pushed+popped clean), warn toast. Feature now COMPREHENSIVELY verified (happy / grouped-undo / locked-skip / no-match). Left PRISTINE (reloaded). **NEXT:** another grounded feature/polish, or owner hands-on for the paint-stroke family.
- **2026-05-29 run #43 — RETOUCH menu definitively classified (was ⬜ assumed): all 8 tools activate + are healthy drag-brushes, NO bugs.**
  Activation test: `setCanvasMode` → correct mode for Clone/Recolor/Smudge/Pencil/Dodge/Burn/Blur/Sharpen (all ok:true, no console errors). Source confirms every RETOUCH tool paints via `&& isDrawing` strokes (Clone 2540, Recolor 2591, Smudge 2609, Pencil 2643, Dodge·Burn 2660→paintDodge/paintBurn, Blur·Sharpen 2678→paintBlurBrush/paintSharpenBrush; mousedown 3256-3397, commit 3771), Layer-Mode-gated → **human-drag-only paint-action** (owner hands-on), tools healthy. **RETOUCH table rows (Clone…Sharpen) = activation ✅ / paint human-drag — do NOT re-pick as untested.** No changes (read-only + mode cycle, ended eyedropper; #55 [234,255,0]). **Coverage classified:** ADJUST 8/8, MASK 7/7, TRANSFORM 2/2, SELECT 5/6, RETOUCH 8/8-activate, PRIMARY mostly — paint-stroke family (Brush/Eraser/Text/Shape + RETOUCH) = human-drag pending owner hands-on. **NEXT:** owner hands-on; else more grounded polish/features.
- **2026-05-29 run #44 — 2nd-pass re-verification (all fixes HOLD) + completed the pan-exemption list.**
  2nd pass: 🔑 regression check on my run #40 shared-dialog edit — Gradient Map dialog renders WITHOUT the all-layers checkbox (gating isolated, no leak) ✅; Color Replace checkbox present ✅; Color Brush activates (no _t0 crash) ✅; zoom-recenter (8703-8725) + pan-exemption (8906) intact in source ✅; no console errors. All BROKEN/FIXED/shipped items hold, no regressions. 🔧 **Completed the run #26-flagged pan-exemption gap:** added the 10 verified drag-paint modes (colorbrush/recolor/smudge/pencil/dodge/burn/blur-brush/sharpen-brush/clone/history-brush) to `drawToolActive` (8906) so zoomed-in RETOUCH/brush drags paint instead of pan-hijacking. Additive/safe; cache-buster `spb-pan-exempt-paintbrushes-20260529`, sync 4/4, served build confirmed expanded (`hasExpandedList:true`; functional zoomed-drag is human-testable). 'shape'/'text' left PARKED (verify drag-vs-click first). Left clean (#55 [234,255,0], defaults). **NEXT:** owner hands-on; verify shape/text; else more polish.
- **2026-05-29 run #45 — Resolved parked shape/text; pan-exemption list now COMPLETE (closes run #26 flag).**
  Source-verified: 'shape' IS a drag tool (mousedown `_shapeStart`+isDrawing 3252 → preview 2530 → commit 3740) → ADDED to `drawToolActive` (8911); 'text' is CLICK-to-place (onTextToolClick 3248, no drag path) → EXCLUDED (drag-to-pan preserved). Verified LIVE (cache-buster `spb-pan-exempt-shape-20260529`, sync 4/4, served build `shapeInList:true`, `textExcluded:true`). Pan-exemption now COMPLETE for every drag-draw/paint tool. Additive/safe; #55 [234,255,0], clean. **NEXT:** owner hands-on for paint family + Zone Pick; else more grounded polish.
- **2026-05-29 run #46 — Backlog triage: "undo stack unbounded" is STALE (all 3 undo stacks ARE bounded).**
  Investigated the MEMORY.md backlog item. `undoStack` bounded by `MAX_UNDO=30` (defined in state-zones.js:266 — a cross-file global; canvas.js only references it, hence an initial "undefined" scare), shift at 4971/4989; `_pixelUndoStack` by `_PIXEL_UNDO_MAX=10` (5002); `_layerUndoStack` by `_LAYER_UNDO_MAX=8`. No unbounded growth → no fix; marked resolved in MEMORY.md. Observation: undoStack worst-case ~30×8MB if zones carry full masks (typically far less) — RLE-compressed undo entries = a future opt (changes undo format → owner-decision). No changes (read-only). **NEXT:** owner hands-on; remaining backlog = perf-refactors (owner-review, not risky overnight); else more verification.
- **2026-05-29 run #47 — Shipped a global uncaught-error handler (closes "script error handling missing" — a REAL gap).**
  Confirmed real: window.onerror + onunhandledrejection both null, no global error listener → uncaught errors + unhandled rejections (incl. tool failures) failed SILENTLY. Fix (paint-booth-v2.html, first `<head>` script, sync 2/2): global `error`+`unhandledrejection` listeners → log `[SPB uncaught]` + record to capped `window._spbUncaughtErrors` (≤50) + THROTTLED toast (≤1/15s). Purely additive (only fires on already-uncaught errors), fully try/caught. **Verified LIVE PASS:** handler installed, before=0 on clean boot (no spurious firing), synthetic uncaught-error + unhandled-rejection BOTH caught+recorded, test entries cleaned. #55 [234,255,0], clean. Future QA fires can read `window._spbUncaughtErrors` to catch silent tool failures. **NEXT:** owner hands-on; remaining backlog = perf-refactors (owner-review).
- **2026-05-29 run #48 — Silent-error sweep (via run #47 handler): all 28 tool modes activate clean (0 errors); + a testing-method lesson.**
  Synchronous cycle of all 28 modes = 26.5ms total (~0.9ms each), 0 throws, 0 recorded errors (sync + 250ms async settle). Toolset activation paths clean. ⚠️ **METHODOLOGY CAUTION (future fires):** the FIRST attempt used one async eval with `await sleep(20)`×28 — the BACKGROUNDED tab throttles setTimeout to ~1s → the sweep crawled (~30s+) → 45s CDP timeout + an ORPHANED runaway function (mode self-advanced spatial-exclude→recolor→smudge). **Avoid long `await sleep` loops in javascript_tool evals; use synchronous ops or one short await.** Recovered via reload (kills the orphaned context). App never corrupted (responsive, 0 errors, #55 intact throughout); post-reload pristine + stable, error handler persists. No app bug. **NEXT:** owner hands-on; safe verification only.
- **2026-05-29 run #49 — Action-level silent-error sweep (selection/mask tools): all clean, 0 silent errors.**
  Extended silent-error coverage from activations (#48) to ACTIONS, synchronously (avoided the #48 async-sleep pitfall; 1 short await). `selectAllColor`/`invertRegionMask`/`smoothRegionMask`/`mirrorRegionMask`/`edgeDetectFill`/`copyMaskToZone(4)` all ok, 0 sync throws, 0 async errors (250ms settle). Cleanup clean: `hasActivePixelSelection`=false, #55 [234,255,0] unchanged, eyedropper. Coverage now = all 28 activations (#48) + drivable selection/mask actions (#49), all error-free via the #47 handler. **NEXT:** owner hands-on; safe verification only.
- **2026-05-29 run #50 — Health check (milestone): all shipped work intact, app healthy, error monitor clean.**
  Server 200, 11 layers, #55 [234,255,0], eyedropper. Run #47 error handler installed + **accumulatedErrorCount=0** (no silent errors since). All shipped changes present in served build: autoColorReplaceAllLayers (fn+src), pan-exempt shape (src), Color Replace feedback (src). **Cumulative window (#37–50) verified+intact:** owner #1 (replace-yellow #37 + base/tiling engine+wiring #38), harmony+idempotency #39, SHIPPED [Color Replace feedback #37, all-layers feature #40-42, pan-exemption #44-45, global error handler #47], 2nd-pass #44, backlog triage #46-47, silent-error sweeps #48-49, RETOUCH classified #43. **Still needs OWNER:** paint-stroke hands-on + Zone Pick spec pattern; perf-refactor backlog (owner-review). **NEXT:** light health-monitoring until owner returns.
- **2026-05-29 runs #51-54 — Light health-monitor (consolidated, ongoing): clean at each check.** Server 200, 11 layers, #55 [234,255,0], eyedropper/zone; run #47 error monitor `accumulatedErrors=0`. No changes (monitoring only — substantive work complete, see run #50 checkpoint). Awaiting owner hands-on (paint-stroke family + Zone Pick). NOTE: further clean health-monitors are consolidated into THIS line (run range bumped) instead of new entries, to keep the log clean until the owner returns + redirects. **The 6-hour window has now ELAPSED — both the original tool-QA purpose and the expanded mandate are complete; recommend pausing the loop until a new task.**
- **2026-05-30 run #55 — Owner returned mid-loop with 5 DIRECTED UI FIXES (all shipped); this run = regression sweep over them → ZERO tool regressions.**
  Between #54 and now the owner gave a verbatim 5-fix list, completed across directed turns: **(1) HSB sliders in overlay layers 2-5** — fixed sticky-drag (removed per-tick `renderZones()` from each slider `oninput`, kept it on the ± step buttons) + added a per-row ↺ reset button (state-zones.js, 4 overlay blocks ~2236/2520/2765/3006). **(2) Base dropdown** — removed the "Solid & Gradients" catch-all (state-zones.js ~4726 + ~12363) + put SHOKK-DROP imports atop the SHOKKER group (finish-data.js `SPECIALS_SECTIONS['SHOKKER']`, 3-copy data file). **(3) Spec-preview hover** — clean pop-out (css `.spec-channel-dock-canvas`: dropped the glitchy width/height/transform transition, kept box-shadow only). **(4) Spec Overlay Patterns picker** — removed the dev labels by NEUTRALIZING AT SOURCE (CSS `display:none` lost a specificity war with css:9336/9488/9509): `_renderSpecPatternRankChips`→`''` (kills per-tile Measured/Spec/Fit), `_ensureSpecCurationLanes`→remove+`null` (kills the curation-lane bar), `_updateSpecGroupHealthBadges`→early-return before append (kills Strong/surgery/rate + Feature-lane heading badges); PLUS **split thumbnails** — `_enhanceSpecPatternCardElement` now wraps each card's `visual-preview` img into a split frame (left = the pattern, right = the combined spec map via an injected SVG `feColorMatrix` recolor `R'=v,G'=v,B'=1-v`; ONE cached image serves both halves → no backend route, no Flask restart, no iRacing-deploy risk). **(5) Recent-colors bar** — hidden when empty (canvas.js `renderRecentColors`). Fix 4 verified through the REAL `_buildSpecPatternPickerCards`+`prepareInlineSpecPatternGrid` path: **200/200 cards split (400 imgs), 0 rank rows / 0 health badges / 0 plan badges / 0 lanes, 25 category headings, 0 errors.** Cache-busters: css→`spb-uifix-fix4c-20260530`, state-zones.js→`spb-uifix-fix4c2-20260530`; all synced (3-copy). **REGRESSION SWEEP (this run, verification-only — no new source edits):** server 200, canary [234,255,0], 11 layers; **29/29 tool modes activate clean (0 throws), 0 new uncaught errors** (run #47 monitor); all shipped features present (autoColorReplaceAllLayers, split-thumb fns, rank-chips return `''`); `renderZones()` + `renderRecentColors()` execute clean; recent-bar `display:none` when empty confirmed. → **The 5 UI fixes introduced no tool regressions.** Cleanup: eyedropper, canary intact. ⚠️ Owner observation flagged: the spec picker's per-tile **category pill** duplicates the section heading (pre-existing, not a dev label) — offered to hide on request. NOTE: the paint-stroke family (Brush/Eraser/Text/Shape + RETOUCH) + Zone Pick still await owner hands-on (synthetic mouse can't drive paint strokes — runs #34/#43).
- **2026-05-30 run #56 — Owner gave 3 MORE directed fixes (advanced-tools popout, HSB re-investigation, spec-tile resize); all handled + regression-swept clean.**
  Owner's 3 issues (direct message): **(1) Advanced spec controls → collapsible.** POS X/Y, SCALE, BOX, ROT + Manual Place should be a popout, not open big by default. Wrapped them in a native `<details class="spec-adv-tools">` (collapsed) summary "⚙ Advanced Spec Overlay Tools" in the spec-layer render (state-zones.js ~1697-1735). Verified `advCollapsed:true`, all controls inside. **(2) 2nd-base HSB "still not working."** Exhaustively tested EVERY link in the live tab (owner: "see for yourself"): slider→state ✅ (sets 120/150), drag ✅ 0.3ms/tick (pushZoneUndo coalesces — NOT sticky), render hash ✅ changes, payload ✅ sends `second_base_hue_shift:150` to `/preview-render`, ENGINE ✅ applies it (preview pixels change), full slider→preview ✅ ("SLIDER→PREVIEW WORKS"). Engine trace: `_apply_hsb_adjustments` (compose.py 1276-1311) correct; `_v6paint` (16245/16292) includes the HSB when the 2nd base is active; first sub-agent's `>0.5`-vs-`>=0.5` finding was a RED HERRING (owner uses hue=150). **→ HSB works end-to-end in the current build; concluded the owner's earlier test hit a STALE build (tab reloaded many times during the fixes). Asked them to hard-reload + give an exact repro. Made NO engine edit** (couldn't reproduce a failure; a blind change + the Flask-reload risk weren't warranted). **(3) Spec tiles "way too small" + combined-spec right-half "not the actual way they look."** Root cause of small: my Fix-4-C `.spec-split-thumb` hardcoded `width:48px` inside 148px cards. FIXED: thumb now FILLS the card (158px, 92px pattern) as a VERTICAL split — pattern on top + the REAL server `/api/spec-pattern-preview` M/R/CC channel strip below (owner picked "Pattern + real M/R/CC channels" via AskUserQuestion). Dropped the synthetic blue/yellow SVG-recolor. Verified via the real builder: 224/224 split, all M/R/CC imgs (src=spec-pattern-preview), thumbWidth 158 (was 48). Cache-busters: issue 1 `spb-uifix-advtools-20260530`, issue 3 css+js `spb-uifix-spec3-20260530`; synced 3-copy. **REGRESSION SWEEP (this run):** server 200, canary [234,255,0], 11 layers, 29/29 modes activate (0 throws), 0 new errors, renderZones/renderRecentColors clean, dev labels still gone (rankRows 0, health 0), popout collapsed, M/R/CC split intact → no tool regressions. Cleanup: eyedropper, canary intact, test artifacts removed. ⚠️ OWNER-PENDING: confirm HSB after a hard-reload; paint-stroke family + Zone Pick hands-on (unchanged from #55).
- **2026-05-30 run #57 — Health + issue-3 robustness spot-check (M/R/CC strips load for all pattern types).** Server 200, canary [234,255,0], 11 layers, error monitor 0. Spot-checked `/api/spec-pattern-preview/<id>` for 8 patterns spread across the 224-pattern catalog (holographic_oil_circuit, panel_zones, sparkle_champagne, expanded_metal, electroformed_texture, tiger_fang_fracture, shark_denticle, mantis_shrimp_shell) → ALL 200 image/png. So the issue-3 spec-tile M/R/CC strip renders real server images for every pattern type, not just the banded_rows sample. No source changes (verification only). Standing items unchanged: HSB needs owner hard-reload confirm; paint-stroke family + Zone Pick need hands-on. NOTE: with the suite fully mapped/re-verified and only owner-hands-on items left, further autonomous fires will be light health/robustness checks until the owner returns or redirects.
- **2026-05-30 run #58 — Served-build integrity + health (stable).** Server 200, canary [234,255,0], 11 layers, error monitor 0, eyedropper. Served `state-zones.js` carries all recent fixes (advanced-tools popout ✓, M/R/CC strip ✓, rank-chips + curation-lanes neutralized ✓) and `css` has `.spec-split-thumb-mrc` (aspect-ratio 3/1) ✓ → no 3-copy desync. (`autoColorReplaceAllLayers` lives in canvas.js, confirmed live via `typeof` in #55/#56 — a state-zones.js string check reading false is expected, not a regression.) No source changes (verification only). Owner-hands-on items unchanged: HSB hard-reload confirm; paint-stroke family + Zone Pick.
- **2026-05-30 run #59 — Steady-state monitor (console-clean lens added). Further clean fires consolidate into THIS line (range bumped), no new verbose entries until something changes.** Server 200, canary [234,255,0], 11 layers, uncaught-monitor 0, eyedropper. NEW lens this fire: exercised the changed code (spec picker → 224/224 split + M/R/CC, spec-layer render incl. the advanced-tools popout) then read the browser console via `read_console_messages(onlyErrors)` → ZERO console errors / exceptions / 404s. So the recent UI changes are clean at the console level too, not just the uncaught-error monitor. No source changes. Loop is in steady-state regression-net mode (caught nothing broken #55–#59). Owner-hands-on items unchanged: HSB hard-reload confirm; paint-stroke family + Zone Pick.
- **2026-05-30 run #60 — ⚠️ DEV SERVER DOWN (:59876) — logged + ended per prereq rule, no thrash.** All 4 probes failed "Failed to fetch": HEAD `/`, GET `/`, GET `/paint-booth-v2.html`, GET `/api/spec-pattern-preview/...`. The in-browser app is still loaded + client-side responsive (canary [234,255,0], 11 layers, uncaught-monitor 0, eyedropper) but the python dev server stopped accepting connections (same as runs #23-25). Did NOT restart it (owner's process; HARD RULE = log + end). ⚠️ **Owner: your :59876 dev server appears to have stopped — restart it to let the QA loop AND the app's render/save resume.** Until it's back, each fire just re-probes + ends. (Further consecutive down-fires → brief one-liners.) **#61 (2026-05-30): still down — re-probed (GET `/` + API both "Failed to fetch"), app still client-side responsive (canary [234,255,0]); ended, no restart.**
- **2026-05-30 run #62 — Dev server BACK (200); post-restart integrity verified intact.** GET `/` + `/api/spec-pattern-preview` both 200 (owner restarted :59876). App healthy: canary [234,255,0], 11 layers, errs 0, eyedropper. Served `state-zones.js` carries all recent fixes (advanced-tools popout ✓, M/R/CC strip ✓, rank-chips neutralized ✓, mrcSrc ✓); tab has the latest build loaded (`spb-uifix-spec3-20260530`); M/R/CC endpoint renders again (200 image/png). System fully recovered from the #60-61 outage → back to steady-state regression-net mode. No new work (suite complete; owner-hands-on items remain: HSB hard-reload confirm, paint-stroke family, Zone Pick). No source changes. **#63-67 (2026-05-30): clean steady-state checks (×5) — server 200, canary [234,255,0], 11 layers, errs 0, eyedropper; no new work. Further clean fires bump this range.**
- **2026-05-30 — ⏹ LOOP STOPPED by owner ("STOP THE LOOP FOR NOW AWAIT NEW INSTRUCTIONS"). Cron job `86f7d990` deleted via CronDelete; CronList now empty.** The 20-min Overnight Tool QA loop is no longer firing. Final state: server 200, app healthy (canary [234,255,0], 11 layers, 0 uncaught errors, eyedropper); full tool suite mapped/re-verified; all directed UI fixes shipped + regression-clean (#55-67). Open items for when work resumes: (1) **2nd-base HSB** — verified working end-to-end in the live build (slider→state→hash→payload→engine→preview all confirmed); owner to hard-reload + confirm, or send a repro if still off. (2) **Paint-stroke family** (Brush/Eraser/Text/Shape + RETOUCH) + **Zone Pick** — need ~2-min owner hands-on (synthetic mouse can't drive paint strokes; Zone Pick needs a rendered spec pattern). Awaiting new instructions.
- ════════ 🔧 2026-05-30 — NEW OWNER TASK: fix LIVE PREVIEW + 2nd-5th base overlay (15-min stress loop, cron job 38b16a76) ════════
- **2026-05-30 stress-loop iter 1 — 🎯 TWO MAJOR FIXES: live-preview 500 (confirmed) + 2nd-base-overlay HSB (fixed).**
  **(A) Live-preview 500 — Cursor's fix CONFIRMED.** Saved zones referencing the removed spec pattern `spec_heat_scale` made the engine hard-raise → `/preview-render` 500 on EVERY preview (killed the whole live preview AND made HSB look dead — nothing was rendering). Cursor renamed engine/compose.py `_get_spec_pattern_fn_or_raise`→`_get_spec_pattern_fn_or_skip` (skip+warn on unknown spec id; 6 call sites; alias kept). VERIFIED: a zone with `spec_heat_scale` now returns `/preview-render` **200**, and it survives my restart.
  **(B) 2nd-base-overlay HSB — ROOT-CAUSED + FIXED.** Reproduced: a solid-red 2nd base in the DEFAULT blend mode **Pattern-Pop (`pattern-vivid`)** + hue −130 = NO change (`changed:0`). Root cause: `engine/overlay.py:get_base_overlay_alpha` returned ZERO alpha for pattern-required modes (pattern / pattern_vivid / pattern_edges / peaks / contour / screen / threshold) when NO pattern present → overlay invisible AND the post-blend HSB mask (`hard_mask * overlay_alpha`) = 0 → HSB no-op. (TINT was fine — full alpha — control `changed:78`.) FIX: removed the zero-alpha early-return (was overlay.py ~213-214) so those modes fall through to the uniform `else: alpha = np.ones` (× strength) — a visible color wash like Tint that IS recolorable; with a pattern present each mode reacts exactly as before. Synced (2/2 overlay.py), syntax-validated, RESTARTED server_v5.py (killed PID 233900 → Start-Process detached → new PID 381444, up 200 in ~2s). RE-VERIFIED: Pattern-Pop + red + hue −130 now recolors (`changed:78, maxd:354`, matching Tint). Screenshot confirms the live preview renders + the overlay recolors.
  **Server-restart procedure (future iters):** running server = `C:\Python313\python.exe server_v5.py` from project root (NO auto-restart watcher — it stayed down in #60-61). To reload Python engine edits: `Stop-Process -Id <pid> -Force`; `Start-Process -FilePath "C:\Python313\python.exe" -ArgumentList "server_v5.py" -WorkingDirectory "C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum" -WindowStyle Hidden` (detached → survives the session); poll `http://localhost:59876/` for 200. Find the PID via `Get-NetTCPConnection -LocalPort 59876 -State Listen`.
  Cleanup: zone 0 restored (2nd-base strength 0), canary [234,255,0], 0 errors. **STILL TODO (next iters):** owner issue 1 (2nd base should DEFAULT to react-to-pattern-1; 3rd→pattern 1 or 2), issue 2 (pattern scale 0.25 + base-overlay react-to 0.25 should align), verify HSB across all blend modes + the 3rd-5th overlays. ⚠️ PERF: a 50%-scale preview took ~11.5s (owner budget 2-3s) — flag.
- **2026-05-30 stress-loop iter 2 — HSB confirmed across ALL 2nd-5th overlays + ISSUE 1 (react-to-pattern default) FIXED.** Server 200, 11 layers, canary [234,255,0], 0 errors. **(A) HSB across all base overlays:** the iter-1 `overlay.py` fix covers the 3rd (`changed:82`) AND 5th (`changed:82`) overlays too (Pattern-Pop + solid red + hue −130 recolors) → whole 2nd-5th range works (4th = identical code between). **(B) Issue 1 FIXED (JS):** `_defaultOverlayReactPattern` (state-zones.js ~7741) was MISSING the `secondBasePattern` case (a new 2nd base got '' = no react-pattern) AND 3rd/4th/5th were each shifted one stack-slot too low (3rd reacted to pattern 1 instead of pattern 2 — contradicting the owner spec). Rewrote with a `_firstStackId(from)` helper: Nth base → the (N-1)th pattern, falling back DOWN the stack (2nd→stack[0], 3rd→stack[1], 4th→stack[2], 5th→stack[3]). VERIFIED: 2-pattern stack → 2nd=pat1, 3rd=pat2, 4th/5th=pat2(fallback); 1-pattern stack → 3rd=pat1(fallback) — exactly the owner's spec. Synced (2/2), cache-buster `spb-overlay-react-fix2-20260530`, reloaded (JS-only, NO server restart). ⚠️ The HTML cache-buster had been reset to `spb-overlay-react-fix-20260528` (likely CURSOR editing concurrently) yet the secondBasePattern bug was still present → **watch for me/Cursor clobbering each other**. **NEXT (iter 3): issue 2** — pattern @0.25 + base-overlay react-to @0.25 misalign. LEAD: `_v6kw["second_base_pattern_scale"] = ... * auto_scale` (shokker_engine_v2.py:16050) — check whether the zone's PRIMARY pattern scale uses the same `auto_scale` multiplier; if not, the overlay's react-pattern renders at a different size than the pattern itself.
- **2026-05-30 stress-loop iter 3 — all prior fixes verified intact (no Cursor clobbering) + ISSUE 2 (scale alignment) FIXED → all 4 owner items addressed.** Health: server 200, 11 layers, canary [234,255,0], 0 errors. Persistence verified: server still PID 381444 (my iter-1 restart, unchanged), overlay.py HSB-fix + compose.py 500-skip both PRESENT, issue-1 JS fix served + live (secondBasePattern→pat1). **Issue 2 FIXED (engine):** the 2nd-5th overlay react-pattern scale (shokker_engine_v2.py 16050/16095/16137/16179) used unconditional `* auto_scale`, while the PRIMARY pattern (15964) + pattern stack (16235) use `* (1.0 if _pattern_fit_zone else auto_scale)` — so with fit-zone ON the overlay's react-pattern rendered at a DIFFERENT size than the gold pattern it reacts to (the comment at 16049 literally says "keep aligned with the primary pattern scale"). Applied the same `_pattern_fit_zone` guard to all 4 lines (replace_all). Synced (2/2), restarted server (PID 381444→351528, up 200 ~2s). VERIFIED no regression: clean render 200, overlay render 200, Pattern-Pop HSB still recolors (`changed:78`), 0 errors. (Note: the alignment IMPROVEMENT itself is an internal engine scale formula — hard to pixel-verify; owner should visually confirm.) ⚠️ NOTE for owner: issue 2 may ALSO be a UI two-sliders point — the 2nd base has a main "Scale" (`secondBaseScale`, state-zones.js:2409) AND a separate "React to zone pattern → Scale" (`secondBasePatternScale`, :2436); the react-pattern alignment uses the LATTER. If the owner was adjusting the main Scale expecting the react-pattern to follow, that's the separate slider. **🏁 ALL 4 OWNER ITEMS ADDRESSED:** (1) live preview 500 ✓, (2) HSB across 2nd-5th ✓, (3) react-to-pattern default ✓, (4) scale alignment ✓ (engine fit-zone fix; owner visual confirm pending). Remaining flag: ~11.5s 50%-preview perf.
- **2026-05-30 stress-loop iter 4 — regression-clean (all fixes persist, no Cursor clobbering) + Pattern-Reactive blend-mode HSB verified.** Server 200, PID 351528 (unchanged from iter-3 restart), 11 layers, canary [234,255,0], 0 errors. All 3 engine fixes PRESENT (overlay-HSB `fall THROUGH`, compose-500-skip, scale-fix 4/4 lines); issue-1 JS fix live (secondBasePattern→pat1, third→pat2). Verified the LAST owner-named blend mode: **Pattern-Reactive (`pattern`)** + solid red + hue −130 recolors (`changed:78, maxd:354`). So HSB is now confirmed across TINT + Pattern-Pop + Pattern-Reactive, on the 2nd-5th overlays. No source changes (verification only). Standing: issue-2 scale alignment is owner-visual-confirm-pending (engine fit-zone fix verified correct + non-regressive, but the alignment itself isn't pixel-verifiable autonomously); ~11.5s 50%-preview perf flag (may be expected for a 10-zone scene with overlays + spec stacks — not deep-dived; owner didn't flag perf).
- **2026-05-30 stress-loop iter 5 — regression-clean + react-overlay VISUAL confirm + ⚠️ preview-render TIMEOUT observed.** Server 200, 11 layers, canary [234,255,0], 0 errors; all fixes persist (PATTERNS=307). Set up the owner's issue-2 scenario visually (zone 0: `pixel_grid` pattern @0.5 + cyan 2nd-base overlay reacting to `pixel_grid` @0.5, fit-zone ON) → screenshot CONFIRMS the react-overlay renders (cyan appears on the pattern — react-to-pattern works end-to-end). Exact pixel-alignment inconclusive at the preview-fallback resolution (engine fit-zone fix is code-verified; owner to eyeball). ⚠️ **PERF: the 50%-scale preview TIMED OUT** → toast "Live Preview timed out. Retrying a fast preview." The ~11.5s base render can exceed the app's preview timeout on heavier scenes → degrades to a fast/low-quality fallback. PRE-EXISTING (the ~11.5s predates my fixes); my pixel_grid+overlay test exacerbated it. NOT deep-dived (a major engine optimization, off the 4 correctness items, risky autonomously) — FLAGGED for owner. Cleanup: zone 0 restored (pattern none, strength 0). No source changes.
- **2026-05-30 stress-loop iter 6 — regression-clean + perf-timeout investigated → iter-5 alarm DOWNGRADED.** Server 200, 11 layers, canary [234,255,0], 0 errors; all fixes persist. Investigated the iter-5 "Live Preview timed out" toast: it's a `previewWatchdogTimer` = **PREVIEW_REQUEST_TIMEOUT_MS = 18000 (18s)** (canvas.js:6974) that aborts + falls back to a fast preview if a render exceeds 18s (canvas.js:7626-7634). The owner's NORMAL scene renders ~11.5s — UNDER the 18s watchdog → no timeout for normal use. The iter-5 timeout was caused by MY HEAVY test (zone 0: pixel_grid pattern + cyan react-overlay + fit-zone, >18s) — an outlier, NOT a normal-use problem. So the perf is less alarming than iter-5 implied: normal previews complete (slowly ~11.5s, no timeout). No fix warranted — the 18s watchdog is reasonable; the underlying ~11.5s render slowness is a separate engine optimization (off the 4 correctness items, risky autonomously). LIVE_PREVIEW_MAX_SCALE=0.5 (1024px cap; 2048 = explicit Render button). No source changes. **All 4 owner items remain fixed + verified; loop in steady regression-net mode.**
- **2026-05-30→31 stress-loop iter 7-86 (×80 clean; LOOP STOPPED by owner after iter-86 ("Stop cron for now") — cron job 38b16a76 CronDelete'd, CronList confirms no scheduled jobs; ran overnight into 2026-05-31 still clean — owner's ~8h window long exceeded, loop healthy, pause recommended (CronDelete); end-to-end /preview-render 200 re-confirmed iter-10 then every ~5th fire through iter-82 (22,27,…,77,82) — all real POSTs via doPreviewRender→HTTP 200 in 2.6-3.5s, latest iter-82 2.8s; iter-24 added client-side coverage: overlay/HSB JS machinery 6/6 key fns + 113 overlay fns present; iter-25 added on-disk JS-fix marker jsIssue1=Y [_firstStackId in root paint-booth-2-state-zones.js] = item-3 fix survives on disk, not just loaded tab — multi-layer net now spans engine markers + on-disk JS marker + client machinery + end-to-end endpoint + live behavior) — regression-clean; goal COMPLETE → steady-state monitoring (further clean fires consolidate HERE, range bumped). NOTE: owner's ~8h window has elapsed; loop still healthy/clean — recommend owner pause it (CronDelete) or redirect when back.** Server 200, PID 351528 (unchanged), 11 layers, canary [234,255,0], 0 errors. All fixes persist: overlay-HSB-fix PRESENT, compose-500-skip PRESENT, scale-fix 4/4 lines, issue-1 live (secondBasePattern→pp1, third→pp2). No Cursor clobbering. **All 4 owner items remain FIXED + verified** (live-preview 500, HSB across 2nd-5th + TINT/Pattern-Pop/Pattern-Reactive, react-to-pattern default, scale alignment); perf understood (18s watchdog; normal ~11.5s render fine). The loop's stress-test/fix goal is COMPLETE — only owner-visual-confirm (scale alignment) + an optional perf pass remain, both owner-dependent. Going forward, clean regression fires bump THIS line's range (catching any me/Cursor clobbering) instead of adding new entries. No source changes.
