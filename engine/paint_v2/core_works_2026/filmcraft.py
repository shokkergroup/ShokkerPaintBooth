"""Cut and worked films; layer topology is the design and owns its spec.
SPB-105 / CORE-WORKS 2026-09-30. Owner asks for things a painter cannot do by hand.
"""
import numpy as np
import cv2
from . import kit as K
from .common import over
F=np.float32

def wrap_air_release(seed=42,attempt=1):
    if attempt>=2:
        from .review_refinements import air_release_manifold
        return air_release_manifold(seed,attempt)
    x,y=K.xy();u=x+2.2*K.noise(seed+10901,113);v=y+2.2*K.noise(seed+10902,101)
    i=np.floor(u/20).astype(np.int32);j=np.floor(v/20).astype(np.int32)
    a=K.frac(u/20)*20-10;b=K.frac(v/20)*20-10
    h=K.fhash(i,j,seed+10903);t=K.tiers(h)
    right=K.fhash(i,j,seed+10904)>.36;left=K.fhash(i-1,j,seed+10904)>.36
    down=K.fhash(i,j,seed+10905)>.48;up=K.fhash(i,j-1,seed+10905)>.48
    hd=np.abs(b)+np.where(np.where(a>0,right,left),0,np.maximum(np.abs(a)-2,0))
    vd=np.abs(a)+np.where(np.where(b>0,down,up),0,np.maximum(np.abs(b)-2,0))
    d=np.minimum(hd,vd);channel=K.near(d,1.3);wall=K.near(np.abs(d-2.6),.7)
    throat=channel*K.near(np.abs(a+b-7),1.5);junction=K.near(np.hypot(a,b),2.5)
    dimple=K.near(np.hypot(a-5,b+5),1.6)*(h>.40)
    region=K.unit(K.fbm(seed+10906,(3,9,24),.6));base=K.ramp(region,['283747','687489','b6aebc','e1cfbf']);col=base.copy()
    col=K.mix(col,base*.20,channel*.9);col=K.mix(col,np.array([.91,.77,.50],F),wall*.8)
    col=K.mix(col,np.array([.38,.58,.71],F),throat*.65);col=K.mix(col,base*.12,junction*.7);col=K.mix(col,base*.42,dimple*.55)
    M=25+100*t;R=35+80*t;C=25+110*t
    M,R,C=over(M,R,C,channel,5+20*t,165+75*t,195+50*t)
    M,R,C=over(M,R,C,wall,90+140*t,20+60*t,18+90*t)
    M,R,C=over(M,R,C,throat,20+65*t,115+105*t,130+110*t)
    M,R,C=over(M,R,C,junction,5+15*t,200+40*t,220+30*t)
    M,R,C=over(M,R,C,dimple,20+55*t,90+110*t,85+145*t)
    return K.pack(col,M,R,C)

def wrap_heat_gun(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+11001,26,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11002)[lab];t=K.tiers(h);theta=np.arctan2(v,u)
    rays=6+np.floor(h*4);phase=theta*rays+.075*d*d+h*7
    rib=K.near(np.abs(np.sin(phase))*np.maximum(d,3)/rays,.8)
    cusp=rib*K.sstep(4,9,d);node=1-K.sstep(2,5,d);edge=K.edge_distance(lab)
    shoulder=K.near(np.abs(np.sin(phase+.6))*np.maximum(d,3)/rays,.9)*(1-node)
    witness=K.near(np.abs(edge-2),.7);stretch=np.clip(d/17,0,1)
    region=K.unit(K.fbm(seed+11003,(4,9,23),.6));base=K.ramp(.65*region+.35*t,['0b2d3d','286a81','7ba8aa','d4d7b3'])
    col=base*(.62+.38*(1-stretch))[...,None];col=K.mix(col,base*.24,rib*.8)
    col=K.mix(col,np.array([.92,.71,.40],F),shoulder*.7);col=K.mix(col,np.array([.73,.86,.84],F),node*.55)
    col=K.mix(col,base*.3,witness*.7)
    M=20+95*t;R=35+80*t;C=25+105*t
    M,R,C=over(M,R,C,rib,45+105*t,135+95*t,160+85*t)
    M,R,C=over(M,R,C,cusp,95+130*t,95+110*t,125+115*t)
    M,R,C=over(M,R,C,node,10+45*t,18+40*t,16+45*t)
    M,R,C=over(M,R,C,shoulder,135+105*t,20+65*t,20+90*t)
    M,R,C=over(M,R,C,witness,35+75*t,80+120*t,65+165*t)
    return K.pack(col,M,R,C)

def wrap_lift_curl(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+11101,22,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11102)[lab];t=K.tiers(h);edge=K.edge_distance(lab)
    facing=(u*.7+v*.4)>0;lift=K.near(edge,3.0)*facing*(h>.25)
    underside=K.near(np.abs(edge-1.2),.8)*facing*(h>.25)
    adhesive=K.near(edge,.7)*(1-facing);hinge=K.near(np.abs(edge-4),.75)*facing*(h>.25)
    ruling=K.iso(u*(.6+h)+v*(1.1-h*.4),8,.65)[0]*(1-lift)
    shoulder=K.near(np.abs(edge-2.8),.65)*facing*(h>.25)
    region=K.unit(K.fbm(seed+11103,(4,10,25),.6));film=K.ramp(.65*region+.35*t,['3d1d45','854e7a','c790aa','edc8bb'])
    col=film*(.82+.16*np.clip((u-v)/20,-1,1))[...,None]
    col=K.mix(col,np.array([.35,.25,.17],F),adhesive*.85);col=K.mix(col,film*.3,lift*.55)
    col=K.mix(col,np.array([.49,.77,.82],F),underside*.85);col=K.mix(col,film*.16,hinge*.8)
    col=K.mix(col,np.array([.99,.81,.47],F),shoulder*.85);col=K.mix(col,film*.42,ruling*.48)
    M=35+110*t;R=30+75*t;C=20+100*t
    M,R,C=over(M,R,C,lift,60+130*t,75+110*t,55+150*t)
    M,R,C=over(M,R,C,underside,190+55*t,45+90*t,90+130*t)
    M,R,C=over(M,R,C,adhesive,5+15*t,200+35*t,215+30*t)
    M,R,C=over(M,R,C,hinge,10+30*t,175+65*t,190+50*t)
    M,R,C=over(M,R,C,shoulder,200+45*t,20+50*t,18+75*t)
    M,R,C=over(M,R,C,ruling,25+65*t,110+105*t,125+105*t)
    return K.pack(col,M,R,C)

