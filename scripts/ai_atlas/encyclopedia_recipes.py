# -*- coding: utf-8 -*-
"""encyclopedia_recipes.py - the hand-written part of the offline encyclopedia (2026-10-04).
Data only; build_encyclopedia.py compiles these recipes + the shipped sources into js/spb-encyclopedia-data.js.
AI-as-compiler: every entry is a one-liner recipe here; the finish choices, colours, parts, shelves, tags,
slang and livery schemes are DERIVED from the shipped data (never typed).

  I(id, title, aliases, summary, details, links, related)               kind=info   (an explanation + links)
  FL(id, title, aliases, summary, details, steps, links, related)       kind=flow   (a guided flow; step = 'type|text')
  A(id, title, aliases, summary, **kw)                                   kind=action (choices ranked from the catalogue) or
                                                                          kind=flow when kw kind='flow' (look with sub-choices)
Aliases: '|' separated, lowercase. Plurals / color-colour / spaced forms are added by the generator.
Link targets: support:<faq/err id>  control:<UI control id>  help:<self-help topic id>  doc:GETTING_STARTED.html#<heading>
Step types: ask_target ask_colour ask_look ask_part ask_choice open_control tell confirm
"""
INFO, FLOW, ACT = [], [], []

def I(id, title, aliases, summary, details=(), links=(), related=()):
    INFO.append(dict(id=id, title=title, al=aliases, sum=summary, det=list(details), links=list(links), rel=list(related)))

def FL(id, title, aliases, summary, details=(), steps=(), links=(), related=()):
    FLOW.append(dict(id=id, title=title, al=aliases, sum=summary, det=list(details), steps=list(steps), links=list(links), rel=list(related)))

def A(id, title, aliases, summary, **kw):
    d = dict(id=id, title=title, al=aliases, sum=summary, det=[], tags=[], name='', words='', shine=None, metal=None, own=None,
             n=5, pats=[], fin=[], links=[], rel=[], kind='action', steps=None)
    d.update(kw); ACT.append(d)

# =====================================================================================================  INFO
I('user_id', 'User ID', 'user id|userid|user number|customer id|customerid|customer number|iracing id|iracing customer id|iracing customer number|iracing user id|member id|my id|cust id',
  'Your User ID is your iRacing Customer ID, 4 to 7 digits. It is NOT your car number.',
  ['Find it in iRacing: helmet icon (top right), then Profile.', 'iRacing only loads paint files that carry your own ID in the file name.', 'A wrong ID means the paint never shows in the sim.'],
  ['support:customer_id', 'control:iracingId', 'doc:GETTING_STARTED.html#Setting up iRacing'], ['number_modes', 'car_folder', 'not_showing'])
I('number_modes', 'Custom Number vs Sim-Stamped', 'custom number|custom numbers|sim stamped|sim stamped number|simstamped|sim stamp|hide car numbers|hide numbers|car num|carnum|number mode|number modes|number setting|number switch|stamped number|numbers twice|double number|two numbers|wrong number',
  'Custom Number saves your paint as car_num_<ID>; Sim-Stamped saves it as car_<ID> and iRacing stamps your number on.',
  ['Custom Number needs iRacing Settings > Graphics > Hide Car Numbers ON.', 'Sim-Stamped works with Hide Car Numbers OFF (the default).', 'The Shokker switch and the iRacing setting must agree or iRacing shows plain paint-shop colours.', 'Do not also paint a number on the template in Sim-Stamped mode.'],
  ['support:number_modes', 'control:useCustomNumberCheckbox', 'control:useSimStampedCheckbox'], ['number', 'user_id', 'not_showing'])
I('iracing', 'iRacing', 'iracing|i racing|the sim|iracing sim|sim|iracing paint|iracing paints|paint shop|paintshop',
  'iRacing is the sim your paint goes into. Shokker writes the paint and a shine file into your iRacing paint folder.',
  ['Set your User ID and car folder once, then press RENDER.', 'In iRacing press Alt+Tab, then Ctrl+R to reload the car textures.'],
  ['support:how_export', 'help:iracing', 'doc:GETTING_STARTED.html#Setting up iRacing'], ['reload', 'car_folder', 'user_id', 'not_showing'])
I('reload', 'Reload in iRacing (Ctrl+R)', 'reload|ctrl r|control r|ctrl+r|reload textures|reload car textures|reload paint|refresh in iracing|alt tab|restart iracing|see changes in iracing',
  'After a render, press Ctrl+R in iRacing to reload the car textures; the car flashes white and shows the new paint.',
  ['If the shine still looks old, see the .mip file note.'],
  ['support:reload', 'support:mip'], ['mip', 'not_showing'])
I('car_folder', 'iRacing Car Folder', 'car folder|iracing car folder|paint folder|iracing paint folder|car paint folder|documents iracing paint|output folder|folder',
  'The Car Folder is the iRacing paint folder for ONE car (a folder, not a file). Set it once and every render lands there.',
  ['Run the car once in iRacing so the folder exists, then pick it in the dropdown.', 'The folder name uses a space where the car path has a slash (e.g. stockcars chevyss).'],
  ['support:where_files', 'control:outputDir', 'control:carPickBtn', 'doc:GETTING_STARTED.html#Setting up iRacing'], ['where_files', 'user_id'])
I('where_files', 'Where my files go', 'where do my files go|where did my files go|where did it go|where are my files|where is my paint|where are my renders|where did it save|where does it save|show my files|saved files|my files|lost file|lost files|lost my paint|find my paint|find my render|old render|earlier render',
  'Every render copies the paint and the spec file into your iRacing Car Folder. Shokker keeps only its two newest renders itself.',
  ['The green Saved bar has a Show my files button.', 'Use Save to keep for a render you want to keep.'],
  ['support:where_files', 'help:render_history', 'support:job_gone'], ['car_folder', 'render'])
I('not_showing', 'It does not show in iRacing', 'not showing|not showing up|doesnt show|does not show|doesnt show up|does not show up|wont show|will not show|wont show up|isnt showing|is not showing|didnt show up|not appearing|doesnt appear|not loading|doesnt load|wont load|plain colours|white car|default paint|looks different in iracing|looks different in the sim|wrong in iracing|paint missing|missing paint',
  'When the paint does not show in iRacing it is almost always the User ID, the number setting, the car folder or a missing Ctrl+R.',
  ['Check the ID, then the number mode against Hide Car Numbers, then the folder, then press Ctrl+R in the sim.', 'Say "it does not show up in iRacing" and the helper checks all of these for you.'],
  ['support:how_export', 'support:number_modes', 'support:customer_id', 'support:where_files', 'support:reload'], ['user_id', 'number_modes', 'car_folder', 'reload'])
I('spec_map', 'Spec map', 'spec map|spec file|car spec|car_spec|specular|spec channels|spec channel|channels|mrcc|metal rough clearcoat|red channel|green channel|blue channel|alpha channel spec',
  'The spec file tells iRacing how shiny each part is: red is metal, green is roughness, blue is clearcoat.',
  ['Red 255 = full metal; green 0 = mirror smooth, 255 = rough; blue 16 = maximum gloss, 255 = dull, 0-15 = no clearcoat.', 'Without it iRacing keeps the car\'s normal material: colours show, shine and chrome do not.'],
  ['support:spec_what', 'help:spec_view'], ['spec', 'roughness', 'clearcoat_channel', 'metal_channel'])
I('metal_channel', 'Metallic (red channel)', 'metallic channel|metalness|red channel metal|how metal',
  'In the spec file the red channel is how metal a part is: 255 is solid metal, 0 is paint or plastic.',
  ['A chrome part needs near-white paint underneath: iRacing multiplies the paint colour by the metal.'], ['support:spec_what', 'support:chrome_dark'], ['spec_map', 'roughness'])
I('roughness', 'Roughness (green channel)', 'roughness|rough|smoothness|smooth|how rough|green channel roughness',
  'In the spec file the green channel is roughness: 0 is a perfect mirror, 255 is rough and dull.',
  ['Low roughness plus high metal is chrome; high roughness is matte or brushed.'], ['support:spec_what', 'control:zone_spec_channel_shift'], ['spec_map', 'metal_channel'])
I('clearcoat_channel', 'Clearcoat (blue channel)', 'clearcoat channel|cc channel|blue channel clearcoat|how much clearcoat|clearcoat amount',
  'In the spec file the blue channel is the clearcoat: 16 is the shiniest, 255 is dull and 0-15 means none.',
  ['A clearcoat of 255 will make even a chrome part look dull.'], ['support:spec_what', 'control:zone_cc_quality'], ['spec_map'])
I('mip', 'The .mip file', 'mip|dot mip|mip file|mip files|car_spec mip|mipmap|mip map',
  'iRacing builds a .mip file from your spec the first time it loads it. After a new render Ctrl+R is normally enough.',
  ['If the shine looks like an old version, move car_spec_<ID>.mip out of the folder and reload.', 'Trading Paints takes the spec only as .mip.'],
  ['support:mip', 'support:trading_paints'], ['spec_map', 'trading_paints'])
I('trading_paints', 'Trading Paints', 'trading paints|trading paint|tradingpaints|tp|downloader|share my paint|share paint|other drivers see|others see my paint|friends see my paint|upload paint',
  'Trading Paints is how other drivers get your files, because iRacing never shares textures between drivers.',
  ['Upload the car_num_<ID> or car_<ID> file Shokker rendered, never the project file.', 'For the shine upload the .mip iRacing makes after you drive the car once.'],
  ['support:trading_paints', 'support:others_see', 'support:mip'], ['mip', 'where_files'])
I('paint_size', 'Paint size (2048)', 'dpi|2048|1024|4096|paint size|texture size|resolution|canvas size|wrong size|resize|2048 paint textures|dimensions',
  'iRacing paints must be exactly 2048 x 2048 (or 1024 x 1024). Any other size is ignored and plain colours show.',
  ['Open the car\'s own template at its normal size and never resize the canvas.', 'If everything is black, check iRacing\'s 2048 paint textures option.'],
  ['support:file_size', 'support:size_2048', 'support:glass_black'], ['template', 'tga'])
