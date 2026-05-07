# SPB Helmet Design Guide

Shokker Paint Booth treats a helmet the same way it treats a car body: a physical surface broken into UV zones, each zone painted with a base color, optional pattern, and a spec-map setting that controls metallic, roughness, and clearcoat. This guide walks through everything you need to design helmets that read well in iRacing and pair cleanly with the rest of a driver kit.

## 1. Helmet UV Layout Explained

Every helmet template in `helmets/catalog.json` declares a `uv_zones` list. The default iRacing helmet layout is:

- `top` — the crown of the shell, the most-visible zone from broadcast and the most-visible zone in racing replays from the chase camera.
- `left` and `right` — the side panels. These are your sponsor and identity panels; the camera spends a lot of time on these in cockpit and side-by-side replays.
- `back` — the rear panel, which the camera behind the car sees constantly. Driver names and country flags traditionally live here.
- `front` — the brow above the visor. Smaller than people expect, but very visible from the front-on broadcast camera.
- `visor` — a separate UV island. Treat this as its own object: it has its own color, its own finish (clear, smoke, chrome, iridescent), and its own spec values.
- `chinbar` — the lower chin section. Frequently used for a single accent color to break up the visor band.

Higher-resolution templates (`iracing_hd_helmet`, `fullface_aero`, `spb_native_2k`) add zones like `neck_skirt`, duct cutouts, a `tearoff_strip` lane on the visor, an interior liner, and an explicit `name_strip` zone.

When you open the helmet workspace, SPB renders these zones as a click-to-paint overlay on the helmet preview. Any zone you don't explicitly paint inherits the template's default base color so you never end up with a pink "missing material" zone in iRacing.

## 2. Common Placement Zones

A helmet design that reads on track usually follows a hierarchy:

1. **Top** carries the strongest single statement — a stripe, a graphic, a flag motif, or a bold solid color.
2. **Sides** carry the personality — sponsor logos, secondary graphics, or a side accent stripe.
3. **Back** carries identity — driver name, country flag, or a smaller graphic that differentiates the design from a clone.
4. **Visor** sets the mood — clear visors look classic, smoke/dark visors look modern, chrome and iridescent visors look premium.
5. **Chinbar** acts as a frame — usually a single accent color that ties everything together.

Designs that try to put a major graphic in every zone read as cluttered in motion. SPB's preview camera lets you orbit and check the design at race speeds before exporting.

## 3. Helmet vs Car Paint Coordination

A helmet is part of a kit. Most professional designs share **two of three** primary colors with the car so the driver reads as part of their team without looking like a costume. The third color is the helmet's personal accent — the thing that makes a driver recognizable across teams and across years.

In SPB you can pin the car's primary/secondary palette and the helmet workspace will offer those as the first two color slots, with a third "personal accent" slot that defaults to the driver's saved accent color.

## 4. Visor Color Choices

The visor is the single most impactful style choice on a helmet. Options:

- **Clear** — classic and traditional. Lets viewers see the driver's face. Best for vintage, period-correct, and minimalist designs.
- **Light smoke** — a 20–30% tint. Most professional drivers run this in real life. Looks neutral and modern.
- **Dark smoke** — a 70–80% tint. Hides the driver's face. Looks aggressive.
- **Mirror chrome** — full reflective. Looks premium, especially on dark or carbon helmets. In SPB, set the visor zone to `metallic: 255, roughness: 0, clearcoat: 16`.
- **Iridescent** — color-shifting (oil-slick / opal effect). Use sparingly; it draws the eye and competes with shell graphics.
- **Tinted color** — a non-neutral tint (gold, blue, red). Reads loud; pair with a restrained shell.

iRacing renders the visor with full PBR, so the spec map values you set will visibly change how the visor catches sunlight on the front straight.

## 5. Chrome and Mirror Visor Effects

