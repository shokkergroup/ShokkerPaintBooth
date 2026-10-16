#!/usr/bin/env python
"""ideas batch 03 (2026-10-05): eras and classic liveries - 50s diner, 60s, 70s, 80s, 90s, powder-blue-and-orange, twin stripes, muscle, hot rod."""
from enc_ideas_build import *

X = lambda t, g, s, r, screen=None: dict(title=t, goal=g, settings=s, result=r, **({'screen': screen} if screen else {}))
D = lambda h, b: dict(heading=h, body=b)
Q = lambda q, a: dict(q=q, a=a)
M = lambda s, c, f: dict(symptom=s, cause=c, fix=f)
ERA = doc(DOC_LIVERY, 'Era palettes')
FAM = doc(DOC_LIVERY, 'Classic scheme families')
WHERE = doc(DOC_LIVERY, 'Where things go on a side panel')

if todo('retro_70s'):
    art('retro_70s', 'Retro 70s: cream, orange and brown with warm earth tones',
        'The 70s look is cream or harvest-gold body, orange and brown stripes, earth-tone geometry and matte-to-satin paint. Warm and low-saturation, never neon.',
        'Buyers ask for "retro 70s", "seventies" or "groovy". The palette is cream, orange and brown with mustard and rust; the finishes are soft (satin or gloss, not metallic), and the graphics are wide bands and zigzags. Disco-era sparkle is a separate, shinier look.',
        'beginner',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #efe2c2 (cream) for the body.',
         'Add the stripes: ' + S_BOX + ' Make one zone orange #e0731f and one brown #6b3b1e, both Gloss, drawn as parallel long bands along the sides and over the hood.',
         'For texture: open PATTERN and choose Earth Tone Geo or Funk Zigzag, Paint mode Blend, Scale (pattern) 0.6, on the lower body only.',
         'Or pick a ready-made 70s finish in Base Material: Shag Harvest or Corduroy Brown. ' + S_RENDER],
        [X('Cream, orange and brown stripes', 'The classic 70s livery', {'Body': 'Gloss, #efe2c2', 'Stripe 1': 'Draw box long band, Gloss, #e0731f', 'Stripe 2': 'Draw box thinner band under it, Gloss, #6b3b1e'}, 'Cream car with a bold orange and brown side stripe.', 'cat_far_out'),
         X('Funk zigzag lower body', 'Pattern accent', {'Body': 'Satin, #d9a521 (mustard)', 'PATTERN': 'Funk Zigzag, Paint mode Blend, Scale (pattern) 0.6', 'Pattern zone': 'Draw box over the rocker'}, 'Mustard car with a zigzag skirt.', 'cat_groovy_vibes')],
        [D('Palette', 'The shipped era notes list powder blue and orange, navy and white, harvest orange, rust brown, mustard and cream for the 1960s-70s. Keep to those and avoid neon.'),
         D('Finish', 'Soft Gloss (roughness 30) or Satin (95) in flat colours. Metallic and chrome belong to the 80s and show-car looks.')],
        [Q('How do I make a retro 70s car?', 'Cream body, orange and brown stripes, earth-tone pattern.'),
         Q('Disco or groovy?', 'Groovy is earth tones; disco adds sparkle and chrome (try the Disco finishes).'),
         Q('Which finish?', 'Gloss or Satin with solid colours.')],
        [M('Looks modern', 'Too saturated or metallic', 'Use warm low-saturation colours and plain gloss.'), M('Stripes crooked', 'Boxes not aligned', 'Check each side on the CAR view.')],
        ['Three stripes in a descending width reads instantly 70s.'],
        ['retro 70s', '70s style', 'seventies look', '1970s livery', '70s livery', 'groovy look', 'earth tones', 'brown and orange', 'harvest gold', 'avocado green', 'disco look', 'shag look', 'vintage 70s'],
        fin=['base::gloss', 'base::satin', 'base::fo_shag_harvest', 'base::fo_corduroy_brown'], pat=['decade_70s_earth_tone_geo', 'decade_70s_funk_zigzag'],
        related=['ideas.retro_60s', 'ideas.retro_80s', 'recipes.retro_stripes', 'ideas.racing_stripes'], combos=[('recipes.retro_stripes', 'Hand-built stripes.')],
        screens=['cat_far_out', 'cat_groovy_vibes'], quick=True, extra_src=[ERA])

