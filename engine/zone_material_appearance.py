"""SPB-93: master color matching on owned paint; spec and coverage stay exact."""
import cv2
import numpy as np
from engine.zone_material_snapshot import decode, encode

MODES = ('tint','hue','saturation','vibrance')

def rgb_to_hsl(rgb):
    value=rgb.astype(np.float64)/255
    r,g,b=np.moveaxis(value,-1,0)
    high=value.max(axis=-1);low=value.min(axis=-1);delta=high-low
    light=(high+low)/2
    saturation=np.divide(delta,1-np.abs(2*light-1),out=np.zeros_like(delta),where=delta>0)
    divisor=np.where(delta>0,delta,1)
    hue=np.where(high==r,((g-b)/divisor)%6,np.where(high==g,(b-r)/divisor+2,(r-g)/divisor+4))*60
    return np.where(delta>0,hue,0),saturation,light

def hsl_to_rgb(hue,saturation,light):
    h=(hue%360)/60;c=(1-np.abs(2*light-1))*saturation
    x=c*(1-np.abs(h%2-1));zero=np.zeros_like(c)
    channels=(np.select([h<1,h<2,h<3,h<4,h<5],[c,x,zero,zero,x],default=c),
              np.select([h<1,h<2,h<3,h<4,h<5],[x,c,c,x,zero],default=zero),
              np.select([h<1,h<2,h<3,h<4,h<5],[zero,zero,x,c,c],default=x))
    rgb=np.stack(channels,axis=-1)+(light-c/2)[...,None]
    return np.clip(np.floor(rgb*255+.5),0,255).astype(np.uint8)

def match_material(target,master,mode):
    if mode not in MODES:raise ValueError('Unknown material color operation')
    paint,spec,mask,paint_mask=decode(target)
    master_paint,_,_,master_mask=decode(master)
    owned=paint_mask>0;master_owned=master_mask>0
    count=int(np.count_nonzero(owned))
    if not count or not np.any(master_owned):
        return target,dict(changedPixels=0,ownedPaintPixels=count,masterPaintPixels=int(np.count_nonzero(master_owned)))
    if mode=='tint':
        height,width=paint.shape[:2]
        aligned_mask=cv2.resize(master_mask,(width,height),interpolation=cv2.INTER_LINEAR)
        weighted=cv2.resize(master_paint.astype(np.float64)*master_mask[:,:,None],(width,height),interpolation=cv2.INTER_LINEAR)
        aligned=np.divide(weighted,aligned_mask[:,:,None],out=np.zeros_like(weighted),where=aligned_mask[:,:,None]>0)
        amount=aligned_mask[:,:,None]*.5
        updated=np.clip(np.floor(paint*(1-amount)+aligned*amount+.5),0,255).astype(np.uint8)
    else:
        mh,ms,_=rgb_to_hsl(master_paint)
        weight=master_mask.astype(np.float64)
        hue_weight=weight*ms
        has_hue=float(hue_weight.sum())>1e-8
        master_hue=np.degrees(np.arctan2((np.sin(np.radians(mh))*hue_weight).sum(),(np.cos(np.radians(mh))*hue_weight).sum()))%360
        master_sat=float((ms*weight).sum()/weight.sum())
        h,s,l=rgb_to_hsl(paint)
        if mode=='hue':
            if has_hue:h=(h+((master_hue-h+540)%360-180)*.85)%360
            s=s+(master_sat-s)*.6
        else:
            s=s+(master_sat-s)*((1-s)*.9 if mode=='vibrance' else .85)
        updated=hsl_to_rgb(h,np.clip(s,0,1),l)
    updated=np.where(owned[:,:,None],updated,paint)
    changed=int(np.count_nonzero(np.any(updated!=paint,axis=2)&owned))
    material=encode(updated,spec,mask,paint_mask) if changed else target
    return material,dict(changedPixels=changed,ownedPaintPixels=count,masterPaintPixels=int(np.count_nonzero(master_owned)))
