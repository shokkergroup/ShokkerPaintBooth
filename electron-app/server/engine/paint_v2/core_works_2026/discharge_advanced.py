"""Rebuilt connected discharges reject the sparse symbol and row prototypes.
SPB-105 / CORE-WORKS 2026-09-30; owner: unique, intricate, fine construction.
"""
import cv2
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def lsk_spark_gap(seed=42,attempt=3):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+2511,22,.95));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+2512)[lab];t=K.tiers(h);a,b=K.rot(u,v,h*F(K.TAU));edge=K.edge_distance(lab)
    pads=K.sstep(2.3,3.4,np.abs(a));bevel=K.near(np.abs(np.abs(a)-3.2),.8)*K.sstep(1,3,edge)
    contact=K.near(np.abs(np.abs(a)-4.3),.9)*K.near(np.abs(b),4.6)
    spark=K.near(np.abs(b-1.4*np.sin(a*1.7+h*7)),.65)*(1-pads)*K.near(np.abs(a),3.5)*(h>.22)
    engraving=K.iso(b+a*.25+h*6,8,.7)[0]*pads
    ceramic=1-pads;seat=K.near(edge,.8)*pads;pores=K.near(np.hypot(a+7,b-5),1.1)*(h>.6)*pads
    region=K.unit(K.fbm(seed+2513,(3,9,24),.6));metal=K.ramp(.6*region+.4*t,['523348','9a6577','d0a6a5','ecd6b4']);porcelain=K.ramp(region,['193848','4b7a85','a1b6aa','d8d6b5'])
    col=K.mix(porcelain,metal*(.65+.30*np.clip(np.abs(a)/12,0,1))[...,None],pads)
    col=K.mix(col,np.array([.96,.81,.50],F),bevel*.85);col=K.mix(col,np.array([.81,.89,.91],F),contact*.72)
    col=K.mix(col,np.array([.63,.91,.90],F),spark*.94);col=K.mix(col,metal*.30,engraving*.62)
    col=K.mix(col,np.array([.045,.025,.04],F),np.clip(seat+pores,0,1)*.87)
    M=5+20*t;R=110+100*t;C=110+135*t
    M,R,C=over(M,R,C,pads,170+75*t,45+105*t,45+155*t)
    M,R,C=over(M,R,C,bevel,225+25*t,18+40*t,16+65*t)
    M,R,C=over(M,R,C,contact,185+60*t,30+75*t,35+125*t)
    M,R,C=over(M,R,C,spark,120+125*t,25+75*t,25+95*t)
    M,R,C=over(M,R,C,engraving,75+125*t,145+85*t,150+95*t)
    M,R,C=over(M,R,C,seat,5+20*t,190+50*t,210+35*t)
    M,R,C=over(M,R,C,pores,5,230,250)
    return K.pack(col,M,R,C)