Chrome visors require both a near-black diffuse color and a spec map set to maximum metallic with minimum roughness. SPB's `chrome_mirror` finish in the helmet style picker handles this automatically: it stamps the visor zone with `R=255 / G=0 / B=16` (max metallic, mirror smooth, clearcoat at peak gloss — remember that the B channel is *inverted*, so 16 is the brightest clearcoat, not 255).

If you want a tinted chrome (gold, blue, smoke chrome), tint the diffuse base color and leave the spec map at chrome values. The metallic reflection will pick up the diffuse tint without losing its mirror behavior.

## 6. Driver Identity (Helmet Personalization)

Helmets are how drivers brand themselves across teams and seasons. The strongest helmet designs:

- Use one bold color choice that reads instantly at speed.
- Carry a single graphic motif (a stripe, a bird, a sun-and-moon, a lightning bolt) consistently across years.
- Reserve the back panel for the driver's name and country.
- Resist the urge to chase trends. A consistent helmet builds recognition.

SPB's `name_strip` zone (on the SPB-native template) is designed for this: drop the driver's name once and it stays cleanly placed across all your shell variations.

## 7. Sponsor Placement on Helmet

Helmets are tertiary sponsor real estate (the suit and the car carry the primary money). Best practice:

- **Side panels** — small chip logos, no more than two per side.
- **Brow** — single small mark above the visor, often the team or driver's personal brand.
- **Chinbar** — usually no logo (it disappears in cockpit cam).
- **Back** — driver name takes precedence over any sponsor.

Do not stack more than 4–5 logos on a helmet total. The eye has nowhere to land and the design loses focus.

## 8. Helmet-Paint Matching the Car

There are three coordination strategies:

1. **Tonal match** — helmet uses the car's primary and secondary colors but in a different ratio (e.g. car is mostly red with white accent, helmet is mostly white with red accent).
2. **Inverted palette** — helmet swaps the car's primary and secondary so the two read as a pair without being identical.
3. **Personal accent override** — helmet keeps a driver-specific signature color regardless of car. This is what most veteran drivers do — their helmet is their helmet, and the car-team livery wraps around it.

Avoid "perfect match" — putting the car's exact graphics on the helmet at smaller scale looks like a costume rather than a kit.

## 9. iRacing Helmet Rendering Specifics

iRacing applies its own tone mapping and exposure to helmets in-sim, which means your in-booth preview won't match the in-sim render exactly. Practical adjustments:

- **Saturated colors** look about 10–15% less saturated in-sim. If you want a vivid red, push it slightly past where it looks right in the booth.
- **Deep blacks** crush a bit. If you want detail in dark zones, raise the black level a few points.
- **Spec/clearcoat** has a stronger effect in iRacing's lighting than in the booth's preview because iRacing renders environment reflections from the actual track skybox.

SPB's "iRacing Lighting" preview toggle approximates the in-sim look using a representative skybox, but the in-sim render is always the source of truth. Test critical designs in a test session before publishing.

## 10. Custom Helmet Styles

The SPB helmet style picker offers the presets in `helmets/styles.json` as starting points. To author a custom style:

1. Pick a template from `helmets/catalog.json`.
2. Choose three colors (primary / secondary / tertiary).
3. Decide your top-zone graphic (stripe, gradient, flag, color block).
4. Choose a visor style.
5. Save the result as a new style preset (the style editor handles writing to `helmets/styles.json` with a unique `id`).

Saved styles can be applied to any compatible template, which means a style you authored on the default template will work on the HD template without rework.

## 11. Saving and Sharing Helmet Designs

Helmets in SPB are saved as a paired diffuse + spec TGA following the template's `filename_convention`. The default iRacing helmet expects:

- `helmet_<iracing_id>.tga` — the diffuse texture
- `helmet_spec_<iracing_id>.tga` — the spec map

Both files go in the user's iRacing custom paint root under the `helmets` folder. The Live Link feature (see `SPB_LIVE_LINK_GUIDE.md`) handles this drop automatically. To share a design with another driver, package both TGA files together — sharing only the diffuse loses every chrome, satin, and matte choice you made.
