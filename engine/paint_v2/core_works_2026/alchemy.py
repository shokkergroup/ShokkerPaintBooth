"""Paint reactions developed into fine, complete material surfaces.
SPB-105 / CORE-WORKS 2026-09-30. Material restraint retains surface detail.
"""
import numpy as np
import cv2
from . import kit as K
from .common import over
F=np.float32

def bth_sand_scratch(seed=42,attempt=1):
    """Crossed independent grit strokes; displaced burrs prove scored alloy."""
    x,y=K.xy();rng=np.random.default_rng(seed+8901)
    grooves=np.zeros((2048,2048),np.uint8);filings=grooves.copy();pores=grooves.copy()
    starts=rng.uniform(-20,2068,(22000 if attempt==1 else 132000,2));angles=rng.uniform(0,np.pi,len(starts))
    lengths=rng.uniform(8,28,len(starts));ends=starts+np.stack((np.cos(angles),np.sin(angles)),1)*lengths[:,None]
    for i,(a,b) in enumerate(zip(starts.astype(np.int32),ends.astype(np.int32))):
        cv2.line(grooves,tuple(a),tuple(b),int(115+140*(i%8)/7),1,cv2.LINE_AA)
        if i%3==0:cv2.line(filings,tuple(b),tuple(b+np.array([3,-2])),int(100+155*(i%7)/6),1,cv2.LINE_AA)
        if i%5==0:cv2.circle(pores,tuple(a),1,220,-1,cv2.LINE_AA)
    g=grooves.astype(F)/255;f=filings.astype(F)/255;p=pores.astype(F)/255
    # The burr is displaced from the same stroke, never an unrelated spec wave.
    lip=np.clip(np.roll(g,(1,-1),(0,1))-g,0,1)
    haze=cv2.GaussianBlur(g,(0,0),1.2)*.8
    tier=K.unit(K.noise(seed+8902,180));region=K.unit(K.fbm(seed+8903,(3,9,23),.6))
    base=K.ramp(region,['122638','365d76','827f86','e3b892'])
    col=base*(.86+.14*tier)[...,None]
    col=K.mix(col,base*.15,g*.8);col=K.mix(col,np.array([.95,.85,.62],F),lip*.9)
    col=K.mix(col,np.array([.35,.72,.88],F),f*.7);col=K.mix(col,np.array([.03,.025,.04],F),p)
    M=160+80*tier;R=35+50*tier;C=30+75*tier
    M,R,C=over(M,R,C,haze,145+85*tier,110+100*tier,155+80*tier)
    M,R,C=over(M,R,C,g,90+130*tier,170+65*tier,210+40*tier)
    M,R,C=over(M,R,C,lip,225+25*tier,18+40*tier,18+55*tier)
    M,R,C=over(M,R,C,f,165+80*tier,40+130*tier,75+140*tier)
    M,R,C=over(M,R,C,p,5,235,250)
    return K.pack(col,M,R,C)

