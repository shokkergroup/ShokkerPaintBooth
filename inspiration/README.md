# Shokker Paint Booth — Inspiration Library

Welcome to the inspiration library. This folder holds starting-point references for livery design — a curated collection of design archetypes and iconic liveries, plus a structured JSON catalog you can query programmatically or browse manually.

## What's Here

| File | Description |
|------|-------------|
| `design_patterns.json` | 25+ design-pattern archetypes with energy, era, recipe hints, and fit notes. Each entry is JSON-structured so tooling can filter by energy or era. |
| `iconic_liveries.md` | 15+ legendary livery archetypes described generically — color schemes, design elements, era and venue, plus SPB recipes. Trademark-free. |
| `README.md` | This document. |

## How to Use the Inspiration Library

1. **Browse the iconic liveries.** Start in `iconic_liveries.md` and scan for an archetype that matches the energy of the car you want to paint.
2. **Read the SPB recipe.** Every archetype comes with a recipe using SPB's zones, patterns, bases, and finishes.
3. **Pick a design pattern.** Once you have a flavor locked in, open `design_patterns.json` and pick one or two patterns that reinforce the archetype — flame, chevron, tricolor, bullseye, whatever fits.
4. **Remix.** None of these are sacred. Start from an archetype, then twist it. Swap colors. Mix two archetypes. Break the rules.

## Query Examples (for tooling authors)

The JSON file is structured so tools can filter easily:

```python
import json

patterns = json.load(open("inspiration/design_patterns.json"))["patterns"]

# All aggressive modern designs
aggressive_modern = [p for p in patterns if p["energy"] == "aggressive" and p["era"] == "modern"]

# All designs that fit GT3
gt3_designs = [p for p in patterns if "GT3" in p["best_for"]]

# Print quick-reference recipe hints for all designs
for p in patterns:
    print(f"{p['name']}: {p['recipe_hint']}")
```

## Energy Field Values

Design patterns are tagged with one of these energy values:

- **aggressive** — Bold, forward, attacking (flame, diagonal slash, tribal).
- **bold** — Strong and direct but not hostile (split halves, front/rear split).
- **dynamic** — Implies motion (diagonal slash, chevron, zigzag).
- **smooth** — Flowing, fluid (wave, gradient fade).
- **technical** — Precision-minded (chevron, carbon weave).
- **classic** — Heritage and time-tested (checker, two-tone, number-centric).
- **refined** — Understated, mature (minimalist, pinstripe, monochrome).
- **retro** — Deliberately evokes older eras (retro chrome, tribal, hot rod flames).
- **electric** — High-voltage, neon, energetic (zigzag, neon tuner).
- **explosive** — Bursts from a center (radial burst, starburst).
- **utilitarian** — Function-first, military or tactical (stencil, digital camo).
- **nostalgic** — Emotionally invokes the past (retro chrome, heritage greens).
- **playful** — Fun, unserious, mascot-friendly (bullseye, cartoon flair).
- **futuristic** — Forward-looking, digital (holographic, pixel glitch, digital camo).
- **professional** — Paid-sponsorship clean (sponsor-focused, league layouts).

## Era Field Values

- **timeless** — Works in any era.
- **classic** — 1950s–1970s heritage feel.
- **retro** — 1970s–1990s specific throwback.
- **modern** — 2000s–present current racing and custom culture.

## Submitting New Inspiration

If you design a livery you think deserves archetype status, share it:

1. Draft a description of the design (color scheme, design elements, era, venue).
2. Write an SPB recipe (base, zones, patterns, finish).
3. Open a discussion in the SPB community discord under `#inspiration-submissions`.
4. The collective reviews and curates additions.

Submissions should reference generic design archetypes only — no trademark content, no specific team or driver references.

## Using This Library in Your Workflow

**When you open a blank canvas:** Browse `iconic_liveries.md` and pick an archetype that matches the car's vibe.

**When you're stuck mid-design:** Open `design_patterns.json` and find a pattern that fills the gap — needs a front accent? Try chevron wing tip or nose cone contrast. Needs visual motion? Try diagonal slash or wave.

**When you're designing for a league:** Check the league's `league_template_config.json` first for required zones and approved finishes, then filter the inspiration library by the energy that matches the league's brand.

**When you're competing:** Pick an archetype your competitors aren't using. Originality reads.

## Design Pattern Categories Quick Reference

The 25+ patterns cluster loosely into these categories. Pick from the category that matches your visual direction:

- **Line and stripe work** — top-to-bottom stripe, pinstripe, American muscle stripes, pinstripe accent.
- **Geometric blocks** — front/rear split, belt-line two-tone, split halves, nose cone contrast.
- **Angular dynamics** — diagonal slash, chevron wing, zigzag bolt, tribal graphic.
- **Curves and flows** — wave, gradient fade, radial burst.
- **Repeating patterns** — checker edge, pixel glitch, digital camo.
- **Focal accents** — number-centric, bullseye, holographic panel.
- **Surface character** — carbon weave, retro chrome, weathered, military stencil, blanket monochrome.

Browse by category to find the visual tool that solves the problem in front of you.

---

This library is a living reference. It grows with the community. Paint bold, remix often, share what you love.
