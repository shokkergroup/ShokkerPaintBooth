# Tutorial 10 — Render & Export

**Estimated time:** 8 minutes
**Prerequisites:** [Tutorial 1 — Your First Livery](01_first_livery.md) (any later tutorial is also fine)
**Skill level:** Beginner to intermediate.

Welcome to the final tutorial. You've built liveries, mastered zones, layered effects, and touched pro-level tools. Now we'll close the loop: the render pipeline. Understanding how SPB turns your project into iRacing-ready TGAs — and how to share your work — turns one-off paints into a repeatable workflow.

## What you'll learn

- The difference between Live Preview and full Render
- When and why to hit `F5`
- How to use the render history to roll back mistakes
- How Live Link deploys to iRacing automatically
- How to export and share a `.shokker` config file

---

## Step 1 — Live Preview vs. full Render

SPB has two rendering modes:

- **Live Preview** — continuous, automatic, lower-quality. Updates as you work so you always see approximately what the final looks like.
- **Full Render** — on-demand, high-quality, writes TGAs to disk. This is what you send to iRacing.

Live Preview runs in a background thread. It's fast, lightweight, and uses GPU acceleration where available. Any time you change a zone, swap a finish, adjust a layer — Live Preview re-composites within ~500ms.

Full Render is slower (1-3 seconds on a modern machine) because it runs the full paint engine at 2048x2048 with all the extra polish — anti-aliasing, high-precision spec map computation, final clearcoat pass. This is what you commit to disk.

The rule: **iterate with Live Preview. Commit with Full Render.**

## Step 2 — The F5 key

Press `F5` any time the Live Preview looks stale or wrong. It flushes the cache and forces a full Live Preview rebuild.

Moments when you'll want F5:

- After changing a layer's visibility and the preview doesn't update
- After reloading a modified external PNG that's used as a pattern
- After changing graphics settings and wanting a fresh comparison
- Whenever the preview "feels" stuck

Ninety percent of "my preview is stuck" support questions resolve with one F5 press.

## Step 3 — Hit RENDER

In the top header, the big gold **RENDER** button. Click it.

Three things happen in sequence:

1. **Color pass:** SPB composites the final color TGA at full resolution.
2. **Spec pass:** SPB generates the matching spec map TGA.
3. **Deploy:** if **iRacing Car Folder** (top bar) is set, both files are copied into it: `car_num_<ID>.tga` (Custom Number) or `car_<ID>.tga` (Sim-Stamped Number), and `car_spec_<ID>.tga`. With no car folder nothing reaches iRacing (a banner says so). Shokker keeps the two newest renders in its own render folder.

A green banner under the render tells you where the files went; a red one tells you what failed.

![Step 3 — Render confirmation dialog](docs/img/tutorial-10-step3.png)

## Step 4 — Render History

Every render is logged in the **Render History** panel (`View → Render History` or `Ctrl+H`).

Each entry shows:

- Timestamp
- Thumbnail of the render
- File paths (color and spec)
- Zone snapshot (which zones were active, which finishes applied)

From any history entry you can:

- **Re-open** — load that render state back into the project (great for "wait, I liked it better three changes ago")
- **Copy paths** — grab file paths for sharing or backup
- **Delete** — prune old renders you don't want cluttering the list

History is stored in `Documents\Shokker Paint Booth\render_history\` as a JSON log plus the actual TGA files. You can clean it out manually — older renders eat disk.

## Step 5 — Getting the files into iRacing

The top bar holds everything iRacing needs:

- **iRacing User ID:** your iRacing **Customer ID** (4–7 digits; helmet icon in iRacing → Profile). It is part of every file name; it is not your car number.
- **Custom Number / Sim-Stamped Number:** Custom Number writes `car_num_<ID>.tga` (your paint carries its own number; iRacing loads it only with **Settings → Graphics → Hide Car Numbers ON**). Sim-Stamped Number writes `car_<ID>.tga` (iRacing stamps your number on; Hide Car Numbers OFF). They must agree. If you are unsure, render once in each mode: both files stay in the folder.
- **iRacing Car Folder:** the car's folder, for example `Documents\iRacing\paint\stockcars chevyss\` (the ▾ menu lists the folders iRacing created; run a car once in iRacing to create its folder).

With the car folder set, every RENDER copies the paint and spec files into it. **Auto-deploy after render** (Settings gear) only matters when the car folder is empty. Then in iRacing press **Alt+Tab → Ctrl+R** (Reload Car Textures).

Something not showing? Say **it does not show up in iRacing** in the chat and the built-in helper checks your settings and your folder.

## Step 6 — Export config (.shokker file)

Project saves (`.spb`) are self-contained but tied to a specific template. To share a **complete painting project** with a friend — including custom patterns, imported logos, reference images — use the `.shokker` export.

`File → Export → Shokker Package` (or `Ctrl+Shift+E`).

Pick an output filename. SPB bundles:

- The `.spb` project file
- All imported layers (logos, patterns)
- Render history (optional, toggle off for smaller file)
- Any custom finishes or presets you've created
- A README with project metadata

The result is a single `.shokker` file that your friend can open on their machine (`File → Open` reads `.shokker` directly) and see your entire project, exactly as you built it. It's the canonical way to share, back up, or submit to a team archive.

## Step 7 — Sharing renders publicly

Just want to show off the finished paint on Discord or Twitter? Two fast paths.

**From the Render History:**
1. Right-click an entry.
2. **Copy as PNG** — puts a PNG of the render on your clipboard.
3. Paste into Discord / X / wherever.

**From the canvas:**
1. `File → Export → PNG Snapshot` (or `Ctrl+Shift+P`).
2. Pick resolution (1080, 1440, or 4K).
3. Save or copy to clipboard.

PNG exports are for social media only — they don't carry the spec map, so they can't be used in iRacing. Use TGA export for the sim.

## Step 8 — Verify in iRacing

The loop closes in-sim.

1. Fire up iRacing.
2. Load the relevant car (Silverado if you followed along).
3. Go to Paint screen.
4. Reload. Your custom paint appears.

Drive a lap. The paint responds to track lighting, direction of motion, and camera angle. This is where your spec map decisions (Tutorial 5) shine or fall flat. If something looks off in-sim, check the Channel Inspector back in SPB, adjust, re-render, reload iRacing.

The fast iteration loop: **SPB change → RENDER → iRacing reload**. Less than 10 seconds, ideally. Budget to do it dozens of times per livery.

---

## Try it yourself

Close the full loop and ship a livery:

1. Load the Silverado (or any template).
2. Build a livery you're happy with — zones, colors, finishes, effects.
3. Hit RENDER.
4. Alt-tab to iRacing. Load the Silverado on a test track.
5. Check it looks right. Note anything off.
6. Back to SPB. Make one adjustment.
7. F5 to refresh Live Preview (sanity check).
8. RENDER again.
9. Reload the Silverado in iRacing. Confirm the change.
10. When happy, `File → Export → Shokker Package`. Send the file to a friend.

Total time, once you have a design ready: about 3 minutes from final tweak to sharable package.

---

## Troubleshooting

**RENDER does nothing or shows a message.** The button is greyed only while no paint is open or one is loading. Otherwise a message tells you what is missing: a Source Paint, your iRacing User ID, or a zone with both a colour and a finish.

**Render finished but iRacing shows old paint.** Alt+Tab to iRacing and press **Ctrl+R** (Reload Car Textures); in a replay, move to a moment when your car is not in the pit lane. Still old? Check that the User ID, the car folder and the Custom Number / Sim-Stamped setting (with iRacing's Hide Car Numbers) all agree: the chat helper can check them for you.

**Car folder not found.** Pick the car's folder again with the ▾ menu or the folder button (it must be a folder, not a .tga file). iRacing creates a car's folder the first time you run that car in a session.

**Render History is empty after restart.** History is enabled by default but can be toggled off in Settings → Render → Keep History. Also check disk space — if `Documents\Shokker Paint Booth\render_history\` is on a full drive, writes silently fail.

**.shokker file won't open on another machine.** Verify the recipient has a matching or newer version of SPB. `.shokker` files from v6.2 open cleanly in v6.2+ but aren't backward-compatible to v5.x.

**PNG export looks different from the in-sim render.** That's expected. Live Preview / PNG export uses flat studio lighting; iRacing uses real-time track lighting with AO and atmosphere. Use the PNG for marketing; trust the in-sim render for "does this actually look right."

---

## What's next?

You've finished the tutorial series. You can build zones, manage layers, stack finishes, author spec maps, place sponsors, apply effects, work with recipes, use the advanced toolbox, and ship renders to iRacing.

Now the fun part: **make something good.** Browse the `#livery-showcase` channel on Discord for inspiration. Import a recipe you like and remix it. Build your own team's brand.

When you hit walls, the reference docs in the `/` root folder cover every feature in depth:

- `SPB_GUIDE.md` — the full user guide
- `SPB_FEATURES.md` — feature catalog with use cases
- `SPB_SPEC_MAP_GUIDE.md` — the spec map bible
- `SPB_TIPS_AND_TRICKS.md` — workflow speed-ups
- `SPB_TROUBLESHOOTING.md` — when things break
- `SPB_FAQ.md` — the 40 most common questions

And if you build a workflow worth teaching, come back and write Tutorial 11. We'd love the contribution. See [README.md](README.md) for submission guidelines.

Happy painting.
