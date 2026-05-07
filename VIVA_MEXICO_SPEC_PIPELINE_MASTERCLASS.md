# Viva Mexico Spec Pipeline — Technical Masterclass

This document captures **what we learned**, **how the procedural spec treatment works**, and **how to repeat or evolve it** for other finish families (including iRacing-style metallic / roughness / clearcoat packs). It reflects the state of `engine/paint_v2/cultural_viva_mexico.py` as implemented in-session.

---

## 1. Why this exists

### The problem

Image-backed “monolithic” finishes ship with author-painted **`{finish_id}_spec.png`** plates. Those plates are a good start but tend to read as:

- **Too uniform** in gloss (one dominant roughness “shade” across large regions).
- **Weak motif relief** when the base spec does not encode emboss-level contrast at ridges.
- **Misaligned with Paint Lab DNA** when dark paint areas still carry hot metallic/clearcoat (wrong “void” read).

Tuning **every** finish by hand in Photoshop would not scale.

### The solution

**One code path** runs for **every** finish ID listed for Viva Mexico:

1. Load resized **paint RGB** + **spec RGBA** from disk.
2. **`_pre_adjust_viva_mexico_spec`** — procedural enhancement *before* user-facing `sm` (spec multiplier) and mask multiply.
3. **`_post_adjust_viva_mexico_spec`** — DNA-safe **void clamp** *after* composite, without destroying ridges or highlight corridors.

No per-finish branches: behavior differs by **paint content**, **mask**, and a **stable hash of `finish_id`** (not runtime randomness).

---

## 2. Assets and layout

| Asset | Path pattern |
|--------|----------------|
| Paint (diffuse) | `assets/reference_textures/cultural/viva_mexico/{finish_id}.png` |
| Spec | `assets/reference_textures/cultural/viva_mexico/{finish_id}_spec.png` |
| Manifest (optional) | `assets/reference_textures/cultural/viva_mexico/manifest.json` |

**Finish list:** `_FINISH_IDS` comes from `manifest.json` → `finishes[].id`, with a **fallback tuple** if the file is missing.

**Caching:** `_load_rgb_cached` / `_load_spec_cached` use `@lru_cache` keyed by `(finish_id, mtime_ns)` so iteration during development does not thrash disk.

---

## 3. Channel semantics (this codebase)

The spec PNG is **RGBA**. In this pipeline:

| Index | Name in code | Role in logic |
|-------|----------------|----------------|
| 0 | **M** | Metallic / metal-weight style channel — driven **up** where we want flash and ridge read. |
| 1 | **R** | Roughness-style channel — in *this* implementation, **lower R → shinier** (more highlight); bumps **subtract** R to add gloss. |
| 2 | **Cc** | Clearcoat-style channel — pearlescence / coat weight; often **pulled toward ~16** on peaks and accents. |
| 3 | α | Forced to **255** in post. |

**Important:** Naming is historical (“R” for roughness). The **numerical direction** that matters is what the **game/shader** expects. If your consumer interprets channels differently, **invert the sign** of the deltas that touch **R** (or remap once at export). This doc describes **this repo’s** convention.

---

## 4. End-to-end data flow

```
_load_spec(finish_id)
    → resize to render shape (INTER_AREA)
    → float32 working buffer

_load_rgb(finish_id)
    → resize to render shape (INTER_AREA)
    → drives all paint-aware masks

_pre_adjust_viva_mexico_spec(spec, tex_rgb, mask, finish_id)
    → heavy lifting (see §6)

_spec_from_asset then:
    → Ch0 *= sm * mask + outside fill
    → Ch1, Ch2 *= mask + outside defaults
    → uint8

_post_adjust_viva_mexico_spec(spec_u8, tex_rgb, mask)
    → DNA void clamp on dark paint (protected zones)
    → final clamps
```

**Global detail scalar:** `DS` (currently **`1.59`**) multiplies most additive/subtractive **weights** so you can tune “overall intensity” in **one place** instead of editing twenty literals.

---

## 5. Core ideas we learned (the “theory”)

### 5.1 Treat the paint plate as ground truth for masks

**Luma** (Rec.709) and **edge magnitude** (Laplacian on 8-bit-scaled luma, percentile-normalized on-mask) give:

- **`dark_paint`**: `gray < 34/255` — aligns with Paint Lab “dark paint DNA” style thresholds.
- **`dark_interior`**: dark **and** low edge — safe to flatten spec without killing motif outlines.
- **`edge_n`**: where motif **lines and emboss** live — worth boosting spec contrast.

