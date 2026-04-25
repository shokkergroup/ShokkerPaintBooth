# SPB Development Guide

> Your first day as an SPB contributor.

This doc walks you through getting a local dev loop running, common development tasks, and the conventions you'll need to follow.

---

## Prerequisites

- **Windows 10 or 11** (SPB is Windows-only; iRacing is Windows-only)
- **Node.js 18 LTS or newer** (`node --version` should print v18+)
- **Python 3.11** (match the version PyInstaller bundles; `python --version`)
- **Git** (obviously)
- **Visual Studio Code** recommended (or any editor you prefer)
- **~8 GB free disk** for dependencies and render output

Optional but helpful:
- **iRacing installed** for end-to-end smoke-tests
- **Photoshop** (for creating test PSDs) — GIMP works too

---

## First-Time Setup

```bash
# 1. Clone
git clone https://github.com/shokkergroup/shokker-paint-booth.git
cd shokker-paint-booth

# 2. Set up Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up Node / Electron
cd electron-app
npm install
cd ..

# 4. Smoke-test
python server.py
# In another terminal:
cd electron-app && npm run start
```

If the Electron window opens and shows the Silverado demo, you're in.

---

## Running Locally

### Option A — Electron dev loop (recommended)

```bash
cd electron-app
npm run start
```

This spawns `main.js`, which in turn spawns the Python server on a free port and opens the Electron window. You get hot-reload on the JS side (Ctrl+R in the window) and server log output in the terminal.

### Option B — Python server only (backend dev)

```bash
python server.py
```

Then open `http://localhost:<port>/` in Chrome. You lose the Electron shell (no file dialogs, no native menus) but you iterate faster when hacking on `engine/`.

### Option C — Standalone engine script

For quickly testing a new finish without boot overhead:

```bash
python benchmark_finishes.py --finish chrome --iterations 5
```

---

## Common Dev Tasks

### Edit a JS file

JS lives at the project root as `paint-booth-*.js`. Edit → `Ctrl+R` in the Electron window to reload. Remember the **3-copy sync rule**.

### Edit a Python engine file

Python changes require restarting the server. In Electron dev mode, close the window and re-run `npm run start`. The bundle cache is not invalidated on file change.

### Add a new finish

See the [Adding a Finish](ARCHITECTURE.md#adding-a-finish) section in ARCHITECTURE.md.

### Add a new spec overlay pattern

1. Write the function in `engine/spec_patterns.py`.
2. Add to `SPEC_PATTERN_GROUPS` in `paint-booth-0-finish-data.js`.
3. Sync to the other two copies.

### Run the test suite

```bash
pytest tests/
```

See [TESTING.md](TESTING.md) for what we test and what's still manual.

### Profile a slow render

```bash
python -m cProfile -o profile.prof benchmark_finishes.py --finish chrome
snakeviz profile.prof
```

See [PERFORMANCE.md](PERFORMANCE.md) for hotspots and optimization guidance.

### Build a Setup.exe

```bash
cd electron-app
npm run build
```

Full instructions: [BUILD.md](BUILD.md).

---

## Common Dev Commands Cheat Sheet

```bash
# Start Electron + Python
cd electron-app && npm run start

# Python server only
python server.py

# Run tests
pytest tests/

# Lint Python
ruff check .

# Lint JS (if configured)
cd electron-app && npm run lint

# Build installer
cd electron-app && npm run build

# Bench a finish
python benchmark_finishes.py --finish <id>

# Verify 3-copy sync
node electron-app/copy-server-assets.js --check

# Clean build artifacts
rm -rf electron-app/dist build/ dist/ __pycache__/
```

---

## Editor Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Error Lens
- GitLens

Create `.vscode/settings.json` (local only, gitignored):

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.trimTrailingWhitespace": true
}
```

### PyCharm

Works fine. Point the interpreter at `.venv/Scripts/python.exe`.

---

## Keeping Your Branch Current

```bash
git fetch origin
git rebase origin/main
# or merge if you prefer
```

SPB uses a trunk-based model with short-lived topic branches. Keep PRs small and focused — large mega-PRs block the review pipeline.

---

## Troubleshooting Dev Issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Python server fails to start | Port already in use | `taskkill /F /IM python.exe` or change port in `.server_port` |
| Electron window blank | JS error in console | Open DevTools (Ctrl+Shift+I), check console |
| Render returns 500 | Python exception | Check server terminal log |
| Finish doesn't appear in picker | Missing `PATTERN_GROUPS` entry | Add to group; un-grouped IDs are stripped |
| Change doesn't appear in built .exe | 3-copy sync violation | Re-run `copy-server-assets.js` |
| `npm install` fails | Node version too old | Upgrade to Node 18 LTS |
| `pip install` fails on numpy | Python 3.12+ incompatibility | Downgrade to 3.11 |

More tips: [DEBUGGING.md](DEBUGGING.md).

---

## Where to Ask for Help

- **Discord `#dev-chat`** — fastest
- **GitHub Discussions** — good for longer questions
- **Email** ricky@shokkergroup.com — for private / sensitive questions

Welcome aboard. Paint the paint, not the pixel.