def bth_dirt_nib(seed=42,attempt=1):
    """Angular dust grains tent a continuous lacquer skin."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+9001,18,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+9002)[lab];t=K.tiers(h)
    a,b=K.rot(u,v,h*6);q=np.maximum(np.abs(a)/(5+2*h),np.abs(b)/(4+2*(1-h)))
    tent=1-K.sstep(.9,1.4,q);roof=np.clip(1-q,0,1)
    grain=1-K.sstep(.5,1.4,np.maximum(np.abs(a+.6),np.abs(b-.8)))
    lip=K.near(np.abs(q-1.0)*(5+2*h),.8)
    cuts=K.near(np.abs(a-b*.45),.65)*tent*K.sstep(.22,.55,q)
    root=K.near(np.abs(q-1.48)*6,.65)
    binder=(1-K.sstep(1.0,2.0,np.hypot(a-5,b+4)))*(h>.45)
    region=K.unit(K.fbm(seed+9003,(3,10,25),.6));base=K.ramp(region,['171743','4b397c','a1739f','ecd4b4'])
    col=base*(.75+.35*roof+.13*np.clip(a/8,-1,1))[...,None]
    col=K.mix(col,np.array([.045,.03,.045],F),grain);col=K.mix(col,base*.2,cuts*.8)
    col=K.mix(col,np.array([.85,.66,.35],F),lip*.7);col=K.mix(col,base*.25,root*.65)
    col=K.mix(col,np.array([.61,.83,.84],F),binder*.8)
    M=45+90*t;R=25+55*t;C=16+80*t
    M,R,C=over(M,R,C,tent,65+140*t,35+95*(1-roof),20+125*t)
    M,R,C=over(M,R,C,grain,8+20*t,205+40*t,215+35*t)
    M,R,C=over(M,R,C,lip,165+85*t,20+70*t,25+90*t)
    M,R,C=over(M,R,C,cuts,15+35*t,160+80*t,195+50*t)
    M,R,C=over(M,R,C,root,15,190+55*t,210+40*t)
    M,R,C=over(M,R,C,binder,15+30*t,18+40*t,16+45*t)
    return K.pack(col,M,R,C)

def bth_edge_map(seed=42,attempt=1):
    """A buried repair stack shows substrate, primer and feathered coat ghosts."""
    x,y=K.xy();f=K.fbm(seed+9101,(105,171,247),.62)
    gx,gy=K.grad(f);distance=f/np.maximum(np.hypot(gx,gy),.014)
    floor=1-K.sstep(-5,-3,distance);primer=K.sstep(-4,-2,distance)*(1-K.sstep(0,2,distance))
    paint=K.sstep(1,3,distance);ghost=K.near(np.abs(distance-6),.75)
    lip=K.near(np.abs(distance-2.2),.7)
    h=K.unit(K.noise(seed+9102,183));t=K.tiers(h)
    notch=K.sstep(.79,.92,h)*K.near(np.abs(distance-1),1.9)
    region=K.unit(K.fbm(seed+9103,(3,8,24),.6))
    alloy=K.ramp(t,['363f50','658494','b2b8ac','e5d5b1']);colour=K.ramp(region,['2b1642','653060','bb6882','efbaa0'])
    col=K.mix(alloy,np.array([.58,.61,.60],F),primer)
    col=K.mix(col,colour,paint);col=K.mix(col,np.array([.90,.74,.47],F),lip*.9)
    col=K.mix(col,colour*.45,ghost*.55);col=K.mix(col,alloy*.3,notch*.85)
    M=200+50*t;R=50+80*t;C=175+65*t
    M,R,C=over(M,R,C,primer,3+12*t,165+70*t,215+35*t)
    M,R,C=over(M,R,C,paint,40+100*t,25+65*t,20+90*t)
    M,R,C=over(M,R,C,ghost,25+60*t,95+100*t,100+130*t)
    M,R,C=over(M,R,C,lip,175+70*t,18+40*t,16+55*t)
    M,R,C=over(M,R,C,notch,70+110*t,180+65*t,205+40*t)
    return K.pack(col,M,R,C)

def bth_buff_hologram(seed=42,attempt=1):
    """Fine broken rotary sweeps, never a large repeated polish stamp."""
    x,y=K.xy();rng=np.random.default_rng(seed+9201);track=np.zeros((2048,2048),np.uint8);hook=track.copy();grain=track.copy()
    centers=rng.uniform(-12,2060,(18500 if attempt==1 else 92500,2));radii=rng.uniform(4,11,len(centers));angle=rng.uniform(0,360,len(centers))
    centers=centers.astype(np.int32)
    for i,(c,r,a) in enumerate(zip(centers,radii,angle)):
        val=int(85+170*(i%8)/7)
        for dr in (0,2):cv2.ellipse(track,tuple(c),(int(r),int(max(3,r-2+dr))),int(a),15,155,val,1,cv2.LINE_AA)
        if i%3==0:cv2.ellipse(hook,tuple(c+np.array([3,2])),(3,4),int(a),100,290,val,1,cv2.LINE_AA)
        if i%4==0:cv2.circle(grain,tuple(c),1,val,-1,cv2.LINE_AA)
    arc=track.astype(F)/255;tail=hook.astype(F)/255;compound=grain.astype(F)/255
    lip=np.clip(np.roll(arc,(-1,1),(0,1))-arc,0,1);haze=cv2.GaussianBlur(arc,(0,0),1.0)*.65
    t=K.tiers(K.unit(K.noise(seed+9202,190)));region=K.unit(K.fbm(seed+9203,(3,8,22),.6))
    base=K.ramp(region,['051b36','124369','438d9c','b0d4bb']);col=base.copy()
    col=K.mix(col,base*.4,arc*.78);col=K.mix(col,np.array([.92,.81,.53],F),lip*.85)
    col=K.mix(col,np.array([.39,.63,.84],F),tail*.65);col=K.mix(col,np.array([.58,.50,.36],F),compound*.8)
    col=K.mix(col,base*.75,haze*.2)
    M=155+90*t;R=20+45*t;C=16+60*t
    M,R,C=over(M,R,C,haze,130+85*t,90+110*t,100+135*t)
    M,R,C=over(M,R,C,arc,175+65*t,110+100*t,125+115*t)
    M,R,C=over(M,R,C,lip,225+25*t,18+40*t,18+50*t)
    M,R,C=over(M,R,C,tail,140+95*t,145+90*t,160+85*t)
    M,R,C=over(M,R,C,compound,10+25*t,210+35*t,220+30*t)
    return K.pack(col,M,R,C)

def bth_mask_bleed(seed=42,attempt=1):
    """Capillary tongues root on one side of a sharp mask cut."""
    x,y=K.xy();u=x+3.2*K.noise(seed+9301,95);v=y+2.1*K.noise(seed+9302,110)
    phase=u/22+F(.22)*np.sin(v/11);cut=np.sin(phase*F(K.TAU))
    du,dv=K.grad(cut);d=cut/np.maximum(np.hypot(du,dv),.07)
    fingerfield=d+2.8*np.sin(v/2.2)+1.1*np.sin(v/1.4+u/8)
    pigment=K.sstep(-.4,.6,fingerfield)
    sharp=K.near(np.abs(d),.6);meniscus=K.near(np.abs(fingerfield)/np.maximum(np.hypot(*K.grad(fingerfield)),.08),.7)
    t=K.tiers(K.unit(K.noise(seed+9303,195)))
    bead=K.sstep(.72,.90,K.unit(K.noise(seed+9304,255)))*meniscus
    tips=meniscus*K.sstep(-4,-1,d)*(1-K.sstep(-1,1,d))
    region=K.unit(K.fbm(seed+9305,(4,10,24),.6));ink=K.ramp(region,['082f44','197b88','73c3bb','dde4af'])
    col=K.mix(np.broadcast_to(np.array([.69,.60,.64],F),(2048,2048,3)).copy(),ink,pigment)
    col=K.mix(col,np.array([.08,.04,.08],F),sharp*.9);col=K.mix(col,np.array([.95,.79,.50],F),meniscus*.65)
    col=K.mix(col,np.array([.70,.91,.94],F),bead*.7)
    M=5+15*t;R=145+80*t;C=195+50*t
    M,R,C=over(M,R,C,pigment,25+100*t,30+65*t,20+90*t)
    M,R,C=over(M,R,C,sharp,160+80*t,35+70*t,50+125*t)
    M,R,C=over(M,R,C,meniscus,125+115*t,20+55*t,18+85*t)
    M,R,C=over(M,R,C,bead,20+65*t,16+30*t,16+35*t)
    M,R,C=over(M,R,C,tips,20+50*t,150+90*t,175+70*t)
    return K.pack(col,M,R,C)

def bth_tape_ridge(seed=42,attempt=1):
    """Raised nested paint shelves remain after the tape is pulled."""
    x,y=K.xy();u=x+4*K.noise(seed+9401,85);v=y+4*K.noise(seed+9402,91)
    a,b=K.rot(u,v,F(.72));f=np.sin(a/5.1)+.58*np.cos(b/4.4)
    gx,gy=K.grad(f);d=f/np.maximum(np.hypot(gx,gy),.045)
    plateau=K.sstep(-.6,.6,d);wall=K.near(np.abs(d-1.7),1.0);crown=K.near(np.abs(d-2.7),.65)
    sliver=K.near(np.abs(d+1.5),1.0);t=K.tiers(K.unit(K.noise(seed+9403,200)))
    teeth=K.sstep(.75,.92,K.unit(K.noise(seed+9404,255)))*sliver
    trapped=K.sstep(.82,.95,K.unit(K.noise(seed+9405,240)))*wall
    region=K.unit(K.fbm(seed+9406,(4,11,25),.6));top=K.ramp(region,['241838','7a477b','c684a4','f0cbb5']);under=K.ramp(t,['133c4d','3e7e80','a0bda0','dedabe'])
    col=K.mix(under,top,plateau);col=K.mix(col,top*.3,wall*.6)
    col=K.mix(col,np.array([.99,.83,.51],F),crown*.85);col=K.mix(col,np.array([.29,.31,.34],F),sliver*.8)
    col=K.mix(col,under*.25,teeth*.8);col=K.mix(col,np.array([.75,.91,.87],F),trapped*.8)
    M=25+65*t;R=65+100*t;C=55+150*t
    M,R,C=over(M,R,C,plateau,50+120*t,25+65*t,20+95*t)
    M,R,C=over(M,R,C,wall,135+110*t,50+95*t,65+140*t)
    M,R,C=over(M,R,C,crown,215+35*t,18+40*t,16+60*t)
    M,R,C=over(M,R,C,sliver,5+10*t,185+50*t,210+40*t)
    M,R,C=over(M,R,C,teeth,15+25*t,210+35*t,225+25*t)
    M,R,C=over(M,R,C,trapped,130+100*t,35+100*t,50+135*t)
    return K.pack(col,M,R,C)

def bth_water_spot(seed=42,attempt=1):
    """Broken drying salt arcs with inward mineral fans, no crater relief."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+9501,19,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+9502)[lab];t=K.tiers(h);theta=np.arctan2(v,u)
    radius=4.5+4*h;irreg=d+.5*np.sin(theta*5+h*7);pool=1-K.sstep(radius-1,radius+1,irreg)
    broken=K.sstep(-.50,-.20,np.sin(theta*2+h*9));rim=K.near(np.abs(irreg-radius),.75)*broken
    fan=K.near(np.abs(np.sin(theta*(5+np.floor(h*4))+h*5))*np.maximum(d,2)/5,.55)*pool*K.sstep(.40,.72,d/radius)
    heart=(1-K.sstep(.25,.48,d/radius))*pool;wet=K.near(np.abs(irreg-radius+.8),.55)*(1-broken)
    grain=K.sstep(.72,.90,K.unit(K.noise(seed+9503,256)))*np.clip(rim+fan,0,1)
    region=K.unit(K.fbm(seed+9504,(4,9,22),.6));base=K.ramp(region,['123440','3a777b','96aaa2','d7c6b0']);col=base.copy()
    col=K.mix(col,base*.7,pool*.35);col=K.mix(col,np.array([.79,.72,.59],F),rim*.85)
    col=K.mix(col,np.array([.66,.75,.73],F),fan*.65);col=K.mix(col,np.array([.93,.81,.52],F),grain*.9)
    col=K.mix(col,np.array([.43,.76,.84],F),wet*.6)
    M=25+85*t;R=25+55*t;C=16+75*t
    M,R,C=over(M,R,C,pool,25+45*t,65+100*t,80+135*t)
    M,R,C=over(M,R,C,heart,20+65*t,20+35*t,16+45*t)
    M,R,C=over(M,R,C,rim,8+20*t,185+60*t,210+40*t)
    M,R,C=over(M,R,C,fan,15+35*t,150+85*t,175+65*t)
    M,R,C=over(M,R,C,grain,110+125*t,65+135*t,85+145*t)
    M,R,C=over(M,R,C,wet,15+30*t,20+40*t,16+55*t)
    return K.pack(col,M,R,C)

