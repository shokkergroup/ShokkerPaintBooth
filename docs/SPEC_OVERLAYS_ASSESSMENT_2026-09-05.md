# SPEC PATTERN OVERLAYS — assessment and rebuild plan

2026-09-05 · Owner-requested analysis · Production renderers, catalogs and picker unchanged

**Recommendation: overhaul the experience and the material construction together.** The existing system is fast and capable of preserving paint, but its previews, material behavior and library organization do not provide a dependable way to choose a surface treatment. More entries alone would compound those problems.

Interactive evidence: [SPEC OVERLAYS assessment](../SPB_AUDIT_spec_overlays.html). Measurements, existing rendered samples and isolated export fixtures: [`_spec_overlays_audit_work` archive](../_archive/root_cleanup_2026-09-05/lane_work/_spec_overlays_audit_work/). Reusable inventory/native probe: [`scripts/spb_spec_overlay_assessment.py`](../scripts/spb_spec_overlay_assessment.py).

## What the current app actually contains

| Measured item | Current result | Implication |
|---|---:|---|
| Visible overlays / backend IDs | 181 / 254 | All visible IDs resolve; retain hidden/legacy ID compatibility. |
| Picker categories | 25; five contain one item | Navigation is fragmented. |
| Semantic archetypes | 91 for 181 choices | Significant construction reuse; labels alone do not establish diversity. |
| Visible renderer implementation | All 181 use `overhaul_2026` | Older functions in the large catalog file are not the live visible implementations. |
| 2048² renders | 181/181 finite, correct three-channel output | The renderer foundation is functional. |
| Renderer time: median / p95 / maximum | 0.157 / 0.254 / 0.433 seconds | Keep its bounded, vectorized approach; timing excludes composition, export and PNG evidence writes. |
| Entry-specific opacity, blend and range defaults | None of the 181 declare them | Every visible treatment starts at normal / 50% / range 40. |
| Material family changes over eight tested seeds | 90 of 181 | For these entries, a seed can change the material palette class as well as geometry. |

The existing subjects include recognizable scales, brickwork, checks, chains and brush marks. There is valuable work here. The problem is treating every subject as a variation of the same material-generation process.

### 1. The preview does not explain the result

The normal split card shows a grayscale visualization beside a colorful combined map. These are **overlay control fields**, not the final spec values on the selected base.

- The grayscale route averages metallic, roughness and clearcoat fields, then amplifies that average. Distinct channel features can cancel each other.
- The combined route displays the raw three fields as RGB and describes them as the actual on-car material spec. Composition instead adds changes to the existing base, applies strength/range, transforms clearcoat differently and clips the output.
- The older three-panel route also averages the three fields. Its M and R panels are identical; Cc is the inverse average. Both live HTTP probes confirmed identical M/R pixels outside the text labels. The normal card uses the combined route, but the older route remains available to other preview paths.
- Native renders and picker renders are generated separately. With the same UI-default parameters at both sizes, their mean absolute difference after reducing the native output to picker size was **28.51/255 median** across the catalog. This isolates the resolution difference; actual HTTP thumbnail routes also omit the UI-default parameter dictionary. This is a consistency diagnostic, not a visual-quality score.
- Holding the input field and size constant, the raw RGB map differed from the engine-applied result on a neutral `(128,128,128)` material by **86.32/255 median**. That demonstrates why “raw overlay” and “applied spec” must be labeled differently.

Live combined previews for Hex Cells and Holographic Oil Circuit matched the current direct renderer exactly. Those two results were **not stale-cache artifacts**. Separately, the preview function fingerprint follows the closure/ID but does not include the global renderer and semantic-module dependencies; future shared renderer edits can leave cache invalidation incomplete.

### 2. Some different names lead to effectively the same structure

A bounded comparison examined **154 pairs sharing an archetype**, using the project's channel/palette-invariant boundary map, rotations/reflections and phase alignment. It found **15 pairs at or above 0.68**, plus two in the 0.55–0.68 review band.

The clearest example is **Teal Hex Haze versus Hex Cells**: 0.993 on the native crop and 0.989 at picker size. Their visible geometry is almost the same; Scorpion Ember Hex also resembles this cluster. Fish Scales and Titanium Heat Fishscale scored 0.849 on native crops. Several other pairs only collide at picker size, which matters because the picker is the product customers use to distinguish them.

