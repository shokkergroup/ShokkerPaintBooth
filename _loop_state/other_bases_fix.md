# "Other Bases" Orphan Section Fix — 2026-05-27

## Bug
Picker showed a non-expandable "Other Bases" section at the bottom of the BASES group containing 11 orphan IDs that had been intentionally cut from BASE_GROUPS by the 2026-05-18 owner mandate but kept in `BASES` for cross-references (HERO_BASES, weathered/chrome chains).

## The 11 orphan IDs (BASES entries not in any BASE_GROUPS entry and not in SPECIAL_GROUPS)

Verified via headless eval of `paint-booth-0-finish-data.js`:

1. `asphalt_grind` — Asphalt Grind
2. `barn_find` — Barn Find
3. `checkered_chrome` — Checkered Chrome
4. `drag_strip_gloss` — Drag Strip Gloss
5. `endurance_ceramic` — Apollo Shield Char
6. `pace_car_pearl` — Pace Car Pearl
7. `race_day_gloss` — Hyper-Ceramic Shell
8. `rally_mud` — Rally Mud
9. `bullseye_chrome` — Liquid Gallium
10. `stock_car_enamel` — Stock Car Enamel
11. `victory_lane` — Victory Lane

All 11 match the prior agent's expectation: leftover Racing Heritage ids (plus a couple renamed ones — `endurance_ceramic`/`race_day_gloss`/`bullseye_chrome` are now named "Apollo Shield Char" / "Hyper-Ceramic Shell" / "Liquid Gallium").

## Option chosen

**Option (a) — removed the "Other Bases" rendering entirely.**

Reasoning:
- Matches the pattern picker's existing stance (comment at line ~4764: *"No ungrouped 'Other' pattern bucket in Alpha UX."*) — consistent UX across picker types.
- Matches the monolithic picker's stance (line ~4737: *"No ungrouped monolithic 'Other' bucket in Alpha UX."*).
- An "Other Bases" bucket is dev-error noise — if a base belongs in the picker, it must live in a `BASE_GROUPS` entry. The 11 here are intentionally cross-reference-only and were never meant to appear in the picker.
- The owner reported the section was non-expandable anyway (it had no toggle handler), so removing it loses zero functionality.

## Files touched

- `paint-booth-2-state-zones.js` (root)
- `electron-app/server/paint-booth-2-state-zones.js`
- `electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js`

MD5 (all three identical): `7f9145f5f834705d2d00f44e024e0594`

## Smoke verify

```
$ node --check paint-booth-2-state-zones.js
SYNTAX OK
```

## Cross-reference safety check

The 11 IDs remain valid in `BASES`. Spot-checked references that still resolve:

- `barn_find` cross-referenced in: weathered chain (line 545), HERO_BASES (line 614 / line 639), Vintage Americana (line 1080), `_BASE_METADATA` (line 493), even a duplicate display variant near line 1602.
- All 11 stay reachable via finish-id lookup in the engine and via HERO_BASES / family chains — only the picker rendering was suppressed.

## Other constraints preserved

- `_BASE_PICKER_HIDDEN_GROUPS` skip-set for PRISM FORGE / Iridescent Insects (added earlier same session) is intact and untouched.
- No edit to `paint-booth-v2.html`.
- No commit; edits staged for owner review.
