"""Snake surfaces with finish-owned scale architecture and microdermatoglyphs.
SPB-105 / CORE-WORKS 2026-09-30. Fine material regions replace flat green specs.
"""
import numpy as np
from . import kit as K
from .common import over
F=np.float32

def slt_sunbeam_iris(seed=42, attempt=1):
    """Swept overlapping lance scales; interference travels inside each scale."""
    x,y=K.xy()
    wx,wy=K.warp(seed+301,17,11)
    if attempt>=5:
        wx+=F(1.7)*K.noise(seed+317,132);wy+=F(1.9)*K.noise(seed+318,161)
    # Rows wander as a biological skin, while scales remain 14x23px.
    v=wy+11*np.sin(wx/F(130.)+.3*K.noise(seed+302,12))
    j=np.floor(v/F(15.)).astype(np.int32)
    row_offset=(j%2).astype(F) if attempt>=6 else j%2
    u=wx+row_offset*F(9.)+K.fhash(j,None,seed+303)*F(3.)
    i=np.floor(u/F(18.)).astype(np.int32)
    a=u/F(18.)-i.astype(F); b=v/F(15.)-j.astype(F)
    ident=K.fhash(i,j,seed+304)
    # A scale's trailing tongue projects into the next row. This is not an
    # ellipsoid/polka-dot field; upper shoulders recede and lips overlap.
    shoulder=.08+.23*np.abs(a-.5)*2
    body=K.sstep(shoulder,shoulder+.10,b)
    tongue=np.sqrt(np.clip(1-((a-.5)*2)**2,0,1))
    roof=np.clip(.78*(1-b)+.22*tongue,0,1)
    groove=K.near(np.abs(a-.5)-(.12+.3*b),.035)*body
    lip=K.near(b-shoulder,.045)
    if attempt>=2:
        # A2: distance functions use native pixels; unit-cell AA=1 washed whole faces.
        groove=K.near((np.abs(a-.5)-(.12+.3*b))*18,.7)*body
        lip=K.near((b-shoulder)*15,.7)
    if attempt>=3:
        groove=K.near(np.abs((np.abs(a-.5)-(.12+.3*b))*18),.7)*body
        lip=K.near(np.abs((b-shoulder)*15),.7)
    slit=1-body
    region=K.unit(K.fbm(seed+305,(3,7,15),.6))
    film_phase=.45*region+.22*ident+.18*a+.09*b
    rainbow=K.thin_film(film_phase,.96,.77)
    dark=K.ramp(region,['050c18','0e2525','182144','351337'])
    if attempt>=2:
        # Regional colour ownership stops tiny spectral hues averaging to grey.
        fam=K.sstep(.43,.62,region)
        cool=K.ramp(.3*ident+.7*roof,['081237','164198','18aabb','79eed0'])
        warm=K.ramp(.4*ident+.6*roof,['220b2d','632163','c44897','f9c56a'])
        rainbow=K.mix(K.mix(cool,warm,fam),rainbow,.20)
    col=K.mix(dark,rainbow*(.45+.65*roof)[...,None],body)
    col *= (1-.5*groove)[...,None]
    col=K.mix(col,np.array([.7,.88,.97],F),lip*(.25+.6*ident))
    # Striae are clipped to scales and use the scale's own phase, not overlay noise.
    stria=K.iso((a-.5)*18+b*8+ident*5,8,.9)[0]*body*(.25+.35*roof)
    col=K.mix(col,rainbow*1.2,stria*.35)
    tiers=K.tiers(ident)
    M=55+125*tiers+42*roof
    R=18+70*(1-roof)+70*groove+30*tiers
    C=16+160*(1-roof)*(.35+.65*tiers)
    if attempt>=2:
        R=18+190*(1-roof)**1.5+45*groove+20*tiers
        C=16+185*tiers*(1-.5*roof)
    if attempt>=4:
        # A4: wet pearl faces, dry roots and dermal grooves are separate
        # materials. The earlier smooth face ramp competed with their edges.
        R=22+55*(1-roof)+20*tiers
        C=16+75*tiers+55*region
    M,R,C=over(M,R,C,slit,10+25*tiers,165+65*tiers,185+60*tiers)
    M,R,C=over(M,R,C,lip,210+40*tiers,20+45*(1-tiers),25+100*tiers)
    M,R,C=over(M,R,C,stria,90+150*tiers,35+105*tiers,45+150*(1-tiers))
    if attempt>=4:
        M,R,C=over(M,R,C,groove,8+20*tiers,215+35*tiers,215+40*tiers)
        M,R,C=over(M,R,C,slit,8+20*tiers,220+30*tiers,205+45*tiers)
        M,R,C=over(M,R,C,lip,205+45*tiers,16+35*(1-tiers),16+65*tiers)
    return K.pack(col,M,R,C)

def slt_reticulated(seed=42,attempt=1):
    """Pinched irregular net blocks packed with clipped dermal crescents."""
    x,y=K.xy();u,v=K.warp(seed+3101,10,35);u,v=K.rot(u,v,F(.62))
    j=np.floor(v/24).astype(np.int32);u+=(j%2)*F(13)
    i=np.floor(u/26).astype(np.int32);a=K.frac(u/26)*26-13;b=K.frac(v/24)*24-12
    h=K.fhash(i,j,seed+3102);t=K.tiers(h)
    q=np.abs(a)*(1+.13*np.sin(b*.35))+.83*np.abs(b)+(h-.5)*2.0
    block=1-K.sstep(10.5,12.3,q)
    net=1-block
    collar=K.near(np.hypot(np.abs(a)-11,np.abs(b)-10),1.8)
    face=np.clip(1-q/15,0,1)
    crescent=K.iso(np.hypot(a+3,b+1.5*h),8,.85)[0]*block
    pore=(1-K.sstep(1.1,2.1,np.hypot(a+3+2*h,b+6)))*(h>.28)*block
    region=K.unit(K.fbm(seed+3103,(3,10,29),.61))
    dark=K.ramp(.7*region+.3*t,['1c172b','463443','705456','a78270'])*(.62+.50*face)[...,None]
    pale=K.ramp(.55*region+.45*t,['866143','c5a06c','ecd6a5','f8edca'])
    col=K.mix(dark,pale,net)
    col=K.mix(col,dark*.28,crescent*.68)
    col=K.mix(col,np.array([.94,.96,.86],F),collar*.65)
    col=K.mix(col,np.array([.032,.045,.06],F),pore)
    M=25+90*t;R=45+75*(1-face)+30*t;C=25+150*t
    M,R,C=over(M,R,C,net,150+95*t,25+75*t,25+130*(1-t))
    M,R,C=over(M,R,C,crescent,10+35*t,175+65*t,170+70*t)
    M,R,C=over(M,R,C,collar,215+35*t,18+42*t,16+80*t)
    M,R,C=over(M,R,C,pore,3,230,250)
    return K.pack(col,M,R,C)

