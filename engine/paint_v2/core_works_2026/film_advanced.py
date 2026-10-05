"""Pressure, thermal print and transparent-coat constructions.
SPB-105 / CORE-WORKS 2026-09-30. Quiet film remains materially meaningful.
"""
import cv2
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def wrap_squeegee(seed=42,attempt=2):
    x,y=K.xy();rng=np.random.default_rng(seed+10211);points=K.sites(seed+10212,13,1.0);count=len(points)
    angle=rng.normal(.55,.32,count).astype(F);length=rng.uniform(12,27,count).astype(F);width=rng.uniform(3.5,6.0,count).astype(F)
    along=np.stack((np.cos(angle),np.sin(angle)),1);across=np.stack((-along[:,1],along[:,0]),1)
    polys=np.rint(np.stack((points-along*length[:,None]/2-across*width[:,None],points+along*length[:,None]/2-across*width[:,None]*.7,points+along*length[:,None]/2+across*width[:,None]*.7,points-along*length[:,None]/2+across*width[:,None]),1)).astype(np.int32)
    ids=np.zeros((2048,2048),np.int32);toe=np.zeros((2048,2048),np.uint8);root=toe.copy();ribs=toe.copy();dust=toe.copy()
    for i,p in enumerate(polys):
        cv2.fillConvexPoly(ids,p,i+1,cv2.LINE_8)
        cv2.line(toe,tuple(p[1]),tuple(p[2]),255,1,cv2.LINE_AA)
        cv2.line(root,tuple(p[0]),tuple(p[3]),220,1,cv2.LINE_AA)
        cv2.line(ribs,tuple(np.rint((p[0]+p[3])/2).astype(int)),tuple(np.rint((p[1]+p[2])/2).astype(int)),190,1,cv2.LINE_AA)
        if i%5==0:cv2.circle(dust,tuple(p[3]),1,220,-1,cv2.LINE_AA)
    safe=np.maximum(ids-1,0);center=points[safe];a=x-center[...,0];b=y-center[...,1]
    axis=along[safe];depth=np.clip(.5+(a*axis[...,0]+b*axis[...,1])/length[safe],0,1)
    t=K.tiers(K.hash01(np.arange(count+1),seed+10213)[ids]);face=(ids>0).astype(F)
    tf=toe.astype(F)/255;rf=root.astype(F)/255;rib=ribs.astype(F)/255;d=dust.astype(F)/255
    region=K.unit(K.fbm(seed+10214,(3,9,24),.6));film=K.ramp(.65*region+.35*t,['123b4b','397a87','96b7ad','e1d2aa']);base=K.ramp(region,['312a45','756174','b5a3a7','dac5b0'])
    col=K.mix(base,film*(.45+.57*depth)[...,None],face);col=K.mix(col,np.array([.97,.80,.47],F),tf*.88)
    col=K.mix(col,film*.13,rf*.8);col=K.mix(col,film*.45,rib*.55);col=K.mix(col,np.array([.025,.025,.04],F),d*.9)
    shoulder=np.clip(np.roll(tf,(1,1),(0,1))-tf,0,1)
    col=K.mix(col,np.array([.59,.85,.87],F),shoulder*.72)
    M=15+45*t;R=145+80*t;C=170+70*t
    M,R,C=over(M,R,C,face,25+100*t,25+65*(1-depth)+25*t,16+85*t)
    M,R,C=over(M,R,C,tf,145+100*t,20+50*t,20+85*t)
    M,R,C=over(M,R,C,rf,5+20*t,185+55*t,210+35*t)
    M,R,C=over(M,R,C,rib,20+55*t,125+100*t,145+95*t)
    M,R,C=over(M,R,C,d,5,235,250)
    M,R,C=over(M,R,C,shoulder,35+85*t,20+45*t,16+65*t)
    return K.pack(col,M,R,C)

