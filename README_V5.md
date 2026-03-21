# Shokker Paint Booth V5
## Quick Start

```powershell
cd "c:\Shokker Paint Booth V5"
# If using Cursor workspace: cd "d:\Cursor - Shokker Paint Booth GOLD\Shokker Paint Booth V5"
python server_v5.py
# Open: http://localhost:59876
```

V5 default: `http://localhost:59876`. For a second instance use `SHOKKER_PORT=59877 python server_v5.py`. V4 (backup) used 59876 from:
`c:\Shokker Paint Booth - AntiGravity`

**Build V5 EXE:** From the V5 folder run `pyinstaller shokker-server-v5.spec` or `python _build_v5.py`. Output: `dist/shokker-paint-booth-v5.exe`.

---

## Front-End Structure (easier to work with)

The UI is split so no single file is huge:

| File | Purpose |
|------|--------|
| `paint-booth-v2.html` | Shell (~1,370 lines): layout, modals, script tags |
| `paint-booth-v2.css` | All styles (~4,720 lines) |
| `paint-booth-1-data.js` | Finish data, TGA decoder, server merge |
| `paint-booth-2-state-zones.js` | State, init, zone list/detail, setters, config |
| `paint-booth-3-canvas.js` | File picker, paint preview, eyedropper, wand, spatial, zoom |
| `paint-booth-4-pattern-renderer.js` | Client-side finish preview (canvas renderers) |
| `paint-booth-5-api-render.js` | ShokkerAPI, render, history gallery |
| `paint-booth-6-ui-boot.js` | Modals, NLP chat, shortcuts, boot |

Scripts load in order 1→6; later files depend on earlier ones.

---

## Where To Fix Things

| Problem | File | What To Look For |
|---|---|---|
| CS Cool wrong colors | `engine/color_shift.py` | Section 2 → `paint_cs_cool` |
| CS Deep Ocean recoloring base | `engine/color_shift.py` | Section 3 → `paint_cs_deepocean` |
| Any CS Duo is brown/wrong | `engine/color_shift.py` | Section 5 → `CS_DUO_DEFS` |
| Fusion (Halo, Sparkle) broken | `engine/fusions.py` | Known issues section at top |
| Standard finish wrong spec | `engine/finishes.py` | Spec Values Reference table |
| Noise/color matching broken | `engine/core.py` | `multi_scale_noise`, `build_zone_mask` |
| Finish ID not found | `engine/registry.py` | Print `MONOLITHIC_REGISTRY.keys()` |
| PARADIGM materials | `engine/paradigm.py` → `shokker_paradigm_expansion.py` | |
| 24K Arsenal finishes | `engine/arsenal.py` → `shokker_24k_expansion.py` | |
| Server routes broken | `server_v5.py` | |

---

## Engine File Map

```
engine/
  __init__.py    [2.3 KB]  Package entry — module map and re-exports
  core.py       [18.4 KB]  Primitives: noise, TGA, color analysis
  color_shift.py[35.3 KB]  ALL Color Shift (adaptive + presets + 75 duos)
  fusions.py    [10.3 KB]  ALL 150 Fusions — bridge + fix guides
  finishes.py    [6.3 KB]  Standard finishes — bridge + spec reference
  arsenal.py     [1.7 KB]  24K Arsenal bridge
  paradigm.py    [1.6 KB]  PARADIGM bridge
  registry.py    [7.8 KB]  Single source of truth for all finish IDs
```

---

## How To Add A New CS Preset

1. Open `engine/color_shift.py` → **SECTION 3**
2. Copy an existing preset, rename it, change the `rgb_stops`
3. Open `engine/registry.py` → `cs_preset_overrides` dict → add one line
4. Add UI entry in `paint-booth-v2.html`

## How To Add A New Fusion

1. Open `engine/fusions.py` → add your spec_fn and paint_fn
2. Add `FUSION_REGISTRY["my_fusion_id"] = (spec_fn, paint_fn)`
3. Add to `get_fusion_group_map()` in the right category list
4. Add UI entry in `paint-booth-v2.html`
