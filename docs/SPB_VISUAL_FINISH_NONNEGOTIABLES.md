# SPB Visual Finish Non-Negotiables

This is the hard visual contract for Shokker Paint Booth finish work.

## The Owner's Core Pain Points

The repeated failures are predictable:

- Details are too large for a 2048x2048 car canvas.
- Patterns repeat or feel like the same generator with swapped colors.
- Specs are flat, generic, or only two-color green/yellow.
- Paint and spec do not reinforce each other.
- Renderers are slow enough that users think the app is broken.
- Thumbnails or runtime mirrors sometimes show stale outputs.
- Broad "fixes" accidentally make everything share the same visual DNA.

Any future work must actively fight those failure modes.

## Scale

The default finish should read as refined texture on a car, not poster art.

Failures:

- Huge blobs.
- Huge checkerboards.
- Giant rings unless intentionally named.
- Giant square panels.
- Oversized Tetris/block shapes.
- Repeated slash/stripe systems.
- Diagonal slash-line fields used as the main paint or pattern idea.
- Sparse "three lines on a 2048 canvas" logic.

Preferred:

- Dense microflake.
- Fine scratches.
- Hairline circuit paths.
- Small arcs.
- Tiny cracks.
- Pinpoint sparkles.
- Short strokes.
- Thin motif tracing.
- Layered micro and macro detail where macro forms are supported by much finer
  texture.

## Uniqueness

Every finish needs its own visual identity.

Shared helpers are acceptable only when each finish changes:

- spatial layout
- rhythm
- density
- focal logic
- paint behavior
- spec behavior
- color/material response

Changing only colors is not enough.

If the same field could be renamed and used for another finish, fail it before
render. Metric-clean output is not review-ready when the concept is generic.

## Bad Paint / Pattern Logic

These fail even when they render fast and pass basic image metrics:

- diagonal-line fallback as the main visual
- scratches, fibers, rings, or microflake as the whole concept
- generic noise plus a themed name
- paint that relies on the same support texture as neighboring finishes
- spec detail that is richer than the paint but does not rescue a weak concept
- visually interchangeable entries with different labels

## Spec Maps

Spec maps are not decorative afterthoughts. They are material logic.

Good specs:

- follow the paint
- trace important design elements
- add hot edges and recessed shadows
- add microflake or glass texture
- use many values in metallic, roughness, and clearcoat channels
- make some motifs feel raised, etched, glowing, wet, polished, satin, or worn
- hide occasional spec-only Easter eggs as light-angle reveals: ghost motifs,
  etched paths, raised enamel edges, buried contour lines, fine glyphs, wave
  crests, rays, flowers, architecture traces, or house marks when appropriate
- use dense multi-color microflake and multi-channel noise fields inspired by
  the owner's reference textures, while preserving the stated material
- choose a material recipe per finish instead of pushing everything toward
  chrome: gloss bases can use metallic flashes, frozen or flat bases can use
  chrome/satin highlights, pearl bases can use candy-chrome traces, aged bases
  can expose rubbed metal only on worn edges, and dual-shift finishes can vary
  across the body without becoming a uniform mirror sheet

Bad specs:

- generic diagonal lines
- generic vertical stripes
- mostly green/yellow
- flat channel fills
- all-metallic/all-chrome treatment on finishes that should be gloss, satin,
  pearl, frozen, flat, ceramic, enamel, weathered, or candy
- unrelated noise pasted over the paint
- beautiful paint with a lifeless spec
- obvious pasted text, logos, or decals pretending to be hidden spec work
- one-color or two-color maps when the paint calls for richer metallic,
  roughness, or clearcoat structure

## Category-Specific Reminders

### Cultural Categories

Reference art may be used as design direction, but text, numbers, watermarks,
and poster labels must not appear in the finish. Crop or mask them out.

Specs should trace meaningful motifs:

- sun rays with varied metallic/clearcoat intensity
- dragon bodies with hot edges and scale texture
- devil eyes or symbol cores with glow-like spec behavior
- shrine/architecture edges with polished or embossed ridges
- floral linework with alternating gloss and metallic accents
- background fibers/grain with subtle roughness variation

### Signal

Signal is the best recent quality reference. Preserve the lesson:

- dense fine events
- energetic but readable specs
- paint/spec agreement
- no single giant feature doing all the work

When an expressive category starts feeling metric-clean but visually samey,
reset against Signal plus the latest Rising Sun and Viva Mexico passes. Those
references are not templates to clone; they are reminders that a finish needs a
specific motif language and a spec map that traces that language. If the new
finish is mostly scratches, fibers, rings, generic microflake, or swapped colors,
it is drifting.

### COLORSHOXX

The color flow must make sense as a full canvas. Do not tile a small reference
badly. Do not include sample image text. Specs must mimic the glitter/flake/flow
structure of the paint.

### Effects And Vision

The common failure is oversized/lazy geometric structure. Push much finer detail
and avoid repeated square/checker/halo DNA.

Additional owner correction from May 6: Effects & Vision can also fail by
becoming too similar across entries and by shipping specs that are technically
varied but not dynamically meaningful. Before another wave is accepted, compare
against Signal, Rising Sun, and Viva Mexico. Each entry needs a distinct
paint/spec idea: optical physics, film chemistry, ritual material, spectral
depth, horror artifact, or another finish-specific behavior. Support textures
are allowed, but they cannot be the whole concept.

Latest wave 3 owner review: paint and spec are both weak, not just spec. Treat
the current wave 3 Workbench as rejected/diagnostic, not accepted. Long Exposure
and X-Ray are the closest relative directions, but X-Ray's spec is only about
one-third of the way there and still needs to move beyond diagonal-line fallback.
Rework wave 3 from concept outward before moving on to wave 4.

### Hidden Spec Motifs

Not every finish needs an Easter egg, but expressive categories should often
include subtle spec-only motif reveals. Match the hidden mark to the finish
identity, bury it in the material response, and keep it refined enough to feel
premium. Ocean paints can hide wave crests or current lines. Depth paints can
hide contour rings and relief ticks. Cultural paints can hide carved symbols or
ornamental traces. Tech paints can hide pulse paths or tiny glyph systems. The
motif should feel discovered under light, not read instantly as surface art.

## Performance Contract

- Preferred: <= 3 seconds at 2048.
- Red flag: > 5 seconds at 2048.
- Bad: > 10 seconds at 2048.

When slow:

- vectorize
- cache repeated carriers
- use lower-resolution procedural fields and upscale carefully
- stamp small texture elements instead of expensive per-pixel branching
- simplify without losing fine detail

## Before Handing Off For Review

Ask:

- Would this look too big on a car?
- Does this look like another finish with different colors?
- Does the spec actually add material magic?
- Does the spec match the paint?
- Could the finish use a subtle spec-only hidden motif or richer channel palette?
- Is the canvas detailed enough at 2048?
- Is render time under control?
- Did I sync runtime mirrors?
- Did I generate a Workbench page?
- Did I update Linear?

If the answer is weak, keep working.
