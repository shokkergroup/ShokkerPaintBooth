"""enc_B_v3_patterns.py - Encyclopedia v3 depth for the 7 hand-written `patterns` articles (2026-10-04).
Idempotent: enrich() replaces by id. Run: python scripts/ai_atlas/enc_B_v3_patterns.py
Every number below was read from: paint-booth-2-state-zones.js (PATTERN section 2258-2420), js/zones/pattern-transform-controls.js,
engine/compose.py (pattern paint 5285-5330, stacked 6120-6200), engine/pattern_paint_placement.py, engine/pattern_material.py,
engine/core.py (auto-scale), shokker_engine_v2.py (pattern stack build 19305-19335), paint-booth-0-finish-data.js (PATTERN_GROUPS),
SPB_WIKI.html (finish_doctrine scale law, lessons), docs/ai_knowledge/*.md.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enc_B_lib import *

SCREEN = ['ui_window_tour']   # placeholder until pattern-specific pictures exist: the window tour marks the zone popout panel that holds PATTERN

# ------------------------------------------------------------------ 1. what_is_a_pattern
enrich('patterns', 'patterns.what_is_a_pattern',
    sources=['js/zones/pattern-transform-controls.js:9-12', 'engine/compose.py:5285-5290', 'engine/compose.py:5426', 'paint-booth-2-state-zones.js:2258-2335', 'paint-booth-0-finish-data.js:5849', 'docs/ai_knowledge/sliders_and_controls.md:11',
             'docs/ai_knowledge/sliders_and_controls.md:23', 'SPB_WIKI.html#lessons', 'docs/ai_knowledge/sliders_and_controls.md:14', 'docs/ai_knowledge/02_spec_and_finishes.md:6-10', 'docs/ai_knowledge/09_field_playbook.md:35'],
    level='beginner',
    deep=[
        dict(heading='Where a pattern lands in the build order',
             body='A zone is built in a fixed order. The base finish makes the colour and material first, then Base Strength mixes that finished base over your source paint, and only then does the pattern go on. '
                  'The engine comment says patterns are deliberately kept outside the Base Strength mix and applied afterwards, so lowering Base Strength fades the base but never dims the pattern. '
                  'Pattern 1 goes down first, then the extra layers in order, then any 2nd to 5th base overlays go on top of the finished pattern. '
                  'So a pattern is always above the base and below the overlays, and the only sliders that fade it are its own Opacity and Strength.'),
        dict(heading='A pattern has two jobs, and only one is on by default',
             body='A pattern can change two things: the paint (colour and light and dark) and the shine map (metal, roughness and clearcoat). '
                  'Out of the box it only does the paint job. The Spec amount slider in the PATTERN section starts at 0%, which the slider tip explains is there to keep your existing base shine. '
                  'At 50% the pattern shine and the base shine mix equally, and at 100% the pattern shine replaces the metal, roughness and clearcoat in that zone. '
                  'That is why a fresh carbon pattern on a gloss base looks like printed weave but does not feel like carbon under the light until you raise Spec amount.'),
        dict(heading='Patterns versus the three other kinds of look',
             body='A base finish is a plain material that takes the zone colour. A monolithic special brings its own colour and texture. A pattern is a paint design that sits on top of either. '
                  'A spec pattern changes only the shine and never the colour, and you can stack up to 5 of them per zone. '
                  'The practical rule from the field notes: finishes that take the zone colour (gloss, satin, matte, candy, pearl, metallic) can be recoloured freely, while patterns and specials that bring their own palette are better steered with Hue and Saturation than with a solid colour, which would flatten them to one colour.'),
        dict(heading='Why some patterns never show up in the picker',
             body='The picker only lists patterns that belong to one of the nine groups. The group lists add up to 317 patterns, and anything not placed in a group is removed when the app starts. '
                  'The wiki lessons add the other half: the engine keeps its own list of what it can draw, and a pattern the engine does not know simply renders nothing. '
                  'If you ever pick a pattern and the preview shows no change, check the Opacity, Strength and Paint mode first, and then suspect that the pattern is not in the picker lists.'),
    ],
    examples=[
        dict(title='Clean single-colour carbon hood', goal='Carbon weave in the colour you already chose, not a grey picture of carbon.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Paint mode': 'Blend - keep paint color', 'Scale': '0.40x', 'Opacity': '100%', 'Spec amount': '0%'},
             result='Your base colour stays and the weave shows as light and dark steps in that colour. The shine stays exactly what the base gave you.'),
        dict(title='Carbon that also feels like carbon', goal='Weave in the paint and in the reflections.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Paint mode': 'Blend - keep paint color', 'Scale': '0.40x', 'Spec amount': '60%'},
             result='The pattern shine now mixes in at 60 percent: the weave catches light differently from the flat base, so it reads as a real woven surface when the car moves.'),
        dict(title='A fixed-palette pattern as a bold hero panel', goal='Show a pattern in its own colours on one panel.',
             settings={'Pattern 1 on this Layer/Zone': 'Camo', 'Paint mode': 'Overlay - full pattern', 'Scale': '0.50x', 'Opacity': '100%'},
             result='The camo draws its own colours across the zone and your base colour no longer shows through. Use this when you want the pattern palette, not yours.'),
    ],
    combos=[
        {'with': 'patterns.paint_mode', 'why': 'Decides whether the pattern shows its own colours or yours. It is the first thing to set after picking a pattern.'},
        {'with': 'spec.paint_spec_marriage', 'why': 'A pattern with Spec amount above 0% starts to carry shine of its own. The marriage article explains how to keep paint shapes and shine shapes pointing the same way.'},
        {'with': 'finishes.colour_source_modes', 'why': 'Decides whether the colour under the pattern is the finish own colour, your paint, or a solid colour. Solid colour on a finish that brings its own colours flattens it.'},
        {'with': 'recipes.carbon_hood', 'why': 'A finished walk-through of the most popular pattern job: a fine carbon weave on one part.'},
    ],
    faq=[
        dict(q='What is the difference between a pattern and a spec pattern?',
             a='A pattern is a visible paint design: it changes colour and light and dark, and can optionally carry shine through Spec amount. A spec pattern changes only the shine map and never the colour, so judge it on the spec preview.'),
        dict(q='Why does my pattern not change how shiny the car is?',
             a='Spec amount starts at 0% on purpose so your base shine is preserved. Raise it in steps of 5 percent to let the pattern bring its own metal, roughness and clearcoat.'),
        dict(q='Can I use more than one pattern on a zone?',
             a='Yes. A zone holds Pattern 1 plus four more layers added with + Add Layer, five in total.'),
        dict(q='Does Base Strength fade my pattern?',
             a='No. The pattern is applied after the Base Strength mix, so it keeps its own strength. Use the pattern Opacity and Strength sliders to fade it.'),
        dict(q='Where do I find the pattern controls?',
             a='Click a zone, open its popout panel and look for the PATTERN section. The pattern controls such as Paint mode, Opacity, Strength, Scale and Rotate only appear after you pick Pattern 1.'),
    ],
    mistakes=[
        dict(symptom='I picked a pattern and the Opacity, Scale and Rotate sliders are missing.',
             cause='The PATTERN section only shows its controls once Pattern 1 is set. With None chosen, only the picker and + Add Layer are there.',
             fix='Click Pattern 1 on this Layer/Zone and choose a pattern. The sliders appear straight away.'),
        dict(symptom='The pattern looks printed on, but the shine is the same as before.',
             cause='Spec amount is still at its starting value of 0%, so the pattern is not allowed to change metal, roughness or clearcoat.',
             fix='Raise Spec amount to 40 to 60 percent and watch the spec preview change.'),
        dict(symptom='I gave the zone a solid colour and my camo turned into one flat colour.',
             cause='Camo and snake finishes bring their own colours. A solid colour paints them one colour and loses the design.',
             fix='Keep the finish own colour and shift Hue or Saturation, or use a base that takes colour and add the pattern on top in Blend mode.'),
    ],
    protips=[
        'Pattern shape and pattern colour are separate jobs: pick the shape in the picker, then decide colour with Paint mode. Blend keeps your colour and gives light and dark steps, Overlay brings the pattern own palette.',
        'Because patterns sit above Base Strength, you can set Base Strength low to let your own paint show through and still have a full-strength pattern on top.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 2. nine_groups
enrich('patterns', 'patterns.nine_groups',
    sources=['paint-booth-0-finish-data.js:5849', 'js/spb-ai-atlas-data.js:2', 'paint-booth-0-finish-data.js:5850', 'paint-booth-0-finish-data.js:1495', 'docs/ai_knowledge/09_field_playbook.md:35'],
    level='beginner',
    deep=[
        dict(heading='How the nine groups add up',
             body='The group lists in the catalogue hold 44 in Abstract, Fractal and Paradigm, 46 in Tech, Carbon and Industrial, 44 in Geometry, Deco and Op-Art, 36 in Nature, Animals and Weather, 39 in Cultural, World and Dark, '
                  '44 in Decades 50s to 80s, 36 in 90s, Skate and Surf, 18 in Reactive and Surface Accents, and 10 in Let Freedom Ring. Together that is all 317 patterns in the catalogue. '
                  'A comment in the catalogue records that 25 small picker groups were collapsed into 8 groups of 50 or fewer; the list now runs to nine. '
                  'Any pattern that is not named in a group is removed from the picker when the app starts, so the groups are also the complete visible list.'),
        dict(heading='What lives where, by job',
             body='Tech, Carbon and Industrial is the structural family: carbon fiber, kevlar weave, nanoweave, chainlink, diamond plate, expanded metal, perforated, hex mesh, and the glitch and data-stream looks. '
                  'Geometry, Deco and Op-Art is the repeat family: art deco, chevron, herringbone, houndstooth, argyle, tartan, greek key and moire grids. '
                  'Nature holds camo, snake skins, leopard, zebra, tiger stripe, lightning and marble. Cultural has aztec, dragon scale, mandala, fleur de lis, runes and skulls. '
                  'Abstract is the generative family: fractals, reaction diffusion, Julia and Lissajous curves, topography, voronoi. These are generated by maths rather than drawn as stock textures, which makes them distinctive hero-panel choices.'),
        dict(heading='The two era groups carry icons, not just texture',
             body='Decades 50s to 80s has ids such as diner checkerboard, jukebox arc, sputnik orbit, drive-in marquee, peace sign, tie-dye spiral, lava lamp blob, pop-art halftone, disco glitter, pong pixels, pac-man maze, neon grid and rubiks cube. '
                  '90s, Skate and Surf has grunge splatter, smiley, cross colours, tamagotchi egg, floppy disk, dial-up static, windows 95, rollerblade streak and a run of surf and skate-deck designs. '
                  'These are recognisable motifs, so use them on one hero area. Repeating an icon over the whole car turns a retro look into wallpaper.'),
        dict(heading='Reactive and Freedom groups are accents and themes',
             body='Reactive and Surface Accents (18 patterns) holds the shimmer family plus iridescent fog, chrome delete edge, carbon clearcoat lock, racing scratch, pearlescent flip, frost crystal, satin wax and UV night accent. '
                  'They are built to modulate a surface, so they need a base with some shine to read. Let Freedom Ring (10 patterns) is the patriotic set: star lattice, stripe drift, bunting scallop, distressed flag, eagle crest, firework radial, constellation field, ribbon weave, stencil stars and liberty filigree.'),
    ],
    examples=[
        dict(title='Find a restrained sponsor-safe weave', goal='Texture the roof without competing with numbers.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber (Tech, Carbon & Industrial)', 'Paint mode': 'Blend - keep paint color', 'Scale': '0.35x', 'Opacity': '60%'},
             result='A quiet woven texture in your own colour. The catalogue description of Carbon Fiber calls it sponsor-safe and professional on any base.'),
        dict(title='Retro diner hood', goal='A period hero panel from the Decades group.',
             settings={'Pattern 1 on this Layer/Zone': 'Diner Checkerboard', 'Paint mode': 'Overlay - full pattern', 'Scale': '0.60x', 'Opacity': '100%'},
             result='The checkerboard shows in its own colours across the hood. Keep the rest of the car calm so the icon reads as one idea.'),
        dict(title='Generative hero panel', goal='Something nobody else has, from the Abstract group.',
             settings={'Pattern 1 on this Layer/Zone': 'Reaction Diffusion (Abstract, Fractal & Paradigm)', 'Paint mode': 'Blend - keep paint color', 'Scale': '0.50x', 'Opacity': '80%'},
             result='An organic, generated texture in the zone colour rather than a stock weave.'),
    ],
    combos=[
        {'with': 'patterns.choosing_at_car_scale', 'why': 'Every group needs a scale check on the car; icon-style groups especially look huge at 1.00x.'},
        {'with': 'patterns.layers_and_stacking', 'why': 'Mixing groups is how you get depth: a fine tech weave underneath and one bold geometry or era motif above it.'},
        {'with': 'spec.pattern_groups', 'why': 'Spec patterns have their own groups of shine-only textures. They pair with a paint pattern from here to make the weave feel real.'},
    ],
    faq=[
        dict(q='How many patterns are there?', a='The catalogue holds 319. The nine group lists add up to 317, and the two left out of every group are removed from the picker. The groups are Abstract, Tech and Carbon, Geometry and Deco, Nature, Cultural, Decades 50s to 80s, 90s and Surf, Reactive Accents and Let Freedom Ring.'),
        dict(q='Where is the camo?', a='In Nature, Animals and Weather: camo, multicam, dazzle and the animal skins. Ready-made camo finishes also exist in the finish catalogue and bring their own palette.'),
        dict(q='Where is the carbon fiber?', a='Tech, Carbon and Industrial, with kevlar weave, nanoweave and wavy carbon next to it. Carbon fiber is listed first in that group.'),
        dict(q='Why can I not find a pattern I saw before?', a='Patterns that are not placed in one of the nine groups are removed from the picker. Search the group names, or use the picker search with the pattern name.'),
    ],
    mistakes=[
        dict(symptom='A reactive accent pattern shows almost nothing.', cause='Reactive and Surface Accents are built to modulate shine, and a flat matte base gives them nothing to play on.',
             fix='Put them on a base with some shine such as pearl, metallic or gloss, and raise Spec amount so the accent shows in the reflections.'),
        dict(symptom='The lightning pattern looks like grey cracks on my matte black car.', cause='Lightning on matte black reads as grey cracked glass at any scale (field note from the design sessions).',
             fix='Pick a different pattern, or put lightning on a lighter or glossier base so the bolts have contrast.'),
        dict(symptom='A retro icon pattern repeats across the whole car and feels like wallpaper.', cause='Era patterns carry recognisable motifs, which are meant for one hero area.',
             fix='Limit the pattern to one zone such as the hood and keep the neighbours calm.'),
    ],
    protips=[
        'Use the group as a casting call: weave from Tech for the calm area, a motif from Geometry or Decades for the hero panel, and a Reactive accent as the last thin layer on top.',
        'Generative Abstract patterns such as reaction diffusion, truchet flow and phyllotaxis are maths, not stock artwork, so nobody else has seen the same panel on another car.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 3. scale_rotation_opacity
enrich('patterns', 'patterns.scale_rotation_opacity',
    sources=['js/zones/pattern-transform-controls.js:5-12', 'js/zones/pattern-transform-controls.js:187-230', 'engine/compose.py:5294-5312', 'engine/compose.py:6130-6140',
             'engine/pattern_paint_placement.py:51-77', 'engine/core.py:1498-1527', 'shokker_engine_v2.py:19023-19031', 'shokker_engine_v2.py:19305',
             'docs/ai_knowledge/how_do_i.md:169-174', 'docs/ai_knowledge/sliders_and_controls.md:12', 'docs/ai_knowledge/sliders_and_controls.md:27',
             'SPB_WIKI.html#finish_doctrine', 'paint-booth-2-state-zones.js:2258-2335'],
    level='intermediate',
    deep=[
        dict(heading='What the Scale number really means',
             body='Scale runs from 0.10x to 4.00x in steps of 0.05 and starts at 1.00x. A smaller number means more repeats, so the pattern gets finer; a bigger number zooms in. '
                  'The pattern shine uses the same Scale and Rotate, so the weave in the paint and the weave in the shine stay lined up. '
                  'Because the paint is one 2048 by 2048 sheet over a whole car, 1.00x often reads large. The field note says 0.3x to 0.6x is typical for fine detail. '
                  'The wiki sizes it in pixels: 16 to 64 px features are macro and dangerous if they carry the whole look, 4 to 8 px is fine texture, and 1 to 2 px is sparkle-level micro detail.'),
        dict(heading='Opacity and Strength multiply',
             body='Both sliders run 0 to 100 percent in steps of 5 and start at 100. In the paint, the engine uses Opacity times Strength as the share of the pattern that lands on the paint, so 50% Opacity with 50% Strength is only 25% pattern. '
                  'Opacity belongs to each layer, while Strength is one value for the whole zone and is used by every layer. Any Opacity below 100 on Pattern 1 moves it into the same layered build that the extra layers use, so it behaves like a layer. '
                  'Spec amount is separate: the slider tip says it is independent of paint Opacity and Strength, so you can fade the colour of a pattern and keep its shine.'),
        dict(heading='Small zones get a free scale boost',
             body='The engine multiplies your Scale by an automatic factor based on the zone size. It measures the box around the zone as a share of the canvas. Above 60 percent the factor is 1. Below that it is the square root of the share, never lower than 0.15. '
                  'A zone whose box covers 25 percent of the sheet gets 0.50, so Scale 1.00x behaves like 0.50x. A box covering 4 percent gets 0.20. The floor of 0.15 is reached at about 2.25 percent. '
                  'This is why a pattern looks finer on a number panel than on the whole-car zone at the same slider setting. Fit to Zone switches the automatic factor off, because it already sizes the pattern to the box.'),
        dict(heading='Pattern Hue and Saturation recolour only the artwork',
             body='Hue runs from -180 to 180 degrees in steps of 1 and Saturation from -100 to 100 percent in steps of 5. They act on the pattern art only, never on your base. They work in Overlay mode and are greyed out in Blend mode, where the pattern keeps the underlying paint colour. '
                  'Saturation -100 turns the pattern grayscale, 0 leaves its original colour, and +100 pushes it to full saturation. A positive value moves the colour toward full saturation by that share; a negative value scales the colour down by that share.'),
    ],
    examples=[
        dict(title='Fine carbon that reads as premium on a whole car', goal='Weave small enough to look like real carbon, not a fishing net.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Scale': '0.30x', 'Rotate': '0', 'Opacity': '100%', 'Strength': '100%'},
             result='Many small repeats across the zone. Compare 1.00x, 0.50x and 0.25x side by side on the car and keep the one where the weave is just readable.'),
        dict(title='Turn the twill with the body line', goal='Make the weave run diagonally along the hood.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Scale': '0.40x', 'Rotate': '45'},
             result='The weave turns 45 degrees. Rotate takes whole degrees from 0 to 359, so use the number box next to the slider for exact values.'),
        dict(title='Subtle texture over a loud base', goal='Let a pattern whisper instead of shout.',
             settings={'Pattern 1 on this Layer/Zone': 'Camo', 'Paint mode': 'Blend - keep paint color', 'Opacity': '40%', 'Strength': '100%', 'Scale': '0.50x'},
             result='Camo shows at 40 percent: the field note puts 30 to 50 percent opacity in the subtle range, with your own colour intact.'),
        dict(title='Grayscale pattern on a coloured car', goal='Use a pattern shape in neutral grey.',
             settings={'Paint mode': 'Overlay - full pattern', 'Saturation': '-100%', 'Hue': '0'},
             result='In Overlay mode the pattern art loses its colour and draws in grey tones. The sliders are disabled in Blend mode.'),
    ],
    combos=[
        {'with': 'finishes.base_scale_rotation', 'why': 'Base Scale sizes the finish own texture. It is a different slider from the pattern Scale, and the two never affect each other.'},
        {'with': 'patterns.choosing_at_car_scale', 'why': 'Gives the reasoning for which pattern sizes read as premium on a whole car and how to judge them.'},
        {'with': 'patterns.paint_mode', 'why': 'Hue and Saturation only work in Overlay mode, and the paint amount calculation is the same in both modes.'},
        {'with': 'spec.scale_rotation', 'why': 'The spec map has its own Scale and Rotation for finish texture; pattern shine follows the pattern Scale instead.'},
    ],
    faq=[
        dict(q='Why does smaller Scale make the pattern finer?', a='Scale is the zoom. A smaller number fits more repeats into the same area, so each shape is smaller. 0.50x is twice as fine as 1.00x.'),
        dict(q='What is the difference between Opacity and Strength?', a='Both fade the pattern in the paint, and they multiply: 50% and 50% gives 25%. Opacity is per layer, Strength is one value for the whole zone. Spec amount is separate from both.'),
        dict(q='Why is my pattern finer on a small zone than on the big one?', a='The engine adds an automatic scale based on the zone size. A zone covering a quarter of the canvas gets 0.50x on top of your slider.'),
        dict(q='Can I rotate by more than 359 degrees?', a='No. Rotate runs from 0 to 359 whole degrees. 360 is the same as 0.'),
        dict(q='Why are Hue and Saturation greyed out?', a='Paint mode is on Blend. In Blend the pattern keeps your paint colour, so the pattern colour sliders are disabled. Switch to Overlay to use them.'),
        dict(q='Does Scale change the pattern shine too?', a='Yes. The pattern shine shares Scale and Rotate with the pattern paint, so they stay aligned.'),
    ],
    mistakes=[
        dict(symptom='The pattern has almost vanished.', cause='Opacity and Strength both sit below 100 and multiply, so 50% and 50% leaves only 25% of the pattern.',
             fix='Raise one of them back to 100% and use the other as the single fade control.'),
        dict(symptom='The camo is so fine it just looks like plain colour.', cause='Scale went too low. Too-fine detail averages out and reads as a flat tint on the car.',
             fix='Raise Scale in steps of 0.05 until single shapes are readable again. The pink camo recipe in the field notes uses 0.60x for camo.'),
        dict(symptom='I changed Scale but the carbon weave of the base finish did not change.', cause='The finish has its own Base Scale slider in the BASE section. The pattern Scale only resizes the pattern.',
             fix='Open BASE and move Base Scale for the finish texture, or move the pattern Scale for the pattern.'),
    ],
    protips=[
        'Zone size changes how a slider value looks: the same Scale on a small zone is finer than on a big one. When you copy settings between zones, compare the result on the car instead of trusting the number.',
        'Use the wiki size bands as a check. If the pattern features are 16 to 64 px they are macro; add a second layer at a much smaller scale for the 4 to 8 px band so the surface has detail at both distances.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 4. placement
enrich('patterns', 'patterns.placement',
    sources=['paint-booth-2-state-zones.js:9338-9376', 'paint-booth-2-state-zones.js:9455-9492', 'paint-booth-2-state-zones.js:2296-2345', 'js/zones/strength-map-controls.js:4',
             'js/zones/strength-map-controls.js:70-80', 'shokker_engine_v2.py:19027-19042', 'shokker_engine_v2.py:19309-19335', 'paint-booth-5-api-render.js:706-720'],
    level='intermediate',
    deep=[
        dict(heading='The three placement modes',
             body='Full Canvas is the default. The pattern is centred and tiled across the whole sheet, and Position X and Y are both 50 percent. '
                  'Fit to Zone makes the engine measure the box around the pixels the zone owns and resize the whole pattern into that box, so one complete copy of the artwork sits inside the zone instead of a crop of a canvas-wide tile. '
                  'Edit on Template lets you drag the pattern on the template by hand; a Position on template banner and a MANUAL PLACEMENT bar appear. '
                  'In Fit to Zone the template offsets are locked: the Position sliders and their buttons are greyed out and stop responding until you switch back.'),
        dict(heading='Fit to Zone replaces the automatic scale',
             body='Normally the engine adds an automatic scale for small zones. In Fit to Zone that automatic boost is skipped, because the pattern is stretched to the zone box instead. '
                  'The box is the rectangle around the zone, so an L-shaped or split zone fits the pattern to the whole rectangle, not to the inside of the L. '
                  'The fit also applies to every pattern layer in the zone, not only Pattern 1. '
                  'This is the mode for a motif that should appear once on a door panel, a number plate area or a logo-sized zone.'),
        dict(heading='Position, flip and the Strength Map',
             body='Under Advanced Pattern Control Panel you get Position X and Position Y from 0 to 100 percent with 50 as the centre, plus Flip H and Flip V to mirror the pattern. The sliders move in 5 percent steps and the minus and plus buttons in 1 percent steps. These controls belong to Pattern 1. '
                  'Strength Map ON creates a 256 by 256 grid that starts fully white, which means the pattern is at 100 percent everywhere; black is 0 and means no pattern. '
                  'The brush is 2 to 80 px wide (20 by default), and the Value slider runs 0 to 255 shown as a percentage. Value starts at 0 percent, so your first stroke erases. '
                  'Helpers: Fill White, Fill Black, Top-Bottom, Left-Right and Center Fade. Turn the map OFF and it no longer applies.'),
        dict(heading='What Edit on Template gives you',
             body='While placing by hand, drag on the template to move the pattern. The bar over the canvas has Flip H, Flip V, 90 degree turns each way, Reset to centred defaults, and Done to keep the values. Esc also leaves placement mode. '
                  'Choosing Full Canvas or Fit to Zone again ends the manual mode. Manual placement is the quickest way to slide a stripe or badge-sized pattern onto one panel; the Position X and Y sliders are the precise way to nudge it afterwards.'),
    ],
    examples=[
        dict(title='One big emblem on a door', goal='Show a single copy of a pattern on one panel.',
             settings={'Pattern 1 on this Layer/Zone': 'Celtic Knot', 'Pattern placement': 'Fit to Zone', 'Paint mode': 'Overlay - full pattern', 'Opacity': '100%'},
             result='One complete copy fits the zone box. The Position sliders lock while Fit to Zone is active.'),
        dict(title='Nudge a stripe pattern sideways', goal='Shift the stripes so a bold line misses the number.',
             settings={'Pattern placement': 'Full Canvas', 'Position X': '55%', 'Position Y': '50%'},
             result='The pattern tile slides across the canvas by one 5 percent step from the centre of 50.'),
        dict(title='Pattern fades out across the zone', goal='Strong at one end of the zone, gone at the other.',
             settings={'Strength Map': 'ON', 'Top-Bottom': 'click', 'Pattern placement': 'Full Canvas'},
             result='The map starts white at the top and fades to black at the bottom, so the pattern is strongest at the top of the map. Look at the preview to see which way that runs on the car.'),
        dict(title='Mirror a pattern', goal='Flip the pattern direction on one zone.',
             settings={'Flip H': 'checked', 'Pattern placement': 'Full Canvas'},
             result='The pattern is mirrored horizontally on that zone.'),
    ],
    combos=[
        {'with': 'ui_shell.placement_overlay', 'why': 'Describes the Position on template banner and the MANUAL PLACEMENT bar you get in Edit on Template mode.'},
        {'with': 'zones.regions', 'why': 'Fit to Zone follows the zone box, so how you select pixels decides what the pattern fits into.'},
        {'with': 'patterns.layers_and_stacking', 'why': 'Fit to Zone is applied to every layer, so a stacked set fits together and keeps its relative sizes.'},
        {'with': 'playbook.placement_wrong', 'why': 'If a stripe or block sits in the wrong place on the car, fix the part or band first rather than guessing positions.'},
    ],
    faq=[
        dict(q='What is the difference between Full Canvas and Fit to Zone?', a='Full Canvas tiles the pattern over the whole sheet, centred. Fit to Zone squeezes one complete copy into the box around your zone.'),
        dict(q='Why can I not move the Position sliders?', a='Fit to Zone is active. It locks the template offsets. Switch to Full Canvas or Edit on Template to move the pattern.'),
        dict(q='What is the Strength Map for?', a='It paints where the pattern is strong or weak: white is 100 percent, black is 0. Fill White resets it, Fill Black zeroes it, and the gradient helpers fade it across the zone.'),
        dict(q='Why does my first Strength Map stroke make the pattern disappear?', a='The brush Value starts at 0 percent, which is black, so painting erases. Raise Value before painting to add the pattern back.'),
        dict(q='Does Position work on extra pattern layers?', a='No. Position X and Y, Flip H, Flip V and the Strength Map belong to Pattern 1. Extra layers have Opacity, Scale, Rotate and Blend.'),
    ],
    mistakes=[
        dict(symptom='The pattern got a very different size after I clicked Fit to Zone.', cause='The whole artwork is resized into the zone box, so the result depends entirely on how large that box is.',
             fix='Check the preview, then go back to Full Canvas and use Scale if you need an exact size.'),
        dict(symptom='Position sliders look faded and do nothing.', cause='Fit to Zone locks the template offsets.', fix='Click Full Canvas to unlock them.'),
        dict(symptom='I turned on Strength Map and the pattern vanished where I painted.', cause='The Value slider starts at 0 percent, so the brush paints black, which means no pattern.',
             fix='Raise Value to 100 percent before painting to add strength, or use Fill White to reset the whole map.'),
    ],
    protips=[
        'For a pattern that should appear once, use Fit to Zone on a small zone with a clean box. For a texture that should flow across panels, use Full Canvas so neighbouring zones share the same tile.',
        'Flip H gives you a mirrored copy of a pattern direction without picking a second pattern, which is handy when the left and right of a design should lean opposite ways.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 5. layers_and_stacking
enrich('patterns', 'patterns.layers_and_stacking',
    sources=['paint-booth-2-state-zones.js:5099-5100', 'paint-booth-2-state-zones.js:2358-2425', 'js/zones/pattern-transform-controls.js:242-255', 'paint-booth-5-api-render.js:207-224',
             'shokker_engine_v2.py:19305-19335', 'engine/compose.py:6118-6126', 'engine/compose.py:6150-6160', 'engine/pattern_material.py:51-79'],
    level='intermediate',
    deep=[
        dict(heading='The order the layers are painted in',
             body='The stack has Pattern 1 plus up to four more layers, five in total. Pattern 1 goes down first, then Pattern 2, 3, 4 and 5 in list order, and each one is painted over the result of the one before. Pattern 5 therefore sits on top. '
                  'A layer left on None is ignored, and a layer whose Opacity is 0 is skipped in the paint (its shine is a separate setting). The engine reads at most four extra layers, which matches the four the app allows. '
                  'Automatic scale for small zones is applied to each extra layer as it is to Pattern 1, unless Fit to Zone is on, in which case every layer is fitted to the zone box instead.'),
        dict(heading='What is per layer and what is shared',
             body='Each extra layer has its own pattern, Opacity (5 percent steps), Scale (0.10x to 4.00x), Rotate (0 to 359), a Blend list with Normal, Multiply, Screen and Overlay, plus Hue, Saturation and Spec amount. A new layer starts on None, 100 percent Opacity, 1.00x and 0 degrees. '
                  'Paint mode (Overlay or Blend) and Strength are shared by the whole zone, so changing them changes every layer at once. Position X and Y, Flip H, Flip V and the Strength Map belong to Pattern 1 only. '
                  'Practical result: in Blend mode every layer takes your base colour and only adds light and dark steps. To give two layers their own palettes, use Overlay for the zone.'),
        dict(heading='The same pattern in Pattern 1 and in a layer',
             body='If a pattern id appears in one of the extra layers, the engine skips it as Pattern 1. A comment in the engine explains why: drawing it twice at default scale would overwhelm the stack scale. '
                  'So Pattern 1 on Carbon Fiber at 1.00x plus a Carbon Fiber layer at 0.30x shows only the 0.30x layer. If you want two scales of the same weave, put the finer one in the layer and choose a different Pattern 1, or use a second zone.'),
        dict(heading='Stacked shine mixes one layer at a time',
             body='Spec amount is also per layer. The engine goes through Pattern 1 and then the layers in order, and for each one it mixes the pattern shine into the map: result equals earlier shine times one minus the amount, plus the layer shine times the amount. '
                  'A layer at 100 percent Spec amount therefore replaces everything before it, and a layer at 30 percent only tints it. Each layer uses its own Scale and Rotate for its shine. '
                  'Layers on 0 percent, the starting value, never touch the shine.'),
    ],
    examples=[
        dict(title='Carbon with a stripe motif on top', goal='A fine weave under one bold geometric shape.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Paint mode': 'Overlay - full pattern', 'Scale': '0.30x',
                       'Pattern 2 on this Layer/Zone': 'Chevron', 'Pattern 2 Opacity': '60%', 'Pattern 2 Scale': '1.00x'},
             result='The chevron sits on top of the weave at 60 percent. The scales differ by more than three times, so they read as two separate ideas, as the tip recommends.'),
        dict(title='Camo that keeps your colour with a fine mesh over it', goal='Texture on texture without losing the paint colour.',
             settings={'Pattern 1 on this Layer/Zone': 'Multicam', 'Paint mode': 'Blend - keep paint color', 'Opacity': '70%', 'Scale': '0.60x',
                       'Pattern 2 on this Layer/Zone': 'Hex Mesh', 'Pattern 2 Opacity': '30%', 'Pattern 2 Scale': '0.25x'},
             result='Camo shapes in your base hue, with a very fine mesh adding micro texture on top. Blend mode is shared, so both layers keep your colour.'),
        dict(title='Add a shine-only layer', goal='A layer that changes the reflections and not the colour.',
             settings={'Pattern 2 on this Layer/Zone': 'Carbon Fiber', 'Pattern 2 Opacity': '0%', 'Pattern 2 Spec amount': '40%'},
             result='Opacity 0 skips the layer in the paint, while Spec amount is independent of Opacity, so the layer still mixes its shine into the map at 40 percent. Check it on the spec preview.'),
    ],
    combos=[
        {'with': 'patterns.paint_mode', 'why': 'Paint mode is shared by every layer in the zone, so decide Overlay or Blend before you build the stack.'},
        {'with': 'spec.how_layers_combine', 'why': 'Explains how shine layers mix; paint pattern layers with Spec amount follow the same mixing idea.'},
        {'with': 'finishes.second_base_overlays', 'why': 'Base overlays go on after the whole pattern stack, so they sit above every pattern layer.'},
        {'with': 'patterns.placement', 'why': 'Fit to Zone fits every layer, and the Position, Flip and Strength Map controls are Pattern 1 only.'},
    ],
    faq=[
        dict(q='How many patterns can I stack in one zone?', a='Five: Pattern 1 plus four more layers. When you try to add a sixth, a message says Max 5 patterns (Pattern 1 + 4 layers).'),
        dict(q='Which layer is on top?', a='The last one. Pattern 5 is painted over 4, which is over 3, and so on back to Pattern 1.'),
        dict(q='How do I remove a layer?', a='Click the None button on that layer. You can then add another layer.'),
        dict(q='Does each layer have its own Strength?', a='No. Strength is one value for the whole zone. Each layer has its own Opacity, Scale, Rotate, Blend, Hue, Saturation and Spec amount.'),
        dict(q='What does the Blend list on a layer do?', a='It offers Normal, Multiply, Screen and Overlay and is saved with the layer. In the current engine the Overlay and Blend paint modes mix layers by Opacity and order and do not read that list, so judge layers by Opacity, order and the zone Paint mode.'),
    ],
    mistakes=[
        dict(symptom='Pattern 1 vanished when I added a layer.', cause='The same pattern is also in a layer. The engine drops Pattern 1 when its pattern is already in the stack.',
             fix='Pick a different pattern for Pattern 1 or for the layer, or put the second scale in another zone.'),
        dict(symptom='My second pattern shows my base colour instead of its own.', cause='Paint mode is Blend, which applies to every layer in the zone.',
             fix='Switch Paint mode to Overlay if you want layers to bring their own colours.'),
        dict(symptom='The layer I added shows nothing.', cause='It is still on None, or its Opacity is 0, and the engine skips both in the paint.', fix='Choose a pattern and keep Opacity above 0. A layer at Opacity 0 can still carry shine through Spec amount.'),
        dict(symptom='The stack turns to noise.', cause='Five busy layers at similar scales fight each other.',
             fix='Use two or three layers, make their scales very different, and fade the top ones with Opacity.'),
    ],
    protips=[
        'Think in size bands: a macro shape layer, a fine texture layer, and optionally a micro layer. The wiki lists the bands as 16 to 64 px, 4 to 8 px and 1 to 2 px on the 2048 sheet.',
        'A layer at Opacity 0 and Spec amount above 0 is a shine-only layer: no paint from it, but its metal, roughness and clearcoat still mix in, since Spec amount is independent of Opacity.',
        'Because overlay bases are painted after the pattern stack, a base overlay can tint or glow the whole stack at once, which is a cheap way to unify layers that do not quite agree.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 6. paint_mode
enrich('patterns', 'patterns.paint_mode',
    sources=['paint-booth-2-state-zones.js:2276-2285', 'js/zones/pattern-transform-controls.js:9-32', 'engine/pattern_paint_placement.py:51-77', 'engine/compose.py:5307-5312',
             'engine/compose.py:6130-6140', 'paint-booth-5-api-render.js:638-645', 'shokker_engine_v2.py:18606-18610', 'shokker_engine_v2.py:20733-20744',
             'docs/ai_knowledge/sliders_and_controls.md:12', 'docs/ai_knowledge/sliders_and_controls.md:23', 'docs/ai_knowledge/sliders_and_controls.md:27'],
    level='intermediate',
    deep=[
        dict(heading='Overlay: the pattern paints its own colours',
             body='Overlay mixes the pattern colour into your paint by an amount equal to its Opacity times Strength, only where the pattern art itself is not transparent. At 100 and 100 the pattern colours replace the base inside the shapes. '
                  'The field tests recorded a snake pattern painting its own brown with the base colour not showing. Hue (-180 to 180) and Saturation (-100 to 100) recolour the pattern art in this mode. '
                  'Overlay is the choice when the pattern palette is the point: camo, snake, flags, retro icons, anything with several set colours.'),
        dict(heading='Blend: your hue, the pattern light and dark',
             body='Blend keeps the hue and saturation of the paint underneath. It stretches the pattern lightness to a 0 to 1 range, then sets the new brightness to 20 percent of the old brightness plus 80 percent of (0.1 plus 0.85 times the pattern detail). '
                  'So most of the brightness now comes from the pattern, not from your base: a mid-tone base gets deep valleys and bright ridges in the same hue. '
                  'Neutral paint such as black, white or grey has no hue to keep, so a Blend weave on pure black stays grey. Hue and Saturation are disabled because the colour is yours.'),
        dict(heading='One mode for the whole zone, and shine is separate',
             body='The Paint mode list sits under Pattern 1 and applies to every layer in the zone. The app only ever sends Overlay or Blend. '
                  'Spec amount (0 to 100, steps of 5, starting at 0) is available in both modes and is independent of paint Opacity and Strength. Raising it mixes the pattern metal, roughness and clearcoat over the base shine. '
                  'A zone that has a pattern Spec amount above 0 is exempt from the final minimum roughness of 15 and minimum clearcoat of 16, so the pattern shine arrives exactly as authored. Check the spec preview after raising it.'),
        dict(heading='Why Base Strength cannot stand in for Paint mode',
             body='Base Strength fades the finished base over your source paint, and the pattern goes on afterwards, so it is not touched. If the base colour vanishes under a pattern, lowering Base Strength will not bring it back. '
                  'The fixes are Blend mode, a lower Opacity, or a lower Strength. The field note puts 30 to 50 percent Opacity in the subtle range if you want your paint to show through an Overlay pattern. Overlay base layers (2nd to 5th base) are applied after the pattern, so they can still tint the result.'),
    ],
    examples=[
        dict(title='Pink camo that stays pink', goal='Camo shapes with a hot pink base.',
             settings={'BASE COLOR': 'Use solid color (#ff69b4)', 'Pattern 1 on this Layer/Zone': 'Multicam', 'Paint mode': 'Blend - keep paint color', 'Opacity': '70%', 'Scale': '0.60x'},
             result='The base colour decides the camo hue and the pattern adds the light and dark shapes. This is the recipe the field notes use when no pink camo finish exists.'),
        dict(title='Snake skin in its own palette', goal='Show the real colours of a pattern.',
             settings={'Pattern 1 on this Layer/Zone': 'Snake Skin 3', 'Paint mode': 'Overlay - full pattern', 'Opacity': '100%', 'Strength': '100%'},
             result='The snake paints its own colours and your base colour does not show inside the scales.'),
        dict(title='Carbon with real shine', goal='A weave that looks and reflects like carbon.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Paint mode': 'Blend - keep paint color', 'Scale': '0.40x', 'Spec amount': '50%'},
             result='Your colour in the paint with half-and-half pattern shine, so the weave catches light differently from the flat base.'),
    ],
    combos=[
        {'with': 'finishes.colour_source_modes', 'why': 'Solid colour or source paint decides which colour Blend keeps; solid colour on a pattern-palette finish flattens it.'},
        {'with': 'patterns.scale_rotation_opacity', 'why': 'Opacity times Strength is the paint amount in both modes, and Hue and Saturation exist only in Overlay.'},
        {'with': 'spec.how_layers_combine', 'why': 'Spec amount mixes pattern shine into the base shine; this article explains how shine layers combine.'},
        {'with': 'recipes.camo', 'why': 'The camo recipe uses Blend so your base colour decides the hue.'},
    ],
    faq=[
        dict(q='Which mode is the default?', a='Overlay - full pattern. Blend - keep paint color is the other choice.'),
        dict(q='My base colour disappeared under the pattern. What do I do?', a='Switch Paint mode to Blend. In Overlay the pattern draws its own colours over the base.'),
        dict(q='Can I use Overlay for one layer and Blend for another?', a='No. Paint mode is one setting for the whole zone and applies to every pattern layer in it.'),
        dict(q='Why is my black car getting a grey weave in Blend mode?', a='Black has no hue to keep, and Blend takes most of its brightness from the pattern. Use a coloured base, or use Overlay mode.'),
        dict(q='Does Spec amount depend on Paint mode?', a='No. Spec amount works the same in both modes and is independent of paint Opacity and Strength.'),
    ],
    mistakes=[
        dict(symptom='Hue and Saturation sliders are greyed out.', cause='Paint mode is Blend, where the pattern keeps your paint colour.', fix='Switch to Overlay mode.'),
        dict(symptom='A solid colour flattened my camo to one colour.', cause='Camo and snake finishes bring their own colours, and a solid colour paints them one flat colour (measured in the field notes).',
             fix='Shift Hue or Saturation instead, or use a base that takes colour plus a pattern in Blend mode.'),
        dict(symptom='Raising Spec amount made the car look dull or odd.', cause='At 100 percent the pattern shine replaces the metal, roughness and clearcoat in the zone, and pattern spec zones skip the usual minimums.',
             fix='Go back to 40 to 60 percent and check the spec preview.'),
    ],
    protips=[
        'Overlay at 30 to 50 percent Opacity is a quick way to get a ghosted version of the pattern own palette over your paint without switching to Blend.',
        'To recolour an Overlay pattern use its Hue slider, not the zone solid colour. A solid colour on a finish that brings its own palette loses the design.',
    ],
    screens=SCREEN)

# ------------------------------------------------------------------ 7. choosing_at_car_scale
enrich('patterns', 'patterns.choosing_at_car_scale',
    sources=['SPB_WIKI.html#finish_doctrine', 'SPB_WIKI.html#lessons', 'docs/ai_knowledge/how_do_i.md:169-174', 'docs/ai_knowledge/09_field_playbook.md:31',
             'docs/ai_knowledge/05_design_and_taste.md:7', 'docs/ai_knowledge/09_field_playbook.md:35', 'engine/core.py:1498-1527', 'js/spb-support-answers.js:88'],
    level='beginner',
    deep=[
        dict(heading='What 2048 pixels means on a car',
             body='The paint is one flat 2048 by 2048 picture of the whole car cut open. The wiki scale law says a mark that looks medium in a square preview may be the size of a mirror, a number panel or a door section on the body. '
                  'It names three size bands on that sheet: macro or mid at 16 to 64 px, fine at 4 to 8 px, and micro at 1 to 2 px. Macro is good for readability but dangerous if it carries the whole look. '
                  'The owner correction recorded in the wiki is that things had been going too big, so bias smaller and denser, and when something already seems detailed enough push the detail another 25 to 40 percent before you call it finished.'),
        dict(heading='The preview lies about small detail',
             body='The wiki lesson says the live preview renders at 1024 while the product is 2048. The field notes add that a preview picture of about 768 px for a 2048 sheet averages out fine effects, such as snakeskin at scale 0.25, so they can look flat or tinted. '
                  'The support answer says the preview shows the same colours and patterns as the render but not the same shine. So zoom into a crop before deciding a small pattern did nothing, and confirm the final look from the real render in iRacing.'),
        dict(heading='A quick scale ladder',
             body='Scale runs from 0.10x to 4.00x, 1.00x is the start, and the field note calls 0.3x to 0.6x typical for fine detail on a whole-car sheet. Try three rungs: 1.00x, 0.50x and 0.25x. '
                  'Pick the largest one where single shapes still read on the car, then add a second layer well below it for fine texture. '
                  'Zone size also matters: the engine multiplies your Scale by the square root of the zone box share when the box is under 60 percent of the canvas, to a floor of 0.15, so small zones come out finer than the number suggests.'),
        dict(heading='Leave room for numbers and sponsors',
             body='The design notes say numbers and sponsor logos need strong contrast with what is behind them and should not sit on busy texture. No sparkle, strong pattern or chameleon shift directly behind numbers. '
                  'Choose calm weave patterns for the area around numbers, lower Opacity there, or keep the number area in its own zone with no pattern. A lightning pattern on matte black was also recorded as reading like grey cracked glass at any scale, so test strong shapes on the real base first.'),
    ],
    examples=[
        dict(title='Three-step scale test on one zone', goal='Find the right size for a pattern without guessing.',
             settings={'Pattern 1 on this Layer/Zone': 'Chain Link', 'Scale': '1.00x, then 0.50x, then 0.25x'},
             result='Look at the car preview after each step. Keep the biggest scale where single links are still readable. Zoom into a crop at 0.25x because very fine detail can look flat.'),
        dict(title='Two sizes for two distances', goal='A pattern that reads from far away and up close.',
             settings={'Pattern 1 on this Layer/Zone': 'Diamond Plate', 'Scale': '0.60x', 'Pattern 2 on this Layer/Zone': 'Carbon Fiber', 'Pattern 2 Scale': '0.25x', 'Pattern 2 Opacity': '40%'},
             result='A bold mid-size plate shape with a fine weave on top. The sizes are well apart, so they read as macro and fine bands.'),
        dict(title='Calm near the numbers', goal='Pattern on the body without fighting the number.',
             settings={'Pattern 1 on this Layer/Zone': 'Carbon Fiber', 'Scale': '0.40x', 'Opacity': '40%'},
             result='A quiet weave at 40 percent, which the notes put in the subtle range. Keep the number panel in its own zone or lower the opacity there.'),
    ],
    combos=[
        {'with': 'support.smeared_blobby', 'why': 'Blobby or smeared looks on the car almost always mean the texture is too big for a whole car.'},
        {'with': 'support.tiny_or_huge', 'why': 'Shows which of the three scale sliders to touch when a texture is microscopic or gigantic.'},
        {'with': 'concepts.preview_vs_truth', 'why': 'The preview is a smaller picture than the real sheet and does not show shine, so confirm small detail on a zoomed crop and in the real render.'},
        {'with': 'playbook.composition_rules', 'why': 'One dominant colour, one accent and one trim, with calm space around numbers.'},
    ],
    faq=[
        dict(q='How big is the paint file?', a='2048 by 2048 pixels, covering the whole car laid flat. A 64 px mark can be the size of a side mirror.'),
        dict(q='What Scale should I use?', a='Start at 0.30x to 0.60x for fine detail and compare with 1.00x and 0.25x on the car.'),
        dict(q='Why does the same Scale look different on a small zone?', a='For zones whose box is under 60 percent of the canvas the engine multiplies your Scale by an automatic factor, the square root of the box share, down to 0.15.'),
        dict(q='Why does a fine pattern look flat in the preview?', a='The preview is smaller than the 2048 sheet, so very fine detail averages out. Zoom in on a crop and check the real render.'),
        dict(q='Can patterns go behind numbers?', a='Avoid strong patterns behind numbers and sponsors. They need strong contrast with what is behind them, so keep that area calm.'),
    ],
    mistakes=[
        dict(symptom='The pattern looks great on the swatch but huge on the car.', cause='The swatch is a thumbnail. On a 2048 sheet over a whole car, medium shapes become mirror or door sized.',
             fix='Drop Scale to 0.50x or lower and judge on the car preview, not the thumbnail.'),
        dict(symptom='One macro-size pattern carries the whole look and the car reads smeared.', cause='Large features with no fine detail look like smeared paint.',
             fix='Add a second layer at a much smaller scale so there is detail in the 4 to 8 px band.'),
        dict(symptom='The pattern is behind my number and I cannot read it.', cause='Busy texture behind numbers kills contrast.', fix='Put the number area in its own zone without a pattern, or lower Opacity there.'),
    ],
    protips=[
        'Plan sizes in bands instead of hoping one Scale does everything: the wiki lists macro at 16 to 64 px, fine at 4 to 8 px and micro at 1 to 2 px on the 2048 sheet.',
        'If a small decorative zone looks too fine at 1.00x, that is the automatic zone scale at work. Raise Scale a little, or turn on Fit to Zone, which replaces the automatic factor with a fit to the zone box.',
    ],
    screens=SCREEN)


# ------------------------------------------------------------------ base-text corrections found while reading the code (idempotent)
def _patch_base():
    import json, os
    p = os.path.join(DRAFTS, 'patterns.jsonl')
    out = []
    changed = 0
    for l in open(p, encoding='utf-8'):
        if not l.strip(): continue
        a = json.loads(l)
        if a['id'] == 'patterns.layers_and_stacking':
            w = a['what'].replace('Each layer has its own pattern, scale, rotation and strength.',
                                  'Each extra layer has its own pattern, opacity, scale, rotation and blend choice. Paint mode and Strength are shared by the whole zone.')
            h = [s.replace('Use Remove on any layer to take it out.', 'Click None on any layer to take it out.') for s in a['how']]
            if w != a['what'] or h != a['how']:
                a['what'], a['how'] = w, h; changed += 1
        out.append(json.dumps(a, ensure_ascii=False))
    if changed:
        tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8').write(chr(10).join(out) + chr(10))
        os.replace(tmp, p)
        print('patched base text in', changed, 'article(s)')

_patch_base()
