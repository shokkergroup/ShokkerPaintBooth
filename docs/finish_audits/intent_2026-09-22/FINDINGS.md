# Finish audit — findings and effort priorities

22 September 2026. Read alongside [the proposed Intent-Fit system](SYSTEM.md) and [the searchable audit](AUDIT.html).

## What was audited

The catalog snapshot contains **1,144 base entries and 2,443 special entries**, or 3,587 surface/ID records with 3,577 distinct bare IDs. Surface matters: a repeated ID across base and monolithic routes is not automatically a duplicate finish. The served catalog and root catalog SHA-256 matched (`9dfb833807edd8fd5bf740f5c321d2c25328cface90bddb18c6d91e1d03a02cf`).

All 1,144 bases have readable saved split pairs. Across both catalogs, 3,575/3,587 split pairs were measured. This is a full automated catalog census, **not 3,587 completed human name tests or in-game approvals**. Visual inspection was sampled and is identified below. Actual base-picker captures are recorded separately in `live_census.json`; those supersede historical static pairs for current base diagnostics.

**Current base sweep completed: 1,144/1,144 usable pairs — 1,140 actual HTTP faithful-picker responses plus four existing fingerprint-matched protected masters.** No requests remain failed and no renderer fingerprint changed during capture. [Current category measurements](MEASUREMENTS.md) and `current_base_measurements.csv` summarize them. The current samples have 534 entries with zero or one substantial chromatic hue sector, and 135 / 65 / 172 entries with low M / Rough / Cc picker spans respectively. Those overlapping descriptors are not bad-finish counts; many are intentional.

The base snapshot has 19 groups, 695 grouped entries and 449 entries not present in BASE_GROUPS. Ungrouped does not prove unreachable: other picker paths, aliases and server merges may expose them. The runtime health endpoint reports 1,236 registered bases and 3,035 monolithics, which is a broader engine registry than the authored picker arrays. Do not turn registry totals into buyer-visible unique-finish counts.

Special groups also refer to IDs outside the MONOLITHICS array, including cross-surface IDs. Preserve those relationships and resolve routing before claiming missing finishes. The working scope here is the complete authored BASES array, with MONOLITHICS as a separate comparison set; arbitrary backend-only entries and saved user imports are not silently added to that denominator.

## Confirmed problems in the measuring system

| Finding | Evidence | Why it matters |
|---|---|---|
| Broad missing coverage | 632/1,144 bases have no saved M7 composite; 824/1,144 have no M6 intent score | The existing ranking cannot fairly compare the whole base catalog. Missing scores are not low quality. |
| Category-forced perfection | `spb_workbook_compute_m7.py` sets composite=100 for six category labels; 38 current special entries match those legacy labels | A 100 can be policy rather than measured excellence. Keep any owner endorsement separate. |
| Missing-input inflation | M7 renormalizes weights over whatever components exist | Sparse evidence can look as conclusive as full evidence. |
| Wrong definition of coherence | M5 compares paint-busyness and spec-liveliness percentile ranks | Quiet paint with active spec can be intentional; equal busyness does not prove spatial/material alignment. |
| Moving targets | M6 uses whole-catalog percentile bands | Adding or removing other finishes can alter an unchanged finish's fit. |
| Overbroad category assumptions | Chrome/Mirror expects high M range in M6; Foundation mixes ordinary and expressive materials | A uniform chrome can be excellent; one profile cannot cover every Foundation entry. |
| Identity blind spots | M1 chromatic hashes include palette difference; very large clone groups receive special handling | Recoloring can appear distinct and some large groups escape the usual penalty. Use independent structural evidence. |
| Tiny historical evidence | Many saved split files are 96×48, only 48×48 per material | Fine geometry, color occupancy and spec variation collapse. A weak thumbnail measurement can be a scale artifact. |
| Freshness not bound to verdict | Legacy JSON generated dates are present, but current renderer/native output provenance is not established for each score | Recent file dates are not proof of current valid measurements. |

The legacy metric files inspected were generated on 18 September. That date alone does not mean each finish was remeasured on that day. No existing score or owner verdict was changed.

## What the images already tell us

These are inspection findings and focused questions, not final finish failures.

