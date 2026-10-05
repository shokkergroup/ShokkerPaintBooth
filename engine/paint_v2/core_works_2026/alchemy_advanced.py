"""Process-led second constructions replace failed emblem and row prototypes.
SPB-105 / CORE-WORKS 2026-09-30. Fine physical features own their materials.
"""
import cv2
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def bth_solvent_pop(seed=42,attempt=2):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+8111,18,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+8112)[lab];t=K.tiers(h);a,b=K.rot(u,v,h*F(K.TAU))
    q=np.hypot(a/(8.2+1.5*h),b/(6.5+2*h))+.07*K.noise(seed+8113,255)
    shell=1-K.sstep(.9,1.18,q);roof=np.sqrt(np.clip(1-q*q,0,1))
    # A one-sided angular tear opens the shell; no symmetric petal/star stamp.
    tear=K.sstep(-2.3,-1.3,b-a*.36)*(1-K.sstep(1.0,2.0,b+a*.55))*K.sstep(-4,-2,a)*(1-K.sstep(5,7,a))*shell
    mouth=tear*(1-K.sstep(1.0,2.3,np.abs(a-1.5)))
    lip=K.near(np.abs(q-.88)*8,.75)*(1-tear)
    split=K.near(np.abs(b-a*.36+1.3),.65)*K.sstep(-5,-3,a)*(1-K.sstep(5,7,a))*shell
    collar=K.near(np.abs(q-1.16)*8,.8);flake=K.sstep(.79,.92,K.unit(K.noise(seed+8114,250)))*collar
    region=K.unit(K.fbm(seed+8115,(3,10,24),.6));paint=K.ramp(.65*region+.35*t,['51223b','985267','d79188','f1cdb0'])
    col=paint*(.51+.51*roof+.11*np.clip(a/10,-1,1))[...,None]
    col=K.mix(col,np.array([.18,.24,.30],F),tear*.9);col=K.mix(col,np.array([.025,.025,.04],F),mouth*.94)
    col=K.mix(col,np.array([.99,.81,.49],F),lip*.8);col=K.mix(col,paint*.14,split*.8)
    col=K.mix(col,np.array([.41,.66,.77],F),collar*.7);col=K.mix(col,np.array([.79,.93,.89],F),flake*.85)
    M=30+90*t;R=40+80*t;C=30+115*t
    M,R,C=over(M,R,C,shell,55+135*t,25+65*(1-roof)+25*t,20+100*t)
    M,R,C=over(M,R,C,tear,20+55*t,160+75*t,190+55*t)
    M,R,C=over(M,R,C,mouth,5+15*t,205+35*t,225+25*t)
    M,R,C=over(M,R,C,lip,175+75*t,20+45*t,20+85*t)
    M,R,C=over(M,R,C,split,10+30*t,185+55*t,210+35*t)
    M,R,C=over(M,R,C,collar,55+125*t,90+110*t,100+135*t)
    M,R,C=over(M,R,C,flake,150+95*t,35+75*t,35+125*t)
    return K.pack(col,M,R,C)

def bth_sag_curtain(seed=42,attempt=2):
    x,y=K.xy();u=x+6*K.noise(seed+8211,155)+3*np.sin(y/19)
    field=np.sin(u/F(4.1))+F(.60)*K.noise(seed+8212,167)
    gx,gy=K.grad(field);d=field/np.maximum(np.hypot(gx,gy),.045)
    run=K.sstep(-.6,.6,d);neck=K.near(np.abs(d-1.6),1.1)*run
    shoulder=K.near(np.abs(d-2.9),.8);trench=K.near(np.abs(d+1.4),.75)
    deposition=K.unit(K.noise(seed+8213,150));t=K.tiers(deposition)
    toe=K.sstep(.76,.91,deposition)*run*K.sstep(2,5,d)
    fold=K.iso(y+x*.20+deposition*3,8,.65)[0]*neck
    roof=K.sstep(0,6,d);region=K.unit(K.fbm(seed+8214,(3,10,24),.6))
    base=K.ramp(region,['302640','715873','b8a0a6','e5d1b8']);wet=K.ramp(.7*region+.3*t,['123e4d','398792','87c4b7','d9e1b9'])
    col=K.mix(base,wet*(.48+.54*roof)[...,None],run)
    col=K.mix(col,np.array([.96,.80,.48],F),shoulder*.8);col=K.mix(col,np.array([.055,.045,.08],F),trench*.87)
    col=K.mix(col,wet*.32,fold*.60);col=K.mix(col,np.array([.70,.94,.87],F),toe*.60)
    M=25+80*t;R=95+100*t;C=95+130*t
    M,R,C=over(M,R,C,run,40+125*t,25+50*(1-roof)+25*t,16+80*t)
    M,R,C=over(M,R,C,neck,60+110*t,60+95*t,55+140*t)
    M,R,C=over(M,R,C,shoulder,165+80*t,20+55*t,20+85*t)
    M,R,C=over(M,R,C,trench,5+15*t,190+50*t,210+35*t)
    M,R,C=over(M,R,C,fold,20+50*t,140+90*t,165+75*t)
    M,R,C=over(M,R,C,toe,35+100*t,18+40*t,16+55*t)
    return K.pack(col,M,R,C)

