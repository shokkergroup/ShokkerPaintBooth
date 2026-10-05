"""Independent routed, woven, fractured and optical film constructions.
SPB-105 / CORE-WORKS 2026-09-30; owner: fine jaw-dropping work, not recolours.
"""
import cv2
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def wrap_hex_ppf(seed=42,attempt=1):
    if attempt>=2:return _elastic_hex_film(seed)
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+11601,25,.10));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11602)[lab];t=K.tiers(h)
    q=np.maximum(np.abs(u),np.maximum(np.abs(u*.5+v*.8660254),np.abs(u*.5-v*.8660254)))
    a,b=K.rot(u,v,F(.26));inner=np.maximum(np.abs(a),np.maximum(np.abs(a*.5+b*.8660254),np.abs(a*.5-b*.8660254)))
    key=1-K.sstep(9.3,10.3,q);insert=1-K.sstep(4.8,5.8,inner);gasket=K.near(np.abs(q-11),.8)
    shoulder=K.near(np.abs(q-9),.7);cut=K.near(np.abs(inner-6.4),.7)
    catch=K.near(np.abs(u),1.2)*K.near(np.abs(v-7.5),2.1)*(h>.3)
    theta=np.arctan2(v,u);notch=K.near(np.abs(np.sin(theta*3+h*6))*np.maximum(d,2)/3,.65)*K.sstep(7,10,q)
    region=K.unit(K.fbm(seed+11603,(4,9,24),.6));film=K.ramp(region,['213b4a','537b8a','a0b5b2','e1d6b5']);metal=K.ramp(t,['554a64','967795','c1a6ac','e9cba1'])
    col=K.mix(film,metal*(.58+.35*np.clip((u-v)/22+.5,0,1))[...,None],key)
    col=K.mix(col,film*(.72+.24*np.cos(theta))[...,None],insert);col=K.mix(col,np.array([.10,.07,.07],F),gasket*.85)
    col=K.mix(col,np.array([.99,.83,.48],F),shoulder*.9);col=K.mix(col,np.array([.47,.79,.84],F),cut*.85)
    col=K.mix(col,np.array([.92,.73,.40],F),catch*.9);col=K.mix(col,metal*.22,notch*.8)
    # Protective film is dielectric. The cell pattern is an elastic/adhesive
    # witness, not the rejected provisional metal-key interpretation.
    M=5+20*t;R=70+100*t;C=65+145*t
    M,R,C=over(M,R,C,key,8+30*t,25+65*t,16+75*t)
    M,R,C=over(M,R,C,insert,10+40*t,20+55*t,16+65*t)
    M,R,C=over(M,R,C,gasket,5+15*t,200+35*t,220+25*t)
    M,R,C=over(M,R,C,shoulder,15+45*t,18+40*t,16+60*t)
    M,R,C=over(M,R,C,cut,10+35*t,95+110*t,100+135*t)
    M,R,C=over(M,R,C,catch,65+95*t,25+55*t,25+85*t)
    M,R,C=over(M,R,C,notch,5+20*t,160+75*t,185+55*t)
    return K.pack(col,M,R,C)

def wrap_twill_film(seed=42,attempt=1):
    x,y=K.xy();u=x+2.2*K.noise(seed+11701,112);v=y+2.2*K.noise(seed+11702,124)
    i=np.floor(u/13).astype(np.int32);j=np.floor(v/13).astype(np.int32);a=K.frac(u/13)*13-6.5;b=K.frac(v/13)*13-6.5
    h=K.fhash(i,j,seed+11703);t=K.tiers(h);warp=1-K.sstep(4.3,5.2,np.abs(a));weft=1-K.sstep(4.3,5.2,np.abs(b))
    top=((i-j)%3!=0).astype(F);w=warp*(1-weft*(1-top));f=weft*(1-warp*top)
    wc=np.clip(1-(a/5)**2,0,1);fc=np.clip(1-(b/5)**2,0,1)
    filament=(K.near(np.abs(np.abs(a)-2.8),.55)*w+K.near(np.abs(np.abs(b)-2.8),.55)*f)
    under=warp*weft*(1-top);split=K.near(np.abs(a-1.1),.55)*K.near(np.abs(b-4.5),1.2)*(h>.65)*w
    region=K.unit(K.fbm(seed+11704,(3,10,24),.6));metal=K.ramp(.65*region+.35*t,['253b54','597b93','aebbad','e8d4a5']);ink=K.ramp(.7*(1-region)+.3*t,['341f4d','7e4e83','c892ad','ecd0bd'])
    col=np.broadcast_to(np.array([.035,.03,.05],F),(2048,2048,3)).copy()
    col=K.mix(col,ink*(.40+.63*fc)[...,None],f);col=K.mix(col,metal*(.40+.63*wc)[...,None],w)
    col=K.mix(col,np.array([.99,.82,.48],F),filament*.60);col=K.mix(col,np.array([.035,.025,.04],F),split*.85)
    M=5+15*t;R=190+45*t;C=205+40*t
    M,R,C=over(M,R,C,f,35+100*t,35+80*(1-fc),20+100*t)
    M,R,C=over(M,R,C,w,175+75*t,30+85*(1-wc),35+150*t)
    M,R,C=over(M,R,C,under*(1-w),35+90*t,100+110*t,120+110*t)
    M,R,C=over(M,R,C,np.clip(filament,0,1),200+45*t,20+55*t,20+85*t)
    M,R,C=over(M,R,C,split,10+25*t,210+30*t,225+25*t)
    return K.pack(col,M,R,C)

def wrap_truchet_knurl(seed=42,attempt=1):
    if attempt>=2:return truchet_facet_knurl(seed,attempt)
    x,y=K.xy();i=np.floor(x/22).astype(np.int32);j=np.floor(y/22).astype(np.int32)
    u=K.frac(x/22)*22;v=K.frac(y/22)*22;h=K.fhash(i,j,seed+11801);t=K.tiers(h)
    flip=h>.5;a=np.where(flip,u,22-u);b=v
    d1=np.hypot(a,b)-11;d2=np.hypot(22-a,22-b)-11;d=np.where(np.abs(d1)<np.abs(d2),d1,d2)
    path=K.near(np.abs(d),2.6);rail=K.near(np.abs(np.abs(d)-2.15),.55)
    insert=K.near(np.abs(d),.75);well=K.near(np.hypot(u-11,v-11),2.3)*((i+j)%2==0)
    seam=K.near(np.minimum(np.minimum(u,22-u),np.minimum(v,22-v)),.6)*path
    key=K.near(np.abs(u-v),.65)*K.near(np.hypot(u-11,v-11),3.2)*(h>.65)
    region=K.unit(K.fbm(seed+11802,(4,9,23),.6));metal=K.ramp(.6*region+.4*t,['244353','5a8c93','a8c6b0','e6d6a5']);back=K.ramp(region,['21152f','4f2d55','8f5b78','be9b9b'])
    roof=np.sqrt(np.clip(1-(d/3)**2,0,1));col=K.mix(back,metal*(.48+.55*roof)[...,None],path)
    col=K.mix(col,np.array([.97,.79,.44],F),rail*.82);col=K.mix(col,back*.7,insert*.65)
    col=K.mix(col,np.array([.035,.025,.04],F),well*.85);col=K.mix(col,metal*.28,seam*.65)
    col=K.mix(col,np.array([.49,.78,.85],F),key*.85)
    M=30+75*t;R=95+100*t;C=80+145*t
    M,R,C=over(M,R,C,path,170+75*t,30+85*(1-roof),35+125*t)
    M,R,C=over(M,R,C,rail,225+25*t,18+45*t,16+60*t)
    M,R,C=over(M,R,C,insert,15+65*t,65+120*t,50+150*t)
    M,R,C=over(M,R,C,well,5+15*t,190+50*t,210+35*t)
    M,R,C=over(M,R,C,seam,65+120*t,120+95*t,135+100*t)
    M,R,C=over(M,R,C,key,155+85*t,50+85*t,45+125*t)
    return K.pack(col,M,R,C)

