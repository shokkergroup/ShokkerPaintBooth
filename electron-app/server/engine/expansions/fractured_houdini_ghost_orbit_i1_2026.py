"""FRACTURED HOUDINI H3-I1 — Ghost Orbit / midnight pearl enamel.

The visible paint is a complete blue-black pearlescent enamel composed of fine
aurora ribs, lacquer eddies, mica pinwork and hairline kintsugi.  Its secret is
not paint: nineteen individually turned galaxy-orbit fragments alter only
metallic, roughness and clearcoat, so a grazing light can assemble spirals that
are absent from the ordinary carrier.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _fract(a):
    return a - np.floor(a)


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1])
    key = (h, w, int(seed))
    with _LOCK:
        got = _CACHE.get(key)
        if got is not None:
            _CACHE.move_to_end(key)
            return got
    # 896² authored field: detail resolves to 8–32px on a 2048² car canvas.
    scale = min(1.0, 896.0 / max(h, w))
    hh, ww = max(96, round(h * scale)), max(96, round(w * scale))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    phase = (int(seed) % 2539) * .0067

    # Continuous midnight pearl enamel, not a dark empty ground: 1–4px ribs,
    # 5–18px aurora contour, 8–26px mica puddle/chip events, all phase-shifted.
    a = (x + 5.3*np.sin(y/23 + phase) + 2.7*np.cos((x+y)/39)) / 5.1
    b = (y - 4.8*np.sin(x/31 - .4*phase) + 2.3*np.sin((2*x-y)/53)) / 7.0
    c = (x*.61 - y*.37 + 4.1*np.cos((x-2*y)/61 + phase)) / 11.7
    rib_a = np.exp(-np.square(np.sin(a)/.105))
    rib_b = np.exp(-np.square(np.sin(b)/.125))
    ribbon = np.maximum(rib_a, rib_b)
    # I2: the first pass exposed too much single-direction ribbon.  A third,
    # drifting lacquer filament creates an enamel gyre rather than wallpaper.
    cross = np.exp(-np.square(np.sin(c)/.115))
    carrier = np.maximum(ribbon, .74*cross)
    aurora = np.exp(-np.square(np.sin(.59*a-.47*b+c)/.20))
    tide = .5 + .5*np.sin(.76*a+.38*b-.31*c)
    pool = .5 + .5*np.sin(.23*a+.41*b-.18*c + .54*np.sin(.37*a-.29*b))
    mica = np.clip((tide-.70)/.30,0,1)*(1-.62*carrier)
    hair = np.exp(-np.square(np.sin(.27*a+.68*b-.42*c)/.075))*(1-.55*carrier)

    gx = np.floor((a-.21*c)/1.47).astype(np.int32)
    gy = np.floor((b+.29*c)/1.61).astype(np.int32)
    state = np.mod(gx*31 + gy*17 + (gx^gy)*9 + int(seed), 8)
    # I4: replace the weak ribbon-only visible surface with a dense midnight
    # cloisonné enamel.  The 11–18px native scales interlock continuously;
    # color is a restrained blue/violet pearl family, never loose confetti.
    hr = np.floor(y / 5.9).astype(np.int32)
    hc = np.floor(x / 6.5 - .5 * np.mod(hr, 2)).astype(np.int32)
    hx = x / 6.5 - .5 * np.mod(hr, 2) - hc - .5
    hy = y / 5.9 - hr - .5
    hdist = np.sqrt(hx*hx + hy*hy)
    cell = np.clip(1.0 - hdist / .70, 0, 1)
    cellrim = np.exp(-np.square((hdist-.43)/.075))
    cellstate = np.mod(hc*19 + hr*37 + (hc^hr)*7 + int(seed), 8).astype(np.float32)/7.0

    # I5: retire the old long-ribbon coordinates entirely.  Keep an irregular
    # pearl microcell enamel—rims, crescents, pits, and short diagonal strokes
    # only—so this cannot read as large flowing blue wallpaper on a car.
    microedge=np.clip((.10-np.minimum(np.minimum(np.mod(x/6.5,1),1-np.mod(x/6.5,1)),np.minimum(np.mod(y/5.9,1),1-np.mod(y/5.9,1))))*9.0,0,1)
    microarc=np.clip((.11-np.abs(hdist-.30))*9.0,0,1)
    micropit=np.clip((.23-hdist)*4.4,0,1)
    microdash=((np.abs(hx)<.075)&(np.abs(hy)<.30)&(np.mod(hc*23+hr*17,5)==0)).astype(np.float32)
    carrier=np.maximum(microedge,np.maximum(microarc*.76,microdash*.86))
    aurora=np.maximum(cellrim*.68,micropit*.54)
    tide=cellstate; pool=np.mod(hc*29+hr*43+(hc^hr)*11+int(seed),8).astype(np.float32)/7.
    mica=np.clip((pool-.55)*2.0,0,1)*(1-.48*carrier)
    hair=microarc*(np.mod(hc*7+hr*13,4)==0)

    # H3-I7 / owner hard reset 2026-08-30: formula spirals were sparse dots.
    # Build many irregular galaxy engravings explicitly: three fine orbit arms,
    # inner lens rings, companion moons and peripheral pearl ticks.  They alter
    # only M/R/Cc; midnight RGB enamel remains an innocent whole-car carrier.
    orbit=np.zeros((hh,ww),np.uint8);core=np.zeros((hh,ww),np.uint8);satellite=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0xC053);count=max(38,int(hh*ww/15000))
    for n in range(count):
        cx=float(rng.uniform(-24,ww+24));cy=float(rng.uniform(-24,hh+24));rad=float(rng.uniform(17,29));ang=float(rng.uniform(-.55,.55));ca,sa=np.cos(ang),np.sin(ang);phase=float(rng.uniform(0,6.283));th=int(rng.integers(2,4))
        def pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
        theta=np.linspace(.08,3.72*np.pi,110)
        for arm,val in ((0,1),(1,3),(2,5)):
            rr=rad*(.07+.072*theta+.016*np.sin(theta*2.7+phase+arm));pts=[pt(np.cos(t+phase+arm*2.094)*r,np.sin(t+phase+arm*2.094)*r*.82) for t,r in zip(theta,rr)]
            cv2.polylines(orbit,[np.array(pts,np.int32)],False,val,th if arm==0 else 1,cv2.LINE_AA)
        for frac,val in ((.16,255),(.28,255),(.43,255)):
            cv2.ellipse(core,pt(0,0),(max(2,int(rad*frac)),max(2,int(rad*frac*.78))),int(np.degrees(ang)),0,360,val,1 if frac<.3 else th,cv2.LINE_AA)
        for k in range(5):
            a=phase+k*np.pi*2/5+.22;cv2.circle(satellite,pt(np.cos(a)*rad*.92,np.sin(a)*rad*.74),max(2,th),255,-1,cv2.LINE_AA)
    secret=(orbit>0)|(core>0)|(satellite>0)

    ink = np.array((.009,.016,.054),np.float32)
    blue = np.array((.032,.082,.225),np.float32)
    cobalt = np.array((.075,.145,.405),np.float32)
    violet = np.array((.135,.070,.325),np.float32)
    pearl = np.array((.34,.43,.72),np.float32)
    # I3: establish a real pearlescent enamel body before the fine line work;
    # I2 was technically dense but read too much like quiet blue wallpaper.
    paint = ink*(.38+.09*tide[...,None]) + blue*(.47+.10*(1-tide[...,None])) + cobalt*(.16*pool[...,None])
    enamel = (cobalt*(.55+.30*cellstate[...,None]) + violet*(.14+.16*(1-cellstate[...,None])))
    z=(cell*.31)[...,None]; paint=paint*(1-z)+enamel*z
    z=(cellrim*.24)[...,None]; paint=paint*(1-z)+pearl*z
    z=(carrier*.15)[...,None]; paint=paint*(1-z)+cobalt*z
    z=(aurora*.14)[...,None]; paint=paint*(1-z)+violet*z
    z=((mica*.19+hair*.08))[...,None]; paint=paint*(1-z)+pearl*z

    tone=state.astype(np.float32)/7.0
    metal=29+45*tone+68*carrier+56*aurora+72*mica+35*hair
    rough=224-43*tone-62*carrier-51*aurora-70*mica-29*hair
    coat=25+49*tone+77*carrier+64*aurora+91*mica+39*hair
    q=np.where(orbit>0,orbit%8,np.where(core>0,0,np.where(satellite>0,6,np.mod(state+np.floor(a*.39).astype(np.int32)+np.floor(b*.51).astype(np.int32),8)))).astype(np.int32)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(250,166,222,181,239,151,203),default=187).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,58,47,88,25,76,41),default=69).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,139,193,118,226,157,170),default=131).astype(np.float32)
    metal=np.where(secret,sm,metal); rough=np.where(secret,sr,rough); coat=np.where(secret,sc,coat)
    if (hh,ww)!=(h,w):
        up=lambda z: cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint); metal,rough,coat=map(up,(metal,rough,coat))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2: _CACHE.popitem(last=False)
    return value


def paint_ghost_orbit_i1(paint, shape, mask, seed, pm, bb):
    del bb
    authored,_=_arrays(shape,seed)
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_ghost_orbit_i1(shape, seed, sm, base_m, base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