I('tga', 'TGA files', 'tga|tga file|targa|24 bit|24 bit tga|32 bit|32 bit tga|alpha|alpha channel|rle|black paint|paint turns black|all black',
  'iRacing wants a 24-bit TGA. A TGA with an alpha channel can make parts vanish or turn black.',
  ['Cars with paintable glass are the exception and need a 32-bit TGA.'], ['support:glass_black', 'support:file_size'], ['paint_size'])
I('template_layers', 'Template layers', 'template layers|template layer|wire|wire layer|wireframe|wire lines|mask layer|car_mandatory|car mandatory|mandatory|turn off before exporting|guide layers|hide template|hide the template',
  'The template layers (Wire, Mask, Car_Mandatory) are guides, not paint. Turn them OFF before every render.',
  ['If they are visible the outlines get baked into the paint and you can get two numbers.'],
  ['support:template_layers', 'help:wireframe'], ['template', 'layer'])
I('trading_zone_limit', 'Zone limit', 'zone limit|too many zones|max zones|maximum zones|how many zones|memory|out of memory|render fails|render failed|preview failed',
  'A render accepts up to 50 zones, but only about 20 zones that have their own painted area fit in memory.',
  ['If you hit it, undo the last design or say start over; fewer zones and simpler finishes always work.'],
  ['support:zone_limit', 'support:memory', 'support:preview_failed', 'support:performance'], ['zone', 'render'])
I('render_time', 'Render time / slow render', 'render time|slow render|rendering slow|render slow|render takes forever|stuck rendering|render stuck|terminate|render busy|how long does it take|speed|slow|laggy|lag|performance',
  'A render usually takes seconds to about a minute; more zones and heavy finishes take longer.',
  ['Fewer zones and fewer stacked spec patterns make it faster.', 'The Terminate button only stops waiting; the engine still finishes.'],
  ['support:render_time', 'support:performance', 'support:render_busy'], ['render', 'zone'])
I('preview_vs_sim', 'Preview vs the real thing', 'preview vs sim|preview looks different|looks different|different in game|different in the game|doesnt match|does not match|shine looks different|live preview|preview|sun|lighting',
  'The live preview is a quick design view. iRacing lights the real paint with its own sun and the car\'s materials, so the shine will not match exactly.',
  ['Colours and patterns match; shine and metal come from the spec file.', 'Always check the real render in the sim.'],
  ['support:preview_vs_sim', 'help:refresh'], ['spec_map', 'render'])
I('autodeploy', 'Auto-deploy', 'auto deploy|autodeploy|live link|livelink|deploy now|deploy|send to iracing|copy to iracing',
  'The car folder is what puts files into iRacing. Auto-deploy only matters when the car folder is empty.',
  ['Deploy Now sends the LAST render to a different car\'s folder.'],
  ['support:autodeploy', 'support:job_gone'], ['car_folder', 'render'])
I('zip_package', 'ZIP package', 'zip|zip package|export zip|zip export|download zip',
  'Turn on Export ZIP Package in Settings and each render also builds a ZIP to download.',
  ['It is not copied into iRacing; download it right away because only the two newest renders are kept.'], ['support:zip', 'control:exportZipCheckbox'], ['export'])
I('helmet_suit', 'Helmets and suits', 'helmet|helmets|suit|suits|driver suit|race suit|helmet design|helmet paint',
  'Shokker paints cars in this build, not helmets or suits.',
  ['Their iRacing files are helmet_<ID>.tga and suit_<ID>.tga; use iRacing\'s own tools or another editor.'], ['support:helmet_suit'], ['wheels'])
I('wheels', 'Wheels', 'wheel|wheels|rim|rims|tire|tires|tyre|tyres',
  'Wheels, rims and tyres are not on the car paint sheet: iRacing paints them from a separate wheel texture.',
  [], ['support:helmet_suit', 'support:what_can_you_do_support'], ['small_parts'])
I('windows', 'Windows and glass', 'window|windows|glass|windshield|windscreen|tinted windows|window tint',
  'The windows are not part of the paint on most iRacing cars; the sim draws the glass.',
  ['Cars with paintable glass need a 32-bit TGA with the glass alpha filled.'], ['support:glass_black'], ['tga'])
I('interior', 'Cockpit and interior', 'cockpit|interior|seat|seats|dash|dashboard|roll bar|rollbar|roll cage|rollcage|pit box|pitbox|pit board|pitboard',
  'The cockpit, roll bar and pit box are only paintable if your template has a layer for them.',
  ['Open the layers panel to see what your template contains.'], ['help:layers_vis', 'help:teach_parts'], ['layer', 'small_parts'])
I('small_parts', 'Small car parts', 'headlight|headlights|head light|head lights|taillight|taillights|tail light|tail lights|light|lights|grille|grill|grilles|mirror|mirrors|splitter|diffuser|scoop|scoops|vent|vents|nerf bar|nerf bars|license plate|licence plate|plate|plates|antenna|wiper|wipers|handle|handles|fender|fenders|quarter panel|quarter panels|side skirt|side skirts|skirt|skirts|mirror cap|mirror caps|number plate',
  'Small parts like lights, grilles and mirrors are usually drawn inside a bigger panel on the paint sheet, not as their own area.',
  ['Tell me which panel to change, or use Teach me the car\'s parts so I learn where things are.'],
  ['help:teach_parts'], ['part', 'zone'])
I('shokker_file', 'Project file (.spb / .shokk)', 'project file|spb file|shokk file|shokker file|shokker project|save project|projects|save my work|autosave|auto save|backup',
  'The Shokker project file holds your whole design so you can reopen and keep editing. Never upload it to Trading Paints.',
  [], ['support:shokker_file', 'help:save', 'support:autosave_off'], ['export', 'recipe'])
I('recipe', 'Recipe (sharing a design)', 'recipe|recipes|copy recipe|import recipe|export recipe|shokkerrecipe|share design|share a design|share my design',
  'A recipe is a block of text (or a .shokkerrecipe file) that rebuilds a design on any car Shokker knows.',
  [], ['support:recipe', 'doc:GETTING_STARTED.html#More tools worth knowing'], ['shokker_file'])
I('settings', 'Settings', 'settings|setting|settings gear|gear|preferences|options|where are the settings|license|licence|activate|activation|license key|licence key|deactivate|update|updates|auto update|new version|upgrade',
  'Most settings are in the top bar; the rest (Auto-deploy, ZIP export, Report a Problem, License) are under the Settings gear at the top right.',
  [], ['support:settings_where', 'support:license_update', 'control:settingsGearBtn', 'control:licenseKeyInput'], ['report_problem'])
I('report_problem', 'Report a problem', 'report a problem|report problem|bug|bugs|crash|crashed|broken|not working|doesnt work|does not work|error|errors|diagnostics|logs|something is wrong|glitch',
  'Report a Problem builds a copy-paste bundle of recent errors and logs. It never includes your license key or passwords.',
  [], ['support:report_problem', 'support:engine_offline'], ['settings'])
I('offline_ai', 'AI helper and key', 'ai|ai key|api key|openrouter|deepseek|chat ai|ai helper|ai cost|offline|offline helper|no internet|without ai|without internet|free|does it cost',
  'The built-in helper works fully offline and free. The AI helper is optional and needs a key you connect yourself.',
  [], ['support:offline_ok', 'support:ai_setup', 'support:ai_cost', 'support:ai_privacy', 'help:ai_key'], ['report_problem'])
I('easy_pro', 'Easy vs Pro', 'easy mode|pro mode|easy|pro|chat mode|chat studio|modes|switch mode',
  'Pro is the full zone-by-zone editor, Easy is paint-by-numbers, and Chat Studio lets you just describe what you want.',
  [], ['help:easy_pro', 'control:spbModeProBtn', 'control:spbModeEasyBtn', 'control:spbModeChatBtn'], ['zone'])
I('hue_sat_bright', 'Hue / saturation / brightness', 'hue|saturation|brightness|hsb|hue shift|saturate|desaturate|tint|more vivid|vivid',
  'Hue, saturation and brightness are three sliders that shift a finish\'s colour. Small moves turn one finish into ten.',
  [], ['help:hue', 'control:zone_hue_shift', 'control:zone_saturation', 'control:zone_brightness'], ['colour'])
I('tolerance', 'Tolerance', 'tolerance|color tolerance|colour tolerance|wand tolerance|too much selected|grabbed the wrong|grabbed too much|selected too much|not selecting everything',
  'Tolerance is how fuzzy a colour match is: low grabs that exact shade, high grabs the whole neighbourhood.',
  ['Raising it fixes most "it missed part of the area" problems; lowering it fixes "it grabbed too much".'], ['help:pick_colours', 'control:wandTolerance', 'doc:GETTING_STARTED.html#Zones'], ['zone'])
I('hard_edge', 'Hard edge', 'hard edge|crisp edge|sharp edge|soft edge|edge softness|feather|feathering|jagged edges|blurry edges',
  'Hard Edge makes a zone\'s boundary crisp instead of a soft blend.', [], ['doc:GETTING_STARTED.html#Zones', 'control:selectionFeather'], ['zone', 'tolerance'])
I('opacity_strength', 'Strength / opacity', 'strength|intensity|opacity|too strong|too weak|too much|not enough|stronger|weaker|subtle|bolder|more intense|less intense|fade it',
  'Strength and opacity control how strongly a finish or pattern shows. Lower it to calm a look down, raise it to make it bold.',
  [], ['help:intensity', 'control:zone_intensity', 'control:zone_pattern_opacity'], ['pattern', 'hue_sat_bright'])
I('pattern_size', 'Pattern size / scale', 'scale|pattern size|pattern scale|bigger pattern|smaller pattern|crushed|crush it|finer|coarser|fine detail|tiny|huge|zoom|rotate pattern|rotation|rotate',
  'Scale makes a pattern bigger or smaller; on a whole car, fine detail looks richest, so crush the scale down.',
  ['Rotation turns the pattern; patterns are built to sit on the car in any orientation.'], ['help:pattern_size', 'control:zone_pattern_scale', 'control:zone_pattern_rotation', 'control:zone_base_scale'], ['pattern'])
