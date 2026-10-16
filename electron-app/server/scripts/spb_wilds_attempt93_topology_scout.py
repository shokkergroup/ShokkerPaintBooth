# -*- coding: utf-8 -*-
"""Paint-only topology silhouettes for Wilds attempt 93 selection.

This scout never installs renderers or establishes acceptance. It intentionally
omits spec maps and most fine anatomy so a bad dominant carrier cannot hide
behind detail. Three full-frame hierarchies are compared at 512 before one is
authorized for native-2048 construction.
"""
from pathlib import Path

import cv2
import numpy as np


SIZE = 512
OUT = Path("_wilds_fullres_progress_20260824/attempt93_topology_scout")
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = np.asarray([
    (5, 7, 18), (15, 17, 43), (31, 25, 70), (56, 31, 94), (86, 38, 111),
    (119, 46, 119), (153, 57, 117), (184, 73, 108), (209, 94, 94),
    (227, 120, 82), (238, 150, 80), (239, 181, 92), (229, 209, 119),
    (207, 229, 155), (177, 240, 199),
], np.uint8)


def atlas_mimic():
    image = np.full((SIZE, SIZE, 3), (3, 5, 12), np.uint8)
    # Seven open, independently shifted mimic boundaries. They share a head-like
    # chronology but never form a concentric eye or repeat a stamp.
    for layer in range(11, -1, -1):
        t = np.linspace(-1.2, 1.18, 420)
        scale = 1.0 - layer * .055
        x = 246 + scale * (235 * np.cos(t) + 64 * np.cos(2.3 * t + .7)) + layer * 5
        y = 279 + scale * (190 * np.sin(t) - 83 * np.sin(2.1 * t - .4)) - layer * 6
        pts = np.rint(np.stack((x, y), axis=1)).astype(np.int32)
        cv2.polylines(image, [pts], False, tuple(int(v) for v in PALETTE[(layer * 4 + 2) % 15]), 13 - layer // 3, cv2.LINE_AA)
    # Three unequal jaw seams and notched outer cheek, still silhouette-only.
    cv2.polylines(image, [np.asarray(((12, 367), (116, 329), (236, 347), (352, 312), (511, 331)), np.int32)],
                  False, tuple(int(v) for v in PALETTE[12]), 9, cv2.LINE_AA)
    cv2.polylines(image, [np.asarray(((41, 118), (143, 154), (231, 131), (327, 169), (482, 126)), np.int32)],
                  False, tuple(int(v) for v in PALETTE[7]), 7, cv2.LINE_AA)
    return image


def calyx_ratchet():
    image = np.full((SIZE, SIZE, 3), (4, 5, 10), np.uint8)
    centre = np.asarray((283.0, 241.0))
    # Seven unequal catch arms with different reach and curvature. The crop cuts
    # arms off-canvas so the read is interlocking mechanism, not a flower stamp.
    for arm in range(7):
        theta = arm * 2 * np.pi / 7 + .18 * np.sin(arm * 1.7)
        length = 250 + (arm * 37) % 111
        width = 36 + (arm * 19) % 31
        pts = []
        for q in np.linspace(0, 1, 90):
            angle = theta + .92 * q + .16 * np.sin(q * np.pi * 3 + arm)
            radius = 26 + length * q
            c = centre + np.asarray((np.cos(angle), np.sin(angle))) * radius
            normal = np.asarray((-np.sin(angle), np.cos(angle)))
            half = width * (1 - .64 * q) * np.sin(np.pi * min(1, q * 1.5))
            pts.append((c - normal * half, c + normal * half))
        poly = np.asarray([a for a, _ in pts] + [b for _, b in pts[::-1]], np.int32)
        cv2.fillPoly(image, [poly], tuple(int(v) for v in PALETTE[(arm * 2 + 4) % 15]), cv2.LINE_AA)
        cv2.polylines(image, [poly], True, tuple(int(v) for v in PALETTE[(arm * 3 + 11) % 15]), 5, cv2.LINE_AA)
        ridge = np.asarray([np.rint((a + b) * .5).astype(np.int32) for a, b in pts])
        cv2.polylines(image, [ridge], False, tuple(int(v) for v in PALETTE[(arm * 5 + 13) % 15]), 5, cv2.LINE_AA)
    cv2.ellipse(image, tuple(centre.astype(int)), (31, 24), -18, 0, 360, tuple(int(v) for v in PALETTE[2]), 8, cv2.LINE_AA)
    return image


def lantern_shell():
    image = np.full((SIZE, SIZE, 3), (3, 5, 8), np.uint8)
    # One articulated shell close-crop: nested chitin lips overlap rather than
    # repeating a segment stamp or circuit grid.
    plates = (
        ((-65, 80), (260, 12), (392, 119), (310, 258), (-28, 281)),
        ((39, 236), (309, 178), (529, 252), (471, 394), (128, 421)),
        ((-41, 390), (213, 339), (444, 419), (392, 548), (-39, 557)),
    )
    for j, control in enumerate(plates):
        poly = np.asarray(control, np.int32)
        cv2.fillPoly(image, [poly], tuple(int(v) for v in PALETTE[(j * 4 + 5) % 15]), cv2.LINE_AA)
        cv2.polylines(image, [poly], True, tuple(int(v) for v in PALETTE[(j * 5 + 13) % 15]), 9 - j, cv2.LINE_AA)
    # Unequal luminous windows with shared oblique articulation, not a grid.
    for j, (c, axes, angle) in enumerate((((86, 145), (58, 31), -18), ((225, 113), (73, 37), 9),
                                          ((355, 164), (47, 29), 31), ((154, 300), (84, 36), -7),
                                          ((337, 316), (68, 32), 18), ((96, 463), (51, 27), -22),
                                          ((275, 448), (91, 34), 6), ((443, 470), (55, 24), 29))):
        cv2.ellipse(image, c, axes, angle, 0, 360, tuple(int(v) for v in PALETTE[(j * 2 + 9) % 15]), -1, cv2.LINE_AA)
        cv2.ellipse(image, c, axes, angle, 0, 360, tuple(int(v) for v in PALETTE[(j * 3 + 1) % 15]), 6, cv2.LINE_AA)
    return image


def label(image, text):
    result = image.copy()
    cv2.rectangle(result, (0, 0), (511, 35), (0, 0, 0), -1)
    cv2.putText(result, text, (11, 24), cv2.FONT_HERSHEY_SIMPLEX, .58, (245, 245, 245), 1, cv2.LINE_AA)
    return result


items = (("Atlas mimic boundary", atlas_mimic()),
         ("Calyx ratchet", calyx_ratchet()),
         ("Articulated lantern", lantern_shell()))
for name, image in items:
    cv2.imwrite(str(OUT / (name.lower().replace(" ", "_") + ".png")), image)
board = cv2.hconcat([label(image, name) for name, image in items])
cv2.imwrite(str(OUT / "ATTEMPT93_TOPOLOGY_SCOUT.png"), board)
print(OUT / "ATTEMPT93_TOPOLOGY_SCOUT.png")
