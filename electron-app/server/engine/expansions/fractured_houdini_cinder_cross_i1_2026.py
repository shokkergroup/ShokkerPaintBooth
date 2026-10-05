"""FRACTURED HOUDINI H4-I1 — Cinder Cross / oxidized jade damascene."""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _fract(a): return a - np.floor(a)


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        got=_CACHE.get(key)
        if got is not None:
            _CACHE.move_to_end(key); return got
    # I8 rejection: 768² did not improve the cold picker path.  Keep the
    # previously measured 832² work field: irregular puddles stay above 8px
    # native and the 9-neighbor carrier remains within its direct 2048 budget.
    # cloisonné search added genuine carrier complexity.
    scale=min(1.0,832.0/max(h,w)); hh,ww=max(96,round(h*scale)),max(96,round(w*scale))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32); phase=(int(seed)%3181)*.0059
    # I6 (owner 2026-08-30): the former analytic damascene made broad vertical
    # waves at card scale.  Retain a warped microcell coordinate only; every
    # visible mark below is cell-local (8–30px native), never a whole-canvas
    # sine lane.
    a=(x+2.1*np.sin(y/13+phase)+1.4*np.cos((x-y)/17))/5.7
    b=(y-1.8*np.sin(x/15-.7*phase)+1.2*np.cos((x+2*y)/21))/7.4
    # I3: reject the stamped running-bond wall.  This is a whole-surface,
    # deterministic micro-cloisonné of irregular 10–24px native puddle cells:
    # five overlapping mark classes now share the carrier instead of one line.
    ux,uy=x/6.4,y/6.4; ix=np.floor(ux).astype(np.int32); iy=np.floor(uy).astype(np.int32)
    near=np.full((hh,ww),99.,np.float32); next_near=np.full((hh,ww),99.,np.float32)
    mosaic_state=np.zeros((hh,ww),np.float32)
    for ox in (-1,0,1):
        for oy in (-1,0,1):
            nx,ny=ix+ox,iy+oy
            jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545)
            jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635)
            dsq=(ux-(nx+jx))**2+(uy-(ny+jy))**2
            take=dsq<near
            next_near=np.where(take,near,np.minimum(next_near,dsq))
            near=np.where(take,dsq,near)
            local=np.mod(nx*23+ny*41+(nx^ny)*7+int(seed),8).astype(np.float32)/7.
            mosaic_state=np.where(take,local,mosaic_state)
    dist=np.sqrt(near); seamgap=np.sqrt(next_near)-dist
    puddle=np.clip(1-dist/.87,0,1)
    rim=np.exp(-np.square((seamgap-.10)/.055))
    # Five local surface marks: fired enamel, copper oxidation, hairline inlay,
    # kiln cracks and pearl rims.  Hash states break station regularity without
    # using large stripes, wallpaper lanes, or random confetti.
    micro=np.mod(ix*19+iy*43+(ix^iy)*11+int(seed),8).astype(np.float32)/7.
    fired=.18+.82*mosaic_state
    inlay=np.clip(rim*.83+np.clip((puddle-.74)*3.2,0,1)*.34,0,1)
    damask=np.clip((1-dist/.59)*(.30+.70*micro),0,1)*(1-rim*.35)
    oxide=((np.mod(ix*31+iy*17+int(seed),13)<3).astype(np.float32))*np.clip(.25+.75*puddle,0,1)*(1-inlay*.55)
    crack=np.clip((np.abs(np.mod(ux+uy*.63,1)-.5)-.38)*8.3,0,1)*(.25+.75*micro)*(1-inlay*.45)
    state=np.mod(ix*29+iy*43+(ix^iy)*13+int(seed),8)

    # H4-I10 / owner hard reset 2026-08-30: replace little formula plus signs
    # with distributed Byzantine-cinder cross reliefs. Every secret is built
    # from an outer halo, bevelled arms, inner inlay, knot-ring and rivets;
    # all changes stay entirely in M/R/Cc, never RGB paint.
    cross=np.zeros((hh,ww),np.uint8);inset=np.zeros((hh,ww),np.uint8);halo=np.zeros((hh,ww),np.uint8);rivet=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0xC412);count=max(42,int(hh*ww/14500))
    for n in range(count):
        cx=float(rng.uniform(-22,ww+22));cy=float(rng.uniform(-22,hh+22));rad=float(rng.uniform(17,28));ang=float(rng.uniform(-.38,.38));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
        def pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
        # Four arms with stepped bevels make a material engraving, not a plus.
        outer=[(-rad*.18,-rad*.92),(rad*.18,-rad*.92),(rad*.18,-rad*.24),(rad*.78,-rad*.24),(rad*.78,rad*.18),(rad*.18,rad*.18),(rad*.18,rad*.82),(-rad*.18,rad*.82),(-rad*.18,rad*.18),(-rad*.78,rad*.18),(-rad*.78,-rad*.24),(-rad*.18,-rad*.24)]
        cv2.polylines(cross,[np.array([pt(px,py) for px,py in outer],np.int32)],True,1,th,cv2.LINE_AA)
        for scale,val in ((.68,3),(.42,5)):
            pts=[pt(px*scale,py*scale) for px,py in outer];cv2.polylines(inset,[np.array(pts,np.int32)],True,val,1 if scale<.5 else th,cv2.LINE_AA)
        cv2.ellipse(halo,pt(0,-rad*.03),(int(rad*.88),int(rad*.88)),int(np.degrees(ang)),18,342,255,1,cv2.LINE_AA)
        for k in range(8):
            a=k*np.pi*2/8+.18;cv2.circle(rivet,pt(np.cos(a)*rad*.66,np.sin(a)*rad*.66),max(2,th),255,-1,cv2.LINE_AA)
        for off in (-.09,.09): cv2.line(cross,pt(off*rad,-rad*.66),pt(off*rad,rad*.62),6,1,cv2.LINE_AA)
    secret=(cross>0)|(inset>0)|(halo>0)|(rivet>0)

    # I7 / owner Houdini rebuild: material breadth already passed, but the
    # neutral carrier read too close to black at picker scale (.0917/.0430
    # mean/std).  Lift the fired jade enamel and copper inclusions without
    # placing a cross in RGB; crosses remain M/R/Cc-only below.
    soot=np.array((.018,.040,.030),np.float32); jade=np.array((.040,.205,.155),np.float32)
    viridian=np.array((.070,.360,.270),np.float32); copper=np.array((.54,.270,.105),np.float32)
    pearl=np.array((.50,.760,.620),np.float32)
    paint=soot*(.68+.10*fired[...,None])+jade*(.50+.18*(1-fired[...,None]))
    chip=(viridian*(.45+.34*mosaic_state[...,None])+copper*(.10+.13*(1-mosaic_state[...,None])))
    z=(puddle*.30)[...,None]; paint=paint*(1-z)+chip*z
    z=(rim*.19)[...,None]; paint=paint*(1-z)+pearl*z
    z=(inlay*.34)[...,None]; paint=paint*(1-z)+viridian*z
    z=(damask*.19)[...,None]; paint=paint*(1-z)+jade*z
    z=(oxide*.28)[...,None]; paint=paint*(1-z)+copper*z
    z=(crack*.15)[...,None]; paint=paint*(1-z)+pearl*z
    tone=state.astype(np.float32)/7.; metal=27+44*tone+79*inlay+51*damask+73*oxide+31*crack
    rough=226-41*tone-68*inlay-45*damask-64*oxide-26*crack
    coat=24+48*tone+82*inlay+61*damask+88*oxide+37*crack
    q=np.where(cross>0,cross%8,np.where(inset>0,inset%8,np.where(halo>0,6,np.where(rivet>0,5,np.mod(state+np.floor(micro*7).astype(np.int32)+np.floor((ux+uy)*.23).astype(np.int32),8))))).astype(np.int32)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(251,162,218,178,242,149,200),default=185).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(10,59,48,89,24,77,42),default=70).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(249,142,195,117,225,158,169),default=132).astype(np.float32)
    metal=np.where(secret,sm,metal); rough=np.where(secret,sr,rough); coat=np.where(secret,sc,coat)
    if (hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint); metal,rough,coat=map(up,(metal,rough,coat))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_cinder_cross_i1(paint,shape,mask,seed,pm,bb):
    del bb; authored,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    cov=np.asarray(mask,np.float32); cov=cov[...,0] if cov.ndim==3 else cov
    return np.clip(src*(1-(np.clip(cov,0,1)*float(pm))[...,None])+authored*(np.clip(cov,0,1)*float(pm))[...,None],0,1).astype(np.float32)


def spec_cinder_cross_i1(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _arrays(shape,seed)[1]
