# How to Verify (SPB Verification Task-Map)

One page that maps **every verification entrypoint** in the Shokker Paint Booth
repo: the exact command, what it checks, and when to run it.

> **Hub:** Start at **`SPB_WIKI.html`** (open it in a browser from the repo
> root). The Wiki is the living index of the whole system; this file is the
> "how do I prove it still works?" companion to it.

All commands below are run from the **repo root**. Verification lanes are
**report-only by design** while the catalog/pattern rebuild is in flight — they
surface signal, they do not (yet) hard-gate. The same commands run in CI; see
`.github/workflows/ci.yml`.

---

## Quick reference

| Entrypoint | Command | What it checks | When to run |
| --- | --- | --- | --- |
| **Doctor** | `python scripts/spb_doctor.py` | Whole-repo health: imports load, registries build, key files present, no obvious breakage. The fastest "is anything on fire?" check. | First thing in any session; before and after a risky change. |
| **tests_v2** | `python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q` | The ground-up regression suite (behavioral contracts that should hold regardless of catalog churn). | Before committing; after touching engine/server/script code. |
| **Legacy tests** | `python -m pytest tests/ -o addopts= -o filterwarnings= -p no:cacheprovider -q --tb=short -m "not gpu and not integration"` | The original suite. Report-only during the rebuild (catalog/quality tests churn). | When working near the areas it covers. |
| **Visual diff** | `python scripts/spb_visual_diff.py` | Golden-image / render comparison — catches unintended visual drift in finishes. | After any change that could affect rendering output (even indirectly). |
| **Catalog report** | `python scripts/spb_catalog_scorecard.py` | Catalog scorecard / drift: finish counts, quality scoring, missing or placeholder entries. | After catalog edits or a rebuild pass. |
| **JS lint** | `node scripts/check-js-lint.mjs` | Lints the JS surface. **Degrades gracefully if eslint is absent** (reports a notice instead of failing). | After editing any `.js`/`.mjs`. |
| **JS syntax** | `npm run check:js` | Plain `node --check` syntax pass over JS files (the hard gate). | After editing any JS. |
| **Sync drift** | `node scripts/sync-runtime-copies.js --check` | Confirms runtime mirror copies are in sync with their source-of-truth (no drift). **`--check` only — never run the writing sync yourself; the orchestrator syncs.** | Before committing if you edited a file that has a runtime mirror. |

---

## Detailed map

### 1. `spb_doctor.py` — repo health check
```
python scripts/spb_doctor.py
```
- **Checks:** that core modules import, the finish registries build without
  error, and the repo is structurally sound. This is the broadest, cheapest
  signal that the system is intact.
- **When:** at the start of a session, and immediately after any change that
  touches imports, registries, or engine wiring. If `spb_doctor` is unhappy,
  fix that before trusting anything else.

### 2. `tests_v2/` — ground-up regression suite
```
python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q
```
- **Checks:** behavioral contracts written ground-up to be stable across the
  catalog rebuild (engine render contract, registry integrity, spec contract,
  server contract, sync integrity, dated regressions). This is the suite to
  trust during the rebuild.
- **Why the flags:** `-o addopts=` and `-o filterwarnings=` neutralize repo
  pytest config so the run is not affected by `addopts`/warning churn;
  `-p no:cacheprovider` avoids stale cache on the network drive.
- **Tip:** if results look stale/garbled, purge `__pycache__` and set
  `PYTHONDONTWRITEBYTECODE=1` before re-running, then trust the exit code.

### 3. `spb_visual_diff.py` — golden-image / visual regression
```
python scripts/spb_visual_diff.py
```
- **Checks:** rendered output against golden images to catch unintended visual
  drift in finishes. The last line of defense for "did the pixels change?"
- **When:** after any change that could affect rendering, even finish-neutral
  refactors. Visual drift can appear from changes you did not expect to matter.

### 4. `spb_catalog_scorecard.py` — catalog report / scorecard
```
python scripts/spb_catalog_scorecard.py
```
- **Checks:** the finish catalog: counts, quality scores, placeholders, and
  drift vs. expected. (Historically referred to as the "catalog report".)
- **When:** after catalog edits or a rebuild pass, to see whether the catalog
  moved in the intended direction.

### 5. `check-js-lint.mjs` — JS lint (graceful)
```
node scripts/check-js-lint.mjs
```
- **Checks:** lint quality of the JS surface. **If eslint is not installed it
  degrades gracefully** — it reports that lint was skipped rather than failing,
  so it is safe to run anywhere and safe to keep report-only in CI.
- **When:** after editing any `.js` / `.mjs`. Pair with `npm run check:js`
  (the syntax gate) for a fuller picture.

### 6. `sync --check` — runtime mirror drift guard
```
node scripts/sync-runtime-copies.js --check
```
- **Checks:** that runtime mirror copies match their source-of-truth files (no
  drift). `--check` is **read-only**.
- **Important:** do **not** run the writing form of the sync yourself — the
  orchestrator owns syncing. Use `--check` to detect drift; if it reports
  drift, flag it rather than fixing it by hand.

---

## CI

All of the above also run in **`.github/workflows/ci.yml`**. The hard gates
today are: runtime mirror drift (`sync --check`) and JS syntax
(`npm run check:js`). Everything else — full test suite, `tests_v2`, catalog
validation, ruff/black/mypy, JS lint, and the dependency audits (`pip-audit`,
`npm audit`) — runs **report-only** (`continue-on-error: true`) while the
rebuild settles. As each area goes green, flip its lane to a hard gate.

---

## When in doubt

1. `python scripts/spb_doctor.py` — is anything on fire?
2. `python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q` — do the contracts hold?
3. `python scripts/spb_visual_diff.py` — did the pixels change?
4. Open **`SPB_WIKI.html`** for the full system map.
