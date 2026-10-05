"""Prototype camouflage and optical films: distinct perceptual constructions.
SPB-105 / CORE-WORKS 2026-09-30; no military-camo or existing ASTRA copies.
"""
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def mul_moire_defeat(seed=42, attempt=1):
    """Crossing chirped diffraction rulings divided into contradictory lens domains."""
    x,y=K.xy()
    wx,wy=K.warp(seed+501,26,7)
    lab,_,pts=K.voronoi(K.sites(seed+502,116,1.0))
    u,v=K.cell_local(lab,pts,wx,wy)
    angle=(K.hash01(np.arange(len(pts)),seed+503)*2.5+.1)[lab]
    a,b=K.rot(u,v,angle)
    warp=.15*K.noise(seed+504,68)
    first=(a+.0012*b*b)/F(9.)+warp
    second=(a*.94+b*.19+.0015*a*b)/F(10.5)-warp*.7
    if attempt>=2:
        first += .0023*a*a/F(9.)
        second += .004*b*b/F(10.5)
    p=K.frac(first); q=K.frac(second)
    ink1=K.sstep(.38,.49,p)*(1-K.sstep(.76,.87,p))
    ink2=K.sstep(.25,.36,q)*(1-K.sstep(.65,.76,q))
    beat=.5+.5*np.cos((first-second)*F(K.TAU))
    fine=K.hash01(np.arange(len(pts)),seed+505)[lab]
    silver=K.ramp(.75*beat+.25*fine,['243c54','496e84','a3c5ce','f0f4df'])
    if attempt>=2:
        silver=K.ramp(.75*beat+.25*fine,['120d32','354b94','7bbac7','e4f1d8'])
    col=silver*(1-.82*ink1)[...,None]
    col=K.mix(col,np.array([.14,.055,.17],F),ink2*.68)
    overlap=ink1*ink2
    col=K.mix(col,np.array([.98,.53,.21],F),overlap*.48)
    seam=K.near(K.edge_distance(lab),1.3)
    hatch=K.iso(a+b,13,1.3)[0]*seam
    col=K.mix(col,np.array([.95,.95,.89],F),seam*.9)
    col=K.mix(col,np.array([.8,.25,.12],F),hatch)
    M=185+60*fine; R=22+90*(1-beat)+25*fine; C=25+155*fine
    M,R,C=over(M,R,C,ink1,15+32*fine,135+80*fine,170+70*fine)
    M,R,C=over(M,R,C,ink2,110+70*fine,45+100*fine,45+160*(1-fine))
    M,R,C=over(M,R,C,overlap,235,18+70*fine,20+90*fine)
    M,R,C=over(M,R,C,seam,245,22+50*fine,25)
    return K.pack(col,M,R,C)

def mul_erlkonig_swirl(seed=42,attempt=1):
    """Counterwound positive/negative print phases splice into a full camo skin."""
    x,y=K.xy();u,v=K.warp(seed+5101,13,35)
    # Interference between two nonlinear curls creates ink pockets and bridges.
    # It is a continuous print field, not a recoloured conductor-coil carrier.
    a=u+7*np.sin(v/14)+5*np.cos(u/19+v/11)
    b=v+8*np.cos(u/15)-5*np.sin(v/17-u/12)
    p=np.sin(a/4.1)+F(.68)*np.cos(b/5.0+a/18)
    q=np.cos(b/4.4)-F(.61)*np.sin(a/5.3-b/17)
    phase=p*q
    positive=K.sstep(-.12,.12,phase)
    gx,gy=K.grad(phase);d=phase/np.maximum(np.hypot(gx,gy),.03)
    key=K.near(np.abs(d),.65)
    bridge=K.sstep(.65,1.03,p)*K.sstep(.55,.9,q)
    cut=K.iso(a+b*.24,8,.7)[0]*positive
    h=K.fhash(np.floor(u/19),np.floor(v/19),seed+5102);t=K.tiers(h)
    seam=K.iso(u+v*.39,29,.85)[0]
    tick=seam*K.iso(v-u*.22,12,1.1)[0]
    ivory=K.ramp(t,['8b9296','c6c7bd','eee6cd'])
    ink=K.ramp(t,['07121f','202b3c','435263'])
    col=K.mix(ivory,ink,positive)
    col=K.mix(col,np.array([.83,.59,.36],F),key*.52)
    col=K.mix(col,np.array([.97,.93,.78],F),bridge*.6)
    col=K.mix(col,col*.35,cut*.45)
    col=K.mix(col,np.array([.48,.66,.68],F),seam*.8)
    col=K.mix(col,np.array([.98,.48,.20],F),tick)
    M=70+130*t;R=45+90*t;C=25+150*t
    M,R,C=over(M,R,C,positive,8+25*t,155+75*t,170+65*t)
    M,R,C=over(M,R,C,key,145+100*t,30+90*t,45+150*t)
    M,R,C=over(M,R,C,bridge,95+135*t,25+65*t,25+100*t)
    M,R,C=over(M,R,C,cut,12,205+30*t,210+35*t)
    M,R,C=over(M,R,C,seam,180+65*t,30+70*t,30+125*t)
    M,R,C=over(M,R,C,tick,200+50*t,18+50*t,20+75*t)
    return K.pack(col,M,R,C)

