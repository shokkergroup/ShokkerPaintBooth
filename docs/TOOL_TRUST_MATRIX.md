# Tool Trust Matrix — PSD Painter Gauntlet (Track A-E)

Last update: 2026-08-09 owner-directed Photoshop/GIMP parity program.

## Active cross-workflow trust repair

| Contract | Flat TGA/JPEG/PNG Zone workflow | PSD/XCF/ORA Layer workflow | Current proof |
|---|---|---|---|
| Document authority | Flat load clears layered state and selects Zone before pixels publish | Layer import retains editable layer authority plus separate Zones | Focused source ratchets; live layered/flat reload resumes when the in-app browser surface is available |
| Tool activation | Zone-only tools route before arming | Layer-only and dual paint tools refuse before arming when no editable target exists; creators remain valid | Live Rectangle: prior 93 ms false drag -> 567 ms real commit, 237,170 mask pixels; focused missing-target runtime proof |
| Brush / Erase target | Zone mask remains Zone-owned | Inactive Zone region no longer clips Layer pixels; enabled region/alpha lock still clip | Live Brush +1,396 visible pixels with exact Undo/Redo; live Eraser Undo restored |
| Fill coordinates | Zone selection behavior retained | Cropped Layer can fill transparent document space without shifting existing pixels | Live Fill 4,029,285 pixels in 539 ms; prior result was silent no-op |
| History truth | One visible chronological read model | Same read model spans Zone/pixel/Layer actions | 2026-08-08 focused regressions; final live panel replay pending browser recovery |
| Retouch upload | N/A | Dirty union uploads changed pixels; whole-image commands retain full fallback | 2048² / 80px-radius transfer ratio >150×; all visible + hidden retouch kernels covered |
| Initial Layer target | N/A | Topmost visible editable Layer is selected and public/private state is published atomically | PSD/XCF/ORA source ratchets; degraded locked source fallback remains Zone-routed |
| Whole-Layer move | N/A | Bbox changes update SOURCE at most once/frame; 2048-square readback happens once on commit | Coalescer latest-frame proof; visual-only drag frames + final publication ordering ratchet |
| Placement drag | Actual Zone/base/pattern offsets mutate only past a 4px screen threshold; live preview is latest-state, not settle-only | Zones remain separate when a layered document is active | Async-pump concurrency proof; both placement paths have no trailing drag debounce or click-only Undo |
| Layer command strip | N/A | Duplicate, Mirror, Merge Down, Delete, visibility, lock, alpha lock, clipping, blend, Blank, and Flatten share one-action/exact-replay semantics | Live 11-layer PSD; Flatten 11→1→11→1→11, Blank 11→12→11→12→11, final 11/0 |
| Destructive confirmation | N/A | Flatten uses a docked nonblocking warning; safe focus, Escape/outside Cancel, mutation only after confirm | Live panel clear of SOURCE; Keep/Escape 11/0; confirm 1/1; Undo 11 named Layers/0 |

Frozen by owner direction: **Pick Color** and current **Spatial Exclude** behavior.

2026-08-08 family proof: core cross-format **38/38**, Zone selection/mask/placement **44/44**, and Layer paint/retouch/transform/adjust **118/118**. These batteries overlap and are intentionally reported separately rather than added into a misleading total.

Columns: ✓ = honored / ✗ = silently ignored / N/A = doesn't apply.

## Brush family

| Tool | brushSize | brushOpacity | brushHardness | brushFlow | brushShape | symmetry | layer-local |
|---|---|---|---|---|---|---|---|
| Brush | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Color / Pattern Brush | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recolor | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Smudge | ✓ | ✓ (as strength) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Clone Stroke | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| History Brush | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Pencil | ✓ | ✓ | N/A (always hard) | N/A (binary stamp) | ✓ | ✗ | ✓ |
| Dodge | ✓ | ✓ (as exposure) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Burn | ✓ | ✓ (as exposure) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Blur Brush | ✓ | ✓ (as strength) | ✓ | ✗ | ✓ | ✗ | ✓ |
| Sharpen Brush | ✓ | ✓ (as strength) | ✓ | ✗ | ✓ | ✗ | ✓ |
| Erase | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |

