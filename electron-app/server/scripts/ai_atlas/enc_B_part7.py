"""Part VII - Patterns (lane B). python scripts/ai_atlas/enc_B_part7.py (append-safe)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'patterns'
Z = 'paint-booth-2-state-zones.js'
ATLAS = 'js/spb-ai-atlas-data.js:2'
def P(*ks): return [{'do': 'pattern', 'id': k} for k in ks]
def C(*ks): return [{'do': 'control', 'id': k} for k in ks]

add(D, id='patterns.what_is_a_pattern', title='What a pattern is',
    summary='A pattern is a shape that tiles across a zone on top of the base finish, such as carbon, camo, flames or a checkerboard. The catalogue has 319 of them.',
    what='The base finish gives the material. A pattern adds visible shape on top: weave, scales, stripes, geometry, icons from an era. Each zone can have a primary pattern and more layers. A pattern changes the paint, and if you raise its spec amount it also changes the shine. Patterns are different from spec patterns, which only change the shine and never the colour.',
    when=['You want carbon, camo, scales or a geometric look', 'You want a retro motif'],
    how=['Click a zone card and open the PATTERN section.', 'Click Pattern 1 on this Layer to open the picker.', 'Pick a pattern. Click None to remove it.', 'Tune Scale, Rotate and Opacity.'],
    controls=[{'label': 'Pattern 1', 'range': 'any of the catalogue patterns or None', 'default': 'None', 'effect': 'Chooses the pattern.', 'inv': 'zone.pattern'}],
    tips=['Pattern first, then colour. Many patterns are about shape and take any colour you give the zone.', 'Use a spec pattern when you want texture without visible shapes.'],
    pitfalls=['A big pattern at default scale looks huge on a whole car.'],
    related=['patterns.nine_groups', 'patterns.scale_rotation_opacity', 'patterns.paint_mode'],
    actions=P('carbon_fiber', 'camo', 'art_deco') + C('zone.pattern'),
    figures=['r06_pattern_scale'],
    covers=['catalog.patterns', 'zone.pattern', 'zone.section_pattern', 'wiki.finish_doctrine.pattern_base_finish_quality'],
    sources=[Z + ':2258-2335', ATLAS, 'SPB_WIKI.html#finish_doctrine'],
    aliases=['what is a pattern', 'patterns', 'add a pattern', 'pattern picker', 'carbon pattern', 'pattern list', 'how many patterns'])

add(D, id='patterns.nine_groups', title='The nine pattern groups',
    summary='Patterns are sorted into nine groups: abstract and fractal, tech and carbon, geometry and deco, nature, cultural, 50s to 80s, 90s and surf, reactive accents, and patriotic.',
    what='Abstract, Fractal and Paradigm has 44 (fractals, biomechanical). Tech, Carbon and Industrial has 46 (carbon, kevlar, nanoweave). Geometry, Deco and Op-Art has 44 (art deco, celtic knot, chevron, greek key). Nature, Animals and Weather has 36 (camo, crocodile, feather, giraffe). Cultural, World and Dark has 39 (aztec, dragon scale). Decades 50s to 80s has 44. 90s, Skate and Surf has 36. Reactive and Surface Accents has 18 (shimmer effects). Let Freedom Ring has 10. Patterns not placed in a group are removed from the picker.',
    when=['You are looking for a type of shape', 'You want an era pattern'],
    how=['Open the pattern picker.', 'Choose a group tab or search.', 'Preview a pattern on the zone.'],
    controls=[],
    tips=['Decades patterns carry icons of the era, such as diner checkerboards and jukebox arcs.'],
    pitfalls=['Reactive accents are subtle and need a base with some shine to show.'],
    related=['patterns.what_is_a_pattern', 'patterns.choosing_at_car_scale', 'patterns.layers_and_stacking'],
    actions=P('fractal', 'kevlar_weave', 'greek_key', 'dragon_scale', 'celtic_knot'),
    figures=['r06_pattern_scale'],
    covers=inv_ids(kinds=['pattern_group'], domains=['patterns']),
    sources=[ATLAS, Z + ':2258'],
    aliases=['pattern groups', 'pattern categories', 'types of patterns', 'decades patterns', 'camo patterns', 'carbon fiber patterns'])

add(D, id='patterns.scale_rotation_opacity', title='Pattern scale, rotation, opacity and strength',
    summary='Four sliders shape a pattern: SCALE (size), ROTATE, OPACITY (how visible) and STRENGTH (how hard it hits paint).',
    what='SCALE runs from 0.10 to 4.00 times. Smaller means more repeats. ROTATE runs from 0 to 359 degrees. OPACITY runs from 0 to 100 percent in steps of 5: 0 is invisible, 100 is full. STRENGTH also runs 0 to 100 percent in steps of 5 and sets the paint strength of the pattern; the spec amount is separate. A pattern hue and saturation slider recolours only the pattern art.',
    when=['The pattern looks huge', 'The pattern is too loud', 'The weave runs the wrong way'],
    how=['Open the PATTERN section of the zone.', 'Drag Scale below 1.00 until the repeats look fine on the car.', 'Use Opacity to dial it back.', 'Use Rotate to turn it.'],
    controls=[{'label': 'Scale', 'range': '0.10x-4x', 'default': '1.00x', 'effect': 'Pattern size.', 'inv': 'zone.pattern_scale'}, {'label': 'Rotate', 'range': '0-359', 'default': '0', 'effect': 'Turns the pattern.', 'inv': 'zone.pattern_rotation'}, {'label': 'Opacity', 'range': '0-100%, step 5', 'default': '100%', 'effect': 'Visibility.', 'inv': 'zone.pattern_opacity'}, {'label': 'Strength', 'range': '0-100%, step 5', 'default': '100%', 'effect': 'Paint strength of the pattern.', 'inv': 'zone.pattern_strength'}, {'label': 'Pattern hue', 'range': 'hue -180 to 180, saturation -100 to 100', 'default': '0', 'effect': 'Recolours the pattern art.', 'inv': 'zone.pattern_hue'}],
    tips=['Fine detail of 8 to 32 pixels on the 2048 canvas looks rich. Large repeats look like smears.', 'Opacity is the first slider to try when a pattern is too much.'],
    pitfalls=['Opacity 0 hides the pattern completely, not just softens it.'],
    related=['patterns.paint_mode', 'patterns.choosing_at_car_scale', 'finishes.base_scale_rotation'],
    actions=C('zone.pattern_scale', 'zone.pattern_rotation', 'zone.pattern_opacity', 'zone.pattern_strength'),
    figures=['r06_pattern_scale', 'r07_pattern_rotation', 'r08_pattern_opacity_strength'],
    covers=['zone.pattern_scale', 'zone.pattern_rotation', 'zone.pattern_opacity', 'zone.pattern_strength', 'zone.pattern_hue'],
    sources=[Z + ':2285-2335'],
    aliases=['pattern scale', 'pattern size', 'pattern too big', 'pattern rotation', 'pattern opacity', 'pattern strength', 'rotate pattern'])

add(D, id='patterns.placement', title='Pattern placement',
    summary='Choose how a pattern sits: tiled across the whole canvas, fitted into the zone, or dragged by hand on the template.',
    what='Full Canvas (centred) tiles the pattern across the sheet. Fit to Zone puts one copy inside the drawn zone box, and then the template offsets are locked. Edit on Template lets you drag the pattern on the template, with a strip for quick rotate and flip. The Advanced Pattern Control Panel adds Position X and Y sliders (0 to 100 in steps of 5, 50 is centre), Flip H and Flip V, and a Strength Map: a brush that paints where the pattern is strong or weak, with fill white, fill black, top to bottom and left to right helpers.',
    when=['You want a logo-like single motif in an area', 'You want to slide a pattern or mirror it', 'You want the pattern strong in one place and faint in another'],
    how=['Open PATTERN and choose a placement button.', 'For fine control open the Advanced Pattern Control Panel.', 'Use Flip H or Flip V to mirror.', 'Use Strength Map to paint where it shows.'],
    controls=[{'label': 'Placement', 'range': 'Full Canvas, Fit to Zone, Edit on Template', 'default': 'Full Canvas', 'effect': 'How the pattern is placed.', 'inv': 'zone.pattern_placement'}, {'label': 'Position X and Y', 'range': '0-100, step 5', 'default': '50', 'effect': 'Slides the pattern.', 'inv': 'zone.pattern_position'}, {'label': 'Fit into area', 'range': 'on or off', 'default': 'off', 'effect': 'Fits one copy into the drawn box.', 'inv': 'zone.fit_into_area'}],
    tips=['Fit to Zone only fits base and pattern, not spec overlays.'],
    pitfalls=['Position sliders are locked while Fit to Zone is active.'],
    related=['patterns.scale_rotation_opacity', 'patterns.layers_and_stacking', 'patterns.what_is_a_pattern'],
    actions=C('zone.pattern_placement', 'zone.pattern_position', 'zone.fit_into_area'),
    figures=['r07_pattern_rotation'],
    covers=['zone.pattern_placement', 'zone.pattern_position', 'zone.fit_into_area'],
    sources=[Z + ':9478-9492', Z + ':2305-2335'],
    aliases=['pattern placement', 'fit to zone', 'edit on template', 'move pattern', 'flip pattern', 'strength map', 'pattern position'])

add(D, id='patterns.layers_and_stacking', title='Pattern layers and stacking',
    summary='A zone holds up to five patterns: Pattern 1 plus four more layers added with + Add Layer.',
    what='Each layer has its own pattern, scale, rotation and strength. Paint mode, Overlay or Blend, applies to all pattern layers. Stacking lets you put a fine weave under a bold shape, or a stripe over camo. Order matters: later layers sit on top. Keep layers different in scale so they read as separate ideas.',
    when=['You want carbon with stripes on top', 'You want camo with a fine overlay'],
    how=['Pick Pattern 1.', 'Click + Add Layer and pick the next pattern.', 'Set a different scale on each layer.', 'Use Remove on any layer to take it out.'],
    controls=[{'label': 'Add Layer', 'range': 'up to 5 patterns per zone', 'default': 'none', 'effect': 'Adds another pattern layer.', 'inv': 'zone.add_pattern_layer'}],
    tips=['Two layers at very different scales usually look best.'],
    pitfalls=['Five busy layers turn into noise.', 'After five patterns a toast tells you the maximum.'],
    related=['patterns.paint_mode', 'spec.how_layers_combine', 'patterns.placement'],
    actions=C('zone.add_pattern_layer'),
    figures=['r06_pattern_scale'],
    covers=['zone.add_pattern_layer'],
    sources=[Z + ':5099-5100', Z + ':12114', Z + ':2258-2335'],
    aliases=['pattern layers', 'stack patterns', 'add layer', 'multiple patterns', 'two patterns on one zone', 'max patterns'])

add(D, id='patterns.paint_mode', title='Pattern paint mode: Overlay or Blend',
    summary='Overlay covers the paint with the pattern own colours. Blend keeps your paint colour and lets the pattern change only the texture and tone.',
    what='The Paint mode dropdown applies to every pattern layer in the zone. Overlay shows the full pattern with its own colours and hides the base colour. Blend keeps the paint colour. The pattern spec amount starts at 0 on purpose, so your base shine stays. Raise it to reveal the pattern own metal, roughness and coat.',
    when=['Your base colour vanished under a pattern', 'You want a pattern in your own colour'],
    how=['Open PATTERN.', 'Open the Paint mode dropdown.', 'Choose Blend to keep your paint colour.', 'Raise Spec amount if you want the pattern to affect the shine.'],
    controls=[{'label': 'Paint mode', 'range': 'Overlay - full pattern, Blend - keep paint color', 'default': 'Overlay', 'effect': 'Whether the pattern hides the base colour.', 'inv': 'zone.pattern_paint_mode'}, {'label': 'Spec amount', 'range': '0-100%', 'default': '0%', 'effect': 'Lets the pattern carry its own shine.', 'inv': 'zone.pattern_spec_amount'}],
    tips=['Blend with a solid colour gives clean single-colour carbon.'],
    pitfalls=['Overlay with a coloured pattern hides your base colour.'],
    related=['patterns.scale_rotation_opacity', 'spec.how_layers_combine', 'finishes.colour_source_modes'],
    actions=C('zone.pattern_paint_mode', 'zone.pattern_spec_amount'),
    figures=['r08_pattern_opacity_strength'],
    covers=['zone.pattern_paint_mode', 'zone.pattern_spec_amount'],
    sources=[Z + ':2258-2335'],
    aliases=['pattern paint mode', 'overlay vs blend', 'pattern hides my colour', 'pattern covers my paint', 'blend mode pattern', 'keep paint colour'])

add(D, id='patterns.choosing_at_car_scale', title='Choosing patterns at car scale',
    summary='The canvas covers a whole car, so a pattern that looks fine in a thumbnail is big on the car. Go smaller than 1.00 and check the car.',
    what='The paint file is 2048 by 2048 pixels for the entire car laid flat. A feature of 64 pixels is the size of a side mirror. Fine detail of 8 to 32 pixels reads as premium texture. Sharp, busy, high-frequency patterns look best, while soft blobs look like smeared paint. Patterns with strong shape need space around them for numbers and sponsors.',
    when=['A pattern looks wrong on the car', 'You are picking between two patterns'],
    how=['Apply the pattern.', 'Drag Scale to 0.50 or lower.', 'Look at the car preview, not the template.', 'Lower Opacity over number and sponsor areas.'],
    controls=[{'label': 'Scale', 'range': '0.10x-4x', 'default': '1.00x', 'effect': 'Pattern size.', 'inv': 'zone.pattern_scale'}],
    tips=['Compare scale 1.00, 0.50 and 0.25 side by side.'],
    pitfalls=['Judging on the thumbnail is the most common mistake.'],
    related=['patterns.scale_rotation_opacity', 'patterns.nine_groups', 'spec.paint_spec_marriage'],
    actions=P('carbon_fiber', 'chainlink', 'diamond_plate'),
    figures=['g19_scale_on_car', 'r06_pattern_scale'],
    covers=['wiki.finish_doctrine.2048_car_canvas_scale_law'],
    sources=['SPB_WIKI.html#finish_doctrine', Z + ':2285-2295'],
    aliases=['pattern too large', 'whole car scale', 'car scale', '2048 canvas', 'make pattern finer', 'pattern looks huge'])

assemble(D)
