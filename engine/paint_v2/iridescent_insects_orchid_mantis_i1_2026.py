"""Orchid Mantis Silk I1 — petal-lobe cuticle with pigment/urate transition anatomy.

IRIDESCENT INSECTS tick 34 / owner identity law 2026-09-02.
This is not generic pink floral wallpaper.  The complete carrier is built from
small bilateral femoral-lobe cuticle fans: translucent petal plates, Wnt-like
growth seams, xanthommatin export notches, urate-white reservoirs, UV-dark
cuticle clefts, articulation pearls and raptorial toothlets.  Every material
channel is owned by those visible structures.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "mantis_orchid",
    "display_name": "Orchid Mantis Silk",
    "promise": "White-pink petal mimicry emerges from layered femoral-lobe cuticle, urate reservoirs and pigment-export seams.",
    "reference_physics": {
        "mechanism": (
            "Orchid mantis petal-like femoral lobes are enlarged exoskeletal cuticle structures. "
            "Their programmed transition from black-red to flower-white simultaneously exports "
            "decarboxylated xanthommatin and accumulates white uric acid in epidermal cells; mature "
            "white body regions are primarily UV absorbing rather than mirror-white."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10415354/",
            "https://pubmed.ncbi.nlm.nih.gov/40447881/",
            "https://bioone.org/journals/journal-of-orthoptera-research/volume-22/issue-1/034.022.0106/Coloration-and-Morphology-of-the-Orchid-Mantis-Hymenopus-coronatus-Mantodea/10.1665/034.022.0106.pdf",
        ],
    },
    "carrier_grammar": (
        "Offset bilateral fans of tiny tapered femoral-lobe plates overlap into a continuous cuticle sheet; "
        "each fan has an articulated waist, asymmetric inner vein, pigment-export cleft and toothlet edge."
    ),
    "spec_grammar": (
        "Urate plate reservoirs, xanthommatin seam notches, translucent lobe rims, UV-dark clefts, "
        "articulation pearls and raptorial toothlets own separate M/R/Cc states."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "petal_plate", "role": "forms the tapered translucent femoral-lobe cuticle"},
        {"name": "urate_reservoir", "role": "stores the flower-white epidermal pigment state"},
        {"name": "xanthommatin_seam", "role": "records the exported red-pigment path between plates"},
        {"name": "growth_vein", "role": "shows the asymmetric structural rib inside each lobe"},
        {"name": "uv_cleft", "role": "adds the narrow UV-absorbing cuticle separation"},
        {"name": "articulation_pearl", "role": "joins the paired lobe fan at its waist"},
        {"name": "raptorial_toothlet", "role": "interrupts soft petal mimicry with mantis anatomy"},
    ],
    "material_binding": {
        "M": ["growth_vein", "xanthommatin_seam", "articulation_pearl", "raptorial_toothlet"],
        "R": ["urate_reservoir", "uv_cleft", "growth_vein"],
        "Cc": ["petal_plate", "urate_reservoir", "xanthommatin_seam", "articulation_pearl"],
    },
    "material_tiers": [
        "urate powder", "translucent petal cuticle", "pink xanthommatin satin", "magenta export seam",
        "UV-dark cleft", "pearl articulation", "wet lobe rim", "hard raptorial tooth",
    ],
    "nearest_neighbors": [
        {"finish_id": "butterfly_glasswing", "difference": "paired tapered exoskeletal lobe fans replace broad membrane panes and vein lattice"},
        {"finish_id": "moth_luna", "difference": "urate-filled cuticle plates and export clefts replace flowing feather scales"},
        {"finish_id": "mantis_leaf", "difference": "soft bilateral flower lobes and pigment transition anatomy replace angular leaf scars and patina"},
    ],
    "name_truth": {
        "visible_evidence": [
            "paired orchid-petal femoral-lobe fans",
            "white urate reservoirs beside pink pigment-export seams",
            "raptorial toothlets interrupting the soft flower mimicry",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "orchid-mantis-bilateral-femoral-lobe-fans-with-export-clefts-and-toothlets",
    "spec_key": "urate-xanthommatin-petal-cleft-articulation-tooth-material-binding",
}


GEN = 640


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(array, shape):
    h, w = _hw(shape)
    array = np.asarray(array, np.float32)
    return array if array.shape[:2] == (h, w) else cv2.resize(array, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .98, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _kite(cx, cy, ux, uy, length, width, bend):
    nx, ny = -uy, ux
    return np.rint(np.asarray([
        (cx - .18 * length * ux, cy - .18 * length * uy),
        (cx + .28 * length * ux - width * nx, cy + .28 * length * uy - width * ny),
        (cx + length * ux + bend * nx, cy + length * uy + bend * ny),
        (cx + .28 * length * ux + width * nx, cy + .28 * length * uy + width * ny),
    ], np.float32)).astype(np.int32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0x0AC41D)
    plate = np.zeros((GEN, GEN), np.float32)
    urate = np.zeros_like(plate)
    pink = np.zeros_like(plate)
    seam = np.zeros_like(plate)
    vein = np.zeros_like(plate)
    cleft = np.zeros_like(plate)
    pearl = np.zeros_like(plate)
    rim = np.zeros_like(plate)
    tooth = np.zeros_like(plate)

    index = 0
    # P2 after P1's sparse repeated white chevrons: tighter, irregular overlap
    # makes one continuous flower-cuticle sheet rather than floating motifs.
    for row, cy0 in enumerate(np.arange(-7.0, GEN + 9.0, 8.4)):
        for col, cx0 in enumerate(np.arange(-8.0, GEN + 10.0, 9.8)):
            cx = cx0 + (4.7 if row % 2 else 0.0) + rng.uniform(-2.1, 2.1)
            cy = cy0 + rng.uniform(-2.0, 2.0)
            field = .52 * np.sin(cx / 71.0 + cy / 103.0) + .48 * np.cos(cy / 57.0 - cx / 137.0)
            base_angle = .42 * np.sin(cx / 113.0 - cy / 89.0) + rng.uniform(-.16, .16)
            waist = float(rng.uniform(.48, .94))
            cv2.circle(pearl, (round(cx), round(cy)), int(rng.integers(1, 3)), waist, -1, cv2.LINE_AA)

            # Two unequal, bilaterally paired femoral lobes. Each primitive is
            # 10–31px after 640→2048 enlargement.
            for side in (-1, 1):
                angle = base_angle + side * rng.uniform(.46, .78)
                ux, uy = np.cos(angle), np.sin(angle)
                nx, ny = -uy, ux
                length = rng.uniform(4.6, 8.5)
                width = rng.uniform(2.3, 4.1)
                bend = side * rng.uniform(.15, 1.1)
                poly = _kite(cx, cy, ux, uy, length, width, bend)
                value = float(np.clip(.36 + .20 * field + rng.uniform(-.10, .34), .14, .98))
                cv2.fillConvexPoly(plate, poly, value, cv2.LINE_AA)
                cv2.polylines(rim, [poly], True, float(rng.uniform(.35, .96)), 1, cv2.LINE_AA)

                # Uric-acid white lies inside the lobe rather than becoming
                # loose dots; red export remains a narrow basal crescent.
                inner = _kite(cx + .45 * ux, cy + .45 * uy, ux, uy,
                              length * .69, width * .58, bend * .62)
                cv2.fillConvexPoly(urate, inner, float(rng.uniform(.34, .98)), cv2.LINE_AA)
                export = pink if field > -.08 else seam
                p0 = (round(cx + .10 * length * ux - .72 * width * nx),
                      round(cy + .10 * length * uy - .72 * width * ny))
                p1 = (round(cx + .46 * length * ux + .42 * width * nx),
                      round(cy + .46 * length * uy + .42 * width * ny))
                cv2.line(export, p0, p1, float(rng.uniform(.38, .98)), 1, cv2.LINE_AA)

                # The vein is deliberately off-axis: a botanical-looking
                # petal that still reveals a jointed mantis cuticle.
                vx = cx + (.24 + rng.uniform(-.05, .08)) * length * ux
                vy = cy + (.24 + rng.uniform(-.05, .08)) * length * uy
                tipx = cx + .82 * length * ux + bend * nx
                tipy = cy + .82 * length * uy + bend * ny
                cv2.line(vein, (round(vx), round(vy)), (round(tipx), round(tipy)),
                         float(rng.uniform(.30, .94)), 1, cv2.LINE_AA)

                if (index + side) % 5 == 0:
                    qx, qy = cx + .63 * length * ux, cy + .63 * length * uy
                    cv2.line(cleft, (round(qx - 1.25 * nx), round(qy - 1.25 * ny)),
                             (round(qx + 1.25 * nx), round(qy + 1.25 * ny)),
                             float(rng.uniform(.45, .98)), 1, cv2.LINE_AA)

            # Mantis identity: tiny plate-bound raptorial teeth, never confetti.
            if index % 7 == 0:
                angle = base_angle + np.pi
                ux, uy = np.cos(angle), np.sin(angle)
                nx, ny = -uy, ux
                tri = np.rint(np.asarray([
                    (cx - 1.3 * nx, cy - 1.3 * ny),
                    (cx + 1.3 * nx, cy + 1.3 * ny),
                    (cx + rng.uniform(3.0, 5.7) * ux, cy + rng.uniform(3.0, 5.7) * uy),
                ], np.float32)).astype(np.int32)
                cv2.fillConvexPoly(tooth, tri, float(rng.uniform(.40, .98)), cv2.LINE_AA)
            index += 1

    arrays = (plate, urate, pink, seam, vein, cleft, pearl, rim, tooth)
    return tuple(cv2.GaussianBlur(a, (0, 0), .18).astype(np.float32) for a in arrays)


def paint_orchid_mantis(paint, shape, mask, seed, pm, _base):
    plate, urate, pink, seam, vein, cleft, pearl, rim, tooth = _surface(seed + 34101)
    colour = np.zeros((*plate.shape, 3), np.float32)
    colour[:] = np.array([.145, .060, .145], np.float32)
    colour += plate[..., None] * np.array([.40, .27, .37], np.float32)
    colour += urate[..., None] * np.array([.48, .55, .63], np.float32)
    colour += pink[..., None] * np.array([.93, .18, .42], np.float32) * .72
    colour += seam[..., None] * np.array([.70, .035, .25], np.float32) * .86
    colour += vein[..., None] * np.array([.26, .56, .51], np.float32) * .58
    colour -= cleft[..., None] * np.array([.21, .15, .19], np.float32) * .72
    colour += pearl[..., None] * np.array([.74, .70, .88], np.float32) * .68
    colour += rim[..., None] * np.array([.38, .22, .52], np.float32) * .42
    colour += tooth[..., None] * np.array([.59, .23, .16], np.float32) * .72
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_orchid_mantis(shape, seed, sm, _base_m, _base_r):
    plate, urate, pink, seam, vein, cleft, pearl, rim, tooth = _surface(seed + 34101)
    # P1 independence .101: plate/urate/pink occupied every channel. P2 gives
    # each anatomical family a dominant response while retaining attached
    # secondary tiers: hard seams/veins in M, powder/clefts in R, translucent
    # petal/rim in Cc.
    # P3 after P2 independence .431: nested features still leaked across
    # channels. Keep the response anatomical and mutually legible.
    # P4 after P3 independence .435: material tiers now select separate
    # subsets *inside* the same visible lobe anatomy instead of lighting every
    # nested layer together. This preserves tracing without a repeated RGB
    # silhouette: export seams/toothlets are hard, concentrated urate pockets
    # are powdery, and only wet rims/pink reservoirs receive high clearcoat.
    m = 18 + 220 * seam + 190 * tooth + 35 * vein + 28 * pearl
    r = 26 + 230 * np.where(urate > .62, urate, 0) + 170 * cleft + 22 * vein
    cc = (15 + 235 * np.where(rim > .62, rim, 0)
          + 150 * np.where(pink > .62, pink, 0) + 18 * plate + 9 * urate + 18 * pearl)

    def spread(array, low, high):
        p1, p99 = np.percentile(array, (1.0, 99.0))
        out = low + (array - p1) * ((high - low) / max(float(p99 - p1), 1e-5))
        return cv2.GaussianBlur(np.clip(out, low, high), (0, 0), .92)

    return (
        np.clip(_resize(spread(m, 12, 244) * sm, shape), 12, 244),
        np.clip(_resize(spread(r, 16, 241) * sm, shape), 16, 241),
        np.clip(_resize(spread(cc, 9, 248) * sm, shape), 9, 248),
    )
