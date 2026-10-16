> Evidence history: checkpoints below apply to their recorded generations. For current integration status and priorities, use [REPORT.md](REPORT.md) and [the strategy review](STRATEGY_REVIEW_2026-10-09.md).

# Layered protection acceptance — 2026-10-09

Private localhost59910 only. Shared runtime sources remain read-only; proposed source changes are exact candidate patches under this lane. No API key or billing fallback, production promotion, output export or live-link write occurred.

## Actual native evidence

The disposable `layered-protection-a.ora` has three 512×512 source layers: Body, Numbers and Sponsors. All contain the same navy. It is synthetic artwork, not an iRacing UV template. Native import and baseline Save succeeded. Request: “Make only the Body layer red. Keep the Numbers and Sponsors layers unchanged.” Sponsors was selected, so the explicit Body target must override the active layer.

Offline initially proposed an unauthorized whole-car step. Nothing ran until corrected. Root cause: `compound9` treats a preservation sentence as another command by prepending `make` and inheriting the first colour. The private common parser now retains exact protected layer names; the early Offline route uses that plan before compound fallback. Unknown/duplicate names, contradictory preservation, whole-car targets and unsupported preservation clauses stop with a clarification. This is bounded grammar repair, not general language understanding. Tests execute the actual staged parser, builder, Offline route and report scope.

The corrected native Offline plan showed one Body→Red operation. Run changed 58,096 pixels of the 256×256 preview. The 2,295 opaque number-core pixels and 2,591 opaque sponsor-core pixels were exact; all three saved source-layer records, including their full raster data and settings, were exact. One new zone bound to Body (`psd_0`). AI Undo restored identical PNG bytes, all RGBA pixels and all five original zones. Native Open of the separately saved edited project reproduced its preview exactly.

Real installed Codex, authenticated with ChatGPT, handled the same incoming request through MCP. It read state and preview, made exactly one `spb_do` call with an explicit Body-layer frame and protected Numbers/Sponsors, then read state, check and preview and replied to the current buyer sequence. No other writes. Its red was #D71920; Offline used #C8102E. Both satisfy the named red request. The model test passes the same pixel, saved-layer, exact Undo and native Save/Open comparisons. The session exited successfully and API fallback was disabled. Claude model inference has not been tested here.

The model appropriately qualified preservation because S3 counted 756 changed artwork-edge pixels. Opaque cores and full saved layer records are independently exact. Transparent/antialiased composite edge pixels may change when the background changes; this evidence does not prove that every rendered edge is visually ideal or that edge measurements can be ignored.

## Reporting defect

The first online run's report labelled the Body-scoped change as “whole car,” because `scopeOf` treats a `body` word as whole-car authority even inside a layer name. The private report candidate now gives fully parsed explicit layer targets precedence and names measured layers before broad coverage descriptions. The actual scope test asserts `layers:[Body]`, `whole:false`, protected Numbers/Sponsors. Native rerun and actual MCP check confirm Body-layer wording, `whole_car:false`, zero outside pixels and measured89% preview, while retaining the756px edge measurement. Receipt `paint-layered-report-scope-2026-10-09T22-16-58-151Z.json`, UI/served script versions `layered-report-scope-ui.json/.png`. Coverage remains a measured preview-grid percentage; protected decal checks remain active. The UI also counts five applied field-description lines as five changes despite one zone operation; that wording issue remains open.

Global native Undo History still displayed old actions after project Open, although AI chat/planner controls reset. Do not claim all editor history is isolated from this AI-only acceptance; investigate the source owner's global history reset separately.

## Receipts and reproduction

Evidence directory: `_codex_mcp_work/chatgpt-dev/59910/`. Native projects and original fixture: `_release_evidence/chatgpt-dev/59910/`.

- `layered-pixel-acceptance.json`, `layered-model-pixel-acceptance.json`: independent comparisons.
- `layered-model-probe-2026-10-09T22-10-11-509Z.json`: exact model tool arguments/results, authentication mode and tested candidate manifest.
- `paint-layered-baseline-reopened-2026-10-09T22-04-36-978Z.json`, `paint-layered-body-after-2026-10-09T22-06-19-668Z.json`, `paint-layered-body-undo-2026-10-09T22-07-23-732Z.json`, `paint-layered-after-reopened-2026-10-09T22-07-58-598Z.json`.
- `paint-layered-model-before-2026-10-09T22-09-54-326Z.json`, `paint-layered-model-after-2026-10-09T22-11-09-793Z.json`, `paint-layered-model-undo-2026-10-09T22-13-59-552Z.json`, `paint-layered-model-reopened-2026-10-09T22-14-59-107Z.json`.
- `layered-*-native.png`, `layered-model-*-native.png`: lossless native displayed preview; screenshots `layered-after-ui.png`, `layered-model-after-ui.png`.

Run `node mcp/chatgpt/test_preserved_layers.cjs`, `node mcp/chatgpt/test_preserved_colours.cjs`, `node mcp/chatgpt/test_colour_report.cjs`, then `python mcp/chatgpt/verify_layered_pixels.py` and `python mcp/chatgpt/verify_layered_pixels.py --model`. Verification reads saved actual evidence; it does not manufacture a runtime edit.

`session-probe.cjs --context --edit-acceptance --messages 1 --port 59910 --codex <installed executable>` first reads the live MCP fixture and refuses any other source/layer/baseline state. Only status/context/chat/state/preview/check and `spb_do` are enabled; no export/render/save tools. It is a bounded owner acceptance harness, not a customer background service or a substitute for cold-start/wake-up installation testing.

Still open: native failed-Open/rollback with layered state, all in-flight mutation boundaries, real templates/artwork, full-resolution rendered output, broader customer scenario gate, cold-start/reconnect reliability and Claude inference parity. The 24-hour goal remains active.