def lsk_tesla_streamer(seed=42,attempt=3):
    x,y=K.xy();rng=np.random.default_rng(seed+2611);points=K.sites(seed+2612,20 if attempt==3 else 17,.9);count=len(points)
    wire=np.zeros((2048,2048),np.uint8);feed=wire.copy();arc=wire.copy();terminal=wire.copy();ids=np.full((2048,2048),-1,np.int32)
    # Real connected square windings, not disconnected concentric stamps.
    winding=np.array([[-8,-8],[8,-8],[8,8],[-6,8],[-6,-6],[6,-6],[6,6],[-4,6],[-4,-4],[4,-4],[4,4],[-2,4],[-2,-2],[2,-2]],F)
    coils=[];feeds=[];arcs=[]
    rotations=rng.uniform(-.20,.20,count);scales=rng.uniform(.78,1.05,count)
    for index,(center,angle,scale) in enumerate(zip(points,rotations,scales)):
        c,s=np.cos(angle),np.sin(angle);matrix=np.array([[c,-s],[s,c]],F)
        p=np.rint(winding@matrix.T*scale+center).astype(np.int32);coils.append(p)
        cv2.polylines(ids,[p],False,index+1,1,cv2.LINE_8)
        start=p[-1];end=start+np.array([9,-4]);feeds.append(np.array([start,start+[4,-1],end],np.int32))
        arcend=end+np.array([rng.integers(-7,8),rng.integers(8,16)])
        arcs.append(np.array([end,end+[4,4],arcend],np.int32));cv2.circle(terminal,tuple(end),1,220,-1,cv2.LINE_AA)
    if attempt>=4:
        # Short neighbor feed segments join actual coil terminals; no common
        # decorative wave is laid over the winding construction.
        from scipy.spatial import cKDTree
        neighbors=cKDTree(points).query(points,k=2)[1][:,1]
        for index,other in enumerate(neighbors):
            start=coils[index][0];end=coils[int(other)][0]
            middle=np.rint((start+end)*.5+np.array([2,-2])).astype(np.int32)
            feeds.append(np.array([start,middle,end],np.int32))
    cv2.polylines(wire,coils,False,255,1,cv2.LINE_AA);cv2.polylines(feed,feeds,False,255,1,cv2.LINE_AA);cv2.polylines(arc,arcs,False,255,1,cv2.LINE_AA)
    w=wire.astype(F)/255;f=feed.astype(F)/255;a=arc.astype(F)/255;end=terminal.astype(F)/255;t=_feature_tier(ids,seed+2613)
    distance=cv2.distanceTransform(255-wire,cv2.DIST_L2,3);insulator=K.near(np.abs(distance-1.6),.65)
    cuff=K.blur(a,1.25);region=K.unit(K.fbm(seed+2614,(3,9,24),.6));grain=K.unit(K.noise(seed+2615,230))
    base=K.ramp(region,['27152e','642b4d','a96071','dca39a'])*(.88+.12*grain)[...,None]
    col=K.mix(base,base*.18,insulator*.77);col=K.mix(col,K.ramp(t,['784334','bd7c4e','ecc48b','fff0c0']),w*.94)
    col=K.mix(col,np.array([.50,.78,.88],F),f*.85);col=K.mix(col,np.array([.80,.94,.90],F),a*.85)
    col=K.mix(col,np.array([.98,.84,.51],F),end);col+=cuff[...,None]*np.array([.04,.09,.10],F)
    M=15+40*grain;R=55+80*grain;C=40+95*grain
    M,R,C=over(M,R,C,insulator,5+15*t,190+50*t,210+35*t)
    M,R,C=over(M,R,C,w,165+80*t,35+110*t,35+170*t)
    M,R,C=over(M,R,C,f,95+140*t,50+95*t,35+140*t)
    M,R,C=over(M,R,C,a,130+115*t,30+75*t,20+95*t)
    M,R,C=over(M,R,C,end,225+25*t,18+45*t,16+65*t)
    M,R,C=over(M,R,C,cuff*(1-a),20+60*t,115+105*t,90+145*t)
    return K.pack(col,M,R,C)

