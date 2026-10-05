"""FRACTURED HOUDINI H1-I3 — Veiled Skull / mercurial brocade.

Owner Houdini rebuild, 2026-08-30.  The first family failed because a single
large secret did not land on enough car panels, while the distributed I1d POC
looked like a grid and revealed its mechanism in the catalog.  I3 uses an
irregular field of many 112–164px skull reveal regions.  The visible carrier
is complete graphite-blue guilloché brocade; skull geometry exists only as
mixed M/R/Cc substitutions inside that pre-existing fine structure.
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
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

    scale = min(1.0, 1024.0 / max(h, w))
    hh, ww = max(96, round(h * scale)), max(96, round(w * scale))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    phase = float(int(seed) % 4093) * .0041
    # I4: no long guilloché lanes.  The visible carrier is a dense 8–28px
    # micro-brocade of warped cells, short rims, inset pearls and charcoal
    # stitch dashes.  It must stay coherent at picker scale without turning
    # into macro wallpaper across a whole 2048² car sheet.
    u = x + 1.35*np.sin(y/10.7+phase) + .85*np.sin((x-y)/16.9)
    v = y + 1.20*np.cos(x/11.3-.6*phase) + .70*np.sin((2*x+y)/19.7)
    gx = np.floor(u/5.6).astype(np.int32); gy = np.floor(v/6.3).astype(np.int32)
    fx = np.mod(u/5.6,1.0); fy = np.mod(v/6.3,1.0)
    edge = np.minimum(np.minimum(fx,1-fx),np.minimum(fy,1-fy))
    engraved = np.clip((.105-edge)*9.5,0,1)
    rr = np.sqrt((fx-.5)**2+(fy-.5)**2)
    pearl_pocket = np.clip((.34-rr)*4.2,0,1)*(1-.45*engraved)
    satin_lip = np.clip((.115-np.abs(rr-.31))*8.7,0,1)*(1-.35*engraved)
    dash = ((np.abs(fx-.5)<.075)&(np.abs(fy-.5)<.31)&(np.mod(gx*13+gy*29,5)==0)).astype(np.float32)
    engraved = np.maximum(engraved,dash*.82)
    a=u/5.6; b=v/6.3; c=(u-.57*v)/7.9
    tide=np.mod(gx*23+gy*41+(gx^gy)*11+int(seed),8).astype(np.float32)/7.
    state=np.mod(gx*19+gy*37+(gx^gy)*7+int(seed),8)
    parcel=(np.mod(gx*7+gy*11+(gx^gy)*5,9)<=6)

    # H1-I9 / owner hard reset 2026-08-30: formula cells yielded sparse tiny
    # symbols.  Build full anatomical skull reliefs explicitly, but only in
    # M/R/Cc: carved cranium, orbital cavities, nasal channel, cheek arches,
    # jaw, teeth and a fine engraved halo.  Irregular placement covers every
    # whole-car canvas without a visible tile cadence or RGB/decal pixels.
    motif=np.zeros((hh,ww),np.uint8);cavity=np.zeros((hh,ww),np.uint8);teeth=np.zeros((hh,ww),np.uint8);halo=np.zeros((hh,ww),np.uint8)
    rng=np.random.default_rng(int(seed)^0x5C011);count=max(32,int(hh*ww/28500))
    for n in range(count):
        cx=float(rng.uniform(-26,ww+26));cy=float(rng.uniform(-34,hh+34));rx=float(rng.uniform(27,42));ry=float(rng.uniform(35,52));ang=float(rng.uniform(-.34,.34));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
        def pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
        # Crown, temple and cheek anatomy are multi-state contour engravings.
        cv2.ellipse(motif,pt(0,-ry*.13),(int(rx*.78),int(ry*.72)),int(np.degrees(ang)),192,348,1,th,cv2.LINE_AA)
        for side,val in ((-1,2),(1,3)):
            cv2.ellipse(cavity,pt(side*rx*.31,-ry*.04),(max(6,int(rx*.25)),max(5,int(ry*.18))),int(np.degrees(ang))+side*8,0,360,255,-1,cv2.LINE_AA)
            cv2.ellipse(motif,pt(side*rx*.31,-ry*.04),(max(7,int(rx*.29)),max(6,int(ry*.22))),int(np.degrees(ang))+side*8,18,342,val,1,cv2.LINE_AA)
            cheek=[(side*rx*.58,ry*.02),(side*rx*.70,ry*.30),(side*rx*.39,ry*.56),(side*rx*.16,ry*.46)]
            cv2.polylines(motif,[np.array([pt(px,py) for px,py in cheek],np.int32)],False,val+2,th,cv2.LINE_AA)
        nose=np.array([pt(0,ry*.12),pt(-rx*.10,ry*.34),pt(rx*.10,ry*.34)],np.int32);cv2.fillConvexPoly(cavity,nose,255,lineType=cv2.LINE_AA);cv2.polylines(motif,[nose],True,4,1,cv2.LINE_AA)
        jaw=[(-rx*.42,ry*.45),(-rx*.34,ry*.72),(0,ry*.82),(rx*.34,ry*.72),(rx*.42,ry*.45)]
        cv2.polylines(motif,[np.array([pt(px,py) for px,py in jaw],np.int32)],False,5,th,cv2.LINE_AA)
        for k in range(-3,4):
            xk=k*rx*.095;cv2.line(teeth,pt(xk,ry*.51),pt(xk,ry*.70),255,max(1,th-1),cv2.LINE_AA)
        # Small engraved halo sections make the secret ornate rather than a
        # flat Halloween icon; each is still an 8-24px native material mark.
        cv2.ellipse(halo,pt(0,-ry*.05),(int(rx*1.10),int(ry*.94)),int(np.degrees(ang)),205,335,255,1,cv2.LINE_AA)
        for k in range(7):
            a=np.pi*(1.15+k*.10);px,py=np.cos(a)*rx*1.02,np.sin(a)*ry*.88;cv2.circle(halo,pt(px,py),max(2,th),255,-1,cv2.LINE_AA)
    secret=(motif>0)|(cavity>0)|(teeth>0)|(halo>0)

    # I6: staged card audit found the neutral brocade underlit.  Lift only
    # graphite-blue lacquer / pearl pockets / steel stitching, never skull RGB.
    graphite = np.array((.050, .070, .115), np.float32)
    midnight = np.array((.090, .140, .235), np.float32)
    pearl = np.array((.55, .66, .82), np.float32)
    blue_steel = np.array((.20, .40, .72), np.float32)
    paint = graphite * (.76 + .13 * tide[..., None]) + midnight * (.14 + .11 * (1 - tide[..., None]))
    z = (engraved * .43)[..., None]; paint = paint * (1 - z) + blue_steel * z
    z = (pearl_pocket * .31)[..., None]; paint = paint * (1 - z) + pearl * z
    z = (satin_lip * .18)[..., None]; paint = paint * (1 - z) + midnight * z

    tone = state.astype(np.float32) / 7.0
    # I7: direct audit found I6 M/R too narrow.  Broaden each local brocade
    # state across M/R/Cc while preserving the fine parcel-bound structure.
    metal = 18 + 88 * tone + 79 * engraved + 63 * pearl_pocket + 44 * satin_lip
    rough = 244 - 108 * tone - 70 * engraved - 62 * pearl_pocket - 38 * satin_lip
    coat = 20 + 103 * (1 - tone) + 88 * engraved + 82 * pearl_pocket + 51 * satin_lip
    # Fractured state ladder: hot/cool chrome, satin, metallic flake, and flat
    # live side-by-side only where a hidden skull crosses carrier parcels.
    q = np.where(motif>0,motif%8,np.where(cavity>0,0,np.where(teeth>0,5,np.where(halo>0,6,np.mod(state + np.floor(a * .61).astype(np.int32) + np.floor(b * .37).astype(np.int32),8))))).astype(np.int32)
    sm = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (246, 31, 204, 86, 229, 54, 171), default=121).astype(np.float32)
    sr = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (14, 202, 61, 154, 31, 181, 83), default=123).astype(np.float32)
    sc = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (240, 48, 181, 105, 215, 71, 158), default=129).astype(np.float32)
    metal = np.where(secret, sm, metal)
    rough = np.where(secret, sr, rough)
    coat = np.where(secret, sc, coat)
    if (hh, ww) != (h, w):
        up = lambda z: cv2.resize(z.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        paint = up(paint)
        metal, rough, coat = map(up, (metal, rough, coat))
    value = (
        np.clip(paint, 0, 1).astype(np.float32),
        np.stack((np.clip(metal, 0, 255), np.clip(rough, 15, 255), np.clip(coat, 16, 255)), 2).astype(np.uint8),
    )
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_veiled_skull_i3(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5:
        src = src / 255.0
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_veiled_skull_i3(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec
