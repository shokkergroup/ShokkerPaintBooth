# -*- coding: utf-8 -*-
"""enc_ideas_fix_r4.py - ROUND 4 fact-check patch for data/encyclopedia/ideas.json (2026-10-05). Idempotent: re-apply after enc_ideas_build.py.
Each entry (article, path, old, new, claim, truth, source); old="*" replaces the whole value. Run: python scripts/ai_atlas/enc_ideas_fix_r4.py"""
import json, os, re, sys
F = []
def f(*a): F.append(a)
CARD = "deep render card (_dumpB.json)"
PIN = CARD + " pattern::pinstripe"
# make_it_pop
f('make_it_pop','how[3]',"so it wins where they meet.","so it wins where they meet. A new zone is added at the BOTTOM of the list and the higher zone wins, so the hero zone has to be dragged up.",
  "hero zone wins by being above the matte zone, without saying where a new zone lands","+ Add Zone appends to the bottom; higher in the list (lower index) wins","ui_map zone list + ENC_FACTCHECK R1-3")
# aggressive_mean : chevron stack
f('aggressive_mean','how[2]',"choose Chevron Stack or Razor Wire, set Paint mode to Blend and Scale (pattern) to 0.5 so the points read fine across the whole car.",
  "choose Chevron (tidy zigzag Vs) or Razor Wire (wavy barbed-wire strands), set Paint mode to Blend and Scale (pattern) to 0.5 so the lines read fine across the whole car.",
  "Chevron Stack gives sharp points","Chevron Stack renders as fine horizontal pinstripes; the chevrons vanish. Chevron renders as tidy repeating Vs",CARD+' pattern::chevron_stack, pattern::chevron')
f('aggressive_mean','examples[0].settings.PATTERN',"Chevron Stack","Chevron","same","same",CARD)
f('aggressive_mean','examples[1].result',"fine sharp lines","fine wavy barbed-wire lines","Razor Wire = sharp lines","Razor Wire renders as wavy wire strands, barbs vanish",CARD+' pattern::razor_wire')
# look_expensive
f('look_expensive','examples[0].result',"Dark red glass with a gold shimmer when the sun hits.","Dark red glass with a faint sandy shimmer in the highlights (Gold Flake changes shine only, no gold colour appears).",
  "Gold Flake overlay gives a gold shimmer","Gold Flake spec overlay renders as a smooth sheen with a slight sandy shimmer; nothing looks gold",CARD+' spec gold_flake')
f('look_expensive','examples[0].title',"Oxblood candy with gold flake","Oxblood candy with a flake overlay","same","same",CARD)
f('look_expensive','protips[1]',"premium surfaces show smooth dark greens, not noisy ones.","premium surfaces show smooth, even dark areas, not noisy ones.",
  "G ROUGH view shows 'dark greens'","The channel preview is a greyscale-style channel view; no green is promised","ui_audit R METAL/G ROUGH/B COAT labels")
# look_fast
f('look_fast','how[2]',"choose Chevron, Lightning or Pinstripe, set Paint mode to Blend, Rotation so the lines run front to back,","choose Chevron or Pinstripe, set Paint mode to Blend, Rotate (pattern) so the lines run front to back,",
  "Lightning pattern gives speed bolts; control called Rotation","Lightning renders as hairline scratches (nothing readable as lightning); the control is Rotate (pattern)",CARD+' pattern::lightning; ui_map pattern controls')
f('look_fast','examples[0].goal',"Arrow the car forward","Lead the eye forward","same","same",CARD)
f('look_fast','examples[0].result',"Arrow shapes that point at the nose and a dark rocker.","Tidy zigzag V rows along the front half and a dark rocker.",
  "Chevron makes arrow shapes pointing at the nose","Chevron renders as horizontal zigzag rows of Vs, not big arrows",CARD+' pattern::chevron')
f('look_fast','examples[1].result',"Fine lengthwise lines that stretch the car.","Fine stripe lines; use Rotate (pattern) until they run lengthwise, and judge on the CAR view because the thumbnail reads busier than one crisp line.",
  "Pinstripe = fine lengthwise lines","Pinstripe card renders as a busy upright streak texture; direction depends on Rotate (pattern)",CARD+' pattern::pinstripe')
f('look_fast','examples[2].title',"Lightning on the sides","Chevron bands on the doors","Lightning example","Lightning pattern is hairline scratches",CARD)
f('look_fast','examples[2].settings.PATTERN',"Lightning, Paint mode Blend, Scale (pattern) 0.4","Chevron, Paint mode Blend, Scale (pattern) 0.4","same","same",CARD)
f('look_fast','examples[2].result',"Bolts that streak toward the rear on a deep blue candy.","Fine zigzag rows on the doors of a deep blue candy.","same","same",CARD)
f('look_fast','protips[1]',"the left and right panels are mirrored on the flat sheet.","check both sides on the CAR view; the left and right panels can run opposite ways on the flat sheet.",
  "panels are mirrored on the flat sheet","Unverified claim; direction must be checked on the CAR view","ENC_FACTCHECK R2 (CAR view check)")
# stealth: none. look_wet none.

