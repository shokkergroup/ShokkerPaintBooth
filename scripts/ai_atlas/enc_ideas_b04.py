#!/usr/bin/env python
"""ideas batch 04 (2026-10-05): motorsport and car-culture styles - JDM, drift, rally, endurance, touring, oval, luxury black and gold, stripes, checker, speed lines."""
from enc_ideas_build import *

X = lambda t, g, s, r, screen=None: dict(title=t, goal=g, settings=s, result=r, **({'screen': screen} if screen else {}))
D = lambda h, b: dict(heading=h, body=b)
Q = lambda q, a: dict(q=q, a=a)
M = lambda s, c, f: dict(symptom=s, cause=c, fix=f)
ERA = doc(DOC_LIVERY, 'Era palettes')
FAM = doc(DOC_LIVERY, 'Classic scheme families')
WHERE = doc(DOC_LIVERY, 'Where things go on a side panel')
READ = doc(DOC_DESIGN, 'Readability first')
THEMES = doc(DOC_DESIGN, 'Themes -> where to look')

if todo('jdm'):
    art('jdm', 'JDM and tuner: sunrise colours, wave scales and wrap-style slashes',
        'JDM style is a clean white or midnight body with red or neon accents, Japanese wave and scale patterns, and tuner-wrap slashes. Build it with plain gloss plus one Japanese-inspired texture.',
        'Buyers asking for "JDM", "tuner" or "import" want a Japanese-street feel: white with red, midnight purple with pink, bright yellow with black. The catalogue has a Rising Sun collection, Neon Underground wraps and wave or scale patterns that carry the look without logos.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #f4f4f4 (white) or #1a1030 (midnight).',
         'Add a red wedge or sunrise accent: ' + S_BOX + ' Gloss with Use solid color #c8102e on the hood and lower side.',
         'Add texture: open PATTERN and choose Seigaiha Scales or Japanese Wave, Paint mode Blend, Scale (pattern) 0.6, on the lower body.',
         'For a ready-made wrap look, pick Import Royalty or Tokyo Rain in Base Material on a box over the hood and doors, BASE COLOR on Use finish\'s own color.',
         S_RENDER],
        [X('White with red sunrise', 'Clean import look', {'Body': 'Gloss, #f4f4f4', 'Wedge zone': 'Draw box, Gloss, #c8102e', 'PATTERN': 'Seigaiha Scales, Blend, Scale (pattern) 0.6'}, 'White car with a red accent and subtle wave scales.', 'cat_rising_sun'),
         X('Tuner wrap panels', 'Slashes and prismatic edges', {'Body': 'Matte, Use solid color #101216', 'Wrap zone': 'Draw box on hood and doors, Base Material Import Royalty'}, 'Razor-vinyl slashes with prismatic edges on a flat dark body.', 'cat_neon_underground'),
         X('Rising Sun Flare', 'Cultural lacquer', {'Base Material': 'Rising Sun Flare', 'BASE COLOR': "Use finish's own color", 'Check': 'about metal 150, roughness 56, coat 43'}, 'A lacquer texture with a warm Japanese-inspired palette.', 'cat_rising_sun')],
        [D('Where to look', 'The catalogue guide points to RISING SUN and ANIME INSPIRED for Japanese looks and NEON UNDERGROUND for tuner night looks.'),
         D('Patterns that carry it', 'Seigaiha Scales and Japanese Wave are traditional wave motifs. Keep Scale (pattern) near 0.6 so they read as fine texture, not wallpaper.'),
         D('Restraint', 'JDM style is usually one colour pair plus a texture, not a collage. White and red is the simplest.')],
        [Q('How do I make a JDM car?', 'White or midnight body, red or neon accent, one wave pattern.'), Q('Which finishes?', 'Rising Sun Flare, Import Royalty, Tokyo Rain, Midnight Drift.'), Q('Can I add kanji or logos?', 'Not as text; place a transparent PNG as a layer if you have the art.')],
        [M('Looks like wallpaper', 'Pattern scale too large', 'Lower Scale (pattern) to 0.5 to 0.6.'), M('Colours fight', 'Too many accent colours', 'One accent only.')],
        ['Midnight Drift and Tokyo Rain suit night races.'],
        ['jdm', 'jdm style', 'jdm look', 'tuner look', 'tuner style', 'import style', 'japanese style car', 'japanese street', 'initial d look', 'stance look', 'hot import', 'tokyo style'],
        fin=['base::gloss', 'base::matte', 'monolithic::rs_rising_sun_flare', 'base::neon_pink_blaze', 'monolithic::neon2_rain', 'monolithic::neon2_splatter'], pat=['seigaiha_scales', 'japanese_wave'],
        related=['ideas.japanese_art', 'ideas.neon_night', 'ideas.drift_car'], combos=[('ideas.drift_car', 'Drift is the dirty cousin.')],
        screens=['cat_rising_sun', 'cat_neon_underground'], quick=True, extra_src=[THEMES])

