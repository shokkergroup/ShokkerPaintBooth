# Tool Trust Matrix — PSD Painter Gauntlet (Track A-E)

Last update: 2026-04-19 TRUE FIVE-HOUR shift.

Columns: ✓ = honored / ✗ = silently ignored / N/A = doesn't apply.

## Brush family

| Tool | brushSize | brushOpacity | brushHardness | brushFlow | symmetry | layer-local |
|---|---|---|---|---|---|---|
| Color Brush | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recolor | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Smudge | ✓ | ✓ (as strength) | ✓ | ✓ | ✗ | ✓ |
| Clone Stroke | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| History Brush | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Pencil | ✓ | ✓ | N/A (always hard) | N/A (binary stamp) | ✗ | ✓ |
| Dodge | ✓ | ✓ (as exposure) | ✓ | ✓ | ✗ | ✓ |
| Burn | ✓ | ✓ (as exposure) | ✓ | ✓ | ✗ | ✓ |
| Blur Brush | ✓ | ✓ (as strength) | ✓ | ✗ | ✗ | ✓ |
| Sharpen Brush | ✓ | ✓ (as strength) | ✓ | ✗ | ✗ | ✓ |
| Erase | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |

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

## Selection modifiers (TF9-TF11 + TF21)

| Tool | undo entry | proof |
|---|---|---|
| Grow Selection | ✓ TF9 (was silent no-op via missing `pushUndo`) | tests/test_runtime_selection_modifiers.py |
| Shrink Selection | ✓ TF10 | × 2 scenarios |
| Smooth Selection | ✓ TF11 | × 2 scenarios |
| Border Selection | ✓ TF21 (Hennig perfection-pass spotted sister bug) | tests/test_tf16_dead_bundle.py |

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
| Selection modifiers route through `pushZoneUndo` not bare `pushUndo` | ✓ TF16 ratchet |

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
