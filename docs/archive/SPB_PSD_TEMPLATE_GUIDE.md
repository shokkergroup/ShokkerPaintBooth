# SPB PSD Template Guide

A comprehensive guide to creating, structuring, and consuming PSD templates inside Shokker Paint Booth (SPB). This document is intended for livery designers, custom-template authors, and developers extending SPB's template system.

---

## 1. What PSD templates are and why they matter for SPB

A **PSD template** is a Photoshop document that represents a vehicle's livery layout. In iRacing and similar racing simulators, every car ships with a flattened TGA (Truevision Graphics Adapter) image as its surface texture. Designers don't paint the TGA directly — they work in a structured PSD that contains organized layers (base paint, sponsors, numbers, manufacturer logos, etc.) and export the final flattened TGA at the end.

SPB sits **on top of** the PSD workflow. Instead of forcing the designer to manually paint each layer in Photoshop, SPB:

- Generates the `Car_Paint` layer programmatically using the engine's 1000+ finishes (chrome, metallic flake, candy, carbon, anime cel-shading, etc.).
- Reads the existing layer structure to know where it can paint without clobbering sponsors or manufacturer logos.
- Renders a real-time preview on a 3D car shape so designers can iterate without hitting Photoshop's slow render cycle.
- Exports the result back into the PSD, replacing only the `Car_Paint` layer and leaving everything else (sponsors, numbers, masks) untouched.

For SPB to do this reliably, it needs to **understand** the PSD's structure. That's where the template metadata system in `psd_templates/` comes in: each template metadata JSON describes what layers SPB should expect, what they mean, and where the paintable areas live in UV space.

When SPB encounters a PSD that matches a known template, it can offer a richer experience:

