"""V3 depth for the finishes articles, part B (retro, nature, picker, cards, pop, colour tuning, gradients, scale, overlays, wear).
Colour Lab maths from engine/compose.py _color_lab_blend; wear numbers from apply_wear. Run: python scripts/ai_atlas/enc_B_v3_finishes_b.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'finishes'
ENG = 'shokker_engine_v2.py'
COMP = 'engine/compose.py'
ATL = 'js/spb-ai-atlas-data.js:2'
ZONES = 'paint-booth-2-state-zones.js'
W = 'SPB_WIKI.html'
AIK = 'docs/ai_knowledge/'

enrich(D, 'finishes.retro_cultural', level='beginner',
    sources=[ATL, AIK + '08_livery_design.md:13', AIK + '05_design_and_taste.md:10-17', 'engine/paint_v2/surface_intent.py:144-156', 'VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md:1'],
    deep=[
        {'heading': 'The shine each retro shelf gives you', 'body': 'Averages (metal, roughness, coat): FAR OUT 61, 86, 78, half satin and half high gloss. BAD AND RAD 72, 114, 146, mostly satin. ALL THAT 50, 128, 149, satin to semi-matte. Sock Hop 97, 162, 97, mostly matte like a diner. Groovy Vibes 110, 144, 99, semi-matte. Flames 134, 132, 126, semi-matte. Every one of these brings its own colours.'},
        {'heading': 'Heritage shelves', 'body': 'RISING SUN (52) averages 100, 79, 66 and is mostly high gloss. VIVA MEXICO (58) averages 97, 78, 74, mostly satin. UNION JACKED (45) averages 85, 86, 76. FORBIDDEN DRAGON (20) averages 120, 55, 43, the glossiest. LET FREEDOM RING (10) averages 66, 151, 70, semi-matte. WORLD OF COLOR (100 country palettes) averages metal 38, the lowest, so it reads as pure colour. ANIME INSPIRED (15) averages 96, 140, 145. Viva Mexico, Union Jacked and Rising Sun began as hand-authored images, then got procedural spec on top; that is why they hold up.'},
        {'heading': 'Matching an era', 'body': 'Throwback palettes: 1960s and 70s powder blue with orange, navy and white, harvest orange. 70s and 80s red, white and blue with chrome trim, or black and gold. 80s hot pink, cyan and purple. 90s teal, purple and magenta. Modern: matte black plus one accent. A retro car reads best when the era shelf supplies the colours and the rest of the car is plain.'},
    ],
    examples=[
        {'title': 'Diner retro', 'goal': 'A 1950s look that is not shiny.',
         'settings': {'Shelf': 'Sock Hop', 'BASE COLOR': "Use finish's own color", 'Trim zone': 'Satin Chrome stripe'},
         'result': 'Matte, creamy colours with a thin chrome line.'},
        {'title': 'Tribute livery', 'goal': 'A heritage theme that keeps its look.',
         'settings': {'Shelf': 'VIVA MEXICO or RISING SUN', 'BASE COLOR': "Use finish's own color", 'Numbers': 'On a calm contrasting area'},
         'result': 'Authentic colours with a satin to gloss finish and readable numbers.'},
    ],
    combos=[{'with': 'patterns.nine_groups', 'why': 'Decades pattern groups give the same eras as shapes you can recolour.'},
            {'with': 'finishes.what_makes_a_finish_pop', 'why': 'A retro theme still needs one hero area.'}],
    faq=[
        {'q': 'Can I recolour a heritage finish?', 'a': 'Use hue and saturation. A solid colour hides the design.'},
        {'q': 'Which shelf is most matte?', 'a': 'Sock Hop, with a roughness average of 162.'},
        {'q': 'Which shelf is most glossy?', 'a': 'FORBIDDEN DRAGON and RISING SUN, mostly high gloss.'},
        {'q': 'Are decades patterns colourful?', 'a': 'No. They are about shape, and you colour them freely.'},
    ],
    mistakes=[
        {'symptom': 'The heritage colours disappeared.', 'cause': 'A solid colour was used.', 'fix': 'Return to Use finish own color.'},
        {'symptom': 'Numbers are lost in the design.', 'cause': 'The finish is busy behind them.', 'fix': 'Put numbers on a calm zone with strong contrast.'},
    ],
    protips=['WORLD OF COLOR has 100 country palettes with the lowest metal of any shelf (38), the safest choice when you want colour with no sparkle.',
             'Flat retro paint with chrome trim lines is the classic modern-retro recipe.'])

enrich(D, 'finishes.nature_tactical_cyberpunk', level='beginner',
    sources=[ATL, AIK + 'sliders_and_controls.md:12', AIK + '09_field_playbook.md:35', AIK + '02_spec_and_finishes.md:20'],
    deep=[
        {'heading': 'Shine profiles', 'body': 'TACTICAL AND FIELD (60) averages metal 43, roughness 115, coat 107, mostly semi-matte and fine detail. DARK CITY (50) averages 43, 161, 151: the most matte, with 23 matte finishes. FRACTURED WILDS (110) averages 117, 123, 116 and 96 of them read semi-matte. CYBERPUNK (60) averages 100, 89, 131, mostly satin. Signal (25) averages 81, 77, 49 and is the glow shelf. Materials and Physics (31) averages metal 187: acid rain, salt spray and weathered metal.'},
        {'heading': 'Camo that works', 'body': 'Pattern Overlay mode draws the pattern\'s own colours. Blend keeps your paint colour and only modulates light and dark, so the base colour decides the camo hue. Camo as a special brings its own colours, so use it as it comes and shift hue if needed. Worn camo: pair it with a weathered and aged finish on the lower zones.'},
        {'heading': 'Weathering logic', 'body': 'Damage logic is physical: oxidised areas lose metal, dirt and etch pits gain roughness, worn zones get a duller coat, rubbed edges stay polished. Raise roughness, add weathering spec patterns, and browse Foundation EFX, Weathered Paint and Hardware: Battle Worn.'},
    ],
    examples=[
        {'title': 'Desert patrol', 'goal': 'A matte camo with dirt on the lower body.',
         'settings': {'Roof, hood': 'A TACTICAL AND FIELD camo', 'BASE COLOR': "Use finish's own color", 'Lower zone': 'A weathered finish', 'Spec overlay': 'A dirt or wear overlay at Strength 30'},
         'result': 'Matte upper camo, grimy lower sills.'},
        {'title': 'Rain-slick city', 'goal': 'A neon city night look.',
         'settings': {'Shelf': 'CYBERPUNK', 'Accent zone': 'A Signal glow finish'},
         'result': 'Satin dark body with a single glow accent.'},
    ],
    combos=[{'with': 'patterns.paint_mode', 'why': 'Blend keeps your colour; Overlay prints the camo colours.'},
            {'with': 'spec.paint_spec_marriage', 'why': 'Matte beside a little gloss reads as two materials.'}],
    faq=[
        {'q': 'Is camo flat?', 'a': 'Mostly. TACTICAL averages roughness 115 and metal 43.'},
        {'q': 'Which shelf is the darkest and flattest?', 'a': 'DARK CITY.'},
        {'q': 'Does cyberpunk glow?', 'a': 'The Signal shelf is the glow source; Cyberpunk is a satin city palette.'},
        {'q': 'Can I add dirt?', 'a': 'Yes, with weathering spec overlays.'},
    ],
    mistakes=[
        {'symptom': 'Lightning on matte black reads as grey cracked glass.', 'cause': 'Low contrast and a rough base.', 'fix': 'Pick a different pattern or a lighter base.'},
        {'symptom': 'Camo turned busy.', 'cause': 'A strong pattern on top of camo.', 'fix': 'Remove the pattern.'},
    ],
    protips=['Blend mode lets one camo pattern take any base colour. That is how one pattern makes forest, desert and snow.',
             'Roughness up and coat duller are the fastest steps to worn.'])

enrich(D, 'finishes.picker_library_browser', level='beginner',
    sources=['paint-booth-v2.html:4779-4857', 'paint-booth-v2.html:3880-3912', 'paint-booth-v2.html:4266', AIK + 'how_do_i.md:124-144', W + ':4247-4254', 'js/spb-ai-cards.js:175'],
    deep=[
        {'heading': 'Three ways in', 'body': 'The Base Material picker is for choosing and staging: search, hashtag chips, Color Lock, Surprise me, See on paint, the On-Car Stage and USE IT. The full-screen library is for browsing: search that understands hashtags, plus a favourites star. The Finish Catalog browser is for comparing: All Types, Base plus Pattern, Monolithic, All Bases or All Patterns, sorted by Default, A to Z, Z to A, Recent or Favorites, with a Finish Comparison table you can widen with + Column.'},
        {'heading': 'Judge the car, not the swatch', 'body': 'A thumbnail shows the paint, not the shine. Chrome, candy and metal twists are nearly invisible in a flat colour preview, and the live preview is only about 768 pixels for a 2048 sheet, so fine flake averages out. Use See on paint to try a finish on your own colours, then read the spec views and check in the sim in sun, shade and night, plus a replay at distance.'},
        {'heading': 'A fast audition loop', 'body': 'Turn Color Lock on, set the colour you want, then click through finishes with USE IT and look at the On-Car Stage. Star the ones you like. Use hashtags to jump between families such as chrome, candy and pearl. This finds a winner in a few minutes instead of scrolling shelves.'},
    ],
    examples=[
        {'title': 'Find a candy red quickly', 'goal': 'Land on a good candy red in under a minute.',
         'settings': {'Search': '#candy red', 'Color Lock': 'On, with your red', 'Action': 'Click a result, then USE IT'},
         'result': 'The candy finish on your red; star it, try the next.'},
        {'title': 'Compare four finishes', 'goal': 'Choose between candidates.',
         'settings': {'Finish Catalog browser': 'All Bases', 'Finish Comparison': '+ Column for each candidate'},
         'result': 'A table of the finishes side by side.'},
    ],
    combos=[{'with': 'finishes.finish_cards', 'why': 'The cards behind the search.'},
            {'with': 'finishes.catalogue_overview', 'why': 'The shelves the picker lists.'}],
    faq=[
        {'q': 'What is See on paint?', 'a': 'A preview of the finish on your own paint.'},
        {'q': 'What does Surprise me do?', 'a': 'It picks a finish at random so you find options you would not search for.'},
        {'q': 'Why does the swatch look different from the car?', 'a': 'The swatch cannot show shine in angle. Use See on paint and the sim.'},
        {'q': 'Where are my favourites?', 'a': 'Use the star and the Favorites filter.'},
    ],
    mistakes=[
        {'symptom': 'Chrome looks like a plain grey swatch.', 'cause': 'A flat preview cannot show reflections.', 'fix': 'Check the spec views and the sim.'},
        {'symptom': 'I lose my colour every time I change finish.', 'cause': 'Color Lock is off.', 'fix': 'Turn Color Lock on.'},
    ],
    protips=['Surprise me is the quickest way to an unexpected winner.',
             'A render takes seconds to about a minute, and a standard finish is meant to render in 2 to 3 seconds at 2048.'])

enrich(D, 'finishes.finish_cards', level='intermediate',
    sources=['js/spb-ai-cards-data.js:2', 'js/spb-ai-cards.js:175', AIK + '11_finish_advisor.md:9', AIK + '11_finish_advisor.md:12-27'],
    deep=[
        {'heading': 'What a card holds', 'body': 'Each of the 4,755 cards has: a plain look description; a list of synonyms and a mood from 19 (aggressive, stealth, luxury, elegant, retro, clean, playful, wild, rugged, techy, natural, spooky, cosmic, tropical, icy, fiery, dreamy, industrial, patriotic); an era from 7 (50s-60s, 70s, 80s, 90s, modern, futuristic, timeless); a fit from 6 (dirt late model, stock car, gt / sports car, open wheel, truck / off-road, show car); a use from 11 (body, hood, roof, sides, stripes, numbers, trim, hero panel, bumpers, spoiler, under stripes); how loud and how busy it is; finishes that pair well and that to avoid; and a set of one-to-five ratings: visibility, appeal, body, accent, hero and risk.'},
        {'heading': 'Deep notes', 'body': 'Cards carry close-up and from-a-distance descriptions, a scale hint, what patterns and spec overlays work over it, what is not true of it (for example: not satin chrome, roughness is 2) and where it works best, plus one warning. Search finds finishes by meaning, not just by name.'},
        {'heading': 'Kits and the advisor', 'body': 'Kits suggest a Classic, Premium or Bold plan for the whole car from one hero finish and its pairs. The built-in advisor is free and offline: it reads the same cards. Finishes do not change how the car drives.'},
    ],
    examples=[
        {'title': 'Search by use', 'goal': 'A finish for numbers.',
         'settings': {'Search': 'numbers satin readable'},
         'result': 'Gloss, satin and matte finishes with strong contrast; the advisor avoids chrome, glitter and colour-shifting finishes on numbers.'},
        {'title': 'Plan a car from a hero', 'goal': 'Get a matching set.',
         'settings': {'Hero': 'One loud finish', 'Kit': 'Classic, Premium or Bold'},
         'result': 'A hood hero with paired finishes for the body, trim and stripes.'},
    ],
    combos=[{'with': 'finishes.picker_library_browser', 'why': 'Where the card search lives.'},
            {'with': 'finishes.what_makes_a_finish_pop', 'why': 'The rules the kits follow.'}],
    faq=[
        {'q': 'Does the advisor need an AI key?', 'a': 'No. It answers free and offline from the cards.'},
        {'q': 'What does risk mean?', 'a': 'How easily the finish goes wrong, such as on numbers or in the wrong colour.'},
        {'q': 'What is the difference between loud and busy?', 'a': 'Loud is attention-grabbing colour or shine; busy is lots of small detail.'},
        {'q': 'Does a finish change handling?', 'a': 'No.'},
    ],
    mistakes=[
        {'symptom': 'Several loud, busy finishes fight each other.', 'cause': 'Too many hero finishes.', 'fix': 'One hero, then its paired finishes.'},
        {'symptom': 'A pair did not work on my colour.', 'cause': 'Pairs ignore your colour.', 'fix': 'Preview with See on paint.'},
    ],
    protips=['Pick one hero finish, then take its paired finishes for the rest of the car.',
             'The avoid list is as valuable as the pair list.'])

enrich(D, 'finishes.what_makes_a_finish_pop', level='intermediate',
    sources=[AIK + '05_design_and_taste.md:4-12', AIK + '08_livery_design.md:7-19', AIK + '03_recipes.md:24', W + ':3492-3556', W + ':3607-3610'],
    deep=[
        {'heading': 'Contrast, not saturation', 'body': 'What pops: complementary neighbour contrast (deep blue beside warm gold, black beside hot pink, white beside red) or a clearly different value. Make the spec the colour-opposite of the paint: warm paint on matte next to a cool colour on metal reads richer than one shine everywhere. Metallic or candy blocks beside flat blocks create pop because the colour and the shine both oppose.'},
        {'heading': 'Fine texture beats big blobs', 'body': 'Texture should be a field of 8 to 32 pixel marks across the sheet, not a poster. Big low-frequency blobs read as dirt or smeared paint. A good finish stacks several different mark types (sweeps, spots, arcs, rings, flecks, hairlines, ridges, chips), and spec that follows the paint structure (hot edges, ridges, cracks, brush direction) beats random noise. A big centred motif reads as a decal on the car.'},
        {'heading': 'The make-it-pop recipe', 'body': 'Deep glossy candy or pearl of its own colour on the biggest flat area, matte or satin or chrome accent on the contrast pair, and a subtle flake spec pattern at opacity 30 to 50. Composition about 60 percent dominant, 30 accent, 10 trim. Two or three colours plus one accent; five looks cheap. Premium sample palettes: near-black matte with gold gloss and white numbers; blue with gold and white; stealth dark grey with satin accents and light grey numbers.'},
    ],
    examples=[
        {'title': 'Candy hero', 'goal': 'One loud area that pops.',
         'settings': {'Hood and roof': 'Candy in the livery colour', 'Sides': 'Matte in the contrast colour', 'Stripe': 'Satin Chrome', 'Spec overlay': 'Fine flake, Strength 40'},
         'result': 'Glossy candy against flat sides, with a bright chrome edge and subtle sparkle.'},
        {'title': 'Numbers that read', 'goal': 'Keep numbers legible.',
         'settings': {'Number zone': 'Gloss or satin with strong colour contrast', 'Avoid': 'Sparkle, strong patterns, colour shift'},
         'result': 'Digits stay readable at speed and at replay distance.'},
    ],
    combos=[{'with': 'spec.paint_spec_marriage', 'why': 'The technical side of the same idea.'},
            {'with': 'finishes.finish_cards', 'why': 'Pair and avoid lists make the pairing choices.'},
            {'with': 'patterns.choosing_at_car_scale', 'why': 'Fine texture, not blobs.'}],
    faq=[
        {'q': 'Is more colour better?', 'a': 'No. Two or three colours plus one accent.'},
        {'q': 'Is chrome good on a whole car?', 'a': 'It is loud and shows every flaw. It suits accents.'},
        {'q': 'How do I make black pop?', 'a': 'Add a flake spec pattern or a candy accent; black beside hot pink or white contrasts strongly.'},
        {'q': 'Does it look the same in the sim?', 'a': 'Judge on a track in sun, shade and night, and at replay distance.'},
    ],
    mistakes=[
        {'symptom': 'Looks cool in the thumbnail, muddy on the car.', 'cause': 'Mid-tone mud at thumbnail size stays mud.', 'fix': 'Add value contrast or shine contrast between neighbours.'},
        {'symptom': 'Everything glossy and flat.', 'cause': 'One material everywhere.', 'fix': 'Give neighbours the opposite shine.'},
    ],
    protips=['A chrome pinstripe on a matte car reads as real chrome.',
             'If a finish does not show up, add more small events and more channel contrast; do not make the marks bigger.'])

enrich(D, 'finishes.base_colour_tuning', level='beginner',
    sources=[COMP + ':1799-1850', COMP + ':4966-4979', COMP + ':5055-5057', COMP + ':5188-5193', ZONES + ':2074-2098', AIK + 'sliders_and_controls.md:6', AIK + 'sliders_and_controls.md:9'],
    deep=[
        {'heading': 'The formulas', 'body': 'Hue shift rotates every hue by the chosen degrees, from minus 180 to plus 180. Saturation becomes saturation times (1 plus the slider over 100). Brightness becomes value times (1 plus the slider over 100). Both are clipped to the legal range. If all three sliders are under half a unit, the step is skipped. The tuning only applies inside the zone mask. Measured: on a green finish, plus 180 gave magenta, minus 150 hot pink and plus 150 purple. Greys have no hue and need a colour mode.'},
        {'heading': 'BASE STRENGTH mixes paint only', 'body': 'BASE STRENGTH mixes the finished base look over your original paint: output = original times (1 minus a) plus result times a, where a is the zone mask times the strength. At 0 you see your original paint; at 100 percent the full base. It never changes the shine, which is the job of SPEC STRENGTH. Patterns are added after the strength mix, so lowering BASE STRENGTH does not dim them.'},
        {'heading': 'Which control for which complaint', 'body': 'More subtle: BASE STRENGTH or intensity. Less shiny: SPEC STRENGTH. Smaller pattern: scale, not strength. Too dark: brightness plus 30 to plus 40. Leaning violet: hue minus 15. Grey with a tint: saturation minus 10. Each slider has a reset arrow.'},
    ],
    examples=[
        {'title': 'Tame a loud finish', 'goal': 'Keep part of your original paint.',
         'settings': {'BASE STRENGTH': '60%'},
         'result': '60 percent of the finish over 40 percent of your own colours.'},
        {'title': 'Fix a navy tint', 'goal': 'Get an own-colour finish to look like the swatch.',
         'settings': {'BRIGHTNESS': '+35', 'HUE SHIFT': '-15'},
         'result': 'Lighter, less purple version without losing the design.'},
    ],
    combos=[{'with': 'finishes.colour_source_modes', 'why': 'The mode decides what the sliders act on.'},
            {'with': 'spec.strength_and_independent', 'why': 'The shine counterpart of Base Strength.'}],
    faq=[
        {'q': 'Does BASE STRENGTH change shine?', 'a': 'No. Only colour.'},
        {'q': 'Why did hue shift not work on grey?', 'a': 'Greys have no hue.'},
        {'q': 'Does hue shift change my numbers?', 'a': 'Only inside the zone, and numbers are protected when they sit on their own layer.'},
        {'q': 'What is the range of brightness?', 'a': 'Minus 100 to plus 200.'},
    ],
    mistakes=[
        {'symptom': 'Lowering BASE STRENGTH dulled the colours.', 'cause': 'It lets your original paint show through.', 'fix': 'Use hue, saturation and brightness for colour changes.'},
        {'symptom': 'Pattern did not fade with Base Strength.', 'cause': 'Patterns come after the mix.', 'fix': 'Lower the pattern opacity.'},
    ],
    protips=['Hue shift is relative to the current hue, so work in small steps.',
             'Right control for the job: more subtle means base strength, less shiny means spec strength, smaller pattern means scale.'])

enrich(D, 'finishes.gradients_flip_depth_underglow', level='intermediate',
    sources=[COMP + ':2158-2216', COMP + ':2486-2500', ZONES + ':1968-2037', 'feedback:'.replace('feedback:', 'js/spb-pro-edit.js:103')],
    deep=[
        {'heading': 'COLOR DEPTH is real candy maths', 'body': 'Depth treats the colour as a translucent coat over the zone\'s own light and dark structure, so metallic grain survives inside the colour. The more depth, the more coats: the colour is raised to a power of about 0.30 plus 2.1 times the depth, which deepens and darkens it, especially toward the edges. The effect fades in over the first third of the slider (it reaches full at 33 percent). At 0, no colour is laid.'},
        {'heading': 'COLOR FLIP and UNDERGLOW', 'body': 'COLOR FLIP rotates the hue of the dark population of the paint (only the dark parts) by the angle, like a chameleon two-tone: 90 degrees gives a neighbouring hue, 180 the opposite. UNDERGLOW lets a ground coat show through: warm colours get a gold under-glow, cool colours a silver one, strongest in highlights. All three are driven by the paint\'s own value structure, so they never fade a zone toward flat grey.'},
        {'heading': 'When they are available', 'body': 'These stay locked until BASE COLOR is solid, gradient or from special. Plain solid colours render exactly as picked until you touch these sliders; touching COLOR DEPTH darkens an exact colour, so leave it at 0 when you need an exact brand colour. COLOR SCALE and ROTATION zoom and turn the colour art of a gradient or borrowed colour source.'},
    ],
    examples=[
        {'title': 'Candy apple red', 'goal': 'A deep red from a plain red.',
         'settings': {'Base Material': 'Metallic', 'BASE COLOR': 'Use solid color, red', 'COLOR DEPTH': '65', 'UNDERGLOW': '30'},
         'result': 'Metallic grain stays visible inside a deep red with a warm gold bloom in the highlights.'},
        {'title': 'Two-tone chameleon', 'goal': 'A second hue in the shadows.',
         'settings': {'BASE COLOR': 'Use solid color, dark teal', 'COLOR FLIP': '120'},
         'result': 'The dark areas shift toward a different hue while the highlights stay teal.'},
    ],
    combos=[{'with': 'finishes.colour_source_modes', 'why': 'The mode that unlocks these.'},
            {'with': 'finishes.colorshoxx_and_shift', 'why': 'Ready-made flips on the Prizm and Spectrum Shift shelves.'}],
    faq=[
        {'q': 'Why are the sliders greyed out?', 'a': 'BASE COLOR must be solid, gradient or from special.'},
        {'q': 'Why did my brand colour get darker?', 'a': 'COLOR DEPTH was above 0.'},
        {'q': 'What is the default depth?', 'a': '0 in the app, which means no change.'},
        {'q': 'Does flip change the highlights?', 'a': 'No. It rotates only the dark part.'},
    ],
    mistakes=[
        {'symptom': 'Exact colour is wrong by a shade.', 'cause': 'Depth or underglow in use.', 'fix': 'Set them to 0.'},
        {'symptom': 'Underglow looks gold on a blue car.', 'cause': 'The colour reads warm on average.', 'fix': 'Adjust the colour or lower underglow.'},
    ],
    protips=['Plain solid colours render exactly as picked until you touch these sliders.',
             'Gradient stops run 2 to 10 and the direction can be horizontal, vertical, diagonal, radial or angular.'])

enrich(D, 'finishes.base_scale_rotation', level='beginner',
    sources=[ZONES + ':1971-1981', ZONES + ':2047-2057', AIK + 'how_do_i.md:169-181', AIK + 'sliders_and_controls.md:12', W + ':3515-3533'],
    deep=[
        {'heading': 'Why 1.00 is usually too big', 'body': 'The canvas is 2048 by 2048 over a whole car. Features of 8 to 32 pixels read as texture, fine is 4 to 8, micro is 1 to 2. A pattern that looks medium in a square preview can be the size of a mirror or a door on the car. Base scale runs from 0.05 to 5.0 times with 1.00 as the finish default; smaller means more repeats and finer detail, and 0.3 to 0.6 is typical for premium detail.'},
        {'heading': 'What base scale scales', 'body': 'It scales the finish\'s own texture (flake, weave, grain, peel), not its colours and not the car. The spec follows base scale until you tick INDEPENDENT SPEC. Rotation goes 0 to 355 degrees in 5 degree steps.'},
        {'heading': 'Fine structural finishes', 'body': 'Fine structural colour finishes are authored at 8 to 32 pixels already. Scaling them up weakens the effect, so leave them at default or finer.'},
    ],
    examples=[
        {'title': 'Crushed to 50 percent', 'goal': 'Twice as fine carbon.',
         'settings': {'BASE SCALE': '0.50x'},
         'result': 'Twice as many weave cells across the same hood.'},
        {'title': 'Diagonal grain', 'goal': 'Turn the grain.',
         'settings': {'BASE ROTATION': '45'},
         'result': 'The finish texture runs on the diagonal.'},
    ],
    combos=[{'with': 'spec.scale_rotation', 'why': 'Spec scale is separate when Independent Spec is on.'},
            {'with': 'patterns.scale_rotation_opacity', 'why': 'Pattern scale is a different control.'}],
    faq=[
        {'q': 'What does crushed to 50 percent mean?', 'a': 'Scale 0.50, twice as fine.'},
        {'q': 'Does scale change colour?', 'a': 'No.'},
        {'q': 'Does it resize the car?', 'a': 'No.'},
        {'q': 'What is typical?', 'a': '0.3 to 0.6.'},
    ],
    mistakes=[
        {'symptom': 'The flake looks like big smears.', 'cause': 'Scale 1.00 on a whole-car canvas.', 'fix': 'Go to 0.3 to 0.6.'},
        {'symptom': 'Fine detail vanished.', 'cause': 'The preview is small.', 'fix': 'Judge on the spec views and in the sim.'},
    ],
    protips=['When detail seems enough, push it another 25 to 40 percent finer.',
             'Right control for smaller pattern is scale, not strength.'])

enrich(D, 'finishes.second_base_overlays', level='intermediate',
    sources=['engine/overlay.py:41-44', 'engine/overlay.py:133-157', 'engine/overlay.py:211-232', COMP + ':5426', ZONES + ':2440', ZONES + ':9425', AIK + '02_spec_and_finishes.md:11'],
    deep=[
        {'heading': 'How an overlay mixes', 'body': 'An overlay base is blended over the result by a per-pixel alpha: paint times (1 minus alpha) plus overlay times alpha. Alpha is linear in strength, and a strength of 0 gives you the primary only. The mix mode decides where the alpha is high: Fractal Dust and marble-like scatter, Tint as a gentle colour wash, and the pattern-driven modes that follow the primary pattern: Pattern Edges, Pattern Peaks, Pattern Glow, Pattern Fresnel, Pattern Flow and Pattern Shatter, plus Pattern-Reactive and Pattern-Pop. An unknown mode falls back to dust.'},
        {'heading': 'Spec and paint both mix', 'body': 'The overlay blends both the paint and a second spec through its own strength, spec strength, blend mode and noise scale, and each overlay has its own hue, saturation and brightness. Overlay scale (0.01 to 5) only affects the fractal and dust modes. They run after patterns, in order second, third, fourth, fifth.'},
        {'heading': 'Typical recipe', 'body': 'A gloss body with a pearl overlay at about 40 percent. Start with Tint (subtle) at a low strength, then try a pattern-driven mode if the zone already has a pattern. Every overlay adds render time and visual noise, so use two or three at most.'},
    ],
    examples=[
        {'title': 'Pearl on gloss', 'goal': 'Depth without losing the base.',
         'settings': {'Base Material': 'Gloss', 'Second base': 'Pearl', 'Blend mode': 'Tint (subtle)', 'Strength': '40'},
         'result': 'A soft pearl shimmer on the gloss body.'},
        {'title': 'Edge glow', 'goal': 'Make the pattern edges light up.',
         'settings': {'Pattern 1': 'A geometric pattern', 'Second base': 'A metallic', 'Blend mode': 'Pattern Edges'},
         'result': 'The overlay shows along the pattern edges.'},
    ],
    combos=[{'with': 'spec.how_layers_combine', 'why': 'Overlays are the last step of the paint stack.'},
            {'with': 'patterns.layers_and_stacking', 'why': 'Pattern-driven modes need a pattern.'}],
    faq=[
        {'q': 'How many bases can a zone have?', 'a': 'Up to five in all: one base plus four overlays.'},
        {'q': 'Why does my pattern-driven mode do nothing?', 'a': 'It needs a pattern in the zone to react to.'},
        {'q': 'Does overlay scale matter?', 'a': 'Only in the fractal and dust modes.'},
        {'q': 'Which mode to start with?', 'a': 'Tint (subtle) at a low strength.'},
    ],
    mistakes=[
        {'symptom': 'The overlay washed out the base.', 'cause': 'Strength too high.', 'fix': 'Lower strength to 30 to 40.'},
        {'symptom': 'Render got slow.', 'cause': 'Every overlay adds work.', 'fix': 'Remove unused overlays.'},
    ],
    protips=['Old saved looks that used removed modes are mapped to a kept mode, so they still render.',
             'Overlay alpha is linear in strength, which makes it predictable: half strength is half the overlay.'])

# 2026-10-05: Season mode is RETIRED and the Pro window has no Wear slider. Corrected depth text lives in enc_wear_fix.py (same source as enc_B_part6.py).
from enc_wear_fix import WEAR_V3
_w = dict(WEAR_V3)
enrich(D, 'finishes.wear', sources=_w.pop('_sources'), **_w)

print('finishes B done')