def bth_fisheye(seed=42, attempt=1):
    """Irregular contamination craters with rolled menisci in metallic candy."""
    x,y=K.xy()
    lab,d,pts=K.voronoi(K.sites(seed+801,25 if attempt==1 else 22,1.0))
    count=len(pts)
    h=K.hash01(np.arange(count),seed+802)[lab]
    size=(3.4+6.8*K.hash01(np.arange(count),seed+803))[lab]
    active=(K.hash01(np.arange(count),seed+804)>.18)[lab]
    dx,dy=K.cell_local(lab,pts,x,y)
    ang=np.arctan2(dy,dx)
    radius=d+(np.sin(ang*3+h*6)+.5*np.sin(ang*7-h*4))*.4
    q=radius/size
    floor=(1-K.sstep(.50,.65,q))*active
    rim=np.exp(-((q-.82)/F(.16))**2)*active
    meniscus=np.exp(-((q-1.12)/F(.18))**2)*active
    crease=K.near(q-.66,.065)*active
    if attempt>=2:
        crease=K.near((q-.66)*size,.7)*active
    if attempt>=3:
        crease=K.near(np.abs((q-.66)*size),.65)*active
    regional=K.unit(K.fbm(seed+805,(4,9,19),.6))
    flake_lab,_,flake_pts=K.voronoi(K.sites(seed+806,9,1.0))
    flake=K.hash01(np.arange(len(flake_pts)),seed+807)[flake_lab]
    body=K.ramp(.70*regional+.30*flake,['05072b','183b7a','2d6e91','725184','bf80a2'])
    if attempt>=2:
        body=K.ramp(.75*regional+.25*flake,['061a29','075460','10959d','73dfcf'])
    body *= (.64+.45*flake)[...,None]
    if attempt>=2:
        # Substrate flakes become pigment glints, not a second competing mosaic.
        body=K.ramp(regional,['051627','12485d','238b98','74d4c5'])*(.9+.1*flake)[...,None]
    col=body.copy()
    substrate=K.ramp(h,['322031','8c5438','d5a66b','f4dac0'])
    col=K.mix(col,substrate*(.55+.25*np.cos(ang-.8))[...,None],floor)
    lipcolor=K.ramp(.55*h+.45*regional,['875941','e9a769','ffd7a2'])
    col=K.mix(col,lipcolor*(.65+.38*np.cos(ang+2.5))[...,None],rim*.95)
    col=K.mix(col,np.array([.64,.86,.98],F),meniscus*.48)
    col *= (1-.7*crease)[...,None]
    glint=K.sstep(.86,.98,flake)*(1-np.clip(floor+rim,0,1))
    col=K.mix(col,body*1.65+np.array([.08,.08,.1],F),glint*.45)
    satellite=(1-K.sstep(.10,.19,np.hypot(dx-size*1.35,dy-size*.75)/size))*(h>.60)
    col=K.mix(col,np.array([.025,.012,.03],F),satellite*.9)
    M=32+105*flake; R=20+72*flake+24*(1-regional); C=18+110*flake
    if attempt>=4:
        # A4: subdued pigment grains no longer receive large unrelated
        # roughness jumps. Open craters and menisci own the material contrast.
        M=75+65*flake; R=20+24*flake; C=16+55*regional+25*flake
    M,R,C=over(M,R,C,floor,170+70*h,100+105*h,185+65*h)
    M,R,C=over(M,R,C,rim,160+85*h,20+80*(1-h),25+90*h)
    M,R,C=over(M,R,C,meniscus,20+35*h,22+36*h,16+40*h)
    M,R,C=over(M,R,C,crease,5,220,250)
    M,R,C=over(M,R,C,glint,245,20+60*h,25+130*h)
    M,R,C=over(M,R,C,satellite,10,235,255)
    return K.pack(col,M,R,C)

