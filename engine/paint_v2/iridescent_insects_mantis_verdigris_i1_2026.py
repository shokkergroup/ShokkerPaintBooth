"""Mantis Verdigris I1 — articulated raptorial cuticle in aged bronze."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "praying_mantis_verdigris",
    "display_name": "Mantis Verdigris",
    "promise": "An antique bronze raptorial-cuticle field folds through hinged femur/tibia plates, socketed spines, honeycomb grip faces and pale contact wear under living verdigris.",
    "reference_physics": {
        "mechanism": (
            "Praying-mantis raptorial forelegs combine differently sclerotized femur and tibia cuticle, rows of fixed and "
            "tiltable spines, elongated support sockets, genicular lobes, spur grooves, rough medial grip faces and smoother "
            "lateral surfaces. Fine honeycomb-like grooves and stiffness gradients tune friction and prey retention."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12181396/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5673847/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC12175983/",
        ],
    },
    "carrier_grammar": (
        "Dense folding chains of 8–32px bronze femur and tibia plates alternate across the full car; every chain owns dark "
        "joint membranes, elongated socket collars, fixed and tiltable spine teeth, honeycomb grip grooves, genicular rims, "
        "pale worn tips and anatomy-bounded verdigris blooms."
    ),
    "spec_grammar": (
        "Femur plate, tibia plate, hinge membrane, socket collar, fixed spine, tiltable spine, honeycomb grip, genicular rim, "
        "contact wear and verdigris bloom are named masks with distinct channel ownership."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "femur_plate", "role": "forms the stout load-bearing bronze half of each fold"},
        {"name": "tibia_plate", "role": "forms the shorter closing half of each fold"},
        {"name": "hinge_membrane", "role": "separates articulated plate pairs"},
        {"name": "elongated_socket", "role": "supports tiltable spines against reverse motion"},
        {"name": "fixed_spine", "role": "forms hard prey-retention teeth"},
        {"name": "tiltable_spine", "role": "adds mechanically graded movable teeth"},
        {"name": "honeycomb_grip", "role": "models rough medial grip microstructure"},
        {"name": "genicular_rim", "role": "reinforces the folding joint edge"},
        {"name": "contact_wear", "role": "polishes tooth tips and closing faces"},
        {"name": "verdigris_bloom", "role": "ages low-contact bronze regions without becoming random noise"},
    ],
    "material_binding": {
        "M": ["femur_plate", "tibia_plate", "fixed_spine", "genicular_rim", "contact_wear"],
        "R": ["hinge_membrane", "honeycomb_grip", "verdigris_bloom"],
        "Cc": ["elongated_socket", "tiltable_spine", "contact_wear", "verdigris_bloom"],
    },
    "material_tiers": [
        "old bronze femur", "dark bronze tibia", "flexible graphite hinge", "polished socket", "hard spine tip",
        "graded movable spine", "rough honeycomb grip", "genicular brass", "ivory contact wear", "wet verdigris",
    ],
    "nearest_neighbors": [
        {"finish_id": "mantis_leaf", "difference": "articulated bronze raptorial chains replace torn dead-leaf lamina, petioles and decay windows"},
        {"finish_id": "mantis_orchid", "difference": "hard socketed spine mechanics replace soft pink-white femoral-lobe fans"},
        {"finish_id": "weevil_gilded", "difference": "folding femur/tibia pairs and socket teeth replace longitudinal elytral striae and sawtooth scale fields"},
    ],
    "name_truth": {
        "visible_evidence": [
            "folded bronze raptorial plate chains", "socketed alternating spine teeth", "rough honeycomb grip faces", "bounded blue-green verdigris and pale worn tips",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "mantis-verdigris-folded-femur-tibia-chains-with-socketed-spines-grip-grooves-and-contact-wear",
    "spec_key": "mantis-femur-tibia-hinge-socket-fixed-tilting-grip-rim-wear-patina-channel-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x6A71D)
    z = np.zeros((GEN, GEN), np.float32)
    femur, tibia, hinge, socket, fixed = (z.copy() for _ in range(5))
    tilting, grip, rim, wear, patina = (z.copy() for _ in range(5))

    sx, sy = 11.0, 18.0
    idx = 0
    for row, cy0 in enumerate(np.arange(-8.0, GEN + 9.0, sy)):
        offset = sx * .5 if row % 2 else 0.0
        for col, cx0 in enumerate(np.arange(-10.0 + offset, GEN + 11.0, sx)):
            cx = int(round(cx0 + rng.uniform(-.8, .8)))
            cy = int(round(cy0 + rng.uniform(-.7, .7)))
            # P2: coherent end-to-end raptorial chains, not a crossing textile.
            flow = 18.0 + 6.0 * np.sin(cy0 * .031) + (3.0 if row % 2 else -3.0)
            theta = np.deg2rad(flow)
            dx, dy = np.cos(theta), np.sin(theta)
            nx, ny = -dy, dx

            joint = np.array([cx, cy], np.float32)
            a = joint - np.array([dx, dy]) * 6.0
            b = joint + np.array([dx, dy]) * 4.0
            width = 2.8
            femur_poly = np.array([
                a + np.array([nx, ny]) * width, joint + np.array([nx, ny]) * width,
                joint - np.array([nx, ny]) * width, a - np.array([nx, ny]) * width,
            ], np.int32)
            tibia_poly = np.array([
                joint + np.array([nx, ny]) * width, b + np.array([nx, ny]) * 1.9,
                b - np.array([nx, ny]) * 1.9, joint - np.array([nx, ny]) * width,
            ], np.int32)
            local = np.clip((.30 if row % 2 else .76) + .14 * np.sin(cx0 * .041 + cy0 * .019), .12, .92)
            cv2.fillConvexPoly(femur, femur_poly, float(.36 + .56 * local), cv2.LINE_AA)
            cv2.fillConvexPoly(tibia, tibia_poly, float(.42 + .50 * (1.0 - local)), cv2.LINE_AA)
            cv2.line(hinge, tuple(np.int32(joint - np.array([nx, ny]) * 3)),
                     tuple(np.int32(joint + np.array([nx, ny]) * 3)), float(rng.uniform(.42, .98)), 2, cv2.LINE_AA)
            cv2.ellipse(socket, (cx, cy), (3, 2), flow, 0, 360, float(rng.uniform(.40, .98)), 1, cv2.LINE_AA)
            cv2.ellipse(rim, (cx, cy), (4, 3), flow, 190, 350, float(rng.uniform(.40, .98)), 1, cv2.LINE_AA)

            # Alternating fixed/tiltable teeth stay attached to their plate.
            for tooth_i, frac in enumerate((-.65, -.18, .38)):
                root_pt = joint + np.array([dx, dy]) * (frac * 6.0) + np.array([nx, ny]) * width
                length = 3 + ((tooth_i + row + col) % 3)
                tip = root_pt + np.array([nx, ny]) * length + np.array([dx, dy]) * (1 if tooth_i == 1 else -1)
                field = tilting if tooth_i == 1 else fixed
                cv2.line(field, tuple(np.int32(root_pt)), tuple(np.int32(tip)), float(rng.uniform(.44, .99)), 2, cv2.LINE_AA)
                cap_a = tip - np.array([dx, dy]) * 1.5
                cap_b = tip + np.array([dx, dy]) * 1.5
                cv2.line(wear, tuple(np.int32(cap_a)), tuple(np.int32(cap_b)),
                         float(rng.uniform(.44, .98)), 1, cv2.LINE_AA)

            # Fine rough grip cells occupy the medial femur face only.
            for q in (-3, 0, 3):
                gp = joint - np.array([dx, dy]) * 3.0 + np.array([dx, dy]) * q * .45
                ga = gp - np.array([nx, ny]) * 1.4
                gb = gp + np.array([nx, ny]) * 1.4
                cv2.line(grip, tuple(np.int32(ga)), tuple(np.int32(gb)),
                         float(rng.uniform(.35, .96)), 1, cv2.LINE_AA)

            # Patina is anatomically bounded to low-contact plate recesses.
            if idx % 2 == 0:
                pp = joint - np.array([dx, dy]) * 4.0 - np.array([nx, ny]) * 1.0
                pa = pp - np.array([dx, dy]) * 2.5
                pb = pp + np.array([dx, dy]) * 2.5
                cv2.line(patina, tuple(np.int32(pa)), tuple(np.int32(pb)),
                         float(rng.uniform(.38, .96)), 2, cv2.LINE_AA)
            idx += 1

    arrays = (femur, tibia, hinge, socket, fixed, tilting, grip, rim, wear, patina)
    return tuple(cv2.GaussianBlur(a, (0, 0), .13).astype(np.float32) for a in arrays)


def _tier(channel_out, field, values, frequency, phase):
    sel = field > .075
    strength = np.clip(field, 0, 1)
    idx = np.floor(np.mod(strength * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel_out[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    femur, tibia, hinge, socket, fixed, tilting, grip, rim, wear, patina = surface
    m = np.full((GEN, GEN), 28.0, np.float32)
    r = np.full((GEN, GEN), 224.0, np.float32)
    cc = np.full((GEN, GEN), 18.0, np.float32)
    _tier(m, femur, (102, 136, 170, 202, 230, 250), 5.3, .11)
    _tier(m, tibia, (72, 112, 154, 196, 236), 4.7, .39)
    _tier(m, fixed, (166, 198, 224, 244, 252), 6.1, .67)
    _tier(m, rim, (122, 158, 194, 224, 246), 5.9, .23)
    _tier(m, wear, (184, 210, 232, 246, 252), 7.1, .53)
    _tier(r, hinge, (186, 208, 226, 242, 250), 4.9, .29)
    _tier(r, grip, (46, 82, 124, 176, 228), 6.7, .61)
    _tier(r, patina, (72, 108, 148, 194, 236), 5.7, .17)
    _tier(cc, socket, (118, 154, 190, 220, 244, 252), 5.1, .43)
    _tier(cc, tilting, (88, 132, 178, 216, 246), 6.3, .71)
    _tier(cc, wear, (164, 196, 224, 244, 252), 4.3, .19)
    _tier(cc, patina, (126, 162, 198, 226, 246), 6.9, .47)
    return m, r, cc


def paint_mantis_verdigris(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 45017)
    femur, tibia, hinge, socket, fixed, tilting, grip, rim, wear, patina = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.055, .075, .050], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(femur, (.08, .045, .015), (.52, .29, .065))
    assign(tibia, (.045, .030, .016), (.30, .16, .045))
    assign(hinge, (.008, .012, .014), (.06, .075, .065))
    assign(socket, (.18, .15, .08), (.74, .68, .36))
    assign(fixed, (.32, .24, .08), (.96, .86, .42))
    assign(tilting, (.18, .14, .08), (.76, .64, .32))
    assign(grip, (.025, .032, .022), (.16, .20, .11))
    assign(rim, (.22, .14, .04), (.84, .62, .16))
    assign(wear, (.52, .48, .31), (1.0, .95, .72))
    assign(patina, (.005, .17, .13), (.05, .84, .62))

    m, r, cc = _material_states(surface)
    luma = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    mapped = .72 * np.power(np.clip(luma, 0, 1), 1.62)[..., None] + chroma * 1.66
    coverage = np.maximum.reduce(surface)
    active = coverage > .075
    colour[active] = mapped[active]
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_mantis_verdigris(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 45017))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