# worn_patina
f('worn_patina','summary',"roughness up, coat down, colour faded","roughness up, coat value up (the clearcoat wears off), colour faded","'coat down' for wear","B coat: 16 = max gloss, higher = duller; worn paint has a HIGHER coat value (Sun Faded 137)","MEMORY spec map; base_registry efx_sun_faded")
f('worn_patina','deep[0].body',"push roughness up and coat down:","push roughness up and the coat value up (B 16 is glossiest, so wear is a bigger number):","same","same","spec map")
f('worn_patina','examples[1].result',"Orange bloom and dark scabs on the lowest panels.","Freckled orange rust spots on the lowest panels, with a dusty sheen from the overlay.","Surface Rust = orange bloom and dark scabs","Surface Rust renders as a polka-dot spread of orange rust spots",CARD+' base::efx_surface_rust')
# retro_70s
f('retro_70s','deep[1].body',"Soft Gloss (roughness 30)","Gloss (roughness 30)","'Soft Gloss' foundation","No Soft Gloss in the picker; Gloss is roughness 30","picker VIS / enc_ideas find")
f('retro_70s','how[3]',"choose Earth Tone Geo or Funk Zigzag, Paint mode Blend","choose Earth Tone Geo (a busy olive-and-pink plaid shimmer) or Funk Zigzag (orange-brown plaid with pale wavy lines), Paint mode Blend","pattern looks","both render as busy plaid, not clean zigzag shapes",CARD+' decade_70s_*')
f('retro_70s','examples[1].result',"Mustard car with a zigzag skirt.","Mustard car with a warm orange-brown plaid skirt.","zigzag skirt","Funk Zigzag reads as orange-brown plaid with wavy lines",CARD)
# retro_60s
f('retro_60s','how[2]',"Open PATTERN and choose Mod Color Block, Paint mode Overlay (so it paints its own colours), Scale (pattern) 0.7.","For clean blocks give each box its own flat Gloss colour (navy, white, orange). For a mosaic instead, open PATTERN and choose Mod Color Block, Paint mode Overlay (so it paints its own colours), Scale (pattern) 0.7; it renders as a busy tile mosaic.","Mod Color Block = Mondrian-style blocks","Mod Color Block (decade_60s_gogo_check) renders as a busy multi-colour pixel/tile mosaic",CARD+' decade_60s_gogo_check')
f('retro_60s','examples[0].result',"Light blue car with a Mondrian-style band.","Light blue car with a busy multi-colour tile-mosaic band (use plain flat boxes for clean Mondrian blocks).","same","same",CARD)
f('retro_60s','how[3]',"pick 60s Sunburst or Flower Power in Base Material on the hood only.","pick 60s Sunburst (a dark red-brown with orange-gold dots) or Flower Power (a dark teal-blue ditsy print) in Base Material on the hood only.","Sunburst = radiating rainbow","60s Sunburst renders as dark red-brown with a polka dot of orange-gold; the rays vanish",CARD+' base::sunburst_60s, base::flower_power')
f('retro_60s','examples[1].result',"White car with a radiating rainbow bonnet.","White car with a dark red-brown bonnet printed with orange-gold dots.","same","same",CARD)
# retro_80s
f('retro_80s','how[3]',"Add a grid: PATTERN Neon Grid,","Add a grid-like shimmer: PATTERN Neon Grid (renders as a fine multi-colour plaid shimmer, not crisp lines),","Neon Grid = a grid","renders as fine plaid / graph-paper shimmer, lines merge into neon static",CARD+' decade_80s_neon_grid')
f('retro_80s','examples[0].result',"Dark car with neon geometry.","Dark car with pink and cyan blocks and a fine neon plaid shimmer on the lower body.","same","same",CARD)
# retro_90s
f('retro_90s','how[2]',"Add PATTERN Rave Zigzag or Geo Minimal,","Add PATTERN Rave Zigzag (bright neon chevron bands) or Geo Minimal (a fine scatter of bright confetti dots),","Geo Minimal = minimal shapes","Geo Minimal renders as dense tiny confetti dots; shapes vanish",CARD+' decade_90s_geo_minimal')
# vintage diner
f('vintage_diner_50s','examples[1].title',"Black and white checker band","Red and cream check band","black and white check","Diner Checkerboard finish renders as red-and-cream gingham",CARD+' base::diner_checker')
f('vintage_diner_50s','examples[1].result',"Checkered lower band on a cherry red body.","A red-and-cream gingham-style check band on a cherry red body.","same","same",CARD)
# candy_lowrider
f('candy_lowrider','examples[0].result',"Deep red with gold sparkle.","Deep red candy with a faint sandy shimmer (the overlay is shine only; Chunky Metalflake is the finish that shows chips).","Gold Flake gives gold sparkle","Gold Flake spec overlay: smooth sheen, slight sandy shimmer, nothing looks gold",CARD+' spec gold_flake')
f('candy_lowrider','how[3]',"choose Gold Flake, Strength 40.","choose Gold Flake, Strength 40 (a faint sandy shimmer, shine only).","same","same",CARD)
f('candy_lowrider','how[4]',"or Gothic Scroll or Fleur-de-Lis on the hood panel, Paint mode Blend.","or Fleur-de-Lis (bold lily shapes) on the hood panel, Paint mode Blend; Gothic Scroll renders as a plum panel with a colourful scribble, so skip it.","Gothic Scroll gives scrolled hood panel","no scrolls survive in the Gothic Scroll render",CARD+' gothic_scroll, fleur_de_lis')
f('candy_lowrider','examples[1].settings.Hood zone',"PATTERN Gothic Scroll","PATTERN Fleur-de-Lis","same","same",CARD)
f('candy_lowrider','examples[1].title',"Blue flake scroll hood","Blue flake lily hood","same","same",CARD)
f('candy_lowrider','examples[1].result',"Heavy flake with a scrolled hood panel.","Heavy flake with bold lily shapes on the hood panel.","same","same",CARD)
f('candy_lowrider','examples[1].settings.Pinstripe',"PATTERN Pinstripe on the doors","PATTERN Pinstripe on the doors (judge direction on the CAR view; use Rotate (pattern))","Pinstripe is a crisp line","renders as a busy upright streak texture",CARD+' pattern::pinstripe')
# rat_rod pinstripe, hot_rod, gulf, racing_stripes pinstripe notes
f('rat_rod','how[4]',"or Pinstripe pattern.","or the Pinstripe pattern (a fine streaky stripe texture; set Rotate (pattern) to taste).","Pinstripe = a clean line","renders as a flickery streak texture",CARD+' pattern::pinstripe')
f('hot_rod_kustom','how[3]',"Pinstripes: a zone with PATTERN Pinstripe, Paint mode Blend, Scale (pattern) 0.4 around the flame edge.","Pinstripes: a thin zone with PATTERN Pinstripe, Paint mode Blend, Scale (pattern) 0.4 around the flame edge; it is a fine streaky stripe texture, so check it on the CAR view.","Pinstripe = hand-lettered thin lines","renders as a flickery streak texture",CARD+' pattern::pinstripe')
f('hot_rod_kustom','deep[1].body',"Pinstripe scale 0.4 gives thin lines that look hand-lettered.","Pinstripe at Scale (pattern) 0.4 gives fine stripes; for a truly hand-lettered line use a thin Draw box in a contrasting Gloss colour.","same","same",CARD)
f('hot_rod_kustom','examples[0].result',"Orange and yellow flames on black.","A glowing red-orange-yellow ember field on the hood and fender over black; it reads as heat shimmer more than distinct licks.","Hot Rod Flames = licks","reads as heat shimmer or blazing embers over the whole panel",CARD+' base::flame_hotrod')
f('hot_rod_kustom','examples[1].title',"Cherry candy with scallops","Cherry candy with chrome trim","title mentions scallops not in settings","settings have no scallops","self-consistency")

