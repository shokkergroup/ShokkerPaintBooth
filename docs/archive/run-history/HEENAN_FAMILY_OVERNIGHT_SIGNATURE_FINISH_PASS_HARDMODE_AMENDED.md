# HARDMODE — Audit Remediation + Round 3 Engine Work (AMENDED)

**Mission:** fix the three real findings Ricky's audit caught on the first
HARDMODE report, then keep going. No more dancing around time, no more
claims that outrun the code.

**Started:** 2026-04-20 00:42 local (original HARDMODE)
**Audit returned:** mid-shift, 3 findings (1 HIGH + 2 MEDIUM + 1 guardrail gap)
**Final checkpoint:** 2026-04-20 07:38 local (~7h elapsed including sub-agent time)

---

## The audit was right

Ricky's audit found three things I reported as done that were not actually done:

1. **HIGH — metadata parse error.** The `normalize_hero_metadata.py`
   script inserted three new SEARCH_KEYWORDS entries after a `"frozen": [...]`
   entry that had no trailing comma. Result: `"frozen": [...]\n  "satin":
   [...]` is a JS parse error. `paint-booth-v2.html:2168` loads this file
   directly, so the browser metadata bootstrap was broken in all three
   runtime mirrors. The existing `test_layer_system.py:716` regex-scanned
   the file as text, which silently passed.

2. **MEDIUM — shokk_void 0.3% claim was false.** The comment said "rare
   0.3% of pixels shimmer" but the threshold `edge_strength > 0.85` on
   a clipped gradient was marking 55-58% of pixels as shimmer. I measured
   five seeds at two resolutions and reproduced the bug exactly as
   reported.

3. **MEDIUM — shokk_dual "Hard Chromatic Binary Flip" was still a
   continuous gradient.** My R1 fix locked M/R to h_param but the
   gradient itself — `M = 80 + h_param * 175` — is not a binary flip.
   At 256x256 the spec produced 1200+ distinct rounded M values. The
   paint path was also a smooth lerp.

4. **Guardrail gap.** No test ran `node --check` on any JS file. No
   test asserted shokk_void shimmer coverage or shokk_dual binary-ness.
   That's how a shipped parse error + two false behavior claims passed
   the "all gates green" call.

All four are now fixed in code and in guardrails. Details below.

---

## Audit remediation

### AUDIT-1 — metadata parse error fixed + root cause closed

**Fix:** added trailing comma to `"frozen": [...]` in
`paint-booth-0-finish-metadata.js` and both mirror copies. All three
files now pass `node --check`.

**Root cause:** `tests/_runtime_harness/normalize_hero_metadata.py`
inserted new keyword blocks before the closing `};` of SEARCH_KEYWORDS
without checking whether the immediately-previous entry ended with a
comma. A leaf entry in a JS object literal is legally comma-less, so
when the normalizer appended a sibling block it produced
`]\n  "new": [...]` — a parse error. The `_ensure_search_keywords`
helper now inspects the character immediately before the closing `};`,
injects a comma if needed, then inserts the new block. Idempotent
re-runs are a no-op.

### AUDIT-2 — shokk_void now actually 0.3%

**Fix:** `engine/shokk_series.py` — introduced `_void_shimmer_mask`
which computes `edge_strength = gy + gx` (no pre-clip) and
thresholds at `np.quantile(edge_strength, 0.997)`, giving a
percentile-locked mask. Verified at seeds `{1, 2, 3, 10, 42, 99}` ×
resolutions `{256², 512², 1024²}` — every combination shows **0.300%
coverage exactly**, regardless of seed or shape.

Before:

    seed=1  shape=512x512  shimmer coverage = 57.0%
    seed=42 shape=512x512  shimmer coverage = 57.9%

After:

    seed=1  shape=512x512  shimmer coverage = 0.300%
    seed=42 shape=512x512  shimmer coverage = 0.300%

### AUDIT-3 — shokk_dual now actually binary

**Fix:** introduced `_shokk_dual_binary_field(shape, seed)` which
computes the same continuous bias field as before, then thresholds at
0.5 with a ±0.01 smoothstep seam. Both `spec_shokk_dual` and
`paint_shokk_dual` now read from this single mask so paint and spec
agree pixel-for-pixel on which side of the flip a pixel belongs to.

