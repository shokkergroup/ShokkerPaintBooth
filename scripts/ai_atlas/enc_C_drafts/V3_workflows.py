"""v3 depth for the workflows domain (lane C, 2026-10-04). Facts: js/spb-support-answers.js, docs/ai_knowledge/01_how_pro_works.md, js/spb-quests.js, engine/SPEC_MAP_REFERENCE.md (already cited in the articles)."""
V3 = {
 'workflows.what_is_shokker': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Two pictures for every car',
    'body': 'iRacing reads two pictures for every car: the paint (the colours) and the spec map (how metallic, rough and glossy each pixel is). Shokker builds both. You describe the look with zones, finishes and patterns, or with plain words in Chat, and Shokker paints the car\'s template with real materials: chrome, candy, carbon, flake, pearl, colour-shift and thousands more.'},
   {'heading': 'Works offline',
    'body': 'The design library, rendering and the built-in helper need no internet. Only the optional online AI chat needs a connection. Everything the AI does can be undone in one click.'},
   {'heading': 'What it does not do',
    'body': 'Shokker does not upload to Trading Paints and does not drive iRacing for you; you press RENDER and Ctrl+R yourself. It paints cars only: helmets and suits are not supported targets.'}],
  'examples': [
   {'title': 'The shortest loop', 'goal': 'See your own design in the sim',
    'settings': {'Open': 'Your car\'s template with PSD/XCF/ORA', 'Design': 'Tell Chat or pick a colour and a finish in PRO', 'Render': 'RENDER', 'Sim': 'Alt+Tab, then Ctrl+R in iRacing'},
    'result': 'The car reloads with your paint and shine.'},
   {'title': 'A flat paint for a quick change', 'goal': 'Recolour a finished paint',
    'settings': {'Open': 'TGA/PNG/JPEG button', 'Do': 'Ask Chat: make the black matte'},
    'result': 'The black becomes matte and the rest of the paint stays.'}],
  'faq': [
   {'q': 'Does Shokker need internet?', 'a': 'No, except for the optional online AI chat.'},
   {'q': 'Does it upload my paint?', 'a': 'No. You press RENDER and Ctrl+R yourself; there is no upload to Trading Paints.'},
   {'q': 'Can I paint a helmet?', 'a': 'No. It paints cars only.'},
   {'q': 'What is a spec map?', 'a': 'The second picture iRacing reads for metal, roughness and clearcoat.'}],
  'mistakes': [
   {'symptom': 'Nothing appears in iRacing', 'cause': 'RENDER was never pressed, or Ctrl+R was pressed in the wrong window', 'fix': 'Press RENDER in Shokker, Alt+Tab to iRacing, then press Ctrl+R there.'},
   {'symptom': 'You expect the helper to upload', 'cause': 'Shokker does not upload anywhere', 'fix': 'Use the rendered files in your car folder.'}],
  'protips': ['Do one test render with no changes the very first time. Seeing your own paint in iRacing proves the whole chain before you design anything.'],
 },
 'workflows.how_paint_gets_on_car': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Five steps, one job each',
    'body': 'Design makes the look in the live preview; nothing is written yet. RENDER builds the full paint and spec at the size of your template (2048 or 1024 square). Copy writes the files into the iRacing Car Folder: car_num_ID.tga or car_ID.tga for the paint and car_spec_ID.tga for the shine, where ID is your iRacing Customer ID. Switch to iRacing in a session with your car. Press Ctrl+R (Reload Car Textures); the car flashes white and then shows the files on disk.'},
   {'heading': 'Shokker never touches iRacing',
    'body': 'It only writes two files to the folder where iRacing looks for your custom paint. Only RENDER writes into iRacing; the preview never does. If no car folder is set, the files stay in Shokker\'s own render folder and iRacing cannot see them.'},
   {'heading': 'Two different Ctrl+R',
    'body': 'In Shokker, Ctrl+R starts a render; in iRacing it reloads textures. Press each in its own window.'}],
  'examples': [
   {'title': 'A render that reaches the sim', 'goal': 'Get your paint on the car',
    'settings': {'iRacing User ID': 'Your Customer ID', 'iRacing Car Folder': 'Your car', 'Press': 'RENDER, wait for the green Saved bar', 'In iRacing': 'Ctrl+R'},
    'result': 'The car flashes white and shows your paint and shine.'},
   {'title': 'Check the files exist', 'goal': 'Make sure the render landed in the folder',
    'settings': {'Button': 'Show my files on the Saved bar'},
    'result': 'The folder opens with the paint and spec files.'}],
  'faq': [
   {'q': 'Which files does iRacing read?', 'a': 'The paint (car_num_ID.tga or car_ID.tga) and the spec (car_spec_ID.tga).'},
   {'q': 'What is the ID in the file name?', 'a': 'Your iRacing Customer ID.'},
   {'q': 'The car flashed white and nothing changed.', 'a': 'The files on disk are not the new ones, or the ID or number mode is wrong. Check Show my files.'},
   {'q': 'Does the preview write files?', 'a': 'No. Only RENDER does.'}],
  'mistakes': [
   {'symptom': 'iRacing shows paint-shop colours', 'cause': 'A wrong Customer ID or number mode gives files iRacing never loads, with no error', 'fix': 'Check the ID and the number mode, then render and press Ctrl+R again.'},
   {'symptom': 'Nothing reloads', 'cause': 'Ctrl+R was pressed while Shokker was in front', 'fix': 'Alt+Tab to iRacing, be in a session with your car, then press Ctrl+R.'}],
  'protips': ['After the first successful render, you only need three actions each time: RENDER, Alt+Tab, Ctrl+R.'],
 },
 'workflows.six_words': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Where, what, design, shine',
    'body': 'Choose where (zone), choose what material (base or monolithic), add a design (pattern), add shine texture (spec pattern), and Shokker builds the spec map for iRacing. A zone is a set of pixels plus a look, chosen by colour, layer, box or named part. Zones stack and the zone higher in the list wins when two want the same pixel.'},
   {'heading': 'Base versus monolithic',
    'body': 'A base is a plain material such as gloss, matte, satin, chrome, candy or pearl that changes colour and shine. A monolithic is a complete finish that brings its own colour and texture, such as a colour-shift or a carbon look. Pick it when you want the whole effect.'},
   {'heading': 'Pattern versus spec pattern',
    'body': 'A pattern is a visible design on top (carbon weave, stripes, camo, flames) that changes colour and only a little shine. A spec pattern is a texture for the shine only (metal flake, holographic flecks) and never changes the colour.'},
   {'heading': 'The spec map',
    'body': 'Red is metal, green is roughness (0 is a mirror), blue is clearcoat (16 is the glossiest) and alpha is a lighting mask. Shokker builds it from your zones.'}],
  'examples': [
   {'title': 'Name the parts of a look', 'goal': 'Describe a chrome car with carbon stripes',
    'settings': {'Zone': 'Body pixels', 'Base': 'Chrome', 'Pattern': 'Carbon weave on a stripe zone', 'Spec pattern': 'Metal flake on the hood'},
    'result': 'You can name each layer of the look and know where to change it.'},
   {'title': 'Change only the shine', 'goal': 'Leave your paint colours alone',
    'settings': {'Finish': 'A Foundation finish', 'Colour': 'Source colours'},
    'result': 'Only the spec map changes; your paint stays exactly as it is.'}],
  'faq': [
   {'q': 'What is the difference between a pattern and a spec pattern?', 'a': 'A pattern is visible; a spec pattern changes only the shine.'},
   {'q': 'How many bases can one zone hold?', 'a': 'Up to five stacked as overlays (second to fifth base).'},
   {'q': 'Which zone wins when two overlap?', 'a': 'The one higher in the list.'},
   {'q': 'What does blue mean in the spec map?', 'a': 'Clearcoat. 16 is the glossiest.'}],
  'mistakes': [
   {'symptom': 'A zone with a finish shows nothing', 'cause': 'It has no pixels', 'fix': 'Pick colours, a layer, a box or a named part for the zone.'},
   {'symptom': 'You expect a spec pattern to add colour', 'cause': 'Spec patterns affect shine only', 'fix': 'Use a pattern for visible design.'}],
  'protips': ['Think of a look as four questions: where, what material, what design, what shine texture. Answer them in that order.'],
 },
 'workflows.pro_or_chat': {
  'level': 'beginner',
  'deep': [
   {'heading': 'One car, two doors',
    'body': 'PRO is the default and the full paint shop: open your template, set ID and car folder, and render. Click CHAT in the mode switch to open the chat studio, type what you want and each change has an Undo. Both change the same zones and layer settings, and your paint and zones stay as they are when you switch.'},
   {'heading': 'What only PRO does',
    'body': 'Importing a paint, exporting to iRacing and hand painting. Chat changes zones and layer settings only, and cannot render, save or export for you.'},
   {'heading': 'Chat needs no key',
    'body': 'A built-in designer does a lot for free. An online AI key only adds open-ended requests.'}],
  'examples': [
   {'title': 'Start in PRO, finish in Chat', 'goal': 'Use each door for what it does best',
    'settings': {'1. PRO': 'Open the template, set ID and car folder', '2. CHAT': 'Describe the colours and finishes', '3. PRO again': 'RENDER'},
    'result': 'The file jobs are done in PRO and the design in Chat, on the same car.'},
   {'title': 'Go back and forth', 'goal': 'Switch without losing anything',
    'settings': {'Click': 'PRO or CHAT in the mode switch'},
    'result': 'Nothing is lost by switching.'}],
  'faq': [
   {'q': 'Which should I start with?', 'a': 'PRO is the default. New to Shokker? Try CHAT for your first look.'},
   {'q': 'Does switching lose my work?', 'a': 'No. Your paint and zones stay as they are.'},
   {'q': 'Can Chat render for me?', 'a': 'No. Press RENDER yourself.'}],
  'mistakes': [
   {'symptom': 'You ask Chat to export and nothing happens', 'cause': 'Chat does not do file jobs', 'fix': 'Switch to PRO and press RENDER.'},
   {'symptom': 'You expect hand tools in Chat', 'cause': 'Hand painting is a PRO tool', 'fix': 'Use the PRO toolbar.'}],
  'protips': ['Say places and parts in plain words in Chat; the app names parts of the car for you.'],
 },
 'workflows.one_flat_sheet': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'One picture wrapped over a 3D car',
    'body': 'Your paint is a single flat 2048 by 2048 picture of the car cut open: sides, hood, roof, trunk, bumpers and spoiler lie side by side. iRacing wraps it over the 3D car. That is why the same colour can appear on several islands and why numbers and text are often mirrored or rotated on some islands.'},
   {'heading': 'Size on the sheet is size on the car',
    'body': 'A 64 pixel feature on the sheet is about the size of a mirror on the car. Left, right, top and bottom mean the flat picture, not the car. The helper talks about places with a grid: columns A to H left to right, rows 1 to 8 top to bottom.'},
   {'heading': 'Gradients and copies',
    'body': 'A horizontal gradient runs across the whole sheet, so several islands share the same colour at the same column. Use one zone per side to fade each side separately. To copy a design to the other side use Mirror (layer MIRROR with FLIP or ROT 90, or Mirror Mask for a zone area) and check the CAR view.'}],
  'examples': [
   {'title': 'Fade each side separately', 'goal': 'Avoid one gradient running across all islands',
    'settings': {'Zone 1': 'Left side, gradient', 'Zone 2': 'Right side, gradient', 'Check': 'CAR view'},
    'result': 'Each side fades on its own.'},
   {'title': 'Copy a design to the other side', 'goal': 'Mirror a decal',
    'settings': {'Layer': 'MIRROR', 'Option': 'FLIP or ROT 90', 'Check': 'CAR view'},
    'result': 'The design lands the right way round on the other side.'}],
  'faq': [
   {'q': 'Why is text mirrored on the car?', 'a': 'Some islands are drawn mirrored or rotated on the sheet. Flip or rotate your placement.'},
   {'q': 'How big is a 64 pixel feature on the car?', 'a': 'About the size of a side mirror.'},
   {'q': 'Can I resize the canvas?', 'a': 'No. iRacing needs 2048 by 2048 or 1024 by 1024.'}],
  'mistakes': [
   {'symptom': 'A copied design lands flipped', 'cause': 'One side of the sheet may be upside down', 'fix': 'Use FLIP or ROT 90 and check the CAR view.'},
   {'symptom': 'Two sides show the same gradient colour', 'cause': 'One zone spans several islands at the same columns', 'fix': 'Use one zone per side.'}],
  'protips': ['Use named parts instead of hunting for islands: a zone can choose Left side, Roof or Hood by name.'],
 },
 'workflows.first_paint': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Seven moves',
    'body': 'Open the template and wait for your paint under SOURCE. Type your iRacing User ID and pick your car in iRacing Car Folder (one-time settings). Press Pick Color From Car in the Zone panel and click a colour on SOURCE. Click the BASE swatch, open Foundations > Foundation Bases, choose a base and press Apply. Switch the template layers (Wire, Mask, Car_Mandatory) off. Press RENDER and wait for the green Saved bar. Alt+Tab to iRacing and press Ctrl+R.'},
   {'heading': 'The Tutorial does this with you',
    'body': 'Press Tutorial in the header any time. It shows the next step as a small chip and checks it off when you do it.'},
   {'heading': 'Why metal can look dark',
    'body': 'Chrome over a dark colour looks dark in the sim. Use a light colour under metal.'}],
  'examples': [
   {'title': 'A chrome hood in ten minutes', 'goal': 'Your first visible result',
    'settings': {'Open': 'The template for your car', 'Zone': 'Pick Color From Car, click the colour of the hood', 'Base': 'Foundations > Foundation Bases > Chrome, Apply', 'Layers': 'Wire, Mask, Car_Mandatory off', 'Then': 'RENDER, Ctrl+R in iRacing'},
   'result': 'Your hood is chrome in the sim.'},
   {'title': 'Prove the chain first', 'goal': 'Check everything is set up before designing',
    'settings': {'Do': 'Render once with no changes'},
    'result': 'You should see your own paint in iRacing. If not, fix IDs and folders before redesigning.'}],
  'faq': [
   {'q': 'Do I need patterns or layers for my first paint?', 'a': 'No. A zone with a base finish is enough.'},
   {'q': 'Where do I find the Tutorial?', 'a': 'The Tutorial button in the header.'},
   {'q': 'Nothing shows in iRacing.', 'a': 'Work through the not-in-iRacing article before redesigning.'},
   {'q': 'Do I set the ID every time?', 'a': 'No. The ID and car folder are one-time settings.'}],
  'mistakes': [
   {'symptom': 'The chrome looks nearly black', 'cause': 'Chrome reflects dark colour under it', 'fix': 'Use a light colour under metal.'},
   {'symptom': 'Lines appear on the car', 'cause': 'Wire, Mask or Car_Mandatory was left on', 'fix': 'Turn them off in Layers, render again.'}],
  'protips': ['If you only follow one habit, make it this: render once with no changes the first time, then design.'],
 },
 'workflows.loading_paint': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Layered or flat',
    'body': 'PSD/XCF/ORA opens a layered template where every layer is editable, so zones can target the body only, keep sponsors safe and hide template guide layers. TGA/PNG/JPEG opens one flat picture: fine for a quick colour change, but you cannot separate the number from the body except by colour. Either way the file must be 2048 by 2048 (or 1024 by 1024).'},
   {'heading': 'Loading time and layers',
    'body': 'A big PSD can take up to a minute. A message at the bottom shows progress and, at the end, how many layers loaded. Only pixel layers import from a PSD, so rasterize text and shapes first.'},
   {'heading': 'Other programs',
    'body': 'GIMP: export as .ora or .psd, or use the .xcf directly. Krita: .ora. Use the buttons so Shokker has the full path; a file name alone in Source Paint is not enough.'}],
  'examples': [
   {'title': 'Layered template', 'goal': 'Keep numbers and sponsors apart from the body',
    'settings': {'Button': 'PSD/XCF/ORA', 'Layer names': 'Car Paint, Numbers, Sponsors', 'Before render': 'Wire, Mask, Car_Mandatory, Turn Off Before Exporting TGA group off'},
    'result': 'Zones can target the body only.'},
   {'title': 'Quick flat change', 'goal': 'Recolour a finished TGA',
    'settings': {'Button': 'TGA/PNG/JPEG'},
    'result': 'You get one flat picture with no layers.'}],
  'faq': [
   {'q': 'Which files open with the PSD/XCF/ORA button?', 'a': 'Only .psd, .xcf and .ora.'},
   {'q': 'My PSD text is missing.', 'a': 'Only pixel layers import. Rasterize text and shape layers first.'},
   {'q': 'Does the size matter?', 'a': 'Yes. It must be 2048 by 2048 or 1024 by 1024. Do not resize.'},
   {'q': 'Can Krita files be used?', 'a': 'Yes, as .ora.'}],
  'mistakes': [
   {'symptom': 'The load seems stuck', 'cause': 'A big PSD takes up to a minute', 'fix': 'Wait for the message at the bottom to say how many layers loaded.'},
   {'symptom': 'Source Paint will not load a typed name', 'cause': 'A name alone has no full path', 'fix': 'Use the buttons to pick the file.'}],
  'protips': ['Name your layers (Car Paint, Numbers, Sponsors). Clear names let you and the helper target exactly one part.'],
 },
 'workflows.user_id_and_folder': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The two boxes that matter most',
    'body': 'Shokker names every file with your Customer ID and copies it into your car\'s paint folder. If either is wrong, iRacing silently shows paint-shop colours instead of your paint.'},
   {'heading': 'Finding the ID',
    'body': 'In iRacing click the helmet icon (top right), then Profile. The number at the top is your Customer ID, 4 to 7 digits. It is not your car number: Shokker has no car-number field. Shokker can often fill it from files already in your paint folders.'},
   {'heading': 'Finding the folder',
    'body': 'Run your car once in iRacing so it creates the paint folder under Documents, then iRacing, then paint. In Shokker open the car menu next to iRacing Car Folder and pick your car (read the folder name; newest is not always yours) or use the folder button.'},
   {'heading': 'Number mode',
    'body': 'Custom Number or Sim-Stamped Number only chooses the file name: car_num_ID.tga or car_ID.tga. Match iRacing\'s Hide Car Numbers setting: ON means Custom Number.'}],
  'examples': [
   {'title': 'One-time setup', 'goal': 'Make renders land where iRacing looks',
    'settings': {'iRacing User ID': 'Customer ID from Profile (4 to 7 digits)', 'iRacing Car Folder': 'Car menu, your car', 'Number mode': 'Custom Number if Hide Car Numbers is ON', 'Check': 'Render once and press Show my files'},
    'result': 'Your files are in the right folder with the right names.'},
   {'title': 'Fix a paint that iRacing ignores', 'goal': 'Find out what is wrong',
    'settings': {'Check 1': 'ID has 4 to 7 digits', 'Check 2': 'Folder matches the car you drive', 'Check 3': 'Number mode matches Hide Car Numbers'},
    'result': 'The mismatch shows up, usually the folder or the number mode.'}],
  'faq': [
   {'q': 'Where do I find my Customer ID?', 'a': 'In iRacing, click the helmet icon, then Profile. It is at the top.'},
   {'q': 'Is it my car number?', 'a': 'No. Shokker has no car-number field.'},
   {'q': 'My paint for car A is ignored.', 'a': 'It is in the folder of car B. iRacing ignores a paint in the wrong car\'s folder.'},
   {'q': 'Why is a project from a friend changing my settings?', 'a': 'Loading someone else\'s project can overwrite your ID and folder. Check them after loading.'}],
  'mistakes': [
   {'symptom': 'iRacing shows paint-shop colours', 'cause': 'Wrong ID, folder or number mode', 'fix': 'Fix the three settings and render again.'},
   {'symptom': 'The car menu has no folder for your car', 'cause': 'iRacing has not created it yet', 'fix': 'Run the car once in a test session.'}],
  'protips': ['Press Show my files on the Saved bar after your first render. Seeing the three expected files proves the setup.'],
 },
 'workflows.install_update': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Installing',
    'body': 'The installer is a small web setup that installs in one click, adds a desktop shortcut and keeps your settings and projects when you uninstall. If it asks for a licence key, type it in the Activate window.'},
   {'heading': 'The update banner',
    'body': 'When a newer version exists, a banner appears under the title bar. Download Update downloads it, then the button changes to Install & Restart. Remind Me Later hides the banner for 24 hours. A downloaded update also installs when you close the app.'},
   {'heading': 'Save first',
    'body': 'Installing restarts the app and unsaved work is lost, so use Save / Open first. If a message says the app and screen versions differ, a restart is needed.'}],
  'examples': [
   {'title': 'A safe update', 'goal': 'Update without losing work',
    'settings': {'Step 1': 'Save your project', 'Step 2': 'Download Update', 'Step 3': 'Install & Restart'},
    'result': 'The new version opens and your settings are kept.'},
   {'title': 'Not now', 'goal': 'Finish a design before updating',
    'settings': {'Button': 'Remind Me Later'},
    'result': 'The banner hides for 24 hours.'}],
  'faq': [
   {'q': 'Does uninstalling delete my settings?', 'a': 'No. Uninstalling keeps your app data.'},
   {'q': 'Do I have to update right away?', 'a': 'No. You choose when to download. Nothing is forced.'},
   {'q': 'Something looks off after an update.', 'a': 'Close Shokker fully and open it once more.'},
   {'q': 'Why is a finish missing that a friend has?', 'a': 'You are on an older version. Update.'}],
  'mistakes': [
   {'symptom': 'You lost unsaved work', 'cause': 'Install & Restart closes the app', 'fix': 'Save your project before installing.'},
   {'symptom': 'The banner never shows', 'cause': 'It appears only when a newer version exists', 'fix': 'You are up to date.'}],
  'protips': ['Update between projects, not during one. A restart is harmless when everything is saved.'],
 },
 'workflows.tutorial_quests': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Eleven quests',
    'body': 'Five core quests: Get your car in here, Claim your pixels, Drop a finish, Point SPB at iRacing, Send it to the track. Six further quests open after the core five: Break up the surface (pattern), Feel the material (spec channels), Stack a second material (overlays), Paint inside the lines (restrict a zone), Fix it by hand (brush) and Keep it forever (Save SHOKK).'},
   {'heading': 'How it guides',
    'body': 'A next-move chip and a checklist highlight the real control and check themselves off when you do the thing. It never clicks for you. A skill\'s hint retires after you have done it three times.'},
   {'heading': 'Collapsed sections',
    'body': 'While the wheels are on and you are at level 1, advanced zone sections start collapsed. Click a section header to peek; everything opens for good after your first render.'}],
  'examples': [
   {'title': 'Follow the core five', 'goal': 'Learn the basic loop',
    'settings': {'Press': 'Tutorial in the header', 'Follow': 'The chip through all five core quests'},
    'result': 'You have rendered your first paint and the six further quests open.'},
   {'title': 'Turn it off', 'goal': 'Remove the guide',
    'settings': {'Press': 'The same Tutorial button'},
    'result': 'The chip and checklist disappear.'}],
  'faq': [
   {'q': 'Does the Tutorial click for me?', 'a': 'No. It highlights the control and checks the step off when you do it.'},
   {'q': 'How many quests are there?', 'a': 'Eleven: five core and six further.'},
   {'q': 'Why are some sections collapsed?', 'a': 'At level 1 advanced zone sections start collapsed. They all open after your first render.'},
   {'q': 'Can I turn it back on?', 'a': 'Yes. Press Tutorial again.'}],
  'mistakes': [
   {'symptom': 'You cannot find a control', 'cause': 'The section is collapsed while the wheels are on', 'fix': 'Click the section header to peek.'},
   {'symptom': 'An old guide says ten quests', 'cause': 'The count changed to eleven', 'fix': 'Follow the chip in the app.'}],
  'protips': ['Finish the core five even if you plan to turn the guide off. They teach the exact loop you will repeat for every paint.'],
 },
}
