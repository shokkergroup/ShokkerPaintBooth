# Archive Index

This folder holds **old audit outputs, dated run/overnight logs, finished sprint notes, one-off scripts, and stray exports** that were cluttering the project root. Nothing here is load-bearing — it's all reference-on-demand. Moved 2026-05-29 during the ship-ready cleanup (the full classification of all ~154 root files is in `docs/archive/root-history/SPB_ROOT_DECLUTTER_PLAN.md`).

**Pass 2 (2026-05-29, overnight):** root was already in good shape after pass 1 — only safe residue moved/removed: deleted 2 rotated 5 MB `server_log.txt.*` (gitignored junk) + a stray `nul`; archived the superseded `SPB_ROOT_DECLUTTER_PLAN.md` here under `root-history/`. Everything else in root is canonical, load-bearing, live tooling, or an owner-decision item (see that plan's §2).

## 👀 What to actually read (canonical docs, still in root)

You do **not** need to read anything in this archive day-to-day. The short canonical set:

| Doc | Purpose |
|-----|---------|
| `SPB_ALPHA_AUDIT.md` | The pre-Alpha codebase audit driving current work. |
| `SPB_TEST_TRIAGE.md` | Triage of the test-suite failures + what's safe to fix. |
| `SPB_ROOT_DECLUTTER_PLAN.md` | Full classification of every root file (keep / archive / load-bearing). |
| `SPB_SPEC_OVERLAY_REGROUP.md` | The spec-overlay regroup plan that was applied. |
| `PRIORITIES.md` | Current focus / steering. |
| `OPEN_ISSUES.md` | Open bug/quality tracker. |
| `CHANGELOG.md` | Session summaries + tags. |
| `README.md` · `CLAUDE.md` · `AGENTS.md` | Repo + agent operating docs. |
| `WORKSPACE_LOCATION.md` / `SPB_CANONICAL_WORKSPACE.md` | "Where does the project live" tie-breaker. |

## 📦 What was moved here (2026-05-29)

| From (root) | To |
|-------------|----|
| `CODEX 55 SPB.md` | `docs/archive/handoffs/` |
| `MORNING_BRIEF_2026-05-27.md` | `docs/archive/overnight-runs/` |
| `LOOKS_THEMING_SPRINT.md` | `docs/archive/sprints/` |
| `UI_UX_OVERNIGHT_SPRINT.md` | `docs/archive/sprints/` |
| `shokker-material-report-grad_aqua_drift-sphere.json` | `docs/archive/material-reports/` |
| `shokker-material-report-mc_neon_camo-sphere.json` | `docs/archive/material-reports/` |
| `shokker-material-report-rs_bell_of_damned-sphere.json` | `docs/archive/material-reports/` |
| `_handler_names.txt` | `docs/archive/audits/` |
| `patch_light_optics_scorecard.py` | `scripts/archive/oneoff/` |
| `retool_fusions.py` | `scripts/archive/oneoff/` |
| `_id_audit.py` | `scripts/archive/oneoff/` |
| `_id_audit2.py` | `scripts/archive/oneoff/` |
| `_route_audit.py` | `scripts/archive/oneoff/` |

All 13 were reference-checked first — none are imported by code, referenced by the build/manifest, or run in tests.

## 🟡 Second-pass candidates — reference-checked, KEPT (they're entangled/active)

A more aggressive second pass was attempted but the obvious-looking candidates turned out to be **load-bearing or active**, so they were deliberately left in root:

| Doc | Why it stays |
|-----|--------------|
| `SPB_LINEAR_HANDOFF.md` | Read by `scripts/spb_context.js` via `spb_context_targets.json` — moving breaks the context tool. |
| `THUMBNAIL_BUG_DIAGNOSTIC.md` | Named in `server.py:1917`. |
| `OVERNIGHT_STATUS.md` | Written by `scripts/overnight_finish_worker.py`. |
| `SPB_PICKER_UI_UX_AGENT_HANDOFF.md` | Active SPB-70 picker work (cited by Slack playbook + UI/UX overnight docs). |
| `SPB_UI_UX_NEXT_THREAD_HANDOFF.md` | Linked from `docs/SPB_UI_UX_DASHBOARD.html` + Slack ops. |
| `SPB_QA_FINDINGS.md` | Active QA log; referenced by `docs/SPB_LOW_USAGE_PROTOCOL.md`. |
| `DEVELOPMENT_NOTES.md` | Flagged in `ARTIFACTS.md` as "migrate then delete" — has content to migrate first. |
| `SPB_SLACK_*.md` | Live Slack-ops operating docs. |
| `SPB_WORKBENCH_*.html` / `SPB_RATE_*.html` | Active finish-rating / workbench tools you open directly. |

**Takeaway:** the root's remaining docs are genuinely canonical, code-referenced, or active. Getting to literally "2-3 docs" isn't safe without losing live content or breaking tools — the realistic canonical reading set is the ~9 listed above. Any further consolidation (e.g. merging the 3 Slack docs, or migrating `DEVELOPMENT_NOTES.md` into `docs/DEVELOPMENT.md`) is a content-merge judgment call best made with you.

> Note: a stray zero-byte `nul` file remains at root (a Windows reserved device name that resists normal moves); it's gitignored and harmless. Leave to a manual cleanup.
