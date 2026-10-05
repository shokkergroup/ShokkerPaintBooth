# ASTRA: rebuild for recognizable materials and readable fine detail

22 September 2026. Proposal requested by the owner after the Intent-Fit audit. No renderer, palette, thumbnail, catalog slot or ranking is changed by this document.

**Recommendation:** retain ASTRA's fifty identities and five existing lanes as the planning inventory. Rebuild its visual organization and material authoring around six demonstrator finishes first. Expand only after the demonstrators prove the improvement on the car. Treat all fifty as review candidates, with preserve/refine/rebuild decisions per finish; do not assume fifty replacements are necessary.

The intended outcome is a category whose finishes have distinct material personalities, readable subject cues, useful quiet areas and finely worked surfaces. A buyer should see a difference in construction and response without needing the title or an enlarged spec bitmap.

## Evidence behind the proposal

The prior audit measured current picker responses for all fifty ASTRA bases as part of the complete base census. For this proposal, the current source/helper architecture and all five archived native contact sheets were inspected. The archived sheets support the construction diagnosis, but they are historical evidence, not a fresh native/export or on-car qualification of all fifty.

| Finding | Evidence | Design consequence |
|---|---|---|
| Repeated local stamps | 11/40 expansion modules use `frames()`, a regular rectangular lattice, with cell pitches around 19–32 px; Janus Blades, Switchyard, Chevron, Scales, Origami and Zipper visibly repeat | Changing the stamp shape, shear or palette does not solve the wallpaper rhythm. Redesign placement and relationships. |
| Irregular placement alone is insufficient | 29/40 use `sites()`, but each still constructs a small local motif in a densely populated territory | Aperiodic confetti can feel as monotonous as a grid. Different finishes need different connectivity, spacing, grouping and empty-space structure. |
| Shared material equalization | All forty use `pack()` in `wave2/materials.py`. Its final loop stretches M to 4–255 and Rough/Cc to 16–255 whenever a channel varies | Absolute material intent can be lost even when spatial masks differ. A narrow roughness palette should remain narrow when that is the design. |
| Coat variation can dominate the named material | Non-MAD `pack()` combines 25% role coat prior with 75% per-object coat tier before final equalization | The role's lacquer, exposed metal or substrate identity needs authority over the coat distribution. |
| MAD SCIENTIST shares a powerful rainbow treatment | Its common branch sets `s = p*.82 + states[lab]*(.18/255.)`, then expands the channels. Native contact sheets visibly show very similar paint/spec chromatic patterns | Strong FOLLOW or millions of RGB values do not prove meaningful membranes, nuclei, crystals and conductors. Give those features actual material roles. |
| Roughness is solved from packed-spec display luminance | Non-MAD branches use RGB luminance weights on M/Rough/Cc to solve a desired relation to pigment value | Physical control channels are not display colors. Replace that convenience with feature-specific material laws. |
| Motif size hides smaller internal marks | Janus's cell is 29×23 native-coordinate px; `abs(v)<.12` gives a nominal collar band 0.24×23≈5.5 px, before clipping/reconstruction | Measure each actual feature width, not only the cell pitch. Small role regions disappear or blend together. |
| Daytime flip remains unproven | Original expansion report explicitly documents white glint washout and weaker chromatic separation after reduction | COLOR SHOXX must demonstrate colored response under matched actual lighting. Broad map ranges and a moving white highlight are insufficient. |

This is evidence of a common visual treatment and readability risk, not proof that all forty use identical geometry. The earlier 1,225-pair comparison reported separation; it did not establish that fifty different micro-patterns were equally readable, name-true or materially convincing.

## 1. Retool the composition rules

### Small features, larger organization

Keep individual authored primitives in the owner's 8–32 px range at 2048², and validate feature widths after rasterization. A grouping can occupy more space through the arrangement of many fine marks; it must not become a larger solid stamp or broad shared wave painted over every finish.

Use three levels of visual importance:

- **Named construction:** the blades, reef growth, folds, cells or tracks that communicate the subject.
- **Supporting construction:** seams, branchlets, junctions, fractured edges and secondary interactions that make it believable.
- **Surface finish:** fine pores, scratches, etching, flecks or polish marks suited to that material.

At close range, all three levels reward inspection. At ordinary viewing distance, the first level remains organized enough to recognize. At picker scale, the overall character and dominant relationships survive even though individual 8px features cannot remain resolved.

