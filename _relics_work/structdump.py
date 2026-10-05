# -*- coding: utf-8 -*-
"""Dump the RAW structural T field of every engine (pre-LUT, pre-colour) at the
same pixel scale the car sees, so geometry can be judged without colour in the
way. Left half = field at GEN; right = a 512 crop at true 2048 scale."""
import importlib, os, sys
import numpy as np, cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
import engine.expansions.fractured_relics_kit_2026 as rkit
import engine.expansions.fractured_relics_2026 as m
importlib.reload(rkit); importlib.reload(m)

OUT = "_relics_work"
only = set(sys.argv[1:])
cells = []
for gname, grp in m.GROUPS.items():
    for fid, d in grp.items():
        if only and fid not in only:
            continue
        T = m.ENGINES[d["engine"]](640, int(d["seed"]), **d.get("eargs", {}))
        T = np.asarray(T, np.float32)
        g8 = (np.clip(T, 0, 1) * 255).astype(np.uint8)
        full = cv2.resize(g8, (512, 512), interpolation=cv2.INTER_AREA)
        # true on-car scale: GEN 640 -> 2048 is x3.2; crop 160px of GEN and blow up
        c = g8[240:400, 240:400]
        crop = cv2.resize(c, (512, 512), interpolation=cv2.INTER_NEAREST)
        cells.append((fid, full, crop))
        print(f"{fid:24s} T range {T.min():.2f}-{T.max():.2f} std {T.std():.3f}", flush=True)

cols = 4
cell_w, cell_h = 512 * 2 + 10, 512 + 24
rws = (len(cells) + cols - 1) // cols
sheet = np.full((rws * cell_h, cols * cell_w), 12, np.uint8)
for i, (fid, a, b) in enumerate(cells):
    cy, cx = divmod(i, cols)
    y0, x0 = cy * cell_h + 22, cx * cell_w
    sheet[y0:y0 + 512, x0:x0 + 512] = a
    sheet[y0:y0 + 512, x0 + 520:x0 + 1032] = b
    cv2.putText(sheet, fid, (x0 + 6, cy * cell_h + 16), cv2.FONT_HERSHEY_SIMPLEX, .5, 240, 1)
cv2.imwrite(f"{OUT}/struct_sheet.png", sheet)
print(f"struct sheet: {OUT}/struct_sheet.png  [field | 3.2x on-car crop]")
