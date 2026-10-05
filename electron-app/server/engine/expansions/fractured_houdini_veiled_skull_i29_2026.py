"""H1-I29 — Veiled Skull / midnight engine-turned black steel, pass 1.

SPB-H1 owner reset, 2026-08-31: this is a new carrier screen after I27 and
I28 failed owner-eye review.  It deliberately avoids cellular oil, marble,
and wallpaper.  The visible finish is an innocent black engine-turned metal;
recurrent small skull reliquaries exist only in M/R/Cc.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_W=768; _C=OrderedDict(); _L=RLock()

def _soft(rng,n,blur):
    a=rng.normal(0,1,(n,n)).astype(np.float32)
    return cv2.GaussianBlur(cv2.resize(a,(_W,_W),interpolation=cv2.INTER_CUBIC),(0,0),blur)

def _skull_reliquary(seed):
    """Dense, whole-canvas 8–32px-native skull/ornament relief; never paint."""
    rel=np.zeros((_W,_W),np.uint8); glint=np.zeros_like(rel)
    rng=np.random.default_rng(int(seed)*9187+91)
    # P4: P1–P3 exposed an unacceptable one-work-pixel secret outline
    # (only ~3px native).  Every reliquary mark is now 3–12 work pixels
    # (8–32px native) while still recurring across the complete carrier.
    for gy in range(10):
        for gx in range(11):
            cx=int((gx+.5+(rng.random()-.5)*.52)*(_W/11)); cy=int((gy+.5+(rng.random()-.5)*.54)*(_W/10))
            sx=int(rng.integers(8,13)); sy=int(sx*1.15); a=float((rng.random()-.5)*34)
            ca,sa=np.cos(np.deg2rad(a)),np.sin(np.deg2rad(a))
            def p(dx,dy): return int(cx+dx*ca-dy*sa),int(cy+dx*sa+dy*ca)
            # crown, eyes, nasal cut, jaw/teeth: a miniature engraving, not an icon dot.
            # P5: P4 made the material skulls large enough, but their broken
            # crowns read like cartoon dots in the literal MRC audit.  A full,
            # fine engraved crown and separated jaw restore skull anatomy.
            cv2.ellipse(rel,p(0,-sy*.13),(sx,sy//2),a,0,360,176,3,cv2.LINE_AA)
            cv2.ellipse(rel,p(0,sy*.30),(max(3,sx-2),max(3,sy//3)),a,14,166,160,2,cv2.LINE_AA)
            for dx in (-sx*.31,sx*.31): cv2.ellipse(rel,p(dx,-sy*.07),(max(3,sx//4),max(3,sy//5)),a,0,360,216,-1,cv2.LINE_AA)
            cv2.fillConvexPoly(rel,np.array([p(0,.02*sy),p(-.12*sx,.20*sy),p(.12*sx,.20*sy)],np.int32),194,lineType=cv2.LINE_AA)
            for dx in (-.28*sx,0,.28*sx): cv2.line(rel,p(dx,.27*sy),p(dx,.45*sy),142,3,cv2.LINE_AA)
            # Fine frame, paired leaf curls and a partial halo supply artistic anatomy.
            cv2.ellipse(rel,p(0,.03*sy),(sx+3,sy+5),a,204,336,96,2,cv2.LINE_AA)
            for sign in (-1,1):
                cv2.ellipse(rel,p(sign*.86*sx,-.32*sy),(max(3,sx//3),max(3,sy//5)),a+sign*35,38,236,113,2,cv2.LINE_AA)
                cv2.ellipse(rel,p(sign*.96*sx,.24*sy),(max(3,sx//4),max(3,sy//4)),a+sign*28,135,312,104,2,cv2.LINE_AA)
            cv2.ellipse(glint,p(0,-.12*sy),(max(3,sx//2),max(3,sy//3)),a,198,342,255,2,cv2.LINE_AA)
    return cv2.GaussianBlur(rel.astype(np.float32)/255.,(0,0),.45),cv2.GaussianBlur(glint.astype(np.float32)/255.,(0,0),.38)

def _master(seed):
    rng=np.random.default_rng(int(seed)+211)
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32)
    low=_soft(rng,18,26.0); mid=_soft(rng,36,9.5)
    # Engine turning is thin, hand-like guilloche; all visible marks are 3–10
    # work pixels (=8–27px native), with changing orientation rather than a tile.
    u=xx+16*np.sin(yy*.018+low*1.5)+8*mid
    v=yy+15*np.sin(xx*.021-mid*1.3)-7*low
    # P3: P2's tiny maze still felt synthetic.  Open the hand-cut spacing,
    # keep each actual line 8–20px native, and let a quiet second pass cross
    # the first instead of creating cellular boundaries.
    a=np.sin(u*.31 + .25*np.sin(v*.043+low))
    b=np.sin(v*.23 - .18*np.sin(u*.051-mid))
    line_a=np.exp(-((np.abs(a)-.925)/.057)**2)
    line_b=np.exp(-((np.abs(b)-.942)/.046)**2)
    # Subtle turn-overlapping crescents; deliberately irregular, never a cell skin.
    radial=np.sin(np.hypot(u-384+42*np.sin(v*.031),v-384+31*np.sin(u*.029))*.18+mid*.9)
    curl=np.exp(-((np.abs(radial)-.965)/.025)**2)
    field=.52+.24*np.sin(u*.064+v*.038+low)+.14*np.sin(u*.019-v*.071+mid)
    field=np.clip(field,0,1)
    # P2: reject the P1 shadowy, wavy picker read. Favor the deliberate
    # crossed turn lines and reduce the broad curl to an occasional accent.
    engraving=np.clip(.78*line_a+.28*line_b+.04*curl,0,1)
    # Complete neutral visible carrier: graphite with cold indigo and restrained
    # antique-violet reflections bound to the linework, no hidden skull in RGB.
    black=np.stack((.034+.036*field,.038+.041*field,.052+.055*field),2)
    blue=np.stack((.018+.046*field,.051+.090*field,.115+.155*field),2)
    violet=np.stack((.064+.080*field,.017+.020*field,.075+.098*field),2)
    steel=np.stack((.22+.24*field,.27+.27*field,.36+.30*field),2)
    blue_mask=np.clip(.32+.68*np.sin(u*.029-v*.041+low),0,1)
    violet_mask=np.clip(.5+.5*np.sin(u*.021+v*.053-mid),0,1)
    art=black + blue*(.18+.15*blue_mask)[...,None] + violet*(.055+.055*violet_mask)[...,None] + steel*(.58*engraving)[...,None]
    art=np.clip(np.power(np.clip(art,0,1),.82)*.95+np.array((.010,.010,.015),np.float32),0,1)
    # Pattern-bound 12-state material deck: metallic, roughness and clearcoat
    # travel independently across the same fine turns, for real angle changes.
    states=np.asarray(((18,44,20),(36,70,29),(58,101,42),(84,136,56),
                       (110,168,72),(143,207,94),(224,16,15),(248,38,240),
                       (29,184,44),(67,223,101),(162,24,32),(238,8,9)),np.uint8)
    q=np.clip(np.floor(field*5.6),0,5).astype(np.int32); spec=states[q].astype(np.float32)
    spec[...,0]+=39*(line_a-.5)+26*(curl-.25)
    spec[...,1]+=72*(line_b-.5)-41*(curl-.20)
    spec[...,2]+=58*(curl-.24)+35*(line_a-line_b)
    # 144 repeating material-only reliquaries are integrated into pre-existing
    # physical linework with distinct high/low cards—not a generic RGB nudge.
    # P5: retain the detailed material engraving without turning the literal
    # diagnostic into flat neon symbols.  Three interleaved physical cards
    # reveal at different angles; no one channel carries the whole picture.
    skull,glint=_skull_reliquary(seed); hot=skull>.58; rim=(skull>.12)&~hot
    spec[hot]=.52*spec[hot]+.48*np.array((232,38,214),np.float32)
    spec[rim]=.54*spec[rim]+.46*np.array((31,182,55),np.float32)
    spec[glint>.40]=.50*spec[glint>.40]+.50*np.array((221,13,31),np.float32)
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

def paint_veiled_skull_i29(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*pm)[...,None])+art*(np.clip(m,0,1)*pm)[...,None],0,1).astype(np.float32)

def spec_veiled_skull_i29(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
