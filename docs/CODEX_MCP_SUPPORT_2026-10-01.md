# Codex subscription MCP support — 2026-10-01

Owner authorized the Claude handoff: add OpenAI assistant access and model choice to the existing AI mode. The implemented route is local Codex acting as SPB's MCP client. The buyer chats in Codex, signs in with ChatGPT, and chooses an account-supported model there. SPB does not access ChatGPT credentials or substitute them for API keys.

## October 2 connection recheck

The pasted handoff is already implemented in this workspace. Official MCP, authentication and model-selection pages were fetched again on October 2 and still support the local Codex route. The buyer selects the model in Codex, rather than an SPB subscription model dropdown; setup preserves their current model and approval settings. Ordinary ChatGPT web chat is not connected by this installer.

- Hardened the dedicated setup module so reconnecting after a buyer removes the SPB entry creates a fresh backup without overwriting their first backup. Six isolated setup/security tests pass, including that reconnect and model-preservation regression. The real JS handler contract and prepared composer-cleanup success/error checks also pass.
- Synced only the owned setup module and buyer README. No shared Claude AI files, finish definitions, catalogs, live paints or persistent buyer Codex settings were changed. Buyer README now discloses the known spec-only and disabled-composer failures instead of presenting keep-colours acceptance as established.
- The current global runtime check examined 16,367 targets and found drift in Claude's active `js/spb-pro-advisor.js`, `js/spb-pro-rank.js` and `scripts/runtime-sync-manifest.json`. Those files were preserved. Earlier zero-drift results below are historical, not a current packaging pass.
- The existing disposable-app smoke and actual Codex image test below remain historical evidence. No new live-app test or server restart was performed for this setup-only correction. Both shared acceptance failures below and the clean-profile/Electron acceptance remain release blockers.

## Delivered

- AI bridge wording covers Claude and Codex. Connect Codex sits beside Install in Claude Desktop; setup displays the actual server/Node paths and app port.
- Setup appends only a new SPB MCP entry after explicit in-panel confirmation, with startup timeout 20 and tool timeout 200 seconds. It backs up an existing config, validates TOML, preserves other settings and model choice, and refuses to replace an existing SPB entry or a concurrently changed config. Uses CODEX_HOME when set.
- MCP server and schemas are included in the runtime sync manifest. Electron's existing resources/server packaging consequently includes resources/server/mcp/server/index.js, tools.json, README and the rebuilt Claude bundle. Node detection uses the actual executable; no unverified Electron-as-Node fallback.
- apply_scheme warms the same car map used by status before building zones.
- External calls hold an exclusive page lock through apply/render/preview, plus a two-minute editing lease. The in-app send/ask and picture-design entry points require explicit takeover while the external assistant owns editing; active calls cannot be taken over. Internal finish/repair holds its lease during asynchronous work.
- edit_zone accepts stable zone_id, unique zone_name, or index with optional expect_name. State exposes stable IDs. Target/guard fields are excluded from zone settings.
- Disable fails queued AND already-delivered pending HTTP calls immediately, and late results are rejected. Page-side queued writes check bridge state before applying. A change already committed is retained and remains undoable; disable cannot retroactively erase an applied edit.
- Local address checks reinforce the existing origin/token checks. No remote transport/tunnel added; no finish/catalog changes.

## Verification