# gulf / racing stripes leftovers
f('gulf_style', 'how[3]', "(or PATTERN Pinstripe)", "(or PATTERN Pinstripe, a fine streaky stripe texture)",
  "Pinstripe = a thin line", "renders as flickery streaks", PIN)
f('racing_stripes', 'examples[1].result', "A fine lengthwise line.",
  "A fine stripe texture; set Rotate (pattern) so it runs lengthwise (the thumbnail reads busier than one crisp line; a thin Draw box in a flat colour gives a true hairline).",
  "Pinstripe = fine lengthwise line", "renders as a busy upright streak texture", PIN)
f('racing_stripes', 'how[3]', "Order the zones: stripes above the body zone so they win.",
  "Order the zones: a new zone is added at the BOTTOM of the list and the higher zone wins, so drag each stripe above the body zone.",
  "stripes above body zone, without saying new zones start at the bottom", "+ Add Zone appends to the bottom; higher in the list wins", "ui_map zone list + ENC_FACTCHECK R1-3")
# martini: pinstripe pattern not used. jdm
f('jdm', 'how[3]', "choose Seigaiha Scales or Japanese Wave, Paint mode Blend",
  "choose Seigaiha Scales (a fine blue-green rippled texture, low contrast) or Japanese Wave (a busier fish-scale mesh with coloured flecks), Paint mode Blend",
  "wave motifs read as clear waves", "Seigaiha = soft corrugated ripple; Japanese Wave = scaly mesh with flecks", CARD + ' seigaiha_scales, japanese_wave')
f('jdm', 'examples[1].result', "Razor-vinyl slashes with prismatic edges on a flat dark body.",
  "Loud pink, purple and blue crossing slash ribbons on black.",
  "Import Royalty = razor-vinyl slashes with prismatic edges", "renders as loud neon pink/purple/blue crossing ribbons on black", CARD + ' base::neon_pink_blaze')
f('jdm', 'examples[2].result', "A lacquer texture with a warm Japanese-inspired palette.",
  "A dark red-maroon lacquer with a bright orange sun in the middle and golden rays.",
  "Rising Sun Flare vague lacquer texture", "renders as dark red-maroon with an orange sun and golden rays (a picture finish)", CARD + ' monolithic::rs_rising_sun_flare')
# drift_car (spec overlays show no soot colour)
f('drift_car', 'how[2]', "choose Exhaust Soot Gradient, Strength 40.",
  "choose Exhaust Soot Gradient, Strength 40. The overlay is shine only (no black soot colour appears), so add a dull dark-grey Matte colour in the same box if you want visible soot.",
  "Exhaust Soot Gradient adds soot", "renders as nothing at distance, at most a watery shimmer; it changes shine only", CARD + ' spec_exhaust_soot_gradient')
f('drift_car', 'examples[0].result', "Dark car with sooty edges and a cyan streak.",
  "Dark car with a cyan streak and a subtle shine change on the rocker (add a dull dark-grey Matte box for visible soot).",
  "sooty edges from the spec overlay", "spec overlay is shine only", CARD)
f('drift_car', 'protips[0]', "Burnt Clutch Dust is another subtle spec overlay for heat marks.",
  "Burnt Clutch Dust is another subtle spec overlay (a light glittery dust in the shine, not a visible heat mark).",
  "heat marks", "renders as a clean sheen with light glittery dust", CARD + ' spec_burnt_clutch_dust')
# rally
f('rally', 'how[3]', "choose Dried Mud Crackle or Red Clay Roost, Strength 45.",
  "choose Dried Mud Crackle or Red Clay Roost, Strength 45. These are shine only (no brown mud appears), so add a dull brown Matte box (for example #6b5238) over the lower third for visible mud.",
  "Red Clay Roost / Dried Mud Crackle give dusty mud", "both render as plain base finish; no red or brown appears, shine only", CARD + ' spec_mud_crackle_dried, spec_red_clay_roost')
f('rally', 'examples[0].result', "Clean upper car with dusty lower panels.",
  "Clean upper car; the lower third only changes shine unless you add a brown Matte box.",
  "dusty lower panels from overlay", "overlay is shine only", CARD)
f('rally', 'examples[1].result', "Green satin car with cracked mud on the sills.",
  "Green satin car; the sills carry only a faint mottled shine unless you add a dull brown box.",
  "cracked mud visible", "Dried Mud Crackle is gone at distance, a trace of mottling", CARD)
# touring
f('touring_car', 'how[2]', "Use a tall box and rotate with the pattern Chevron if you want a notched edge.",
  "For a notched edge, add a PATTERN Chevron (tidy zigzag Vs) in a second box beside the slash.",
  "a box can be rotated with the Chevron pattern", "a Draw box has no rotation; Chevron is a pattern with its own Rotate (pattern)", "ui_map zone/pattern controls")
f('touring_car', 'examples[1].title', "White with blue chevron", "White with blue chevron rows", "same", "same", CARD)
f('touring_car', 'examples[1].result', "Notched arrow shapes pointing forward.",
  "Fine blue zigzag rows across the panel (Chevron paints repeating Vs, not one big arrow).",
  "Chevron = notched arrows pointing forward", "renders as horizontal zigzag rows of Vs", CARD + ' pattern::chevron')
