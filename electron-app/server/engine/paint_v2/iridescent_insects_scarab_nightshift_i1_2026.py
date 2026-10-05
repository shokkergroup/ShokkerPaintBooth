"""Scarab Nightshift I1 — absorptive pillar armour with chiral crescents."""

from functools import lru_cache

import cv2
import numpy as np


IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "scarab_night",
    "display_name": "Scarab Nightshift",
    "promise": "Near-black scarab armour swallows ordinary light while crescent helicoids, wet channels and pillar crowns flash midnight colour.",
    "reference_physics": {
        "mechanism": (
            "Some black scarab elytra use ellipsoidal micropillars over melanin to enhance absorption toward 99.5%. "
            "Scarab helicoidal exocuticle produces circularly polarized reflection, while pores, pits and vertical channels "
            "can transport moisture into multilayer structural units and reversibly darken the shell."
        ),
        "sources": [
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC11835496/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC7803976/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC5493795/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6283984/",
        ],
    },
    "carrier_grammar": (
        "Alternating 10–30px lenticular elytral tiles form a complete midnight shell; every tile carries a crescent "
        "helicoid seam, ellipsoidal absorber pillars, moisture pit/channel, cross-ply fibre window and polished crown."
    ),
    "spec_grammar": (
        "Absorptive tile, crescent helicoid, pillar body, pillar crown, moisture pit, vertical channel, cross-ply window "
        "and wet edge are exact named masks with independent M/R/Cc tier families."
    ),
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "lenticular_tile", "role": "forms the continuous midnight elytral shell"},
        {"name": "crescent_helicoid", "role": "provides chiral blue-violet seam relief"},
        {"name": "absorber_pillar", "role": "traps light above melanin-rich cuticle"},
        {"name": "pillar_crown", "role": "catches sparse mercury-blue glints"},
        {"name": "moisture_pit", "role": "collects water at the epicuticle surface"},
        {"name": "vertical_channel", "role": "moves water through the multilayer unit"},
        {"name": "cross_ply_window", "role": "reveals longitudinal/transverse protein fibres"},
        {"name": "wet_tile_edge", "role": "marks locally flooded clear shell rims"},
    ],
    "material_binding": {
        "M": ["crescent_helicoid", "pillar_crown", "cross_ply_window"],
        "R": ["lenticular_tile", "absorber_pillar", "moisture_pit"],
        "Cc": ["pillar_crown", "vertical_channel", "wet_tile_edge"],
    },
    "material_tiers": [
        "ultrablack melanin", "midnight indigo shell", "violet chiral crescent", "absorber velvet",
        "mercury pillar crown", "wet pore", "cyan water channel", "cross-ply satin", "flooded clear rim",
    ],
    "nearest_neighbors": [
        {"finish_id": "scarab_sunplate", "difference": "dark lenticular absorber tiles replace interlocking gold radial sunplates"},
        {"finish_id": "cockroach_onyx", "difference": "diagonal chiral crescents and micropillars replace horizontal tergite shingles and gland anatomy"},
        {"finish_id": "beetle_ground", "difference": "moisture-responsive pillar tiles replace continuous carabid obsidian armour"},
    ],
    "name_truth": {
        "visible_evidence": [
            "near-black diagonal lenticular armour",
            "blue-violet crescent helicoid seams",
            "mercury pillar crowns and wet cyan channels",
        ],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "scarab-night-lenticular-absorber-tiles-with-chiral-crescents-pillars-and-moisture-channels",
    "spec_key": "night-scarab-tile-crescent-pillar-crown-pit-channel-crossply-wetedge-binding",
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
    rng = np.random.default_rng(int(seed) ^ 0xA16A7)
    z = np.zeros((GEN, GEN), np.float32)
    tile, crescent, pillar, crown = (z.copy() for _ in range(4))
    pit, channel, crossply, wet = (z.copy() for _ in range(4))

    # P5: an ordered flowing elytral field, not a stochastic pebble/noise mat.
    # Each lens remains <=32 px at the final 2048 canvas while coherent local
    # orientation changes make the armour read across the whole car.
    sx, sy = 10.4, 8.8
    idx = 0
    for row, cy0 in enumerate(np.arange(-6.0, GEN + 7.0, sy)):
        offset = 0.0 if row % 2 == 0 else sx * .5
        for cx0 in np.arange(-6.0 + offset, GEN + 7.0, sx):
            cx = int(round(cx0 + rng.uniform(-.35, .35)))
            cy = int(round(cy0 + rng.uniform(-.35, .35)))
            angle = float(24.0 + 17.0 * np.sin(cx0 * .024) + 11.0 * np.cos(cy0 * .031)
                          + (4.0 if row % 2 else -4.0))
            ax, ay = 5, 3
            local = .5 + .5 * np.sin(cx0 * .043 + cy0 * .027)
            cv2.ellipse(tile, (cx, cy), (ax, ay), angle, 0, 360, float(.38 + .40 * local), -1, cv2.LINE_AA)
            cv2.ellipse(crescent, (cx, cy), (ax, ay), angle, 205, 344,
                        float(.52 + .44 * (1.0 - local)), 1, cv2.LINE_AA)
            if idx % 7 == 0:
                cv2.ellipse(wet, (cx, cy), (ax, ay), angle, 18, 122,
                            float(.48 + .46 * local), 1, cv2.LINE_AA)

            # Ellipsoidal pillars stay inside their biological tile.
            for k in ((-1, 1) if idx % 3 == 0 else (0,)):
                theta = np.deg2rad(angle)
                px = cx + int(round(np.cos(theta) * k * 2))
                py = cy + int(round(np.sin(theta) * k * 2))
                cv2.ellipse(pillar, (px, py), (1, 2), angle, 0, 360, float(rng.uniform(.28, .95)), -1, cv2.LINE_AA)
                if idx % 5 == 0:
                    cv2.circle(crown, (px, py), 1, float(rng.uniform(.34, .99)), -1, cv2.LINE_AA)

            if idx % 6 == 0:
                cv2.circle(pit, (cx, cy), 1, float(rng.uniform(.35, .98)), -1, cv2.LINE_AA)
                theta = np.deg2rad(angle + 72)
                cv2.line(channel, (cx, cy),
                         (cx + int(round(np.cos(theta) * 6)), cy + int(round(np.sin(theta) * 6))),
                         float(rng.uniform(.30, .98)), 1, cv2.LINE_AA)
            if idx % 13 == 0:
                cv2.line(crossply, (cx - 3, cy), (cx + 3, cy), float(rng.uniform(.28, .9)), 1, cv2.LINE_AA)
                cv2.line(crossply, (cx, cy - 2), (cx, cy + 2), float(rng.uniform(.28, .9)), 1, cv2.LINE_AA)
            idx += 1

    arrays = (tile, crescent, pillar, crown, pit, channel, crossply, wet)
    return tuple(cv2.GaussianBlur(a, (0, 0), .13).astype(np.float32) for a in arrays)


def _material_states(surface):
    tile, crescent, pillar, crown, pit, channel, crossply, wet = surface
    m = np.full((GEN, GEN), 18.0, np.float32)
    r = np.full((GEN, GEN), 238.0, np.float32)
    cc = np.full((GEN, GEN), 12.0, np.float32)

    def assign(channel_out, field, values, frequency, phase):
        sel = field > .075
        strength = np.clip(field, 0, 1)
        # Quantised optical tiers give every biological feature several
        # distinct states without turning the three channels into recolours.
        tier = np.floor(np.mod(strength * frequency + phase, 1.0) * len(values)).astype(np.int16)
        palette = np.asarray(values, np.float32)
        channel_out[sel] = palette[np.clip(tier[sel], 0, len(values) - 1)]

    # P4: channel ownership follows the biological identity contract.
    # Metallic reads chiral helicoids and reflective fibre/crown anatomy.
    assign(m, crescent, (126, 154, 184, 210, 232, 250), 5.7, .13)
    assign(m, crossply, (72, 116, 166, 206, 242), 4.9, .41)
    assign(m, crown, (148, 184, 218, 244, 252), 6.3, .67)
    # Roughness reads the absorbing substrate, pillars, and moisture pits.
    assign(r, tile, (102, 128, 154, 182, 208, 232), 4.3, .29)
    assign(r, pillar, (190, 206, 222, 238, 248), 5.1, .58)
    assign(r, pit, (42, 76, 112, 164, 218), 6.7, .17)
    # Clearcoat reads water transport and flooded tile edges.
    assign(cc, channel, (118, 154, 190, 220, 242, 252), 5.9, .37)
    assign(cc, wet, (96, 138, 180, 214, 240, 250), 4.7, .71)
    assign(cc, crown, (142, 178, 212, 238, 250), 7.1, .23)
    return m, r, cc


def paint_scarab_night(paint, shape, mask, seed, pm, _base):
    surface = _surface(seed + 42017)
    tile, crescent, pillar, crown, pit, channel, crossply, wet = surface
    colour = np.zeros((GEN, GEN, 3), np.float32)
    colour[:] = np.array([.003, .004, .010], np.float32)

    def assign(field, dark, bright):
        sel = field > .075
        strength = np.clip(field, 0, 1)[..., None]
        mapped = np.asarray(dark, np.float32) + (np.asarray(bright, np.float32) - np.asarray(dark, np.float32)) * strength
        colour[sel] = mapped[sel]

    assign(tile, (.020, .034, .105), (.105, .155, .36))
    assign(pillar, (.001, .001, .004), (.012, .016, .035))
    assign(crescent, (.025, .055, .20), (.22, .12, .70))
    assign(pit, (.002, .004, .01), (.03, .02, .07))
    assign(channel, (.015, .12, .22), (.06, .70, .92))
    assign(crossply, (.06, .09, .24), (.22, .45, .82))
    assign(wet, (.10, .12, .34), (.38, .24, .88))
    assign(crown, (.16, .25, .42), (.74, .92, 1.0))

    m, r, cc = _material_states(surface)
    luma = (.2126 * m + .7152 * r + .0722 * cc) / 255.0
    # P6: spec luminance is the optical skeleton, while amplified source
    # chroma keeps that skeleton midnight indigo/violet instead of grey.
    source_luma = colour[..., 0] * .2126 + colour[..., 1] * .7152 + colour[..., 2] * .0722
    chroma = colour - source_luma[..., None]
    colour = .86 * np.power(np.clip(luma, 0, 1), 1.72)[..., None] + chroma * 1.72
    return _blend(paint, mask, pm, _resize(np.clip(colour, 0, 1), shape))


def spec_scarab_night(shape, seed, sm, _base_m, _base_r):
    m, r, cc = _material_states(_surface(seed + 42017))
    return (
        np.clip(_resize(m * sm, shape), 8, 248),
        np.clip(_resize(r * sm, shape), 12, 246),
        np.clip(_resize(cc * sm, shape), 8, 252),
    )