def bth_mottling(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+8411);points=K.sites(seed+8412,10.5 if attempt==2 else 7.2,1.0);count=len(points)
    orientation=K.noise(seed+8413,105);ix=np.clip(points[:,0].astype(int),0,2047);iy=np.clip(points[:,1].astype(int),0,2047)
    angle=orientation[iy,ix]*F(3.1)+rng.normal(0,.35,count).astype(F);L=rng.uniform(8,19,count).astype(F);W=rng.uniform(2.2,4.1,count).astype(F)
    along=np.stack((np.cos(angle),np.sin(angle)),1);across=np.stack((-along[:,1],along[:,0]),1)
    polys=np.rint(np.stack((points-along*L[:,None]/2,points+across*W[:,None],points+along*L[:,None]/2,points-across*W[:,None]*.75),1)).astype(np.int32)
    ids=np.zeros((2048,2048),np.int32);edges=np.zeros((2048,2048),np.uint8);tips=edges.copy()
    if attempt>=4:
        # SPB-105 / CORE-WORKS a4: owner asks intricate grain, not empty stamps.
        # Retain all five a3 grain shapes and exact overlap order; precompute
        # their vertices instead of allocating 56,048 arrays in the hot loop.
        # Native byte equivalence and cold timing recorded in retained evidence;
        # legacy M7 remains diagnostic (no current category profile/baseline).
        mid12=np.rint((polys[:,1]+polys[:,2])/2).astype(np.int32)
        mid01=np.rint((polys[:,0]+polys[:,1])/2).astype(np.int32)
        mid23=np.rint((polys[:,2]+polys[:,3])/2).astype(np.int32)
        shapes=[np.ascontiguousarray(polys[:,[0,1,2]]),np.stack((polys[:,0],polys[:,1],mid12,polys[:,2],polys[:,3]),1),
                np.stack((polys[:,0],mid01,polys[:,2],polys[:,3]),1),
                np.stack((polys[:,0],polys[:,1],polys[:,2],mid23,polys[:,3]),1),polys]
    for i,p in enumerate(polys):
        if attempt>=4:p=shapes[i%5][i]
        elif attempt>=3:
            # Five actual deposited grain shapes, not a single stamped chip.
            kind=i%5
            if kind==0:p=p[[0,1,2]]
            elif kind==1:p=np.rint(np.stack((p[0],p[1],(p[1]+p[2])/2,p[2],p[3]),0)).astype(np.int32)
            elif kind==2:p=np.rint(np.stack((p[0],(p[0]+p[1])/2,p[2],p[3]),0)).astype(np.int32)
            elif kind==3:p=np.rint(np.stack((p[0],p[1],p[2],(p[2]+p[3])/2,p[3]),0)).astype(np.int32)
        cv2.fillConvexPoly(ids,p,i+1,cv2.LINE_8)
        cv2.line(tips,tuple(p[1]),tuple(p[2]),190,1,cv2.LINE_AA)
    cv2.polylines(edges,list(polys),True,255,1,cv2.LINE_AA)
    h=K.hash01(np.arange(count+1),seed+8414)[ids];t=K.tiers(h);flake=(ids>0).astype(F)
    seam=edges.astype(F)/255;tip=tips.astype(F)/255;deposit=K.blur(flake,1.1)
    knot=K.sstep(.87,.98,deposit)*K.sstep(.70,.9,K.unit(K.noise(seed+8415,220)))
    tilt=K.sstep(-.9,.9,orientation);region=K.unit(K.fbm(seed+8416,(3,10,24),.6))
    warm=K.ramp(.6*region+.4*t,['63384a','ad7776','e2bc96','f1dcb9']);cool=K.ramp(.6*(1-region)+.4*t,['213f57','49869d','9bc7c4','d5e4c7'])
    pigment=K.mix(warm,cool,K.sstep(.35,.65,h));base=K.ramp(region,['263044','555872','9a8b9a','ccb9ac'])
    col=K.mix(base,pigment*(.50+.48*tilt)[...,None],flake)
    col=K.mix(col,np.array([.88,.80,.58],F),seam*.55);col=K.mix(col,np.array([.04,.04,.06],F),knot*.7)
    col=K.mix(col,np.array([.88,.98,.91],F),tip*.70)
    M=15+40*t;R=110+105*t;C=125+115*t
    M,R,C=over(M,R,C,flake,120+125*t,30+80*(1-tilt)+45*t,25+155*t)
    M,R,C=over(M,R,C,seam,20+55*t,125+100*t,155+85*t)
    M,R,C=over(M,R,C,knot,50+100*t,170+65*t,185+55*t)
    M,R,C=over(M,R,C,tip,215+35*t,20+45*t,18+70*t)
    return K.pack(col,M,R,C)

