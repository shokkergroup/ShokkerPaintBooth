# SPB Tool Architecture — Zone vs Layer Contract (SPB-93)

**Status**: Foundational document for the Heenan Family Tool Trust Sprint (SPB-93).  
**Last updated**: 2026-08-09 (owner-directed Photoshop/GIMP parity program)
**Owner**: Bockwinkel (architecture) + Heenan Family

> This document defines the **single source of truth** for how painting tools must behave, integrate, and be organized in Shokker Paint Booth. It is the cure for the 19k-line `paint-booth-3-canvas.js` monster.

---

## 1. The Problem We Are Solving

As of May 2026, the client-side painting system lives almost entirely in two massive files:

- `paint-booth-2-state-zones.js` — **17,116 lines** (state, zones, `canvasMode`, per-zone `regionMask` + `spatialMask`)
- `paint-booth-3-canvas.js` — **19,101 lines** (everything else: `setupCanvasHandlers`, all mouse dispatch, 15+ tools, Layer transform system, file picker, decals, placement drag, etc.)

**Core disease**: There is **no architectural boundary** between:
- **Zone tools** (operate on `zones[i].regionMask` / `spatialMask`, traditional zone workflow)
- **Layer tools** (operate on active PSD layer pixel buffers + transforms when a PSD has been imported)

What exists today is only a **runtime flag** (`toolbarEditMode = 'zone' | 'layer'`) and two guard lookup tables inside one giant closure. This is insufficient for professional trust (Photoshop / GIMP / Trading Paints parity).

Every new professional feature (better pressure, smoothing, clone stamp, healing, adjustment layers, true layer masks) makes the file worse and increases the risk of Zone ↔ Layer desync bugs.

---

## 2. The Zone / Layer Contract (Definitive Rules)

**Element commands and copies (SPB-93, 2026-09-08):** viewport context routing admits paintCanvas/transformCanvas after pan suppression; the dedicated menu owns bounds and keyboard. Projects/history retain independent groups/instances. `element-instances.js` prepares actual non-overlapping copies read-only; the caller publishes one Layer history action. A picked instance moves independently; only explicit groups batch transforms. Link bounds relocate simultaneously from immutable pre-change rectangles. CPU element preview/commit rasters preserve colors; extracted source rectangles clear fully (alpha-weighted destination-out leaves ghosts). Native saved-layer master/copy/outside pixels and Undo/Redo/Cancel are exact. Sync/Re-apply share `prepareSync`: current-master Layer-local crop, complete candidate, full target clearing, current bounds, cloned snapshot metadata, then one history/publication transaction after settling active geometry. Native master/copy invocation, Undo/Redo and project roundtrip verified; independent rotation preservation is verified. `sourceToInstance` maps current master document coordinates to copy coordinates; relocation composes the committed copy transform and inverse master transform around the previous map. Match raster flip/rotation/scale order and padded centers. Legacy rectangular records infer an initial map. Picked linked masters/copies use saved identity before alpha flood/lift, retaining padding and link access. Non-primary transform-down exits before hit testing/commit so context-menu access preserves its session. Apply/Cancel/deactivation must clear `layerSubRectDragActive` when clearing freeTransformState; the mousemove owner guard requires an actually active Layer transform. A stale flag otherwise swallows all drag dabs after the first, including on a newly imported document. `prepareLinks` changes only metadata: promotion rebases relative maps around the selected copy and retains all destinations; breaking a master re-homes remaining siblings. Settle geometry before preparing, snapshot history before publication, and never stamp pixels merely to change link ownership. Native rotated role reversal, inverse sync and exact Break history are in the tools report. `instance-appearance.js` owns six Layer appearance candidates with module-local HSL conversions (the later global helper has a different return shape). Current source, alpha-aware circular hue statistics, immutable input, preserved color-action alpha, and one settled history transaction are mandatory. Finish/Replace use affine paint appearance copying; never mutate Zone spec from this Layer path.

**Zone material scale (SPB-93, 2026-09-08):** Zone base/pattern/spec-piece placement persists a single uniform scale. `js/canvas/zone/transform-scale.js` keeps all edge/corner handles proportional and anchors the opposite side (Alt centers); use drag-start geometry and rotated axes. Layer stretch stays in its own scale module. Active transform overlays redraw after Fit/zoom/Edit Big to keep hit targets aligned. Contracts: `zone_transform_scale_contract.cjs`, `layer_transform_scale_contract.cjs`, `zone_sub_piece_contract.cjs`.

**Project tool-workflow persistence (SPB-93, 2026-09-08):** `spb-projects.js` uses CPU-backed Layer raster encoding/decoding to preserve native composite precision. Its explicit layered import passes `{ restoreProject: true }`, suppressing independent crash recovery only for that import; ordinary source imports keep confirmed recovery. Project validation/rollback owns saved state. In-app project naming lives in `js/features/project-name-dialog.js`; Enter/Save and Escape/Cancel resolve a name or null. Native11-layer edit/save/reopen and `project_import_recovery_contract.cjs` cover the boundary.

**Paint cache publication (SPB-93, 2026-09-07):** `recompositeFromLayers` and flat-pixel history restore must advance `_spbLayerRev` before preview publication. History pushes alone are insufficient: Undo and repeated edits sharing one undo entry must invalidate both live composite and encoded PNG caches immediately. Keep unchanged-paint finish controls eligible for cache reuse. Executed regression: `tests/paint_cache_history_contract.cjs`.

**Exact Layer publication and bounded work (SPB-93, 2026-09-07):** Layer history retains immutable drawables; edits replace `layer.img` rather than mutate a saved image. Import and recomposite publish through the same compositor. CPU-backed commit crops preserve native rounding. `js/canvas/layer/paint-commit-bounds.js` merges active alpha bounds with original off-document strips; `thumbnail-refresh.js` refreshes only the edited row, with full-panel fallback when absent. Neither module owns routing or history.

**Adjustment previews (SPB-93, 2026-09-07):** the preview session owns the immutable original and publication. Large previews use `adjustment-worker-client.js` with one in-flight request and latest pending state; the worker shares the pure Apply kernels. Stale responses cannot publish. Cancel/Apply dispose the worker and restore the original before Cancel finishes or Apply makes its one exact native-resolution commit. Worker errors use synchronous fallback. Flat preview/restoration advances the paint revision too. Contracts: `adjustment_worker_contract.cjs`, `adjustment_preview_session_contract.cjs`.

