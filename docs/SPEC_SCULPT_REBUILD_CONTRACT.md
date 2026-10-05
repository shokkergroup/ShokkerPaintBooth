# SPEC SCULPT Rebuild Contract

Status: owner-corrected next-beta contract, updated 2026-07-19

## The corrected decision

The first child-simple `Sculpt My Paint` cut was rejected by the owner. It hid too
much creative choice and its seed-only `TRY ANOTHER` action frequently produced an
indistinguishable result. That interaction must not return.

The product remains **SPEC SCULPT**. It should feel familiar to existing users and
retain the full range of available looks, while removing the setup systems and
technical tuning that made the old laboratory difficult to understand.

The primary journey is now:

1. Load a finished 2048 x 2048 iRacing paint.
2. Pick a named whole-paint look from the complete visual library.
3. Optionally add a paint color, click that color on the artwork, and give it a
   different named look.
4. Optionally make the active material finer with one linked base/spec scale.
5. Preview the material plan and put it in iRacing.

"Stripped back" describes the workflow, not the catalog.

## What customers can choose

The guided library is assembled live from the authoritative engine endpoints:

- three signature modes: Smart Materials, FRACTURE and Candy Depth;
- every `/api/spec-sculpt/presets` entry;
- every base and special returned by `/api/spec-sculpt/catalog-index`.

As of the correction this is 2,632 named choices: 178 Spec Looks and 2,454 Paint
Booth looks. Counts are rendered from live data rather than hard-coded.

The library provides:

- thumbnails or swatches on every ordinary look;
- search across name, ID, category, description and tags;
- `ALL`, `SPEC LOOKS` and `PAINT BOOTH` filters with counts;
- an unmistakable selected-look receipt;
- paged display (`SHOW MORE`) so thousands of choices do not freeze the screen;
- `SURPRISE ME`, which must select a different named look and build it immediately.

There is no seed-only `TRY ANOTHER` button. Variety comes from choosing another
real look, not from pretending a reroll changed something.

## Color-by-color editing and linked scale

The whole-paint look is always the foundation. `ADD COLOR` turns the original
paint preview into a sampler; one click adds a visible RGB chip and makes it the
active editing target. The next library choice affects only that matched paint
color. A user can switch between `WHOLE PAINT` and up to six color chips, change
one look at a time, adjust color reach (`TIGHT`, `NORMAL`, `WIDE`), or remove a
chip. Unmatched pixels keep the whole-paint look and later color chips win only
where soft masks overlap.

Each active preset/catalog material has one `BASE SCALE` control from 0.25x to
1.00x. Lower values tile the source detail more finely; `SPEC SCALE` is visibly
reported as matched and cannot diverge in Easy Mode. Signature procedural modes
show `SCALE: AUTOMATIC` instead of exposing a misleading control. Scale belongs
to the active target, so separate colors can retain separate material sizes.

This does not recolor the livery. A sampled color identifies an area of paint;
the user is assigning that area's physical finish.

## What is removed from the primary screen

The guided workflow does not expose channel numbers, M/R/CC, masks, seeds, blend
strategies, stack weights, channel trims, iron clamps, raw job output, or competing
Scratch/Catalog/Fusion creation models. Those capabilities remain in the engine
and in the preserved laboratory.

The user is never forced to choose an iRacing customer ID or car before previewing
a look. Deployment questions appear only after a successful visual preview.

## Progressive disclosure

There are three useful levels in the app:

1. **SPEC SCULPT** — the focused full-library workflow described here.
2. **Whole Car / By Color** — the existing guided Paint Booth workflows.
3. **Original Spec Sculpt** — the preserved full laboratory at
   `spec-sculpt.html`, including SHOKK THE WORLD, Auto-Sculpt, stacks, masks,
   channel tuning and its other deep controls. It has a clearly labeled action
   on the Easy fork and at the top of the guided rail; it is no longer buried
   below thousands of look cards.

The legacy code, routes and page are not deleted. It remains available for further
product work without forcing its control density onto every beta user.

There is only one customer-facing Easy Spec Sculpt implementation. The former
CSS-only `Easy Mode` toggle on `spec-sculpt.html` is preserved in source for
compatibility but is no longer an entry point; its button opens the canonical
guided main-app flow. The original page itself always remains the full/intermediate
laboratory.

## File and artwork handling

- PSD, TGA, PNG, JPG and JPEG are accepted.
- The source must be exactly 2048 x 2048.
- Layered PSDs still protect number, sponsor, logo, text and guide/template layers.
- Flat artwork continues through the existing automatic protection path.
- Preview remains independent from iRacing deployment.
- Final output still runs through the existing legality and deployment engine.

## Next-beta scope cut

Customer-facing now:

- SPEC SCULPT with the complete look library;
- Whole Car and By Color;
- real PSD layer editing;
- finish selection and iRacing save.

Preserved in source but not advertised for this beta:

- Smart Separate / Smart TGA automatic layer construction;
- Shokker Forge;
- the standalone original Spec Sculpt laboratory as a main-header entry point
  (it remains explicitly reachable through `OPEN ORIGINAL SPEC SCULPT` inside
  Easy Mode and the Electron View menu).

Do not delete their implementation, routes, tests, models or research artifacts.

## Release acceptance gates

- The product is called `SPEC SCULPT` everywhere customers enter it.
- A valid paint reaches the library before any look is generated.
- All live preset, base and special catalog entries are present and searchable.
- Clicking a look sends its real preset or catalog ID to the generation endpoint.
- A sampled color becomes a sticky target chip; library selection changes only
  that target and server-reported coverage is returned to the UI.
- `BASE SCALE` automatically drives the same target's Spec Sculpt pattern scale;
  Easy Mode offers no independent spec-scale control.
- The result plainly says the named look was applied, visibly uses its local
  M/R/CC structure, and shows the actual generated map as proof.
- Main-app quest/training overlays never cover or intercept Spec Sculpt cards.
- `SURPRISE ME` excludes the current named look.
- Selected look name remains visible beside the preview and deployment action.
- There is no `TRY ANOTHER` or `KEEP THIS LOOK` yes/no gate.
- Exact 2048 PNG, TGA, JPG and layered PSD sources reach a result.
- The original `spec-sculpt.html`, SHOKK THE WORLD, Auto-Sculpt and
  `openSpecSculptWindow()` implementation remain directly reachable.
- Smart Separate and Shokker Forge stay absent from the next-beta customer shell.
- Full 2048 render remains within the owner's 2–3 second standard budget.

## Definition of done

A new user can load a paint, recognize that the cards are looks, search or browse
all of them, click one, see that exact named result, and put it in iRacing without
learning how a spec map is built.