def slt_keeled_viper(seed=42,attempt=1):
    """Independent left/right slopes are split by a raised spear keel."""
    if attempt>=2:return _viper_packed_keels(seed,reverse_rows=attempt>=3,split_material=attempt>=4)
    x,y=K.xy();u,v=K.warp(seed+3201,8,25)
    j=np.floor(v/29).astype(np.int32);u+=(j%2)*F(10)
    i=np.floor(u/20).astype(np.int32);a=K.frac(u/20)*20-10;b=K.frac(v/29)*29-14.5
    h=K.fhash(i,j,seed+3202);t=K.tiers(h)
    q=np.abs(a)/(8.4+.8*h)+np.abs(b)/F(16)
    face=1-K.sstep(.88,1.04,q)
    roof=np.clip(1-np.abs(a)/9,0,1)*face
    keel=K.near(np.abs(a-1.0*np.sin(b*.25+h*4)),.95)*face
    shoulder=1-face
    cut=K.iso(b+a*.65+h*4,8,.85)[0]*face*(1-keel)
    hook=K.near(np.hypot(a-2,b-11),1.7)*(h>.45)
    region=K.unit(K.fbm(seed+3203,(4,9,25),.58))
    left=K.ramp(.55*region+.45*t,['174137','42856a','8dcc9e','dce9b9'])
    right=K.ramp(.65*region+.35*t,['51352b','966441','dbaa67','f2d5a0'])
    plane=K.mix(left,right,K.sstep(-.8,.8,a))*(.57+.55*roof)[...,None]
    col=K.mix(K.ramp(region,['102d2a','3d5c42','829779']),plane,face)
    col=K.mix(col,plane*.35,cut*.68)
    col=K.mix(col,np.array([.75,.96,.83],F),keel*(.65+.3*t))
    col=K.mix(col,np.array([.98,.73,.43],F),hook)
    M=40+110*t+60*roof;R=32+95*(1-roof);C=20+135*t
    M,R,C=over(M,R,C,shoulder,8+20*t,175+65*t,190+60*t)
    M,R,C=over(M,R,C,cut,15+60*t,145+100*t,160+75*t)
    M,R,C=over(M,R,C,keel,195+50*t,18+42*t,18+85*t)
    M,R,C=over(M,R,C,hook,200+50*t,20+45*t,22+90*t)
    return K.pack(col,M,R,C)