I('priority', 'Zone order (which wins)', 'zone order|which zone wins|zone priority|overlap|overlapping zones|covered by another zone|zone covered|hidden zone|zone hidden|zone not showing|zone doesnt show|mute|muted|unmute',
  'When zones overlap, the zone higher in the list wins. A muted or covered zone shows nothing.',
  ['Move the zone up, or unmute it, if its look is not showing.'], ['help:zone_order', 'help:mute', 'control:zone_order_priority', 'control:zone_mute'], ['zone'])
I('lock', 'Lock', 'lock|lock zone|locked|pin zone|randomize|randomise|dice|surprise me|random',
  'Lock pins a zone so it survives if you randomise other things.', [], ['doc:GETTING_STARTED.html#Bases', 'control:smartRandomize', 'control:swatchDiceBtn'], ['zone'])
I('beta', 'Beta / known issues', 'beta|known issues|unfinished|half baked|looks half finished|mid redo',
  'Shokker is in beta: some finishes are being rebuilt. If one looks half-baked, flag it with Report a Problem.', [], ['doc:GETTING_STARTED.html#Gotchas'], ['report_problem'])
I('about_helper', 'What can the helper do', 'help|helper|what can you do|what can i ask|how do i|how to|tutorial|getting started|get started|guide|manual|instructions|stuck|im stuck|confused|no idea',
  'Ask in plain words: change a colour, add a look, fix why something does not show, or ask how any button works.',
  [], ['support:getting_started', 'support:what_can_you_do_support', 'support:about_app', 'doc:GETTING_STARTED.html#Quick Start'], ['colour', 'zone'])
I('spec_sculpt', 'Spec Sculpt Lab', 'spec sculpt|specsculpt|spec sculpt lab|sculpt|spec lab|sculpt spec|import spec map|spec map import',
  'Spec Sculpt is a full-page workshop that builds a spec map from a paint image on its own, outside the zone flow.',
  [], ['help:spec_sculpt', 'doc:GETTING_STARTED.html#More tools worth knowing'], ['spec_map', 'spec'])
I('shokk_drop', 'Shokk Drop', 'shokk drop|shokkdrop|spbdrop|drop pack|import artwork|dna spec|import my artwork|import my own artwork|share finishes',
  'Shokk Drop imports your own artwork or a DNA spec and shares finishes as .spbdrop packs.', [], ['doc:GETTING_STARTED.html#More tools worth knowing'], ['recipe'])
I('finish_viewer', 'Finish Viewer', 'finish viewer|window shop|browse finishes|browse the catalogue|browse the catalog|catalogue|catalog|all finishes|finish library|library|swatches|swatch',
  'The Finish Viewer lets you window-shop the whole library as thumbnails.', [], ['doc:GETTING_STARTED.html#More tools worth knowing', 'control:finishSearch'], ['finish'])
I('psd', 'PSD vs TGA', 'psd|photoshop|layered psd|import psd|open psd|layers map to zones|xcf|ora|gimp|flat tga|just a tga',
  'A layered PSD gives each layer its own zone, so finishes never bleed onto sponsors or numbers. A flat TGA still works: carve zones by colour.',
  [], ['support:open_psd', 'doc:GETTING_STARTED.html#PSD vs TGA', 'control:onboardingImportPsdBtn'], ['template', 'layer', 'zone'])
I('car_numbers_info', 'Car number vs User ID', 'car number vs id|number vs id|is my id my number|id is not my number|iracing number',
  'Your User ID (Customer ID) is not your car number. The car number is part of the paint or stamped on by iRacing.', [], ['support:customer_id', 'support:number_modes'], ['user_id', 'number_modes'])
I('quality_tips', 'Make it look expensive', 'pop|make it pop|look expensive|premium|premium look|looks cheap|looks flat|looks boring|stand out|eye catching|eye-catching|wow|wow factor|sick|badass|clean look|looks busy|too busy|too plain',
  'To make a car pop: pair a colour with its opposite on the wheel, keep one hero panel, and let a fine-detail spec do the sparkle.',
  ['Too busy? Lower strength or scale up. Too plain? Add a spec pattern.'], ['help:spec_pattern', 'help:intensity'], ['spec', 'pattern'])

# =====================================================================================================  FLOWS
FL('colour', 'Change a colour', 'color|colour|colors|colours|recolor|recolour|recolored|recoloured|repaint|re paint|change color|change colour|change the color|change the colour|color change|colour change|switch color|swap color|swap colour|new color|new colour|different color|different colour|dye|dyed|tint the|change|changing|changed|switch|swap|replace|turn the',
   'Change one colour on the car to another. I find the colour on your car, you pick the new one.',
   ['Works on a colour wherever it appears, or limit it to a part (hood, sides, roof).', 'Everything else stays as it is, and Undo takes it back.'],
   ['ask_target|Which colour on the car do you want to change?', 'ask_colour|What colour should it become?', 'ask_part|Everywhere, or just one part?', 'confirm|Change it now?'],
   ['help:zone_colour', 'help:whats_on_car', 'help:hue'], ['hue_sat_bright', 'finish'])
FL('finish', 'Pick a finish', 'finish|finishes|finish type|material|materials|base|bases|look|looks|effect|effects|what finishes|finish picker|apply finish|a finish|surface',
   'A finish is the surface: how glossy, metallic or textured a part is.',
   ['Foundation finishes keep your paint colours and change only the shine; other finishes bring their own colours.'],
   ['ask_part|Which part of the car?', 'ask_look|What kind of look (matte, chrome, candy, pearl, a pattern)?', 'ask_choice|Pick one of the suggestions.', 'confirm|Apply it?'],
   ['help:pick_finish', 'help:keep_paint', 'doc:GETTING_STARTED.html#Bases'], ['spec', 'pattern'])
FL('pattern', 'Add a pattern', 'pattern|patterns|add a pattern|texture|textures|print|prints|graphic pattern|overlay pattern|pattern overlay',
   'A pattern lays a texture or shape over a part of the car, like carbon weave, camo or checkers.',
   ['Treat a pattern as a material, not an upright decal: it can sit at any angle.', 'Scale, rotate and opacity change how it reads.'],
   ['ask_part|Which part of the car?', 'ask_choice|Which pattern?', 'ask_colour|Keep the paint colour or tint it?', 'confirm|Apply it?'],
   ['help:pattern', 'help:pattern_size', 'doc:GETTING_STARTED.html#Patterns'], ['pattern_size', 'finish'])
FL('spec', 'Shine, metal & clearcoat (spec)', 'spec|specs|spec pattern|spec patterns|shine|shiny|shininess|metal look|only the shine|just the shine|keep my colors|keep my colours|keep the colors|keep the colours|spec only|reflection|reflections|reflective surface|sheen|how shiny',
   'Spec controls how shiny, metallic or rough a part is, without changing its colour.',
   ['Red is metal, green is roughness (0 = mirror), blue is clearcoat (16 = maximum gloss).', 'Use a Foundation finish with "use source paint" to change only the shine.'],
   ['ask_part|Which part?', 'ask_choice|More shine, less shine, metal, matte or sparkle?', 'confirm|Change only the shine and keep my colours?'],
   ['support:spec_what', 'help:keep_paint', 'help:spec_strength', 'help:spec_pattern', 'doc:GETTING_STARTED.html#Spec Patterns'], ['spec_map', 'spec_sculpt'])
FL('number', 'Car numbers', 'number|numbers|car number|car numbers|my number|digits|number panel|number panels|racing number|door number|roof number|roof numbers|door numbers|numbers on the car|add a number|change the number|change the numbers|number colour|number color',
   'Your car number is either drawn on the paint (Custom Number) or stamped on by iRacing (Sim-Stamped).',
   ['There is no box to type a number: pick the mode, then paint the number on the template if you chose Custom.', 'Keep finishes off the number layers so the number stays readable.'],
   ['ask_choice|Draw my own number (Custom) or let iRacing stamp it (Sim-Stamped)?', 'ask_colour|What colour should the number be?', 'tell|Set the matching switch next to your User ID and check Hide Car Numbers in iRacing.'],
   ['help:numbers', 'support:number_modes', 'control:useCustomNumberCheckbox', 'control:useSimStampedCheckbox'], ['number_modes', 'sponsor'])
FL('sponsor', 'Sponsors & logos', 'sponsor|sponsors|sponsor logo|sponsor logos|sponsor panel|sponsor panels|logo|logos|decal|decals|lettering|branding|dealer logo|team name|driver name|windshield banner|sun strip|sunstrip|banner|sponsor strip|advert|adverts|advertising|ads|add a logo|add my logo|add a picture|picture|image|stamp|sticker|stickers|badge|badges',
   'Sponsors and logos are stamped ON TOP of the paint so a finish never smears them.',
   ['Import your logo or picture as a layer, then place it; strip any white background first.', 'In Sim-Stamped mode iRacing adds its own sponsor stamps, so do not also paint those blocks.'],
   ['ask_choice|Add my own logo or picture, or recolour the sponsors that are there?', 'ask_part|Where on the car?', 'confirm|Place it?'],
   ['help:logo', 'help:layers_vis'], ['number', 'layer'])
FL('stripes', 'Stripes & graphics', 'stripe|stripes|racing stripe|racing stripes|twin stripes|center stripe|centre stripe|pinstripe|pinstripes|pin stripe|accent|accents|accent line|trim|trim line|graphic|graphics|highlight|highlights|outline|outlines|detail|details|detailing|line|lines|lower band|upper band|belt stripe|beltline|side stripe|rally stripes|le mans stripes|lemans stripes|hood stripe|band|bands|racing line',
   'Stripes and bands are the classic way to give a car a second colour.',
   ['Choose where (along the sides, over the hood and roof, or at the lower body), the colour and the width.', 'A thin pinstripe above a bold band looks premium.'],
   ['ask_choice|Twin stripes, a centre stripe, a lower band or a pinstripe?', 'ask_colour|What colour?', 'confirm|Add it?'],
   ['help:add_zone', 'help:draw_area'], ['colour', 'gradient'])
FL('gradient', 'Gradient / fade', 'gradient|gradients|fade|fades|faded to|ombre|ombré|blend|blend colours|blend colors|two color fade|two colour fade|transition|sunset fade|color fade|colour fade|fade to black|fade out',
   'A gradient blends two or more colours smoothly across the car.',
   ['Gradients run across the whole paint sheet (all panels), so check both sides in the preview.'],
   ['ask_colour|Start colour?', 'ask_colour|End colour?', 'ask_choice|Which direction: front to back, top to bottom?', 'confirm|Apply it?'],
   ['help:gradient', 'control:zone_gradient', 'control:gradientType'], ['colour'])
