# PSD Layer ↔ Zone Pattern Placement — plan & status

Owner scenarios (2026-05-28): drop a pattern/finish **inside one element of a PSD layer** (e.g. a
Viva Mexico finish into the *yellow* of one number), transform one picked element, and fill a
hand-drawn body-panel section with a pattern that **scales to fit** that section. SPB is a
*pattern-placement* tool, not a car-painting app — these placement flows are the priority.

## Key finding — most of the machinery ALREADY EXISTS
Investigated the real code (not assumptions):

| Capability | Status | Where |
|---|---|---|
| Pick ONE element inside a layer (tight bbox via 8-connected alpha flood) | **Exists** | `selectConnectedLayerPixelsAtPoint()` paint-booth-3-canvas.js:19739 |
| Picked element → **written into the selected zone's `regionMask`** (the layer↔zone bridge!) | **Exists** | same fn, lines ~19783, 19805 |
| Free transform of a picked element (move/scale/rotate, commit sub-rect, siblings untouched) | **Exists** | `freeTransformState` / `commitLayerTransform()` |
| Zone region = color-key (color+tolerance) OR hand-drawn RLE mask | **Exists** | zone `color`/`colors[]`, `regionMask` |
| **Fit pattern to region bbox** (scale the 2048² pattern into a small region) | **Exists in engine + render plumbing** | `pattern_fit_zone` compose.py:2070/2411/2478; plumbed paint-booth-5-api-render.js:502 via `z.patternFitZone` / `z.patternPlacement==='fit'` / `z.fitIntoApplyArea` |

So the work is **glue + discoverability + 2 small gaps**, NOT rebuilding primitives.

## Done this session
- **Color Limit pick** (NEW) — opt-in mode: a pick confines the flood to the *clicked colour*, so
  clicking the yellow inside a number grabs only the yellow (verified: tol40→900px yellow-only vs
  tol200→6400px whole glyph). The *tolerance is the zone's EXISTING 0-100 "TOL" slider*
  (`zone.pickerTolerance`, default 40) — NOT a separate hardcoded number — using the same Euclidean*3
  match convention as the magic wand / Select-All-Color. The pill in Pick-Item mode
  (`window._spbColorLimitPick`) only chooses the *mode* (whole element vs one colour); the slider sets
  how close counts. `opts.colorLimit`/`opts.colorTol` on `selectConnectedLayerPixelsAtPoint`,
  paint-booth-3-canvas.js. This is the "replace only the yellow" step of Scenario B.
  - OPEN UX QUESTION for owner: keep this as a pick *mode*, or drop the pill entirely and rely on the
    existing color-key + region intersection (pick whole element → set zone colour=yellow + TOL slider)?
    Need to confirm the render intersects color-key ∩ region (compose.py has no region_mask; the
    region mask is applied in the generated script — trace before committing to that path).

## Remaining build order
1. **Surface "Fit pattern to region" as an obvious per-zone toggle.** Engine + render already honor it;
   confirm whether any UI sets `z.patternFitZone` today. If not, add one checkbox in the zone editor
   (SPEC/BASE/pattern area) that sets `z.patternFitZone = true`. Unlocks Scenario C and the visual half
   of B. Verify by rendering a small-region zone with a high-frequency pattern (feature scale shrinks).
2. **Guided flow (discoverability)** — the "without brain surgery" ask. After Pick Item captures an
   element into a zone, offer one-click "Fill this with a finish/pattern" + auto-enable Fit-to-region.
   This is the connective UX, not new engine work.
3. **Skew** in free transform (Scenario A polish) — `freeTransformState` currently does move/scale/
   rotate/flip only; add shear handles + matrix. Lower priority (A already works without it).

## Verification notes
- Color Limit verified end-to-end on the live function via a synthetic 3-colour layer.
- Fit-to-region visual verification needs a real render; the preview screenshot tool currently times
  out on this canvas-heavy app, so verify by reading rendered output pixels or owner eyeball.
