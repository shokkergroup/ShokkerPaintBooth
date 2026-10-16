"""Bounded X LAB contact and tile-scale diagnostic (SPB-105 / X-LAB-1)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from engine.expansions.x_lab_2026 import RECIPES, arrays  # noqa: E402


def _structure(image: np.ndarray, side: int = 64) -> np.ndarray:
    lum = cv2.resize(np.mean(image, axis=2).astype(np.float32), (side, side), interpolation=cv2.INTER_AREA)
    lum -= float(lum.mean())
    return (lum / max(float(np.linalg.norm(lum)), 1e-7)).ravel()


def _tile_read(image: np.ndarray, side: int) -> dict[str, float]:
    thumb = cv2.resize(np.asarray(image, np.float32), (side, side), interpolation=cv2.INTER_AREA)
    lum = np.mean(thumb, axis=2)
    sat = np.max(thumb, axis=2) - np.min(thumb, axis=2)
    gy, gx = np.gradient(lum)
    edge = np.sqrt(gx * gx + gy * gy)
    return {
        "luma_std": round(float(lum.std()), 4),
        "edge_energy": round(float(edge.mean()), 5),
        "lit_chroma_fraction": round(float(np.mean((sat > .20) & (lum > .10))), 4),
    }


def main() -> int:
    out = ROOT / "_x_lab_work" / "first_contact"
    out.mkdir(parents=True, exist_ok=True)
    tiles=[]; metrics={}; structures={}
    for recipe in RECIPES:
        paint,spec=arrays(recipe.fid)
        image=np.clip(paint*255,0,255).astype(np.uint8)
        tile=cv2.resize(image,(192,192),interpolation=cv2.INTER_AREA)
        card=np.zeros((218,192,3),np.uint8); card[:192]=tile
        cv2.putText(card,recipe.name,(7,210),cv2.FONT_HERSHEY_SIMPLEX,.43,(235,235,235),1,cv2.LINE_AA)
        tiles.append(card)
        lum=paint.mean(axis=2); small=cv2.resize(lum,(64,64),interpolation=cv2.INTER_AREA)
        gy,gx=np.gradient(small)
        metrics[recipe.fid]={
            "name":recipe.name,
            "paintStd":round(float(paint.std()),4),
            "tileEdge":round(float(np.mean(np.sqrt(gx*gx+gy*gy))),4),
            "tileRead":{"128":_tile_read(paint,128),"64":_tile_read(paint,64)},
            "specStd":[round(float(spec[...,i].std()),2) for i in range(3)],
            "specRange":[[int(spec[...,i].min()),int(spec[...,i].max())] for i in range(3)],
        }
        structures[recipe.fid]=_structure(paint)
    rows=[]
    for start in range(0,len(tiles),5):
        row=tiles[start:start+5]+[np.zeros_like(tiles[0])]*(5-len(tiles[start:start+5]))
        rows.append(np.concatenate(row,axis=1))
    contact=np.concatenate(rows,axis=0)
    cv2.imwrite(str(out/"x_lab_contact_192.png"),cv2.cvtColor(contact,cv2.COLOR_RGB2BGR))
    pairs=[]
    for i, recipe in enumerate(RECIPES):
        for other in RECIPES[i+1:]:
            pairs.append({"a":recipe.fid,"b":other.fid,"correlation":round(float(np.dot(structures[recipe.fid],structures[other.fid])),4)})
    pairs.sort(key=lambda row:row["correlation"],reverse=True)
    (out/"tile_metrics.json").write_text(json.dumps({"metrics":metrics,"nearest_structure_pairs":pairs[:30]},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"count":len(tiles),"contact":str(out/"x_lab_contact_192.png")},indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
