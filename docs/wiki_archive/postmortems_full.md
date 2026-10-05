<!-- ARCHIVED FROM SPB_WIKI.html on 2026-07-19. Content verbatim — nothing rewritten, reordered or removed.
     (Double-encoded UTF-8 from an earlier bad save was repaired with ftfy.fix_encoding; no wording changed.)
     The Living Wiki (SPB_WIKI.html) now carries only current/active material.
     Index: SPB_WIKI_ARCHIVE.md at the repo root. -->

# SPB Trouble Log & Post-Mortems — FULL ARCHIVE

## Trouble Log & Post-Mortems

### 2026-07-19 - Shrinking Easy Spec Sculpt library overflowed beneath the install panel

**What happened.** The guided rail rendered its 120 visible look cards inside a flex child with `min-height:0`. Once the new target editor increased rail demand, that child shrank but its card contents still painted outside its box. The later install panel occupied the same pixels. In browser QA an automated click aimed at the visible `Mirror Chrome` card landed on `PUT THIS LOOK IN iRACING`, installing the currently previewed whole-paint job to the configured `dirtlatemodel 438` target (`car_23371.tga`, `car_spec_23371.tga`, `car_spec_23371.mip`, 00:41). Existing one-time `ORIGINAL_*` backups remain in that folder, but the immediately previous 23:58 spec had no new per-write backup and was not blindly restored.

**Root cause.** `.spb-easy-sculpt-library` was allowed to shrink in the scrolling column (`flex-shrink:1`) while its descendants overflowed visibly. DOM ordering was correct; visible hit ownership was not.

**How fixed.** The library is now `flex: 0 0 auto`, so the parent rail owns scrolling and every card retains real layout height. The compact install block is placed before the library. A fresh real-PSD screenshot proves target editor, install block, library header, selected receipt and cards occupy separate vertical bands; subsequent whole-look, sampled-color look and scale interactions completed without any save/deploy state.

**Reusable lesson.** Accessibility snapshots and DOM order do not prove pointer safety. Any scrollable flex rail containing hundreds of controls needs a screenshot/hit-target pass; a child with visible overflow must never be allowed to shrink underneath later destructive actions. Automated UI QA must also keep destructive actions visually isolated, not merely avoid selecting them by label.

---

### 2026-07-18 - Successful Spec Sculpt renders looked inert and a global quest intercepted clicks

**What happened.** In Easy Mode, owners could click a look and see little or no believable change; cards and the original-lab action lower on the screen could also fail to respond.
**Root cause.** The look generator returned valid, different maps, but the customer preview emphasized one generic white lighting sweep and gave no direct proof of the changed material map. Independently, the main-app training quest had a higher global layer and overlapped Spec Sculpt controls, intercepting pointer input outside Spec Sculpt's ownership.
**How fixed.** Spec Sculpt hides the global quest/guide only while its overlay is active, displays the named applied state plus the actual generated iRacing map, and feeds M/R/CC into the visible material-lighting result. The full original lab is now above the library and also reachable from the Easy fork and Electron View menu.
**Reusable lesson.** Do not accept selected-card state or a non-empty canvas as proof that a visual tool works. Browser acceptance must prove an unobstructed hit target, a named result, a changed generated artifact, a perceptible before/after, and access to preserved expert controls.

---

### 2026-07-17 - PSD display names were treated as raster identities, then a broken stack replaced the source

**What happened.** Some PSDs showed their correct flattened livery immediately after import, then became black or empty when the first Layer interaction triggered recomposition.
**Root cause.** The server used full name paths as dictionary keys while the client kept only the immediate parent; deep leaves never matched. Duplicate sibling names overwrote each other. The client nevertheless marked the stack loaded and cleared the known-good composite before drawing leaves with missing images. A separate decode race let the later flat preview temporarily hide this broken state until the first click.
**How fixed.** Import metadata and rasterization now share deterministic positional keys plus full ancestry/inherited visibility. The client awaits the source composite, matches by positional identity, and fidelity-compares the rebuilt stack. Any materially incomplete/black/divergent result fails closed to a locked Source Composite Layer; original leaves remain hidden for recovery. Sequential public Layer IDs remain compatible with saved Zone bindings.
**Reusable lesson.** Never use user-visible Layer names or paths as identity, and never replace an authoritative source image merely because an asynchronous decomposition request completed—validate completeness and pixel fidelity before promotion.

---

### 2026-07-17 - Shape-softness patch first landed in the wrong giant-file branch

