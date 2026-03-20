# Base Overlay Blend Modes — FAQ

This document describes all **10 blend modes** for Base Overlay layers (2nd, 3rd, 4th, and 5th base) in Shokker Paint Booth. Each overlay can use a different blend mode to control **where** and **how** the overlay material appears over the primary base.

---

## React to Pattern (all modes)

Every blend mode uses the **React to zone pattern** settings:

- **React to** — Which pattern drives the overlay (zone pattern or another pattern).
- **Invert mask** — Swap pattern light/dark so the overlay appears where the pattern was dark.
- **Harden** — Restrict overlay to only the strongest pattern areas.
- **Opacity, Scale, Rotate, Strength** — Control the pattern’s size, rotation, and intensity.
- **Position X / Y** — Pan the pattern.

So every mode is **pattern-aware**: the same pattern controls can be used with Fractal Dust, Liquid Swirl, or any of the pattern-only modes.

---

## The 10 Blend Modes

### 1. ✨ Fractal Dust

**What it does:** Tiny, sharp “sparkle” or dust particles. The overlay appears as fine flakes or grit.

**How it works:** Procedural multi-scale noise is shaped with a power curve to create small bright peaks. When a pattern is selected, that pattern **masks** the dust: dust only shows where the pattern is (and is scaled by pattern brightness). So you get sparkles only inside your pattern shape.

**Good for:** Metallic flake in pattern areas, glitter, fine texture that respects the pattern.

**Extra controls (when this mode is selected):** Fractal Detail (noise scale), Overlay Scale.

---

### 2. 🌪️ Liquid Swirl

**What it does:** Smooth, flowing bands like marble or liquid swirls.

**How it works:** Multi-scale noise is warped and passed through sine bands to create flowing streaks. When a pattern is selected, the swirl is **multiplied** by the pattern: swirls only appear (or are stronger) where the pattern is.

**Good for:** Marble or liquid effects inside logos, veins that follow the pattern.

**Extra controls (when this mode is selected):** Fractal Detail, Overlay Scale.

---

### 3. 📐 Pattern Edges

**What it does:** Overlay appears **along the edges** of the pattern (outlines/rims).

**How it works:** The pattern’s gradient (rate of change) is computed; overlay strength is highest where the pattern value changes fastest (edges). So you get a rim or outline effect instead of a fill.

**Good for:** Chrome or metallic outlines, accent lines along pattern boundaries, “only the edges” look.

**Requires:** A pattern selected in React to pattern. If no pattern is available, the mode falls back to a uniform blend.

---

### 4. 🔷 Pattern-Reactive

**What it does:** Overlay follows the pattern as a **smooth gradient**: brighter pattern = more overlay, darker = more base.

**How it works:** Blend alpha = pattern value × strength. So you get a continuous blend that follows the pattern’s brightness.

**Good for:** Natural, soft placement of the overlay; full control over how much overlay shows where.

---

### 5. 💥 Pattern-Pop

**What it does:** Overlay appears at **full intensity** only in the **brightest** parts of the pattern. Strength controls **how much** of the pattern area gets that full overlay (threshold), not how strong the blend is.

**How it works:** A threshold is set from strength (e.g. strength = 0.5 → top 50% of pattern brightness gets full overlay). Where the pattern is above threshold, alpha = 100%; below, 0%. So no dulling—full overlay where it shows.

**Good for:** Punchy, selective placement; “only the hot spots” of the pattern.

---

### 6. 🎨 Tint (subtle)

**What it does:** Overlay **tints** the base without fully covering it. Overlay is capped so the base always shows through.

**How it works:** Same as Pattern-Reactive (pattern × strength) but alpha is limited to about 35% max. So you get a subtle color or material shift in pattern areas.

**Good for:** Gentle color shift, tinted clear, subtle accent without replacing the base.

---

### 7. ⛰️ Pattern Peaks

**What it does:** Overlay appears on the **ridges** or **peaks** of the pattern (where the pattern is locally brighter than its neighborhood).

**How it works:** The pattern is blurred; “peaks” = pattern minus blurred pattern (positive values). Overlay is strongest where the pattern stands out as a ridge.

**Good for:** Embossed or relief looks; highlighting raised parts of the pattern.

**Requires:** A pattern selected in React to pattern.

---

### 8. 〰️ Pattern Contour

**What it does:** Overlay appears in a **narrow band** (contour line) of pattern value. Strength sets **where** that band is (e.g. low strength = dark band, high strength = bright band).

**How it works:** A band of pattern values is selected around a center derived from strength. Only pixels in that band get the overlay, giving an iso-line or contour effect.

**Good for:** Graphic, map-like contour lines; single “level” of the pattern highlighted.

**Requires:** A pattern selected in React to pattern.

---

### 9. ✨ Pattern Screen

**What it does:** Overlay is blended with the base using a **Screen** blend (brightening) in pattern-driven areas, instead of a simple mix.

**How it works:** Alpha is still pattern × strength. Where alpha is applied, the result is **screen**(base, overlay) instead of a linear blend. Screen brightens: result = 1 − (1 − base)(1 − overlay).

**Good for:** Brighter, more luminous overlay in pattern areas; specular or glow that respects the pattern.

**Requires:** A pattern selected in React to pattern.

---

### 10. ◐ Pattern Threshold

**What it does:** Overlay appears in the **darks and the lights** of the pattern; the **midtones** keep the base. Strength controls how wide the “midtone” band is.

**How it works:** Two bands are defined (low and high pattern values). Overlay shows where pattern is below the low threshold or above the high threshold; in between (midtones), the base shows.

**Good for:** “Shadow and highlight” accent; overlay in both dark and bright pattern areas with base in the middle.

**Requires:** A pattern selected in React to pattern.

---

## Summary Table

| Mode              | Pattern used as…        | Best for                          |
|-------------------|-------------------------|-----------------------------------|
| Fractal Dust      | Mask for sparkles       | Flake/glitter in pattern          |
| Liquid Swirl      | Mask for swirls         | Marble/veins in pattern           |
| Pattern Edges     | Edge detector           | Outlines, rims                    |
| Pattern-Reactive  | Gradient (smooth blend)  | Natural, soft overlay             |
| Pattern-Pop       | Threshold (full/zero)   | Punchy, selective overlay         |
| Tint              | Gradient, capped        | Subtle color shift                |
| Pattern Peaks     | Ridge/peak detector     | Embossed, relief                  |
| Pattern Contour   | Iso-band                | Contour lines                     |
| Pattern Screen    | Gradient + screen blend | Bright, luminous overlay          |
| Pattern Threshold | Darks + lights          | Shadow/highlight accent           |

---

## Tips

- Use **Invert mask** in React to pattern to put the overlay in the “negative” of the pattern (e.g. background instead of logo).
- **Fractal Dust** and **Liquid Swirl** still use **Fractal Detail** and **Overlay Scale** when those modes are selected; other modes only use the React to pattern controls.
- For maximum “pop,” combine **Pattern-Pop** with a high-contrast pattern and a strong overlay base (e.g. chrome).
- **Pattern Screen** is especially useful for specular or light-colored overlays where you want a brightening effect instead of a simple mix.
