# SPB Helmets Library

This directory contains the metadata library that drives Shokker Paint Booth's helmet design system. SPB ships every helmet template definition, UV zone map, and built-in style preset as plain JSON so that artists, integrators, and downstream tools can reason about the data without parsing engine code.

## Contents

| File | Purpose |
|------|---------|
| `catalog.json` | Defines available helmet templates: canvas size, UV zone names, iRacing folder/filename conventions, spec-map support, and DPI defaults. |
| `styles.json` | Ships built-in helmet design presets: per-zone color / pattern recipes, finish + spec settings, and category tags. |

Both files are versioned with the SPB build number (currently `6.2.0`) so consumers can detect schema upgrades.

## Helmet Metadata Format

### Templates (`catalog.json`)

A template describes a *physical helmet model* — its UV layout, expected pixel resolution, and the file-naming rules iRacing requires when the asset is exported.

Required fields:

- `id` — stable string identifier used by the booth and downstream tools.
- `name` — human-readable display name in the picker.
- `canvas_size` — `[width, height]` pixel dimensions for both the diffuse and spec map.
- `uv_zones` — ordered list of UV island names. SPB's zone tool maps each name to a paintable region.
- `iracing_folder` — folder name (relative to the user's iRacing custom paint root) where the file is dropped.
- `filename_convention` / `spec_filename` — the iRacing filename pattern with `<iracing_id>` or `<slug>` placeholder.
- `default_dpi` — base DPI used for SPB's preview rendering.
- `supports_spec_map` — `true` if the template expects a paired `_spec.tga` companion.
- `alpha_supported` — set to `true` only for SPB-native templates that allow transparent regions.
- `notes` — short prose about the template's intended use case.

### Styles (`styles.json`)

A style is a *complete design recipe* the user can drop on a helmet template as a starting point. Every style provides:

- `id` / `name` / `category` — identification and picker grouping.
- `primary_color` / `secondary_color` / `tertiary_color` — RGB triples used by the zone recipes.
- `zones` — keyed by UV zone name, each value is a *recipe expression* (e.g. `primary`, `gradient_primary_to_secondary`, `carbon_weave_pattern_with_tertiary_logo`). The zone engine resolves the expression against SPB's pattern + finish registries.
- `finish` — top-level finish category (`gloss`, `matte`, `satin`, `gloss_with_chrome`, `satin_carbon`, etc.).
- `spec` — default spec-map values: `metallic` (R), `roughness` (G), `clearcoat` (B). Use `zone_chrome_only: true` to scope chrome to specific zones rather than the whole shell.
- `notes` — usage tips and pairing recommendations.

## How SPB Uses Helmet Styles

1. The user opens the helmet workspace and chooses a template from `catalog.json`.
2. SPB instantiates the canvas, builds the UV zone overlay, and offers the style picker filtered to that template's compatible zone names.
3. When a style is applied, each zone recipe expression is resolved into pattern + color + finish operations, which are pushed onto the engine the same way a car-paint zone works. This lets the helmet share every paint, pattern, and spec preset already in the booth.
4. The user can override individual zones from the style without losing the rest, then export to TGA following the template's filename convention.

## Adding Custom Helmet Templates

To add a new helmet model:

1. Append a new entry to the `templates` array in `catalog.json`.
2. Pick a unique `id` and define the `uv_zones` exactly as the source helmet model's UV islands are named in the engine.
3. If the new template introduces zone names not yet in `uv_zone_descriptions`, add them so the picker tooltips render correctly.
4. (Optional) Add new style presets in `styles.json` whose `zones` map matches the new template's UV zones.
5. Bump the `version` field if the schema changes in a backwards-incompatible way.

## Adding Custom Helmet Styles

To author a new style preset:

1. Decide which template family the style targets (its zone names need to match the recipe keys).
2. Create a new entry in `styles.json` with a unique `id`, sensible `category`, three colors, and per-zone recipe expressions.
3. Pick a `finish` from the SPB finish registry and tune the `spec` triple (metallic/roughness/clearcoat) to taste — see `SPB_HELMET_GUIDE.md` for the practical ranges that read well in iRacing's lighting.
4. Test by selecting the new style in the helmet picker and verifying every zone resolves without falling back to the default.

## Related Documentation

- `SPB_HELMET_GUIDE.md` — full tutorial on designing and exporting helmets.
- `SPB_IRACING_INTEGRATION.md` — file system layout, naming conventions, and live preview rules.
- `SPB_LIVE_LINK_GUIDE.md` — auto-export workflow that drops new helmets into iRacing on save.
