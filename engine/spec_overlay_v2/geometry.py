"""Small geometry operations, not a shared surface carrier or material recipe.

SPB-105 / v2 tick 2. Owner: fine 8–32px details and unique construction.
Every design supplies its own arrangement, masks and material intervals. This
module only samples shapes and composites named features. No paint is authored.
"""
from __future__ import annotations
import numpy as np
import cv2

def sat(x):return np.clip(x,0,1).astype(np.float32)
def edge(distance,width=1.):return sat(1.0-np.abs(distance)/max(.2,width))
def disk(u,v,r):return sat((r-np.hypot(u,v))+.7)
def box(u,v,rx,ry):return sat(np.minimum(rx-np.abs(u),ry-np.abs(v))+.7)
def ring(u,v,r,width=1.3):return edge(np.hypot(u,v)-r,width)
def line(u,v,ax,ay,bx,by,width=1.):
    dx,dy=bx-ax,by-ay;t=np.clip(((u-ax)*dx+(v-ay)*dy)/np.maximum(dx*dx+dy*dy,1e-6),0,1)
    return sat(width+.7-np.hypot(u-ax-t*dx,v-ay-t*dy))

class Surface:
    def __init__(self,shape,seed):
        self.h,self.w=shape;self.seed=int(seed)
        self.x=np.arange(self.w,dtype=np.float32)[None,:]*(2048/self.w)
        self.y=np.arange(self.h,dtype=np.float32)[:,None]*(2048/self.h)
        self.rgb=np.zeros((*shape,3),np.float32);self.alpha=np.zeros(shape,np.float32)
        self.names=[]
    def cell(self,px=32.,py=None,stagger=0.,angle=0.):
        py=py or px;co,si=np.cos(angle),np.sin(angle)
        x=co*self.x+si*self.y;y=-si*self.x+co*self.y
        gy=np.floor(y/py);x=x+stagger*px*np.mod(gy,2);gx=np.floor(x/px)
        return x-gx*px-px*.5,y-gy*py-py*.5,gx,gy
    def rand(self,gx,gy,salt=0):
        a=np.asarray(gx,dtype=np.int64).astype(np.uint32)*np.uint32(73856093)
        b=np.asarray(gy,dtype=np.int64).astype(np.uint32)*np.uint32(19349663)
        v=a^b^np.uint32((self.seed*83492791+salt*2654435761)&0xffffffff)
        v^=v>>13;v*=np.uint32(1274126177);v^=v>>16
        return (v.astype(np.float32)/np.float32(4294967295.))
    def mark(self,name,mask,m,r,cc,shade=.5,coat_shade=None,rough_shade=None,coverage=1.):
        """Each named mask owns authored material intervals and shading fields."""
        a=sat(mask*coverage);t=sat(shade)
        tr=sat(rough_shade if rough_shade is not None else t)
        tc=sat(coat_shade if coat_shade is not None else t)
        # Eight authored physical stops with continuous interpolation. The
        # per-feature coordinate/shade is authored by the calling design.
        stops=np.array([0,.13,.24,.39,.54,.68,.84,1],np.float32)
        for i,(bounds,q) in enumerate(zip((m,r,cc),(t,tr,tc))):
            shaped=np.interp(q,np.linspace(0,1,8,dtype=np.float32),stops).astype(np.float32)
            val=(bounds[0]+(bounds[1]-bounds[0])*shaped)/255.
            self.rgb[:,:,i]=self.rgb[:,:,i]*(1-a)+val*a
        self.alpha=self.alpha+(1-self.alpha)*a;self.names.append(name)
    def finish(self):
        # rgb has been accumulated premultiplied; preserve material targets
        # at antialiased boundaries and keep zero-coverage holes transparent.
        out=np.empty((self.h,self.w,4),np.float32)
        out[:,:,:3]=self.rgb/np.maximum(self.alpha[:,:,None],1e-8)
        out[:,:,3]=self.alpha
        return np.clip(out,0,1)

def voronoi(s,pitch=28.):
    """Jittered fine cells: callers decide whether to use walls, interiors or ribs."""
    gx=np.floor(s.x/pitch);gy=np.floor(s.y/pitch)
    best=np.full((s.h,s.w),1e8,np.float32);second=best.copy();ux=best.copy();vy=best.copy();rid=best.copy()
    for oy in (-1,0,1):
        for ox in (-1,0,1):
            ix,iy=gx+ox,gy+oy
            px=(ix+.2+.6*s.rand(ix,iy,19))*pitch;py=(iy+.2+.6*s.rand(ix,iy,23))*pitch
            u,v=s.x-px,s.y-py;d=u*u+v*v;hit=d<best
            second=np.where(hit,best,np.minimum(second,d));best=np.minimum(best,d)
            ux=np.where(hit,u,ux);vy=np.where(hit,v,vy);rid=np.where(hit,s.rand(ix,iy,37),rid)
    wall=(np.sqrt(second)-np.sqrt(best))*.5
    return ux,vy,wall,rid