def _viper_packed_keels(seed,reverse_rows=False,split_material=False):
    # SPB-105 / CORE-WORKS a2 / owner: density > size, never lazy.
    # Native owner-review page exposed a1's bare green backing. Keep fine
    # 14–29px scale anatomy; stack overlapping asymmetric spear polygons.
    # M7 movements remain diagnostics in the retained attempt evidence.
    import cv2
    x,y=K.xy();rng=np.random.default_rng(seed+32021)
    yy,xx=np.mgrid[-1:116,-1:160];centres=np.stack(((xx+(yy%2)*.5)*13,yy*18),-1).reshape(-1,2).astype(F)
    centres+=rng.uniform(-2.3,2.3,centres.shape).astype(F);count=len(centres)
    angle=rng.uniform(-.17,.17,count).astype(F);scale=rng.uniform([.88,.85],[1.08,1.08],(count,2)).astype(F)
    vertices=np.array([[-6.5,-10],[4,-12],[7.5,-1],[1.5,13],[-5,5]],F)
    local=vertices[None,:,:]*scale[:,None,:];cc=np.cos(angle);ss=np.sin(angle)
    polygons=np.rint(centres[:,None,:]+np.stack((local[...,0]*cc[:,None]-local[...,1]*ss[:,None],local[...,0]*ss[:,None]+local[...,1]*cc[:,None]),-1)).astype(np.int32)
    ids=np.zeros((2048,2048),np.int32)
    order=range(count-1,-1,-1) if reverse_rows else range(count)
    for i in order:cv2.fillConvexPoly(ids,polygons[i],i+1,cv2.LINE_8)
    centres=np.vstack((np.zeros((1,2),F),centres));angle=np.r_[F(0),angle];scale=np.vstack((np.ones((1,2),F),scale))
    dx=x-centres[ids,0];dy=y-centres[ids,1];cos=np.cos(angle[ids]);sin=np.sin(angle[ids])
    a=(dx*cos+dy*sin)/scale[ids,0];b=(-dx*sin+dy*cos)/scale[ids,1]
    h=K.hash01(np.arange(count+1),seed+32022)[ids];h2=K.hash01(np.arange(count+1),seed+32023)[ids];t=K.tiers(h);t2=K.tiers(h2)
    face=(ids>0).astype(F);roof=np.clip(1-np.abs(a)/F(8),0,1)
    lap=K.near(K.edge_distance(ids),1.15)*face;root=lap*(b<-4.5)
    keel=K.near(np.abs(a-F(1.05)*np.sin((b+8)/F(4)+h*F(3))),.75)*face
    cuts=K.iso(b+F(.55)*a+h2*F(3),8,.75)[0]*face*(1-keel)
    pore=K.near(np.abs(a+F(3)+F(.25)*np.sin(b)),.65)*K.sstep(-7,-4,b)*(1-K.sstep(3,6,b))*face
    tip=K.near(np.abs(a-F(1.2)-F(.12)*(b-5)),.7)*K.sstep(4,7,b)*face
    left=K.ramp(.65*t+.35*t2,['0c443c','288779','83cbb0','d4ead0'])
    right=K.ramp(.65*(1-t)+.35*t2,['573047','985754','d99e78','f3d8a4'])
    plane=K.mix(left,right,K.sstep(-.55,.55,a))*(.52+.55*roof)[...,None]
    col=K.mix(np.broadcast_to(np.array([.10,.16,.15],F),(2048,2048,3)),plane,face)
    col=K.mix(col,plane*.17,lap*.66);col=K.mix(col,plane*.13,root*.82)
    col=K.mix(col,plane*.33,cuts*.60)
    col=K.mix(col,np.array([.83,.98,.83],F),keel*(.72+.2*t2))
    col=K.mix(col,np.array([.045,.08,.075],F),pore*.84)
    col=K.mix(col,np.array([.99,.79,.47],F),tip*.82)
    M=8+20*t2;R=175+65*t2;C=195+55*t2
    if split_material:
        # a4 material audit: a3's named left/right faces shared one state.
        # Cool foil face polished; warm pigmented face rougher and coat-dull.
        # Both have independent local tiers, not a decorative spec recolour.
        side=K.sstep(-.55,.55,a)
        fm=K.mix(170+65*t+15*roof,55+120*t2,side)
        fr=K.mix(22+55*(1-roof)+55*t2,105+100*t+25*(1-roof),side)
        fc=K.mix(16+95*t,110+125*t2,side)
        M,R,C=over(M,R,C,face,fm,fr,fc)
    else:
        M,R,C=over(M,R,C,face,85+135*t+20*roof,28+65*(1-roof)+75*t2,20+145*t2)
    M,R,C=over(M,R,C,lap,20+50*t2,135+95*t,165+75*t2)
    M,R,C=over(M,R,C,root,8+20*t,195+45*t2,215+35*t)
    M,R,C=over(M,R,C,cuts,25+90*t2,130+110*t,145+100*t2)
    M,R,C=over(M,R,C,keel,200+45*t,18+55*t2,16+90*t)
    M,R,C=over(M,R,C,pore,5+20*t2,200+45*t,220+30*t2)
    M,R,C=over(M,R,C,tip,190+60*t2,22+65*t,20+95*t2)
    return K.pack(col,M,R,C)

def slt_cycloid_gloss(seed=42,attempt=1):
    """Actual overlapping cycloid shells; the front shell occludes its root."""
    import cv2
    r=K.rng(seed+3301);labels=np.zeros((K.N,K.N),np.int32)
    centres=[(-20.,-20.)];sizes=[(13.,13.)]
    # Draw from upper to lower so lower shells cover earlier shell roots.
    for j in range(-1,116):
        for i in range(-1,101):
            cx=i*22+(j%2)*11+r.uniform(-2,2);cy=j*19+r.uniform(-1.6,1.6)
            rx=r.uniform(11.5,14);ry=r.uniform(11.5,14)
            centres.append((cx,cy));sizes.append((rx,ry))
            cv2.ellipse(labels,(int(cx),int(cy)),(int(rx),int(ry)),0,0,360,len(centres)-1,-1)
    centres=np.asarray(centres,F);sizes=np.asarray(sizes,F)
    x,y=K.xy();u=x-centres[labels,0];v=y-centres[labels,1]
    q=np.hypot(u/sizes[labels,0],v/sizes[labels,1])
    roof=np.sqrt(np.clip(1-q*q,0,1))
    h=K.hash01(np.arange(len(centres)),seed+3302)[labels];t=K.tiers(h)
    edge=K.near(K.edge_distance(labels),1.1)
    fan=K.iso(np.arctan2(v+9,u)*13,8,.75)[0]*(1-edge)
    pocket=K.sstep(.80,.97,q)*(v<-2)
    droplet=(1-K.sstep(1.2,2.2,np.hypot(u-4,v-3)))*(h>.71)
    region=K.unit(K.fbm(seed+3303,(4,11,27),.59))
    face=K.ramp(.65*region+.35*t,['183750','417d9c','78b9c7','dddcb1'])
    col=face*(.48+.60*roof+.13*u/14)[...,None]
    col=K.mix(col,face*.25,pocket*.85)
    col=K.mix(col,face*.34,fan*.48)
    col=K.mix(col,np.array([.85,.96,.90],F),edge*(.25+.55*t))
    col=K.mix(col,np.array([.98,.95,.80],F),droplet*.75)
    M=35+115*t;R=18+55*(1-roof)+25*t;C=16+95*t
    M,R,C=over(M,R,C,pocket,10+20*t,180+60*t,200+45*t)
    M,R,C=over(M,R,C,fan,20+90*t,125+105*t,130+100*t)
    M,R,C=over(M,R,C,edge,145+100*t,20+55*t,20+75*t)
    M,R,C=over(M,R,C,droplet,15+45*t,16+25*t,16+35*t)
    return K.pack(col,M,R,C)

