# SPB Decal Metadata Library

This folder holds the JSON metadata that Shokker Paint Booth uses to suggest decal placement, sponsor block layouts, number panel styles, series identifiers, and mandatory safety markings on a livery. None of these files contain raster artwork; they are pure metadata that tells the Booth UI where things should go and how they should be styled.

## What decal metadata is

A decal in SPB is a placeable graphic that is *not* part of the underlying paint physics. Decals live on dedicated PSD layers (Sponsors, Numbers, Tape) and sit on top of the painted finish. While the engine itself does not render the decals, it needs to know:

- where each decal class typically lives on the body
- how big it usually is (in UV space, so it scales with the car)
- what stroke, shadow, and contrast rules apply
- what aspect ratio and grid alignment to expect
- which decals are *mandatory* in regulated series

This library is the source of truth for those answers. The UI surfaces the data as alignment hints, snap targets, "missing safety decal" warnings, and pre-built sponsor stack templates.

## How SPB consumes the data

The five JSON files break the decal universe into orthogonal categories:

| File | Contains |
|------|----------|
| `number_panels.json` | 10 number panel presets (NASCAR, GT3, F1, IndyCar, LMP, dirt, vintage) |
| `contingency_stacks.json` | 8 sponsor stack layouts (vertical, horizontal, grid) |
| `series_logos.json` | 12 racing series identifiers (generic descriptions, no trademark) |
| `sponsor_blocks.json` | 8 common sponsor block placement templates |
| `safety_required.json` | 6 mandatory safety / regulatory decals |

Each file shares a similar structure — a top-level `version` and `description`, followed by a `schema` block explaining the field meanings, then an array of preset entries.

When the user drops a decal onto the canvas, SPB looks up the closest matching preset and applies the `size_hint_uv`, `stroke`, `drop_shadow`, and alignment rules automatically. The user can override any of them, but the defaults match real-world racing conventions, so first-pass placements feel correct.

## JSON schema reference

All five files follow this convention:

```json
{
  "version": "6.2.0",
  "description": "what this file is for",
  "schema": {
    "field_name": "type and meaning"
  },
  "<top_level_array>": [
    { "id": "...", "name": "...", "...": "..." }
  ]
}
```

The `schema` block is human-readable, not JSON Schema validated — it documents the shape of the entries below for whoever is editing the file. The top-level array is named for the entity (`panels`, `stacks`, `series`, `blocks`, `decals`).

### Common field types

- **id** — lowercase snake_case string, must be unique within the file
- **size_hint_uv** — `[width, height]` in UV space, both 0..1, where 1 is the full body width or height
- **placement** / **good_for** — string array of zone names from the SPB zone vocabulary
- **stroke / drop_shadow** — graphic styling instructions used by the renderer overlay
- **notes / tips** — freeform text shown in the UI as tooltips

UV space is used everywhere because the actual pixel dimensions depend on the chassis being painted. A NASCAR door panel and an F1 nose panel both use 0..1 UV coordinates; the Booth scales them to physical pixels at render time.

## How to add a custom decal preset

1. Decide which of the five files your preset belongs in. Number panels and roundels go in `number_panels.json`. Stacks of small sponsor logos go in `contingency_stacks.json`. Series-specific identifiers go in `series_logos.json`. Single-logo sponsor zones go in `sponsor_blocks.json`. Required regulatory decals go in `safety_required.json`.
2. Add a new entry to the appropriate top-level array. Pick a unique `id` in lowercase snake_case (e.g., `imsa_pro3_door`, `vintage_bonneville_strip`).
3. Fill in every field shown in the file's `schema` block. Don't omit `notes` — the UI shows them as tooltips when a user hovers over the preset.
4. If your preset references a placement zone that does not yet exist in the SPB zone vocabulary, add it to the master zone list first. Otherwise the UI will warn that the zone is unknown.
5. Bump the file's `version` field if the change is part of a Booth release. Patch bumps are fine for additive changes; minor bumps for shape changes; major bumps if you rename or remove fields that existing presets rely on.

## Layer convention

By Booth convention, decals are painted on one of three reserved PSD layers:

- **Sponsors** — primary, secondary, associate, and contingency sponsor blocks. Most entries from `sponsor_blocks.json` and `contingency_stacks.json` end up here.
- **Numbers** — number panels and class indicators. Entries from `number_panels.json` belong on this layer. Some series also keep series identifiers (from `series_logos.json`) on the Numbers layer; others keep them on Sponsors.
- **Tape** — mandatory regulatory and safety markings. Entries from `safety_required.json` always go here. The Tape layer is locked by default to prevent accidental modification of safety decals.

When SPB exports a livery, the Tape layer is rendered last (on top of everything else) so safety decals are never occluded by sponsor art. The Numbers layer is rendered second-to-last for the same reason.

## Validation

All five JSON files are valid JSON-with-comments-disallowed (strict). Run `python -m json.tool decals/<file>.json` from the repo root to validate any change. Pre-commit hooks should reject malformed JSON in this folder.

## Versioning

All files are versioned together at the top-level. The current library version is `6.2.0`, matching the Gold-to-Platinum experimental release. Don't fork file versions — keep them in lockstep so the Booth can validate the entire library at once.

## Trademark policy

`series_logos.json` uses generic descriptions only (e.g., "Premier Stock Car Series" rather than the actual series name). This is deliberate — SPB ships without any trademarked content, and end users supply their own logo art at livery-design time. The metadata is purely advisory: it tells the user *where* a series logo typically goes, not *what* the logo looks like.