**What happened.** The first Pass 107 edit meant for `_paintOnLayerAt` matched a generic `} else` earlier in the 29k-line canvas file and inserted the non-round softness branch inside `liftSelectionToNewLayer`.
**Root cause.** A broad textual patch anchor was not unique enough for a monster file with many nearly identical branch shapes.
**How fixed.** The focused source regression immediately failed; the stray block was removed, the edit was re-anchored on the exact Layer paint function, then `node --check`, clipboard/source-link coverage, the shape-softness fixture, and runtime sync all passed. A targeted search proved only the intended Special and Layer-paint branches remained.
**Reusable lesson.** In `paint-booth-3-canvas.js`, never anchor behavior edits on generic braces/`else`. Include the owning function signature and nearby semantic comment in the patch, then search for the new marker before running wider tests.

---

### 2026-07-15 - Shape helper lost its mouseup endpoint across a JavaScript scope boundary

**What happened.** The pure Shape geometry tests passed, but the first served build rejected every real drag. Mousedown and mousemove appeared active; no layer, toast, or runtime error appeared on release.
**Root cause.** `_resolveShapeGesture` moved to module scope while `getPixelAtClamped` remained a private closure inside `setupCanvasHandlers`. JavaScript `typeof` safely returned `undefined`, so release resolved to `null` without throwing and commit never ran. Early browser probes also used coordinates inside the nominal 205-pixel canvas rectangle but outside its clipped 120-pixel visible pane, obscuring the event path until hit-testing identified the actual paintable intersection.
**How fixed.** Added `_shapeCanvasPointFromEvent`, owned by the Shape lane and based on the real `paintCanvas` rectangle; both primary and legacy Shape routes use it. Cache-busted and retested only points where `elementFromPoint` returned `paintCanvas`. A normal gesture then created exactly one layer and one undo removed it.
**Reusable lesson.** When extracting handlers from a giant closure, inventory every lexical dependency; `typeof missingFunction` can turn a scope regression into a silent no-op. In clipped/zoomed canvas UIs, test the hit-tested visible intersection, not only the child canvas bounding box.

---

### 2026-07-13 - Smart TGA cross-validation leaked through a frozen intermediate selection

**What happened.** The first appearance-veto evaluation appeared to pass spectacularly at 11 true / 1 false, but a stricter audit showed the veto threshold was trained on Cycle732 additions produced by other outer folds.
**Root cause.** Although every appearance prediction was source-content-disjoint, membership in the *training nomination set* was not nested for the current fold. Each old OOF nomination had been selected while some current test labels were available to that old fold's assembly configuration, creating an indirect label path into threshold selection.
**How fixed.** For every outer appearance fold, replay the frozen Cycle732 completeness/certainty heads, raw baseline and assembly config using only that fold's training source groups; select the veto threshold on those inner nominations; then score the untouched outer nominations. Display-rounded raw thresholds were also replaced by deterministic recomputation because an 8-decimal ledger value moved one boundary candidate. The apparent 11/1 result disappeared; handcrafted appearance correctly measured zero movement. The later frozen-pretrained 10/2 pass uses the corrected nesting.
**Reusable lesson.** OOF predictions are not enough: every label-dependent intermediate set used for calibration/thresholding must be regenerated inside the current outer training fold. A frozen artifact can still leak if it was selected under a different fold partition.

---

### 2026-07-11 - SPB default port 59876 blocked by stale HNS/WinNAT exclusion

**What happened.** Fresh Start killed every stale SPB process and loaded the full engine, but backend startup ended with `WinError 10013` while binding `0.0.0.0:59876`; Electron therefore had no backend and appeared not to open.
**Root cause.** Windows HNS/WinNAT virtualization networking had dynamically reserved TCP block `59842-59941`, covering SPB's longstanding `59876`. Docker Desktop's WSL2 distribution was installed/configured but its daemon was inactive; HNS and WinNAT were still running with numerous 100-port active exclusions. `START_SERVER.bat` correctly kept the established port pinned, so SPB surfaced the host reservation instead of silently moving.
**How fixed.** With elevation, shut down WSL, stopped HNS and WinNAT, cleared the exact active allocation, then restarted WinNAT/HNS. The services regenerated their dynamic blocks elsewhere; `59876` disappeared from both IPv4 and IPv6 exclusion tables. Raw binds passed on `127.0.0.1` and `0.0.0.0`; real SPB PID `117392` then listened on `0.0.0.0:59876` and `/api/health` returned 200/status ok. Recovery is captured in `scripts/fix_spb_port_59876_host.ps1`.
**Reusable lesson.** `WinError 10013` with no listener can mean an HNS/WinNAT excluded range, not a firewall or stale app process. Check `netsh interface ipv4/ipv6 show excludedportrange protocol=tcp`; recycle stale virtualization networking before changing an application's established port.

---

