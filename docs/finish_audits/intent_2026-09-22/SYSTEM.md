# SPB Intent-Fit — proposed finish evaluation system

Designed 22 September 2026 from the current catalog, M1/M2/M5/M6/M7, Finish Law, owner protections and saved/live picker evidence. This is an audit and replacement-system proposal, not a change to production finish rankings or ship gates.

**The question is “how well does it deliver its intended experience?” More colors, more texture, more channel range and more complexity are not universal improvements.** A plain satin, polished chrome, scarred metal and exuberant holographic finish can all be excellent.

## 1. Keep quality, expression and confidence separate

Every finish gets four independent records:

1. **Intent contract:** the promised subject/process, material, color policy, geometry and behavior. Established before scoring; backed by the owner brief, current identity contract, reference and current name. A category is a suggested starting point, not a binding classification.
2. **Quality profile:** how faithfully and cleanly the finish delivers that contract, axis by axis.
3. **Expression profile:** paint richness, spatial material variation and angular/light response. Descriptive, never “more is better.”
4. **Evidence status:** what was actually observed, where, at which renderer revision, and what remains unknown. Owner approval is recorded separately from automated scores.

The catalog needs “best quiet bases”, “best colorful finishes”, “best dynamic materials”, “needs investigation” and “missing evidence” views. A single intensity-sorted leaderboard cannot serve all those jobs.

### Two different meanings of dynamic

**Spatial variation** means different material values across a map. **Optical response** means appearance changes with lighting and viewing angle. A spatially uniform polished metal can have dramatic moving reflections. A rainbow spec bitmap may give a dull or incoherent result. Measure both independently.

## 2. Per-finish contract

Extend, rather than replace, the existing `spb-finish-identity/1` record. Link its source and hash. The assessment contract stores:

| Field | Required content |
|---|---|
| Identity | Canonical surface + ID, current name and description, aliases, current groups, renderer/source revision |
| Promise | What should be recognizable; 2–4 visible cues; reference; prohibited interpretations |
| Paint policy | Preserve source color, fixed authored palette, tintable palette, two-tone, multicolor, monochrome; expected families and relative area |
| Paint detail | Uniform, subtly textured, fine structured, narrative motif; feature classes and native scale |
| Material policy | Substrate and named feature roles; expected M / Rough / Cc neighborhoods and alpha behavior |
| Channel duties | Independently for each channel: fixed, narrow, feature-varied, or broadly dynamic, with rationale |
| Binding policy | Which material follows each paint feature; documented spec-only or independent behavior |
| Optical promise | Restrained, satin rolloff, moving reflection, fine sparkle, strong shift, reveal, etc.; view/light conditions |
| Use | Full body, accent, supporting base; source-color behavior; controls that must work |
| Distinctness | Closest alternatives; unique construction or declared useful substrate/palette variant |
| Authority | Owner verdict, protected state, exceptions, approval date and covered source/output hashes |
| Calibration | Accepted and rejected anchors, metric version, target bands and provenance |

Unknown fields stay unknown. Do not classify a renamed finish from an old ID word. Do not declare a finish “plain” after discovering weak output. Changing a contract to excuse a failed result requires an explicit documented design decision.

### Starting profiles, with per-finish exceptions