def truchet_facet_knurl(seed=42,attempt=2):
    # SPB-105 / CORE-WORKS a2. Owner: unique construction, not a rescale.
    # Native neighbor review rejected a1's quarter-turn carrier despite its
    # passing thumbnail fingerprint: FF Truchet Glass already uses that grammar.
    # Original triangular Truchet reference: Bridges 2011, Dunham, pp. 311–318.
    # M7 diagnostic delta/name/native/live evidence recorded with this attempt.
    x,y=K.xy();pitch=F(24);i=np.floor(x/pitch).astype(np.int32);j=np.floor(y/pitch).astype(np.int32)
    u=K.frac(x/pitch)*pitch;v=K.frac(y/pitch)*pitch;h=K.fhash(i,j,seed+13801);t=K.tiers(h)
    a=np.where(h>.5,u,pitch-u);b=v;diagonal=(a+b-pitch)/F(1.41421356)
    side=K.sstep(-.6,.6,diagonal);tb=K.tiers(K.fhash(i,j,seed+13802))
    fold=K.near(np.abs(diagonal),1.45);lip=K.near(np.abs(np.abs(diagonal)-1.7),.55)
    hem=K.near(np.minimum(np.minimum(u,pitch-u),np.minimum(v,pitch-v)),.6)
    groove=K.near(np.abs(K.frac((a-b)/F(9.2)+h*.23)-.5)*F(9.2),.65)*(1-side)*(1-fold)
    window=K.near(np.maximum(np.abs(a-12)-4.1,np.abs(b-18)-4.1),.55)*side*(1-fold)
    boss=K.near(np.hypot(a-5,b-5),4.2)*(1-side)
    boss_rim=K.near(np.abs(np.hypot(a-5,b-5)-3.7),.55)*(1-side)
    tab=K.near(np.maximum(np.abs(a-18)-4.5,np.abs(b-4)-3.9),.55)*(1-side)*(1-hem)
    key=K.near(np.abs(a-18),.6)*tab
    roof_a=np.clip((a+b)/pitch,0,1);roof_b=np.clip((a-b)/pitch+.5,0,1)
    green=K.ramp(t,['103430','3b7360','87b69c','e3ead0']);rose=K.ramp(tb,['442034','8a4b61','d58b78','f8ccae'])
    col=K.mix(green*(.52+.48*roof_a)[...,None],rose*(.55+.45*roof_b)[...,None],side)
    col=K.mix(col,np.array([.035,.035,.05],F),fold*.92);col=K.mix(col,np.array([.94,.81,.53],F),lip*.8)
    col=K.mix(col,green*.40,groove*.78);col=K.mix(col,np.array([.12,.16,.19],F),window*.92)
    col=K.mix(col,rose*.38,hem*.65);col=K.mix(col,green*(.60+.37*tb)[...,None],boss*.7)
    col=K.mix(col,np.array([.82,.94,.87],F),boss_rim*.86);col=K.mix(col,rose*.82,tab*.65);col=K.mix(col,np.array([.035,.025,.04],F),key*.8)
    M=(150+95*t)*(1-side)+(165+85*tb)*side
    R=(35+75*(1-roof_a)+40*t)*(1-side)+(45+70*(1-roof_b)+35*tb)*side
    C=(30+140*t)*(1-side)+(45+135*tb)*side
    M,R,C=over(M,R,C,fold,15+35*tb,180+55*tb,200+45*tb)
    M,R,C=over(M,R,C,lip,225+25*t,18+40*t,16+65*t)
    M,R,C=over(M,R,C,groove,105+100*t,145+85*t,145+90*t)
    M,R,C=over(M,R,C,window,5+20*tb,175+60*tb,215+30*tb)
    M,R,C=over(M,R,C,hem,50+80*t,120+105*t,135+105*t)
    M,R,C=over(M,R,C,boss,185+55*tb,35+75*tb,25+115*tb)
    M,R,C=over(M,R,C,boss_rim,215+35*t,20+40*t,18+60*t)
    M,R,C=over(M,R,C,tab,140+90*tb,55+95*tb,65+145*tb)
    M,R,C=over(M,R,C,key,5+30*t,180+55*t,200+45*t)
    return K.pack(col,M,R,C)

def wrap_craze_net(seed=42,attempt=1):
    x,y=K.xy();rng=np.random.default_rng(seed+11901);primary=np.zeros((2048,2048),np.uint8);secondary=primary.copy();tips=primary.copy();flakes=primary.copy()
    roots=rng.uniform(-30,2078,(2300 if attempt==1 else 7500,2));angles=rng.uniform(0,6.283,len(roots))
    if attempt>=3:
        count=len(roots);angles=angles[:,None]+np.cumsum(rng.normal(0,.27,(count,8)),axis=1)
        L=rng.uniform(8,24,(count,8));delta=np.stack((np.cos(angles),np.sin(angles)),2)*L[...,None]
        paths=np.concatenate((roots[:,None,:],roots[:,None,:]+np.cumsum(delta,axis=1)),1)
        branch_roots=paths[:,[0,3,6]];branch_angles=angles[:,[0,3,6]]+rng.choice([-1,1],(count,3))*rng.uniform(.6,1.2,(count,3))
        branch_ends=branch_roots+np.stack((np.cos(branch_angles),np.sin(branch_angles)),2)*rng.uniform(8,18,(count,3,1))
        trunks=np.rint(paths).astype(np.int32);branches=np.rint(np.stack((branch_roots,branch_ends),2)).astype(np.int32)
        ids=np.full((2048,2048),-1,np.int32)
        for tier in range(8):
            use=np.arange(count)%8==tier;val=int(100+155*tier/7)
            cv2.polylines(primary,list(trunks[use]),False,val,1,cv2.LINE_AA)
            cv2.polylines(secondary,list(branches[use].reshape(-1,2,2)),False,val,1,cv2.LINE_AA)
        for index,p in enumerate(trunks):
            cv2.polylines(ids,[p],False,index,2,cv2.LINE_8)
            val=int(100+155*(index%8)/7)
            for end in branches[index,:,1]:cv2.circle(tips,tuple(end),1,val,-1,cv2.LINE_AA)
            if index%4==0:
                q=p[0];cv2.fillConvexPoly(flakes,np.array([q,q+[3,-1],q+[1,3]],np.int32),val,cv2.LINE_AA)
    for index,(p,angle) in enumerate(zip(roots,angles)):
        if attempt>=3:break
        p=p.copy();val=int(100+155*(index%8)/7)
        for step in range(8):
            angle+=rng.normal(0,.27);L=rng.uniform(8,24);q=p+L*np.array([np.cos(angle),np.sin(angle)])
            cv2.line(primary,tuple(p.astype(np.int32)),tuple(q.astype(np.int32)),val,1,cv2.LINE_AA)
            if step%3==0:
                aa=angle+rng.choice([-1,1])*rng.uniform(.6,1.2);r=p+rng.uniform(8,18)*np.array([np.cos(aa),np.sin(aa)])
                cv2.line(secondary,tuple(p.astype(np.int32)),tuple(r.astype(np.int32)),val,1,cv2.LINE_AA);cv2.circle(tips,tuple(r.astype(np.int32)),1,val,-1,cv2.LINE_AA)
                if index%4==0:cv2.fillConvexPoly(flakes,np.array([p,p+[3,-1],p+[1,3]],np.int32),val,cv2.LINE_AA)
            p=q
    crack=primary.astype(F)/255;branch=secondary.astype(F)/255;tip=tips.astype(F)/255;flake=flakes.astype(F)/255
    full=np.maximum(crack,branch);lip=np.clip(np.roll(full,(1,1),(0,1))-full,0,1)
    if attempt>=3:
        grown=K.dilate_ids(ids,8);t=K.tiers(K.hash01(np.arange(len(roots)),seed+11902)[np.maximum(grown,0)])
    else:t=K.tiers(K.unit(K.noise(seed+11902,200)))
    region=K.unit(K.fbm(seed+11903,(3,10,24),.6));base=K.ramp(region,['1d3440','4d796f','9eaf8a','dfd3a6'])
    col=base*(.91+.09*t)[...,None];col=K.mix(col,np.array([.025,.025,.035],F),crack*.9)
    col=K.mix(col,base*.17,branch*.8);col=K.mix(col,np.array([.97,.76,.43],F),lip*.85)
    col=K.mix(col,np.array([.53,.67,.75],F),tip*.7);col=K.mix(col,base*.4,flake*.75)
    M=35+100*t;R=25+60*t;C=20+85*t
    M,R,C=over(M,R,C,crack,5+15*t,195+50*t,215+30*t)
    M,R,C=over(M,R,C,branch,15+35*t,170+65*t,190+50*t)
    M,R,C=over(M,R,C,lip,165+85*t,25+60*t,30+100*t)
    M,R,C=over(M,R,C,tip,25+55*t,110+115*t,120+115*t)
    M,R,C=over(M,R,C,flake,40+80*t,180+55*t,205+35*t)
    return K.pack(col,M,R,C)

