# Tutorial 3 — Zones Explained

**Estimated time:** 15 minutes
**Prerequisites:** [Tutorial 1 — Your First Livery](01_first_livery.md), [Tutorial 2 — Layer Basics](02_layer_basics.md)
**Skill level:** Beginner-to-intermediate. The single most important tutorial in the series.

This is the tutorial that turns SPB from "an interesting paint app" into "the most powerful livery tool you've ever used." Zones are the heart of SPB. Understand zones and the rest of the app is easy. Misunderstand zones and you'll be confused for weeks.

So we're going to take our time on this one.

## What you'll learn

- What a zone actually is and why SPB is built around them
- How to use color match selection to scope a zone
- How to lock a zone to a single layer (the gold button)
- How multiple zones interact and how priority order resolves conflicts
- The "Remaining" and "Everything" special zones
- The infamous yellow #55 bug and what it taught us about alpha masks

---

## Step 1 — What's a zone, really?

A **zone** is a named region of your paint that gets one combined "look" — a color, a base finish, a pattern, and a spec map override. Think of it as a recipe for one part of the truck:

> "The hood is matte black with a carbon-weave pattern."
> "The doors are candy red with chrome accents."
> "The numbers are gloss white with a gold stroke and drop shadow."

Each of those sentences is one zone.

The brilliance of zones is that you don't have to hand-paint every pixel. You define a region (by color, by layer, or by both) and assign a finish to it. SPB does the rest.

## Step 2 — Color match selection

Add a fresh zone (`+ Add Zone` in the Zones panel). Click its color swatch.

In the color picker dialog, instead of typing a hex code, click the **Eyedropper** icon. Then click anywhere on the truck canvas — say, on the yellow door numbers.

![Step 2 — eyedropper sampling yellow](docs/img/tutorial-03-step2.png)

Two things happened:

1. The zone's **color** is now that exact yellow.
2. The zone's **mask** is now "every pixel on the truck that matches this yellow."

That second one is the magic. SPB looked at every pixel on the entire truck, found the ones whose color is close to the yellow you sampled, and made them the zone's region. You didn't draw a selection. You didn't paint a mask. You just sampled a color.

Hit RENDER. The yellow numbers (and only the yellow numbers) get whatever finish you assign to this zone. Everything else is unchanged.

## Step 3 — Add tolerance and multiple colors

Real liveries don't have one perfect pixel of yellow — they have a spectrum because of anti-aliasing, JPG artifacts, and shading. SPB handles this with **tolerance**.

In the zone card, find the **Tolerance** slider. Default is around 12. Drag it up to 30. The zone now matches yellow plus near-yellow pixels too.

Need to match multiple distinct colors in the same zone? Click **+ Add Color** in the zone card and sample a second color. The zone now matches *both*. Useful for things like "match all the team colors as one zone."

## Step 4 — Layer restriction (the gold button)

Color matching by itself is powerful but imperfect. Sometimes pixels of the same color exist in places you don't want — a yellow numbers zone might accidentally pick up yellow pixels in a sponsor logo on the other side of the truck.

This is where layer restriction comes in.

Select the **Numbers** layer in the right panel (Tutorial 2 covers this). Then look above the canvas at the active-layer dock. The gold button labeled **🔒 Lock Active Zone to This Layer** is the one we want.

Click it.

![Step 4 — locked to layer](docs/img/tutorial-03-step4.png)

Two things just happened:

1. The active zone is now restricted to **only paint pixels that exist on the Numbers layer.**
2. The zone card shows a small layer badge confirming the binding.

Now even if the same yellow exists in 20 other places on the truck, the zone won't touch them. Color match + layer lock is the combination that powers 90% of professional liveries.

> Tip: This gold button is the single biggest workflow shortcut in SPB. Whenever you find yourself wishing you could "just paint this one part," reach for it.

## Step 5 — Multiple zones and priority

Add a second zone. Make it red. Sample a red pixel somewhere on the truck (or just type `#E63946`). Pick a finish.

You now have two zones: yellow Numbers and red Something Else.

Look at the zones panel — they stack. The zone at the **top of the stack has higher priority.** If two zones target overlapping pixels, the higher-priority zone wins.