### 2026-06-11 — New finishes invisible in picker/search (static JS catalog vs live registry)

**What happened.** After the Spectrum Shift category replacement, the new finishes (e.g. STRESS STORM) didn't appear in the Zone Popout picker, the category lane, or the search bar — even after server restart + hard refresh. Old names/thumbnails kept showing. A few wave2-era finishes had also been invisible.
**Root cause.** The picker/search run off STATIC baked arrays (`paint-booth-0-finish-data.js`: MONOLITHICS + SPECIAL_GROUPS lanes). The runtime server merge in `paint-booth-1-data.js` existed but was neutered (`allowAdd=false`, no pruning, no group sync) — so registry changes NEVER reached the UI. 77 dead ids lingered; 283 live registry finishes had never been listed at all.
**How fixed.** (1) Regenerated the static Spectrum Shift entries (names + descriptions + swatch hexes sampled from the audit renders). (2) `_mergeFinishDataFromServer` now treats `/api/finish-data` `specials` as REGISTRY TRUTH: new monolithics auto-added, dead ids pruned, picker groups whose names match server categories get the server id list. (3) server_v5 boot launches a detached below-normal `rebuild_picker_swatches.py --warm-cache` — swatch cache keys carry the renderer hash, so only new/changed finishes re-bake (verified: changed = 1.3s bake, unchanged = 0.0s skip). Cache tokens bumped (`spb-spectrum-reinvented-20260611`, `spb-registry-sync-20260611`).
**Reusable lesson.** Registry-side registration is NOT enough — the booth UI has static catalog files. Anything that adds/renames/removes finish ids must either ride the runtime registry sync (now default for monolithics) or regenerate the static arrays; and thumbnails only refresh because cache keys embed the renderer hash.

> **Purpose.** Dated, reusable post-mortems of notable defects and false alarms, written in a fixed shape — **What happened / Root cause / How fixed / Lesson** — so future agents recognize the *pattern*, not just the one bug. Each entry ends with a one-line **Reusable lesson**.
>
> **Seed source.** The five entries below are drawn from the 2026-05-29 autonomous "ship-ready" pass and its companion reports: `SHIP_READY_PROGRESS.md`, `SPB_TEST_TRIAGE.md`, `SPB_RUNTIME_BUGHUNT.md` (plus QA color from `docs/TOOL_QA_FINDINGS.md`).
>
> **Standing constraint for every entry.** This pass stayed in **code / infra / tests / catalog-metadata** lanes. **No finish/base/pattern rendered output was changed** — Codex owns the live rebuild. "Finish-neutral" in these entries means *the happy path and rendered pixels are unchanged*; only crash/error/contract behavior moved.

---

### 2026-06-06 — Installer would not BUILD: 32-bit makensis can't mmap an oversized app (TWO stacked ceilings)

**What happened.** `npm run build` / `publish` failed at the final NSIS step: `File: failed creating mmap of ...nsis.7z`. Deterministic (identical hash every retry); a clean `dist/`, a freshly re-downloaded NSIS cache, and a different output folder all failed the same way. The app had grown from ~800 MB to **~3.4 GB**.

**Root cause.** TWO stacked ceilings, not one. **(A)** electron-builder's bundled `makensis.exe` is **32-bit and NOT large-address-aware** (PE Characteristics `0x010F`, ~2 GB virtual-address cap); it memory-maps the compressed app `.7z` to embed it, so a ~2 GB+ payload cannot be mapped. **(B)** GitHub Releases caps a **single asset at 2 GiB** — independent of makensis. So even after fixing (A), a >2 GiB `Setup.exe` can't be auto-updated.

**How fixed.** (1) Cut dead weight — two orphaned PyInstaller bundles shipped at `server/` root (`server.exe` 64 MiB + `shokker-paint-booth-v5.exe` **251 MiB** = ~314 MB) that the app **never launches** (it runs `server/python/python.exe server_v5.py`; the only references are taskkill image-name sweeps). Excluded those + unused Electron locales + python `tests/`/`.pyi`/`pip` + duplicate assets via the `extraResources` filter in `electron-app/package.json` → installer 1.96 GiB → 1.57 GiB. (2) For real growth toward 3.5 GB, switched `win.target` to **`nsis-web`** (a tiny web `Setup.exe` + a separate `*.nsis.7z` hosted on the GitHub release, downloaded at install) — makensis only compiles the stub, sidestepping BOTH ceilings.

**Lesson.** "failed creating mmap" is almost always **app size vs a 32-bit NSIS limit**, not corruption. Before chasing assets/cache: check `makensis.exe`'s LAA bit (PE characteristics), measure the real unpacked size, and hunt for dead bundles. Remember GitHub's 2 GiB/asset cap is a SECOND ceiling.

