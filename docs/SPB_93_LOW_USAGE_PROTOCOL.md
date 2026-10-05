# SPB-93 Low-Usage Protocol

Status: mandatory for Codex/AI work on SPB-93 after the 2026-05-17 usage spike. This document extends the repo-wide `docs/SPB_LOW_USAGE_PROTOCOL.md`; read that first.

SPB-93 work must not spend a weekly usage budget by repeatedly loading giant files. The tool system still needs hardening, but every pass must use a narrow context window and prove its work with focused checks.

## Read Order

1. Read `WORKSPACE_LOCATION.md`.
2. Read `docs/SPB_LOW_USAGE_PROTOCOL.md`.
3. Read this file.
4. Read only the needed section of `docs/TOOL_ARCHITECTURE.md`, not the whole document unless changing the architecture contract.
5. Use `node scripts/spb_context.js --list` to choose a small context target.

## Hard Limits

- Do not print all of `paint-booth-3-canvas.js`.
- Do not run raw `git diff` on `paint-booth-3-canvas.js`.
- Do not run broad `rg` over the whole repo when a file-scoped search will do.
- Do not dump full test files, generated files, Electron mirrors, image manifests, or build artifacts.
- Do not use autonomous 30-minute loops for SPB-93 unless the owner explicitly re-enables them.
- Keep Linear updates concise: finding, change, verification, next target.

## Preferred Commands

Use the context gateway first:

```powershell
node scripts\spb93_context.js --list
node scripts\spb93_context.js dispatch
node scripts\spb93_context.js canvas-guards
node scripts\spb93_context.js pick-item
node scripts\spb_context.js --target canvas-dispatch
node scripts\spb_context.js --target canvas-layer-target
```

For targeted searches:

```powershell
rg -n "requireLayerToolbarTarget|canvasMode === 'fill'" paint-booth-3-canvas.js js\canvas\dispatch.js
```

For small line windows:

```powershell
$lines = Get-Content paint-booth-3-canvas.js
$start = 3000; $end = 3060
for ($i = $start; $i -le $end; $i++) { '{0,5}: {1}' -f $i, $lines[$i-1] }
```

For changed-file awareness:

```powershell
git status --short -- paint-booth-3-canvas.js js\canvas\dispatch.js tests\test_layer_system.py
```

## Verification Ladder

Run only the smallest verification that proves the change:

1. Structural regression for the touched behavior, usually a focused `pytest -k`.
2. `node --check` for changed JS and mirrored runtime copies.
3. `node scripts\sync-runtime-copies.js --check` if client runtime files changed.

Run broad suites only when a shared contract or renderer changes.

## Extraction Bias

When a fix requires adding new tool logic, prefer a small module under `js/canvas/` or future `tools/zone/` / `tools/layer/` instead of adding more bulk to `paint-booth-3-canvas.js`.

If a change must touch the giant file, edit the smallest local block and add a regression that lets the next pass inspect the behavior without rereading the whole file.
