"""Houdini recovery POC I1 — distributed skull reveals in material space.

This is intentionally UNREGISTERED. It corrects the failed one-centre Houdini
premise: repeated 120–190px skulls occur across the full carrier, but each is
assembled solely from the existing 8–24px enamel cells' M/R/Cc state changes.
Paint is a complete non-symbol graphite-pearl microquilt in neutral light.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)

def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        old=_CACHE.get(key)
        if old is not None:_CACHE.move_to_end(key);return old
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&8191)*.0011
    # I1d: continuous graphite guilloché. Fine 1–4px engraving lines and
    # 8–24px interference pockets produce a premium carrier with neither the
    # old checker cadence nor isolated microflake debris.
    a=x/10.7+.34*np.sin(y/37.+phase)+.19*np.sin((x+y)/61.)
    b=y/13.3-.28*np.sin(x/43.-phase*.7)+.17*np.cos((x-y)/53.)
    c=(x-y)/18.1+.24*np.sin((x+y)/71.+phase)
    l1=np.exp(-np.square(np.sin(a)/.105));l2=np.exp(-np.square(np.sin(b)/.112));l3=np.exp(-np.square(np.sin(c)/.095))
    rim=np.clip(np.maximum(l1,np.maximum(l2,l3)),0,1)
    pocket=.5+.5*np.sin(a+.62*np.sin(b)-.31*np.cos(c))
    cell=np.clip(.30+.42*pocket+.28*rim,0,1)
    gx=np.floor(a/np.pi).astype(np.int32);gy=np.floor(b/np.pi).astype(np.int32)
    state=np.mod(gx*17+gy*31+(gx^gy)*5+int(seed),8)
    # Repeated jittered motif compartments roughly 244px apart. Their skulls
    # are 120–190px, so many fragments land on each car side/hood/rear.
    pitch=244.;tx=np.floor(x/pitch).astype(np.int32);ty=np.floor(y/pitch).astype(np.int32)
    px=_fract(x/pitch);py=_fract(y/pitch)
    h1=_fract(np.sin(tx*127.1+ty*311.7+phase)*43758.5453)
    h2=_fract(np.sin(tx*269.5-ty*183.3+phase*1.7)*21347.2187)
    h3=_fract(np.sin(tx*91.7+ty*57.4+phase*2.3)*11371.1291)
    cx=.32+.36*h1;cy=.36+.24*h2;scale=.47+.22*h3
    X=(px-cx)/scale;Y=(py-cy)/scale
    cranium=(X/.67)**2+((Y+.15)/.68)**2<1.
    jaw=(np.abs(X)<.47)&(Y>.18)&(Y<.66)&((np.abs(X)+.58*(Y-.18))<.48)
    eye_l=((X+.25)/.20)**2+((Y+.05)/.15)**2<1.;eye_r=((X-.25)/.20)**2+((Y+.05)/.15)**2<1.
    nose=(np.abs(X)<.095)&(Y>.12)&(Y<.34)
    teeth=(np.abs(X)<.34)&(Y>.39)&(Y<.54)&(np.mod(np.floor((X+.38)*22),2)==0)
    skull=(cranium|jaw)&~(eye_l|eye_r|nose);skull=skull&(~teeth|(np.abs(X)<.29))
    # Reveal only via carrier cells. A different subset per motif means no
    # literal, solid skull decal appears in the combined material field.
    carve=(np.mod(state*5+gx*7+gy*11+tx*3+ty*9,7)<=3)&(cell>.13)
    secret=(skull&carve).astype(np.float32)
    # I1b: neutral-light carrier lift. The ordinary graphite-pearl quilt must
    # be attractive before a track light ever discovers its spec-only secret.
    graphite=np.array((.042,.054,.091),np.float32);steel=np.array((.17,.23,.36),np.float32)
    pearl=np.array((.40,.48,.66),np.float32);blue=np.array((.15,.32,.56),np.float32)
    tone=(state%4).astype(np.float32)/3.
    paint=graphite*(1-cell[...,None]*.74)+steel*(cell[...,None]*.74)
    paint=paint*(1-rim[...,None]*.38)+pearl*(rim[...,None]*.38)
    paint=paint*(.93+.15*tone[...,None])+blue*(cell[...,None]*.13)
    # Ordinary carrier states; skull parcels exchange their existing cells for
    # fractured hot/cool/chrome/flat combinations only in the spec channels.
    metal=42+32*tone+51*cell+28*rim;rough=205-43*tone-67*cell-32*rim;coat=37+38*tone+71*cell+54*rim
    q=np.mod(state+(tx+2*ty),8)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(244,28,194,80,226,54,168),default=118).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(16,199,68,151,34,181,86),default=121).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(238,49,174,109,211,74,155),default=132).astype(np.float32)
    metal=np.where(secret>0,sm,metal);rough=np.where(secret>0,sr,rough);coat=np.where(secret>0,sc,coat)
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value

def paint_houdini_distributed_skull(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)

def spec_houdini_distributed_skull(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