def bth_solvent_pop(seed=42,attempt=1):
    """Angular blister shells rupture; their curved lips remain attached."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+8101,21,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+8102)[lab];t=K.tiers(h)
    theta=np.arctan2(v,u);radius=5.5+2.6*h
    angular=d+1.3*np.cos(theta*3+h*6)+.55*np.sin(theta*7-h*4)
    q=angular/radius
    shell=1-K.sstep(.95,1.23,q)
    mouth=(1-K.sstep(.23,.48,q))*(h>.17)
    split=K.near(np.abs(np.sin(theta*3+h*4))*np.maximum(d,2)/3,.55)*shell*K.sstep(.24,.5,q)
    lip=K.near(np.abs(q-.80)*radius,.8)*(1-split)
    collar=K.near(np.abs(q-1.16)*radius,.85)
    pigment=K.sstep(.72,.90,K.unit(K.noise(seed+8103,230)))*(1-shell)
    region=K.unit(K.fbm(seed+8104,(4,11,27),.60))
    paint=K.ramp(.7*region+.3*t,['521c37','a64357','da806f','f3c399'])
    roof=np.sqrt(np.clip(1-q*q,0,1))
    col=paint*(.70+.34*roof)[...,None]
    col=K.mix(col,np.array([.07,.035,.08],F),mouth*.96)
    col=K.mix(col,paint*.22,split*.90)
    col=K.mix(col,K.ramp(t,['987046','e0bb74','ffe7b0']),lip*.85)
    col=K.mix(col,np.array([.42,.60,.78],F),collar*.65)
    col=K.mix(col,np.array([.96,.72,.65],F),pigment*.55)
    M=35+105*t;R=30+70*(1-roof)+25*t;C=20+125*t
    M,R,C=over(M,R,C,shell,65+120*t,35+80*(1-roof),25+130*t)
    M,R,C=over(M,R,C,mouth,5+15*t,195+50*t,210+40*t)
    M,R,C=over(M,R,C,split,3,225+20*t,230+20*t)
    M,R,C=over(M,R,C,lip,155+95*t,20+55*t,18+85*t)
    M,R,C=over(M,R,C,collar,75+130*t,70+105*t,75+140*t)
    M,R,C=over(M,R,C,pigment,160+85*t,35+65*t,35+100*t)
    return K.pack(col,M,R,C)

def bth_sag_curtain(seed=42,attempt=1):
    """Descending run necks widen into toes and folded wet shoulders."""
    x,y=K.xy();u=x+6*K.noise(seed+8201,50)+3*np.sin(y/19)
    i=np.floor(u/24).astype(np.int32);j=np.floor(y/28).astype(np.int32)
    a=K.frac(u/24)*24-12;b=K.frac(y/28)*28
    h=K.fhash(i,j,seed+8202);t=K.tiers(h)
    # The width grows downstream then contracts; shoulders feed real toes.
    width=3.0+4.0*K.sstep(3,22,b)+1.2*np.sin(b*.3+h*4)
    neck=K.smooth(np.abs(a)-width,1)
    shoulder=K.near(np.abs(np.abs(a)-width),1.0)
    trench=K.near(np.abs(np.abs(a)-width-2.6),.85)
    toe=(1-K.sstep(2.5,4.5,np.hypot(a,b-21)))*(h>.4)
    fold=K.iso(a+b*.21+h*4,8,.7)[0]*neck
    roof=np.clip(1-np.abs(a)/np.maximum(width,1),0,1)
    region=K.unit(K.fbm(seed+8203,(3,9,25),.59))
    base=K.ramp(region,['3e2649','775c83','bda0ad','e5c9b8'])
    run=K.ramp(.6*region+.4*t,['184654','448b92','8ec7b7','e0e6bb'])
    col=K.mix(base,run*(.48+.58*roof)[...,None],neck)
    col=K.mix(col,np.array([.075,.052,.10],F),trench*.9)
    col=K.mix(col,np.array([.98,.79,.51],F),shoulder*.80)
    col=K.mix(col,run*.24,fold*.65)
    col=K.mix(col,np.array([.77,.97,.89],F),toe*.74)
    M=25+80*t;R=80+75*t;C=65+135*t
    M,R,C=over(M,R,C,neck,55+125*t,20+75*(1-roof)+25*t,16+100*t)
    M,R,C=over(M,R,C,trench,5+15*t,190+55*t,205+40*t)
    M,R,C=over(M,R,C,shoulder,155+95*t,25+65*t,25+105*t)
    M,R,C=over(M,R,C,fold,15+55*t,130+100*t,145+90*t)
    M,R,C=over(M,R,C,toe,60+145*t,18+45*t,16+65*t)
    return K.pack(col,M,R,C)

def bth_dry_spray(seed=42,attempt=1):
    """Unflowed splats crowd into a rough dry aggregate with rare wet windows."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+8301,14,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+8302)[lab];t=K.tiers(h)
    theta=np.arctan2(v,u)
    q=(d+.6*np.sin(theta*5+h*6))/(5.2+2*h)
    splat=1-K.sstep(.90,1.12,q)
    rim=K.near(np.abs(q-1.04)*6,.9)
    crown=K.sstep(.65,.92,K.unit(K.noise(seed+8303,250)))*splat
    neck=K.near(K.edge_distance(lab),.85)*K.sstep(.42,.74,h)
    wet=(1-K.sstep(1.2,2.5,np.hypot(u-2,v+1.5)))*(h>.70)
    pore=(1-K.sstep(1,1.8,np.hypot(u+2.5,v-2)))*(h>.42)
    region=K.unit(K.fbm(seed+8304,(4,11,27),.60));roof=np.clip(1-q,0,1)
    base=K.ramp(.6*region+.4*t,['5b4656','a28574','d0b59a','e8d7b6'])
    col=base*(.65+.4*roof)[...,None]
    col=K.mix(col,base*.45,rim*.65)
    col=K.mix(col,np.array([.38,.53,.58],F),neck*.58)
    col=K.mix(col,np.array([.96,.80,.50],F),crown*.7)
    col=K.mix(col,np.array([.75,.93,.90],F),wet*.8)
    col=K.mix(col,np.array([.10,.065,.095],F),pore*.9)
    M=10+60*t;R=150+80*t;C=170+75*t
    M,R,C=over(M,R,C,rim,5+25*t,185+55*t,205+40*t)
    M,R,C=over(M,R,C,crown,85+120*t,75+100*t,70+145*t)
    M,R,C=over(M,R,C,neck,20+55*t,130+100*t,140+95*t)
    M,R,C=over(M,R,C,wet,10+45*t,18+55*t,16+65*t)
    M,R,C=over(M,R,C,pore,0,235,255)
    return K.pack(col,M,R,C)

