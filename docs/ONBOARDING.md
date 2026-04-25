# Shokker Paint Booth — Contributor Onboarding

Welcome. This document gets a new contributor from a fresh machine to their first
merged pull request. It assumes you can read code and know how to use Git; it does
not assume you have seen SPB before.

## What is SPB?

Shokker Paint Booth (SPB) is a desktop application for designing automotive paint
schemes destined for iRacing, rFactor 2, Automobilista 2, and other sim platforms
that consume PBR-style textures. A user drops a car template image, defines
**zones** (hood, doors, roof, etc.), then mixes **bases**, **patterns**, and
**finishes** into each zone. The Python engine renders a preview and exports the
four-channel spec map (R=metallic, G=roughness, B=clearcoat, A=reserved) plus the
diffuse PNG that the sim expects. The moat is per-channel pattern control, live
preview on a car-shape, and zone-level spec settings — no competitor does all
three.

## Prerequisites

- **Windows 10 or 11** (the Electron build is Windows-only today; WSL is fine for
  the Python side but GUI testing needs a native host)
- **Python 3.11–3.13** (3.13 recommended; bundled runtime ships 3.13)
- **Node.js 18 LTS or 20 LTS** (the Electron main process runs on Node)
- **Git for Windows** with bash shell
- **Visual Studio Code** (not required, but `.vscode/` ships wired up for it)
- Optional: a CUDA GPU if you want to test the `engine.gpu` code path — CPU
  rendering works everywhere

## Clone & setup (5 steps)

1.  **Clone.** Do it to a path without spaces if you can; the project lives at
    `E:\Koda\Shokker Paint Booth Gold to Platinum` on the maintainer's machine and
    the apostrophe in `Ricky's PC` has caused shell-quoting pain in the past. A
    path like `C:\spb` is friendlier.

        git clone https://github.com/shokkergroup/paint-booth.git
        cd paint-booth

2.  **Install Python dev deps.** Create a venv so you don't pollute system Python,
    then install the project as editable with dev extras:

        python -m venv .venv
        .venv\Scripts\activate
        pip install -e .[dev]

    This reads `pyproject.toml` and installs `flask`, `numpy`, `scipy`, `pillow`,
    `opencv-python-headless`, plus `black`, `ruff`, `pytest`, and `mypy`.

3.  **Install Node deps.** The Electron shell lives under `electron-app/`:

        cd electron-app
        npm install
        cd ..

4.  **Verify with smoke tests.** This renders a tiny car, exercises the registry,
    and confirms your environment is sane:

        python tests/smoke_test.py
        python -m pytest tests -v -m smoke

5.  **Launch the app.** Two processes — Flask server and Electron shell. Two
    terminals is simplest, or use the VS Code compound launch config "Full stack:
    Server + Electron":

        # Terminal 1
        cd electron-app/server && python server_v5.py
        # Terminal 2
        cd electron-app && npm start

    You should see the booth UI open on a car template; the bottom status bar
    should read "Server: connected".

## Your first contribution

Look for issues tagged `good-first-issue` on GitHub. Good candidates live in
three areas:

- **New spec pattern.** Pick a texture (e.g., "fine pinstripe"), write the
  function, register it. See [PATTERN_COOKBOOK.md](PATTERN_COOKBOOK.md) for a
  step-by-step recipe — this is the best starter task because it touches the
  engine, the JS catalog, and the UI without needing deep architecture knowledge.
- **Documentation fix.** Typos, outdated screenshots, missing captions in
  `docs/`. Low-risk, high-value.
- **Test coverage.** Look at `coverage.xml` after `pytest --cov`; any `engine/`
  module under 70 % coverage is fair game.

Open a PR against `main`. Keep it under ~300 changed lines for your first one so
review is fast. Squash merge is the norm.

## Key concepts to understand before touching code

- **Three-copy sync.** Three files (`base_registry_data.py`,
  `paint-booth-0-finish-data.js`, and a handful more) exist in three locations:
  `./`, `electron-app/server/`, and `electron-app/server/pyserver/_internal/`.
  Edit only the root copy, then run `node scripts/sync-runtime-copies.js --write`
  or VS Code task "Write Sync". CI will fail on PRs that skip this.
- **Zones vs layers.** A **zone** is a region of the car (hood, door, bumper). A
  **layer** is a paint operation within a zone (base colour, pattern, finish
  overlay). The UI edits layers per zone; the renderer composites layers bottom-
  up per zone then the whole car in one pass.
- **Spec channel semantics.** R=metallic, G=roughness, B=clearcoat **inverted**
  (0–15 = none, 16 = maximum gloss, 255 = dull). That B-channel inversion
  surprises everybody; see `docs/CONVENTIONS.md` for the full table.
- **Finish vs pattern.** A **finish** is a whole-surface effect (chrome, candy,
  matte) that modifies all four spec channels. A **pattern** is a texture
  (stripes, carbon weave, flake) that modulates one or more channels. Some
  categories blur the line (e.g., "brushed aluminium" is sold as a finish but is
  implemented as a pattern stack).
- **Registry double-binding.** Every pattern lives in three registries:
  `PATTERNS` (JS display), `PATTERN_GROUPS` (JS picker), and `PATTERN_REGISTRY`
  (Python lookup). Miss one and the UI shows it but rendering silently skips it.

## Who to ask for help

- **Maintainer:** Ricky (ricky@shokkergroup.com). GitHub `@shokkergroup`.
- **Engine questions:** start with `docs/ARCHITECTURE.md` and `shokker_engine_v2.py`
  (search for `_engine_rot_debug` — that function is the engine's narration).
- **UI questions:** `paint-booth-2-state-zones.js` is the state machine.
- **Build/release:** `docs/BUILD.md` and `docs/RELEASE_PROCESS.md`.
- **Persistent agent notes:** the project keeps a `MEMORY.md` under
  `.claude/projects/…/memory/` with 80+ session summaries. Read it if you want
  the "why" behind oddities.

## Where to start reading code

In this order:

1.  `docs/ARCHITECTURE.md` — 10-minute high-level tour.
2.  `electron-app/server/engine/base_registry_data.py` — see how a finish maps to
    an engine function; pick one you've heard of (chrome, matte, candy) and
    follow the function reference.
3.  `electron-app/server/engine/compose.py` — the layer compositor. Small,
    readable, and the heart of the render pipeline.
4.  `electron-app/server/server.py` — Flask routes. Start at `POST /render` and
    trace a request top-to-bottom.
5.  `electron-app/main.js` → `paint-booth-2-state-zones.js` → `paint-booth-3-canvas.js`
    for the UI side. Don't try to understand it all at once; pick a feature, e.g.
    "how does a user add a new zone?", and trace *just that*.

Welcome aboard. Ship something small this week.
