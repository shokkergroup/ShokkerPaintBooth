# COLORSHOXX — Angle-Reveal Doctrine

**Owner mandate 2026-05-27 (SPB rate portal, `cx_electric_storm` car screenshots)**

## What iRacing can and cannot do

iRacing **cannot** perform true hue-shifting paint. The COLORSHOXX promise is **not** chameleon rainbow rotation.

The promise **is**:

1. **Bury colors** in a near-black (or near-neutral) paint base.
2. **Marriage with spec** — fine 8–32px pins on the 2048² canvas with extreme M/R/CC swings.
3. **Angle-dependent reveal** — at normal incidence the car reads as one color (often black). At glancing / specular angles, buried colors **flash through** and features **appear and disappear** panel-to-panel across the body.

This is the needle-mover. Not macro blobs. Not smooth duo gradients alone.

## Reference finish: `cx_electric_storm`

Owner verdict: the *design* still needs work (does not yet scream “Tesla currents”), **but the car photos prove the technique**:

- Head-on / flat panels → reads **black / thundercloud**
- Pan front-to-back along curved panels → **purple / violet** buried color erupts
- Features vanish and reappear as light angle changes — because spec pins are **fine enough** that each body panel catches a different subset of glints

The purple is not a paint “color shift” — it is **hidden violet micro-flake + spec flash** married at fine scale. The aqua/violet reference profile (`9015`) plus `_cx_fine_spec_pins` + directional fields create the illusion.

## Next level (the COLORSHOXX holy grail)

**Multi-directional buried palette:**

| Pan / light direction | Hidden color revealed |
|-----------------------|------------------------|
| Front → back (U axis) | Color A (e.g. purple) |
| Side / other axis (V) | Color B (e.g. electric blue) |
| Diagonal | Color C (e.g. green accent) |

Straight-on may still read as **one** buried base. Each travel direction unlocks a **different** hidden color. Still not true hue shift — **spec + paint gate** at fine scale.

## Implementation contract (`structural_color.py`)

Helpers (2026-05-27):

| Helper | Role |
|--------|------|
| `_cx_fine_spec_pins` | 8–32px spec pin lattice — no macro shop tubes |
| `_cx_directional_mask` | U / V / diagonal bias fields for pan-direction reveals |
| `_cx_buried_reveal_gate` | Pins + micro sparkle — color only exists on gate |
| `_cx_angle_reveal_spec` | Married spec: extreme M/R on gated directional flashes |
| `_cx_apply_angle_reveals` | Paint overlay: dark base + directional buried RGB layers |

### Recipe for every COLORSHOXX finish

1. **Base** — push matte zone to `(0.02–0.06)` luma unless finish identity requires otherwise.
2. **Reveals** — 2–3 `(rgb, axis, strength)` tuples; axes must differ (`u`, `v`, `diag_a`, `diag_b`).
3. **Gate density** — `0.005–0.008` on 2048²; 5+ pin layers.
4. **Spec** — `_cx_angle_reveal_spec` or custom override; ΔM ≥ 200 on flash pins.
5. **Never** rely on a single smooth duo gradient alone — that reads cookie-cutter on the car.

### Auditing on car (not thumbnail)

Thumbnail lies. Validate on truck/body mesh in iRacing showroom:

- Rotate slowly — colors should **appear**, not just brighten.
- Different pan directions should prefer **different** buried hues when multi-axis reveals are configured.
- Flat hood vs curved fender should **not** show identical pattern phase (fine pins + warp).

## Related files

- `engine/paint_v2/structural_color.py` — canonical implementation
- `engine/micro_flake_shift.py` — wave-4 monolithics (override via BASE_REGISTRY when angle-reveal needed)
- `engine/dual_color_shift.py` — duo presets; prefer dedicated BASE fn for angle-reveal duos