# speed_lines_motion
f('speed_lines_motion', 'summary', "Motion graphics are streaks, zigzags and bolts that run front to back",
  "Motion graphics are streaks and zigzags that run front to back", "bolts", "Lightning pattern renders as hairline scratches", CARD + ' pattern::lightning')
f('speed_lines_motion', 'how[2]', "choose Zigzag Bands, Rollerblade Streak or Lightning, Paint mode Blend, Scale (pattern) 0.5, Rotation so lines run front to back.",
  "choose Rollerblade Streak (pastel zigzag bands and dots) or Chevron (tidy zigzag Vs), Paint mode Blend, Scale (pattern) 0.5, and Rotate (pattern) so lines run front to back.",
  "Zigzag Bands / Lightning make speed streaks; control called Rotation", "Zigzag Bands = brown/cream stepped basket bands; Lightning = hairline scratches; control is Rotate (pattern)", CARD + ' zigzag_bands, lightning')
f('speed_lines_motion', 'examples[0].result', "Streaks that fade toward the rear.",
  "Bright pastel zigzag bands and dots on the front half of each side of a dark car.",
  "Rollerblade Streak = streaks fading to the rear", "renders as 90s Memphis zigzag bands and dots", CARD + ' decade_90s_rollerblade_streak')
# high_vis
f('high_vis', 'how[2]', "For orange you can pick Blaze Orange in Base Material instead.",
  "For orange use Gloss with #ff6a00. The Field: Blaze Orange finish is not safety orange: it renders dark brown with orange sparks.",
  "Blaze Orange finish = fluorescent safety orange", "renders as dark brown with orange sparks, not solid safety orange", CARD + ' base::tac_blaze_orange')
f('high_vis', 'examples[1].title', "Blaze orange", "Safety orange", "same", "same", CARD)
f('high_vis', 'examples[1].settings', '*', {"Body": "Gloss, Use solid color #ff6a00", "Check": "metal 0, roughness 30, coat 16"},
  "Blaze Orange finish example", "replaced by a plain Gloss orange", "registry base::gloss")
f('high_vis', 'examples[1].result', "A fluorescent-feel orange with a high shine.", "A bright flat orange with a high shine.", "same", "same", CARD)
f('high_vis', 'examples[2].result', "Yellow and black chevron plates.",
  "A dark amber-gold finish with a fine black stipple; it hints at hazard colours but is not crisp yellow-black chevrons (draw black bands over a Gloss yellow zone for those).",
  "Wasp Signal = yellow and black chevron plates", "renders as dark golden-brown amber with fine black stipple", CARD + ' base::wasp_warning')
f('high_vis', 'faq[1].a', "Retroreflective spec overlay.", "Retroreflective spec overlay (shine only; at distance it reads as a dry sandy sheen, so do not expect it to change colour).",
  "Retroreflective gives a visible glint", "renders as a dry sandy sheen, no colour of its own", CARD + ' spec_retroreflective')
# police
f('police_emergency', 'examples[1].result', "Yellow-black chevron cuticle on the bumper.",
  "A dark amber-gold finish with a fine black stipple on the bumper (draw black bands on a Gloss yellow box for crisp hazard stripes).",
  "yellow-black chevrons; typo 'cuticle'", "Wasp Signal renders as amber with black stipple", CARD + ' base::wasp_warning')
# black_gold_luxury
f('black_gold_luxury', 'how[3]', "Gold Flake at Strength 30 on the body for a glittering depth.",
  "Gold Flake at Strength 30 on the body for a faint sandy shimmer (shine only; no gold colour appears).",
  "Gold Flake glitters gold", "smooth sheen with slight sandy shimmer, nothing looks gold", CARD + ' spec gold_flake')
f('black_gold_luxury', 'examples[2].title', "Black-gold colour shift", "Black-to-gold fade", "Cs Black Gold = black that warms to gold", "Cs Black Gold renders as a vivid teal and purple marble", CARD + ' monolithic::cs_black_gold')
f('black_gold_luxury', 'examples[2].settings', '*', {"Base Material": "Black Gold (search it)"}, "same", "Black Gold (gradient) renders black-to-gold", CARD + ' monolithic::grad_black_gold')
f('black_gold_luxury', 'examples[2].result', "Black that warms to gold at an angle.", "Black melting into gold with a glittery gold cross-hatch sparkle.", "same", "same", CARD)
# colour_shift
f('colour_shift', 'faq[2].a', "Cs Black Gold.", "Use the Black Gold gradient finish for a black-to-gold fade; Cs Black Gold renders as a busy teal and purple marble.",
  "Cs Black Gold for black-gold", "renders as teal/purple marbled swirl", CARD + ' monolithic::cs_black_gold')
f('colour_shift', 'how[3]', "try values 0 to 100.", "try 90 for a neighbouring hue or 180 for the opposite hue (0 is off).",
  "Color Flip range 0 to 100", "Color Flip: 0 = off, 90 = neighbour, 180 = opposite; only on finishes that support it", 'ui_map zone.color_flip')
f('colour_shift', 'examples[0].result', "Deep purple, blue and star-white.", "Deep purple-indigo with a speckle of stars and a faint ringed swirl.", "same", "same", CARD + ' chameleon_galaxy')
f('colour_shift', 'examples[1].result', "Green, yellow and pink.", "A near-black car with a faint neon-cyan crackle haze (teal glitter over dark).", "Chameleon Neon = green yellow pink", "renders as black with faint neon-cyan crackle", CARD + ' chameleon_neon')
f('colour_shift', 'examples[2].result', "Orange to red.", "A warm orange-red metallic with yellow glitter.", "same", "same", CARD + ' chameleon_fire')

