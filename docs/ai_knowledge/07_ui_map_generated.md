# Where things are in the app RIGHT NOW (AI knowledge card, generated from the real UI)

IMPORTANT: the tutorials mention menus like File, View and Layer with paths such as "File -> Import as Layer" or "View -> Channel Inspector". The current app does NOT have those menus. Describe buttons only by the names listed here (top toolbar menus, header buttons, Layers panel). Dropping an image file onto the centre canvas LOADS IT AS THE WHOLE PAINT FILE (it replaces the paint), it does not add a logo layer.

## Top toolbar menu: History
- **Undo Ctrl+Z** — Undo (Ctrl+Z) — undo last stroke, transform, or layer action. Also available via right-click ▸ Undo.
- **Redo Ctrl+Y** — Redo (Ctrl+Y / Ctrl+Shift+Z) — redo last undone action. Also available via right-click ▸ Redo.
- **Undo History…** — Undo History — open recent action list

## Top toolbar menu: Select
- **⊞ Select All Color** — Select All Color (A) — click to sample matching pixels across the full visible source; Shift adds, Alt subtracts
- **Grab Object** — Grab Object (G) — click inside a solid part of a number or logo to include its outline and shadow. Samples visible paint: hide wire/template guide layers if they split the artwork. Shift adds, Alt subtracts.
- **Smart Region Fill** — Smart Region Fill — click inside an edge-bounded region; Tolerance changes boundary sensitivity, Shift adds, Alt subtracts
- **⬌ Move Selection Border** — Move Selection Border — Arrow moves 1px, Shift+Arrow moves 10px; drag inside to move freely; pixels do not move
- **⊕ Pick Layer Element** — Pick Item (explicit) — always force isolation of one sponsor/number/shape inside the layer for its own tight transform box
- **⧉ Zone Pick** — Zone Pick — click spec patterns / bases / sub-pieces for independent move, rotation and proportional resize (handles, live numbers, snapping).
- **⬭ Elliptical Marquee** — Elliptical Marquee (M) — drag a Zone selection; Shift makes a circle, Alt draws from center, Esc cancels

## Top toolbar menu: Retouch
- **＋ Add blank for Color Brush**
- **Color Brush** — Color Brush (C) — paint solid RGB or the selected Pattern Brush onto the selected Layer
- **Recolor** — Recolor Tool (R) — on the selected Layer, first click samples source; paint foreground hue/chroma while preserving light and texture
- **Healing Brush** — Healing Brush (Shift+J) — Alt+click clean texture on the selected Layer, then paint to blend its detail into the target
- **Smudge** — Smudge Tool (Q) — smear selected Layer pixels in the drag direction
- **Burn** — Burn (J) — darken selected Layer pixels under the brush

## Top toolbar menu: Mask
- **＋ Grow 1 px** — Grow Selection 1px — expand the active Zone selection by one pixel
- **＋ Grow 2 px** — Grow Selection 2px — add edge safety around an active Zone selection
- **− Shrink 1 px** — Shrink Selection 1px — contract the active Zone selection by one pixel
- **− Shrink 2 px** — Shrink Selection 2px — pull the active Zone selection inward
- **Fill Holes** — Fill Selection Holes — include empty islands fully enclosed by the active selection
- **Feather 2 px** — Feather Selection 2px — soften the active Zone selection edge
- **∿ Smooth Edges** — Smooth Edges — smooth jagged mask boundaries
- **⊘ Invert Mask** — Invert Mask — swap selected and unselected areas
- **Copy Mask** — Copy Mask — copy this zone's mask to another zone
- **Mirror Mask** — Mirror Mask — flip mask horizontally
- **Include Region** — Include Region — paint areas to keep in zone color match
- **Exclude Region** — Exclude Region — paint areas to remove from zone color match
- **Erase Spatial** — Erase Spatial Strokes — remove include/exclude paint