def wrap_lens_array(seed=42,attempt=1):
    x,y=K.xy();u=x+2.5*K.noise(seed+12001,104);v=y+2.5*K.noise(seed+12002,113)
    j=np.floor(v/14).astype(np.int32);i=np.floor((u+(j%2)*12)/25).astype(np.int32);a=K.frac((u+(j%2)*12)/25)*25-12.5;b=K.frac(v/14)*14-7
    h=K.fhash(i,j,seed+12003);t=K.tiers(h);d=np.hypot(np.maximum(np.abs(a)-6,0),b)-5.0
    lens=1-K.sstep(-.5,.5,d);roof=np.sqrt(np.clip(1-(b/5)**2,0,1));split=K.near(np.abs(b-.5),.55)*lens
    root=K.near(np.abs(d-.8),.7);cap=K.near(np.abs(np.abs(a)-8),.8)*lens
    backing=K.near(np.hypot(a-10,b-4),1.0)*(h>.55)
    region=K.unit(K.fbm(seed+12004,(4,9,23),.6));blue=K.ramp(.6*region+.4*t,['123e5e','3f899f','9fcdd1','e8dfba']);rose=K.ramp(.6*(1-region)+.4*t,['48233f','9a5a77','d59ba6','edd3b8'])
    col=K.mix(blue,rose,K.sstep(-1,1,b));col*= (.35+.65*roof)[...,None]
    col=K.mix(col,np.array([.04,.035,.055],F),root*.9);col=K.mix(col,np.array([.98,.82,.49],F),cap*.75)
    col=K.mix(col,np.array([.08,.08,.13],F),split*.8);col=K.mix(col,np.array([.50,.78,.82],F),backing*.8)
    M=10+35*t;R=145+80*t;C=175+70*t
    M,R,C=over(M,R,C,lens,15+65*t,18+45*(1-roof)+15*t,16+55*t)
    M,R,C=over(M,R,C,split,30+80*t,95+120*t,85+145*t)
    M,R,C=over(M,R,C,root,5+15*t,180+55*t,200+45*t)
    M,R,C=over(M,R,C,cap,100+130*t,20+55*t,20+75*t)
    M,R,C=over(M,R,C,backing,180+65*t,45+90*t,80+145*t)
    return K.pack(col,M,R,C)

