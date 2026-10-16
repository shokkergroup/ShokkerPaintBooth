# HANDOFF → ChatGPT / OpenAI: build SPB's ChatGPT connection (2026-10-09)

**From:** Claude (SPB orchestrator chat) · **To:** ChatGPT / Codex (OpenAI) · **Owner:** Ricky (ricky@shokkergroup.com)
**Project:** `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum` (Windows; the user path has an apostrophe, so quote every path). Branch `codex/JuneAlphaPolish`.
**Owner's words:** "Build a handoff TO OPENAI/CHATGPT for IT to work on its MCP connection. It should be very similar to how yours works but in their ecosystem. I'll let it build out its own over there."

You own the OpenAI side end to end: design it, build it, test it, document it. This file tells you how the Claude side works today, what you can reuse, which lines not to cross, and how to prove yours works.

---

## 1. What SPB is, and what "the MCP connection" means

Shokker Paint Booth (SPB) designs iRacing car paints. A paint is ONE flat 2048×2048 sheet of the whole car cut open (two side panels, hood, roof, trunk, bumpers, spoiler). Painters build it from **zones**, each with a base finish, a colour, patterns and spec (metal / roughness / clearcoat).

The MCP connection lets a buyer's **own AI subscription** drive SPB. The buyer types in their AI app; the AI calls SPB's tools; SPB shows each change live with an Undo button. No API key and no per-token bill for the owner.

```
AI app  --MCP (stdio JSON-RPC)-->  mcp/server/index.js  --POST 127.0.0.1:59876/api/mcp/call (pairing token)-->  SPB Flask server
                                                                                     <--GET /api/mcp/poll (long-poll)--  the open SPB page runs the tool
```

- **Claude:** works today in Claude Desktop (the `mcp/shokker-paint-booth.mcpb` extension) and Claude Code. Server version 1.4.0.
- **Codex:** a local Codex connection already exists. The AI panel has a "Connect ChatGPT / Codex" setup button that writes `~/.codex/config.toml`; see `mcp/README.md` § ChatGPT / Codex setup, `docs/HANDOFF_OPENAI_CODEX_MCP.md` (2026-10-01) and `docs/CODEX_MCP_SUPPORT_2026-10-01.md`. Start by checking that this still works end to end.
- **The gap is yours: ChatGPT itself (the desktop and web apps).** The README says plainly: "This connects local Codex, rather than ordinary ChatGPT web chat." Bring the same experience into ChatGPT's own ecosystem, through whichever route OpenAI supports today (ChatGPT connectors / developer mode, Apps SDK, a remote MCP endpoint, or whatever is current). **Check OpenAI's current docs yourself** rather than trusting this file; the platform changes fast.

## 2. Read these first (in order)

1. `mcp/README.md`: setup for both assistants, safety model and the developer notes (65 lines).
2. `mcp/server/index.js` (388 lines): a dependency-free MCP server (JSON-RPC 2.0 over stdio). It holds the tool list, the app tool-name map (`NAME_MAP`), the static tools (`spb_tweak`, `spb_render`, `spb_reset_zones`, `spb_wait_for_message`, `spb_reply`, …), the read-only set, and the server **instructions**, which carry the behaviour rules.
3. `mcp/server/tools.json`: the 23 generated tool schemas plus descriptions. They are generated from the app by `python scripts/build_mcpb.py --tools` (app open, bridge on). **Treat it as the single source of tool truth: reuse it, don't fork it.**
4. `server_routes/mcp_bridge_routes.py`: the bridge (`/api/mcp/status|enable|poll|result|ping|call`, plus the chat relay `/api/mcp/inbox`, `inbox/wait`, `reply`, `chat` and `codex-setup`).
5. The page side: `js/spb-mcp-bridge.js` + `spbProAI.mcpCall` in `js/spb-pro-ai.js`.
6. Tests: `node mcp/test/client.js read` (no paint change) and `node mcp/test/client.js smoke` (writes then undoes; use a throwaway project).

## 3. Behaviour the buyer must get, the same as on Claude

