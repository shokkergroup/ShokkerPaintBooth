"""Jewel Spider Cuticle I1 — guanocyte mosaic and fluorescent microspheres."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "jewel_spider",
    "display_name": "Jewel Spider Cuticle",
    "promise": "A transparent spider cuticle reveals a packed guanocyte jewel mosaic, silver guanine doublets, ruby fluorescent microspheres and silk-root filaments.",
    "reference_physics": {
        "mechanism": (
            "Phoroncidia rubroargentea combines closely packed soft guanocytes at triple-grain junctions with irregular "
            "silver guanine microplate doublets and red fluorescent microspheres above the reflectors. Spider structural "
            "colour also uses transparent cuticle, multilayers, gratings and scale/seta geometry to tune iridescence."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5832734/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8326826/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5014068/",
        ],
    },
    "carrier_grammar": (
        "A complete borderless mosaic of irregular 14–32px guanocyte cells meets at soft triple-grain junctions; every cell "
        "contains offset guanine platelet doublets, with sparse attached ruby microsphere chains and silk-root filaments."
    ),
    "spec_grammar": (
        "Guanocyte body, junction, platelet face, doublet gap, fluorescent microsphere shell/core, silk root and transparent "
        "cuticle rim are separate named masks with channel-specific M/R/Cc ownership."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "guanocyte_cell", "role": "forms the complete soft-packed optical substrate"},
        {"name": "triple_grain_junction", "role": "marks contact between adjacent guanocytes"},
        {"name": "guanine_platelet", "role": "provides irregular broadband silver-green reflection"},
        {"name": "platelet_doublet_gap", "role": "separates the paired outer guanine layers"},
        {"name": "fluorescent_microsphere", "role": "loads ruby fluorophore above selected reflectors"},
        {"name": "microsphere_core", "role": "creates a dark absorptive center within ruby spheres"},
        {"name": "silk_root_filament", "role": "anchors the jewel field to spider cuticle anatomy"},
        {"name": "transparent_cuticle_rim", "role": "adds wet optical windows above guanocyte boundaries"},
    ],
    "material_binding": {
        "M": ["guanine_platelet", "platelet_doublet_gap", "fluorescent_microsphere"],
        "R": ["guanocyte_cell", "triple_grain_junction", "microsphere_core"],
        "Cc": ["transparent_cuticle_rim", "silk_root_filament", "fluorescent_microsphere"],
    },
    "material_tiers": [
        "emerald guanocyte", "silver guanine", "blue-green platelet edge", "doublet shadow", "ruby fluorosphere",
        "absorptive sphere core", "soft grain membrane", "silk-root satin", "transparent wet cuticle",
    ],
    "nearest_neighbors": [
        {"finish_id": "weevil_opal", "difference": "soft polygonal guanocytes and slivered doublets replace concave circular scale pits and photonic diamond rosettes"},
        {"finish_id": "scarab_sunplate", "difference": "irregular intracellular reflectors replace radial helicoid wedges inside hard hex plates"},
        {"finish_id": "butterfly_emperor", "difference": "packed spider cells and ruby microspheres replace wing-scale eyelet anatomy"},
    ],
    "name_truth": {
        "visible_evidence": [
            "emerald-black cellular jewel mosaic", "silver-green guanine doublet slivers", "attached ruby fluorescent bead chains", "fine silk-root filaments",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "jewel-spider-soft-guanocyte-mosaic-with-guanine-doublets-ruby-microspheres-and-silk-roots",
    "spec_key": "spider-cell-junction-platelet-doublet-sphere-core-silkroot-cuticle-channel-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0x5A1D3)
    z = np.zeros((GEN, GEN), np.float32)
    cell, junction, plate, gap = (z.copy() for _ in range(4))
    sphere, core, root, cuticle = (z.copy() for _ in range(4))

    sx, sy = 9.2, 8.1
    idx = 0
    for row, cy0 in enumerate(np.arange(-7.0, GEN + 8.0, sy)):
        offset = sx * .5 if row % 2 else 0.0
        for col, cx0 in enumerate(np.arange(-7.0 + offset, GEN + 8.0, sx)):
            cx = int(round(cx0 + rng.uniform(-1.35, 1.35)))
            cy = int(round(cy0 + rng.uniform(-1.20, 1.20)))
            radius = float(rng.uniform(4.0, 5.9))
            phase = float(rng.uniform(-30, 30))
            pts = []
            for k in range(6):
                a = np.deg2rad(phase + k * 60.0 + rng.uniform(-14, 14))
                rr = radius * rng.uniform(.76, 1.18)
                pts.append([int(round(cx + np.cos(a) * rr)), int(round(cy + np.sin(a) * rr))])
            poly = np.asarray(pts, np.int32)
            local = .5 + .5 * np.sin(cx0 * .031 + cy0 * .047)
            cv2.fillConvexPoly(cell, poly, float(.36 + .48 * local), cv2.LINE_AA)
            cv2.polylines(junction, [poly], True, float(.36 + .56 * (1.0 - local)), 1, cv2.LINE_AA)
            if (row + col) % 5 == 0:
                cv2.polylines(cuticle, [poly], True, float(.46 + .50 * local), 1, cv2.LINE_AA)

            # Paired irregular guanine slivers: a crystal doublet, never a dot.
            angle = float(18.0 + 42.0 * np.sin(cx0 * .019) - 28.0 * np.cos(cy0 * .023))
            theta = np.deg2rad(angle)
            dx, dy = np.cos(theta), np.sin(theta)
            nx, ny = -dy, dx
            length = int(rng.integers(5, 9))
            for side in (-1.0, 1.0):
                ox, oy = nx * side * 1.15, ny * side * 1.15
                p0 = (int(round(cx - dx * length * .5 + ox)), int(round(cy - dy * length * .5 + oy)))
                p1 = (int(round(cx + dx * length * .5 + ox)), int(round(cy + dy * length * .5 + oy)))
                cv2.line(plate, p0, p1, float(rng.uniform(.42, .98)), 2, cv2.LINE_AA)
            cv2.line(gap,
                     (int(round(cx - dx * length * .45)), int(round(cy - dy * length * .45))),
                     (int(round(cx + dx * length * .45)), int(round(cy + dy * length * .45))),
                     float(rng.uniform(.34, .94)), 1, cv2.LINE_AA)

            # Fluorescent spheres are attached chains on chosen reflectors.
            if idx % 11 == 0:
                for bead in (-2, 0, 2):
                    bx = int(round(cx + nx * bead + dx * 2.0))
                    by = int(round(cy + ny * bead + dy * 2.0))
                    cv2.circle(sphere, (bx, by), 2, float(rng.uniform(.48, .99)), -1, cv2.LINE_AA)
                    cv2.circle(core, (bx, by), 1, float(rng.uniform(.42, .95)), -1, cv2.LINE_AA)
            if idx % 17 == 0:
                # Short forked pyriform-style attachment root, cell bounded.
                anchor = (cx, cy)
                end = (int(round(cx - dx * 5)), int(round(cy - dy * 5)))
                cv2.line(root, anchor, end, float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
                cv2.line(root, end, (end[0] + int(round(nx * 3)), end[1] + int(round(ny * 3))),
                         float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
                cv2.line(root, end, (end[0] - int(round(nx * 3)), end[1] - int(round(ny * 3))),
                         float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
            idx += 1

    arrays = (cell, junction, plate, gap, sphere, core, root, cuticle)
    return tuple(cv2.GaussianBlur(a, (0, 0), .13).astype(np.float32) for a in arrays)


def _tier(channel_out, field, values, frequency, phase):
    sel = field > .075
    strength = np.clip(field, 0, 1)
    idx = np.floor(np.mod(strength * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel_out[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    cell, junction, plate, gap, sphere, core, root, cuticle = surface
    m = np.full((GEN, GEN), 24.0, np.float32)
    r = np.full((GEN, GEN), 226.0, np.float32)
    cc = np.full((GEN, GEN), 18.0, np.float32)
    _tier(m, plate, (132, 166, 198, 224, 244, 252), 5.7, .11)
    _tier(m, gap, (48, 82, 118, 158, 202), 4.9, .43)
    _tier(m, sphere, (102, 148, 190, 226, 250), 6.1, .69)
    _tier(r, cell, (72, 102, 136, 170, 204, 234), 4.3, .27)
    _tier(r, junction, (186, 208, 226, 242, 250), 5.3, .59)
    _tier(r, core, (18, 46, 82, 126, 178), 6.7, .19)
    _tier(cc, cuticle, (126, 160, 194, 222, 242, 252), 5.9, .31)
    _tier(cc, root, (72, 118, 166, 210, 244), 4.7, .73)
    _tier(cc, sphere, (142, 178, 212, 238, 252), 7.1, .21)
    return m, r, cc


def paint_jewel_spider(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 43017)
    cell, junction, plate, gap, sphere, core, root, cuticle = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.006, .009, .014], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(cell, (.012, .055, .052), (.06, .32, .25))
    assign(junction, (.006, .008, .018), (.045, .025, .08))
    assign(plate, (.20, .36, .40), (.82, 1.0, .92))
    assign(gap, (.018, .035, .06), (.12, .20, .26))
    assign(sphere, (.30, .006, .035), (1.0, .08, .22))
    assign(core, (.015, .002, .008), (.12, .012, .04))
    assign(root, (.16, .12, .24), (.72, .66, .98))
    assign(cuticle, (.06, .20, .24), (.22, .80, .84))

    m, r, cc = _material_states(surface)
    luma = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    colour = .79 * np.power(np.clip(luma, 0, 1), 1.52)[..., None] + chroma * 1.86
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_jewel_spider(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 43017))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
