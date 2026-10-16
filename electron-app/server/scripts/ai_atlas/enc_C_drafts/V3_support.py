"""v3 depth for the support (troubleshooting) domain, lane C, 2026-10-04.
Format: symptom -> every cause -> fix steps -> how to confirm. Facts are the ones already sourced in each article
(docs/ai_knowledge/10_support_troubleshooting.md, js/spb-support-answers.js, engine/SPEC_MAP_REFERENCE.md, electron-app/main.js)."""
V3 = {
 'support.not_in_iracing': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Every cause, most likely first',
    'body': '1. Wrong User ID (a car number or a made-up number instead of your Customer ID). 2. Number switch does not match iRacing Hide Car Numbers. 3. Car folder is not the folder of the car you are driving. 4. The render never finished or never copied (no green Saved bar). 5. You did not reload (Ctrl+R in iRacing) or did not restart iRacing after changing Hide Car Numbers. 6. The paint is the wrong size or not a real TGA. 7. Black or missing parts: the glass alpha was not filled. 8. Trading Paints Downloader swapped the files. 9. Someone else\'s project overwrote your ID and folder. iRacing shows no error for any of them.'},
   {'heading': 'How to confirm the fix',
    'body': 'After RENDER press Show my files on the green Saved bar. You should see your paint (car_num_<ID>.tga or car_<ID>.tga) and car_spec_<ID>.tga, newer than your last change, and the ID in the file name must be yours. Then press Ctrl+R in iRacing with your car on track. If the car changes, it was a reload problem; if not, go back to the cause list.'},
   {'heading': 'Why the order matters',
    'body': 'A wrong but valid ID renders perfectly and produces files iRacing never loads for you, so the render looks healthy while nothing appears. Fix the cheap checks (ID, switch, folder) first; they cause most cases.'}],
  'examples': [
   {'title': 'The car number typed as the ID', 'goal': 'Find why a green render shows nothing',
    'settings': {'Symptom': 'Saved bar is green, car is white in iRacing', 'Check': 'iRacing User ID box holds the car number (for example 7)', 'Fix': 'Type your Customer ID (4 to 7 digits, helmet icon > Profile in iRacing), RENDER again, Ctrl+R in iRacing'},
    'result': 'The new files carry your ID and iRacing loads them.'},
   {'title': 'Hide Car Numbers ON but Sim-Stamped selected', 'goal': 'Match the number switch',
    'settings': {'iRacing': 'Settings > Graphics > Hide Car Numbers ON', 'Shokker': 'Switch to Custom Number (writes car_num_<ID>.tga)', 'Then': 'RENDER, restart iRacing if you just changed the setting, Ctrl+R'},
    'result': 'iRacing finds car_num_<ID>.tga and shows your paint.'},
   {'title': 'Not sure which mode iRacing wants', 'goal': 'Cover both cases',
    'settings': {'Do': 'Render once in Custom Number, then once in Sim-Stamped Number'}, 'result': 'Both files stay in the folder and iRacing loads the one it needs.'}],
  'faq': [
   {'q': 'Why does iRacing not show an error?', 'a': 'It simply finds no file with your name on it and falls back to the paint-shop colours.'},
   {'q': 'Is the User ID my car number?', 'a': 'No. It is your iRacing Customer ID, 4 to 7 digits.'},
   {'q': 'Can Shokker read my Hide Car Numbers setting?', 'a': 'No. Only you can look at it in iRacing.'},
   {'q': 'Is there a quick way to check all this?', 'a': 'Yes. Press Check my setup in the Chat panel; it reads your settings and folder and marks the first wrong step.'}],
  'mistakes': [
   {'symptom': 'Paint appears for you but not for other drivers', 'cause': 'iRacing only shows other drivers the files in their paint folder', 'fix': 'That is what Trading Paints does; see the Trading Paints article.'},
   {'symptom': 'Paint disappears after loading a friend\'s project', 'cause': 'It overwrote your ID and car folder', 'fix': 'Check both boxes after loading any project.'}],
  'protips': ['Do the checks in order and render after each fix. Changing three things at once hides which one mattered.'],
 },
 'support.colours_differ': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Every cause',
    'body': 'Darker or greyer: metal over a dark paint (iRacing multiplies paint by the metal), or a cloudy sky. Lines or masks on the car: template guide layers left on. Numbers twice or sparkly: iRacing stamps its own numbers and sponsors with the material of the spec under them. Sparkly or flat everywhere: the spec, not the colour. No shine: an old or missing spec file. The preview itself is only a quick flat picture.'},
   {'heading': 'Where to look first',
    'body': 'Switch the preview views to R METAL, G ROUGH and B COAT. Metal should be bright red (about 255) on chrome and G ROUGH near black. Most differences hide in these views, not in the colour view.'},
   {'heading': 'How to confirm',
    'body': 'After the fix, render again, press Ctrl+R in iRacing and judge at driving distance. A spec file newer than your last change in Show my files means the sim has the new shine.'}],
  'examples': [
   {'title': 'Chrome hood looks dark', 'goal': 'Make chrome read in the sim',
    'settings': {'Check': 'R METAL bright red, G ROUGH near black', 'Fix': 'Lighten the body colour under it, or use a Foundation chrome finish with Source colours kept', 'Then': 'RENDER, Ctrl+R'},
    'result': 'Brighter chrome. On an overcast track mirror chrome can still look grey; that is the sky.'},
   {'title': 'Lines across the car', 'goal': 'Remove guide lines',
    'settings': {'Layers panel': 'Switch OFF Wire, Mask, Car_Mandatory and the group Turn Off Before Exporting TGA', 'Then': 'RENDER again'},
    'result': 'The lines are gone from the file.'},
   {'title': 'Sparkly numbers', 'goal': 'Calm stamped numbers',
    'settings': {'Where': 'Decal Rescue Kit in the toolbar', 'Choose': 'Flat, satin or gloss non-metal spec'},
    'result': 'Numbers get a plain spec while your paint stays.'}],
  'faq': [
   {'q': 'Should I repaint my colours to match?', 'a': 'No. Fix the spec or the template layers first.'},
   {'q': 'Why is mirror chrome grey on a cloudy track?', 'a': 'Flat mirror metal reflects the sky. Try a track with a brighter sky.'},
   {'q': 'What if there is no shine at all?', 'a': 'Check car_spec_<ID>.tga exists and is new, then Ctrl+R. If it still looks old, move car_spec_<ID>.mip out of the folder and reload.'}],
  'mistakes': [
   {'symptom': 'Judging colour from the zoomed-in preview', 'cause': 'The sim adds light and shadow', 'fix': 'Judge in the sim at driving distance.'},
   {'symptom': 'Old shine in the sim', 'cause': 'The spec file is older than your change', 'fix': 'Render, then Ctrl+R.'}],
  'protips': ['Compare the three spec views, not only the colour view. Most surprises are in the spec.'],
 },
 'support.flat_or_shiny': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Every cause',
    'body': 'The finish is the wrong one for the look. SPEC STRENGTH is below 100 percent so the finish fades to neutral. A SPEC slider (R METAL, G ROUGH, B COAT) was pushed the wrong way. A zone above it covers it. INDEPENDENT SPEC is hiding a change made on the base. The preview colour view cannot show a mirror at all.'},
   {'heading': 'The numbers',
    'body': 'Roughness 0 is a perfect mirror and 255 is flat matte; reference points are chrome near 2, gloss near 30, satin near 95, soft matte near 200. Clearcoat is backwards: 16 is the glossiest, 255 the dullest, 0 means no coat. Metal is red, with 255 full metal.'},
   {'heading': 'How to confirm',
    'body': 'Open G ROUGH and B COAT in the preview. Black in G ROUGH is a mirror; dark in B COAT is a glossy coat. When those match your intent, render and check in the sim.'}],
  'examples': [
   {'title': 'Gloss that looks dead', 'goal': 'Bring the shine back',
    'settings': {'SPEC STRENGTH': 'Raise back to 100 in steps of 5', 'G ROUGH slider': 'Negative values make it shinier', 'Check': 'B COAT dark'},
    'result': 'A tighter, brighter highlight.'},
   {'title': 'Satin that throws a harsh mirror', 'goal': 'Soften',
    'settings': {'Finish': 'Satin or Soft Matte', 'G ROUGH slider': 'Positive values make it duller'},
    'result': 'A soft sheen near roughness 95.'}],
  'faq': [
   {'q': 'Does Strength 0 mean no shine?', 'a': 'No. Strength 0 is neutral, not zero shine.'},
   {'q': 'Which slider range is there?', 'a': '-127 to 127 in steps of 5; Shokker then clips to safe limits.'},
   {'q': 'Why change the finish rather than the sliders?', 'a': 'Large slider moves can cancel the finish; a better finish is cleaner.'}],
  'mistakes': [
   {'symptom': 'Spec looks wrong after resizing a spec picture elsewhere', 'cause': 'Resizing can create forbidden values', 'fix': 'Render again instead.'},
   {'symptom': 'Coat value 1 to 15 does not stay', 'cause': 'Shokker lifts 1 to 15 to 16', 'fix': 'Use 0 for no coat or 16 and up.'}],
  'protips': ['Move one slider by 5 at a time and watch the spec views. Big jumps hide what each one does.'],
 },
 'support.zone_no_show': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Every cause in order',
    'body': '1. The eye icon has the zone muted. 2. It lacks a colour or a finish. 3. A zone higher in the list claims the same pixels (the lower number wins). 4. Colour tolerance catches only part of the area. 5. It is limited to a layer that is hidden or missing, which paints nothing on purpose. 6. Intensity is 0. 7. The finish is a Foundation finish with Source colours kept, which changes the shine only. 8. The preview is stale. 9. A saved Spec Sculpt or imported spec map holds the shine.'},
   {'heading': 'The fastest test',
    'body': 'Mute every other zone. If your zone shows, an overlap is the cause; drag it higher. If it still shows nothing, read the message on its card, which names the missing piece.'},
   {'heading': 'How to confirm',
    'body': 'After the fix the preview changes. Press F5 to rebuild it, then RENDER. RENDER is never greyed for a missing zone; it shows a message instead.'}],
  'examples': [
   {'title': 'Zone with a colour but no finish', 'goal': 'Make it appear',
    'settings': {'Message': 'To render, pick a color on the paint, then assign a Finish from the library to each zone', 'Fix': 'Pick a finish for the zone'},
    'result': 'The zone claims pixels and shows.'},
   {'title': 'Hidden by a zone above', 'goal': 'Win the pixels',
    'settings': {'Fix': 'Drag the zone higher in the list; keep Everything Else at the bottom'},
    'result': 'Your zone wins the shared pixels.'},
   {'title': 'Limited to a layer that is gone', 'goal': 'Find the empty restriction',
    'settings': {'Test': 'Clear Restrict to layer'}, 'result': 'It paints again, which shows the restriction was the cause.'}],
  'faq': [
   {'q': 'Why does a Foundation finish change nothing visible?', 'a': 'By design it changes the shine only and leaves the colour as it was.'},
   {'q': 'Does a muted zone render?', 'a': 'No. It is skipped in the preview and in RENDER.'},
   {'q': 'What does intensity 0 do?', 'a': 'It hides the zone even when it is set up correctly.'}],
  'mistakes': [
   {'symptom': 'Only part of the area changes', 'cause': 'Colour tolerance too low', 'fix': 'Raise it.'},
   {'symptom': 'Shine ignores your zones', 'cause': 'A saved Spec Sculpt keeps its own spec', 'fix': 'Clear the imported spec map in Settings.'}],
  'protips': ['A zone is a set of pixels plus a look. If it claims no pixels, no finish can show.'],
 },
 'support.render_slow_or_fails': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Cannot start: the checks in order',
    'body': 'A render is already running; the button says OPEN PAINT FIRST or LOADING PAINT; the engine is offline (wait 10 seconds); Source Paint needs a full path; the User ID is empty or not 4 to 7 digits; no zone has both a colour and a finish. The message names the first one that fails.'},
   {'heading': 'Starts but fails or crawls',
    'body': 'Too many zones with their own painted area (about 16 is the limit), a very slow stacked finish, a file held by another program (permission error, copy verification failed), or the 5-minute timeout. Terminate only stops Shokker waiting; the engine finishes and still copies the files.'},
   {'heading': 'How to confirm',
    'body': 'A good render ends with the green Saved bar. Press Show my files and check that the files are new.'}],
  'examples': [
   {'title': 'Too many zones', 'goal': 'Make a slow design render',
    'settings': {'Count': 'Zones with a region, layer or part', 'Fix': 'Merge zones that share a look; hide a zone with its eye icon to find the slow finish'},
    'result': 'Fewer painted areas and a faster render.'},
   {'title': 'File held by another program', 'goal': 'Clear a copy failure',
    'settings': {'Close': 'iRacing paint preview, 3D Car Viewer and any image viewer with the TGA open', 'Then': 'RENDER again'},
    'result': 'The copy succeeds.'}],
  'faq': [
   {'q': 'Should I press RENDER repeatedly?', 'a': 'No. A second render during a running one says render_busy.'},
   {'q': 'How long until it gives up?', 'a': '5 minutes.'},
   {'q': 'What if the engine stays down?', 'a': 'Close Shokker fully and open it again. Antivirus can block the engine.'}],
  'mistakes': [
   {'symptom': 'Render stuck and you press Terminate', 'cause': 'Terminate only stops waiting', 'fix': 'Wait about a minute, then render again.'},
   {'symptom': 'Many tiny zones are slow', 'cause': 'Each painted area costs memory', 'fix': 'Use fewer zones with a good tolerance.'}],
  'protips': ['If a render started failing right after a design change, Undo that change first.'],
 },
 'support.lost_files': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The four places',
    'body': 'The iRacing car folder (finished paint and spec copied by RENDER); Shokker\'s own render folder (only the two newest renders); the keep folder (copies you made with Save to keep); and your saved projects. A file you cannot find is in one of those or was never written.'},
   {'heading': 'Every cause',
    'body': 'No car folder was set, so the render stayed in Shokker\'s own folder. A newer render replaced the older one. The folder you picked is not the one iRacing uses (OneDrive can show a second, empty Documents folder). A typed folder that does not exist may have saved into its parent. The file is the backup type (spec_..., paint_base, ORIGINAL_) you took for junk.'},
   {'heading': 'How to confirm',
    'body': 'Press Show my files on the Saved bar. File Explorer opens on the folder with your paint highlighted; look for car_num_<ID>.tga or car_<ID>.tga and car_spec_<ID>.tga.'}],
  'examples': [
   {'title': 'No car folder was set', 'goal': 'Get the last render into iRacing',
    'settings': {'Set': 'iRacing Car Folder from the car menu', 'Then': 'Deploy Now under the render, or RENDER again'},
    'result': 'The files land in the car folder.'},
   {'title': 'An older look is gone', 'goal': 'Recover it',
    'settings': {'Press': 'RENDER HISTORY on the top row, click the thumbnail'},
    'result': 'The whole recipe is rebuilt; render to write the files again.'}],
  'faq': [
   {'q': 'Does the preview write to iRacing?', 'a': 'No. Only RENDER does.'},
   {'q': 'How many renders does Shokker keep?', 'a': 'The two newest as files. Older ones come back by rebuilding from History.'},
   {'q': 'Is a saved project an iRacing file?', 'a': 'No. A project (.spb) is for Shokker only.'}],
  'mistakes': [
   {'symptom': 'Deploy Now says Job not found', 'cause': 'Only the two newest renders can be deployed', 'fix': 'Render again, then Deploy Now.'},
   {'symptom': 'You delete backup-looking files', 'cause': 'They are backups of files Shokker replaced', 'fix': 'They are harmless; keep them unless space matters.'}],
  'protips': ['Save a project at the end of each session and use Save to keep on any render you love.'],
 },
 'support.numbers_vanished': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Every cause',
    'body': 'A zone set to Everything, Remaining or a loose colour match claimed the number or sponsor pixels. A colour match caught the logo colour. A whole-car finish with its own colour painted over everything. On the sim side, iRacing stamps its own number and sponsors, causing doubles. A metal spec under stamped items makes them sparkle.'},
   {'heading': 'Find the culprit',
    'body': 'Press Undo (Ctrl+Z) once, or step back in Undo History, until the numbers return. The last undone step is the cause. Open that zone to fix it.'},
   {'heading': 'How to confirm',
    'body': 'Re-apply the change with Restrict to layer set to the body layer only, check the CAR view, then render. The numbers should be exactly as before.'}],
  'examples': [
   {'title': 'Whole-car candy covered the number', 'goal': 'Keep the number',
    'settings': {'Zone': 'Restrict to layer: Car Paint only', 'Or': 'A Foundation finish with Source colours'},
    'result': 'The body changes, the number stays pixel-identical.'},
   {'title': 'Make the numbers gold on purpose', 'goal': 'Different finish for decals',
    'settings': {'Zone': 'Select the Numbers layer by name', 'Order': 'Above the body zone (lower number wins)'},
    'result': 'Only the numbers change.'}],
  'faq': [
   {'q': 'Is there a field for my car number?', 'a': 'No. The number switches only choose the file name.'},
   {'q': 'Will the AI helper touch numbers?', 'a': 'Not unless you name them, and every step has Undo.'},
   {'q': 'What about doubled numbers in the sim?', 'a': 'Switch off the number or sponsor layer of the template and keep Sim-Stamped Number as the file mode.'}],
  'mistakes': [
   {'symptom': 'Colour pick also hit the logo', 'cause': 'Tolerance too high', 'fix': 'Keep tolerance low and restrict to a layer.'},
   {'symptom': 'Numbers sparkle in the sim', 'cause': 'Metal spec under stamped items', 'fix': 'Decal Rescue Kit.'}],
  'protips': ['Select logos and numbers by layer name, not colour: exact edges, no bleed.'],
 },
 'support.smeared_blobby': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Every cause',
    'body': 'The pattern scale is too big for a whole car. The Base Scale of the finish texture is too big. The finish itself is made of large soft shapes. The source file is already soft (a JPEG or resized picture). Soft colour edges from a selection feather or high tolerance. Judging in the fit-to-window preview, which hides fine detail.'},
   {'heading': 'The numbers',
    'body': 'On a 2048 canvas, features of 4 to 8 pixels read as fine texture, 1 to 2 pixels as sparkle, and 16 to 64 pixels as macro that reads big on the car. Pattern Scale runs 0.10x to 4.0x and Base Scale 0.05x to 5.0x; 0.5 is twice as fine.'},
   {'heading': 'How to confirm',
    'body': 'Render and zoom to 100 percent. Fine features should now be crisp. If they are not, the source or the finish is the cause, not the scale.'}],
  'examples': [
   {'title': 'Carbon looks like a net', 'goal': 'Make a fine weave',
    'settings': {'Scale (pattern)': '0.5', 'Base Scale': 'Lower for a finer base texture'},
    'result': 'Twice as fine.'},
   {'title': 'Soft source paint', 'goal': 'Get a crisp start',
    'settings': {'Open': 'The car template as PSD/XCF/ORA or a clean TGA/PNG at 2048'},
    'result': 'No compression blur in the base.'}],
  'faq': [
   {'q': 'What does crushed to 50 percent mean?', 'a': 'Scale 0.5.'},
   {'q': 'Which slider do I change first?', 'a': 'Lower scale first; it is the cheapest fix.'},
   {'q': 'Do plain finishes have a scale?', 'a': 'Solid-colour finishes have no texture to scale.'}],
  'mistakes': [
   {'symptom': 'Judging at fit-to-window', 'cause': 'It hides fine detail and blur alike', 'fix': 'Zoom to 100 percent.'},
   {'symptom': 'Changing Base Scale for a pattern problem', 'cause': 'They are separate sliders', 'fix': 'Use Scale (pattern) for patterns.'}],
  'protips': ['Pick finishes whose catalogue card shows a small feature size. Large soft shapes always read as smeared.'],
 },
 'support.preview_render_mismatch': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Three pictures',
    'body': 'The preview is quick and approximate. The render is the full build written to disk. The sim adds light, shadow, materials and stamped numbers. A mismatch between the first two is a setting; a mismatch with the third is lighting.'},
   {'heading': 'Every cause between preview and render',
    'body': 'A stale preview (press F5 or click the red Preview failed bar). A different PSD whose old picture is still shown. Template guide layers on when you rendered. A saved Spec Sculpt or imported spec map that overrides zone shine. More than about 16 painted-area zones or an offline engine, so the preview fails and shows the last good one.'},
   {'heading': 'How to confirm',
    'body': 'After F5, the preview rebuilds from current settings. Compare the channel views COMBINED, R METAL, G ROUGH and B COAT, not the colour view. Then render and press Ctrl+R in iRacing.'}],
  'examples': [
   {'title': 'Stale preview after opening a new PSD', 'goal': 'Refresh',
    'settings': {'Press': 'F5 over the preview'}, 'result': 'The preview rebuilds from the new file.'},
   {'title': 'Shine ignores zones after Spec Sculpt', 'goal': 'Go back to zone shine',
    'settings': {'Where': 'Settings, clear the imported spec map'}, 'result': 'RENDER uses your zones again.'}],
  'faq': [
   {'q': 'Does the preview write files?', 'a': 'No, only RENDER does.'},
   {'q': 'What does Server busy - retrying mean?', 'a': 'The preview retries itself and times out after 18 seconds, then tries a faster one.'},
   {'q': 'Can I compare before and after?', 'a': 'Yes, with Before After.'}],
  'mistakes': [
   {'symptom': 'You diagnose a failed change', 'cause': 'The preview was stale', 'fix': 'Refresh first, then diagnose.'},
   {'symptom': 'Guide lines in the render', 'cause': 'Wire, Mask or Car_Mandatory on', 'fix': 'Switch them off and render again.'}],
  'protips': ['Judge shine in the channel views. The colour view cannot show a mirror.'],
 },
 'support.wont_start_or_update': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Every cause',
    'body': 'Server Failed: antivirus blocking the paint engine, a missing Microsoft Visual C++ Redistributable, or another program (often a second copy of Shokker) using the engine port. After an update: the window and engine versions differ until you restart fully. A crash of the interface reloads the window.'},
   {'heading': 'Fix steps',
    'body': 'Read the box. Allow Shokker and its engine in your antivirus or Windows Security. Install the Visual C++ Redistributable. Close other copies in the tray and Task Manager. The box names the debug log; send it to support if it keeps failing. After any update close and reopen Shokker once.'},
   {'heading': 'How to confirm',
    'body': 'The main window opens, the engine status is ready and a render starts. A message that app and screen versions differ means a restart is still needed.'}],
  'examples': [
   {'title': 'Server Failed after install', 'goal': 'Start the engine',
    'settings': {'Check': 'Antivirus, Visual C++ Redistributable, second copy running', 'Then': 'Start Shokker again'},
    'result': 'The engine starts within about a minute.'},
   {'title': 'Updating safely', 'goal': 'Update without losing work',
    'settings': {'Do': 'Save a project, click Download Update, let the app restart when it asks'},
    'result': 'The new version runs; Remind Me Later hides the banner for now.'}],
  'faq': [
   {'q': 'Will an update lose my work?', 'a': 'It restarts the app and can lose unsaved work. Save a project first.'},
   {'q': 'What if the interface crashes?', 'a': 'Shokker shows a message and reloads; your project may be recoverable from autosave. Save once it is back.'},
   {'q': 'What happens if I close with unsaved changes?', 'a': 'Shokker asks whether to quit anyway. Choose Cancel and save.'}],
  'mistakes': [
   {'symptom': 'Engine port busy', 'cause': 'A second copy runs in the background', 'fix': 'Close it in the tray or Task Manager.'},
   {'symptom': 'Old screen after update', 'cause': 'Not fully restarted', 'fix': 'Close Shokker fully and open it once.'}],
  'protips': ['Keep the Windows user name out of screenshots you send. The diagnostics report masks it; screenshots do not.'],
 },
 'support.error_messages': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'How the list is organised',
    'body': 'Messages come from four places: render start checks (paint, User ID, zones), the engine (offline, timed out, out of memory), the car folder (folder not found, copy failed) and the finishes (unknown or missing). Match your message to the group, then use the fix on its line in the steps and tips.'},
   {'heading': 'Warnings are not errors',
    'body': 'Yellow notes about PSD blend modes or layers are information. Messages that mention a port, a path or a log mean the app wrote more detail to its debug log.'},
   {'heading': 'How to confirm',
    'body': 'After the fix, render again. A cleared problem ends with the green Saved bar and no red text.'}],
  'examples': [
   {'title': 'Enter your iRacing User ID (4-7 digits)', 'goal': 'Fix a start refusal',
    'settings': {'Fix': 'Type your Customer ID (helmet icon > Profile in iRacing). It is not your car number.'}, 'result': 'RENDER starts.'},
   {'title': 'Failed to push / Copy verification failed', 'goal': 'Clear a held file',
    'settings': {'Fix': 'Close the iRacing paint preview or 3D Car Viewer and any image viewer, then render again'}, 'result': 'The copy completes.'},
   {'title': 'Unknown base / pattern id', 'goal': 'Replace a retired finish',
    'settings': {'Fix': 'Open that zone, pick another finish, render again'}, 'result': 'The zone renders.'}],
  'faq': [
   {'q': 'Can the helper read my error?', 'a': 'Yes. Paste the exact text into the Chat panel and it explains it.'},
   {'q': 'What if my message is not here?', 'a': 'Press Check my setup, then Settings gear > Report a Problem.'},
   {'q': 'What does cross_origin_forbidden mean?', 'a': 'You opened Shokker in a browser tab by hand. Use the Shokker Paint Booth window.'}],
  'mistakes': [
   {'symptom': 'Paraphrasing the message', 'cause': 'The helper matches the exact wording', 'fix': 'Copy the exact text or a screenshot.'},
   {'symptom': 'Retrying instantly on render_busy', 'cause': 'Only one render runs at a time', 'fix': 'Wait about a minute.'}],
  'protips': ['A paste of the exact message into Chat is faster than reading the list.'],
 },
 'support.reporting_problem': {
  'level': 'beginner',
  'deep': [
   {'heading': 'What the report holds',
    'body': 'Recent errors and warnings, a summary of your zones, your car folder and paint path, app and engine details and the end of the debug logs. It masks secrets and never includes your licence key or passwords. It leaves out your User ID and number mode.'},
   {'heading': 'What to add yourself',
    'body': 'What you expected and what you saw in the sim (white car, paint-shop colours, old paint, black parts), your User ID and your number mode. One line is enough.'},
   {'heading': 'How to confirm',
    'body': 'A message says Diagnostics copied - paste it to Shokker support. If it could not copy, press Save .txt and send that file. You can read the text first; it is plain.'}],
  'examples': [
   {'title': 'A render problem', 'goal': 'Get fast help',
    'settings': {'Do': 'Press Check my setup, then Settings gear > Report a Problem, paste into your message', 'Add': 'White car in iRacing, User ID, Sim-Stamped Number'},
    'result': 'Support can answer without asking again.'},
   {'title': 'Copy blocked', 'goal': 'Send the report anyway',
    'settings': {'Press': 'Save .txt and send the file'}, 'result': 'The same report as a file.'}],
  'faq': [
   {'q': 'Does the report include my licence key?', 'a': 'No, secrets are masked.'},
   {'q': 'Where are licence questions?', 'a': 'The License section is also in the Settings gear. Rendering does not check the licence.'},
   {'q': 'Does it see what iRacing shows?', 'a': 'No. Describe it yourself.'}],
  'mistakes': [
   {'symptom': 'Support asks for your ID', 'cause': 'The report omits it', 'fix': 'Add your User ID and number mode.'},
   {'symptom': 'Report sent without checks', 'cause': 'Setup problems are common', 'fix': 'Press Check my setup first.'}],
  'protips': ['Say what you expected and what happened in one line; the report supplies the rest.'],
 },
 'support.trading_paints': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'What Shokker does and does not do',
    'body': 'Shokker writes files on your PC only. It does not upload. iRacing does not send textures between drivers; the Trading Paints service and its Downloader put your files in other drivers\' paint folders.'},
   {'heading': 'Number modes and the spec',
    'body': 'Sim-Stamped Number writes car_<ID>.tga, called a Sim-Stamped Number paint on Trading Paints. Custom Number writes car_num_<ID>.tga, a Custom Number paint that needs Trading Paints Pro. For the shine, Trading Paints shares the car_spec_<ID>.mip that iRacing builds, not the .tga.'},
   {'heading': 'Why your test paint changes',
    'body': 'With Update My Own Paints on, the Downloader may overwrite files in your folder. Whether it does is not documented, so treat it as likely. Close it or turn that option off while you test.'}],
  'examples': [
   {'title': 'Share a finished paint', 'goal': 'Let others see it',
    'settings': {'Render': 'Sim-Stamped Number (or Custom Number with Pro)', 'Run': 'The car once so iRacing builds the .mip', 'Upload': 'Paint and spec on the Trading Paints site or app, optional Copy TP Desc'},
    'result': 'Other drivers see your paint through Trading Paints.'},
   {'title': 'Test locally', 'goal': 'Stop the swap',
    'settings': {'Do': 'Close the Downloader or turn off Update My Own Paints'},
    'result': 'Your local files stay.'}],
  'faq': [
   {'q': 'Can Shokker upload for me?', 'a': 'No automatic upload exists.'},
   {'q': 'Can Trading Paints share the .tga spec?', 'a': 'No, only the compiled .mip. The .tga spec is for your own car.'},
   {'q': 'Why do others see a white car?', 'a': 'They do not have your files. Give the car a plain paint-shop colour scheme in iRacing too.'}],
  'mistakes': [
   {'symptom': 'Uploading the .tga spec', 'cause': 'Trading Paints reads the .mip', 'fix': 'Run the car so iRacing builds the .mip, upload that.'},
   {'symptom': 'Sync folder problems', 'cause': 'OneDrive syncing the paint folder', 'fix': 'Keep iRacing\'s paint folder out of sync folders.'}],
  'protips': ['When the spec is final you can delete the spec .tga so iRacing stops rebuilding it at every start.'],
 },
 'support.psd_wont_open': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Every cause',
    'body': 'The wrong button (a flat TGA, PNG or JPEG opens with the TGA/PNG/JPEG button, layered files with PSD/XCF/ORA). The file is not .psd, .xcf or .ora. A big PSD is still loading (up to a minute). Non-pixel layers (text, shapes, adjustments) cannot import. Some blend modes become Normal. The file is damaged. The canvas was resized.'},
   {'heading': 'Reading the result toast',
    'body': 'It says how many editable layers loaded (for example 12 of 12). A note about layers missing or opened from the source composite means the picture is right but some layers are not editable, and the names are listed. A failed import keeps your previous paint unchanged.'},
   {'heading': 'How to confirm',
    'body': 'The layers appear in the Layers panel with the expected count and the preview shows your template. A zone limited to a layer name only works if the file has it.'}],
  'examples': [
   {'title': 'Text layers skipped', 'goal': 'Make text editable',
    'settings': {'Photoshop': 'Right-click the layer > Rasterize, save again', 'Shokker': 'Re-open with PSD/XCF/ORA'},
    'result': 'The layer loads as pixels.'},
   {'title': 'GIMP or Krita template', 'goal': 'Open without Photoshop',
    'settings': {'GIMP': 'Use the .xcf directly, or Export As .ora or .psd', 'Krita': 'Save as .ora'},
    'result': 'Layers import.'}],
  'faq': [
   {'q': 'Why does a big PSD take so long?', 'a': 'It can take up to a minute; a Loading message shows at the bottom.'},
   {'q': 'Does a failed import break my paint?', 'a': 'No. The previous source stays unchanged.'},
   {'q': 'Can I resize the canvas first?', 'a': 'No. Open the car template at its normal 2048 size.'}],
  'mistakes': [
   {'symptom': 'Nothing in a zone after import', 'cause': 'It is limited to a layer name the file lacks', 'fix': 'Check the layer names.'},
   {'symptom': 'Looks slightly different', 'cause': 'Blend modes imported as Normal', 'fix': 'Set them to Normal in Photoshop and re-open.'}],
  'protips': ['Keep a copy of your original PSD before experimenting.'],
 },
 'support.tiny_or_huge': {
  'level': 'intermediate',
  'deep': [
   {'heading': 'Three separate scales',
    'body': 'Base Scale (0.05x to 5.0x) sets the finish texture, Scale (pattern) (0.10x to 4.0x) sets a pattern, and Color Scale (0.05x to 5x) with Color Rotation (0 to 355 degrees) sets gradient or special colour art. They do not affect each other. Spec Scale follows Base Scale unless Independent Spec is on.'},
   {'heading': 'Every cause',
    'body': 'Flake like boulders or a net-like weave: scale above 1.0 on a whole car. A camo too fine to read: scale below 0.5 with colours of similar value. A slider you moved on the wrong control. The editor zoom, which does not change scale.'},
   {'heading': 'How to confirm',
    'body': 'Render and judge on the car at 100 percent. The Base Scale slider is not linear: left half 0.05 to 1, right half 1 to 5, centre 1.00x.'}],
  'examples': [
   {'title': 'Carbon too coarse', 'goal': 'Make the weave finer',
    'settings': {'Scale (pattern)': '0.5', 'Base Scale': 'Lower if the finish has its own weave'}, 'result': 'A finer weave.'},
   {'title': 'Gradient too small', 'goal': 'Enlarge colour art',
    'settings': {'Color Scale': 'Above 1.0 for a custom gradient or borrowed special'}, 'result': 'Bigger colour art; the material texture is unchanged.'}],
  'faq': [
   {'q': 'Does Base Scale change colours?', 'a': 'No. It never changes colours or the car size.'},
   {'q': 'Why is my whole car small in the window?', 'a': 'That is editor zoom, not scale.'},
   {'q': 'What is a good starting point?', 'a': 'On a whole car, start at 0.5x.'}],
  'mistakes': [
   {'symptom': 'Scale slider does nothing', 'cause': 'A plain finish has no texture', 'fix': 'Pick a textured finish.'},
   {'symptom': 'Spec looks out of step with the texture', 'cause': 'Independent Spec is on', 'fix': 'Untick it so the spec follows Base Scale.'}],
  'protips': ['Change one scale at a time and render. Three scales at once make it impossible to see what helped.'],
 },
}