Drag-and-drop to reorder. This is the same metaphor as Photoshop layers but applied to *paint regions.* The intuition is exactly the same: top wins.

## Step 6 — Special zones: Remaining and Everything

Look at the dropdown that normally says "Custom" on a zone card. There are two special values:

- **Remaining** — fills every pixel on the truck that isn't already claimed by a higher-priority zone.
- **Everything** — fills every pixel on the truck regardless of other zones (this is essentially a "background" override).

`Remaining` is the workhorse. The pattern goes:

1. Build several specific zones for important parts (numbers, sponsors, hood)
2. Add one final zone, set it to **Remaining**, and give it your base body color and finish

That last `Remaining` zone catches everything else. You don't have to build a "body base" zone manually — SPB does it for you.

## Step 7 — The yellow #55 bug story (and the alpha-mask fix)

Real story from SPB development that teaches a critical lesson.

A user built a livery with yellow #55 numbers. Color matched, layer locked, finish assigned. Render came out — and the entire truck had subtle yellow halos on the edges of every other shape. Tiny, but visible in bright light.

What happened? Anti-aliased edges. The pixels at the boundary of every shape on the truck contain a little of every nearby color, including yellow. Color matching at high tolerance picked them up. Even with layer restriction, the *layer* itself had partially-transparent yellow pixels at its boundaries.

The fix was an **alpha-mask threshold**: SPB now ignores pixels with an alpha below a configurable threshold (default 0.5) when building zone masks. If a pixel is less than half-opaque on its layer, it doesn't count.

The lesson for you: if you ever see "ghost" zone coverage where you don't expect it, check the **Alpha Threshold** slider on the zone card. Pull it up to 0.6 or 0.7 to be stricter. Most of the time the default works, but it's the first thing to adjust when masks misbehave.

---

## Try it yourself

A real, three-color livery. This is the exercise that makes everything click.

1. **Reset.** Delete every zone you have so the truck is back to a blank canvas.
2. **Zone 1: Body.** Add a zone, set color to deep blue (`#1F3A6E`), pick the **gloss_clean** finish, set the zone type to **Remaining**. This is your background.
3. **Zone 2: Numbers.** Add a zone, sample the white pixels of the door numbers, set the **Numbers** layer as the active layer, click the gold lock button. Pick **gloss_clean** with white. Tolerance around 25.
4. **Zone 3: Stripes.** Add a zone, sample any stripe color, lock to the Stripes layer, pick **chrome_mirror**. Tolerance around 30.
5. **Reorder.** Drag the zones so Numbers is at the top, Stripes in the middle, Body at the bottom. Numbers wins where it overlaps stripes; stripes win over body.
6. RENDER.

Look at the result. Three distinct materials — gloss blue body, gloss white numbers, mirror chrome stripes — each correctly scoped to its part of the truck. No hand-painting. No masking by hand. Just zones doing their job.

---

## Troubleshooting

**My zone is painting where I don't want it.** First check the layer lock — is the zone bound to a layer? The badge on the zone card shows it. If not, click the gold button. Second, check the alpha threshold (above) and tolerance — too-loose tolerance picks up unrelated pixels.

**My zone isn't painting anything.** Three causes, in order of likelihood: (1) higher-priority zone is covering it — drag this zone above the others; (2) the color match is too tight — raise tolerance; (3) you locked it to the wrong layer — check the badge, re-lock if needed.

**The gold lock button is grayed out.** You haven't selected a zone OR you haven't selected a layer. Both are required. Click a zone in the left panel, click a layer in the right panel, then the button activates.

**Two zones are fighting and the result flickers between renders.** Equal priority. Drag one above the other in the zones panel to make priority unambiguous.

**I want a zone to cover everything *except* one part.** Use a `Remaining` zone for the everything, and put a higher-priority zone over the part you want to exclude with a different color or finish.

---

## Next up

[Tutorial 4 — Finishes Deep Dive](04_finishes_deep_dive.md). You've been picking finishes from a list. Now we'll go through every category — bases, patterns, monolithics, and spec patterns — so you know exactly what each one does and when to reach for it.