if todo('retro_60s'):
    art('retro_60s', 'Retro 60s: powder blue, mod blocks and sunburst',
        'The 60s look is powder blue, navy, white and orange with mod colour blocks, op-art and sunburst graphics on plain glossy paint. Bright but still soft.',
        'Sixties styling mixes racing-heritage colours (powder blue, navy, white) with pop-art graphics: colour blocks, halftone dots, peace and flower motifs. Keep the paint plain and put the personality in a few bold graphic zones.',
        'beginner',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #8cc3e6 (powder blue) or #f4f4f4 (white).',
         'Add a colour-block zone: ' + S_BOX + ' Open PATTERN and choose Mod Color Block, Paint mode Overlay (so it paints its own colours), Scale (pattern) 0.7.',
         'For psychedelic flavour pick 60s Sunburst or Flower Power in Base Material on the hood only.',
         'Trim with navy #1c2a56 Gloss stripes and keep numbers white on navy. ' + S_RENDER],
        [X('Powder blue with mod blocks', 'Pop-art racer', {'Body': 'Gloss, #8cc3e6', 'Block zone': 'Draw box on the lower side, PATTERN Mod Color Block, Paint mode Overlay, Scale (pattern) 0.7'}, 'Light blue car with a Mondrian-style band.', 'cat_groovy_vibes'),
         X('Sunburst hood', 'Hippie accent', {'Body': 'Gloss, #f4f4f4', 'Hood zone': 'Draw box, Base Material 60s Sunburst'}, 'White car with a radiating rainbow bonnet.', 'cat_far_out')],
        [D('Overlay or Blend', 'Overlay mode lets the pattern paint its own colours; Blend keeps your paint. Mod blocks need Overlay to show their colours.'),
         D('Keep paint plain', 'Gloss keeps the 60s feel and sponsors readable; save the loud finishes for one panel.')],
        [Q('What colours say 60s?', 'Powder blue, navy, orange, mustard, white.'), Q('Psychedelic?', 'Use the Groovy Vibes finishes on a single panel.'), Q('Race-style or hippie?', 'Race-style is blue/white/orange stripes; hippie is swirl and flower finishes.')],
        [M('Looks like a poster', 'Pattern over the whole car', 'Limit to a box.'), M('Colours muddy', 'Blend mode with mid-tones', 'Switch pattern to Overlay.')],
        ['Navy plus powder blue plus one orange accent is the safest 60s trio.'],
        ['retro 60s', '60s style', 'sixties look', '1960s livery', '60s livery', 'mod look', 'pop art look', 'op art', 'psychedelic look', 'hippie look', 'flower power', 'tie dye look', 'vintage 60s'],
        fin=['base::gloss', 'base::sunburst_60s', 'base::flower_power'], pat=['decade_60s_gogo_check', 'decade_60s_pop_art_halftone'],
        related=['ideas.retro_70s', 'ideas.gulf_style', 'ideas.vintage_diner_50s'], combos=[('ideas.gulf_style', 'The racing side of the 60s.')],
        screens=['cat_groovy_vibes', 'cat_sock_hop'], extra_src=[ERA])

