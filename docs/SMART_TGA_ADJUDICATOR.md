# Smart TGA Component Evidence and Ownership Adjudicator

Status: Cycle 608 Phase 2/3 qualification, shadow-only. Baseline: Cycle 604 commit
`ce139044` over Cycle 603 commit `6da5c7ef` (2026-07-09). Apply remains
intentionally unavailable.

## Why this exists

`engine/spec_sculpt/car_layers.py` contains valuable knowledge accumulated from
hundreds of real liveries. Its convergence limit is authority, not knowledge:
repair helpers directly move pixels and several are replayed at multiple phases.
A later recovery can undo an earlier demotion, so a target can pass while an old
contract becomes red.

The adjudicator changes the authority model:

```text
immutable detector-stage proposals
        |
        v
stable ownership atoms built once ---- OCR / GPU / car-intel provenance
        |
        +---- geometry / color / palette / shape evidence
        |
        +---- proximity / containment / repeat / mirror / 180-degree / family edges
        |
        v
classifier evidence votes (no pixel writes)
        |
        v
one deterministic ownership decision per node
        |
        v
one hard Numbers / Sponsors / Template / Brand / Paint partition
```

Existing rules are not discarded. Their outputs are converted into votes, then
their ability to repeatedly mutate the partition is retired in bounded groups.

## Binding invariants

1. Current shipped output remains the fallback.
2. Default mode is `off`.
3. The only enabled experimental mode is `shadow`.
4. `apply` is intentionally rejected until owner-authorized exit gates pass.
5. Shadow mode never returns replacement masks to `car_layers.py`.
6. Input RGB and masks are never mutated.
7. Component and ownership maps are read-only NumPy arrays.
8. Every output pixel has exactly one owner.
9. Ties and weak evidence preserve current ownership.
10. A family relationship needs at least two corroborating nodes, and its total
    vote is capped below the current-owner vote. Relationships can strengthen
    classifier/OCR/guard evidence but cannot relabel a component by themselves.
11. Runtime exceptions fail closed to the current shipped masks.
12. Root and Electron copies remain byte-identical.
13. Final-owner components are split at immutable proposal boundaries. A missed
    decal inside one giant Paint component remains independently adjudicable.
14. Every non-hard ownership change requires two independent non-relationship
    evidence sources. A detector or legacy guard plus visual-family similarity is
    one claim plus corroboration, not two independent claims.
15. Blocked proposals remain visible in bounded telemetry.

## Module contract

`engine/spec_sculpt/candidate_evidence.py` captures the pre-repair knowledge.

- frozen bbox-local `CandidateRegion` records avoid full-frame-mask memory per
  component;
- `CandidateSnapshot` preserves overlapping proposals without applying layer
  priority;
- raw OCR, GPU, Template-prior, and logo proposals keep stage/source provenance;
- legacy guard masks become immutable `MaskEvidence` records;
- `capture_mask_evidence_batch(...)` freezes a bounded family ledger at each
  existing repair boundary;
- proposal boundaries refine final ownership into stable atoms.

`engine/spec_sculpt/component_evidence.py` owns graphing and resolution.

- `build_component_graph(rgb, masks, ocr_regions=..., candidate_snapshot=...)`
  - normalizes overlap with production priority:
    Numbers > Template > Sponsors > Brand Graphics > Paint;
  - builds connected components once;
  - freezes component/owner maps;
  - records node geometry, area, fill, centroid, RGB/HSV statistics, white/dark/
    colored fractions, edge density, palette descriptor, normalized shape
    descriptor, and OCR orientation/mirror provenance;
  - records relationship edges for proximity, containment, palette, repeated
    shape, horizontal reflection, 180-degree rotation, side/rear family, and
    shared OCR regions.
- `votes_from_mask(...)`
  - converts an existing guard mask into evidence without moving pixels.
- `mask_evidence_vote_specs(...)`
  - aggregates replayed evidence by node, target owner, and source;
  - repeated calls from one source contribute one vote at the maximum observed
    weight, with unioned support/reasons, so replay count cannot manufacture
    confidence or independent-source quorum.
