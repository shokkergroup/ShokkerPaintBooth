# DLM core-car reconstruction — 2026-09-05

Owner-authorized practical trial: Waffle House first, then Domino's, Crystal Lake / Friday the 13th, and Mr. Zog's Sex Wax. The active goal is reference-faithful, editable paints whose placement is checked on the real iRacing car. No proxy score or successful PSD export constitutes acceptance.

## Current state

- **Active, not accepted.** Historical candidates remain untouched. New work is in `_dlm_rebuild_work/`.
- Original Waffle House reference sheets and owner-labeled official DLM template recovered. Clean number, tile wordmark, roundel, syrup, and waffle graphics extracted with provenance.
- Prior number extraction was visibly compressed. Fresh source number is 384 × 221; preserve its aspect when placing it.
- Official labels are orientation clues, not physical ownership proof. The actual grid pass shows the engine cover extends into the region labeled TUB; the original draft hood bounds are too short.
- Native historical side masks can help define boundaries; their old role/readiness claims are not physical placement proof.
- Actual DLM 438 grid, Waffle, and Domino's captures obtained. Latest staging is recorded in `calibration/active_staging.json`; original four files are hash-verified in `calibration/backups/20260905T054337Z`.
- **Owner roof rule:** DLM roof numbers face the grandstands. The original Waffle v04 direction was correct. The agent's camera-upright reversal in v05–v08 and Domino's v01–v02 was a regression, not an improvement. `template_rules.json` records the correction and the scratch compiler rejects the reversed basis.

## Viewer access and file safety

The owner authorized unrestricted viewer use **after 05:41:20 UTC on September 5** (01:41:20 EDT), following his requested 30-minute delay. Leave native iRacing controls alone until then. He will leave the Dirt Late Model 438 viewer open.

Owner confirms all three DLM cars share the template: 350, 358, 438. Observed local folders include spaces: `Documents/iRacing/paint/dirtlatemodel 438` (and corresponding 350/358 folders). Work on 438 only for this trial. Existing customer 23371 paint/spec files must be copied with SHA-256 records before any diagnostic/candidate swap; preserve restoration files outside the active paint folder.

## Acceptance evidence

1. Reference likeness: correct silhouette of the number, sponsor hierarchy, artwork scale, color blocks, checker detail, syrup/waffle placements, and independent left/right text.
2. Physical placement: actual iRacing views of both sides, hood/nose, roof, rear deck/spoiler. No painted tires, cages, seats, lighting, wire guides, or false wheel holes.
3. Editability: independent named layers for base fields, stripes/checker, illustrative graphics, numbers, and branding. No opaque difference-snapshot repair layers.
4. Final owner-eye verdict remains outstanding until the owner reviews the actual candidate. Do not label historical `DELIVER` directories as accepted work.

## Reproduction

- `_dlm_rebuild_work/inspect_sources.py`: read-only template census and inspection copies.
- `_dlm_rebuild_work/prepare_trial.py`: clean source asset extraction and calibration texture.
- Each candidate must record its asset manifest, mapping version, output hashes, and actual-car captures.

## Session ledger

- 05:11 UTC: owner authorized continued goal work and delayed viewer availability; explicit goal created without a token budget.
- 05:13 UTC: fresh source asset contact visually checked; adjacent graphic fragments removed from syrup/waffle extractions. No car files changed.
- 05:24 UTC: Waffle `trial_v03` now contains both sides, roof, hood, rear deck, and spoiler in 45 independent PSD pixel layers. Source SVG plates remain editable. PSD recomposition maximum error is 1/255; hiding the left door number changes 63,613 pixels and zero pixels outside its alpha. These are file/editability checks only.
- Provisional mapping v0 clipped 12.164% of the left number; v1 reduced that to 1.183%. Residual clipping and all physical dimensions/directions remain calibration work. The right rear wordmark was raised within the provisional layout to clear the native arch. No metric is treated as an owner verdict.
- Built-in ImageGen produced one provisional hood illustration from PAGE 3, with branding applied separately. The exact prompt and provenance are in `_dlm_rebuild_work/waffle/imagegen_log.md`. Two side-decal generations failed real-alpha inspection (RGB checkerboards); the side candidate uses supplied original graphics instead.
- Remaining core source sheets inventoried: 10 each for Domino's, Friday the 13th, and Sex Wax. Each has a distinct layout; they are not Waffle recolors.
- Reversible staging utility has an executable 05:41:20 UTC gate, immutable original-file hashes, and restoration support. Actual staging history is in `calibration/active_staging.json`.
- 05:37 UTC: full Waffle pre-viewer draft is `trial_v04`, with 58 independent pixel layers; the same PSD reconstruction/hide-number checks pass. Stop unobserved variants here and use actual car evidence next. Fresh source assets prepared for all four schemes. Crystal Lake filenames `(2)`, `(5)`, `(6)` actually contain PAGE 6 numbers, PAGE 2 right, PAGE 5 rear respectively. Compact continuation instructions: `_dlm_rebuild_work/VIEWER_RUNBOOK.md`.