if todo('drift_car'):
    art('drift_car', 'Drift car: smoke, soot and a neon slash',
        'A drift car looks used and fast: a dark satin body, soot and clutch dust on the lower body and rear, a single neon accent and a few diagonal slashes.',
        'Drift builds are dark, a bit dirty and bright in one place. Use dark satin or matte, put wear where the car works hardest (rocker, rear quarters, bumpers), and add one neon colour for night shots.',
        'intermediate',
        [S_ZONE, S_BASE % 'Satin (metal 0, roughness 95, coat 70)' + ' with Use solid color #1a1c20.',
         'Add soot: a zone with Draw box along the rocker and rear, open BASE > SPEC OVERLAYS > + ADD SPEC OVERLAY, choose Exhaust Soot Gradient, Strength 40.',
         'Add tyre-heat texture: a lower-body box with Base Material Burnout Ember, Base Strength 50 so your colour shows through.',
         'Add the neon: a diagonal slash zone Gloss with #ff2bd6 or #00e5ff, or pick Midnight Drift in Base Material for the hood. ' + S_RENDER],
        [X('Soot and slash', 'Dark with one accent', {'Body': 'Satin, #1a1c20', 'Rocker zone': 'Draw box, SPEC OVERLAY Exhaust Soot Gradient 40', 'Slash zone': 'Gloss, #00e5ff'}, 'Dark car with sooty edges and a cyan streak.', 'cat_dark_city'),
         X('Burnout lower body', 'Tyre-heat tracks', {'Zone': 'Draw box on the lower third', 'Base Material': 'Burnout Ember', 'Base Strength': '50'}, 'Curved heat tracks and ember rubber over your own paint.', 'cat_neon_underground')],
        [D('Wear belongs low and rear', 'Real drift cars gather soot, dust and rubber at the rear, wheel arches and rocker.'), D('Base Strength', '0 is your original paint; 100 is the full finish. Use 40 to 60 for wear.')],
        [Q('How do I make it look used?', 'Soot spec overlay and Burnout Ember at about 50 strength.'), Q('Gloss or satin?', 'Satin or matte.'), Q('Night look?', 'Midnight Drift or Wet Apex.')],
        [M('Looks like mud', 'Wear over the whole car', 'Restrict it to low and rear boxes.'), M('Accent drowned out', 'Neon on a mid-tone', 'Dark body only.')],
        ['Burnt Clutch Dust is another subtle spec overlay for heat marks.'],
        ['drift car', 'drift style', 'drift livery', 'drifting look', 'drift missile', 'smoky look', 'tire smoke look', 'burnout look', 'sooty look', 'used look', 'street drift'],
        fin=['base::satin', 'base::gloss', 'base::neon_orange_hazard', 'monolithic::neon2_splatter', 'monolithic::neon2_torque_scar'], spc=['spec_exhaust_soot_gradient', 'spec_burnt_clutch_dust'],
        related=['ideas.jdm', 'ideas.worn_patina', 'ideas.neon_night'], combos=[('ideas.worn_patina', 'Gentler wear.')],
        screens=['cat_dark_city', 'spec_wear'], extra_src=[THEMES])

