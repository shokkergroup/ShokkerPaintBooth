# Spec Sculpt — SHOKK THE WORLD paint-trace (2026-06-02)

## Problem

Owner screenshot: 24 World previews on the Chevy truck looked like **full-frame spec wallpaper**
(spirals, dragons, seismic bands) — not **paint-aware** spec that follows body panels, decals, and
voids the way Viva Mexico teaches.

Regression metrics (`scripts/spec_sculpt_world_selfcheck.py`) already passed **luminance**
paint-awareness (avg paw ~0.58) because global catalog patterns still correlate weakly with paint
brightness — but they do **not** trace graphics.

## Root cause

1. `pick_diverse` chooses real SPB finish ids (good material diversity).
2. `blend_registered_specs_float` renders each finish on **mask = ones** → identical UV tiling on
   every car.
3. `apply_paint_linked_emphasis` (fix#3–#9) adds gentle coupling; not enough to suppress finish
   wallpaper.

Skipping full `_pre_adjust_viva_mexico_spec` avoided **grid flash** (2026-06-01 pivot) but also
removed **ridge/crest tracing**.

## Fix (fix#13) — `engine/spec_sculpt/paint_trace.py`

Pipeline on every **catalog** `scratch_spec_from_any_paint` call (World batch + Catalog mode):

| Step | Function | Role |
|------|----------|------|
| 1 | `edge_gated_catalog_detail` | Low-pass = catalog material; high-pass × paint edge gate |
| 2 | `imprint_scratch_highpass` | Paint scratch detail band imprinted on gated high-pass |
| 3 | `spatial_envelope_catalog` | Void panels → matte; graphics keep finish character |
| 4 | `apply_paint_linked_emphasis` | Existing per-look emphasis (batch cycles modes) |
| 5 | `apply_paint_trace_prepass` | Viva ridge/crest/chroma/void — **no dot/octave grids** |
| 6 | `finalize_traced_spec_u8` | Post void clamp with ridge protect |

Skeleton **full-channel fuse** was tried first; it homogenized the 24 picks (minpair &lt; 150).
High-pass imprint gives tracing without killing diversity.

## Verify (no server restart required)

```bash
python scripts/spec_sculpt_world_selfcheck.py
python scripts/spec_sculpt_world_contact_sheet.py --out _perf/shokk_world_paint_trace.png
```

Live Spec Sculpt UI uses `/api/spec-sculpt/batch` → **restart Flask** after pulling engine changes.

## Tuning (in `engine/spec_sculpt/generate.py`)

- `edge_gated_catalog_detail(..., strength=1.08)`
- `imprint_scratch_highpass(..., mix=0.48)`
- `spatial_envelope_catalog(..., strength=0.92)`
- `apply_paint_trace_prepass(..., strength=1.05, detail_scale=1.48)`

Raise mix / strength if void panels still show finish wallpaper; lower if looks become too samey.
