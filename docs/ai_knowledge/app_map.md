# Where everything is: the app map (AI knowledge card, generated from scripts/ai_atlas/ui_map.json)

Use these names exactly. Modes: PRO (full shop), CHAT (talk to Shokker). The Pro zone editor is the ZONE POPOUT PANEL that opens when a zone card is clicked. There is no File menu: saving a project is the "Save / Open" button. Dropping a picture on the canvas replaces the paint; "+ Layer" adds a logo.

## Pro: Header rows (1 of 3)
Top of the window: iRacing User ID, Number type, Source Paint (TGA / PSD) and iRacing Car Folder. These decide WHAT is painted and WHERE the files go. Where: Pro > top of the window, first rows (iRacing User ID, Source Paint, iRacing Car Folder).
- **Download Update** (button): Downloads the new Shokker version. Watch out: Save your project first; installing restarts the app.
- **Remind Me Later** (button): Hides the update banner for now.
- **IRACING USER ID box** (text input): Your iRacing customer number (4-7 digits); it is part of the saved file names. Watch out: A wrong ID means iRacing ignores the files.
- **CUSTOM NUMBER** (toggle): Custom Number: the number is part of your paint and iRacing will not add one. Watch out: Needs Settings > Graphics > Hide Car Numbers ON in iRacing to load car_num_.
- **SIM-STAMPED NUMBER** (toggle): Sim-Stamped Number: iRacing stamps your number on the car in the series font. Watch out: Do not also paint a number on the template.
- **SOURCE PAINT box** (text input): The paint file Shokker works on (a flat TGA / PNG / JPEG, or a PSD): type or paste a path, or use the buttons beside it. Watch out: Pasting a folder path here does not load a paint. A flat TGA has no layers; a PSD does.

## Pro: Header rows (2 of 3)
- **TGA/PNG/JPEG** (button): Browse for a flat paint picture (TGA / PNG / JPEG / BMP) and load it as the paint. Watch out: Dropping an image on the canvas also REPLACES the paint; it does not add a logo (use + Layer for that).
- **PSD/XCF/ORA** (button): Browse for a layered PSD / XCF / ORA template so every layer (body, numbers, sponsors, tape) stays separate. Watch out: Make sure the template layers (Mask, Wire, Car_Mandatory) are OFF before exporting.
- **IRACING CAR FOLDER box** (text input): The iRacing car folder the finished paint and spec files are written to. Watch out: Point to the car FOLDER, not a TGA file. It sets the file names car_num_ID.tga or car_ID.tga and...
- **Pick detected iRacing car** (button): Pick your car from the list of iRacing cars Shokker detected (most recently painted first). Watch out: If your car is missing, paint it once in iRacing or browse for the folder.
- **Browse iRacing car folder in Windows File Explorer** (button): Browse for the iRacing car folder in Windows. Watch out: Pick the car's own folder inside Documents/iRacing/paint, not a TGA file.
- **FRACTURE THIS PAINT** (button): One click puts a Soul Core Emerald / Pink Flash finish into the selected zone's base (and its colour unless Color Lock is on). Watch out: Changes the zone's colour too unless the Lock is on.

## Pro: Header rows (3 of 3)
- **Settings** (button): Opens Settings: licence, keyboard shortcuts, ZIP export, spec map import, Live Link, Training Wheels.
- **Tutorial** (button): Training Wheels: step-by-step quests that teach the app as you use it (load, zone, finish, render, then patterns, spec, overlays), plus a hint chip for your next move. Watch out: Toggle it any time; it is also a checkbox in Settings.
- **Make UI chrome smaller** (button): shrink toolbar / panel chrome (does NOT zoom the canvas)
- **UI Larger** (button): grow toolbar / panel chrome (does NOT zoom the canvas)
- **SPEC SCULPT** (button): Open the complete guided Spec Sculpt look library
- **Shokk Drop** (button): import art, Import DNA spec, share .spbdrop packs
- **Encyclopedia** (button): SPB Encyclopedia: how everything in Shokker works - spec maps, zones, finishes, every control. Press / inside to search.

## Any mode: PRO / CHAT pill
Switches between the full shop and the talk-to-Shokker front door. The paint and zones carry across. Where: Any mode > top row > PRO / CHAT pill.
- **PRO** (button): Switch to the full Pro shop.
- **CHAT** (button): Switch to Chat (talk to Shokker).

## Pro: Top toolbar (1 of 6)
Tool row (Move, Pick, Color, Wand, Lasso, Rect, Brush, Fill, Erase), the HISTORY / SELECT / RETOUCH / MASK / SPEC TOOLS / TRANSFORM / ADJUST menus, the ZONE / LAYER target switch, RENDER HISTORY, Save / Open and Import Recipe. Where: Pro > top toolbar (tool row).
- **Move** (button): Move tool (V): in Layer mode click a sponsor / number to drag it; Alt forces the whole layer. Watch out: Switch ZONE / LAYER to LAYER first.
- **Pick** (button): Pick Item (Y): pick one sponsor / number inside a layer for independent move / rotate.
- **Color** (button): Color (P): click a colour on the paint to select by it. In Pro zone mode it feeds the selected zone's colour list.
- **Wand** (button): Magic Wand (W): click to select similar colour; Shift adds, Alt subtracts; Tolerance sets how similar.
- **Lasso** (button): Lasso (L): draw a free-hand selection. Watch out: Enter closes the shape.
- **Rect** (button): Rectangle select (O): drag a box selection.
- **Brush** (button): Brush (B): paint the zone's mask, or the selected layer's pixels. Watch out: ZONE mode paints a mask; LAYER mode paints pixels.
- **Fill** (button): Fill bucket (K): fill a region of the zone mask or the layer.
- **Erase** (button): Eraser (E): erase zone mask or layer pixels.
- **History** (menu): HISTORY menu: Undo, Redo, Undo History.

## Pro: Top toolbar (2 of 6)
- **Undo Ctrl+Z** (button): Undo the last stroke, transform or layer action (Ctrl+Z).
- **Redo Ctrl+Y** (button): Redo (Ctrl+Y or Ctrl+Shift+Z).
- **Undo History…** (button): Opens the recent-actions list so you can jump back several steps.
- **Select** (menu): SELECT menu: Select All Color, Grab Object, Smart Region Fill, Move Selection Border, Pick Layer Element, Zone Pick, Elliptical Marquee.
- **Select All Color** (button): Select All Color (A): select every pixel of the sampled colour across the whole paint.
- **Grab Object** (button): Grab Object (G): click inside a number or logo and its whole outline is selected. Watch out: Works best on clear solid shapes.
- **Smart Region Fill** (button): Smart Region Fill: click inside an edge-bounded area to select it.
- **Zone Pick** (button): Zone Pick: click a spec pattern / base piece to move, rotate and resize it independently.
- **Retouch** (menu): RETOUCH menu: Color Brush, Recolor, Healing Brush, Smudge, Burn - pixel retouching on the selected layer. Watch out: Grey until a blank layer exists: use the Add blank for Color Brush button.
- **＋ Add blank for Color Brush** (button): Adds a blank layer so the Color Brush has somewhere to paint.
- **Color Brush** (button): Color Brush (C): paint solid colour or a pattern brush onto the selected layer. Watch out: Needs a blank paintable layer (use + Blank layer).

