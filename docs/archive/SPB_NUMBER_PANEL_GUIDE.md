# SPB Number Panel Guide

Number panels are the largest single piece of livery design that *must* be readable, *must* fit a body shape it wasn't drawn for, and *must* obey rules that vary by series. This guide walks through everything Shokker Paint Booth knows about putting numbers on cars: what a panel is, what each major series demands, how to handle visibility, how the Numbers PSD layer interacts with zones, and what stylistic choices separate amateur liveries from competition-grade ones.

## What a number panel is

A number panel is the assembled graphic that shows a car's competition number — the digits themselves plus any background fill, outline stroke, drop shadow, class abbreviation, and surrounding bezel. In SPB terminology, the panel is everything that lives inside the bounding box reserved for the number on the body. The Booth treats the panel as a single placement unit even when its constituent parts are individually editable.

Panels exist because raw digits floating on a livery rarely read well. A black "24" on a navy car disappears from grandstand distance. A white "3" on a yellow nose cone bleeds into the background under stadium lights. The panel — fill, stroke, and shadow combined — is what guarantees the number stays legible across body color, lighting, and viewing distance.

## Series-specific requirements

Different sanctioning bodies have wildly different ideas about how a number should look.

### NASCAR (Cup, Xfinity, Truck)

Stock car series want bold, blocky numbers that read at 200mph from a TV camera 400 yards away. Door panels are the primary placement, with a mandatory roof number for spotters. The standard recipe is a heavy block typeface (Impact, Arial Black, or a proprietary team font), an 8-pixel black stroke, and a hard 4-pixel drop shadow offset down and right. Two-digit numbers are the norm; three-digit numbers (100s and up) require slightly tighter letter spacing to fit the same panel.

### GT3 (IMSA, SRO, Blancpain heritage)

GT3-class sports cars favor cleaner, smaller numbers inside roundels (circular discs) or rectangular contrast panels. The disc fill color often encodes class — yellow for GTD, white for GT4, red for top-class GTP/Hypercar. The number itself is usually Helvetica Bold or Univers, no drop shadow, with a thin 3-4 pixel black stroke for separation. Most GT3 sanctioning bodies mandate a 30mm clear zone around the digits with no other graphics allowed inside it.

### Formula 1

Modern F1 numbers are stylistic rather than regulatory in their typeface — drivers are encouraged to use a personal font or logo as their number. They are tiny: roughly 5% of UV width on the nose cone, and about 9% on the engine cover for helicam visibility. Stroke is usually a 1-2 pixel team-color outline, never black on black. There are no drop shadows because the surface curvature provides natural shading.

### IndyCar

American open-wheel sits between F1 and NASCAR — bigger and bolder than F1 but not as block-heavy as NASCAR. Numbers go on the sidepod intake (mirrored both sides) and on the airbox for top-down camera ID. Heavy 6-pixel stroke, moderate drop shadow, often paired with a team-color outline ring. Three-digit numbers are rare; the most common range is 1-99.

### LMP / Hypercar

Le Mans Prototypes carry a class indicator above the number — "P1", "P2", "LMP3", or "Hypercar" depending on the era and class. The class abbreviation sits in a colored bar (red for Hypercar, blue for LMP2, orange for LMP3) directly above the digits. The combined panel is taller than it is wide, the opposite of most number panels.

### Dirt Late Model / Sprint Car

Saturday-night short-track racing wants the *biggest possible number* on the door — often spanning 22% of UV width. A 10-pixel stroke with a heavy 6-pixel drop shadow gives the digit grandstand readability through dust and low-quality stadium lighting. Many drivers commission custom-cut number art in a personal style; the digit becomes part of the brand identity.

### Vintage / Historic

Pre-1970s racing used hand-painted roundels — white discs with black digits in a period-appropriate sans (Futura, Gill Sans). No drop shadows, no aggressive strokes. SPB's vintage roundel preset uses an off-white cream background to feel period-correct rather than freshly-printed.

## Number visibility rules

Visibility is the single most important constraint on number panel design. A beautiful number that no spotter can read on lap 47 is a failure. Three rules dominate:

**Size.** A door number should be at least 12% of UV width for any series with TV broadcast coverage. Roof numbers for spotter visibility need 18% or more. Below 8% and the number disappears past 50 yards.

**Contrast.** The panel must contrast against the body color in *both* hue and value. A red number on a blue background satisfies hue contrast but fails value contrast — both colors carry the same lightness and bleed together at distance. Always check the panel in grayscale; if you can't read it monochrome, you can't read it at distance.

**Stroke.** A black stroke around the digits gives separation when body color is uncertain. The recommended stroke width is between 4 pixels (GT3) and 10 pixels (dirt late model). Anything below 3 pixels disappears at compression; anything above 12 pixels swallows the digit.

## Placement conventions

Door panels are the universal default. Most cars also need a roof number for aerial cameras and a windshield-banner location for the series identifier. F1 and IndyCar replace the door with a sidepod or nose location because their bodywork has no real door. LMP cars place the number where the bodywork allows on each iteration of the regulations — often on the front splitter side, the aft door region, and the rear wing endplate.

The most-overlooked placement is the *forward-facing* number. F1 mandates a nose number visible from a camera mounted on the car directly in front of the driver. NASCAR includes a hood number for tower cameras. GT3 endurance racing requires four-cardinal-angle visibility, meaning a number must read from front, rear, and both sides without occlusion.

