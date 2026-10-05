# Source Paint across all collections — verified hotfix, 2026-09-09

## Scope and release status

**Released 2026-09-09:** owner accepted the staged test and authorized activation. 10.0.3 is live on Cloudflare; its feed hash and objects are verified. The owner-requested 10.0.2 payload/installer withdrawal is complete; both old URLs return 404. Receipts: `_release_evidence/10.0.3/release-complete.json` and `withdraw-10.0.2-receipt.json`.

Owner confirmed the customer 10.0.2 app fails Use Source Paint across most collections outside Foundation/Core, including FRACTURED, SHOKKER and Cultural. The earlier assessment understated the scope. On 2026-09-09 the owner authorized preparing, building and staging **10.0.3** using Claude's release handoff ae079b3c. Progress and final candidate proof belong in `_release_evidence/10.0.3/`; the owner subsequently supplied acceptance and GO, now recorded in the release evidence.

Source of truth: canonical localhost59876 and root→electron-app/server. The two 10.0.2 public download objects were withdrawn at the owner's explicit request; 10.0.3 uses new versioned installer/payload names. The earlier verification below was performed before the version bump.

## Two defects repaired

1. **Color-mode instruction lost in transit.** Monolithic materials use an explicit-mode flag to distinguish a chosen source mode from old inherited defaults. Preview rebuilt zones and dropped that flag. Selected source therefore became finish color for the large monolithic catalog, including materials picked through regular BASE. Both choices could look identical. Both app serializers now make the displayed mode authoritative, including Everything Else and saved projects. Shared server key normalization also recognizes a named mode without relying on the auxiliary flag, covering old clients and camel-case saved records. Preview and Photoshop transports preserve the normalized marker; full Render uses the same normalization. Direct engine-only legacy calls retain their historical behavior.

2. **Some gradient renderers overwrote the source snapshot.** The broader audit initially failed Gradient Directional, Gradient Extended and GRADIENTS even with the correct mode flag. Their in-place paint functions received a view of the original snapshot. `_monolithic_underpaint_from_zone` now gives them a separate buffer. Source mode and Base Strength can restore the intact paint; the helper is shared by car/helmet/suit. No finish function, palette, geometry, spec construction or catalog changed. Source-pixel error235→0; no new M7 claim.

The active dropdown already supported finish mode. An older extracted handler was also brought into parity; it was not the active failure. Five persistence maps now keep the explicit choice marker. Five JS cache tokens changed to spb-base-color-mode-20260909.

## Verification

- **48 collection families /96 actual localhost preview requests, all PASS.** One existing registered finish from every populated SPECIALS_SECTIONS family, plus Foundation, Foundation EFX and ASTRA. Includes all12 FRACTURED families, all13 populated SHOKKER families, all5 Cultural families, FABLE, Color Science, Material World, Fusion Lab and Signal. Empty/dynamic groups are recorded separately, not counted. These are representative family checks, not every individual finish.
- Every source output is **pixel-exact** to the four-color source; source vs own mode spec maps are also **pixel-exact** in all48 final cases. Paint-own mode changes46; the2 Foundation controls intentionally contribute material/spec without new paint.
- **57 focused tests PASS:**45 actual Flask requests over5 modes×3 routing cases×missing/false/true flag, saved camel-case/default boundary,10 actual TGA export pairs spanning every major collection section plus all3 failing gradients, and mutation-isolation regression.
- **15 existing source/pattern tests PASS**, including independent pattern paint/spec controls. Both Node base-mode and pattern-persistence checks PASS. Total72 Python tests across the two suites.
- Full app in a private MCP document: GRADIENTS /grd_oklab_flow source→own changes the1024² preview from9b6fefa355210f54d8372158d96180b356d382b1f77c7310c8bb89751123693b to53571ca4c51118a273416232fb24921eb08d394bbf5c169030e70b66b3514631. Source preview visibly restores the complete colored Chevy livery. The owner's open document was preserved; no Render/deploy or track writes.
- **Nine runtime files synchronized**, JS syntax checked and all five served JS files byte-match root. Canonical server10.0.2-beta, generation5/PID131204.

## Reviewable runtime scope

- `server.py`: shared named-mode normalization and preview passthrough.
- `server_routes/psd_layer_export_routes.py`: preserve normalized marker.
- `shokker_engine_v2.py`: separate renderer input from immutable source snapshot.
- `paint-booth-3-canvas.js`, `paint-booth-5-api-render.js`: displayed mode authoritative.
- `paint-booth-2-state-zones.js`, `js/zones/zone-config-zone-map-controls.js`: persistence.
- `js/zones/zone-base-color-controls.js`: legacy handler parity.
- `paint-booth-v2.html`: five cache tokens.

Root plus corresponding Electron mirrors. Regression files: `tests/test_base_color_mode_transport.py`, `tests/base_color_mode_transport.cjs`.

## Evidence and shipped comparison

`_spec_overlays_v2_work/base_mode_20260909/`: collection_probe.py, catalog-scope.json, collection-results.json, pre-gradient-fix failed results, paired rendered PNGs, transport-export-tests.log, verification-final.json and runtime-scope.json.

The shipped10.0.2 archive was verified against SHA25666cb9589b050a8169b79388a473c9fbd8b1f38942acb3c0cc01e95478d692731 (4,157,085,544 bytes). Its server.py member CRC48A72561 and741147 bytes match the unpacked release runtime, which has zero base_color_explicit references. Five unpacked files match release commit7810813e after line-ending normalization. The defect was present in shipped code; normal Foundation use or successful Render-only testing did not cover the failing preview paths. Earlier Sandbox reassurance must not override the owner's broader reproduced failures.