# ---- tribal
f('tribal', 'summary', "Use Tribal Flame or the Tribal Tattoo, Celtic Spiral and Norse Runes patterns on the hood and sides.",
  "Use the Tribal Flame finish for bold shapes; the Tribal Tattoo, Celtic Spiral and Norse Runes patterns render as fine texture (scratchy hatching, a dotted wallpaper, a speckle), so use them small.",
  "tribal patterns paint bold swirls/spikes", "Tribal Tattoo = scratchy multicolour confetti; Celtic Spiral = dotted green-purple wallpaper; Norse Runes = fine tan/teal speckle",
  CARD + ' decade_90s_tribal_tattoo, tribal_celtic_spiral, tribal_norse_runes')
f('tribal', 'examples[0].title', "Black tribal on orange", "Tribal hatching on orange", "same", "same", CARD)
f('tribal', 'examples[0].result', "Thick black swirls.", "A fine scratchy hatch texture over the orange; it reads as texture, not thick black swirls.", "Tribal Tattoo = thick black swirls", "renders as fine scratchy multicolour confetti", CARD)
f('tribal', 'examples[1].result', "Fine knotwork over a base colour.", "A dotted, wallpaper-like spiral texture over the base colour.", "Celtic Spiral = knotwork", "spirals shrink to a polka-dot texture", CARD)
f('tribal', 'examples[2].result', "Sharp flame-shaped tribal swirls.", "Bold red and black fire shapes with a yellow edge glow; very high contrast.", "same", "Tribal Flame renders as bold red/black camo-like fire shapes with yellow edge glow", CARD + ' base::flame_tribal')
# ---- geometric
f('geometric', 'examples[0].settings.PATTERN', "Chevron Stack, Blend, 0.8", "Chevron, Blend, 0.8", "Chevron Stack = arrows", "Chevron Stack renders as fine horizontal pinstripes", CARD + ' pattern::chevron_stack')
f('geometric', 'examples[0].result', "Arrows pointing forward.", "Tidy zigzag V rows across the panel.", "arrows pointing forward", "Chevron renders as horizontal zigzag rows of Vs", CARD + ' pattern::chevron')
f('geometric', 'examples[0].title', "Chevron arrows", "Chevron rows", "same", "same", CARD)
f('geometric', 'examples[1].result', "A diamond pattern.", "A soft harlequin check with low contrast.", "Argyle = diamond pattern", "reads as a soft purple-green harlequin check, no strong contrast", CARD + ' pattern::argyle')
f('geometric', 'deep[1].body', "Keep shapes large enough to read at 50 metres.",
  "Keep shapes large enough to read at 50 metres. On the car Chevron is the cleanest of these; Houndstooth and Star Tile Mosaic read as confetti-like speckle and Art Deco Chevron as soft mottling, so judge on the CAR view.",
  "all listed patterns read as crisp flat shapes", "Houndstooth = busy confetti, Star Tile Mosaic = speckle, Art Deco Chevron = mottled grey", CARD)
# ---- hex_tech
f('hex_tech', 'summary', "Use Hex Mesh, Hex Carbon, Hex Circuit or Graphene Hex patterns, with the Hex Cells spec overlay for shine.",
  "Tech looks are fine hexagon grids on dark: use Graphene Hex or Hex Carbon with the Hex Cells spec overlay for shine. Hex Mesh and Hex Circuit render as busy static.",
  "Hex Mesh / Hex Circuit give clean honeycombs and traces", "Hex Mesh = multicolour confetti with no mesh; Hex Circuit = dense static, no structure", CARD + ' hex_mesh, hex_circuit')
f('hex_tech', 'how[2]', "choose Hex Mesh, Hex Circuit or Graphene Hex, Paint mode Blend", "choose Graphene Hex or Hex Carbon, Paint mode Blend", "same", "same", CARD)
f('hex_tech', 'examples[0].title', "Hex mesh on black", "Graphene hex on black", "same", "same", CARD)
f('hex_tech', 'examples[0].settings.PATTERN', "Hex Mesh, Blend, 0.6", "Graphene Hex, Blend, 0.6", "same", "same", CARD)
f('hex_tech', 'examples[0].result', "A dark car with honeycomb glints.", "A dark car with a fine jewel-toned hex-ring dot grid and honeycomb glints from the spec overlay.", "same", "Graphene Hex renders as a fine jewel-toned hex-ring dot grid", CARD + ' graphene_hex')
f('hex_tech', 'examples[1].title', "Circuit cyan", "Hex carbon", "Hex Circuit = cyan circuit traces", "renders as dense multicolour static, no traces", CARD + ' hex_circuit')
f('hex_tech', 'examples[1].settings', '*', {"PATTERN": "Hex Carbon, Blend, 0.6"}, "same", "same", CARD)
f('hex_tech', 'examples[1].result', "Cyan circuit traces on hex cells.", "A dark panel with a soft muted hex-tile texture.", "same", "Hex Carbon renders as a soft muted hex-dot pattern, strokes gone", CARD + ' hex_carbon')
f('hex_tech', 'faq[0].a', "Hex Mesh pattern plus Hex Cells spec.", "Graphene Hex pattern plus Hex Cells spec.", "same", "same", CARD)
f('hex_tech', 'faq[1].a', "Hex Circuit.", "No pattern draws clear circuit traces; Hex Circuit gives a busy multicolour static. A cyberpunk finish is nearer.", "Hex Circuit = circuits", "renders as static", CARD)
# ---- marble_stone
f('marble_stone', 'summary', "or the Marble Veining pattern.", "(the Marble Veining pattern renders as rippled drapery stripes, not stone veins).", "Marble Veining = stone veins", "renders as rippled striped fabric in muted purple, teal, pink", CARD + ' marble_veining')
f('marble_stone', 'how[3]', "Or use PATTERN Marble Veining on a solid white or black body, Paint mode Blend, Scale (pattern) 0.8.",
  "The Marble Veining pattern is only a soft rippled-drapery look (no stone veins), so prefer the finishes above.", "same", "same", CARD)