Pass 39 preview contract: Zone Brush and scoped Zone refinement trace the same selected footprint into the fast overlay; dedicated Spatial Include/Exclude/Erase explicitly stays round. Focused proof: **4/4** and refreshed packaged token with zero console errors.

### Natural stroke dynamics (Pass 45)

| Path | configured controls are hard maxima | event-independent spacing | pressure behavior |
|---|---|---|---|
| Mouse Brush / Erase | ✓ | ✓ | pressure-neutral `1.0`; exact configured radius/opacity |
| Pen Brush / Erase | ✓ | ✓ | monotonic size/opacity curves; pressure interpolated between dabs |
| Clone, Color Brush, Recolor, Smudge, Pencil, Dodge/Burn, Blur/Sharpen, History, Healing | ✓ | not yet (tool-specific cadence retained) | shared bounded resolver; no size/opacity overshoot |

Pass 45 proof: pure dynamics/resampling and caller ratchets **5/5**; related legacy brush-tool checks **26/26**. Served Car Paint Brush used non-default Size/Opacity/Flow/Spacing/Smoothing, committed a multi-segment stroke, and Ctrl+Z reported `Undid layer: brush on layer`. Real stylus hardware curve calibration remains an explicit follow-up.

## Clipboard / selection lift

| Action | layer-origin pixels | source bake-back link | result |
|---|---|---|---|
| Ctrl+V Paste | ✓ | Never | Independent layer centered on active selection, else visible canvas, else canvas |
| Ctrl+Shift+V Paste in Place | ✓ | Never | Independent layer at exact copied offsets |
| Ctrl+J Layer via Copy | ✓ | Never | Independent new layer |
| Transform Selection lift | ✓ | Explicit only | Temporary layer bakes back into its captured source |

Pass 40/44 proof: source-link and placement policies plus caller/UX ratchets **8/8**. The served shortcut panel advertises both placement modes and loaded the refreshed clipboard module/token with zero console errors. Browser virtual-clipboard interception prevented a trustworthy full live Ctrl+C -> Ctrl+V claim; placement math and app wiring remain focused-runtime proven.

## Layer per-element transform commit

| Contract | status | proof |
|---|---|---|
| Moved element vacates original alpha | ✓ | `layer-transform-raster.eraseSourceAlpha` + caller-order ratchet |
| Linked elements preserve relative spacing | ✓ | pure placement fixture; commit no longer piles every member at master destination |
| Linked instances vacate their source alpha | ✓ | explicit pre-composite erase ratchet |
| Missing/locked Layer activation returns false | ✓ | isolated runtime refusal fixture; pending metadata cleared |
| Successful activation propagates truthfully | ✓ | selection/context callers consume boolean result; failed lifted session rolls back |
| Selection -> Zone mask uses transformed alpha | ✓ | full-canvas raster honors move/rotation/negative flip/scale and soft alpha |
| Zone mask combine is truthful | ✓ | byte-wise Replace/Add/Subtract/Intersect; one captured Zone undo only on change |

Pass 41-43 proof: **12/12**. Refreshed packaged transform module/token loaded with zero console errors; live Wire whole-Layer Transform activated and cancelled cleanly without mutation. The transformed mask raster/combine contract is pure-runtime and source-ratchet proven; full live bake awaits a disposable active Zone selection.

## Composite mutators (TF1-TF5)

Columns: locked-layer guard / active-layer routing / preview refresh on composite path / proof.

