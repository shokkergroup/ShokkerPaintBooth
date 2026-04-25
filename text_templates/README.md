# SPB Text Templates

Text templates are pre-configured text layer setups for SPB's text tool. Where the font library (`fonts/font_presets.json`) gives you a typographic recipe — family, weight, italic, tracking — a text template gives you the *whole text layer*, ready to drop on the car: typeface, size, color, stroke, shadow, alignment, and even sample text content.

## What Templates Are

A template answers the question "I want a racing number — what does that look like?" with a complete answer:

- The right font (Impact, weight 900, no italic).
- The right size (~200px for a door number).
- The right color (white fill).
- The right stroke (8px black outline for TV legibility).
- The right shadow (4/4 black, 50% opacity, no blur).
- Sample text ("55") so you immediately see how it sits.

Each template is a single JSON file in this directory. SPB exposes the templates as a "Quick Templates" section in the text tool — click a template, get a fully-formed text layer added to the active zone, then edit the text content and tweak as needed.

## How to Use Templates

1. Open the text tool (T key, or click the text icon in the toolbar).
2. In the right-side panel, find the "Templates" tab.
3. Click a template tile. A new text layer is added to the currently selected zone using the template's full configuration.
4. Edit the text in the live editor — change "55" to your actual car number, change "SPONSOR" to the actual sponsor name, etc.
5. Use the variant dropdown (if the template has variants) to switch between built-in alternatives (e.g., "Inverted (Dark Base)").
6. Adjust size, position, and rotation as normal.

## Templates in This Library

| File | Use For |
|------|---------|
| `racing_number.json` | Main car number on door, roof, nose. 2-3 digits. |
| `sponsor_block.json` | Primary title sponsor name. Hood, door upper, rear quarter. |
| `driver_name.json` | Driver name above the door, NASCAR-style. |
| `team_logo.json` | Team brand identity text. Nose, C-pillar, repeated accents. |
| `contingency_stack.json` | Stacked small associate sponsors. Rocker panel, wheel arch area. |

## How to Create Your Own Templates

1. Copy one of the existing templates as a starting point (e.g., copy `sponsor_block.json` to `my_template.json`).
2. Edit the JSON fields (see format reference below).
3. Save the file in this directory.
4. SPB will pick it up on next app launch.

For best results, build a template by first creating the look you want directly in the text tool (set font, size, color, stroke, shadow, alignment until it looks right), then export the text layer's state as JSON via the "Export as Template" debug button (if enabled) or copy the values manually into a new template file.

## JSON Format Reference

```json
{
  "name": "Display Name",
  "description": "What this template is for, when to use it",
  "category": "Numbers" | "Sponsor" | "Driver" | "Branding" | "Decorative",
  "version": "6.2.0",
  "template": {
    "text": "Sample content",
    "font_family": "CSS font stack with fallbacks",
    "font_weight": 100..900,
    "font_size": 8..400 (px),
    "italic": true | false,
    "color": "#hex",
    "stroke_color": "#hex",
    "stroke_width": 0..20 (px),
    "shadow": {
      "color": "#hex",
      "opacity": 0.0..1.0,
      "dx": -20..20 (px),
      "dy": -20..20 (px),
      "blur": 0..20 (px)
    },
    "alignment": "left" | "center" | "right",
    "letter_spacing": -5..+10 (px),
    "line_height": 0.8..2.0,
    "rotation": -180..180 (degrees),
    "anchor_x": 0.0..1.0,
    "anchor_y": 0.0..1.0
  },
  "placement_hints": {
    "recommended_zones": ["zone_name", ...],
    "min_size_px": int,
    "max_size_px": int,
    "safe_area_padding_px": int
  },
  "variants": [
    {
      "name": "Variant Display Name",
      "overrides": { "any field from template": "new value" }
    }
  ],
  "compatible_finishes": ["finish_name", ...],
  "notes": "Free-form designer notes about edge cases, sizing tips, etc."
}
```

**Anchor coordinates** (`anchor_x`, `anchor_y`) define which part of the text bounding box sits at the layer's position. `0.5, 0.5` is center-anchored (text grows in all directions from its position). `0.0, 0.0` is top-left anchored (text grows down and to the right).

**Variants** are pre-baked alternatives — instead of cloning the whole template, a variant lists only the fields it overrides. The variant dropdown in the UI lets a user A/B between a default and any number of variants without manual re-tweaking.

## Contribution Guide

If you build a template you'd like included in the default SPB distribution:

1. Make sure the JSON validates (use any JSON linter).
2. Use realistic sample text (a real number, a real-looking sponsor name).
3. Include a `description` that explains the design decisions ("why bold italic" not just "bold italic").
4. Add at least 2 `variants` — typically a dark-base counterpart and a stylistic alternative.
5. List `compatible_finishes` honestly — text with a thin stroke disappears on busy metallic flake bases, so don't claim compatibility you can't deliver.
6. Add `notes` covering known edge cases (long names, single-digit numbers, etc.).
7. Submit via PR or drop the file in the SPB user-templates directory and request inclusion.

## See Also

- `fonts/README.md` — the font preset library that templates reference.
- `SPB_TYPOGRAPHY_GUIDE.md` — typography theory, sizing guidelines, readability at speed.
- The text tool documentation in the in-app help drawer.