def lsk_corona_ring(seed=42,attempt=3):
    x,y=K.xy();rng=np.random.default_rng(seed+2711);points=K.sites(seed+2712,17,1.0);count=len(points)
    rings=np.zeros((2048,2048),np.uint8);fringe=rings.copy();seats=rings.copy();ids=np.full((2048,2048),-1,np.int32)
    if attempt>=5:
        axes_all=rng.integers([6,8],[10,12],(count,2));angles=rng.integers(-45,46,count)
        theta=rng.uniform(0,6.283,(count,2));rad=angles[:,None]*np.pi/180
        cc,ss=np.cos(rad),np.sin(rad);aa=axes_all[:,0,None]*np.cos(theta);bb=axes_all[:,1,None]*np.sin(theta)
        roots=points[:,None,:]+np.stack((cc*aa-ss*bb,ss*aa+cc*bb),2)
        nx=np.cos(theta)/axes_all[:,0,None];ny=np.sin(theta)/axes_all[:,1,None]
        normals=np.stack((cc*nx-ss*ny,ss*nx+cc*ny),2);normals/=np.linalg.norm(normals,axis=2)[...,None]
        ends=roots+normals*rng.uniform(4,8,(count,2,1))
        rays=np.rint(np.stack((roots,ends),2)).astype(np.int32)
        for index,(px,py) in enumerate(points):
            center=(int(px),int(py));axes=tuple(map(int,axes_all[index]));angle=int(angles[index])
            cv2.ellipse(rings,center,axes,angle,0,360,255,3,cv2.LINE_AA)
            cv2.ellipse(ids,center,axes,angle,0,360,index+1,3,cv2.LINE_8)
            cv2.ellipse(seats,center,axes,angle,5,60,200,1,cv2.LINE_AA)
        for tier in range(8):cv2.polylines(fringe,list(rays[np.arange(count)%8==tier].reshape(-1,2,2)),False,int(100+155*tier/7),1,cv2.LINE_AA)
    for index,(px,py) in enumerate(points):
        if attempt>=5:break
        center=(int(px),int(py));axes=(int(rng.integers(6,10)),int(rng.integers(8,12)));angle=int(rng.integers(-45,46))
        cv2.ellipse(rings,center,axes,angle,0,360,255,3,cv2.LINE_AA)
        cv2.ellipse(ids,center,axes,angle,0,360,index+1,3,cv2.LINE_8)
        cv2.ellipse(seats,center,axes,angle,5,60,200,1,cv2.LINE_AA)
        for ray in range(2):
            theta=rng.uniform(0,6.283);rad=angle*np.pi/180;c,s=np.cos(rad),np.sin(rad)
            rot=np.array([[c,-s],[s,c]])
            local=np.array([axes[0]*np.cos(theta),axes[1]*np.sin(theta)])
            a=np.array([px,py])+rot@local
            normal=rot@np.array([np.cos(theta)/axes[0],np.sin(theta)/axes[1]])
            normal/=np.linalg.norm(normal);b=a+normal*rng.uniform(4,8)
            cv2.line(fringe,tuple(a.astype(np.int32)),tuple(b.astype(np.int32)),int(100+155*(index%8)/7),1,cv2.LINE_AA)
    ring=rings.astype(F)/255;f=fringe.astype(F)/255;seat=seats.astype(F)/255;t=_feature_tier(ids,seed+2713)
    inside=cv2.distanceTransform(rings,cv2.DIST_L2,3);roof=np.clip(inside/2.3,0,1)
    # Occlusion is from the actual rasterized ring stack. Nearest-cell clipping
    # cannot chop the torus into the rejected pebble/confetti prototype.
    lip=np.clip(np.roll(ring,(1,-1),(0,1))-ring,0,1);ruling=K.iso(x*.75-y*.65+t*4,8,.65)[0]*ring
    region=K.unit(K.fbm(seed+2714,(3,10,24),.6));base=K.ramp(region,['102f44','286e84','72adac','c8d5b4'])
    metal=K.ramp(t,['426573','7d9ca0','bfccba','eae0b8']);col=K.mix(base,metal*(.40+.60*roof)[...,None],ring)
    col=K.mix(col,np.array([.97,.79,.47],F),lip*.9);col=K.mix(col,base*.18,seat*.75)
    col=K.mix(col,np.array([.56,.85,.94],F),f*.75);col=K.mix(col,base*.34,ruling*.55)
    M=15+45*t;R=45+80*t;C=30+120*t
    M,R,C=over(M,R,C,ring,165+85*t,25+105*(1-roof)+45*t,35+170*t)
    M,R,C=over(M,R,C,lip,225+25*t,18+40*t,16+65*t)
    M,R,C=over(M,R,C,seat,25+65*t,175+60*t,195+50*t)
    M,R,C=over(M,R,C,f,95+140*t,45+95*t,25+130*t)
    M,R,C=over(M,R,C,ruling,10+30*t,135+95*t,165+75*t)
    return K.pack(col,M,R,C)

def _feature_tier(ids,seed,radius=8):
    grown=K.dilate_ids(ids,radius)
    h=K.hash01(np.arange(int(ids.max())+2),seed)
    return K.tiers(h[np.maximum(grown,0)])

def lsk_return_stroke(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+1311);core=np.zeros((2048,2048),np.uint8);fork=core.copy();tip=core.copy();ids=np.full((2048,2048),-1,np.int32)
    count=98;steps=119
    xx=rng.uniform(-25,2073,(count,1))+np.cumsum(rng.normal(0,8,(count,steps)),axis=1)
    yy=np.broadcast_to(np.arange(steps)*18-30,(count,steps))+rng.uniform(-5,5,(count,steps))
    paths=np.rint(np.stack((xx,yy),axis=2)).astype(np.int32)
    cv2.polylines(core,list(paths),False,255,2,cv2.LINE_AA)
    for i,p in enumerate(paths):cv2.polylines(ids,[p],False,i+1,2,cv2.LINE_8)
    origins=np.stack((xx[:,2:-2:4],yy[:,2:-2:4]),axis=2).reshape(-1,2)
    angle=rng.uniform(-2.8,-.3,len(origins));L=rng.uniform(9,24,len(origins));direction=np.stack((np.cos(angle),np.sin(angle)),1)
    ends=origins+direction*L[:,None];middle=origins+direction*L[:,None]*.4+rng.normal(0,2.0,(len(origins),2))
    branch=np.rint(np.stack((origins,middle,ends),axis=1)).astype(np.int32)
    cv2.polylines(fork,list(branch),False,255,1,cv2.LINE_AA)
    for i,p in enumerate(branch):
        cv2.polylines(ids,[p],False,count+i+1,1,cv2.LINE_8)
        if i%3==0:cv2.circle(tip,tuple(p[-1]),1,220,-1,cv2.LINE_AA)
    full=np.maximum(core,fork);d=cv2.distanceTransform(255-full,cv2.DIST_L2,3)
    main=core.astype(F)/255;f=fork.astype(F)/255;end=tip.astype(F)/255;t=_feature_tier(ids,seed+1312)
    collar=K.near(np.abs(d-2.6),.9);shock=K.near(np.abs(d-6.2),.65);burn=K.near(d,7.5)
    grain=K.unit(K.noise(seed+1313,205));region=K.unit(K.fbm(seed+1314,(3,11,25),.6))
    base=K.ramp(region,['091a38','263c65','557b9b','b2c2c4'])*(.90+.10*grain)[...,None]
    col=K.mix(base,base*.19,burn*.68);copper=K.ramp(t,['63312f','b8674c','e7a16d','ffe4ac'])
    col=K.mix(col,copper,collar*.85);col=K.mix(col,K.ramp(t,['3c94b1','79d7d5','e8ffe0']),main)
    col=K.mix(col,np.array([.50,.73,.94],F),f*.88);col=K.mix(col,col*.25,shock*.85)
    col=K.mix(col,np.array([.99,.69,.36],F),end*.9)
    M=15+40*grain;R=25+45*grain;C=20+75*grain
    M,R,C=over(M,R,C,burn,5+15*t,165+75*t,190+55*t)
    M,R,C=over(M,R,C,collar,155+90*t,30+110*t,35+165*t)
    M,R,C=over(M,R,C,main,205+45*t,18+40*t,16+70*t)
    M,R,C=over(M,R,C,f,100+140*t,40+90*t,25+130*t)
    M,R,C=over(M,R,C,shock,5+15*t,210+35*t,225+25*t)
    M,R,C=over(M,R,C,end,225+25*t,20+50*t,20+80*t)
    return K.pack(col,M,R,C)

