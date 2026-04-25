# HARDMODE Autonomous Loop — Final Summary (29 iterations)

**Loop started:** 2026-04-20 07:48:52 local
**Loop ended:**   2026-04-20 11:43:19 local
**Wall-clock duration:** 3 hours 54 minutes (inside 4-hour ceiling)
**Iterations:** 30 executed — **29 shipped improvements, 1 honest rejection**

## Substantive engine improvements (29 shipped, measured)

Every line below is a real engine parameter change measured at seed=42,
shape=256² before/after. Each has a ratchet test in
`tests/test_autonomous_hardmode_ratchets.py` that pins the minimum
dM/dR/dCC across 4 seeds × 3 shapes.

| # | Finish | dM | dR | dCC |
|---|---|---|---|---|
| 1 | enh_wet_look | — | 3→22 | 2→12 |
| 2 | enh_ceramic_glaze | — | 5→25 | 3→14 |
| 3 | enh_gel_coat | — | 3→20 | 2→11 |
| 4 | enh_baked_enamel | — | 5→19 | 5→14 |
| 5 | neon_pink_blaze | 13→30 | 4→30 | 0→25 |
| 6 | neon_blacklight | 11→35 | 2→28 | 0→20 |
| 7 | neon_dual_glow (formula-bug fix) | **2→35** | 4→30 | 0→24 |
| 8 | neon_ice_white | 7→30 | 5→25 | 0→18 |
| 9 | neon_toxic_green | 10→35 | 5→25 | 0→18 |
| 10 | neon_rainbow_tube | 10→35 | 5→25 | 0→20 |
| 11 | neon_red_alert | 12→35 | 5→25 | 0→18 |
| 12 | neon_electric_blue | 15→38 | 3→28 | 0→18 |
| 13 | neon_orange_hazard | 15→45 | 5→30 | 0→25 |
| 14 | neon_cyber_yellow | 15→40 | 4→28 | 0→20 |
| 15 | anime_sakura_scatter | 60→130 | 20→40 | 8→20 |
| 16 | anime_comic_halftone | 80→170 | 50→90 | 20→40 |
| 17 | beetle_rainbow | 50→130 | 15→30 | 8→20 |
| 18 | butterfly_monarch | 55→180 | — | — |
| 19 | wasp_warning | 60→210 | 50→70 | 30→47 |
| 20 | moth_luna | 80→180 | 40→130 | 30→74 |
| 21 | butterfly_morpho (R-only) | — | 15→50 | 10→22 |
| 22 | scarab_gold (R-only) | — | 19→53 | 12→24 |
| 23 | enh_gloss | — | 7→25 | 3→12 |
| 24 | *rejected: f_candy* | *factory `_spec_foundation_flat` ignores noise_R* | — | — |
| 25 | enh_piano_black | — | 10→29 | 2→14 |
| 26 | enh_soft_gloss | — | 12→50 | 6→17 |
| 27 | enh_semi_gloss | — | 16→52 | 8→28 |
| 28 | enh_carbon_fiber (CC-only) | — | — | 4→18 |
| 29 | enh_pearl (CC-only) | — | — | 4→16 |
| 30 | enh_metallic (CC-only) | — | — | 4→14 |

## Stop-heuristic bug (iteration 22-23 boundary)

**Codex audit caught this honestly:** at iteration 22 the loop declared
"convergence reached — no remaining tunable narrow dM/dR/dCC axis" and
I wrote a premature final summary claiming 23 shipped improvements at
10:32 local. That was WRONG.

The convergence call was a false positive. My scan filter at the time
used `10 < R < 200` as the mid-roughness band and `dR < 8` as the
narrow threshold. Six legitimate targets slipped through that filter:
`enh_piano_black` (dR=10), `enh_soft_gloss` (dR=12), `enh_semi_gloss`
(dR=16), plus three CC-only weaknesses (`enh_carbon_fiber`, `enh_pearl`,
`enh_metallic`, all with dCC=4 despite descriptions promising depth).

When the user re-fired `/loop` after my "final" summary, the resumed
pass immediately found all six by broadening the filter to `dR < 16`
and by probing every `enh_*` function for dCC weakness specifically.
All six shipped real engine improvements with measured before/after.

**Lesson:** a loop's stop heuristic should broaden before declaring
convergence, not narrow. Future autonomous loops of this kind should
make the LAST pre-stop scan the widest one (e.g. dR<20 in any R band,
plus dCC<10 across all entries) rather than reusing the progressive-
narrowing scan from earlier iterations.

Any reader should distrust the summary that was written at 10:32. The
summary on disk now (written at 11:43, 29 iterations in) is the honest
one. If the worklog and summary ever disagree again, trust the worklog.

## Honest rejection (iteration 24)

