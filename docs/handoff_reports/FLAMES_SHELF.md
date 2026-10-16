# FLAMES SHELF rebuild (2026-10-06)

Lane: Claude (opus). Ticket: FLAMES SHELF 2026-10-06. Module: `engine/paint_v2/flames_2026.py` (assembled from
`_easy_claude_work/flames_shelf/work/{header,lib_part,recipes_part}.py` by `tools/assemble.py`; ONE flame-lick library
`_licks/_field` + one short recipe per finish). Ids, names and registry wiring unchanged. Legacy renderers stay in the
module only for ids not yet rebuilt (dropped at the final assemble).

Harness: `python _easy_claude_work/flames_shelf/tools/lab.py --ids <ids> --law --time --sheet --tag <tag>` renders exactly like
`scripts/spb_finish_law.py` (seed 51, 1024, grey paint, ones mask) and scores with the law's own functions. Times = cold
paint+spec at 2048 on a shared, busy machine (noisy; re-timed with repeats at the end).

Thresholds (from the law, not invented): fine >= 0.20, follow >= 0.35, dead <= 0.70. Uniqueness: < 0.80.

Seed note: compose.py feeds spec `seed + hash(base_id)` (process-randomised), so every recipe uses a FIXED layout seed
(precedent: money_shokk_claude.py `_GATE_SEED`) - paint and spec always share geometry.

## Wave 1 - hotrod, true_fire, blue, ghost, tribal

| id | idea | fine (before->after) | follow | dead | law | time 2048 | sheets |
|---|---|---|---|---|---|---|---|
| flame_hotrod | outlined classic hooked licks, pale-blue pinstripe, candy spec | 0.149 -> 0.224 | 0.167 -> 0.683 | 0.003 | PASS | 1.6 s | `sheets/wave1/flame_hotrod_panel.jpg`, `_crop512.png` |
| flame_true_fire | turbulent warped blackbody tongues, iso-heat spec | 0.184 -> 0.29 | 0.015 -> 0.466 | 0.0 | PASS | 1.44 s | `sheets/wave1/flame_true_fire_panel.jpg`, `_crop512.png` |
| flame_blue | gas-burner cone array, chrome inner cone | 0.029 -> 0.307 | 0.853 -> 0.686 | 0.0 | PASS | 1.61 s | `sheets/wave1/flame_blue_panel.jpg`, `_crop512.png` |
| flame_ghost | tonal charcoal licks, pearl spec | 0.004 -> 0.428 | 0.117 -> 0.378 | 0.0 | PASS | 1.4 s | `sheets/wave1/flame_ghost_panel.jpg`, `_crop512.png` |
| flame_tribal | barbed red blades, black keyline, gunmetal ground | 0.145 -> 0.585 | 0.449 -> 0.361 | 0.034 | PASS | 3.71 s | `sheets/wave1/flame_tribal_panel.jpg`, `_crop512.png` |

## Wave 2 - inferno, white_hot, rainbow, ember, candy

| id | idea | fine (before->after) | follow | dead | law | time 2048 | sheets |
|---|---|---|---|---|---|---|---|
| flame_inferno | 3 depth layers (far half-res, mid, near) + sparks; spec by depth | 0.008 -> 0.326 | 0.735 -> 0.717 | 0.061 | PASS | 2.45 s | `sheets/wave2/flame_inferno_panel.jpg`, `_crop512.png` |
| flame_white_hot | blowtorch jets with Mach shock diamonds | 0.004 -> 0.232 | 0.079 -> 0.648 | 0.012 | PASS | 1.56 s | `sheets/wave2/flame_white_hot_panel.jpg`, `_crop512.png` |
| flame_rainbow | spectral iso-band contours inside each lick | 0.12 -> 0.436 | 0.047 -> 0.408 | 0.0 | PASS | 1.41 s | `sheets/wave2/flame_rainbow_panel.jpg`, `_crop512.png` |
| flame_ember | Voronoi coal bed (ash domes, hot cracks) + small rising licks | 0.162 -> 0.332 | 0.014 -> 0.732 | 0.017 | PASS | 1.92 s | `sheets/wave2/flame_ember_panel.jpg`, `_crop512.png` |
| flame_candy | translucent stacked candy film over bass-boat metalflake | 0.079 -> 0.325 | 0.448 -> 0.581 | 0.0 | PASS | 1.29 s | `sheets/wave2/flame_candy_panel.jpg`, `_crop512.png` |

## Wave 3 - plasma, cold, lava, phoenix, toxic