**Reusable lesson.** Two build ceilings: 32-bit makensis (~2 GB mmap) + GitHub 2 GiB/asset. Trim verified-dead weight first; use `nsis-web` to exceed 2 GB while keeping GitHub auto-update.

---

### 2026-06-06 — Auto-updater pointed at a repo that doesn't exist + a token without write

**What happened.** Every update reference targeted `shokkergroup/ShokkerPaintBooth-Releases`, which returns **404**. The real (owner-confirmed) feed repo is `shokkergroup/ShokkerPaintBooth` (public, 30 releases). After repointing, `npm run publish` then **403'd**: `Resource not accessible by personal access token`.

**Root cause.** (1) A stale runbook invented a separate "-Releases" repo that was never created. (2) The fine-grained token had **Contents: Read-only**. The `GET /repos` field `permissions.push:true` is **misleading for an owner's OWN repo** — it reflects ownership, not the token's granted scope. The release API needs **Contents: Write** (`x-accepted-github-permissions: contents=write`).

**How fixed.** Repointed all four shipping refs (`package.json` `publish.repo`, `update-check.js`, `main.js`, `paint-booth-v2.html`) to `shokkergroup/ShokkerPaintBooth`. Re-issued the token with **Contents: Read and write** and verified it with a **non-destructive write-probe** (`POST /repos/.../releases/generate-notes`) BEFORE the expensive rebuild+upload.

**Reusable lesson.** Don't trust `permissions.push` to prove a fine-grained token can write — probe a real write endpoint (`generate-notes`) first. Confirm the release repo actually EXISTS (exact name/casing) via the API, not a runbook. Feed repo = `shokkergroup/ShokkerPaintBooth`.

---

### 2026-06-06 — Big release-asset upload silently killed by the command timeout (half-published "live but broken" release)

**What happened.** `npm run publish` created the v7.0.1 release and uploaded the tiny web installer, then died (exit 255, **no error message**) partway through the 1.6 GB `.nsis.7z`. Result: a **live release with only the stub and no app package** — the web installer would 404 its payload.

**Root cause.** The 1.6 GB upload exceeded the ~10-minute command timeout, which killed the process mid-stream (real upload errors LOG; a clean cut-off = a kill). Also: nsis-web REQUIRES the release be **published (not draft)** — draft assets aren't publicly downloadable, so the web installer can't fetch the `.7z`.

**How fixed.** Immediately drafted the release (hid the broken state), re-uploaded the `.7z` as a **fully detached process** (survives the wrapper timeout) and polled the API for completion. Set `publish.releaseType: "release"`. Post-publish, verify ALL expected assets are present and complete.

**Reusable lesson.** A long upload that "fails with no error" was probably KILLED by a timeout, not the network — detach + poll for big uploads. nsis-web needs `releaseType:"release"`. Always post-publish-verify the asset set; a half-uploaded live release is worse than none.

---

### 2026-06-06 — Image-based pattern overlays misaligned with the primary (Art Deco vs Hilbert Curve)

**What happened.** Owner: a primary pattern and a 2nd-base "react-to" overlay at the SAME scale/rotation/position **didn't line up** — but only for SOME patterns. The owner's key insight cracked it: image-built patterns (Art Deco Classic) misaligned; procedural patterns (Hilbert Curve) lined up perfectly.

**Root cause.** Confirmed by measurement (FFT xcorr): the overlay mask builder `_get_pattern_mask`'s **image branch** (`engine/compose.py`) had two image-only divergences from the primary image path — (1) it applied the pan offset AFTER masking (rolling the zone window) instead of before, and (2) it never called `_fit_pattern_to_mask_bbox` (fit-to-zone) that the primary applies — so the image tiled full-canvas while the primary was squeezed into the zone bbox. **Procedural patterns tile from a global origin (position-invariant), so they aligned regardless** — which is exactly why three earlier code-only traces (all using procedural stand-ins) couldn't reproduce it.

**How fixed.** In the image branch: copy the pattern, apply offset on the FULL pattern BEFORE masking, honor a new `fit_zone` param via `_fit_pattern_to_mask_bbox`, then mask — mirroring the primary path. Threaded `fit_zone` through `_get_overlay_pattern_mask` and passed the primary's `pattern_fit_zone` at all **12** overlay call sites. That fixed **scale 1.0** (xcorr 0.30 → 0.98)... but the owner re-tested at **scale 0.20 and it was STILL off (xcorr 0.80)**. **Deeper cause (the real one):** the overlay mask used a DIFFERENT image loader (`_load_image_pattern`, with its own resize + coverage/POP hardening) than the primary visible path (`_load_color_image_pattern` → alpha). At scale 1.0 the two nearly matched; once the image **tiles at fractional scale** the resize+coverage differences compound and the overlay drifts (best-align shift was (0,0) — i.e. a *content/processing* divergence, not a phase offset). **Final fix:** build the overlay mask from `_load_color_image_pattern`'s ALPHA — the exact same loader/derivation the primary uses — then offset-before-mask + fit_zone. Result: **xcorr 1.000 at ALL scales** (1.0 and 0.20, fit_zone on/off); procedural unchanged.