- Pre-loaded zone defaults for that car shape.
- Sponsor placeholder slots with safe-area constraints.
- Mandatory-layer warnings (don't paint over Class Lights on LMP cars).
- One-click recipes ("Apply factory livery", "Apply chrome accent + carbon hood").

Without metadata, SPB still works — it falls back to layer auto-discovery — but the experience is more "raw editor" and less "smart livery designer".

## 2. Standard PSD layer conventions

Most racing-sim PSD templates (iRacing, ACC, rFactor 2) follow a roughly common pattern. SPB normalizes around the iRacing convention because that's the dominant ecosystem for our users. The following layers are considered "standard" — any compatible PSD should have most of them:

| Layer name | Type | Purpose | Required? |
|---|---|---|---|
| `Wire` | Raster | Wireframe overlay for placement reference | Yes (visible only in editor) |
| `Mask` | Mask | Defines paintable region | Yes |
| `Car_Paint` | Raster | Base paint — SPB writes here | Yes |
| `Numbers` | Smart object | Driver number panels | Yes |
| `Sponsors` | Group | Sponsor logo group | Yes |
| `Tape` | Raster | Decorative tape stripes | Optional |
| `Pitbox Colors` | Raster | Pit stall signage tint | iRacing-specific |
| `Color Change Logos` | Raster | Manufacturer logo recolor | Yes for branded series |
| `Windshield Banner` | Raster | Driver name strip | Yes |
| `Class Lights` | Raster | Mandatory class identifier (LMP/IMSA) | Required for prototypes |
| `TV Panel` | Raster | Above-door TV-camera panel | NASCAR Cup specific |
| `Turn Off Before Exporting TGA` | Group | Reference layers (hide before export) | Recommended |

You will see exact layer names in the per-template JSONs in `psd_templates/`.

## 3. Recommended layer names

SPB's auto-discovery looks for layers by **name** before falling back to position-based heuristics. Stick to these names exactly (case-sensitive):

- `Car_Paint` — singular, underscore. Not `CarPaint`, `car_paint`, or `Paint`.
- `Numbers` — plural, no prefix.
- `Sponsors` — plural, no prefix.
- `Color Change Logos` — three words, spaces, capitalized.
- `Windshield Banner` — two words, spaces, capitalized.
- `Wire` — single word.
- `Mask` — single word.
- `Class Lights` — for any prototype/multi-class car.

If you must use a non-standard name (e.g., a translated localization), you can map it via SPB's **Layer Alias** settings panel. The alias is stored per-PSD in the `.spb_meta` sidecar file and is read on every load.

## 4. How SPB discovers layers

When SPB opens a PSD, it does the following:

1. **Check for metadata match.** SPB hashes the PSD's top-level layer names and looks up the result in `catalog.json`. If a match is found, SPB loads the per-template JSON and uses it as ground truth.
2. **Fall back to auto-discovery.** If no metadata match, SPB scans top-level layer names and matches against a built-in alias dictionary (handles `CarPaint` -> `Car_Paint`, `numbers` -> `Numbers`, etc.).
3. **Surface gaps.** Any layer SPB expected (per metadata) but didn't find triggers a warning chip in the SPB header. The user can dismiss, remap, or open the Layer Alias panel.
4. **Cache the result.** SPB writes a `.spb_meta` sidecar next to the PSD with the resolved layer-id-to-purpose map, so subsequent loads skip the discovery step.

This three-tier approach (metadata > auto-discovery > sidecar cache) means the first load of an unknown PSD is the only "slow" step — every subsequent load is fast.

## 5. Layer groups (Paintable Area, Turn Off Before Exporting TGA)

iRacing's official templates use two top-level groups by convention:

### Paintable Area

A group containing every layer the designer is allowed to edit. SPB respects this boundary: it will never write outside this group. If you have a layer outside the group (e.g., a base wireframe) that you want SPB to consider paintable, move it inside, or alias it via the Layer Alias panel.

### Turn Off Before Exporting TGA

A group containing reference-only layers — typically `Wire`, `Guides`, sponsor placement notes, and color reference swatches. Photoshop designers manually toggle this group OFF before File > Export As > TGA. SPB's export pipeline does this automatically, so you don't have to remember.

If you create a custom PSD, organize accordingly: paintable on top, reference at bottom, and group everything that should not appear in the final TGA.

## 6. Canvas size conventions

The de-facto standard for racing-sim PSDs is **2048 x 2048** (square, power of two). This is what every official iRacing template ships with, and it's what SPB defaults to.

You can use other sizes — SPB supports anything from 512x512 up to 8192x8192 — but be aware:

- **Smaller** (512, 1024): faster preview but visible pixelation on large sponsor logos.
- **Larger** (4096, 8192): crisp detail but slow to upload, slow to preview, and may exceed iRacing's per-livery file size cap (~1.5 MB compressed TGA at 4096).
- **Non-square**: SPB tolerates non-square canvases but the preview's automatic UV unwrap assumes 1:1 aspect, so a 2048x1024 PSD will render with horizontally-stretched paint.

For new templates, **stick to 2048x2048** unless you have a specific reason. Document the choice in your template's `notes` field if you deviate.

## 7. Color space (sRGB recommended)

Use **sRGB** as the document color profile. Reasons:

- iRacing, ACC, rFactor 2, and most consumer monitors expect sRGB.
- SPB's preview engine does its lighting math in linear-sRGB and converts to sRGB for display. A non-sRGB source PSD will produce subtly off-color preview results.
- Hex colors in `recommended_zones` and SPB's color picker are treated as sRGB.

When creating a new PSD: File > New > Color Profile > sRGB IEC61966-2.1.

If you must work in Adobe RGB or ProPhoto for source artwork, convert to sRGB before saving as the SPB-bound PSD.

## 8. Alpha channel expectations

The `Car_Paint` layer should NOT have an alpha channel — SPB writes RGB only and relies on the `Mask` layer for paint constraints.

The `Sponsors` and `Numbers` groups SHOULD use per-layer alpha (transparent backgrounds on each logo), so they composite cleanly over the base paint.

When SPB exports the final TGA, the alpha channel is generated from the `Mask` layer by default. If your PSD uses a custom alpha source (rare), set the `alpha_required: true` flag in your metadata JSON and SPB will use the document's alpha channel verbatim.

## 9. How to prepare a custom PSD for SPB

Step-by-step for taking a brand-new PSD (or a community-shared template) and making it SPB-compatible:

1. **Open in Photoshop.** Verify color space is sRGB, canvas is 2048x2048 (or your intended size).
2. **Audit layer names.** Match the standard names above. Rename anything non-conforming.
3. **Group correctly.** Place all editable layers under a `Paintable Area` group; reference layers under `Turn Off Before Exporting TGA`.
4. **Add a Mask layer.** A grayscale mask (white = paintable, black = excluded). SPB uses this to constrain paint.
5. **Save as PSD** (not PSB, not TIFF). Maximize compatibility option ON.
6. **Generate metadata.** Copy the closest existing JSON in `psd_templates/`, rename, and fill in:
   - `id`, `name`, `category`
   - `canvas_size`
   - `layer_tree` matching your actual layers
   - `uv_safe_areas` for sponsor placement
   - `number_panels` for driver number positions
   - `recommended_zones` for first-run defaults
   - `warnings` and `tips`
7. **Add to catalog.** Append a summary entry to `catalog.json`.
8. **Reload SPB.** Either restart, or call the catalog-reload endpoint (`POST /api/catalog/reload`).
9. **Test.** Load the PSD in SPB, verify all expected layers are detected, run a paint cycle, export TGA, and verify in iRacing.

## 10. Debugging missing layers

When SPB can't find an expected layer, it surfaces a warning chip in the header. Click it to open the Layer Alias panel, which shows:

- Expected layers (from metadata)
- Found layers (from PSD)
- Unmapped layers (need a decision)
- Aliases you've already set (editable)

Common causes of missing layers:

- **Renamed layer.** Designer changed `Car_Paint` to `Base Paint`. Fix: rename back, or alias.
- **Moved layer.** Layer is outside the `Paintable Area` group. Fix: drag inside, or alias.
- **Locked layer.** Photoshop lock prevents SPB from writing. Fix: unlock the layer.
- **Smart object wrapper.** Designer converted a raster layer to a smart object. SPB can read smart objects but can't write back to them. Fix: rasterize.
- **Hidden layer.** SPB ignores hidden layers by default. Fix: toggle visible, or use the Layer Alias's "include hidden" toggle.

If a critical layer (like `Car_Paint` or `Mask`) is missing entirely, SPB will refuse to paint and prompt the user to either fix the PSD or pick a different template.

## 11. When to re-import vs live-update

SPB supports two modes for PSD changes:

- **Live update (default).** SPB watches the PSD file (or the in-memory representation) and reflows the preview when you tweak finishes, colors, or zones. The `Car_Paint` layer is regenerated in-place; no full reload needed.
- **Re-import.** When the underlying PSD's structure changes (layers added, removed, renamed, or moved), use File > Re-Import PSD. This re-runs metadata matching and rebuilds the layer alias map.

Rule of thumb: **paint edits = live update; structural edits = re-import.**

If you're iterating on a custom PSD and changing layer names mid-session, expect to re-import frequently. Once the PSD is stable, live updates are nearly instant (<200 ms for a 2048x2048 paint regeneration on a modern GPU).

---

## Appendix A: Glossary

- **PSD** — Photoshop Document. Layered raster format used by Adobe Photoshop and most industry tools.
- **TGA** — Truevision Graphics Adapter. The flattened image format consumed by iRacing.
- **UV space** — A 2D coordinate system (u, v in 0..1) used to wrap a 2D texture onto a 3D mesh. SPB uses `0..1` with origin top-left to match Photoshop.
- **Bbox** — Bounding box. Two corners (min, max) defining a rectangular area.
- **Smart object** — A Photoshop layer type that wraps another raster/vector source, allowing non-destructive scaling.
- **Mask layer** — A grayscale layer used to constrain visibility or paint application.
- **Zone** — SPB-specific concept: a named region of the body with its own finish + color + pattern settings.
- **Finish** — SPB-specific concept: a paint material (chrome, candy, metallic, matte, etc.) selected from `FINISH_REGISTRY`.

## Appendix B: File naming convention

For metadata JSONs in `psd_templates/`:

- Use `snake_case`: lowercase with underscores between words.
- Match the iRacing folder name where possible.
- Format: `<manufacturer>_<model>_<year>.json` for specific cars, or `generic_<class>.json` for class baselines.

Examples:
- `chevy_silverado_2019.json`
- `porsche_911_gt3r_2023.json`
- `generic_gt3.json`
- `generic_lmp.json`

## Appendix C: Future work

Planned enhancements to the template system:

- **Auto-generated thumbnails.** SPB will render a preview thumbnail per template and cache it in `psd_templates/thumbs/`.
- **Community catalog.** A community-contributed registry of templates downloadable from the SPB UI.
- **Per-team default recipes.** Save a `recommended_zones` set as a "team livery preset" that can be reapplied across templates.
- **Validation CLI.** A `spb-validate-template` command that checks JSON conformance and PSD structural compatibility before submission.

---

Maintained by the Shokker team. Questions: ricky@shokkergroup.com.
