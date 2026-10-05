# SPB Finish Quality Metrics — Reference

**Last updated:** 2026-05-15
**Source of truth:** this doc + `scripts/spb_workbook_compute_m*.py`
**Visual surface:** `SPB_FINISH_QUALITY_WORKBOOK.html` (open from project root)

This doc explains every metric in the SPB Finish Quality Workbook — what it
measures, how it scores, what it surfaces, and what it can't do. The next
agent should read this BEFORE adding/modifying metrics or interpreting the
STILL-WEAK list.

---

## 0. Why the existing scorecard wasn't enough

`paint-booth-0-catalog-scorecard.js` already exists with fields like
`overallQuality`, `paintQuality`, `specQuality`, `paintFineEnergy`,
`specMRange`, etc. It measures **signal properties** — frequency-band
energy, channel range, color count. It doesn't measure **quality properties**
— does the finish match its name, do siblings look distinct, does the
spec channel agree with the paint channel, etc.

The new metric suite was built on top of that scorecard data plus the
existing thumbnail bake, treating the scorecard signals as inputs to
higher-level judgements.

---

## 1. The doctrine (read this before designing metrics)

Three rules are non-negotiable. Every metric must respect them.

### A. The 2048×2048 car-body rule

**Render canvas is 2048×2048 covering an entire car body.** Anything that
looks small in a 256-pixel thumbnail is huge on the car.

- A noise octave of 64 produces ~32-pixel features at 2048 = the size of a
  side mirror. That's NOT "fine detail," that's "macro structure."
- "Fine detail" means octaves at **128, 256, 512, 1024, 2048** (single-pixel).
- Every generator must layer **at least 3 frequency bands** with the highest
  legitimately fine (single-pixel sparkle, micro-flake, micro-facet).
- No purely-procedural-from-zero unless the fine layer earns its complexity.

### A.1 Match the frequency band to the measurement scale (tick 27 insight)

"Fine grain" is not one thing — it's **three distinct bands at three
measurement scales**, and a renderer needs all three to pass the metric
suite AND look right on the car:

| Band | Octaves (at 2048) | Feature size | What it lifts |
|---|---|---|---|
| **Macro** | 32 / 64 / 128 | 16–64 px | `M8 macro_std32` (visible thumbnail-scale structure) |
| **Fine** | 256 / 512 | 4–8 px | `M6 paintFineEnergy` (the audit metric reads this) |
| **Micro** | 1024 / 2048 | 1–2 px | Sub-pixel sparkle / micro-flake on the actual car render |

A common bug pattern (caught multiple times in this session): a renderer
adds "fine grain" at octaves 256+ thinking it's the right answer. M6 may
register the lift, but **M8 stays at 0** because sub-32px noise averages
out within 32px blocks. The thumbnail still looks flat. Owner rejects.

Recipe to fix that bug:

```python
mid_band  = _noise(shape, [32, 64, 128], [0.4, 0.35, 0.25], seed)   # M8 lift
fine_band = _noise(shape, [256, 512],    [0.55, 0.45], seed + 1)    # M6 lift
micro_band = _noise(shape, [1024],        [1.0], seed + 2)           # car-scale sparkle
out = (
    (mid_band   - 0.5) * 0.080 +
    (fine_band  - 0.5) * 0.060 +
    (micro_band - 0.5) * 0.040
)
```

Proven applications: SPB-80 Panel Quilting (10/10 finishes lifted),
SPB-81 Weather & Age (10/10 lifted, salt_spray jumped 1.1 → 9.7).

This rule is restated in `CLAUDE.md` and was learned the hard way during
SPB-85 (efx_* v1 rewrite — owner rejected as "boring, blobby, out of place").

### B. Surface intent

Different surface families have different intent. The metric framework
respects this — penalizing intentional quietness is a bug.

**Canonical mapping lives in `engine/paint_v2/surface_intent.py`.** Import
from there; never hand-code a duplicate in a new script:

```python
from engine.paint_v2.surface_intent import get_intent, is_spec_driven
is_spec_driven("Foundation")   # True
get_intent("Geometric")        # "pattern_design"
get_intent("Candy & Pearl")    # "full" (default for unmapped)
```