def mul_confusion_blob(seed=42,attempt=1):
    """Two independent amorphous print masks with rooted inner keylines."""
    x,y=K.xy();field=K.noise(seed+5201,128)+F(.28)*K.noise(seed+5202,215)
    second=K.noise(seed+5203,175)
    island=K.sstep(-.055,.055,field)
    pocket=K.sstep(.05,.18,second)*island
    gx,gy=K.grad(field);d=field/np.maximum(np.hypot(gx,gy),.02)
    key=K.near(np.abs(d-2.2),.65)
    void=K.sstep(.17,.35,second)*(1-island)
    grain=K.unit(K.noise(seed+5204,245));t=K.tiers(grain)
    chalk=K.ramp(.55*K.unit(field)+.45*t,['707e89','b6bbb6','e8ddc0'])
    graphite=K.ramp(t,['121c36','263955','516978'])
    col=K.mix(graphite,chalk,island)
    col=K.mix(col,np.array([.41,.69,.68],F),pocket*.8)
    col=K.mix(col,np.array([.87,.49,.28],F),key*.80)
    col=K.mix(col,np.array([.07,.045,.11],F),void*.8)
    col *= (.86+.16*grain)[...,None]
    M=25+75*t;R=75+70*t;C=40+150*t
    M,R,C=over(M,R,C,island,15+65*t,130+90*t,150+85*t)
    M,R,C=over(M,R,C,pocket,80+120*t,35+80*t,25+125*t)
    M,R,C=over(M,R,C,key,160+85*t,30+85*t,30+140*t)
    M,R,C=over(M,R,C,void,4+15*t,205+40*t,220+25*t)
    return K.pack(col,M,R,C)

def mul_shutline_fake(seed=42,attempt=1):
    """A panel-gap jigsaw is interrupted by contradictory oblique printed seams."""
    x,y=K.xy();u,v=K.warp(seed+5301,6,42)
    j=np.floor(v/25).astype(np.int32)
    shift=K.fhash(j,None,seed+5302)*24
    i=np.floor((u+shift)/29).astype(np.int32)
    a=K.frac((u+shift)/29)*29;b=K.frac(v/25)*25
    h=K.fhash(i,j,seed+5303);t=K.tiers(h)
    gap=K.near(np.minimum(a,29-a),.95)+K.near(np.minimum(b,25-b),.95)
    contrary=K.iso(u-v*.61,21,1.0)[0]*(h>.31)
    shadow=K.near(np.minimum(a,29-a),3)*(1-K.near(np.minimum(a,29-a),1.1))
    bevel=K.near(np.abs(a-2.5),.65)+K.near(np.abs(b-2.5),.65)
    hinge=K.near(np.abs(a-4.5),1.1)*K.near(np.abs(b-8),2.0)
    stamp=K.iso(a+h*7,8,.7)[0]*K.near(np.abs(b-16),1.1)*(h>.48)
    region=K.unit(K.fbm(seed+5304,(4,10,23),.61))
    panel=K.ramp(.55*region+.45*t,['24445a','577f97','b5c9c9','e5e8ce'])
    roof=np.sin(np.clip(a/29,0,1)*F(np.pi))
    col=panel*(.64+.38*roof)[...,None]
    col=K.mix(col,panel*.24,shadow*.8)
    col=K.mix(col,np.array([.055,.05,.085],F),np.clip(gap+contrary,0,1)*.95)
    col=K.mix(col,np.array([.89,.96,.93],F),np.clip(bevel,0,1)*.80)
    col=K.mix(col,np.array([.91,.50,.27],F),hinge)
    col=K.mix(col,np.array([.27,.28,.38],F),stamp)
    M=55+125*t;R=32+75*(1-roof)+25*t;C=25+145*t
    M,R,C=over(M,R,C,shadow,25+45*t,130+95*t,150+90*t)
    M,R,C=over(M,R,C,np.clip(gap+contrary,0,1),5+20*t,200+45*t,210+35*t)
    M,R,C=over(M,R,C,np.clip(bevel,0,1),170+80*t,20+55*t,18+85*t)
    M,R,C=over(M,R,C,hinge,180+70*t,30+80*t,25+125*t)
    M,R,C=over(M,R,C,stamp,10+35*t,180+65*t,195+50*t)
    return K.pack(col,M,R,C)

def mul_foam_clad(seed=42,attempt=1):
    """Strapped closed-cell cushions; nonmetal foam is intentionally matte."""
    x,y=K.xy();u,v=K.warp(seed+5401,5,65)
    i=np.floor(u/24).astype(np.int32);j=np.floor(v/23).astype(np.int32)
    a=K.frac(u/24)*24-12;b=K.frac(v/23)*23-11.5
    h=K.fhash(i,j,seed+5402);t=K.tiers(h)
    q=((np.abs(a)/11)**4+(np.abs(b)/10.5)**4)**F(.25)
    roof=np.clip(1-q,0,1)
    rim=K.near(np.abs(q-.9)*11,1.2)
    pores=K.sstep(.72,.91,K.unit(K.noise(seed+5403,245)))*(1-rim)
    strap=K.iso(u+v*.35,29,2.3)[0]
    root=K.iso(u+v*.35+2.7,29,1.0)[0]
    fastener=strap*(1-K.sstep(1.3,2.5,np.hypot(a-4,b+3)))*(h>.36)
    foam=K.ramp(t,['5d6469','929ba0','c9ccc4','e8e6d6'])
    col=foam*(.69+.34*roof)[...,None]
    col=K.mix(col,foam*.32,rim*.50)
    col=K.mix(col,foam*.20,pores*.58)
    col=K.mix(col,np.array([.045,.063,.075],F),root*.80)
    col=K.mix(col,np.array([.14,.21,.25],F),strap*.92)
    col=K.mix(col,np.array([.75,.82,.82],F),fastener)
    M=2+9*t;R=145+80*t;C=175+70*t
    M,R,C=over(M,R,C,rim,3+12*t,110+95*t,130+105*t)
    M,R,C=over(M,R,C,pores,0,210+40*t,225+25*t)
    M,R,C=over(M,R,C,strap,3+15*t,105+95*t,100+135*t)
    M,R,C=over(M,R,C,root,2,235,250)
    M,R,C=over(M,R,C,fastener,160+85*t,30+70*t,35+115*t)
    return K.pack(col,M,R,C)

