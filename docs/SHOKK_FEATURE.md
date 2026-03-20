# SHOKK Feature — How It Works

This document describes how **SHOKK files** (`.shokk`) and the **Spec Canvas (Zone 0)** work so you can confirm the feature behaves as intended.

---

## Your understanding (correct)

1. **Save a SHOKK** → the current **spec map** (baked from the last render), **zone config**, and optionally **paint file** are packed into one `.shokk` file.
2. **Import a SHOKK** → you can bring that pack back in. The **spec map becomes the base layer** — in the UI this is called **Spec Canvas (Zone 0)** or “Under 1” (under all zone layers).
3. **Workflow**: Import the SHOKK spec as the background → optionally **load a new car file** (e.g. edited in Photoshop) as the paint on top → then **edit zone finishes** (spec mapping) on top of that. Zone edits **do not replace or overwrite** the locked spec canvas; they **merge on top** of it where each zone has pixels.

That is how it is implemented.

---

## Spec Canvas = Zone 0 (base layer)

- **Zone 0** is not a real zone in the zone list. It is the **background spec layer**.
- When you **import a spec map** (from a SHOKK or via “Import spec map”):
  - The engine sets `combined_spec` from that file (resized to match the paint resolution).
  - Then it applies **zones 1, 2, …** on top: each zone’s finish is merged into `combined_spec` only where that zone’s mask has pixels (strong mask = replace, soft = blend).
- So: **Zone 0 = imported/locked spec**. Zones above = your current zone config. They **override or blend** only in their own areas; everywhere else, the spec canvas shows through.

The banner **“SPEC CANVAS (ZONE 0)”** in the zone list appears when `importedSpecMapPath` is set (from SHOKK or manual import). It’s there to show that a locked spec is active and that “zones above override this.”

---

## Save SHOKK

- **Save SHOKK** uses the **last render job** (or the job you specify) to get:
  - **Spec**: e.g. `car_spec_XXXXX.tga` from that job (the baked spec map).
  - **Paint**: e.g. `car_num_XXXXX.tga` (optional, checkbox “Include paint”).
- It also saves **session_json** (zones, driver name, etc.).
- All of that is packed into a single `.shokk` file (e.g. zip with manifest, spec TGA, optional paint TGA, session JSON).

So yes: the **spec map** that was rendered is what gets stored and can be re-used as the base layer when you open the SHOKK later.

---

## Open SHOKK — three modes

When you **OPEN** a SHOKK (double‑click or OPEN button), you get a small dialog:

1. **Spec Map Only**  
   - Imports **only the spec map** as the **Spec Canvas (Zone 0)**.  
   - **Keeps** your current paint and zones.  
   - Use this for the **Photoshop roundtrip**: you already have a car (or new car) loaded; you just want the SHOKK’s spec as the background so further zone edits don’t touch that base.

2. **Spec + Zones (Keep Paint)**  
   - Imports the **spec map** (Zone 0) and **restores the saved zone config**.  
   - **Keeps** your current paint.  
   - Good when you want the SHOKK’s zone setup but your own car texture.

3. **Full Import (Everything)**  
   - Imports **spec + zones + paint** from the SHOKK.  
   - Replaces everything: the SHOKK’s spec becomes Zone 0, its zones are restored, and its paint is loaded as the current car (via `/api/shokk/extracted/...` so the client can fetch it).

If **no paint is loaded** when you open a SHOKK, the app skips the dialog and does **Full Import** so you get at least spec + zones + paint from the file.

---

## “Import a new car file above the current spec”

- After you’ve imported a SHOKK (e.g. **Spec Map Only** or **Spec + Zones**), the **Spec Canvas (Zone 0)** is set and stays set.
- You then **load a different car TGA** (e.g. from Photoshop) via the normal **Load car / file picker**.
- That only replaces the **paint** (color/albedo). The **imported spec** remains the base.
- Next render: **paint** = new car file, **spec** = Zone 0 (from SHOKK) with your **zone finishes** merged on top where each zone has pixels.
- So yes: you can **import the whole spec map from the SHOKK**, then **put a new car file on top**, then **edit zone spec mapping** without that editing replacing the locked Zone 0 spec.

---

## Where it’s implemented

| What | Where |
|------|--------|
| SHOKK save/open UI, import modes | `paint-booth-7-shokk.js` |
| Spec Canvas banner (Zone 0), `importedSpecMapPath`, clear | `paint-booth-2-state-zones.js` |
| Render request sends `import_spec_map` | `paint-booth-5-api-render.js`, `paint-booth-3-canvas.js` |
| Server passes `import_spec_map` to engine | `server.py` (preview + full render) |
| Engine: load spec as base, then merge zones | `shokker_engine_v2.py`: `build_multi_zone()`, `preview_render()` — `combined_spec` from file then zone loop |
| Config persistence (imported spec path) | Client: `getConfig()` / `loadConfigFromObj()`; server: POST `/api/config` with `imported_spec_path` |

So the SHOKK feature is wired so that: **saved spec map → becomes Zone 0 when imported → you can load a new car on top and keep editing zones without overwriting that base spec.**