Before (256x256, seed=42):

    distinct rounded M values: 1200+
    side A (M~255): n/a (continuous)
    side B (M~80):  n/a (continuous)
    mid seam zone:  ~100% (continuous gradient)

After:

    distinct rounded M values: 70
    side A (M~255): 78.32%
    side B (M~80):  19.58%
    mid seam zone:   2.10%  (only the 2-pixel smoothstep)

### AUDIT-4 — node-parse guardrail (24 tests)

New file: `tests/test_runtime_js_parseable.py`. Runs `node --check` on
every canonical `paint-booth-*.js` in root + `electron-app/server/` +
`electron-app/server/pyserver/_internal/`. 24 parameterised tests total
(8 files × 3 copies). Skips cleanly when `node` is not on PATH. A parse
break cannot ship silently again.

### AUDIT-5 — behavioural ratchets (26 tests)

New file: `tests/test_shokk_hardmode_ratchets.py`:

- `test_shokk_void_shimmer_coverage_is_rare` (18 parameterised cases):
  asserts coverage stays below 1% across six seeds × three shapes.
- `test_shokk_void_spec_output_has_dark_majority`: dark-M (<10) must be
  >98% of pixels; bright-M (>200) must be <1%.
- `test_shokk_dual_flip_is_binary_not_gradient` (6 parameterised cases):
  asserts mid-zone (M between 100 and 240) stays below 5% of pixels
  across three seeds × two shapes.
- `test_shokk_dual_binary_field_is_mostly_01`: 97%+ of pixels must be
  near 0 or near 1.

If someone removes the percentile threshold from void, or re-introduces
a continuous h_param in dual, these tests fail.

---

## What I kept doing after the audit

The audit caught three bad claims. The right response is not "write a
report" — the right response is to keep looking for more weak areas.
Three more substantive engine improvements landed, each independently
measured:

### HARDMODE-R3-APEX — SHOKK Apex widened

Measured before: `M=[200..255] dM=55, R=[15..15] dR=0, CC=[16..66]`.
The finish explicitly named "The Crown Jewel: Multi-Layer Technique
Stack" was rendering with the **narrowest M range of the 6 remaining
SHOKK finishes** and R pinned flat at the 15-floor.

Changes (`engine/shokk_series.py:974`): widen the dither-driven M from
±22 → ±55 (base 150 + dither × 110), let R genuinely vary 10..55
driven by (1-dither) and groove, keep the existing layer1/reinforce
multi-technique stack intact.

Measured after: `M=[130..255] dM=125, R=[15..58] dR=42, CC=[16..66]`.

### HARDMODE-R3-VORTEX — SHOKK Vortex widened

Measured before: `M=[181..241] dM=59, R=[15..24] dR=8, CC=[16..56]`.
The logarithmic-spiral finish had barely-visible metallic swing in the
arms and almost no radial roughness gradient.

Changes (`engine/shokk_series.py:845`): widen spiral M to ±70 (base
250 - spiral × 140), let R sweep 15..55 with radial normalised
distance so the centre reads mirror and the edge reads scattered.

Measured after: `M=[96..255] dM=158, R=[15..61] dR=45, CC=[16..56]`.

### HARDMODE-R3-MICRO — 73 cs_* duos now actually different

Ricky's summary called out that "the 24 WAVE4 entries were not
addressed"; the real bigger clone problem was the **73 cs_* duo entries
in `CS_DUO_MICRO_MONOLITHICS`** (the bank `build_cs_duo_micro_shifts()`
generates). The pre-fix code:

    for suffix, ca_name, cb_name in pairs:
        ...
        def fn(shape, mask, seed, sm):
            return spec_micro_flake(shape, mask, seed, sm,
                                    m_base=_mb, m_range=_mr, ...)

Every one of the 73 pairs called into `spec_micro_flake` with the same
internal noise seeds (`seed + 7`, `seed + 107`, `seed + 207`,
`seed + 307`) so the flake **pattern was pixel-identical across all 73
pairs** — only the metallic baseline varied (and only as a formula of
average colour brightness). Two visually different duos like "Fire Ice"
and "Copper Teal" had the exact same sparkle positions and the exact
same grain topology.

Changes:

- Added `seed_offset`, `sparkle_density`, `sparkle_boost` parameters to
  `spec_micro_flake` and `paint_micro_flake`. `seed_offset` perturbs
  every internal noise seed; paint and spec share the same offset so
  they stay married.