f('marble_stone', 'examples[1].title', "Black marble", "Ebru marble", "Marble Veining pale veins on black", "pattern has no visible stone veins", CARD)
f('marble_stone', 'examples[1].settings', '*', {"Base Material": "Ebru Marble"}, "same", "same", CARD)
f('marble_stone', 'examples[1].result', "Pale veins across a black body.", "A calm muted violet with dark veins, satin not shiny.", "same", "Ebru Marble renders as a purple and black marbled car", CARD + ' monolithic::fm_ebru_marble')
f('marble_stone', 'examples[2].result', "A floating blue-white glow over fine silver.", "A cool blue-grey cracked-crystal look with glowing blue-violet edges, like labradorite.", "Moonstone = blue-white glow over silver", "renders as cool blue-grey cracked crystal with blue-violet edges", CARD + ' monolithic::fmo_moonstone_adular')
f('marble_stone', 'faq[1].a', "White gloss with Marble Veining.", "Search the stone finishes and use Hue Shift or a solid colour toward white; Marble Veining does not draw stone veins.", "same", "same", CARD)
# ---- holographic_iridescent
f('holographic_iridescent', 'how[1]', "BASE COLOR on Use finish's own color.", "BASE COLOR on Use solid color and choose black or deep blue (Holo Flake is a fine pink-white twinkle dust, so the colour is whatever you put under it).",
  "Holo Flake brings its own colours", "renders as a sparkling dust that tints with pink-white twinkle; the real colour is what is under it", CARD + ' base::efx_holo_flake')
f('holographic_iridescent', 'examples[0].result', "A mirror finish with rainbow flake.", "A fine pink-white twinkle dust over your chosen dark colour.", "mirror finish with rainbow flake", "see how[1]", CARD)
f('holographic_iridescent', 'examples[2].result', "A thin-film rainbow over black.", "A smooth oily-looking sheen with a faint wavering shimmer on black; the rainbow is subtle.", "thin-film rainbow", "renders as a smooth oily sheen with faint wavering shimmer", CARD + ' spec_iridescent_film')
# ---- space_galaxy
f('space_galaxy', 'summary', "with the Stardust pattern and Galaxy Swirl or Stardust Fine overlays.", "with the Stardust Fine and Galaxy Swirl overlays (the Stardust pattern is a navy woven haze, not stars).", "Stardust pattern makes stars", "renders as a deep navy woven fabric with faint purple haze", CARD + ' pattern::stardust')
f('space_galaxy', 'how[2]', "open PATTERN and choose Stardust, Blend, Scale (pattern) 0.6.", "for a deep blue woven haze under the stars you can also open PATTERN and choose Stardust, Blend, Scale (pattern) 0.6.", "same", "same", CARD)
f('space_galaxy', 'faq[0].a', "Dark base plus Stardust.", "Dark base plus the Stardust Fine overlay or the Stardust Coat finish.", "same", "same", CARD)
f('space_galaxy', 'examples[1].result', "A magenta and cyan ion cloud.", "A glowing purple cloud with bright lilac wisps against dark indigo.", "Nebula = magenta and cyan", "renders purple/lilac on indigo, no cyan visible", CARD + ' monolithic::ff_nebula')
f('space_galaxy', 'examples[2].result', "Purple to blue to white.", "Deep purple-indigo with a speckle of stars and a faint ringed swirl.", "same", "same", CARD)
f('space_galaxy', 'protips[0]', "Galaxy Swirl adds a spiral of sparkle.", "Galaxy Swirl adds a faint wavy ripple to the sheen on metal (almost plain on satin).", "spiral of sparkle", "renders as a soft wavy ripple / fine scroll sheen", CARD + ' spec galaxy_swirl')
# ---- dragon_snake_scales
f('dragon_snake_scales', 'how[2]', "choose Dragon Scale, Snake Skin or Snake Skin 3,", "choose Dragon Scale (a mottled hide with soft oval scales), Snake Skin (olive-green scaly skin) or Snake Skin 3 (a tan brocade-like skin),", "same", "see cards", CARD)
f('dragon_snake_scales', 'how[3]', "pick Duality Scales or Dragon Ascent in Base Material.",
  "pick Duality Scales (lime-green and purple patchwork) or Dragon Ascent (an orange-and-black dragon picture) in Base Material.", "Duality Scales / Dragon Ascent = scale looks", "Duality = clashing two-colour patchwork; Dragon Ascent = dragon-in-flames illustration", CARD)