def slt_ventral_scute(seed=42,attempt=1):
    """Transverse flexible plates with separately rooted side hinges."""
    x,y=K.xy();u,v=K.warp(seed+3401,9,28)
    j=np.floor(v/14).astype(np.int32);u+=(j%2)*F(14)
    i=np.floor(u/29).astype(np.int32);a=K.frac(u/29)*29;b=K.frac(v/14)*14
    h=K.fhash(i,j,seed+3402);t=K.tiers(h)
    rear=2.0+1.3*np.cos(a*.22+h*4)
    seam=K.near(np.abs(b-rear),.95)
    hinge=K.near(np.abs(a-1.5-1.2*np.sin(b*.45)),1.2)
    lip=K.near(np.abs(b-rear-1.6),.65)
    roof=np.sin(np.clip((b-rear)/12,0,1)*F(np.pi))
    rib=K.iso(a+b*.13+h*4,8,.75)[0]*(1-seam)*(1-hinge)
    pore=(1-K.sstep(.9,1.8,np.hypot(a-3,b-8)))*(h>.45)
    region=K.unit(K.fbm(seed+3403,(3,8,22),.60))
    col=K.ramp(.7*region+.3*t,['4c2b43','946168','c69c86','e8d7ae'])*(.64+.42*roof)[...,None]
    col=K.mix(col,np.array([.10,.08,.14],F),np.clip(seam+hinge,0,1)*.9)
    col=K.mix(col,col*.40,rib*.48)
    col=K.mix(col,np.array([.97,.94,.78],F),lip*.78)
    col=K.mix(col,np.array([.08,.05,.085],F),pore)
    M=35+110*t;R=28+60*(1-roof)+30*t;C=20+120*t
    M,R,C=over(M,R,C,rib,20+60*t,120+100*t,130+100*t)
    M,R,C=over(M,R,C,np.clip(seam+hinge,0,1),5+15*t,200+45*t,205+40*t)
    M,R,C=over(M,R,C,lip,150+95*t,18+45*t,16+75*t)
    M,R,C=over(M,R,C,pore,0,235,255)
    return K.pack(col,M,R,C)

def slt_boa_saddle(seed=42,attempt=1):
    """Curved opposed saddle lobes turn over fine scalloped keratin tesserae."""
    x,y=K.xy();u,v=K.warp(seed+3501,10,27);u,v=K.rot(u,v,F(.22))
    j=np.floor(v/27).astype(np.int32);u+=(j%2)*F(15)
    i=np.floor(u/30).astype(np.int32);a=K.frac(u/30)*30-15;b=K.frac(v/27)*27-13.5
    h=K.fhash(i,j,seed+3502);t=K.tiers(h)
    waist=3.0+7.2*(b/13.5)**2+.9*np.sin(b*.35+h*4)
    dist=np.abs(a)-waist
    saddle=1-K.sstep(-.7,.7,dist)
    rim=K.near(np.abs(dist-1.3),.75)
    pinch=K.near(np.abs(a),.65)*K.near(np.abs(b),3)
    micro=K.frac((u+v*.24)/9)*9-4.5
    scallop=K.near(np.abs(micro)-2.0-.6*np.cos(v*.75),.65)
    freckle=K.sstep(.91,.98,K.fhash(np.floor(u/8),np.floor(v/8),seed+3503))
    region=K.unit(K.fbm(seed+3504,(4,13,23),.55))
    hide=K.ramp(.75*region+.25*t,['694440','b99170','e6c9a0','f6e7c7'])
    dark=K.ramp(.55*region+.45*t,['231c35','553d52','90636c','ba8981'])
    col=K.mix(hide,dark,saddle)
    col *= (.80+.22*np.cos(b*.10))[...,None]
    col=K.mix(col,col*.40,scallop*.55)
    col=K.mix(col,np.array([.97,.92,.74],F),rim*.86)
    col=K.mix(col,np.array([.075,.045,.095],F),np.clip(pinch+freckle,0,1)*.80)
    M=30+95*t;R=65+70*t;C=45+130*(1-t)
    M,R,C=over(M,R,C,saddle,20+55*t,100+90*t,70+140*t)
    M,R,C=over(M,R,C,scallop,12+25*t,180+55*t,180+65*t)
    M,R,C=over(M,R,C,rim,155+90*t,20+65*t,20+95*t)
    M,R,C=over(M,R,C,np.clip(pinch+freckle,0,1),5,225,245)
    return K.pack(col,M,R,C)

