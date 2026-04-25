# Shokker Paint Booth — Recipe Library

Downloadable preset liveries. Each `.json` file in this folder is a complete SPB zone configuration that loads straight into the app via the **Import Config** button.

Recipes are your head start. They ship with a full set of zones, finish assignments, colors, and sensible defaults — so you can open a recipe, tweak your team color and sponsor logos, and be racing a polished livery in minutes instead of hours.

---

## What a recipe is

A recipe is a JSON file describing a complete paint job: the zones (color rules), the base finish, pattern, intensity, and color defaults for each. It is the exact same format SPB uses when you click **Export Config** on a paint you built yourself — which means every livery in this folder was built in the tool you have in front of you, and you can export your own paints as new recipes any time.

Top-level fields:

| Field | Purpose |
|---|---|
| `name` | Human-readable recipe name (shown in SHOKK library UI) |
| `description` | One-line pitch — what look this recipe delivers |
| `author` | Who built it (Shokker Paint Booth, or community contributor handle) |
| `version` | SPB version this recipe targets (backward-compatible across 6.x) |
| `compatible_with` | Which chassis/car types this recipe suits |
| `notes` | Tuning tips, color variants, known quirks |
| `zones` | Array of zone objects — the heart of the recipe |

Each zone has (at minimum) a `name`, a color selector (`color` + `colorMode` + `pickerColor` + `pickerTolerance`), a `base` (the foundation finish), an optional `pattern`, and an `intensity`. Optional fields cover advanced features — gradient stops, secondary/tertiary bases, pattern stacks, wear level, etc. Unused fields fall back to sane defaults on import.

---

## How to use a recipe

**Method 1 — via the SHOKK library (easiest):**
1. Open SPB.
2. Open the SHOKK panel (top-right sidebar).
3. Browse the Recipes tab, click the recipe you want, and hit **Load**.
4. Your zone list is replaced with the recipe's zones.
5. Tweak colors and sponsors, then render.

**Method 2 — via Import Config (direct file):**
1. Open SPB.
2. Click the **Import Config** button in the top toolbar.
3. Select a `.json` file from this folder.
4. Confirm the replace-zones dialog.
5. Tweak as above.

**Method 3 — via URL share (community recipes):**
Recipes can be shared via GitHub gists, Discord, or any file host. Anyone with the `.json` can drop it into their own recipes folder.

---

## Tips for customizing

- **Start with team color first.** The `Body` zone's `baseColor` hex is almost always the right first edit. Changing it re-themes the whole livery.
- **Don't touch the `color` / `colorMode` fields unless you know what you're doing.** Those drive the pixel-selection logic, and changing them changes what part of the car a zone covers.
- **Sponsor zones pick up white pixels by default.** If your paint file uses a different sponsor-panel color, update the `pickerColor` and `pickerTolerance` on the Sponsors zone.
- **Wear / weathering.** Every zone supports a `wear` field (0-100). Global wear is also controlled by the export slider.
- **Layer effects and PSD layers are not baked into recipes.** Recipes are pure zone rules — bring your own paint file.
- **Pattern intensity.** Dial `patternIntensity` (0-100) on a zone to make a pattern subtle vs. dominant.

---

## Contributing a recipe

Want to submit your own recipe to the library? We love that. Here's how:

1. Build the livery in SPB until it hits the look you want.
2. Click **Export Config** and save the JSON.
3. Open it in a text editor and fill in a good `description`, `author`, and `notes`.
4. Give it a clean filename: `lowercase_with_underscores.json`.
5. Rename zones to be clear (`Body`, `Sponsors`, `Numbers` — not `Body Color 1`).
6. Remove any personal data (driver name, iRacing ID) from top-level fields.
7. Submit via Discord (QR in the install folder) or GitHub PR.

We curate submissions for quality and variety — so make yours distinctive. "Blue car with a white stripe" is not distinctive. "Pearl-shift body that flips teal in shadow with hand-drawn tribal accent" is.

---

## Recipe format reference (minimal)

```json
{
  "name": "My Recipe",
  "description": "One-line pitch.",
  "author": "Your Handle",
  "version": "6.2.0",
  "compatible_with": "any chassis",
  "notes": "Tuning tips here.",
  "zones": [
    {
      "name": "Body",
      "color": "everything",
      "base": "gloss",
      "pattern": "none",
      "intensity": "100",
      "colorMode": "special",
      "baseColor": "#ff0000",
      "baseColorMode": "solid"
    }
  ]
}
```

Valid `base` and `pattern` IDs are listed in `finish_ids_canonical.json` at the project root. Invalid IDs will silently render as nothing — so check that list when building custom recipes.

---

## Versioning and compatibility

- Recipes are tagged with a `version` field (e.g. `6.2.0`).
- Recipes are **backward-compatible** within SPB 6.x — a v6.0 recipe still loads cleanly in v6.2+.
- Forward-compatibility is not guaranteed — a v7.0 recipe may use fields SPB 6.x does not understand. Unknown fields are ignored on import, but the final look may differ.
- When in doubt, rebuild the recipe in the current version of SPB and re-export.

---

## Current library (v6.2.0)

See the top-level `SPB_GUIDE.md` for the one-line tour of all shipping recipes. File-level details live in each recipe's `description` and `notes` fields — open them in a text editor for a quick preview before importing.

— The Shokker team