- **ASTRA deserves an early name/readability review.** Current sampled cards for Janus Blades, Chromatic Switchyard and Pipeline Royale show very dense fine fields. Their named blade, routing and wave ideas are difficult to identify at picker scale. Color and material variation are present; adding more random variation would not address the question. First inspect native crops and matched car views, then improve feature hierarchy, local separation and negative space if the promised construction is also lost there. Preserve fine feature size.
- **SLITHERIN / MULE / WRAP SHOP need intended-strength review, not indiscriminate boosting.** Sampled Keeled Viper, Edge Chamfer and Air Release retain restrained palettes. Their current responses contain more spec variation than the historical 48px files suggested. Decide whether scales, edges and release structure remain identifiable on the car, and which channels should actually vary. Do not turn subtle engineering surfaces into rainbow effects.
- **FLAW LAB proves why a universal spec-range floor is wrong.** Protected Isochromatic Fringe has highly visible paint fringes with a restrained spec, while protected Magnetic Particle has a different material distribution. Their owner acceptance must survive the new metric. Eddy Current, Isochromatic Fringe, Isoclinic Band and Magnetic Particle were preserved; the live census reads matching existing masters for them rather than rebaking them.
- **BAD & RAD / ALL THAT / CYBERPUNK offer useful feature-binding calibration candidates.** Sampled Neon Spandex, LAN Party Circuit and Biohazard Bloom show readable structures and corresponding spec organization. This is evidence to study, not a category-wide pass or an on-car verdict. Their native scale, long-distance retention and material meaning still need the full tests.
- **Foundation needs a restraint calibration ladder.** Gloss and Semi-Gloss have exactly matching historical paint pixels, which can be correct. Compare their actual material response against Wet Look, Satin, Matte and Chrome under identical lighting. Count useful response differences, not paint noise.
- **Gloss Wrap has a concrete description/material discrepancy.** Its current description explicitly says “No metallic,” but the actual faithful picker response has M p01=65, median=82 and p99=100. This is a native-output verification priority, not a request to increase spec strength. Confirm whether the composed export also carries metal and whether the description or material routing is wrong; repair the actual mismatch if confirmed. Source tint and response fingerprint are recorded in `live_census.json`.
- **Foundation EFX needs recognition and behavior tests.** A restrained paint half can be correct for a spec-led effect. Holographic Drift, Nacre, Surface Rust and other named effects should be judged by whether their mechanisms read in material/light response and native detail, not simply by number of paint colors.

Contact sheets are presentation-scale evidence, not 1:1 native-size qualification. `contact_1.jpg` and `contact_2.jpg` show historical snapshots; `live_contact_1.jpg` shows selected current responses/protected masters. A blank sheet slot means that ID was not available for that particular sample, not a black finish. The existing 512px-per-half ASTRA masters were also inspected for Janus Blades and Pipeline Royale: the latter reveals small curved elements, supporting part of its wave idea, but this does not settle on-car recognition. Copies and fingerprints are retained; no native 2048 verdict is implied.

## Where to focus first

1. **Trustworthy inputs and per-finish intent.** Reconcile current standard/picker/native routes and assign explicit profiles. Otherwise a “fix” may chase an old thumbnail or a wrong expectation.
2. **ASTRA and similarly dense theme constructions.** Test idea readability and separation before adding complexity. This is a focused visual concern from sampled current cards, not a blanket rejection of ASTRA.
3. **Foundation / Foundation EFX, then MULE / WRAP SHOP / SLITHERIN.** Build the quiet-to-expressive calibration set. Validate the distinction between deliberate restraint, flattened previews and genuinely weak material behavior.
4. **Colorful rebuilt categories.** BAD & RAD, ALL THAT, FAR OUT, CYBERPUNK and TACTICAL & FIELD need feature-level palette and material checks. Colors that disappear through reduction need better placement/separation, not automatically larger motifs. Low M variation may correctly describe fabric, plastic or painted surfaces.
5. **Cross-category identity and role coverage.** After input/intent repair, compare closest constructions and map useful roles. Rebuild confirmed repeats; keep declared useful palette variants without awarding new-design credit.

## Every base group: next useful assessment

This table prescribes the review that would help each group; it does not claim those tests have all been performed.