def bth_mottling(seed=42,attempt=1):
    """Tilted pigment fans collect into clumps separated by actual binder."""
    x,y=K.xy();u,v=K.warp(seed+8401,9,42)
    lab,_,pts=K.voronoi(K.sites(seed+8402,25,1.0));a,b=K.cell_local(lab,pts,u,v)
    h=K.hash01(np.arange(len(pts)),seed+8403)[lab];t=K.tiers(h)
    angle=h*F(K.TAU);p,q=K.rot(a,b,angle)
    fan=K.iso(p+.045*q*q,8,1.6)[0]
    seam=K.near(K.edge_distance(lab),1.0)
    knot=K.near(np.hypot(p-3,q+1),2.4)*(h>.35)
    tip=fan*K.sstep(4,8,p)*(1-K.sstep(8,11,p))
    tilt=np.clip(.5+p/25+q*.015,0,1)
    region=K.unit(K.fbm(seed+8404,(4,10,28),.60))
    warm=K.ramp(.6*region+.4*t,['6b3146','b26767','edbd8a'])
    cool=K.ramp(.65*(1-region)+.35*t,['24445d','4f91a7','a3d9cb'])
    col=K.mix(warm,cool,fan)*(.61+.42*tilt)[...,None]
    col=K.mix(col,np.array([.93,.91,.73],F),seam*.76)
    col=K.mix(col,np.array([.08,.049,.11],F),knot*.85)
    col=K.mix(col,np.array([.93,.98,.91],F),tip*.75)
    M=80+125*t;R=40+90*(1-tilt);C=25+155*t
    M,R,C=over(M,R,C,fan,155+95*t,25+70*tilt,20+130*(1-t))
    M,R,C=over(M,R,C,seam,15+55*t,100+100*t,105+125*t)
    M,R,C=over(M,R,C,knot,25+60*t,170+65*t,185+55*t)
    M,R,C=over(M,R,C,tip,210+40*t,18+40*t,18+70*t)
    return K.pack(col,M,R,C)

