# WP10 Plumbing report (2026-10-03)

Status: DONE (all three units).

## Unit 1 - route tests: `tests/test_ai_car_routes_elements.py` - 29 tests, 29 passed
- Builds a bare Flask app + `register_ai_car_routes(app)` (server.py:13850 does the same). Data dir redirected with env vars `SPB_AI_DIR`, `SPB_LEARNED_ELEMENTS`, `SPB_AI_MISSES`, `SPB_LEARNED_CARS` to a per-test folder (real AppData never touched).
- NOTE: `tests/conftest.py` overrides `tmp_path` with ONE shared directory, so the file uses its own `work` fixture (unique subfolder, removed afterwards).
- Covers: GET empty, POST persist (read back from disk), GET returns it, replace + `n` count, `forget:true` removes, box clamping/area rules, 12-box cap, 400-row cap, invalid bodies (missing key/kind/boxes, wrong types, unsupported kind, whole-sheet box, key `../..`), non-JSON / list / scalar bodies, traversal key flattened (`..\..\evil/../Windows` -> `evilwindows`, no stray files), origin guard 403 on foreign Origin, misses append-only (earlier bytes untouched, GET does not modify), truncation 200/60, rotation, learned-cars smoke.
- Design note: invalid input returns HTTP 200 with `{"ok": false}`, not 4xx (the page ignores the status; this is a design choice, not changed). Tests assert "no 5xx, ok false, nothing written".

## Route bug found + fixed
- `POST /api/ai/misses` with a JSON array / scalar body (`["a"]`) raised AttributeError -> HTTP 500 (`body.get` on a list). Fixed in `server_routes/ai_car_routes.py` (`# [WP10 2026-10-03]`, LF file, 3 lines). `py_compile` OK; sync with `sync_mine.json --write` then `--check`: "no drift detected".

## Unit 2/3 - `scripts/ai_atlas/merge_learned_elements.py`
- Reads `learned_elements.json` (`SPB_LEARNED_ELEMENTS` / `SPB_AI_DIR` / `%APPDATA%\ShokkerPaintBooth\ai`, or `--from`). Rows: `{key, kind:'numbers', boxes, source, n, at}`.
- Writes `scripts/ai_atlas/out/learned_elements_atlas.json` (or `--out`): `{v:1, proposals_only:true, cars:{<folder key>:{numbers:[{box (2dp), sources:{buyer,ai,viewer}, count}]}}}`. `--dry-run` is default, `--write` writes (temp + os.replace), input never modified.
- Dedupe by (folder, kind, box rounded to 2dp); source mapped confirm/teach/other -> buyer, ai, viewer; per-source count = MAX (not sum) so re-runs are idempotent.
- Demo: 2 rows (teach n=2 + ai n=1, boxes 0.101 vs 0.104 -> same box). Dry run: "1 new box(es)", file not created. Write: 1 new box, sources {buyer:2, ai:1}, count 3. Second write: "0 new ... (no change)", file bytes identical (also asserted in the test). Raising `n` to 5 raises only buyer count.
- CLIENT LOADER IS NOT BUILT. `js/spb-pro-elements.js` only reads `/api/ai/learned-elements` and localStorage `spb_elem_learned_v1`; nothing consumes the shipped atlas. JS is out of lane. The `out/` dir does not exist until the first real `--write` (no real learned file was merged; the owner's AppData was not read).

## Not verified
- Live server / real page (forbidden); no real learned_elements.json merged; running with the real server after restart.
- Only the `numbers` kind exists server-side (`_ELEM_KINDS`); sponsors/stripes are not learned yet.