def wrap_wet_apply(seed=42,attempt=1):
    x,y=K.xy();rng=np.random.default_rng(seed+11201)
    field=cv2.resize(rng.uniform(-1,1,(115,230)).astype(F),(2048,2048),interpolation=cv2.INTER_CUBIC)
    field+=F(.3)*cv2.resize(rng.uniform(-1,1,(151,287)).astype(F),(2048,2048),interpolation=cv2.INTER_CUBIC)
    gx,gy=K.grad(field);d=field/np.maximum(np.hypot(gx,gy),.022)
    liquid=K.sstep(-.4,.6,d);meniscus=K.near(np.abs(d),.8)
    neck=K.near(np.abs(d-2),.85)*liquid;contact=1-K.sstep(-5,-3,d)
    t=K.tiers(K.unit(K.noise(seed+11203,190)))
    particle=K.sstep(.81,.93,K.unit(K.noise(seed+11204,250)))*meniscus
    wake=cv2.GaussianBlur(particle,(1,9),1.1)*(1-liquid)
    region=K.unit(K.fbm(seed+11205,(3,8,23),.6));base=K.ramp(region,['163d4b','4c8c98','adcfcc','e8e7c9'])
    col=base*(.67+.29*liquid)[...,None];col=K.mix(col,np.array([.97,.84,.55],F),meniscus*.8)
    col=K.mix(col,np.array([.22,.36,.45],F),contact*.55);col=K.mix(col,np.array([.10,.07,.10],F),particle*.8)
    col=K.mix(col,base*.32,wake*.6)
    M=15+60*t;R=50+95*t;C=45+135*t
    M,R,C=over(M,R,C,liquid,10+40*t,18+45*t,16+50*t)
    M,R,C=over(M,R,C,meniscus,70+140*t,25+55*t,20+70*t)
    M,R,C=over(M,R,C,neck,25+65*t,35+80*t,20+95*t)
    M,R,C=over(M,R,C,contact,10+30*t,145+85*t,155+90*t)
    M,R,C=over(M,R,C,particle,5+20*t,210+30*t,220+30*t)
    M,R,C=over(M,R,C,wake,15+40*t,125+100*t,140+100*t)
    return K.pack(col,M,R,C)

def wrap_creases(seed=42,attempt=1):
    x,y=K.xy();u=x+3.4*K.noise(seed+11301,99);v=y+3.4*K.noise(seed+11302,110)
    i=np.floor(u/27).astype(np.int32);j=np.floor(v/25).astype(np.int32);a=K.frac(u/27)*27-13.5;b=K.frac(v/25)*25-12.5
    h=K.fhash(i,j,seed+11303);t=K.tiers(h);a-=2*(h-.5);b+=2*(h-.5)
    slope=np.abs(a)+.55*np.abs(b);phase=np.arctan2(b,a);plane=(np.cos(phase*3+h*2)+1)/2
    crease=K.near(np.abs(np.sin(phase*3+h*2))*np.maximum(np.hypot(a,b),2)/3,.65)
    crown=K.near(np.abs(np.sin(phase*3+h*2+.42))*np.maximum(np.hypot(a,b),2)/3,.6)
    pocket=crease*K.sstep(6,12,slope);junction=K.near(np.hypot(a,b),1.7)
    hinge=K.near(np.abs(b-10),.65)*(h>.4)
    region=K.unit(K.fbm(seed+11304,(4,11,23),.6));foil=K.ramp(.6*region+.4*t,['293a58','6e83b0','bdb2ca','edcbb6'])
    col=foil*(.35+.70*plane)[...,None];col=K.mix(col,foil*.15,crease*.75)
    col=K.mix(col,np.array([.98,.84,.50],F),crown*.75);col=K.mix(col,np.array([.035,.025,.05],F),junction*.9)
    col=K.mix(col,foil*.35,hinge*.75)
    M=85+150*t;R=35+100*(1-plane);C=25+130*t
    M,R,C=over(M,R,C,crease,35+75*t,150+85*t,175+70*t)
    M,R,C=over(M,R,C,crown,195+50*t,20+45*t,18+65*t)
    M,R,C=over(M,R,C,pocket,10+25*t,185+55*t,205+40*t)
    M,R,C=over(M,R,C,junction,5+15*t,215+30*t,230+20*t)
    M,R,C=over(M,R,C,hinge,50+100*t,115+105*t,135+105*t)
    return K.pack(col,M,R,C)