def mul_bubble_clad(seed=42,attempt=1):
    """A sealed quilt beneath a separately ruled protective cover film."""
    x,y=K.xy();u,v=K.warp(seed+5501,4,60)
    j=np.floor(v/20).astype(np.int32);u+=(j%2)*F(11)
    i=np.floor(u/23).astype(np.int32);a=K.frac(u/23)*23-11.5;b=K.frac(v/20)*20-10
    h=K.fhash(i,j,seed+5502);t=K.tiers(h)
    q=np.hypot(a/11,b/10);roof=np.sqrt(np.clip(1-q*q,0,1))
    root=K.sstep(.93,1.1,q)
    weld=K.near(np.abs(q-.85)*10,.75)+K.near(np.abs(q-1.05)*10,.65)
    contact=K.near(np.abs(np.hypot(a-2,b+3)-5),.85)*(1-root)
    cover=K.iso(u*.38+v+3*K.noise(seed+5503,90),8,.65)[0]
    tape=K.iso(u-v*.22,31,1.5)[0]*K.near(np.abs(b-5),2)
    region=K.unit(K.fbm(seed+5504,(4,11,29),.59))
    plastic=K.ramp(.6*region+.4*t,['485469','8297ac','c4d4d7','eae9d2'])
    col=plastic*(.48+.59*roof+.13*a/12)[...,None]
    col=K.mix(col,plastic*.25,root*.78)
    col=K.mix(col,np.array([.75,.88,.90],F),np.clip(weld,0,1)*.48)
    col=K.mix(col,np.array([.91,.90,.73],F),contact*.45)
    col=K.mix(col,col*.56,cover*.28)
    col=K.mix(col,np.array([.20,.23,.27],F),tape*.8)
    M=4+45*t;R=20+65*(1-roof)+25*t;C=16+90*t
    M,R,C=over(M,R,C,root,4+15*t,140+95*t,165+75*t)
    M,R,C=over(M,R,C,np.clip(weld,0,1),10+35*t,85+90*t,100+115*t)
    M,R,C=over(M,R,C,contact,10+50*t,50+85*t,45+100*t)
    M,R,C=over(M,R,C,cover,10+50*t,100+85*t,100+120*t)
    M,R,C=over(M,R,C,tape,8+30*t,160+70*t,160+80*t)
    return K.pack(col,M,R,C)

def mul_countershade(seed=42,attempt=1):
    """Inverse print shading deliberately cancels the apparent barrel shoulder."""
    x,y=K.xy();u,v=K.warp(seed+5601,10,31);u,v=K.rot(u,v,F(-.28))
    j=np.floor(v/24).astype(np.int32);i=np.floor((u+j*7)/27).astype(np.int32)
    a=K.frac((u+j*7)/27)*27;b=K.frac(v/24)*24
    h=K.fhash(i,j,seed+5602);t=K.tiers(h)
    curved=b+2.4*np.sin(a*.16+h*4)
    crown=np.exp(-((curved-11)/F(4))**2)
    underside=K.near(np.abs(curved-19.5),1.25)
    shoulder=K.near(np.abs(curved-3),1.1)
    cut=K.iso(a+h*6,8,.7)[0]*(1-shoulder)
    register=K.near(np.hypot(a-21,b-6),1.4)*(h>.46)
    region=K.unit(K.fbm(seed+5603,(3,9,24),.60))
    plane=K.ramp(.65*region+.35*t,['69465c','ae8190','d9b9b1','eadbba'])
    col=plane*(1-.66*crown)[...,None]
    col=K.mix(col,np.array([.95,.93,.82],F),underside*.9)
    col=K.mix(col,np.array([.22,.39,.44],F),shoulder*.9)
    col=K.mix(col,col*.43,cut*.43)
    col=K.mix(col,np.array([.91,.59,.34],F),register)
    M=50+125*t;R=40+60*t;C=25+135*t
    M,R,C=over(M,R,C,crown,10+35*t,165+70*t,170+70*t)
    M,R,C=over(M,R,C,underside,100+140*t,20+60*t,20+95*t)
    M,R,C=over(M,R,C,shoulder,115+125*t,45+75*t,40+140*t)
    M,R,C=over(M,R,C,cut,15+45*t,145+95*t,140+105*t)
    M,R,C=over(M,R,C,register,205+45*t,18+45*t,20+70*t)
    return K.pack(col,M,R,C)

