"""v3 depth for the playbook domain (lane C, 2026-10-04). Facts: docs/ai_knowledge/01_how_pro_works.md, 08_livery_design.md, 09_field_playbook.md (already cited in the articles)."""
V3 = {
 'playbook.colour_modes': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The four answers to "where does the colour come from"',
    'body': 'BASE COLOR decides it. Use source paint keeps the car\'s own colour and changes only the shine: perfect for gloss, matte, satin, pearl or candy over an existing livery. Solid paints the whole zone one colour. Gradient blends 2 to 10 colours in a direction. Finish colour lets chrome, carbon, holographic and similar finishes bring their own.'},
   {'heading': 'Gradients run across the whole sheet',
    'body': 'A gradient runs across the entire flat sheet, so a horizontal fade follows the sheet columns, not the length of the car. Panels do not line up. Give each panel its own zone if you want a fade per panel.'},
   {'heading': 'Colour replacement warning',
    'body': 'A finish that brings its own colour replaces your colour. If you want to keep your colours, use a coating base with source paint instead.'}],
  'examples': [
   {'title': 'Matte over an existing livery', 'goal': 'Change shine only',
    'settings': {'Base': 'A Foundation finish such as Soft Matte', 'BASE COLOR': 'Use source paint'},
    'result': 'The colours stay and only the shine changes.'},
   {'title': 'A fade on one side', 'goal': 'Blend two colours on the left side',
    'settings': {'Zone': 'Left side only', 'BASE COLOR': 'Custom gradient with 2 stops', 'Direction': 'Along the side'},
    'result': 'A fade on that side that does not run into other panels.'}],
  'faq': [
   {'q': 'Which mode keeps my paint colours?', 'a': 'Use source paint.'},
   {'q': 'How many colours can a gradient have?', 'a': '2 to 10 stops.'},
   {'q': 'Why does my fade not line up on the bumper?', 'a': 'A gradient covers the flat sheet, not the 3D car. Use one zone per panel.'},
   {'q': 'Why did chrome replace my colour?', 'a': 'A finish with its own colour replaces yours. Use a Foundation finish with source paint.'}],
  'mistakes': [
   {'symptom': 'Your livery turned plain silver', 'cause': 'A finish that brings its own colour was applied', 'fix': 'Undo and use a coating or Foundation base with Use source paint.'},
   {'symptom': 'A horizontal fade looks different on each side', 'cause': 'It follows sheet columns', 'fix': 'Use a zone per side or panel.'}],
  'protips': ['Decide the colour mode first. Most "it looks wrong" problems are a mode mismatch, not a bad finish.'],
 },
 'playbook.strengths_adjustments': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'The ranges',
    'body': 'Intensity runs 0 to 100 and sets the overall strength of the zone. Base Strength runs 0 to 200 percent: 100 replaces your paint fully and lower values let more of the original show. Spec Strength runs 0 to 200 percent and scales the shine map. Hue is -180 to 180, Saturation -100 to 100 and Brightness -100 to 200. Base Scale is 0.05 to 5 where 1.00 is normal. Scale and Rotation change the size and angle of the finish\'s own texture.'},
   {'heading': 'Size is not strength',
    'body': 'When someone says "crushed down to 50 percent" they mean texture scale, not strength. Changing strength when you meant size makes the finish weaker, not smaller.'},
   {'heading': 'The three spec sliders',
    'body': 'They push metal, roughness and clearcoat up or down for the whole zone. Large moves can cancel the finish: pick a better finish instead.'}],
  'examples': [
   {'title': 'Weaker finish', 'goal': 'Let more of the original paint show through',
    'settings': {'Base Strength': '60%'},
    'result': 'The finish replaces less of your paint.'},
   {'title': 'Finer texture', 'goal': 'Make the pattern smaller',
    'settings': {'Base Scale': '0.5', 'Judge in': 'Render'},
    'result': 'Finer detail. Fine detail does not show well in the small preview.'}],
  'faq': [
   {'q': 'What is the difference between Intensity and Base Strength?', 'a': 'Intensity is the overall strength of the zone (0 to 100). Base Strength is how much of the finish replaces your paint (0 to 200%).'},
   {'q': 'What does Base Scale 1.00 mean?', 'a': 'Normal size. Lower is finer, higher is larger (0.05 to 5).'},
   {'q': 'Do the popout percentages differ from the saved value?', 'a': 'No, they are the same number.'}],
  'mistakes': [
   {'symptom': 'The finish got weaker but not smaller', 'cause': 'Strength was lowered when scale was meant', 'fix': 'Use Base Scale instead.'},
   {'symptom': 'The finish disappeared after big spec moves', 'cause': 'Large spec slider moves cancel the finish', 'fix': 'Reset the sliders and choose a better finish.'}],
  'protips': ['Move one slider at a time and judge in Render. Several at once makes it impossible to know which one did it.'],
 },
 'playbook.hsb_sliders': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Tune the finish, do not swap it',
    'body': 'If a finish is almost right, move the three colour sliders instead of changing finish. Too dark or navy: Brightness up 30 to 40. Leaning violet: Hue down about 15 toward sky blue. Grey looking tinted: Saturation down about 10. Flecks gone grey after darkening: Saturation up.'},
   {'heading': 'Order matters a little',
    'body': 'Move Brightness first, then Hue, then Saturation, a little at a time, and check the preview after each move. Hue rotates every colour in the finish, not just one.'},
   {'heading': 'A real worked case',
    'body': 'A blue-white glow finish took Brightness plus 35, Hue minus 15 and Saturation minus 10 to reach a light ice blue and steel grey with no gradient.'}],
  'examples': [
   {'title': 'Ice blue from a blue-white glow finish', 'goal': 'Shift the palette without changing finish',
    'settings': {'Brightness': '+35', 'Hue': '-15', 'Saturation': '-10'},
    'result': 'Light ice blue and steel grey.'},
   {'title': 'Fix a navy look', 'goal': 'Lighten a finish that came out too dark',
    'settings': {'Brightness': '+30 to +40'},
    'result': 'The navy lifts toward the intended colour.'}],
  'faq': [
   {'q': 'Does Hue change only one colour?', 'a': 'No. It rotates every colour in the finish.'},
   {'q': 'What are the ranges?', 'a': 'Hue -180 to 180, Saturation -100 to 100, Brightness -100 to 200.'},
   {'q': 'What if I cannot reach the colour?', 'a': 'Try another finish and tune that one.'}],
  'mistakes': [
   {'symptom': 'The flecks went grey', 'cause': 'Brightness was lowered a lot', 'fix': 'Raise Saturation after darkening.'},
   {'symptom': 'Everything turned the wrong colour', 'cause': 'Hue moved too far', 'fix': 'Use small steps.'}],
  'protips': ['Start with Brightness; most "wrong colour" complaints are really "wrong lightness".'],
 },
 'playbook.gradients_and_flake': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Why gradients disappoint on a car',
    'body': 'Because the car is unwrapped, one fade does not continue from the side onto the bumper or the other side, and buyers notice. Use a gradient only for a deliberate whole-sheet effect, or give each panel its own zone and its own fade.'},
   {'heading': 'A touch of colour in black',
    'body': 'Use sparkles or flecks of that colour, not a gradient. A deep-space flake finish (black with blue, purple and silver flake) steered with Brightness about minus 45, Hue about minus 20 and Saturation about plus 60 gave roughly 55 percent pure black with blue flecks.'},
   {'heading': 'Patterns cannot do this job',
    'body': 'Paint patterns cannot take a colour in this way, and patterns with strong opacity flood the area instead of sparkling.'}],
  'examples': [
   {'title': 'Deep blue sparkle in black', 'goal': 'A mostly black car with blue flecks',
    'settings': {'Finish': 'A deep-space flake finish', 'Brightness': '-45', 'Hue': '-20', 'Saturation': '+60'},
    'result': 'About 55 percent pure black with blue flecks.'},
   {'title': 'Fade per panel', 'goal': 'A fade that looks right on each side',
    'settings': {'Zones': 'One per panel', 'Each': 'Its own gradient'},
    'result': 'Each panel fades on its own.'}],
  'faq': [
   {'q': 'Why does my gradient break at the bumper?', 'a': 'It lives on the flat sheet, not the 3D car.'},
   {'q': 'How do I get a little colour in black?', 'a': 'Use a flake finish with flecks of that colour.'},
   {'q': 'Can I add texture without changing colour?', 'a': 'Yes, add a spec pattern on top.'}],
  'mistakes': [
   {'symptom': 'The black turned fully coloured', 'cause': 'A high-opacity pattern flooded the area', 'fix': 'Use a flake finish instead.'},
   {'symptom': 'Flecks vanish after darkening', 'cause': 'Brightness lowered without Saturation', 'fix': 'Raise Saturation.'}],
  'protips': ['Check the result in Render at full size. Flecks are the first thing the small preview hides.'],
 },
 'playbook.buyer_words': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Words with a precise meaning',
    'body': 'Pattern size, thinner, bigger, smaller or crushed down means the zone\'s texture scale (0.05 to 5) and the spec pattern scale, not strength. A touch of colour in a dark area means flecks, not a fade. Same shade means sample the colour from the car instead of guessing a name. Keep the strokes means recolour only the fill colour with a tight tolerance and leave the outline colours alone.'},
   {'heading': 'Only the yellow',
    'body': 'Only the yellow in the logo means pick that colour, with a tolerance, on that art\'s layer inside a small box.'},
   {'heading': 'Starting over',
    'body': 'Starting from the base file means clean zones: reset them (Reset All Zones) rather than undoing many steps.'}],
  'examples': [
   {'title': 'Smaller pattern', 'goal': 'Make a pattern thinner',
    'settings': {'Control': 'Base Scale or the pattern Scale'},
    'result': 'The texture gets smaller without losing strength.'},
   {'title': 'Match the hood colour', 'goal': 'Same shade on the roof',
    'settings': {'Tool': 'PICK COLOR FROM CAR', 'Click': 'The hood'},
    'result': 'You get the real colour, not a guess.'}],
  'faq': [
   {'q': 'Does "make it smaller" change strength?', 'a': 'No. It changes scale.'},
   {'q': 'How do I recolour a fill without touching the outline?', 'a': 'Keep the tolerance low and pick only the fill colour.'},
   {'q': 'How do I go back to the base file?', 'a': 'Press Reset All Zones.'}],
  'mistakes': [
   {'symptom': 'The finish got weaker instead of smaller', 'cause': 'Strength was changed', 'fix': 'Use Base Scale.'},
   {'symptom': 'The outline colour changed', 'cause': 'Tolerance was too wide', 'fix': 'Lower the tolerance.'}],
  'protips': ['When describing a change to the helper, use these words. They map straight onto the right control.'],
 },
 'playbook.recolour_art_part': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Limit to the art layer',
    'body': 'Use a zone limited to the Numbers layer and the fill colour. Sample the real fill first: dark fills are often close to a black outline, so keep the tolerance around 10 to 16.'},
   {'heading': 'A colour inside one logo',
    'body': 'Combine the colour with a small box around the logo and limit the layers to the decal layers. Without the layer limit the box also grabs body paint whose original colour matches.'},
   {'heading': 'Check the outline',
    'body': 'Zoom the preview to confirm the outline and drop stroke survived. A wide tolerance eats the outline.'}],
  'examples': [
   {'title': 'New number fill colour', 'goal': 'Change only the fill of the numbers',
    'settings': {'Zone': 'PICK COLOR FROM CAR on the fill', 'RESTRICT TO LAYERS': 'Numbers only', 'Tolerance': '10 to 16'},
    'result': 'The fill changes and the outline stays.'},
   {'title': 'One colour in a logo', 'goal': 'Recolour yellow in a sponsor logo',
    'settings': {'Box': 'Small box around the logo', 'Layers': 'Decal layers only', 'Tolerance': 'Low'},
    'result': 'Only that logo changes.'}],
  'faq': [
   {'q': 'Why does the body also change?', 'a': 'The layer limit was off, so body paint of the same colour was caught.'},
   {'q': 'What tolerance should I use?', 'a': 'About 10 to 16 for dark fills near a black outline.'},
   {'q': 'Does this work on a flat paint?', 'a': 'Only by colour. A layered file is much better.'}],
  'mistakes': [
   {'symptom': 'The outline disappeared', 'cause': 'Tolerance too wide', 'fix': 'Lower it and check by zooming.'},
   {'symptom': 'Body paint changed too', 'cause': 'No layer limit', 'fix': 'Tick only the art\'s layer under RESTRICT TO LAYERS.'}],
  'protips': ['Sample the fill with PICK COLOR FROM CAR instead of guessing a name. Dark fills are easy to mistake for the outline.'],
 },
 'playbook.session_start': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Why guides lie',
    'body': 'Template layers can be on by default to show the panels, and they draw grids, outlines and fake headlights over the preview you are judging. With Mask off, the empty space between panels shows the base colour: that is not on the car, and iRacing never shows it.'},
   {'heading': 'Zone numbers move',
    'body': 'Zone numbers move when zones are added on top, so read the zone list top to bottom before editing and use names.'},
   {'heading': 'One page only',
    'body': 'If two different designs show on consecutive reads, two Shokker pages are open. Close the other one first.'}],
  'examples': [
   {'title': 'The three-step opener', 'goal': 'Start every session clean',
    'settings': {'1': 'Layers tab: Wire, Mask, Car Mandatory off', '2': 'Read the zone list', '3': 'Close extra Shokker windows'},
    'result': 'You judge the real preview.'},
   {'title': 'Empty space looks wrong', 'goal': 'Know what to ignore',
    'settings': {'Look at': 'Space between panels'},
    'result': 'It is not part of the car, whatever colour it shows.'}],
  'faq': [
   {'q': 'Why are there lines over my preview?', 'a': 'Wire or Mask is on. Turn it off.'},
   {'q': 'Why do I see two designs?', 'a': 'Two Shokker pages are open.'},
   {'q': 'Why does empty space have colour?', 'a': 'It shows the base colour with Mask off; iRacing never shows it.'}],
  'mistakes': [
   {'symptom': 'You fix things that are not wrong', 'cause': 'Template guides were on', 'fix': 'Turn them off before judging.'},
   {'symptom': 'Edits land on the wrong zone', 'cause': 'Zone numbers moved', 'fix': 'Re-read the list.'}],
  'protips': ['Make the guide-off routine a habit. It is the same four switches as the clean-render check.'],
 },
 'playbook.preview_cannot_show': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Small preview, big paint',
    'body': 'The live preview is much smaller than the real 2048 paint, so fine sparkle, micro-flake and small-scale patterns average out. Candy, chrome and metal twists are invisible in the flat colour preview, so confirm them on the spec views.'},
   {'heading': 'Reading the spec views',
    'body': 'Red is metal, green is roughness and blue is clearcoat, where high means dull. In one test a holographic drift finish at a small scale looked flat green in the spec view, yet measured clearly metal against plain gloss.'},
   {'heading': 'Do not delete on a hunch',
    'body': 'Do not conclude a finish did nothing from the small picture. Zoom a crop, read the spec views, or Render.'}],
  'examples': [
   {'title': 'Check a quiet finish', 'goal': 'Decide if it is really doing something',
    'settings': {'Views': 'R METAL, G ROUGH, B COAT', 'Compare': 'A plain gloss zone'},
    'result': 'You see the metal and roughness difference even if the colour looks flat.'},
   {'title': 'Zoom check', 'goal': 'See fine detail',
    'settings': {'Do': 'Zoom into a crop, then Render'},
    'result': 'Detail that averaged out in the small preview appears.'}],
  'faq': [
   {'q': 'Why does my sparkle finish look flat?', 'a': 'The small preview averages out fine sparkle. Render and zoom.'},
   {'q': 'What does high blue mean?', 'a': 'Dull clearcoat. Low blue is glossier.'},
   {'q': 'Where do I see what iRacing will light?', 'a': 'In the spec views.'}],
  'mistakes': [
   {'symptom': 'You removed a finish that was working', 'cause': 'The small picture looked flat', 'fix': 'Check the spec views before removing it.'},
   {'symptom': 'Chrome looks like plain paint', 'cause': 'The colour view cannot show a mirror', 'fix': 'Look at R METAL.'}],
  'protips': ['Compare with a plain gloss version of the same zone whenever a finish looks like nothing. If the spec views differ, it is working.'],
 },
 'playbook.things_to_avoid': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Undo after a manual reset',
    'body': 'Undoing many steps after you reset zones by hand can bring back an old state with dozens of zones. Mute or edit back instead, or press Reset All Zones.'},
   {'heading': 'Patterns that surprise',
    'body': 'The lightning paint pattern on matte black reads as grey cracked glass, not bolts, at any scale.'},
   {'heading': 'The space between panels',
    'body': 'The base colour of a scheme is limited to the paintable area, so once Mask is hidden the empty space keeps the old colour. That is harmless in iRacing.'},
   {'heading': 'Hidden values',
    'body': 'The zone list does not show scale or spec strength, so if you set a value by hand keep it in mind before a helper overwrites it. On some cars a part such as the spoiler has no body paint pixels, so schemes skip it.'}],
  'examples': [
   {'title': 'Go back safely', 'goal': 'Return to an earlier look',
    'settings': {'Do': 'Mute the zone or edit it back', 'Or': 'Reset All Zones'},
    'result': 'You avoid restoring dozens of old zones.'},
   {'title': 'Matte black with a pattern', 'goal': 'Pick a pattern that reads well',
    'settings': {'Avoid': 'Lightning', 'Try': 'A different pattern'},
    'result': 'The pattern reads as intended.'}],
  'faq': [
   {'q': 'Why did undo bring back dozens of zones?', 'a': 'You undid many steps after resetting by hand. Use Reset All Zones next time.'},
   {'q': 'Why is the spoiler skipped?', 'a': 'On some cars it has no body paint pixels.'},
   {'q': 'Why does the empty space keep an old colour?', 'a': 'It is outside the paintable area. It is harmless.'}],
  'mistakes': [
   {'symptom': 'An old state came back', 'cause': 'Many undo steps after a manual reset', 'fix': 'Reset All Zones instead.'},
   {'symptom': 'Helper overwrote your scale', 'cause': 'The zone list does not show scale', 'fix': 'Note hand-set values before asking the helper.'}],
  'protips': ['If you are going to try something risky, save a project first. Undo is for small steps, not for time travel.'],
 },
 'playbook.artwork_reveal': {
  'level': 'pro',
  'deep': [
   {'heading': 'Only the shine map changes',
    'body': 'The picture never changes. The whole art layer gets a soft matte base so shadows absorb light. Above it a second zone takes only the art\'s light tones (colours such as light grey, tolerance near 40) and gets a satin chrome.'},
   {'heading': 'What you see in the sim',
    'body': 'The light parts flash silver as the sun or track lights sweep, and the dark parts stay dead, so the shape appears out of the paint. Use mirror chrome instead of satin for a harder flash.'},
   {'heading': 'Order matters',
    'body': 'The upper zone must be above the matte one, because the top zone wins. Check the spec view: chrome (red) should sit only on highlights, matte on shadows. Make sure the same layer does not also hold light text, which would get chrome too.'}],
  'examples': [
   {'title': 'A hidden logo that flashes', 'goal': 'Reveal artwork only at certain light angles',
    'settings': {'Zone 2 (top)': 'Art layer, light tones at tolerance about 40, satin chrome Foundation finish', 'Zone 1 (below)': 'Art layer, soft matte Foundation finish', 'BASE COLOR': 'Use source paint on both'},
    'result': 'The picture is unchanged in colour and flashes silver on its light parts.'},
   {'title': 'Harder flash', 'goal': 'More contrast',
    'settings': {'Zone 2 finish': 'Mirror chrome'},
    'result': 'A sharper flash.'}],
  'faq': [
   {'q': 'Does this change my artwork colours?', 'a': 'No. Only the shine map changes.'},
   {'q': 'Why does my text also flash?', 'a': 'The same layer holds light text. Separate it.'},
   {'q': 'Which zone goes on top?', 'a': 'The chrome one.'}],
  'mistakes': [
   {'symptom': 'Nothing flashes', 'cause': 'The chrome zone is below the matte one', 'fix': 'Move the chrome zone above.'},
   {'symptom': 'The whole art flashes', 'cause': 'Tolerance too wide', 'fix': 'Lower it so only light tones are picked.'}],
  'protips': ['This is the cleanest way to give flat artwork depth: no colour change at all, only light.'],
 },
 'playbook.spec_only_changes': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Why Foundation finishes',
    'body': 'Foundation finishes (named Foundation or starting with f) are made to change the shine only. On real templates the paint changed 0 percent with Foundation finishes, and about 78 to 85 percent of a hood changed with ordinary chrome, metallic or candy.'},
   {'heading': 'The looks you can get',
    'body': 'Mirror chrome, satin chrome, dark chrome, polished metal, matte metal, pearl, satin pearl, candy, brushed metal, frosted, matte, satin and gloss. A finish that brings its own pattern can also be given a solid colour so you keep the colour flat and get only its texture in the shine map.'},
   {'heading': 'Stacking',
    'body': 'When stacking a chrome fill over gloss decals, keep the special fill zone above the decal gloss zone.'}],
  'examples': [
   {'title': 'Mirror chrome, keep colours', 'goal': 'Chrome shine on the hood without recolouring',
    'settings': {'Base': 'Chrome (mirror) from Foundation Bases', 'BASE COLOR': 'Use source paint'},
    'result': 'The preview colours are identical; the sim shows a mirror.'},
   {'title': 'Satin livery', 'goal': 'Make a gloss livery satin',
    'settings': {'Base': 'A Foundation satin finish', 'BASE COLOR': 'Use source paint'},
    'result': 'Same colours, softer shine.'}],
  'faq': [
   {'q': 'Why not use the normal chrome base?', 'a': 'It repaints the car. Foundation chrome keeps your colours.'},
   {'q': 'How do I confirm nothing changed in colour?', 'a': 'Compare the preview before and after.'},
   {'q': 'Can I fine-tune the shine?', 'a': 'Yes, with the three spec sliders.'}],
  'mistakes': [
   {'symptom': 'The hood changed colour', 'cause': 'An ordinary chrome, metallic or candy base was used', 'fix': 'Undo and use a Foundation finish with source paint.'},
   {'symptom': 'Chrome covers decals', 'cause': 'The special fill zone is below the decal zone', 'fix': 'Move it above.'}],
  'protips': ['If the request is "only the shine", the answer is always Foundation plus Use source paint.'],
 },
 'playbook.livery_parts': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Height bands on a side panel',
    'body': 'Height is measured from the roof-line (0) down to the rocker (1). 0.00 to 0.12 is the window edge; 0.10 to 0.25 the beltline, where a thin stripe separates body from glass; 0.30 to 0.65 the door centre where the number lives, so keep it calm; 0.64 to 0.70 a pinstripe above the lower band; 0.68 to 1.00 the lower body and rocker band, the classic place for the second colour.'},
   {'heading': 'Length along a side',
    'body': 'The front 22 percent of the length is the front fender and the rear 24 percent the rear quarter. Sides mirror each other, so one region can take both.'},
   {'heading': 'Work by named part',
    'body': 'A scheme is a base colour, one or two accents and a trim colour laid on named parts: two side panels, hood, roof, trunk, front and rear bumper and spoiler. Outside assistants refuse very large boxes, so name the part instead.'}],
  'examples': [
   {'title': 'Lower-band two-tone', 'goal': 'Put the second colour where it belongs',
    'settings': {'Part': 'Left side', 'Band': 'Height 0.68 to 1.00', 'Mirror': 'To the right side'},
    'result': 'A classic lower band on both sides.'},
   {'title': 'Calm number area', 'goal': 'Keep the number readable',
    'settings': {'Keep clear': 'Door centre, height 0.30 to 0.65'},
    'result': 'No busy stripes behind the number.'}],
  'faq': [
   {'q': 'Where does the number live?', 'a': 'Around the door centre, height 0.30 to 0.65.'},
   {'q': 'Where does the beltline stripe go?', 'a': 'At height 0.10 to 0.25.'},
   {'q': 'Why work by part, not by box?', 'a': 'Named parts are exact and boxes across the sheet may hit other panels.'}],
  'mistakes': [
   {'symptom': 'A stripe crosses the number', 'cause': 'It was placed in the door-centre band', 'fix': 'Move it to the beltline or the lower band.'},
   {'symptom': 'The assistant refuses a huge box', 'cause': 'Boxes over a small share of the sheet are refused', 'fix': 'Name the part.'}],
  'protips': ['The built-in design recipes already know these proportions. Use them to lay a whole scheme in one go, then adjust.'],
 },
 'playbook.scheme_families': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The six families',
    'body': 'Retro lower band: body colour, a bold lower band, a thin trim line above it, bumpers and spoiler in the band colour (Pepsi, Sunoco, Gulf style). Classic twin stripes: two parallel stripes along the sides continuing as a centre stripe over hood, roof and trunk. Two-tone: second colour from the belt down plus hood and bumpers. Colour block: hood, roof and rear quarters in different colours. Bookends: contrasting front and rear ends with a quiet body. Stealth: dark on dark with one thin accent.'},
   {'heading': 'Era palettes',
    'body': '1960s to 70s: powder blue and orange, navy and white, harvest orange, rust brown, mustard. 1970s to 80s: red, white and blue with chrome trim, black and gold, blue and yellow. 1980s: hot pink, cyan and purple on black or white. 1990s: teal, purple and magenta splashes. Modern: matte black with one accent, or white with one strong colour.'},
   {'heading': 'One twist only',
    'body': 'A twist on a retro scheme is one unexpected element: a candy or pearl panel, a flipped colour, a metallic roof. More than one makes the scheme look busy.'}],
  'examples': [
   {'title': 'Gulf-style retro', 'goal': 'Powder blue and orange lower band',
    'settings': {'Family': 'Retro lower band', 'Palette': '1960s to 70s powder blue and orange'},
    'result': 'A classic racing livery.'},
   {'title': 'Modern stealth', 'goal': 'A quiet, aggressive look',
    'settings': {'Family': 'Stealth', 'Palette': 'Matte black with one thin accent'},
    'result': 'Dark on dark with a single accent.'}],
  'faq': [
   {'q': 'Can Chat lay a whole scheme in one go?', 'a': 'Yes, the design recipes lay a scheme and you adjust.'},
   {'q': 'What is a twist?', 'a': 'One unexpected element, such as a candy panel or a metallic roof.'},
   {'q': 'Which palette is modern?', 'a': 'Matte black with one accent, or white with one strong colour.'}],
  'mistakes': [
   {'symptom': 'The scheme looks busy', 'cause': 'More than one twist', 'fix': 'Keep one.'},
   {'symptom': 'The era feels off', 'cause': 'Colours from different decades mixed', 'fix': 'Stay in one era palette.'}],
  'protips': ['Pick the family first, then the era. Family decides layout, era decides colour.'],
 },
 'playbook.composition_rules': {
  'level': 'beginner',
  'deep': [
   {'heading': '60-30-10',
    'body': 'One dominant colour (about 60 percent), one accent (about 30) and one trim (about 10). White or black as the quiet colour lets the accents sing.'},
   {'heading': 'Line things up',
    'body': 'The side band continues the bumper colour, and the hood stripe continues over the roof and trunk. Keep contrast between the number and its background, and do not run a busy stripe behind the numbers.'},
   {'heading': 'Finish choices',
    'body': 'Matte for flat paint, gloss for showroom, satin in between, chrome for trim lines (a chrome pinstripe on a matte car reads as real chrome). Metallic or candy blocks beside flat blocks create the pop through opposite colour and opposite shine. Never paint over numbers, sponsors or tape; use the body paint layers only.'}],
  'examples': [
   {'title': 'Modern retro', 'goal': 'Matte body with real-looking trim',
    'settings': {'Body': 'Matte', 'Trim': 'Chrome pinstripe', 'Hero block': 'Candy or metallic'},
    'result': 'A matte car with chrome lines and a single hero block.'},
   {'title': 'Showroom', 'goal': 'A glossy clean look',
    'settings': {'Finish': 'Gloss everywhere'},
    'result': 'A clean showroom look.'}],
  'faq': [
   {'q': 'How many colours should a scheme have?', 'a': 'One dominant, one accent and one trim.'},
   {'q': 'Why does my chrome stripe look fake?', 'a': 'Chrome reads as real against matte; against gloss it blends in.'},
   {'q': 'Can I paint over numbers?', 'a': 'No. Use the body paint layers only.'}],
  'mistakes': [
   {'symptom': 'The number is hard to read', 'cause': 'Low contrast or a busy stripe behind it', 'fix': 'Calm the door centre and raise contrast.'},
   {'symptom': 'The scheme feels flat', 'cause': 'No contrast in shine', 'fix': 'Put a metallic or candy block next to flat paint.'}],
  'protips': ['Opposite colour and opposite shine together make a block pop more than either alone.'],
 },
 'playbook.placement_wrong': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Say it by part and band',
    'body': 'When a stripe or block is in the wrong place, say which part and band you mean, such as the lower third of the left side. Do not guess new coordinates; that makes it worse.'},
   {'heading': 'Compare with what the zone covers',
    'body': 'Check the zone\'s covers text and its visible share, then change the part, portion or band. Say plainly which part you changed.'},
   {'heading': 'Unknown parts',
    'body': 'If a part of the car is not known, show it to Shokker once and it remembers.'}],
  'examples': [
   {'title': 'Move a stripe lower', 'goal': 'Fix a stripe that sits too high',
    'settings': {'Say': 'the lower third of the left side', 'Check': 'The zone card'},
    'result': 'The stripe moves to the band.'},
   {'title': 'Unknown part', 'goal': 'Fix a block on a part Shokker does not know',
    'settings': {'Do': 'Show the part once in the AI panel'},
    'result': 'Placement by name works from then on.'}],
  'faq': [
   {'q': 'Should I give coordinates?', 'a': 'No. Name the part and band.'},
   {'q': 'How do I see what a zone covers?', 'a': 'Open its card; it shows the covers text and visible share.'},
   {'q': 'What if the part is unknown?', 'a': 'Show it once and it is remembered.'}],
  'mistakes': [
   {'symptom': 'Corrections make it worse', 'cause': 'Coordinates were guessed', 'fix': 'Name the part and band.'},
   {'symptom': 'The block lands on a different panel', 'cause': 'The part is unknown', 'fix': 'Teach the part.'}],
  'protips': ['Use a fraction of a part ("the lower third of the left side"). It is more reliable than numbers.'],
 },
 'playbook.smart_separate_status': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'What the idea is',
    'body': 'For a flat paint with no layers, the app would work out what is a number, a sponsor, a logo, the fixed car template and the base paint, then build real layers so you can restrict a zone to them. It used a text-reading engine for numbers and sponsor words and a stored template for about 67 known cars.'},
   {'heading': 'Why it is not in the window',
    'body': 'It was judged not reliable enough to ship, so the page does not load it and no Auto-build layers button appears.'},
   {'heading': 'What to use today',
    'body': 'A layered PSD template gives real layers. Spec Sculpt has its own Auto-Separate for protecting decals while you sculpt the shine. On a flat paint, select numbers by colour with a zone and a medium tolerance.'}],
  'examples': [
   {'title': 'Protect decals while sculpting shine', 'goal': 'Keep numbers and sponsors untouched',
    'settings': {'Where': 'Spec Sculpt', 'Use': 'Auto-Separate'},
    'result': 'Decals are protected while you sculpt.'},
   {'title': 'Numbers on a flat paint', 'goal': 'Select numbers without layers',
    'settings': {'Zone': 'Pick the number colour', 'Tolerance': 'Medium'},
    'result': 'The numbers can be targeted by colour.'}],
  'faq': [
   {'q': 'Where is the Auto-build layers button?', 'a': 'It does not appear in this build.'},
   {'q': 'Is there another way to protect decals?', 'a': 'Yes, Spec Sculpt\'s Auto-Separate.'},
   {'q': 'How do I get real layers?', 'a': 'Open a layered PSD template.'}],
  'mistakes': [
   {'symptom': 'You search for a Smart Separate button', 'cause': 'It is not loaded in this build', 'fix': 'Use a layered file.'},
   {'symptom': 'Number colour edits spill onto the body', 'cause': 'The tolerance is too wide on a flat paint', 'fix': 'Lower it and check the preview.'}],
  'protips': ['If you often work from flat paints, ask the paint\'s author for the layered file. It saves more time than any workaround.'],
 },
}
