# SPB Color Theory — A Painter's Field Guide

A practical color theory reference for everyone designing liveries in the Shokker Paint Booth. This guide is written for sim racers, livery shop operators, and amateur painters who want their work to look intentional, professional, and camera-ready. No art-school prerequisites required.

---

## Why Color Theory Matters for Liveries

A livery is not a painting. It is a wrapper for a fast-moving 3D object that will be seen at speed, on a small screen, in mixed lighting, often through a chase cam. The colors you pick have to survive motion blur, broadcast compression, JPEG artifacting on stream, and players' wildly different monitor calibrations. They also have to communicate something — your team identity, your sponsor's brand, the era you are referencing — in less than a second.

Good color choices solve all of those problems before they appear. Bad color choices are visible from the grid stand and look amateurish on replays. The difference is rarely talent. It is almost always information.

---

## The Color Wheel — The 90-Second Version

The color wheel arranges hues around a circle. The three positions you need to remember:

- **Primary colors** — Red, Yellow, Blue. These cannot be mixed from other colors.
- **Secondary colors** — Orange, Green, Violet. Each is a 50/50 mix of two primaries.
- **Tertiary colors** — Red-Orange, Yellow-Green, Blue-Violet, etc. Each sits between a primary and a secondary.

Position on the wheel determines relationship. Two colors directly across from each other are complementary. Three colors evenly spaced are triadic. Two colors next to each other are analogous. Every color scheme below is just a geometric rule applied to the wheel.

---

## The Five Core Color Schemes

### Complementary

Two colors directly opposite on the wheel — red and green, blue and orange, yellow and violet. Complementary pairs produce the highest possible contrast and look vibrant together. The Gulf livery (Gulf Blue + Gulf Orange) is the most famous complementary scheme in motorsport. This is why it works at any speed, in any light, on any car.

Use complementary when you want maximum punch. Use sparingly — putting two complements at full saturation in equal amounts can vibrate uncomfortably (called "simultaneous contrast"). The Gulf trick is a 70/30 split: lots of blue, a little orange, with white as a buffer.

### Analogous

Three colors next to each other on the wheel — for example, blue, blue-green, and green. Analogous palettes feel harmonious and calm because the colors share underlying pigment. They rarely clash. Use them when you want a sophisticated, designed-feeling livery rather than a screaming statement.

The downside: analogous palettes lack contrast. If you build a livery from three shades of blue, your numbers and sponsor logos will be hard to read. Add a neutral (white, black, silver) to fix this.

### Triadic

Three colors evenly spaced around the wheel — red, yellow, blue is the textbook example. Triadic palettes are bold, balanced, and high-energy. They are popular on stock cars and toy-aisle liveries because they read clearly to a casual viewer.

Like complementary, triadic schemes need a hierarchy. Pick one hue as the dominant body color (60 percent), one as the secondary (30 percent), and one as the accent (10 percent). The "60-30-10 rule" is the easiest cheat code in livery design.

### Split-Complementary

A color plus the two colors adjacent to its complement. For example: blue, plus yellow-orange and red-orange. This is more sophisticated than straight complementary because the contrast is high but the discomfort of full opposition is softened.

This is the secret behind a lot of late-90s F1 liveries. McLaren-era papaya with a chrome accent and a deep navy stripe is essentially a split-complement.

### Tetradic (Double-Complementary)

Two pairs of complementary colors — four total. Tetradic palettes are the richest and most flexible but also the hardest to control. If you use this scheme, make one of the four colors clearly dominant and treat the other three as supporting players. Otherwise the result looks like a clown car.

---

## Warm vs. Cool Tones

Every color leans warm (toward red-orange) or cool (toward blue-green). Mixing warm and cool tones intentionally creates depth. Putting warm-leaning highlights against a cool body color reads as 3D and metallic — your eye reads warm as "closer" and cool as "farther."

A rule of thumb: cool body color, warm accent gives a high-tech feel (think Mercedes Petronas teal with copper accents). Warm body color, cool accent gives a sporty, athletic feel (Ferrari red with metallic blue wheels). Two warm tones together feel cozy and old-school. Two cool tones together feel clinical and futuristic.

---

## Sponsor Color Matching — The Real Skill

If your livery is sponsored — even by a fake in-sim brand — matching the sponsor's brand color exactly is a sign of professional polish. Three rules:

### Rule 1: Find the Brand Hex Code

Most companies publish their brand guidelines online. Search "<brand name> brand guidelines pdf" and you will usually find the exact Pantone, RGB, and hex codes. If the company doesn't publish guidelines, sample the color directly from their official logo PNG using a color picker. Do not eyeball it from a screenshot of a TV ad — broadcast color is mangled by compression, white balance, and gamma.

