# How do I ... in Shokker Paint Booth (AI knowledge card: step by step with the exact button names)

Each entry starts with a tag line: [id | mode | needs | ui ids]. "Pro" = the full shop. Button names are exactly what the screen shows. If a buyer is stuck, find the closest entry, give the numbered steps, and say which one they are probably on.

## How do I load my paint file (a flat TGA, PNG or JPEG)?
[hdi.load_flat | pro | needs: none | ui: paintFile, pro.header.tga_png_jpeg, pro.center.load_tga]
Also asked as: where do i load my paint; how to import tga; my paint wont load; how do i start
1. Top row, find SOURCE PAINT. Click the "TGA/PNG/JPEG" button beside it (or on the empty canvas click "Load TGA" / "Load Paint Image").
2. Pick your paint file in the window that opens, then confirm.
3. Wait for the paint to appear in the SOURCE picture in the middle; the LIVE PREVIEW fills in next.
4. You can also paste the full file path into the Source Paint box and press Enter.
A flat TGA has no layers. Dropping a picture onto the canvas also loads it as the whole paint, it does not add a logo.

## How do I load a layered PSD template (so I get layers)?
[hdi.load_psd | pro | needs: none | ui: pro.header.psd_xcf_ora, onboardingImportPsdBtn, pro.layers.open_layered]
Also asked as: how do i open a psd; where do i load my paint; my paint wont load; wheres my layres
1. Top row, SOURCE PAINT, click the "PSD/XCF/ORA" button (or "Import PSD" on the empty canvas, or the LAYERS tab > "Open Layered").
2. Choose your PSD (XCF and ORA also work) and confirm.
3. Wait while the layers load, then open the LAYERS tab on the right to see them.
4. Before rendering, switch the template layers (Mask, Wire, Car_Mandatory) OFF with their eye icons.

## How do I start from a blank canvas with no paint file?
[hdi.blank_canvas | pro | needs: none | ui: pro.center.blank_canvas]
1. On the empty centre canvas click "Blank Canvas".
2. You get a plain white canvas to build colours on with zones and finishes.
3. Set the iRacing customer ID and car folder at the top before you render.

## How do I switch between PRO, CHAT and EASY?
[hdi.switch_mode | any | needs: none | ui: spbModeProBtn, spbModeChatBtn, spbModeEasyBtn]
1. At the top find the pill with PRO, CHAT and EASY.
2. Click the one you want. Your paint and zones stay open.
3. In Easy, "PRO MODE ->" at the top right brings you back.
Pro = every control. Chat = type what you want. Easy = paint by numbers (tap a colour part, pick a finish).

## How do I make a zone?
[hdi.make_zone | pro | needs: paint | ui: pro.zones.add_zone, zone.section_color, zone.base_material]
Also asked as: how do i make a zone; what is a zone
1. In the left ZONES column click "+ Add Zone". The new zone goes to the top and opens in the ZONE POPOUT PANEL.
2. In COLOR choose which pixels it covers: "PICK COLOR FROM CAR" then click the car, or tick a layer under RESTRICT TO LAYERS.
3. In BASE click Base Material and choose a finish.
4. Watch the LIVE PREVIEW. A zone needs BOTH an area (colour, layer or box) and a finish.

## How do I put a finish on just one part of the car (the hood, the roof, one side)?
[hdi.finish_one_part | pro | needs: paint, zone | ui: pro.zones.add_zone, zone.draw_box, zone.base_material]
Also asked as: how do I make just the hood different; make the roof black
1. Click "+ Add Zone".
2. In the ZONE POPOUT PANEL find APPLY AREA and click "Draw box".
3. Drag a box on the paint around that panel (the sheet is flat: hood, roof and sides are separate rectangles).
4. Under BASE click Base Material and pick the finish.
Faster: in Chat or the AI panel just say "make the hood chrome" if the car's parts are known. In Easy tap that colour part instead.

## How do I change only one colour of my livery (say all the red)?
[hdi.change_one_colour | pro | needs: paint | ui: zone.pick_color_from_car, zone.base_color_mode]
Also asked as: how do i do a two tone; how do i select just the red
1. Click "+ Add Zone".
2. In COLOR click "PICK COLOR FROM CAR", then click a red spot on the car. Raise the tolerance if red edges are left.
3. In BASE pick a finish.
4. To make it a different colour set the BASE COLOR dropdown to "Use solid color" and choose the colour.
Easy does the same: tap the red part in the rail on the right.

## How do I select a colour so a zone only affects that colour?
[hdi.select_by_colour | pro | needs: zone, paint | ui: zone.pick_color_from_car, zone.tolerance, vtModeEyedropper]
Also asked as: how do i select a color; how do i select just the red; the edges are left behind; it picked too much
1. Select the zone, open COLOR.
2. Click "PICK COLOR FROM CAR", then click the colour on the paint. A second click on another colour ADDS it.
3. Adjust the tolerance sliders until the edges are clean (about 30-50 is normal).
The "Remaining" button instead catches everything no higher zone claims.

## How do I sort or see my layers by colour?
[hdi.sort_layers_by_colour | pro | needs: psd | ui: layer.search, zone.pick_color_from_car, mode.easy]
Also asked as: can i sort by color
1. The LAYERS tab lists layers in the PSD's own order; there is no sort-by-colour. Use the "filter..." box at the top of the list to find a layer by name.
2. To work BY COLOUR instead: in Pro make a zone and use "PICK COLOR FROM CAR".

## How do I find one layer in a long PSD?
[hdi.find_layer | pro | needs: psd | ui: layer.search, rpTabLayers]
Also asked as: how do i find a layer; i have too many layers
1. Open the LAYERS tab.
2. Type part of the name in the "filter..." box (top right of the list); Escape clears it.
3. Alt+click an eye icon to see only that layer.

## How do I put a finish on the numbers?
[hdi.finish_numbers | pro | needs: paint | ui: zone.restrict_layers, layer.make_zone, mode.easy]
Also asked as: how do i do the numbers; make the numbers gold chrome; how do i make a finish only on the numbers layer; i cant find the numbers
1. With a PSD: open the LAYERS tab and click the zone icon on the Numbers layer (it makes a zone limited to that layer). Then in BASE pick the finish.
2. Or make a zone and tick "Numbers" under RESTRICT TO LAYERS.
3. With a flat TGA: if the numbers are one clear colour, "+ Add Zone" > "PICK COLOR FROM CAR" and click a number.
4. Easy: type "numbers gold chrome" in the Tell bar, or tap the Numbers layer in the LAYERS list.
If the colour is also used elsewhere add a box with APPLY AREA > "Draw box". Not every paint has numbers drawn (iRacing can stamp them).

