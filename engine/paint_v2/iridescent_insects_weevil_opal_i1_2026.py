"""Weevil Opal I1 — scale-by-scale single-diamond photonic rosettes.

SPB-105 / owner 2026-09-02: independently constructed 8–32px native paint
and feature-bound M/R/Cc. The carrier is a dense field of individually tuned
weevil scales seated in concave cuticular pits, never a recoloured wave field.
"""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "weevil_opal",
    "display_name": "Weevil Opal Mosaic",
    "promise": "Thousands of pit-seated weevil scales behave as individually tuned opal photonic crystals.",
    "reference_physics": {
        "mechanism": (
            "Pachyrhynchus and related weevil scales contain chitin-air single-diamond photonic crystals. "
            "Lattice parameter, filling fraction and domain orientation tune hue scale by scale; some species "
            "mix red, yellow, green and blue micro-pixels additively, while concave scale-bearing pits scatter "
            "the structural colour over broad angles."
        ),
        "sources": [
            "https://pubmed.ncbi.nlm.nih.gov/30112799/",
            "https://pubmed.ncbi.nlm.nih.gov/29443002/",
            "https://pubmed.ncbi.nlm.nih.gov/22378806/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC9475527/",
        ],
    },
    "carrier_grammar": (
        "Staggered concave 10–26px scale pits each hold a compact four-domain opal rosette, a dark grain-boundary "
        "cross, an ice rim and one or more clear microbead points; local lattice classes change per scale."
    ),
    "spec_grammar": (
        "Pit recess, scale cortex, four differently oriented photonic domains, grain boundary, ice rim and "
        "microbead points are exact shared masks with separate M/R/Cc tier families."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "concave_scale_pit", "role": "seats each scale in the dark elytral cuticle"},
        {"name": "opal_scale_cortex", "role": "forms the pale shell around the photonic interior"},
        {"name": "diamond_domain_a", "role": "records one single-diamond lattice orientation"},
        {"name": "diamond_domain_b", "role": "records a second differently tuned lattice orientation"},
        {"name": "grain_boundary_cross", "role": "separates the internal photonic crystal domains"},
        {"name": "ice_scale_rim", "role": "catches the polished perimeter of the flattened scale"},
        {"name": "microbead_point", "role": "adds discrete clear lattice/filling-fraction highlights"},
        {"name": "missing_scale_socket", "role": "reveals occasional empty attachment sockets"},
    ],
    "material_binding": {
        "M": ["diamond_domain_a", "diamond_domain_b", "ice_scale_rim"],
        "R": ["concave_scale_pit", "grain_boundary_cross", "missing_scale_socket"],
        "Cc": ["opal_scale_cortex", "ice_scale_rim", "microbead_point"],
    },
    "material_tiers": [
        "opal pearl", "ice chrome", "violet satin", "cyan diamond domain", "rose diamond domain",
        "amber lattice domain", "dark pit recess", "dry grain boundary", "clear microbead", "empty socket",
    ],
    "nearest_neighbors": [
        {"finish_id": "beetle_jewel", "difference": "thousands of pit-seated four-domain rosette scales replace a continuous jewel shell"},
        {"finish_id": "butterfly_morpho", "difference": "single-diamond pointillist scale domains replace lamellar blue wing ridges"},
        {"finish_id": "cockroach_onyx", "difference": "compact radial photonic scales replace overlapping abdominal tergite shingles"},
    ],
    "name_truth": {
        "visible_evidence": [
            "dense individually tuned opal scale rosettes",
            "concave black scale pits and ice-bright rims",
            "cyan, violet, rose and amber photonic domains mixed scale by scale",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "weevil-concave-pits-with-four-domain-single-diamond-opal-rosette-scales",
    "spec_key": "weevil-pit-cortex-domain-grain-rim-microbead-socket-material-binding",
}


GEN = 768


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(array, shape):
    h, w = _hw(shape)
    a = np.asarray(array, np.float32)
    return a if a.shape[:2] == (h, w) else cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .98, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0x0FA1C7)
    z = np.zeros((GEN, GEN), np.float32)
    pit, cortex, d0, d1, d2, d3 = (z.copy() for _ in range(6))
    boundary, rim, bead, socket = (z.copy() for _ in range(4))

    step_x, step_y = 8.4, 7.2
    index = 0
    domains = (d0, d1, d2, d3)
    for row, cy0 in enumerate(np.arange(-5.0, GEN + 6.0, step_y)):
        offset = 0.0 if row % 2 == 0 else step_x * .5
        for cx0 in np.arange(-6.0 + offset, GEN + 7.0, step_x):
            cx = int(round(cx0 + rng.uniform(-.9, .9)))
            cy = int(round(cy0 + rng.uniform(-.7, .7)))
            ax = int(rng.integers(3, 5))
            ay = int(rng.integers(3, 5))
            angle = float(rng.uniform(-28, 28))
            strength = float(rng.uniform(.34, .99))

            cv2.ellipse(pit, (cx, cy), (ax + 1, ay + 1), angle, 0, 360, strength, -1, cv2.LINE_AA)
            # Missing scales expose sockets instead of becoming arbitrary holes.
            if index % 47 == 0:
                cv2.ellipse(socket, (cx, cy), (ax, ay), angle, 0, 360, float(rng.uniform(.45, .98)), 1, cv2.LINE_AA)
                cv2.circle(socket, (cx, cy), 1, float(rng.uniform(.35, .9)), -1, cv2.LINE_AA)
                index += 1
                continue

            cv2.ellipse(cortex, (cx, cy), (ax, ay), angle, 0, 360, strength, -1, cv2.LINE_AA)
            cv2.ellipse(rim, (cx, cy), (ax, ay), angle, 0, 360, float(rng.uniform(.30, .99)), 1, cv2.LINE_AA)

            # Four compact wedges create a rosette while preserving per-domain identity.
            radius = max(2, min(ax, ay))
            phase = np.deg2rad(angle + rng.uniform(-15, 15))
            centers = []
            # P3 owner-eye correction: each scale has one dominant lattice
            # class, with only an occasional adjacent-domain inclusion. This
            # reads as scale-by-scale opal pointillism instead of RGB confetti.
            lattice_phase = (
                np.sin(cx * .075 + 1.30 * np.sin(cy * .021))
                + np.cos(cy * .067 - .80 * np.sin(cx * .027))
                + rng.uniform(-.28, .28)
            )
            base_class = int(np.clip(np.floor((lattice_phase + 2.28) / 1.14), 0, 3))
            for k in range(4):
                class_step = 1 if (index + k) % 17 == 0 else 0
                target = domains[(base_class + class_step) % 4]
                theta = phase + k * np.pi * .5
                px = cx + int(round(np.cos(theta) * radius * .43))
                py = cy + int(round(np.sin(theta) * radius * .43))
                centers.append((px, py))
                cv2.ellipse(target, (px, py), (max(1, ax - 2), max(1, ay - 2)),
                            np.rad2deg(theta), 0, 360, float(rng.uniform(.26, .99)), -1, cv2.LINE_AA)

            # Two crossing one-pixel grain boundaries remain bound to this scale.
            ca, sa = np.cos(phase), np.sin(phase)
            for theta in (phase, phase + np.pi * .5):
                dx, dy = int(round(np.cos(theta) * ax)), int(round(np.sin(theta) * ay))
                cv2.line(boundary, (cx - dx, cy - dy), (cx + dx, cy + dy),
                         float(rng.uniform(.28, .95)), 1, cv2.LINE_AA)

            if index % 3 == 0:
                bx, by = centers[int(rng.integers(0, 4))]
                cv2.circle(bead, (bx, by), 1, float(rng.uniform(.38, .99)), -1, cv2.LINE_AA)
            if index % 11 == 0:
                theta = phase + rng.uniform(0, np.pi * 2)
                bx = cx + int(round(np.cos(theta) * ax * .8))
                by = cy + int(round(np.sin(theta) * ay * .8))
                cv2.circle(bead, (bx, by), 1, float(rng.uniform(.38, .99)), -1, cv2.LINE_AA)
            index += 1

    arrays = (pit, cortex, d0, d1, d2, d3, boundary, rim, bead, socket)
    return tuple(cv2.GaussianBlur(a, (0, 0), .12).astype(np.float32) for a in arrays)