**Lesson.** "Right size, wrong position" is a PLACEMENT divergence, not a scale bug — and image vs procedural assets take DIFFERENT placement code. TWO traps stacked here: (1) offset-order/fit-to-zone, and (2) the overlay and primary used DIFFERENT image loaders. A fix that measures aligned at one scale (1.0) can still fail where the image TILES (0.20) — always re-verify at multiple scales. The owner's "image vs procedural" hint + a 0.20 re-test cracked what scale-1.0 measurements hid.

**Reusable lesson.** Keep the OVERLAY and PRIMARY on the SAME image loader/derivation (here `_load_color_image_pattern` alpha) AND the same offset-order + fit-to-zone. Verify alignment at MULTIPLE scales (1.0 AND ~0.20), because divergences only surface once the image tiles at fractional scale.

---

### 2026-06-06 — Three more render bugs + the process gotchas that slowed the hunt

**What happened.** Alongside the alignment bug, the owner hit: (a) a Solid overlay color did nothing on a **monolithic** 2nd-base; (b) **numbers/sponsors turned solid WHITE** under a 2nd-base overlay; (c) ~200 patterns showed **gray-on-gray** in the picker dropdown.

**Root cause + fix.**
- **Overlay color ignored** — the inline-mono path (`shokker_engine_v2.py:18103`) promoted the mono to its OWN color renderer without checking `second_base_color_source`, so "Solid"/"From base" were skipped. Fix: add the source guard the sibling base branch already had (`... in ("","overlay")`).
- **White numbers/sponsors** — a 2nd-base overlay white-seeds RGB across the WHOLE zone mask incl. decal pixels (`compose.py compose_paint_mod*`). Fix: after the zone loop, restore decal RGB from the original composite, gated by the client's `decal_mask_base64` (`shokker_engine_v2.py`).
- **Gray picker dropdown** — the picker requests `color=888888`; the earlier override-tile patch only ever covered ~210 of 410 patterns. Fix: colorize neutral requests in `_render_picker_split_snapshot_bytes` via `_swatch_display_color` (the non-split swatch path already did this).

**Process lessons (these cost real time — heed them).**
- **Adversarial verification earns its keep.** Two "fixes" passed a first agent but FAILED a skeptical second pass that REPRODUCED with measurement (one targeted the engine when the engine was already correct; one patched the spec channel, not the visible render path). Never ship a fix you haven't measured against the real symptom.
- **When a recurring bug resists fixes, question the REPRO, not just the code.** The engine measured correct twice; the actual bug only surfaced with the owner's exact asset (image pattern) + screenshot.
- **PowerShell path-guard** blocks `Remove-Item` on root-level paths (`C:\spbbuild`) and `Env:` drives — use Bash `rm` for cleanup. **`node` stderr (even warnings) makes PowerShell report exit 255 on success** — verify by inspecting the actual artifact, not the exit code.
- After ANY engine edit: **edit root → `node scripts/sync-runtime-copies.js --write` → purge `__pycache__` → restart `server_v5.py`**, or the change silently doesn't load (3 copies + stale `.pyc`).

**Reusable lesson.** Fix at the shared chokepoint, mirror guards a sibling branch already has, and ALWAYS adversarially re-verify a fix by reproducing the symptom with a measurement. A fix that isn't measured against the real symptom is a guess.

---

### 2026-06-05 — Per-element transform ROTATE+Apply clipped the element (owner's #1 "doesn't half work")

**What happened.** Owner: the per-element layer transform "doesn't half work" despite prior testing. Live repro: PICK ITEM -> isolate a layer -> rotate **+90deg** -> **Apply**. The on-canvas PREVIEW rotated correctly, but the committed BAKE **clipped** the element: a 602x402 rect rotated 90deg + Apply produced an img still **602x402** (not the expected ~402x602), with the rotated content clipped to a 402x402 region (corners/ends lost). Prior "rotate works" tests passed because they checked the PREVIEW, not the committed pixels.

