"""v3 depth for the concepts domain (lane C, 2026-10-04). Facts: SPB_WIKI.html Hard-Won Lessons (lines 540-642), docs/FINISH_LAW.md, CLAUDE.md house rules."""
V3 = {
 'concepts.green_is_not_good': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'What the automatic checks actually look at',
    'body': 'Every finish in the catalogue is run through scripts that measure five things: how different it is from every other finish (sameness), how fine its detail is (scale), whether the shine map follows the paint (follow), whether the shine map is its own design and not a shared one (story), and whether the paint is not mostly solid black or white (coverage). A finish passes when all five clear their bars. Those bars were fitted to the owner\'s own yes/no verdicts on 24 finishes and agree with him on 20 of them, which is good but not perfect. A check can only see what it measures.'},
   {'heading': 'Why a green tick can still hide a bad look',
    'body': 'A real case: a 60-finish set shipped on only 5 different shine maps, and every check said green, because the sameness check treated a copy shifted sideways as a brand-new design. Another set of three finishes passed every bar while nearly solid black. The lesson baked into the house rules: a test you could never fail honestly is not measuring what you care about, and a score that rewards the wrong thing (big blobby shapes instead of fine detail) drags designs the wrong way.'},
   {'heading': 'The order of trust',
    'body': 'Your eye at full size on the car comes first, the spec views second, the automatic scores last. When a score and your eye disagree, the eye wins. The only finishes protected from change at any cost are the five gold standards (Hologram Metal, Dichroic Skin, Truchet Glass, Cinder Pulse, Hologram Noir), because they passed the owner\'s eye, not just the numbers.'}],
  'examples': [
   {'title': 'Judge a finish the right way', 'goal': 'Decide whether a finish is really good before you commit a whole car to it',
    'settings': {'Zone': 'Paint one body panel only', 'Finish': 'the finish you are testing', 'View': 'Render, then zoom to 100% (1:1)', 'Spec views': 'Look at R METAL, G ROUGH and B COAT'},
    'result': 'You see the detail at the size the car will show it. Fine texture across the panel is good. One big blob, a smooth ramp or a flat colour means pick another.'},
   {'title': 'Compare against plain gloss', 'goal': 'Check that a finish is adding something real',
    'settings': {'Zone 1': 'the finish', 'Zone 2 (a copy on another panel)': 'plain Gloss base in the same colour', 'View': 'Render at 1:1'},
    'result': 'If you cannot tell the two apart at normal viewing distance, the finish is not earning its place on that car.'}],
  'faq': [
   {'q': 'Why does a finish with a great rating look bad to me?', 'a': 'The rating measures a few things, not taste. Trust what you see at full size. If your eye says no, the answer is no.'},
   {'q': 'What is the 1:1 view?', 'a': 'Looking at the render at 100% zoom so one screen pixel is one paint pixel. It is the only view that shows the true size of the detail.'},
   {'q': 'Are some finishes safe from being changed?', 'a': 'Yes. Five gold-standard finishes (Hologram Metal, Dichroic Skin, Truchet Glass, Cinder Pulse, Hologram Noir) are never changed, because the owner approved them by eye.'},
   {'q': 'Does a green check mean a finish is original?', 'a': 'It means it passed the sameness bar against every other finish in the catalogue. A recolour of an existing finish does not count as new work, and the check ignores colour on purpose.'}],
  'mistakes': [
   {'symptom': 'You pick a finish only because its card shows a high score', 'cause': 'The score is only a filter that removes obvious failures', 'fix': 'Put it on your car, render, and look at 1:1 before you decide.'},
   {'symptom': 'The finish looks smeared or blobby on the car', 'cause': 'The detail is large on the sheet, and the sheet covers the whole car', 'fix': 'Pick a finish with fine detail, or raise the pattern scale so features get smaller.'}],
  'protips': ['A thumbnail hides how coarse a finish is: the paint sheet covers a whole car, so anything that looks small in a thumbnail is huge on the car.',
              'Look for a shine map that follows the paint pattern. When the two line up, the finish looks designed; when they ignore each other, it looks pasted on.'],
  'sources_add': ['docs/FINISH_LAW.md:1'],
 },
 'concepts.nothing_changed': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The four reasons, most likely first',
    'body': 'One: the preview picture is stale and has not redrawn (press F5). Two: the zone you edited is muted, or a zone above it covers the same area, so you cannot see your change; zones higher in the list win where they overlap. Three: you are running an older copy of the app than the one that has the change or the finish. Four: the thing you changed only matters in the saved files, not in the preview (a spec tweak on a very fine pattern, for example, can look flat in the small preview).'},
   {'heading': 'Why an older copy shows different finishes',
    'body': 'The finish list on your screen is built from what your installed copy knows. A friend on a newer version can see finishes that yours does not list at all. Updates arrive through the update banner, and the new version only takes effect after a restart.'},
   {'heading': 'How to test it in one minute',
    'body': 'Make the change very large on purpose: set a zone to a loud colour or a very different finish and press F5. If even that does nothing, the cause is the zone being hidden or covered. If it appears, your earlier change was simply too small to see at preview size.'}],
  'examples': [
   {'title': 'A finish seems to do nothing', 'goal': 'Find out why a finish change is invisible',
    'settings': {'Step 1': 'Press F5', 'Step 2': 'Open the zone list and check the zone is not muted', 'Step 3': 'Drag the zone to the top of the list', 'Step 4': 'Look for the update banner and restart if one is waiting'},
    'result': 'In most cases the change appears at step 1 or 2. If it appears only after moving the zone up, another zone was covering it.'},
   {'title': 'A finish a friend has is missing from your picker', 'goal': 'Get a finish that exists in a newer version',
    'settings': {'Check': 'Compare version numbers with your friend', 'Action': 'Install the update from the banner and restart'},
    'result': 'After the restart the picker lists the newer finishes.'}],
  'faq': [
   {'q': 'I changed a colour and the car looks the same. Why?', 'a': 'Most often the preview has not redrawn or a zone above covers the area. Press F5 and check the zone order.'},
   {'q': 'Does a muted zone still count?', 'a': 'A muted zone is switched off, so it paints nothing until you unmute it.'},
   {'q': 'Do I need to restart after an update?', 'a': 'Yes. A downloaded update only takes effect after the app restarts.'},
   {'q': 'What do I send if it is still wrong?', 'a': 'Use Report a Problem in the Settings gear. It attaches the details a fix needs.'}],
  'mistakes': [
   {'symptom': 'You keep changing settings and nothing moves', 'cause': 'A zone above yours covers the same area', 'fix': 'Move your zone to the top of the list or shrink the zone above it.'},
   {'symptom': 'You keep reinstalling but the picker is the same', 'cause': 'The installed copy was never restarted after the update', 'fix': 'Close the app fully and open it again, then check the version.'}],
  'protips': ['Make a test change big and obvious first. Only fine-tune once you have proven the zone is really showing.'],
 },
 'concepts.preview_vs_truth': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Preview size versus final size',
    'body': 'The live preview is drawn at 1024 pixels across, while the final paint is 2048. Anything sized in fixed pixels is therefore twice as large in the preview as it will be on the final paint, and fine effects can average out and look flat in the small picture. The Render button draws the real thing at full size.'},
   {'heading': 'Preview is a design aid, the saved file is the product',
    'body': 'A preview that looks right does not prove the saved file is right. A past bug lived entirely in the gap between the two: a rotated element looked right in the preview and was cut off when it was applied. The habit that avoids it is to make your last check on the rendered result and, for iRacing, on the car in the sim.'},
   {'heading': 'Rendering at both sizes',
    'body': 'Some problems only show at one size. If a pattern looks too big or too small, render once at the final size before you change anything, so you fix the real problem and not a preview difference.'}],
  'examples': [
   {'title': 'Final check before you save to iRacing', 'goal': 'Confirm the saved result matches what you designed',
    'settings': {'Step 1': 'Press RENDER at full size', 'Step 2': 'Zoom to 100% and inspect each panel', 'Step 3': 'Check the R METAL, G ROUGH and B COAT views', 'Step 4': 'Save to the iRacing folder, then press Ctrl+R in the sim'},
    'result': 'You have seen the paint, the shine maps and the sim result, so nothing surprises you on track.'},
   {'title': 'A pattern looks too large in the preview', 'goal': 'Decide whether to change the pattern scale',
    'settings': {'Do first': 'Render at full size', 'Compare': 'Preview versus render at the same panel'},
    'result': 'If the render shows the right size, leave the scale alone; the preview was only drawn smaller.'}],
  'faq': [
   {'q': 'How big is the preview compared to the final paint?', 'a': 'The preview is drawn at 1024 pixels across; the final paint is 2048 (or 1024 if your car is a 1024 sheet).'},
   {'q': 'Why does my fine texture look flat in the preview?', 'a': 'Very fine effects average out when drawn small. Render at full size to see them.'},
   {'q': 'Do I need to check in the sim?', 'a': 'Yes for your last check. Save to the iRacing folder and press Ctrl+R in the sim to reload the car textures.'},
   {'q': 'What should I send if the render looks different from the preview?', 'a': 'Send a problem report from the Settings gear with your project, the car and your number mode.'}],
  'mistakes': [
   {'symptom': 'You tune a pattern until the preview looks perfect, then the render looks wrong', 'cause': 'The preview is half the size of the final paint', 'fix': 'Tune against a full-size render and use the preview only for rough placement.'},
   {'symptom': 'You skip the sim check', 'cause': 'A good render still can look different on the car because of the shine map and the track lighting', 'fix': 'Always look at the car in the sim after a save and press Ctrl+R to reload.'}],
  'protips': ['If you only have time for one check, make it the full-size render at 100% zoom. It catches most surprises.'],
 },
 'concepts.reporting_with_evidence': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'One change at a time',
    'body': 'The fastest way to find a cause is to go back to the last good state and change one thing, check, then change the next. In one past case, a paint looked far too strong because one setting was being applied twice (once as a zone strength and once after mixing). It was found only by changing one field at a time and comparing the results.'},
   {'heading': 'What to send',
    'body': 'A description alone rarely shows the cause. The useful package is: your saved project, the report from Report a Problem in the Settings gear, which car you used, your number mode (Custom Number or Sim-Stamped Number), your User ID, what you see in the sim, and the single change that made it happen.'},
   {'heading': 'Why real settings beat memory',
    'body': 'Fixes start from your actual file and your actual values. Quoted numbers from memory are often wrong; the shipped data is the authority. That is why the report carries the real zone settings and not a retelling.'}],
  'examples': [
   {'title': 'Narrow down a surprising result', 'goal': 'Find which setting caused a bad look',
    'settings': {'Step 1': 'Save the project now', 'Step 2': 'Undo back to the last good state', 'Step 3': 'Change one setting and render', 'Step 4': 'Repeat for the next setting until the problem returns'},
    'result': 'The last setting you changed before it broke is the cause or a part of it.'},
   {'title': 'Send a problem report', 'goal': 'Give support everything needed in one message',
    'settings': {'Where': 'Settings gear, Report a Problem', 'Add': 'Car name, number mode, User ID, what you see in the sim', 'Attach': 'The saved project'},
    'result': 'Support can reproduce the problem from your real file.'}],
  'faq': [
   {'q': 'Is a screenshot enough?', 'a': 'Rarely. A screenshot shows the result but not the settings behind it. Send the report and the project.'},
   {'q': 'What is my User ID?', 'a': 'It is your iRacing Customer ID. It decides the file names your paint is saved under.'},
   {'q': 'Why do you ask for my number mode?', 'a': 'Custom Number saves car_num_ID files and Sim-Stamped Number saves car_ID files. A mismatch with the sim setting is a common cause.'}],
  'mistakes': [
   {'symptom': 'You change five things and then report that it broke', 'cause': 'Nobody can tell which change did it', 'fix': 'Undo to the last good state and change one thing at a time.'},
   {'symptom': 'Support cannot reproduce your problem', 'cause': 'The report had no project and no car name', 'fix': 'Save the project and attach it with the report.'}],
  'protips': ['Write down the one change that made it happen. That sentence is worth more than a page of description.'],
 },
 'concepts.what_makes_a_finish_good': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Fields, not posters',
    'body': 'The paint sheet covers a whole car, so a good finish is a fine texture spread across all of it. The target is detail about 8 to 32 pixels across, over every panel. A big picture in the middle of the sheet ends up as a smear on one door. Finishes follow a house rule of full coverage (no dead corners) and fine detail (never a smooth ramp or a fat blob).'},
   {'heading': 'One idea per collection',
    'body': 'A collection should tell one story with one arc, not be a grid of colour times pattern. Grids feel samey, and the automatic checks cannot see it because a recolour scores as well as an original. A collection that grew from five grids into 50 distinct objects in five chapters is the model.'},
   {'heading': 'Small, turned hidden details',
    'body': 'Hidden features and motifs should be small (70 to 225 pixels on the sheet) and turned and mirrored in different directions. Larger, upright shapes read as stickers. The best-looking effects keep most cells dark with a few strong colour states, rather than a field of random bright squares.'},
   {'heading': 'The shine map follows the paint',
    'body': 'A finish also has a shine map (metal, roughness, clearcoat). It is built against the rendered paint, so a bright pattern edge has a matching shine edge. Faults to look out for: two families of shine settings in one set, roughness that rises and falls for no reason, and a set that drifts to one colour.'}],
  'examples': [
   {'title': 'Pick between two finishes', 'goal': 'Choose the better one for a car',
    'settings': {'Both': 'Applied to the same panel', 'View': 'Render at 100% zoom', 'Look for': 'Detail all over, not one big shape; shine edges matching paint edges'},
    'result': 'The finish with fine, even detail whose shine follows the paint is the better choice.'},
   {'title': 'Place a hidden-detail finish', 'goal': 'Keep hidden marks from looking like decals',
    'settings': {'Mark size': 'About 70 to 225 px on the sheet', 'Direction': 'Turned and mirrored', 'Spread': 'Evenly across the panels'},
    'result': 'The marks read as part of the surface instead of stickers.'}],
  'faq': [
   {'q': 'What size should the detail be?', 'a': 'About 8 to 32 pixels on the 2048 sheet, across the whole car.'},
   {'q': 'Why does a new colour of the same finish not count as new?', 'a': 'The sameness check ignores colour, so a recolour is judged the same as the original.'},
   {'q': 'What is a shine map?', 'a': 'The set of metal, roughness and clearcoat values that decide how the paint catches light. See the spec views.'}],
  'mistakes': [
   {'symptom': 'A finish looks like confetti', 'cause': 'Bright squares everywhere, with no dark ground to rest the eye', 'fix': 'Prefer finishes where most cells are dark with a few strong accents.'},
   {'symptom': 'A finish looks like a sticker on the car', 'cause': 'Large upright motifs', 'fix': 'Pick one with small, turned and mirrored motifs.'}],
  'protips': ['If a collection feels samey, look for its one idea. A good collection has a clear arc; a grid of swaps does not.'],
  'sources_add': ['docs/FINISH_LAW.md:1', 'CLAUDE.md:1'],
 },
}
