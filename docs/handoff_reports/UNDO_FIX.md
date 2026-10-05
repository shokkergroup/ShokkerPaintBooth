# UNDO-FIX (2026-10-04) - every copilot change is undoable (top Undo + per-message Undo), proven in-app

Lane: `js/spb-pro-ai.js` (undo bookkeeping only; routing order untouched), `_easy_claude_work/pw/undo_*.py` (+ `undo_block.js`, `undo_patch.py`, `chrome_up_9725.py`), this doc.
Test server 59879 only, own Chrome CDP 9725. Live app (59876) untouched.

## Root cause (measured)
- An AI entry counted as undoable only when the app's zone undo stack GREW: `entry.undoable = lines && (undoDepth() > undoBefore || layerUndo > 0)` (finishCore + MCP apply).
- That stack is capped: `MAX_ZONE_UNDO = 15` (`paint-booth-2-state-zones.js`; `pushZoneUndo` does push + `shift()` at the cap). After loading the owner's PSD and rebuilding the 8 zones it is already **15/15** (measured), so every AI change left the length at 15 -> `undoable:false` for every entry (pre-fix probe: "make the numbers pink" -> `undoable:false`, depth 15 -> 15).
- Consequences: no "↶ Undo" under the message (it renders only for `undoable`); the studio's top Undo (`spbProAI._undoLast()`) found nothing and fell through to the app's global `undoZoneChange()`, which pops whatever is newest (a manual edit if one came after), keeps region masks as they are now and never puts layer visibility back. "12 of 15" in ROUTER-FIX = the stack after such fall-through pops; whenever it is at the cap the depth test fails.
- The old undo was also inexact even when it fired: one global pop + masks only for `edit`-with-region ops (zones the AI deleted lost their masks), layer undo by popping the global layer stack (8+ shared steps).

## Fix (`js/spb-pro-ai.js`, token `20261004undo`)
- `applyQueue` takes the change's OWN exact before-state when the change is its own undo step (`undoSnapTake`): every zone (the app's `_cloneZoneState` with spatial mask + strength map; region mask packed losslessly by value runs, any typed-array type), zone order, the selected zone, every layer's visibility / opacity / blend; plus the app-history entries the change pushed (`zPushed` / `lPushed`).
- `finishCore` / MCP apply: `entry.undoSnap`, `undoSeal(entry)` (after-state signature; re-sealed by `mergeMaskUndo`, which both repair passes call), `undoable = lines && (snapshot || old depth test)`; `undoTrim()` keeps snapshots for the newest 15 changes (older ones become not-undoable instead of popping the wrong thing).
- `doUndo` -> `undoRestore`: nothing changed since -> the exact before-state comes back (zones, masks, order, selection, layers); something else changed since (a manual edit) -> only the zones / layers THIS change touched go back, later work stays. The app-history entries the change pushed are dropped while still on top. Legacy global-stack path only when no snapshot exists.
- One message = one step (one snapshot per message, repairs merge into it). A complaint-revert, kit Use, offline edit, online turn, MCP call all go through the same path, so each is undoable; undoing a complaint-revert brings back the state it corrected.
- AI `redo` tool: exact redo of the copilot's last Undo first (`redoLast`, only while nothing changed since), else the app's `redoZoneChange` as before.
- Panel: the per-message "↶ Undo" also shows on the newest change when a later answer changed nothing (a question, an advisor list).

## In-app proof: 8/8 (`pw/undo_inapp.py`, results `eval/undo_fix/results_final.jsonl`, log `run_final.log`)
Setup: the owner's `SPB ARCA Chevy PSD.psd` + the 8 zones of `output/job_render_1791086800_23371_a498bdd430c6/zones_payload.json` (rebuilt by `replay_owner.restore_zones`), zone undo stack 15/15 at the start, chat studio open, "Free designer first" ON. Check = the full state right before the change (every zone field via `_cloneZoneState`, FULL hashes of region mask / spatial mask / strength map, zone order, selected zone, every layer's visibility / opacity / blend) vs the state after Undo; diff printed per case.
| # | change | undo from | change made | diff after Undo |
|---|---|---|---|---|
| 1-2 | offline edit "make the numbers pink" | top / message | new zone | 0 / 0 |
| 3-4 | advisor kit: "suggest a finish package for the whole car" -> "Use this kit" (Classic) | top / message | 5 zones in ONE message (7 diffs) | 0 / 0 |
| 5-6 | complaint-revert "You covered up some of the white stripes on the left side..." (after "make the left side pink") | top / message | region mask carved + desc | 0 / 0 (mask hash back) |
| 7-8 | online (offline-first OFF, deepseek-v4.1-flash, 2 calls each) "Refinish the hood in a deep metallic midnight blue" | top / message | new hood zone | 0 / 0 |
Every entry `undoable:true` with a snapshot before Undo, `undone:true` after; the versions strip gained one item per change and dropped it on Undo. The set-up change under the complaints was also undone by the top Undo afterwards. Online spend $0.0026 (whole lane incl. earlier runs ~$0.0075). Page errors: none.
Extra (not in the 8): "hide the sponsors" (4-5 layers hidden) undone exactly from top + message (`results_layers.jsonl`). Before the fix (same setup): "make the numbers pink" -> `undoable:false`, depth 15 -> 15, no per-message Undo.

## Gates
edit_corpus 466/0 · convo 52/52 · tool 15/15 · stack_test 108/108 · selfhelp 162/182 + guards 22/22 (unchanged) · browser (CDP 9725, server 59879): wp12_askfirst 13/13, t259_elem_policy arcachevy25 11/11 · node --check, scan_ctrl 0 control chars, token `spb-pro-ai.js?v=20261004undo`, sync `--manifest _easy_claude_work/sync_mine.json --write` (2 files: spb-pro-ai.js, paint-booth-v2.html) then `--check` no drift.

## Not verified / open
- The AI `redo` tool's new exact path (`redoLast`) was not exercised live (no DeepSeek "redo" turn run); falls back to `redoZoneChange` as before.
- The "something changed since" selective undo (manual edit between the AI change and Undo) is code-path only; an AI `move` (priority) is not re-ordered back in that mode.
- "Undo the whole last change" zdiff fallback (ROUTER-FIX) still marks the old entry undone without a link back; it now only runs when a change's snapshot has expired (more than 15 changes ago).
- Undo History panel: the copilot Undo drops the app-history entry the change pushed (only while it is still on top); the app's Ctrl+Y no longer redoes a copilot Undo.
- Live app (59876) untouched: the owner needs a page reload for `20261004undo`.