def wrap_roll_memory(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+11401,25,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11402)[lab];t=K.tiers(h);hand=np.where(h>.5,1.,-1.).astype(F)
    theta=np.arctan2(v,u)*hand;phase=d-1.25*theta-2*h
    seam=K.iso(phase,8,.85)[0];lip=K.iso(phase-.95,8,.65)[0]
    rib=K.iso(phase+2.2,8,.65)[0];root=K.near(d,1.6);edge=K.near(K.edge_distance(lab),.75)
    curl=K.frac(phase/8);region=K.unit(K.fbm(seed+11403,(4,9,24),.6));base=K.ramp(.65*region+.35*t,['343448','797187','bda8b3','edd0b6'])
    col=base*(.46+.55*np.sin(curl*F(np.pi)))[...,None]
    col=K.mix(col,np.array([.035,.03,.045],F),seam*.87);col=K.mix(col,np.array([.96,.81,.52],F),lip*.85)
    col=K.mix(col,base*.45,rib*.58);col=K.mix(col,np.array([.33,.60,.69],F),root*.65);col=K.mix(col,base*.20,edge*.72)
    M=35+110*t;R=35+70*(1-np.sin(curl*F(np.pi)));C=25+100*t
    M,R,C=over(M,R,C,seam,8+20*t,190+50*t,205+40*t)
    M,R,C=over(M,R,C,lip,165+80*t,20+50*t,18+80*t)
    M,R,C=over(M,R,C,rib,40+85*t,130+95*t,140+105*t)
    M,R,C=over(M,R,C,root,25+65*t,90+120*t,100+140*t)
    M,R,C=over(M,R,C,edge,15+35*t,175+65*t,190+50*t)
    return K.pack(col,M,R,C)

def wrap_ceramic_coat(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+11501,19,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11502)[lab];t=K.tiers(h);a,b=K.rot(u,v,h*6)
    edge=K.edge_distance(lab);terrace=K.iso(np.maximum(np.abs(a),np.abs(b)*1.3)+h*3,8,.75)[0]
    binder=K.near(edge,.8);root=K.near(np.abs(edge-1.2),.65);pore=K.near(np.hypot(a+2,b-1),.85)*(h>.45)
    inclusion=K.near(np.abs(a-b*.4-4),.7)*K.near(np.abs(b+3),1.5)*(h>.60)
    facet=K.frac((a*.6+b*.8+h*5)/8);region=K.unit(K.fbm(seed+11503,(3,10,25),.6))
    ceramic=K.ramp(.7*region+.3*t,['303c51','667f99','bdc5ca','ece2cf']);col=ceramic*(.60+.35*facet)[...,None]
    col=K.mix(col,np.array([.76,.88,.87],F),terrace*.65);col=K.mix(col,ceramic*.22,root*.7)
    col=K.mix(col,np.array([.93,.82,.60],F),binder*.65);col=K.mix(col,np.array([.035,.025,.04],F),pore)
    col=K.mix(col,np.array([.95,.69,.29],F),inclusion*.9)
    M=5+30*t;R=35+95*t+35*facet;C=25+130*t
    M,R,C=over(M,R,C,terrace,10+40*t,20+60*t,20+80*t)
    M,R,C=over(M,R,C,binder,5+20*t,18+40*t,16+50*t)
    M,R,C=over(M,R,C,root,5+15*t,170+70*t,195+45*t)
    M,R,C=over(M,R,C,pore,3,225,250)
    M,R,C=over(M,R,C,inclusion,170+75*t,35+90*t,60+130*t)
    return K.pack(col,M,R,C)

def wrap_panel_seam(seed=42,attempt=1):
    x,y=K.xy();u=x+3*K.noise(seed+10101,91);v=y+3*K.noise(seed+10102,84)
    j=np.floor(v/25).astype(np.int32);i=np.floor((u+j%2*13)/28).astype(np.int32)
    a=K.frac((u+j%2*13)/28)*28-14;b=K.frac(v/25)*25-12.5
    h=K.fhash(i,j,seed+10103);t=K.tiers(h);side=np.abs(a+.18*b)-10.5
    end=np.abs(b)-9;d=np.maximum(side,end)
    roof=1-K.sstep(-.5,.5,d);wall=K.near(np.abs(d+.9),1.2);lip=K.near(np.abs(d+2.1),.6)
    adhesive=K.near(np.abs(d-1.0),.9);key=K.near(np.hypot(a-8,b+7),1.7)*(h>.35)
    notch=K.near(np.abs(a+6),.65)*K.near(np.abs(b-8),2.0)*(h>.4)
    region=K.unit(K.fbm(seed+10104,(4,9,23),.6));base=K.ramp(region,['112e44','396f88','8fafb3','dbd3b3']);panel=K.ramp(.6*region+.4*t,['352744','85618c','c99eac','f5d6b2'])
    col=K.mix(base,panel*(.77+.25*(b+12.5)/25)[...,None],roof)
    col=K.mix(col,panel*.24,wall*.65);col=K.mix(col,np.array([.97,.83,.50],F),lip*.88)
    col=K.mix(col,np.array([.43,.28,.15],F),adhesive*.7);col=K.mix(col,np.array([.54,.83,.89],F),key*.9);col=K.mix(col,base*.12,notch)
    M=30+70*t;R=140+75*t;C=165+80*t
    M,R,C=over(M,R,C,roof,55+130*t,30+60*t,20+100*t)
    M,R,C=over(M,R,C,wall,150+95*t,70+95*t,80+130*t)
    M,R,C=over(M,R,C,lip,225+25*t,18+45*t,16+55*t)
    M,R,C=over(M,R,C,adhesive,5+10*t,205+35*t,215+30*t)
    M,R,C=over(M,R,C,key,200+45*t,25+55*t,25+90*t)
    M,R,C=over(M,R,C,notch,5,235,250)
    return K.pack(col,M,R,C)

