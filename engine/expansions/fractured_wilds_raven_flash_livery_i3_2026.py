"""Raven Flash I3 — edge-to-edge black flash-lacquer candidate (SPB-105, 2026-08-27).

I2 collapses into an almost-black generic line field. I3 is a full-canvas
automotive blade-flash construction: graphite shear blades, their own etched
grain, cold optical cuts and copper fracture tips. No template, border, photo,
noise layer or shared Wilds material carrier.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import cv2, numpy as np
ID='fmo_raven_flash'; NATIVE=2048
MT=np.asarray((8,31,59,92,127,167,210,252),np.uint8); RT=np.asarray((11,38,69,104,142,181,220,249),np.uint8); CT=np.asarray((5,27,55,86,121,160,208,253),np.uint8)
def n(a): a=a.astype(np.float32);return (a-a.min())/(a.max()-a.min()+1e-8)
def q(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def f():
 p=Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'raven_flash_livery_i3.png';raw=cv2.imread(str(p),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(p)
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(lum,cv2.CV_32F,0,1,ksize=3);edge=n(np.hypot(gx,gy));angle=(np.arctan2(gy,gx)+np.pi)/(2*np.pi);grain=n(np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.35)));shear=n(np.abs(.82*gx+.57*gy));plane=n(cv2.GaussianBlur(lum,(0,0),15.));
 cyan=np.clip((rgb[:,:,2]+.45*rgb[:,:,1]-1.04*rgb[:,:,0]-.06)/.42,0,1);violet=np.clip((rgb[:,:,2]+.32*rgb[:,:,0]-1.12*rgb[:,:,1]-.08)/.38,0,1);silver=np.clip((lum-.42+.18*(1-hsv[:,:,1]/255.))/.42,0,1);copper=np.clip((rgb[:,:,0]+.35*rgb[:,:,1]-1.15*rgb[:,:,2]-.1)/.40,0,1)
 return rgb,edge,angle,grain,shear,plane,cyan,violet,silver,copper
def _authored():
 rgb,e,a,g,s,p,cy,vi,si,cu=f();A=np.clip(rgb*.80+np.dstack((.11*cu+.05*vi,.06*cu+.08*cy,.18*cy+.13*vi)),0,1);B=np.stack((A[:,:,0]*.23+.30*vi+.13*cu,A[:,:,1]*.24+.25*cy+.12*si,A[:,:,2]*.25+.62*cy+.44*vi+.07*e),2);metal=n(.46*cy+.41*vi+.31*si+.18*e);rough=n(.53*g+.29*s+.25*e+.18*np.abs(cv2.Laplacian(p,cv2.CV_32F)));clear=n(.48*(.5+.5*np.sin(2*np.pi*(a+.19*p)))+.31*p-.19*g+.24*n(cv2.GaussianBlur(s,(0,0),9.)));return A,np.stack((q(metal,MT),q(rough,RT),q(clear,CT)),2)