## How do I recolour the numbers?
[hdi.recolour_numbers | pro | needs: paint | ui: zone.base_color_mode, zone.solid_color, pro.toolbar.color_replace, easy.tell_input]
Also asked as: make the numbers purple; how do i colour the numbres; how do i do the numbers
1. Quickest: in the AI panel type "numbers purple metallic".
2. In Pro make a zone for the numbers (see "put a finish on the numbers"), then in BASE set BASE COLOR to "Use solid color" and pick the colour.
3. To change the actual pixels instead use ADJUST > "Color Replace" on the Numbers layer.
Solid colour flattens finishes that bring their own colours; use Hue Shift for those.

## How do I teach the app where the numbers are?
[hdi.teach_numbers | chat | needs: paint | ui: ai.panel, ai.input]
Also asked as: i cant find the numbers; the app doesnt know where my numbers are; there are no numbers on my paint
1. Open the AI panel (the AI button bottom right) and ask for something on the numbers, e.g. "make the numbers gold".
2. It shows the car and asks. If its guess is right press "Yes, that is right".
3. If not press "No, I will show you", then draw a box around ONE number (a single one, not the whole panel). It finds the rest.
4. If the paint has none press "There are none on this paint".
It remembers places for this car. Never draw around a big area.

## How do I tell Shokker where the car's parts are (hood, roof, sides)?
[hdi.teach_parts | chat | needs: paint | ui: ai.panel]
Also asked as: how do i tell it where the hood is; it doesnt know my car; make the roof black
1. Ask the AI panel for a part change ("make the roof black"). If it does not know the car it shows the sheet and asks.
2. Draw a box around the part when asked (one part at a time) and say which part it is.
3. It remembers the car's parts from then on. The gear drawer can save or load a car map.

## How do I make a colour or finish "pop" on the car?
[hdi.make_pop | pro | needs: zone | ui: zone.auto_pop, zone.spec_sliders, zone.spec_preset]
Also asked as: it looks flat how do i make it pop; how do i make the colors pop; make it shinier
1. Select the zone, open BASE > Spec Sliders.
2. Click "Auto-Pop" (it nudges the spec toward glossy and metallic). Click again for more.
3. Or choose a "Spec preset..." such as Track Flash or Wet Candy.
4. Neighbouring areas in complementary colours help a finish read from far away.

## How do I make the shine shinier without changing the colour (spec only)?
[hdi.spec_only_shine | pro | needs: zone | ui: zone.base_color_mode, zone.spec_sliders, zone.g_rough]
Also asked as: make it shinier; how do i keep my colors but change the shine; i want to change only the shine; how do i change just the spec; where is the shiny thing
1. Select the zone that covers the area (or make one).
2. In BASE choose a Foundation finish such as Chrome / Satin Chrome / Metallic / Pearl / Satin, and set the BASE COLOR dropdown to "Use source paint (spec only)".
3. Or keep your finish and open Spec Sliders: lower "G Rough" and raise "R Metal" for shinier, or click "Auto-Pop".
4. The colour preview may barely move; look at the spec channel views (R METAL, G ROUGH, B COAT) under the preview.

## How do I make something matte (flat, no shine)?
[hdi.make_matte | pro | needs: zone | ui: zone.base_material, zone.g_rough]
Also asked as: how do i make it matte
1. Select the zone, BASE > Base Material > Matte (or Flat Black for the deadest look).
2. Keep your colour: BASE COLOR "Use source paint (spec only)".
3. Or push "G Rough" up in Spec Sliders. Satin is the in-between.

## How do I make something chrome?
[hdi.make_chrome | pro | needs: zone | ui: zone.base_material, zone.base_color_mode]
Also asked as: how do i make it chrome; how do i mak it chrome; metalic look
1. Select the zone, BASE > Base Material > Chrome (mirror) or Satin Chrome (softer).
2. Chrome repaints the zone silver. To keep your colours and only get the shine, use a Foundation chrome with "Use source paint (spec only)".
3. In iRacing the paint under a metal part should be near white for chrome to read.

## How do I change a finish's colour?
[hdi.finish_colour | pro | needs: zone | ui: zone.base_color_mode, zone.solid_color, zone.hue_shift]
Also asked as: change the color of the finish; how do i recolor a carbon finish; i picked pink and the camo turned flat; ugh the colors are all wrong
1. In BASE look at the BASE COLOR dropdown.
2. Plain finishes (gloss, matte, satin, candy, pearl, metallic) take a colour: choose "Use solid color" and pick it.
3. Finishes that bring their own colours (carbon, camo, holographic, flames ...) keep their look: use "Hue Shift" (and Saturation / Brightness) instead.
Solid colour on a brings-its-own-colours finish flattens it to one colour.

## Why is the colour not applying to my finish?
[hdi.colour_not_applying | pro | needs: zone | ui: zone.base_color_mode, zone.lock_base_color, zone.hue_shift]
Also asked as: why is the color not changing; i picked a color and it didnt apply; color wont apply; i picked pink and the camo turned flat; the pattern covers my color; ugh the colors are all wrong
1. Check BASE COLOR. "Use finish's own color" ignores your colour; "Use source paint (spec only)" keeps the car's colour. Pick "Use solid color" to force one.
2. Some finishes bring their own palette (camo, carbon, holographic). A solid colour on those makes one flat colour and loses the pattern: use Hue Shift to recolour them.
3. A pattern in "Overlay" paint mode paints its own colours over yours: set Paint mode to "Blend" or use the pattern Hue slider.
4. If colours keep changing when you change finish, switch ON the Lock beside Base Color (or Color Lock in the picker).

## How do I make a gradient (fade) between two colours?
[hdi.gradient | pro | needs: zone | ui: zone.base_color_mode, zone.gradient]
Also asked as: how do i make a gradient; fade from red to black
1. Select the zone and in BASE set BASE COLOR to "Custom gradient".
2. Set 2 colour stops (more for a sunset) and the direction.
3. The fade runs across the flat sheet, so each side of the car may fade differently; use one zone per side to control it.

## How do I crush a pattern finer (smaller texture)?
[hdi.pattern_finer | pro | needs: zone | ui: zone.pattern_scale, zone.base_scale]
Also asked as: the pattern is too big; make the pattern smaller; how do i crush the pattern finer; the texture looks huge; what does scale do; carbon looks too big
1. Select the zone, open PATTERN.
2. Drag "Scale" to the left (below 1.00x). Smaller means more repeats.
3. For the base finish's own texture use "Base Scale" in BASE.
4. On a whole car even normal-size patterns look big; 0.3x to 0.6x is typical for fine detail.

