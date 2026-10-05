# HANDOFF → Codex / OpenAI: "Bring your own ChatGPT plan" AI mode for Shokker Paint Booth

**From:** Claude (Claude Code session, 2026-10-01) · **To:** Codex (OpenAI) · **Owner:** Ricky
**Status of the Claude side:** built and working (verified live today on the owner's ARCA Chevrolet SS).
**Your job:** make the *same* thing work for buyers who pay for **ChatGPT Plus / Pro**, without OpenAI API keys or per-token cost.

Read this whole file before writing code. Most of the work is already done: the MCP server in `/mcp` follows the standard protocol and works with any client. What's missing is the OpenAI-side install path, the wording, and a few fixes that today's live test exposed.

---

## 1. The idea in one paragraph

Shokker Paint Booth (SPB) has two ways to put an AI in charge of a paint job:

| | **In-app copilot** (exists) | **Bring-your-own-assistant via MCP** (exists for Claude, YOUR task for OpenAI) |
|---|---|---|
| Where the buyer types | The chat box *inside* SPB's AI panel | Their own AI app (Claude Desktop / Claude Code today; **Codex / ChatGPT desktop** for you) |
| Who calls whom | SPB → LLM API (OpenRouter, DeepSeek today) | AI app → MCP server → SPB |
| Who pays | Buyer needs an API key; billed per token | **The buyer's existing subscription.** No key, no per-token bill |
| Code | `js/spb-pro-ai.js` (`send`, `ask`, `buildSystem`) | `mcp/server/index.js` + `server_routes/mcp_bridge_routes.py` + `js/spb-mcp-bridge.js` |

The MCP direction is the one that lets a subscription stand in for API usage. The AI app is the *client*, SPB is a *tool server*, and the model runs on the buyer's own plan. **The buyer chats in their AI app, not inside SPB.** SPB shows each change live in its AI panel with an Undo button.

---

## 2. Architecture (what already exists)

```
 Buyer types in Claude / Codex
          │  (MCP, JSON-RPC 2.0, newline-delimited, over stdio)
          ▼
 mcp/server/index.js            ← zero-dependency Node process the AI app spawns
          │  POST http://127.0.0.1:59876/api/mcp/call
          │  header X-SPB-MCP-Token: <token from %APPDATA%\ShokkerPaintBooth\mcp\token.txt>
          ▼
 server_routes/mcp_bridge_routes.py   ← Flask; queues the call, waits for the page
          ▲  GET /api/mcp/poll (long-poll)   POST /api/mcp/result
          │
 js/spb-mcp-bridge.js  (in the open SPB page: Electron window OR a browser tab on localhost:59876)
          │  window.spbProAI.mcpCall(tool, args)   ← same zone kit the in-app copilot uses
          ▼
 Zones / car library / design library / renderer → result JSON + preview images go back up the chain
```

Key facts:

- **The page executes everything.** The Python server only relays. If no SPB page is open, calls time out with "Is the app running?". A browser tab works as well as the Electron window (verified today in Edge).
- **Off by default.** The buyer turns it on in the AI panel (gear icon). The toggle is currently labelled *"Let Claude control Shokker Paint Booth"*. Turning it on creates the pairing token; turning it off fails all pending calls immediately.
- **Security:** `/api/mcp/call` requires the token *and* a local request; Origin/Sec-Fetch-Site checks stop a web page from calling it. Keep all of that.
- **Tools** (20): `spb_status, spb_get_state, spb_get_zones, spb_get_car_map, spb_preview, spb_request_parts, spb_design_recipes, spb_apply_scheme, spb_add_zone, spb_edit_zone, spb_duplicate_zone, spb_edit_layer, spb_undo, spb_find_finishes, spb_finish_details, spb_compare_finishes, spb_browse_catalog, spb_find_patterns, spb_find_spec_patterns, spb_manual`. Descriptions and schemas are **generated from the app** into `mcp/server/tools.json` by `python scripts/build_mcpb.py --tools` (app open, bridge on). `NAME_MAP` in `index.js` maps MCP names to app tool names.
- **Server `instructions`** (the `INSTRUCTIONS` const in `index.js`) carry the design rules: work on named parts, never big grid boxes; band geometry; spec-only = Foundation finish + `color:"source"`; never invent finish keys. Two **prompts** also exist (`design_livery`, `spec_only`).
- **Images:** `spb_preview` and every write tool return the live preview (and optionally the spec map) as MCP `image` content blocks. The model *looking at its own work* is what makes the results good. See §5.3: you must confirm that Codex passes these images to the model.
- **Timeouts:** per-tool HTTP timeouts in `timeoutFor()`: `apply_scheme` 170 s, `add_zone`/`edit_zone` 150 s, `preview` 90 s, default 60 s.
- **Tests:** `node mcp/test/client.js smoke|design|spec|list` runs a scripted conversation against a running app and saves returned images to `mcp/test/out/`.
- **Claude packaging:** `mcp/shokker-paint-booth.mcpb` (a Claude Desktop extension bundle) plus an "Install in Claude Desktop" button (`POST /api/mcp/open-bundle`). Docs for buyers: `mcp/README.md`.

---

## 3. The OpenAI route — what to target

Researched 2026-10-01. **Re-verify against current OpenAI docs before building; this area changes monthly.**

### 3.1 Recommended: **Codex** (CLI, IDE extension, and the Codex surface in the ChatGPT desktop app)
- Codex signs in with the buyer's **ChatGPT account** (Plus / Pro / Business…): subscription usage, no API key. ✔ This is the equivalent of "Claude Code on a Claude plan".
- Codex supports **local stdio MCP servers**, which is exactly what `mcp/server/index.js` is. ✔ No server rewrite needed.
- One config is shared by the Codex CLI, the IDE extension and the ChatGPT desktop app (per OpenAI's docs: "The ChatGPT desktop app, Codex CLI, and IDE extension share this configuration."). File: `~/.codex/config.toml` (Windows: `%USERPROFILE%\.codex\config.toml`).

Install command:
```bash
codex mcp add shokker-paint-booth -- node "C:/Program Files/Shokker Paint Booth/resources/mcp/server/index.js"
```
Equivalent `config.toml` (what an "Install in Codex" button should write):
```toml
[mcp_servers.shokker-paint-booth]
command = "node"
args = ["<install dir>/mcp/server/index.js"]
startup_timeout_sec = 20
tool_timeout_sec = 200          # REQUIRED: apply_scheme can take ~170 s; a lower client timeout kills it mid-render
# default_tools_approval_mode = "auto"   # optional: skips a confirm prompt on every tool call (offer it as a choice, don't force it)

[mcp_servers.shokker-paint-booth.env]
SPB_PORT = "59876"
```
⚠ Confirm the real install path of the `mcp/` folder in the packaged Electron app (see §5.5) before you hard-code it in a button.

### 3.2 Not recommended (yet): ChatGPT web / desktop **chat** with Developer Mode connectors
- Plus/Pro can add custom MCP connectors in Developer Mode, **but only remote HTTPS servers. There is no stdio.** A local server needs a tunnel (ngrok, Cloudflare, or OpenAI's Secure MCP Tunnel).
- Exposing a "repaint this person's car" endpoint to the internet is a security and support burden. **Do not ship this path** unless the owner explicitly asks. If he does, it needs: a Streamable-HTTP transport added to `index.js`, OAuth or a strong per-install secret, the tunnel set up by the buyer, and the same token and Origin rules. Write a design note first and get approval.

---

## 4. What to build (task list, in order)

1. **Prove it works unchanged.** On a dev box with SPB open and the bridge on, run `codex mcp add …` (above) and ask Codex: *"Using Shokker Paint Booth, call spb_status."* Then run a full design brief (§6). Record what works and what doesn't in your lane doc, not the wiki.
2. **Make the server client-neutral** (`mcp/server/index.js`):
   - `friendly()` error strings say *"restart Claude"* / *"Claude bridge"*. Change them to *"your AI assistant (Claude or Codex)"*.
   - Header comment and README: name both clients.
   - Keep `serverInfo.name = 'shokker-paint-booth'` (both clients key on it).
3. **Make the app UI client-neutral:**
   - Toggle label → *"Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth"*. It's found via `grep -rn "Let Claude control" js/` (also `js/spb-ai-knowledge.js`).
   - Add an **"Connect Codex"** button next to "Install in Claude Desktop". Simplest safe version: show the exact `codex mcp add …` command, with the real install path filled in and a Copy button. Better version: a server route that **appends** (never overwrites) the `[mcp_servers.shokker-paint-booth]` block to `~/.codex/config.toml` after the buyer confirms, using a temp file plus atomic replace (`engine/atomic_io.py` pattern). Never edit other sections of that file.
   - Show "connected" status for either client. `/api/mcp/status` already reports `connected` / `lastTool`; it doesn't know which client is connected, and doesn't need to.
4. **Write buyer docs:** add a "ChatGPT / Codex" section to `mcp/README.md` in the same style as the Claude section (setup in 3 steps, a sample prompt, the safety section unchanged).
5. **Fix the two bugs found today** (§5.1, §5.2). They affect Claude users too.
6. **Run the gates** (§7) and update the Living Wiki (board row + one log entry, per CLAUDE.md).

---

## 5. Traps and open issues (READ — found live on 2026-10-01)

### 5.1 BUG: `apply_scheme` said "sides not known" right after `spb_status` listed them
The first `spb_apply_scheme` of the session skipped every band, stripe and bumper with *"the left / right sides are not known on this car"*. A moment earlier, `spb_status` had returned all 8 parts with `"source": "car library"`. After a `spb_get_car_map` call, the identical request worked. This looks like the car-library parts are loaded lazily, or `apply_scheme` reads a different cache than `status`. **Fix at the source:** `apply_scheme` must resolve parts the same way `status` / `get_car_map` do. Until then, the server instructions could tell the model to call `spb_get_car_map` before `spb_apply_scheme`, but fix the real cause.

### 5.2 BUG / DESIGN GAP: two AIs editing the same car at once
While Claude was mid-design over MCP, the in-app copilot (OpenRouter/DeepSeek) ran an answer. Its changes interleaved with Claude's: a zone index Claude had read became a different zone ("Powder blue body base"), so Claude's edit landed on the wrong zone. `mcpCall` only refuses a call *while* the in-app copilot is busy (`_busy` in `js/spb-pro-ai.js`). There's no lock *between* MCP calls. Zone **indices** are not stable identities. Fix:
- a **session lease**: while an external assistant has made a call in the last ~2 minutes, the in-app chat shows "An external AI is designing; take over?" instead of silently running (and vice versa);
- let `edit_zone` accept a stable zone **id or name** (and/or an `expect_name` guard that fails if the index now points at a different zone).

### 5.2b BUG (root cause of most of today's chaos): two open SPB pages both answer MCP calls
With SPB open in an Edge tab **and** a Chrome tab, both pages long-poll `/api/mcp/poll`, and each call goes to whichever page grabs it first. Consecutive `spb_get_zones` calls alternated between two different designs (a 5-zone reset vs a 13-zone Gulf scheme), `spb_status` reported the *other* page's `ai_panel_busy:true`, and edits landed on the wrong car. It was diagnosed with `Get-NetTCPConnection -RemotePort 59876` (msedge plus chrome both connected). Fix in `server_routes/mcp_bridge_routes.py` + `js/spb-mcp-bridge.js`: **one page owns the bridge** (a lease held by a per-page id, renewed on each poll). Other pages get `{owned_by_other:true}` and show "Another Shokker window is connected to the AI. Use this one instead?" in the AI panel. Also return the page id in every result so a client can detect a switch.

### 5.2c BUG: `spb_undo` skips over manual resets in the app
The owner cleared the zones in the app (5 empty zones), then Claude made 8 MCP changes and called `spb_undo steps:8`. Expected: back to the 5-zone reset. Actual: a **33-zone** snapshot from much older sessions, with most regions widened to "everything on body layers". Manual edits made in the app (reset / clear) don't push an undo snapshot, so the AI undo stack's "before" state is stale. Fix: snapshot the live zones at the **start of every MCP/copilot change** (not at the previous AI change), and/or make every manual zone-list reset push to the same undo stack.

### 5.3 Images must reach the model
The workflow depends on the model seeing `spb_preview` images (preview + spec map). OpenAI's Codex MCP docs don't state whether `image` content blocks from MCP tools are forwarded to the model. **Test it first.** If they aren't, add a fallback: a `spb_preview` option that returns a short **measured** text summary instead (colour shares already exist; add per-part dominant colour, visible % per zone, and the `problems_found_by_app` list). Do not let a model claim it "looked" at something it never received.

### 5.4 Timeouts
Codex's default per-tool timeout is shorter than SPB's slowest calls. Without `tool_timeout_sec = 200`, `apply_scheme` gets cut off mid-render and the model retries, which **stacks duplicate zones**. Set the value in every config you generate, and document it.

### 5.5 Packaging
- `electron-app` packaging: confirm `mcp/server/index.js` + `tools.json` actually ship (check `electron-app/package.json` `files`/`extraResources` and `scripts/sync-runtime-copies.js`; the **two-copy rule** in CLAUDE.md applies to runtime files). Users need `node` on PATH for Codex. Claude Desktop bundles its own Node; Codex doesn't. Either detect Node and show install guidance, or point `command` at the Electron binary with `ELECTRON_RUN_AS_NODE=1` (verify that this works before relying on it).
- Regenerate `tools.json` with `python scripts/build_mcpb.py --tools` whenever app tool schemas change, or both clients drift.

### 5.6 Design-quality lessons from today's live build (put them in the instructions if they help Codex)
- Whole-car looks belong on the body paint layers only. Numbers, sponsors and logos stay untouched; the app already enforces this.
- The `lightning` paint pattern on a matte-black body reads as **grey cracked glass**, not bolts, at scale 1–2.6. Prefer a monolithic special with built-in veins (e.g. `monolithic::fmo_spectrolite_vein`).
- Chrome pinlines on a white base need a real silver colour; candy and metal twists are invisible in the flat preview, so check `spb_preview spec=true`.
- On the ARCA Chevy SS the **spoiler has no body-paint pixels**, so `apply_scheme` skips it. That's expected.
- The right-side panel is stored upside down on the sheet (roof-line at the bottom edge), so a "lower band" appears near the top of that panel in the flat preview. That's correct, not a bug.

---

## 6. Acceptance test (what "done" means)

On a clean Windows user profile with only ChatGPT Plus signed into Codex (no OpenAI API key set anywhere):

1. SPB open (Electron *and*, separately, a browser tab on `localhost:59876`), bridge on, "Connect Codex" used.
2. In Codex: *"Using Shokker Paint Booth, give my car an old-school Pepsi look with chrome trim over a flat finish."* The model calls `spb_status → spb_design_recipes → spb_apply_scheme → spb_preview`, and the scheme appears on the car with Undo entries in the AI panel.
3. *"Now make only the hood mirror chrome, keep the colours."* The paint stays pixel-identical and only the spec changes (Foundation finish + `color:"source"`). Check with `spb_preview spec=true`.
4. *"Undo that."* `spb_undo` restores the previous state.
5. Bridge toggled **off** mid-call → Codex gets the friendly "switched off" error, and nothing changes.
6. Wrong or missing token → friendly 401 message, and nothing changes.
7. In-app copilot started while Codex is designing → no interleaved edits (after the §5.2 fix).
8. The Claude path still passes the same test unchanged (`node mcp/test/client.js smoke` + a Claude Code run).

---

## 7. Gates before you call it done (project laws)

- `node scripts/sync-runtime-copies.js --check` (two-copy rule) after touching any synced runtime file; `--write` to sync.
- Bump the `?v=` cache token on **every** changed JS/CSS file (stale-cache trap: 16 files once shipped stale).
- `node mcp/test/client.js smoke` green against a running app.
- No changes to finishes, the catalogue, or protected finishes are in scope for this task. The Finish Law / Uniqueness gates don't apply unless you touch them.
- Update `SPB_WIKI.html`: claim a board row ("OpenAI/Codex MCP client support"), add **one** Daily Work Log entry per day, and keep it lean (see CLAUDE.md).
- `CHANGELOG.md` entry when it ships.

---

## 8. File map (everything you'll touch or read)

| File | What it is |
|---|---|
| `mcp/server/index.js` | The MCP server (152 lines, no deps). Instructions, prompts, NAME_MAP, timeouts, friendly errors |
| `mcp/server/tools.json` | Generated tool list (descriptions + schemas). Don't hand-edit; regenerate |
| `mcp/README.md` | Buyer-facing setup doc (Claude only today) |
| `mcp/test/client.js` | Scripted stdio test client |
| `scripts/build_mcpb.py` | `--tools` refreshes tools.json; also packs the Claude `.mcpb` |
| `server_routes/mcp_bridge_routes.py` | Flask relay: status / enable / poll / result / call / ping / open-bundle; token + origin guards |
| `js/spb-mcp-bridge.js` | Page-side long-poller → `spbProAI.mcpCall` |
| `js/spb-pro-ai.js` | In-app copilot; `mcpCall` (~line 685), `_busy` lock, settings UI, OpenRouter path |
| `js/spb-ai-knowledge.js` | In-app help text that mentions the Claude toggle |
| `%APPDATA%\ShokkerPaintBooth\mcp\token.txt` | Pairing token (created when the bridge is enabled) |
| `~/.codex/config.toml` | Codex MCP config (append only) |

Sources consulted for §3: OpenAI Codex MCP docs (learn.chatgpt.com/docs/extend/mcp, redirected from developers.openai.com/codex/mcp) and current write-ups of ChatGPT Developer Mode connectors (remote HTTPS only; Plus/Pro/Business/Enterprise/Edu).
