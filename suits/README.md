# SPB Suits Library

This directory holds the metadata library that drives Shokker Paint Booth's driver suit design system. Like the helmet library, every template definition, UV zone map, and style preset is shipped as plain JSON so external tools and integrators can consume the data without touching engine code.

## Contents

| File | Purpose |
|------|---------|
| `catalog.json` | Defines available suit templates: canvas size, UV zone names, iRacing folder/filename conventions, spec-map support, and DPI defaults. |
| `styles.json` | Ships built-in driver suit style presets: per-zone color/pattern recipes, finish + spec settings, and category tags. |

Both files share the SPB build version (`6.2.0`) so downstream consumers can detect schema upgrades cleanly.

## Suit Metadata Format

### Templates (`catalog.json`)

A template describes a *physical suit cut* — one-piece pro, vintage two-piece, or SPB-native with extended sponsor zones. Required fields mirror the helmet catalog:

- `id`, `name`, `canvas_size`, `uv_zones`
- `iracing_folder`, `filename_convention`, `spec_filename`
- `default_dpi`, `supports_spec_map`, `alpha_supported`
- `notes`

The big difference from helmets is that suits typically have ten or more UV zones (chest, back, two arms, two legs, collar, belt, two shoulders, plus optional cuffs/knee panels and SPB-native logo fields). The zone engine handles the larger zone count the same way regardless.

### Styles (`styles.json`)

Each style provides:

- `id`, `name`, `category`
- `primary_color` / `secondary_color` / `tertiary_color`
- `zones` — recipe expression per UV zone
- `finish` — usually `matte` for realistic Nomex-style fabric, but `satin` works well for tech/carbon-accent looks
- `spec` — values like `roughness: 220` and `clearcoat: 200` are typical for fabric (very dull, no clearcoat shine). Avoid setting `metallic` above 60 unless you are intentionally going for a foil/exotic look.
- `notes` — pairing recommendations (which helmet preset matches, which template families it fits)

## How SPB Uses Suit Styles

1. The user opens the suit workspace and chooses a template from `catalog.json`.
2. SPB instantiates the canvas, builds the UV zone overlay, and shows the style picker filtered to the template.
3. When a style is applied, each zone recipe expression is resolved into pattern + color + finish operations and pushed onto the engine — the same pipeline that paints car bodies and helmets.
4. The user can override any zone without touching the rest, then export to TGA following the template's iRacing filename pattern.

## Adding Custom Suit Templates

1. Append a new entry to the `templates` array in `catalog.json`.
2. Use a unique `id` and ensure `uv_zones` exactly matches the source model's UV island names.
3. Add new zone names to `uv_zone_descriptions` so the picker tooltips render properly.
4. (Optional) Author matching styles in `styles.json` whose `zones` keys match the new template.
5. Bump the `version` field on any breaking schema change.

## Adding Custom Suit Styles

1. Confirm which template family you're targeting (zone names must match).
2. Add an entry to `styles.json` with a unique `id`, sensible `category`, three colors, and per-zone recipes.
3. Choose a fabric-appropriate `finish` and tune the `spec` triple. For most suit work: `metallic: 0`, `roughness: 200-230`, `clearcoat: 180-220`.
4. Test by selecting the style in the suit picker and verifying every zone resolves without fallback.

## Working as a Set

Suits and helmets are usually designed together. SPB's "set" mode lets you apply a paired helmet style and suit style at once, sharing the primary/secondary/tertiary palette across both. When authoring a new suit style, consider also authoring a matching helmet style with the same color triple — see `SPB_SUIT_GUIDE.md` for guidance on coordinated kit design.

## Related Documentation

- `SPB_SUIT_GUIDE.md` — full tutorial on designing and exporting suits.
- `SPB_IRACING_INTEGRATION.md` — file system layout, naming conventions, and live preview rules.
- `SPB_LIVE_LINK_GUIDE.md` — auto-export workflow that drops new suits into iRacing on save.