def wrap_flow_wrapline(seed=42,attempt=1):
    x,y=K.xy();u=x+4*np.sin(y/13)+2*K.noise(seed+12101,124);v=y+4*np.sin(x/17)+2*K.noise(seed+12102,115)
    i=np.floor(u/28).astype(np.int32);j=np.floor(v/28).astype(np.int32);a=K.frac(u/28)*28-14;b=K.frac(v/28)*28-14
    h=K.fhash(i,j,seed+12103);t=K.tiers(h);da=a-5*np.sin(b/7);db=b-5*np.sin(a/7+1.4)
    wa=1-K.sstep(3.1,4.2,np.abs(da));wb=1-K.sstep(3.1,4.2,np.abs(db));order=((i+j)%2==0).astype(F)
    upper=wa*(1-wb*(1-order));lower=wb*(1-wa*order);cross=wa*wb
    rail=K.near(np.abs(np.abs(da)-3.0),.65)*upper+K.near(np.abs(np.abs(db)-3.0),.65)*lower
    engraving=K.iso(v+u*.18,8,.65)[0]*upper+K.iso(u-v*.19,9,.65)[0]*lower
    split=K.near(np.abs(da),.65)*K.near(np.abs(b-10),1.7)*(h>.65)*upper
    region=K.unit(K.fbm(seed+12104,(4,10,24),.6));foil=K.ramp(.65*region+.35*t,['354654','778d97','c0c5b0','e8d3a2']);ink=K.ramp(.65*(1-region)+.35*t,['352443','7c577f','b68f9f','dec8b5'])
    col=np.broadcast_to(np.array([.035,.04,.06],F),(2048,2048,3)).copy()
    col=K.mix(col,ink*(.40+.55*np.clip(1-(db/4)**2,0,1))[...,None],lower)
    col=K.mix(col,foil*(.40+.55*np.clip(1-(da/4)**2,0,1))[...,None],upper)
    col=K.mix(col,np.array([.96,.77,.44],F),np.clip(rail,0,1)*.78);col=K.mix(col,col*.35,np.clip(engraving,0,1)*.4)
    col=K.mix(col,np.array([.015,.025,.035],F),split*.9)
    M=5+15*t;R=195+40*t;C=210+35*t
    M,R,C=over(M,R,C,lower,35+105*t,35+90*t,20+110*t)
    M,R,C=over(M,R,C,upper,175+75*t,30+75*t,30+145*t)
    M,R,C=over(M,R,C,cross*(1-upper),45+95*t,100+115*t,120+115*t)
    M,R,C=over(M,R,C,np.clip(rail,0,1),205+45*t,20+45*t,18+70*t)
    M,R,C=over(M,R,C,np.clip(engraving,0,1),65+125*t,140+85*t,155+85*t)
    M,R,C=over(M,R,C,split,5+15*t,225+25*t,235+20*t)
    return K.pack(col,M,R,C)

def wrap_spiral_burnish(seed=42,attempt=1):
    return _spiral_polish(seed,attempt)

def _spiral_polish(seed,attempt):
    x,y=K.xy();rng=np.random.default_rng(seed+12211);points=K.sites(seed+12212,17 if attempt==1 else 10,1.0)
    score=np.zeros((2048,2048),np.uint8);tails=score.copy();compound=score.copy();shear=score.copy()
    count=len(points);angle=np.linspace(0,7.8,22,dtype=F)
    rotation=rng.uniform(0,6.283,(count,1)).astype(F);hand=rng.choice(np.array([-1,1],F),(count,1))
    radii=rng.uniform(6,8.5,(count,1)).astype(F);q=np.linspace(0,1,22,dtype=F)[None,:]
    radius=F(1.5)+(radii-F(1.5))*q;theta=angle[None,:]*hand+rotation
    eccentric=rng.uniform(.72,1.05,(count,1)).astype(F)
    u=points[:,0,None]+radius*np.cos(theta);v=points[:,1,None]+radius*np.sin(theta)*eccentric
    spirals=np.rint(np.stack((u,v),2)).astype(np.int32);weights=np.arange(count)%8
    ends=spirals[:,-1];direction=np.stack((-np.sin(theta[:,-1]),np.cos(theta[:,-1])),1)*hand
    tailends=np.rint(ends+direction*rng.uniform(8,14,(count,1))).astype(np.int32)
    tailpaths=np.stack((ends,tailends),1)
    for i in range(0,count,3):cv2.circle(compound,tuple(np.rint(points[i]).astype(np.int32)),1,int(80+175*(i%8)/7),-1,cv2.LINE_AA)
    for i in range(0,count,4):cv2.line(shear,tuple(spirals[i,8]),tuple(spirals[i,8]+[5,-4]),190,1,cv2.LINE_AA)
    for tier in range(8):
        cv2.polylines(score,list(spirals[weights==tier]),False,85+24*tier,1,cv2.LINE_AA)
        cv2.polylines(tails,list(tailpaths[weights==tier]),False,85+24*tier,1,cv2.LINE_AA)
    s=score.astype(F)/255;tail=tails.astype(F)/255;c=compound.astype(F)/255;cross=shear.astype(F)/255
    lip=np.clip(np.roll(s,(1,-1),(0,1))-s,0,1);haze=cv2.GaussianBlur(np.maximum(s,tail),(0,0),.85)
    t=K.tiers(K.unit(K.noise(seed+12213,220)));region=K.unit(K.fbm(seed+12214,(3,10,24),.6))
    base=K.ramp(region,['122e47','416c8c','9bb4bd','e1d6b8']);col=base*(.87+.13*t)[...,None]
    col=K.mix(col,base*.3,s*.86);col=K.mix(col,np.array([.97,.82,.50],F),lip*.83)
    col=K.mix(col,np.array([.37,.69,.78],F),tail*.60);col=K.mix(col,np.array([.52,.41,.31],F),c*.75)
    col=K.mix(col,base*.18,cross*.85)
    M=10+55*t;R=20+50*t;C=16+65*t
    M,R,C=over(M,R,C,haze,15+45*t,85+105*t,85+140*t)
    M,R,C=over(M,R,C,s,35+90*t,135+100*t,155+85*t)
    M,R,C=over(M,R,C,lip,120+120*t,20+55*t,20+80*t)
    M,R,C=over(M,R,C,tail,30+75*t,100+105*t,80+150*t)
    M,R,C=over(M,R,C,c,5+15*t,205+30*t,220+25*t)
    M,R,C=over(M,R,C,cross,25+60*t,175+60*t,195+45*t)
    return K.pack(col,M,R,C)

