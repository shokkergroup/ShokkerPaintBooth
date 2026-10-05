# Independent pattern paint and spec — completed 2026-09-08

Owner request09-07: Hue/Saturation on pattern artwork, working Blend that retains underlying paint color, and independent spec replacement default0%, linear through50%, complete at100%. Shared pattern/spec scale.

## Result

- Primary and additional pattern layers expose Hue−180…180°, Saturation−100…100%, and Spec Amount0…100%, with step/reset controls and explanatory tooltips. New and older recipes without a spec amount start at0. Five explicit persistence maps, config application, serializer, Undo and resets retain the controls.
- Overlay applies Hue/Saturation to the isolated artwork before it is composited. Source paint and spec do not receive that color adjustment. Blend uses the pattern's normalized tonal detail and the underlying paint's hue/saturation, giving strong visible structure without replacing its color. Color controls are disabled in Blend with visible guidance explaining why.
- The pattern's existing full compiled spec uses the catalog's chrome reference carrier. Spec Amount replaces M/R/Cc independently of paint opacity/strength; alpha remains the separate zone lighting mask.50% is an equal mix. Native material is cached in a bounded four-entry cache; scale, rotation, offsets, flips and fit operate on the pure spec plate. Car auto-scaling follows the same scale factor as pattern paint; accessory paths use their existing direct scale convention.
- Explicit spec amounts bypass the old automatic pattern modulation for ordinary bases and monolithic/generic finishes. A common stage applies the chosen pattern spec over the zone material. Additional layers each have their own amount. Legacy non-app calls without the new control retain their old rendering behavior, including existing picker bakes.
- Explicit spec mixtures preserve linear interpolation through final material threshold handling: a former roughness re-clamp changed a few midpoint pixels by4/255. Existing ordinary-material floors remain unchanged. Zone masks and later explicit zone-level material/lighting controls still apply.

## Transport defect found during verification

The preview endpoint reconstructs each zone using a manual field list. It was dropping `pattern_paint_mode` from the earlier repair, so changing Blend in the UI could never reach the renderer. The initial new controls also exposed that gap. Shared `server_routes/pattern_controls.py` now preserves Blend, Hue, Saturation and explicit-zero Spec Amount in both preview and Photoshop layer-export builders. Full render retains these fields through its general key conversion.

This is covered by executable Flask-route regressions, not just a test of the helper: both regular `base` and monolithic `finish` requests are checked at the actual engine call boundary. Production controls and their serializer were exercised in a disposable browser harness forwarding previews to the normal server. The owner's existing browser document was preserved.

## Evidence

Work folder: `_spec_overlays_v2_work/pattern_material/`.

-75 focused Python tests passed as a suite; two additional actual preview-transport tests passed with the final six-test material file (77 distinct regressions total). Real TGA tests cover independent channels, 0/50/100 spec, hue, desaturation, Blend, scale, additional layers and ordinary/special bases. `tests/pattern_material_persistence.cjs` passes production config serialize/hydrate, missing-field defaults, stacked fields and all five mapping sites.
-44 real HTTP previews on59876 cover Abstract Gradient, Leg Warmer and Funk Zigzag over Electroplate and Soul Core Crimson. Default spec exactly matches no-pattern spec; paint is unchanged by Spec Amount; halfway spec is the midpoint within quantization;100% spec matches across bases. Hue/Saturation leave spec unchanged, desaturation is grayscale, Blend visibly differs, and scaling moves the spec.
- Browser controls: Hue120/Spec50, Blend with disabled H/S guidance, Spec100, additional-layer H/S/spec defaults/changes and Undo were exercised. `live-color-controls.png` shows actual HTTP output for original/Hue120/desaturated/Blend. `live-results.json` records the six base+pattern combinations.
-235 legacy spec golden comparisons unchanged;240/240 existing v2 spec-overlay thumbnails match. Verified bakes were re-registered after the shared compose fingerprint changed. No finish geometry, image artwork or named spec renderer was rebuilt; no new M7 claim.
-2048² Soul Core+Leg Warmer complete preview passes: Overlay/spec0 **1.367s**, Overlay/spec100 **1.727s**, Blend/spec100 **1.367s**. Local timings, not a universal latency guarantee.
-14 runtime paths verified synchronized; four live client files match root bytes with cache token `spb-pattern-material-20260908`. Canonical59876 runs10.0.1-beta, supervisor generation8/PID37952. Synthetic paint and isolated export destinations; no customer document/config or track output was changed.

Reload the booth once to load the new client controls. Fresh preview requests then carry all independent fields.
