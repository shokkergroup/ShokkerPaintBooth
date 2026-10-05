# SHOKK DEMO Electron shell

This package is independent from the full Shokker Paint Booth desktop app. It
uses its own application identity, installer identity, executable, shortcut,
storage directories, Chromium session, server port, release feed, and staged
server payload.

## Commands

- `npm run stage` calls `demo/build_demo_stage.py --output electron-demo/.stage`
  and adds the hardened Electron main/preload files to that disposable stage.
- `npm start` stages, launches `server/demo_server.py` on `127.0.0.1:59886`,
  waits for the demo-only health response, and opens the app.
- `npm run build` stages and creates the Windows installer in `dist/`.

Packaged builds require `.stage/server/python/python.exe`. Development may use
`SPB_DEMO_PYTHON`, `py -3`, or `python3`; there is no full-product server or
runtime fallback.

## Production build

From the repository root, verify or rebuild the reviewed 2048px material pack,
then build the isolated installer:

```powershell
python -m demo.backend.build_snapshots --verify --min-size 2048
python -m demo.verify_color_fidelity
cd electron-demo
npm ci
npm run build
```

The installer and its `shokk-demo.yml` update metadata are written to `dist/`.
The stage is regenerated from an explicit allowlist on every build; do not hand
edit or publish `.stage`.

Before a public release, Authenticode-sign the executable/installer, verify the
signature on a clean Windows profile, and replace the supplied branded starter
paint with marketing-safe fictional/owned artwork unless the necessary rights
are documented. Upload only to the separate `/shokk-demo` update feed. Never
reuse the paid product's installer identity, updater feed, license files, or
server-copy pipeline.

## demo.13 — matching material colors without surprise darkening

- Selecting a Base Material now selects **From special → that material**, unless
  Base Color LOCK is on. An unlocked selection also starts Depth/Flip/Underglow
  at zero; HSB, Base Strength and Spec Strength remain your explicit settings.
- Color Lab starts/reset at 0% Depth. Enabled with all three effects at zero,
  it preserves the selected color exactly. Deliberately raising Depth still
  adds candy absorption and can make dark colors much darker.
- Existing saved effects are retained on restore. To get the corrected starting
  color in an existing zone, unlock and reselect its Base Material, or reset the
  three Color Lab effects. Lock preserves the color and effects during automatic
  material changes; direct edits still work.
- Manual finish-own and source-only behavior is unchanged. FRACTURE THIS PAINT
  keeps the source-responsive finish-own route when unlocked and honors a lock.
- Cherry Polka matches current main-engine special RGB at 1024/2048; demo
  preview/export verified. See `docs/DEMO_COLOR_PARITY_2026-09-06.md`.

### Historical demo.11 notes

- Color Lab (Depth, Flip, Underglow) is explicitly opt-in and defaults OFF,
  including when old sessions contain the former automatic 65% depth.
- Removed the hidden 80%/50% zone-strength defaults. Restoring a Demo session
  normalizes the two uneditable strength multipliers to 100%; the visible Base
  Strength and deliberate HSB controls remain unchanged.
- Corrected near-black hex parsing (`#010101` must stay RGB 1/1/1).
- 29 picker finishes plus the hidden Fracture shortcut: added Wovencell,
  Molten: Foundry Spatter, Truchet Glass, and Cinder Pulse. Truchet uses the
  existing `ff_truchet_glass` renderer with the owner's Fractured Tessera label.
- The release gate checks all 30 real captures at both native sizes (1024/2048):
  exact solid red, authored finish paint, and special color fields; also PNG/TGA
  encoding. Its report is `demo/color-fidelity-report.json` (build evidence only,
  not part of the packaged runtime).