def wrap_heat_gun(seed=42,attempt=2):
    x,y=K.xy();heat=K.noise(seed+11011,156)+F(.25)*K.noise(seed+11012,237)
    hot=K.sstep(-.08,.19,heat);gx,gy=K.grad(heat);distance=(heat-.08)/np.maximum(np.hypot(gx,gy),.025)
    edge=K.near(np.abs(distance),.7);u=x+2.8*K.noise(seed+11013,203)*hot;v=y+3.5*K.noise(seed+11014,197)*hot
    a,b=K.rot(u,v,F(.41));c,e=K.rot(u,v,F(-.34))
    dot1=K.near(np.hypot(K.frac(a/8)*8-4,K.frac(b/8)*8-4),2.6)
    dot2=K.near(np.hypot(K.frac(c/9)*9-4.5,K.frac(e/9)*9-4.5),2.4)
    dot3=K.near(np.hypot(K.frac((u+v*.2)/8)*8-4,K.frac(v/8)*8-4),2.1)
    t=K.tiers(K.fhash(np.floor(u/17).astype(np.int32),np.floor(v/19).astype(np.int32),seed+11015))
    region=K.unit(K.fbm(seed+11016,(3,10,24),.6));base=K.ramp(region,['394058','7b8898','bac6bc','e7d5b3'])
    col=K.mix(base,np.array([.21,.58,.68],F),dot1*.72)
    col=K.mix(col,np.array([.63,.30,.50],F),dot2*.67);col=K.mix(col,np.array([.90,.71,.35],F),dot3*.54)
    softened=K.blur(col,1.15);col=K.mix(col,softened,hot*.85)
    streak=K.iso(v+u*.35+hot*3,8,.65)[0]*hot
    pool=np.clip(dot1*dot2+dot2*dot3,0,1)*hot
    col=K.mix(col,col*.55,streak*.5);col=K.mix(col,np.array([.88,.80,.59],F),edge*.45)
    col=K.mix(col,np.array([.36,.27,.40],F),pool*.22)
    M=15+45*t;R=130+95*t;C=145+95*t
    M,R,C=over(M,R,C,np.clip(dot1+dot2+dot3,0,1),20+65*t,100+95*t,105+120*t)
    M,R,C=over(M,R,C,hot,15+50*t,20+50*t,16+65*t)
    M,R,C=over(M,R,C,edge,50+100*t,40+75*t,35+115*t)
    M,R,C=over(M,R,C,streak,25+60*t,95+100*t,100+135*t)
    M,R,C=over(M,R,C,pool,35+100*t,35+70*t,25+95*t)
    return K.pack(col,M,R,C)

def wrap_ceramic_coat(seed=42,attempt=2):
    if attempt>=4:
        from .review_refinements import ceramic_levelled_glaze
        return ceramic_levelled_glaze(seed,attempt)
    x,y=K.xy();u=x+3*K.noise(seed+11511,140);v=y+3*K.noise(seed+11512,173)
    wipe=K.iso(u*.78+v*.32,8,.65)[0]
    filmfield=np.sin((u+1.8*np.sin(v/11))/F(4.1))+.36*K.noise(seed+11513,183)
    gx,gy=K.grad(filmfield);d=filmfield/np.maximum(np.hypot(gx,gy),.06)
    lift=K.near(np.abs(d),.65)*K.sstep(.12,.40,K.noise(seed+11514,205))
    meniscus=K.near(np.abs(d-1.1),.7)*K.sstep(.12,.40,K.noise(seed+11514,205))
    lab,r,pts=K.voronoi(K.sites(seed+11515,17,1.0));a,b=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11516)[lab];t=K.tiers(h)
    contact=K.sstep(.08,.3,K.noise(seed+11514,205));bead=(1-K.sstep(3,4.6,r))*contact*(h>.48)
    roof=np.sqrt(np.clip(1-(r/4.6)**2,0,1));beadlip=K.near(np.abs(r-4.0),.65)*contact*(h>.48)
    witness=K.sstep(.85,.98,h)*wipe*(1-lift)
    region=K.unit(K.fbm(seed+11517,(3,10,24),.6));base=K.ramp(.97*region+.03*t,['2b465a','6f98a6','bac8c0','e4d9bc'])
    col=base*(.98+.02*t)[...,None]
    col=K.mix(col,base*.78,wipe*.36);col=K.mix(col,base*.50,lift*.55)
    col=K.mix(col,np.array([.76,.86,.87],F),meniscus*.45)
    col=K.mix(col,base*(.50+.65*roof)[...,None],bead*.65)
    col=K.mix(col,np.array([.95,.86,.62],F),beadlip*.62);col=K.mix(col,np.array([.96,.76,.46],F),witness*.65)
    M=5+30*t;R=20+45*t;C=16+55*t
    M,R,C=over(M,R,C,wipe,10+35*t,45+65*t,35+95*t)
    M,R,C=over(M,R,C,lift,10+30*t,135+100*t,165+80*t)
    M,R,C=over(M,R,C,meniscus,15+45*t,25+60*t,20+80*t)
    M,R,C=over(M,R,C,bead,8+30*t,18+45*(1-roof)+15*t,16+45*t)
    M,R,C=over(M,R,C,beadlip,20+55*t,25+60*t,25+90*t)
    M,R,C=over(M,R,C,witness,100+135*t,35+70*t,35+120*t)
    return K.pack(col,M,R,C)