f('dragon_snake_scales', 'examples[0].result', "Overlapping dark red scales.", "A mottled reptile hide with soft oval scales over the dark red body.", "overlapping dark red scales", "Dragon Scale renders as a mottled hide with a few soft ovals", CARD + ' dragon_scale')
f('dragon_snake_scales', 'examples[1].settings.PATTERN', "Snake Skin 3, Blend, 0.6", "Snake Skin, Blend, 0.6", "Snake Skin 3 = green reptile skin", "Snake Skin 3 is warm brown-gold brocade; Snake Skin is olive-green scales", CARD + ' snake_skin_3, snake_skin')
f('dragon_snake_scales', 'examples[1].result', "A green reptile skin.", "A mottled olive-green scaly skin; the scales merge into texture at distance.", "same", "same", CARD)
f('dragon_snake_scales', 'examples[2].result', "Dragon gold with flame trails.", "An orange-and-black blaze with a dragon head and a gold circular emblem: a picture finish, not a scale texture.", "same", "MS Dragon Ascent renders as a dragon-in-flames illustration", CARD + ' base::ms_dragon_ascent')
# ---- patriotic_rwb
f('patriotic_rwb', 'examples[1].result', "Navy with red-white star flecks.", "A navy car streaked with red and white, like a flag blowing in wind.", "star flecks", "renders as navy streaked red and white", CARD + ' lfr_old_glory_flux')
f('patriotic_rwb', 'examples[2].result', "Firework bursts on a black field.", "A saturated royal blue-violet with a soft lilac haze and scattered white star points, like a firework night sky.", "black field", "renders royal blue-violet", CARD + ' lfr_rockets_red_glare')
f('patriotic_rwb', 'protips[0]', "Distressed Patina is a weathered flag pattern.", "Distressed Patina is a muted red linen-grain pattern with barely visible spots; use it as a faded red area, not a flag.", "weathered flag", "renders as flat grainy muted red", CARD + ' lfr_distressed_flag')
# ---- japanese_art
f('japanese_art', 'examples[0].result', "Deep blue waves.", "A fine scaly wave-mesh texture over the deep indigo.", "clear waves", "Japanese Wave renders as a fish-scale mesh with colour flecks", CARD + ' japanese_wave')
f('japanese_art', 'examples[1].result', "A Japanese-inspired lacquer.", "A pastel pink, lilac and coral landscape poster with a mountain and a red sun.", "same", "renders as a pastel Fuji landscape", CARD + ' rs_fuji_dawn')
f('japanese_art', 'examples[2].result', "Red rising-sun street chrome with black speed stripes.", "A loud red, black and silver diagonal stripe job with a sun burst.", "same", "renders as red/black/silver diagonal stripes with a sunburst", CARD + ' rs_bosozoku_riot')
f('japanese_art', 'protips[0]', "Hakuryu Ice is a cool white lacquer.", "Hakuryu Ice is a big icy dragon scene fading from white-cyan to deep blue.", "cool white lacquer", "renders as a dragon hero picture", CARD + ' rs_hakuryu_ice')
# ---- surf
f('surf_beach_summer', 'examples[1].result', "Rows of peeling surf barrels with foam.", "A bright teal-and-cyan ocean-wave stripe field with white crest highlights.", "same", "renders as aqua ripples with white crests", CARD + ' astra_pipeline_royale')
f('surf_beach_summer', 'examples[2].result', "Cream, mint and coral wax shavings.", "A pale warm cream with a faint pink and green confetti speckle, soft and sandy.", "same", "renders as pale cream with faint speckle", CARD + ' at_surf_wax')
# ---- punk
f('punk_grunge_street', 'how[2]', "PATTERN Grunge Splatter or Beanie Tag, Overlay, Scale (pattern) 0.8, colour #ff2bd6 or #d7ff00.",
  "PATTERN Grunge Splatter (grimy dark maroon and charcoal blotches) or Beanie Tag (a confetti of red, green, blue and yellow tags), Overlay, Scale (pattern) 0.8. Overlay paints the pattern's own colours; use Hue / Saturation (pattern) to push them toward pink or lime.",
  "splatter in a picked colour #ff2bd6 / #d7ff00", "Overlay paints own colours; Grunge Splatter renders as dark maroon/charcoal digital camo, not splatter in a chosen colour", CARD + ' decade_90s_grunge_splatter, decade_90s_beanie_tag')
f('punk_grunge_street', 'examples[0].settings.Colour', "#d7ff00", "Hue / Saturation (pattern) toward lime", "same", "same", CARD)
f('punk_grunge_street', 'examples[0].result', "A black car with lime splatter.", "A black car with grimy dark blotches shifted toward lime.", "lime splatter", "see how[2]", CARD)
f('punk_grunge_street', 'examples[1].result', "Faded clearcoat patches.", "Dusty aged earth-tone patches with dark smoky areas and a faint crackle grain.", "faded clearcoat patches", "Die-Back Patina renders as dusty aged earth-tone paint", CARD + ' base::bth_die_back')
# ---- checkered_flag
f('checkered_flag', 'examples[0].result', "A black and white band along the sill.", "A fine black-and-white check band along the sill (small checks, not big race squares).", "same", "renders as a fine checker that merges to mid-grey at distance", CARD + ' decade_50s_diner_checkerboard')
f('checkered_flag', 'examples[1].result', "A black car with a checker that appears in reflections.", "A black car with a faint gingham shimmer in the bright highlights (it does not read as a flag from a distance).", "checker appears in reflections", "renders as a faint gingham shimmer, no flag read", CARD + ' spec checker_flag_subtle')
# ---- fade_gradient
f('fade_gradient', 'examples[2].result', "Pale blue to white.", "A loud icy cyan and sky-blue marbled pattern with grey islands, more water-cell mosaic than a clean gradient.", "Arctic Dawn = pale blue to white", "renders as icy cyan marbled mosaic", CARD + ' grad_arctic_dawn')
# ---- flames
f('flames', 'examples[0].result', "Orange-yellow licks on black.", "A glowing red-orange-yellow ember field over the zone; it reads as heat shimmer more than distinct licks.", "licks", "Hot Rod Flames reads as heat shimmer / embers over the panel", CARD + ' base::flame_hotrod')
f('flames', 'examples[1].result', "Flames that only half show in the dark paint.", "A near-solid black-charcoal with faint warm smudges, ghosts of flames behind the paint.", "same", "same", CARD + ' base::flame_ghost')
f('flames', 'examples[2].settings.Body', "Gloss, #f4f4f4", "Gloss, #0b0b0e", "blue flames on a white body", "Blue Flame is sparse glowing blue orbs on black; it needs a dark ground", CARD + ' base::flame_blue')
f('flames', 'examples[2].result', "Blue fire on white.", "Sparse glowing electric-blue dots on a dark body, like neon bubbles.", "same", "same", CARD)
# ---- cyberpunk
f('cyberpunk_synthwave', 'how[3]', "PATTERN Neon Grid, Paint mode Blend,", "PATTERN Neon Grid (a fine multicolour plaid shimmer, not crisp lines), Paint mode Blend,", "Neon Grid = crisp grid", "renders as fine plaid / graph-paper shimmer, neon static", CARD + ' decade_80s_neon_grid')
f('cyberpunk_synthwave', 'examples[0].result', "A purple car with a pink dusk fade and a glowing grid.", "A purple car with a pink dusk fade and a fine neon plaid shimmer on the lower body.", "same", "same", CARD)
f('cyberpunk_synthwave', 'examples[2].result', "A deep violet with digital glow.", "A smooth purple galaxy of round lenses with diagonal lime streaks as the one bright accent.", "same", "renders as purple lenses with lime ribbons", CARD + ' base::cbp_quantum_violet')
# ---- glass_crystal
f('glass_crystal', 'examples[0].result', "Voronoi crystal shards with prism edges.", "A loud multicolour stained-glass confetti with white seams.", "same", "renders as saturated stained-glass confetti", CARD + ' base::anime_crystal_facet')
f('glass_crystal', 'examples[1].result', "Ice dendrites over frosted rime.", "A deep navy blue with a snowy starfield of light flecks and a frosty speckle.", "ice dendrites", "renders as navy blue with snowy starfield", CARD + ' base::astra_cryogenic_bloom')
f('glass_crystal', 'examples[2].result', "Frosted pebbles in strong colours.", "A loud stained-glass confetti of blue, amber, green and turquoise patches.", "same", "same", CARD + ' base::astra_sea_glass_confessional')
# ---- pastel
f('pastel', 'examples[1].result', "Pink and teal grid feel.", "A pastel pink car with aqua and yellow Memphis-style shapes.", "pink and teal grid", "renders pink with aqua and yellow Memphis shapes", CARD + ' base::rad_miami_pastel')
f('pastel', 'examples[2].result', "Matte pastel diamonds.", "A cream base with a pastel confetti-and-net texture that blurs to pale cream at distance.", "diamonds", "renders as cream with confetti-and-net texture", CARD + ' base::argyle_pastel')
# ---- metal_flake
f('metal_flake_sparkle', 'examples[1].result', "Black paint with gold sparkle.", "Black paint with a faint sandy shimmer in the highlights (shine only, no gold colour).", "gold sparkle", "Gold Flake renders as smooth sheen, nothing looks gold", CARD + ' spec gold_flake')
f('metal_flake_sparkle', 'examples[2].result', "Rainbow sparkle.", "A brighter, busier grainy sparkle in the highlights (shine only; no rainbow colour).", "rainbow sparkle", "Holographic Flake renders as a sparkly grainy sheen", CARD + ' spec holographic_flake')
# ---- camo
f('camo_woodland_desert', 'examples[1].result', "Two-colour disruptive sand pattern.", "Dark brown with tan spots in a loose scatter that reads as faded desert camo.", "same", "renders dark brown with tan spots", CARD + ' base::tac_desert_dpm')
f('camo_digital_urban', 'examples[2].result', "White with grey tears.", "A frosty grey-white speckle, like granite or salt.", "same", "renders as mid-light grey-white frosty speckle", CARD + ' base::tac_snow_overwhite')
# ---- action list edits: ('ACT-', aid, id) removals
ACT_DEL = [('look_fast', 'lightning'), ('aggressive_mean', 'chevron_stack'), ('speed_lines_motion', 'zigzag_bands'), ('speed_lines_motion', 'lightning'),
           ('hex_tech', 'hex_mesh'), ('hex_tech', 'hex_circuit'), ('high_vis', 'base::tac_blaze_orange'), ('candy_lowrider', 'gothic_scroll'),
           ('marble_stone', 'marble_veining'), ('black_gold_luxury', 'monolithic::cs_black_gold'), ('colour_shift', 'monolithic::cs_black_gold')]
