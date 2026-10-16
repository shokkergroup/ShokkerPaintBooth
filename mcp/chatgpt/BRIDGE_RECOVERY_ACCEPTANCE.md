> Evidence history: checkpoints below apply to their recorded generations. For current integration status and priorities, use [REPORT.md](REPORT.md) and [the strategy review](STRATEGY_REVIEW_2026-10-09.md).

# Private MCP poll recovery — 2026-10-09

The editor stayed responsive while private59910 stopped polling its MCP queue.
Health returned200; status/chat requests continued. Read-only tool receipts
returned app-not-ready. Native connection off/on did not resume polling.
No paint change was executed during that failure.

The source bridge has no poll timeout, and `running` prevents off/on or periodic
refresh from starting a replacement while a fetch remains pending. The actual
source script reproduces both failures with a controlled stalled transport.
The precise cause of the native stalled request is still unverified.

`bridge_recovery_edits.py` creates an exact private candidate for the shared
`js/spb-mcp-bridge.js`; shared source is unchanged. It limits poll transport to
45seconds, retries after3seconds, cancels abandoned polls on explicit toggle,
and rejects late responses from prior polling generations. A delivered paint
call completes before a replacement poll starts. Its execution and result
posting are not timed out or replayed by this fix.

`node mcp/chatgpt/test_bridge_recovery.cjs` executes the actual original and
candidate scripts. The original stalls; the candidate passes stalled transport
recovery, explicit off/on, late-call rejection, no overlap during a120second
paint handler, toggling during that handler, and superseded-page reclaim.
These are transport/component tests, not native pixel or wake-up acceptance.

Owned59910 restarted from PID126624 to171704 because its private routing now
includes the18th candidate. Served bridge bytes match; health200 and native
reload resumed polling. Reload recovery alone does not prove the watchdog
recovered a native stall. Actual model wake-up, sleep/resume, delivered-call
hangs and extended connection testing remain open.

Before restart, native Save preserved the42-layer/5-zone ARCA baseline in the
private project library. Native Open restored42 layers/5 zones with source verified; fresh paint/spec
receipt `paint-arca-recovery-ready-2026-10-10T00-11-08-727Z.json` passed.
The first capture overlapped import and was rejected by the document guard. No ARCA recolour/Undo acceptance is claimed here.

Claude handoff: this transport contract applies to both subscription helpers.
Review the exact patch and tests together; preserve page ownership and never
use a transport recovery timer to repeat a delivered mutation.

## Filtered chat long-poll — Oct10 03:40

Private logs showed an old document calling /api/mcp/chat repeatedly within milliseconds: the wake predicate saw any newer entry while the output filter hid foreign document/provider entries. The relay candidate now uses the same eligible-entry condition before waking. Real Flask tests assert filtered history actually waits and matching history returns without waiting. Live `verify_live_chat_poll.py` passes on PID165872/59910 (`live-chat-poll-acceptance.json`): two0.2-second empty polls take0.217/0.216s and the matching message returns in0.006s. Synthetic inbox/inflight cleared in finally; no model or paint calls. The editor was reloaded afterward to register its real scope. Root source and59876 untouched. This does not establish all reconnect or replay behavior.
