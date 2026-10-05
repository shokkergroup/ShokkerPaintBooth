# Actual SPB ChatGPT MCP sprint — final handoff

Verified handoff: 2026-10-05 05:00:40 UTC. Owner deadline: October 5 at 04:57:58 UTC / 12:57:58 AM America/New_York. Scoped implementation and practical app testing are finished. The ten-minute recovery heartbeat was paused after the deadline while completing this handoff; unrelated automations were not resumed. Claude owns the offline helper.

MCP access works. This work used the built-in SPB MCP connector, real browser controls and existing app controllers, plus actual production Node MCP contracts against a live private SPB instance. Fixture originals and owner documents were preserved. No DeepSeek/OpenRouter model calls were made. Root orchestrated up to three Luna workers for implementation, independent review and acceptance support.

## The biggest buyer-facing wins

1. **Change the requested paint region reliably.** The old named-pink RAM material export changed27195 pixels outside the visible pink family; the accepted guard now has zero visible-family spill. ARCA red satin has zero changes outside the accepted red/exclusion mask. The mask intersects existing part, spatial, layer and exclusion restrictions, and checks source identity before changes. Missing, stale and ambiguous inputs fail before mutation.
2. **Recolour without flattening the design.** Actual ARCA red-to-blue hue adjustment kept its fine tiled detail, numbers and sponsors.1354343 full-resolution paint pixels changed, zero outside the accepted mask, with original shade/detail retained within1 RGB quantization step. All five material files stayed byte-identical. A later same-zone pearl/roughness/clearcoat refinement retained both blue paint files exactly.
3. **Finish-only requests leave the artwork intact.** RAM pink pearl, FormulaIR04 white satin-pearl/sparkle and GT3 neon-orange metallic preserved original diffuse RGB. Formula sparkle affects only metallic, at maximum5/255, while Rough/Clearcoat stay exact. GT3 changes923167 Metal/Rough pixels with zero material changes outside its actual944781-pixel mask; paint files are byte-identical.
4. **Save and Undo are dependable on the tested workflows.** Stable zone render seed identities stop a new roof zone from changing unrelated roughness. Saved Chevy, PRO4, Formula, RAM, ARCA and GT3 projects regenerate all seven wanted TGA files byte-for-byte after a private backend restart. Current-document Undo restores the checked states exactly. Current28-tool ARCA-to-GT3 switching refuses older Undo history and leaves the new car's paint/spec/source/layers/zones exact.
5. **Opening a file from chat now works visibly.** The first route repair handles layered and flat files; the follow-up stacking repair keeps the canonical picker above Chat Studio. Actual foreground click/fill, Cancel, TGA import and PSD import passed. The ARCA PSD retains all13 editable layers and exact raster buffers.
6. **The bridge gives useful, truthful answers.** Exact layer selection, source/async completion guards, truthful idle status, malformed-frame recovery and document-bound Undo were repaired in this lane. New initialization guidance explains connected number-fill seeds, texture-preserving hue edits and finish-only refinement. An exact palette label boundary is now supported: the GT3's reported neon orange #ff3600 is classified red internally; the exact-name fallback works without changing shared classifier thresholds or offline routing.
7. **MCP packaging agrees with the current server.** Both source MCPB archives now contain the same current index/tools payloads and28 manifest tools. The builder includes Claude's existing Encyclopedia tool instead of silently omitting it. This lane preserved that tool, rather than authoring it. Eight fault/guard cases and independent review checked promotion rollback, foreign edits, corrupt backups and post-replace read failures.

## Actual car and file acceptance

| Fixture | Useful work exercised | Scope / integrity proof | Persistence |
| --- | --- | --- | --- |
| Chevy truck PSD,11 layers | Red chrome roof |118593 full paint/Metal/Rough changes; zero outside actual roof mask; source and11 raster buffers exact; Undo exact | Backend cold, all7 exports exact |
| ARCA PSD,13 layers | Red-only satin; same-zone blue hue; pearl refinement; named layer opacity |1354343 scoped changes; zero spill; original13 raster buffers exact; blue refinement paint bytes exact; current28 Numbers80 changes only that opacity and Undo restores all state | Backend cold blue satin, all7 exact; refined pearl separately saved |
| RAM PSD,10 layers | Pink-only pearl; duplicate/mute/reorder; Undo |1331282 material changes, zero outside visible pink; paint/source/all10 layers exact | Backend cold, all7 exact |
| Chilis Next Gen TGA | Matte black spec; connected77 numeral fills blue |68993 full diffuse changes inside accepted numeral mask, zero outside; loose selections rejected/undone | Saved/fresh browser, all7 exact; same backend |
| PRO4 TGA | Taught connected gold stripes; same-zone material refinement |102920 full diffuse changes inside actual two-stripe mask, zero outside | Backend cold, all7 exact, including legacy seed migration |
| FormulaIR04 TGA | White satin pearl + fine M-only sparkle; stack clear/mute/Undo | Original full diffuse RGB exact;2729432 sparkle Metal changes, max5; Rough/Clearcoat exact vs satin reference;605333 conservative dark-source pixels retain baseline material | Backend cold, all7 exact |
| Mustang GT3 TGA | Exact reported neon-orange metallic; Save/Undo/car switch |923167 Metal/Rough changes, zero outside mask; original diffuse RGB and paint files exact; Undo all7 original exports exact | Backend cold, all7 wanted exports exact; mask/seed1 persist |

These are seven distinct sampled assets: three PSDs and four TGAs. The final nine original/private-copy hash records all match their original SHA256 values, including two path-preserving duplicate copies. This covers varied real files, not every iRacing car type.

## Source installation and practical limits

- Owned source fixes are installed in Root and `electron-app/server/` through independently based, guarded changes with exact before backups and reverse-hunk evidence. Shared AI/canvas/finish bytes were preserved. The new native control metadata and guide are source-installed as well.
- Both MCPB archives are rebuilt and match. No installer was built or launched, and Root did not restart or reload the owner app. Concurrent owner PID changed outside this lane; the final private backend restart preserved the then-current owner706268. Private backend59931 is425684; proxy59930 remains868244.
- Current Python native MCP process caches its startup inspector. The accepted read-only pointerReachable/occludedBy helper was loaded only into isolated acceptance sessions; its source version activates on a new connector process. Main app frontend source changes require a load/reload to activate; owner-window activation was not inspected.
- The final independent review confirms both MCPBs and the builder match their accepted pins, both archives contain 28 unique manifest tools and 22 schemas, and the native controls source/guide and Chat picker CSS match their installation receipts. Exact-label and family-mask guards remain present in both trees. Claude's current Root/mirror AI, edit, zone files, HTML tokens and catalogue lookup data differ. This lane did not normalize his files. Complete installer/runtime parity remains a coordination task; no whole-tree parity claim is made. The reviewer finished before the last car-switch case; Root separately verified that case against its actual before/after receipt.
- All visual acceptance is actual UV paint, material maps and exported pixels. No3D car-view or in-game appearance acceptance was performed. A flat TGA color selection cannot distinguish same-color body and logo pixels without a taught region; tested finish-only cases preserve paint RGB everywhere. Unknown car-part maps are reported as missing rather than invented.
- RAM's accepted contract uses the **visible composite**.40 underlying BASE red/purple pixels appear pink in the visible composite; it is not a strict BASE-only family claim.
- A `second_base` metallic overlay experiment tinted ARCA paint by the documented overlay-color behavior. It was rejected as a paint-preserving refinement and undone. Use the accepted finish/spec-shift/spec-pattern paths for shine-only changes.
- Missing lookup files in the frozen private harness were restored read-only from active source. That repaired test setup and is not credited as an app feature fix.
- Required SPB-93 Linear posting remains blocked by connector reauthentication. Compact local evidence and Wiki are updated; no external post was sent.

## Reviewable outputs and evidence

Private projects and car exports: `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum/_release_evidence/spb_mcp10h_recovery22/output`. Originals were never exported over. Saved projects include the blue textured satin/pearl ARCA, pink-only pearl RAM, GT3 neon-orange metallic, Formula white satin-pearl/sparkle, Chevy roof and PRO4 stripes.

The evidence root is `C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum/_easy_claude_work/spb_mcp10h_recovery22`. Key executable proofs/receipts:

- `gt3-neon-orange-metallic-full-proof-0459.json`, `gt3-undo-seven-proof-0505.json`, `gt3-backend-cold-seven-proof-0439.json`.
- `arca-family-mask-v3-full-output-proof-0334.json`, `arca-hue-blue-full-output-proof-0337.json`, `arca-blue-pearl-refinement-full-output-proof-0351.json`.
- `ram-family-mask-v3-backend-cold-seven-proof-0347.json`, `arca-family-mask-v3-backend-cold-seven-proof-0347.json`, `formula-full-output-proof-0300.json`.
- `current28-native-numbers-opacity80-proof-0446.json`, `current28-native-numbers-undo-proof-0446.json`, `current28-cross-document-undo-proof-0452.json`.
- `chat-file-picker-active-runtime-20261005/native-acceptance.json`, `picker-native-PSD-direct-import-0442.json`, `picker-native-PSD-layer-pixels-exact-0443.json`.
- `safety/named-family-mask-v3/source-promotion-v8/live-install-receipt.json`, `safety/exact-reported-colour-promotion-20261005/promotion-execution-20261005T043428Z.json`.
- `safety/mcpb-builder-repair-v3/execution-receipt-v3.json`, `safety/mcpb-builder-repair-v3/post-install-verification.json`.
- `fixture-originals-and-copies-final-0447.json`, `RECOVERY_STATE_FINAL_20261005.json`.

Earlier sequential checkpoint prose is preserved privately in `handoff-report-before-final-20261005.md`. Evidence filename suffixes are labels; each receipt's UTC timestamp is authoritative. The active baked-picker loader contract passed after the final source/cache-token changes.
