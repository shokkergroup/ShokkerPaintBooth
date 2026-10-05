"""FRACTURED HOUDINI H1-I6 — Veiled Skull / cut-enamel nocturne.

I6 discards the I5 stripe/lattice topology.  The ordinary carrier is an
asymmetric field of tiny cut-enamel facets, inlaid edge filigree, worn faces,
and mica pin-prisms.  Repeated skulls exist only as a local redistribution of
those material states; paint never receives skull geometry.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock(); _WORK=576
def _f(a): return a-np.floor(a)
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _hash(x,y,s): return _f(np.sin(x*12.9898+y*78.233+s*.017)*43758.5453)


def _cell_field(h,w,seed):
    """Jittered cut facets; neighbourhood ownership, never a visible grid."""
    yy,xx=np.mgrid[:h,:w].astype(np.float32); p=6.6
    gx=np.floor(xx/p); gy=np.floor(yy/p)
    best=np.full((h,w),1e9,np.float32); second=best.copy(); owner=np.zeros((h,w),np.float32)
    for oy in (-1,0,1):
        for ox in (-1,0,1):
            qx,qy=gx+ox,gy+oy
            cx=(qx+.18+.64*_hash(qx,qy,seed))*p
            cy=(qy+.18+.64*_hash(qx,qy,seed+53))*p
            d=(xx-cx)**2+(yy-cy)**2
            take=d<best
            second=np.where(take,best,np.minimum(second,d)); owner=np.where(take,_hash(qx,qy,seed+101),owner); best=np.minimum(best,d)
    rad=np.sqrt(best); gap=np.sqrt(second)-rad
    edge=np.clip((.78-gap)*1.55,0,1)
    face=np.clip(1-rad/(p*.69),0,1)
    return xx,yy,owner,edge,face


def _points(rng,w,h,n):
    out=[]
    for _ in range(n*200):
        if len(out)>=n:break
        p=(float(rng.uniform(-34,w+34)),float(rng.uniform(-40,h+40)))
        if all((p[0]-q[0])**2+(p[1]-q[1])**2>70**2 for q in out):out.append(p)
    return out


def _arrays(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    sc=min(1.,_WORK/max(h,w)); hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    xx,yy,own,edge,face=_cell_field(hh,ww,int(seed)); rng=np.random.default_rng(int(seed)^0x61A6)
    # Slow probability neighbourhoods organize fine facets, never becoming
    # large visible blocks.  Fine brush arcs and mica centres are attached to
    # the facets so there is no free-floating confetti.
    drift=.5+.5*np.sin(xx/59+np.sin(yy/41)+.55*np.cos((xx-yy)/83))
    flow=np.clip(.13-np.abs(np.sin((xx+6*np.sin(yy/25)+3*np.cos(xx/49))/3.05))*.72,0,1)
    inner=np.clip((face-.48)*2.1,0,1)*(1-edge*.55)
    pin=np.clip((_f(own*37.3+drift*5.7)-.83)*5.9,0,1)*inner

    # The hidden anatomy is only a local state-population field.  It is built
    # from many 8–32px facets; eyes/nose are not graphic cutouts.
    skull=np.zeros((hh,ww),np.float32); hollow=np.zeros_like(skull); chin=np.zeros_like(skull); wreath=np.zeros_like(skull)
    teeth=np.zeros_like(skull); ribs=np.zeros_like(skull); filigree=np.zeros_like(skull)
    for cx,cy in _points(rng,ww,hh,max(18,int(hh*ww/35000))):
        rx,ry=rng.uniform(20,29),rng.uniform(27,37); a=rng.uniform(-.31,.31);ca,sa=np.cos(a),np.sin(a)
        X=((xx-cx)*ca+(yy-cy)*sa)/rx;Y=(-(xx-cx)*sa+(yy-cy)*ca)/ry
        crown=np.clip(1-(X*X+((Y+.13)/.86)**2),0,1); lower=np.clip(1-((X/.60)**2+((Y-.55)/.34)**2),0,1)
        skull=np.maximum(skull,np.maximum(crown,lower))
        e=np.maximum(np.clip(1-(((X+.31)/.28)**2+((Y+.04)/.21)**2),0,1),np.clip(1-(((X-.31)/.28)**2+((Y+.04)/.21)**2),0,1))
        n=np.clip(1-((X/.12)**2+((Y-.27)/.17)**2),0,1)
        hollow=np.maximum(hollow,np.maximum(e,n*.70)); chin=np.maximum(chin,lower*np.clip((Y-.29)*2.6,0,1))
        rr=np.sqrt(X*X+Y*Y); wreath=np.maximum(wreath,np.clip(.10-np.abs(rr-1.05),0,1)*9)
        # Fine 8–20px internal anatomy: tooth slots and crown engraving alter
        # material states only. They make a discovered skull a relief, not a
        # pair of circular eyes pasted onto a field.
        teeth=np.maximum(teeth,lower*np.clip((Y-.25)*3.2,0,1)*np.clip(.16-np.abs(np.sin(X*27.0)),0,1)*6.2)
        ribs=np.maximum(ribs,crown*np.clip(.10-np.abs(np.sin(X*15.5 + Y*3.4)),0,1)*5.8)
        theta=np.arctan2(Y,X); radial=np.sqrt(X*X+Y*Y)
        filigree=np.maximum(filigree,crown*np.clip(.075-np.abs(np.sin(theta*5.0+radial*18.0)),0,1)*7.5)

    # Paint is the independent luxury enamel.  No skull/hollow/chin/wreath
    # value is allowed in this block.
    palette=np.array(((.085,.105,.188),(.122,.142,.252),(.175,.151,.315),(.238,.174,.375),(.142,.205,.326),(.302,.225,.440)),np.float32)
    # I6i: balanced lacquer depth. Regional variation only biases the tiny
    # facet families; it cannot become the broad striped field rejected in I6h.
    pi=np.clip((own*2.1+drift*2.25+inner*.85+flow*.45).astype(np.int32),0,len(palette)-1)
    paint=palette[pi]*(.78+.27*inner[...,None])
    paint=paint*(1-(edge*.28)[...,None])+np.array((.31,.34,.56),np.float32)*(edge*.28)[...,None]
    paint=paint*(1-(flow*.16)[...,None])+np.array((.26,.30,.50),np.float32)*(flow*.16)[...,None]
    paint=paint*(1-(pin*.33)[...,None])+np.array((.56,.49,.72),np.float32)*(pin*.33)[...,None]

    # Full material cards.  Each channel has independent physical meaning.
    # I6c / clean-restart mechanism 2: paired Fractured cards occupy nearly
    # the same literal violet/rose family but have deliberately separated BRDF
    # response.  A skull biases *state population*, so it can emerge at a
    # grazing response without being readable as paint or a coloured outline.
    base_state=np.clip((own*3.4+drift*1.3+inner*.8).astype(np.int32),0,4)
    # I6d is a deliberate reveal-strength experiment: each skull still uses
    # locally varied high-response cards, while cavities use locally varied
    # buried cards.  This gives the grazing route enough contrast to be tested
    # without drawing an RGB outline.
    raised=5+((own*3+flow*2+inner).astype(np.int32)%3)
    buried=(own*2+drift*2).astype(np.int32)%3
    secret_state=np.where(hollow>.22,buried,np.where(chin>.18,np.clip(raised+1,0,9),raised))
    secret_state=np.where(wreath>.20,3+((own*2).astype(np.int32)%3),secret_state)
    secret_state=np.where(teeth>.25,np.clip(raised+2,0,9),secret_state)
    secret_state=np.where(ribs>.22,4+((own*3).astype(np.int32)%3),secret_state)
    secret_state=np.where(filigree>.24,3+((own*4).astype(np.int32)%4),secret_state)
    state=np.where(skull>.09,secret_state,base_state)
    # I6b: avoid the literal red/cyan failure of I6a.  These are complete
    # Fractured violet/rose material states, not an RGB colorisation trick:
    # metallic exposure and coat condition vary independently, while the map
    # remains visually coherent enough for the owner to judge in the picker.
    M=np.array((170,185,200,215,230,246,238,223,214,205),np.float32)
    R=np.array((142,120,98,76,55,46,82,106,118,124),np.float32)
    C=np.array((186,202,218,234,248,250,238,223,216,208),np.float32)
    metal=M[state]+edge*39+flow*26+pin*29-inner*11
    rough=R[state]-edge*44-flow*25-pin*31+inner*13
    coat=C[state]-edge*43-flow*28-pin*22+inner*16
    # Within skull territory physical roles change state *locally*, never as
    # uniformly colored silhouettes. The optical read must come from adjacency.
    metal+=skull*18-hollow*24+chin*10+wreath*11+teeth*13+ribs*8+filigree*9
    rough+=-skull*19+hollow*31-chin*11+wreath*7-teeth*14-ribs*9-filigree*10
    coat+=-skull*21+hollow*29-chin*12+wreath*10-teeth*15-ribs*10-filigree*11
    if (hh,ww)!=(h,w):paint=_up(paint,w,h);metal,rough,coat=(_up(a,w,h) for a in (metal,rough,coat))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_veiled_skull_i6(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i6(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
