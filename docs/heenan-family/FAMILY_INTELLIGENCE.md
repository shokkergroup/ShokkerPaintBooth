# Heenan Family Intelligence

**Last updated:** 2026-04-18 (FAMILY INTELLIGENCE — MARKET DOMINANCE PASS)

Cross-project Family doctrine now lives in:
`docs/heenan-family/MASTER_HEENAN_FAMILY.md`

This is the persistent brain of the Heenan Family. Future shifts
should read this BEFORE picking work, so the Family gets smarter over
time rather than re-learning the same lessons.

---

## What we have learned about SPB

### The moat
SPB is the only painting tool that treats spec maps as a first-class
concept at the zone level. Every other tool either makes the painter
author RGBA channels by hand (Photoshop / paint.net / Affinity / Krita
/ GIMP / Photopea) or hides spec behind a beta layer toggle (Trading
Paints Paint Builder).

The strategy is: **defend and amplify the spec/zone/finish trio.**
Everything else is secondary.

### The competitive landscape
- **Trading Paints Paint Builder**: free downloader/showroom, paid
  Pro tier ($23.99/yr) for the actual builder. Has Sim Preview
  round-trip into iRacing's 3D viewer (#1 retention feature TP has).
  Spec map control is BETA and per-layer only.
- **Photoshop**: the unbeatable raster gold standard. Smart Templates
  ecosystem (Heatwave / Coulby / SimWrapMarket) keeps painters in PS.
  Spec map workflow is manual channel painting.
- **paint.net**: free, sub-2-second launch, simple UI. Casual
  painters use it as a "just open and edit" tool.
- **Affinity / Krita / GIMP / Photopea**: the indie quartet. Each has
  a killer feature SPB could borrow without copying wholesale.

### What painters actually want (sourced from forums + tutorials)
1. Real-time PBR preview on the actual car geometry — SPB **already
   does this**. The opportunity is messaging.
2. One-click material presets — discoverability win, not capability.
   **Shipped 2026-04-18 as Material Quick-Pick.**
3. PSD round-trip that preserves Smart Template structure — moonshot.
4. Coordinated palette across car/helmet/suit — TP Pro has partial
   parity, no one has full parity.
5. Spec-map workflow that doesn't require painters to learn that
   B=16 means max gloss.

---

## What repeatedly breaks trust

### Silent drops (painter sets X, engine ignores X)
The single highest-trust-cost class of bug in the codebase. Examples
fixed in the last 2 shifts:
- Engine sliced `pattern_stack[:3]` while JS allowed 4 → silent 4th
  layer drop
- Builder #3 used `if (z.X != null)` guards that omitted defaults
  → preview/render and export sent different payloads for the same
  zone
- Builders #1/#2 dropped `fourth_base_pattern_invert/harden` while
  builder #3 emitted them → WYSIWYG broken across paths
- Builder #3 had stale regex missing `mc_` prefix → multi-color
  finishes silently lost colors in PS export
- `gradient_stops` / `gradient_direction` were forwarded by
  server.py but never read by the engine kwarg adapter → painters
  using gradient base color saw nothing happen

**Pattern:** the JS payload builders and the Python engine kwarg
adapters are the highest-risk drift surfaces. Any new field needs
to be added to ALL 3 JS builders AND ALL 3 engine entry points.

### Composite vs layer confusion
The Codex HIGH (history brush) is the poster child. When the user is
painting on a layer, the snapshot must be from THAT layer, not from
the composite. Any tool that snapshots state needs per-layer maps,
not single-canvas storage.

### Lying overlays
The pre-fix `computeZoneStats` used arbitrary `50` as fallback for
un-customized zones, ignoring the actual `INTENSITY_VALUES` profile.
The painter saw "50" in the overlay and thought their chrome zone
was at half-strength when it was actually at 100. Trust catastrophe.

---

## What repeatedly delivers wins

### Drift-hunt dedup with paired structural ratchets
Animal extracts the helper, Hawk writes the "exactly N call sites"
ratchet, Street writes the behavioral simulation. Three-agent pattern
that scales.

### Per-layer state thinking
Every layered-tool bug solved this shift was about replacing
single-canvas state with per-layer Maps. The pattern is universal.

### Behavioral tests via Python ports
Pure-Python ports of JS algorithms catch math bugs that source-text
guards miss. Cheap, fast, and outlive refactors.

### Surfacing unused but pre-curated data
The HERO_BASES quick-pick was a one-line UI win because the data
was already curated by an earlier dev. Always grep for "defined but
never imported" before designing new features.

---

## What painters likely care about most

Based on FAMILY INTELLIGENCE — MARKET DOMINANCE PASS research:

| Rank | Painter need | SPB status |
|------|--------------|------------|
| 1 | Spec authoring without learning channel semantics | Material Quick-Pick shipped; deeper work needed |
| 2 | PSD round-trip with Smart Template ecosystem | Partial: PSD ingest exists, round-trip parity not shipped |
| 3 | Real-time accurate preview of final iRacing render | SPB has its own renderer; TP Sim Preview is gold standard |
| 4 | Coordinated palette across car/helmet/suit | Not shipped (medium) |
| 5 | "I don't know which finish is the chrome one" | **Solved** by Material Quick-Pick |
| 6 | Albedo compensation for chrome | **Solved** by albedo hint toast |
| 7 | Tagged / favoritable preset library | Favorites + Recents partially shipped; tags missing |

---

## How future shifts should prioritize work

### Inviolable order
1. **Fix silent drops first.** Any "JS emits X, engine ignores X" bug
   blocks all other work. Painters cannot trust a tool that lies.
2. **Then drift-hunt dedup.** Six silent-drift bugs in one shift
   suggests there are more. Animal + Hawk + Street pattern works.
3. **Then painter-facing trust.** Lying overlays, hidden toolbar
   no-ops, missing locked-layer warnings.
4. **Then strategic features.** Market-driven quick wins (Material
   Quick-Pick, albedo hint) before moonshots (PSD import, Sim
   Preview parity).

### What to defer
- Photoshop tool clones (brush engine, magic wand variants)
- Catalog inflation (more finishes, more patterns)
- Vanity refactors that don't fix a real bug
- UI redesigns that change without measuring painter friction

---

## What market research suggests SPB must become

**Short version:** the tool a serious iRacing painter cannot leave
because nothing else understands spec maps as a first-class concept.

**Long version:**
1. Beat Photoshop on spec authoring (already winning, must not
   regress)
2. Match Trading Paints on iRacing template auto-detect + Sim
   Preview parity (currently behind)
3. Borrow Krita's right-click radial Pop-up Palette (productivity
   moat for power users)
4. Borrow Affinity's Live Filter Layers UX for the spec stack
   (matches painter mental model)
5. Turn existing PSD ingest into true PSD round-trip / Smart Template
   parity (biggest moonshot ROI)

---

## Family lineup (quick reference)

| Agent | Primary lane |
|-------|-------------|
| **Heenan** | CEO / orchestrator / heartbeats / handoffs |
| **Flair** | Hardest correctness, session semantics, parity |
| **Windham** | Repetitive consistency sweeps, UI truth cleanup |
| **Luger** | Cross-file fixes, glue, integration support |
| **Sting** | Visible UX polish, 2026 feel without breaking it |
| **Hawk** | Perf + preview discipline, canvas responsiveness |
| **Animal** | Engine fixes, render quality, hot paths |
| **Bockwinkel** | Photoshop/competitor research → SPB-specific lessons |
| **Pillman** | Hostile chaos QA, "find the shit before the user" |
| **Street** | One SPB-only wow improvement (gated until trust healthy) |
| **Raven** | Cleanup, naming, dead-path trimming, doc truthfulness |
| **Hennig** | "Mr. Perfect" — final perfection pass, file-by-file rigor |

Detailed per-agent role files live alongside this doc:
`docs/heenan-family/agent-<name>.md`.

---

## TWENTY WINS shift charter (2026-04-19)

The shift after the marathon expanded the lane assignments above. The
Family no longer maps cleanly to "research roles" because we already
have the research artifacts (`MARKET_RESEARCH_PAINTER_WORKFLOWS.md`,
`SPRINT_2026_04_18_MARATHON.md`, `FINISH_QUALITY_REPORT_v2.md`,
`MONOLITHIC_HEALTH_REPORT.md`, `PATTERN_HEALTH_REPORT.md`,
`TOOL_TRUST_MATRIX.md`). The new charter is execution-first: ship
twenty disciplined wins toward Photoshop-grade trust without catalog
inflation, vanity refactors, or random feature spree.

Hennig joins the Family this shift. Hennig is the gate every other
agent's work passes through before it counts as shipped.

Ground truth as of 2026-04-19 ~20:00 EST:
- Tests green (445 from prior marathon)
- Runtime sync clean
- 73 marathon bugs already fixed; deferred punchlist documented in
  `docs/SPRINT_2026_04_18_MARATHON.md`
- Tool trust improved but not complete
- Command surfaces cleaner but still partially redundant
- Finish browser honesty improving
- Finish catalog quality (78 PAINT_BROKEN) is biggest product-quality hole
- Monolithics healthy — do not waste the night there
- Patterns mostly registry/picker UX, not renderer bugs