| Surface family | What varies | What is intentionally flat |
|---|---|---|
| **Foundation** (`f_*`, `enh_*`, `efx_*`), Clearcoat, Ghost Geometry | Spec channel (M / R / CC) | Paint channel — no paint functions by design |
| **Regular patterns** (Carbon, Geometric, Op-Art, Decades, Tech & Circuit, Guilloché, etc.) | Pattern **structure** (frequency-domain energy + regularity) | Paint color & saturation — patterns are about design, not color |
| **Image-based patterns** (small subset, TBD per SPB-75) | Both design and color | Nothing |
| **Bases, Monolithics, Effects** | Both paint and spec | — |

When you design a metric:
- If it cares about paint variation, EXCLUDE `spec_driven` finishes
- If it cares about color, EXCLUDE `pattern_design` finishes
- M6 has explicit per-category profiles encoding this; M7 weights are
  surface-aware too.

### C. Reference standards (the bar to clear)

Three image-backed cultural finishes are the owner-rated top tier. New
finishes must match or beat their detail level:

- **Viva Mexico** — see `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`
- **Union Jacked**
- **Rising Sun**

All three were made via: GPT Images 2.0 PNG plate → Spec Map Maker →
procedural enhancement on top of the plates. The procedural enhancement
uses paint-RGB to drive masks (luma + edge magnitude), three-channel
triplet variation, deterministic finish_id-seeded RNG, ridge protection,
and a global DS scalar for one-knob intensity tuning.

Pure-procedural-from-zero (no PNG plate) is *possible* at the quality
bar — see `engine/paint_v2/enhanced_foundation_exotic.py` (current state)
— but harder. PNG-backed is the safer path for premium finishes.

---

## 2. The 8 metrics

### M1 — Sibling Differentiation

**Script:** `scripts/spb_workbook_compute_m1.py`
**Output:** `_workbook_metrics/m1_sibling_diff.{json,js}` (key `window.SPB_M1`)
**Coverage:** 99% (1532 / 1546 finishes)
**In M7 composite:** yes (weight 0.20–0.30 depending on surface intent)

**What it measures:** For each finish, compute 64-bit dHash of its thumbnail,
then mean Hamming distance to category siblings. Low distance = looks like
a clone of its neighbors.

**Scoring:** `(mean_distance / 32) * 70` mapped to [0, 100]. Random pairs at
~d=32 score 70.

**Bonus output:** `cloneGroups` — union-find connected components at
Hamming ≤ 2. Surfaces the 587-megaclone (SPB-74) and 150 smaller groups.
Per-finish `cloneGroupSize` powers M4-style clone penalty in M7.

**Limitation:** Depends on thumbnails being accurate renders of the finish.
For spec-driven finishes, paint-only thumbnails are flat gray → all spec-
driven finishes appear as clones to M1 even when their spec is wildly
different. M7 handles this with surface-aware weight redistribution.

### M2 — Intent-Fit Proxy

**Script:** `scripts/spb_workbook_compute_m2.py`
**Output:** `_workbook_metrics/m2_intent_fit.{json,js}` (key `window.SPB_M2`)
**Coverage:** 69% (1073 / 1546 finishes — expanded 2026-05-15)
**In M7 composite:** yes (weight 0.20)

**What it measures:** Tokenize the finish ID. Each token maps to expected
directional signatures (LO / MID / HIGH) on the 9 measurable axes from the
scorecard. Compares actual percentile-ranked values to expected directions.
Score = % of expected ranges met.

**Vocabulary:** ~115 tokens. See `VOCAB` dict in the script. Examples:
- `chrome` → HIGH specMRange, LOW paintFineEnergy, HIGH specChannelIndependence
- `candy` → HIGH paintSaturationMean, HIGH specMRange, HIGH specCcRange
- `matte` → LOW paintFineEnergy, LOW specMRange, LOW paintSaturationMean
- `weather` → HIGH paintFineEnergy, LOW paintSaturationMean

**Limitation:** Vocabulary gaps. 31% of finishes have no matching tokens
and score null. Adding tokens is mechanical (one PR per vocab batch).

### M3 — Cross-Scale / Cross-Variant Coherence

