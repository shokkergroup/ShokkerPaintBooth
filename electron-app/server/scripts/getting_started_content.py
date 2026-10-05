# -*- coding: utf-8 -*-
"""Content for SPB Getting Started Guide — verified against live app (v6.3.0-alpha)."""

from reportlab.platypus import PageBreak, Spacer
from reportlab.lib.units import inch

# (anchor, bookmark_title, display_title, level)
TOC = [
    ("part0", "Part 0 — Start Here", None, 0),
    ("what_is_spb", "What SPB Is", "What Shokker Paint Booth Is", 1),
    ("first15", "Your First 15 Minutes", "Your First 15 Minutes (Do This First)", 1),
    ("mental_model", "Mental Model", "Paint + Spec + Zones", 1),
    ("part1", "Part I — Setup", None, 0),
    ("header_setup", "Header Fields", "Header: ID, Paint Path, Output Folder", 1),
    ("load_paint", "Loading Paint", "Loading Your Paint (PSD vs TGA)", 1),
    ("settings", "Settings", "Settings (Gear Menu)", 1),
    ("part2", "Part II — Interface", None, 0),
    ("interface_map", "Interface Map", "Where Everything Lives", 1),
    ("zones_panel", "Zones Panel", "Left Panel — The 10 Default Zones", 1),
    ("zone_popout", "Zone Popout", "Zone Popout Panel (Your Control Center)", 1),
    ("layers_panel", "Layers Panel", "Right Panel — Layers (Not Finishes)", 1),
    ("part3", "Part III — Core Workflow", None, 0),
    ("pick_colors", "Define Zone Colors", "Step 1: Tell Each Zone Which Pixels", 1),
    ("assign_finish", "Assign Finishes", "Step 2: Assign Finishes (Popout Only)", 1),
    ("layer_restrict", "Layer Restriction", "Step 3: Restrict to Layer (When Needed)", 1),
    ("preview_render", "Preview & Render", "Step 4: Preview, Then RENDER", 1),
    ("part4", "Part IV — Zone Popout Reference", None, 0),
    ("popout_color", "COLOR Section", "COLOR Section", 1),
    ("popout_base", "BASE Section", "BASE — Swatch Picker", 1),
    ("popout_pattern", "Pattern & Spec", "Pattern, Spec Stack & Overlays", 1),
    ("part5", "Part V — Finishes", None, 0),
    ("finish_types", "Finish Types", "Bases, Patterns, Monolithics, Spec Patterns", 1),
    ("swatch_picker", "Swatch Picker", "How the Finish Picker Works", 1),
    ("part6", "Part VI — Spec Maps", None, 0),
    ("spec_channels", "Spec Channels", "M / R / CC for iRacing", 1),
    ("spec_iron", "Iron Rules", "Iron Rules", 1),
    ("part7", "Part VII — Tools", None, 0),
    ("toolbar_modes", "Zone vs Layer Mode", "Toolbar: Zone Mode vs Layer Mode", 1),
    ("tools_ref", "Tool Reference", "Selection, Draw & Spatial Tools", 1),
    ("part8", "Part VIII — Render & Deploy", None, 0),
    ("render", "Render Pipeline", "What RENDER Does", 1),
    ("live_link", "Auto-Deploy", "Auto-Deploy to iRacing", 1),
    ("part9", "Part IX — Save & Share", None, 0),
    ("shokk_files", "SHOKK & Recipes", ".shokk Files & Import Recipe", 1),
    ("part10", "Part X — Finish Viewer", None, 0),
    ("fv_guide", "Finish Viewer", "Finish Viewer (Paint Lab)", 1),
    ("part11", "Part XI — Spec Sculpt", None, 0),
    ("ss_guide", "Spec Sculpt", "Spec Sculpt Lab", 1),
    ("part12", "Part XII — Shokk Drop", None, 0),
    ("sd_guide", "Shokk Drop", "Shokk Drop", 1),
    ("part13", "Part XIII — Workflows", None, 0),
    ("workflows", "Common Workflows", "Copy-Paste Workflows", 1),
    ("part14", "Reference", None, 0),
    ("shortcuts", "Shortcuts", "Keyboard Shortcuts", 1),
    ("trouble", "Troubleshooting", "Troubleshooting", 1),
    ("glossary", "Glossary", "Glossary", 1),
]