def bth_water_spot(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+9511);points=K.sites(seed+9512,13,1.0);count=len(points)
    rings=np.zeros((2048,2048),np.uint8);floor=rings.copy();salt=rings.copy();wet=rings.copy();grain=rings.copy();ids=np.full((2048,2048),-1,np.int32)
    # SPB-105 / CORE-WORKS a3: identical physical mark vocabulary, vectorized
    # endpoint generation; no per-droplet matrix allocations in the hot loop.
    axes_all=rng.integers([4,4],[9,8],(count,2));angle_all=rng.integers(0,180,count)
    start_all=rng.integers(0,130,count);end_all=start_all+rng.integers(150,280,count)
    theta=(start_all[:,None]+rng.random((count,2))*(end_all-start_all)[:,None])*np.pi/180
    rot=angle_all*np.pi/180;cos=np.cos(rot)[:,None];sin=np.sin(rot)[:,None]
    aa=axes_all[:,0,None]*np.cos(theta);bb=axes_all[:,1,None]*np.sin(theta)
    delta=np.stack((cos*aa-sin*bb,sin*aa+cos*bb),2)
    roots=np.rint(points[:,None,:]+delta).astype(np.int32)
    tips=np.rint(points[:,None,:]+delta*rng.uniform(.25,.6,(count,2,1))).astype(np.int32)
    for index,(px,py) in enumerate(points):
        center=(int(px),int(py));axes=tuple(map(int,axes_all[index]));angle=int(angle_all[index]);start=int(start_all[index]);end=int(end_all[index])
        cv2.ellipse(floor,center,axes,angle,0,360,190,-1,cv2.LINE_AA)
        cv2.ellipse(rings,center,axes,angle,start,end,255,1,cv2.LINE_AA)
        cv2.ellipse(ids,center,axes,angle,start,end,index,2,cv2.LINE_8)
        cv2.ellipse(wet,center,(max(2,axes[0]-1),max(2,axes[1]-1)),angle,end+6,end+65,170,1,cv2.LINE_AA)
        for p,q in zip(roots[index],tips[index]):
            cv2.line(salt,tuple(p),tuple(q),190,1,cv2.LINE_AA)
            cv2.line(salt,tuple(q),tuple(q+[2,-2]),150,1,cv2.LINE_AA)
            if index%4==0:cv2.circle(grain,tuple(p),1,200,-1,cv2.LINE_AA)
    rim=rings.astype(F)/255;f=floor.astype(F)/255;fan=salt.astype(F)/255;w=wet.astype(F)/255;g=grain.astype(F)/255
    grown=K.dilate_ids(ids,8);t=K.tiers(K.hash01(np.arange(count+1),seed+9513)[np.maximum(grown,0)])
    region=K.unit(K.fbm(seed+9514,(3,9,24),.6));base=K.ramp(region,['163d49','4e8385','aab8a2','e1d4b0']);col=base.copy()
    col=K.mix(col,base*.67,f*.26);col=K.mix(col,K.ramp(t,['708278','b5b8a0','e4d4af']),rim*.82)
    col=K.mix(col,np.array([.77,.81,.74],F),fan*.75);col=K.mix(col,np.array([.41,.68,.79],F),w*.7)
    col=K.mix(col,np.array([.99,.78,.43],F),g*.85)
    M=20+65*t;R=25+65*t;C=16+85*t
    M,R,C=over(M,R,C,f,15+45*t,75+100*t,80+145*t)
    M,R,C=over(M,R,C,rim,8+30*t,165+75*t,190+55*t)
    M,R,C=over(M,R,C,fan,10+40*t,180+60*t,205+40*t)
    M,R,C=over(M,R,C,w,15+55*t,20+45*t,16+65*t)
    M,R,C=over(M,R,C,g,110+125*t,55+110*t,65+150*t)
    return K.pack(col,M,R,C)