FL('zone', 'Zones', 'zone|zones|add a zone|new zone|add zone|region|regions|area|areas|section|sections|select a zone|select zone|pick colours|draw area|restrict to layer|selection|select|wand|lasso|zone manager',
   'A zone is a region of the car (picked by colour, layer or part) that you dress with its own finish.',
   ['Tolerance sets how fuzzy the colour match is; Hard Edge keeps boundaries crisp.', 'A render takes up to 50 zones, but about 20 with their own painted area is the practical limit.'],
   ['ask_part|Which area: pick a colour on the car, a layer, or a named part?', 'ask_look|What look should that zone get?', 'confirm|Create the zone?'],
   ['help:add_zone', 'help:select_zone', 'help:pick_colours', 'help:draw_area', 'doc:GETTING_STARTED.html#Zones'], ['tolerance', 'priority', 'trading_zone_limit'])
FL('layer', 'Layers', 'layer|layers|layer panel|layers panel|show layer|hide layer|hide a layer|show a layer|layer visibility|layer opacity|merge layers|layer order|layered|layer 1|restrict layer|group|groups|merge|merge layers|flatten|flatten image',
   'Layers come from a layered PSD template; each layer can be shown, hidden or tied to its own zone.',
   ['Layer-to-zone mapping keeps a finish on the body from bleeding onto numbers and sponsors.'],
   ['ask_target|Which layer?', 'ask_choice|Show it, hide it, or tie a zone to it?', 'confirm|Do it?'],
   ['help:layers_vis', 'help:restrict_layer', 'doc:GETTING_STARTED.html#PSD vs TGA'], ['psd', 'zone', 'template_layers'])
FL('template', 'Template', 'template|templates|car template|psd template|open template|load template|my template|template for|iracing template|which template|wrong template|source paint|open paint|load paint|load my paint|import paint|import my paint|open my paint|upload paint|start|begin|new paint|livery|paint file|blank canvas|new canvas|empty canvas',
   'The template is the flat sheet of your car that you paint on. Use the template for the SAME car you drive.',
   ['Open it with the PSD/XCF/ORA button next to Source Paint, or drag a TGA or PSD into the centre.', 'Never resize the canvas: it must stay 2048 x 2048.'],
   ['ask_choice|Open a layered PSD, or a flat TGA?', 'open_control|SOURCE PAINT box', 'tell|When it shows in the centre, the live preview fills in.'],
   ['help:load_paint', 'support:open_psd', 'control:paintFile', 'control:onboardingImportPsdBtn'], ['psd', 'paint_size'])
FL('render', 'Render', 'render|rendering|rendered|re render|rerender|render it|build paint|final paint|make the paint|finalize|finalise|bake',
   'RENDER builds the final paint and shine files and copies them into your iRacing car folder.',
   ['Switch the template layers OFF first.', 'Then press Ctrl+R in iRacing to see it.'],
   ['tell|Turn OFF Wire, Mask and Car_Mandatory.', 'open_control|RENDER button', 'tell|When it is saved, press Alt+Tab then Ctrl+R in iRacing.'],
   ['help:render', 'support:how_export', 'support:render_time', 'control:btnRender'], ['reload', 'car_folder', 'not_showing'])
FL('export', 'Export to iRacing', 'export|exporting|exported|save for iracing|get it into iracing|put it in iracing|put it in the game|send it to iracing|install paint|install my paint|use it in iracing|use in game|deploy to iracing|send to the sim|export tga|save tga|download|zip it',
   'Exporting is just RENDER with your User ID and car folder set; the files copy into iRacing for you.',
   ['Set User ID, pick the car folder, choose the number mode, then RENDER and press Ctrl+R in the sim.'],
   ['ask_choice|Have you set your User ID and car folder?', 'open_control|RENDER button', 'tell|Press Alt+Tab then Ctrl+R in iRacing.'],
   ['support:how_export', 'help:iracing', 'control:iracingId', 'control:outputDir', 'control:btnRender'], ['render', 'user_id', 'car_folder'])
FL('undo', 'Undo / start over', 'undo|history|undo history|take it back|go back|revert|put it back|put it back how it was|put it back to normal|as it was|restore|restore original|original paint|reset|start over|start again|clear all|redo|oops|mistake|i messed up|i broke it',
   'Every change can be undone. Start over clears the design and keeps your paint loaded.',
   [], ['ask_choice|Undo the last change, or start over?', 'confirm|Do it?'], ['help:undo', 'help:start_over'], ['zone'])
FL('part', 'Car parts', 'part|parts|car part|car parts|panel|panels|body panel|body panels|left side|right side|passenger side|driver side|driver door|passenger door|door|doors|flank|side panel|side panels|both sides|front|rear|back|whole car|entire car|the car|the truck|my car|my truck|everything|all of it|the whole thing|vehicle|body|bodywork|paintwork|the paint|base color|base colour|main color|main colour|primary color|primary colour|the base|truck|car',
   'Parts are the named areas of your car: hood, roof, trunk, bumpers, spoiler, left and right side.',
   ['Tell me a part by name and I put the change only there; say "whole car" for everything.', 'If I do not know your car\'s parts yet, Teach me the car\'s parts.'],
   ['ask_part|Which part?', 'ask_look|Colour or finish?', 'confirm|Apply it?'], ['help:teach_parts', 'help:whats_on_car'], ['zone', 'colour'])
FL('schemes', 'Livery schemes', 'scheme|schemes|livery scheme|color scheme|colour scheme|colors scheme|livery style|race livery|design a livery|full livery|make a livery|design me|design a design|design',
   'A scheme lays out a whole livery at once: a base colour plus bands, stripes or blocks on named parts.',
   ['Pick a style, then a colour set (a team look, a country, an era), and I place it on the right parts.'],
   ['ask_choice|Which style: retro lower band, classic twin stripes, two-tone, colour block, bookends or stealth?', 'ask_colour|Which colour set?', 'confirm|Lay it out on the car?'],
   ['help:add_zone', 'help:whats_on_car'], ['stripes', 'colour'])
FL('iracing_checklist', 'Check why it is not showing', 'check my settings|check settings|troubleshoot|troubleshooting|diagnose|why isnt it working|why is it not working|checklist|iracing checklist|help me fix',
   'I check your User ID, number setting, folder and files and tell you which step is off.',
   [], ['tell|Checking the User ID.', 'tell|Checking the number mode against Hide Car Numbers.', 'tell|Checking the car folder and the files in it.', 'tell|Then press Ctrl+R in iRacing.'],
   ['support:how_export', 'support:number_modes', 'support:customer_id', 'support:where_files'], ['not_showing', 'user_id'])
FL('paint_bucket', 'Paint tools (brush, fill, text)', 'bold|italic|letter spacing|font size|text size|brush|paint brush|brushes|fill|bucket|eyedropper|eraser|clone|smudge|text tool|add text|text|font|shape tool|shapes|healing|dodge|burn|touch up|touch ups|touchup|retouch',
   'There are pixel tools on the canvas for touch-ups. They work, but the power is in finishes and spec.',
   [], ['ask_choice|Brush, fill, eyedropper, text or shapes?', 'open_control|the tool in the left toolbar'], ['control:vtModeBrush', 'control:vtModeFill', 'control:vtModeEyedropper', 'control:textFont', 'control:shapeType'], ['zone'])

# =====================================================================================================  LOOK FAMILIES (action / flow)
# tags = atlas tags (any); name = regex on the finish name/key; words = regex on the card's buyer words / look text.
A('holographic', 'Holographic', 'holographic|holographics|holo|holos|hologram|holograms|holo foil|holographic foil|hologram foil|holo paint|laser|laser foil|holographic paint|hologrphic|holographik|holografic',
  'A holographic look: a rainbow diffraction shimmer that moves as the light changes.',
  det=['It lives in the shine, so your paint colour stays.', 'Looks best on a darker base.'], tags=['holographic'], name='holo', words='holo', own=None, n=6,
  fin=['base::efx_holographic_drift', 'base::holographic_base'], links=['help:pick_finish'], rel=['colour_shift', 'iridescent', 'chrome_family'])
A('colour_shift', 'Colour shift (chameleon)', 'chameleon|color shift|colour shift|colorshift|colourshift|color flip|colour flip|colorflip|chromaflair|chroma flair|flip paint|colour changing|color changing|two color shift|multi color shift',
  'Colour-shift paint changes colour as you look from different angles, like chameleon paint.', tags=['iridescent', 'rainbow'], name='chameleon|flair|shift|flip|chroma', words='chameleon|colo(u)?r shift|flip', n=6,
  fin=['base::chromaflair'], rel=['holographic', 'iridescent'])
A('iridescent', 'Iridescent / prism', 'iridescent|iridescence|iridescents|prism|prizm|prismatic|dichroic|oil slick|oilslick|rainbow|rainbows|opalescent|opal|soap bubble|bubble|nacre|mother of pearl|mother-of-pearl',
  'Iridescent finishes split light into rainbow colours, like oil on water or a soap bubble.', tags=['iridescent', 'rainbow', 'nacre'], name='prism|iridesc|opal|nacre|dichroic|oil', words='iridesc|prism|rainbow|oil slick|opal', n=6,
  fin=['monolithic::xlab_dichroic_skin'], rel=['holographic', 'colour_shift', 'pearl_look'])
A('chrome_family', 'Chrome', 'chrome|chromed|chromey|crome|chrom|mirror chrome|mirror|mirrors finish|mirror finish|mirrored|liquid chrome|polished chrome|chrome paint|full chrome|chrome wrap|chrome car',
  'Chrome is a perfect mirror metal. It reflects everything, so the car looks like polished steel.',
  det=['Chrome wants a near-white paint underneath or it goes dark in the sim.', 'Variants: mirror, satin (soft), dark (smoked).'], kind='flow',
  steps=['ask_part|Whole car or just a part?', 'ask_choice|Mirror chrome, satin chrome or dark chrome?', 'confirm|Apply it?'],
  tags=['chrome', 'reflective', 'polished'], name='chrome|mirror|liquid metal', n=6, fin=['base::f_chrome', 'base::f_satin_chrome', 'base::f_dark_chrome'], links=['support:chrome_dark'], rel=['metallic_look', 'gunmetal'])
