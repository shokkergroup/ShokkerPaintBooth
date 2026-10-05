# Finish-Picker Duplicate-Display Fix — PRISM FORGE & IRIDESCENT INSECTS

Date: 2026-05-27
Author: dev agent (interesting-austin-f9e56a worktree)

## Problem

`★ PRISM FORGE` and `Iridescent Insects` finish families each rendered TWICE
in the Base picker UI:

1. Once as their own top-level **base group** (from `BASE_GROUPS`)
2. Once nested under the **SHOKKER** super-group (from `SPECIAL_GROUPS` →
   `SPECIALS_SECTIONS["SHOKKER"]`)

Owner wants them visible ONLY under SHOKKER.

## Data-Flow Map (4 keys traced)

### `BASE_GROUPS["Iridescent Insects"]` (paint-booth-0-finish-data.js, ~line 2979)
Defines 10 beetle/butterfly/etc base ids.
Consumers:
- **paint-booth-2-state-zones.js:4633** — base picker render loop
  (`Object.keys(BASE_GROUPS).forEach`). This is what causes the dupe lane.
- **paint-booth-2-state-zones.js:6374** — builds `baseCat` inverse lookup
  (id → group label). Used purely for category labeling; multiple groups for
  same id are tolerated.
- **paint-booth-2-state-zones.js:10849** — `_spbGetBaseGroup()` lazy inverse
  lookup, used for the (currently dead-code) `_SPB_NO_AUTO_COLOR_GROUPS` set.
  Insects ids still resolve via `_SPECIALS_IRIDESCENT_INSECTS` → SPECIAL_GROUPS
  for the active `_spbIsShippingSpecialLikeFinishId` path.
- **paint-booth-2-state-zones.js:11145, 11716** — `GROUP_MAPS` for the unified
  picker; reads ALL of BASE_GROUPS / PATTERN_GROUPS / SPECIAL_GROUPS.
- **paint-booth-2-state-zones.js:16180, 16472** — category-tab merging in the
  Finish Browser; merges BASE_GROUPS + SPECIAL_GROUPS.
- **paint-booth-0-finish-metadata.js** — `family` / `browserSection` fields per
  base (purely metadata, not driven by BASE_GROUPS key — uses the literal
  string).

### `BASE_GROUPS["★ PRISM FORGE"]` (paint-booth-0-finish-data.js, ~line 2985)
Defines 50 pf_* base ids.
Consumers:
- Same paint-booth-2-state-zones.js paths as above.
- **paint-booth-6-ui-boot.js:1564** — Finish Browser "featured" lane reads
  `BASE_GROUPS['★ PRISM FORGE']` and picks the first 3 ids as PF features.
  **If we deleted the BASE_GROUPS entry, this featured lane would go empty
  for PF.** (Reason we chose option (b) instead of (a).)

### `_SPECIALS_IRIDESCENT_INSECTS["★ IRIDESCENT INSECTS"]` (line 1239)
Same 10 ids. Merged into `SPECIAL_GROUPS` (line 1281).
Consumed by `SPECIALS_SECTIONS["SHOKKER"]` (line 1269) → rendered in the
SHOKKER super-group lane via `renderGroupSection` (paint-booth-2-state-zones.js
line 4672) iterated by `SPECIALS_SECTION_ORDER` (line 1266).

### `_SPECIALS_SHOKKER["★ PRISM FORGE"]` (line 1102)
Same 50 pf_* ids as `BASE_GROUPS["★ PRISM FORGE"]`, defined directly inside
`_SPECIALS_SHOKKER`. Comment on line 1101 confirms: *"SPB-102 — same 50 pf_*
ids as BASE_GROUPS["★ PRISM FORGE"]; surfaced here for SHOKKER swatch picker
lane"*. Merged into `SPECIAL_GROUPS` → SHOKKER lane.

## Fix Picked: **Option (b)** — Skip-Set in Picker Render Code

Why not option (a) (delete BASE_GROUPS entries):
- `paint-booth-6-ui-boot.js:1564` reads `BASE_GROUPS['★ PRISM FORGE']`
  directly for the Finish Browser "featured" lane. Deletion would empty PF
  from that lane.
- Python engine `shokker_engine_v2.py:13704` and `13921` reference the
  "Iridescent Insects" group label for chroma-tuning metadata. (Independent
  dict — unaffected by JS edits — but signals that the group label is part
  of the wider taxonomy.)
- Several downstream JS consumers iterate ALL BASE_GROUPS entries. None
  break if entries remain — they merely show the dupes the user is
  complaining about, which we silence at the picker layer.

Option (b) keeps data intact and silences ONE consumer (the base picker).
Maximum-safety, minimum-blast-radius.

## Files Touched

- `paint-booth-2-state-zones.js` (root)
- `electron-app/server/paint-booth-2-state-zones.js`
- `electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js`

md5 (all 3 in sync): `f2fcada89a84bb26d3c7b8bb1b8b2b7e`

### Change

At the top of the base-picker render loop (paint-booth-2-state-zones.js
~line 4632), added a hidden-groups set:

```js
const _BASE_PICKER_HIDDEN_GROUPS = new Set(['Iridescent Insects', '★ PRISM FORGE']);
```

Loop now short-circuits on those two keys, while still registering their ids
into `baseGroupedIds` so the "Other Bases" safety-net at line 4654 does NOT
treat them as ungrouped and re-list them.

## Smoke Trace

**Base picker (user clicks a `base` / `secondBase` / `thirdBase` / etc.
swatch picker):**
- Top of HTML: "(not set)" tile + Foundation group (default expanded).
- Then alphabetized BASE_GROUPS lanes — EXCLUDING `Iridescent Insects` and
  `★ PRISM FORGE`. So "Iridescent Insects" lane no longer appears between
  "Industrial & Tactical" and "Metallic Standard"; "★ PRISM FORGE" lane no
  longer appears at the bottom of the alphabetical list.
- Then "Other Bases" safety net — empty for these ids because they were
  registered into `baseGroupedIds`.
- Then SPECIALS sections (rendered by `renderGroupSection` driven by
  `SPECIALS_SECTION_ORDER`):
  - **SHOKKER** section (10 subgroups including `★ PRISM FORGE` with its 50
    pf_* ids and `★ IRIDESCENT INSECTS` with its 10 insect ids) — visible
    AS EXPECTED, unchanged.

**Result:** PRISM FORGE and Iridescent Insects appear EXACTLY ONCE in the
picker, under SHOKKER.

**Finish Browser "featured" lane** (paint-booth-6-ui-boot.js line 1564):
unchanged behavior — still reads `BASE_GROUPS['★ PRISM FORGE']` and picks
3 PF ids. Featured row still shows PF.

**Python engine chroma logic:** unchanged — independent dict.

**`validateFinishData` mental run:** BASE_GROUPS entries kept intact, all
their ids still exist in BASES, so no orphan/phantom warnings.

## Coordination Note

The other in-flight agent was reported to be editing `paint-booth-v2.html`
and possibly other `paint-booth-*.js` files for a separate
dropdown/CSS fix. This edit only touches `paint-booth-2-state-zones.js`
inside the base-picker render block (~line 4632). No HTML touched.
Merge conflict surface is one localized block. Low risk.

## Verification Commands

```bash
md5sum paint-booth-2-state-zones.js \
       electron-app/server/paint-booth-2-state-zones.js \
       electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js
# All three should match: f2fcada89a84bb26d3c7b8bb1b8b2b7e
```

## Not Committed

Per task instruction — owner reviews before commit.
