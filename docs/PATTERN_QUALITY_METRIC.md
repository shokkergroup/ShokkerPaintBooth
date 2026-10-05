# SPB Pattern Quality Metric (PQM) — Reference

**Last updated:** 2026-05-21
**Source of truth:** this doc + `scripts/spb_pattern_quality_metric.py`
**Visual surface:** `SPB_PATTERN_QUALITY_REVIEW.html` (open from project root, `file://` works)
**Output:** `_workbook_metrics/pattern_quality.{json,js}`
**Sister metric suite:** see `docs/METRICS.md` for the M1-M8 finish-quality
suite (covers all surfaces, including patterns as one slice of that catalog).
PQM is the per-pattern deep dive — designed to make pattern rework
prioritization fast for one person.

---

## 1. Why this exists

The M1-M8 finish quality workbook (`SPB_FINISH_QUALITY_WORKBOOK.html`)
covers the whole 1500+ finish catalog. Patterns are 586 of those entries
but they share scoring assumptions with bases/monolithics that don't fit:

- M1 sibling differentiation lumps patterns with other surfaces in one
  catalog-wide hash distribution.
- M6 intent profiles barely cover patterns (most pattern categories
  return null from M6).
- The owner wants a **single 1-100 number per pattern** that says "rework
  this one" without cross-referencing four scripts.

PQM scores each pattern on 8 explicit components, composites them with
documented weights, and surfaces the result in a sortable HTML grid so
weak patterns are visible at a glance.

---

## 2. The doctrine (read before changing components)

PQM inherits the three non-negotiable rules from `docs/METRICS.md`:

1. **2048×2048 car-body rule** — Render canvas is huge. A "fine detail"
   pattern needs structure at three frequency bands (macro/mid/fine).
   See `docs/METRICS.md` §1A.1.
2. **Surface intent** — Patterns are about **design structure**, not
   color. Pattern thumbnails are rendered with neutral spec; the metric
   shouldn't penalize a black-and-white carbon weave for low saturation.
   That's why P2 (edges) is weighted higher than P7 (dynamic range).
3. **Reference standards** — Patterns should look as crisp as the
   image-backed cultural finishes (Viva Mexico, Union Jacked, Rising
   Sun). Procedural-from-zero is allowed but must layer frequency bands.

PQM additions on top of those rules:

4. **Catalog-relative calibration** — Each component's raw measurement
   is mapped to a 0-100 score via the catalog's own percentile
   distribution. A pattern at 50 sits at the catalog median; 90 = top
   10%; 10 = bottom 10%. Absolute floors/ceilings would be wrong because
   pattern thumbnails are 256×256 baked (not 2048 renders).
5. **Composite is owner-actionable** — Tiers map to action urgency:
   keeper (ship), ok (low-pri polish), watch (re-render if time), fix
   (queue for rebuild), critical (rework before alpha).

---

## 3. The 8 components

### P1 — Structural Energy (weight 0.16)

**What it measures:** Tri-band activity. The pattern actually has
structure across macro (32px blocks), mid (Sobel-magnitude edges), and
fine (3×3 high-pass) bands. Score is the geometric mean of three
band-scores so a pattern with zero macro structure can't compensate with
fine noise (and vice versa).

**Diagnostics:** `macro_std`, `edge_mean`, `fine_energy`.

**Catches:** flat smears (P1 < 25), noise-only patterns lacking macro
structure (P1 < 40), bake-pipeline placeholder thumbnails.

### P2 — Edge Definition (weight 0.14)

**What it measures:** Crispness. Sobel mean magnitude + edge density
(fraction of pixels above an adaptive threshold) + histogram bimodality
proxy (low entropy = crisp two-tone). Patterns need clean edges to read
on a car body.

**Diagnostics:** `sobel_mean`, `edge_density_pct`, `crispness`.

**Catches:** blurry/mushy patterns, overly anti-aliased renders,
patterns where the design has been smoothed away by gain reduction.

### P3 — Coverage Uniformity (weight 0.10)

**What it measures:** Whether the pattern fills the canvas uniformly.
Divides into 8×8 grid of 32px blocks; score is `p10(block_std) /
median(block_std)`. 1.0 = perfectly uniform coverage; 0.0 = pattern only
in center with dead corners.

**Diagnostics:** `median_std`, `min_std`, `p10_std`, `uniformity`.

