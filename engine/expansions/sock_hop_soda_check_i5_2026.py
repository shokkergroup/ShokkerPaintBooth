"""Sock Hop Soda Check I5 — 1950s fountain counter enamel and chrome.

SPB-105 / owner scale audit, 2026-08-29.  32px tile faces (not the prior
~60px macro checker) are built from 3px chrome grout, 4–9px fizz bubbles,
fine ice chips and wet highlight arcs.  The readable checker rhythm is a
composition of fine physical marks, not a giant wallpaper primitive.
"""
import numpy as np
from engine.core import get_mgrid

_CACHE={}


def _field(shape,seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE:return _CACHE[key]
    h,w=shape[:2]; y,x=(a.astype(np.float32) for a in get_mgrid((h,w)))
    # 40px period tile pitch, leaving exactly 32px face after chrome grout.
    px=np.mod(x+2.4*np.sin(2*np.pi*y/307),40.0); py=np.mod(y+2.1*np.sin(2*np.pi*x/283),40.0)
    ix=np.floor((x+2.4*np.sin(2*np.pi*y/307))/40).astype(np.int32); iy=np.floor((y+2.1*np.sin(2*np.pi*x/283))/40).astype(np.int32)
    aqua=((ix+iy)&1).astype(np.float32)
    edge=np.minimum.reduce((px,40-px,py,40-py))
    grout=np.clip((4.0-edge)/3.1,0,1)
    fx=px-20; fy=py-20
    # A diagonal soda-fizz cluster in aqua cells—four different native-sized
    # bubbles, a reflected ice chip, and a very small glass glint.
    b1=np.exp(-((fx+9)**2+(fy+6)**2)/14.0); b2=np.exp(-((fx+2)**2+(fy-2)**2)/24.0)
    b3=np.exp(-((fx-8)**2+(fy-8)**2)/9.0); b4=np.exp(-((fx-12)**2+(fy+12)**2)/5.0)
    bubbles=np.clip(b1+b2+b3+b4,0,1)*aqua
    ice=np.exp(-((np.abs(fx-8)+np.abs(fy+10))**2)/22.0)*(1-aqua)
    wet=np.exp(-((fx+10)**2/5+(fy-9)**2/30))*aqua
    # Hairline counter nick follows a different repeat so it cannot become
    # repeated grain or random confetti.
    nick=np.power(.5+.5*np.sin(2*np.pi*(x/12+y/17+(seed%73)/73)),30.0)*(1-grout)
    result=tuple(np.ascontiguousarray(z,dtype=np.float32) for z in (aqua,grout,bubbles,ice,wet,nick,px,py))
    _CACHE[key]=result
    if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
    return result


def _mix(base,color,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(color,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_soda_check(paint,shape,mask,seed,pm,bb):
    del pm,bb
    aqua,grout,bubbles,ice,wet,nick,px,py=_field(shape,seed)
    col=np.empty((shape[0],shape[1],3),np.float32); col[:]=(.96,.80,.56)
    col=_mix(col,(.055,.60,.66),aqua)
    col=_mix(col,(.055,.07,.10),grout*.92)
    col=_mix(col,(.56,.98,.94),bubbles*.75)
    col=_mix(col,(1.,.96,.71),ice*.78)
    col=_mix(col,(1.,1.,.93),wet*.84)
    col=_mix(col,(.51,.19,.13),nick*.14)
    return _apply(paint,mask,np.clip(col,0,1))


def spec_soda_check(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    aqua,grout,bubbles,ice,wet,nick,px,py=_field(shape,seed)
    # Ceramic cream, glassy aqua, black-chrome grout and wet fizz vary hard
    # enough to appear as different material states under track illumination.
    M=30+128*aqua+139*grout+70*ice+199*np.clip(.31*wet+.25*bubbles+.18*nick+.16*grout+.10*ice,0,1)*sm
    R=239-121*aqua-153*grout-88*ice-132*np.clip(.29*wet+.24*bubbles+.19*nick+.16*grout+.12*ice,0,1)
    CC=18+136*aqua+162*grout+79*ice+158*np.clip(.30*wet+.24*bubbles+.19*ice+.15*nick+.12*grout,0,1)
    return tuple(np.clip(z,0,255).astype(np.float32) for z in (M,R,CC))