| Tool | locked | active-layer | preview | runtime proof |
|---|---|---|---|---|
| Auto Levels | ✓ TF1 | ✓ TF1 | ✓ W5 | tests/test_runtime_composite_mutators.py × 3 scenarios |
| Auto Contrast | ✓ TF2 | ✓ TF2 | ✓ W6 | × 3 scenarios |
| Desaturate | ✓ TF3 | ✓ TF3 | ✓ W7 | × 3 scenarios + algebra check |
| Invert Colors | ✓ TF4 | ✓ TF4 | ✓ W8 | × 3 scenarios + algebra check |
| Posterize | ✓ TF5 | ✓ TF5 | ✓ W9 | × 3 scenarios |

## Canvas-geometry refuse-when-layered (TF6-TF8)

Columns: PSD-layer guard (refuses, does NOT route to layer — semantics differ from TF1-TF5) / preview / proof.

| Tool | PSD-layer guard | preview on no-layer path | runtime proof |
|---|---|---|---|
| Flip Canvas H | ✓ TF6 (refuses + error toast) | ✓ W5-W9 era | tests/test_runtime_canvas_geometry.py × 2 |
| Flip Canvas V | ✓ TF7 (refuses + error toast) | ✓ | × 2 |
| Rotate Canvas 90 | ✓ TF8 (refuses + error toast) | ✓ | × 2 |
| Flip/Rotate/Resize + Zone masks | ✓ (same refusal contract) | ✓ paint + `regionMask`/`spatialMask` stay registered | exact transforms + atomic dimension/pixel/mask undo in `tests/test_regression_canvas_mask_geometry.py` |

## Adjustment family (uses `_getAdjustmentTarget` dispatcher)

| Tool | locked | active-layer | preview | proof |
|---|---|---|---|---|
| Brightness/Contrast | ✓ | ✓ | ✓ | dispatcher (existing) |
| Hue/Saturation | ✓ | ✓ | ✓ | dispatcher |
| Sepia | ✓ | ✓ | ✓ | dispatcher |
| Gaussian Blur | ✓ | ✓ | ✓ | dispatcher |
| Sharpen | ✓ | ✓ | ✓ | dispatcher |
| Add Noise | ✓ | ✓ | ✓ | dispatcher |
| Emboss | ✓ | ✓ | ✓ | dispatcher |
| Vignette | ✓ | ✓ | ✓ | dispatcher |
| Threshold | ✓ | ✓ | ✓ | dispatcher |
| Color Temperature | ✓ | ✓ | ✓ | dispatcher |
| Vibrance | ✓ | ✓ | ✓ | dispatcher |
| Gradient Map | ✓ | ✓ | ✓ | dispatcher |
| Color Replace | ✓ | ✓ | ✓ | dispatcher |

## Selection modifiers (TF9-TF11 + TF21 + SPB-93 Pass 29)

| Tool | history / ownership | proof |
|---|---|---|
| Grow Selection | Candidate compared before one real Zone-mask snapshot; full/edge no-op creates no history | `tests/test_regression_selection_refine_naturalness.py` |
| Shrink Selection | Typed separable candidate; one captured-Zone mask history only when changed | same |
| Fill Holes | Typed boundary flood fill; no enclosed holes creates no history | same |
| Feather Selection | Three separable box passes approximate Gaussian falloff; reports soft-pixel count | same |
| Smooth Selection | Pure Shrink1 -> Grow1 candidate; exact comparison before history | same |
| Border Selection | ✓ TF21 (Hennig perfection-pass spotted sister bug) | `tests/test_tf16_dead_bundle.py` |
| Select All | Already-full no-op creates no history; real selection records/restores actual `regionMask` | `tests/test_regression_selectall_naturalness.py` |
| Elliptical Marquee | Candidate commits once, exact duplicate is history-free, and canonical settlement updates visible Region state immediately | Live 1,052,051 to 1,800,224 px; duplicate no-op; Undo exact + `tests/test_regression_ellipse_naturalness.py` |
| Lasso | Replace/Add/Subtract build privately; History captures BEFORE before publication; feather is candidate-local; exact duplicate is history-free; polygon vertex hint updates on add/remove/close | Freehand live 358,701 to 1,441,625 px with exact Undo/Redo; polygon live 1/2/3/4, Backspace 3, Enter 995,501, Undo exact + `tests/test_regression_lasso_history_settlement.py` |

