# Owner tool corrections — 2026-09-08

This supersedes the broad completion claim in the earlier tools report. The owner found failures in ordinary Brush and the visible Select/Transform workflow despite prior command-level acceptance. This pass tests the actual toolbar route, gesture, affected pixels, output and history. It does not re-certify every unrelated tool.

## What changed

- **Ordinary Brush/Eraser:** pass the real dab bounds into the existing frame queue. During opaque layer painting, a disposable, small composite display surface avoids repeatedly uploading the full 4096 SOURCE canvas. Transparent composites/effects retain the exact existing fallback. Apply/Cancel remove the display surface; authoritative Layer pixels and history stay in their existing controllers.
- **Select Object:** the Select menu now routes to the visible-layer object picker. The selected-Layer move shortcut no longer intercepts this route. A clicked number/logo enters the existing direct sub-element transform, using a read-only bounds probe; it does not lift clipboard pixels or replace the Zone mask. Failed object picks cannot silently become whole-layer transforms. Existing linked-object identity is retained. Near-miss classification uses actual document dimensions; perimeter searches skip redundant interior iterations.
- **Transform:** explicit Object, Free Transform, selected-pixel and entire-layer choices; Rotate 90°, horizontal/vertical flips and existing Fit-to-Zone remain accessible. Free Transform retains an already picked object. Rotation updates the numeric controls. The redundant top XFORM icon is hidden; existing keyboard and Layer-card access remain.
- **Mask:** common area actions first. Ten edge/mask operations remain under Refine edges & advanced masks. The four former Spec Tools commands remain under Advanced spec utilities. Original handlers and Zone/Layer ownership rules remain.
- **Workspace:** Render keeps a large button but loses its oversized wrapper; smaller color and zoom controls reclaim width. No extra center row. Object quick controls use the existing blank strip only when it has room; shorter windows use the existing bottom controls, without covering the spec channels. SOURCE/LIVE preview areas are preserved.
- **Precision:** Pick Color gets a visual 15×15 pixel magnifier. Pixel detail gives Exclude a 1:1 view with the same magnifier; Fit restores the full paint. Sampling/matching functions are unchanged.

## Native evidence

Foreground Chrome, isolated localhost:59880, real 4096 Chevy paint with 11 Layers. The owner’s localhost:59876 session was not reloaded or modified. Source code is shared and served there after refresh.

| Check | Result |
|---|---|
| Positive ordinary Brush stroke | 67,837 changed pixels; SOURCE/export agree; no Zone mask changes; exact Undo |
| Comparable Brush preview work | 9 updates: 159 ms total/max25 before small display surface → 14 ms total/max4 after; 16 dabs7 ms total/max1 |
| Brush limitation | Positive stroke initialization40 ms, release commit157 ms; no claim of uninterrupted60 fps or zero release pause |
| Car Paint selected → Select Object → click Numbers → Rotate90 → Apply | Only Numbers pixels changed. SOURCE/export:368,350 changed pixels within [1791,551,2589,1354]; no alpha changes; other Layer pixels and Zone mask unchanged |
| Object Undo | SOURCE/export return exactly to baseline; Zone masks unchanged |
| Final near-gap pick / horizontal Flip / Cancel | “Layer Element: Numbers” starting from Car Paint; Cancel restores SOURCE/export/mask exactly, including after the tutorial changed the available workspace |
| Earlier object move check |535,458 changed pixels confined to old/new number bounds; exact source/export parity and Undo |
| Entire-layer action / Cancel | Explicit label “Transform Layer: Numbers”; Cancel leaves source/export and both masks exactly unchanged |
| Precision Exclude | Native fine stroke at100%, magnifier visible; Undo restores mask; Fit returns SOURCE from4096 CSS pixels to410 |
| Pick Color | Magnifier visible over Source; existing sampler regression suite passes |
| Mask capabilities | Native expansion exposes10 advanced mask commands and4 spec utilities |

Evidence is in `_tools_simplification_work/owner-brush-positive-stroke-20260908.json`, `owner-brush-source-parity-20260908.json`, `owner-brush-undo-20260908.json`, `owner-direct-object-rotate-20260908.json`, `owner-direct-object-undo-20260908.json`, and `owner-final-cancel-and-precision-undo-20260908.json`.

The intermediate `owner-cross-layer-number-rotate-flip-20260908.json` is rejected acceptance evidence: the temporary clipboard-lift path changed composited pixels outside the object by up to2/255. The final Select Object path bypasses that lift and passes exact outside-object preservation. Arbitrary masked selection transforms still use their existing lift implementation; this pass does not claim the direct-object result for that separate implementation.

## Verification and remaining scope

Executed production Brush bounds and object dispatch/bounds routes; display-surface lifecycle/transparent fallback; preview queue and composite-region contracts; menu navigation contracts;22 Python tests covering pointer routing, locks, Brush selection clipping and unchanged eyedropper sampling. Root/Electron runtime copies are synchronized with the scoped manifest. No installer build or production deployment was performed.

Final verification:6 Node contracts,22 Python tests and4 JS syntax checks pass;65 scoped runtime pairs plus Wiki match. Owner localhost:59876 serves current `spb-owner-tool-workflow-20260908h` HTML and byte-identical canvas, workflow, magnifier, Brush display and CSS assets (`owner-served-tools-20260908.json`). Final native flip cancellation is in `owner-final-object-flip-cancel-20260908.json`.

Remaining responsiveness work is the measured Brush start/release cost, particularly the off-canvas original-raster preservation fallback. Evaluate longer owner fill strokes before claiming all lag resolved. Hover still uses the existing connected-component probe; this pass does not claim Photoshop semantic object detection or universal recognition. Linear SPB-93 posting remains pending connector reauthentication; the local handoff records the changes.