## Top toolbar menu: Spec Tools
- **Decal Rescue Kit…** — Decal Rescue Kit — apply a flat, satin, or gloss non-metallic spec beneath sim-stamped numbers and sponsors while preserving source paint
- **Lighting Mask…** — iRacing Lighting Mask — control the spec TGA alpha channel for fake holes, grille openings, recessed vents, and deep seams
- **Material Sampler…** — Material Sampler — click the compiled spec map to read exact M/R/CC/A values and transfer them to an active Zone selection
- **≋ Range Remapper…** — Material Range Remapper — tune Metallic, Roughness, and Clearcoat ranges inside the active Zone while preserving spec texture

## Top toolbar menu: Transform
- **⊞ Transform** — Transform (Ctrl+T) — Layer mode: selected artwork or selection. Zone mode: current pattern or base.
- **Fit Layer to Zone Selection** — Fit Layer to Zone Selection — proportionally fit the selected artwork Layer inside the active Zone mask, then Enter applies or Esc cancels

## Top toolbar menu: Adjust
- **Brightness / Contrast** — Brightness / Contrast — adjust image brightness and contrast
- **Hue / Saturation** — Hue / Saturation — shift colors and saturation levels
- **Color Replace** — Color Replace — change one color to another everywhere
- **⊘ Invert Colors** — Invert Colors — negate all pixel colors
- **Grayscale** — Grayscale — convert to black and white
- **Gradient Map** — Gradient Map — map a color gradient to luminosity
- **⊕ Vibrance** — Vibrance — boost muted colours without over-saturating already-vivid ones
- **Color Temperature** — Color Temperature — warm or cool the image (Kelvin shift)

## Top toolbar menu: RENDER HISTORY
- **Gallery** — Open render history gallery — view all past renders in a grid, search + compare
- **Recent** — Recent Renders — recall one of the last 10 saved renders (survives restart) and restore its full recipe

## Header command buttons (top of the window)
- **SPEC SCULPT** — Open the complete guided Spec Sculpt look library
- **Shokk Drop** — SHOKK DROP — import art, Import DNA spec, share .spbdrop packs
- **FRACTURE THIS PAINT** — FRACTURE THIS PAINT — one click drops Soul Core Emerald / Pink Flash into this zone's base material (and its base color unless Color Lock is on)
- **Save / Open** — SPB Projects — save or load a complete workflow: the open paint (PSD included), every zone, and all layer settings in one file
- **Import Recipe** — Import a .shokkerrecipe file (your own or one shared with you) and restore the full recipe into your zones

## Layers panel (right column, LAYERS tab) buttons
- **Open Layered** — Import a layered PSD, XCF, or ORA file
- **+ Layer** — Add Layer — import PNG/JPG as a new layer on top
- **Actions** — Layer document actions
- **+ Blank layer** — Add a blank transparent layer to paint on with the Retouch brushes
- **Flatten document** — Flatten the whole document into one Layer — hidden Layers and Zone links are disclosed before removal
- **Merge visible** — Merge all VISIBLE layers into one (hidden layers survive) — Ctrl+Shift+E
- **Photoshop round-trip** — Export layers for Photoshop editing and bring the TGA back (round trip)
- **Thumbnail size** — Cycle layer thumbnail size (small / medium / large)
- **Close** — Close Finish Library (Esc)

## Saving your work and coming back later
Press **Save / Open** (header row, top right of the tool row): SPB Projects saves or loads a complete workflow in one file - the open paint (PSD included), every zone, and all layer settings. **Import Recipe** / **Share Recipe** move just the zone recipe (colours, finishes, effects) as a .shokkerrecipe file, which works across cars. There is no File menu; Ctrl+S is not documented for projects, so point to the **Save / Open** button.

## Adding a logo or an image
Use the Layers panel (right column, LAYERS tab): **+ Layer** adds a PNG / JPG / WebP / GIF as a new image layer; **Open Layered** imports a whole PSD / XCF / ORA template. Spec Stamps (**Import Stamp**) take a transparent PNG whose alpha marks an area that only changes the spec map. The copilot itself cannot import files.
