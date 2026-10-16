# Shine, Material and Symmetry tools (AI knowledge card: what each one does, where it is, the steps)

These tools are in the toolbar and under the Live Preview. Button and menu names are exactly what the screen shows. They only change what the buyer sees until RENDER writes the paint file and the spec file for iRacing. The spec map has four channels: R is metallic, G is roughness (0 is a mirror), B is clearcoat (0 to 15 is none, 16 is maximum gloss, 255 is dull) and A is the mask. Do not promise more than is listed here.

## What is new: the Shine Lens, the Material / Spec menu and the Car menu
[rev.whats_new | pro | needs: none | ui: none]
Also asked as: what is new; whats new; new tools; new features; what changed; where are the new tools
1. Shine bar under the Live Preview: Off, Lens, Full, Sweep. It shows the finish under a studio light.
2. Select > Material... selects every pixel with the same finish.
3. Material / Spec menu in the toolbar, next to Retouch (U, and Shift+U steps through them): Material Brush, Spec Brush, Wear Brush, Spec Eyedropper.
4. Car menu in the toolbar: Mirror Paint, Mirror To Other Side, Copy To Other Side (Text Reads Right), Car Stripe..., Number Kit..., Sponsor Kit..., Car-Space Fade..., Re-Measure Car Sides. Spec Doctor is in the Material / Spec menu.
5. Top row: Open Paint... is one menu with Layered template and Flat image (they replace the PSD/XCF/ORA and TGA/PNG/JPEG buttons). Source Paint and iRacing Car Folder are file chips.
6. First-step fixes: RENDER leaves the guide layers (Wire, Mask, Car Mandatory) out for you. + Layer adds a blank layer and Actions > Place image... brings in a picture. FRACTURE THIS PAINT asks before it applies. Esc closes Save / Open. The render result shows the car first.