A('snakeskin', 'Snakeskin', 'snakeskin|snake skin|snakeskins|snake|snakes|rattlesnake|rattle snake|rattlesnakes|snake scale|snake scales|snakescale|python|cobra|viper|serpent|reptile|reptiles|reptilian|lizard|lizards|reptile skin|reptile scales',
  'Snakeskin is a scaly reptile texture: rows of small diamond scales across the car.',
  det=['Pick a colour for the scales and I add the texture on top.', 'Python, cobra and rattlesnake all give a diamond scale.'], kind='flow',
  steps=['ask_part|Whole car or a part?', 'ask_colour|What colour should the snake be?', 'ask_choice|Pick a snake look.', 'confirm|Apply it?'],
  name='snake|python|cobra|viper|serpent|reptil|lizard|gecko|anaconda', words='snake|reptil|lizard|python|cobra|viper|serpent', tags=[], n=6,
  pats=['snake_skin'], specs=['snake_scale_diamond', 'spec_snake_scales'], rel=['crocodile', 'dragon_scales', 'fish_scales'])
A('crocodile', 'Crocodile skin', 'croc|crocs|crocodile|crocodile skin|croc skin|alligator|gator|alligator skin|gator skin|croc leather|crocodile leather',
  'Crocodile skin is a bumpy armoured-leather texture, big plates with a rugged feel.', name='croc|alligator|gator|armor|armour', words='croc|alligator|gator', n=5,
  pats=['crocodile'], specs=['croc_delta_armor'], rel=['snakeskin', 'dragon_scales'])
A('dragon_scales', 'Dragon scales', 'dragon scales|dragon scale|dragon skin|dragon hide|dragon|dragons|dragon armor|dragon armour',
  'Dragon scales are big overlapping armour scales, like a fantasy dragon hide.', name='dragon', words='dragon', n=5, pats=['dragon_scale'], specs=['dragon_scale_macro'], rel=['snakeskin', 'fish_scales'])
A('fish_scales', 'Fish scales', 'fish scales|fish scale|fishscale|mermaid scales|mermaid scale|mermaid|scales|scale pattern|scaly|scale texture|seigaiha|koi',
  'Fish scales are rows of small overlapping half-circles, like a mermaid tail or Japanese wave scales.', tags=['scales'], name='scale|mermaid|koi|seigaiha', words='scale|mermaid|fish', n=6,
  pats=['seigaiha_scales'], specs=['spec_fish_scales'], rel=['snakeskin', 'dragon_scales'])
A('carbon_fiber', 'Carbon fibre', 'carbon fiber|carbon fibre|carbonfiber|carbonfibre|carbon|carbon weave|carbon look|cf|kevlar|aramid|twill weave|2x2 twill|woven carbon|forged carbon',
  'Carbon fibre is the woven dark texture of race-car body panels, under a deep gloss.', kind='flow',
  steps=['ask_part|Whole car or a part (hood, roof, splitter)?', 'ask_choice|Classic weave, forged carbon or kevlar?', 'confirm|Apply it?'],
  tags=['carbon', 'weave', 'aramid', 'forged'], name='carbon|kevlar|aramid|weave|twill', words='carbon|kevlar|weave', n=6, pats=['carbon_fiber', 'hex_carbon'], rel=['hexagon', 'brushed_aluminum'])
A('camo', 'Camouflage', 'camo|camos|camouflage|camouflaged|digital camo|woodland camo|desert camo|army|army paint|military|military paint|army green|multicam|splinter camo|pixel camo|urban camo|hunting camo|snow camo|marpat',
  'Camouflage is a blotchy multi-colour pattern made to hide a shape.', kind='flow',
  steps=['ask_part|Whole car or a part?', 'ask_choice|Woodland, desert, digital, urban or snow?', 'confirm|Apply it?'],
  tags=['camo', 'military', 'tactical'], name='camo|woodland|multicam|splinter|marpat|tiger stripe', words='camo', n=6, pats=['camo'], rel=['tactical', 'matte_look'])
A('flames', 'Flames', 'flames|flame|flaming|flame job|flamejob|flames paint|hot rod flames|hotrod flames|true fire|fire|fires|on fire|inferno|blowtorch|blow torch|phoenix|burning|burn|blaze|blazing|fire paint|fire look|fire effect',
  'Flames are the classic hot-rod licking-fire graphic, from clean tribal tongues to realistic fire.', kind='flow',
  steps=['ask_part|Where do the flames go: hood and sides, or the whole car?', 'ask_colour|Fire colours: red-orange, blue or custom?', 'ask_choice|Pick a flame style.', 'confirm|Apply it?'],
  tags=['flames', 'fire'], name='flame|fire|inferno|blaze|phoenix|torch|ember|cinder', words='flame|fire|inferno', n=6, fin=['base::flame_phoenix', 'monolithic::ffl_blowtorch'], rel=['lava', 'neon'])
A('lava', 'Lava / molten', 'lava|molten|magma|volcano|volcanic|ember|embers|hot coals|coals|glowing|glow|cinder|cinders|lava lamp|forge|forged fire|smolder|smoulder',
  'Lava finishes look like molten rock: dark crust with glowing orange cracks.', name='lava|magma|molten|ember|cinder|volcan|smolder|forge', words='lava|molten|magma|ember|glow(ing)? crack', tags=[], n=5, rel=['flames', 'patina'])
A('galaxy', 'Galaxy / space', 'galaxy|galaxies|nebula|nebulas|cosmic|cosmos|space|outer space|stars|star field|starfield|starry|starry night|night sky|milky way|universe|astro|astral|stardust|constellation|supernova|black hole|planet|planets|aurora|northern lights|aurora borealis',
  'Galaxy finishes put a deep-space look on the car: nebula clouds, star fields and glowing colour.', tags=['cosmic', 'space', 'aurora'], name='galax|nebula|cosm|star|space|aurora|astro|nova|void|orbit|comet|meteor', words='galax|nebula|space|star', n=6,
  fin=['base::pour_galaxy'], rel=['neon', 'iridescent'])
A('checkered', 'Checkered / chequered', 'checkered|chequered|checker|checkers|checkerboard|chequerboard|checker board|check|checks|checked|race flag|racing flag|finish line|finish flag|flag pattern|diner checkerboard|chess|chessboard|gingham|ska',
  'A checkered pattern is the racing-flag squares, big or tiny.', name='check|flag|chess|gingham', words='check(er)?|flag|chess', tags=[], n=5, pats=['decade_50s_diner_checkerboard'], rel=['stripes', 'plaid'])
A('hexagon', 'Hexagons / honeycomb', 'hex|hexes|hexagon|hexagons|hexagonal|honeycomb|honey comb|beehive|bee hive|hex grid|hex mesh|hex pattern|hex carbon',
  'Hexagons are a honeycomb grid of six-sided cells, a clean technical look.', name='hex|honeycomb|bee', words='hex|honeycomb', tags=['geometric'], n=5, pats=['hex_carbon'], rel=['carbon_fiber', 'geometric'])
A('diamond_plate', 'Diamond plate', 'diamond plate|diamondplate|tread plate|treadplate|tread|checker plate|checkerplate|checkered plate|chequer plate|truck bed liner|bed liner|raised diamonds|industrial floor',
  'Diamond plate is the raised-diamond metal of truck beds and workshop floors.', name='diamond|tread|plate', words='diamond plate|tread plate|checker plate', tags=['industrial'], n=5, pats=['diamond_plate'], rel=['brushed_aluminum', 'hammered_metal'])
A('tiger', 'Tiger stripes', 'tiger|tigers|tiger stripe|tiger stripes|tiger print|tiger skin|zebra|zebra stripe|zebra stripes|zebra print|animal print|animal stripes|big cat|big cats',
  'Tiger stripes are bold curved stripes like a big cat, in any colour pairing.', name='tiger|zebra|stripe', words='tiger|zebra|stripe', n=5, pats=['tiger_stripe'], rel=['leopard', 'snakeskin'])
A('leopard', 'Leopard / cheetah', 'leopard|leopards|cheetah|cheetahs|jaguar spots|jaguar print|leopard print|cheetah print|spots|spotted|dalmatian|cow print|cow|giraffe|animal spots|polka',
  'Leopard and cheetah prints are rosettes and spots in a soft cat colourway.', name='leopard|cheetah|jaguar|spot|dalmatian|giraffe|cow|polka|dot', words='leopard|cheetah|spot|dalmat|polka|dot', n=5, rel=['tiger', 'snakeskin'])
A('plaid', 'Plaid / tartan', 'plaid|plaids|tartan|tartans|flannel|lumberjack|buffalo plaid|scottish|kilt|argyle|houndstooth|hounds tooth|dogstooth|herringbone|tweed|gingham plaid',
  'Plaid and tartan are crossing woven stripes; houndstooth is the small broken-check tweed look.', name='plaid|tartan|houndstooth|argyle|tweed|herringbone|flannel', words='plaid|tartan|houndstooth|argyle|tweed', n=5, pats=['plaid', 'houndstooth'], rel=['checkered'])
A('metallic_look', 'Metallic flake', 'metal flake|metalflake|metal flakes|flake|flakes|flaked|microflake|micro flake|glitter|glitters|glittery|sparkle|sparkles|sparkly|sparkling|sparkle paint|bling|glam|xirallic|stardust flake|bass boat|bass boat flake|jewel|jewels',
  'Metal flake is tiny sparkling flecks suspended in the paint, like a bass boat in the sun.', tags=['sparkle', 'flake', 'glitter', 'shimmer'], name='flake|glitter|sparkl|xirallic|stardust|bling|jewel', words='flake|glitter|sparkl', n=6,
  fin=['base::xirallic'], rel=['look:metallic', 'pearl_look', 'candy_look'])