if todo('rally'):
    art('rally', 'Rally: big blocks, mud splash and readable numbers',
        'A rally car is a few big flat colour blocks, giant readable numbers, and a dirty lower body of dried mud and clay. Gloss body, dusty spec overlays low.',
        'Rally liveries are simple and loud so they read through dust: a white or bright body, a bold roof and hood block, large numbers and a muddy lower third. The mud is mostly a spec effect, so the colours stay clean.',
        'intermediate',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #f4f4f4 or a team colour.',
         'Add big colour blocks: ' + S_BOX + ' Roof and hood in a strong accent (for example #0a3fd0), Gloss.',
         'Add mud: draw a box along the lower third, open BASE > SPEC OVERLAYS > + ADD SPEC OVERLAY, choose Dried Mud Crackle or Red Clay Roost, Strength 45.',
         'Keep the number panels clean and high contrast. ' + S_RENDER],
        [X('White and blue with clay roost', 'Classic gravel stage', {'Body': 'Gloss, #f4f4f4', 'Roof and hood': 'Gloss, #0a3fd0', 'Lower third': 'SPEC OVERLAY Red Clay Roost, Strength 45'}, 'Clean upper car with dusty lower panels.', 'cat_tactical_field'),
         X('Dark mud-spattered', 'Wet stage', {'Body': 'Satin, #2a3a2a', 'Lower': 'Dried Mud Crackle, Strength 50'}, 'Green satin car with cracked mud on the sills.', 'spec_wear')],
        [D('Mud is spec', 'The overlays change roughness and coat on the lower body; the paint colour stays readable.'), D('Big blocks', 'Few colours, large areas, so the car reads at stage speed.')],
        [Q('How do I make a rally car?', 'Bold blocks, big numbers and a muddy lower third.'), Q('Which overlay?', 'Dried Mud Crackle or Red Clay Roost.'), Q('Does it work on gloss?', 'Yes.')],
        [M('Mud too strong', 'Overlay strength high', 'Lower to 30 to 45.'), M('Numbers dirty', 'Mud over the door centre', 'Keep it in a low box.')],
        ['Keep the roof number crisp; it is read from above.'],
        ['rally car', 'rally style', 'rally livery', 'wrc look', 'gravel look', 'mud splash', 'dirty rally car', 'stage rally', 'dirt road look', 'offroad livery', 'safari look'],
        fin=['base::gloss', 'base::satin'], spc=['spec_mud_crackle_dried', 'spec_red_clay_roost'],
        related=['ideas.worn_patina', 'ideas.readable_on_tv', 'ideas.team_colours'], combos=[('ideas.readable_on_tv', 'Numbers must stay clean.')],
        screens=['cat_tactical_field', 'spec_wear'], extra_src=[READ])

if todo('le_mans_endurance'):
    art('le_mans_endurance', 'Le Mans and endurance: clean flanks, swooshes and a loud roof number',
        'Endurance cars are a clean metallic or white body, one sweeping colour swoosh down the flank, carbon splitter details, and a high-contrast roof and door number.',
        'Prototype and GT racers must be read by teams, timing and spotters at night and at speed. Use one bold swoosh, clear class colours, carbon trim and a huge roof number on a plain panel.',
        'intermediate',
        [S_ZONE, S_BASE % 'Metallic (metal 200, roughness 50, coat 16)' + ' with Use solid color #c9ccd1 (silver) or white.',
         'Swoosh: ' + S_BOX + ' Draw a long diagonal box along the flank, Gloss with your team colour, or set BASE COLOR to Custom gradient for a fade.',
         'Carbon details: a zone on splitter and diffuser with PATTERN Carbon Fiber, Paint mode Blend, Scale (pattern) 0.5.',
         'Roof number panel: a flat white or yellow box with a black number. ' + S_RENDER],
        [X('Silver with blue swoosh', 'Prototype', {'Body': 'Metallic, #c9ccd1', 'Swoosh': 'Draw box diagonal, Gloss, #0a3fd0', 'Splitter': 'PATTERN Carbon Fiber, Blend, Scale (pattern) 0.5'}, 'Silver car with a blue flank and carbon front.', 'cat_materials_physics'),
         X('White GT with class roof', 'Readable GT', {'Body': 'Gloss, #f4f4f4', 'Roof zone': 'Draw box, Gloss, #ffd400', 'Number': 'Black on yellow'}, 'A yellow roof panel visible from the air.', 'cat_signal')],
        [D('Endurance needs identity', 'Teams recognise the car at night by one colour and one shape. Keep it simple.'), D('Carbon is trim', 'Carbon on splitter and diffuser looks purposeful; carbon everywhere looks busy.')],
        [Q('What makes it endurance?', 'Clean body, one swoosh, loud roof number.'), Q('Gradient swoosh?', 'Custom gradient in BASE COLOR.'), Q('Do I need carbon?', 'Optional trim.')],
        [M('Swoosh does not match both sides', 'Drawn once', 'Copy the zone and mirror it.'), M('Number lost', 'Busy roof', 'Plain panel.')],
        ['Pick one class colour and use it for roof, mirrors and splitter edge.'],
        ['le mans', 'le mans style', 'endurance livery', 'endurance racing', 'prototype look', 'gt racing look', 'gt3 livery', 'daytona style', 'imsa look', 'wec livery', 'sports car livery', 'night endurance'],
        fin=['base::f_metallic', 'base::gloss'], pat=['carbon_fiber', 'chevron'],
        related=['ideas.gulf_style', 'ideas.carbon_race_bare', 'ideas.readable_on_tv', 'ideas.team_colours'], combos=[('ideas.gulf_style', 'The classic endurance colours.')],
        screens=['cat_materials_physics', 'cat_signal'], extra_src=[READ, FAM])