def wrap_squeegee(seed=42,attempt=1):
    x,y=K.xy();v=y+2*K.noise(seed+10201,110);row=np.floor(v/20).astype(np.int32)
    b=K.frac(v/20)*20-10;sgn=np.where(row%2==0,1.,-1.).astype(F)
    u=x+sgn*b*.8+3*K.noise(seed+10202,120);i=np.floor(u/26).astype(np.int32)
    a=K.frac(u/26)*26-13;h=K.fhash(i,row,seed+10203);t=K.tiers(h)
    face=1-K.sstep(7,9,np.abs(b));toe=K.near(np.abs(b+7.5),.85)
    root=K.near(np.abs(b-7.5),.7);rib=K.iso(a+2*h,8,.65)[0]*face
    shoulder=K.near(np.abs(b+5.1),1.0);dust=K.near(np.hypot(a-6,b+1),1.0)*(h>.5)
    region=K.unit(K.fbm(seed+10204,(4,11,25),.6));base=K.ramp(region,['0d3b45','367f79','92b68f','e2d8ac']);roof=np.clip((b+8)/16,0,1)
    col=base*(.52+.50*roof)[...,None];col=K.mix(col,np.array([.92,.76,.46],F),toe*.8)
    col=K.mix(col,base*.2,root*.8);col=K.mix(col,base*.45,rib*.55);col=K.mix(col,np.array([.63,.87,.90],F),shoulder*.45);col=K.mix(col,np.array([.025,.03,.035],F),dust)
    M=30+105*t;R=70+100*t;C=65+145*t
    M,R,C=over(M,R,C,face,45+120*t,25+70*(1-roof),20+80*t)
    M,R,C=over(M,R,C,toe,180+65*t,20+50*t,20+85*t)
    M,R,C=over(M,R,C,root,10+20*t,190+50*t,205+40*t)
    M,R,C=over(M,R,C,rib,15+45*t,130+100*t,160+80*t)
    M,R,C=over(M,R,C,shoulder,55+90*t,20+40*t,16+60*t)
    M,R,C=over(M,R,C,dust,5,235,250)
    return K.pack(col,M,R,C)

def wrap_microbubble(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+10301,17,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+10302)[lab];t=K.tiers(h);theta=np.arctan2(v,u)
    r=d*(1+.14*np.sin(theta*4+h*6)+.10*np.cos(theta*3));rad=7+2*h;q=r/rad
    cap=1-K.sstep(.85,1.15,q);roof=np.sqrt(np.clip(1-q*q,0,1));root=K.near(np.abs(q-.98)*rad,.75)
    shoulder=K.near(np.abs(q-.72)*rad,.8);vent=K.near(np.hypot(u-4.1,v+3.8),.8)*(h>.64)*cap
    web=K.near(K.edge_distance(lab),1.0)
    region=K.unit(K.fbm(seed+10303,(3,8,24),.6));base=K.ramp(region,['293845','667983','bac2b6','eddfc1'])
    col=base*(.54+.50*roof+.12*np.clip((u-v)/14,-1,1))[...,None]
    col=K.mix(col,base*.18,root*.75);col=K.mix(col,np.array([.92,.87,.67],F),shoulder*.6)
    col=K.mix(col,base*.30,web*.55);col=K.mix(col,np.array([.02,.03,.035],F),vent)
    M=10+35*t;R=100+110*t;C=100+135*t
    M,R,C=over(M,R,C,cap,15+70*t,18+55*(1-roof)+25*t,16+70*t)
    M,R,C=over(M,R,C,root,10+25*t,140+90*t,155+80*t)
    M,R,C=over(M,R,C,shoulder,40+100*t,20+50*t,20+75*t)
    M,R,C=over(M,R,C,web,5+20*t,165+70*t,185+60*t)
    M,R,C=over(M,R,C,vent,2,235,250)
    return K.pack(col,M,R,C)

def wrap_laminate(seed=42,attempt=1):
    x,y=K.xy();a,b=K.rot(x+3*K.noise(seed+10401,91),y+3*K.noise(seed+10402,103),F(.37))
    i=np.floor(a/25).astype(np.int32);j=np.floor(b/23).astype(np.int32);u=K.frac(a/25)*25-12.5;v=K.frac(b/23)*23-11.5
    h=K.fhash(i,j,seed+10403);t=K.tiers(h)
    d=np.maximum(np.abs(u+.3*v)-7,np.abs(v)-7);top=K.sstep(-.5,.5,d)
    lower=K.sstep(-.5,.5,np.maximum(np.abs(u-3-.15*v)-7,np.abs(v+3)-7))
    lip=K.near(np.abs(d),.7);double=K.near(np.abs(np.maximum(np.abs(u-3-.15*v)-7,np.abs(v+3)-7)),.7)*(1-top)
    r1=K.iso(a+b*.3,8,.75)[0]*top;r2=K.iso(b-a*.2,9,.8)[0]*(1-top)
    overlap=top*lower;region=K.unit(K.fbm(seed+10404,(4,11,25),.6))
    foil=K.ramp(region,['22354f','587f94','b1b5a7','e8d5b1']);film=K.ramp(.7*region+.3*t,['331f4f','8061a0','c0a2c2','f0d1c1'])
    col=K.mix(foil,film,top*.78);col=K.mix(col,foil*.35,r2*.72);col=K.mix(col,film*.35,r1*.55)
    col=K.mix(col,np.array([.98,.83,.49],F),lip*.78);col=K.mix(col,np.array([.45,.77,.83],F),double*.85)
    col=K.mix(col,film*.84,overlap*.15)
    M=180+65*t;R=55+95*t;C=35+115*t
    M,R,C=over(M,R,C,top,20+75*t,25+60*t,16+70*t)
    M,R,C=over(M,R,C,overlap,30+85*t,45+65*t,25+70*t)
    M,R,C=over(M,R,C,r1,15+45*t,135+90*t,160+80*t)
    M,R,C=over(M,R,C,r2,75+130*t,145+75*t,155+85*t)
    M,R,C=over(M,R,C,lip,205+45*t,20+40*t,16+65*t)
    M,R,C=over(M,R,C,double,165+80*t,35+60*t,25+95*t)
    return K.pack(col,M,R,C)

