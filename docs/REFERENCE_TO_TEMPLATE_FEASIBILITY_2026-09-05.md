# Reference images to an actually painted iRacing template

Date: 2026-09-05. Author: Codex. Status: feasibility assessment, not implementation or demonstrated reconstruction accuracy.

**Recommendation: pursue a bounded proof for one calibrated template.** A separate SPB workspace that turns a sufficiently clear, consistent reference pack into editable paint is technically plausible. Arbitrary photographs of arbitrary cars producing an exact template automatically remains unproved. A newer model or more skills alone does not establish that capability.

The decisive dependency is a measured connection between physical car surfaces and template pixels, plus an independent rendering test. The historical work already proposed this architecture. The improvement must be completing and validating that connection, not renaming Forge or writing more gates around guessed placements.

## What was reviewed

Read the Living Wiki board, conventions, trouble spots and bounded historical entries; traced the archived Forge workbooks and selected source; visually inspected the Waffle V20 regression comparison, Crystal Lake rejected/recovery comparison, and the four rejected flat deliveries. Reviewed the later V2/V3 orthographic state as well as the earlier Codex work. Historical scores below are recorded results, not rerun measurements.

Archive root for the links below: `../_archive/root_cleanup_2026-09-04/lane_work/`. Large archives were sampled by named evidence, not treated as current executable truth.

| Attempt | Actual evidence | Implication |
|---|---|---|
| Adidas / early kit ripping | The [lessons](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/LESSONS.md) record an x1.286 coordinate error from reading a resized sheet, inconsistent number assets, wrong side orientation, wheel contamination and crop slivers. | Better semantic interpretation helps, but exact coordinate systems and source asset identity must be enforced by code. |
| Mountain Dew / Miller universal adapter | [Recorded side reconstruction](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/CODEX_UNIVERSAL_ADAPTER_STATE.md) reached 94.8768 on same-reference observed-side reconstruction, with 605,683 common UV pixels, only 14.4406% of the canvas. | Useful partial projection evidence. This was not 94.9% full-car fidelity or an independent iRacing success. |
| Waffle House V20 | [Owner-render comparison](../_archive/root_cleanup_2026-09-04/lane_work/_forge_out/codex_full_surface_adapter/wafflehouse_multiview/V20_REGRESSION_EVIDENCE.png) visibly loses the intended side composition. Its [post-mortem](../_archive/root_cleanup_2026-09-04/lane_work/_forge_out/codex_full_surface_adapter/wafflehouse_multiview/V20_REGRESSION_POSTMORTEM.md) identifies distorted fenders, wrong faces and self-referential scoring. | A correctly named panel and a passing wire containment check do not establish pixel correspondence. |
| Crystal Lake, Waffle, Domino's and Sex Wax deliveries | The [four rejected flats](../_archive/root_cleanup_2026-09-04/lane_work/_forge_out/codex_full_uv_recovery/run_83_actual_flat_rejection/ACTUAL_REJECTED_FOUR_FLATS.png) visibly contain photographed tire/hardware fragments. The [rejection analysis](../_archive/root_cleanup_2026-09-04/lane_work/_forge_out/codex_four_psd_delivery/owner_rejections/2026-07-16_crystal_lake_whole_car_projection/REJECTION_ANALYSIS.md) records evidence-only rasters entering delivery compilation. | Moving photograph pixels is not equivalent to painting a livery. Illumination, geometry and artwork need separate treatment. |
| Full-UV recovery through Run213 | [Final Codex state](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/CODEX_DLM_FULL_UV_STATE.md) says all four remained rejected: the large center island was the driver tub, not the hood; former nose geometry was the hood. Claimed exact mask coverage was 86.44%, but both corrected roles remained hypotheses, 0/2 release-ready. | More mask coverage never repaired wrong physical identity. Older files claiming authority are contradictory and need requalification. |
| Later V2/V3 orthographic approach | [State log](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/V2_ORTHO_PROJECTION_STATE.md) explicitly improved whole-view projection, then recorded 99.1/100 from a proxy score despite remaining visible defects. Its final section reports 65% piece coverage, exact PSD recomposition and no declared placement problems, while still proposing a final master-view review. | This is later work, not proof that the old failure was solved. The inspected final section contains no fresh owner iRacing acceptance. Corpus occupancy and official number blocks are useful priors, not reference-specific placement truth. |

