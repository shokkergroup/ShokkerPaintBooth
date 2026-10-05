# RETIRED SHELVES — 2026-09-05

Owner call: retire the six legacy shelves discussed across 2026-09-04/05.

## What was done, and what deliberately was NOT

**Removed:** the six group entries from `BASE_GROUPS` in `paint-booth-0-finish-data.js`.
That is what takes a shelf out of the picker — an un-grouped base id is dropped from
the picker at boot.

**Kept, on purpose:** every one of the 104 `BASES` entries and every one of their engine
renderers. Verified after the change: **104/104 still render** through
`engine.registry.BASE_REGISTRY` with finite paint and spec output.

That distinction is the whole point. Retiring a shelf must not repaint a customer's
saved car. Hiding them from the picker stops anyone *choosing* them; deleting them
would silently change every design that already used one. Reversing this is a one-line
restore of the six group blocks.

## The 17 places the app itself pointed at a retired id

These were repointed BEFORE the groups were removed, so nothing is left pointing at a
hidden finish:

| was | now | where |
|---|---|---|
| `metallic` | `f_metallic` | built-in presets (6) |
| `chrome` | `f_chrome` | built-in presets (5) + spec-preview tab |
| `candy` | `f_candy` | built-in preset |
| `pearl` | `f_pearl` | built-in presets (2) |
| `carbon_base` | `wrap_twill_film` | built-in preset |
| `brushed_titanium` | `f_brushed` | built-in preset |
| `ceramic` | `wrap_ceramic_coat` | Easy Mode quick list |
| `piano_black` | *(removed)* | Easy Mode quick list — redundant beside `gloss` and `wet_look` |

## Suggested successors for painters

| retired shelf | closest live home |
|---|---|
| Carbon & Composite | WRAP SHOP (`wrap_twill_film`, `wrap_forged*`), FOUNDATION `f_brushed` |
| Ceramic & Glass | WRAP SHOP `wrap_ceramic_coat`, `wrap_laminate`; FOUNDATION gloss ladder |
| Chrome & Mirror | FOUNDATION `f_chrome`, `f_dark_chrome`, `f_satin_chrome` |
| Exotic Metal | FOUNDATION `f_metallic`, `f_matte_metallic`; WRAP SHOP `wrap_brushed_film` |
| Metallic Standard | FOUNDATION `f_metallic`, `f_pearl`, `f_satin_pearl` |
| Candy & Pearl | FOUNDATION `f_candy`, `f_pearl`, plus opal / moonstone / spectraflame / chameleon / hypershift_spectral |

## The full 104

### Carbon & Composite (20)

`aramid`, `carbon_base`, `carbon_ceramic`, `fiberglass`, `forged_composite`, `graphene`, `hybrid_weave`, `kevlar_base`, `carbon_weave`, `forged_carbon_vis`, `carbon_3k_fine`, `carbon_satin`, `carbon_red`, `carbon_blue`, `spread_tow`, `forged_blue`, `nomex_honeycomb`, `kevlar_red`, `basalt_weave`, `dyneema_white`

### Ceramic & Glass (20)

`ceramic`, `ceramic_matte`, `crystal_clear`, `enamel`, `obsidian`, `piano_black`, `porcelain`, `tempered_glass`, `cathedral_glass`, `sea_glass`, `sapphire_glass`, `ruby_glass`, `emerald_glass`, `amber_glass`, `smoked_glass`, `milk_glass`, `mercury_glass`, `crackle_glaze`, `liquid_glaze`, `terracotta_glaze`

### Chrome & Mirror (11)

`antique_chrome`, `black_chrome`, `blue_chrome`, `candy_chrome`, `chrome`, `dark_chrome`, `mirror_gold`, `red_chrome`, `satin_chrome`, `surgical_steel`, `electroplated_gold`

### Exotic Metal (16)

`anodized`, `brushed_aluminum`, `brushed_titanium`, `cobalt_metal`, `diamond_coat`, `frozen`, `liquid_titanium`, `platinum`, `raw_aluminum`, `rose_gold`, `titanium_raw`, `tungsten`, `organic_metal`, `anodized_exotic`, `xirallic`, `chromaflair`

### Metallic Standard (22)

`candy`, `candy_apple`, `champagne`, `copper`, `gunmetal`, `gunmetal_satin`, `metal_flake_base`, `original_metal_flake`, `champagne_flake`, `fine_silver_flake`, `blue_ice_flake`, `bronze_flake`, `gunmetal_flake`, `green_flake`, `fire_flake`, `metallic`, `midnight_pearl`, `pearl`, `pearlescent_white`, `pewter`, `satin_metal`, `alubeam`

### Candy & Pearl (15)

`candy_burgundy`, `candy_cobalt`, `candy_emerald`, `iridescent`, `tinted_clear`, `tri_coat_pearl`, `jelly_pearl`, `orange_peel_gloss`, `satin_candy`, `deep_pearl`, `candy_gold`, `candy_lime`, `candy_aqua`, `copper_pearl`, `coral_pearl`