These rules live in the server instructions and tool descriptions. Reuse that text; don't write a weaker copy.
- **Restraint.** For vague, mood or taste requests ("make it pop", "Brazil colours"), change nothing: ask ONE short question or offer 2-3 concrete options. Concrete orders (a part plus a colour, finish, pattern or named classic livery, including terse or misspelt ones like "hod to chrom") are carried out at once. Questions or how-tos go to `spb_encyclopedia` and change nothing. Never repaint the whole car unasked, and change ONLY the parts the buyer named.
- **Named parts, not grid boxes:** `region: {part: "hood"}`. Read the parts with `spb_status` / `spb_get_car_map`.
- **Check your own work:** `spb_preview` / `spb_check` after a change, and `spb_undo` when it went wrong.
- **Iterate on one zone:** "smaller / brighter / rotate it" means `spb_tweak`, not a new zone.
- **Zone economy:** for a new base look use `spb_reset_zones` and edit the catch-all, rather than muting zones one by one.
- **Render once** per finished request with `spb_render`, and report seconds plus the files saved.
- **App chat relay (new in 1.4.0):** `spb_wait_for_message` / `spb_reply` let the buyer type in SPB's own chat box and have the external assistant answer there.
- **Pattern position (new today):** an offline-helper op `pattern_position` moves a zone's pattern. Position X up moves the pattern LEFT; Y up moves it UP. The MCP has no parameter for it yet; the proposed shape is in `_easy_claude_work/eval/w13nudge/MCP_SPEC.md`.

## 4. Lines you must not cross

- **Don't edit `mcp/server/*`, `js/spb-ai-connect.js`, `js/spb-ai-core.js` or `js/spb-quests.js`.** Another Claude chat ("APPCHAT") owns them and edits them daily. Build the ChatGPT side in **your own folder, `mcp/chatgpt/`** (plus your own `docs/` notes). If you need a change in a shared file (a new bridge route, a token mode, a tool text), write it up in `mcp/chatgpt/REQUESTS_FOR_CLAUDE.md` with the exact diff, and the owner will relay it.
- **Security.** The bridge listens only on 127.0.0.1, needs a pairing token (`%APPDATA%\ShokkerPaintBooth\mcp\token.txt`), and is **off by default**; switching it off fails pending calls. If ChatGPT needs a remote HTTPS endpoint, **never expose the raw bridge or the token**. Put a proper auth layer in front (OAuth or a per-buyer secret, per OpenAI's connector requirements), keep it off by default, make the buyer opt in explicitly, and send the minimum data. Preview images go to the AI the buyer chose; say so in the UI.
- **No API keys, no per-token cost for the owner.** That is the whole point: the buyer's ChatGPT plan pays.
- **Repo hygiene:** no git commits (the owner commits). Never use `rm`/`del` in the shell; delete files with Python `os.remove`. Never kill processes by name, only your own PID. Port **59876 is the owner's live SPB app**: MCP tests may paint on it (the owner allows that for MCP tests), but run your own servers on other ports (59880-59885 are taken; use 59910+), e.g. `SHOKKER_PORT=59910 PYTHONHASHSEED=0 python server_v5.py` from the project root.
- **Two-copy rule:** shipped files live at the root and in `electron-app/server/`. When you add a runtime file, add it to `scripts/runtime-sync-manifest.json` and run `node scripts/sync-runtime-copies.js --write`. Bump the `?v=` token in `paint-booth-v2.html` for any changed JS file.
- **Easy mode is hidden.** Never mention it in UI text, docs or replies.
- **Keep your own log.** The project wiki `SPB_WIKI.html` (Agent Coordination Board + Daily Work Log) is the shared source of truth. Claim a row for your lane, and keep entries short: one log entry per lane per day.

## 5. How to prove it works

Gate on behaviour, not on "it connected."
1. **Connection:** a fresh ChatGPT install plus your setup steps reaches `spb_status` on a real car. Time the setup and count the clicks.
2. **Scenario bank:** the Claude side is scored on 52 online scenarios (latest: 43/52, 83%, 0 harmful pixel changes). Harness and frames: `_easy_claude_work/eval/mcpscen/`, `verify_online/`, `online_ground/` (read the host scripts there). Run the same scenarios through ChatGPT and report the score in the same format. **Ship bar: ≥90% and 0 harmful** (harmful = the paint changed where the buyer did not ask).
3. **Screenshots:** for each scenario, save before/after previews, and look at them yourself. A green gate with a wrong-looking car is a fail.
4. **Safety checks:** bridge off means every call fails cleanly. Token missing or wrong means refused. An exposed endpoint without auth means refused.

## 6. Deliverables

- `mcp/chatgpt/`: your server or adapter, its setup (one-click from SPB's AI panel if possible, modelled on the existing "Connect ChatGPT / Codex" button), and a README written for a buyer.
- `mcp/chatgpt/REPORT.md`: route chosen and why, setup steps, scenario score, screenshots folder, known limits.
- `mcp/chatgpt/REQUESTS_FOR_CLAUDE.md`: any changes needed in files Claude owns.
- A line in `mcp/README.md` pointing to your section. That README is shared docs, so add a section; don't rewrite it.

Questions about product direction go to the owner, Ricky. Questions about how the Claude side behaves can be answered from the files above; when they disagree, the code wins.
