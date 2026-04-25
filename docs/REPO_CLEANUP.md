# Repo Cleanup

Date: 2026-04-20

## Summary

This pass focused on low-risk workspace hygiene:

- Archived clearly historical run docs and helper files
- Moved rotated logs and an old CSS backup out of the root
- Deleted disposable generated audit output and cache folders
- Left active source, runtime files, QA docs, assets, and ambiguous staging/output folders untouched

The goal was to reduce clutter without risking runtime behavior.

## Archived

### Root historical docs moved to `docs/archive/root-history/`

- `BOIL_THE_OCEAN_FINAL_REPORT.md`
- `BOIL_THE_OCEAN_METRICS.md`
- `OVERNIGHT_LOG.md`
- `OVERNIGHT_QUEUE.md`
- `OVERNIGHT_REPORT.md`

### Historical run docs moved to `docs/archive/run-history/`

- `docs/AUTONOMOUS_4HR_HANDOFF_2026_04_19.md`
- `docs/AUTONOMOUS_4HR_WORKLOG_2026_04_19.md`
- `docs/BONUS_RUN_HANDOFF_2026_04_19.md`
- `docs/FIVE_HOUR_DEEP_SHIFT_2026_04_19_HANDOFF.md`
- `docs/LOW_RISK_MAX_VOLUME_HANDOFF_2026_04_19.md`
- `docs/TRUE_FIVE_HOUR_HANDOFF_2026_04_19.md`
- `docs/TRUE_FIVE_HOUR_WORKLOG_2026_04_19.md`
- `docs/TWENTY_WINS_2026_04_19_HANDOFF.md`
- `docs/SPRINT_2026_04_17_FINAL_REPORT.md`
- `docs/SPRINT_2026_04_17_HANDOFF.md`
- `docs/HEENAN_FAMILY_OVERNIGHT_SIGNATURE_FINISH_PASS.md`
- `docs/HEENAN_FAMILY_OVERNIGHT_SIGNATURE_FINISH_PASS_HARDMODE.md`
- `docs/HEENAN_FAMILY_OVERNIGHT_SIGNATURE_FINISH_PASS_HARDMODE_AMENDED.md`

### Local-only legacy helpers moved to `_archive/2026-04-cleanup/legacy-root/`

- `BUILD_WIKI_OVERNIGHT.py`
- `BUILD_WIKI_ROUND2.py`
- `BUILD_WIKI_ROUND3.py`
- `HERMES.md`
- `HERMES_ONBOARDING.md`
- `HERMES_OVERNIGHT_SETUP.md`

### Local-only logs and backups moved to `_archive/2026-04-cleanup/`

- `server_log.txt.1`
- `server_log.txt.2`
- `server_log.txt.3`
- `paint-booth-v2.css.v611backup`

## Deleted

### Disposable generated files

- `_full_pattern_audit.json`
- `_pattern_audit_results.json`
- `_patterns_below_A.json`
- `test_swatch.png`

### Cache folders

- `.pytest_cache/`
- `__pycache__/`
- `_staging/monolithic_upgrades/__pycache__/`
- `_staging/pattern_upgrades/__pycache__/`
- `engine/__pycache__/`
- `engine/expansions/__pycache__/`
- `engine/paint_v2/__pycache__/`
- `engine/registry_patches/__pycache__/`
- `tests/__pycache__/`

## Intentionally Kept

These looked like cleanup candidates but were left alone because they may still be active, useful, or risky to touch without a second pass:

- `server_log.txt`
- `FINISH_QUALITY_REPORT.md`
- `FINISH_QUALITY_REPORT_v2.md`
- `MONOLITHIC_HEALTH_REPORT.md`
- `PATTERN_HEALTH_REPORT.md`
- `QA_REPORT.md`
- `REGISTRY_CONFLICTS.md`
- `CLEANUP_DECISION_NEEDED.md`
- `CLEANUP_LOG.md`
- `output/`
- `PayHip-upload/`
- `Ricky Whittenburg/`
- `docs/HARDMODE_AUTONOMOUS_FINAL_SUMMARY.md`
- `docs/HARDMODE_AUTONOMOUS_WORKLOG.md`
- `docs/hardmode_proof/`

## Why These Decisions

- Historical run/handoff docs were cluttering the main `docs/` surface but still may be useful for later reference, so they were archived instead of deleted.
- Root-level overnight reports and boil-the-ocean snapshots were old enough to move off the main shelf without losing them.
- Rotated logs and the CSS backup were safe to remove from day-to-day view but worth preserving locally.
- JSON audit outputs and caches were straightforward disposable artifacts with no value once regenerated.
- `output/`, `PayHip-upload/`, and similar directories were left untouched because they may contain current assets, staging payloads, or useful render/debug material.

## Result

The root is lighter, `docs/` is less dominated by handoff/worklog debris, and the obvious generated junk is gone.

## Verification

Run after cleanup:

- `python -m pytest tests -q`
- `node tests/_runtime_harness/validate_finish_data.mjs`
- `node tests/_runtime_harness/registry_collisions.mjs`
- `node scripts/sync-runtime-copies.js --write`
- `node --check paint-booth-0-finish-metadata.js`