### 5.2 Spec “color” in a PBR sense is often **triplet variation**

Players perceive “different greens” or “gold flashes” not from painting arbitrary RGB into the spec file but from **different combinations** of **metal vs roughness vs clearcoat**. So we:

- Derived **warm / cool / green / yellow-hint weights** from **paint RGB** (same resolution as spec).
- Applied **correlated** changes to **M, R, Cc** so neighboring regions diverge in **read**, not just noise in one channel.

### 5.3 Repeatable variety beats true randomness

Using `numpy.random.default_rng` with seeds derived from **`finish_id`** means:

- Two finishes get **different** sparkle grids.
- The **same** finish is **deterministic** across runs (good for QA and caching).

### 5.4 Protect corridors from void logic

Bright **thin ridges** (crest residual after Gaussian baseline removal) get:

- **Hard cores**: pin metallic, clamp roughness, snap clearcoat (within clip limits).
- **`protect_lw`**: dilated halo so **`_post_adjust`** does not **void-wash** those pixels.

### 5.5 Layer detail at multiple frequencies

- **Low frequency:** chromatic steering and green phase split.
- **Mid:** ridge relief + sparse dot grids (different densities / thresholds).
- **High:** multi-sine octaves + weave + **nano** crystalline fringe.

This avoids “single-frequency shimmer” and reduces visible banding.

---

## 6. Stage-by-stage: `_pre_adjust_viva_mexico_spec`

Below is the **conceptual order** (see source for exact constants).

### 6.1 Dark interior void blend (pre-sculpt)

Where **`dark_interior`** is strong, blend spec toward a **matte / high-roughness / low-clearcoat** baseline so DNA-dark regions do not glow.

### 6.2 Paint-chroma steering

From normalized paint channels:

- **`warm_w`**: red-orange pull vs secondary channels.
- **`cool_w`**: blue pull.
- **`green_dom`**: green dominance.
- **`yellow_hint`**: `(R+G)/2 - B` gated by minimum R and G — sparse gold/lemon **hints**.

These weight **additive maps** into **R, M, Cc** with **`chrom_interior`** reducing strength inside problematic dark interiors.

### 6.3 Green “phase split”

A **sin phase** over **x/y** with frequencies perturbed by **`seed`** breaks large uniform green fields into **alternating gloss textures** without manual masks.

### 6.4 Ridge relief (`pop`)

**Edge^n** (power < 1) × interior suppression → boosts **M**, reduces **R**, may crush **Cc** on **ridge_peak** mask.

### 6.5 Sparse dot grids (three passes)

- **`rng` / `rng_b` / `rng_c`**: independent sparse binary grids resized with **NEAREST** so specks stay **crisp**.
- Different **tonal gates** (`mid_tone`, `shadow_band`, `flat_rig`) × **`flat_w`** (anti-speckle on edges) × dark suppression.
- Dot thresholds and grid sizes control **density** vs **noise**.

### 6.6 Highlight crest (“living water” generalized)

**`_viva_mexico_highlight_crest`** returns:

- **`streak_soft`**: smooth envelope strength.
- **`streak_core_f`**: pin cores.
- **`protect_lw`**: dilated protection for post.

**Wet** terms add glossy envelope; **ring_lw** morphologically sharpens core vs halo.

### 6.7 Rare gold/lemon sparks

**`rng_d`** full-res uniform — only survives where **`yellow_hint`** is sufficient → **M↑ R↓ Cc↓**, edge-weighted.

### 6.8 Multi-octave micro + curl

Three summed sines (`oct_a/b/c`) modulate **R, Cc, M** with **`mic_g`** (gray × edge × mask × dark suppression). Weights mix **`hue_warm` / `hue_cool` / `hue_green`**.

**`curl`**: extra term gated by **`yellow_hint`**.

### 6.9 Diagonal weave

Finish-seeded frequencies along **`(x+y)`** and **`(x−y)`** to break axis-aligned artifacts.

### 6.10 Nanoscopic fringe (“nano”)

Higher spatial frequencies than octaves, phase from **`seed >> 11`**, gated by **`nano_g`** — tuned for **mip-0 sparkle** / fine shear; **hue-aware** on **Cc**.

### 6.11 Anisotropic ripple

Low-amplitude **R** modulation using screen-space sine product; damped under **`protect_lw`**.