def mul_false_shadow(seed=42,attempt=1):
    """Two incompatible networks of cast wedges and false folds share a plane."""
    x,y=K.xy();u,v=K.warp(seed+5701,10,35)
    p=u+v*.58+5*np.sin(v*.15);q=v-u*.41+4*np.cos(u*.17)
    fp=K.frac(p/25);fq=K.frac(q/28)
    ribbon=K.sstep(.22,.32,fp)*(1-K.sstep(.55,.65,fp))
    wedge=K.sstep(.45,.78,fq)*K.sstep(.58,.84,fp)
    lip=K.near(np.abs(fp-.25)*25,.75)
    fold=K.near(np.minimum(fq,1-fq)*28,1.25)
    hatch=K.iso(p+q*.27,8,.7)[0]*ribbon
    vertex=K.near(np.hypot((fp-.25)*25,(fq-.50)*28),1.6)
    h=K.fhash(np.floor(p/25),np.floor(q/28),seed+5702);t=K.tiers(h)
    region=K.unit(K.fbm(seed+5703,(4,12,23),.62))
    blue=K.ramp(.60*region+.4*t,['263050','596cab','a6bad7','e0dfc8'])
    col=blue*(.75+.24*np.sin(fq*F(np.pi)))[...,None]
    col=K.mix(col,np.array([.08,.063,.15],F),ribbon*.92)
    col=K.mix(col,np.array([.29,.15,.30],F),wedge*.88)
    col=K.mix(col,np.array([.92,.91,.82],F),lip*.85)
    col=K.mix(col,np.array([.86,.53,.28],F),fold*.85)
    col=K.mix(col,np.array([.36,.47,.69],F),hatch*.75)
    col=K.mix(col,np.array([1,.92,.65],F),vertex)
    M=60+135*t;R=35+70*t;C=25+140*t
    M,R,C=over(M,R,C,ribbon,8+25*t,155+80*t,160+80*t)
    M,R,C=over(M,R,C,wedge,20+40*t,115+115*t,120+110*t)
    M,R,C=over(M,R,C,lip,125+120*t,25+65*t,25+95*t)
    M,R,C=over(M,R,C,fold,150+95*t,40+80*t,35+135*t)
    M,R,C=over(M,R,C,hatch,30+80*t,100+95*t,95+135*t)
    M,R,C=over(M,R,C,vertex,240,16,16)
    return K.pack(col,M,R,C)

def mul_qr_scramble(seed=42,attempt=1):
    """Decorative scrambled finder/timing grammar built from fine 8px modules."""
    import cv2
    r=K.rng(seed+5801);n=256
    data=(r.random((n,n))>.50).astype(F)
    finder=np.zeros((n,n),F);timing=np.zeros_like(finder);erase=np.zeros_like(finder)
    for j in range(0,n,16):
        for i in range(0,n,16):
            oi=i+int(r.integers(0,3));oj=j+int(r.integers(0,3))
            for gy in range(7):
                for gx in range(7):
                    yy=oj+gy;xx=oi+gx
                    if yy>=n or xx>=n:continue
                    black=gx in (0,6) or gy in (0,6) or (2<=gx<=4 and 2<=gy<=4)
                    data[yy,xx]=black;finder[yy,xx]=black
            length=min(11,n-oi)
            if oj+10<n:
                timing[oj+10,oi:oi+length]=np.arange(length)%2
                data[oj+10,oi:oi+length]=timing[oj+10,oi:oi+length]
            if oj+13<n and oi+9<n:
                erase[oj+12:oj+14,oi+8:oi+10]=1
    def native(a):return cv2.resize(a,(K.N,K.N),interpolation=cv2.INTER_NEAREST)
    ink=native(data);find=native(finder);rail=native(timing);window=native(erase)
    x,y=K.xy();i=np.floor(x/8).astype(np.int32);j=np.floor(y/8).astype(np.int32)
    h=K.fhash(i,j,seed+5802);t=K.tiers(h)
    edge=K.near(np.minimum(K.frac(x/8)*8,8-K.frac(x/8)*8),.55)*ink
    register=K.near(np.hypot(K.frac(x/8)*8-2,K.frac(y/8)*8-2),.8)*rail
    region=K.unit(K.fbm(seed+5803,(4,11,25),.60))
    foil=K.ramp(.7*region+.3*t,['1b4760','4d8a96','a6c9bf','ebdfb2'])
    black=K.ramp(t,['061426','152c45','354b5b'])
    col=K.mix(foil,black,ink)
    col=K.mix(col,K.ramp(t,['69446b','b67f8d','edc4aa']),find*.72)
    col=K.mix(col,np.array([.86,.73,.40],F),rail*.82)
    col=K.mix(col,np.array([.13,.14,.24],F),window)
    col=K.mix(col,foil*.35,edge*.65)
    col=K.mix(col,np.array([.94,.94,.81],F),register)
    M=145+100*t;R=30+85*t;C=25+145*t
    M,R,C=over(M,R,C,ink,8+25*t,155+80*t,165+70*t)
    M,R,C=over(M,R,C,find,115+125*t,35+85*t,30+145*t)
    M,R,C=over(M,R,C,rail,85+140*t,45+95*t,45+145*t)
    M,R,C=over(M,R,C,window,5+15*t,195+50*t,220+30*t)
    M,R,C=over(M,R,C,edge,8,225,245)
    M,R,C=over(M,R,C,register,215+35*t,18+40*t,20+65*t)
    return K.pack(col,M,R,C)

