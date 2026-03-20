# Patterns — Deep Dive: How They Work & How to Improve Them

**Purpose:** Single reference for how patterns are implemented in Shokker Paint Booth, how many exist, where they live, how they drive spec channels, and how to add or improve patterns without duplication. Use this before building new patterns or changing the design process.

---

## 1. Pattern count and sources (no duplication)

**Total pattern IDs in the app:** **413** (from `PATTERN_REGISTRY` after server load).

| Source | Approx. count | Where defined | Notes |
|--------|----------------|---------------|--------|
| **Legacy (monolith)** | ~239 | `shokker_engine_v2.py` → `PATTERN_REGISTRY` | Original texture_fn + paint_fn per ID. Many share the same underlying `texture_*` (aliases). |
| **Expansion (V5)** | **113** | `engine/pattern_expansion.py` (IDs) + `engine/expansion_patterns.py` (impl) | Each ID has its **own** closure over `variant=pattern_id`; no rehash of legacy. |
| **Image-based** | **61** | `engine/registry.py` `_img_pats` + optional `_generated` | PNG from `assets/patterns/<category>/<id>.png`. paint_fn = `paint_none`. |

- **Do not** point a new UI pattern to an existing `texture_*` and “rehash” it under a new name unless the doc explicitly allows it. New patterns = **new IDs and new implementations** (new entry in expansion_patterns or new image + registry line).
- **Canonical list:** Backend truth is `PATTERN_REGISTRY` (built in `engine/registry.py`). UI list is `PATTERNS` / `PATTERN_GROUPS` in `paint-booth-1-data.js` (and/or `_ui_finish_data.js`). Server can merge from `/api/finish-data`. Run `python scripts/export_finish_ids.py` to refresh `finish_ids_canonical.json` for thumbnails.

---

## 2. How patterns work in the framework

### 2.1 Data flow (high level)

1. **Zone** has: base (e.g. gloss, matte) + **pattern** (e.g. carbon_fiber, decade_80s_neon_hex) + intensity/scale/rotation.
2. **Render request** sends zones to the server. Server builds per-zone finish via **engine**.
3. **Engine** resolves base (BASE_REGISTRY) and pattern (PATTERN_REGISTRY). For **base+pattern** it calls:
   - **texture_fn(shape, mask, seed, sm)** → returns `{"pattern_val": H×W float32 0–1, "R_range": float, "M_range": float, "CC": optional}`.
   - **paint_fn(paint, shape, mask, seed, pm, bb)** → returns modified RGB paint (optional tint/darken in “grooves”).
4. **compose_finish()** (monolith / engine) combines base spec (R, M, B) with pattern:
   - `spec_R = base_R + pattern_val * R_range * intensity_scale`
   - `spec_M = base_M + pattern_val * M_range * intensity_scale` (if base varies M).
   - So **pattern_val** is a **spatial mask** (0–1); **R_range** / **M_range** control how much the pattern **modulates** roughness and metalness. Negative R_range = pattern areas become **smoother** (lower R).
5. **Spec map output** (what the sim uses): R = roughness, G = smoothness/microsurface, B = clearcoat etc. Pattern only affects where and how much the **base** is varied, so the base’s “character” stays; the pattern adds **texture** (weave, grooves, flames, etc.).

### 2.2 Texture function contract

Every **procedural** pattern (legacy or expansion) implements:

- **texture_fn(shape, mask, seed, sm)**  
  - `shape` = (H, W), `mask` = zone mask, `seed` = rng seed, `sm` = intensity/scale from zone.  
  - Returns dict:
    - **pattern_val**: float32 (H,W) in [0, 1]. **1 = full pattern effect**, 0 = base only.
    - **R_range**, **M_range**: floats. How much pattern_val modulates R and M (can be negative).
    - **CC**: optional (e.g. for clearcoat or extra channels).
    - **R_extra**, **M_extra**: optional per-pixel additive noise (e.g. battle_worn, metal_flake).

**Image patterns** don’t have a texture_fn in the same way: the engine loads the PNG via `engine/render.py` `_load_image_pattern()`, normalizes to 0–1 (luminance or alpha), then that array is used **as** pattern_val; R_range/M_range can be fixed or from a small set for image patterns.

### 2.3 Where the work is done