**Rectangle guide and produced bounds (SPB-93, 2026-09-07):** the temporary rectangle border and colored fill live in `rectSelectionBox`; begin/move/cancel perform no region canvas pixel reads or writes. Actual masks are published only on commit. The hard Replace mask producer returns exact bounds/count, shared through `SPBMaskStats.primeBounds` only for the unchanged non-feathered candidate. The usual microtask expiry and mutation invalidation apply. Add/Subtract and feathered candidates use normal scans. Contracts: `rect_css_preview_contract.cjs`, `rect_produced_bounds_contract.cjs`.

**Render mask presence (SPB-93, 2026-09-07):** the common mask encoder and canonical/Fleet/Season serializers share byte-mask presence through `_renderMaskHasPixels` and the existing same-turn stats cache. Other mask types preserve their original positive-value predicate. Never extend cache lifetime to speed serialization. Executed complete-payload parity: `tests/render_mask_stats_contract.cjs`.

**Spec Tool persistence (SPB-93,2026-09-08):** authored `specMaterialRemap`, `specMaterialOverride` and `specLightingMask` must survive the actual session and shareable-preset JSON maps in state-zones, not only the extracted zone-config module. Preserve numeric lighting alpha0 and explicit null clears. Native remap output was correct but reopening dropped it because the live maps omitted these fields. Executed live-map contract: `tests/spec_tool_persistence_contract.cjs`; native saved-TGA Undo/reopen parity in the tools report.

**Render source readiness (SPB-93,2026-09-08):** `js/canvas/render-source-readiness.js` gates full-render and preview entry on published pixel dimensions/length and the existing PSD import counter. Import start/finally and canvas-dimension changes refresh the button; no per-stroke observer or polling. Readiness restoration requests one debounced preview, never an automatic full render. Keep terminate/cancel available. Never resize masks to the browser canvas placeholder. Native early-reload failure and exact post-ready output are in the tools report; contract `tests/render_source_readiness_contract.cjs`.

**Exact Spec inspection (SPB-93,2026-09-08):** compiled PNG alpha is material data. Canvas readback loses RGB at zero alpha and rounds low-alpha values. `js/canvas/zone/spec-png-pixels.js` reads stored8-bit RGB/RGBA PNG channels directly. The live and delegated inspector providers share raw pixels with sampling/selection and channel stats; pending/error states must not fall back to canvas approximation. Ignore stale source completions. Applying a sampled M/R/Cc/A material removes a conflicting Lighting Mask in the same Zone history entry. Native saved-file proof and independent PNG decoder tests are in the tools report.

**Committed SOURCE parity (SPB-93,2026-09-08):** normal readback Layer recomposites use `js/canvas/layer/composite-publication.js`: fresh stack canvas → one pixel read → explicit SOURCE publication, reusing that canvas in the existing export memo when no active paint surface is present. Native Transform Undo previously differed by one RGB level on the reused display surface while fresh/export composites were exact. Keep live gesture/dirty previews on their existing fast path. `tests/paint_cache_history_contract.cjs` executes the actual publication and immediate Undo/Redo/export cache path; native proof is in the tools report.

**Stroke source ownership (SPB-93,2026-09-08):** `paint-source-snapshot.js` may retain the initialization read as one immutable, transient full-canvas snapshot only when the original image is entirely in-canvas at integer coordinates. Consume once with image/target/geometry/dimension validation. Compare that snapshot at origin0,0; retain the original complete-raster read for off-canvas/fractional fallback and off-canvas union. Never turn this into a history-wide pixel cache. Contract: `tests/paint_source_snapshot_contract.cjs`; native consecutive-stroke/Undo and4096 timings in the tools report.

**Stroke region publication (SPB-93,2026-09-08):** `paint-composite-region.js` uses the exact stack compositor on a translated CPU region canvas for ordinary integer-position/source-over Layers. A baseline belongs to one stroke and must match revision, dimensions, order, metadata and non-active image/bounds identity. Complex stack semantics and unknown/full dirty requests keep full publication. Separate frame/stroke unions prevent RAF consumption from losing commit coverage. The known synchronous history snapshot may advance a valid baseline by exactly one revision; other changes invalidate it. Publish into a new pixel array/canvas; never mutate saved baseline pixels. Native real11-layer4096 median commit248→122ms, independent fresh full SOURCE/export parity0, exact Undo. Contract: `tests/paint_composite_region_contract.cjs`.

**Zone instance data ownership (SPB-93,2026-09-08):** `patternInstances` belongs to Zone configuration. Preserve independent records in live save/load/preset maps and delegated maps; `_cloneZoneState` already deep-copies them for history. Create/Sync/Re-apply/Promote/Break snapshot before mutation; reject empty-link operations without history. Existing visual implementation remains unaccepted: it captures SOURCE paint and the engine does not consume its snapshot payload. Actual material render/placement must be implemented before claiming visual sync. History/persistence foundation: `zone_instance_history_contract.cjs` and native saved-project evidence in the tools report.

**Version2 material content (SPB-93,2026-09-08):** `engine/zone_material_instances.py` places copies at the shared final preview/TGA/export-layer boundary, sampling immutable completed material arrays. Spec alpha is lighting, independent of geometry coverage. Paint ownership compares rendered/source bytes; unchanged raw Layer artwork never transfers. Version2 records carry original document dimensions, source/render-source rectangle, independent destination rectangle and rotation. Legacy paint snapshots are inert. `material-instance-payload.js` forwards only v2 fields through all frontend builders; server preview must preserve the list. Creation model finds separate document space. Native Create/Undo/Redo preview passes; independent transforms and remaining link actions are still unaccepted. Tests: `test_zone_material_instances.py`, `zone_material_instance_contract.cjs`.

### 2.1 Definitions

- **Zone context**: The traditional SPB workflow. A livery is divided into named zones. Each zone has a `regionMask` (Uint8Array) and optional `spatialMask`. Painting affects the selected zone’s masks. The final render merges zones + their finishes.
- **Layer context**: Activated when a PSD has been imported (`_psdLayersLoaded === true`). The user can toggle into "Layer Toolbar Mode". Painting and selection now target the **active PSD layer’s pixel data** instead of (or in addition to) zone masks. Many tools become "layer-local".

### 2.2 Hard Rules

1. **Ownership is absolute**
   - Code that primarily mutates `zones[i].regionMask` or `zones[i].spatialMask` **belongs in the Zone system**.
   - Code that primarily mutates an active PSD layer’s pixel buffer or its transform/bbox state **belongs in the Layer system**.