Dense detail stays; equal loudness does not. Redistribute some competing high-contrast stamps into subtler feature-bound detail. Give important motifs breathing room without leaving large untreated gaps or increasing primitive size. Different finishes need different coverage: a woven surface may properly be dense, while an aperture-based design needs substantial quiet space.

### Author topology before decorative marks

Each finish must declare its spatial construction: branching network, interrupted routes, layered fragments, growth fronts, overlapping sheets, nested cavities, braided strands, directional wear or another subject-appropriate system. Author connections and terminations first. Then populate their surfaces.

Do not make every design an independent object inside a nearest-site cell. Reusable mathematical utilities are fine; a common finish-level placement field or repeated composition is not. Jitter, random rotation and a different seed alone do not create a new construction.

Regularity is allowed when it communicates the name. A zipper needs interlocking order and a weave needs over/under order. Their distinctive relationships must remain visible; gratuitous randomness would make them worse. Routes extending across the canvas are assembled from fine authored segments, with distinct arrangements per finish.

## 2. Retool materials and color

Replace the common visual finishing recipe with a neutral output packer and a **per-finish role table**. Each named feature supplies its pigment family, M/Rough/Cc center, justified tier range, local surface behavior and relationships to adjacent features. Retain shared caching, hashing, clipping and export utilities.

- Stop global full-range equalization. Preserve authored material neighborhoods; correct a weak effect in the responsible feature, not by expanding every channel.
- Stop treating packed spec luminance as a physical target. The lacquer/metal/water/wax role determines roughness and coat.
- Replace the MAD paint-to-spec mapping with semantic feature masks. Shared edges can align perfectly while paint RGB and material channels differ substantially.
- Keep many meaningful tiers where intended. Use smooth, restrained tiers on wax, broad contrasts between exposed alloy and insulating substrate, and polished caps on selected facets. Count useful states occupying meaningful features, not raw RGB combinations.
- Judge the actual shader response of blue-channel clearcoat using SPB's existing encoding and anchors. Do not interpret brighter blue as stronger coat.
- Make color families belong to features. Add within-family shade depth and purposeful accent colors without cycling every feature through the whole rainbow. Preserve intentional complementary pairs in COLOR SHOXX.

Examples of different material personalities: matte wax over resin; polished conductive paths in ceramic; rough coral-like growth beside smooth dark-water pockets; satin membrane around more reflective nuclei; brushed folds with polished hinges. These are art/material concepts, not claims of physical displacement, translucency, emission or a new iridescence shader.

## 3. Six demonstrators

These form a comparison set across different construction and material problems. They are proposals, not new owner-approved designs. Existing versions remain the before references, and IDs/names remain stable.

| Pilot | Construction to build | Five or more purposeful feature types | Material and color behavior | Proof of improvement |
|---|---|---|---|---|
| **Janus Blades** | Unequal, interrupted blade groupings with visible lacquer channels; varied spacing and genuine overlap, no staggered all-over stamp grid | Blade faces, cut edges, concave heels, collars, forked tips, lacquer gaps | Scarlet lacquer owns dielectric regions; cobalt owns reflective blades; edge polish and machining differ. Multiple shades within each family | Blades and lacquer remain separable after reduction. Directional grid repetition falls. Colored response is distinguishable from white glare on the car |
| **Pipeline Royale** | Distinct current paths assembled from fine curled segments, with breaking fronts and quieter water between them; avoid evenly scattered shell-like curls | Crest hooks, inner lips, foam beads, broken wakes, return eddies, water pockets | Turquoise/deep-blue water, cream foam; material contrast keyed to wet surface, foam and restrained highlight populations | Reads as moving surf rather than a field of rosettes; crest organization survives distance |
| **Neuron Carnival** | Connected branching networks with varied node spacing, short axon segments, forks and clear termination rules | Cell bodies, axons, dendrites, synapses, membranes, branch collars | Different pigment families identify network populations. Membranes and nodes own material states; spec does not reproduce the paint rainbow | Connections are traceable; it differs structurally from isolated Petri colonies and chromosome forms |
| **Causal Origami** | Connected folded micro-facets meeting at unequal junctions and interruptions; remove the repeated diagonal ribbon tile | Faces, mountain folds, valley folds, hinge cuts, tab ends, edge scuffs | Silver satin faces, violet undersides, ion-blue hinges; high polish reserved for selected exposed folds | Fold direction and front/back relationships are legible; no endless diagonal checker rhythm |
| **Surf Wax Ritual** | Directional use/wear zones built from short comb marks, scraped clear pockets and fine crumbs rather than repeated chunky cells | Wax crumbs, comb strokes, scrape lips, resin openings, compressed patches, fine scuffs | Chalky mint/cream wax over warm resin; restrained metal content, deliberate roughness and coat differences | A quieter finish still looks detailed and wax-like; the new metric does not demand rainbow spec |
| **Negative Space Engine** | Connected struts enclose unequal apertures; voids lead the design and junctions form secondary structure | Apertures, fine strut segments, joints, end caps, inner lips, inset plates | Copper struts, subdued dark wells, selective silver plates; polished and satin populations have clear ownership | Apertures survive reduction; open area is intentional architecture rather than missing detail |