## How do I see how my finish catches the light (Shine Lens)?
[rev.shine_lens | pro | needs: a loaded paint | ui: none]
Also asked as: shine lens; shine bar; my chrome looks flat in the preview; see the shine before i render; preview reflections
1. Find the small Shine bar under the Live Preview. Click Lens and move the mouse over the preview: a circle shows that spot under a studio light.
2. Click Full to light the whole preview. Drag on the car, or drag the round light button on the bar, to move the light. Arrow keys nudge it.
3. Click Sweep to make the light circle the car by itself. Best for flake, candy and chrome.
4. Hold the ` key (top left, under Esc) over the car for a quick peek with any tool. Click Off to go back to the flat preview.
It is a preview only: it lights the spec map the preview already made, never renders and never changes files. Sharp stripes mean mirror-smooth, a soft glow means satin, nothing moving means matte or no clearcoat.

## How do I select everything made of the same finish (Select > Material...)?
[rev.select_material | pro | needs: a loaded paint | ui: none]
Also asked as: select all the chrome; select by material; select by finish; select all matte; select everything shiny
1. Open Select in the toolbar and choose Material....
2. Click the car (left side or Live Preview). Everything with the same finish turns teal and shines. Shift+click adds another material, Alt+click removes one.
3. Or press a preset: All Chrome, All Matte, All Gloss Clear, Rough Below N, Metal Above N.
4. Tolerance (starts at 12) widens the match, Soft Edge (starts at 6) feathers it, Contiguous keeps only the patch you clicked, Match Whole Finish (on) treats carbon, flake and candy as one material.
5. Pick Apply As (Replace, Add or Subtract) and press OK. It becomes a normal Zone selection. Esc cancels.
It picks by the spec map, not by colour, so a red chrome panel and a blue chrome panel both count as chrome.

## How do I brush a real finish onto the car (Material Brush)?
[rev.material_brush | pro | needs: a loaded paint | ui: none]
Also asked as: material brush; paint chrome with a brush; brush on candy; paint a finish by hand; what is the u key
1. Open the Material / Spec menu in the toolbar (next to Retouch) or press U.
2. Click the finish button in the bar above the canvas and pick any finish from the normal finish picker.
3. Set Size, Opacity and Hardness, then brush. Soft edges and lower opacity really blend: a 50 percent chrome stroke gives half the metal.
4. The Source view shows the stroke at once. A moment later the Live Preview shows the real finish.
5. Hold Alt and brush to erase. Ctrl+Z and Ctrl+Y undo and redo one stroke. Press RENDER to write it into the paint and spec files.
With a Zone that has an area selected, strokes stay inside it (Clip to in the bar turns that off). Keep Colour in the bar keeps the colour already on the car. Clear removes every Material, Spec and Wear stroke, and Ctrl+Z brings them back.

## How do I change only the shine, metal or roughness with a brush (Spec Brush)?
[rev.spec_brush | pro | needs: a loaded paint | ui: none]
Also asked as: spec brush; make the bumper matte; how do i make it shiny with a brush; change the shine without changing the colour; paint the spec map
1. Open the Material / Spec menu or press Shift+U until you reach Spec Brush.
2. Pick a preset: Gloss, Satin, Matte, Chrome, Brushed Metal, Patina or Clearcoat Fade. Or type 0 to 255 in the M, R and CC boxes.
3. M is metal (spec R channel). R is roughness (spec G channel, 0 is a mirror). CC is clearcoat (spec B channel: 0 to 15 none, 16 maximum gloss, 255 dull). Click a letter to switch that channel off.
4. Brush over the panel. The colours do not change. For Brushed Metal or Patina turn on Grain for fine texture along the stroke.
5. The bottom bar shows on car: the M, R and CC read back after the preview updates. Press RENDER when it looks right.
A CC of 0 to 15 means no clearcoat in iRacing, so keep CC at 16 or more for gloss.

## How do I add dirt, rubber marks or stone chips (Wear Brush)?
[rev.wear_brush | pro | needs: a loaded paint | ui: none]
Also asked as: wear brush; paint dirt on my car; rubber marks; stone chips; make the car look raced; mud on the lower doors
1. Open the Material / Spec menu or press Shift+U until you reach Wear Brush.
2. Pick Dirt / Grime, Rubber Marks or Stone Chips.
3. Stroke along the way the air flows, nose to rear or upward from the sills. Dirt streaks follow the stroke.
4. Dirt is dull and rough, rubber is matte, a stone chip has a bare-metal core, a primer ring and a dark lip. It writes into the paint and the spec in one stroke.
5. Ctrl+Z undoes a stroke. Press RENDER when you like it.
The texture is fine on purpose (about 8 to 32 pixels) so it reads as real wear on a whole car.

## How do I copy a finish from one part of the car to another (Spec Eyedropper)?
[rev.spec_eyedropper | pro | needs: a loaded paint | ui: none]
Also asked as: spec eyedropper; copy the shine from one panel to another; pick up a finish; what is the spec at this spot
1. Open the Material / Spec menu or press Shift+U until you reach Spec Eyedropper.
2. Click a spot on the car (Source or Live Preview). If it says to wait, let the Live Preview finish and click again.
3. On a spot you brushed with the Material Brush it loads that finish into the Material Brush. Anywhere else it loads the exact M, R and CC and the colour into the Spec Brush as Picked.
4. Brush it onto another panel.

## How do I paint both sides of the car at once (Mirror Paint)?
[rev.mirror_paint | pro | needs: a loaded paint | ui: none]
Also asked as: mirror paint; symmetry; paint both sides; mirror my brush strokes; both sides match
1. Pick the Brush, Eraser or a Retouch brush.
2. Click Mirror Paint in the tool options bar at the bottom, or use Car > Mirror Paint.
3. Paint one side. The same stroke lands on the matching part of the car (left to right, and the other half of the hood, roof, trunk and bumpers). A dashed ring shows where the copy lands.
4. Ctrl+Z takes back both sides in one step.
The copy is fitted to the other panel shape, not flipped. Wheel openings stay clear. The first use on a new car takes about 2 to 3 seconds while the car sides are measured. If the sides look off, use Car > Re-Measure Car Sides.

## How do I copy a finished design to the other side (Mirror To Other Side)?
[rev.mirror_to_other_side | pro | needs: a layer or selection | ui: none]
Also asked as: mirror the left side to the right; copy to the other side; text reads right; numbers backwards on the other side
1. Select the layer with the design, or select around one graphic.
2. Open the Car menu. Choose Mirror To Other Side for stripes, flames and shapes (a true mirror image).
3. For numbers and sponsor names choose Copy To Other Side (Text Reads Right) so the lettering reads the right way.
4. Ctrl+Z undoes it. Re-Measure Car Sides measures the car again after a template change.
The copy is fitted to the other panel. Pick an unlocked layer first.

## How do I put a stripe down the middle of the car (Car Stripe)?
[rev.car_stripe | pro | needs: a loaded paint | ui: none]
Also asked as: car stripe; racing stripe; center stripe; twin stripe; stripe down the hood and roof
1. Choose Car > Car Stripe....
2. Set the width, colour and offset. Turn on twin stripe and set the gap for two stripes. Tick bumpers to include them.
3. The preview shows on the car as you change things.
4. Click Add Stripe. It goes on its own layer named Car Stripe, centred and lined up where the hood, roof, trunk and bumpers meet. Ctrl+Z removes it.

## How do I open my car's paint now (Open Paint)?
[rev.open_paint | pro | needs: none | ui: none]
Also asked as: where did the psd button go; where did the tga png jpeg button go; where is open paint; layered template; flat image; how do i load my template; where is the source paint box
1. Top row, click Open Paint... next to the Source Paint chip.
2. Choose Layered template for a PSD, XCF or ORA file with layers (best), or Flat image for a TGA, PNG or JPEG.
3. Pick your car's template in the file window. The Source Paint chip then shows the file name; hover it for the full path.
4. To paste a path instead, click the Source Paint chip, paste the full path and press Enter. Esc goes back to the chip.
5. The iRacing Car Folder is a chip too: hover for the full path, click to type a path. iRacing ID and the Custom Number or Sim-Stamped Number choice sit together in the Car group.
6. Use the template for the same car you drive and never resize it (2048 x 2048). A flat image has no layers, so use Layered template to aim a finish at only the numbers or the body.