A particularly revealing artifact is [Run115's physical capture report](../_archive/root_cleanup_2026-09-04/lane_work/_forge_out/codex_full_uv_recovery/run_115_physical_capture_bundle_v1/PHYSICAL_CAPTURE_BUNDLE_REPORT.json): its calibration assets and capture plan were complete, but `captured_frame_count` was **0**, `captures_complete` was **false**, and projector/physical-ownership claims were **false**. That describes this bundle; it does not mean no owner screenshots existed elsewhere.

The [physical recovery plan](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/SHOKK_FORGE_CORE4_PHYSICAL_RECOVERY_PLAN.md) also identifies a process failure: a 220-frame prerequisite became an all-or-nothing wall. A smaller targeted capture experiment must demonstrate value before commissioning a full atlas.

## Why it kept failing

Five different questions were collapsed into one: **what the design depicts; which surface owns it; how that surface unfolds; where it is visible; and whether the exported car matches the reference.** Each needs distinct evidence.

The old loop often measured its own assumptions. Mapping an image with a guessed transform and reversing the same transform can reproduce the input even when the real car would be wrong. Exact layer recomposition verifies the file writer. It does not verify the car. A base coat can also hide that almost none of the actual design reached a panel.

Historical example volume did not automatically become reliable learning. Finished TGAs reveal layout conventions and recurring template regions, but usually lack paired camera views, verified physical labels and lighting-free artwork. Averaged examples even produced corrupted mandatory marks in the later V3 notes. Contradictory labels, masks and old accepted statuses must not be pooled as ground truth.

## What current skills change

Vision and code tools can help interpret multiple views, propose landmarks, separate meaningful objects, author editable graphics, inspect native-resolution crops and run repeatable measurements. Image generation can create artwork and concept references. Persistent files can retain verified template knowledge between sessions.

However, the current [OpenAI vision documentation](https://developers.openai.com/api/docs/guides/images-vision) still identifies precise spatial localization, rotation, small text and image resizing as limitations. The [image-generation documentation](https://developers.openai.com/api/docs/guides/image-generation) warns about precise composition, text placement and consistency across generations. These support using model proposals with geometric verification. They do not support promising exact UV layouts from prompting alone.

**No controlled old-model/new-model comparison was run in this audit.** Any claim that the current model has solved this specific task would be speculation. Skills supply methods and tools; they are not themselves trained car geometry. In this proposal, “learn a template” first means building and persisting a verified calibration package. Task-specific model training is a later option once reliable paired examples exist.

## The system worth building

User flow: **Choose car → Add references → Review conflicts or missing views → Build paint → Inspect actual-car comparisons → Open editable layers in SPB.** Template preparation should normally happen once per exact supported template revision, rather than being repeated by every customer for every scheme.

### 1. Template knowledge that survives a conversation

Store the template hash/version/resolution, original layer identity, paintable and protected areas, immutable geometry IDs, verified physical roles, independent left/right reading directions, seams, visibility and calibration captures. Preserve uncertainty per region. A shared family name is insufficient to reuse coordinates across different templates.

There are two viable geometry routes:

- **Exact mesh with matching UVs, if legitimately available:** fit reference cameras, project onto visible mesh triangles, then bake into the existing UV layout. An approximate generic car mesh is insufficient for final placement. This audit did not establish access to an exact mesh; the inspected DLM dossier/template directories contained no OBJ/GLB/FBX/BLEND file.
- **Actual iRacing viewer as a measurement instrument:** display asymmetric diagnostic textures, capture fixed views and decode which texture locations appear at which screen locations. Use independently verified landmarks and seam probes to check the result. This can provide reliable mappings for supported views without extracting a mesh. It does not automatically supply arbitrary-camera 3D geometry.

The [old calibration handoff](../_archive/root_cleanup_2026-09-04/lane_work/_forge_workbook/SHOKK_FORGE_UV_CALIBRATION_HANDOFF.md) and archived decoder are useful starting points. The code includes both an early color-ratio decoder and later multi-pass high-precision encoding. Actual rendering introduces gamma, lighting, highlights, texture filtering, antialiasing and camera drift; synthetic decode success cannot substitute for measuring those effects. Start with a small set of difficult surfaces and an independent marker pattern.

iRacing documents the official [template workflow](https://support.iracing.com/support/solutions/articles/31000133480-how-do-i-custom-paint-my-iracing-cars-). A robust programmatic camera/capture interface has not been demonstrated in this audit. Reliable capture and refresh are first-stage engineering dependencies.

### 2. Interpret design in physical car coordinates

Build one structured design description across all views: background fields, stripes, patterns, number instances, wordmarks, logos and their physical relationships. Example: the number sits between the wheel arches; the primary sponsor occupies the rear quarter above the wheel opening; a stripe continues across the door/fender seam.

The model proposes those relationships and object identities. A registration solver fits their exact position, size and curvature using the calibrated car. [OpenCV pose estimation](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html) supplies established methods when valid 3D-to-2D correspondences exist; [remapping](https://docs.opencv.org/4.x/d1/da0/tutorial_remap.html) applies a known image-coordinate transformation. Neither discovers a correct UV atlas by itself.

Do not constrain every design number to the official default number block. The reference may intentionally differ. Measure artwork against actual body landmarks, using blocks as priors and sim-stamping constraints only when applicable.

### 3. Author clean, editable paint

Reconstruct numbers, text and clean logos from approved assets or verified shapes. Preserve their exact identity and one instance per physical placement. Author paint fields and stripe paths at template resolution through surface coordinates; split a seam-crossing object into related pieces without duplicating its whole design.

Project photographic paint only where body segmentation, registration and lighting treatment support it. Shadows, reflections, tires, cockpit and hardware are not source paint. Complex illustrations may require isolated source artwork or assisted reconstruction; extracting their intrinsic colors perfectly from one lit photo is not guaranteed.

Export named editable layers and a flattened TGA, preserving template protections. Apply SPB materials as a later separate stage: paint placement accuracy and spec appearance need separate evaluation. Existing finish rules continue to govern any finish work.

### 4. Close the loop with independent renders

Render the exact exported texture on the actual car at matched cameras and at a withheld view. Compare object count/identity, reading direction, silhouettes, body-relative landmarks, stripe edges and seam continuation. Evaluate color under controlled lighting; do not optimize a raw RGB match by painting shadows into the texture.

The model can diagnose a visible error and propose a bounded repair. The geometry system applies the repair; an independent render checks it. Keep the better candidate unless measured evidence supports the replacement. An attractive generated car image is never proof that the exported template works.

## Real photographs and AI concepts need different handling

| Input | Realistic initial promise |
|---|---|
| Consistent clear views of the supported car, with clean logos/numbers | Best reconstruction target after calibration. Detail depends on visibility and resolution. |
| Real race photos of that car | Feasible with additional registration, occlusion and lighting work; low-resolution decals may need source assets. |
| AI views with matching body geometry and consistent artwork | Feasible candidate input, subject to the same geometry checks. |
| AI views whose logos, stripes or body panels disagree | Detect and reconcile the disagreement. There may be no single paint that can reproduce every image exactly. |
| One image with unseen rear/opposite side | Reproduce observed regions; offer explicitly inferred design for the rest. More images help only if they add consistent evidence. |
| Reference car with different bodywork from the target | Design adaptation, not exact reconstruction. Preserve design intent while refitting to the target car. |

For AI-origin designs, the strongest eventual workflow is to establish one canonical layered design on the calibrated car and render all subsequent concept views from it. Independently generating five attractive car photos does not ensure that one coherent texture exists behind them. An imported concept can still seed this canonical design after its contradictions are resolved.

## A bounded proof before another large build

**Experiment A — prove the ruler.** Use one exact DLM template. Place asymmetric IDs, arrows, a numbered grid and a stripe crossing a known seam. Capture the real car, fit the mapping, and test a second marker pattern excluded from calibration. Explicitly test hood versus tub, both fenders, left/right direction, roof and deck. First demonstrate a few difficult regions; expand only after the method measures correctly.

**Experiment B — blind reconstruction.** Choose an existing owner-approved painted TGA with layered assets if available. Keep its original paint hidden from the reconstruction stage; supply only controlled real-car renders and any explicitly permitted clean decal assets. Reconstruct using the fixed atlas. Evaluate against the hidden original on observable regions and fresh iRacing views. An audit-controlled test harness must enforce the holdout; merely telling an agent not to look is insufficient. Repeat on two different designs without geometry edits. Rejected historical packs remain regression cases, not the only benchmark.

**Experiment C — intended input.** Reconstruct one consistent AI reference pack and one real-photo pack using the same atlas. Record every manual correction, missing object and unresolved region. Only then connect the separate workspace to normal SPB import and qualify a second template.

Proposed initial acceptance criteria, to be frozen before evaluation rather than tuned afterward:

- Zero wrong surface assignments, mirrored readable objects or duplicate major graphics.
- Every reference-visible major number/logo/wordmark accounted for; correct text verified separately from visual similarity.
- Held-out landmark error and seam error measured in native texture coordinates where correspondence permits it. A starting target is p95 landmark error at most 4 texels at 2048, and seam displacement at most 4 texels. Validate capture precision first; these are proposed targets, not achieved results or a universal fidelity percentage.
- Report observed-area coverage, design coverage and unknown area separately; no base-coat credit for missing artwork.
- Exact layer recomposition and protected-region preservation, followed by independent full-car visual acceptance.
- Record correction count, operator minutes, compute time and inference spend per car. A result requiring manual placement of every decal fails the automation objective even if the final car looks good.

Compare a direct-model baseline with the calibrated pipeline on the same fixed inputs where practical. The existing project has no measured improvement result for the current model. Cap each geometry hypothesis at a small number of informative trials, investigate failure causes, and stop expansion if independent error does not improve. Do not resume recurring/overnight work as part of this analysis.

## What SPB already has, and what must be rebuilt

The root retains [Forge service modules](../forge_service/pipeline.py), a separate Forge page and routes, adapter storage, resumable jobs and PSD import infrastructure. The [registry](../forge_service/adapter_registry.py) exposes DLM capability flags partly from adapter package versions; the inspected package is version 10 with 14 named surface entries. Version flags and populated surface names are not fresh physical validation. The inspected `ForgePipeline.run()` ends at `anchored`/next stage `semantics` when projection succeeds; it is not a completed semantic painting/export pipeline.

Reuse job persistence, original-layer preservation, deterministic raster/export utilities, calibration codec candidates, provenance and selected regression fixtures after narrow requalification. Rebuild physical authority and the end-to-end reconstruction/render test first. Do not restore every archived `_forge*` module or assume the old test counts describe a working current program; the Wiki records collection failures caused by archived imports.

Use a small dedicated backend package and a separate UI workspace, feeding the existing PSD importer only after verification. Respect [SPB's Zone/Layer contract](TOOL_ARCHITECTURE.md); do not grow the main canvas module or let a reconstruction job mutate live zone masks and layer buffers interchangeably. Keep cloud inference optional at the architecture boundary, with explicit per-job usage accounting; local projection should be deterministic. Production cost, latency, licensing of any additional runtime and clean-machine packaging require later measurement.

## Decision

There is enough existing work to justify a focused proof. There is not enough accepted evidence to promise that this is already solved or that arbitrary references will transfer exactly. The first deliverable should be a blind reconstruction that works on the car. If it passes, the separate SPB feature has a credible foundation; if it fails, its isolated measurements tell us whether to fix perception, geometry, artwork reconstruction or capture, rather than starting another unbounded iteration cycle.

Audit scope: documentation/source inspection and historical image review only. No new paint generated, model benchmark run, iRacing paint replaced, application code changed or historical acceptance status promoted.
