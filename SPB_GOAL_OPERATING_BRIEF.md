# SPB Goal Operating Brief

Use this file as durable memory for long-running SPB `/goal` work. Chat history
is not the source of truth; this file, Linear, and the repo are.

## Mission

Make every active SPB finish feel painter-grade: unique, detailed, fast, and
trustworthy in preview/render/export. The target reaction is "this is special",
not "this is another swapped-color generator".

## Current Goal

Work SPB-67 catalog-wide finish performance and redundancy hardening.

Use the active-only catalog scorecard as a planning source:

```text
audit/2026-05-03-spb-catalog-scorecard-active-v2
```

Only use orphan inventory for cleanup/quarantine decisions. Do not let orphaned
or deleted finishes inflate active work estimates.

## Owner Priority Queue

Owner feedback on May 6: do not blindly follow the last suggested category if
the owner calls a different active category visibly weak. Current priority is:

1. Atmosphere: 25 active entries, currently owner-visible and "pretty trash" at
   a glance. Work this next unless Linear has a higher-priority active issue.
2. Weather and Age.
3. Reactive Panels.
4. Directional Grain.
5. Material Gradients.
6. Ornamental: had a recent pass, but still re-check if owner-visible weakness
   remains.
7. Standalone Effects / Effects & Vision.
8. Brushed and Machined: category is underbuilt; owner sees only Brushed Metal
   Flake carrying it.

There is also a product-architecture task: prune down categories, combine weak
or redundant groups, and improve the picker so users are not lost in a giant
flat dropdown. Treat this as a major SPB hardening task, not polish.

## Non-Negotiables

- No lazy patterns.
- No repeated pattern DNA.
- No giant features unless the finish name intentionally demands a hero shape.
- No flat two-color spec maps for expressive finishes.
- No generic spec stripes/slashes when the paint has meaningful structure.
- No diagonal-line, stripe, scratch, fiber, ring, or noise fallback pretending to
  be a finish concept. Support texture is not the paint identity.
- No renderer errors hidden by wrappers or fallbacks.
- No broad refactors just because the area is nearby.
- No "one tiny fix and call it done" on a category pass.

## 2048 Canvas Rule

SPB canvases are 2048x2048 and get wrapped onto full-car templates. A detail
that looks medium-sized in a square preview can look huge and crude on a car.

Default to finer detail than feels necessary:

- Add microflake, hairlines, pinpoints, scratches, tiny filaments, fine cracks,
  small edge traces, dense short strokes, and secondary/tertiary texture systems.
- When a finish seems detailed enough, push detail another 25-40%.
- Avoid big checkerboards, huge cells, huge grids, giant blobs, oversized halos,
  poster-sized circles, and repeated blocks.
- If a finish is failing, do not make the main form bigger. Add smaller systems.

## Spec Map Rule

Spec maps must be alive. They should carry material behavior, not just color.

The spec should mimic the paint and enhance the design:

- Metallic channel: hot flakes, metal cores, metal-lit motifs, energetic details.
- Roughness channel: matte shadows, satin valleys, low-gloss recessed zones,
  broken texture, dirty/soft areas.
- Clearcoat channel: gloss ridges, glassy highlights, hot edges, wet pockets,
  raised elements, polished overlays.

Use rich R/G/B variation across the whole spec map. Flat green/yellow specs are
not enough for expressive finishes. The owner specifically wants specs that can
trace design elements: sun rays, dragon bodies, devil eyes, shrine edges, floral
linework, hot borders, glowing centers, raised/etched details, and small local
material changes that make the design feel almost 3D.

Dynamic spec does not mean every finish becomes metallic/chrome. Choose a
material recipe that fits the finish name and paint identity:

- Gloss base with metallic flashes: mostly clearcoat/gloss movement, with hot
  metal sparks only on edges, flecks, motif tips, or pressure points.
- Frozen or flat base with chrome/satin highlights: restrained metallic in
  ice-fracture ridges, frost facets, polished cracks, or cold edge glints while
  the base remains low-gloss or satin.
- Pearl base with candy/chrome traces: broad pearlescent clearcoat shifts,
  subtle roughness shimmer, and tiny metallic/candy-chrome threads in the motif.
- Dual-shift finish: distributed channel shifts across the whole body, but with
  local roughness/clearcoat pockets so it does not read as one uniform chrome
  sheet.
- Worn, weathered, raw, or aged finish: metallic should often be exposed edges,
  scratches, rubbed corners, oxidized pits, or buried flakes, not a polished
  mirror wash.