**Catches:** patterns whose generator only paints inside a bounding box,
patterns that drift to a flat color in corners, single-spot motifs that
were never meant to tile.

### P4 — Tileability (weight 0.10)

**What it measures:** Seam visibility. Compare a 32×wide band at the top
vs the bottom of the canvas, and the same for left vs right. RMS
difference; lower = more tileable. Score = `(1 - rms/0.15) * 100`.

**Diagnostics:** `vert_seam_rms`, `horiz_seam_rms`.

**Catches:** patterns that have visible joins when tiled — pattern
overlays often repeat across a car body, so a high seam is a visible
defect.

### P5 — Frequency Balance (weight 0.14)

**What it measures:** All three octave bands present at non-trivial
levels (M8 doctrine restated). Macro (32px), mid (8px), fine (high-pass).
Score = `0.6 * min(band_scores) + 0.4 * mean(band_scores)` so a single
missing band drags the score down hard.

**Diagnostics:** per-band `value`, `floor`, `score`.

**Catches:** purely low-frequency blobby patterns (no fine), purely
high-frequency noise (no macro), single-octave gradients (no mid).

### P6 — Sibling Differentiation (weight 0.10)

**What it measures:** dHash distance to category siblings (M1-style
per-category). 64-bit dHash; mean Hamming distance scaled `mean_d/32 *
80`. No siblings (category=1) defaults to 60.

**Diagnostics:** `siblings`, `mean_distance`.

**Catches:** clones (P6 < 30), near-duplicates across versions
(`_v1`/`_v2`/`_v3` triples that look identical).

### P7 — Dynamic Range (weight 0.10)

**What it measures:** Luminance p99-p1 spread + mean chroma. Patterns
that collapsed to mid-gray score low.

**Diagnostics:** `luma_p1`, `luma_p99`, `spread`, `chroma_mean`.

**Catches:** broken renders (P7 < 20), patterns whose paint_fn
underflowed and produced flat output.

### P8 — Intent Fit (weight 0.16)

**What it measures:** Category-aware profile match. Each category has
expected bands (LO/MID/HI) on the four primary diagnostic axes
(`edge_density`, `block_std_p50`, `fine_energy`, `color_entropy`).
Percentile-bands are computed from the catalog itself, so the profile
adapts to what patterns actually do.

Score = % of profile axes whose actual band matches expected.

**Profile examples** (see `INTENT_PROFILES` dict in the script):
- Carbon & Weave: `edge_density=HI, block_std_p50=MID, fine_energy=HI, color_entropy=LO`
- Geometric: `edge_density=HI, block_std_p50=MID, fine_energy=MID, color_entropy=MID`
- Astro & Cosmic: `edge_density=MID, block_std_p50=MID, fine_energy=HI, color_entropy=HI`
- Tribal & Mythology: `edge_density=HI, block_std_p50=HI, fine_energy=MID, color_entropy=MID`

**Catches:** patterns whose ID promises one thing but renders another
(carbon_weave that's actually a smooth wash, tribal pattern with no
high-detail motif, geometric pattern with no edges).

**Limitation:** ~22 category profiles cover ~80% of pattern entries.
Unprofiled patterns default to 65 (no penalty). Adding a profile is
mechanical — edit `INTENT_PROFILES`, re-run.

---

## 4. Composite + tiers

Weighted sum of the 8 components (weights sum to 1.0):

```
composite = 0.16*P1 + 0.14*P2 + 0.10*P3 + 0.10*P4
          + 0.14*P5 + 0.10*P6 + 0.10*P7 + 0.16*P8
```

Tier thresholds (calibrated against the actual catalog distribution —
top ~10% are keepers):

| Tier      | Composite | Meaning                                            |
|-----------|-----------|----------------------------------------------------|
| keeper    | ≥ 70      | Ship-quality, no rework expected                   |
| ok        | 55-69     | Acceptable, low-priority polish                    |
| watch     | 45-54     | Borderline, schedule a re-render if time permits   |
| fix       | 35-44     | Visible issues, queue for renderer rebuild         |
| critical  | < 35      | Broken / placeholder / clone — rework before alpha |

Catalog distribution (2026-05-21 baseline, 797 patterns):

| Tier      | Count | %    |
|-----------|-------|------|
| keeper    | 143   | 18%  |
| ok        | 321   | 40%  |
| watch     | 185   | 23%  |
| fix       | 134   | 17%  |
| critical  | 14    | 2%   |