def mul_wireframe(seed=42,attempt=1):
    """Foreshortened truss rails and hidden cross-braces on false facets."""
    x,y=K.xy();u,v=K.warp(seed+5901,11,30)
    p=u+v*.48+4*np.sin(v/17);q=v-u*.32+3*np.cos(u/21)
    first,ip,fp=K.iso(p,26,1.1)
    second,iq,fq=K.iso(q,23,1.0)
    brace=K.iso(p+q,31,.8)[0]
    h=K.fhash(ip,iq,seed+5902);t=K.tiers(h)
    facet=K.sstep(.24,.52,fp+fq*.45)
    hidden=brace*K.sstep(.42,.60,K.frac((p-q)/10))*(1-facet)
    vertex=first*second
    rail=np.clip(first+second,0,1)
    roof=np.sin(fp*F(np.pi))*np.sin(fq*F(np.pi))
    region=K.unit(K.fbm(seed+5903,(3,10,27),.60))
    glass=K.ramp(.65*region+.35*t,['123a3f','2e7979','69b3a0','bde5bb'])
    col=glass*(.43+.58*roof)[...,None]
    col=K.mix(col,glass*.20,facet*.65)
    col=K.mix(col,np.array([.53,.72,.82],F),brace*facet*.85)
    col=K.mix(col,np.array([.86,.96,.91],F),rail*.9)
    col=K.mix(col,np.array([.34,.46,.57],F),hidden*.85)
    col=K.mix(col,np.array([.97,.58,.28],F),vertex)
    M=20+80*t;R=35+70*(1-roof)+40*facet;C=25+145*t
    M,R,C=over(M,R,C,facet,10+30*t,155+75*t,165+65*t)
    M,R,C=over(M,R,C,brace*facet,110+130*t,35+90*t,35+130*t)
    M,R,C=over(M,R,C,rail,180+65*t,18+55*t,18+85*t)
    M,R,C=over(M,R,C,hidden,20+60*t,130+100*t,140+95*t)
    M,R,C=over(M,R,C,vertex,195+55*t,25+65*t,25+105*t)
    return K.pack(col,M,R,C)

def mul_matte_cover(seed=42,attempt=1):
    """Dry crinkled polymer cloth; no invented metallic rainbow on matte yarn."""
    x,y=K.xy();u,v=K.warp(seed+6001,8,45)
    i=np.floor(u/14).astype(np.int32);j=np.floor(v/12).astype(np.int32)
    a=K.frac(u/14)*14;b=K.frac(v/12)*12
    h=K.fhash(i,j,seed+6002);t=K.tiers(h)
    warp=K.near(np.minimum(a,14-a),2.1)
    weft=K.near(np.minimum(b,12-b),1.9)
    order=((i+j)%2).astype(F)
    fibre=np.clip(warp*(1-weft*order)+weft*(1-warp*(1-order)),0,1)
    lip=K.iso(u+v*.24,31,1.2)[0]
    tension=K.iso(v+5*np.sin(u*.09),27,.85)[0]*(h>.32)
    abrasion=K.iso(u+v*.18+h*4,8,.65)[0]*fibre
    pore=(1-fibre)*K.sstep(.65,.85,h)
    roof=np.sin(a/F(14)*F(np.pi))*.55+np.sin(b/F(12)*F(np.pi))*.45
    cloth=K.ramp(t,['111a27','283342','46505d','65707a'])
    col=cloth*(.60+.38*roof)[...,None]
    col=K.mix(col,cloth*.42,pore*.83)
    col=K.mix(col,cloth*1.30,abrasion*.35)
    col=K.mix(col,np.array([.10,.15,.19],F),tension*.70)
    col=K.mix(col,np.array([.30,.35,.38],F),lip*.58)
    M=1+10*t;R=160+70*t+15*(1-roof);C=190+55*t
    M,R,C=over(M,R,C,fibre,2+15*t,135+95*t,165+75*t)
    M,R,C=over(M,R,C,abrasion,1+12*t,190+45*t,205+35*t)
    M,R,C=over(M,R,C,tension,2,220+25*t,230+20*t)
    M,R,C=over(M,R,C,lip,5+18*t,100+100*t,115+120*t)
    M,R,C=over(M,R,C,pore,0,235,255)
    return K.pack(col,M,R,C)

