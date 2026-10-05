# FRACTURED HOUDINI H1 — Veiled Skull I33 P18

Status: **live-development candidate; not accepted**.

## Proven locally

- Neutral paint carrier is generated independently from the hidden masks;
  hidden anatomy is authored only through metallic / roughness / clearcoat.
- Full-canvas layout: 32 non-grid, varied ornamental skull reliefs, each built
  from 8–32px-native crown, cheek, socket, nose, teeth, and curl components.
- Direct 2048² route: `0.695s`; paint sigma `0.1053`; M/R/Cc sigma
  `49.59 / 46.58 / 60.32`.
- Exact engine picker path: 2048 source → 1024 preview → 48px split in
  `1.483s` wall time; corresponding 256px standard is generated from that
  same engine render.
- Paint-coloured neutral/grazing and independent chrome/satin/clearcoat/mixed
  diagnostics are in `_houdini_proof/`. They are explicitly **not** track
  evidence.
- Root and Electron bridge/module/standard/picker assets are SHA matched.
- `scripts/spb_verify_protected_hologram_metal.py` passes.

## M7 applicability

No H1/Houdini route exists in `scripts/spb_workbook_compute_m7.py`, its M1
companion, or `_workbook_metrics/m7_composite.json`. Therefore M7 cannot be
claimed for this material-only experimental card. Direct channel variance and
actual lighting behavior are the measurable local gates.

## Still required before acceptance

1. Four same-location iRacing captures: neutral, chrome reflection, satin or
   alternate angle, and relief-recede—per `HOUDINI_H1_TRACK_CAPTURE_PROTOCOL.md`.
2. The motif must emerge/recede/reorganize under those frames without reading
   as paint/decal art or uniformly brightening.
3. Official picker-manifest writer completion. The visual static thumbnails
   are engine-faithful; the stale manifest bookkeeping is not a visual bake.

