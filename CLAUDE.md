# Project: Shokker Paint Booth (Gold to Platinum)

## 🔴 FIRST, EVERY SESSION — the Living Wiki is THE single source of truth

Before touching anything, open **`SPB_WIKI.html`** (the Living Wiki). It is the single source of truth for what every agent is doing, the working conventions, the open trouble spots, and the post-mortems. Using it is **mandatory and constant** for every agent (Claude, Codex, Cursor, Gemini, Grok) — not a courtesy.

> **New to this codebase? Read these three wiki sections first (2026-09-04):**
> **🚀 Start Here** (10-minute onboarding — where things live, how to run it, the three traps) →
> **⚖️ The Laws** (every non-negotiable in one place, each with its runnable gate) →
> **🧠 Hard-Won Lessons** (32 traps that have cost real time, grouped by how they fool you).
> The wiki has full-text search — press `/`. `SPB_LIVING_WIKI.md` is a *secondary* deep-reference companion; where the two disagree, **`SPB_WIKI.html` wins**.

1. **READ** the **Agent Coordination Board** (who's on what + file lanes) and **Working Conventions (READ FIRST)** before editing.
2. **CLAIM** your work: update your row on the **Agent Coordination Board** — what you're working on, the files/lane you're touching, status, date — so no two agents collide on a file.
3. **LOG as you go**: append a dated entry to the **Daily Work Log** (newest at top) — what you did, what you touched, what's left. Update it **throughout** the session, not just at the end.
4. Hit a wall you can't solve → add it to **Known Trouble Spots**. Broke + fixed something notable → write a **Post-Mortem** (What happened / Root cause / How fixed / Lesson).

The wiki sections are plain markdown inside `<script type="text/markdown" data-section="...">` blocks — edit the markdown, save, reload. If you finish a work item and the wiki still says you're "idle" or shows stale work, **you did it wrong**: keeping the board + log current is part of the task, every time.

### ⚠️ KEEP IT LEAN — owner mandate 2026-07-19

The wiki was consolidated from **2.62 MB → 186 KB** because finished work never left it (336 log entries, 397 board rows of which 385 were DONE). It became unusable. **Do not regrow it.** Three binding rules:

> **It regrew anyway.** By **2026-09-04** it was back to **1.37 MB** — the Daily Work Log alone was 1.02 MB / 220 entries (75% of the page), much of it *per-run* entries on a single lane (the 2026-08-31 Houdini lane contributed ~26 by itself), and the board was back to 50 rows. It was consolidated a second time to **386 KB** *while adding four sections*. Everything is archived verbatim — see `SPB_WIKI_ARCHIVE.md`. **These three rules are not optional; they are the only thing keeping this document usable.**

1. **Board rows are ownership, not a diary.** One row per *active* lane. When your lane closes, compress it to a single sentence under *Recently Shipped* and delete the row.
2. **ONE log entry per agent, per lane, per day — not per run.** Twenty runs on one lane is ONE entry with the outcome and what's next (~6 bullets max). Per-run evidence, metrics and file lists belong in *your lane's own state/handoff doc*, not the wiki.
3. **When the Daily Work Log passes ~30 entries**, roll the oldest into the compact history table at the bottom of that section and append the full text to `docs/wiki_archive/daily_log_full_*.md`.

All prior history is preserved verbatim — index at **`SPB_WIKI_ARCHIVE.md`** (root), files in `docs/wiki_archive/`. Search it with `grep -rn "<term>" docs/wiki_archive/` before assuming something is lost.

---

**Then read `WORKSPACE_LOCATION.md` at the project root before doing anything else.**

It is the source of truth for *where this project lives* and the outstanding migration tasks from the 2026-05-14 move off the E: drive.

## Quick orientation

- Working dir: `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`
- Previous (stale) path: `E:\Koda\Shokker Paint Booth Gold to Platinum` — do not touch
- If your `cwd` reports anything starting with `E:\Koda\`, stop and tell the user — they need to relaunch you here.

## Two-copy rule (was three until 2026-06-09)

Several core files must stay in sync across TWO locations:
1. Project root (source of truth)
2. `electron-app/server/` (packaged into the installer)

**2026-06-09:** the old third copy `electron-app/server/pyserver/_internal/` (a vestigial PyInstaller bundle excluded from the installer via `!pyserver/**`) was deleted + removed from the sync manifest — it shipped to nobody and only caused 3-way drift. `node scripts/sync-runtime-copies.js --write` now syncs root → `electron-app/server/` only, and the build hard-fails on drift. Don't recreate the third copy. (See CHANGELOG 2026-06-09.)

Apply this to: `base_registry_data.py`, `paint-booth-0-finish-data.js`, `spec_patterns.py`, and the `viva_mexico/manifest.json` assets.

## ⚠️ UNIVERSAL RULES — owner mandate 2026-05-16 (SPB-105)

These rules apply to **every AI agent** touching finishes — Claude, Codex, Cursor, Grok, Gemini, anything. No exceptions.

### 00. THE FINISH LAW — the rule in stone (owner mandate 2026-08-31) — **READ `docs/FINISH_LAW.md` BEFORE AUTHORING ANY FINISH**

FRACTURED ELEMENTS shipped 60 finishes over **5 spec decks** (deck was a property of the *chapter*, not the finish; zero per-finish specs) and **its gate reported green** — because that gate compared finishes with a *phase-sensitive* cosine, which scores a pure re-seed as unique. Owner: *"Our #1 rule - above ALL ELSE - is NO LAZINESS, NO REPEATS."*

```bash
python scripts/spb_finish_law.py --group "<shelf name>"   # non-zero exit = FAIL
python scripts/spb_finish_law.py --calibrate              # re-check against owner verdicts
```

Five axes, thresholds **fitted to the owner's own verdicts** (20/24 agreement, all 5 gold standards pass): **SCALE** `max(paint_band, spec_band) >= 0.20` (either channel may carry the detail — Dichroic Skin's paint is broad and its spec is fine); **FOLLOW** `amp_corr >= 0.35`, band-limited to the car window (Truchet Glass 0.844 is the reference); **STORY** shelf `story_ratio >= 0.90` — the spec deck is a property of the FINISH, never of the chapter/lane/shelf; **TWIN** phase-invariant `< 0.80` (advisory: at 0.80 it fails all 5 gold standards); **COVERAGE** `dead <= 0.70` (fraction of paint near-black/near-white — added 2026-09-02 after three PARADIGM finishes passed every axis nearly solid black); **PROTECTED** — `scripts/protected_finishes.json` (Hologram Metal, Dichroic Skin, Truchet Glass, Cinder Pulse, Hologram Noir) is **NEVER CHANGED, at all costs**.

**Two absolutes:** never invent a threshold (fit it to owner verdicts and show the separation), and **never report a gate green without looking at a 1:1 contact sheet** — every failure in this project's history was visible instantly by eye.

### 0. The Uniqueness Law — no clones, ever (owner mandate 2026-06-15) — **HARD LINE**
Before any new or rebuilt finish is "done," it MUST clear the **uniqueness gate**. A finish that is **≥80% structurally similar to ANY other finish in the WHOLE catalog** (cross-category, and the check is **color-independent so recolors count**) FAILS and gets redone. PERIOD — not a smaller tweak, a *different idea*. And a finish's **spec must mirror the paint's structure** (same geometry, so they work together) unless the id is deliberately listed in `scripts/uniqueness_exemptions.json`.

```bash
python scripts/spb_catalog_fingerprint.py                       # refresh the whole-catalog index (cached, incremental)
python scripts/spb_uniqueness_gate.py --module <your_module>    # gate a module, or --ids a,b,c
python scripts/spb_uniqueness_gate.py --report                  # existing dup pairs = the rebuild worklist
```

Non-zero exit = something FAILED = not done. The full law + rationale is **`docs/UNIQUENESS_LAW.md`**; the same index powers the **Similarity** slider tab in `/SPB_WORKBENCH.html` (find dup clusters and empty lanes). Do not compound the duplication already in the catalog — anything NEW must pass this first.

### 0b. The Coverage + Fine-Detail + No-Laziness Law (owner mandate 2026-06-18) — **HARD LINE, GATED**
The render canvas is **2048×2048 over a WHOLE car**. Three binding defaults, enforced **mechanically** (a gate, not a memory):

1. **FULL-CANVAS COVERAGE by default.** Every finish/pattern/spec fills the canvas — no dead corners, no lonely centered motif, no big empty regions. Gate metric: `coverage_score` (signal present across an 8×8 grid) `>= MIN_COVERAGE`.
2. **CRUSHED FINE DETAIL by default.** High-octave, busy, premium detail — never a smooth flat ramp, a fat blob, or a single recolored primitive. Gate metric: `fineness_score` (high-frequency-energy ratio) `>= MIN_FINENESS`. (Aligns with the "Quality bar for ALL spec/paint generators" below — now with teeth.)
3. **NO LAZINESS — EVER.** No lazy finishes, no lazy patterns, no lazy specs. Highest standards, every time. A recolor of an existing field is NOT new work. Inventing genuinely new generative math IS the job.

**Exceptions are allowed but must be DELIBERATE and DOCUMENTED** — the owner's words: "there WILL be cases where it's not [covered/crushed]." A finish opts out only by being named, *with a written reason*, in an exempt list (e.g. `flame_math.COVERAGE_EXEMPT` / `FINE_DETAIL_EXEMPT`). Adding a name there is a reviewable act; silently dodging the bar is not.

**BE CREATIVE — go wild.** Invent new math concepts. Do not paint yourself into a box — you have the whole universe of generative math (flow/curl, cellular/Worley, reaction-diffusion, Lichtenberg branching, interference, metaballs, Voronoi seams, ferrofluid/Rosensweig lattices, spectral, …). The most exotic, beautiful math that draws the look out is the goal.

**Reference implementation of the gate:** `tests/regression_flame_uniqueness_test.py` runs four fail-closed checks — uniqueness `<0.80`, render `<3s @2048`, coverage `>= MIN_COVERAGE`, fineness `>= MIN_FINENESS` — over `flame_math.FLAME_STRUCTURES`. New structures auto-gate. This is the model for extending the catalog-wide gate (`scripts/spb_uniqueness_gate.py`) with the same coverage + fineness teeth.

### 1. The 85% rule
Any rebuilt or modified finish MUST score **≥85 on the M7 composite** before you stop iterating. If the score is below 85, redo it. Keep redoing it until it hits 85+. "I made the renderer better but didn't check the score" is not acceptable. The workflow is:

> **Note — 85 (owner ship-bar) vs 80 (code keeper tier):** The ≥85 here is the *owner's ship mandate* (SPB-105) — the bar you must hit before you stop iterating. It is NOT the same as the M7 "keeper" tier, which the code sets at **≥80** (`final >= 80` and `tierThresholds.keeper == 80` in `scripts/spb_workbook_compute_m7.py` as of 2026-05-30). A finish at 80–84 is a code-classified "keeper" but is still below the owner ship-bar — keep iterating to ≥85.

1. Edit renderer
2. Rebake thumbnail
3. Run `python scripts/spb_workbook_compute_m1.py && python scripts/spb_workbook_compute_m7.py`
4. Read the per-finish composite from `_workbook_metrics/m7_composite.json`
5. If composite < 85, iterate. Don't ship until ≥85.

Exception: spec_driven intent finishes have M1 dropped from the composite by design (SPB-95). For those, M7 doesn't fully reflect renderer quality. Score the spec channel stats directly (M_std, R_std, CC_std) — they should each be ≥20 with a range spanning most of [0, 255]. If both M7 ≥85 AND spec stats meet that bar, the finish is shippable. If M7 < 85 but spec stats are strong, flag it as "metric-blind, owner-approve-only" and surface it to the owner.

### 2. Render time budget
**Standard finish renders must complete in 2-3 seconds at 2048².** A finish that takes 20 seconds (e.g. tick-91 depth_bubble) is broken — fix it. Layer stacking and zone overlays are allowed exceptions, but bare paint+spec must stay in budget. Profile with `audit_render_perf.py --trials 3` after engine changes.

> **⚠ HOUDINI / X-LAB agents (Codex): `docs/HOUDINI_XLAB_LOOK_AND_PERF_MANDATE.md` is BINDING (owner, 2026-08-29).** Two modes: **OPTIMIZE** = same pixels, faster (SHA contract in `_finish_look_refs/2026-08-29/`; bit-exact or owner-approve-only) — fix the budget breaches (25/50 cards over 3s) and the Base-Scale color loss (wiki T66) this way. **IMPROVE** = you may change a look at your own free will through any number of iterations — declare the intent, pass the gates, re-bake that card's reference (`bake_refs.py <id>`). Forbidden: silent look drift during a perf pass.

### 3. Per-finish auditable trail
Every renderer edit must leave a comment in the source citing the SPB ticket, tick number, owner verdict snippet, and the metric movement (composite before → after). Otherwise the next agent has no idea why the code looks the way it does.

---

## ⚠️ Quality bar for ALL spec/paint generators

**Render canvas is 2048×2048 covering an ENTIRE CAR BODY.** Anything that looks small in a thumbnail will be huge on the car. Owner brief 2026-05-15:

- **Default frequency content must include high octaves.** A noise octave of 64 = ~32-pixel features on a 2048 canvas = the size of a side mirror. Use octaves at minimum (128, 256, 512, 1024+) for "fine detail." Hash any coarser octaves only as macro structure that fine detail rides on top of.
- **No blobby fields.** A finish that's mostly low-frequency variation reads as smeared paint on the car. Every spec/paint generator should layer at least 3 distinct frequency bands, with the highest band being legitimately fine (single-pixel or sub-pixel sparkle, micro-flake, micro-facet).
- **No "interesting math = good finish" assumptions.** Multi-octave Perlin alone is boring. Layer sharp edges, anisotropic grain, micro-flake distributions, ridge protection (Viva Mexico playbook), edge-light corridors, etc.
- **The reference is Viva Mexico / Union Jacked / Rising Sun.** See `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`. Those started from hand-authored PNGs and got procedural enhancement on top. Pure-procedural-from-zero is usually not enough for premium quality.
- **For spec-driven categories** (Foundation, Enhanced Foundation, Enhanced Foundation Exotic, Ghost Geometry, Clearcoat): the spec channel does ALL the visual work. Anything boring in the spec reads as a boring car. The bar is "would a real customer pay for this finish on their car?"

## Where to look for more

- `PRIORITIES.md` — current focus
- `RESEARCH.md` — market intel
- `CHANGELOG.md` — session summaries + tags
- `SPB_LINEAR_HANDOFF.md` — handoff doc that mirrors Linear
- `docs/ONBOARDING.md` — broader onboarding
- `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md` — gold-standard procedural spec technique reference
- `docs/METRICS.md` — full reference for the 8-metric finish quality suite + workbook
- `engine/paint_v2/surface_intent.py` — canonical category→intent mapping (spec_driven / pattern_design / pattern_image / full). All consumers (M6, future bake pipeline) read from here. Don't hand-code duplicates.

## TOKEN EFFICIENCY MANDATE (owner, 2026-06-10 — BINDING, ALL AGENTS, ALL THE TIME)

A 9-wide agent fleet once burned 33% of the owner's 5-hour limit (~10% of the weekly limit) in 15-20 minutes and produced NOTHING because the agents held all output in memory and wrote at the end. Owner: "That can NEVER HAPPEN."

1. **Incremental output, always.** Any agent producing multi-part work writes/updates its output file after EVERY completed unit and resumes by skipping units already on disk. Write-at-end-only is forbidden.
2. **Fleet size = burn rate.** Run agent lanes in waves (≤3 concurrent for authoring jobs). Wall-clock is cheaper than the owner's limits.
3. **One engine boot per verification round.** Every `import engine.*` costs ~30s + ~100 log lines. Batch ALL checks into one python run per round — never one run per item.
4. **Filter all command output** (e.g. `2>$null | Select-String "OK|FAIL|RESULT"`). Registry/build spam must never enter any agent's context.
5. **Read surgically** (grep anchors, offset/limit reads, never re-read or cat your own output back). **Write surgically** (Edit over rewrite; assemble big text on disk via scripts, not through context).
6. **Author to land on try 1-2:** worked examples + exact numeric gates up front; ≤2 revision cycles, then one targeted fix pass.
7. **Verify at reduced size while iterating** when the metric rescales; full-size confirmation once, on the final candidate.

### ARCHITECTURE ADDENDUM (2026-06-10, after root-cause analysis — supersedes process-only rules above where they conflict)
- **AI-as-compiler:** for any batch of N similar artifacts, build a generator library ONCE, then author each item as a ~10-20 line recipe — never N bespoke 100-line files through model context. (Engine + 92 recipes ≈ 150k tokens vs 2M+ bespoke.)
- **Generated content never re-enters context:** append-only JSONL drafts (rewriting a growing JSON is quadratic), scripts assemble big text on disk, no echo-backs.
- **Verification outside the loop:** one standing harness, one process, one verdict line per item; the model sees verdict lines, not logs or per-item runs.
- **Digests in:** a ≤60-line contract card replaces reading any big module.
- **Default 0-2 agents; declare a token estimate before any >50k-token job and design the kill-safe path first.**
