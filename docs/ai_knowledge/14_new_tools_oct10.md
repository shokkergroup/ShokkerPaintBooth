# Sponsor Kit, Number Kit, Spec Doctor, Car-Space Fade, the layer card and in-app dialogs (AI knowledge card)

These tools are in the toolbar (Car menu, Material / Spec menu) and on the selected-layer card. Button and menu names are exactly what the screen shows. They change your layers and what the buyer sees; the car paint and the spec map for iRacing are only written when you press RENDER. Do not promise more than is listed here. Answer with the tool name the buyer used, and say where the tool is.

## Where is the Sponsor Kit and what does it do?
[k2.sponsor_kit | pro | needs: a loaded paint with its car template | ui: none]
Also asked as: sponsor kit; sponser kit; one logo on every panel; same size logo on both doors; logo with a white box; clean a logo and place it on the car; sponsor kit chrome foil; sponsor kit gold
1. Open the Car menu in the tool band and choose Sponsor Kit... (right under Number Kit). Nothing moves on the car yet.
2. Drop a logo (PNG, JPG or SVG) on the box, or press Choose File.... For a layer you already have, select it and press Use Selected Layer.
3. Check Before and After. Remove Box takes off the white or flat box and the JPEG fringe. Click the box in Before to pick its colour. Raise Edge for leftover fringe, lower Tolerance if part of the logo went, leave Clear Inside off for white lettering.
4. Tick the parts with the Slots chips: Left Door, Right Door, Hood, Trunk / Deck, Left or Right Rear Quarter, Left or Right TV Panel, Left or Right Roof Rail.
5. Size is the real size: the line under it shows centimetres on each part. "Bigger than the room on..." means it would run over that part's edge.
6. Material: None, Chrome Foil, Gold Leaf (patchy on purpose), Gold Foil (solid, best for lettering), Matte Vinyl, Gloss Vinyl. These change the spec map too.
7. Press Add Sponsor Kit. One Ctrl+Z takes back the whole kit. Remove Kit deletes all its layers later. Each part is a normal layer, so dragging one moves only that part.

## Where is the Number Kit and what does it do?
[k2.number_kit | pro | needs: a loaded paint with its car template | ui: none]
Also asked as: number kit; numbr kit; car number on both doors and the roof; put my number on the roof; change the car number everywhere; replace the old numbers; sim stamped number
1. Open Car > Number Kit.... Type the number (1 to 4 letters or digits). It appears at once on the Left Door, the Right Door and the Roof, each turned to read right on the car.
2. Pick Font, Bold, Italic, Slant, Gap, Fill, Outline 1, Outline 2, Shadow and an optional Panel. Every place updates together.
3. Under Places switch Left Door, Right Door, Roof on or off. Roof says which side it reads from. Size scales all three.
4. Material: None, Chrome Foil, Gloss Vinyl, Satin Vinyl or Matte Vinyl.
5. If the paint already has numbers the dialog asks: Replace Existing (takes their height, centre and slant), Add Alongside, or Cancel.
6. If Sim-Stamped Number is on in the Car group, iRacing stamps its own number over yours. Press Use Custom Number in the warning.
7. Press Add Number Kit. One Ctrl+Z takes it back. Later, click a kit number with the Text tool to edit all places; Remove Kit deletes the lot.

## What is Spec Doctor and how do I use it?
[k2.spec_doctor | pro | needs: a loaded paint | ui: none]
Also asked as: spec doctor; spec docter; check my spec map; why does my chrome look black; clearcoat 1 to 15; dull coat; fix spec mistakes; check before uploading to iRacing
1. Open Material / Spec > Spec Doctor (also in Spec Tools; on a narrow window under Menus > Material / Spec). A panel opens next to the Live Preview.
2. Press Run Check. It renders the car at full size, the same spec map RENDER writes, about 20 to 40 seconds.
3. Each card says how serious it is (High, Medium, Tip), what it is, where it is (by car part) and why it matters in iRacing.
4. Show draws a magenta overlay on the Live Preview over the exact pixels. Press the fix button to apply a fix (Ctrl+Z undoes it). Ignore hides a card; Show Ignored brings it back.
It checks: Chrome Over Near-Black Paint, Clearcoat Set To 1-15 (that means NO clearcoat in iRacing), Dull Coat On A Mirror-Smooth Area, No Clearcoat Anywhere, a decal that took the body chrome, One Material On The Whole Car, a spec that sits some pixels off the paint, and pixel noise. Nothing changes until a fix button is pressed. A clean car says "Nothing to fix".

