# Shokker Paint Booth for Claude and Codex (MCP)

Design iRacing paints by talking to Claude, **using your own Claude Pro / Max plan: no API key, no extra cost**.
Claude drives Shokker Paint Booth through a local MCP server: it reads your car's named parts, lays out liveries on them, changes only the spec (shine / metal / roughness) when you ask,
searches the 4,800-finish catalogue, and looks at the live preview to check its own work. Every change shows up in the Shokker AI panel with an Undo button.

## Claude setup (once)
1. In Shokker Paint Booth (Pro mode) open the **AI panel** → ⚙ settings → switch on **"Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth"**.
2. Connect Claude:
   * **Claude Desktop (easiest):** Settings → Extensions → Advanced settings → **Install Extension…** → choose `shokker-paint-booth.mcpb` from this folder. (Claude Desktop ships its own Node.js; nothing to install.)
   * **Claude Desktop (manual):** add this to `claude_desktop_config.json` and restart Claude:
     ```json
     { "mcpServers": { "shokker-paint-booth": { "command": "node", "args": ["<this folder>/server/index.js"] } } }
     ```
   * **Claude Code:** `claude mcp add shokker-paint-booth -- node "<this folder>/server/index.js"`
3. Keep Shokker Paint Booth open, then ask Claude: *"Using Shokker Paint Booth, give me an old-school Pepsi look with chrome trim over a flat finish."*

If Shokker runs on another port set `SPB_PORT` (the extension has a setting for it).

## ChatGPT / Codex setup (once)
1. Install Codex and Node.js on this PC. Sign into Codex with **ChatGPT** to use your eligible plan; your subscription limits apply. Keep SPB open in Pro mode (an Electron window or localhost browser tab works).
2. Open SPB's AI panel → settings → **Connect ChatGPT / Codex**. Review the exact connection and click **Add SPB to Codex settings**. Setup appends only SPB's entry, preserves other settings, backs up an existing file, and refuses to overwrite an existing SPB entry. Restart Codex and switch on the AI bridge.
3. Choose your model **in Codex**: its model picker beneath the composer, or `/model` in the CLI. Then ask: *"Using Shokker Paint Booth, give my car an old-school Pepsi look with chrome trim over a flat finish."* SPB uses the selected Codex model; model availability depends on your account and client.

You type in Codex; the changes and Undo buttons appear live in SPB. Your ChatGPT login is held by Codex. SPB does not read your login or turn your ChatGPT plan into an OpenRouter API key. This connects local Codex, rather than ordinary ChatGPT web chat.

**Manual connection:** use the exact config displayed by SPB in `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`). The installed path is under `resources/server/mcp/server/index.js`, not `resources/mcp`. Setup detects the actual path and Node executable. Example:

```toml
[mcp_servers.shokker-paint-booth]
command = "node"
args = ["<SPB mcp folder>/server/index.js"]
startup_timeout_sec = 20
tool_timeout_sec = 200

[mcp_servers.shokker-paint-booth.env]
SPB_PORT = "59876"
```

The CLI equivalent is `codex mcp add shokker-paint-booth --env SPB_PORT=59876 -- node "<SPB mcp folder>/server/index.js"`. **After that command, add `tool_timeout_sec = 200` inside this server's config block**: the default 60 seconds is too short for full schemes. The SPB setup button sets it for you. Preserve existing settings and approval preferences; setup never forces automatic tool approval.

**Current acceptance limitation:** after an assistant repaints the car, adding a new hood zone with `color:"source"` can restore the original hood paint instead of preserving the new design. Keep-colours spec-only overlays are not release-qualified yet. Check the paint and spec previews; use `spb_undo` if the paint changes. Completed MCP calls can also leave the in-app composer disabled until its idle-state repair is merged. See `docs/CODEX_MCP_SUPPORT_2026-10-01.md` for the measured failures and remaining acceptance checks.

While an external assistant owns editing, the in-app chat asks you to **Take over in SPB** in bridge settings. Takeover waits for an active call to finish; otherwise ownership expires two minutes after the last call. Assistants should edit by stable `zone_id`, unique `zone_name`, or an index plus `expect_name` to reject a stale target.

Official OpenAI documentation: [MCP setup](https://learn.chatgpt.com/docs/extend/mcp), [ChatGPT authentication](https://learn.chatgpt.com/docs/auth), [model selection](https://learn.chatgpt.com/docs/models).

## What your assistant can do (tools)
`spb_status` (what car / which parts are known) · `spb_request_parts` (asks you to show the parts once) · `spb_design_recipes` + `spb_apply_scheme` (whole liveries on exact parts) ·
`spb_add_zone` / `spb_edit_zone` / `spb_edit_layer` · `spb_preview` (live preview + spec map + parts map images) · `spb_get_zones` · `spb_undo` ·
`spb_find_finishes` / `spb_finish_details` / `spb_browse_catalog` / `spb_find_patterns` / `spb_find_spec_patterns` / `spb_manual`.

## Safety
* **Off by default.** Nothing can touch your paint until you switch the bridge on; switching it off fails pending calls immediately and prevents queued changes from applying. A change already applied remains undoable.
* The bridge only listens on your own PC (127.0.0.1) and needs a random pairing token stored in your Windows profile (`%APPDATA%\ShokkerPaintBooth\mcp\token.txt`).
* Nothing is stored or logged except counts. Preview pictures go to your chosen AI assistant (as with any image you share with it).

## For developers
`server/index.js` is a dependency-free MCP implementation (JSON-RPC over stdio). `server/tools.json` is generated from the app: `python scripts/build_mcpb.py --tools` (app open, bridge on) refreshes it and packs `shokker-paint-booth.mcpb`.
`node mcp/test/client.js smoke` runs a scripted conversation against a running app.
The page side is `js/spb-mcp-bridge.js` + `spbProAI.mcpCall` in `js/spb-pro-ai.js`; the server side is `server_routes/mcp_bridge_routes.py`.

`node mcp/test/client.js read` checks status, car map and image delivery without changing paint. `smoke` writes a scheme and undoes it: use a disposable test project. Both report nonzero exit status on tool failures.

If a model selected in the desktop app is rejected by an older CLI, update the CLI or use `/model` to choose a model supported by that client and account. SPB does not change your default model.
