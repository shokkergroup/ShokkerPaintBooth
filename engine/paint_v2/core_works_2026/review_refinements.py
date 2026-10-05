"""Distinct constructions after the actual-output cross-card review.
SPB-105 / CORE-WORKS 2026-09-30: owner asks for unique fine material stories.
Actual gate: Flow/Hex .66452, Flow/Laminate .57801; Ceramic/Craze .59061,
Ceramic/Blush .56670; AirRelease/PixelBreak .55339. Previous carriers retained
in attempt evidence. M7 remains diagnostic; no owner verdict is invented.
"""
import numpy as np
from . import kit as K
from .common import over
F=np.float32


def flow_streamlets(seed=42,attempt=4):
    """Short curved foil streamlets, split tails and independently worked beds."""
    x,y=K.xy();lab,_,pts=K.voronoi(K.sites(seed+12241,22,1.0))
    a,b=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+12242)[lab]
    h2=K.hash01(np.arange(len(pts)),seed+12243)[lab];t=K.tiers(h);t2=K.tiers(h2)
    angle=F(.6)+F(1.3)*np.sin(pts[lab,1]/F(81))+F(.7)*np.cos(pts[lab,0]/F(99))+F(.55)*(h2-.5)
    u=a*np.cos(angle)+b*np.sin(angle);v=-a*np.sin(angle)+b*np.cos(angle)
    bend=F(2.8)*np.sin(u/F(5.5)+h2*F(3))+F(.016)*u*u*(h-.5)
    d=v-bend;ends=1-K.sstep(8,13,np.abs(u))
    span=F(2.6)+F(1.6)*K.sstep(-12,8,u)
    tail=K.near(np.abs(d),.65)*K.sstep(2,8,u)
    foil=K.near(np.abs(d),span)*ends*(1-tail)
    roof=np.clip(1-(d/(span+.5))**2,0,1)
    rail=K.near(np.abs(d-span+.55),.55)*ends
    bed=K.near(np.abs(d),span+1.5)*ends*(1-foil)
    rung=K.near(np.abs(K.frac((u+13)/8)*8-4),.6)*foil*K.sstep(-8,2,u)
    lip=K.near(np.abs(u+9),.65)*foil
    port=K.near(np.hypot(u-5,d-1.9),1.15)*(h2>.57)
    # Local populations own colour. No broad house background can dominate
    # grayscale comparison or turn two unrelated processes into one carrier.
    ink=K.ramp(t2,['201b35','5a3156','a46f86','d8a594'])
    metal=K.ramp(.55*t+.45*(1-t2),['0b4253','268293','9ccdb4','eee1a3'])
    col=ink*(.76+.24*t)[...,None]
    col=K.mix(col,ink*.13,bed*.85)
    col=K.mix(col,metal*(.38+.65*roof)[...,None],foil)
    col=K.mix(col,np.array([.99,.82,.48],F),rail*.86)
    col=K.mix(col,metal*.17,rung*.65)
    col=K.mix(col,np.array([.62,.88,.82],F),lip*.78)
    col=K.mix(col,np.array([.025,.025,.04],F),np.maximum(port,tail*ends)*.93)
    M=15+50*t2;R=125+105*t2;C=155+85*t2
    M,R,C=over(M,R,C,bed,5+15*t2,195+45*t2,215+35*t2)
    M,R,C=over(M,R,C,foil,145+105*t,22+80*(1-roof)+45*t2,20+145*t2)
    M,R,C=over(M,R,C,rail,210+40*t,18+45*t2,16+75*t)
    M,R,C=over(M,R,C,rung,45+110*t,145+90*t2,165+75*t)
    M,R,C=over(M,R,C,lip,165+80*t2,25+65*t,20+95*t2)
    M,R,C=over(M,R,C,np.maximum(port,tail*ends),5+15*t,215+30*t2,230+25*t)
    return K.pack(col,M,R,C)