A('gunmetal', 'Gunmetal / graphite', 'gunmetal|gun metal|gunmetal grey|gunmetal gray|graphite|anthracite|titanium|tungsten|steel|stainless|stainless steel|iron|cast iron|pewter|slate|slate grey|slate gray|dark steel|dark metal|raw steel|forged steel',
  'Gunmetal is a dark, cool, slightly bluish metal grey, like a gun barrel or graphite.', tags=['steel', 'iron', 'cast', 'forged'], name='gunmetal|graphite|titanium|tungsten|steel|iron|pewter|slate|anthracite|damascus', words='gunmetal|graphite|titanium|steel|iron', n=5,
  fin=['base::gunmetal'], rel=['chrome_family', 'brushed_aluminum'])
A('copper', 'Copper / bronze / brass', 'copper|coppery|bronze|brass|rose gold|rosegold|rose-gold|antique gold|burnished|burnished copper|gold leaf|goldleaf|gold foil|brassy|bronzed',
  'Copper, bronze and brass are warm metals: orange-red, brown-gold and yellow-gold.', tags=['copper', 'gold'], name='copper|bronze|brass|rose gold|gold leaf|burnish', words='copper|bronze|brass|rose gold', n=5, fin=['base::copper'], rel=['gold_look', 'patina'])
A('gold_look', 'Gold', 'gold|golden|gilded|gilt|gold paint|gold finish|24k|24 karat|karat|bullion|goldplate|gold plated|gold chrome|champagne gold|liquid gold|midas|treasure|money|cash|dollar|dollars|bank|banknote|luxury gold|king',
  'Gold finishes range from bright mirror gold to soft champagne and antique gold.', tags=['gold', 'luxury'], name='gold|midas|champagne|aureate|gilt|royal|money|treasure|king', words='gold|midas|luxur', n=6, rel=['copper', 'chrome_family'])
A('patina', 'Rust / patina / weathered', 'rust|rusty|rusted|rusting|rat rod|ratrod|rat-rod|barn find|barnfind|weathered|distressed|aged paint|old paint|faded paint|oxidized paint|oxidised paint|corroded|corrosion|verdigris|salt|salty|sun bleached|sunbleached|rustic|wear|wear and tear|race wear|chipped|chips|stone chips|bug splatter|bugs|tire marks|skid marks|skid|stains|stained|oil stains|dust|dusty|overspray|damage|damaged|beat up|beaten|battered|grungy|grunge|gritty|dirty|dirt|mud|muddy|soot|sooty|smoke damage',
  'Rust and patina are the look of old metal: peeled paint, orange rust and weathering.', tags=['rust', 'weathered', 'weather', 'patina', 'distressed', 'soot', 'salt', 'rustic', 'aged'], name='rust|patina|weather|distress|corro|verdigris|grunge|peel|salt|soot|rat', words='rust|patina|weather|distress|barn', n=6, rel=['matte_look', 'copper'])
A('marble', 'Marble / stone', 'marble|marbled|marbling|granite|stone|stones|rock|rocks|concrete|cement|slate stone|terrazzo|onyx|agate|quartz|jasper|travertine|limestone|sandstone|lapis|malachite|obsidian|pebble|pebbles|cobblestone|cobble',
  'Marble and stone finishes show natural veined rock, from white marble to black onyx.', tags=['stone', 'terrazzo', 'pebble'], name='marble|granite|onyx|agate|quartz|jasper|stone|rock|terrazzo|obsidian|lapis|malachite|concrete|pebble', words='marble|granite|onyx|stone|rock|concrete', n=6, rel=['wood_grain', 'gold_look'])
A('wood_grain', 'Wood grain', 'wood|woodgrain|wood grain|wooden|wood paneling|wood panelling|woody|timber|oak|walnut|mahogany|bamboo|birch|cedar|driftwood|log|bark|plywood|teak|ebony|burl|burr|veneer|woodie|station wagon wood|wood trim',
  'Wood-grain finishes copy real timber, from retro station-wagon panelling to dark burl.', tags=['wood', 'grain'], name='wood|oak|walnut|mahogany|bamboo|timber|bark|teak|ebony|burl|veneer|grain|plank', words='wood|oak|walnut|timber|bark|grain', n=6, rel=['marble', 'leather_look'])
A('leather_look', 'Leather', 'leather|leathery|suede|stitched|stitching|saddle|saddle leather|upholstery|hide|cowhide|pleather|alcantara|nappa|quilted|quilting|diamond stitch|diamond stitching',
  'Leather finishes give a stitched, grained hide look.', tags=['leather'], name='leather|suede|stitch|saddle|hide|quilt|nappa|alcantara', words='leather|suede|stitch|saddle|quilt', n=5, rel=['wood_grain', 'matte_look'])
A('glass_look', 'Glass / crystal', 'glass|glassy look|crystal|crystals|crystalline|stained glass|shattered|shattered glass|broken glass|cracked glass|prism glass|diamond|diamonds|gem|gems|gemstone|jewel look|faceted|facets|facet|kaleidoscope|mosaic|tile|tiles|tiled|mosaic tile|truchet',
  'Glass and crystal finishes are faceted, see-through looking surfaces, from shattered glass to gemstones.', tags=['glass', 'jeweled'], name='glass|crystal|facet|gem|diamond|kaleido|mosaic|tile|truchet|shatter|prism', words='glass|crystal|facet|gem|mosaic|kaleido', n=6, rel=['iridescent', 'ice'])
A('ice', 'Ice / frost / snow', 'ice|icy|iced|icicle|icicles|frost|frosty|frosted glass|frozen|freeze|freezing|cryo|cryogenic|glacier|glacial|arctic|snow|snowy|snowflake|snowflakes|winter|blizzard|sleet|hoarfrost|rime',
  'Ice and frost finishes look frozen: cold blues, crystal patterns and frosted metal.', tags=['ice', 'frost', 'cold', 'snow', 'frozen', 'rain'], name='ice|icy|frost|frozen|cryo|glacier|arctic|snow|winter|blizzard|rime', words='ice|frost|frozen|snow|glacier|arctic', n=6, rel=['glass_look', 'water'])
A('water', 'Water / ocean / waves', 'water|watery|liquid|liquids|aqua look|ocean|oceans|sea|seas|waves|wave|wavy|ripple|ripples|rippled|tidal|tide|rain|rainy|raindrops|droplets|droplet|beads|beading|water beads|wet|splash|splashes|underwater|deep sea|abyss|abyssal|surf|reef|coral reef|marine|nautical|pool',
  'Water finishes look like waves, ripples or beaded droplets.', tags=['water', 'rain', 'beads'], name='water|ocean|wave|ripple|rain|drop|bead|sea|tide|surf|reef|abyss|splash|aqua', words='water|ocean|wave|ripple|rain|droplet', n=6, rel=['ice', 'glass_look'])
A('neon', 'Neon / glow', 'neon|neons|neon glow|neon sign|neon lights|neon look|glow in the dark|glowing neon|fluorescent|fluoro|day glo|dayglo|day-glo|electric|cyber|cyberpunk|cyber punk|synthwave|synth wave|retrowave|retro wave|vaporwave|vapor wave|outrun|tron|rave|club|laser lights|blacklight|black light|uv|uv paint|uv reactive|highlighter|highlighter yellow',
  'Neon finishes glow in hot electric colours, like signs, synthwave grids and cyberpunk streets.', tags=['neon', 'cyber', 'futuristic'], name='neon|cyber|synth|retrowave|vapor|tron|rave|glow|electric|laser|fluoro|punk', words='neon|cyber|synth|glow|retrowave|vapor|tron', n=6, rel=['galaxy', 'iridescent'])
A('lightning', 'Lightning / electric', 'lightning|lightning bolt|lightning bolts|bolt|bolts|thunder|storm|storms|stormy|thunderstorm|electric arc|electricity|plasma|spark|sparks|static|shock|tesla|arc|arcs|lichtenberg',
  'Lightning finishes crackle with branching electric arcs and bolts.', tags=['lightning'], name='lightning|bolt|thunder|storm|plasma|spark|tesla|arc|lichtenberg|static|shock', words='lightning|bolt|thunder|plasma|electric|lichtenberg', n=5, rel=['neon', 'galaxy'])
A('geometric', 'Geometric / abstract', 'geometric|geometry|geo|abstract|shapes|triangles|triangle|low poly|lowpoly|polygon|polygons|mosaic shapes|tessellation|tessellations|tessellated|fractal|fractals|mandelbrot|kaleidoscopic|op art|optical illusion|moire|moiré|interference|zigzag|zig zag|chevron|chevrons|herringbone shape|diamonds pattern|stripes pattern|lattice|grid|grids|mesh|circuit|circuits|circuit board|pcb|techy|tech|technical|futuristic|sci fi|scifi|sci-fi',
  'Geometric finishes are clean repeating shapes, grids and fractals with a technical feel.', tags=['geometric', 'fractal', 'mathematical', 'futuristic', 'moire', 'spiral'], name='geo|tessell|fractal|lattice|grid|mesh|circuit|chevron|moire|zigzag|poly|triangle|truchet', words='geometric|fractal|lattice|grid|circuit|chevron|moire', n=6, rel=['hexagon', 'carbon_fiber'])
A('stealth_look', 'Stealth / murdered out', 'stealth|stealth black|stealth bomber|blackout|black out|blacked out|murdered out|murdered|all black|all black everything|blackedout|ghost|ghosted|ghosting|tone on tone|tonal|subtle|understated|sleeper|dark mode|nightshade|midnight',
  'Stealth looks keep everything dark and tone-on-tone, so the car reads as a silhouette.', tags=['stealth', 'dark'], name='stealth|black|night|ghost|shadow|void|noir|midnight|obsidian', words='stealth|blackout|murdered|tone on tone|ghost', n=6, rel=['matte_look', 'gunmetal'])
A('pearl_look', 'Pearl / pearlescent', 'pearl|pearls|pearly|pearlescent|pearl paint|pearl white|tri coat|tricoat|tri-coat|three stage|3 stage|luxury white|lexus white',
  'Pearl is a soft glow under the clearcoat that shifts a little with the light.', tags=['pearl', 'shimmer'], name='pearl|nacre|opal', words='pearl', n=5, fin=['base::pearl', 'base::f_pearl'], rel=['candy_look', 'iridescent'])
