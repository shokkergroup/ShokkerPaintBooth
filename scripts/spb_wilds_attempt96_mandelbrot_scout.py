# -*- coding: utf-8 -*-
"""Three deterministic Mandelbrot deposition contacts for attempt 96.

Paint-only 512² screen. No registry/spec/runtime mutation and no acceptance.
"""
from pathlib import Path

import cv2
import numpy as np


OUT = Path("_wilds_fullres_progress_20260824/attempt96_mandelbrot_scout")
OUT.mkdir(parents=True, exist_ok=True)
N = 512
PALETTE = np.asarray([
    (4, 3, 15), (17, 7, 38), (37, 12, 61), (63, 18, 80), (91, 26, 92),
    (121, 36, 96), (151, 49, 94), (179, 66, 87), (203, 87, 79),
    (221, 112, 75), (233, 141, 82), (235, 171, 99), (226, 199, 125),
    (208, 222, 158), (180, 237, 199),
], np.float32) / 255.0


def ramp(t):
    u = np.clip(t, 0, 1) * 14
    i = np.minimum(u.astype(np.int32), 13)
    f = (u - i)[..., None]
    return PALETTE[i] * (1 - f) + PALETTE[i + 1] * f


def render(cx, cy, span, iterations):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = (cx + (xx / (N - 1) - .5) * span
         + 1j * (cy + (yy / (N - 1) - .5) * span)).astype(np.complex128)
    z = np.zeros_like(c)
    escape = np.full((N, N), iterations, np.float32)
    smooth = np.zeros((N, N), np.float32)
    active = np.ones((N, N), bool)
    trap = np.full((N, N), 9.0, np.float32)
    for k in range(iterations):
        z[active] = z[active] * z[active] + c[active]
        trap[active] = np.minimum(trap[active], np.abs(z[active].real * .61 + z[active].imag * .79).astype(np.float32))
        mag = np.abs(z)
        newly = active & (mag > 4)
        if newly.any():
            escape[newly] = k
            smooth[newly] = k + 1 - np.log2(np.log2(np.maximum(mag[newly], 4.0001)))
        active[newly] = False
        if not active.any():
            break
    field = np.where(escape < iterations, smooth / iterations, 0)
    field = cv2.GaussianBlur(field.astype(np.float32), (0, 0), 1.7)
    trap = cv2.GaussianBlur(np.clip(trap, 0, .25) / .25, (0, 0), 1.4)
    gy, gx = np.gradient(field)
    travel = (field * 7.9 + trap * .23 + gx * .19 - gy * .13) % 1
    shade = np.clip(.21 + .67 * (1 - field) + .22 * (1 - trap), .08, 1.04)
    image = ramp(travel) * shade[..., None]
    image[active] *= .04
    return np.clip(image * 255 + .5, 0, 255).astype(np.uint8)


CASES = (
    ("seahorse_5e4", -.743643887037151, .13182590420533, .00050, 230),
    ("seahorse_1e4", -.743643887037151, .13182590420533, .00010, 270),
    ("seahorse_3e5", -.743643887037151, .13182590420533, .00003, 310),
)
images = []
for name, cx, cy, span, iterations in CASES:
    image = render(cx, cy, span, iterations)
    cv2.rectangle(image, (0, 0), (511, 31), (0, 0, 0), -1)
    cv2.putText(image, name, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.imwrite(str(OUT / f"{name}.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    images.append(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
cv2.imwrite(str(OUT / "ATTEMPT96_MANDELBROT_DEEP_SCOUT.png"), cv2.hconcat(images))
print(OUT / "ATTEMPT96_MANDELBROT_DEEP_SCOUT.png")