def bth_tiger_stripe(seed=42,attempt=1):
    """Gun passes have unequal feather teeth and actual overlap seams."""
    x,y=K.xy();u,v=K.rot(x,y,F(.49));v+=5*K.noise(seed+8501,53)
    j=np.floor(v/24).astype(np.int32);b=K.frac(v/24)*24
    h=K.fhash(np.floor(u/18),j,seed+8502);t=K.tiers(h)
    width=4.5+2.0*h
    d=np.abs(b-11.5-1.2*np.sin(u*.21+h*6))
    core=K.smooth(d-width,1)
    teeth=K.near(np.abs(d-width-1.5),1.5)*K.sstep(.30,.58,K.frac((u+j*3)/8))
    seam=K.near(np.abs(b-21),1.15)
    lip=K.near(np.abs(d-width),.75)
    flake=K.iso(u+b*.26+h*4,8,.8)[0]*core
    region=K.unit(K.fbm(seed+8503,(3,10,28),.61))
    amber=K.ramp(.7*region+.3*t,['63352c','af7348','e9bd7d','f7dfac'])
    violet=K.ramp(.55*region+.45*t,['302447','665079','ab829b'])
    roof=np.clip(1-d/9,0,1)
    col=K.mix(violet,amber*(.62+.44*roof)[...,None],core)
    col=K.mix(col,np.array([.47,.70,.73],F),teeth*.80)
    col=K.mix(col,np.array([.07,.057,.11],F),seam*.92)
    col=K.mix(col,np.array([.97,.91,.72],F),lip*.80)
    col=K.mix(col,amber*.38,flake*.48)
    M=35+80*t;R=75+75*t;C=60+140*t
    M,R,C=over(M,R,C,core,110+125*t,25+65*(1-roof)+25*t,22+115*t)
    M,R,C=over(M,R,C,teeth,25+65*t,140+90*t,150+95*t)
    M,R,C=over(M,R,C,seam,8+20*t,185+55*t,195+50*t)
    M,R,C=over(M,R,C,lip,165+85*t,20+55*t,18+80*t)
    M,R,C=over(M,R,C,flake,120+120*t,60+110*t,65+145*t)
    return K.pack(col,M,R,C)

def bth_die_back(seed=42,attempt=1):
    """Fine collapse wrinkles leave coated survivor lips in deliberately quiet paint."""
    x,y=K.xy();field=K.noise(seed+8601,145)+F(.33)*K.noise(seed+8602,235)
    gx,gy=K.grad(field);d=field/np.maximum(np.hypot(gx,gy),.018)
    wrinkle=K.near(np.abs(d),1.0)
    lip=K.near(np.abs(d-2.6),.75)
    dry=K.near(np.abs(d+1.6),.85)
    density=K.unit(K.noise(seed+8603,160));t=K.tiers(density)
    witness=K.sstep(.79,.95,density)*K.near(np.abs(d),3.7)
    region=K.unit(K.fbm(seed+8604,(4,11,26),.59))
    lacquer=K.ramp(.7*region+.3*t,['433c49','807371','b8a78c','d6c5aa'])
    col=lacquer*(.88+.12*density)[...,None]
    col=K.mix(col,lacquer*.50,wrinkle*.64)
    col=K.mix(col,np.array([.85,.89,.78],F),lip*.44)
    col=K.mix(col,lacquer*.35,dry*.40)
    col=K.mix(col,np.array([.91,.68,.41],F),witness*.66)
    M=15+65*t;R=115+105*t;C=140+100*t
    M,R,C=over(M,R,C,wrinkle,5+25*t,175+65*t,195+50*t)
    M,R,C=over(M,R,C,dry,3,220+25*t,230+20*t)
    M,R,C=over(M,R,C,lip,35+115*t,35+85*t,25+115*t)
    M,R,C=over(M,R,C,witness,120+120*t,25+70*t,25+120*t)
    return K.pack(col,M,R,C)