if todo('retro_80s'):
    art('retro_80s', 'Retro 80s: hot pink, cyan and sharp colour blocks',
        'The 80s look is hot pink, cyan and purple on black or white, sharp angular blocks, grid and sunrise graphics, and glossy or chrome paint.',
        'Eighties styling is neon on dark: pink and cyan on black, geometric blocks, outrun sunset bars and chrome type. Build it with a glossy dark body, two neon colours in sharp shapes and one grid or stripe pattern.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #0d0d10 (or white #f4f4f4).',
         'Add colour blocks as zones: hot pink #ff2bd6 and cyan #00e5ff, Gloss, drawn as sharp diagonal bands (Draw box, then PATTERN Chevron to sharpen).',
         'Add a grid: PATTERN Neon Grid, Paint mode Blend, Scale (pattern) 0.6 on the lower body.',
         'Or pick Outrun Stripe, Digital Sunrise or Miami Pastel in Base Material for ready-made 80s graphics. ' + S_RENDER],
        [X('Pink and cyan on black', 'Miami night', {'Body': 'Gloss, #0d0d10', 'Block 1': 'Gloss, #ff2bd6', 'Block 2': 'Gloss, #00e5ff', 'PATTERN': 'Neon Grid, Blend, Scale (pattern) 0.6'}, 'Dark car with neon geometry.', 'cat_bad_rad'),
         X('Outrun stripe', 'Ready-made', {'Base Material': 'Grid: Outrun Stripe', 'BASE COLOR': "Use finish's own color"}, 'Red and cyan speed chevrons on midnight enamel.', 'cat_neon_underground')],
        [D('Neon needs dark', 'Neon colours only glow against a dark ground; on white they look pastel. Use black or deep navy as the quiet colour.'),
         D('Sharp beats soft', 'Hard diagonal edges and stepped shapes read 80s; gradients read 70s or modern.')],
        [Q('What is the 80s palette?', 'Hot pink, cyan, purple on black or white.'), Q('Chrome in the 80s look?', 'Yes, as type or trim.'), Q('Miami style?', 'Pink, aqua and lemon pastels: Grid: Miami Pastel.')],
        [M('Looks pastel', 'Neon on white', 'Dark body.'), M('Too busy', 'Too many shapes', 'Two neon colours, one pattern.')],
        ['One diagonal split with two neon colours beats five shapes.'],
        ['retro 80s', '80s style', 'eighties look', '1980s livery', '80s livery', 'miami vice', 'outrun', 'synthwave', 'vaporwave', 'neon 80s', 'arcade look', 'memphis style', 'pink and cyan', 'radical 80s'],
        fin=['base::gloss', 'base::rad_outrun_stripe', 'base::rad_digital_sunrise', 'base::rad_miami_pastel'], pat=['decade_80s_neon_grid', 'chevron'],
        related=['ideas.cyberpunk_synthwave', 'ideas.neon_night', 'ideas.retro_90s'], combos=[('ideas.cyberpunk_synthwave', 'Same neon, darker mood.')],
        screens=['cat_bad_rad', 'cat_neon_underground'], extra_src=[ERA])

