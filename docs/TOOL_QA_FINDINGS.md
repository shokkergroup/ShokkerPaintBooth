# Tool QA Findings — overnight loop (started 2026-05-28)

Detailed per-tool findings + fixes from the 20-min QA loop (cron `7,27,47 * * * *`).
Format per entry: tool, what I did, expected vs actual, verdict, root cause + fix (file:line) if broken.

---

## Run #1 — 2026-05-28 — SELECT menu (4 tools, all PASS, no fixes needed)

- **Select All Color** (`setCanvasMode('selectall')` → click a colour): clicked a solid cyan body area.
  Expected: select all pixels matching that colour within tolerance. Actual: status bar → **Sel: 1,441,885 px**. ✅ PASS. Console clean.
- **Edge Detect** (`setCanvasMode('edge')` → click): `edgeDetectFill` (paint-booth-3-canvas.js:5426) flood-fills a region
  **bounded by edges** — you click INSIDE a region, not on the boundary. First click landed on an edge → selected nothing
  (correct: it bails on edges). Click inside cyan → **Sel: 704 px**. ✅ PASS. Console clean.
  UX note: this is "smart fill to edges," not "trace the boundary line" — could confuse users; consider a clearer label/tooltip later.
- **Elliptical Marquee** (`setCanvasMode('ellipse-marquee')` → drag bbox): dragged an ellipse. Actual: **Sel: 123,530 px**. ✅ PASS. Console clean.
- **Move Selection Border** (`activateSelectionMove()` → drag): mode → 'selection-move'; dragged the existing selection.
  Expected: move the outline (not pixels), selection persists. Actual: persisted and shifted (123,530 → 111,922 px). ✅ PASS. Console clean.

## Run #2 — 2026-05-28 — RETOUCH start (Color Brush) + Layer-Mode methodology

- **Color Brush** (`setCanvasMode('colorbrush')` → paint stroke): activated (mode 'colorbrush'), painted a
  drag stroke over the cyan body. Sampled #paintCanvas region (216,529,40×40) sum before/after = **377219
  unchanged** → no paint. NOT a bug: a toast appeared — *"Color Brush only edits layers in Layer Mode —
  switch the toolbar to LAYER."* App was in **Zone Mode** (`window.isLayerToolbarMode()===false`). So the
  tool correctly refuses to paint outside Layer Mode. Console clean. Verdict: ⏸ guard correct; paint-action
  test deferred to a Layer-Mode pass.
- **METHODOLOGY DISCOVERY (important for the whole RETOUCH menu):** paint/retouch tools edit LAYER pixels
  and require Layer Mode. Mode flag = `window.toolbarEditMode` ('layer' vs zone); read via
  `window.isLayerToolbarMode()`. Active layer = `window._selectedLayerId` (layers in `window._psdLayers`;
  e.g. psd_0 = "Car Paint"). The clean Layer-Mode SETTER is not exposed under obvious window names
  (`setToolbarMode`/`setLayerMode`/etc. all undefined) — it likely lives in js/canvas/dispatch.js
  (`_dispatchOwnsToolbarMode` + `window.toolbarEditMode`) or behind the on-canvas ZONE/LAYER toggle button.
  Next run: locate it, enter Layer Mode, select a layer, then paint-test Color Brush, Clone, Smudge, Pencil,
  Dodge, Burn, Blur, Sharpen. Paint-detection method (proven): getImageData region-sum on #paintCanvas (2048²).
- No fixes required this run (no broken tool found; the "no paint" was a correct mode guard).

## Run #3 — 2026-05-29 — RETOUCH: Color Brush — 🔧 FIXED A REAL CRASH

- **Setup:** entered Layer Mode via `window.setToolbarEditMode('layer')` (defined in js/canvas/dispatch.js;
  this is the mode-switch the loop needs for all RETOUCH tools). Selected the **Numbers** layer (psd_2)
  by clicking its row in the LAYERS panel (`window._selectedLayerId='psd_2'`).
- **Bug:** with mode='colorbrush' + Layer Mode + active layer, the first paint attempt fired:
  `ReferenceError: _t0 is not defined` at `_paintColorBrushAt` (paint-booth-3-canvas.js:14481) →
  `paintFn` → `paintColorBrush` → `canvas.onmousedown`. So the Color Brush tool handler **threw on every
  mousedown and painted nothing** — fully broken.
- **Root cause:** the last line of `_paintColorBrushAt` was `_logPaintPerf('clone', _t0, radius)` — a
  perf-log line copy-pasted from the clone-stamp function (note the wrong `'clone'` label). `_t0` is the
  start-timestamp in the clone fn but was **never defined** inside `_paintColorBrushAt`. Because
  `_logPaintPerf` exists, the `_t0` reference evaluated → ReferenceError.
- **Fix (canvas.js):** added `const _t0 = (performance.now ? performance.now() : 0)` at the top of
  `_paintColorBrushAt` (line ~14453) + corrected the label to `'colorbrush'`. In-source audit comment added.
  Synced (3-copy), bumped the canvas.js cache-buster (`?v=spb-preview-refresh-20260519` →
  `spb-qa-colorbrush-fix-20260529`) so clients fetch the fix, reloaded Chrome.
- **Re-test:** mode colorbrush + Layer Mode + Numbers layer → painted again → **no console error** (crash
  gone). ✅ Crash FIXED.
- **Open caveat (not a regression):** could not positively confirm pixel-level painting in Layer Mode via
  composite getImageData sampling — a drag in Layer Mode surfaced the **layer-element free-transform overlay**
  (Rot/Scale/Pos + Apply/Cancel) rather than an obvious paint stroke. Possible that in Layer Mode a drag on a
  layer element is routed to element-transform, or the composite display isn't live-sampled. Cancelled the
  transform (no element moved), undo×3, returned to Zone Mode. **TODO next run:** confirm Color Brush actually
  writes pixels in Layer Mode (sample the active layer's own `img`, or trigger recomposite) and clarify the
  drag-routing (paint vs element-transform) — this also affects how the other RETOUCH brushes are tested.

## Run #4 — 2026-05-29 — Color Brush deep-dive: crash fix holds; SECOND issue found (paint not landing)

- **Crash fix confirmed:** Layer Mode + Numbers layer + Color Brush, painted again → still NO `_t0` error.
  The run-#3 fix is solid.
- **NEW issue — Color Brush does not visibly paint in Layer Mode.** Single CLICK (no drag, avoids the
  element-transform interception) with FG=#ffffff and brushSize=60 on a dark area → before/after zoom of
  the exact spot showed **no white mark**. The tool runs without error but produces no paint.
- **Diagnosis (flow traced):**
  - `paintColorBrush` (canvas.js:14484) paints into `paintImageData.data` (composite buffer) then calls
    `_flushPaintImageDataToCurrentSurface()` (canvas.js:14547).
  - `_flushPaintImageDataToCurrentSurface` (canvas.js:18814): `_activeLayerCtx.putImageData(paintImageData,0,0)`
    (if active-layer canvas exists) AND `paintCanvas.putImageData(paintImageData,0,0)`.
  - `_refreshActiveLayerCompositePreviewNow` (canvas.js:18830) rebuilds paintCanvas from the layer stack
    (drawing `_activeLayerCanvas` for the active layer + each layer `.img`), then resets `paintImageData`.
  - **Hypothesis:** the stroke hits paintImageData/paintCanvas briefly but the recomposite reverts it because
    the painted pixels never reach the active layer's persistent buffer (`_activeLayerCanvas` may be unset/
    mismatched for the selected layer, or the flush dumps the FULL composite into the layer at 0,0 instead of
    compositing just the stroke). Net: paint is transient → erased on refresh.
- **Decision: NOT fixed in the loop** — shared layer-paint commit path; a blind edit risks breaking ALL paint
  tools + compositing. Needs a focused session (verify `_activeLayerCanvas` wiring + where the stroke should
  persist + re-test composite refresh).
- **⚠️ Likely affects the whole RETOUCH menu** (Clone/Smudge/Pencil/Dodge/Burn/Blur/Sharpen — shared commit
  path). Future runs: treat the layer-paint commit as the prime suspect, don't re-test each brush in isolation.
- Cleaned up: undo×5, Zone Mode, eyedropper, layer deselected. Car verified intact (no stray marks).

## Run #5 — 2026-05-29 — SELECT (Pick Layer Element) + MASK (Invert / Smooth / Mirror) — all PASS

- **Pick Layer Element** (`activateLayerElementPickMode`): Layer Mode + Numbers layer (psd_2) + clicked a
  #55 → isolated one element: `_spbLastPickedElementBbox` = {pixelCount 80,148, bbox [888,355,1295,592],
  layerId psd_2}. ✅ PASS. Console clean.
- **Invert Mask** (`invertRegionMask`): on a 948,123-px selection → **3,246,181 px** = exactly
  4,194,304 − 948,123. Perfect inversion. ✅ PASS.
- **Smooth Edges** (`smoothRegionMask`): 3,246,181 → 3,133,443 px (≈112K edge pixels rounded off). Count
  changed as expected. ✅ PASS.
- **Mirror Mask** (`mirrorRegionMask`): ran cleanly, count preserved at 3,133,443 (correct — a mirror is
  count-invariant). ✅ PASS with caveat: because count is invariant under mirroring, the status-bar method
  can't independently confirm the geometry actually flipped. To fully verify a future run could sample the
  regionMask left/right asymmetry, but no console error + count-preserved is consistent with a working mirror.
- No fixes needed. Cleaned up (deselect, eyedropper, Zone Mode, layer deselected).
- Note: **Zone Pick** deferred — it picks spec-pattern/base sub-pieces, so it needs a zone with a spec pattern
  assigned to have anything to pick; set one up before testing, else it'll select nothing (not a bug).

## Run #6 — 2026-05-29 — ADJUST (Grayscale + Invert Colors) + TRANSFORM (Transform Pattern/Base) — all PASS

- **Grayscale** (`adjustGrayscale()`): sampled #paintCanvas region (700,900,100×100) before/after using a
  colourfulness metric `Σ(|R−G| + |G−B|)`. Before = **106,617**, after = **0** → every sampled pixel fully
  desaturated (R=G=B). ✅ PASS. `undoDrawStroke()` restored the region to exactly **106,617**. Console clean.
- **Invert Colors** (`adjustInvertColors()`): sampled the same region with a total-RGB sum. Before = **668,871**,
  after = **6,981,129**. For a 100×100 region the max possible sum is 100·100·3·255 = 7,650,000, and
  7,650,000 − 668,871 = **6,981,129** — i.e. every channel mapped v→255−v exactly. ✅ PASS. Undo restored to
  **668,871**. Console clean.
- **Transform Pattern / Base** (`activateZoneTransform()`): with zone 1 (which has a base, no pattern) selected,
  calling the handler opened a **free-transform overlay targeting the base** — `window.freeTransformState =
  {target:"base", hasBox:true}`, the top bar showed a "Zone Transform · base" pill, and the on-canvas hint box
  appeared ("drag/Arrow keys to resize/rotate. R/S/X/Y/numeric, double-click to apply… Enter=commit, Esc=cancel").
  That is the correct activation (it transforms the pattern first if present, else the base). ✅ PASS.
  **Cleanup:** pressed **Esc** (NOT Enter — committing would have transformed the base) → `freeTransformState`
  cleared to `null`, `canvasMode` back to `eyedropper`. Base untouched. Console clean.
- **No fixes needed, no source changes this run.** Car verified intact (Grayscale/Invert both undone; transform
  cancelled, not committed). State returned to eyedropper / Zone Mode / no selection.
- **Methodology note for the rest of ADJUST:** the two tools tested here (`adjustGrayscale`, `adjustInvertColors`)
  apply immediately with no dialog, so they're safe to invoke via javascript_tool. The remaining ADJUST tools
  open dialogs — `promptAdjustBrightnessContrast`, `promptAdjustHueSat`, `promptVibrance`, `promptColorTemp`,
  `openColorReplaceDialog`, `openGradientMapDialog`. ⚠️ Any that use a **native `prompt()`** would BLOCK a
  javascript_tool eval (synchronous modal the eval can't dismiss). Next ADJUST run: drive these through the
  dialog UI (open via the ADJUST menu, set a value, click Apply) and verify with the same region-sum + undo
  method — do NOT call the handler blind via JS until it's confirmed to be a non-blocking custom dialog.

## Run #7 — 2026-05-29 — PRIMARY icons (Magic Wand, Pick Color) + MASK Include Region — all PASS + 🔑 methodology breakthrough

**🔑 The big finding this run: canvas-click tools MUST be driven by the real mouse (computer tool).**
Spent the first half of the run discovering that my JS-only approaches do NOT work for selection tools:
- **Synthetic `MouseEvent` dispatch** on #paintCanvas (with computed clientX/clientY + defineProperty offsetX/offsetY,
  mousemove→mousedown→mouseup) → selected nothing.
- **Direct handler call** `magicWandFill(1024,1024,30,false)` (correct 4-arg signature `magicWandFill(startX,
  startY, tolerance, addToExisting)`) → returned undefined, selected nothing. regionCanvas alpha count stayed at a
  constant 5068 (a static overlay, NOT the selection) regardless of click color.
- Only when I clicked with the **computer-tool real mouse** did the wand actually fire.
Conclusion: the real selection pipeline lives behind the canvas's onmousedown handler chain (mode routing, coord
transform, internal fill) — calling the leaf function or faking events bypasses it. **For ALL canvas-click/drag
tools (SELECT marquees, wand, lasso, spatial brushes, fill, gradient, move, pick), use the computer tool.**

**Coordinate mapping (CONFIRMED, reusable):** #paintCanvas getBoundingClientRect = {left 747, top 366, w 416, h 416}
(2048² internal). `window.innerWidth=1920`, screenshots come back 1568 wide. The computer tool takes coords in
**screenshot space** and scales them ×(1920/1568)=×1.2245 to the viewport. So to click canvas pixel (cx,cy):
viewport_x = 747 + cx*416/2048, viewport_y = 366 + cy*416/2048, then **computer-tool coord = viewport/1.2245**.
Verified twice: wand click intended canvas-center landed dead-on; eyedropper click readout showed "X:1299 Y:896"
for an intended (1300,900). The spatial drag echoed back "Dragged from (857,490) to (943,575)" = my (700,400)/(770,470)
screenshot inputs ×1.2245.

**Selection-size readout (reusable):** status-bar **"Sel: N px"** (scan elements for `/\d[\d,]{2,}\s*px/`,
regex `/Sel\s*:?\s*([\d,]+)\s*px/i`) AND counting `regionCanvas` alpha>0 pixels — the two agree exactly (both
475,271 for the wand). ⚠️ `_hasAnyMaskPixels()` stayed **false** during a valid 475K-px wand selection — it tracks
COMMITTED ZONE region masks, not the transient active selection. Do NOT use it to verify selection tools.

- **Magic Wand** (`setCanvasMode('wand')` + real-mouse click at canvas ~center): selected a contiguous 475,271-px
  color region. Status bar "Sel: 475,271px"; toast "Magic Wand: selected 475,271 pixels [Shift=add, Alt=subtract]";
  banner "Wand select for: Zone 1: Body Color 1"; red overlay drawn on canvas. ✅ PASS. Console clean.
- **Pick Color / eyedropper** (`setCanvasMode('eyedropper')` + real-mouse click on canvas pixel (1300,900)=`83,71,65`):
  before, 0 DOM elements had bg `rgb(83,71,65)`; after, **5** did — including `fgColorSwatch` and `eyedropperSwatch`,
  and readouts showing **#534741**. The FG paint color adopted the picked pixel exactly. ✅ PASS. Console clean.
- **Include Region** (`setCanvasMode('spatial-include')` + real-mouse drag): painted a spatial-include stroke →
  regionCanvas 0 → **709 px** marked. Banner "Including for: Zone 1: Body Color 1 (paint green areas to KEEP in this
  zone's color match)", mode pill "SPATIAL +", status "SPATIAL INCLUDE". ✅ PASS. Console clean.
- **No fixes needed, no source changes.** All 3 work as intended.
- **Cleanup + a gotcha:** `clearSpatialMask(zoneIndex)` takes a **zone-index arg** (a no-arg call is a silent no-op).
  The active selection / spatial stroke is actually cleared by `deselectRegion()` / `_clearActivePixelSelection()`,
  BUT the regionCanvas can keep showing a **stale bitmap** (e.g. 709) until a mode switch forces a repaint from the
  (now-empty) data. Confirmed clean by switching to spatial-include mode (repaint → 0) and final read: mode
  eyedropper, Zone Mode, regionCanvas 0, `_hasAnyMaskPixels` false. State left clean; FG color left at #534741
  (harmless transient UI state, not saved project data).
