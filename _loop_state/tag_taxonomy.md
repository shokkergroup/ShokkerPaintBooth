# SPB Smart Tag Taxonomy

**Owner-approved canonical list of tags** auto-applied by
`scripts/build_finish_tags.py` and recognized by the fuzzy search layer in
`paint-booth-2-state-zones.js` (`_libraryItemMatchesSearch`, `_getLibrarySearchText`).

Tags are lowercase, kebab-case where multi-word, and live on each finish id in
`paint-booth-0-finish-tags.js` as `FINISH_TAGS[id] = ["tag1", "tag2", ...]`.

The auto-tagger derives tags from three sources:

1. **Id-prefix seeds** — `p_*` -> `paradigm,showcase`; `vm_*` -> `viva-mexico,cultural,showcase`; `anime_*` -> `anime,cultural`; etc.
2. **Name/description keyword scan** — case-insensitive substring against `TAG_KEYWORDS` in the script.
3. **Group-label hints** — currently scaffolded but not wired in (the script does not yet read `BASE_GROUPS`/`PATTERN_GROUPS`; that's a future enhancement).

## Canonical tag list

### Color family
red, blue, green, purple, pink, orange, yellow, copper, gold, silver, black, white, grey, cyan, neon, multicolor, iridescent, holographic

### Material
metallic, pearl, candy, carbon, aramid, weave, forged, chrome, ceramic, glass, satin, matte, gloss, vinyl, anodized, flake, sparkle, shimmer

### Style / mood
racing, luxury, military, tactical, stealth, vintage, retro, modern, futuristic, cyber, gothic, dark, industrial, organic, alien, showroom, drift, offroad, bright, warm, cold, deep, reflective

### Era
era-50s, era-60s, era-70s, era-80s, era-90s, muscle

### Theme
fire, ice, water, weather, lightning, aurora, space, predator-skin, scales, anime, cultural, sunset

### Texture
smooth, rough, hammered, brushed, weathered, distressed, rust, polished

### Special use-case
emergency, paradigm, viva-mexico, prism-forge, rising-sun, colorshoxx, showcase

### Notes
- `iridescent` is awarded by both color (rainbow, prizm, holographic) and material (beetle, crystal).
- `weathered` doubles as a state and a style — most aged finishes pick it up.
- The keyword `water` over-fires on text mentioning "ocean horizon" or "marine" descriptors. Expect false positives like `battleship_gray` getting `water`. Owner manual pass should prune.

## Untagged finishes

The script prints any finish that got zero tags. As of the first run there are
163 such finishes — most are short cryptic names (`shokk_helix`,
`shokk_polarity`, `glitch_scan`, etc.) where neither the name nor the brief
description match any taxonomy keyword. These need an owner manual pass or an
expansion to the keyword map.

## How to update

1. Edit `TAG_KEYWORDS`, `ID_PREFIX_TAGS`, or `GROUP_LABEL_TAGS` in `scripts/build_finish_tags.py`.
2. Re-run `python scripts/build_finish_tags.py`.
3. Verify the new `paint-booth-0-finish-tags.js` md5 is identical in all 3
   mirror locations (the script does this for you).
4. Open the booth UI, search for the new tag — finishes should now surface.
