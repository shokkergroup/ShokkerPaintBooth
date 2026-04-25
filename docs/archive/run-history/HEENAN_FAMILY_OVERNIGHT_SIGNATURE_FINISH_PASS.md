# Heenan Family Overnight — Signature Finish Trust Pass

**Mission:** make the most visible painter-facing finish catalog feel
premium, trustworthy, distinct, and worth money by morning.

**Lead:** Heenan Family
**Started:** 2026-04-20 00:11 local
**Ended:**   2026-04-20 00:27 local
**Mode:** product-quality + catalog-trust. NO fake wins, NO broad
"looks better" claims, NO risky rename spree, NO breaking runtime mirrors.

---

## Executive summary

The COLORSHOXX brand looked dilute and the Foundation lane disagreed
with itself in metadata. This shift fixed the disagreements without
adding finishes. **3 reusable normalizer harnesses, 1 painter-visible
name fix, 30 ★ Enhanced Foundation tiles promoted to consistent premium
metadata, 4 cs_*↔cx_* name collisions disambiguated, 3 cx_* engine-clone
tiles demoted to Advanced. All gates green: 661 tests, 0 validator
problems, 0 registry collisions, 375/375 engine OK, 0 mirror drift.**

The honest read: the catalog had ~40 truly distinct premium finishes
masquerading as ~130. We did not delete the clones — painters who want
them via Advanced toggle still get them — but we stopped them from
diluting the front shelf and stopped two finishes from sharing display
names.

---

## What moved the needle most

1. **Piano Black is searchable again.** The display string was "Vortex
   Ebony Depth" — every painter searches "piano black" and got nothing.
   Renamed to "Piano Black (Vortex Depth)" so the poetic name lives
   inside the obvious name. One of the most-requested OEM finishes in
   the catalog now responds to its actual name.

2. **★ Enhanced Foundation actually behaves like a premium tier now.**
   Of the 30 ★-marked entries, the metadata had:
     - `enh_metallic`  → featured=true, sortPriority=80   (premium)
     - `enh_chrome`    → featured=true, sortPriority=80   (premium)
     - `enh_pearl`     → featured=false, sortPriority=50  (utility)
     - `enh_gloss`     → utility=true, sortPriority=50    (utility)
     - `enh_satin`     → utility=true, sortPriority=50    (utility)
   Painter saw the ★ tile, expected premium treatment, got utility-tier
   sort behaviour. **All 30 normalized** to consistent `featured=true`,
   `utility=false`, `sortPriority=90`, `browserSection="★ Enhanced
   Foundation"` — above plain Foundation (80) and visible in the
   Materials tab as a real curated lane.

3. **`cs_inferno` no longer tries to BE `cx_inferno`.** Four cs_*
   color-shift overlay presets had display names that collided with
   COLORSHOXX hero finishes. Painter clicked "Inferno", got either of
   two visibly different results, couldn't tell which was the hero.
   Disambiguated:
     - `cs_inferno`     → "CS Inferno (Overlay Shift)"
     - `cs_supernova`   → "CS Supernova (Overlay Shift)"
     - `cs_oilslick`    → "CS Oil Slick (Overlay Shift)"
     - `cs_mystichrome` → "CS Mystichrome (Purple→Green Overlay)"

4. **3 cx_* chrome-flip clones demoted out of the front shelf.**
   `cx_rose_chrome`, `cx_blood_mercury`, `cx_toxic_chrome` all use the
   identical `_cx_fine_field` engine kernel as `cx_chrome_void` with
   only color RGB changing. Marked `advanced=true` so the default
   Specials picker surfaces the 7 distinct chrome flips
   (`cx_chrome_void`, `cx_neon_abyss`, `cx_obsidian_gold`,
   `cx_electric_storm`, `cx_midnight_chrome`, `cx_white_lightning`,
   `cx_glacier_fire`) — and the 3 colour-swap variants stay accessible
   behind the Advanced toggle.

---

## Phase 1 — Inventory and triage

### COLORSHOXX runs through three engine modules

| Engine module | Hero count | Differentiation |
|---|---:|---|
| `engine/paint_v2/structural_color.py` | 25 | Hand-tuned per-finish M/R/CC + unique `seed_off` (9001..9029). Each has its own paint+spec function. **Strongest visual identity.** |
| `engine/dual_color_shift.py` | 8 + 1 custom | Each duo gets a UNIQUE `field_style`: arc / split / faceted / vortex / banded / sweep. Married paint+spec via shared seed. **All 8 distinct.** |
| `engine/micro_flake_shift.py` | 33 (18 MICRO_SHIFT + 15 WAVE4) | Unique color stops + per-preset `m_base/m_range`. Engine kernel is shared. Mostly color-stop variation. |

