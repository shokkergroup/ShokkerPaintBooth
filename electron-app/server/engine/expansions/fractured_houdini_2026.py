"""FRACTURED HOUDINI — lighting-dependent hidden-material finishes.

This starts the owner-authorized twenty-card Houdini family. The development
catalog is live so the owner can inspect real-car behavior. A card's final
keep/rebuild decision still requires neutral, combined-map, and moving-light
evidence; no ordinary visible art is substituted for a material-only reveal.

H1 / Veiled Skull: the visible carrier is midnight mineral lacquer: connected
smoky-indigo, plum and steel process fields with fine seam relief. The skull
is absent from paint. It is assembled solely by locally changing deliberately
interleaved M/R/Cc material states inside many small, irregularly placed
engraved reliefs. In ordinary light the lacquer dominates; under grazing light
the material-state silhouette can reveal itself then vanish.
"""
from __future__ import annotations

import numpy as np
from engine.expansions import fractured_houdini_veiled_skull_i33_2026 as _h1_i20
from engine.expansions import fractured_houdini_ember_cipher_i5_2026 as _h2_i5
from engine.expansions import fractured_houdini_ghost_orbit_i1_2026 as _h3_i4
from engine.expansions import fractured_houdini_cinder_cross_i1_2026 as _h4_i4
from engine.expansions import fractured_houdini_ouroboros_i1_2026 as _h5_i4
from engine.expansions import fractured_houdini_storm_glyph_i1_2026 as _h7_i4
from engine.expansions import fractured_houdini_seraph_eye_i1_2026 as _h8_i2
from engine.expansions import fractured_houdini_verdigris_star_i1_2026 as _h9_i2
from engine.expansions import fractured_houdini_frost_crescent_i1_2026 as _h10_i1
from engine.expansions import fractured_houdini_gilded_crown_i1_2026 as _h11_i1
from engine.expansions import fractured_houdini_glacier_eye_i2_2026 as _h12_i2
from engine.expansions import fractured_houdini_phantom_comet_i1_2026 as _h13_i1
from engine.expansions import fractured_houdini_verdigris_ankh_i1_2026 as _h14_i1
from engine.expansions import fractured_houdini_porcelain_cipher_i1_2026 as _h15_i1
from engine.expansions import fractured_houdini_mirage_compass_i1_2026 as _h16_i1
from engine.expansions import fractured_houdini_quicksilver_helix_i1_2026 as _h17_i1
from engine.expansions import fractured_houdini_chroma_pyre_i1_2026 as _h18_i1
from engine.expansions import fractured_houdini_tidal_relic_i1_2026 as _h19_i1
from engine.expansions import fractured_houdini_lapis_scarab_i1_2026 as _h20_i1
from engine.expansions import fractured_houdini_prism_moth_i5_2026 as _h6_i5


GROUP = "🎩 FRACTURED HOUDINI"
H1_ID = "houdini_veiled_skull"
H2_ID = "houdini_ember_cipher"
H3_ID = "houdini_ghost_spiral"
H4_ID = "houdini_cinder_cross"
H5_ID = "houdini_ouroboros"
H6_ID = "houdini_prism_moth"
H7_ID = "houdini_eclipse_veil"
H8_ID = "houdini_aurora_wolf"
H9_ID = "houdini_velvet_dagger"
H10_ID = "houdini_marble_rose"
H11_ID = "houdini_gilded_crown"
H12_ID = "houdini_glacier_eye"
H13_ID = "houdini_phantom_comet"
H14_ID = "houdini_verdigris_ankh"
H15_ID = "houdini_porcelain_cipher"
H16_ID = "houdini_mirage_compass"
H17_ID = "houdini_quicksilver_helix"
H18_ID = "houdini_chroma_pyre"
H19_ID = "houdini_tidal_relic"
H20_ID = "houdini_lapis_scarab"
_WORK = 1024


def _resize(a: np.ndarray, h: int, w: int) -> np.ndarray:
    if a.shape[:2] == (h, w):
        return a
    try:
        import cv2
        return cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)
    except Exception:
        yi=np.linspace(0,a.shape[0]-1,h).astype(np.int32); xi=np.linspace(0,a.shape[1]-1,w).astype(np.int32)
        return a[yi][:,xi]


def _carrier_and_secret(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return visible diamond textile, fractured local state, and a skull-only material mask."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # Visible carrier: rotating 8–24px-native diamond textile.  All of this
    # survives independently of the secret; no paint pixel contains a skull.
    u=(x*.82+y*.57)/11.5; v=(-x*.57+y*.82)/11.5
    fu=u-np.floor(u)-.5; fv=v-np.floor(v)-.5
    diamond=np.clip((.52-(np.abs(fu)+np.abs(fv)))*5.4,0,1)
    rim=np.clip((.085-np.abs(np.abs(fu)+np.abs(fv)-.43))*11.7,0,1)
    # Each actual diamond is assigned one of four quiet visible pearl tones;
    # this is a textile rhythm, not a secret-symbol colour channel.
    gx=np.floor(u).astype(np.int32); gy=np.floor(v).astype(np.int32)
    code=np.mod(gx*17+gy*31+gx*gy*3,8)
    visible_state=(code%4).astype(np.float32)/3.0
    # Skull geometry lives only in material space.  It is further broken into
    # existing diamond cells so there is no opaque one-channel silhouette.
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.49)/(wh*.50)
    cranium=((X/.255)**2+((Y+.10)/.31)**2)<1.0
    jaw=(np.abs(X)<.20)&(Y>.08)&(Y<.34)&((np.abs(X)+.48*(Y-.08))<.25)
    eye_l=((X+.092)/.075)**2+((Y+.075)/.055)**2<1.; eye_r=((X-.092)/.075)**2+((Y+.075)/.055)**2<1.
    nose=(np.abs(X)<.040)&(Y>-.005)&(Y<.10)
    teeth=(np.abs(X)<.15)&(Y>.17)&(Y<.27)&(np.mod(np.floor((X+.16)*46),2)==0)
    silhouette=(cranium|jaw)&~(eye_l|eye_r|nose)
    silhouette= silhouette & (~teeth | (np.abs(X)<.13))
    # Forty-to-sixty percent of only the already visible local cells shift
    # material state. This makes the combined map legible but denies a solid
    # decal-like secret in neutral viewing.
    fractured=(np.mod(code*5+gx*7+gy*11,7)<=3)&(diamond>.12)
    secret=(silhouette&fractured).astype(np.float32)
    carrier=np.stack((diamond,rim,visible_state),axis=2).astype(np.float32)
    return _resize(carrier,h,w).astype(np.float32), _resize((code%5).astype(np.float32),h,w), _resize(secret,h,w)


def render_h1(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1])
    carrier,local,secret=_carrier_and_secret(h,w)
    d,rim,state=carrier[...,0],carrier[...,1],carrier[...,2]
    # Cool navy/graphite visible carrier: it is complete and attractive without
    # discovering a skull. Tiny pearl change follows the actual diamonds.
    # H1-I2: keep the skull entirely spec-only, but lift the ordinary navy
    # diamond carrier enough that it reads as premium quilted enamel in a
    # catalog/neutral-light view rather than a near-black blank.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.030,.052,.105)
    quiet=np.stack((.070+.075*state,.115+.085*state,.205+.135*state),axis=2)
    paint=paint*(1-d[...,None]*.86)+quiet*(d[...,None]*.86)
    paint=paint*(1-rim[...,None]*.38)+np.asarray((.26,.35,.54),np.float32)*(rim[...,None]*.38)
    # Baseline local material map: four quiet states per diamond.
    metal=56+32*state+22*rim; rough=151-44*state+24*(1-d); coat=62+44*d+20*rim
    # Secret pixels exchange local physical states instead of simply brightening
    # one channel. M high/R low/CC high is a fractured hot-pink/grazing family;
    # offsets preserve multiple adjacent states and a non-solid map silhouette.
    q=np.mod(local,5)
    sm=np.select((q==0,q==1,q==2,q==3),(238,34,176,209),default=132).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3),(22,188,82,43),default=112).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3),(224,66,164,205),default=126).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    spec=np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),axis=2).astype(np.uint8)
    return np.clip(paint,0,1).astype(np.float32),spec


def h1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h1((h,w))
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h1_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h1((h,w))
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


