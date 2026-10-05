# COMMIT_GUIDE — Safe Commit of Tonight's Uncommitted Work

Owner-facing checklist for committing the night's uncommitted work **safely**.
Run the verification sequence first, read the CRITICAL git note, then commit.

> Run every command from the **project root**:
> `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`

---

## 1. Verification sequence (run in this exact order)

Do **not** skip steps, and do **not** reorder them. Step 0 (purging the
bytecode cache) must come first — stale `__pycache__` is the #1 cause of
phantom test failures on this repo's network drive.

### 0. Purge `__pycache__` and disable new bytecode

PowerShell:

```powershell
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ |
  Remove-Item -Recurse -Force
$env:PYTHONDONTWRITEBYTECODE = "1"
```

Bash:

```bash
find . -type d -name __pycache__ -prune -exec rm -rf {} +
export PYTHONDONTWRITEBYTECODE=1
```

### 1. Runtime-copy drift check (read-only)

```bash
node scripts/sync-runtime-copies.js --check
```

**Expected:** `0` *writable* drift.
A report of **~16 report-only engine** files is **expected and OK** — those
are report-only and are converged separately by the owner (see
[§3 What NOT to commit](#3-what-not-to-commit)). Do **not** run the sync
script to "fix" them here.

### 2. Python test suite

```bash
python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q
```

**Expected:** `~1164 passed`.
The flags matter:
- `-o addopts=` / `-o filterwarnings=` — ignore repo `pytest.ini` / `pyproject`
  overrides so the run is reproducible.
- `-p no:cacheprovider` — no pytest cache writes (avoids network-drive cache
  artifacts).

If anything fails, treat it as **guilty-until-proven a cache/sync artifact**:
re-run Step 0, then re-run this step before believing a real failure.

### 3. JS lint

```bash
node scripts/check-js-lint.mjs
```

**Expected:** exit code `0` (no lint errors).

### 4. Project doctor

```bash
python scripts/spb_doctor.py
```

**Expected:** exit code `0` / clean report.

> On this network drive, **trust process exit codes** over raw stdout —
> stdout can be stale, empty, or contaminated by engine output. A green exit
> code from each step above is the source of truth.

---

## 2. CRITICAL git note — `tests/` and `tests_v2/` must be added explicitly

**`tests/` and `tests_v2/` were NEVER git-tracked.** Two `.gitignore` rules
silently swallowed them:

1. A broad `test_*.py` ignore rule (matched every test file by name), and
2. An 8-char sentinel pattern that also matched the string **`tests_v2`**.

These ignore rules were **fixed tonight**. But because the directories were
never tracked, Git will **not** pick them up automatically — you must add
them **explicitly**:

```bash
git add tests/ tests_v2/
```

### Verify the ignore fix actually took (do this before committing)

```bash
git check-ignore tests_v2/test_engine_render_contract.py
```

**Expected:** **return code `1`** with **no output** — meaning the path is
**no longer ignored**. (`git check-ignore` prints the matching pattern and
returns `0` when a path *is* ignored; returning `1` / empty confirms the fix.)

PowerShell — read the return code explicitly:

```powershell
git check-ignore tests_v2/test_engine_render_contract.py; "rc=$LASTEXITCODE"
```

If this still returns `0` (a pattern is printed), **stop** — the ignore fix
did not apply; do not commit until `rc=1`.

After `git add tests/ tests_v2/`, confirm the test files are staged
(`git status` should list the new test files under "Changes to be committed").

---

## 3. What NOT to commit

- **The report-only engine drift (~16 files from Step 1).**
  These are report-only and the **owner converges them separately**. Do not
  stage them, and do not run the sync script to silence the `--check` report.
- **`_visual_diff/current` and `report.*`** — these are **git-ignored**
  build/diagnostic artifacts. Leave them ignored; do not force-add them.

If `git status` shows any of the above as staged, unstage them
(`git restore --staged <path>`) before committing.

---

## 4. Where to go next

- **`MORNING_BRIEF_2026-05-30.md`** (project root) — start here: the night's
  summary and current state.
- **`SHIP_READY_INDEX.md`** (project root) — the ship-readiness index / map of
  what is done and verified. (`SHIP_READY_PROGRESS.md` tracks live progress.)
- **Owner-decision queue** — the list of items awaiting your call (including
  the report-only engine convergence in §3). See the MORNING_BRIEF for the
  current queue.

---

### One-line commit recipe (after all checks are green)

```bash
git add tests/ tests_v2/        # explicit — these were never tracked
git check-ignore tests_v2/test_engine_render_contract.py   # expect rc=1, no output
git add <your other intended changes>
git status                       # confirm NO report-only drift / artifacts staged
git commit -m "..."              # owner-authored message
```