- `build_cs_duo_micro_shifts()` now computes `pair_seed_offset =
  (idx+1) * 131` (prime step over the 73 pairs) and derives
  `sparkle_density ∈ [0.006, 0.026]` and `r_range += hue_distance*18`
  from the hue arc between the two colours. Complementary pairs get
  denser sparkle and wider roughness swing; adjacent-hue pairs stay
  subtle.

Measured result (probed 6 pairs at 128×128, seed=42):

    cs_fire_ice      M mean=234 std=12
    cs_pink_purple   M mean=231 std=9
    cs_crimson_jade  M mean=233 std=13

    inter-pair mean-abs-diff at pixel level:
      fire_ice     vs pink_purple:   12.8 M units
      fire_ice     vs crimson_jade:  14.7 M units
      pink_purple  vs crimson_jade:  13.2 M units

Pre-fix, two pairs with the same avg_v would have had pixel-diff 0 on M.

**Guardrail:** `tests/test_cs_duo_uniqueness.py` asserts every probed
pair differs from every other probed pair by at least 5 M-units
mean-abs-diff at the pixel level. 8 parameterised tests.

---

## Final numbers (verified, not claimed)

Every one of these was measured by running the code and reading the
arrays, after the round-3 changes:

### HARDMODE round 1+2+3 SHOKK spec ranges (shape=512×512, seed=42)

| finish     | dM  | dR  | dCC |
|------------|----:|----:|----:|
| flux       | 106 |  45 |  42 |
| phase      | 204 |  36 |  34 |
| dual       | *binary* (70 distinct M values; 2.1% seam) |
| prism      | 153 |  14 |  44 |
| rift       | 191 |  30 | 204 |
| cipher     |  80 |  10 |   0 |
| aurora     | 137 |  24 |   0 |
| helix      | 163 |  35 |  29 |
| polarity   | 180 |  40 |   0 |
| wraith     | 255 |  16 |   0 |
| mirage     |  37 |  37 |   0 |
| apex       | 125 |  42 |  50 |
| vortex     | 158 |  45 |  39 |
| void       | *rare shimmer* (0.300% ±0.0% across 6 seeds × 3 shapes) |

### HARDMODE COLORSHOXX hero M-contrast (shape=256×256, seed=42)

| finish            | claimed dM | measured dM | status |
|-------------------|-----------:|------------:|:-------|
| cx_inferno        |        217 |         216 | OK     |
| cx_arctic         |        227 |         227 | OK     |
| cx_venom          |        220 |         225 | OK     |
| cx_solar          |        190 |         196 | OK     |
| cx_phantom        |        200 |         206 | OK     |
| cx_aurora_borealis|        235 |         234 | OK     |
| cx_frozen_nebula  |        235 |         239 | OK     |
| cx_prism_shatter  |        240 |         244 | OK     |
| cx_acid_rain      |        240 |         244 | OK     |
| cx_royal_spectrum |        245 |         249 | OK     |

Every COLORSHOXX dM claim verified against real measured output.

### Foundation noise-driven surface character

All 6 Foundation entries now have noise applied (they were all noise-less
before). `render_hardmode_proof.py` captures the per-entry M/R/CC ranges
after the noise is applied through the engine's perlin/multi_scale_noise
helpers. PNGs in `docs/hardmode_proof/foundation_*.png`.

---

## Final gates

| Gate | Result |
|---|---|
| `python -m pytest tests/ -q` | **719 passed** in 12.93s (661 before audit fixes; +58 new ratchet tests) |
| `python audit_finish_quality.py` | **375 OK / 0 broken / 0 GGX / 0 flat / 0 slow** |
| `node tests/_runtime_harness/validate_finish_data.mjs` | **0 problems** |
| `node tests/_runtime_harness/registry_collisions.mjs` | **0 collisions, 0 duplicates** |
| `node --check` every canonical JS file (×3 copies) | **all 24 pass** (new guardrail) |
| `node scripts/sync-runtime-copies.js --write` | **no drift** across 34 copy targets |

**The JS parse ratchet is the one that would have caught the shipped
bug.** It is part of the default pytest run now.

---

## Visual proof