A('retro', 'Retro / vintage', 'retro|vintage|classic|old school|oldschool|old-school|nostalgia|nostalgic|throwback|70s|1970s|seventies|80s|1980s|eighties|90s|1990s|nineties|60s|1960s|sixties|50s|1950s|fifties|disco|groovy|hippie|hippy|psychedelic|psychedelics|sock hop|diner|pop art|memphis|memphis design',
  'Retro finishes bring back a decade: 50s diner checks, 70s earth tones, 80s neon, 90s teal.', tags=['retro', 'vintage', 'era-50s', 'era-60s', 'era-70s', 'era-80s', 'era-90s'], name='retro|vintage|70s|80s|90s|50s|60s|disco|groovy|diner|sock hop|decade|psychedel', words='retro|vintage|70s|80s|90s|disco|groovy|diner', n=6, rel=['neon', 'checkered'])
A('japanese', 'Japanese / anime', 'japanese|japan|anime|manga|kawaii|samurai|ninja|katana|rising sun|risingsun|sakura|cherry blossom|cherry blossoms|koi fish|tokyo|jdm|drift|drifting|wabi sabi|ukiyo e|ukiyoe|kanji|dragon japanese|torii|shogun',
  'Japanese-inspired finishes cover anime graphics, rising-sun rays, waves, koi and cherry blossom.', tags=['japanese', 'anime', 'rising-sun', 'drift'], name='japan|anime|samurai|sakura|koi|tokyo|rising|sun|kanji|torii|shogun|manga|jdm|drift', words='japan|anime|samurai|sakura|koi|jdm', n=6, rel=['fish_scales', 'floral'])
A('mexican', 'Mexican / Day of the Dead', 'mexican|mexico|viva mexico|vivamexico|day of the dead|dia de los muertos|calavera|sugar skull|sugar skulls|talavera|serape|papel picado|aztec|mayan|maya|lucha libre|luchador|fiesta|tequila|marigold',
  'Mexican-inspired finishes cover serape stripes, talavera tile, sugar skulls and papel picado.', tags=['mexican', 'viva-mexico', 'cultural'], name='mexic|viva|serape|talavera|calavera|azteca|aztec|maya|muerto|picado|lucha', words='mexic|serape|talavera|calavera|aztec|maya|muerto', n=6, rel=['floral', 'skull'])
A('skull', 'Skulls / spooky / gothic', 'skull|skulls|skeleton|skeletons|bones|bone|death|grim|reaper|grim reaper|spooky|spooktacular|halloween|haunted|ghost story|horror|creepy|scary|gothic|goth|vampire|vampires|witch|witches|dark art|occult|demon|demons|devil|evil|zombie|zombies|monster|monsters|cemetery|graveyard|bat|bats|spider|spiders|spiderweb|cobweb|web|webs',
  'Spooky finishes bring skulls, bones, webs and gothic darkness.', tags=['spooky', 'gothic'], name='skull|skeleton|bone|grave|reaper|spook|haunt|goth|vampire|witch|demon|zombie|monster|web|spider|bat', words='skull|skeleton|bone|haunt|goth|spooky|web', n=6, rel=['stealth_look', 'lava'])
A('floral', 'Flowers / floral', 'floral|flowers|flower|flowery|roses|rose pattern|rose|petals|petal|botanical|blossom|blossoms|bloom|blooms|daisy|daisies|tulip|tulips|lotus|garden|gardens|vine|vines|leaf|leaves|leafy|foliage|jungle|tropical|tropics|palm|palms|palm tree|hibiscus|paisley|damask|toile|ivy|fern|ferns|nature|natural|forest|woodland|woods|trees|tree|grass|moss|mossy|organic',
  'Floral and nature finishes cover flowers, leaves, vines and jungle foliage.', tags=['floral', 'leaf', 'nature', 'organic', 'tribal'], name='flor|flower|rose|petal|botan|bloom|lotus|vine|leaf|leaves|fern|jungle|paisley|damask|garden|forest|moss|ivy|palm', words='flower|floral|leaf|leaves|vine|botanic|jungle|paisley|damask', n=6, rel=['japanese', 'camo'])
A('patriotic', 'Patriotic / flags', 'patriotic|america|american|american flag|us flag|usa|u s a|stars and stripes|old glory|red white and blue|red white blue|fourth of july|4th of july|july 4th|independence day|freedom|liberty|eagle|bald eagle|union jack|union jacked|british|britain|uk|england|flag|flags|stars|stripes and stars|tricolor|tricolour|canada|canadian|maple|ireland|irish|german|germany|brazil|brazilian|italy|italian|france|french|sweden|swedish',
  'Patriotic finishes cover flags, stars and stripes, eagles and national colours.', tags=['patriotic', 'july4', 'stars', 'freedom', 'bunting', 'fireworks', 'spangled'], name='flag|freedom|liberty|patriot|union jack|eagle|usa|america|bunting|firework|spangle', words='flag|patriot|usa|america|union jack|eagle|freedom', n=6, rel=['stripes', 'checkered'])
A('tribal', 'Tribal / celtic / norse', 'tribal|tribals|celtic|celts|knot|knotwork|norse|viking|vikings|runic|runes|rune|nordic|maori|polynesian|tiki|mandala|mandalas|aztec pattern|ethnic|folk|folk art|ornament|ornamental|baroque|filigree|scroll|scrollwork|damascus pattern|arabesque|moroccan|persian|turkish|islamic',
  'Tribal and heritage finishes use knots, runes, mandalas and ornamental line work.', tags=['tribal', 'norse', 'runic', 'celtic', 'cultural', 'spiral'], name='tribal|celtic|norse|viking|rune|mandala|maori|tiki|ornament|baroque|filigree|arabesque|persian|moroccan|knot', words='tribal|celtic|norse|viking|rune|mandala|filigree|baroque|knot', n=6, rel=['floral', 'japanese'])
A('brushed_aluminum', 'Brushed aluminium', 'brushed aluminum|brushed aluminium|aluminum|aluminium|alu|brushed|brush|brushed steel|brushed metal|brushed look|machined|machined aluminum|bare metal|raw aluminum|raw metal|billet|spun|spun aluminum|turned aluminum|engine turned|engine turn|guilloche|knurl|knurled|knurling',
  'Brushed aluminium has fine straight grain lines, like machined metal.', tags=['brushed', 'machined', 'knurled', 'metal'], name='brushed|aluminum|aluminium|machined|billet|spun|knurl|turned|guilloche', words='brushed|aluminum|aluminium|machin|billet|knurl', n=6, fin=['base::brushed_aluminum'], rel=['chrome_family', 'gunmetal'])
A('hammered_metal', 'Hammered / dimpled metal', 'orange peel|orangepeel|peel|textured paint|hammered|hammered metal|hammertone|hammer tone|hammer finish|hammered paint|peened|shot peened|dimpled|dimples|dents|dented|dinged|ding|golf ball|beaten metal|forged look|pitted|pitting',
  'Hammered metal has soft round dents like beaten copper or a hammertone finish.', tags=['hammered', 'dents', 'pitted', 'forged'], name='hammer|dimple|dent|peen|pitted|forged|golf', words='hammer|dimple|dent|peen|pitted', n=5, rel=['diamond_plate', 'brushed_aluminum'])
A('candy_look', 'Candy paint', 'candy|candies|candy apple|candy apple red|candy paint|candy coat|candy coated|candy colour|candy color|kandy|kustom|kustom kandy|tinted gloss|deep gloss|deep color|deep colour|lowrider|low rider|show car paint|cherry|cherry red|apple red|wine|wine red|ruby|ruby red',
  'Candy paint is a deep, glowing translucent colour over a bright metallic base, like a lollipop made of metal.', tags=['candy'], name='candy|kandy|apple|ruby|cherry', words='candy|kandy|lowrider', n=6, fin=['base::candy', 'base::f_candy'], rel=['pearl_look', 'metallic_look'])
A('matte_look', 'Matte / flat', 'matte|matt|mat|flat|flat black|matte black|flat paint|dull|dead flat|no shine|no gloss|satin black|chalky|chalk|velvet|velvety|suede finish|soft touch|soft-touch|rubberized|rubber|plasti dip|plastidip|dip|cerakote|duracoat|gunkote|powder coat|powdercoat|powdercoated|wrinkle|wrinkle coat|crinkle|primer|primer grey|primer gray|raw|bare|unpainted',
  'Matte finishes have no shine: a flat, soft surface that hides reflections.', tags=['matte', 'powder', 'soft', 'wrinkle', 'vinyl'], name='matte|flat|velvet|suede|powder|plasti|rubber|cerakote|wrinkle|primer|chalk', words='matte|flat|velvet|suede|powder|rubber', shine=['semi-matte', 'matte', 'satin'], n=6,
  fin=['base::f_soft_matte', 'base::f_powder_coat'], rel=['satin_look', 'stealth_look'])
A('satin_look', 'Satin / eggshell', 'satin|satiny|satin paint|satin finish|eggshell|egg shell|silk|silky|semi gloss|semigloss|semi-gloss|semi matte|semimatte|semi-matte|low sheen|soft sheen|mid gloss|half gloss',
  'Satin sits between gloss and matte: a soft sheen with no hard reflections.', tags=['satin', 'smooth'], name='satin|eggshell|silk|sheen', words='satin|eggshell|silk', shine=['satin', 'semi-matte'], n=5, fin=['base::f_clear_satin'], rel=['matte_look', 'gloss_look'])
A('gloss_look', 'Gloss / wet look', 'gloss|glossy|glossier|high gloss|highgloss|mirror gloss|shiny|shinier|shine|gleaming|show car|showroom|showroom shine|clearcoat|clear coat|clear|ceramic|ceramic coat|ceramic coating|wet look|wetlook|wet paint|wet shine|dripping wet|piano black|piano|lacquer|enamel|baked enamel|glaze|glazed|polished|polish|buffed|waxed|wax|detailed|factory|factory paint|factory finish',
  'Gloss is a deep, wet-looking shine with sharp reflections.', tags=['gloss', 'polished', 'lacquer', 'glaze', 'ceramic', 'smooth'], name='gloss|wet|lacquer|enamel|piano|glaze|ceramic|polish|gel', words='gloss|wet look|lacquer|enamel|piano|polish', shine=['high gloss'], n=5, fin=['base::f_soft_gloss', 'base::f_gel_coat'], rel=['satin_look', 'candy_look'])