if todo('retro_90s'):
    art('retro_90s', 'Retro 90s: teal, purple and magenta splashes',
        'The 90s look is teal, purple and magenta splashes, geometric minimal shapes, grunge flannel and Y2K chrome, in mixed gloss and matte.',
        'Nineties styling runs two ways: loud Saved-by-the-bell colour splashes and zigzags, or grungy flannel and denim. Late 90s tips toward silver Y2K chrome. Pick one thread.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #0f9d9a (teal) or #1a1a1e.',
         'Splash zones in purple #6a2c91 and magenta #d6249f: ' + S_BOX + ' Add PATTERN Rave Zigzag or Geo Minimal, Paint mode Overlay, Scale (pattern) 0.6.',
         'For grunge: Base Material Flannel: Flannel Forest, or Distressed Denim. For Y2K: Cdrom: Y2K Chrome.',
         # ENC_READER_FIX 2026-10-05: the only catalogue finish that renders teal/purple/pink SPLASHES (looked at on the example car)
         "For the splash look in one go: Base Material Radical: Splatter Tee (fine teal, purple and pink thrown paint over a light base), BASE COLOR Use finish's own color.",
         S_RENDER],
        [X('Teal and purple splash', 'Loud 90s', {'Body': 'Gloss, #0f9d9a', 'Splash zone': 'Draw box, PATTERN Rave Zigzag, Overlay, Scale (pattern) 0.6'}, 'Teal car with a purple zigzag panel.', 'cat_all_that'),
         X('Y2K chrome', 'Late 90s', {'Base Material': 'Cdrom: Y2K Chrome', 'BASE COLOR': "Use finish's own color"}, 'Scattered liquid-silver inflatable chrome.', 'cat_all_that')],
        [D('Two threads', 'Bright splash (teal/purple/magenta) or washed grunge (flannel, denim). Mixing them looks confused.'),
         D('Overlay mode', 'Patterns in Overlay paint their own colours; use that for splash graphics.')],
        [Q('Colours of the 90s?', 'Teal, purple, magenta; or flannel red and forest green.'), Q('Y2K look?', 'Silver chrome fragments: Cdrom: Y2K Chrome.'), Q('Grunge?', 'Distressed Denim or Flannel finishes.')],
        [M('Looks 80s', 'Neon on black', 'Switch to teal and purple on light.'), M('Muddy', 'Mixed grunge and splash', 'Pick one thread.')],
        ['Memphis-style squiggles are 80s; 90s shapes are more angular and minimal.'],
        ['retro 90s', '90s style', 'nineties look', '1990s livery', '90s livery', 'y2k look', 'y2k chrome', 'grunge look', 'flannel look', 'saved by the bell', 'rave look', 'vintage 90s', 'millennium look'],
        fin=['base::gloss', 'base::rad_splatter_tee', 'base::at_y2k_chrome', 'base::at_flannel_forest', 'base::at_distressed_denim'], pat=['decade_90s_rave_zigzag', 'decade_90s_geo_minimal'],
        related=['ideas.retro_80s', 'ideas.punk_grunge_street'], combos=[('ideas.punk_grunge_street', 'The grungy 90s thread.')],
        screens=['look_splatter_tee'], extra_src=[ERA])

if todo('vintage_diner_50s'):
    art('vintage_diner_50s', 'Vintage 50s diner: pastel metalflake, checker and chrome',
        'The 50s look is pink and turquoise metalflake, cream, cherry red, black and white checker and bright chrome trim.',
        'Fifties diners and show cars use pastel metalflake, two-tone panels, checkerboard and plenty of chrome. Pair a pastel body with a cream roof and chrome side trim.',
        'beginner',
        [S_ZONE, 'Under BASE press Base Material and search Pink Metalflake or Turquoise Metalflake for the body, with BASE COLOR on Use finish\'s own color.',
         'Make the roof cream: ' + S_BOX + ' Gloss with #efe2c2.',
         'Add chrome trim zones in Satin Chrome (metal 250, roughness 45, coat 40) with BASE COLOR on Use source paint (spec only).',
         'Optional: Diner Checkerboard finish on a lower band. ' + S_RENDER],
        [X('Pink metalflake two-tone', 'Classic 50s', {'Body': 'Pink Metalflake', 'Roof zone': 'Draw box, Gloss, #efe2c2', 'Trim': 'Satin Chrome, Use source paint'}, 'Pink sparkle body with cream roof and chrome edge.', 'cat_sock_hop'),
         X('Black and white checker band', 'Diner floor', {'Band zone': 'Draw box on the rocker, Base Material Diner Checkerboard'}, 'Checkered lower band on a cherry red body.', 'cat_sock_hop')],
        [D('Flake in pastel', 'Metalflake in pastel colours sparkles at an angle to the sun; the preview shows it flat.'), D('Chrome frames it', 'Chrome trim separates the two tones and ties the era together.')],
        [Q('50s colours?', 'Pink, turquoise, cream, cherry red.'), Q('Chrome?', 'Trim only.'), Q('Checker?', 'Lower band or hood stripe.')],
        [M('Looks modern', 'No chrome trim', 'Add Satin Chrome edging.'), M('Flake invisible', 'Judged in preview', 'Look in the sim.')],
        ['Two-tone with a cream roof says 50s instantly.'],
        ['50s style', 'fifties look', 'vintage diner', 'diner look', 'sock hop', 'pink car', 'turquoise car', 'metalflake pastel', 'chrome and pastel', 'checkerboard', 'happy days', 'rockabilly', 'jukebox look', 'retro diner'],
        fin=['base::pink_fleck', 'base::turquoise_fleck', 'base::gloss', 'base::f_satin_chrome', 'base::diner_checker'],
        related=['ideas.retro_60s', 'ideas.chrome_show_car', 'ideas.checkered_flag'], combos=[('ideas.chrome_show_car', 'Chrome trim practice.')],
        screens=['cat_sock_hop', 'spec_chrome'], extra_src=[ERA])