## Pro: Top toolbar (3 of 6)
- **Recolor** (button): Recolor (R): paint a new hue over a sampled colour on the selected layer.
- **Mask** (menu): MASK menu: Grow / Shrink / Fill Holes / Feather / Smooth / Invert / Copy / Mirror a zone's area, plus Include / Exclude Region.
- **Spec Tools** (menu): SPEC TOOLS menu: Decal Rescue Kit, Lighting Mask, Material Sampler, Range Remapper.
- **Decal Rescue Kit…** (button): Puts a flat / satin / gloss NON-metallic spec under sim-stamped numbers and sponsors so they read cleanly.
- **Lighting Mask…** (button): Controls the spec alpha channel (fake holes, grille openings, recessed vents). Watch out: Advanced.
- **Material Sampler…** (button): Click the compiled spec map to read exact Metallic / Roughness / Clearcoat values and copy them to a zone.
- **Range Remapper…** (button): Retunes Metallic / Roughness / Clearcoat ranges inside the active zone while keeping the texture.
- **Transform** (menu): TRANSFORM menu: Transform (Ctrl+T) and Fit Layer to Zone Selection.
- **Adjust** (menu): ADJUST menu: Brightness/Contrast, Hue/Saturation, Color Replace, Invert, Grayscale, Gradient Map, Vibrance, Color Temperature. Watch out: These edit the paint pixels; finishes and zone Hue Shift are render settings.

## Pro: Top toolbar (4 of 6)
- **Hue / Saturation** (button): Shifts hue and saturation of the selected layer or paint. Watch out: Applies to pixels, unlike zone Hue Shift which is a render setting.
- **Color Replace** (button): Replaces one colour with another everywhere on the layer or paint. Watch out: This edits pixels; for finishes use a zone.
- **ZONE** (button): ZONE mode: toolbar tools edit zones and masks. Watch out: Tools behave differently in ZONE vs LAYER mode - check this switch if a tool "does nothing".
- **LAYER** (button): LAYER mode: toolbar tools edit the selected layer's pixels.
- **Recent** (button): Recent Renders: recall one of your last 10 saved renders and restore its recipe.
- **Save / Open** (button): Save / Open: saves or loads a complete workflow in one file (paint incl. PSD, every zone, all layer settings). Watch out: There is no File menu; this is the save.
- **Import Recipe** (button): Imports a .shokkerrecipe (yours or shared) and restores the recipe (colours, finishes, effects) on this car.
- **Xform** (button): Layer mode: selected artwork or selection. Zone mode: current pattern or base.
- **Excl** (button): paint areas on the car to REMOVE from this zone's color match (red overlay)
- **Move Selection Border** (button): Arrow moves 1px, Shift+Arrow moves 10px; drag inside to move freely; pixels do not move

## Pro: Top toolbar (5 of 6)
- **Pick Layer Element** (button): always force isolation of one sponsor/number/shape inside the layer for its own tight transform box
- **Elliptical Marquee** (button): drag a Zone selection; Shift makes a circle, Alt draws from center, Esc cancels
- **Healing Brush** (button): Alt+click clean texture on the selected Layer, then paint to blend its detail into the target
- **Smudge** (button): smear selected Layer pixels in the drag direction
- **Burn** (button): darken selected Layer pixels under the brush
- **＋ Grow 1 px** (button): expand the active Zone selection by one pixel
- **＋ Grow 2 px** (button): add edge safety around an active Zone selection
- **Shrink 1 px** (button): contract the active Zone selection by one pixel
- **Shrink 2 px** (button): pull the active Zone selection inward
- **Fill Holes** (button): include empty islands fully enclosed by the active selection
- **Feather 2 px** (button): soften the active Zone selection edge
- **Smooth Edges** (button): smooth jagged mask boundaries
- **Invert Mask** (button): swap selected and unselected areas
- **Copy Mask** (button): copy this zone's mask to another zone
- **Mirror Mask** (button): flip mask horizontally
- **Include Region** (button): paint areas to keep in zone color match
- **Exclude Region** (button): paint areas to remove from zone color match

## Pro: Top toolbar (6 of 6)
- **Erase Spatial** (button): remove include/exclude paint
- **Transform** (button): Layer mode: selected artwork or selection. Zone mode: current pattern or base.
- **Fit Layer to Zone Selection** (button): proportionally fit the selected artwork Layer inside the active Zone mask, then Enter applies or Esc cancels
- **Brightness / Contrast** (button): adjust image brightness and contrast
- **Invert Colors** (button): negate all pixel colors
- **Grayscale** (button): convert to black and white
- **Gradient Map** (button): map a color gradient to luminosity
- **Vibrance** (button): boost muted colours without over-saturating already-vivid ones
- **Color Temperature** (button): warm or cool the image (Kelvin shift)
- **RENDER HISTORY** (menu): click a thumbnail to rebuild it fully
- **Gallery** (button): view all past renders in a grid, search + compare

## Pro: Settings (gear)
Licence key, Keyboard Shortcuts, ZIP export, Live Link / auto-deploy, imported spec map, Training Wheels, file picker style. Where: Pro > Settings (gear) > License.
- **ZIP export checkbox** (toggle): Bundles paint TGA, spec TGA and preview into a ZIP on every render.
- **Import TGA** (button): Import an existing spec map TGA to merge under your render. Watch out: Use Clear to go back to the default spec.
- **Auto-deploy (Live Link) checkbox** (toggle): Auto-deploy: copies every render to your iRacing car folder automatically. Watch out: Only matters when the car folder is empty; with a car folder set, files are copied after each render anyway.
- **Licence key box** (text input): Enter your Shokker Paint Booth license key (format: SHOKKER-XXXX-XXXX-XXXX, 19 characters total)
- **Activate** (button): Validate and activate your license key
- **Deactivate** (button): required if you want to use the key on a different machine
- **Training Wheels checkbox** (toggle): step-by-step quests and a next-move hint chip that teach the app while you use it
- **Keyboard Shortcuts** (button): Show all keyboard shortcuts (press ?)
- **Clear** (button): Remove imported spec map and render on default base
- **Close (Esc)** (button): Close shortcuts overlay (Esc)

