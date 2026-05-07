# Shokker Paint Booth — User Glossary

Plain-English definitions of terms you'll encounter in SPB. Organized A-to-Z. Written for users, not developers — for the developer-focused glossary see `docs/GLOSSARY.md`.

---

## A

**Alpha channel** — The transparency channel of an image. An alpha of 255 is fully opaque; alpha of 0 is fully transparent. SPB uses alpha when layering zones on top of each other.

**Approved bases / patterns** — In a league config, the whitelist of bases and patterns drivers are allowed to use. Controlled by the league admin.

**Asset pack** — A zipped bundle containing a league's required logos, contingency decals, and starter templates. Distributed to drivers so they can paint league-compliant liveries.

## B

**Banned bases / patterns** — In a league config, the blacklist of bases and patterns drivers are not allowed to use. Any wildcard matching applies (`mortal_shokk_*` bans every Mortal Shokk variant).

**Base** — The foundational paint layer of a zone. Examples: gloss red, matte black, carbon fiber, chrome gold. Every zone has exactly one base. Bases define the core look before any patterns or finishes are applied.

**Belt line** — The horizontal line where the car's body meets the glass (top of door glass). Often used as a split point for two-tone paint jobs.

**Broadcast view** — A preview mode in SPB that simulates how the car looks on a broadcast TV feed — lower resolution, specific lighting, motion blur. Use to verify your design reads well during a race.

## C

**Candy** — A type of clearcoat finish where colored translucent layers create a "wet," deep look. Candy red over a metallic silver base gives a vivid, glowing red that shifts subtly with light.

**Canvas** — The SPB editing surface where you paint. Zoom with scroll wheel; pan with middle mouse or hold space.

**Carbon base** — A base that simulates woven carbon fiber. Often used on hoods, roofs, and wings for a performance look.

**Chameleon** — A color-shift finish where the apparent color changes depending on the viewing angle. Shifts from one hue to another across the car's surface.

**Cheat sheet** — The `SPB_CHEAT_SHEET.md` file — one-page reference for shortcuts, workflows, and common fixes.

**Chrome base** — A highly reflective base that simulates polished metal. Spec values: R=255, G=0, B=16.

**Clearcoat** — The top protective/shiny layer over the paint. Controls gloss level. In SPB, the B channel of the spec map controls clearcoat: 16 = maximum gloss, 255 = fully dull.

**Color palette** — The set of colors your livery uses. Can be locked by a league config or defined per-painter.

**Color-shift** — Any finish that changes apparent color based on viewing angle or lighting. Includes chameleon, astro cosmic, iridescent, and some pearl finishes.

**COLORSHOXX** — A color shift modulation feature in SPB that dynamically tunes how finishes react across the car's surface. Advanced users dial this to fine-tune field-sharpened color shifts.

**Compliance** — How well a livery matches its league's configuration. Shown in the League Validator panel as a green (compliant), yellow (warning), or red (non-compliant) indicator.

**Contingency stack** — A vertically stacked set of small sponsor logos, typically placed on the B-pillar or rear quarter. Leagues often supply this stack pre-built and locked.

**Custom gradient** — A user-defined gradient with two or more color stops applied across a zone. New in v6.1.

## D

**Decal** — A pre-made graphic (logo, number, sponsor mark) that can be dropped into a zone. Often distributed as `.shokker` snippets.

**Dielectric** — A non-metallic surface. Paint, plastic, leather. Spec R=0 in SPB.

**Driver-choice** — In a league config, a field marked `driver_choice` means the driver can pick that value within the league's constraints.

## E

**Era field** — A design-pattern categorization: `timeless`, `classic`, `retro`, or `modern`. Helps you filter inspiration patterns to match the car or series you're painting for.

**Export** — Save the finished livery as a `.shokker` file. Use Ctrl+E or File → Export.

**Eyedropper** — Tool that picks up the color at the cursor and sets it as the current paint color. Keyboard shortcut `I`. Use `Ctrl+Shift+E` to sample from the reference panel.

