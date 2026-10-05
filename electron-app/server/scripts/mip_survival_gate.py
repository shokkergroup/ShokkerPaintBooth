# -*- coding: utf-8 -*-
"""MIP-SURVIVAL GATE (owner mandate 2026-06-09): does a finish's detail survive
being viewed at track distance, or does it turn to gray mush?

Finishes are judged in the booth at 2048 px but the sim shows them mip-mapped
far smaller most of the race. This gate downsamples each swatch 4x (mip-style),
measures how much contrast + high-frequency structure survives, and flags
finishes below threshold. Metric: engine.color_science.mip_survival.

Usage:
  py -3 scripts/mip_survival_gate.py thumbnails/audit/letfreedomring
  py -3 scripts/mip_survival_gate.py <folder> --split half   # 2-up audit swatches: judge LEFT (paint) half
  py -3 scripts/mip_survival_gate.py <folder> --threshold 0.25

Exit code 1 if any file fails the gate (CI-friendly).
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from engine.color_science import mip_survival

ap = argparse.ArgumentParser()
ap.add_argument("folder", help="folder of swatch PNGs/JPGs to gate")
ap.add_argument("--threshold", type=float, default=0.25, help="fail below this retention (default 0.25)")
ap.add_argument("--warn", type=float, default=0.45, help="warn below this retention (default 0.45)")
ap.add_argument("--factor", type=int, default=4, help="mip downsample factor (default 4 = quarter res)")
ap.add_argument("--split", choices=["whole", "half"], default="whole",
                help="'half' judges only the LEFT half (for the 2-up audit swatches: paint|spec)")
args = ap.parse_args()

files = sorted(f for f in os.listdir(args.folder) if f.lower().endswith((".png", ".jpg", ".jpeg")))
if not files:
    print("no images in", args.folder); sys.exit(2)

rows, fails, warns = [], 0, 0
for f in files:
    img = cv2.imread(os.path.join(args.folder, f), cv2.IMREAD_COLOR)
    if img is None:
        continue
    if args.split == "half":
        img = img[:, : img.shape[1] // 2]
    score = mip_survival(img.astype(np.float32) / 255.0, factor=args.factor)
    status = "FAIL" if score < args.threshold else ("warn" if score < args.warn else "ok")
    fails += status == "FAIL"; warns += status == "warn"
    rows.append((score, status, f))

for score, status, f in sorted(rows):
    print("%5.2f  %-4s  %s" % (score, status, f))
print()
print("gate @ %.2f: %d FAIL, %d warn, %d ok / %d total (1/%dx view)"
      % (args.threshold, fails, warns, len(rows) - fails - warns, len(rows), args.factor))
sys.exit(1 if fails else 0)
