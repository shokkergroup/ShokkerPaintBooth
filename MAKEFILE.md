# SPB Common Commands Cheat Sheet

> Paste-ready commands for everyday dev tasks. Bookmark this file.

Not a real Makefile (Windows dev environment); just a cheat sheet of what to type.

---

## Quick Start

```bash
# Clone + install + run (first time)
git clone https://github.com/shokkergroup/shokker-paint-booth.git
cd shokker-paint-booth
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
cd electron-app && npm install && npm run start
```

---

## Running

```bash
# Full app (Electron + Python server)
cd electron-app && npm run start

# Python server only (browser at printed URL)
python server.py

# Python server with debug output
set SPB_DEBUG=1 && python server.py
```

---

## Building

```bash
# Full Setup.exe build
cd electron-app && npm run build

# Just sync server assets (fast, run after editing root files)
cd electron-app && node copy-server-assets.js

# Just PyInstaller bundle (for debugging)
cd electron-app/server && pyinstaller --onedir --noconsole --name pyserver server.py

# Clean build artifacts
rm -rf electron-app/dist build/ dist/ __pycache__/ server.build/ server.dist/
```

---

## Testing

```bash
# All tests
pytest tests/

# Single test file
pytest tests/test_finish_registry.py

# With coverage
pytest --cov=engine tests/

# Benchmark suite
python benchmark_finishes.py

# Benchmark single finish
python benchmark_finishes.py --finish chrome
```

---

## Linting & Formatting

```bash
# Python
ruff check .
ruff format .

# JS (if eslint configured)
cd electron-app && npm run lint
cd electron-app && npm run format
```

---

## Profiling

```bash
# CPU profile a render
python -m cProfile -o profile.prof -s cumulative benchmark_finishes.py --finish chrome

# Visualize
snakeviz profile.prof

# Memory profile
pip install memray
memray run server.py
memray flamegraph memray-*.bin
```

---

## Git Workflow

```bash
# Create a branch
git checkout -b feat/my-new-finish

# Stage + commit
git add -p
git commit -m "feat(finishes): add neon lime variant"

# Push and open a PR
git push -u origin feat/my-new-finish
gh pr create --fill

# Keep branch current
git fetch origin && git rebase origin/main
```

---

## Release

```bash
# Tag a release
git tag -a v6.2.0 -m "v6.2.0 — Boil the Ocean"
git push origin v6.2.0

# Build installer
cd electron-app && npm run build

# List GitHub releases
gh release list

# Create GitHub release with installer asset
gh release create v6.2.0 \
  --title "v6.2.0 — Boil the Ocean" \
  --notes-file SPB_RELEASE_NOTES.md \
  electron-app/dist/*.exe
```

---

## File Sync Verification

```bash
# Check all three copies are in sync
diff -r engine/ electron-app/server/engine/
diff -r engine/ electron-app/server/pyserver/_internal/engine/

# Verify paint-booth-*.js copies
for f in paint-booth-*.js; do
  diff "$f" "electron-app/server/$f" || echo "MISMATCH: $f"
done
```

---

## Ports & Processes

```bash
# Find what's on a port (if SPB won't start)
netstat -ano | findstr :5000

# Kill a stuck Python
taskkill /F /IM python.exe

# Kill a stuck Electron
taskkill /F /IM electron.exe
taskkill /F /IM "Shokker Paint Booth.exe"
```

---

## Dependency Management

```bash
# Python
pip install <pkg>
pip freeze > requirements.txt

# Node
npm install <pkg>
npm outdated
npm audit

# Upgrade Electron
cd electron-app && npm install electron@latest --save-dev
```

---

## Log Inspection

```bash
# Server log tail
tail -f server_log.txt

# Packaged app logs
notepad "%APPDATA%\Shokker Paint Booth\logs\main.log"

# Recent render request
type last_render_request.json | jq
```

---

## Docs

```bash
# Serve docs locally with any static server
cd docs && python -m http.server 8080
# then open http://localhost:8080/

# Convert MD to HTML (one-off)
pip install markdown
python -m markdown README.md > README.html
```

---

## See Also

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — deep dive on the dev loop
- [docs/BUILD.md](docs/BUILD.md) — full build process
- [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) — release checklist
- [docs/DEBUGGING.md](docs/DEBUGGING.md) — when it breaks