| Profile | Good paint behavior | Good material behavior | Wrong improvement |
|---|---|---|---|
| Clean solid / matte / satin | Clean, stable, usually single hue; preserves intended color | Appropriate means and restrained distribution; visibly different gloss levels under matched light | Adding rainbow noise or forcing every channel across 0–255 |
| Polished chrome / mirror | Clean albedo appropriate to the promised metal | Correct metal/roughness/coat state; strong angular reflection can come from a uniform map | Treating low M standard deviation as weak chrome |
| Candy / pearl / fine flake | Controlled pigment richness; fine sparkle where promised | Substrate and flake roles, convincing depth/response; varied only on relevant channels | Inflating flakes or scattering unrelated material states |
| Brushed / woven / physical texture | Recognizable fine directional or interlocked construction | Roughness/material changes at fibers, grooves, exposed substrate | A generic grain with a new palette |
| Weathered / layered material | Believable intact, worn, exposed and oxidized regions | Each region owns a physically or stylistically justified material state | Making every rust pixel metallic to increase M range |
| Chromatic / iridescent / fractured | Promised palette and structure survive car scale | Strong intended response, purposeful tiers, no generic spec deck | Maximizing all channels regardless of mechanism |
| Graphic / theme / narrative | Recognizable visual idea, controlled palette, useful hierarchy | Feature-owned or explicitly justified supporting spec | Awarding identity because the title contains the right noun |
| Hidden / spec-led | Quiet or source-preserving paint can be correct | Spec carries the promised detail or reveal | Penalizing paint/spec busyness mismatch |

Foundation currently mixes ordinary gloss/matte/chrome with Dragon's Pearl Scale, Orchid Shift Pearl and other expressive ideas. It cannot have one blanket “quiet” target.

## 3. Quality axes

The weights below are **initial product-design proposals**, not calibrated release thresholds. Show all axis values; a composite must never hide a failure.

| Axis | Proposed weight | Evidence and measurement | Improvement when weak |
|---|---:|---|---|
| Name and idea fidelity | 20 | Blind cue review against near-neighbor alternatives; after revealing title, identify actual cues in native crops and car views. Reviewers may identify the subject family rather than guess a fanciful exact name. | Repair the construction that carries the idea; renaming is a separate owner decision. |
| Color fulfillment | 15 | Native perceptual color clusters, chroma/lightness distributions, family occupancy, within-family shades, separation after downsampling; compare with the intended palette and tint mode. | Add missing meaningful families or shades, preserve intended neutrals, improve separation and placement. |
| Material fulfillment | 20 | Native M/Rough/Cc means and distributions by named feature, material-state occupancy, channel clipping, alpha, and observed response under fixed light/view sweeps. | Correct substrate values and feature tiers; increase variation only on channels with that duty. |
| Paint–spec relationship | 15 | Feature-mask alignment, boundary agreement, per-feature material tables, multiscale envelope correspondence; inspect differences, not merely shared busyness. | Bind spec to the same rims, fibers, cuts, pores or other named features. |
| Detail and construction | 10 | Native full canvas plus unscaled crops, feature widths, density, hierarchy, seams, repetition, aliasing and distance survival. | Finer purposeful marks, more density and tier variety where needed; preserve clean surfaces. |
| On-car usefulness | 10 | Matched source templates, panel curvature, normal use distances, lighting, decal readability, controls and source-color preservation. | Improve visibility, contrast or restraint without obscuring the livery. |
| Distinct contribution | 10 | Color-invariant paint and per-channel/combined-spec comparison; nearest neighbors; native/picker/car review; material response comparison for uniform substrates. | Change repeated construction or label a useful variant honestly; do not count variants as new designs. |

Correct delivery, finite/range-valid maps, proper encoding, identity integrity, protection and freshness are separate integrity checks. Render cost is a separate usability constraint (existing 2–3 seconds at 2048² for standard finishes, measured with warmups and three timed trials). Fast rendering does not compensate for bad appearance.

### Material strength is fit, not range

For M, Rough and Cc, record mean/median, p01/p05/p95/p99, robust span, standard deviation, end-point occupancy and effective state count. Also report feature-conditioned distributions and rare-event occupancy. Global percentiles deliberately reject isolated hot pixels, but cannot judge a legitimate sparse sparkle population; measure that feature separately at native size.

Use named feature masks from the renderer where available, and independently verify those masks against output. Otherwise mark semantic alignment pending manual annotation. A renderer cannot prove its own correctness simply by emitting matching labels.

Never interpret the blue byte as a linear “more clearcoat” slider. Use the project's spec encoding/anchor rules, including the special zero state and active-coat neighborhood, and validate under the actual game renderer. Never infer material families from filtered thumbnail bytes: interpolation creates intermediate states that may never exist in native output. Spec color diversity is material diversity, not paint hue diversity.

