"""v3 depth for the recipes domain (lane C, 2026-10-04): complete worked builds with exact settings. Facts: docs/ai_knowledge/03_recipes.md, 08_livery_design.md, 09_field_playbook.md,
scripts/ai_atlas/ui_map.json, engine/SPEC_MAP_REFERENCE.md (all already cited in the articles). Values quoted here (Chrome 255/2/16, Satin Chrome 250/45/40, Wet Look 0/15/16, candy depth 0/15/65/100) come from those sources."""
V3 = {
 'recipes.matte_black': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Why the colour is set by hand',
    'body': 'A plain finish takes the colour you choose under BASE COLOR, while a finish that brings its own colour would ignore it. That is why Soft Matte (a plain foundation with zero sheen and zero texture) plus Use solid color is the clean way to get an exact black.'},
   {'heading': 'Matte in the shine views',
    'body': 'Matte reads bright in G ROUGH (roughness near 200) and the B COAT view should not be at 16, which is the glossiest. If the car looks too dead, Clear Satin gives a soft sheen, or keep the matte body and add gloss accents in a zone above it.'},
   {'heading': 'Order of zones',
    'body': 'A solid black zone under a chrome zone does nothing: the higher zone wins. Put the black zone where it is meant to apply.'}],
  'examples': [
   {'title': 'Deadest flat black', 'goal': 'The flattest possible black body, numbers untouched',
    'settings': {'Zone': '+ Add Zone, COLOR: Remaining', 'RESTRICT TO LAYERS': 'Car Paint', 'BASE': 'Foundation Bases > Flat Black', 'BASE COLOR': 'Use solid color, black', 'Then': 'RENDER, Ctrl+R in iRacing'},
    'result': 'A flat black body with the numbers and sponsors as they were.'},
   {'title': 'Matte with a little shape', 'goal': 'Black that still shows the body lines',
    'settings': {'BASE': 'Matte', 'BASE COLOR': 'Use solid color, 0a0a0a'},
    'result': 'A very dark grey that keeps a faint coat so it does not look dead.'},
   {'title': 'Keep your colours, make them matte', 'goal': 'Matte version of a livery',
    'settings': {'BASE': 'Soft Matte', 'BASE COLOR': 'Use source paint (spec only)'},
    'result': 'Colours unchanged, shine gone.'}],
  'faq': [
   {'q': 'Which matte should I pick?', 'a': 'Soft Matte is the plain foundation version, Matte keeps a faint coat, Flat Black is the deadest.'},
   {'q': 'How do I check it is matte?', 'a': 'Open G ROUGH under the preview: matte reads bright, with roughness near 200.'},
   {'q': 'Will it paint over my numbers?', 'a': 'Not if you tick Car Paint under RESTRICT TO LAYERS.'},
   {'q': 'Does matte black hide flaws?', 'a': 'It hides reflections, not flaws. Judge it in the sim.'}],
  'mistakes': [
   {'symptom': 'The black does not show', 'cause': 'A chrome or other zone above it wins', 'fix': 'Drag the black zone above it.'},
   {'symptom': 'The black is not black', 'cause': 'The finish brought its own colour', 'fix': 'Use a plain foundation and set BASE COLOR to Use solid color.'}],
  'protips': ['A very dark grey such as 0a0a0a often looks better than pure 000000 because the shape of the car still reads.'],
 },
 'recipes.chrome_source': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Spec only',
    'body': 'The ordinary chrome base repaints the zone silver. A Foundation finish is a pure spec: it writes the metal and roughness and keeps your colours, so your art, numbers and sponsors are not touched.'},
   {'heading': 'The numbers',
    'body': 'Chrome reads 255 metal, 2 roughness and 16 coat. Satin Chrome is 250 metal, 45 roughness and 40 coat. In the preview strip, R METAL should be bright red (about 255) and G ROUGH near black for mirror chrome. The colour preview barely moves; that is correct.'},
   {'heading': 'Dark paint under chrome',
    'body': 'In iRacing the paint under a metal part should be near white for chrome to read, so dark colours turn dark chrome. Lighten the colour, or choose Satin Chrome or Metallic. Flat chrome on an overcast track looks grey; that is the sky.'}],
  'examples': [
   {'title': 'Mirror-chrome hood, same paint', 'goal': 'Make one colour area mirror chrome',
    'settings': {'Zone': '+ Add Zone, PICK COLOR FROM CAR on the hood colour', 'BASE': 'Foundation Bases > Chrome (mirror)', 'BASE COLOR': 'Use source paint (spec only)', 'Check': 'R METAL about 255, G ROUGH near black'},
    'result': 'Colours identical in the preview; mirror metal in the sim.'},
   {'title': 'Softer chrome', 'goal': 'A satin metallic look over the whole livery',
    'settings': {'COLOR': 'Remaining', 'BASE': 'Satin Chrome', 'BASE COLOR': 'Use source paint (spec only)'},
    'result': 'Metal 250, roughness 45, coat 40 over the whole car, colours untouched.'}],
  'faq': [
   {'q': 'Why does my chrome look dark in the sim?', 'a': 'The paint under it is dark. Lighten the colour or use Satin Chrome or Metallic.'},
   {'q': 'Is the preview supposed to look unchanged?', 'a': 'Yes. A spec-only change barely moves the colour preview.'},
   {'q': 'Which other spec-only finishes exist?', 'a': 'Metallic, Pearl, Brushed and Clear Satin, among the Foundation finishes.'},
   {'q': 'Why is chrome grey on an overcast track?', 'a': 'It mirrors the sky. That is not a bug.'}],
  'mistakes': [
   {'symptom': 'The car became silver', 'cause': 'The plain Chrome base was used', 'fix': 'Use the Foundation Chrome with Use source paint.'},
   {'symptom': 'Chrome does not read', 'cause': 'Dark paint underneath', 'fix': 'Use a lighter colour, or Satin Chrome.'}],
  'protips': ['Look at R METAL first. If it is bright red where you want chrome, the recipe worked, whatever the colour preview says.'],
 },
 'recipes.retro_stripes': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Stripes are zones, not drawings',
    'body': 'Shokker is not a drawing program; it paints your template with materials. Stripes come from zones (a coloured area with a finish), from your template\'s own art, or from artwork you add as a layer. Numbers are not typed either: they exist in the template or you add them as a picture. There is no Text button; to add new lettering, place a transparent PNG with + Layer and move it with Move (V).'},
   {'heading': 'Fast way, by hand way',
    'body': 'Fast: type the look into Chat, for example "retro red white and blue stripes, flat with chrome trim", then refine with "thinner", "make the red orange" or "matte". By hand: one box zone per stripe on the hood, roof or side, a base such as Gloss, BASE COLOR set to Use solid color, then the Pinstripe or Chevron pattern with Paint mode on Blend so it keeps your stripe colour.'},
   {'heading': 'Order and direction',
    'body': 'Stripes must be above the body zone in the list so they win. One side of the sheet may be upside down relative to the other, so check the CAR view.'}],
  'examples': [
   {'title': 'Red, white and blue in Chat', 'goal': 'Get a retro stripe set in one sentence',
    'settings': {'Message': 'retro red white and blue stripes, flat with chrome trim', 'Refine': 'thinner, make the red orange, matte'},
    'result': 'A full stripe scheme you can undo step by step.'},
   {'title': 'One stripe by hand', 'goal': 'A red hood stripe',
    'settings': {'Zone': '+ Add Zone', 'APPLY AREA': 'Draw box along the hood', 'BASE': 'Gloss', 'BASE COLOR': 'Use solid color, red', 'List': 'Above the body zone'},
    'result': 'A red stripe along the hood.'},
   {'title': 'Recolour the template numbers', 'goal': 'Different number colour',
    'settings': {'Layers tab': 'Zone icon on the Numbers layer', 'BASE COLOR': 'Use solid color'},
    'result': 'The numbers change colour only.'}],
  'faq': [
   {'q': 'Can I type new numbers or text?', 'a': 'There is no Text button. Place a transparent PNG with + Layer instead.'},
   {'q': 'How many colours look good?', 'a': 'Three in a 60-30-10 split: one dominant, one accent, one trim.'},
   {'q': 'Why is my stripe hidden?', 'a': 'It is below the body zone in the list. Drag it above.'},
   {'q': 'Why does the stripe look backwards on one side?', 'a': 'One side of the sheet may be upside down. Check the CAR view and flip.'}],
  'mistakes': [
   {'symptom': 'The pattern replaced the stripe colour', 'cause': 'Paint mode was on Overlay', 'fix': 'Set Paint mode to Blend.'},
   {'symptom': 'Stripes do not line up across panels', 'cause': 'Each panel was drawn separately', 'fix': 'Line the bands up across the car; the side band continues the bumper colour.'}],
  'protips': ['Start in Chat to get the layout, then fix details by hand. It is far faster than building every stripe yourself.'],
 },
 'recipes.two_tone': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Six zones from top to bottom',
    'body': 'Zone 1 trim or stripes; Zone 2 hood; Zone 3 roof; Zone 4 trunk or rear deck; Zone 5 body; Zone 6 Everything Else at the bottom as the safety net for everything the others did not catch. Zones stack and the one higher in the list wins, so accents sit above the body.'},
   {'heading': 'Shine contrast',
    'body': 'Neighbours should differ in shine as well as colour: matte body with gloss accents, or satin body with chrome trim. Use matte beside gloss, or chrome beside dark. One dominant colour (about 60 percent), one accent (30), one trim (10).'},
   {'heading': 'Everything Else belongs at the bottom',
    'body': 'Everything Else above other zones steals their pixels. And more effects is not better: one hero area wins.'}],
  'examples': [
   {'title': 'Matte body, gloss accents', 'goal': 'A classic two-tone',
    'settings': {'Zone 1 trim': 'PICK COLOR FROM CAR on the stripe colour, BASE Gloss', 'Zones 2-4': 'Draw box over hood, roof, trunk, accent colour and finish', 'Zone 5 body': 'PICK COLOR FROM CAR on body colour, BASE Matte, Use source paint', 'Zone 6': 'Everything Else, last'},
    'result': 'A calm matte body with glossy accents.'},
   {'title': 'Satin and chrome', 'goal': 'A premium two-tone',
    'settings': {'Body': 'Satin', 'Trim': 'Chrome'},
    'result': 'Chrome trim lines pop against the satin body.'}],
  'faq': [
   {'q': 'Why six zones?', 'a': 'Each part gets its own look and the last one catches everything else.'},
   {'q': 'Where does Everything Else go?', 'a': 'At the very bottom.'},
   {'q': 'How do I keep the number readable?', 'a': 'Keep number and sponsor contrast strong; check the preview from a distance.'}],
  'mistakes': [
   {'symptom': 'Accent zones vanished', 'cause': 'Everything Else is above them', 'fix': 'Move it to the bottom.'},
   {'symptom': 'The livery looks busy', 'cause': 'Several hero effects', 'fix': 'Keep one hero area.'}],
  'protips': ['Look at the preview from a distance (zoom out) before rendering. Contrast problems hide up close.'],
 },
 'recipes.colour_shift': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'The finish brings its own colour',
    'body': 'Colour-shift (chameleon) finishes are built from a spec map and a colour field that shift with the light and your view, like real flip paint. There are many (Amethyst, Arctic, Phoenix, Galaxy and more). Leave BASE COLOR on Use finish\'s own color; a solid colour flattens it to one colour and loses the shift.'},
   {'heading': 'Recolouring',
    'body': 'Use Hue Shift (-180 to 180) plus Saturation and Brightness. The shift equals target hue minus current hue: +150 on green gives purple, not pink.'},
   {'heading': 'Judging it',
    'body': 'The flat colour preview shows one angle only. Look at the car in the sim under different light. The preview cannot show the angle change, so the sim is the only real check. Keep neighbouring zones calm (matte or satin, dark) so the shift is the hero.'}],
  'examples': [
   {'title': 'Amethyst flip body', 'goal': 'A purple colour-shift body, numbers safe',
    'settings': {'Zone': 'COLOR: Remaining', 'RESTRICT TO LAYERS': 'Car Paint', 'BASE': 'Chameleon Amethyst', 'BASE COLOR': 'Use finish\'s own color'},
    'result': 'The body changes colour with angle; numbers untouched.'},
   {'title': 'Change the family of hues', 'goal': 'Turn a green flip into purple',
    'settings': {'Hue Shift': '+150'},
    'result': 'Purple tones; use small steps to land on the hue you want.'}],
  'faq': [
   {'q': 'Why does it look like one colour in the preview?', 'a': 'The preview shows one angle only. Check in the sim.'},
   {'q': 'Can I set a solid colour on it?', 'a': 'You can, but it flattens the shift. Use Hue Shift instead.'},
   {'q': 'What goes beside it?', 'a': 'A dark satin or matte body zone so the shift stands out.'}],
  'mistakes': [
   {'symptom': 'The shift disappeared', 'cause': 'BASE COLOR was set to a solid colour', 'fix': 'Return it to the finish\'s own colour.'},
   {'symptom': 'Numbers are hard to read', 'cause': 'Colour shift or sparkle sits behind them', 'fix': 'Restrict the zone to Car Paint.'}],
  'protips': ['The flat preview cannot show an angle change. Judge colour-shift finishes in the sim on a daytime track; the R METAL, G ROUGH and B COAT views show the spec behind the effect.'],
 },
 'recipes.carbon_hood': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Size is everything',
    'body': 'On a whole-car sheet a normal weave looks like a fishing net. Go smaller (pattern scale below 1.0, try 0.5) and put the weave only on the part you want so the rest of the car stays calm.'},
   {'heading': 'Two routes',
    'body': 'Hardware: Carbon Handguard is a glossy twill weave under resin and Carbon Twill Weave is semi-matte; the weave is the finish. Or use a plain dark base plus the Carbon Fiber pattern (classic 2 by 2 twill) with Paint mode on Blend so it keeps the dark base. Base Scale does the same job for a base with its own weave.'},
   {'heading': 'Depth',
    'body': 'A spec overlay such as Carbon Wet Layup adds resin depth and changes shine only. The colour preview cannot show clearcoat depth; check B COAT.'}],
  'examples': [
   {'title': 'Fine carbon hood', 'goal': 'A believable carbon bonnet',
    'settings': {'APPLY AREA': 'Draw box around the hood', 'BASE': 'Carbon Fiber under Foundation Bases', 'PATTERN': 'Carbon Fiber', 'Paint mode': 'Blend', 'Scale (pattern)': '0.5'},
    'result': 'A fine weave on the hood only.'},
   {'title': 'Stealth carbon', 'goal': 'OEM-looking carbon',
    'settings': {'BASE': 'Carbon Satin', 'Neighbour': 'A gloss accent next to the hood so the weave reads'},
    'result': 'A subtle satin weave.'}],
  'faq': [
   {'q': 'What scale looks good?', 'a': 'Try 0.5. At 1.0 the weave looks big on a car.'},
   {'q': 'Pattern or base?', 'a': 'Either: a carbon base such as Carbon Twill Weave carries its own weave; a dark base plus the pattern gives control.'},
   {'q': 'How do I check it?', 'a': 'Render and look at 100 percent zoom, not the fit-to-window view.'}],
  'mistakes': [
   {'symptom': 'The weave looks like a net', 'cause': 'Scale at 1.0 or higher', 'fix': 'Lower Scale to about 0.5.'},
   {'symptom': 'The base colour vanished', 'cause': 'Paint mode was Overlay', 'fix': 'Set it to Blend.'}],
  'protips': ['Put carbon only on a few panels (hood, roof, splitter). Carbon everywhere reads as a texture, not as a material.'],
 },
 'recipes.candy': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Why candy looks deep',
    'body': 'Light passes through tinted clear and bounces off bright metal underneath. Pale or metallic grounds make candy glow; dark flat ones make it look black.'},
   {'heading': 'The three controls',
    'body': 'Color Depth: 0 is no tint, 15 a glaze, 65 rich (the default), 100 the deepest. Color Flip (0 to 355 degrees) adds a second hue at an angle (90 neighbouring, 180 opposite). Underglow (0 to 100 percent) lets the ground coat burn through the brights. They only show on candy-like finishes.'},
   {'heading': 'Checking',
    'body': 'In the preview strip G ROUGH low means glassy and B COAT at 16 is the deepest coat. For a named candy colour such as gold, lime or aqua, pick Candy and choose that colour yourself.'}],
  'examples': [
   {'title': 'Deep red candy', 'goal': 'A rich candy apple body',
    'settings': {'BASE': 'Candy', 'BASE COLOR': 'Use solid color, deep red', 'Color Depth': '65 (or 100 for deepest)', 'Spec overlay': 'Gold Flake or Pearl Micro'},
    'result': 'A deep, glowing red with sparkle.'},
   {'title': 'Two-hue candy', 'goal': 'A second colour at an angle',
    'settings': {'Color Flip': '90 for a neighbouring hue, 180 for the opposite'},
    'result': 'The second hue appears at an angle.'}],
  'faq': [
   {'q': 'Which colours work best?', 'a': 'Deep red, cobalt and emerald.'},
   {'q': 'Why does my candy look black?', 'a': 'A dark flat ground. Use a bright metallic ground.'},
   {'q': 'Do depth and flip work on any finish?', 'a': 'No, only on candy-like finishes.'}],
  'mistakes': [
   {'symptom': 'Candy looks like plain paint', 'cause': 'Color Depth is near 0', 'fix': 'Raise it toward 65.'},
   {'symptom': 'Candy is hard to read behind numbers', 'cause': 'It sits next to a busy pattern', 'fix': 'Keep candy away from busy patterns near the number.'}],
  'protips': ['Candy and a complementary neighbour read from far away. Pair a deep red candy with a quiet satin cream.'],
 },
 'recipes.edit_one_thing': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Layers keep decals safe',
    'body': 'Sponsors and numbers sit on their own layers of a layered template, so a zone limited to the body layer (for example Car Paint) never reaches them. Chat follows the same rule: it never touches numbers, sponsors or logos unless you name them, and every change has an Undo.'},
   {'heading': 'Flat paints',
    'body': 'Without layers, use PICK COLOR FROM CAR on the body colour with a tolerance of 30 to 45, or Draw box around the body panels. Use Exclude Region to cut out a logo.'},
   {'heading': 'If numbers look wrong afterwards',
    'body': 'If a special finish makes numbers sparkle or dull, open Spec Tools > Decal Rescue Kit and choose Flat Vinyl, Satin Decal or Gloss Decal.'}],
  'examples': [
   {'title': 'Body only', 'goal': 'Change the body and leave the rest',
    'settings': {'Zone': '+ Add Zone', 'RESTRICT TO LAYERS': 'Car Paint only', 'BASE / COLOR': 'The colour and finish you want'},
    'result': 'Numbers, tape and logos are unchanged.'},
   {'title': 'Ask Chat', 'goal': 'Same job in one sentence',
    'settings': {'Message': 'change the body but leave the numbers alone'},
    'result': 'The helper restricts the change; press Undo under the reply if it is wrong.'}],
  'faq': [
   {'q': 'Which layer is the body?', 'a': 'Look in the Layers tab; it is often named Car Paint or Body.'},
   {'q': 'What does Everything or Remaining touch?', 'a': 'Every layer unless you restrict it.'},
   {'q': 'Can Chat change the numbers?', 'a': 'Yes, if you name them.'}],
  'mistakes': [
   {'symptom': 'Numbers got a whole-car finish', 'cause': 'No layer restriction and a finish with its own colour', 'fix': 'Tick only the body layer under RESTRICT TO LAYERS.'},
   {'symptom': 'Numbers sparkle behind metal', 'cause': 'Metal spec under stamped numbers', 'fix': 'Use Decal Rescue Kit.'}],
  'protips': ['Select logos and numbers by layer name for exact edges; use colour only for large flat areas.'],
 },
 'recipes.camo': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Two routes',
    'body': 'The pattern route puts the Camo design (digital splinter camo) on any base and is the most controllable. The finish route uses a camo finish that brings its own palette (woodland, desert, flecktarn, urban digital, Multicam Transition and more): it looks right at once, but you recolour it with Hue Shift, not a solid colour.'},
   {'heading': 'Paint mode matters',
    'body': 'In Overlay mode the pattern\'s own colours win and your base colour is hidden. Blend keeps your base colour. Use Opacity to taste.'},
   {'heading': 'Size',
    'body': 'Make the blocks smaller with Scale (pattern), for example 0.5, so the camo breaks up across the whole car. Camo reads best on matte, cerakote or blackout bases; stack a second base from OVERLAYS for a sheen difference between the blocks.'}],
  'examples': [
   {'title': 'Blackout camo', 'goal': 'Subtle dark camo',
    'settings': {'RESTRICT TO LAYERS': 'Car Paint', 'BASE': 'Matte or Flat Black', 'PATTERN': 'Camo', 'Paint mode': 'Blend', 'Scale (pattern)': '0.5'},
    'result': 'A quiet camo that breaks up over the whole car.'},
   {'title': 'Ready-made woodland', 'goal': 'Fast and authentic',
    'settings': {'Base Material': 'M81 Woodland', 'BASE COLOR': 'Use finish\'s own color', 'Recolour': 'Hue Shift, Saturation, Brightness'},
    'result': 'A woodland camo you can tint.'}],
  'faq': [
   {'q': 'Why do I lose my base colour?', 'a': 'Paint mode is Overlay. Switch to Blend.'},
   {'q': 'Can I use a solid colour on a camo finish?', 'a': 'No, it flattens the pattern. Use Hue Shift.'},
   {'q': 'What base looks best?', 'a': 'Matte, cerakote or blackout.'}],
  'mistakes': [
   {'symptom': 'Camo looks huge', 'cause': 'Scale at 1.0', 'fix': 'Lower to about 0.5.'},
   {'symptom': 'The pattern vanished after recolouring', 'cause': 'A solid colour was set', 'fix': 'Go back to the finish\'s own colour and use Hue Shift.'}],
  'protips': ['Check camo from a distance. Pattern scale is judged by how it reads at track distance, not up close.'],
 },
 'recipes.gradient_roof_rocker': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Roof at the top, rocker at the bottom',
    'body': 'On the side panels the top of the sheet is the roof line and the bottom is the rocker, so a vertical gradient inside a box around a side panel fades roof to rocker. Several islands share the same columns, which is why one zone per side is the safe way.'},
   {'heading': 'Directions and stops',
    'body': '2 to 10 stops. Six directions: horizontal, vertical, diagonal down, diagonal up, radial and angular. Colour Scale (0.05x to 5x) and Colour Rotation (0 to 355 degrees) zoom or rotate the gradient. If a side of the sheet is upside down, reverse the stops or pick the other vertical direction.'},
   {'heading': 'Colours',
    'body': 'Gradient stops use true colours (gold is about d4a017, deep blue 0a3fd6). On a zone that only covers some colours, the gradient shows only on those colours.'}],
  'examples': [
   {'title': 'Blue to gold on the left side', 'goal': 'A roof-to-rocker fade',
    'settings': {'APPLY AREA': 'Draw box around ONE side panel', 'BASE': 'Gloss, Candy, Pearl or Metallic', 'BASE COLOR': 'Custom gradient', 'Stops': 'Deep blue 0a3fd6 to gold d4a017', 'Direction': 'Vertical'},
    'result': 'A fade from roof to rocker on that side.'},
   {'title': 'Other side', 'goal': 'Match the right side',
    'settings': {'Zone': 'A second zone with its own box', 'If upside down': 'Reverse the stops'},
    'result': 'The right side fades the same way.'}],
  'faq': [
   {'q': 'Why one zone per side?', 'a': 'Islands share columns on the flat sheet; one zone per side fades each properly.'},
   {'q': 'Can I ask Chat?', 'a': 'Yes: "a gradient from blue to gold to white" sets the stops.'},
   {'q': 'Why does it cover the roof and hood too?', 'a': 'Without a box the gradient runs over the whole sheet.'}],
  'mistakes': [
   {'symptom': 'The right side fades the wrong way', 'cause': 'That side of the sheet is upside down', 'fix': 'Reverse the stops or use the other vertical direction.'},
   {'symptom': 'A horizontal fade ignores the car\'s length', 'cause': 'It follows sheet columns', 'fix': 'Use a vertical fade per side.'}],
  'protips': ['Check the CAR view, not the flat sheet, to judge a gradient. The flat sheet misleads.'],
 },
 'recipes.flake_pearl': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Flake versus pearl',
    'body': 'Flake and pearl are small particles in clear. Flake is bold and sparkly; pearl is a soft colour-shifting sheen. Both depend on fine detail, so keep the particles small on a whole-car sheet. Large flake on a whole car looks like gravel.'},
   {'heading': 'Choices',
    'body': 'Bases: Chunky Metalflake (heavy visible flake), Holo Flake (rainbow flake) or Micro Glitter (fine sparkle) from the Foundation EFX shelf, or Pearl (Foundation) for a softer sheen. Spec overlays (BASE > SPEC OVERLAYS > + ADD SPEC OVERLAY): Gold Flake, Holographic Flake or Pearl Micro. Opacity 30 to 50 gives subtle depth; heavy flake looks loud.'},
   {'heading': 'Blue in the black',
    'body': 'For a coloured sparkle in a dark area, choose flecks of that colour, not a gradient. Spec overlays do not show in the colour preview: check the spec views and the sim.'}],
  'examples': [
   {'title': 'Subtle gold flake', 'goal': 'Expensive-looking sparkle',
    'settings': {'BASE': 'Pearl (Foundation)', 'BASE COLOR': 'Use solid color', 'Spec overlay': 'Gold Flake, Strength 40', 'Scale': 'Lowered until fine on the car'},
    'result': 'A fine sparkle that glints at an angle to the sun.'},
   {'title': 'Keep the livery, add sparkle', 'goal': 'Flake over existing art',
    'settings': {'BASE': 'Metal Flake', 'BASE COLOR': 'Use source paint (spec only)'},
    'result': 'The art stays; the flake rides in the shine.'}],
  'faq': [
   {'q': 'Why can I not see the sparkle in the preview?', 'a': 'Spec overlays do not show in the colour preview. Check the spec views and the sim.'},
   {'q': 'What opacity should I use?', 'a': '30 to 50 percent for a subtle, expensive look.'},
   {'q': 'Why does the flake look like gravel?', 'a': 'Scale is too large. Lower it.'}],
  'mistakes': [
   {'symptom': 'Flake is too loud', 'cause': 'High opacity', 'fix': 'Drop to 30 to 50.'},
   {'symptom': 'No sparkle in iRacing', 'cause': 'Judged only in the preview', 'fix': 'Render and look at an angle to the sun.'}],
  'protips': ['Judge flake in the sim at an angle to the sun. It is the only honest test.'],
 },
 'recipes.flames_graphics': {
  'level': 'beginner',
  'deep': [
   {'heading': 'A flame is a finish',
    'body': 'Flame finishes bring their own colours and shapes, so they are a complete graphic rather than a material: Hot Rod Flames (orange and yellow on black), True Fire, Blue Flame, Purple Flame, Green Fire or Ghost Flames (tonal). Limit them to the area you want with a box zone and keep the rest calm.'},
   {'heading': 'Recolouring and edges',
    'body': 'Leave BASE COLOR on Use finish\'s own color; a solid colour makes one flat colour and loses the flames. Use Hue Shift to change the colour. For the classic flame-lapped edges add the Flame Lapped Clearcoat spec overlay, which adds glossy edges without changing the colour.'},
   {'heading': 'Lightning and stripes',
    'body': 'They are patterns you add on top: the Lightning pattern on a chrome, candy or very dark base, with a lower Scale for finer bolts. Flames are drawn on the flat sheet; check they land on the right part.'}],
  'examples': [
   {'title': 'Hot rod hood flames', 'goal': 'Classic flames on the bonnet',
    'settings': {'APPLY AREA': 'Draw box around the hood', 'Base Material': 'Hot Rod Flames', 'BASE COLOR': 'Use finish\'s own color', 'List': 'Above the body zone'},
    'result': 'Orange and yellow flames on a black hood.'},
   {'title': 'Blue flames', 'goal': 'A cooler flame',
    'settings': {'Base Material': 'Blue Flame or Hue Shift on Hot Rod Flames'},
    'result': 'Blue flame tones.'}],
  'faq': [
   {'q': 'Why did my flames turn into one flat colour?', 'a': 'A solid colour was set on the flame finish.'},
   {'q': 'Can I keep flames off the numbers?', 'a': 'Yes, box the zone or restrict it to a layer.'},
   {'q': 'How do I get glossy flame edges?', 'a': 'Add the Flame Lapped Clearcoat spec overlay.'}],
  'mistakes': [
   {'symptom': 'Flames land on the wrong part', 'cause': 'They are drawn on the flat sheet', 'fix': 'Check the CAR view and redraw the box.'},
   {'symptom': 'Flames hide the number', 'cause': 'The zone covers the number panel', 'fix': 'Keep flames away from number panels.'}],
  'protips': ['Flames read best on a clean dark or solid body with plenty of contrast.'],
 },
 'recipes.mirror_side': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Three ways to mirror',
    'body': 'For artwork on a layer, click MIRROR on the layer card: a flipped copy is made for the opposite side. For a zone area, use Mirror in the selection bar, or Mirror Mask in the toolbar MASK menu, which flips the zone mask horizontally. For finishes only, make one zone per side with Draw box around each panel and give both the same colour and finish.'},
   {'heading': 'Why it can land wrong',
    'body': 'The two sides sit on the flat sheet as separate panels, and the layout does not always put them the same way up. A mirrored copy can land rotated, and text may read backwards on one island. Use FLIP or ROT 90 on the copy until it matches.'},
   {'heading': 'Asymmetric logos',
    'body': 'If an asymmetric logo must read correctly on both sides, mirror, then FLIP the copy back.'}],
  'examples': [
   {'title': 'Mirror a decal to the other side', 'goal': 'Sponsor on both doors',
    'settings': {'Layers tab': 'MIRROR on the layer card', 'If upside down': 'FLIP or ROT 90', 'Check': 'CAR view'},
    'result': 'The decal appears on the opposite side and reads correctly.'},
   {'title': 'Same finish on both sides', 'goal': 'A symmetric stripe finish',
    'settings': {'Zones': 'One per side with Draw box', 'Colour and finish': 'Identical'},
    'result': 'Both sides match and are easy to adjust later.'}],
  'faq': [
   {'q': 'Why is my mirrored logo upside down?', 'a': 'The two sides are not placed the same way up. Use FLIP or ROT 90.'},
   {'q': 'Do both panels sit the same on every car?', 'a': 'No. Check the CAR view.'},
   {'q': 'Easier for symmetric designs?', 'a': 'Yes, one zone per side is easier to adjust.'}],
  'mistakes': [
   {'symptom': 'Text reads backwards on one side', 'cause': 'Mirror flips the text', 'fix': 'FLIP the copy back.'},
   {'symptom': 'You trusted the flat picture', 'cause': 'The flat picture does not show the 3D car', 'fix': 'Check the CAR view.'}],
  'protips': ['For anything with text, mirror first and then flip the text back. It takes seconds and avoids backward sponsors.'],
 },
 'recipes.match_photo': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'What it can do offline',
    'body': 'Shokker cannot trace a photo into paint by itself offline. It can match colours exactly and build zones with real finishes. Pick Color (P) captures a colour from your SOURCE paint; + Add Color adds it to a zone, Set replaces it. For a colour from the photo, type its hex in the zone HEX box.'},
   {'heading': 'With an AI',
    'body': 'In Chat press the paper-clip (Attach a picture), choose the livery, logo or flag, and ask it to copy the design or the colours. This needs an online AI key or the Claude and ChatGPT connection; offline Chat cannot read pictures. Say "same shade as the hood" to sample from your own car.'},
   {'heading': 'Keep it simple',
    'body': 'Use a limited palette of two or three colours plus one accent; five colours look cheap. A photo shows lighting; match the paint colour, not the shadows.'}],
  'examples': [
   {'title': 'Eyedropper match', 'goal': 'Copy a reference livery by hand',
    'settings': {'Step 1': 'Reference next to the preview', 'Step 2': 'One zone per colour area', 'Step 3': 'Hex of each colour typed in the HEX box', 'Step 4': 'Matching finish per zone (matte, gloss, satin, chrome, candy)'},
    'result': 'A close match built from real zones.'},
   {'title': 'Let the AI propose it', 'goal': 'A first draft from a picture',
    'settings': {'Chat': 'Paper-clip, attach the picture', 'Ask': 'copy the colours of this livery', 'Needs': 'An AI key or Claude / ChatGPT'},
    'result': 'Zones and colours appear; refine with words.'}],
  'faq': [
   {'q': 'Can offline Chat read pictures?', 'a': 'No. It needs an online AI key or the Claude / ChatGPT connection.'},
   {'q': 'How do I get an exact colour?', 'a': 'Use Pick Color (P) on your paint or type a hex.'},
   {'q': 'Why do my colours look different from the photo?', 'a': 'Photos show lighting. Match the paint colour, not the shadows.'}],
  'mistakes': [
   {'symptom': 'Too many colours', 'cause': 'Five or more colours', 'fix': 'Limit to two or three plus an accent.'},
   {'symptom': 'Colours match but the look is wrong', 'cause': 'The finish is wrong', 'fix': 'Pick the right shine (matte, gloss, satin, chrome, candy).'}],
  'protips': ['Match the finish before the colour. Gloss versus matte changes how a colour reads more than a small hue difference.'],
 },
 'recipes.night_day': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'iRacing has one paint per car',
    'body': 'Shokker has no automatic day and night switch because iRacing does not read one. Keep two looks side by side, one bright for day and one darker or more reflective for night, and render the one you want before the session.'},
   {'heading': 'Naming and keeping',
    'body': 'The newest render overwrites the paint in the car folder, and Shokker keeps only the two newest renders in its own folder. Press Save to keep on the render card so each render gets its own folder, and name the projects separately (for example livery night). Two renders with the same name replace each other.'},
   {'heading': 'Making the night version',
    'body': 'Change colours (Hue Shift, Saturation, Brightness, or new solid colours) and swap to darker bases with brighter accents. Reflective finishes and flake catch light better at night.'}],
  'examples': [
   {'title': 'A day and a night version', 'goal': 'Two renders from one design',
    'settings': {'Day': 'Save / Open > Save, RENDER, Save to keep', 'Night': 'Hue Shift or darker bases, RENDER, Save to keep', 'Names': 'livery day, livery night'},
    'result': 'Two projects and two kept renders.'},
   {'title': 'Before a session', 'goal': 'Load the right one',
    'settings': {'Do': 'Open the project, RENDER, Ctrl+R in iRacing'},
    'result': 'The car shows the version you picked.'}],
  'faq': [
   {'q': 'Can iRacing switch day and night automatically?', 'a': 'No. It reads one paint per car.'},
   {'q': 'How do I bring back an older version?', 'a': 'Open the project, or click an old thumbnail in Render History.'},
   {'q': 'Why did my day paint disappear?', 'a': 'A newer render replaced the file in the car folder.'}],
  'mistakes': [
   {'symptom': 'Day paint overwritten', 'cause': 'A new render replaced the file', 'fix': 'Use Save to keep before the next render.'},
   {'symptom': 'Variants overwrite each other', 'cause': 'Same name', 'fix': 'Name projects and renders differently.'}],
  'protips': ['Share Recipe gives you a light copy of each variant, which is easier to store than full projects.'],
 },
 'recipes.team_liveries': {
  'level': 'pro',
  'deep': [
   {'heading': 'Build once, reuse',
    'body': 'Build the scheme on your first car. In the left column press More > Save as Template, name it (60 characters at most) and Save. Open the next car\'s template and choose your layout from Load Template... in the same menu. Fleet batch rendering (Add Car, Render All Cars) exists in the code but is disabled in this build, so teams work car by car.'},
   {'heading': 'What transfers',
    'body': 'Cars with similar templates share part names, so layouts transfer cleanly. Use layer names (Car Paint, Numbers) rather than colours. Colour regions picked from the first car may need to be re-picked with PICK COLOR FROM CAR on the new car.'},
   {'heading': 'Sharing and IDs',
    'body': 'After RENDER use Share Recipe on the recipe card; a teammate loads it with Import Recipe in the top toolbar. A recipe carries the look, not the car template. Each driver needs files named with their own Customer ID, so put their ID in the box before rendering.'}],
  'examples': [
   {'title': 'Three cars, one livery', 'goal': 'Reuse the layout across a team',
    'settings': {'Car 1': 'Build, More > Save as Template', 'Car 2 and 3': 'Open template, Load Template..., re-pick colours, set the driver\'s ID', 'Each': 'RENDER'},
    'result': 'Three cars with the same scheme and each driver\'s own file names.'},
   {'title': 'Share with a teammate', 'goal': 'Send the look only',
    'settings': {'You': 'Share Recipe', 'Teammate': 'Import Recipe'},
    'result': 'The look appears on their car; they may need to re-pick colours.'}],
  'faq': [
   {'q': 'Is there a batch render for a team?', 'a': 'Not in this build. Teams render car by car.'},
   {'q': 'How long can a template name be?', 'a': '60 characters.'},
   {'q': 'Do I put my ID or the driver\'s?', 'a': 'The driver\'s own Customer ID for their files.'}],
  'mistakes': [
   {'symptom': 'The loaded layout looks wrong', 'cause': 'Colour regions were picked from the first car', 'fix': 'Re-pick them with PICK COLOR FROM CAR.'},
   {'symptom': 'A teammate\'s paint does not load in iRacing', 'cause': 'Files named with the wrong Customer ID', 'fix': 'Render with their ID in the box.'}],
  'protips': ['Use layers, not colours, to pick areas. A layer-based template works on every car with the same layer names.'],
 },
 'recipes.wet_glass': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Wet look in numbers',
    'body': 'Wet Look is metal 0, roughness 15 and coat 16: the tightest highlight a non-metal paint can have. It comes from low roughness and the glossiest clearcoat.'},
   {'heading': 'Glass finishes',
    'body': 'Glass looks put clear colour over the paint: Cathedral Veil lays leaded glass panes in your colour, Shag: Smoked Glass is a bronze tint and Glass Flake suspends glass shards in clear; for a plain gem glass use Wet Look and pick the colour yourself. They are paint looks: the car\'s windows do not become transparent because window glass keeps the template\'s alpha.'},
   {'heading': 'Extra realism',
    'body': 'A Wet Zone spec overlay (CC Wet Zone) adds slightly uneven glossy clear patches that read like real wet clear. A glossy car is a mirror for the track, and mirror-level gloss shows every flaw in your art.'}],
  'examples': [
   {'title': 'Wet-look body', 'goal': 'A razor-sharp lacquer gloss',
    'settings': {'RESTRICT TO LAYERS': 'Car Paint', 'Base Material': 'Wet Look', 'BASE COLOR': 'Use solid color', 'Check': 'G ROUGH near black, B COAT darkest (16)'},
    'result': 'A deep, mirror-like gloss.'},
   {'title': 'Sapphire glass', 'goal': 'A gem-like blue',
    'settings': {'Base Material': 'Sapphire Glass', 'BASE COLOR': 'Use finish\'s own color', 'Spec overlay': 'CC Wet Zone (optional)'},
    'result': 'A transparent blue gem look.'}],
  'faq': [
   {'q': 'Does glass make windows see-through?', 'a': 'No. Window glass keeps the template\'s alpha.'},
   {'q': 'What is the best check?', 'a': 'G ROUGH near black and B COAT at its darkest.'},
   {'q': 'Why does gloss show every flaw?', 'a': 'Mirror-level gloss reflects everything, including flaws in your art.'}],
  'mistakes': [
   {'symptom': 'The wet look is dull', 'cause': 'Roughness or coat sliders were moved', 'fix': 'Reset the spec sliders.'},
   {'symptom': 'The colour does not read under reflections', 'cause': 'A very light or very dark colour', 'fix': 'Pick a colour that still reads under reflections.'}],
  'protips': ['Look at the car with a bright sky in the sim. Wet looks are judged by their highlight, not their colour.'],
 },
 'recipes.weathered': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Three fine layers',
    'body': 'Weathering is sun-faded paint, chips at the edges and a rough clearcoat: a worn base finish for the look plus spec overlays for the shine damage. Bases: Desert Worn (sun-bleached), Battle Worn (worn through to metal at the edges), Die-Back Patina, or a rust or salvage finish. Overlays: Micro Chipping or Orange Peel Film.'},
   {'heading': 'Let your paint show through',
    'body': 'Lower Base Strength (0 is your original paint, 100 the full finish) to let your own colours show through the wear. Recolour a worn finish that brings its own palette with Hue Shift, not a solid colour.'},
   {'heading': 'Believable places',
    'body': 'Wear tends to sit on edges, lower panels and the front; use a box so the roof stays cleaner. Matte and low-metal finishes look more weathered than chrome. A Wear slider appears in the code but was not seen in the live panel of this build, so use the worn finishes and overlays.'}],
  'examples': [
   {'title': 'Battle-worn lower body', 'goal': 'A raced-hard look',
    'settings': {'APPLY AREA': 'Draw box on the lower half', 'Base Material': 'Battle Worn', 'Base Strength': '60', 'Spec overlay': 'Micro Chipping'},
    'result': 'Chips and wear on the lower panels with your paint showing through.'},
   {'title': 'Sun-faded roof', 'goal': 'Faded paint',
    'settings': {'Base Material': 'Desert Worn', 'Spec overlay': 'Orange Peel Film'},
    'result': 'A bleached, rough-clear look.'}],
  'faq': [
   {'q': 'How do I keep my livery visible?', 'a': 'Lower Base Strength so your paint shows through.'},
   {'q': 'Where should wear go?', 'a': 'Edges, lower panels and the front.'},
   {'q': 'Is there a Wear slider?', 'a': 'Not in this build\'s panel. Use worn finishes and overlays.'}],
  'mistakes': [
   {'symptom': 'Sponsors are unreadable', 'cause': 'Too much damage', 'fix': 'Lower Base Strength and keep damage off logos.'},
   {'symptom': 'Wear looks blotchy', 'cause': 'Scale too large', 'fix': 'Lower scale and check at 100 percent zoom.'}],
  'protips': ['Weathering should read as fine detail. If you see blotches at 100 percent zoom, lower the scale.'],
 },
 'recipes.helmet_suit': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Cars only',
    'body': 'iRacing reads helmets, suits and cars from different folders and file types. Shokker writes only car paint and car spec files, so it cannot render a helmet or suit. Do not pick a helmet or suit folder as the iRacing Car Folder: Shokker reports it is not a car.'},
   {'heading': 'Make them match anyway',
    'body': 'After RENDER, press Copy Card or Save Card PNG on the recipe card to keep the list of colours and finishes. Each zone shows its exact HEX colour. Recreate the same colours in the editor you use for helmets and suits, keeping the 60-30-10 proportions.'},
   {'heading': 'Expect small differences',
    'body': 'Gloss differences between helmet and car are normal in the sim. There is no automatic Trading Paints upload.'}],
  'examples': [
   {'title': 'Matching helmet colours', 'goal': 'Use the same palette',
    'settings': {'Press': 'Copy Card after RENDER', 'Note': 'HEX of each zone', 'Recreate': 'In your helmet editor with the same hex values'},
    'result': 'Helmet and car share one palette.'},
   {'title': 'Keep proportions', 'goal': 'Match the balance',
    'settings': {'Split': '60 percent main, 30 percent accent, 10 percent trim'},
    'result': 'The helmet feels part of the same scheme.'}],
  'faq': [
   {'q': 'Can Shokker paint a helmet?', 'a': 'No. Cars only.'},
   {'q': 'Why does it say my folder is not a car?', 'a': 'You picked a helmet or suit folder.'},
   {'q': 'How do I get the exact colours?', 'a': 'Open each zone and read its HEX.'}],
  'mistakes': [
   {'symptom': 'Shokker refuses the folder', 'cause': 'It is a helmet or suit folder', 'fix': 'Pick a car folder.'},
   {'symptom': 'Colours differ slightly in the sim', 'cause': 'Different gloss on helmet and car', 'fix': 'This is normal.'}],
  'protips': ['Copy the card as text and paste it into your notes. It is the easiest way to keep a palette.'],
 },
 'recipes.psd_to_iracing': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The whole job as one routine',
    'body': 'Open the template and wait for the layers to load. Set the ID, car folder and number mode once per car. Make a body zone limited to Car Paint. Add accent zones above it. Leave numbers and sponsors alone, or give the Numbers layer its own zone. Switch OFF Wire, Mask, Car_Mandatory and the group named Turn Off Before Exporting TGA. Check the preview and the R METAL, G ROUGH and B COAT views. RENDER, then Show my files, then Alt+Tab and Ctrl+R in iRacing.'},
   {'heading': 'The two steps people forget',
    'body': 'Template layers off and Ctrl+R. Forgetting the layers paints guide lines into the render. A wrong ID or number mode gives no error in iRacing, just paint-shop colours.'},
   {'heading': 'Save while you are ahead',
    'body': 'Save a project as soon as the layout is right and save a template to reuse the layout on teammates\' cars.'}],
  'examples': [
   {'title': 'A complete livery', 'goal': 'From template to track',
    'settings': {'Open': 'PSD/XCF/ORA', 'Setup': 'User ID, Car Folder, number mode', 'Body zone': 'RESTRICT TO LAYERS: Car Paint', 'Accents': 'Draw box or PICK COLOR FROM CAR, above the body', 'Guides': 'Wire, Mask, Car_Mandatory and the export group off', 'Finish': 'RENDER, Show my files, Ctrl+R in iRacing'},
    'result': 'The finished livery on the car.'},
   {'title': 'Numbers look wrong under metal', 'goal': 'Rescue stamped numbers',
    'settings': {'Where': 'Spec Tools > Decal Rescue Kit'},
    'result': 'A plain non-metal spec under the numbers.'}],
  'faq': [
   {'q': 'What do I do first?', 'a': 'Open the template of the car you drive.'},
   {'q': 'Why are there lines on my car?', 'a': 'A template guide layer was left on.'},
   {'q': 'Why is iRacing showing paint-shop colours?', 'a': 'ID, folder or number mode is wrong.'}],
  'mistakes': [
   {'symptom': 'Guide lines on the car', 'cause': 'Template layers on at render', 'fix': 'Turn all four off.'},
   {'symptom': 'Nothing in iRacing', 'cause': 'Ctrl+R forgotten, or pressed in Shokker', 'fix': 'Press it in iRacing.'}],
  'protips': ['Keep this recipe open next to the app the first few times. After three paints it is muscle memory.'],
 },
 'recipes.three_colour_gradient': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Setting it up',
    'body': 'A zone can fade between 2 to 10 colours. Pick the zone that owns the body area and give it a coating finish such as Gloss, Pearl or Candy. Set BASE COLOR to the custom gradient. Add three stops: deep blue at 0, gold at 50 and white at 100 (positions run from 0 to 100).'},
   {'heading': 'Direction',
    'body': 'Horizontal runs left to right across the sheet, vertical top to bottom, or one of the diagonal and radial options. Left to right on the sheet is not always front to back on the car.'},
   {'heading': 'Limits',
    'body': 'The fade does not line up from the side panel over the bumper or onto the other side; that is how a flat unwrapped sheet works. A finish that brings its own colour (chrome, carbon, holographic) ignores the gradient. If the zone only covers some colours of the paint, the gradient shows only there.'}],
  'examples': [
   {'title': 'Blue, gold, white', 'goal': 'The classic three-stop fade',
    'settings': {'BASE': 'Gloss', 'BASE COLOR': 'Custom gradient', 'Stops': '0 = deep blue, 50 = gold d4a017, 100 = white', 'Direction': 'Vertical'},
    'result': 'A fade from blue through gold to white.'},
   {'title': 'Ask Chat', 'goal': 'The same without sliders',
    'settings': {'Message': 'a gradient from blue to gold to white'},
    'result': 'Chat sets the stops.'}],
  'faq': [
   {'q': 'How many stops can I have?', 'a': '2 to 10.'},
   {'q': 'Why does one side fade the wrong way?', 'a': 'Each side of the car sits in its own part of the sheet. Give each side its own zone.'},
   {'q': 'Why does chrome ignore it?', 'a': 'Finishes with their own colour ignore gradients. Use a coating base.'}],
  'mistakes': [
   {'symptom': 'No gradient appears', 'cause': 'A finish that brings its own colour', 'fix': 'Use Gloss, Pearl or Candy.'},
   {'symptom': 'The fade breaks at the bumper', 'cause': 'Unwrapped sheet', 'fix': 'Use a zone per panel.'}],
  'protips': ['Use true colours for stops: a warm gold such as d4a017 and a deep blue read better than pure primaries.'],
 },
 'recipes.holographic': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'It lives in the shine map',
    'body': 'Holographic here means a rainbow shimmer that changes with the light. It needs a reflective base underneath (Pearl, Metallic or Chrome). The colour you chose stays; the shimmer rides in the spec map.'},
   {'heading': 'Base plus overlay or a finish',
    'body': 'If you pick a finish that brings its own holographic colour, that finish replaces your colour. Choose base plus spec overlay when you want a specific colour; a monolithic holographic finish is the quick all-in-one when you do not need one.'},
   {'heading': 'Judging',
    'body': 'Fine shimmer averages out in the live preview and can look flat; that does not mean it did nothing. The shimmer shows as variation in the red metal view.'}],
  'examples': [
   {'title': 'Holographic over a chosen colour', 'goal': 'Rainbow shimmer, your colour',
    'settings': {'Base Material': 'Pearl, Metallic or Chrome', '+ ADD SPEC OVERLAY': 'A holographic pattern', 'Opacity': '80'},
    'result': 'Your colour with a rainbow shimmer.'},
   {'title': 'Quick all-in-one', 'goal': 'No specific colour needed',
    'settings': {'Base Material': 'A monolithic holographic finish'},
    'result': 'A complete holographic look.'}],
  'faq': [
   {'q': 'Why does it look flat in the preview?', 'a': 'Fine shimmer averages out. Render and check R METAL.'},
   {'q': 'Can I choose the colour?', 'a': 'Yes, with a reflective base plus a holographic spec overlay.'},
   {'q': 'Which opacity?', 'a': 'About 80 to start.'}],
  'mistakes': [
   {'symptom': 'My colour changed', 'cause': 'A finish with its own holographic colour replaced it', 'fix': 'Use a base plus the overlay.'},
   {'symptom': 'No shimmer', 'cause': 'A non-reflective base', 'fix': 'Use Pearl, Metallic or Chrome.'}],
  'protips': ['Check R METAL for variation. If you see it vary, the shimmer is there, whatever the colour preview shows.'],
 },
 'recipes.rear_accents': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'The idea',
    'body': 'Front and rear accents share a colour, so a normal colour pick catches both. Limit a new zone to the rear with a box or a named part and put it above the zone that already owns the accent so it wins that area.'},
   {'heading': 'Sample, do not guess',
    'body': 'Pick the accent colour with PICK COLOR FROM CAR on the front accent so the zone matches exactly. Never guess "the same blue".'},
   {'heading': 'The look',
    'body': 'A chrome or metallic finish with BASE COLOR on your own paint, plus a flake spec overlay at Strength about 70.'}],
  'examples': [
   {'title': 'Rear chrome-flake accent', 'goal': 'Rear sides only',
    'settings': {'Pick': 'PICK COLOR FROM CAR on the front accent', 'APPLY AREA': 'Draw box around the rear of the left side, repeat on the right', 'BASE': 'A chrome or metallic finish', 'BASE COLOR': 'Your own paint', 'Spec overlay': 'Flake, Strength 70', 'List': 'Top'},
    'result': 'The rear accents glitter and match the front colour.'},
   {'title': 'Using a named part', 'goal': 'Skip drawing boxes',
    'settings': {'Choose': 'A car part if the car is known'},
    'result': 'The zone lands exactly on the part.'}],
  'faq': [
   {'q': 'Why does the zone not show?', 'a': 'It sits below the zone that owns the accent. Drag it up.'},
   {'q': 'Can Chat do this?', 'a': 'Yes: name the part and the look, then check the preview.'},
   {'q': 'Why sample instead of naming the colour?', 'a': 'Naming gives a nearby colour; sampling gives the exact one.'}],
  'mistakes': [
   {'symptom': 'The rear stays the old colour', 'cause': 'The zone is below another', 'fix': 'Move it to the top.'},
   {'symptom': 'The accent colour does not match the front', 'cause': 'The colour was guessed', 'fix': 'Use PICK COLOR FROM CAR.'}],
  'protips': ['If there is a front accent to match, always sample it. It saves a lot of trial and error.'],
 },
 'recipes.finish_on_numbers': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Layered templates',
    'body': 'A layered template keeps numbers, sponsors and stripes on their own layers, so a zone can touch only that layer. In the Layers tab find the layer (for example Numbers) and press the button that creates a zone restricted to it, then choose the finish under BASE.'},
   {'heading': 'Flat paints',
    'body': 'A flat paint has no layers, so select the colour of the numbers instead. Use PICK COLOR FROM CAR on the number colour and set the tolerance to about 30 to 45 so soft edges are caught. If a nearby colour is also taken, tighten the tolerance.'},
   {'heading': 'Without a layer limit',
    'body': 'A finish that brings its own colour paints over everything under the same colour. In Chat, name them: "make the numbers gold chrome". Numbers are only touched when you name them.'}],
  'examples': [
   {'title': 'Chrome numbers', 'goal': 'Give the numbers a metal finish',
    'settings': {'Layers tab': 'Create a zone restricted to the Numbers layer', 'BASE': 'A chrome Foundation finish', 'BASE COLOR': 'Use source paint'},
    'result': 'The numbers shine and keep their colour.'},
   {'title': 'Numbers on a flat paint', 'goal': 'Change number finish without layers',
    'settings': {'Zone': 'PICK COLOR FROM CAR on the number colour', 'Tolerance': '30 to 45'},
    'result': 'Only the numbers are picked.'}],
  'faq': [
   {'q': 'Can Chat change numbers?', 'a': 'Yes, if you name them.'},
   {'q': 'What tolerance on a flat paint?', 'a': 'About 30 to 45 to catch soft edges.'},
   {'q': 'Does it also do sponsors and stripes?', 'a': 'Yes, the same way, using their layers.'}],
  'mistakes': [
   {'symptom': 'Nearby colours also changed', 'cause': 'Tolerance too wide', 'fix': 'Tighten it.'},
   {'symptom': 'Everything with that colour changed', 'cause': 'No layer limit', 'fix': 'Restrict the zone to the layer.'}],
  'protips': ['Use the layer button first when you have layers. Colour picks are the fallback, not the first choice.'],
 },
 'recipes.make_it_pop': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Contrast of colour and shine',
    'body': 'A livery pops when neighbouring areas differ in both colour and shine, not when everything gets more saturated. One glossy deep area beside a flat area reads as depth on the car.'},
   {'heading': 'The recipe',
    'body': 'Find the biggest area and the two colours that contrast most. Give one a deep glossy candy or pearl of its own colour (BASE COLOR set to use your paint). Keep the other matte or satin, or give it a chrome trim. Add a subtle flake overlay on the body with Strength 30 to 50.'},
   {'heading': 'Stop early',
    'body': 'Compare with the SOURCE view and stop when it reads clearly at arm\'s length. Too many glossy areas cancel each other out: keep one hero area.'}],
  'examples': [
   {'title': 'Candy hero beside matte', 'goal': 'Instant depth',
    'settings': {'Area A': 'Candy or Pearl, BASE COLOR: your paint', 'Area B': 'Matte or Satin', 'Overlay': 'Flake on the body, Strength 30 to 50'},
    'result': 'A clear contrast of shine between neighbours.'},
   {'title': 'Chrome trim', 'goal': 'Sharpen the edges',
    'settings': {'Trim zone': 'A chrome Foundation finish with Use source paint'},
    'result': 'Edges look crisp.'}],
  'faq': [
   {'q': 'Should I boost saturation?', 'a': 'No. Contrast in colour and shine matters more.'},
   {'q': 'How much flake?', 'a': 'Subtle: 30 to 50 percent opacity.'},
   {'q': 'How many glossy areas?', 'a': 'One hero area.'}],
  'mistakes': [
   {'symptom': 'Everything looks the same', 'cause': 'All areas glossy', 'fix': 'Make the neighbour matte or satin.'},
   {'symptom': 'Hard to undo', 'cause': 'Several changes at once', 'fix': 'Change one thing at a time.'}],
  'protips': ['View it small (zoomed out). If it still reads, it will read on track.'],
 },
 'recipes.undo_start_over': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Three levels',
    'body': 'One step back: Ctrl+Z or the Undo button under a helper answer. Several steps: press Undo more than once, with the Undo History list of recent actions to see where you are. A clean slate: Reset All Zones, which returns the list to the default five zones.'},
   {'heading': 'What the helper cannot do',
    'body': 'The helper cannot delete zones itself; it mutes them and tells you where to delete. Never mute every zone: a render needs at least one zone.'},
   {'heading': 'Caution',
    'body': 'Undoing many steps after you reset by hand can bring back an old state. When you want the base file, reset instead. Save a project first if you might want the current look back.'}],
  'examples': [
   {'title': 'Undo one step', 'goal': 'Take back the last change',
    'settings': {'Key': 'Ctrl+Z', 'or': 'Undo under the helper\'s answer'},
    'result': 'The last change is gone.'},
   {'title': 'Start over', 'goal': 'Clean slate',
    'settings': {'Save': 'A project first', 'Press': 'Reset All Zones'},
    'result': 'The default five zones remain.'}],
  'faq': [
   {'q': 'Where is Undo History?', 'a': 'Open it to see the list of recent actions.'},
   {'q': 'Can the helper delete a zone?', 'a': 'No. It mutes it and tells you to delete it.'},
   {'q': 'What does Reset All Zones return to?', 'a': 'The default five zones.'}],
  'mistakes': [
   {'symptom': 'An old state came back', 'cause': 'Many undo steps after a hand reset', 'fix': 'Use Reset All Zones.'},
   {'symptom': 'Render refuses', 'cause': 'Every zone is muted', 'fix': 'Unmute at least one zone.'}],
  'protips': ['Save a project before any big experiment. It costs a second and removes the fear of trying things.'],
 },
 'recipes.change_body_keep_numbers': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Body layer only',
    'body': 'On a layered template the body and the decals are separate layers. A zone limited to the body layer (named like Car Paint or Body) cannot touch the decals. A whole-car finish that brings its own colour (colour shift, candy, holographic) with no layer limit paints over every number and logo.'},
   {'heading': 'Steps',
    'body': 'In the Layers tab find the body layer. Add or edit the zone that covers the car and tick only that layer under RESTRICT TO LAYERS. Give it the colour and finish. Check the numbers and sponsors are still crisp. If you want them changed too, include their layers.'},
   {'heading': 'Chat and flat paints',
    'body': 'Chat does this by default and says it kept your numbers and sponsors. A flat paint has no layers; use the colour pick instead and check the numbers after.'}],
  'examples': [
   {'title': 'Recolour the body only', 'goal': 'New body colour, decals untouched',
    'settings': {'RESTRICT TO LAYERS': 'Car Paint only', 'Colour / finish': 'As wanted'},
    'result': 'The body changes; numbers and sponsors stay crisp.'},
   {'title': 'Candy body', 'goal': 'A whole-car candy without hiding the numbers',
    'settings': {'BASE': 'Candy', 'RESTRICT TO LAYERS': 'Car Paint only'},
    'result': 'Candy only on the body.'}],
  'faq': [
   {'q': 'Why did my numbers vanish?', 'a': 'The zone had no layer limit and a finish with its own colour.'},
   {'q': 'Can I include the numbers on purpose?', 'a': 'Yes, tick their layers too.'},
   {'q': 'What if there are no layers?', 'a': 'Use the colour pick and check the numbers afterwards.'}],
  'mistakes': [
   {'symptom': 'Numbers covered', 'cause': 'No RESTRICT TO LAYERS', 'fix': 'Tick the body layer only.'},
   {'symptom': 'Sponsors changed', 'cause': 'The zone reaches every layer', 'fix': 'Restrict it.'}],
  'protips': ['Always look at the numbers in the CAR view after a body-wide change. It takes five seconds.'],
 },
}