if todo('touring_car'):
    art('touring_car', 'Touring car: a bold diagonal and big sponsor panels',
        'Touring-car liveries are a strong block colour with one sharp diagonal cut and large clean panels that carry sponsors. Gloss body, high contrast.',
        'Touring cars race door-to-door, so the livery is graphic and flat: a dominant colour, a diagonal slash in the second colour and a quiet area for logos. Use sharp edges and no fine texture.',
        'beginner',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #c8102e (or your team colour).',
         'Draw a diagonal slash: ' + S_BOX + ' Use a tall box and rotate with the pattern Chevron if you want a notched edge.',
         'Give the slash a contrasting colour, #0b0b0e or #f4f4f4, Gloss.',
         'Leave the doors for sponsors. ' + S_RENDER],
        [X('Red with black slash', 'Classic block livery', {'Body': 'Gloss, #c8102e', 'Slash zone': 'Draw box, Gloss, #0b0b0e', 'Doors': 'Kept clean'}, 'Red car with a hard black diagonal.', 'cat_color_clash'),
         X('White with blue chevron', 'Notched edge', {'Body': 'Gloss, #f4f4f4', 'Chevron zone': 'PATTERN Chevron, Overlay, Scale (pattern) 0.8, colour via Hue'}, 'Notched arrow shapes pointing forward.', 'cat_signal')],
        [D('Flat beats fancy', 'Big flat shapes read on TV; fine texture does not.'), D('Sponsor room', 'Leave rectangular quiet areas for logos on door and bonnet.')],
        [Q('How do I make a touring car?', 'Block colour and a diagonal.'), Q('Sponsor panels?', 'Keep doors plain.'), Q('Chevron?', 'Use the Chevron pattern.')],
        [M('Too many colours', 'Three accents', 'One accent.'), M('Slash cuts the number', 'Box over the door', 'Move it forward.')],
        ['A hard diagonal in a contrasting value is the whole idea.'],
        ['touring car', 'touring car livery', 'btcc look', 'btcc style', 'saloon racer', 'sedan racing livery', 'block colour livery', 'diagonal livery', 'sponsor livery', 'club racer'],
        fin=['base::gloss'], pat=['chevron'],
        related=['ideas.oval_stock_car', 'ideas.two_tone', 'ideas.sponsor_friendly_bases'], combos=[('ideas.sponsor_friendly_bases', 'Plain areas for logos.')],
        screens=['cat_color_clash', 'cat_signal'], extra_src=[READ])