def lsk_spider_crawl(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+1411);centers=K.sites(seed+1412,34 if attempt==2 else 20,1.0)
    count=len(centers);points=np.empty((count,8,2),F);points[:,0]=centers
    angle=rng.normal(0,.33,count).astype(F)+rng.choice(np.array([0,np.pi],F),count)
    for step in range(1,8):
        angle+=rng.normal(0,.32,count).astype(F);L=rng.uniform(8,18,count).astype(F)
        points[:,step]=points[:,step-1]+np.stack((np.cos(angle),np.sin(angle)),1)*L[:,None]
    ids=np.full((2048,2048),-1,np.int32);crawl=np.zeros((2048,2048),np.uint8);hooks=crawl.copy();knots=crawl.copy();dust=crawl.copy()
    mains=np.rint(points).astype(np.int32);cv2.polylines(crawl,list(mains),False,255,1,cv2.LINE_AA)
    for i,p in enumerate(mains):cv2.polylines(ids,[p],False,i+1,1,cv2.LINE_8)
    roots=points[:,1:7:2].reshape(-1,2);theta=rng.uniform(-1.3,1.3,len(roots));sign=rng.choice([-1,1],len(roots));theta+=sign*np.pi/2
    L=rng.uniform(8,20,len(roots));q=roots+np.stack((np.cos(theta),np.sin(theta)),1)*L[:,None]
    turn=q+np.stack((np.cos(theta+sign*1.1),np.sin(theta+sign*1.1)),1)*rng.uniform(5,9,len(roots))[:,None]
    branches=np.rint(np.stack((roots,q,turn),1)).astype(np.int32);cv2.polylines(hooks,list(branches),False,255,1,cv2.LINE_AA)
    for i,p in enumerate(branches):
        cv2.polylines(ids,[p],False,count+i+1,1,cv2.LINE_8)
        if i%4==0:cv2.circle(knots,tuple(p[0]),1,220,-1,cv2.LINE_AA)
        if i%3==0:cv2.circle(dust,tuple(p[-1]),1,170,-1,cv2.LINE_AA)
    full=np.maximum(crawl,hooks);d=cv2.distanceTransform(255-full,cv2.DIST_L2,3)
    c=crawl.astype(F)/255;b=hooks.astype(F)/255;k=knots.astype(F)/255;end=dust.astype(F)/255;t=_feature_tier(ids,seed+1413)
    cuff=np.exp(-d/3.8);bridge=K.near(np.abs(d-2.5),.75)*K.sstep(.58,.74,t)
    region=K.unit(K.fbm(seed+1414,(3,9,24),.6));grain=K.unit(K.noise(seed+1415,205));base=K.ramp(region,['092c36','246969','6f9c85','c8c9a4'])*(.86+.14*grain)[...,None]
    col=K.mix(base,base*.15,cuff*.82);col=K.mix(col,K.ramp(t,['316f9b','71bfc5','d6f2d4']),c)
    col=K.mix(col,np.array([.84,.62,.32],F),b*.9);col=K.mix(col,np.array([.97,.85,.54],F),bridge*.76)
    col=K.mix(col,np.array([.97,.95,.78],F),k);col=K.mix(col,np.array([.56,.71,.84],F),end*.55)
    M=15+45*grain;R=30+55*grain;C=25+80*grain
    M,R,C=over(M,R,C,cuff,5+15*t,165+75*t,195+50*t)
    M,R,C=over(M,R,C,c,170+80*t,20+65*t,20+95*t)
    M,R,C=over(M,R,C,b,135+110*t,35+110*t,35+150*t)
    M,R,C=over(M,R,C,bridge,185+60*t,30+70*t,35+125*t)
    M,R,C=over(M,R,C,k,225+25*t,18+45*t,16+60*t)
    M,R,C=over(M,R,C,end,35+80*t,145+85*t,155+85*t)
    return K.pack(col,M,R,C)

