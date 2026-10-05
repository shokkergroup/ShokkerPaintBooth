"""FRACTURE engine — the Wovenlight ignition doctrine generalized to ANY paint.

The catalog FRACTURED finishes (engine/expansions/fractured_minds_soul_2026.py) trace
their OWN procedural geometry by re-deriving it from a shared seed, then apply this
ignition relationship to the spec map:

    Metalness  M  ~= 252   (near-chrome body)
    Clearcoat  Cc =  255   (maxed -> Fresnel flash that "ignites" at grazing angles)
    Roughness  R  =  30 off-motif (mirror) rising to ~78 along the woven motif "lanes"

The drama is the near-chrome body flaring as the car turns, with the motif read as a
woven roughness tracery. The PAINT supplies the dark albedo; the SPEC supplies the
ignition.

Spec Sculpt's "FRACTURE-ize" and Shokk Drop's FRACTURE auto-derive must ignite an
ARBITRARY user paint, where there is no shared seed to re-derive geometry from. So we
trace the REAL pixels via paint_graphic_weight (edges / crests / saturated graphics =
the livery's own "lanes") and apply the same ignition relationship to that traced field.

Returns float-or-uint8 HxWx4 spec (M, R, Cc, A) in 0..255, matching the engine's spec
contract (the same shape _spec_from_combined / authored specs return).
"""
from __future__ import annotations

import numpy as np

from engine.spec_sculpt.paint_trace import paint_graphic_weight

# Ignition constants — lifted verbatim from fractured_minds_soul_2026 (_FM_M / _FM_G_FLOOR /
# _FM_G_LANE) so a FRACTURE-ized arbitrary paint reads like a true FRACTURED finish.
_FR_M = 252.0          # metalness, near-max chrome body
_FR_G_FLOOR = 30.0     # roughness off-motif (glossy mirror)
_FR_G_LANE = 78.0      # roughness along the woven motif lanes
_FR_CC = 255.0         # clearcoat maxed -> angle-gated Fresnel ignition
# Outside-mask calm defaults (match the soul engine's inv-mask fill).
_OUT_M, _OUT_R, _OUT_CC = 4.0, 120.0, 16.0


def fracture_spec(
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    *,
    ignition: float = 1.0,
    angle_gate: float = 1.0,
    trace_strength: float = 1.0,
    calm_floor: float = _FR_G_FLOOR,
    decorrelation: float = 0.0,
    as_uint8: bool = True,
) -> np.ndarray:
    """FRACTURE the spec of an arbitrary paint.

    Dials (all safe at their defaults = a faithful FRACTURED look):
      ignition       0..2  overall drama — lane contrast + how hard the motif pops.
      angle_gate     0.25..2  tightness of the ignition (higher = sharper, more concentrated lanes).
      trace_strength 0..2  how strongly the paint's own geometry drives the motif lanes.
      calm_floor     14..110  off-motif roughness (lower = glossier mirror body).
      decorrelation  0..1  pushes M / R / Cc motifs apart so the channels aren't carbon copies
                            (helps each FRACTURE-ized look stay distinct + clears the uniqueness gate).
    """
    tex = np.asarray(tex_rgb_hwc, dtype=np.float32)
    if float(tex.max() if tex.size else 0.0) > 1.5:
        tex = tex / 255.0
    tex = np.clip(tex[:, :, :3], 0.0, 1.0)
    h, w = tex.shape[:2]

    m = np.asarray(mask_hw, dtype=np.float32)
    if m.ndim == 3:
        m = m[:, :, 0]
    m = np.clip(m, 0.0, 1.0)

    ignition = float(np.clip(ignition, 0.0, 2.0))
    angle_gate = float(np.clip(angle_gate, 0.25, 2.0))
    trace_strength = float(np.clip(trace_strength, 0.0, 2.0))
    calm_floor = float(np.clip(calm_floor, 14.0, 110.0))
    decorrelation = float(np.clip(decorrelation, 0.0, 1.0))

    # Trace the paint's own geometry -> the woven "lane" field the ignition rides on.
    graphic, gray, edge_n, dark_interior, streak = paint_graphic_weight(tex, m)
    lane = (
        graphic * (0.55 + 0.45 * trace_strength)
        + np.power(np.clip(edge_n, 0.0, 1.0), 0.6) * 0.50 * trace_strength
        + streak * 0.40 * trace_strength
    )
    lane = np.clip(lane, 0.0, 1.0)
    # angle_gate sharpens the ignition (higher = tighter, more dramatic lanes).
    lane = np.power(lane, 1.0 / angle_gate)
    lane = np.clip(lane * (0.70 + 0.55 * ignition), 0.0, 1.0)

    # A decorrelated companion field (lane shifted) so M / R / Cc motifs differ.
    lane_dc = np.clip(np.power(lane, 1.0 + 0.9 * decorrelation) * (1.0 - 0.30 * decorrelation), 0.0, 1.0)

    # Metalness: near-chrome body, tiny dip along lanes for motif definition.
    M = _FR_M - lane * (18.0 * (0.6 + 0.4 * ignition))
    # Roughness: calm/glossy floor off-motif, rises along the lanes (the woven tracery).
    g_lane = _FR_G_LANE + decorrelation * 34.0
    R = calm_floor + (g_lane - calm_floor) * lane
    # Clearcoat: maxed (Fresnel ignition); decorrelation pulls a faint motif into it.
    Cc = _FR_CC - lane_dc * (28.0 * decorrelation)

    out = np.zeros((h, w, 4), dtype=np.float32)
    inv = 1.0 - m
    out[:, :, 0] = np.clip(M * m + _OUT_M * inv, 0.0, 255.0)
    out[:, :, 1] = np.clip(np.clip(R, 14.0, 140.0) * m + _OUT_R * inv, 0.0, 255.0)
    out[:, :, 2] = np.clip(Cc * m + _OUT_CC * inv, 0.0, 255.0)
    out[:, :, 3] = 255.0

    if as_uint8:
        return np.clip(np.round(out), 0, 255).astype(np.uint8)
    return out
