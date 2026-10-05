"""Grid Runner: broken perspective light architecture over a digital void.

SPB-105 / NU-V4-2 / 2026-08-27. Owner verdict: v3 lacked Oil Slick's
coherent SPEC mechanics and did not read as neon, Tokyo Drift, or Fast &
Furious. This uses one vanishing floor and one hard-turn trail; the grid is
perspective anatomy, not a uniformly tiled micro-packet carpet.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, FinishResult, begin, blur, coords, edge, finish, normal_light,
    pack_physical, palette_cycle, ridge, smooth, soft_noise, unit,
    warp_vortices,
)


FINISH_ID = "neon2_wireframe"
DISPLAY_NAME = "Grid Runner"
DEFAULT_SEED = 0x6A1D4E12


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    """Build a coherent perspective floor with a decisive cornering trail."""
    started = begin()
    size = int(size)
    x, y = coords(size)
    scale = size / float(WORK)
    depth = np.clip((y + 0.48) / 1.48, 0.0, 1.0)
    spread = 0.075 + 0.98 * np.power(depth, 0.84)
    u = x / spread
    floor = smooth(-0.50, -0.25, y)
    dropout_field = soft_noise(seed ^ 0xD09A, size, 74.0 * scale, 12.0 * scale)
    intact = smooth(0.34, 0.61, dropout_field)

    perspective_rails = ridge(5.8 * u + 0.20 * np.sin(2.8 * y), 0.070) * floor
    cross_phase = 13.2 * np.log2(0.105 + depth) + 0.28 * np.sin(4.0 * u)
    crossbars = ridge(cross_phase, 0.075) * floor
    grid = np.clip(np.maximum(perspective_rails, 0.88 * crossbars) * (0.30 + 0.70 * intact), 0.0, 1.0)
    dropout_gaps = grid * (1.0 - intact)

    # SPB-105 / NU-V4-2F / owner whole-car verdict: preserve the hard-turn
    # hero, but use the same vanishing architecture across the overhead half
    # and side panels. These are coherent 8-32px rails/scans, never filler.
    overhead_depth = np.clip((-y - 0.40) / 0.60, 0.0, 1.0)
    overhead_spread = 0.075 + 0.98 * np.power(overhead_depth, 0.84)
    overhead_u = x / overhead_spread
    ceiling = 1.0 - smooth(-0.62, -0.40, y)
    overhead_rails = ridge(5.4 * overhead_u - 0.18 * np.sin(2.5 * y), 0.070) * ceiling
    overhead_phase = 12.4 * np.log2(0.105 + overhead_depth) - 0.24 * np.sin(3.6 * overhead_u)
    overhead_crossbars = ridge(overhead_phase, 0.075) * ceiling
    overhead_grid = np.clip(
        np.maximum(overhead_rails, 0.86 * overhead_crossbars) * (0.36 + 0.64 * intact),
        0.0, 1.0,
    )
    side_panels = smooth(0.42, 0.88, np.abs(x))
    vector_scans = ridge(62.0 * (0.18 * x + y) + 0.55 * dropout_field, 0.075) * side_panels
    carrier_grid = np.clip(np.maximum.reduce((grid, 0.78 * overhead_grid, 0.28 * vector_scans)), 0.0, 1.0)

    turn_curve = 0.37 * np.sin(2.15 * y - 0.35) + 0.10 * np.sin(5.1 * y + 0.4)
    turn_distance = x - turn_curve
    hard_turn = np.exp(-((turn_distance / 0.066) ** 2)) * floor
    turn_shoulders = np.exp(-((turn_distance / 0.20) ** 2)) * floor
    apex_nodes = ridge(29.0 * y + 2.2 * np.sin(4.0 * y), 0.12) * hard_turn
    scan_filaments = ridge(68.0 * u + 5.0 * cross_phase, 0.068) * grid
    fracture_stubs = ridge(51.0 * (x + 0.28 * y) + 0.8 * dropout_field, 0.08) * dropout_gaps
    luminous_edges = np.clip(edge(carrier_grid + 0.72 * hard_turn), 0.0, 1.0)
    # SPB-105 / NU-V4-TILE-1, 2026-08-28. The existing grid hero survives
    # reduction, but its black inter-rail field reads as empty screen space.
    # A single warped conductive clear sheet fills those rail bays; it exposes
    # only process-derived thin-film pools, lamellae and order lips, never a
    # copied Oil Slick carrier or decorative rainbow texture.
    film_x, film_y = warp_vortices(x, y, (
        (-0.55, -0.42, 0.60, 0.34), (0.30, -0.04, 0.62, -0.31),
        (-0.24, 0.58, 0.56, 0.28),
    ))
    conductive_film = unit(
        0.51 + 0.12 * film_x - 0.075 * film_y
        + 0.096 * np.sin(7.4 * film_x + 2.3 * film_y)
        + 0.062 * np.sin(13.2 * film_y - 3.8 * film_x)
        + 0.038 * np.sin(24.6 * film_x + 15.0 * film_y)
        + 0.15 * carrier_grid + 0.12 * turn_shoulders
    )
    film_slope = edge(conductive_film)
    film_lamella = ridge(
        film_x * (43.0 + 10.0 * film_slope) + film_y * (18.0 - 5.0 * film_slope),
        0.14,
    ) * (0.20 + 0.80 * (floor + ceiling))
    film_order = np.mod(2.58 * conductive_film + 0.15 * carrier_grid + 0.12 * hard_turn, 1.0)
    order_lip = np.exp(-np.minimum(film_order, 1.0 - film_order) / 0.038)
    order_lip *= 0.18 + 0.82 * (0.55 * carrier_grid + 0.45 * turn_shoulders)
    film_pool = np.exp(-((conductive_film - 0.55) / 0.18) ** 2) * (1.0 - 0.48 * film_slope)
    height = unit(
        0.44 * carrier_grid + 0.50 * hard_turn + 0.24 * turn_shoulders
        + 0.16 * luminous_edges + 0.10 * apex_nodes + 0.08 * vector_scans
        + 0.12 * film_pool + 0.10 * order_lip + 0.06 * film_lamella
    )

    def paint_view(
        travel: float,
        light_vec: tuple[float, float, float],
        grazing: float = 0.0,
    ) -> np.ndarray:
        light = normal_light(height, light_vec)
        exposure = np.clip((light + 0.55) / 1.55, 0.0, 1.0)
        optical = np.mod(
            0.68 * depth + 0.50 * overhead_depth + 0.28 * carrier_grid + 0.16 * turn_shoulders
            + travel * (0.48 + 0.52 * exposure),
            1.0,
        )
        grid_color = palette_cycle(
            optical,
            ((0.00, 0.24, 0.48), (0.00, 0.90, 1.00), (0.64, 0.96, 1.00),
             (0.80, 0.18, 1.00), (1.00, 0.12, 0.62), (0.08, 0.28, 0.65)),
        )
        paint = np.zeros((size, size, 3), np.float32)
        paint[:] = (0.002, 0.004, 0.011)
        carrier_bed = blur(carrier_grid, 13.0 * scale)
        paint += carrier_bed[..., None] * np.asarray((0.005, 0.075, 0.145), np.float32)
        paint += grid_color * (0.026 + 0.060 * conductive_film + 0.10 * film_pool + 0.050 * film_lamella)[..., None]
        paint += grid_color * (
            grid * (0.25 + 0.48 * exposure + 0.58 * float(grazing))
        )[..., None]
        paint += grid_color * (
            overhead_grid * (0.14 + 0.30 * exposure + 0.34 * float(grazing))
        )[..., None]
        paint += np.asarray((0.18, 0.42, 0.82), np.float32) * (0.15 * vector_scans)[..., None]
        paint += grid_color * (
            float(grazing) * 0.44 * blur(carrier_grid + 0.82 * turn_shoulders, 9.0 * scale)
        )[..., None]
        paint += np.asarray((0.98, 0.98, 1.00), np.float32) * (0.52 * hard_turn + 0.25 * apex_nodes)[..., None]
        paint += np.asarray((1.00, 0.08, 0.60), np.float32) * (0.24 * turn_shoulders + 0.18 * crossbars * grid)[..., None]
        paint += np.asarray((0.00, 0.88, 1.00), np.float32) * (0.24 * perspective_rails * grid + 0.17 * scan_filaments)[..., None]
        paint += np.asarray((0.58, 0.20, 1.00), np.float32) * (0.17 * fracture_stubs)[..., None]
        paint += np.asarray((0.70, 0.94, 1.00), np.float32) * (0.12 * luminous_edges)[..., None]
        paint += np.asarray((0.86, 0.94, 1.00), np.float32) * (0.095 * order_lip)[..., None]
        return np.clip(paint, 0.0, 1.0)

    paint = paint_view(0.00, (0.52, -0.42, 0.74))
    # SPB-105 / NU-V4-2R / owner verdict: v3 omitted the Oil Slick witness.
    # Grid-owned grazing reflection moves native A/B delta 0.0224 -> 0.0561.
    paint_b = paint_view(0.72, (-0.72, 0.10, 0.68), 0.52)

    conductor = np.clip(grid + 0.72 * overhead_grid + 0.24 * vector_scans + 0.66 * hard_turn, 0.0, 1.0)
    metal = np.clip(
        0.03 + 0.72 * conductor + 0.48 * apex_nodes + 0.34 * luminous_edges
        + 0.24 * scan_filaments + 0.18 * overhead_crossbars + 0.18 * order_lip
        + 0.10 * film_lamella - 0.42 * dropout_gaps,
        0.0, 1.0,
    )
    rough = np.clip(
        0.12 + 0.66 * dropout_gaps + 0.52 * fracture_stubs
        + 0.32 * np.maximum(crossbars, overhead_crossbars) + 0.30 * vector_scans
        + 0.24 * dropout_field * (floor + ceiling) + 0.20 * film_slope
        + 0.16 * film_lamella - 0.48 * hard_turn,
        0.0, 1.0,
    )
    coat = np.clip(
        0.10 + 0.68 * turn_shoulders + 0.54 * hard_turn
        + 0.30 * np.maximum(perspective_rails, overhead_rails)
        + 0.24 * blur(carrier_grid, 8.0 * scale) + 0.22 * film_pool + 0.18 * order_lip
        - 0.56 * dropout_gaps - 0.32 * fracture_stubs - 0.12 * film_lamella,
        0.0, 1.0,
    )
    spec = pack_physical(
        metal, rough, coat,
        m_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91),
        r_cuts=(0.08, 0.17, 0.27, 0.38, 0.49, 0.60, 0.71, 0.82, 0.92),
        c_cuts=(0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91),
    )
    return finish(
        started, FINISH_ID, DISPLAY_NAME, paint, paint_b, spec,
        "one full-field floor/overhead perspective lattice crossed by a broad hard-turn trail, with a conductive clear film, converging rails, crossbars, apex nodes, side scans, coherent dropouts and fracture stubs",
        {
            "M": "conductive floor and overhead rails, hard-turn trail, apex nodes, film order lips and attached luminous edges",
            "R": "strained film lamellae, coherent lattice dropouts, fractured stubs, crossbar damage, side scans and dark panel wear",
            "Cc": "mid-depth conductive-film pools, polished turn shoulders and intact perspective lattice, interrupted where the digital surface breaks",
        },
    )