- Ceramic, enamel, gel, glass, or wet finishes: prioritize clearcoat depth,
  gloss ridges, wet pockets, and roughness contrast with only selective metal
  accents.

### Hidden Spec Motif / Easter Egg Rule

Some expressive finishes should contain hidden spec-only Easter eggs that reveal
themselves when light hits from the right angle. These must be subtle material
events, not obvious painted decals. Build them by varying metallic, roughness,
and clearcoat channels with fine-scale motif masks, microflake clusters, etched
lines, ghost relief, polish direction changes, and low-contrast sparkle fields.

Use finish-specific hidden motifs. Ocean and wave paints can hide currents, foam
threads, tide rings, wave crests, shell glints, or deep-water contour lines.
Cultural paints can hide suns, rays, eyes, flowers, architecture, carved borders,
raised enamel edges, and meaningful ornamental traces. Depth and illusion paints
can hide contour lines, relief rings, impossible-shadow ticks, refraction ghosts,
and tiny parallax flecks. Signal and tech paints can hide pulse paths, tiny
glyphs, trace islands, antenna echoes, and scanline shimmer. Racing or
brand-forward paints may very rarely hide a tasteful house mark or "SHOKKER"
trace, but never in a way that reads like a pasted watermark.

The user's reference images show the desired spec density: thousands of tiny
local events, many neighboring channel values, and faint larger motifs embedded
inside a high-detail microstructure. Do not copy the hot pink/yellow palette
blindly. Translate the idea into physically plausible paint behavior for each
finish: candy, pearl, chrome, satin, polish, flake, ceramic, clearcoat depth, and
roughness response should all have different color/channel rhythms. Avoid
all-chrome wash unless chrome is the stated finish, and even chrome finishes
should contain satin/roughness breaks, clearcoat pockets, or directional polish
changes so the catalog does not collapse into one material personality.

## Good Reference Logic

These are not templates to copy. They are quality bars.

- Signal category:
  - Strong, readable channel separation.
  - Paint and spec logic reinforce each other.
  - Micro sparks, tiny lines, glow carriers, and fine events make the canvas feel
    alive.
  - The repeated owner correction was "more finer detail", not "bigger shapes".
- Signal + latest Rising Sun + latest Viva Mexico are the quality reset
  references when Effects & Vision or any expressive category starts drifting
  into same-DNA scratches, generic fibers, repeated rings, or metric-clean but
  boring spec maps. Before rebuilding another Effects & Vision wave, inspect
  those three reference sets and write down what is being borrowed at the level
  of principle: unique motif logic, paint/spec agreement, dense local channel
  variation, hidden material events, and category-specific visual language. Do
  not copy their layouts or palette.
- Atmosphere keepers:
  - Solar Wind: aurora-like ribbons plus sparse particle energy.
  - Volcanic Glass: black glass, fracture, sheen, and HSB-reactive depth.
- Successful cultural/spec direction:
  - Paint motifs should be preserved.
  - Specs should trace meaningful motif structure and add rich local material
    variation, not sit as a generic overlay.

## Recent Category Notes

- Atmosphere:
  - Owner called the 25 active entries weak on May 6.
  - Start here next unless Linear says otherwise.
  - Use the good keeper logic for Solar Wind and Volcanic Glass as quality
    references, but do not let weak entries share the same sky/noise DNA.
  - Specs should carry atmospheric material behavior: misted clearcoat, vapor
    trails, pressure bands, charged particulate, glassy fracture, storm-edge
    roughness, and subtle light-angle motifs.
- Rising Sun:
  - Paint direction is closer.
  - Specs still need 30-40% more detail and more channel variety.
  - Avoid green/yellow-only specs.
- Viva Mexico:
  - Specs need total rework from the original flat style.
  - Use meaningful design tracing: suns, devils, dragons, symbols, rays, eyes,
    hot edges, and raised texture.
- Reactive Panels:
  - Avoid weird checkerboard-square line patterns.
  - Fine detail is mandatory.
  - Specs can be strong, but paint needs smaller-scale systems.