**Root cause.** `commitLayerTransform()` whole-layer commit branch (`paint-booth-3-canvas.js` ~L21325) sized the destination canvas to the ORIGINAL box (`newW x newH`) and drew the rotated content into it -- so anything past the original axis-aligned box was clipped. `boxW`/`boxH` are never grown on rotation (the +90deg preset / drag-rotate only set `s.rotation`); only resize-drag writes a grown size to boxW/boxH (which is why scale-up was already safe). Isolated elements (selxform layer, `subRect=null`) take this whole-layer branch.

**How fixed.** Size the destination canvas to the transformed **AABB** (`newW*|cos|+newH*|sin|` by `newW*|sin|+newH*|cos|`), draw the content centered, set bbox to that AABB centered on the unchanged transform center. At `rotation===0` the AABB === `newW x newH` and `bx1===newX1`/`by1===newY1` (provable identity) -> move/scale/flip commits are byte-for-byte unchanged; only rotation grows. 3-copy synced, cache-buster `spb-rotate-apply-aabb-20260605n`, reloaded, **verified live**: 602x402 rect +90deg Apply -> img **407x606** (grown AABB), bbox [347,147,754,753], edge sample **"MMM"** (fully filled, no clip).

**Lesson.** A PREVIEW that looks right does NOT prove the COMMIT is right. This "tested, still broken" class lives in the gap between the live transform preview (full rotated element drawn on an unclipped canvas ctx) and the bake (rasterized into a fixed-size destination). When verifying any tool that has a preview + a commit, **measure the committed artifact** (layer `img` dims, `bbox`, pixel sample), not just the on-screen preview.

**Reusable lesson.** Preview != bake -- verify the committed pixels/geometry, not the preview; and when rasterizing a transformed element, size the destination to the transformed **AABB**, never the source box.

---

### 2026-05-29 — `depth_*` / `halo_*` MONO `spec_fn` crash at small sizes

**What happened.** `test_all_monolithic_spec_fns_work_at_64x64` failed: 19 `depth_*` (and then 11 `halo_*`) MONOLITHIC `spec_fn`s crashed when rendered below 96 px (e.g. at 64×64). Production never hit it — production always renders at ≥256 — so it was invisible until a small-size test exercised the path.

**Root cause.** Two layered defects in the small-size path:
- A **shape-unpack / reconcile bug** in `engine/fusions.py`: the mask-resize was gated on a downscale condition (`ds > 1`) only, so when the internal *work shape* differed from the *input shape* for any other reason, the mask was never reconciled to the working resolution — `_depth_work_shape` unpacked wrong and downstream array math blew up. (Triage S/`spec_misc` recorded the same class: "mask resize gated on `ds>1` only … resize the mask whenever work-shape ≠ input.")
- More broadly, the **monolithic-contract wrapper** in `engine/shokker_engine_v2.py` had no fallback for a factory that throws on this otherwise-crashing path, so *every* current and future `depth_*`/`halo_*`-style factory was one small-size call away from the same crash.

**How fixed.** Two-level fix:
1. Corrected the `_depth_work_shape` unpack and the `(work ≠ out)` reconcile in `fusions.py` so the mask resizes whenever the work shape differs from the input shape (not only on downscale). Synced to all 3 runtime copies.
2. Added a **systemic fallback in the monolithic-contract wrapper** (`shokker_engine_v2.py`) that triggers *only on the otherwise-crashing path* — hardening every present and future factory against this class, not just the 19+11 known ones.

Result: `test_all_monolithic_spec_fns_work_at_64x64` passes. Finish-neutral (production renders ≥256, where the path was never taken).

**Lesson.** When a whole *family* of factories shares one contract entry point, fix the bug at the instance **and** add a guard/fallback at the **shared wrapper** — that converts "19 found" into "this entire class can't recur." Also: a resize/reconcile gated on one narrow condition (`ds>1`) is a latent crash for every *other* reason the shapes can diverge; gate on the actual invariant (`work-shape ≠ input-shape`).

---

### 2026-05-29 — Spec-overlay regroup (9 moved, empty duplicate group removed)

**What happened.** The 149 spec overlays were audited against the canonical 22-group taxonomy and found mis-grouped: several overlays sat in the wrong category, there was an **empty duplicate "Carbon & Composite" group**, and `SPEC_PATTERN_GROUP_ORDER` was stale (did not list all 22 groups).

**Root cause.** Catalog-metadata drift accumulated as overlays were added/renamed over time — group assignments and the group-order array were edited piecemeal and fell out of sync with the taxonomy. A duplicate group had been created and then emptied, leaving a blank tile; the order array was never rebuilt to match the real group set.

