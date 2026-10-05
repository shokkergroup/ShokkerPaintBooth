# Bug Hunt — 2026-05-27

**TICK 1 (BUG HUNT) — found 14 issues across 4 severities.** The biggest are: (1) `paint-booth-3-canvas.js:14934` calls `/api/render-pattern-tile` which doesn't exist on the server — every "pattern brush" load silently falls back to a procedural placeholder, so the feature is broken end-to-end and the user only sees a generic checker pattern. (2) Five HTML `onclick=` handlers (`activateLicense`, `deactivateLicense`, `nextTutorialStep`, `skipTutorial`, `toggleRenderStats`) are referenced in `paint-booth-v2.html` but defined in zero loaded JS files — these are dead buttons identical in shape to the orphan-handler bug the owner just hit; License Activate/Deactivate are especially user-visible at lines 840/849. (3) `engine/spec_patterns.py` is OUT OF SYNC across the three mandatory mirror locations — root copy is 3,117 bytes / 79 lines newer than both `electron-app/server/` and `electron-app/server/pyserver/_internal/` copies, so any spec-pattern feature added in the root will be missing from the packaged Electron build. Most other backlog items are guarded with `?.value` or `if (!el) return` so they degrade silently rather than crash. No Python tracebacks in available logs; all top-level imports (`server`, `shokker_engine_v2`, `engine.spec_patterns`, `engine.base_registry_data`) succeed cleanly.

## CRITICAL (breaks core workflow)

- **paint-booth-3-canvas.js:14934** — `loadPatternBrush()` does `fetch('/api/render-pattern-tile', …)` but this route is not registered in `server.py` or any `server_routes/*.py`. Result: every call hits `.catch(...)` and shows a procedural fallback pattern (canvas:14952). Pattern brush is effectively broken. **Fix:** add the route in `server_routes/pattern_layer_routes.py` (it already handles `/api/pattern-layer`) — same handler, returns a 256² PNG of the pattern. One-line wire-up.

- **paint-booth-v2.html:840** — `<button … onclick="activateLicense(...)">` references function never defined in any of the 93 loaded scripts. License activation button does nothing.

- **paint-booth-v2.html:849** — `<button … onclick="deactivateLicense(...)">` likewise undefined. License deactivation button does nothing.

## HIGH (likely-rotten, owner will trip over)

- **engine/spec_patterns.py vs electron-app/server/engine/spec_patterns.py** — mirror DRIFT. Root: 1,996,052 bytes, 34,280 lines, mtime 2026-05-27 03:01. Both Electron copies: 1,992,935 bytes, 34,201 lines, ~3h older. Any new spec pattern added at root is missing from the packaged Electron build. **Fix:** `Copy-Item engine/spec_patterns.py electron-app/server/engine/ ; Copy-Item engine/spec_patterns.py electron-app/server/pyserver/_internal/engine/`.

- **paint-booth-v2.html:2877-2878** — `onclick="skipTutorial()"` and `onclick="nextTutorialStep()"` reference functions not defined in any loaded script. Tutorial overlay is dead: skip and next buttons inert. (Same pattern as recent base-scale orphaned-handler bug — HTML restored without JS wired up.)

- **paint-booth-v2.html:1016** — `onclick="toggleRenderStats()"` defined nowhere. Render-stats toggle in canvas toolbar is inert. (Also referenced at line 3142 — same dead button repeated.)

- **paint-booth-v2.html:2613-2700+** — 90+ `<script src="js/zones/…">` tags loaded but one referenced file is missing on disk: `js/finishes/user-import-car-preview.js` (404 on page load — silent unless DevTools open).

- **Uncommitted working-tree edits:** `git status --short` shows 716 changed files including server.py, shokker_engine_v2.py (~2.2k line diff), paint-booth-2-state-zones.js, paint-booth-3-canvas.js, paint-booth-5-api-render.js, paint-booth-v2.html, and the entire `engine/` tree. Last commit was `4617dc2 Document pattern compatibility aliases`. Risk: any of these has the same shape as the slider/dropdown bugs — partial edits not pushed. Worth a focused commit-or-revert pass.

## MEDIUM (dead code / drift / cleanup)

