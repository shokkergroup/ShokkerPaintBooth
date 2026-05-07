# Shokker Paint Booth — Complete Feature Catalog

**Version:** v6.2.0 "Boil the Ocean"
**Last Updated:** 2026-04-17

This document is the full inventory of features shipped in Shokker Paint Booth. Organized by system. Each feature includes a description, how to use it, and why it matters.

If you're looking for release notes, see `SPB_RELEASE_NOTES.md`. If you're looking for workflows, see `SPB_WORKFLOW_EXAMPLES.md`. If you're looking for a specific keyboard shortcut, see `SPB_KEYBOARD_SHORTCUTS.md`.

---

## Table of Contents

1. [File Management](#file-management)
2. [Canvas & Drawing Tools](#canvas--drawing-tools)
3. [Zone System](#zone-system)
4. [Layer System](#layer-system)
5. [Layer Effects](#layer-effects)
6. [Finishes & Bases](#finishes--bases)
7. [Patterns](#patterns)
8. [Spec Map System](#spec-map-system)
9. [Render Pipeline](#render-pipeline)
10. [Preview System](#preview-system)
11. [Server & API](#server--api)
12. [Keyboard & UX](#keyboard--ux)
13. [License & Deployment](#license--deployment)
14. [Comparison Matrix](#comparison-matrix)

---

## File Management

### First-Run Default Paint

**Description:** On first launch, SPB loads the Chevy Silverado 2019 PSD as a starting canvas.
**How to use:** Launch SPB. That's it. The Silverado is there.
**Why it matters:** Empty-canvas anxiety is real. A new user who opens SPB to a blank white square is a user who closes SPB thirty seconds later. Starting with a real, paint-able car means the first thing you do is *make art*, not *hunt for a file*.

### Auto-Restore Last Paint File

**Description:** On subsequent launches, SPB restores the paint file you were editing last — including zones, layers, mask regions, and tool state.
**How to use:** Close the app. Reopen the app. Your work is back.
**Why it matters:** No more "where did I save that?" moments. The app treats your in-progress livery as first-class state.

### Save As / Open

**Description:** Standard save/open for SPB project files (`.spb` format — JSON-based, human-readable, diffable).
**How to use:** `Ctrl+S` to save, `Ctrl+O` to open, `Ctrl+Shift+S` to save as.
**Why it matters:** Human-readable saves mean version control actually works. Diff your changes. Merge paint files across team members.

### PSD Import

**Description:** Load Photoshop `.psd` files directly. Layers become SPB layers. Groups flatten intelligently.
**How to use:** Load Paint button on the welcome screen, or `Ctrl+O`.
**Why it matters:** Most existing livery templates are PSDs. No conversion step.

### TGA Export

**Description:** Export the final render as a 2048x2048 TGA — the exact format iRacing expects.
**How to use:** `File → Export → TGA`, or `Ctrl+E`.
**Why it matters:** One-click path from art to in-sim. No Photoshop intermediate. No color profile wrangling.

### Live Link Deploy

**Description:** Automatically copy exported TGA to your iRacing custom paints directory.
**How to use:** Enable Live Link in settings, paste your iRacing custom paints path, click deploy.
**Why it matters:** Iterate in-sim in seconds, not minutes.

---

## Canvas & Drawing Tools

### Brush Tool

**Description:** Pressure-sensitive pixel brush with hardness, spacing, and flow controls.
**How to use:** `B` to select. Adjust size with `[` and `]`.
**Why it matters:** Detail painting. Logo touch-ups. Hand-lettered numbers.

### Fill Bucket

**Description:** Flood-fill tool supporting flat color and gradient fill modes.
**How to use:** `G` to select. Click target area.
**Why it matters:** Fast block-color work. Gradient mode fills with a two-color gradient in one click.

### Selection Tools

**Description:** Rectangular, elliptical, lasso, and magic-wand selection, each with optional zone-clip mode.
**How to use:** `M` rectangle, `L` lasso, `W` magic wand.
**Why it matters:** Precise edit control. Zone-clip means your selection respects your zone boundaries automatically.

### Shape Tools

**Description:** Rectangle, ellipse, line, polygon, star shapes with fill + stroke control.
**How to use:** Select from the shape dropdown in the toolbar. `Shift` for aspect lock, `Alt` for center-anchored drag.
**Why it matters:** Geometric design without leaving SPB.

### Text Tool

**Description:** Bitmap text with font-family, size, stroke, and kerning controls.
**How to use:** `T` to select. Click canvas. Type.
**Why it matters:** Number panels. Sponsor text. Driver names.

### Transform Handles

**Description:** Rotate, scale, skew, and distort any selection or layer with visual handles.
**How to use:** Select layer → `Ctrl+T` to enter transform mode.
**Why it matters:** Standard Photoshop-equivalent transform. Larger hit boxes than v6.1 so you don't miss corners at 100%.

### Region Mask (RLE)

**Description:** Run-length-encoded region masks for memory-efficient selections even on massive canvases.
**How to use:** Any selection or mask operation uses this under the hood.
**Why it matters:** 2048x2048 selections don't eat RAM. You can have 20 complex zones active simultaneously without a memory crisis.

---

## Zone System

### Zone Concept

**Description:** Zones are named regions of your paint where you assign a finish (base + pattern + spec). Think "the hood is chrome, the roof is matte, the doors are metallic red."
**How to use:** `+ Add Zone` button in the zones panel. Paint or select a region. Name it.
**Why it matters:** Multi-material liveries. The fundamental unit of SPB's workflow.

### Zone Finish Assignment

**Description:** Each zone gets a base + pattern + spec combination from the finish picker.
**How to use:** Select a zone card → click finish picker → pick a base → pick a pattern → optionally override spec.
**Why it matters:** Build up a livery by assigning materials to regions rather than hand-painting every pixel.

### Zone Lock (`Ctrl+L`)

**Description:** Pin the selected zone to the currently selected layer, so stray clicks in the canvas can't change which layer sources the zone's mask.
**How to use:** Select zone → select layer → `Ctrl+L`.
**Why it matters:** Complex liveries have dozens of zones. One stray click rebinding a zone's source has cost us hours. Never again.

### Zone Clone

**Description:** Right-click a zone → duplicate. Preserves mask, finish, spec override, and layer binding.
**How to use:** Right-click zone card → Duplicate.
**Why it matters:** "Same treatment on the other door." One click.

### Zone Mute

**Description:** Dim a zone card, exclude from render, but keep available for toggle-on later.
**How to use:** Click the mute icon on the zone card.
**Why it matters:** A/B testing designs. Keep the option alive without deleting.

### Zone Reorder

**Description:** Drag handles on the zone list to reorder layering priority.
**How to use:** Hover zone card → grab drag handle → reorder.
**Why it matters:** Later zones draw over earlier ones. Reorder controls stacking.

### Per-Zone Spec Override

**Description:** Override the spec map for a single zone independently of the base finish's default spec.
**How to use:** Select zone → spec panel → override toggle → pick custom spec.
**Why it matters:** Use the visual of one finish but the material physics of another. "Chrome look with matte roughness" is a real design request.

### sourceLayer Persistence

**Description:** Each zone remembers which PSD layer sourced its mask, and round-trips through save/load.
**How to use:** Automatic. Set once per zone, sticks forever.
**Why it matters:** Open a six-month-old project and every zone still knows where it came from.

---

## Layer System

### Layer Panel

**Description:** Photoshop-style layer list with visibility, opacity, blend mode, and thumbnail.
**How to use:** Right-side layer panel. Click visibility eye to toggle. Drag to reorder.
**Why it matters:** Industry-standard workflow. No learning curve.

### Layer Thumbnails

**Description:** 64px high-DPI thumbnails per layer, cached by layer ID.
**How to use:** Automatic.
**Why it matters:** Recognize layers at a glance. No more hunting by name.

### Layer Drag-Reorder

**Description:** Drag layers up and down the list to change stacking order with live preview.
**How to use:** Click and drag a layer in the panel.
**Why it matters:** Instant visual feedback of reorder effect.

### Blend Modes

**Description:** 14 blend modes per layer (Normal, Multiply, Screen, Overlay, Soft Light, Hard Light, Darken, Lighten, Color Dodge, Color Burn, Difference, Exclusion, Hue, Saturation).
**How to use:** Blend-mode dropdown at top of layer panel.
**Why it matters:** Full compositing control. Match what Photoshop does, match what users expect.

### Layer Opacity

**Description:** Per-layer 0-100% opacity slider.
**How to use:** Slider at top of layer panel.
**Why it matters:** Fine-tune contribution without destructive edits.

### Clip-to-Layer-Below

**Description:** Mask a layer to the non-transparent region of the layer below it.
**How to use:** Right-click layer → Clip to Layer Below, or `Ctrl+Alt+G`.
**Why it matters:** Photoshop-standard clipping mask behavior. Essential for effects like "color-overlay this logo but only inside this shape."

### Layer Contribution Mask (Alpha-Based)

**Description:** A layer's contribution to the final render is masked by its own alpha channel. This was broken in v6.1 — layers leaked through zones. Fixed in v6.2.
**How to use:** Automatic.
**Why it matters:** The render matches the on-screen composite, pixel-for-pixel. No surprises after export.

---

## Layer Effects

Five layer effects, each per-layer, each live-previewed.

### Drop Shadow

**Description:** Offset shadow behind the layer with distance, angle, blur, spread, opacity, and color.
**How to use:** Layer → `fx` button → Drop Shadow.
**Why it matters:** Depth. Legibility on light backgrounds. The #1 most-requested effect.

### Outer Glow

**Description:** Soft glow around the layer with size, spread, opacity, and color.
**How to use:** Layer → `fx` button → Outer Glow.
**Why it matters:** Neon looks. Highlight accents. Emphasis on logos and numbers.

### Stroke

**Description:** Solid-color outline around the layer with size, position (inside / center / outside), and color.
**How to use:** Layer → `fx` button → Stroke.
**Why it matters:** Number-panel outlines. Logo borders. Contrast on low-contrast backgrounds.

### Color Overlay

**Description:** Flat-color fill on the layer using blend-mode compositing.
**How to use:** Layer → `fx` button → Color Overlay.
**Why it matters:** Recolor a layer non-destructively. Try alternate color schemes without editing the source art.

### Bevel

**Description:** Highlight + shadow on the edges of the layer to simulate a raised or carved surface.
**How to use:** Layer → `fx` button → Bevel.
**Why it matters:** 3D look on 2D art. Old-school but effective for emblems and badges.

---

## Finishes & Bases

### Base Paints

**Description:** Hundreds of base paint definitions across OEM automotive, racing, exotic, chrome, candy, pearl, matte, metallic, neon, and more.
**How to use:** Zone → finish picker → base tab.
**Why it matters:** Industry-realistic colors out of the box. OEM codes for real cars. No color-matching guesswork.

### Base Groups

**Description:** Bases organized into functional groups (OEM Automotive, Racing, Exotic Metals, Chrome Family, etc.).
**How to use:** Group dropdown in the finish picker.
**Why it matters:** Discoverability. You know you want "a chrome" — the Chrome Family group has them all.

### Custom Finishes

**Description:** Save a base + pattern + spec combination as a named custom finish for later reuse.
**How to use:** Finish editor → Save as Custom → name it.
**Why it matters:** Reuse your signature look across projects.

### Finish Mixer

**Description:** Blend two finishes with a weight slider to produce a third.
**How to use:** Finish picker → Mixer tab → pick two finishes → weight slider.
**Why it matters:** Fine-tune without writing custom code. "70% chrome, 30% matte" is a valid finish.

---

## Patterns

### Pattern Concept

**Description:** A pattern is a procedural texture that composites onto a base to produce the final paint look (metallic flake, brushed, candy, holographic, etc.).
**How to use:** Zone → finish picker → pattern tab.
**Why it matters:** Procedural means infinitely scalable. No texture maps to download, no resolution limits.

### Pattern Strength Zones

**Description:** Per-zone pattern intensity. The pattern can be full-strength in one region and 40% in another.
**How to use:** Zone → pattern strength slider.
**Why it matters:** Realistic paint variation. Real paint isn't uniform.

### Pattern Groups

**Description:** Patterns organized by category (metallic, flake, brushed, candy, iridescent, damage, etc.).
**How to use:** Group dropdown in the pattern picker.
**Why it matters:** Fast discovery.

### Pattern Overlays

**Description:** Stack multiple patterns on a single base.
**How to use:** Pattern panel → add overlay button.
**Why it matters:** Multi-layer finishes. "Metallic base + flake overlay + clearcoat swirl."

---

## Spec Map System

### Spec Map Concept

**Description:** A 4-channel RGBA texture that tells the iRacing renderer how each pixel reflects light. R=Metallic, G=Roughness, B=Clearcoat (inverted), A=Specular Mask.
**How to use:** Automatic — SPB generates the spec map from your finish choices. Override per-zone if needed.
**Why it matters:** Physically-based rendering. This is what makes chrome look like chrome and matte look like matte in-sim.

### 214 Spec Patterns

**Description:** 214 procedural spec patterns across 19+ categories: chrome family, metallic flake, brushed directional, iridescent, anime, military, neon, exotic metal, ceramic glass, candy, carbon composite, and more.
**How to use:** Spec pattern picker in the right panel.
**Why it matters:** Every material you'd want, pre-built, deterministic.

### Per-Channel Spec Control

**Description:** R, G, B, and A channels each get an independent pattern picker.
**How to use:** Spec panel → channel tabs (R/G/B/A) → pick pattern per channel.
**Why it matters:** **Nobody else offers this.** Not Photoshop. Not Paint Builder. Not GIMP. Per-channel pattern control is SPB's moat.

### Spec Picker Tabs

**Description:** Category tabs filter the spec pattern grid (All / Chrome / Metallic / Iridescent / etc.).
**How to use:** Tabs at top of spec picker.
**Why it matters:** 214 patterns is a lot. Tabs make it navigable.

### GGX Floor

**Description:** The GGX BRDF roughness floor — the minimum roughness value below which the renderer stops producing visible highlights.
**How to use:** Automatic. The engine enforces correct physics.
**Why it matters:** Mirror chrome looks like mirror chrome. Six bugs fixed in v6.2 (WARN-GGX-001 through 006).

### Iron Rules

**Description:** Hard-enforced rules on spec-channel values for physical plausibility (e.g., clearcoat B=16 means max gloss, not B=255).
**How to use:** Automatic.
**Why it matters:** You can't build a physically-impossible paint by accident. The engine catches you.

---

## Render Pipeline

### Composition Pipeline

**Description:** Clear stage order: pre-base → base → pattern → spec → overlay → post. Each stage independently testable.
**How to use:** Automatic, but diagnostic endpoints let you see each stage's output.
**Why it matters:** Debuggability. If chrome looks wrong, you can inspect which stage broke it.

### Deterministic Seeds

**Description:** Every pattern function takes a seed and produces bit-identical output run-to-run.
**How to use:** Automatic — seeds are part of the save file.
**Why it matters:** Regression testing. Collaboration. "It looked like this yesterday" now means something.

### GPU Acceleration

**Description:** CUDA-accelerated render path when NVIDIA GPU + CUDA toolkit are available.
**How to use:** Enable in settings → GPU Mode.
**Why it matters:** 5-10x faster renders on supported hardware.

### Progress Callback

**Description:** `full_render_pipeline()` emits per-zone progress updates through a callback, surfaced through `/api/render-status` to the UI progress bar.
**How to use:** Automatic. The progress bar in the render panel shows it.
**Why it matters:** No more "is it frozen or is it rendering?" anxiety.

### Color Shift / Chameleon

**Description:** Angle-dependent color shifts for chameleon, flip-flop, and iridescent finishes.
**How to use:** Select a chameleon base or iridescent pattern.
**Why it matters:** Real paint shifts with viewing angle. SPB's chameleon output is sim-quality.

---

## Preview System

### Real-Time Car-Shape Preview

**Description:** The preview pane shows your paint on the actual car shape, not a flat square.
**How to use:** Automatic — always on.
**Why it matters:** Nothing else in the livery space does this. You see exactly what iRacing will show.

### TGA Preview Cache

**Description:** LRU cache (8 entries) keyed by path + mtime. Switching between recently-loaded cars is instant.
**How to use:** Automatic.
**Why it matters:** Teams working on multiple cars don't wait for re-decode every switch.

### F5 Refresh Preview

**Description:** Flush the cache and re-render from pixels on disk.
**How to use:** `F5`.
**Why it matters:** When you edit the source PSD outside SPB, `F5` brings the changes in.

### Progress Bar

**Description:** Live render progress with phase indicator (pre-base / base / pattern / spec / overlay / post).
**How to use:** Visible at the bottom of the render panel.
**Why it matters:** Know where you are in a long render.

---

## Server & API

### 93 Endpoints

**Description:** Flask API server exposes 93 endpoints covering render, preview, zones, layers, spec, export, and diagnostics.
**How to use:** `http://127.0.0.1:5000/` with appropriate route.
**Why it matters:** Extensibility. Write your own integrations. Batch scripts. Team workflows.

### 77 Passing Tests

**Description:** Automated test suite covering engine, server, and registry.
**How to use:** Developers: `pytest` from project root.
**Why it matters:** No silent regressions. A feature that worked yesterday works tomorrow.

### `/health` Heartbeat

**Description:** Lightweight liveness endpoint with uptime tracking.
**How to use:** `GET /health`.
**Why it matters:** Production monitoring. Keep the server honest.

### `/api/render-status`

**Description:** Per-zone render progress.
**How to use:** `GET /api/render-status` (UI polls this every 500ms).
**Why it matters:** Live progress bar.

### `/api/render-progress`

**Description:** Detailed render progress with phase tracking.
**How to use:** `GET /api/render-progress`.
**Why it matters:** Diagnostic granularity.

### Categorized Error Messages

**Description:** Computation, file-not-found, and out-of-memory errors produce distinct user-facing text.
**How to use:** Automatic.
**Why it matters:** "Render failed" tells you nothing. "Out of memory — try lowering render resolution" tells you everything.

---

## Keyboard & UX

### `?` Keyboard Shortcut Overlay

**Description:** Press `?` anywhere to see a full cheat sheet.
**How to use:** `?`. `Esc` to dismiss.
**Why it matters:** Discoverability. Users learn shortcuts passively.

### 26 New Tooltips

**Description:** Every checkbox, slider, color picker, batch-mode button, license control, and spec-channel button has a hover tooltip.
**How to use:** Hover.
**Why it matters:** Self-documenting UI.

### Cyan Focus Glow

**Description:** All form inputs glow cyan when focused.
**How to use:** Automatic.
**Why it matters:** Keyboard-navigation clarity.

### Custom Scrollbars

**Description:** 4px thin cyan scrollbars across every panel.
**How to use:** Automatic.
**Why it matters:** Consistent visual language. Doesn't disrupt UI flow with default OS chrome.

### First-Run Welcome Toast

**Description:** On first launch, a toast appears: "Press ? for keyboard shortcuts."
**How to use:** Automatic on first run.
**Why it matters:** Guides new users toward the shortcut system.

---

## License & Deployment

### License Management

**Description:** In-app license activation tied to your Shokker account.
**How to use:** Settings → License → enter key.
**Why it matters:** Pro features unlock cleanly.

### Live Link

**Description:** Automated TGA export to your iRacing custom paints folder.
**How to use:** Settings → Live Link → paste iRacing path → toggle on.
**Why it matters:** Export → test in sim in under 5 seconds.

### Batch Mode

**Description:** Render multiple configurations of a paint in a single pass.
**How to use:** Batch panel → add configurations → Run Batch.
**Why it matters:** Team liveries. A/B variations. Time savings compound.

---

## Comparison Matrix

| Feature | SPB v6.2 | Photoshop | Trading Paints Paint Builder | GIMP | paint.net |
|---|---|---|---|---|---|
| Real-time car-shape preview | **Yes** | No | Yes (basic) | No | No |
| Per-channel spec pattern control | **Yes** | No | No | No | No |
| Zone-level spec override | **Yes** | No | No | No | No |
| 214 built-in spec patterns | **Yes** | No | ~20 | No | No |
| Layer effects (5 types) | **Yes** | Yes | No | Partial | Partial |
| PSD import | **Yes** | Native | No | Yes | Limited |
| TGA export | **Yes** | Via plugin | Yes | Yes | Via plugin |
| Automated iRacing deploy | **Yes (Live Link)** | No | Yes | No | No |
| Deterministic procedural patterns | **Yes** | No | No | No | No |
| GPU-accelerated render | **Yes (CUDA)** | Yes | No | Limited | No |
| 93 API endpoints | **Yes** | No (AppleScript only) | No | Script-Fu | No |
| Zone-based workflow | **Yes** | Manual | No | Manual | Manual |
| Finish Mixer | **Yes** | Manual | No | Manual | Manual |
| Chameleon / angle-dependent color | **Yes** | Manual | Limited | Manual | Manual |
| GGX physically-based shading preview | **Yes** | No | Partial | No | No |
| Auto-restore last session | **Yes** | Recent files only | No | Yes | Yes |
| Free tier | **Yes** | No | Yes | Yes | Yes |

---

## Closing Note

SPB is built for a specific person: the racing-sim livery artist who wants real materials, real workflow, and real output — without fighting their tool. Every feature in this document exists because a real user asked for it or an artist's real project needed it.

If you're a new user, start with `SPB_QUICKSTART.md` and `SPB_WORKFLOW_EXAMPLES.md`. If you're an existing user, skim this doc for features you didn't know existed.

Paint hard. Ship clean.
