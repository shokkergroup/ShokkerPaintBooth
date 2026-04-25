# SPB Developer Cheatsheet

One page. Print it, tape it to your monitor. If you find yourself reaching for this doc a lot, that's fine — it exists so you don't have to remember everything.

---

## Common Commands

### Run dev build

```bash
cd electron-app
npm run dev
```

### Run Python server standalone

```bash
python server.py
```

### Run tests

```bash
pytest -q                    # Python suite
pytest tests/engine -q       # just engine
```

### Build installer

```bash
cd electron-app
npm run build
```

### Sync three-copy files

```bash
# Manual diff (quickest sanity check)
diff base_registry_data.py electron-app/server/engine/base_registry_data.py
diff electron-app/server/engine/base_registry_data.py electron-app/server/pyserver/_internal/engine/base_registry_data.py
```

### Grep the whole repo

```bash
# Use the Grep tool in Claude. On the command line:
rg "FINISH_REGISTRY" --type py
```

---

## Key File Paths

### Frontend (three-copy)

- `paint-booth-0-finish-data.js` — BASES, PATTERNS, SPEC_PATTERNS, groups
- `paint-booth-2-state-zones.js` — state, zone UI
- `paint-booth-3-canvas.js` — canvas + RLE masks
- `paint-booth-5-api-render.js` — API client, render history

### Engine (three-copy)

- `shokker_engine_v2.py` — core paint physics, ~8,200 lines
- `engine/base_registry_data.py` — FINISH_REGISTRY
- `engine/patterns.py` — PATTERN_REGISTRY
- `engine/spec_patterns.py` — SPEC_PATTERN_REGISTRY
- `engine/gpu.py` — GPU pipeline
- `engine/paint_v2/*.py` — one file per finish family

### Server

- `server.py` — Flask API
- `config.py` — ports, paths, toggles

### Packaging

- `electron-app/copy-server-assets.js` — stages bundled Python
- `electron-app/package.json` — version, entry points

### Release

- `VERSION.txt` — canonical version string
- `CHANGELOG.md` — history
- `LAUNCH_CHECKLIST.md` — pre-flight
- `SPB_ROADMAP.md` — what's next

---

## Keyboard Shortcuts (in-app)

Defaults — not yet fully remappable, planned for 6.3.0.

| Action | Shortcut |
|--------|----------|
| Undo | Ctrl+Z |
| Redo | Ctrl+Y / Ctrl+Shift+Z |
| Save Shokk | Ctrl+S |
| Open Shokk | Ctrl+O |
| Toggle zone picker | Z |
| Toggle finish picker | F |
| Toggle spec picker | Shift+F |
| Render refresh | R |
| Zoom in / out | Ctrl+= / Ctrl+- |
| Fit to view | Ctrl+0 |
| Select all zones | Ctrl+A |
| Clear selection | Esc |

---

## Spec Map Cheat (inverted B scale!)

| Channel | Meaning | 0 | 255 |
|---------|---------|---|-----|
| R | Metallic | Dielectric | Metallic |
| G | Roughness | Mirror | Matte |
| **B** | **Clearcoat** | **None** (0-15) / **Max gloss** (16) | **Dull** |
| A | Specular mask | Reserved | Reserved |

Key presets:

- Chrome: R255 / G0 / B16
- Metallic: R255 / G85 / B0
- Matte: R0 / G220 / B15
- Gloss Black: R0 / G20 / B16

---

## Adding a Pattern (in order)

1. `PATTERNS` in all three copies of `paint-booth-0-finish-data.js`
2. `PATTERN_GROUPS` in the same three files
3. `PATTERN_REGISTRY` in all three copies of `engine/patterns.py`
4. Texture function: `def texture_NAME(shape, mask, seed, sm):`

If any step is missed you'll get a specific failure. See `TROUBLESHOOTING_DEV.md`.

---

## Common Bugs & First Check

| Symptom | First thing to check |
|---------|---------------------|
| Finish missing in packaged build | Is `_internal` copy synced? |
| Pattern magenta | `PATTERN_REGISTRY` entry exists? |
| Pattern missing from picker | `PATTERN_GROUPS` entry exists? |
| Chrome looks matte | Spec B channel (should be 16) |
| App won't start on sandbox | `pyserver/_internal` bundled? |
| `python.exe` zombie | Shutdown handler in server.py |
| Splash shows old version | Grep for old version string; update all hits |
| Undo eats RAM | Known — stack unbounded, fix on 6.3.0 |

---

## Version Bump Checklist (mini)

Bumping the version touches **many** places. Don't miss one:

1. `VERSION.txt`
2. `electron-app/package.json`
3. `CHANGELOG.md` heading
4. `README.md` (if it shows current version)
5. About dialog / splash in-app
6. Installer EXE metadata
7. `git tag v<version>`

See `LAUNCH_CHECKLIST.md` section 5 for the authoritative list.

---

## Debug Hooks

- `_engine_rot_debug()` at `shokker_engine_v2.py` ~line 84 — use for engine-state dumps. Gated on env var.
- `assignFinishToSelected` in `paint-booth-2-state-zones.js` — keep the debug lines, they're intentional.

---

## Fast Links

- Memory index: `memory/MEMORY.md`
- Heartbeats: `memory/heartbeats_history.md`
- Priorities (this week): `PRIORITIES.md`
- Known issues: `OPEN_ISSUES.md`
- QA flags: `QA_REPORT.md`
- Conventions: `docs/CONVENTIONS.md`
- Glossary: `docs/GLOSSARY.md`
- Troubleshooting (dev): `docs/TROUBLESHOOTING_DEV.md`
- Troubleshooting (user): `SPB_TROUBLESHOOTING.md`

---

*Keep this file short. If it grows past two printable pages, split it.*
