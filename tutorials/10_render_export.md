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
3. **Deploy:** If Live Link is enabled, both files are copied to your iRacing paints folder. Otherwise they land in `Documents\Shokker Paint Booth\renders\`.

A confirmation dialog tells you exactly where the files went.

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

## Step 5 — Live Link to iRacing

Live Link is the feature that makes SPB feel like magic: every time you hit RENDER, the files go *straight to iRacing's paints folder*. No manual copy, no file management. You go from "change a color" to "see it in the sim" in seconds.

Configure in `Settings → Live Link`:

- **Enabled:** On / off
- **iRacing Paints Folder:** Browse to `Documents\iRacing\paint\` (typically auto-detected)
- **Subfolder convention:** SPB auto-routes to the right subfolder based on the current template — `trucks\silverado2019\` for the Silverado, `series\gt3\` for GT3 cars, etc.
- **File naming:** `car_<driver-id>.tga` and `car_spec_<driver-id>.tga` (driver ID pulled from iRacing profile)

Once configured, forget it. Every render from then on deploys automatically.

**Multi-machine:** if you paint on one machine and race on another, set Live Link to a shared Dropbox / OneDrive folder that both machines sync. Paint on the laptop, race on the gaming desktop, no manual transfer.

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

**RENDER is grayed out.** No active zones, or the current project has errors. Check the Zones panel for missing colors or finishes.

**Render finished but iRacing shows old paint.** iRacing caches aggressively. In the Paint screen, hit the reload button. If still stale, exit to the main menu and come back — iRacing sometimes only reloads on session change.

**Live Link path not found.** Open Settings → Live Link → verify the path. If iRacing was installed to a non-default location (e.g., `D:\iRacing`), update the path manually.

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
