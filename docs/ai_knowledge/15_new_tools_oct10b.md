# Auto Spec, Race Wear Studio, Colourway Studio, the Spec Sculpt panel, the new Shokk Drop page, Edge Bleed and the renamed menus (AI knowledge card)

The Symmetry menu is now called the Car menu and the Material menu is now called Material / Spec. Button and menu names are exactly what the screen shows. These tools change the buyer's layers and spec map in the app; the car paint and the spec files for iRacing are only written when RENDER is pressed. Do not promise more than is listed here. Answer with the tool name the buyer used, and say where the tool is.

## What is the Car menu (it used to be called Symmetry) and what is in it?
[k3.car_menu | pro | needs: none | ui: none]
Also asked as: car menu; symmetry menu; what is in the symmetry menu; where did the symmetry menu go; mirror paint menu; where is number kit; where is sponsor kit; where is race wear
The Car menu is in the tool band, next to Material / Spec. It has three groups.
1. Mirror: Mirror Paint, Mirror To Other Side, Copy To Other Side (Text Reads Right), Re-Measure Car Sides.
2. Place On The Car: Number Kit..., Sponsor Kit..., Car Stripe....
3. Across The Car: Car-Space Fade..., Race Wear....
On a narrow window the menus fold under Menus.

## What is in the Material / Spec menu (it used to be called Material)?
[k3.material_spec_menu | pro | needs: none | ui: none]
Also asked as: material spec menu; material menu; what is in the material menu; where did the material menu go; where is auto spec; where is spec doctor; where is the wear brush
The Material / Spec menu is in the tool band right after Retouch. It has two groups.
1. Brushes: Material Brush (U; Shift+U steps to the next brush), Spec Brush, Wear Brush, Spec Eyedropper, Clear Material Strokes.
2. Whole Car: Layer Materials..., Auto Spec..., Spec Doctor, Shine Lens, Spec Sculpt....

## What is Auto Spec and how do I use it?
[k3.auto_spec | pro | needs: a loaded paint with layers | ui: none]
Also asked as: auto spec; autospec; give every layer a material; first spec for the whole car; spec autopilot; showroom to race worn
1. Open Material / Spec > Auto Spec.... A window opens next to the Live Preview and reads every layer (a few seconds).
2. Each row is one layer: tick box, name (click to select it), Material box, what it thinks the layer is, the parts it sits on, a percent and a reason. Rows marked Not sure start unticked. Leave To The Zones keeps the zone's own finish.
3. Drag the Showroom to Race-Worn dial: Showroom is glossy with mirror chrome, the middle is the default, Race-Worn is satin and matte vinyl.
4. Live Preview shows the proposal under the Shine Lens. Rescan reads the layers again.
5. Apply Auto Spec gives each ticked layer its material in ONE undo step (Ctrl+Z takes it all back), then Spec Doctor checks the result. Cancel puts everything back.
It changes only the spec of the ticked layers. Your artwork and colours are not touched. A flat picture with no layers has nothing to read.

## What is Race Wear Studio and how do I use it?
[k3.race_wear | pro | needs: a loaded paint with its car template | ui: none]
Also asked as: race wear studio; race wear; make the car look raced; worn car in one click; short track oval wear; endurance wear; dirt late model wear; remove race wear
1. Open Car > Race Wear... (Across The Car group).
2. Pick a look: Showroom, Short-Track Oval, Road Course, Dirt Late Model or Endurance 24 h. The car is worn straight away: dirt behind the wheels, bugs and chips on the nose, rubber at door height.
3. Laps (hours for Endurance) builds the wear up or down, Strength fades the whole layer, New Seed gives a different pattern.
4. Keep decals clean keeps numbers and sponsors free of wear. Mask Off Selection keeps the wear off the selected area; Clear Mask undoes that.
5. Hide takes the layer off, Remove deletes it, Ctrl+Z and Ctrl+Y undo and redo exactly. Done closes the window.
Paint and spec change together when rendered: mud is matte, rubber has no clearcoat, bare-metal chips are metallic. The wear is a separate layer, saved with the project and restored after a crash.