def build_all(ctx):
    s, st = ctx["story"], ctx["st"]
    part, h1, h2, body, tip, warn, bullets, table = (
        ctx["part"], ctx["h1"], ctx["h2"], ctx["body"],
        ctx["tip"], ctx["warn"], ctx["bullets"], ctx["table"],
    )

    # ═══ PART 0 ═══
    part(s, "part0", "Part 0 — Start Here",
         "Read this part once. It matches what the app actually shows on first launch.")

    h1(s, "what_is_spb", "What Shokker Paint Booth Is",
       "SPB finishes iRacing liveries. You load a paint file, tell the app which pixels belong to which "
       "<b>zone</b>, assign a <b>finish</b> (chrome, candy, carbon, COLORSHOXX, etc.) to each zone, "
       "and hit <b>RENDER</b>. The engine writes both the color TGA and the spec map iRacing expects.")
    bullets(s, [
        "<b>Not Photoshop</b> — build logos and layout in Photoshop; use SPB for materials, gloss, flake, and spec.",
        "<b>2,400+ finishes</b> — bases, patterns, monolithics, and spec-overlay patterns.",
        "<b>Zone-level control</b> — one panel chrome, the next matte red, side by side.",
        "<b>Companion labs</b> (header buttons): Finish Viewer, Spec Sculpt, Shokk Drop — covered later in this guide.",
    ])

    h1(s, "first15", "Your First 15 Minutes (Do This First)",
       "This path matches the in-app guided tour. No labs, no save files — just paint → zone → finish → render.")
    bullets(s, [
        "<b>1. Load paint.</b> Header → <b>Import PSD</b> (recommended) or browse a TGA. "
        "First launch may already show the demo Chevy truck paint.",
        "<b>2. Enter your iRacing User ID</b> in the header (4–7 digits). Set your <b>iRacing Car Folder</b> output path.",
        "<b>3. Click a zone</b> in the left list — you already have <b>10 default zones</b> "
        "(Body Color 1–4, Car Number, Custom Art 1–2, Sponsors, Open Zone 9, Everything Else). "
        "Do not click + Add Zone unless you need an extra slot.",
        "<b>4. Define what pixels the zone covers.</b> With the zone selected, use the "
        "<b>ZONE POPOUT PANEL</b> (floating panel): quick-color chips, eyedropper on canvas (Pick Color tool), "
        "or Magic Wand. Each zone card shows a hint explaining its purpose.",
        "<b>5. Assign a finish.</b> In the popout, open the <b>BASE</b> section → click the "
        "<b>Base swatch dropdown</b> (shows “Select base…” or current finish name). "
        "Pick a finish from the picker that opens. "
        "<b>Do not use the Finish Library on the right panel to assign finishes to zones.</b>",
        "<b>6. Repeat</b> for other zones you care about. Delete unused body-color slots (× on zone card) if single-color.",
        "<b>7. Check preview.</b> Use the preview pane; press <b>F5</b> or Refresh if it stalls.",
        "<b>8. RENDER.</b> Click the big <b>RENDER</b> button. Confirm <code>car_&lt;id&gt;.tga</code> "
        "and <code>car_spec_&lt;id&gt;.tga</code> land in your output folder.",
    ])
    tip(s, "Zone 10 “Everything Else” is pre-set to catch unclaimed pixels with a gloss base — "
         "keep it at the bottom of the stack.")

    h1(s, "mental_model", "Paint + Spec + Zones")
    bullets(s, [
        "<b>Paint file</b> — PSD (layers) or flat TGA/PNG on the canvas.",
        "<b>Zone</b> — named slot that maps pixels → finish. Top zones win over lower ones.",
        "<b>Finish</b> — material recipe (base + optional pattern + spec). Assigned via popout Base swatch.",
        "<b>Spec map</b> — second TGA iRacing uses for metallic/roughness/clearcoat. SPB generates it on render.",
    ])

    # ═══ PART I ═══
    part(s, "part1", "Part I — Setup", "Before you render, these header fields must be correct.")

    h1(s, "header_setup", "Header: ID, Paint Path, Output Folder")
    table(s, [
        ["Field", "What it does"],
        ["iRacing User ID", "Your member number — used in output filenames (car_23371.tga)"],
        ["Source Paint", "Path to PSD/TGA/PNG; Import PSD button for layered files"],
        ["iRacing Car Folder", "Where RENDER writes car_*.tga — browse to your iRacing paint folder"],
    ], [1.6 * inch, 4.0 * inch])
    body(s, "Header also has: <b>RENDER</b>, lab buttons (Finish Viewer / Spec Sculpt / Shokk Drop), "
         "<b>Import Recipe</b>, <b>Commands</b> menu, and <b>Settings</b> (gear).")

    h1(s, "load_paint", "Loading Your Paint (PSD vs TGA)")
    table(s, [
        ["Format", "When to use"],
        ["PSD (Import PSD button)", "Primary workflow — keeps Numbers, Sponsors, Car Paint as separate layers"],
        ["TGA / PNG", "Flat paint, quick tests, or when PSD unavailable"],
    ], [1.8 * inch, 3.8 * inch])
    body(s, "After PSD import, the right panel lists layers (Wire, Mask, Numbers, Sponsors, Car Paint, etc.). "
         "Layer names power the <b>Restrict to Layer</b> dropdown in the zone popout.")

    h1(s, "settings", "Settings (Gear Menu)")
    bullets(s, [
        "<b>License</b> — activate Payhip key or early-access code.",
        "<b>Auto-Deploy to iRacing</b> — copy each render straight to iRacing folder (Live Link).",
        "<b>Import Spec Map (Merge Mode)</b> — merge external spec TGA into output.",
        "<b>Car File Naming</b> — custom number options if needed.",
        "<b>LOOKS</b> — shop theme presets (cosmetic only).",
    ])

    # ═══ PART II ═══
    part(s, "part2", "Part II — Interface", "Know the four work areas.")

    h1(s, "interface_map", "Where Everything Lives")
    table(s, [
        ["Area", "Location", "Purpose"],
        ["Header", "Top", "ID, paths, RENDER, labs, settings"],
        ["Zones list", "Left", "10 default zone cards — click to select"],
        ["Zone popout", "Floating", "COLOR, BASE, pattern, spec — assign finishes HERE"],
        ["Toolbar", "Far left", "Pick Color, Wand, Brush, Include/Exclude, etc."],
        ["Canvas", "Center", "Your paint; eyedropper and region tools"],
        ["Preview", "Center-right", "Live rendered car view"],
        ["Layers list", "Right", "PSD layer visibility — not for finish assignment"],
        ["RENDER", "Canvas area / header", "Generates final TGAs"],
    ], [1.0 * inch, 1.1 * inch, 3.5 * inch])

    h1(s, "zones_panel", "Left Panel — The 10 Default Zones")
    body(s, "On every fresh session SPB creates these zones automatically:")
    table(s, [
        ["#", "Name", "Typical use"],
        ["1–4", "Body Color 1–4", "Primary/secondary body colors — delete extras if unused"],
        ["5", "Car Number", "Number panel colors"],
        ["6–7", "Custom Art 1–2", "Stripes, accents, custom graphics"],
        ["8", "Sponsors / Logos", "Sponsor regions"],
        ["9", "Open Zone 9", "Spare slot before catch-all"],
        ["10", "Everything Else", "Remaining pixels — pre-set gloss safety net"],
    ], [0.4 * inch, 1.4 * inch, 3.8 * inch])
    bullets(s, [
        "Each card: rename, solo (👁), reorder (▲▼), duplicate (☍), delete (×).",
        "<b>Restore All</b> — resets all 10 defaults (keeps finishes on matching names where possible).",
        "<b>+ Add Zone</b> — only if you need more than 10.",
        "Click a zone card → popout opens for that zone.",
    ])

    h1(s, "zone_popout", "Zone Popout Panel (Your Control Center)",
       "Labeled <b>ZONE POPOUT PANEL</b> at the top. This is where you work — not the right-side Finish Library.")
    warn(s, "Assign finishes by clicking the <b>Base swatch dropdown</b> in this panel. "
         "The Finish Library panel on the right is for browsing/reference — do not use it as your primary assign path.")
    bullets(s, [
        "Header row: Auto-name, copy/paste zone, Solo, Reset, ⚡ SHOKK ME.",
        "<b>COLOR</b> — which pixels (quick chips, hex, tolerance, Hard Edge, Draw box, Lasso).",
        "<b>BASE</b> — finish assignment via swatch dropdown ▾.",
        "Below BASE (after a finish is set): Base Color mode, HSB sliders, Pattern, Spec stack, overlays.",
        "Sections below BASE stay hidden until you pick a base or monolithic — that is normal.",
    ])

    h1(s, "layers_panel", "Right Panel — Layers (Not Finishes)",
       "After PSD import this shows your layer stack: Wire, Mask, Numbers, Sponsors, Car Paint, etc.")
    bullets(s, [
        "Click a layer to select it for <b>Layer mode</b> drawing tools.",
        "Toggle visibility, opacity, blend mode per layer.",
        "Double-click → Layer Effects (shadow, stroke, glow).",
        "Use <b>Restrict to Layer</b> in zone popout to limit a zone to one layer's pixels.",
        "The collapsible Finish Library on the right is optional browse — "
        "<b>assign finishes through the zone popout Base swatch</b>.",
    ])

    # ═══ PART III ═══
    part(s, "part3", "Part III — Core Workflow", "The four steps every livery goes through.")

    h1(s, "pick_colors", "Step 1: Tell Each Zone Which Pixels")
    bullets(s, [
        "Select zone in left list → popout opens.",
        "<b>Quick colors</b> — Red, Blue, White, Remaining, etc. (chips in COLOR section).",
        "<b>Pick Color tool</b> (🎨) — click a pixel on canvas; color adds to zone.",
        "<b>Magic Wand</b> — flood-select by tolerance.",
        "<b>Draw box / Lasso</b> — manual region when color match fails.",
        "<b>Tolerance slider</b> — Exact / Tight / Std / Loose presets + numeric slider.",
        "<b>Hard Edge</b> — on by default; crisp zone boundaries.",
    ])

    h1(s, "assign_finish", "Step 2: Assign Finishes (Popout Only)",
       "In ZONE POPOUT → BASE section → click the <b>Base</b> row swatch (name + ▾ arrow).")
    bullets(s, [
        "Picker opens with search, #hashtag filters, Favorites, Grouped view.",
        "Choose a <b>base</b> (gloss, chrome, matte…) or a <b>monolithic</b> (COLORSHOXX, MORTAL SHOKK).",
        "Click a finish → it applies to the active zone; popout expands with more controls.",
        "Pattern: second swatch row in popout (below base controls).",
        "Spec patterns: stack section in popout for per-channel M/R/CC overlays.",
        "<b>Intensity</b> — strength preset dropdown in popout after base assigned.",
    ])
    warn(s, "Again: do not assign zone finishes from the right-panel Finish Library tab. "
         "Always use the popout Base swatch — same catalog, correct workflow.")

    h1(s, "layer_restrict", "Step 3: Restrict to Layer (When Needed)",
       "If the same color appears on multiple layers, restrict the zone so it only paints one layer.")
    bullets(s, [
        "Popout → COLOR section → <b>RESTRICT TO LAYER</b> dropdown (visible when PSD loaded).",
        "Example: Car Number zone → restrict to <b>Numbers</b> layer.",
        "Sponsors zone → restrict to <b>Sponsors</b> layer.",
        "Without restriction, a yellow pixel on Numbers AND Stripes both get the finish.",
    ])

    h1(s, "preview_render", "Step 4: Preview, Then RENDER")
    bullets(s, [
        "Preview pane updates as zones change — same engine as final render.",
        "<b>F5</b> or Refresh button if preview hangs.",
        "Channel buttons: Combined spec, Metallic, Roughness, Clearcoat diagnostics.",
        "<b>RENDER</b> — writes 2048² <code>car_&lt;id&gt;.tga</code> + <code>car_spec_&lt;id&gt;.tga</code>.",
        "Enable Auto-Deploy in Settings to copy straight to iRacing folder.",
        "Reload car in iRacing Paint screen to see updates.",
    ])

    # ═══ PART IV ═══
    part(s, "part4", "Part IV — Zone Popout Reference", "Section-by-section detail.")

    h1(s, "popout_color", "COLOR Section")
    bullets(s, [
        "Quick color chips + Remaining + Everything special selectors.",
        "Hex input + Apply button for precise colors.",
        "Tolerance + Hard Edge checkbox.",
        "Draw box / Lasso / Refine color for manual masks.",
        "Apply Area controls for drawn regions.",
        "Restrict to Layer dropdown (PSD workflow).",
    ])

    h1(s, "popout_base", "BASE — Swatch Picker")
    body(s, "The gold-labeled <b>Base</b> row with swatch dot + name + ▾ opens the finish catalog picker. "
         "This is the primary finish assignment control in the entire app.")
    bullets(s, [
        "Lock icon — keep base when randomizing (⚡ SHOKK ME).",
        "After pick: Base Color mode (source / solid / special / gradient).",
        "Hue / Saturation / Brightness sliders adjust tint without changing finish identity.",
        "Base scale, rotation, strength sliders for placement tuning.",
    ])

    h1(s, "popout_pattern", "Pattern, Spec Stack & Overlays")
    bullets(s, [
        "<b>Pattern swatch</b> — texture overlay (carbon, weave, noise…).",
        "<b>Spec pattern stack</b> — up to 5 layers affecting M/R/CC independently.",
        "<b>2nd–5th base overlays</b> — additional material layers with blend modes.",
        "<b>Manual placement bar</b> — appears on canvas when adjusting pattern position.",
        "⚡ SHOKK ME — randomize entire zone (fun, not for production).",
    ])

    # ═══ PART V ═══
    part(s, "part5", "Part V — Finishes", "What you're picking in the Base swatch dropdown.")

    h1(s, "finish_types", "Bases, Patterns, Monolithics, Spec Patterns")
    table(s, [
        ["Type", "What it is", "Pick via"],
        ["Base", "Foundation material (gloss, chrome, matte…)", "Popout → Base swatch"],
        ["Pattern", "Texture overlay on base", "Popout → Pattern swatch"],
        ["Monolithic", "All-in-one (COLORSHOXX, MORTAL SHOKK, PARADIGM)", "Popout → Base swatch"],
        ["Spec pattern", "PBR overlay on M/R/CC channels", "Popout → Spec stack"],
    ], [1.1 * inch, 2.5 * inch, 1.8 * inch])
    body(s, "Monolithics bundle base + pattern + spec in one click — good first choice for dramatic looks.")

    h1(s, "swatch_picker", "How the Finish Picker Works")
    bullets(s, [
        "Opens from popout Base/Pattern swatch click — search bar, #hashtag chips.",
        "Grouped / Favorites / Showcase / Best / A-Z sort toggles.",
        "Click finish → applies and closes (or use Compare in catalog modal for A/B).",
        "Same catalog powers Finish Viewer lab previews — different entry point.",
    ])

    # ═══ PART VI ═══
    part(s, "part6", "Part VI — Spec Maps", "What iRacing reads besides color.")

    h1(s, "spec_channels", "M / R / CC for iRacing")
    table(s, [
        ["Channel", "Meaning", "Remember"],
        ["R — Metallic", "0 = paint, 255 = metal", "Chrome = high R"],
        ["G — Roughness", "0 = mirror, 255 = matte", "Lower = shinier"],
        ["B — Clearcoat", "16 = MAX gloss", "INVERTED — 255 = dull"],
    ], [1.2 * inch, 2.0 * inch, 2.4 * inch])

    h1(s, "spec_iron", "Iron Rules")
    body(s, "SPB clamps illegal values on export. Clearcoat 1–15 causes whitewash in-sim — never use. "
         "Spec Sculpt and Render both enforce iron rules.")

    # ═══ PART VII ═══
    part(s, "part7", "Part VII — Tools", "Left toolbar reference.")

    h1(s, "toolbar_modes", "Zone Mode vs Layer Mode")
    body(s, "Bottom of canvas area: toggle <b>Zone</b> (pressed by default) vs <b>Layer</b>. "
         "Zone mode: color picking, spatial include/exclude, mask tools affect zones. "
         "Layer mode: brush, move, transform affect PSD layers.")

    h1(s, "tools_ref", "Selection, Draw & Spatial Tools")
    table(s, [
        ["Tool", "Key", "Use"],
        ["Pick Color", "P", "Sample pixel → zone color"],
        ["Magic Wand", "W", "Flood by tolerance"],
        ["Lasso / Rect", "L / O", "Manual selection"],
        ["Include / Exclude", "—", "Add/subtract zone region"],
        ["Brush / Fill", "B / K", "Paint mask or layer"],
        ["Move / Transform", "V / Ctrl+T", "Layer elements"],
    ], [1.2 * inch, 0.7 * inch, 3.7 * inch])

    # ═══ PART VIII ═══
    part(s, "part8", "Part VIII — Render & Deploy", None)

    h1(s, "render", "What RENDER Does")
    bullets(s, [
        "Composites all visible zones → color TGA.",
        "Generates matching spec TGA from zone finish settings.",
        "Shows Render Recipe card with job summary.",
        "Typical time: a few seconds at 2048².",
    ])

    h1(s, "live_link", "Auto-Deploy to iRacing")
    bullets(s, [
        "Settings → Auto-Deploy to iRacing → On.",
        "Set iRacing Car Folder to your paint directory.",
        "Each RENDER atomically writes car + spec TGAs.",
        "Reload car in iRacing — no restart needed.",
    ])

    # ═══ PART IX ═══
    part(s, "part9", "Part IX — Save & Share", "After you're comfortable with the core loop.")

    h1(s, "shokk_files", ".shokk Files & Import Recipe")
    bullets(s, [
        "<b>Save SHOKK</b> — full session (zones, finishes, layers) for backup or sharing.",
        "<b>Import Recipe</b> (header) — load a .shokkerrecipe into zones.",
        "<b>Auto-save</b> — session persists across restarts.",
        "<b>.spbdrop</b> — single finish pack from Shokk Drop (see Part XII).",
    ])

    # ═══ PART X–XII Labs ═══
    part(s, "part10", "Part X — Finish Viewer (Paint Lab)",
         "Optional lab — preview any finish on a spinning ball without a car render.")

    h1(s, "fv_guide", "Finish Viewer (Paint Lab)")
    bullets(s, [
        "Open: header <b>Finish Viewer</b> button.",
        "Browse catalog → inspect on sphere with lighting rigs.",
        "Modules: Live Preview, Spec Doctor, Lighting Sim, Compare, Export QA, Reports.",
        "Use to audition finishes before picking them in the zone popout Base swatch.",
        "Does not replace the zone workflow — it previews finishes in isolation.",
    ])

    part(s, "part11", "Part XI — Spec Sculpt Lab", "Paint plate → spec map authoring.")

    h1(s, "ss_guide", "Spec Sculpt Lab")
    bullets(s, [
        "Open: header <b>Spec Sculpt</b>.",
        "Drop a paint TGA/PNG → pick Scratch / Catalog / Fusion look → Generate spec TGA.",
        "Auto-Sculpt, Shokk the World (~20 looks), saved recipes.",
        "Complements booth: booth assigns finishes to zones; Sculpt builds spec from flat paint.",
        "Iron rules enforced on export.",
    ])

    part(s, "part12", "Part XII — Shokk Drop", "Art → finish import and sharing.")

    h1(s, "sd_guide", "Shokk Drop")
    bullets(s, [
        "Open: header <b>Shokk Drop</b>.",
        "Drop PNG/JPG → Import DNA → Gauntlet validation → Commit.",
        "Finished imports appear in popout Base picker under SHOKK DROP groups.",
        "Share via .spbdrop packs; SHOKK THE WORLD generates variant sets.",
    ])

    # ═══ PART XIII ═══
    part(s, "part13", "Part XIII — Workflows", None)

    h1(s, "workflows", "Copy-Paste Workflows")
    h2(s, "Single-color body + chrome numbers")
    bullets(s, [
        "Import PSD. Delete Body Color 2–4 and unused art zones.",
        "Body Color 1: pick body color → popout Base → gloss or candy base.",
        "Car Number: pick number color → restrict to Numbers layer → monolithic or chrome base.",
        "Everything Else: leave as catch-all (or delete if all pixels claimed above).",
        "RENDER.",
    ])
    h2(s, "Recolor existing TGA")
    bullets(s, [
        "Load TGA in header. Select zone → pick old color → assign new finish via popout Base.",
        "Use Remaining on Everything Else to skip unclaimed pixels.",
    ])
    h2(s, "Spec only from finished paint")
    bullets(s, [
        "Open Spec Sculpt → drop flat paint → Auto-Sculpt or Shokk the World → Deploy spec TGA.",
    ])

    # ═══ REFERENCE ═══
    part(s, "part14", "Reference", None)

    h1(s, "shortcuts", "Keyboard Shortcuts")
    table(s, [
        ["Shortcut", "Action"],
        ["Ctrl+Z / Ctrl+Shift+Z", "Undo / Redo"],
        ["Ctrl+R", "Render"],
        ["F5", "Refresh preview"],
        ["P / W / B / E", "Pick Color / Wand / Brush / Eraser"],
        ["Ctrl+0 / scroll", "Fit / zoom canvas"],
        ["Space + drag", "Pan canvas"],
        ["?", "Shortcut legend"],
    ], [1.6 * inch, 4.0 * inch])

    h1(s, "trouble", "Troubleshooting")
    table(s, [
        ["Problem", "Fix"],
        ["Finish didn't apply", "Use popout Base swatch — not right-panel library"],
        ["Wrong region painted", "Add Restrict to Layer in popout COLOR section"],
        ["Popout empty below Base", "Pick a base/monolithic first — sections are gated"],
        ["Preview blank", "Define zone colors; F5; check server status"],
        ["iRacing old paint", "Reload car in Paint screen; verify output folder"],
        ["Lost default zones", "Click Restore All in zones panel"],
    ], [2.0 * inch, 3.6 * inch])

    h1(s, "glossary", "Glossary")
    table(s, [
        ["Term", "Meaning"],
        ["Zone", "Named pixel region + finish assignment"],
        ["Zone popout", "Floating panel — assign finishes here"],
        ["Base swatch", "Dropdown in popout BASE row — opens finish picker"],
        ["Monolithic", "One-click bundled finish"],
        ["Spec map", "Metallic/Roughness/Clearcoat TGA for iRacing"],
        ["Remaining", "Selector for unclaimed pixels"],
        ["Live Link", "Auto-deploy render to iRacing folder"],
    ], [1.4 * inch, 4.2 * inch])

    s.append(Spacer(1, 0.3 * inch))
    body(s, "Shokker Paint Booth · Paint the paint. Not the pixel.")
