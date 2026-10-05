# Render-Time Findings — 2026-05-30

Owner mandate: "Go through all bases/monolithics/color functions — reduce render times
WITHOUT reducing quality. Before/after on times. Shave all times down."

## What got built (reusable, kept in repo)

- **`scripts/spb_color_fn_profiler.py`** — times every base / monolithic / fusion `spec_fn`+`paint_fn`
  in isolation, best-of-N, slowest-first. `--tag before|after`, `--compare A B`. Reports → `_perf/` (gitignored).
- **`scripts/spb_color_fn_verify.py`** — captures the full uint8 output of each function so any
  optimization can be PROVEN quality-neutral (`capture --tag pre|post`; `compare pre post --tol 1` →
  exit 0 iff every finish is byte-identical or ≤1 LSB). Pixel-identity safety net.

## Measured baseline (MONOLITHIC catalog, 256px, best-of-1)

**Total 47.35 s across 2486 timed function-calls (1243 unique finishes).** At the real 2048 render
size these scale ~16–60× per function (area + cache effects), so the hot tail is where the painter
actually waits.

### The hot tail (unique finish = spec+paint, slowest first)

| finish | total s @256 | note |
|---|---:|---|
| **depth_bubble** | **3.03** | **6.4% of the ENTIRE monolithic catalog in ONE finish** — 6.6× the next. |
| depth_crack | 0.46 | same `_mono_make_depth_finish` factory as depth_bubble |
| dualshift_pink_to_gold | 0.19 | `dualshift_*` family (~12 finishes) |
| cx_purple_to_green | 0.18 | `cx_*` colorshift family (~15 finishes) |
| cx_red_to_cyan | 0.18 | |
| dualshift_teal_to_magenta | 0.17 | |
| cx_blue_to_orange | 0.17 | |
| … then long tails of `cs_*`, `spectrum_*`, `microshift_*`, `rs_*`, `vm_*`, `uj_*` | 0.05–0.10 each | hundreds of finishes |

**Biggest single lever:** `depth_bubble` + `depth_crack` share the `_mono_make_depth_finish` factory —
fixing that ONE factory's hot loop fixes every depth_* finish at once (~3.5 s of the 47 s).

**Biggest aggregate lever:** the `cx_* / dualshift_* / cs_* / microshift_* / spectrum_*` colorshift
families are individually ~0.05–0.18 s but number in the hundreds — they dominate the long tail and
almost certainly share the same collapsible `Σ sin(sameArray + scalarPhase)` loop structure.

## APPLIED & PROVEN — depth_bubble CSE hoist (2026-05-30)

First quality-neutral win landed in `engine/expansions/fusions.py` (the depth-fusion factory
`_make_depth_fusion._compute_depth_pattern`, `bubble` branch — `depth_bubble` was the single
slowest finish in the app at ~6.2s spec + 6.2s paint @512px warm).

**Fix:** pure common-subexpression hoist — `dist / r_b` and the dome falloff
`np.clip(1 - (dist/r_b)**2, 0, 1)` were each computed **twice** per bubble chunk (once for `dome`,
once for `spec`). Hoisted to `_ratio` / `_dome_falloff` computed once. No math/constants/visual change.

**Proven (size 512, best-of-3, warm):**
| fn | PRE sha1 | POST sha1 | identical | PRE | POST | Δ |
|---|---|---|---|---:|---:|---|
| depth_bubble.spec | 06b97b… | 06b97b… | ✅ byte-identical | 6.21s | 4.69s | **−24.5%** |
| depth_bubble.paint | 9231105… | 9231105… | ✅ byte-identical | 6.18s | 4.79s | **−22.6%** |
| depth_crack (control, untouched) | e640554… | e640554… | ✅ | 3.95s | 3.95s | 0 |

SHA-1 identical = zero quality change. depth_crack hash+time unchanged confirms surgical scope.
3-copy synced; `tests_v2` 1196 passed / 22 skipped / 0 failed. `fusions.py` is NOT contended by Codex.

## Remaining optimizations (proven-safe transforms, NOT yet applied — see blocker)

Quality-neutral transforms identified for the hot functions:
1. **Angle-addition collapse** — a loop `Σ wᵢ·sin(θ + φᵢ)` with `θ` the same array and `φᵢ` a scalar
   collapses EXACTLY to `sin(θ)·A + cos(θ)·B` (scalars `A,B`). Turns N full-array `sin()` into 1 sin + 1 cos.
2. `x**2`/`np.power(x,2)`→`x*x`; `x**3`→`x*x*x`; `sqrt(x²+y²)`→`sqrt(x*x+y*y)`; drop unused `rng`.

Both are float-exact to ≤1 LSB (invisible at 8-bit) and verifiable per-finish with `spb_color_fn_verify.py`.

## BLOCKER — why no engine edits were applied this session

`shokker_engine_v2.py` (the file holding all these functions) could NOT be safely edited right now:
1. **Codex is concurrently editing it** — it has uncommitted changes (+12 lines and counting). Editing
   the same 19,500-line file from two agents risks clobbering each other's work on sync.
2. **The hot functions are closures inside factories** (`_mono_make_depth_finish.<locals>._depth_spec`),
   so they can't be patched by a simple unique-string replace without reading the factory exactly.
3. **The network drive's read tooling went unreliable** for this large file this session: `grep`/ripgrep
   returned stale "no matches" for strings that exist, `inspect.getsource` couldn't match the on-disk
   source, bash stdout garbled, and even direct Python reads returned impossible line numbers. I could
   not *verify* an edit landed correctly — and an unverified edit to the render engine is unacceptable.

Per the project's own safety rules (trust nothing you can't verify on this drive), I stopped rather
than risk corrupting the engine.

## Recommended next step (clean-room session)

Do the engine perf pass when **Codex is paused on `shokker_engine_v2.py`** and the drive read tools are
behaving (or working from a local non-network checkout). Then, in priority order:
1. `_mono_make_depth_finish` factory (fixes depth_bubble + depth_crack, ~3.5 s) — highest single win.
2. The `cx_* / dualshift_*` colorshift families (shared loop, hundreds of finishes — biggest aggregate).
3. The `cs_* / spectrum_* / microshift_*` tails.
Each step: `spb_color_fn_verify.py capture --tag pre` → edit → `capture --tag post` → `compare pre post`
(must be ≤1 LSB) → `spb_color_fn_profiler.py --compare before after` for the measured delta → 3-copy sync.

Baseline JSON is saved at `_perf/profile_before.json` for the eventual before/after comparison.