if todo('oval_stock_car'):
    art('oval_stock_car', 'Oval stock car: giant number, bright top, dark bottom',
        'A stock car is one bold colour, a strong top-versus-bottom split, a giant number and plain panels for sponsors. Simple, loud and readable.',
        'Oval racing is watched from far away and from the stands, so the livery is built for readability: bright upper body, darker lower body, a huge number and no fine detail.',
        'beginner',
        [S_ZONE, S_BASE % 'Gloss (metal 0, roughness 30, coat 16)' + ' with Use solid color #ffd400 (yellow) or another bright team colour.',
         'Darken the lower body: ' + S_BOX + ' Draw a band along the lower third, Gloss with #14284b.',
         'Add a thin separation line: a thin box between the two in white #f4f4f4.',
         'Keep numbers huge, with an outline: white on dark or black on bright. ' + S_RENDER],
        [X('Yellow over navy', 'Classic stock car', {'Body': 'Gloss, #ffd400', 'Lower band': 'Gloss, #14284b', 'Line': 'Gloss, #f4f4f4, thin box'}, 'Bright top, dark bottom, white pinline.', 'cat_signal'),
         X('Red over black', 'Aggressive', {'Body': 'Gloss, #c8102e', 'Lower band': 'Gloss, #0b0b0e'}, 'Red top with a black skirt.', 'cat_color_clash')],
        [D('Top and bottom', 'The split gives the car a clear horizon at a distance.'), D('Large number', 'The number should fill the door; an outline makes it read on any ground.')],
        [Q('How do I do a stock car?', 'Bright top, dark bottom, huge number.'), Q('Where do sponsors go?', 'Hood and quarter panels on plain colour.'), Q('Gloss?', 'Yes.')],
        [M('Number lost', 'Mid-tone on mid-tone', 'Strong contrast.'), M('Looks busy', 'Too many logos', 'Plain panels.')],
        ['A white pinline between the two colours is the stock-car polish.'],
        ['stock car', 'nascar style', 'oval racer', 'oval track livery', 'late model look', 'dirt oval look', 'big number livery', 'bright top dark bottom'],
        fin=['base::gloss'],
        related=['ideas.touring_car', 'ideas.sponsor_friendly_bases', 'ideas.readable_on_tv'], combos=[('ideas.readable_on_tv', 'Contrast rules.')],
        screens=['cat_signal', 'cat_foundation'], extra_src=[READ])

if todo('black_gold_luxury'):
    art('black_gold_luxury', 'Black and gold luxury: near-black body, gold hairlines',
        'A near-black satin or matte body with gold metal accents and white numbers. The gold is a metal finish on a thin area; the black stays calm.',
        'Black and gold is the classic luxury pairing. Keep the body dark and soft, make the gold metallic and thin (hairlines, wheel arches, a stripe), and let the number be white or gold.',
        'beginner',
        [S_ZONE, S_BASE % 'Satin (metal 0, roughness 95, coat 70)' + ' with Use solid color #0d0d10.',
         'Add gold lines: ' + S_BOX + ' thin boxes along the beltline and rocker. Choose Satin Chrome (metal 250, roughness 45, coat 40) with Use solid color #d4a017.',
         'Optional: BASE > SPEC OVERLAYS > + ADD SPEC OVERLAY, Gold Flake at Strength 30 on the body for a glittering depth.',
         'Numbers white or gold. ' + S_RENDER],
        [X('Satin black with gold line', 'Premium dark', {'Body': 'Satin, #0d0d10', 'Line': 'Satin Chrome, Use solid color #d4a017, thin box'}, 'A black car with a gold hairline.', 'spec_matte'),
         X('Ready-made brass', 'From the catalogue', {'Base Material': 'Brass Night (search it)', 'BASE COLOR': "Use finish's own color"}, 'A darkened brass finish with warm metal.', 'cat_money_shokk'),
         X('Black-gold colour shift', 'Subtle shift', {'Base Material': 'Cs Black Gold (search it)'}, 'Black that warms to gold at an angle.')],
        [D('Gold is metal', 'Satin Chrome with a gold colour gives a gold that behaves like metal, not yellow paint.'), D('The palette', 'A shipped palette uses near-black #0d0d10, gold #d4a017 and white numbers.')],
        [Q('How do I make black and gold?', 'Satin black body, thin gold metal lines.'), Q('Gloss or satin?', 'Satin for the body.'), Q('Gold wheels?', 'Wheels are not painted here.')],
        [M('Gold looks yellow', 'Gloss gold', 'Use Satin Chrome with a gold colour.'), M('Too heavy', 'Wide gold areas', 'Keep to hairlines.')],
        ['Money Shokk finishes (vault and mint themes) bring ready-made luxury.'],
        ['black and gold', 'gold and black', 'jps style', 'luxury black gold', 'gold livery', 'gold accents', 'black gold look', 'bling look', 'gold trim', 'gold on black'],
        fin=['base::satin', 'base::f_satin_chrome', 'monolithic::dkc_brass_night', 'monolithic::cs_black_gold', 'monolithic::msk_bullion_stack'], spc=['gold_flake'],
        related=['ideas.look_expensive', 'ideas.clean_classy', 'ideas.monochrome'], combos=[('ideas.look_expensive', 'Same family.')],
        screens=['cat_money_shokk', 'spec_matte'], extra_src=[PRO_DOC if False else doc(DOC_DESIGN, 'Palettes that work')])