**How fixed.** Reviewed all 149 overlays vs the 22-group taxonomy and **moved 9 misplaced ones** (e.g. `anodized_rainbow`→Optical, `voronoi_fracture`→Structure, `spec_carbon_weave`→Carbon Weave, `salt_spray_corrosion`→Weather, `aniso_grain` / `sparkle_shattered`→Mechanical). **Dropped the empty duplicate "Carbon & Composite" group**, rebuilt `SPEC_PATTERN_GROUP_ORDER` to all 22 groups, and cleaned the purge cruft. Verified the **invariant held — 149 ids in, 149 ids out** — JS valid, **synced to all 3 copies with "no drift."** Plan: `SPB_SPEC_OVERLAY_REGROUP.md`. This is metadata only — no overlay's render changed.

**Lesson.** For pure catalog/metadata reorganizations, assert a **conservation invariant** (count in == count out; same id set) before and after — it catches an accidental drop/dupe instantly. Treat the human-readable **group-order array as derived state** that must be rebuilt from the taxonomy, not hand-patched, or it silently desyncs and produces blank/duplicate tiles.

---

### 2026-05-29 — FALSE ALARM: "zone popout broken — can't scroll past Base"

**What happened.** A report came in that the **zone popout panel was broken** — you supposedly "couldn't scroll past Base." Initial fix attempts appeared to do **nothing** in the running app, which made it look like a stubborn real bug.

