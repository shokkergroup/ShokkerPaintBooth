# Regular pattern visibility repair — 2026-09-07

Owner: Checker Warp in Pattern 1 barely visible at100%; expects a full overlay with opacity/strength reducing it, plus an optional stronger paint blend.

## Cause and resulting behavior

- Rebuilt regular paint callbacks deliberately add only a small achromatic delta. Composition further attenuated based on active paint-function count and could tint the result back into the source color. This was shading, not a complete pattern layer.
- Strength (`patternSpecMult`) reached spec composition but was absent from all six zone paint-call payloads. The paint callback therefore used its default strength.
- Primary and additional pattern opacity handlers used `parseInt(value) || 100`, turning0 into100. Fixed both installed control implementations.
- Paint mode now defaults to **Overlay — full pattern**. **Blend — keep paint color** uses strong hard-light contrast. The selector applies to the regular pattern stack; it persists through config/recipe mapping and Undo.
- Procedural pattern plates use existing authored paint/texture construction, isolated from source paint. Full tonal coverage is placed before destination masking. Image patterns retain their RGBA artwork. Opacity, Strength and advanced intensity attenuate the completed contribution linearly, once. Adding an invisible pattern no longer changes the base's paint attenuation.
- Full Overlay covers the selected region, including anything intentionally inside that region. Excluded source layers and pixels outside the zone stay untouched. Scaling transforms the isolated design, never customer paint pixels.

## Scope and compatibility

No finish renderer, spec construction, identity contract, geometry, baked standard/picker asset, or finish catalog entry was rebuilt. Compositor calls used by existing authored thumbnail paths retain the legacy default; app zone payloads explicitly use Overlay or Blend. Existing app recipes without a mode adopt Overlay, as requested. M7 was not recomputed: this is a compositing/control repair, not a new finish-quality claim. The235 legacy spec golden comparisons remain unchanged.

## Verification

Evidence: `_spec_overlays_v2_work/pattern_visibility/`.

- Focused Python tests cover five actual pattern types, primary/stack parity,100/50/0 opacity and strength, invisible added layers, source exclusion, five sizes with rotation/offset, and real TGA export defaults/controls.
- Browser fixture executes production controls and shared payload builder. Tests mode selection/persistence, primary/additional zero opacity, undo entries, and five actual HTTP preview renders using a synthetic source only.
- Live half-opacity differs from the exact midpoint by at most0.5 on the255-byte scale; zero opacity and zero strength yield identical underlying paint. Full Checker Warp paint difference from its zero baseline averages50.36/255.
- Previous scaling and spec-only contract tests remain part of the regression run. The120 verified spec thumbnail pairs were re-registered after the compositor fingerprint changed; no rebake or pixel substitution.

Final regression run:51 Python tests pass; browser and spec-overlay UI contracts pass;235 legacy spec golden comparisons unchanged. Checker Warp's2048-square paint pass takes2.659s at1x and1.943s at0.4x on this host (uncontended run). A concurrent-test run measured3.074s/2.871s, so these are local measurements, not a whole-app latency guarantee.

Normal development endpoint remains `http://localhost:59876/paint-booth-v2.html`. Refreshed through the existing canonical supervisor:10.0.1-beta, PID48560, generation2. All9 owned runtime copies match. Live normal-port probe:240/240 spec thumbnail assets match the verified bakes.
