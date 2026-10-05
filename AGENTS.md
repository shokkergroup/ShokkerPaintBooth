## Owner override — 2026-09-18
Owner PASS is final authorization for live installation and thumbnail baking. M7 is diagnostic and must not block owner-approved finishes. Preserve identity, source integrity, material semantics and actual-output checks. Complete ERA120 then FLAW LAB; preserve its four named favorites.

# Agent Instructions — Shokker Paint Booth

## Persistent category picker contract — owner 2026-10-02

- Category URLs MUST use `source=faithful-v1&baked=1`; browsing may never invoke a renderer. Eagerly load the open category; keep closed categories out of its image queue. No timestamp cache tokens.
- The active loader currently lives in `paint-booth-2-state-zones.js`; loaded extraction modules are not proof that they are installed. Run `node tests/picker_baked_loading_contract.cjs` against the active code.
- Startup, offline repairs and packaging use `scripts/bake_faithful_picker.py` (V5 bootstrap order). Legacy48px `rebuild_picker_swatches.py` output does NOT cover the current picker.
- After catalog changes: `python scripts/bake_faithful_picker.py --export-registry`, then `node scripts/spb_picker_catalog.cjs`, then `python scripts/bake_faithful_picker.py --workers 8`, then `--check`. The exporter runs the actual async registry merge and retirement filters; raw finish arrays are NOT the category inventory. Keep actual catalog tints, per-finish identities, full-detail masters and256px derivatives; synchronize both runtime trees. Never clear content-addressed bakes globally.
- Packaging must fail on stale catalog export or missing/corrupt current bakes. Tests: `tests/test_picker_baked_only.py`, `tests/test_faithful_swatch_persistence.py` and the active-loader contract above.

## ⚠️ OWNER'S FINISH DOCTRINE — READ BEFORE EVERY EDIT (2026-05-21) ⚠️

Owner's exact words: *"We HATE lazy finishes in here but we also need FINE DETAILS on just about everything. And WAY more spec coloring/shades of colors in the spec maps. Your patterns are WAY TOO BIG as a rule. Almost all of them. THINK universally — they ALL need to be small, fine patterns so they show up more pretty on these car canvases."*

**Non-negotiable. Trumps M7, SPM7, any metric.**

1. **FINE FEATURES — 8-32 px at 2048².** Every primitive. Not 40, not 64, not 120. No "macro feature" recipes. A 64px polish mark is wrong — make it a cluster of 8-12px points instead.
2. **MANY DISTINCT SPEC SHADES.** Wide intensity palette per feature (e.g. 8-tier `[0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]`), not just dark base + bright peak. Per-feature random brightness + per-feature random tint. Owner repeats this every audit.
3. **DENSITY > SIZE.** "Doesn't show up on car" = more features, finer, more contrast variety. NOT bigger features. If sparse → 3-10x more.
4. **NO LAZY FINISHES.** Single repeated feature type = lazy. Stack 5+ distinct mark types (sweeps + spots + arcs + rings + flecks) with varied chroma.

The M7 `B_structure` axis literally rewards macro-features (16×16 block std-dev) — that metric is wrong on this dimension. When owner eye and M7 disagree, **eye wins, always**.

## ⚠️ FINISH IDENTITY LAW — UNIQUE CONSTRUCTION, UNIQUE SPEC, NAME-TRUE (2026-09-01) ⚠️

Owner's exact correction: *"We need unique DESIGNS/LOOKS across the board. And they ALWAYS need to represent the name and idea behind the finish as well."*

This is a separate ship gate from M7. A high score, new palette, new name, or new description cannot rescue a repeated design.

1. **Write the identity contract before rendering.** Record the finish's name/idea, biological/material reference, unique carrier grammar, 5+ purposeful mark types, native scale, M/R/Cc binding law, and the nearest existing finishes it must not resemble.
2. **Construction must be unique without color.** Audit paint in grayscale and edge/spectral space. A recolor, phase shift, rescale, rotated copy, parameter tweak, or different seed of an existing carrier is the same design and fails. Shared low-frequency coordinate fields across a category are prohibited unless they model a documented common substrate and are visually subordinate.
3. **Spec must trace this finish—not a house template.** M/R/Cc states are derived from named paint features (cell, rim, vein, pore, rib, scale, groove, filament, etc.) and use distinct per-feature material tiers. Generic `f0/f1/f2` rainbow waves laid over unrelated paint fail. Deliberate spec-only/hidden-material designs are exceptions only when the identity contract explicitly requires them.
4. **Spec silhouette must also be unique without color.** Compare the combined spec and each M/R/Cc channel against every finish in the category at native and picker scale. Recoloring the same combined RGB/spec pattern fails because RGB here represents material channels, not decorative color.
5. **Live output is the authority.** Compare the actual standard and picker assets served by the app, not only isolated evidence. A runtime wrapper, stale bake, or catalog route that makes distinct sources look alike is still a failed finish.
6. **Cross-card rejection gate.** Run the category similarity audit before promotion. Color-invariant structural similarity >=0.68 is an automatic reject/rebuild unless the owner explicitly adjudicates a necessary shared substrate; 0.55–0.68 requires direct side-by-side owner-eye review. The owner's eye can reject below the threshold and always overrides the metric.
7. **Name test.** Hide the card title and ask whether the construction communicates the promised subject/process. Then reveal the title and record the visible evidence. If the explanation depends mainly on color or description text, the design is off-concept and fails.
8. **No category count credit for duplicates.** A repeated paint carrier, repeated spec carrier, or palette-only variant does not count toward the requested finish total.