M/Rough/Cc independence is not automatically good. Shared feature masks can correctly correlate channels. Channel swaps are not new geometry and can change material meaning disastrously.

### Score relative to an intended band

For a measurable feature with calibrated acceptable band `[L,U]`, give full credit within that band. Below L, penalize insufficient effect; above U, penalize excess. Use calibrated outer bounds for gradual penalties. `band_fit()` implements this two-sided utility. A narrow-span satin and broad-span effect can both receive full credit against different approved bands.

Do not use the catalog's own percentile ranks as acceptance targets: adding weak finishes would otherwise change the judgment of an unchanged finish. Keep fixed reference anchors and versioned units. Some variables are one-sided; model them explicitly rather than inventing a symmetric target.

### Missing evidence cannot improve a score

With normalized fixed weights `w`, verified scores `s`, report:

`lower = sum(w*s for observed axes)`

`upper = lower + 100*sum(w for missing axes)`

`coverage = sum(w for observed axes)`

These are possible-score bounds, not statistical confidence intervals and not a failing score for an unreviewed finish. A finish with only a perfect 20%-weight identity review is **unrated, possible range 20–100**, not a 100. `evidence_interval()` implements this rule. Missing critical evidence always prevents a verified ranking.

An inapplicable axis is established in the contract before measurement, with a predeclared profile-specific weighting scheme. It is different from missing evidence. Most plain finishes still have all seven axes: their identity, restraint, material, source-color relationship, clean construction, usefulness and contribution remain assessable.

### Verdicts and owner authority

Use **unrated**, **needs evidence**, **needs owner comparison**, **meets calibrated intent**, **repair candidate**, and **owner protected**. Do not invent a universal “85” replacement. Derive thresholds from owner examples and holdout validation first. A failed name test, invalid material semantics or repeated construction cannot be averaged away. An owner PASS remains authoritative; diagnostics do not erase it or trigger a rebuild.

The current owner identity similarity rules remain in force for construction-bearing designs: ≥0.68 reject/rebuild unless explicitly adjudicated; 0.55–0.68 needs direct comparison. Do not transfer those numeric thresholds to a different feature extractor without calibration. Uniform substrates require comparing material response/declared purpose, since identical empty edge maps say nothing about gloss versus matte. Palette variants can be useful catalog choices without counting as unique constructions.

## 4. Evidence collection

For every canonical finish, store a manifest containing renderer and dependency fingerprints, catalog/contract hashes, source tint, strength, scale, seed, surface, output dimensions, time, server version, requested URL, response hash and final exported paint/spec hashes.

Collect these stages separately:

1. **Catalog/availability census:** root and served catalog agreement, IDs, aliases, routes, static asset availability, legacy metric coverage. This audit implements this baseline, with a live base-picker companion.
2. **Current standard and picker outputs:** actual served images using the same tint and routing as the UI. Compare native-derived output to both; invalidate only affected entries after changes. Current HTTP output can still be stale if dependency fingerprints are incomplete.
3. **Native production output:** actual 2048² composed paint/spec, full canvas and 1:1 crops; channel images; features and material tables. Use exported composition, not only isolated renderer functions.
4. **On-car fixtures:** same car, neutral/dark/light source colors as appropriate, daylight/shade/night and multiple angles/distances. Add one second body shape to detect template overfitting. Source-preserving bases must be tested on existing multicolor paint.
5. **Owner/visual review:** blind cues, nearest-neighbor comparison, material/readability decisions and protected anchors, tied to the inspected revision.

Suggested calibration fixtures are starting designs, not claims of completed tests. Use short synchronized light/view sweeps for optical response. Compare the intended spec against a uniform-material control under the same scene; this separates paint-driven changes from material-driven changes. Record exposure/tone mapping and prohibit automatic exposure from making a weak material seem dynamic.

