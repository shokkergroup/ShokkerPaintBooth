"""H1-I26 — Veiled Skull / midnight lacquer reliquary, pass 1.

Owner reset (2026-08-31): the carrier must be beautiful before the hidden
relief is considered.  This is deliberately not a tile, grid, or a painted
skull: an organic mineral-lacquer field is visible in neutral light and many
small, differently oriented skull *material* reliefs recur only in M/R/Cc.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_relics_2026 as _relics

_W=768; _C=OrderedDict(); _L=RLock()

def _frac(x): return x-np.floor(x)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*74.13)*43758.5453)

def _skull_relief(xx,yy,seed):
    """Fine recurrent engraved skulls, rasterized rather than pixel-solved.

    This retains 81 whole-canvas, irregularly placed reliefs but makes their
    8–32px-native components production-fast at 2048².
    """
    h,w=xx.shape; rel=np.zeros((h,w),np.uint8); glint=np.zeros((h,w),np.uint8)
    rng=np.random.default_rng(int(seed)*9973+41)
    for gy in range(9):
        for gx in range(9):
            cx=int((gx+.5+(rng.random()-.5)*.78)*(w/9.0)); cy=int((gy+.5+(rng.random()-.5)*.78)*(h/9.0))
            sx=int(7+rng.integers(0,5)); sy=int(sx*1.16); angle=float((rng.random()-.5)*46)
            # engraved crown, paired eye sockets, nasal keyhole, jaw and
            # three tooth notches; all stay beneath paint and are not decals.
            cv2.ellipse(rel,(cx,cy-sy//4),(sx,sy//2),angle,188,352,168,1,cv2.LINE_AA)
            cv2.ellipse(rel,(cx,cy+sy//3),(max(2,sx-2),max(2,sy//3)),angle,18,162,174,1,cv2.LINE_AA)
            ca,sa=np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle))
            def pt(dx,dy): return (int(cx+dx*ca-dy*sa),int(cy+dx*sa+dy*ca))
            for dx in (-sx*.33,sx*.33): cv2.ellipse(rel,pt(dx,-sy*.10),(max(2,sx//5),max(2,sy//6)),angle,0,360,224,-1,cv2.LINE_AA)
            tri=np.array([pt(0,0),pt(-sx*.12,sy*.18),pt(sx*.12,sy*.18)],np.int32); cv2.fillConvexPoly(rel,tri,196,lineType=cv2.LINE_AA)
            for dx in (-sx*.28,0,sx*.28): cv2.line(rel,pt(dx,sy*.27),pt(dx,sy*.46),142,1,cv2.LINE_AA)
            # Pass 14: an incomplete ornamental halo and side curls turn the
            # reveal into engraved filigree, not a bare repeated icon.
            cv2.ellipse(rel,pt(0,sy*.03),(sx+3,sy+5),angle,205,335,96,1,cv2.LINE_AA)
            cv2.ellipse(rel,pt(-sx*.73,sy*.05),(max(2,sx//4),max(2,sy//3)),angle,260,88,104,1,cv2.LINE_AA)
            cv2.ellipse(rel,pt(sx*.73,sy*.05),(max(2,sx//4),max(2,sy//3)),angle,92,260,104,1,cv2.LINE_AA)
            # Pass 19: paired filigree leaves make the hidden event a small
            # reliquary engraving. They are material-only 1–3 work-pixel
            # strokes (8–32px native after the surrounding relief), never art.
            for sign in (-1,1):
                cv2.ellipse(rel,pt(sign*sx*.88,-sy*.38),(max(2,sx//3),max(2,sy//5)),angle+sign*32,45,235,112,1,cv2.LINE_AA)
                cv2.ellipse(rel,pt(sign*sx*.96,sy*.26),(max(2,sx//4),max(2,sy//4)),angle+sign*28,132,312,108,1,cv2.LINE_AA)
            cv2.ellipse(glint,pt(0,-sy*.12),(max(2,sx//2),max(2,sy//3)),angle,198,342,255,1,cv2.LINE_AA)
    return cv2.GaussianBlur(rel.astype(np.float32)/255.,(0,0),.55),cv2.GaussianBlur(glint.astype(np.float32)/255.,(0,0),.45)

def _master(seed):
    # Pass 5: discard the repeated alligator substrate. This is authored as
    # flowing black lacquer: non-repeating broad current, with many 8–32px
    # contour lips that are actual material relief rather than grain.
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32); rng=np.random.default_rng(int(seed)+307)
    def soft(n,blur):
        a=rng.normal(0,1,(n,n)).astype(np.float32)
        return cv2.GaussianBlur(cv2.resize(a,(_W,_W),interpolation=cv2.INTER_CUBIC),(0,0),blur)
    n1,n2,n3=soft(19,21.0),soft(31,11.0),soft(47,6.0)
    u=xx+26*np.sin(yy*.019+n1*1.8)+12*n2
    v=yy+31*np.sin(xx*.017+n2*1.5)+10*n1
    current=.73*np.sin(u*.115+np.sin(v*.071+n3)*1.9)+.42*np.sin(v*.168-u*.052+n2*1.2)+.24*n3
    current=(current-current.min())/(np.ptp(current)+1e-6)
    broad=cv2.GaussianBlur(current,(0,0),8.5)
    flow=.68*current+.32*broad
    # Fine painted contour events: 3–10 work pixels (8–27px native) between
    # broad pools; no spatial cell index or repeated wallpaper primitive.
    # Pass 15: preserve 8–32px lips but widen their spacing so the carrier
    # breathes at picker scale instead of becoming a dense wallpaper field.
    phase=np.sin((u*.315+v*.145+n3*3.0)+.58*np.sin(v*.145+n1))
    seam=np.exp(-((np.abs(phase)-.89)/.055)**2)
    ridge=np.clip(np.abs(flow-cv2.GaussianBlur(flow,(0,0),2.8))*7.8+.40*seam,0,1)
    # A mineral-lacquer visible field: dark but not crushed, with deliberate
    # smoky-indigo, plum, steel and pearl edge events—not grain/noise rescue.
    # Pass 7: graphite lacquer, not a bright illustrated oil pattern. Cold
    # violet exists only as a reflected undertone; steel follows fine lips.
    void=np.stack((.016+.025*broad,.015+.022*broad,.020+.027*broad),2)
    indigo=np.stack((.035+.075*flow,.050+.090*flow,.095+.135*flow),2)
    plum=np.stack((.075+.105*flow,.018+.018*flow,.070+.105*flow),2)
    steel=np.stack((.29+.23*flow,.30+.23*flow,.34+.25*flow),2)
    # Pass 13: raise only the wet graphite / pearl-lip visual contrast. This
    # keeps the secret absent from paint while giving the neutral carrier an
    # actual premium material read at picker scale.
    # Pass 16: selected existing lip segments receive pearl, creating a
    # restrained moving highlight rather than detached sparkle/confetti.
    pearl_lip=seam*(.5+.5*np.sin(u*.071-v*.109+n2*1.7))
    moon=np.stack((.075+.10*flow,.16+.17*flow,.34+.28*flow),2)
    # Pass 17: richer smoke-violet undertone, restricted to the existing
    # liquid pools so it reads as lacquer depth rather than color confetti.
    # Pass 18: cold moon-pearl is confined to selected wet lips.
    art=void+indigo*(.66+.27*flow)[...,None]+plum*(np.clip(flow-.45,0,1)*.34)[...,None]+steel*((.57*ridge+.38*seam+.16*pearl_lip)[...,None])+moon*(.11*pearl_lip)[...,None]
    art=np.clip(np.power(np.clip(art,0,1),.78)*.97+np.array((.014,.012,.019),np.float32),0,1)
    # A many-state physical deck. Every base region has coherent local
    # material; sharp state changes are reserved for fine seams and relief.
    t=np.clip(.64*flow+.22*broad+.14*ridge,0,1)
    # Pass 6: the calm lacquer material hierarchy is continuous through its
    # pools. Exact high-contrast states are localized at contour lips and
    # secrets, rather than turning the entire Combined map into an RGB rug.
    deck=np.asarray(((12,35,16),(24,54,23),(40,72,31),(59,90,40),
                     (82,108,51),(108,125,64),(218,12,12),(249,42,250),
                     (31,172,61),(70,202,106),(152,25,28),(236,9,8)),np.uint8)
    smooth=cv2.GaussianBlur(t,(0,0),3.2)
    q=np.clip(np.floor(smooth*5.2),0,5).astype(np.int32)
    # Six exact, close lacquer states carry the quiet body of the finish.
    spec=deck[q]
    edge_state=deck[np.where(ridge>.57,7,np.where(seam>.56,6,q))]
    blend=np.clip(ridge*.32+seam*.38,0,.68)[...,None]
    spec=(spec.astype(np.float32)*(1-blend)+edge_state.astype(np.float32)*blend)
    # Pass 8: broaden the physically useful roughness ladder inside the same
    # coherent pools—no added dots, noise, or substitute geometry.
    spec[...,0]+=31*(flow-.50)+18*seam
    spec[...,1]+=72*(.50-flow)+42*seam
    spec[...,2]+=48*(flow-.50)-31*seam
    # Pass 9: the pre-existing lacquer contour gets a full matte-to-wet
    # roughness sweep. This is pattern-bound response, not a metric-only
    # noise layer, and keeps its turns synchronized with the paint relief.
    rough_sweep=.5+.5*phase
    spec[...,1]+=60*(rough_sweep-.50)
    # Pass 11: clearcoat has its own offset fine-flow response. M/R/Cc now
    # share the lacquer anatomy without being three recolored copies of one
    # scalar field, which is essential for an actual changing material read.
    coat_sweep=.5+.5*np.sin(u*.247-v*.163+1.35*n2+0.55*np.sin(v*.091+n1))
    spec[...,2]+=68*(coat_sweep-.50)
    spec=np.clip(spec,0,255).astype(np.uint8)
    # The secret is a recurrent relief, never an albedo mark. Its high/low
    # physical states are deliberately interleaved with the real carrier deck.
    skull,glint=_skull_relief(xx,yy,seed)
    hot=skull>.38; cool=(skull>.18)&~hot
    spec=spec.astype(np.int16)
    # Pass 12: secret edges receive real named material cards—not a generic
    # brightness nudge. The visible lacquer remains unmarked in RGB paint.
    spec[hot]=(.28*spec[hot]+.72*np.array((248,24,244),np.float32)).astype(np.int16)
    spec[cool]=(.35*spec[cool]+.65*np.array((26,194,42),np.float32)).astype(np.int16)
    spec[glint>.44]=(.22*spec[glint>.44]+.78*np.array((238,7,14),np.float32)).astype(np.int16)
    return art.astype(np.float32),np.clip(spec,0,255).astype(np.uint8)

def _assets(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _L:
        if key in _C: _C.move_to_end(key); return _C[key]
    art,spec=_master(seed)
    if (h,w)!=(_W,_W):
        mode=cv2.INTER_AREA if max(h,w)<_W else cv2.INTER_LINEAR
        art=cv2.resize(art,(w,h),interpolation=mode); spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    out=(art.astype(np.float32),spec.astype(np.uint8))
    with _L:
        _C[key]=out
        if len(_C)>2: _C.popitem(last=False)
    return out

def paint_veiled_skull_i26(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*pm)[...,None])+art*(np.clip(m,0,1)*pm)[...,None],0,1).astype(np.float32)

def spec_veiled_skull_i26(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
