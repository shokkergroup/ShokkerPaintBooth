"""FRACTURED HOUDINI H1-I11 — Veiled Skull / reliquary silk.

An irregular midnight silk carrier with fine chased marks.  Skull assemblies
are repeated over the entire canvas but exist solely in M/Rough/Cc cards.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=576
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _frac(x): return x-np.floor(x)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _arrays(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    sc=_WORK/max(h,w); hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32); sd=float(int(seed)^0xE117)

    # I11a visible carrier: five irregular fine material families—warp/weft
    # bundles, chased arcs, mica pips, short scars and dark seam pockets.
    warp=.5+.5*np.sin(xx*.92+1.5*np.sin(yy*.075)+.8*np.sin(xx*.16+yy*.11))
    weft=.5+.5*np.sin(yy*1.08+1.2*np.sin(xx*.068)-.7*np.sin(xx*.13-yy*.17))
    thread=np.exp(-((warp-.77)/.13)**2)*.44+np.exp(-((weft-.80)/.12)**2)*.36
    qx=np.floor(xx/5.8);qy=np.floor(yy/5.8);fx=_frac(xx/5.8)-.5;fy=_frac(yy/5.8)-.5
    salt=_hash(qx,qy,sd); ang=(salt-.5)*1.5
    u=fx*np.cos(ang)+fy*np.sin(ang);v=-fx*np.sin(ang)+fy*np.cos(ang)
    scar=np.exp(-(v/.055)**2)*np.exp(-((np.abs(u)-.19)/.19)**2)*(.35+.50*(salt>.54))
    pip=np.exp(-(((fx-(salt-.5)*.28)/.065)**2+((fy-(_hash(qx,qy,sd+3)-.5)*.28)/.065)**2))
    a=np.arctan2(fy,fx);r=np.sqrt(fx*fx+fy*fy)
    arc=np.exp(-((r-(.29+.06*salt))/.047)**2)*np.clip(.65+.35*np.cos(a*3+salt*6),0,1)
    seam=np.exp(-((np.abs(np.sin((xx*.31+yy*.27)+np.sin(xx*.07)*1.4))-.91)/.06)**2)*.22
    field=np.clip(.08+thread+scar*.42+pip*.35+arc*.48+seam,0,1)
    ridge=np.clip(thread*.70+arc*.75+scar*.56,0,1); recess=np.clip(seam+pip*.24,0,1)

    void=np.array((.012,.006,.030),np.float32);wine=np.array((.20,.012,.13),np.float32)
    indigo=np.array((.025,.060,.27),np.float32);violet=np.array((.34,.034,.48),np.float32)
    pearl=np.array((.58,.18,.58),np.float32);ink=np.array((.010,.018,.070),np.float32)
    paint=np.broadcast_to(void,(hh,ww,3)).copy()
    paint=paint*(1-field[...,None]*.64)+wine*(field[...,None]*.64)
    paint=paint*(1-thread[...,None]*.42)+indigo*(thread[...,None]*.42)
    paint=paint*(1-arc[...,None]*.45)+violet*(arc[...,None]*.45)
    paint=paint*(1-pip[...,None]*.62)+pearl*(pip[...,None]*.62)
    paint=paint*(1-recess[...,None]*.54)+ink*(recess[...,None]*.54)
    paint=np.clip(paint*(.94+.12*(.5+.5*np.sin(xx/47-yy/63))[...,None]),0,1)

    # Repeated connected skull engraving assemblies. Each mark is a 4–28px
    # native component after upscale; each complete motif is ~55px and occurs
    # dozens of times across the sheet, never once as a centered decal.
    # I11b: vectorized jittered cells. This preserves numerous rotated-looking
    # assemblies while removing the expensive full-canvas loop per motif.
    step=51.0;gx=np.floor(xx/step);gy=np.floor(yy/step)
    cx=(gx+.22+.58*_hash(gx,gy,sd+11))*step;cy=(gy+.18+.61*_hash(gx,gy,sd+29))*step
    rot=(_hash(gx,gy,sd+43)-.5)*.52;ca,sa=np.cos(rot),np.sin(rot)
    X=((xx-cx)*ca+(yy-cy)*sa)/7.2;Y=(-(xx-cx)*sa+(yy-cy)*ca)/8.6
    headrim=np.exp(-((np.sqrt(X*X+((Y+.14)/.88)**2)-.89)/.060)**2)
    jawrim=np.exp(-((np.sqrt((X/.64)**2+((Y-.56)/.33)**2)-.88)/.070)**2)
    eyes=np.maximum(np.exp(-((((X+.31)/.27)**2+((Y+.03)/.22)**2-.82)/.11)**2),np.exp(-((((X-.31)/.27)**2+((Y+.03)/.22)**2-.82)/.11)**2))
    sockets=np.maximum(np.clip(1-(((X+.31)/.18)**2+((Y+.03)/.14)**2),0,1),np.clip(1-(((X-.31)/.18)**2+((Y+.03)/.14)**2),0,1))
    nose=np.exp(-(((X/.115)**2+((Y-.29)/.16)**2-.70)/.14)**2)
    cheeks=np.exp(-((np.abs(np.abs(X)-(.30+.18*(Y+.10)))/.060)**2))*np.clip((Y+.10)*2.1,0,1)
    halo=np.clip(.048-np.abs(np.sqrt(X*X+Y*Y)-1.13),0,1)*20
    teeth=np.exp(-((np.sin(X*26)*.5+.5-.57)/.14)**2)*np.clip((Y-.27)*2.6,0,1)*np.clip(1-((X/.64)**2+((Y-.56)/.34)**2),0,1)
    skull=np.clip(headrim*.92+jawrim*.90+eyes*.70+cheeks*.63+nose*.55+teeth*.72+halo*.38,0,1)
    hollow=np.clip(sockets*.95+nose*.48,0,1);jaw=np.clip(jawrim*.72+teeth*.82,0,1)

    # Complete physical cards: matte seams, wet silk ridges, Fractured rail,
    # dark-chrome engraved lines and sparse clearcoat razors.
    # I11d — reserve hot/mirror cards for actual chased contours. Broad silk
    # stays a buried rose-metal rather than collapsing into a pink dot field.
    # I11e — hot arc state only at its chased crest; add independent rough
    # silk variation through thread/recess cards rather than pink repetitions.
    state=np.full((hh,ww),2,np.int32);state[recess>.20]=1;state[thread>.22]=0;state[arc>.62]=3;state[ridge>.58]=6;state[pip>.52]=5;state[(pip>.42)&(arc>.42)]=7
    secret=np.where(hollow>.32,1,np.where(jaw>.30,6,np.where(halo>.34,7,3)))
    state=np.where(skull>.12,secret,state)
    # I11c — Hologram-informed physical states, not the cyan/magenta
    # day/night pair that made I11b's literal map read as noise. The sparse
    # dielectric interruption remains for contrast; violet/rose dominates.
    M=np.array((180,22,206,234,250,254,224,40),np.float32)
    R=np.array((62,164,84,34,14,30,34,16),np.float32)
    C=np.array((152,48,184,222,248,168,188,16),np.float32)
    metal=M[state];rough=R[state];coat=C[state]
    if (hh,ww)!=(h,w): paint=_up(paint,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
    val=(paint.astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=val
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return val

def paint_veiled_skull_i11(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i11(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
