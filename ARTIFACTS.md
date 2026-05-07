# SPB Repository Artifacts Inventory

> Index of "what's that file doing in the root?" — scan output of abandoned, historical, and unclear files in the SPB repo.

This document was produced during the Gold-to-Platinum final audit. It catalogues files at the project root that look dated, experimental, or unclear, and proposes a disposition for each. Most of these are safe to delete but tracked here in case anyone needs to recover one.

**Status legend:**
- *KEEP* — in active use, leave alone
- *ARCHIVE* — move to `_archive/` (already gitignored)
- *DELETE* — safe to remove next cleanup pass
- *REVIEW* — ambiguous; needs owner decision

---

## Build / Wiki Scripts (one-shot overnights)

| File | Status | Notes |
|---|---|---|
| `BUILD_WIKI_OVERNIGHT.py` | ARCHIVE | One-off script from early April 2026 wiki generation run. Superseded by current `SPB_*.md` doc structure. |
| `BUILD_WIKI_ROUND2.py` | ARCHIVE | Second iteration of wiki generator. Same as above. |
| `BUILD_WIKI_ROUND3.py` | ARCHIVE | Third iteration. Current docs are hand-maintained now. |
| `HERMES.md` | ARCHIVE | Historical agent spec for the "Hermes" doc agent. Superseded. |
| `HERMES_ONBOARDING.md` | ARCHIVE | Hermes agent onboarding. Superseded. |
| `HERMES_OVERNIGHT_SETUP.md` | ARCHIVE | Hermes overnight setup. Superseded. |

## Audit & Report Snapshots

**Relocated 2026-04-24:** all 6 health/QA snapshots moved from repo root to
`docs/health-reports/`. The "Active" labels for `QA_REPORT.md` and
`REGISTRY_CONFLICTS.md` still apply — agents updating them now write to
`docs/health-reports/<FILE>.md`. Update path references accordingly.

| File (in `docs/health-reports/`) | Status | Notes |
|---|---|---|
| `FINISH_QUALITY_REPORT.md` | KEEP (read-only) | Snapshot of finish audit 2026-04-03. Referenced by QA agent. |
| `FINISH_QUALITY_REPORT_v2.md` | KEEP (read-only) | Follow-up audit same day. Keep both for history. |
| `PATTERN_HEALTH_REPORT.md` | KEEP (read-only) | Pattern audit snapshot 2026-04-03. |
| `MONOLITHIC_HEALTH_REPORT.md` | KEEP (read-only) | Monolithic finishes audit 2026-04-03. |
| `QA_REPORT.md` | KEEP | Active QA tracking doc. Referenced by agents. |
| `REGISTRY_CONFLICTS.md` | KEEP | Active conflict log. |
| `OPEN_ISSUES.md` (still at root) | REVIEW | Last updated 2026-03-29. May be stale; check against GitHub Issues. |

## Overnight Logs

| File | Status | Notes |
|---|---|---|
| `OVERNIGHT_LOG.md` | ARCHIVE | Log from overnight run 2026-04-02. Historical. |
| `OVERNIGHT_QUEUE.md` | ARCHIVE | Queue file for overnight run. Historical. |
| `OVERNIGHT_REPORT.md` | ARCHIVE | Report output from overnight run. Historical. |

## Cleanup Decisions

**Relocated 2026-04-24:** both files moved from repo root to
`_archive/cleanup-history/`. The 2026-03-30 decision queue had been
superseded by subsequent CHANGELOG entries; the cleanup log is preserved
for historical audit.

| File (in `_archive/cleanup-history/`) | Status | Notes |
|---|---|---|
| `CLEANUP_DECISION_NEEDED.md` | ARCHIVED | 2026-03-30 decision queue. Superseded by later CHANGELOG entries; preserved for audit trail. |
| `CLEANUP_LOG.md` | ARCHIVED | Log of prior cleanups. Historical; preserved for reference. |

## Dev Docs (historical)

