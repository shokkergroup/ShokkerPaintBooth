# SPB Testing Guide

> How we verify SPB works — automated tests, manual smoke-tests, and what we don't test (yet).

---

## Overall Strategy

SPB is tested at three levels:

1. **Unit tests** (`pytest`) — Python engine, registries, utility functions.
2. **Integration smoke** — render real liveries, compare against goldens.
3. **Manual QA** — human-in-the-loop visual checks on the Electron UI.

We are explicitly **not** trying to achieve 100 % coverage. We target:

- **>80 %** on engine math and registries
- **>60 %** on server.py routes
- **0 %** on the Electron shell (manual QA owns this)
- **Visual goldens** on a curated subset of finishes

---

## Running Tests

```bash
# All unit tests
pytest tests/

# Specific file
pytest tests/test_finish_registry.py

# With coverage
pytest --cov=engine tests/

# Verbose
pytest -v tests/

# Run a single failing test
pytest tests/test_something.py::test_case_name -vv
```

---

## Test Layout

```
tests/
├── README.md                   ← detailed testing info (if present)
├── conftest.py                 ← pytest fixtures
├── test_finish_registry.py     ← registry consistency checks
├── test_spec_patterns.py       ← spec pattern registration
├── test_render_smoke.py        ← end-to-end render smoke
├── test_color_shift.py         ← color-shift math
├── golden/                     ← reference renders
│   ├── chrome_silverado.png
│   └── ...
└── fixtures/                   ← test PSDs / TGAs
```

(Actual layout may differ — this is the target.)

---

## Writing a Unit Test

Use `pytest` style, not `unittest`. Keep tests short and focused:

```python
# tests/test_finish_registry.py
import pytest
from engine.base_registry_data import FINISH_REGISTRY

def test_all_registered_finishes_have_paint_and_spec():
    for finish_id, entry in FINISH_REGISTRY.items():
        assert callable(entry.get('paint')), f"{finish_id} missing paint()"
        assert callable(entry.get('spec')), f"{finish_id} missing spec()"

def test_chrome_produces_spec_16():
    from engine.paint_v2.chrome_mirror import chrome_spec
    spec = chrome_spec(...)
    # Chrome's clearcoat (B channel) should be 16 (max gloss)
    assert spec[..., 2].mean() == pytest.approx(16, abs=1)
```

---

## Golden Image Tests

For finishes where visual fidelity matters:

```python
# tests/test_render_smoke.py
from PIL import Image
import numpy as np

def test_chrome_silverado_matches_golden():
    actual = render_livery('fixtures/silverado.psd', finish='chrome')
    golden = np.array(Image.open('tests/golden/chrome_silverado.png'))
    diff = np.abs(actual.astype(int) - golden.astype(int)).mean()
    assert diff < 2.0, f"Render diverged from golden by {diff:.2f}"
```

When you intentionally change a finish, update the golden:

```bash
python tests/update_goldens.py --finish chrome
```

Review the git diff of the PNG before committing — make sure the change is what you expected.

---

## Smoke Test Checklist (Pre-Release)

Run this before every tagged release. ~15 minutes.

- [ ] Fresh install from Setup.exe on a clean VM
- [ ] Silverado auto-loads
- [ ] Create 3 zones, assign 3 different finishes
- [ ] Render (should complete < 3 s)
- [ ] Save `.spb`, close, reopen — zones persist
- [ ] Export TGA at 2048x2048, open in Photoshop — looks right
- [ ] Load a different PSD (use a community paint kit)
- [ ] Apply a monolithic (COLORSHOXX, MORTAL SHOKK, or PARADIGM)
- [ ] Apply a spec overlay (brushed, hammered, or peened)
- [ ] Test Undo (3x) and Redo (3x)
- [ ] Test Ctrl+Z edge cases (no crashes)
- [ ] Test File → New
- [ ] Check Help → About shows correct version
- [ ] No console errors in DevTools at any point

---

## What We Don't Test (Yet)

Honest acknowledgements:

- **Electron file dialogs** — painful to automate; manual only.
- **PSD parsing edge cases** — we test common cases; the long tail is tested in production.
- **License validation** — covered by manual QA on each release.
- **Performance regressions across all finishes** — `benchmark_finishes.py` is available but not wired into CI.
- **Visual diffs for every finish** — we golden the top ~20 most-used.

---

## CI (Future)

When CI lands (tracked in PRIORITIES.md), expected pipeline:

```yaml
# .github/workflows/ci.yml (planned)
- pytest tests/
- ruff check .
- node electron-app/copy-server-assets.js --verify
- python benchmark_finishes.py --compare-baseline
```

No CI currently runs on push. Tests are on the honor system for now.

---

## Regression Prevention

If a bug ships and bites users:

1. Fix it.
2. **Write the test that would have caught it.**
3. Add to `tests/`.
4. Ship the hotfix with the test.

Over time this builds a regression suite where our bugs have gone to die.

---

## Visual Regression on Goldens

When a golden changes, the reviewer should:

1. Open `old.png` and `new.png` side-by-side.
2. Decide: is the change intentional (a finish was tuned) or a regression (something broke)?
3. If intentional, update the golden and note the change in `CHANGELOG.md`.
4. If regression, reject the PR.

Never auto-update goldens. That defeats the purpose.

---

## Test Data Hygiene

- Keep `fixtures/*.psd` small (< 5 MB each). Use cropped paint kits, not full 4K PSDs.
- Goldens are `.png` (compressible, lossless). Don't use JPG.
- Don't commit fixture output files — regenerate in CI or test setup.
- `.gitignore` already excludes `output/`, `swatches/`, `audit_images/`.

---

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md)
- [DEBUGGING.md](DEBUGGING.md)
- [PERFORMANCE.md](PERFORMANCE.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — test requirements for PRs