if todo('gulf_style'):
    art('gulf_style', 'Powder blue and orange: the vintage endurance livery',
        'A powder-blue body with a bold orange centre stripe, thin navy pinlines and white numbers in round plates. Describe it with colours and layout only.',
        'Buyers ask for "vintage Gulf colours" or "that blue and orange racing livery". It is a timeless two-colour layout: light blue body, orange stripe over hood, roof and trunk, and a tidy navy line either side. Use generic colours and plain shapes; no logos.',
        'beginner',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #7ab8e6 (powder blue) for the body.',
         'Orange stripe: ' + S_BOX + ' Draw a long band down the centre of the hood, roof and trunk, Gloss with #f26b1d.',
         'Navy pinlines: two thin boxes either side, Gloss #14284b (or PATTERN Pinstripe).',
         'Numbers: white or navy on a round orange plate on each door. ' + S_RENDER],
        [X('Hood-roof-trunk stripe', 'The classic centre stripe', {'Body': 'Gloss, #7ab8e6', 'Stripe': 'Draw box down the car centre, Gloss, #f26b1d', 'Pinlines': 'Gloss, #14284b, two thin boxes'}, 'Blue car with an orange spine.', 'cat_foundation'),
         X('Satin heritage', 'Modern take', {'Body': 'Satin, #7ab8e6', 'Stripe': 'Satin, #f26b1d'}, 'Same layout in soft satin.', 'spec_matte')],
        [D('The 60-30-10 split', 'About 60 percent blue, 30 percent orange stripe, 10 percent navy pinline and white numbers.'), D('Alignment', 'The stripe must continue across hood, roof and trunk and meet the bumper colour.')],
        [Q('How do I do vintage blue and orange?', 'Powder blue body, orange centre stripe, navy pinlines.'), Q('Can I use the real logo?', 'No: build with colours and shapes only.'), Q('Gloss or satin?', 'Gloss is traditional.')],
        [M('Stripe breaks at the roof', 'Zones drawn separately', 'Draw each panel and check the CAR view.'), M('Orange too dull', 'Mid-tone orange', 'Use a pure #f26b1d.')],
        ['A very thin navy line either side of the orange makes it look professional.'],
        ['vintage gulf colours', 'gulf style', 'gulf livery', 'gulf colors', 'blue and orange livery', 'powder blue and orange', 'endurance livery', 'classic racing livery', '917 style', 'vintage racing livery', 'heritage livery', 'baby blue and orange'],
        fin=['base::gloss', 'base::satin'], pat=['pinstripe'],
        related=['ideas.martini_style', 'ideas.le_mans_endurance', 'ideas.racing_stripes', 'ideas.retro_60s'], combos=[('ideas.racing_stripes', 'Stripe mechanics.')],
        screens=['cat_foundation', 'cat_union_jacked'], quick=True, extra_src=[FAM, ERA])