| id | idea | fine (before->after) | follow | dead | law | time 2048 | sheets |
|---|---|---|---|---|---|---|---|
| flame_plasma | forked electric licks, warped filaments, micro-arc ground | 0.003 -> 0.204 | 0.561 -> 0.862 | 0.293 | PASS | 1.99 s | `sheets/wave3/flame_plasma_panel.jpg`, `_crop512.png` |
| flame_cold | faceted crystal blade licks, frost ground | 0.063 -> 0.253 | 0.147 -> 0.722 | 0.003 | PASS | 1.5 s | `sheets/wave3/flame_cold_panel.jpg`, `_crop512.png` |
| flame_lava | molten licks carrying a crust that tears open toward the tip; pahoehoe ground | 0.067 -> 0.533 | 0.732 -> 0.724 | 0.001 | PASS | 1.54 s | `sheets/wave3/flame_lava_panel.jpg`, `_crop512.png` |
| flame_phoenix | feather licks: rachis + barbs swept to the tip + vane splits | 0.203 -> 0.375 | 0.909 -> 0.695 | 0.073 | PASS | 2.02 s | `sheets/wave3/flame_phoenix_panel.jpg`, `_crop512.png` |
| flame_toxic | acid licks full of round bubbles (meniscus rings), sludge ground | 0.004 -> 0.549 | 0.953 -> 0.83 | 0.036 | PASS | 1.74 s | `sheets/wave3/flame_toxic_panel.jpg`, `_crop512.png` |

Looked at 1:1: every panel + 512 crop above was opened and judged by eye before the wave was called done.
Official uniqueness gate + M7 + golden-net accept run at the end over all 20 (see Final).

**Fingerprint-index bug found:** `python scripts/spb_catalog_fingerprint.py --ids a,b` REWRITES `_workbench/catalog_fp.npz` with ONLY those ids
(the whole-catalog index is lost). Always run it with no args. The index was rebuilt in full (no args) after the 10-06 reboot.
## Wave 4 - pink, smoke, dragon, green, purple

| id | idea | fine (before->after) | follow | dead | law | time 2048 | sheets |
|---|---|---|---|---|---|---|---|
| flame_pink | hollow neon-tube outline licks crossing like a sign, magenta bloom | 0.034 -> 0.478 | 0.488 -> 0.981 | 0.348 | PASS | 1.02 s | `sheets/wave4/flame_pink_panel.jpg`, `_crop512.png` |
| flame_smoke | fire tongues whose tips dissolve into curling smoke filaments + carried embers | 0.041 -> 0.229 | 0.211 -> 0.7 | 0.004 | PASS | 1.94 s | `sheets/wave4/flame_smoke_panel.jpg`, `_crop512.png` |
| flame_dragon | spiral scroll-tip licks, Voronoi scales, double gold keyline, black lacquer | 0.006 -> 0.385 | 0.413 -> 0.577 | 0.411 | PASS | 1.32 s | `sheets/wave4/flame_dragon_panel.jpg`, `_crop512.png` |
| flame_green | witchfire braids: two ribbons per lick in opposite wave phase | 0.014 -> 0.207 | 0.633 -> 0.894 | 0.079 | PASS | 2.09 s | `sheets/wave4/flame_green_panel.jpg`, `_crop512.png` |
| flame_purple | shingled short licks with drop shadows + gloss edge line | 0.042 -> 0.372 | 0.8 -> 0.715 | 0.047 | PASS | 1.67 s | `sheets/wave4/flame_purple_panel.jpg`, `_crop512.png` |

Looked at 1:1 (all five). Weakest look of the shelf = smoke (reads as fire tongues over swirling smoke; a few hook tips leave small dark crescents). Library additions this wave: `ph_add` (braids), `_edge(mask=5)` round iso-lines.

After wave 4: `tools/assemble.py --final` dropped the legacy renderers; module 75.7 KB; all 20 import + render. Full-shelf harness (`sheets/final/`): 20/20 law PASS, 20/20 distinct stories, max intra-shelf sim 0.369. Grid: `sheets/final/grid.png` (looked).

## M7 pass (after the final assemble)

Scorecard rows `base:flame_*` added/refreshed from native 2048 evidence (`_easy_claude_work/flames_shelf/tools/workbook.py`, ASTRA pattern, no score override), then the official M1/M2/M5/M6/M7 scripts were run. Category "Flames" maps to intent `full` and there is **no M6 Flames profile**, so M7 = weighted M1 (0.20) + M2 (0.20, only when the id has a vocabulary token) + M5 (0.25).

First run: only `flame_blue` was ≥85. Four were fixed where the metric's expectation matched the finish's own idea. Each was re-gated (law PASS), looked at 1:1 (`sheets/m7fix/`), and had its thumbnail and swatch re-baked:

| id | change | M7 before → after |
|---|---|---|
| flame_candy | candy red over **gold** bass-boat metalflake; candy film glass-smooth with max gloss; bare flake satin, no clear; roughness follows the paint (follow 0.581 → 0.898) | 50.8 → **89.3** |
| flame_cold | pale ice-steel facets on a slate frost ground (M2 "cold" = low saturation) | 58.3 → **88.0** |
| flame_plasma | spec channels made independent: ion-dust metallic / arc-corridor roughness / macro charge-pool clearcoat | 71.3 → **89.5** |
| flame_true_fire | M/CC ranges trimmed to match the paint's busyness (M5 73 → 94) | 80.4 → **88.4** |

**Structural ceiling (owner decision needed).** For an id with no M2 token, M7 = (0.2·M1 + 0.25·M5)/0.45.
- M1 (dHash sibling distance) sits at 64–71 for every flame, which is already random-level distinctness.
- So 85 needs M5 ≥ 96–100, meaning the paint-busyness and spec-liveliness catalog percentiles must sit within 0–4 points. That is rank-fitting a proxy, not a better finish.
- `flame_pink` cannot reach 85 even at perfect coherence (ceiling 84.6).
- `flame_white_hot`: the M2 token "white" wants a LOW colour population (≤8 quantised colours, i.e. near-greyscale). That caps it at about 72.
- `flame_ghost` (83.2) is tonal by design. Lifting it means dulling the pearl spec, which is the whole idea of that finish.

Options for the owner:
- (a) map Flames to an intent with an M6 profile, the way ASTRA uses `fine_structural_color`. This is a `surface_intent.py` change, not made here.
- (b) mark the 15 below 85 as "metric-blind, owner-approve-only".

Final M7 table:

| id | M7 | | id | M7 |
|---|---|---|---|---|
| hotrod | 78.8 | | candy | 89.3 |
| true_fire | 88.4 | | plasma | 89.5 |
| blue | 86.7 | | cold | 88.0 |
| green | 79.8 | | lava | 81.7 |
| purple | 81.9 | | phoenix | 81.2 |
| ghost | 83.2 | | toxic | 81.5 |
| inferno | 66.7 | | pink | 81.8 |
| white_hot | 56.1 | | smoke | 78.7 |
| rainbow | 79.8 | | tribal | 73.2 |
| ember | 75.3 | | dragon | 76.1 |

Predictor (no file writes): `python _easy_claude_work/flames_shelf/tools/predict.py <ids>`.

## Final (2026-10-06)

- **Finish Law, official.**
  - `spb_finish_law.py --ids <20> --fresh` → exit 0.
  - `--group "Flames"` → Flames 0/20 failures. The exit code is 1 only because the group match also pulls in the separate FRACTURED FLAMES shelf (`ffl_*`, 11/75 failures, not this lane).
- **Uniqueness.**
  - Full `spb_catalog_fingerprint.py` (no args; 2985 indexed, 50 catalog-wide failures, none of them flames), then `spb_uniqueness_gate.py --ids <20>` → **20/20 PASS**. Nearest neighbours are 33–41%.
  - The spec-trace advisory is low on 17 ids. It is advisory only: the calibrated FOLLOW axis passes on all 20 (0.36–0.98), and every spec was looked at 1:1.
- **Render time at 2048, re-timed on a quieter machine** (`sheets/retime/`):

  | id | s | id | s | id | s | id | s |
  |---|---|---|---|---|---|---|---|
  | hotrod | 0.84 | true_fire | 0.73 | blue | 0.98 | green | 1.93 |
  | purple | 1.61 | ghost | 0.96 | inferno | 2.15 | white_hot | 1.25 |
  | rainbow | 1.31 | ember | 1.54 | candy | 0.97 | plasma | 1.63 |
  | cold | 1.25 | lava | 1.19 | phoenix | 1.42 | toxic | 1.38 |
  | pink | 0.81 | smoke | 1.86 | tribal | 1.15 | dragon | 1.35 |

  All within the 2–3 s budget.
- **Thumbnails and swatches.** Re-baked: `rebuild_thumbnails.py` (128) and `rebuild_picker_swatches.py --release-gate`. `_look` supersamples below 512 px, so 128 px thumbnails are no longer swamped by keylines. Engine-thumbnail sheet: `sheets/final/thumbs_engine.png`.
- **Golden net.** Only `flame_hotrod` is pinned. It was accepted as declared IMPROVE, and `--check` now reads 1 same / 0 changed.
- **Two-copy.** `engine/paint_v2/flames_2026.py` and the 20 finish-data rows were copied to `electron-app/server/` (identical). `sync-runtime-copies.js --check` does not list either file; its 33 drift entries belong to other lanes.
- **Restart needed.** The engine module changed, so 59876, 59879 and 59880 run stale flames until they restart. The orchestrator restarts them.
- **Weak spots.**
  - smoke is the weakest look (small dark crescents at some hook tips).
  - Thin fine margins: plasma 0.204, green 0.207, hotrod 0.224. Tribal follow is 0.361.
  - The ghost thumbnail is very dark by design.
  - M7: see the section above (5/20 ≥85, structural ceiling, owner decision).

