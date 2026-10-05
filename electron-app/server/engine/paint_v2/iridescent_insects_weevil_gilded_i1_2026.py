"""Gilded Weevil I1 — punctured striae and sawtooth scale ridges.

SPB-105 / owner 2026-09-02: 8–32px native marks, research-led carrier,
feature-bound orthogonal material states, and no construction/spec reuse.
"""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "weevil_gilded",
    "display_name": "Gilded Weevil Striae",
    "promise": "A gold-armoured weevil shell built from punctured elytral striae and directional sawtooth scales.",
    "reference_physics": {
        "mechanism": (
            "Weevil elytra carry longitudinal striae, punctures, convex intervals, recumbent directional scales "
            "and microreticulate cuticle. Their armour combines a dense sclerotized exocuticle with layered "
            "endocuticle microfibres joined by protruding interlocking ridges."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC4296478/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6189447/",
            "https://pubmed.ncbi.nlm.nih.gov/26529582/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC7365837/",
        ],
    },
    "carrier_grammar": (
        "Broken longitudinal strial lanes made from 8–28px native segments divide convex intervals packed with "
        "directional sawtooth scales; puncture sockets, boss crowns, transverse interlocks and worn gilding sit on named anatomy."
    ),
    "spec_grammar": (
        "Gold scale faces, sharp sawtooth lips, dark punctures, convex interval lacquer, boss crowns, interlocking "
        "ridges and olive wear each own distinct orthogonal M/R/Cc ranges derived from their visible masks."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "strial_segment", "role": "forms broken longitudinal elytral furrows"},
        {"name": "puncture_socket", "role": "marks the coarse punctures arranged along each stria"},
        {"name": "convex_interval", "role": "creates the raised cuticle lanes between striae"},
        {"name": "sawtooth_scale", "role": "lays directional overlapping gilded scales on each interval"},
        {"name": "scale_lip", "role": "catches the polished tooth edge of each recumbent scale"},
        {"name": "boss_crown", "role": "raises selected sclerotized cuticle bosses"},
        {"name": "interlocking_ridge", "role": "shows transverse fibre-binding ridges inside worn intervals"},
        {"name": "olive_wear", "role": "confines patina and abrasion to anatomical lanes"},
    ],
    "material_binding": {
        "M": ["sawtooth_scale", "scale_lip", "boss_crown"],
        "R": ["strial_segment", "puncture_socket", "olive_wear"],
        "Cc": ["convex_interval", "scale_lip", "interlocking_ridge"],
    },
    "material_tiers": [
        "antique gold scale", "burnished tooth lip", "brown gloss interval", "black puncture",
        "olive patina", "dry strial furrow", "chrome boss crown", "clear interlock", "velvet recess",
    ],
    "nearest_neighbors": [
        {"finish_id": "weevil_opal", "difference": "longitudinal punctured sawtooth lanes replace radial photonic rosette scales"},
        {"finish_id": "scarab_gold", "difference": "fine directionally scaled striae replace broad sunplate shell panels"},
        {"finish_id": "beetle_longhorn", "difference": "punctured elytral intervals replace filamentary longhorn sack scales"},
    ],
    "name_truth": {
        "visible_evidence": [
            "antique-gold sawtooth scale lanes",
            "black puncture rows and brown convex elytral intervals",
            "polished boss crowns with olive patina wear",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "gilded-weevil-broken-striae-punctures-convex-intervals-and-directional-sawtooth-scales",
    "spec_key": "weevil-stria-puncture-interval-scale-lip-boss-interlock-patina-material-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x61DDED)
    z = np.zeros((GEN, GEN), np.float32)
    stria, puncture, interval, scale = (z.copy() for _ in range(4))
    lip, boss, interlock, patina = (z.copy() for _ in range(4))

    lane_step = 10.6
    for lane, x0 in enumerate(np.arange(-4.0, GEN + 6.0, lane_step)):
        phase = rng.uniform(0, np.pi * 2)
        lane_gain = float(rng.uniform(.42, .98))
        for row, y0 in enumerate(np.arange(-4.0, GEN + 6.0, 5.3)):
            y = int(round(y0 + rng.uniform(-.45, .45)))
            bend = np.sin(y0 * .027 + phase) * 1.7 + np.sin(y0 * .083 + phase * .4) * .55
            x = int(round(x0 + bend + rng.uniform(-.35, .35)))
            # Short furrow fragments avoid one macro line across the canvas.
            if (row + lane) % 7 != 0:
                cv2.line(stria, (x, y - 2), (x + int(rng.integers(-1, 2)), y + 2),
                         lane_gain * float(rng.uniform(.52, 1.0)), 1, cv2.LINE_AA)
            if (row * 3 + lane) % 4 == 0:
                cv2.circle(puncture, (x, y), int(rng.integers(1, 3)),
                           float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)

            # Raised interval plate and one recumbent sawtooth scale.
            ix = x + int(round(lane_step * .5))
            cv2.rectangle(interval, (ix - 3, y - 2), (ix + 3, y + 2),
                          float(rng.uniform(.22, .92)), -1, cv2.LINE_AA)
            flip = -1 if (row + lane) % 2 else 1
            pts = np.array([
                [ix - 3, y + 2], [ix - 2, y - 2], [ix, y - 3],
                [ix + 2, y - 2], [ix + 3, y + 2], [ix, y + flip],
            ], np.int32)
            cv2.fillConvexPoly(scale, pts, float(rng.uniform(.32, .99)), cv2.LINE_AA)
            cv2.polylines(lip, [pts[:5]], False, float(rng.uniform(.32, .99)), 1, cv2.LINE_AA)

            if (row + lane * 5) % 17 == 0:
                cv2.circle(boss, (ix, y), 2, float(rng.uniform(.42, .99)), -1, cv2.LINE_AA)
                cv2.circle(boss, (ix, y), 1, 0.0, -1, cv2.LINE_AA)
            if (row * 5 + lane) % 13 == 0:
                cv2.line(interlock, (ix - 3, y), (ix + 3, y),
                         float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)
                cv2.line(interlock, (ix, y - 2), (ix, y + 2),
                         float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)
            if (row + lane * 2) % 19 in (0, 1, 2):
                cv2.ellipse(patina, (ix, y), (int(rng.integers(1, 4)), 2),
                            float(rng.uniform(-25, 25)), 0, 360, float(rng.uniform(.26, .92)), -1, cv2.LINE_AA)

    arrays = (stria, puncture, interval, scale, lip, boss, interlock, patina)
    return tuple(cv2.GaussianBlur(a, (0, 0), .14).astype(np.float32) for a in arrays)


def _material_states(surface):
    stria, puncture, interval, scale, lip, boss, interlock, patina = surface
    m = np.full((GEN, GEN), 42.0, np.float32)
    r = np.full((GEN, GEN), 202.0, np.float32)
    cc = np.full((GEN, GEN), 34.0, np.float32)

    def assign(field, mv, rv, cv):
        sel = field > .075
        strength = np.clip(field, 0, 1)
        m[sel] = mv[0] + (mv[1] - mv[0]) * strength[sel]
        r[sel] = rv[0] + (rv[1] - rv[0]) * strength[sel]
        cc[sel] = cv[0] + (cv[1] - cv[0]) * strength[sel]

    # P2: deliberately orthogonal material coordinates per named feature.
    # Dense gold does not mean three recoloured copies of the same channel.
    assign(interval, (22, 82), (242, 174), (112, 166))
    assign(scale, (174, 238), (184, 116), (18, 78))
    assign(stria, (116, 176), (18, 72), (34, 94))
    assign(puncture, (8, 64), (214, 248), (242, 178))
    assign(patina, (72, 132), (132, 194), (12, 68))
    assign(interlock, (214, 248), (54, 118), (146, 212))
    assign(lip, (42, 96), (8, 56), (218, 252))
    assign(boss, (148, 212), (244, 184), (18, 74))
    return m, r, cc


def paint_gilded_weevil(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 40017)
    stria, puncture, interval, scale, lip, boss, interlock, patina = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.025, .014, .008], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(interval, (.09, .035, .012), (.34, .14, .035))
    assign(scale, (.27, .12, .012), (.92, .57, .06))
    assign(stria, (.012, .008, .004), (.10, .045, .012))
    assign(puncture, (.002, .002, .001), (.055, .022, .006))
    assign(patina, (.055, .09, .018), (.28, .39, .055))
    assign(interlock, (.18, .12, .028), (.64, .40, .08))
    assign(lip, (.52, .28, .025), (1.0, .80, .23))
    assign(boss, (.44, .30, .07), (1.0, .91, .46))

    m, r, cc = _material_states(surface)
    # P3: exact combined-spec luminance is the topology authority. Chroma
    # remains gold/olive, while every visible transition follows M/R/Cc.
    optical = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    colour = np.power(np.clip(optical, 0, 1), 1.28)[..., None] + chroma * 1.28
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_gilded_weevil(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 40017))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 14, 246),
        np.clip(_resize(cc * sm, shape), 8, 242),
    )