if todo('martini_style'):
    art('martini_style', 'Twin stripes along the side: the three-stripe racing livery',
        'A white body with three parallel stripes (deep blue, light blue and red) running the full length of the side and continuing over the nose and tail.',
        'The famous racing look is a clean white car with thin parallel stripes that follow the body line. Describe it as colours and layout: three colours, equal widths, a tidy gap, and a straight run from nose to tail.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #f4f4f4 for the body.',
         'Draw three stripe zones along each side, from front to rear: ' + S_BOX + ' Each is Gloss: #14327a (deep blue), #4a8fd6 (light blue), #c8102e (red).',
         'Put the stripes between the beltline and the rocker (roughly 0.30 to 0.65 of the height is the number zone; keep stripes below or above it).',
         'Continue the stripes over the hood and trunk with matching boxes. ' + S_RENDER],
        [X('Three-stripe side', 'Clean heritage', {'Body': 'Gloss, #f4f4f4', 'Stripes': 'Three long boxes, Gloss, #14327a, #4a8fd6, #c8102e', 'Numbers': 'Black on white door'}, 'White car with a tri-colour run.', 'cat_foundation'),
         X('Satin modern take', 'Understated', {'Body': 'Satin, #f4f4f4', 'Stripes': 'Satin, the same three colours'}, 'Softer sheen on the same layout.', 'spec_matte')],
        [D('Equal widths', 'Stripes read as one object when widths and gaps are equal.'), D('Straight on the flat sheet', 'The car is unwrapped, so boxes must line up across the door and fender seams.')],
        [Q('How do I do the three-stripe look?', 'White body, three equal thin stripes, straight run.'), Q('Can I use real colours?', 'Any three; deep blue, light blue and red is the classic.'), Q('Does it need chrome?', 'No.')],
        [M('Stripes wobble', 'Boxes drawn freehand', 'Redo with rectangles and check seams.'), M('Stripes hit the number', 'Stripes cross the door centre', 'Keep them above or below it.')],
        ['Thin stripes with a gap equal to their width look expensive.'],
        ['martini stripes', 'martini style', 'martini livery', 'three stripe look', 'tri color stripes', 'racing stripes white car', 'classic stripe livery', 'twin stripes', 'side stripes', 'stripe run nose to tail'],
        fin=['base::gloss', 'base::satin'], pat=['pinstripe'],
        related=['ideas.gulf_style', 'ideas.racing_stripes', 'ideas.clean_classy'], combos=[('ideas.clean_classy', 'White plus stripes is the cleanest livery.')],
        screens=['cat_foundation', 'ui_zone_apply_area'], extra_src=[FAM])

if todo('old_school_muscle'):
    art('old_school_muscle', 'Old school muscle: bold colour, black stripes, chrome',
        'Muscle-car paint is a bold saturated metallic, wide black hood and trunk stripes, a flat black scoop and bright chrome trim.',
        'The muscle car look is loud and simple: one saturated colour, two wide parallel stripes over the hood, roof and trunk, black accents and chrome. Use metallic, not candy, and keep the layout symmetrical.',
        'beginner',
        [S_ZONE, S_BASE % 'Metallic (metal 200, roughness 50, coat 16)' + ' with Use solid color #5c1f7a (plum) or #e8631a (orange).',
         'Stripes: ' + S_BOX + ' Two parallel long boxes over hood, roof and trunk, Matte or Gloss, Use solid color #0b0b0e.',
         'A flat black scoop or hood panel: Flat Black zone.',
         'Chrome trim zones in Satin Chrome with Use source paint. ' + S_RENDER],
        [X('Orange with black stripes', 'Hemi-era look', {'Body': 'Metallic, #e8631a', 'Stripes': 'Two boxes, Gloss, #0b0b0e', 'Hood scoop': 'Flat Black'}, 'Orange metallic with black twin stripes.', 'cat_bad_rad'),
         X('Plum with white stripe', 'Cool muscle', {'Body': 'Metallic, #5c1f7a', 'Stripe': 'Gloss, #f4f4f4'}, 'Purple metallic with a white racing stripe.', 'cat_color_clash')],
        [D('Metallic not candy', 'Metallic is metal 200, roughness 50, coat 16: a bright metal highlight in a flat finish. Candy has roughness 15, a tighter and glassier highlight that suits lowriders.'), D('Stripe widths', 'Wide stripes with a thin gap read muscle; thin lines read European.')],
        [Q('What colours?', 'Orange, plum, yellow, red, blue, white.'), Q('Gloss or matte stripes?', 'Matte stripes on gloss paint is the classic.'), Q('Add scoop?', 'Flat Black panel on the hood.')],
        [M('Looks like a family car', 'No stripes', 'Add stripes.'), M('Stripe off centre', 'Boxes mismatched', 'Check CAR view.')],
        ['Matte black stripes on a gloss body create the contrast that makes it pop.'],
        ['muscle car', 'old school muscle', 'classic muscle', 'american muscle', 'hemi look', 'plum crazy', 'black hood stripes', 'racing stripe muscle', 'detroit look', 'pony car', 'vintage muscle', 'dragstrip look'],
        fin=['base::f_metallic', 'base::gloss', 'base::matte', 'base::flat_black', 'base::f_satin_chrome'],
        related=['ideas.racing_stripes', 'ideas.hot_rod_kustom', 'ideas.aggressive_mean'], combos=[('ideas.racing_stripes', 'Stripe mechanics.')],
        screens=['cat_bad_rad', 'cat_color_clash'], quick=True, extra_src=[FAM])

if todo('hot_rod_kustom'):
    art('hot_rod_kustom', 'Hot rod and kustom: flames, pinstripes and deep gloss',
        'Hot rod style is deep gloss or candy, hot rod flames licking back from the nose, fine pinstripes and chrome trim.',
        'The kustom look: a deep colour, flames that lick from the front, hand-style pinstripes along the edges and chrome. Keep the flames on the front third and let the rest stay clean.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #0b0b0e or cherry #7a0a14.',
         'Flames: ' + S_BOX + ' Draw a box over the hood and front fender, Base Material Hot Rod Flames, BASE COLOR on Use finish\'s own color.',
         'Pinstripes: a zone with PATTERN Pinstripe, Paint mode Blend, Scale (pattern) 0.4 around the flame edge.',
         'Chrome trim zones in Satin Chrome with Use source paint. ' + S_RENDER],
        [X('Black with flames', 'Classic hot rod', {'Body': 'Gloss, #0b0b0e', 'Flame zone': 'Draw box over hood and fender, Base Material Hot Rod Flames', 'Pinstripe': 'Pinstripe, Blend, Scale (pattern) 0.4'}, 'Orange and yellow flames on black.', 'cat_flames'),
         X('Cherry candy with scallops', 'Kustom', {'Body': 'Candy, #7a0a14', 'Trim': 'Satin Chrome, Use source paint'}, 'Deep red candy with chrome edges.', 'spec_candy')],
        [D('Flames on the front third', 'Flames that start at the nose and fade back read as speed; across the whole side they look pasted.'), D('Fine lines', 'Pinstripe scale 0.4 gives thin lines that look hand-lettered.')],
        [Q('How do I add flames?', 'Draw a box and pick Hot Rod Flames.'), Q('Other flames?', 'True Fire, Blue Flame, Ghost Flames.'), Q('Gloss or candy?', 'Both work; black gloss is classic.')],
        [M('Flames cover the number', 'Box too large', 'Limit the box to the front.'), M('Pinstripe too heavy', 'Scale too large', '0.4.')],
        ['Ghost Flames on a black car are a tonal kustom look.'],
        ['hot rod', 'kustom', 'custom hot rod', 'hot rod flames', 'traditional hot rod', 'pinstriping', 'rockabilly car', 'old school hot rod', 'rod and custom', 'flame job'],
        fin=['base::gloss', 'base::flame_hotrod', 'base::f_candy', 'base::f_satin_chrome', 'base::flame_ghost'], pat=['pinstripe'],
        related=['ideas.flames', 'ideas.rat_rod', 'ideas.candy_lowrider', 'recipes.flames_graphics'], combos=[('ideas.flames', 'More flame styles.')],
        screens=['cat_flames', 'cat_fractured_flames'], extra_src=[FAM])
