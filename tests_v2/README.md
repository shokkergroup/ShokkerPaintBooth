# tests_v2 — Current, ground-up SPB test suite

A **fresh, all-green** test suite built 2026-05-30, reflecting the **current** state of Shokker Paint Booth and where it's heading. It exists alongside the legacy `tests/` suite (which is kept as history but is noisy: many of its assertions predate the MR→MRC spec-routing migration, the 2D→3-channel spec change, and the active base/pattern rebuild).

## Why a new suite

The catalog is under **active rebuild** — finishes, bases, and spec patterns are added/removed daily (by Codex + the owner). A test suite that asserts *exact catalog counts, exact IDs, or exact pixel values* will flap every day and train everyone to ignore red. So this suite is built on a different principle:

> **Test stable CONTRACTS, not churning DATA.**

What that means in practice:
- ✅ We assert: *every registered finish renders without crashing*, *spec output is iron-safe and finite*, *registries are internally consistent (no phantom group refs)*, *the bugs we fixed stay fixed*, *server routes return correct status codes*, *the 3-copy sync is intact*.
- ❌ We do **not** assert: exact finish counts, exact catalog membership, exact M/R/CC pixel values, or anything that legitimately changes when the owner curates the catalog. (The **visual-diff harness** — `scripts/spb_visual_diff.py` — is the right tool for "did a finish's *look* change"; this suite is for "is the app *correct and uncrashing*".)

## The iron rule of this suite

**Every test here passes against the current app. No red tests, ever.** If something genuinely can't be made green because behavior is in flux, it is `@pytest.mark.xfail(reason=...)` with a written reason, never left failing.

## Run it

```
python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q
```

(The `-o` overrides neutralize the repo-global `pyproject.toml` addopts/filterwarnings so this suite runs clean and standalone. Also available as `npm run test:v2`.)

## Layout

| File | Covers |
|------|--------|
| `conftest.py` | session-scoped `engine` import (stdout-suppressed) + `registries` fixture + `is_valid_spec` helper |
| `test_engine_render_contract.py` | every base/monolithic/pattern renders at small + mid size without crashing; output finite |
| `test_spec_contract.py` | spec output shape + iron-safe ranges + GGX floor; handles 2D and 3-channel |
| `test_registry_integrity.py` | registries load; IDs unique; no phantom/orphan group references that crash the picker |
| `test_regressions_2026_05.py` | regression guards for every bug fixed in the 2026-05-29/30 hardening pass |
| `test_server_contract.py` | key Flask routes return correct status codes / shapes (incl. render-busy 429) |
| `test_sync_integrity.py` | 3-copy sync: manifest valid, writable pairs identical, engine drift is report-only |

## Goal

Over time this becomes the canonical suite and CI gates on it; the legacy `tests/` is retired once its still-valuable invariants are ported here. Add new contract tests as the app grows — keep them green.
