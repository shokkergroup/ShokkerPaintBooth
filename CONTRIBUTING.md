# Contributing to Shokker Paint Booth

Thanks for your interest in SPB. This project runs on a small core team plus a growing community of livery artists, iRacing sim-racers, and PBR nerds. We welcome bug reports, PRs, finish ideas, and test liveries.

Before you submit anything substantial, please skim this document — SPB has a couple of non-obvious conventions (especially the **3-copy sync rule**) that will save you a rejected PR.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Ways to Contribute](#ways-to-contribute)
3. [Getting the Code](#getting-the-code)
4. [The 3-Copy Sync Rule (CRITICAL)](#the-3-copy-sync-rule)
5. [File Ownership Map](#file-ownership-map)
6. [Code Style](#code-style)
7. [Commit Message Format](#commit-message-format)
8. [Pull Request Process](#pull-request-process)
9. [Testing Requirements](#testing-requirements)
10. [Adding a New Finish](#adding-a-new-finish)
11. [Reporting Bugs](#reporting-bugs)
12. [Getting Help](#getting-help)

---

## Code of Conduct

By participating you agree to the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). TL;DR: be kind, be useful, don't be a jerk, assume good intent.

## Ways to Contribute

- **Test liveries** — open issues with screenshots when something looks wrong.
- **Feature ideas** — open a GitHub Discussion; describe the painter's workflow pain.
- **Bug reports** — see [Reporting Bugs](#reporting-bugs) below.
- **Documentation** — fixes to any `SPB_*.md` or `docs/*.md` file are always welcome.
- **Code** — pick up an issue tagged `good-first-issue` or `help-wanted`.
- **New finishes** — follow [Adding a New Finish](#adding-a-new-finish); this is the most-needed contribution path.

---

## Getting the Code

```bash
git clone https://github.com/shokkergroup/shokker-paint-booth.git
cd shokker-paint-booth
cd electron-app && npm install && npm run start
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full onboarding.

---

## The 3-Copy Sync Rule

**READ THIS TWICE.** SPB ships an embedded Python server that is packaged three ways:

1. Root level (for local dev runs) — e.g. `engine/base_registry_data.py`
2. `electron-app/server/` (copied at build time) — e.g. `electron-app/server/engine/base_registry_data.py`
3. `electron-app/server/pyserver/_internal/` (PyInstaller bundle) — e.g. `electron-app/server/pyserver/_internal/engine/base_registry_data.py`

Any change to a server-side Python file in `engine/`, `engine/paint_v2/`, `engine/expansions/`, `config.py`, or `server.py` **MUST be applied to all three copies**. The same rule applies to `paint-booth-*.js` static assets: all three copies exist.

**If you only edit the root copy, your change will not appear in a built Setup.exe.**

Use the `copy-server-assets.js` script (run as part of `npm run build`) to verify sync. When in doubt, run `diff` across the three trees before pushing.

---

## File Ownership Map

Some files are owned by automated agents. Check the header of any `SPB_*.md` file before editing:

| Area | Owner | Can External Contributors Edit? |
|---|---|---|
| `paint-booth-*.js`, `paint-booth-*.css` | UI agent | PRs welcome, review required |
| `engine/` (all subtrees) | Render agent | PRs welcome, review required |
| `server.py`, `config.py`, `shokk_manager.py` | Server agent | PRs welcome, review required |
| `SPB_*.md` (user docs) | Docs agent | PRs welcome anytime |
| `README.md`, `CONTRIBUTING.md`, `docs/*.md` | Open | Yes, anytime |
| `CHANGELOG.md` | Release agent | Release-only |

---

## Code Style

### Python
- **PEP 8** with 4-space indent and max line length 100.
- Type hints on all new public functions.
- Use f-strings, not `%` or `.format()`.
- Keep files under 1,500 lines where possible. `shokker_engine_v2.py` is grandfathered.

### JavaScript
- **Vanilla ES2020+**, no framework. SPB ships without React/Vue on purpose.
- 2-space indent, single quotes, semicolons.
- `const` by default, `let` when reassigning, never `var`.
- Keep modules small. The `paint-booth-N-*.js` split is logical, not a hard rule.

### Markdown
- ATX headings (`#`, `##`), not Setext.
- Fenced code blocks with language tags.
- Wrap prose at 100 characters. Tables are exempt.

---

## Commit Message Format

Follow a loose Conventional-Commits style:

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `chore`.
- **scope** (optional): `engine`, `ui`, `spec`, `finishes`, `build`, etc.
- **subject**: imperative mood, no period, under 72 chars.

Examples:
```
feat(finishes): add 12 new neon underground variants
fix(spec): clamp GGX roughness floor to 0.02 (WARN-GGX-001)
perf(engine): vectorize metallic flake pass (3.1x speedup)
docs(readme): add build instructions and screenshot placeholder
```

Tag-ship versions get a separate style — see `CHANGELOG.md` history.

---

## Pull Request Process

1. Fork and create a topic branch: `feat/neon-greens`, `fix/spec-clamp`.
2. Make changes. Respect the **3-copy sync rule** if touching server files.
3. Run tests: `pytest` (from `tests/` if present) and smoke-render at least one livery.
4. Push to your fork.
5. Open a PR against `main`. Fill in the PR template (summary + test plan).
6. A maintainer will review. Expect ~48h turnaround.
7. Squash-merge is default. Keep your commit messages clean.

---

## Testing Requirements

- **New finish**: include a swatch render (2048x2048 TGA) in the PR description.
- **Bug fix**: include a before/after screenshot or a failing test that now passes.
- **Engine change**: run `benchmark_finishes.py` and paste deltas.
- **UI change**: confirm no console errors and all three JS copies are in sync.

See [docs/TESTING.md](docs/TESTING.md) for the full strategy.

---

## Adding a New Finish

The canonical path is:

1. Add finish function to `engine/paint_v2/<category>.py` (e.g. `candy_special.py`).
2. Register in `engine/base_registry_data.py` under `FINISH_REGISTRY`.
3. Add UI entry in `paint-booth-0-finish-data.js` under `BASES` + appropriate `BASE_GROUPS`.
4. Mirror changes to the two additional copies (see 3-copy sync rule).
5. Generate a swatch: run `scripts/make_swatch.py <finish_id>`.
6. Add to `CHANGELOG.md` under the current unreleased version.

Full walkthrough: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#adding-a-finish).

---

## Reporting Bugs

Open a GitHub issue with:

- SPB version (Help → About)
- Windows version
- Steps to reproduce
- Expected vs. actual behavior
- Screenshot and/or render output
- Any error text from the server console (Help → Open Server Log)

---

## Getting Help

- **Discord**: [SPB Community](https://discord.gg/shokker)
- **Email**: ricky@shokkergroup.com
- **GitHub Discussions**: for open-ended feature chat

Thanks for contributing. Paint the paint, not the pixel.