**Script:** `scripts/spb_workbook_compute_m3.py`
**Output:** `_workbook_metrics/m3_cross_variant.{json,js}` (key `window.SPB_M3`)
**Coverage:** 17% (only spec_pattern surface)
**In M7 composite:** ⚠️ **NO** — diagnostic only

**Status:** Original design was "render at 512/1024/2048 and compare."
Blocked without a renderer harness. Tried using existing
`thumbnails/spec_patterns/` vs `_metal/` vs `_visual/` variant folders as
a substitute. **The data doesn't support it** — those three folders contain
independent designs that happen to share IDs, not contextual renders of
the same finish.

See **SPB-83** for the resolution path (rename folders / restructure /
document intent).

### M4 — Family-Clone Detector

**Source:** Same data as M1 (clone groups computed by `spb_workbook_compute_m1.py`)
**Output:** Part of M1's JSON output (cloneGroups, cloneGroupsCrossCategory)
**Coverage:** 99%
**In M7 composite:** yes — implemented as clone-group penalty

**What it measures:** Union-find over near-identical thumbnails. Per-finish
`m4Score = 100 - 8 × (cloneGroupSize - 1)`, floor 0.

**SPB-74 bake-artifact handling (tick 14):** When `cloneGroupSize > 50`, M1
is dropped from M7's composite entirely instead of applying a multiplicative
penalty. Rationale: 587 finishes sharing one hash is a bake-pipeline bug,
not 587 quality failures. Let M5/M6 carry the verdict.

### M5 — Spec/Paint Coherence

**Script:** `scripts/spb_workbook_compute_m5.py`
**Output:** `_workbook_metrics/m5_spec_paint_coherence.{json,js}` (key `window.SPB_M5`)
**Coverage:** 100% (no thumbnail dependency)
**In M7 composite:** yes (weight 0.20–0.30)

**What it measures:** Rank each finish's "paint busy-ness" (fine/residual/
block energy + color population) and "spec liveliness" (M/R/CC dynamic
range) within the catalog. Score = `(1 - |paint_rank - spec_rank|) * 100`.

**Bonus output:**
- `verdict`: `coherent` / `ok` / `drifting` / `paint_louder_than_spec` / `spec_louder_than_paint`
- `copyPasteFlag`: paint fine energy percentile ≡ spec M range percentile, both > 0.5 = spec likely copy-pasted from paint

**Strength:** No thumbnail dependency — immune to SPB-74.

### M6 — Intent-Aware Floor/Ceiling

**Script:** `scripts/spb_workbook_compute_m6.py`
**Output:** `_workbook_metrics/m6_intent_floor_ceiling.{json,js}` (key `window.SPB_M6`)
**Coverage:** ~80% (~80 category profiles)
**In M7 composite:** yes (weight 0.35–0.50)

**What it measures:** Each profiled category has expected LO/MID/HIGH bands
on the 9 measurable axes. For each finish, check % of axes that fall in
the expected band. Categories without a profile → null score (not penalized).

**Category profiles** live in `CATEGORY_PROFILES` dict in the script.
Examples:
- Candy & Pearl: `{paintSaturationMean: HI, specMRange: HI, specCcRange: HI, paintFineEnergy: LO}`
- Foundation: `{paintFineEnergy: LO, paintColorPopulation: LO, paintSaturationMean: LO}` (no spec opinion — Foundation spec is supposed to vary)
- Carbon & Weave: `{paintFineEnergy: HI}` (design-not-color rule)
- Ghost Geometry: `{paintSaturationMean: LO, paintFineEnergy: LO}`

**Adding a profile:** add to `CATEGORY_PROFILES`. Document the design intent
in a comment. Re-run.

**Don't profile "Ungrouped Base", "Ungrouped Monolithic", or "Misc"** —
those have no coherent intent and should be re-categorized (SPB-77).

### M7 — Composite + STILL-WEAK list

**Script:** `scripts/spb_workbook_compute_m7.py`
**Output:** `_workbook_metrics/m7_composite.{json,js}` (key `window.SPB_M7`)
**Coverage:** 100%
**The headline deliverable.** This is what the workbook surfaces at the top.