## What does the Base Scale slider do?
[hdi.what_base_scale | pro | needs: zone | ui: zone.base_scale, zone.spec_scale]
Also asked as: what does the base scale slider do; what does scale do; carbon looks too big; the texture looks huge
1. It changes how big the finish's own texture (flake, weave, grain) is inside that zone, from 0.05x to 5.0x (1.00x is normal).
2. Smaller = finer and more repeats; bigger = zoomed in.
3. It does not change colours or resize the car. Spec Scale follows it until you tick Independent Spec.

## How do I add a pattern (carbon, flames, camo ...)?
[hdi.add_pattern | pro | needs: zone | ui: zone.section_pattern, zone.pattern, zone.pattern_paint_mode]
Also asked as: how do i add a pattern; the pattern covers my color; how do i add flake
1. Select the zone, open PATTERN.
2. Click the pattern name box (shows "None") and choose a pattern.
3. Set "Paint mode": "Overlay" = the pattern's own colours cover the paint; "Blend" = it keeps your colour.
4. Use Opacity, Scale and Rotate to taste.

## How do I remove a pattern?
[hdi.remove_pattern | pro | needs: zone | ui: zone.pattern]
Also asked as: how do i remove the pattern
1. Select the zone, open PATTERN.
2. Click the small x ("Remove this pattern") beside the pattern name.

## How do I rotate a pattern?
[hdi.rotate_pattern | pro | needs: zone | ui: zone.pattern_rotation]
Also asked as: how do i rotate the pattern
1. PATTERN > "Rotate" slider (0-359 degrees) or type the number in the box beside it.
2. For the base finish texture use "Base Rotation" in BASE.

## How do I move a pattern to a specific spot?
[hdi.move_pattern | pro | needs: zone | ui: zone.pattern_placement, zone.pattern_position]
Also asked as: move the pattern
1. In PATTERN find "Pattern placement" and click "Edit on Template" to drag it by hand, or "Fit to Zone".
2. For fine control open "Advanced Pattern Control Panel" and use Position X / Position Y, Flip H / Flip V.

## How do I add a shiny texture without changing the colour (spec overlay)?
[hdi.spec_overlay | pro | needs: zone | ui: zone.section_spec_overlays, zone.add_spec_overlay]
Also asked as: what is an overlay
1. Select the zone, open BASE > SPEC OVERLAYS.
2. Click "+ ADD SPEC OVERLAY" and choose a texture (brushed, hammered, scratched ...).
3. It changes shine and metal only. Check the R METAL / G ROUGH / B COAT views to see it.

## How do I stack two finishes (second base)?
[hdi.second_base | pro | needs: zone | ui: zone.section_overlays, zone.second_base]
Also asked as: how do i layer two finishes; what is an overlay
1. Select the zone, open OVERLAYS.
2. Click the "2nd Base" box and pick a finish; use "+ Add 3rd overlay" for more (up to five layers).
3. Each overlay has its own blend controls.

## How do I make a finish less strong (blend it with my paint)?
[hdi.finish_less_strong | pro | needs: zone | ui: zone.base_strength, zone.spec_strength]
1. BASE > "Base Strength": lower it. 0% = your original paint, 100% = full finish.
2. "Spec Strength" does the same for the shine only.
In Easy use ADJUST > BLEND.

## How do I change the order or priority of zones?
[hdi.zone_order | pro | needs: zone | ui: zone.order, pro.zones]
1. In the left ZONES column drag a zone card by its handle (the three-line icon).
2. Top = highest priority; where two zones select the same pixels the higher one wins.
3. A catch-all "Remaining" zone belongs at the bottom.

## Why is my zone not showing / doing anything?
[hdi.zone_not_showing | pro | needs: zone | ui: zone.order, zone.section_color, zone.base_material]
Also asked as: i made a zone and nothing happens; zone not working; my zone does nothing; why is my zone not showing; why wont it change
1. Does it have an area (colour, layer, or box) AND a finish? The panel warns "No color or region set yet".
2. Is a zone ABOVE it claiming the same pixels? Drag it higher.
3. Is the colour tolerance too tight? Raise it.
4. Is the zone muted (eye icon off) or limited to a hidden layer?
5. Is the preview stale? Press the Refresh button or F5.

## Why is my preview not changing?
[hdi.preview_not_changing | pro | needs: paint | ui: btnPreviewRefresh, zone.order, zone.section_color]
Also asked as: why wont it change; why cant i see my changes; preview wont update; preveiw wont chnage; nothing works
1. Press F5 (or the "Refresh" button beside the preview) to force it.
2. Make sure the zone has an area and a finish, and nothing above it claims the same pixels.
3. Spec-only changes (shine, metal, coat) hardly change the colour preview: look at R METAL / G ROUGH / B COAT.
4. Make sure the view is not on SOURCE only: use SPLIT or CAR (buttons next to the zoom).
5. If it says "Preview failed - showing the LAST GOOD render", click that bar; reopen the app if it persists.

## I loaded my paint and nothing happened. What now?
[hdi.loaded_nothing | pro | needs: paint | ui: paintFile, pro.zones.add_zone, btnRender]
Also asked as: i loaded my paint and nothing happened
1. Loading only shows your paint. Nothing changes until you give a zone a finish.
2. Click "+ Add Zone", pick a colour with "PICK COLOR FROM CAR", then choose a finish in BASE.
3. Or switch to CHAT and just say what you want.
4. Press RENDER at the end to write the files.

## What do I do first? (a complete beginner)
[hdi.what_now | any | needs: none | ui: spbGuideToggle, mode.easy, mode.chat]
Also asked as: this is confusing; what now; help; i dont get it; how do i start; i hate this i cant figure it out
1. Load your paint: top row, SOURCE PAINT, "TGA/PNG/JPEG" (flat) or "PSD/XCF/ORA" (layers).
2. Make zones in PRO, or switch to CHAT to type what you want.
3. Pick looks, check the LIVE PREVIEW.
4. Set your iRacing customer ID and car folder at the top, then press RENDER.
Press "Tutorial" in the top bar for Training Wheels: quests that teach the app step by step.

## How do I turn on the step-by-step tutorial (Training Wheels)?
[hdi.tutorial | pro | needs: none | ui: spbGuideToggle, trainingWheelsCheckbox]
Also asked as: how do i get a tutorial; this is confusing; i hate this i cant figure it out
1. Click "Tutorial" in the top bar, or tick Training Wheels in Settings (the gear).
2. Follow the quests: load, zone, finish, render, then patterns, spec, overlays.
3. Click it again to turn it off.