def wrap_brushed_film(seed=42,attempt=1):
    if attempt>=2:return _dense_mill_grain(seed,attempt)
    x,y=K.xy();rng=np.random.default_rng(seed+10501);grooves=np.zeros((2048,2048),np.uint8);ends=grooves.copy();cross=grooves.copy()
    centers=rng.uniform(-20,2068,(17000,2));angles=rng.normal(.36,.26,len(centers));length=rng.uniform(10,27,len(centers))
    for i,(center,angle,L) in enumerate(zip(centers,angles,length)):
        along=np.array([np.cos(angle),np.sin(angle)]);across=np.array([-along[1],along[0]])
        for k in range(-2,3):
            a=(center+across*k*1.7-along*(L/2)).astype(np.int32);b=(center+across*k*1.7+along*(L/2-abs(k))).astype(np.int32)
            cv2.line(grooves,tuple(a),tuple(b),int(80+175*((i+k)%8)/7),1,cv2.LINE_AA)
            if k==2:cv2.line(ends,tuple(b),tuple(b+across.astype(np.int32)*2),200,1,cv2.LINE_AA)
        if i%5==0:
            cv2.line(cross,tuple((center-across*3).astype(np.int32)),tuple((center+across*3).astype(np.int32)),230,1,cv2.LINE_AA)
    g=grooves.astype(F)/255;e=ends.astype(F)/255;c=cross.astype(F)/255;lip=np.clip(np.roll(g,1,0)-g,0,1)
    t=K.tiers(K.unit(K.noise(seed+10502,180)));region=K.unit(K.fbm(seed+10503,(4,9,25),.6));base=K.ramp(region,['303940','687e80','b4b6a5','e6d6b6'])
    col=base*(.85+.15*t)[...,None];col=K.mix(col,base*.40,g*.65);col=K.mix(col,np.array([.94,.84,.63],F),lip*.85)
    col=K.mix(col,np.array([.36,.65,.72],F),e*.7);col=K.mix(col,base*.25,c*.85)
    M=190+55*t;R=90+80*t;C=100+115*t
    M,R,C=over(M,R,C,g,170+70*t,145+85*t,170+75*t)
    M,R,C=over(M,R,C,lip,225+25*t,25+65*t,40+110*t)
    M,R,C=over(M,R,C,e,160+80*t,65+115*t,90+140*t)
    M,R,C=over(M,R,C,c,125+100*t,195+40*t,215+30*t)
    return K.pack(col,M,R,C)

def _dense_mill_grain(seed,attempt):
    """A2: full-sheet mill grain, vectorized 8–28px filament bundles."""
    x,y=K.xy();rng=np.random.default_rng(seed+10511);count=79000
    centers=rng.uniform(-20,2068,(count,2)).astype(F);angle=rng.normal(.36,.23,count).astype(F);L=rng.uniform(8,27,count).astype(F)
    along=np.stack((np.cos(angle),np.sin(angle)),1);across=np.stack((-along[:,1],along[:,0]),1)
    offsets=np.arange(-2,3,dtype=F)[None,:,None]
    start=centers[:,None,:]+across[:,None,:]*offsets*F(1.7)-along[:,None,:]*L[:,None,None]/2
    end=centers[:,None,:]+across[:,None,:]*offsets*F(1.7)+along[:,None,:]*(L[:,None,None]/2-np.abs(offsets))
    paths=np.rint(np.stack((start,end),2)).astype(np.int32).reshape(-1,2,2)
    weights=np.repeat(np.arange(count)%8,5)
    groove=np.zeros((2048,2048),np.uint8);burr=groove.copy();cross=groove.copy()
    for tier in range(8):cv2.polylines(groove,list(paths[weights==tier]),False,80+25*tier,1,cv2.LINE_AA)
    ends=np.rint(np.stack((end[:,4,:],end[:,4,:]+across*3),1)).astype(np.int32)
    cv2.polylines(burr,list(ends),False,210,1,cv2.LINE_AA)
    crosspaths=np.rint(np.stack((centers[::5]-across[::5]*4,centers[::5]+across[::5]*4),1)).astype(np.int32)
    cv2.polylines(cross,list(crosspaths),False,230,1,cv2.LINE_AA)
    g=groove.astype(F)/255;b=burr.astype(F)/255;c=cross.astype(F)/255;lip=np.clip(np.roll(g,1,0)-g,0,1)
    t=K.tiers(K.unit(K.noise(seed+10512,220)));region=K.unit(K.fbm(seed+10513,(3,9,24),.6));base=K.ramp(region,['253b49','5a7e89','aebcaf','e6d6b1'])
    col=base*(.87+.13*t)[...,None];col=K.mix(col,base*.32,g*.70)
    col=K.mix(col,np.array([.96,.85,.61],F),lip*.87);col=K.mix(col,np.array([.38,.67,.78],F),b*.72);col=K.mix(col,base*.20,c*.8)
    M=190+55*t;R=90+85*t;C=100+125*t
    M,R,C=over(M,R,C,g,165+80*t,145+90*t,170+75*t)
    M,R,C=over(M,R,C,lip,225+25*t,25+65*t,40+115*t)
    M,R,C=over(M,R,C,b,160+80*t,65+115*t,90+140*t)
    M,R,C=over(M,R,C,c,120+110*t,190+50*t,210+35*t)
    return K.pack(col,M,R,C)