## Custom number creation

SPB lets the user override the preset in three ways:

1. **Typeface swap.** Pick any installed font. The preset's `font_recommendation` is a stack — the Booth tries each in order and falls back to the next if the first isn't available.
2. **Style override.** Adjust stroke width, drop shadow offset, and color independently. The preset's defaults snap back if the user clears the override.
3. **Custom art.** Drop in a hand-cut SVG or PNG of the digits and bypass the type system entirely. Useful for dirt late model and sprint car liveries where the number is a brand mark.

When using custom art, the Booth still respects the preset's `typical_dimensions_uv` for placement bounds — the custom art is scaled to fit, not the preset to fit the art.

## Digit count considerations

A one-digit number sits too small inside a panel sized for two digits. A three-digit number gets cramped inside a panel sized for two. SPB scales the panel automatically based on digit count:

- **1 digit** — center the digit but inflate it 25% wider than the per-digit width of a 2-digit panel. A solo "7" on a NASCAR door looks weak otherwise.
- **2 digits** — the canonical case; presets are tuned for this.
- **3 digits** — tighten the letter spacing to -5% and shrink the stroke from 8 to 6 pixels so the digits don't merge.
- **0** — leading zeros are valid in some series (vintage, dirt) and forbidden in others (most modern road racing). Check the rule book.

## Roof number requirements

NASCAR requires a roof number sized at least 18% of UV width, oriented so spotters in the stands read it upright when the car is pointing away from them. This means the digits face *backward* relative to driving direction. SPB's `nascar_roof_panel` preset auto-flips the orientation; if the user creates a custom roof number from scratch, they need to remember the flip themselves.

GT3 and IMSA endurance racing also use roof numbers but allow either orientation. F1 has no roof number — the airbox number serves the same function.

## Mirror and door number alignment

When mirroring a livery across the car's longitudinal axis, the number panel must mirror with it. The mirror operation is *not* a simple horizontal flip of the digits — the digits stay readable, but the panel position flips. SPB handles this automatically: the `mirror_panel` operation on a number zone preserves digit orientation while flipping the placement.

A common amateur mistake is mirroring the entire panel including the digits, producing a backward-reading "42" on the passenger side. SPB warns when this happens, but the warning can be suppressed for stylistic purposes.

## Class number markers

Multi-class endurance racing requires a class indicator alongside the number. The conventions are:

- **P** — Prototype (LMP1, LMP2, LMP3, Hypercar variants)
- **G** or **GT** — Grand Touring (GTE, GT3, GT4)
- **L** — historically LMP, less used now

The class marker sits above the number in a colored bar matching class color. SPB's `lmp_class_panel` preset includes this stack; for GT3 the class color usually appears as a roundel fill rather than a separate bar.

## Stylistic vs regulatory numbers

Some numbers are mandated by the rule book — size, font, contrast, panel color, placement zones. Others are purely stylistic — drivers can choose font and color within wide bounds. The general rule:

- **Regulatory** — stock car (NASCAR), prototype (LMP, Hypercar), most national series
- **Mostly regulatory** — IndyCar, IMSA, FIA WEC
- **Stylistic** — F1, drift, drag racing, vintage, time attack

When in doubt, default to the more conservative regulatory style. A judge or scrutineer can disqualify a livery for a noncompliant number; nobody will reject a perfectly legible one.

## Working with the Numbers PSD layer

The Numbers layer is the third reserved layer in the SPB PSD stack, sitting between Sponsors (below) and Tape (above). When SPB renders a livery, the Numbers layer is composited near the top so panels are never occluded by sponsor art. The layer is unlocked by default but can be locked from the layers panel if you want to protect the panels while editing the rest of the livery.

The Numbers layer accepts:
- Vector type from the typography tool
- Imported SVG and PNG digit art
- Stroke, fill, and drop-shadow effects from the layer effects panel

The layer does *not* accept paint brushes, pattern fills, or overlay textures — those belong on the body paint layers below. This separation is enforced because Number panels need to render with crisp, anti-aliased edges; running them through the engine's pattern overlay would soften the digits.

## Locking zones to the Numbers layer

When you assign a zone to a number panel preset, SPB locks the zone to the Numbers layer. This means:

- The zone's color, stroke, and shadow can be edited in the Numbers layer panel
- The zone is excluded from body-paint operations (chameleon shifts, finish swaps, pattern overlays)
- The zone snaps to the preset's alignment guides

To unlock, right-click the zone and choose "Unlock from Numbers Layer." The zone reverts to a normal paintable region. This is rarely what you want — a paintable number panel is hard to keep readable across livery changes.

## Practical workflow

A typical number panel pass goes:

1. Choose a preset that matches the series being painted. The Booth offers a series filter in the panel picker.
2. Drop the preset onto the body. SPB places it at the canonical location for that preset and snaps to the body's actual door/sidepod cavity.
3. Type the digit(s). The preset's font, stroke, and shadow apply automatically.
4. Adjust contrast against the body color. SPB shows a live grayscale preview in the corner of the canvas to flag low contrast.
5. Mirror to the opposite side. The Booth offers a "mirror panel" button that handles orientation correctly.
6. Add the roof number if the series requires it.
7. Lock the zone to the Numbers layer to prevent accidental edits during the rest of the livery work.

Following this workflow gets you from blank body to legal, readable, broadcast-ready numbering in about three minutes per panel.
