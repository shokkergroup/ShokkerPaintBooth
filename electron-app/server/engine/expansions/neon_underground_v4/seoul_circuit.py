"""Seoul Circuit — rounded city-current panels in wet midnight clear."""
from __future__ import annotations

import numpy as np

from .core import (
    FinishResult,
    WORK,
    begin,
    blur,
    coords,
    finish,
    normal_light,
    pack_physical,
    palette_ramp,
    resize_result,
    ridge,
    smooth,
    unit,
)


FINISH_ID = "neon2_circuit_city"
DISPLAY_NAME = "Seoul Circuit"
DEFAULT_SEED = 0x5E0C17

# SPB-105 / NU-V4-SC-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, actual neon, and Tokyo Drift identity.  This carrier uses
# broad unequal city panels; the fine current anatomy remains subordinate.
# NU-V4 whole-car correction: a deterministic luminous conduit network now
# carries panel current through the dark body between facades. No node beads,
# random retrace masks, edge damage, or particle quota is used.


def _rounded_box(
    x: np.ndarray,
    y: np.ndarray,
    cx: float,
    cy: float,
    half_w: float,
    half_h: float,
    angle: float,
    radius: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ca, sa = np.float32(np.cos(angle)), np.float32(np.sin(angle))
    px, py = x - cx, y - cy
    u, v = ca * px + sa * py, -sa * px + ca * py
    qx = np.abs(u) - (half_w - radius)
    qy = np.abs(v) - (half_h - radius)
    outside = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    signed = outside + np.minimum(np.maximum(qx, qy), 0.0) - radius
    face = smooth(-0.025, 0.055, -signed)
    rim = np.exp(-((signed / 0.0105) ** 2)).astype(np.float32)
    return face, rim, u


def _mix(paint: np.ndarray, color: np.ndarray, amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    return paint * (1.0 - a) + color * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Seoul Circuit requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    # Seven unequal, overlapping rounded facade plates create one broad
    # descending current rather than a repeated PCB/tile field.
    panels = (
        (-0.72, -0.61, 0.43, 0.18, -0.16, 0.075),
        (-0.28, -0.39, 0.56, 0.20, 0.10, 0.090),
        (0.35, -0.18, 0.48, 0.17, -0.08, 0.070),
        (0.70, 0.09, 0.41, 0.16, 0.17, 0.065),
        (0.24, 0.35, 0.61, 0.21, -0.12, 0.095),
        (-0.43, 0.53, 0.50, 0.18, 0.08, 0.075),
        (-0.79, 0.76, 0.34, 0.14, -0.18, 0.055),
    )
    face = np.zeros_like(x)
    rim = np.zeros_like(x)
    address = np.zeros_like(x)
    for i, row in enumerate(panels):
        f, r, u = _rounded_box(x, y, *row)
        face = np.maximum(face, f * np.float32(0.72 + 0.04 * i))
        rim = np.maximum(rim, r)
        address += f * np.mod(np.float32(0.17 * i) + 0.33 * u + 0.19 * y, 1.0)
    address = unit(address)

    # A connected city-current backbone joins every facade in cascade order,
    # plus one long return route. Segment distance keeps all conduit anatomy
    # causally attached to actual panel centers rather than filling darkness.
    links = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (1, 4))
    conduit_core = np.zeros_like(x)
    conduit_halo = np.zeros_like(x)
    conduit_lips = np.zeros_like(x)
    conduit_pulses = np.zeros_like(x)
    centers = tuple((row[0], row[1]) for row in panels)
    segments = tuple((centers[ia], centers[ib], 1.0) for ia, ib in links) + (
        (centers[0], (-1.14, -0.94), 0.62),
        (centers[3], (1.14, -0.78), 0.62),
        (centers[6], (-1.14, 1.04), 0.62),
        (centers[4], (1.14, 0.94), 0.62),
    )
    for i, ((ax, ay), (bx, by), weight) in enumerate(segments):
        dx, dy = np.float32(bx - ax), np.float32(by - ay)
        length2 = np.float32(dx * dx + dy * dy)
        travel = np.clip(((x - ax) * dx + (y - ay) * dy) / length2, 0.0, 1.0)
        px, py = ax + travel * dx, ay + travel * dy
        distance = np.hypot(x - px, y - py)
        core = np.float32(weight) * np.exp(-((distance / 0.012) ** 2)).astype(np.float32)
        halo = np.float32(weight) * np.exp(-((distance / 0.18) ** 2)).astype(np.float32)
        lips = np.float32(weight) * np.exp(-(((distance - 0.028) / 0.009) ** 2)).astype(np.float32)
        pulses = np.float32(weight) * ridge(34.0 * travel + 0.31 * i, 0.17)
        pulses *= np.exp(-((distance / 0.040) ** 2))
        conduit_core = np.maximum(conduit_core, core)
        conduit_halo = np.maximum(conduit_halo, halo)
        conduit_lips = np.maximum(conduit_lips, lips)
        conduit_pulses = np.maximum(conduit_pulses, pulses)

    junction_rings = np.zeros_like(x)
    for cx, cy in centers:
        rr = np.hypot(x - cx, y - cy)
        junction_rings = np.maximum(
            junction_rings,
            np.exp(-(((rr - 0.026) / 0.008) ** 2)).astype(np.float32),
        )

    # Deterministic 8–32px current families live on panel faces, rims, or the
    # conduit backbone; nothing is a freestanding bead or splinter.
    current_seams = rim
    scan_dashes = ridge(48.0 * (x + 0.17 * np.sin(2.8 * y)) + 7.0 * y, 0.14) * face
    bridge_slivers = ridge(34.0 * (x - 0.31 * y + 0.035 * np.sin(7.0 * y)), 0.075)
    bridge_slivers *= smooth(0.28, 0.72, face) * (0.22 + 0.78 * rim)
    retrace_cuts = ridge(57.0 * (y + 0.12 * x) + 2.0 * np.sin(6.0 * x), 0.060)
    retrace_cuts *= face
    edge_relays = ridge(57.0 * x - 15.0 * y + 0.40 * address, 0.11) * rim
    network_louvers = ridge(43.0 * (x - 0.27 * y + 0.026 * np.sin(5.2 * y))
                            + 0.48 * address, 0.15)
    network_louvers *= 0.22 + 0.78 * conduit_halo

    broad_charge = np.clip(0.48 * face + 0.92 * blur(rim, 7.5), 0.0, 1.0)
    anatomy = np.clip(
        current_seams + 0.55 * scan_dashes + 0.50 * bridge_slivers
        + 0.62 * junction_rings + 0.48 * edge_relays,
        0.0,
        1.0,
    )
    # Conduits are luminous current under the clear, not carved scratches;
    # only their broad optical halo perturbs the panel light normal.
    height = blur(0.58 * face + 0.74 * rim + 0.20 * scan_dashes
                  + 0.14 * conduit_halo, 1.35)
    light_a = smooth(-0.12, 0.70, normal_light(height, (0.62, -0.34, 0.71)))
    light_b = smooth(-0.12, 0.70, normal_light(height, (-0.55, 0.44, 0.71)))

    city_color = palette_ramp(
        np.clip(0.12 + 0.76 * address + 0.12 * y, 0.0, 1.0),
        ((0.02, 0.30, 0.34), (0.10, 1.00, 0.78), (0.92, 0.39, 0.98), (0.42, 0.22, 1.00)),
    )
    # View B traverses the opposite panel interference order: mint/cyan
    # ownership moves to faces that were lilac in A, while the displaced
    # lilac order appears on the opposite rounded shoulders.
    city_color_b = palette_ramp(
        np.clip(0.10 + 0.68 * (1.0 - address) + 0.22 * light_b + 0.08 * x, 0.0, 1.0),
        ((0.06, 0.40, 0.48), (0.16, 1.00, 0.86), (0.50, 0.30, 1.00), (1.00, 0.34, 0.88)),
    )
    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.006, 0.010, 0.030)
    ground += (0.018 * smooth(-1.0, 1.0, y))[..., None] * np.asarray((0.12, 0.10, 0.28), np.float32)

    network_address = np.mod(0.24 + 0.31 * x + 0.19 * y + 0.08 * conduit_pulses, 1.0)
    network_color_a = palette_ramp(
        network_address,
        ((0.02, 0.16, 0.24), (0.05, 0.62, 0.54), (0.36, 0.22, 0.70), (0.68, 0.20, 0.58)),
    )
    network_color_b = palette_ramp(
        np.mod(1.0 - network_address + 0.16 * light_b, 1.0),
        ((0.03, 0.20, 0.28), (0.10, 0.68, 0.60), (0.46, 0.20, 0.78), (0.76, 0.18, 0.54)),
    )
    network_energy_a = np.clip(
        0.20 * conduit_halo + 0.46 * conduit_core + 0.24 * conduit_lips
        + 0.18 * conduit_pulses + 0.11 * network_louvers,
        0.0,
        0.72,
    ) * (0.34 + 0.66 * light_a)
    network_energy_b = np.clip(
        0.21 * conduit_halo + 0.48 * conduit_core + 0.26 * conduit_lips
        + 0.20 * conduit_pulses + 0.12 * network_louvers,
        0.0,
        0.74,
    ) * (0.34 + 0.66 * light_b)
    ground_a = _mix(ground, network_color_a, network_energy_a)
    ground_b = _mix(ground, network_color_b, network_energy_b)

    energy_a = np.clip(broad_charge * (0.42 + 0.72 * light_a) + 0.62 * anatomy, 0.0, 1.0)
    energy_b = np.clip(
        broad_charge * (0.26 + 0.96 * light_b)
        + 0.62 * anatomy
        + 0.34 * face * smooth(0.30, 0.78, light_b),
        0.0,
        1.0,
    )
    paint_a = _mix(ground_a, city_color, np.clip(0.18 * face + 0.82 * energy_a, 0.0, 0.96))
    paint_b = _mix(ground_b, city_color_b, np.clip(0.12 * face + 0.88 * energy_b, 0.0, 0.97))
    hot = np.clip(rim + 0.58 * junction_rings + 0.38 * scan_dashes
                  + 0.42 * conduit_core + 0.30 * conduit_pulses, 0.0, 1.0)
    paint_a = _mix(paint_a, np.ones_like(paint_a), 0.42 * hot * light_a)
    paint_b = _mix(paint_b, np.ones_like(paint_b), 0.58 * hot * smooth(0.18, 0.76, light_b))

    metal = unit(0.05 + 0.70 * current_seams + 0.62 * conduit_core
                 + 0.48 * junction_rings + 0.42 * conduit_pulses
                 + 0.34 * edge_relays + 0.16 * face)
    rough = unit(0.10 + 0.54 * retrace_cuts + 0.46 * edge_relays
                 + 0.36 * network_louvers + 0.28 * scan_dashes
                 + 0.15 * (1.0 - np.maximum(face, conduit_halo)))
    coat = unit(0.08 + 0.72 * face + 0.48 * conduit_halo
                + 0.34 * blur(rim, 5.0) + 0.24 * conduit_lips
                - 0.46 * retrace_cuts - 0.32 * edge_relays
                - 0.28 * network_louvers)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.06, 0.11, 0.18, 0.28, 0.40, 0.54, 0.69, 0.82, 0.93),
        r_cuts=(0.08, 0.16, 0.25, 0.35, 0.46, 0.58, 0.70, 0.82, 0.92),
        c_cuts=(0.05, 0.12, 0.22, 0.34, 0.47, 0.60, 0.73, 0.85, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "smoked wet-look body clear carrying a cascading current of unequal rounded Seoul light panels",
        {
            "M": "panel seams, bridge slivers, conduit cores, pulse relays, and junction rings expose metallic current",
            "R": "deterministic retrace cuts, edge relays, network louvers, and scan bands tune the current path",
            "Cc": "rounded faces, conduit halos, return lips, and optical shoulders retain deep wet clear across the body",
        },
    )
