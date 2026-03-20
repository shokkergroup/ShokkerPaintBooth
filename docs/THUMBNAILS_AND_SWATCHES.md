# Pattern (and finish) thumbnails — exact look before launch

**Goal:** The pattern swatches you see in the picker and finish library are the **exact** way the engine renders that pattern (same pipeline as full render), and they are **tied to each pattern ID** and available **before you launch** the app — no live render needed at runtime.

---

## How it works

1. **Bake (pre-launch)**  
   Run the thumbnail rebuild so every pattern (and optionally every base and monolithic) is rendered **once** using the **same engine** as in-app (`build_multi_zone`):

   ```bash
   cd "Shokker Paint Booth V5"
   python rebuild_thumbnails.py --type pattern
   ```

   Output: `thumbnails/pattern/<pattern_id>.png` for every pattern in `PATTERN_REGISTRY` (e.g. `acid_wash.png`, `long_flame_sweep.png`, …). Each PNG is the **exact** engine output at 128×128 (or the size you pass with `--size`).

2. **Tie to patterns**  
   - File name = pattern ID: `thumbnails/pattern/<id>.png`.  
   - The server and the rebuild script both use the same registry and the same path convention, so each pattern ID has exactly one thumbnail file.

3. **Server serves them**  
   When the front-end requests a swatch (e.g. `/api/swatch/pattern/acid_wash?color=888888&size=48`), the server:

   - Looks for `thumbnails/pattern/acid_wash.png`.
   - If it exists → serves that file (resized to the requested size if needed). **No live render.**  
   - If it does not exist → falls back to live `_render_swatch_bytes()` (which can be slow or flaky).

   So once thumbnails are baked, the **exact** look is shown and rendering/thumbnail problems at runtime are avoided for patterns.

4. **Before launch**  
   - Run the bake (step 1) before packaging or releasing.  
   - Commit or ship the `thumbnails/` folder (or at least `thumbnails/pattern/`) so the installed app has pre-rendered PNGs.  
   - Then at launch the server finds `thumbnails/pattern/<id>.png` for each pattern and serves them; the front-end never needs a live pattern swatch render.

---

## One-time bake (patterns only)

From the **V5** folder:

```bash
python rebuild_thumbnails.py --type pattern
```

- Uses the **full engine** (same as in-app).  
- Writes only `thumbnails/pattern/*.png`.  
- Faster than baking bases + monolithics.  
- After this, pattern swatches in the UI are exact and tied to IDs.

---

## Full bake (all types)

One full run updates **all existing** thumbnails for every finish the app can show:

```bash
cd "Shokker Paint Booth V5"
python rebuild_thumbnails.py
```

(No `--type` means `--type all`.)

| Type | Output folder | Includes |
|------|----------------|----------|
| **base** | `thumbnails/base/<key>.png` | Every combinable base finish |
| **pattern** | `thumbnails/pattern/<key>.png` | All pattern overlays |
| **monolithic** | `thumbnails/monolithic/<key>.png` | Fusions, Color Shift, chameleon, and every other one-shot finish |

Fusions live in `MONOLITHIC_REGISTRY`, so they are included when you build monolithics or run a full bake.

**Bake only one type:**

| Command | What gets (re)built |
|--------|----------------------|
| `python rebuild_thumbnails.py --type base` | Bases only |
| `python rebuild_thumbnails.py --type pattern` | Patterns only |
| `python rebuild_thumbnails.py --type monolithic` | Monolithics only (includes Fusions) |

---

## Where things live

| What | Where |
|------|--------|
| Bake script | `rebuild_thumbnails.py` (V5 root) |
| Output directory | `thumbnails/` (V5); config: `config.THUMBNAIL_DIR` |
| Pattern thumbnails | `thumbnails/pattern/<pattern_id>.png` |
| Manifest (ok/fail) | `thumbnails/rebuild_manifest.json` |
| Server swatch route | `server.py`: `/api/swatch/<type>/<key>`; prefers pre-rendered file when present |
| Front-end swatch URL | Built in `paint-booth-2-state-zones.js` (e.g. `getSwatchUrl`) → `/api/swatch/pattern/<id>?color=...&size=48` |

---

## Reliable thumbnails on every load (pipeline fixes)

**Goal:** Accurate thumbnails that show up every time someone loads the program.

- **Server-authoritative type:** `/api/finish-data` now returns a `type` field (`base` | `pattern` | `monolithic`) for every finish. The client uses this (and a `FINISH_TYPE_BY_ID` map) so swatch URLs always use the correct path (`/api/swatch/base/...`, `/api/swatch/pattern/...`, or `/api/swatch/monolithic/...`). No more wrong-type guesses.
- **Key normalization:** The server tries both the exact key and a hyphen→underscore variant when looking for a pre-rendered PNG, so IDs that differ only by hyphen/underscore still find the baked file.
- **Thumbnail-status banner:** On load, the app calls `/api/thumbnail-status`. If the thumbnail folder is missing or any expected PNGs are missing, a dismissible banner tells the user to run `python rebuild_thumbnails.py` from the V5 folder.
- **See on paint:** In the swatch picker (base/pattern/monolithic), a "See on paint" button opens a modal with a large swatch and a "Preview on paint" action that runs a one-zone preview-render with the selected finish on the current paint file, so you can see exactly what that finish does to your paint.

1. **Canonical location**  
   All pre-rendered thumbnails live in **one folder**: `<V5>/thumbnails/` (e.g. `Shokker Paint Booth V5/thumbnails/`). The server reads `config.THUMBNAIL_DIR`, which is set to `ROOT_DIR/thumbnails` in `config.py`. When the app runs from the V5 folder, `ROOT_DIR` is the V5 folder, so the server looks in `V5/thumbnails/`.

2. **Run rebuild from V5**  
   Always run the bake from the **V5** directory so output is written to `V5/thumbnails/`:
   ```bash
   cd "Shokker Paint Booth V5"
   python rebuild_thumbnails.py --type pattern
   ```
   or `python rebuild_thumbnails.py` for bases + patterns + monolithics.

3. **Ship the thumbnails folder**  
   Include the `thumbnails/` folder in your build or installer (e.g. copy `V5/thumbnails/` next to the server or set `THUMBNAIL_DIR` to that path). Then when a user launches the app, the server finds the PNGs and serves them; no live render and no missing swatches.

4. **If thumbnails don’t show**  
   - **Server log:** On startup the server logs either `Thumbnails: <path> (N pre-rendered PNGs)` or `Thumbnail dir missing/empty`. Check that path and run the bake if needed.  
   - **Wrong directory:** If the server runs from a different root (e.g. Electron packaged path), ensure `config.THUMBNAIL_DIR` or the fallback in `server.py` points at the same `thumbnails/` folder that rebuild_thumbnails.py wrote to.  
   - **Bake failures:** Check `thumbnails/rebuild_manifest.json` for `fail` entries; fix the listed keys (e.g. missing registry entry or engine error) and re-run the bake.

---

## Optional: bake before every release

Add a pre-release or pre-pack step that runs:

```bash
python rebuild_thumbnails.py --type pattern
```

(or `python rebuild_thumbnails.py` for full bake). Then include `thumbnails/` in the build so the exact pattern look is always available and tied to each pattern ID before launch.
