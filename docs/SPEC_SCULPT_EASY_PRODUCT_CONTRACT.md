# Easy Spec Sculpt Product Contract

Status: active product guardrail for the 2026-07-20 Easy Spec Sculpt marathon.

## Promise

Drop a finished 2048 x 2048 iRacing paint, choose how it should feel under light,
and install a verified paint/spec pair without needing to understand M/R/Cc.

## The three-decision core

1. Choose the paint.
2. See Shokker's Smart Materials starting point, then choose another look if desired.
3. Put it in iRacing.

Everything else must either remove work from one of those decisions or remain
progressively disclosed. A capability does not earn Easy Mode screen space merely
because the engine can do it.

## Two-minute demo acceptance

1. Use the paint already open (or choose one file). Smart Materials begins without another decision.
2. Show `ORIGINAL -> SCULPTED PAINT -> SPEC OUTPUT` together; one Whole Car click visibly updates
   the material plan while the original remains available.
3. Ask `WHICH iRACING CAR?` in readable car names, retain the exact folder as proof, and keep
   Customer ID secondary.
4. End on one `PUT THIS MATERIAL PLAN IN iRACING` action with both exact output filenames visible.

No destination re-entry, channel jargon, fake lighting, or advanced-control detour belongs in this demo.

## Power without clutter

- Keep every look searchable; default to a short, paint-aware starting set. Search should
  understand novice intent words such as shiny, flat, sparkly, subtle, and wild; ignore
  conversational filler, translate phrases such as "not too shiny" into a useful satin
  intent, tolerate a simple typo, rank direct names first, and offer one
  obvious way to clear the search back to the smart shortlist. Escape and the visible clear
  action do the same thing. If a mixed request has no exact intersection, show honest,
  material-first closest matches (for example, carbon for `purple carbon`) instead of a dead
  end; the material/action word remains mandatory so unrelated gibberish does not flood the rail.
  Match intent tokens as words, not arbitrary substrings: `red` must not match `colored`, and
  `rough` must not treat a finish described as `low roughness` as the requested rough material.
- Opening a full-library tab must stay responsive. Page the card grid in useful browse-sized
  batches and let the browser skip offscreen card layout; "all looks" must never mean
  "render thousands of controls before the click responds."
- Catalog cards use real registry descriptions for search/tooltips and translate cryptic
  taxonomy into a short plain material-family label without adding another control. Strip
  ticket IDs, renderer function names, raw channel assignments, audit scores, and owner-review
  breadcrumbs before any description reaches Easy Mode. Expand internal family prefixes
  (for example `PF`, `FF`, and `ENH`) into customer-readable names while keeping the registry
  ID as the selection identity. A look with no authored description uses its readable name
  as the tooltip; never replace useful names with one generic "special finish" label.
- A brand-new paint should demonstrate the product before asking for expertise: automatically
  render Smart Materials as a reversible preview starting point, but never auto-install it.
  Keep the full 2,632-look library available on the same screen.
- The 12 smart picks are a demonstration set, not twelve near-duplicates: after the three
  signature anchors, prefer material-family breadth before filling remaining relevance slots.
  Registry twins may remain individually browseable, but must never occupy two smart-pick
  slots or make `Try next`, `Surprise me`, or the two-color auto-plan rebuild the same recipe.
- A transient local-server startup failure must not permanently cache the three signature
  fallbacks as the entire library. Retry the complete environment after the server recovers.
- The first catalog response must warm every lazy expansion pack before claiming the library
  is complete; the initial Easy screen and a post-render reload must expose the same looks.
  Listing and selection must use the same merged registry: every card returned by the catalog
  endpoint must survive `normalize_catalog_stack` and render, including runtime-only bases and
  specials. A fresh process must expose 695 bases + 1,759 specials before any prior render.
- Detect useful source colors; let one click turn a color into an editable material.
- A selected color owns one compact `PAINT COLOR` decision: `KEEP ORIGINAL` or
  `CHANGE COLOR`. Changing it updates the painted preview immediately and the full-size
  install must bake that replacement into the diffuse TGA using the same soft color mask
  as its material, while preserving local livery shading and every untouched color.
- On a fresh plan, offer one compact **AUTO-SCULPT 2 COLORS** action. It must prefer
  recognizable accent colors over template gutters, choose different paint-aware material
  families, and build the combined preview in one render. Manual color chips remain available.
- Use plain material language in the primary flow. Raw M/R/Cc stays supporting proof.
- The default result is one glanceable proof sequence: **ORIGINAL -> SCULPTED PAINT -> SPEC OUTPUT**.
  All three remain on screen after every Whole Car or color-look change; the raw map is a
  real panel, not a tiny overlay. Its copy says that the RGB image is material data, not paint
  color. `VIEW BIG` and full-map views are reversible disclosures, never the default. Never add
  fake spotlights.