- Effects and Vision:
  - Spectral Reactive, Fractal Chaos, Metallic Halos, Tri-Zone Materials,
    Depth Illusion, and Ghost Geometry have been called out for too-large/lazy
    detail. Exotic Physics is closer but still needs checking.
  - May 6 owner correction after wave 3: wave 3 is not accepted. The owner
    called the paint functions and specs roughly 75% off: too much same-DNA
    diagonal-line, scratch, fiber, ring, and noise fallback; not enough unique,
    outside-the-box finish concepts. Long Exposure and X-Ray are the strongest
    relative directions inside wave 3, but X-Ray's spec is only about one-third
    of the way there and still leans on lazy diagonal-line fallback. Revisit
    wave 3 before continuing to wave 4 unless the owner explicitly redirects.
    Rebuild from concept outward: each finish needs its own paint motif,
    material recipe, and spec behavior. Generic scratches/fibers/rings/microflake
    are only support texture, not the concept.
  - May 6 v5d correction pass revisited wave 3 with concept-first source
    renderers and a clean 2048 Workbench:
    `audit/2026-05-06-spb67-effects-vision-wave3-v5d-correction-2048`.
    Treat it as pending owner taste review, not final forever. If rejected,
    start from the owner's visual objections, not from Workbench metrics.
- COLORSHOXX:
  - Must flow naturally across the canvas.
  - Do not paste reference-image text/logos into generated finishes.
  - Specs must mimic paint microstructure, not generic vertical/slash lines.

## Category Pruning And Picker Direction

The picker/dropdown is too overwhelming. Users should not have to browse one
giant list and guess what matters. Keep categories, but make the picker behave
more like a guided catalog:

- Add a two-level browsing model: category rail/group list first, then finishes
  inside the selected group.
- Preserve category grouping, but order groups by owner value and buyer-facing
  clarity: Best / Featured / New / Core Materials / Artistic Effects / Culture /
  Utility / Legacy or Archived.
- Add search with forgiving aliases: "old", "rust", "weather", "carbon",
  "chrome", "flake", "Mexico", "sun", "ocean", etc.
- Add filters for material behavior: metallic, pearl, chrome, satin, matte,
  clearcoat-heavy, spec-easter-egg, fast render, high detail, color-shift.
- Mark premium/showcase finishes so buyers can find the "I would pay $50 for
  this one finish" materials quickly.
- Collapse or merge categories that only have one or two weak entries. Examples
  to investigate: Brushed and Machined, Directional Grain, Material Gradients,
  Standalone Effects, Reactive Panels, and overlapping Effects/Vision groups.
- Do not delete aggressively without a mapping plan. First propose
  keep/merge/archive decisions and preserve IDs as aliases where saves/projects
  might reference them.
- Picker work should become its own Linear task if SPB-67 remains focused on
  renderer/category hardening.

## Render Budget

- Under 3 seconds at 2048 is preferred.
- Over 5 seconds is a red flag.
- Over 10 seconds is unacceptable unless specifically justified and fixed before
  owner review.
- Use vectorized NumPy fields, seeded masks, cached carriers, small repeated
  texture stamps, and low-resolution upsampled fields where useful.
- Avoid slow brute-force per-pixel loops.

## Known Culprits / Check First

When a category pass takes longer than expected, leave a short note here or in
the category's audit folder before moving on. Future passes should check these
culprits first before inventing a new theory:

- Picker rankings are wrong if they are based primarily on finish names,
  descriptions, or old generated metadata. Use the active scorecard
  (`audit/2026-05-03-spb-catalog-scorecard-active-v2/catalog_scorecard.json`
  and browser mirror `paint-booth-0-catalog-scorecard.js`) as the first evidence
  source because it measures actual renderer output, spec channel variation,
  detail energy, blockiness, and estimated 2048 render cost. Text heuristics
  are fallback only.
- Wrapper retry loops can hide the real performance bug. If a monolithic render
  is strangely slow, time the raw `paint_fn` and `spec_fn` separately at 2048.
  A shape/broadcast error may force the contract wrapper to retry multiple
  shape/bright-bump combinations before succeeding.
- Bright-bump arrays are a repeat offender. Paint functions often receive `bb`
  as 2D while the paint/mask path is 3D. Normalize once with
  `bb3 = bb[:, :, None]` for 2D arrays before adding it to RGB paint. The
  Chromatic Flake pass dropped from roughly 20s+ to about 3-4s after fixing a
  2D/3D `bb` broadcast retry.
- If a new detailed field is slow, separate field generation cost from paint
  assignment/spec assignment cost. Low-resolution upsampled fields help only
  when the field generation is actually the bottleneck.
- Avoid per-color boolean assignment loops over full 2048 frames when many
  palette entries exist. Prefer indexed palette/spec arrays where possible.
- If Workbench reports good visuals but high wall-clock time, inspect
  `report.json` sorted by `render_ms`, then probe the worst finish alone before
  rerunning the full category.
- If a 512 preassess is clean but 2048 is slow, run a 3-item 2048 probe on the
  weakest/slowest IDs before the full category page.
- Runtime mirror drift can make app behavior disagree with source. Run
  `node scripts/sync-runtime-copies.js --write --force`, then
  `npm run check-runtime-sync` before treating a visual/perf result as final.