if todo('racing_stripes'):
    art('racing_stripes', 'Racing stripes: width, gap, colour and where to stop',
        'Racing stripes are long parallel bands over the hood, roof and trunk. Build each stripe as a thin box zone, keep widths and gaps equal, and mirror them so both sides match.',
        'Stripes are the simplest graphic on a car and the easiest to get wrong. The rules are straight lines, equal gaps, a clean start and stop, and a contrasting finish so the stripe reads in the sim.',
        'beginner',
        [S_ZONE, 'Make the body first (any base). Then add a new zone per stripe: ' + S_BOX,
         'Draw each stripe as a long thin rectangle along the hood, roof and trunk. Use Gloss for the stripe colour; use Matte stripes on a gloss body for the classic contrast.',
         'Order the zones: stripes above the body zone so they win.',
         'Use the zone copy icon to duplicate a stripe, then move the box. Check the side panels are mirrored. ' + S_RENDER],
        [X('Twin hood stripes', 'Muscle layout', {'Body': 'Gloss, #e8631a', 'Stripe 1 and 2': 'Draw box over hood, roof, trunk, Matte, #0b0b0e', 'Gap': 'Equal to stripe width'}, 'Two black stripes on orange.', 'cat_bad_rad'),
         X('Pinstripe hairline', 'Fine line', {'PATTERN': 'Pinstripe, Blend, Scale (pattern) 0.4', 'Zone': 'Draw box along the beltline'}, 'A fine lengthwise line.', 'cat_foundation')],
        [D('Order matters', 'A zone higher in the list wins where two zones select the same pixels.'), D('Match across seams', 'The car is unwrapped; check that the stripe on the door lines up with the one on the fender on the CAR view.')],
        [Q('How do I add racing stripes?', 'One thin box zone per stripe.'), Q('Matte or gloss stripe?', 'Matte on gloss pops.'), Q('How do I match both sides?', 'Copy the zone and mirror the box.')],
        [M('Stripe hidden', 'A zone above it covers it', 'Drag it up.'), M('Stripe crooked', 'Box slightly rotated', 'Redraw.')],
        ['Stripe width about a third of the car width for muscle, a tenth for European.'],
        ['racing stripes', 'add racing stripes', 'hood stripes', 'center stripe', 'twin stripes hood', 'stripe over roof', 'le mans stripes', 'dual stripes', 'rally stripes', 'stripes on car', 'sport stripes'],
        fin=['base::gloss', 'base::matte'], pat=['pinstripe'],
        related=['recipes.retro_stripes', 'ideas.martini_style', 'ideas.old_school_muscle', 'ideas.look_fast'], combos=[('recipes.retro_stripes', 'Stripes with numbers.')],
        screens=['ui_zone_apply_area', 'cat_foundation'], quick=True, extra_src=[FAM, WHERE])