- Give the real painted result one compact `VIEW BIG` disclosure. It may enlarge the
  existing material simulation and exact map proof, but must not add a sweep, beam,
  animated light, or other screen-space effect that is not part of the spec response.
- Expose one whole-plan `MATERIAL IMPACT` choice: Subtle, Balanced, or Bold, with Balanced
  as the obvious default. It changes the human-visible metal/gloss/coat response together
  after all material layers are composited; it must not resize or reseed authored fine
  features, and protected artwork is applied after it. The iRacing blue channel is inverted,
  so Subtle moves toward no clearcoat (`B=255`) while Bold moves toward more coat. Do not
  describe an inherently dramatic finish as "BOLD RESPONSE" after the user chose Subtle;
  the nearby summary is a neutral `MATERIAL READOUT`.
- Whole-paint Metal/Gloss/Coat meters describe the complete map. While a color is active,
  those same meters describe the actual material inside that color's mask; a small accent
  must not look weak merely because most of the car uses something else. Those per-mask
  response statistics must include the current whole-plan Material Impact transform.
- Preview recommended library looks on the user's livery when practical; upgrade those
  thumbnails in place so background work can never steal a click.
- Every named preset must ship with truthful card art. A missing or failed dynamic image
  reveals deterministic fallback art instead of leaving an empty card.
- When a color is active, both recommendation ranking and thumbnails must use that
  selected color. Show only that color changing in the current material plan; do not
  pretend the candidate covers the whole paint.
- Label preview-resolution material maps as previews. Reserve "exact 2048" for the
  full installation render. During install, the paint/spec TGAs remain exact 2048,
  while response/job PNGs stay bounded to the 512 proof resolution already used by
  Easy; never spend seconds encoding redundant full-size browser previews.
- Preserve the current paint, look, color targets, scales, Material Impact, and deployment
  identity while iterating.
- `Use the paint already open` must accept PSD, TGA, PNG, and JPG sources. When the
  main 2048 canvas is live, sculpt the exact current composite (including in-app edits)
  rather than silently reopening an older file from disk; otherwise fall back safely to
  the real local path. Keep a local path available for the Original Spec Sculpt handoff.
- Browser-uploaded layered PSDs may exceed the app's normal 16 MB request ceiling. Keep
  a bounded 256 MB allowance on Spec Sculpt/PSD routes only, with truthful limit errors.
- A directly selected PSD is transferred and parsed once: its layer import supplies the
  exact-size check, composite preview, and protection tree. Do not upload a large PSD once
  for analysis and then immediately upload it again for the same import. In the desktop
  runtime, use an available local PSD path directly instead of transferring those bytes.
  After a pathless PSD upload, reuse the server-retained import path for every recommendation,
  preview, and install; browsing looks must not resend the original PSD.
  A path-based PSD follows the same one-read rule; do not run `/analyze` before `/api/psd-import`.
- A heavy live-canvas capture must paint its working acknowledgement before synchronous
  composite work begins; no valid click may look like a no-op on a slower machine.
- A named material plan is deterministic: Back restores the exact prior map, and recent
  plans may be cached so exploration never punishes the user with needless rebuilding.
  The server must retain at least the same 12 jobs as the client preview cache, so an
  older visible Back target can never point at an expired render after a long session.
  Every desktop/dev server launcher pins Python's process hash seed; a saved plan must not
  subtly reshuffle because the app process restarted.
- An accidental reload or full app restart must not destroy a finished material plan.
  Reopening the same source restores its look, colors, scales, active target, and library
  context, iRacing Customer ID, and selected discovered car folder; choosing a different paint intentionally clears that recovery record.
- Whole paint and every color target own independent deterministic material seeds. Editing
  one color must not visually reshuffle the base or any sibling color.
- Keep Original Spec Sculpt reachable as the advanced bridge, but visually secondary;
  carry the current local paint/PSD, iRacing ID, selected car/folder, and custom-number mode
  into it instead of presenting another file picker or making the user rebuild the job.
  Its doorway belongs after the Easy workflow, never ahead of area, look, or install.
  Browser-uploaded files with no exposed local path must cross the same-origin doorway
  in memory and enter the Original workspace's existing upload/PSD import path.
- While Easy Mode is open, the permanent Pro workspace must be inert and hidden from
  assistive technology; shared file/modal surfaces remain available when Easy opens them.