## SPB-native Zone tools (SPB-93 Passes 27-37)

| Tool | ownership | history / preview | live proof |
|---|---|---|---|
| Move Selection Border nudge | Zone `regionMask` only; active only in Move Border | Arrow burst = one real mask undo/redo; no history for blocked/no-op; modifiers do not split the burst | 1,002,001 px: `6px, 10px` one commit; mostly 31-114 ms repeat input; non-Move Arrow created no ghost |
| Decal Rescue Kit | Active Zone recipe + exact existing UV selection; no PSD pixel writes | One Zone-config undo/redo; both refresh compiled paint/spec preview | Flat Vinyl apply removed stale layer restriction, preserved 1,002,001 px mask/source RGB; Undo/Redo changed spec preview and restored/reapplied restriction |
| Selection Refine | Captured Zone `regionMask` only; top Mask menu exposes Grow/Shrink/Fill/Feather/Smooth | Candidate before one actual mask snapshot; identical/no-result operations create no history | 1,002,001 px Grow2: 125.4 ms compute / 198 ms total / 8,024 changed; full-canvas no-op: 24.3 ms, no commit |
| iRacing Lighting Mask | Active Zone `specLightingMask` + exact existing UV selection; no RGB/M/R/CC or layer writes | One Zone-config undo only when alpha setting changes; preview/full/PS payload parity and config persistence | Real multi-zone pair: A0 only inside exact 1,120 px region, M/R/CC byte-identical, outside untouched; production 32-bit TGA readback preserved A0 |
| Point Material Sampler | Channels Inspector samples compiled M/R/CC/A; transfer writes only active Zone `specMaterialOverride` | Same-value apply is history-free; one Zone-config undo for apply/clear; all payload builders + preview adapter agree | Real multi-zone: M200/R80/CC40/A32 confined to exact 1,024 px region; source paint byte-identical; Lighting Mask alpha precedence proven |
| Spec Material Select | Compiled M/R/CC/A -> active Zone `regionMask`; Connected or All Similar | Current Replace/Add/Subtract; candidate/no-op before one actual mask snapshot; lower-res preview maps nearest to canvas | 2048² 160,000 px: All 11.2 ms, Connected 7.4 ms; split-island barrier and composition byte math proven |
| Clear All Regions | Batch of existing Zone `regionMask` values only | One stable-ID multi-mask transaction; no-op safe; undo/redo atomic across Zone reorder | 2/2 masks restored then re-cleared; focused 6/6 |
| Material Range Remapper | Active Zone `specMaterialRemap`; maps M/R/CC ranges without flattening texture | One Zone-config undo only when changed; all preview/export builders and engine agree; RGB/alpha/PSD untouched | Real imported texture kept >8 distinct values/channel inside exact 1,024 px; outside/alpha/source paint exact; 2048² performance locked |
| Escape / shortcut ownership | Installed-once Zone keyboard module; Lasso/modal consumes only when active | No history for cancel; otherwise plain Escape reaches Layer selection owner | Runtime 5/5 + dedicated source guard |
| Canvas mask geometry | Composite paint plus all Zone `regionMask`/`spatialMask` geometry | One dimension + pixel + multi-mask transaction; bilinear soft masks, nearest categorical masks | Exact flip/rotate/resize + 2x3/3x2 undo/redo + 2048² performance; focused 6/6 and legacy runtime 6/6 |
| Exported selection compatibility APIs | Grow/Shrink/Smooth delegate to the candidate engine; Border/Color Range own only active Zone `regionMask` | Candidate/no-op before real mask history; Color Range honors Replace/Add/Subtract and tolerance 0 | Focused API/history ratchet 6/6; audited span has zero `pushZoneUndo` |

