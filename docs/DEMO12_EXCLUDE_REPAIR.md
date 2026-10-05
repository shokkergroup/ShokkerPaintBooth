# Demo 12 — Exclude repair / SPB-93

2026-09-04. Owner requested a working, aligned, resizable Exclude brush on both
SOURCE and LIVE, automatic flat-image scope, and personal testing before reupload.
Only the standalone demo is changed. Paid tool dispatch and finish renderers are
untouched. Publication is held for the owner's acceptance test.

## Reproduced before editing

In isolated Chrome at localhost:59889, the old SOURCE drag only added the sampled
color #444444 to a color-wide exclusion list. There was no spatial brush. A click
at (805,593) placed the marker center near (799.75,539.5), approximately 54px high.
LIVE had no Exclude handler and a drag there did nothing.

## Implementation contract

- `demo/frontend/js/exclude-mask.js`: native-document coordinates, continuous round
  capsule rasterization, RLE mask codec, and flat-import scope normalization.
- `demo/frontend/js/exclude-brush.js`: one shared zone mask viewed through either
  canvas's current DOM rectangle; fixed-position, scale-correct pointer ring.
- Visible size slider/number field, red coverage overlay, Undo/Clear, Shift restore,
  bracket size shortcuts, Ctrl+Z. A stroke commits once on pointer-up. Escape,
  lost capture, pointer cancel, blur, or target changes roll it back.
- Zone-only `spatialMask` (0 untouched / 2 excluded) is sent through existing
  backend `spatial_mask` handling for both preview and export. No PSD pixel writes.
- Flat TGA/PNG/JPEG has a checked, disabled automatic layer indicator. Its request
  bypasses PSD layer restriction masks, including obsolete IDs from a prior PSD.
  Missing real PSD restrictions still fail closed, not silently broadened.
- Same-document reload preserves exclusions. New/changed document, fallback
  starter, or mismatched saved mask dimensions clears stale spatial coordinates.
- Existing color-wide exclusions from old sessions remain removable in the UI.

## Evidence

Real browser drags, not injected JavaScript events:

| Case | Result |
| --- | --- |
| SOURCE fit, non-square 1024x512 TGA | End pointer (740,545), ring center (740,545); both overlay rectangles exactly match canvases |
| LIVE fit | End pointer (1540,675), ring center (1540,675); mask grew 24,027 to 44,713 pixels |
| LIVE 120% independent zoom | End pointer (1400,470), ring center (1400,470); Undo restored 44,713 pixels |
| SOURCE wheel zoom 120% | End pointer (850,490), ring center (850,490) |
| Packaged demo.12 starter PSD | Loaded 2048x2048 ARCA, five zones; 160px brush ring at (870,585), width 42.109375 CSS px (160 * 539 / 2048) |
| Packaged same-file reopen | 81,327 excluded pixels preserved |
| Packaged PSD BASE01 restriction → flat TGA | Automatically checked flat scope, no missing PSD restriction, old spatial mask cleared |
| Packaged 160px brush on LIVE TGA | Ring center (1300,520), width 84.21875 CSS px (160 * 539 / 1024) |

Automated gates cover geometry at eight fit/zoom/aspect/origin combinations;
continuous strokes, radius, edge clipping, codec roundtrip, wrong-size masks;
real event-handler transaction/Shift/Undo/cancellation/zone-switch/size behavior
in an isolated DOM test harness; and backend exact pixels through preview at
1x/0.5x/0.25x plus full-resolution TGA export. Excluded paint remains original,
excluded spec remains neutral (0,128,0), same-colored unexcluded paint changes,
and exclusions release pixels to a later Remaining zone.

Full regression command:

Final result: **116 passed**. The additional unchanged-color release gate
(`python -m demo.verify_color_fidelity`) passed **180 real-capture checks** across
all 30 allowed materials at 1024 and 2048, with maximum RGB error **0**. Exact red
also survived PNG/TGA encoding. All **999** packaged inventory files matched
their SHA256 entries and the packaged-tree allowlist passed.

```powershell
python -m pytest tests/test_shokk_demo_frontend.py tests/test_shokk_demo_backend.py tests/test_shokk_demo_exclude.py tests/test_shokk_demo_electron.py tests/test_shokk_demo_branding_recipe.py tests/test_shokk_demo_stage.py tests/test_shokk_demo_thumbnails.py -q --disable-warnings
```

## Packaging / handoff

Version: `1.0.0-demo.12`, build ID `shokk-demo-exclude-20260904a`.
New modules are explicitly included in `demo/build_demo_stage.py`'s allowlist.
Stage with `node stage.js` from `electron-demo`, then package with
`node node_modules/electron-builder/cli.js --win --x64 --publish never`.
The first compression pass was canceled so the changed-document safeguard could
be included. Do not use interim artifacts. Final proof/hashes are recorded in
`demo/release-demo12-proof.json` after successful build verification.

SPB-93 Linear comment could not be posted: connector requires reauthentication.
This document and the Living Wiki preserve the local issue handoff. Reupload to
the existing itch.io listing only after owner test approval; preserve owner copy.
