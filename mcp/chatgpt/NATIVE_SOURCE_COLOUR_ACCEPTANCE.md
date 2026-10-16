# Native source-layer colour — private acceptance, 2026-10-10

**PASS for the native Offline Helper journey on private59910.** The customer sentence was: “Make only the red areas in car_pattern_001.tga #b39a58. Keep the green and blue unchanged.” Send → one reviewed step → Run → Save → chat Undo → Save now reaches SPB's native Color Replace operation on the exact layer.

## Evidence

All receipts are under `_codex_mcp_work/chatgpt-dev/59910/`.

- `native-helper-replace-saved.json`: only psd_23 changed; 2,331,152 full-resolution source pixels match the native kernel exactly (max error0). All other layer rasters and non-pixel metadata are preserved. Chat Undo restores all42 RGBA buffers exactly. Showing the originally hidden pattern was deliberate test preparation.
- `helper-native-colour-composite.json`: independent full source-stack compositing with the actual LANCZOS preview filter matches every1,048,576 preview pixel within2 channel values. The older flattened-zone result differs by>10 at13,524 qualified artwork-edge pixels where this result matches within2.
- `native-helper-colour-recovery.json`:42 layer metadata records and five zones unchanged; spec preview unchanged; every returned image and the lossless native preview PNG restored exactly by chat Undo.
- Native receipts: `paint-helper-native-colour-before-2026-10-10T06-11-17-177Z.json`, `paint-helper-native-colour-after-2026-10-10T06-12-06-587Z.json`, `paint-helper-native-colour-undo-2026-10-10T06-13-33-923Z.json`.
- Saved projects: `ARCA native source colour after - private59910.spbproj` and `ARCA native source colour Undo - private59910.spbproj`, in `_release_evidence/chatgpt-dev/59910/projects/`. Source hashes are in the saved-raster receipt.

## What changed

Literal imported filenames can supply exact layer scope without requiring the word “layer”; repeated names still ask. A trailing colour-preservation sentence remains a constraint rather than a second recolour. Both ordinary Run and planner-card routes can reach the native adapter, with typed-request/card agreement and selection/spec guards.

Source colours must come from the exact layer's committed pixels. The real flattened palette included both pattern red #ff0000 and foreground-art red #aa1f2d. Even passing a raw palette to the zone compiler was insufficient because its live edge fitter reads the flattened image again. The adapter therefore reuses the canonical colour vocabulary/resolver directly on the raw palette, then uses native Color Replace with tolerance40. Missing/busy/wrong-ID/ambiguous/excluded targets refuse instead of silently falling back.

Native target preparation, selection clipping, pixel kernel and commit/history remain the existing tool code. Chat Undo snapshots retain immutable layer image references and respect later-edit ownership. MCP `spb_edit_layer` exposes source_colour and replace_tolerance through the same adapter.

## Limits and next work

### Actual subscription measurement successor — 2026-10-10 03:03 EDT

Actual ChatGPT subscription inference now receives an automatic measurement for native source replacement. It selected exact red with tolerance0, applied one edit to psd_23, inspected the result and disclosed the preview's estimated256-pixel protected-artwork difference. It did not claim perfect preservation or save/export. `online-source-report-acceptance.json` and `verify_online_source_report.py` verify the model/tool exchange and native Undo:42 metadata records/zones, returned previews, native lossless preview and the inspected source thumbnail restore exactly. This successor does not independently prove full-raster equality for tolerance0.

The same receipt preserves a report defect: `edit_layer` did not supply optional `buyer_said`; the reporter skipped its exact native layer queue and described hood/roof/sides despite an empty scope. Candidate now resolves that queue's exact current layer ID, names the layer, and uses neutral preview wording when no scope is known. A large change confined to an explicitly targeted native layer is not an unasked whole-car edit; an injected outside-layer spill still fails the existing gate. Actual S3 regression tests cover the original lost scope, candidate layer label, unknown target and spill rejection. P7/owner-promotion checks pass. This scope correction still needs a fresh native/model run; the existing256-pixel warning is retained, not excused by changing thresholds.

### PASS: native common reporting — 2026-10-10 02:46 EDT

Fresh editor first edit/repeated request/Undo now passes. The first exact Base Paint overlay returns an actual automatic report:41,971 changed cells on the256×256 preview grid (64%), exact target psd_0, zero measured outside/decal/spec changes. This is sampled preview evidence, not full-raster proof. The repeated request leaves all42 layer records, zones and all returned preview/spec images unchanged. Chat and builder both say no change; the builder Undo button is disabled. Undo of the real first edit restores42 records/zones/all returned images exactly.

Reproduce with `python mcp/chatgpt/verify_native_outcomes.py`; result `native-outcomes-acceptance.json`. Screenshot `outcome-noop-builder-pass.png`, negative control preserved above. Loaded versions are recorded: pro-ai d0ee9d942ee8, builder afe2591cd0e9, native-colour7ccf6e878887. The subsequent report-ID filtering refinement passed component tests and was not loaded for this native run. Exact builder Undo targeting also has function-level regression proof; this native restoration used the first entry's chat Undo. Automatic source-colour replacement measurement, actual model reporting, complete schemes and shared/package adoption remain open.

### Native reporting follow-up — 2026-10-10 02:43 EDT

Native Offline completion now correctly says “applied colour” and a repeated request says “no colour change was made,” with no second chat change/Undo. This test exposed a remaining builder contradiction: “Not done yet” plus a builder Undo button that called the latest editable entry. Preserved negative control: `outcome-noop-builder-negative.txt/.png`. The real first edit was undone using its own chat button; `outcome-noop-first-native.json` verifies all42 layer metadata records, zones and all returned preview/spec images restored exactly.

Successor candidate carries the no-change receipt into the builder, labels it “No change made,” disables/guards its Undo, and binds other builder Undo actions to their exact entry ID instead of `undoLast`. Report lookup also filters that entry ID, so a late unrelated report cannot overwrite it. Actual builder and Undo-function regression tests pass; successor native acceptance is in progress.

The missing-render-check investigation found a concrete shared ordering defect: `applyQueue` ran layer edits before capturing `zdiff.s3b`. Layer mutation invalidates the preview, so no before-shot was retained. The candidate captures before dispatching either layer or zone changes. `test_layer_report_capture.cjs` runs the actual queue prefix, reproduces the original missing shot, verifies layer/mixed/zone ordering, and retains refusal of an unsynced baseline. Existing P7 source-history safeguards pass. Native rendered measurement is still pending; no thresholds or pixel algorithms were relaxed.

### Outcome reporting successor — 2026-10-10 02:34 EDT

Private candidate now carries `layer_colour_outcomes` through the common layer executor and MCP reply. Offline completion uses those same applied/unchanged/failed receipts instead of leaving a pre-execution “Ready to replace” promise on the completed card. Colour-only no-ops have an empty applied list and consume no layer history; the actual Offline and MCP dispatcher tests cover both paths. Native kernel tests cover successful replacement and no-match recovery. No source-pixel algorithm changed.

Native commit evidence explicitly has `render_verified:false`. The kernel count precedes selection clipping and is exposed only as `matched_pixels_before_selection`, never “changed pixels.” This does **not** resolve the separate rendered-report `not_measured` gap. Four focused suites pass (native layer colour, native replacement, region preservation, builder receipt). Fresh browser/actual model acceptance of this reporting successor remains pending; the earlier full-raster and model proofs above apply to the edit operation, not this new UI wording. Shared/package adoption remains pending.

**Actual ChatGPT successor02:23:** real ChatGPT-authenticated session (no API fallback) inspected the pattern and used spb_edit_layer with source_colour #ff0000, colour #b39a58, tolerance40, exact psd_23. It inspected and replied in SPB. `online-source-colour.json` and `verify_online_source_colour.py` prove all42 saved online layer payloads and lossless preview PNGs equal the independently proven native result, both after the edit and after customer-facing chat Undo. Five zones/spec/metadata remain unchanged. Probe: `context-session-probe-2026-10-10T06-18-28-098Z.json`; projects: `ARCA ChatGPT source colour after - private59910.spbproj` and `ARCA ChatGPT source colour Undo - private59910.spbproj` in the private projects directory. The model did not automatically undo its result.

The app returned not_measured for the automatic rendered report; the model disclosed that limitation. Independent saved-raster and preview comparisons supply the acceptance proof. Common automatic measurement remains open. The bounded test listener exited normally; this does not prove persistent-session lifecycle behavior.

This is one actual ARCA workflow with normal source-over layers. MCP frame routing, broader scheme conversations and hue/shade/finish operations, Claude inference parity, other blend modes/templates, full render/export and shared/package delivery remain open. No proof of UV island geometry is implied.

The current native message still says “Ready to replace” after Run; its change details and Done/Undo state are correct, but that wording needs polish. The source-layer inspection tool returns a512px thumbnail; do not use it to claim full-raster equality. Full-raster proof above comes from native saved projects.

Earlier failed native attempts and exact recovery remain in `helper-replace-routing-negative-control.json`, `helper-replace-card-undo.json` and the associated receipts. Planner preemption was an incomplete early explanation; real palette and edge-fit dependencies were the decisive blockers.