def wrap_print_band(seed=42,attempt=1):
    x,y=K.xy();a,b=K.rot(x,y,F(.57));a+=2*K.noise(seed+10601,143)
    j=np.floor(b/25).astype(np.int32);u=K.frac(b/25)*25;h=K.fhash(np.floor(a/29).astype(np.int32),j,seed+10602);t=K.tiers(h)
    c=1-K.sstep(5.5,6.5,np.abs(u-7));m=1-K.sstep(5.5,6.5,np.abs(u-11-1.4*h));yellow=1-K.sstep(5.5,6.5,np.abs(u-15+1.5*h))
    trap=np.clip(c*m+m*yellow,0,1);dot=K.near(np.hypot(K.frac(a/8)*8-4,K.frac(b/8)*8-4),1.4)*np.clip(c+m+yellow,0,1)
    slot=K.near(np.abs(K.frac(a/29)*29-23),1.1)*K.near(np.abs(u-11),3.3)*(h>.47)
    region=K.unit(K.fbm(seed+10603,(3,9,23),.6));base=K.ramp(region,['38445a','7c92a0','c1c3b4','e8d8b5'])
    col=K.mix(base,np.array([.13,.63,.70],F),c*.83);col=K.mix(col,np.array([.70,.20,.43],F),m*.70);col=K.mix(col,np.array([.91,.68,.22],F),yellow*.65)
    col=K.mix(col,col*.24,trap*.55);col=K.mix(col,np.array([.09,.04,.10],F),dot*.7);col=K.mix(col,base*1.15,slot)
    M=180+65*t;R=55+80*t;C=50+100*t
    M,R,C=over(M,R,C,c,10+45*t,65+110*t,60+145*t)
    M,R,C=over(M,R,C,m,20+65*t,40+95*t,25+115*t)
    M,R,C=over(M,R,C,yellow,35+95*t,35+85*t,25+95*t)
    M,R,C=over(M,R,C,trap,10+35*t,160+70*t,180+60*t)
    M,R,C=over(M,R,C,dot,5+35*t,130+95*t,150+90*t)
    M,R,C=over(M,R,C,slot,220+30*t,20+45*t,20+60*t)
    return K.pack(col,M,R,C)

def wrap_perf_window(seed=42,attempt=1):
    x,y=K.xy();u=x+2*K.noise(seed+10701,110);v=y+2*K.noise(seed+10702,117)
    j=np.floor(v/18).astype(np.int32);i=np.floor((u+j%2*11)/22).astype(np.int32)
    a=K.frac((u+j%2*11)/22)*22-11;b=K.frac(v/18)*18-9;h=K.fhash(i,j,seed+10703);t=K.tiers(h)
    aa,bb=K.rot(a,b,np.where(j%2==0,.37,-.37).astype(F));length=3+3*h
    d=np.hypot(np.maximum(np.abs(aa)-length,0),bb)-3.1
    hole=1-K.sstep(-.45,.45,d);lip=K.near(np.abs(d-.8),.7);burr=lip*K.sstep(.2,.6,aa/(length+2))
    ruling=K.iso(u+v*.25,8,.65)[0]*(1-hole);bridge=K.near(np.abs(b+8),.7)*(1-hole)
    region=K.unit(K.fbm(seed+10704,(4,10,24),.6));film=K.ramp(region,['314748','699d90','b6c4a2','e8d8ad'])
    col=K.mix(film,np.array([.035,.04,.06],F),hole);col=K.mix(col,np.array([.93,.78,.50],F),lip*.85)
    col=K.mix(col,np.array([.40,.65,.76],F),burr*.7);col=K.mix(col,film*.45,ruling*.55);col=K.mix(col,film*.25,bridge*.6)
    M=45+105*t;R=40+80*t;C=25+110*t
    M,R,C=over(M,R,C,hole,3+8*t,190+50*t,205+40*t)
    M,R,C=over(M,R,C,lip,185+60*t,20+45*t,20+65*t)
    M,R,C=over(M,R,C,burr,140+100*t,90+115*t,125+115*t)
    M,R,C=over(M,R,C,ruling,25+65*t,130+95*t,140+105*t)
    M,R,C=over(M,R,C,bridge,15+40*t,100+100*t,90+145*t)
    return K.pack(col,M,R,C)

def wrap_knife_edge(seed=42,attempt=1):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+10801,24,1.0));u,v=K.cell_local(lab,pts,x,y)
    edge=K.edge_distance(lab);h=K.hash01(np.arange(len(pts)),seed+10802)[lab];t=K.tiers(h)
    bridge=K.sstep(.66,.85,K.unit(K.noise(seed+10803,163)));cut=K.near(edge,.7)*(1-bridge)
    flap=K.near(np.abs(edge-2.5),1.3)*(h>.48)*(1-bridge)
    wall=K.near(np.abs(edge-1.2),.7)*(1-bridge);hinge=K.near(np.abs(edge-4.2),.65)*(h>.48)*(1-bridge)
    turn=K.sstep(.76,.9,K.unit(K.noise(seed+10804,230)))*wall
    ruling=K.iso(u*.6+v*.8+h*7,9,.7)[0]*(1-np.clip(cut+flap,0,1))
    region=K.unit(K.fbm(seed+10805,(3,10,25),.6));base=K.ramp(region,['1a304b','506b8f','aaa8bb','e9cfc0'])
    col=base.copy();col=K.mix(col,np.array([.025,.02,.035],F),cut*.95);col=K.mix(col,base*.47,flap*.7)
    col=K.mix(col,np.array([.94,.78,.44],F),wall*.82);col=K.mix(col,base*.20,hinge*.85)
    col=K.mix(col,np.array([.54,.85,.88],F),turn*.8);col=K.mix(col,base*.45,ruling*.45)
    M=40+105*t;R=30+80*t;C=20+100*t
    M,R,C=over(M,R,C,cut,5+10*t,195+50*t,215+30*t)
    M,R,C=over(M,R,C,flap,65+135*t,65+100*t,40+130*t)
    M,R,C=over(M,R,C,wall,195+50*t,20+45*t,20+70*t)
    M,R,C=over(M,R,C,hinge,10+35*t,175+65*t,195+50*t)
    M,R,C=over(M,R,C,turn,135+110*t,100+110*t,120+110*t)
    M,R,C=over(M,R,C,ruling,30+70*t,95+105*t,130+105*t)
    return K.pack(col,M,R,C)

