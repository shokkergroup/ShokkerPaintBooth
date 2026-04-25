# Shokker Paint Booth — Style Guide

This is the code style guide for SPB. It codifies what "looks right" in this
codebase so reviewers can spend energy on logic, not bikeshedding. When the guide
disagrees with an existing file, the guide wins for new code; do not mass-reformat
existing files in the same PR as a logic change — land formatting separately.

Tools enforce most of this automatically: black for Python, prettier for JS/JSON,
ruff for Python lint, EditorConfig for whitespace. Configure them from the repo
root (`pyproject.toml`, `.prettierrc.json`, `.editorconfig`); do not override per
directory unless there is a specific reason documented in a comment.

## Python

### Formatting

- **PEP 8** with the exceptions below.
- **Line length 120.** (Not 80, not 79. Engine code is dense numeric math where
  100+ is normal; 120 is the ceiling.)
- **Black** is the formatter. Run `black .` before pushing; no manual alignment.
- **Ruff** is the linter and import sorter. `ruff check --fix .` before pushing.
- **f-strings** preferred over `.format()` or `%`. Reserve `%`-style for logging
  calls where you want deferred formatting.

### Exceptions to PEP 8

- `E501` (line too long) — black handles; ignore in ruff config.
- `E741` (ambiguous variable name) — we use `l`, `I`, `O` in linear-algebra code
  where they have mathematical meaning (identity, ones). Acceptable in engine
  only.
- `N806` (non-lowercase var in function) — shape tuples `(H, W)`, colour tuples
  `(R, G, B)`, and channel matrices are upper-case by convention. Keep them.

### Type hints

- **Encouraged but gradual.** Engine code is pre-typed; UI/server code is not.
  When adding a new module, type it fully. When editing an untyped module, type
  the function you touch; don't sweep.
- Prefer modern syntax: `list[int]` not `List[int]`, `int | None` not
  `Optional[int]`. We target Python 3.11+.
- Use `numpy.typing.NDArray[np.uint8]` when you care about dtype; plain
  `np.ndarray` is fine when the caller already enforces shape.

### Docstrings

- **Google style** (not NumPy, not Sphinx). One-line summary, blank line, then
  `Args:`, `Returns:`, `Raises:`, `Example:` sections as needed.
- Every public function in `engine/` gets a docstring. Private helpers
  (`_leading_underscore`) can skip if the name is self-explanatory.
- Example:

      def composite_zone(base: NDArray, pattern: NDArray, alpha: float) -> NDArray:
          """Blend a pattern into a zone base with premultiplied alpha.

          Args:
              base: (H, W, 3) uint8 RGB zone base image.
              pattern: (H, W, 4) uint8 RGBA pattern overlay.
              alpha: Global strength multiplier, clamped to [0, 1].

          Returns:
              (H, W, 3) uint8 RGB composited image.

          Raises:
              ValueError: If shapes do not match.
          """

### Imports

- Standard library first, then third-party, then first-party, separated by blank
  lines. Ruff's `I` rule enforces this.
- Avoid `from x import *` in production code. Tests may use it sparingly for
  fixtures.
- Relative imports within `engine/` are fine (`from .compose import composite`),
  absolute imports at the server/app boundary.

## JavaScript

### Formatting

- **4-space indent, single quotes, semicolons, ES2020 target.** Prettier
  enforces; config is in `.prettierrc.json`.
- **Line length 120.** Matches Python for consistency.
- **Trailing commas `es5`** — on multi-line arrays/objects, not on function
  arguments (ES2017 syntax is allowed but not required).
- **Semicolons always.** Automatic semicolon insertion has too many foot-guns.

### Modules

- **Plain script files** are the norm (no bundler). Concatenated into
  `booth.html` at build time. Keep file-level IIFEs and guard globals behind an
  object (`window.SPB = window.SPB || {}`).
- **No default exports** — export named symbols. Makes refactors (rename,
  find-references) far cheaper.

### Variables

- **`const` by default**, `let` when mutation is required, **never `var`**.
- Destructure when it improves readability, don't when it creates 4-line
  patterns to pull one field.

### Comments

- Same "why not what" rule as Python. `// HACK:` and `// TODO(#123):` flags are
  welcome; naked `// TODO` is not (attach an issue number or remove).

## Markdown

