"""Orb Weaver Silk I1 — paired capture fibres, glue droplets and anchors."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "orb_weaver_silk",
    "display_name": "Orb Weaver Silk",
    "promise": "A dense blue-silver capture-silk material where paired tension fibres carry humidity-responsive glue pearls, capillary spools and branching attachment discs.",
    "reference_physics": {
        "mechanism": (
            "Orb-weaver capture spirals use paired flagelliform axial fibres coated with evenly spaced viscoelastic glue droplets. "
            "Each droplet has an aqueous salt coat and glycoprotein core, can spool the axial thread by capillarity, and responds "
            "to humidity. Pyriform attachment discs tie draglines into thin plaques through branching nanofibre bridges."
        ),
        "sources": [
            "https://www.nature.com/articles/ncomms1019",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC4896710/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5332566/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6553539/",
        ],
    },
    "carrier_grammar": (
        "Closely spaced paired 8–32px capture-fibre segments flow continuously across the car and cross a second load-bearing "
        "family; bead-on-string aqueous droplets, internal glycoprotein cores, salt glints, capillary spools and compact branching "
        "pyriform anchor discs remain physically attached to those strands."
    ),
    "spec_grammar": (
        "Axial fibre, radial load fibre, aqueous glue shell, glycoprotein core, salt glint, capillary spool, pyriform plaque and "
        "branch bridge are independent named masks with channel-specific material ownership."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "paired_axial_fibre", "role": "forms the continuous compliant capture-silk field"},
        {"name": "radial_load_fibre", "role": "crosses capture silk and carries impact tension"},
        {"name": "aqueous_glue_shell", "role": "forms evenly spaced humidity-responsive beads"},
        {"name": "glycoprotein_core", "role": "provides viscoelastic adhesion within each bead"},
        {"name": "salt_glint", "role": "marks hygroscopic salts throughout selected droplets"},
        {"name": "capillary_spool", "role": "stores axial filament inside a glue droplet"},
        {"name": "pyriform_anchor_plaque", "role": "forms compact crossed attachment discs"},
        {"name": "branch_bridge", "role": "ties dragline crossings into the plaque"},
    ],
    "material_binding": {
        "M": ["paired_axial_fibre", "radial_load_fibre", "salt_glint"],
        "R": ["glycoprotein_core", "pyriform_anchor_plaque", "branch_bridge"],
        "Cc": ["aqueous_glue_shell", "capillary_spool", "salt_glint"],
    },
    "material_tiers": [
        "silver axial silk", "blue load fibre", "wet aqueous shell", "amber glycoprotein", "hygroscopic salt", "coiled spool",
        "graphite anchor plaque", "pearl bridge", "dew clearcoat",
    ],
    "nearest_neighbors": [
        {"finish_id": "jewel_spider", "difference": "continuous paired silk and bead-on-string glue replace packed guanocyte cells and intracellular platelets"},
        {"finish_id": "butterfly_glasswing", "difference": "tension fibres and adhesive droplets replace membrane panes and wing veins"},
        {"finish_id": "moth_owl", "difference": "smooth wet filament crossings replace broken bronze ocelli and absorptive pile"},
    ],
    "name_truth": {
        "visible_evidence": [
            "paired silver-blue capture fibres", "evenly spaced wet glue pearls", "amber adhesive cores", "compact branching anchor discs",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "orb-weaver-paired-capture-fibres-with-viscoelastic-beads-capillary-spools-and-pyriform-anchors",
    "spec_key": "orb-silk-axial-radial-shell-core-salt-spool-plaque-bridge-channel-binding",
}


GEN = 512


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
    rng = np.random.default_rng(int(seed) ^ 0x0B5E7)
    z = np.zeros((GEN, GEN), np.float32)
    axial, radial, shell, core = (z.copy() for _ in range(4))
    salt, spool, plaque, bridge = (z.copy() for _ in range(4))

    paths = []
    for row, y0 in enumerate(np.arange(-8.0, GEN + 9.0, 8.5)):
        phase = float(rng.uniform(0, np.pi * 2))
        phase2 = float(rng.uniform(0, np.pi * 2))
        pts = []
        for x in np.arange(-8.0, GEN + 9.0, 7.0):
            y = y0 + 3.4 * np.sin(x / 27.0 + phase) + 1.5 * np.sin(x / 8.3 + phase2)
            pts.append((int(round(x)), int(round(y))))
        arr = np.asarray(pts, np.int32)
        paths.append(arr)
        # Paired flagelliform fibres; both are visible, never a generic line.
        cv2.polylines(axial, [arr + np.array([0, -2], np.int32)], False, float(.38 + .56 * ((row * 3) % 11) / 10), 1, cv2.LINE_AA)
        cv2.polylines(axial, [arr + np.array([0, 2], np.int32)], False, float(.94 - .42 * ((row * 5) % 9) / 8), 1, cv2.LINE_AA)

        # Bead-on-string capture glue remains attached to the paired thread.
        for bead_i, pidx in enumerate(range(2 + row % 2, len(pts) - 2, 3)):
            bx, by = pts[pidx]
            rx = 3 + ((bead_i + row) % 2)
            cv2.ellipse(shell, (bx, by), (rx, 3), 0, 0, 360, float(rng.uniform(.42, .99)), -1, cv2.LINE_AA)
            cv2.ellipse(core, (bx, by), (max(1, rx - 1), 2), 0, 0, 360, float(rng.uniform(.38, .96)), -1, cv2.LINE_AA)
            if (bead_i + row) % 5 == 0:
                cv2.circle(salt, (bx + 1, by - 1), 1, float(rng.uniform(.48, .99)), -1, cv2.LINE_AA)
            if (bead_i + row) % 7 == 0:
                cv2.ellipse(spool, (bx, by), (rx, 3), 0, 200, 520, float(rng.uniform(.42, .98)), 1, cv2.LINE_AA)

    # A different, load-bearing silk family crosses the capture fibres.
    radial_paths = []
    for col, y0 in enumerate(np.arange(-GEN * .55, GEN + GEN * .15, 14.5)):
        phase = float(rng.uniform(0, np.pi * 2))
        pts = []
        for x in np.arange(-8.0, GEN + 9.0, 8.0):
            y = y0 + .55 * x + 4.2 * np.sin(x / 33.0 + phase)
            pts.append((int(round(x)), int(round(y))))
        arr = np.asarray(pts, np.int32)
        radial_paths.append(arr)
        cv2.polylines(radial, [arr], False, float(.40 + .54 * ((col * 7) % 13) / 12), 1, cv2.LINE_AA)

    # Compact attachment discs: crossed plaque loops with branching bridges.
    for idx in range(0, min(len(paths), len(radial_paths)), 3):
        p = paths[idx][min(len(paths[idx]) - 1, 5 + (idx * 3) % max(6, len(paths[idx]) - 7))]
        cx, cy = int(p[0]), int(p[1])
        angle = float((idx * 29) % 180)
        cv2.ellipse(plaque, (cx, cy), (5, 3), angle, 0, 360, float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
        cv2.ellipse(plaque, (cx, cy), (3, 5), angle, 0, 360, float(rng.uniform(.38, .96)), 1, cv2.LINE_AA)
        for branch_i in (-1, 0, 1):
            theta = np.deg2rad(angle + 90 + branch_i * 34)
            ex = cx + int(round(np.cos(theta) * 7))
            ey = cy + int(round(np.sin(theta) * 7))
            cv2.line(bridge, (cx, cy), (ex, ey), float(rng.uniform(.42, .98)), 1, cv2.LINE_AA)

    arrays = (axial, radial, shell, core, salt, spool, plaque, bridge)
    return tuple(cv2.GaussianBlur(a, (0, 0), .14).astype(np.float32) for a in arrays)


def _tier(channel_out, field, values, frequency, phase):
    sel = field > .075
    strength = np.clip(field, 0, 1)
    idx = np.floor(np.mod(strength * frequency + phase, 1.0) * len(values)).astype(np.int16)
    palette = np.asarray(values, np.float32)
    channel_out[sel] = palette[np.clip(idx[sel], 0, len(values) - 1)]


def _material_states(surface):
    axial, radial, shell, core, salt, spool, plaque, bridge = surface
    m = np.full((GEN, GEN), 22.0, np.float32)
    r = np.full((GEN, GEN), 232.0, np.float32)
    cc = np.full((GEN, GEN), 14.0, np.float32)
    _tier(m, axial, (118, 152, 184, 214, 238, 252), 5.9, .13)
    _tier(m, radial, (72, 112, 158, 202, 242), 4.7, .41)
    _tier(m, salt, (174, 204, 228, 246, 252), 6.3, .67)
    _tier(r, core, (32, 66, 104, 148, 194, 232), 5.1, .29)
    _tier(r, plaque, (112, 146, 180, 214, 242), 6.7, .57)
    _tier(r, bridge, (170, 198, 220, 238, 250), 4.3, .19)
    _tier(cc, shell, (126, 158, 190, 218, 240, 252), 5.7, .37)
    _tier(cc, spool, (88, 132, 176, 216, 246), 6.9, .73)
    _tier(cc, salt, (164, 196, 224, 244, 252), 4.9, .23)
    return m, r, cc


def paint_orb_weaver_silk(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 44017)
    axial, radial, shell, core, salt, spool, plaque, bridge = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.008, .012, .025], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(axial, (.16, .24, .38), (.78, .90, 1.0))
    assign(radial, (.04, .12, .30), (.20, .54, .95))
    assign(shell, (.08, .24, .38), (.34, .86, 1.0))
    assign(core, (.20, .08, .018), (.92, .48, .06))
    assign(salt, (.48, .60, .72), (1.0, 1.0, .92))
    assign(spool, (.08, .18, .34), (.42, .72, 1.0))
    assign(plaque, (.018, .024, .042), (.15, .20, .34))
    assign(bridge, (.18, .16, .30), (.74, .66, .98))

    m, r, cc = _material_states(surface)
    luma = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    # P3: the live paint must carry the same tension/glue hierarchy as spec.
    # Expand material luminance around mid-grey so paired fibres, wet shells
    # and adhesive cores remain legible on a whole-car 2048 canvas.
    optical = np.clip((luma - .50) * 1.72 + .50, 0, 1)
    colour = .90 * np.power(optical, 1.32)[..., None] + chroma * 1.78
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_orb_weaver_silk(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 44017))
    return (
        np.clip(_resize(m * sm, shape), 8, 252),
        np.clip(_resize(r * sm, shape), 12, 250),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