2. **Dispatch is the single source of truth**
   - The only place that decides “does this tool run in Zone mode or Layer mode right now?” is the dispatch logic (currently the giant `onmousedown` / mousemove handlers + `isLayerToolbarMode()`).
   - Every tool **must** be explicitly registered in one of the two guard maps:
     - `zoneOnlyToolNames`
     - `layerOnlyToolNames`
   - Dual-path tools (brush, erase, fill, gradient, clone, etc.) must route through a clean abstraction (`paintTarget`, `activeMask`, `pushUndoForCurrentTarget`).

3. **No cross-contamination**
   - A Zone-only tool must never write directly to layer pixels.
   - A Layer-only tool must never write to `regionMask` / `spatialMask` (except when explicitly “baking” a layer selection back into a zone mask as a deliberate user action).

4. **Undo parity**
   - Zone mask changes → `pushZoneUndo` / `pushUndo`
   - Layer pixel changes → `_pushLayerUndo` + layer snapshot
   - The system must never mix the two undo stacks for the same stroke.

5. **Preview & live feedback parity**
   - Fast overlay arcs, ghost previews, cursor feedback, and live render triggers must feel identical whether the user is painting a zone mask or an active PSD layer.

### 2.3 Document-capability and interaction contract (2026-08-08)

The layout stays recognizable; the document decides which mutation authority is valid.

- **Flat TGA/JPEG/PNG/BMP** loads are Zone documents. A successful flat load settles any outgoing Layer stroke, clears private and public PSD/XCF/ORA state, selects Zone mode, then publishes the new pixels. A saved Layer mode must never leak into the flat document.
- **PSD/XCF/ORA** loads are layered documents. Layer pixels, bboxes, visibility, locks, blend state, and the active Layer remain authoritative; Zone masks remain a separate material/UV authority. Successful import publishes one private/public state, selects the topmost visible editable Layer, and enters Layer mode. The layered picker accepts an exact typed file path without directory scanning (including files hidden by large-folder protection) and reports the real PSD/XCF/ORA format. A degraded locked source-composite fallback remains Zone-routed.
- An explicit Layer-creation action may promote the working session to Layer mode. A normal flat-image load may not do so implicitly.
- Tool activation is truthful: a Zone-only or Layer-only tool routes to its owner before it appears armed. A tool with no usable Layer target refuses immediately and leaves the current tool active. Manual mode switches must also end on a compatible tool (Layer → Move, Zone → dual Brush when the prior tool is incompatible), and stale persisted Layer mode is ignored on flat startup. Pick Color retains its owner-frozen routing. Spatial Exclude routes to Zone before arming—including from the Easy toolbar—while its owner-frozen temporary-eyedropper Alt intent, round red-mask footprint, undo, preview, and mask math remain unchanged (owner superseding activation direction, 2026-09-03).
- A pointer gesture is one transaction: pointer-down captures the target and pre-edit state, pointer-move previews locally on SOURCE, pointer-up commits exactly one undo entry, Escape/cancel restores the exact pre-edit state, and a no-op creates no history.
- The History panel is a read model over all mutation authorities; it does not own another competing undo stack. Ctrl+Z, toolbar Undo, and the visible history label must agree on the next action.
- SOURCE feedback is frame-bounded and immediate. Retouch kernels publish their dirty pixel union to the active Layer, while the whole Layer stack is composited at most once per animation frame. Expensive 3D/server preview work may trail local pixels but may never block pointer input or discard the final released position.

---

## 3. Current (Flawed) Implementation

- `toolbarEditMode` and `isLayerToolbarMode()` live in `paint-booth-3-canvas.js:15288`
- Guard tables + early return blocks live in the main `canvas.onmousedown` (~lines 2624–2665)
- Most actual painting kernels (`paintRegionCircle`, `paintCloneStroke`, `_paintOnLayerAt`, etc.) are still in the same file.
- Layer free-transform system (`activateLayerTransform`, transform handles, quickbar) is appended at the bottom of the same 19k-line file.
- `paint-booth-layer-flow.js` (only ~1.3k lines) handles PSD loading and `_psdLayers` state but is loaded *after* the giant canvas file.

This is the exact anti-pattern that makes tools feel “jinky” and untrustworthy.

---

## 4. Target Architecture (Post-Foundation)

### 4.1 Recommended Module Structure (Future State)

```
client/js/                          (or keep flat + numbered files during transition)
├── core/
│   ├── state/
│   │   ├── zones.js                # zones[], regionMask, spatialMask, zone CRUD, undo
│   │   ├── layers.js               # _psdLayers, selectedLayerId, layer pixel buffers, layer undo
│   │   └── canvas-mode.js          # canvasMode, toolbarEditMode, isLayerToolbarMode
│   └── utils/
│       ├── coords.js
│       └── masks.js                # RLE, shift, combine, fast arc overlay
├── canvas/
│   ├── setup.js                    # thin setupCanvasHandlers orchestrator
│   ├── dispatch.js                 # ★ THE SINGLE SOURCE OF TRUTH for tool routing
│   │   (zoneOnly / layerOnly maps + require* guards + target abstraction)
│   ├── placement-drag.js
│   ├── decal-interaction.js
│   └── overlay.js
├── tools/
│   ├── shared/                     # brush spacing, hardness falloff, smoothing, stabilizer, pressure
│   ├── zone/                       # only ever touch zone masks
│   │   ├── brush.js
│   │   ├── wand.js
│   │   ├── rect-lasso-pen.js
│   │   ├── spatial-brush.js
│   │   └── eyedropper.js
│   └── layer/                      # only ever touch active PSD layer pixels or transforms
│       ├── brush.js
│       ├── clone-stamp.js
│       ├── transform.js            # free transform, rotate, quickbar (moved out of monster file)
│       ├── history-brush.js
│       ├── dodge-burn.js
│       └── adjustment/             # future non-destructive work
└── layers/
    ├── psd-loader.js               # current paint-booth-layer-flow.js responsibilities
    ├── selection.js
    └── paint-target.js             # isLayerPaintMode, _initLayerPaintCanvas, etc.
```

During the transition we keep the numbered `paint-booth-*.js` files as thin facades that re-export from the new structure so the three-copy build and script tags continue to work.

### 4.2 Dispatch.js Responsibilities (Non-Negotiable)

`dispatch.js` (or the dispatch section while we are still in the monster file) must be the **only** file that:

- Knows about `toolbarEditMode`
- Owns the two guard name maps
- Calls `requireZoneToolbarMode()` / `requireLayerToolbarTarget()`
- Decides which paint kernel + undo path to invoke for the current stroke

