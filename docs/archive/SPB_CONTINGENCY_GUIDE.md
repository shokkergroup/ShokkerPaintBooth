# SPB Contingency Decal Guide

Contingency decals are the small grids of sponsor logos that sit on a race car's b-pillar, quarter panel, sidepod, or rear wing endplate. They are not the primary sponsor block — those get hood, door, and primary canvas placement — but they are arguably more interesting to design, because the constraints are tighter and the rules are unwritten. This guide walks through what contingency decals are, why they matter, how the common stack arrangements work, what size and spacing rules to follow, and how Shokker Paint Booth automates the layout work.

## What contingency decals are

A contingency sponsor is a company that pays a driver or team a bonus when specific results happen — a podium, a class win, a fastest lap. In exchange the team carries the sponsor's logo on the car. Because contingency programs are pay-for-performance rather than pay-for-placement, the logos get smaller, less prominent slots than primary sponsors. They are usually packed together in a tight grid called a contingency stack.

A typical NASCAR Cup car carries between six and twelve contingency logos on the b-pillar, plus another four to eight on the rear quarter panel. A GT3 endurance car may carry sixteen or more, distributed across multiple stacks. The total number of contingency logos on a top-level car is often higher than the number of named primary sponsors — the contingency stack is where the long tail of sponsor relationships lives.

## Why contingency decals matter

For the team, contingency decals matter because the bonus money adds up. For the livery designer, they matter because the stacks are *visually load-bearing* — they fill negative space, balance the composition, and signal that this is a real race car rather than a rendered concept. A livery without contingency stacks looks like a video game car. A livery *with* well-aligned, visually consistent contingency stacks looks like a livery that ran at Daytona last weekend.

Real racing tradition treats the b-pillar contingency stack the way a NASCAR fan treats a stat line. The stack is read from top to bottom; the topmost logos signal the most prestigious contingency relationships. Misaligning the stack, mixing logo aspect ratios badly, or leaving uneven gaps reads as amateurish to a knowledgeable viewer.

## Common stack arrangements

There are three canonical layouts: vertical, horizontal, and grid.

### Vertical stack

The classic NASCAR b-pillar — six to twelve logos stacked top to bottom, each cell typically 4% of UV width by 1.8% of UV height. Logos must be normalized to a consistent height; logos that come in widely different aspect ratios are letterboxed to fit. Spacing between rows is about 4 pixels at native resolution.

Vertical stacks fit narrow body zones — pillars, sail panels, the aft edge of a wheel arch. They are read top to bottom, so the most prestigious logo goes at the top.

### Horizontal cluster

NASCAR quarter panel layout — four to eight logos in a horizontal row, slightly larger than vertical-stack logos (5% UV width, 2.5% UV height). Spacing is more generous (6 pixels). The cluster reads left to right.

Horizontal clusters fit wide body zones — quarter panels, lower doors, splitter top edges. They are visually heavier than vertical stacks and serve as a secondary anchor point in the composition.

### Grid

GT3 endurance and LMP acrylic panels — multi-row, multi-column arrangements with eight to sixteen logos. Cells are slightly smaller than horizontal clusters (3.5% UV width, 2% UV height) because the grid packs more density. Spacing tightens to 3 pixels to maintain visual cohesion.

Grids fit large flat panels — door panel lower edges, acrylic side windows, rear wing endplates on prototypes. They are the most space-efficient layout but also the most demanding to align correctly.

## Size considerations

Contingency logos are *small*. The typical NASCAR b-pillar logo is about 1.8% of UV height — at a 4096px UV map, that's roughly 73 pixels tall. At broadcast resolution, the logo occupies about 30 pixels of screen height. That is barely enough for a wordmark to be readable; pure logo marks (no text) work better at this size.

The temptation when designing a contingency stack is to make the logos bigger so they read better. Resist it. A stack with logos that are too large stops looking like a contingency stack and starts looking like a row of mid-tier sponsors. The visual code matters: viewers know what a contingency stack is supposed to look like, and breaking the convention undercuts the realism of the livery.

Conversely, logos that are too small disappear entirely on broadcast. The sweet spot is 1.5-2.5% of UV height for vertical stacks, 2-3% for horizontal clusters, 1.8-2.2% for grids.

## Logo aspect ratio preservation

