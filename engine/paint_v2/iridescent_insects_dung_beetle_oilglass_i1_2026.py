"""Dung Beetle Oilglass I1 — petroleum thin film over corrugated scarab elytra."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "dung_beetle_oil",
    "display_name": "Dung Beetle Oilglass",
    "promise": "Petroleum thin-film color flows through corrugated dung-beetle shell basins, wax channels, microcracks, pores, setae and helicoidal cuticle—not a generic oil-slick texture.",
    "reference_physics": {
        "mechanism": (
            "Dung-beetle elytra carry compound corrugated bumps, larger and smaller elliptical protrusions, tiny cracks, "
            "pores, sparse setae and wax-modified wetting. Their cuticle is multilayered, with parallel fibres rotating by "
            "about 70 degrees between adjacent layers. Polarization-sensitive dung-beetle ommatidia use orthogonal microvilli."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC3464267/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5060978/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC3522911/",
        ],
    },
    "carrier_grammar": (
        "A continuous dark elytral skin is deformed by irregular nested corrugation basins. Fine petroleum interference "
        "contours follow those basins and merge into wax channels; shell microcracks, pore collars, flat setae, 70-degree "
        "cross-ply windows, wet troughs, mud contact shadows and sparse orthogonal compass glints interrupt the film."
    ),
    "spec_grammar": (
        "Corrugation crown, oil contour, wax channel, microcrack, pore collar, flat seta, cross-ply window, wet trough, "
        "mud contact and compass glint each own distinct M/R/Cc tiers following visible shell anatomy."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "corrugation_crown", "role": "forms large and small elliptical shell bumps"},
        {"name": "oil_contour", "role": "carries thin-film color along shell height"},
        {"name": "wax_channel", "role": "modifies wetting between bump families"},
        {"name": "microcrack", "role": "breaks the elytral film along real surface defects"},
        {"name": "pore_collar", "role": "marks secretion openings"},
        {"name": "flat_seta", "role": "adds sparse hairs lying against the shell"},
        {"name": "cross_ply_window", "role": "reveals rotating helicoidal fibre layers"},
        {"name": "wet_trough", "role": "collects glossy oil-water in corrugation lows"},
        {"name": "mud_contact", "role": "adds matte dung-soil contact only in protected troughs"},
        {"name": "compass_glint", "role": "echoes orthogonal polarization microvilli sparingly"},
    ],
    "material_binding": {
        "M": ["corrugation_crown", "oil_contour", "pore_collar", "cross_ply_window"],
        "R": ["oil_contour", "microcrack", "flat_seta", "mud_contact"],
        "Cc": ["wax_channel", "wet_trough", "compass_glint", "oil_contour"],
    },
    "material_tiers": [
        "petroleum shell", "iridescent oil contour", "waxy channel", "dry shell crack", "metal pore collar",
        "satin seta", "helicoid fibre window", "wet cobalt trough", "matte earth contact", "polarized compass flash",
    ],
    "nearest_neighbors": [
        {"finish_id": "scarab_night", "difference": "nested petroleum corrugation topography replaces lenticular absorber armor and chiral crescents"},
        {"finish_id": "beetle_ground", "difference": "wet oilglass height contours replace dry black carabid diffraction mesh"},
        {"finish_id": "beetle_rainbow", "difference": "name-bound shell basins, cracks and wax wetting replace a broad full-spectrum iridescent shell"},
    ],
    "name_truth": {
        "visible_evidence": [
            "oil-film contours following corrugated elytra", "elliptical shell bumps", "wax channels and wet troughs",
            "microcracks, pores and flat setae", "helicoidal windows and compass glints",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "dung-beetle-oilglass-continuous-petroleum-film-over-irregular-corrugation-basins-with-wax-cracks-pores-setae-helicoids-and-troughs",
    "spec_key": "dung-oilglass-crown-contour-wax-crack-pore-seta-crossply-trough-mud-compass-channel-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x01D61A55)
    yy, xx = np.mgrid[0:GEN, 0:GEN].astype(np.float32)
    # Smooth shell height combines rotated fine corrugations with irregular elliptical basins.
    height = .38 * np.sin(xx * .031 + yy * .011) + .31 * np.sin(xx * .014 - yy * .027 + 1.7)
    height += .21 * np.sin(xx * .043 + yy * .037 + .8)
    crown = np.zeros((GEN, GEN), np.float32)
    for row, cy0 in enumerate(np.arange(-12.0, GEN + 13.0, 17.0)):
        offset = 8.0 if row % 2 else 0.0
        for cx0 in np.arange(-14.0 + offset, GEN + 15.0, 19.0):
            cx, cy = cx0 + rng.uniform(-4, 4), cy0 + rng.uniform(-3, 3)
            rx, ry = rng.uniform(5.0, 9.0), rng.uniform(3.0, 6.0)
            angle = rng.uniform(-35, 35)
            blob = np.zeros((GEN, GEN), np.float32)
            cv2.ellipse(blob, (int(cx), int(cy)), (int(rx), int(ry)), angle, 0, 360,
                        float(rng.uniform(.42, .98)), -1, cv2.LINE_AA)
            blob = cv2.GaussianBlur(blob, (0, 0), 2.0)
            crown = np.maximum(crown, blob)
            height += blob * rng.uniform(.26, .58)
    height = cv2.GaussianBlur(height, (0, 0), 1.2)
    hnorm = cv2.normalize(height, None, 0, 1, cv2.NORM_MINMAX).astype(np.float32)

    phase = np.mod(hnorm * 11.0 + .20 * np.sin(xx * .019 - yy * .023), 1.0)
    contour = np.clip(1.0 - np.abs(phase - .5) * 6.5, 0, 1).astype(np.float32)
    trough = np.clip((.34 - hnorm) * 4.2, 0, 1).astype(np.float32)
    wax = np.clip(1.0 - np.abs(np.mod(hnorm * 5.0 + xx * .002, 1.0) - .18) * 9.0, 0, 1).astype(np.float32)
    crack = np.zeros((GEN, GEN), np.float32)
    pore = np.zeros_like(crack); seta = np.zeros_like(crack); cross = np.zeros_like(crack)
    mud = np.zeros_like(crack); compass = np.zeros_like(crack)

    # Broken crack walks are anatomical defects, not noise overlays.
    for i in range(72):
        p = np.array([rng.uniform(0, GEN), rng.uniform(0, GEN)], np.float32)
        heading = rng.uniform(-np.pi, np.pi)
        for _ in range(rng.integers(3, 8)):
            q = p + np.array([np.cos(heading), np.sin(heading)]) * rng.uniform(4.0, 8.0)
            cv2.line(crack, tuple(np.int32(p)), tuple(np.int32(q)), float(rng.uniform(.38, .98)), 1, cv2.LINE_AA)
            p = q; heading += rng.uniform(-.55, .55)

    # Named fine structures remain attached to bump and trough anatomy.
    for i in range(900):
        x, y = int(rng.integers(4, GEN - 4)), int(rng.integers(4, GEN - 4))
        if i % 5 == 0 and crown[y, x] > .12:
            cv2.circle(pore, (x, y), 2, float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)
        elif i % 5 == 1 and crown[y, x] > .10:
            ang = rng.uniform(-np.pi, np.pi); q = (int(x + np.cos(ang) * 5), int(y + np.sin(ang) * 5))
            cv2.line(seta, (x, y), q, float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
        elif i % 5 == 2 and trough[y, x] > .12:
            cv2.ellipse(mud, (x, y), (3, 2), rng.uniform(0, 180), 0, 360,
                        float(rng.uniform(.38, .96)), -1, cv2.LINE_AA)
        elif i % 5 == 3 and crown[y, x] > .16:
            cv2.line(cross, (x - 3, y - 1), (x + 3, y + 1), float(rng.uniform(.40, .98)), 1, cv2.LINE_AA)
            cv2.line(cross, (x - 1, y + 3), (x + 1, y - 3), float(rng.uniform(.40, .98)), 1, cv2.LINE_AA)
        elif trough[y, x] > .16:
            cv2.line(compass, (x - 3, y), (x + 3, y), float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)
            cv2.line(compass, (x, y - 3), (x, y + 3), float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)

    arrays = (crown, contour, wax, crack, pore, seta, cross, trough, mud, compass, hnorm, phase)
    return tuple(a.astype(np.float32) for a in arrays)


def _tier(channel, field, values, frequency, phase):
    sel = field > .075
    idx = np.floor(np.mod(np.clip(field, 0, 1) * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    crown, contour, wax, crack, pore, seta, cross, trough, mud, compass, _height, _phase = surface
    m = np.full((GEN, GEN), 44.0, np.float32)
    r = np.full((GEN, GEN), 198.0, np.float32)
    cc = np.full((GEN, GEN), 34.0, np.float32)
    _tier(m, crown, (78, 112, 148, 184, 216, 240, 252), 6.3, .11)
    _tier(m, contour, (104, 140, 176, 208, 232, 248), 7.1, .43)
    _tier(m, pore, (126, 164, 198, 226, 246), 5.7, .71)
    _tier(m, cross, (94, 134, 178, 216, 244), 6.7, .27)
    _tier(r, crack, (36, 78, 126, 178, 224, 246), 6.1, .37)
    _tier(r, contour, (42, 84, 132, 180, 224, 248), 6.7, .21)
    _tier(r, seta, (92, 132, 174, 212, 240), 5.5, .63)
    _tier(r, mud, (166, 194, 218, 236, 248), 5.9, .17)
    _tier(cc, wax, (74, 112, 154, 196, 228, 248), 6.3, .49)
    _tier(cc, trough, (118, 154, 190, 220, 244, 252), 5.7, .79)
    _tier(cc, compass, (144, 178, 208, 232, 248), 6.9, .29)
    _tier(cc, contour, (92, 132, 176, 214, 242), 7.3, .57)
    return m, r, cc


def paint_dung_beetle_oilglass(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 48029)
    crown, contour, wax, crack, pore, seta, cross, trough, mud, compass, height, phase = surface
    stops = np.array([
        [.012, .018, .026], [.09, .015, .18], [.10, .12, .58], [.00, .48, .62],
        [.06, .62, .24], [.72, .62, .04], [.88, .22, .03], [.48, .02, .34],
    ], np.float32)
    pos = np.mod(phase + .13 * height, 1.0) * len(stops)
    i0 = np.floor(pos).astype(np.int16) % len(stops); i1 = (i0 + 1) % len(stops)
    f = (pos - np.floor(pos))[..., None]
    colour = stops[i0] * (1 - f) + stops[i1] * f
    colour *= (.34 + .78 * height[..., None])

    def assign(field, dark, bright):
        sel = field > .075; strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(contour, (.04, .06, .16), (.85, .32, .96))
    assign(wax, (.02, .12, .16), (.14, .86, .78))
    assign(crack, (.003, .004, .006), (.07, .045, .025))
    assign(pore, (.12, .16, .22), (.82, .90, .96))
    assign(seta, (.08, .055, .025), (.48, .34, .12))
    assign(cross, (.12, .08, .28), (.64, .72, 1.0))
    assign(trough, (.005, .025, .06), (.02, .22, .54))
    assign(mud, (.055, .028, .012), (.26, .12, .035))
    assign(compass, (.18, .12, .30), (.94, .82, 1.0))

    m, r, cc = _material_states(surface)
    optical = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    src_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - src_luma[..., None]
    colour = .82 * np.power(np.clip(optical, 0, 1), 1.34)[..., None] + chroma * 1.62
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_dung_beetle_oilglass(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 48029))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
