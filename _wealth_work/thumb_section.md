### Thumbnails rebaked

The picker requests `/api/swatch/<type>/<id>?...&prefer=live`, which deliberately skips the static PNGs and serves from `thumbnails/swatch_cache/picker_split/`. Both layers had to be rebuilt, and the audit found more stale than new:

* **`rebuild_picker_swatches.py`** (incremental, renderer-hash driven) — **562 baked**. That covered all 484 ids with no thumbnail at all (`msk_` 40 · `woc_` 100 · `pdg_` 50 · `cos_` 60 · `elm_` 60 · `nsx_` 50 · `ffl_` 75 · `fts_` 49) plus VIVA MEXICO and UNION JACKED.
* **Change detection missed four cultural shelves.** RISING SUN rebaked 7 of 52, FORBIDDEN DRAGON 0 of 40, LET FREEDOM RING 0 of 10, MORTAL SHOKK 0 of 26 — so those tiles would have kept showing the *old* specs indefinitely. Forced by id: **108 baked, 0 errors**.
* **`--warm-cache`** for the `prefer=live` path: **696 baked, 0 errors**. It aborts the entire batch if any item trips the FRACTURED WILDS release lock (`wilds_110_owner_review_manifest.json` is absent), so it has to be run scoped to non-Wilds ids.

Verified against the live server using the exact URLs the picker builds, 39-finish random sample across all fourteen shelves: **39/39 HTTP 200, median 4.2 ms, p90 6.2 ms**.

Two things left alone on purpose: the 300 errors in the incremental pass are all the WILDS release lock (a deliberate guard in another lane), and `electron-app/server/thumbnails/picker_split/` sits **632 files behind root** — those PNGs are not in `runtime-sync-manifest.json` and look to be populated at package time, so that gap predates today and is the owner's call.

