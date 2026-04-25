# Tutorial 8 — Recipe Workflow

**Estimated time:** 8 minutes
**Prerequisites:** [Tutorial 4 — Finishes Deep Dive](04_finishes_deep_dive.md)
**Skill level:** Intermediate.

A **recipe** in SPB is a saved preset — a complete set of zones, layer bindings, colors, finishes, and effects — that you can apply to any compatible template. Think of it as "livery DNA": the visual formula for a specific look, independent of which specific truck or car it lives on. SPB ships with a recipe library and makes it easy to import, customize, and save your own.

## What you'll learn

- Where the recipe library lives and what's in it
- How to import a recipe into your current project
- How to customize the colors while keeping the livery structure
- How to save your customizations as a new recipe
- How to share recipes with teammates

---

## Step 1 — Browse the recipe library

Recipes live in two places:

- **Bundled library** — ships with SPB, in the `recipes/` folder inside the app install
- **User library** — your own recipes, stored in `Documents\Shokker Paint Booth\recipes\`

Open the Recipe Browser via `File → Recipes → Browse Library` (or `Ctrl+R`).

![Step 1 — Recipe browser](docs/img/tutorial-08-step1.png)

You'll see a grid of recipe cards. Each card shows:

- A thumbnail preview
- The recipe name (e.g., "NASCAR Classic," "JDM Drift," "F1 Retro")
- The tags / categories
- The author
- The date created

The bundled library has around 30 recipes covering common livery archetypes — classic stock car, modern NASCAR, sports car racing, drift culture, retro F1, GT3, rally, custom street. Good starting points for your own work.

## Step 2 — Preview a recipe

Hover any card. A larger preview pops up with all angles of the livery rendered on a stock chassis. If the preview looks like what you want, click **Preview in Project**.

SPB applies the recipe's zones and finishes to *your current truck* in a non-destructive preview mode. Your existing zones are still there — the preview is just temporary.

Hit `Esc` to cancel the preview without applying. Hit **Apply** to commit the recipe to your project.

## Step 3 — Import NASCAR Classic

Let's walk through a real example.

1. Open the Recipe Browser.
2. Find **NASCAR Classic**. Click **Preview in Project**.
3. Your Silverado transforms into a classic stock-car-style livery: large body color, white horizontal stripe across the middle, big black door numbers, a few placeholder sponsors.

![Step 3 — NASCAR Classic preview](docs/img/tutorial-08-step3.png)

4. Hit **Apply** to commit.

Now look at your Zones panel — you have a full set of zones (maybe 6-8) that the recipe created. Everything is named clearly: "Body," "Centerline Stripe," "Door Numbers," "Hood Number," etc.

## Step 4 — Customize the colors

The recipe gave you structure. Now personalize it. Every zone in the recipe is a normal zone — you can edit it like any zone you built yourself.

Click the **Body** zone. Change its color. Say, from default red to a deep blue (`#0E2C5C`). The truck body updates immediately.

Click the **Centerline Stripe** zone. Change the color to bright yellow (`#FFD60A`).

Click each door number zone and change the number color to something that contrasts with the new body.

You've just reskinned a full NASCAR-style livery in 30 seconds. No zone wiring, no layer binding, no finish picking — the recipe did all of that; you just picked palette.

## Step 5 — Customize the finishes

Same deal for finishes. Click any zone's finish slot and pick a new base or pattern.

Common customizations:

- Body from `gloss_clean` to `candy_apple` for a juicy deep-gloss feel
- Numbers from `gloss_clean` to `chrome_mirror` for a flashy reflective number
- Stripes from solid to `chameleon` pattern for color-shift

Each swap respects the recipe's structure — you're only changing the finish on an existing zone, not rewiring anything.

## Step 6 — Save as a new recipe

Happy with your customization? Save it as a new recipe for future reuse.

1. `File → Recipes → Save Current as Recipe`.
2. Enter a name (e.g., "Blue/Yellow NASCAR 2026").
3. Tag it (recipes support multi-tag — "nascar, retro, blue, yellow" is fine).
4. Optionally add a description and author name.
5. Click **Save**.

The recipe is written to your `Documents\Shokker Paint Booth\recipes\` folder as a JSON file (or `.spb-recipe` with the same contents). It now appears in the Recipe Browser alongside the bundled library.

## Step 7 — Share a recipe with teammates

Recipe files are portable. To share:

1. Open `Documents\Shokker Paint Booth\recipes\`.
2. Find your `.spb-recipe` file (it has the name you gave it).
3. Send it to your teammate via Discord, email, or any file share.
4. Teammate drops it into their own `Documents\Shokker Paint Booth\recipes\` folder.
5. Teammate opens SPB — your recipe appears in their Recipe Browser.

Recipes are designed to be template-agnostic within reason. A recipe built on the Silverado will apply to the Ford F-150 template too, because SPB matches zone bindings by layer *role* (e.g., "Numbers" layer) not by specific coordinates. Cross-series recipes (Silverado recipe on a GT3 car) work less perfectly because the layer sets are different — SPB will apply what it can and flag the rest.

## Step 8 — Recipe vs. project save

Two save systems, different purposes:

- **Project save** (`Ctrl+S`, `.spb` file) — saves *this specific* paint file with all its pixel-level paint, mask data, and zone state. Locked to the current template.
- **Recipe save** (`File → Recipes → Save Current`) — saves only the *zone recipe* (colors, finishes, bindings, effects). Template-agnostic. Small file.

Use project save for "this is my current work-in-progress." Use recipe save for "this is a reusable design formula."

---

## Try it yourself

Build a recipe from scratch by customizing an existing one:

1. Open the Recipe Browser. Pick **JDM Drift** (or any recipe that interests you).
2. Apply it to the Silverado.
3. Change the body color to your favorite hue.
4. Swap one pattern — try carbon weave at 40% strength if the recipe didn't have carbon.
5. Adjust one sponsor placement using the Move tool.
6. `File → Recipes → Save Current as Recipe`.
7. Name it "My Custom [Year]."
8. Re-open Recipe Browser. Confirm your recipe appears.

Now try applying it to a *different* template — if you have a sports car template loaded, your recipe should transfer most of the zones automatically.

---

## Troubleshooting

**Preview doesn't show anything when I hover a recipe.** Preview generation happens the first time and caches. Wait a second or two, or click the card once to force load.

**Apply produced a bunch of empty zones.** The recipe was built for a different template with layers that don't exist on your current template. SPB applies what it can and lists the missing layers in a dialog. Either (a) manually rebind the empty zones to relevant layers on your template, or (b) delete the empty zones and rebuild just those sections.

**My custom recipe doesn't show up after saving.** Close and reopen the Recipe Browser — it scans the folder at open. If still missing, verify the file is in `Documents\Shokker Paint Booth\recipes\` and has a `.spb-recipe` extension.

**Sharing a recipe with a teammate, they can't see it.** Check that they dropped the file in the correct folder (`Documents\Shokker Paint Booth\recipes\`, not `Program Files\...`). The `Documents` path is per-user and required.

**Applied a recipe and lost my original zones.** Recipes by default replace zones. To *merge* instead, hold `Shift` while clicking Apply in the Recipe Browser. Merged recipes keep your existing zones and add the recipe's zones on top.

---

## Next up

[Tutorial 9 — Advanced Tools](09_advanced_tools.md). You've been using the basic drawing tools. Next we open the drawer for brush stabilizer, smart guides, snap-to-pixel, and the specialty tools — smudge, clone stamp, dodge, and burn — that unlock pro-level detail work.