This is a **screening result**, not certification of every duplicate or a completed library ship gate. It covers same-archetype pairs and combined local render output. A promotion audit must cover all pairs, each channel, standard and picker assets actually served by the app, and direct visual review. The contact sheet supports rebuilding the hex cluster; no existing entry was deleted or renamed during this assessment.

### 3. Material detail follows a shared recipe

Every visible overlay starts with a subject-specific scalar field. A common helper derives metallic from the core/smoothing, roughness from inverse core/directional edges, and clearcoat from cross-edges and displaced relief. Eight shared material palettes then map those fields to intensities. A few IDs receive additional shared relief, and one receives a specific exception.

This produces many numerical shades, but **numerical shade count is not the same as purposeful material detail**. A fiber crown, a resin pocket, a fracture wall and a polished rim should have their own material relationships. They should not all inherit the same derivative formula.

The 2048² output is constructed on a maximum 768² working grid and linearly enlarged. That is economical, but an 8-pixel feature has only about three working samples. Native-detail and picker proofs are needed before accepting a design whose small features depend on several distinct internal edges. The lowest measured native channel standard deviation was 14.73/255; the historical header's channel statistics must not be substituted for today's native-output measurements.

### 4. Stacking needs a consistent, explicit contract

The actual legacy behavior is additive for “normal.” UI 50% becomes `sqrt(0.5)`, about 70.7%, inside composition. Clearcoat additionally receives a sign inversion, square-root polarization and 2.5× gain. These choices affect appearance substantially, yet every entry starts with the same defaults.

Verified cases:

- **Paint preservation passes the bounded export check.** On a conventional metallic base and ASTRA Cobalt Guillotine, actual 512² paint TGAs were byte-identical with zero, one and five overlays; the corresponding spec TGAs changed. This is two base scenarios, not certification of every zone/layer/export route.
- On `f_electroplate`, `f_galvanized` and `f_hot_dip`, a clearcoat-only Hex Cells overlay changed the single composer but changed **nothing** through `compose_finish_stacked`. The stacked call omits the scalar-clearcoat fallback used by the single call. The reproduction calls the public stacked composer with an empty regular-pattern list to isolate this path.
- Neutral `(0.5,0.5,0.5)` and zero strength preserve a midrange material; explicit single-channel selection preserves the other channels in the helper probes.
- A separate no-coat edge case fails: a clearcoat value of 0 becomes 16 inside the helper even with zero opacity. That is a helper-level reproduction, not an assertion that every full export takes this path.
- Repeating Hex Cells five times on a neutral fixture pinned 62.7% of metallic pixels and 88.3% of clearcoat pixels to a channel limit. This deliberately repetitive stress case shows how stacking can flatten detail; it does not describe every five-overlay combination.
- Overlay composition uses Python's process-dependent `hash(id)` in its seed. Two fresh processes with `PYTHONHASHSEED` unset produced different seeds and different Hex Cells arrays for the same requested seed. The running server was not restarted. Saved recipes need explicit stable seeds and a compatibility policy before changing this behavior.