Consolidated proof: Pass 27-37 regression/runtime files are **74/74**, including source-paint preservation and real engine/TGA round-trips. Pass 38's shared footprint contract is **4/4**, its 1.2-million-point stress probe is 55.4 ms, and the refreshed packaged booth committed/undid a real Square Dodge dab on Car Paint.

## Apply* family (W1-W4 — proven this shift)

| Tool | preview refresh | runtime proof |
|---|---|---|
| applyFinishFromBrowser | ✓ (prior W1) | tests/test_runtime_apply_paths.py |
| applyCombo | ✓ (prior W2) | tests/test_runtime_apply_paths.py |
| applyChatZones | ✓ (prior W3) | tests/test_runtime_apply_paths.py |
| applyHarmonyColor | ✓ (prior W4) | tests/test_runtime_apply_paths.py |

## PS Export (W14 — proven this shift)

| Path | PSD-layer composite-fallback | proof |
|---|---|---|
| doExportToPhotoshop | ✓ (prior W14) | tests/test_runtime_ps_export.py × 4 scenarios |

## Finish registry (TF12-TF14)

| Check | status | proof |
|---|---|---|
| Phantom BASE_GROUPS entries | 0 (was 9) TF12 | tests/test_runtime_finish_registry.py |
| Phantom PATTERN_GROUPS entries | 0 | validateFinishData runtime |
| Phantom SPEC_PATTERN_GROUPS entries | 0 | validateFinishData runtime |
| Cross-registry PATTERN_GROUPS entries | 0 | validateFinishData runtime |
| Duplicate PATTERN names | 0 (was 4) TF13 | validateFinishData runtime |
| Duplicate SPEC_PATTERN names | 0 (was 4) TF14 | validateFinishData runtime |

## Catalog correctness (TF15 + TF20)

| Check | status |
|---|---|
| UTF-8→cp1252→UTF-8 mojibake bytes (em/en/ellipsis cluster) | 0 (was 51) TF15 |
| UTF-8→cp1252→UTF-8 mojibake bytes (lightning bolt cluster `âš¡`) | 0 (was 6) TF20 — Hennig spotted in SHOKK'D toast |

## Build hygiene (TF16)

| Check | status |
|---|---|
| Dead `paint-booth-app.js` bundle marked `!STALE-BUNDLE` | ✓ TF16 |
| No HTML loads dead bundle | ✓ TF16 |
| Region-mask mutations use actual Zone-mask snapshots, never Zone-config history | ✓ Passes 27/29/33/36/37 ratchet |
| Zone/Lasso/modal shortcuts have one installed owner; Escape consumes only when acted | ✓ Pass 35 runtime + source guard |

## Layer-Local Behavior — confirmed via gating

All 10 paint tools route through `isLayerPaintMode()` → `_initLayerPaintCanvas()` when an editable layer is selected, OR fall to composite via `pushPixelUndo()`. Locked-layer strokes refuse via `shouldBrushStrokeProceed()`. Hidden-layer strokes warn once via `warnIfPaintingOnHiddenLayer()`.

The TF1-TF8 composite mutators now use the same active-layer routing pattern (with explicit locked-layer guards) instead of always mutating composite — closing a silent-data-divergence bug that the prior shift admitted was unfixed.

## Runtime-accepted vs structural-only

| Bucket | Accepted via | Coverage |
|---|---|---|
| Runtime-proven (Node V8 executes function body, asserts observable side effects) | tests/test_runtime_*.py | 21 NEW TF wins + W1-W4 + W14 reopen-proof = 33+ runtime tests |
| Structural-only (string presence in source) | tests/test_layer_system.py | TF15 mojibake byte ratchet, TF16 selection routing ratchet |
| Verified clean by audit | docs/FINISH_QUALITY_REPORT.md (2026-04-19 01:01) | 375 finishes, 0/0/0/0 broken/GGX/spec-flat/slow |
| Manual-only (running app) | TBD next shift | PSD painter gauntlet items in docs/PSD_PAINTER_GAUNTLET_OVERNIGHT.md |