Real-world sponsor logos come in every aspect ratio imaginable — square (Goodyear), wide (Sunoco), tall (oil bottle shapes), irregular (custom marks). The contingency stack needs to display all of them at consistent visual weight without distorting any of them.

Two strategies handle this:

**Letterbox.** Fit each logo into a uniform cell, with the logo centered and scaled to fit the smaller of the cell's dimensions. Empty space surrounds wide logos vertically and tall logos horizontally. This preserves logo proportions perfectly but produces uneven visual density across the stack.

**Width-normalize.** Scale each logo to a uniform width and let the height vary. This produces consistent left-right alignment but creates uneven row heights, which fights the grid feel.

SPB defaults to letterbox because preserving logo aspect ratios is more important than perfect grid uniformity. Sponsors care about their logos looking right; viewers won't notice slight gaps. The Booth offers a width-normalize toggle for users who prefer the alternate look.

## Color uniformity vs variety

There are two schools on contingency stack color treatment:

**Monochrome.** Every logo is converted to a single color (usually white or black) so the stack reads as a unified visual element. This is the modern Formula 1 approach — sponsors are rendered in a color that matches the team livery. It looks clean but reduces sponsor visibility.

**Full color.** Every logo retains its original brand colors. This is the NASCAR approach. The stack reads as a riot of color, each sponsor distinct. It looks cluttered but sponsors love it because their brand identity stays intact.

Most series trend toward full color for contingency, monochrome for primary sponsors. The reasoning is that a primary sponsor's brand is already established by the rest of the livery; the contingency stack is the only place where lesser-known brands get visual identity.

SPB defaults to full color and offers a monochrome toggle. The toggle applies to the entire stack at once — partial monochrome (some logos color, others mono) looks broken.

## Stack alignment (vertical vs horizontal)

Vertical and horizontal stacks behave differently in the Booth's alignment engine.

**Vertical stacks** are anchored at the top edge of the highest logo. Subsequent logos are placed below at the configured spacing. The stack grows downward as logos are added. The bottom edge is unconstrained — it ends wherever the last logo lands.

**Horizontal stacks** are anchored at the left edge of the leftmost logo. Subsequent logos place to the right at the configured spacing. The stack grows rightward. The right edge is unconstrained.

**Grids** have two anchors — top-left of the first logo, and the column count. The grid grows downward and rightward. Both edges are unconstrained until the configured maximum cell count is reached, at which point the grid wraps.

Anchor points matter when a stack lands on a curved body surface. Vertical stacks deal with body curvature better than horizontal because pillars are usually straighter than quarter panels. Horizontal stacks on heavily curved surfaces need each logo individually warped to follow the surface — SPB does this automatically using the body's UV unwrap, but the result is sometimes uneven.

## Spacing guidelines

Spacing affects how the stack reads at distance. Tight spacing makes the stack look like a single block; loose spacing makes individual logos pop.

| Stack type | Recommended spacing |
|------------|---------------------|
| Vertical b-pillar | 3-5 pixels |
| Horizontal quarter | 5-8 pixels |
| Grid endurance | 2-4 pixels |
| Horizontal floor strip | 6-10 pixels |
| Vertical sidepod | 4-6 pixels |

These are at native UV resolution (typically 4096px). At lower export resolutions the spacing scales proportionally. SPB enforces a minimum 1-pixel spacing at any export size to prevent logos from touching.

## B-pillar placement (the most common location)

The b-pillar — the body member between the front and rear doors — is the canonical contingency stack location. It's narrow, vertical, perfectly suited for a 6-12 logo stack. It's also visually neutral; the b-pillar is usually painted a single solid color, so the stack pops without competing visual elements.

Place the stack centered on the pillar's vertical axis. Top of the stack should sit just below the roof rail (about 8% of UV height down from the roof line). Bottom of the stack ends naturally based on logo count.

If the team's livery includes a stripe or graphic that crosses the b-pillar, the contingency stack typically sits below the stripe — never on top of it. The stripe is the brand element; the contingency is utility.

## Quarter panel placement

The quarter panel — the rear-fender area between the rear wheel arch and the rear bumper — is the second most common contingency location. It's wider and shorter than the b-pillar, suiting a horizontal cluster or small grid rather than a vertical stack.

Place the cluster above the wheel arch, below the beltline (the visual line where the windows meet the body). On most race cars there's a 15-20% UV-height band between the arch and the beltline that's perfect for contingency.

