"""Moonstone Adular I3—fractured cleavage-lacquer candidate; SPB-105 2026-08-27.
I1's contour eyes are rejected. I3 uses distinct moonstone packet pigment,
lamella abrasion and packet-depth clearcoat—no loops, noise, or shared carrier.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np
ID='fmo_moonstone_adular';NATIVE=2048
M=np.asarray((6,30,58,92,129,169,212,253),np.uint8);R=np.asarray((9,37,68,103,141,180,219,250),np.uint8);C=np.asarray((5,26,54,85,122,161,208,253),np.uint8)
def n(x):x=x.astype(np.float32);return(x-x.min())/(x.max()-x.min()+1e-8)
def q(x,t):return t[np.digitize(x,np.quantile(x,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def f():
 p=Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'moonstone_adular_livery_i3.png';a=cv2.imread(str(p),cv2.IMREAD_COLOR)
 if a is None:raise FileNotFoundError(p)
 x=cv2.cvtColor(cv2.resize(a,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0);gy=cv2.Sobel(l,cv2.CV_32F,0,1);e=n(np.hypot(gx,gy));lam=n(np.abs(l-cv2.GaussianBlur(l,(0,0),1.15)));depth=n(cv2.GaussianBlur(l,(0,0),18));cleave=n(np.abs(.77*gx-.64*gy));ice=np.clip((x[:,:,2]+.45*x[:,:,1]-1.05*x[:,:,0]-.1)/.38,0,1);lil=np.clip((x[:,:,2]+.25*x[:,:,0]-1.10*x[:,:,1]-.08)/.36,0,1);silver=np.clip((l-.40+.17*(1-h[:,:,1]/255.))/.38,0,1);gold=np.clip((x[:,:,0]+.38*x[:,:,1]-1.14*x[:,:,2]-.14)/.36,0,1);return x,e,lam,depth,cleave,ice,lil,silver,gold
def _paint(angle_b: bool = False) -> tuple[np.ndarray, tuple[np.ndarray, ...]]:
    """Return the same cleavage packet material under opposed optical travel."""
    x, edge, lamella, depth, cleavage, ice, lilac, silver, gold = f()
    a = np.clip(x * .81 + np.dstack((.10 * gold + .08 * lilac,
                                     .10 * ice + .06 * gold,
                                     .19 * ice + .13 * lilac)), 0, 1)
    if not angle_b:
        return a, (edge, lamella, depth, cleavage, ice, lilac, silver, gold)
    # SPB-105 / owner full-size review 2026-08-27: the flip retains every
    # moonstone packet and lamella, but changes which cleavage lips catch the
    # light.  This is optical ownership, not a global hue rotation.
    b = a * .26 + np.dstack((.31 * lilac + .21 * gold + .08 * silver,
                              .18 * ice + .12 * silver + .07 * gold,
                              .64 * ice + .46 * lilac + .09 * edge))
    b += np.dstack((.03 * cleavage, .06 * lamella, .13 * cleavage))
    return np.clip(b, 0, 1), (edge, lamella, depth, cleavage, ice, lilac, silver, gold)


def _material(fields: tuple[np.ndarray, ...]) -> np.ndarray:
    edge, lamella, depth, cleavage, ice, lilac, silver, _gold = fields
    metal = n(.42 * silver + .33 * ice + .29 * lilac + .17 * edge)
    rough = n(.53 * lamella + .30 * cleavage + .24 * edge)
    clear = n(.49 * depth + .31 * (.5 + .5 * np.sin(9 * depth + 4 * cleavage))
              - .18 * lamella + .19 * n(cv2.GaussianBlur(edge, (0, 0), 11)))
    return np.stack((q(metal, M), q(rough, R), q(clear, C)), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    a, fields = _paint(False)
    return a, _material(fields)


def clear_cache() -> None:
    f.cache_clear()


def render_evidence(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache(); started = time.perf_counter()
        a, fields = _paint(False); b, _ = _paint(True); spec = _material(fields)
        timings.append(time.perf_counter() - started)
        hashes.append(hashlib.sha256(a.tobytes() + b.tobytes() + spec.tobytes()).hexdigest())
        last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for name, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, index])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1,
              "spec_std": [float(spec[:, :, index].std()) for index in range(3)],
              "spec_range": [[int(spec[:, :, index].min()), int(spec[:, :, index].max())] for index in range(3)],
              "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "moonstone_adular_livery_i3"), indent=2))
