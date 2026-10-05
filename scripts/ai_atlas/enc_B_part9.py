"""Part IX - Spec Sculpt Lab (lane B). python scripts/ai_atlas/enc_B_part9.py (append-safe)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from enc_B_lib import *

D = 'spec_sculpt'
H = 'spec-sculpt.html'
W = 'SPB_WIKI.html#spec_sculpt'
ALLS = [i for i in inv_ids(domains=['spec_sculpt'], prefix='sculpt.') if 'EasyMode' not in i]   # hidden feature: never covered
used = set()


def S(*names, rx=None):
    """sculpt ids by short name ('sFrIgnition') or by regex on the id; remembers what was used."""
    out = []
    for i in ALLS:
        short = i[len('sculpt.'):]
        if short in names or (rx and re.search(rx, short)):
            out.append(i)
    used.update(out)
    return out


def C(*ks): return [{'do': 'control', 'id': k} for k in ks]


add(D, id='spec_sculpt.what_is_spec_sculpt', title='Why Spec Sculpt exists',
    summary='Spec Sculpt is a separate lab that builds a shine map for your finished paint, so a flat paint file can look like chrome, candy or carbon in the sim.',
    what='iRacing decides chrome versus matte versus wet candy from the spec map. Writing a good, safe one by hand is slow. Spec Sculpt reads your paint, builds a spec map that follows it, and installs it for your car. It has four steps: 1 Source (drop your paint as TGA, PNG, JPEG or PSD, 2048 by 2048 in Simple mode), 2 Look (choose a style), 3 Generate (a 2048 spec; the live preview is 512), and 4 Deploy (iRacing member ID, a car, and optional Live Link). A Simple and an Advanced switch hide or show the full control set. Reach it from the SPEC SCULPT button in the header, which opens the guided look library; the OPEN ORIGINAL SPEC SCULPT button there opens this lab in a new window with your paint carried over.',
    when=['You have finished paint and want a matching shine fast', 'You want chrome, candy or carbon without hand-editing'],
    how=['Click SPEC SCULPT in the top bar to open the guided look library, then click OPEN ORIGINAL SPEC SCULPT to open this lab.', 'Drop your paint file into Source.', 'Pick a look, then click Build spec + iRacing files (or BUILD + INSTALL IN iRACING in Simple).', 'Refresh the car in iRacing.'],
    controls=[{'label': 'Simple and Advanced', 'range': 'two modes', 'default': 'Simple', 'effect': 'Shows the short or the full control set.', 'inv': 'sculpt.uiModeAdvanced'}],
    tips=['Press the Take the guided tour button for a walkthrough.', 'Use Try an example car to see it work before using your own paint.'],
    pitfalls=['Simple mode needs exactly 2048 by 2048. It will not silently resize.', 'Judge the result in the sim, not in the flat preview.'],
    related=['spec_sculpt.three_modes', 'spec_sculpt.iron_safe_export', 'spec.what_is_spec_map'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=['spec.sculpt', 'wiki.spec_sculpt.why_it_matters_the_spec_map_in_30_second', 'wiki.spec_sculpt.2026_05_31_flagship_ux_elevation'] + S('fileInput', 'uiModeSimple', 'uiModeAdvanced', 'btnReopenGuide', 'btnPaintBooth', 'btnPaintLab', 'btnAnalyze', 'btnGenerate', 'btnGenerateSimple', 'btnTakeTour', 'btnTryExample', 'btnEmptyTour', 'tourBack', 'tourNext', 'tourSkip', 'btnCloseShortcutHelp', 'btnStartFresh', 'btnDismissRestored', 'strict2048', 'chkLivePreview', 'btnCancelLivePreview'),
    sources=[W, H + ':831-835', 'paint-booth-v2.html:1935'],
    aliases=['spec sculpt', 'spec sculpt lab', 'what is spec sculpt', 'sculpt my spec', 'spec generator', 'make a spec map', 'generate spec map', 'spec sculpt tour'])

add(D, id='spec_sculpt.three_modes', title='The three modes: Scratch, Catalog and Fusion',
    summary='Scratch builds looks from your paint with 120-plus styles, Catalog borrows real Paint Booth materials, and Fusion blends the two.',
    what='Scratch uses procedural, paint-aware styles. Catalog uses the real materials from the Paint Booth catalogue and their spec behaviour. Fusion mixes both with a weight slider and can split the mix per channel (metal, rough and coat). Fusion strategy has two settings: Balanced, a straight weighted average, and Showroom, where metal takes the shinier of the two at each pixel. Two special looks sit beside the modes: FRACTURE ignites any paint near-chrome with a woven motif, and CANDY DEPTH builds wet candy with flake.',
    when=['You want fast, expressive looks', 'You want to match a known Paint Booth finish', 'You want catalogue richness with a procedural edge'],
    how=['In step 2 Look, pick Scratch, Catalog or Fusion.', 'For Fusion, drag the mix weight and choose Balanced or Showroom.', 'For FRACTURE, tune Ignition, Angle gate, Trace strength (each default 100), Calm floor (default 30) and Decorrelation (default 0).', 'For CANDY DEPTH, tune Depth (default 100), Flake density (default 50), Flake size (default 10), Wetness (default 78) and Satin floor (default 42).'],
    controls=[{'label': 'Fusion strategy', 'range': 'Balanced (linear), Showroom', 'default': 'Balanced', 'effect': 'How catalogue and scratch specs are mixed.', 'inv': 'sculpt.fusionStrategy'}, {'label': 'Calm floor', 'range': '14-110', 'default': '30', 'effect': 'Keeps quiet areas of FRACTURE calm.', 'inv': 'sculpt.sFrCalm'}, {'label': 'Wetness', 'range': '0-100', 'default': '78', 'effect': 'How wet the candy looks.', 'inv': 'sculpt.sCdWet'}],
    tips=['Fusion at about half is a good first try.', 'Showroom changes only metal and keeps the larger source, so use Compare Looks to check it on your own paint.'],
    pitfalls=['Catalog looks from cultural finishes do not translate well to a spec map. Prefer material looks.'],
    related=['spec_sculpt.scratch_presets', 'spec_sculpt.paint_response', 'spec_sculpt.recipes'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=['wiki.spec_sculpt.the_three_modes'] + S('fusionStrategy', 'splitFusionChannels', rx=r'^(sFr|sCd|sFusion|below_if|procedural|real_paint|blend_catalog|ignite_any)') + S('catalogSearch', 'btnShuffleCatalog', 'catalogClear', 'mixStyleNotes', 'btnBlend', 'blendMix', 'blendA', 'blendB'),
    sources=[W, H + ':831-877', H + ':841-872'],
    aliases=['scratch catalog fusion', 'spec sculpt modes', 'fusion mode', 'showroom fusion', 'fracture ignition', 'candy depth'])

add(D, id='spec_sculpt.scratch_presets', title='Style presets and stacks',
    summary='The look library has 125 ready presets in six groups, and you can stack up to five with different weights.',
    what='Each preset points at a real Paint Booth finish. The groups are Candy and pearl (22), Holo and shift (22), Chrome and metal (21), Carbon and matte (20), Flake and sparkle (20), and Exotic and glow (20). The stack bar shows each layer and its share. Simple mode shows 12 go-to styles. Advanced shows 60 plus. Quick buttons like Wet + pearl and Matte duo build a stack in one click. Surprise picks a random look.',
    when=['You want a quick look', 'You want a custom blend of two or three looks'],
    how=['Open the look library.', 'Search or pick a group.', 'Click a style to add it. Click more to stack, up to five.', 'Adjust each weight.'],
    controls=[{'label': 'Preset search', 'range': 'text', 'default': '', 'effect': 'Filters the look library.', 'inv': 'sculpt.presetSearch'}],
    tips=['Pairs like Mirror Chrome plus a touch of Brushed Titanium look more real than one preset.'],
    pitfalls=['Five heavy presets can fight and flatten each other.'],
    related=['spec_sculpt.three_modes', 'spec_sculpt.power_features', 'spec_sculpt.recipes'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=['wiki.spec_sculpt.the_8_scratch_presets'] + S('presetSearch', 'presetQuickWet', 'presetQuickMatte', 'presetClear', 'btnSurprise', rx=r'^(surprise|chrome|candy|carbon_matte|holo_shift|flake)\.\d+$'),
    sources=['engine/spec_sculpt/presets.py:18', W],
    aliases=['spec sculpt presets', 'look library', 'style gallery', 'preset stack', 'stack looks'])

add(D, id='spec_sculpt.paint_response', title='Paint response: tie the spec to your colours',
    summary='Paint response makes the shine follow the colours in your paint, for example more shine on the bright areas or on one hue.',
    what='Where to emphasize spec offers Uniform (ignore colours), Bright or glossy-looking areas, Dark panels, Strong saturated colours and Muted, grey or white zones. Emphasis strength starts at 0. A Hue boost colour lets you pick a colour, with a Hue match width from 20 to 120 degrees (default 60) and a Hue boost strength from 0 to 100 starting at 0. There are also Color to Material and Tone to Material tools that map hues or tones to materials, and a Recolor source paint control with Hue, Saturation and Brightness (HSB) sliders.',
    when=['You want the red parts shinier than the blue parts', 'You want highlights in the bright areas of the livery'],
    how=['In step 2 Look, open Paint response.', 'Choose Where to emphasize spec.', 'Raise Emphasis strength.', 'Optionally pick a Hue boost colour and strength.'],
    controls=[{'label': 'Where to emphasize spec', 'range': 'Uniform, Bright, Dark, Saturated, Muted', 'default': 'Uniform', 'effect': 'Which paint areas get more spec.', 'inv': 'sculpt.paintEmphasis'}, {'label': 'Emphasis strength', 'range': '0-100', 'default': '0', 'effect': 'How much emphasis.', 'inv': 'sculpt.paintEmphasisStrength'}, {'label': 'Hue match width', 'range': '20-120 degrees', 'default': '60', 'effect': 'How wide the hue match is.', 'inv': 'sculpt.hueFocusWidth'}, {'label': 'Hue boost strength', 'range': '0-100', 'default': '0', 'effect': 'How much the chosen hue is boosted.', 'inv': 'sculpt.hueFocusStrength'}],
    tips=['Start with Bright at a low strength.'],
    pitfalls=['A narrow hue width can make a blotchy result.'],
    related=['spec_sculpt.generation_dna', 'spec_sculpt.power_features', 'spec_sculpt.three_modes'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=['wiki.spec_sculpt.paint_response_tie_spec_to_the_colors_in'] + S('paintEmphasis', 'paintEmphasisStrength', 'hueFocusColor', 'hueFocusWidth', 'hueFocusStrength', 'hsbH', 'hsbS', 'hsbV', 'btnHsbReset', 'hueMapBase', 'toneMapBase', 'btnHueMap', 'btnToneMap', 'btnApplyHueMap', 'btnApplyToneMap'),
    sources=[H + ':935-954', H + ':986-988', W],
    aliases=['paint response', 'emphasize spec', 'hue boost', 'color to material', 'tone to material', 'spec follows my paint'])

add(D, id='spec_sculpt.generation_dna', title='Generation DNA: detail, flatten and voids',
    summary='Generation DNA tunes the fine detail of the build: how busy, how flat in the interiors, how strong and how dark the voids can go.',
    what='Procedural detail intensity runs from 105 to 205 and defaults to 159 (shown as 1.59). Interior flatten runs from 0 to 100 and defaults to 38, which calms large flat areas. Spec strength runs from 0 to 200 and defaults to 100. The void caps set limits for empty areas: Void metallic cap 92 (range 40 to 130), Void roughness floor 158 (120 to 220) and Void clearcoat cap 44 (15 to 90). Channel trims for metal, roughness and coat run from 30 to 200 with a default of 100. Other settings are a Seed (default 9101), a Chromatic shift option, an auto-levels option and a Reset advanced to defaults button. Four DNA presets give quick starts: Catalog signature, Rich detail, Softer and Ink-heavy panels.',
    when=['The result is too busy or too plain', 'You want to calm large flat panels'],
    how=['Open Advanced and find Generation DNA.', 'Pick a DNA preset.', 'Fine tune Procedural detail intensity and Interior flatten.', 'Use the seed to re-roll while keeping all else.'],
    controls=[{'label': 'Procedural detail intensity', 'range': '105-205', 'default': '159', 'effect': 'How much fine detail is built.', 'inv': 'sculpt.sVmDetail'}, {'label': 'Interior flatten', 'range': '0-100', 'default': '38', 'effect': 'Calms big flat areas.', 'inv': 'sculpt.sInterior'}, {'label': 'Spec strength', 'range': '0-200', 'default': '100', 'effect': 'Overall strength.', 'inv': 'sculpt.sSpecStr'}, {'label': 'Void caps', 'range': 'metal cap 92, rough floor 158, coat cap 44', 'default': 'as listed', 'effect': 'Limits for empty areas.', 'inv': 'sculpt.sVoidM'}],
    tips=['Same seed gives the same result, so you can compare one change at a time.'],
    pitfalls=['High detail with a high flatten gives mixed results. Change one at a time.'],
    related=['spec_sculpt.paint_response', 'spec_sculpt.iron_safe_export', 'spec_sculpt.power_features'],
    actions=[],
    figures=[],
    covers=['wiki.spec_sculpt.generation_dna_the_viva_pipeline_exposed'] + S('sVmDetail', 'sInterior', 'sSpecStr', 'sVoidM', 'sVoidR', 'sVoidC', 'specGainM', 'specGainR', 'specGainCc', 'seed', 'btnRandSeed', 'chromatic', 'autoLevels', 'btnResetAdvancedMaterial', 'dnaPresetShipped', 'dnaPresetRich', 'dnaPresetSoft', 'dnaPresetInk', 'useCustomNum'),
    sources=[H + ':975', H + ':1007-1026', H + ':1048-1064', W],
    aliases=['generation dna', 'detail intensity', 'interior flatten', 'void caps', 'seed', 'procedural detail'])

add(D, id='spec_sculpt.smart_separate', title='Smart Separate: numbers, sponsors and paint',
    summary='Smart Separate finds the numbers, sponsors and logos in your paint so they stay crisp while the body gets the fancy shine.',
    what='In the current beta the flat-image Separate button and its two sliders are switched off, so the PSD layer picker is the working route. Auto-Separate, when on, detects the number, sponsors and paint areas on a flat image. Sensitivity (30 to 200, default 100; higher detects more as decals) and Number size (40 to 250, default 100; glyphs taller than this multiple of the livery median count as numbers) tune the detection. For PSD files the PSD layer picker lets you choose layers, with all, none and invert buttons. Protect edge and Feather soften the boundary. A Decal finish option sets how protected decals look: Matte (flat), Satin, Glossy, Wet or Carbon. Auto-assign gives each layer a material and Apply layer material applies it. Car intelligence makes this work by knowing where the parts of each car sit on the sheet.',
    when=['Your numbers look like chrome blobs', 'You want sponsor logos readable'],
    how=['Load a layered PSD paint.', 'Open the PSD layer picker and tick the layers to sculpt (all, none and invert help).', 'Set Protect edge, Feather and the Decal finish.', 'Build the map; unticked layers stay flat.'],
    controls=[{'label': 'Sensitivity', 'range': '30-200', 'default': '100', 'effect': 'Higher finds more decals.', 'inv': 'sculpt.sepSens'}, {'label': 'Number size', 'range': '40-250', 'default': '100', 'effect': 'Raise it if sponsor text is tagged as a number (flat-image detection is off in this beta).', 'inv': 'sculpt.sepNum'}, {'label': 'Protect material', 'range': 'Matte (flat), Satin, Glossy, Wet, Carbon', 'default': 'Matte (flat)', 'effect': 'Finish used for protected decals.', 'inv': 'sculpt.protectMaterial'}],
    tips=['Layered PSD files give the cleanest separation.'],
    pitfalls=['Flat images are not split automatically in this beta; use a layered PSD.'],
    related=['spec_sculpt.auto_protect', 'spec_sculpt.power_features', 'spec.material_override_remap_lighting'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=S('sepSens', 'sepNum', 'autoSepLive', 'protectMaterial', 'btnAutoSep', 'btnAutoLayerMat', 'btnApplyLayerMat', 'psdSelAll', 'psdSelNone', 'psdSelInvert', 'btnAutoZone', 'maskGrow', 'maskFeather'),
    sources=[H + ':1209-1218', 'SPB_WIKI.html#smart_separate'],
    aliases=['smart separate', 'auto separate', 'protect numbers', 'protect sponsors', 'decal finish', 'separate numbers from paint'])

add(D, id='spec_sculpt.auto_protect', title='Auto-protect',
    summary='Auto-protect keeps the numbers, logos and sponsors out of the heavy shine automatically, using the detection strength you set.',
    what='The Auto-detect decals box (off by default) finds numbers, sponsors and decals on a flat paint and keeps them flat while the body is sculpted. The detection strength slider runs from 50 to 180, shown as 0.5x to 1.8x, and defaults to 1.0x. Protect edge and Feather sliders set the soft edge. Protected areas keep a calm finish such as the Decal finish setting, so they stay readable at speed. You can preview what is protected before building.',
    when=['You do not want to separate things by hand', 'You want a safe default'],
    how=['Tick Auto-detect decals in the Look area.', 'Set the detection strength.', 'Click Preview and check what is shielded.'],
    controls=[{'label': 'Auto-detect decals', 'range': 'on or off', 'default': 'off', 'effect': 'Shields decals from the main effect.', 'inv': 'sculpt.autoProtect'}, {'label': 'Detection strength', 'range': '50-180 (0.5x-1.8x)', 'default': '100 (1.0x)', 'effect': 'How eagerly decals are found.', 'inv': 'sculpt.apStrength'}],
    tips=['Preview first, then build.'],
    pitfalls=['Too strong a setting can protect parts of the body paint.'],
    related=['spec_sculpt.smart_separate', 'spec_sculpt.diagnostics', 'spec_sculpt.iron_safe_export'],
    actions=[],
    figures=[],
    covers=S('autoProtect', 'apStrength', 'btnApPreview'),
    sources=[H + ':995-999', W],
    aliases=['auto protect', 'protect decals', 'protect logos', 'keep numbers readable'])

add(D, id='spec_sculpt.power_features', title='Power features',
    summary='Beyond the basics, the lab has saved looks, a community gallery, a variation maker, brushes, gradients, batch builds and more.',
    what='Auto-Sculpt reads your paint and recommends a look. My Looks saves a look, exports or imports a .shokklook file, or copies a share code. Shokk the World is a gallery of 20 looks. More like this makes 6 variations. Favorites and Recent remember what you used. A Drama slider turns the look up or down. Detail bake adds swirl marks, brushed, micro-scratch, hairline, road grime, orange peel, water spots, hammered or sandblast. Style Blend mixes A and B. Compare Looks holds 4 slots. Material Probe reads values. Batch Sculpt a Folder builds up to 64 files. Share Proof Card makes a PNG. Material Spotlight, Color to Material, Tone to Material, Region Brush (Chrome, Wet, Gloss, Satin, Matte, Carbon with brush size, Snap and symmetry), Material Gradient (horizontal, vertical, diagonal, radial), Match a Photo and Eyedropper complete the set. Shortcuts: G or Ctrl+Enter builds, V variations, D deploy, W Shokk the World, R surprise, Ctrl+Z and Ctrl+Shift+Z undo and redo.',
    when=['You want to explore, compare and save looks', 'You have many files to process'],
    how=['Open Advanced.', 'Use Auto-Sculpt for a starting recommendation.', 'Save a look you like with Save look.', 'Use Sculpt folder to build many at once.'],
    controls=[{'label': 'Drama', 'range': '0-100', 'default': '35', 'effect': 'Turns the look from subtle to wild.', 'inv': 'sculpt.dramaSlider'}, {'label': 'Detail amount', 'range': '0-100', 'default': '55', 'effect': 'How much baked detail is added.', 'inv': 'sculpt.detailAmount'}, {'label': 'Brush size', 'range': '6-64', 'default': '24', 'effect': 'Region Brush size.', 'inv': 'sculpt.brushSize'}],
    tips=['Compare Looks with four slots makes choosing easy.', 'Save every look you like, they are tiny files.'],
    pitfalls=['Batch builds of 64 files take a while. Start with a few.'],
    related=['spec_sculpt.scratch_presets', 'spec_sculpt.diagnostics', 'spec_sculpt.recipes'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=['wiki.spec_sculpt.power_features_2026_05_31'],
    sources=[W, H + ':1048-1064'],
    aliases=['spec sculpt power features', 'shokk the world', 'my looks', 'shokklook', 'compare looks', 'batch sculpt', 'region brush', 'material gradient', 'proof card', 'spec sculpt shortcuts'])

add(D, id='spec_sculpt.diagnostics', title='Diagnostics: seeing the channels',
    summary='The preview packs the spec channels into false colour, the channel tiles are tinted, and a Material readout tells you what the pixel under the pointer is.',
    what='The composite preview shows metal in red, roughness in green and clearcoat in blue, so you can see materials as colour. Tiles for each channel are tinted to match. The Material readout and the Material Probe give numbers at a point. A loupe magnifies details. Use diagnostics to see why a look is flat or too busy.',
    when=['A build looks wrong and you want to find out why', 'You want to check numbers on a point'],
    how=['Build a look.', 'Look at the composite preview and the R, G and B tiles.', 'Hover with the loupe on.', 'Use Material Probe for exact numbers.'],
    controls=[{'label': 'Loupe', 'range': 'on or off', 'default': 'on', 'effect': 'Magnifies the preview.', 'inv': 'sculpt.loupeOn'}],
    tips=['Compare the false colour with the spec colour reading table in this guide.'],
    pitfalls=['False colour is for reading, it does not match how the car looks.'],
    related=['spec.reading_by_colour', 'spec.inspector', 'spec_sculpt.power_features'],
    actions=[],
    figures=['r13_spec_channel_views'],
    covers=['wiki.spec_sculpt.diagnostics_in_the_preview'] + S('loupeOn', 'btnClearProbes', 'eyedropMat', 'btnEyedropper', 'btnEyedropApply', 'btnSpotlight'),
    sources=[W],
    aliases=['spec sculpt diagnostics', 'false colour preview', 'material probe', 'loupe'])

add(D, id='spec_sculpt.iron_safe_export', title='Iron rules on export',
    summary='Every Spec Sculpt export is checked against the iron rules, so it cannot produce an illegal spec map.',
    what='Before a file is written the lab enforces the same three rules as the Paint Booth: clearcoat kept at 16 or more, roughness at 15 or more unless the metal is 240 or more, and alpha left at full lighting. You never need to check this by hand. The strict 2048 check refuses the wrong size rather than resizing quietly. Deploy writes to your iRacing folder for the member ID and car you pick, and Live Link can refresh it. The Deploy-only button redeploys the last job without rebuilding.',
    when=['You worry a custom look will break the sim', 'You want to install the result'],
    how=['Enter your iRacing member ID.', 'Pick the car.', 'Click Build, then Deploy, or tick Deploy now.', 'Refresh the car in iRacing.'],
    controls=[{'label': 'iRacing member ID', 'range': 'number', 'default': '', 'effect': 'Which folder the files go to.', 'inv': 'sculpt.iracingId'}, {'label': 'Live Link', 'range': 'on or off', 'default': 'off', 'effect': 'Keeps iRacing updated while you work.', 'inv': 'sculpt.liveLink'}],
    tips=['Preview does not need a member ID. Only deploy does.'],
    pitfalls=['A stale compiled file in iRacing can hide your new spec until it rebuilds.'],
    related=['spec.iron_rules', 'spec.colour_space_and_files', 'spec_sculpt.what_is_spec_sculpt'],
    actions=[],
    figures=['g18_iron_rules'],
    covers=['wiki.spec_sculpt.iron_rules_always_enforced_on_export'] + S('iracingId', 'outputDir', 'deployCar', 'deployCarSearch', 'liveLink', 'deployNow', 'btnDeployOnly', 'btnOpenFolder', 'btnPickFolder', 'fbPath', 'fbClose', 'fbUse'),
    sources=[W, 'engine/spec_sculpt/presets.py:18', 'shokker_engine_v2.py:301'],
    aliases=['export iron safe', 'deploy to iracing', 'iracing member id', 'install spec in iracing', 'spec sculpt deploy'])

add(D, id='spec_sculpt.recipes', title='Recipes: five looks to try',
    summary='Five starting points that work well: wet candy, mirror chrome, carbon and matte, holo shift and flake.',
    what='Each is a one-click stack in the look library. Candy: pick the Candy look and raise Wetness. Chrome: pick Chrome, then use Auto-protect so numbers stay clear. Carbon and Matte: matte body with carbon accents and a quiet Interior flatten. Holo and Shift: fine detail with Paint response set to Saturated. Flake: set Flake density and Flake size, then add a touch of Satin floor. Save the result as a look and compare four at a time.',
    when=['You do not know where to start', 'You want a safe first result'],
    how=['Click a quick look button.', 'Build a preview.', 'Adjust Drama.', 'Save it and compare with another.'],
    controls=[],
    tips=['Make small changes between builds, and keep the seed fixed.'],
    pitfalls=['Strong drama on every look makes them all look alike.'],
    related=['spec_sculpt.three_modes', 'spec_sculpt.power_features', 'spec_sculpt.scratch_presets'],
    actions=[],
    figures=['r14_sculpt_before_after'],
    covers=S('btnFavCurrent', 'btnSaveRecipe', 'recipeName', 'btnSaveLook', 'btnExportLook', 'btnImportLook', 'btnCopyCode', 'btnApplyCode', 'lookName', 'lookCodeIn', 'lookCodeOut', 'importLookFile', 'btnAddCompare', 'btnUndo', 'btnRedo', 'btnProofCard', 'btnProofDownload', 'btnAutoSculpt', 'btnSmartVariant', 'btnShokkWorld', 'btnReroll', 'btnMoreLikeThis', 'btnRunBatchFolder', 'batchFolder', 'batchOutDir', 'refMatchFile', 'btnRefPick'),
    sources=[W, H + ':860-872'],
    aliases=['spec sculpt recipes', 'sculpt starting points', 'how to make candy spec', 'how to make chrome spec'])

# --- remainder: every other sculpt.* control goes to the power-features article's coverage via an extra article
rest = [i for i in ALLS if i not in used]
add(D, id='spec_sculpt.controls_reference', title='Spec Sculpt: the rest of the controls',
    summary='A short guide to the remaining brushes, gradient buttons, detail bakes and file pickers in the lab.',
    what='Region Brush paints a material on an area with Chrome, Wet, Gloss, Satin, Matte or Carbon, with symmetry Off, Vertical, Horizontal or Quad, plus its own Undo, Clear and Apply brush buttons. Material Gradient fades between materials horizontally, vertically, diagonally or radially. Detail bake adds None, Swirl marks, Brushed, Micro-scratch, Hairline, Road grime, Orange peel, Water spots, Hammered or Sandblast. Zone buttons show Chrome zones, Wet and gloss, Matte zones and Show car. Copy buttons copy values from the readout.',
    when=['You want to paint a material by hand', 'You want to add a worn or textured detail'],
    how=['Open Advanced.', 'Choose Region Brush, pick a material and size, and paint.', 'Click Apply brush.', 'Use Undo to step back.'],
    controls=[{'label': 'Mask grow and feather', 'range': 'grow -20 to 20, feather 0 to 12', 'default': 'grow 0, feather 2', 'effect': 'Grows or softens the protected edge.', 'inv': 'sculpt.maskFeather'}, {'label': 'Brush Snap tolerance', 'range': '8-60', 'default': '28', 'effect': 'How different a neighbouring colour must be before the snap stops.', 'inv': 'sculpt.brushSnapTol'}],
    tips=['Use symmetry for cars with matching sides.'],
    pitfalls=['A big brush with Snap off covers sponsor areas.'],
    related=['spec_sculpt.power_features', 'spec_sculpt.smart_separate', 'spec_sculpt.recipes'],
    actions=[],
    figures=[],
    covers=rest,
    sources=[W, H + ':1048-1064'],
    aliases=['material gradient tool', 'detail bake', 'brush symmetry'])
used.update(rest)

# --- spec tools menu (top bar of the main app): remaining buttons
spec_tools = [i for i in inv_ids(domains=['spec_sculpt'], prefix='pro.spec_tools.')]
add(D, id='spec_sculpt.spec_tools_menu', title='SPEC TOOLS in the main app',
    summary='The SPEC TOOLS menu opens four helpers: the Material Sampler, the Lighting Mask, the Material Range Remapper and the Decal Rescue Kit.',
    what='Material Sampler reads and copies spec values from any spot. Lighting Mask sets alpha with Use Source Alpha, Full Lighting, Reduced Lighting or Kill Lighting. Material Range Remapper has preset buttons: Original, Metallic Texture, Printed Vinyl, Matte Texture and Gloss Texture, plus Apply Remap and Restore Original. Decal Rescue Kit has Flat Vinyl, Satin Decal and Gloss Decal for decals that arrive in the wrong finish. The full lab is a separate page: SPEC SCULPT opens the guided look library, and its OPEN ORIGINAL SPEC SCULPT button opens the lab.',
    when=['Decals look glassy', 'You want to adjust an existing spec file'],
    how=['Click SPEC TOOLS in the top bar.', 'Pick a tool.', 'Choose a preset and click Apply.', 'Use Restore Original to go back.'],
    controls=[{'label': 'Apply Remap', 'range': 'one click', 'default': '', 'effect': 'Applies the chosen range changes.', 'inv': 'pro.spec_tools.remap_apply'}],
    tips=['Try Flat Vinyl first for glassy decals.'],
    pitfalls=['Remap changes the whole zone. Use Restore Original if unsure.'],
    related=['spec.material_override_remap_lighting', 'spec.inspector', 'spec_sculpt.what_is_spec_sculpt'],
    actions=[],
    figures=['r13_spec_channel_views'],
    covers=spec_tools + inv_ids(domains=['spec_sculpt'], prefix='btn') + ['specMaterialSelectTolerance', 'specMaterialSampleSize'],
    sources=['paint-booth-v2.html:2391', 'paint-booth-v2.html:4105', 'paint-booth-v2.html:4148', 'paint-booth-v2.html:4196'],
    aliases=['spec tools menu', 'decal rescue kit', 'material range remapper'])

assemble(D)