If the livery has a swooping graphic that crosses the quarter panel, contingency sits *below* the graphic, never on top. Same rule as the b-pillar.

## Pre-made contingency packs vs custom

SPB ships with eight pre-made contingency stack templates (see `decals/contingency_stacks.json`). Each template defines layout, spacing, cell size, and alignment for a specific stack location and racing class. Drop the template onto a body zone and the Booth applies all the defaults; you only need to fill in the actual logo art.

Custom stacks are also possible. The Stack Builder tool lets you define:
- Layout (vertical/horizontal/grid)
- Cell count (min and max)
- Cell size in UV units
- Spacing in pixels
- Anchor point
- Color treatment (full color / monochrome / letterboxed)

Custom stacks are saved as user presets and become available alongside the shipped templates.

## Series-specific contingency conventions

Each major racing series has unwritten rules about contingency stacks:

**NASCAR.** B-pillar vertical stack of 8-12 logos. Quarter panel horizontal cluster of 4-6 logos. Both at full color. The b-pillar stack is mandatory in Cup; teams without enough sponsors place "house" decals in unused slots to fill the stack visually.

**IMSA / SRO GT3.** Door panel lower edge grid of 8-12 logos. Often paired with a vertical stack on the front fender for class-specific suppliers (tire, brake, fuel). Color treatment varies by team — some teams monochrome to match the livery, most full color.

**FIA WEC / Le Mans.** Front fender vertical stack and rear quarter horizontal cluster. Logo count is high (12-16 per stack) because endurance racing has more contingency programs. Color is full at all levels except top-class Hypercar, where some teams monochrome.

**F1.** Floor edge horizontal strip of 4-7 logos, very tightly spaced. Almost always monochrome to match team livery. The strip is one of the only places non-title sponsors appear on a modern F1 car.

**IndyCar.** Sidepod aft section vertical stack, 5-8 logos. Full color. Slightly larger than NASCAR contingency because the sidepod is closer to the camera angles used for oval racing telecasts.

**Dirt Late Model / Sprint.** Quarter panel horizontal cluster of 3-6 large logos. Few but visible — viewing distance is short, dust is heavy, fewer well-placed logos beat many tiny ones. Color is full and bright.

**Vintage / Historic.** Lower door horizontal strip of 3-5 logos with generous spacing. Reflects the era — no team had 12 contingency sponsors in 1965. Period-correct color and slight intentional misalignment add authenticity.

## Common mistakes

The most common contingency stack mistakes Booth users make:

1. **Logos too large.** The stack stops reading as contingency and starts reading as a row of badly-placed primary sponsors.
2. **Inconsistent cell sizes.** When letterbox is off and width-normalize is also off, each logo lands at its native size. The stack looks like a junk drawer.
3. **Ignoring body curvature.** Placing a horizontal cluster on a heavily curved quarter panel without warping each logo to follow the surface.
4. **Stack on top of livery graphic.** A swooping team graphic crosses the b-pillar; the contingency stack lands on top of it. Both elements lose impact.
5. **Asymmetric stacks.** The driver-side b-pillar gets a 12-logo stack; the passenger-side gets 6. Real race cars carry identical stacks on both sides.
6. **Wrong anchor.** Vertical stack anchored at the bottom rather than the top, so adding logos pushes the stack upward into the roof rail.

SPB warns about most of these, but the warnings can be suppressed for users who know what they're doing.

## Practical workflow

A typical contingency pass takes about five minutes:

1. Choose a stack template that matches the body zone you're filling. The picker filters templates by zone.
2. Drop the template onto the zone. SPB places it at the canonical anchor for that zone.
3. Drag-drop logo art (PNG, SVG, or imported brand kit) into each cell. The Booth scales each logo to fit using the configured letterbox or width-normalize setting.
4. Mirror the stack to the opposite side using the "Mirror Stack" button. Real cars carry symmetric stacks; the mirror operation copies the entire stack including order.
5. Adjust spacing if the stack feels too tight or too loose for the body zone. Default values work for most cases.
6. Lock the stack to the Sponsors layer to prevent accidental edits during the rest of the livery work.

That's it. The Booth handles alignment, scaling, mirroring, and layering automatically; the user provides the logo art and the design intent.
