# Shokker Paint Booth — Cheat Sheet

One-page quick reference. Print it, pin it, keep it next to your monitor.

---

## Keyboard Shortcuts (Condensed)

### Tools
- `B` — Brush
- `E` — Eraser
- `G` — Gradient fill
- `I` — Eyedropper
- `M` — Mask tool
- `Z` — Zoom
- `V` — Pan
- `Shift+R` — Rotate canvas view

### Zones & Layers
- `N` — New zone
- `D` — Duplicate selected zone
- `Del` — Delete selected
- `F` — Fit zone to selection
- `Ctrl+G` — Group zones
- `Ctrl+Shift+G` — Ungroup
- `[` / `]` — Decrease / increase brush size
- `{` / `}` — Decrease / increase zone priority

### Edit
- `Ctrl+Z` — Undo
- `Ctrl+Shift+Z` — Redo
- `Ctrl+C` — Copy selected
- `Ctrl+V` — Paste
- `Ctrl+X` — Cut
- `Ctrl+A` — Select all
- `Ctrl+D` — Deselect

### File
- `Ctrl+N` — New livery
- `Ctrl+O` — Open
- `Ctrl+S` — Save
- `Ctrl+Shift+S` — Save As
- `Ctrl+E` — Export final render
- `Ctrl+I` — Import league config

### Preview
- `Space` (hold) — Temporary pan
- `Ctrl+R` — Render preview
- `Ctrl+Shift+R` — Full-quality render
- `1`/`2`/`3`/`4` — Preview lighting presets
- `Tab` — Toggle UI panels

### Pro shortcuts
- `Ctrl+Shift+E` — Eyedropper at cursor (any mode)
- `Ctrl+L` — Toggle live-link to iRacing
- `Ctrl+Shift+L` — Refresh iRacing
- `Ctrl+M` — Mirror zones left/right
- `Shift+Click` — Add to selection
- `Alt+Click` — Subtract from selection

---

## Common Workflows (5 Steps Each)

### Workflow 1 — New livery from scratch
1. `Ctrl+N` → choose car model.
2. Pick body base from the Base panel → click "apply to all zones."
3. Add centerline stripe zone → fill with accent color.
4. Drop in race number on both doors.
5. `Ctrl+S` → name it following your league's convention.

### Workflow 2 — Recreate an iconic archetype
1. Open `inspiration/iconic_liveries.md` → pick an archetype.
2. Apply the recipe's suggested base.
3. Create zones as the recipe describes.
4. Apply the recommended patterns and finishes.
5. Render preview, iterate, save.

