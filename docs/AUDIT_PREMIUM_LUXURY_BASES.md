# Premium Luxury Base Finishes — Audit & Recommendations

Audit date: 2026-03. Reference: UI screenshot (10 finishes, two-tone swatches) and current data in `paint-booth-0-finish-data.js` + `engine/base_registry_data.py` + `engine/expansions/arsenal_24k.py`.

---

## 1. Current state (all 10)

| # | ID | Display name | Short desc (UI) | Swatch (hex) | Notes |
|---|----|--------------|-----------------|-------------|--------|
| 1 | bentley_silver | Bentley Silver | Rolls-Royce/Bentley ultra-fine silver | #ccccdd | OK; slight pink/silver in render. |
| 2 | bugatti_blue | Bugatti Blue | Bugatti Bleu de France deep two-tone | #2244aa | OK; two-tone blue/green in render. |
| 3 | ferrari_rosso | **Magma Core** | Surface cooling magma with deep incandescent red subsurface scattering | #880000 | Name/desc intentionally not “Ferrari”; ID kept for engine. |
| 4 | koenigsegg_clear | Koenigsegg Clear | Clear carbon visible weave (Koenigsegg style) | #333333 | Dark neutral; screenshot shows brown/gold weave → swatch can suggest warmth. |
| 5 | lamborghini_verde | Lambo Verde | Lamborghini Verde Mantis electric green | #33cc55 | OK. |
| 6 | maybach_two_tone | Maybach Two-Tone | Mercedes-Maybach duo-tone luxury split | #aabbcc | Too light; screenshot is dark grey + brown → swatch should be darker. |
| 7 | mclaren_orange | McLaren Orange | McLaren Papaya Spark vivid orange | #ee6622 | OK. |
| 8 | pagani_tricolore | Pagani Tricolore | Pagani chameleon tricolore shift paint | #8844aa | OK for “shift”; could use a more neutral mid-tone. |
| 9 | porsche_pts | Porsche PTS | Porsche Paint-to-Sample custom deep coat | #336688 | Screenshot: dark grey + purple shimmer → swatch can be darker with purple hint. |
| 10 | satin_gold | Satin Gold | Satin gold metallic warm sheen | #bb9933 | OK; can nudge to richer gold. |

---

## 2. Findings

- **Naming**: Display names and short descriptions are consistent with the screenshot and brand intent. “Magma Core” (ferrari_rosso) is correctly the UI name; engine can keep longer/technical desc.
- **Category**: All 10 are in `BASE_GROUPS["Premium Luxury"]` in `paint-booth-0-finish-data.js`; order matches the list above.
- **Engine**: All 10 exist in `engine/base_registry_data.py` and/or `engine/expansions/arsenal_24k.py` with `spec_premium_luxury` and appropriate paint_fn. `satin_gold` lives elsewhere in base_registry (e.g. paint_warm_metal) and is correct.
- **Swatches**: The UI two-tone swatches are likely server-rendered thumbnails. The single hex in BASES is used as fallback and for “primary” color; several hexes could be tuned to better match the screenshot’s dominant (left) tone.

---

## 3. Recommended changes (display + swatch only)

Apply in **`paint-booth-0-finish-data.js`** only (no ID or engine changes).

| ID | Current swatch | Suggested swatch | Reason |
|----|----------------|------------------|--------|
| koenigsegg_clear | #333333 | #3d3020 | Dark brown/gold tint to match visible weave. |
| maybach_two_tone | #aabbcc | #4a4035 | Warm dark grey-brown (primary of duo-tone). |
| porsche_pts | #336688 | #2a2438 | Dark grey with purple hint (PTS deep coat). |
| satin_gold | #bb9933 | #c9a227 | Slightly richer gold (optional). |

**Optional (lower priority):**

- **magma_core (ferrari_rosso)**: #880000 → #6a1020 (dark red with slight purple for “cooling”).
- **pagani_tricolore**: #8844aa → #5c5c6a (neutral mid for tricolore shift).

**Leave as-is:** bentley_silver, bugatti_blue, lamborghini_verde, mclaren_orange (already good).

---

## 4. Description tweaks (optional)

- **Porsche PTS**: Add “metallic” if you want to stress depth: e.g. “Porsche Paint-to-Sample custom deep metallic coat” (current “custom deep coat” is fine).
- **Koenigsegg Clear**: Already clear; no change needed.
- **Maybach Two-Tone**: “duo-tone luxury split” is good; no change.

---

## 5. What not to change

- **IDs**: Do not rename `ferrari_rosso` → `magma_core`; engine and registries use the ID; display name “Magma Core” is correct in BASES.
- **Engine entries**: base_registry_data.py and arsenal_24k.py desc/paint_fn are separate from UI; only adjust if you want backend copy to match “Magma Core” naming (e.g. desc “Magma Core – surface cooling magma…”).
- **Category order**: Current order is logical; no change unless you want a specific visual order (e.g. brand alphabetical).

---

## 6. Summary

- **Swatch updates (recommended):** koenigsegg_clear, maybach_two_tone, porsche_pts (and optionally satin_gold, ferrari_rosso, pagani_tricolore) in `paint-booth-0-finish-data.js`.
- **Copy:** Descriptions are already consistent with the screenshot; only optional Porsche PTS tweak.
- **Wiring:** All 10 Premium Luxury bases are correctly wired; no structural changes needed.