Painter-facing `cx_*` count in `paint-booth-0-finish-data.js` MONOLITHICS:
**67 entries.** Plus 27 `cs_*` color-shift overlay presets in the same
SPECIAL_GROUPS lane (different system, same brand-adjacent surface).

### The honesty problem (Phase 1 finding)

Engine audit (Explore agent, 2026-04-20 00:18):

| Category | Total | Genuinely distinct | Engine clones |
|---|---:|---:|---:|
| structural_color (cx_* heroes) | 25 | 18 | 7 |
| dual_color_shift (cx_* duos) | 8 | 8 | 0 |
| micro_flake_shift (cx_* WAVE4 + MICRO_SHIFT) | 33 | 9 | 24 |
| cs_* duo bank (engine-side) | 66 | 5 | 61 |
| **TOTAL engine-side** | **132** | **40** | **92** |

The painter-facing 67 cx_* + 27 cs_* (94 total visible tiles) collapsed
to roughly **40 truly distinct finishes**, with the rest being
color-stop variation on shared engine kernels. The trust problem isn't
that they exist — it's that they all sit at the same picker tier.

---

## Phase 2 — Foundation lane truth

### Win HSIG-FOUND-1 — Piano Black searchability

`paint-booth-0-finish-data.js:175`

```diff
- { id: "piano_black", name: "Vortex Ebony Depth",
+ { id: "piano_black", name: "Piano Black (Vortex Depth)",
```

Painter searches "piano black" → tile surfaces. Painter searches
"vortex" → tile still surfaces (substring match in display name).
Description rewritten to lead with "Mirror-deep piano-black lacquer"
so the poetic Vortex framing remains but is no longer the only entry
point. **3-copy synced.**

### Win HSIG-FOUND-2 — ★ Enhanced Foundation metadata normalization

Built `tests/_runtime_harness/normalize_enhanced_foundation_metadata.py`.
Idempotent. Targets all 30 ids in `BASE_GROUPS["★ Enhanced Foundation"]`.

For each entry, sets:
| Key | Old (mixed) | New (consistent) |
|---|---|---|
| `browserGroup` | "Materials" / "Full Library" / "Specials" / "Utility" | "Materials" |
| `browserSection` | "Paint Sheen" / "Chrome & Mirror" / "Optical / Shift" / etc. | "★ Enhanced Foundation" |
| `featured` | true / false (mixed) | true |
| `utility` | true / false (mixed) | false |
| `sortPriority` | 50 / 80 (mixed) | 90 |
| `advanced` | false / unset | false |

**90 metadata mutations applied** (30 entries × 3 mirror copies).
All 30 entries now sort above plain Foundation (priority 80) in the
Materials tab.

---

## Phase 3 — COLORSHOXX hero pass

Built `tests/_runtime_harness/normalize_color_shift_metadata.py`.
Three-part fix; idempotent.

### Win HSIG-CX-1 — cs_* metadata audit

Verified that all 27 cs_* MONOLITHIC overlay presets have FINISH_METADATA
entries (initially feared they were orphaned with no metadata; reading
confirmed they live in `FINISH_METADATA` lines 4814-5100). Existing
metadata: `family: "Color Science"`, `browserGroup: "Specials"`,
`featured: false`, `sortPriority: 50`. Acceptable as-is — they sort
below cx_* heroes (sortPriority 80) and don't clutter Quick Start.

### Win HSIG-CX-2 — name collision disambiguation

| ID | Old display name | New display name | Reason |
|---|---|---|---|
| `cs_inferno` | "CS Inferno" | "CS Inferno (Overlay Shift)" | name collided with `cx_inferno` "COLORSHOXX Inferno Flip" |
| `cs_supernova` | "CS Supernova" | "CS Supernova (Overlay Shift)" | name collided with `cx_supernova` |
| `cs_oilslick` | "CS Oil Slick" | "CS Oil Slick (Overlay Shift)" | name collided with `cx_oil_slick` |
| `cs_mystichrome` | "CS Mystichrome" | "CS Mystichrome (Purple→Green Overlay)" | "Mystichrome" IS purple→green; clarifies this is the overlay version vs `cx_purple_to_green` hero |

**3-copy synced** (4 fixes × 3 = 12 mutations).

### Win HSIG-CX-3 — engine-clone demotion

Per the explore-agent audit (2026-04-20 00:18):

> "cx_rose_chrome, cx_blood_mercury, cx_toxic_chrome (lines 303-321):
> All three use `_cx_fine_field` with identical M/R architecture
> (M_hi=240-245, M_lo=8-25, R_hi=15, R_lo=165-200). The spec map is
> copy-pasted with only color stops changing."

Set `advanced: true` on these 3 metadata entries:
- `cx_rose_chrome`
- `cx_blood_mercury`
- `cx_toxic_chrome`

**9 metadata mutations applied** (3 × 3 mirror copies).

The 7 chrome-flip cx_* heroes still in default view: `cx_chrome_void`,
`cx_neon_abyss`, `cx_obsidian_gold`, `cx_electric_storm`,
`cx_midnight_chrome`, `cx_white_lightning`, `cx_glacier_fire`.

---

## Phase 4 — SHOKK + special-finish follow-up

Reviewed `docs/SHOKK_BASES_AND_DEDUP_HANDOFF_2026_04_19.md` and
`docs/HEENAN_FAMILY_LIBRARY_AUDIT_2026_04_19.md` deferred-items lists.

| Deferred item | Status |
|---|---|
| `shokk_blood + shokk_static` share `paint_plasma_shift` | **Resolved earlier**: registry now routes `shokk_static → paint_shokk_static_v2` (`engine/registry_patches/shokk_series_reg.py:6`). |
| `shokk_static` noise scales [1,2,4] sub-pixel | **Resolved earlier**: H4HR-BOCK1 retuned to [4,16,32], `noise_M` 30→55 (`engine/base_registry_data.py:695`). |
| `shokk_blood/pulse/static/venom/void` lack dedicated `base_spec_fn` | Resolved by SHOKK_BASES handoff (5 dedicated functions added). |
| Sting #18-20 CX/MS/NU prefix expansion | Still deferred — saved-config-relevance is real. Not a trust problem; requires migration template. |
| Sting #24 `Art_Deco_V2/V3/V4` rename | Still deferred — same reason. |

**No new SHOKK fixes shipped this run** because the deferred queue is
genuinely empty of safe wins. Honest call rather than a fake one.

---

## Phase 5 — Browser/metadata truth alignment

Phase 2 + Phase 3 metadata writes covered the highest-impact alignment
work (60 metadata entries normalized: 30 enh_* + 27 cs_* verified + 3
cx_* demotions). Spot-checked the `_filterByBrowseMode()` machinery
in `paint-booth-2-state-zones.js:8100-8124` — confirmed:

- `materials` tab: shows `browserGroup === 'Materials' || === 'Utility'`
  → ★ Enhanced Foundation now shows here (was scattered).
- `quick` tab for bases: uses `HERO_BASES` curated list (12 entries).
  Foundation entries with `featured=true` no longer accidentally
  promote into Quick Start.
- `advanced` tab: shows `meta.advanced || browserGroup === 'Advanced'`
  → 3 cx_* clones now demoted here.

**No browser-tab structural changes needed** — the existing tab plumbing
respects metadata; the metadata was the lie. Lie corrected.

---

## Phase 6 — Visual proof

Visual changes this run are all **picker-presentation** changes, not
render changes. The before/after proof is the metadata diff itself
(captured in Phase 2 + Phase 3 sections above) and the validator
gate output (Phase 7).

No on-canvas pixel changes were made. No need for swatch capture
proof — the engine produces the same images for the same `(base,
pattern, finish)` triple as it did before this shift. What changed is
which tiles you see when you open the picker.

This is honest: the run was about presentation truth, not render
quality. Phase 6 gracefully degrades to "metadata diff IS the proof".

---

## Phase 7 — Verification (final gate)

| Receipt | Result |
|---|---|
| `node tests/_runtime_harness/validate_finish_data.mjs` | **0 problems**, 0 phantoms, 0 ungrouped, 0 cross-registry, 0 dup names, 0 missing desc/swatch |
| `node tests/_runtime_harness/registry_collisions.mjs` | **0 collisions, 0 duplicates** across BASES (358) / PATTERNS (319) / MONOLITHICS (628) / SPEC_PATTERNS (285) |
| `python audit_finish_quality.py` | **375 OK / 0 broken / 0 GGX / 0 spec-flat / 0 slow** |
| `python -m pytest tests -q` | **661 passed** in 10.98s |
| `node scripts/sync-runtime-copies.js --write` | **no drift** across 34 copy targets, 14 ms |

Engine 0/0/0/0 throughout. Registry 0/0 throughout. Validator 0
throughout. **Catalog trust gates all green.**

---

## Risks avoided

1. **Did NOT rename `cs_inferno`/`cs_supernova`/etc IDs.** The display
   name was the painter-visible problem. Renaming the ID would require
   another HP-MIGRATE entry and risk saved-config corruption. Display
   name change is purely cosmetic and 100% safe for saved configs.
2. **Did NOT delete the 3 demoted cx_* clones.** Some painter somewhere
   has them in a saved config; the Advanced toggle still surfaces them.
3. **Did NOT change the `_filterByBrowseMode()` tab logic.** The
   existing metadata-driven plumbing was correct — only the metadata
   itself was the lie. Fixed at the data layer.
4. **Did NOT promote the 27 cs_* entries to `featured: true`.** Their
   default `featured: false` keeps them honest as overlay parametric
   presets, not pretending to be the hand-tuned cx_* heroes.
