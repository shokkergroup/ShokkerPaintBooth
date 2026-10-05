# Spec map, finishes and looks (AI knowledge card)

## The spec map in iRacing (what "spec" means)
iRacing reads a second image, the spec map, beside the paint. Its channels: RED = metallic (0 = plastic/paint, 255 = bare metal/chrome), GREEN = roughness (0 = perfect mirror, 255 = fully matte), BLUE = clearcoat (inverted: 16 = maximum glossy clearcoat, 255 = no clearcoat/dull). Gloss paint is roughly M0 R20 CC16; matte M0 R215 CC215; chrome M255 R2 CC0; metallic paint M200 R50 CC16. When a buyer says "the spec finish" or "how it reflects" they mean this map: reflective/mirror = low roughness + high metal; matte = high roughness; flake/sparkle = tiny bright specks in the metal channel; holographic = rainbow-shifting specks or bands.

## Four kinds of "finish" in Shokker
- BASE: a plain material for a zone (gloss, matte, satin, chrome, candy, pearl, metallic, carbon, brushed metal ...). key looks like base::chrome. The colour comes from the zone's colour mode.
- MONOLITHIC: a complete special look that brings its own colour and texture together (exotic, animated-looking, themed). key looks like monolithic::name. Use one when the buyer describes a whole special effect ("holographic", "galaxy", "hologram").
- PATTERN: a paint-colour pattern layered on top of the base (carbon weave, camo, stripes, flames ...). Changes what you SEE.
- SPEC PATTERN: a texture that changes the spec map only (flake, sparkle, micro-metal, holographic prism, engine-turn, weave ...). Changes how the surface REFLECTS, not the colour. Up to 5 stack on a zone, each with opacity, scale, rotation and channels (M = metallic, R = roughness, C = clearcoat).
A zone may also have a SECOND BASE blended over the first (for example gloss body + a pearl overlay at 40%).

## How to choose (design sense)
- Big body areas: candy, pearl, metallic, satin or gloss in the livery colour read premium; chrome on a large area is loud and shows every flaw, so use it for accents, numbers, trim.
- Adjacent areas must contrast in colour or in shine (matte next to gloss, chrome next to dark). Keep numbers/sponsors readable: high-contrast colour and a clean finish.
- A limited palette (2-3 colours + one accent) looks expensive.
- "Flake" = a spec pattern from the Sparkle & Micro-Metal group (holographic_flake, gold_flake, ...) on top of a metallic-capable base (metallic, chrome, candy, pearl).
- "Holographic / rainbow / iridescent / prismatic" = a holographic spec pattern (holo_prism_shift, spec_holographic_oil_circuit) and/or a holographic monolithic finish; pair with a bright reflective base.
- "Reflective / mirror / wet" = chrome or a very low-roughness base plus high clearcoat.
- "Worn / weathered / dirty" = roughness up, clearcoat down, weathering spec patterns.

## Adjusting a look
Too shiny: raise roughness with spec_shift rough +40, or lower spec_strength. Too flat: lower roughness, raise clearcoat, add a flake spec pattern. Colour too strong over the livery: lower base_strength. Texture too big/small: scale.