def bth_blush(seed=42,attempt=1):
    """Moisture haze whitens film; surviving clear binder remains visible."""
    x,y=K.xy();moisture=K.noise(seed+8701,130)+F(.28)*K.noise(seed+8702,240)
    haze=K.sstep(-.02,.15,moisture)
    t=K.tiers(K.unit(K.noise(seed+8703,190)))
    u=x+9*K.noise(seed+8704,60);v=y+5*K.noise(seed+8705,110)
    stringer=K.iso(u+v*.3,8,.85)[0]*haze
    lab,d,pts=K.voronoi(K.sites(seed+8706,14,1.0))
    h=K.hash01(np.arange(len(pts)),seed+8707)[lab]
    droplet=(1-K.sstep(2,3.6,d))*(h>.54)*haze
    meniscus=K.near(np.abs(d-4),.7)*(h>.54)*haze
    witness=K.sstep(.82,.97,t)*(1-haze)
    region=K.unit(K.fbm(seed+8708,(3,10,26),.60))
    rose=K.ramp(.7*region+.3*t,['672b58','a8648a','dca0b4','efcfc6'])
    milk=K.ramp(.65*region+.35*t,['978eac','cbc7cf','eee6d3'])
    col=K.mix(rose,milk,haze*.75)
    col=K.mix(col,rose*.60,stringer*.50)
    col=K.mix(col,np.array([.89,.94,.95],F),droplet*.55)
    col=K.mix(col,rose*.43,meniscus*.56)
    col=K.mix(col,np.array([.98,.77,.54],F),witness*.60)
    M=35+105*t;R=25+75*t;C=16+120*t
    M,R,C=over(M,R,C,haze,8+45*t,95+125*t,100+140*t)
    M,R,C=over(M,R,C,stringer,20+55*t,135+90*t,150+80*t)
    M,R,C=over(M,R,C,droplet,10+35*t,20+45*t,16+65*t)
    M,R,C=over(M,R,C,meniscus,8+25*t,170+65*t,180+65*t)
    M,R,C=over(M,R,C,witness,145+95*t,25+60*t,25+90*t)
    return K.pack(col,M,R,C)

def bth_lifting(seed=42,attempt=1):
    """Attacked coating ribbons buckle and peel away to expose dry primer."""
    x,y=K.xy();u,v=K.warp(seed+8801,13,38);u,v=K.rot(u,v,F(-.62))
    i=np.floor(u/25).astype(np.int32);j=np.floor(v/27).astype(np.int32)
    a=K.frac(u/25)*25;b=K.frac(v/27)*27
    h=K.fhash(i,j,seed+8802);t=K.tiers(h)
    edge=7+2.4*np.sin(b*.24+h*6)
    peeled=K.sstep(edge-1,edge+1,a)*(1-K.sstep(19,21,a))
    tongue=peeled*K.sstep(10,17,b)*(1-K.sstep(21,24,b))
    lip=K.near(np.abs(a-edge),.85)
    hinge=K.near(np.abs(a-20),1.0)
    flake=K.iso(a+b*.38+h*4,8,.8)[0]*tongue
    roof=np.sin(np.clip((a-edge)/np.maximum(21-edge,1),0,1)*F(np.pi))
    region=K.unit(K.fbm(seed+8803,(4,10,27),.60))
    primer=K.ramp(.65*region+.35*t,['303947','727c83','b3b7a5'])
    film=K.ramp(.65*region+.35*t,['4c2754','94648c','dba0b6','f0cfbb'])
    col=K.mix(primer,film*(.47+.60*roof)[...,None],peeled)
    col=K.mix(col,np.array([.97,.82,.50],F),lip*.86)
    col=K.mix(col,np.array([.07,.049,.11],F),hinge*.92)
    col=K.mix(col,film*.29,flake*.68)
    col=K.mix(col,np.array([.62,.83,.81],F),tongue*roof*.24)
    M=8+35*t;R=145+95*t;C=160+85*t
    M,R,C=over(M,R,C,peeled,45+135*t,30+80*(1-roof)+20*t,22+125*t)
    M,R,C=over(M,R,C,tongue,90+130*t,45+80*t,45+145*t)
    M,R,C=over(M,R,C,lip,160+90*t,20+55*t,20+90*t)
    M,R,C=over(M,R,C,hinge,3+15*t,210+35*t,225+25*t)
    M,R,C=over(M,R,C,flake,15+60*t,165+70*t,160+85*t)
    return K.pack(col,M,R,C)