def mul_retro_patch(seed=42,attempt=1):
    """Crowded enclosed bead lenses with metal backings and binder menisci."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+6101,11,.9))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+6102)[lab];t=K.tiers(h)
    q=d/(4.7+.65*h);roof=np.sqrt(np.clip(1-q*q,0,1))
    cup=K.near(np.abs(q-.86)*5,.7)
    heart=1-K.sstep(1.2,2.5,np.hypot(u-1.2,v+1.4))
    backing=K.sstep(.10,.45,u/5)*K.sstep(.55,.78,q)*(1-K.sstep(.97,1.10,q))
    binder=K.near(np.abs(q-1.14)*5,.75)
    p=x+y*.35;seam=K.iso(p+3*K.noise(seed+6103,40),29,1.0)[0]
    region=K.unit(K.fbm(seed+6104,(4,10,26),.62))
    glass=K.ramp(.65*region+.35*t,['515168','9c88a5','cbb4b9','eadac4'])
    col=glass*(.45+.62*roof)[...,None]
    col=K.mix(col,glass*.28,cup*.84)
    col=K.mix(col,np.array([.91,.75,.44],F),backing*.80)
    col=K.mix(col,np.array([.95,.97,.88],F),heart*.85)
    col=K.mix(col,np.array([.62,.79,.82],F),binder*.44)
    col=K.mix(col,np.array([.13,.13,.23],F),seam*.83)
    M=5+50*t;R=20+55*(1-roof)+30*t;C=16+100*t
    M,R,C=over(M,R,C,cup,10+30*t,135+100*t,160+80*t)
    M,R,C=over(M,R,C,backing,170+75*t,30+75*t,25+125*t)
    M,R,C=over(M,R,C,heart,20+65*t,16+35*t,16+55*t)
    M,R,C=over(M,R,C,binder,5+35*t,40+85*t,25+100*t)
    M,R,C=over(M,R,C,seam,5,215+30*t,220+25*t)
    return K.pack(col,M,R,C)

def mul_tape_seam(seed=42,attempt=1):
    """Independent tape passes composite in actual overlap order."""
    if attempt>=6:return _gaffer_cache_tiles(seed,rows=16 if attempt>=7 else 128)
    x,y=K.xy();region=K.unit(K.fbm(seed+6201,(4,10,24),.62))
    col=K.ramp(region,['182c30','3f5555','7c8176'])
    M=8+20*region;R=150+70*region;C=170+70*region
    for index,angle in enumerate((.32,-.58,1.15) if attempt<4 else (.32,-.58)):
        u,v=K.rot(x,y,F(angle));u+=5*K.noise(seed+6210+index,60)
        row=np.floor(u/31).astype(np.int32);a=K.frac(u/31)*31
        h=K.fhash(row,np.floor(v/15),seed+6220+index);t=K.tiers(h)
        rag=1.3*K.noise(seed+6230+index,230)
        strip=K.sstep(4+rag,5+rag,a)*(1-K.sstep(18+rag,19+rag,a))
        lip=K.near(np.abs(a-19.5-rag),.85)
        contour=K.iso_line if attempt>=5 else lambda f,s,w:K.iso(f,s,w)[0]
        crease=contour(v+2*np.sin(u*.2),12,.8)*strip
        torn=K.near(np.abs(a-4.5-rag),1.0)*K.sstep(.4,.7,K.frac(v/8))
        witness=contour(v+h*5,8,.7)*lip
        shades=[['192b35','4c5b62','8d9691'],['3a3437','72686b','b4a89a'],['273629','566450','9c9d78']][index]
        if attempt>=5:
            values=np.arange(8,dtype=F)/F(7)
            palette=K.ramp(values,shades)
            tape=palette[np.rint(t*F(7)).astype(np.int32)]
        else:tape=K.ramp(t,shades)
        shade=.70+.29*np.sin((a-4)/15*F(np.pi))
        # A3: keep the same native three-pass tape topology, blend small row
        # tiles so five consecutive RGB operations stay in cache. SPB-105.
        for start in range(0,2048,256):
            sl=slice(start,start+256)
            if attempt>=5:
                # Same ordered blends, one reused private tile buffer.
                tile=col[sl];scratch=np.empty_like(tile)
                for target,alpha in ((tape[sl]*shade[sl,...,None],strip[sl]),(tape[sl]*F(.30),crease[sl]*F(.67)),(np.array([.64,.49,.30],F),lip[sl]*F(.48)),(np.array([.78,.75,.60],F),torn[sl]*F(.65)),(np.array([.13,.17,.21],F),witness[sl]*F(.7))):
                    np.subtract(target,tile,out=scratch);scratch*=alpha[...,None];tile+=scratch
                continue
            tile=K.mix(col[sl],tape[sl]*shade[sl,...,None],strip[sl])
            tile=K.mix(tile,tape[sl]*.30,crease[sl]*.67)
            tile=K.mix(tile,np.array([.64,.49,.30],F),lip[sl]*.48)
            tile=K.mix(tile,np.array([.78,.75,.60],F),torn[sl]*.65)
            col[sl]=K.mix(tile,np.array([.13,.17,.21],F),witness[sl]*.7)
        M,R,C=over(M,R,C,strip,2+20*t,140+90*t,155+85*t)
        M,R,C=over(M,R,C,crease,3,220+25*t,225+25*t)
        M,R,C=over(M,R,C,lip,4+25*t,55+95*t,40+125*t)
        M,R,C=over(M,R,C,torn,3+15*t,190+55*t,205+40*t)
        M,R,C=over(M,R,C,witness,10+45*t,150+85*t,150+95*t)
    return K.pack(col,M,R,C)

def _gaffer_cache_tiles(seed,rows=128):
    # SPB-105 / CORE-WORKS a6: actual export a5 exposed memory pressure above
    # the 3s native budget. Same two-pass topology; compute features with a
    # Sobel halo and blend private 128-row tiles, including material channels.
    # SPB-105 / CORE-WORKS tick a7: owner "FINE DETAILS" preserved byte-exact.
    # Private 16-row tiles cut a6's 2.20s construction to 1.45s in the cold
    # controlled trial; paint/spec difference 0. Diagnostic M7 78.9 -> 78.8 (Viper changed the cohort; pixels unchanged).
    # This is a computation change, not an additional construction identity.
    x,y=K.xy();region=K.unit(K.fbm(seed+6201,(4,10,24),.62))
    col=K.ramp(region,['182c30','3f5555','7c8176']);M=8+20*region;R=150+70*region;C=170+70*region
    values=np.arange(8,dtype=F)/F(7)
    for index,angle in enumerate((.32,-.58)):
        warp=F(5)*K.noise(seed+6210+index,60);ragfield=F(1.3)*K.noise(seed+6230+index,230)
        shades=[['192b35','4c5b62','8d9691'],['3a3437','72686b','b4a89a']][index];palette=K.ramp(values,shades)
        for start in range(0,2048,rows):
            end=min(start+rows,2048);lo=max(0,start-1);hi=min(2048,end+1);outer=slice(lo,hi);inner=slice(start-lo,end-lo);dest=slice(start,end)
            u,v=K.rot(x[outer],y[outer],F(angle));u+=warp[outer]
            row=np.floor(u/F(31)).astype(np.int32);a=K.frac(u/F(31))*F(31)
            h=K.fhash(row,np.floor(v/F(15)),seed+6220+index);t=K.tiers(h);rag=ragfield[outer]
            strip=K.sstep(4+rag,5+rag,a)*(1-K.sstep(18+rag,19+rag,a));lip=K.near(np.abs(a-19.5-rag),.85)
            crease=K.iso_line(v+2*np.sin(u*.2),12,.8)*strip
            torn=K.near(np.abs(a-4.5-rag),1.0)*K.sstep(.4,.7,K.frac(v/8))
            witness=K.iso_line(v+h*5,8,.7)*lip;shade=.70+.29*np.sin((a-4)/15*F(np.pi))
            strip,lip,crease,torn,witness,t,shade=[q[inner] for q in (strip,lip,crease,torn,witness,t,shade)]
            tape=palette[np.rint(t*F(7)).astype(np.int32)];tile=col[dest];scratch=np.empty_like(tile)
            for target,alpha in ((tape*shade[...,None],strip),(tape*F(.30),crease*F(.67)),(np.array([.64,.49,.30],F),lip*F(.48)),(np.array([.78,.75,.60],F),torn*F(.65)),(np.array([.13,.17,.21],F),witness*F(.7))):
                np.subtract(target,tile,out=scratch);scratch*=alpha[...,None];tile+=scratch
            mscratch=np.empty_like(t)
            states=((strip,(2+20*t,140+90*t,155+85*t)),(crease,(3,220+25*t,225+25*t)),(lip,(4+25*t,55+95*t,40+125*t)),(torn,(3+15*t,190+55*t,205+40*t)),(witness,(10+45*t,150+85*t,150+95*t)))
            for alpha,targets in states:
                alpha=np.clip(alpha,0,1)
                for base,target in zip((M[dest],R[dest],C[dest]),targets):
                    np.subtract(target,base,out=mscratch);mscratch*=alpha;base+=mscratch
    return K.pack(col,M,R,C)

def mul_pixel_break(seed=42,attempt=1):
    """Unequal 8–32px guillotine pixels, each with its own internal registration."""
    r=K.rng(seed+6301);n=K.N
    label=np.zeros((n,n),np.int32);leaves=[]
    def split(x,y,w,h):
        if w<=32 and h<=32:
            leaves.append((x,y,w,h));label[y:y+h,x:x+w]=len(leaves)-1;return
        axis=(w>h) if w!=h else r.random()>.5
        if axis:
            cut=int(r.integers(max(8,int(w*.30)),min(w-8,int(w*.70))+1))
            split(x,y,cut,h);split(x+cut,y,w-cut,h)
        else:
            cut=int(r.integers(max(8,int(h*.30)),min(h-8,int(h*.70))+1))
            split(x,y,w,cut);split(x,y+cut,w,h-cut)
    split(0,0,n,n)
    cells=np.asarray(leaves,F);x,y=K.xy()
    a=x-cells[label,0];b=y-cells[label,1];w=cells[label,2];height=cells[label,3]
    h=K.hash01(np.arange(len(leaves)),seed+6302)[label];t=K.tiers(h)
    foil=(h>.46).astype(F)
    edge=K.near(np.minimum(np.minimum(a,w-a),np.minimum(b,height-b)),.75)
    slot=K.near(np.abs(b-height*.62),.85)*K.sstep(w*.2,w*.3,a)*(1-K.sstep(w*.7,w*.8,a))*(h>.30)
    scan=K.iso(a+b*.15,8,.65)[0]*(1-edge)*(h>.57)
    corner=K.near(np.hypot(a-2.5,b-2.5),.9)*(h>.35)
    region=K.unit(K.fbm(seed+6303,(3,10,28),.60))
    metal=K.ramp(.65*region+.35*t,['15375f','3976b0','8ec4d5','e2e5c4'])
    ink=K.ramp(.55*region+.45*t,['3b1944','7d366e','c77591','eabaad'])
    roof=np.sin(a/np.maximum(w,1)*F(np.pi))*.5+np.sin(b/np.maximum(height,1)*F(np.pi))*.5
    col=K.mix(ink,metal,foil)*(.63+.40*roof)[...,None]
    col=K.mix(col,np.array([.09,.078,.16],F),edge*.90)
    col=K.mix(col,np.array([.92,.84,.57],F),scan*.64)
    col=K.mix(col,np.array([.025,.02,.045],F),slot)
    col=K.mix(col,np.array([.97,.96,.80],F),corner)
    M=20+55*t;R=130+75*t;C=130+100*t
    M,R,C=over(M,R,C,foil,170+75*t,25+85*(1-roof)+25*t,25+135*t)
    M,R,C=over(M,R,C,edge,8,210+35*t,220+25*t)
    M,R,C=over(M,R,C,scan,130+110*t,35+85*t,35+130*t)
    M,R,C=over(M,R,C,slot,3,230,250)
    M,R,C=over(M,R,C,corner,210+40*t,18+45*t,18+70*t)
    return K.pack(col,M,R,C)

def mul_decoy_blackout(seed=42,attempt=1):
    """Restrained blackout paint hides deliberately dynamic coated apertures."""
    x,y=K.xy();u,v=K.warp(seed+6401,10,39)
    j=np.floor(v/24).astype(np.int32);u+=(j%2)*F(14)
    i=np.floor(u/28).astype(np.int32);a=K.frac(u/28)*28-14;b=K.frac(v/24)*24-12
    h=K.fhash(i,j,seed+6402);t=K.tiers(h)
    q=np.maximum(np.abs(a)/11,np.abs(b)/(6.5+2*h))+.07*np.sin(a*.5+h*4)
    mask=1-K.sstep(.8,1.1,q)
    aperture=K.sstep(.5,.72,np.cos(a*.27+h*4))*mask
    rim=K.near(np.abs(q-1.0)*9,.65)
    tooth=K.iso(a+1.5*np.sin(b*.7),8,.85)[0]*rim
    cut=K.near(np.abs(b-3-.20*a),.65)*mask*(h>.48)
    grain=K.unit(K.noise(seed+6403,210))
    base=K.ramp(.7*grain+.3*t,['131b29','283242','414a57','626673'])
    col=base*(.69+.15*mask)[...,None]
    col=K.mix(col,base*.67,aperture*.35)
    col=K.mix(col,np.array([.35,.39,.43],F),rim*.50)
    col=K.mix(col,np.array([.14,.16,.21],F),tooth*.72)
    col=K.mix(col,np.array([.055,.07,.10],F),cut*.7)
    M=3+20*t;R=155+75*t;C=175+65*t
    M,R,C=over(M,R,C,mask,2+18*t,175+65*t,195+50*t)
    M,R,C=over(M,R,C,aperture,5+40*t,18+50*t,16+65*t)
    M,R,C=over(M,R,C,rim,55+125*t,35+80*t,30+125*t)
    M,R,C=over(M,R,C,tooth,3+12*t,180+55*t,200+40*t)
    M,R,C=over(M,R,C,cut,1,235,255)
    return K.pack(col,M,R,C)

def mul_edge_chamfer(seed=42,attempt=1):
    """Nested contradictory octagonal bevels with a separate centre window."""
    x,y=K.xy();u,v=K.warp(seed+6501,5,43);u,v=K.rot(u,v,F(.31))
    i=np.floor(u/27).astype(np.int32);j=np.floor(v/27).astype(np.int32)
    a=K.frac(u/27)*27-13.5;b=K.frac(v/27)*27-13.5
    h=K.fhash(i,j,seed+6502);t=K.tiers(h)
    q=np.maximum(np.maximum(np.abs(a),np.abs(b)),(np.abs(a)+np.abs(b))*.72)
    outer=K.near(np.abs(q-11.2),1.2)
    inner=K.near(np.abs(q-6.9),1.0)
    counter=K.near(np.abs(np.maximum(np.abs(a-1.8),np.abs(b+1.0))-8.5),.75)
    window=1-K.sstep(6.0,7.3,q)
    cut=K.iso(a+b+h*3,8,.7)[0]*K.sstep(7,9,q)*(1-K.sstep(12,13,q))
    shade=np.clip(.5+(a+b)/27,0,1)
    region=K.unit(K.fbm(seed+6503,(4,11,25),.60))
    plane=K.ramp(.65*region+.35*t,['442d50','906487','cfa2ae','e7d5c0'])
    col=plane*(.54+.48*shade)[...,None]
    col=K.mix(col,np.array([.17,.21,.32],F),window*.75)
    col=K.mix(col,np.array([.93,.96,.88],F),outer*.84)
    col=K.mix(col,np.array([.07,.05,.10],F),inner*.9)
    col=K.mix(col,np.array([.94,.61,.29],F),counter*.85)
    col=K.mix(col,col*.32,cut*.70)
    M=55+125*t;R=35+75*(1-shade)+30*t;C=25+145*t
    M,R,C=over(M,R,C,window,15+60*t,95+90*t,65+145*t)
    M,R,C=over(M,R,C,outer,185+65*t,18+50*t,18+85*t)
    M,R,C=over(M,R,C,inner,8+20*t,180+60*t,205+40*t)
    M,R,C=over(M,R,C,counter,155+95*t,35+85*t,40+140*t)
    M,R,C=over(M,R,C,cut,10+35*t,165+75*t,165+75*t)
    return K.pack(col,M,R,C)