def _material_states(surface):
    pit, cortex, d0, d1, d2, d3, boundary, rim, bead, socket = surface
    m = np.full((GEN, GEN), 28.0, np.float32)
    r = np.full((GEN, GEN), 226.0, np.float32)
    cc = np.full((GEN, GEN), 18.0, np.float32)

    def assign(field, mv, rv, cv):
        sel = field > .075
        strength = np.clip(field, 0, 1)
        m[sel] = mv[0] + (mv[1] - mv[0]) * strength[sel]
        r[sel] = rv[0] + (rv[1] - rv[0]) * strength[sel]
        cc[sel] = cv[0] + (cv[1] - cv[0]) * strength[sel]

    # P2: orthogonal feature triplets.  The same named masks still bind paint
    # and spec, but no two material channels are recoloured copies of one field.
    assign(pit, (8, 48), (244, 194), (8, 52))
    assign(cortex, (68, 132), (82, 154), (204, 128))
    assign(d0, (194, 248), (96, 24), (172, 82))
    assign(d1, (164, 96), (232, 156), (24, 92))
    assign(d2, (18, 82), (102, 176), (246, 184))
    assign(d3, (226, 162), (142, 216), (214, 154))
    assign(boundary, (18, 76), (62, 128), (236, 166))
    assign(rim, (246, 188), (206, 134), (18, 76))
    assign(bead, (112, 184), (18, 74), (254, 208))
    assign(socket, (72, 138), (246, 178), (82, 154))
    return m, r, cc


def paint_weevil_opal(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 39017)
    pit, cortex, d0, d1, d2, d3, boundary, rim, bead, socket = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.014, .012, .026], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(pit, (.008, .006, .020), (.07, .025, .13))
    assign(cortex, (.20, .22, .35), (.71, .83, .96))
    assign(d0, (.025, .18, .31), (.08, .78, .96))
    assign(d1, (.16, .05, .31), (.68, .19, .93))
    assign(d2, (.30, .035, .19), (.94, .18, .51))
    assign(d3, (.27, .11, .025), (.96, .63, .10))
    assign(boundary, (.012, .01, .035), (.10, .055, .19))
    assign(rim, (.32, .48, .64), (.91, .98, 1.0))
    assign(bead, (.18, .56, .69), (.98, 1.0, 1.0))
    assign(socket, (.018, .012, .028), (.18, .08, .25))

    # Material luminance is the shared topology authority; chroma retains the
    # scale-by-scale additive colour mixing without disconnecting spec.
    m, r, cc = _material_states(surface)
    material_luma = (.38 * m + .37 * (255.0 - r) + .25 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    colour = np.power(np.clip(material_luma, 0, 1), .92)[..., None] + chroma * 1.08
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_weevil_opal(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 39017))
    return (
        np.clip(_resize(m * sm, shape), 8, 250),
        np.clip(_resize(r * sm, shape), 14, 244),
        np.clip(_resize(cc * sm, shape), 8, 254),
    )