## Pro: ZONES (left column)
The list of zones, top = highest priority. Each card shows what it covers. + Add Zone, Reset All Zones, More menu. Click a card to open its ZONE POPOUT PANEL. Where: Pro > left column (ZONES).
- **+ Add Zone** (button): Adds an empty zone at the top. Watch out: A new zone does nothing until you give it a colour / layer / box AND a finish.
- **Reset All Zones** (button): Resets to the default set of zones (confirmed, undoable).
- **More** (button): Opens the More menu (presets, randomise, apply to all, library, templates, SHOKK files, channel PNG export).
- **Collapse arrow (left column)** (button): Collapses or expands the ZONES column.
- **Zone editor tab (E)** (button): Shows or hides the floating ZONE POPOUT PANEL (press E).

## Pro: ZONES > More menu (1 of 2)
Presets Gallery, randomise, Apply Finish to All, Shokker Library, Undo History, templates, SHOKK files, PNG channel export. Where: Pro > left column > ZONES > More (three-dot) menu.
- **Presets Gallery** (button): Browse ready-made zone layouts / looks and apply one.
- **Rand Current Zone** (button): Randomises the finish of the selected zone. Watch out: Ctrl+Z undoes.
- **Rand All Zones** (button): Randomises every zone. Watch out: Overwrites your finishes (undoable).
- **Apply Finish to All** (button): Gives the same finish to every zone.
- **Shokker Library** (button): Opens the Shokker Library of saved looks.
- **Undo History** (button): Opens the Undo History list.
- **Save as Template** (button): Saves the current zone layout as a named template.
- **Load Template... dropdown** (dropdown): Dropdown of your saved zone templates; choosing one loads it.
- **LOAD SHOKK FILE** (button): Loads a saved .shokk session.
- **SAVE SHOKK** (button): Saves the zones and finishes (and optionally the paint) as a .shokk file.
- **PNG Channels Export** (button): Exports the paint and the spec channels as PNG pictures for inspection or Photoshop.
- **Export folder box (PNG channels)** (text input): Folder where PNG channel exports are written.
- **Browse Folder** (button): Choose the export folder in Explorer.

## Pro: ZONES > More menu (2 of 2)
- **Smart Randomize checkbox** (toggle): Smart Randomize: picks good-looking combinations instead of pure chance.
- **e.g. My 3-Color Layout (max 60 chars)** (text input): use a descriptive name you'll recognize later
- **Save** (button): Save current zone layout as a reusable template

## Pro: ZONE POPOUT PANEL (1 of 9)
Where one zone is edited: COLOR (which pixels), APPLY AREA (box / lasso), BASE (finish + colour + strengths + spec sliders), SPEC OVERLAYS, PATTERN, OVERLAYS (2nd to 5th base). Where: Pro > ZONE POPOUT PANEL.
- **Reset Zone** (button): Puts this one zone back to its defaults (finish, colour, patterns, sliders). Watch out: It resets the zone, not the whole car - Reset All Zones in the left column does that.
- **COLOR (section)** (section): Decides WHICH PIXELS of the paint this zone owns: by clicked colour, by PSD layer, or as catch-all (Remaining). Watch out: A zone with no colour, layer or box set does nothing ("No color or region set yet" warning).
- **RESTRICT TO LAYERS (checkboxes per PSD layer)** (toggle): Tick a layer (Car Paint, Sponsors, Numbers, Tape ...) and the zone only covers pixels that exist on that layer. Watch out: Layers named Mask / Wire / Car_Mandatory are template layers - do not restrict to them. Unticking...
- **PICK COLOR FROM CAR** (button): Arms an eyedropper: click a colour on the car and this zone grabs every pixel of that colour. Each further click ADDS another colour. Watch out: Anti-aliased edges need tolerance; if edges are left over raise tolerance. Colours that also appear on...

## Pro: ZONE POPOUT PANEL (2 of 9)
- **Remaining** (button): Makes this zone the catch-all: it gets every pixel no zone above it claims. Watch out: Put it at the BOTTOM of the zone list; higher zones win overlaps.
- **HEX (colour box and colour wheel) + Apply** (text input): Type or pick a colour to select by (with Apply), or use the wheel which applies live. Watch out: This chooses which paint pixels to catch, it does not recolour them. To RECOLOUR use BASE > Base Color >...
- **Colour tolerance (sliders next to the colour chips)** (slider): How close a pixel must be to the picked colour to belong to the zone (about 30-50 normal; 6 = exact shade, 100 = loose). Watch out: Too high grabs neighbouring colours; too low leaves fringes around lettering.
- **Hard Edge** (toggle): Cuts the zone edge sharp instead of softly anti-aliased. Watch out: Hard edges can look jagged on diagonal lines.
- **APPLY AREA (section)** (section): Limits the zone to a drawn shape (box or lasso) or a refined colour area, on top of the colour/layer choice. Watch out: "Draw box" boxes are on the flat unwrapped sheet; one box may cover several car panels.
- **Draw box** (button): Click, then drag a rectangle on the paint; the zone only affects what is inside it. Watch out: The box is on the flat sheet - the hood and the roof are different rectangles, not one.

## Pro: ZONE POPOUT PANEL (3 of 9)
- **Lasso (apply area)** (button): Draw a free-hand outline; the zone only affects what is inside. Watch out: Close the shape by returning near the start point.
- **Refine color** (button): Keeps the colour selection but lets you paint a green brush to limit it to places you choose. Watch out: Needs a colour already set on the zone.
- **Activate (apply area)** (button): Turns the stored apply area on again after you cleared or paused it.
- **Clear (apply area)** (button): Removes the drawn box / lasso so the zone is back to colour/layer only.
- **Fit pattern/base swatch into box** (toggle): Instead of tiling across the sheet, fit one copy of the pattern / base texture into the drawn box. Watch out: Only base + pattern are fitted, not spec overlays.
- **BASE (section)** (section): Everything about the surface look: finish, colour source, hue / saturation / brightness, strengths, scale, rotation, spec sliders. Watch out: Without picking a finish the zone shows source paint unchanged.
- **Base Material (finish picker button)** (picker): Opens the finish picker popup: bases (gloss, matte, satin, chrome, candy, pearl, metallic ...) and special looks. Shows the current finish name. Watch out: Foundation (f_*) finishes change only the spec when colour = Use source paint; bases like chrome / candy...