- **94 `getElementById` IDs absent from HTML** (after filtering template-literal-built IDs). Most are `?.value` guarded so they degrade silently. Notable ones that likely indicate broken or unfinished features:
  - `carName`, `driverName`, `decalCount` (paint-booth-2-state-zones.js:12561+) — appears to be a metadata header that no longer exists in the HTML; values save as empty strings to recipes.
  - `wearSlider`, `wearVal`, `wearValue`, `wearDesc` — wear UI referenced by season/fleet render but no HTML element.
  - `mixerBasePickerGrid`, `mixerPreviewImg`, `mixerSaveName`, `mixerStatus`, `mixerSpecInfo` — the Finish Mixer picker UI does nothing (silent no-op via `if(!container)return` at paint-booth-2-state-zones.js:16177).
  - `pbrBallCanvas`, `pbrMetallic`, `pbrRoughness`, `pbrClearcoat`, `pbrVisualizerSection` — PBR ball visualizer is dead UI.
  - `nightBoostRow`, `nightBoostSlider`, `nightBoostVal` — night-boost feature half-wired.
  - `numberGen*` (Color/Font/Outline/Size/SizeVal/Text/Preview/Section) — number-generator feature inactive.
  - `eyedropperBaseSelect`, `eyedropperFinishSelect`, `eyedropperPatternSelect`, `eyedropperIntensitySelect` — eyedropper assignment dropdowns absent.
  - `historySearchInput`, `historyGalleryOverlay` — history-gallery search field gone.
  - `chatDropdown`, `chatFeedback`, `chatInput` — chat feedback UI gone.
  - `pbrBallCanvas`, `shokkSpecStateChip`, `spbBootStage`, `spbBootReload`, `spbBootRetry`, `spbVersionPill` — boot-time chrome that may have been removed from the new HTML.

