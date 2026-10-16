# Everyday tool upgrades (AI knowledge card: Text, smart guides, Gradient, Refine Edge, Brush Dynamics, crash recovery)

These upgrades are in the toolbar and the tool options bar. Button and menu names are exactly what the screen shows. They change your layers in Shokker; the car paint and the spec map for iRacing are only written when you press RENDER. Do not promise more than is listed here.

## What is new in the everyday tools
[fix3.whats_new | pro | needs: none | ui: none]
Also asked as: what is new in the tools; text button; smart guides; gradient colours; refine edge; dynamics button; crash recovery
1. Text button (key T) in the tool row, after Erase. The text stays editable.
2. Move (V) has smart guides (coloured lines) and arrow-key nudge. Ctrl = free move, Shift = straight line.
3. Gradient (G) has a Colours button with presets and colour stops, and a live preview.
4. Mask > Refine Edge... cleans a selection edge and can make a cut-out layer.
5. The Brush has a Dynamics button next to Flow: speckle, spray, splatter, confetti and tapered strokes.
6. Copy and Cut follow the soft edge of a feathered selection. The Fill message counts only the pixels that really changed.
7. After a crash, reopen the same file and restore your layers, live text, masks and adjustment layers.

## How do I add text to the car and change it later (Text tool)?
[fix3.text_tool | pro | needs: a loaded paint | ui: none]
Also asked as: text tool; where is the text button; edit my text; change the font; rasterize; text turned into pixels; type on the car; neon text; glow on text
1. Press T, or click Text in the tool row (right after Erase).
2. Choose Font, Bold, Italic, Letter spacing, Text transform and Text effect (Drop Shadow, Outer Glow, Emboss, Neon) in the tool options bar.
3. Click the paint and type. Enter commits the text, Shift+Enter starts a new line.
4. To change it later, click it again with the Text tool, or double-click it with Move (V).
5. Move it with Move (V); scale or rotate it with Transform (Ctrl+T). The RASTERIZE button on its layer card turns it into plain pixels.
Painting over live text, stretching, flipping or skewing also makes it pixels; Ctrl+Z brings the live text back. Bold simple fonts such as Impact, Bebas Neue or Oswald read best from far away. If the number is part of your paint, choose Custom Number in the Car group.

## How do I line things up or centre a logo exactly (smart guides and nudge)?
[fix3.smart_guides | pro | needs: a layer | ui: none]
Also asked as: smart guides; snap to center; center my logo; line up two sponsors; align layers; pink line when i drag; stop snapping; nudge with arrow keys; move one pixel; move straight
1. Pick Move (V) in LAYER mode and select the layer.
2. Drag it. A coloured line shows what it snapped to: magenta = another layer, cyan = the canvas edge or centre, yellow = your selection.
3. Hold Ctrl while dragging to turn the snapping off, or Shift to move in a straight line.
4. For the last pixel use the arrow keys: 1 pixel each, Shift+Arrow for 10. One burst is one undo step.
The cyan line is the middle of the whole 2048 x 2048 sheet, not the middle of the car. For the car's centre line use the Wire layer or Car > Car Stripe....

## How do I make a fade with my own colours (Gradient tool, Colours button)?
[fix3.gradient | pro | needs: a layer | ui: none]
Also asked as: gradient; gradient tool; gradient colours; colour stops; three colour gradient; chrome sweep; fade to transparent; save my gradient; radial gradient; hard stop gradient
1. In LAYER mode, select a layer and pick Gradient (G). Choose Linear, Radial, Reflected, Diamond or Conical.
2. Click Colours (next to Linear and Reverse) to open "Gradient colours".
3. Click a preset chip (for example Sunset, Chrome sweep, Red, White, Blue bands or Foreground to Transparent), or click the colour bar to add stops and set each Stop colour, Position, Opacity and Midpoint to next stop.
4. Drag across the layer. The gradient previews live and applies when you let go. It stays inside an active selection.
5. Save preset keeps your gradient. Ctrl+Z removes it.
The paint sheet is the car cut open, so a fade across the whole sheet breaks at the panel edges. Select one panel (the hood, say) and run the fade inside it.

## How do I clean up the edge of a selection or cut a logo out cleanly (Refine Edge)?
[fix3.refine_edge | pro | needs: a selection | ui: none]
Also asked as: refine edge; select and mask; white halo around my logo; cut out a logo; clean the edge colours; sloppy selection; selection follows the edge
1. Make a rough selection around the logo or number (Rectangle M, Lasso L or Wand W).
2. Open the Mask menu and click Refine Edge... (under Smooth Edges).
3. Raise Edge radius until the red overlay hugs the logo. Tick Smart radius (soft and sharp edges) for soft edges. Check the View buttons: On white and On black.
4. Tune Smooth, Feather, Contrast and Shift edge. Choose Selection, or New layer (cut-out), and tick Clean the edge colours of the cut-out to remove the old background colour.
5. Press Apply. Ctrl+Z undoes it in one step; Cancel throws it away.
It replaces guessing with Feather or Grow for logos and numbers. Copy and Cut also follow the soft edge of a feathered selection.

## How do I make speckles, spray, splatter or a tapered stroke (Brush Dynamics)?
[fix3.brush_dynamics | pro | needs: a layer | ui: none]
Also asked as: brush dynamics; dynamics button; speckle brush; scatter; splatter; overspray; confetti; tapered stroke; taper out; stroke that gets thinner; random colour brush
1. In LAYER mode, select a layer and pick the Brush (B). In ZONE mode the zone brush has Dynamics too, without the colour sliders.
2. Click Dynamics (next to Flow) to open "Brush dynamics".
3. Click a preset: Natural hand, Speckle, Mud splatter, Dust and overspray, Confetti, Two-tone flecks, Taper out or Taper in. Off goes back to the plain brush.
4. Tune Size jitter, Scatter, Dabs per step, Flow jitter, Taper length and the Colour jitters if you like. A toast may say Spacing was set for you.
5. Paint. For a straight tapered line click once, then Shift-click the end.
Speckle and Dust and overspray read best with a small brush (size 6 to 14). It is colour only; for dirt that also changes the shine use the Wear Brush in the Material / Spec menu.

## Why does Fill say the spot is outside the active selection?
[fix3.fill_outside_selection | pro | needs: a selection | ui: none]
Also asked as: fill skipped; fill outside the selection; fill did nothing with a selection; fill says outside the active selection
1. You clicked outside the selection, so nothing was filled.
2. Click inside the selection, or clear it with Ctrl+D.
3. The message after a successful Fill now counts only the pixels that really changed.

## How do I make a perfect square or circle selection (marquee keys)?
[fix3.marquee_keys | pro | needs: none | ui: none]
Also asked as: perfect square selection; perfect circle selection; draw selection from the centre; add to a selection with the marquee; esc cancel selection drag
1. Pick Rect (M) or press M again for the Ellipse.
2. Start dragging, then press and hold Shift for a square or circle, or Alt to draw from the centre.
3. Hold Shift when you start to add to the selection, or Alt to subtract.
4. Esc cancels the drag.

## What if Shokker crashes? Will I lose my layers?
[fix3.recover_after_crash | pro | needs: a loaded paint | ui: none]
Also asked as: shokker crashed; did i lose my layers; recover my layers; restore my work; power cut; spb found your work from an interrupted session
1. Start Shokker and open the same file (Open Paint... > Layered template, or Flat image). It may reopen by itself.
2. A message starting "SPB found your work from an interrupted session" lists what can come back: layers you added, live text, painted layers, layer masks and adjustment layers.
3. Choose to restore. The restore is one undo step.
4. Save a project right away (Save / Open). Recovery does not replace a saved project.
iRacing only gets new files when you press RENDER again, then Ctrl+R in iRacing.

## Does Shokker have clipping masks, and do Photoshop smart objects survive?
[fix3.photoshop_limits | pro | needs: none | ui: none]
Also asked as: clipping mask; clip a zone to a layer; zone only affect one layer; smart objects; photoshop round trip; live photoshop text; rasterise smart objects
1. There is no clipping mask. The nearest thing is RESTRICT TO LAYERS on a zone (COLOR section of the zone): tick the layers and the finish only covers the pixels on them. It is not exactly a clipping mask, so do not promise it is.
2. Smart objects and live Photoshop text are not plain pixels. They are not guaranteed to come back editable after a round trip through Photoshop. Rasterise or flatten them in Photoshop first, then open the file in Shokker again.
3. There is no crop and no flip of the whole design; Transform (Ctrl+T) works on one layer at a time.