## What are layers?
[hdi.what_are_layers | pro | needs: none | ui: rpTabLayers, pro.layers]
Also asked as: what are layers; wheres my layres
1. A layered PSD keeps parts of the livery on separate sheets: Car Paint (body colours), Numbers, Sponsors, Tape, Decals.
2. Layers let you change one thing (just the numbers) without touching the rest.
3. Template layers (Mask, Wire, Car_Mandatory) only show the car outlines and must be OFF when you render.
4. A flat TGA has no layers. Load a PSD ("PSD/XCF/ORA") to get them; see the LAYERS tab on the right.

## How do I turn a layer on or off?
[hdi.layer_visibility | pro | needs: psd | ui: layer.eye]
Also asked as: how do i hide a layer
1. Open the LAYERS tab.
2. Click the eye icon on the layer. Alt+click shows only that layer.

## How do I switch off the template lines (Mask, Wire, Car_Mandatory) before exporting?
[hdi.template_layers_off | pro | needs: psd | ui: layer.eye, easy.template_guides]
Also asked as: there are lines all over my car; i see the wireframe on my paint; how do i turn off mask and wire
1. LAYERS tab: click the eye on Car_Mandatory, Mask and Wire (the group "Turn Off Before Exporting TGA").
2. In Easy click "Turn off" on the "Template guides are on" warning.
3. Then render. If lines still show on the car, one of them was left on.

## How do I add a logo or sponsor picture?
[hdi.add_logo | pro | needs: paint | ui: pro.layers.layer, layer.rename]
Also asked as: i dropped a picture on the canvas and it replaced everything; how do i add a logo; how do i add my sponsor
1. Open the LAYERS tab and click "+ Layer".
2. Choose a PNG / JPG / WebP / GIF (transparent PNG is best).
3. Drag it with Move (V) in LAYER mode, or use Transform (Ctrl+T) to size it.
Do not drop it onto the canvas: that REPLACES the whole paint.

## How do I move or resize a number or logo?
[hdi.move_logo | pro | needs: psd | ui: btnToolbarModeLayer, vtModeLayerMove, vtModeLayerTransform]
Also asked as: how do i move a layer; how do i move the numbers; how do i resize a logo
1. Click LAYER in the ZONE | LAYER switch (top toolbar).
2. Pick Move (V), click the number / logo (it isolates it), drag.
3. Use Transform (Ctrl+T) for size and rotation; "Apply" confirms.

## How do I change a layer's opacity or blend mode?
[hdi.layer_opacity | pro | needs: psd | ui: layer.opacity, layer.blend]
Also asked as: how do i change layer opacity
1. LAYERS tab, find the layer row.
2. Drag its opacity slider (or type a value), and use the blend dropdown (Normal, Multiply, Screen, Overlay ...).

## How do I delete or duplicate a layer?
[hdi.layer_delete | pro | needs: psd | ui: layer.rename]
Also asked as: how do i delete a layer
1. LAYERS tab, use the layer's duplicate (Shift = offset copy) or delete icon.
2. Deleting removes the art; use the eye icon if you only want it hidden. Ctrl+Z undoes.

## How do I merge or flatten layers?
[hdi.merge_flatten | pro | needs: psd | ui: layerActionsMenuBtn]
Also asked as: how do i merge layers
1. LAYERS tab > "Actions".
2. "Merge visible" combines the visible layers (hidden ones survive); "Flatten document" makes one layer and loses separation.

## How do I paint on a layer by hand?
[hdi.paint_on_layer | pro | needs: psd | ui: btnToolbarModeLayer, vtModeBrush, vtModeColorBrush]
Also asked as: how do i paint on a layer
1. Click LAYER in the ZONE | LAYER switch.
2. Pick Brush (B) and set size / opacity in the options bar (or open RETOUCH for Color Brush, Recolor, Smudge).
3. For a fresh blank layer: LAYERS tab > Actions > "+ Blank layer".

## How do I make a zone follow one layer (restrict to a layer)?
[hdi.restrict_to_layer | pro | needs: psd, zone | ui: zone.restrict_layers, layer.make_zone, layer.lock_zone]
Also asked as: how do i make a finish only on the numbers layer
1. Select the zone, COLOR section > RESTRICT TO LAYERS, tick the layer(s).
2. Or press the zone icon on a layer row to make a new zone limited to it, or Ctrl+L to lock the active zone to the selected layer.
Choose only paintable layers (Car Paint, Sponsors, Numbers ...), not Mask or Wire.

## How do I keep sponsors and numbers untouched when I change the body?
[hdi.protect_sponsors | pro | needs: psd | ui: zone.restrict_layers]
Also asked as: only change the body not the sponsors; how do i leave the numbers alone
1. Make a zone for the body and tick only "Car Paint" under RESTRICT TO LAYERS.
2. Or in Chat say "change the body but leave the numbers alone".

## How do I undo?
[hdi.undo | pro | needs: paint | ui: pro.toolbar.undo_ctrl_z, pro.toolbar.undo_history, ai.undo, easy.undo]
Also asked as: undo; how do i undo; i messed up; put it back; how do i go back several steps; i dropped a picture on the canvas and it replaced everything
1. Press Ctrl+Z, or the Undo button in the top toolbar (HISTORY menu).
2. To go back several steps open "Undo History...".
3. Under an AI panel answer press Undo to take back that whole answer. In Easy use UNDO at the top.
Ctrl+Y or Ctrl+Shift+Z redoes.

## How do I start over completely?
[hdi.start_over | pro | needs: paint | ui: pro.zones.reset_all_zones, easy.start_over]
Also asked as: i want to start over; i messed up
1. Pro: left ZONES column > "Reset All Zones" (undoable, resets to the default zones).
2. Easy: "START OVER" at the top right.
3. One zone only: "Reset Zone" at the top of its panel.

## How do I export my paint to iRacing?
[hdi.export_iracing | pro | needs: paint, car_folder | ui: iracingId, outputDir, btnRender]
Also asked as: how do i export; how do i get it into iracing; where does the file go; where is the render button; how doo i exprot; how do i save
1. Top row: enter your iRacing customer number (IRACING USER ID) and set IRACING CAR FOLDER (use the car list button or browse).
2. Turn the template layers (Mask, Wire, Car_Mandatory) OFF.
3. Click RENDER (Ctrl+R). The paint and spec files are written to the car folder.
4. In iRacing press Alt+Tab, then Ctrl+R to reload paints.
Easy: SAVE TO iRACING does the same.

## How do I get Shokker to write straight into my iRacing folder every time?
[hdi.live_link | pro | needs: car_folder | ui: outputDir, liveLinkCheckbox]
1. Set IRACING CAR FOLDER at the top: that alone copies every render there.
2. Settings (gear) > "Auto-deploy" only matters when the car folder is empty.

