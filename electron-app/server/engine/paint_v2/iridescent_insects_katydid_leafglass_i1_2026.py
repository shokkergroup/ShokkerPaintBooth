"""Katydid Leafglass I1 — transparent reticulate tegmen with acoustic anatomy.

IRIDESCENT INSECTS tick 36 / owner identity law 2026-09-02.
Not Leaf Mantis in green: this carrier is an enclosed wing-cell system. Fine
longitudinal veins and irregular cross-veins surround transparent panes that
carry necrotic mimic spots, feeding-bite scallops, skeletonized ocellata,
resonant mirror membranes and stridulatory file teeth.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "katydid_leafglass",
    "display_name": "Katydid Leafglass",
    "promise": "A leaf-masquerading tegmen becomes transparent green glass while its venation, necrosis and acoustic mirror remain insect-specific.",
    "reference_physics": {
        "mechanism": (
            "Katydid leaf masquerade combines tegmen shape, color and venation. In unpigmented species, "
            "cells enclosed by reticulate veins can be translucent or fully transparent. Typophyllum "
            "forewings also imitate necrotic spots, marginal feeding bites and skeletonized ocellata, "
            "while male wings retain a stridulatory file, scraper and resonant mirror cells."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12582443/",
            "https://www.sciencedirect.com/science/article/pii/S0044523117300748",
            "https://pubmed.ncbi.nlm.nih.gov/19032495/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5541040/",
        ],
    },
    "carrier_grammar": (
        "Fine sinuous longitudinal tegmen veins are joined by irregular cross-veins into enclosed transparent leaf cells; "
        "selected cells own acoustic mirrors, file teeth, necrotic panes, bite scallops and skeletonized ocellata."
    ),
    "spec_grammar": (
        "Vein rails, file teeth, clear cell membranes, resonant mirrors, necrotic panes, bite margins and ocellata rings "
        "each receive independent material tiers tied to their visible boundaries."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "longitudinal_vein", "role": "forms the fine load-bearing leaf-like tegmen rails"},
        {"name": "cross_vein", "role": "closes irregular transparent reticulation cells"},
        {"name": "transparent_pane", "role": "reveals the unpigmented translucent wing membrane"},
        {"name": "necrotic_cell", "role": "mimics dead leaf tissue inside an enclosed pane"},
        {"name": "bite_scallop", "role": "imitates marginal feeding damage on a cell boundary"},
        {"name": "acoustic_mirror", "role": "marks the resonant oval sound-radiating wing membrane"},
        {"name": "file_tooth", "role": "records the stridulatory tooth row attached to a vein"},
        {"name": "skeleton_ocellata", "role": "creates a ringed skeletonized false-hole inside a pane"},
    ],
    "material_binding": {
        "M": ["longitudinal_vein", "file_tooth", "skeleton_ocellata"],
        "R": ["cross_vein", "necrotic_cell", "bite_scallop"],
        "Cc": ["transparent_pane", "acoustic_mirror", "skeleton_ocellata"],
    },
    "material_tiers": [
        "chlorophyll glass", "clear unpigmented pane", "silver vein rail", "dry cross-vein",
        "rough necrotic cell", "black bite margin", "resonant mirror film", "chrome file tooth", "ocellata wet ring",
    ],
    "nearest_neighbors": [
        {"finish_id": "mantis_leaf", "difference": "enclosed transparent tegmen cells and acoustic apparatus replace free crumple/tear lamina"},
        {"finish_id": "butterfly_glasswing", "difference": "dense leaf venation, necrotic mimic cells and file/mirror anatomy replace broad clear butterfly membrane"},
        {"finish_id": "cicada_membrane", "difference": "reticulate green leaf cells and acoustic file teeth replace unequal bronze veins over nanocone glass"},
    ],
    "name_truth": {
        "visible_evidence": [
            "enclosed translucent green leaf-wing cells",
            "necrotic spots and skeletonized bite/ocellata damage",
            "resonant mirror ovals and vein-bound stridulatory file teeth",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "katydid-reticulate-transparent-tegmen-with-necrotic-cells-bites-mirrors-and-files",
    "spec_key": "vein-file-pane-necrosis-bite-mirror-ocellata-material-binding",
}


GEN = 640


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
    rng = np.random.default_rng(int(seed) ^ 0x36A7D1)
    pane = np.zeros((GEN, GEN), np.float32)
    clear = np.zeros_like(pane)
    long_vein = np.zeros_like(pane)
    cross = np.zeros_like(pane)
    necrotic = np.zeros_like(pane)
    bite = np.zeros_like(pane)
    mirror = np.zeros_like(pane)
    mirror_rim = np.zeros_like(pane)
    file_tooth = np.zeros_like(pane)
    ocellata = np.zeros_like(pane)

    yy, xx = np.mgrid[0:GEN, 0:GEN].astype(np.float32)
    pane[:] = np.clip(.39 + .16 * np.sin(xx / 89.0 + yy / 143.0)
                          + .12 * np.cos(yy / 71.0 - xx / 127.0), .10, .78)

    # SPB-105 / identity-gate P2: a katydid tegmen is organized around
    # branching midribs, not a wallpaper stack of parallel rails.  Every long
    # vein below is assembled from 9–19px native segments; the connected
    # anatomy may cross the sheet, but no drawn primitive is macro-sized.
    cell_index = 0
    for rib_i, base_y in enumerate(np.arange(-34.0, GEN + 42.0, 37.0)):
        phase = rng.uniform(0, np.pi * 2)
        slope = rng.uniform(-.19, .19)
        xs = np.arange(-18.0, GEN + 20.0, rng.uniform(3.1, 5.4))
        ys = (base_y + slope * (xs - GEN / 2)
              + 5.2 * np.sin(xs / rng.uniform(55, 91) + phase)
              + 1.1 * np.sin(xs / rng.uniform(13, 24) - phase))

        for j in range(len(xs) - 1):
            cv2.line(long_vein, (round(xs[j]), round(ys[j])),
                     (round(xs[j + 1]), round(ys[j + 1])),
                     float(rng.uniform(.36, .98)), 1, cv2.LINE_AA)

        # Alternating oblique secondary veins create the unmistakable leaf
        # grammar.  Short tertiary forks close irregular translucent panes.
        spacing = int(rng.integers(3, 5))
        for j in range(2 + rib_i % 3, len(xs) - 3, spacing):
            x0, y0 = float(xs[j]), float(ys[j])
            tangent = np.arctan2(ys[j + 1] - ys[j - 1], xs[j + 1] - xs[j - 1])
            side = -1.0 if (j // spacing + rib_i) % 2 else 1.0
            angle = tangent + side * rng.uniform(.72, 1.08)
            length = rng.uniform(12.0, 24.0)
            branch_pts = []
            steps = max(4, int(length / rng.uniform(3.0, 4.8)))
            for k in range(steps + 1):
                t = k / steps
                bend = side * np.sin(t * np.pi) * rng.uniform(1.2, 3.4)
                bx = x0 + np.cos(angle) * length * t - np.sin(angle) * bend
                by = y0 + np.sin(angle) * length * t + np.cos(angle) * bend
                branch_pts.append((bx, by))
            for k in range(len(branch_pts) - 1):
                cv2.line(cross, tuple(map(round, branch_pts[k])),
                         tuple(map(round, branch_pts[k + 1])),
                         float(rng.uniform(.27, .94)), 1, cv2.LINE_AA)

            # Tertiary forks are individually 8–29px at native resolution.
            for fork_at in (0.38, 0.68):
                k = min(len(branch_pts) - 2, max(1, round(fork_at * steps)))
                fx, fy = branch_pts[k]
                fang = angle + side * rng.uniform(.60, .92)
                flen = rng.uniform(3.0, 8.2)
                ex, ey = fx + np.cos(fang) * flen, fy + np.sin(fang) * flen
                cv2.line(cross, (round(fx), round(fy)), (round(ex), round(ey)),
                         float(rng.uniform(.24, .88)), 1, cv2.LINE_AA)

            # The material features live inside or directly on this branch's
            # cell wedge, so the spec traces named anatomy instead of overlay.
            mid = branch_pts[max(1, len(branch_pts) // 2)]
            cx = mid[0] + np.cos(angle + side * 1.57) * rng.uniform(1.0, 3.3)
            cy = mid[1] + np.sin(angle + side * 1.57) * rng.uniform(1.0, 3.3)
            axes = (int(rng.integers(3, 9)), int(rng.integers(2, 6)))
            if cell_index % 4 != 1:
                cv2.ellipse(clear, (round(cx), round(cy)), axes,
                            np.degrees(angle), 0, 360, float(rng.uniform(.25, .94)), -1, cv2.LINE_AA)
            if cell_index % 9 == 0:
                cv2.ellipse(necrotic, (round(cx), round(cy)), axes,
                            np.degrees(angle), 0, 360, float(rng.uniform(.35, .98)), -1, cv2.LINE_AA)
            if cell_index % 17 == 0:
                cv2.circle(ocellata, (round(cx), round(cy)), int(rng.integers(2, 5)),
                           float(rng.uniform(.38, .98)), 1, cv2.LINE_AA)
            if cell_index % 19 == 0:
                cv2.ellipse(bite, (round(branch_pts[-1][0]), round(branch_pts[-1][1])),
                            (int(rng.integers(2, 5)), int(rng.integers(2, 4))),
                            np.degrees(angle), 185, 350, float(rng.uniform(.40, .98)), 2, cv2.LINE_AA)
            if cell_index % 23 == 0:
                maxes = (int(rng.integers(3, 7)), int(rng.integers(2, 5)))
                cv2.ellipse(mirror, (round(cx), round(cy)), maxes, np.degrees(angle),
                            0, 360, float(rng.uniform(.42, .98)), -1, cv2.LINE_AA)
                cv2.ellipse(mirror_rim, (round(cx), round(cy)), maxes, np.degrees(angle),
                            0, 360, float(rng.uniform(.44, .98)), 1, cv2.LINE_AA)

            if cell_index % 5 == 0:
                for tooth_i in range(5):
                    tx = x0 + np.cos(tangent) * (tooth_i - 2) * 1.7
                    ty = y0 + np.sin(tangent) * (tooth_i - 2) * 1.7
                    nx, ny = -np.sin(tangent) * 1.5, np.cos(tangent) * 1.5
                    cv2.line(file_tooth, (round(tx - nx), round(ty - ny)),
                             (round(tx + nx), round(ty + ny)),
                             float(rng.uniform(.34, .98)), 1, cv2.LINE_AA)
            cell_index += 1

    arrays = (pane, clear, long_vein, cross, necrotic, bite, mirror, mirror_rim, file_tooth, ocellata)
    return tuple(cv2.GaussianBlur(a, (0, 0), .17).astype(np.float32) for a in arrays)


def paint_katydid_leafglass(paint, shape, mask, seed, pm, _base):
    pane, clear, vein, cross, necrotic, bite, mirror, mirror_rim, file_tooth, ocellata = _surface(seed + 36019)
    colour = np.zeros((*pane.shape, 3), np.float32)
    colour[:] = np.array([.015, .060, .033], np.float32)
    colour += pane[..., None] * np.array([.052, .36, .17], np.float32)
    colour += clear[..., None] * np.array([.20, .56, .50], np.float32) * .76
    colour += vein[..., None] * np.array([.34, .84, .27], np.float32) * .91
    colour += cross[..., None] * np.array([.52, .86, .32], np.float32) * .78
    colour += necrotic[..., None] * np.array([.42, .25, .065], np.float32) * .82
    colour -= bite[..., None] * np.array([.28, .22, .18], np.float32) * .80
    colour += mirror[..., None] * np.array([.14, .54, .62], np.float32) * .71
    colour += mirror_rim[..., None] * np.array([.31, .75, .73], np.float32) * .68
    colour += file_tooth[..., None] * np.array([.76, .90, .38], np.float32) * .88
    colour += ocellata[..., None] * np.array([.48, .31, .09], np.float32) * .76
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_katydid_leafglass(shape, seed, sm, _base_m, _base_r):
    pane, clear, vein, cross, necrotic, bite, mirror, mirror_rim, file_tooth, ocellata = _surface(seed + 36019)
    m = 16 + 171 * vein + 231 * file_tooth + 128 * ocellata + 54 * mirror_rim
    r = 25 + 139 * cross + 218 * necrotic + 236 * bite + 66 * vein
    cc = 13 + 72 * pane + 184 * np.where(clear > .55, clear, 0) + 239 * mirror + 208 * mirror_rim + 171 * ocellata

    def spread(a, low, high):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        out = low + (a - p1) * ((high - low) / max(float(p99 - p1), 1e-5))
        return cv2.GaussianBlur(np.clip(out, low, high), (0, 0), .60)

    return (
        np.clip(_resize(spread(m, 11, 246) * sm, shape), 11, 246),
        np.clip(_resize(spread(r, 16, 241) * sm, shape), 16, 241),
        np.clip(_resize(spread(cc, 8, 249) * sm, shape), 8, 249),
    )