def wrap_layered_cut(seed=42, attempt=1):
    """Interlocking cut-foil tongues, exposed backing and fine registration edges."""
    if attempt>=4:
        return _layered_lace(seed,attempt)
    x,y=K.xy()
    wx,wy=K.warp(seed+1001,25,9)
    a,b=K.rot(wx,wy,F(.58))
    region=K.unit(K.fbm(seed+1002,(4,8,16),.55))
    # Two independently cut sheets interlock. Variable tooth lengths, deliberate
    # registration offset and exposed underside give material ownership.
    row=np.floor(b/F(24.)).astype(np.int32)
    local=b/F(24.)-row
    shift=K.fhash(row,None,seed+1003)*F(28.)
    ui=(a+shift)/F(28.)
    cell=np.floor(ui).astype(np.int32); u=ui-cell
    h=K.fhash(cell,row,seed+1004)
    tooth=.20+.58*(1-np.abs(u-.5)*2)+.08*np.sin(u*F(K.TAU))
    upper=K.sstep(tooth-.04,tooth+.02,local)
    lower=1-K.sstep(tooth+.15,tooth+.21,local)
    exposed=np.clip(1-upper-lower,0,1)
    overlap=np.clip(upper+lower-1,0,1)
    seam=K.near(local-tooth,.035)+K.near(local-tooth-.18,.035)
    if attempt>=2:
        seam=K.near((local-tooth)*24,.8)+K.near((local-tooth-.18)*24,.8)
    if attempt>=3:
        # A3: narrow cut edges require absolute native-pixel distances. A2's
        # signed bands filled faces and failed the visible flat-cut identity.
        seam=K.near(np.abs((local-tooth)*24),.8)+K.near(np.abs((local-tooth-.18)*24),.8)
    tone=K.tiers(h)
    backing=K.ramp(.6*region+.4*tone,['080717','142739','215967','68a3a3'])
    foil_a=K.ramp(.65*region+.35*tone,['390b22','861b44','e33c70','ffc179'])
    foil_b=K.ramp(.7*(1-region)+.3*tone,['0b291d','38702e','7bab34','d2ed69'])
    if attempt>=2:
        foil_a=K.ramp(.65*region+.35*tone,['241137','633898','ad69ce','f0b5de'])
        foil_b=K.ramp(.7*(1-region)+.3*tone,['05273e','176e91','34bfca','a2efdc'])
    col=K.mix(backing,foil_a,upper)
    col=K.mix(col,foil_b,lower)
    col *= (.70+.35*np.sin(np.clip(local,0,1)*F(np.pi)))[...,None]
    # An exposed adhesive lip is warm and matte; the cut is a narrow polished edge.
    adhesive=K.near(local-tooth-.10,.028)*exposed
    if attempt>=2:
        adhesive=K.near((local-tooth-.10)*24,.65)*exposed
    if attempt>=3:
        adhesive=K.near(np.abs((local-tooth-.10)*24),.65)*exposed
    col=K.mix(col,np.array([.91,.70,.31],F),adhesive)
    col=K.mix(col,np.array([.94,.96,.99],F),np.clip(seam,0,1)*.80)
    printline=K.iso(a+row*5,9,1.0)[0]*upper*(.15+.4*tone)
    col=K.mix(col,foil_a*.38,printline*.4)
    pin=K.near(np.hypot((u-.85)*28,(local-.87)*24),1.6)*(h>.64)
    col=K.mix(col,np.array([.1,.1,.14],F),pin)
    M=30+75*tone; R=140+65*tone; C=190+60*tone
    M,R,C=over(M,R,C,upper,205+45*tone,18+85*tone,20+190*(1-tone))
    M,R,C=over(M,R,C,lower,20+55*tone,70+110*tone,35+95*tone)
    M,R,C=over(M,R,C,overlap,145+70*tone,35+85*tone,80+150*tone)
    M,R,C=over(M,R,C,np.clip(seam,0,1),245,18+55*tone,16+90*tone)
    M,R,C=over(M,R,C,adhesive,4,230,250)
    M,R,C=over(M,R,C,printline,25+40*tone,135+95*tone,190+55*tone)
    M,R,C=over(M,R,C,pin,0,240,255)
    return K.pack(col,M,R,C)

