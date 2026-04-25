# Tutorial 2 — Layer Basics

**Estimated time:** 8 minutes
**Prerequisites:** [Tutorial 1 — Your First Livery](01_first_livery.md)
**Skill level:** Beginner.

In Tutorial 1 you painted the whole Silverado one color. That was easy because every iRacing template is built on a stack of **layers** — labeled regions of the truck like "Hood," "Doors," "Numbers," "Sponsors," and so on. Once you understand layers, you can paint each region separately, and from there everything in SPB clicks into place.

## What you'll learn

- What a PSD layer actually is and why iRacing templates use them
- How to navigate the Layers panel
- How to select a layer and what selection does
- How to use the active-layer dock above the canvas
- How to toggle layer visibility and reorder layers

---

## Step 1 — Open the Layers panel

If you've still got the Silverado loaded from Tutorial 1, look at the right side of the screen. There are two tabs at the top: **Layers** and **Finishes**. Click **Layers**.

![Step 1 — Layers panel open](docs/img/tutorial-02-step1.png)

You'll see a long, scrollable list. Each row is a layer in the underlying PSD template — things like:

- `Background`
- `Body Base`
- `Hood`
- `Doors`
- `Roof`
- `Numbers`
- `Sponsors`
- `Stripes`
- `Window Trim`

The exact list depends on the template (different cars have different parts). The Silverado has about 30 layers.

## Step 2 — What's a PSD layer, in 30 seconds

iRacing's car painting templates are Photoshop files (`.psd`). A PSD is a stack of transparent images, one on top of the other, that combine to form the final paint. Each layer is one piece — the hood is a layer, the door numbers are a layer, the manufacturer logo is a layer. When SPB loads a PSD, it preserves that layer structure.

This matters because **zones in SPB can be restricted to a single layer.** That means you can say "paint the Hood layer red" without affecting any other part of the truck. We'll do exactly that in Tutorial 3.

## Step 3 — Select a layer

Click the **Numbers** layer in the panel.

Two things happen:

1. The row highlights gold. That layer is now your **active layer**.
2. The **active-layer dock** above the canvas updates to show the layer's name and a few quick-action buttons.

![Step 3 — Numbers layer selected](docs/img/tutorial-02-step3.png)

> Tip: Selecting a layer here tells SPB which layer your *drawing tools* (brush, eraser, fill bucket) will paint on. Selecting a layer does NOT yet restrict any zone to that layer — that requires the gold **Lock** button, covered in Tutorial 3.

## Step 4 — Tour the active-layer dock

The dock above the canvas is a small but powerful UI element. From left to right it has:

- **Layer name** — confirms which layer you've got selected
- **Visibility toggle** (eye icon) — show or hide the layer
- **Solo** — temporarily hide every other layer so you only see this one
- **Opacity slider** — fade the layer from 0 to 100 percent
- **Lock to Layer** (the gold padlock) — pin the active zone to this layer (Tutorial 3 covers this in detail)
- **Effects** (FX) — open the Layer Effects dialog (Tutorial 7)

Hover any of these for a tooltip. The dock is the single most-used UI element after the zones panel itself.

## Step 5 — Toggle visibility

Click the eye icon next to a layer in the panel — say, **Sponsors**.

The sponsor logos disappear from the canvas. Click again, they come back. Visibility toggles are non-destructive: hiding a layer doesn't delete anything, it just stops drawing it during preview and render.

This is incredibly useful for:

- A/B testing designs ("does the truck look better with or without the door numbers?")
- Cleaning up the canvas while you work on a fiddly part
- Temporarily hiding clutter to take a clean screenshot

> Tip: `Alt+click` the eye icon to **solo** the layer — hide everything except the one you clicked. `Alt+click` again to restore.

## Step 6 — Move a layer in the stack

Click and drag the **Stripes** layer up or down in the list.

Layer order matters. Layers higher in the panel render *on top of* layers below. Move Stripes above Sponsors and your stripes will cover the sponsor logos. Move it back down and the sponsors paint over the stripes.

This is the same as Photoshop layer ordering. If you've done any digital art, it'll feel familiar instantly. If you haven't, the rule of thumb is: **top of the panel = on top of the canvas.**

## Step 7 — Lock a layer

Right-click any layer and pick **Lock layer** from the menu (or use the lock icon in the layer row).

A locked layer can't be edited by the drawing tools. It's a guardrail — useful when you're doing detail work near a layer you don't want to bump.

`Ctrl+L` while a layer is selected toggles its lock state.

---

## Try it yourself

A focused exercise to lock in the muscle memory:

1. **Hide every layer except Numbers.** Use solo (`Alt+click` the eye on Numbers) — much faster than clicking each eye one at a time.
2. Note that the canvas now shows only the race numbers floating in space. The rest of the truck is invisible.
3. **Re-show all layers.** `Alt+click` the Numbers eye again to un-solo.
4. **Drag Numbers above Sponsors** in the stack. Watch the canvas — if your truck has any overlap between the two layers, the order swap will be visible.
5. **Lock the Background layer.** Try to paint on it with the brush tool (`B`). SPB will refuse and pop a tooltip telling you the layer is locked. Unlock and try again.

If you got through all five with no surprises, you understand layers.

---

## Troubleshooting

**I can't find the Layers panel.** Press `Tab` to toggle panel visibility. If still missing, the panel might be collapsed — look for a thin vertical strip on the right edge of the screen, click it to expand.

**Selecting a layer doesn't seem to do anything visible.** That's correct. Selecting a layer in SPB is a *workflow* action, not a visual one. It tells the next drawing or zone-locking action which layer to operate on. The visible feedback is the gold highlight in the panel and the active-layer dock update — nothing on the canvas changes just because you selected a layer.

**Solo isn't working.** Make sure you're holding `Alt` when you click the eye. Plain-click toggles visibility on just that one layer; `Alt+click` solos it.

**The layer order looks scrambled after I imported a PSD.** SPB preserves the original PSD layer order on import. If it looks wrong, the original PSD file probably had unusual ordering. You can re-order in SPB without affecting the source PSD.

**Right-click context menu doesn't appear.** A few graphics drivers swallow right-click events. Try using the gear icon next to the layer name instead — same menu, different access path.

---

## Next up

[Tutorial 3 — Zones Explained](03_zones_explained.md). This is the most important tutorial in the whole series. Layers tell SPB which *region* of the truck a thing is on. Zones tell SPB *what color and finish* to paint there. The two systems work together, and once you get the combo, you can paint anything.