- `relationship_votes(...)`
  - emits a vote only after multiple related nodes agree.
- `adjudicate(...)`
  - resolves each node exactly once;
  - hard safety contracts override soft votes;
  - deterministic ties favor the current owner, then production priority.
- `materialize_masks(...)`
  - creates one exhaustive, non-overlapping partition from assignments.
- `run_shadow_if_enabled(...)`
  - returns compact comparison telemetry only.
- `number_family_signals(...)` and `number_family_template_inlay(...)`
  - provide conservative, scale-invariant production evidence for repeated
    Number decals, compact multi-glyph wordmarks, and number ink embedded inside
    a fixed Template component;
  - require multiple large palette-consistent anchors before protecting/recovering
    small variants, and extract number ink rather than flooding hardware.

Cycle 608 requires every soft owner change to clear independent-source quorum.
Relationship evidence can raise confidence, but it cannot satisfy the quorum.

## Feature gate

```powershell
# Normal buyer/runtime behavior; zero graph cost.
$env:SPB_SMART_TGA_ADJUDICATOR_MODE = 'off'

# Build proposal and telemetry, but keep current masks byte-for-byte.
$env:SPB_SMART_TGA_ADJUDICATOR_MODE = 'shadow'
```

Any other value, including `apply`, resolves to `off`.

## Shadow telemetry

The compact response reports:

- schema and mode;
- elapsed milliseconds;
- node/edge/pair counts and pair-budget truncation;
- relationship-vote count;
- current/proposed pixel totals per owner;
- per-owner XOR pixel counts;
- changed node count;
- production-component count, proposal split count, and atom-budget status;
- detector region/stage/source counts and candidate-vote count;
- blocked-proposal count/reasons/sources;
- immutable legacy-mask evidence and vote counts;
- bounded changed-node evidence: bbox, area, from/to, confidence, margin, scores,
  vote sources, reasons, and supporting family nodes;
- `output_applied: false`.

Telemetry must stay bounded. It does not include masks, component maps, RGB data,
or unbounded rule histories.

## Migrating legacy knowledge safely

Migrate one rule family at a time:

1. Run the current helper exactly as today to obtain its candidate mask and guard
   metadata.
2. Convert the mask to `EvidenceVote` objects with `votes_from_mask`.
3. In shadow mode, compare the adjudicator proposal with the current final masks.
4. Prove target improvement and control stability across the whole corpus.
5. Only after owner review, disable that helper's pixel mutation while retaining
   its evidence producer.
6. Keep the old path behind the instant `off` fallback during rollout.

The first migration candidate should be a family with repeated final replays,
because removing repeated authority produces the largest convergence win.

## Current five-red proof set — green in Cycle 606

Cycle 606 made these full-suite contracts green without filename/bbox lookup
rules and without enabling adjudicator apply:

1. `test_smart_tga_warm_livery_arc_retries_before_paint_materializes`
   - final sponsor recovery now precedes the one late warm-livery decision.
2. `test_smart_tga_number_trim_fragment_recovers_dense_dlm_number_shell_sponsor_chips_real_38631`
   - immediate Number-vs-Sponsor ring ownership defeats broad dilation alone.
3. `test_smart_tga_panel_text_residual_recovers_dark_grayscale_logo_interior_fill`
   - bright neutral fill no longer qualifies as mixed contingency evidence.
4. `test_smart_tga_red_white_dlm_body_slabs_fall_back_to_paint_real_artifacts`
   - partial-mask and whole-component evidence use independent safety budgets.
5. `test_smart_tga_panel_text_residual_recovers_mixed_sponsor_hairline_text`
   - the specific hairline taxonomy wins over broader overlapping evidence.

Verification: five-red proof **5/5**, affected shared-family suite **90/90**, and
full `tests_v2` **1832 passed / 14 skipped / 0 failed**.

