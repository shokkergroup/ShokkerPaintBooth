"""Audit and gently repair static Wilds plates that visibly break at tile edges.

Usage:
  python scripts/spb_wilds_asset_seam_audit.py butter_pollen_i3 lime_mold_i2
  python scripts/spb_wilds_asset_seam_audit.py butter_pollen_i3 --repair

Repair only blends a 48px edge band into its corresponding opposite edge.  It
does not add procedural noise or touch the interior design; pixel 0 and pixel
-1 become identical, so wrapping cannot create a hard canvas border.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def _path(name: str) -> Path:
    return ROOT / "assets" / "generated" / "wilds" / f"{name}.png"

def _metrics(img: np.ndarray) -> tuple[float, float, float]:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lr = float(np.abs(lab[:, 0] - lab[:, -1]).mean())
    tb = float(np.abs(lab[0] - lab[-1]).mean())
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    high_frequency = float(np.abs(gray-cv2.GaussianBlur(gray,(0,0),1.2)).mean())
    return lr, tb, high_frequency

def _feather_wrap(img: np.ndarray, band: int) -> np.ndarray:
    """Match opposite edges with a cosine feather; preserve every interior pixel."""
    out = img.astype(np.float32).copy(); h, w = out.shape[:2]
    if not 2 <= band < min(h, w)//2: raise ValueError(f"invalid band {band} for {w}x{h}")
    for i in range(band):
        amount = .5 * (1 + np.cos(np.pi*i/band))
        pair = (out[:, i] + out[:, -1-i])*.5
        out[:, i] = out[:, i]*(1-amount) + pair*amount
        out[:, -1-i] = out[:, -1-i]*(1-amount) + pair*amount
    for i in range(band):
        amount = .5 * (1 + np.cos(np.pi*i/band))
        pair = (out[i] + out[-1-i])*.5
        out[i] = out[i]*(1-amount) + pair*amount
        out[-1-i] = out[-1-i]*(1-amount) + pair*amount
    return np.uint8(np.clip(np.rint(out), 0, 255))

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("names", nargs="+"); ap.add_argument("--repair", action="store_true"); ap.add_argument("--band", type=int, default=48)
    args = ap.parse_args()
    for name in args.names:
        path = _path(name); img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None: print(f"MISSING {name}: {path}"); continue
        before = _metrics(img)
        if args.repair:
            img = _feather_wrap(img, args.band)
            if not cv2.imwrite(str(path), img): raise OSError(f"could not write {path}")
        after = _metrics(img)
        state = "repaired" if args.repair else "audited"
        print(f"{name} {state}  LR {before[0]:.2f}->{after[0]:.2f}  TB {before[1]:.2f}->{after[1]:.2f}  HF {before[2]:.2f}->{after[2]:.2f}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
