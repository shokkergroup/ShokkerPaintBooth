# 🔥 FRACTURED FLAMES rebuild — 144 → 75 (2026-08-30)

> Owner: *"we have 3 FRACTURED FLAMES categories and way too many finishes. We
> only need about 75 total flames. And MANY of them are repeats and redundant or
> just lazy/not good. Keep some of the better one's but make new math and styles
> and apply what we've learned in the Spec channel to make them really come to
> life."*

## What the old shelf actually was

`_flames_work/triage.py` rendered all 51 structures at 2048 and scored them.

**It was a cross-product, not a catalog.** The 135 `flm_*` ids are
`{51 structures} × {ignite, topo, dance} × {a palette name}`, and
`flames_catalog_2026._art_work_cached` calls the structure with **no palette
argument**:

```python
art = fm.FLAME_STRUCTURES[row["flame"]]((_WORK, _WORK), 7)   # no palette
```

So two things were true of every card:

* a structure's 2–3 cards carried **byte-identical paint** — verified with
  `np.array_equal` on `flm_lava_flow_{ignite,topo,dance}_classic`;
* every card named **(Blue)**, **(Violet)** or **(Green Toxic)** was **orange**
  — `flm_curl_streamers_ignite_blue` measures mean RGB (0.366, 0.228, 0.173).
  The palette only ever reached the spec.

**And 42 of the 51 structures were posters, not fields.** Car-band energy (the
8–32px window the driver actually sees, r 32..256 on a 2048 canvas):

| structure | car-band | what it is on a whole car |
|---|---:|---|
| `gas_ring` | 0.003 | one ring |
| `will_o_wisp` | 0.004 | one glow |
| `radial` | 0.005 | one sunburst |
| `candle` | 0.007 | one flame, 22% coverage |
| `mach_cone` | 0.009 | one cone |

Only **9 of 51** passed car-band + coverage + distinctness. The nine legacy
`fml_*` cards in the same shelf were measured too: **8 of 9 are also posters**
(`fml_caldera_rim` 0.070), which is why the rebuild is exactly 75 and not 84.

## What replaced it

**One card per idea. No matrix.** Five chapters of 15, tracing the life of a
fire — the arc is the category's identity, the way RELICS is old-world occult
and FOUNDRY is worked metal:

| chapter | what it is | spec character |
|---|---|---|
| 🜂 IGNITION | the catch — sparks, char creep, the front before there is a flame | unburnt matte → scorch → oxide scale → the ignition point |
| 🔥 FLAME | the body — reaction sheets, wrinkled fronts, turbulent braids | dead soot → vitrified skin → bare metal → wet core |
| ⚡ PLASMA | past flame — arcs, streamers, ionisation, magnetised jets | the Fractured night-carrier population lives here and nowhere else |
| 🌋 MOLTEN | what melts — lava skin, slag, weld pools, quenched glass | ash crust → oxide scale → bare steel → wet melt |
| 🜃 CINDER | after — ember beds, ash, soot, clinker, spall | mostly dead, with retained heat showing as metal |

### Colour is physics, not a tag

`kit.blackbody()` integrates **Planck's law** against an analytic fit of the
**CIE 1931** colour-matching functions (Wyman/Sloan/Shirley 2013), so 900K really
is a dull cherry and 3400K really is warm white. `FUELS` then adds real
**chemiluminescence** — copper green, cupric blue, strontium crimson, sodium
amber, potassium lilac, barium apple, lithium magenta, boron emerald. **A card's
palette is what is burning, and it drives the paint.**

Three mechanisms give a card its chroma range, all of them structural:

1. **the fuel's own ladder** — eight quantised blackbody tiers, re-spanned in
   value (raw emissive weighting lands all eight between luma 0.09 and 0.63,
   which reads as one muddy midtone wash);
2. **a doped population** — a minority of the bed burns a *second* chemistry, in
   coherent 40–80px regions, because a fire bed is chemically zoned (a copper
   nail, salt-soaked driftwood, treated timber);
3. **the unburnt substrate** — fire happens *on* something, and that something
   keeps its own colour until the heat arrives.

Six cards are declared `mono=True` with a written reason: ash and soot are grey,
and forcing a second hue family on Cold Ash would be a lie about the material.

### The spec follows the design

`kit.flame_spec()` implements Spec Guide v1 §7–§9 against the **same heat field
that made the paint**:

* **complete material CARDS chosen per coherent cell** — never a linear smear
  between tuples, and never a per-pixel decision (`cell_mean` averages the heat
  inside each label first);
