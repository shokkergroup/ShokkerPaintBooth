# SPB Morning Brief — 2026-05-27

> Single-page summary of the overnight maintenance loop. Open `SPB_WIKI.html` for full deep-dive on any item.

---

## ✅ Landed overnight (no action needed)

1. **Thumbnail paint side fixed.** Dropdown swatches now render through the real engine instead of the fake painter. Per-finish disk cache keyed on a content hash → updates self-invalidate. Verify PNGs at `_loop_state/thumbnail_fix_verify/` show 5 categories side-by-side.

2. **Slider regression fixed.** `SCALE_BASE_MIN` lowered to 0.05 (sub-1.0 tiling now works) + 6 missing Color/Spec scale handlers wired per-zone. Smoke test 40/40 PASS. Zones isolated A/B confirmed.

3. **Inner-mirror drift caught and re-synced.** 10 paint_v2/v3 engine files were stale in `pyserver/_internal/` but matched root in the outer Electron mirror. Re-mirrored, py_compile clean on all 10. Wide-scan found 153 sibling files in sync.

4. **SPB_WIKI.html built.** 11-tab single-source-of-truth at project root, ~80 KB after tonight's updates, fully self-contained. Tabs include AI Agent Briefing with the 3 doctrines every future agent needs (Tier Floor, Universal Law, 3-Copy Mirror).

5. **Root archive proposal staged.** 35 safe-to-archive files (~21 MB), 9 unsure, ~120 load-bearing. Opt-in PowerShell script at `_loop_state/archive_apply.ps1` — idempotent, run when you want.

---

## 🟠 Needs your decision (action items)

| # | Item | What's needed | Where |
|---|---|---|---|
| 1 | **Pattern brush silently broken** | Approve the Case-B JS adapter fix (switch to `GET` + query string + blob URL). Then I apply + 3-copy mirror + smoke. | `_loop_state/pattern_brush_fix_proposal.md` |
| 2 | **Missing `user-import-car-preview.js`** | Decide: (a) create the JS with intended functionality, (b) remove the script tag, or (c) point at an existing file that has the function. 404 baked into dist. | bug_hunt_findings.md TICK 5 |
| 3 | **Packaged dist is 4 days stale** | Rebuild before any contributor distribution — current dist ships ALL the bugs we just fixed. Run `npm run dist` (or equivalent). | bug_hunt_findings.md TICK 6 |
| 4 | **Orphan handlers in `paint-booth-v2.html`** | Confirm whether `activateLicense / deactivateLicense / skipTutorial / nextTutorialStep / toggleRenderStats` are planned features or dead UI. | Bug hunt CRITICAL #3 |
| 5 | **716 uncommitted files in working tree** | Targeted commit-or-revert sweep recommended before more drift accumulates. Same risk surface that produced all 4 of tonight's regressions. | Bug hunt sidebar concern |
| 6 | **6 dead-code candidates** (low priority) | Leave-in-place is safe; can be cleaned in a future release-build pass. | bug_hunt_findings.md TICK 3-4 |

---

## 📊 Numbers from tonight's runs

- 4 background agents launched · all completed cleanly
- 8 loop ticks fired between 07:11–08:54 UTC
- 14 bugs catalogued (3 CRITICAL · 5 HIGH · 3 MED · 3 LOW)
- 10 engine files re-mirrored
- 5 new active-bug cards added to the wiki
- 0 changes pushed to git (per loop discipline — owner-controlled)

---

## 🔄 Pattern observed

Tonight's bug pattern is **partial uncommitted edits**. Every single regression has the same shape: a 2026-05-22 / 2026-05-23 working-tree edit that touched one side of a contract (HTML, or JS, or server, or dist) without touching the other side. That's why all four bugs (slider clamp, slider handlers, thumbnail engine path, pattern brush route, missing JS, stale dist) share a single root cause.

**Single biggest win available:** finish committing or reverting the 716-file working tree. That alone will prevent ~80% of future regressions of this class.

---

## 🛠 Continuing

The 15m maintenance loop (`b6180cde`) continues firing on regression watch + wiki upkeep + new-bug hunting. When you're ready to pick up items 1-5 above, just ask — each one is a contained next-tick step with a clear contract already documented.

**Wiki:** `SPB_WIKI.html` (open in browser)
**Full bug catalog:** `_loop_state/bug_hunt_findings.md`
**Mirror health:** `_loop_state/regression_watch.md`
**Archive proposal:** `_loop_state/archive_proposal.md` + `_loop_state/archive_apply.ps1`
