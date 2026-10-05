# Authored pattern color routing — 2026-09-07

Owner: Abstract Gradient has full color, while Leg Warmer, Funk Zigzag and other Decades patterns do not.

## Follow-up: the missed Soul Core / monolithic route

The owner's subsequent Leg Warmer screenshot proved the earlier completion claim was too broad. The44 live tests below exercised a regular `metallic` base only. Special finishes such as **Soul Core Crimson — Teal Flash** route through `overlay_pattern_paint`, which bypassed both the new Overlay/Blend mode and the authored-color resolver. Abstract Gradient's existing image path worked there while other patterns still used the old shaded paint callbacks. This is an engine dispatch defect, not an opacity setting error or a required browser-cache workaround.

All ten car/generic/helmet/suit call sites now pass zone controls to the shared authored pattern compositor, including the monolithic additional-pattern stack. Full color, actual alpha, linear Opacity/Strength/Intensity, placement, flips and scaling follow the regular pattern contract. Standalone legacy calls retain their existing behavior; no authored finish/spec construction changed and no new M7 score is claimed.

Verification after the follow-up:

- Reproduced the miss on normal59876 using `finish=fs_core_crimson`: Leg Warmer differed from its authored artwork by up to249/255. Saved three actual before previews.
- Re-ran **all44 Decades50s–80s** through normal59876 over Soul Core:40 artwork matches within1/255 and four procedural color checks. Full/half/zero opacity and zero strength pass for all three owner examples.
- **71 focused tests pass**, including12 new regressions: real Soul Core TGA exports via both `finish` and `base` routing, additional pattern layers, identical regular/monolithic Overlay and Blend output with scale40%, rotation, offsets, flips, zone fit, protected pixels and fractional controls.
-235 legacy spec golden comparisons unchanged;240/240 current spec-overlay thumbnails still match. Two changed runtime code files are mirrored and SHA-verified. Canonical supervisor generation6/PID74516 serves10.0.1-beta on59876.
- Native2048 pattern-paint stages: Abstract Gradient0.348s, Leg Warmer0.265s, Funk Zigzag0.232s. Synthetic source and isolated TGA destinations only; no customer document/config or track output modified.

Evidence: `mono_live.py`, `mono-before.json/png`, `mono-after.json/png`, `mono-performance.json`, `mono-runtime-scope.json` in `_spec_overlays_v2_work/pattern_color/`. The actual open in-app tab contained a different document from the owner's screenshot and was inspected without changing it. The repaired combination was therefore verified through the same live HTTP renderer, not claimed as a visual inspection of the owner's native session.

## What the prior repair missed

The picker intentionally displayed234 authored image overrides while the paint renderer excluded the `regular_floor` artwork and used procedural shading. The opacity repair made that shading fully visible, but could not restore discarded artwork. Abstract Gradient already followed the normal color-image route, explaining the inconsistent behavior. Decade registry detail wrappers also replaced some original color callbacks with achromatic callbacks.

The old color-image loader additionally synthesized transparency from brightness, removing dark or light artwork even at100% opacity. Prior visibility tests did not verify fidelity to the picker artwork. New regressions compare actual authored pixels and real TGA/HTTP output.

## Repair

- `engine/pattern_artwork.py` resolves the same authored artwork for the picker and Overlay/Blend paint modes. If there is no image override, retained original decade paint/texture callbacks supply procedural color.
- `engine/registry.py` retains those authored callbacks before detail/material wrappers replace active callbacks. Existing finish functions and spec construction are not rewritten.
- `engine/render.py` has an explicit, separately cached authored-alpha mode. Full overlays retain actual alpha and all RGB colors. Rotated repeating artwork wraps through the edges instead of introducing transparent wedges.
- Primary and stacked paint composition both use the shared source and placement helper. Placement works on a copy so moving a pattern cannot corrupt the cached original. Opacity and Strength still attenuate the finished contribution once.
- Five active procedural picker assets were refreshed with their retained color callbacks, and their fingerprints include the authored color source so browser caches update.40 image-art cards in Decades retain their existing artwork.

## Evidence and scope

Evidence folder: `_spec_overlays_v2_work/pattern_color/`.

- All44 Decades50s–80s choices exercised through actual HTTP previews:40 image outputs match their authored artwork within1/255; four procedural choices retain color. Abstract Gradient, Leg Warmer and Funk Zigzag also pass half-opacity and zero-opacity checks.
- Native source-pixel tests for Leg Warmer and Funk Zigzag; actual TGA exports for all three owner examples; authored alpha, dark/white pixels, rotation, placement, cache isolation, source exclusion, linear controls, prior scaling and spec-only behavior.58 focused tests pass.
- All234 mapped artwork assets exist and already match the packaged runtime copies. Twelve changed runtime/artifact files synced across246 checked paths.
-235 legacy spec golden comparisons remain unchanged. No new finish module, geometry, palette, or spec renderer was authored, and no new M7 score is claimed. This restores existing authored color/artwork routing.
- Synthetic source images and isolated output were used for previews/exports. No customer paint, recipe, project or iRacing viewer was modified.

Live comparison: `_spec_overlays_v2_work/pattern_color/live-three-patterns.png`. Category comparison and detailed results: `before-category.png`, `after-category.png`, `live-audit.json`, `bake.json`.

Normal59876 refreshed through the canonical supervisor to generation5/PID87052,10.0.1-beta. All five refreshed picker assets are pixel-identical when fetched from the normal live route. An additional startup fingerprint regression passes: the browser hash tracks retained authored color even when the legacy registry entry differs before the first render. The eight authored-art tests pass after that cache correction; the earlier full58-test run also passed.2048-square paint-pass timings for the three examples: Abstract Gradient2.427s, Leg Warmer0.467s, Funk Zigzag0.432s. These are local paint-stage measurements, not a whole-app latency guarantee.