def slt_sidewinder_micro(seed=42,attempt=1):
    """Windward polish, broken lee ridges and sand in irregular desert granules."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+3601,18,.90))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+3602)[lab];t=K.tiers(h)
    a,b=K.rot(u,v,F(.65));edge=K.edge_distance(lab)
    wind=K.sstep(-3,3,a)
    roof=np.clip(1-(np.abs(a)*.7+np.abs(b))/12,0,1)
    lee=K.near(edge,1.6)*(1-wind)
    face=K.sstep(.6,2.0,edge)
    pit=(1-K.sstep(1.1,2.0,np.hypot(a-2.5,b+h*3)))*(h>.34)*face
    sand=K.sstep(.68,.90,K.unit(K.noise(seed+3603,220)))*(1-face)
    grain=K.iso(a+b*.28+h*3,8,.7)[0]*face
    region=K.unit(K.fbm(seed+3604,(4,10,24),.60))
    dry=K.ramp(.7*region+.3*t,['5c3c51','95756c','d0b896','e8dbc2'])
    polished=K.ramp(.6*region+.4*t,['3b5960','8baba1','d9dfb6'])
    col=K.mix(dry,polished,wind*.67)*(.68+.38*roof)[...,None]
    col=K.mix(col,np.array([.16,.11,.14],F),lee*.82)
    col=K.mix(col,col*.35,grain*.54)
    col=K.mix(col,np.array([.065,.046,.072],F),pit)
    col=K.mix(col,np.array([.93,.84,.61],F),sand*.80)
    M=30+95*t;R=85+85*(1-wind)+30*t;C=80+125*t
    M,R,C=over(M,R,C,wind*face,100+110*t,25+65*t,25+100*t)
    M,R,C=over(M,R,C,lee,10+25*t,180+60*t,205+40*t)
    M,R,C=over(M,R,C,grain,20+40*t,155+85*t,150+95*t)
    M,R,C=over(M,R,C,pit,0,240,255)
    M,R,C=over(M,R,C,sand,45+85*t,125+100*t,170+65*t)
    return K.pack(col,M,R,C)

def slt_gaboon_geometric(seed=42,attempt=1):
    """Razor hourglass planes and flank wedges with clipped dermal leaf cuts."""
    x,y=K.xy();u,v=K.warp(seed+3701,6,31);u,v=K.rot(u,v,F(-.35))
    j=np.floor(v/30).astype(np.int32);i=np.floor(u/29).astype(np.int32)
    a=K.frac(u/29)*29-14.5;b=K.frac(v/30)*30-15
    h=K.fhash(i,j,seed+3702);t=K.tiers(h)
    waist=3+np.abs(b)*F(.59)
    dist=np.abs(a)-waist
    hourglass=1-K.sstep(-.65,.65,dist)
    bevel=K.near(np.abs(dist)-.65,.65)
    wedge=K.sstep(5,12,np.abs(a)+.8*b)*(1-hourglass)
    cut=K.iso(a*.38+b+h*5,8,.85)[0]*(.4+.6*hourglass)
    root=K.near(np.abs(np.abs(b)-14.3),.7)
    grain=K.unit(K.noise(seed+3703,180));region=K.unit(K.fbm(seed+3704,(4,9,26),.64))
    bronze=K.ramp(.6*region+.4*t,['714827','bc8850','eed093'])
    plum=K.ramp(.7*region+.3*t,['251832','5a3d54','a3737d'])
    flank=K.ramp(.65*region+.35*t,['314b59','78929b','c6d1b8'])
    col=K.mix(bronze,plum,hourglass)
    col=K.mix(col,flank,wedge*.92)*(.84+.17*grain)[...,None]
    col=K.mix(col,col*.34,cut*.57)
    col=K.mix(col,np.array([.98,.89,.71],F),bevel*.85)
    col=K.mix(col,np.array([.045,.034,.061],F),root*.9)
    M=85+115*t;R=40+75*t;C=25+125*t
    M,R,C=over(M,R,C,hourglass,20+65*t,125+80*t,115+100*t)
    M,R,C=over(M,R,C,wedge,80+130*t,35+70*t,25+145*t)
    M,R,C=over(M,R,C,cut,15+40*t,185+50*t,200+40*t)
    M,R,C=over(M,R,C,bevel,170+75*t,20+55*t,18+75*t)
    M,R,C=over(M,R,C,root,4,230,250)
    return K.pack(col,M,R,C)

def slt_milk_band(seed=42,attempt=1):
    """Strict tricolour order on flexible fine anatomical riblets."""
    x,y=K.xy();u,v=K.warp(seed+3801,15,24);v+=u*F(.21)
    phase=K.frac(v/48)*48
    red=K.sstep(0,1,phase)*(1-K.sstep(17,18,phase))
    cream=K.sstep(25,26,phase)*(1-K.sstep(40,41,phase))
    black=np.clip(1-red-cream,0,1)
    i=np.floor(u/10).astype(np.int32);j=np.floor(v/12).astype(np.int32)
    h=K.fhash(i,j,seed+3802);t=K.tiers(h)
    a=K.frac(u/10)*10;b=K.frac(v/12)*12
    seam=K.near(np.abs(b-2.2-1.2*np.cos(a*.45)),.75)
    cuts=K.near(np.abs(a-5.0-.5*np.sin(b)),.65)*red
    pearl=(1-K.sstep(1.1,2.2,np.hypot(a-6,b-7)))*cream*(h>.4)
    roof=np.sin(np.clip(b/12,0,1)*F(np.pi))
    scarlet=K.ramp(.55*t+.45*roof,['661124','be2c37','f75b48','ffb16c'])
    ivory=K.ramp(.6*t+.4*roof,['8c818b','d4c7bd','f4e9cb'])
    ink=K.ramp(.6*t+.4*roof,['080d19','1e2536','454b5e'])
    col=K.mix(K.mix(ink,scarlet,red),ivory,cream)*(.78+.24*roof)[...,None]
    col=K.mix(col,col*.28,seam*.82)
    col=K.mix(col,col*.35,cuts*.55)
    col=K.mix(col,np.array([1,.96,.83],F),pearl*.75)
    M=5+20*t;R=175+65*t;C=205+45*t
    M,R,C=over(M,R,C,red,20+90*t,20+65*(1-roof)+30*t,16+120*t)
    M,R,C=over(M,R,C,cream,85+130*t,40+95*t,30+155*(1-t))
    M,R,C=over(M,R,C,seam,5,220+25*t,225+25*t)
    M,R,C=over(M,R,C,cuts,15+40*t,155+80*t,150+95*t)
    M,R,C=over(M,R,C,pearl,170+75*t,18+40*t,18+75*t)
    return K.pack(col,M,R,C)

def slt_corn_blotch(seed=42,attempt=1):
    """Outlined rounded angular saddles on distinct checker-backed skin."""
    x,y=K.xy();u,v=K.warp(seed+3901,9,31)
    j=np.floor(v/28).astype(np.int32);u+=(j%2)*F(15)
    i=np.floor(u/30).astype(np.int32);a=K.frac(u/30)*30-15;b=K.frac(v/28)*28-14
    h=K.fhash(i,j,seed+3902);t=K.tiers(h)
    q=((np.abs(a)/(9+1.3*h))**3+(np.abs(b)/(8.5+.7*h))**3)**F(1/3)
    blotch=1-K.sstep(.85,1.03,q)
    outline=K.near(np.abs(q-1.06)*9,1.0)
    rim=K.near(np.abs(q-1.29)*9,.65)
    check=((np.floor(u/8).astype(np.int32)+np.floor(v/8).astype(np.int32))%2).astype(F)
    cut=K.iso(a*.45+b+h*4,8,.75)[0]*(1-outline)
    pore=(1-K.sstep(1,1.8,np.hypot(a-2.5,b+3)))*(h>.38)*blotch
    roof=np.clip(1-q*.55,0,1)
    region=K.unit(K.fbm(seed+3903,(4,12,26),.61))
    orange=K.ramp(.7*region+.3*t,['79402d','c37945','eda965','f4d498'])
    scarlet=K.ramp(.6*region+.4*t,['6b172d','b72f3c','ed6550','f5a171'])
    col=K.mix(orange,orange*.47,check*.40)
    col=K.mix(col,scarlet*(.69+.38*roof)[...,None],blotch)
    col=K.mix(col,np.array([.07,.037,.067],F),outline*.93)
    col=K.mix(col,np.array([.98,.88,.65],F),rim*.78)
    col=K.mix(col,col*.31,cut*.4)
    col=K.mix(col,np.array([.05,.024,.045],F),pore)
    M=35+95*t+45*check;R=50+80*check+35*t;C=30+130*t
    M,R,C=over(M,R,C,blotch,35+85*t,25+65*(1-roof)+25*t,20+100*t)
    M,R,C=over(M,R,C,outline,5,200+45*t,205+40*t)
    M,R,C=over(M,R,C,rim,145+100*t,25+60*t,25+90*t)
    M,R,C=over(M,R,C,cut,15+50*t,155+85*t,160+75*t)
    M,R,C=over(M,R,C,pore,0,235,255)
    return K.pack(col,M,R,C)

def slt_shed_ecdysis(seed=42,attempt=1):
    """Torn translucent membranes and curled dry lips, not living scale domes."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+4001,24,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+4002)[lab];t=K.tiers(h)
    edge=K.edge_distance(lab)
    curl=K.near(np.abs(edge-2.3),.85)
    basal=K.near(edge,.9)
    window=K.sstep(.22,.46,K.noise(seed+4003,210))*K.sstep(2,5,edge)*(h>.32)
    wrinkle=K.iso(v+1.5*np.sin(u*.4+h*4)+u*.25,8,.7)[0]*(1-window)
    intact=1-np.clip(window+basal,0,1)
    region=K.unit(K.fbm(seed+4004,(3,10,28),.59))
    paper=K.ramp(.7*region+.3*t,['777782','b4abb8','ded6cc','f1e9d3'])
    beneath=K.ramp(.65*region+.35*t,['4c5263','7c8190','b9b2ab'])
    col=K.mix(paper,beneath,window*.82)
    col=K.mix(col,np.array([.24,.25,.34],F),basal*.58)
    col=K.mix(col,paper*.55,wrinkle*.55)
    col=K.mix(col,np.array([.94,.94,.86],F),curl*(.35+.45*t))
    col *= (.87+.13*K.sstep(1,8,edge))[...,None]
    M=4+50*t;R=150+85*t;C=165+75*(1-t)
    M,R,C=over(M,R,C,window,2+15*t,190+50*t,210+40*t)
    M,R,C=over(M,R,C,basal,5,225+20*t,230+20*t)
    M,R,C=over(M,R,C,wrinkle,8+35*t,195+45*t,210+30*t)
    M,R,C=over(M,R,C,curl,55+140*t,45+95*t,45+135*t)
    return K.pack(col,M,R,C)

