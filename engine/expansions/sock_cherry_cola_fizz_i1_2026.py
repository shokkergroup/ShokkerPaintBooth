"""Cherry Cola Fizz I1 — candidate 1950s diner candy-glass material.

SPB-105 / owner doctrine / 2026-08-30.  The inherited Cherry Polka card is
literal oversized dots.  This replacement is deep cherry-cola enamel with
fine 8–28px carbonation rings, cream foam skins, syrup depth, tiny chrome
catchlights and dark glass troughs.  Every event is generated from one
connected liquid field; no random dots, confetti, checker, or detached spec.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&0xffff)*.00107
    # A few gentle syrup currents move the fine carbonation without forming
    # repeated rows, a macro blob, or a radial centerpiece.
    u=x+5.4*np.sin(y/109.+phase)+2.7*np.sin((x+y)/53.)
    v=y+4.7*np.sin(x/131.-phase*.7)-2.5*np.sin((x-y)/61.)
    a=np.sin(u*.176+.54*np.sin(v*.083))
    b=np.sin(v*.153-.47*np.sin(u*.111))
    c=np.sin((u+v)*.098+.31*np.sin((u-v)*.067))
    liquid=np.clip(.5+.31*a+.24*b+.17*c,0,1)
    # Each threshold produces a connected bubble wall / foam skin / glass
    # trough. Their widths are 2–7px around 8–28px interior forms.
    foam=np.exp(-np.square((liquid-.57)/.050))
    ring=np.exp(-np.square((liquid-.70)/.045))
    syrup=np.clip((liquid-.62)/.38,0,1)
    trough=np.clip((.43-liquid)/.36,0,1)
    glint=np.clip((np.sin(u*.337+.62*np.sin(v*.201))
                   *np.sin(v*.289-.39*np.sin(u*.219))-.37)/.63,0,1)*ring
    # Slow colour is a candy-resin depth shift, not a background stripe.
    depth=.5+.5*np.sin(x/241.+.20*np.sin(y/79.)+phase)*np.sin(y/197.-.17*np.sin(x/103.))
    cherry=np.array((.46,.006,.040),np.float32)
    wine=np.array((.18,.003,.018),np.float32)
    cola=np.array((.13,.022,.016),np.float32)
    cream=np.array((.94,.72,.45),np.float32)
    chrome=np.array((.76,.66,.66),np.float32)
    paint=np.broadcast_to(cola,(h,w,3)).astype(np.float32).copy()
    paint+=cherry*((.24+.45*depth)*(.40+.60*liquid))[...,None]
    paint+=wine*(trough*(.26+.25*(1-depth)))[...,None]
    paint+=cream*(foam*(.10+.23*depth))[...,None]
    paint+=np.array((.75,.07,.20),np.float32)*(ring*(.06+.14*depth))[...,None]
    paint+=chrome*(glint*(.10+.27*depth))[...,None]
    M=17+106*syrup+69*ring+121*glint+57*foam+26*depth-38*trough
    R=223-68*syrup-111*ring-126*glint-64*foam+38*trough+16*(1-depth)
    C=18+93*syrup+94*ring+137*glint+68*foam+22*depth-28*trough
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_cherry_cola_fizz(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_cherry_cola_fizz(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