For the active IRIDESCENT INSECTS lane, the executable live-picker gate is `scripts/spb_iridescent_insects_similarity_gate.py`; its baseline and every accepted movement belong in `docs/IRIDESCENT_INSECTS_REBUILD_2026-09-01.md` and the Living Wiki.

**Executable identity enforcement (2026-09-02):** every new or rebuilt finish
module must declare a valid `IDENTITY_CONTRACT` (`spb-finish-identity/1`) before
M7 is allowed to score it. Validation lives in `scripts/spb_finish_identity.py`.
The rendered cross-card gate must treat palette swaps, M/R/Cc channel swaps,
translations, flips and rotations as the same construction. Passing prose is
not passing evidence: both standard and picker output must still prove the
contract, and a failed name test or owner-eye review rejects the finish.

---

## 🔴 THE LIVING WIKI IS THE SINGLE SOURCE OF TRUTH — read + update it every session

Before touching anything, open **`SPB_WIKI.html`**. Every agent (Claude, Codex, Cursor, Gemini, Grok — no exceptions) **reads it first and updates it constantly** as work happens:

1. **READ** the **Agent Coordination Board** (who's on what + file lanes) + **Working Conventions (READ FIRST)**.
2. **CLAIM** your work on the **Agent Coordination Board** — what you're doing, the files/lane, status, date — so two agents never collide on a file.
3. **LOG as you go** in the **Daily Work Log** (newest at top): what you did, what you touched, what's left — throughout the session, not only at the end.
4. Wall you can't solve → **Known Trouble Spots**. Notable break+fix → **Post-Mortem**.

Sections are markdown inside `<script type="text/markdown" data-section="...">` blocks — edit the markdown, save, reload. A stale board/log (your row still "idle", or work that's done not logged) means the task wasn't finished. This is non-negotiable.

---

**Read `WORKSPACE_LOCATION.md` at the project root first.** It contains the canonical project location and the outstanding migration checklist from the 2026-05-14 move off the E: drive.

## Usage Budget Guardrail — owner mandate 2026-05-17

SPB has already burned too much Codex weekly usage through repeated giant-file reads. Treat usage containment as a production requirement.

- For all SPB work, read `docs/SPB_LOW_USAGE_PROTOCOL.md` immediately after `WORKSPACE_LOCATION.md`.
- For SPB-93/tool-system work, also read `docs/SPB_93_LOW_USAGE_PROTOCOL.md`.
- Do not dump monster files, raw full diffs of monster files, generated mirrors, archives, installers, packed Electron builds, image assets, or broad repo search output into the chat.
- Start with `node scripts\spb_context.js --list`, then request the smallest named context slice.
- For Linear context, follow `docs/SPB_LINEAR_LOW_USAGE.md`: read bounded issue/comment slices and maintain compact local mirrors.
- Prefer targeted `rg` searches and 50-150 line windows.
- Keep autonomous/heartbeat work paused unless the owner explicitly re-enables it with a longer interval and a narrow target.
- Every cleanup should make the next agent need less context, not more.

## ⚠️ UNIVERSAL RULES — owner mandate 2026-05-16 (SPB-105)

These apply to **every AI agent** touching finishes — Claude, Codex, Cursor, Grok, Gemini, anything. No exceptions.

1. **The 85% rule.** Any rebuilt or modified finish must score **≥85 on the M7 composite** before you stop iterating. Workflow: edit renderer → rebake thumbnail → run `python scripts/spb_workbook_compute_m1.py && python scripts/spb_workbook_compute_m7.py` → read the per-finish composite from `_workbook_metrics/m7_composite.json` → if <85, iterate. Don't ship until ≥85. (Note: 85 is the owner *ship-bar*, not the code keeper tier — M7's "keeper" threshold in code is **≥80** per `scripts/spb_workbook_compute_m7.py` as of 2026-05-30. 80–84 = code "keeper" but still below the owner ship-bar; keep iterating to ≥85.)
2. **Render budget.** Standard finish renders must complete in **2-3 seconds at 2048²**. Anything taking longer (e.g. tick-91 depth_bubble at 20s) is broken; fix the math. Layer stacking + zone overlays are allowed exceptions.
3. **Auditable comments.** Every renderer edit cites the SPB ticket, tick #, owner verdict snippet, and metric movement (composite before → after). Otherwise the next agent can't trace why the code looks the way it does.

For spec_driven intent finishes (Foundation / Enhanced Foundation / Ghost Geometry / Clearcoat) the M1 component is dropped from M7 composite by design (SPB-95). For those, also check spec_channel std stats directly via `scripts/spb86_probe_real_weak_clusters.py` — each of M_std / R_std / CC_std should be ≥20 with range spanning most of [0, 255]. Both must pass.

## Critical context

- Canonical working directory: `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`
- Stale/old path: `E:\Koda\Shokker Paint Booth Gold to Platinum` — do not edit anything there.
- If you are operating in `E:\Koda\...`, halt and notify the user that the project has moved.

## Two-copy rule (was three until 2026-06-09)

Core data files exist in TWO synchronized locations. When editing any of these, update both:
1. Project root (the source of truth — edit here)
2. `electron-app/server/` (the tree packaged into the installer)

**Why only two now:** until 2026-06-09 there was a third copy, `electron-app/server/pyserver/_internal/` (a vestigial PyInstaller bundle). It was EXCLUDED from the installer (`!pyserver/**` in `electron-app/package.json`), so it shipped to nobody and only created 3-way drift. It was deleted (~585 MB) and removed from the sync manifest. Sync is now root → `electron-app/server/` only, and the build hard-fails if the two drift. Do NOT recreate the third copy. (See CHANGELOG 2026-06-09.)

Files this applies to: `base_registry_data.py`, `paint-booth-0-finish-data.js`, `spec_patterns.py`, and `assets/reference_textures/cultural/viva_mexico/manifest.json`.

## Conventions

- Windows 10 host. Paths use backslashes.
- The host username path contains an apostrophe (`Ricky's PC`) — be careful with quoting in shell commands.
- **Tool System work (SPB-93 Heenan Family)**: Creating or editing architecture docs under `docs/` is explicitly allowed and encouraged when advancing the Foundation Hardening plan. See `docs/TOOL_ARCHITECTURE.md`.
- Keep `WORKSPACE_LOCATION.md` current — tick the migration checklist as items finish.

## Where to look

- `PRIORITIES.md` — current focus / steering
- `RESEARCH.md` — market intel and competitor notes
- `CHANGELOG.md` — session log
- `SPB_LINEAR_HANDOFF.md` — Linear handoff mirror
- `docs/ONBOARDING.md` — broader onboarding
- **`docs/TOOL_ARCHITECTURE.md`** — **MANDATORY for any work on painting tools, canvas dispatch, Zone vs Layer logic, or SPB-93**. This is the single source of truth for the tool system contract.

---

## Tool System Architecture (SPB-93 — Heenan Family Guiding Light)

All work on painting tools (brush, clone, fill, selection, spatial, layer transforms, etc.) **must** follow the rules in `docs/TOOL_ARCHITECTURE.md`.

### Critical Rules

- The single source of truth for tool routing is the dispatch logic (`isLayerToolbarMode`, the `zoneOnlyToolNames` / `layerOnlyToolNames` maps, and the early-return guards in the main mouse handlers).
- **Zone code** only ever mutates `zones[i].regionMask` / `spatialMask`.
- **Layer code** only ever mutates active PSD layer pixel buffers or layer transform state.
- New tools must be implemented in small dedicated files under a future `tools/zone/` or `tools/layer/` structure (during transition they may still live in `paint-booth-3-canvas.js` but must be cleanly extractable).
- Autonomous / sub-agent cycles must obey strict scoping (targeted reads only on `paint-booth-3-canvas.js` when instructed) and make one smallest safe reversible improvement per cycle.
- Every significant tool change must be posted to Linear **SPB-93** with context and diff.

Violating the Zone ↔ Layer boundary or growing the 19k-line monster further is considered a serious architectural regression.

See `docs/TOOL_ARCHITECTURE.md` for the full contract, module breakdown, and agent scoping guidelines.