## How do I choose my iRacing car?
[hdi.pick_car | pro | needs: none | ui: carPickBtn, outputDir]
Also asked as: which car folder do i pick; how do i pick my car; where does the file go
1. Top row, click the car-list button beside IRACING CAR FOLDER ("Pick detected iRacing car").
2. Choose your car (most recently painted first), or use the browse button.
3. In Easy: WHERE IT GOES > search / choose your car.

## What is my iRacing customer ID and where do I put it?
[hdi.customer_id | pro | needs: none | ui: iracingId]
Also asked as: what is my customer id; what do i put in the iracing user id box
1. It is your iRacing member number (4-7 digits), shown in your iRacing account.
2. Type it in IRACING USER ID at the top. It is part of the saved file names; a wrong one means iRacing shows nothing.

## What is the difference between Custom Number and Sim-Stamped Number?
[hdi.number_type | pro | needs: none | ui: useCustomNumberCheckbox, useSimStampedCheckbox]
Also asked as: what is custom number vs sim stamped
1. Custom Number: the number is part of your paint (files car_num_ID.tga); iRacing adds none. Needs Hide Car Numbers ON in iRacing.
2. Sim-Stamped Number: iRacing stamps the number in the series font (files car_ID.tga). Do not also paint a number.
3. Switch at the top (CUSTOM NUMBER / SIM-STAMPED NUMBER).

## Why doesn't my paint show in iRacing?
[hdi.not_in_iracing | pro | needs: render, car_folder | ui: iracingId, outputDir, useCustomNumberCheckbox]
Also asked as: my paint doesnt show in iracing; i rendered but its not in the sim; iracing shows the old paint
1. Check the customer ID is right.
2. Check CUSTOM / SIM-STAMPED matches iRacing's Hide Car Numbers setting.
3. Check IRACING CAR FOLDER is the exact car folder.
4. Render again, then Alt+Tab and press Ctrl+R in iRacing.
5. Make sure the template layers were off and the file is a 2048 TGA.

## How do I get my paint to look the same in iRacing as in Shokker?
[hdi.look_differs | pro | needs: render | ui: btnRender]
Also asked as: the chrome looks dark in iracing; looks different in iracing; iracing shows the old paint
1. Remember the preview is a quick flat view; iRacing adds sun, shadow and its own stamps.
2. Chrome needs light paint under it and strong metal in the spec map.
3. Reload with Ctrl+R in iRacing; if the shine looks old move the old car_spec .mip file away.

## What is a spec map?
[hdi.what_is_spec | pro | needs: none | ui: pro.preview, btnSpecMapInspector]
Also asked as: what is a spec map; what does spec mean; what is R G B coat; spek map
1. It is a second picture iRacing reads to know how shiny each pixel is.
2. Red = metal (255 = metal), Green = roughness (0 = mirror, 255 = matte), Blue = clearcoat (16 = best gloss, 255 = dull).
3. You see it under the preview as COMBINED, R METAL, G ROUGH, B COAT. RENDER writes both the paint and the spec file.

## Where are the spec sliders?
[hdi.where_spec_sliders | pro | needs: zone | ui: zone.spec_sliders, zone.r_metal, zone.g_rough, zone.b_coat]
Also asked as: where is the shiny thing; where are the spec sliders; where is metal rough coat
1. Click a zone card in the left column to open the ZONE POPOUT PANEL.
2. Open the BASE section and scroll to "Spec Sliders": R Metal, G Rough, B Coat.
3. Strength of the whole spec is "Spec Strength" higher up in BASE.

## How do I see the spec map?
[hdi.see_spec | pro | needs: paint | ui: pro.preview.r_metal, btnSpecMapInspector, btnSpecMapInspectorSource]
Also asked as: how do i see the spec
1. Under the LIVE PREVIEW click COMBINED, R METAL, G ROUGH or B COAT.
2. Click one to open it larger, or use "Channels" for exact numbers.

## How do I read the exact metal / rough / coat of a spot?
[hdi.read_spec_value | pro | needs: render | ui: pro.toolbar.material_sampler]
Also asked as: how do i read the exact metal value
1. Top toolbar > SPEC TOOLS > "Material Sampler...".
2. Click a spot on the spec map: M / R / CC values appear; "Apply to Active Zone" copies them to the zone.

## How do I make numbers and sponsors read cleanly under chrome or candy?
[hdi.decal_rescue | pro | needs: paint | ui: pro.toolbar.decal_rescue_kit]
Also asked as: sponsors look weird under chrome; my numbers look sparkly
1. Top toolbar > SPEC TOOLS > "Decal Rescue Kit...".
2. Choose Flat Vinyl, Satin Decal or Gloss Decal. It puts a plain non-metal spec under stamped numbers and sponsors.

## How do I make fake grille holes or vents (lighting mask)?
[hdi.lighting_mask | pro | needs: paint | ui: pro.toolbar.lighting_mask]
Also asked as: how do i make a vent
1. Top toolbar > SPEC TOOLS > "Lighting Mask...".
2. Choose Use Source Alpha, Full Lighting, Reduced Lighting or Kill Lighting for the area.