def _layered_lace(seed,attempt):
    """Two independent laser-cut lattices: openings expose the other sheet.

    A4 rejects the toothed-row carrier. Interpenetrating flat cut sheets own
    the material map; exposed backing and undercut lips prove layer topology.
    """
    x,y=K.xy()
    u,v=K.warp(seed+1011,8,13)
    a,b=K.rot(u,v,F(.28))
    c,e=K.rot(u,v,F(-.61))
    f=np.sin(a/F(4.2))*np.sin(b/F(4.5))
    g=np.cos(c/F(4.8))+F(.72)*np.cos(e/F(3.8))
    top=K.sstep(-.12,.12,f)
    second=K.sstep(-.18,.14,g)
    # Sheet openings are 8-25px; each sheet forms continuous cut webs.
    rim=K.near(np.abs(f)/np.maximum(np.hypot(*K.grad(f)),.05),.85)
    lower_rim=K.near(np.abs(g)/np.maximum(np.hypot(*K.grad(g)),.05),.8)*(1-top)
    region=K.unit(K.fbm(seed+1012,(3,8,19),.60))
    tile=K.fhash(np.floor(a/26).astype(np.int32),np.floor(b/28).astype(np.int32),seed+1013)
    tier=K.tiers(tile)
    substrate=K.ramp(region,['0a1731','183a51','396167','9da3a0'])
    foil=K.ramp(.75*region+.25*tier,['22172e','683474','bd66a5','eac6be'])
    under=K.ramp(.7*(1-region)+.3*tier,['274537','669560','bacc85','f4e6b9'])
    roof=np.clip(np.abs(f),0,1)
    foil *= (.57+.50*roof)[...,None]
    under *= (.6+.4*np.clip(np.abs(g)/1.72,0,1))[...,None]
    col=K.mix(substrate,under,second)
    col=K.mix(col,foil,top)
    col=K.mix(col,np.array([.13,.058,.10],F),lower_rim*.9)
    adhesive=K.near(np.abs(g)/np.maximum(np.hypot(*K.grad(g)),.05),1.7)*(1-top)*(1-second)
    col=K.mix(col,np.array([.58,.35,.18],F),adhesive*.60)
    col=K.mix(col,np.array([.99,.85,.56],F),rim*.68)
    ruling=K.iso(a-b*.27,8,.8)[0]*top*roof
    col=K.mix(col,foil*.42,ruling*.45)
    puncture=(1-K.sstep(1,2,np.hypot(K.frac(a/26)*26-17,K.frac(b/28)*28-18)))*(tile>.56)*top
    col=K.mix(col,np.array([.015,.025,.04],F),puncture)
    M=30+55*tier; R=145+80*tier; C=175+75*tier
    M,R,C=over(M,R,C,second,185+65*tier,50+100*(1-roof),30+115*tier)
    M,R,C=over(M,R,C,top,45+115*tier,28+45*(1-roof),16+65*tier)
    M,R,C=over(M,R,C,lower_rim,15+20*tier,195+45*tier,210+40*tier)
    M,R,C=over(M,R,C,adhesive,5,225+25*tier,230+25*tier)
    M,R,C=over(M,R,C,rim,220+30*tier,18+36*tier,16+50*tier)
    M,R,C=over(M,R,C,ruling,30+80*tier,100+115*tier,140+95*tier)
    M,R,C=over(M,R,C,puncture,0,240,255)
    return K.pack(col,M,R,C)

def wrap_holographic(seed=42, attempt=1):
    """Security-foil rosettes with locally ruled diffraction sectors and ink windows."""
    x,y=K.xy()
    lab,d,pts=K.voronoi(K.sites(seed+1201,31,1.0))
    dx,dy=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+1202)[lab]
    theta=np.arctan2(dy,dx)
    petals=5+np.floor(h*4)
    rosette=d+2.0*np.cos(theta*petals+h*6)
    etched,_,rphase=K.iso(rosette,8,1.2)
    phase=h*F(K.TAU)
    ray=K.iso(dx*np.cos(phase)+dy*np.sin(phase),9,1.1)[0]
    if attempt>=3:
        # Engraving removes the foil ruling. Its material cannot simultaneously
        # be a polished ruling and a rough trench at their intersection.
        ray *= 1-etched
    faceted=(np.floor((theta+np.pi)*petals/F(K.TAU))%2)
    region=K.unit(K.fbm(seed+1203,(3,7,16),.6))
    film=K.thin_film(.50*region+.24*h+.07*rosette+.12*faceted,.97,.86)
    if attempt>=2:
        family=K.ramp(region,['542045','b44273','ee945d','e9d777','2eaaa9','1b327a'])
        film=K.mix(family,K.thin_film(.50*region+.24*h+.12*rphase+.12*faceted,.97,.86),.22)
    col=film*(.58+.42*(1-etched)+.20*faceted)[...,None]
    if attempt>=3:
        col=film*(.65+.30*(1-etched)+.08*faceted)[...,None]
    col=K.mix(col,film*.32,etched*.72)
    col=K.mix(col,np.minimum(film*1.2+.12,1),ray*.35)
    centre=1-K.sstep(2.5,4.5,d)
    col=K.mix(col,np.array([.92,.93,.88],F),centre*.85)
    edge=K.near(K.edge_distance(lab),1.0)
    col=K.mix(col,np.array([.05,.018,.095],F),edge*.8)
    ghost=K.near(np.abs(rosette-9.5),.9)*(h>.72)
    col=K.mix(col,np.array([.98,.79,.44],F),ghost*.65)
    tier=K.tiers(h)
    M=180+70*tier; R=22+85*faceted+35*tier; C=16+170*tier
    if attempt>=3:
        M=185+45*tier; R=18+32*faceted+20*tier; C=16+60*tier
    M,R,C=over(M,R,C,etched,35+85*tier,140+80*tier,170+70*tier)
    if attempt>=3:
        M,R,C=over(M,R,C,etched,20+55*tier,180+55*tier,195+50*tier)
    M,R,C=over(M,R,C,ray,225+25*tier,22+65*tier,25+145*(1-tier))
    M,R,C=over(M,R,C,centre,230,16,16)
    M,R,C=over(M,R,C,edge,5,230,250)
    M,R,C=over(M,R,C,ghost,170+75*tier,40+75*tier,35+165*tier)
    return K.pack(col,M,R,C)
