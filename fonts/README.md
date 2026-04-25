# SPB Font Library

The Shokker Paint Booth font library is a curated collection of typography presets tuned for racing liveries, sponsor blocks, driver nameplates, and decorative car graphics. Every preset in `font_presets.json` has been chosen for one purpose: looking right on a car at iRacing's TV camera distance, where most viewers will actually see your work.

## What This Library Is

`font_presets.json` is the canonical font preset catalog for SPB's text tool. It is loaded by the text-layer UI and exposed in the font picker as a categorized dropdown. Each preset is a fully-specified typographic recipe — family stack, weight, italic flag, recommended letter-spacing, and a one-line `good_for` hint that tells the user when to reach for that font.

The library does not ship font files. It ships font configurations that reference system fonts and common web-safe fallbacks. SPB renders text using the user's installed system fonts, so a preset like "Brush Script Std, Lucida Handwriting, cursive" will fall through that stack until it finds a font the user actually has — and the final fallback (`cursive`, `serif`, `sans-serif`, `monospace`) guarantees something always renders.

## How SPB Loads Fonts

At app boot, `paint-booth-2-state-zones.js` requests `fonts/font_presets.json` and populates the text-tool font dropdown. The dropdown is grouped by category (Racing Numbers, Sponsor Block, Driver Name, etc.) and each entry shows the preset's display name plus its `good_for` text as hover help. Selecting a preset writes the entire preset object into the active text layer's state.

When the canvas renders text, it uses the browser's text-rendering pipeline (Canvas 2D `fillText`/`strokeText`) which respects the family stack, weight, italic, and letter-spacing values directly. The Python server-side render uses Pillow's `ImageFont.truetype` with the same family stack — the first font that resolves on the host OS wins.

This means: a preset that calls for `Impact, Arial Black, sans-serif` will look identical on Windows (Impact is a system font), nearly identical on macOS (Arial Black is universal), and acceptable on Linux (the generic `sans-serif` fallback substitutes a default sans).

## System Fonts vs Web Fonts

Today, SPB uses **system fonts only**. No webfont (`@font-face`) is fetched at runtime. This is intentional:

- **Reliability:** the engine renders identically online and offline.
- **Speed:** no network round-trip for fonts during a render.
- **Server-side parity:** the Python renderer can only use fonts installed on the host. System-font-only keeps client and server visually aligned.

A future v6.3+ release may add a curated webfont bundle (Bebas Neue, Oswald, Roboto, Montserrat) that ships with the Electron app and is registered with both the browser CSS engine and the Python server's font directory.

## JSON Format Reference

```json
{
  "version": "6.2.0",
  "description": "Font presets for SPB text tool",
  "categories": {
    "Category Name": [
      {
        "name": "Display Name",
        "family": "CSS-style font stack with fallbacks",
        "weight": 100..900,
        "italic": true | false,
        "letter_spacing": -5..+10 (px),
        "good_for": "One-line hint describing when to use this preset"
      }
    ]
  }
}
```

**Field rules:**

- `name`: shown in the picker, must be unique within a category.
- `family`: a CSS-format stack. End with a generic family (`sans-serif`, `serif`, `monospace`, `cursive`) so something always renders.
- `weight`: standard CSS numeric weight. 400 = regular, 700 = bold, 900 = black.
- `italic`: boolean. The text-tool UI exposes a separate italic toggle, but presets can pre-select it.
- `letter_spacing`: pixels added between characters. Negative values tighten (good for display headlines and condensed numbers); positive values loosen (good for caps-and-spaced sponsor blocks).
- `good_for`: free-form hint, ~50-80 characters. Shown as tooltip in the picker.

## How to Add Your Own Presets

1. Open `fonts/font_presets.json`.
2. Pick an existing category that fits, or create a new top-level key under `categories`.
3. Add a new object to the array. Make sure the `name` is unique within that category.
4. Save. SPB will pick it up on next app launch (or use the "Reload Fonts" debug button if you have it enabled).
5. **Test the font stack on the host OS.** Open a text layer, select your preset, and confirm the rendered glyph shape matches your intent. If you see Times New Roman where you expected Eurostile, your stack didn't resolve — add a more common fallback earlier in the chain.

## Best Fonts for Racing Livery

The classics, ranked by frequency of appearance in real-world racing:

1. **Impact / Arial Black** — the universal car-number font. If you do nothing else, use Impact for numbers.
2. **Helvetica / Helvetica Neue** — every clean sponsor block since 1968.
3. **Eurostile / Microgramma** — the "futuristic" font you've seen on a thousand spec series.
4. **Bebas Neue / Oswald** — the modern condensed sans, perfect for tight spaces.
5. **Futura** — vintage Le Mans and Formula 1 era feel.
6. **DIN** — German engineering brands, BMW Motorsport vibe.
7. **Stencil** — military, rally, and tactical/utility aesthetic.

Avoid: Comic Sans (obvious), Papyrus (obvious), Brush Script in tiny sizes (illegible), and any font with thin hairlines (they blow out at speed).

## Font Licensing Note

The font *names* in this library reference fonts that may be licensed software. SPB does not redistribute font files — it only references font names that the user's operating system or installed software is expected to provide. If you ship a livery export that includes rasterized text, no font licensing applies (the text became pixels). If you ship a livery file that contains live editable text and font references, the receiving user needs the same fonts installed.

For commercial livery work and resale, prefer fonts you have license to use:

- All Adobe Creative Cloud users can license Adobe Originals fonts (Source Sans, Source Serif, Source Code Pro).
- Google Fonts (Roboto, Open Sans, Bebas Neue, Oswald, Montserrat, Pacifico, Lobster) are open-source and free for commercial use.
- Microsoft system fonts (Impact, Arial Black, Stencil, Times New Roman) are licensed for use with Microsoft platforms — read your EULA before redistributing rendered output commercially.

## See Also

- `text_templates/README.md` — pre-configured text layer setups that combine font presets with size, color, stroke, and shadow.
- `SPB_TYPOGRAPHY_GUIDE.md` — typography theory and best practices for racing livery.
- `paint-booth-0-finish-data.js` — base paint and pattern catalogs that interact with text overlays.