## Pro: ZONE POPOUT PANEL (4 of 9)
- **Lock (Base Color lock)** (toggle): When on, switching finish keeps your zone colour instead of auto-adopting the finish's default colour.
- **BASE COLOR dropdown** (dropdown): Where the zone colour comes from: Use finish's own color / Use source paint (spec only) / Use solid color / From special / Custom gradient. Watch out: Solid colour on a finish that brings its own colours (carbon, camo, holographic ...) flattens it to one...
- **Solid colour swatch / hex (appears with Use solid color)** (picker): Paints the zone this exact colour with the finish's shine on top. Watch out: Only used when BASE COLOR = Use solid color.
- **Custom gradient (stops + direction)** (section): 2 to 10 colour stops fading across the zone in a chosen direction. Watch out: Direction runs on the flat sheet, so each car side may fade differently - use one zone per side to control...
- **Hue Shift** (slider): Rotates every colour around the colour wheel (-180 to +180). Keeps the finish's structure. Watch out: Shift = target hue minus current hue; +150 on green gives purple, not pink.
- **Saturation** (slider): How vivid or grey the colour is (-100 to +100).
- **Brightness** (slider): Lighter or darker (-100 to +200).

## Pro: ZONE POPOUT PANEL (5 of 9)
- **Base Strength** (slider): Fades the whole base look over the source paint: 0 = original paint, 100 = full finish. Watch out: This also reduces colour changes; for shine only use Spec Strength.
- **Spec Strength** (slider): Overall strength of the spec map (shine / metal / coat) of this zone.
- **Base Scale** (slider): Size of the finish's texture inside this zone (0.05x to 5.0x; 1.00x is normal). Smaller = finer, more repeats. Watch out: Scales the texture, NOT the colours or the whole car; spec follows it unless Independent Spec is ticked.
- **Base Rotation** (slider): Rotates the finish's texture in 5 degree steps.
- **Color Depth** (slider): For candy / tinted finishes: 0 = no tint, 15 = glaze, 65 = rich, 100 = deepest. Watch out: Only shows on candy-like finishes.
- **Color Flip** (slider): Adds a second hue that appears at an angle (0 = off, 90 = neighbour, 180 = opposite). Watch out: Only on finishes that support it.
- **Underglow** (slider): How much of the ground coat burns through the brights.
- **Independent Spec (checkbox by Spec Scale)** (toggle): Lets Spec Scale differ from Base Scale; otherwise spec follows the base size.
- **Spec Scale** (slider): Size of the shine / metal texture (0.05x-5.0x) when independent. Watch out: Ignored until Independent Spec is ticked.
- **Spec Rotation** (slider): Rotates the spec channels in 5 degree steps.

## Pro: ZONE POPOUT PANEL (6 of 9)
- **Spec Blend** (dropdown): How a pattern changes this base's optics: Normal, Ghost Carve, Chrome Inlay, Frost Etch, Angle Flip, Ember Gate, Depth Press, and legacy Multiply / Screen / Overlay...
- **Spec Sliders (R Metal, G Rough, B Coat)** (section): Three sliders (-127 to +127) that push the whole zone's spec map: R = metal, G = roughness (low = mirror), B = clearcoat. Watch out: B Coat is inverted in iRacing terms - the number moves clearcoat strength, see the tooltip. Spec only...
- **Auto-Pop** (button): One click nudges the three spec sliders toward glossier (more metal flash, less rough, deeper clearcoat) so the zone pops on track. Watch out: It nudges from where the sliders are; press repeatedly for more, Reset arrows to go back.
- **Spec preset... dropdown** (dropdown): Applies a named spec feel (Wet Candy, Track Flash, Chrome Mirror, Deep Gloss, Soft Pearl, Satin Matte) to the R/G/B sliders.
- **Save spec preset (disk icon)** (button): Saves this zone's R/G/B spec shifts under a name you can reuse.
- **R Metal** (slider): Pushes the METAL channel (-127 to +127). More metal = the body colour flashes harder.
- **G Rough** (slider): Pushes ROUGHNESS (-127 to +127). Lower = sharper mirror flashes, higher = soft satin glow.
- **B Coat** (slider): Pushes CLEARCOAT (-127 to +127). 16 is max gloss: minus = glossier (stops at 16), plus = duller.

## Pro: ZONE POPOUT PANEL (7 of 9)
- **SPEC OVERLAYS + ADD SPEC OVERLAY** (section): Stack spec-only textures on top of the base: they change shine / metal / roughness patterns, never the colour. Watch out: Colour preview will not show them; look at the spec channel views.
- **+ ADD SPEC OVERLAY** (button): Opens the spec-overlay picker to add one more spec texture layer. Watch out: Up to 5 layers on the primary base.
- **PATTERN (section)** (section): Adds a visible pattern (carbon, camo, flames, stripes ...) on this zone, with Paint mode, Opacity, Strength, Hue, Saturation, Spec amount, Scale, Rotate and Position.
- **Pattern 1 picker (name + dropdown arrow)** (picker): Choose the pattern from the catalogue; "None" (x) removes it.
- **+ Add Layer (pattern)** (button): Adds a second / third pattern layer to the zone.
- **Paint mode (Overlay / Blend)** (dropdown): Overlay = the pattern paints its own colours over the paint; Blend = it keeps the underlying paint colour. Watch out: In Overlay the pattern's own colours win, so the base colour is hidden - use Blend or Hue to recolour.
- **Opacity (pattern)** (slider): How visible the pattern is, 0-100%.
- **Strength (pattern)** (slider): Pattern paint strength in 5% steps; spec amount is separate.
- **Hue / Saturation (pattern)** (slider): Recolours only the pattern artwork (hue -180..180, saturation -100..100). Overlay mode uses this colour.

## Pro: ZONE POPOUT PANEL (8 of 9)
- **Spec amount (pattern)** (slider): Starts at 0% so your base shine stays; raise to reveal the pattern's own metal / rough / coat. Watch out: Spec starts at 0 on purpose.
- **Scale (pattern)** (slider): Size of the pattern: smaller = more repeats, larger = zoomed in (0.1x to 4x). Watch out: On a whole-car canvas a normal-size pattern looks huge: go below 1.0x for fine detail.
- **Rotate (pattern)** (slider): Rotates the pattern 0-359 degrees (also a number box).
- **Pattern placement: Full Canvas / Fit to Zone / Edit on Template** (button): Choose how the pattern is placed: tiled over the sheet, fitted to the zone, or dragged by hand on the template.
- **Advanced Pattern Control Panel (Position X / Y, Flip H / V, Strength Map)** (section): Slide the pattern left/right and up/down, flip it, or paint where it is strong versus weak.
- **OVERLAYS (2nd to 5th base)** (section): Stack extra base finishes over the first with blend modes.
- **2nd Base (picker) + Add 3rd overlay** (picker): Pick a second finish blended on top of the primary base; "+ Add 3rd overlay" shows the next slot.
- **Zone order (drag handle and priority)** (section): Top zone wins where two zones select the same pixels. Watch out: Remaining belongs at the bottom.