* **every band is a materially different surface** — the first pass stacked
  soot / porous / flat / ash in one map, four names for "rough dielectric with no
  coat" separated by 10–30 bytes of green, and the maps rendered as flat cyan
  with black dots;
* **band edges are percentiles of the card's own heat**, so a field whose
  histogram piles up in one place still populates its bands in the designed
  proportions (with absolute edges, Weld Pool handed almost every pixel the same
  material: roughness σ 14.3, clearcoat σ 9.1);
* **2–6px dark-chrome hot edges** on the reaction front, capped at 7.5% of the
  surface so the lip never buries the band map;
* **the clearcoat field is offset** from the metal/roughness field, so the two
  specular lobes peak at different view angles;
* **proportional roughness spread** — an absolute ±13 was wider than the gap
  between `gloss` (30) and `wet` (18), so the two stopped being distinguishable.

## Gates — 75/75

`python _flames_work/verify.py` — all measured at 2048, best of 2 cold runs:

| gate | floor | result |
|---|---|---|
| render time | ≤3.0s | median **2.35s**, max 2.96s |
| car-band (8–32px) | ≥0.45 | **0.469 – 0.929** |
| coverage (8×8) | ≥0.95 | **1.00** on all 75 |
| shade tiers | ≥7 of 12 | **7 – 12** |
| spec channel σ | ≥18 each | **M 86–115 · R 77–103 · Cc 74–101** (old shelf: 6 / 18 / 2) |
| spec-follows-design | ≥0.30 | **0.31 – 0.83** |
| uniqueness (in-set) | <0.80 | max **0.75** |

Plus the two catalog-wide gates:

* `scripts/spb_uniqueness_gate.py --ids <75>` — **75/75 pass**, nearest
  neighbour anywhere in the 2,400-card catalog only **34–37%**.
* `tests/regression_new_categories_all_sizes_test.py ffl_` — every card renders
  both channels at **48 / 256 / 512 / 1024 / 2048**.

> **On that gate's "spec-trace low" advisory:** it correlates spec *luma* against
> paint *luma*. This band map is deliberately non-monotonic in luma — `wet` packs
> darker than `ash` — so a correct card scores near zero there by construction.
> The harness measures the real question instead: classify each cell to its
> nearest material card and rank-correlate against the cell's own heat.

## What I got wrong on the way (so the next agent doesn't repeat it)

* **Green gates, bad look.** The first full pass was 75/75 and the contact sheet
  was confetti. The fix was `cell_mean` — deciding the material per cell rather
  than per pixel — and cutting the per-cell hue rotation from ±19° to ±4°. I had
  been chasing a HUE metric that was pushing the paint toward randomised colour.
* **The contact sheet lied.** A 2048 spec downsampled to 256 aliases 10px cells
  into pixel noise. One whole iteration went into "fixing" a defect that was in
  the thumbnail, not the finish. Spec panels are 1:1 crops now.
* **Fewer PDE steps is better.** `wrinkle` at 26 steps: 0.82s / band 0.589. At
  14: ~0.45s / 0.66. The extra diffusion only smoothed away the cusps the
  primitive exists to make.
* **Rectifying a sine halved the band energy.** `|roll|` doubles the spatial
  frequency but spikes the histogram; signed roll measured 0.87 vs 0.42.
* **Cells cut from the field itself are worse than a plain lattice.** Sparse
  fields segment into one giant background blob (Touchpaper fell to 2 shades),
  and guarding against that means paying for both paths — a dozen cards hit 6–9s.
* **A shared machine breaks timing gates.** The owner's app server rendering
  picker swatches reported 6–9s for cards that measure 1.7–2.5s quiet. The
  harness now takes the best of 2 cold runs, same policy as
  `audit_render_perf.py --trials 3`.

## Files

| file | role |
|---|---|
| `engine/expansions/fractured_flames_kit_2026.py` | the engine: blackbody colour, FUELS, 12 field primitives, `flame_spec` |
| `engine/expansions/fractured_flames_2026.py` | the 75 recipes + chapter spec grammar |
| `_flames_work/triage.py` | scores the OLD 51 structures (the evidence above) |
| `_flames_work/verify.py` | the gate harness, one verdict line per card |
| `FRACTURED_FLAMES_PROGRESS.jsonl` | append-only per-card log across 43 iterations |

Old `flm_*` and `fml_*` ids stay registered in both engines so saved projects
keep rendering; they are only retired from the picker.
