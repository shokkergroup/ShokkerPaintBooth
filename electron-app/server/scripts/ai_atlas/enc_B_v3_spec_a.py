"""V3 depth for the spec map articles, part A (what it is, the four channels, colour reading, the grid).
Every number is from the engine, the registry, the wiki spec guide or the support answers; sources listed per article.
Run: python scripts/ai_atlas/enc_B_v3_spec_a.py   (idempotent; then assemble('spec'))"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'spec'
ENG = 'shokker_engine_v2.py'
COMP = 'engine/compose.py'
BASE = 'engine/base_registry_data.py'
W = 'SPB_WIKI.html'
SUP = 'js/spb-support-answers.js'
AIK = 'docs/ai_knowledge/'

enrich(D, 'spec.what_is_spec_map', level='beginner',
    sources=[W + ':3566-3573', W + ':3796-3797', SUP + ':37', ENG + ':267', ENG + ':20735-20744'],
    deep=[
        {'heading': 'How iRacing reads the two pictures', 'body': 'iRacing gets two pictures for your car. The paint picture is the colour you see. The spec picture is four numbers per pixel that tell the lighting engine what the surface is made of: red is metal, green is roughness, blue is the clear layer on top, alpha is a lighting mask. The sim lights every pixel from those four numbers, using its sun, sky and your view angle. That is why the same paint can look like wet enamel, brushed steel or flat vinyl without a single colour changing.'},
        {'heading': 'Why paint and spec are never judged apart', 'body': 'Metal reflection is tinted by the paint colour, while clear-coat highlights are close to white. So a metal value of 255 on a near-white paint gives silver, the same value on a dark red gives dark tinted metal, and on near-black it can vanish. The spec only decides how much of each effect you get. The colour you painted decides what that effect looks like. Judge the two together, on the car, never one without the other.'},
        {'heading': 'What Shokker Paint Booth does for you', 'body': 'You never paint these four numbers by hand. Every zone has a base finish that sets a starting metal, roughness and coat, then pattern, overlays and sliders move them. At the very end the app raises any coat value below 16 to 16 and any roughness below 15 to 15 unless the pixel is chrome tier (metal 240 or more), so a render cannot hand iRacing a value that whitewashes. The paint goes out as a 24-bit picture and the spec as a 32-bit picture with alpha, both for the same car.'},
    ],
    examples=[
        {'title': 'Same red, three materials', 'goal': 'See that one colour becomes three looks through spec alone.',
         'settings': {'BASE COLOR': 'Use source paint (spec only)', 'Gloss body': 'Gel Coat (metal 0, roughness 15, coat 16)', 'Satin body': 'Satin (metal 0, roughness 95, coat 70)', 'Chrome body': 'Chrome (metal 255, roughness 2, coat 16)'},
         'result': 'Gel Coat is a wet-looking red, Clear Satin is a soft low-sheen red, and Chrome turns the red into tinted mirror metal. The paint picture is identical in all three.'},
        {'title': 'Read a spec colour at a glance', 'goal': 'Tell what a spec picture colour means before opening any tool.',
         'settings': {'Dark green-black 0,30,16': 'normal glossy paint', 'Bright red 255,2,16': 'mirror chrome', 'Bright green': 'very rough, matte', 'White': 'rough metal with the coat off, not chrome'},
         'result': 'You can sort a whole spec picture into gloss, chrome, matte and rough metal just by its colour families.'},
    ],
    combos=[{'with': 'spec.reading_by_colour', 'why': 'Teaches the colour code of a spec picture so you can read any export.'},
            {'with': 'spec.iron_rules', 'why': 'The three limits applied to every render, and why they exist.'},
            {'with': 'spec.paint_spec_marriage', 'why': 'How to choose paint and spec so they help each other.'}],
    faq=[
        {'q': 'Do I have to understand the spec map to use the app?', 'a': 'No. Pick a finish and the app sets all four numbers. Read this when you want to tune a shine, fix a washed-out look or build your own material.'},
        {'q': 'Does the spec map change how the car drives?', 'a': 'No. Spec only changes how the car looks, never how it handles.'},
        {'q': 'What happens if there is no spec file?', 'a': 'iRacing falls back to the car\'s normal material and your colours still show. You just lose your custom shine.'},
        {'q': 'Why does iRacing look different from the preview?', 'a': 'The preview is a quick design view. iRacing lights the real render with its own sun, shadows and materials, and it reads the spec file separately, so shine only shows in the sim.'},
    ],
    mistakes=[
        {'symptom': 'The finish looks washed out and white in the sim.', 'cause': 'A clear-coat value between 1 and 15 reached iRacing. That band is treated as no coat or a legacy value.', 'fix': 'Re-render from the app instead of editing the file by hand. The app raises every coat value to at least 16.'},
        {'symptom': 'Silver chrome comes out black or grey.', 'cause': 'Metal reflection takes the paint colour, and the paint under it was dark or mid grey.', 'fix': 'Paint the zone near-white, or use a Foundation chrome with Use source paint if you want to keep your colours and accept tinted chrome.'},
        {'symptom': 'I changed a spec value and nothing happened.', 'cause': 'The old compiled copy of the spec is still loaded by the sim.', 'fix': 'Render again, then press Ctrl+R in iRacing. If it still looks old, move the compiled spec copy for that car out of the folder and reload.'},
    ],
    protips=['The preview shows the same colours as the render but not the same shine, so judge shine on the spec views (R METAL, G ROUGH, B COAT) and in the sim.',
             'A dark paint under high metal is buried: nearly black until the right reflection arrives. Colour first, then metal.'])

enrich(D, 'spec.channel_r_metallic', level='beginner',
    sources=[W + ':3843-3850', ENG + ':20225-20250', COMP + ':428-438', BASE + ':425-430'],
    deep=[
        {'heading': 'The six metal bands', 'body': '0 to 15 is plain non-metal: enamel, lacquer, rubber, glass. 16 to 63 is low metal such as carbon, mineral loading or subtle flake. 64 to 127 is pearl, mica and patina. 128 to 175 is strong pearl or anodized metal. 176 to 239 is true metallic: aluminium, gunmetal, brushed titanium, metallic candy. 240 to 255 is chrome tier, the only band allowed to push roughness below 15. Foundation anchors: Pearl 100, Metallic 200, Candy 200, Satin Chrome 250, Chrome 255.'},
        {'heading': 'Metal eats the paint colour', 'body': 'As metal goes up, the surface shows less of its own diffuse colour and more of a tinted reflection. Past about 240 almost everything you see is reflection, tinted by the paint colour. That is why silver chrome needs near-white paint and why a fully metallic dark red looks nearly black. Partial-metal finishes such as pearl, metallic and satin chrome keep their colour much better than full chrome.'},
        {'heading': 'What moves metal after the base', 'body': 'Spec Strength pulls metal toward zero: metal becomes metal times strength, so 50 percent of Chrome is about 128. The R METAL slider adds a value from minus 127 to plus 127 under the zone mask and clips at 0 and 255. Spec patterns add their pattern to metal when the M tick is on. After those, the Material Remap tool squeezes metal into a new low-to-high range and the Material Override tool can set it flat, so those two can overrule the slider.'},
    ],
    examples=[
        {'title': 'Pearl that shimmers but keeps its colour', 'goal': 'Get depth without losing the paint colour.',
         'settings': {'Base Material': 'Pearl (Foundation)', 'BASE COLOR': 'Use source paint (spec only)', 'Spec values': 'metal 100, roughness 40, coat 16'},
         'result': 'A soft pearl shimmer that sits on your own colours, about a third of full metal.'},
        {'title': 'Gunmetal sheen on a dark car', 'goal': 'Make a dark car read as metal, not as black paint.',
         'settings': {'Base Material': 'Metallic (Foundation)', 'R METAL': '+20', 'Spec values': 'metal 200 to 220, roughness 40 to 50'},
         'result': 'Dark paint with a real metallic sparkle in sun. Going all the way to 255 would bury the colour instead.'},
    ],
    combos=[{'with': 'spec.channel_g_roughness', 'why': 'Metal says what it is, roughness says how sharp it reflects. Always set them as a pair.'},
            {'with': 'spec.metal_rough_grid', 'why': 'Shows where every metal and roughness pair lands as a material.'},
            {'with': 'spec.channel_sliders', 'why': 'Where the R METAL nudge fits in the order of operations.'}],
    faq=[
        {'q': 'What is the best metal value for chrome?', 'a': '255. The Foundation Chrome uses metal 255, roughness 2, coat 16. Anything from 240 up is chrome tier.'},
        {'q': 'Why is my metallic car dark?', 'a': 'Metal reflection inherits the paint colour. Dark paint plus high metal is buried until light hits it. Lower metal to around 180 to 200, or lighten the paint.'},
        {'q': 'Is more metal always shinier?', 'a': 'No. Shine is mostly roughness. Metal controls what the reflection is made of. A rough, metallic surface is satin or brushed, not shiny.'},
        {'q': 'What metal do pearl and candy use?', 'a': 'Pearl is 100. Candy is 200 in the current registry, with a low roughness of 15 so the tinted coat reads deep.'},
    ],
    mistakes=[
        {'symptom': 'Gloss black turned into dark metal.', 'cause': 'Metal was raised, by a slider, a metallic overlay or a wrong base.', 'fix': 'Keep metal at 0 with a wet-look gloss such as Gel Coat 0, 15, 16 or Gloss 0, 30, 16.'},
        {'symptom': 'Coloured chrome looks muddy.', 'cause': 'A dark, over-saturated paint is under the metal and buries the reflection.', 'fix': 'Use a bright, controlled colour of the same hue under chrome or candy.'},
        {'symptom': 'Metal slider seems to stop working.', 'cause': 'It was already at 0 or 255, where the result is clipped.', 'fix': 'Move the other way, or change the base so there is room above or below.'},
    ],
    protips=['Metal bands decide the legal roughness: only metal 240 or more may have roughness under 15. A chrome-tier pixel is the one place a mirror is allowed.',
             'Spec Strength is the quick way to get half-metal: 50 percent strength on Chrome gives about 128, a pearl-level metal, without picking another finish.'])

enrich(D, 'spec.channel_g_roughness', level='beginner',
    sources=[W + ':3858-3868', ENG + ':270', ENG + ':20735-20737', COMP + ':428-438', AIK + 'sliders_and_controls.md:18'],
    deep=[
        {'heading': 'Nine roughness bands', 'body': '0 to 14 razor mirror, reserved for chrome-tier pixels. 15 to 29 wet gloss. 30 to 59 high gloss. 60 to 99 satin gloss. 100 to 129 satin or eggshell. 130 to 159 semi-matte. 160 to 199 matte or blasted. 200 to 229 flat. 230 to 255 dead or porous. Anchors: Gel Coat 15, Gloss 30, Semi Gloss 55, Satin 95, Eggshell 140, Matte 200, Primer 215, Flat Black 250.'},
        {'heading': 'The floor of 15 and the chrome exception', 'body': 'Roughness below 15 is reserved for mirror metal, so every render lifts it to 15 wherever metal is under 240. Chrome-tier pixels, metal 240 or more, keep their low values: Foundation Chrome is roughness 2. Pixels that come from a pattern whose own spec amount is on are exempt from this floor.'},
        {'heading': 'Smooth ramps smear, steps travel', 'body': 'A continuous high-roughness gradient makes the highlight smear across the panel. Quantised roughness steps make the highlight jump in controlled stages as the camera moves, which is how engineered finishes get a sparkle that travels. Spec Strength pivots roughness around 128: roughness becomes 128 plus (roughness minus 128) times strength, so strength 0 gives a neutral 128.'},
    ],
    examples=[
        {'title': 'Make a car less shiny without changing colour', 'goal': 'Tame a too-glossy zone.',
         'settings': {'G ROUGH': '+40', 'SPEC STRENGTH': '70%'},
         'result': 'Roughness rises by 40 so reflections soften. Either control works; the slider adds, the strength pulls toward 128.'},
        {'title': 'Satin from gloss', 'goal': 'Move from a wet look to a quiet satin.',
         'settings': {'Base Material': 'Clear Satin (Foundation)', 'BASE COLOR': 'Use source paint (spec only)', 'Spec values': 'metal 0, roughness 100, coat 75'},
         'result': 'The same colours with a low sheen that hides small flaws.'},
    ],
    combos=[{'with': 'spec.channel_b_clearcoat', 'why': 'Roughness and coat together make satin versus matte. Raising roughness alone leaves a glossy halo.'},
            {'with': 'spec.channel_sliders', 'why': 'G ROUGH is added after patterns and before remap, and is clipped at 15.'},
            {'with': 'spec.iron_rules', 'why': 'The floor of 15 and the chrome exception in one place.'}],
    faq=[
        {'q': 'What roughness is a mirror?', 'a': '0 on paper, but only chrome-tier pixels (metal 240 or more) may go under 15. Foundation Chrome uses 2.'},
        {'q': 'Why can I not go below 15 on a gloss car?', 'a': 'The app lifts non-chrome roughness to 15 on every render because lower values flare badly in the sim.'},
        {'q': 'Which is better for matte, roughness or coat?', 'a': 'Both. Matte colour is roughly roughness 200 and coat 160, for example. Do not use alpha to fake matte.'},
        {'q': 'Does roughness change the colour?', 'a': 'Not directly. It changes how wide and bright the reflection is, which can make a colour look lighter or deeper.'},
    ],
    mistakes=[
        {'symptom': 'Matte paint still has a glossy halo.', 'cause': 'Roughness was raised but the clearcoat byte was left at 16, so a sharp coat layer sits over a rough base.', 'fix': 'Raise coat to around 160 as well, or start from Soft Matte (0, 200, 165).'},
        {'symptom': 'Highlight smears into one large blur.', 'cause': 'A smooth roughness gradient across the panel.', 'fix': 'Use a few distinct roughness steps, or a spec pattern, so the highlight moves in controlled jumps.'},
        {'symptom': 'Mirror finish looks dull.', 'cause': 'Roughness above 15 on a metal 255 surface, or coat byte high.', 'fix': 'Start from Chrome (255, 2, 16) and check the B COAT view is dark green-blue, not bright.'},
    ],
    protips=['Satin is not one number. Eggshell sits at roughness 140, Satin at 95 and Semi Gloss at 55. Pick the base that matches the look instead of dialling roughness blind.',
             'Wet droplets look: base 0, 22, 16 with rims at roughness 15 and the lens at 35 to 70, in 8 to 24 pixel drops.'])

enrich(D, 'spec.channel_b_clearcoat', level='intermediate',
    sources=[W + ':3873-3891', ENG + ':267', ENG + ':20738-20744', W + ':4268-4274', W + ':4178'],
    deep=[
        {'heading': 'The backwards channel in full', 'body': 'Blue 16 is the strongest active coat. Values rise toward 255 as the coat fades: 17 to 31 very strong, 32 to 63 strong to medium, 64 to 127 satin, 128 to 191 dull, 192 to 254 almost none, 255 none. Values 0 to 15 are treated by the sim as no coat or a legacy value. 255 is the raw maximum byte but the weakest clearcoat. Old notes that call it maximum are wrong.'},
        {'heading': 'The floor of 16 and its two exceptions', 'body': 'In a normal render every coat value is raised to at least 16, including matte, so no pixel lands in the 1 to 15 band that whitewashes. The two exceptions are pixels from an imported spec (including the SHOKK DROP authored sets) and pixels where a pattern spec amount is on; those keep their exact values, 0 included. Resizing or smoothing a spec picture can create 1 to 15 values by accident, which is another reason to re-render instead of resizing.'},
        {'heading': 'Clearcoat quality and strength', 'body': 'The quality control maps straight onto the byte: coat = 16 + (1 minus quality) times 239. Quality 1.0 is coat 16, quality 0.5 is about 135, quality 0 is 255. Spec Strength pulls coat toward 16: coat becomes 16 + (coat minus 16) times strength, so strength 0 gives the full glossy 16. Never blend a coat value from 0 to 16 across an edge; the blend passes through the dead 1 to 15 band. Use a hard edge or blend from 16 upward.'},
    ],
    examples=[
        {'title': 'Candy depth', 'goal': 'A deep wet colour on a metallic body.',
         'settings': {'Base Material': 'Candy', 'Spec values': 'metal 200, roughness 15, coat 16', 'B COAT': '0'},
         'result': 'Maximum coat on a tinted base, which is what makes candy look bottomless.'},
        {'title': 'Soft matte without glare', 'goal': 'A flat stealth finish that does not shine at an angle.',
         'settings': {'Base Material': 'Soft Matte (Foundation)', 'Spec values': 'metal 0, roughness 200, coat 165', 'B COAT': '+20'},
         'result': 'Roughness and coat are both high so no wet halo appears. Pushing coat up further removes the last bit of sheen.'},
    ],
    combos=[{'with': 'spec.channel_g_roughness', 'why': 'The pair that separates satin from matte.'},
            {'with': 'spec.iron_rules', 'why': 'Why the coat floor is 16 and where the exceptions are.'},
            {'with': 'spec_sculpt.iron_safe_export', 'why': 'The Spec Sculpt Lab applies the same floor to every file it writes.'}],
    faq=[
        {'q': 'Is a bigger blue number more clearcoat?', 'a': 'No. It is the reverse. 16 is the strongest coat and 255 is none.'},
        {'q': 'Why does the app raise my coat 0 to 16?', 'a': 'Values 1 to 15 whitewash in the sim and exact 0 means coat disabled, which in normal renders is also raised to 16. Only imported specs and pattern-driven pixels may keep 0.'},
        {'q': 'What coat do Foundation finishes use?', 'a': 'Gloss and Wet Look 16, Pearl 16, Metallic 16, Chrome 16, Candy 16, Satin Chrome 40, Clear Satin 75, Brushed 65, Soft Matte 165.'},
        {'q': 'Can I make blue 255 for a matte look?', 'a': 'Only with an imported or authored spec. In normal zones values from 192 to 254 give almost-no coat and are the usual matte territory.'},
    ],
    mistakes=[
        {'symptom': 'Chrome is dull even on white paint.', 'cause': 'The coat byte is high, for example 255, which removes the coat reflectivity.', 'fix': 'Use coat 16 on chrome. Check the B COAT view is dark.'},
        {'symptom': 'A fade between a clear zone and a bare zone looks whitewashed in the middle.', 'cause': 'The blend passed through coat 1 to 15.', 'fix': 'Use a hard edge, or keep both sides at 16 or more.'},
        {'symptom': 'A slider made the coat go the wrong way.', 'cause': 'B COAT is added straight to the value, so plus means duller.', 'fix': 'Move B COAT left for glossier, right for duller. Nothing goes under 16.'},
    ],
    protips=['Offsetting the coat structure a little from the metal and roughness structure gives a depth cue, because the two highlight lobes peak at different angles.',
             'Clear Satin is only 75 on blue but 100 on green. Many satin looks are about roughness. Coat is what makes the edge of a highlight crisp or soft.'])

enrich(D, 'spec.channel_a_mask', level='intermediate',
    sources=[W + ':3892-3898', W + ':4385', ENG + ':20253-20255', ENG + ':20735-20747', 'paint-booth-v2.html:4148'],
    deep=[
        {'heading': 'What alpha really does', 'body': 'Alpha is a lighting and specular mask, not opacity and not a matte switch. 255 means full normal lighting, which is the production default and what every normal zone has. 128 reduces the response and is only meant for specialised fake-depth or shadow tricks. 0 kills lighting and specular response completely, useful for faked vents or unlit holes, but a flat sticker look if overused.'},
        {'heading': 'Where alpha comes from in a render', 'body': 'The spec starts with alpha 255 everywhere. The only things that change it are the Lighting Mask tool, the Material Override tool (when it sets alpha) and an imported spec map. Soft zone edges also blend alpha across the border, so a soft edge gives a soft lighting fade. The Lighting Mask runs together with the other spec tools after the sliders and before the final coat and roughness floors.'},
        {'heading': 'Matte is not alpha', 'body': 'A common mistake is lowering alpha to get a matte colour. Matte comes from higher roughness and higher clearcoat bytes (for example 0, 200, 160). Reducing alpha only mutes lighting and makes the area look dead and flat, as if it were printed on.'},
    ],
    examples=[
        {'title': 'Fake grille holes', 'goal': 'Make a printed grille look like dark openings.',
         'settings': {'SPEC TOOLS': 'Lighting Mask', 'Mode': 'Kill Lighting A0', 'Zone': 'The grille zone only'},
         'result': 'The grille loses all reflection and reads as a dark gap. Use it on small areas only.'},
        {'title': 'Subtle depth in a recessed panel', 'goal': 'Reduce highlights in a recess without going fully dark.',
         'settings': {'SPEC TOOLS': 'Lighting Mask', 'Mode': 'Reduced Lighting A128'},
         'result': 'Lighting response is reduced there, so the panel reads as recessed.'},
    ],
    combos=[{'with': 'spec.material_override_remap_lighting', 'why': 'The three power tools, with Lighting Mask as the one that touches alpha.'},
            {'with': 'spec.iron_rules', 'why': 'Alpha is the one channel the floors do not touch.'}],
    faq=[
        {'q': 'Should I touch alpha for a normal car?', 'a': 'No. Keep it at 255. The app does that for you.'},
        {'q': 'Can alpha make a hole in the car?', 'a': 'It can fake one for lighting, but it does not change the car shape or the paint.'},
        {'q': 'Why does my matte look flat and dead?', 'a': 'If alpha was lowered, the lighting response is gone. Reset to 255 and use roughness and coat for matte.'},
        {'q': 'Does soft edge affect alpha?', 'a': 'Yes. Soft edges blend alpha as well as colour, so a lighting mask fades softly at its border.'},
    ],
    mistakes=[
        {'symptom': 'A zone looks like a flat sticker on track.', 'cause': 'Alpha is at or near 0 over a large area.', 'fix': 'Set the Lighting Mask back to Full Lighting A255, or Use Source Alpha.'},
        {'symptom': 'Matte colour is not matte.', 'cause': 'Reduced alpha was used as the matte control.', 'fix': 'Raise roughness and coat bytes instead, for example start from Soft Matte.'},
    ],
    protips=['Use Source Alpha in the Lighting Mask tool keeps whatever alpha the zone already has, so it is the no-change choice.',
             'Set a lighting mask only after you are happy with metal, roughness and coat, because it hides their effect where it applies.'])

enrich(D, 'spec.reading_by_colour', level='beginner',
    sources=[W + ':3808-3816', W + ':3733-3745', W + ':3825-3831', ENG + ':23-27'],
    deep=[
        {'heading': 'Why spec pictures use odd colours', 'body': 'The spec picture is data, not paint. Red holds metal, green holds roughness, blue holds the clear coat, so every colour is a code. Bright green does not mean glossy, it means very rough and matte. Bright blue means a weak clear coat, not the strongest one. Red alone means metal. Yellow, red plus green, is rough metal. White is rough metal with the coat off, which is not chrome and not gloss.'},
        {'heading': 'The neighbourhoods worth memorising', 'body': 'A dark green-black such as 0, 30, 16 is the normal gloss neighbourhood. Bright red such as 255, 2, 16 is the chrome neighbourhood. Pure green 0, 255, 0 is dead matte. 255, 255, 0 is chalky or oxidised raw metal. Magenta, 255, 0, 255, is mirror metal with the coat suppressed, an extreme corner used by Fractured night carriers, not ordinary gloss.'},
        {'heading': 'A trap in the preview', 'body': 'The colour views under the live preview show bytes, not a paint job. A hot-pink spec region is just the way high metal, a high coat byte and low roughness pack into colour. On its own it does nothing; the effect needs spatial pattern, crushed dark paint and lighting around it.'},
    ],
    examples=[
        {'title': 'Reading a gloss car', 'goal': 'Confirm a gloss body is healthy.',
         'settings': {'COMBINED view': 'Mostly very dark green-black', 'R METAL view': 'Near black', 'G ROUGH view': 'Dark grey', 'B COAT view': 'Dark'},
         'result': 'Metal 0, roughness about 30, coat 16: wet-looking paint with no metal.'},
        {'title': 'Reading chrome trim', 'goal': 'Confirm chrome parts are set up for a mirror.',
         'settings': {'COMBINED view': 'Bright red', 'R METAL view': 'Near white', 'G ROUGH view': 'Near black', 'B COAT view': 'Dark'},
         'result': 'Metal 255, roughness 2, coat 16: a mirror.'},
    ],
    combos=[{'with': 'spec.inspector', 'why': 'Click a spot and read the exact bytes instead of guessing from colour.'},
            {'with': 'spec.channel_b_clearcoat', 'why': 'Blue is backwards; the most common mis-reading.'}],
    faq=[
        {'q': 'Why is my gloss car green in the spec view?', 'a': 'Dark green-black is the code for normal gloss. The green is the roughness byte, around 30.'},
        {'q': 'What colour is chrome in a spec picture?', 'a': 'Bright red, because metal is 255 and the green and blue bytes are low.'},
        {'q': 'What does white mean?', 'a': 'Rough metal with the coat off. It is not chrome.'},
        {'q': 'Is the spec picture what iRacing shows?', 'a': 'No. iRacing reads the numbers and lights the car with them. The picture is only for you.'},
    ],
    mistakes=[
        {'symptom': 'I thought bright green meant glossy.', 'cause': 'Green is roughness, so bright green is very rough.', 'fix': 'Look for dark green or black for gloss. Use the G ROUGH view to confirm.'},
        {'symptom': 'I thought bright blue meant maximum coat.', 'cause': 'Blue is backwards: 16 is the strongest coat and bright blue is a weak coat.', 'fix': 'The strongest coat is a dark blue channel. Check B COAT.'},
    ],
    protips=['Switch to the single-channel views (R METAL, G ROUGH, B COAT) when something looks wrong. The mixed colour hides which channel is off.',
             'Use the Channels readout to see exact numbers before changing any slider.'])

enrich(D, 'spec.metal_rough_grid', level='intermediate',
    sources=[W + ':3940-3987', W + ':3995-4001', BASE + ':421-461', ENG + ':20735-20747'],
    deep=[
        {'heading': 'Every finish has a home on the grid', 'body': 'Put metal across and roughness down. Low metal with low roughness (0 and 15 to 30) is wet paint and gel coat. Low metal with high roughness (0 and 200 or more) is matte and flat. High metal with low roughness (250 or more and 2 to 15) is chrome. High metal with high roughness (180 and 160) is bead blast and sandblasted metal. The middle band is where brushed, pearl and satin chrome live. The coat then adds the polish on top.'},
        {'heading': 'Anchor cards with exact values', 'body': 'Liquid glaze 0, 15, 16. Wet look 0, 22, 16. Gloss 0, 30, 16. Semi gloss 0, 55, 40. Satin 0, 95, 70. Eggshell 0, 140, 100. Matte 0, 200, 160. Flat black 0, 250, 255. Pearl 100, 40, 16. Metallic 200, 50, 16. Gunmetal 220, 40, 16. Brushed titanium 180, 70, 16. Antique chrome 220, 18, 50. Dark chrome 250, 15, 40. Chrome 255, 2, 16. Satin chrome 250, 45, 40. Candy 200, 15, 16. Gloss carbon 55, 30, 16. Satin carbon 55, 110, 120.'},
        {'heading': 'Live finishes move around their anchor', 'body': 'Real finishes are not one point. Chrome is 245 plus 10 times a displacement for metal and 2 plus 8 times it for roughness. Dark chrome is 230 plus 20 times a field. Metallic flake is 168 plus up to 24 from the body and 14 from the polish. Pearl layers sit at metal 90 plus 55 times a layer. Quantised steps are what make highlights jump instead of smearing.'},
    ],
    examples=[
        {'title': 'Pick a point, then pick the finish', 'goal': 'Choose a Foundation finish from where you want it on the grid.',
         'settings': {'Wet and glossy': 'Gel Coat 0, 15, 16', 'Soft satin': 'Satin 0, 95, 70', 'Brushed steel': 'Brushed 180, 75, 65', 'Mirror': 'Chrome 255, 2, 16'},
         'result': 'Four corners of the grid in four clicks, all keeping your paint colours.'},
        {'title': 'Mix two corners on one car', 'goal': 'Get the matte-beside-metal contrast that makes a livery pop.',
         'settings': {'Body zone': 'Soft Matte 0, 200, 165', 'Stripe zone': 'Satin Chrome 250, 45, 40'},
         'result': 'Two materials from opposite sides of the grid, with a clean edge between them.'},
    ],
    combos=[{'with': 'spec.paint_spec_marriage', 'why': 'Which corner of the grid suits which paint colour.'},
            {'with': 'finishes.foundation_shine_only', 'why': 'The Foundation shelf is the grid, one finish per useful point.'}],
    faq=[
        {'q': 'Where does satin chrome sit?', 'a': 'Near metal 250, roughness 45, coat 40: metal like chrome but with soft reflections.'},
        {'q': 'What separates pearl from metallic?', 'a': 'Metal. Pearl is about 100, metallic about 200.'},
        {'q': 'Where is carbon?', 'a': 'Low metal, 55, with a gloss roughness of 30 or satin 110. The weave itself comes from a pattern.'},
        {'q': 'Why are there matte metals?', 'a': 'Metal and roughness are independent. Matte metallic is 225, 140, 100 and bead blast is 180, 160, 140.'},
    ],
    mistakes=[
        {'symptom': 'My brushed look is just a flat grey metal.', 'cause': 'Only the average values were set. Brushed needs variation in the spec.', 'fix': 'Add a brushed spec overlay on top of Brushed 180, 75, 65.'},
        {'symptom': 'A roughness under 15 was changed back.', 'cause': 'It was a non-chrome pixel, so the floor lifted it.', 'fix': 'Raise metal to 240 or more if you want a true mirror.'},
    ],
    protips=['The grid is two-dimensional but a good finish uses a third dimension: variation. Flat points look like paint swatches, varied points look like materials.',
             'Dark chrome (250, 15, 40) is the quickest way to a black mirror finish; the extra coat makes it less sharp than chrome.'])
print('part A done')
