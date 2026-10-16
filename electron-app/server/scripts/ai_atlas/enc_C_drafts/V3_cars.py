"""v3 depth for the cars domain (lane C, 2026-10-04). Facts: docs/CAR_LEARNING.md, js/spb-car-atlas-data.js, js/spb-support-answers.js, docs/ai_knowledge/06_layers_panels_and_export.md."""
V3 = {
 'cars.supported_cars': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Checked layouts and drafts',
    'body': 'The library lists 38 cars. 31 are checked layouts: NASCAR Cup Gen 4, Gen 6 and Next Gen, ARCA, Class B and Xfinity, Late Model and Super Late Model, Street Stock, Mini Stock, trucks (Silverado, F-150) and a Dirt Late Model. Seven are drafts (dirt mod, dirt sprint winged, legends, pro trucks, SK modified and similar): Shokker may suggest their layout but asks you to confirm before it uses it.'},
   {'heading': 'What "known" buys you',
    'body': 'For a known car, Chat and the AI helper already know where the hood, roof, left and right sides, front and rear bumper, trunk and spoiler are, so "make the roof black" lands on the right panel without any questions. The render, the files and the colours work the same for every car.'},
   {'heading': 'How a car is recognised',
    'body': 'Two clues are used: the car folder name and the shape of the paintable area on the sheet. If one is missing the other is still tried. A sheet that looks 78% or more like a known car is only proposed, never applied silently, because two cars can share a similar layout.'}],
  'examples': [
   {'title': 'Check if your car is known', 'goal': 'Find out before you start',
    'settings': {'Source Paint': 'Open your car template', 'iRacing Car Folder': 'Set to your car\'s folder', 'Chat message': 'make the roof black'},
    'result': 'A known car says it recognises it and aims the zone at the roof. An unknown car asks you to show the parts once.'},
   {'title': 'Confirm a draft car', 'goal': 'Use a draft layout safely',
    'settings': {'Helper says': 'It recognises a draft car', 'You do': 'Look at the preview and click Yes, that is right'},
    'result': 'The layout is used only after your yes.'}],
  'faq': [
   {'q': 'My car is not on the list. Can I still use Shokker?', 'a': 'Yes. Any template opens and renders. You teach the parts once and Shokker remembers them.'},
   {'q': 'How many cars are in the library?', 'a': '38: 31 checked layouts and 7 drafts.'},
   {'q': 'Is the library the same as a template?', 'a': 'No. It is only the names and places of parts. You still open the car\'s own template.'},
   {'q': 'Why did it ask me to confirm?', 'a': 'A draft car, or a sheet that only looks 78% or more like a known car, is a proposal. Shokker waits for your one click.'}],
  'mistakes': [
   {'symptom': 'The zone lands on the wrong panel', 'cause': 'A draft layout or a look-alike car was proposed and accepted without checking', 'fix': 'Check the preview, then teach the part again or load a car map.'},
   {'symptom': 'You assume an unlisted car will not work', 'cause': 'The library is only about named parts', 'fix': 'Open the template anyway and teach the parts.'}],
  'protips': ['Set the iRacing Car Folder before you ask Chat for a part. The folder name is one of the two clues that identify the car.'],
 },
 'cars.reading_sheet': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The usual stock-car layout',
    'body': 'On a typical stock-car sheet the long upper band is the right side and the long lower band is the left side. Across the middle run the trunk, roof and hood. The front bumper is at the top left, the rear bumper next to it and the spoiler far right. Rockers, splitters, mirrors and wheels fill the gaps. This held for 13 measured stock-car families.'},
   {'heading': 'Up on the sheet is not up on the car',
    'body': 'One side panel may be drawn upside down, and some sheets run a side from rear to front. When a stripe looks backwards or upside down on the car, the panel direction is the reason, not the paint. Mirror or flip the placement.'},
   {'heading': 'Other cars differ',
    'body': 'Trucks, dirt cars and sprint cars arrange panels differently, so do not assume the stock-car pattern. Use the Car parts tab in Chat to see the parts Shokker knows drawn over your sheet.'},
   {'heading': 'Do not trust a picture-reading AI for panel names',
    'body': 'Measured on real sheets, picture-reading models name panels wrongly most of the time. Shokker takes names from the library or from what you teach.'}],
  'examples': [
   {'title': 'Find the hood on a stock car', 'goal': 'Place a zone by hand on the right panel',
    'settings': {'Layer': 'Wire on (and off again before render)', 'Hood': 'Across the middle of the sheet with the roof and trunk', 'Check': 'Car parts tab in Chat'},
    'result': 'You know which outline is the hood before you draw.'},
   {'title': 'Fix a backwards stripe', 'goal': 'Make a stripe run the right way on one side',
    'settings': {'Cause': 'Side panel direction', 'Action': 'Mirror or flip the placement on that panel'},
    'result': 'The stripe runs front to back on the car.'}],
  'faq': [
   {'q': 'Which side is the left side on the sheet?', 'a': 'On a typical stock car the lower long band is the left side and the upper long band is the right side.'},
   {'q': 'Why is a side panel upside down?', 'a': 'Templates often draw one side flipped. Up on the sheet is not up on the car.'},
   {'q': 'How do I see the panel outlines?', 'a': 'Turn on the template\'s Wire layer. Mask shows what is paintable.'},
   {'q': 'Is the layout the same for trucks?', 'a': 'No. Trucks, dirt cars and sprint cars differ. Check the Car parts view.'}],
  'mistakes': [
   {'symptom': 'Template lines show on the car in iRacing', 'cause': 'Wire, Mask or Car_Mandatory was still on when you rendered', 'fix': 'Turn all three off, render again and save.'},
   {'symptom': 'You paint the upper band for the left side', 'cause': 'On a stock-car sheet the upper band is the right side', 'fix': 'Use the Car parts tab to check before drawing.'}],
  'protips': ['Use the Car parts tab as a map. It draws the names of the parts over your own sheet, which beats memorising layouts.'],
 },
 'cars.teach_parts': {
  'level': 'beginner',
  'deep': [
   {'heading': 'How teaching works',
    'body': 'If you ask Chat for something on a part and the car is unknown, Shokker shows your sheet and asks. You tap or draw a box around one panel at a time and say which part it is. You can confirm a guess (Yes, that is right) or say the paint has none (There are none on this paint), for example for numbers. The answer is remembered for this car layout, so another paint of the same car is recognised next time.'},
   {'heading': 'Tight boxes matter',
    'body': 'Draw tight around one single part. A box around two parts teaches the wrong thing. For numbers, draw around one number and Shokker finds the rest.'},
   {'heading': 'Where it is stored',
    'body': 'What you teach stays on this computer and is not sent to other users. In the Chat gear you can copy, save or load a car map, which is how you fix a mistake or move a map to another PC.'}],
  'examples': [
   {'title': 'Teach the roof', 'goal': 'Let Chat aim at the roof of an unknown car',
    'settings': {'Chat message': 'make the roof black', 'Box': 'Draw around the roof only', 'Label': 'roof'},
    'result': 'The roof is remembered and the zone lands on it. The next paint of this car needs no teaching.'},
   {'title': 'Fix a wrong part', 'goal': 'Correct a part that was taught wrong',
    'settings': {'Where': 'Chat gear', 'Action': 'Load or save a car map, or teach the part again'},
    'result': 'The corrected box replaces the old one.'}],
  'faq': [
   {'q': 'Do I have to teach every part?', 'a': 'No. Teach only the parts you ask for. Shokker asks again when it needs another.'},
   {'q': 'Is the lesson shared with other users?', 'a': 'No. It stays on this computer.'},
   {'q': 'What if I draw around two panels?', 'a': 'It teaches the wrong thing. Redo it with one box per part.'},
   {'q': 'What does "There are none on this paint" do?', 'a': 'It tells Shokker the paint has none of that item, such as numbers, so it will not keep asking.'}],
  'mistakes': [
   {'symptom': 'The hood zone covers the roof too', 'cause': 'One box was drawn around two parts', 'fix': 'Teach the part again with a tight box around only the hood.'},
   {'symptom': 'Chat keeps asking the same question', 'cause': 'The part was skipped, so nothing was stored', 'fix': 'Teach it once with a box and a label.'}],
  'protips': ['Save a car map from the Chat gear after you teach a car. It is a quick backup if you reinstall.'],
 },
 'cars.choose_template': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Same car, same template',
    'body': 'Each iRacing car has its own paint template with its own layout. Open the template made for the same car you drive. A template for another car paints the wrong places because the panels do not match.'},
   {'heading': 'Do not resize',
    'body': 'iRacing accepts only 2048 by 2048 or 1024 by 1024 paints and ignores any other size, showing your paint-shop colours instead. Shokker renders at the template\'s own size, so leave the canvas as it is.'},
   {'heading': 'Folder name matters',
    'body': 'Use the car menu in the iRacing Car Folder section so the files land in the right folder. A twin folder (the same layout for two cars) still needs the right folder name, because that is the folder iRacing reads from.'},
   {'heading': 'No template, only a finished paint',
    'body': 'Open it as a flat TGA, PNG or JPEG. It works, but layers do not exist, so you cannot use the Wire and Mask guides.'}],
  'examples': [
   {'title': 'Start a new car', 'goal': 'Open the right file and set the right folder',
    'settings': {'Source Paint': 'PSD / XCF / ORA button, open the template', 'iRacing Car Folder': 'Car menu, pick your car', 'Check': 'Wire layer on; panels match your car'},
    'result': 'The preview shows your car\'s sheet and the files will save to the right place.'},
   {'title': 'You only have a finished paint', 'goal': 'Work from a flat file',
    'settings': {'Button': 'TGA / PNG / JPEG next to Source Paint'},
    'result': 'The paint opens as one flat layer.'}],
  'faq': [
   {'q': 'My paint shows on the wrong parts in iRacing.', 'a': 'You probably opened the wrong car\'s template. Open the one for the car you drive.'},
   {'q': 'Can I use another car\'s template as a starting look?', 'a': 'No. The panels will not match.'},
   {'q': 'iRacing shows my paint-shop colours, not my paint.', 'a': 'The size is wrong. iRacing accepts only 2048 or 1024 square paints.'},
   {'q': 'Where do I get a template?', 'a': 'From iRacing or a source you trust.'}],
  'mistakes': [
   {'symptom': 'The paint appears in iRacing but on the wrong parts', 'cause': 'A different car\'s template was used', 'fix': 'Open the correct template and rebuild or copy your artwork over.'},
   {'symptom': 'iRacing ignores your paint', 'cause': 'The canvas was resized to something other than 2048 or 1024 square', 'fix': 'Start again from the template at its original size.'}],
  'protips': ['Check the preview against your car\'s sheet before you design anything. Two minutes there saves a redo.'],
 },
 'cars.safe_areas': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Car and dead space',
    'body': 'The 2048 square sheet holds the car\'s panels and a lot of dead space between them. The template\'s Mask layer marks which is which: transparent is paintable and opaque is dead space. Shokker uses the same idea to decide where a whole-car look may go. The dead space on templates is a brown tone, which the app uses to find the car shape.'},
   {'heading': 'Guide layers are not paint',
    'body': 'Wire, Mask, Car_Mandatory and the group Turn Off Before Exporting TGA show you panels and reserved stamp blocks. They must be off when you render or lines appear on the car.'},
   {'heading': 'Numbers and sponsors',
    'body': 'For a car that gets stamped numbers and sponsors, keep the stamp blocks clear if you want the sim to place them. Chat\'s whole-car looks stay inside the body paint layers, so numbers, sponsors and logos are untouched unless you ask.'},
   {'heading': 'Export format',
    'body': 'iRacing wants a 24-bit TGA. A TGA that carries an alpha channel from the template can make parts disappear or turn black, so re-export as 24-bit if you export by hand.'}],
  'examples': [
   {'title': 'Check your artwork is inside', 'goal': 'Confirm a stripe will not be thrown away',
    'settings': {'Mask view': 'On', 'Wire view': 'On', 'Rule': 'Keep artwork in the transparent area'},
    'result': 'You see where the paintable area ends and can move artwork before rendering.'},
   {'title': 'Clean render for iRacing', 'goal': 'Avoid template lines on the car',
    'settings': {'Wire': 'Off', 'Mask': 'Off', 'Car_Mandatory': 'Off', 'Turn Off Before Exporting TGA group': 'Off'},
    'result': 'The car shows only paint.'}],
  'faq': [
   {'q': 'Why did my stripe stop at an invisible edge?', 'a': 'It reached the edge of the paintable area. Anything outside the Mask is thrown away.'},
   {'q': 'Why do I see lines or blocks on the car in the sim?', 'a': 'A guide layer was on when you rendered.'},
   {'q': 'Why did parts turn black?', 'a': 'A TGA with an alpha channel from the template. Export it as 24-bit.'},
   {'q': 'Will Chat paint over my numbers?', 'a': 'No. Whole-car looks stay inside the body paint layers.'}],
  'mistakes': [
   {'symptom': 'Lines show on the car', 'cause': 'Wire or Mask was visible at render time', 'fix': 'Turn them off, render and save again.'},
   {'symptom': 'Parts vanish in the sim', 'cause': 'The exported TGA carries an alpha channel', 'fix': 'Re-export as a 24-bit TGA.'}],
  'protips': ['Do the clean-render check last, every time. It is a four-switch routine and the most common cause of "lines on my car".'],
 },
}