A('vinyl_wrap', 'Vinyl wrap', 'vinyl|vinyl wrap|vinylwrap|wrap|wraps|wrapped|car wrap|full wrap|3m wrap|3m|avery|carbon wrap|color wrap|colour wrap|film|ppf|paint protection film',
  'A vinyl-wrap look is a smooth satin-matte film surface, the way a wrapped car looks.', tags=['vinyl'], name='vinyl|wrap|film', words='vinyl|wrap', n=5, fin=['base::f_vinyl_wrap'], rel=['satin_look', 'matte_look'])
A('anodized_look', 'Anodized', 'anodized|anodised|anodize|anodise|anodizing|anodising|anodized aluminum|anodised aluminium|titanium anodized|burnt titanium|heat blue|heat tint|exhaust blue|spectrum metal',
  'Anodized metal is aluminium with a dyed oxide layer: rich, slightly satin colour on metal.', tags=['anodized'], name='anodi|titanium|heat', words='anodi|titanium|heat blue', n=5, fin=['base::f_anodized'], rel=['brushed_aluminum', 'candy_look'])
A('bead_blasted', 'Bead blasted / sandblasted', 'bead blasted|bead blast|beadblasted|beadblast|sand blasted|sandblasted|sandblast|sand blast|grit blasted|grit blast|blasted|media blasted|etched|etching|etched metal|acid etched|frosted metal|matte metal|satin metal',
  'Bead-blasted metal is an evenly rough, fine-grain matte metal surface.', tags=['blasted', 'metal'], name='blast|etch|bead|grit|sand', words='blast|etch|bead|grit', n=5, fin=['base::f_bead_blast'], rel=['hammered_metal', 'matte_look'])
A('pixel_look', 'Pixel / digital / glitch', 'pixel|pixels|pixelated|pixel art|8 bit|8bit|16 bit|retro game|retro gaming|arcade|digital|digital look|glitch|glitchy|glitched|datamosh|binary|matrix|code|ascii|scanline|scanlines|crt|vhs|halftone|half tone|dots|dot pattern|benday|ben day|comic|comic book|pop art dots|lichtenstein|screen print',
  'Pixel and digital finishes cover pixel art, glitches, scanlines and comic halftone dots.', tags=['scanline', 'cells'], name='pixel|digital|glitch|scanline|matrix|halftone|comic|dot|binary|arcade|vhs|crt', words='pixel|glitch|scanline|halftone|comic|dot|binary|arcade|matrix', n=6, rel=['neon', 'geometric'])
A('swirl_look', 'Swirl / marbling / smoke', 'swirl|swirls|swirly|swirled|marbled paint|paint pour|pour|pouring|fluid art|fluid|flow|flowing|smoke|smoky|smokey|smoked|cloud|clouds|cloudy|mist|misty|fog|foggy|steam|vapor|vapour|haze|hazy|ink|ink drop|watercolor|watercolour|splatter|splatters|splash paint|paint splatter|drip|drips|dripping|paint drip|graffiti|spray paint|spray|airbrush|airbrushed|air brush',
  'Swirl finishes look like poured paint, smoke or ink flowing across the car.', tags=['swirl', 'streak', 'drift'], name='swirl|pour|smoke|cloud|mist|fog|ink|splatter|drip|graffiti|spray|airbrush|watercolo|flow|marbl', words='swirl|pour|smoke|cloud|ink|splatter|drip|graffiti|airbrush|flow', n=6, rel=['marble', 'galaxy'])
A('police_look', 'Emergency / police / safety', 'police|cop|cop car|patrol|patrol car|sheriff|state trooper|trooper|ambulance|fire truck|fire engine|firetruck|rescue|emergency|emergency lights|taxi|cab|school bus|safety|safety yellow|high vis|high visibility|hi vis|hi-vis|hazard|hazard stripes|caution|caution stripes|warning|construction|reflective tape|retroreflective|reflective stripes',
  'Emergency and safety finishes use reflective tape, hazard stripes and service-vehicle colours.', tags=['emergency', 'tactical', 'reflective'], name='police|emergency|hazard|caution|reflective|safety|hi vis', words='police|emergency|hazard|reflective|safety|hi vis', n=5, rel=['stripes', 'tactical'])
A('tactical', 'Tactical / military', 'tactical|combat|operator|swat|special forces|military look|desert tan|flat dark earth|fde|coyote|coyote tan|od green|olive drab|ranger green|cerakote tan|gunmetal tactical|battlefield|warzone|bunker|armored|armoured|armor|armour|armor plate|armour plate|steel plate|bullet|bullet holes|bullet hole',
  'Tactical finishes are flat, field-ready military coatings: olive drab, desert tan and cerakote greys.', tags=['tactical', 'military'], name='tactical|military|olive|desert|coyote|ranger|combat|armor|armour|bullet', words='tactical|military|olive|coyote|combat|armor', n=5, rel=['camo', 'matte_look'])
A('sunset_look', 'Sunset / sunrise', 'sunset|sunsets|sunrise|sunrises|dawn|dusk|twilight|golden hour|sun|sunny|sunburst|sun rays|rays|sunshine|summer|beach|miami|miami vice|malibu|tropical sunset|orange sky|horizon|ombre sunset|palm sunset',
  'Sunset finishes blend orange, pink and purple like a sky at dusk.', tags=['sunset', 'sun', 'gradient', 'warm'], name='sunset|sunrise|dawn|dusk|twilight|sun|miami|horizon|summer|beach', words='sunset|sunrise|dawn|dusk|sun|miami|horizon', n=5, rel=['gradient_look', 'neon'])
A('gradient_look', 'Gradient finishes', 'gradient finish|gradient finishes|colour fade finish|color fade finish|rainbow fade|rainbow gradient|spectrum|spectrum shift|colour gradient|color gradient|ombre finish|fade finish',
  'Gradient finishes are ready-made colour fades from one end of the car to the other.', tags=['gradient'], name='gradient|fade|ombre|spectrum|shift', words='gradient|fade|ombre|spectrum', n=6, rel=['sunset_look', 'iridescent'])
A('streaks_look', 'Speed streaks / motion', 'streaks|streak|speed lines|speedlines|speed line|motion|motion blur|speed|fast|racing look|racy|aggressive|aggressive look|slash|slashes|slashed|scratches|scratch|scratched|claw|claws|claw marks|swoosh|swooshes|swoosh stripe|stripe sweep|sweep|sweeping|tape stripes',
  'Streak finishes run fine speed lines or slashes along the car, so it looks fast standing still.', tags=['streaks-h', 'streaks-v', 'streak', 'scratches', 'racing', 'hot-edge'], name='streak|speed|motion|slash|scratch|claw|swoosh|sweep|slice|blade|hot edge', words='streak|speed|motion|slash|scratch|swoosh|sweep', n=6, rel=['stripes', 'carbon_fiber'])

# stripes and other tags used above as related ids that map to flows/info must resolve; the generator drops unknown related ids and reports them.

I('foundation', 'Foundation finishes', 'foundation|foundation finish|foundation finishes|foundation base|foundation bases|keep source paint|source paint spec only|use source paint|spec only finish|f chrome|efx|enhanced foundation',
  'Foundation finishes change only the shine and keep your paint colours exactly as they are.',
  ['Use one with "Use source paint (spec only)" to add chrome, metal or matte without repainting.', 'Other finishes (candy, pearl, patterns) repaint the car.'],
  ['help:keep_paint', 'doc:GETTING_STARTED.html#Bases'], ['spec', 'finish', 'chrome_family'])
I('pop', 'Make it pop', 'pop|pops|popping|stand out|stands out|accentuate|emphasize|emphasise|more contrast|contrast|punch up|punch it up|jazz up|jazz it up|spice up|liven up|make it zing|zing',
  'To make a car pop, add contrast: pair a colour with its opposite and let the shine do the sparkle.',
  ['A bright accent on a dark body, or a fine-detail spec pattern, lifts a plain car fast.'], ['help:spec_pattern', 'help:intensity'], ['spec', 'colour', 'stripes'])

I('effects', 'Layer effects (shadow, glow, bevel)', 'drop shadow|outer glow|glow effect|bevel|bevel and emboss|emboss|stroke effect|layer effect|layer effects|color overlay|colour overlay|fx',
  'Layer effects add a drop shadow, outer glow, stroke, colour overlay or bevel to a layer, like in an image editor.',
  ['They shape how a logo or number reads on the paint.'], ['control:fxDropShadowEnabled', 'control:fxOuterGlowEnabled', 'control:fxStrokeEnabled', 'control:fxBevelEnabled'], ['sponsor', 'layer'])
I('selection_mask', 'Selection & masks', 'mask|masks|selection mask|invert mask|copy mask|grow selection|shrink selection|marquee|elliptical marquee|rectangle select|select all|deselect|selection tools',
  'A selection or mask limits where a change lands. Draw one with the wand, lasso, rectangle or brush tools.',
  ['Feather softens its edge; grow and shrink resize it.'], ['control:selectionMode', 'control:selectionFeather', 'control:wandTolerance', 'control:vtModeRect', 'control:vtModeEllipseMarquee'], ['zone', 'tolerance'])
I('image_adjust', 'Blur, sharpen & adjustments', 'blur|sharpen|vibrance|grayscale|greyscale|black and white|adjust|adjustments|curves|levels|brightness contrast|desaturate paint|invert|invert colours|invert colors',
  'Image tools like blur, sharpen and brightness work on the pixels of a layer; for finishes use zones instead.',
  [], ['control:blurSharpenStrength', 'control:brushOpacity'], ['paint_bucket', 'hue_sat_bright'])
I('shortcuts', 'Keyboard shortcuts', 'shortcut|shortcuts|keyboard shortcut|keyboard shortcuts|hotkey|hotkeys|key bindings|keybindings|f5|refresh preview',
  'Keyboard shortcuts are listed under the Settings gear. F5 rebuilds the preview.', [], ['support:preview_failed', 'control:settingsGearBtn', 'control:btnPreviewRefresh'], ['settings'])