**Weight maps by surface intent:**
- `full`:           M1=0.20, M2=0.20, M5=0.25, M6=0.35
- `spec_driven`:    M2=0.20, M5=0.30, M6=0.50 (no M1 — paint clones are CORRECT)
- `pattern_design`: M1=0.30, M5=0.20, M6=0.50 (no M2 — paint color irrelevant)

**Clone penalty:**
- `cloneGroupSize == 1`: penalty = 1.0
- `cloneGroupSize ≤ 50`: penalty = `1 - min(0.5, (size-1) × 0.04)` (multiplicative)
- `cloneGroupSize > 50`: drop M1 entirely (recognized as SPB-74 bake artifact, M5/M6 carry the verdict)

**Tier thresholds** (matches `scripts/spb_workbook_compute_m7.py` as of 2026-05-30):
- composite ≥ 80: **keeper**
- 65–79: **ok**
- 50–64: **watch**
- 35–49: **fix**
- < 35: **critical**

> The code keeper tier is **≥80** (`final >= 80`; `tierThresholds.keeper == 80`). The "≥85" cited in `CLAUDE.md`/`AGENTS.md` is the owner's *ship-bar* (SPB-105) — a stricter process mandate that sits above the keeper tier, not the code threshold. 80–84 = code "keeper" but below the owner ship-bar.

**STILL-WEAK list:** All finishes sorted by composite ascending. Top 120
emitted in `stillWeak` field. Workbook hero panel surfaces top 60.

### M8 — Thumbnail-Scale Visibility

**Script:** `scripts/spb_workbook_compute_m8.py`
**Output:** `_workbook_metrics/m8_thumb_visibility.{json,js}` (key `window.SPB_M8`)
**Coverage:** 99%
**In M7 composite:** ⚠️ **NO** — diagnostic only (needs owner sign-off that it tracks taste)

**What it measures:** Std of mean-pooled 32-pixel blocks of each thumbnail.
Captures "would a painter see structure or a smear at picker scale."

**Scoring:**
- macroStd < 2  → 0 (flat smear, owner will reject)
- < 5  → 30 (weak)
- < 10 → 60 (acceptable)
- < 20 → 85 (strong cellular/zoned)
- ≥ 20 → 100 (premium)

**Catalog-level finding:** 631 of 1552 finishes (41%) score M8 < 30 =
thumbnail-flat. Almost all are SPB-74 bake-pipeline victims (spec-driven
finishes whose paint-only thumbnails are flat gray). Categories where
100% of entries are flat: Foundation, Gothic & Dark, Metal & Industrial,
Ghost Geometry, ★ Enhanced Foundation legacy, OEM Automotive.

**Why this metric exists:** Caught after owner reviewed Enhanced Foundation
Exotic v1 and said "boring, blobby, out of place" (SPB-85). The bug was
that my generators had high-frequency content that disappeared at thumbnail
scale. M8 surfaces this class of issue automatically — would have caught
it before owner review.

---

## 3. Linear ticket / metric cross-references

The metric suite's job is to surface real issues. Each major Linear ticket
filed in this session corresponds to a metric finding:

| Linear | Metric finding | Category |
|---|---|---|
| **SPB-73** | (admin — E:→C: migration cleanup) | meta |
| **SPB-74** | M1 + M8 — 587-member clone group, 41% catalog thumbnail-flat | bake pipeline |
| **SPB-75** | doctrine — surfaceIntent field needs to live in finish-data, not just M6 script | data model |
| **SPB-76** | M7 — Enhanced Foundation mean ~64, no keepers | category-level fix |
| **SPB-77** | M7 — Ungrouped Monolithic all 25 critical | category cleanup |
| **SPB-78** | M2 + M6 — Ghost Geometry too loud for its name | renderer rebuild |
| **SPB-79** | M7 — Gradient Extended 91 entries, 89% below watch | category split + audit |
| **SPB-80** | M6 — Panel Quilting no actual quilted structure | renderer rebuild |
| **SPB-81** | M2 + M6 — Weather & Age missing texture/grime | renderer rebuild |
| **SPB-82** | M2 + M6 — Textile-Inspired renderers don't deliver weave | renderer rebuild |
| **SPB-83** | M3 — spec_pattern variants are independent designs | catalog architecture |
| **SPB-84** | (admin — regenerate scorecard for new efx_*) | catalog data |
| **SPB-85** | M8 + visual review — efx_* v1 generators too low-frequency | engine rewrite |