## What is Car-Space Fade and how do I use it?
[k2.car_space_fade | pro | needs: a loaded paint with its car template | ui: none]
Also asked as: car-space fade; car space fade; fade along the car; nose to tail fade; chrome to matte fade; both sides match; gradient differs left and right
1. Open Car > Car-Space Fade.... A panel opens.
2. Pick a Direction: Nose to Tail, Bottom to Top, Centre to Out, or Custom (Pick 2 points, then click the start and the end on the car). Reverse swaps the ends.
3. Parts: click a part name to take it out of the fade. Spread over: Chosen parts runs the fade over just the chosen parts.
4. Stops: drag a stop, press + Stop to add one. Each stop has a colour and a material (Keep, Gloss, Satin, Matte, Chrome or Finish...). Untick Colour to fade only the material.
5. Keep decals on top (ticked by default) keeps numbers, sponsors, logos and the Car Mandatory layer exactly as they are, with the fade under them.
6. Press Add Fade. It shows in the Live Preview and Shine Lens and is written by RENDER. Reopen the panel to edit or remove it. Fades are saved inside the project file and come back when you open it.
A normal Gradient runs across the flat sheet, so the two sides and the hood, roof and trunk can differ. Car-Space Fade runs along the car.

## Where did the buttons on the layer card go?
[k2.layer_card | pro | needs: a layer | ui: none]
Also asked as: layer card icons; more menu; where is flip; where is rotate 90; where is solo; where is export as png; where is make zone from layer; layer card changed
1. Select a layer. Its card has one row of five icons: Duplicate Layer, Mirror Clone, Free Transform, Merge Down, Delete Layer, then More.
2. More is grouped. Arrange: Duplicate Layer, Mirror Clone, Merge Down, Solo Layer (then Restore Layers), Rename, Delete Layer. Transform: Move, Free Transform, Flip Horizontal, Flip Vertical, Rotate 90, Pan to Layer, Fit to Layer.
3. Effects: Stroke FX..., FX Strength. Output: Export as PNG, Make Zone from Layer, Lock Zone to Layer, Rasterize Text (live text only). Deselect Layer is last.
Old names: DUPE, MIRROR, XFORM, MERGE, FLIP H, FLIP V, ROT 90, EXPORT, MAKE ZONE, LOCK ZONE, DONE. No button was removed. Shift+click Duplicate Layer makes a copy 50 px away.

## Why does a name box look different, and why did Rename do nothing before?
[k2.in_app_dialogs | pro | needs: none | ui: none]
Also asked as: rename box does nothing; name box; prompt is not supported; save preset name; link zone pick list; resize canvas box; guide position box
1. The installed app has no browser pop-up for typing text, so buttons that asked for a name or a number did nothing. They now open Shokker's own small dialog.
2. Type the name or number, press Enter or OK to accept, Esc or Cancel to leave everything as it was. A number out of range shows a message under the box.
3. Link a zone shows a pick list of the other zones. Layer rename, comment, colour tag and preset name open a small box beside the layer card.
4. Are-you-sure questions (delete, discard) are still normal Windows boxes and work as before.

## Does Brush Dynamics work with the zone brush and Mirror Paint?
[k2.brush_updates | pro | needs: none | ui: none]
Also asked as: dynamics in zone mode; zone brush scatter; mirror paint with dynamics; taper in; taper pause; dynamics off resets spacing
1. In ZONE mode the zone mask brush has the Dynamics button too: scatter, size jitter, count and flow jitter, and taper. The colour sliders are dimmed because a zone is a mask and has no colour.
2. With Mirror Paint on (Car menu) the other side gets the same stroke, including the taper, in the same position.
3. A tapered stroke keeps its taper if you pause mid-stroke. Off and Reset put back the Spacing and Hardness a preset changed.
4. The zone brush on a scoped zone is faster than before.
5. After a crash, reopening the same file offers to restore your added layers, live text, masks and adjustment layers. This also works for a flat TGA, PNG or JPEG source, not only a PSD.