## F

**Field-sharpened** — A SPB feature that enhances the clarity of color-shifted finishes by sharpening the edges where two hues meet. Reduces blurriness in candy and chameleon finishes.

**Finish** — The surface character applied over the base. Includes gloss, matte, pearl, candy, metallic, chrome, satin. A zone has a base and a finish; they combine to produce the final appearance.

**Flip-flop** — A color-shift finish that flips between two very different hues at specific angles. Dramatic and distinctive.

## G

**Gloss** — High-reflection finish. Spec B=16. Wet-looking.

**Gold-to-Platinum** — The codename of the current SPB development branch, aimed at bringing SPB from feature-complete ("gold") to best-in-class ("platinum").

**Gradient** — A smooth transition between two or more colors across a surface. Created via SPB's gradient tool or custom gradient feature.

**GT3 / GT4 / GTE** — Classes of sports car racing. Liveries for each class tend to follow different visual conventions; SPB lets you match these.

## H

**Helmet crossover** — Reusing colors from a livery on the driver's helmet. Some leagues allow, some require.

**Hierarchy** — The visual ranking of elements on a livery: primary (biggest), associate (mid), contingency (smallest). See `SPB_DESIGN_PRINCIPLES.md`.

**Holographic** — A color-shift finish that creates rainbow highlights across the surface. Related to chameleon but more iridescent.

## I

**Iconic livery** — A legendary racing livery from motorsport history. SPB's `inspiration/iconic_liveries.md` catalogs 15+ archetypes.

**Inspiration library** — The `inspiration/` folder with design patterns and iconic liveries for reference.

**Iron rules** — SPB design guidelines that apply regardless of style: readability, contrast, hierarchy. See `SPB_DESIGN_PRINCIPLES.md`.

**iRacing ID** — Your iRacing account identifier. SPB uses this to enable live-link and push finished liveries directly to iRacing.

**Iridescent** — A finish that shows multiple colors depending on angle, like soap bubbles or insect wings.

## L

**Layer** — A labeled region of the car's body (hood, door, roof, B-pillar, etc.). Each layer contains zero or more zones.

**League** — A sim-racing community that runs coordinated series using shared paint rules. See `SPB_LEAGUE_GUIDE.md`.

**League config** — A JSON file that defines a league's visual rules: required zones, approved bases, palette, number style, submission process. See `leagues/league_template_config.json`.

**Live link** — SPB's integration with iRacing. When enabled, changes to your livery push to iRacing in real-time. Ctrl+L to toggle.

## M

**Mask** — A grayscale image that defines where paint or a pattern appears. White = full paint; black = no paint; grays = partial. Used for complex shapes like flames or tribal graphics.

**Matte** — Low-reflection finish. Spec B=240+. Absorbs light, reads as stealthy or tactical.

**Metallic** — A finish where tiny metallic flakes give the paint a sparkle and depth. Spec R>0 controls metallic amount.

**Mirror mode** — A SPB feature that mirrors painting from one side to the other. Turn on for symmetric liveries; turn off for asymmetric.

**Monolithic** — A body-wide unified finish without zone breaks. A "color-monolithic" livery is painted as a single coherent color and material across the whole car, with no zones or stripes.

**Mortal Shokk** — An SPB base family with aggressive damage-and-wear aesthetics. Often banned in professional-feeling leagues.

## N

**Number-centric** — A livery design pattern where the race number dominates the door panel.

**Number style** — How numbers appear on the car. Defined by font, size, fill color, outline color, and placement. Controlled per-livery or locked by league config.

## O

**OEM** — Stock factory-style paint, as the car would come from the manufacturer. SPB has an OEM base group for this look.

## P

**Palette** — The set of colors available for use on a livery. Can be constrained by league config.

**Pattern** — A repeated graphic or texture applied to a zone. Examples: stripes, checker, flame, chevron, carbon weave.