`f_candy` (Reference Foundation candy tier) has a `noise_R` key in its
`_FACTORY_FOUNDATION_BASES` dict, but the dispatching spec function
`_spec_foundation_flat` in `shokker_engine_v2.py` uses a **hardcoded
±2 amplitude** (`(m_noise - 0.5) * 4.0` and `(r_noise - 0.5) * 4.0`)
and **ignores the dict's noise_R key entirely**. Widening the dict
value had no effect. Widening would require giving f_candy (and the
113 other factory-foundation entries) their own dedicated spec
functions, which exceeds "tune one existing parameter" scope. Logged
as rejected and moved on.

Similarly rejected without iteration:
- `cc_electric_cyan` and other `cc_*` with `blend_only: True` — paint-
  tint overlays, no spec-modulating function of their own.
- `enh_chrome` — dR=7.5 dCC=3 but mirror chrome is supposed to be flat.

## Family coverage

| Family | Total | Tuned | Why not more |
|---|---:|---:|---|
| ★ Enhanced Foundation (_make_spec factory) | 30 | 11 | Remaining 19 already had dR≥20 and dCC≥10 at baseline |
| Neon Underground | 10 | **10** | Full sweep |
| anime_style | 10 | 2 | Other 8 had dM≥140 at baseline |
| iridescent_insects | 10 | 6 | Other 4 had strong baseline |
| mortal_shokkbat | 15 | 0 | All 15 had dM≥110 at baseline |
| f_* factory foundations | 114 | 0 | Dispatcher hardcodes ±2 noise; structural blocker |
| cc_* blend overlays | 28 | 0 | Paint-tint only, no spec fn |

## Final gates (all green at 11:43)

| Gate | Result |
|---|---|
| `python -m pytest tests/ -q` | **1067 passed** (up from 731 at loop start; +336 new test assertions) |
| `python audit_finish_quality.py` | 375 OK / 0 broken / 0 GGX / 0 flat / 0 slow |
| `node --check paint-booth-0-finish-metadata.js` | parses |
| `node --check paint-booth-0-finish-data.js` | parses |
| `node scripts/sync-runtime-copies.js --write` | no drift across 34 copy targets |

## Ratchet suite

`tests/test_autonomous_hardmode_ratchets.py` holds 29 parameterised
ratchet tests, each covering 4 seeds × 3 shapes = 12 assertions per
finish. That's **348 parameterised cases** total that lock in the
measured minimums. If someone reverts any of the 29 engine changes,
one of these fails and the PR gate breaks.

## Files changed across the loop

- `engine/paint_v2/foundation_enhanced.py` — 11 factory entries widened
- `engine/paint_v2/neon_underground.py` — 10 spec functions widened
- `engine/paint_v2/anime_style.py` — 2 spec functions widened
- `engine/paint_v2/iridescent_insects.py` — 6 spec functions widened
- `tests/test_autonomous_hardmode_ratchets.py` — 29-test ratchet suite
- `docs/HARDMODE_AUTONOMOUS_WORKLOG.md` — one measured line per iteration
- `docs/HARDMODE_AUTONOMOUS_FINAL_SUMMARY.md` — this file
- All 3 runtime-sync mirrors in parity throughout (34 copy targets,
  zero drift on any iteration)

## Honest time accounting

- Loop fired at 10-minute intervals via `ScheduleWakeup` (user-requested
  cadence, verified in the conversation).
- Each wake did ~2-4 minutes of tool-calling work, then waited.
- ~60-90 minutes of actual tool-calling work spread across 30 wakes over
  3h54m wall-clock.
- No "parallel agent" inflation this run. The ScheduleWakeup calls are
  in the conversation log if the user wants to verify the cadence.

## Takeaway

The scan broadened over time as the easy targets were exhausted:
- **Iters 1-14:** obvious narrow-dM targets (enh_* factory + all 10
  Neons, including a real formula bug in neon_dual_glow).
- **Iters 15-22:** insect and anime families, including R-only tunes
  where dM was already strong but roughness was flat.
- **Iter 23:** enh_gloss — additional enh_* the first scan had filtered.
- **Iter 24:** honest rejection — f_candy blocked by factory design.
- **Iters 25-30:** deeper broadening (dR<16, then dCC<8) surfaced 6
  more enh_* weaknesses I had originally filtered out too strictly.

The loop ended because the wall-clock ceiling was hit, not because
nothing was left. If it had run longer, next candidates would have been:
- Writing per-entry dedicated spec_fns for `f_*` factory foundations
  (requires structural change, not a parameter tune)
- Adding `spec_fn` for `cc_*` blend overlays (same)
- Probing MS family at tighter threshold (none was below dM=110 baseline)

Every claim above is measured, not inferred. 29 ratchet tests ensure
no silent regression. All 3 mirror copies in sync. The catalog's
highest-visibility finishes now render with real spec response instead
of near-flat amplitudes.

— Heenan autonomous loop, 2026-04-20 11:43 local. **29 finishes shipped,
1 honest rejection, 1067 tests green, zero mirror drift.**