No other file should contain `if (isLayerToolbarMode())` checks for routing decisions.

---

## 5. Rules for Agents & Autonomous Work (SPB-93)

These rules are **mandatory** for any agent (Grok, Claude, Cursor, Codex, or the running Heenan autonomous scheduler) working on tools.

### 5.0 Usage Budget Rule (2026-05-17)

SPB-93 work must follow `docs/SPB_LOW_USAGE_PROTOCOL.md` and `docs/SPB_93_LOW_USAGE_PROTOCOL.md`.

- Use `node scripts/spb_context.js --list` and named slices before reading the giant canvas file.
- Do not print all of `paint-booth-3-canvas.js` or raw full diffs of it.
- Keep loops paused unless the owner explicitly re-enables them with a narrow target and longer interval.
- Prefer extraction into small files so future agents inspect modules, not the 19k-line monster.

### 5.1 Scoping Rules (Strict)

- When the autonomous mode or a sub-agent prompt says “work only on `paint-booth-3-canvas.js` with targeted reads”, the agent **must** obey (offset + limit reads, never load the whole file).
- New tool implementations must be created as **separate small files** (`tools/zone/xxx.js` or `tools/layer/xxx.js`), not appended to the monster.
- Any change that touches both Zone and Layer paths must be reviewed by at least two Heenan personas (Bockwinkel + Nash recommended).

### 5.2 Change Size Rule

- Single autonomous cycle = **one smallest safe, reversible, high-impact improvement**.
- Never exceed ~80–120 lines of net diff per cycle unless explicitly approved on Linear.
- Every change must be fully reversible (guarded by `typeof` checks where possible).

### 5.3 Documentation & Linear

- Every significant architectural or tool change must be reflected in this document.
- Every cycle must post a concise update + diff (or link to diff) as a comment on **SPB-93**.

### 5.4 Two-Copy Awareness

Since 2026-06-09, client tool files have exactly two supported runtime copies: project root (source of truth) and `electron-app/server/` (installer tree). The vestigial `pyserver/_internal/` copy was deleted and must not be recreated. Painting-kernel modules must be present in `scripts/runtime-sync-manifest.json`; run `node scripts/sync-runtime-copies.js --write --verify` after every change and keep root/Electron bytes exact.

---

## 6. Immediate Next Steps (Foundation Hardening)

1. ✅ Create this document (`docs/TOOL_ARCHITECTURE.md`)
2. Update `AGENTS.md` with a prominent “Tool System Architecture” section + link here.
3. Extract `dispatch.js` (or at minimum the guard tables + `isLayerToolbarMode` logic) into its own small file as the first real module split.
4. Pick the highest-pain dual-path tool (Clone Stamp is currently being worked on autonomously) and split its implementation into `tools/zone/clone-stamp.js` + `tools/layer/clone-stamp.js` while keeping the old function as a thin delegator.
5. Add regression tests that assert “Zone-only tool never writes layer pixels” and vice versa.

### 6.1 Extracted SPB-native Zone tools and controls (updated 2026-07-19)

- `js/canvas/retouch-readiness.js` (SPB-93, 2026-09-07): Retouch menu guidance reads dispatch activation authority, without document mutation on menu open. Its explicitly labeled blank-layer action activates Color Brush and verifies the result; an empty layer is not advertised as source artwork for retouch. No new routing, pixel or undo authority. Six executed controller/dispatch scenarios plus current-source live recovery/Undo verified; full simplification goal tracked in `docs/TOOLS_SIMPLIFICATION_2026-09-07.md`.
- `js/canvas/tool-menus.js` (SPB-93, 2026-09-07): owns only dropdown lifecycle, viewport containment and keyboard navigation. Escape consumed by an open menu restores summary focus and must not reach canvas cancellation. Live83,520px selection survived menu Escape unchanged. Narrow Edit Big panel clearing is CSS-only and preserves panel state; no new document, dispatch or undo authority.