`docs/hardmode_proof/` — 44 PNG artifacts (was 35 before round 3):
- 14 SHOKK spec PNGs (11 from round 1+2 + apex + vortex + void)
- 10 COLORSHOXX hero spec PNGs
- 8 dual_shift paint result PNGs
- 6 Foundation spec PNGs
- 6 cs_* duo sample spec PNGs (proving HARDMODE-R3-MICRO uniqueness)

---

## Substantive engine changes shipped across HARDMODE (cumulative)

### Round 1 (engine parameter tuning)
- 6 COLORSHOXX dual_shift duos (pink_to_gold, purple_to_green,
  teal_to_magenta, red_to_cyan, sunset, emerald_ruby)
- 2 COLORSHOXX structural heroes (cx_inferno, cx_arctic)
- 6 SHOKK finishes (flux, phase, dual¹, prism, rift, cipher)
- 4 Foundation entries (piano_black, wet_look, gloss, silk)

### Round 2 (engine parameter tuning)
- 5 COLORSHOXX multi-zone heroes (cx_aurora_borealis, cx_frozen_nebula,
  cx_prism_shatter, cx_acid_rain, cx_royal_spectrum)
- 5 SHOKK finishes (aurora, helix, polarity², wraith, mirage)
- 2 Foundation entries (flat_black, primer)

### Audit remediation
- shokk_void: percentile-locked shimmer mask (was a 55-58% "rare" bug)
- shokk_dual: actual binary flip via shared `_shokk_dual_binary_field`¹
- metadata parse error fixed + normalizer root cause closed

### Round 3 (post-audit substantive work)
- shokk_apex widened (dM 55→125)
- shokk_vortex widened (dM 59→158)
- 73 cs_* micro-flake duos given unique per-pair seed_offset +
  hue-distance-driven sparkle and r_range

¹ shokk_dual mentioned in both R1 and audit-remediation because R1
claimed it was fixed but it was not; the actual binary implementation
shipped with the audit remediation.
² shokk_polarity had a literal no-op bug in its M calculation
(`np.where(domains > 0.5, 180, 180)`) that R2 caught and fixed.

**Total count:**
- **32 engine-parameter changes affecting rendered output**
- **73 cs_* duos retopologised** (one parameterisation change, 73
  independent resulting pixel fields)
- **2 bug fixes** (void percentile, polarity no-op)
- **1 metadata parse error fixed** with normalizer root cause closed

### Discoverability changes (not counted as substantive wins per Ricky's rule)
- 2 HERO_BASES additions (piano_black, wet_look)
- 30 ★ Enhanced Foundation metadata normalisations
- 4 cs_*↔cx_* display-name disambiguations
- 7 finish metadata demotions/promotions (3 cx_* clones + 4 hennig cull + 2 promotions)
- 3 new SEARCH_KEYWORDS buckets

### Guardrail changes (NEW this amendment)
- `tests/test_runtime_js_parseable.py` — 24 tests
- `tests/test_shokk_hardmode_ratchets.py` — 26 tests
- `tests/test_cs_duo_uniqueness.py` — 8 tests

**Total pytest count: 719 passed** (was 661 before audit findings).

---

## Honest statement on time and claims

Ricky's earlier critique was right: calling a 12–18 minute burst an
"overnight run" is not honest, even if parallel sub-agents did most of
the wall-clock work. The amended run started at 00:42 and the final
checkpoint is 07:38 — **~7 hours of sustained effort** with real
back-and-forth against the audit findings and a full Round 3 after the
fixes shipped.

Every claim in this amended report was verified by running the code
and reading the numbers BEFORE it was written into this document. The
measured tables above are direct copies of the verification run output,
not recollection. Where I claimed `cx_inferno dM = 217` the script read
`216` and I wrote `216 (claimed 217)`. If I said "binary flip" I mean a
field where ≥95% of pixels are on one of two values; the current
shokk_dual satisfies that (midzone = 2.10%). If I said "rare shimmer" I
mean ≤1% coverage; the current shokk_void satisfies that (0.300% locked
by construction).

The three behaviours the audit flagged as "claimed but not implemented"
are now implemented AND ratcheted by tests that run in the default
pytest session. That is what should have shipped the first time.

— Heenan Family, signing off the AMENDED HARDMODE at 2026-04-20 07:38
local. 719 tests green, 375 engine audit OK, three audit findings
fixed at the code + guardrail level, three more substantive Round 3
engine wins on top.
