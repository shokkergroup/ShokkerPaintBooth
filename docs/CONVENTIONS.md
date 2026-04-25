# SPB Code Conventions

These are the conventions we follow across the Shokker Paint Booth codebase. They are **descriptive** where we already agree and **prescriptive** where we want to stop future bikeshedding. Use your judgment where this doc is silent — but if you find yourself breaking one of these rules, check with the team first.

---

## 1. Naming

### Python

- **Modules:** `snake_case.py`. Long names are fine; abbreviations are not. `chameleon.py` is OK; `cham.py` is not.
- **Functions:** `snake_case`. Private helpers prefixed with `_`.
- **Classes:** `PascalCase`. Acronyms keep their case (`GPUEngine`, not `GpuEngine`).
- **Constants:** `UPPER_SNAKE_CASE`. Registries are constants: `FINISH_REGISTRY`, `PATTERN_REGISTRY`.
- **Paint functions:** name matches what they render. `texture_carbon_fiber`, `paint_chrome_mirror`. Readers should guess the function name from the finish name.

### JavaScript

- **Files:** `paint-booth-N-category.js` for the numbered core files. Keep the numeric prefix — it makes ordering explicit in directory listings.
- **Functions:** `camelCase`. DOM helpers prefixed with `dom`: `domBuildZoneRow`.
- **Globals:** avoid. When unavoidable, prefix `SPB_`: `SPB_STATE`, `SPB_IRON_RULES`.
- **Event handlers:** prefix with `on`: `onZoneClick`, `onFinishPicked`.

### Registry keys

- Finish IDs: lowercase snake_case, descriptive. `carbon_fiber_black`, `chrome_deep`, `monolithic_arsenal_24k`.
- Never rename a finish ID in place — that breaks saved Shokks. Add a new ID and alias the old one.

---

## 2. File Organization

### The three-copy rule

Several files exist in **three places** for historical and packaging reasons:

1. Repo root (canonical for hand-editing)
2. `electron-app/server/` (what the dev server runs)
3. `electron-app/server/pyserver/_internal/` (what ships in the installer)

Files under this rule (partial list, see `MEMORY.md`):

- `base_registry_data.py`
- `shokker_engine_v2.py`
- `paint-booth-0-finish-data.js`
- `paint-booth-2-state-zones.js`
- `server.py`

**Rule:** when you touch one, you touch all three, **in the same commit.** A pre-commit diff check helps; if yours is stale, ask the team for the latest one.

### Where things live

| Kind | Location |
|------|----------|
| Frontend core | `electron-app/*` and the three `paint-booth-*.js` copies |
| Engine / rendering | `shokker_engine_v2.py` and `engine/` |
| Finishes | `engine/paint_v2/` (one file per finish family) |
| Patterns | `engine/expansions/` and `engine/patterns.py` |
| API server | `server.py`, `server_v5.py`, `config.py` |
| Build scripts | `electron-app/` JS build, `scripts/` for Python-side |
| Dev docs | `docs/` |
| Shipping docs | repo root `SPB_*.md` and `README.md` |
| Tests | `tests/` |

If something doesn't fit any of these, ask before inventing a new location. New directories at the repo root are almost always wrong.

---

## 3. Commit Messages

### Format

```
<scope>: <short imperative summary>

<optional longer body explaining why>
```

### Examples that pass review

- `engine: fix GGX floor clamp so chrome highlights don't blow out`
- `finishes: add carbon_forged and four weave variants to monolithic catalog`
- `ui: bound undo stack at 100 entries to stop long-session memory creep`

### Examples that don't

- `wip` (no)
- `fixed stuff` (no)
- `updated paint-booth-2-state-zones.js` (file name is not a message)

### Version bumps

Follow the `vX.Y.Z — Codename — highlights` format used in recent tags. Example: `v6.1.1 — Finish Mixer + Pattern Strength Zones`.

### Squash policy

Feature branches squash on merge. The squash message should read like a changelog entry.

---

## 4. Comments

- **Comment intent, not mechanics.** Bad: `# loop over finishes`. Good: `# Iterate in registry order so save files stay deterministic`.
- **Mark the load-bearing weirdness.** If a line is load-bearing for a non-obvious reason, say so. Spec map B channel's inverted scale is a great example — it should be commented wherever it's used.
- **TODO tags have owners and tiers.** `# TODO(ricky, polish): ...` is fine. `# TODO(blocker): ...` is a release blocker and must be resolved before the next tag.
- **Don't comment-out dead code.** Delete it. Git remembers.
- **Module-level docstring.** Every new Python module starts with a one-paragraph docstring explaining what it owns.

---

## 5. Python specifics

- **Type hints encouraged on new code**, not required on legacy.
- **Engine hot paths avoid abstractions.** If you're about to introduce a class inside `shokker_engine_v2.py`, think twice. Functions + clear dataclasses are the pattern.
- **No wildcard imports** — `from x import *` is banned outside `__init__.py`.
- **NumPy over Python loops** anywhere pixel-wise operations happen.
- **Avoid global mutable state.** Registries are the exception; anything else needs a reason.

---

## 6. JavaScript specifics

- **No bundlers for the three paint-booth files.** These load directly in the Electron shell; keep them plain JS.
- **No frameworks.** We are not adopting React, Vue, or Svelte in this codebase. The existing vanilla-JS pattern is deliberate.
- **Event delegation over per-element listeners** for repeated DOM nodes.
- **DOM rebuilds are expensive.** Prefer diffing. `renderZones()` is the standing example of what not to do going forward.

---

## 7. Tests

- Tests live in `tests/`. Python: `pytest`. JS: not yet standardized — when we pick a runner, this doc gets updated.
- Every new finish gets a golden-image smoke test. A golden image lives in `tests/golden/<finish_id>.png`.
- Don't mark a test skipped without a linked issue in the skip reason.

---

## 8. Things that are OK to break

These conventions bend for good reasons. Don't bend them without one:

- 3-copy sync on experimental branches that haven't touched the installer in weeks — fine. But sync before merging.
- File naming inside `scripts/` is looser than the rest of the repo.
- Comment style inside `BUILD_WIKI_*.py` is intentionally verbose; they're one-off build tools.

---

*When you add a rule here, link to the PR where it was agreed.*
