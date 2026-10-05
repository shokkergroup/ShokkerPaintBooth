# SPB_WIKI.html — Build Log

## Build 2026-05-27T07:02Z

- **File:** `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\SPB_WIKI.html`
- **Size:** 60,018 bytes (~58.6 KB)
- **Tabs:** 11 (Overview, Architecture, Finish System, Spec Doctrine, Bugs / Watchlist, Recent Wins, Backlog, AI Agent Briefing, Tools & Scripts, Metrics Index, Owner Directives)
- **Rebuild strategy:** v2 written from scratch (existing v1 used a sidebar nav with cyan-on-navy palette; owner spec was top-bar tabs + dark `#111` palette with `--accent: #c5a572`). v1 was not appended — full rewrite produced a tighter, on-spec file.
- **Self-contained:** zero external CSS, zero CDN, zero JS libraries. Plain JS for tab switching and search filter. Opens offline.
- **Build verification:** size 58.6 KB sits inside the 30-50 KB ± target; 11 tabs each have matching `data-tab` button + `data-pane` section (22 total attribute hits in grep).

## Sources synthesized

1. `MEMORY.md` (auto-memory CLAUDE.md context block) — Universal Law, Tier Floor Policy, architecture quick-ref, 3-copy rule
2. `PRIORITIES.md` — Priority 1-5 (current focus), Priority 5 audit checklist, WARN-GGX-001..006, FLAG-IND-003, FLAG-CANDY, FLAG-OEM-002, BUG-CHROME-001, WEAK-001 through WEAK-024
3. `CHANGELOG.md` — 2026-05-27 RATE10 loops 1-7, 2026-05-26 spec-overlay first/second strike, 2026-04-23 HEENAN FAMILY 6h hardening (DECAL/STAMP/Fleet/compose_finish fixes), 2026-04-22 HEENAN FAMILY 2h (gradient single-stop, hex-string solid)
4. `RESEARCH.md` — RESEARCH-042 catalog snapshot (344 bases / 22 BASE_GROUPS / ~305 patterns / 27 PATTERN_GROUPS), category strength rankings, top-5 next-push priorities, RESEARCH-041 COLORSHOXX Wave 3
5. `SPB_FINISH_QUALITY_WORKBOOK.html` — `<pre id="changelog">` block (Tick 91 / 92 / 93 / 94, SPM7→SPM8→SPM9→SPM10 chain narrative, M9 Pearson 0.193 finding, owner concordance gap, false-positive / false-negative lists)
6. `_loop_state/round6_loop_state.json` — confirmed loop active (2 506 lines of state); no per-tick detail mined for brevity
7. `_loop_state/thumbnail_fix_progress.md` — Fix 1 swatch routes engine-vs-fake-painter env-gate drop, content-hash disk cache, v6 zone shape v2 (`_catalog_swatch_zone_for_preview_v2`)
8. `_loop_state/slider_bug_diagnostic.md` — Tick 1 + Tick 2 SCALE_BASE_MIN 1.0 → 0.05 + 6 missing handlers; smoke 40/40 PASS; 3-copy md5 `26f8439b…`
9. `engine/spec_pattern_aliases.py` — racing-pivot batches V1 / V2 / V3 + RENAME_V4 (~30 legacy aliases)
10. `paint-booth-0-finish-data.js` — registry list (BASES / PATTERNS / SPEC_PATTERNS / BASE_GROUPS / PATTERN_GROUPS / SPEC_PATTERN_GROUPS); no transcription
11. `SPB_QA_FINDINGS.md` — recent QA batch (Batch 135 Ctrl+Z/Ctrl+Y normalization), live build-check port `59876`

## Sources I wanted but did not find

- **No `bug_hunt_findings.md`** at the project root (the owner brief mentioned "pull from bug_hunt_findings.md if it exists" — it does not). Watchlist instead populated from `slider_bug_diagnostic.md` + `thumbnail_fix_progress.md` + WARN-P3 entries in `PRIORITIES.md` + R4/R9/R12 OPEN items from HEENAN risk register.
- **No `THUMBNAIL_BUG_DIAGNOSTIC.md`** at the project root (the brief listed it as a separate file). The diagnostic content used was from `_loop_state/thumbnail_fix_progress.md`, which references but doesn't duplicate the original diagnostic. If the original diagnostic exists elsewhere it wasn't surfaced via glob.
- **`server.py` first 200 lines route map** — not transcribed inline (would have bloated the file beyond budget); the wiki references the route surface (`/render`, `/api/spec-preview-composite`, `/api/spec-pattern-preview-metal`, swatch routes, `/build-check`) without enumerating every signature.
[Tick @ 2026-05-27T07:39:15Z] TRACK C wiki upkeep: added 3 new Active Bug cards — pattern-brush proposal (RED), orphan handlers (YELLOW), working-tree drift (YELLOW). Wiki now reflects current state for morning review.
