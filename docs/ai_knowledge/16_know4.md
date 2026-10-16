# Car numbers that are not in the paint, opacity versus shine, banded gradients and what the AI cannot download (AI knowledge card)

Four questions the buyers keep asking. Answer with the facts below, in the buyer's own words, and say which control or menu to use. Do not promise more than is listed here.

## How do I erase the car numbers when the car or class has none, or when the sim adds them?
[k4.erase_numbers_sim | pro | needs: none | ui: none]
Also asked as: erase the car numbers; remove the numbers from the car; this class has no numbers; my template has no number; the numbers come from the sim; iracing still shows a number; turn off the sim numbers; take the numbers off the car; who adds the numbers
First find out where the number comes from. There is no place to type a car number in Shokker. The two switches next to the User ID only choose the file name.
1. Sim-Stamped Number writes car_<ID>.tga. With Hide Car Numbers OFF in iRacing (the default) iRacing stamps the driver number and the sponsors on top of the paint when it loads the car. The number is not in the buyer's file, so no eraser, brush or layer can take it off.
2. Custom Number writes car_num_<ID>.tga and needs Hide Car Numbers ON in iRacing. Then iRacing stamps no number, and the only number on the car is the one painted on a layer (the Number Kit places it).
3. The number and sponsor stamp blocks in a template are guide layers. RENDER leaves them out of the paint, so a class with none has nothing to remove.
4. A number painted into one of the buyer's own layers can be removed: hide or delete that layer, or erase it on that layer.
Point to the number modes article, not to the eraser tools. After a change, RENDER and press Ctrl+R in iRacing.

## Does layer or zone opacity change the shine (spec), or only the colour?
[k4.opacity_vs_shine | pro | needs: none | ui: none]
Also asked as: does opacity change the shine; opacity vs spec; faded layer still shiny in the sim; does opacity fade the metallic; opacity and the spec map; how do I fade the shine too; lower opacity but still chrome
It depends which opacity.
1. Layer opacity (Layers panel) fades only the colour. The shine under that spot stays what the zone gives. The exception is a layer with a Layer Material (Material / Spec > Whole Car > Layer Materials...): its shine follows the layer, so 50 percent opacity mixes its material half and half with what is below, and a hidden layer has no shine.
2. Pattern Opacity (zone PATTERN section) fades the pattern colour, and the shine the pattern adds fades with it when the pattern spec amount is above 0.
3. A zone has no opacity slider. BASE STRENGTH fades the paint toward the original colours and leaves the shine alone. SPEC STRENGTH weakens the material (metal, roughness, clearcoat move toward neutral) and leaves the colour alone.
4. The Opacity slider in the selection bar next to Zoom only sets how strongly the zone overlay shows on screen. It changes nothing in the render.
5. The Material Brush honours Opacity (a 50 percent chrome stroke is half chrome). Car > Car-Space Fade... fades colour and shine together along the car.
To fade the shine too: lower SPEC STRENGTH, give the layer a Layer Material, or use Car-Space Fade.

## Why does my gradient look banded or stepped in iRacing, and how do I fix it?
[k4.gradient_banding | pro | needs: none | ui: none]
Also asked as: gradient banding; gradient looks stepped in the sim; gradient has stripes; stair step gradient; contour lines in a fade; dither a gradient; add noise to a gradient; gradient not smooth in game
Each colour channel has 256 levels (8 bits). A long, gentle fade, especially a dark low-contrast one, only passes through a few of them, so each level becomes a wide stripe. Shokker's preview is smaller and softer and hides it. iRacing turns the paint into a compressed texture and shows smaller copies (mips) at distance, which makes the steps stand out.
Fixes that exist in Shokker:
1. Make the fade with the Gradient tool Colours ramp (LAYER mode, G, then Colours). It adds a touch of dither (about half a colour step) so the stripe edges turn into fine grain. A plain two-colour drag without Colours has no dither.
2. Add colour stops. A zone BASE COLOR set to Custom gradient takes 2 to 10 stops. Give each stop a clearly different colour.
3. Push the colours further apart or shorten the fade so it crosses more levels over less distance.
4. Put a finish with micro-texture (flake, pearl or a fine-grain finish) on the same zone; the speckle hides the band edges.
There is no Add Noise filter. RENDER already dithers the spec map, so a smooth shine fade is covered. Check it in iRacing after RENDER and Ctrl+R.

## Can the AI just find or download the template (or any file) from the internet?
[k4.ai_cannot_download | pro | needs: none | ui: none]
Also asked as: can the ai download the template; can the helper get the template from the internet; can claude download a file; does the ai have internet access; can the ai open a link; search the web for the template
No. The AI helper, offline or online (Claude or ChatGPT through the connector), does not download anything from the web: no template, PSD, logo or picture. It cannot browse or open a link, and it has no download step. Nothing changes on the car.
What works:
1. The buyer downloads the template for their exact car from iRacing or a trusted source such as Trading Paints or their league, and opens it with Open Paint... next to Source Paint.
2. The car library already knows 31 checked iRacing templates. For any other car the helper asks once to see the parts (teach parts) and remembers them.
3. For a logo or picture: save it to the computer, then drop it on the Sponsor Kit box or add it as a layer.
Then the helper does the paint job on the open template in words.
