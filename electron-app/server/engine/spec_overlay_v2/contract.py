"""SPB-105 / SPEC OVERLAYS v2 tick 1, owner 2026-09-06: complete overhaul.

Legacy pixels are guarded by scripts/spb_spec_overlay_legacy_guard.py (235
goldens). New materials use explicit M/R/Cc targets plus coverage, not colored
paint and not the old shared delta transform. Quality movement belongs to the
per-design evidence; this module changes no legacy renderer.
"""
from __future__ import annotations
import hashlib,math
import cv2
import numpy as np

VERSION=2
DEFAULT_SEED=42

def active_layers(layers):
    """Mute/solo are recipe state and apply equally to legacy and v2 passes."""
    layers=layers or []
    if not any(layer.get('muted') or layer.get('solo') for layer in layers):return layers
    active=[layer for layer in layers if not layer.get('muted')]
    return [layer for layer in active if layer.get('solo')] if any(layer.get('solo') for layer in active) else active

def active_options(options):
    return {key:active_layers(value) if key.endswith('spec_pattern_stack') else value for key,value in options.items()}

def version(layer,renderer=None):
    return int((layer or {}).get('render_version',getattr(renderer,'_spb_overlay_version',1)))

def opacity(layer,renderer=None):
    if layer.get('muted',False):return 0.0
    value=float(layer.get('opacity',.5))
    if not math.isfinite(value):value=0.0
    if version(layer,renderer)>=VERSION:return min(1.,max(0.,value))
    return value**.5 if value>0 else 0.0

def seed(layer,renderer,base_seed,lane_offset):
    explicit=layer.get('seed')
    if explicit is not None:return int(explicit)&0x7fffffff
    if version(layer,renderer)>=VERSION:return DEFAULT_SEED
    # Saved unversioned recipes keep their historical behavior. New entries
    # and migrated layers store an explicit seed; do not silently recolor old work.
    return int(base_seed)+int(lane_offset)+hash(layer.get('pattern',''))%10000

def stable_id_seed(value):
    return int.from_bytes(hashlib.blake2s(str(value).encode(),digest_size=4).digest(),'little')

def apply_material(fields,M,R,Cc,strength,channels='MRC',cc_fallback=None,xp=np):
    """Apply absolute material targets through authored coverage, preserving holes.

    fields[..., :3]: M/R/Cc in 0..1; fields[..., 3]: coverage in 0..1.
    Zero strength is exact identity, including Cc=0 (no acrylic coat). This
    convex interpolation introduces no 2.5x coat gain or hidden strength curve.
    """
    strength=float(np.clip(strength,0,1))
    if strength==0 or not channels:return M,R,Cc
    coverage=xp.clip(fields[:,:,3],0,1)*strength
    if Cc is None and 'C' in channels and cc_fallback is not None:
        Cc=xp.full(fields.shape[:2],float(cc_fallback),dtype=xp.float32)
    result=[M,R,Cc]
    for i,channel in enumerate('MRC'):
        current=result[i]
        if channel not in channels or current is None:continue
        target=xp.clip(fields[:,:,i],0,1)*255.
        changed=current+(target-current)*coverage
        # Preserve unselected/transparent pixels exactly, even for values that
        # belong to the valid no-coat interval 0..15.
        result[i]=xp.where(coverage>0,xp.clip(changed,0,255),current).astype(xp.float32)
    return tuple(result)

def transform(renderer,shape,seed_value,sm,params,scale,rotation,offset_x,offset_y,box_size):
    """One native-coordinate transform for all four fields; coverage outside=0.

    Render at a bounded canonical canvas, then sample. Scale affects spatial
    detail only. Premultiplication prevents material values in transparent
    pixels from bleeding into the occupied edge during interpolation.
    """
    h,w=map(int,shape[:2]);scale=max(.05,min(5.,float(scale)))
    fields=np.asarray(renderer((h,w),seed_value,sm,**(params or {})),np.float32)
    if abs(scale-1)<1e-6 and abs(rotation)%360<1e-6 and abs(offset_x-.5)<1e-6 and abs(offset_y-.5)<1e-6 and int(box_size)>=100:return fields
    # Wrap the construction at boundaries, matching the existing tiling control.
    angle=np.deg2rad(float(rotation));co,si=np.cos(angle),np.sin(angle)
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    xx=(xx-(w-1)*.5-(float(offset_x)-.5)*w)/scale
    yy=(yy-(h-1)*.5-(float(offset_y)-.5)*h)/scale
    u=(co*xx+si*yy+(w-1)*.5).astype(np.float32)
    v=(-si*xx+co*yy+(h-1)*.5).astype(np.float32)
    premult=fields.copy();premult[:,:,:3]*=premult[:,:,3:4]
    moved=cv2.remap(premult,u,v,cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)
    cover=moved[:,:,3:4];moved[:,:,:3]=np.divide(moved[:,:,:3],np.maximum(cover,1e-8),out=np.zeros_like(moved[:,:,:3]),where=cover>1e-8)
    if int(box_size)<100:
        box=max(0.,int(box_size)/100.);cy,cx=float(offset_y)*h,float(offset_x)*w
        y,x=np.mgrid[:h,:w];inside=(abs(x-cx)<=w*box*.5)&(abs(y-cy)<=h*box*.5)
        moved[:,:,3]*=inside
    return moved.astype(np.float32,copy=False)