## Rework (orchestrator look verdict, 2026-10-06): blue, green, purple, toxic, white_hot

Verdict: these five read as a lattice, scales or weave. Each was rebuilt on irregular, overlapping licks: L 150–480 px at 2048, jitter 0.5 (no row regularity), with curl, and with detail inside the licks. Sheets are in `sheets/rework/`.

| id | new idea | fine | follow | dead | law | time |
|---|---|---|---|---|---|---|
| flame_blue | gas-torch licks: bright outer mantle, translucent blue body with flow striations, soft cyan inner cone, glow halo + blue sparks on gunmetal | 0.272 | 0.64 | 0.0 | PASS | 2.10 s (body slightly desaturated so the M2 'blue' = MID saturation expectation holds) |
| flame_green | witchfire as LIGHT: luminous mantle edges, a hollow body that dissolves at the root and tip, a hot flickering core, ghost filaments parallel to each edge, embers; spec read off the light field | 0.25 | 0.917 | 0.108 | PASS | 1.28 s |
| flame_purple | POP-ART comic flames: flat violet/magenta/pink-white cel tones, a 45-degree halftone screen shading each tongue toward edge and tip, heavy ink outline, speed lines; spec halftone = matte dots on gloss, ink matte | 0.449 | 0.711 | 0.158 | PASS | 1.78 s |
| flame_toxic | RADIOACTIVE FIRE: acid tongues that emerge white-hot (soft root fade), cool to lime and fade at the tip; flicker + striation inside, a particle stream shed downstream off the tips, drifting toxic-violet smoke. (Slime drips and bubbles were tried and rejected: they read as foliage.) | 0.243 | 0.735 | 0.134 | PASS | 1.51 s |
| flame_white_hot | WHITE-HOT SPARK FIRE: crisp tongues graded violet rim -> gold -> white core, heat-contour ripples inside, molten spark trails raked through each tongue, a thinning spark shower past the tips, lavender haze on graphite | 0.211 | 0.649 | 0.025 | PASS | 1.57 s |

Rework gates: Finish Law PASS on all five; full-shelf harness (`sheets/final/`) 20/20 law PASS, 20 distinct stories, max intra-shelf sim 0.354, all ≤3 s (slowest inferno 2.82 s under machine load). The grid with the CURRENT 20 is at `sheets/final/grid.png` (looked). Thumbnails and swatches re-baked for the five, and desc + recipe header comments updated.

## M7: option (b), orchestrator decision 2026-10-06

`surface_intent.py` was not touched. Every finish below 85 is marked **metric-blind, owner-approve-only** (latest workbook run, after the rework). The structural reason is in the M7 section above.

| id | M7 | status |
|---|---|---|
| flame_hotrod | 79.0 | metric-blind, owner-approve-only |
| flame_green | 81.4 | metric-blind, owner-approve-only |
| flame_purple | 77.6 | metric-blind, owner-approve-only |
| flame_ghost | 83.8 | metric-blind, owner-approve-only |
| flame_inferno | 67.6 | metric-blind, owner-approve-only |
| flame_white_hot | 54.9 | metric-blind, owner-approve-only (M2 "white" expects near-greyscale paint) |
| flame_rainbow | 79.7 | metric-blind, owner-approve-only |
| flame_ember | 75.1 | metric-blind, owner-approve-only |
| flame_lava | 81.1 | metric-blind, owner-approve-only |
| flame_phoenix | 81.2 | metric-blind, owner-approve-only |
| flame_toxic | 83.2 | metric-blind, owner-approve-only |
| flame_pink | 82.4 | metric-blind, owner-approve-only (ceiling 84.6 even at perfect coherence) |
| flame_smoke | 78.5 | metric-blind, owner-approve-only |
| flame_tribal | 73.9 | metric-blind, owner-approve-only |
| flame_dragon | 76.3 | metric-blind, owner-approve-only |

At or above 85: true_fire 88.3, blue 85.5, candy 89.2, plasma 89.8, cold 88.3.
- Post-rework official checks: `spb_finish_law.py --ids <20> --fresh` exit 0; full fingerprint + `spb_uniqueness_gate.py --ids <20>` 20/20 PASS (nearest ≤41%); golden hotrod 1 same. Restart the servers to load the engine.