def slt_cobra_hood(seed=42,attempt=1):
    """Splayed shoulder fans stretch wide plates around curved hood ribs."""
    x,y=K.xy();u,v=K.warp(seed+4101,13,27)
    j=np.floor(v/26).astype(np.int32);i=np.floor((u+j.astype(F)*8)/29).astype(np.int32)
    a=K.frac((u+j.astype(F)*8)/29)*29-14.5;b=K.frac(v/26)*26-13
    h=K.fhash(i,j,seed+4102);t=K.tiers(h)
    arch=b+F(.038)*a*a
    rib=K.near(np.abs(arch+4),1.25)
    shoulder=K.near(np.abs(arch-4),.75)
    hinge=K.near(np.abs(arch-10.5),1.0)
    fanphase=a+F(.06)*a*b
    vein=K.iso(fanphase,10,.75)[0]*(1-hinge)
    vein2=K.iso(fanphase+2.2,10,.65)[0]*(1-hinge)
    cut=K.iso(arch+h*4,8,.65)[0]*(1-rib)
    roof=np.clip(1-np.abs(arch)/15,0,1)
    region=K.unit(K.fbm(seed+4103,(4,9,24),.63))
    cobalt=K.ramp(.55*region+.45*t,['153047','346e8b','72b0b2','c3dfc9'])
    bronze=K.ramp(.7*region+.3*t,['604235','aa7d53','e7c087'])
    col=K.mix(cobalt,bronze,K.sstep(-1,3,a))*(.61+.43*roof)[...,None]
    col=K.mix(col,np.array([.91,.96,.84],F),rib*.78)
    col=K.mix(col,np.array([.87,.67,.42],F),shoulder*.86)
    col=K.mix(col,col*.29,np.clip(vein+hinge,0,1)*.78)
    col=K.mix(col,cobalt*.58,vein2*.54)
    col=K.mix(col,col*.47,cut*.43)
    M=55+130*t;R=30+85*(1-roof)+30*t;C=25+130*t
    M,R,C=over(M,R,C,np.clip(vein+hinge,0,1),8+25*t,185+55*t,195+50*t)
    M,R,C=over(M,R,C,vein2,25+75*t,115+105*t,120+100*t)
    M,R,C=over(M,R,C,rib,170+80*t,18+45*t,16+90*t)
    M,R,C=over(M,R,C,shoulder,150+95*t,30+75*t,25+105*t)
    M,R,C=over(M,R,C,cut,20+65*t,140+100*t,150+85*t)
    return K.pack(col,M,R,C)