**Root cause (two compounding factors).**
1. **Not actually broken.** The popout simply **required a base to be selected first**; with no base selected the panel was in the expected empty/initial state, which *looked* like "stuck on Base." This mirrors the broader QA lesson that several zone tools are **state-conditional, not global** — e.g. the zone-editor float (`zoneEditorFloat` / `.zone-editor-float`) only manifests when a zone is selected (`docs/TOOL_QA_FINDINGS.md` Run #27/#28), and Color Replace targets the *selected layer*, not everything (Run #37). The precondition, not the code, was the issue.
2. **CSS cache tokens masked the verification.** In this codebase every asset is loaded with a `?v=` **cache-buster token** and fixes are synced to all 3–6 runtime copies; a fix only reaches the browser when its token is bumped (the QA log is full of `cache-buster spb-…-20260529; sync N/N; reload` ceremony, and `FRONT-03` flags that some `<script>`/CSS tags are *unversioned*). Because the CSS token wasn't bumped (or the wrong copy was edited), the browser kept serving the **stale stylesheet**, so each fix attempt "did nothing" — making a non-bug look real *and* unfixable.

**How fixed.** No code fix was needed for the popout itself — selecting a base resolved the reported symptom. The "fix did nothing" confound was resolved by recognizing the **cache-token / multi-copy sync** mechanism: bump the `?v=` token (and sync the edited file to all runtime copies) before judging whether a change had any effect.

**Lesson.** Two reusable rules. **(a)** Before filing a UI defect, confirm the **preconditions/selected-state** — many tools here are state-conditional (need a zone/base/layer selected); an empty initial state is not a bug. **(b)** On a no-build, token-cache-busted, multi-copy frontend, an edit that "changes nothing" is usually **stale cache or the wrong copy**, not a wrong edit — *always* bump the `?v=` token and sync all copies, then hard-reload, before concluding the fix failed.

---

### 2026-05-29 — Runtime bug-hunt: 42 found, ~28 fixed (incl. the render-lock)

**What happened.** A read-only hunt of the **Codex-free runtime** (Flask server, `server_routes/`, scripts, Electron, frontend plumbing) surfaced **42 concrete, finish-neutral bugs**, including **2 confirmed high-severity** defects. **~28 of 42 were fixed, verified, and synced** in this pass; the remaining 14 are the documented "needs care" set. Full ledger: `SPB_RUNTIME_BUGHUNT.md`.

**Root cause (recurring classes).** The 42 collapsed into a handful of patterns:
- **Lock-ownership / concurrency** — most importantly **`SERVERCORE-1`** (the *render-lock* bug): `/render` **force-`release()`s a `threading.Lock` it does not own** on acquire-timeout (compounded by an unconditional `finally` release). Two concurrent renders then race shared, unlocked engine caches (`build_multi_zone._zone_cache`, `_prev_spec_cache`) → **garbled/corrupted output, `KeyError`, or crash**. It is the *only* confirmed defect that can produce *wrong rendered pixels* (not just a hang/500).
- **Missing input validation / type coercion** — non-numeric `size`/`seed`/`width` params returning 500 instead of 400; `'24' > 0` TypeErrors; non-string id/name on custom-finish save/delete.
- **Missing contract/null guards** — finish-viewer mono passing `spec=None` or mishandling 2-D grayscale; `doRender` deref of `barInner` masking a *successful* render; unguarded `JSON.parse` of localStorage.
- **No fetch timeouts** — hung server freezing the UI on "Rendering…/Generating…" with buttons stuck disabled.
- **Startup/lifecycle** — **`ELECTRON-2`**: startup **never rejects on server `exit`** and **resolves "ready" on an alive-but-portless process**, so the app can load against a dead/wedged engine.
- **Script/worker resilience & dead code** — overnight worker stuck re-entering a dead portal, crashing on partial JSON; cwd-dependent `spb_context.js`; dead preload channels and stale build scripts.

**How fixed.** Applied the **entire "trivially safe" category** — local, happy-path-preserving guards: `safe_int`/coercion on route params, `None`/2-D guards in the finish viewer, `/cleanup` coercion, mixer 2–3-finish bound, OneDrive folder-scan precedence parenthesization, deploy array-guard, `AbortSignal.timeout` across preview/upload/boot/mixer fetches, localStorage `try/catch`, temp-dir `try/finally` cleanup, concurrent-delete-safe mtime sort, workbook + overnight-worker `try/except` hardening, dead-channel/stale-script removal, `__dirname` anchoring. Each was **verified and synced to all copies**.

The **two confirmed high-severity bugs were deliberately left for a supervised pass** (verify by running the app), because they touch the render lock and app-startup orchestration:
- `SERVERCORE-1`: the safe fix is *never release a lock you may not hold* — on timeout return `429 render_busy`, track a local `have_lock`, and guard every `finally` release on it.
- `ELECTRON-2`: on `exit` before ready, clear the poll interval + the 60s timer and **reject** so retry advances; on the timeout branch, reject (not `resolve(port)`) when the process is merely alive.

A LAN-exposure posture item (`SERVERCORE-5`: default-bind `0.0.0.0` + wide-open CORS with the `/render` license gate commented out) was flagged for an owner decision.

**Lesson.** Triage by **class, not by count** — the 42 are ~6 recurring patterns (lock-ownership, input validation, contract guards, timeouts, lifecycle, resilience), and naming the class makes the fixes systematic and the long tail mechanical. **Separate "trivially safe" from "needs care":** ship the local guards immediately, but anything touching a **lock, app startup, or a security boundary** must be verified by *running the app*, not by reading the diff. And the single highest-value rule it reaffirmed: **never `release()` a lock you might not hold** — a force-release on timeout silently destroys mutual exclusion and is the one runtime bug here that can corrupt rendered output.

---

### Cross-cutting lessons (index)

| # | Reusable lesson | Anchored by |
|---|---|---|
| L1 | Fix a *family* bug at the **shared wrapper/contract**, not just each instance — turns "N found" into "this class can't recur." | `depth_*`/`halo_*` MONO |
| L2 | Gate a resize/reconcile on the **real invariant** (`work-shape ≠ input-shape`), not a narrow proxy (`ds>1`). | `depth_*` mask resize |
| L3 | For metadata reorgs, assert a **conservation invariant** (same id set in/out) before/after. | Spec-overlay regroup |
| L4 | UI tools here are **state-conditional** (need a zone/base/layer selected) — an empty initial state is not a bug. | Zone-popout false alarm |
| L5 | On the no-build, `?v=`-cache-busted, multi-copy frontend, a "fix that did nothing" is usually **stale cache / wrong copy** — bump the token + sync all copies + hard-reload before judging. | Zone-popout false alarm |
| L6 | **Never `release()` a lock you may not hold**; on timeout, return busy and guard `finally` on a local `have_lock`. | `SERVERCORE-1` render-lock |
| L7 | Split **trivially-safe guards** (ship now) from **needs-care** lock/startup/security changes (verify by running the app). | Runtime bug-hunt |
| L8 | Lifecycle/startup must **reject on failure** and verify the **port is actually open**, not just that the process is alive. | `ELECTRON-2` |

---

> **Provenance / accuracy note.** Entries 1, 2, 4, and 5 are taken directly from `SHIP_READY_PROGRESS.md`, `SPB_TEST_TRIAGE.md`, and `SPB_RUNTIME_BUGHUNT.md`. For entry 3 (the "can't scroll past Base" false alarm), the *narrative* — needing a base selected, compounded by CSS cache tokens making fixes appear to do nothing — is reconstructed from the user's account; the named three docs do **not** contain that verbatim incident. It is grounded in two documented, stable mechanisms in this repo: (a) the pervasive `?v=` **cache-buster + multi-copy sync** convention (`docs/TOOL_QA_FINDINGS.md`, `FRONT-03` in `SPB_ALPHA_AUDIT.md`), and (b) the **state-conditional** zone-popout/`zoneEditorFloat` behavior (`docs/TOOL_QA_FINDINGS.md` Run #27/#28). If a dedicated incident log for it exists elsewhere, it should be linked here.