def lsk_sprite(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+2011);centers=K.sites(seed+2012,19 if attempt==2 else 15 if attempt>=4 else 12,1.0);count=len(centers)
    width=rng.uniform(4,8,count).astype(F);height=rng.uniform(2.8,5.5,count).astype(F);rotation=rng.uniform(-.12,.12,count).astype(F)
    theta=np.linspace(-np.pi,0,13,dtype=F)[None,:]+rotation[:,None]
    caps=np.stack((centers[:,0,None]+width[:,None]*np.cos(theta),centers[:,1,None]+height[:,None]*np.sin(theta)),2)
    cap=np.zeros((2048,2048),np.uint8);body=cap.copy();tendril=cap.copy();tips=cap.copy();ids=np.full((2048,2048),-1,np.int32)
    cap_paths=np.rint(caps).astype(np.int32);cv2.polylines(cap,list(cap_paths),False,255,1,cv2.LINE_AA)
    for i,p in enumerate(cap_paths):
        cv2.fillConvexPoly(body,np.concatenate((p,p[[0]])),int(100+155*(i%8)/7),cv2.LINE_AA)
        cv2.fillConvexPoly(ids,p,i+1,cv2.LINE_8)
    q=np.linspace(0,1,8,dtype=F);branches=[]
    for offset in (-.75,-.25,.25,.75):
        L=rng.uniform(9,23,count).astype(F);phase=rng.uniform(0,6.283,count).astype(F)
        xx=centers[:,0,None]+width[:,None]*offset+2.0*np.sin(q[None,:]*5+phase[:,None])*q[None,:]
        yy=centers[:,1,None]+L[:,None]*q[None,:]
        paths=np.rint(np.stack((xx,yy),2)).astype(np.int32);branches.extend(paths)
    cv2.polylines(tendril,branches,False,255,2 if attempt==3 else 1,cv2.LINE_AA)
    for i,p in enumerate(branches):
        cv2.polylines(ids,[p],False,i%count+1,1,cv2.LINE_8)
        if i%4==0:cv2.circle(tips,tuple(p[-1]),1,190,-1,cv2.LINE_AA)
    cf=cap.astype(F)/255;bf=body.astype(F)/255;tf=tendril.astype(F)/255;end=tips.astype(F)/255;t=_feature_tier(ids,seed+2013)
    cuff=K.blur(np.maximum(cf,tf),1.0);region=K.unit(K.fbm(seed+2014,(3,9,23),.6));grain=K.unit(K.noise(seed+2015,230))
    base=K.ramp(region,['211737','58335e','aa668a','e0ada9'])*(.88+.12*grain)[...,None]
    col=K.mix(base,base*.30,cuff*.55);col=K.mix(col,K.ramp(t,['683859','ad6481','eaa885','ffe6bd']),bf*.65)
    col=K.mix(col,np.array([.98,.85,.54],F),cf*.95);col=K.mix(col,K.ramp(t,['29627a','6cadb9','c2e8d8']),tf*.9)
    col=K.mix(col,np.array([.89,.84,.96],F),end*.7)
    M=20+45*grain;R=45+75*grain;C=35+100*grain
    M,R,C=over(M,R,C,cuff,15+35*t,150+85*t,165+80*t)
    M,R,C=over(M,R,C,bf,45+120*t,40+85*t,25+115*t)
    M,R,C=over(M,R,C,cf,170+75*t,20+55*t,20+90*t)
    M,R,C=over(M,R,C,tf,100+140*t,35+100*t,25+145*t)
    M,R,C=over(M,R,C,end,70+125*t,100+110*t,90+145*t)
    return K.pack(col,M,R,C)
