# SPB Test Suite

Comprehensive pytest scaffold for Shokker Paint Booth. Covers engine math,
iron-rule enforcement, zone validation, finish-data integrity, and Flask
route contracts.

## Layout

| File | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures: `app_client`, `tmp_paint_file`, `sample_zones`, `clean_caches`, `engine_module`, `server_module`, `finish_data_js_text`. |
| `smoke_test.py` | Fast end-to-end registry/compose smoke battery (legacy — kept). |
| `test_engine.py` | Iron rules, seed determinism, gradient bounds, apply_wear clamping, registry completeness (15+ tests). |
| `test_zones.py` | Zone validation, priority order, link groups, mute, roundtrip (10+ tests). |
| `test_finish_data.py` | Data integrity of `paint-booth-0-finish-data.js` — ID uniqueness, hex color validity, group orphans (10+ tests). |
| `test_server_routes.py` | Flask route contracts: /status, /health, /finish-groups, /api/finish-data, /api/diagnostics, /api/render-stats, etc. (10+ tests). |

## Running tests

From the project root:

```bash
# Full suite, quiet output
python -m pytest tests/ -q

# Verbose
python -m pytest tests/ -v

# Single file
python -m pytest tests/test_engine.py -v

# Single test
python -m pytest tests/test_engine.py::test_iron_rules_cc_floor -v

# Stop on first failure
python -m pytest tests/ -x

# Show slowest 10 tests (useful for keeping the suite under a minute)
python -m pytest tests/ --durations=10
```

## Coverage

Install `pytest-cov` first:

```bash
pip install pytest-cov
python -m pytest tests/ --cov=engine --cov=shokker_engine_v2 --cov-report=term-missing
```

For HTML coverage:

```bash
python -m pytest tests/ --cov=engine --cov=shokker_engine_v2 --cov-report=html
# open htmlcov/index.html
```

## Design rules (must hold for every new test)

1. **Fast** — each test should complete in well under a second. Use
   `(64, 64)` shapes for engine calls, not `(2048, 2048)`.
2. **Independent** — no test relies on another test's side effects. Use
   fixtures (especially `clean_caches`) when touching shared state.
3. **Clear assertions** — every `assert` has a message explaining the
   expected outcome, not just `assert x`.
4. **Scoped fixtures** — heavy work (registry import, server import)
   happens in `scope="session"` fixtures so it amortizes.
5. **Skip with reason** — if a test is temporarily broken or
   environment-dependent, use `@pytest.mark.skip(reason="...")` rather
   than deleting it.

## Adding new tests

1. Decide which file it belongs in (engine math → `test_engine.py`, route
   contract → `test_server_routes.py`, etc.).
2. Reuse existing fixtures where possible.
3. Keep the assertion count modest — one behavior per test function is
   ideal for clear diagnostics.

## CI integration

Minimum CI invocation:

```bash
python -m pytest tests/ --tb=short -q
```

For a richer report (recommended once the suite stabilizes):

```bash
python -m pytest tests/ \
  --tb=short \
  --durations=10 \
  --junitxml=build/test-results.xml \
  --cov=engine --cov=shokker_engine_v2 \
  --cov-report=xml:build/coverage.xml
```

### Known Windows notes

* The project root contains an apostrophe (`Ricky's PC`) — pytest is fine,
  but some shells need the path quoted.
* Engine import logs to stderr on startup; this is normal and does not
  affect test results.

## Why not mock?

We deliberately hit the real engine and real Flask routes. The SPB moat
(real-time car preview + zone-level spec + pattern-per-channel) depends on
subtle correctness across hundreds of finish functions — mocking the engine
away would defeat the point. All tests are still fast because the registries
load once per session and each test uses tiny canvases.