For each pilot, compare two authored arrangements, such as more open versus more connected. This tests a specific composition decision; do not generate a seed lottery or count alternatives as new finishes.

## 4. Direction for all fifty

These are design briefs for the review queue, not assertions that each current finish fails. Preserve successful ideas and reduce unnecessary change. The original ten were explicitly preserved during the expansion; keep their baselines and evaluate them individually before any later implementation touches them.

| Lane | Finish | Proposed construction focus |
|---|---|---|
| Original ten | Event Horizon | Unequal aperture groups, interrupted orbit segments and bridges; break identical disc rows |
| Original ten | Quasicrystal Crown | Aperiodic facets with a readable hierarchy of seams and junctions; reduce equal-brightness clutter |
| Original ten | Gravity Loom | Preserve three-way over/under identity; strengthen knot, strand and gap separation |
| Original ten | Phoenix Ceramic | Connected repair seams separating enamel regions; let glaze, copper repair and pores have different roles |
| Original ten | Sovereign Nacre | Slipped overlapping tablet arrangements with distinct edges and interruptions; avoid a brick-wall impression |
| Original ten | Magnetic Regalia | Unequal groups of droplet crowns and connecting wet saddles; reduce repeated emblem appearance |
| Original ten | Meteorite Royal | Intersecting etched blade families with clipped growth boundaries; improve alloy/matrix distinction |
| Original ten | Cryogenic Bloom | Branching dendritic growth with visible tips and unfilled pockets; test the current repeated loop rhythm |
| Original ten | Chronograph Gold | Distinguish overlapping tool-cut arcs, stopped passes and spindle detail; use controlled metal shades |
| Original ten | Velvet Supernova | Directional fiber blooms with quieter inter-bloom fibers; avoid isolated identical floral stamps |
| COLOR SHOXX | Janus Blades | Interrupted, overlapping blade groups; pilot above |
| COLOR SHOXX | Chromatic Undertow | Connected opposing currents with unequal splits and returns, rather than scattered hooks |
| COLOR SHOXX | Spectrum Guillotine | Cut shutter fragments and severed hinges with coherent cut direction; remove diagonal stamp grid |
| COLOR SHOXX | Chromatic Switchyard | Routed connections, actual junction decisions and dead ends; no repeating plus-sign pavement |
| COLOR SHOXX | Bipolar Cyclone | Opposing groups of rotor fragments with readable wakes and open centers; avoid uniform rosette density |
| COLOR SHOXX | Prism Rebellion | Unequal facet adjacency and fracture junctions; make competing prism populations legible |
| COLOR SHOXX | Dichroic Rivets | Partial overlap, recessed sockets and varied clusters; preserve rivet identity without dot wallpaper |
| COLOR SHOXX | Switchblade Chevron | Linked fork assemblies with starts, breaks and directional changes; keep the chevron meaningful |
| COLOR SHOXX | Duality Scales | Overlap following distinct local growth directions; exposed tips and recessed roots remain different |
| COLOR SHOXX | Polarity Lace | Continuous open lace connections with varying openings; resolve crossings and avoid isolated saddle confetti |
| SURFS UP | Pipeline Royale | Crest fronts and linked current segments; pilot above |
| SURFS UP | Reef Cathedral | Branching reef structures with tip growth and mineral clearings; distinguish it from Kelp's stalk topology |
| SURFS UP | Tidal Lacework | Interconnected irregular foam membranes, ruptured edges and dark pockets; avoid regular circular cells |
| SURFS UP | Surf Wax Ritual | Fine directional wear and deposited wax; restrained pilot above |
| SURFS UP | Wipeout Paisley | Nested broken drop relationships and asymmetric eyes; vary grouping while retaining paisley identity |
| SURFS UP | Kelp Couture | Traceable branching stalks with alternating leaves and floats, with current-aligned openings |
| SURFS UP | Boardwalk Pinlines | Fine segmented pinline runs with unequal starts, returns and worn interruptions; avoid repeating board stamps |
| SURFS UP | Volcanic Break | Broken layered reef edges with connected tide gaps and localized copper cracks |
| SURFS UP | Abyssal Lanterns | Unequal bell groupings, coherent cilia and trailing fragments in quiet dark water; no claim of emission |
| SURFS UP | Sea Glass Confessional | Distinct tumbled shard edges and contact relationships; preserve softer sea-glass shades and mineral separation |
| MAD SCIENTIST | Cytokinesis Candy | Different division stages connected by convincing necks; separate membrane, interior and nuclei |
| MAD SCIENTIST | Quantum Petri Carnival | Interacting colony boundaries, contained reaction fronts and local exclusions; no generic rainbow cells |
| MAD SCIENTIST | Chromosome Riot | Readable paired arms, centromeres and varied group relationships; keep it distinct from Neuron's network |
| MAD SCIENTIST | Plasma Sutures | Branching cuts and cross-stitches with irregular spacing; material changes follow injury and repair features |
| MAD SCIENTIST | Bismuth Delirium | Unequal nested hopper cavities and stepped fine rims; distinguish crystal faces from cavities |
| MAD SCIENTIST | Strange Attractor | Connected fine return paths and bifurcation relationships; avoid a pile of unrelated curved fragments |
| MAD SCIENTIST | Neuron Carnival | Connected neuronal topology and semantic material roles; pilot above |
| MAD SCIENTIST | Xenobot Orchard | Unequal grouped lobes with cilia and bud interactions; each organism remains readable against its substrate |
| MAD SCIENTIST | Fermion Foundry | Interlocked chamber walls, necks and openings; make foundry connections different from cell growth |
| MAD SCIENTIST | Chromatic Centrifuge | Eccentric fine rotor segments with sorted material populations and clear gaps; no uniform crescent scatter |
| FUTURE SHOXX | Causal Origami | Connected folded facets and varied junctions; pilot above |
| FUTURE SHOXX | Photonic Switchboard | Unequal routed bus connections with distinctive endpoints, couplers and isolators; separate from Chromatic Switchyard |
| FUTURE SHOXX | Negative Space Engine | Aperture-led structure; pilot above |
| FUTURE SHOXX | Temporal Braille | Small code groupings with deliberate spacing and separators; no all-over rounded-pad grid |
| FUTURE SHOXX | Klein Circuit | Coherent return-route relationships with visible crossings and interrupted boundaries; material differentiation at bridges |
| FUTURE SHOXX | Auxetic Exoskin | Deforming re-entrant connections and unequal openings; let joint relationships distinguish it from a checker |
| FUTURE SHOXX | Memory Metal Zipper | Interlocking tooth runs, staggered engagement and occasional open seams; regularity serves the mechanism |
| FUTURE SHOXX | Orbitless Navigation | Linked waypoints with route decisions and sparse directional fragments; avoid repeated compass icons |
| FUTURE SHOXX | Tachyon Feather | Connected quill/barb relationships and layered directional groups; polish selected edges, preserve quieter vane detail |
| FUTURE SHOXX | Programmable Matter | Connected block assemblies with attachment/release boundaries and voids; avoid endless same-sized block tiling |

