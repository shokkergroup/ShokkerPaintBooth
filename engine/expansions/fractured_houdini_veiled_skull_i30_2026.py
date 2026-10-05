"""H1-I30 — Veiled Skull / obsidian prismatic lattice, pass 1.

SPB-H1 owner reset (2026-08-31).  Independent carrier after I27/I28/I29
rejections.  This uses a dense, authored 10-work-pixel (27px native) prism
lattice with 3-work-pixel (8px native) seams and varied adjacent material
cards. It is not a generic grid recolor: each cell has a deliberate four-way
black, indigo, violet, and cold-chrome response.  Skulls remain M/R/Cc only.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_W=768; _C=OrderedDict(); _L=RLock()
def _frac(x): return x-np.floor(x)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*74.13)*43758.5453)

def _ornate_skull_reliquary(seed):
    """64 complete repeated micro-reliquaries, encoded only in material.

    P10 replaces I29's small scattered glyph source.  Each whole 64–88px
    native skull is composed of 8–32px native crown, sockets, teeth, halo and
    leaf primitives.  The motif stays recurrent across the complete canvas,
    yet becomes an actual engraving under light rather than a pink dot.
    """
    rel=np.zeros((_W,_W),np.uint8); glint=np.zeros_like(rel)
    rng=np.random.default_rng(int(seed)*9311+47)
    for gy in range(8):
        for gx in range(8):
            cx=int((gx+.5+(rng.random()-.5)*.30)*(_W/8)); cy=int((gy+.5+(rng.random()-.5)*.32)*(_W/8))
            sx=int(rng.integers(12,15)); sy=int(sx*1.20); a=float((rng.random()-.5)*22)
            ca,sa=np.cos(np.deg2rad(a)),np.sin(np.deg2rad(a))
            def p(dx,dy): return int(cx+dx*ca-dy*sa),int(cy+dx*sa+dy*ca)
            # Complete crown and chin are separate engraved forms, not a blob.
            cv2.ellipse(rel,p(0,-.16*sy),(sx,sy//2),a,0,360,165,3,cv2.LINE_AA)
            cv2.ellipse(rel,p(0,.29*sy),(max(7,sx-2),max(5,sy//3)),a,8,172,151,3,cv2.LINE_AA)
            # The paired sockets/nose form uses 8–20px-native interior marks.
            for sign in (-1,1):
                cv2.ellipse(rel,p(sign*.31*sx,-.08*sy),(max(3,sx//4),max(3,sy//5)),a,0,360,216,-1,cv2.LINE_AA)
            cv2.fillConvexPoly(rel,np.asarray([p(0,.035*sy),p(-.14*sx,.20*sy),p(.14*sx,.20*sy)],np.int32),188,lineType=cv2.LINE_AA)
            for dx in (-.31*sx,-.10*sx,.10*sx,.31*sx): cv2.line(rel,p(dx,.28*sy),p(dx,.50*sy),139,3,cv2.LINE_AA)
            # Engraved containment: halo, scrolls, then a split leaf frame.
            cv2.ellipse(rel,p(0,.03*sy),(sx+7,sy+8),a,197,343,100,3,cv2.LINE_AA)
            for sign in (-1,1):
                cv2.ellipse(rel,p(sign*1.02*sx,-.27*sy),(max(4,sx//3),max(3,sy//5)),a+sign*37,35,238,111,3,cv2.LINE_AA)
                cv2.ellipse(rel,p(sign*1.15*sx,.25*sy),(max(4,sx//4),max(4,sy//4)),a+sign*31,132,313,104,3,cv2.LINE_AA)
            cv2.ellipse(glint,p(0,-.15*sy),(max(4,sx//2),max(3,sy//3)),a,196,344,255,3,cv2.LINE_AA)
    return cv2.GaussianBlur(rel.astype(np.float32)/255.,(0,0),.46),cv2.GaussianBlur(glint.astype(np.float32)/255.,(0,0),.40)

def _master(seed):
    # P2: P1 had the right micro-cell grammar but was too timid at picker
    # scale.  12 work pixels is the deliberate 32px-native upper bound.
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32); cell=12.0
    # Slight, bounded panel drift prevents wallpaper precision while retaining
    # 8–32px native cell anatomy.  It is a lattice, not a noise substitute.
    warp_x=1.05*np.sin(yy*.025)+.55*np.sin(xx*.012+yy*.017)
    warp_y=.92*np.sin(xx*.023)-.47*np.sin(xx*.014-yy*.016)
    gx=(xx+warp_x)/cell; gy=(yy+warp_y)/cell
    ix=np.floor(gx); iy=np.floor(gy); fx=gx-ix; fy=gy-iy
    h0=_hash(ix,iy,float(seed)); h1=_hash(ix+17,iy-31,float(seed)+3.1)
    tier=np.clip(np.floor(h0*8),0,7).astype(np.int32)
    # P8: P6–P7's literal sub-squares became a pale digital mesh at picker
    # scale. Return to the stronger P5 dark prism facets: their values remain
    # independently authored, while the diagonal join stays an 8px-native
    # primitive rather than a macro tile.
    face=np.where(fx+fy<1,0,1)+np.where(fx>fy,2,0)
    edge=np.minimum(np.minimum(fx,1-fx),np.minimum(fy,1-fy))
    seam=np.clip((.30-edge)/.30,0,1)
    diag=np.clip((.16-np.abs(fx-fy))/.16,0,1)
    # Dark but legible visible carrier: each 27px prism has a controlled
    # value/undertone, with no skull or glyph information in RGB paint.
    palette=np.asarray(((.058,.071,.105),(.073,.108,.174),(.097,.061,.158),(.068,.144,.190),
                        (.124,.106,.190),(.097,.162,.206),(.151,.081,.198),(.079,.112,.151)),np.float32)
    face_gain=np.asarray((.76,.99,.90,1.15),np.float32)[face]
    face_tint=np.asarray(((.012,.014,.022),(.008,.021,.041),(.020,.008,.033),(.010,.030,.045)),np.float32)[face]
    # P9: P8's lattice had only a small repeating deck. Give every parent
    # prism its own controlled black-metal value so adjacent cells can change
    # in motion, without detached grain or confetti geometry.
    cell_gain=.74+.44*h0
    cell_tint=np.stack((.010*(h1-.5),.022*(h0-.5),.035*(h1-.5)),2)
    art=palette[tier]*face_gain[...,None]*cell_gain[...,None]+face_tint+cell_tint
    chrome=np.stack((.29+.20*h1,.38+.24*h1,.52+.29*h1),2)
    # P1: deliberate cold edge facets; a 3-work-pixel seam is the smallest
    # visible primitive allowed by owner doctrine, not a hairline artifact.
    art=art*(1-.52*seam[...,None])+chrome*(.52*seam[...,None])
    art=art*(1-.17*diag[...,None])+np.array((.038,.060,.102),np.float32)*(.17*diag[...,None])
    # P3: P2 had fine anatomy but a flat field.  A slow oblique reflected-light
    # sweep crosses existing prism faces so the black lattice has a composed
    # visual rhythm, rather than randomly bright cell confetti.
    sweep=.5+.5*np.sin(ix*.137+iy*.079+.33*np.sin(ix*.051-iy*.043))
    cool=np.array((.018,.098,.154),np.float32)
    orchid=np.array((.082,.015,.112),np.float32)
    art += cool*((.055+.095*sweep)*(face==3))[...,None]
    art += orchid*((.025+.052*(1-sweep))*(face==2))[...,None]
    # P4: retain the black-metal identity but let the four prism faces survive
    # a 256px picker reduction. This is value separation, not larger geometry.
    art=np.clip(np.power(np.clip(art,0,1),.66)*1.04,0,1)
    # Per-face 12-card M/R/Cc deck; channels use divergent decks so the grid
    # can actually dance under motion rather than merely change brightness.
    states=np.asarray(((15,38,15),(29,68,28),(52,102,43),(81,142,60),
                       (112,177,75),(150,213,100),(226,15,16),(248,41,239),
                       (27,184,43),(68,222,101),(170,22,31),(238,8,10)),np.float32)
    base=states[(tier+face*2)%6]
    m=base[...,0]+36*(face==3)-20*(face==0)+38*seam-17*diag
    r=base[...,1]+55*(face==1)-43*(face==2)-46*seam+27*diag
    c=base[...,2]+48*(face==2)-31*(face==1)+49*seam-22*diag
    spec=np.stack((m,r,c),2)
    # P10's full ornate 8–32px-native anatomy is interleaved with tile states;
    # it remains M/R/Cc only and can never become paint/decal art.
    # P5: make the completed 8–32px-native anatomy recoverable in the MRC
    # proof while preserving a quiet neutral carrier. The reveal is still
    # mixed between three physical cards, never a flat neon stamp.
    skull,glint=_ornate_skull_reliquary(seed); hot=skull>.46; rim=(skull>.11)&~hot
    spec[hot]=.50*spec[hot]+.50*np.array((229,40,215),np.float32)
    spec[rim]=.53*spec[rim]+.47*np.array((31,181,55),np.float32)
    spec[glint>.40]=.48*spec[glint>.40]+.52*np.array((221,13,31),np.float32)
    return art.astype(np.float32),np.clip(spec,0,255).astype(np.uint8)

def _assets(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _L:
        if key in _C: _C.move_to_end(key); return _C[key]
    art,spec=_master(seed)
    if (h,w)!=(_W,_W):
        art=cv2.resize(art,(w,h),interpolation=cv2.INTER_AREA if max(h,w)<_W else cv2.INTER_LINEAR)
        spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    out=(art.astype(np.float32),spec.astype(np.uint8))
    with _L:
        _C[key]=out
        if len(_C)>2: _C.popitem(last=False)
    return out

def paint_veiled_skull_i30(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*pm)[...,None])+art*(np.clip(m,0,1)*pm)[...,None],0,1).astype(np.float32)

def spec_veiled_skull_i30(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
