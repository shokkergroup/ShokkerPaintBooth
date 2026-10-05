"""Firefly Emberglass I1 — red-shifted light behind faceted soot cuticle.

IRIDESCENT INSECTS tick 32 / owner identity law 2026-09-02.
Owner verdict driving this renderer: bases and specs cannot be recolours or
shared carriers; both must be name-true and the spec must trace the finish.

This is intentionally unrelated to Firefly Lantern's repeated three-layer
photogenic glyph modules. Emberglass is one connected angular material:
irregular soot-lacquer sclerite facets contain asymmetric ember wedges whose
yellow/orange/red state models the green-to-red pH/temperature shift of firefly
luciferase. Salt-bridge clamp rails, triangular quenched pockets, copper seam
lips, wet prism edges and sparse oxygen capillaries are attached to the facets.
No beads, dots, broad glow bands, honeycomb, confetti or palette-only variants.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "firefly_ember",
    "display_name": "Firefly Emberglass",
    "promise": "Smoked angular shell glass traps asymmetric living ember wedges.",
    "reference_physics": {
        "mechanism": (
            "Firefly luciferase shifts from yellow-green toward orange/red as acidic pH, "
            "heat, or metal binding weakens electrostatic active-site gates; oxygen reaches "
            "photocytes through reinforced tracheolar arborizations."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6279810/",
            "https://pubmed.ncbi.nlm.nih.gov/30249073/",
        ],
    },
    "carrier_grammar": (
        "A nonperiodic triangulated sheet of overlapping soot-glass sclerites, with local "
        "asymmetric wedge chambers and interrupted shared seams."
    ),
    "spec_grammar": (
        "Facet bodies, ember states, clamp rails, pits, seam lips, prism edges and oxygen "
        "capillaries each own different M/R/Cc tiers; no independent overlay field."
    ),
    "native_scale_px": [8, 31],
    "mark_types": [
        {"name": "soot_facet", "role": "forms the continuous smoked cuticle glass sheet"},
        {"name": "ember_wedge", "role": "shows the pH-tuned photogenic chamber inside a facet"},
        {"name": "clamp_rail", "role": "models the paired electrostatic gate around emission"},
        {"name": "quenched_pit", "role": "marks a dark triangular inactive chamber pocket"},
        {"name": "seam_lip", "role": "joins adjacent hard sclerites with a copper cuticle edge"},
        {"name": "prism_edge", "role": "catches wet extraction light on selected glass edges"},
        {"name": "oxygen_capillary", "role": "routes sparse reinforced tracheolar oxygen branches"},
    ],
    "material_binding": {
        "M": ["soot_facet", "seam_lip", "clamp_rail", "ember_wedge"],
        "R": ["soot_facet", "quenched_pit", "oxygen_capillary", "seam_lip"],
        "Cc": ["soot_facet", "prism_edge", "ember_wedge", "clamp_rail"],
    },
    "material_tiers": [
        "dry soot shell", "smoked glass", "copper seam", "yellow closed gate",
        "orange unstable gate", "red open gate", "wet prism", "quenched matte pit",
    ],
    "nearest_neighbors": [
        {
            "finish_id": "firefly_lantern",
            "difference": "one triangulated glass sheet replaces complete repeated organ glyphs",
        },
        {
            "finish_id": "beetle_click",
            "difference": "angular chamber wedges and shared seams replace circular bead routes",
        },
        {
            "finish_id": "wasp_warning",
            "difference": "irregular three-vertex glass facets replace nested tergite chevrons",
        },
    ],
    "name_truth": {
        "visible_evidence": [
            "smoked interlocked glass facets",
            "asymmetric ember chambers",
            "wet prism and copper cuticle edges",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "triangulated-soot-sclerites-with-ember-wedge-chambers",
    "spec_key": "ph-gate-wedge-prism-seam-capillary-material-binding",
}


GEN = 640


def _hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _resize(array, shape):
    h, w = _hw(shape)
    array = np.asarray(array, np.float32)
    if array.shape[:2] == (h, w):
        return array
    return cv2.resize(array, (w, h), interpolation=cv2.INTER_CUBIC)


def _blend(paint, mask, pm, colour):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    alpha = np.clip(mask * pm * .98, 0, 1)[..., None]
    paint[:, :, :3] = paint[:, :, :3] * (1 - alpha) + np.clip(colour, 0, 1) * alpha
    return np.clip(paint, 0, 1).astype(np.float32)


def _inner_triangle(points: np.ndarray, centre: np.ndarray, amount: float) -> np.ndarray:
    return np.rint(centre + (points - centre) * amount).astype(np.int32)


@lru_cache(maxsize=2)
def _surface(seed):
    rng = np.random.default_rng(int(seed) ^ 0xE6B3A5)
    h = w = GEN
    soot = np.zeros((h, w), np.float32)
    yellow = np.zeros_like(soot)
    orange = np.zeros_like(soot)
    red = np.zeros_like(soot)
    clamp = np.zeros_like(soot)
    pit = np.zeros_like(soot)
    seam = np.zeros_like(soot)
    prism = np.zeros_like(soot)
    oxygen = np.zeros_like(soot)

    step = 8.5  # 27px at 2048; all internal marks remain 8-31px native.
    rows = int(np.ceil(h / step)) + 2
    cols = int(np.ceil(w / step)) + 2
    points = np.zeros((rows, cols, 2), np.float32)
    for row in range(rows):
        for col in range(cols):
            points[row, col] = (
                (col - 1) * step + (step * .48 if row % 2 else 0) + rng.uniform(-2.0, 2.0),
                (row - 1) * step + rng.uniform(-2.0, 2.0),
            )

    facet_index = 0
    for row in range(rows - 1):
        for col in range(cols - 1):
            p00, p10 = points[row, col], points[row, col + 1]
            p01, p11 = points[row + 1, col], points[row + 1, col + 1]
            split = (row + col + int(2 * np.sin(row * .37 + col * .23))) & 1
            triangles = ((p00, p10, p11), (p00, p11, p01)) if split else (
                (p00, p10, p01), (p10, p11, p01)
            )
            for tri_values in triangles:
                tri = np.rint(np.asarray(tri_values, np.float32)).astype(np.int32)
                centre = np.mean(tri.astype(np.float32), axis=0)
                if centre[0] < -8 or centre[0] > w + 8 or centre[1] < -8 or centre[1] > h + 8:
                    continue
                field = (
                    .52 * np.sin(centre[0] / 47.0 + centre[1] / 83.0)
                    + .31 * np.cos(centre[1] / 39.0 - centre[0] / 71.0)
                    + .17 * np.sin((centre[0] + centre[1]) / 113.0)
                )
                body = float(np.clip(.27 + .22 * field + rng.uniform(-.12, .14), .08, .72))
                cv2.fillConvexPoly(soot, tri, body, cv2.LINE_AA)

                # Broken shared edges form sclerite seams without a regular mesh outline.
                edge_id = int(rng.integers(0, 3))
                a, b = tri[edge_id], tri[(edge_id + 1) % 3]
                if rng.random() < .72:
                    q0 = np.rint(a * .78 + b * .22).astype(int)
                    q1 = np.rint(a * .20 + b * .80).astype(int)
                    cv2.line(seam, tuple(q0), tuple(q1), float(rng.uniform(.30, .95)), 1, cv2.LINE_AA)
                if rng.random() < .42:
                    edge2 = (edge_id + 1) % 3
                    c, d = tri[edge2], tri[(edge2 + 1) % 3]
                    q0 = np.rint(c * .70 + d * .30).astype(int)
                    q1 = np.rint(c * .34 + d * .66).astype(int)
                    cv2.line(prism, tuple(q0), tuple(q1), float(rng.uniform(.34, 1.0)), 1, cv2.LINE_AA)

                # A subset of facets contain an asymmetric chamber wedge rather than a dot.
                # P3 varied density/mesh warp and passed 88.3, but owner-eye
                # rejected its extra dead pockets. P2 remains the brighter,
                # stronger emberglass carrier at the 20-minute cap.
                active = rng.random() < .68
                vertex = int(rng.integers(0, 3))
                inner = _inner_triangle(tri, centre, rng.uniform(.36, .58))
                if active:
                    tip = inner[vertex]
                    left = np.rint(centre + (inner[(vertex + 1) % 3] - centre) * .72).astype(int)
                    right = np.rint(centre + (inner[(vertex + 2) % 3] - centre) * .72).astype(int)
                    wedge = np.asarray([tip, left, right], np.int32)
                    state = field + rng.normal(0, .31)
                    target = red if state < -.22 else orange if state < .33 else yellow
                    cv2.fillConvexPoly(target, wedge, float(rng.uniform(.34, 1.0)), cv2.LINE_AA)

                    # Paired active-site clamp rails sit on the wedge, never globally.
                    for offset in (-.7, .7):
                        v0 = centre + (tip - centre) * .18 + offset * np.array([.7, -.7])
                        v1 = centre + (tip - centre) * .76 + offset * np.array([.7, -.7])
                        cv2.line(clamp, tuple(np.rint(v0).astype(int)), tuple(np.rint(v1).astype(int)),
                                 float(rng.uniform(.32, .94)), 1, cv2.LINE_AA)
                elif rng.random() < .74:
                    # Inactive chambers are angular voids, not floating circles.
                    dark = _inner_triangle(tri, centre, rng.uniform(.20, .34))
                    cv2.fillConvexPoly(pit, dark, float(rng.uniform(.38, .96)), cv2.LINE_AA)
                facet_index += 1

    # Sparse reinforced tracheolar branches cross and terminate inside facets.
    for _ in range(58):
        x, y = rng.uniform(-8, w + 8), rng.uniform(-8, h + 8)
        angle = rng.uniform(-np.pi, np.pi)
        pts = [(x, y)]
        for _segment in range(int(rng.integers(3, 7))):
            angle += rng.uniform(-.62, .62)
            length = rng.uniform(6.0, 12.0)
            x += length * np.cos(angle)
            y += length * np.sin(angle)
            pts.append((x, y))
        for index, (a, b) in enumerate(zip(pts, pts[1:])):
            cv2.line(oxygen, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                     float(rng.uniform(.30, .88)), 1, cv2.LINE_AA)
            if index and rng.random() < .45:
                aa = angle + rng.choice((-1, 1)) * rng.uniform(.45, .82)
                end = (b[0] + 4.0 * np.cos(aa), b[1] + 4.0 * np.sin(aa))
                cv2.line(oxygen, tuple(np.rint(b).astype(int)), tuple(np.rint(end).astype(int)),
                         float(rng.uniform(.28, .78)), 1, cv2.LINE_AA)

    arrays = (soot, yellow, orange, red, clamp, pit, seam, prism, oxygen)
    return tuple(cv2.GaussianBlur(array, (0, 0), .16).astype(np.float32) for array in arrays)


def paint_firefly_ember(paint, shape, mask, seed, pm, _base):
    soot, yellow, orange, red, clamp, pit, seam, prism, oxygen = _surface(seed + 32107)
    colour = np.zeros((*soot.shape, 3), np.float32)
    colour[:] = np.array([.012, .006, .010], np.float32)
    colour += soot[..., None] * np.array([.19, .055, .045], np.float32)
    colour += yellow[..., None] * np.array([1.00, .72, .08], np.float32) * .76
    colour += orange[..., None] * np.array([1.00, .25, .018], np.float32) * .86
    colour += red[..., None] * np.array([.82, .018, .035], np.float32) * .95
    colour += clamp[..., None] * np.array([.92, .54, .13], np.float32) * .48
    colour -= pit[..., None] * np.array([.09, .04, .035], np.float32)
    colour += seam[..., None] * np.array([.62, .22, .075], np.float32) * .52
    colour += prism[..., None] * np.array([.92, .58, .35], np.float32) * .58
    colour += oxygen[..., None] * np.array([.30, .12, .055], np.float32) * .43
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_firefly_ember(shape, seed, sm, _base_m, _base_r):
    soot, yellow, orange, red, clamp, pit, seam, prism, oxygen = _surface(seed + 32107)
    # I1 P2 after P1 66.5 / independence .330 / FOLLOW .073. P1 put almost
    # every feature strongly into every channel, making the spec louder than
    # the paint and collapsing channel identity. Each channel now owns a
    # different anatomical subset while the shared wedge carrier remains
    # visible in combined spec. Owner verdict: spec must trace *this* finish.
    m = 28 + 24 * soot + 142 * seam + 126 * clamp + 34 * yellow + 51 * orange + 174 * red + 23 * prism
    r = 34 + 31 * soot + 151 * yellow + 74 * orange + 42 * red + 137 * pit + 112 * oxygen + 22 * seam - 24 * prism
    cc = 18 + 112 * soot + 38 * yellow + 157 * orange + 67 * red + 164 * prism + 54 * clamp - 29 * pit

    # Secondary per-feature tiers add rich material variation without an
    # independent field or one global rainbow deck.
    m += seam * 28 + clamp * 19 + red * 24 - pit * 9
    r += pit * 25 + oxygen * 21 + yellow * 17 - prism * 18
    cc += prism * 29 + orange * 24 + soot * 13 - seam * 11

    def spread(array, low, high):
        p1, p99 = np.percentile(array, (1.0, 99.0))
        return np.clip(low + (array - p1) * ((high - low) / max(float(p99 - p1), 1e-5)), low, high)

    return (
        np.clip(_resize(cv2.GaussianBlur(spread(m, 14, 241), (0, 0), .72) * sm, shape), 14, 241),
        np.clip(_resize(cv2.GaussianBlur(spread(r, 18, 237), (0, 0), .72) * sm, shape), 18, 237),
        np.clip(_resize(cv2.GaussianBlur(spread(cc, 9, 246), (0, 0), .72) * sm, shape), 9, 246),
    )
