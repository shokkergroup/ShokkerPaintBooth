# Runtime Sync

The root-level UI/runtime files are the source of truth.

Managed files:
- `paint-booth-v2.html`
- `paint-booth-v2.css`
- `paint-booth-0-finish-data.js`
- `paint-booth-0-finish-metadata.js`
- `paint-booth-1-data.js`
- `paint-booth-2-state-zones.js`
- `paint-booth-3-canvas.js`
- `paint-booth-4-pattern-renderer.js`
- `paint-booth-5-api-render.js`
- `paint-booth-6-ui-boot.js`
- `paint-booth-7-shokk.js`
- `fusion-swatches.js`
- `swatch-upgrades.js`
- `swatch-upgrades-2.js`
- `swatch-upgrades-3.js`

Managed targets:
- `electron-app/server/`
- `electron-app/server/pyserver/_internal/`

Commands:
- `npm run sync-runtime`
- `npm run check-runtime-sync`
- `cd electron-app && npm run sync-runtime`
- `cd electron-app && npm run check-runtime-sync`

Build behavior:
- `electron-app/copy-server-assets.js` now runs the runtime sync before packaging.
- `electron-app/package.json` already runs `copy-server` as `prebuild`, so normal Electron builds stay aligned automatically.

Guardrails:
- `tests/smoke_test.py` checks that all manifest-managed runtime copies match the root source files.
- If you edit one of the managed root files, run the sync command before committing if you are not already going through the Electron build flow.
