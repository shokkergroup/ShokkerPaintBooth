# How to Add or Remove a Finish

**Single source of truth:** All bases, patterns, and specials are defined in **`paint-booth-1-data.js`** only.

---

## Add a finish

1. **Edit `paint-booth-1-data.js`**
   - **Base:** Add `{ id: "my_base", name: "My Base", desc: "...", swatch: "#hex" }` to the `BASES` array and add the id to the right group in `BASE_GROUPS`.
   - **Pattern:** Add to `PATTERNS` and to the right key in `PATTERN_GROUPS`.
   - **Special (monolithic):** Add to the `MONOLITHICS` array (or to the generated color monolithics if it’s a gradient/solid/ghost/multi). Add the id to the right `_SPECIALS_*` section so it appears under the correct header in the UI.

2. **Regenerate canonical list (for thumbnails/status)**  
   From the V5 folder:
   ```bash
   python scripts/export_finish_ids.py
   ```
   This updates `finish_ids_canonical.json`. The server uses it for `/api/thumbnail-status` expected counts and missing list.

3. **Backend (if the finish is rendered by the engine)**  
   - **Pattern:** Ensure the id is in `PATTERN_REGISTRY` in `shokker_engine_v2.py` (or the engine module that holds it).
   - **Base / monolithic:** Ensure the id is in `BASE_REGISTRY` or `MONOLITHIC_REGISTRY` as needed so the server can render it.

4. **Thumbnails (optional)**  
   To generate or refresh thumbnails:
   ```bash
   python rebuild_thumbnails.py
   ```
   Or `python rebuild_thumbnails.py --type base` / `--type pattern` / `--type monolithic` for one category.

5. **Client swatch (optional)**  
   If the finish should have a custom preview in the picker, add a renderer in **`paint-booth-4-pattern-renderer.js`** for its id (search for the finish type: baseFns, patternFns, or the specials object).

---

## Remove a finish

1. **Edit `paint-booth-1-data.js`**
   - Remove the entry from `BASES`, `PATTERNS`, or `MONOLITHICS` (and from the generated color monolithics if applicable).
   - Remove the id from `BASE_GROUPS`, `PATTERN_GROUPS`, or the relevant `_SPECIALS_*` section in `SPECIAL_GROUPS`.
   - If you want to hide it without deleting (e.g. for legacy configs): add the id to **`REMOVED_SPECIAL_IDS`** (specials only); `MONOLITHICS` is already filtered by it.

2. **Regenerate canonical list**
   ```bash
   python scripts/export_finish_ids.py
   ```

3. **Backend**  
   Remove or comment out the id from `PATTERN_REGISTRY`, `MONOLITHIC_REGISTRY`, or `BASE_REGISTRY` in the engine so the server doesn’t try to render it.

4. **Thumbnails**  
   You can leave old PNGs in `thumbnails/` or delete them; the server will stop expecting them once the id is out of the canonical list.

---

## Summary

| Step                    | Add                         | Remove                          |
|-------------------------|-----------------------------|----------------------------------|
| 1-data.js               | Add to array + group        | Remove from array + group (or REMOVED_SPECIAL_IDS) |
| export_finish_ids.py    | Run                         | Run                             |
| Engine registries       | Register id                 | Remove id                       |
| rebuild_thumbnails.py   | Optional                    | Optional (delete PNGs if desired)|
| paint-booth-4 (swatch)  | Optional                    | Optional                         |

See **PROJECT_STRUCTURE.md** for where each piece lives.
