"""H1-I31 — Veiled Skull / obsidian cathedral lace, pass 1.

SPB-H1, 2026-08-31. New visible-carrier family after I30 was rejected.  The
neutral material is a controlled black art-deco lattice made of 8–32px-native
arches, ribs, diamonds and pearl intersections.  Hidden skull reliquaries are
interleaved into that pre-existing cadence exclusively through M/R/Cc.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_W=768; _C=OrderedDict(); _L=RLock()

def _deco_lace(seed):
    """Visible 8–32px-native art-deco anatomy; no secret in RGB."""
    ribs=np.zeros((_W,_W),np.uint8); pearls=np.zeros_like(ribs); rng=np.random.default_rng(int(seed)+501)
    cell=24
    for gy in range(0,_W,cell):
        for gx in range(0,_W,cell):
            jx=int((rng.random()-.5)*2); jy=int((rng.random()-.5)*2)
            cx=gx+cell//2+jx; cy=gy+cell//2+jy
            # P4: P3's connected lower arches became fish scales. Replace them
            # with vertical cathedral tracery: a tall diamond and centre rib,
            # each component still 8–32px native and never macro artwork.
            cv2.line(ribs,(cx,cy-11),(cx,cy+11),118,3,cv2.LINE_AA)
            dia=np.asarray(((cx,cy-10),(cx+6,cy),(cx,cy+10),(cx-6,cy)),np.int32)
            cv2.polylines(ribs,[dia],True,142,3,cv2.LINE_AA)
            cv2.line(ribs,(gx,cy+11),(gx+cell,cy+11),96,3,cv2.LINE_AA)
            # A restrained alternating side chevron retains secondary detail.
            if ((gx//cell)+(gy//cell))%2: cv2.line(ribs,(cx-9,cy),(cx-4,cy+5),101,3,cv2.LINE_AA)
            else: cv2.line(ribs,(cx+9,cy),(cx+4,cy+5),101,3,cv2.LINE_AA)
    return cv2.GaussianBlur(ribs.astype(np.float32)/255.,(0,0),.52),cv2.GaussianBlur(pearls.astype(np.float32)/255.,(0,0),.40)

def _skull_reliquaries(seed):
    """64 material-only hidden skulls seated inside the lace's cadence."""
    rel=np.zeros((_W,_W),np.uint8); glint=np.zeros_like(rel); rng=np.random.default_rng(int(seed)*1237+19)
    step=96
    for gy in range(48,_W,step):
        for gx in range(48,_W,step):
            cx=gx+int((rng.random()-.5)*12); cy=gy+int((rng.random()-.5)*12); sx=int(rng.integers(11,14)); sy=int(sx*1.16)
            # A complete small engraved skull made solely from 8–32px-native
            # components: crown, sockets, nose, teeth, halo and leaf scrolls.
            cv2.ellipse(rel,(cx,cy-sy//5),(sx,sy//2),0,0,360,164,3,cv2.LINE_AA)
            cv2.ellipse(rel,(cx,cy+sy//3),(sx-2,max(6,sy//3)),0,8,172,151,3,cv2.LINE_AA)
            for dx in (-sx//3,sx//3): cv2.ellipse(rel,(cx+dx,cy-sy//10),(max(3,sx//4),max(3,sy//5)),0,0,360,214,-1,cv2.LINE_AA)
            cv2.fillConvexPoly(rel,np.asarray(((cx,cy),(cx-3,cy+5),(cx+3,cy+5)),np.int32),188,lineType=cv2.LINE_AA)
            for dx in (-sx//3,-sx//9,sx//9,sx//3): cv2.line(rel,(cx+dx,cy+sy//3),(cx+dx,cy+sy//2),139,3,cv2.LINE_AA)
            cv2.ellipse(rel,(cx,cy+2),(sx+7,sy+8),0,198,342,98,3,cv2.LINE_AA)
            for sign in (-1,1): cv2.ellipse(rel,(cx+sign*(sx+8),cy+3),(4,6),sign*30,38,238,108,3,cv2.LINE_AA)
            cv2.ellipse(glint,(cx,cy-sy//5),(max(4,sx//2),max(3,sy//3)),0,196,344,255,3,cv2.LINE_AA)
    return cv2.GaussianBlur(rel.astype(np.float32)/255.,(0,0),.46),cv2.GaussianBlur(glint.astype(np.float32)/255.,(0,0),.40)

def _master(seed):
    lace,pearl=_deco_lace(seed); skull,glint=_skull_reliquaries(seed)
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32)
    sweep=.5+.5*np.sin(xx*.021-yy*.015+.38*np.sin(yy*.041))
    # Quiet graphite-black with cobalt/plum reflections that obey the actual
    # lace geometry. It should read as a complete premium finish when neutral.
    void=np.stack((.025+.018*sweep,.027+.021*sweep,.040+.034*sweep),2)
    cobalt=np.stack((.050+.052*sweep,.107+.095*sweep,.205+.145*sweep),2)
    plum=np.stack((.110+.070*(1-sweep),.025+.018*(1-sweep),.125+.085*(1-sweep)),2)
    pearl_col=np.stack((.34+.20*sweep,.42+.24*sweep,.58+.25*sweep),2)
    # P5: avoid a uniform wallpaper carrier. Broad reflected-light bands move
    # through the existing small diamond tracery without adding macro marks.
    ribbon=.5+.5*np.sin(xx*.017+yy*.023+.33*np.sin(yy*.041))
    art=void+cobalt*(.12+.11*ribbon+.43*lace)[...,None]+plum*(.035+.09*(1-ribbon)+.15*lace)[...,None]+pearl_col*(.10*pearl)[...,None]
    art=np.clip(np.power(np.clip(art,0,1),.72)*.96,0,1)
    # Separate material logic for metal / rough / clear follows the lace but
    # intentionally offsets each axis; it is not three recolors of one map.
    states=np.asarray(((17,45,16),(34,72,27),(57,106,43),(86,145,59),(116,180,76),(151,216,99),
                       (226,16,16),(248,41,239),(27,184,43),(68,222,101),(170,22,31),(238,8,10)),np.float32)
    q=np.clip(np.floor((.64*lace+.36*sweep)*5.7),0,5).astype(np.int32); base=states[q]
    spec=np.empty_like(base)
    spec[...,0]=base[...,0]+46*lace+21*pearl-18*sweep
    spec[...,1]=base[...,1]-52*lace+64*pearl+31*sweep
    spec[...,2]=base[...,2]+53*lace-30*pearl-27*sweep
    # Relics are material-only, seated into the lattice; their three cards are
    # deliberately interleaved so a single lighting angle cannot show all.
    hot=skull>.46; rim=(skull>.11)&~hot
    spec[hot]=.52*spec[hot]+.48*np.array((231,37,215),np.float32)
    spec[rim]=.56*spec[rim]+.44*np.array((30,181,55),np.float32)
    spec[glint>.40]=.50*spec[glint>.40]+.50*np.array((222,13,31),np.float32)
    return art.astype(np.float32),np.clip(spec,0,255).astype(np.uint8)

def _assets(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _L:
        if key in _C: _C.move_to_end(key); return _C[key]
    art,spec=_master(seed)
    if (h,w)!=(_W,_W):
        art=cv2.resize(art,(w,h),interpolation=cv2.INTER_AREA if max(h,w)<_W else cv2.INTER_LINEAR)
        spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    out=(art.astype(np.float32),spec.astype(np.uint8))
    with _L:
        _C[key]=out
        if len(_C)>2: _C.popitem(last=False)
    return out

def paint_veiled_skull_i31(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*pm)[...,None])+art*(np.clip(m,0,1)*pm)[...,None],0,1).astype(np.float32)

def spec_veiled_skull_i31(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