def slt_wart_tubercle(seed=42,attempt=1):
    """Offset worn wart crowns rise from granular collars and fissured hide."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+4201,17,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+4202)[lab];t=K.tiers(h)
    a,b=K.rot(u,v,h*F(K.TAU));q=np.hypot(a/(7+2*h),b/(5.8+1.5*h))
    if attempt>=2:
        theta=np.arctan2(b,a)
        q+=F(.18)*np.sin(theta*5+h*6)+F(.07)*K.noise(seed+4211,255)
    if attempt>=3:
        q=np.hypot(a/(7+2*h),b/(5.8+1.5*h))+F(.23)*K.noise(seed+4213,300)+F(.07)*np.sin(theta*3+h*8)
    tubercle=1-K.sstep(.90,1.13,q);roof=np.sqrt(np.clip(1-q*q,0,1))
    collar=K.near(np.abs(q-1.10)*7,1.1)
    crown=(1-K.sstep(2.2,3.6,np.hypot(a-1.5,b+1.0)))*tubercle
    if attempt>=2:
        # A2 rejects the smooth lens-like heart. Multiple papillary crowns
        # and lobed rough anatomy distinguish wart hide from Retro Patch glass.
        crown=K.sstep(.58,.83,K.unit(K.noise(seed+4212,255)))*tubercle
    satellite=(1-K.sstep(1.8,3.0,np.hypot(a+5,b-3)))*(h>.55)
    fissure=K.iso(np.arctan2(b,a)*8+q*3,8,.7)[0]*collar
    grain=K.unit(K.noise(seed+4203,230));region=K.unit(K.fbm(seed+4204,(4,11,24),.60))
    hide=K.ramp(.65*region+.35*t,['322a47','745374','b0849d','dfb8b1'])
    col=hide*(.54+.60*roof+.14*grain)[...,None]
    col=K.mix(col,hide*.29,collar*.70)
    col=K.mix(col,K.ramp(t,['875639','c49360','efd5a0']),crown*.85)
    col=K.mix(col,np.array([.70,.75,.86],F),satellite*.66)
    col=K.mix(col,np.array([.07,.043,.09],F),fissure*.84)
    M=25+75*t;R=125+80*(1-roof)+35*t;C=125+105*t
    M,R,C=over(M,R,C,collar,8+20*t,185+50*t,205+40*t)
    M,R,C=over(M,R,C,crown,120+125*t,30+80*t,25+115*t)
    M,R,C=over(M,R,C,satellite,65+135*t,65+110*t,45+150*t)
    M,R,C=over(M,R,C,fissure,5,230,250)
    return K.pack(col,M,R,C)

def slt_diamondback(seed=42,attempt=1):
    """Four-way shield rhombs over a distinct crossed keel field."""
    x,y=K.xy();u,v=K.warp(seed+4301,8,29);a,b=K.rot(u,v,F(.71))
    i=np.floor(a/23).astype(np.int32);j=np.floor(b/23).astype(np.int32)
    p=K.frac(a/23)*23-11.5;q=K.frac(b/23)*23-11.5
    h=K.fhash(i,j,seed+4302);t=K.tiers(h)
    shield=np.maximum(np.abs(p),np.abs(q))
    border=K.near(np.abs(shield-9.2),.85)
    centre=1-K.sstep(8.0,9.5,shield)
    crease=K.near(np.abs(np.abs(p)-np.abs(q)),.75)
    facet=(np.abs(p)>np.abs(q)).astype(F)
    keel=K.iso(np.where(facet>0,p,q)+h*4,8,.85)[0]*centre
    scar=K.iso(p+q*.65+h*5,8,.65)[0]*centre*(h>.32)
    notch=(1-K.sstep(1,2,np.hypot(p-8,q+8)))*(h>.42)
    roof=np.clip(1-shield/14,0,1)
    region=K.unit(K.fbm(seed+4303,(4,13,25),.60))
    base=K.ramp(.7*region+.3*t,['535044','9e9771','d4c49a'])
    dark=K.ramp(.5*region+.5*t,['1c2530','3f4d52','768476'])
    col=K.mix(base,dark,centre)*(.65+.38*roof+.08*facet)[...,None]
    col=K.mix(col,np.array([.93,.85,.63],F),border*.88)
    col=K.mix(col,np.array([.55,.71,.70],F),keel*.67)
    col=K.mix(col,col*.27,np.clip(crease+scar,0,1)*.60)
    col=K.mix(col,np.array([.03,.04,.045],F),notch)
    M=40+95*t;R=65+65*(1-roof)+40*facet;C=35+130*t
    M,R,C=over(M,R,C,centre,20+55*t,110+75*t,110+115*t)
    M,R,C=over(M,R,C,border,145+100*t,25+75*t,25+105*t)
    M,R,C=over(M,R,C,keel,145+105*t,22+65*t,20+115*t)
    M,R,C=over(M,R,C,np.clip(crease+scar,0,1),8+20*t,180+55*t,200+40*t)
    M,R,C=over(M,R,C,notch,0,235,255)
    return K.pack(col,M,R,C)

def slt_anaconda_oval(seed=42,attempt=1):
    """Anisotropic reaction/diffusion forms staggered oval pigment regions."""
    import cv2
    r=K.rng(seed+4401);n=256 if attempt==1 else 512
    A=np.ones((n,n),F);B=np.zeros((n,n),F)
    # Fine nuclei produce emergent unequal ovals; no stamped circle carrier.
    pitch=3 if attempt==1 else 7
    iy,ix=np.mgrid[1:n:pitch,1:n:pitch]
    xx=np.clip(ix+r.integers(-1,2,ix.shape),0,n-1);yy=np.clip(iy+r.integers(-1,2,iy.shape),0,n-1)
    B[yy,xx]=r.uniform(.35,.65,xx.shape);A[yy,xx]=.5
    if attempt>=2:
        B=cv2.dilate(B*F(1.35),np.ones((2,2),np.uint8))
        A[B>0]=F(.55)
    lap=np.array([[.05,.25,.05],[.15,-1,.15],[.05,.25,.05]],F)
    iterations=380 if attempt==1 else 320
    if attempt>=4:
        # SPB-105 a4: keep the same reaction law and 320 integration steps;
        # recycle float32 work buffers rather than allocate every expression.
        ab_buf=np.empty_like(A);la=np.empty_like(A);lb=np.empty_like(A);feed_buf=np.empty_like(A)
    for _ in range(iterations):
        if attempt>=4:
            np.multiply(A,B,out=ab_buf);ab_buf*=B
            cv2.filter2D(A,-1,lap,dst=la,borderType=cv2.BORDER_REFLECT)
            cv2.filter2D(B,-1,lap,dst=lb,borderType=cv2.BORDER_REFLECT)
            np.subtract(1,A,out=feed_buf);feed_buf*=F(.037)
            la*=F(.20);la-=ab_buf;la+=feed_buf;A+=la
            lb*=F(.10);lb+=ab_buf;np.multiply(B,F(.100),out=feed_buf);lb-=feed_buf;B+=lb
            continue
        ab=A*B*B
        A+=F(.20)*cv2.filter2D(A,-1,lap,borderType=cv2.BORDER_REFLECT)-ab+F(.033 if attempt==1 else .037)*(1-A)
        B+=F(.10)*cv2.filter2D(B,-1,lap,borderType=cv2.BORDER_REFLECT)+ab-F(.095 if attempt==1 else .100)*B
    global CHEMISTRY_STATS
    CHEMISTRY_STATS=dict(id='slt_anaconda_oval',attempt=attempt,resolution=n,iterations=iterations,
                         minimum=float(B.min()),maximum=float(B.max()),std=float(B.std()))
    if attempt>=2 and B.std()<.025:raise ValueError('Collapsed Anaconda chemistry: '+str(CHEMISTRY_STATS))
    field=cv2.resize(B,(K.N,K.N),interpolation=cv2.INTER_CUBIC)
    field=K.unit(field)
    oval=K.sstep(.35,.53,field)
    heart=K.sstep(.68,.84,field)
    if attempt>=3:
        heart=K.sstep(.91,.99,field)*K.sstep(.60,.85,K.unit(K.noise(seed+4411,210)))
    gx,gy=K.grad(field);dist=(field-.45)/np.maximum(np.hypot(gx,gy),.015)
    rim=K.near(np.abs(dist),.85)
    x,y=K.xy();crease=K.iso(x+6*K.noise(seed+4402,160)+y*.3,8,.75)[0]
    pores=K.sstep(.88,.98,K.unit(K.noise(seed+4403,240)))*oval
    tier=K.tiers(K.unit(K.noise(seed+4404,120)))
    region=K.unit(K.fbm(seed+4405,(3,11,29),.60))
    emerald=K.ramp(.7*region+.3*tier,['214c37','538d58','9abe77','d5dba5'])
    dark=K.ramp(.6*region+.4*tier,['0c2021','213d36','466657'])
    pale=K.ramp(.65*region+.35*tier,['73896b','b0bd89','deddb0'])
    col=K.mix(emerald,dark,oval)
    col=K.mix(col,pale,heart*.85)
    col=K.mix(col,np.array([.72,.83,.55],F),rim*.75)
    col=K.mix(col,col*.40,crease*(.25+.4*oval))
    col=K.mix(col,np.array([.08,.11,.08],F),pores*.8)
    M=25+80*tier;R=55+65*tier;C=25+120*tier
    M,R,C=over(M,R,C,oval,10+35*tier,145+85*tier,150+85*tier)
    M,R,C=over(M,R,C,heart,70+120*tier,35+85*tier,25+130*tier)
    M,R,C=over(M,R,C,rim,120+110*tier,25+65*tier,25+100*tier)
    M,R,C=over(M,R,C,crease,10+35*tier,165+65*tier,180+55*tier)
    M,R,C=over(M,R,C,pores,5,220,245)
    return K.pack(col,M,R,C)

def slt_albino_translucent(seed=42,attempt=1):
    """Living pigmentless veils overlap a fine rose capillary scaffold."""
    x,y=K.xy();u,v=K.warp(seed+4501,9,34)
    j=np.floor(v/20).astype(np.int32);u+=(j%2)*F(11)
    i=np.floor(u/22).astype(np.int32);a=K.frac(u/22)*22-11;b=K.frac(v/20)*20-10
    h=K.fhash(i,j,seed+4502);t=K.tiers(h)
    q=(a/(8.0+1.1*h))**2+((b+1)/(9.0-1.2*h))**2+.018*a*b
    veil=1-K.sstep(.83,1.07,q)
    lip=K.near(np.abs(q-1.0)*8,.75)
    root=K.near(np.abs(a*.5+b-6),.85)*(1-veil)
    ghost=K.near(np.abs(q-.55)*8,.65)*veil
    cut=K.iso(a*.45+b+h*4,8,.7)[0]*veil
    roof=np.sqrt(np.clip(1-q,0,1))
    region=K.unit(K.fbm(seed+4503,(4,10,26),.61))
    skin=K.ramp(.6*region+.4*t,['9f7c94','c5a1ad','e3c1bc','f3e3cd'])
    ivory=K.ramp(.65*region+.35*t,['b1a7b4','d9d2ce','f0e9d5'])
    col=K.mix(skin,ivory*(.86+.14*roof)[...,None],veil*.86)
    col=K.mix(col,np.array([.62,.32,.42],F),root*.38)
    col=K.mix(col,skin*.66,ghost*.40)
    col=K.mix(col,ivory*.65,cut*.30)
    col=K.mix(col,np.array([.97,.96,.87],F),lip*(.25+.45*t))
    M=5+50*t;R=75+90*(1-roof)+30*t;C=65+145*t
    M,R,C=over(M,R,C,veil,10+65*t,45+85*(1-roof)+30*t,35+130*t)
    M,R,C=over(M,R,C,root,3+12*t,170+65*t,195+50*t)
    M,R,C=over(M,R,C,ghost,8+35*t,125+95*t,130+100*t)
    M,R,C=over(M,R,C,cut,10+30*t,145+80*t,160+65*t)
    M,R,C=over(M,R,C,lip,75+125*t,22+65*t,25+90*t)
    return K.pack(col,M,R,C)
