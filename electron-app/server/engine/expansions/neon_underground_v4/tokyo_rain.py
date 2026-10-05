"""Tokyo Rain — broad sign reflections pulled vertically through wet clear.

SPB-105 / NU-V4 tick 4 + whole-car rain pass / 2026-08-27. Owner rejected
v3's samey dark microtexture, then called this carrier "real potential" if its
2048 field gained dense smart detail with no wasted zones. Every added mark is
therefore attached to rain flow, a sign bank, a drainage rim or a pooled film;
there is no freestanding speckle, distress or brightness-quota filler.
"""
from __future__ import annotations

import numpy as np

from .core import (
    WORK, begin, coords, edge, finish, normal_light, pack_physical,
    palette_cycle, ridge, smooth, soft_noise, unit,
)


ID = "neon2_rain"
NAME = "Tokyo Rain"
RAIN_A = ((1, 5, 14), (2, 44, 88), (0, 217, 255), (185, 252, 255),
          (255, 41, 175), (117, 23, 255), (255, 71, 89), (5, 17, 43))
RAIN_B = ((2, 4, 12), (51, 7, 91), (255, 31, 181), (255, 226, 248),
          (0, 235, 230), (0, 111, 207), (151, 40, 255), (3, 22, 45))


def build(seed: int = 4307, size: int = WORK):
    started = begin()
    x, y = coords(size)
    # Each unequal Gaussian is a sign bank; vertical wet drag gives it a broad
    # reflection territory without drawing literal text or city scenery.
    centers = (-0.82, -0.47, -0.08, 0.29, 0.66, 0.91)
    widths = (0.15, 0.22, 0.13, 0.25, 0.16, 0.11)
    weights = (0.75, 1.00, 0.63, 0.88, 0.71, 0.52)
    columns = np.zeros_like(x)
    chroma_phase = np.zeros_like(x)
    for i, (cx, width, weight) in enumerate(zip(centers, widths, weights)):
        warped_x = x + 0.055 * np.sin((4.1 + i * 0.37) * y + i)
        bank = np.exp(-((warped_x - cx) / width) ** 2)
        vertical = 0.48 + 0.52 * np.exp(-((y - (-0.52 + 0.19 * i)) / (0.72 + 0.07 * i)) ** 2)
        columns += weight * bank * vertical
        chroma_phase += bank * (0.13 + i * 0.161)
    columns = unit(columns)
    wet_wave = (0.52 + 0.19 * np.sin(4.6 * y + 1.8 * x)
                + 0.10 * np.sin(11.3 * y - 3.7 * x)
                + 0.055 * np.sin(23.1 * y + 7.2 * x))
    film = unit(0.55 * columns + 0.45 * wet_wave)
    drag = ridge(y * 7.3 + 0.44 * np.sin(5.1 * x) + 0.17 * film, 0.19) * columns

    # SPB-105 / NU-V4 whole-car rain pass. The earlier ultra-thin horizontal
    # ridge multiplied by detail noise broke into artifact dots at 2048. These
    # 8–32px-native structures instead share one gravity/shear history:
    # continuous rain ribbons, their paired capillary rims, broader drainage
    # runnels and fine reflection breaks inside the actual sign banks.
    rain_load = 0.34 + 0.66 * soft_noise(seed + 5, size, 0.052 * size)
    shear_axis = (x - 0.118 * y + 0.030 * np.sin(7.4 * y + 1.6 * film)
                  + 0.014 * np.sin(17.2 * y - 2.3 * columns))
    rain_phase = 52.0 * shear_axis + 0.42 * wet_wave
    rain_core = ridge(rain_phase, 0.20)
    rain_rims = np.maximum(ridge(rain_phase - 0.27, 0.11),
                           ridge(rain_phase + 0.27, 0.11))
    rain = rain_core * rain_load * (0.46 + 0.54 * film)
    capillary_rim = rain_rims * rain_load * (0.39 + 0.61 * film)

    drain_axis = (x - 0.072 * y + 0.052 * np.sin(4.9 * y + 0.8 * wet_wave)
                  + 0.018 * np.sin(12.6 * y + 2.1 * columns))
    drain_phase = 34.0 * drain_axis + 0.58 * film
    drain_body = ridge(drain_phase, 0.30) * smooth(0.24, 0.82, film)
    drain_rim = np.maximum(ridge(drain_phase - 0.34, 0.13),
                           ridge(drain_phase + 0.34, 0.13))
    drain_rim *= smooth(0.20, 0.78, film)

    sign_louvers = np.zeros_like(x)
    for i, (cx, width) in enumerate(zip(centers, widths)):
        signed_bank = (x + 0.055 * np.sin((4.1 + i * 0.37) * y + i) - cx) / width
        bank_skin = np.exp(-(signed_bank ** 4))
        louver_phase = (43.0 + 3.0 * (i % 3)) * y + 0.55 * signed_bank + 0.37 * i
        sign_louvers += bank_skin * ridge(louver_phase, 0.18)
    sign_louvers = np.clip(sign_louvers, 0.0, 1.0) * (0.28 + 0.72 * columns)

    reflection_breaks = ridge(44.0 * y + 1.8 * columns
                              + 0.46 * np.sin(9.0 * x), 0.16)
    reflection_breaks *= smooth(0.20, 0.76, drag + 0.45 * columns)
    ripple = np.zeros_like(x)
    pool = np.zeros_like(x)
    for cx, cy, radius in ((-0.53, 0.35, 0.31), (0.18, 0.58, 0.25), (0.71, 0.19, 0.21)):
        rr = np.sqrt((x - cx) ** 2 + ((y - cy) * 1.55) ** 2)
        pool_skin = np.exp(-((rr - radius) / 0.15) ** 2)
        pool += pool_skin
        ripple_phase = (rr - radius) * 32.0
        # Paired ring shoulders keep the puddles readable without adding dots.
        ring_pair = np.maximum(ridge(ripple_phase - 0.23, 0.11),
                               ridge(ripple_phase + 0.23, 0.11))
        arc_gate = 0.56 + 0.44 * smooth(-0.55, 0.62, (x - cx) / (rr + 1e-4))
        ripple += ring_pair * pool_skin * arc_gate
    pool = np.clip(pool, 0.0, 1.0)
    ripple = np.clip(ripple, 0.0, 1.0)
    runoff_rim = smooth(0.50, 0.79, edge(columns + 0.22 * drag))
    # Fine anatomy changes local material response below, but does not emboss
    # the broad wet-film carrier; that would turn coherent rain into a grid.
    thickness = unit(0.20 + 0.53 * film + 0.17 * columns + 0.09 * drag
                     + 0.055 * pool + 0.030 * ripple)
    slope = edge(thickness)
    # A sign bank keeps a recognizable color as rain carries it through the
    # clear. The original multi-order wrap turned every bank into a repeating
    # psychedelic ribbon at 128px; this is one restrained thin-film drift,
    # with order boundaries still available where real thickness changes.
    spectral = np.mod(0.34 * thickness + chroma_phase + 0.10 * drag
                      + 0.014 * ripple, 1.0)
    order_jump = ridge(spectral, 0.047) * (0.30 + 0.70 * columns)

    def render(angle_b: bool) -> np.ndarray:
        light = normal_light(thickness + 0.030 * ripple,
                             (-0.46, 0.49, 0.74) if angle_b else (0.51, -0.41, 0.72))
        color = palette_cycle(spectral + (0.27 if angle_b else 0.0), RAIN_B if angle_b else RAIN_A)
        asphalt = np.stack((0.008 + 0.026 * film, 0.014 + 0.032 * film,
                            0.025 + 0.060 * film), axis=2)
        # SPB-105 / NU-V4-TILE-1, 2026-08-28. At picker scale the first
        # treatment collapsed wet film and optical-order lips into an overly
        # bright psychedelic field. Keep the same sign/rain causality but
        # reserve the highest return for actual rims and rain deformation so
        # the card reads as premium black-wet lacquer with neon inside it.
        energy = np.clip(0.042 + 0.29 * columns + 0.14 * drag + 0.15 * runoff_rim
                         + 0.070 * ripple + 0.024 * pool
                         + 0.075 * order_jump + 0.12 * np.maximum(light, 0.0), 0.0, 0.92)
        detail_return = (0.135 * rain + 0.108 * capillary_rim
                         + 0.070 * drain_body + 0.072 * drain_rim
                         + 0.038 * sign_louvers + 0.040 * reflection_breaks
                         + 0.030 * order_jump)
        wet_glint = 0.78 * color + 0.22 * np.asarray((0.35, 0.62, 0.68), np.float32)
        return np.clip(asphalt + color * energy[..., None]
                       + wet_glint * detail_return[..., None], 0.0, 1.0)

    metal = unit(0.39 * (1.0 - thickness) + 0.22 * runoff_rim + 0.16 * rain
                 + 0.14 * capillary_rim + 0.18 * drain_rim
                 + 0.12 * sign_louvers + 0.12 * order_jump)
    rough = unit(0.27 * slope + 0.23 * rain + 0.22 * capillary_rim
                 + 0.17 * runoff_rim + 0.15 * ripple + 0.12 * reflection_breaks
                 + 0.11 * sign_louvers + 0.12 * drag - 0.18 * drain_body)
    coat = unit(0.37 * film + 0.25 * columns + 0.20 * order_jump
                + 0.20 * pool + 0.14 * drain_body + 0.13 * ripple
                - 0.18 * rain - 0.14 * capillary_rim - 0.12 * runoff_rim)
    return finish(started, ID, NAME, render(False), render(True), pack_physical(metal, rough, coat),
                  "unequal sign-color banks dragged through a whole-field rain-sheared wet asphalt film",
                  {"M": "sign louvers, paired runoff rims, rain lips and drainage shoulders",
                   "R": "rain ribbons, capillary edges, reflection breaks, ripples and film slope",
                   "Cc": "pooled sign reflections, drainage bodies and optical wet-film shoulders"})