Diagnostic spec is a flat nonmetallic rough material with clearcoat disabled, solely to make grid labels readable. Blue-channel interpretation is grounded in the [official iRacing 2023 S1 release notes](https://iracing.freshdesk.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-). It is not a finished material design.

### Actual-car pass, 05:43–06:00 UTC

- Owner explicitly resumed viewer control after the physical Escape stop. Baseline paint and all four active files preserved before staging the grid, then v04.
- Actual captures: `calibration/captures/baseline_00.png`, `grid_left_elevated_01.png`, `waffle_v04_left_elevated.png`, `waffle_v04_right_front.png`. These are iRacing captures, not simulated renders.
- Both side numbers and sponsor groups land on their intended side regions. Remaining spacing/clipping must be judged against references. Hood lettering is mirrored and hood artwork stops before the air-filter region. These failures reject v04 for delivery. Earlier claims that the rear deck was mirrored and the roof direction wrong were incorrect: measured coordinates resolved the deck, and the owner explicitly confirmed the original grandstand-facing roof.
- Paint Shop initially selects Limited even when opened from the Super information view. Explicitly selecting **Dirt Late Model - Super** restores the staged 438 candidate. Paint files reload automatically. Native clicks work; camera drags have not yet visibly rotated the model.

### Measured top-view correction, 06:04–06:09 UTC

- Owner positioned an elevated top view and confirmed left-button hold + drag and wheel zoom; prefers fullscreen. Tool drag did not visibly rotate, although file reload and zoom work. Mouse Keys shortcut did not enable the feature (registry Flags 62/off); Control Panel launch failed without opening a window. No accessibility setting change is retained.
- New deterministic Gray-code calibration uses 19 actual renders (black/white, 8 U bits, 8 V bits, and a separate checker check). 280,654 pixels decoded confidently; held-checker agreement 99.9904%. All frame hashes are recorded. This covers visible surfaces only, with 8 px native bins, and does not score likeness.
- Waffle trial_v05 / mapping_v4 correct hood mirroring and hood extent (rear corners measured near U1090; v04 started at U1324). Its roof reversal was subsequently rejected by the owner. Rear-deck direction was initially misread in an oblique view; the actual coordinate data proves its existing text direction correct. Its layout now uses the visible deck behind the roof.
- Actual v05 top capture confirms the wordmark is readable and the hood art reaches around the air filter. PSD has 59 independent pixel layers, max recomposition difference 1/255; hide-number changes stay inside that number alpha. No owner acceptance yet.
- Preliminary dense homographies reject a single planar main-hood approximation (p95 8.52 screen px). Curved regions must be split or use the measured map directly. Flat-patch fits and original captures are retained, not promoted as a universal geometry model.

### Owner correction and second scheme, 06:26 UTC

- Owner: **"Roof direction on Dirt Late Models ARE supposed to be facing the grandstands so they were right the first time."** Restored the original positive-U / positive-V basis for the 600×500 roof plates in Waffle mapping_v8 and Domino's mapping_v3. Roof direction follows this semantic rule, not the inspection camera's readability. Previous reversed candidates remain evidence of the error, not accepted output.
- Waffle now has separate source roundel layers on the two spoiler-side masks. Side body-edge fits address the old shear that clipped upper rear logos and lowered front contingencies. Explicit correspondences and residuals are in `calibration/reference_side_alignment.json`; lower side-view validation remains open.
- Domino's independent SVG/layer draft uses original 23, tile logo, wordmarks, Noid and contingency artwork. Actual trial_v03 top capture shows the restored roof direction, hood tile clear of the filter, and upper/rear color placement. Side clipping, front fender color wedges and hood-wordmark margin still need work. Neutral diagnostic material remains temporary.
- Gray-code measurement proves visible UV correspondence, not reference fidelity. The flat-patch fit's random pixel split is preliminary; a formal fit must hold out entire UV cells to avoid repeated-cell leakage.

### Camera input diagnosis and roof post-mortem

- Owner explicitly requires the agent to operate orbit without asking for angles all night. The supported `sky.drag` fails a separate Photoshop brush test: one dot appears at the start; no stroke follows the moving pointer. Thus the failure extends beyond iRacing. Wheel zoom works; the available tool API has no separate hold/release or duration parameter. Exact reproduction and other routes checked: `_dlm_rebuild_work/calibration/CAMERA_INPUT_DIAGNOSIS.md`. This is unresolved, not camera-control success.
- A second actual Gray-code set, `gray_left_01`, independently resolves 231,129 visible pixels at 99.9996% checker agreement. That map and the actual lower-left/right Waffle views remain useful for correcting clipping and semantic placement.
- **Roof post-mortem:** measured coordinates establish orientation on the mesh; they do not establish which audience should read the art upright. Reversing a roof to suit the inspection camera replaced a correct motorsport layout with a wrong one. Owner's grandstand-facing rule is now recorded separately in `template_rules.json`, and the scratch compiler rejects the reversed basis. Placement and likeness still require review.

### Direct mouse helper verified — camera blocker resolved

The owner's supplied SendInput suggestion passed the same Photoshop path that failed under `sky.drag`: one continuous stroke, subsequently undone and scratch closed. `_dlm_rebuild_work/calibration/DragMouse.ps1` then rotated the actual maximized DLM 438 viewer horizontally on its first attempt; vertical rotation and wheel zoom also passed. Evidence is saved as `sendinput_photoshop_stroke.png`, `sendinput_iracing_rear_threequarter.png`, and `waffle_v09_top_sendinput.png` under the calibration capture directory. No original Photoshop document edits, installation, elevated process, or security setting change. Foreground/process guards and a finally-block release constrain the helper to each freshly observed action. This resolves autonomous camera control, not scheme likeness or owner acceptance.

### Autonomous placement pass, 07:14–07:35 UTC

- New measured views: `gray_left_low_02` (182,983 trusted pixels, checker agreement 100%), `gray_right_low_01` (156,480, 99.9987%), `gray_rear_01` (90,789, 99.9989%). Each has 19 hashed actual frames and a decoded UV archive. Unlike the early top fit, these fin/wing fits hold out entire UV cells: left fin 161 cells/33 holdouts/max 2.34 px; right fin 176/35/max 2.08 px; outward wing 360/72/max 2.09 px.
- Waffle `trial_v14`, mapping `mapping_v13.json`, source `artwork_v3`: number margins repaired without changing numeral proportions; WH badges contained on the actual shallow fins; nose X direction corrected from mirrored front lettering while preserving the correct lower-band Y direction; hood logo enlarged proportionally with its top anchored clear of the air filter.
- The former `spoiler_outside` at V1925..2011 was the inward face. Actual outward wing coordinates are in the V1800s. Boxed WAFFLE HOUSE lettering is now on that rear face, clear of the vertical rib.
- Source defect: `waffle/assets/wordmark.png` actually reads WAFFFLE HOUSE. SVG crops in `correct_waffle_wordmark.py` remove only the extra F, retaining the supplied glyphs and HOUSE row. Corrected asset and provenance are in `waffle/assets_corrected/`. Both sides, hood and deck now use the six-letter word. The wing's substitute plain-font text was replaced with original letter tiles.
- Actual v14 front/right/upper/rear/left captures are attached to the candidate manifest and verified against the stage active when saved. TGA SHA-256: `f8d1f4ef12f720008bd657e078b1bce8cfce5049ec93e74e58599bea5549e92b`. PSD verification: 63 pixel layers, max recomposition difference 2/255, mean 0.0110/255; hiding left number changes 54,731 pixels with zero changes outside its alpha. This verifies editability only.
- Remaining Waffle work: reference white/yellow front-fender sweeps, lower-nose band/fold extent, detailed illustration likeness and final materials. The reference rear-center placard has no demonstrated usable paint equivalent in the current view; center-box response was 0 and lower-panel median response ~0.67. Do not paste a placard onto unrelated hardware. The right rear-wheel white crescent had 0 response versus ~121 on adjacent paint, proving it is open space in this view.
- Shared physical rules updated in `template_rules.json`; carry fin/wing/nose corrections to Domino's (still v03), then author Crystal Lake and Sex Wax. No final owner verdict. Current 438 paint remains Waffle v14 plus diagnostic spec while goal work continues. Original backups and other car folders untouched.

### Curved fenders and front lip, 07:39–07:59 UTC

- Rechecked the supplied mouse-drag note against the saved Photoshop/iRacing evidence. Its direct SendInput workaround is working through repeated autonomous rotations and wheel zoom. Built-in `sky.drag` remains the specifically reproduced failure; no further owner-assisted camera movement is needed.
- Waffle `trial_v17`, `mapping_v15.json`, `artwork_v5`: independent yellow outer-fender wedges, fine arch lines, and white front-face sweeps. `project_fender_vectors.py` projects editable vector contours through measured UV-cell triangles, rejecting contours outside the measured hull or crossing large UV gaps. The side fits hold out whole cells: p95 1.30/1.43 screen px. This verifies correspondence only.
- New front set `gray_front_01`: 19 actual frames, 203,407 trusted pixels, 99.9862% held-checker agreement. `refine_graycode_cells.py` adds two lower Gray bits to refine the same fixed camera from 8px to 4px native cells, without recapturing the original set. Refined set: 155,715 trusted pixels, 100% independent checker agreement. Front-fender whole-cell holdout p95 is 1.25/1.12 screen px; maxima 2.60/6.54. Unobserved regions and hull-edge extrapolation remain excluded. This is not a complete mesh or a likeness score.
- The unwanted yellow border beside the hood was an uncovered nose boundary around native U1668..1684/V1300..1340. Added a separate black foundation underneath the existing hood and nose artwork. The lower vertical lip is another UV strip near U2000..2040; its measured hull is now dark, retaining the yellow stripe on the valance above it. `repair_front_vectors.py` and `calibration/front_lower_lip.json` record the repair.
- Actual front, left-upper and right-upper v17 captures show the corrections and are attached to its manifest with stage-time/hash checks. TGA SHA-256: `f074ddfaa32228cbf2c6d16bd2514b456d974f2eb4e3fbdea39297a33ff9d107`. PSD: 71 pixel layers; maximum recomposition difference 2/255, mean 0.01133/255; hide-number changes 54,731 pixels and zero outside its alpha. The grandstand-facing roof and prior lettering repairs remain intact.
- Remaining Waffle work: fine contour/illustration likeness and final materials; reference syrup and waffle structure still differ from the hood illustration. Current material is neutral diagnostic, not final. Transfer the confirmed physical geometry to Domino's next; Crystal Lake and Sex Wax are still unpainted. No owner acceptance claim. The active 438 paint remains v17 for continued goal work; originals are preserved in the immutable backup.

### Waffle hood and materials checkpoint, 08:12 UTC onward

- `trial_v20`, `artwork_v8`, unchanged measured `mapping_v15.json`: revised hood image retains longer syrup drips and returns the waffle grid to fine scale. Stretched v18 and oversized-grid v19 were rejected. Full ImageGen prompts and hashes: `_dlm_rebuild_work/waffle/HOOD_IMAGEGEN_20260905.md`.
- Diffuse SHA `4eb5ba55a9eb8a4c54b195c8c0a720a1787b9d01c2f655077e4fac0cc8b6ef9c`. Editable PSD: 71 pixel layers, recomposition max 2/255, mean 0.011333/255; hiding left number changes 54,731 pixels, zero outside its alpha.
- Custom `materials_v1` follows named paint masks and separately classifies syrup/waffle. Identity and channel encoding recorded before rendering. 57 editable spec layers, 994 distinct material RGB triples, PSD reconstruction max 1/255. These are structural checks, not likeness scores or catalog M7 acceptance. Spec SHA `51e9cf2ebc6db4a305ddeab628597d5958abe48c59773fa5ddbbcc7f4c60e514`.
- Actual front/left/right v20 views attached to diffuse and spec manifests with stage/hash validation. Black panel gloss and hood material separation visible. Waffle remains a review candidate: fine illustration/contour likeness and owner eye pending. No production renderer/catalog changes. Continue Domino's geometry transfer next.
- Usage incident: reading a short SVG line window emitted a huge embedded data URI. Line count is not a safe output bound. New `inspect_svg_structure.py` parses SVG and prints bounded attributes plus embedded-image hashes; use it for all SVG reads.

### Domino's measured geometry and independent layout, 08:17–08:28 UTC

- Current `dominos/trial_v09`, `dominos_mapping_v9.json`, `dominos/artwork_v7`. Reused confirmed DLM fin, outward-wing, nose and separate lip geometry while preserving Domino's own artwork. Roof still faces the grandstands. The original supplied tile is 225×224; hood placement now preserves that proportion, and the wordmark has a margin.
- Actual v04 exposed incomplete fin backgrounds, isolated lower-fender patches and rear-branding collisions. Full outer-fin masks now provide blue backing, fenders have blue fields and editable white arches, and the separate front lip plus adjacent U1870s fold are red. Black/white field placement remains a reference interpretation, not an owner-approved match.
- Both PIZZA words moved clear of the main wordmark and the rear red streak now passes below them. Final layer clipping: left/right Noid 0.00050/0.00137 (from 0.10035/0.14622); hood wordmark and right rear wordmark zero. This is containment evidence only: the actual right Noid ears remain close to DOMINO'S and need a visual clearance correction.
- `smooth_dominos_fenders.py` removes cell-scale path jitter: p95 movement 0.57/0.63 actual screen px, maximum 1.64/1.06. v06's extra front sweep duplicated the side accent and was rejected. v09 retains one smoothed arch per side. Full contour likeness remains open.
- Four actual v09 views—left, right, rear, front-upper—attached to its manifest with stage/hash checks. Outward-wing lettering is readable. PSD: 68 editable pixel layers; recomposition max 1/255, mean 0.008826812/255; hiding the left number changes 52,068 pixels, none outside its alpha. Diffuse SHA `1199ce0b5c3ea6fdd85ce2ccfb3ce600a2fd8eb1dd601e157b3fcce8705fd36b`. Neutral diagnostic spec, not final materials. Immutable original 438 files remain intact; 350/358 untouched.
- Reference conflicts are explicit in the map: PAGE 2 main right number slants opposite its own detail and PAGE 6; PAGE 1/2 white-upper fenders disagree with PAGE 4 blue front fenders. Remaining Domino work: right Noid ear clearance, inner-fin/wing colors, lower-lip side returns, final contours/materials and owner-eye judgment. Waffle v20/materials_v1 remains the earlier review candidate. Next broaden to Crystal Lake and Sex Wax from their extracted references; neither has an authored paint yet. No production application or catalog changes.


## Crystal Lake v05 — first four-view material checkpoint

- Current candidate: `friday13/trial_v05`, `crystal_mapping_v5.json`, `friday13/artwork_v5`; 70 editable pixel layers. Independent PSD reconstruction max 1/255, mean 0.008967; hiding the left number changes 44,970 pixels, zero outside its alpha. These are editability checks, not likeness scores.
- The same physical DLM masks do not imply identical source-photo coordinates. Crystal's own upper/lower body boundaries were fitted separately; reusing Waffle's source origin initially clipped artwork. Curved wood is projected through measured front/side UV cells by `project_surface_texture.py`, with hull and long-triangle guards.
- Source-alpha fault found and repaired: border-white removal had erased 988 legitimate moon pixels. `restore_crystal_moon.py` reproduces the original crop, restores original RGB/opacity inside the moon and removes 457 background islands outside it. See `friday13/assets/moon_restoration.json`. v05 actual left/right views show complete round moons; no generated replacement moon was used. Grandstand roof direction retained.
- Fine green/brown wood and a quiet forest background were generated from references; original numbers, lettering, mask, moon, cabin and contingency marks remain separate. Exact prompts and asset hashes: `friday13/imagegen_log.md`, `imagegen_asset_hashes.json`. Whole generated rear-scene composition was rejected for focal spacing; v1 wood was too dark.
- `materials_v1` follows named paint features and eight per-feature intensity tiers; no metallic wood or emissive-window claim. 54 spec layers, 1,893 combined material states, reconstruction max 1/255; M/R/Cc ranges 0–0 / 32–190 / 35–218. Both manifests attach four actual DLM438 front/left/right/rear views checked against staged diffuse/spec hashes. Fresh SendInput drags succeeded for each camera change.
- Active 438 diffuse SHA `3b91d5028b6ed4dc929e57d212f8f4f070252e3e2321aedc60be8c07cc8d99c5`; spec SHA `1f42681860486f1f233804aba83bcadaed67396230e0fec0f21ac4eabeca0ce8`. All four immutable original backup hashes verified; 350/358 untouched.
- Still a review candidate: hood moon is obscured by the air cleaner in the current front view, and wood tone, scenery/sign proportions, fender transitions, lower-lip side returns and gloss balance need comparison/refinement. Waffle v20 and Domino's v09 remain preserved with their previously recorded issues. Sex Wax is the remaining unpainted core scheme. No production application/catalog changes or owner acceptance claim.


## Sex Wax v04 — four actual material views and a legacy mask correction

- First authored fourth scheme: `sexwax/trial_v04/SEXWAX_55.psd` + TGA, `sexwax_mapping_v4.json`, `sexwax/artwork_v3`, `sexwax/materials_v2`. All four core schemes now have actual-car trial paints; none is owner-accepted.
- Original 55s, roundels, words, waves, burst and contingency decals are separate layers. Neighboring shapes caught in the right number and burst crops were removed after inspection. PAGE 8 supplies clearer white FloRacing and sponsor variants. A generated fine cream texture is the sole new bitmap illustration; built-in tool, exact prompt and saved asset/hash are recorded in `sexwax/IMAGEGEN_LOG.md`.
- Independent source body/wheel alignment was fitted before placement. v01 actual views exposed sponsor clipping and front-fender coverage issues. v03 uses a measured smooth outer-arch boundary: cream above, black below and across the inner front; it also restores the right number's top outline and clears FloRacing from the wheel. All main numbers, roundels and contingencies have less than 0.1% clipped alpha. Remaining fine contours are not thereby accepted.
- A significant semantic error was diagnosed through actual captured UVs. The historical `left_quarter_window` mask includes the bumper/frame region at U0–299/V0–154. Changing the fallback color alone failed because its cream foundation overrode it. v04 restores that region to black. The same rear view proves the correction; diffuse/spec each changed 41,788 pixels, zero outside the mask. Some trim also shares the mask: subdivide with actual evidence before restoring cream trim. `calibration/frame_region_evidence.json` records trusted points and source hashes.
- Current diffuse/spec PSDs have 86/70 pixel layers and max recomposition error 1/255 each. Hiding the left number changes 59,891 pixels, none outside its alpha. Material states follow this scheme's actual cream, matte black wave ink, orange/yellow ink and wear; M stays zero. Both manifests contain four actual v04 views, checked against staged paint/spec hashes. These are structural and placement proofs, not visual acceptance.
- Active 438 diffuse SHA `47fe894a40f19e5a9f3334af7d61d986d8fc69961a9d92b6ea27d6d21928221d`, spec SHA `5739e21c041415a962195e80e5d68107f1b6cd1fd03028cc9db54d508b1e68f5`. All four immutable original hashes verified; 350/358 untouched. Grandstand roof direction preserved.
- Remaining Sex Wax work: fender spears/tips, orange lip returns, inner fin/wing colors, weathering and burst character, and owner-eye likeness/material review. Next shared correction: actual sampled frame texel is already black in Waffle v20, but white in Domino v09 and green in Crystal v05. Fix those two candidates, then continue their recorded individual likeness issues. No production runtime/catalog edits.

## Domino v10 — source cleanup, frame repair and a fresh drag confirmation

- Rechecked the owner's pasted SendInput suggestion against the existing implementation and saved Photoshop/iRacing evidence. Fresh held drags again rotated the actual DLM438 through front, right, rear and left views. No change to the working helper was needed; native drag failure and successful workaround remain documented in `calibration/CAMERA_INPUT_DIAGNOSIS.md`.
- `correct_domino_noid_and_frames.py` preserves original Noid RGB while clearing 582 contaminated alpha pixels, including source-sheet caption fragments. `noid_clean_v2.png` is embedded in both sides. Right Noid is reduced/lowered and DOMINO'S raised; the actual right view shows clearance above its ears. The source and previous candidates are preserved.
- v10 restores the measured shared frame region to black. The actual rear view confirms black bumper/tubes. Four captures are attached to the manifest and verified against staging hashes. Diffuse SHA `847f2664573d66b3927fd0920ce91e0c3dfb93d506ff6b96e7f7cc131958be63`; neutral spec remains in use. PSD: 68 layers, max reconstruction error 1/255; hiding the left number changes 52,068 pixels, zero outside its alpha.
- Crystal `trial_v06` / `crystal_mapping_v6.json` carries the same diffuse frame repair and passes its 70-layer PSD check, max 1/255; hiding the left number changes 44,970 pixels, zero outside alpha. It has not yet received the corrected frame material or actual v06 validation. Preserve v05/materials_v1 as the previous evidenced candidate.
- Active 438 is Domino v10/neutral spec; immutable originals were hash-verified by staging. Pending: Crystal frame spec/checks, Domino's first custom spec, and the already recorded art/contour/trim refinements across the four cars. No owner acceptance or production-runtime change.


## Material completion pass and Crystal PAGE 4 front variant

- Domino v10 now has `materials_v1`: smooth white/blue/red coated paint and original printed inks, nonmetallic throughout. Its material foundation contains no flattened decals. 68 editable spec layers, reconstruction max 1/255; hiding the left number changes 51,094 pixels, zero outside its alpha. Four actual material views are attached to diffuse/spec manifests with matching stage hashes; neutral checks retained. Spec SHA `27775d8b6f2bb8c67f8fc352a05f3a8d9f6af92a59d0cb282cf48a3dc15e1ab3`.
- Crystal v06/materials_v2 finished the frame correction: 41,788 changed spec pixels, none outside the measured mask, 55 layers, max reconstruction 1/255. Four actual views confirm black frame/tubes. This preserves the PAGE 3 hood layout for review.
- PAGE 3 and PAGE 4 specify different hood compositions. V11 is an explicit PAGE 4 variant, using the original isolated WELCOME TO wooden sign instead of the smaller three-line sign. The scene is shifted forward; the moon clears the actual air cleaner in elevated and lower front views. The PAGE 4 variant omits PAGE 3's hood sponsor stack. Original sources and v06 remain preserved.
- Source extraction needed more than border flood fill: antialiased paper edges left white outlines, and red drips enclosed white/gray paper islands. Boundary matting plus bounded lower/taper cleanup corrected these while retaining source lettering and moon interiors. Final sign `front_welcome_sign_page4_v5.png`; final hood scene `cabin_scene_clean_v4.png`. Exact crops, thresholds, unchanged regions and hashes are recorded beside the assets. V07–v10 are intermediate cleanup attempts, not owner-accepted paints.
- V11/materials_v3: 66 diffuse / 51 spec layers, reconstruction max 1/255 each. Number hide changes 44,970 diffuse / 44,762 spec pixels, zero outside alpha. Five actual views are attached to both manifests. The material base now comes from foundation geometry alone, so removing a decal does not expose its baked material ghost.
- Current 438 diffuse SHA `b7f7f7a77560a139cd1b605b194214b67c14494b63dc9dce6a43db20efbbe107`, spec SHA `1fbfc0a77988f49662a81b6812f87dac9eff19582d1e81df51b1ef1bf12e6ffc`. Immutable original hashes checked; roof direction preserved; 350/358 untouched. No production runtime/catalog changes.
- Still unfinished: Crystal hood/rear-deck forest/lake coverage (large plain wood gaps remain), source-choice review, scene/sign proportions, fender/lip/trim continuity and gloss; Domino Noid scale/edges, fins/lips/fenders and owner materials; earlier Waffle and Sex Wax fine-likeness work. Existing `night_forest_background_v1.png` is suitable to test as background behind separate focal assets. Every scheme remains owner-unaccepted.


### 2026-09-05 — Mouse suggestion evidence and unstaged forest checkpoint

The owner-supplied mouse-drag suggestion is confirmed by the retained Photoshop dot-versus-stroke test and actual horizontal/vertical iRacing views: use the guarded SendInput helper; camera control is resolved. No new mouse-input test or helper modification was needed.

Crystal v13/artwork_v12/map_v13/materials_v4 completed its local builds and editability checks, but remains unstaged. The new hood background and separately editable source moon/cabin/sign are retained. Rear alpha coverage still misses 38,587 of 356,268 measured polygon pixels because the source canvas remains too narrow; correction and actual-car checks are next. V11/materials_v3 remains active. Full details and the next matrix are in `_dlm_rebuild_work/VIEWER_RUNBOOK.md`. Goal and owner acceptance remain open.


### 2026-09-05 — Crystal v15 forest coverage and visible cabins

Crystal Lake: `friday13/trial_v15`, `crystal_mapping_v15.json`, `artwork_v14`, `materials_v6`. Full hood/rear forest fields and visible original-source cabins above/beside the PAGE 4 sign. Five actual views; 71 diffuse / 56 spec layers, max reconstruction 1/255. Rear measured uncovered pixels fell from 38,587 to 282. PAGE 3 remains v06/materials_v2; no owner acceptance.

V14 exposed a cabin almost completely hidden by the sign. V15 keeps source pixels and moves/scales two independent cabin layers above/beside the sign, with the moon right of center. Rear source width corrected from 600 to 710 while preserving focal placement. Five actual captures match staged paint/spec hashes. All four original backups verified; only 438/customer23371 staged; grandstand roof orientation preserved. No production renderer/catalog edit or owner acceptance. Remaining work is recorded in the current runbook.

V15 low-front limitation: the sign remains vertically compressed relative to PAGE 4 and red nose/lip bands remain too broad. Right quarter-window trim needs an independent source/UV check. These are next-step observations, not accepted details.


## SHOKK FORGE handoff and dual PSD delivery

The owner assessed overall results at approximately 75–80% likeness and requested a transferable explanation/skill before further refinement. `docs/SHOKK_FORGE_HANDOFF_2026-09-05.md` now documents camera control, Gray-code correspondence measurement, independent source artwork, real-car iteration, portable profile contracts, product integration boundaries, a Claude/new-template test and exact current artifacts. No weight training or unattended-product claim.

`_dlm_rebuild_work/handoff_20260905/` contains a portable skill ZIP and a separate four-paint ZIP. All four current versions retain byte-identical TGA/detailed PSD/spec sources and actual capture hashes. New simple PSDs have exactly SPONSORS / NUMBERS / BASE PAINT, with reconstruction maximum 1/255 and independent group hiding showing zero changes outside group alpha. Crystal's 331 number/sign overlap pixels required visible occlusion in foreground masks; its detailed master retains hidden artwork. Portable decoder reproduces all five original front-8px arrays exactly, with 203,407 trusted pixels and 99.9862% held-checker agreement. Skill validation and ZIP integrity pass; manifest records hashes and unproved claims.

Skill installed in the owner's personal Codex skills folder. An actual SPB simple-file import/edit/save/reopen, clean-machine setup and independent model/new-template test remain outstanding. Existing paint versions/staging were not changed. Resume Crystal front sign, red nose/lip proportions and right-quarter trim, then the recorded other-scheme likeness work. Overall paint goal remains unfinished.


## Paint work resumed after the handoff

Crystal's new working candidate is `friday13/trial_v16`, `artwork_v15`, `crystal_mapping_v16.json`, `materials_v7`. The four-paint ZIP deliberately retains the completed handoff snapshot (Crystal v15/materials_v6); it is not silently replaced by this later experiment.

PAGE 4 uses fine red/brown valance trim. V15 had a 32-source-pixel solid band and a fully red lower lip. `refine_crystal_front_bands.py` replaces those blocks with three narrow strokes and a green lip foundation, using the measured native hull. The sign/scenery and other surfaces are unchanged. Exactly 55,296 diffuse pixels changed, zero outside nose/lip regions. V16 has 72 diffuse / 57 spec layers, maximum reconstruction 1/255 each; independent number-hide checks pass. Two actual front/left captures are attached to both manifests with matching staged hashes. Right-view inspection and side returns remain open; this is not final likeness acceptance.

The viewer reopened on a newer custom-number Sex Wax paint than the recorded stage. That file and its generated cache were preserved in `calibration/external_paint_backups/20260905T131739588549Z/`; their hashes and restoration overrides are in `calibration/active_staging.json`. `viewer_paint_files.py` now detects intervening TGA edits before staging/restoring, keeps the original baseline immutable, and restores newer user changes for the affected files. A temporary-directory regression verified a newer number paint/cache and intentional file absence surviving stage/restore. All original and override backup hashes were verified.

Held drags succeeded on both axes again. The foreground guard also stopped drags when Task Manager was in front. Reobserve, activate iRacing, inspect whether activation restored a smaller window, maximize if needed, and then drag from fresh coordinates. Do not diagnose a foreground rejection as a failed held-mouse implementation. Current capture output was JPEG; retained `.jpg` files preserve the returned bytes.

Next: correct the compressed front sign using measured hood/nose continuity, inspect v16 from the right, then validate right-quarter trim and the remaining four-scheme defects. Reproduce v16 from the retained artwork/map with fresh output names; the one-off trim builder refuses existing v15-art/v16-map/trial directories. Do not rerun it blindly. Current diffuse SHA `f4a95a1fc9502d4d6f3c7a37ef22023202f4b76ba5594bb096b2fd0dc994639f`; spec SHA `75532536686cc66f532eb809237f62a1d63d3b626b1daf9a548070f512ce6642`. Only 438 is staged, currently at the left-front view. The broad paint goal remains unfinished.


### Waffle front recheck after owner clarification

Voice recheck: loaded unchanged Waffle v20/materials_v1 and rotated the actual viewer to the front. Front 77 and Hoosier/QA1/COMP/BILSTEIN are readable, not mirrored. No paint correction was needed or made. Passenger-side number height has not been re-evaluated in this check. Viewer left on Waffle front; latest staging and evidence are saved.

Owner then confirmed the front 77 and sponsors are correct. The front strip remains visibly wrong and is the next front defect; do not mirror or reposition the accepted number/sponsor artwork as part of that repair. This is partial orientation acceptance only.


## First gate: preserve the correct car body

Owner requirement: start from the correct car/template body already present in a verified source file. Prefer the full iRacing PSD; a correct TGA is the minimum acceptable baseline. A blank texture or labeled UV chart is not an equivalent body baseline. Preserve a copy, its hash, exact car/version identity and native dimensions before painting.

Load the baseline on the actual car and confirm its grille, applicable decals/rivets and other required details before custom artwork. Establish which details come from exported texture layers and which are supplied by the renderer. Identify the allowed custom-paint mask and independently evidenced protected regions. Clip every custom paint operation to its permitted regions and verify that protected source pixels/details survive composition and export. Do not infer protected regions solely from a filename, darkness or a connected paintable-mask component.

With a PSD, record layer hierarchy, masks, blend modes, visibility and roles: substrate, required exported details, optional variants, guide-only content and spec content. Hide export guides according to the real template's conventions. An important car detail must survive, but a guide layer named Mandatory is not automatically artwork to bake into the TGA. Verify the actual render.

With only a TGA, retain the clean body baseline and explicit protection masks as separate immutable inputs. Do not claim that original layer semantics have been recovered. Prefer a clean template; inherited race numbers/sponsors must not become hidden ghosts in the base paint. Keep custom numbers/sponsors separate and keep required car details in their proper compositing order. Preserve the detailed authoring master; flatten the appropriate template-detail composite into BASE PAINT for the simplified PSD without breaking required occlusion.

Test the clean baseline first, then the paint operation's mask containment, protected-region comparison and actual-car result. Temporary coded calibration textures do not replace the preserved starting body. Existing DLM drafts have not yet passed this newly explicit body-preservation gate; this record does not claim that missing details are already restored.


### Owner supplying the authoritative body baseline

Owner will provide the correct starting TGA and raw iRacing-download PSD in this chat. Those files have not arrived at this checkpoint. Inspect and hash the supplied originals, verify clean car-body rendering and required/protected details, then adapt the paint compiler before further paint refinement. Do not substitute the older/labeled template just because it is already on disk. Current viewer remains Waffle front; front 77/sponsors accepted, strip and passenger-side number-height review still open.


## Official DLM 2025 source received and checked

The owner supplied `Dirt Late Model2025.psd` and withdrew the assumption that DLM should include NASCAR-style headlights/grille artwork. The official source has 48 layers at 2048 square. Its clean export and actual DLM438 front/passenger-side views have no baked headlight/grille graphics. Do not treat their absence as missing artwork or add substitute grille/headlight details.

Source and derived assets are in `_dlm_rebuild_work/official_dlm2025/`: immutable `SOURCE_OFFICIAL.psd`, full source manifest, clean PNG/TGA, isolated original layers, guide comparison, inspection image with both Mask/Wire enabled, and two actual-car captures. The original external PSD hash is unchanged. The saved source has Mandatory and Mask visible but Wire hidden; the owner's open Photoshop document may have a different unsaved visibility state. Only the inspection copy enables Wire.

The source's Mandatory, Number Blocks, Sponsor Blocks, Mask and Wire are in its export-excluded guide group. Retain them for learning and constraint checks; they are not themselves a colored overlay to bake into the final TGA. Keep actual exported details such as Rivets and Pitbox Colors distinct from guide graphics. WOO/Dirtcar decal layers are separate variants; the supplied WOO-visible state was preserved for this baseline, not declared mandatory for every recreation.

Wire pixels exactly match the retained guide. Alpha coverage of Mandatory, Mask, Rivets and number/sponsor guides also matches; only small RGB differences remain in Mask/Rivets. Existing native UV evidence can be retained. A conservative allowed-paint mask was derived from transparent Mask/Mandatory pixels (3,406,052 allowed pixels), but it remains a candidate constraint: it is not proof of surface ownership and must not replace the measured physical atlas.

Clean baseline was checked from front and passenger side with the existing neutral diagnostic spec. Capture times and hashes match staging. Waffle v20/materials_v1 was then restored to the viewer, now at the passenger side. Its front 77/sponsors remain owner-accepted; the front strip is still open, and the right number sits close to the upper checker/rail and needs the owner's earlier height correction considered. No new scheme artwork was edited during source inspection.

Next: integrate the verified source baseline, actual export-detail layers and confirmed protection constraints into the experimental compiler, with a scoped before/after preservation check. Do not claim current candidates already pass that integration gate. Then repair the Waffle strip/right-number placement without touching accepted front number/sponsor orientation, and resume the other recorded scheme defects.

Owner clarification (2026-09-05): the DLM PSD decal logos, including WOO/Dirtcar, are optional, replaceable scheme artwork. They may be hidden or changed. Do not force them on, protect their pixels as mandatory body details, or bake them into every base paint. Keep them separately editable when used. The earlier WOO-visible baseline records the supplied visibility state only.
