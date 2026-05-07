# Shokker Paint Booth — League Administrator Guide

A complete guide for sim-racing league admins who want to run paint-compliant series using Shokker Paint Booth. Covers what a league config does, how to set one up, how to run livery review sessions, and how to keep consistency across a grid without burning out as an admin.

---

## What Is a League in SPB?

A "league" in SPB is any community that wants their drivers to show up looking coordinated. That could mean:

- A weekly iRacing league with shared contingency decals.
- A monthly Rocket-League-style arena league with team-color schemes.
- A one-off special-event series (endurance race, invitational) where every car must share a windshield banner.

SPB's league system gives admins tools to encode rules, distribute templates, and approve liveries without manually checking every pixel.

## Why Standardize a League's Look?

Inconsistent liveries read as unprofessional on broadcast. Even the best driving gets undercut by a grid where half the cars have a championship-ready paint and the other half look slapped-together. Standardization doesn't mean forcing identical cars — it means setting a baseline: contingency decals present, windshield banner attached, numbers readable, color palette cohesive.

The league that standardizes looks more like a real racing series. That attracts better drivers, better sponsors, and better broadcast numbers.

## The League Config JSON — Field-by-Field

Open `leagues/league_template_config.json` in any text editor. Each field has a purpose. Here's how to decide what to put in each one.

### `league_name`, `league_slug`, `season`, `series_tier`
Identity fields. `league_name` is display text. `league_slug` is a URL-safe lowercase identifier used in filenames. `season` distinguishes spring/summer/fall/winter seasons. `series_tier` lists the class of car.

### `regulations_url`
Where drivers read your full non-visual rules (contact rules, pit rules, etc.). SPB links to this from the league panel.

### `contact.admin_email` and `contact.discord_channel`
Two contact paths. Drivers use Discord for fast turnaround, email for appeals.

### `required_zones`
The heart of the config. Every object in this array is a zone that must be filled on every submitted livery. Specify the layer (where on the car), minimum size, whether it's approval-required, and whether you supply an asset pre-built.

Common required zones:
- **Windshield banner** — league logo or broadcast graphic.
- **B-pillar contingency stack** — league-wide sponsor decals.
- **Door primary sponsor** — driver's chosen sponsor.
- **Roof stripe** — series title-sponsor wordmark.

### `approved_bases` and `banned_bases`
Two lists. The approved list is whitelist. The banned list is blacklist for anything that would otherwise be allowed. Wildcards work (`mortal_shokk_*` bans every variant of the Mortal Shokk family).

Common banned-base patterns for professional-feeling leagues:
- `mortal_shokk_*` — too chaotic for broadcast.
- `damage_wear_*` — intentional damage reads unprofessional.
- `neon_underground_*` — too intense for heritage series.

### `approved_patterns` and `banned_patterns`
Same pattern for patterns. Heritage series ban glitch and digital-camo patterns. Stock-car series usually allow flames and pinstripes. GT series lean minimalist.

### `color_palette`
Either pick a preset (`racing_classic`, `modern_gt`, `heritage_luxury`, `tuner_aggressive`) or define your own with `allowed_colors` and `banned_colors` lists.

Tighter palettes = stronger visual cohesion. Looser palettes = more driver expression. Pick based on your league's personality.

### `number_style`
How race numbers appear:
- `preset` — use a pre-built preset or `custom`.
- `font` — bold upright, bold italic, modern stencil, retro block.
- `fill_color` — `driver_choice` or lock to a specific color.
- `outline_color` — same.
- `minimum_height_pixels` — ensures numbers are readable on broadcast.
- `placement` — where numbers appear on the car.

### `contingency_stack`
Supply a pre-built `.shokker` file with the stack laid out exactly as it must appear. Set `"locked": true` so drivers cannot edit the stack. This is how you protect sponsor layout.

### `naming_convention`
A format string with placeholders. SPB auto-names exports that match, and rejects exports that don't. `<driver_last>_<car_number>_<season>.shokker` is a good default.

### `submission`
Deadline, channel, review turnaround, revision policy. Set `approval_required_before_qualifying: true` to block drivers from entering a session if their paint hasn't been approved.

### `penalties_for_non_compliance`
An array of violation-and-penalty pairs. SPB surfaces these in the validator so drivers know the stakes before they submit.

### `optional_features`
Flexibility toggles:
- `allow_driver_custom_primary_sponsor` — let drivers pick their own sponsor or not.
- `allow_helmet_crossover_from_livery` — allow reusing the livery's colors on the driver's helmet.
- `allow_custom_monolithic_bases` — for leagues that allow one-off custom bases.
- `allow_personalized_damage_wear` — for themed weeks (dirt track, weathered).

### `template_liveries_provided`
Starter templates drivers can import and modify. Supply at least three: a clean version, a split-color version, and a minimalist version. Drivers who start from a template build faster and more consistently.

## The League Setup Workflow (First Time)

**Step 1 — Gather requirements.**
Before touching the config: what's your series identity? What palette? How strict vs. loose? Write a one-paragraph brand brief before editing JSON.

**Step 2 — Copy and fill the template.**
Duplicate `leagues/league_template_config.json`. Replace every `example_` value. Save under your league slug: `your-league-2026-spring.json`.