### 6.12 Morphological pin / core–ring sharpen

Local **M** maxima → **core** vs **ring**: cores get **shinier** (more **M**, less **R**), rings get a **rougher halo** read — reads as **faceted glitter** under motion.

---

## 7. `_post_adjust_viva_mexico_spec`

After mask/sm composite as uint8:

- Recompute **`dark_paint`**, **`edge_n`**, **`protect_lw`**.
- **`void_px`**: inside mask, dark paint, **not** ridge-protected, **not** in crest protect.
- Force **M low**, **R high**, **Cc low** on void pixels (exact caps in source).

This is the **DNA safety net** when pre-pass missed a pocket.

---

## 8. Key implementation tactics (“how we moved fast”)

1. **Single module** — All logic in `cultural_viva_mexico.py`; registry builds `(spec_fn, paint_fn)` per ID.
2. **One global knob** — `DS` scales almost every intentional artistic weight.
3. **No per-finish `if`** — Variation comes from **data** + **hash(seed)** + **paint**.
4. **Vectorized NumPy + OpenCV** — Full-frame ops; no Python pixel loops.
5. **Mirrors** — Same file copied to Electron server bundles so runtime picks up changes:

   - `electron-app/server/engine/paint_v2/cultural_viva_mexico.py`
   - `electron-app/server/pyserver/_internal/engine/paint_v2/cultural_viva_mexico.py`

   After edits, sync mirrors and run `python -m py_compile engine/paint_v2/cultural_viva_mexico.py`.

---

## 9. Tuning guide (practical)

| Symptom | First knob | Second knob |
|---------|------------|-------------|
| Overall too weak / strong | **`DS`** | Scale ridge `pop` coefficients only |
| Too noisy / sandy | Raise dot thresholds (`> 0.974` → stricter) | Reduce **`nano`** amplitudes |
| Flat green fields | Increase **`phase_g`** multiplier or **`green_dom`** split | |
| Not enough warm sparkle | Lower **`spark_u`** threshold slightly | Increase **`yellow_hint`** gates |
| Metal pegging at 255 | Lower **`DS`** or reduce **`M`** boosts on **`pop`/dots** | |
| Dark areas still glossy | Strengthen **`blend_v`** or post void caps | Check preview **luma parity** with `34/255` |

---

## 10. Evolution timeline (session narrative)

This section records **intent** so future readers understand *why* numbers moved.

1. **Catalog-wide rollout** — Agave-only tuning generalized to **all** VM IDs via shared `_pre_adjust_*` / `_post_adjust_*`.
2. **Chromatic steering** — Paint RGB drives **M/R/Cc** variation (warm/cool/green/yellow).
3. **Detail wave 1** — Introduced **`DS ≈ 1.36`** and multi-octave / weave / sparks.
4. **Detail wave 2** — Raised **`DS`** toward **`1.59`**, denser grids, **`nano`** high-frequency pass.

If you change **`DS`** again, note the date and subjective result here.

---

## 11. Replication checklist for another cultural pack

1. Copy the module pattern: **`cultural_<pack>.py`** with `_ASSET_DIR`, manifest optional.
2. Confirm **channel meanings** in the consuming shader — **flip R deltas** if needed.
3. Align **`dark_paint` threshold** with your Paint Lab / preview DNA if applicable.
4. Keep **`_finish_rng_seed`** for deterministic grids.
5. Add **`DS`** as your first balancing lever.
6. Ship **mirrors** if your app loads duplicated engine paths.

---

## 12. Caveats

- **Absolute luma threshold** `34/255` assumes preview gamma/exposure consistent with authoring. If DNA preview shifts, revisit **void** and **`dark_paint`** alignment.
- **Clipping:** Aggressive **`DS`** can saturate **M**; monitor visually and in histograms.
- **iRacing export:** This repo documents **this pipeline’s** channel **direction**. Always verify against **iRacing’s** material expected ranges before publishing public textures.

---

## 13. Primary source file

Authoritative implementation:

`engine/paint_v2/cultural_viva_mexico.py`

Registry export: **`VIVA_MEXICO_MONOLITHICS`**.

---

## 14. Document maintenance

When you materially change the pipeline, update:

- **`DS`** default and date.
- New stages (add a §6 subsection).
- Any change to **channel direction** or **void caps**.

---

*Written to preserve operational knowledge for future refinement — “revolutionary” spec authoring lives in repeatable systems, not one-off surgeries.*