- **Next runs (now unblocked by the real-mouse method):** Lasso (polygon — needs multi-waypoint drag; verify the
  computer tool's drag/mouse-down-move-up support), Exclude/Erase Spatial (same drag pattern as Include), Move,
  Pick Item, Fill, Gradient, Eraser, Brush. RETOUCH brushes still HELD (layer-paint commit, run #4). Dialog-based
  ADJUST tools still need UI-driven testing (run #6 note).

## Run #8 — 2026-05-29 — MASK Exclude/Erase Spatial + TRANSFORM Decal — all PASS

Used the run-#7 real-mouse method throughout (computer-tool drag, coords in screenshot space = viewport/1.2245;
verified via regionCanvas alpha count). Prereqs OK (server 200, browser connected, clean baseline regionCanvas 0).

- **Exclude Region** (`setCanvasMode('spatial-exclude')` + real-mouse drag): regionCanvas 0 → **709 px**. UI:
  banner "❌ Excluding from: Zone 1: Body Color 1 (paint red areas to REMOVE from this zone's color match)", mode
  pill "SPATIAL −", status "SPATIAL EXCLUDE", toast "Tool: SPATIAL −". ✅ PASS. Console clean.
- **Erase Spatial** (`setCanvasMode('spatial-erase')` + real-mouse drag over the exclude marks): ✅ PASS, but with
  an instructive first miss —
  - **Attempt 1:** dragged a path OFFSET ~10px screenshot (~60 canvas px) from the exclude path → **709 → 709**
    (no change). Mode/status were correct ("SPATIAL ERASE"), no error.
  - **Diagnosis:** the spatial brush is **THIN** — 709 px spread over a ~680-canvas-px stroke ≈ **~1 canvas px wide**.
    A thin erase line offset from a thin exclude line simply doesn't overlap, so nothing erases. NOT a bug.
  - **Attempt 2:** dragged the EXACT exclude path → **709 → 0** (fully erased). ✅ Confirms erase works when the
    brush passes over the marks. Console clean.
  - Lesson for future spatial-tool tests: erase/refine drags must trace the existing marks closely; verify by the
    regionCanvas count dropping. (A wider brush-size setting may exist; not needed for this verification.)
- **Transform Decal** (`activateFreeTransform('decal')`): with NO decal selected → returned **false**, opened no
  free-transform (`freeTransformState` null), mode unchanged (eyedropper), and surfaced the toast **"Select a decal
  first before using Transform Decal"**. ✅ PASS — correct precondition guard, no error, no state change. A
  "Car_decal" layer exists in the LAYERS panel; the **happy path** (select that decal → activateFreeTransform('decal')
  opens the transform overlay, à la Transform Pattern/Base in run #6) is a noted follow-up.
- **No fixes, no source changes.** Cleanup: confirmed BOTH spatial channels empty via mode-cycle repaint
  (spatial-include → 0, spatial-exclude → 0), `_clearActivePixelSelection`/`deselectRegion`, back to eyedropper /
  Zone Mode / regionCanvas 0. No console errors all run.
- **Coverage milestones:** MASK menu fully covered except **Copy Mask** (`toggleCopyMaskDropdown` — needs an event
  arg + a 2nd zone to copy to). TRANSFORM menu fully covered (Transform Decal happy-path follow-up aside).

## Run #9 — 2026-05-29 — PRIMARY icons: Lasso + Pick Item — both PASS + computer-tool gesture limits

Prereqs OK (server 200, browser connected, clean baseline rc 0).

**🔑 Computer-tool gesture capability (important for all future canvas tools):** this Claude-in-Chrome `computer`
tool does **NOT** support `left_mouse_down` / `left_mouse_up` (attempting `left_mouse_down` errors: "Unsupported
action: left_mouse_down"). So there is **no held-button freehand-path gesture**. Supported: `left_click`,
`double_click`, `left_click_drag` (straight start→end), `mouse_move`, `key`, `wait`, `screenshot`. Consequences:
- Freehand-drag tools can't be traced as a curve. Drive **polygon/click-based** tools by clicking vertices.
- `left_click_drag` (straight line) is correct for marquee boxes, gradient lines, and the spatial brushes (runs 7-8).

- **Lasso** (`setCanvasMode('lasso')`): activated → banner "Lasso for: [zone]". It is a **POLYGON-CLICK lasso**, not a
  freehand drag — clicking places vertices, double-click closes. Test: `left_click` (700,420)→(825,425)→(770,525),
  `double_click` (702,422) to close → selection **233,668 px** (status bar "Sel: 233,668px", regionCanvas alpha count
  matches). Sanity: mapping those screenshot points to canvas space gives a triangle with vertices ≈(541,729),
  (1295,758), (965,1364); its area = ½|Σ| ≈ **233,247 px** vs measured 233,668 = **0.2% match** → the lasso selected
  exactly the polygon I traced. ✅ PASS. Console clean. (My first instinct — a freehand `left_mouse_down`+moves — is
  impossible here, see gesture note; the polygon-click model is the right driver.)
- **Pick Item** (`setCanvasMode('pick-item')`): banner read "Pick which finish layer the template drag should move."
  A real-mouse click on the #55 area: mode switched to **zone-pick** ("Drawing for: Zone 1: Body Color 1"), a toast
  "…independent transform active (handles + pivot + live numbers)" appeared, and `freeTransformState` became active
  with `{target:"base", zoneIndex, centerX, centerY, scaleX, scaleY, rotation, origCenterX/Y, origScaleX/Y,
  origRotation}`. So Pick Item **picks the zone item under the cursor and opens an independent free-transform on it**
  (drag handles + pivot + live numeric readout). No console error. ✅ PASS (functional + cleanly cancellable).
  - **NOTE on intent:** it targeted `target:"base"` (the whole zone base), NOT an isolated single sub-element (e.g.
    just the #55). The owner's "click ONE number and transform only it" workflow is therefore a *different* path
    (likely Layer Mode / element-level pick, cf. run #5 Pick Layer Element which DID isolate a #55 at element level).
    Pick Item here = pick the zone-level item + transform it. Flagging so intent vs behavior is on record.
  - **Cleanup:** pressed **Esc** (NOT Enter — committing would have transformed Zone 1's base). Esc cancelled the
    transform (`freeTransformState`→null) AND cleared the lingering lasso selection in one go (regionCanvas → 0).
    Note: `_clearActivePixelSelection()`/`deselectRegion()` alone did NOT clear the lasso selection's display
    (stayed 233,668) — **Esc is the reliable deselect+cancel**. Final state: eyedropper, Zone Mode, rc 0, ft null.
- **No fixes, no source changes, no console errors.** State left clean.

## Run #10 — 2026-05-29 — PRIMARY icons: Transform (layer) + Move — both PASS (Move "dead" flag resolved)

Picked the two layer-manipulation tools (position/transform) deliberately — they're independent of the held
layer-paint commit bug (run #4), so they're cleanly testable now. Prereqs OK (server 200, browser connected).
Setup: `setToolbarEditMode('layer')` + `selectPSDLayer('psd_2')` (Numbers). Layer object keys: id, name, path,
visible, opacity, img, **bbox**, groupName, elementLinkGroups → position is in `bbox`.

- **Transform (layer)** (`activateLayerContextTransform()`): returned **true**; `freeTransformState` opened with
  `{target:"layer", layerId:"psd_2", sessionUndoMode, sessionScopeLabel, centerX, centerY, scaleX, scaleY, rotation,
  origCenterX/Y, origScale...}`. Screenshot showed the full layer-transform UI: "EDITING LAYER Numbers" header,
  rotate −90°/+90°/180°/Apply/Cancel, live Rot/Scale/Pos (Pos 851,1179), on-canvas handles + pivot, hint
  "Layer Transform: drag/Arrow keys to move, handles to resize/rotate. R/S/X/Y=numeric, double-click to apply.
  Per-element sub-piece supported. Enter=apply, Esc/Ctrl+Z=cancel." ✅ PASS. Console clean. bbox unchanged.
  - **⚠️ Cancel gotcha:** pressing **Esc** here DESELECTED the layer (`_selectedLayerId`→null) but left
    `freeTransformState` ACTIVE — Esc routed to the layer-deselect handler, not the transform-cancel. The correct
    cancel is **`cancelActiveTransformSession()`** (or `cancelLayerTransform()`); calling it set ft→null with bbox
    untouched (no commit). (Contrast run #6's zone-base transform, where Esc DID cancel — handler priority differs
    in Layer Mode.) Useful numeric controls discovered for future transform tests: `setLayerTransformRotation`,
    `setLayerTransformUniformScale`, `setLayerTransformPosition`, `rotateActiveLayerTransformBy`,
    `flipActiveLayerTransformH/V`, `resetActiveLayerTransform`, `resetLayerTransformPivot`.
- **Move** (`setCanvasMode('layer-move')`): with psd_2 selected, captured bbox **[406,355,1295,2003]**, then a
  horizontal `left_click_drag` (+60px screenshot ≈ +74px viewport ≈ +364 canvas px). bbox → **[771,355,1660,2003]**:
  x shifted 406→771 and 1295→1660 (**+365** each), y unchanged (355/2003) — i.e. it moved the layer by exactly the
  drag delta in the drag direction. ✅ PASS — **Move is NOT dead** (resolves the long-standing "possibly dead" flag).
  Restore: the exact inverse drag returned bbox to **[406,355,1295,2003]** (pixel-exact), so the Numbers layer was
  left untouched. Console clean.
- **Cleanup:** `deselectPSDLayer()`, `cancelActiveTransformSession()`, `setCanvasMode('eyedropper')`,
  `setToolbarEditMode('zone')`. Final verified state: eyedropper, Zone Mode, `_selectedLayerId` null, psd_2 bbox
  restored, regionCanvas 0, freeTransformState null. No console errors all run.
- **Verdict:** both layer-manipulation tools work correctly. Remaining PRIMARY are the paint/vector tools (Fill,
  Gradient, Eraser, Brush, Text, Shape, Pen) — expected to be Layer-Mode gated and likely entangled with the held
  layer-paint commit; a focused run should categorize them (guard vs paint vs held) rather than test blindly.

## Run #11 — 2026-05-29 — PRIMARY paint: Gradient (PASS) + Fill Bucket (BROKEN click) + key process lessons

Setup: Layer Mode + selectPSDLayer('psd_2' Numbers). Baseline composite region (980,980,80,80) sum = 3,959,844,
center pixel (1024,1024) = yellow 234,255,0.

- **Gradient** (`setCanvasMode('gradient')` + real-mouse drag): the drag committed a gradient onto psd_2 — region
  3,959,844 → 1,934,940, and it PERSISTED (sampled after, still 1,934,940). `undoDrawStroke()` restored it exactly
  to 3,959,844. ✅ PASS, console clean. Mousedown 'gradient' branch (canvas.js:3590) commits via mouseUP draw; uses
  the same guards as Fill but works because it's a drag.
- **Fill Bucket** (`setCanvasMode('fill')`) — ❌ **CLICK PATH BROKEN (engine works):**
  - Click-fill (canvas pixel 1024,1024) in Layer Mode produced NO change — pixel stayed yellow, region 3,959,844
    unchanged, immediate AND after 2s, no console error. Repeated with `getSelectedEditableLayer()` verified =
    'psd_2' (so the `requireLayerToolbarTarget('Fill Bucket')` guard at canvas.js:3579 passes) → still no-op.
  - BUT `fillBucketOnLayer(1024,1024)` called DIRECTLY fills correctly: center pixel yellow → #534741 (the FG),
    region dropped. So the fill ENGINE works; the **click → fill path doesn't apply**.
  - Handler: mousedown `else if (canvasMode === 'fill')` (canvas.js:3571-3581) → `if isLayerToolbarMode(): if
    shouldBrushStrokeProceed() && requireLayerToolbarTarget('Fill Bucket') → _pushLayerUndo(...);
    fillBucketOnLayer(pos.x, pos.y)`. Guards verified passing, branch is reachable (no earlier else-if matches
    'fill'), `isLayerPaintSourceSpecial()`=false (ruled out the special-cache early-return at canvas.js:1947-1960).
    Remaining candidates: (a) the mousedown handler is pre-empted in Layer Mode by a separate element-interaction
    listener before this branch runs (cf. run #3/#4 — Layer-Mode click routes to element transform/move; the very
    first fill-click even surfaced a stray "Layer moved" toast); or (b) `pos` is wrong for this click context.
    Needs instrumentation to confirm — DEFERRED to the focused layer-paint session (same risky area as run #4;
    NOT a safe autonomous blind edit, especially after this run already churned layer/undo state).
- **🔑 Process findings (important for future paint-tool testing):**
  1. **`selectPSDLayer(id)` TOGGLES.** Calling it a 2nd time on the already-selected id DESELECTS (→ `_selectedLayerId`
     null → `getSelectedEditableLayer()` null). This briefly made me think Fill's guard was the bug; it was my double-
     select. Always check `_selectedLayerId !== id` before calling, or it'll toggle off.
  2. **Direct `fillBucketOnLayer()` bypasses undo.** The click handler pushes undo via `_pushLayerUndo` (canvas.js:3580)
     BEFORE calling the engine; a direct engine call skips that, so the fill is NOT on the undo stack and
     `undoDrawStroke()` can't revert it (it reverts the wrong/earlier entry). This tangled the undo stack mid-run.
  3. **Restore without reload:** a direct fill left the center #55 stuck at #534741 (undo couldn't fix it). Restored
     by setting FG to the original #EAFF00 (via fgColorPicker/fgHexInput input events + window._foregroundColor) and
     re-filling the now-uniform footprint → center pixel back to **234,255,0**. Region 3,983,277 vs original 3,959,844
     (**+0.6%**, because re-fill makes the edge anti-aliasing solid yellow rather than the original feathering — one
     number's edge, visually negligible). Deliberately did NOT reload the page (the imported PSD is likely client-side
     and a reload could lose it). **Lesson: test paint tools ONLY via the click/handler path; never mix direct paint-
     fn calls with undo; if a paint commits, undo it immediately through the same handler path that pushed the entry.**
- **Cleanup:** deselect layer, cancel transform, eyedropper + Zone Mode. Verified: center pixel yellow, regionCanvas 0,
  no layer selected, no console errors. FG left at #EAFF00 (transient UI state).
- **Convergence:** Fill (click), the RETOUCH brushes (run #4), and probably Brush/Eraser/Pencil clicks all point at
  ONE root cause — Layer-Mode click→paint routing/commit. Gradient works because it commits on drag-up via a path that
  reaches the engine. The focused session should fix the Layer-Mode click→paint routing once, then re-verify the group.

## Run #12 — 2026-05-29 — PRIMARY paint: Brush (BROKEN, diagnosis REFINED) + Eraser (inferred)

Disciplined run (lesson from #11): click/handler path only, no direct paint-fn calls, undo via the proper master
undo, verify no artifact. Setup: Layer Mode + selectPSDLayer('psd_2') ONCE + FG=magenta (#ff00ff via picker input
events) + brush size 15 + `setCanvasMode('brush')`. Baseline composite region (540,540,160,160): sum 5,573,059,
magenta px 0. `getSelectedEditableLayer()`='psd_2'.

- **Brush** (`setCanvasMode('brush')` + real-mouse drag stroke) — ❌ **BROKEN (held/display), but diagnosis refined:**
  - After the stroke, the **composite** (#paintCanvas) region was UNCHANGED — sum still 5,573,059, magenta 0. No
    console error. So from the user's POV the brush does nothing.
  - **BUT** sampling **`psd_2.img` (the layer buffer) directly** found **750 magenta px** (the stroke landed there).
    So — contrary to run #4's guess that "paint never reaches the layer buffer" — the paint DOES reach `layer.img`;
    the failure is that the **post-stroke composite refresh does not re-render the modified layer buffer** onto
    #paintCanvas. The stroke is real but invisible.
  - Path: brush mousedown branch (canvas.js:3450, handles `'brush'||'erase'`) → `isLayerPaintMode()` →
    `_initLayerPaintCanvas()` + `_paintOnLayerAt(...)` (canvas.js:3460-3475). The composite-refresh after the
    commit is the gap (cf. run #4 `_refreshActiveLayerCompositePreviewNow` / `recompositeFromLayers`).
  - **Layer.img is an Image (not a canvas)** — `img.getContext` is undefined — so it can't be clearRect'd directly;
    layer paint replaces the Image.
  - **Undo:** `undoDrawStroke()` did NOT revert the layer (750→750). **Ctrl+Z (master undo) DID** (750→0). So the
    correct revert for layer paint is the global undo, not undoDrawStroke (which is for composite/zone pixel ops).
- **Eraser** (`setCanvasMode('erase')`) — ❌ **inferred** (NOT separately repainted): it shares the exact same brush
  mousedown branch (canvas.js:3450 → `_paintOnLayerAt` with the erase flag), so it has the identical held/display
  bug. Skipped a destructive re-test to avoid leaving another layer artifact; verify alongside Brush in the fix.
- **No fixes (deferred), no source changes.** Cleanup: Ctrl+Z reverted the brush stroke (psd_2.img magenta 750→0),
  verified center #55 still yellow 234,255,0 (run-#11 restore intact, Ctrl+Z didn't disturb it — that re-fill was a
  direct call, not on the undo stack), eyedropper + Zone Mode + layer deselected + regionCanvas 0. No console errors.
  **No test artifact left this run** (unlike #11). FG left at #ff00ff (transient UI state).
- **Focused-session map (now precise):** the Layer-Mode bug is a **composite-refresh-after-paint** gap — paint
  commits to `layer.img` but #paintCanvas isn't re-rendered from the layer stack afterward. This single fix should
  unblock Brush, Eraser, Color Brush (run #4), and likely Pencil/Dodge/Burn/Blur/Sharpen. Fill-click is a separate
  (routing) issue (run #11). Gradient already works. Re-verify the whole RETOUCH + paint group after the fix.

## Run #13 — 2026-05-29 — ADJUST dialog tools (Brightness/Contrast, Hue/Sat, Color Temp, Vibrance) — all PASS

Pivoted from the risky paint tools to the SAFE ADJUST family (composite adjustments with proven `undoDrawStroke`
undo, run #6). Prereqs OK (server 200, Zone Mode, no selection). All 6 ADJUST handlers exist.

- **🔑 Resolved the run-#6 native-`prompt()`-blocking worry:** `promptAdjustBrightnessContrast()` does NOT call
  `window.prompt` (overrode it — never invoked) and does NOT change the canvas on its own. Instead it opens a
  **custom DOM modal** (screenshot showed a clean "BRIGHTNESS / CONTRAST" dialog with Brightness/Contrast sliders +
  Cancel/Apply). So the `promptAdjust*` family is **non-blocking custom dialogs**, safe to invoke. The dialog's
  Apply calls the underlying engine `adjust*()`.
- **Verification method:** drove the engines directly (precise + cleanly undoable) and separately confirmed the
  dialog opens. The dialog's sliders are custom (NOT `<input type=range>` — the range-finder only saw zone-panel
  sliders), so the slider→engine wiring wasn't independently driven; the dialog-open + engine are verified, wiring
  assumed. Engine signatures: `adjustBrightnessContrast(brightness, contrast)`, `adjustHueSaturation(hueShift,
  saturation, lightness)`, `adjustVibrance(amount)`, `adjustColorTemperature(shift)`. Dialog closes via `closeModal()`.
- **Brightness/Contrast** — `adjustBrightnessContrast(40,20)`: region(600,600) sum 4,410,394 → 4,933,591 (brighter),
  undoDrawStroke → 4,410,394 exact. ✅ PASS. (Region 900,900 didn't change — clamped/grayscale; not a fault.)
- **Hue/Saturation** — `adjustHueSaturation(60,30,0)`: 4,410,394 → 4,471,687, undoDrawStroke restored exact. ✅ PASS.
- **Color Temperature** — `adjustColorTemperature(40)`: 4,410,394 → 4,629,387 (warm shift), undo restored exact. ✅ PASS.
- **Vibrance** — `adjustVibrance(...)`: a SUM metric showed no change (region 600,600 is white → 0 saturation, and
  sum is blind to saturation anyway). Re-tested with a **colorfulness metric** Σ(|R-G|+|G-B|+|R-B|): colored region
  700,1100 went 337,302 → 366,684 (more saturated) while grayscale region 900,900 stayed 0→0 (correct — vibrance
  preserves gray). undoDrawStroke restored 700,1100 to 337,302. ✅ PASS.
- **Process notes / mistakes caught:** (1) an undo-verification loop keyed its stop-condition on the WRONG region
  (the grayscale 900,900 instead of the changed 700,1100) so it skipped the undo → vibrance was briefly left applied;
  caught it and restored. Lesson: use the SAME region for the apply-check and the undo-check. (2) the open dialog's
  Cancel button didn't match a `<button>` text query (custom markup); `closeModal()` closed it; my first "dialog
  still open" reading was a FALSE POSITIVE matching the ADJUST menu's "Brightness / Contrast" label — refined the
  detector to the dialog title element + screenshot to confirm closed.
- **No fixes, no source changes, NO artifact** — every adjustment applied then undone; final verified state:
  eyedropper, Zone Mode, reg600 4,410,394, reg900 3,166,590, cf700_1100 337,302, regionCanvas 0, no dialog, no console
  errors. **ADJUST menu now 6/8** (these 4 + Grayscale/Invert from run #6).
- **Remaining ADJUST:** Color Replace (`openColorReplaceDialog`) + Gradient Map (`openGradientMapDialog`) — the
  `open*Dialog` ones need real inputs (from/to colors; gradient stops), so a future run must drive those dialogs.

## Run #14 — 2026-05-29 — ADJUST finish: Gradient Map + Color Replace — both PASS (ADJUST menu 8/8 complete)

Completed the ADJUST menu. Both have direct-arg engines (no dialog-driving needed), undoable via undoDrawStroke.
Engine signatures: `applyGradientMap(color1, color2)`, `autoColorReplace(targetHex, replacementHex, tolerance)`.
Prereqs OK (server 200, Zone Mode, no selection).

- **Gradient Map** — `applyGradientMap('#001040', '#ffe000')` (maps dark luminance→navy, bright→yellow): region
  600,600 sum 4,410,394 → 4,339,549 and region 900,900 3,166,590 → 3,671,594 (both remapped by luminance). The undo
  loop checked BOTH regions in its stop-condition → undoDrawStroke restored both to exact originals. ✅ PASS. Console clean.
- **Color Replace** — `autoColorReplace('#eaff00', '#ff00ff', 40)` (replace yellow→magenta, tolerance 40): the yellow
  #55 pixel(1024,1024) went **234,255,0 → 255,0,255** (exact magenta), region(980,980,100×100) 6,543,839 → 6,645,861.
  undoDrawStroke restored the pixel to 234,255,0 and region to 6,543,839. ✅ PASS. Console clean.
- **No fixes, no source changes, NO artifact.** Applied the run-#13 lesson (undo stop-condition checks ALL sampled
  regions/pixels) — clean restore both times. Final verified state: eyedropper, Zone Mode, #55 yellow (234,255,0),
  reg600 4,410,394, reg900 3,166,590, regionCanvas 0, no dialog open, no console errors.
- 🎉 **ADJUST MENU COMPLETE (8/8):** Brightness/Contrast, Hue/Saturation, Color Temperature, Vibrance (run #13),
  Grayscale, Invert Colors (run #6), Gradient Map, Color Replace (run #14) — all PASS, all cleanly undoable.
- **Whole-suite status:** SELECT 5/6 (Zone Pick pending — needs a spec pattern in a zone). MASK 6/7 (Copy Mask pending
  — needs a 2nd zone). TRANSFORM 2/2. ADJUST 8/8. PRIMARY: 8 PASS (Rect, Wand, Pick Color, Lasso, Pick Item, Move,
  Transform-layer, Gradient), Fill/Brush/Eraser BROKEN (Layer-Mode composite-refresh, held), Text/Shape/Pen pending.
  RETOUCH held pending the one Layer-Mode composite-refresh-after-paint fix (runs #4/#11/#12). **The remaining
  testable-without-paint-fix tools are: Text/Shape/Pen (vector — caution), Copy Mask, Zone Pick.** After those, the
  bulk of remaining work is the single focused layer-paint fix that unblocks the whole RETOUCH + click-paint group.

## Run #15 — 2026-05-29 — PRIMARY vector: Pen (PASS) + Shape & Text (investigated → deferred)

Investigated the 3 remaining PRIMARY vector tools to classify them (selection/path = safe; pixel-paint = held).
Prereqs OK (server 200, Zone Mode). No artifact this run.

- **Pen** (`setCanvasMode('pen')`) — ✅ **PASS. It's a PEN / BEZIER PATH tool (non-destructive).** State lives on
  `window.penPoints` / `penClosed` / `penDragging` / `penDragIndex`. Test: 3 real-mouse clicks at canvas points →
  `penPoints.length` went 0 → 3, each entry a bezier node `{x,y,cx1,cy1,...}`; the first node was at canvas
  **(541,610)** — exactly the mapped coord of my first click (screenshot 700,400). `penClosed` stayed false (didn't
  close). Pressing **Escape cleared the path** (penPoints → 0). No console error, no pixel/selection commit (path is
  in-memory until you do something with it). Clean.
- **Shape** (`setCanvasMode('shape')`) — ⏸ **deferred (investigated, not action-tested).** A drag in Zone Mode is a
  **NO-OP**: regionCanvas unchanged (no selection) AND composite region unchanged (no paint); the contextual banner
  fell through to the template-drag text "Pick which finish layer the template drag should move." So Shape is a
  **layer-oriented draw tool** (Layer-Mode-gated, like Brush/Fill) that does nothing useful in Zone Mode. In Layer
  Mode it would rasterize a shape onto the layer → will hit the held composite-refresh-after-paint bug. Not tested in
  Layer Mode (artifact-prone + would just re-confirm held).
- **Text** (`setCanvasMode('text')`) — ⏸ **deferred (investigated, not action-tested).** Has `window._textInputActive`
  state + a "Smart Text Pick" toggle; on a canvas click it opens a text entry and renders text onto the active layer
  → same layer-draw family, same held bug. Not action-tested (would need typing + commit onto a layer = artifact-prone).
- **No fixes, no source changes, no artifact.** Cleanup: Escape cleared the pen path; final state eyedropper, Zone
  Mode, penPoints 0, regionCanvas 0, no console errors. (FG left at its prior value — transient UI state.)
- **Takeaway:** the non-paint PRIMARY icons are now ALL verified PASS (Move, Pick Item, Transform-layer, eyedropper,
  Magic Wand, Lasso, Rectangle, Gradient, Pen). Shape + Text join the held layer-draw group (Brush/Eraser/Fill-click/
  Color Brush) — all blocked behind the ONE focused Layer-Mode composite-refresh-after-paint fix; re-verify the whole
  group together after that fix. **Only two tools remain that are testable without the paint fix: Copy Mask (needs a
  2nd zone with a mask to copy to) and SELECT Zone Pick (needs a spec pattern assigned to a zone) — both modify
  project/zone data, so a future run must set up + tear down carefully.**

## Run #16 — 2026-05-29 — last untested tools: Copy Mask (PASS) + Zone Pick (deferred) → SUITE FULLY MAPPED

Tackled the two remaining truly-untested tools. No zones accessor exists (`window.getZones`/`window.zones` undefined),
so I used **regionCanvas-per-zone + toasts** as the readout. Probing zones 0/1/4 showed regionCanvas 0 — the project's
zones are **color-based (no region masks set)**, which made a transient test mask safe to create + fully clear.

- **Copy Mask** — engine `copyMaskToZone(targetIndex)` (also `toggleCopyMaskDropdown(e)` UI opener, `clearZoneRegions(
  zoneIndex, noToast)`). Test: selectZone(0) + wand click → zone 0 got a **475,182 px** mask. `copyMaskToZone(4)` →
  selectZone(4) showed regionCanvas **475,182** = EXACT copy; toast "Copied mask from Zone 1 → Zone 5" (index 4 = UI
  "Zone 5"). ✅ PASS. Cleanup: `clearZoneRegions(4,true)` → zone 4 rc 0; `clearZoneRegions(0,true)` → zone 0 rc 0;
  both zones restored to their original empty state. No console error, no artifact. **MASK MENU 7/7 COMPLETE.**
- **Zone Pick** (`setCanvasMode('zone-pick')`) — ⏸ deferred. Activates correctly (mode 'zone-pick', "ZONE-PICK"
  banner). A click on zone 0 (no spec pattern assigned) selected **nothing** (regionCanvas 0, no error) — the correct
  no-op per the run #5 note ("needs a spec pattern to have sub-pieces to pick"). Verifying the actual sub-piece pick
  requires ASSIGNING a spec pattern to a zone (modifies the zone's finish; no zones accessor for safe verify/restore),
  so the action-test is deferred to a focused session. No artifact (nothing selected).
- **No fixes, no source changes, no artifact.** Final state: eyedropper, Zone Mode, zone 0 selected, regionCanvas 0,
  no console errors.

### 🗺️ MILESTONE — every tool in the suite is now mapped (verdict or documented deferral)
- **PASS (31):** SELECT 5 · MASK 7/7 · TRANSFORM 2/2 · ADJUST 8/8 · PRIMARY 9 (Rect, Magic Wand, Pick Color, Lasso,
  Pick Item, Move, Transform-layer, Gradient, Pen).
- **❌ BROKEN — one shared root cause (Layer-Mode composite-refresh-after-paint, diagnosed runs #4/#11/#12):** Color
  Brush, Fill (click), Brush, Eraser. ⏸ same family (layer-draw, not individually re-tested to avoid artifacts):
  Shape, Text, and the rest of RETOUCH (Clone, Smudge, Pencil, Dodge, Burn, Blur, Sharpen).
- **⏸ DEFERRED (focused data-setup session):** SELECT Zone Pick.
- **REMAINING WORK:** (1) the single focused **Layer-Mode composite-refresh-after-paint fix** — paint commits to
  `layer.img` but #paintCanvas isn't re-rendered from the layer stack after the stroke; revert is Ctrl+Z not
  undoDrawStroke (run #12). This one fix unblocks the entire RETOUCH + click-paint + Shape/Text group; re-verify them
  all after. (2) Zone Pick action-test with a spec pattern assigned. (3) A final second pass over BROKEN/FIXED items.
  The autonomous loop has completed its discovery/mapping mission — the rest needs the focused paint fix (best done
  with the owner present, per the held-bug policy) + the two data-setup tests.

## Run #17 — 2026-05-29 — 🚨 MAJOR CORRECTION: the "broken paint group" was a STALE-CANVAS-RECT measurement error

Went in to pinpoint the layer-paint composite-refresh "bug" for the focused-session writeup. Read the full flow
(`_initLayerPaintCanvas` 18775 → `_paintOnLayerAt` 19189 → `_commitLayerPaint` 19088 → `recompositeFromLayers` 16623)
— it all looked correct, and `triggerPreviewRender` (7398) only touches the preview panes, not #paintCanvas. So I
did a live diagnostic: painted a brush stroke (magenta FG) and measured.

**The smoking gun:** `#paintCanvas.getBoundingClientRect()` is **{left:747, top:468, width:416, height:416}** — but
I had hardcoded **top:366** since run #7. The canvas had shifted DOWN ~102px (layout reflow over the session). So
EVERY canvas click/drag in runs #4/#11/#12/#15 landed at the wrong canvas coords (≈500 canvas-px off in y), and I
sampled the composite in the WRONG region. Evidence this run:
- Brush stroke at screenshot (705,395). With the stale rect I assumed canvas (571,581); with the LIVE rect it's
  canvas (571,**79**). The painted magenta landed at canvas (553-588, 59-94).
- layer.img (psd_2) got the paint (1070 magenta) AND the **composite #paintCanvas showed 217 magenta px at the actual
  paint location** (region 530,45,120,80). In run #12 I sampled (540,540,160,160) — y 540-700 — and missed paint at
  y≈59-94, so I wrongly concluded "composite unchanged / held."
- Ctrl+Z reverted cleanly: psd_2 layer magenta 0, bbox restored to [406,355,1295,2003] (so psd_2 was NOT corrupted by
  earlier runs — this run's paint at y=59 had temporarily expanded the bbox top, and undo restored it), composite 0.

**→ Brush is CONFIRMED WORKING (❌→✅).** Layer paint commits to layer.img AND displays in the composite correctly.
**This invalidates the run #4/#11/#12 "held/broken" verdicts** for the entire paint group — all measured with the
stale rect, so paint landed outside my sampled regions:
- **Fill** (run #11 ❌): the click "did nothing to pixel (1024,1024)" because with rect.top=468 the click landed at
  canvas (1024,**522**) — it filled THERE. Engine works; click almost certainly works. → ⏸ RE-TEST.
- **Eraser** (run #12 ❌, inferred): shares Brush's path → almost certainly works. → ⏸ RE-TEST.
- **Color Brush** (run #4): crash fix (run #3 `_t0`) is real and holds; the "doesn't paint" was the stale-rect zoom
  looking at the wrong spot. → 🔧⏸ RE-TEST.
- **Shape, Text** (run #15 ⏸) + **Clone/Smudge/Pencil/Dodge/Burn/Blur/Sharpen** (RETOUCH, never individually tested):
  same family → RE-TEST with the fresh rect.

🔑 **METHODOLOGY FIX (do this EVERY run from now on):** read `#paintCanvas.getBoundingClientRect()` LIVE at run start;
never hardcode it. The mapping: `canvasX=(viewportX-rect.left)*2048/rect.width`, `canvasY=(viewportY-rect.top)*2048/
rect.height`; computer-tool coords are SCREENSHOT-space = viewport/(innerWidth/screenshotWidth)=/1.2245. The rect can
drift between runs as the layout reflows — a hardcoded rect silently sends every click to the wrong place.

**NO source change this run** (no bug to fix — the tools work). psd_2 fully restored, no artifact, no console errors.

### REVISED OUTLOOK (supersedes the run #16 "broken paint group")
There is very likely **NO layer-paint bug**. The next run(s) should systematically RE-TEST the paint group with the
LIVE canvas rect: Brush ✅ (done) · Fill · Eraser · Color Brush · Shape · Text · Clone/Smudge/Pencil/Recolor/Dodge/
Burn/Blur/Sharpen. If they pass (expected), the suite is ~fully green (only Zone Pick's spec-pattern action-test +
a second pass remain) and the planned "focused paint fix" is unnecessary. **Verify each with a fresh-rect before/after
at the ACTUAL paint location**, and revert layer paint with **Ctrl+Z** (not undoDrawStroke).

## Run #18 — 2026-05-29 — paint-group re-test attempt; found 2 MORE confounds (rect drifts LIVE + a cruft layer)

Tried to systematically re-test the paint group per run #17. Hit two confounds that make clean autonomous paint
testing hard, and (correctly, per the run-#17 lesson) declined to issue verdicts from confounded data.

- **CONFOUND 1 — the canvas rect drifts mid-run (not just between runs).** Read `#paintCanvas.getBoundingClientRect()`
  at setup: top=**366**. Re-read a few calls later: top=**464**. It shifts ~100px *during* a session — almost certainly
  an autosave/notification banner toggling the header height. So reading it once per run is NOT enough; it can move
  between the rect-read and the click. Any click whose target was computed from a now-stale rect lands ~500 canvas-px
  off in y.
- **CONFOUND 2 — a stray "Transform Selection" synthetic layer is the active/top layer.** While re-testing Fill, the
  UI showed "FILL BUCKET → layer:**Transform Selection**" — the active layer had become `selxform_…v2qk9` "Transform
  Selection" (a synthetic layer created by the transform-selection feature during my earlier element-pick/Pick-Item
  tests, runs #5/#9). It sits on TOP, so a Layer-Mode click selects IT (not psd_2). My fill therefore targeted the
  wrong layer, and I was checking psd_2 for the result → false "no fill." (psd_2 magenta 0 AND Transform-Selection
  magenta 0 — no paint committed; the click appears to have been consumed by layer-selection.)
- **Fill verdict: INCONCLUSIVE (confounded).** Both confounds were active (rect drifted to 464 mid-test; the click hit
  the cruft layer). The click selecting the top layer instead of filling is consistent with the run-#11 "Layer-Mode
  click interception" hypothesis, but I will NOT assert "broken" from confounded data (that's the run-#17 trap in
  reverse). Needs a CLEAN focused test.
- **Brush ✅ (run #17) HOLDS** — it was verified by paint appearing in the composite (independent of which layer/
  region), so it's not subject to these confounds.
- 🔑 **Updated method for paint testing (both confounds):** (a) read getBoundingClientRect() IMMEDIATELY before the
  click AND re-read right after — if top moved, discard the test; (b) FIRST remove any `selxform_*` cruft layers, then
  explicitly `selectPSDLayer('psd_2')` and VERIFY `getSelectedEditableLayer().id==='psd_2'` right before the click;
  (c) verify the result on the ACTUAL active layer, not an assumed one.
- **Cleanup:** deselected, eyedropper, Zone Mode. **psd_2 fully intact** (bbox [406,355,1295,2003], magenta 0 — NO fill
  artifact), no console errors. ⚠️ **1 stray "Transform Selection" (`selxform_…v2qk9`) layer remains on the PSD** — test
  cruft I created via transform/pick tests. NOT deleted autonomously (permanent-deletion caution). **The owner / focused
  session should delete it** (it's clutter on top of the real psd_0–10 layers, and it hijacks Layer-Mode clicks).
- **Honest status of the run-#17 optimism:** "the whole paint group works" is NOT yet confirmed. Brush ✅ + Gradient ✅
  (drag) are the only confirmed-working paint tools. Fill (click) remains unproven and may genuinely be intercepted in
  Layer Mode. The clean focused session is the right place to settle Fill + Eraser + Color Brush + Shape + Text + the
  RETOUCH brushes (remove cruft, drift-aware clicks, verify active layer).

## Run #19 — 2026-05-29 — THIRD confound (drag-on-element MOVES it); STOP autonomous paint testing

Attempted a clean drift-aware Color Brush test + an A/B control with the known-working Brush. Found a third confound
that makes autonomous paint testing infeasible, and (again) twice moved + restored psd_2 while chasing it.

- **Color Brush test:** rect held at 468 during the drag (R1==R2), active layer stayed psd_2, FG magenta, drag on a
  #55 (canvas ~995,497 — inside psd_2). Result: **no magenta anywhere** (composite wide-scan 0, psd_2.img 0).
- **A/B control — the PRIMARY Brush (run-#17-confirmed-working), exact same drag:** ALSO painted nothing (composite 0,
  psd_2.img 0). Since the known-good tool failed under identical conditions, the problem is my METHOD/STATE, not the
  tool.
- **Root cause of the "no paint": drag-on-element = MOVE.** Checking psd_2.bbox revealed it had shifted
  **[406,355,1295,2003] → [584,473,1473,2121]** (≈ +178,+118 = the sum of my two ~(+88,+59) drag deltas). So in Layer
  Mode, **a drag that begins on an existing layer element MOVES the element** (the drag is routed to layer-move),
  rather than painting. My run-#19 drags landed on the #55 → moved psd_2. Run #17's brush PAINTED because it dragged
  on EMPTY canvas (canvas y≈79, outside psd_2's [355..] content). `freeTransformState` was null (no transform overlay
  involved — it's the element-move-on-drag behavior).
- **Restore:** 2× Ctrl+Z → psd_2.bbox back to **[406,355,1295,2003]** exactly (via [495,414,1384,2062] after the 1st).
  No lasting corruption, magenta 0.
- 🚨 **THREE confounds now block clean autonomous paint testing:** (1) **rect drifts mid-run** (366↔468); (2) **stray
  "Transform Selection" cruft layer** auto-selected by clicks; (3) **drag-on-element MOVES the element** instead of
  painting. Each masquerades as a "broken paint tool." I have twice corrupted + restored psd_2 (runs #11, #19) chasing
  paint verdicts under these confounds.
- **Honest verdict status:** the Fill / Color-Brush "no paint" results (runs #11/#18/#19) are ALL confounded — NOT
  clean. Only **Brush ✅ and Gradient ✅** (paint shown in composite, run #17/#11) are confirmed. Whether Fill (click)
  and the RETOUCH brushes truly work or not CANNOT be determined in this confound-heavy autonomous session.
- 🛑 **STRATEGIC PIVOT (recommendation):** STOP autonomous paint-tool testing — it's infeasible here and risks
  corrupting the user's layers. The paint group must be settled in a **focused session with the owner**: reload to a
  clean state, delete the stray `selxform_*` cruft layer(s), confirm the rect is stable, and test each paint tool by
  dragging on EMPTY canvas (and clarify the intended paint-vs-move routing when a drag starts on an element — that may
  itself be a real UX bug worth fixing). **Future autonomous loop runs should instead do the SECOND-PASS re-verification
  of the 31 confirmed-PASS NON-paint tools** (SELECT 5, MASK 7, TRANSFORM 2, ADJUST 8, PRIMARY 9) — clean, safe, no
  canvas-paint confounds — to catch any regressions. psd_2 restored; 1 cruft layer still flagged for removal.

## Run #20 — 2026-05-29 — SECOND PASS begins: ADJUST re-verification (4/8), no regression

Per the run-#19 pivot, started the second pass on the confound-free non-paint tools. Re-verified 4 ADJUST engines
(handler-invoked, so no rect-drift/cruft/drag-move confounds), each apply → verify-changed → undo → verify-restored:
- **Grayscale** `adjustGrayscale()` — colorfulness(700,1100) 315,860 → 0 → 315,860. ✅
- **Invert Colors** `adjustInvertColors()` — sum(600,600) 4,410,394 → 8,339,606 → 4,410,394. ✅
- **Brightness/Contrast** `adjustBrightnessContrast(40,20)` — 4,410,394 → 4,933,591 → restored. ✅
- **Color Temperature** `adjustColorTemperature(40)` — 4,410,394 → 4,629,387 → restored. ✅
All change values are IDENTICAL to runs #13/#14 → the engines are deterministic and **un-regressed**. Composite fully
restored (sum600 4,410,394, cf700 315,860), regionCanvas 0, eyedropper/Zone Mode, no console errors, no artifact.
**Second-pass tracker:** ADJUST 4/8 done. Remaining 2nd-pass: ADJUST {Hue/Sat, Vibrance, Gradient Map, Color Replace}
(handler-invoked, clean) → MASK ops (need a region mask) → TRANSFORM (overlay-open + cancel) → SELECT + non-paint
PRIMARY (canvas clicks — use the drift-aware rule: read rect live + re-read after each click). Paint group parked for
the focused session.

## Run #21 — 2026-05-29 — SECOND PASS cont'd: ADJUST re-verification COMPLETE (8/8), no regression

Re-verified the remaining 4 ADJUST engines, each apply → verify → undo → restore:
- **Hue/Saturation** `adjustHueSaturation(60,30,0)` — sum(600,600) 4,410,394 → 4,471,687 → restored (exact match run #13). ✅
- **Vibrance** `adjustVibrance(70)` — colorfulness(700,1100) 315,860 → 345,464 → restored. ✅
- **Gradient Map** `applyGradientMap('#001040','#ffe000')` — sum600 4,410,394→4,334,399; sum900 3,166,590→3,671,594
  (exact match run #14); both restored. ✅
- **Color Replace** `autoColorReplace('#eaff00','#ff00ff',40)` — pixel(1024,1024) 234,255,0 → 255,0,255 → restored. ✅
No console errors, composite fully restored (allRestored=true), no artifact. **ADJUST second pass DONE: 8/8 engines
deterministic + un-regressed.** Next 2nd-pass targets: MASK ops, TRANSFORM, SELECT + non-paint PRIMARY (drift-aware
canvas clicks). Paint group remains parked for the focused session; 1 "Transform Selection" cruft layer still flagged.

## Run #22 — 2026-05-29 — SECOND PASS cont'd: MASK region-ops (invert/smooth/mirror), no regression

Created a partial region mask via a Zone-Mode wand click (475,271 px; Zone Mode = composite-based, so no Layer-Mode
cruft/drag confounds, and the click location is irrelevant for testing the MASK ops). Re-verified the 3 region-ops:
- **invertRegionMask** ✅ — 466,646 → **3,727,658** = EXACTLY 4,194,304 − 466,646 (exact complement), and reversible.
- **smoothRegionMask** ✅ — on the big inverted mask: 3,727,658 → **3,692,111** (~35K edge pixels rounded off). (On a
  clean color-selection mask it was net-zero, which is fine — smoothing a smooth-edged region barely changes the count.)
- **mirrorRegionMask** ✅ — runs cleanly, count-invariant (as in run #5; the geometry flip is count-invariant so not
  independently verified via count — assume OK).
- 🔑 **GOTCHA (important for all future MASK/selection verification): the `regionCanvas` DISPLAY is STALE after MASK
  ops.** invertRegionMask/etc. update the mask DATA, but the regionCanvas pixels do NOT auto-refresh, and
  `renderRegionOverlay()` does NOT refresh them either — only **`_doRenderRegionOverlay()`** forces the refresh. My
  first reads (showing "no change") were the stale display. **Always call `_doRenderRegionOverlay()` before reading the
  regionCanvas count after a MASK op.** (This is the regionCanvas analogue of the run-#8 spatial-mask stale-bitmap.)
- Cleanup: `clearZoneRegions(0)` → regionCanvas 0; psd_2 #55 intact (px1024 yellow — MASK ops operate on the zone mask,
  not the layer pixels); eyedropper/Zone Mode; no console errors, no artifact.
- **MASK 2nd-pass: 3/7 done** (invert, smooth, mirror). Copy Mask was clean in run #16. Include/Exclude/Erase Spatial
  need drift-aware canvas drags — deferred to a later 2nd-pass run. Next: TRANSFORM, then SELECT + non-paint PRIMARY.

## Run #23 — 2026-05-29 — TRANSFORM 2nd-pass (1/2) then ⚠️ SERVER DOWN — ended per prereq rule

- **Transform Pattern/Base** ✅ re-verified (before the server issue): `activateZoneTransform()` on zone 0 → returned
  true, opened a free-transform overlay on the base (`freeTransformState = {target:"base", scaleX, rotation, …}` —
  matches run #6). Cancelled cleanly via `cancelActiveTransformSession()` (ft→null). No regression.
- ⚠️ **PREREQ FAILURE — server on http://localhost:59876/ is DOWN.** The startup HEAD fetch returned "Failed to fetch";
  retried with GET on `/` AND `/paint-booth-v2.html` — BOTH "Failed to fetch". So the server (python on :59876, the
  user's persistent dev server) is not accepting HTTP connections. The in-browser app is STILL responsive client-side
  (JS executes, handlers work, the transform opened/cancelled fine — it's the already-loaded in-memory app), but new
  HTTP requests fail. Per the loop's HARD RULE ("if server down, log it to FINDINGS and end the run — do not thrash"),
  **ending this run.** Did NOT get to re-verify Transform Decal (2nd item) or the SELECT/PRIMARY second pass.
- **State left clean (client-side):** transform cancelled (ft null), eyedropper, Zone Mode, regionCanvas 0, psd_2 bbox
  [406,355,1295,2003] intact, no artifact. The stray "Transform Selection" cruft layer is still present (flagged).
- **For the next run:** the cron loop fires again in ~20 min; it will re-check the server. If :59876 is back (returns
  200), resume the second pass at **Transform Decal**, then **SELECT + non-paint PRIMARY** (drift-aware canvas clicks +
  `_doRenderRegionOverlay()` refresh before reading selection counts). If still down, log + end again. (I did not
  attempt to restart the server — it's the owner's process; not in scope for the autonomous loop.)
- **2nd-pass tracker:** ADJUST 8/8 ✅ · MASK 3/7 region-ops ✅ (+Copy Mask run #16) · TRANSFORM 1/2 ✅ (Pattern/Base;
  Decal pending) · SELECT + non-paint PRIMARY pending. Paint group parked for the focused session.

## 2026-05-29 (owner request, between cron fires) — SOURCE wheel-zoom RE-CENTER bug FIXED 🔧

- **Report (owner):** mouse-wheel zoom over the SOURCE pane (and "LIVE PREVIEW") pans the canvas around erratically,
  "doesn't resize properly," strands content off-view, and there's no easy way back to normal. Asked for a click-to-
  recenter OR auto-recenter-on-zoom-out.
- **Root cause** (paint-booth-3-canvas.js, SOURCE `viewport.addEventListener('wheel', …)`, ~line 8697): the handler
  intends cursor-anchored zoom, but its scroll math (`contentX = (scrollLeft + mx)/oldZoom; scrollLeft = contentX*newZoom
  − mx`) **ignores the centering MARGINS** `applyZoom()` writes to `#canvasInner` (marginLeft/Top) when the canvas is
  smaller than the pane. At the fit↔overflow boundary the margin jumps between a large value and 0, so the un-accounted
  offset (~340 screen px ÷ ~0.32 zoom ≈ 1000+ canvas px) is dumped into the scroll → the view lurches + content flies off.
- **Fix:** margin-aware anchor + auto-recenter. Capture pre-zoom `_oldMarginX/Y` (parseFloat of `#canvasInner` style
  margins) BEFORE the zoom; `contentX = (scrollLeft + mx − _oldMarginX)/oldZoom`; per axis — if the post-zoom canvas now
  FITS the pane → set that axis's scroll to **0** (margins re-center it = owner's "re-center as you scroll out"), else
  re-anchor `contentX*newZoom + newMargin − mx` (clamped ≥0). Dated audit comment in-source.
- **Verified live** (simulated WheelEvents): zoom-in 300% + pan into a corner, then wheel-out → the instant an axis fits
  (≤~33% in the 681px split pane) its scroll snaps to 0 and `#canvasInner` margins grow to center it (fully visible every
  step). Cursor-anchor error across the fit→overflow transition dropped from ~1000+ canvas px to **−6…−16 px (<1%)**.
- **3-copy:** synced (4 files), bumped canvas.js `?v=` → **spb-zoom-recenter-20260529**, reloaded, confirmed live, no
  console errors.
- **LIVE PREVIEW:** different mechanism — `transform: scale()` + `transform-origin: center center` (`_applyPreviewPaneZoom`,
  ~7189). Scales from center → can't drift sideways, returns cleanly to `scale(1)` on scroll-out → already self-centers,
  NO fix needed. (Offered owner an optional explicit 100%/reset button or pan-when-zoomed for the preview.)

## Run #26 — 2026-05-29 — 2nd pass: Transform Decal (re-verified) + Elliptical Marquee engine + marquee-drag methodology

- **Prereqs:** server 200, browser connected, zoom fix live (jsVer spb-zoom-recenter-20260529). editMode was 'layer'
  (leftover) → switched to 'zone' for selection testing. No artifact, no console errors, composite intact.
- **Transform Decal** (`activateFreeTransform('decal')`) ✅ re-verified — no decal selected → returns **false**,
  `freeTransformState` stays null, mode unchanged (eyedropper), toast "Select a decal first before using Transform
  Decal". Exact match to run #8. → **TRANSFORM 2nd-pass 2/2 COMPLETE.**
- **Elliptical Marquee — ENGINE ✅ re-verified:** `commitEllipseSelection({x:700,y:700},{x:1300,y:1300})` → active pixel
  selection of **282,697 px = 99.98%** of geometric π/4·600² (282,743); `hasActivePixelSelection()` true; rendered to
  regionCanvas. Selection math + commit correct.
- 🔑 **METHODOLOGY FINDING — marquee/rect drag-gestures are NOT exercisable via `left_click_drag`:** instrumented
  `commitEllipseSelection` (logging wrapper) + dragged the ellipse twice with correct canvas mapping and **zero rect
  drift** (top 297.2 both times) → commit called **0×**, no selection. So the synthetic `left_click_drag` does not drive
  the tool's mousedown→`isDrawing`/`_ellipseStart`→mouseup→commit state machine (canvas.js mousedown 3299-3301, mouseup
  3756-3767). A single real-mouse CLICK works (wand, run #7); a held drag-state gesture apparently does not (≥ for
  marquee in Zone Mode). `commitRectSelection(endPos, eventLike)` (22723) can't be invoked directly either — early-returns
  unless module-scoped `rectStart` (set only by a real mousedown) is present (22724). **Conclusion:** ellipse/rect
  selection ENGINES are sound; their drag GESTURES need real human/focused-session confirmation. NOT a regression (run #1
  verified ellipse's gesture historically; engine + source wiring correct).
- **Selection-state clarification:** marquee selections live in the **active-pixel-selection** (`hasActivePixelSelection`
  / `_getActiveSelectionInfo` → {zone,width,height,minX,minY,maxX,maxY,clipW,clipH}); regionCanvas DISPLAY reflects them
  only after `_doRenderRegionOverlay()`. A naive regionCanvas alpha read showed 0 until the engine ran / refresh called.
- **Cleanup:** cleared selection (`_clearActivePixelSelection`), restored the wrapped fn, eyedropper, Zone Mode,
  regionCanvas 0, ft null, composite intact (px1024 [234,255,0] = #55 yellow canary). No artifact, no console errors.
- **NEXT 2nd-pass:** CLICK-based SELECT/PRIMARY (Select All Color, Edge Detect, Magic Wand, Pick Color — real-mouse CLICK
  DOES register; drift-aware: read rect live + re-read after, refresh via `_doRenderRegionOverlay`), then Move Selection
  Border. Paint group parked; 1 cruft "Transform Selection" layer still flagged.
- 🔧 **BUGFIX (found while diagnosing the marquee drag) — pan-exemption list incomplete (canvas.js:8895):** the mousedown
  pan-vs-tool gate (8898) makes a left-drag a PAN when `canvasOverflows() && !drawToolActive`. `drawToolActive` is a
  hardcoded mode array (8895) that was MISSING 'ellipse-marquee' (its siblings 'rect'/'lasso' ARE present), so a zoomed-in
  (overflow) ellipse-marquee drag was hijacked as a pan → no selection. Code-confirmed: `canvasOverflows()`=true at 200%
  zoom + mode not in list → deterministic `pendingPan`. Same omission: **'gradient'**, **'spatial-erase'** (siblings
  spatial-include/-exclude ARE present). **FIX:** added 'ellipse-marquee','spatial-erase','gradient' to the array + dated
  audit comment. Synced (4 files), bumped canvas.js ?v= → spb-marquee-panfix-20260529, reloaded, served JS verified to
  contain the fix, no console errors, composite intact. **STILL MISSING (flagged, parked paint group):** 'shape','text' +
  RETOUCH brushes (colorbrush/clone/smudge/pencil/dodge/burn/blur-brush/sharpen-brush/recolor/history-brush) — drag tools
  that would pan-hijack when zoomed in; complete the list after verifying each.
- 🔑 **SHARPENED FINDING — `left_click_drag` cannot drive ANY drag-state canvas handler.** A/B control: an EYEDROPPER drag
  at 200% zoom did NOT pan (eyedropper is NOT pan-exempt, so a real drag SHOULD pan there) → proves the computer-tool
  `left_click_drag` doesn't trigger the app's mousedown→mousemove→mouseup drag machinery (pan, marquee, gradient, brush).
  Only single CLICKS register (wand/eyedropper/pen — runs #7/#9/#15). ⇒ the pan-hijack fix is verified by code analysis +
  served-code confirmation (deterministic gate), NOT by a behavioral drag; real-mouse behavior needs human/focused-session
  confirmation. **Corrects the run #9 assertion** that "left_click_drag is fine for marquee/box gestures" — it is NOT for
  drag-state tools (it works only for single-click tools).

## Run #27 — 2026-05-29 — 2nd pass click SELECT/PRIMARY: Pick Color ✅ + ZONE POPOUT panel covers the canvas (major confound)

- **Pick Color/eyedropper ✅ re-verified** — but first appeared broken: a center-canvas click left `eyedropperSwatch`
  empty and didn't fire the pick. **Root cause = the `zoneEditorFloat` panel ("ZONE POPOUT PANEL", z-index 36, class
  "zone-editor-float active") COVERS the left ~2/3 of the SOURCE canvas** when a zone is selected: panel viewport x[226,691]
  vs canvas x[256,917]. `document.elementFromPoint` at the click (vx≈587) returned the panel's `color-selector` div, not
  `#paintCanvas`, so the canvas mousedown handler (eyedropper pick, src 3403) never ran — only the document/viewport-level
  mousemove HOVER readout fired (status bar showed the right hover hex, but the swatch stayed empty). Probe across the
  canvas: fx 0.15-0.65 = float; fx 0.8-0.92 = paintCanvas (uncovered right strip, canvas x>~1348). Re-clicked the
  uncovered strip → `hitCanvas:true`, pick FIRED, `eyedropperHex`/`eyedropperRGB` dynamically = the clicked pixel (clean
  no-drift black-pixel click: pxAtClick [0,0,0] = eyedropperRGB "RGB: (0,0,0)").
- 🔑 **CORRECTION to run #26's A/B "control":** run #26 partly argued `left_click_drag` can't drive drags via "an eyedropper
  drag at 200% zoom didn't pan." That drag was at viewport x[482,676] — UNDER the float — so it hit the panel, not the
  canvas → INVALID control (confounded, same as the run #26 marquee drags which were also under the float).
- **Core conclusion HOLDS, now cleanly:** re-ran the ellipse-marquee drag on the confirmed-UNCOVERED bare canvas (both
  endpoints verified `elementFromPoint===paintCanvas` immediately before) → instrumented `commitEllipseSelection` called
  **0×**, no selection. So single real-mouse CLICKS reach the canvas + fire handlers (eyedropper picked), but
  `left_click_drag` does NOT drive the mousedown→mouseup drag-commit (marquee). Drag-gesture tools stay un-auto-verifiable;
  engines sound (run #26).
- ⚠️ **Rect-drift OSCILLATES (272↔297 px) between calls** (header height toggling) → click coords from one call can be
  ~77 canvas-px off by the next. A colored-pixel eyedrop got drift-muddled (scan: cyan [0,211,243] at (1450,500);
  post-click read green [1,255,0]) — discarded as inconclusive; the no-drift black click was the clean confirmation.
- **FLAG for owner (UX):** the ZONE POPOUT panel overlapping ~2/3 of the SOURCE canvas blocks canvas tools (eyedropper,
  wand, brush, marquee) on that region until it's closed. Intended (closable popout) or a layout issue to fix?
- **Cleanup:** cleared selection, eyedropper, Zone Mode, regionCanvas 0, all instrumentation/wrappers removed, #55 canary
  [234,255,0] intact, no artifact, no console errors. (One javascript_tool result was blocked by a content filter —
  "[BLOCKED: Cookie/query string data]" — on an event-listener-install snippet; harmless, re-approached without it.)
- **NEXT (focused, like the paint group):** CLOSE `zoneEditorFloat` for full canvas access + a drift-robust protocol (read
  rect immediately before each click, re-read after, invalidate if moved), then re-verify wand / Select All Color / Edge
  Detect / Move Selection Border.

## Run #28 — 2026-05-29 — 2nd pass click SELECT/PRIMARY: 🎯 ENGINE-LEVEL re-verification (4 tools) — beats the click confounds

- **Setup:** bypassed the zoneEditorFloat via `style.pointerEvents='none'` (reversible) so clicks could reach the canvas.
- **Click path STILL failed (environmental, NOT a tool bug):** an eyedropper click on a bare cyan pixel — direct hit
  (`elementFromPoint`=paintCanvas), rect stable — left `eyedropperHex` stale (#000000): the mousedown PICK did not fire
  (only the mousemove hover readout did). Wand clicks (4×, various colors) → no selection. Screenshot confirmed the app is
  healthy + the hover readout tracks the cursor → so it's a mousedown-DELIVERY problem (computer-tool clicks not landing a
  usable mousedown on the canvas this session), compounded by rect-drift OSCILLATING 272↔309 every 1-2 calls. The
  eyedropper fired ONCE in run #27 → intermittent.
- 🎯 **PIVOT — verify the ENGINES directly (no click), like run #26's `commitEllipseSelection`. All work cleanly:**
  - **Magic Wand ✅** `magicWandFill(1024,1024,32,false)` → 5,076 px contiguous (985-1101 × 996-1076) at #55 yellow; has=true.
  - **Select All Color ✅** `selectAllColor(1024,1024,32,false)` → 204,456 px (ALL yellow within tol, non-contiguous) — correctly ≫ wand's contiguous 5,076.
  - **Edge Detect ✅** `edgeDetectFill(startX,startY,tolerance,addToExisting,subtractMode)` (canvas.js:5426). With tol 32 → 730 px bounded (1010-1042 × 1017-1044, stops at edges; matches run #1's 704). ⚠️ Omitting `tolerance` floods the whole canvas (4,194,304) — missing-arg artifact, not a bug.
  - **Move Selection Border ✅** `activateSelectionMove()` (mode→'selection-move', ret true) + `nudgeRegionSelection(60,0)` → selection bounds shifted EXACTLY +60,0 (minX 1010→1070, minY unchanged).
- 🔑 **CORRECTS run #7's assertion** that "direct `magicWandFill()`/handler calls don't register." They DO — magicWandFill,
  selectAllColor, edgeDetectFill all create real selections (has=true, regionCanvas populated) when called directly with
  valid args. Run #7's "only the real mouse registers" was about synthetic mouse EVENTS / the click pipeline, NOT direct
  engine calls. **Engine-level verification is the reliable path for click-based selection tools** — immune to the float,
  rect-drift, and mousedown-delivery confounds. Likely also unblocks the parked PAINT group (try `fillBucketOnLayer`,
  `_paintOnLayerAt` directly — but mind the layer-undo/corruption caveats from runs #11/#19).
- **Cleanup:** cleared selection, eyedropper, Zone Mode, zoneEditorFloat pointerEvents restored, regionCanvas 0, #55 canary
  [234,255,0] intact, no artifact, no console errors.
- **FLAGS for owner stand:** (1) zoneEditorFloat (ZONE POPOUT) covers 2/3 of the SOURCE canvas; (2) rect-drift oscillation
  (canvas top 272↔309, likely the autosave-banner height toggling). Both hamper click-based UX + autonomous click testing;
  a fixed-height banner would stop the drift and unblock click-driven QA.
- **NEXT:** engine-verify MASK spatial (include/exclude/erase) + remaining PRIMARY (Pick Item/Layer Element, Transform-
  layer, Gradient, Pen, Rect), then the PAINT group via engine calls.

## Run #29 — 2026-05-29 — 2nd pass: Transform-layer ✅ re-verified; autonomous 2nd-pass limit reached

- **Transform (layer) ✅** — `activateLayerContextTransform()` (editMode→layer, psd_2) → ret true, opens a free-transform
  on the LAYER (`freeTransformState` {target:'layer', layerId:'psd_2', scaleX, rotation, centerX}; matches run #10).
  `cancelActiveTransformSession()` → ft null, psd_2 bbox [406,355,1295,2003] unchanged (no commit, no corruption).
- **Surveyed the rest of the 2nd-pass backlog — all blocked for clean autonomous re-verification:**
  - **MASK spatial (include/exclude/erase):** the brush paints via `_paintScopedSpatialCircle(zone,scopeMask,w,h,cx,cy,radius,value)` (canvas.js:1701) — **closure-scoped, NOT on window** (unlike `_buildZoneScopedSelectorMask` right next to it), so no direct engine call; and the brush-drag is click-confounded. Mask lives at `zones[i].spatialMask` (Uint8Array). Verified runs #7/#8 (real mouse).
  - **Gradient:** `fillGradientOnLayer(x1,y1,x2,y2,gradientType,layerOverride)` (canvas.js:1869) IS on window, but a DIRECT call bypasses the handler's undo-push → **non-undoable** (run #11 caveat) → layer-corruption risk on live psd_2. Defer to the handler/drag path + clean reload.
  - **Pen / Rect / Pick Item / Pick Layer Element:** need canvas clicks (confounded). `commitRectSelection` needs module-scoped `rectStart` (run #26). No click-free element-isolate engine (`isolateLayerElementAt` undefined).
  - **Paint group:** pixel-modify corruption risk (parked since run #19).
- 🏁 **CONCLUSION:** the autonomous 2nd pass is COMPLETE for all tools verifiable without a real canvas click or a risky
  pixel-write. Re-verified: ADJUST 8/8 · MASK region-ops 3/7 + Copy Mask · TRANSFORM 2/2 · SELECT/PRIMARY selection
  engines (wand/selectall/edge/move-border/marquee/eyedropper) · Transform-layer. **The remaining tools need a FOCUSED
  session.**
- ⚠️ **Highest-leverage fix to unblock that session = FIX THE RECT-DRIFT.** Canvas top wandered 272→309→317 this run
  (~45px). It breaks click-targeting AND is a real UX jank (the canvas visibly jumps as you work) — almost certainly the
  autosave-status/banner row changing the header height. A fixed-height header row would stop it and make autonomous
  click-testing of the whole remaining set viable. (Pinpoint the variable-height element by watching the canvas in both states.)
- **Cleanup:** eyedropper, Zone Mode, ft null, psd_2 intact, #55 canary [234,255,0], no artifact, no console errors.

## Run #30 — 2026-05-29 — 🎯 BIG CORRECTION: clicks + drags work when canvas uncovered; 4 tools re-verified (MASK 7/7 done)

- **Root discovery:** the run #27/#28 click/drag failures were ENTIRELY the **zoneEditorFloat overlapping the SOURCE
  canvas**, NOT a mousedown-delivery bug and NOT a `left_click_drag` limitation. This run the layout had reflowed — canvas
  left moved **256→747**: the float went from OVERLAY (canvas under it, left ⅔ covered) to DOCKED (canvas pushed right,
  beside it, fully UNCOVERED). With the canvas uncovered, both clicks AND drags work:
  - **Pick Color/eyedropper** (real click on #55 center, `elementFromPoint`=paintCanvas, stable rect) → `eyedropperHex`
    #000000→**#EAFF00**, `eyedropperRGB` "RGB: (234,255,0)" = clicked pixel. The mousedown pick FIRES.
  - **Pick Layer Element ✅** (real click) → isolated element bbox(824,971)-(1111,1311), **78,085 px**, layerId psd_2
    (`_spbLastPickedElementBbox` set). 🔑 The `selxform_*` isolation layer it spawns (run #18's "persistent cruft") is
    cleanly removed by **`cancelActiveTransformSession()`** → back to 11 layers, psd_2 intact. The cruft only persisted in
    runs #18/#19 because those sessions didn't cancel the isolation.
  - **Spatial Include ✅** (drag) → 1,418 value-1 (keep) marks in `zones[0].spatialMask`.
  - **Spatial Exclude ✅** (drag) → 1,418 value-2 (remove) marks (total 2,836).
  - **Spatial Erase ✅** (drag over the include region) → removed exactly the 1,418 include marks (inc 1418→0; the
    geographically-separate exclude marks untouched).
- 🎯 **CORRECTS run #28's "left_click_drag cannot drive drag-state handlers"** — that A/B + the marquee drags were all
  UNDER the float, so they hit the panel, not the canvas. Drag-state handlers (marquee, pan, spatial brush) DO fire via
  `left_click_drag` when the canvas is uncovered. So drag-based tools ARE autonomously testable when the float is docked.
- ✅ **MASK menu 2nd-pass now 7/7 COMPLETE** (smooth/invert/mirror [#22] + Copy Mask [#16] + include/exclude/erase [#30]).
  **Pick Layer Element ✅** (SELECT).
- 🔑 **The float's positioning is STATE-DEPENDENT (overlay ↔ docked)** — it varies between sessions/reflows. When DOCKED
  (canvas uncovered), the remaining click/drag tools are testable; when OVERLAY (canvas covered), they're blocked. Plus the
  vertical drift persists (canvas top 317↔346 this run) = a dynamic layout the owner should stabilize.
- **Drift cause REVISED:** NOT the header (NAV.header is `nowrap` → autosave text can't change its height) and NOT editMode
  (canvas top stable across toggles). The horizontal shift IS the float overlay↔docked; the vertical drift's exact trigger
  is still unpinned (intermittent, not editMode).
- **Cleanup:** clearSpatialMask→0, `cancelActiveTransformSession` removed the selxform, eyedropper, Zone Mode, 11 layers,
  psd_2 [406,355,1295,2003], #55 canary [234,255,0], no artifact, no console errors.
- **NEXT (while the canvas stays uncovered):** re-verify Pick Item (click + cancel-cleanup), Gradient (real drag), Pen
  (real clicks), Rect (real drag), then attempt the PAINT group (Brush/Eraser/Fill — pixel-modify; undo via Ctrl+Z, watch
  for layer corruption per runs #11/#19).

## Run #31 — 2026-05-29 — 2nd pass PRIMARY click/drag: Rect ✅ + Pick Item ✅ + Pen ✅ (canvas uncovered)

- Canvas still UNCOVERED (float docked, l:747, center=paintCanvas). Re-verified 3 PRIMARY tools via real mouse:
  - **Rectangle Select ✅** — drag (canvas 950,850→1250,1150) → rect selection 13,049 px, bounds (948,997)-(1101,1152) =
    drag-rect ∩ zone 0 (zone-scoped select; the active zone clips the rect). has=true.
  - **Pick Item ✅** — click → zone-pick mode + free-transform on the picked item (ft target="second_base", zone 0,
    scale/rotation/center). `cancelActiveTransformSession()` cancelled cleanly: ft null, 11 layers, **NO selxform cruft**
    (zone-item transform, not a layer isolation — so Pick Item itself is clean; only Pick LAYER Element spawns a selxform).
  - **Pen ✅** — 3 clicks → penPoints 0→3, each {x,y,cx1,cy1,cx2,cy2} (bezier); first canvas (898,897) ≈ click (900,900);
    penClosed false. Matches run #15.
- ⚠️ **Escape (computer-tool key) did NOT clear the pen path** (penPoints stayed 3 after Escape) — likely the synthetic key
  lacked canvas/document focus, OR an Escape-clears-pen hiccup. Cleared via JS. The pen's point-ADDING (tool action) works.
- 🔑 **LIVE PREVIEW overlaps the canvas's RIGHT side** — `elementFromPoint` at canvas x≳1397 returns livePreviewImg. So the
  reliably-clickable canvas zone is ~x 0-1397 (vx 747-1198); keep test clicks/drags central.
- **Cleanup:** penPoints 0, eyedropper, Zone Mode, rc 0, 11 layers, #55 [234,255,0], no cruft, no artifact, no console errors.
- **2nd-pass status:** ADJUST 8/8 · MASK 7/7 · TRANSFORM 2/2 · SELECT 5/6 (Zone Pick deferred) · PRIMARY most ✅. Remaining:
  PRIMARY **Move** (drag) + **Lasso** (poly-click) [non-destructive], then the PIXEL-MODIFY group (**Gradient, Brush,
  Eraser, Fill, Text, Shape** — undo via Ctrl+Z, watch corruption per #11/#19), + SELECT **Zone Pick** (needs a spec pattern).

## Run #32 — 2026-05-29 — 2nd pass: Lasso ✅ + Move inconclusive + a composite-RENDER-degradation scare (no data loss)

- **Lasso ✅ re-verified** — polygon-click (2 clicks + double-click to close) → triangle selection **62,106 px** (≈ geometric
  0.5·400·300 = 60,000), bounds (890,891)-(1292,1202) matching the vertices (900,900)/(1300,900)/(1100,1200). Matches run #9.
- **Move — INCONCLUSIVE (2nd pass):** in layer-move mode with psd_2 selected + editable, a real drag did NOT move the layer
  (bbox stayed [406,355,1295,2003]), even starting on psd_2's opaque #55 content. Selection drags (rect/lasso/spatial) DID
  work this session → the failure is layer-move-SPECIFIC (its drag-state isn't driven by left_click_drag the way selection
  drags are). No move-by-delta engine exposed on window (moveLayerBy/translateLayer/nudgeLayer/moveSelectedLayer/
  setLayerPosition/nudgeActiveLayer/moveActiveLayerBy all undefined) → no engine fallback. Move stays ✅ from run #10 (real
  drag verified bbox change); re-verify with a human drag in the focused session.
- ⚠️ **RENDER-DEGRADATION SCARE (no data loss):** during the Move-test sequence (editMode zone→layer→zone + the failed
  layer-move drag), the live COMPOSITE render degraded — px(1024,1024) canary yellow→**BLACK**, whole-canvas yellow dropped
  205,926→85,773. Verified NOT data corruption: screenshot showed the car fully intact, psd_2.bbox unchanged, 11 layers.
  `recompositeFromLayers()` did NOT restore it (still degraded); a **page reload FULLY restored** the pristine composite
  (canary [234,255,0], yellow 205,926, 11 layers, bbox intact). So the layer DATA was always safe — only the in-memory
  composite RENDER had degraded. 🔑 **FLAG for investigation: the editMode-switch / failed-layer-move sequence can leave the
  composite render incomplete (reload-recoverable).**
- 🔑 **Implication for the PIXEL-MODIFY group:** if a NON-pixel tool (Move — which didn't even move anything) can degrade
  the composite render, the pixel-modify tools (Gradient/Brush/Eraser/Fill/Text/Shape) are even riskier to test
  autonomously. **Strongly prefer a focused session** (owner present, reload-on-hand) for that group + Move + Zone Pick.
- **Cleanup:** reload → clean (canary yellow, 11 layers, no cruft, eyedropper, no console errors). No data loss, no artifact.

## Run #33 — 2026-05-29 — 🎯 THROWAWAY-LAYER method unblocks the pixel-modify group; Gradient ✅ + Fill ✅

- **The method (psd_2-safe paint testing):** `addBlankLayer()` (→ a new blank layer, auto-selected, bbox [0,0,2048,2048],
  id `blank_*`) → run the paint ENGINE with that layer as the target → verify the throwaway's OWN pixels (draw layer.img to
  a 1×1 canvas + getImageData) → `deleteLayer(throwawayId)` (wrap `window.confirm=()=>true` in case it prompts) → back to
  11 layers, psd_2 NEVER touched. Clean each time, **no render degradation** (confirming run #32's degradation was the
  Move/editMode-switch sequence, not layer-paint).
- **Gradient ✅** — `fillGradientOnLayer(500,500,1500,1500,'linear', throwaway)` → throwaway pixels blank [0,0,0,0] →
  gradient **229→127→25** (light-to-dark). Engine sound. Matches run #11.
- **Fill ✅** — `fillBucketOnLayer(1024,1024, throwaway)` → flood-filled the all-transparent throwaway uniformly with the
  FG (white [255,255,255,255]). Engine sound. Matches run #11. **⏸→✅: the run #11/#17 "Fill broken/suspect" verdict is
  RESOLVED** — the engine works; the earlier click-path failures were the stale-rect + float confounds.
- 🔑 **This RESOLVES the "pixel-modify group needs a focused session" worry** (runs #29-32). Brush, Eraser, Text, Shape are
  now safely re-verifiable via the throwaway method (paint on a throwaway, never psd_2; deleteLayer to clean up).
- **Cleanup:** both throwaways deleted, 11 layers, psd_2 [406,355,1295,2003], canary [234,255,0], no cruft, no console
  errors, no artifact. psd_2 was NEVER the paint target.
- **NEXT:** Brush, Eraser, Text, Shape via throwaway; then Move (real drag — focused) + SELECT Zone Pick (spec pattern).

## Run #34 — 2026-05-29 — Brush/paint-strokes NOT autonomously action-testable (hard limit); corrects run #33

- Owner granted render + free mess-around (Restore All as the safety net). Tested **Brush** three ways — all blocked for the paint ACTION:
  1. **Throwaway blank layer + drag** → no paint (brush mousedown didn't engage: isDrawing false, _activeLayerCanvas null).
  2. **psd_2 (real layer) + drag** → the drag MOVED the layer (undo "move layer", bbox 406→653) = the run #19 drag-on-content-moves confound. Restored via **bbox-reset** (a move is bbox-only; img intact) → yellow 205,926.
  3. **Brush engine direct** (`_initLayerPaintCanvas()`+`_paintOnLayerAt(x,y)`+`_commitLayerPaint()`) → `_paintOnLayerAt` threw `createRadialGradient … non-finite` (called bare it's missing the live stroke state — brush radius/last-point — the mousedown sets up).
- 🔑 **Brush/Eraser/Text/Shape paint strokes CANNOT be driven by the synthetic computer mouse.** A drag moves the layer (content) or no-ops (empty); the engine throws when called bare. They need a REAL human drag → verified in practice by the owner's daily use. **Corrects run #33's optimism:** the throwaway method covers Gradient/Fill (engines take a `layerOverride` + paint directly) but NOT the brush family (no layerOverride engine; the stroke needs live mousedown state).
- ⚠️ Re-confirmed **Restore All ≠ layer recovery** (zones only). Layer recovery: transform → undo entry's `imgCanvas` (prev turn); move → bbox-reset (this turn).
- **Cleanup:** psd_2 fully restored (yellow 205,926, px1024 [234,255,0], bbox [406,355,1295,2003]), 11 layers, no cruft, no console errors, **NO data loss** (psd_2 was briefly moved during testing, then restored).
- 🏁 **Autonomous 2nd pass is COMPLETE for everything testable without a real human paint-stroke.** Un-action-tested (need owner's hands): **Brush, Eraser, Text, Shape**; **Move** (real drag); **Zone Pick** (spec pattern). **RECOMMENDATION:** a brief owner hands-on of the paint strokes (drag brush/eraser, type text, draw a shape) closes the suite — everything else is ✅.

## Run #35 — 2026-05-29 — Zone Pick not autonomously testable → autonomous QA loop COMPLETE

- **Zone Pick setup blocked from page scope:** `PATTERNS`/`SPEC_PATTERNS` arrays + the spec-assign functions (setZoneSpecMap,
  applySpecOverlay, setZoneSpecPattern, …) are NOT on `window` (module-scoped). `setZonePattern(zoneIndex,id)` IS on window
  but needs a valid pattern id + a render to produce pickable content. So Zone Pick can't be set up/driven autonomously
  (confirms run #16). It needs manual UI setup (assign a spec pattern + render, then click a sub-piece).
- 🏁 **The autonomous 2nd pass is COMPLETE** — every tool drivable by a JS handler + synthetic mouse has been tested &
  re-verified. Remaining un-action-tested (require a human/manual step): **Brush, Eraser, Text, Shape** (paint strokes) +
  **Zone Pick** (spec pattern + render).
- No changes this fire (read-only); state clean (psd_2 #55 intact, 11 layers, no cruft, no console errors).
- **FINAL TALLY:** ADJUST 8/8 ✅ · MASK 7/7 ✅ · TRANSFORM 2/2 ✅ · SELECT 5/6 ✅ (Zone Pick deferred) · PRIMARY:
  Rect/Pick Item/Pen/Lasso/Wand/eyedropper/Transform-layer/Gradient/Fill/Brush(#17)/Move ✅; Eraser/Text/Shape = the
  paint-stroke family (human-drag only). Bugs found & FIXED: Color Brush `_t0` crash (#3), pan-exemption list (#26).
  Owner-requested ships: zoom re-center fix, layers-panel trim. **RECOMMENDATION: pause the loop + ~2-min owner hands-on**
  to close the 5 human-only tools.

## Run #36 — 2026-05-29 — Investigated the brush-paint-vs-move question (read-only); loop remains COMPLETE

- Re: the open question "does a brush drag over content paint or move?" — investigated the source (can't do a real drag).
  In Layer mode over the active layer, the app runs **element detection** (canvas.js:2267): hover → preview, click →
  isolate (Pick Layer Element), drag → move. There's also a transform-handle drag-move (`layerSubRectDragActive`, ~12409)
  but that needs an active `freeTransformState`. The run #34 brush-mode drag within psd_2's bbox produced a "move layer"
  undo, so the Layer-mode element/auto-select-move machinery intercepts a brush drag over content. The EXACT brush-mode
  trigger isn't fully traced (the obvious move paths require an active transform; run #34's path is the auto-select-move).
- 🔑 **Can't confirm from source alone** whether this blocks a REAL user's painting-on-content (vs. just the synthetic
  `left_click_drag`). **The owner's 5-second test settles it:** Layer mode → select a layer → Brush → drag over existing
  artwork. PAINTS = fine (synthetic-drag artifact). MOVES the layer = real bug (can't paint over existing content) → focused fix.
- No changes this fire (read-only); state clean (psd_2 #55 [234,255,0], 11 layers, no cruft, server 200).
- 🏁 Loop remains COMPLETE (run #35). Recommend pausing + the owner hands-on.

## Run #37 — 2026-05-29 — Owner EXPANDED the mandate (away 6h); verified base-in-numbers + shipped a Color Replace improvement

**Owner direct message (away 6h):** keep exercising the app; verify layers/zones work in harmony; CRITICAL — make sure we can pick a base picture and apply it to a car area / tile inside the numbers / apply a base color inside the numbers that replaces ONLY the yellow inside the numbers; improve the tools; if out of work, build REAL new features. (Recorded at top of TOOL_QA_PROGRESS.md so every fire continues it.)

**✅ VERIFIED — "replace ONLY the yellow inside the numbers" (owner-named).** Mechanism = `selectPSDLayer('psd_2')` (Numbers layer) → `autoColorReplace('#eaff00', newColor, tol)`. Evidence (pixel-level, self-restoring cycle):
- Composite yellow 198,799 → 70,540 = **128,259 px of the numbers' yellow replaced**; `(1024,1024)` `[234,255,0]`→exact `[255,0,153]`.
- **Every non-yellow reference point unchanged** — body `[83,71,65]`, black `[0,0,0]`, cyan `[0,211,243]`. So it replaces ONLY the matched yellow.
- Restore **pixel-exact** (→198,799, `(1024,1024)`→`[234,255,0]`) via `recompositeFromLayers` from my own backup canvas of `psd_2.img`. Final state clean.

**✅ LAYER/ZONE HARMONY.** Per-layer yellow scan: Numbers 136,688 (in-layer) · Car Paint 45,325 · Sponsors 36,854 · Tape 22,563 · others 0. Layers composite with correct occlusion; replacing on one layer scopes to that layer (the Car-Paint/Sponsors/Tape yellow was left alone — exactly the owner's intent); `recompositeFromLayers` is lossless.

**KEY PRECONDITION (also corrects an Explore-agent claim).** `autoColorReplace` is NOT global — it runs on `_getAdjustmentTarget('color replace')` = the SELECTED layer, or the composite `paintCanvas` if no layer is selected (canvas.js:17648). My first bare call no-op'd visually because the selected layer was psd_10 (no yellow). **To replace all yellow everywhere → deselect layers. To replace only the numbers' yellow → select the Numbers layer.**

**🔧 IMPROVEMENT SHIPPED — Color Replace no-match feedback** (canvas.js `autoColorReplace`; sync'd 6/6; cache-buster `spb-colorreplace-feedback-20260529`; reload confirmed `hasNewCode:true`). Before: a 0-match replace still ran `_commitAdjustment` (layer img swap + recomposite + preview render), left a dangling undo entry, and toasted a bare "Replaced 0 pixels". After: short-circuits — skips the needless commit/render, pops the no-op undo `_getAdjustmentTarget` pushed, and toasts actionable guidance. **Verified PASS:** composite unchanged (198,799=198,799), undo neutral (0=0), warn toast = *"…no pixels near #eaff00 found on layer \"Color Change Logos\" — that color may be on another layer or the base; deselect the layer to replace across the whole car"*, no console errors. In-source audit comment dated.

**NEXT (priority-1 remainder):** the OTHER half of the owner's #1 — pick a base PICTURE, apply to a region, and confirm it TILES correctly inside the numbers. Path: zone base (`setZoneBase`/`setZoneBaseColorSource` + `zone.regionMask` hard_mask) + engine tiling (`_transform_base_color_source`/`_tile_fractional`). Likely needs the engine/preview-render path to observe tiling, not just canvas-state reads.

## Run #38 — 2026-05-29 — Deploy boundary mapped + base-picture region+tiling EMPIRICALLY VERIFIED (engine) + wiring confirmed → owner's #1 substantially verified

**🔒 DEPLOY BOUNDARY (essential session-wide safety).** Three render entry points:
- `triggerPreviewRender()` (canvas.js:7398) — renders ONLY into the in-app `livePreviewImg`/`livePreviewSpecImg` panes via a debounced zone-config-hash check. **No iRacing deploy → SAFE to call.**
- `doRender()` (api-render.js:2845) — full render; builds server zones, honors a `liveLink`/auto-deploy path. **Avoid (the HARD-RULE "render").**
- `deployToIracing()` (api-render.js:4018) — explicit `POST /deploy-to-iracing` with `lastRenderedJobId`. **Never call.**

**✅ ENGINE — base picture applied to a region + tiling (EMPIRICALLY verified on real engine code, synthetic inputs, NO deploy; subagent wrote+ran+deleted a temp test).**
- HARD MASK (region confinement): `_apply_base_color_override` blend `paint[:,:,:3] = paint*(1-w) + src*w`, `w=(hard_mask*strength)` (compose.py:1820-1822). Test: 64×64 paint + 20×16 rect mask → EXACTLY 320 px changed (= rect area), inside = solid color exact, outside **byte-for-byte unchanged**, ZERO leakage; partial strength 0.5 = correct 50/50 blend.
- TILING: `_transform_base_color_source` (compose.py:893-931) routes `use_scale<1.0` per-channel to `_tile_fractional` (core.py:1313-1331) = `np.tile(arr,(reps,reps))` (reps 2-10) → crop → resize. Test: 4×4 source (bright px at 0,0) tiled ×4 → bright px at EXACTLY the period-4 grid {0,4,8,12}²; 2×2 checker ×8 → repeats every 2px. Genuinely tiled, not stretched. (`engine.compose` imports standalone; solid mode + `_tile_fractional` need no BASE_REGISTRY/disk assets.)

**✅ JS→ENGINE WIRING confirmed** (`buildServerZonesForRender` api-render.js:2484 — the shared preview+render zone-payload builder): sends `zoneObj.base` (2501), base color/picture source via `_applyBaseColorMode` (2538), `base_scale`/`base_strength` (2533-2534), and the **region mask RLE** via `encodeRegionMaskRLE` (2556+); the zone filter (2485) includes region-masked zones. So the app feeds base+region to the verified engine.

**🏁 OWNER'S #1 PRIORITY — SUBSTANTIALLY VERIFIED.** (a) base color/picture applied to a region → wired + engine confines to region (zero leakage); (b) tiles inside numbers → engine tiles period-exact; (c) base color inside numbers replacing ONLY the yellow → `autoColorReplace` on the Numbers layer (run #37). **Caveat:** verified engine LOGIC (empirical, synthetic inputs) + WIRING (code read), but did NOT run a full LIVE render of an actual base-picture-in-numbers (deploy risk; owner renders daily). A ~30-sec owner live-render confirms the visual end-to-end. No live-app changes this fire (all reads + an isolated subagent test that cleaned up after itself).

## Run #39 — 2026-05-29 — Layer/zone harmony stress: compositor honors visibility+opacity, recomposite is IDEMPOTENT (run #32 scare resolved)

**✅ Compositor honors per-layer dynamic properties** (toggled psd_2 "Numbers" flags directly + `recompositeFromLayers`, then restored):
- VISIBILITY: `visible=false` → composite yellow 198,799 → 76,164 (numbers' ~122k yellow removed), `(1024,1024)` `[234,255,0]`→`[0,0,0]` (under-layer shows through). `visible=true` → restored. ✓
- OPACITY: `opacity≈40%` → yellow → 74,264, `(1024,1024)` → `[94,102,0]` (= 0.4×`[234,255,0]` over black). Restored. ✓
- Cross-check: hidden-numbers yellow (76,164) ≈ run #37's "70,540 yellow on the OTHER layers" (Car Paint/Sponsors/Tape) — consistent; reconfirms the multi-layer-yellow finding.

**✅ `recompositeFromLayers` is IDEMPOTENT — no accumulating degradation.** Ran it 6× consecutively: yellow held at EXACTLY 198,802 each time (zero drift). This **resolves the run #32 "render-degradation scare"** — repeated layer ops / recomposites do NOT rot the composite.

**📋 Benign one-time AA offset (NOT a bug).** Initial-load composite (198,799) vs recomposited composite (198,802) differ by **3 px** (0.0015%, sub-visible) at yellow/non-yellow AA edges — a one-time, NON-accumulating rounding difference between the two composite code paths. Reload restores 198,799. Documented so future fires don't mistake 198,802 for corruption.

**State left pristine:** reloaded → yellow 198,799, `(1024,1024)`=`[234,255,0]`, clean defaults (eyedropper/zone, no layer selected), 11 layers, no console errors.

**Queued feature (grounded, for a dedicated fire):** the yellow is split across 4 layers, so Color Replace (hits one layer, or the composite) can't recolor "a whole team color across the car" in one shot. A **"Replace color across ALL layers"** scope option would directly serve livery recoloring: `autoColorReplaceAllLayers(target,replacement,tol)` (iterate unlocked layers, reuse the replace loop, recomposite once) + a scope toggle on the Color Replace dialog.

## Run #40 — 2026-05-29 — SHIPPED a real new feature: "Replace color across ALL layers"

**Owner mandate:** "create REAL features… useful SPECIFICALLY for people using this app." **Grounded in run #37/#39:** the car's team color is split across layers (yellow on 6 layers), so single-layer Color Replace can't recolor a whole team color in one action. Built + shipped the all-layers variant.

**What shipped (all in canvas.js, root → sync 6/6 → cache-buster `spb-replace-all-layers-20260529`):**
- `autoColorReplaceAllLayers(targetHex, replacementHex, tolerance)` (window-exported, placed after `autoColorReplace`) — iterates every UNLOCKED layer with an img, reuses autoColorReplace's exact color-distance match+blend, swaps each affected layer's img, recomposites once, pushes one undo entry per affected layer, toasts "Replaced N px across M layers" (notes locked-layer skips). No-match → warn toast. Canvas + recomposite only (NO render/deploy — uses the safe `triggerPreviewRender`). Falls back to single-target `autoColorReplace` if no layers loaded.
- UI: added an optional **"Replace across ALL layers"** checkbox to the Color Replace dialog — implemented as an opt-in `config.allLayersToggle` flag on the shared `_openAdjustmentColorDialog` (gated, so other callers like Gradient Map are unaffected); payload carries `allLayers`; `openColorReplaceDialog` routes to the all-layers fn when ticked.

**Verified LIVE (PASS):** reload → `autoColorReplaceAllLayers` present + source has new code; dialog checkbox renders + closes cleanly. Functional test (backed up all 11 layers → ran → restored): composite yellow 198,799 → **0** (all yellow recolored across 6 layers; **255,459 px** total — exceeds the composite's 198,799 because of occluded/overlapping yellow across layers, which is exactly the point of "all layers"); `(1024,1024)` → exact `[255,0,153]`; body/cyan untouched; restore **pixel-exact** (→198,799, `[234,255,0]`); 6 undo entries (tidied in test); **no console errors**. Reloaded → pristine (yellow 198,799, clean defaults; feature persists in the synced build).

**Audit:** dated in-source comments on all edits; 3-copy synced; no git ops. **NEXT:** more tool polish / another feature, or owner hands-on for the human-only paint-stroke family.

## Run #41 — 2026-05-29 — Polished the all-layers feature: single GROUPED undo (one Ctrl+Z reverts every layer)

**Rough edge in run #40's feature:** it pushed one undo entry PER affected layer (e.g. 6 undos to revert one "Replace across all layers" action) — surprising for a single user action.

**Fix (canvas.js `autoColorReplaceAllLayers`; cache-buster `spb-allreplace-grouped-undo-20260529`; sync 4/4):** switched to the app's existing multi-layer undo convention — push ONE `_pushLayerStackUndo('color replace (all layers)')` (a `type:'stack'` snapshot of the whole layer stack, retaining old img refs since we swap `layer.img` rather than mutate it) BEFORE the loop instead of a per-layer `_pushLayerUndo`; pop it if nothing matched (keeps the stack clean on no-op).

**Verified LIVE (PASS):** reload → source has the new code. Functional test (id-keyed backups as safety net): composite yellow 198,799 → **0** (feature still works); `_layerUndoStack` gained **exactly 1** entry (was 6), `type==='stack'`, label "color replace (all layers)"; applying ONE undo (`_restoreLayerStack(snapshot)`, the same path Ctrl+Z uses for stack entries) restored yellow → 198,802 (= the benign +3 recomposite value, within ±5 tolerance) — i.e. one undo reverted ALL layers. No console errors, no backup fallback needed. Reloaded → pristine (198,799, clean defaults).

The "Replace across ALL layers" feature is now production-quality (one action = one undo). **NEXT:** more polish / another grounded feature, or owner hands-on for the human-only paint-stroke family.

## Run #42 — 2026-05-29 — All-layers feature fully hardened: locked-skip + no-match branches verified LIVE

Completed branch coverage of the "Replace across ALL layers" feature (runs #40 happy-path, #41 grouped-undo). Both edge guards now verified live (id-keyed backups as safety net; pristine after):

**✅ Locked-layer skip (PASS).** Locked the Numbers layer (psd_2) → ran all-layers replace yellow→pink:
- psd_2's yellow PRESERVED (in-layer 136,688 → 136,688, untouched — the lock was honored).
- Other layers replaced: composite yellow 198,799 → 128,259 (= the Numbers' visible yellow remaining; the 5 unlocked layers' yellow gone).
- Toast: "Replaced 116,898 px across 5 layers … **(1 locked skipped)**". Still ONE grouped undo (undoDelta 1). Restored exact (198,799).
- Cross-check: 255,459 (all 6 layers, run #40) − 116,898 (5 layers now) = 138,561 ≈ psd_2's 136,688 in-layer yellow. ✓

**✅ No-match (PASS).** Ran all-layers replace with an absent color (#ff00ff, tol 8): composite UNCHANGED (198,799), **undoDelta 0** (the grouped 'stack' undo was pushed then correctly POPPED — stack stays clean, verifying the run #41 no-match-pop path), warn toast "no pixels near #ff00ff found on any unlocked layer".

**The "Replace across ALL layers" feature is now COMPREHENSIVELY verified** across all branches (happy path, grouped undo, locked-skip, no-match). No live-app changes persisted (tests self-restored; reloaded → pristine 198,799, no locked layers, undo 0). **NEXT:** another grounded feature / polish, or owner hands-on for the human-only paint-stroke family.

## Run #43 — 2026-05-29 — RETOUCH menu definitively classified: all 8 tools activate + are healthy drag-brushes (no bugs)

Closed the RETOUCH menu's QA (previously ⬜ untested, *assumed* human-drag — now confirmed via activation test + source).

**✅ Activation (all 8 PASS):** `setCanvasMode` → correct mode for Clone, Recolor, Smudge, Pencil, Dodge, Burn, Blur Brush, Sharpen Brush (each `ok:true`, no console errors).

**Source classification (canvas.js):** every RETOUCH tool paints via `&& isDrawing` strokes — Clone 2540, Recolor 2591, Smudge 2609, Pencil 2643, Dodge/Burn 2660 (→ `paintDodge`/`paintBurn`), Blur/Sharpen 2678 (→ `paintBlurBrush`/`paintSharpenBrush`); mousedown starts the stroke (3256-3397), mouseup commits the layer stroke (3771); all Layer-Mode-gated (`_maybeToastLayerPaintFallback`). So they're DRAG-BRUSHES — same family as Brush/Eraser: the paint-action needs a real human drag (synthetic drag doesn't engage the `isDrawing` stroke machine / moves the layer), but the tools are healthy + correctly wired. **No bugs found.**

**RETOUCH menu status:** activation ✅ 8/8; paint-action = human-drag (deferred to owner hands-on, like Brush/Eraser/Text/Shape). No changes made (read-only + mode cycling; ended on eyedropper; px(1024,1024)=[234,255,0]; no console errors).

**Tool-QA coverage now comprehensively classified:** ADJUST 8/8 ✅, MASK 7/7 ✅, TRANSFORM 2/2 ✅, SELECT 5/6 ✅ (Zone Pick needs a spec pattern), RETOUCH 8/8 activate ✅ (paint = human-drag), PRIMARY mostly ✅ (paint-stroke family = human-drag). Plus shipped this window: Color Replace no-match feedback (improvement) + Replace-across-ALL-layers (new feature, fully verified). **NEXT:** owner hands-on for the human-drag paint family + Zone Pick; otherwise more grounded polish/features.

## Run #44 — 2026-05-29 — 2nd-pass re-verification (all fixes HOLD) + completed the pan-exemption list

**2nd pass (cron-mandated) — every BROKEN/FIXED/shipped item HOLDS in the current build, no regressions:**
- 🔑 REGRESSION CHECK (my run #40 shared-dialog edit): the Gradient Map dialog (another `_openAdjustmentColorDialog` caller) renders WITHOUT the all-layers checkbox (`hasCheckbox:false`), shows its 2 color fields, closes cleanly → my opt-in `config.allLayersToggle` gating is correctly isolated, no leak into other callers. ✅
- Color Replace dialog still shows the all-layers checkbox (run #40) ✅; Color Brush activates with no `_t0` crash (run #3) ✅; `autoColorReplace` / `autoColorReplaceAllLayers` / `openGradientMapDialog` all present ✅.
- Source intact: zoom re-center (canvas.js:8703-8725, margin-aware anchor + auto-recenter) ✅; pan-exemption list (8906) ✅. No console errors.

**🔧 Completed the pan-exemption list (closes the run #26-flagged gap):** added the 10 VERIFIED drag-paint modes — colorbrush, recolor, smudge, pencil, dodge, burn, blur-brush, sharpen-brush, clone, history-brush (confirmed drag-paint by run #43 activation + the mouseup layer-stroke-commit list at canvas.js:3771) — to `drawToolActive` (8906). Without this, a zoomed-in left-drag with any RETOUCH/paint brush was hijacked into a SOURCE PAN instead of painting. **Purely additive** (only exempts more modes from pan → cannot affect non-drag modes; pan stays via space+drag/middle/right-click). cache-buster `spb-pan-exempt-paintbrushes-20260529`, sync 4/4, reload → served build confirmed to contain the expanded list (`hasExpandedList:true`). Left **'shape'/'text' PARKED** (not in the paint-stroke commit list — verify their drag-vs-click-to-place behavior before exempting, else drag-to-pan might be lost). The fix is code-verified + additive/safe; the FUNCTIONAL effect (zoomed-in drag) is a human-drag scenario, so it rides on the owner's paint-tool hands-on.

No live-app changes persisted (read-only 2nd-pass + one code edit; reloaded → #55 [234,255,0], clean defaults). **NEXT:** owner hands-on for the human-drag paint family + Zone Pick; verify shape/text drag-behavior; else more grounded polish.

## Run #45 — 2026-05-29 — Resolved the parked shape/text pan-exemption; list now COMPLETE

Finished the run #26/#44 pan-exemption thread by verifying the two parked modes in source:
- **'shape' = DRAG tool** → mousedown sets `_shapeStart`+`isDrawing` (3252), drag previews the shape (2530), mouseup commits (3740); crosshair cursor. A zoomed-in drag should DRAW the shape, not pan → **ADDED to `drawToolActive` (8911).**
- **'text' = CLICK-to-place** → mousedown calls `onTextToolClick(x,y)` (3248); no `isDrawing`/drag path; text cursor. A drag is NOT a text action, so drag-to-pan is still wanted → **deliberately EXCLUDED.**

Verified LIVE: cache-buster `spb-pan-exempt-shape-20260529`, sync 4/4, reload → served build has `'shape'` in the list (`shapeInList:true`) and `'text'` correctly absent (`textExcluded:true`). Additive/safe (same posture as run #44; the functional zoomed-drag is human-testable). #55 [234,255,0], clean defaults.

**The pan-exemption list is now COMPLETE** — every drag-draw/paint tool (selection marquees, spatial masks, gradient, the full brush/RETOUCH family, shape) is exempt from zoomed-in pan-hijack; click-to-place text correctly retains drag-to-pan. **Closes the run #26 flag.** **NEXT:** owner hands-on for the human-drag paint family + Zone Pick; else more grounded polish/features.

## Run #46 — 2026-05-29 — Backlog triage: "undo stack unbounded" is STALE — all 3 undo stacks ARE bounded

Worked the MEMORY.md improvement backlog. Investigated "Undo stack unbounded (memory risk)":
- `undoStack` (zone-mask undo; pushUndo/pushZoneMaskUndoSnapshotForRedo, canvas.js:4952-4990) — bounded: `const MAX_UNDO = 30` (paint-booth-2-state-zones.js:266, a cross-file global alongside `const undoStack = []` at :264); `undoStack.shift()` when `> MAX_UNDO` (4971/4989). MAX_UNDO is referenced-not-defined *in canvas.js* (initial scare) but IS defined in state-zones.js → the cap works.
- `_pixelUndoStack` (pixel/paint-stroke undo; pushPixelUndo, canvas.js:4993-5004) — bounded: `_PIXEL_UNDO_MAX = 10`, shift at 5002.
- `_layerUndoStack` (layer ops) — bounded: `_LAYER_UNDO_MAX = 8` (19005/19022).

**Verdict: the backlog item is STALE — no unbounded growth, no fix needed.** Marked resolved in MEMORY.md.

**Observation (not a bug):** `undoStack` entries hold up to two 2048² masks (`prevMask`+`prevSpatial` ≈ 4 MB each); 30-deep worst case ≈ 240 MB IF every zone carries both full masks (typical is far less — masks are null until used). Bounded + fine for normal use; an RLE-compressed undo entry (the app already has `encodeRegionMaskRLE`) would slash the worst case but changes the undo format → owner-decision optimization, not an overnight change. No live-app changes (read-only investigation). **NEXT:** owner hands-on (paint family + Zone Pick); remaining backlog items are perf-refactors (renderZones DOM rebuild, O(n) finish lookup) better suited to owner-reviewed changes than risky overnight edits — will pick safe items / more verification.

## Run #47 — 2026-05-29 — Shipped a global uncaught-error handler (closes "script error handling missing" — a REAL gap)

Backlog item "Script error handling in HTML missing" = **CONFIRMED REAL** (unlike the undo item): `window.onerror` + `window.onunhandledrejection` both null; grep found only LOCAL img/reader `.onerror` handlers, NO global `addEventListener('error'|'unhandledrejection')`. So uncaught errors + unhandled promise rejections (the app has many async fetch/render ops) failed SILENTLY — including failures inside the tools (a tool could throw and the user would see nothing).

**Fix (paint-booth-v2.html, first `<script>` in `<head>`; sync 2/2):** a global handler that (1) logs with a `[SPB uncaught <kind>]` marker, (2) records to a capped `window._spbUncaughtErrors` (≤50, for inspection/QA), (3) surfaces a THROTTLED toast (≤1 per 15 s, only on real uncaught errors) so failures are NOTICED without spam. **Purely additive** — the listeners only fire on errors that were ALREADY going uncaught, so they can't change any working path; the whole handler is wrapped so it can never throw. (No cache-buster needed — the served HTML re-fetches on reload; verified.)

**Verified LIVE (PASS):** reload → `window._spbUncaughtErrors` exists (handler installed) and **before=0 on a clean boot** (the app loads with NO uncaught errors → confirms no spurious firing). Fired a synthetic uncaught error + an unhandled rejection → BOTH caught + recorded (`caughtError:true`, `caughtReject:true`); entry shape `{kind,msg,where}`. Test entries cleaned up (record → 0). #55 [234,255,0], clean defaults. (Console retains 4 clearly-marked `SPB-TEST` entries from the verification — cleared on next reload.)

Owner follow-ups (optional): tune the toast wording/severity (a UX choice); and **a future QA fire can read `window._spbUncaughtErrors` to catch silent tool failures**. **NEXT:** owner hands-on (paint family + Zone Pick); remaining backlog = perf-refactors (owner-review).

## Run #48 — 2026-05-29 — Silent-error sweep (via the run #47 handler): all 28 tool modes activate clean; + a testing-method lesson

Used the run #47 global error handler for a NEW check: do any tool activations trigger SILENT (async) errors that my earlier sync-only tests would have missed?

**✅ Result: all 28 tool modes activate FAST + ERROR-FREE.** A *synchronous* cycle of every mode (wand/selectall/edge/rect/ellipse-marquee/lasso/spatial-include/-exclude/-erase/brush/erase/colorbrush/recolor/smudge/pencil/dodge/burn/blur-brush/sharpen-brush/clone/history-brush/gradient/fill/shape/text/zone-pick/move/eyedropper) ran in **26.5 ms total** (~0.9 ms each), **0 sync throws, 0 recorded errors** (incl. a 250 ms async-settle check). Individually timed spatial-exclude/spatial-erase/wand/etc. = 0.1–0.8 ms. The toolset's activation paths are clean.

**⚠️ TESTING-METHOD LESSON (important for future fires):** the FIRST attempt used ONE async eval cycling 28 modes with `await sleep(20)` between each. The Claude-in-Chrome tab is BACKGROUNDED, so the browser THROTTLES `setTimeout` to ~1 s minimum → the 28 sleeps became a ~30 s+ crawl → the CDP eval timed out at 45 s AND left the async function running as a RUNAWAY background process (observed the mode self-advancing across checks: spatial-exclude → recolor → smudge). **Do NOT use long `await sleep` loops in javascript_tool evals — background-tab timer throttling makes them crawl, time out, and orphan a runaway function. Use synchronous operations, or a single short await.** Recovered cleanly by reloading (destroys the orphaned context).

**App health throughout:** never corrupted — responsive, 0 recorded errors, #55 [234,255,0], 11 layers the entire time. Post-reload: pristine + STABLE (mode held `eyedropper` over 1.2 s = no runaway), and the run #47 error handler re-installed (confirms it persists across reloads). **No app bug — the whole incident was a CDP-eval/throttling artifact.** **NEXT:** owner hands-on; safe verification / owner-reviewed perf items only.

## Run #49 — 2026-05-29 — Action-level silent-error sweep (selection/mask tools): all clean, no silent errors

Extended the silent-error coverage from activations (run #48) to tool ACTIONS, using the run #47 handler — and **avoiding the run #48 async-sleep pitfall** (synchronous ops + ONE short 250 ms await).

**✅ All drivable selection/mask ACTIONS run error-free:** `selectAllColor`, `invertRegionMask`, `smoothRegionMask`, `mirrorRegionMask`, `edgeDetectFill`, `copyMaskToZone(4)` — all returned ok (0 sync throws), and the error record showed **0 silent/async errors** after the settle. (Earlier per-tool tests verified these RESULTS; this adds async-error coverage via the new handler.)

**Cleanup verified clean:** `clearZoneRegions(0)` + `clearZoneRegions(4)` + `clearSel` → `hasActivePixelSelection()`=false, composite `(1024,1024)`=[234,255,0] unchanged (these ops touch the selection/mask overlay, not the paint), mode=eyedropper. No reload needed.

Silent-error coverage now spans tool ACTIVATIONS (run #48, all 28 modes) + drivable selection/mask ACTIONS (this fire) — all error-free with the run #47 handler as the net. **NEXT:** owner hands-on (paint-stroke family + Zone Pick); safe verification / owner-reviewed perf items only.

## Run #50 — 2026-05-29 — Health check (milestone): all shipped work intact, app healthy, error monitor clean

Light health-check (substantive autonomous work complete; owner back soon). Confirmed:
- App healthy: server 200, 11 layers, #55 [234,255,0], mode eyedropper / edit zone.
- Run #47 error handler INSTALLED + **accumulatedErrorCount = 0** (no silent errors since the last clear — the app's been error-free during idle).
- All shipped changes present in the served build: `autoColorReplaceAllLayers` (fn + source), pan-exemption `shape` (source), Color Replace no-match feedback (source), `autoColorReplace` (fn).

**Cumulative state of this 6-hour window (runs #37–#50) — all VERIFIED + intact:**
- **Owner's #1 priority:** replace-only-yellow-in-numbers (#37) + base-picture→region + tiling (engine empirical + wiring, #38) — VERIFIED.
- **Layer/zone harmony** + recomposite idempotency (#39) — VERIFIED; the run #32 degradation scare was disproven.
- **SHIPPED:** Color Replace no-match feedback (#37); **Replace-across-ALL-layers feature** (#40; hardened #41 grouped-undo, #42 locked-skip + no-match); pan-exemption completion for the brush family (#44) + shape (#45); **global uncaught-error handler** (#47).
- **2nd-pass** re-verification — all fixes hold (#44); **backlog triage** — undo stale (#46), error-handling fixed (#47); **silent-error sweeps** — activations (#48) + actions (#49) all clean.
- **RETOUCH menu classified** (#43): 8/8 activate, paint = human-drag.

**Still needs the OWNER (the only remaining items):** ~2-min hands-on for the paint-stroke family (Brush/Eraser/Text/Shape + RETOUCH brushes — drag each once) + assign a spec pattern for Zone Pick; plus the perf-refactor backlog (renderZones DOM rebuild, O(n) finish lookup) for owner-reviewed changes. **NEXT:** light health-monitoring only until owner returns.

## Run #55 — 2026-05-30 — Owner's 5 directed UI fixes SHIPPED + regression sweep (ZERO tool regressions)

The owner returned mid-loop and gave a verbatim 5-fix list (separate from the tool sweep). All shipped (3-copy synced, cache-busted, verified live); then this run regression-swept them against the tool suite.

**The 5 fixes (file : root cause / change):**
1. **HSB sliders dead + sticky in overlay layers 2-5** — `paint-booth-2-state-zones.js` (4 overlay HSB blocks). The slider `oninput` called `renderZones()` every tick → full zone-panel DOM rebuild mid-drag = the hang/stick, and the rebuild also dropped live updates. FIX: `oninput` now updates `zones[i].{second..fifth}Base{Hue|Sat|Brt}` + the inline label + `triggerPreviewRender()` only; `renderZones()` stays on the ± step buttons. Added a per-row ↺ reset button (sets the field to 0 + `renderZones()` + preview).
2. **Base dropdown "Solid & Gradients" + SHOKK-DROP placement** — removed the two "Solid & Gradients" catch-all blocks (state-zones.js ~4726 zone picker + ~12363 library) that swept ungrouped groups into a junk section; prepended `"SHOKK DROP"` to `SPECIALS_SECTIONS['SHOKKER']` in `paint-booth-0-finish-data.js` (3-copy data file) so imported finishes sit atop the SHOKKER group above PARADIGM.
3. **Spec-preview hover glitch** — `paint-booth-v2.css` `.spec-channel-dock-canvas`: the hover pop-out animated width/height/transform → janky reflow. Changed `transition` to `box-shadow` only; the position/size now snaps cleanly.
4. **Spec Overlay Patterns picker — dev labels + split thumbnails (the big one).**
   - **Dev-label removal — CSS `display:none` FAILED a specificity war** (caught only by VISUAL verification, NOT by "is the rule in the served file"): `.spec-rank-row` computed `display:grid` because a later same-specificity rule at css:9336 won on source order, and the curation lanes were re-shown by `.spec-curation-lanes.spec-picker-popout-open` (css:9488/9509, higher specificity). LESSON: when hiding generated UI, neutralize at the SOURCE, don't fight `!important`/specificity. FIX (state-zones.js): `_renderSpecPatternRankChips`→`return ''` (per-tile Measured/Spec/Fit), `_ensureSpecCurationLanes`→remove existing + `return null` (curation-lane bar), `_updateSpecGroupHealthBadges`→early-`return` before the badge appends (Strong / N surgery / N rate + Feature-lane heading badges; the badge-CLEAR above it is kept).
   - **Split thumbnails:** spec patterns are SINGLE-CHANNEL (server `_generate_spec_preview_image` fakes M/R/CC from one field: M=field, R=field, CC=inverted), so the "combined spec map" = `RGB(v, v, 255-v)`. `_enhanceSpecPatternCardElement` now wraps the card's `spec-pattern-visual-preview` img into a `.spec-split-thumb` (left = the pattern), and adds a sibling img with the SAME src recolored to the combined map by an injected SVG `feColorMatrix` filter (`#specCombinedFilter`, rows `1 0 0 0 0 / 1 0 0 0 0 / -1 0 0 0 1 / 0 0 0 1 0`, sRGB). ONE cached image serves both halves → no second fetch, **no backend route, no Flask restart** (so no iRacing auto-deploy risk). The original img stays the FIRST `<img>` so the overlay-grid hover popups (`el.querySelector('img').src`) keep working; favorites `cloneNode(true)` inherits the split; a `dataset.splitThumb` guard prevents double-wrap. Verified through the REAL `_buildSpecPatternPickerCards` + `prepareInlineSpecPatternGrid` path: **200/200 cards split (400 imgs), 0 rank rows / 0 health / 0 plan / 0 lanes, 25 category headings, 0 errors.**
5. **Stray floating "recent colors" bar** — `paint-booth-3-canvas.js` `renderRecentColors`: now `display:none` + empties when `window.recentColors` is empty (removed the old "recent colors" placeholder span).

**Regression sweep (verification-only — no new source edits this run):** server 200, canary [234,255,0], 11 layers; **29/29 tool modes activate clean (0 throws), 0 new uncaught errors** (run #47 monitor); shipped features intact (`autoColorReplaceAllLayers`, split-thumb fns, `_renderSpecPatternRankChips`→`''`); `renderZones()` + `renderRecentColors()` run clean; recent-bar hidden-when-empty confirmed. **→ The 5 UI fixes caused no tool regressions.** Cache-busters: css `spb-uifix-fix4c-20260530`, state-zones.js `spb-uifix-fix4c2-20260530`.

⚠️ **Flagged for owner:** the spec picker's per-tile **category pill** duplicates the section heading right above it (pre-existing `::before`, not a dev label) — left as-is; offered to hide on request. **Unchanged from #50:** paint-stroke family + Zone Pick still need owner hands-on.

## Run #56 — 2026-05-30 — Owner's 3 directed fixes: advanced-tools popout + HSB deep-trace (works, no fix) + spec-tile resize/M-R-CC

**(1) Advanced Spec Overlay Tools popout** — `paint-booth-2-state-zones.js` spec-layer render (~1697-1735): wrapped the POS X/Y / SCALE / BOX / ROT grid + Manual Place in a native `<details class="spec-adv-tools">` (collapsed; summary "⚙ Advanced Spec Overlay Tools"). Zero JS, robust. Verified `details.open === false` by default with a real spec layer in zone 0.

**(2) 2nd-base HSB — deep diagnosis, concluded WORKING (no fix made).** Owner said HSB still doesn't apply; tested + traced the ENTIRE chain live:
- JS: `getZoneConfigHash()` includes `secondBaseHueShift` (canvas.js:7283) so the render isn't skipped; the payload at canvas.js:7783 sends `second_base_hue_shift` when `secondBaseStrength>0`. Captured the live `/preview-render` POST body → it contains `second_base_hue_shift:150`. Value reaches the server.
- Engine: `shokker_engine_v2.py:16074` always builds `_v6kw["second_base_hue_shift"]`; `_v6paint` (16245 stacked / 16292 single) copies the HSB keys in when the 2nd base is active; `compose_paint_mod[_stacked]` applies them (compose.py 4515-4531 / 5172-5185) to the overlay paint AND the post-blend paint (masked to overlay alpha). `_apply_hsb_adjustments` (compose.py 1276-1311) does a correct sRGB→HSV hue-rotate/sat/brightness.
- VISUAL test (red 2nd base on zone 0; hue 0 vs hue 160+brt 90+sat −90; `doPreviewRender(...,0.25)`; pixel-diff `livePreviewImg`): **"ENGINE APPLIES HSB"** — 38/2304 sampled px changed, maxd 152. Full slider→preview: **"SLIDER→PREVIEW WORKS"**. Slider perf: 31 drag events in 10ms (0.3ms each); `pushZoneUndo('',true)` coalesces (state-zones.js:418-423) → NOT sticky.
- **Conclusion:** works end-to-end in the current build → owner likely tested a STALE build (the tab was reloaded many times during the spec-tile work). Asked them to hard-reload + give an exact repro before any engine change. ⚠️ The first Explore sub-agent's "`>0.5` should be `>=0.5`" is a RED HERRING (owner uses hue=150, far past 0.5) — do NOT act on it.

**(3) Spec tiles too small + wrong combined-spec** — `paint-booth-v2.css` + `_applySpecCardSplitThumbnail` (state-zones.js). "Too small" root cause: my Fix-4-C `.spec-split-thumb` was `width:48px` inside 148px cards (`.spec-pattern-grid` = `minmax(148px,1fr)`; normal thumbs 148×92). Fixed → `.spec-split-thumb { display:flex; flex-direction:column; width:100% }`: pattern img on top (`height:92px`) + a `.spec-split-thumb-mrc` strip below (`aspect-ratio:3/1; object-fit:fill`) from the REAL `/api/spec-pattern-preview/<id>` (server [Metallic | Roughness | Clearcoat]) — replacing the synthetic `#specCombinedFilter` blue/yellow recolor the owner rejected ("not the actual way they look"). Owner chose "Pattern + real M/R/CC channels" via AskUserQuestion. Verified via real builder: 224/224 split, all MRC imgs (src `spec-pattern-preview`), thumbWidth 158 (was 48). `_ensureSpecCombinedFilterDef` is now unused (harmless dead code, left in place).

**Regression sweep:** server 200, canary [234,255,0], 11 layers; 29/29 modes activate (0 throws), 0 new errors; renderZones/renderRecentColors clean; dev-label removal still holds (rankRows 0, health 0); popout collapsed; M/R/CC split intact → no regressions. Cache-busters `spb-uifix-advtools-20260530` (issue 1) + `spb-uifix-spec3-20260530` (issue 3, css+js); all synced 3-copy.

**Still owner-pending:** confirm HSB after a hard-reload; paint-stroke family + Zone Pick hands-on.

## 2026-05-30 stress-loop iter 1 — LIVE-PREVIEW 500 + 2nd-base-overlay HSB both FIXED

**(A) Live-preview 500 (Cursor's fix — confirmed).** Saved zones referencing the removed `spec_heat_scale` spec pattern made the engine hard-raise → `/preview-render` 500 on EVERY preview (this is why the live preview "broke" AND HSB looked dead — nothing rendered). Fixed in engine/compose.py: `_get_spec_pattern_fn_or_raise` → `_get_spec_pattern_fn_or_skip` (skip+warn on unknown spec/pattern id; alias kept; 6 call sites). Verified: a `spec_heat_scale` zone now returns `/preview-render` 200, survives restart.

**(B) 2nd-base-overlay HSB (engine fix).** `engine/overlay.py:get_base_overlay_alpha` had an early return `if blend_mode in _PATTERN_REQUIRED_BLEND_MODES and pattern_mask is None: return np.zeros((H,W))` (~line 213). Pattern-reactive modes (`pattern`, `pattern_vivid`=Pattern-Pop=the DEFAULT for a new 2nd base, `pattern_edges`/`peaks`/`contour`/`screen`/`threshold`) with NO pattern present returned ZERO alpha → the overlay was invisible AND the post-blend HSB mask (`_hsb_mask = hard_mask * overlay_alpha`) became 0 → HSB had no effect ("solid red 2nd base, hue −130 does nothing"). TINT was unaffected (not pattern-required → full alpha → HSB works; control test `changed:78`). FIX: removed the zero-alpha early-return so pattern-modes-without-a-pattern fall through to the existing uniform `else: alpha = np.ones((H,W))` branch (then `× strength`) — a visible uniform color wash like Tint that HSB recolors; with a pattern present, each mode reacts exactly as before. Empirical: Pattern-Pop + solid red + hue −130 went `changed:0` → `changed:78, maxd:354` after the fix + server restart. Required restarting `server_v5.py` (no Python hot-reload) — killed PID 233900, `Start-Process` detached new PID 381444, up 200 in ~2s.

**Remaining (next stress-loop iters):** owner issue 1 (2nd base should DEFAULT to react-to-pattern-1; 3rd→pattern 1, or pattern 2 if present); issue 2 (a pattern at scale 0.25 + its base-overlay react-to at 0.25 should align/fit); verify HSB across ALL blend modes and the 3rd/4th/5th overlays; ~11.5s 50%-scale preview perf (owner budget 2-3s).

## 2026-05-30 stress-loop iter 2 — HSB across 2nd-5th confirmed + issue 1 (react-to-pattern default) FIXED

**HSB across all overlays:** the iter-1 `engine/overlay.py` fix (uniform fallback for pattern-reactive modes with no pattern) covers the 3rd and 5th base overlays too — Pattern-Pop + solid red + hue −130 recolors each (`changed:82`). Full 2nd-5th range confirmed (4th = identical code).

**Issue 1 (JS fix) — `paint-booth-2-state-zones.js:_defaultOverlayReactPattern` (~7741).** The function set the default "react-to" pattern for a newly-added base overlay, but it only handled `thirdBasePattern` / `fourthBasePattern` / `fifthBasePattern` — the **`secondBasePattern` case was missing entirely** (a new 2nd base defaulted to `''` = no react-pattern), AND the 3rd/4th/5th were each shifted one stack slot too low (3rd → `stack[0]` = pattern 1 instead of `stack[1]` = pattern 2 — the exact opposite of the owner's "3rd should default to pattern 2 unless none"). FIX: rewrote with `_firstStackId(from)` (first non-empty `stack[k].id` for k from `from` down to 0): `secondBasePattern`→slot 0, `thirdBasePattern`→slot 1, `fourthBasePattern`→slot 2, `fifthBasePattern`→slot 3. Verified: 2-pattern stack → 2nd=pat1, 3rd=pat2, 4th/5th=pat2 (fallback); 1-pattern stack → 3rd=pat1 (fallback). JS-only (cache-buster `spb-overlay-react-fix2-20260530` + reload; no server restart). ⚠️ The HTML cache-buster had been independently reset to `spb-overlay-react-fix-20260528` — likely Cursor editing concurrently; watch for clobbering.

**Next (iter 3): issue 2** — a pattern at scale 0.25 + its base-overlay react-to at 0.25 don't align. Lead: `_v6kw["second_base_pattern_scale"] = float(...) * auto_scale` (shokker_engine_v2.py ~16050) — verify the zone's PRIMARY pattern uses the same `auto_scale` multiplier, else the overlay's react-pattern renders at a different size.

## 2026-05-30 stress-loop iter 3 — issue 2 (overlay react-pattern scale alignment) FIXED + all prior fixes intact

All prior fixes persist (server PID 381444 unchanged, `overlay.py` HSB-fix + `compose.py` 500-skip + `state-zones.js` issue-1 all present/live) — no clobbering by Cursor.

**Issue 2 (engine fix) — `shokker_engine_v2.py`.** The 2nd-5th base overlay react-pattern scale (lines 16050/16095/16137/16179) multiplied by `auto_scale` UNCONDITIONALLY, but the primary pattern (15964: `if not _pattern_fit_zone: zone_scale *= auto_scale`) and the pattern stack (16235: `* (1.0 if _pattern_fit_zone else auto_scale)`) apply `auto_scale` only when fit-zone is OFF. So with fit-zone ON, the overlay's react-pattern got an extra `auto_scale` → rendered at a different size than the gold pattern it reacts to (the 16049 comment's stated goal: "keep aligned with the primary pattern scale"). FIX: applied the same `(1.0 if _pattern_fit_zone else auto_scale)` guard to all 4 overlay lines (replace_all). Server restarted (381444→351528, up 200 ~2s). No regression: clean render 200, overlay render 200, Pattern-Pop HSB `changed:78`. The alignment improvement itself is an internal scale formula (not pixel-verifiable) — owner to confirm visually.

⚠️ The 2nd base has TWO scale controls — main "Scale" (`secondBaseScale`, state-zones.js:2409) and "React to zone pattern → Scale" (`secondBasePatternScale`, :2436). The react-pattern alignment is governed by the LATTER. If the owner's "scale the BASE OVERLAY LAYER" meant the main Scale, the alignment slider is the separate React-to-pattern one — owner to confirm which.

🏁 All 4 owner items addressed: (1) live-preview 500 ✓, (2) HSB across 2nd-5th ✓, (3) react-to-pattern default ✓, (4) scale alignment ✓ (engine fit-zone fix). Remaining: ~11.5s 50%-preview perf flag.
