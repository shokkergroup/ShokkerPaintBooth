"""FRACTURED HOUDINI H2-I5 — Ember Cipher / smoked mokume lacquer.

Owner full rebuild, 2026-08-30.  This is intentionally unrelated to H1's
graphite brocade: the neutral carrier is a dense copper/umber mokume-gane
lacquer made from fine forged seams, oxidation halos, mica tears and dark
anneal pools.  Many irregular 116–184px flame revelations live only in M/R/Cc
substitutions, so one car has multiple independent discovery opportunities.
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
    # I5c — render through a 896² authored field, then resolve to the native
    # canvas.  This keeps the seam/halo/mica vocabulary in the intended
    # 8–32px band while bringing a full 2048² material render under budget.
    scale = min(1.0, 896.0 / max(h, w))
    hh, ww = max(96, round(h * scale)), max(96, round(w * scale))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    phase = (int(seed) % 3571) * .0053

    # I7 / owner-eye rejection: I6's tiny squares still read as a brown
    # waffle at card scale.  Replace their visible grammar with irregular
    # forged mokume parcels.  Nearest-site puddles, folded foil rims, anneal
    # arcs, oxide pits and mica tears remain 8–28px native events—never a
    # broad flow lane, a stamped wall, or a random grain rescue.
    ux=(x+1.75*np.sin(y/10.7+phase)+.95*np.cos((x-y)/18.9))/6.45
    uy=(y+1.40*np.cos(x/12.1-.6*phase)+.85*np.sin((x+2*y)/22.7))/6.85
    gx=np.floor(ux).astype(np.int32); gy=np.floor(uy).astype(np.int32)
    fx=np.mod(ux,1.); fy=np.mod(uy,1.)
    near=np.full((hh,ww),99.,np.float32); nxt=np.full((hh,ww),99.,np.float32)
    dx0=np.zeros((hh,ww),np.float32); dy0=np.zeros((hh,ww),np.float32)
    state=np.zeros((hh,ww),np.int32)
    for ox in (-1,0,1):
        for oy in (-1,0,1):
            nx,ny=gx+ox,gy+oy
            jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545)
            jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635)
            dx,dy=ux-(nx+jx),uy-(ny+jy); dsq=dx*dx+dy*dy; take=dsq<near
            nxt=np.where(take,near,np.minimum(nxt,dsq)); near=np.where(take,dsq,near)
            dx0=np.where(take,dx,dx0); dy0=np.where(take,dy,dy0)
            local=np.mod(nx*23+ny*41+(nx^ny)*11+int(seed),8)
            state=np.where(take,local,state)
    dist=np.sqrt(near); seamgap=np.sqrt(nxt)-dist
    puddle=np.clip(1-dist/.89,0,1); rim=np.exp(-np.square((seamgap-.105)/.052))
    anneal=state.astype(np.float32)/7.
    ang=np.arctan2(dy0,dx0)
    curl=.5+.5*np.sin(ang*2.1+dist*20.0+anneal*5.7)
    arc=np.clip((.070-np.abs(dist-(.24+.13*anneal)))*12.0,0,1)*(.35+.65*curl)
    pit=np.clip((.24-dist)*4.2,0,1)*(1-rim*.65)
    forge=np.maximum(rim*.92,np.maximum(arc*.74,pit*.48))
    halo=np.clip(rim*.62+arc*.82+pit*.42,0,1)
    tear=np.clip((anneal-.40)*1.75,0,1)*np.clip((.56-np.abs(dx0*.62-dy0*.49))*2.1,0,1)*(1-.55*forge)
    a=ux; b=uy; c=(ux+.43*uy)/1.36
    # I5b: the first pass hid too much of each flame in fragmented parcels.
    # Retain varied M/R/Cc microstates but let enough of each local flame read
    # when a grazing light catches it.
    parcel = np.mod(gx * 13 + gy * 5 + np.floor(c * 1.7).astype(np.int32) * 7, 10) <= 8

    # H2-I9 / owner hard reset 2026-08-30: remove the tiny formula flames.
    # Ember Cipher is now a distributed set of jewelled forge-sigils: nested
    # six-sided seal rings, radial ticks, internal rune strokes and ember
    # beads, all material-only and built from 8–28px linework.
    seal=np.zeros((hh,ww),np.uint8);rune=np.zeros((hh,ww),np.uint8);bead=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0xE2B9);count=max(43,int(hh*ww/14500))
    for n in range(count):
        cx=float(rng.uniform(-22,ww+22));cy=float(rng.uniform(-22,hh+22));rad=float(rng.uniform(17,28));ang=float(rng.uniform(-.46,.46));th=int(rng.integers(2,4))
        def pt(px,py): return tuple(np.rint((cx+np.cos(ang)*px-np.sin(ang)*py,cy+np.sin(ang)*px+np.cos(ang)*py)).astype(np.int32))
        outer=[pt(np.cos(ang0)*rad,np.sin(ang0)*rad) for ang0 in np.linspace(0,2*np.pi,7)[:-1]]
        inner=[pt(np.cos(ang0)*rad*.57,np.sin(ang0)*rad*.57) for ang0 in np.linspace(.18,2*np.pi+.18,7)[:-1]]
        cv2.polylines(seal,[np.array(outer,np.int32)],True,1,th,cv2.LINE_AA);cv2.polylines(seal,[np.array(inner,np.int32)],True,3,1,cv2.LINE_AA)
        for k in range(12):
            a=k*np.pi*2/12;cv2.line(seal,pt(np.cos(a)*rad*.72,np.sin(a)*rad*.72),pt(np.cos(a)*rad*.94,np.sin(a)*rad*.94),(k%6)+1,1,cv2.LINE_AA)
        for j in range(3):
            a=ang+(j-1)*.86+rng.uniform(-.20,.20);stem=[(np.cos(a)*rad*.34,np.sin(a)*rad*.34),(np.cos(a+.35)*rad*.10,np.sin(a+.35)*rad*.10),(np.cos(a-.30)*rad*.46,np.sin(a-.30)*rad*.46)]
            cv2.polylines(rune,[np.array([pt(px,py) for px,py in stem],np.int32)],False,(j*2+2)%7+1,th,cv2.LINE_AA)
        for k in range(6):
            a=k*np.pi*2/6+.22;cv2.circle(bead,pt(np.cos(a)*rad*.76,np.sin(a)*rad*.76),max(2,th),255,-1,cv2.LINE_AA)
    secret=(seal>0)|(rune>0)|(bead>0)

    # I7b: retain the irregular forged topology, but give neutral catalog
    # light enough copper/ember depth to read as a finished lacquer rather
    # than near-black brown.  Hidden flames remain material-only.
    coal = np.array((.075, .030, .018), np.float32)
    umber = np.array((.285, .105, .040), np.float32)
    copper = np.array((.620, .235, .075), np.float32)
    old_gold = np.array((.800, .420, .135), np.float32)
    mica = np.array((.900, .620, .300), np.float32)
    paint = coal * (.74 + .14 * anneal[..., None]) + umber * (.40 + .13 * (1 - anneal[..., None]))
    z = (forge * .41)[..., None]; paint = paint * (1 - z) + copper * z
    z = (halo * .28)[..., None]; paint = paint * (1 - z) + old_gold * z
    z = (tear * .20)[..., None]; paint = paint * (1 - z) + mica * z

    tone = state.astype(np.float32) / 7.0
    metal = 31 + 42 * tone + 76 * forge + 51 * halo + 69 * tear
    rough = 224 - 45 * tone - 67 * forge - 44 * halo - 61 * tear
    coat = 27 + 47 * tone + 81 * forge + 58 * halo + 86 * tear
    # A deliberately broad fractured heat-state ladder. It is placed only
    # inside hidden flames and remains physically tied to the local lacquer.
    q = np.where(seal>0,seal%8,np.where(rune>0,rune%8,np.where(bead>0,5,np.mod(state + np.floor(a * .43).astype(np.int32) + np.floor(c * .52).astype(np.int32),8)))).astype(np.int32)
    # I5e: all eight secret states remain materially different, but none are
    # a dead matte value that deletes the outer flame at grazing angle.
    sm = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (252, 154, 214, 173, 237, 148, 197), default=181).astype(np.float32)
    sr = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (11, 62, 53, 92, 27, 78, 44), default=71).astype(np.float32)
    sc = np.select((q == 0, q == 1, q == 2, q == 3, q == 4, q == 5, q == 6),
                   (247, 143, 189, 121, 222, 159, 165), default=133).astype(np.float32)
    metal = np.where(secret, sm, metal)
    rough = np.where(secret, sr, rough)
    coat = np.where(secret, sc, coat)
    if (hh, ww) != (h, w):
        up = lambda z: cv2.resize(z.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        paint = up(paint)
        metal, rough, coat = map(up, (metal, rough, coat))
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(metal, 0, 255), np.clip(rough, 15, 255), np.clip(coat, 16, 255)), 2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_ember_cipher_i5(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5:
        src = src / 255.0
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_ember_cipher_i5(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec
