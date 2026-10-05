# SMALL FOLLOWUPS (2026-10-04) - ROUTER-FIX leftovers: lock-suggestion chip + MCP spb_refinish part/object

Source: `docs/handoff_reports/ROUTER_FIX.md` item 5 and its "not applied" notes.

## 1. Lock suggestion only for instructions (`js/spb-chat-studio.js` `beforeSend()`)
Applied exactly as ROUTER-FIX specified: `_sug = (named layer AND spbProAI.lockWorthy(t)) ? layer : null; syncLock();`. Resetting `_sug` on every send makes the chip vanish after the next message; `lockWorthy` is false for complaints, questions and help asks (and the guard tolerates a missing `spbProAI.lockWorthy`). Cache token `spb-chat-studio-20261004lock`, synced to `electron-app/server/`.

Verified on the TEST server only (59879, own Chrome CDP 9727, `_easy_claude_work/pw/lock_test.py`, shots in `_easy_claude_work/eval/lock_test/`), typing into the real chat input + Enter (beforeSend never runs for `spbProAI.send()`), ARCA PSD offline:
- control (lockWorthy forced true = old behaviour): "You changed the white base to pink and should not have" -> chip shown (so the test can fail)
- same complaint, real behaviour -> NO chip
- "make the White Base layer satin" -> chip "Keep working in the White Base layer? Lock to it"
- next message ("make the left side a little darker") -> chip gone

Test note: `SPB ARCA V7.psd` has no layer literally called "White Base" (its white layer is "White Accent"), so the driver renames that layer in the page only (never saved) so the owner's exact sentences name a real layer.

## 2. MCP `spb_refinish` now exposes `part` and `object` (`mcp/server/tools.json`)
Same parameter text as the in-app `refinish` tool in `js/spb-pro-ai.js`: `part` (limit a COLOUR target to a place; comma lists) and `object` (a named thing holding the colour, e.g. "the yellow on the spray can"). `node _easy_claude_work/mcp_parity_test.js` PASS (21 MAPT tools + 1 extra, 22 in tools.json, no mismatches); JSON loads. The `.mcpb` was NOT rebuilt (owner step): an installed bridge only picks up tools.json from the packaged build.

## Open
- The owner's live page (59876) needs a reload for the new chat-studio token.
- `.mcpb` rebuild (owner step) for the new spb_refinish parameters to reach installed MCP clients.
