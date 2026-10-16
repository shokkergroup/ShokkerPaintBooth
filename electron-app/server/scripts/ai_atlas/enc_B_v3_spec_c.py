"""V3 depth for the spec map articles, part C (tools, blend modes, overlays, feels, auto-pop, inspector, angle reveal, groups).
Blend-mode maths are quoted from engine/compose.py apply_physical_spec_blend. Run: python scripts/ai_atlas/enc_B_v3_spec_c.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'spec'
ENG = 'shokker_engine_v2.py'
COMP = 'engine/compose.py'
ZONES = 'paint-booth-2-state-zones.js'
W = 'SPB_WIKI.html'
AIK = 'docs/ai_knowledge/'

enrich(D, 'spec.material_override_remap_lighting', level='pro',
    sources=[ENG + ':331-355', ENG + ':366-393', ENG + ':396-420', ENG + ':20253-20255', ENG + ':20735-20747', AIK + 'how_do_i.md:437-453', W + ':4276-4286'],
    deep=[
        {'heading': 'The order the three tools run', 'body': 'After the sliders, the zone spec goes through Material Remap first, then Material Override, then Lighting Mask. All three run before the final floors, so a flat override of roughness 5 on a non-chrome pixel is lifted to 15 and a coat of 1 to 15 is lifted to 16. Remap and Override work per channel (metal, roughness, coat); Lighting Mask only touches alpha.'},
        {'heading': 'Remap in numbers', 'body': 'Remap squeezes a channel into a new low and high range: result = low + source / 255 times (high minus low). A source 0 goes to Low and a source 255 goes to High. A metal range of 0 to 100 turns a chrome (255) into metal 100 but keeps every bit of variation, so a brushed grain stays brushed while the whole thing calms down. Override is blunt: it sets one flat value for the channel across the zone and loses all variation.'},
        {'heading': 'Sampler and decal rescue', 'body': 'The Material Sampler reads the exact metal, roughness and coat at a spot (Point, 3 by 3 median or 5 by 5 median) and can copy them onto the active zone. Decal Rescue Kit puts a plain non-metal spec under stamped numbers and sponsors: Flat Vinyl, Satin Decal or Gloss Decal, so they do not take the sparkle of whatever spec is below.'},
    ],
    examples=[
        {'title': 'Calm a too-sparkly metallic', 'goal': 'Keep the texture, lower the metal.',
         'settings': {'SPEC TOOLS': 'Material Range Remapper', 'Metal Low': '0', 'Metal High': '120', 'Roughness': 'Original', 'Coat': 'Original'},
         'result': 'The brightest flakes now peak at metal 120 and every pattern shape is still there.'},
        {'title': 'Rescue sponsor logos', 'goal': 'Stop numbers and sponsors from going sparkly under chrome.',
         'settings': {'SPEC TOOLS': 'Decal Rescue Kit', 'Finish': 'Flat Vinyl', 'Body zone': 'Limited to the car paint layer'},
         'result': 'Decals keep a plain non-metal look while the body stays chrome.'},
    ],
    combos=[{'with': 'spec.channel_sliders', 'why': 'Sliders run just before these tools, so a remap or override can overrule a slider.'},
            {'with': 'spec.channel_a_mask', 'why': 'Lighting Mask is the tool that changes alpha.'},
            {'with': 'spec.iron_rules', 'why': 'The floors run after all three tools.'}],
    faq=[
        {'q': 'Remap or slider?', 'a': 'Sliders move the whole zone evenly. Remap rescales the range and keeps the variation.'},
        {'q': 'Can I undo a remap?', 'a': 'Yes. Restore Original puts the zone back.'},
        {'q': 'What does Override do to texture?', 'a': 'It flattens the channel to one value, so texture in that channel is lost.'},
        {'q': 'Do these tools change colour?', 'a': 'No. They only change spec channels and alpha.'},
    ],
    mistakes=[
        {'symptom': 'My override of coat 5 became 16.', 'cause': 'The floors run after the tools.', 'fix': 'Use 16 or more.'},
        {'symptom': 'Override removed my brushed grain.', 'cause': 'A flat value replaces the channel.', 'fix': 'Use Remap, which keeps variation.'},
        {'symptom': 'Numbers look sparkly or dull.', 'cause': 'Stamped items take the spec of whatever is under them.', 'fix': 'Use Decal Rescue Kit and limit the body zone to the car paint layer.'},
    ],
    protips=['Remap presets are a fast start: Original, Metallic Texture, Printed Vinyl, Matte Texture and Gloss Texture. Then fine tune Low and High.',
             'Use the Material Sampler first. Copying exact numbers from a part you like is quicker than guessing.'])

enrich(D, 'spec.blend_modes', level='pro',
    sources=[COMP + ':2619-2622', COMP + ':2625-2712', ZONES + ':2118-2140', ZONES + ':2137', ENG + ':20170-20219],'.rstrip('],')],
    deep=[
        {'heading': 'The six named modes rewrite three channels', 'body': 'Ghost Carve pulls the coat value toward 64 plus 176 times the pattern, so pattern lows and highs land at very different coat values and form carved cells, and lowers roughness by up to 25. It leaves the metal alone, so any base keeps its tinted flash. Chrome Inlay lowers metal (by up to 85 percent) and roughness (by up to 65 percent) where the pattern is hot and pushes the coat value toward 245: a mirror inlay in a metal surround. Frost Etch lowers metal by up to 45, raises roughness by up to 150 and lowers the coat value by up to 35: sandblasted, milky areas. Angle Flip adds up to plus or minus 85 metal and moves the coat value by the opposite sign, up to 135, so the pattern shows at one angle and inverts at another. Ember Gate lights only the top ridges: above a pattern value of 0.80 the coat value goes to 252 and roughness to 34. Depth Press embosses: a lit rim (metal plus 110, coat plus 90) and a shadow rim (metal minus 70).'},
        {'heading': 'Without a pattern the zone itself is the field', 'body': 'These modes work with or without a pattern. With a pattern the pattern drives the effect. Without one, the zone\'s own paint structure drives it, so your livery becomes the carve: the field is the paint brightness first, the base spec shape second, a flat 0.5 last. Flat solid zones with a featureless base respond only subtly, so give the mode some structure to work with.'},
        {'heading': 'The legacy five', 'body': 'Multiply, Screen, Overlay, Hard Light and Soft Light are the older blend modes that mix the overlay values with the base. They keep working but can wash out a finish, and a strong overlay under a classic mode may flatten it. The named modes are physical: they change how metal, gloss and coat behave, not just brightness. All modes honour the iron floors afterward.'},
    ],
    examples=[
        {'title': 'Carve a livery into chrome', 'goal': 'Make the livery shapes read as mirror cuts.',
         'settings': {'Base Material': 'Chrome Foundation', 'SPEC BLEND': 'Chrome Inlay', 'Pattern': 'Any bold geometric pattern', 'Pattern spec amount': 'Raised above 0'},
         'result': 'Hot parts of the pattern become mirror-like inlays while the surround loses most of its metal.'},
        {'title': 'Colour-flip from any base', 'goal': 'Get angle-dependent flashes on a dark colour.',
         'settings': {'SPEC BLEND': 'Ghost Carve', 'Colour': 'Deep dark red or purple', 'Brightness': 'Dragged way down', 'Track': 'A daytime one'},
         'result': 'Cells with different coat values flash sky or sun colour as the car turns, while the metal stays tinted and dark.'},
    ],
    combos=[{'with': 'spec.angle_reveal', 'why': 'Ghost Carve is the recipe behind most angle-reveal finishes.'},
            {'with': 'spec.overlays_stack', 'why': 'Blend decides how an overlay meets the base; the stack decides the order.'},
            {'with': 'spec.how_layers_combine', 'why': 'See where the blend sits in the order of operations.'}],
    faq=[
        {'q': 'Which mode for sparkle that ignites on edges?', 'a': 'Ember Gate. Only the brightest ridges light up.'},
        {'q': 'Which mode for a stamped look?', 'a': 'Depth Press. Every element gets a lit rim and a shadow rim.'},
        {'q': 'Why does nothing change on my plain zone?', 'a': 'Flat solid zones with featureless bases respond subtly. Add a pattern or a structured base.'},
        {'q': 'Do the modes change the colour?', 'a': 'No. They change metal, roughness and coat only.'},
    ],
    mistakes=[
        {'symptom': 'The effect is too strong and everything is chrome.', 'cause': 'Strength and pattern spec amount both high with Chrome Inlay.', 'fix': 'Lower strength before the next layer.'},
        {'symptom': 'Ghost Carve shows nothing.', 'cause': 'The base colour is too bright, so diffuse colour hides the flashes.', 'fix': 'Crush the colour near black and judge on a daytime track.'},
        {'symptom': 'A classic blend washed out my finish.', 'cause': 'Legacy modes mix values directly.', 'fix': 'Switch to a named mode or lower strength.'},
    ],
    protips=['Compare Normal and the named mode side by side before you commit.',
             'Angle Flip is the one to try for a finish that changes between camera angles in replays.'])

enrich(D, 'spec.overlays_stack', level='intermediate',
    sources=['js/spec-overlays/picker.js:60-85', ZONES + ':12292', COMP + ':3944', COMP + ':2551-2600', AIK + 'sliders_and_controls.md:15', AIK + '02_spec_and_finishes.md:10'],
    deep=[
        {'heading': 'How an overlay changes the spec', 'body': 'Each spec overlay moves the finished material toward its own target on the channels you tick (M, R, C): result = current + (target minus current) times coverage times strength. Strength defaults to 50 percent. Overlays are applied last on the finished material, so the base cannot undo them, and the later sliders and floors still apply afterward.'},
        {'heading': 'Order and channels', 'body': 'The stack runs from the first layer to the fifth, each mixing onto the result of the one before. Texture on roughness only is the safest: it changes how light spreads without touching metal or the coat. M-only overlays add sparkle on metal. C-only overlays vary the clearcoat and tend to be the most visible in direct sun. Five layers at full strength fight each other, so build with two or three and balance their strengths.'},
        {'heading': 'Debugging a busy look', 'body': 'Mute turns a layer off without deleting it and Solo shows only that layer. Inspect reads the numbers at a spot. Because spec overlays never change colour, a flat colour preview looks identical with and without them. Use the spec views (R METAL, G ROUGH, B COAT) or the Channels readout to confirm they did anything.'},
    ],
    examples=[
        {'title': 'Brushed steel hood', 'goal': 'Real brushed texture on a metallic base.',
         'settings': {'Base Material': 'Brushed (Foundation)', 'Spec overlay 1': 'A brushed metal pattern', 'Channels': 'M and R', 'Strength': '50', 'Size': '0.5'},
         'result': 'Fine directional grain with occasional bright glints.'},
        {'title': 'Carbon under gloss', 'goal': 'Visible weave only in the shine.',
         'settings': {'Base Material': 'Gloss Carbon (metal 55, roughness 30, coat 16)', 'Spec overlay 1': 'A carbon weave pattern', 'Channels': 'R', 'Strength': '40'},
         'result': 'A weave that moves with the light while the paint stays a plain colour.'},
    ],
    combos=[{'with': 'spec.blend_modes', 'why': 'The blend mode changes how each overlay meets the base spec.'},
            {'with': 'spec.pattern_groups', 'why': 'Where to find each kind of overlay.'},
            {'with': 'patterns.layers_and_stacking', 'why': 'Paint patterns and spec overlays both stack to five, but only patterns change colour.'}],
    faq=[
        {'q': 'How many overlays can I stack?', 'a': 'Up to five per zone.'},
        {'q': 'Why does my overlay do nothing in the preview?', 'a': 'Overlays change shine only. Check the spec views.'},
        {'q': 'What strength should I use?', 'a': 'Start at 50, the default, and go lower if the look is loud. 30 to 50 reads as subtle flake.'},
        {'q': 'Can I mute a layer?', 'a': 'Yes. Mute, Solo and Duplicate are on each layer.'},
    ],
    mistakes=[
        {'symptom': 'Everything looks noisy.', 'cause': 'Several overlays at high strength on all three channels.', 'fix': 'Solo each layer, tick fewer channels, lower strength.'},
        {'symptom': 'The old stack disappeared.', 'cause': 'Setting overlays through an apply command replaces the stack.', 'fix': 'Add layers one at a time with Add Spec Overlay.'},
    ],
    protips=['A subtle flake overlay at strength 30 to 50 adds depth to almost any finish.',
             'Pick the channel on purpose. The same pattern on R, on M and on C gives three different looks.'])

enrich(D, 'spec.presets_feels', level='beginner',
    sources=[ZONES + ':9969-9975', ENG + ':20225-20250', AIK + 'sliders_and_controls.md:18'],
    deep=[
        {'heading': 'What each Feel really does', 'body': 'A Feel is three slider values applied at once, each between minus 127 and plus 127. Wet Candy is metal plus 30, roughness minus 55, coat plus 45. Track Flash is 55, minus 35, plus 60. Chrome Mirror is 80, minus 80, plus 70. Deep Gloss is 25, minus 45, plus 85. Soft Pearl is 15, 25, 10. Satin Matte is minus 25, plus 65, minus 15. Roughness minus always means glossier. The coat numbers are positive, and because the coat byte is backwards a plus value makes the coat duller, so these Feels make the coat a little duller while they lower roughness and add metal.'},
        {'heading': 'Feels sit on top of the finish', 'body': 'They are added to whatever the finish already is, then clipped at 0 for metal, 15 for roughness and 16 for coat. So Chrome Mirror on a matte finish will not make it chrome: metal 0 plus 80 and roughness 200 minus 80 is a satin metal. On a gloss finish the same Feel makes a real step toward chrome.'},
        {'heading': 'Your own Feels', 'body': 'Set the three sliders, click the save icon, and the Feel is kept on this computer next to the built-in ones. They are not shared with other computers or other drivers.'},
    ],
    examples=[
        {'title': 'Candy glow', 'goal': 'More wet depth on a coloured gloss.',
         'settings': {'Base Material': 'Candy', 'Spec preset': 'Wet Candy'},
         'result': 'Roughness drops and metal rises a little for a deeper, glassier colour.'},
        {'title': 'Quick stealth', 'goal': 'Turn a gloss zone into a flat one.',
         'settings': {'Base Material': 'Gloss', 'Spec preset': 'Satin Matte'},
         'result': 'Roughness 30 plus 65 is 95 and coat 16 minus 15 clips at 16: a satin from gloss in one click.'},
    ],
    combos=[{'with': 'spec.channel_sliders', 'why': 'A Feel is just three slider values; fine tune them by hand afterward.'},
            {'with': 'spec.auto_pop', 'why': 'Auto-Pop is the automatic version of a Feel.'}],
    faq=[
        {'q': 'Do Feels change colour?', 'a': 'No.'},
        {'q': 'Can I stack two Feels?', 'a': 'A Feel sets the sliders, so a second one replaces the first.'},
        {'q': 'Where are saved Feels kept?', 'a': 'On this computer only.'},
        {'q': 'Which Feel for chrome?', 'a': 'Chrome Mirror, but start from a gloss or metallic base. On a matte base it will only reach satin metal.'},
    ],
    mistakes=[
        {'symptom': 'A Feel did nothing on chrome.', 'cause': 'The finish was already at the limit of the channels the Feel pushes.', 'fix': 'Pick a Feel that pushes the other way.'},
        {'symptom': 'The coat looks duller with Wet Candy.', 'cause': 'Its coat number is positive and the coat scale is backwards.', 'fix': 'Judge by eye and lower B COAT by 5s if you want it wetter.'},
    ],
    protips=['Apply a Feel, then fine tune in steps of 5.',
             'Feels are a good way to learn the sliders: apply one and look at what the R, G and B values became.'])

enrich(D, 'spec.auto_pop', level='beginner',
    sources=[ZONES + ':9919', ZONES + ':9945', ENG + ':20225-20250'],
    deep=[
        {'heading': 'The exact thresholds', 'body': 'Auto-Pop reads the zone average from the spec preview. If the metal average is under 70 it adds up to 15 metal, 30 percent of the gap to 70. If roughness averages over 70 it lowers roughness by the excess, up to 45. If the coat averages over 55 it lowers the coat value by the excess, up to 45, which is glossier. Every step is a multiple of 5 and it only moves in the direction of gloss. A zone that is already glossy gets a note and no change.'},
        {'heading': 'What it needs and what it does not do', 'body': 'It needs a spec preview to have been rendered first, because it measures the real zone spec. It adds to the three sliders, so it can be undone in one step. It will not turn matte into chrome, because the metal boost is capped at 15 and roughness and coat drop by at most 45 per click. Repeated clicks keep boosting until the limits are reached.'},
    ],
    examples=[
        {'title': 'Rescue a dull zone', 'goal': 'Add life to a zone that renders flat.',
         'settings': {'Step 1': 'Render a preview', 'Step 2': 'Open the zone SPEC sliders', 'Step 3': 'Click Auto-Pop'},
         'result': 'The sliders move by a few steps toward more metal and less roughness. Check the car and press Undo if it is not right.'},
        {'title': 'Already glossy', 'goal': 'See that Auto-Pop respects a good zone.',
         'settings': {'Zone': 'Gel Coat or Gloss body', 'Action': 'Auto-Pop'},
         'result': 'It says the zone is already glossy and changes nothing.'},
    ],
    combos=[{'with': 'spec.channel_sliders', 'why': 'Auto-Pop moves these three sliders.'},
            {'with': 'spec.presets_feels', 'why': 'For a bigger, deliberate move use a Feel.'}],
    faq=[
        {'q': 'Will Auto-Pop wreck my finish?', 'a': 'No. It is small, conservative, and one Undo step.'},
        {'q': 'Why does it ask me to render first?', 'a': 'It measures the real spec preview of the zone.'},
        {'q': 'Does it add colour?', 'a': 'No. Spec only.'},
        {'q': 'Can I use it twice?', 'a': 'Yes, each click boosts again until the limits.'},
    ],
    mistakes=[
        {'symptom': 'Nothing happened.', 'cause': 'The zone is already glossy, or no spec preview was rendered.', 'fix': 'Render a preview first and read the message.'},
        {'symptom': 'I wanted a matte car shiny.', 'cause': 'Auto-Pop is capped at gentle steps.', 'fix': 'Use a Feel or choose a different base finish.'},
    ],
    protips=['Auto-Pop is a safe first move when a zone looks dull and you do not know why.',
             'After Auto-Pop the sliders hold real numbers, so you can read them to learn what the zone needed.'])

enrich(D, 'spec.inspector', level='intermediate',
    sources=['paint-booth-v2.html:3980', 'paint-booth-v2.html:2391', AIK + 'how_do_i.md:431-441', W + ':4787'],
    deep=[
        {'heading': 'Seeing the real numbers', 'body': 'The Material Sampler shows exact metal, roughness, coat and alpha at a clicked spot. The channel buttons ALL, R, G, B and A switch the preview between the channels. Sample modes are Point, 3 by 3 Median and 5 by 5 Median, and a table lists the minimum, maximum and mean of each channel. Use Median on any textured area, because a single point on grain gives a random value.'},
        {'heading': 'Finding and copying a material', 'body': 'Select Connected grows from the clicked pixel across touching similar pixels; Select All Similar finds every matching pixel on the car. Material tolerance runs from 0 to 64 with a default of 12. Copy M, R, CC and A copy the numbers, and Apply to Active Zone writes them as an override for the zone. Clear Zone Override undoes it.'},
        {'heading': 'The material readout', 'body': 'After a preview renders, the app also reports the material mix of the whole spec as a bar: percent glossy, metallic and matte, with plain warnings for flat or whitewashed settings, such as coat in the 1 to 15 dead band or a metal floor too low. Treat it as a quick check before you export.'},
    ],
    examples=[
        {'title': 'Copy the exact chrome from one part', 'goal': 'Match the chrome on a bumper to the hood.',
         'settings': {'SPEC TOOLS': 'Material Sampler', 'Sample mode': '3 by 3 Median', 'Tolerance': '12', 'Action': 'Copy M, R, CC, then Apply to Active Zone'},
         'result': 'The hood zone gets the same metal, roughness and coat as the bumper.'},
        {'title': 'Verify a matte', 'goal': 'Check a matte finish is truly matte.',
         'settings': {'Channel view': 'G', 'Sample mode': '5 by 5 Median'},
         'result': 'The roughness reads around 200 or more and the readout shows mostly matte.'},
    ],
    combos=[{'with': 'spec.reading_by_colour', 'why': 'Colour tells you the family; the Sampler tells you the number.'},
            {'with': 'spec.material_override_remap_lighting', 'why': 'Apply to Active Zone is an override.'}],
    faq=[
        {'q': 'Why does the same finish read different values?', 'a': 'Textured finishes vary. Use Median sampling and compare means.'},
        {'q': 'Is the Sampler changing my car?', 'a': 'Not until you press Apply to Active Zone.'},
        {'q': 'What tolerance should I use?', 'a': '12 is the default. Raise it to find broader areas.'},
        {'q': 'Does it show the preview or the export?', 'a': 'The preview spec. The export runs the same steps at full size.'},
    ],
    mistakes=[
        {'symptom': 'Values jump between clicks.', 'cause': 'Point sampling on a textured area.', 'fix': 'Switch to a Median size.'},
        {'symptom': 'Select All Similar grabbed too much.', 'cause': 'Tolerance too high.', 'fix': 'Lower it toward 12 or less.'},
    ],
    protips=['Sample the spot you like, copy the numbers, then recreate it with a base and sliders. You learn what makes it.',
             'Bright green in the spec colour views means rough, not shiny.'])

enrich(D, 'spec.angle_reveal', level='pro',
    sources=[W + ':3444-3466', W + ':3591-3631', 'docs/COLORSHOXX_ANGLE_REVEAL.md:1', W + ':4223', COMP + ':2625-2712],'.rstrip('],')],
    deep=[
        {'heading': 'The mechanism in three lobes', 'body': 'There is no true colour rotation in the sim. What exists is paint-tinted metal, environment-coloured clear coat and roughness gating. Metal at 176 to 255 keeps the reflection tinted with the paint hue even when the paint is nearly black. The clear coat is a separate, nearly white lobe that mirrors the environment: teal sky at one angle, gold sun or tarmac at another. Crushing the base colour removes the diffuse light, so only the two lobes remain and cells flip between dark and flash as the car turns.'},
        {'heading': 'What it needs to read', 'body': 'Two cell styles work: large coherent cells (the Ghost Shift recipe) and fine cells of 8 to 32 pixels whose channels disagree (the Fractured and ColorShoxx style). For the fine style use 6 to 8 crushed near-black shades (about 10 to 18 percent lightness) so metal cells cross lighting thresholds at different times. A single flat magenta carrier looks dead. Two routes work: a dark buried palette (any hue, best for warm, green and copper) or a bright cool base (blue, violet, magenta). Warm bright bases blend into warm sun and lose the second colour.'},
        {'heading': 'Where to judge it', 'body': 'Flash colours come from the track\'s sky and sun, so daytime tracks show them best and night or indoor lighting mutes them. Judge on the curved hood, roof and fenders, because a flat door can hold the base look longer. A good one reveals panel by panel, not the whole car at once, and survives shade, glare and replay distance.'},
    ],
    examples=[
        {'title': 'Ghost Shift recipe', 'goal': 'A dark red that flashes teal.',
         'settings': {'Base Material': 'A Ghost Geometry finish', 'Colour': 'Deep red', 'Brightness': 'Dragged far down', 'Track': 'Daytime'},
         'result': 'The body reads near black and flashes teal and gold as it turns.'},
        {'title': 'Any base, same trick', 'goal': 'Add the effect to a base you already like.',
         'settings': {'SPEC BLEND': 'Ghost Carve', 'Pattern': 'A coherent cell pattern', 'Colour': 'Crushed near black'},
         'result': 'Coat cells carve in on any finish while the metal keeps its tinted flash.'},
    ],
    combos=[{'with': 'spec.blend_modes', 'why': 'Ghost Carve and Angle Flip are the blend modes that build this effect.'},
            {'with': 'finishes.colorshoxx_and_shift', 'why': 'The finish families built on this idea.'},
            {'with': 'spec.metal_rough_grid', 'why': 'Fractured carriers sit in a corner of the grid with metal 242 to 255.'}],
    faq=[
        {'q': 'Can paint really change colour with the angle?', 'a': 'Not with a true shader. Colour-shift finishes fake it with paint plus spec.'},
        {'q': 'Why does the effect disappear at night?', 'a': 'The flash colours come from the sky and sun; night mutes them.'},
        {'q': 'Why dark colours?', 'a': 'A bright paint adds diffuse light that hides the two specular lobes.'},
        {'q': 'Does the preview show it?', 'a': 'The flat preview cannot show angle changes. Judge it in the sim on a daytime track.'},
    ],
    mistakes=[
        {'symptom': 'It reads as sparkle, not a shift.', 'cause': 'Pins or cells too large or all one shade.', 'fix': 'Use finer cells and 6 to 8 dark shades.'},
        {'symptom': 'The second colour never shows.', 'cause': 'A warm bright base blended into warm sun.', 'fix': 'Use a dark buried palette, or a cool bright base.'},
        {'symptom': 'Hot pink spec did not flip.', 'cause': 'Pink is only how the bytes pack. The effect needs spatial pattern, dark paint and lighting.', 'fix': 'Add the pattern and crush the paint.'},
    ],
    protips=['Offset the clear-coat structure from the metal structure so the two lobes peak at different angles.',
             'Judge on a daytime track and on the hood and fenders, not on a flat door.'])

enrich(D, 'spec.pattern_groups', level='beginner',
    sources=['js/spb-ai-atlas-data.js:2', 'js/spec-overlays/picker.js:60-85', AIK + '02_spec_and_finishes.md:17'],
    deep=[
        {'heading': 'How the 301 are organised', 'body': 'The picker sorts spec patterns into groups by what the texture does: sparkle and micro-metal, optical and interference, directional metal and brush, carbon and composite weave, clearcoat and coating, structure and geometry, surface and spray texture, weather and wear, machined hardware, and themed sets such as predator skins, voodoo, rising sun and let freedom ring. Source Pattern Plates is the largest group with 24 and matches the plate finishes of the same name.'},
        {'heading': 'Choosing by job', 'body': 'Want sparkle or flake: the Sparkle and Micro-Metal group. Want weave: Carbon and Composite Weave. Want brushed or machined: Directional Metal and Brush, Machined and Race Hardware. Want rainbow or oil film: Optical and Interference, or a holographic overlay over a pearl, metallic or chrome base. Want worn or weathered: Weather, Wear and Track plus a rougher base. Themed groups are loud, so lower strength before stacking another layer.'},
        {'heading': 'Every one changes shine only', 'body': 'Each spec pattern lists which channels it touches by default (M, R or C) and you can tick or untick them. Roughness only is the safest choice for subtle texture.'},
    ],
    examples=[
        {'title': 'Fine flake on anything', 'goal': 'Add depth to a plain colour.',
         'settings': {'Spec overlay': 'A micro-metal sparkle pattern', 'Strength': '30 to 50', 'Channels': 'M and R'},
         'result': 'Depth in sun, no change to colour.'},
        {'title': 'Holo effect', 'goal': 'Rainbow oil film on a reflective base.',
         'settings': {'Base Material': 'Pearl, Metallic or Chrome', 'Spec overlay': 'A holographic spec pattern from the Optical group'},
         'result': 'Shifting prismatic highlights on top of a reflective base.'},
    ],
    combos=[{'with': 'spec.overlays_stack', 'why': 'How to add and stack the patterns you find here.'},
            {'with': 'finishes.what_makes_a_finish_pop', 'why': 'A subtle flake at strength 30 to 50 is part of the make-it-pop recipe.'}],
    faq=[
        {'q': 'Which group first?', 'a': 'Sparkle and Micro-Metal and Carbon and Composite Weave are the safest first picks.'},
        {'q': 'Why do some groups look the same?', 'a': 'They are different names for related textures; compare them on the spec views.'},
        {'q': 'Can I search instead?', 'a': 'Yes. The picker has search.'},
        {'q': 'Do spec patterns match the paint patterns?', 'a': 'Source Pattern Plates match the plate finishes of the same name.'},
    ],
    mistakes=[
        {'symptom': 'A themed group looks too loud.', 'cause': 'Strength 50 is strong for a bold texture.', 'fix': 'Lower strength before adding a second layer.'},
        {'symptom': 'I cannot see the pattern.', 'cause': 'Spec patterns change shine only.', 'fix': 'Check the spec views and the sim.'},
    ],
    protips=['A holographic overlay needs a reflective base. On matte paint it has nothing to shimmer.',
             'Try the same pattern on R only, then on C only. The look changes more than the pattern does.'])
print('part C done')