### Workflow 3 — Build a league-compliant livery
1. `Ctrl+I` → import league config.
2. Start from one of the supplied league template liveries.
3. Fill required zones (validator shows what's missing).
4. Add your personal accent within palette.
5. Export with league naming convention and submit.

### Workflow 4 — Match an existing paint
1. Open the reference image in the Reference panel.
2. Use `I` (eyedropper) on reference to grab colors into your palette.
3. Approximate shapes with zones.
4. Tune finish (gloss level, metallic amount) in spec panel.
5. Render side-by-side to compare.

### Workflow 5 — Color-shift showcase build
1. Pick a color-shift base (chameleon, astro cosmic, iridescent).
2. Apply to full body.
3. Add minimal contrast element (single stripe, single logo) in a neutral.
4. Render under all 4 lighting presets — color shift amplifies in each.
5. Export animated preview (showcases the shift).

---

## File Paths (Where Stuff Lives)

**Your liveries:** `Documents/ShokkerPaintBooth/liveries/`
**League configs you've imported:** `Documents/ShokkerPaintBooth/leagues/`
**Shared decals and sponsor packs:** `Documents/ShokkerPaintBooth/sponsors/`
**Custom palette files:** `Documents/ShokkerPaintBooth/palettes/`
**Render output cache:** `Documents/ShokkerPaintBooth/renders/`
**SPB install location:** (varies by OS) — see About screen for path.

---

## Common Fixes

| Problem | Fix |
|---------|-----|
| Number not readable on broadcast | Add solid-color roundel behind number; ensure high luminance contrast. |
| Livery looks flat in preview | Check clearcoat — might be matte when you want gloss. Spec B=16 = max gloss. |
| Pattern not showing | Check pattern is registered (PATTERN_REGISTRY) and zone is assigned. |
| Render is slow | Drop preview quality in preferences; use full-quality render only for final. |
| Colors look different on broadcast | Preview under all 4 lighting presets; render matches spec of broadcast lighting. |
| League validator keeps rejecting | Read the exact error — it tells you which required zone is missing. |
| Zones won't mirror | Ensure "mirror mode" is enabled in zone panel; only some zones are mirror-eligible. |
| Lost recent changes | Ctrl+Z multiple times; check auto-save folder. |
| Spec map looks wrong | Remember B channel is inverted — 16 = max gloss, 255 = dull. |
| Chrome finish too dim | Spec R should be 255, G should be 0, B should be 16. |
| Eyedropper grabs wrong color | You're picking from preview, not from reference — use Ctrl+Shift+E for reference. |
| Saved file won't open | Check SPB version — newer versions can open older files but not vice-versa. |

---

## "I Want To..." → Answer Table

| I want to... | Answer |
|--------------|--------|
| Paint a chrome look | Use chrome base, spec R=255 G=0 B=16. |
| Paint a matte look | Use matte base, spec B>=240. |
| Match my team's color exactly | Use Color → Custom, input exact hex. Save to team palette. |
| Add a racing number | Use Number tool in toolbar; pick font and size from number panel. |
| Share a livery with my league | File → Export as `.shokker`, post to league Discord. |
| Import someone else's palette | Drop the `.palette.json` file into your palettes folder; restart SPB. |
| Try a color-shift finish | Browse the Chameleon, Astro Cosmic, or Iridescent base groups. |
| See my livery on broadcast-quality render | Ctrl+Shift+R for full-quality render. |
| Check my livery for league compliance | Window → League Validator panel; needs imported config. |
| Revert to an earlier version | File → Version History (keeps last 20 auto-saves). |
| Share a sponsor decal with others | File → Export as `.shokker` snippet; upload to community #sponsor-packs. |
| Weathering / rust look | Apply damage_wear_* base variants. |
| Remove all patterns from a zone | Select zone → Pattern panel → "None." |
| Copy settings from one zone to another | Select source → Ctrl+C. Select target → Paste Zone Properties from Edit menu. |
| Add a pearlescent sheen | Use any pearl finish from pearl base group, or add pearl clearcoat via finish panel. |
| Create a custom gradient | Zone → Fill → Custom Gradient; add 2-4 color stops. |
| Save a specific palette | Color panel → Save Palette → name it. |
| Fix a weird reflection | Check spec map — R (metallic) and B (clearcoat) interact. Lower metallic if too mirror-like. |
| Match iRacing dynamic lighting | Enable live-link with Ctrl+L when iRacing is running. |
| Get feedback before finalizing | Post 80%-done screenshot to SPB Discord #work-in-progress. |
| Approve liveries as a league admin | Window → League Review panel; opens all submitted files for batch review. |
| Set up a league for my community | See `SPB_LEAGUE_GUIDE.md`; start with `leagues/league_template_config.json`. |
| Find color inspiration | See `SPB_COLOR_COMBINATIONS.md`. |
| Find pattern inspiration | See `inspiration/design_patterns.json`. |
| Find livery archetypes | See `inspiration/iconic_liveries.md`. |
| Understand jargon | See `SPB_GLOSSARY.md`. |
| Get design principles | See `SPB_DESIGN_PRINCIPLES.md`. |
| Join the community | See `SPB_COMMUNITY_GUIDE.md`. |

---

## Spec Map Quick Reference

R — metallic (0 = dielectric/plastic, 255 = full metallic)
G — roughness (0 = mirror, 255 = matte)
B — clearcoat (0–15 = none, 16 = max gloss, 255 = dull)
A — specular mask (rarely used; advanced)

**Common presets:**
- Chrome: R=255 G=0 B=16
- Metallic paint: R=255 G=85 B=0
- Gloss body paint: R=0 G=85 B=16
- Matte: R=0 G=220 B=15
- Flat military: R=0 G=230 B=20
- Pearl: R=150 G=60 B=18

---

Keep this sheet open while you paint. The more you use it, the less you need it.