**Step 3 — Build the asset bundle.**
Collect or create:
- League windshield banner PNG (1024x128 typical).
- Contingency stack `.shokker` file built in SPB.
- Series title-sponsor roof PNG.
- At least three template `.shokker` liveries.

**Step 4 — Zip and distribute.**
Package the config + assets into a zip. Share on Discord (pinned message in `#livery-submissions`), GitHub release, or your league website.

**Step 5 — Announce.**
Post a walkthrough: how to import the config, where to find templates, how to submit. Link new drivers to the SPB onboarding docs.

## Running a Weekly Livery Review Session

Livery review is the weekly admin ritual that keeps a league's look tight. Plan a 30-minute block every Thursday (or whatever your deadline is) to review all submissions.

**Before the session:**
- Submissions close at 11:59 PM the night before.
- Admin opens all submitted `.shokker` files in SPB's review mode (File → Open Batch).
- SPB runs the league validator against each file. Red = fails. Yellow = warning. Green = approved.

**During the session:**
- Click through each red file, read the validator error, either fix in-place (admin privilege) or message the driver.
- Click through each yellow file and make a call: approve with note, or reject.
- Approve greens without opening them unless you want to.

**After the session:**
- Post the approval list in the Discord channel.
- Post rejection messages with clear reasons (missing zone, banned base, etc).
- Give drivers a revision window before the race.

## Paint Approval Process — Practical Tips

- **Turn around fast.** 24 hours max. Drivers who wait three days stop submitting.
- **Give reasons, not verdicts.** "Rejected" is cheap. "Rejected — B-pillar contingency stack missing, please drop in `contingency_stack.shokker` from the league assets and resubmit" is actionable.
- **Use a second pair of eyes for close calls.** Two admins agreeing on an edge case is better than one admin making a unilateral call that looks arbitrary.
- **Log your calls.** Keep a changelog so precedent is visible: "W5: approved metallic purple because it was in-palette. W7: approved metallic purple+candy clearcoat. W8: rejected purple with holographic flake — too intense for broadcast."
- **Be gentle with new drivers.** Their first livery will break rules. Help them fix it rather than punishing them.

## Shared Sponsor Decal Packs

Most pro-feel leagues run shared sponsor decals — the same brand logos appear on every car in the series. Build these once and distribute.

**Process:**
1. Get permission from brand holders if using real brand artwork. Most leagues use original "fictional-brand" artwork instead — it's safer.
2. Build the decal pack as `.shokker` snippets that can drop onto any car.
3. Supply size guidelines so decals render consistently across cars.
4. Update quarterly as sponsors rotate.

## Contingency Stack Standardization

The contingency stack is the pillar of sponsors on the B-pillar or quarter panel. Standardization is critical:

- Admin builds the stack once as a locked `.shokker` file.
- Every driver drops the stack onto their car unchanged.
- Stack file is versioned — `contingency_stack_v1.shokker`, `contingency_stack_v2.shokker`.
- When sponsors rotate, push `v2` with a Discord announcement.

SPB's stack-lock feature prevents drivers from accidentally editing the stack. This is the single biggest league-consistency win — use it.

## Penalties for Non-Compliance

Have them written down. Don't improvise. Here's a starter penalty model:

- **First offense missing required zone:** Warning; 24hr window to fix; race as submitted.
- **Second offense same issue:** Forced to use previous approved livery for the race.
- **Using banned base:** Livery rejected; no race entry until fixed.
- **Modifying locked contingency stack:** Automatic rejection.
- **Out-of-palette color:** Warning first offense, rejection second.

Penalties should be visible in the league regulations page. Drivers should never be surprised by a penalty.

## Template-Based League Look

Templates are how you get week-one rookies to look as good as week-40 veterans. Build three templates minimum:

1. **Clean Template** — a base body color with one centerline stripe. Drop in numbers and sponsors. Beginner-friendly.
2. **Split Template** — two-color split down the centerline. More visual but still simple.
3. **Minimalist Template** — a solid body color with a single accent. For drivers who want their helmet and skill to do the talking.

Every template ships with the required zones pre-filled. Drivers can always build from scratch, but templates are the safety net.

## Running a Multi-Series League

If your league runs multiple series (Open-wheel + GT3 + Truck, say), each gets its own config JSON and asset bundle. Naming:

```
your-league-openwheel-2026-spring.json
your-league-gt3-2026-spring.json
your-league-truck-2026-spring.json
```

Drivers switch between active configs using SPB's league selector. Shared assets can live in a common folder across all three configs.

## Seasonal Refresh Checklist

At the start of each season:

- [ ] Update `season` field.
- [ ] Refresh title-sponsor roof stripe asset.
- [ ] Review banned bases — has SPB added any new variants that should be blocked?
- [ ] Review palette — swap in a new accent color for the season if you want a visual marker.
- [ ] Update template liveries with the new season's assets.
- [ ] Publish changelog so drivers know what's different.
- [ ] Re-zip and distribute.

## Getting Help

- **SPB Discord #leagues channel** — hundreds of admins across many series share tips.
- **SPB Support** — for tool-level questions about the config schema or validator.
- **Community examples** — check `leagues/examples/` for real-world configs contributed by other leagues (anonymized).

---

Running a league is a real commitment. The tools exist to make it manageable — enforce rules once in the config, distribute templates, approve weekly, iterate quarterly. A well-run league lasts years. Build your rules to be sustainable from the start.
