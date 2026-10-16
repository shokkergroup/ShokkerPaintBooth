// Source-backed FAQ references adopted from batches85,95,96,97. No answer text or action data.
(function(W){"use strict";W.SpbOfflineFactRoutes={
  "85": [
    {
      "key": "shape-colour",
      "id": "zones.coverage_truth_shape",
      "q": "Why can a drawn material apply-area shape still affect only my picked colour?",
      "patterns": [
        "\\b(?:box|shape|drawn area)\\b",
        "\\b(?:picked|selected|pick)\\b",
        "\\bcolou?r\\b"
      ]
    },
    {
      "key": "preview-edge",
      "id": "zones.coverage_truth_restriction",
      "q": "Why can fine layer edges differ between a reduced preview and full size?",
      "patterns": [
        "\\b(?:thin|fine|edge|grille)\\b",
        "\\b(?:small|reduced|preview)\\b",
        "\\b(?:disappear|coverage|differ|vanish)"
      ]
    },
    {
      "key": "invalid-restriction",
      "id": "zones.coverage_truth_restriction",
      "q": "Why does an invalid layer restriction paint nothing instead of the whole car?",
      "patterns": [
        "\\b(?:invalid|malformed|broken)\\b",
        "\\b(?:restriction|mask)\\b"
      ]
    },
    {
      "key": "alpha-pick",
      "id": "zones.coverage_truth_colour",
      "q": "Why is a nearly transparent layer pixel not picked for my material colour zone?",
      "patterns": [
        "\\b(?:transparent|translucent|low alpha|nearly invisible)\\b",
        "\\b(?:pick|picked|select|selection|match)"
      ]
    },
    {
      "key": "remaining-local",
      "id": "zones.coverage_truth_remaining",
      "q": "Does Remaining inside a numbers layer mean every unpainted part of the car?",
      "patterns": [
        "\\bremaining\\b",
        "\\b(?:restricted|numbers|logo|layer)\\b",
        "\\b(?:whole|every|car|local)\\b"
      ]
    },
    {
      "key": "template-share",
      "id": "recipes.team_liveries",
      "q": "Does Save as Template transfer my team scheme to another computer?",
      "patterns": [
        "\\btemplate\\b",
        "\\b(?:share|cloud|computer|teammate|sync)"
      ]
    },
    {
      "key": "template-mask",
      "id": "recipes.team_liveries",
      "q": "Does loading a Zone template preserve my exact painted masks and layer restrictions?",
      "patterns": [
        "\\btemplate\\b",
        "\\b(?:mask|restriction|painted area)"
      ]
    },
    {
      "key": "template-replace",
      "id": "recipes.team_liveries",
      "q": "Does Load Template append the team settings to the zones I already have?",
      "patterns": [
        "\\btemplate\\b",
        "\\b(?:append|replace|existing zones|current zones)"
      ]
    },
    {
      "key": "template-art",
      "id": "recipes.team_liveries",
      "q": "Does the saved team Zone template include each driver Customer ID or the car artwork?",
      "patterns": [
        "\\btemplate\\b",
        "\\b(?:customer id|driver id|artwork|car art)"
      ]
    },
    {
      "key": "template-modern",
      "id": "recipes.team_liveries",
      "q": "Does a loaded team Zone template reproduce all my current Base and Spec settings?",
      "patterns": [
        "\\btemplate\\b",
        "\\b(?:independent spec|modern spec|spec scale|imported source|all.*settings)"
      ]
    },
    {
      "key": "holo-metal",
      "id": "recipes.holographic",
      "q": "Does variation in R METAL prove holographic shimmer is visible on the car?",
      "patterns": [
        "\\b(?:holo|holographic)\\b",
        "\\b(?:metal|metallic|r metal)\\b",
        "\\b(?:variation|vary|shimmer|prove)"
      ]
    },
    {
      "key": "holo-strength",
      "id": "recipes.holographic",
      "q": "Is holographic overlay strength 80 a verified ideal setting?",
      "patterns": [
        "\\b(?:holo|holographic)\\b",
        "\\b(?:80|ideal strength|best strength)\\b"
      ]
    },
    {
      "key": "holo-rainbow",
      "id": "recipes.holographic",
      "q": "Does a holographic spec overlay contain a rainbow paint image?",
      "patterns": [
        "\\b(?:holo|holographic)\\b",
        "\\b(?:spec|material)\\b",
        "\\b(?:rainbow|paint image|colou?r image)\\b"
      ]
    },
    {
      "key": "flake-preserve",
      "id": "recipes.flake_pearl",
      "q": "Is Holo Flake guaranteed to keep exact sponsor colours?",
      "patterns": [
        "\\b(?:holo flake|holographic flake)\\b",
        "\\b(?:exact|preserve|unchanged|sponsor)\\b"
      ]
    },
    {
      "key": "flake-scale",
      "id": "recipes.flake_pearl",
      "q": "Should I lower Base Scale to fix every oversized flake overlay?",
      "patterns": [
        "\\b(?:flake|glitter)\\b",
        "\\b(?:base scale|independent.*scale|overlay.*scale)\\b"
      ]
    },
    {
      "key": "gradient-half",
      "id": "finishes.material_gradient_truth_paint_protection",
      "q": "What happens to my colours at half gradient paint amount?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:half|50 percent)\\b",
        "\\b(?:colou?r|paint|amount)"
      ]
    },
    {
      "key": "gradient-shades",
      "id": "finishes.material_gradient_truth_profile_limits",
      "q": "Does every gradient really contain eight spec shades after export?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:eight|8)\\b",
        "\\b(?:shades|tiers|export|occupied)\\b"
      ]
    },
    {
      "key": "gradient-replace",
      "id": "finishes.material_gradient_truth_paint_protection",
      "q": "Does full gradient paint amount completely replace my existing RGB?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:full|100|one hundred)\\b",
        "\\b(?:replac\\w*|rgb|paint amount)\\b"
      ]
    },
    {
      "key": "gradient-boundary",
      "id": "finishes.material_gradient_truth_paint_protection",
      "q": "Will a soft gradient mask leave the boundary colour unchanged?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:soft|feathered)\\b",
        "\\b(?:boundary|edge)\\b"
      ]
    },
    {
      "key": "gradient-native",
      "id": "finishes.material_gradient_truth_resolution_and_mask",
      "q": "Are gradient fine details calculated directly at every native 2048 pixel?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:2048|native pixel|native resolution)\\b",
        "\\b(?:detail|calculated|compute|resolution)"
      ]
    },
    {
      "key": "retired-tricoat",
      "id": "recipes.named_looks",
      "q": "Can I select Tri-Coat Pearl by asking the AI when it is missing from the picker?",
      "patterns": [
        "\\btri[ -]?coat pearl\\b",
        "\\b(?:missing|picker|select|ai|available)\\b"
      ]
    },
    {
      "key": "retired-carbon",
      "id": "recipes.named_looks",
      "q": "Can I select Forged Carbon Visible by asking the AI when it is missing from the picker?",
      "patterns": [
        "\\bforged carbon visible\\b",
        "\\b(?:missing|picker|select|ai|available)\\b"
      ]
    },
    {
      "key": "retired-composite",
      "id": "recipes.named_looks",
      "q": "Can I select Forged Composite by asking the AI when it is missing from the picker?",
      "patterns": [
        "\\bforged composite\\b",
        "\\b(?:missing|picker|select|ai|available)\\b"
      ]
    },
    {
      "key": "retired-anodized",
      "id": "recipes.named_looks",
      "q": "Can I select Anodized by asking the AI when it is missing from the picker?",
      "patterns": [
        "\\banodized\\b(?!\\s+gloss\\b)",
        "\\b(?:missing|picker|select|ai|available)\\b"
      ]
    },
    {
      "key": "absent-rally",
      "id": "recipes.named_looks",
      "q": "Can I select Rally Mud by asking the AI when it is missing from the picker?",
      "patterns": [
        "\\brally mud\\b",
        "\\b(?:missing|picker|select|ai|available)\\b"
      ]
    }
  ],
  "95": [
    {
      "key": "b90-region",
      "id": "zones.practical_reset_scope",
      "q": "Will Reset Zone preserve my drawn lasso or brush area?",
      "patterns": [
        "\\breset\\b",
        "\\b(?:outline|mask|drawn)\\b"
      ]
    },
    {
      "key": "b90-restore",
      "id": "zones.practical_link_limits",
      "q": "Does unlinking restore the different finishes I had before linking?",
      "patterns": [
        "\\bunlink",
        "\\b(?:old|previous|restore|back)\\b"
      ]
    },
    {
      "key": "b90-fit-lock",
      "id": "patterns.practical_target_controls",
      "q": "Why are the pattern position controls disabled in Fit to Zone?",
      "patterns": [
        "\\bfit\\b",
        "\\b(?:grey|gray|disabled|offset|x|y)\\b"
      ]
    },
    {
      "key": "b90-offset",
      "id": "patterns.practical_target_controls",
      "q": "Do the pattern X and Y sliders move my imported sponsor artwork layer?",
      "patterns": [
        "\\bpattern\\b",
        "\\b(?:logo|sponsor|artwork)\\b",
        "\\b(?:x|y|offset|move|moving|moved)\\b"
      ]
    },
    {
      "key": "b91-plural-practical_merge_identity",
      "id": "layers.practical_merge_identity",
      "q": "Does Merge Visible migrate every entry in a multi-layer Zone restriction?",
      "patterns": [
        "\\bmerge\\b",
        "\\bvisible\\b",
        "\\b(?:multi|multiple|array|targets?|sourceLayers)\\b"
      ]
    },
    {
      "key": "b91-warning",
      "id": "layers.practical_flatten_limits",
      "q": "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
      "patterns": [
        "\\bflatten",
        "\\b(?:warning|warn|alert)\\b",
        "\\b(?:array|multiple|multi|targets?)\\b"
      ]
    },
    {
      "key": "b91-hidden",
      "id": "layers.practical_flatten_limits",
      "q": "Will Flatten document keep hidden layers for later editing?",
      "patterns": [
        "\\bflatten",
        "\\b(?:hidden|backup)\\b"
      ]
    },
    {
      "key": "b91-effects",
      "id": "layers.practical_png_export_limits",
      "q": "Does Export on a layer card include its drop shadow and stroke styles?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:shadow|effects?)\\b"
      ]
    },
    {
      "key": "b91-opacity",
      "id": "layers.practical_png_export_limits",
      "q": "Does layer PNG export bake the card’s opacity percentage?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:opacity|translucent|semitransparent)\\b"
      ]
    },
    {
      "key": "b91-blend",
      "id": "layers.practical_png_export_limits",
      "q": "Will a Multiply layer PNG look exactly like its appearance over the body paint?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:multiply|blend mode|background)\\b"
      ]
    },
    {
      "key": "b91-download",
      "id": "layers.practical_png_export_limits",
      "q": "Does a successful layer Export return prove the PNG was saved in my chosen folder?",
      "patterns": [
        "\\b(?:png|export|download)\\b",
        "\\b(?:success|successful|said|says)\\b",
        "\\b(?:file|folder|disk|saved)\\b"
      ]
    },
    {
      "key": "b91-position",
      "id": "layers.practical_png_export_limits",
      "q": "Does a single-layer PNG retain the layer’s absolute position on the template?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:position|origin|coordinates?|alignment)\\b"
      ]
    },
    {
      "key": "b92-origin",
      "id": "spec.presets_feels",
      "q": "Are my saved Feels synchronized with my account or another localhost port?",
      "patterns": [
        "\\b(?:feel|presets?)\\b",
        "\\b(?:saved|save)\\b",
        "\\b(?:gone|missing|reopen|browser|origin|device)\\b"
      ]
    },
    {
      "key": "b92-collision",
      "id": "spec.presets_feels",
      "q": "Why does my saved Feel named Wet Candy apply the built-in values instead?",
      "patterns": [
        "\\b(?:feel|preset|WetCandy)\\b",
        "\\b(?:same name|named|name|collision)\\b",
        "\\b(?:wrong|builtin|built-in|original|sliders|different)\\b"
      ]
    },
    {
      "key": "b92-delete-state",
      "id": "spec.presets_feels",
      "q": "Will deleting a saved Feel undo it on Zones that already used it?",
      "patterns": [
        "\\b(?:feel|presets?)\\b",
        "\\b(?:delete|deleted|deleting)\\b",
        "\\b(?:unchanged|restore|still|back|revert)\\b"
      ]
    },
    {
      "key": "b92-saturation",
      "id": "spec.auto_pop",
      "q": "Can Auto-Pop report a boost when my shift slider is already at its limit?",
      "patterns": [
        "\\bAuto\\s?Pop\\b",
        "(?:127|\\b(?:limit|clamp|saturat|toast))"
      ]
    },
    {
      "key": "b92-post-pass",
      "id": "spec.presets_feels",
      "q": "Can later material controls override the channel values suggested by a Feel?",
      "patterns": [
        "\\b(?:override|remap|Flake Studio)\\b",
        "\\b(?:sliders?|shift|Feel)\\b",
        "\\b(?:ignored|different|not|overwrite|overrule)\\b"
      ]
    },
    {
      "key": "b93-lab-retained",
      "id": "finishes.practical_colour_picker_modes",
      "q": "Does choosing Solid Color switch off Depth, Flip and Underglow I already enabled?",
      "patterns": [
        "\\b(?:solid|plain)\\b",
        "\\b(?:old candy|candy treatment|depth|flip|underglow)\\b"
      ]
    },
    {
      "key": "b93-blank-white",
      "id": "finishes.practical_colour_picker_modes",
      "q": "Does clearing the committed Base Color hex field mean “keep source colour”?",
      "patterns": [
        "\\b(?:hex|colour field|color field)\\b",
        "\\b(?:clear|cleared|blank|empty)\\b",
        "\\b(?:source|white|original)\\b"
      ]
    },
    {
      "key": "b93-one-percent",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "Can a gradient list containing only positions0 and1 unambiguously mean a one-percent interval?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:stop|position)\\b",
        "\\b(?:one percent|1percent|one-percent|far end|fraction)\\b"
      ]
    },
    {
      "key": "b93-add-position",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "Where does Add Gradient Stop place a new colour?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:add|adding|added|new)\\b",
        "\\b(?:grey|gray|midpoint|gap|strange place)\\b"
      ]
    },
    {
      "key": "b93-css-proof",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "Does the gradient bar prove the exact rendered RGB of my material on the car?",
      "patterns": [
        "\\b(?:gradient bar|little gradient|CSS bar)\\b",
        "\\b(?:render|match|material|car|output)\\b"
      ]
    },
    {
      "key": "b94-sample-current-target",
      "id": "spec.practical_sampled_material_limits",
      "q": "If I select another Zone after sampling, which Zone receives the sampled material?",
      "patterns": [
        "\\b(?:sample|sampled|sampler)\\b",
        "\\b(?:another|different|switched|switch)\\b",
        "\\bzone\\b"
      ]
    },
    {
      "key": "b94-sample-retains-remap",
      "id": "spec.practical_sampled_material_limits",
      "q": "Does applying a flat sample delete my earlier remap settings?",
      "patterns": [
        "\\b(?:sample|sampled)\\b",
        "\\b(?:removed|remove|clear|cleared|clearing)\\b",
        "\\b(?:range|remap)\\b"
      ]
    },
    {
      "key": "sample-alpha-copy",
      "id": "spec.material_override_remap_lighting",
      "q": "Does material override change alpha?",
      "patterns": [
        "\\b(?:sample|sampled|copied|copy)\\b",
        "\\b(?:alpha|lighting)\\b",
        "\\b(?:255|changed|went|replace|overrid)"
      ]
    }
  ],
  "96": [
    {
      "key": "b87-busy-separate",
      "id": "support.preview_render_mismatch",
      "q": "Does Server busy count as an ordinary failed preview retry?",
      "patterns": [
        "\\b(?:busy|queued)\\b",
        "\\b(?:retry|tries|attempts|two|2)\\b"
      ]
    },
    {
      "key": "b87-refresh-visible",
      "id": "support.preview_render_mismatch",
      "q": "Why can Refresh switch the canvas from Source to the rendered view?",
      "patterns": [
        "\\b(?:refresh|retry)\\b",
        "\\b(?:old|previous|stale)\\b",
        "\\b(?:visible|image|preview)\\b"
      ]
    },
    {
      "key": "b87-timeout-client",
      "id": "support.render_slow_or_fails",
      "q": "Is the five-minute render timeout a guaranteed engine completion limit?",
      "patterns": [
        "\\b(?:timeout|timed out)\\b",
        "\\b(?:engine|server|finished|stopped|running)\\b"
      ]
    },
    {
      "key": "b87-abort-vs-timeout",
      "id": "support.render_slow_or_fails",
      "q": "Should a cancelled request and a timeout get the same troubleshooting answer?",
      "patterns": [
        "\\b(?:cancel|cancelled|abort|aborted)\\b",
        "\\b(?:timeout|retry|retries)\\b"
      ]
    },
    {
      "key": "b87-busy-not-offline",
      "id": "support.render_slow_or_fails",
      "q": "Does a server-busy preview mean the engine is offline?",
      "patterns": [
        "(?:\\bbusy|503)",
        "\\b(?:offline|disconnected|network)\\b"
      ]
    },
    {
      "key": "b88-alpha-preserved",
      "id": "spec_sculpt.iron_safe_export",
      "q": "Does iron-safe export force every spec alpha byte to 255?",
      "patterns": [
        "\\b(?:Iron.?Safe|safe export)\\b",
        "\\balpha",
        "(?:127|255|\\b(?:preserv|replace))"
      ]
    },
    {
      "key": "b88-writer-size",
      "id": "spec_sculpt.iron_safe_export",
      "q": "Does the low-level Spec Sculpt TGA writer itself enforce a 2048-square size?",
      "patterns": [
        "\\b(?:writer|export)\\b",
        "(?:2048|\\b(?:dimensions|size)\\b)",
        "\\b(?:accept|validate|enforc|check|mandatory)"
      ]
    },
    {
      "key": "b88-gpu-not-proof",
      "id": "preview_render.render_stats_overlay",
      "q": "Does a GPU name in Render Statistics prove every finish ran on the GPU?",
      "patterns": [
        "\\bGPU\\b",
        "\\b(?:label|stats|statistic)\\b",
        "\\b(?:prove|proof|every|finish|render)\\b"
      ]
    },
    {
      "key": "b89-make-no-material",
      "id": "layers.lock_zone_to_layer",
      "q": "Does MAKE ZONE copy the selected layer’s material into the new zone?",
      "patterns": [
        "\\b(?:make zone|made a zone|created a zone)\\b",
        "\\b(?:layer|sponsor|logo)\\b",
        "\\b(?:chrome|material|finish)\\b"
      ]
    },
    {
      "key": "b89-coordinate-not-door",
      "id": "recipes.mirror_side",
      "q": "Does mirroring one side guarantee the copy lands on the opposite door for this car?",
      "patterns": [
        "\\bmirror",
        "\\b(?:door|side|panel)\\b",
        "\\b(?:position|alignment|calibrat|physical|wrong)"
      ]
    },
    {
      "key": "b89-mask-not-art",
      "id": "recipes.mirror_side",
      "q": "Does Mirror Mask duplicate and flip the sponsor image layer too?",
      "patterns": [
        "\\bmirror",
        "\\b(?:region|mask)\\b",
        "\\b(?:logo|artwork|layer)\\b"
      ]
    },
    {
      "key": "b89-paint-vs-spec",
      "id": "layers.lock_zone_to_layer",
      "q": "Will a layer-restricted source-paint material leave that logo’s reflected appearance identical?",
      "patterns": [
        "\\b(?:source paint|source mode)\\b",
        "\\b(?:sponsor|logo|numbers?)\\b",
        "\\b(?:shine|spec|material|shiny)\\b"
      ]
    },
    {
      "key": "b91-crop",
      "id": "layers.practical_png_export_limits",
      "q": "Why is my exported layer PNG smaller than the full car template?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:cropped|crop|bounding|full canvas|small image)\\b"
      ]
    },
    {
      "key": "b91-hsb",
      "id": "layers.practical_png_export_limits",
      "q": "Are Hue/Saturation adjustments included in the standalone layer PNG?",
      "patterns": [
        "\\b(?:png|export)\\b",
        "\\b(?:HSB|hue|saturation|brightness)\\b"
      ]
    },
    {
      "key": "b92-preview",
      "id": "spec.auto_pop",
      "q": "Can Auto-Pop work from the paint image when no spec preview has loaded?",
      "patterns": [
        "\\bAuto\\s?Pop\\b",
        "\\b(?:old|stale|spinning|current|refresh)\\b",
        "\\b(?:preview|image|render)\\b"
      ]
    },
    {
      "key": "b92-mask-dimensions",
      "id": "spec.auto_pop",
      "q": "Does Auto-Pop always restrict analysis to my drawn Zone region?",
      "patterns": [
        "\\bAuto\\s?Pop\\b",
        "\\bmask\\b",
        "\\b(?:size|dimensions|length|whole car|mismatch)\\b"
      ]
    },
    {
      "key": "b92-selector",
      "id": "spec.auto_pop",
      "q": "Does Auto-Pop resolve my sponsor layer and colour picks into the analyzer mask?",
      "patterns": [
        "\\bAuto\\s?Pop\\b",
        "\\b(?:sponsor|layer|colour|color)\\b",
        "\\b(?:only|restrict(?:ions?)?|selection|whole)\\b"
      ]
    },
    {
      "key": "b92-mean-label",
      "id": "spec.auto_pop",
      "q": "Why can Auto-Pop suggest shifts even when the analyzer label describes mixed materials?",
      "patterns": [
        "\\bAuto\\s?Pop\\b",
        "\\b(?:median|mean|average)\\b"
      ]
    },
    {
      "key": "b92-writefail",
      "id": "spec.presets_feels",
      "q": "Does the Saved spec preset toast prove it will survive closing the app?",
      "patterns": [
        "\\b(?:feel|preset)\\b",
        "\\b(?:saved|save)\\b",
        "\\b(?:storage|write|blocked|quota|toast)\\b"
      ]
    },
    {
      "key": "b93-hex-paths",
      "id": "finishes.practical_colour_picker_modes",
      "q": "Why can a short hex colour work in a gradient payload but fail in the Base Color input?",
      "patterns": [
        "\\b(?:hex|three-digit|six-digit|short hex)\\b",
        "\\b(?:Base Color|Base Colour|gradient)\\b",
        "\\b(?:work|fail|accept|valid)"
      ]
    },
    {
      "key": "b93-picker-vs-base",
      "id": "finishes.practical_colour_picker_modes",
      "q": "Why does picking a colour sometimes change the selected pixels rather than repaint them?",
      "patterns": [
        "\\b(?:picked|picker|pick)\\b",
        "\\bcolou?r\\b",
        "\\b(?:selected|selection|zone|part)\\b",
        "\\b(?:different|changed|tint|painted)\\b"
      ]
    },
    {
      "key": "b93-empty-source",
      "id": "finishes.practical_colour_picker_modes",
      "q": "Does clearing the Special Color source automatically return to Source mode?",
      "patterns": [
        "\\b(?:special|colour source|color source)\\b",
        "\\b(?:clear|cleared|empty|removed)\\b",
        "\\b(?:mode|still|remains|label)\\b"
      ]
    },
    {
      "key": "b94-inspector-pending",
      "id": "spec.practical_sampled_material_limits",
      "q": "Why does sampling refuse while the Inspector is pending even if an old spec image is visible?",
      "patterns": [
        "\\b(?:sampler|sampling|sample)\\b",
        "\\bInspector\\b",
        "\\b(?:pending|loading|old image|waiting)\\b"
      ]
    },
    {
      "key": "b94-copy-only",
      "id": "spec.practical_sampled_material_limits",
      "q": "Does Copy Material Sample create a portable texture preset or apply anything to the Zone?",
      "patterns": [
        "\\b(?:copy|copied|copying)\\b",
        "\\b(?:material sample|sampled material)\\b",
        "\\b(?:texture|preset|recipe|portable)\\b"
      ]
    },
    {
      "key": "b94-failed-click-old-sample",
      "id": "spec.practical_sampled_material_limits",
      "q": "Can clicking outside the spec image accidentally leave the previous material sample active?",
      "patterns": [
        "\\b(?:sample|sampler|sampling)\\b",
        "\\b(?:outside|missed|failed click)\\b",
        "\\b(?:previous|old|still|kept|keep)\\b"
      ]
    }
  ],
  "97": [
    {
      "key": "b89-replace-target",
      "id": "layers.lock_zone_to_layer",
      "q": "Does setting one source layer append it to the zone’s earlier restrictions?",
      "patterns": [
        "\\b(?:layer target|source.?layers?|restriction)\\b",
        "\\b(?:new|another|second|replace|append)\\b"
      ]
    },
    {
      "key": "b89-clear-broadens",
      "id": "layers.lock_zone_to_layer",
      "q": "Does clearing a source-layer restriction keep the zone confined to that artwork?",
      "patterns": [
        "\\b(?:layer target|layer restriction|source.?layer)\\b",
        "\\b(?:clear|cleared|clearing|remove|removed|removing)\\b",
        "\\b(?:broader|everywhere|whole|area|coverage)\\b"
      ]
    },
    {
      "key": "b89-id-not-name",
      "id": "layers.lock_zone_to_layer",
      "q": "Can I safely choose a layer just because it has the expected sponsor name?",
      "patterns": [
        "\\blayers?\\b",
        "\\b(?:same name|identical name|renamed|names?)\\b",
        "\\b(?:identity|id|target|restriction)\\b",
        "\\b(?:zone|restriction|target|stored)\\b"
      ]
    },
    {
      "key": "b89-summary-not-mask",
      "id": "layers.lock_zone_to_layer",
      "q": "Does seeing a source-layer name prove the zone has valid nonempty coverage?",
      "patterns": [
        "\\b(?:target summary|source layer summary|restriction summary)\\b",
        "\\b(?:coverage|mask|outline|pixels?)\\b"
      ]
    },
    {
      "key": "b89-role-guesses",
      "id": "layers.colourway_studio",
      "q": "Does Colourway Studio know which layers are logos without inspecting their contents?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\b(?:roles?|names?|classif|guess)"
      ]
    },
    {
      "key": "b89-numbers-default",
      "id": "layers.colourway_studio",
      "q": "Are all number layers automatically protected from Colourway Studio recolouring?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\bnumbers?\\b",
        "\\b(?:default|protected|protect|changed)\\b"
      ]
    },
    {
      "key": "b89-hidden-protection",
      "id": "layers.colourway_studio",
      "q": "Does a hidden protected layer contribute protection to the current visible colourway composite?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\bhidden\\b",
        "\\b(?:sponsor|logo|protect)"
      ]
    },
    {
      "key": "b89-overlap-protection",
      "id": "layers.colourway_studio",
      "q": "Is Colourway Studio’s protection mask just a solid rectangle around each logo?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\b(?:overlap|overlapping|above|occlu)"
      ]
    },
    {
      "key": "b89-include-clears",
      "id": "layers.colourway_studio",
      "q": "What does including sponsors and logos do to the protected-ID list?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\binclude\\b",
        "\\b(?:sponsor|logo|protect)"
      ]
    },
    {
      "key": "b89-snapshot-limits",
      "id": "layers.colourway_studio",
      "q": "Does the colourway Zone snapshot store every mask and spec setting?",
      "patterns": [
        "\\b(?:Zone.?Snap|colourway snapshot|colorway snapshot)\\b",
        "\\b(?:project|backup|mask|complete|entire|full)"
      ]
    },
    {
      "key": "b89-restore-identity",
      "id": "layers.colourway_studio",
      "q": "Will a colourway restore always match zones after I rename or reorder them?",
      "patterns": [
        "\\b(?:Zone.?Snap|colourway snapshot|colorway snapshot)\\b",
        "\\b(?:restore|restored|reorder|reordered|identity)"
      ]
    },
    {
      "key": "b89-materials-optional",
      "id": "layers.colourway_studio",
      "q": "Does trying a colourway always replace every zone’s finish?",
      "patterns": [
        "\\bcolou?rway\\b",
        "\\b(?:material|materials)\\b",
        "\\b(?:optional|automatically|every|option|flag)"
      ]
    },
    {
      "key": "b91-union",
      "id": "layers.practical_merge_identity",
      "q": "Why can a sponsor-only Zone cover more artwork after Merge Down?",
      "patterns": [
        "\\bmerge\\b",
        "\\bdown\\b",
        "\\b(?:sponsor|target|footprint|coverage|union)"
      ]
    },
    {
      "key": "b91-identity",
      "id": "layers.practical_merge_identity",
      "q": "Does Merge Down create a new layer or keep the lower layer identity?",
      "patterns": [
        "\\bmerge\\b",
        "\\bdown\\b",
        "\\b(?:identity|id|name|surviv)"
      ]
    },
    {
      "key": "b91-pending",
      "id": "layers.practical_merge_identity",
      "q": "Why does Merge Visible ask me to wait when the layer list already shows names?",
      "patterns": [
        "\\bmerge\\b",
        "\\bvisible\\b",
        "\\b(?:pending|loading|missing image|not loaded)"
      ]
    },
    {
      "key": "b91-groups",
      "id": "layers.practical_merge_identity",
      "q": "Why does Merge Visible refuse a grouped PSD?",
      "patterns": [
        "\\bmerge\\b",
        "\\bvisible\\b",
        "\\b(?:groups?|grouped|hierarchy)\\b"
      ]
    },
    {
      "key": "b92-overwrite",
      "id": "spec.presets_feels",
      "q": "Will saving an existing user Spec Feel name ask before replacing it?",
      "patterns": [
        "\\b(?:feel|preset)\\b",
        "\\b(?:same name|overwrite|overwritten|duplicate name)\\b",
        "\\b(?:save|saved|saving|overwrite|overwritten)\\b"
      ]
    },
    {
      "key": "b92-cache",
      "id": "spec.presets_feels",
      "q": "Why might a preset storage change not appear in an already open editor?",
      "patterns": [
        "\\b(?:feel|preset)\\b",
        "\\b(?:storage|localStorage|cache)\\b",
        "\\b(?:changed|refresh|reread|stale|reload)\\b"
      ]
    },
    {
      "key": "b92-race",
      "id": "spec.presets_feels",
      "q": "What shifts are saved if I change or reorder Zones while the Feel-name dialog is open?",
      "patterns": [
        "\\b(?:feel|preset)\\b",
        "\\b(?:save|saving|name dialog)\\b",
        "\\b(?:reorder|reordered|index|different zone|identity)"
      ]
    },
    {
      "key": "b93-rgb-units",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "What happens if a gradient colour array mixes fractional and byte RGB values?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:RGB|colour array|color array)\\b",
        "\\b(?:mixed|units|fraction|byte|255)"
      ]
    },
    {
      "key": "b93-direction",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "How does the gradient bar treat an unrecognized direction?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:unknown|unrecognized|unsupported|invalid)\\b",
        "\\b(?:direction|right|bar)\\b"
      ]
    },
    {
      "key": "b93-minimum",
      "id": "finishes.practical_gradient_editor_truth",
      "q": "Why cannot I remove another gradient stop when only two remain?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:two|2|minimum)\\b",
        "\\b(?:remove|removing|delete|deleting|remain)"
      ]
    },
    {
      "key": "b94-complete-sample",
      "id": "spec.practical_sampled_material_limits",
      "q": "Can an imported RGB-only material override preserve existing alpha automatically?",
      "patterns": [
        "\\b(?:material override|sampled override|sample)\\b",
        "\\b(?:RGB-only|missing alpha|without alpha|three.channel)"
      ]
    },
    {
      "key": "b94-later-contributors",
      "id": "spec.practical_sampled_material_limits",
      "q": "Is sampled material or remapped texture guaranteed to be the final exported map?",
      "patterns": [
        "\\b(?:sample|sampled|remap|material)\\b",
        "\\bFlake Studio\\b",
        "\\b(?:back on|after|later|replace|changed|right until)"
      ]
    },
    {
      "key": "b94-clipboard-failure",
      "id": "spec.practical_sampled_material_limits",
      "q": "Does a Material sample toast prove that the values reached my clipboard?",
      "patterns": [
        "\\b(?:sample|material)\\b",
        "\\b(?:clipboard|copy)\\b",
        "\\b(?:failed|failure|denied|toast|did not|didn.t)"
      ]
    }
  ],
  "customerDiagnostics": [
    {
      "key": "recovery2-render-average-not-current",
      "article": "preview_render.render_stats_overlay",
      "q": "Can average render and per-zone times tell me whether my current render has completed?",
      "patterns": [
        "\\brender\\b",
        "\\b(?:average|last render|per.zone times?)\\b",
        "\\b(?:current|finished|completion|pending)\\b"
      ]
    },
    {
      "key": "recovery2-mixed-sponsor-layer",
      "article": "layers.lock_zone_to_layer",
      "q": "Can I safely choose a layer just because it has the expected sponsor name?",
      "patterns": [
        "\\blayer\\b",
        "\\bsponsor\\b",
        "\\b(?:merged|body artwork|name[ds]?)\\b",
        "\\b(?:isolat\\w*|safe\\w*|target\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-flip-not-placement",
      "article": "recipes.mirror_side",
      "q": "Will flipping mirrored text back also repair a copy that landed on the wrong panel?",
      "patterns": [
        "\\b(?:logo|text|letter\\w*)\\b",
        "\\b(?:backwards|flipp\\w*|flip)\\b",
        "\\b(?:landed|panel|placement|where)\\b"
      ]
    },
    {
      "key": "recovery2-colourway-partial-finish",
      "article": "layers.colourway_studio",
      "q": "Does trying a colourway always replace every zone’s finish?",
      "patterns": [
        "\\bcolourway\\b",
        "\\bfinish\\b",
        "\\b(?:not|extra|missing|every zone|all zones)\\b"
      ]
    },
    {
      "key": "recovery2-reset-source-target",
      "article": "zones.practical_reset_scope",
      "q": "Does Reset Zone keep its restriction to my sponsor layer?",
      "patterns": [
        "\\breset\\b",
        "\\b(?:sponsor|source.layer)\\b",
        "\\b(?:target\\w*|restrict\\w*|still says)\\b"
      ]
    },
    {
      "key": "recovery2-link-overlay-limits",
      "article": "zones.practical_link_limits",
      "q": "Do linked zones automatically synchronize every modern material and spec overlay?",
      "patterns": [
        "\\b(?:link\\w*|chain icons?)\\b",
        "\\b(?:spec overlay|imported spec|material stack|spec pattern stack)\\b",
        "\\b(?:different|same|synchron\\w*|every|not|yet)\\b"
      ]
    },
    {
      "key": "recovery2-fit-third-base",
      "article": "patterns.practical_target_controls",
      "q": "Does fitting my second Base also fit the third and fourth Bases?",
      "patterns": [
        "\\b(?:base|bases)\\b",
        "\\b(?:fit\\w*|fits)\\b",
        "\\b(?:third|fourth|3rd|4th)\\b"
      ]
    },
    {
      "key": "recovery2-merge-down-broadening",
      "article": "layers.practical_merge_identity",
      "q": "Why can a sponsor-only Zone cover more artwork after Merge Down?",
      "patterns": [
        "\\bmerg\\w*\\b",
        "\\b(?:sponsor|logo|decal)\\b",
        "\\b(?:underneath|cover\\w* more|affect\\w* the paint|broaden\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-flatten-warning-plural",
      "article": "layers.practical_flatten_limits",
      "q": "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
      "patterns": [
        "\\bflatten\\w*\\b",
        "\\b(?:warning|count|no links)\\b",
        "\\b(?:several|multiple|multi.layer|two.layer|source layers)\\b"
      ]
    },
    {
      "key": "recovery2-feel-name-collision",
      "article": "spec.presets_feels",
      "q": "Why does my saved Feel named Wet Candy apply the built-in values instead?",
      "patterns": [
        "\\b(?:feel|preset)\\b",
        "\\bwet candy\\b",
        "\\b(?:custom|saved|my)\\b",
        "\\b(?:different|built.in|instead|applying)\\b"
      ]
    },
    {
      "key": "recovery2-feel-later-override",
      "article": "spec.presets_feels",
      "q": "Can later material controls override the channel values suggested by a Feel?",
      "patterns": [
        "\\b(?:feel|deep gloss|preset)\\b",
        "\\b(?:material override|lighting mask|remap|flake)\\b",
        "\\b(?:still|later|final|control\\w*|override\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-radial-bar-not-door",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Does clicking a radial gradient bar place the new stop at a physical car-panel location?",
      "patterns": [
        "\\b(?:gradient|radial bar)\\b",
        "\\bradial\\b",
        "\\b(?:bar|click)\\b",
        "\\b(?:door|panel|place|position|physical)\\b"
      ]
    },
    {
      "key": "recovery2-stats-load-not-paint",
      "article": "preview_render.render_stats_overlay",
      "q": "Does failing to load statistics mean my paint source or finish is invalid?",
      "patterns": [
        "\\b(?:statistics|stats)\\b",
        "\\b(?:fail\\w*|could not load|cannot load)\\b",
        "\\b(?:paint|source|finish|file)\\b"
      ]
    },
    {
      "key": "recovery2-stats-function-not-button",
      "article": "preview_render.render_stats_overlay",
      "q": "Does having toggleRenderStats prove there is a visible Render Stats button in my editor?",
      "patterns": [
        "togglerenderstats",
        "\\b(?:button|editor)\\b",
        "\\b(?:find|visible|where|mentioned|missing)\\b"
      ]
    },
    {
      "key": "recovery2-feel-reapply-replaces",
      "article": "spec.presets_feels",
      "q": "If I apply a Feel twice, will the second application add another dose?",
      "patterns": [
        "\\bfeel\\b",
        "\\b(?:twice|same|second)\\b",
        "\\b(?:strong|shine|add|dose|double)\\b"
      ]
    },
    {
      "key": "recovery2-feel-not-whole-look",
      "article": "spec.presets_feels",
      "q": "Does saving a Spec Feel store the Base, material stack, scale and Zone mask?",
      "patterns": [
        "\\bfeel\\b",
        "\\bsav\\w*\\b",
        "\\bbase\\b",
        "\\b(?:lost|drawn|region|mask|whole)\\b"
      ]
    },
    {
      "key": "recovery2-merge-editability",
      "article": "layers.practical_merge_identity",
      "q": "Can I still edit the separate strokes and colour adjustments after Merge Down?",
      "patterns": [
        "\\bmerg\\w* down\\b",
        "\\b(?:strokes|colour adjustments|color adjustments|effects)\\b",
        "\\b(?:separate\\w*|edit|old)\\b"
      ]
    },
    {
      "key": "recovery2-flatten-one-layer",
      "article": "layers.practical_flatten_limits",
      "q": "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
      "patterns": [
        "\\bflatten\\w*\\b",
        "\\b(?:one.layer|single.layer)\\b",
        "\\b(?:nothing|broken|no.op|does not|refus\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-gradient-eleven",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Why does the gradient editor refuse an eleventh stop?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:ten|10|eleven|11)\\b",
        "\\bstops?\\b",
        "\\b(?:add|another|refus\\w*|maximum|limit)\\b"
      ]
    },
    {
      "key": "recovery2-gradient-integer-position",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Do gradient position inputs preserve fractional percentages?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:fractional|decimal)\\b",
        "\\bposition\\b",
        "\\b(?:whole|round\\w*|integer)\\b"
      ]
    },
    {
      "key": "recovery2-gradient-duplicate-stops",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Does gradient payload normalization sort and deduplicate overlapping stops?",
      "patterns": [
        "\\bgradient\\b",
        "\\b(?:duplicate|overlap\\w*)\\b",
        "\\b(?:sort\\w*|tidy|order|export)\\b"
      ]
    },
    {
      "key": "recovery2-sampler-current-zone",
      "article": "spec.practical_sampled_material_limits",
      "q": "If I select another Zone after sampling, which Zone receives the sampled material?",
      "patterns": [
        "\\bsampl\\w*\\b",
        "\\b(?:select\\w*|another|different|switched)\\b",
        "\\bzone\\b",
        "\\b(?:appl\\w*|gets|receive\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-sampler-neighborhood",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does an unsupported sampler neighborhood size create a larger averaging window?",
      "patterns": [
        "\\bsampl\\w*\\b",
        "\\b(?:neighborhood|neighbourhood|window)\\b",
        "\\b(?:unsupported|size|larger|bigger)\\b"
      ]
    },
    {
      "key": "recovery2-feel-number-clamp",
      "article": "spec.presets_feels",
      "q": "How are malformed or out-of-range stored Feel numbers applied?",
      "patterns": [
        "\\bfeel\\b",
        "\\b(?:stored|saved)\\b",
        "\\b(?:out.of.range|malformed|nan|invalid)\\b",
        "\\b(?:numbers|channels?|values)\\b"
      ]
    },
    {
      "key": "recovery2-merge-lower-identity",
      "article": "layers.practical_merge_identity",
      "q": "Does Merge Down create a new layer or keep the lower layer identity?",
      "patterns": [
        "\\bmerg\\w* down\\b",
        "\\blower\\b",
        "\\b(?:identity|name|new|fresh)\\b"
      ]
    },
    {
      "key": "recovery2-flatten-confirmation",
      "article": "layers.practical_flatten_limits",
      "q": "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
      "patterns": [
        "\\bflatten\\w*\\b",
        "\\b(?:confirmation|warning|dialog)\\b",
        "\\b(?:unavailable|missing|abort\\w*)\\b"
      ]
    },
    {
      "key": "recovery2-sampler-clipboard-toast",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does a Material sample toast prove that the values reached my clipboard?",
      "patterns": [
        "\\b(?:sample|sampler|material)\\b",
        "\\bclipboard\\b",
        "\\b(?:empty|blank|fail\\w*|denied)\\b"
      ]
    },
    {
      "key": "recovery2-sampler-pending",
      "article": "spec.practical_sampled_material_limits",
      "q": "Why does sampling refuse while the Inspector is pending even if an old spec image is visible?",
      "patterns": [
        "\\b(?:spec|sample|sampler|sampling)\\b",
        "\\b(?:pending|waiting)\\b",
        "\\b(?:old|visible|image)\\b"
      ]
    },
    {
      "key": "recovery2-sampler-copy-not-preset",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does Copy Material Sample create a portable texture preset or apply anything to the Zone?",
      "patterns": [
        "\\bcopy material sample\\b",
        "\\b(?:preset|texture|reusable|grain|finish)\\b"
      ]
    },
    {
      "key": "preset-drawn-mask",
      "article": "zones.practical_named_preset_storage",
      "q": "Why are my drawn regions and spatial masks missing from a named Zone preset?",
      "patterns": [
        "\\bpreset\\b",
        "\\b(?:drawn|region|spatial|brush|lasso)\\b",
        "\\b(?:selection|mask|region|outline)\\b",
        "\\b(?:gone|missing|lost|loaded|load)\\b"
      ]
    },
    {
      "key": "zone-preset-overwrite",
      "article": "zones.practical_named_preset_storage",
      "q": "Which Zone state is saved if I edit Zones while the overwrite confirmation is open?",
      "patterns": [
        "\\bzones?\\b",
        "\\bpreset\\b",
        "\\boverwrite\\b",
        "\\b(?:dialog|confirmation|open)\\b",
        "\\b(?:edited|edit|changed|change|version)\\b"
      ]
    },
    {
      "key": "make-zone-is-coverage",
      "article": "layers.lock_zone_to_layer",
      "q": "Does MAKE ZONE copy the selected layer’s material into the new zone?",
      "patterns": [
        "\\bmake zone\\b",
        "\\b(?:created|made)\\b",
        "\\b(?:material|finish|chrome)\\b"
      ]
    },
    {
      "key": "alpha-not-universal255",
      "article": "spec.channel_a_mask",
      "q": null,
      "patterns": [
        "\\balpha\\b",
        "\\b(?:all|every|must)\\b",
        "\\b255\\b"
      ]
    },
    {
      "key": "single-layer-replaces-list",
      "article": "layers.lock_zone_to_layer",
      "q": "Does setting one source layer append it to the zone’s earlier restrictions?",
      "patterns": [
        "\\b(?:lock(?:ed)?|restrict(?:ed)?)\\b",
        "\\b(?:one|single)\\b",
        "\\blayer\\b",
        "\\b(?:previous|earlier|two|multiple)\\b",
        "\\b(?:target|targets|restriction|restrictions|disappeared|gone)\\b"
      ]
    },
    {
      "key": "mirror-mask-vs-art",
      "article": "recipes.mirror_side",
      "q": "Does Mirror Mask duplicate and flip the sponsor image layer too?",
      "patterns": [
        "\\bmirror(?:ed)?\\b",
        "\\bmask\\b",
        "\\b(?:picture|image|sponsor|logo|artwork)\\b"
      ]
    },
    {
      "key": "colourway-rollback-identity",
      "article": "layers.colourway_studio",
      "q": "Will a colourway restore always match zones after I rename or reorder them?",
      "patterns": [
        "\\bcolo(?:u)?rway\\b",
        "\\bzones?\\b",
        "\\b(?:name|rename|reorder|order)\\b",
        "\\b(?:cancel|restore|preview)\\b"
      ]
    },
    {
      "key": "auto-pop-pending-preview",
      "article": "spec.auto_pop",
      "q": "Should I click Auto-Pop several times before the new preview finishes?",
      "patterns": [
        "\\bauto[- ]?pop\\b",
        "\\b(?:twice|several|again|repeated|repeat)\\b",
        "\\b(?:preview|spinning|pending|finish)\\b"
      ]
    },
    {
      "key": "auto-pop-shift-clamp",
      "article": "spec.auto_pop",
      "q": "Can Auto-Pop report a boost when my shift slider is already at its limit?",
      "patterns": [
        "\\bauto[- ]?pop\\b",
        "\\b(?:127|limit|maximum|max|clamp)\\b",
        "\\b(?:shift|slider|boost|metal)\\b"
      ]
    },
    {
      "key": "auto-pop-layer-mask",
      "article": "spec.auto_pop",
      "q": "Does Auto-Pop resolve my sponsor layer and colour picks into the analyzer mask?",
      "patterns": [
        "\\b(?:auto[- ]?pop|analy[sz]er)\\b",
        "\\b(?:sponsor|layer|colo(?:u)?r pick)\\b",
        "\\b(?:zone|whole car|mask)\\b"
      ]
    },
    {
      "key": "feel-saved-toast",
      "article": "spec.presets_feels",
      "q": "Does the Saved spec preset toast prove it will survive closing the app?",
      "patterns": [
        "\\bfeel\\b",
        "\\b(?:saved|save|toast)\\b",
        "\\b(?:gone|missing|reopen|reopened|restart|closing)\\b",
        "^(?!.*\\b(?:another|different|other)\\s+(?:browser|port|profile|computer|device|origin)\\b)(?!.*\\b(?:account|sync\\w*|localhost)\\b)"
      ]
    },
    {
      "key": "feel-dialog-zone-identity",
      "article": "spec.presets_feels",
      "q": "What shifts are saved if I change or reorder Zones while the Feel-name dialog is open?",
      "patterns": [
        "\\bfeel\\b",
        "\\bzones?\\b",
        "\\b(?:rearranging|reorder|reordered|change|changed)\\b",
        "\\b(?:dialog|save|name|named)\\b"
      ]
    },
    {
      "key": "restore-original-not-history",
      "article": "spec.practical_remap_transactions",
      "q": "Does Restore Original undo my sampled material, slider edits and Base changes?",
      "patterns": [
        "\\brestore original\\b",
        "\\b(?:base|shine|slider|sliders|sample)\\b",
        "\\b(?:did not|didn't|bring back|undo|restore)\\b"
      ]
    },
    {
      "key": "narrow-range-missing-subject",
      "article": null,
      "q": null,
      "patterns": [
        "\\b(?:scratch|scratches|fine detail)\\b",
        "\\b(?:vanished|gone|missing|lost)\\b",
        "\\b(?:narrowed|narrow|range)\\b"
      ]
    },
    {
      "key": "recovery4-link-direction-report",
      "article": "zones.practical_link_limits",
      "q": "Which zone supplies the settings when I use the chain icon to link?",
      "patterns": [
        "\\bi linked\\b",
        "\\b(?:old finish|old look)\\b",
        "\\b(?:replaced|changed)\\b",
        "\\bclicked\\b"
      ]
    }
  ],
  "customerFollowups": [
    {
      "key": "recovery3-feel-name",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "Why does my saved Feel named Wet Candy apply the built-in values instead?",
      "patterns": [
        "\\bsame name\\b",
        "\\bbuilt.in\\b"
      ]
    },
    {
      "key": "recovery3-feel-save-scope",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "Does saving a Spec Feel store the Base, material stack, scale and Zone mask?",
      "patterns": [
        "\\bsav\\w*\\b",
        "\\bbase\\b",
        "\\b(?:selection|region|mask)\\b"
      ]
    },
    {
      "key": "recovery3-feel-repeat",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "If I apply a Feel twice, will the second application add another dose?",
      "patterns": [
        "\\btwice\\b",
        "\\bstrong\\b"
      ]
    },
    {
      "key": "recovery3-feel-later",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "Can later material controls override the channel values suggested by a Feel?",
      "patterns": [
        "\\boverride\\b",
        "\\b(?:final|result)\\b"
      ]
    },
    {
      "key": "recovery3-feel-number",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "How are malformed or out-of-range stored Feel numbers applied?",
      "patterns": [
        "\\b(?:decimal|out.of.range)\\b",
        "\\bvalues?\\b"
      ]
    },
    {
      "key": "recovery3-feel-browser",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "Are my saved Feels synchronized with my account or another localhost port?",
      "patterns": [
        "\\b(?:another|different)\\b",
        "\\bbrowser\\b"
      ]
    },
    {
      "key": "recovery3-feel-dialog",
      "from": "spec.presets_feels",
      "article": "spec.presets_feels",
      "q": "What shifts are saved if I change or reorder Zones while the Feel-name dialog is open?",
      "patterns": [
        "\\b(?:switch|change|reorder)\\b",
        "\\bzones?\\b",
        "\\bdialog\\b"
      ]
    },
    {
      "key": "recovery3-gradient-eleven",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Why does the gradient editor refuse an eleventh stop?",
      "patterns": [
        "\\b(?:eleventh|11th)\\b",
        "\\bstop\\b"
      ]
    },
    {
      "key": "recovery3-gradient-fraction",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Do gradient position inputs preserve fractional percentages?",
      "patterns": [
        "\\b(?:fractional|decimal)\\b",
        "\\bpercent\\w*\\b"
      ]
    },
    {
      "key": "recovery3-gradient-dedup",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Does gradient payload normalization sort and deduplicate overlapping stops?",
      "patterns": [
        "\\b(?:merge|dedup\\w*)\\b",
        "\\bstops?\\b",
        "\\bsame position\\b"
      ]
    },
    {
      "key": "recovery3-gradient-door",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Does clicking a radial gradient bar place the new stop at a physical car-panel location?",
      "patterns": [
        "\\bbar\\b",
        "\\b(?:door|panel)\\b",
        "\\b(?:click\\w*|spot)\\b"
      ]
    },
    {
      "key": "recovery3-gradient-minimum",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Why cannot I remove another gradient stop when only two remain?",
      "patterns": [
        "\\blast two\\b",
        "\\bstops?\\b"
      ]
    },
    {
      "key": "recovery3-gradient-grey",
      "from": "finishes.practical_gradient_editor_truth",
      "article": "finishes.practical_gradient_editor_truth",
      "q": "Where does Add Gradient Stop place a new colour?",
      "patterns": [
        "\\badd\\b",
        "\\b(?:biggest|largest) gap\\b"
      ]
    },
    {
      "key": "recovery3-sample-target",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.practical_sampled_material_limits",
      "q": "If I select another Zone after sampling, which Zone receives the sampled material?",
      "patterns": [
        "\\b(?:change|switch|select\\w*)\\b",
        "\\bzone\\b",
        "\\b(?:applying|where)\\b"
      ]
    },
    {
      "key": "recovery3-sample-size",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does an unsupported sampler neighborhood size create a larger averaging window?",
      "patterns": [
        "\\beleven\\b",
        "\\bneighbou?rhood\\b"
      ]
    },
    {
      "key": "recovery3-sample-preset",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does Copy Material Sample create a portable texture preset or apply anything to the Zone?",
      "patterns": [
        "\\bcopy\\w*\\b",
        "\\btexture\\b",
        "\\b(?:finish|preset)\\b"
      ]
    },
    {
      "key": "recovery3-sample-clipboard",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.practical_sampled_material_limits",
      "q": "Does a Material sample toast prove that the values reached my clipboard?",
      "patterns": [
        "\\bclipboard\\b",
        "\\b(?:blank|empty)\\b",
        "\\btoast\\b"
      ]
    },
    {
      "key": "recovery3-sample-pending",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.practical_sampled_material_limits",
      "q": "Why does sampling refuse while the Inspector is pending even if an old spec image is visible?",
      "patterns": [
        "\\bold\\b",
        "\\b(?:picture|image)\\b",
        "\\bpending\\b"
      ]
    },
    {
      "key": "recovery3-sample-alpha",
      "from": "spec.practical_sampled_material_limits",
      "article": "spec.material_override_remap_lighting",
      "q": "Does material override change alpha?",
      "patterns": [
        "\\bapplying\\b",
        "\\b(?:replace|change)\\b",
        "\\balpha\\b"
      ]
    },
    {
      "key": "recovery3-merge-footprint",
      "from": "layers.practical_merge_identity",
      "article": "layers.practical_merge_identity",
      "q": "Why can a sponsor-only Zone cover more artwork after Merge Down?",
      "patterns": [
        "\\bsponsor.only\\b",
        "\\b(?:footprint|isolat\\w*)\\b"
      ]
    },
    {
      "key": "recovery3-merge-effects",
      "from": "layers.practical_merge_identity",
      "article": "layers.practical_merge_identity",
      "q": "Can I still edit the separate strokes and colour adjustments after Merge Down?",
      "patterns": [
        "\\b(?:effects|adjustments)\\b",
        "\\bseparate\\w*\\b"
      ]
    },
    {
      "key": "recovery3-flatten-one",
      "from": "layers.practical_flatten_limits",
      "article": "layers.practical_flatten_limits",
      "q": "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
      "patterns": [
        "\\bone layer\\b",
        "\\b(?:document|only)\\b"
      ]
    },
    {
      "key": "recovery3-flatten-count",
      "from": "layers.practical_flatten_limits",
      "article": "layers.practical_flatten_limits",
      "q": "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
      "patterns": [
        "\\bwarning\\b",
        "\\bcount\\b",
        "\\bmulti.layer\\b"
      ]
    },
    {
      "key": "recovery3-linked-overlay",
      "from": "zones.practical_link_limits",
      "article": "zones.practical_link_limits",
      "q": "Do linked zones automatically synchronize every modern material and spec overlay?",
      "patterns": [
        "\\bchain\\b",
        "\\bimported\\b",
        "\\bspec overlay\\b"
      ]
    },
    {
      "key": "recovery3-reset-name",
      "from": "zones.practical_reset_scope",
      "article": "zones.practical_reset_scope",
      "q": "Does Reset Zone keep its restriction to my sponsor layer?",
      "patterns": [
        "\\b(?:unchanged|same) name\\b",
        "\\b(?:target\\w*|restrict\\w*)\\b",
        "\\blayer\\b"
      ]
    },
    {
      "key": "recovery3-colourway-material",
      "from": "layers.colourway_studio",
      "article": "layers.colourway_studio",
      "q": "Does trying a colourway always replace every zone’s finish?",
      "patterns": [
        "\\bevery zone\\b",
        "\\bfinish\\b"
      ]
    },
    {
      "key": "recovery3-stats-current",
      "from": "preview_render.render_stats_overlay",
      "article": "preview_render.render_stats_overlay",
      "q": "Can average render and per-zone times tell me whether my current render has completed?",
      "patterns": [
        "\\baverages\\b",
        "\\b(?:job|completed|completion)\\b"
      ]
    },
    {
      "key": "recovery4-merge-refusal",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Can a refused Merge Down still move my Zone’s layer target?",
        "Why can a sponsor-only Zone cover more artwork after Merge Down?",
        "Does Merge Down create a new layer or keep the lower layer identity?",
        "Can I still edit the separate strokes and colour adjustments after Merge Down?",
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Can a refused Merge Down still move my Zone’s layer target?",
      "patterns": [
        "\\bmerge down\\b",
        "\\brefus\\w*\\b",
        "\\btarget\\b"
      ]
    },
    {
      "key": "recovery4-visible-loading",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Why does Merge Visible ask me to wait when the layer list already shows names?",
      "patterns": [
        "\\bwait\\b",
        "\\blayer names\\b"
      ]
    },
    {
      "key": "recovery4-visible-group",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Why does Merge Visible refuse a grouped PSD?",
      "patterns": [
        "\\bgrouped\\b",
        "\\b(?:artwork|layers|psd)\\b"
      ]
    },
    {
      "key": "recovery4-visible-base",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Which layer keeps its identity in Merge Visible?",
      "patterns": [
        "\\bwhich one\\b",
        "\\bname\\b",
        "\\bid\\b"
      ]
    },
    {
      "key": "recovery4-visible-clipping",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Does an eye-on clipped layer always participate in Merge Visible?",
      "patterns": [
        "\\bclipped\\b",
        "\\bbase\\b",
        "\\bhidden\\b"
      ]
    },
    {
      "key": "recovery4-visible-targets",
      "from": "layers.practical_merge_identity",
      "fromFaqs": [
        "Why does Merge Visible ask me to wait when the layer list already shows names?",
        "Why does Merge Visible refuse a grouped PSD?",
        "Which layer keeps its identity in Merge Visible?",
        "Does an eye-on clipped layer always participate in Merge Visible?",
        "Does Merge Visible migrate every entry in a multi-layer Zone restriction?"
      ],
      "article": "layers.practical_merge_identity",
      "q": "Does Merge Visible migrate every entry in a multi-layer Zone restriction?",
      "patterns": [
        "\\bids\\b",
        "\\bmultiple.layer target\\b"
      ]
    },
    {
      "key": "recovery4-flatten-hidden",
      "from": "layers.practical_flatten_limits",
      "fromFaqs": [
        "Will Flatten document keep hidden layers for later editing?",
        "Does Flatten clear both single-layer and multi-layer Zone restrictions?",
        "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
        "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
        "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
        "What editable settings remain on the new Flattened layer?"
      ],
      "article": "layers.practical_flatten_limits",
      "q": "Will Flatten document keep hidden layers for later editing?",
      "patterns": [
        "\\bhidden\\b",
        "\\b(?:artwork|pixels)\\b",
        "\\bincluded\\b"
      ]
    },
    {
      "key": "recovery4-flatten-targets",
      "from": "layers.practical_flatten_limits",
      "fromFaqs": [
        "Will Flatten document keep hidden layers for later editing?",
        "Does Flatten clear both single-layer and multi-layer Zone restrictions?",
        "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
        "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
        "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
        "What editable settings remain on the new Flattened layer?"
      ],
      "article": "layers.practical_flatten_limits",
      "q": "Does Flatten clear both single-layer and multi-layer Zone restrictions?",
      "patterns": [
        "\\bclear\\b",
        "\\bmultiple.layer restriction\\b"
      ]
    },
    {
      "key": "recovery4-flatten-dialog",
      "from": "layers.practical_flatten_limits",
      "fromFaqs": [
        "Will Flatten document keep hidden layers for later editing?",
        "Does Flatten clear both single-layer and multi-layer Zone restrictions?",
        "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
        "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
        "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
        "What editable settings remain on the new Flattened layer?"
      ],
      "article": "layers.practical_flatten_limits",
      "q": "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
      "patterns": [
        "\\bconfirmation\\b",
        "\\b(?:cannot|can'?t|won'?t) open\\b"
      ]
    },
    {
      "key": "recovery4-flatten-styles",
      "from": "layers.practical_flatten_limits",
      "fromFaqs": [
        "Will Flatten document keep hidden layers for later editing?",
        "Does Flatten clear both single-layer and multi-layer Zone restrictions?",
        "Can a multi-layer restriction exist without appearing in the Flatten warning count?",
        "What happens if Flatten needs a confirmation but the confirmation UI is unavailable?",
        "Why does Flatten do nothing on a one-layer document or without a paint canvas?",
        "What editable settings remain on the new Flattened layer?"
      ],
      "article": "layers.practical_flatten_limits",
      "q": "What editable settings remain on the new Flattened layer?",
      "patterns": [
        "\\blocks\\b",
        "\\bclipping\\b",
        "\\bresulting layer\\b"
      ]
    },
    {
      "key": "recovery4-link-direction",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Which zone supplies the settings when I use the chain icon to link?",
      "patterns": [
        "\\bwhich side\\b",
        "\\bclicked\\b",
        "\\bchoose\\b"
      ]
    },
    {
      "key": "recovery4-link-programmatic",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Does every programmatic link operation immediately make the zones match?",
      "patterns": [
        "\\bprogrammatically\\b",
        "\\bchain\\b"
      ]
    },
    {
      "key": "recovery4-link-region",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Will linked zones share their drawn regions and colour-selection masks?",
      "patterns": [
        "\\bboth sides\\b",
        "\\bdrawn region\\b"
      ]
    },
    {
      "key": "recovery4-link-source",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Does linking zones copy the source-layer restriction to the other side?",
      "patterns": [
        "\\bsponsor.layer\\b",
        "\\brestriction\\b",
        "\\bother side\\b"
      ]
    },
    {
      "key": "recovery4-link-slider",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Will every slider adjustment propagate to all linked zones?",
      "patterns": [
        "\\bevery slider\\b",
        "\\bfollow\\b"
      ]
    },
    {
      "key": "recovery4-link-unlink-pair",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Why did both chain icons disappear after I unlinked one of two zones?",
      "patterns": [
        "\\bboth chain icons\\b",
        "\\bdisappear\\b",
        "\\bunlinked\\b"
      ]
    },
    {
      "key": "recovery4-link-deepcopy",
      "from": "zones.practical_link_limits",
      "fromFaqs": [
        "Which zone supplies the settings when I use the chain icon to link?",
        "Does every programmatic link operation immediately make the zones match?",
        "Will linked zones share their drawn regions and colour-selection masks?",
        "Does linking zones copy the source-layer restriction to the other side?",
        "Do linked zones automatically synchronize every modern material and spec overlay?",
        "Will every slider adjustment propagate to all linked zones?",
        "Why did both chain icons disappear after I unlinked one of two zones?",
        "Does unlinking restore the different finishes I had before linking?",
        "Are linked pattern stacks independent deep copies?"
      ],
      "article": "zones.practical_link_limits",
      "q": "Are linked pattern stacks independent deep copies?",
      "patterns": [
        "\\bpattern stacks\\b",
        "\\bindependent copies\\b"
      ]
    },
    {
      "key": "recovery4-reset-name",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Does Reset Zone keep the name but discard its settings?",
      "patterns": [
        "\\bstill\\b",
        "\\bsame name\\b"
      ]
    },
    {
      "key": "recovery4-reset-region",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Will Reset Zone preserve my drawn lasso or brush area?",
      "patterns": [
        "\\blasso\\b",
        "\\boutline\\b",
        "\\bsurvive\\b"
      ]
    },
    {
      "key": "recovery4-reset-source",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Does Reset Zone keep its restriction to my sponsor layer?",
      "patterns": [
        "\\btarget only\\b",
        "\\bsponsor layer\\b"
      ]
    },
    {
      "key": "recovery4-reset-stack",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
      "patterns": [
        "\\berase\\b",
        "\\bmaterial\\b",
        "\\bpattern rows\\b"
      ]
    },
    {
      "key": "recovery4-reset-map",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Does Reset Zone leave a zone-specific imported spec map attached?",
      "patterns": [
        "\\bimported spec map\\b",
        "\\bstill attached\\b"
      ]
    },
    {
      "key": "recovery4-reset-muted",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Can resetting a muted Zone make it active again?",
      "patterns": [
        "\\bstay muted\\b"
      ]
    },
    {
      "key": "recovery4-reset-lock",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Do Zone choice locks protect my settings from Reset Zone?",
      "patterns": [
        "\\bbase\\b",
        "\\bcolou?r locks\\b",
        "\\bstop\\b"
      ]
    },
    {
      "key": "recovery4-reset-dialog",
      "from": "zones.practical_reset_scope",
      "fromFaqs": [
        "Does Reset Zone keep the name but discard its settings?",
        "Will Reset Zone preserve my drawn lasso or brush area?",
        "Does Reset Zone keep its restriction to my sponsor layer?",
        "What happens to modern material stacks and extra pattern stacks during Reset Zone?",
        "Does Reset Zone leave a zone-specific imported spec map attached?",
        "Can resetting a muted Zone make it active again?",
        "Do Zone choice locks protect my settings from Reset Zone?",
        "Why might confirming Reset Zone leave the settings unchanged?"
      ],
      "article": "zones.practical_reset_scope",
      "q": "Why might confirming Reset Zone leave the settings unchanged?",
      "patterns": [
        "\\bzone list\\b",
        "\\bconfirmation\\b",
        "\\bnothing happen\\b"
      ]
    },
    {
      "key": "recovery4-remap-undo",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Does Apply store the last preview draft as the state to undo to?",
      "patterns": [
        "\\bundo\\b",
        "\\bpreview draft\\b",
        "\\bbefore the dialog\\b"
      ]
    },
    {
      "key": "recovery4-remap-malformed",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Why did one malformed channel prevent the other remap ranges from taking effect?",
      "patterns": [
        "\\bone channel\\b",
        "\\breversed range\\b",
        "\\bother two\\b"
      ]
    },
    {
      "key": "recovery4-remap-preset",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
      "patterns": [
        "\\bmatte\\b",
        "\\bgloss\\b",
        "\\brecommendations\\b"
      ]
    },
    {
      "key": "recovery4-remap-target",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
      "patterns": [
        "\\banother zone\\b",
        "\\bapply\\b",
        "\\bwhich one\\b"
      ]
    },
    {
      "key": "recovery4-remap-noop",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Why did applying unchanged material ranges report no history added?",
      "patterns": [
        "\\bapply\\b",
        "\\bno history\\b"
      ]
    },
    {
      "key": "recovery4-remap-preview",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Does moving Remapper inputs immediately save every draft to project history?",
      "patterns": [
        "\\bpreview\\b",
        "\\binput changes\\b",
        "\\bhistory\\b"
      ]
    },
    {
      "key": "recovery4-remap-freshness",
      "from": "spec.practical_remap_transactions",
      "fromFaqs": [
        "Does Restore Original undo my sampled material, slider edits and Base changes?",
        "Are applying Original ranges and pressing Restore Original the same when I have a sample override?",
        "Can I cancel a remap preview without committing the draft material?",
        "Does Apply store the last preview draft as the state to undo to?",
        "Can a very narrow remap range preserve every distinct scratch shade?",
        "Why did one malformed channel prevent the other remap ranges from taking effect?",
        "Are Metallic, Vinyl, Matte and Gloss remap presets verified car-finish recommendations?",
        "Can changing the selected Zone while a Remapper dialog is open redirect Apply?",
        "Why did applying unchanged material ranges report no history added?",
        "Does moving Remapper inputs immediately save every draft to project history?",
        "Does opening Remapper guarantee that its draft starts from a fresh spec render?"
      ],
      "article": "spec.practical_remap_transactions",
      "q": "Does opening Remapper guarantee that its draft starts from a fresh spec render?",
      "patterns": [
        "\\bopening\\b",
        "\\bstarting spec image\\b",
        "\\bcurrent\\b"
      ]
    }
  ]
};
})(typeof window!=="undefined"?window:this);