- `js/canvas/brush-footprint.js`: pure shared geometry for Round, Square, Diamond, Slash, and Noise tips across both Zone masks and Layer pixel tools. It owns no dispatch or mutation; each tool resolves one footprint per dab/stroke, then keeps its existing Zone/Layer target. Shape-relative distance keeps non-round hardness falloff truthful, while Canvas-path tracing and a bounded Noise stamp cover the native Layer brush path.
- `js/canvas/layer/clipboard-layer.js`: pure source-link and placement policy for copied pixel layers. Paste and Ctrl+J are always independent layers; only the explicit Transform Selection lift may retain `sourceLayerId` for commit-time bake-back. Normal Paste resolves selection center -> visible canvas center -> canvas center with bounds clamping; Paste in Place preserves exact source offsets. It owns no pixel capture, stack mutation, or transform dispatch.
- `js/canvas/layer/layer-transform-raster.js`: pure commit and raster helpers for Layer transforms. Source alpha is removed with scoped `destination-out` before transformed pixels are composited, linked elements preserve their source-relative offsets, and transformed selection alpha is rasterized at full canvas authority with translation/rotation/flip/scale plus soft-edge preservation. Zone mask combination is byte-wise Replace/Add/Subtract/Intersect; the canvas controller remains the only owner of Layer pixels/history and Zone routing.
- `js/canvas/layer/rgba-blend.js`: pure straight-RGBA/premultiplied-alpha compositing for Layer pixel tools. Opaque paint and sampled texture use source-over; History uses state interpolation so amount 1 restores exact RGBA. It owns no target selection, history, dispatch, canvas, or Zone state.
- `js/canvas/layer/psd-import-safety.js`: pure PSD hierarchy flattening, blend-name normalization, and source-vs-reconstructed-stack fidelity scoring. `server_routes/psd_import_tree.py` gives import metadata and raster payloads the same collision-free positional identity while retaining full paths and inherited visibility. The canvas controller remains the only Layer-state owner and fails a divergent/incomplete import closed to a locked authoritative Source Composite instead of clearing valid paint. Public sequential `psd_N` IDs remain stable for saved Zone bindings.
- `js/canvas/layer/selection-placement.js`: pure proportional-fit geometry for the app-specific **Fit Layer to Zone Selection** command. It reads only the selected Zone mask bounds and selected Layer dimensions; the canvas controller remains the sole owner of Layer transform preview, Enter/Escape settlement, and history. The command never mutates a Zone mask.
- `js/canvas/layer/adjustment-preview.js`: pure RGBA mutators for all eight live Layer adjustments, including Gradient Map and Color Replace. The controller captures one immutable Layer source, publishes disposable selection-clipped previews, restores the exact source on Cancel, and restores source before the existing transactional commit so Apply creates exactly one Layer undo. The module owns no dispatch, canvas, history, PSD state, or Zone mutation.
- Layer Effects follows the same modal transaction contract even though its renderer remains in the transitional canvas controller: opening captures an immutable pre-dialog Layer-stack snapshot outside History, controls preview live on SOURCE, Apply publishes that snapshot as exactly one Layer action, and Cancel/X/Esc restores the original effects without clearing Redo or leaving ghost history. The dialog docks left with no backdrop blur so SOURCE remains visible throughout the session.
- Layer names edit inline in the Layers rail: double-clicking a name or pressing `RENAME` selects a focused 64-character editor in place. Enter/click-away commits one Layer-history action only after validation; Escape cancels with no History mutation. Native blocking `prompt()` dialogs are forbidden for this flow because they hide app context and break continuous painter interaction.
- Layer stack order supports both row dragging and Photoshop muscle memory: `Ctrl+[` / `Ctrl+]` moves the selected Layer down/up one step, while `Ctrl+Shift+[` / `Ctrl+Shift+]` sends it to the bottom/top. Each successful command is one Layer-history action; boundary no-ops and locked Layers never consume History. Zone order and Zone masks are outside this command path.
- Active Layer and Zone free transforms expose live inline `R°`, `S%`, `X`, and `Y` number fields in the persistent context bar. Typing previews handles/SOURCE without History; Enter or blur settles the field value inside the still-open transform session; Escape restores that field's focus-start value; transform Apply remains the sole commit and transform Cancel restores the original. Blocking native numeric prompts are forbidden for these visible transform controls.
- `js/canvas/layer/selection-clip.js`: pure active-mask authority. Layer tools ignore inactive Zone region masks; alpha lock and an explicitly enabled Zone region remain the only valid Layer clips. Zone tools keep their existing region ownership.
- `js/canvas/layer/history-budget.js`: pure Layer-history memory policy. It estimates retained RGBA bytes, preserves a five-entry floor, keeps up to 30 small or cropped edits inside a 96 MiB budget, and reports evictions so the controller prunes the matching unified-history entries. It owns no stacks, DOM, routing, or mutation.
- `js/canvas/layer/fill-bucket.js`: pure Fill working-raster selection plus contiguous-candidate logic. A click inside a cropped Layer keeps the fast local path; a click elsewhere expands to document coordinates so transparent canvas can be filled without shifting existing pixels.
- `js/canvas/layer/document-capability.js`: pure initial-Layer selection for normal and degraded imports. The controller owns publication, toolbar routing, and UI; this module only chooses the correct Layer object.
- `js/canvas/paint-dirty-region.js`: pure clamped rectangle/circle union. Retouch kernels mark their changed bounds; the controller consumes one union for bounded `putImageData`, with a full-upload fallback for whole-document commands.
- `js/canvas/confirm-dialog.js`: transient docked confirmation UI for destructive canvas/Layer commands. It owns DOM/focus/Escape/outside-click cleanup only; command controllers retain validation, History, and mutation ownership.
- `js/canvas/dispatch.js`: owns mode, ownership maps, activation preflight, and activation-time routing. Spatial Exclude is Zone-owned and routes there before arming; only its established pointer and mask semantics remain frozen.
- `js/zones/zone-undo-history-controls.js`: renders the unified chronological history read model supplied by the canvas controller. Its controls call the same Undo/Redo dispatch as keyboard shortcuts; it owns no competing stack.
- `js/canvas/stroke-dynamics.js`: pure input normalization and stroke sampling. Mouse is pressure-neutral and receives the configured size/opacity exactly; pen pressure curves are monotonic and bounded by those controls. Continuous Brush/Erase and every continuous retouch brush use distance-based spacing with pressure interpolation and carry across pointer events, so dab density does not depend on event frequency. Each tool retains its Layer mutation owner and tool-specific pixel kernel; the controller batches generated dabs into one surface upload per pointer segment.
- `js/canvas/zone/selection-move.js`: compact mask analysis/translation for Move Border drag and fine/coarse keyboard nudge. It owns only `zones[i].regionMask`, captures the starting Zone, uses a GPU ghost, and commits one real Zone-mask undo per burst.
- `js/canvas/zone/decal-rescue.js`: Zone-only iRacing sim-stamp material rescue. It applies verified flat Foundation M/R/CC recipes to the active UV selection, forces source-paint mode, clears competing spatial/layer restrictions, and never touches PSD pixels. Zone-config Undo/Redo now refreshes the compiled preview so recipe history is visually truthful.
- `js/canvas/zone/selection-refine.js`: pure candidate engine for Grow, Shrink, Fill Holes, Feather, and Smooth. It uses typed arrays and separable passes, never owns history or UI, and lets the thin canvas controller compare before a single real Zone-mask snapshot. Selection refinement and Select All mutate only the captured Zone's `regionMask`; no-op candidates never create history.
- `js/canvas/zone/spec-lighting-mask.js`: Zone-only iRacing spec-alpha authoring for exact selected UV footprints. It changes nullable `specLightingMask` only, preserves RGB/M/R/CC and layer pixels, validates before one Zone-config history entry, and delegates alpha application to the engine's common post-material/pre-cache point.
- `js/canvas/zone/spec-material-sampler.js`: pure point sampling/coordinate mapping plus a thin Channels Inspector integration. A sampled flat M/R/CC/A override is Zone configuration, never layer pixels; it requires an exact region selection, creates one Zone-config undo only when changed, and the engine applies it before any explicit Lighting Mask alpha override.
- `js/canvas/zone/spec-material-select.js`: typed material-channel selection over compiled preview M/R/CC/A. Select Connected is a four-neighbor flood; Select All Similar is a full-field range query. Both compose through the current Replace/Add/Subtract mode, compare before one actual Zone-mask snapshot, scale preview masks to canvas resolution, and never write layer pixels.
- `js/canvas/zone/zone-mask-history.js`: atomic multi-Zone region-mask capture/restore for destructive batch commands such as Clear All. Snapshots are deep copies keyed by stable Zone ID with index fallback; undo and redo capture reciprocal state and never masquerade as Zone-config history.
- `js/canvas/zone/spec-material-remap.js`: pure per-channel M/R/CC range mapping plus a thin Zone controller. It preserves texture ordering and local detail, stores only Zone configuration, clears a competing flat override on apply, and leaves source RGB, alpha, and PSD pixels untouched. The engine applies it before flat material transfer and Lighting Mask alpha.
- `js/zones/base-spec-scale-link.js`: pure Base/Spec Scale state contract. Missing or `match` mode means Spec follows Base atomically; only explicit `independent` mode permits divergence. It owns no rendering or DOM mutation. The Zone UI disables independent Spec controls while linked, config/Finish DNA persist the explicit mode, and every render builder resolves through the same linked value.
- `js/zones/zone-keyboard-controls.js`: installed-once owner of Zone N/Shift+M/Delete shortcuts, in-progress Lasso cancellation, and visible Zone/finish modal Escape. It consumes Escape only when it acted, leaving plain Escape to Layer selection semantics otherwise.
- `js/canvas/zone/canvas-mask-geometry.js`: pure flip/rotate/resize transforms and stable-ID mask snapshots used by composite canvas geometry. Region masks resize bilinearly, categorical spatial masks resize nearest, and pixel history restores dimensions + paint + Zone masks as one transaction.