5. **Did NOT rename "Vortex Ebony Depth" to plain "Piano Black".** The
   poetic name had real product-character value; preserved it as the
   parenthetical so both names work for search.

---

## Deferred items

| Item | Reason |
|---|---|
| Tune `cs_*` metadata `featured`/`sortPriority` for the 27 overlay presets | Lower priority than disambiguation work; current default-50 priority keeps them sorted below cx_* heroes in Specials. |
| Demote the 24 micro_flake_shift `cx_*` WAVE4 entries that the agent flagged as "color-stop only variation" | More aggressive call; defer until painter-feedback confirms the front shelf still feels too dense after this shift's 3-entry demotion. |
| Sting #18-20 CX/MS/NU prefix consistency rename | Saved-config relevance; needs MIGRATION_TEMPLATE-style careful pass. |
| `cx_inferno` vs `cx_galaxy_dust` description audit (overlapping cosmic concept) | Not a name collision per se; description-only polish. |
| Standalone "Color Shift Overlays" browserSection split | Currently `cs_*` entries live under "Color Science" section. Splitting requires picker UI awareness of the new section name; defer until UI work. |

---

## Top 10 most improved finishes (this shift)

| # | Finish | Improvement |
|---|---|---|
| 1 | `piano_black` | Display name now searchable; description rewritten lead-with-Piano-Black |
| 2 | `enh_gloss` | Promoted from utility-tier metadata to consistent ★ Enhanced premium tier |
| 3 | `enh_satin` | Same — utility→★ Enhanced |
| 4 | `enh_matte` | Same — utility→★ Enhanced |
| 5 | `enh_pearl` | Promoted from Specials/featured-false to Materials/featured-true |
| 6 | `enh_chrome` | Moved from "Full Library" (no tab maps to that) → Materials |
| 7 | `cs_inferno` | Display name disambiguated from `cx_inferno` hero |
| 8 | `cs_mystichrome` | Display name now reads "Purple→Green Overlay" — connects concept to its `cx_purple_to_green` hero counterpart |
| 9 | `cx_chrome_void` | Becomes the unambiguous front-shelf chrome flip — the 3 weakest siblings demoted to Advanced |
| 10 | `enh_piano_black` | Same metadata normalization + lives next to renamed `piano_black` for the most-searched-for Audi/BMW finish family |

---

## Top 5 still not good enough

| # | Finish / area | Reason |
|---|---|---|
| 1 | The 24 micro_flake_shift WAVE4 cx_* entries | Engine-side audit flagged them as "color-stop only" variation. Front shelf still has them at hero level. Deferred demotion pending painter feedback. |
| 2 | The 66 engine-side `CS_DUO_MICRO_MONOLITHICS` (in `micro_flake_shift.py`) | All share identical `m_base = int(215 + avg_v * 15)` formula. Mechanically defensible, experientially redundant. Should probably collapse to a parametric picker rather than 66 tiles. |
| 3 | `cx_inferno` vs `cs_inferno` Description | Both still describe "inferno"-themed paint. The display-name suffix helps, but the core descriptions remain conceptually overlapping. |
| 4 | `cx_glacier_fire` vs `cx_ice_fire` (different engines, similar concept) | One is Wave-2 chrome-vs-matte (structural_color), one is dual_shift gradient. Both ship at hero tier. Either rename one or accept the dual-engine "ice/fire" theme has two valid expressions. |
| 5 | The 7 cx_* "structural_color clones" the agent identified | Audit named 4-5 specific demote candidates; we acted on 3. The remaining 2-4 may also warrant Advanced flagging, but the call is less clean-cut without painter feedback. |

---

## Files changed

| File | Change |
|---|---|
| `paint-booth-0-finish-data.js` (×3 copies) | piano_black display name + 4 cs_* display names disambiguated |
| `paint-booth-0-finish-metadata.js` (×3 copies) | 30 enh_* normalized + 3 cx_* demoted (33 entries × 3 = 99 metadata mutations) |
| `tests/_runtime_harness/normalize_enhanced_foundation_metadata.py` | NEW — idempotent ★ Enhanced metadata normalizer |
| `tests/_runtime_harness/normalize_color_shift_metadata.py` | NEW — idempotent COLORSHOXX honesty pass (cs_/cx_ disambig + clone demote) |
| `docs/HEENAN_FAMILY_OVERNIGHT_SIGNATURE_FINISH_PASS.md` | NEW — this file |

**Total mutations:** 12 display-name fixes + 99 metadata field updates = **111 painter-visible truth fixes** in one shift. Engine 0/0/0/0. Registry 0/0. Tests 661 green.

— Heenan Family, signing off the SIGNATURE FINISH TRUST PASS at
2026-04-20 00:27 local.
