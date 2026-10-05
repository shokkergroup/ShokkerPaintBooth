# SHOKK DROP — product tracker (internal: user_imports)

**Visual reference:** [`SHOKK_DROP_BIBLE.html`](../SHOKK_DROP_BIBLE.html) · **Linear hub:** [SPB-109](https://linear.app/shokker-poster-engine-gold/issue/SPB-109)

## Shipped
- **SHOKK THE WORLD** — 20-variant DNA explosion + EKG UI + multi-save + Try in Booth (SPB-109)
- **DNA Remix** slider — blend two styles; live preview with active World session
- Full lab at `shokk-drop.html` — header tab alongside Finish Viewer & Spec Sculpt
- Import DNA, `.spbdrop` packs, gallery, Re-DNA, engine preview
- Picker category **SHOKK DROP** · cousin to full **`.SHOKK`** designs
- Multi-panel preview: upload · spec ALL · paint|R/G/B channels
- Guest Designer catalog merge (`Guest Designer · Lyons Designs`)
- Gallery click → full channel preview in sidebar
- Finish Viewer catalog: `ui_*` drops show **human names** (e.g. Groovy Waves) not slug ids

## Overnight loop (15m) — **must wake this chat**

The old `while true; echo TICK` loop only wrote to a terminal file — **it did not run the agent**.

**Correct setup (active now):**
1. Agent runs a tick → ships code → appends `docs/SHOKK_DROP_LOOP_LOG.md` → posts summary **in this chat**
2. Agent starts `scripts/shokk_drop_loop_arm.ps1` (Windows) or `.sh` (Git Bash) in background with **monitored output** on `^AGENT_LOOP_WAKE_shokk_drop`
3. After 15m the wake line fires → **this conversation** gets a notification → next tick runs

**You need for overnight:**
- Cursor **open** on this project
- **This chat** tab active (or Cursor allowed to notify on background agent wakes)
- PC **not fully asleep** (display off OK; system sleep stops the timer)
- Optional backup: Cursor **Automations** (separate cloud runs — see prefill URL if offered)

Stop loop: ask agent to kill the background `shokk_drop_loop_arm.sh` sleep process.

### Loop backlog
- [x] Tick 1 — Gallery card click loads full channel preview panel + Re-DNA on card
- [x] Tick 2 — Finish Viewer / finish-data human names for `ui_*` + guest designer groups
- [x] Tick 3 — Search/filter in Shokk Drop gallery
- [x] Tick 4 — Pack import toast + auto-select new drop in preview
- [x] Tick 5 — DNA style picker shows human descriptions
- [x] Tick 6 — Drag PNG directly onto sidebar (not just gallery zone)
- [x] Tick 7 — `.spbdrop` share link copy button
- [x] Tick 8 — Import DNA gauntlet stats badge on gallery cards

**Backlog complete** — loop may continue for polish; ask to stop the 15m timer when done for the night.

## Demo (5 min sell)
1. Generate art externally
2. **Shokk Drop** tab → Import & preview → Commit drop
3. Click gallery card → see upload + spec + R/G/B channels
4. Share `.spbdrop` · friend drops it in gallery
5. Paint Booth → **Specials** → **SHOKK DROP** → Finish Viewer shows your drop by name