ACT_ADD = [('aggressive_mean', 'pattern', 'chevron'), ('speed_lines_motion', 'pattern', 'chevron')]
f('speed_lines_motion', 'what', "Streaks, chevrons and bolts do this;", "Streaks, chevrons and zigzags do this;", "bolts", "Lightning pattern renders as hairline scratches", CARD + ' pattern::lightning')
f('speed_lines_motion', 'mistakes[0].cause', "Rotation unset", "Rotate (pattern) unset", "control name", "label is Rotate (pattern)", 'ui_map pattern controls')


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = os.path.join(ROOT, 'data', 'encyclopedia', 'ideas.json')
def _tok(p): return re.findall(r'[^.\[\]]+|\[\d+\]', p)
def main():
    doc = json.load(open(P, encoding='utf-8'))
    A = {a['id'][6:]: a for a in doc['articles']}
    n = 0
    for (aid, path, old, new, *_r) in F:
        t = _tok(path); o = A[aid]
        for x in t[:-1]: o = o[int(x[1:-1])] if x.startswith('[') else o[x]
        k = int(t[-1][1:-1]) if t[-1].startswith('[') else t[-1]
        cur = o[k]
        if old == '*':
            if cur != new: o[k] = new; n += 1
        elif new in cur: continue
        elif old in cur: o[k] = cur.replace(old, new); n += 1
    for aid, i in ACT_DEL: A[aid]['actions'] = [x for x in A[aid]['actions'] if x['id'] != i]
    for aid, do, i in ACT_ADD + [('geometric', 'pattern', 'chevron'), ('black_gold_luxury', 'finish', 'monolithic::grad_black_gold')]:
        if not any(x['id'] == i for x in A[aid]['actions']): A[aid]['actions'].append({'do': do, 'id': i})
    A['geometric']['actions'] = [x for x in A['geometric']['actions'] if x['id'] != 'chevron_stack']
    m = A['marble_stone']
    m['summary'] = "Marble and stone looks come from ready-made stone finishes (Marble, Banded Agate, Ebru Marble, Moonstone). They suit clean, premium builds; the Marble Veining pattern is only a rippled-drapery look."
    m['faq'][0]['a'] = "Use a Marble finish; the Marble Veining pattern does not draw stone veins."
    A['hex_tech']['summary'] = "Tech looks are fine hexagon grids on dark: use Graphene Hex or Hex Carbon with the Hex Cells spec overlay for shine. Hex Mesh and Hex Circuit render as busy static."
    nl = chr(10)
    s = '{"domain": ' + json.dumps(doc['domain']) + ', "version": ' + json.dumps(doc['version']) + ', "articles": [' + nl + (',' + nl).join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in doc['articles']) + nl + ']}' + nl
    with open(P + '.tmp', 'w', encoding='utf-8', newline=nl) as fh: fh.write(s)
    os.replace(P + '.tmp', P)
    print('enc_ideas_fix_r4: applied', n, 'text fixes')
if __name__ == '__main__': main()
