# How Shokker Paint Booth Pro works (AI knowledge card)

## The big idea: paint file in, zones decide the look
The buyer opens their car's paint file (a flat, unwrapped 2048x2048 picture of the whole car: left side, right side, hood, roof, front, rear laid out as separate islands). Shokker turns it into a finished iRacing paint + a "spec map" that controls how shiny/metallic/rough every pixel is. The look is decided by ZONES. The paint canvas is flat, so "left/right/top/bottom" mean the flat picture, not the car. The grid A-H (columns, left to right) by 1-8 (rows, top to bottom) is how the copilot talks about places.

## What a zone is
A zone = (which pixels it covers) + (a look for them). The look = a base material (gloss, matte, satin, chrome, candy, pearl, metallic, ...) OR a monolithic special finish (a complete exotic look), a colour mode (keep the paint's own colour / solid colour / gradient / the finish's own colour), optional pattern on top, optional spec patterns (change the shine/metal/roughness texture), an optional second base blended over the first, intensity, and spec-channel shifts.

## Which pixels a zone covers (the REGION)
- By paint colour: one or several picked colours with a tolerance (6-100; 30-50 is normal). Every pixel on the paint close to that colour belongs to the zone. Anti-aliased edges need a bit of tolerance.
- By PSD layer: restrict the zone to pixels that exist on chosen layers (Numbers, Sponsors, Car Paint, ...). Colour + layer together = "that colour, but only on that layer".
- By a box: limit the zone to a rectangle of the canvas (cells like B3:D5). Colour + box = "that colour, only inside the box".
- Catch-alls: "Remaining" = everything no zone above it claimed (the classic body zone, always at the bottom). "Everything" = every pixel (combine with a layer or box to make it precise).

## PRIORITY: the top zone wins
Zones are a stack. Position 1 (the TOP of the list) has the highest priority: where two zones select the same pixel, the higher one gets it, the lower one gets nothing there. So a new zone that must show on pixels another zone already selects has to be placed ABOVE it (the copilot places new zones at the top by default). A "Remaining" zone belongs at the bottom. If a zone "does nothing", the usual reasons are: a zone above already claims those pixels; its colour tolerance is too tight; it is bound to the wrong layer; it is muted; intensity is 0.

## Colour modes (what colour the finish paints)
- source: keep the car's own paint colour, only change the shine/spec (great for gloss/matte/satin/pearl/candy over an existing livery colour).
- solid #rrggbb: paint the whole zone that colour.
- gradient: 2-10 colour stops blended across the whole canvas in a direction (horizontal left-to-right, vertical top-to-bottom, diagonal_down, diagonal_up, radial from the centre, angular around the centre). The gradient runs over the entire 2048x2048 canvas, so a horizontal gradient changes colour with the canvas column, not along the car's length. Because the car is unwrapped, several islands share the same columns; to fade each side of the car separately, use one zone per side (region box) with its own gradient.
- finish: the finish brings its own colour (chrome, carbon, holographic, ...).

## Strengths and adjustments
- intensity 0-100: overall strength of the whole zone.
- base_strength 0-200%: how much of the finish replaces the original paint (100 = full; lower = show more of the original paint).
- spec_strength 0-200%: overall strength of the shine/metal map.
- hue -180..180, saturation -100..100, brightness -100..200: tweak the base colour.
- scale / rotation: size and angle of the finish's own texture.
- spec_shift metal / rough / clearcoat (-127..127): push those channels up or down for the whole zone (more metal, rougher, less clearcoat...).

## The unwrapped-paint reality
Text and numbers on the paint are often mirrored/rotated on other islands. Sponsor logos, numbers and stripes are usually separate PSD layers: prefer selecting them by layer name (exact, no colour bleed) over colour matching. Colour matching is best for big flat colours (body, stripes). When a colour is used both on the body and on a logo, add a layer restriction or a box.