def ceramic_levelled_glaze(seed=42,attempt=4):
    """A restrained intact glaze with fine fluid contact/levelling anatomy."""
    x,y=K.xy();lab,_,pts=K.voronoi(K.sites(seed+11641,23,1.0))
    a,b=K.cell_local(lab,pts,x,y)
    h=K.hash01(np.arange(len(pts)),seed+11642)[lab]
    h2=K.hash01(np.arange(len(pts)),seed+11643)[lab];t=K.tiers(h);t2=K.tiers(h2)
    angle=h2*F(6.283185);u=a*np.cos(angle)+b*np.sin(angle);v=-a*np.sin(angle)+b*np.cos(angle)
    # Unequal levelling tongues terminate in a wet contact neck, rather than
    # fracture lines or condensation cloud patches used by its neighbours.
    tongue_radius=np.hypot((u+2.1)*F(.67),v+F(.8)*np.sin(u/F(3.5)))
    tongue=1-K.sstep(4.5,6.7,tongue_radius)
    neck=K.near(np.abs(v),.8)*K.sstep(2,5,u)*(1-K.sstep(8,10,u))
    radius=np.hypot((u-5.2)*F(.91),v-F(.45))
    contact=(h>.42).astype(F)
    bead=(1-K.sstep(2.4,4.0,radius))*contact
    dome=np.sqrt(np.clip(1-(radius/F(4.1))**2,0,1))
    meniscus=K.near(np.abs(tongue_radius-6.4),.65)*(1-bead)
    bead_lip=K.near(np.abs(radius-3.8),.65)*contact
    stria=K.near(np.abs(K.frac((u+2)/8)*8-4),.55)*tongue
    witness=K.near(np.hypot(u+5,v-1),1.1)*(h2>.94)
    # Intentionally quiet blue-grey, with independently local glass thickness.
    # No coloured macro clouds; the small fluid features carry the identity.
    base=np.stack((.40+.08*t2,.59+.075*t2,.65+.065*t2),axis=-1).astype(F)
    col=base.copy();col=K.mix(col,base*(1.02+.075*t)[...,None],tongue*.68)
    col=K.mix(col,base*.85,stria*.30)
    col=K.mix(col,np.array([.77,.87,.86],F),meniscus*.25)
    col=K.mix(col,base*(.79+.29*dome)[...,None],bead*.77)
    col=K.mix(col,np.array([.77,.87,.86],F),bead_lip*.44)
    col=K.mix(col,base*.72,neck*.26)
    col=K.mix(col,np.array([.84,.76,.55],F),witness*.70)
    M=5+20*t2;R=22+37*t2;C=16+45*t2
    M,R,C=over(M,R,C,tongue,6+25*t,20+40*t2,16+50*t)
    M,R,C=over(M,R,C,stria,8+22*t2,70+80*t,75+110*t2)
    M,R,C=over(M,R,C,meniscus,10+35*t2,22+50*t,18+65*t2)
    M,R,C=over(M,R,C,bead,5+25*t,18+45*(1-dome)+20*t2,16+55*t)
    M,R,C=over(M,R,C,bead_lip,12+40*t2,22+45*t,18+60*t2)
    M,R,C=over(M,R,C,neck,5+20*t,65+65*t2,65+95*t)
    M,R,C=over(M,R,C,witness,80+135*t,40+75*t2,40+110*t)
    return K.pack(col,M,R,C)


def air_release_manifold(seed=42,attempt=2):
    """Curved spines feed unequal oblique blind vents in an adhesive film."""
    x,y=K.xy();u=F(.79)*x+F(.61)*y;v=-F(.61)*x+F(.79)*y
    u+=F(2.7)*np.sin(v/F(15))+F(1.4)*K.noise(seed+10921,143)
    i=np.floor(u/F(24)).astype(np.int32);a=K.frac(u/F(24))*F(24)-F(12)
    q=v+F(4)*np.sin(i.astype(F)*F(1.13));j=np.floor(q/F(21)).astype(np.int32)
    b=K.frac(q/F(21))*F(21)-F(10.5)
    h=K.fhash(i,j,seed+10922);h2=K.fhash(i,j,seed+10923);t=K.tiers(h);t2=K.tiers(h2)
    side=np.where((j%2)==0,F(1),F(-1));along=a*side
    # Open spine plus short, blind oblique feeders: no box-grid intersections.
    spine_d=np.abs(a);feeder_d=np.abs(b-F(.62)*along-F(.9)*np.sin(along/F(3)))
    feeder=K.near(feeder_d,1.05)*K.sstep(-.5,1.5,along)*(1-K.sstep(8,10,along))
    spine=K.near(spine_d,1.3);channel=np.maximum(spine,feeder)
    wall=np.maximum(K.near(np.abs(spine_d-2.6),.65),K.near(np.abs(feeder_d-2.25),.6)*K.sstep(0,2,along)*(1-K.sstep(8,10,along)))
    collector=K.near(np.hypot(a/F(1.25),b),2.7)
    throat=K.near(np.hypot(a-side*F(2.3),b-F(1.45)),1.3)
    blind=K.near(np.hypot(along-8.2,b-F(5.5)),1.45)
    roof_rib=K.near(np.abs(b+F(.22)*a+3),.6)*(1-channel)*(np.abs(a)>4)
    film=K.ramp(.75*t2+.25*t,['625743','a89e7d','d7d4b2','f0e9d2'])
    col=film*(.85+.15*t)[...,None]
    col=K.mix(col,film*.14,channel*.92)
    col=K.mix(col,np.array([.48,.72,.70],F),wall*.72)
    col=K.mix(col,film*.10,collector*.85)
    col=K.mix(col,np.array([.29,.43,.48],F),throat*.86)
    col=K.mix(col,film*.29,blind*.75)
    col=K.mix(col,film*.69,roof_rib*.53)
    M=15+75*t;R=35+75*t2;C=25+110*t
    M,R,C=over(M,R,C,channel,5+15*t,170+70*t2,195+55*t)
    M,R,C=over(M,R,C,wall,65+140*t2,25+65*t,20+95*t2)
    M,R,C=over(M,R,C,collector,5+15*t2,205+35*t,220+30*t2)
    M,R,C=over(M,R,C,throat,15+60*t,115+110*t2,130+110*t)
    M,R,C=over(M,R,C,blind,10+40*t2,130+105*t,145+100*t2)
    M,R,C=over(M,R,C,roof_rib,20+80*t,90+110*t2,100+120*t)
    return K.pack(col,M,R,C)