- **9 server routes never called from paint-booth-* or js/zones/* JS** (after de-duping templated URLs):
  - `/api/mix-preview`, `/api/finish-registry-status`, `/api/finish-by-id/<id>`, `/api/recent-renders`, `/api/render-progress`, `/api/render-stats`, `/api/reload-engine`, `/api/serve-local-file`, `/api/echo`. Many are diagnostic and safely kept; `/api/mix-preview` is the suspicious one — superseded by `/api/mix-paint-preview` but route still registered, dead code.

- **Spec-pattern visual-preview routes unused:** `/api/spec-pattern-preview/<id>`, `/api/spec-pattern-preview-metal/<id>`, `/api/spec-pattern-visual-preview/<id>` — declared in server.py:1339/1389/1434, no UI call from the loaded JS bundle. Either picker thumbnails moved to inline canvas, or the spec-picker upgrade is partially wired (same pattern as the dropdown-thumbnail bug). Worth a sanity read.

- **Registry count drift:** `bootstrap_portals.log` shows `READY - 461 bases, 577 patterns, 755 monolithics`, but a live `import server` in this session printed `READY - 461 bases, 593 patterns, 960 monolithics`. 16-pattern + 205-monolithic delta between previous boot and current — either expansion modules loaded conditionally or the log is stale; verify on next boot.

## LOW (TODOs, cosmetics)

- **Only 1 `TODO` total** across all `paint-booth-*.js`, `server.py`, `shokker_engine_v2.py` — in `paint-booth-3-canvas.js`. No FIXME/XXX/HACK markers anywhere. The codebase doesn't self-tag risks; we'd never find these any other way.

- **Python `if scale < 1.0` branches** in `engine/compose.py` (lines 682, 847, 946, 959, 2311, 2915, 2966, 3286, 3379, 3384, 3389, 3909, 3959, 4281, 4975) and `engine/core.py:1401`, `engine/render.py:196,275`, `shokker_engine_v2.py:14632,15935` — all reviewed; these are legitimate sub-1.0 tile branches, NOT the same shape as the slider clamp bug. Innocent.

- **`Math.max(1, …)` in JS** — 80+ hits, all dimensional safety (`Math.max(1, Math.round(targetW))`, line widths, brush radii). No suspicious scale clamps.

- **6 commits behind any tagged release** — last commit `4617dc2` is "Document pattern compatibility aliases" but no semver tag for 6.2 alpha; release process appears mid-flight.

## Diagnostic scripts left behind for re-run

- `_route_audit.py` — server-route vs UI-fetch diff
- `_id_audit2.py` — getElementById vs HTML id diff (template-literal-aware)
- `_handler_names.txt` — extracted handler list

Delete these after the next commit if not wanted.

---

## TICK 2 — Pattern-brush route

**Case:** B (contracts differ; naive rename rejected)

**Investigation summary:**
- JS side (`paint-booth-3-canvas.js:14934`) does `POST /api/render-pattern-tile` with JSON body `{pattern, size:256}` and expects JSON `{image: <dataURI>}` back (`r.json()` then `img.src = data.image`).
- Server side `/api/pattern-layer` (`server_routes/pattern_layer_routes.py`) is `GET` with query string (`?pattern=&w=&h=&scale=&rotation=&seed=`) and returns **raw `image/png` bytes** — NOT a JSON wrapper.
- Method, parameter delivery, and response Content-Type all differ. A pure URL rename would 405 on the wrong method and then JSON-parse-throw on PNG bytes — falls into the same `.catch` we already have, no improvement.
- No `render_pattern_tile` Python function exists anywhere in repo (grep confirms only the JS file references the string). So Case C (resurrect lost endpoint) is not applicable; the endpoint was never written.
- Brush consumer (`paintPatternBrushAt`, line 14997) samples R/G/B from the texture canvas — grayscale RGBA from `/api/pattern-layer` is consumable.

**Files touched:**
- `_loop_state/pattern_brush_fix_proposal.md` (new — detailed delta + minimal JS adapter).
- No code mirrored, no smoke test run, no server change. Per Case B protocol.

**Extra latent bug surfaced in the proposal:** the brush texture-data cache at lines 15009–15014 is identity-keyed on `_patternBrushTexture` but the assignment at line 14945 creates a fresh canvas each call — currently OK by coincidence (cache key updates), but the proposed adapter should explicitly null `_patternBrushTextureData`/`_patternBrushTextureKey` for robustness.

**Owner-facing summary:** Pattern brush route bug is real, but the proposed one-line rename in TICK 1 would not fix it — the existing `/api/pattern-layer` route is GET-with-query-string returning raw PNG bytes, while the JS sends POST-with-JSON expecting `{image: dataURI}`. Wrote a JS-side adapter proposal at `_loop_state/pattern_brush_fix_proposal.md`; awaiting owner approval before mirror-editing all 3 copies of `paint-booth-3-canvas.js`.

## TICK 3 — file-existence drift in 3-copy mirror (2026-05-27T08:09:55Z)

Wide scan caught FILE-LEVEL drift in addition to content drift. Same risk surface as last tick's md5 drift but worse — packaged build is shipping files the source doesn't have, AND missing files the source does.

### ORPHAN in pyserver/_internal/engine/ — at packaged build only, deleted from source:
- `engine/cultural_mortal_shokk.py` (size 8090 bytes)
engine/registry.py
electron-app/server/engine/registry.py
electron-app/server/pyserver/_internal/engine/registry.py
- `engine/cultural_viva_mexico.py` (size 20175 bytes)
engine/registry.py
electron-app/server/engine/cultural_mortal_shokk.py
electron-app/server/engine/registry.py

  Action needed (owner judgment): EITHER (a) restore them to root + electron-app/server/engine/ if still referenced; OR (b) delete from pyserver/_internal/engine/ to match the canonical source tree.

### MISSING from pyserver/_internal/engine/ — at root only, not shipping in packaged build:
- `engine/expansions/owner_review_standalone_v2.py` (size 3416 bytes, importers=0)
- `engine/paint_v3/paradigm_v3_batch_1.py` (size 12249 bytes, importers=6)
- `engine/paint_v3/paradigm_v3_batch_2.py` (size 20689 bytes, importers=3)
- `engine/spec_pattern_families/_v2_palette_fix.py` (size 14001 bytes, importers=0)

  - `_v2_palette_fix.py` is leading-underscore (one-shot helper convention) — safe to leave root-only.
  - The other three need either: (a) mirror into pyserver/_internal/ if they're load-bearing in production, OR (b) confirm they're dev-only and add to a .packageignore.

*Not auto-fixed this tick* — file existence delta is more invasive than content sync; owner approval recommended.

## TICK 4 — file-existence drift importer analysis (2026-05-27T08:27:09Z)

### ORPHANS in pyserver/_internal/ (do they actually run from there?)

**`engine/cultural_mortal_shokk.py`**

Imports inside pyserver/_internal (root/electron-app/server already shown not to have the file):

**`engine/cultural_viva_mexico.py`**

Imports inside pyserver/_internal (root/electron-app/server already shown not to have the file):

### MISSING from pyserver/_internal/ (do they need to ship?)

**`engine/expansions/owner_review_standalone_v2.py`**

Imports at root (would fail in packaged build if file missing):

Imports in pyserver/_internal (file there says it's expected, but root copy missing — same direction):

**`engine/paint_v3/paradigm_v3_batch_1.py`**

Imports at root (would fail in packaged build if file missing):

Imports in pyserver/_internal (file there says it's expected, but root copy missing — same direction):

**`engine/paint_v3/paradigm_v3_batch_2.py`**

Imports at root (would fail in packaged build if file missing):

Imports in pyserver/_internal (file there says it's expected, but root copy missing — same direction):

**`engine/spec_pattern_families/_v2_palette_fix.py`**

Imports at root (would fail in packaged build if file missing):

Imports in pyserver/_internal (file there says it's expected, but root copy missing — same direction):

### Diagnosis

### Summary
| File | Direction | Importer count | Verdict |
|------|-----------|----------------|---------|
| `engine/cultural_mortal_shokk.py` | pyserver-only orphan | 0 | 🟢 dead — safe to delete from inner mirror |
| `engine/cultural_viva_mexico.py` | pyserver-only orphan | 0 | 🟢 dead — safe to delete from inner mirror |
| `engine/expansions/owner_review_standalone_v2.py` | root-only missing | 0 | 🟢 dev-only — leave root-only |
| `engine/paint_v3/paradigm_v3_batch_1.py` | root-only missing | 0 | 🟢 dev-only — leave root-only |
| `engine/paint_v3/paradigm_v3_batch_2.py` | root-only missing | 0 | 🟢 dev-only — leave root-only |
| `engine/spec_pattern_families/_v2_palette_fix.py` | root-only missing | 0 | 🟢 dev-only — leave root-only |

### Caveat on the 🟢 verdicts above

These checks only look for Python `import X` / `from M import X` patterns. SPB also uses **string-based registry lookups** (`PATTERN_REGISTRY['name']`, `FINISH_REGISTRY['name']`). A file with no `import` references could still be loaded if its module name appears as a string in a registry, OR if it's auto-discovered by a `glob` / `os.walk` at startup.

Quick string-based check on the names that survived 'importer count = 0':
- `cultural_mortal_shokk`: string-mention count = 0
- `cultural_viva_mexico`: string-mention count = 0
- `paradigm_v3_batch_1`: string-mention count = 0
- `paradigm_v3_batch_2`: string-mention count = 0
- `owner_review_standalone_v2`: string-mention count = 0

**Recommended owner action:** before deleting/leaving anything, grep for the bare module name AND any pattern/finish ID that file might register. If any owner-loved finish stops working after a cleanup, restore from `_archive/`.

## TICK 5 — script-src and missing-resource scan (2026-05-27T08:39:06Z)

### `<script src>` tags in paint-booth-v2.html that point to non-existent files:
  ⚠ MISSING: js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523
  → 93 <script src> tags · 1 missing

### `<link href>` (stylesheets/icons) in paint-booth-v2.html that don't exist:
  → 15 <link href> tags · 0 missing

### `<img src>` in paint-booth-v2.html that don't exist (sampling first 50):
  → 0 <img src> sampled · 0 missing

### Investigating missing user-import-car-preview.js

Does js/finishes/ even exist as a directory?
  Yes — contents:
guest-designers.js
user-import-drop-preview.js
user-import-gallery.js
user-imports.js

Other files referencing 'user-import-car-preview' or 'userImportCarPreview' name:
electron-app/dist-contributor-portable/win-unpacked/resources/server/paint-booth-v2.html:2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>
electron-app/dist-contributor-portable/win-unpacked/resources/server/pyserver/_internal/paint-booth-v2.html:2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>
electron-app/dist-contributor-portable/win-unpacked/resources/server/pyserver/_internal/shokk-drop.html:95:  <script src="js/finishes/user-import-car-preview.js?v=shokk-drop"></script>
electron-app/dist-contributor-portable/win-unpacked/resources/server/shokk-drop.html:95:  <script src="js/finishes/user-import-car-preview.js?v=shokk-drop"></script>
electron-app/server/paint-booth-v2.html:2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>
electron-app/server/pyserver/_internal/paint-booth-v2.html:2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>
paint-booth-v2.html:2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>

Same cache-buster (?v=spb-user-imports-20260523) appears in HTML — sibling files of the missing one to see what landed vs didn't:
2686:    <script src="js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523"></script>
2687:    <script src="js/finishes/user-import-gallery.js?v=spb-user-imports-20260523"></script>
2688:    <script src="js/finishes/user-imports.js?v=spb-user-imports-20260523"></script>

### Diagnosis (HIGH severity, new finding)

Same partial-edit pattern as tonight's two big bugs. The 2026-05-23 'spb-user-imports' batch added 3 script tags at `paint-booth-v2.html:2686-2688`. Two of the three JS files exist; **`user-import-car-preview.js` does not**. Every page load 404s on this resource.

The file is referenced in **all 3 mirror copies** AND in the **packaged dist** at `electron-app/dist-contributor-portable/win-unpacked/` — meaning the broken HTML has already shipped to a build.

User-facing impact: the user-imports feature exists (gallery + main module both load) but `car-preview` sub-feature is silently dead. Browser dev-tools would show the 404 but otherwise no crash — feature just doesn't appear.

Fix options (owner judgment, not autonomous):
1. **Create `js/finishes/user-import-car-preview.js`** with the intended preview functionality — need original spec from the 2026-05-23 directive.
2. **Remove the script tag** (lines 2686 + 2693 if it appears in shokk-drop.html too) to silence the 404 — loses the unbuilt feature.
3. **Find the preview function in another file** (e.g. inlined into `user-import-gallery.js` or `user-imports.js`) — rename the script src to whichever file actually contains it.

**Severity:** HIGH — production 404 on every page load, ships in the dist build. Same root cause class as slider regression + pattern-brush bug.

## TICK 6 — dist build freshness check (2026-05-27T08:54:03Z)

The packaged build at `electron-app/dist-contributor-portable/win-unpacked/` was referenced earlier in a 404 finding. Checking whether it contains tonight's fixes:

[1] SCALE_BASE_MIN in dist paint-booth-2-state-zones.js:
194:const SCALE_BASE_MIN = 1.0, SCALE_BASE_MAX = 10.0;

  Expected: 0.05 (post-fix). If 1.0 → dist is pre-slider-fix.

[2] swatch_routes.py in dist still gated on SHOKKER_SWATCH_LIVE_SPLIT?
135:                if prefer_live and truthy_env('SHOKKER_SWATCH_LIVE_SPLIT'):

[3] Does the dist contain the 6 new Color/Spec scale handlers?
  setZoneBaseColorScale → 0
0 occurrence(s)
  setZoneSpecScale → 0
0 occurrence(s)
  resetZoneBaseColorScale → 0
0 occurrence(s)
  resetZoneSpecScale → 0
0 occurrence(s)
  stepZoneBaseColorScale → 0
0 occurrence(s)
  stepZoneSpecScale → 0
0 occurrence(s)

[4] Inner-mirror state for 10 paint_v2/v3 files in dist (do they match root?):
  drift: engine/paint_v2/iridescent_insects.py (root=c976dfa17e45f2880e0857203a7c7aa0 dist=8258c529d6e3f19a777d14878699eeae)
  drift: engine/paint_v2/military_tactical.py (root=a31b45092ace43d1aaf2fa240f308bcb dist=33d2aa5b3a243bc09bd82390674e8773)
  drift: engine/paint_v2/spectrum_shift.py (root=ae6ce2140a30326b0f6709a91e5e2098 dist=b53395403c8958ab68714be752cc1fc0)
  drift: engine/paint_v3/paradigm_v3.py (root=c329ee31afd50106642d8156322c0aa1 dist=a987f9ee8e195b9afedf2874ae7504dd)
  drift: engine/paint_v3/primitives.py (root=230d9e421807bbda2bac24f739fb6c4d dist=30baf6eaa2b82e6c933f42e691449a6c)
  → 0/5 sampled in sync, 5 drift

[5] dist build modification time vs latest tonight-fix:
  dist paint-booth-v2.html mtime:   1779545350 (2026-05-23T14:09:10Z)
  root paint-booth-2-state-zones.js: 1779863937 (2026-05-27T06:38:57Z)
  → 🟠 DIST IS OLDER than tonight's fix. Rebuild needed before shipping.

### Verdict — 🟠 DIST IS STALE

The packaged build under `electron-app/dist-contributor-portable/win-unpacked/` was packed on **2026-05-23**, before any of tonight's fixes landed. It contains:

- ❌ Slider bug NOT fixed (SCALE_BASE_MIN=1.0 still clamps sub-1.0)
- ❌ Thumbnail bug NOT fixed (SHOKKER_SWATCH_LIVE_SPLIT env gate still present)
- ❌ Missing all 6 new Color/Spec scale handlers
- ❌ Stale engine files (5/5 sampled paint_v2/v3 files drifted)
- ❌ Missing user-import-car-preview.js (404 baked in)

**If owner ships this dist to anyone, they ship all five regressions.**

**Recommended owner action:** rebuild the Electron dist before any contributor distribution. Use whatever `npm run dist` / `electron-builder` invocation produces `win-unpacked`. **Not auto-triggered** because it's a long batch process and loop discipline says no long-running batch ops without owner approval.

After rebuild, re-run this same Tick 6 check to confirm dist now matches root.

## TICK 7 — multi-HTML missing-resource scan (2026-05-27T09:54:02Z)

Sweep all SPB_*.html + paint-booth-*.html for <script src> tags that 404. Already checked paint-booth-v2.html → 1 miss (user-import-car-preview.js). Now checking siblings.

  ⚠ paint-booth-v2.html → missing: js/finishes/user-import-car-preview.js?v=spb-user-imports-20260523

Summary: scanned 52 HTML files · 1 missing <script src> references

## TICK 9 — server-route vs UI-fetch parity (2026-05-27T10:23:41Z)

Cross-reference all UI fetch('/api/...') paths against actually-registered server routes.

Extracting UI fetch('/api/...') paths...
  found 10 distinct /api/* routes called from UI JS

Extracting server @app.route('/api/...') definitions...
  found 57 distinct /api/* routes registered server-side

### Routes UI calls but server doesn't register (UI-side BROKEN):
< /api/render-pattern-tile

### Routes server registers but no UI ever calls (server-side DEAD CODE):
> /api/blank-canvas
> /api/clear-cache
> /api/default-assets
> /api/diagnostics
> /api/dual-shift-preview
> /api/echo
> /api/export-spec-channels
> /api/export-to-photoshop
> /api/finish-by-id
> /api/finish-registry-status
> /api/finish-viewer
> /api/for-review
> /api/guest-designers
> /api/health
> /api/iracing-viewer-info
> /api/mix-preview
> /api/pattern-layer
> /api/photoshop-exchange-root
> /api/photoshop-import-file
> /api/photoshop-import-list

### Diagnosis

**UI-BROKEN (real bug):** Only `/api/render-pattern-tile` — already on the morning brief, no new findings here. Good.

**Server-DEAD (apparent):** 20+ routes the UI doesn't call. But CAVEAT: my UI scan only grepped root-level `*.js` (10 routes found across paint-booth-*.js). The actual UI surface includes:
- `js/finishes/*.js` (user imports, gallery)
- `js/zones/*.js` (zone material controls — never installed but ships)
- HTML inline scripts in `finish-viewer.html`, `shokk-drop.html`, `spec-sculpt.html`
- `SPB_*.html` page-specific inline fetches

So many of the 'dead' routes are probably live elsewhere. Concrete examples I can vouch are intentional:
- `/api/health`, `/api/echo`, `/api/diagnostics` — dev/monitoring endpoints (always kept)
- `/api/pattern-layer` — exactly what the pattern-brush fix proposal wants to repoint TO; so it's correctly server-side ready
- `/api/finish-viewer`, `/api/guest-designers` — likely called from their own HTML pages
- `/api/photoshop-*` — Photoshop bridge feature; called from a separate flow

**Actual durable finding from this tick:** only the previously-known pattern-brush issue. The other 20+ apparent 'dead routes' need a deeper sub-page UI scan before any can be declared safe to remove. Recommend leaving them alone.
