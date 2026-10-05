"""H1-I32 — Veiled Skull / prismatic reliquary microstate screen, pass 1.

SPB-H1 owner direction, 2026-08-31: a hidden motif cannot be one flat bright
stamp. This rebuild uses a dark, fine prismatic neutral carrier and creates
each material-only skull out of interleaved chrome, matte, pearl and fractured
statelets so the hidden anatomy changes internally as light/view changes.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_houdini_veiled_skull_i30_2026 as _i30

_W=768; _C=OrderedDict(); _L=RLock()
def _frac(x): return x-np.floor(x)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*74.13)*43758.5453)

def _ornamental_masks(seed):
    """64 full-canvas skull reliquaries, each made from 8–32px-native parts."""
    allm=np.zeros((_W,_W),np.uint8); frame=np.zeros_like(allm); accent=np.zeros_like(allm); socket=np.zeros_like(allm)
    rng=np.random.default_rng(int(seed)*1117+71)
    for gy in range(8):
        for gx in range(8):
            cx=int((gx+.5+(rng.random()-.5)*.26)*(_W/8)); cy=int((gy+.5+(rng.random()-.5)*.27)*(_W/8))
            sx=int(rng.integers(11,14)); sy=int(sx*1.18); a=float((rng.random()-.5)*18)
            ca,sa=np.cos(np.deg2rad(a)),np.sin(np.deg2rad(a))
            def p(dx,dy): return int(cx+dx*ca-dy*sa),int(cy+dx*sa+dy*ca)
            # Complete skull anatomy: all strokes 3 work px (=8px native).
            cv2.ellipse(allm,p(0,-.16*sy),(sx,sy//2),a,0,360,168,3,cv2.LINE_AA)
            cv2.ellipse(allm,p(0,.30*sy),(max(7,sx-2),max(5,sy//3)),a,8,172,151,3,cv2.LINE_AA)
            for sign in (-1,1):
                cv2.ellipse(allm,p(sign*.31*sx,-.08*sy),(max(3,sx//4),max(3,sy//5)),a,0,360,218,-1,cv2.LINE_AA)
                cv2.ellipse(socket,p(sign*.31*sx,-.08*sy),(max(3,sx//4),max(3,sy//5)),a,0,360,225,-1,cv2.LINE_AA)
            tri=np.asarray([p(0,.03*sy),p(-.14*sx,.20*sy),p(.14*sx,.20*sy)],np.int32)
            cv2.fillConvexPoly(allm,tri,190,lineType=cv2.LINE_AA); cv2.fillConvexPoly(socket,tri,205,lineType=cv2.LINE_AA)
            for dx in (-.31*sx,-.10*sx,.10*sx,.31*sx):
                cv2.line(allm,p(dx,.28*sy),p(dx,.50*sy),141,3,cv2.LINE_AA)
                cv2.line(socket,p(dx,.28*sy),p(dx,.50*sy),170,3,cv2.LINE_AA)
            # Ornamental enclosure keeps the reveal from looking like a stamp.
            cv2.ellipse(frame,p(0,.03*sy),(sx+7,sy+8),a,198,343,111,3,cv2.LINE_AA)
            for sign in (-1,1):
                cv2.ellipse(frame,p(sign*1.03*sx,-.27*sy),(max(4,sx//3),max(3,sy//5)),a+sign*37,35,238,109,3,cv2.LINE_AA)
                cv2.ellipse(frame,p(sign*1.15*sx,.25*sy),(max(4,sx//4),max(4,sy//4)),a+sign*31,132,313,103,3,cv2.LINE_AA)
            cv2.ellipse(accent,p(0,-.15*sy),(max(4,sx//2),max(3,sy//3)),a,196,344,255,3,cv2.LINE_AA)
    blur=lambda a,s: cv2.GaussianBlur(a.astype(np.float32)/255.,(0,0),s)
    return blur(allm,.43),blur(frame,.42),blur(accent,.38),blur(socket,.38)

def _master(seed):
    # Reuse only I30's strongest neutral RGB carrier; discard its prior spec
    # entirely and author a new multi-state material deck below.
    art,_discard=_i30._master(seed)
    # P6: the inherited P1–P5 carrier was technically rich but too grey at
    # picker scale. Deepen it toward black chrome, then let one quiet cobalt
    # reflection move through existing micro-prisms—no new geometry or decal.
    yy0,xx0=np.mgrid[:_W,:_W].astype(np.float32)
    refl=.5+.5*np.sin(xx0*.018-yy0*.013+.31*np.sin(yy0*.039))
    art=art*np.array((.67,.78,1.00),np.float32)
    art += np.array((.005,.032,.078),np.float32)*(refl[...,None])
    art=np.clip(np.power(np.clip(art,0,1),.89),0,1)
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32); cell=12.0
    gx=xx/cell; gy=yy/cell; ix=np.floor(gx); iy=np.floor(gy); fx=gx-ix; fy=gy-iy
    h0=_hash(ix,iy,float(seed)); h1=_hash(ix+19,iy-23,float(seed)+4.7)
    edge=np.minimum(np.minimum(fx,1-fx),np.minimum(fy,1-fy)); seam=np.clip((.27-edge)/.27,0,1)
    face=np.where(fx+fy<1,0,1)+np.where(fx>fy,2,0)
    # Deliberately divergent base M/R/C cards in each small facet.
    metallic=34+154*h0+37*(face==3)+43*seam
    rough=215-148*h1+51*(face==1)-62*seam
    coat=31+179*_frac(h0*.67+h1*.48)+47*(face==2)+49*seam
    spec=np.stack((metallic,rough,coat),2)
    skull,frame,accent,socket=_ornamental_masks(seed)
    # Each skull's *interior* is a smart, deterministic microstate mosaic.
    # All primitives are 3–10 master px (8–27 native), not grain/noise.
    # P7: replace waveform flecks with actual 3-work-pixel / 8px-native
    # material tiles.  The deterministic offset deck makes every hidden skull
    # a composed micro-mosaic of physical states, never generic noise.
    tx=np.floor(xx/3.0).astype(np.int32); ty=np.floor(yy/3.0).astype(np.int32)
    micro=(tx*3+ty*5+(tx//4)*2+(ty//5))%4
    # P3: retain four neighboring chrome/matte/pearl states but compress the
    # extremes so a grazing reveal reads as a material event, not neon overlay.
    cards=np.asarray(((212,28,31),(51,178,61),(188,61,190),(116,96,188)),np.float32)
    inside=cards[micro]
    # P2: P1's outside halo was too uniform. Let the skull's own fractured
    # microstate interior emerge first; reserve frame and crown for later
    # glancing events rather than outlining a hard stamped icon.
    # P8: individual reliquaries need varying degrees of emergence across a
    # car, not a synchronized stamped response. The modulation is material
    # strength only; the neutral RGB carrier remains untouched.
    reveal=.68+.32*(.5+.5*np.sin(xx*.049+yy*.037+.42*np.sin(xx*.021-yy*.029)))
    outer=np.clip((skull*.82+frame*.20)*reveal,0,1); hot=outer>.20
    # The same hidden symbol holds neighboring chrome/matte/pearl states, and
    # the surrounding carrier remains untouched RGB paint.
    # P5: preserve the four internal finishes but leave more of the carrier
    # visible between them, allowing a symbol to assemble/disassemble across
    # light rather than appear as one high-contrast decal event.
    spec[hot]=.60*spec[hot]+.40*inside[hot]
    # P4: sockets/nose/teeth are a dedicated satin-matte card. This gives the
    # secret a readable internal hierarchy without ever writing it into paint.
    cut=socket>.16
    spec[cut]=.68*spec[cut]+.32*np.array((62,218,78),np.float32)
    rim=(frame>.32)&~hot
    spec[rim]=.54*spec[rim]+.46*np.array((28,184,55),np.float32)
    gl=(accent>.44)
    spec[gl]=.38*spec[gl]+.62*np.array((232,8,17),np.float32)
    return np.clip(art,0,1).astype(np.float32),np.clip(spec,0,255).astype(np.uint8)

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

def paint_veiled_skull_i32(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*pm)[...,None])+art*(np.clip(m,0,1)*pm)[...,None],0,1).astype(np.float32)

def spec_veiled_skull_i32(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
