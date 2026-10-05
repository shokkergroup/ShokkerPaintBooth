"""Hornet Titanium I1 — micro-lamellar Vespa gaster armor."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "hornet_titanium",
    "display_name": "Hornet Titanium",
    "promise": "Titanium hornet gaster armor sweeps through fine turbine lamellae, black joint membranes, yellow pigment windows, pore reservoirs and elastic hinge glints.",
    "reference_physics": {
        "mechanism": (
            "Vespa gasters are articulated sclerites with intersegmental membranes and spiracles. Sternal glands form dense "
            "anterior pore bands and paired lateral pore clusters flanking a hyaline setal brush; some pores share small "
            "reservoir depressions. Insect cuticle is a helicoidal chitin composite, while resilin-rich hinge regions provide "
            "fatigue-resistant elastic response."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8868583/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC324569/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5082342/",
        ],
    },
    "carrier_grammar": (
        "Thousands of individually swept 8–30px titanium tergite lamellae form staggered, locally curving armor streams. "
        "Each stream carries dark articulation seams, anterior pore rails, paired gland reservoirs, yellow cuticle windows, "
        "hyaline brush filaments, spiracle collars and blue-violet elastic hinge glints."
    ),
    "spec_grammar": (
        "Titanium lamella, polished stria, black membrane, yellow window, pore rail, gland reservoir, brush filament, "
        "spiracle collar, elastic hinge and worn posterior lip are separate named masks with independent M/R/Cc tiers."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "titanium_lamella", "role": "forms the overlapping abdominal armor"},
        {"name": "swept_stria", "role": "gives each armor unit its turbine-like load direction"},
        {"name": "joint_membrane", "role": "separates articulated armor streams"},
        {"name": "yellow_window", "role": "binds warning pigment to selected cuticle plates"},
        {"name": "pore_rail", "role": "models continuous anterior gland pore bands"},
        {"name": "gland_reservoir", "role": "models pores recessed into shared depressions"},
        {"name": "hyaline_brush", "role": "fills the median gap between paired pore clusters"},
        {"name": "spiracle_collar", "role": "marks repeated respiratory ports"},
        {"name": "elastic_hinge", "role": "adds fatigue-resistant blue-violet hinge material"},
        {"name": "worn_lip", "role": "polishes posterior sclerite edges"},
    ],
    "material_binding": {
        "M": ["titanium_lamella", "swept_stria", "spiracle_collar", "worn_lip"],
        "R": ["joint_membrane", "pore_rail", "gland_reservoir", "hyaline_brush"],
        "Cc": ["yellow_window", "elastic_hinge", "spiracle_collar", "worn_lip"],
    },
    "material_tiers": [
        "smoked titanium", "bright titanium", "black flexible membrane", "yellow candy cuticle", "dry pore rail",
        "wet gland reservoir", "hyaline brush", "dark spiracle", "violet elastic hinge", "ice-polished lip",
    ],
    "nearest_neighbors": [
        {"finish_id": "wasp_warning", "difference": "micro-lamellar titanium anatomy and gland systems replace broad warning bands"},
        {"finish_id": "praying_mantis_verdigris", "difference": "swept gaster lamellae and pore rails replace serrated raptorial chains and verdigris"},
        {"finish_id": "mayfly_silver", "difference": "solid articulated abdominal armor replaces translucent wing membrane and vein forks"},
    ],
    "name_truth": {
        "visible_evidence": [
            "staggered titanium abdominal lamellae", "black articulation membranes", "yellow cuticle windows",
            "paired gland pores and spiracle collars", "blue-violet elastic hinge glints",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "hornet-titanium-swept-gaster-lamellae-with-pore-rails-reservoirs-brushes-spiracles-and-hinges",
    "spec_key": "hornet-lamella-stria-membrane-yellow-pore-reservoir-brush-spiracle-hinge-lip-channel-binding",
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
    # IRIDESCENT INSECTS card 46 / owner 2026-09-02: unique name-true carrier,
    # no shared insect field, no warning-stripe recolor, all visible primitives 8–32px at 2048².
    rng = np.random.default_rng(int(seed) ^ 0x71A9E)
    z = np.zeros((GEN, GEN), np.float32)
    lamella, stria, membrane, yellow, pore = (z.copy() for _ in range(5))
    reservoir, brush, spiracle, hinge, lip = (z.copy() for _ in range(5))

    # P4: coherent 80–100px turbine assemblies, each built only from 8–32px native cuticle primitives.
    pitch_x, pitch_y = 31.0, 36.0
    for row, y0 in enumerate(np.arange(-18.0, GEN + 19.0, pitch_y)):
        offset = (row % 3) * 8.5 + rng.uniform(-3.0, 3.0)
        phase = rng.uniform(-np.pi, np.pi)
        for col, x0 in enumerate(np.arange(-18.0 + offset, GEN + 19.0, pitch_x)):
            cx = x0 + rng.uniform(-4.2, 4.2)
            cy = y0 + rng.uniform(-2.6, 2.6) + 8.5 * np.sin(x0 * .022 + phase) + 2.8 * np.sin(x0 * .061 + row)
            c = np.array([cx, cy], np.float32)
            spin = 28.0 * np.sin(cx * .011 + cy * .016) + rng.uniform(-14.0, 14.0)
            blades = 4 + ((row * 3 + col * 5) % 3)
            for blade_i in range(blades):
                base_angle = spin + blade_i * (360.0 / blades)
                # Three short tangent plates make one swept blade without any macro primitive.
                for seg in range(3):
                    r0 = 4.0 + seg * 4.2
                    r1 = r0 + 5.4
                    sweep = base_angle + seg * 10.0
                    th = np.deg2rad(sweep)
                    dx, dy = np.cos(th), np.sin(th)
                    nx, ny = -dy, dx
                    p0 = c + np.array([dx, dy]) * r0
                    p1 = c + np.array([dx, dy]) * r1
                    width0, width1 = 2.3 - seg * .25, 1.55 - seg * .18
                    poly = np.array([
                        p0 + np.array([nx, ny]) * width0,
                        p1 + np.array([nx, ny]) * width1,
                        p1 - np.array([nx, ny]) * width1 * .45,
                        p0 - np.array([nx, ny]) * width0 * .55,
                    ], np.int32)
                    cv2.fillConvexPoly(lamella, poly, float(rng.uniform(.34, .99)), cv2.LINE_AA)
                    cv2.line(stria, tuple(np.int32(p0)), tuple(np.int32(p1)),
                             float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)
                    if seg == 2:
                        la = p1 - np.array([nx, ny]) * 1.4
                        lb = p1 + np.array([nx, ny]) * 1.4
                        cv2.line(lip, tuple(np.int32(la)), tuple(np.int32(lb)),
                                 float(rng.uniform(.40, .98)), 1, cv2.LINE_AA)
                    if (row * 3 + col + blade_i + seg) % 13 in (0, 1):
                        cv2.fillConvexPoly(yellow, poly, float(rng.uniform(.38, .99)), cv2.LINE_AA)

            # Central hornet gland system: paired reservoirs, pore collar, hyaline brush and occasional spiracle.
            for side in (-1.0, 1.0):
                rp = c + np.array([side * 3.1, 0.0])
                cv2.circle(reservoir, tuple(np.int32(rp)), 3, float(rng.uniform(.46, .99)), 1, cv2.LINE_AA)
            for a in range(0, 360, 45):
                th = np.deg2rad(a + spin)
                pp = c + np.array([np.cos(th), np.sin(th)]) * 6.0
                cv2.circle(pore, tuple(np.int32(pp)), 1, float(rng.uniform(.40, .98)), -1, cv2.LINE_AA)
            for q in (-2, 0, 2):
                cv2.line(brush, (int(cx + q), int(cy - 3)), (int(cx + q), int(cy + 3)),
                         float(rng.uniform(.40, .96)), 1, cv2.LINE_AA)
            cv2.circle(membrane, tuple(np.int32(c)), 3, float(rng.uniform(.38, .92)), -1, cv2.LINE_AA)
            cv2.circle(hinge, tuple(np.int32(c)), 5, float(rng.uniform(.42, .98)), 1, cv2.LINE_AA)
            if (row * 5 + col * 7) % 11 == 0:
                cv2.ellipse(spiracle, tuple(np.int32(c)), (5, 3), spin, 0, 360,
                            float(rng.uniform(.54, .99)), 1, cv2.LINE_AA)

            # One directional bridge carries each turbine into the next aerodynamic stream segment.
            stream_angle = np.arctan(8.5 * .022 * np.cos(x0 * .022 + phase))
            va = np.array([np.cos(stream_angle), np.sin(stream_angle)])
            p0 = c + va * 14.5
            p1 = c + va * rng.uniform(18.0, 22.0)
            cv2.line(membrane, tuple(np.int32(p0)), tuple(np.int32(p1)),
                     float(rng.uniform(.34, .90)), 2, cv2.LINE_AA)
            cv2.line(hinge, tuple(np.int32(p0 + (0, 1))), tuple(np.int32(p1 + (0, 1))),
                     float(rng.uniform(.36, .96)), 1, cv2.LINE_AA)

    return tuple(cv2.GaussianBlur(a, (0, 0), .16).astype(np.float32)
                 for a in (lamella, stria, membrane, yellow, pore, reservoir, brush, spiracle, hinge, lip))


def _tier(channel, field, values, frequency, phase):
    sel = field > .075
    idx = np.floor(np.mod(np.clip(field, 0, 1) * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    lamella, stria, membrane, yellow, pore, reservoir, brush, spiracle, hinge, lip = surface
    m = np.full((GEN, GEN), 34.0, np.float32)
    r = np.full((GEN, GEN), 214.0, np.float32)
    cc = np.full((GEN, GEN), 22.0, np.float32)
    _tier(m, lamella, (92, 122, 154, 184, 214, 238, 250), 6.3, .11)
    _tier(m, stria, (144, 174, 202, 226, 244, 252), 7.1, .37)
    _tier(m, spiracle, (62, 104, 152, 202, 238), 5.7, .71)
    _tier(m, lip, (168, 194, 218, 238, 250), 6.7, .53)
    _tier(r, membrane, (182, 204, 222, 238, 248), 5.1, .23)
    _tier(r, pore, (76, 112, 154, 198, 232), 6.9, .47)
    _tier(r, reservoir, (34, 62, 96, 142, 198), 6.1, .79)
    _tier(r, brush, (118, 154, 188, 220, 242), 5.9, .17)
    _tier(cc, yellow, (72, 108, 148, 190, 224, 246), 6.5, .41)
    _tier(cc, hinge, (126, 162, 198, 226, 246, 252), 7.3, .67)
    _tier(cc, spiracle, (58, 98, 148, 202, 238), 5.5, .29)
    _tier(cc, lip, (148, 180, 210, 234, 248), 6.3, .83)
    return m, r, cc


def paint_hornet_titanium(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 46019)
    lamella, stria, membrane, yellow, pore, reservoir, brush, spiracle, hinge, lip = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = (.018, .022, .028)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(lamella, (.08, .10, .13), (.76, .83, .91))
    assign(stria, (.22, .27, .34), (.98, .99, 1.00))
    assign(membrane, (.004, .006, .010), (.035, .045, .060))
    assign(yellow, (.30, .17, .005), (1.00, .78, .035))
    assign(pore, (.05, .055, .060), (.24, .28, .31))
    assign(reservoir, (.008, .010, .014), (.15, .19, .23))
    assign(brush, (.30, .34, .38), (.90, .94, .94))
    assign(spiracle, (.005, .007, .012), (.20, .27, .34))
    assign(hinge, (.08, .04, .20), (.40, .52, 1.00))
    assign(lip, (.32, .38, .45), (1.00, .99, .90))

    m, r, cc = _material_states(surface)
    optical = (.42 * m + .34 * (255.0 - r) + .24 * cc) / 255.0
    src_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - src_luma[..., None]
    mapped = .94 * np.power(np.clip(optical, 0, 1), .94)[..., None] + chroma * 1.48
    active = np.maximum.reduce(surface) > .075
    colour[active] = mapped[active]
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_hornet_titanium(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 46019))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
