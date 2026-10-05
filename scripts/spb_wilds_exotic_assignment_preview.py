#!/usr/bin/env python3
"""Palette-free preview of candidate exotic-math assignments for Wilds WR-2."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ASSIGNMENTS = {
    "fbl_magenta_whorl": ("bz_spirals", 4),
    "fbl_leafvine_drape": ("thorn_bramble", 3),
    "fbl_butter_pollen": ("ford_circles", 5),
    "fbl_pink_rose": ("rhodonea_field", 4),
    "fbl_coral_cluster": ("dla_aggregate", 3),
    "fbl_butter_mosaic": ("hat_monotile", 3),
    "fbl_pink_pollen": ("potential_flow_cylinders", 5),
    "fbl_white_whorl": ("rose_window", 12),
    "fbl_coral_stamen": ("cardioid_caustic", 10),
    "fbl_lilac_rose": ("dark_damask", 5),
    "fbl_coral_vine": ("gosper_flowsnake", 4),
    "fbl_lilac_stamen": ("reactor_lattice", 4),
    "fbl_magenta_mosaic": ("spectre_monotile", 3),
    "fbl_leaf_whorl": ("clelie_spiral", 12),
    "fbl_white_pollen": ("ferrofluid_spikes", 3),
    "fbl_pink_stamen": ("fourier_epicycle", 12),
    "fbl_blush_rose": ("quatrefoil_tess", 4),
    "fbl_lilac_vine": ("epitrochoid_weave", 6),
    "fbl_butter_whorl": ("spirograph_lattice", 5),
    "fbl_magenta_pollen": ("wallpaper_p6m", 3),
    "fpe_magenta_bloom": ("hodgepodge", 2),
    "fpe_cyan_membrane": ("gray_scott_uskate", 2),
    "fpe_lime_culture": ("eden_growth", 3),
    "fpe_amber_agar": ("crack_network", 2),
    "fpe_violet_garden": ("pythagoras_tree", 5),
    "fpe_lime_diatom": ("diffraction_grating", 2),
    "fpe_magenta_mosaic": ("ammann_beenker", 3),
    "fpe_cyan_spineball": ("hyperbolic_pqr", 8),
    "fpe_amber_moldring": ("liesegang_rings", 6),
    "fpe_violet_chains": ("neural_ca_worms", 2),
    "fpe_cyan_colony": ("lenia", 2),
    "fpe_lime_mold": ("rust_bloom", 3),
    "fpe_amber_diatom": ("scratch_striation", 2),
    "fpe_magenta_radiolaria": ("superformula_field", 5),
    "fpe_cyan_mold": ("tracery_web", 3),
    "fpe_amber_plankton": ("curl_streaklines", 3),
    "fpe_violet_membrane": ("bubble_lattice", 3),
    "fpe_lime_chains": ("steiner_chain", 6),
    "fpe_violet_frustule": ("maurer_rose", 6),
    "fpe_magenta_plankton": ("curl_smoke", 3),
}


def repeat_field(src, out_size, repeats, angle):
    src = np.asarray(src, np.float32) / 255.0
    h, w = src.shape
    yy, xx = np.mgrid[0:out_size, 0:out_size].astype(np.float32)
    cx = xx - out_size * 0.5
    cy = yy - out_size * 0.5
    ca, sa = np.cos(angle), np.sin(angle)
    u = (cx * ca + cy * sa) * (w * repeats / out_size) + w * 0.5
    v = (-cx * sa + cy * ca) * (h * repeats / out_size) + h * 0.5
    return cv2.remap(src, u.astype(np.float32), v.astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "_wilds_rejection_work" / "exotic_inventory" / "fields"
    output = root / "_wilds_rejection_work" / "exotic_assignments"
    output.mkdir(parents=True, exist_ok=True)
    cell, label_h, cols = 256, 32, 5
    rows = (len(ASSIGNMENTS) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), (7, 7, 9))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (fid, (engine, repeats)) in enumerate(ASSIGNMENTS.items()):
        raw = cv2.imread(str(source / f"{engine}.png"), cv2.IMREAD_GRAYSCALE)
        if raw is None:
            raise FileNotFoundError(engine)
        f = repeat_field(raw, cell, repeats, (i % 7 - 3) * 0.037)
        # Same fixed hue for every card. No palette can produce separation.
        rgb = np.stack((f * 0.18, f * 0.76, f), axis=2)
        rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        x, y = (i % cols) * cell, (i // cols) * (cell + label_h)
        sheet.paste(Image.fromarray(rgb, "RGB"), (x, y))
        draw.text((x + 4, y + cell + 3), f"{fid} | {engine} x{repeats}", fill=(235, 235, 235), font=font)
    sheet.save(output / "assignment_hue_null_contact.png")
    print(output / "assignment_hue_null_contact.png")


if __name__ == "__main__":
    main()
