# Shokker Paint Booth V5 — Electron Build

Packaged desktop app. Source of truth: parent V5 folder. This folder contains the Electron shell; server assets are copied from V5 root.

## Build steps

1. **Copy server assets** (run from `electron-app/`):
   ```bash
   npm run copy-server
   ```
   Copies: HTML, JS, CSS, Python server, engine/, finish_colors*, thumbnails/ from V5 root.

2. **Build the installer**:
   ```bash
   npm run build
   ```
   `prebuild` runs `copy-server` automatically, so `npm run build` alone is enough.

3. **Server EXE** (if not using bundled Python): Build `shokker-paint-booth-v5.exe` (e.g. PyInstaller) and place in `electron-app/server/` before packaging.

## Edit workflow

- Edit files in the **V5 root** (parent folder), not in `electron-app/server/`.
- Run `npm run copy-server` before building so the packaged app has your changes.
- `electron-app/server/` is overwritten by copy-server — do not edit it directly.

## What gets copied

- `paint-booth-v2.html`, `paint-booth-v2.css`, `paint-booth-*-*.js`
- `server.py`, `server_v5.py`, `config.py`, `shokker_engine_v2.py`
- Expansion modules: `shokker_24k_expansion.py`, `shokker_color_monolithics.py`, etc.
- `finish_colors_lookup.py`, `finish_colors.json`
- `engine/` (full package)
- `thumbnails/` (pre-rendered base/pattern/monolithic PNGs)