## Pro: ZONE POPOUT PANEL (9 of 9)
- **Zone eye / duplicate / link / x icons on each zone card** (button): Eye hides a zone for testing, the copy icon duplicates, the x deletes it. Watch out: x removes the zone (undoable with Ctrl+Z).
- **Color Scale / Color Rotation** (slider): Zooms and rotates the colour art (gradient or borrowed special colours) without touching the material texture. Watch out: Solid colours have nothing to scale; these only appear for From special / Custom gradient.
- **Intensity (zone strength, legacy preset buttons)** (slider): Overall strength of the zone's effect: lower = closer to the original paint and a calmer spec. Watch out: Not seen in the live panel of build 10.0.3 (listed in app_controls.json); prefer Base Strength / Spec...
- **Wear / weathering** (slider): Scuffs and ages the finish (chips, dulling). Watch out: Not seen in the live panel of build 10.0.3; check for a Wear control or ask Chat for a weathered finish.

## Pro: Centre column (1 of 2)
The paint (SOURCE) and the LIVE PREVIEW of the finished car, zoom buttons, the RENDER button and the spec channel strip. Where: Pro > centre > empty canvas.
- **Blank Canvas** (button): Blank Canvas: start from plain white to design from scratch.
- **Zone overlay opacity percent** (slider): Zone overlay opacity: how strongly the zone colour overlay shows on the canvas (default 50%).
- **Import PSD** (button): Import PSD: load a Photoshop template to get editable layers.
- **Load TGA** (button): Load TGA: load a flat paint picture (no layers).
- **Edit Big** (button): Edit Big: hide the live preview and edit the source canvas larger.
- **SOURCE** (button): SOURCE view: the original paint canvas where tools work.
- **CAR** (button): CAR view: show the rendered car under the canvas while tools stay active.
- **SPLIT** (button): SPLIT view (Shift+V): source and live preview side by side.
- **Load Paint Image** (button): browse for a car paint TGA file
- **Spatial brush size** (slider): Spatial brush size
- **Blank Canvas** (button): start with a blank white canvas for color-shift effects
- **Refresh** (button): aborts any stuck render, clears pipeline, and re-runs. Use this if the preview is hung.
- **B/A** (button): compare the last preview against the current one
- **Channels** (button): view spec map channels and numeric values

## Pro: Centre column (2 of 2)
- **Zoom out canvas** (button): decrease canvas zoom
- **Zoom In (Ctrl+Plus)** (button): increase canvas zoom
- **FIT** (button): fit canvas in viewport
- **1:1** (button): 100% zoom (1:1 pixels)
- **Compare** (button): before/after comparison slider

## Pro: Tool options bar (1 of 5)
Appears under the toolbar; its sliders change with the tool you picked (brush size, wand tolerance, text font ...). Where: Pro > centre > tool options bar (changes with the active tool).
- **Selection mode dropdown (Add / Replace / Subtract)** (dropdown): How a new selection combines with the existing one: Add (+), Replace, Subtract.
- **Brush size in pixels** (slider): Brush / eraser size in pixels (1-300); [ and ] keys change it.
- **Brush shape dropdown** (dropdown): Shape of the brush tip: round, square, diamond, slash, noise.
- **Pattern Brush — paint with a texture instead of solid color** (dropdown): Paint with a texture instead of a solid colour.
- **Eraser mode — soft brush, hard square block, or clear the current Layer / Zone mask** (dropdown): Eraser style: soft brush, hard block, or clear the whole layer / zone mask.
- **Gradient shape used by the active Layer or Zone** (dropdown): Shape of the gradient tool: linear, reflected, radial, angular, diamond.
- **Gradient Reverse** (toggle): Flips the gradient direction.
- **Gradient Fg To Transparent** (toggle): Fade the foreground colour to transparent instead of to the background colour.
- **Font** (dropdown): Font for text options. Watch out: There is no Text button in the main tool row; add lettering as a PNG layer.
- **Text Bold** (toggle): Bold text option.

## Pro: Tool options bar (2 of 5)
- **Text Italic** (toggle): Italic text option.
- **Text transform** (dropdown): Text case: as typed, UPPERCASE, lowercase, Capitalize.
- **Text effect** (dropdown): Text effect: drop shadow, outer glow, emboss and more.
- **Shape type** (dropdown): Shape for the shape tool: rectangle, rounded rectangle, ellipse, triangle, polygon, star, line.
- **Shape Filled** (toggle): Fill the shape with the fill colour.
- **Shape stroke color** (picker): Outline colour of a shape.
- **Start cap** (dropdown): Line start cap: flat, round, arrow.
- **End cap** (dropdown): Line end cap: flat, round, arrow.
- **Dash style** (dropdown): Line style: solid, dashed, dotted, dash-dot.
- **Fg Color Picker** (picker): Foreground (paint) colour for brushes and fills; X swaps with background.
- **Layer Brush / Fill paint source** (dropdown): Brush / Fill source on a layer: solid colour or a baked Special finish.
- **Clone Aligned** (toggle): Aligned clone: the source moves with the brush.
- **Healing Aligned** (toggle): Aligned healing source.
- **Color difference allowed (higher = more colors included)** (slider): How different a colour can be and still get picked (higher = more colours).
- **Wand Contiguous** (toggle): Contiguous: only select touching pixels of that colour (off = everywhere).

## Pro: Tool options bar (3 of 5)
- **Sample area — averages color under cursor for more forgiving selection** (dropdown): Sample area for the wand: single point or an average of 3x3 / 5x5 / 11x11 pixels.
- **Wand Anti Alias** (toggle): Smooths the wand selection edge.
- **Active paint tool opacity percent** (slider): Active paint tool opacity: 100% (range 1-100%). Press 1-9 keys for quick opacity (1=10%, 5=50%, 0=100%).
- **Smudge strength percent** (slider): Smudge strength: how firmly each dab carries picked-up pixels (1-100%).
- **Dodge and Burn tonal range** (dropdown): Choose which tones Dodge or Burn affects most
- **Dodge and Burn exposure percent** (slider): Dodge/Burn exposure: strength built up by each pass (1-100%). Number keys set exposure.
- **Blur and Sharpen strength percent** (slider): Blur/Sharpen strength: effect built up by each pass (1-100%). Number keys set strength.
- **Brush hardness percent** (slider): Brush hardness: 100% (range 0-100%, 0=soft feather, 100=hard edge). Use { } keys to adjust.
- **Brush flow percent** (slider): how fast paint builds up per pass (1-100%)
- **Brush spacing percent of brush size** (slider): distance between dabs (% of brush size)
- **Brush stroke smoothing percent** (slider): averages pointer jitter (0-100%). 10% is the natural default.

## Pro: Tool options bar (4 of 5)
- **Brush stabilizer distance in pixels** (slider): Lazy-mouse stabilizer rope in source pixels (0-200px). Higher values make the brush tip trail the pointer.
- **Reference image opacity** (slider): Reference image opacity
- **Font size (px)** (number input): Font size (px)
- **Fill color** (picker): Fill color
- **Outline color** (picker): Outline color
- **Outline width** (number input): Outline width
- **Letter spacing (px)** (number input): Letter spacing (px)
- **Line height multiplier** (number input): Line height multiplier
- **Shape fill color** (picker): Shape fill color (used when Fill is checked)
- **Shape stroke width in canvas pixels** (number input): Shape stroke width in canvas pixels (0 disables stroke)
- **Shape corner radius in canvas pixels** (number input): Rectangle corner radius in canvas pixels
- **Shape vertex count** (number input): Polygon or star vertex count
- **#hex** (text input): Foreground hex color
- **Swap foreground and background colors** (button): swap foreground and background colors
- **Reset foreground and background colors** (button): Reset foreground/background colors to default black/white (button only — D is Dodge)
- **Save Swatch** (button): save foreground color to swatches
- **Choose Special...** (button): Choose a baked Special finish for layer fill / brush

## Pro: Tool options bar (5 of 5)
- **Choose Special...** (button): Current baked Special source
- **PathSelection** (button): Close any open path and convert it to the active Zone selection
- **Clear Path** (button): Clear current path without changing selection history
- **Clone opacity percent** (slider): Clone opacity
- **Set source** (button): Arm source picking, then click a clean area on the canvas
- **Clear source** (button): Forget the current Healing source
- **Save snapshot** (button): Capture the current composite and every Layer for selective restoration
- **Clear** (button): Forget the saved History Brush source
- **Auto-feather selection edges (px). 0 = off (hard edge). Any value softens the edge of the NEXT selection you commit (marquee / lasso / wand / pen / smart-fill), so the finish fades in at the border. One Undo reverts the whole selection.** (number input): Auto-feather selection edges (px). 0 = off (hard edge). Any value softens the edge of the NEXT selection you commit (marquee / lasso / wand / pen / smart-fill), so...
- **Edge Preview** (button): shows detected boundaries in red so you can adjust tolerance before clicking
- **Spatial brush size** (slider): Spatial brush size
- **Erase** (button): Erase spatial include/exclude strokes
- **Erase** (button): Erase brush/wand/region strokes

## Pro: Selection / mask bar
Under the canvas: Include / Exclude brushes, Undo / Redo, Deselect, Invert, Grow / Shrink / Feather / Smooth, Copy / Mirror mask, Zoom to selection. Where: Pro > centre > selection / mask bar under the canvas.
- **Include** (button): paint areas to KEEP in zone's color match (green overlay)
- **Exclude** (button): paint areas to REMOVE from zone's color match (red overlay)
- **Undo** (button): Undo last stroke (Ctrl+Z)
- **Redo** (button): Redo last undone action (Ctrl+Y / Ctrl+Shift+Z)
- **Deselect** (button): Clear selection for the current zone
- **Invert** (button): Invert the current zone selection
- **Spatial** (button): Clear spatial include/exclude for current zone
- **Clear All** (button): Clear ALL drawn regions
- **+ Grow** (button): Expand selection outward by 2px
- **+1** (button): Expand selection by 1px
- **Shrink** (button): Contract selection inward by 2px
- **Contract selection by 1px** (button): Contract selection by 1px
- **Fill** (button): Fill enclosed holes in selection
- **Feather** (button): Soften selection edges (grow then shrink)
- **Smooth** (button): Smooth jagged selection edges
- **Copy** (button): Copy this zone's mask to another zone
- **Mirror** (button): Mirror mask horizontally (flip leftright)
- **Zoom** (button): Zoom viewport to fit current zone's selection

## Pro: Preview and spec channels (1 of 2)
LIVE PREVIEW of the render plus COMBINED / R METAL / G ROUGH / B COAT views of the spec map. Where: Pro > centre > spec channel strip under the preview.
- **R METAL** (button): Red channel of the spec map: Metallic (brighter = more metal).
- **G ROUGH** (button): Green channel: Roughness (darker = mirror, lighter = matte).
- **B COAT** (button): Blue channel: Clearcoat (16 = max gloss, 255 = dull).
- **Refresh** (button): Refresh preview (F5): aborts a stuck render and re-runs the live preview.
- **Before After** (button): Before / After (B): compare the last preview with the current one.
- **Spec Map Inspector** (button): Channels inspector: spec map channels with numeric values.
- **COMBINED** (button): hover to enlarge, click for full view
- **ALL** (button): Show all spec channels combined
- **R Metal** (button): Metallic (0=dielectric, 255=full metallic)
- **G Rough** (button): Roughness (0=mirror smooth, 255=fully matte)
- **B Coat** (button): Clearcoat (16=max gloss, 255=dull)
- **A Mask** (button): Specular Mask (rarely used, advanced control)
- **PAINT** (button): View paint preview
- **SPEC MAP** (button): View spec map preview
- **Close lightbox** (button): Close lightbox (Esc)
- **ALL** (button): Show all spec channels combined
- **R Metal** (button): Metallic (0=dielectric, 255=metallic)
- **G Rough** (button): Roughness (0=mirror, 255=matte)

## Pro: Preview and spec channels (2 of 2)
- **B Coat** (button): Clearcoat (16=max gloss, 255=dull)

## Pro: RENDER and recipe card (1 of 2)
RENDER makes the finished paint + spec TGAs; the recipe card afterwards offers Copy Card, Save Card PNG, Share Recipe, Copy TP Desc, Save to keep, Deploy. Where: Pro > centre > RENDER button.
- **RENDER** (button): RENDER (Ctrl+R): builds the finished paint TGA and the spec TGA and writes them to the iRacing car folder. Watch out: It will not start if the paint, customer ID or car folder is missing, or template layers are still on.
- **Copy Card** (button): Copies the recipe card picture to the clipboard (paste into Discord).
- **Share Recipe** (button): Downloads this look as a .shokkerrecipe file with preview.
- **Save to keep** (button): Copies this render to a subfolder so the next render does not overwrite it.
- **Deploy Car Select** (dropdown): Pick another iRacing car to also copy this render to.
- **Deploy Now** (button): Copies this render to the chosen car's iRacing folder.
- **Save Card PNG** (button): Save this recipe card as a PNG image file
- **Copy TP Desc** (button): copy Trading Paints description (zone finishes, colors) to clipboard
- **Recent renders** (button): recall one of the last 10 saved renders and restore its full recipe
- **Deploy to a different car** (button): This render is already in the active car's iRacing folder (Live Link). Open this to also copy it into a different car's folder.

