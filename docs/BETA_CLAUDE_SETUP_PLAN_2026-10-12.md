# Beta: Claude setup that "just works" — plan (Claude Opus, 2026-10-12)

Owner ask: "How are we going to ensure that people who try to use Claude AI can easily install whatever they need and it's bundled in the install itself?"

## What is already true (read from the repo, not yet clicked end to end)
- The Shokker connector for Claude Desktop ships INSIDE the SPB installer: `resources/server/mcp/shokker-paint-booth.mcpb` (synced by `scripts/runtime-sync-manifest.json:1010-1018`, `electron-app/copy-server-assets.js`).
- The buyer needs no Node or Python: Claude Desktop runs the extension on its own Node; SPB ships its own Python (`server/python/python.exe`).
- In-app path exists: AI panel → "Who should answer you?" → Claude → **Add Shokker to Claude** (opens the .mcpb; `server_routes/claude_connect_routes.py:294-312`), **Check** reads `%APPDATA%\Claude\Claude Extensions` (`:162-190`). Picking Claude switches the bridge on by itself (`js/spb-ai-connect.js:120-131`).

## What can still stop a buyer (most likely first)
1. **Claude Desktop is not installed.** We cannot bundle it (Anthropic's app, their installer and updates). The browser version of claude.ai cannot use a local extension. Today the card says "Claude Desktop / claude.ai" — wrong for beta.
2. **The connector goes stale after every SPB update.** Nothing tells the buyer to reinstall; this PC has 1.4.0 installed while the repo builds 11.0.0.
3. **No release gate for the .mcpb.** It is built by hand on the dev PC; the last `win-unpacked` carries an older .mcpb (Oct 11) than `electron-app/server/mcp/` (Oct 12). `docs/RELEASE_PROCESS.md` / `spb_release.ps1` never mention it.
4. **Never tested on a clean PC.** The wiki says the Add/Check buttons were "not clicked yet" (`SPB_WIKI.html:2705`).
5. **Unsigned** .mcpb (and no installer signing config in `electron-app/package.json`) → possible warnings (Claude's extension dialog; Windows SmartScreen for the app itself).
6. **SPB must be open** (Pro, AI panel) for tools to work; Claude cannot start SPB. Calls fail with "Is the app running?" (`mcp/server/index.js:620,709`).
7. **Help text is stale:** `data/encyclopedia/ai_copilot.json:884,885,982` ("switch on the control option", "about 27 tools"), `mcp/README.md:7`; `GETTING_STARTED.html` never mentions Claude.
8. Skill upload is manual (optional now that knowledge ships inside the extension); app-box chat needs the "Listen to my Shokker chat" loop each session.

## Plan (beta)
A. **One guided card, first launch and in the AI panel** — three states, auto-detected:
   - Claude Desktop missing → "Get Claude Desktop (free)" opens the official download page; re-checks when the window regains focus.
   - Installed, connector missing or older than this SPB → **Add / Update Shokker in Claude** (one click opens the bundled .mcpb), then the card polls the extensions folder and turns green by itself — no "Check" button needed.
   - Connected → one example line to type in Claude ("Paint my roof matte black").
   Same check at every SPB start: if the installed connector version ≠ shipped version, show the one-click Update banner.
B. **Release gate (fail the build):** `spb_release.ps1` runs `python scripts/build_mcpb.py`, then verifies (1) manifest version == SPB version, (2) the .mcpb in `win-unpacked/resources/server/mcp/` is byte-identical to the fresh build, (3) `node` from the packaged Electron can start `mcp/server/index.js` and list tools with no PATH Node (Codex already has this proof: `mcp/chatgpt/fresh-install/release-gate-proposal/` — review and adopt).
C. **Claude can open SPB:** when the app is not reachable, the connector starts the installed SPB (known install path) and waits for health, instead of only erroring.
D. **Signing:** sign the installer (code-signing certificate) and the .mcpb (`mcpb sign`), if the owner buys/has a certificate.
E. **Words:** "Claude Desktop" everywhere (not claude.ai), refresh the encyclopedia/README/GETTING_STARTED steps, version-free tool counts.
F. **Clean-PC acceptance before shipping:** fresh Windows user account (no Node, no Python, no Claude): install SPB → install Claude Desktop → one click → paint a roof → update SPB → banner → one click → still works. Screenshots of every step.

## Ownership (proposed)
- Codex (owns `mcp/`, `js/spb-ai-connect.js`, `server_routes/claude_connect_routes.py`, encyclopedia): A, C, E.
- Claude (release/build): B (+ review Codex's release-gate proposal), F.
- Owner: D (certificate purchase), final yes on the beta.