**Pattern strength zones** — New in v6.1. Lets you vary a pattern's intensity across a zone — strong at one edge, subtle at another.

**Pearl** — A finish with mica-like flakes that shift subtly between two related colors. Less dramatic than chameleon; more sophisticated.

**Pinstripe** — A very thin decorative line, usually traced along body contours. Classic hot-rod and lowrider accent.

**Preview** — A rendered view of your livery. Two qualities: live preview (fast, lower quality) and full-quality render (slow, broadcast-level).

**Primary sponsor** — The largest, most prominent sponsor on the car. Typically on the hood and/or doors.

**Priority** — A zone property that determines which zone wins when two zones overlap. Higher priority paints on top.

## R

**Reference panel** — A side panel where you can drop a reference image for color-matching with the eyedropper.

**Remainder** — The area of the car not covered by any zone. Defaults to the body base color.

**Render** — The process of producing a final image from the canvas. Live preview = fast; full render = broadcast-quality.

**Roundel** — A circular background panel, often used behind a race number for contrast. Traditional motorsport convention.

## S

**Satin** — A finish between matte and gloss. Has some reflection but not mirror-like. Spec B around 30-60.

**Seed** — A random-number seed used by SPB patterns (grain, weathering, glitch). Change the seed to get a different randomization of the same pattern.

**Shokker Paint Booth (SPB)** — The application itself. Desktop tool for designing sim-racing liveries.

**Snippet** — A small reusable `.shokker` fragment — a sponsor decal, a number roundel, a contingency stack — that can be imported into other liveries.

**Spec map** — A four-channel image (R, G, B, A) that controls a zone's surface properties: metallic (R), roughness (G), clearcoat (B), specular mask (A).

**Specular mask** — The alpha channel of the spec map. Controls where specular highlights appear. Rarely used by consumer tools.

**Split color halves** — A design pattern where the car is divided into two colors along the centerline.

**Sponsor pack** — A bundled set of sponsor decals shared across a league or community. Distributed as `.shokker` snippets.

**Stock car** — A class of racing car with specific livery conventions — big numbers on doors, sponsor-heavy hood, contingency stack on B-pillar.

**Submission** — The process of sending your completed livery to a league admin for approval.

## T

**Template** — A pre-built starter livery supplied by a league to drivers. Drivers import and modify.

**Texture** — A pattern's visual character (carbon weave, brushed metal, wood grain).

**Touring car** — A class of racing derived from street sedans. Liveries often use full-body graphics and bold centerline stripes.

**Two-tone** — A livery design where the upper and lower halves of the car are different colors, split at the belt line.

## U

**Undo stack** — The history of your recent actions. Ctrl+Z walks backward through it. The stack is bounded — old actions eventually drop off.

## V

**Validator** — The League Validator panel. Checks your livery against the imported league config and flags non-compliant elements.

**Version** — SPB release identifier. Current: v6.2.0. Newer versions can open older files but not vice-versa.

## W

**Weathering** — Simulated wear — rust, dust, scratches, faded paint. Applied via the damage_wear base family or weathering patterns.

**Workflow** — A sequence of SPB steps to accomplish a common task. See `SPB_CHEAT_SHEET.md` for 5-step workflows.

## X

*(No terms currently starting with X)*

## Y

*(No terms currently starting with Y)*

## Z

**Zigzag** — A design pattern with sharp angular zigs and zags. Reads as electric or aggressive.

**Zone** — A named painted region on the car. Every zone has a base, optional pattern, optional finish, and a priority. Zones overlap, with higher-priority zones painting on top of lower.

**Zoom** — Scale the canvas view. Use scroll wheel or `Ctrl+=`/`Ctrl+-`. `Ctrl+0` resets to fit.

---

This glossary is maintained for end-users. For the developer-facing glossary with Python/JS code references, see `docs/GLOSSARY.md`. If a term you needed isn't here, request it via the SPB Discord under `#documentation`.