def _elastic_hex_film(seed):
    # SPB-105 / CORE-WORKS a2: reject the metal-key prototype. Rounded
    # elastic roofs, adhesive seats and directional stress trace polymer film.
    x,y=K.xy();u=x+F(1.4)*K.noise(seed+11621,168);v=y+F(1.2)*K.noise(seed+11622,153)
    lab,r,pts=K.voronoi(K.sites(seed+11623,21,.12));a,b=K.cell_local(lab,pts,u,v)
    h=K.hash01(np.arange(len(pts)),seed+11624)[lab];t=K.tiers(h)
    q=np.maximum(np.abs(a),np.maximum(np.abs(F(.5)*a+F(.8660254)*b),np.abs(F(.5)*a-F(.8660254)*b)))
    roof=1-K.sstep(8.6,10.2,q);dome=np.clip(1-(q/F(10.4))**2,0,1)
    seat=K.near(np.abs(q-F(10.4)),F(.9));lip=K.near(np.abs(q-F(8.9)),F(.65))
    stress=K.near(np.abs(b-F(.25)*a-F(1.4)*np.sin(a/F(4))),F(.7))*roof*K.sstep(3.8,6.0,q)
    witness=K.near(np.abs(a+b*F(.35)-F(3)),F(.6))*roof*K.sstep(.5,.7,h)
    pigment=K.near(np.hypot(a+F(3),b-F(2)),F(1.15))*(h>F(.86))
    region=K.unit(K.fbm(seed+11625,(3,9,24),.6));base=K.ramp(.95*region+.05*t,['224153','608795','afc4be','e1d7b8'])
    col=base*(.88+.12*dome)[...,None];col=K.mix(col,base*.43,seat*.68)
    col=K.mix(col,np.array([.79,.90,.91],F),lip*.46)
    col=K.mix(col,base*.50,stress*.46);col=K.mix(col,base*.67,witness*.32)
    col=K.mix(col,np.array([.96,.79,.48],F),pigment*.67)
    M=5+25*t;R=60+85*t;C=65+130*t
    M,R,C=over(M,R,C,roof,8+30*t,20+35*(1-dome)+35*t,16+60*t)
    M,R,C=over(M,R,C,seat,5+15*t,180+55*t,205+45*t)
    M,R,C=over(M,R,C,lip,15+40*t,20+45*t,16+60*t)
    M,R,C=over(M,R,C,stress,10+30*t,95+105*t,105+130*t)
    M,R,C=over(M,R,C,witness,8+35*t,45+80*t,40+100*t)
    M,R,C=over(M,R,C,pigment,100+135*t,35+65*t,30+100*t)
    return K.pack(col,M,R,C)