When the workbook surfaces a new persistent finding, file a Linear ticket
and link the metric data. Don't let findings sit only in the workbook —
the workbook is a diagnostic surface, Linear is the work backlog.

---

## 4. Adding a new metric

1. Write `scripts/spb_workbook_compute_m<N>.py`. Inputs: `paint-booth-0-catalog-scorecard.js`,
   thumbnails, and/or earlier-metric outputs. Output: `_workbook_metrics/m<N>_<name>.{json,js}`
   with `window.SPB_M<N> = {...}` global.
2. The output JSON should have `byFinish` (per-finish scores) and ideally
   `byCategory` (rollup) + a `<finding>Preview` list for the workbook to surface.
3. Add `<script src="_workbook_metrics/m<N>_<name>.js"></script>` to the
   workbook's `<head>` script list.
4. Wire into the per-finish merge near the top of the workbook's inline JS.
5. Add a column header + cell template + tooltip + sort option.
6. Add a findings `<section>` between the existing metric sections.
7. If the metric should affect the composite, edit `scripts/spb_workbook_compute_m7.py`
   to include it. Decide weight per surface intent.
8. Document in this file. Update the table in Section 2.

---

## 5. Re-running the pipeline

Order matters because some scripts consume others' outputs:

```bash
# Hash-based metrics (~30s — walks all thumbnails)
python scripts/spb_workbook_compute_m1.py

# Independent metrics (each ~3s)
python scripts/spb_workbook_compute_m2.py
python scripts/spb_workbook_compute_m5.py
python scripts/spb_workbook_compute_m6.py
python scripts/spb_workbook_compute_m3.py   # spec_pattern only, diagnostic
python scripts/spb_workbook_compute_m8.py

# Composite (depends on M1, M2, M5, M6 outputs)
python scripts/spb_workbook_compute_m7.py
```

After re-runs, open `SPB_FINISH_QUALITY_WORKBOOK.html` in a browser. Side-
car JS files auto-load via `<script>` tags. No build step. No web server
required — `file://` URL works.

---

## 6. Things this suite does NOT do

Worth being explicit about the limits.

- **Doesn't render finishes.** Metrics operate on existing thumbnail bakes
  + the catalog scorecard. If thumbnails are wrong (SPB-74), metrics
  inherit the wrongness.
- **Doesn't replace owner taste.** Calibration misses (biomech tick 9,
  art_deco_fan tick 14) happened because the metric framework alone can't
  encode every aesthetic preference. Owner-loved finishes get explicit
  recognition in the workbook's "Reference Standards" section.
- **Doesn't judge premium feel directly.** M7 is composite of structural
  signals. Premium-feel-as-design-intent (the "would a customer pay for
  this?" question) is M7 + owner eyeball, not M7 alone.
- **Doesn't auto-fix anything.** Findings become Linear tickets, then
  engineering work. The workbook is decision support.

---

## 7. Common gotchas

- **Stale scorecard:** `paint-booth-0-catalog-scorecard.js` is generated
  from an audit pipeline (likely `audit_finish_quality.py` family). New
  finish IDs (e.g. efx_*) don't appear in metrics until the scorecard is
  regenerated. SPB-84 tracks this.
- **Three-copy rule:** any change to `engine/`, `paint-booth-0-*.js`, or
  asset manifests must mirror to `electron-app/server/` AND
  `electron-app/server/pyserver/_internal/`. Renderer reads from one
  location, picker from another, scoring pipeline from a third.
- **Thumbnail bake renders paint channel only:** spec-driven finishes
  (Foundation, Enhanced, Exotic, Ghost) bake to flat gray because their
  paint is intentionally flat. Use `scripts/bake_efx_spec_previews.py` as
  the workaround pattern — render the spec channel directly. SPB-74
  tracks the proper fix.
- **Render at 2048, downsample to 256:** never render previews directly at
  256. High-frequency bands (octaves 256+) collapse to single pixels and
  the preview is unrepresentative of the actual car render. `bake_efx_spec_previews.py`
  has the correct LANCZOS downsample.