## What is Colourway Studio and how do I use it?
[k3.colourway | pro | needs: a loaded paint | ui: none]
Also asked as: colourway studio; colorway; colourways; other colours for my livery; night version of my livery; team colours colourway; change all the colours but keep the finishes
1. Open Adjust > Colourway Studio... (at the bottom of the menu). It reads the 3 to 6 main colours of your art and gives each a role: Main, Accent, Trim or Detail. Black, white and grey are always kept.
2. Click a colourway in the grid (Complementary, Split Complementary, Triadic, Analogous, Tonal, Reverse, Night and more). The right side shows it larger.
3. For your own colours type 2 or 3 hex codes under Team Colours and press Make Team Colourway.
4. Sponsor And Logo Art is left alone unless you tick Recolour sponsors and logos too. Also set a finish per role swaps base finishes as well.
5. See Live Preview shrinks the window so you can watch the car, with < and > to flip colourways. Apply Colourway adds one Colourway layer and updates the zones that pick by colour: ONE undo step. Cancel changes nothing.
Save As Variant keeps a colourway by name; the dropdown on the Colourway layer switches between them.

## What is the Spec Sculpt panel and how do I use it?
[k3.spec_sculpt_panel | pro | needs: a loaded paint | ui: none]
Also asked as: spec sculpt; spec sculpt panel; spec sculpt button in the header; five spec looks; material for each colour; classic lab; keep look
1. Click SPEC SCULPT in the header, or Material / Spec > Spec Sculpt.... A panel opens beside the canvases and reads your main colours.
2. Pick a look: Pop, Stealth, Showroom, Chrome Trim or Satin Race.
3. Under Your Colours set the material of any colour (Leave zones decide keeps the zone's finish). Light Studio (Studio, Sweep, Off) moves a light over the car so chrome flashes and matte stays flat.
4. Keep Look writes it as a normal spec layer: renders, saves and undoes as one step. Cancel or Esc steps it back.
5. Classic Lab at the bottom opens the older Spec Sculpt lab in its own window (spec files from a folder, photo matching).
It changes the spec only, never your paint colours.

## What changed on the Shokk Drop page?
[k3.shokk_drop_page | pro | needs: Shokk Drop open | ui: none]
Also asked as: shokk drop page; shokk drop batch import; use on car; save to library; shokk drop three columns; many images at once
1. The page has three columns: the import rail on the left (type chips Paint, Pattern, Spec overlay, Paint + my spec, Whole car; Import & preview, SHOKK THE WORLD and Batch import... pinned at the bottom), the gallery of your drops in the middle, and a preview panel on the right.
2. New art opens in the preview with Save to library. Discard drops it. Batch import... brings in many images one by one with a progress panel (Stop after this one ends it cleanly).
3. Hover a gallery card and press Use on car. Choose the selected zone, a new whole-car zone, or a named part such as the hood or front bumper. The drop lands on the Paint Booth that opened Shokk Drop, and Ctrl+Z there takes it back.
4. A More menu in the header holds the report, the guide, export all, inbox import and the shortcut list. Press ? for the keys.

## What is Edge Bleed (Bleed Paint Past Panel Edges)?
[k3.edge_bleed | pro | needs: a car template with panel outlines | ui: none]
Also asked as: edge bleed; bleed paint past panel edges; seams in iracing; lines between panels in iracing
1. Open the Settings gear at the top right and look under Options. Tick Bleed Paint Past Panel Edges. It is off by default and Shokker remembers the choice.
2. Render as usual. Each panel's edge paint and spec is copied about 16 pixels into the gap next to it, so cars in the distance show fewer seam lines. Panels themselves are never touched.
3. A flat picture with no panel outlines cannot be bled; the box says so and the render is unchanged.
Save Project keeps whether it is on, and a crash restore keeps it too.

## Does a crash restore or Save Project bring back my tools? What are the new keys?
[k3.restore_keys | pro | needs: none | ui: none]
Also asked as: crash restore; save project keeps; lost race wear after a crash; error report key; merge visible shortcut; n key new zone; ctrl a does nothing
1. After a crash, open the same file again and choose to restore. Car-Space Fade, Sponsor Kit, Number Kit, Race Wear, Layer Materials (with Auto Spec results), Colourway variants, Car Stripe layers, brushed materials and Edge Bleed all come back. One Ctrl+Z undoes the whole restore.
2. Save Project keeps the same tools, so they are there when you open the project.
3. Keys: Ctrl+Shift+E is Merge Visible Layers. Ctrl+Alt+Shift+E opens the error report. N adds a zone, and N and Ctrl+A only work when the workspace has the focus, not inside a dialog, menu or text box.
4. The Sponsor Kit keeps logos clear of Number Kit numbers: a logo moves to the nearest free spot on its part and may shrink, and the note says what moved.