def _rejected_spiral_pleat_concept(seed,attempt):
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+12201,28,1.0));u,v=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+12202)[lab];t=K.tiers(h);theta=np.arctan2(v+1.5,u-2)
    spokes=5+np.floor(h*4);phase=(theta-.15*d)*spokes/F(K.TAU);f=K.frac(phase)
    valley=K.near(np.minimum(f,1-f)*np.maximum(d,2)*F(K.TAU)/spokes,.65)
    crown=K.near(np.abs(f-.52)*np.maximum(d,2)*F(K.TAU)/spokes,.65)
    hub=K.near(np.hypot(u-2,v+1.5),1.7);rim=K.near(K.edge_distance(lab),.75)*(h>.35)
    reverse=K.sstep(.58,.80,f);roof=np.sin(f*F(np.pi))
    region=K.unit(K.fbm(seed+12203,(3,10,24),.6));foil=K.ramp(.65*region+.35*t,['3b2345','835481','c390a6','e9c8b5'])
    col=foil*(.30+.67*roof)[...,None];col=K.mix(col,np.array([.31,.59,.70],F),reverse*.3)
    col=K.mix(col,np.array([.025,.02,.035],F),valley*.75);col=K.mix(col,np.array([.96,.80,.46],F),crown*.78)
    col=K.mix(col,np.array([.66,.86,.88],F),hub*.75);col=K.mix(col,foil*.15,rim*.85)
    M=90+150*t;R=30+90*(1-roof);C=25+145*t
    M,R,C=over(M,R,C,reverse,70+125*t,70+105*t,90+130*t)
    M,R,C=over(M,R,C,valley,25+65*t,170+65*t,195+50*t)
    M,R,C=over(M,R,C,crown,210+40*t,20+45*t,18+70*t)
    M,R,C=over(M,R,C,hub,30+95*t,25+75*t,20+100*t)
    M,R,C=over(M,R,C,rim,10+30*t,195+45*t,215+30*t)
    return K.pack(col,M,R,C)

def wrap_overlap_ghost(seed=42,attempt=1):
    x,y=K.xy();a,b=K.rot(x+3*K.noise(seed+12301,111),y+3*K.noise(seed+12302,103),F(.44))
    c,e=K.rot(x+3*K.noise(seed+12303,101),y+3*K.noise(seed+12304,117),F(-.39))
    i=np.floor(a/25).astype(np.int32);j=np.floor(b/21).astype(np.int32);h=K.fhash(i,j,seed+12305);t=K.tiers(h)
    u=K.frac(a/25)*25-12.5;v=K.frac(b/21)*21-10.5;d=np.maximum(np.abs(u)+.35*np.abs(v)-8,np.abs(v)-7)
    aa=K.frac(c/23)*23-11.5;bb=K.frac(e/25)*25-12.5;d2=np.maximum(np.abs(bb)+.25*np.abs(aa)-9,np.abs(aa)-7)
    top=1-K.sstep(-.5,.5,d);lower=1-K.sstep(-.5,.5,d2);overlap=top*lower
    lip=K.near(np.abs(d),.7);buried=K.near(np.abs(d2),.7)*top
    ink=K.iso(c+e*.3,8,.65)[0]*overlap;pocket=K.sstep(.78,.93,K.unit(K.noise(seed+12306,240)))*buried
    region=K.unit(K.fbm(seed+12307,(4,9,24),.6));back=K.ramp(region,['273949','5a818c','a5b6b0','e0d3b5']);film=K.ramp(.6*region+.4*t,['362045','805379','c1909e','edc8b5'])
    col=K.mix(back,film,lower*.50);col=K.mix(col,film,top*.64);col=K.mix(col,back*.42,buried*.65)
    col=K.mix(col,np.array([.96,.82,.53],F),lip*.8);col=K.mix(col,film*.30,ink*.55);col=K.mix(col,np.array([.42,.30,.18],F),pocket*.8)
    M=25+80*t;R=65+100*t;C=55+140*t
    M,R,C=over(M,R,C,lower,30+95*t,40+90*t,25+110*t)
    M,R,C=over(M,R,C,top,20+65*t,25+65*t,16+85*t)
    M,R,C=over(M,R,C,overlap,30+85*t,35+70*t,16+65*t)
    M,R,C=over(M,R,C,lip,165+80*t,20+50*t,18+75*t)
    M,R,C=over(M,R,C,buried,65+105*t,90+110*t,70+145*t)
    M,R,C=over(M,R,C,ink,20+45*t,140+85*t,155+85*t)
    M,R,C=over(M,R,C,pocket,5+15*t,200+35*t,215+30*t)
    return K.pack(col,M,R,C)
