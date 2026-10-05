# Shokker Paint Booth Low-Usage Protocol

Status: mandatory for all AI/Codex/Claude/Cursor/Grok work after the 2026-05-17 usage spike.

The SPB app contains several huge source files, generated docs, packaged builds, image assets, Electron mirrors, and archives. Agents must not treat the repository as a normal small codebase. Every task starts by taking the smallest useful context slice.

## Required Read Order

1. `WORKSPACE_LOCATION.md`
2. This file
3. `AGENTS.md` only if the active prompt did not already provide it
4. A named context target from `scripts/spb_context.js`

Only read a domain-specific architecture doc when the task enters that domain. Example: `docs/TOOL_ARCHITECTURE.md` is required for painting tool routing, not for every unrelated task.

## Hard Bans

- Do not print an entire monster file into chat.
- Do not run raw full `git diff` on monster files.
- Do not broad-search generated mirrors, archives, installers, packed Electron builds, image assets, or `_workbook_metrics`.
- Do not open `electron-app/server/` mirrors unless checking runtime sync or a packaged-runtime bug.
- Do not run autonomous loops below a multi-hour interval unless the owner explicitly approves the cost.
- Do not re-read large docs every turn when a short protocol or named slice is enough.

## Monster Files

Treat these as slice-only files:

- `paint-booth-3-canvas.js`
- `paint-booth-2-state-zones.js`
- `shokker_engine_v2.py`
- `server.py`
- `paint-booth-0-catalog-scorecard.js`
- `paint-booth-0-finish-data.js`
- `paint-booth-4-pattern-renderer.js`
- `finish-viewer.html`
- `SPB_WIKI.html`
- `SPB_QA_FINDINGS.md`
- large expansion modules under `engine/expansions/`

## Default Tool

Use the repo-wide context gateway:

```powershell
node scripts\spb_context.js --list
node scripts\spb_context.js --target canvas-dispatch
node scripts\spb_context.js --target server-render
node scripts\spb_context.js --target server-diagnostics
node scripts\spb_context.js --target server-static-pages
node scripts\spb_context.js --target server-config
node scripts\spb_context.js --target server-render-monitoring
node scripts\spb_context.js --find "preview_render_endpoint" server.py
node scripts\spb_context.js --large
```

The gateway excludes known expensive directories by default and caps search output.
The gateway's named target database lives in `scripts/spb_context_targets.json`; see `docs/SPB_CONTEXT_DATABASE.md` before adding or changing targets.
For Linear context, read `docs/SPB_LINEAR_LOW_USAGE.md`; use bounded issue/comment reads and compact local mirrors instead of full discussion dumps.

## Expensive Directories

Avoid these unless the task specifically targets packaging, release artifacts, or image assets:

- `.git/`
- `node_modules/`
- `electron-app/server/`
- `electron-app/dist*/`
- `_archive/`
- `_workbook_metrics/`
- `.claude/worktrees/`
- `PayHip-upload/`
- `docs/DNA FINISH BIBLES/`
- `server_log.txt` and other logs
- large binary/image folders under `assets/reference_textures/`

## Verification Ladder

Use the smallest proof that covers the change:

1. Syntax check for changed JS/Python.
2. Focused unit or structural test with `-k`.
3. Runtime sync check only when mirrored client/server files changed.
4. Broad suites only for shared contracts, release gates, or renderer changes.

For heartbeat/status-only release checks, prefer `node scripts\spb_release_gate_status.js`.
It reports only current gate blockers and the short scorecard drift summary. Use the strict
`--enforce` scripts when a formal gate result is needed.

## Structural Goal

Every cleanup should reduce future context cost. Prefer:

- small modules over appending to giant files
- named context targets over ad hoc reads
- focused regression tests over repeated manual inspection
- generated indexes/maps over rereading large source files
- route modules under `server_routes/` over adding endpoints to `server.py`
- compact Linear mirrors over rereading long Linear discussions
- compact release status via `scripts\spb_release_gate_status.js` over dumping the full file-budget table
- `scripts/spb_generated_drift_guard.js --enforce` before accepting any growth in `paint-booth-0-catalog-scorecard.js` or `engine/spec_patterns.py`
