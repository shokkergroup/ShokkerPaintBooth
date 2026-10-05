# Tutorial 1 — Your First Livery

**Estimated time:** 10 minutes
**Prerequisites:** None. This is the first tutorial.
**Skill level:** Absolute beginner.

Welcome. By the end of this tutorial you'll have rendered a real iRacing-ready paint job and seen it on a Chevy Silverado in the sim (or sitting in your iRacing paints folder, ready for the next time you fire up the game). It's going to take ten minutes and you're going to feel like a wizard at the end.

## What you'll learn

- How to open SPB and what you're looking at
- How to add a zone and assign a color
- How to pick a finish and watch the live preview update
- How to render and find the output file
- The general shape of every SPB workflow you'll ever do

---

## Step 1 — Open SPB and meet the Silverado

Launch SPB from the Start Menu. The first time you open the app, the **Chevy Silverado 2019** demo PSD loads automatically. You don't have to find a file, import anything, or configure anything. SPB just opens to a real, paint-able truck.

![Step 1 — Silverado loaded](docs/img/tutorial-01-step1.png)

Take a quick tour:

- **Center:** the canvas. That's the truck's UV-unwrapped paint texture.
- **Right side:** the **Layers** and **Finishes** panels (two tabs at the top).
- **Left side:** the **Zones** panel, currently empty, plus the toolbar.
- **Top:** the file menu, the big gold **RENDER** button, and the active-layer dock.

If you don't see all of this, press `Tab` once to toggle the panels back on.

## Step 2 — Add a zone

Look at the **Zones** panel on the left. Click **+ Add Zone**.

A card appears called `Zone 1` with a placeholder color swatch and finish slot. This is the basic building block of SPB: a zone is "a region of the paint that gets one specific color and finish." Most liveries are built from three to ten zones.

![Step 2 — empty zone added](docs/img/tutorial-01-step2.png)

## Step 3 — Pick a color

Click the color swatch on the Zone 1 card. The color picker pops open.

For your first livery, pick something bold. **Hex `#E63946`** is a great race red. Type it into the hex field, hit Enter, then click **Apply**.

The swatch updates. The whole truck doesn't turn red yet because we haven't told the zone *where* to paint. By default a fresh zone covers the whole car, so the entire truck is now flagged for red — but you won't see it until we apply a finish. That's next.

## Step 4 — Pick a finish

Click the **Finishes** tab at the top of the right panel.

Scroll until you find the **Candy / Liquid** category. Expand it and click **candy_apple**.

![Step 4 — candy_apple selected](docs/img/tutorial-01-step4.png)

Within a second or two, the canvas redraws. The Silverado is now wearing a deep, juicy candy-apple red coat. The Live Preview pane (split with the canvas) shows you the same paint with realistic 3D-aware shading so you can see how light catches the curves.

Pause and admire. You are five clicks into SPB and you have a real livery.

> Tip: candy_apple is one of dozens of finishes. The **★ COLORSHOXX** category at the very top has the wildest premium options. We'll cover the full catalog in Tutorial 4.

## Step 5 — Hit RENDER

In the top header, click the big gold **RENDER** button.

SPB does three things in sequence:

1. Composites the final color paint texture (the `.tga` iRacing reads for color)
2. Generates a matching spec map (the `_spec.tga` iRacing reads for material properties)
3. Copies both into your iRacing car folder (the **iRacing Car Folder** in the top bar)

A green banner under the render tells you where the files went, something like:

```
Documents\iRacing\paint\trucks silverado2019\car_num_<your-iracing-id>.tga
Documents\iRacing\paint\trucks silverado2019\car_spec_<your-iracing-id>.tga
```

(`car_num_` when **Custom Number** is selected next to your ID, `car_` for **Sim-Stamped Number**; iRacing loads the one that matches its **Hide Car Numbers** setting.) If the car folder is empty, SPB still renders but nothing is copied into iRacing, and a banner tells you to set the car folder.

## Step 6 — See it in iRacing

If iRacing is already running with your car:

1. **Alt+Tab** to iRacing.
2. Press **Ctrl+R** (Reload Car Textures). The car flashes white, then shows your new paint.

If iRacing isn't running, start it: the custom paint loads when you sit in the car.

![Step 6 — Silverado in iRacing](docs/img/tutorial-01-step6.png)

That's it. You painted a car. Welcome to the club.

---

## Try it yourself

The same workflow, but make it yours:

1. With the Silverado still loaded, click your zone's color swatch.
2. Pick a totally different color. Try a deep teal (`#0A6E7C`) or a hot pink (`#FF3D7F`).
3. Pick a different finish — try **chrome_mirror** for a wild mirror finish, or **matte_clean** if you want the opposite of candy.
4. Hit RENDER again.
5. Reload the truck in iRacing.

Every time you change the color or finish, you can re-render. There is no "save before you can see it" step. The pipeline is built for fast iteration — most users iterate ten or twenty times on a livery before they're happy with it.

---

## Troubleshooting

**The canvas is blank or stuck on a placeholder.** Press `F5` to flush the preview cache and force a re-render. If that fails, restart the app — the auto-restore feature will bring back your work.

**RENDER button is grayed out.** It is greyed only while no paint is open or one is still loading. If you click it and a message appears, read it: it names what is missing (a Source Paint, your iRacing User ID, or a zone that has both a colour and a finish).

**Render finished but I can't find the file in iRacing.** Check the **iRacing Car Folder** in the top bar: it must be the folder of the car you drive. Say **it does not show up in iRacing** in the chat and the helper checks it for you.

**iRacing shows the old paint.** Alt+Tab to iRacing and press **Ctrl+R** (Reload Car Textures). No restart needed.

**The candy red looks weirdly muted in iRacing.** That's correct! iRacing applies its own lighting, ambient occlusion, and clearcoat. The Live Preview in SPB shows the paint in flat studio lighting; in-sim you'll see the same paint under track lighting. They will look slightly different. This is expected.

---

## Next up

[Tutorial 2 — Layer Basics](02_layer_basics.md). You just painted the whole truck one color. Next we'll learn how to paint *parts* of the truck differently — and that starts with understanding the Layers panel.
