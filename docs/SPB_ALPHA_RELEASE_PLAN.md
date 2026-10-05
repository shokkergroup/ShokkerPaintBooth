# SPB Alpha Release Plan

Status: active release-readiness spine for SPB-105.
Owner direction: 2026-05-20.

## Mission

Move Shokker Paint Booth from open-ended alpha development into a paid early-access candidate that painters can trust for one complete workflow:

```text
Import PSD/template -> assign zones/layers -> apply finishes/patterns/spec -> live preview -> render -> export to iRacing -> reload saved state and repeat
```

The release goal is not "everything SPB could ever become." The release goal is a dependable buyer workflow with known limits.

## Release Lane

Only these areas are release-blocking for the alpha candidate:

1. **Startup and project load**
   - App opens without console-breaking errors.
   - Source paint and iRacing output folder selection works.
   - Auto-restore never blocks boot.

2. **PSD and layer workflow**
   - PSD import populates layers correctly.
   - Layer visibility, lock state, selection, transform, duplicate, merge, and flatten behave predictably.
   - Layer tools mutate only active editable layer pixels or transforms.

3. **Zone workflow**
   - Zone creation, selection, source-layer restriction, masks, colors, finishes, base overlays, and spec overlays round-trip through save/load.
   - Zone tools mutate only zone masks/regions.

4. **Preview/render/export trust**
   - Live Preview, Refresh, full Render, and export use the same payload semantics.
   - A visible control must affect the exact thing it claims to affect.
   - Cache invalidation must never make stale results look like current results.

5. **Packaging and handoff**
   - Runtime mirrors are synced.
   - Installer launches cleanly.
   - Known limitations are documented.

6. **File-budget and AI-usage control**
   - Monster files are release-readiness risks because they force costly context reads and make fixes harder to isolate.
   - Every pass should prefer extracting bounded modules over adding to the largest files.
   - `scripts/spb_file_budget.js` is the tripwire: targets are refactor goals; ceilings prevent new bloat while the app is stabilized.
   - `scripts/spb_generated_drift_guard.js` is the stricter ratchet for `paint-booth-0-catalog-scorecard.js` and `engine/spec_patterns.py`; growth there must be paid down with extraction or explicit owner review, not casual ceiling bumps.

## Freeze Rules

Until this plan exits P0/P1 hardening:

- No new finish/category expansion unless it fixes a release-blocking bug.
- No new tool families unless they replace a broken release-lane tool.
- No large visual redesigns unless they remove workflow confusion.
- No broad monster-file reads. Use `docs/SPB_LOW_USAGE_PROTOCOL.md` and `scripts/spb_context.js`.
- No new code should be added to a monster file when a small module can own it.
- If a monster file must be touched, leave it no larger unless the change fixes a release blocker.
- Prefer small reversible fixes with focused verification.

## Trust Kill List

Any item below is a release blocker when it occurs inside the release lane:

- A button does nothing.
- A slider/control moves but does not affect render output.
- Preview differs from full render without a documented reason.
- Render differs from export without a documented reason.
- Save/load changes painter-authored values.
- Auto-restore prevents boot.
- A zone tool mutates layer pixels.
- A layer tool mutates zone masks.
- A missing source/layer silently broadens scope instead of failing closed.
- Cache reuse shows stale output after Refresh or Render.
- UI hides/clips current values needed for painter trust.
- Backend exceptions are swallowed without a visible failure state.

## Release Gates

The alpha candidate is not release-ready until:

1. `docs/SPB_RELEASE_GAUNTLET.md` has a dated PASS run on the canonical project.
2. P0 issues found by the gauntlet are fixed or explicitly scoped out of the release lane.
3. Runtime mirrors pass sync verification for changed files.
4. Relevant Python/JS syntax checks pass.
5. `node scripts/spb_file_budget.js --enforce` passes.
6. `node scripts/spb_generated_drift_guard.js --enforce` passes.
7. A clean packaged app smoke test completes the release lane once.

## Linear

Primary Linear issue: SPB-105, "Alpha release readiness gauntlet and P0 trust hardening".

Every autonomous run should update SPB-105 and the active Codex thread:

```text
Focus:
Done:
Verified:
Risks:
Next:
```