# Owner-directed H1-I28 proof screen: independent blue-black oxide carrier.
# I26 remains the current live-development staging candidate unless I28 wins
# I33 is live-development visible after ten isolated visual iterations. It is
# unaccepted pending official picker manifest and real fixed-location evidence.
def h1_i3_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h1_i20.paint_veiled_skull_i33(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h1_i3_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h1_i20.spec_veiled_skull_i33(
        (h, w), 42 if seed is None else int(seed), sm, 0, 0,
    )
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    if coverage.shape != (h, w):
        coverage = _resize(coverage, h, w)
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = (mrc * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out


# SPB-H1 / picker truth, 2026-08-31: the stable bridge wrappers delegate to
# I33, so bytecode-only picker hashing otherwise misses isolated carrier edits.
# This existing server hook tracks the actual source dependency; render output
# is unchanged.
h1_i3_paint._spb_picker_dependency_modules = (
    'engine.expansions.fractured_houdini_veiled_skull_i33_2026',
)
h1_i3_spec._spb_picker_dependency_modules = (
    'engine.expansions.fractured_houdini_veiled_skull_i33_2026',
)


# H2-I5e — owner-directed total Houdini rebuild, 2026-08-30.  An innocent
# smoked mokume-gane lacquer carries repeated full-canvas flame envelopes only
# in varied M/R/Cc states.  This replaces the failed old H2 pinstripe pass;
# native preflight 2.106s, channel std 48.9/48.1/47.5.  It is deliberately
# retained as live-development material pending required multi-light car proof.
def h2_i5_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h2_i5.paint_ember_cipher_i5(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h2_i5_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h2_i5.spec_ember_cipher_i5(
        (h, w), 42 if seed is None else int(seed), sm, 0, 0,
    )
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = mrc
    out[..., 3] = np.clip(coverage, 0, 1) * 255
    return out


# H3-I4 — independently authored midnight pearl cloisonné with nineteen
# rotated M/R/Cc-only spiral discoveries.  Native preflight 2.927s;
# 50.5/49.6/48.5 channel std.  Development wiring only pending real car proof.
def h3_i4_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h3_i4.paint_ghost_orbit_i1(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h3_i4_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h3_i4.spec_ghost_orbit_i1(
        (h, w), 42 if seed is None else int(seed), sm, 0, 0,
    )
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = mrc
    out[..., 3] = np.clip(coverage, 0, 1) * 255
    return out


# H4-I4 — a distinct oxidized jade micro-cloisonné carrier. Seventeen rotated
# cinder crosses are M/R/Cc-only repeat events (2.501s, std 44.7/42.5/45.2).
def h4_i4_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h4_i4.paint_cinder_cross_i1(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h4_i4_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h4_i4.spec_cinder_cross_i1(
        (h, w), 42 if seed is None else int(seed), sm, 0, 0,
    )
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = mrc
    out[..., 3] = np.clip(coverage, 0, 1) * 255
    return out


# H5-I4 — smoked rose lacquer with sixteen repeated, rotated M/R/Cc-only
# ouroboros events (1.956s; channel std 50.3/48.6/48.9).
def h5_i4_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h5_i4.paint_ouroboros_i1(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h5_i4_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h5_i4.spec_ouroboros_i1(
        (h, w), 42 if seed is None else int(seed), sm, 0, 0,
    )
    coverage = np.asarray(mask, np.float32)
    coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty((h, w, 4), np.uint8)
    out[..., :3] = mrc
    out[..., 3] = np.clip(coverage, 0, 1) * 255
    return out


# H7-I4 — dark prismatic microcells with seventeen repeated, connected
# M/R/Cc-only lightning glyphs (0.853s; material simulation screened).
def h7_i4_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h7_i4.paint_storm_glyph_i1(
        paint, shape, mask, 42 if seed is None else int(seed), pm, bb,
    )


def h7_i4_spec(shape, mask, seed=None, sm=1.0):
    h, w = int(shape[0]), int(shape[1])
    mrc = _h7_i4.spec_storm_glyph_i1((h, w), 42 if seed is None else int(seed), sm, 0, 0)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty((h, w, 4), np.uint8); out[..., :3] = mrc; out[..., 3] = np.clip(coverage, 0, 1) * 255
    return out


# H8-I2 — sapphire kintsugi marquetry with sixteen repeated, three-state
# M/R/Cc-only Seraph eyes (1.035s; neutral/grazing screen passed).
def h8_i2_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h8_i2.paint_seraph_eye_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h8_i2_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h8_i2.spec_seraph_eye_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h9_i2_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h9_i2.paint_verdigris_star_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h9_i2_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h9_i2.spec_verdigris_star_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h10_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h10_i1.paint_frost_crescent_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h10_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h10_i1.spec_frost_crescent_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h11_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h11_i1.paint_gilded_crown_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h11_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h11_i1.spec_gilded_crown_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h12_i2_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h12_i2.paint_glacier_eye_i2(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h12_i2_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h12_i2.spec_glacier_eye_i2((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h13_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h13_i1.paint_phantom_comet_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h13_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h13_i1.spec_phantom_comet_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h14_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h14_i1.paint_verdigris_ankh_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h14_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h14_i1.spec_verdigris_ankh_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h15_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h15_i1.paint_porcelain_cipher_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h15_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h15_i1.spec_porcelain_cipher_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h16_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h16_i1.paint_mirage_compass_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h16_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h16_i1.spec_mirage_compass_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h17_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h17_i1.paint_quicksilver_helix_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h17_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h17_i1.spec_quicksilver_helix_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h18_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h18_i1.paint_chroma_pyre_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h18_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h18_i1.spec_chroma_pyre_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h19_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h19_i1.paint_tidal_relic_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h19_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h19_i1.spec_tidal_relic_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h20_i1_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h20_i1.paint_lapis_scarab_i1(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h20_i1_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h20_i1.spec_lapis_scarab_i1((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


def h6_i5_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    return _h6_i5.paint_prism_moth_i5(paint, shape, mask, 42 if seed is None else int(seed), pm, bb)


def h6_i5_spec(shape, mask, seed=None, sm=1.0):
    h,w=int(shape[0]),int(shape[1]);mrc=_h6_i5.spec_prism_moth_i5((h,w),42 if seed is None else int(seed),sm,0,0)
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    out=np.empty((h,w,4),np.uint8);out[...,:3]=mrc;out[...,3]=np.clip(coverage,0,1)*255;return out


LIVE_PAIRS={H1_ID:(h1_spec,h1_paint)}

def _carrier_and_flame(h: int, w: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """H2: normal smoked-copper pinstripe weave + a flame-only material mask."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # Two tight, curled pinstripe families make a complete 8–28px native
    # smoked-copper weave. It is physically unrelated to H1's diamond quilt.
    a=x*.116+y*.040+2.7*np.sin(y*.022); b=y*.103-x*.052+2.2*np.sin(x*.018)
    rail_a=np.clip((.070-np.abs(np.sin(a)))*14.2,0,1); rail_b=np.clip((.050-np.abs(np.sin(b)))*18.4,0,1)
    joint=np.clip(rail_a*rail_b*1.7,0,1); weave=np.maximum(rail_a,rail_b)
    gx=np.floor((x*.116+y*.040)/np.pi).astype(np.int32); gy=np.floor((y*.103-x*.052)/np.pi).astype(np.int32)
    local=np.mod(gx*23+gy*13+gx*gy*5,6).astype(np.float32)
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.51)/(wh*.50)
    # A asymmetric multi-tongue flame; it exists nowhere in visible paint.
    body=(Y>.02)&(Y<.44)&(np.abs(X+.035*np.sin(11*Y)) < (.29-.44*(Y-.02)))
    tongue_l=((X+.10+.10*np.sin(17*Y))**2/.010+(Y-.04)**2/.12<1)&(Y<.27)
    tongue_r=((X-.11-.09*np.sin(15*Y))**2/.008+(Y-.03)**2/.10<1)&(Y<.24)
    tip=((X+.02*np.sin(26*Y))**2/.013+(Y-.34)**2/.030<1)
    flame=(body|tongue_l|tongue_r|tip)&(Y>-.01)
    # Broken along carrier rails: hard lighting states are localized marks,
    # never a one-channel flame painted over the material.
    # H2-I2: do not restrict the secret to rail pixels—the result was a thin
    # outline, not a feature discovered *inside* the carrier. Half of the
    # existing small weave parcels switch state, retaining broken topology.
    fractured=np.mod(gx*7+gy*11,6)<=3
    return _resize(np.stack((weave,joint,local/5.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((flame&fractured).astype(np.float32),h,w)


def render_h2(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); carrier,local,secret=_carrier_and_flame(h,w)
    weave,joint,tier=carrier[...,0],carrier[...,1],carrier[...,2]
    # H2-I3: neutral light should read as a smoked-copper pinstripe weave;
    # lift only its ordinary carrier, never the hidden flame material mask.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.105,.052,.030)
    copper=np.stack((.39+.25*tier,.155+.145*tier,.070+.080*tier),2)
    paint=paint*(1-weave[...,None]*.92)+copper*(weave[...,None]*.92)
    paint=paint*(1-joint[...,None]*.52)+np.asarray((.52,.20,.052),np.float32)*(joint[...,None]*.52)
    # Full carrier keeps its own six quiet material populations; the flame
    # locally reorders them into its hot/cool fractured family.
    metal=38+72*weave+58*joint+68*tier; rough=213-82*weave-47*joint-71*tier; coat=34+66*weave+86*joint+74*tier
    q=np.mod(local,6)
    sm=np.select((q==0,q==1,q==2,q==3,q==4),(244,42,191,224,117),default=161).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4),(18,196,66,34,132),default=94).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4),(238,54,176,216,108),default=146).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h2_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h2((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h2_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h2((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_spiral(h: int, w: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """H3: midnight quartz shuttle weave; secret is a broken galaxy spiral."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # Distinct visible carrier: short interlaced shuttle ribs, not H1 diamonds
    # or H2 pinstripes. Each rib is 8–26px native after upscale.
    u=x*.153+y*.041+2.5*np.sin(y*.019); v=y*.129-x*.064+2.0*np.sin(x*.023)
    rib_u=np.clip((.058-np.abs(np.sin(u)))*17.2,0,1); rib_v=np.clip((.050-np.abs(np.sin(v)))*19.6,0,1)
    knot=np.clip(rib_u*rib_v*1.85,0,1); carrier=np.maximum(rib_u,rib_v)
    gx=np.floor(u/np.pi).astype(np.int32); gy=np.floor(v/np.pi).astype(np.int32)
    local=np.mod(gx*29+gy*17+gx*gy*7,7).astype(np.float32)
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.50)/(wh*.50); rad=np.sqrt(X*X+Y*Y)+1e-5; ang=np.arctan2(Y,X)
    # Two broken logarithmic-ish arms and a quiet core. The secret is sampled
    # only through local shuttle parcels, so it cannot become a painted logo.
    arm=np.abs(np.sin(2.0*ang+rad*22.5+1.5*np.sin(rad*8.0)))<.16
    core=rad<.075; galaxy=((arm&(rad>.06)&(rad<.36))|core)
    fractured=np.mod(gx*11+gy*5+gx*gy,7)<=3
    return _resize(np.stack((carrier,knot,local/6.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((galaxy&fractured).astype(np.float32),h,w)


def render_h3(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_spiral(h,w)
    carrier,knot,tier=field[...,0],field[...,1],field[...,2]
    # H3-I2: expose the ordinary midnight-quartz shuttle weave to neutral
    # catalog light only; the galaxy spiral remains entirely spec-hidden.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.020,.048,.085)
    quartz=np.stack((.065+.085*tier,.145+.125*tier,.265+.185*tier),2)
    paint=paint*(1-carrier[...,None]*.90)+quartz*(carrier[...,None]*.90)
    paint=paint*(1-knot[...,None]*.50)+np.asarray((.18,.46,.70),np.float32)*(knot[...,None]*.50)
    metal=31+79*carrier+62*knot+76*tier; rough=218-87*carrier-54*knot-75*tier; coat=29+69*carrier+94*knot+77*tier
    q=np.mod(local,7)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5),(246,28,182,221,96,158),default=205).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5),(16,204,68,31,146,88),default=49).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5),(242,52,170,213,92,140),default=193).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h3_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h3((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h3_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h3((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_cross(h: int, w: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """H4: dark stained-oilskin mosaic with a material-only cross."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # Skewed micro-tiles with a soft inset are an oilskin mosaic—not any prior
    # Houdini carrier. The 6–18px source tiles become 12–36px native.
    u=(x+.31*y+3*np.sin(y*.019))/13.2; v=(y-.17*x+2*np.sin(x*.021))/10.8
    fu=u-np.floor(u)-.5; fv=v-np.floor(v)-.5
    inset=np.clip((.43-np.maximum(np.abs(fu),np.abs(fv)))*7.0,0,1)
    seam=np.clip((.055-np.abs(np.maximum(np.abs(fu),np.abs(fv))-.43))*17.0,0,1)
    gx=np.floor(u).astype(np.int32); gy=np.floor(v).astype(np.int32); local=np.mod(gx*37+gy*19+gx*gy*3,8).astype(np.float32)
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.50)/(wh*.50)
    vertical=(np.abs(X)<.070)&(Y>-.34)&(Y<.34); horizontal=(np.abs(Y+.045)<.068)&(np.abs(X)<.25)
    cross=vertical|horizontal
    fractured=np.mod(gx*3+gy*13+gx*gy*5,7)<=3
    return _resize(np.stack((inset,seam,local/7.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((cross&fractured).astype(np.float32),h,w)


def render_h4(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_cross(h,w)
    inset,seam,tier=field[...,0],field[...,1],field[...,2]
    # H4-I2: ordinary stained-oilskin tiles need a visible neutral-light
    # surface; hidden cross state remains exclusively in fractured spec cells.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.040,.050,.040)
    oil=np.stack((.085+.082*tier,.155+.092*tier,.115+.062*tier),2)
    paint=paint*(1-inset[...,None]*.92)+oil*(inset[...,None]*.92)
    paint=paint*(1-seam[...,None]*.40)+np.asarray((.31,.28,.18),np.float32)*(seam[...,None]*.40)
    metal=35+73*inset+58*seam+81*tier; rough=220-79*inset-44*seam-78*tier; coat=31+66*inset+91*seam+77*tier
    q=np.mod(local,8)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,30,180,217,76,154,230),default=116).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(15,205,70,29,159,92,43),default=129).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(244,48,171,210,84,143,220),default=110).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h4_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h4((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h4_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h4((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_ouroboros(h: int, w: int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """H5: scaled ceramic microtiles with a fractured ouroboros in spec only."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # Offset fishscale cells are neither a grid nor any prior carrier. Each
    # semicircle/rim is 8–30px native once rendered full-size.
    cell=12.0; gy=np.floor(y/cell).astype(np.int32); gx=np.floor((x+(gy&1)*cell*.5)/cell).astype(np.int32)
    fx=np.mod(x+(gy&1)*cell*.5,cell)-cell*.5; fy=np.mod(y,cell)-cell*.5
    arc=np.sqrt((fx/(cell*.45))**2+((fy+cell*.10)/(cell*.43))**2)
    scale=np.clip((.11-np.abs(arc-1.0))*8.8,0,1); bowl=np.clip(1.-arc,0,1)
    rim=np.maximum(scale,np.clip((.065-np.abs(fy-cell*.30))*13.,0,1)*np.clip(1.-np.abs(fx)/(cell*.45),0,1))
    local=np.mod(gx*41+gy*23+gx*gy*7,9).astype(np.float32)
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.50)/(wh*.50); r=np.sqrt(X*X+Y*Y); a=np.arctan2(Y,X)
    ring=(r>.165)&(r<.265)&~((a>-.42)&(a<-.03))
    # A raised serpent head and eye at the ring gap make it an ouroboros rather
    # than a generic halo, but only material parcels carry this silhouette.
    head=((X-.20)**2/.010+(Y+.065)**2/.006)<1.; jaw=((X-.16)**2/.010+(Y+.11)**2/.004)<1.
    ouro=ring|head|jaw
    fractured=np.mod(gx*5+gy*17+gx*gy*3,8)<=4
    return _resize(np.stack((bowl,rim,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((ouro&fractured).astype(np.float32),h,w)


def render_h5(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_ouroboros(h,w)
    bowl,rim,tier=field[...,0],field[...,1],field[...,2]
    # H5-I2: reveal a quiet blue ceramic fishscale carrier in neutral light;
    # retain the ouroboros entirely as a fractured material-state silhouette.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.025,.040,.062)
    ceramic=np.stack((.060+.090*tier,.125+.125*tier,.180+.155*tier),2)
    paint=paint*(1-bowl[...,None]*.86)+ceramic*(bowl[...,None]*.86)
    paint=paint*(1-rim[...,None]*.40)+np.asarray((.18,.40,.52),np.float32)*(rim[...,None]*.40)
    metal=29+75*bowl+61*rim+84*tier; rough=222-83*bowl-48*rim-81*tier; coat=27+66*bowl+92*rim+80*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(248,26,183,224,74,151,232,109),default=179).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(15,206,65,28,161,91,40,137),default=80).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(244,47,173,217,82,141,222,103),default=164).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h5_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h5((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h5_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h5((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_prism_moth(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Opaline micro-feather lacquer with an entirely material-bound moth."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32)
    # H6 I2: a bright, layered 9–28px feather-lacquer field—not the rejected
    # black-dot textile.  Core, rim, vein, nick and pearlescent wash stack as
    # distinct visible marks while none carries the moth in RGB.
    cell=17.; gy=np.floor(y/(cell*.63)).astype(np.int32); gx=np.floor((x+(gy&1)*cell*.48)/cell).astype(np.int32)
    fx=np.mod(x+(gy&1)*cell*.48,cell)-cell*.50; fy=np.mod(y,cell*.63)-cell*.315
    core=np.clip(1.-np.sqrt((fx/(cell*.42))**2+(fy/(cell*.27))**2),0,1)
    rim=np.clip((.07-np.abs(np.sqrt((fx/(cell*.42))**2+(fy/(cell*.27))**2)-.83))*13.,0,1)
    vein=np.clip((.052-np.abs(fx+fy*.58))*18.,0,1)*np.clip(1-np.abs(fy)/(cell*.28),0,1)
    nick=np.clip((.042-np.abs(fy+fx*.38))*21.,0,1)*np.clip(1-np.abs(fx)/(cell*.34),0,1)
    code=np.mod(gx*37+gy*19+gx*gy*7,9).astype(np.float32)
    wash=.5+.5*np.sin(x*.018+y*.011)+.5*np.sin(x*.006-y*.019)
    X=(x-ww*.50)/(ww*.50); Y=(y-wh*.47)/(wh*.50)
    # A deliberately large-but-cell-broken moth has wing notches, antennae and
    # a tail; only existing lacquer cells change optical state.
    body=(X/.038)**2+((Y+.01)/.255)**2<1.
    left=((X+.225)/.285)**2+((Y+.025)/.275)**2<1.; right=((X-.225)/.255)**2+((Y+.018)/.255)**2<1.
    left &= (X<-.018)&(Y<.23)&~(((X+.34)/.105)**2+((Y-.15)/.09)**2<1.)
    right &= (X>.018)&(Y<.21)&~(((X-.31)/.095)**2+((Y-.13)/.085)**2<1.)
    antenna=(np.abs(Y+.27+1.15*np.abs(X))<.017)&(np.abs(X)<.17)
    tail=(np.abs(X)<.13)&(Y>.18)&(Y<.31)&(np.abs(X)<(.14-(Y-.18)*.44))
    moth=body|left|right|antenna|tail
    fractured=(np.mod(gx*11+gy*5+gx*gy*3,9)<=5)&(core>.11)
    return _resize(np.stack((core,rim,vein,nick,code/8.,wash),2),h,w).astype(np.float32),_resize(code,h,w),_resize((moth&fractured).astype(np.float32),h,w)


def render_h6(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,code,secret=_carrier_and_prism_moth(h,w)
    core,rim,vein,nick,tier,wash=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.030,.016,.055)
    pearl=np.stack((.16+.14*tier+.05*wash,.055+.08*tier+.03*wash,.20+.20*tier+.08*wash),2)
    paint=paint*(1-core[...,None]*.88)+pearl*(core[...,None]*.88)
    paint=paint*(1-rim[...,None]*.46)+np.asarray((.54,.22,.56),np.float32)*(rim[...,None]*.46)
    paint=paint*(1-vein[...,None]*.34)+np.asarray((.18,.56,.61),np.float32)*(vein[...,None]*.34)
    paint=paint*(1-nick[...,None]*.31)+np.asarray((.78,.42,.19),np.float32)*(nick[...,None]*.31)
    metal=31+63*core+74*rim+82*vein+44*nick+49*tier; rough=220-72*core-68*rim-84*vein-41*nick-55*tier; coat=32+63*core+92*rim+65*vein+51*nick+67*tier
    q=np.mod(code,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(249,24,184,229,64,151,238,104),default=176).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(14,217,57,25,170,86,36,141),default=78).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(248,41,173,224,79,139,230,98),default=165).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h6_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h6((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h6_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h6((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_eclipse(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full-canvas night-lacquer composition; the portal remains material-only."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # H7 correction: broad composition is built from 8–32px filaments, lips,
    # broken inlays, and pearl motes—not a repeated field.  Three bent seams
    # deliberately travel the entire car canvas without becoming the hidden portal.
    c1=np.abs(y-(wh*.19+.00034*(x-ww*.20)**2)); c2=np.abs(y-(wh*.69-.00027*(x-ww*.67)**2)); c3=np.abs(y-(wh*.47+18*np.sin(x*.017)))
    lip=np.maximum.reduce((np.clip((8-c1)*.125,0,1),np.clip((7-c2)*.143,0,1),np.clip((6-c3)*.167,0,1)))
    halo=np.maximum.reduce((np.clip((20-c1)*.045,0,1),np.clip((18-c2)*.05,0,1),np.clip((16-c3)*.056,0,1)))
    # Fine 8–24px broken hatches flow *along* the seams; their phase diversity
    # gives density without making a macro painted stripe.
    phase=np.mod(np.floor((x*.63+y*.29)/9)+np.floor((x*.11-y*.41)/7),7)
    hatch=np.clip((.72-np.abs(np.sin((x*.092+y*.051)+np.sin(y*.033)*.8)))*1.8,0,1)
    mote=(np.mod(np.floor(x/13)*19+np.floor(y/11)*23,13)<1).astype(np.float32)
    arc=np.sqrt(((X-.22)/.31)**2+((Y-.55)/.47)**2); arc_lip=np.clip((.020-np.abs(arc-.78))*42.,0,1)
    arc2=np.sqrt(((X-.76)/.29)**2+((Y-.42)/.42)**2); arc_lip2=np.clip((.018-np.abs(arc2-.82))*47.,0,1)
    local=np.mod(np.floor(x/11)*37+np.floor(y/9)*17+np.floor((x+y)/23)*7,9).astype(np.float32)
    # The eclipse is not a base-color circle: only fractured material parcels
    # around the portal's ring/iris can brighten under the right reflection.
    ex=(X-.50)/.235; ey=(Y-.49)/.235; er=np.sqrt(ex*ex+ey*ey); ea=np.arctan2(ey,ex)
    ring=(er>.69)&(er<.91)&~((ea>-.66)&(ea<-.22)); corona=(er>.53)&(er<.65)&((np.sin(ea*7+er*19)>-.28))
    shard=(np.mod(np.floor(x/12)*11+np.floor(y/10)*7,8)<=4)
    secret=(ring|corona)&shard
    return _resize(np.stack((lip,halo,hatch,mote,arc_lip,arc_lip2,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize(secret.astype(np.float32),h,w)


def render_h7(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_eclipse(h,w)
    lip,halo,hatch,mote,arc,arc2,tier=(field[...,i] for i in range(7))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.018,.010,.048)
    # A midnight violet ground, cool pearl arcs, copper lips and sparse small
    # flecks make an intentional all-car composition before any reveal occurs.
    ground=np.stack((.025+.052*tier,.030+.034*tier,.090+.095*tier),2)
    paint=paint*.54+ground*.46
    paint=paint*(1-halo[...,None]*.32)+np.asarray((.09,.13,.34),np.float32)*(halo[...,None]*.32)
    paint=paint*(1-lip[...,None]*.70)+np.asarray((.77,.30,.16),np.float32)*(lip[...,None]*.70)
    paint=paint*(1-(arc+arc2)[...,None]*.42)+np.asarray((.25,.65,.83),np.float32)*((arc+arc2)[...,None]*.42)
    fil=np.clip(hatch*(.20+.54*halo+.38*arc+.38*arc2),0,1)
    paint=paint*(1-fil[...,None]*.26)+np.asarray((.65,.43,.86),np.float32)*(fil[...,None]*.26)
    paint=paint*(1-mote[...,None]*.045)+np.asarray((.94,.71,.34),np.float32)*(mote[...,None]*.045)
    metal=25+78*lip+44*halo+73*hatch+47*mote+81*arc+89*arc2+46*tier; rough=229-86*lip-37*halo-69*hatch-31*mote-72*arc-78*arc2-54*tier; coat=27+88*lip+49*halo+70*hatch+38*mote+89*arc+81*arc2+64*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(250,21,190,234,56,158,241,93),default=173).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(11,224,51,21,177,80,31,148),default=76).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(251,36,171,232,74,132,235,89),default=160).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h7_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h7((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h7_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h7((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_wolf(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Flowing aurora-lacquer composition with a material-only wolf face."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Four drifting aurora rivers cross the whole field.  Their edges are made
    # from 8–28px segmented lips, shards, ribs and pearl windows, avoiding an
    # ordinary macro gradient or repeated wallpaper.
    f=x+44*np.sin(y*.014)+19*np.sin(y*.038)
    p1=np.abs(np.mod(f-ww*.13,ww*.42)-ww*.21); p2=np.abs(np.mod(f-ww*.29,ww*.47)-ww*.235)
    river=np.maximum(np.clip((32-p1)/32,0,1),np.clip((25-p2)/25,0,1))
    lip=np.maximum(np.clip((8-p1)*.125,0,1),np.clip((7-p2)*.143,0,1))
    rib=np.clip((.64-np.abs(np.sin(f*.15+y*.027)))*2.75,0,1)*river
    shard=np.clip((.55-np.abs(np.sin(f*.11-y*.071+np.sin(y*.033))))*2.3,0,1)*river
    pearl=np.clip((.12-np.abs(np.sin(f*.045+y*.052)))*7.7,0,1)*(1-river*.35)
    local=np.mod(np.floor(f/12)*29+np.floor(y/10)*17+np.floor((f-y)/27)*5,9).astype(np.float32)
    # A forward-looking wolf: forehead, tapered cheek, ears, muzzle and the
    # negative eye breaks are sampled through existing micro-ribbon parcels only.
    cx=(X-.50)/.27; cy=(Y-.48)/.31
    head=cx*cx+cy*cy<1.
    ear_l=(X>.27)&(X<.45)&(Y<.38)&(Y>.12+(X-.27)*1.55); ear_r=(X<.73)&(X>.55)&(Y<.38)&(Y>.12+(.73-X)*1.55)
    muzzle=(np.abs(X-.50)<.17)&(Y>.47)&(Y<.72)&((np.abs(X-.50)+.52*(Y-.47))<.23)
    cheek=((X-.50)/.24)**2+((Y-.53)/.21)**2<1.
    eye_l=((X-.42)/.045)**2+((Y-.45)/.027)**2<1.; eye_r=((X-.58)/.045)**2+((Y-.45)/.027)**2<1.
    nose=(np.abs(X-.50)<.05)&(Y>.59)&(Y<.65)
    wolf=(head|ear_l|ear_r|muzzle|cheek)&~(eye_l|eye_r|nose)
    parcel=(np.mod(np.floor(f/11)*7+np.floor(y/9)*13,8)<=5)&((rib+shard+lip+pearl)>.12)
    return _resize(np.stack((river,lip,rib,shard,pearl,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((wolf&parcel).astype(np.float32),h,w)


def render_h8(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_wolf(h,w)
    river,lip,rib,shard,pearl,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.010,.045,.040)
    aurora=np.stack((.025+.06*tier,.18+.19*tier,.15+.17*tier),2)
    paint=paint*(1-river[...,None]*.64)+aurora*(river[...,None]*.64)
    paint=paint*(1-lip[...,None]*.67)+np.asarray((.35,.90,.62),np.float32)*(lip[...,None]*.67)
    paint=paint*(1-rib[...,None]*.38)+np.asarray((.10,.37,.80),np.float32)*(rib[...,None]*.38)
    paint=paint*(1-shard[...,None]*.26)+np.asarray((.61,.31,.83),np.float32)*(shard[...,None]*.26)
    paint=paint*(1-pearl[...,None]*.20)+np.asarray((.76,.84,.55),np.float32)*(pearl[...,None]*.20)
    metal=22+61*river+91*lip+71*rib+58*shard+47*pearl+51*tier; rough=232-59*river-91*lip-68*rib-48*shard-35*pearl-57*tier; coat=25+73*river+96*lip+68*rib+55*shard+43*pearl+65*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(251,20,193,237,53,162,243,89),default=171).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(10,226,49,20,180,77,29,151),default=75).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(252,34,168,236,72,128,238,85),default=158).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h8_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    h,w=int(shape[0]),int(shape[1]); authored,_=render_h8((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def h8_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    h,w=int(shape[0]),int(shape[1]); _,spec=render_h8((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _authored_paint(renderer, paint, shape, mask, pm):
    h,w=int(shape[0]),int(shape[1]); authored,_=renderer((h,w)); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.
    if src.shape[:2]!=(h,w): src=_resize(src,h,w)
    coverage=np.asarray(mask,np.float32); coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    mix=np.clip(coverage,0,1)[...,None]*float(pm)
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def _authored_spec(renderer, shape, mask):
    h,w=int(shape[0]),int(shape[1]); _,spec=renderer((h,w)); coverage=np.asarray(mask,np.float32)
    coverage=coverage[...,0] if coverage.ndim==3 else coverage
    if coverage.shape!=(h,w): coverage=_resize(coverage,h,w)
    out=np.empty((h,w,4),np.uint8); out[...,:3]=(spec*np.clip(coverage,0,1)[...,None]).astype(np.uint8); out[...,3]=(np.clip(coverage,0,1)*255).astype(np.uint8)
    return out


def _carrier_and_dagger(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wine-black folded satin with a dagger sampled only through fold parcels."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Full-car satin folds are macro organization constructed from many fine
    # 8–32px prisms, lips, cross-grain cuts and seam breaks—not broad flat bands.
    u=x*.73+y*.52+30*np.sin(y*.019); v=-x*.31+y*.83+18*np.sin(x*.022)
    fold=.5+.5*np.sin(u*.029+np.sin(v*.018)*1.3)
    crease=np.clip((.092-np.abs(np.sin(u*.058+np.sin(v*.021))))*10.5,0,1)
    prism=np.clip((.43-np.abs(np.sin(u*.15-v*.07)))*2.35,0,1)
    cross=np.clip((.12-np.abs(np.sin(v*.12+u*.025)))*7.8,0,1)*(.25+.75*prism)
    nick=np.clip((.070-np.abs(np.sin(u*.31+v*.14)))*12.,0,1)*(.18+.82*crease)
    local=np.mod(np.floor(u/11)*23+np.floor(v/9)*31+np.floor((u+v)/27)*7,9).astype(np.float32)
    # Dagger: blade taper, central fuller, hilt bar and pointed pommel.  The
    # neutral RGB contains only satin; broken fold parcels carry the silhouette.
    blade=(np.abs(X-.50)<(.035+.18*(.64-Y)))&(Y>.20)&(Y<.64)
    fuller=(np.abs(X-.50)<.022)&(Y>.25)&(Y<.58)
    hilt=(np.abs(X-.50)<.19)&(Y>.62)&(Y<.68); grip=(np.abs(X-.50)<.06)&(Y>.67)&(Y<.80)
    pommel=(X-.50)**2/.006+(Y-.82)**2/.012<1.
    dagger=(blade&~fuller)|hilt|grip|pommel
    parcel=(np.mod(np.floor(u/10)*5+np.floor(v/8)*11,9)<=5)&((crease+prism+cross+nick)>.14)
    return _resize(np.stack((fold,crease,prism,cross,nick,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((dagger&parcel).astype(np.float32),h,w)


def render_h9(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_dagger(h,w)
    fold,crease,prism,cross,nick,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.042,.006,.020)
    satin=np.stack((.16+.22*fold+.07*tier,.015+.035*fold+.025*tier,.065+.10*fold+.045*tier),2)
    paint=paint*.34+satin*.66
    paint=paint*(1-crease[...,None]*.46)+np.asarray((.86,.19,.37),np.float32)*(crease[...,None]*.46)
    paint=paint*(1-prism[...,None]*.30)+np.asarray((.54,.10,.46),np.float32)*(prism[...,None]*.30)
    paint=paint*(1-cross[...,None]*.19)+np.asarray((.92,.56,.30),np.float32)*(cross[...,None]*.19)
    paint=paint*(1-nick[...,None]*.16)+np.asarray((.24,.02,.10),np.float32)*(nick[...,None]*.16)
    metal=23+62*fold+91*crease+68*prism+39*cross+46*nick+52*tier; rough=230-57*fold-88*crease-67*prism-34*cross-39*nick-56*tier; coat=28+68*fold+95*crease+71*prism+45*cross+42*nick+64*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(252,19,196,239,50,165,245,86),default=169).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(9,229,47,19,183,74,27,154),default=74).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(253,32,165,240,69,124,240,81),default=156).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h9_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h9,paint,shape,mask,pm)


def h9_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h9,shape,mask)


def _carrier_and_rose(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Alabaster mineral veins and a material-only fractured rose."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Marble is organized as a full-car geological field: subtle broad beds
    # plus 8–30px capillary veins, mineral lips, mica flashes and fissure cuts.
    u=x+48*np.sin(y*.011)+18*np.sin(y*.037); v=y+31*np.sin(x*.015)
    bed=.5+.5*np.sin(u*.013+v*.006)
    vein=np.clip((.10-np.abs(np.sin(u*.071+np.sin(v*.018))))*8.5,0,1)
    capillary=np.clip((.075-np.abs(np.sin(u*.19-v*.043+np.sin(v*.029))))*11.,0,1)
    mineral=np.clip((.15-np.abs(np.sin(u*.034+v*.081)))*6.7,0,1)
    mica=(np.mod(np.floor(u/14)*29+np.floor(v/12)*17,17)<2).astype(np.float32)*mineral
    local=np.mod(np.floor(u/11)*41+np.floor(v/9)*19+np.floor((u-v)/29)*3,9).astype(np.float32)
    # Five rotated nested petals, a central cup and small leaf tips are retained
    # only as a broken material population.  The neutral marble has no rose RGB.
    cx=X-.50; cy=Y-.49; petal=np.zeros_like(X,dtype=bool)
    for ang in (0.,1.257,2.514,3.771,5.028):
        ca=np.cos(ang); sa=np.sin(ang); px=cx*ca+cy*sa; py=-cx*sa+cy*ca
        petal|=((px/.19)**2+((py+.105)/.12)**2<1.)&~((px/.070)**2+((py+.105)/.045)**2<1.)
    cup=(cx/.075)**2+(cy/.07)**2<1.; stem=(np.abs(cx)<.018)&(cy>.12)&(cy<.30)
    leaf=((cx+.08)/.11)**2+((cy-.20)/.055)**2<1.
    rose=petal|cup|stem|leaf
    parcel=(np.mod(np.floor(u/10)*7+np.floor(v/8)*13,9)<=5)&((vein+capillary+mineral+mica)>.11)
    return _resize(np.stack((bed,vein,capillary,mineral,mica,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((rose&parcel).astype(np.float32),h,w)


def render_h10(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_rose(h,w)
    bed,vein,capillary,mineral,mica,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.21,.19,.17)
    stone=np.stack((.58+.18*bed+.05*tier,.52+.18*bed+.04*tier,.46+.16*bed+.03*tier),2)
    paint=paint*.26+stone*.74
    paint=paint*(1-vein[...,None]*.53)+np.asarray((.22,.11,.23),np.float32)*(vein[...,None]*.53)
    paint=paint*(1-capillary[...,None]*.31)+np.asarray((.66,.31,.42),np.float32)*(capillary[...,None]*.31)
    paint=paint*(1-mineral[...,None]*.22)+np.asarray((.27,.57,.61),np.float32)*(mineral[...,None]*.22)
    paint=paint*(1-mica[...,None]*.20)+np.asarray((.90,.72,.34),np.float32)*(mica[...,None]*.20)
    metal=27+45*bed+89*vein+66*capillary+54*mineral+83*mica+48*tier; rough=223-39*bed-83*vein-61*capillary-42*mineral-71*mica-52*tier; coat=31+52*bed+91*vein+63*capillary+50*mineral+86*mica+62*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(253,18,199,242,47,169,247,83),default=166).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(8,232,44,18,187,71,25,157),default=72).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(254,29,162,243,66,120,244,78),default=153).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h10_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h10,paint,shape,mask,pm)


def h10_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h10,shape,mask)


def _carrier_and_crown(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Navy brass-patina rays with a crown held strictly in material cells."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Off-canvas radial etching prevents a wallpaper repeat.  Fine ray lips,
    # broken teeth, pinprick inlays and radial brush cuts fill the car surface.
    dx=x+ww*.17; dy=y-wh*1.13; a=np.arctan2(dy,dx); r=np.sqrt(dx*dx+dy*dy)
    ray=.5+.5*np.sin(a*42+r*.0035)
    lip=np.clip((.11-np.abs(np.sin(a*79+r*.007)))*8.4,0,1)
    tooth=np.clip((.32-np.abs(np.sin(a*26-r*.026)))*3.1,0,1)*(.25+.75*lip)
    brush=np.clip((.13-np.abs(np.sin(r*.108+a*5.7)))*7.7,0,1)
    inlay=(np.mod(np.floor(a*117)+np.floor(r/14)*23,13)<2).astype(np.float32)*brush
    local=np.mod(np.floor(a*93)*19+np.floor(r/11)*37+np.floor((r+a*40)/29)*5,9).astype(np.float32)
    # Crown has a shallow base, three unequal peaks and cap gems.  It is only a
    # material mask broken into the existing radial features, never RGB ink.
    base=(np.abs(X-.50)<.27)&(Y>.59)&(Y<.69)
    p1=(X>.27)&(X<.43)&(Y>.34)&(Y<.61)&(Y>.61-(X-.27)*1.55)
    p2=(X>.43)&(X<.57)&(Y>.25)&(Y<.61)&(Y>.61-np.abs(X-.50)*2.55)
    p3=(X>.57)&(X<.74)&(Y>.35)&(Y<.61)&(Y>.61-(.74-X)*1.45)
    gems=(((X-.35)/.035)**2+((Y-.60)/.035)**2<1.)|(((X-.50)/.04)**2+((Y-.56)/.04)**2<1.)|(((X-.65)/.035)**2+((Y-.60)/.035)**2<1.)
    crown=base|p1|p2|p3|gems
    parcel=(np.mod(np.floor(a*89)*11+np.floor(r/9)*7,9)<=5)&((lip+tooth+brush+inlay)>.11)
    return _resize(np.stack((ray,lip,tooth,brush,inlay,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((crown&parcel).astype(np.float32),h,w)


def render_h11(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_crown(h,w)
    ray,lip,tooth,brush,inlay,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.010,.030,.068)
    patina=np.stack((.045+.07*ray+.05*tier,.11+.12*ray+.06*tier,.19+.17*ray+.08*tier),2)
    paint=paint*.38+patina*.62
    paint=paint*(1-lip[...,None]*.54)+np.asarray((.78,.51,.15),np.float32)*(lip[...,None]*.54)
    paint=paint*(1-tooth[...,None]*.33)+np.asarray((.30,.69,.61),np.float32)*(tooth[...,None]*.33)
    paint=paint*(1-brush[...,None]*.20)+np.asarray((.40,.25,.09),np.float32)*(brush[...,None]*.20)
    paint=paint*(1-inlay[...,None]*.18)+np.asarray((.89,.76,.38),np.float32)*(inlay[...,None]*.18)
    metal=22+58*ray+94*lip+71*tooth+43*brush+79*inlay+50*tier; rough=231-53*ray-91*lip-69*tooth-34*brush-73*inlay-55*tier; coat=27+64*ray+96*lip+72*tooth+41*brush+84*inlay+63*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(254,17,202,245,44,173,249,80),default=164).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(7,235,41,17,190,68,23,160),default=70).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,27,159,247,63,115,247,75),default=151).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h11_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h11,paint,shape,mask,pm)


def h11_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h11,shape,mask)


def _carrier_and_eye(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Glacier-mercury crackfield whose eye is material-only."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Two displaced frozen flows make a non-repeating full-car surface.  Each
    # supplies 8–32px crack lips, step-shards, cold windows, mercury seams and mica.
    u=x+65*np.sin(y*.012)+17*np.sin(y*.051); v=y+37*np.sin(x*.018)
    flow=.5+.5*np.sin(u*.015+v*.009)
    crack=np.clip((.09-np.abs(np.sin(u*.092+np.sin(v*.026))))*9.5,0,1)
    shard=np.clip((.38-np.abs(np.sin(u*.16-v*.091)))*2.65,0,1)
    window=np.clip((.18-np.abs(np.sin(u*.039+v*.078)))*5.4,0,1)
    mercury=np.clip((.07-np.abs(np.sin(u*.27+v*.12)))*13.,0,1)*(.22+.78*crack)
    mica=(np.mod(np.floor(u/13)*31+np.floor(v/10)*11,19)<2).astype(np.float32)*window
    local=np.mod(np.floor(u/10)*19+np.floor(v/8)*41+np.floor((u+v)/31)*7,9).astype(np.float32)
    # Eye anatomy is material geometry only: almond lid, iris ring, pupil
    # subtraction and fine lower lid.  Parcel breaks deny a decal-like solid outline.
    ex=(X-.50)/.30; ey=(Y-.49)/.135; almond=ex*ex+ey*ey<1.
    iris=((X-.50)/.115)**2+((Y-.49)/.115)**2<1.; pupil=((X-.50)/.047)**2+((Y-.49)/.047)**2<1.
    upper=(np.abs(Y-.37-.12*np.cos((X-.50)*8))<.017)&(np.abs(X-.50)<.28)
    lower=(np.abs(Y-.61+.09*np.cos((X-.50)*8))<.015)&(np.abs(X-.50)<.25)
    eye=(almond&~iris)|(iris&~pupil)|upper|lower
    parcel=(np.mod(np.floor(u/9)*13+np.floor(v/8)*5,9)<=5)&((crack+shard+window+mercury+mica)>.12)
    return _resize(np.stack((flow,crack,shard,window,mercury,mica,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((eye&parcel).astype(np.float32),h,w)


def render_h12(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_eye(h,w)
    flow,crack,shard,window,mercury,mica,tier=(field[...,i] for i in range(7))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.046,.086,.11)
    ice=np.stack((.26+.23*flow+.06*tier,.44+.24*flow+.05*tier,.53+.24*flow+.07*tier),2)
    paint=paint*.28+ice*.72
    paint=paint*(1-crack[...,None]*.55)+np.asarray((.78,.88,.93),np.float32)*(crack[...,None]*.55)
    paint=paint*(1-shard[...,None]*.31)+np.asarray((.15,.38,.72),np.float32)*(shard[...,None]*.31)
    paint=paint*(1-window[...,None]*.24)+np.asarray((.31,.76,.83),np.float32)*(window[...,None]*.24)
    paint=paint*(1-mercury[...,None]*.28)+np.asarray((.39,.46,.54),np.float32)*(mercury[...,None]*.28)
    paint=paint*(1-mica[...,None]*.18)+np.asarray((.95,.86,.58),np.float32)*(mica[...,None]*.18)
    metal=31+49*flow+90*crack+68*shard+53*window+81*mercury+63*mica+49*tier; rough=218-42*flow-87*crack-64*shard-46*window-76*mercury-57*mica-53*tier; coat=36+57*flow+93*crack+70*shard+55*window+88*mercury+61*mica+63*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,16,205,248,40,177,252,76),default=160).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(6,238,38,16,194,65,21,164),default=68).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,24,156,250,58,109,250,71),default=148).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h12_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h12,paint,shape,mask,pm)


def h12_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h12,shape,mask)


def _carrier_and_starburst(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Midnight comet trails with a starburst hidden in material response."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Three purposefully different bent meteor tracks are composed of narrow
    # 8–32px cores, halos, tail dashes, cold scratches and tiny dust sparks.
    d1=np.abs(y-(wh*.20+.00031*(x-ww*.22)**2)); d2=np.abs(y-(wh*.76-.00023*(x-ww*.72)**2)); d3=np.abs(y-(wh*.49+26*np.sin(x*.014)))
    core=np.maximum.reduce((np.clip((7-d1)/7,0,1),np.clip((6-d2)/6,0,1),np.clip((5-d3)/5,0,1)))
    halo=np.maximum.reduce((np.clip((22-d1)/22,0,1),np.clip((18-d2)/18,0,1),np.clip((16-d3)/16,0,1)))
    dash=np.clip((.50-np.abs(np.sin(x*.14+y*.043)))*2.15,0,1)*halo
    scratch=np.clip((.11-np.abs(np.sin(x*.033-y*.081)))*7.,0,1)
    dust=(np.mod(np.floor(x/15)*17+np.floor(y/12)*29,23)<2).astype(np.float32)*np.clip(.35+.65*halo,0,1)
    local=np.mod(np.floor(x/10)*31+np.floor(y/8)*43+np.floor((x+y)/27)*5,9).astype(np.float32)
    cx=X-.50; cy=Y-.49; r=np.sqrt(cx*cx+cy*cy); a=np.arctan2(cy,cx)
    # Eight broken rays and a small nucleus form a starburst only in M/R/Cc.
    ray=(np.abs(np.sin(a*4))<.18)&(r>.055)&(r<.31)
    nucleus=r<.09; burst=ray|nucleus
    parcel=(np.mod(np.floor(x/9)*7+np.floor(y/8)*11,9)<=7)&((core+halo+dash+scratch+dust)>.11)
    return _resize(np.stack((core,halo,dash,scratch,dust,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((burst&parcel).astype(np.float32),h,w)


def render_h13(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_starburst(h,w)
    core,halo,dash,scratch,dust,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.006,.011,.040)
    night=np.stack((.02+.04*tier,.03+.07*tier,.11+.13*tier),2)
    paint=paint*.54+night*.46
    paint=paint*(1-halo[...,None]*.31)+np.asarray((.08,.12,.31),np.float32)*(halo[...,None]*.31)
    paint=paint*(1-core[...,None]*.74)+np.asarray((.54,.78,.98),np.float32)*(core[...,None]*.74)
    paint=paint*(1-dash[...,None]*.36)+np.asarray((.20,.48,.91),np.float32)*(dash[...,None]*.36)
    paint=paint*(1-scratch[...,None]*.18)+np.asarray((.50,.24,.73),np.float32)*(scratch[...,None]*.18)
    paint=paint*(1-dust[...,None]*.14)+np.asarray((.93,.75,.34),np.float32)*(dust[...,None]*.14)
    metal=21+43*halo+94*core+66*dash+45*scratch+77*dust+51*tier; rough=235-37*halo-91*core-64*dash-37*scratch-71*dust-55*tier; coat=24+47*halo+98*core+68*dash+49*scratch+82*dust+64*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,15,208,250,37,181,254,72),default=157).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(5,241,35,15,198,61,19,168),default=66).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,22,153,252,54,104,252,67),default=145).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h13_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h13,paint,shape,mask,pm)


def h13_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h13,shape,mask)


def _carrier_and_ankh(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Verdigris copper etching with a secret material-only ankh."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Uneven etched copper planes are full-canvas and non-uniform: subtle arch
    # bands, 8–32px intaglio lips, oxidized pools, dot rivets, filigree cuts.
    u=x*.87+y*.24+31*np.sin(y*.013); v=-x*.19+y*.91+23*np.sin(x*.016)
    patina=.5+.5*np.sin(u*.014+v*.010)
    etch=np.clip((.10-np.abs(np.sin(u*.083+np.sin(v*.021))))*8.8,0,1)
    filigree=np.clip((.08-np.abs(np.sin(v*.112+u*.037)))*10.8,0,1)
    pool=np.clip((.21-np.abs(np.sin(u*.028-v*.052)))*4.75,0,1)
    rivet=(np.mod(np.floor(u/14)*13+np.floor(v/13)*31,17)<2).astype(np.float32)*pool
    scratch=np.clip((.052-np.abs(np.sin(u*.28-v*.16)))*17.,0,1)*(.25+.75*etch)
    local=np.mod(np.floor(u/10)*17+np.floor(v/9)*37+np.floor((u-v)/29)*7,9).astype(np.float32)
    # Ankh loop, crossbar and stem use local copper details only; there is no
    # ankh color in the source RGB carrier.
    loop=((X-.50)/.105)**2+((Y-.35)/.13)**2<1.; hole=((X-.50)/.052)**2+((Y-.35)/.070)**2<1.
    bar=(np.abs(X-.50)<.22)&(Y>.47)&(Y<.53); stem=(np.abs(X-.50)<.052)&(Y>.50)&(Y<.76)
    ankh=(loop&~hole)|bar|stem
    parcel=(np.mod(np.floor(u/9)*11+np.floor(v/8)*7,9)<=6)&((etch+filigree+pool+rivet+scratch)>.12)
    return _resize(np.stack((patina,etch,filigree,pool,rivet,scratch,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((ankh&parcel).astype(np.float32),h,w)


def render_h14(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_ankh(h,w)
    patina,etch,filigree,pool,rivet,scratch,tier=(field[...,i] for i in range(7))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.090,.045,.018)
    copper=np.stack((.29+.22*patina+.06*tier,.11+.11*patina+.04*tier,.030+.045*patina+.02*tier),2)
    paint=paint*.33+copper*.67
    paint=paint*(1-etch[...,None]*.48)+np.asarray((.80,.37,.10),np.float32)*(etch[...,None]*.48)
    paint=paint*(1-filigree[...,None]*.34)+np.asarray((.12,.57,.51),np.float32)*(filigree[...,None]*.34)
    paint=paint*(1-pool[...,None]*.28)+np.asarray((.07,.32,.29),np.float32)*(pool[...,None]*.28)
    paint=paint*(1-rivet[...,None]*.21)+np.asarray((.91,.65,.22),np.float32)*(rivet[...,None]*.21)
    paint=paint*(1-scratch[...,None]*.16)+np.asarray((.46,.20,.055),np.float32)*(scratch[...,None]*.16)
    metal=31+55*patina+88*etch+63*filigree+49*pool+82*rivet+44*scratch+50*tier; rough=224-48*patina-85*etch-59*filigree-41*pool-75*rivet-34*scratch-54*tier; coat=33+57*patina+92*etch+65*filigree+47*pool+86*rivet+41*scratch+63*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,14,211,252,34,185,255,68),default=154).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(4,244,32,14,201,57,17,171),default=64).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,20,150,254,50,99,255,63),default=142).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h14_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h14,paint,shape,mask,pm)


def h14_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h14,shape,mask)


def _carrier_and_keyhole(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Cobalt porcelain filigree with a material-only keyhole revelation."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # A deliberately complete antique porcelain carrier: fine blue scrollwork,
    # kiln-crazing, enamel cells, gold pinpoints and fine inlay lashes.
    u=x+34*np.sin(y*.017)+12*np.sin(y*.061); v=y+25*np.sin(x*.021)
    scroll=np.clip((.105-np.abs(np.sin(u*.072+np.sin(v*.031))))*8.1,0,1)
    craze=np.clip((.052-np.abs(np.sin(u*.236-v*.141)))*17.0,0,1)
    cell=np.clip((.18-np.abs(np.sin(u*.038+v*.061)))*5.25,0,1)
    lash=np.clip((.075-np.abs(np.sin(v*.121-u*.029)))*11.2,0,1)*cell
    gold=(np.mod(np.floor(u/12)*23+np.floor(v/11)*17,19)<2).astype(np.float32)*(.20+.80*cell)
    local=np.mod(np.floor(u/9)*29+np.floor(v/8)*17+np.floor((u+v)/25)*11,9).astype(np.float32)
    # The keyhole has no paint allocation. Its circle, shoulder and narrow
    # shaft exist only as broken high-contrast material parcels.
    knob=((X-.50)/.115)**2+((Y-.39)/.115)**2<1.
    shaft=(np.abs(X-.50)<.052)&(Y>.43)&(Y<.72)
    shoulder=(np.abs(X-.50)<(.17-(Y-.43)*.54))&(Y>.43)&(Y<.54)
    keyhole=knob|shaft|shoulder
    # Restrict the secret to existing scroll/lash/gold detail parcels.  This
    # keeps the keyhole from reading as a broad neutral-light silhouette while
    # retaining enough discontinuous material for a grazing discovery.
    parcel=(np.mod(np.floor(u/8)*7+np.floor(v/9)*13,9)<=5)&((scroll+lash+gold)>.16)
    return _resize(np.stack((scroll,craze,cell,lash,gold,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((keyhole&parcel).astype(np.float32),h,w)


def render_h15(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_keyhole(h,w)
    scroll,craze,cell,lash,gold,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.045,.070,.090)
    porcelain=np.stack((.42+.18*cell+.06*tier,.55+.19*cell+.05*tier,.61+.20*cell+.06*tier),2)
    paint=paint*.22+porcelain*.78
    paint=paint*(1-scroll[...,None]*.42)+np.asarray((.025,.12,.47),np.float32)*(scroll[...,None]*.42)
    paint=paint*(1-craze[...,None]*.29)+np.asarray((.10,.19,.31),np.float32)*(craze[...,None]*.29)
    paint=paint*(1-cell[...,None]*.19)+np.asarray((.63,.76,.78),np.float32)*(cell[...,None]*.19)
    paint=paint*(1-lash[...,None]*.30)+np.asarray((.06,.35,.62),np.float32)*(lash[...,None]*.30)
    paint=paint*(1-gold[...,None]*.20)+np.asarray((.88,.60,.18),np.float32)*(gold[...,None]*.20)
    metal=24+72*scroll+43*craze+55*cell+76*lash+91*gold+47*tier; rough=232-65*scroll-32*craze-49*cell-72*lash-84*gold-51*tier; coat=27+76*scroll+42*craze+59*cell+79*lash+96*gold+61*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,13,215,253,31,188,255,65),default=151).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(4,245,31,13,203,54,16,174),default=62).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,19,149,255,47,97,255,59),default=139).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h15_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h15,paint,shape,mask,pm)


def h15_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h15,shape,mask)


def _carrier_and_compass(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Black-opal mineral lacquer with a fractured material-only compass rose."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # This carrier has no broad wallpaper device: the visible opal comes from
    # fine mineral threads, scale pockets, micro-fissures, chips and pin-fire.
    u=x*.91+y*.18+27*np.sin(y*.016)+9*np.sin(y*.067); v=-x*.16+y*.94+19*np.sin(x*.023)
    thread=np.clip((.065-np.abs(np.sin(u*.177+np.sin(v*.081))))*14.5,0,1)
    pocket=np.clip((.26-np.abs(np.sin(u*.041-v*.073)))*3.65,0,1)
    fissure=np.clip((.041-np.abs(np.sin(u*.291-v*.157)))*21.5,0,1)
    chip=np.clip((.17-np.abs(np.sin(u*.114+v*.132)))*5.5,0,1)*pocket
    fire=(np.mod(np.floor(u/11)*37+np.floor(v/9)*19,23)<2).astype(np.float32)*(.20+.80*(pocket+chip))
    local=np.mod(np.floor(u/8)*31+np.floor(v/10)*23+np.floor((u-v)/27)*13,9).astype(np.float32)
    cx=X-.50; cy=Y-.49; r=np.sqrt(cx*cx+cy*cy); angle=np.arctan2(cy,cx)
    # N/E/S/W points plus intercardinal cuts, a broken ring, and an off-centre
    # needle form the compass only as fractured material cells.
    cardinal=(np.abs(np.sin(angle*4))<.13)&(r>.075)&(r<.34)
    intercardinal=(np.abs(np.cos(angle*4))<.09)&(r>.12)&(r<.27)
    ring=(np.abs(r-.205)<.014)
    needle=(np.abs(cx+.022*cy)<.027)&(r<.31)&(r>.045)
    compass=cardinal|intercardinal|ring|needle
    parcel=(np.mod(np.floor(u/8)*11+np.floor(v/9)*7,9)<=5)&((thread+pocket+fissure+chip+fire)>.15)
    return _resize(np.stack((thread,pocket,fissure,chip,fire,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((compass&parcel).astype(np.float32),h,w)


def render_h16(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_compass(h,w)
    thread,pocket,fissure,chip,fire,tier=(field[...,i] for i in range(6))
    # H16-I2: raise only the ordinary opal-pocket compass carrier so it reads
    # in catalog light; all hidden compass geometry remains spec-only.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.014,.022,.036)
    opal=np.stack((.045+.085*pocket+.035*tier,.070+.120*pocket+.052*tier,.115+.175*pocket+.085*tier),2)
    paint=paint*.46+opal*.54
    paint=paint*(1-thread[...,None]*.45)+np.asarray((.08,.63,.67),np.float32)*(thread[...,None]*.45)
    paint=paint*(1-fissure[...,None]*.25)+np.asarray((.30,.10,.54),np.float32)*(fissure[...,None]*.25)
    paint=paint*(1-chip[...,None]*.32)+np.asarray((.12,.28,.52),np.float32)*(chip[...,None]*.32)
    paint=paint*(1-fire[...,None]*.22)+np.asarray((.94,.49,.15),np.float32)*(fire[...,None]*.22)
    metal=17+84*thread+52*pocket+38*fissure+71*chip+96*fire+54*tier; rough=240-80*thread-47*pocket-33*fissure-67*chip-89*fire-58*tier; coat=20+88*thread+57*pocket+41*fissure+75*chip+101*fire+66*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,12,218,254,29,190,255,62),default=149).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(3,246,29,12,205,52,15,176),default=60).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,18,147,255,45,95,255,57),default=136).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h16_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h16,paint,shape,mask,pm)


def h16_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h16,shape,mask)


def _carrier_and_helix(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Liquid-chrome peacock lacquer with a material-only DNA helix."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Fluid chrome is built from narrow flow lips, oil interference cells,
    # micro-beads, etched scratches and bright droplet facets—not a flat foil.
    u=x+8*np.sin(y*.083)+5*np.sin(x*.071+y*.137)+3*np.sin(y*.419)
    v=y+7*np.sin(x*.097)+4*np.sin(x*.163-y*.059)
    # Irregular small chrome grain: phase is changed by larger, non-aligned
    # cells so the field cannot read as a generic repeated stripe wallpaper.
    gx=np.floor(x/19); gy=np.floor(y/17)
    phase=np.mod(np.sin(gx*127.1+gy*311.7)*43758.5453,1.)*6.283
    phase2=np.mod(np.sin(gx*269.5-gy*183.3)*12415.873,1.)*6.283
    lip=np.clip((.052-np.abs(np.sin(u*.49+.46*np.sin(v*.19+phase))))*18.3,0,1)
    oil=.5+.5*np.sin(u*.34-v*.47+.72*np.sin(v*.23+phase2))
    bead=np.clip((.15-np.abs(np.sin(u*.41+v*.58+phase)))*6.7,0,1)
    etch=np.clip((.031-np.abs(np.sin(u*.83-v*.51+phase2)))*28.5,0,1)
    facet=(np.mod(np.floor(u/5)*17+np.floor(v/6)*41+np.floor(phase*7),21)<2).astype(np.float32)*(.16+.84*bead)
    local=np.mod(np.floor(u/5)*37+np.floor(v/6)*19+np.floor((u+v)/12)*7+np.floor(phase*11),9).astype(np.float32)
    # The helix strands, intermittent rungs, and central void are material
    # geometry only; paint receives no DNA silhouette or colour allocation.
    phase=(Y-.50)*21.5
    left=.50-.125*np.sin(phase); right=.50+.125*np.sin(phase)
    strand=(np.abs(X-left)<.016)|(np.abs(X-right)<.016)
    rung=(np.abs(np.sin(phase*.63))<.105)&(X>np.minimum(left,right))&(X<np.maximum(left,right))
    central=(np.abs(X-.50)<.018)&(np.abs(np.cos(phase))<.24)
    helix=(strand|rung)&~central
    parcel=(np.mod(np.floor(u/8)*13+np.floor(v/9)*5,9)<=5)&((lip+bead+etch+facet)>.13)
    return _resize(np.stack((lip,oil,bead,etch,facet,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((helix&parcel).astype(np.float32),h,w)


def render_h17(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_helix(h,w)
    lip,oil,bead,etch,facet,tier=(field[...,i] for i in range(6))
    # H17-I2: expose the normal liquid-chrome helix carrier in neutral light;
    # helix silhouette and all secret material transitions stay untouched.
    paint=np.empty((h,w,3),np.float32); paint[:]=(.035,.045,.058)
    chrome=np.stack((.16+.16*oil+.055*tier,.20+.18*oil+.052*tier,.26+.21*oil+.068*tier),2)
    paint=paint*.34+chrome*.66
    paint=paint*(1-lip[...,None]*.42)+np.asarray((.50,.74,.82),np.float32)*(lip[...,None]*.42)
    peacock=np.stack((.08+.16*oil,.035+.09*(1-oil),.15+.20*(1-oil)),2)
    paint=paint*.87+peacock*.13
    paint=paint*(1-bead[...,None]*.25)+np.asarray((.58,.24,.67),np.float32)*(bead[...,None]*.25)
    paint=paint*(1-etch[...,None]*.18)+np.asarray((.05,.42,.48),np.float32)*(etch[...,None]*.18)
    paint=paint*(1-facet[...,None]*.17)+np.asarray((.82,.53,.14),np.float32)*(facet[...,None]*.17)
    metal=42+79*lip+54*oil+71*bead+43*etch+94*facet+48*tier; rough=211-75*lip-48*oil-67*bead-38*etch-87*facet-53*tier; coat=45+83*lip+57*oil+75*bead+46*etch+99*facet+62*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,11,221,255,27,193,255,59),default=146).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(3,247,27,11,207,49,14,178),default=58).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,17,145,255,43,93,255,55),default=133).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h17_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h17,paint,shape,mask,pm)


def h17_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h17,shape,mask)


def _carrier_and_firebird(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Iridescent liquid-carbon carrier with a material-only firebird glyph."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Two off-canvas liquid interference centres prevent a tiled field. Fine
    # ripple lips, oil bands, tiny prism pools, fracture cuts and micro flakes
    # form the visible Oil-Slick-like carbon finish at native detail scale.
    da=np.hypot(x-ww*.17,y-wh*.29); db=np.hypot(x-ww*.83,y-wh*.71)
    aa=np.arctan2(y-wh*.29,x-ww*.17); ab=np.arctan2(y-wh*.71,x-ww*.83)
    ripple=np.clip((.054-np.abs(np.sin(da*.52+aa*2.3+db*.11)))*17.8,0,1)
    band=.5+.5*np.sin(da*.27-db*.23+aa*1.6-ab*.9)
    prism=np.clip((.15-np.abs(np.sin(da*.38+db*.31+aa*3.2)))*6.45,0,1)
    cut=np.clip((.032-np.abs(np.sin((x*.67-y*.48)+np.sin(da*.17)*5)))*28.8,0,1)
    flake=(np.mod(np.floor(x/6)*29+np.floor(y/7)*37+np.floor(da/13)*11,27)<2).astype(np.float32)*(.16+.84*prism)
    local=np.mod(np.floor(x/5)*31+np.floor(y/6)*17+np.floor(da/9)*7+np.floor(db/11)*13,9).astype(np.float32)
    # A wide broken wing pair, small crown/head, body and tapered tail form a
    # firebird only in M/R/Cc. Feather segmentation is material parceling.
    body=(np.abs(X-.50)<.040)&(Y>.40)&(Y<.73)
    head=((X-.50)/.065)**2+((Y-.35)/.060)**2<1.
    crown=(Y<.35)&(Y>.25)&(np.abs(X-.50)<(.10-(.35-Y)*.48))
    lx=.50-X; rx=X-.50
    left=(lx>.03)&(lx<.39)&(Y>.30)&(Y<.73)&(np.abs(Y-(.66-.72*lx+.22*np.sin(lx*21)))<(.022+.022*lx))
    right=(rx>.03)&(rx<.39)&(Y>.30)&(Y<.73)&(np.abs(Y-(.66-.72*rx+.22*np.sin(rx*21)))<(.022+.022*rx))
    tail=(Y>.69)&(Y<.88)&(np.abs(X-.50)<(.105-(Y-.69)*.42))
    firebird=body|head|crown|left|right|tail
    parcel=(np.mod(np.floor(x/7)*11+np.floor(y/8)*13+np.floor(da/10)*5,9)<=5)&((ripple+prism+cut+flake)>.13)
    return _resize(np.stack((ripple,band,prism,cut,flake,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((firebird&parcel).astype(np.float32),h,w)


def render_h18(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_firebird(h,w)
    ripple,band,prism,cut,flake,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.007,.009,.013)
    carbon=np.stack((.025+.075*band+.04*tier,.030+.085*band+.05*tier,.050+.12*band+.075*tier),2)
    paint=paint*.43+carbon*.57
    oil=np.stack((.06+.22*band,.03+.16*(1-band),.12+.30*(1-band)),2)
    paint=paint*.73+oil*.27
    paint=paint*(1-ripple[...,None]*.43)+np.asarray((.12,.74,.76),np.float32)*(ripple[...,None]*.43)
    paint=paint*(1-prism[...,None]*.27)+np.asarray((.72,.16,.61),np.float32)*(prism[...,None]*.27)
    paint=paint*(1-cut[...,None]*.21)+np.asarray((.38,.10,.08),np.float32)*(cut[...,None]*.21)
    paint=paint*(1-flake[...,None]*.18)+np.asarray((.92,.61,.13),np.float32)*(flake[...,None]*.18)
    metal=23+88*ripple+52*band+72*prism+39*cut+95*flake+50*tier; rough=234-83*ripple-47*band-68*prism-34*cut-88*flake-55*tier; coat=26+92*ripple+56*band+76*prism+42*cut+100*flake+64*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,10,224,255,25,196,255,56),default=143).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(2,248,25,10,210,46,13,181),default=55).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,16,143,255,41,91,255,52),default=130).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h18_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h18,paint,shape,mask,pm)


def h18_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h18,shape,mask)


def _carrier_and_trident(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deep-ocean ceramic/coral material carrier with a hidden broken trident."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Coral ceramic avoids broad waves: its field is a set of fine porous
    # cells, salt fissures, nacre crescents, algae cuts and dark depth pockets.
    u=x+9*np.sin(y*.091)+4*np.sin(x*.137-y*.053); v=y+7*np.sin(x*.079)
    gx=np.floor(x/17); gy=np.floor(y/19)
    phase=np.mod(np.sin(gx*171.7+gy*93.1)*37131.487,1.)*6.283
    phase2=np.mod(np.sin(gx*51.3-gy*287.9)*19013.531,1.)*6.283
    pore=np.clip((.17-np.abs(np.sin(u*.39+v*.57+phase)))*5.9,0,1)
    salt=np.clip((.034-np.abs(np.sin(u*.81-v*.63+np.sin(v*.22+phase2))))*26.5,0,1)
    crescent=np.clip((.052-np.abs(np.sin(u*.31+np.sin(v*.18+phase))))*17.0,0,1)*pore
    algae=np.clip((.046-np.abs(np.sin(u*.59-v*.37+phase2)))*20.2,0,1)
    depth=.5+.5*np.sin(u*.19+v*.23+np.sin(u*.11+phase)*.8)
    local=np.mod(np.floor(u/5)*19+np.floor(v/6)*31+np.floor((u-v)/13)*11+np.floor(phase*13),9).astype(np.float32)
    # The trident's centre spear, outward side spears, bar and pointed crown
    # are only a material-location mask; none of this changes source RGB.
    shaft=(np.abs(X-.50)<.030)&(Y>.34)&(Y<.79)
    bar=(Y>.57)&(Y<.61)&(np.abs(X-.50)<.205)
    left=np.abs(X-(.34+.19*(Y-.34)))<.027
    right=np.abs(X-(.66-.19*(Y-.34)))<.027
    prongY=(Y>.23)&(Y<.61)
    tips=((np.abs(X-.50)<(.06-(Y-.23)*.42))|(np.abs(X-.34)<(.05-(Y-.28)*.30))|(np.abs(X-.66)<(.05-(Y-.28)*.30)))&(Y>.23)&(Y<.34)
    trident=shaft|bar|((left|right)&prongY)|tips
    parcel=(np.mod(np.floor(u/6)*7+np.floor(v/7)*17,9)<=5)&((pore+salt+crescent+algae)>.12)
    return _resize(np.stack((pore,salt,crescent,algae,depth,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((trident&parcel).astype(np.float32),h,w)


def render_h19(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_trident(h,w)
    pore,salt,crescent,algae,depth,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32); paint[:]=(.008,.024,.033)
    ceramic=np.stack((.025+.055*depth+.025*tier,.10+.16*depth+.04*tier,.14+.21*depth+.06*tier),2)
    paint=paint*.30+ceramic*.70
    paint=paint*(1-pore[...,None]*.33)+np.asarray((.08,.32,.37),np.float32)*(pore[...,None]*.33)
    paint=paint*(1-salt[...,None]*.26)+np.asarray((.62,.77,.72),np.float32)*(salt[...,None]*.26)
    paint=paint*(1-crescent[...,None]*.30)+np.asarray((.18,.66,.71),np.float32)*(crescent[...,None]*.30)
    paint=paint*(1-algae[...,None]*.21)+np.asarray((.08,.42,.29),np.float32)*(algae[...,None]*.21)
    metal=18+57*pore+83*salt+71*crescent+48*algae+52*depth+50*tier; rough=238-51*pore-78*salt-66*crescent-42*algae-47*depth-54*tier; coat=21+61*pore+87*salt+75*crescent+51*algae+56*depth+63*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,9,226,255,23,198,255,53),default=140).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(2,249,23,9,212,44,12,183),default=53).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,15,141,255,39,89,255,50),default=127).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h19_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h19,paint,shape,mask,pm)


def h19_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h19,shape,mask)


def _carrier_and_scarab(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lapis micro-marquetry with a hidden scarab in fractured material states."""
    wh=max(96,int(round(h*_WORK/max(h,w)))); ww=max(96,int(round(w*_WORK/max(h,w))))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32); X=x/ww; Y=y/wh
    # Small interlocked marquetry tiles give every 8–32px region a distinct
    # visible and material personality: lapis, pearl, gold leaf, dark stone,
    # enamel, bevels, hairline inlay and controlled chip marks.
    u=x*.92+y*.17+4*np.sin(y*.19); v=-x*.14+y*.95+3*np.sin(x*.23)
    gx=np.floor(u/7).astype(np.int32); gy=np.floor(v/7).astype(np.int32)
    fx=np.mod(u/7,1.); fy=np.mod(v/7,1.)
    edge=np.clip((.12-np.minimum(np.minimum(fx,1-fx),np.minimum(fy,1-fy)))*8.4,0,1)
    code=np.mod(gx*17+gy*31+gx*gy*7,11).astype(np.float32)
    bevel=np.clip((.065-np.abs(fx-fy))*15.4,0,1)*(.30+.70*(code%2))
    inlay=np.clip((.035-np.abs(np.sin(u*.92+v*.71)))*26.5,0,1)
    chip=(np.mod(gx*41+gy*13,17)<2).astype(np.float32)*np.clip((.25-np.abs(fx-.5)-np.abs(fy-.5))*4.1,0,1)
    local=np.mod(gx*29+gy*19+np.floor((u-v)/9)*11,9).astype(np.float32)
    # Scarab anatomy remains a material-only assembly: shield shell, head,
    # wing seam, small legs and antennae all broken through existing tiles.
    shell=((X-.50)/.16)**2+((Y-.54)/.23)**2<1.
    head=((X-.50)/.075)**2+((Y-.31)/.065)**2<1.
    seam=(np.abs(X-.50)<.013)&(Y>.35)&(Y<.75)
    legL=(X<.42)&(X>.25)&(Y>.45)&(Y<.70)&(np.abs(Y-(.68-.66*(X-.25)))<.018)
    legR=(X>.58)&(X<.75)&(Y>.45)&(Y<.70)&(np.abs(Y-(.68-.66*(.75-X)))<.018)
    antL=(X<.49)&(X>.38)&(Y>.22)&(Y<.33)&(np.abs(Y-(.33-.72*(.49-X)))<.014)
    antR=(X>.51)&(X<.62)&(Y>.22)&(Y<.33)&(np.abs(Y-(.33-.72*(X-.51)))<.014)
    scarab=shell|head|seam|legL|legR|antL|antR
    parcel=(np.mod(gx*7+gy*11,9)<=6)&((edge+bevel+inlay+chip)>.08)
    return _resize(np.stack((edge,bevel,inlay,chip,code/10.,local/8.),2),h,w).astype(np.float32),_resize(local,h,w),_resize((scarab&parcel).astype(np.float32),h,w)


def render_h20(shape: tuple[int,int]) -> tuple[np.ndarray,np.ndarray]:
    h,w=int(shape[0]),int(shape[1]); field,local,secret=_carrier_and_scarab(h,w)
    edge,bevel,inlay,chip,code,tier=(field[...,i] for i in range(6))
    paint=np.empty((h,w,3),np.float32)
    # Eleven intentional tile families, never a generic hue-shifted copy.
    # The exposed paint is a cohesive lapis family; the wide multi-state
    # personality is deliberately reserved for M/R/Cc rather than confetti RGB.
    paint=np.stack((.014+.040*code+.012*tier,.044+.105*code+.016*tier,.095+.205*code+.028*tier),2).astype(np.float32)
    paint=paint*(1-edge[...,None]*.46)+np.asarray((.012,.024,.050),np.float32)*(edge[...,None]*.46)
    paint=paint*(1-bevel[...,None]*.31)+np.asarray((.71,.52,.16),np.float32)*(bevel[...,None]*.31)
    paint=paint*(1-inlay[...,None]*.18)+np.asarray((.48,.64,.59),np.float32)*(inlay[...,None]*.18)
    paint=paint*(1-chip[...,None]*.11)+np.asarray((.66,.43,.13),np.float32)*(chip[...,None]*.11)
    metal=18+77*edge+92*bevel+68*inlay+96*chip+49*code+52*tier; rough=240-71*edge-86*bevel-62*inlay-91*chip-44*code-55*tier; coat=21+81*edge+97*bevel+72*inlay+101*chip+53*code+65*tier
    q=np.mod(local,9)
    sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,8,229,255,21,201,255,50),default=137).astype(np.float32)
    sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(2,250,21,8,214,42,11,185),default=51).astype(np.float32)
    sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6,q==7),(255,14,139,255,37,87,255,47),default=124).astype(np.float32)
    metal=np.where(secret>0,sm,metal); rough=np.where(secret>0,sr,rough); coat=np.where(secret>0,sc,coat)
    return np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8)


def h20_paint(paint, shape, mask, seed=None, pm=1.0, bb=None):
    del seed,bb
    return _authored_paint(render_h20,paint,shape,mask,pm)


def h20_spec(shape, mask, seed=None, sm=1.0):
    del seed,sm
    return _authored_spec(render_h20,shape,mask)


LIVE_PAIRS={H1_ID:(h1_i3_spec,h1_i3_paint), H2_ID:(h2_i5_spec,h2_i5_paint), H3_ID:(h3_i4_spec,h3_i4_paint), H4_ID:(h4_i4_spec,h4_i4_paint), H5_ID:(h5_i4_spec,h5_i4_paint), H6_ID:(h6_i5_spec,h6_i5_paint), H7_ID:(h7_i4_spec,h7_i4_paint), H8_ID:(h8_i2_spec,h8_i2_paint), H9_ID:(h9_i2_spec,h9_i2_paint), H10_ID:(h10_i1_spec,h10_i1_paint), H11_ID:(h11_i1_spec,h11_i1_paint), H12_ID:(h12_i2_spec,h12_i2_paint), H13_ID:(h13_i1_spec,h13_i1_paint), H14_ID:(h14_i1_spec,h14_i1_paint), H15_ID:(h15_i1_spec,h15_i1_paint), H16_ID:(h16_i1_spec,h16_i1_paint), H17_ID:(h17_i1_spec,h17_i1_paint), H18_ID:(h18_i1_spec,h18_i1_paint), H19_ID:(h19_i1_spec,h19_i1_paint), H20_ID:(h20_i1_spec,h20_i1_paint)}

# Owner Houdini rebuild / 2026-08-30 runtime audit: catalog thumbnails and
# regular renders use a 1.5x monolithic paint boost. A material finish owns
# the entire masked surface, so coverage must saturate at 1.0 rather than
# extrapolate source-to-carrier blending into negative RGB. Centralizing this
# contract prevents a correct hidden-spec card from collapsing to black.
def _saturating_paint(paint_fn):
    def _wrapped(paint, shape, mask, seed=None, pm=1.0, bb=None):
        return paint_fn(paint, shape, mask, seed, min(1.0, max(0.0, float(pm))), bb)
    _wrapped.__name__ = getattr(paint_fn, "__name__", "houdini_paint")
    return _wrapped

LIVE_PAIRS={finish_id:(spec_fn,_saturating_paint(paint_fn)) for finish_id,(spec_fn,paint_fn) in LIVE_PAIRS.items()}


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    del base_reg,fusion_reg
    mono_reg.update(LIVE_PAIRS)
    return "fractured-houdini live development: 20 material-hidden finishes"