if todo('checkered_flag'):
    art('checkered_flag', 'Checkered flag: finish-line checks, solid or hidden in the shine',
        'Checks can be painted (a checker pattern band), printed as a finish, or hidden in the spec so they only show in the sun. Keep them to a band or the roof.',
        'Chequers say race. You can paint them as a visible band, use the Diner Checkerboard finish, or add the Checker Flag Subtle spec overlay so a checker appears only in reflections.',
        'beginner',
        [S_ZONE, 'Choose a gloss or satin body.',
         'Visible band: ' + S_BOX + ' Open PATTERN, choose Diner Checkerboard, Paint mode Overlay, Scale (pattern) 0.6, on the rocker or roof.',
         'Hidden checks: open BASE > SPEC OVERLAYS > + ADD SPEC OVERLAY and choose Checker Flag Subtle, Strength 40.',
         S_RENDER],
        [X('Checker rocker', 'Visible band', {'Body': 'Gloss, #c8102e', 'Band zone': 'Draw box on the rocker, PATTERN Diner Checkerboard, Overlay, Scale (pattern) 0.6'}, 'A black and white band along the sill.', 'cat_sock_hop'),
         X('Hidden checks', 'Checks only in the sun', {'Body': 'Gloss, #0b0b0e', 'SPEC OVERLAY': 'Checker Flag Subtle, Strength 40'}, 'A black car with a checker that appears in reflections.', 'spec_ghost_hex')],
        [D('Overlay mode', 'Overlay lets the checker paint its own black and white.'), D('Spec-only', 'The spec overlay changes shine, not colour.')],
        [Q('How do I add a checkered flag?', 'Checker pattern in a band, or the subtle spec overlay.'), Q('Hidden?', 'Checker Flag Subtle.'), Q('Scale?', 'About 0.6.')],
        [M('Checks too big', 'Scale 1.0', 'Lower to 0.6.'), M('Checks over the number', 'Large box', 'Band only.')],
        ['Black and white on a red body is the strongest read.'],
        ['checkered flag', 'checkered', 'chequered flag', 'checker pattern', 'checker band', 'checkerboard stripe', 'finish line look', 'race flag', 'checks on roof', 'checker roof'],
        fin=['base::gloss', 'base::diner_checker'], pat=['decade_50s_diner_checkerboard', 'checker_warp'], spc=['checker_flag_subtle'],
        related=['ideas.vintage_diner_50s', 'ideas.racing_stripes', 'ideas.geometric'], combos=[('ideas.vintage_diner_50s', 'Diner checkers.')],
        screens=['cat_sock_hop', 'spec_ghost_hex'], extra_src=[FAM])

if todo('speed_lines_motion'):
    art('speed_lines_motion', 'Speed lines and motion graphics: streaks, zigzags and bolts',
        'Motion graphics are streaks, zigzags and bolts that run front to back: patterns at fine Scale, plus Anime Speed-Line Storm or Tunnel Vision for ready-made versions.',
        'To show motion without blur, run lines lengthwise, fade them toward the rear and keep the pattern fine. Streaks, chevrons and bolts do this; round shapes do not.',
        'intermediate',
        [S_ZONE, 'Body: any dark gloss or satin base.',
         S_BOX + ' Over the front half of each side, open PATTERN and choose Zigzag Bands, Rollerblade Streak or Lightning, Paint mode Blend, Scale (pattern) 0.5, Rotation so lines run front to back.',
         'Ready-made: pick Anime Speed-Line Storm or Tunnel Vision in Base Material on a box over the flanks.',
         S_RENDER],
        [X('Streak flanks', 'Lines along the side', {'Body': 'Satin, #101216', 'PATTERN': 'Rollerblade Streak, Blend, Scale (pattern) 0.5', 'Zone': 'Front half of each side'}, 'Streaks that fade toward the rear.', 'cat_signal'),
         X('Tunnel Vision', 'Yellow and cyan wedges', {'Base Material': 'Tunnel Vision', 'BASE COLOR': "Use finish's own color"}, 'Vanishing tunnel lights stretched into speed wedges.', 'cat_neon_underground')],
        [D('Direction', 'Lines should run in the direction of travel on both sides.'), D('Fine scale', 'Scale (pattern) 0.5 gives streaks; 1.0 gives stickers.')],
        [Q('How do I add speed lines?', 'Fine streak pattern on the front half.'), Q('Which finishes?', 'Anime Speed-Line Storm, Tunnel Vision.'), Q('Blur?', 'No real blur; streaks are the honest version.')],
        [M('Lines point the wrong way', 'Rotation unset', 'Rotate the pattern.'), M('Looks like stickers', 'Scale too big', 'Lower scale.')],
        ['Fade lines out at the rear by ending the box mid-door.'],
        ['speed lines', 'motion lines', 'motion graphics', 'streaks', 'speed streaks', 'zigzag graphics', 'lightning bolt look', 'manga speed lines', 'swoosh graphics', 'racing graphics fast'],
        fin=['base::satin', 'base::anime_speed_lines', 'base::neon_cyber_yellow'], pat=['zigzag_bands', 'decade_90s_rollerblade_streak', 'lightning'],
        related=['ideas.look_fast', 'ideas.racing_stripes', 'ideas.japanese_art'], combos=[('ideas.look_fast', 'The strategy behind it.')],
        screens=['cat_signal', 'pair_base_scale'], extra_src=[THEMES])
