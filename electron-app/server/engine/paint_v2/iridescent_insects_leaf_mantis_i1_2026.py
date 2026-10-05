"""Leaf Mantis Patina I1 — ripped, crumpled Deroplatys cuticle-lamina.

IRIDESCENT INSECTS tick 35 / owner identity law 2026-09-02.
The carrier is neither Orchid Mantis recolored nor generic leaf wallpaper.
Short connected crease segments build a broad dead-leaf lamina; every ridge
owns torn margin jaws, petiole remnants, decay windows, pore chains and
serrated leg-lobe edges at native 8–32px scale.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "mantis_leaf",
    "display_name": "Leaf Mantis Patina",
    "promise": "A ripped and crumpled dead-leaf prothorax becomes weathered bronze cuticle with localized verdigris decay.",
    "reference_physics": {
        "mechanism": (
            "Deroplatys dead-leaf mantises range from brown to gray and use a broad prothorax "
            "that resembles a ripped, crumpled leaf. Dead-leaf ecomorphs add lateral pronotal "
            "projections and leg lobes, while expanded cuticle-gene families support the modified exoskeleton."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10415354/",
            "https://pubmed.ncbi.nlm.nih.gov/37563121/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12579948/",
        ],
    },
    "carrier_grammar": (
        "Interlocking short angular crumple runs cross a complete dead-leaf cuticle lamina; attached "
        "tear jaws, petiole remnants, bounded decay windows, pore chains and serrated lobe edges break every run."
    ),
    "spec_grammar": (
        "Dry lamina, polished crumple lips, black tear wells, oxidized decay windows, petiole bronze, "
        "pore satin and serration burrs occupy different pattern-bound material tiers."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "crumple_ridge", "role": "forms the connected angular relief of the dead-leaf lamina"},
        {"name": "ripped_margin", "role": "cuts paired jagged jaws into ridge interruptions"},
        {"name": "petiole_remnant", "role": "attaches short blunt stalk fragments to selected creases"},
        {"name": "decay_window", "role": "holds bounded oxidized loss inside the cuticle sheet"},
        {"name": "pore_chain", "role": "runs compact cuticle pores along surviving ridge lips"},
        {"name": "lobe_serration", "role": "references the lateral pronotal and leg-lobe projections"},
        {"name": "lamina_plate", "role": "keeps the carrier a complete broad leaf-like exoskeletal sheet"},
    ],
    "material_binding": {
        "M": ["crumple_ridge", "petiole_remnant", "lobe_serration"],
        "R": ["lamina_plate", "ripped_margin", "pore_chain"],
        "Cc": ["crumple_ridge", "decay_window", "lobe_serration"],
    },
    "material_tiers": [
        "dry umber lamina", "smoked bronze plate", "polished crease lip", "black ripped well",
        "verdigris decay", "petiole brass", "pore satin", "chrome serration burr",
    ],
    "nearest_neighbors": [
        {"finish_id": "mantis_orchid", "difference": "connected angular dead-leaf creases and tear jaws replace bilateral white-pink petal fans"},
        {"finish_id": "firefly_ember", "difference": "short routed crumple runs replace a triangulated soot-glass sclerite sheet"},
        {"finish_id": "stick_insect_bark", "difference": "broad cuticle lamina and ripped pronotal edges replace longitudinal bark bundles"},
    ],
    "name_truth": {
        "visible_evidence": [
            "brown-gray connected crumpled leaf lamina",
            "ripped margin jaws and blunt petiole remnants",
            "bounded verdigris decay inside mantis cuticle",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "deroplatys-connected-short-crumple-runs-with-tear-jaws-petioles-and-serrations",
    "spec_key": "dry-lamina-polished-ridge-tear-well-patina-pore-serration-material-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x1EAF35)
    lamina = np.zeros((GEN, GEN), np.float32)
    ridge = np.zeros_like(lamina)
    ridge_lip = np.zeros_like(lamina)
    tear = np.zeros_like(lamina)
    petiole = np.zeros_like(lamina)
    decay = np.zeros_like(lamina)
    pore = np.zeros_like(lamina)
    serration = np.zeros_like(lamina)
    scar = np.zeros_like(lamina)

    yy, xx = np.mgrid[0:GEN, 0:GEN].astype(np.float32)
    lamina[:] = np.clip(.43 + .20 * np.sin(xx / 79.0 + np.sin(yy / 131.0))
                             + .13 * np.cos(yy / 53.0 - xx / 149.0), .08, .86)

    # Connected crumple paths are composed only of 3–9px work-grid segments
    # (10–29px native); no single macro curve is drawn.
    event = 0
    # P2 after P1's perimeter loops / empty center: seed short local crumple
    # runs across the whole lamina. Their segments touch inside each packet,
    # but no chain is allowed to become a macro scribble.
    starts = []
    for row, y0 in enumerate(np.arange(-4.0, GEN + 5.0, 10.6)):
        for col, x0 in enumerate(np.arange(-5.0, GEN + 6.0, 12.4)):
            x = x0 + (5.9 if row % 2 else 0.0) + rng.uniform(-2.6, 2.6)
            y = y0 + rng.uniform(-2.5, 2.5)
            angle = .88 * np.sin(x / 73.0 - y / 91.0) + .47 * np.cos((x + y) / 127.0)
            starts.append((x, y, angle + rng.uniform(-.30, .30)))

    for x, y, angle in starts:
        for step in range(int(rng.integers(3, 7))):
            length = rng.uniform(3.2, 8.7)
            angle += float(rng.choice(
                np.asarray([-np.pi / 3, -np.pi / 6, 0.0, np.pi / 6, np.pi / 3]),
                p=np.asarray([.08, .20, .44, .20, .08]),
            )) + rng.uniform(-.13, .13)
            ux, uy = np.cos(angle), np.sin(angle)
            nx, ny = -uy, ux
            x2, y2 = x + length * ux, y + length * uy
            val = float(rng.uniform(.28, .98))
            cv2.line(ridge, (round(x), round(y)), (round(x2), round(y2)), val, 2, cv2.LINE_AA)
            cv2.line(ridge_lip, (round(x + 1.25 * nx), round(y + 1.25 * ny)),
                     (round(x2 + 1.25 * nx), round(y2 + 1.25 * ny)),
                     float(rng.uniform(.25, .95)), 1, cv2.LINE_AA)

            # Ripped margins are paired jaws anchored to a broken crease.
            if event % 13 == 0:
                qx, qy = x + .56 * length * ux, y + .56 * length * uy
                for side in (-1, 1):
                    tip = (qx + rng.uniform(2.5, 5.2) * ux + side * rng.uniform(1.5, 3.5) * nx,
                           qy + rng.uniform(2.5, 5.2) * uy + side * rng.uniform(1.5, 3.5) * ny)
                    tri = np.rint(np.asarray([
                        (qx - .9 * ux, qy - .9 * uy),
                        (qx + .9 * ux, qy + .9 * uy), tip,
                    ], np.float32)).astype(np.int32)
                    cv2.fillConvexPoly(tear, tri, float(rng.uniform(.38, .98)), cv2.LINE_AA)

            # Petiole remnants and serrations remain attached to a ridge.
            if event % 19 == 0:
                qx, qy = x + .35 * length * ux, y + .35 * length * uy
                cv2.line(petiole, (round(qx), round(qy)),
                         (round(qx + rng.uniform(3.0, 7.2) * nx), round(qy + rng.uniform(3.0, 7.2) * ny)),
                         float(rng.uniform(.36, .96)), 2, cv2.LINE_AA)
            if event % 11 == 0:
                qx, qy = x + .75 * length * ux, y + .75 * length * uy
                tooth_poly = np.rint(np.asarray([
                    (qx - 1.3 * ux, qy - 1.3 * uy),
                    (qx + 1.3 * ux, qy + 1.3 * uy),
                    (qx + rng.uniform(2.6, 5.4) * nx, qy + rng.uniform(2.6, 5.4) * ny),
                ], np.float32)).astype(np.int32)
                cv2.fillConvexPoly(serration, tooth_poly, float(rng.uniform(.34, .98)), cv2.LINE_AA)

            # Decay is a bounded polygon touching the crease—not random dots.
            if event % 17 == 0:
                qx, qy = x + .52 * length * ux, y + .52 * length * uy
                axes = (int(rng.integers(2, 5)), int(rng.integers(1, 4)))
                cv2.ellipse(decay, (round(qx), round(qy)), axes, np.degrees(angle), 0, 360,
                            float(rng.uniform(.30, .94)), -1, cv2.LINE_AA)
                cv2.ellipse(scar, (round(qx), round(qy)), axes, np.degrees(angle), 0, 360,
                            float(rng.uniform(.24, .88)), 1, cv2.LINE_AA)

            # Compact pore chain follows this exact ridge segment.
            if event % 7 == 0:
                for frac in (.22, .50, .78):
                    qx, qy = x + frac * length * ux, y + frac * length * uy
                    cv2.circle(pore, (round(qx), round(qy)), 1, float(rng.uniform(.25, .90)), -1, cv2.LINE_AA)

            x, y = x2, y2
            if x < -12 or y < -12 or x > GEN + 12 or y > GEN + 12:
                break
            event += 1

    arrays = (lamina, ridge, ridge_lip, tear, petiole, decay, pore, serration, scar)
    return tuple(cv2.GaussianBlur(a, (0, 0), .21).astype(np.float32) for a in arrays)


def paint_leaf_mantis(paint, shape, mask, seed, pm, _base):
    lamina, ridge, lip, tear, petiole, decay, pore, serration, scar = _surface(seed + 35031)
    colour = np.zeros((*lamina.shape, 3), np.float32)
    colour[:] = np.array([.055, .032, .022], np.float32)
    colour += lamina[..., None] * np.array([.26, .13, .065], np.float32)
    colour += ridge[..., None] * np.array([.43, .20, .075], np.float32) * .66
    colour += lip[..., None] * np.array([.65, .38, .12], np.float32) * .66
    colour -= tear[..., None] * np.array([.31, .19, .10], np.float32) * .79
    colour += petiole[..., None] * np.array([.61, .30, .08], np.float32) * .72
    colour += decay[..., None] * np.array([.035, .55, .34], np.float32) * .82
    colour += pore[..., None] * np.array([.26, .10, .035], np.float32) * .56
    colour += serration[..., None] * np.array([.53, .25, .065], np.float32) * .76
    colour += scar[..., None] * np.array([.10, .36, .24], np.float32) * .58
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_leaf_mantis(shape, seed, sm, _base_m, _base_r):
    lamina, ridge, lip, tear, petiole, decay, pore, serration, scar = _surface(seed + 35031)
    # P3 after P2 FOLLOW edge .198: the smooth whole-sheet lamina dominated R
    # and hid the actual painted boundaries. Every channel now transitions on
    # a visible named mark: lips/crests in M, tears/pore scars in R, bounded
    # verdigris/scar/serration in Cc.
    m = 18 + 143 * ridge + 207 * lip + 221 * petiole + 241 * serration
    # P5 after P4 FOLLOW edge .335: visible orange crumple lips now contribute
    # dry shoulders to R and narrow polished torn edges to Cc. Dominant channel
    # ownership remains separate; these are secondary states on the same mark.
    # P6 brackets P4 (independence .678 / FOLLOW .335) against P5
    # (independence .418 / FOLLOW .523): half-strength secondary lip states
    # retain boundary tracing without collapsing M/R/Cc into one silhouette.
    r = 27 + 218 * tear + 176 * pore + 103 * scar + 31 * ridge + 24 * lip
    cc = 14 + 231 * decay + 196 * scar + 224 * serration + 31 * ridge + 40 * lip + 22 * tear

    def spread(a, low, high):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        out = low + (a - p1) * ((high - low) / max(float(p99 - p1), 1e-5))
        # P4 after P3 FOLLOW edge .340: preserve the native torn-lip boundary
        # instead of smearing a 1–2px work-grid mark beyond its painted edge.
        return cv2.GaussianBlur(np.clip(out, low, high), (0, 0), .42)

    return (
        np.clip(_resize(spread(m, 13, 244) * sm, shape), 13, 244),
        np.clip(_resize(spread(r, 17, 241) * sm, shape), 17, 241),
        np.clip(_resize(spread(cc, 10, 247) * sm, shape), 10, 247),
    )