Do not turn this table into fifty parameter presets of one new generator. Each construction needs its own identity contract and arrangement law. Thematic neighbors above deliberately demand different topology.

## 5. Evaluate the new failure modes explicitly

Keep Intent-Fit's seven axes, but add these diagnostics for ASTRA. Numerical pass thresholds require calibration from owner comparisons; none are invented here.

| Diagnostic | What to inspect/measure | What it prevents |
|---|---|---|
| Within-finish repetition | Autocorrelation peaks, directional spectral peaks, repeated patch matches, visible straight rows; examine native and reduced views | Distinct files can each still be repetitive wallpaper |
| Feature survival | Per-role mask widths and area; native edge separation; recognizable relationships through 2048/512/256/128/64 reductions and actual car views | Calling a 29px cell fine when its important parts are only 3–6px |
| Crowding and hierarchy | Nearest-neighbor spacing, overlap/occlusion, high-contrast edge occupancy and separation of feature levels; owner side-by-side review | Every motif and every detail competing at maximum strength |
| Actual palette survival | Which intended hue families and within-family shades retain useful area and contrast after reduction | Millions of different pixels averaging into one muddy color |
| Material ownership | Native M/Rough/Cc distributions within named masks; adjacent-role contrasts; actual light/view behavior | All channels expanded just to increase score, or paint copied into spec |
| Name recognition | Hide titles; compare subject cues against close alternatives; record the visible evidence after revealing names | A convincing paragraph rescuing an unreadable construction |
| Category contribution | Existing invariant comparisons plus whole-category silhouette, rhythm and material-response review | Fifty mathematically different variants with the same visual personality |

