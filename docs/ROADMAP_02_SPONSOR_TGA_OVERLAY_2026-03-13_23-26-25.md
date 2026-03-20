# Roadmap #2 - Sponsor TGA Overlay Layer

**Created:** 2026-03-13 23:26:25 (local)  
**Status:** Planning-ready reference  
**Owner intent:** Allow users to import sponsor/number overlays as a top zone layer with independent finish behavior.

## Goal
Add a direct sponsor overlay workflow so users can drop in a TGA/PNG decal layer above zone rendering, then assign its own base material (gloss, matte, metallic, etc.) without rebuilding sponsors inside the editor.

## Product Requirements
- Import one or more sponsor overlay images (`.tga`, `.png`) with alpha.
- Place overlay above normal zone compositing (late-stage render pass).
- Give each sponsor overlay its own finish controls:
  - Base finish (`base`) or monolithic (`finish`)
  - Intensity and base strength
  - Optional wear and spec multiplier
- Basic transforms per sponsor overlay:
  - Scale, rotation, X/Y offset
  - Flip H/V
  - Opacity
- Per-overlay toggle and ordering (move up/down in sponsor stack).

## Engine Design Direction
- Implement as a dedicated post-zone compositing pass in Python:
  1. Render normal zones first (existing pipeline untouched).
  2. For each sponsor overlay, decode RGBA alpha mask.
  3. Build a temporary zone mask from alpha.
  4. Apply selected finish through existing compose path.
  5. Alpha-composite into final paint/spec outputs.
- Keep this isolated from existing zone mask logic to avoid regressions.

## Frontend Design Direction
- New panel: `Sponsor Overlay Layers` with add/remove/reorder cards.
- Card fields:
  - Source file path
  - Finish picker
  - Strength/opacity sliders
  - Transform controls
- Add to render payload under `extras.sponsor_overlays`.

## Payload Contract (Draft)
```json
{
  "extras": {
    "sponsor_overlays": [
      {
        "path": "D:/.../sponsor.tga",
        "base": "gloss",
        "finish": null,
        "strength": 1.0,
        "opacity": 1.0,
        "scale": 1.0,
        "rotation": 0,
        "offset_x": 0.5,
        "offset_y": 0.5,
        "flip_h": false,
        "flip_v": false,
        "wear_level": 0
      }
    ]
  }
}
```

## Phase Plan
- **Phase A (MVP):** single sponsor overlay, fixed top layer, base-only finish.
- **Phase B:** multi-overlay stack + reorder + monolithic support.
- **Phase C:** SHOKK export/import integration for sponsor overlay bundles.

## Risks / Guardrails
- Alpha edge halos on resampling -> use premultiplied-alpha compositing.
- Performance on many overlays -> cap max overlays for MVP.
- Avoid touching existing zone semantics in Phase A.

## Acceptance Criteria
- User can import a sponsor TGA and render it with independent material.
- Sponsor remains crisp with transparent edges.
- No behavior regressions in normal zone-only renders.