All bounded canvas modules are loaded before `paint-booth-3-canvas.js`, are Node-testable without DOM mutation, and are synchronized through the runtime manifest. `zone-keyboard-controls.js` is installed once by Zone state setup and contains the only Zone shortcut/modal listener island. Exported legacy Grow/Shrink/Smooth APIs delegate to the same candidate engine; Border and Color Range also compare before actual mask history, so globally callable compatibility paths cannot reintroduce Zone-config history for mask bytes. A successful refine settlement must refresh every visible consumer of the committed mask—the Zone Popout, Zone list, Region status, context actions, overlay, and LIVE PREVIEW—from that same candidate; stale counters are a correctness failure even when the bytes are right. Fast Zone feedback traces the same brush footprint as the committed mask; dedicated Spatial Include/Exclude/Erase explicitly remains round because it exposes no shape control. Layer Transform activation is boolean: refusal clears pending session metadata and callers propagate failure. Pick Item/Transform Selection captures the complete pre-lift stack privately, creates no History or Redo mutation during preview, restores that capture directly on Cancel or activation failure, and publishes exactly one captured-stack action on Apply before the temporary pixels merge back into their source Layer. Layer opacity uses the same transaction principle at gesture scope: SOURCE preview is frame-coalesced, Escape restores privately, and release/Enter/blur publishes one captured stack only when the settled value differs. Visible Layer outline work routes to the transactional, nondestructive Stroke control in Layer Effects; the destructive pixel-bake outline helper is compatibility-only and must not be surfaced as the normal rail command. Zone eyedropper samples are represented as a color stack from the first click, so one sample owns one swatch and one independent Exact↔Loose tolerance control; SOURCE and LIVE PREVIEW share this commit route, duplicate rejection must repaint stale UI without ghost history, and neither this UI/state normalization nor future repairs may alter the owner-frozen pixel-sampling or Spatial Exclude semantics. Layer-selection -> Zone-mask bake uses the committed transform's full alpha raster and one captured Zone undo; it never edits PSD pixels directly. Pointer type and pressure are reset at the input boundary so mouse strokes cannot inherit stale stylus pressure.

Advanced Mask mutations share one post-commit settlement contract: Refine, Invert, Copy, and Mirror must update Zone Popout, Zone list, Region status, context actions, overlay, and LIVE PREVIEW from the same committed bytes exactly once. A correct mask with stale visible counters is still a failed command. Copy Mask target UI is one body-level anchored menu shared by every visible trigger; target selection, Escape, and outside click must all clear its listener and `aria-expanded` state so repeated use is reliable. These UI/settlement rules do not authorize changes to mask math or the owner-frozen Spatial Exclude semantics.

Zone color picking has one target authority: `selectedZoneIndex`. The launch-time armed-picker record and the bottom-bar Zone selector must follow that visible selection; neither may override it during a SOURCE or LIVE PREVIEW commit. Switching Zones while the eyedropper remains armed must immediately repaint the “Pick colors for” label and rebind the pending target. This routing rule does not change color sampling, tolerance math, or Spatial Exclude.

Slider-based Layer adjustments use a private live-preview transaction and must leave SOURCE visually judgeable throughout. At normal editor widths, the shared dialog docks outside the artwork with no backdrop blur or dark veil; each range control has a synchronized exact numeric input honoring the same min/max/step. Slider or numeric movement remains 0 History, Apply publishes exactly one Layer action, and Cancel restores privately. Compact viewports may center the dialog when docking is impossible.

The persistent active-tool options surface is one docked, non-wrapping horizontal rail. Tool changes may change its scroll width but never its height or the SOURCE/LIVE PREVIEW position. Every visible option and context action must remain reachable through native horizontal scrolling, wheel-to-horizontal translation, keyboard focus scrolling, or direct pointer interaction; a rendered control covered by later workspace chrome is a failed tool. The Zone/Layer ownership badge and tool name stay at the leading edge, while tool-specific controls and context actions retain DOM order inside the same rail.

Pointer modifiers have one ownership decision in `js/canvas/dispatch.js`. Alt belongs to selection subtraction for Wand, Select All Color, Smart Region, Grab Object, and Lasso; to source capture for Clone/Healing; and to the active geometry/session for marquee, path, selection-move, Zone-pick, and Layer-move tools. Only tools without an Alt contract may fall through to the temporary eyedropper. This routing rule changes neither eyedropper sampling math nor the owner-frozen Spatial Exclude path.

Extracted Zone Spec Tools cannot call the canvas IIFE's private `triggerPreviewRender`; their only cross-file route is public `window.spbKickLivePreview`. A forced bridge render must clear both the preview dedupe hash and the serialized preview-body memo, and every authored Spec Tool field must participate in `getZoneConfigHash`. Region/spatial RLE dimensions must describe the actual mask length, never merely the current canvas after a source swap. Any client-side spec-image draft must invalidate the server image signature while displayed, restore the exact prior source/signature on Cancel, publish one Zone-config action on Apply, and let Undo/Redo request authoritative server pixels. Point/median sampling and Connected/All Similar selection share one compiled-preview pixel buffer; these tools mutate only Zone configuration or `regionMask`, never PSD Layer pixels.

Late Zone selection tools follow one candidate-first transaction contract. Rectangle, Ellipse, Lasso, Pen Path, and future marquee/path commands must preserve the current `regionMask`, build any Replace/Add/Subtract/feather result privately, compare exact bytes before History, capture undo while the Zone still owns the BEFORE mask, publish the candidate once, and run the canonical full Zone-mask settlement. A duplicate/no-op gesture consumes no History. Undo/Redo must round-trip the exact mask and immediately refresh the Zone Popout, Zone list, Region status, context actions, overlay, and LIVE PREVIEW; a correct mask hidden behind stale counters is still a failed command.