Existing snapshots and new renders should share seeds for reproducible comparisons. Use additional seeds for stochastic finishes to check identity stability, not to harvest a lucky example.

## 5. Calibration and resistance to score gaming

Begin with stratified owner examples covering clean bases, restrained textures, colorful effects, spec-led exceptions and rejected twins. The existing five protected Finish Law references are useful but insufficient to calibrate the plain-material end. Existing owner passes and four FLAW LAB favorites stay protected. Ask for comparative judgments only where existing evidence cannot establish preference.

Split training/holdout by renderer construction or family, not random neighboring seeds. Fit target bands and decision thresholds to the training set, then report holdout false rejection of accepted quiet finishes, false acceptance of rejected finishes, pairwise agreement and uncertainty. Show confusion cases rather than hiding them in an average.

Challenge the system with recolors, translations, flips, rotations, channel permutations, reseeds, one bright pixel, random noise, oversized detail, stale thumbnails, missing evidence and a quiet chrome control. Tests must catch meaningless score increases. Adding off-intent color or noise must not improve quality. Reusing a carrier with a different seed must not create originality credit. The included tests cover band fairness, missing evidence and hot-pixel robustness; full visual calibration is still to be done.

Never hard-code a category to 100. Never replace unknown name fidelity with keyword confidence. Never advertise a new scoring system as validated because its unit tests pass.

## 6. Turning results into effort priorities

Maintain two queues:

- **Evidence queue:** uncertainty that could change a decision. First resolve stale/runtime discrepancies, missing contracts and misclassified profiles.
- **Improvement queue:** verified promise failures. Order by owner severity, affected use cases, prevalence and estimated benefit relative to effort. Keep speculative benefit separate from measured evidence; do not fabricate usage counts.

Each action card names the finish, promised behavior, observed failure, evidence link, proposed mechanism change, protected constraints, expected axis improvement and an exact before/after test. “Make it pop” is not an action card.

For category health, report coverage, confirmed-failure rate **among reviewed entries**, unreviewed count, median/lower-quartile intent fit, construction variety and useful-role coverage. Never rank categories by average intensity or treat unreviewed items as passes. Publish denominators and avoid comparing categories with incompatible evidence coverage.

### Find holes by useful roles

Build a matrix of **material family × restrained/moderate/expressive response × paint policy × full-body/accent role**. Count only verified, distinct constructions, while listing useful palette variants separately. An empty cell is a candidate opportunity, not automatic proof a new finish is needed.

Promising questions: Is there a clear, reliably distinct gloss/satin/matte ladder? Enough subtle source-preserving alternatives to busy hero finishes? Fine sparkle that remains controlled around sponsors? Multicolor designs with meaningful secondary shades rather than three dominant primaries? Dark finishes that remain legible in daylight and at night? Finishes that reveal different material behavior without destroying source artwork? Each proposed gap requires inventory and matched-output evidence before a build request.

## 7. Implementation status and next acceptance milestones

**Implemented here:** complete static catalog census, saved-pair measurements, hashes, legacy coverage reconciliation, exact cached-pixel groups, searchable dashboard, live base-picker capture runner, two-sided target utility and missing-evidence bounds with tests. No replacement scores are assigned.

**Next:** approve per-finish contracts using existing evidence, extract native output and semantic features, compare current standard/picker/native routes, collect matched car fixtures, calibrate against owner examples and validate holdouts. Then run both systems in diagnostic comparison before changing UI rankings. The initial census identifies where to start; it does not pretend to have completed every name test or in-game judgment.

Reference implementation: `scripts/spb_finish_intent_audit.py`, `scripts/spb_finish_live_census.py`. Evidence: `census.json`, `live_census.json`, `FINDINGS.md`, `AUDIT.html` in this directory. Source rules: `docs/FINISH_LAW.md`, `scripts/protected_finishes.json`, `SPB_WIKI.html` Finish Doctrine / Spec Guide, and the current owner instructions.
