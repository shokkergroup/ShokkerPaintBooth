# RENDER-BUDGET 2026-10-04: first live preview fails with "aggregate decoded payload budget exceeded"

Lane: payload builder `paint-booth-5-api-render.js` (buildServerZonesForRender), `server.py` (decoders + budget only),
`_easy_claude_work/pw/budget_*.py`. Own server 59883 + own Chrome 9731 (both stopped); live 59876 and shared 59879 untouched.

## Symptom
With ~10-13 zones limited to PSD layers, the first preview after any layer change errors with
`source_layer_rgb decode failed: preview source_layer_rgb_png: aggregate decoded payload budget exceeded`
(or `source_layer_mask ... aggregate RLE decode budget exceeded`). On a server error the client does NOT schedule
a retry (`!data.success` -> `_finishPreviewRequest('error')`), so the old picture stays up until the next change:
the owner sees "my change didn't happen".

## Root cause (measured, `budget_measure.py` on the captured request bodies)
`server.py` charges every decoded mask / layer image of one request against `SPB_RLE_DECODE_BUDGET_BYTES` = 256 MiB:
float32 RLE masks = 16 MiB each at 2048x2048, layer RGB PNG decoded to RGBA = 16 MiB. Identical layer payloads are only
charged once while they sit in an 8-entry LRU. A cold cache (any layer visibility change bumps `_layerCompositeRevision`,
which is in the cache key) charges everything:

| design (owner ARCA PSD) | unique layer sets | region masks | cold decode | 256 MiB budget |
|---|---|---|---|---|
| 8 zones (job_render_1791086800) | 5 x 32 MiB | 3 x 16 MiB | **208 MiB** | fits |
| 13 zones (after AI turn 1: 4 part-limited black recolours + Numbers) | 5 x 32 MiB | 7 x 16 MiB | **272 MiB** | fails at zone 12's RGB |
| 20 zones (+7 single-layer, part-limited) | 9 x 32 MiB | 14 x 16 MiB | **512 MiB** | fails; 9 sets > LRU 8 so it fails WARM too (cyclic LRU thrash: every entry misses every render) |

Not the cause: the same layer mask being decoded N times (server already deduped identical payloads via the LRU) and
not the JSON size. What the duplicates DID cost was client time: the builder re-ran `toDataURL` on the same 2048 canvas
per zone (Spray Can left/right/hood = 3 x 2.0 MB PNG, 6 of the 8.8 MB of zone JSON).

## Fix
1. `server.py` budget 256 MiB -> **1 GiB** (config + the decoders' literal fallback), error text now carries the numbers
   (`... (X MiB decoded + Y MiB > Z MiB)`). Memory reason, measured on 59883: a cold 20-zone layer-limited render at FULL
   2048 resolution peaks the server at **4.48 GB** working set (decoded payload 512 MiB = ~11%); the 0.5-scale preview
   peaks at 1.96 GB. 1 GiB = 64 planes = ~20 zones that each have their own layer set AND a part limit; still a hard
   ceiling (a hostile 50-zone payload with four full-canvas masks per zone would need ~2.6 GiB and is refused).
2. `server.py` exact per-request dedupe (`_request_source_layer_memo`, on `flask.g`): an identical layer payload is decoded
   and charged once per request whatever the LRU size; LRU 8 -> 16 so 9-16-set designs stop thrashing warm
   (worst case resident 16 x 16 MiB per cache, only for designs that use that many sets). Same arrays as before.
3. `paint-booth-5-api-render.js` per-build memo (`_slBuildMemo`) of the union mask, its RLE and the layer RGB PNG, keyed
   by the exact ordered layer-id list + canvas size; lives only for one synchronous build, so it cannot go stale.
   Payload is byte-identical to before (verified: every zone field equal except the wall-clock revision).
   Cache token `paint-booth-5-api-render.js?v=spb-renderbudget-20261004`.

## Proof (`budget_repro.py before|after --capture`; cold = layer revision bumped, w = warm repeat)
| stage | before: first attempt | after: first attempt | after: trigger -> answer | client build before -> after |
|---|---|---|---|---|
| 8 cold / warm | OK / OK | OK / OK | 4.8 s / 2.9 s | 282-348 -> 164-208 ms |
| 13 cold / warm | **FAIL** (budget) / OK only on a later retry | **OK / OK** | 6.8 s / 3.7 s | 345-541 -> 224-268 ms |
| 20 cold / warm | **FAIL / FAIL** (never renders) | **OK / OK** | 8.0 s / 5.7 s | 549-798 -> 382-435 ms |

Pixels: 13-zone first attempt with the fix = old code's eventually-successful 13-zone preview, **max abs diff 0**
(md5 3be47963a27f both). 8-zone preview identical before/after (md5 281dbfba2458) and vs the owner's
`RENDER_paint.png` mean abs diff 11.08 both runs (harness restore approximations, same as REPLAY_OWNER). 20-zone cold =
warm (md5 958a77949f8d) and shows the 7 new zones. Direct replays of the old-client bodies to the patched server
(`budget_replay.py`, cold): 13 and 20 zones succeed.

Tests: `test_shared_rle_decoder_binds_shape_values_and_aggregate_budget`, `tests/test_layer_system.py -k decode/rle/
source_layer` (13 passed), `test_psd_source_layer_decode_paths_fail_loudly_instead_of_dropping_layer_scope` pass.
The decoders stay self-contained (tests exec them standalone), so the budget code is inline in each.

## Owner step
**Restart the live server** (server.py changed) and reload the page (new JS token). Until then the live app keeps the
256 MiB budget.

## Left open (not in this lane)
- Client: a server error on preview is not retried automatically (`!data.success` path) - fine now for this error, but
  any other transient server error still leaves the old picture up with an error badge.
- Full-resolution 20-zone cold render takes ~15 s on the server (engine time, not the budget).