The blue channel also needs an explicit **no coat** state. iRacing documents 0–15 as no coat, 16 as maximally shiny coat, and 255 as no shine. Metallic changes can alter the apparent paint color even when paint pixels are untouched. These are documented material interactions, not evidence of actual geometric embossing or guaranteed color flips. [iRacing clearcoat documentation](https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-), [iRacing paint textures](https://support.iracing.com/support/solutions/articles/31000153524-paint-textures).

### 5. Categories mix several different organizing systems

Current headings mix geometry, materials, effects, themes and development history. “Source Pattern Plates” and “Definitive Spec Replacements” expose provenance. Predator Skins and Dangerous Animals overlap. Holographic/Color-Shift labels can imply an effect that has not been demonstrated on the car. Color names such as Teal or Pink are also poor primary labels for a spec-only treatment.

The overlay picker already has search, favorites and ratings. Its separate narrow popout, category tabs and accordion/card implementation nevertheless differs substantially from the large Bases picker. Copying its CSS would perpetuate two interfaces that drift apart.

## Proposed replacement experience

Use the **same Bases picker component and navigation**, fed by a spec-overlay catalog adapter: identical category tiles, category entry/back, search, favorites, sorting, card sizing, focus/keyboard behavior, close/Escape and scroll restoration. Preserve selection/application semantics appropriate to adding an overlay. Extract shared behavior into small modules; do not append another large picker to `paint-booth-2-state-zones.js`.

Each card should show **surface detail and the applied spec on a consistent reference material**. Opening a card should let the user preview it on their current paint with a before/after comparison. Preserve the user's paint bytes throughout. M/R/Cc channel inspection and raw control fields belong in an optional inspector, accurately labeled. A 2D lighting illustration must be labeled as an approximation; real iRacing views remain the appearance check.

The normal stack controls should be simple: **Strength, Detail Size, Rotation, Metal/Roughness/Coat**, with clear per-overlay defaults. Add/reuse reorder, duplicate, mute and solo controls, and make the current five-overlay limit visible. Strength must behave monotonically, zero must do nothing, and size must preserve the promised fine construction. Advanced controls can expose channel response and clipping without filling the main workflow with implementation terms.

### Ten primary families

| Family | Distinct construction to pursue |
|---|---|
| Machined & Brushed | Tool entry/exit marks, interrupted cuts, lapping, weld crowns and directional polish |
| Weave & Composite | Different over/under topologies, tow bundles, seam junctions, resin pockets |
| Crystal & Mineral | Competing growth fronts, terraces, cleavage, twinning and inclusions |
| Skin & Cellular | Denticles, pores, scutes, membranes, ridges and cell connections |
| Liquid & Coating | Menisci, wet/dry boundaries, evaporation remnants, droplets and coating islands |
| Crack & Weather | Crack hierarchies, delamination, corrosion fronts and worn edges |
| Optical & Interference | Distinct interleaved gloss/matte structures; appearance claims require car evidence |
| Engraved & Ornamental | Engraved intersections, chased recesses, interlace and compact ornamental relief |
| Track & Motorsport | Tire-contact traces, local wear, technical weave and concealed racing motifs |
| Experimental Structures | Aperiodic tilings, branching networks, labyrinths and topology-driven material patterns |

Use **effect tags**—subtle reveal, strong metal contrast, matte/gloss, coat-only, directional, irregular, dense—to cut across these families. Theme tags can retain Rising Sun, Gothic, Voodoo or patriotic collections without making a second competing hierarchy. Curated theme collections must contain genuinely distinct constructions.

## Twelve design briefs to prove the new standard

These are proposed designs, **not finished assets or validated identity contracts**. Each requires reference research and an executable identity contract before rendering. All primitive features stay within 8–32 pixels at 2048²; long forms are assemblies of fine features. The five marks in each row must be visible and purposeful, not decorative noise added to satisfy a count.

| Design / family | Five purposeful feature types | Its material binding |
|---|---|---|
| **Toolpath Reversal** / Machined | Cut segments, entry crescents, exit scallops, overlapping lands, compact burrs | Exposed lands own metallic peaks; cut floors and burrs have separate roughness tiers; coating follows protected lands. |
| **Braided Junction** / Weave | Overpassing bundles, underpassing bundles, stitch collars, loose fiber ends, resin pockets | Bundle crowns, shadowed crossings and resin each receive different M/R/Cc states; no generic crosshatch overlay. |
| **Crystal Front** / Mineral | Nuclei, growth terraces, twin seams, interstitial pockets, chipped tips | Terrace generations and twins drive metal/roughness differences; coat continuity breaks at chipped tips and pockets. |
| **Denticle Armor** / Skin | Individual plates, split keels, root collars, abrasion patches, between-plate pores | Keel crowns polish; roots and pores scatter; abrasion locally removes the coating response. |
| **Tidal Meniscus** / Coating | Contact-line arcs, receding islands, pinning points, bead clusters, residue rings | Coat owns wet-film edges and islands; roughness follows residue; metallic modulation remains subordinate. |
| **Crazed Porcelain** / Crack | Primary fissure segments, secondary checks, curled glaze lips, pore clusters, exposed chips | Glaze, crack floors and exposed substrate have distinct material identities; joints are not a rainbow contour field. |
| **Paired Facet Lattice** / Optical | Alternating platelets, bevel bands, junction knots, etched notches, sparse polished tips | Interleaved sharp/broad response areas attempt strong highlight exchange. This is static M/R/Cc construction, not new surface normals. |
| **Security Guilloché** / Engraved | Interlaced arclets, crossover saddles, recessed knots, beaded borders, burnished crests | Rough grooves against metal crests; coat breaks and junction states distinguish it from repeated sine waves. |
| **Pit Lane Ghost** / Motorsport | Micro-check packets, staggered tick clusters, corner tabs, wear scuffs, polished witness dots | A coat-led hidden racing motif with a restrained roughness difference; M variation follows the witness details. |
| **Aperiodic Alloy** / Experimental | Unequal small tiles, multiway junctions, inset windows, interrupted bridges, corner scars | Tile role and junction topology assign material states; no shared periodic carrier or palette-only variants. |
| **Diatom Sieve** / Cellular | Perforation rows, radial struts, valve rims, bridge ribs, scar plugs | Pore interiors, struts and rims have separate material tiers; coating continuity differs around plugged pores. |
| **Weld-Pool Archive** / Machined | Solidification crescents, overlap saddles, edge toes, compact spatter clusters, polished breaks | Metal follows solidified crowns; roughness distinguishes toes and spatter; coat differences follow the local process. |

## Implementation order and acceptance

1. **Freeze compatibility and correct preview/composition contracts.** Capture current saved-recipe/export fixtures; introduce explicit overlay version and stable stored seed. Resolve scalar-coat parity, neutral/zero/no-coat behavior, defaults and cache dependency fingerprints. Old recipe IDs and responses must remain reproducible through an explicit legacy path; never silently reinterpret all existing recipes.
2. **Unify the picker.** Use a shared Bases component with an overlay adapter, then test category/back/search/favorites/keyboard/application and cancellation in the real app. Keep internal review tooling out of the customer browsing flow. Bake thumbnails from canonical output and cache an actual applied result keyed by overlay version, parameters, seed and reference material.
3. **Build the twelve proofs.** Each owns its geometry, feature masks and per-feature material rules. Version 2 should provide explicit feature coverage plus signed per-channel changes or masked material targets; transparent areas preserve the base. Any behavior like adaptive headroom preservation must be explicit and preview/export-identical, not a hidden remapping. Do not retrofit this by silently changing legacy blend modes.
4. **Validate through the whole app.** Native and picker detail, name-with-title-hidden review, every M/R/Cc channel, actual applied/exported specs, paint-byte preservation, masked boundaries, base stacks, reordered overlays, reload/restart determinism and clipping. Use contrasting plain and intricate bases; test close and race-distance daylight/glancing/overcast views in iRacing when its viewer is available.
5. **Expand only after the proof set separates clearly.** A useful planning target is approximately **120 accepted constructions across the ten families**, with old IDs retained for compatibility. This is a recommendation, not a count already built or a reason to accept duplicates. Keep/rebuild/legacy-only decisions should follow the modern live similarity gate and direct visual review.

Every new or modified design must meet the owner's identity law, five-purposeful-mark rule, fine-feature rule and M7 ≥85 ship bar. Use the spec-driven scoring treatment where applicable; include direct per-channel strength/span evidence. Similarity ≥0.68 rejects; 0.55–0.68 requires side-by-side owner-eye review. Metrics do not overrule the name test or the owner's eye. Speed measurements must include the relevant composed path as well as isolated renderer time.

## Audit limits and handoff

The focused existing tests produced **18 passed / 19 failed**. Two failures pin obsolete 2D-only output/source-string assumptions. The channel-inference suite also contains outdated per-ID/default expectations, plus a clearcoat-routing behavior failure that warrants separate diagnosis. These results are not 19 newly introduced bugs and are not a green regression baseline. Replace brittle source/docstring checks with saved-recipe and exported-pixel checks while retaining useful coverage. Detailed output is archived as `pytest.txt`.

No M7 promotion was run: this task analyzed existing assets and changed no finish. No iRacing appearance claim has been validated in this audit; the viewer belongs to the active ARCA lane. No app renderer, category or picker has been replaced yet. This report, the interactive evidence page and reproducible probes are the completed analysis deliverables.

Implementation entry points: `engine/spec_pattern_families/overhaul_2026.py` (`_render`, `_semantic_channel_fields`, `_material_for`); `semantic_overlays_2026.py`; final catalog override in `engine/spec_patterns.py`; `engine/compose.py` (`_apply_spec_pattern_to_channels`, both public composers); `server.py` (`_generate_spec_preview_image`, `_generate_spec_visual_image`, `_generate_spec_combined_image`, `_get_fn_hash`); picker functions near line 12765 onward in `paint-booth-2-state-zones.js`; shared Bases modules under `js/zones/swatch-popup*` and `js/spb-finish-atlas.js`. Extract small modules at these boundaries; do not grow the legacy files further.
