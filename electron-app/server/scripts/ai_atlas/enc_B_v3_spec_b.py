"""V3 depth for the spec map articles, part B (iron rules, marriage of paint and spec, how layers combine, files, strength, scale, sliders).
Order-of-operations facts come from the engine (build_multi_zone and compose) as read on 2026-10-04. Run: python scripts/ai_atlas/enc_B_v3_spec_b.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'spec'
ENG = 'shokker_engine_v2.py'
COMP = 'engine/compose.py'
W = 'SPB_WIKI.html'
SUP = 'js/spb-support-answers.js'
AIK = 'docs/ai_knowledge/'

enrich(D, 'spec.iron_rules', level='intermediate',
    sources=[ENG + ':267', ENG + ':270', ENG + ':274', ENG + ':20735-20747', W + ':4278-4286', W + ':4766', 'engine/SPEC_MAP_REFERENCE.md:15-35'],
    deep=[
        {'heading': 'The exact rules and the numbers behind them', 'body': 'Rule one, coat: every coat value is raised to at least 16 (the app calls this the clearcoat floor). Rule two, roughness: wherever metal is under 240, roughness is raised to at least 15. Metal of 240 or more is chrome tier and may keep roughness down to 0. Rule three, alpha: it starts at 255 everywhere and only a lighting mask, an override or an imported spec changes it. After the rules, values are clipped to 0 to 255 and any invalid number becomes a safe value. These run at the very end of a render, so no slider, overlay or tool can slip past them.'},
        {'heading': 'Why each rule exists', 'body': 'Coat values 1 to 15 sit in the band the sim reads as no coat or legacy, and they whitewash the paint; resizing or smoothing a spec file creates them by accident, so the app removes the whole band. Roughness under 15 is reserved for mirror metal, so a gloss or satin zone is held at 15 and only a chrome-tier pixel can be a true mirror. Alpha stays at full lighting because it is a mask for the lighting response, not a gloss control; dropping it makes an area look dead.'},
        {'heading': 'The two places a value may stay below the floor', 'body': 'Pixels from an imported or authored spec (the SHOKK DROP sets) keep their exact coat. Pixels from a pattern whose own spec amount is switched on are also left alone, because the pattern carries its own material. Everything else is lifted. If a design truly needs exact no-coat, check the exported file with the Inspector instead of trusting the preview.'},
    ],
    examples=[
        {'title': 'The slider that stops', 'goal': 'Understand why B COAT will not go glossier than 16.',
         'settings': {'Base': 'Gel Coat (coat 16)', 'B COAT': '-40'},
         'result': 'The result is clipped at 16. Nothing changes, because 16 is already the glossiest coat the app allows.'},
        {'title': 'Roughness cannot go under 15', 'goal': 'See the roughness floor on a non-metal finish.',
         'settings': {'Base': 'Gel Coat', 'Spec values': 'metal 0, roughness 15, coat 16', 'G ROUGH': '-40'},
         'result': 'Roughness stays at 15 because the pixel is not chrome tier. Only metal of 240 or more may go lower.'},
    ],
    combos=[{'with': 'spec.channel_b_clearcoat', 'why': 'The blue channel details behind rule one.'},
            {'with': 'spec_sculpt.iron_safe_export', 'why': 'The Spec Sculpt Lab applies the same rules before it writes a file.'},
            {'with': 'spec.channel_sliders', 'why': 'Slider shifts are clipped at 0, 15 and 16 before the final rules run.'}],
    faq=[
        {'q': 'Can I turn the iron rules off?', 'a': 'No. They protect every file from values that look wrong in the sim.'},
        {'q': 'Why is my chrome allowed roughness 2 but my gloss is not?', 'a': 'Only pixels with metal of 240 or more may go below 15. Gloss has metal 0, so it is held at 15.'},
        {'q': 'Does a hand-edited spec file get checked?', 'a': 'Only if you bring it back into the app as an imported spec. Files you edit elsewhere are your responsibility.'},
        {'q': 'Does the preview follow the same rules?', 'a': 'Yes. The preview runs the same final rules as the export.'},
    ],
    mistakes=[
        {'symptom': 'My exact coat of 0 became 16.', 'cause': 'Normal zones are floored at 16. Only imported specs and pattern-driven pixels keep 0.', 'fix': 'Use coat 16 for the shiniest look, or import an authored spec if you really need coat off.'},
        {'symptom': 'A blend between a clear zone and a bare zone looks whitewashed.', 'cause': 'The blend crossed coat 1 to 15.', 'fix': 'Hard-edge the zone, or keep both sides at 16 or more.'},
        {'symptom': 'A roughness below 15 got lifted.', 'cause': 'The pixel is not chrome tier.', 'fix': 'Raise metal to 240 or more if you want a mirror there.'},
    ],
    protips=['The iron rules are a safety net, not a design tool. If a slider hits one, the look is telling you to change the base finish instead.',
             'Resizing a spec picture in an editor can reintroduce illegal values. Re-render at 2048 instead.'])

enrich(D, 'spec.paint_spec_marriage', level='intermediate',
    sources=[AIK + '05_design_and_taste.md:4', AIK + '02_spec_and_finishes.md:15', AIK + '08_livery_design.md:16', W + ':3796-3797', W + ':4236-4246', AIK + '11_finish_advisor.md:25'],
    deep=[
        {'heading': 'What actually makes a finish pop', 'body': 'Saturation alone does not pop. Complementary neighbour contrast does: deep blue beside warm gold, black beside hot pink, white beside red. Then make the spec the colour-opposite of the paint: a warm paint on matte next to a cool colour on metal reads richer than one shine everywhere. Adjacent areas should differ in colour or in shine, ideally both. One loud hero area (hood or a big panel), calm neighbours, and fine texture for depth, not big blobs.'},
        {'heading': 'Paint guidance by material', 'body': 'Silver chrome: near-white neutral paint. Coloured chrome or candy: a bright, controlled colour, since an over-saturated dark paint buries the mirror. Pearl: body hue plus lighter and darker flake colours, because a uniform paint makes the spec look pasted on. Gloss black: near-black paint with metal kept at 0. Matte colour: a normal body hue with roughness and coat raised, never reduced alpha. Weathering: oxide colours lined up with the worn spec.'},
        {'heading': 'A palette that reads as expensive', 'body': 'Two or three colours plus one accent looks expensive; five looks cheap. A good split is about 60 percent dominant, 30 percent accent, 10 percent trim. Candy, pearl, metallic, satin or gloss in the livery colour read premium on big areas; chrome on a large area is loud and shows every flaw, so use it on accents, trim and thin lines. A chrome pinstripe on a matte car reads as real chrome.'},
    ],
    examples=[
        {'title': 'Two-material hood', 'goal': 'Make the hood the hero without a new colour.',
         'settings': {'Hood zone': 'Candy', 'Hood colour': 'Deep red, bright and controlled', 'Roof and sides': 'Soft Matte, same family', 'Stripe': 'Satin Chrome'},
         'result': 'Glossy candy hood, flat neighbours and a bright satin accent: three surfaces, one palette.'},
        {'title': 'Stealth with one accent', 'goal': 'A dark car that still has life.',
         'settings': {'Body': 'Matte black-grey at metal 0, roughness 200', 'Accent': 'Satin at metal 0, roughness 100', 'Numbers': 'Light grey, high contrast'},
         'result': 'The matte body hides panel lines, the satin accent gives a quiet edge, and the numbers stay readable.'},
    ],
    combos=[{'with': 'finishes.what_makes_a_finish_pop', 'why': 'The livery view of the same idea, with zone roles.'},
            {'with': 'spec.metal_rough_grid', 'why': 'Pick the two opposite corners for your neighbouring zones.'},
            {'with': 'zones.priority', 'why': 'Neighbouring zones only show contrast if the right zone owns the shared edge.'}],
    faq=[
        {'q': 'Why does my bright colour look flat?', 'a': 'Probably the shine is the same everywhere. Add a neighbour with the opposite shine.'},
        {'q': 'Does more saturation help?', 'a': 'No. Contrast between neighbours helps. More saturation mostly muddies a spec.'},
        {'q': 'What goes behind numbers?', 'a': 'A calm gloss, satin or matte with strong colour contrast. Avoid sparkle, strong patterns and colour-shifting finishes there.'},
        {'q': 'Chrome on the whole car?', 'a': 'It is loud and shows every flaw. It works as a show-car statement, but accents and trim usually look better.'},
    ],
    mistakes=[
        {'symptom': 'Everything is metallic and nothing stands out.', 'cause': 'One shine used all over.', 'fix': 'Choose a hero zone, then give the neighbours matte or satin.'},
        {'symptom': 'Black chrome looks like a black hole.', 'cause': 'Very dark paint under high metal.', 'fix': 'Use Dark Chrome 250, 15, 40, or lighten the paint a little.'},
        {'symptom': 'It looked great as a thumbnail and muddy on the car.', 'cause': 'Mid-tone mud at thumbnail size stays mud on the car.', 'fix': 'Judge on the car at a distance and on a sunny track.'},
    ],
    protips=['Test the contrast with the spec views off: if two zones are only different in shine, they will read the same in a dull photo and different in the sim.',
             'Flat paint with chrome trim lines is the modern retro look; gloss everywhere is the showroom look.'])

enrich(D, 'spec.how_layers_combine', level='pro',
    sources=[ENG + ':18336-18340', ENG + ':18353-18372', ENG + ':18563', ENG + ':20225-20255', ENG + ':20317-20366', ENG + ':20387-20432', ENG + ':20735-20747',
             COMP + ':2967-2970', COMP + ':5287-5291', COMP + ':3944', 'paint-booth-2-state-zones.js:5099'],
    deep=[
        {'heading': 'Step 1: which zone owns each pixel', 'body': 'Every zone builds a mask from its colour match or drawn area, softened by about 3 pixels unless the zone has a hard edge. Zones are processed in list order and an earlier zone claims first: where two overlap, the lower number wins and the later one is cut back. A soft mask above 0.15 is hardened to full ownership. At the end a zone replaces the spec fully where its mask is above 0.5, blends linearly between 0.05 and 0.5, and leaves the spot alone below that. Paint is blended by the mask in the paint stack.'},
        {'heading': 'Step 2: the paint stack inside a zone', 'body': 'In order: the base finish paint (skipped when the colour mode is Use source paint, so only the spec changes); the base colour mode (solid, gradient, finish colours); hue, saturation and brightness inside the mask (hue up to 180 degrees either way, skipped if all three are under half a percent); base scale placement; then BASE STRENGTH, which mixes the result over your original paint. Patterns come after Base Strength, so lowering it never dims a pattern. Last come the second to fifth base overlays.'},
        {'heading': 'Step 3: the spec stack inside a zone', 'body': 'In order: the base finish spec; SPEC STRENGTH pulling metal toward 0, roughness toward 128 and coat toward 16; base scale, rotation and clear-coat quality; a second base blended through its gradient; spec patterns (metal, roughness and coat ticks); pattern spec amount; second to fifth base overlays; then the versioned spec overlays, applied last on the finished material as a mix toward their target. After the finish is built: an imported spec map if present, spec placement, then the three SPEC sliders (R, G, B), then Material Remap, Material Override and Lighting Mask, in that order.'},
        {'heading': 'Step 4: after every zone is done', 'body': 'The app protects numbers and sponsors: wherever the decal mask is on, the original colour is restored so no overlay can repaint them. Wear is applied in one pass, scaled per zone. Decal spec finishes and spec stamps are blended in by their own alpha. Then the final floors run (coat at least 16, roughness at least 15 under metal 240) and the paint and spec files are written. Preview runs exactly the same steps at a smaller size.'},
    ],
    examples=[
        {'title': 'Pearl body with carbon hood stripes', 'goal': 'Build a layered finish and predict each layer.',
         'settings': {'Base Material': 'Gloss (metal 0, roughness 30, coat 16)', 'Second base': 'Pearl at 40%', 'Pattern 1': 'Carbon fibre, Blend', 'Spec overlay': 'Brushed grain, M and R ticked, Strength 50', 'G ROUGH': '+10'},
         'result': 'Pearl shimmer on gloss, a carbon weave that keeps the body colour, grain only in the shine, and a slightly softer gloss from the slider at the end.'},
        {'title': 'Overlap on purpose', 'goal': 'Make a stripe beat the body where they overlap.',
         'settings': {'Zone 1': 'Stripe', 'Zone 2': 'Body'},
         'result': 'The stripe is higher in the list, so it keeps the overlap. Swap the order and the body wins.'},
    ],
    combos=[{'with': 'spec.channel_sliders', 'why': 'Step 3 ends with these three sliders.'},
            {'with': 'spec.strength_and_independent', 'why': 'Spec Strength sits at the start of Step 3 and Base Strength at the end of Step 2. They never touch each other.'},
            {'with': 'patterns.layers_and_stacking', 'why': 'The pattern layers that sit between the base and the overlays.'}],
    faq=[
        {'q': 'Does Base Strength change the shine?', 'a': 'No. Base Strength only blends the paint toward your original colours. SPEC STRENGTH changes the shine.'},
        {'q': 'Which zone wins when two overlap?', 'a': 'The one higher in the list (lower number). New zones go on top.'},
        {'q': 'What runs last, my slider or my overlay?', 'a': 'The overlays run first as part of the finish, then the R, G and B sliders, then Remap, Override and Lighting Mask.'},
        {'q': 'Does the preview match the export?', 'a': 'It runs the same steps and floors at a smaller size, so very fine detail can look different from the full render.'},
    ],
    mistakes=[
        {'symptom': 'My pattern is not dimmed when I lower Base Strength.', 'cause': 'Patterns are added after Base Strength.', 'fix': 'Lower the pattern opacity instead.'},
        {'symptom': 'A zone changes nothing.', 'cause': 'A higher zone covers it, the colour match selects nothing, or Base Strength or intensity is low.', 'fix': 'Check the list order, then the zone mask, then the strength sliders.'},
        {'symptom': 'Sponsors got a chrome look.', 'cause': 'The body zone also grabbed the sponsor layer, and decals take the material under them.', 'fix': 'Limit the body zone to the car paint layer and use a decal spec finish for the sponsors.'},
    ],
    protips=['Quick triage order for any odd look: zone owner, then base colour mode, then Base Strength, then SPEC STRENGTH, then the sliders.',
             'There are at most five pattern layers and five spec overlays per zone, and each zone renders with its own random seed, so two zones with the same finish never repeat exactly.'])

enrich(D, 'spec.colour_space_and_files', level='intermediate',
    sources=[SUP + ':63', SUP + ':66', SUP + ':69', SUP + ':72', W + ':4307-4308', ENG + ':20772-20828', AIK + '10_support_troubleshooting.md:30'],
    deep=[
        {'heading': 'Two files, two kinds of data', 'body': 'The paint file is 24-bit colour, read as normal screen colour. The spec file is 32-bit with alpha and is read as raw numbers, with no colour correction. Both are 2048 by 2048 for a standard car, and the size must match the car template exactly, or iRacing shows the paint shop colours instead. An optional normal map can be written from the metal channel.'},
        {'heading': 'The compiled copy trap', 'body': 'The first time iRacing loads your files it compiles the spec into a faster copy next to it. If you render again and the look does not change, that compiled copy is stale. Press Ctrl+R in the sim to reload the car textures. If the old shine still shows, move that car\'s compiled spec copy out of the folder and reload. Other drivers only see your spec if the compiled copy is shared too; Trading Paints shares it.'},
        {'heading': 'Byte order and tools', 'body': 'The spec file stores its bytes as blue, green, red, alpha, while tools show red, green, blue, alpha. That is normal, so never swap channels by hand. Saving the spec through a photo editor can shift values, apply colour management or sharpen edges, all of which break the iron rules.'},
    ],
    examples=[
        {'title': 'Spec change not visible', 'goal': 'Make a new render show up in the sim.',
         'settings': {'After the render': 'Ctrl+R in iRacing', 'If still old': 'Move the compiled spec copy for that car out of the folder, then Ctrl+R again'},
         'result': 'iRacing rebuilds the compiled copy from the new spec and shows the new shine.'},
        {'title': 'Paint all black', 'goal': 'Fix a paint file that loads wrong.',
         'settings': {'Paint file': '24-bit, no template alpha', 'Size': '2048 by 2048', 'iRacing option': '2048 paint textures on'},
         'result': 'The paint loads with its real colours.'},
    ],
    combos=[{'with': 'spec.channel_a_mask', 'why': 'The 32-bit spec file is the one with alpha.'},
            {'with': 'spec.iron_rules', 'why': 'Editing the file elsewhere can break the rules the app enforces.'}],
    faq=[
        {'q': 'How big must the paint be?', 'a': 'Exactly 2048 by 2048 (or 1024 by 1024), 24-bit.'},
        {'q': 'Why do other drivers not see my shine?', 'a': 'iRacing never shares textures. Files must be in their folder; Trading Paints does that, and its spec needs the compiled copy.'},
        {'q': 'Why is my paint all black?', 'a': 'It was saved with the template alpha channel instead of 24-bit, or 2048 paint textures is off in the sim.'},
        {'q': 'Do I need the spec file at all?', 'a': 'No. Without it iRacing uses the car normal material. Your colours still show.'},
    ],
    mistakes=[
        {'symptom': 'New shine does not show after a render.', 'cause': 'A stale compiled copy.', 'fix': 'Ctrl+R in the sim, or move the compiled copy out and reload.'},
        {'symptom': 'iRacing shows paint shop colours.', 'cause': 'Wrong size.', 'fix': 'Use the car template size exactly and never resize.'},
    ],
    protips=['In a replay, reload textures at a moment when the car is not in the pit stall.',
             'A render takes seconds to about a minute. If it takes much longer, check how many zones have their own painted area.'])

enrich(D, 'spec.strength_and_independent', level='beginner',
    sources=[COMP + ':428-438', COMP + ':2967-2970', COMP + ':2902', COMP + ':4966-4979', AIK + 'sliders_and_controls.md:9', W + ':4262-4267', AIK + '09_field_playbook.md:13'],
    deep=[
        {'heading': 'The exact maths of SPEC STRENGTH', 'body': 'Strength pulls the base finish toward a neutral plate: metal becomes metal times strength, roughness becomes 128 plus (roughness minus 128) times strength, coat becomes 16 plus (coat minus 16) times strength. At 100 percent nothing changes. At 50 percent Chrome (255, 2, 16) becomes about (128, 65, 16). At 0 you get metal 0, roughness 128, coat 16, a neutral gloss. It runs on the base spec before patterns and overlays, so those keep their own strength.'},
        {'heading': 'Three strengths that are easy to mix up', 'body': 'SPEC STRENGTH changes the shine and leaves colour alone. BASE STRENGTH blends the base paint over your original paint and leaves the spec alone. INTENSITY scales how strong a base texture generator is. Use the right one: less shiny means SPEC STRENGTH, more subtle colour means BASE STRENGTH or intensity, smaller pattern means scale, not strength.'},
        {'heading': 'Independent spec', 'body': 'By default the spec texture follows the base scale and rotation, so a brushed grain turns with the brushed paint. Tick INDEPENDENT SPEC to unlock SPEC SCALE and SPEC ROTATION so the shine texture can be finer, larger or turned differently from the paint. Only the spec moves; the colour stays put.'},
    ],
    examples=[
        {'title': 'Half-chrome', 'goal': 'A softer chrome look without changing finish.',
         'settings': {'Base Material': 'Chrome (Foundation)', 'SPEC STRENGTH': '50%'},
         'result': 'Metal about 128 and roughness about 65: a bright metallic with soft reflections instead of a mirror.'},
        {'title': 'Grain across the paint grain', 'goal': 'Turn the shine texture 45 degrees from the paint texture.',
         'settings': {'INDEPENDENT SPEC': 'On', 'SPEC ROTATION': '45', 'SPEC SCALE': '0.60x'},
         'result': 'The spec grain is finer and diagonal to the base texture.'},
    ],
    combos=[{'with': 'spec.scale_rotation', 'why': 'The two controls that Independent Spec unlocks.'},
            {'with': 'spec.how_layers_combine', 'why': 'Where Spec Strength sits in the order of operations.'},
            {'with': 'spec.channel_sliders', 'why': 'Sliders add after strength; use strength for overall, sliders for one channel.'}],
    faq=[
        {'q': 'Does strength 0 mean dull?', 'a': 'No. It is neutral: metal 0, roughness 128, coat 16, a plain gloss. Coat 16 is the glossiest coat.'},
        {'q': 'Which slider makes the car less shiny?', 'a': 'SPEC STRENGTH, or G ROUGH plus 40.'},
        {'q': 'Does strength change colour?', 'a': 'No. Only the spec.'},
        {'q': 'Why can I not change SPEC SCALE?', 'a': 'It is locked until INDEPENDENT SPEC is ticked.'},
    ],
    mistakes=[
        {'symptom': 'Lowering strength made the car look like plain gloss.', 'cause': 'Strength pulls toward a neutral plate, so every finish converges on plain gloss at 0.', 'fix': 'Lower in small steps, or change the base finish.'},
        {'symptom': 'I used strength to shrink a pattern.', 'cause': 'Strength is not size.', 'fix': 'Use scale. Smaller number means finer and more repeats.'},
    ],
    protips=['Authored imports (SHOKK DROP sets) ignore SPEC STRENGTH on purpose, so their hand-tuned numbers stay exact.',
             'The same slider also scales the noise in noisy bases, so on those the effect is a bit stronger than the plain formula.'])

enrich(D, 'spec.scale_rotation', level='intermediate',
    sources=['paint-booth-2-state-zones.js:2111-2115', AIK + 'how_do_i.md:176-181', W + ':3492-3503', W + ':3521-3533', ENG + ':20156-20169', 'engine/core.py:1498-1527'],
    deep=[
        {'heading': 'What scale really does on a whole car', 'body': 'The canvas is 2048 by 2048 and covers the entire car. A feature of 8 to 32 pixels reads as texture; 64 pixels is the size of a side mirror. Scale runs from 0.05 to 5 times with 1.00 as the finish default, and smaller means more repeats, so 0.30 to 0.60 is typical for fine detail. The app also auto-scales a pattern to the zone size: 1.0 if the zone covers more than 60 percent of the canvas, otherwise about the square root of its area share, between 0.15 and 1.'},
        {'heading': 'Spec placement is its own pass', 'body': 'After the zone finish is built, a separate placement pass moves, turns, scales and flips only the spec. That is why independent spec scale and rotation never recolour anything. Rotation goes 0 to 355 degrees in steps of 5.'},
        {'heading': 'The fine-detail rule', 'body': 'Fine is 4 to 8 pixels, micro is 1 to 2 pixels (car-scale sparkle), and 8 to 32 pixels is the sweet spot for a finish that reads as material. When detail seems enough, make it 25 to 40 percent finer. If a finish does not show up, add more small events and more channel contrast; do not make the marks bigger.'},
    ],
    examples=[
        {'title': 'Brushed grain that reads as steel', 'goal': 'Fine, horizontal brushing on a hood.',
         'settings': {'Base Material': 'Brushed (Foundation)', 'INDEPENDENT SPEC': 'On', 'SPEC SCALE': '0.50x', 'SPEC ROTATION': '0'},
         'result': 'Twice as many grain lines across the hood, the size of real brushing at distance.'},
        {'title': 'Carbon on the diagonal', 'goal': 'Turn a weave without turning the paint.',
         'settings': {'INDEPENDENT SPEC': 'On', 'SPEC ROTATION': '45'},
         'result': 'The weave in the spec runs diagonally while any painted pattern stays put.'},
    ],
    combos=[{'with': 'patterns.scale_rotation_opacity', 'why': 'The paint version of the same idea. Pattern scale is a separate control.'},
            {'with': 'spec.strength_and_independent', 'why': 'Independent spec must be ticked first.'}],
    faq=[
        {'q': 'Why is my texture huge?', 'a': 'Scale 1.00 on a whole-car canvas is often too big. Go to 0.3 to 0.6.'},
        {'q': 'Does spec scale change the paint?', 'a': 'No. Spec only.'},
        {'q': 'What is the best size?', 'a': 'Features of 8 to 32 pixels at 2048.'},
        {'q': 'Does rotation work on flat finishes?', 'a': 'There is nothing to turn on a flat spec. It needs a texture, such as brushed grain or a weave.'},
    ],
    mistakes=[
        {'symptom': 'Scale is greyed out.', 'cause': 'INDEPENDENT SPEC is not ticked.', 'fix': 'Tick it first.'},
        {'symptom': 'Fine detail disappears in the preview.', 'cause': 'The preview is smaller than the 2048 export.', 'fix': 'Zoom in or read the spec views before deciding it did nothing.'},
    ],
    protips=['Preview is about 768 pixels for a 2048 sheet. Micro flake and holographic grating at small scale average out and look flat there.',
             'Rotation of 45 degrees on a weave is the quickest way to a different carbon look.'])

enrich(D, 'spec.channel_sliders', level='intermediate',
    sources=[ENG + ':20225-20250', ENG + ':20253-20255', AIK + 'sliders_and_controls.md:18', AIK + 'how_do_i.md:124-130', 'paint-booth-2-state-zones.js:2143', ENG + ':20735-20747'],
    deep=[
        {'heading': 'Exactly what a slider does', 'body': 'Each slider adds its value, from minus 127 to plus 127, to that channel under the zone mask. The result is clipped at 0 to 255, with floors of 0 for metal, 15 for roughness and 16 for coat. Sliders at 0 (or all under half a point) are ignored. The sliders run after patterns, overlays and blend modes, so they are the last creative step; only Remap, Override and Lighting Mask come after.'},
        {'heading': 'Which way each one goes', 'body': 'Metal plus means more metal. Roughness plus means duller, minus means glossier. Coat plus means duller, because blue is backwards, minus means glossier and stops at 16. Rough recipes: satin from gloss is G ROUGH plus 40 to plus 80 with B COAT plus 30 to plus 60. Wetter is G ROUGH minus and B COAT minus.'},
        {'heading': 'Sliders versus other tools', 'body': 'Sliders shift a whole zone evenly. Material Remap squeezes a channel into a new low to high range and keeps variation. Material Override sets flat values. Spec Strength pulls everything toward neutral. A shift of 20 is subtle, 50 is a clear style change, and anything near 100 usually cancels the finish character.'},
    ],
    examples=[
        {'title': 'Satin from gloss', 'goal': 'Take a gloss body to satin without changing the base.',
         'settings': {'Base Material': 'Gloss', 'G ROUGH': '+60', 'B COAT': '+45'},
         'result': 'Roughness around 90 and coat around 61: a quiet satin.'},
        {'title': 'Duller candy', 'goal': 'Take some wet depth out of a candy zone.',
         'settings': {'Base Material': 'Candy (metal 200, roughness 15, coat 16)', 'G ROUGH': '+30', 'B COAT': '+20'},
         'result': 'Roughness 45 and coat 36: the candy colour stays but the glassy look relaxes into a satin candy.'},
    ],
    combos=[{'with': 'spec.presets_feels', 'why': 'Feels are slider combinations saved as one click.'},
            {'with': 'spec.material_override_remap_lighting', 'why': 'The tools that run right after the sliders.'},
            {'with': 'spec.iron_rules', 'why': 'The floors that clip slider results.'}],
    faq=[
        {'q': 'Why does B COAT plus make it duller?', 'a': 'Because blue is backwards. The number is added to the coat value, where bigger means less coat.'},
        {'q': 'Why did my slider stop working?', 'a': 'The channel reached its floor or ceiling.'},
        {'q': 'Can sliders recolour?', 'a': 'No. They only change metal, roughness and coat.'},
        {'q': 'Slider or SPEC STRENGTH?', 'a': 'Use the slider to move one channel. Use strength to scale the whole finish.'},
    ],
    mistakes=[
        {'symptom': 'Large shifts make the finish look generic.', 'cause': 'A shift near 100 overwhelms the base values.', 'fix': 'Choose a different base finish and nudge by 20 to 40.'},
        {'symptom': 'Wetter did not work on a gel coat.', 'cause': 'It is already at the floor of 15 and 16.', 'fix': 'Nothing more to gain. Change the pattern or the paint.'},
    ],
    protips=['The B COAT slider tooltip in the app says higher is a stronger mirror. The number is really added to the coat value where bigger means duller, so judge by eye.',
             'Save a good slider set as a Feel so it can be reused on other zones.'])
print('part B done')
