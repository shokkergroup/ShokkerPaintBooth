"""Roach Onyx I1 — overlapping cockroach tergite lacquer.

SPB-105 / owner 2026-09-02: independently constructed 8–32px native paint
and feature-bound M/R/Cc.  The carrier is not a dark recolor: staggered
abdominal tergite shingles, arthrodial membranes, gland crescents, tongue
plates, wax pores, campaniform sockets, abrasion tracks and polished lips.
"""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "cockroach_onyx",
    "display_name": "Roach Onyx Armor",
    "promise": "Overlapping cockroach tergites become black onyx lacquer while flexible membranes and gland anatomy remain visible.",
    "reference_physics": {
        "mechanism": (
            "Cockroach abdominal cuticle is divided into layered tergites with exocuticle/endocuticle organization. "
            "Intertergal membrane is flexible and can include crescentic gland zones with dense pores and transverse "
            "tongue-shaped plates; the epicuticle carries waxy hydrocarbons, setae and campaniform sensilla."
        ),
        "sources": [
            "https://pubmed.ncbi.nlm.nih.gov/13224655/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6804909/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8778109/",
            "https://pubmed.ncbi.nlm.nih.gov/993271/",
        ],
    },
    "carrier_grammar": (
        "Staggered overlapping 10–24px native onyx tergite shingles expose narrow arthrodial membranes; selected "
        "plates own wax pores, campaniform sockets, abrasion tracks, crescent gland fields and tongue plates."
    ),
    "spec_grammar": (
        "Plate cores, polished posterior lips, soft membranes, wax pores, gland crescents, tongue plates, sensory "
        "sockets and abrasion tracks each receive distinct tiers derived from their exact visible masks."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "tergite_core", "role": "forms overlapping lacquered abdominal armor shingles"},
        {"name": "posterior_lip", "role": "marks the polished overlap edge of each tergite"},
        {"name": "arthrodial_membrane", "role": "separates hard plates with flexible dark joint material"},
        {"name": "wax_pore", "role": "records cuticular hydrocarbon outlets in the epicuticle"},
        {"name": "gland_crescent", "role": "creates the pore-rich membranous tergal gland zone"},
        {"name": "tongue_plate", "role": "bridges gland and membrane with transverse platelets"},
        {"name": "sensillum_socket", "role": "preserves campaniform and setal sensory anatomy"},
        {"name": "abrasion_track", "role": "adds plate-bounded wear rather than generic scratches"},
    ],
    "material_binding": {
        "M": ["tergite_core", "posterior_lip", "tongue_plate"],
        "R": ["arthrodial_membrane", "gland_crescent", "abrasion_track"],
        "Cc": ["posterior_lip", "wax_pore", "sensillum_socket", "tergite_core"],
    },
    "material_tiers": [
        "onyx lacquer", "mahogany exocuticle", "blue oil wax", "soft membrane",
        "polished plate lip", "dry gland crescent", "chrome tongue plate", "wet sensillum cap", "abrasion satin",
    ],
    "nearest_neighbors": [
        {"finish_id": "ant_velvet", "difference": "staggered shingle tergites and membranes replace capsule sclerites and warning pile"},
        {"finish_id": "beetle_ground", "difference": "flexible gland-bearing abdominal plates replace continuous obsidian carabid armor"},
        {"finish_id": "stick_insect_bark", "difference": "overlapping horizontal shingles replace longitudinal bark-splinter bundles"},
    ],
    "name_truth": {
        "visible_evidence": [
            "dense black-mahogany overlapping tergite shingles",
            "soft membrane seams with pore-rich gland crescents and tongue plates",
            "blue wax pores, sensory sockets and plate-bounded abrasion",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "cockroach-staggered-tergite-shingles-with-membranes-gland-crescents-and-tongue-plates",
    "spec_key": "tergite-lip-membrane-wax-gland-tongue-sensillum-abrasion-material-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0xC0C4A7)
    z = np.zeros((GEN, GEN), np.float32)
    plate, lip, membrane = z.copy(), z.copy(), z.copy()
    pore, gland, tongue = z.copy(), z.copy(), z.copy()
    socket, abrasion, oil = z.copy(), z.copy(), z.copy()

    idx = 0
    row_step, col_step = 6.2, 7.4
    for row, cy in enumerate(np.arange(-3.0, GEN + 4.0, row_step)):
        offset = 0.0 if row % 2 == 0 else col_step * .5
        for cx in np.arange(-5.0 + offset, GEN + 6.0, col_step):
            center = (round(cx + rng.uniform(-.65, .65)), round(cy + rng.uniform(-.45, .45)))
            axes = (int(rng.integers(3, 6)), int(rng.integers(2, 4)))
            angle = rng.uniform(-8, 8)
            pv = float(rng.uniform(.18, .98))
            cv2.ellipse(plate, center, axes, angle, 0, 360, pv, -1, cv2.LINE_AA)
            cv2.ellipse(membrane, center, axes, angle, 0, 360, float(rng.uniform(.25, .92)), 1, cv2.LINE_AA)
            # Posterior half-lip makes the overlap direction legible.
            cv2.ellipse(lip, center, axes, angle, 12, 168, float(rng.uniform(.26, .98)), 1, cv2.LINE_AA)

            if idx % 4 == 0:
                px = center[0] + int(rng.integers(-2, 3))
                py = center[1] + int(rng.integers(-1, 2))
                cv2.circle(pore, (px, py), 1, float(rng.uniform(.25, .98)), -1, cv2.LINE_AA)
            if idx % 13 == 0:
                cv2.circle(socket, center, int(rng.integers(1, 3)), float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)
                cv2.line(socket, center, (center[0] + int(rng.integers(-3, 4)), center[1] - int(rng.integers(2, 6))),
                         float(rng.uniform(.30, .96)), 1, cv2.LINE_AA)
            if idx % 9 == 0:
                # Abrasion remains wholly bounded within one plate.
                x0 = center[0] - int(rng.integers(1, 4))
                y0 = center[1] + int(rng.integers(-1, 2))
                cv2.line(abrasion, (x0, y0), (x0 + int(rng.integers(2, 6)), y0 + int(rng.integers(-1, 2))),
                         float(rng.uniform(.25, .96)), 1, cv2.LINE_AA)
            if idx % 23 == 0:
                cv2.ellipse(gland, center, axes, angle, 185, 350, float(rng.uniform(.35, .98)), 2, cv2.LINE_AA)
                for k in range(3):
                    tx = center[0] + (k - 1) * 2
                    cv2.line(tongue, (tx, center[1] - 1), (tx, center[1] + 2),
                             float(rng.uniform(.32, .98)), 1, cv2.LINE_AA)
            if idx % 3 == 0:
                cv2.ellipse(oil, center, (max(1, axes[0] - 1), max(1, axes[1] - 1)), angle,
                            0, 360, float(rng.uniform(.16, .92)), -1, cv2.LINE_AA)
            idx += 1

    arrays = (plate, lip, membrane, pore, gland, tongue, socket, abrasion, oil)
    return tuple(cv2.GaussianBlur(a, (0, 0), .16).astype(np.float32) for a in arrays)


def _material_states(surface):
    """One topology authority shared by paint and spec (P7 identity fix)."""
    plate, lip, membrane, pore, gland, tongue, socket, abrasion, oil = surface
    m = np.full((GEN, GEN), 24.0, np.float32)
    r = np.full((GEN, GEN), 208.0, np.float32)
    cc = np.full((GEN, GEN), 22.0, np.float32)

    def assign(mask, mv, rv, cv):
        sel = mask > .08
        strength = np.clip(mask, 0, 1)
        m[sel] = mv[0] + (mv[1] - mv[0]) * strength[sel]
        r[sel] = rv[0] + (rv[1] - rv[0]) * strength[sel]
        cc[sel] = cv[0] + (cv[1] - cv[0]) * strength[sel]

    assign(plate, (170, 225), (80, 130), (20, 70))
    assign(oil, (40, 90), (130, 180), (180, 230))
    assign(membrane, (15, 60), (190, 240), (85, 135))
    assign(lip, (75, 130), (20, 70), (205, 249))
    assign(abrasion, (105, 155), (175, 225), (20, 60))
    assign(gland, (35, 85), (85, 140), (150, 210))
    assign(pore, (140, 190), (35, 80), (190, 240))
    assign(socket, (195, 235), (145, 200), (65, 115))
    assign(tongue, (220, 247), (20, 60), (120, 170))
    return m, r, cc


def paint_roach_onyx(paint, shape, mask, seed, pm, _base):
    plate, lip, membrane, pore, gland, tongue, socket, abrasion, oil = _surface(seed + 38117)
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.006, .004, .009], np.float32)

    # P4 uses the same priority topology as spec so every material transition
    # traces a visible named feature rather than an unrelated additive blend.
    def assign(mask_field, dark, bright):
        sel = mask_field > .08
        strength = np.clip(mask_field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(plate, (.10, .018, .025), (.52, .10, .07))
    assign(oil, (.018, .055, .16), (.08, .29, .68))
    assign(membrane, (.003, .003, .008), (.035, .018, .055))
    assign(lip, (.25, .055, .045), (.88, .31, .16))
    assign(abrasion, (.28, .13, .10), (.83, .49, .31))
    assign(gland, (.16, .025, .055), (.52, .12, .22))
    assign(pore, (.025, .15, .27), (.10, .58, .84))
    assign(socket, (.06, .19, .27), (.32, .72, .88))
    assign(tongue, (.29, .24, .20), (.88, .78, .61))

    m, r, cc = _material_states((plate, lip, membrane, pore, gland, tongue, socket, abrasion, oil))
    material_luma = (m * .2126 + r * .7152 + cc * .0722) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma_only = colour - source_luma[..., None]
    onyx_luma = np.power(np.clip(material_luma, 0, 1), 2.35)
    colour = onyx_luma[..., None] + chroma_only * .72
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_roach_onyx(shape, seed, sm, _base_m, _base_r):
    surface = _surface(seed + 38117)
    m, r, cc = _material_states(surface)

    return (
        np.clip(_resize(m * sm, shape), 11, 247),
        np.clip(_resize(r * sm, shape), 16, 243),
        np.clip(_resize(cc * sm, shape), 8, 249),
    )
