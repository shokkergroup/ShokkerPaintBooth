"""Lemon Meringue Pearloid I1 — candidate 1950s counter enamel.

SPB-105 / owner doctrine / 2026-08-30.  Lemon Polka's green-dot wallpaper is
replaced with a period-true diner material: creamy lemon pearloid enamel with
connected 8–28px inlay cells, 2–6px chrome rims, custard depth, mica cores,
and toasted-sugar troughs.  It uses a nonperiodic, connected enamel field;
there are no literal polka dots, checker cells, or random flecks.
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
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&0xffff)*.00131
    u=x+4.8*np.sin(y/103.+phase)+2.3*np.sin((x+y)/49.)
    v=y+4.1*np.sin(x/127.-phase*.7)-2.1*np.sin((x-y)/57.)
    p=np.sin(u*.171+.52*np.sin(v*.081))
    q=np.sin(v*.149-.44*np.sin(u*.109))
    r=np.sin((u+v)*.093+.30*np.sin((u-v)*.065))
    enamel=np.clip(.5+.30*p+.25*q+.18*r,0,1)
    pearl=np.clip((enamel-.61)/.39,0,1)
    rim=np.exp(-np.square((enamel-.57)/.047))
    core=np.clip((np.sin(u*.303+.57*np.sin(v*.191))*np.sin(v*.271-.43*np.sin(u*.213))-.34)/.66,0,1)*pearl
    toast=np.clip((.42-enamel)/.35,0,1)
    # Gentle regional custard warmth survives a picker without becoming a
    # broad primitive or stripe.
    warm=.5+.5*np.sin(x/237.+.21*np.sin(y/77.)+phase)*np.sin(y/191.-.18*np.sin(x/107.))
    cream=np.array((.58,.47,.13),np.float32)
    lemon=np.array((.91,.74,.05),np.float32)
    pearlcol=np.array((.98,.89,.49),np.float32)
    amber=np.array((.44,.18,.03),np.float32)
    chrome=np.array((.71,.74,.58),np.float32)
    paint=np.broadcast_to(cream,(h,w,3)).astype(np.float32).copy()
    paint+=lemon*((.17+.31*warm)*(.38+.62*enamel))[...,None]
    paint+=pearlcol*(pearl*(.11+.22*warm))[...,None]
    paint+=amber*(toast*(.13+.20*(1-warm)))[...,None]
    paint+=chrome*(rim*(.06+.15*warm))[...,None]
    paint+=np.array((1.0,.92,.67),np.float32)*(core*.12)[...,None]
    M=21+91*enamel+107*pearl+83*rim+121*core+28*warm-38*toast
    R=219-57*enamel-92*pearl-109*rim-127*core+41*toast+17*(1-warm)
    C=19+84*enamel+122*pearl+106*rim+142*core+27*warm-26*toast
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_lemon_meringue_pearl(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_lemon_meringue_pearl(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
