# Paste-Ready SPB New Chat Goal Prompt

Use this in a fresh Codex chat/thread. The old heartbeat loop should stay
deleted/paused so the new thread is not competing with stale context.

```text
/goal

Workspace:
E:\Koda\Shokker Paint Booth Gold to Platinum

Goal:
Continue Shokker Paint Booth post-alpha hardening using Linear as the source of
truth. Work SPB-67 catalog-wide finish performance and redundancy hardening one
bounded active UI category at a time until the active catalog scorecard no
longer has weak, lazy, redundant, oversized, flat-spec, broken, or slow
owner-visible finish categories.

Before every pass:
1. Read SPB_LINEAR_HANDOFF.md.
2. Read SPB_GOAL_OPERATING_BRIEF.md.
3. Read docs/SPB_VISUAL_FINISH_NONNEGOTIABLES.md.
4. Read docs/SPB_2048_VISUAL_SCALE_RULES.md.
5. Inspect git status.
6. Inspect Linear team "Shokker Paint Booth", project "SPB Post-Alpha Hardening".
7. Work SPB-67 unless Linear shows a higher-priority active issue.

Planning source:
- Use active-only scorecard:
  audit/2026-05-03-spb-catalog-scorecard-active-v2
- Use orphan_inventory.csv only for separate cleanup/quarantine decisions.
- Do not let deleted/orphaned finishes inflate active work.

Non-negotiables:
- No lazy patterns.
- No repeated pattern DNA.
- No same generator with swapped colors.
- Details must fit 2048x2048 full-car scale.
- When detail looks "enough", push it 25-40% finer.
- Specs must mimic paint structure and use rich metallic/roughness/clearcoat
  channel variation.
- Flat green/yellow specs are not good enough for expressive finishes.
- Do not use generic spec stripes/slashes when paint has meaningful design.
- Fix source renderer logic, not lazy shared wrappers.
- Do not silently swallow renderer errors.
- Preserve user changes.
- Sync runtime mirrors.
- Prefer <=3s render time; treat >5s as a red flag.

Current owner pain points to honor:
- Rising Sun specs are closer but still need 30-40% more detail and richer
  channel variety.
- Viva Mexico specs need total rework from flat/original style.
- Cultural specs should trace meaningful design elements: suns, dragons, devils,
  eyes, rays, hot edges, flowers, architecture, and raised/etched motifs.
- Reactive Panels and Effects/Vision categories still have oversized/lazy detail
  problems.
- Signal category is the best recent quality reference for lively, detailed,
  paint-matching specs. Learn from it, do not clone it.

Work loop:
1. Choose one bounded active category from SPB-67/scorecard.
2. Preassess active entries for render time, redundancy, detail scale, paint
   quality, and spec quality.
3. Rebuild weak entries individually from source renderer logic.
4. Keep every finish unique. Shared helpers are allowed only if outputs are
   genuinely distinct in layout, density, rhythm, material, and spec response.
5. Verify runtime mirror sync.
6. Run focused tests and/or runtime harness checks.
7. Generate a 512 and/or 2048 Visual Workbench review page.
8. Update Linear with:

Focus:
Done:
Verified:
Risks:
Next:

Checkpoint rule:
After each category, stop and report:
- category completed
- review page path
- files changed
- tests/checks run
- render-time risks
- recommended next category

Do not run silently for days without checkpoints. Move fast, but keep the work
reviewable.
```