## How do I pick or change a finish for a zone?
[hdi.pick_finish | pro | needs: zone | ui: zone.base_material, swatchSearchInput, swatchStageUseBtn]
Also asked as: how do i add flake; how do i pick a finish; where are the finishes; metalic look; how do i search for a finish; i dont know what finish to use
1. Select the zone, BASE > click the Base Material box.
2. Search by name or idea (try "gold chrome" or #carbon), or tap a #tag chip.
3. Preview on the On-Car Stage, then press "USE IT". "Surprise me" rolls a random good one.

## How do I search the whole finish library?
[hdi.search_finishes | pro | needs: none | ui: rpTabFinishes, finishSearch, fbSearch]
Also asked as: how do i search for a finish; where are the finishes
1. Click the FINISHES tab on the right (full-screen library).
2. Type in the search box: names, ideas ("icy blue"), or #tags; use the filters and the star for favourites.

## How do I get ideas for a finish I can't name?
[hdi.finish_ideas | chat | needs: paint | ui: swatchDiceBtn, ai.panel]
Also asked as: i dont know what finish to use; give me ideas
1. In the AI panel describe the feel ("like a rainy city night, but glossier") and it offers several real finishes with previews.
2. Or open the Base Material picker and press "Surprise me".

## How do I apply a ready-made look (preset)?
[hdi.presets | pro | needs: paint | ui: pro.zones.more, pro.zones_more.presets_gallery]
Also asked as: are there presets
1. Left column > "More" (three dots) > "Presets Gallery".
2. Click a preset to apply it.
Easy has "TRY A LOOK" (Show car, Subtle OEM, Candy shop, Matte & chrome).

## How do I give every zone the same finish?
[hdi.same_finish_all | pro | needs: zone | ui: pro.zones_more.apply_finish_to_all]
Also asked as: same finish on everything
1. Pick the finish on one zone.
2. Left column > More > "Apply Finish to All".

## How do I duplicate a zone?
[hdi.duplicate_zone | pro | needs: zone | ui: zone.mute]
Also asked as: how do i copy a zone
1. On the zone card in the left column click the copy icon.
2. Change the area or finish of the copy.

## How do I hide a zone for a moment?
[hdi.hide_zone | pro | needs: zone | ui: zone.mute]
Also asked as: how do i hide a zone
1. Click the eye icon on its card in the ZONES column. Click again to bring it back.

## How do I delete a zone?
[hdi.delete_zone | pro | needs: zone | ui: zone.mute]
Also asked as: how do i delete a zone
1. Click the x on the zone's card (Ctrl+Z undoes). The Chat copilot cannot delete zones.

## How do I draw the exact area a zone covers (a box or lasso)?
[hdi.draw_area | pro | needs: zone, paint | ui: zone.draw_box, zone.lasso, zone.clear_area]
Also asked as: how do i draw a box; how do i use lasso
1. In the zone's APPLY AREA click "Draw box" or "Lasso".
2. Drag on the paint. "Clear" removes it, "Activate" turns it back on.

## How do I use the magic wand or lasso to select an area?
[hdi.wand_select | pro | needs: paint | ui: vtModeWand, wandTolerance, useRegionBtn]
Also asked as: how do i use the magic wand; how do i use lasso
1. Pick Wand (W) in the top toolbar (or Lasso L / Rect O). Click or drag on the paint.
2. Shift adds, Alt subtracts; the Tolerance slider sets how similar colours must be.
3. Select a zone in the left column and press "Use Region" to give it that selection.

## How do I select a number or logo as a whole?
[hdi.grab_object | pro | needs: paint | ui: vtModeGrabObject, useRegionBtn]
Also asked as: how do i select a logo
1. Top toolbar > SELECT menu > "Grab Object" (G).
2. Click inside a solid part of the number; its outline is selected.
3. Use "Use Region" on the zone you want.

## How do I grow, shrink or soften a selection edge?
[hdi.mask_edges | pro | needs: zone | ui: pro.toolbar.grow_1_px, pro.toolbar.feather_2_px, pro.toolbar.smooth_edges]
Also asked as: how do i soften the edge
1. Top toolbar > MASK menu: "Grow 1 px / 2 px", "Shrink", "Fill Holes", "Feather 2 px", "Smooth Edges", "Invert Mask".
2. The same buttons sit in the bar under the canvas (Grow, Shrink, Feather, Smooth).

## How do I invert or copy a zone's area?
[hdi.mask_copy | pro | needs: zone | ui: pro.toolbar.invert_mask, pro.toolbar.copy_mask, pro.toolbar.mirror_mask]
1. Top toolbar > MASK: "Invert Mask" swaps selected / unselected, "Copy Mask" copies it to another zone, "Mirror Mask" flips it left-right.

## How do I remove one spot from a zone's colour match?
[hdi.exclude_region | pro | needs: zone | ui: vtModeSpatialExclude, vtModeSpatialInclude]
Also asked as: how do i exclude a spot
1. Top toolbar > MASK > "Exclude Region", then paint over the bits to leave out (red overlay).
2. "Include Region" paints bits to keep (green); "Erase Spatial" removes those strokes.

## How do I zoom and move around the canvas?
[hdi.zoom | pro | needs: paint | ui: pro.center.fit, pro.center.1_1]
Also asked as: how do i zoom
1. Buttons beside the canvas: zoom out, +, FIT (Ctrl+0), 1:1 (actual size).
2. Ctrl+plus / Ctrl+minus also zoom.

## How do I compare before and after?
[hdi.before_after | pro | needs: render | ui: btnBeforeAfter, btnCompare, btnSplitView]
Also asked as: how do i compare before and after
1. Click "B/A" (or press B) to flip between the last preview and now.
2. "Compare" gives a wipe slider; SPLIT shows source and preview side by side.

## How do I see the car preview bigger?
[hdi.preview_bigger | pro | needs: paint | ui: btnPreviewRefresh, btnSourceFocus, btnSplitView]
1. Click the preview picture to open it full size (PAINT / SPEC MAP).
2. Or use "Edit Big" to give the source canvas the whole window, or Easy's "BIGGER PICTURE".

## How do I save my project and come back later?
[hdi.save_project | pro | needs: paint | ui: spbProjectsButton, pro.zones_more.save_shokk]
Also asked as: how do i save; how do i save my project; how do i come back to this later
1. Click "Save / Open" in the top toolbar (SPB Projects). It saves the paint (PSD included), every zone and layer settings in one file.
2. To reopen, click "Save / Open" again and load it.
There is no File menu.

## How do I share my finish setup with someone?
[hdi.share_recipe | pro | needs: render | ui: pro.render.share_recipe, pro.render.copy_card]
Also asked as: how do i share my paint recipe
1. After RENDER the recipe card appears: "Copy Card" (paste into Discord), "Save Card PNG", "Share Recipe" (a .shokkerrecipe file) or "Copy TP Desc" (Trading Paints description).
2. Others load it with "Import Recipe" in the top toolbar.

## How do I load a recipe someone sent me?
[hdi.import_recipe | pro | needs: paint | ui: pro.toolbar.import_recipe]
Also asked as: how do i load a recipe
1. Top toolbar > "Import Recipe".
2. Choose the .shokkerrecipe file; its zones, colours and finishes are applied to your car.

## How do I save a zone layout as a template?
[hdi.save_template | pro | needs: zone | ui: pro.zones_more.save_as_template, templateSelect]
Also asked as: how do i save a template
1. Left column > More > "Save as Template", name it, Save.
2. Load it later from the "Load Template..." dropdown in the same menu.

## How do I go back to an earlier render?
[hdi.old_render | pro | needs: render | ui: pro.toolbar.render_history, pro.toolbar.recent, btnSaveToKeep]
Also asked as: go back to my old render
1. Top toolbar > RENDER HISTORY > "Recent" or "Gallery", click a thumbnail to restore it with its full recipe.
2. To keep one safe, press "Save to keep" on the recipe card.

## How do I save a zip of my paint files?
[hdi.zip_export | pro | needs: render | ui: exportZipCheckbox]
1. Settings (gear) > tick the ZIP option. Every render bundles the paint TGA, spec TGA and preview.

## How do I export the spec channels as pictures (for Photoshop)?
[hdi.export_png_channels | pro | needs: render | ui: pro.zones_more.png_channels_export]
1. Left column > More > "PNG Channels Export" (choose the export folder first).
2. Or LAYERS tab > Actions > "Photoshop round-trip" to export layers and bring a TGA back.

## How do I use the Chat mode / AI panel?
[hdi.use_chat | chat | needs: paint | ui: mode.chat, ai.panel, ai.input]
Also asked as: how do i use chat; how do i talk to the ai; what can the ai do; do i need an api key
1. Click CHAT in the pill (or the AI button bottom right).
2. Type what you want: "make the hood matte black", "retro red white and blue stripes", "numbers gold chrome". Enter sends.
3. Each answer has an Undo button; "Another take" tries a different idea.
It works with no key for common requests; a key makes it smarter.

## How do I use Easy mode (paint by numbers)?
[hdi.use_easy | easy | needs: paint | ui: mode.easy, easy.rail, easy.finish_picker, easy.save]
Also asked as: how do i use easy mode; what is easy mode; i dont get it; i hate this i cant figure it out
1. Load your paint, then click EASY in the pill.
2. Shokker finds the colours and gives each a finish. Tap any part of the car (or a row on the right) to change it.
3. Pick a finish card, keep your colour or take the finish's colour, adjust Blend / Size / Color.
4. Choose your car, check the READY TO RACE checklist, then SAVE TO iRACING.

## How do I change one colour part in Easy?
[hdi.easy_change_part | easy | needs: paint | ui: easy.rail, easy.color_reach, easy.finish_picker]
Also asked as: how do i change one color in easy
1. Tap the part (e.g. "Black - Gloss") in the rail, or tap that colour on the car.
2. Use COLOR REACH to catch more or fewer shades (the orange highlight shows what it catches).
3. In FINISH choose a card and decide COLOR (finish's own / keep yours / pick) and PUT IT ON (This part / Every color / Shine only - whole car).

## How do I tell Easy what I want in words?
[hdi.easy_tell | easy | needs: paint | ui: easy.tell_input, easy.tell_help]
Also asked as: how do i tell easy what i want
1. Type in "Tell Shokker what you want..." above the car, e.g. "make the brown carbon" or "everything matte black", press "Do it".
2. Press "?" for examples or the dice for a surprise.

## How do I style just one layer in Easy?
[hdi.easy_layer | easy | needs: psd | ui: easy.layers]
1. In the LAYERS list on the right tap a layer ("tap to style this layer") or its sparkle button to say what you want for it.
2. A flat TGA has no layers; load a PSD.

## Why won't SAVE TO iRACING work in Easy?
[hdi.easy_save_blocked | easy | needs: paint, car_folder | ui: easy.readiness, easy.save, easy.template_guides]
Also asked as: easy mode wont let me save
1. Read the READY TO RACE? checklist: paint, customer ID, your iRacing car, a finish picked.
2. Arrows show what is missing; choose the car under WHERE IT GOES.
3. If "Template guides are still on" appears click "Turn them off first".

## How do I add a colour part Easy missed?
[hdi.easy_missed_colour | easy | needs: paint | ui: easy.pick_color, easy.rebuild]
Also asked as: it missed a color in easy
1. In the rail click "Pick a color off the car" and click the colour on the car.
2. "Find the parts again" re-reads the paint; your earlier finish choices are kept.

## How do I merge two colour parts in Easy?
[hdi.easy_merge | easy | needs: paint | ui: easy.merge_with]
1. Tap one part, use "Merge with" and choose the other.

## How do I talk to Claude about my paint through MCP?
[hdi.use_claude_mcp | pro | needs: paint | ui: mcp.claude, ai.gear]
Also asked as: how do i use claude with this; how do i use mcp
1. Open the AI panel, press the gear, switch ON "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth".
2. Press "Install in Claude Desktop" and restart Claude Desktop.
3. With Shokker open, ask Claude: "Using Shokker Paint Booth, give me a Gulf-style livery".
4. Every change shows in the AI panel with an Undo button. No API key needed; your Claude plan is used.

## How do I use ChatGPT / Codex with Shokker?
[hdi.use_chatgpt | pro | needs: paint | ui: mcp.chatgpt, ai.gear]
Also asked as: how do i connect chatgpt; how do i use mcp
1. AI panel > gear > bridge settings > "Connect ChatGPT / Codex", review, then "Add SPB to Codex settings".
2. Restart Codex, sign in with ChatGPT, choose a model, chat with Shokker open.
3. Use "Take over in SPB" before asking the in-app copilot while an outside assistant has control.

## How do I give the in-app copilot an AI key (and which model)?
[hdi.ai_key | chat | needs: none | ui: ai.gear]
Also asked as: do i need an api key
1. AI panel > gear.
2. Paste your OpenRouter key and pick the one model offered (DeepSeek v4.1 Flash is recommended). A daily cap protects your spend.
3. Without a key the built-in designer still handles common requests.

## What can the AI copilot NOT do?
[hdi.ai_limits | chat | needs: none | ui: ai.panel]
Also asked as: what can the ai do; the ai cant do what i asked
1. It cannot delete zones, open or save files, import a paint, export to iRacing, or hand-paint.
2. It can tell you the exact buttons to click. Every change it makes has an Undo.

## How do I make a livery from a description (retro stripes, Gulf style ...)?
[hdi.design_from_words | chat | needs: paint | ui: ai.panel, ai.input]
Also asked as: how do i make a livery from a description
1. Open the AI panel and describe it: "retro red white and blue stripes, flat with chrome trim" or "black and gold two-tone".
2. Refine: "thinner", "make the red orange", "matte", "another take".
3. Press Undo under any answer to go back.

## How do I copy the look of a picture?
[hdi.copy_picture | chat | needs: paint | ui: ai.attach]
Also asked as: copy this picture
1. In the AI panel click the paper-clip (Attach a picture) and choose the livery, logo or flag.
2. Ask it to copy the design or the colours. Needs an AI key; check the preview and refine.

## How do I change the on-screen size of the buttons?
[hdi.ui_size | pro | needs: none | ui: pro.header.ui_smaller, pro.header.ui_larger]
Also asked as: how do i make the buttons smaller
1. Top row, the minus and plus buttons beside the percentage ("UI Smaller / UI Larger"). They resize the toolbars, not the canvas.

## How do I see the keyboard shortcuts?
[hdi.shortcuts | pro | needs: none | ui: pro.settings.keyboard_shortcuts]
Also asked as: what are the keyboard shortcuts
1. Press ? or Settings (gear) > "Keyboard Shortcuts".

## How do I move the finish library or panels out of the way?
[hdi.collapse_panels | pro | needs: none | ui: leftCollapseBtn, rightCollapseBtn]
1. Click the small arrow at the edge of the left or right column to collapse it. Press E to show / hide the zone editor.

## How do I fix a stuck or blank preview?
[hdi.fix_preview | pro | needs: paint | ui: btnPreviewRefresh]
Also asked as: preview is blank; the preview is stuck; preview wont update
1. Press F5 or the "Refresh" button.
2. Click the red "Preview failed" bar if shown.
3. Close and reopen the app if the engine says it is offline.

## Why won't the RENDER button start?
[hdi.render_wont_start | pro | needs: paint | ui: btnRender, paintFile, iracingId, outputDir]
Also asked as: the render button doesnt work; render wont start; nothing works
1. Is a paint loaded? Does the Source Paint box have a full path?
2. Did you enter your iRacing customer ID (4-7 digits)?
3. Does every zone you want have BOTH a colour/area and a finish? A message says which does not.
4. Is another render still running? Wait a minute.

## How do I recolour artwork on the paint itself (not just a finish)?
[hdi.recolour_pixels | pro | needs: paint | ui: pro.toolbar.hue_saturation, pro.toolbar.color_replace]
1. Top toolbar > ADJUST > "Hue / Saturation" (shift every colour) or "Color Replace" (one colour to another).
2. In LAYER mode these edit the selected layer.

## How do I add text (lettering) to the paint?
[hdi.add_text | pro | needs: psd | ui: pro.layers.layer, pro.layers.open_layered]
Also asked as: can i put text on it
1. There is no Text button in the main tool row. The easiest way: make the lettering as a transparent PNG (or in your PSD in Photoshop) and add it with LAYERS tab > "+ Layer".
2. Then move and size it with Move (V) and Transform (Ctrl+T) in LAYER mode.
3. For a PSD, edit the text layer in Photoshop and re-open it with "Open Layered".

## How do I use the eyedropper to match a colour on the car?
[hdi.eyedropper | pro | needs: zone, paint | ui: vtModeEyedropper, eyedropperAddColorBtn, eyedropperSetBtn]
1. Pick Color (P) in the toolbar, choose the zone in the box that appears, click the colour on the SOURCE picture.
2. "+ Add Color" adds it to the zone; "Set" replaces the zone's colour.

## How do I make a car side different from the other side?
[hdi.left_vs_right | pro | needs: paint | ui: zone.draw_box, zone.order]
Also asked as: how do i make the left side different from the right; how do i do a two tone
1. Make one zone per side with APPLY AREA > "Draw box" around each side's panel on the flat sheet.
2. Give each its own finish or colour; both sides are separate rectangles.
3. Or in Chat say "make the left side matte black" if the car's parts are known.

## What are Foundation finishes and what is a "brings its own colours" finish?
[hdi.finish_kinds | pro | needs: none | ui: zone.base_material, zone.base_color_mode]
1. Foundation (f_) finishes change only the shine; with "Use source paint (spec only)" they leave your colours alone.
2. Plain bases (gloss, matte, satin, candy, pearl, metallic) take the zone colour.
3. Special finishes (carbon, camo, holographic, flames ...) bring their own colours: recolour them with Hue Shift, not a solid colour.

## How do I know what the base finishes do?
[hdi.base_finishes | pro | needs: none | ui: zone.base_material]
1. Gloss = standard shiny paint, Matte = flat, Satin = soft sheen, Chrome = mirror, Candy = deep tinted gloss, Pearl = shimmer, Metallic = flake.
2. Hover or tap a finish in the picker to read what it does.

## How do I make a finish more or less glossy?
[hdi.gloss_level | pro | needs: zone | ui: zone.g_rough, zone.b_coat, zone.spec_strength]
Also asked as: how do i make it glossy
1. Spec Sliders: "G Rough" lower = glossier, higher = duller.
2. "B Coat" sets the clearcoat glass look. "Spec Strength" scales it all.

## How do I fix numbers or sponsors that look wrong under a special finish?
[hdi.numbers_look_wrong | pro | needs: psd | ui: zone.restrict_layers, pro.toolbar.decal_rescue_kit]
Also asked as: my numbers look sparkly
1. Make sure the body zone is limited to "Car Paint" under RESTRICT TO LAYERS so numbers are not covered.
2. Use SPEC TOOLS > "Decal Rescue Kit..." if they read sparkly or dull.

## How do I get started with a PSD that has many layers and I'm overwhelmed?
[hdi.psd_overwhelmed | pro | needs: psd | ui: layer.search, mode.easy, spbGuideToggle]
Also asked as: i have too many layers
1. Turn on Training Wheels ("Tutorial").
2. In Pro use the "filter..." box in the LAYERS tab and ignore Mask / Wire / Car_Mandatory.

## How do I go from Easy to the full controls without losing my work?
[hdi.easy_to_pro | easy | needs: paint | ui: easy.pro_btn]
Also asked as: how do i get back to pro
1. Click "PRO MODE ->" at the top right. The paint and zones carry over.

## How do I use SPEC SCULPT?
[hdi.spec_sculpt | pro | needs: paint | ui: pro.header.spec_sculpt]
1. Click "SPEC SCULPT" in the top row for the guided look library of spec-only effects.
2. After saving a Sculpt spec the main RENDER keeps that spec; clear the imported spec map in Settings to go back to zone shine.

## How do I import art or a pack (Shokk Drop)?
[hdi.shokk_drop | pro | needs: paint | ui: pro.header.shokk_drop]
1. Click "Shokk Drop" in the top row.
2. Import art, Import DNA spec, or share .spbdrop packs.

## How do I randomise a look for ideas?
[hdi.randomise | pro | needs: paint | ui: pro.zones_more.rand_current_zone, pro.zones_more.rand_all_zones, swatchDiceBtn]
Also asked as: surprise me; randomize everything; give me ideas
1. Left column > More > "Rand Current Zone" or "Rand All Zones".
2. In the picker, "Surprise me" rolls one good finish. Ctrl+Z undoes.

## What is NOT in Shokker today (animation, other sims, 3D view, a shop, live Photoshop sync, Mac)?
[hdi.not_in_shokker | any | needs: none | ui: btnRender, live_preview]
Also asked as: can i make an animated paint; does it work with other sims; is there a mac version; can i sell my paints; can i paint in 3d; live photoshop sync; glow in the dark
1. Honest answer: that is not available in Shokker today. Not in the app: animated or moving paints, glow-in-the-dark paint (iRacing has no emissive paint), other sims (Shokker writes iRacing paint + spec TGAs only), a 3D car view or painting on a 3D model, a shop or marketplace to sell paints, live sync with Photoshop while you edit, and a Mac version (Windows only).
2. Nearest thing you can do: render, then look at the car in iRacing's own 3D paint viewer; for Photoshop, save your PSD and load it again with "PSD/XCF/ORA" (top row, SOURCE PAINT).
3. Everything else - colours, finishes, patterns, spec - is in Pro; ask "how do I ..." for the steps.