### Rule 2: Adjust for Display, Not for Print

A sponsor's print color (specified in CMYK or Pantone) often looks duller than the same color on a screen. Liveries are seen on screens, so use the RGB or hex value, not the CMYK conversion. If only the Pantone is published, look it up in a Pantone-to-RGB converter and use the RGB value.

### Rule 3: Adjust for Surface and Finish

A "Coca-Cola Red" applied to a glossy candy paint is going to read as a slightly different color than the same hex applied to a matte vinyl wrap. SPB's finish system simulates this. If you want the sponsor color to read true on stream, apply it on a satin or semi-gloss finish — extreme matte and extreme gloss both shift the perceived hue.

---

## Color Psychology — What Your Choices Communicate

Color carries cultural meaning. Even unconsciously, viewers assign personality to your livery based on the dominant hue.

| Color | Reads As | Common Use |
|-------|----------|------------|
| Red | Aggressive, fast, passionate, dangerous | Ferrari, fire, stop |
| Blue | Professional, trustworthy, calm, technical | Williams, IBM, Ford |
| Yellow | Energetic, attention-grabbing, friendly | Renault, taxis, caution |
| Green | Natural, fresh, money, vintage racing | British heritage, environmental brands |
| Orange | Playful, warm, athletic, bold | McLaren, Gulf, Halloween |
| Purple | Luxury, mystery, creativity, royal | FedEx, Cadbury, premium beauty |
| Black | Premium, stealth, serious, intimidating | Lotus JPS, premium German marques |
| White | Clean, neutral, peaceful, fresh | Honda Type-R, Apple, surgical |
| Silver | Modern, technological, premium | Mercedes Silver Arrows, Apple |
| Pink | Bold, fun, fashionable, contrarian | Alpine, Stewart-Haas, Mary Kay |

Use these associations on purpose. A grim-dark stealth livery built in pastel pink works only if you mean it as a joke. An aggressive aero-package supercar in baby blue feels confused. Match your color to your livery's personality.

---

## iRacing and Sim Display Considerations

iRacing, ACC, AMS2, rFactor 2, and most sim platforms render liveries using sRGB color space at standard gamma 2.2. SPB previews are color-accurate to sRGB. Two real-world adjustments to make:

### Monitor Gamut

Many sim racers run wide-gamut monitors (DCI-P3 or Adobe RGB) without color management. On those displays, sRGB content appears oversaturated. A color you picked on a wide-gamut monitor without sRGB clamp will look 15 to 25 percent more saturated to other players running calibrated displays. Solution: pick colors on a calibrated sRGB display, or enable sRGB clamp in your monitor's OSD when designing.

### HDR vs. SDR

Most sim renderers are SDR. If you are picking colors on an HDR monitor, your highlights will look brighter than they actually render in-game. A "neon yellow" that pops on your HDR display may look like a regular yellow in someone else's SDR stream.

### Broadcast Compression

Twitch, YouTube, and replay encoders compress chroma aggressively. Reds and saturated yellows survive worst — they bleed and posterize. Blues and greens hold up well. If your livery is going to be on streams, lean toward blues, greens, and desaturated reds. Pure 255-0-0 red will crawl with compression artifacts.

---

## HSL vs. RGB vs. HEX — When to Use Which

These are three ways to describe the same color. SPB accepts all three.

- **HEX** — `#RRGGBB`. Six characters, two each for red, green, blue, encoded as hexadecimal. Compact, universal, copy-paste-friendly. Use for sharing palettes and for sponsor color matching.
- **RGB** — `rgb(255, 100, 50)`. Three numbers from 0 to 255 for red, green, blue. Same data as hex, just decimal. Useful when working with code or images.
- **HSL** — `hsl(15, 100%, 60%)`. Hue (0–360 degrees on the wheel), Saturation (0–100 percent), Lightness (0–100 percent). The format painters actually think in.

The killer feature of HSL: you can shift one parameter without breaking the others. Want a darker version of your body color? Drop the L by 20. Want a more muted version? Drop the S by 30. Want the complementary color? Add 180 to the H. Do all this in HSL, then convert to hex when you commit the palette.

SPB shows all three values in the color picker. Pick in HSL, share in hex.

---

## Color Accessibility — Sponsor Readability

If the viewer cannot read your sponsor logos at speed, the livery has failed its primary commercial job. Two metrics matter:

### Contrast Ratio

The luminance contrast between text/logo and background. The W3C accessibility standard demands 4.5:1 for normal text. Liveries should aim for 7:1 or higher, because the viewer is moving. Yellow text on white is unreadable. White text on light gray is unreadable. Black text on dark green is unreadable.

The fastest test: convert your livery preview to grayscale. If the sponsor logos disappear, your contrast is too low.