- `python tests/test_codex_mcp_setup.py`: 5 isolated checks pass (preservation/idempotence/backup, collision and invalid config refusal, apostrophe paths/Node detection, origin/token/confirmation, disable of a delivered call and late-result rejection). All config writes use a temporary test profile.
- `node tests/codex_mcp_client_contract.cjs`: real page handlers pass schema, stale target, lazy car warm-up, overlapping calls and takeover checks. Schemas regenerated using `--tools`, from the actual app handlers and real Zone SCHEMA in a VM without a live-paint change. Claude bundle rebuilt with `python scripts/build_mcpb.py`.
- Syntax checks pass for all changed JS and Python runtime modules.
- `node mcp/test/client.js read`: live ARCA status and car map pass; preview returns two MCP image blocks (paint and spec). Read mode never writes paint. Smoke now fails nonzero on tool errors; its spec path uses base::f_chrome with source color.
- Actual installed Codex CLI 0.124.0, with a per-run MCP config override and ChatGPT authentication, successfully called status and preview and described both received images. Evidence: `_codex_mcp_work/codex-image-proof.txt`. Its default desktop model was incompatible with this old CLI; a per-run compatible gpt-5.5 test succeeded. No persistent user settings/model were changed. Buyers should choose supported models or update their client.
- Browser render verified in an isolated localhost59877 setup page: neutral toggle, adjacent Connect Codex button, exact config and model-selection guidance. Native confirmation dialogs interrupted browser automation; replaced with explicit inline Confirm add/Cancel. Backend confirmed-install behavior is tested independently.
- Owned 13 runtime assets synchronized with SHA-256 verification using `_codex_mcp_work/runtime-manifest.json`. Final global `node scripts/sync-runtime-copies.js --check` passed: all 4,161 runtime pairs checked, no drift. Earlier temporary Pro-design drift converged through Claude's own lane.

## Remaining acceptance and activation

**2026-10-02 acceptance update: integration is implemented, but not release-ready.** An isolated real SPB server on 59881, using its own pairing directory and Codex test profile, loaded `SPB ARCA V7.psd`. The supplied smoke client passed status, car map, recipes, full scheme, preview, zones and Undo; only its evidence destination was redirected into `_codex_mcp_work/acceptance/smoke-output/`. A Pepsi retro-band scheme also applied successfully straight after status/recipes, without the old extra car-map workaround. Six elements painted; the spoiler was correctly skipped because it had no body paint pixels.

Two acceptance failures are now reproduced (details and evidence in `_codex_mcp_work/acceptance/REVIEW.md`):

- **Spec-only after repaint restores original source paint.** Adding hood chrome with `color:"source"` after the Pepsi scheme restored the original green hood. The actual returned paint preview changed 32,311 pixels (20,166 by more than 20/255). Undo restored the prior paint and spec previews exactly. This is a shared zone-composition issue, not an OpenAI authentication issue; the keep-colors claim is not yet satisfied.
- **Completed MCP writes leave the composer disabled at Thinking.** `mcpCall` clears `_busy` after the last UI render. A narrow, tested cleanup patch is prepared at `_codex_mcp_work/acceptance/mcp-busy-cleanup.patch`; it has not been merged into Claude's actively claimed `js/spb-pro-ai.js`.

Current checks: five Python setup/security tests and the JS client contract pass; full runtime sync reports 4,172 pairs with no drift. The real setup UI completed its inline-confirm flow into an isolated test config and preserved model selection; screenshot `_codex_mcp_work/acceptance/codex-setup.jpg`. Historical image-model proof below remains valid. No owner live app/server was restarted or painted.

The already-open owner page/server still uses previously loaded JS/routes until restart/reload. Do not restart during Claude's active design session. After saving the paint and finishing that session: restart SPB, reload its page, then use Connect Codex.

The clean Windows profile / ChatGPT Plus-only full sequence, separately in Electron and browser, remains unverified. The disposable browser test above now proves a failure in the hood spec-only step and an exact preview restoration by Undo; it must pass after repair before shipping. These measurements use returned 768px paint and 512px spec JPEG previews, not native 2048px exports. No API key was needed for the earlier ChatGPT-authenticated Codex image probe.

The editing lease is page-local and distinguishes external assistants from the in-app copilot. It does not assign separate leases to Claude versus Codex or coordinate manual edits across multiple concurrently polling SPB pages. Use one SPB page for the external session; stable-ID/expected-name guards protect stale targets.

Official sources fetched October 1: [MCP](https://learn.chatgpt.com/docs/extend/mcp), [authentication](https://learn.chatgpt.com/docs/auth), [models](https://learn.chatgpt.com/docs/models).
