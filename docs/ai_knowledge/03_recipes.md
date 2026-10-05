# Worked recipes: what buyers ask -> what to do (AI knowledge card)

Always: look at STATE first (zones, layers, paint colours with WHERE they are), reuse an existing zone when one already covers the area, add a zone only for an area nothing covers or when a spot needs different treatment. New zones go at the TOP (they win overlaps). Never invent ids: search_finishes / search_patterns / search_spec_patterns, copy exactly.

## Recipe: "a gradient from blue to gold to white"
The gradient goes on the zone that owns the big body area. edit_zone {zone: <body zone>, finish: <a coating base like gloss/pearl/candy>, gradient: {stops: [{pos:0,color:"#0a3fd6"},{pos:50,color:"#d4a017"},{pos:100,color:"#ffffff"}], direction: "horizontal"}}. Pick the direction that matches the flat layout: horizontal = left to right across the canvas, vertical = top to bottom, diagonal_down/diagonal_up, radial from the centre. Choose true colours (gold = #d4a017 or #e0a800; white = #ffffff; deep blue = #0a3fd6). If the body zone only covers some colours of the paint, the gradient shows only there.

## Recipe: "reflective holographic finish"
On the same zone add spec patterns: edit_zone {zone, spec_patterns: [{id:"holo_prism_shift", opacity:80}]} (check with search_spec_patterns "holographic"), and make the base reflective (pearl, metallic or chrome). Optionally add a holographic monolithic finish if the buyer wants the whole special effect instead of a gradient body (a monolithic brings its own colour, so it replaces the gradient colour: prefer base + spec pattern when the buyer asked for a specific colour gradient).

## Recipe: "accents on the rear of each side, the same blue as the front accents, in a chrome flake look"
1. Find the front accents' colour: the paint colours list shows the accent hex and which grid cells it sits in; if unsure ask_vision "where are the accent stripes on the front and rear of each side?".
2. Rear accents = the same paint colour (or the same layer) but limited to the rear cells. add_zone {name:"Rear accents", region:{colors:["#accent hex"], cells:"<rear cells, e.g. A7:D8>"}, finish:"base::chrome" (or a metallic base), color: <the blue hex of the front accents or "source">, spec_patterns:[{id:"holographic_flake" or another chrome/metal flake id from search_spec_patterns "flake", opacity:70}]}.
3. If the rear accents share a colour with the front ones, the front zone above may already claim them (the footprint shows blocked_by): the new zone sits at the top, so it wins its box.
"Same blue as the front" means read the actual front accent colour from the paint colours or from the zone that covers it; do not guess a blue.

## Recipe: "make the numbers/sponsors/stripes chrome (or any finish)"
Use the PSD layer if one exists by that name: edit_zone or add_zone with region:{layers:["Numbers"], everything:true} and finish. Otherwise select by the number colour with tolerance 30-45.

## Recipe: "matte body with gloss accents / two-tone"
Body zone (remaining or its paint colour): finish base::matte or satin, color "source". Accent zone above it: finish base::gloss (or candy/chrome) on the accent colour.

## Recipe: "make it pop"
Find the biggest flat area and the strongest contrast pair. Push one to a deep glossy candy/pearl of its own colour, keep the other matte/satin or chrome accent; add a subtle flake spec pattern (opacity 30-50) on the body for depth. Explain what you did in one sentence.

## Recipe: "why does it look flat / wrong / nothing changed?"
Look at the zone in STATE (get_state): if visible_pct is much lower than share_pct, higher zones block it (say which, offer to move it up). If share is 0 the colour/tolerance/layer selects nothing (offer the fix). If intensity/base_strength is low, raise it. Answer in plain words and offer to fix.

## Recipe: "undo / go back"
Every AI change is one undo step in Pro (Ctrl+Z, or the Undo button under the reply). You cannot delete zones yourself: mute them (muted:true) and tell the buyer they can delete it in the zone list.

## Recipe: "change the car / the body / the whole car" (keep the numbers and sponsors)
If the paint has a layer named like "Car Paint" or "Body", put the change on that layer only: edit the catch-all zone (or add a zone) with region {layers:["Car Paint"]}. Numbers, sponsors, tape and logos sit on other layers, so they stay exactly as they are; tell the buyer ("I kept your numbers and sponsors"). If the buyer names the decals or says "everything", include them. A whole-car finish that brings its own colour (chameleon, candy, holographic) on the catch-all WITHOUT a layer restriction paints over every number and logo.

## Recipe: "start over / reset"
Zones cannot be deleted by the copilot. Mute every zone except the catch-all, then set the catch-all to plain gloss with colour "source" (keeps the car's own paint). Never mute all zones: Pro cannot render with none ("No zones provided").