Sampled Zone selections—Magic Wand, Select All Color, Smart Region Fill, and Grab Object—use that same settlement. The committed result count controls apply-area activation: any non-empty result activates `useRegion`, while a subtraction that empties the mask deactivates it immediately. Zone-mask History captures and restores `useRegion` with the mask bytes so Undo/Redo cannot restore only half of the visible/effective selection. This contract changes neither source-color sampling nor the owner-frozen Spatial Exclude behavior.

Gesture feedback is part of selection correctness. Multi-step polygon/path tools must expose their live vertex count after every add/remove and reset it after close/cancel; the persistent hint may not remain at its activation-time value while private gesture state changes. Dismissed global hints remain dismissed.

Visible destructive Layer commands must not use blocking native `prompt()` / `confirm()` UI. `js/canvas/confirm-dialog.js` owns the bounded docked confirmation surface: SOURCE remains judgeable under a 4% veil, the safe action receives initial focus, Escape/outside click cancels, and no History or state mutation occurs before explicit confirmation. The command controller retains mutation/history ownership and must refuse safely if the dialog module is unavailable.

---

## 7. Related Documents

Transform numeric previews must retain the focused input node. Context markup replacement routes through `SPBToolOptionsFocus.setMarkup`; once numeric editing starts, it retains nodes through focus transfers within the bar and defers one latest markup refresh until focus leaves. Nonfocused values and button state still synchronize. Initial activation and Apply/Cancel must replace obsolete controls immediately. Apply/Cancel retain their existing transaction ownership. Do not rebuild the field on every preview and interrupt multi-character typing. Live proof and regression: `docs/TOOLS_SIMPLIFICATION_2026-09-07.md`, `tests/tool_options_focus_contract.cjs`.

Region overlay uploads may crop to the selected region/spatial union through `SPBRegionOverlaySurface`; mask reads remain in native document coordinates and the helper translates only RGBA writes. Clear the previous canvas before each publication, preserve spatial precedence and edge outlines, and retain the full-canvas fallback. Pixel parity is exercised by `tests/region_overlay_surface_contract.cjs`. Rectangle commits reuse the kernel's exact change count unless feathering produced a new candidate; no-op detection and history still precede publication.

Picked Layer transforms capture immutable `origSubRect` through `SPBElementTransformState`; `subRect` is the destination frame. Initialize picked centers as well as dimensions. Numeric setters and pointer movement synchronize the frame; preview and Apply read the immutable source crop. Unchanged Apply closes through the existing cancellation transaction before raster/history mutation. Fit Layer validates both targets, then routes its explicit Layer operation through the canonical dispatcher even when drawing the Zone selection left the toolbar in Zone mode. Neither operation mutates Zone masks. Linked groups use `setMembers/item` for a shared frame and per-member source dimensions in preview and Apply; committed member bounds remain selectable through their link records. Image and stack history capture independent link metadata, and each accepted transform is a separate action. See `tests/element_transform_state_contract.cjs` and the tools report for executed and live evidence.

- `SPB-93` on Linear (single source of truth for the sprint)
- `docs/ARCHITECTURE.md` — high-level Electron + Python + browser overview
- `docs/TOOL_TRUST_MATRIX.md` — current tool capability matrix
- `docs/heenan-family/` — persona definitions (Bockwinkel, Nash, Hall, Pillman, etc.)
- `AGENTS.md` — agent instructions (this document takes precedence for tool work)
- `PRIORITIES.md` / `SPB_LINEAR_HANDOFF.md`

---

Transform previews use session-owned `SPBTransformPreview` canvases and the native Layer stack compositor; never publish temporary pixels into committed layers. Preserve group/clipping/order and virtually settle lifted selections as Apply does. Insert-above-source clipboard layers inherit independent group metadata. Restore source visibility on shared exit; failed compositions must not become valid audit baselines. Contract: `tests/transform_preview_contract.cjs`.

Zone selection frames use `SPBZoneSubPieceTransform`: accept the native inclusive min/max selection API, store immutable selection bounds and material placement separately, and compose the frame into material coordinates at Apply. Isolation alone must not move the material or add Undo. Clear carries pending placement into the ordinary Zone transform; draw/hit-test share the synchronized destination rectangle. Zone masks remain unchanged. Contract: `tests/zone_sub_piece_contract.cjs`.

**This document is now the law for all tool work on SPB-93.**

If you are an agent and you are about to add logic to `paint-booth-3-canvas.js` that touches painting or selection, **stop and re-read this document first**.

Heenan Family Guiding Light — clarity before velocity.


Source-path and PSD import transactions stage retained Zone masks and raw/compressed/batch mask history through `SPBSourceMaskTransition` before resizing the source canvas. Nearest sampling preserves authored mask strengths and spatial states at the same UV footprint. Stage independent objects; failed publication restores the exact prior Zone reference and Undo/Redo records. Never relax the server's source-shape validation or relabel an unscaled mask as the current grid. Direct-file and decoded imports use the same mask transition through `SPBSourceFileCommit`: settle/capture, stage masks, publish pixels, then clear the outgoing PSD. Restore on any failed publication; mark live-source identity only after success. Contract: `tests/source_mask_transition_contract.cjs`.


Every direct FileReader/Image loader shares `_spbSourceLoadGeneration` with normal path/PSD imports. Guard both success and failure callbacks before publishing pixels, metadata or UI errors. URL imports begin before fetch and pass their transaction into file decode; never start a fresh generation after an old fetch completes. Superseded promise imports reject explicitly. Contract: `tests/source_file_generation_contract.cjs`.


Layer pixel commits use `SPBPaintCommitBounds.analyze` for exact alpha restoration, bounds and no-op detection. Row endpoints may replace per-pixel bounds accumulation, but every RGBA channel (including transparent RGB) must still participate in the original-surface comparison. Preserve off-canvas strips and immutable original drawables. Contract: `tests/layer_commit_scan_contract.cjs`.


Ordinary preview settle/retry preparation waits while `isDrawing` is true. No mask hash, export composite or PNG capture belongs on a held brush stroke. Preserve immediate local SOURCE feedback and the explicit interactive material-placement pump. Release/cancel/blur settles drawing through the existing dispatcher, then one fresh preview captures the latest state. Contract: `tests/preview_drawing_settle_contract.cjs`.


