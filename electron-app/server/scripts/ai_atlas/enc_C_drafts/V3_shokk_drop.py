"""v3 depth for the shokk_drop domain (lane C, 2026-10-04). Facts: shokk-drop.html, paint-booth-v2.html, paint-booth-2-state-zones.js (all already cited in the articles)."""
V3 = {
 'shokk_drop.what_is_shokk_drop': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Five things an image can become',
    'body': 'The Type list on the left decides it. Paint finish: the image is the colour and a matching shine is made for it. Pattern: a repeating design that keeps its transparency. Spec overlay: shine only, no colour. Paint + spec maps (exact): you supply both and they are used word for word. Car template (whole car): a whole-car paint and shine as one zone. When unsure, leave it on Paint finish with the default shine.'},
   {'heading': 'Everything is fitted to the 2048 sheet',
    'body': 'Whatever you drop is auto-sized to the 2048 by 2048 flat car sheet, so you do not resize beforehand. Only PNG, JPG and WebP are accepted. After Commit drop the result appears in a SHOKK DROP group in the booth, and you still have to put that finish on a zone yourself: drops are finishes, not zones.'},
   {'heading': 'SHOKK THE WORLD: twenty shines from one picture',
    'body': 'This button turns one picture into 20 shine variations: 8 standard ones, 7 that mix two styles and 5 extreme four-way blends. You keep the ones you like. Holding Shift while dropping an image runs it straight away.'},
   {'heading': 'Sharing',
    'body': 'Drops can be shared as .spbdrop files. Drag a friend\'s .spbdrop file onto the gallery to import it.'}],
  'examples': [
   {'title': 'Your own artwork as a finish', 'goal': 'Turn a texture into a reusable finish',
    'settings': {'Type': 'Paint finish', 'File': 'A PNG, JPG or WebP', 'Next': 'Look at the preview, then Commit drop'},
    'result': 'A new entry in the SHOKK DROP group, ready to put on a zone like any other finish.'},
   {'title': 'Pick the best shine for one picture', 'goal': 'See many shine looks and keep a few',
    'settings': {'Drop the image': 'Hold Shift while dropping, or click SHOKK THE WORLD', 'Variants': '20: 8 standard, 7 two-style mixes, 5 four-way blends', 'Keep': 'Your favourites'},
    'result': 'Your kept variants appear in the SHOKK DROP group.'},
   {'title': 'Try it with no artwork', 'goal': 'Learn the window safely',
    'settings': {'Button': 'Try a sample'},
    'result': 'The real process runs on a built-in test picture.'}],
  'faq': [
   {'q': 'What file types can I drop?', 'a': 'PNG, JPG and WebP only.'},
   {'q': 'Where do my drops go?', 'a': 'Into a SHOKK DROP group in the booth, after you click Commit drop.'},
   {'q': 'Does a drop paint my car by itself?', 'a': 'No. A drop is a finish. Put it on a zone to see it on the car.'},
   {'q': 'The Shokk Drop window did not open.', 'a': 'A pop-up blocker may have stopped it. The booth then goes to Shokk Drop itself; use the Paint Booth link at its top to come back.'},
   {'q': 'Can I share a drop?', 'a': 'Yes, as a .spbdrop file. Drag a friend\'s file onto the gallery to import it.'}],
  'mistakes': [
   {'symptom': 'You committed a drop but the car did not change', 'cause': 'Drops are finishes, not zones', 'fix': 'Go back to the booth, open the SHOKK DROP group and apply the finish to a zone.'},
   {'symptom': 'The shine looks wrong for a pattern', 'cause': 'The Type was set to Paint finish when you wanted a repeating stamp', 'fix': 'Drop it again with Type set to Pattern, which keeps transparency.'}],
  'protips': ['Paint finish with the default shine is the best starting point. Switch Type only when you know what you want.',
              'SHOKK THE WORLD is a fast way to learn what a shine does: compare the 20 variants side by side before you decide.'],
 },
 'shokk_drop.import_exact_set': {
  'level': 'pro',
  'deep': [
   {'heading': 'Two ways to supply the shine',
    'body': 'Give Shokk Drop your colour art plus a spec either as one combined RGB picture or as three separate black-and-white plates. In the combined picture red is metallic, green is roughness and blue is clearcoat. Saved word for word, it renders exactly the way you made it, with no automatic shine added.'},
   {'heading': 'Reading the blue plate',
    'body': 'Blue is clearcoat with an inverted feel: low blue values are a strong clearcoat (16 is maximum gloss in the game) and high blue is dull. Check the clearcoat article before painting that plate.'},
   {'heading': 'The spec options',
    'body': 'You can choose No spec (auto-generate), FRACTURE the spec, Combined spec (one RGB image), or separate R, G and B plates. If you leave a plate empty, Shokk fills it for you when the "any plate left empty" option is on. Save as chooses whether the set becomes a paint finish or a stamp-on pattern, and you can set how strong the metal and clearcoat come out.'},
   {'heading': 'No rescue from auto-shine',
    'body': 'An exact set will not be rescued by automatic shine. If your roughness plate is flat, the car will look flat. A combined spec is read as colour channels, so keep it a normal RGB picture and avoid colour profiles that shift values.'}],
  'examples': [
   {'title': 'Import a combined spec', 'goal': 'Use your own Photoshop shine map exactly',
    'settings': {'Save as': 'Paint finish', 'Colour art': 'Your paint PNG', 'Spec form': 'Combined spec (one RGB image)', 'Red': 'Metallic', 'Green': 'Roughness', 'Blue': 'Clearcoat (16 = max gloss)'},
    'result': 'The set renders exactly as authored. Find it in the SHOKK DROP group and put it on a zone.'},
   {'title': 'Three plates, one left empty', 'goal': 'Supply only metallic and roughness',
    'settings': {'Spec form': 'Separate R, G and B plates', 'R plate': 'Your metallic plate', 'G plate': 'Your roughness plate', 'B plate': 'Left empty with the fill option on'},
    'result': 'Shokk fills the clearcoat plate for you; the other two are used as you drew them.'}],
  'faq': [
   {'q': 'What do the three channels mean?', 'a': 'Red is metallic, green is roughness and blue is clearcoat.'},
   {'q': 'Why is my blue plate backwards?', 'a': 'Low blue means strong clearcoat; 16 is maximum gloss and high values are dull.'},
   {'q': 'Will Shokk improve my maps?', 'a': 'No. An exact set is saved word for word.'},
   {'q': 'Can I import it as a pattern?', 'a': 'Yes. Choose Save as: Pattern instead of Paint finish.'}],
  'mistakes': [
   {'symptom': 'The car looks flat after an exact import', 'cause': 'The roughness plate is flat, and exact sets get no auto shine', 'fix': 'Add variation to the green plate, or use the auto-generate spec form.'},
   {'symptom': 'The shine values are slightly off', 'cause': 'The combined spec was saved with a colour profile that shifts values', 'fix': 'Save it as a plain RGB image with no profile conversion.'}],
  'protips': ['Paint the blue plate last and check it against the clearcoat scale. Mixed up clearcoat is the commonest mistake with hand-made specs.'],
  'related_add': ['spec.what_is_spec_map'],
 },
 'shokk_drop.shokk_library_files': {
  'level': 'beginner',
  'deep': [
   {'heading': 'What a .shokk file holds',
    'body': 'SAVE SHOKK writes your current session as a recipe: a name (required), an author, a short description and tags such as Pearl, Candy, Neon, Dark, Pattern-Based, Multi-Layer or Full Scheme. With Include paint on, the file also carries the paint picture, so it opens the same on another machine. The file is larger but fully portable.'},
   {'heading': 'Finding and loading',
    'body': 'LOAD SHOKK FILE opens the library window. Search by name, author or tag, select a file and click Open Selected (a double-click also loads it). By default the library lives in your Documents folder under Shokker Paint Booth, then SHOKK Library.'},
   {'heading': 'Not the same as a project or a drop',
    'body': 'A project file is your working session with its layers. A .shokk recipe is your zones and finishes, not your layered work: for layers use Save project. Shokk Drop is a different tool that makes finishes from pictures. Channel PNG Export extracts a recipe\'s paint and spec to PNG for inspection only and does not make the iRacing TGA files.'}],
  'examples': [
   {'title': 'Save a look for later', 'goal': 'Keep a finished scheme as a reusable recipe',
    'settings': {'Where': 'Zones panel, More menu, SAVE SHOKK', 'Name': 'Gulf stripes on 718 GT3', 'Tags': 'Full Scheme', 'Include paint': 'On'},
    'result': 'A .shokk file in your SHOKK Library that you can search by name or tag.'},
   {'title': 'Send a look to a friend', 'goal': 'Make a file that opens the same elsewhere',
    'settings': {'Include paint': 'On', 'Name': 'Car and look in the name'},
    'result': 'Your friend loads it with LOAD SHOKK FILE and sees the same result.'}],
  'faq': [
   {'q': 'Where are my recipes stored?', 'a': 'By default in Documents, under Shokker Paint Booth and SHOKK Library.'},
   {'q': 'Does a .shokk file keep my layers?', 'a': 'No. Use Save project for layers.'},
   {'q': 'Is a .shokk the same as a Shokk Drop?', 'a': 'No. A .shokk is a saved recipe of zones; a Shokk Drop is a finish made from a picture.'},
   {'q': 'What does Channel PNG Export do?', 'a': 'It writes a recipe\'s paint and spec to PNG files so you can look at them in Photoshop. It does not make iRacing files.'}],
  'mistakes': [
   {'symptom': 'Your friend sees a different paint', 'cause': 'Include paint was off when you saved', 'fix': 'Save again with Include paint on.'},
   {'symptom': 'You cannot find a recipe later', 'cause': 'It was saved with a vague name and no tags', 'fix': 'Put the car and look in the name and add tags.'}],
  'protips': ['Name recipes with the car first. A library of fifty files searches much faster when the car comes first in every name.'],
 },
 'shokk_drop.fracture_this_paint': {
  'level': 'beginner',
  'deep': [
   {'heading': 'What exactly the button does',
    'body': 'FRACTURE THIS PAINT sets the finish of your selected zone (or the first zone if none is selected) to Soul Core Emerald, which gives the broken-glass style shine with pink flashes. If there are no zones yet it asks you to add one first. It changes only one zone and replaces that zone\'s current finish.'},
   {'heading': 'Colour lock',
    'body': 'If the zone\'s colour is locked, the finish changes but your colour is kept, and the on-screen message says so. Lock the colour first if you want your own colour with only the fractured shine.'},
   {'heading': 'Not a separate tool',
    'body': 'It is a quick way to see how a heavy fractured finish looks on your car, not a different engine. Undo (Ctrl+Z) brings the old finish back.'}],
  'examples': [
   {'title': 'Fracture the hood only', 'goal': 'Get a striking fractured hood fast',
    'settings': {'Select': 'The hood zone', 'Colour': 'Locked, if you want to keep your colour', 'Button': 'FRACTURE THIS PAINT'},
    'result': 'The hood takes the Soul Core Emerald shine and the message names the zone and says if your colour was kept.'},
   {'title': 'Undo it', 'goal': 'Go back after testing',
    'settings': {'Key': 'Ctrl+Z'},
    'result': 'The zone returns to its earlier finish.'}],
  'faq': [
   {'q': 'Which finish does it apply?', 'a': 'Soul Core Emerald.'},
   {'q': 'Does it change every zone?', 'a': 'No, only the selected zone, or the first zone if none is selected.'},
   {'q': 'Does it change my colour?', 'a': 'Only if the colour is not locked. With the lock on, your colour is kept.'},
   {'q': 'Nothing happened.', 'a': 'There may be no zones yet. Add a zone first.'}],
  'mistakes': [
   {'symptom': 'Your zone lost its previous finish', 'cause': 'The button replaces the zone\'s current finish', 'fix': 'Press Ctrl+Z to go back.'},
   {'symptom': 'The colour changed too', 'cause': 'The colour was not locked', 'fix': 'Undo, lock the colour, and press the button again.'}],
  'protips': ['Use it as a quick preview of what a fractured look does to a panel, then switch to other fractured finishes from the picker if you want a different mood.'],
 },
 'shokk_drop.tools_not_in_booth': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Names you may see in old notes',
    'body': 'Auto Painter (also called Shokk Trace) had its top-bar button removed because it was not working well, so it is not something you can click. The experimental tab (Design It, Photo to Livery, Shokker-ize) is hidden in this build. Image Forge is a guide for finish authors: a table of finish ids for replacing or adding finishes by dropping pictures in a folder, not a buyer feature.'},
   {'heading': 'What to use instead',
    'body': 'For your own picture as a finish, use Shokk Drop. For a look similar to a photo, use the chat helper and attach the picture for colours to match (see the match-a-photo recipe). For a shine you authored, use Import a set in Shokk Drop.'},
   {'heading': 'If you cannot find a button',
    'body': 'Check the top-bar help and the window tour before assuming something is broken. The feature may simply not be part of this build.'}],
  'examples': [
   {'title': 'You saw Shokk Trace in a video', 'goal': 'Get a similar result with what you have',
    'settings': {'Use': 'Chat helper with the picture attached, or Shokk Drop', 'Not': 'A Shokk Trace or Auto Painter button'},
    'result': 'You get a colour-matched livery or a finish from your picture.'},
   {'title': 'Your own exact shine', 'goal': 'Use maps you built yourself',
    'settings': {'Tool': 'Shokk Drop, Import a set - exact finish'},
    'result': 'Your maps are used as authored.'}],
  'faq': [
   {'q': 'Where did Auto Painter go?', 'a': 'Its button was removed from the top bar in this build.'},
   {'q': 'Can I use Image Forge?', 'a': 'It is a guide for authors. Dropping files into its folder does nothing for a normal installed booth.'},
   {'q': 'Where are Design It and Photo to Livery?', 'a': 'The experimental tab is hidden in this build.'},
   {'q': 'What is the closest thing for photos?', 'a': 'Attach the picture in the chat helper and ask for colours to match it, or turn it into a finish with Shokk Drop.'}],
  'mistakes': [
   {'symptom': 'You hunt through menus for a button from a video', 'cause': 'The video shows an older or different build', 'fix': 'Look in Shokk Drop or the chat helper for the same job.'},
   {'symptom': 'You drop images into the Image Forge folder and nothing changes', 'cause': 'It is not a buyer feature', 'fix': 'Use Shokk Drop to bring in pictures.'}],
  'protips': ['If a tutorial or post names a tool you cannot find, search the Encyclopedia for what it did, not what it was called. The job usually has a current home.'],
 },
}
