# Finish picker detail and durable personal preferences — 2026-09-15

## Owner request and root causes

The owner supplied ALL THAT / FAR OUT screenshots: Y2K Chrome and Vinyl Groove
changed appearance on enlargement. Small requests used 48px legacy static/warm
snapshots; enlargement rejected undersized snapshots and rendered current output.
The grid displayed nine small cards across a 1920px screen. A capture-phase card
click handler also intercepted favorite and rating controls before their own
handlers. Favorites/ratings had only origin-scoped localStorage persistence.

## Result

- Responsive finish grids: five cards at desktop widths above 1300px; four,
  three, two and one at smaller breakpoints. Previews fill each card at 2:1.
- Split chips request 256px per side. `source=faithful-v1` derives both chip and
  enlargement from one current 512px-per-side master, keyed by renderer hash,
  engine cache token, finish type/ID, tint and seed. It never uses legacy static
  or synthetic fallback images. Existing finish math and M/R/Cc remain unchanged.
- Cold masters use atomic disk writes and at most two concurrent renders.
  Hidden cards no longer get eagerly primed. Category banners use the same lazy
  observer and rotate only visible banners, every 12 seconds instead of 950ms.
- Rating handles are 24px with a 36px input hit area. Ratings update during a
  drag and sorting runs on release. My Rating replaces the ambiguous Best label;
  higher ratings lead within each category. A–Z remains alphabetical.
- Preview interception excludes controls. Favorite clicks update in place;
  search/Favorites results keep matching cards expanded after leaving a category.

## Persistence contract

`GET/POST /api/finish-preferences` stores versioned data in
`%APPDATA%/ShokkerPaintBooth/finish-preferences.json`, outside the install tree and
independent of browser port/origin. `.bak` retains the previous valid file.
Existing browser favorites/ratings migrate by filling missing IDs only. Favorite
removals are explicit false entries, so an old profile cannot resurrect them.
Per-ID patches and a file lock protect independent concurrent changes. Browser
storage is retained as a local copy with a persistent pending-write journal and
retry after a failed request. Corrupt server data is refused and preserved.
The installer already specifies `deleteAppDataOnUninstall: false`.

An already-erased browser favorite cannot be reconstructed if no copy remains.
This change migrates available existing choices and protects subsequent saves.

## Verification and delivery boundary

- `python -m pytest tests/test_picker_detail_preferences.py -q`: five tests pass
  (shared image identity, simulated installation replacement/new-origin reads,
  old-profile removal safety, concurrent patches, invalid/corrupt preservation,
  stable storage path).
- `node tests/test_finish_preferences_client.js`: migration, removal, offline
  journal/retry and ratings pass.
- `node tests/test_picker_control_clicks.js`: favorite/rating clicks pass through
  the capturing preview handler; artwork clicks still enlarge.
- Live V5 HTTP: `at_y2k_chrome` and `fo_vinyl_groove` 256px chips exactly equal
  BOX-downsampled 512px enlargements, pixel for pixel. Warm requests measured
  48–79ms; one cold Vinyl Groove request took 6.6s. Cold latency depends on the
  existing finish renderer; the new master is reused across display sizes.
- Browser: five loaded 512×256 images across 1920px, four at 1280px, enlarged
  handles, dragged Dial-Up Green 50→88 and observed it move to first place;
  rating persisted on reload, then native range set to89 and favorite saved
  in the isolated data file. A subsequent full reload restored both. Removing
  the favorite preserved search; a final real pointer drag89→67 kept the picker
  open (no accidental image viewer). Clicking Y2K artwork still opened its
  matching1024×512 image. No production preferences used as test writes.

QA used an isolated V5 server on59877; the owner's59876 process was untouched.
Root/runtime mirrors must be synchronized before handoff. The running app needs
a restart for Python route changes and reload for the cache-tokened frontend.
No installer build, public release, commit or push is part of this change.

M7 is not applicable: this changes preview selection, resizing, UI and storage,
not authored finish construction or the engine's paint/spec math.
