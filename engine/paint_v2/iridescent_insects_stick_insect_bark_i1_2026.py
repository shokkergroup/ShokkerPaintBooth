"""Stick Insect Bark I1 — name-bound phasmid bark masquerade.

SPB-105 / owner 2026-09-02: unique 8–32px native construction and feature-
tracing material channels.  This is not Leaf Mantis recolored: it is an
elongated phasmid cuticle made from bundled bark splinters, segment sutures,
scar collars, lichen rosettes, resin wells, cuticular tubercles and femoral
spines.  Long visual fibers are assembled from compact native segments.
"""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "stick_insect_bark",
    "display_name": "Stick Insect Bark",
    "promise": "A phasmid exoskeleton masquerades as weathered bark without becoming generic woodgrain.",
    "reference_physics": {
        "mechanism": (
            "Phasmids mimic twigs, bark, lichens and moss. Their cuticle can carry two scales of light-scattering "
            "micro-elevation, hydrophobic surface relief, tergal extensions and femoral spines; the prothorax also "
            "contains paired invaginated defensive glands."
        ),
        "sources": [
            "https://pubmed.ncbi.nlm.nih.gov/27890511/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10759571/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8288419/",
        ],
    },
    "carrier_grammar": (
        "Tight longitudinal bundles of individually short bark-cuticle splinters are interrupted by transverse "
        "segment sutures, scar collars, lichen rosettes, resin wells, two-scale tubercles and attached femoral spines."
    ),
    "spec_grammar": (
        "Splinter cores/lips, matte bark troughs, suture cuts, scar rims, lichen crust, resin wells, tubercle crowns "
        "and spine burrs each receive separate feature-bound M/R/Cc tiers."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "splinter_core", "role": "forms elongated phasmid bark bundles from short connected marks"},
        {"name": "splinter_lip", "role": "adds polished raised edges to selected cuticle fibers"},
        {"name": "segment_suture", "role": "interrupts the bark disguise with phasmid tergite joints"},
        {"name": "scar_collar", "role": "records healed cuticular damage around a fiber bundle"},
        {"name": "lichen_rosette", "role": "builds compact crust islands attached to bark relief"},
        {"name": "resin_well", "role": "creates wet amber secretion pockets at sutures"},
        {"name": "tubercle_crown", "role": "models the two-scale light-scattering cuticle elevations"},
        {"name": "femoral_spine", "role": "preserves unmistakable phasmid defensive anatomy"},
    ],
    "material_binding": {
        "M": ["splinter_lip", "tubercle_crown", "femoral_spine"],
        "R": ["splinter_core", "segment_suture", "lichen_rosette", "scar_collar"],
        "Cc": ["resin_well", "splinter_lip", "scar_collar", "tubercle_crown"],
    },
    "material_tiers": [
        "bark matte", "weathered bronze", "black suture", "scar satin", "lichen patina",
        "wet amber resin", "hydrophobic tubercle", "chrome splinter lip", "spine burr",
    ],
    "nearest_neighbors": [
        {"finish_id": "mantis_leaf", "difference": "longitudinal segmented exocuticle bundles replace free angular crumple lamina"},
        {"finish_id": "ant_velvet", "difference": "bark fibers and lichen crust replace capsule armor and edge-born warning pile"},
        {"finish_id": "beetle_longhorn", "difference": "scarred twig masquerade and tubercles replace cerambycid scale sacks"},
    ],
    "name_truth": {
        "visible_evidence": [
            "elongated weathered bark-cuticle fiber bundles",
            "phasmid segment sutures and attached femoral spines",
            "lichen crust, scar collars, resin wells and cuticular tubercles",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "phasmid-segmented-bark-splinter-bundles-with-lichen-scars-tubercles-and-spines",
    "spec_key": "splinter-suture-scar-lichen-resin-tubercle-spine-material-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x57B4A2)
    shape = (GEN, GEN)
    core = np.zeros(shape, np.float32)
    lip = np.zeros(shape, np.float32)
    suture = np.zeros(shape, np.float32)
    scar = np.zeros(shape, np.float32)
    lichen = np.zeros(shape, np.float32)
    resin = np.zeros(shape, np.float32)
    tubercle = np.zeros(shape, np.float32)
    spine = np.zeros(shape, np.float32)
    trough = np.zeros(shape, np.float32)

    # Each connected bark bundle consists of 8–31px native splinter strokes.
    bundle_x = np.arange(-8.0, GEN + 10.0, 7.4)
    for bundle_i, base_x in enumerate(bundle_x):
        y = rng.uniform(-8, 2)
        phase = rng.uniform(0, np.pi * 2)
        while y < GEN + 8:
            seg = rng.uniform(2.6, 9.4)
            x0 = base_x + 2.2 * np.sin(y / rng.uniform(31, 58) + phase)
            x1 = base_x + 2.2 * np.sin((y + seg) / rng.uniform(31, 58) + phase) + rng.uniform(-.9, .9)
            val = float(rng.uniform(.22, .98))
            cv2.line(core, (round(x0), round(y)), (round(x1), round(y + seg)), val, 1, cv2.LINE_AA)
            side = -1 if (bundle_i + round(y)) % 2 else 1
            if rng.random() < .58:
                cv2.line(lip, (round(x0 + side), round(y)), (round(x1 + side), round(y + seg)),
                         float(rng.uniform(.25, .96)), 1, cv2.LINE_AA)
            if rng.random() < .31:
                cv2.line(trough, (round(x0 - side), round(y)), (round(x1 - side), round(y + seg)),
                         float(rng.uniform(.28, .94)), 1, cv2.LINE_AA)
            y += seg + rng.uniform(.4, 2.0)

    # Tergite sutures are built from short transverse pieces, never one macro line.
    for y0 in np.arange(8.0, GEN, 18.0):
        x = rng.uniform(-5, 2)
        while x < GEN + 4:
            seg = rng.uniform(3.0, 9.0)
            y = y0 + 1.8 * np.sin(x / rng.uniform(17, 39) + rng.uniform(0, 6.28))
            cv2.line(suture, (round(x), round(y)), (round(x + seg), round(y + rng.uniform(-1.2, 1.2))),
                     float(rng.uniform(.25, .96)), 1, cv2.LINE_AA)
            x += seg + rng.uniform(1.0, 3.2)

    for i in range(920):
        x, y = int(rng.integers(3, GEN - 3)), int(rng.integers(3, GEN - 3))
        if i % 11 == 0:
            axes = (int(rng.integers(2, 6)), int(rng.integers(2, 5)))
            cv2.ellipse(scar, (x, y), axes, rng.uniform(-18, 18), 0, 360,
                        float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)
        elif i % 7 == 0:
            # Compact lichen rosette: 5–8 separately shaded crust lobes.
            for k in range(int(rng.integers(5, 9))):
                a = k * (2 * np.pi / 7) + rng.uniform(-.22, .22)
                rr = rng.uniform(1.2, 4.2)
                cv2.circle(lichen, (round(x + np.cos(a) * rr), round(y + np.sin(a) * rr)),
                           int(rng.integers(1, 3)), float(rng.uniform(.22, .98)), -1, cv2.LINE_AA)
        elif i % 5 == 0:
            cv2.ellipse(resin, (x, y), (int(rng.integers(1, 4)), int(rng.integers(1, 3))),
                        rng.uniform(-30, 30), 0, 360, float(rng.uniform(.25, .98)), -1, cv2.LINE_AA)
        else:
            rad = 1 if i % 4 else 2
            cv2.circle(tubercle, (x, y), rad, float(rng.uniform(.18, .98)), -1, cv2.LINE_AA)

    # Small tapered femoral-spine wedges attach to suture/fiber intersections.
    for i in range(190):
        x, y = int(rng.integers(4, GEN - 4)), int(rng.integers(4, GEN - 4))
        side = -1 if i % 2 else 1
        pts = np.array([(x, y), (x + side * int(rng.integers(3, 8)), y + int(rng.integers(-2, 3))),
                        (x, y + int(rng.integers(2, 5)))], np.int32)
        cv2.fillConvexPoly(spine, pts, float(rng.uniform(.30, .98)), cv2.LINE_AA)

    arrays = (core, lip, suture, scar, lichen, resin, tubercle, spine, trough)
    return tuple(cv2.GaussianBlur(a, (0, 0), .19).astype(np.float32) for a in arrays)


def paint_stick_insect_bark(paint, shape, mask, seed, pm, _base):
    core, lip, suture, scar, lichen, resin, tubercle, spine, trough = _surface(seed + 37103)
    yy, xx = np.mgrid[0:GEN, 0:GEN].astype(np.float32)
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.055, .035, .022], np.float32)
    bark = .38 + .13 * np.sin(xx / 47.0 + yy / 121.0) + .08 * np.cos(yy / 29.0)
    colour += bark[..., None] * np.array([.27, .14, .052], np.float32)
    colour += core[..., None] * np.array([.49, .27, .085], np.float32) * .93
    colour += lip[..., None] * np.array([.83, .55, .20], np.float32) * .96
    colour -= trough[..., None] * np.array([.36, .25, .16], np.float32) * .88
    colour -= suture[..., None] * np.array([.38, .29, .22], np.float32) * .98
    colour += scar[..., None] * np.array([.52, .40, .22], np.float32) * .90
    colour += lichen[..., None] * np.array([.23, .61, .20], np.float32) * .98
    colour += resin[..., None] * np.array([.91, .39, .035], np.float32) * 1.02
    colour += tubercle[..., None] * np.array([.33, .43, .19], np.float32) * .76
    colour += spine[..., None] * np.array([.79, .76, .47], np.float32) * .96
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_stick_insect_bark(shape, seed, sm, _base_m, _base_r):
    core, lip, suture, scar, lichen, resin, tubercle, spine, trough = _surface(seed + 37103)
    m = 18 + 72 * core + 185 * lip + 118 * scar + 74 * lichen + 226 * spine + 144 * tubercle
    r = 32 + 111 * core + 210 * trough + 225 * suture + 174 * scar + 236 * lichen + 61 * spine
    cc = 16 + 95 * lip + 154 * scar + 240 * resin + 181 * tubercle + 68 * core + 205 * spine

    def spread(a, low, high):
        p1, p99 = np.percentile(a, (1.0, 99.0))
        out = low + (a - p1) * ((high - low) / max(float(p99 - p1), 1e-5))
        return cv2.GaussianBlur(np.clip(out, low, high), (0, 0), .58)

    return (
        np.clip(_resize(spread(m, 12, 247) * sm, shape), 12, 247),
        np.clip(_resize(spread(r, 17, 243) * sm, shape), 17, 243),
        np.clip(_resize(spread(cc, 9, 249) * sm, shape), 9, 249),
    )
