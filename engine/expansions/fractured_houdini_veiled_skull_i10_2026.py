"""FRACTURED HOUDINI H1-I10 — Veiled Skull / midnight marquetry.

Purpose-built clean candidate. The paint is a complete fine ornamental lacquer:
interlocking petals, diamond filigree, medallion rings, pricked inlay and thread
marks. Repeated skull anatomy exists only as small redirects among those existing
material plates; it is never drawn into paint.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=576
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _frac(a): return a-np.floor(a)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _arrays(shape,seed):
    h,w=map(int,shape);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    # I10k — author at one canonical working scale for every requested output.
    # Generating native 128px with 7.6px modules made the picker a macro
    # pattern; render at 576 then downsample so card and 2048² car agree.
    sc=_WORK/max(h,w);hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32);sd=float(int(seed)^0x51A77)

    # I10a visible carrier — 7.6 work-pixel modules resolve to ~27px native.
    # Five related mark families make a true surface, not scaled wallpaper.
    tile=7.6;qx=np.floor(xx/tile);qy=np.floor(yy/tile)
    fx=_frac(xx/tile)-.5;fy=_frac(yy/tile)-.5
    r=np.sqrt(fx*fx+fy*fy);a=np.arctan2(fy,fx)
    ring=np.exp(-((r-.335)/.045)**2)
    petal=np.exp(-((np.abs(np.sin(a*4.0))*r-.245)/.060)**2)*np.exp(-((r-.28)/.18)**2)
    diamond=np.exp(-((np.abs(fx)+np.abs(fy)-.43)/.040)**2)
    thread=np.exp(-((np.sin((fx-fy)*np.pi*4.0)*.5+.5-.70)/.075)**2)*.36
    jx=.18*np.sin(qx*1.71+qy*2.31+sd*.003);jy=.18*np.cos(qx*2.13-qy*1.27+sd*.004)
    prick=np.exp(-(((fx-jx)/.055)**2+((fy-jy)/.055)**2))
    salt=_hash(qx,qy,sd);orn=np.clip(ring*.83+petal*.58+diamond*.48+thread+prick*.74,0,1)
    micro=.5+.5*np.sin((xx*1.37+yy*.91)+np.sin(xx*.47-yy*.32)*1.4)
    micro=np.exp(-((micro-.78)/.16)**2)*.18
    # I10c — give the innocent lacquer a readable midtone bed; pattern density
    # increases by layered value, not by enlarging its 27px native modules.
    field=np.clip(.22+orn*(.72+.22*salt)+micro,0,1);edge=np.clip((ring+diamond+petal*.55),0,1)

    # Paint never samples any skull variable. It is a complete midnight-violet
    # marquetry finish even if every secret material state is disabled.
    # I10b — native proof had good anatomy but the field disappeared at picker
    # scale. Lift the material hierarchy, never the primitive size.
    void=np.array((.040,.012,.088),np.float32);indigo=np.array((.16,.035,.34),np.float32)
    violet=np.array((.54,.105,.76),np.float32);cobalt=np.array((.030,.31,.67),np.float32)
    rose=np.array((.82,.18,.72),np.float32);gold=np.array((.92,.43,.18),np.float32)
    paint=np.broadcast_to(void,(hh,ww,3)).copy()
    paint=paint*(1-field[...,None]*.82)+indigo*(field[...,None]*.82)
    paint=paint*(1-petal[...,None]*.57)+violet*(petal[...,None]*.57)
    paint=paint*(1-ring[...,None]*.48)+cobalt*(ring[...,None]*.48)
    paint=paint*(1-prick[...,None]*.56)+rose*(prick[...,None]*.56)
    paint=paint*(1-micro[...,None]*.32)+gold*(micro[...,None]*.32)
    paint=np.clip(paint*(.92+.17*(.5+.5*np.sin(xx/39+yy/57))[...,None]),0,1)

    # I10e — one 20px silhouette vanished in whole-car evidence. Build each
    # repeated skull from several 8–32px components into a ~35px motif, then
    # repeat it across the entire carrier rather than placing one giant icon.
    step=27.0;gx=np.floor(xx/step);gy=np.floor(yy/step)
    cx=(gx+.22+.56*_hash(gx,gy,sd+11))*step;cy=(gy+.23+.54*_hash(gx,gy,sd+29))*step
    X=(xx-cx)/(4.30+.55*_hash(gx,gy,sd+43));Y=(yy-cy)/(5.20+.65*_hash(gx,gy,sd+59))
    # I10h — no filled cartoon head. This is an engraved reliquary skull made
    # from separate fine contour, hollow, cheek-cut, tooth and halo components.
    head=np.clip(1-(X*X+((Y+.12)/.90)**2),0,1);jawfill=np.clip(1-((X/.62)**2+((Y-.57)/.33)**2),0,1)
    headrim=np.exp(-((np.sqrt(X*X+((Y+.12)/.90)**2)-.91)/.075)**2)*np.clip(1-Y*.18,0,1)
    jawrim=np.exp(-((np.sqrt((X/.62)**2+((Y-.57)/.33)**2)-.89)/.085)**2)
    eye_outer=np.maximum(np.exp(-((((X+.31)/.28)**2+((Y+.02)/.23)**2-.84)/.13)**2),np.exp(-((((X-.31)/.28)**2+((Y+.02)/.23)**2-.84)/.13)**2))
    eye_inner=np.maximum(np.clip(1-(((X+.31)/.19)**2+((Y+.02)/.14)**2),0,1),np.clip(1-(((X-.31)/.19)**2+((Y+.02)/.14)**2),0,1))
    nose=np.exp(-(((X/.12)**2+((Y-.28)/.16)**2-.70)/.18)**2)
    cheek=np.exp(-((np.abs(np.abs(X)-(.30+.18*(Y+.12)))/.075)**2))*head*np.clip((Y+.10)*2.0,0,1)
    halo=np.clip(.060-np.abs(np.sqrt(X*X+Y*Y)-1.10),0,1)*15
    teeth=jawfill*np.exp(-((np.sin(X*24)*.5+.5-.57)/.16)**2)*np.clip((Y-.26)*2.5,0,1)
    skull=np.clip(headrim*.90+jawrim*.82+eye_outer*.72+cheek*.58+nose*.52+teeth*.64+halo*.44,0,1)
    hollow=np.clip(eye_inner*.95+nose*.48,0,1);jaw=np.clip(jawrim*.80+teeth*.70,0,1)

    # I10i — Spec Guide v1 material cards, not a decorative RGB ramp. The
    # pattern owns actual day-matte, gloss, Fractured, dark-chrome and white
    # razor states; each channel therefore has a causal physical role.
    base=np.zeros((hh,ww),np.int32)                            # F0: day-matte rest
    # I10j — ratio pass: give the Fractured rail enough interleaved ownership
    # to create optical motion while retaining a coherent quiet matte ground.
    base[field>.31]=1                                          # F1: deep porous seam
    base[petal>.13]=3                                          # P2: Fractured satin petal
    base[petal>.37]=4                                          # P4: active petal core
    base[ring>.22]=2                                           # G0: wet gloss ring
    base[edge>.61]=6                                           # E0: dark-chrome engraved lip
    base[prick>.34]=5                                          # P6: hot inlay dot
    base[(micro>.12)&(edge>.32)]=7                             # W0: rare white razor
    up=np.clip(base+2,0,7);down=np.clip(base-2,0,7)
    secret=np.where(hollow>.30,down,up);secret=np.where(jaw>.24,np.clip(up+1,0,7),secret)
    secret=np.where(halo>.28,np.clip(base+1,0,7),secret);secret=np.where(teeth>.28,up,secret)
    # I10g — let the whole tiny silhouette participate. The prior decorative
    # gate broke it into unrelated flecks, which cannot form a light reveal.
    use=(skull>.12)
    state=np.where(use,secret,base)
    # F0/F1, G0, P2/P4/P6, E0, W0 respectively. No interpolation occurs
    # between incompatible physics; fine masks choose complete cards.
    M=np.array((0,8,0,246,250,254,250,40),np.float32)
    R=np.array((220,235,30,62,46,30,15,16),np.float32)
    C=np.array((210,220,16,250,254,255,40,16),np.float32)
    metal=M[state].astype(np.float32);rough=R[state].astype(np.float32);coat=C[state].astype(np.float32)
    # I10d — a light-dependent reveal needs meaningful separation among
    # adjacent material states. The skull remains absent from paint and is
    # still only ~20px native; this boosts response contrast, not icon scale.
    metal+=skull*34-hollow*68+jaw*42+halo*26+teeth*38;rough+=-skull*48+hollow*76-jaw*50+halo*32-teeth*48;coat+=-skull*52+hollow*84-jaw*54+halo*36-teeth*54
    if (hh,ww)!=(h,w):paint=_up(paint,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
    val=(paint.astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=val
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return val

def paint_veiled_skull_i10(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i10(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