### Hue-Independent Visibility

About 8 percent of male viewers and 0.5 percent of female viewers have some form of color vision deficiency. The most common form makes red and green hard to distinguish. A red sponsor logo on a green body will be invisible to those viewers. Add a white or black outline, or shift the contrast to lightness rather than hue.

---

## Historical Color Schemes — Livery Traditions by Series

Liveries carry historical baggage. Knowing the tradition lets you reference it on purpose — or break it on purpose.

- **Formula 1 (pre-1968):** National racing colors. British Racing Green for the UK, Bleu de France for France, Rosso Corsa for Italy, Silber Pfeil silver for Germany, Bianco for Japan. This system collapsed when sponsorship became legal in 1968 (Lotus debuted the gold-and-red Gold Leaf livery).
- **Le Mans / WEC:** Manufacturer prototypes lean toward a single dominant team color; gentleman-team GT cars often run sponsor-driven schemes. The Gulf-Aston Martins are the canonical reference.
- **NASCAR:** Heavy primary colors driven by sponsor identity. Tradition: number font, contrasting roof color, big sponsor on the hood.
- **Touring Cars (BTCC, WTCR):** Bold tobacco-era inspired graphics, heavy stripes, manufacturer-tied accent colors.
- **Rally:** Earth tones for vintage Group B nostalgia (Audi quattro), bright corporate colors for modern WRC.
- **IndyCar:** Anything goes. Variety is the tradition.
- **GT3 / Endurance:** Multi-class visibility is the design constraint. Bold body color, large numbers, light-colored class identifier panels.
- **Historic / Vintage:** Period-appropriate palettes only. Putting a 2024 metallic color on a 1972 reproduction looks like a costume mistake.

---

## Don't-Do-This Gallery — Common Mistakes

### Mistake 1: All Saturation, All the Time

Every color cranked to 100 percent saturation. The livery looks like a gas station candy display. Mute most colors and let one or two pop. The ratio: roughly one fully-saturated accent for every five muted body colors.

### Mistake 2: Too Many Colors

Five primary colors plus three accents plus four sponsor logos in their own brand colors. The eye gives up. Stick to a three-color palette plus neutrals for the body, and let sponsor colors live inside their bounded logo decals.

### Mistake 3: Low-Contrast Numbers

Race numbers in the same lightness as the body color. From 200 feet they disappear. Numbers should be the highest-contrast element on the car. Black on white or white on black is always safe.

### Mistake 4: Ignoring 3D Form

The car has highlights and shadows. A bright color that looks great on a flat preview will pool on the roof and disappear in the wheel arches. Always preview on the rendered 3D body, not just the unwrapped UV.

### Mistake 5: Tribal Color Conflicts

Painting a Ferrari blue, a Williams red, or a Lotus orange. You can do it, but you are picking a fight with decades of fan expectation. Have a reason.

### Mistake 6: Wrong Era

Carbon-fiber-textured matte gloss on a 1960s GT40 reproduction. Modern PPF gradient fades on a vintage NASCAR. Match your finish era to your color era.

### Mistake 7: Sponsor Logo Color-Modification

Recoloring a real sponsor's logo to match your livery. This is a fast way to get a copyright complaint and also looks unprofessional. Adjust your livery to fit the sponsor color, never the other way around.

### Mistake 8: Identical Adjacent Colors

Two greens of nearly the same value next to each other. Looks like a printing error. Either commit to one green or push them several steps apart in lightness or saturation.

---

## Quick Tips for Picking a Livery Palette

If you have 60 seconds before a race and need a palette:

1. **Pick one anchor.** Start with the single most important color — your team color, your sponsor's primary, your favorite hue.
2. **Add a neutral.** White, black, silver, or cream. This will be your "rest" color.
3. **Pick a complement or split-complement** of your anchor for the accent. Use SPB's color wheel — it shows the geometry visually.
4. **Test in motion.** Spin the preview camera. If colors blend together when the car moves, push the contrast up.
5. **Look at it in grayscale.** If you can still distinguish all the elements, you have enough contrast. If not, add black-or-white outlines.
6. **Reference a real livery.** When in doubt, find a real-world livery you love and analyze its palette. The classics are classics for a reason.

---

## Final Thought

Color theory is not a set of rules to follow. It is a vocabulary that lets you describe what you are doing on purpose. Once you can name what is happening — "this is split-complementary," "this is a 60-30-10 ratio," "this fails contrast for the rear sponsor at 4K" — you can fix it, push it, or break it intentionally. That is the difference between a livery that looks designed and a livery that looks like it happened.

Welcome to the booth. Pick good colors.

---

*Maintained by Shokker Paint Booth — see `palettes/README.md` for the bundled palette library.*
