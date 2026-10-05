"""Bluebottle Mercury I1 — flow-aligned blowfly facets in liquid metal cuticle."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "bluebottle_mercury",
    "display_name": "Bluebottle Mercury",
    "promise": "A liquid-mercury bluebottle cuticle made from direction-changing corneal facet shoals, dark pseudopupils, wing-vein seams, pustulate lens dust, setulae and a sparse ginger beard.",
    "reference_physics": {
        "mechanism": (
            "Calliphora are named for a shiny metallic body; blowfly compound eyes arrange thousands of ommatidia in "
            "hexagonal rows whose orientation and density change across the eye. SEM studies report densely pustulate "
            "corneal surfaces, several sensillum classes, stem-vein setulae and species-specific orange facial hairs."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10762291/",
            "https://pubmed.ncbi.nlm.nih.gov/17339116/",
            "https://pubmed.ncbi.nlm.nih.gov/11016789/",
            "https://pubmed.ncbi.nlm.nih.gov/18343951/",
        ],
    },
    "carrier_grammar": (
        "Thousands of 8–30px convex mercury lenslets form locally curved shoals rather than a uniform honeycomb. "
        "Each lens owns a steel rim, displaced cobalt pseudopupil and pustulate dust; translucent calypter membranes, "
        "branching wing veins, stem setulae, spiracle crescents and short orange beard barbs interrupt named regions."
    ),
    "spec_grammar": (
        "Lens crown, steel rim, pseudopupil, lens pustule, membrane, vein, setula, spiracle and beard are independent "
        "material populations; M/R/Cc silhouette is generated from those exact masks without a decorative overlay."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "lens_crown", "role": "forms convex liquid-metal ommatidia"},
        {"name": "steel_rim", "role": "separates the changing facet rows"},
        {"name": "pseudopupil", "role": "darkens an optically displaced core"},
        {"name": "pustule", "role": "models dense corneal surface sculpture"},
        {"name": "calypter", "role": "introduces translucent wing membrane shoals"},
        {"name": "wing_vein", "role": "branches through membrane only"},
        {"name": "setula", "role": "adds short hairs along stem veins"},
        {"name": "spiracle", "role": "marks dark thoracic breathing crescents"},
        {"name": "ginger_barb", "role": "cites the orange facial beard"},
    ],
    "material_binding": {
        "M": ["lens_crown", "steel_rim", "wing_vein"],
        "R": ["pseudopupil", "pustule", "setula", "ginger_barb"],
        "Cc": ["lens_crown", "calypter", "spiracle"],
    },
    "material_tiers": [
        "black chitin", "blue mercury", "cyan lens", "steel rim", "cobalt pseudopupil",
        "grey corneal dust", "smoked calypter", "chrome vein", "brown setula", "ginger beard",
    ],
    "nearest_neighbors": [
        {"finish_id": "hoverfly_mirror", "difference": "changing convex ommatidial shoals replace axial mirror bars"},
        {"finish_id": "damselfly_cobalt", "difference": "faceted corneal cuticle replaces paired wing laminations"},
        {"finish_id": "scarab_sunplate", "difference": "displaced pseudopupil lenses replace radial helicoid sunplates"},
    ],
    "name_truth": {
        "visible_evidence": [
            "liquid blue-mercury facets", "direction-changing ommatidial rows", "dark pseudopupils",
            "pustulate corneal dust", "wing-vein setulae", "orange ginger hairs",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "bluebottle-mercury-changing-ommatidial-shoals-with-pseudopupils-calypters-veins-setulae-and-ginger-barbs",
    "spec_key": "bluebottle-lens-rim-pseudopupil-pustule-calypter-vein-setula-spiracle-beard-material-binding",
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
    # IRIDESCENT INSECTS card 49 / owner 2026-09-02: local optical-axis flow,
    # not a uniform honeycomb, recolored beetle scale, or generic rainbow spec.
    rng = np.random.default_rng(int(seed) ^ 0xB10EB077)
    z = np.zeros((GEN, GEN), np.float32)
    crown, rim, pupil, pustule, calypter = (z.copy() for _ in range(5))
    vein, setula, spiracle, beard = (z.copy() for _ in range(4))

    # Staggered facet rows bend and change spacing with the optical-axis field.
    step_y = 9.0
    for row, y0 in enumerate(np.arange(-10.0, GEN + 12.0, step_y)):
        xoff = 4.5 if row % 2 else 0.0
        for col, x0 in enumerate(np.arange(-10.0 + xoff, GEN + 12.0, 9.0)):
            bend = 5.0 * np.sin(x0 * .012 + y0 * .004) + 3.2 * np.sin(y0 * .021)
            x = x0 + 2.5 * np.sin(y0 * .016 + row * .17)
            y = y0 + bend
            theta = .62 * np.sin(x * .0067) + .34 * np.cos(y * .0091) + .18 * np.sin((x + y) * .013)
            radius = rng.uniform(3.0, 4.7) * (1.0 + .12 * np.sin(y * .018))
            pts = []
            for k in range(6):
                ang = theta + np.pi / 3.0 * k
                rr = radius * rng.uniform(.88, 1.10)
                pts.append((x + np.cos(ang) * rr, y + np.sin(ang) * rr))
            poly = np.asarray(pts, np.int32)
            level = float(rng.uniform(.34, .99))
            cv2.fillConvexPoly(crown, poly, level, cv2.LINE_AA)
            cv2.polylines(rim, [poly], True, float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)

            # Pseudopupil displacement changes coherently across the field.
            pd = np.array([np.cos(theta + .65), np.sin(theta + .65)]) * rng.uniform(.8, 1.8)
            pc = np.array([x, y]) + pd
            cv2.ellipse(pupil, tuple(np.int32(pc)), (max(1, int(radius * .42)), max(1, int(radius * .25))),
                        np.degrees(theta), 0, 360, float(rng.uniform(.40, .99)), -1, cv2.LINE_AA)
            # Densely pustulate corneal lens surface; bounded to the crown.
            if (row * 5 + col * 3) % 4 != 1:
                pa = theta + rng.uniform(-1.0, 1.0)
                pp = np.array([x, y]) + np.array([np.cos(pa), np.sin(pa)]) * radius * .62
                cv2.circle(pustule, tuple(np.int32(pp)), 1, float(rng.uniform(.38, .98)), -1, cv2.LINE_AA)

    # Narrow translucent calypter ribbons interrupt the facets without becoming macro wallpaper.
    for band in range(20):
        phase = rng.uniform(-np.pi, np.pi)
        base = -80.0 + band * 39.0
        points = []
        for x in np.arange(-20, GEN + 21, 8):
            y = base + .31 * x + 10.0 * np.sin(x * .026 + phase) + 3.0 * np.sin(x * .071 + band)
            points.append((int(x), int(y)))
        for a, b in zip(points[:-1], points[1:]):
            cv2.line(calypter, a, b, float(rng.uniform(.38, .93)), 3, cv2.LINE_AA)
            cv2.line(vein, a, b, float(rng.uniform(.46, .99)), 1, cv2.LINE_AA)
        # Short branches and setulae stay attached to a real vein.
        for q in range(5, len(points) - 4, 8):
            p = np.asarray(points[q], np.float32)
            branch_ang = -.72 + .18 * np.sin(q + band)
            tip = p + np.array([np.cos(branch_ang), np.sin(branch_ang)]) * rng.uniform(7.0, 10.0)
            cv2.line(vein, tuple(np.int32(p)), tuple(np.int32(tip)), float(rng.uniform(.46, .99)), 1, cv2.LINE_AA)
            for j in (0.25, .55, .82):
                root = p * (1 - j) + tip * j
                normal = np.array([-np.sin(branch_ang), np.cos(branch_ang)])
                end = root + normal * rng.choice((-1.0, 1.0)) * rng.uniform(2.5, 4.5)
                cv2.line(setula, tuple(np.int32(root)), tuple(np.int32(end)), float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)

    # Repeating thoracic spiracles and short orange postgenal beard barbs.
    for i in range(58):
        x, y = rng.uniform(0, GEN, 2)
        if i % 2:
            cv2.ellipse(spiracle, (int(x), int(y)), (rng.integers(3, 6), rng.integers(2, 4)),
                        rng.uniform(0, 180), 15, 325, float(rng.uniform(.44, .99)), 1, cv2.LINE_AA)
        else:
            angle = rng.uniform(-1.2, 1.2)
            a = np.array([x, y])
            b = a + np.array([np.cos(angle), np.sin(angle)]) * rng.uniform(4.0, 8.0)
            cv2.line(beard, tuple(np.int32(a)), tuple(np.int32(b)), float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)

    return tuple(cv2.GaussianBlur(a, (0, 0), .13).astype(np.float32)
                 for a in (crown, rim, pupil, pustule, calypter, vein, setula, spiracle, beard))


def _tier(channel, field, values, frequency, phase):
    sel = field > .075
    idx = np.floor(np.mod(np.clip(field, 0, 1) * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    crown, rim, pupil, pustule, calypter, vein, setula, spiracle, beard = surface
    m = np.full((GEN, GEN), 38.0, np.float32)
    r = np.full((GEN, GEN), 202.0, np.float32)
    cc = np.full((GEN, GEN), 26.0, np.float32)
    _tier(m, crown, (72, 108, 142, 176, 206, 230, 246, 252), 7.3, .11)
    _tier(m, rim, (138, 170, 198, 222, 240, 250), 6.7, .37)
    _tier(m, vein, (96, 136, 176, 210, 236, 250), 7.1, .71)
    _tier(r, pupil, (22, 54, 92, 138, 188, 232), 6.9, .19)
    _tier(r, pustule, (38, 78, 124, 168, 210, 244), 7.7, .43)
    _tier(r, setula, (66, 108, 154, 202, 242), 6.3, .67)
    _tier(r, beard, (84, 126, 170, 212, 246), 5.9, .83)
    _tier(cc, crown, (74, 110, 148, 184, 216, 240, 250), 7.5, .29)
    _tier(cc, calypter, (104, 142, 180, 214, 238, 250), 6.5, .53)
    _tier(cc, spiracle, (42, 86, 138, 190, 232, 248), 7.1, .79)
    return m, r, cc


def paint_bluebottle_mercury(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 49023)
    crown, rim, pupil, pustule, calypter, vein, setula, spiracle, beard = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = (.008, .012, .018)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(crown, (.015, .045, .11), (.10, .78, .98))
    # P2: every ommatidium keeps one coherent bluebottle-metal hue class.
    # The class comes from that crown's own construction level, not a detached
    # full-canvas rainbow field, so grayscale topology and spec causality stay intact.
    crown_sel = crown > .075
    mercury_palette = np.asarray([
        (.018, .035, .12), (.025, .16, .58), (.018, .46, .68),
        (.055, .70, .72), (.31, .62, .72), (.22, .12, .55),
        (.08, .32, .90), (.62, .82, .88),
    ], np.float32)
    crown_class = np.floor(np.mod(crown * 9.17 + .13, 1.0) * len(mercury_palette)).astype(np.int16)
    crown_colour = mercury_palette[np.clip(crown_class, 0, len(mercury_palette) - 1)]
    crown_gain = (.54 + .48 * np.clip(crown, 0, 1))[..., None]
    colour[crown_sel] = np.clip(crown_colour[crown_sel] * crown_gain[crown_sel], 0, 1)
    assign(rim, (.10, .16, .22), (.78, .94, 1.0))
    assign(pupil, (.002, .004, .012), (.025, .08, .22))
    assign(pustule, (.18, .22, .26), (.82, .90, .94))
    assign(calypter, (.018, .04, .065), (.22, .43, .58))
    assign(vein, (.10, .18, .22), (.72, .88, .94))
    assign(setula, (.045, .025, .018), (.36, .22, .12))
    assign(spiracle, (.002, .006, .010), (.05, .16, .21))
    assign(beard, (.14, .025, .004), (.98, .38, .035))

    m, r, cc = _material_states(surface)
    optical = (.46 * m + .28 * (255.0 - r) + .26 * cc) / 255.0
    luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - luma[..., None]
    mapped = .86 * np.power(np.clip(optical, 0, 1), 1.18)[..., None] + chroma * 1.58
    active = np.maximum.reduce(surface) > .075
    colour[active] = mapped[active]
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_bluebottle_mercury(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 49023))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
