# ENC_IDEAS - Design Ideas & Styles part of the Encyclopedia (2026-10-05)

## Result
- `data/encyclopedia/ideas.json`: **70 articles** (`ideas.*`), 246 KB (cap 320 KB), 790 aliases (vague phrasings), 20 marked `quick`.
- Every article has summary, what, how (real button names), 2-3 examples with exact settings (zone target, hex, finish, pattern + scale, spec overlay + strength), combos, 3+ FAQ, mistakes, protips, aliases, related, actions, sources, screens.
- Coverage: pop/contrast, aggressive, clean/classy, expensive, fast, stand out, readable on TV, stealth, wet look, satin OEM, chrome show car, candy/lowrider, patina, rat rod, retro 50s/60s/70s/80s/90s, Gulf-style and Martini-style (generic colours and layout only), muscle, hot rod/kustom, JDM, drift, rally, Le Mans/endurance, touring, oval, black-gold luxury, racing stripes, checkered flag, speed lines, neon night, cyberpunk/synthwave, fighter jet, military, police/emergency (generic), high-vis, carbon/race-bare, two-tone, fade/gradient, three camo articles, flames, tribal, geometric, hex/tech, marble/stone, holographic/iridescent, colour shift, pastel, monochrome, metal flake, pearl, liquid metal, glass/crystal, matte with chrome, space/galaxy, scales, patriotic, Japanese art, surf/beach, racing green heritage, punk/grunge, team colours, numbers vs body, sponsor-friendly bases, and a `style_menu` entry point.
- quick (20): make_it_pop, aggressive_mean, clean_classy, look_expensive, readable_on_tv, stealth_murdered_out, retro_70s, gulf_style, old_school_muscle, jdm, racing_stripes, neon_night, fighter_jet, fade_gradient, camo_woodland_desert, police_emergency, carbon_race_bare, flames, holographic_iridescent, style_menu.

## Id verification (never invented)
- 117 finish ids, 47 pattern ids, 28 spec-pattern ids are named across the articles (each also listed in `actions[]`).
- Method (`scripts/ai_atlas/enc_ideas.py`, run on every article before it is written): finish key must be in the atlas dump (`data/encyclopedia/_drafts/_dumpB.json`, `atlas.items`) AND not in `scripts/ai_atlas/enc_picker_hidden.json`; pattern must be in PATTERNS and in PATTERN_GROUPS and have a `pattern::` atlas key; spec pattern must be in SPEC_PATTERNS and SPEC_PATTERN_GROUPS and have a `spec::` atlas key. `python scripts/ai_atlas/enc_ideas.py check` re-verifies the whole file: `CHECK 70 articles, 0 with bad ids`.
- Spec numbers: the flat foundations use the pinned engine-registry values (`enc_foundation_pinned.json`, from `engine/base_registry_data.py`); other finishes are quoted as "about ..." atlas averages. Every cited finish/pattern/spec line is in `sources[]` as file:line (anchors rebuilt; gate shows cited-without-anchor 0).
- Picker-HIDDEN ids avoided on purpose: hi_vis_lime, retroreflective_silver, cats_eye_beaded, base::candy, base::chrome, base::metallic and the glass finishes (the high-vis and police recipes use plain Gloss + solid colours + the Retroreflective spec overlay instead). Note: some older `recipes.*` articles cite hidden ids (base::candy, base::chrome, glass finishes, f_soft_*); not touched (not my files).

## Gates (run after the last article)
```
node _easy_claude_work/enc_v2_test.js --final  -> PASS ideas.json 70 articles (70 written) 246 KB ... TOTAL 379 files, 6164 articles checked, all PASS ; ANCHORS PASS anchors ok 2562, cited-without-anchor 0
node _easy_claude_work/enc_v2_test.js --depth  -> PASS ideas.json ; DEPTH lane C: 189/189 hand-written articles meet the bar
python scripts/ai_atlas/build_encyclopedia.py -> ran OK, "encyclopedia: 500 terms ... 976 KB", ideas.json present in js/spb-encyclopedia-data.js (28 KB of the v2 index)
```

## Open items (not mine to fix)
1. `node _easy_claude_work/enc_test.js` is now 26/27 RED: the size check fails (keyword part 433 KB vs 400 KB target; whole file 976 KB vs 900 KB cap). The ideas part adds only 28 KB, so the file was already about 947 KB before it (search-lab alias growth); someone needs to trim or raise the cap.
2. The reader's table of contents (`js/spb-encyclopedia.js`, parts list near line 28) has no part for domain `ideas`; add `{ n: ..., t: 'Design ideas and styles', d: ['ideas'] }`. Until then the articles are reachable by search/aliases only. The helper needs wiring to answer vague asks from `ideas.*` (entry article: `ideas.style_menu`).
3. Spec facts for Fractured/Astra colour-shift finishes are described qualitatively (their catalogue coat values are unusual); judge them in the sim.

## Alias collisions
Aliases are normalised and unique across ALL encyclopedia files. 85 requested aliases were already owned by other articles and were dropped (kept in `data/encyclopedia/_drafts/ideas_alias_dropped.txt`). Notable: "make it pop" and "make my car pop" are owned by `spec.paint_spec_marriage`, "wet look" / "rat rod" / "patina" / "weathered" / "show car" / "mirror chrome" by other articles. The ideas article still carries other phrasings, and the ranker can pick it from title/summary text. Real brand words appear only as aliases, never in article text.