Repeating structures can be correct for a zipper or weave. The failure is unmotivated repeated layout, weak distinction or loss of the intended mechanism. Do not turn an autocorrelation value into a universal anti-pattern rule.

### Required comparison board for each candidate

Use the same seed, tint, strength, scale, exposure, car panel and camera conditions for before/after. Show: full 2048 paint/spec; several unscaled native crops, including quiet and busy regions; actual served standard/picker output; matched car daylight/shade/night views and normal-distance views. Include a title-hidden view, grayscale construction and per-channel spec. Do not select only the most flattering crop or replace a weak car result with an enlarged thumbnail.

If a material needs a particular lighting condition, declare it. COLOR SHOXX needs a real heading/view comparison with visible colored separation, not just moving white glare. Maintain the 2–3s standard-render budget and demonstrate actual composed exports, not only isolated module output. Preserve alpha and source-color semantics.

M7 remains diagnostic under the owner's override. A better-looking, more name-true material may have lower channel spread or fewer encoded colors. Owner review can reject a numerically distinct result, and confirmed owner approval must not be erased by the metric.

## 6. Implementation sequence after the proposal

1. **Freeze the before evidence.** Fifty current source/dependency hashes, native/current picker/export references, prior owner verdicts and protected status. Preserve old versions by revision; no duplicate category slots or destructive ID changes.
2. **Separate utilities from artistic policy.** Add a new opt-in material path for pilots; retain caching and ABI/export behavior. Do not modify `pack()` globally and unintentionally change forty finishes at once. Give each pilot explicit role masks and material rules; remove uniform range stretching and pigment-derived spec from those new paths.
3. **Build the six demonstrators.** Approve each identity contract before rendering. Compare two purposeful arrangements per pilot, maintain fine features, and select by the actual evidence board. Follow the existing local-development visibility/baking rules during an authorized implementation; mark candidates as review versions and preserve their before evidence.
4. **Review the category-wide comparison.** Put demonstrators beside all fifty old designs. Confirm improved readability, different construction and appropriate quiet/dynamic behavior. A shared new look across all six is a reason to revisit the approach.
5. **Rebuild in small batches.** Prioritize the remaining COLOR SHOXX repetition and MAD SCIENTIST material coupling, then the grid-heavy FUTURE SHOXX entries and subject-specific SURFS UP work. Review the original ten individually; preserve what already works.
6. **Promote verified improvements.** Existing stable IDs, two-copy synchronization, persistent thumbnails, current API/output checks, export identity, render budget and owner judgments recorded per revision. No credit for merely recoloring or reseeding an existing construction.

The first decision point should be six demonstrably improved materials with different personalities. That is enough evidence to establish a useful rebuild method before committing the entire category to it.

## Source references

- `engine/expansions/astra/wave2/materials.py`: `frames`, `sites`, `pack`, material/paint coupling and final channel equalization.
- `engine/expansions/astra/wave2/janus_blades.py`: local cell and internal role widths.
- `engine/expansions/astra/common.py`: original-ten shared shading and binding utilities.
- `docs/ASTRA_2026-09-05.md`, `docs/ASTRA_EXPANSION_2026-09-05.md`: original intentions, evidence, original-ten preservation and unproven daytime flip.
- `_archive/root_cleanup_2026-09-05/lane_work/_astra_work/contact_native.jpg` and `_astra40_work/{color_shoxx,surfs_up,mad_scientist,future_shoxx}.jpg`: historical native contact sheets inspected for this proposal.
- `docs/finish_audits/intent_2026-09-22/live_census.json`, `SYSTEM.md`, `FINDINGS.md`: current picker measurements and Intent-Fit design.