| Layer | File(s) | Responsibility |
|-------|---------|-----------------|
| **Registry** | `engine/registry.py` | Builds PATTERN_REGISTRY: legacy from monolith, then NEW_PATTERNS (expansion), then image list. Single place that maps pattern_id → { texture_fn, paint_fn, image_path?, … }. |
| **Legacy patterns** | `shokker_engine_v2.py` | Defines PATTERN_REGISTRY dict and all texture_* / paint_* used by it. Many UI IDs point to the same texture_* (alias block ~5170+). |
| **Expansion IDs** | `engine/pattern_expansion.py` | List `NEW_PATTERN_IDS` (flames, decades, music, astro, hero, reactive). |
| **Expansion impl** | `engine/expansion_patterns.py` | `_texture_expansion(shape, mask, seed, sm, variant)` and `_paint_expansion(..., variant)`. Dispatches by **variant** (pattern_id). Each variant gets **dedicated** geometry (starburst, stripes, flames, zodiac glyphs, etc.). `build_expansion_entries(ids)` returns dict of id → { texture_fn, paint_fn, variable_cc, desc } with closures over variant. |
| **Image load** | `engine/render.py` | `_load_image_pattern(image_path, shape, scale, rotation)`. Loads PNG, luminance/alpha → float32 0–1, tile/crop/rotate via `engine/core.py`. Cached by (path, shape, scale, rotation). |
| **Compose** | Monolith / `engine/compose.py` | `compose_finish()`: takes base spec (R,M,B), pattern dict (pattern_val, R_range, M_range), intensity → final spec map. |
| **UI** | `paint-booth-1-data.js`, `_ui_finish_data.js` | PATTERNS array (id, name, desc, swatch). PATTERN_GROUPS for categories. Must include every pattern_id you want in the picker. |

---

## 3. Categories and where to add patterns

- **Legacy:** 20+ groups in PATTERN_GROUPS (Abstract, Animal, Carbon, Flames, Geometric, etc.). Defined in `paint-booth-1-data.js`. Do **not** add new legacy IDs that just alias an existing texture_fn; add **new** texture/paint or use expansion/image.
- **Expansion:** Flames (21), Decades 50s–90s (10 each), Music (10), Astro (incl. 12 zodiac), Hero (3), Reactive (10). Add **new** IDs in `pattern_expansion.py` and **new** variant branches in `expansion_patterns.py` (`_texture_expansion`, `_paint_expansion`). No re-use of legacy pattern logic.
- **Image:** Decades + Music Inspired PNGs in `assets/patterns/50s/`, `60s/`, … `musicinspired/`. Add `(category, id)` to `_img_pats` in `engine/registry.py` and put `assets/patterns/<category>/<id>.png` in place. Optionally add UI in PATTERNS + group.

**Rule:** Everything new = **new ID + new implementation** (new variant in expansion, or new image file + one registry line). No “rehash” of an existing pattern under a new name.

---

## 4. Getting maximum effect in the sim and spec channels

- **pattern_val** should be **clear and readable** at car scale: not too fine (noise that disappears at 2k), not too sparse. Prefer shapes that read as “weave”, “flame”, “stripe”, “starburst” on a hood/fender.
- **R_range / M_range**: Negative R_range makes pattern areas **smoother** (more reflection); positive R_range makes them **rougher**. Tune so the pattern is visible in spec (R/M variation) without blowing out or flattening the base. Use M_range when the base has varying metalness (e.g. metallics).
- **Tileability:** Procedural patterns are naturally tileable. Image patterns: **make them tileable** (offset + clone in Photoshop/Krita, or generate “seamless”) so repeats don’t show a hard seam.
- **Scale/rotation:** Zone scale and rotation are applied in the pipeline; expansion patterns use `shape` and can use `sm` for intensity. Image patterns: `_load_image_pattern(..., scale, rotation)`; at scale=1.0 the image is **tiled** to fill the zone for crisp repeats.
- **Reactive patterns:** The 10 `reactive_*` IDs are designed as **masks** for Pattern-Reactive / Pattern-Pop blend modes (iridescent flake, pearl shift, candy depth, chrome veil, etc.). They output a 0–1 mask that drives where a second base or overlay shows through; they are not “standalone” looks.

---

## 5. Design process improvements