Dropped (article :: alias):
- camo_digital_urban :: digital camo (owned by recipes.camo)
- camo_woodland_desert :: camo (owned by finishes.nature_tactical_cyberpunk)
- camo_woodland_desert :: camouflage (owned by finishes.nature_tactical_cyberpunk)
- camo_woodland_desert :: hunting camo (owned by recipes.camo)
- camo_woodland_desert :: woodland camo (owned by recipes.camo)
- candy_lowrider :: candy apple (owned by recipes.candy)
- candy_lowrider :: candy paint (owned by finishes.gradients_flip_depth_underglow)
- candy_lowrider :: metalflake (owned by recipes.flake_pearl)
- carbon_race_bare :: carbon hood (owned by recipes.carbon_hood)
- carbon_race_bare :: carbon roof (owned by recipes.carbon_hood)
- chrome_show_car :: chrome car (owned by help_howto_2.make_chrome)
- chrome_show_car :: chrome wrap (owned by recipes.chrome_source)
- chrome_show_car :: mirror chrome (owned by help_howto_2.make_chrome)
- chrome_show_car :: show car (owned by controls_spec_sculpt_3.sculpt.show_car.1463)
- clean_classy :: professional look (owned by playbook.composition_rules)
- colour_shift :: chameleon paint (owned by recipes.colour_shift)
- colour_shift :: color flip (owned by finishes.gradients_flip_depth_underglow)
- colour_shift :: color shift (owned by spec.angle_reveal)
- colour_shift :: colour shift (owned by spec.angle_reveal)
- colour_shift :: flip paint (owned by recipes.colour_shift)
- cyberpunk_synthwave :: cyberpunk (owned by finishes.nature_tactical_cyberpunk)
- cyberpunk_synthwave :: synthwave (owned by another ideas article)
- cyberpunk_synthwave :: vaporwave (owned by another ideas article)
- drift_car :: used look (owned by finishes.wear)
- fade_gradient :: colour fade (owned by recipes.gradient_roof_rocker)
- fade_gradient :: fade (owned by recipes.gradient_roof_rocker)
- fade_gradient :: ombre (owned by recipes.gradient_roof_rocker)
- fade_gradient :: sunset fade (owned by recipes.gradient_roof_rocker)
- flames :: add flames (owned by recipes.flames_graphics)
- flames :: blue flames (owned by recipes.flames_graphics)
- flames :: flame job (owned by another ideas article)
- flames :: flames (owned by recipes.flames_graphics)
- flames :: flames on hood (owned by recipes.flames_graphics)
- flames :: hot rod flames (owned by recipes.flames_graphics)
- glass_crystal :: glass look (owned by recipes.wet_glass)
- gulf_style :: gulf style (owned by playbook.scheme_families)
- hex_tech :: hex (owned by zones.add_pick_colour)
- holographic_iridescent :: hologram (owned by recipes.holographic)
- holographic_iridescent :: holographic (owned by recipes.holographic)
- hot_rod_kustom :: hot rod flames (owned by recipes.flames_graphics)
- hot_rod_kustom :: kustom (owned by another ideas article)
- japanese_art :: rising sun (owned by finishes.retro_cultural)
- le_mans_endurance :: endurance livery (owned by another ideas article)
- look_wet :: high gloss (owned by recipes.wet_glass)
- look_wet :: liquid look (owned by recipes.wet_glass)
- look_wet :: make it look wet (owned by recipes.wet_glass)
- look_wet :: wet look (owned by recipes.wet_glass)
- make_it_pop :: make it pop (owned by spec.paint_spec_marriage)
- make_it_pop :: make my car pop (owned by finishes.what_makes_a_finish_pop)
- martini_style :: twin stripes (owned by playbook.scheme_families)
- metal_flake_sparkle :: flake paint (owned by recipes.flake_pearl)
- metal_flake_sparkle :: glitter paint (owned by recipes.flake_pearl)
- metal_flake_sparkle :: metal flake (owned by recipes.flake_pearl)
- metal_flake_sparkle :: metalflake (owned by recipes.flake_pearl)
- monochrome :: one colour (owned by help_howto_1.change_one_colour)
- numbers_match_body :: door number (owned by recipes.add_race_number)
- numbers_match_body :: number colour (owned by help_howto_3.recolour_numbers)
- numbers_match_body :: number contrast (owned by another ideas article)
- pastel :: candy colours (owned by recipes.candy)
- pearl_white :: mica (owned by recipes.flake_pearl)
- pearl_white :: pearl paint (owned by recipes.flake_pearl)
- pearl_white :: pearl white (owned by recipes.flake_pearl)
- pearl_white :: pearlescent (owned by recipes.flake_pearl)
- police_emergency :: cruiser look (owned by another ideas article)
- punk_grunge_street :: grunge look (owned by another ideas article)
- punk_grunge_street :: rough look (owned by another ideas article)
- racing_stripes :: center stripe (owned by recipes.retro_stripes)
- racing_stripes :: racing stripes (owned by recipes.retro_stripes)
- rally :: dirty rally car (owned by recipes.named_looks)
- rat_rod :: rat rod (owned by recipes.weathered)
- stealth_murdered_out :: no shine (owned by support.flat_or_shiny)
- style_menu :: surprise me (owned by finishes.picker_library_browser)
- team_colours :: team livery (owned by recipes.team_liveries)
- two_tone :: two colour car (owned by recipes.two_tone)
- two_tone :: two tone (owned by recipes.two_tone)
- two_tone :: two tone paint (owned by recipes.two_tone)
- vintage_diner_50s :: sock hop (owned by finishes.retro_cultural)
- worn_patina :: aged paint (owned by recipes.weathered)
- worn_patina :: barn find (owned by recipes.weathered)
- worn_patina :: distressed (owned by recipes.weathered)
- worn_patina :: patina (owned by recipes.weathered)
- worn_patina :: rusty (owned by recipes.weathered)
- worn_patina :: sun faded (owned by recipes.weathered)
- worn_patina :: weathered (owned by recipes.weathered)
- worn_patina :: worn paint (owned by finishes.wear)