- Adding a new Python owner-review/runtime module is a two-step sync change:
  add it to `scripts/runtime-sync-manifest.json`, then update the runtime
  manifest whitelist/count in `tests/test_regression_runtime_mirror_coverage.py`.
  Otherwise `check-runtime-sync` can pass while coverage correctly flags the
  module as an unapproved mirror leak.
- Pytest capture may fail on this Windows workspace with "No usable temporary
  directory found" even when `C:\tmp` or `output\temp` exists. Rerun focused
  pytest checks with `-s` before treating it as a code failure. This showed up
  during the Weather & Age pass.
- Monolithic contract wrappers preserve only known custom markers. If a new
  category adds a source-owned/provenance marker and tests see it disappear
  after `_ensure_expansions_loaded()`, check
  `_spb_wrap_monolithic_paint_contract` and `_spb_wrap_monolithic_spec_contract`
  first and explicitly copy that marker onto the wrapper.
- If a monolithic paint/spec pair shares expensive procedural fields, cache
  same shape/seed fields across the paint and spec call. Brushed & Machined
  crossed the >5s red flag at 2048 until the shared brushed/machined field cache
  avoided recomputing the same full-size machining fields.
- Effects & Vision scene-style finishes can still pass visual metrics while
  burning time on oversized semantic geometry. In the May 6 wave 1 pass,
  `graveyard` and `reaper` stayed above 6s until their tombstone/scythe/hood
  fields were built at a bounded semantic scale and full-resolution
  lichen/thread/spark micro overlays were added afterward.
- A 512-clean Effects & Vision finish can still fail 2048 micro-detail if the
  upsampled semantic field is carrying too much of the texture. In the May 6
  wave 2 pass, `gargoyle` needed more native full-resolution grit/pore energy
  after the 2048 Workbench flagged weak stone micro despite clean 512 checks.
- Spec overlay patterns can be visually recognizable but still fail as
  owner-scale material if broad semantic fields dominate the signal. In the
  May 6 spec-overlay pass, `electric_branches`, `tire_smoke_residue`, and
  `galaxy_swirl` needed bounded concept carriers plus native full-resolution
  micro events; `galaxy_swirl` also needed a smaller semantic carrier to stay
  inside the 512 hot-path budget.
- Do not copy the Viva Mexico masterclass idea as "boost metallic on every
  detected ridge." The May 6 Paradigm base pass produced repeated red
  M-channel lines because a shared helper pushed M on all edges. Translate
  masterclass logic into material-specific M/R/CC profiles first, then inspect
  the spec contact sheet for channel-color artifacts before generating 2048.
- Effects & Vision shared spec helpers can inject diagonal pin-line DNA even
  when the paint concept is not diagonal. In the May 6 wave 4 pass, `hellhound`
  needed a custom spec path instead of the shared `_spec_from_fields` helper so
  claw, paw, ember, and hide material events stayed local to the concept.
- Sine-hash "random" noise can create diagonal moire at 2048 even when 512
  looks clean. In the May 7 Effects & Vision tail pass, `rust` needed true
  deterministic random pit/grit fields plus bounded semantic corrosion blobs;
  `_hash_noise` and full-size semantic fields caused hidden diagonal texture
  and >5s render times.

## Work Loop

1. Read `SPB_LINEAR_HANDOFF.md`.
2. Read this file.
3. Read `docs/SPB_VISUAL_FINISH_NONNEGOTIABLES.md`.
4. Inspect git status.
5. Inspect Linear.
6. Pick one bounded active category from SPB-67 and the active scorecard.
7. Preassess render time, similarity/redundancy, detail scale, and spec quality.
8. Write a one-sentence concept/motif/material plan per finish before coding.
   If that sentence could describe another finish, the idea is too generic.
9. Rebuild source renderer logic, not wrappers.
10. Sync runtime mirrors.
11. Run focused tests and runtime verification.
12. Generate 512/2048 Workbench review page.
13. Update Linear using Focus/Done/Verified/Risks/Next.
14. Check whether the category earned hidden spec motifs or richer microflake
    channel variety, and add them where they fit the finish identity.
15. Stop/checkpoint with the review path and recommended next category.

## Definition Of Review-Ready

A category is review-ready only when:

- Active entries render without errors.
- No obvious same-DNA duplicates remain.
- Details fit 2048 full-car scale.
- Specs mimic paint and use rich channel variation.
- Render times are within budget or known risks are called out.
- Runtime mirrors are synced.
- Tests or targeted runtime checks were run.
- A Workbench page exists for owner review.
