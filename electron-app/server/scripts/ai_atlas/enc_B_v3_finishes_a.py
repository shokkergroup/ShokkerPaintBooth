"""V3 depth for the finishes articles, part A (kinds, colour modes, Foundation, intent, overview, EFX, ASTRA, ghost, shift, fractured, plates).
Shelf averages are computed from the catalogue data (every base and special on the shelf); exact specs from the registry and the wiki spec guide.
Run: python scripts/ai_atlas/enc_B_v3_finishes_a.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'finishes'
ENG = 'shokker_engine_v2.py'
COMP = 'engine/compose.py'
BASE = 'engine/base_registry_data.py'
ATL = 'js/spb-ai-atlas-data.js:2'
ZONES = 'paint-booth-2-state-zones.js'
SI = 'engine/paint_v2/surface_intent.py'
W = 'SPB_WIKI.html'
AIK = 'docs/ai_knowledge/'

enrich(D, 'finishes.four_kinds', level='beginner',
    sources=[ATL, COMP + ':5135-5170', ENG + ':19010-19480', ENG + ':19506-20109', AIK + '08_livery_design.md:22', AIK + '09_field_playbook.md:28'],
    deep=[
        {'heading': 'What the engine does differently for each kind', 'body': 'A base is built from a plain material recipe: it draws a spec (and paint) over the zone, then takes the colour you set. A one-piece special, called a monolithic, is rendered by its own paint and spec routines and brings both together; given a solid colour it keeps that colour flat and contributes mainly its spec texture. A pattern is a shape laid on top of the base, and a spec pattern is a texture that only touches the shine, up to five stacked in a zone. The catalogue holds 1,144 bases, 2,993 specials, 317 patterns and 301 spec patterns.'},
        {'heading': 'Why Foundation behaves differently', 'body': 'Foundation bases have no paint routine at all, only a flat spec. When BASE COLOR is Use source paint (spec only) the base paint is skipped entirely and your original colours are untouched. That is measured: using a Foundation chrome with source paint changed 0 percent of the paint, while the plain Chrome base repainted 78 to 85 percent of a hood.'},
        {'heading': 'Picking the control that matters', 'body': 'For a base: BASE COLOR, hue, saturation and brightness matter. For a special: leave the colours alone and use scale, strength and the colour tuning sliders. For a pattern: scale, rotation, opacity and Paint mode. For a spec pattern: strength and the M, R and C ticks. Using the wrong control is the most common reason a change seems to do nothing.'},
    ],
    examples=[
        {'title': 'Shine only', 'goal': 'Make a livery chrome without changing its colours.',
         'settings': {'Base Material': 'Chrome from the Foundation shelf', 'BASE COLOR': 'Use source paint (spec only)'},
         'result': 'Your design is unchanged. The whole zone reflects like a mirror, tinted by your paint.'},
        {'title': 'Special as it comes', 'goal': 'Use a carbon or camo special properly.',
         'settings': {'Base Material': 'A special', 'BASE COLOR': "Use finish's own color", 'BASE SCALE': 'Below 1.00 for finer detail'},
         'result': 'The special shows its own colours and spec together at a car-scale detail.'},
    ],
    combos=[{'with': 'finishes.colour_source_modes', 'why': 'The BASE COLOR modes decide which kind behaviour you get.'},
            {'with': 'finishes.foundation_shine_only', 'why': 'The spec-only kind in detail.'},
            {'with': 'patterns.what_is_a_pattern', 'why': 'The pattern kind in detail.'}],
    faq=[
        {'q': 'Why did my livery get repainted?', 'a': 'You picked a base or special that brings its own colour handling. Use a Foundation material with Use source paint to keep your colours.'},
        {'q': 'What is a monolithic?', 'a': 'A one-piece special finish that brings its own paint and its own shine together.'},
        {'q': 'How many finishes are there?', 'a': '4,137 bases and specials, plus 317 patterns and 301 spec patterns.'},
        {'q': 'Can I mix kinds in one zone?', 'a': 'Yes. A base, up to five pattern layers, up to four more base overlays and up to five spec overlays can share a zone.'},
    ],
    mistakes=[
        {'symptom': 'A solid colour wiped out a special\'s design.', 'cause': 'Specials draw their design with their own colours, and a solid colour overrides them.', 'fix': 'Leave BASE COLOR on the finish own colour, or use a take-your-colour base plus a pattern.'},
        {'symptom': 'Shine-only change repainted my livery.', 'cause': 'A non-Foundation base was used.', 'fix': 'Pick the Foundation version and set Use source paint.'},
    ],
    protips=['A monolithic given a solid colour keeps that colour flat and contributes only its spec texture, so a snake or camo special in hot pink becomes flat pink with its texture in the shine only.',
             'Hue shift is relative, so it works on own-colour finishes where a solid colour would flatten them: on green, plus 180 gives magenta.'])

enrich(D, 'finishes.colour_source_modes', level='beginner',
    sources=[COMP + ':2218-2500', COMP + ':5135-5170', ZONES + ':1910-1911', ZONES + ':7925-7940', AIK + 'sliders_and_controls.md:6', AIK + 'sliders_and_controls.md:24', AIK + '09_field_playbook.md:19', AIK + '09_field_playbook.md:22', AIK + '09_field_playbook.md:25'],
    deep=[
        {'heading': 'What each mode does to the paint', 'body': 'Use finish\'s own color leaves the finish colours as made. Use source paint (spec only) skips the base paint completely, so the base contributes spec only. Use solid color replaces the zone colour with one exact colour and renders it as you picked it. From special borrows the colours of a special. Custom gradient fades between 2 to 10 stops, with a direction of horizontal, vertical, diagonal down, diagonal up, radial or angular. Each of these has its own strength (0 to 100) and placement scale, offset, rotation and flip.'},
        {'heading': 'Gradients are drawn on the flat sheet', 'body': 'The sheet is the car cut open, so a gradient runs across the whole 2048 square, not along each part. A fade will not line up across panels. Use one zone per panel when it matters, or use a flake or sparkle material when you only want a little colour in the black.'},
        {'heading': 'Tuning own-colour finishes', 'body': 'A solid colour on a camo or snake paints it one flat colour and loses the pattern. Shift hue and saturation instead. Examples measured on real finishes: too dark or navy, brightness plus 30 to plus 40; leaning violet, hue minus 15; grey looks tinted, saturation minus 10. Greys have no hue to shift and need a colour mode.'},
    ],
    examples=[
        {'title': 'Exact brand colour', 'goal': 'A precise colour on the whole body.',
         'settings': {'Base Material': 'Gloss, Satin, Matte, Metallic, Pearl or Candy', 'BASE COLOR': 'Use solid color', 'Colour': 'Your exact hex'},
         'result': 'The zone renders the colour you picked. Avoid COLOR DEPTH, which darkens an exact colour.'},
        {'title': 'Fade across the hood', 'goal': 'A two-colour fade with a direction.',
         'settings': {'BASE COLOR': 'Custom gradient', 'Stops': '2', 'Direction': 'Diagonal down', 'Zone': 'Hood only'},
         'result': 'A smooth diagonal blend across the hood panel, not the whole car.'},
    ],
    combos=[{'with': 'finishes.gradients_flip_depth_underglow', 'why': 'Depth, flip and underglow only unlock in solid, gradient or from special modes.'},
            {'with': 'finishes.base_colour_tuning', 'why': 'Hue, saturation and brightness work on any mode.'},
            {'with': 'finishes.foundation_shine_only', 'why': 'Source paint is how Foundation keeps your colours.'}],
    faq=[
        {'q': 'Which mode keeps my livery?', 'a': 'Use source paint (spec only), with a Foundation finish.'},
        {'q': 'Why did my solid colour render slightly different?', 'a': 'A plain solid colour should render exactly. If it looks darker, COLOR DEPTH or a brightness slider is on.'},
        {'q': 'How many gradient stops?', 'a': 'From 2 to 10.'},
        {'q': 'What does Lock Base Color do?', 'a': 'It keeps your colour while you swap finishes, so you can audition many finishes on one colour.'},
    ],
    mistakes=[
        {'symptom': 'Source paint mode did nothing.', 'cause': 'The zone does not sit over paint you already have.', 'fix': 'Load your paint first or use a solid colour.'},
        {'symptom': 'Gradient breaks at a panel joint.', 'cause': 'The gradient lays over the full sheet.', 'fix': 'Use one zone per panel.'},
        {'symptom': 'Paint patterns cannot take a custom colour; metal flake draws silver.', 'cause': 'Patterns carry their own colours.', 'fix': 'Use a flake special or a flake spec pattern for coloured sparkle.'},
    ],
    protips=['Black with blue sparkle: Deep Space flake special, brightness minus 45, hue minus 20, saturation plus 60 gives about 55 percent pure black with blue flecks.',
             'For a little colour in the black, use a flake or sparkle material instead of a gradient.'])

enrich(D, 'finishes.foundation_shine_only', level='beginner',
    sources=[BASE + ':421-461', ZONES + ':14519-14531', 'js/spb-pro-edit.js:103-130', AIK + '08_livery_design.md:22', W + ':3940-3987', ATL],
    deep=[
        {'heading': 'The exact Foundation values', 'body': 'Metal, roughness, coat from the registry: Gel Coat (wet look) 0, 15, 16. Gloss 0, 30, 16. Semi Gloss 0, 55, 40. Satin 0, 95, 70. Eggshell 0, 140, 100. Matte 0, 200, 160. Primer 0, 215, 200. Flat Black 0, 250, 255. Satin Pearl 100, 90, 60. Pearl 100, 40, 16. Metallic 200, 50, 16. Matte Metallic 225, 140, 100. Candy 200, 15, 16. Brushed 180, 75, 65. Frozen 160, 85, 130. Bead Blast 180, 160, 140. Chrome 255, 2, 16. Dark Chrome 250, 15, 40. Satin Chrome 250, 45, 40.'},
        {'heading': 'Everyday words that map to a Foundation finish', 'body': 'Wet look, ceramic coating and glassy map to Gel Coat. Plasti dip, stealth, primer and cerakote map to Matte (plasti dip and stealth push rougher). Powder coat, wrinkle coat, vinyl wrap, baked enamel, anodized, frosted, bead blasted, hammered, patina, galvanized and dark chrome each have a Foundation entry. These are the finishes the built-in edit helper picks when you ask for a look in plain words.'},
        {'heading': 'Pure by design', 'body': 'Foundation spec is flat inside each finish: no grain, flake or peel. That keeps it predictable and keeps your paint. Texture belongs in spec overlays, which you add on top (brushed grain over Brushed, a weave over Gloss Carbon). The Foundation EFX shelf is the separate shelf that carries texture of its own.'},
    ],
    examples=[
        {'title': 'Satin black stealth', 'goal': 'Dull a gloss livery without recolouring.',
         'settings': {'Base Material': 'Satin', 'BASE COLOR': 'Use source paint (spec only)', 'Spec values': 'metal 0, roughness 95, coat 70'},
         'result': 'Your colours with a soft satin sheen.'},
        {'title': 'Pearl glow', 'goal': 'A shimmer that keeps the paint colour.',
         'settings': {'Base Material': 'Pearl', 'BASE COLOR': 'Use source paint (spec only)', 'Spec values': 'metal 100, roughness 40, coat 16'},
         'result': 'A soft pearl shift over your own colours.'},
    ],
    combos=[{'with': 'spec.metal_rough_grid', 'why': 'Foundation is the grid, one useful point per finish.'},
            {'with': 'spec.overlays_stack', 'why': 'Add grain or weave on top of a Foundation base.'},
            {'with': 'finishes.foundation_and_efx', 'why': 'The textured sibling shelf.'}],
    faq=[
        {'q': 'How many Foundation finishes are there?', 'a': 'The Foundation shelf holds 25.'},
        {'q': 'Why does plain Chrome repaint my car?', 'a': 'The plain Chrome base brings its own colour handling. The Foundation Chrome only touches the shine.'},
        {'q': 'Which Foundation for numbers?', 'a': 'Gloss, satin or matte for the numbers with a strong colour contrast.'},
        {'q': 'Does Foundation look flat?', 'a': 'It is flat on purpose. Add a spec overlay for texture.'},
    ],
    mistakes=[
        {'symptom': 'Chrome came out dark.', 'cause': 'Dark paint under metal.', 'fix': 'Paint near-white, or use Satin Chrome (metal 250, roughness 45) which keeps more colour.'},
        {'symptom': 'Gloss black went metallic.', 'cause': 'Metal was added.', 'fix': 'Gel Coat or Gloss keep metal at 0.'},
    ],
    protips=['Foundation bases are the cheapest way to try a shine on a finished livery. Try five in a row with Lock Base Color on.',
             'Partial-metal finishes (Metallic, Pearl, Satin Chrome) keep your colour better than full Chrome.'])

enrich(D, 'finishes.surface_intent', level='intermediate',
    sources=[SI + ':98-160', SI + ':183-197', 'scripts/spb_workbook_compute_m7.py:56-60', BASE + ':421-461'],
    deep=[
        {'heading': 'What the groups actually are', 'body': 'Spec-driven: Foundation, Clearcoat and Ghost Geometry. Fine structural colour: Fractured Cryptid, Morpho, Bloom and Petri, Neon and ASTRA. Pattern-design: carbon, geometric, guilloche, panel quilting, optical, op-art, mathematical and fractal, decades, ornamental, artistic and cultural. Pattern-image: Cultural, with one single exception for a Celtic spiral. Everything else, including Foundation EFX, is a full finish. The grouping is a lookup by shelf name.'},
        {'heading': 'It describes the catalogue, it does not change the render', 'body': 'The render path is the same for every finish. The group is used by the catalogue checks and the thumbnail baking: spec-driven finishes are judged mostly on their spec (and their thumbnail shows the spec channel), pattern-design finishes are judged on shape, and fine structural colour finishes on their micro detail. What makes a Foundation finish spec-only in practice is its data: it has no paint routine and a flat spec, so with Use source paint it cannot touch your colours.'},
        {'heading': 'How to use the group when choosing', 'body': 'Spec-driven: pick for shine and set colour separately. Pattern-design: pick for the shape and recolour freely. Fine structural colour: pick for the effect, leave scale alone and judge it on the car, because scaling it up weakens the colour that shows through the shine. Full: use as it comes and adjust.'},
    ],
    examples=[
        {'title': 'Pick by group for a three-zone car', 'goal': 'Choose one finish per job.',
         'settings': {'Body': 'Spec-driven (Gloss or Pearl, source paint)', 'Hood': 'Fine structural colour (an ASTRA finish)', 'Stripe': 'Pattern-design (a carbon pattern in Blend)'},
         'result': 'Your livery colours stay, the hood gets a hero effect and the stripe gets a shape you can recolour.'},
        {'title': 'Why recolouring did nothing', 'goal': 'Diagnose a no-change.',
         'settings': {'Finish': 'A pattern-image or fine structural colour finish', 'BASE COLOR': 'Use solid color'},
         'result': 'These finishes carry their colour in the design. Use hue, saturation or brightness instead of a solid colour.'},
    ],
    combos=[{'with': 'finishes.foundation_shine_only', 'why': 'The best example of spec-driven.'},
            {'with': 'finishes.astra', 'why': 'The best example of fine structural colour.'},
            {'with': 'patterns.nine_groups', 'why': 'The pattern-design groups.'}],
    faq=[
        {'q': 'Does the group change how a finish renders?', 'a': 'No. It describes where the finish character lives and how the catalogue is judged.'},
        {'q': 'Why is Foundation EFX a full finish?', 'a': 'It carries its own paint and shine, unlike the plain Foundation shelf.'},
        {'q': 'Where does Ghost Geometry sit?', 'a': 'Spec-driven, because the pattern is hidden in the clear coat.'},
        {'q': 'What is pattern-image?', 'a': 'Patterns that carry real colour from an image, the Cultural family.'},
    ],
    mistakes=[
        {'symptom': 'I scaled an ASTRA finish up and it lost its look.', 'cause': 'Fine structural colour depends on 8 to 32 pixel detail.', 'fix': 'Leave scale at default or go finer.'},
        {'symptom': 'I expected a spec-driven finish to recolour my car.', 'cause': 'Spec-driven finishes change shine, not paint.', 'fix': 'Set the colour separately.'},
    ],
    protips=['A finish name should match its behaviour: a base called chrome acts like chrome, and satin, ceramic, pearl, weathered, candy, carbon and matte should not secretly be gloss or chrome.',
             'The shelf name tells you the group. If you are unsure, preview with See on paint.'])

enrich(D, 'finishes.catalogue_overview', level='beginner',
    sources=[ATL, 'paint-booth-0-finish-metadata.js:19327-19447', AIK + '05_design_and_taste.md:1', AIK + '11_finish_advisor.md:9'],
    deep=[
        {'heading': 'The real numbers', 'body': 'There are 1,144 bases and 2,993 specials, which is 4,137 finishes, on 59 shelves. Patterns number 317 and spec patterns 301, so the full catalogue is 4,755. Two big groups collect the rest: More Bases with 449 and More Specials with 1,158. They are not shelves in the picker: most of them are not listed there at all, and you reach them by asking the Shokker AI helper for them by name. Shelf sizes include ASTRA 50, FLAW LAB 25, SHOKK WORKS 89, Foundation 25, Foundation EFX 46, Iridescent Insects 50, PRISM FORGE 50, Wilds 110 and Fractured Forge 88.'},
        {'heading': 'What to expect from a shelf', 'body': 'Averages over each shelf: ASTRA metal 113, roughness 114, coat 136, all bring their own colours. SHOKK WORKS metal 90, roughness 114, coat 127. X LAB metal 138, roughness 69. TACTICAL AND FIELD metal 43, roughness 115. DARK CITY metal 43, roughness 161: mostly matte. Fractured Minds averages metal 241 and coat 252: the night-carrier state. The shelf is the quickest hint of the shine you will get.'},
        {'heading': 'Finding things', 'body': 'Every finish has a card with a plain description, ratings and best uses. The advisor searches about 4,800 cards by meaning, free and without an internet key. Search for a feeling such as icy or rusty. Shelf, category, tag chips and the favourites star all narrow the list.'},
    ],
    examples=[
        {'title': 'Find a matte military look', 'goal': 'Quickly land on a matte camo.',
         'settings': {'Search': 'tactical matte', 'Shelf': 'TACTICAL AND FIELD'},
         'result': 'Mostly semi-matte camo with low metal (shelf average 43) that keeps its own colours.'},
        {'title': 'Browse by feeling', 'goal': 'Find a finish without knowing the name.',
         'settings': {'Search': 'icy', 'Tags': '#ice or #glass'},
         'result': 'Finish cards whose description or mood matches icy, ranked by meaning.'},
    ],
    combos=[{'with': 'finishes.picker_library_browser', 'why': 'The tools to browse the shelves.'},
            {'with': 'finishes.finish_cards', 'why': 'What is on each card.'}],
    faq=[
        {'q': 'How many finishes are there?', 'a': '4,137 bases and specials; 4,755 including patterns and spec patterns.'},
        {'q': 'What is More Specials?', 'a': 'A big group of 1,158 specials that do not belong to a themed shelf. Most of them are not listed in the picker; ask the Shokker AI helper for one by name.'},
        {'q': 'Do I need an AI key to search?', 'a': 'No. The built-in advisor works free and offline.'},
        {'q': 'Where are patterns?', 'a': 'In their own picker, not the Base Material list.'},
    ],
    mistakes=[
        {'symptom': 'I cannot find a pattern in the base list.', 'cause': 'Patterns are a separate list.', 'fix': 'Use the PATTERN section of the zone.'},
        {'symptom': 'The count in a report differs.', 'cause': 'Some counts include patterns and spec patterns.', 'fix': 'Remember 4,137 finishes versus 4,755 total.'},
    ],
    protips=['The shelf average tells you the shine before you open a card.',
             'Surprise me in the picker is the fastest way to find an unexpected winner.'])

enrich(D, 'finishes.foundation_and_efx', level='beginner',
    sources=[ATL, SI + ':98-110', BASE + ':421-461', ZONES + ':14519'],
    deep=[
        {'heading': 'Foundation versus Foundation EFX', 'body': 'Foundation (25 finishes) is flat spec, no paint, keeps your colours. Foundation EFX (46 finishes) carries a surface story of its own: orange peel, wire-brushed metal, damascus steel, gold leaf, snow crust, chalked paint, cast iron. Only 11 percent of EFX bring their own colours, so most still take yours. EFX averages metal 107, roughness 82, coat 82 with a large spread (metal varies by about 66), and 18 of its 46 are micro-detail.'},
        {'heading': 'When EFX is the right choice', 'body': 'Use EFX when you want the surface to read from afar without building it. Use Foundation plus a spec overlay when you want control over the texture and its strength. Do not stack a heavy pattern on an EFX finish; it already has texture and the two fight.'},
    ],
    examples=[
        {'title': 'Textured steel', 'goal': 'Brushed metal with real character.',
         'settings': {'Base Material': 'A wire-brushed metal from Foundation EFX', 'BASE COLOR': 'Pick your colour', 'BASE SCALE': '0.80x'},
         'result': 'A coloured metal with visible grain.'},
        {'title': 'Controlled texture', 'goal': 'Brushed grain you can tune.',
         'settings': {'Base Material': 'Brushed (Foundation)', 'Spec overlay': 'Brushed pattern, Strength 40', 'BASE COLOR': 'Use source paint'},
         'result': 'The same idea but every part is adjustable.'},
    ],
    combos=[{'with': 'finishes.foundation_shine_only', 'why': 'The flat sibling.'},
            {'with': 'spec.overlays_stack', 'why': 'The way to texture a Foundation base.'}],
    faq=[
        {'q': 'Does EFX keep my colours?', 'a': 'Mostly it takes the colour you give it; about 11 percent bring their own.'},
        {'q': 'Why is EFX a full finish?', 'a': 'It carries its own paint and shine, not only spec.'},
        {'q': 'Foundation or EFX for stealth?', 'a': 'Soft Matte from Foundation, which is flat and quiet.'},
        {'q': 'How many EFX are there?', 'a': '46.'},
    ],
    mistakes=[
        {'symptom': 'It looks too busy.', 'cause': 'An EFX finish plus a pattern.', 'fix': 'Remove the pattern or use plain Foundation.'},
        {'symptom': 'EFX changed my livery colours.', 'cause': 'EFX carries paint of its own.', 'fix': 'Use Foundation with source paint when you need to keep colours.'},
    ],
    protips=['Start with Foundation and add a spec overlay for texture. Use EFX when you want the whole surface story ready made.',
             'EFX detail is mostly micro and fine, so do not scale it up.'])

enrich(D, 'finishes.astra', level='intermediate',
    sources=[ATL, SI + ':108-118', W + ':3492-3503', 'docs/COLORSHOXX_ANGLE_REVEAL.md:1'],
    deep=[
        {'heading': 'What ASTRA is made of', 'body': 'All 50 ASTRA finishes bring their own colours and are built from 8 to 32 pixel authored geometry whose materials follow the features: most are medium (30) or fine (16). Averages: metal 113, roughness 114, coat 136; metal varies by about 37 across a finish. By shine, 25 read semi-matte, 19 satin and 5 gloss, so they glow rather than mirror. They are classed as fine structural colour.'},
        {'heading': 'How they reveal colour', 'body': 'The colour in ASTRA appears through the shine: the paint and the spec disagree in tiny places, so the colour you see changes with light and angle. That is why scale must stay at default. A bigger scale makes the marks bigger than 32 pixels and the effect turns into ordinary pattern.'},
        {'heading': 'Placement', 'body': 'One ASTRA finish per car, on the hero zone (hood or side panels), with matte or plain neighbours. Two ASTRA zones compete. Numbers and sponsors should sit on a calm area, never on the ASTRA zone.'},
    ],
    examples=[
        {'title': 'Hero hood', 'goal': 'One ASTRA finish as the focal point.',
         'settings': {'Hood zone': 'Any ASTRA finish', 'BASE COLOR': "Use finish's own color", 'BASE SCALE': '1.00x', 'Neighbours': 'Soft Matte or Satin in a matching colour'},
         'result': 'The hood glows with fine colour detail and the rest of the car stays calm.'},
        {'title': 'Colour tuning without breaking it', 'goal': 'Shift the hue gently.',
         'settings': {'HUE SHIFT': '-15', 'SATURATION': '-10', 'BASE COLOR': "Use finish's own color"},
         'result': 'A tuned version of the same design; a solid colour would have flattened it.'},
    ],
    combos=[{'with': 'finishes.surface_intent', 'why': 'ASTRA belongs to fine structural colour.'},
            {'with': 'spec.paint_spec_marriage', 'why': 'Hero zone and calm neighbours.'},
            {'with': 'spec.angle_reveal', 'why': 'The idea behind colour moving through the shine.'}],
    faq=[
        {'q': 'Can I recolour ASTRA?', 'a': 'Use hue, saturation and brightness. A solid colour wipes the design out.'},
        {'q': 'Why does it look plain in the preview?', 'a': 'Fine detail averages out in a small preview. Check it on the car and the spec views.'},
        {'q': 'How many ASTRA finishes?', 'a': '50.'},
        {'q': 'Does ASTRA work on numbers?', 'a': 'No. Keep numbers on a calm area.'},
    ],
    mistakes=[
        {'symptom': 'The finish lost its sparkle.', 'cause': 'Scale was raised.', 'fix': 'Reset scale to 1.00x or lower.'},
        {'symptom': 'Every zone has ASTRA and the car is chaos.', 'cause': 'Too many hero finishes.', 'fix': 'Keep one and use matte on the rest.'},
    ],
    protips=['If a fine finish looks like it did nothing, add more small events rather than bigger marks, and look at the spec views.',
             'ASTRA averages a high coat byte (136), so it reads as soft glow, not wet gloss.'])

enrich(D, 'finishes.ghost_geometry_clearcoat', level='pro',
    sources=[W + ':3440-3466', ATL, SI + ':98-110', 'engine/compose.py:2625-2712'],
    deep=[
        {'heading': 'Where the pattern is hidden', 'body': 'Ghost Geometry hides its stripes, grids and hexes in the clear coat. Head on, the paint looks plain. At an angle the clear coat carves cells that mirror the environment, so the pattern appears. The Depth and Geometry shelf has 41 finishes with a high average metal (207), low roughness (50) and a coat average of 110; gloss (15) and satin (14) are the most common shines, plus 6 mirrors.'},
        {'heading': 'The Ghost Shift recipe', 'body': 'Use a Ghost Geometry finish as the base, pick a colour, drag brightness far down, view on a daytime track. Measured: metal 176 to 255 everywhere keeps reflections tinted with the paint hue even when the paint is nearly black. The clear coat varies in large coherent cells (about 124 to 240) and mirrors the sky and sun. Dark red flashes teal, purple flashes green, green flashes gold.'},
        {'heading': 'Clearcoat finishes', 'body': 'Clearcoat finishes work the same way: spec-driven, plain paint, character in the top coat. Because they live in the shine, your paint colour stays yours. They look like almost nothing on a flat preview, which is expected.'},
    ],
    examples=[
        {'title': 'Ghost Shift', 'goal': 'A dark colour that flashes a second colour.',
         'settings': {'Base Material': 'A Ghost finish from Depth and Geometry', 'Colour': 'Deep purple', 'BRIGHTNESS': 'Dragged far down', 'Track': 'A daytime one'},
         'result': 'The car reads near-black head on and flashes green at angles.'},
        {'title': 'Hidden stripes', 'goal': 'Stripes that only show at an angle.',
         'settings': {'Base Material': 'Ghost Stripes', 'BASE COLOR': 'Use source paint (spec only)'},
         'result': 'Plain paint head on and stripes in the reflections.'},
    ],
    combos=[{'with': 'spec.angle_reveal', 'why': 'The full explanation of the effect.'},
            {'with': 'spec.blend_modes', 'why': 'Ghost Carve gives the same effect on any base.'}],
    faq=[
        {'q': 'Why do I see nothing?', 'a': 'Ghost finishes show at angles and in sun. A flat preview shows almost nothing.'},
        {'q': 'Does the paint colour change?', 'a': 'No. The effect is in the clear coat.'},
        {'q': 'Which track is best?', 'a': 'A daytime track. Night and indoor lighting mute the flashes.'},
        {'q': 'How many Ghost finishes?', 'a': 'The Depth and Geometry shelf has 41.'},
    ],
    mistakes=[
        {'symptom': 'The flashes are weak.', 'cause': 'Paint is too bright or the lighting is dim.', 'fix': 'Crush the paint toward black and use a sunny track.'},
        {'symptom': 'It looks like plain paint.', 'cause': 'Judged head on in a flat view.', 'fix': 'Judge on the curved hood, roof and fenders in the sim.'},
    ],
    protips=['Judge on the hood, roof and fenders; a flat door holds the base look longer.',
             'The spec varies across a Ghost finish, so it is not flat like Foundation.'])

enrich(D, 'finishes.colorshoxx_and_shift', level='pro',
    sources=[ATL, W + ':3591-3631', 'docs/COLORSHOXX_ANGLE_REVEAL.md:1', W + ':4223'],
    deep=[
        {'heading': 'What is on the shelves', 'body': 'Prizm has 40 chameleon metals, averaging metal 173, roughness 94 and coat 166. Spectrum Shift has 60 spectral colour pairs averaging metal 103, roughness 115 and coat 45. Fractured Nightshift has 50 day and night flips averaging metal 107, roughness 98 and coat 103, almost all satin. The retired ColorShoxx family (78 dual-tone finishes) is off the shelves. Color Science also holds Color Clash and the two gradient shelves.'},
        {'heading': 'How the shift is built', 'body': 'A true hue rotation does not exist in the sim. These finishes combine paint-tinted metal, an environment-coloured clear coat and roughness gating, with metal cells that cross the lighting threshold at different times. A colour-change finish should show two named colours to a normal driver, reveal panel by panel and survive shade, glare and replay distance.'},
        {'heading': 'Using COLOR FLIP', 'body': 'Where available, COLOR FLIP (0 to 355) rotates the dark structure of the paint to a second hue: 90 gives a neighbouring hue, 180 the opposite. Keep the base dark and the scale fine. Warm bright bases blend into warm sun and lose the second colour, so for those use the dark buried route.'},
    ],
    examples=[
        {'title': 'Chameleon hood', 'goal': 'A hood that shifts between two colours.',
         'settings': {'Shelf': 'Prizm or Spectrum Shift', 'BASE COLOR': "Use finish's own color", 'COLOR FLIP': '90'},
         'result': 'A neighbouring second hue appears in the reflections.'},
        {'title': 'Day and night flip', 'goal': 'A car with different looks in sun and under lights.',
         'settings': {'Shelf': 'Fractured Nightshift', 'Base': 'Dark', 'Scale': 'Default'},
         'result': 'The car changes character between daylight and night lighting.'},
    ],
    combos=[{'with': 'spec.angle_reveal', 'why': 'The mechanism behind every shift finish.'},
            {'with': 'finishes.fractured_mortal_neon', 'why': 'Fractured shelves share the idea.'}],
    faq=[
        {'q': 'Does it really change colour?', 'a': 'It fakes it with paint plus spec. There is no true shader hue shift.'},
        {'q': 'Why dark?', 'a': 'A dark paint exposes the specular lobes that make the flashes.'},
        {'q': 'Does it work at night?', 'a': 'Less. The flashes come from the track environment.'},
        {'q': 'What COLOR FLIP value is the opposite?', 'a': '180.'},
    ],
    mistakes=[
        {'symptom': 'Scaling up killed the shift.', 'cause': 'The cells are now bigger than 32 pixels.', 'fix': 'Leave scale default.'},
        {'symptom': 'Only one colour shows.', 'cause': 'Warm bright base in warm sun.', 'fix': 'Choose a dark or cool base.'},
    ],
    protips=['Judge on the car at distance with the car turned, in the sim.',
             'Colour shifts need more than one lighting condition to judge: try sun, shade and night.'])

enrich(D, 'finishes.fractured_mortal_neon', level='pro',
    sources=[ATL, W + ':4010-4040', W + ':4075-4090', W + ':4019-4020', SI + ':108-122'],
    deep=[
        {'heading': 'Two families of Fractured', 'body': 'The Fractured series splits by their spec. The mirror-carrier shelves (Minds 55, Souls 30, Forge 88, Opalfire 50) average metal 233 to 242 and coat 237 to 252, with roughness 31 to 61: the night-carrier state that reads hot pink in a spec picture. The colour-detail shelves (Elements 60, Cosmos 60, Nightshift 50, Flames 75, Wilds 110, Tessera 50, Relics 50) average much lower metal, from 57 to 156.'},
        {'heading': 'Why a carrier is not one flat fill', 'body': 'A Fractured carrier uses metal 242 to 255, roughness 22 to 78 and coat 246 to 255. A single flat magenta fill looks dead; the good ones use 6 to 8 or more quantised carriers, crushed dark shades, black pits and thin bright veins, and white clear-coat razor lips of 40, 16, 16 in 2 to 6 pixel lines. Hologram-type cells take discrete states in 8 to 18 pixel cells.'},
        {'heading': 'Mortal Shokk and Neon Underground', 'body': 'Mortal Shokk has 26 finishes built on 4K plates, each with its own hand-built spec map. Neon Underground has 25 street-racing neon finishes whose fine coloured detail averages metal 60, roughness 81 and coat 123. Both are fine structural colour and both bring their own colours.'},
    ],
    examples=[
        {'title': 'Weather hero', 'goal': 'A body panel with a thematic micro-world.',
         'settings': {'Shelf': 'Fractured Elements', 'BASE COLOR': "Use finish's own color", 'Preview': 'See on paint'},
         'result': 'Fine detail tied to the theme, best read close.'},
        {'title': 'Mirror carrier', 'goal': 'A night-bright mirror look.',
         'settings': {'Shelf': 'Fractured Opalfire', 'Colour': 'Own', 'Track': 'Daytime then night'},
         'result': 'Metal 242, roughness 31 and coat 246 on average; the car flashes strongly as lighting changes.'},
    ],
    combos=[{'with': 'finishes.colorshoxx_and_shift', 'why': 'The sibling shelves built on the same flip idea.'},
            {'with': 'spec.angle_reveal', 'why': 'The mechanism.'},
            {'with': 'spec.reading_by_colour', 'why': 'Why carriers look pink in a spec picture.'}],
    faq=[
        {'q': 'Why is the spec view pink?', 'a': 'High metal, high coat byte and low roughness pack into pink. It is not paint.'},
        {'q': 'Can I scale Fractured up?', 'a': 'No. The detail is the point.'},
        {'q': 'How many Fractured shelves?', 'a': 'Thirteen, from 20 to 110 finishes each.'},
        {'q': 'Does a solid colour work?', 'a': 'It overrides the design. Use hue shift.'},
    ],
    mistakes=[
        {'symptom': 'One flat magenta fill looks dead.', 'cause': 'A single carrier has no variety.', 'fix': 'Use a finish built with 6 to 8 carriers, or one from the shelf.'},
        {'symptom': 'Big scale broke it.', 'cause': 'Detail is 8 to 32 pixels.', 'fix': 'Reset scale.'},
    ],
    protips=['Mortal Shokk plates are 4K and carry hand-built spec maps, so their detail holds up at distance.',
             'Fractured Wilds is the largest shelf with 110 finishes and averages semi-matte, which suits dirty tracks.'])

enrich(D, 'finishes.plates_xlab_works', level='intermediate',
    sources=[ATL, W + ':3995-4001', 'scripts/protected_finishes.json:1'],
    deep=[
        {'heading': 'What each shelf averages', 'body': 'SOURCE PATTERN PLATES (24): metal 122, roughness 115, coat 152, authored pattern images. X LAB (50): metal 138, roughness 69, coat 152, a gloss and satin mix with large spread. SHOKK WORKS (89): metal 90, roughness 114, coat 127, mostly satin. PRISM FORGE (50): metal 150, roughness 122, coat 100, semi-matte iridescent. FLAW LAB (25): metal 85, roughness 79, coat 127, almost all satin. IMPOSSIBLE FINISHES (10): metal 104, roughness 140, coat 108, micro and fine.'},
        {'heading': 'Protected gold standards', 'body': 'A handful of X LAB and Paradigm finishes are protected: they never change between versions, so a livery that uses them looks the same next season. All of these shelves bring their own colours, so a solid colour overrides their look.'},
    ],
    examples=[
        {'title': 'One experimental hero', 'goal': 'Use an X LAB finish as the car\'s statement.',
         'settings': {'Hood': 'An X LAB finish', 'BASE COLOR': "Use finish's own color", 'Rest of car': 'Plain gloss or matte'},
         'result': 'One experimental look with calm surroundings.'},
        {'title': 'Authored plate', 'goal': 'Use a Source Pattern Plate with its matching spec overlay.',
         'settings': {'Finish': 'A Source Pattern Plate finish', 'Spec overlay': 'The spec pattern of the same name'},
         'result': 'Paint and spec match each other.'},
    ],
    combos=[{'with': 'spec.pattern_groups', 'why': 'Spec Source Pattern Plates match these plate finishes by name.'},
            {'with': 'finishes.what_makes_a_finish_pop', 'why': 'One hero per car.'}],
    faq=[
        {'q': 'Will a protected finish change?', 'a': 'No.'},
        {'q': 'What is FLAW LAB?', 'a': 'Industrial inspection looks: etches, stress bands and cracks.'},
        {'q': 'What is SHOKK WORKS?', 'a': 'Engineered specials such as foil webs, charge ropes and lightning channels.'},
        {'q': 'Can I recolour?', 'a': 'Use hue and saturation. A solid colour overrides the design.'},
    ],
    mistakes=[
        {'symptom': 'Looks washed out with a solid colour.', 'cause': 'Experimental finishes bring their own colours.', 'fix': 'Use own colour and tune hue.'},
        {'symptom': 'Two experimental finishes fight.', 'cause': 'More than one hero.', 'fix': 'Keep one.'},
    ],
    protips=['X LAB averages roughness 69, glossier than most shelves, so it reads sharper in sun.',
             'Plates pair with spec patterns of the same name.'])
print('finishes A done')