| File | Status | Notes |
|---|---|---|
| `DEVELOPMENT_NOTES.md` | REVIEW | Pre-dates `docs/DEVELOPMENT.md`. Migrate any still-relevant bits then delete. |
| `RESEARCH_REFERENCE.md` | KEEP | Active research pointer file. Short and useful. |
| `SHOKKER_BIBLE.md` | KEEP | Brand/voice bible. Used by docs agent. |

## Temporary JSON Audit Output

| File | Status | Notes |
|---|---|---|
| `_full_pattern_audit.json` | DELETE | Audit output, gitignored. Regenerate as needed. |
| `_pattern_audit_results.json` | DELETE | Same. |
| `_patterns_below_A.json` | DELETE | Same. |

## Backup CSS

| File | Status | Notes |
|---|---|---|
| `paint-booth-v2.css.v611backup` | ARCHIVE | Pre-v6.1.1 CSS backup. Keep until v6.2 ships clean. |

## Build Helper Scripts

| File | Status | Notes |
|---|---|---|
| `audit_finish_quality.py` | KEEP | Active audit script. Used by QA agent. |
| `benchmark_finishes.py` | KEEP | Active bench script. Referenced in docs. |
| `BUILD_INSTALLER.py` | ARCHIVE | Pre-electron-builder installer script. Superseded. |
| `shokker_color_monolithics.py` | ARCHIVE | One-shot expansion script. Code folded into `engine/expansions/color_monolithics.py`. |

## Startup Batch Files

| File | Status | Notes |
|---|---|---|
| `START_SERVER.bat` | KEEP | Convenience launcher for Python server. |
| `START_V5_DEV.bat` | REVIEW | V5 dev mode launcher. V5 may be deprecated. Confirm before delete. |
| `WAKE_AGENT.bat` | KEEP | Agent wake script. Used by scheduler. |

## Marketing / Community

| File | Status | Notes |
|---|---|---|
| `SPB - QR - Discord.jpg` | KEEP | Discord QR code image. Used in Discord announcements. |
| `SPB_DISCORD_ANNOUNCEMENT.md` | KEEP | Announcement template. |
| `SPB_RELEASE_NOTES.md` | KEEP | User-facing release notes. |
| `PayHip-upload/` | KEEP (gitignored) | Staging folder for PayHip uploads. Local only. |

## User-Facing Docs (authoritative)

The following `SPB_*.md` files are all KEEP and are actively maintained by the docs agent:

- `SPB_GUIDE.md`
- `SPB_QUICKSTART.md`
- `SPB_FEATURES.md`
- `SPB_FAQ.md`
- `SPB_KEYBOARD_SHORTCUTS.md`
- `SPB_SPEC_MAP_GUIDE.md`
- `SPB_TROUBLESHOOTING.md`
- `SPB_WORKFLOW_EXAMPLES.md`

These files are **owned by the docs agent**. Do not edit them ad hoc.

## Sample / Demo Content

| Path | Status | Notes |
|---|---|---|
| `assets/` | KEEP | Screenshots, QR codes, icon. |
| `Ricky Whittenburg/` | REVIEW | Personal folder. Might belong outside the repo. |

---

## Proposed Cleanup (one-time)

When doing a cleanup pass, the safe deletes are:

1. `_full_pattern_audit.json`, `_pattern_audit_results.json`, `_patterns_below_A.json` (gitignored anyway, regenerable).
2. `paint-booth-v2.css.v611backup` after v6.2.0 ships stable.
3. `BUILD_WIKI_*.py` trio (move to `_archive/`).
4. `HERMES*.md` trio (move to `_archive/`).
5. `OVERNIGHT_*.md` trio (move to `_archive/`).

The ARCHIVE tier can all go to `_archive/` which is gitignored, keeping repo root clean without losing history.

---

## Process for Future Artifacts

When you generate a one-shot artifact (audit output, overnight log, etc.):

1. Prefix with `_` so `.gitignore` catches it.
2. If it must be tracked, put it in `_archive/YYYY-MM-DD/` not the root.
3. If you produce a report that the team should read, add it to this file with a disposition.

This keeps the root directory signal-to-noise high.

---

*Last updated: 2026-04-17*
