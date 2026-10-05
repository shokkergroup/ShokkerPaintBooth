"""Leafcutter Copper I1 — zinc-edged mandible cut paths in worked copper."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "leafcutter_copper",
    "display_name": "Leafcutter Copper",
    "promise": "Controlled copper mandible sheaves carry hundreds of individually cut green leaf plates with zinc-bright teeth, directional wear scores, clay packing and red oxide recesses.",
    "reference_physics": {
        "mechanism": (
            "Atta leafcutter mandibles use sharp toothed cutting margins in anchor-and-drag and symmetric sawing motions. "
            "Cutting edges are the hardest regions and are enriched with zinc; repeated abrasive work blunts distal teeth and "
            "leaves measurable wear. Mandibular joints also combine smooth articulations with spine-like and hairy surfaces."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10577030/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11008964/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC4736916/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10577034/",
        ],
    },
    "carrier_grammar": (
        "Long, gently undulating copper mandible stems travel in controlled diagonal sheaves across the full car. Hundreds "
        "of alternating 8–32px green leaf plates remain physically attached to those stems; every leaf carries a zinc saw "
        "margin, tooth wedges, a wear midrib, a polished tip, and bounded clay, oxide, boss and secretion details."
    ),
    "spec_grammar": (
        "Jaw plate, zinc cutting edge, tooth wedge, abrasion score, leaf fibre, clay pack, oxide recess, articulation boss, "
        "secretion puncture and polished tip are separately tiered masks; spec follows those masks exactly."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "jaw_plate", "role": "forms paired copper mandible trails"},
        {"name": "zinc_edge", "role": "hardens the opposing cutting margins"},
        {"name": "tooth_wedge", "role": "anchors and saws the leaf seam"},
        {"name": "abrasion_score", "role": "records directional cutting wear"},
        {"name": "leaf_fibre", "role": "retains torn green tissue inside each cut"},
        {"name": "clay_pack", "role": "adds matte soil residue in protected jaw recesses"},
        {"name": "oxide_recess", "role": "ages low-contact copper without generic patina noise"},
        {"name": "joint_boss", "role": "marks smooth articulation points"},
        {"name": "secretion_puncture", "role": "darkens repeated processed leaf punctures"},
        {"name": "polished_tip", "role": "brightens worn distal tooth ends"},
    ],
    "material_binding": {
        "M": ["jaw_plate", "zinc_edge", "tooth_wedge"],
        "R": ["abrasion_score", "clay_pack", "oxide_recess"],
        "Cc": ["leaf_fibre", "joint_boss", "secretion_puncture", "polished_tip"],
    },
    "material_tiers": [
        "hammered copper jaw", "zinc-rich edge", "hard tooth wedge", "dry wear score", "wet leaf fibre",
        "matte clay", "red oxide recess", "polished joint", "dark secretion", "chrome-worn tip",
    ],
    "nearest_neighbors": [
        {"finish_id": "praying_mantis_verdigris", "difference": "leaf-bearing diagonal cutting sheaves replace compact folding raptorial chains"},
        {"finish_id": "ant_velvet", "difference": "hard copper cutting mechanics replace soft velvet pile and brood-grooming fibres"},
        {"finish_id": "weevil_gilded", "difference": "opposed jaw edges and torn leaf wakes replace elytral furrows and sawtooth scale intervals"},
    ],
    "name_truth": {
        "visible_evidence": [
            "controlled diagonal copper mandible sheaves", "hundreds of attached green cut leaves", "opposing zinc teeth", "directional blade wear", "clay and red oxide in recesses",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "leafcutter-copper-controlled-diagonal-mandible-sheaves-with-attached-zinc-edged-green-leaf-plates-and-clay-oxide-wear",
    "spec_key": "leafcutter-jaw-edge-tooth-score-fibre-clay-oxide-boss-puncture-tip-material-binding",
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
def _surface_rejected_p3(seed):
    # IRIDESCENT INSECTS card 47 / owner 2026-09-02: paired shearing carrier,
    # not another ant recolor or generic copper texture; all primitives 8–32px native.
    rng = np.random.default_rng(int(seed) ^ 0x1EAFC)
    z = np.zeros((GEN, GEN), np.float32)
    jaw, edge, tooth, score, fibre = (z.copy() for _ in range(5))
    clay, oxide, boss, puncture, tip = (z.copy() for _ in range(5))

    # P2: independently oriented anchor-and-drag trajectories replace horizontal cable lanes.
    for lane in range(48):
        centre_x = rng.uniform(-40.0, GEN + 40.0)
        centre_y = rng.uniform(-40.0, GEN + 40.0)
        heading = rng.uniform(-np.pi, np.pi)
        hx, hy = np.cos(heading), np.sin(heading)
        nx0, ny0 = -hy, hx
        path_length = rng.uniform(340.0, 620.0)
        phase = rng.uniform(-np.pi, np.pi)
        amp = rng.uniform(7.0, 14.0)
        period = rng.uniform(.018, .034)
        for seg, u0 in enumerate(np.arange(-path_length * .5, path_length * .5, 7.2)):
            u1 = u0 + rng.uniform(6.2, 8.4)
            v0 = amp * np.sin(u0 * period + phase) + 3.0 * np.sin(u0 * .057 + lane)
            v1 = amp * np.sin(u1 * period + phase) + 3.0 * np.sin(u1 * .057 + lane)
            x0, y0 = centre_x + u0 * hx + v0 * nx0, centre_y + u0 * hy + v0 * ny0
            x1, y1 = centre_x + u1 * hx + v1 * nx0, centre_y + u1 * hy + v1 * ny0
            xm = (x0 + x1) * .5
            dx, dy = x1 - x0, y1 - y0
            mag = max(np.hypot(dx, dy), 1e-5)
            dx, dy = dx / mag, dy / mag
            nx, ny = -dy, dx
            separation = 8.2 + 1.8 * np.sin(xm * .031 + lane)
            for side in (-1.0, 1.0):
                a = np.array([x0 + nx * separation * side, y0 + ny * separation * side])
                b = np.array([x1 + nx * separation * side, y1 + ny * separation * side])
                half = rng.uniform(1.7, 2.5)
                poly = np.array([
                    a + np.array([nx, ny]) * half,
                    b + np.array([nx, ny]) * half * .72,
                    b - np.array([nx, ny]) * half * .72,
                    a - np.array([nx, ny]) * half,
                ], np.int32)
                cv2.fillConvexPoly(jaw, poly, float(rng.uniform(.34, .99)), cv2.LINE_AA)
                inner_a = a - np.array([nx, ny]) * side * half * .82
                inner_b = b - np.array([nx, ny]) * side * half * .64
                cv2.line(edge, tuple(np.int32(inner_a)), tuple(np.int32(inner_b)),
                         float(rng.uniform(.44, .99)), 1, cv2.LINE_AA)

                # Opposing wedge teeth point into the leaf seam.
                if (seg + lane + int(side)) % 2 == 0:
                    root = inner_a * .28 + inner_b * .72
                    apex = root - np.array([nx, ny]) * side * rng.uniform(2.4, 3.8)
                    left = root - np.array([dx, dy]) * 1.4
                    right = root + np.array([dx, dy]) * 1.4
                    cv2.fillConvexPoly(tooth, np.array([left, right, apex], np.int32),
                                       float(rng.uniform(.42, .99)), cv2.LINE_AA)
                    cv2.circle(tip, tuple(np.int32(apex)), 1, float(rng.uniform(.48, .99)), -1, cv2.LINE_AA)

                # Directional wear scores stay on the jaw plate.
                for q in (.30, .62):
                    p = a * (1 - q) + b * q
                    sa = p - np.array([nx, ny]) * 1.5
                    sb = p + np.array([nx, ny]) * 1.5
                    cv2.line(score, tuple(np.int32(sa)), tuple(np.int32(sb)),
                             float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
                if (seg + lane * 3) % 9 == 0:
                    bp = a * .35 + b * .65
                    cv2.circle(boss, tuple(np.int32(bp)), 2, float(rng.uniform(.44, .99)), 1, cv2.LINE_AA)
                if (seg * 5 + lane) % 11 in (0, 1):
                    op = a * .60 + b * .40
                    cv2.line(oxide, tuple(np.int32(op - np.array([dx, dy]) * 2.0)),
                             tuple(np.int32(op + np.array([dx, dy]) * 2.0)), float(rng.uniform(.40, .97)), 2, cv2.LINE_AA)

            # Three overlapping fine strips make a broad shredded leaf body without a macro primitive.
            centre = np.array([xm, (y0 + y1) * .5])
            for band in (-.62, 0.0, .62):
                fp0 = np.array([x0, y0]) + np.array([nx, ny]) * separation * band
                fp1 = np.array([x1, y1]) + np.array([nx, ny]) * separation * band
                cv2.line(fibre, tuple(np.int32(fp0)), tuple(np.int32(fp1)),
                         float(rng.uniform(.38, .98)), 3, cv2.LINE_AA)
                for q in (.30, .68):
                    rp = fp0 * (1 - q) + fp1 * q
                    ra = rp - np.array([nx, ny]) * 1.6
                    rb = rp + np.array([nx, ny]) * 1.6
                    cv2.line(score, tuple(np.int32(ra)), tuple(np.int32(rb)),
                             float(rng.uniform(.34, .92)), 1, cv2.LINE_AA)
            if (seg * 3 + lane) % 13 == 0:
                cv2.circle(puncture, tuple(np.int32(centre)), 2, float(rng.uniform(.44, .99)), -1, cv2.LINE_AA)
            if (seg + lane * 7) % 8 == 0:
                cp = centre + np.array([nx, ny]) * rng.uniform(-7.0, 7.0)
                cv2.ellipse(clay, tuple(np.int32(cp)), (3, 2), np.degrees(np.arctan2(dy, dx)), 0, 360,
                            float(rng.uniform(.36, .96)), -1, cv2.LINE_AA)

    return tuple(cv2.GaussianBlur(a, (0, 0), .15).astype(np.float32)
                 for a in (jaw, edge, tooth, score, fibre, clay, oxide, boss, puncture, tip))


@lru_cache(maxsize=2)
def _surface_v4(seed):
    """P4 botanical rebuild; P1–P3 trail carriers remain only as rejected evidence."""
    rng = np.random.default_rng(int(seed) ^ 0x4C0FF)
    z = np.zeros((GEN, GEN), np.float32)
    jaw, edge, tooth, score, fibre = (z.copy() for _ in range(5))
    clay, oxide, boss, puncture, tip = (z.copy() for _ in range(5))

    base_heading = np.deg2rad(17.0)
    base_tangent = np.array([np.cos(base_heading), np.sin(base_heading)], np.float32)
    base_normal = np.array([-base_tangent[1], base_tangent[0]], np.float32)
    for stem_i in range(28):
        heading = base_heading + np.deg2rad(9.0 * np.sin(stem_i * .73))
        hx, hy = np.cos(heading), np.sin(heading)
        nx, ny = -hy, hx
        centre = np.array([GEN * .5, GEN * .5], np.float32)
        centre += base_normal * ((stem_i - 13.5) * 26.0)
        centre += base_tangent * rng.uniform(-85.0, 85.0)
        length = rng.uniform(760.0, 920.0)
        phase = rng.uniform(-np.pi, np.pi)
        amp = rng.uniform(6.0, 16.0)
        freq = rng.uniform(.012, .025)
        previous = None
        for seg, u in enumerate(np.arange(-length * .5, length * .5, 7.0)):
            v = amp * np.sin(u * freq + phase) + 2.2 * np.sin(u * .061 + stem_i)
            p = centre + np.array([hx, hy]) * u + np.array([nx, ny]) * v
            if previous is not None:
                cv2.line(jaw, tuple(np.int32(previous)), tuple(np.int32(p)),
                         float(rng.uniform(.36, .98)), 3, cv2.LINE_AA)
                if (seg + stem_i) % 5 == 0:
                    cv2.line(oxide, tuple(np.int32(previous)), tuple(np.int32(p)),
                             float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
            previous = p
            # Alternating attached leaf fragments: each 19–32px long and 8–18px wide at native scale.
            dv = amp * freq * np.cos(u * freq + phase)
            tangent = np.array([hx, hy]) + np.array([nx, ny]) * dv
            tangent /= max(np.linalg.norm(tangent), 1e-5)
            normal = np.array([-tangent[1], tangent[0]])
            side = -1.0 if (seg // 2 + stem_i) % 2 else 1.0
            leaf_len = rng.uniform(7.5, 10.0)
            leaf_w = rng.uniform(3.5, 5.0)
            root = p + tangent * rng.uniform(-1.0, 1.0)
            leaf_tip = root + normal * side * leaf_len + tangent * rng.uniform(-1.5, 1.5)
            mid = (root + leaf_tip) * .5
            left = mid - tangent * leaf_w
            right = mid + tangent * leaf_w
            poly = np.array([root, left, leaf_tip, right], np.int32)
            cv2.fillConvexPoly(fibre, poly, float(rng.uniform(.36, .99)), cv2.LINE_AA)
            cv2.polylines(edge, [poly], True, float(rng.uniform(.42, .99)), 1, cv2.LINE_AA)
            cv2.line(score, tuple(np.int32(root)), tuple(np.int32(leaf_tip)),
                     float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
            # Two small zinc tooth wedges bite along the distal margin.
            for q in (.48, .72):
                rp = root * (1 - q) + leaf_tip * q
                ta = rp - tangent * 1.2
                tb = rp + tangent * 1.2
                apex = rp + normal * side * 1.8
                cv2.fillConvexPoly(tooth, np.array([ta, tb, apex], np.int32),
                                   float(rng.uniform(.44, .99)), cv2.LINE_AA)
            cv2.circle(tip, tuple(np.int32(leaf_tip)), 1, float(rng.uniform(.48, .99)), -1, cv2.LINE_AA)
            if (seg + stem_i * 3) % 8 == 0:
                cv2.circle(boss, tuple(np.int32(root)), 2, float(rng.uniform(.42, .98)), 1, cv2.LINE_AA)
            if (seg * 3 + stem_i) % 11 == 0:
                cv2.circle(puncture, tuple(np.int32(mid)), 1, float(rng.uniform(.44, .99)), -1, cv2.LINE_AA)
            if (seg + stem_i * 5) % 13 == 0:
                cp = root - normal * side * 2.0
                cv2.ellipse(clay, tuple(np.int32(cp)), (3, 2), np.degrees(heading), 0, 360,
                            float(rng.uniform(.38, .96)), -1, cv2.LINE_AA)

    return tuple(cv2.GaussianBlur(a, (0, 0), .15).astype(np.float32)
                 for a in (jaw, edge, tooth, score, fibre, clay, oxide, boss, puncture, tip))


def _tier(channel, field, values, frequency, phase):
    sel = field > .075
    idx = np.floor(np.mod(np.clip(field, 0, 1) * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    jaw, edge, tooth, score, fibre, clay, oxide, boss, puncture, tip = surface
    m = np.full((GEN, GEN), 30.0, np.float32)
    r = np.full((GEN, GEN), 220.0, np.float32)
    cc = np.full((GEN, GEN), 20.0, np.float32)
    _tier(m, jaw, (92, 126, 158, 190, 220, 242, 252), 6.3, .13)
    _tier(m, edge, (172, 198, 220, 238, 250), 6.9, .41)
    _tier(m, tooth, (146, 178, 206, 232, 248), 5.7, .67)
    _tier(r, score, (24, 72, 126, 184, 232, 248), 6.5, .37)
    _tier(r, clay, (118, 164, 202, 232, 248), 5.3, .17)
    _tier(r, oxide, (54, 104, 158, 208, 244), 6.7, .47)
    _tier(cc, fibre, (92, 132, 176, 214, 242), 5.7, .53)
    _tier(cc, boss, (142, 174, 204, 230, 248), 6.9, .71)
    _tier(cc, puncture, (54, 92, 142, 198, 238), 5.5, .31)
    _tier(cc, tip, (168, 198, 224, 242, 252), 7.1, .89)
    return m, r, cc


def paint_leafcutter_copper(paint, shape, mask, seed, pm, _base):
    surface = _surface_v4(seed + 47023)
    jaw, edge, tooth, score, fibre, clay, oxide, boss, puncture, tip = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = (.035, .018, .012)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(jaw, (.15, .045, .012), (.92, .37, .08))
    assign(edge, (.36, .32, .25), (.98, .96, .78))
    assign(tooth, (.30, .14, .035), (1.0, .64, .18))
    assign(score, (.055, .022, .012), (.26, .08, .02))
    assign(fibre, (.025, .10, .025), (.22, .74, .12))
    assign(clay, (.12, .055, .02), (.46, .23, .07))
    assign(oxide, (.12, .012, .005), (.62, .06, .012))
    assign(boss, (.22, .10, .025), (.88, .62, .22))
    assign(puncture, (.004, .008, .006), (.06, .11, .06))
    assign(tip, (.46, .42, .31), (1.0, .98, .84))

    m, r, cc = _material_states(surface)
    optical = (.44 * m + .32 * (255.0 - r) + .24 * cc) / 255.0
    src_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - src_luma[..., None]
    mapped = .90 * np.power(np.clip(optical, 0, 1), 1.05)[..., None] + chroma * 1.52
    active = np.maximum.reduce(surface) > .075
    colour[active] = mapped[active]
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_leafcutter_copper(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface_v4(seed + 47023))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