def wrap_flow_wrapline(seed=42,attempt=2):
    if attempt>=4:
        from .review_refinements import flow_streamlets
        return flow_streamlets(seed,attempt)
    if attempt>=3:return _flow_lamella(seed)
    x,y=K.xy();u=x+5*np.sin(y/13)+1.5*K.noise(seed+12111,145);v=y+5*np.sin(x/17)+1.5*K.noise(seed+12112,151)
    f=np.sin(u/F(3.4));g=np.sin(v/F(3.6));fg=np.maximum(np.hypot(*K.grad(f)),.05);gg=np.maximum(np.hypot(*K.grad(g)),.05)
    da=f/fg;db=g/gg;wa=K.near(np.abs(da),3);wb=K.near(np.abs(db),3)
    i=np.floor(u/F(3.4*np.pi)).astype(np.int32);j=np.floor(v/F(3.6*np.pi)).astype(np.int32)
    t=K.tiers(K.fhash(i,j,seed+12113));order=((i+j)%2==0).astype(F)
    upper=wa*(1-wb*(1-order));lower=wb*(1-wa*order);cross=wa*wb
    rail=K.near(np.abs(np.abs(da)-2.5),.6)*upper+K.near(np.abs(np.abs(db)-2.5),.6)*lower
    engraving=K.iso(v+u*.15,8,.65)[0]*upper+K.iso(u-v*.18,9,.65)[0]*lower
    split=K.near(np.abs(da),.55)*K.sstep(.80,.93,K.unit(K.noise(seed+12114,230)))*upper
    region=K.unit(K.fbm(seed+12115,(3,10,24),.6));metal=K.ramp(.65*region+.35*t,['244650','5f8c88','b4c7a3','e9d5a2']);ink=K.ramp(.7*(1-region)+.3*t,['342345','77537a','b28ba4','e0c8b5'])
    col=np.broadcast_to(np.array([.035,.035,.055],F),(2048,2048,3)).copy()
    col=K.mix(col,ink*(.35+.62*np.clip(1-(db/3.7)**2,0,1))[...,None],lower)
    col=K.mix(col,metal*(.35+.62*np.clip(1-(da/3.7)**2,0,1))[...,None],upper)
    col=K.mix(col,np.array([.98,.82,.49],F),np.clip(rail,0,1)*.72);col=K.mix(col,col*.33,np.clip(engraving,0,1)*.45)
    col=K.mix(col,np.array([.02,.025,.04],F),split*.9)
    M=5+15*t;R=190+45*t;C=210+35*t
    M,R,C=over(M,R,C,lower,30+105*t,30+90*t,20+115*t)
    M,R,C=over(M,R,C,upper,170+80*t,30+80*t,35+145*t)
    M,R,C=over(M,R,C,cross*(1-upper),35+90*t,110+100*t,120+115*t)
    M,R,C=over(M,R,C,np.clip(rail,0,1),200+45*t,20+45*t,18+75*t)
    M,R,C=over(M,R,C,np.clip(engraving,0,1),55+130*t,145+80*t,155+85*t)
    M,R,C=over(M,R,C,split,5+15*t,215+30*t,230+25*t)
    return K.pack(col,M,R,C)

def _flow_lamella(seed):
    # SPB-105 / CORE-WORKS a3: owner fine/unique doctrine. Reject a2's
    # over-under weave; trace one continuously curving lamella family instead.
    x,y=K.xy();u=x+F(.44)*y+F(7)*np.sin(y/F(18))+F(2.8)*K.noise(seed+12131,154)
    v=y+F(2)*np.sin(x/F(23));phase=u/F(3.8)
    wave=np.sin(phase);gx,gy=K.grad(wave);d=wave/np.maximum(np.hypot(gx,gy),F(.055))
    lamella=K.near(np.abs(d),F(3.1));roof=np.clip(1-(d/F(3.7))**2,0,1)
    i=np.floor(phase/F(np.pi)).astype(np.int32);j=np.floor(v/F(19)).astype(np.int32)
    t=K.tiers(K.fhash(i,j,seed+12132));etch=K.iso(u+F(.16)*np.sin(v/F(3)),8,.65)[0]*lamella
    rupture=K.sstep(.28,.48,K.noise(seed+12133,211))*K.near(np.abs(d),F(1.15))
    lamella*=1-rupture
    shoulder=K.near(np.abs(np.abs(d)-F(2.6)),F(.65))*lamella
    root=K.near(np.abs(np.abs(d)-F(3.6)),F(.7))
    wake=K.iso(v+F(.35)*u,9,.65)[0]*(1-lamella)*K.sstep(.60,.82,t)
    region=K.unit(K.fbm(seed+12134,(3,10,24),.6));metal=K.ramp(.65*region+.35*t,['194151','4b8791','a6c7bd','eee0af'])
    base=K.ramp(region,['261e3c','654d75','ad8c9f','d9bdac'])
    col=K.mix(base,metal*(.32+.68*roof)[...,None],lamella)
    col=K.mix(col,np.array([.98,.82,.47],F),shoulder*.82)
    col=K.mix(col,base*.16,root*.72);col=K.mix(col,metal*.30,etch*.52)
    col=K.mix(col,np.array([.61,.84,.81],F),wake*.6);col=K.mix(col,np.array([.035,.025,.045],F),rupture*.85)
    M=15+45*t;R=130+100*t;C=160+80*t
    M,R,C=over(M,R,C,lamella,165+85*t,30+75*(1-roof)+40*t,25+145*t)
    M,R,C=over(M,R,C,shoulder,210+40*t,18+45*t,16+75*t)
    M,R,C=over(M,R,C,root,5+15*t,195+45*t,220+30*t)
    M,R,C=over(M,R,C,etch,70+130*t,135+90*t,150+95*t)
    M,R,C=over(M,R,C,wake,55+130*t,70+115*t,65+135*t)
    M,R,C=over(M,R,C,rupture,5+15*t,210+35*t,230+25*t)
    return K.pack(col,M,R,C)
