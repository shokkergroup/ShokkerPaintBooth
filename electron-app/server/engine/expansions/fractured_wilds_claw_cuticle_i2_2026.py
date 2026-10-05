# -*- coding: utf-8 -*-
"""Claw Rake I2 — raw native 2048 keratin-damage study.

The carrier is a continuous, fine triply-periodic keratin cuticle; short claw
incisions merely damage that body.  This avoids both the prior global-scratch
rail failure and decorative isolated mark fields.  All geometry is analytic
and deterministic: no noise/FBM/RNG/stamp atlas/shared Wilds renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np

ID, WORK, NATIVE = "fc_claw_rake", 1024, 2048
A = np.asarray(((5, 8, 11), (12, 27, 32), (21, 52, 54), (37, 83, 75),
                (64, 116, 91), (110, 145, 97), (158, 164, 93), (205, 148, 84),
                (220, 102, 83), (185, 62, 93), (129, 47, 111), (72, 47, 112)), np.float32)
B = np.asarray(((7, 6, 12), (23, 13, 31), (49, 24, 58), (84, 39, 85),
                (123, 60, 109), (163, 91, 127), (201, 134, 139), (224, 181, 151),
                (196, 217, 154), (132, 205, 160), (74, 162, 159), (38, 102, 143)), np.float32)


def _palette(v: np.ndarray, bank: np.ndarray) -> np.ndarray:
    p = np.mod(v, 1.0) * len(bank)
    lo = np.floor(p).astype(np.int16)
    q = (p - lo)[..., None]
    return bank[lo] * (1.0 - q) + bank[(lo + 1) % len(bank)] * q


def _curve(ctrl: tuple[tuple[int, int], ...], n: int = 64) -> np.ndarray:
    p = np.asarray(ctrl, np.float32)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return np.rint(q**3*p[0] + 3*q*q*t*p[1] + 3*q*t*t*p[2] + t**3*p[3]).astype(np.int32)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # A deformed gyroid makes a single continuous keratin microcuticle.  Its
    # 4--12 work-pixel webs become 8--24 native px after the final upsample.
    warp_a = 0.33*np.sin((x + 1.7*y)/97.0) + 0.19*np.sin((2.0*x-y)/43.0)
    warp_b = 0.28*np.cos((x-1.3*y)/79.0) + 0.17*np.sin((x+y)/53.0)
    u, v, w = x/4.1 + warp_a, y/4.6 + warp_b, (x+y)/5.2 + 0.6*warp_a - 0.5*warp_b
    gyroid = np.sin(u)*np.cos(v) + np.sin(v)*np.cos(w) + np.sin(w)*np.cos(u)
    web = np.exp(-np.square(gyroid/0.30)).astype(np.float32)
    cell = np.exp(-np.square((np.abs(gyroid)-0.83)/0.24)).astype(np.float32)
    # A second nonparallel protein grain stays subordinate to the cuticle.
    protein = 0.5 + 0.5*np.sin((0.72*x-0.48*y)/3.2 + 0.45*np.sin((x+y)/61.0))
    shoulder = np.clip(cell*(0.42+0.58*protein), 0.0, 1.0)
    phase = np.mod(0.19 + 0.36*web + 0.28*shoulder + 0.17*np.sin((x-2*y)/137.0), 1.0)
    if angle_b:
        phase = np.mod(phase + 0.36 + 0.11*web - 0.08*shoulder, 1.0)
        light = 0.20 + 0.36*web + 0.28*shoulder + 0.13*protein
        bank = B
    else:
        light = 0.18 + 0.41*web + 0.25*shoulder + 0.11*(1.0-protein)
        bank = A
    image = np.clip(_palette(phase, bank) * light[..., None], 0, 255).astype(np.uint8)

    cut = np.zeros((WORK, WORK), np.uint8)
    lip = np.zeros_like(cut)
    trough = np.zeros_like(cut)
    stitch = np.zeros_like(cut)
    abrasion = np.zeros_like(cut)
    # Every incision is a short, unequal mechanical failure (18--30 native
    # px), not an uninterrupted scratch rail.
    cuts = (
        ((84, 105), (91, 98), (106, 111), (118, 102)), ((219, 151), (228, 143), (243, 156), (257, 148)),
        ((402, 82), (413, 94), (424, 86), (438, 98)), ((641, 143), (648, 134), (663, 149), (676, 141)),
        ((826, 91), (836, 104), (850, 97), (863, 109)), ((133, 337), (145, 328), (158, 343), (173, 335)),
        ((311, 285), (320, 298), (333, 290), (346, 304)), ((531, 352), (542, 342), (554, 356), (567, 347)),
        ((744, 309), (753, 322), (766, 313), (779, 326)), ((916, 382), (927, 371), (940, 385), (953, 376)),
        ((76, 573), (88, 564), (102, 579), (115, 570)), ((246, 521), (255, 534), (269, 526), (283, 539)),
        ((455, 609), (466, 599), (481, 613), (494, 604)), ((662, 550), (672, 563), (687, 555), (700, 568)),
        ((847, 631), (858, 620), (872, 634), (886, 625)), ((169, 758), (181, 749), (194, 764), (208, 755)),
        ((365, 700), (376, 713), (389, 704), (402, 717)), ((564, 827), (574, 817), (589, 831), (602, 821)),
        ((749, 753), (760, 766), (774, 757), (788, 770)), ((928, 894), (938, 884), (953, 898), (966, 889)),
    )
    for i, ctrl in enumerate(cuts):
        pts = _curve(ctrl)
        cv2.polylines(cut, [pts], False, 118+(i%8)*16, 1, cv2.LINE_AA)
        cv2.polylines(lip, [pts + np.asarray((1 if i&1 else -1, -1 if i&1 else 1))], False, 112+(i%8)*18, 1, cv2.LINE_AA)
        mid = pts[24:43]
        cv2.polylines(trough, [mid], False, 126+(i%8)*16, 2, cv2.LINE_AA)
        if i % 2 == 0:
            for p in pts[13:53:10]:
                cv2.circle(stitch, tuple(p), 1, 132+(i%8)*15, -1, cv2.LINE_AA)
        if i % 3 == 0:
            p = pts[35]
            cv2.ellipse(abrasion, tuple(p), (3, 2), (i*29)%180, 0, 360, 128+(i%8)*16, -1, cv2.LINE_AA)
    # Each damage reaction follows a different material rule.
    image = image.astype(np.float32)
    image *= (1.0 - 0.86*(trough.astype(np.float32)/255.0)[...,None])
    image += cv2.cvtColor(lip, cv2.COLOR_GRAY2RGB).astype(np.float32) * np.asarray((0.30, 0.42, 0.24) if angle_b else (0.46, 0.31, 0.13))
    image += cv2.cvtColor(stitch, cv2.COLOR_GRAY2RGB).astype(np.float32) * np.asarray((0.17, 0.37, 0.31))
    image *= (1.0 - 0.29*(abrasion.astype(np.float32)/255.0)[...,None])
    return np.clip(image, 0, 255).astype(np.uint8), {"cuticle_web": (web*255).astype(np.uint8), "shoulder": (shoulder*255).astype(np.uint8), "protein": (protein*255).astype(np.uint8), "cut": cut, "lip": lip, "trough": trough, "stitch": stitch, "abrasion": abrasion}


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 0]): raise OSError(path)


def _spec_maps(marks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """M/R/Cc follow the visible cuticle and claw-damage anatomy.

    SPB-105 / owner verdict 2026-08-27: the prior roughness channel was
    dominated by the separate diagonal ``protein`` sine field.  That made a
    diagonal material pattern travel independently of the painted claw/cuticle
    design.  Protein remains a subtle paint-phase ingredient, but no spec
    channel may be driven by it; every response below comes from a visible
    cuticle face, edge, lip, trough, stitch, or abrasion mark.
    """
    tm=np.asarray((5,38,71,105,142,179,216,251),np.uint8); tr=np.asarray((8,43,77,111,146,182,218,249),np.uint8); tc=np.asarray((4,39,73,106,142,179,216,252),np.uint8)
    web=marks['cuticle_web'].astype(np.float32)/255; shoulder=marks['shoulder'].astype(np.float32)/255
    cutv=marks['cut'].astype(np.float32)/255; lipv=marks['lip'].astype(np.float32)/255; troughv=marks['trough'].astype(np.float32)/255; stitchv=marks['stitch'].astype(np.float32)/255; abrasionv=marks['abrasion'].astype(np.float32)/255
    cut=cutv>0; lip=lipv>0; trough=troughv>0; stitch=stitchv>0; abrasion=abrasionv>0
    # Visible micro-edge density of the existing gyroid cuticle, not a new
    # decorative directional field. It owns the tactile matte response.
    micro=np.hypot(cv2.Sobel(web,cv2.CV_32F,1,0),cv2.Sobel(web,cv2.CV_32F,0,1)); micro/=micro.max()+1e-8
    polish=cv2.GaussianBlur(shoulder,(0,0),3.0); polish=(polish-polish.min())/(polish.max()-polish.min()+1e-8)
    # Metal owns intact raised web faces and healed stitch/lip hardware.
    mi=np.floor(np.clip(.10+.63*web+.20*shoulder+.10*micro,0,.999)*8).astype(np.int16); mi[trough|cut]=0; mi[stitch|lip]=7
    # Roughness owns visible cuticle micro-edges, troughs and abrasion only.
    ri=np.floor(np.clip(.08+.49*micro+.25*shoulder+.12*troughv+.10*abrasionv,0,.999)*8).astype(np.int16); ri[trough|abrasion]=7; ri[lip]=0
    # Clearcoat owns smooth shoulder faces and uplifted lacquer lips, distinct
    # from both metallic web coverage and rough cuticle edge density.
    ci=np.floor(np.clip(.09+.58*polish+.18*web+.12*lipv+.08*stitchv,0,.999)*8).astype(np.int16); ci[trough|cut]=0; ci[lip|stitch]=7
    return tm[np.clip(mi,0,7)],tr[np.clip(ri,0,7)],tc[np.clip(ci,0,7)]


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, marks = _paint(False)
    return paint, np.stack(_spec_maps(marks), axis=2)


def _corr(a: np.ndarray,b:np.ndarray)->float:
    return float(np.corrcoef(a.astype(np.float32).ravel(),b.astype(np.float32).ravel())[0,1])


def main() -> int:
    out = Path(__file__).resolve().parents[2] / "_wilds_rejection_work" / "claw_cuticle_i2"; out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter(); a, marks = _paint(False); b, _ = _paint(True); m,r,cc=_spec_maps(marks)
    a, b = cv2.resize(a, (NATIVE,NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.resize(b, (NATIVE,NATIVE), interpolation=cv2.INTER_LANCZOS4)
    _write(out/f"{ID}_angle_a_2048.png", a); _write(out/f"{ID}_angle_b_2048.png", b); _write(out/f"{ID}_detail_1to1_1024.png", a[512:1536,512:1536])
    for suffix,ch in (("M",m),("R",r),("Cc",cc)):
        native=cv2.resize(ch,(NATIVE,NATIVE),interpolation=cv2.INTER_NEAREST); _write(out/f"{ID}_{suffix}_2048.png",cv2.cvtColor(native,cv2.COLOR_GRAY2RGB))
    delta=np.mean(np.abs(a.astype(np.float32)-b.astype(np.float32)),2)/255.0
    (out/'manifest.json').write_text(json.dumps({'id':ID,'status':'KEEP-CANDIDATE-I2-NATIVE-2048-MATERIALLED-NOT-WIRED','topology':'continuous fine gyroid keratin cuticle with short claw cuts, uplift lips, troughs, stitches and abrasion','angle_delta_mean':round(float(delta.mean()),6),'angle_delta_p95':round(float(np.percentile(delta,95)),6),'coverage':{n:round(float(np.mean(v>0)),6) for n,v in marks.items()},'spec':{'std':[round(float(np.std(c)),6) for c in (m,r,cc)],'range':[[int(c.min()),int(c.max())] for c in (m,r,cc)],'occupied_tiers':[int(len(np.unique(c))) for c in (m,r,cc)],'correlations_m_r_m_cc_r_cc':[round(_corr(m,r),6),round(_corr(m,cc),6),round(_corr(r,cc),6)]},'elapsed_seconds':round(time.perf_counter()-started,6)},indent=2)+'\n',encoding='utf-8')
    return 0

if __name__ == '__main__': raise SystemExit(main())