## Pro: RENDER and recipe card (2 of 2)
- **Close render statistics** (button): Close render stats panel

## Pro: Right column
Tabs: FINISHES (library) and LAYERS (PSD layers). Where: Pro > right column.
- **FINISHES** (tab): FINISHES tab: opens the full-screen finish library.
- **LAYERS** (tab): LAYERS tab: PSD layer list.
- **Collapse arrow (right column)** (button): Collapses or expands the FINISHES / LAYERS column.

## Pro: LAYERS tab (1 of 3)
The layer list of a PSD / XCF / ORA: eye, name, opacity, blend, lock, ... plus Open Layered, + Layer, Actions, filter box. Where: Pro > right column > LAYERS tab.
- **Open Layered** (button): Import a layered PSD / XCF / ORA with its layer tree.
- **+ Layer** (button): + Layer: adds a PNG / JPG / WebP / GIF as a NEW image layer on top (a logo, a sponsor). Watch out: Dropping a file on the canvas instead REPLACES the paint.
- **Actions** (button): Actions: + Blank layer, Flatten document, Merge visible, Photoshop round-trip, Thumbnail size. Watch out: Flatten discards layer separation.
- **e.g. DLM438-base-001** (text input): Name for the exported car file in the Photoshop round trip.
- **Path to export folder...** (text input): Folder shared with Photoshop for the round trip.
- **Export** (button): Exports layers to the exchange folder for Photoshop editing; bring the TGA back afterwards.
- **Clear All** (button): Clears all layer effects (Layer Effects dialog).
- **Apply** (button): Applies the layer effects.
- **Layer eye icon** (toggle): Shows / hides the layer. Alt+click isolates that layer. Watch out: Leaving Mask / Wire / Car_Mandatory on paints them into the car.
- **Layer opacity** (slider): Fades the layer 0-100% (drag, or type an exact number).