- **ATX headings** (`#`, `##`) — never `====` underlines. Consistent with GitHub.
- **Fenced code blocks** with language tags (` ```python `, not bare ` ``` `).
  Renders syntax highlighting on GitHub and VS Code preview.
- **Tables preferred over bullet lists** for comparative data. Humans scan
  tables faster. Lists for sequences of related statements; tables for "X has
  property A, Y has property B".
- **Wrap at ~88 columns** for prose paragraphs; do not wrap tables, code, or
  URLs. Prettier's `proseWrap: preserve` respects this.
- **Links are reference-style** in long documents (`[text][ref]` with refs at
  bottom). Inline links are fine in short docs.
- **No trailing whitespace** *inside paragraphs*, but `.md` files do not trim
  trailing whitespace globally — GFM uses double-space for linebreaks. Our
  EditorConfig reflects this.

## File naming

| Layer        | Convention      | Example                              |
| ------------ | --------------- | ------------------------------------ |
| Python files | `snake_case.py` | `spec_patterns.py`, `compose.py`     |
| Python classes | `PascalCase`  | `class ZoneRenderer:`                |
| Python funcs | `snake_case`    | `def composite_zone(...)`            |
| Python const | `SCREAMING`     | `PATTERN_REGISTRY`, `MAX_ZONES`      |
| JS modules   | `kebab-case.js` | `paint-booth-3-canvas.js`            |
| JS classes   | `PascalCase`    | `class RenderQueue { ... }`          |
| JS functions | `camelCase`     | `function assignFinishToSelected()`  |
| JS constants | `SCREAMING`     | `const MAX_HISTORY = 50;`            |
| Markdown docs | `UPPER_CASE.md` in `/docs` | `ONBOARDING.md`, `STYLE_GUIDE.md` |

Directories use `kebab-case` (`electron-app/`, `spec-patterns/`) except Python
packages which use `snake_case` (`engine/expansions/`).

## Comments

- **Why, not what.** `# increment counter` is noise; `# compensate for GGX lobe
  darkening at grazing angles` is gold.
- **`TODO`** includes an issue number or the author's initials and a date:
  `# TODO(#412): move to lookup table`, `# TODO(rs 2026-04-17): refactor`.
- **`FIXME`** is stronger than `TODO` — means a known bug that should block a
  release. Audit before every release.
- **Block comments** above the code they describe, aligned to its indent. No
  mid-line trailing `# comments` for anything non-trivial.

## Tests

- **Naming:** `test_what_when_expected`. Example:
  `test_composite_zone_when_alpha_zero_returns_base`.
- **One assertion per test** where practical; multiple if they test the same
  behaviour from different angles.
- **Fixtures in `tests/fixtures/`**, parametrize with `@pytest.mark.parametrize`.
- **Markers:** `@pytest.mark.slow`, `@pytest.mark.gpu`, `@pytest.mark.integration`.
  Default `pytest` run excludes `slow` and `gpu` via CI config.
- **Golden images** live under `tests/fixtures/golden/`. Regenerate with
  `pytest --regenerate-goldens` (opt-in flag in `conftest.py`).

## Commit messages

- **Imperative mood.** "Add pattern cookbook", not "Added" or "Adds".
- **Subject line < 72 characters.** Hard limit. Summary before any prefix.
- **Prefix with scope** when helpful: `engine: fix GGX floor`, `ui: reduce
  rebuild cost in renderZones`.
- **Body wraps at 72 columns**, blank line between subject and body.
- **Link the issue** on its own line at the end: `Fixes #412`, `Refs #87`.
- **Co-authors** on their own lines at the very end, in
  `Co-Authored-By: Name <email>` format.
- Avoid `WIP:` commits on `main`; use a branch if you need to stash in-flight work.

## Versioning

- `VERSION.txt` is the single source of truth. Read via `pyproject.toml`
  dynamic version and via `electron-app/package.json` build script.
- SemVer: `MAJOR.MINOR.PATCH`. Engine-breaking registry changes bump MAJOR;
  new finishes/patterns bump MINOR; bug fixes bump PATCH.
- Tag every release: `git tag -a v6.1.2 -m "..."`.

## When in doubt

Match the surrounding code. If two files in the same directory disagree, match
the one that looks like it was written more recently (check `git log --follow`).
If you're still unsure, open the PR with a question in the description — review
is cheap, rewriting post-merge is expensive.