- Never claim installation until copied files are verified.
- A multi-color install receipt and Main Render lock name the complete material plan, not
  whichever color happened to be selected when the user pressed install.
- Non-JSON server/proxy failures must become plain recovery instructions; never expose an
  `Unexpected token <` parser error to an Easy Mode user.
- Temporary HTTP failures (408/425/429/5xx) must preserve the paint and expose the same retry
  action promised by the message; never say "try again" while withholding the button.
- Once the full-size install begins, disable Easy/Pro exits until the verified response
  returns; aborting the browser response cannot be allowed to hide a server-side copy.
- Car discovery and installation must resolve the same Windows Documents root, including
  redirected/OneDrive Documents. Verification compares exact file content, not only size.
- Never let an invalid Customer ID or car choice fail silently. Explain the exact missing
  choice in one installation message, focus it, and do not mislabel it as a preview error.
- If discovery returns no cars, never say `Pick from 0 folders`; explain that opening iRacing
  once and reopening Spec Sculpt lets Shokker find the local paint folders.
- Keep a valid destination collapsed by default, but name the exact selected car folder and
  say that paint + spec auto-route together. `SWITCH CAR` opens a plain `WHICH iRACING CAR?`
  selector populated only from discovered iRacing paint folders. Choices lead with a readable car
  name (`Dirt Late Model 438`, `Acura ARX-06 GTP`) and retain the exact folder code beside it;
  Customer ID remains secondary.
  Opening focuses the car choice; `DONE` or Escape collapses a valid editor and returns keyboard focus
  predictably. Invalid fields deliberately stay open. A route is never shown as verified until both folder and ID are valid.
- When destination fields are empty, infer the Customer ID from conventional
  `car_<id>` / `car_num_<id>` filenames and the car from a recognized parent paint
  folder. A conventional filename also determines sim-stamped (`car_`) versus custom-number
  (`car_num_`) output so a hidden stale setting cannot install the right paint under the
  wrong name. Never overwrite a valid manual or restored destination. Hide obvious backup
  and junk directories from Easy Mode's optional car list.
- Never install an incomplete color plan; identify the unfinished color and keep the
  install action locked until it has a look or is removed. A color look with zero matched
  pixels is also incomplete; offer Wide or remove rather than installing a no-op layer.
- While a newly added color is still waiting for its look, do not label the whole-paint
  response meters as that color's response. Hide the irrelevant proof until a real color
  material has been rendered.
- `Try next` and `Surprise me` must always select a different look. If a one-result search
  contains only the current look, leave that dead end and fall back to a useful broader set.
- Main Render must preserve the active Sculpt map until the user deliberately replaces it.

## Screen-space test

Before adding a visible control, answer all three:

1. Does a first-time user understand it without knowing spec-map terminology?
2. Does it save a decision or make the result materially more trustworthy/impressive?
3. Can the feature stay useful with one obvious default?

If any answer is no, put it in Original Spec Sculpt or leave it out.

## Acceptance signals

- The first useful recommendation is visible without scrolling.
- All looks remain reachable within one tap plus search/browse.
- Every shipping named-preset card resolves to a visible 256px thumbnail; Designer
  Fusion cards combine both authored source appearances rather than showing one half.
- A detected paint color becomes a material target with one click.
- Adding a new color clears the prior material search and opens that color's own 12 smart
  picks; switching existing colors may preserve a deliberate search for comparison.
- Base/material scale and generated spec scale move together from one simple control.
- The scale control, its two readouts, preview recipe, and install recipe must agree even
  when a keyboard or assistive input path commits only a range `change` event.
- Preview language explains metal, gloss, and coat without requiring channel knowledge.
- Bad files fail before rendering; failed previews keep the paint and offer a retry path.
- Deep-library exploration preserves the clicked card's visual position and keyboard
  focus while the material preview rebuilds.
- Non-look controls preserve their own focus after a rebuild: Material Impact returns to
  its chosen button, linked scale to its slider, and color reach to its chosen button.
- Subtle, Balanced, and Bold move the reported whole-paint and selected-color response in
  the same human direction, and a non-balanced install receipt names the chosen impact.
- At 1280 x 720 the three default proof panels and their material-response note fit without
  horizontal overflow. Applying another Whole Car look replaces both the sculpted result and
  spec output while leaving the original visible.
- Switching to any discovered car updates the collapsed route immediately, persists with the
  recovered sculpt plan, and sends the exact folder identity as `deploy_car_folder`.
- Clearing the car or invalidating the ID removes ready status and hides `DONE`; correcting the
  field restores both immediately while retaining focus (and the ID caret) in the corrected control.
- Install receipt names the exact verified files and target.
