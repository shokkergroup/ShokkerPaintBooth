"""Scarab Sunplate I1 — compact graded-helicoid reflector fans.

SPB-105 / owner 2026-09-02: dense 8–32px primitives, independently authored
carrier/spec silhouette, research-led name truth, and exact material binding.
"""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "scarab_sunplate",
    "display_name": "Scarab Sunplate",
    "promise": "Golden scarab helicoids break into compact sunplate fans whose radial lamellae and diffraction teeth answer light differently.",
    "reference_physics": {
        "mechanism": (
            "Golden scarab cuticle uses graded-pitch helicoidal chitin multilayers as a broadband reflector and "
            "left-handed circular polarizer. Scarab cuticle can also superimpose diffraction gratings on multilayer "
            "iridescence; pitch and lamellar thickness vary through the exocuticle."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6352678/",
            "https://www.nature.com/articles/s41598-018-24761-w",
            "https://pubmed.ncbi.nlm.nih.gov/20665535/",
            "https://pubmed.ncbi.nlm.nih.gov/16564066/",
        ],
    },
    "carrier_grammar": (
        "A borderless staggered field of compact radial sunplate fans is assembled from individual 8–30px wedge "
        "lamellae, broken pitch arcs, circular-polarizer cores, diffraction teeth, pore canals, seams and worn gold rims."
    ),
    "spec_grammar": (
        "Helicoid wedges, pitch arcs, polarizer cores, diffraction teeth, pore canals, black seams, cobalt underplates "
        "and worn rims each receive distinct M/R/Cc tier families on their exact visible masks."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "helicoid_wedge", "role": "forms compact radial broadband-reflector lamellae"},
        {"name": "graded_pitch_arc", "role": "records increasing helicoid pitch through broken rings"},
        {"name": "polarizer_core", "role": "marks the circularly polarizing centre of each fan"},
        {"name": "diffraction_tooth", "role": "adds a second structural-colour mechanism at fan edges"},
        {"name": "pore_canal", "role": "crosses multilayers with narrow exocuticle pores"},
        {"name": "underplate", "role": "shows cobalt reflector beneath selected gold fans"},
        {"name": "shell_seam", "role": "breaks the field into scarab cuticle plates"},
        {"name": "worn_rim", "role": "confines abrasion to sunplate perimeter segments"},
    ],
    "material_binding": {
        "M": ["helicoid_wedge", "diffraction_tooth", "worn_rim"],
        "R": ["graded_pitch_arc", "shell_seam", "pore_canal"],
        "Cc": ["polarizer_core", "underplate", "worn_rim"],
    },
    "material_tiers": [
        "broadband gold", "cobalt underplate", "black shell seam", "graded satin pitch",
        "circular-polarizer core", "hot clear rim", "chrome diffraction tooth", "dry pore canal", "worn gold edge",
    ],
    "nearest_neighbors": [
        {"finish_id": "weevil_gilded", "difference": "compact radial helicoid fans replace longitudinal punctured sawtooth scale rows"},
        {"finish_id": "weevil_opal", "difference": "graded multilayer wedges replace single-diamond rosette scales"},
        {"finish_id": "beetle_buprestid", "difference": "radial scarab reflector plates replace thermosensitive jewel-beetle layering"},
    ],
    "name_truth": {
        "visible_evidence": [
            "many compact gold radial sunplates",
            "broken graded-pitch arcs and bright diffraction teeth",
            "cobalt underplates, black seams and polarizer cores",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "scarab-compact-radial-helicoid-sunplates-with-pitch-arcs-polarizer-cores-and-diffraction-teeth",
    "spec_key": "scarab-wedge-pitch-core-tooth-pore-underplate-seam-rim-material-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x5CA4AB)
    z = np.zeros((GEN, GEN), np.float32)
    wedge, pitch, core, tooth = (z.copy() for _ in range(4))
    pore, under, seam, wear = (z.copy() for _ in range(4))

    # P3 owner-eye rebuild: tessellated shell plates replace isolated floral
    # icons. Every plate is continuous; the fine radial lamellae live inside.
    sx, sy = 16.0, 13.8
    idx = 0
    for row, cy0 in enumerate(np.arange(-10.0, GEN + 11.0, sy)):
        offset = 0.0 if row % 2 == 0 else sx * .5
        for cx0 in np.arange(-10.0 + offset, GEN + 11.0, sx):
            cx = int(round(cx0 + rng.uniform(-1.3, 1.3)))
            cy = int(round(cy0 + rng.uniform(-1.0, 1.0)))
            radius = int(rng.integers(8, 11))
            phase = float(rng.uniform(0, 360))
            hex_pts = np.array([
                [cx + np.cos(np.deg2rad(phase + k * 60)) * radius,
                 cy + np.sin(np.deg2rad(phase + k * 60)) * radius]
                for k in range(6)
            ], np.int32)
            cv2.fillConvexPoly(under, hex_pts, float(rng.uniform(.28, .86)), cv2.LINE_AA)
            cv2.polylines(seam, [hex_pts], True, float(rng.uniform(.24, .88)), 1, cv2.LINE_AA)

            for k in range(8):
                a0 = np.deg2rad(phase + k * 45.0 + rng.uniform(-4, 4))
                a1 = a0 + np.deg2rad(rng.uniform(25, 34))
                r0, r1 = int(rng.integers(2, 4)), radius
                pts = np.array([
                    [cx + np.cos(a0) * r0, cy + np.sin(a0) * r0],
                    [cx + np.cos(a0) * r1, cy + np.sin(a0) * r1],
                    [cx + np.cos(a1) * r1, cy + np.sin(a1) * r1],
                    [cx + np.cos(a1) * r0, cy + np.sin(a1) * r0],
                ], np.int32)
                cv2.fillConvexPoly(wedge, pts, float(rng.uniform(.26, .99)), cv2.LINE_AA)
                if (k + idx) % 2 == 0:
                    tx = int(round(cx + np.cos((a0 + a1) * .5) * r1))
                    ty = int(round(cy + np.sin((a0 + a1) * .5) * r1))
                    cv2.circle(tooth, (tx, ty), 1, float(rng.uniform(.36, .99)), -1, cv2.LINE_AA)

            for band, frac in enumerate((.43, .68, .92)):
                start = phase + band * 37 + rng.uniform(-14, 14)
                cv2.ellipse(pitch, (cx, cy), (max(2, int(radius * frac)),) * 2, 0,
                            start, start + rng.uniform(150, 260), float(rng.uniform(.28, .96)), 1, cv2.LINE_AA)
            cv2.circle(core, (cx, cy), int(rng.integers(1, 3)), float(rng.uniform(.40, .99)), -1, cv2.LINE_AA)

            if idx % 3 == 0:
                theta = np.deg2rad(phase + rng.uniform(0, 360))
                px = int(round(cx + np.cos(theta) * radius * .65))
                py = int(round(cy + np.sin(theta) * radius * .65))
                cv2.line(pore, (px - 1, py - 2), (px + 1, py + 2), float(rng.uniform(.30, .95)), 1, cv2.LINE_AA)
            if idx % 5 == 0:
                start = phase + rng.uniform(0, 180)
                cv2.ellipse(wear, (cx, cy), (radius, radius), 0, start, start + rng.uniform(35, 90),
                            float(rng.uniform(.32, .98)), 2, cv2.LINE_AA)
            idx += 1

    arrays = (wedge, pitch, core, tooth, pore, under, seam, wear)
    return tuple(cv2.GaussianBlur(a, (0, 0), .14).astype(np.float32) for a in arrays)


def _material_states(surface):
    wedge, pitch, core, tooth, pore, under, seam, wear = surface
    m = np.full((GEN, GEN), 34.0, np.float32)
    r = np.full((GEN, GEN), 214.0, np.float32)
    cc = np.full((GEN, GEN), 28.0, np.float32)

    def assign(field, mv, rv, cv):
        sel = field > .075
        strength = np.clip(field, 0, 1)
        m[sel] = mv[0] + (mv[1] - mv[0]) * strength[sel]
        r[sel] = rv[0] + (rv[1] - rv[0]) * strength[sel]
        cc[sel] = cv[0] + (cv[1] - cv[0]) * strength[sel]

    assign(under, (42, 102), (236, 176), (146, 216))
    assign(wedge, (186, 246), (124, 58), (22, 82))
    assign(pitch, (26, 84), (22, 86), (216, 252))
    assign(core, (112, 178), (242, 180), (28, 94))
    assign(tooth, (226, 252), (148, 82), (164, 226))
    assign(pore, (8, 58), (182, 242), (92, 26))
    assign(seam, (84, 148), (18, 68), (34, 104))
    assign(wear, (146, 214), (206, 138), (238, 178))
    return m, r, cc


def paint_scarab_sunplate(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 41017)
    wedge, pitch, core, tooth, pore, under, seam, wear = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.012, .009, .005], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(under, (.015, .035, .12), (.04, .22, .60))
    assign(wedge, (.28, .16, .004), (1.0, .84, .10))
    assign(pitch, (.42, .29, .016), (.98, .89, .24))
    assign(core, (.12, .022, .05), (.48, .10, .16))
    assign(tooth, (.58, .46, .09), (1.0, .98, .62))
    assign(pore, (.006, .005, .004), (.07, .035, .01))
    assign(seam, (.003, .003, .005), (.055, .022, .012))
    assign(wear, (.35, .24, .022), (.92, .70, .10))

    m, r, cc = _material_states(surface)
    luma = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    colour = np.power(np.clip(luma, 0, 1), 1.46)[..., None] + chroma * 1.46
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_scarab_sunplate(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 41017))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 242),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