Preview PNG preparation awaits `SPBPreviewPngEncoder` using the full-resolution chosen source and existing asynchronous encoder. Guard request version, source generation and paint revision before using the result; attach its immutable URL/signature pair rather than rereading the shared memo. Superseded work must neither overwrite the memo nor finish a newer request. Recheck version after response JSON before adopting server tokens. Keep synchronous full-render/shared attachment callers compatible. Contract: `tests/preview_png_encoder_contract.cjs`.


Off-canvas Layer commits may retain the newly allocated merged canvas directly when surviving bounds exactly cover it. Cropped bounds still require cropping; never reuse the immutable original/history drawable as a mutable work surface. Contract: `tests/layer_merge_reuse_contract.cjs`.


Retouch uploads pass their dirty union into `SPBPaintPreviewRegion`. Union all requests in the same animation frame; any whole-image/initial request requires a full refresh. Clip the existing stack compositor's destination, preserving its blend/group semantics and active source override. Active enabled effects use full repaint. Cancel/commit clears pending region state. Always restore canvas state and keep `paintImageData` pinned to the editable Layer. Contract: `tests/paint_preview_region_contract.cjs`; browser parity control in the opt-in local audit compares full RGBA output outside as well as inside the patch.


A successfully replaced source cannot retain outgoing pixel/Layer Undo or Redo chronology. `SPBSourcePixelHistory` clears flat pixel stacks, removes only pixel/Layer trail and visible History entries, and preserves retained Zone history. Include these arrays and the legacy Color Brush snapshot in source rollback, keeping array aliases and repainting the History panel after restore. Run cleanup only at publication, never at request/decode start. Flat cleanup and PSD publication share the boundary. Contract: `tests/source_pixel_history_contract.cjs`.


Source-mask transitions include spatial/region masks inside retained Zone-config Undo/Redo snapshots, alongside live Zones and brush history. Region-mask history and config history remain separate authorities, but both must match the newly committed source grid. Preserve metadata and array aliases, stage immutable entries, and snapshot both config stacks for failed-publication rollback. Explicitly dimensioned pattern-strength maps remain independent. Contracts: `tests/source_mask_transition_contract.cjs`, `tests/source_pixel_history_contract.cjs`.


When flat-source cleanup requests Layer-link removal, apply it to current Zones and retained Zone-config Undo/Redo snapshots together. `SPBSourceLayerLinks` stages immutable detached entries while preserving masks/settings; splice existing history arrays. Honor the explicit preserve-links option and retain exact old snapshots for failed-publication rollback. Contract: `tests/source_layer_links_contract.cjs`. Layered publication separately rebinds current/config-history restrictions by exact unique hierarchical layer names before replacing `_psdLayers`. Missing/ambiguous identities remain explicit unresolved references; never reuse positional IDs for unrelated artwork. Save/load carries normalized identity metadata; initial legacy documents without metadata retain their historical IDs. Contract: `tests/source_layer_rebind_contract.cjs`.

Startup source dispatch must share the Open Layered format set (PSD/ORA/XCF, case insensitive). Never route those inputs to a flat loader when the layered importer is unavailable. Active/delegated startup contracts: `tests/source_startup_routing_contract.cjs`.

Layer drag scaling uses `SPBLayerTransformScale` and the drag-start frame: opposite edge/corner fixed normally, center fixed with Alt, no cumulative event drift. Preserve scale signs and source rectangle identity. Zone single-scale placement remains separate. Contract: `tests/layer_transform_scale_contract.cjs`; native acceptance is tracked in the tools report.

**Independent Zone instance frame (SPB-93,2026-09-08):** `material-instance-transform.js` resolves v2 IDs and hit-tests rotated independent frames. Move/scale/rotation update only instanceBbox/rotation, with one pre-mutation Zone history entry for changed Apply; Cancel/no-op preserve state. Re-pick scale uses canonical source dimensions, so50% remains50%. Cropped spec ghost supplies local feedback; shared renderer refreshes after Apply/Cancel. Native saved geometry/paint preservation/Undo evidence is in `zone-instance-transform-live-20260908.json`. Source material and Layer pixels are never moved.

**Zone material unlink (SPB-93,2026-09-08):** `material-instance-commands.js` retains v2 records with detached/frozenMaterial; it never removes the rendered copy. `server_routes/zone_material_capture.py` reuses the preview builder/engine without file output, retaining exact native masks before preview resizing. Snapshot format `spb-zone-material/1` stores lossless paint/spec bytes and independent float32 geometry/paint coverage; unowned pixels are zeroed. A matching preview-resolution patch prevents detail changes on unlink. Mutate only after successful capture and unchanged target/config; group capture commits once or not at all. Pending instance frame joins that transaction. Remaining legacy master/appearance handlers are unaccepted.

**Zone master topology (SPB-93,2026-09-08):** `material-instance-masters.js` owns group resolution, Promote and Sync/Re-apply. Source rectangles identify groups; masterId is direct authority, member frozenMaterial is an override. Promotion captures native+preview material and adds one isSource member without moving frames; Sync clears non-master overrides. Unlinking the master reassigns a remaining member in the same history transaction. Renderer and transform ghost resolve the same master snapshot. Conservative source bounds preserve odd-origin preview edges; an unchanged isSource frame aligns to captured source pixels. Moved original-source ownership is now enforced by the mask-stage helper described below.

**Source member ownership (SPB-93,2026-09-08):** `zone_material_ownership.py` releases the canonical source rectangle only when a valid frozen-source member moves/scales/rotates or is hidden. Run before shape/color priority claims and remainder publication, so lower Zones retain their rightful pixels. Unchanged source frames keep existing composition. Never destructively clear stored regionMask or Layer pixels. Detached source members retain ownership; incomplete legacy records cannot erase source pixels. Keep muted isSource metadata in payloads even though the renderer skips drawing that member. Native movement/Undo/reopen and39 material tests cover the corrected underlay.

**Material color actions (SPB-93,2026-09-08):** `engine/zone_material_appearance.py` changes owned paint only, preserves raw spec RGBA and both coverage masks, and matches Layer tool tint/HSL semantics. `MaterialCapture` accepts a bounded ID batch and captures one native/preview pair for the group, resolving explicit master records or a temporary canonical source reference. Never publish the temporary reference. `material-instance-masters.js` verifies the entire group and current selection before a single Undo/mutation; failed/stale/partial capture and spec-only/no-change results are atomic no-ops. Strip operation statistics from persisted snapshots. Replace/Sync/Re-apply remove member overrides and preserve every frame. Native representative actions, exact Undo/reopen and real4096 saved-TGA comparisons now pass.
