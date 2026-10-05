"""FRACTURED HOUDINI H5-I1 — Ouroboros / smoked rose lacquer tesserae."""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
def _fract(a): return a-np.floor(a)

def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE: _CACHE.move_to_end(key); return _CACHE[key]
    scale=min(1.,864./max(h,w)); hh,ww=max(96,round(h*scale)),max(96,round(w*scale))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32); phase=(int(seed)%2741)*.0061
    # I7 (owner 2026-08-30): I6 removed the macro rings but still read as a
    # uniform tiled field.  Use irregular nearest-site lacquer parcels instead:
    # 8–28px rose pools, fractured foil rims, char pockets, scratchlets and
    # pearl points have no repeated station grid or whole-canvas wave lane.
    ux,uy=x/6.1,y/6.7; gx=np.floor(ux).astype(np.int32); gy=np.floor(uy).astype(np.int32)
    near=np.full((hh,ww),99.,np.float32); next_near=np.full((hh,ww),99.,np.float32); dx0=np.zeros((hh,ww),np.float32); dy0=np.zeros((hh,ww),np.float32)
    for ox in (-1,0,1):
        for oy in (-1,0,1):
            nx,ny=gx+ox,gy+oy
            jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545); jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635)
            dx,dy=ux-(nx+jx),uy-(ny+jy); dsq=dx*dx+dy*dy; take=dsq<near
            next_near=np.where(take,near,np.minimum(next_near,dsq)); near=np.where(take,dsq,near); dx0=np.where(take,dx,dx0); dy0=np.where(take,dy,dy0)
    dist=np.sqrt(near); seamgap=np.sqrt(next_near)-dist; puddle=np.clip(1-dist/.88,0,1); rim=np.exp(-np.square((seamgap-.105)/.055))
    state=np.mod(gx*37+gy*21+(gx^gy)*11+int(seed),8); micro=state.astype(np.float32)/7.; fx=np.mod(ux,1.0); fy=np.mod(uy,1.0)
    foil=np.clip(rim*.90+np.clip((puddle-.74)*3.1,0,1)*.28,0,1)*(.52+.48*micro)
    bloom=np.clip((puddle-.32)*1.5,0,1)*(.25+.75*np.mod(gx*17+gy*31+int(seed),5)/4.)
    ember=.12+.88*micro
    pearl=np.clip((bloom-.42)*2.0,0,1)*(1-.60*foil)
    scratch=np.clip((.055-np.abs(dx0*.69+dy0*.41-(micro-.5)*.19))*15.,0,1)*(.30+.70*micro)*(1-.55*foil)

    # H5-I12 / owner hard reset: ornate material-only ouroboros reliefs.
    coil=np.zeros((hh,ww),np.uint8);scale_mark=np.zeros((hh,ww),np.uint8);head=np.zeros((hh,ww),np.uint8);eye=np.zeros((hh,ww),np.uint8);tail=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0x0B0E);count=max(38,int(hh*ww/14500))
    for n in range(count):
        cx=float(rng.uniform(-24,ww+24));cy=float(rng.uniform(-24,hh+24));rx=float(rng.uniform(18,29));ry=float(rng.uniform(16,26));ang=float(rng.uniform(-.48,.48));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
        def pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
        cv2.ellipse(coil,pt(0,0),(int(rx),int(ry)),int(np.degrees(ang)),24,328,1,th,cv2.LINE_AA);cv2.ellipse(coil,pt(0,0),(int(rx*.76),int(ry*.76)),int(np.degrees(ang)),36,316,3,1,cv2.LINE_AA)
        for k in range(15):
            aa=np.deg2rad(35+k*19);px,py=np.cos(aa)*rx*.88,np.sin(aa)*ry*.88;cv2.ellipse(scale_mark,pt(px,py),(max(2,th+1),max(2,th)),int(np.degrees(aa+ang)),0,360,(k%6)+1,1,cv2.LINE_AA)
        hx,hy=np.cos(np.deg2rad(12))*rx,np.sin(np.deg2rad(12))*ry;head_poly=[(hx,hy),(hx+rx*.22,hy-ry*.12),(hx+rx*.29,hy+ry*.06),(hx+rx*.10,hy+ry*.23),(hx-rx*.08,hy+ry*.10)]
        cv2.polylines(head,[np.array([pt(px,py) for px,py in head_poly],np.int32)],True,255,th,cv2.LINE_AA);cv2.circle(eye,pt(hx+rx*.13,hy),max(2,th),255,-1,cv2.LINE_AA)
        tx,ty=np.cos(np.deg2rad(338))*rx,np.sin(np.deg2rad(338))*ry;cv2.polylines(tail,[np.array([pt(tx,ty),pt(tx-rx*.22,ty+ry*.08),pt(tx-rx*.37,ty-rx*.04)],np.int32)],False,255,th,cv2.LINE_AA)
    secret=(coil>0)|(scale_mark>0)|(head>0)|(eye>0)|(tail>0);head_event=head>0;tail_event=tail>0

    # I8 / owner Houdini rebuild: the I7 fractured-lacquer geometry was right,
    # but the neutral whole-car carrier remained too underlit (.0848/.0585).
    # Enrich rose, gold and frost lacquer states only; the serpent stays in the
    # M/R/Cc `secret` replacement below, never as visible RGB artwork.
    coal=np.array((.040,.015,.030),np.float32); wine=np.array((.290,.050,.110),np.float32); rose=np.array((.660,.150,.310),np.float32); gold=np.array((.760,.400,.170),np.float32); frost=np.array((.750,.550,.660),np.float32)
    paint=coal*(.66+.12*ember[...,None])+wine*(.52+.17*(1-ember[...,None]))
    z=(foil*.35)[...,None]; paint=paint*(1-z)+rose*z; z=(bloom*.21)[...,None]; paint=paint*(1-z)+gold*z; z=(pearl*.24+scratch*.12)[...,None]; paint=paint*(1-z)+frost*z
    tone=state.astype(np.float32)/7.; metal=28+46*tone+74*foil+55*bloom+78*pearl+32*scratch; rough=225-42*tone-66*foil-49*bloom-69*pearl-28*scratch; coat=24+50*tone+81*foil+65*bloom+90*pearl+38*scratch
    q=np.where(coil>0,coil%8,np.where(scale_mark>0,scale_mark%8,np.where(head>0,0,np.where(eye>0,5,np.where(tail>0,6,np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor(micro*7).astype(np.int32),8)))))).astype(np.int32)
    # I2: retain eight independent heat states, but lift every state above a
    # dead matte floor so the linked serpent ring survives a grazing sweep.
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(252,164,220,176,240,150,201),default=186).astype(np.float32); sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(10,60,49,90,25,79,43),default=70).astype(np.float32); sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(249,141,196,119,224,158,170),default=132).astype(np.float32)
    metal=np.where(secret,sm,metal); rough=np.where(secret,sr,rough); coat=np.where(secret,sc,coat)
    # I10: circles alone did not read as serpents in the grazing diagnostic.
    # Give only the already-material-only head/snout and tapered tail their
    # own physically distinct states; nothing changes in the RGB lacquer.
    metal=np.where(head_event,252,metal); rough=np.where(head_event,12,rough); coat=np.where(head_event,249,coat)
    metal=np.where(tail_event,164,metal); rough=np.where(tail_event,86,rough); coat=np.where(tail_event,151,coat)
    if (hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR); paint=up(paint); metal,rough,coat=map(up,(metal,rough,coat))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value

def paint_ouroboros_i1(paint,shape,mask,seed,pm,bb):
    del bb; authored,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    cov=np.asarray(mask,np.float32); cov=cov[...,0] if cov.ndim==3 else cov; mix=(np.clip(cov,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)
def spec_ouroboros_i1(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _arrays(shape,seed)[1]