---

## 5. Re-running

```bash
python scripts/spb_pattern_quality_metric.py
```

The script reads `thumbnails/pattern/*.png` (~10s on 797 thumbnails) and
writes:
- `_workbook_metrics/pattern_quality.json` — full payload (~1.9MB)
- `_workbook_metrics/pattern_quality.js` — sidecar `window.SPB_PQM` for HTML

Then refresh `SPB_PATTERN_QUALITY_REVIEW.html` in a browser. No build
step. No server. `file://` URL works because the JS sidecar is loaded
via `<script src=...>`.

---

## 6. Using the HTML review surface

`SPB_PATTERN_QUALITY_REVIEW.html` features:
- **Header summary** — total count, tier counts (color-coded cards)
- **Filter toolbar** — search by id/category, category dropdown, sort,
  per-tier toggle pills (click to mute a tier)
- **Category rollup** — collapsible table showing mean/median/min/max
  composite per category, sorted weakest first (priority view for category-
  level rebuilds)
- **Pattern grid** — thumbnail + composite badge + per-component breakdown
  cells. Click a card → detail modal with full diagnostics JSON.
- **Detail modal** — large thumbnail, all 8 components with bars, raw
  diagnostic numbers.

Suggested workflows:

| Goal                                        | Setting                                              |
|---------------------------------------------|------------------------------------------------------|
| Find patterns needing immediate rework      | Sort: composite ↑, tiers: critical+fix only          |
| Audit a single category                     | Category: <X>, sort: composite ↑                     |
| Find clones                                 | Sort: P6 sibling-diff ↑                              |
| Find blurry/mushy patterns                  | Sort: P2 edges ↑                                     |
| Find blown-out / collapsed renders          | Sort: P7 dynamic range ↑                             |
| Find seamful patterns                       | Sort: P4 tileability ↑                               |

---

## 7. What PQM does NOT do

- **Doesn't render patterns.** Operates on existing thumbnails under
  `thumbnails/pattern/`. If a thumbnail is stale, the metric inherits the
  staleness. Re-bake the thumbnail and re-run.
- **Doesn't measure color quality.** Pattern thumbnails are rendered on
  neutral backgrounds — chroma is a P7 sub-signal but doesn't dominate.
  Pattern color comes from the base in actual zone composition.
- **Doesn't replace owner taste.** P8 intent profiles are heuristics.
  An owner-loved pattern that scores 50 isn't invalidated by the metric;
  it might just need its category profile loosened.
- **Doesn't fix anything.** Findings become Linear sub-tickets, not auto-
  PRs. The review surface is decision support.

---

## 8. Adding a category profile

When a category mass-fails P8 because the profile is wrong, edit
`INTENT_PROFILES` in `scripts/spb_pattern_quality_metric.py`:

```python
INTENT_PROFILES["My New Category"] = {
    "edge_density":   "HI",   # patterns are sharp-edged
    "block_std_p50":  "MID",  # moderate macro structure
    "fine_energy":    "HI",   # busy at fine band
    "color_entropy":  "MID",  # mixed-tone histogram
}
```

Re-run; check the HTML surface for the category rollup change.

If a category profile is uncertain, leave it out — unprofiled patterns
default to P8=65 (no penalty).

---

## 9. Common gotchas

- **Stale thumbnails:** If a pattern's renderer was updated but the
  thumbnail wasn't re-baked, PQM scores the old thumbnail. Re-bake first.
- **Unmatched IDs:** ~25 pattern registry entries don't have thumbnails
  on disk (capitalized IDs, alts that bake under a different name). They
  don't appear in the metric. Bake those thumbnails or rename the registry
  keys.
- **Scorecard category gaps:** Patterns missing from
  `paint-booth-0-catalog-scorecard.js` show as "Uncategorized" — they
  still get scored but P8 always falls back to the unprofiled default.
  Regenerate the scorecard to fix.

---

## 10. Linear

Findings are mirrored to Linear. PQM is the per-pattern view; M1-M8 is
the per-catalog view. When a category systematically fails (e.g. P8 < 50
on 80% of "Cultural & World" patterns), file a parent ticket under
SPB-105 (alpha release plan) with a Loom/HTML pointer to the relevant
review surface filter.