## Cycle 606 real-route proof

Real DLM `car_num_1101717.tga`, GPU-hybrid, 1024 output:

- 239 immutable raw detector regions;
- 314 production components refined to 398 stable atoms (84 splits);
- 283 candidate votes and 359 relationship votes;
- 17 Template proposals blocked for lacking a second independent source;
- 0 changed nodes and zero XOR for all five owners;
- shadow analysis about 2.9-3.4 seconds;
- current output byte-identical to the prior good masks;
- exact Number bboxes preserved: `[254,225,143,125]`, `[262,709,150,122]`,
  `[798,840,176,128]`.

## Cycle 607 immutable guard-ledger proof

Seven high-replay legacy families now emit frozen evidence ledgers at the engine
and route final boundaries while their current production behavior is preserved:

- `panel_text_residual` -> Sponsors;
- `warm_livery_arc` -> Paint;
- `number_trim_fragment` -> Numbers;
- `smooth_red_body_panel` -> Paint;
- `white_livery_number_panel` -> Paint;
- `number_logo_false_positive` -> Sponsors;
- `large_stylized_number_shell` -> Numbers.

Replayed records from the same family/source are collapsed before voting. A real
ARCA `81` exposed why the universal quorum matters: one legacy guard proposed a
484-pixel Paint -> Sponsor move and relationship evidence echoed it. The old
high-risk-only quorum would have allowed that loss. The universal quorum blocks
it as `insufficient_independent_sources`.

Mixed real-corpus off/shadow proof covered DLM `1101717`, Cup `23371`, and ARCA
`313679`: **3/3 route success**, **375 generated PNG artifacts byte-identical**,
and zero owner XOR. DLM produced 398 atoms, 22 mask-evidence votes, 283 candidate
votes, 359 relationship votes, 14 blocked proposals, and zero changes.

## Cycle 608 universal Number-family proof

Real ARCA `car_num_313679.tga` exposed two complementary family failures: a true
small `81` was treated as a tiny logo, while another small `81` lived inside one
large headlight Template component. At the same time, a Snap-on wordmark was
incorrectly owned by Numbers.

The new Number-family evidence uses repeated palette/shape/scale agreement rather
than file, car, or bbox lookup:

- two or more large, palette-consistent Number anchors can protect a smaller
  scale variant when its fill and geometry remain family-consistent;
- compact, wide, separated multi-glyph islands without Number-family support are
  wordmark evidence and demote to Sponsors;
- a Template inlay is recovered only after large anchors and an already-owned
  small exemplar agree on two-color palette and scale; only matching number ink
  plus a one-pixel immediate outline moves to Numbers.

Fresh ARCA production output contains exactly six real `81` decals at
`[94,24,31,24]`, `[817,58,31,21]`, `[416,229,184,121]`,
`[261,471,326,251]`, `[418,842,177,123]`, and `[179,914,121,110]`.
The Snap-on bbox `[45,942,71,30]` is Sponsors, while the headlight remains
Template and only about 569 Number-ink pixels are extracted. DLM and Cup control
layers stayed byte-identical; DLM preserved its exact three red-`6` boxes.

Verification: focused evidence **14/14**, accumulated false-Number/component
evidence **27/27**, route/five-red set **53/53**, and full canonical `tests_v2`
**1835 passed / 14 skipped / 0 failed in 309.50s**. Live root server PID `157752`
on port `59876` returns build
`smart-tga-cycle608-universal-number-family-evidence-20260709`; live DLM and ARCA
POSTs reproduce the expected boxes with zero shadow changes/XOR. The in-app page
loads completely as v8.0.3-beta with zero browser errors; only unrelated existing
finish-catalog grouping warnings remain.

## Cycle 609 golden-corpus release gate

`scripts/smart_tga_golden_corpus_gate.py` turns route-inspector artifacts into a
repeatable qualification gate instead of relying on component totals or memory.
For every reviewed manifest entry it proves:

- both route calls succeeded on the same Smart TGA build and engine;
- the control really ran in `off`, the comparison really ran in `shadow`, and
  neither applied adjudicator output;
- every pixel has exactly one of the five owners (zero gaps and overlaps);
- rebuilding the source from the five ownership masks is pixel-exact;
- off/shadow source images and every owner-mask PNG are byte-identical, with zero
  pixel XOR;
- shadow reports zero changed nodes and zero owner XOR;
- reviewed component counts/bboxes/pixel bounds still match their manifest.

The gate deliberately separates `technical_pass` from semantic-review coverage.
A tiny green smoke set cannot become a release verdict: default qualification
requires at least 100 entries, full review of all five owners, and no known issue.
`--strict` exits nonzero until those requirements are satisfied. It also generates
a bounded HTML review board linking the source overlays and per-owner sheets.

The first three-entry seed covers DLM `1101717`, Cup `23371`, and ARCA `313679`.
The first comparison caught stale evidence: saved artifacts named as Cycle 608
still reported the Cycle 606 build stamp. Those artifacts were rejected even
though their masks happened to match. Fresh current-build off/shadow routes then
passed all technical gates:

- **3/3 technical pass**;
- zero gaps, overlaps, or reconstruction mismatches;
- all 15 owner masks byte-identical off versus shadow;
- zero changed nodes and zero shadow XOR;
- DLM exact three-number contract, Cup zero-number control, and ARCA exact
  six-number contract all green;
- exact build on both sides:
  `smart-tga-cycle608-universal-number-family-evidence-20260709`.

Release remains correctly blocked at **3/100 entries** and **0/3 fully reviewed**.
ARCA explicitly retains its Sponsor/livery semantic issue rather than hiding it
behind the technical pass. The seed manifest is
`tests_v2/smart_tga_golden_corpus_v1.json`; focused gate tests are **4/4**.

## Rollout phases

### Phase 1 - Foundation (complete)

- Dedicated module.
- Immutable graph and deterministic resolver.
- Legacy-mask-to-vote adapter.
- Feature gate limited to off/shadow.
- Focused synthetic contract tests.
- Minimal final-boundary telemetry hook.

### Phase 2 - Evidence adapters (in progress)

- Capture initial OCR/template/brand proposals before repair mutation.
- Pass real OCR boxes with mirror/orientation provenance.
- Convert one repeated helper family to votes while leaving current masks intact.
- Add corpus reports keyed by car, component family, and reason.

### Phase 3 - Shadow corpus qualification (started)

- DLM 603/604 targets and four-file controls.
- Five-red proof set.
- Francis and non-DLM controls.
- Number masks must remain protected against mirror-only Sponsor evidence.
- Measure runtime and bound graph pair work.
- Grow the manifest-backed, five-owner reviewed golden corpus from 3 to at least
  100 entries; `technical_pass` alone is not release qualification.

### Phase 4 - Owner-gated authority transfer

- Add apply capability only after explicit owner approval.
- Move one helper family at a time from mutation to evidence-only.
- Preserve environment fallback to the current pipeline.
- Do not remove old rule code until its corpus contract is represented by evidence
  tests and rollback has survived a release cycle.

## Apply-mode exit gates

All are required:

- new module tests green;
- full Smart TGA suite green, including the five-red proof set;
- Cycle 603 correct Number bboxes preserved;
- Cycle 604 CPU Number XOR remains zero with mirror OCR on/off;
- current route masks byte-identical with adjudicator off versus shadow;
- mixed DLM/Cup/ARCA shadow corpus byte-identical and zero XOR;
- ARCA Number-family contract preserves all six true `81` decals, demotes the
  Snap-on wordmark, and leaves headlight hardware in Template;
- no partition gap or overlap;
- golden-corpus strict gate passes with at least 100 fully reviewed entries and
  no known semantic issues;
- no unbounded telemetry or material runtime regression;
- root/Electron hashes match and runtime manifest coverage passes;
- owner explicitly authorizes behavior application.