- **One source of truth for “what exists”:** Use `PATTERN_REGISTRY` (or export from it) as the canonical list. Before adding a “new” pattern, search the registry and expansion IDs so we don’t duplicate.
- **Naming:** Prefer one clear convention: e.g. `decade_80s_neon_hex`, `music_smilevana`, `reactive_pearl_shift`. No duplicate IDs (e.g. circuit_board vs circuitboard); pick one and migrate references.
- **Thumbnails:** After adding patterns, run `python rebuild_thumbnails.py --type pattern` (or script) so `thumbnails/pattern/<id>.png` exist. Server serves these first; UI shows exact engine output.
- **Testing:** Use `python test_image_patterns.py` (or equivalent) to verify engine loads and renders sample patterns. Manually test one per category (e.g. one flame, one decade, one image) in the app: assign to zone → RENDER → inspect spec in Channels/Spec Map Inspector.
- **Gaps:** Use `docs/MAJOR_PATTERN_AUDIT.md` and this doc to decide **groups** to fill (e.g. “90s needs 2 more”, “Music needs 1 more”). Then add **only** new IDs and new impl (expansion or image), and wire UI.

---

## 6. How to build better patterns from scratch

- **Procedural (expansion):**  
  1. Add ID to `NEW_PATTERN_IDS` in `engine/pattern_expansion.py`.  
  2. In `engine/expansion_patterns.py`, add a branch in `_texture_expansion(shape, mask, seed, sm, variant)` that matches your variant (e.g. `if "my_new_pattern" in variant:`).  
  3. Build a float32 (H,W) pattern in [0,1] using helpers (`_get_grid`, `_radial_starburst`, `_stripe_diagonal`, `_flame_tongues`, `_noise_simple`, etc.) or new geometry.  
  4. Return `_pack(val, R_range, M_range)` (or the dict with pattern_val, R_range, M_range, CC).  
  5. Add a matching branch in `_paint_expansion(..., variant)` if the pattern should tint/darken paint (e.g. lava glow, carbon darken).  
  6. Add UI entry in PATTERNS and the right PATTERN_GROUPS in `paint-booth-1-data.js`.

- **Image-based:**  
  1. Create a tileable PNG (grayscale or RGB; bright = pattern, dark = base). Optional alpha.  
  2. Put it in `assets/patterns/<category>/<id>.png`.  
  3. Add `(category, id)` to `_img_pats` in `engine/registry.py`.  
  4. Add UI entry. No new Python texture code; R_range/M_range for image patterns can be fixed in the loader or in a small lookup if you introduce per-id ranges later.

- **Quality bar:**  
  - Readable at 2048×2048 (or your target res).  
  - No obvious tiling seam (procedural: periodic; image: seamless).  
  - R_range/M_range chosen so the pattern is visible in spec without destroying the base feel.  
  - Name and category consistent with existing naming and PATTERN_GROUPS.

---

## 7. File reference (quick)

| What | Where |
|------|--------|
| Pattern registry build | `engine/registry.py` |
| Legacy PATTERN_REGISTRY + texture_* / paint_* | `shokker_engine_v2.py` |
| Expansion IDs | `engine/pattern_expansion.py` → NEW_PATTERN_IDS |
| Expansion texture/paint per variant | `engine/expansion_patterns.py` → _texture_expansion, _paint_expansion, _texture_reactive |
| Image pattern load | `engine/render.py` → _load_image_pattern |
| Compose (base + pattern → spec) | Monolith / `engine/compose.py` → compose_finish |
| UI PATTERNS / PATTERN_GROUPS | `paint-booth-1-data.js`, `_ui_finish_data.js` |
| Pattern assets (PNG) | `assets/patterns/<category>/`, `assets/patterns/_placeholders/` |
| Design / audit docs | `docs/PATTERN_EXPANSION_DESIGN.md`, `docs/MAJOR_PATTERN_AUDIT.md`, `docs/ADD_CUSTOM_IMAGE_PATTERNS.md` |

---

## 8. Next steps (surgical work)

- Use this doc + MAJOR_PATTERN_AUDIT + PATTERN_EXPANSION_DESIGN when you get direction on “build X” or “fix group Y”.
- For each new pattern: **new ID + new implementation** (expansion branch or new image). Check registry and NEW_PATTERN_IDS for duplicates before adding.
- After changes: export finish IDs, rebuild pattern thumbnails, and spot-check in the app and in the Spec Map Inspector.