## Pro: LAYERS tab (2 of 3)
- **Layer blend mode** (dropdown): How the layer mixes with those below (Normal, Multiply, Screen, Overlay ...).
- **Layer lock** (toggle): Locks the layer so it cannot be painted or changed. Watch out: The Shokker AI cannot edit locked layers - unlock first.
- **Create a zone restricted to this layer** (button): One click makes a zone that only covers this layer's pixels; then give it a finish.
- **Lock the active zone to this layer (Ctrl+L)** (button): Restricts the currently selected zone to this layer.
- **Rename / duplicate / delete / merge / flip / rotate / effects icons** (button): Standard layer housekeeping: rename, duplicate (Shift = offset copy), delete, merge into the layer below, flip, rotate 90 degrees, Layer Effects (drop shadow, glow,... Watch out: Delete removes the layer art from the document; use the eye to just hide it.
- **Filter layers box** (text input): Type part of a layer name or group to narrow a long list; Escape clears. Watch out: There is no sort-by-colour: the list is in PSD order. To work BY COLOUR use a zone with PICK COLOR FROM CAR.
- **Layer name (click) / Ctrl+click / double-click** (button): Click selects the layer; Ctrl+click moves it on the canvas; double-click opens Layer Effects.
- **+ Blank layer** (button): Add a blank transparent layer to paint on with the Retouch brushes

## Pro: LAYERS tab (3 of 3)
- **Flatten document** (button): hidden Layers and Zone links are disclosed before removal
- **Merge visible** (button): Ctrl+Shift+E
- **Photoshop round-trip** (button): Export layers for Photoshop editing and bring the TGA back (round trip)
- **Thumbnail size** (button): Cycle layer thumbnail size (small / medium / large)
- **Layers filter box** (search box): Escape clears
- **Cancel layer effects dialog** (button): Cancel (Esc)

## Pro: FINISHES library
Full-screen browser of the whole catalogue (about 4,800 looks) with search, filters and favourites. Where: Pro > FINISHES library (full-screen).
- **Finish library search box** (text input): Search the finish library by name, description or #tag. Watch out: Try plain words ("gold chrome") or hashtags (#carbon).
- **Toggle favorites-only filter** (button): filter to starred finishes
- **Library** (button): close fine tuning panel
- **Automatically collapse other sections when opening a new one** (toggle): Automatically collapse other sections when opening a new one

## Pro: Base Material picker
Popup opened from a zone BASE section: search, #hashtag chips (#carbon, #chrome ...), On-Car Stage, Surprise me, See on paint, Color Lock. Where: Pro > zone editor > Base Material picker (popup).
- **Color: AUTO** (button): Color Lock: when ON, picking a finish keeps your current colour instead of adopting the finish's default.
- **Finish picker search box** (text input): Search finishes in the base picker by name, idea or #tag.
- **Surprise me** (button): Surprise me: rolls a high-ranked finish onto the On-Car Stage; confirm with Enter / click.
- **See on paint** (button): See on paint: previews the selected finish on your paint file.
- **Clear search** (button): Clears the search so the whole list shows again.
- **USE IT** (button): USE IT: applies the previewed finish to this zone.
- **Preview on paint** (button): Applies the preview of the selected finish on your paint.
- **Internal picker review queue** (button): Internal picker review queue
- **Internal picker category planning** (button): Internal picker category planning
- **‹ ON-CAR STAGE** (button): Show on-car preview

## Pro: Spec Tools (1 of 3)
Decal Rescue Kit, Lighting Mask, Material Sampler (read M/R/CC of any pixel), Range Remapper. For spec-map fixing. Where: Pro > Spec Tools > Material Sampler.
- **Point reads the exact UV pixel; local median rejects isolated flake and texture outliers** (dropdown): Sample size for the Material Sampler: exact pixel or local median.
- **Copy M/R/CC/A** (button): Copies the M / R / CC / A values you sampled.
- **Select Connected** (button): Selects the connected area with the same material values.
- **Select All Similar** (button): Selects every pixel with similar material values.
- **Apply to Active Zone** (button): Gives the active zone the sampled material values.
- **Clear Zone Override** (button): Removes the sampled override from the zone.
- **Flat Vinyl Neutralizes chrome or candy beneath numbers and sponsor stamps. M 0 R 100 CC 110** (button): Flat vinyl spec under numbers / sponsors: neutralises chrome or candy beneath.
- **Satin Decal Keeps printed vinyl readable with a controlled soft sheen. M 0 R 100 CC 75** (button): Satin decal spec: keeps printed vinyl readable.
- **Gloss Decal Adds clean printed gloss without metallic contamination. M 0 R 42 CC 22** (button): Gloss decal spec: clean printed gloss.

## Pro: Spec Tools (2 of 3)
- **Use Source Alpha Remove SPB's override and preserve the finish or imported map. AUTO** (button): Lighting mask: use the source file's alpha, removing Shokker's override.
- **Full Lighting Force normal lighting and reflections in the selected footprint. A 255** (button): Lighting mask: force normal lighting.
- **Reduced Lighting Half-strength response for recessed vents and deep seams. A 128** (button): Lighting mask: half-strength lighting response.
- **Kill Lighting Suppress spec and environment light for cutout geometry. A 0** (button): Lighting mask: suppress spec and environment (fake a hole or dead-dark vent).
- **Original** (button): Range Remapper preset: original values.
- **Metallic Texture** (button): Range Remapper preset: metallic texture.
- **Printed Vinyl** (button): Range Remapper preset: printed vinyl.
- **Matte Texture** (button): Range Remapper preset: matte texture.
- **Gloss Texture** (button): Range Remapper preset: gloss texture.
- **Range Remapper: MLow** (number input): Metallic range low end (0-255).
- **Range Remapper: MHigh** (number input): Metallic range high end.
- **Range Remapper: RLow** (number input): Roughness range low end.
- **Range Remapper: RHigh** (number input): Roughness range high end.
- **Range Remapper: CCLow** (number input): Clearcoat range low end.

## Pro: Spec Tools (3 of 3)
- **Range Remapper: CCHigh** (number input): Clearcoat range high end.
- **Restore Original** (button): Puts the zone's original spec ranges back.
- **Apply Remap** (button): Applies the remapped ranges to the active zone.
- **ALL** (button): Show all four spec map channels combined
- **R Metallic** (button): Red channel: Metallic (0=dielectric, 255=full metallic)
- **G Roughness** (button): Green channel: Roughness (0=mirror smooth, 255=fully matte)
- **B Clearcoat** (button): Blue channel: Clearcoat (16=max gloss, 255=dull, 0-15=none)
- **A Mask** (button): Alpha channel: Specular mask (rarely used, advanced control)
- **Maximum allowed difference in each M/R/CC/A channel; 0 selects exact matches** (slider): Maximum allowed difference in each M/R/CC/A channel; 0 selects exact matches

## Pro: Undo History
List of recent actions with Undo / Redo / Clear. Where: Pro > Undo History panel.
- **Undo** (button): Undo last action (Ctrl+Z)
- **Redo** (button): Redo last action (Ctrl+Y / Ctrl+Shift+Z)
- **Clear** (button): Clear all history (cannot be undone)

## Pro: SHOKK files (1 of 2)
Save or load a whole session (zones + finishes, optionally the paint) as a .shokk file. Where: Pro > ZONES > More > LOAD SHOKK FILE.
- **Close SHOKK Library** (button): Closes the SHOKK library.
- **e.g. Purple Color Shift v1** (text input): Name for the .shokk file.
- **Your name or username (optional)** (text input): Your name (optional) stored in the file.
- **Short description of this paint recipe (e.g. 'Holographic chrome with red flake highlights — works great on dark cars')...** (text input): Short description of the recipe.
- **Search by name, author, or tag...** (text input): Filter SHOKK files by name, author, or tag
- **Open Selected** (button): Open the selected SHOKK file
- **Channel PNG Export** (button): extracts selected SHOKK paint/spec into PNG inspection files. This does not create final iRacing TGAs.
- **Path to PS export folder...** (text input): folder where paint_base.png, spec_full.png, and separated channel PNGs are written
- **Browse** (button): Choose folder in File Explorer
- **Folder** (button): Open the SHOKK Library folder in Explorer
- **Save SHOKK** (button): Save current session as a .shokk file
- **Include the paint TGA in the .shokker preset file for full portability** (toggle): Include the paint TGA in the .shokker preset file for full portability

## Pro: SHOKK files (2 of 2)
- **Save SHOKK** (button): Save the current zones, finishes, and (optionally) paint to a .shokk file

## Pro / Chat: Shokker AI panel (1 of 2)
The "AI" button (bottom right) opens the copilot: type what you want, it changes zones; each answer has Undo. Gear = key, model, Claude / ChatGPT connection. Where: Pro / Chat > Shokker AI panel.
- **AI button (bottom right)** (button): Opens the Shokker AI panel (the copilot).
- **Shokker AI panel** (panel): Chat window: type what you want, the copilot changes zones and layers. Works with no key for common requests (colours, matte / gloss / chrome, stripes, spec looks). Watch out: It cannot import files, export, or hand-paint; it can only tell the buyer where to click.
- **Tell me what you want... box** (text input): Type your request; Enter sends, Shift+Enter adds a line.
- **Attach a picture** (button): Attach a livery you like, a logo or a flag; the AI can copy its design or colours (needs an AI key). Watch out: Cheap models cannot read UV sheets; results may need correcting.
- **Undo (under each answer)** (button): Puts everything back the way it was before that answer (all zones and layer changes of that answer).
- **Another take / Refine / Ask the AI** (button): Another try with a different idea; Refine looks at the preview and fixes what is off; Ask the AI undoes and lets the AI have a go.

## Pro / Chat: Shokker AI panel (2 of 2)
- **Gear (key, model, daily cap, Claude / ChatGPT connection)** (button): Settings: your OpenRouter key and model (one model only), a daily spending cap, and "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth" with... Watch out: The gear MODEL only applies to the in-app copilot; Claude Desktop uses its own model. Use Take over in SPB...
- **Use Claude Desktop through MCP** (toggle): Install Shokker into Claude Desktop, then ask Claude "Using Shokker Paint Booth, give me a Gulf-style livery". Changes appear in the AI panel with Undo. Watch out: Restart Claude Desktop after installing; Shokker must be open.
- **Connect ChatGPT / Codex** (toggle): Add SPB to Codex settings, restart Codex and sign in with ChatGPT. Watch out: Your subscription limits apply.

## Chat: Chat mode
Pro screen plus the AI copilot opened for talking; same zones, same Undo. Where: Chat > Chat mode.

## Retired controls (not in this build)
Fleet mode and Season mode are retired in this booth build: the panel stays hidden, nothing opens it, and the buttons only show a "disabled" message. Do not send a buyer to them. Render one car at a time with the normal RENDER button.
- **Add Car, Add Race, Quick: Wear Ramp, Render All Cars, Render All Races** (retired buttons): they cannot be clicked. For a worn look pick a worn Base Material and lower Base Strength (see the Wear article).