| Group | Count | Next assessment / plausible improvement if a failure is confirmed |
|---|---:|---|
| ASTRA | 50 | Blind subject cues, crowded fine structure, paint/spec hierarchy; improve readable construction rather than noise quantity. |
| SLITHERIN | 16 | Species/process cues, scale/ridge geometry, restrained versus active channel duties; separate micro-relief from flat tint. |
| LIGHTNING SHOKK | 16 | Branching and discharge identity, fine contrast hierarchy, relevant spec alignment; avoid generic colored streaks. |
| MULE | 16 | Engineering marks and subtle relief under raking light; improve edge/groove correspondence only where promised. |
| THE BOOTH | 16 | Painting/process marks, fine layering and surface-state plausibility; distinguish application methods. |
| FLAW LAB | 25 | Preserve four favorites; compare inspection-specific cues and feature-owned material behavior across the remaining entries. |
| WRAP SHOP | 25 | Vinyl/laminate/release/process identity and gloss differences; retain restrained commercial-wrap roles. |
| Foundation | 25 | Matched clean finish ladder; separately classify its expressive members; source-color preservation. |
| Foundation EFX | 46 | Effect-specific optical/physical behavior, native texture and appropriate paint restraint. |
| FAR OUT | 60 | Era motifs and palette hierarchy; resolve absent root static standard assets before interpreting old comparisons. |
| BAD & RAD | 60 | 1980s material distinctions, color family/shade coverage, material response of fabric/plastic/metal. |
| ALL THAT | 60 | 1990s subject/material identity, visible palette separation and contextual M variation; honor recent owner decisions. |
| TACTICAL & FIELD | 60 | Concealment, field-wear and equipment materials; judge restricted palettes against purpose, not chromatic categories. |
| CYBERPUNK | 60 | Recognizable electronic/urban/biological mechanisms, controlled bright/dark hierarchy and meaningful material differences. |
| Flames | 20 | Flame tongues, layering, fine breakup and spec placement; avoid palette-only repeated flames. |
| Sock Hop | 20 | Distinct period-specific motif construction and clean usable material behavior. |
| Groovy Vibes | 20 | Distinct period motifs, purposeful multi-hue families and fine shape separation. |
| Iridescent Insects | 50 | Name/biology cues, unique paint and spec carriers, actual angle/light behavior; retain the established similarity gate. |
| PRISM FORGE | 50 | Distinct prismatic/construction mechanisms and scene response; compare with same IDs/shelves across surfaces before counting. |

The 449 ungrouped BASES entries also have individual census records and live-capture requests. Review whether each is intentionally available, an alias, a migrated finish or an orphan before choosing to hide, retire or rebuild it.

## Holes worth filling

**Confirmed evidence holes:** per-finish target contracts; large legacy metric-coverage gaps; calibrated plain-material examples; output-bound native/on-car proof; clear accounting of aliases and ungrouped entries. These should be filled before ordering another large batch of finishes.

**Candidate product opportunities, not proven absences:** a clearly differentiated subtle gloss/satin/matte ladder; more source-preserving supporting finishes; fine restrained sparkle for sponsor-heavy liveries; dark dynamic materials that retain daytime identity; purposeful secondary shades within colorful designs; useful response variants with simple paint. The proposed material × expression × paint-policy × use-role matrix will show which of these are already served and which need new work.

## Limits and protections

The automated census measures every listed record, but does not decide every finish's name fidelity, semantic material correctness, identity uniqueness or in-game appearance. No new “best finish” score is defensible until those intent/evidence stages are complete. All suggested rebuilds remain conditional on their tests. Renderers, palettes, favorite files and production ranking logic were not edited. Normal live swatch requests can populate missing content-addressed caches; protected favorites are read from existing matching masters only.

Legacy disk findings include 155 missing root standard assets for bases and 775 for specials, plus 12 missing special split files (`gl_*`). These are file-coverage findings, not proof of broken runtime routes. The 67 exact cached paint/spec pixel-match groups are in `census.json`; aliases, clean substrates and stale evidence must be separated before any duplicate verdict.

Validation: five focused mathematical/measurement tests passed; both audit scripts compile, the contract schema parses, all base keys are unique, and capture fingerprints remained stable. Browser search/category filtering, images and current-evidence labeling were checked. `audit_validation.json` records the final counts. Full native/on-car calibration remains explicitly unperformed.
