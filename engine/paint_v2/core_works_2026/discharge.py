"""Independent electrical constructions, not one lightning field recoloured.
SPB-105 / CORE-WORKS 2026-09-30: owner wants intricate 'jaw droppers'.
Attempt records, visual verdicts and M7 movements are in the owned work lane.
"""
import math
import cv2
import numpy as np
from . import kit as K
from .common import over
F = np.float32
N = K.N

def lsk_lichtenberg(seed=42, attempt=1):
    """Dendritic dielectric burn with ash collars and conductive inner paths."""
    r = K.rng(seed + 1201)
    x, y = K.xy()
    core = np.zeros((N,N), np.uint8)
    trunk = np.zeros_like(core)
    tips = np.zeros_like(core)
    paths={2:[],3:[]}; trunks=[]; endpoints=[]
    if attempt>=4:
        # A4 keeps recursive dielectric physics but advances whole frontiers
        # in float32. Each segment remains 8–27px; no large carrier stamp.
        centers=K.sites(seed+2,57,1.0)
        px=np.repeat(centers[:,0],3);py=np.repeat(centers[:,1],3)
        angle=np.repeat(r.uniform(0,K.TAU,len(centers)),3)+np.tile(np.arange(3)*2.094,len(centers))
        angle=angle.astype(F);length=r.uniform(17,27,len(px)).astype(F)
        for depth in range(4,-1,-1):
            points=np.empty((len(px),5,2),F);points[:,0,0]=px;points[:,0,1]=py
            for step in range(1,5):
                angle+=r.normal(0,.25,len(px)).astype(F)
                px=px+np.cos(angle)*length/4;py=py+np.sin(angle)*length/4
                points[:,step,0]=px;points[:,step,1]=py
            q=np.rint(points).astype(np.int32)
            paths[3 if depth>=3 else 2].extend(q)
            if depth>=3:trunks.extend(q)
            if depth:
                origin=r.integers(2,5,(len(px),2));accepted=r.random((len(px),2))<.88
                indexes=np.repeat(np.arange(len(px)),2);sides=np.tile(np.array([-1,1],F),len(px))
                children=points[indexes,origin.ravel()]
                nextangle=np.repeat(angle,2)+sides*r.uniform(.35,.8,len(indexes)).astype(F)
                length=np.repeat(length,2)[accepted.ravel()]*F(.66)
                px=children[:,0][accepted.ravel()];py=children[:,1][accepted.ravel()];angle=nextangle[accepted.ravel()]
            else:endpoints=list(zip(px.astype(int),py.astype(int)))
    # Hundreds of recursively ramified trees; each segment is a fine feature.
    # Attempt 2 interlocks neighbouring coronas and increases tertiary branches.
    pitch = 74 if attempt == 1 else 57
    for cx, cy in ([] if attempt>=4 else K.sites(seed + 2, pitch, 1.0)):
        def grow(px, py, angle, length, depth):
            points = [(px, py)]
            for _ in range(4):
                angle += r.normal(0, .25)
                px += math.cos(angle)*length/4; py += math.sin(angle)*length/4
                points.append((px,py))
            q = np.round(points).astype(np.int32)
            width=2 if depth < 3 else 3
            if attempt>=3:
                paths[width].append(q)
            else:
                cv2.polylines(core, [q], False, 255, width, cv2.LINE_AA)
            if depth >= 3:
                if attempt>=3: trunks.append(q)
                else: cv2.polylines(trunk, [q], False, 255, 2, cv2.LINE_AA)
            if depth:
                for side in (-1,1):
                    if r.random() < .88:
                        sx, sy = points[2 + int(r.integers(0,3))]
                        grow(sx,sy,angle+side*r.uniform(.35,.8),length*.66,depth-1)
            else:
                if attempt>=3: endpoints.append((int(px),int(py)))
                else: cv2.circle(tips,(int(px),int(py)),2,255,-1,cv2.LINE_AA)
        a = r.uniform(0, K.TAU)
        for j in range(3):
            grow(float(cx),float(cy),a+j*2.094,r.uniform(17,27),4)
    if attempt>=3:
        for width,segments in paths.items():
            cv2.polylines(core,segments,False,255,width,cv2.LINE_AA)
        cv2.polylines(trunk,trunks,False,255,2,cv2.LINE_AA)
        # Terminal pinholes are subdued conductors, not square white sparkles.
        for px,py in endpoints: cv2.circle(tips,(px,py),1,180,-1,cv2.LINE_AA)
    d = cv2.distanceTransform(255-core,cv2.DIST_L2,3)
    c = core.astype(F)/255; t = trunk.astype(F)/255
    ash = np.exp(-d*d/F(15.))
    scorch = np.exp(-d/F(8.5))
    lab, _, points = K.voronoi(K.sites(seed + 9, 17, 1.0))
    crystal = K.hash01(np.arange(len(points)),seed+10)[lab]
    body = K.unit(K.fbm(seed+11,(5,11,25,128),.65))
    # Etched dielectric carries amber depth; crystalline cores carry local lilac.
    glass = K.ramp(.65*body+.35*crystal,['130923','382150','815462','db9b65','ffe0a0'])
    glass *= (.64+.4*crystal)[...,None]
    if attempt>=2:
        # A2 eye review: crystal boundaries were competing with the burn forest.
        glass=K.ramp(body,['110b20','392040','80565a','d8a56c'])*(.88+.12*crystal)[...,None]
    char = K.ramp(crystal,['010205','09080c','281a1e'])
    col = K.mix(glass,char,scorch*.89)
    copper = K.ramp(.55*crystal+.45*t,['45171b','bb4925','ef9860','ffd59a'])
    edge = K.near(d-3.6,1.1)*(.55+.45*crystal)
    if attempt>=3:
        edge=K.near(np.abs(d-3.6),1.1)*(.55+.45*crystal)
    col = K.mix(col,copper,edge*.7)
    vein = K.ramp(.4+.6*crystal,['309d9e','73e2cc','eaffca']) if attempt >= 2 else K.ramp(crystal,['7e56a8','cc97ec','fff1ce'])
    col = K.mix(col,vein,c*(.63+.37*t))
    tip = tips.astype(F)/255
    col += tip[...,None]*np.array([.5,.6,.3],F)
    M = 22+85*crystal; R = 28+58*(1-body)+38*crystal; C = 22+94*crystal
    if attempt>=2:
        M=18+35*crystal; R=18+22*(1-body)+12*crystal; C=16+70*crystal
    M,R,C = over(M,R,C,scorch*.86,5+17*crystal,180+65*crystal,205+50*crystal)
    if attempt>=2:
        M,R,C = over(M,R,C,scorch*.92,2+12*crystal,225+30*crystal,220+35*crystal)
    M,R,C = over(M,R,C,edge,190+62*crystal,22+105*crystal,70+150*(1-crystal))
    M,R,C = over(M,R,C,c,165+85*crystal,16+66*(1-crystal),18+190*(1-t))
    M,R,C = over(M,R,C,tip,240,16,16)
    return K.pack(col,M,R,C)

def lsk_return_stroke(seed=42,attempt=1):
    """Stepped continuous channels with independently registered leader forks."""
    x,y=K.xy(); u,v=K.rot(x,y,F(-.36))
    row=np.floor(v/27).astype(np.int32)
    step=np.floor(u/17).astype(np.int32)
    h=K.fhash(step,row,seed+1301); t=K.tiers(h)
    # Piecewise steps, not a sinusoidal neon stripe. Short inclined links
    # connect neighbouring step heights while preserving fine feature scale.
    z=K.frac(u/17)
    h2=K.fhash(step+1,row,seed+1301)
    offset=(h-.5)*10+(h2-h)*10*K.sstep(.70,1,z)
    distance=np.abs(v-(row+.5)*27-offset)
    core=K.near(distance,1.25)
    collar=K.near(np.abs(distance-3.3),1.0)
    fork=K.near(np.abs(v-(row+.5)*27-offset-8*(1-z)),.8)*(h>.52)*K.sstep(.12,.25,z)
    shock=K.near(np.abs(distance-8.2),.7)*(h>.35)
    grain=K.unit(K.noise(seed+1302,160))
    region=K.unit(K.fbm(seed+1303,(4,12,28),.62))
    col=K.ramp(region,['10143e','2c315e','596e9c','b4bfca'])*(.80+.22*grain)[...,None]
    col=K.mix(col,np.array([.02,.015,.04],F),K.near(distance,7)*.60)
    copper=K.ramp(t,['54232f','b44c4d','eea978','ffe7b2'])
    col=K.mix(col,copper,collar*.85)
    col=K.mix(col,np.array([.91,.97,1],F),core)
    col=K.mix(col,np.array([.38,.83,.88],F),fork*.75)
    col=K.mix(col,col*.32,shock)
    tip=K.near(np.hypot((z-.70)*17,distance-6),1.1)*(h>.70)
    col=K.mix(col,np.array([1,.55,.44],F),tip)
    M=12+38*grain; R=32+38*grain; C=22+95*region
    M,R,C=over(M,R,C,K.near(distance,7),5+15*t,165+60*t,185+65*t)
    M,R,C=over(M,R,C,collar,160+85*t,25+100*(1-t),35+125*t)
    M,R,C=over(M,R,C,core,220+30*t,16+32*t,16+45*t)
    M,R,C=over(M,R,C,fork,110+130*t,30+75*(1-t),25+125*t)
    M,R,C=over(M,R,C,shock,8,235,245)
    M,R,C=over(M,R,C,tip,245,16,16)
    return K.pack(col,M,R,C)

def lsk_spider_crawl(seed=42,attempt=1):
    """A lateral hooked braid with crawling fans and copper cross-stitches."""
    x,y=K.xy(); wx,wy=K.warp(seed+1401,15,17)
    row=np.floor(wy/25).astype(np.int32)
    h=K.fhash(row,None,seed+1402)
    phase=wx/F(18.)+h*6
    path=(row+.5)*25+4*np.sin(phase)+2*np.sin(phase*F(.61))
    d=np.abs(wy-path)
    crawl=K.near(d,1.0)
    branch=K.near(np.abs(wy-path-7*np.sin(phase*1.8)-4),.85)*(np.sin(phase*1.8)>.10)
    bridge=K.near(np.abs(K.frac((wx+row*11)/21)*21-10.5),.9)*K.near(d,8)
    cuff=np.exp(-d/F(3.5))
    knot=K.near(np.hypot(K.frac((wx+row*11)/21)*21-10.5,wy-path),2.1)
    dust=K.near(np.abs(np.sin(phase*1.8)),.025)*K.near(np.abs(d-9),.9)
    region=K.unit(K.fbm(seed+1403,(5,9,21),.58)); t=K.tiers(K.fhash(np.floor(wx/21),row,seed+1404))
    base=K.ramp(region,['092636','145761','327e78','9caeb0'])
    col=base*(1-.75*cuff)[...,None]
    copper=K.ramp(t,['503526','a97e44','e2c78a','fff0c8'])
    col=K.mix(col,copper,bridge*.9)
    col=K.mix(col,np.array([.29,.74,.84],F),branch*.85)
    col=K.mix(col,K.ramp(t,['467d91','8ad0cd','e0ffe8']),crawl)
    col=K.mix(col,np.array([.96,.77,.49],F),knot)
    col=K.mix(col,np.array([.74,.77,.83],F),dust*.6)
    M=25+45*region;R=28+35*region;C=16+70*region
    M,R,C=over(M,R,C,cuff,5,175+65*t,200+50*t)
    M,R,C=over(M,R,C,branch,100+140*t,35+70*t,35+125*t)
    M,R,C=over(M,R,C,bridge,160+85*t,25+80*t,22+110*t)
    M,R,C=over(M,R,C,crawl,195+55*t,16+42*t,16+65*t)
    M,R,C=over(M,R,C,knot,240,16+30*t,25+65*t)
    M,R,C=over(M,R,C,dust,25+60*t,115+110*t,175+70*t)
    return K.pack(col,M,R,C)

def lsk_st_elmo(seed=42,attempt=1):
    """Fine pointed electrodes carry brush-shaped corona, not circular halos."""
    if attempt>=2:
        return _st_elmo_facet_forest(seed,attempt)
    x,y=K.xy();u,v=K.warp(seed+1501,7,24)
    j=np.floor(v/27).astype(np.int32);i=np.floor((u+(j%2)*12)/25).astype(np.int32)
    a=K.frac((u+(j%2)*12)/25)*25-12.5;b=K.frac(v/27)*27-13.5
    h=K.fhash(i,j,seed+1502);t=K.tiers(h)
    cone=K.smooth(np.abs(a)-np.maximum(0,(b+6)*.21),1)*(1-K.sstep(4,6,b))*K.sstep(-7,-5,b)
    skirt=K.smooth(np.abs(a)-np.maximum(0,(6-b)*.45),1)*K.sstep(-12,-10,b)*(1-K.sstep(4,6,b))
    rib=K.iso(a/(np.maximum(2,(6-b)))*18,8,.9)[0]*skirt*(1-cone)
    collar=K.near(np.hypot(a,b-5)-4.2,.7)*(b>3)
    root=K.near(np.hypot(a,b-6),2.3)
    region=K.unit(K.fbm(seed+1503,(3,10,23),.57));grain=K.unit(K.noise(seed+1504,180))
    col=K.ramp(region,['190c35','3e2468','7556a8','b27fac'])*(.80+.25*grain)[...,None]
    col=K.mix(col,K.ramp(.6*h+.4*region,['252767','626ed0','9cd6ef']),skirt*.58)
    col=K.mix(col,np.array([.31,.8,1],F),rib*.85)
    col=K.mix(col,K.ramp(t,['365361','8dbfce','dcece9']),cone)
    col=K.mix(col,np.array([.93,.54,.24],F),collar)
    col=K.mix(col,np.array([.04,.028,.09],F),root)
    M=20+45*grain;R=30+50*grain;C=20+100*region
    M,R,C=over(M,R,C,skirt,60+110*t,45+75*(1-t),25+145*t)
    M,R,C=over(M,R,C,rib,150+90*t,18+55*t,16+90*t)
    M,R,C=over(M,R,C,cone,200+45*t,18+38*t,16+65*t)
    M,R,C=over(M,R,C,collar,145+95*t,35+85*t,55+130*(1-t))
    M,R,C=over(M,R,C,root,5,230,250)
    return K.pack(col,M,R,C)

def lsk_plasma_globe(seed=42,attempt=1):
    """Chamber-clipped curved plasma filaments inside convex glass lenses."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+1601,29,1.0))
    u,v=K.cell_local(lab,pts,x,y);theta=np.arctan2(v,u)
    h=K.hash01(np.arange(len(pts)),seed+1602)[lab];t=K.tiers(h)
    edged=K.edge_distance(lab)
    face=K.sstep(0,3,edged)
    filament=K.near(np.abs(np.sin(theta*3+h*6+d*.21))*np.maximum(3,d/3),.65)*face
    ruling=K.iso(d+2*np.sin(theta*2+h*6),9,.8)[0]*face
    nucleus=1-K.sstep(1.3,3,d)
    rim=K.near(edged,1.2)
    contact=rim*K.sstep(.7,.95,np.cos(theta*3+h*6+d*.21))
    region=K.unit(K.fbm(seed+1603,(4,11,25),.60));grain=K.unit(K.noise(seed+1604,170))
    glass=K.ramp(.65*region+.35*h,['190e35','663568','b46099','e5aaaf'])
    roof=np.clip(1-d/19,0,1)
    col=glass*(.50+.5*roof+.15*np.cos(theta-1))[...,None]
    col=K.mix(col,glass*.2,rim*.8)
    col=K.mix(col,np.array([.95,.35,.76],F),filament*.87)
    col=K.mix(col,glass*.35,ruling*.33)
    col=K.mix(col,np.array([1,.85,.71],F),contact)
    col=K.mix(col,np.array([.77,.97,1],F),nucleus)
    col *= (.93+.10*grain)[...,None]
    M=30+65*t;R=22+60*(1-roof);C=16+110*t
    M,R,C=over(M,R,C,rim,5,210+35*t,220+35*t)
    M,R,C=over(M,R,C,ruling,15+70*t,125+80*t,135+105*t)
    M,R,C=over(M,R,C,filament,150+95*t,22+65*t,25+95*t)
    M,R,C=over(M,R,C,contact,205+40*t,18+35*t,16+50*t)
    M,R,C=over(M,R,C,nucleus,245,16,16)
    return K.pack(col,M,R,C)

def lsk_jacobs_ladder(seed=42,attempt=1):
    """Continuous paired rails with independent rising arcs and heat slots."""
    x,y=K.xy();a,b=K.rot(x,y,F(.27));a+=3*K.noise(seed+1701,24)
    i=np.floor(a/29).astype(np.int32);u=K.frac(a/29)*29
    j=np.floor(b/22).astype(np.int32);v=K.frac(b/22)*22
    h=K.fhash(i,j,seed+1702);t=K.tiers(h)
    rail=K.near(np.minimum(np.abs(u-4),np.abs(u-25)),1.3)
    arch=7+F(.043)*(u-14.5)**2+h*3
    rung=K.near(np.abs(v-arch),1.0)*K.sstep(3,5,u)*(1-K.sstep(24,26,u))
    shoe=rail*K.near(np.abs(v-arch),2.4)
    heat=K.near(np.abs(v-arch-2.7),1.0)*(1-rail)
    mark=K.near(np.abs(v-17),.7)*K.near(np.abs(u-10),2.7)
    region=K.unit(K.fbm(seed+1703,(5,13,27),.58));grain=K.iso(b+2*K.noise(seed+1704,150),8,.6)[0]
    col=K.ramp(region,['10261f','284c39','658569','c4c99e'])*(.88+.12*grain)[...,None]
    col=K.mix(col,col*.27,heat)
    col=K.mix(col,K.ramp(t,['6b3424','ca7546','f7c979']),rail)
    col=K.mix(col,np.array([.56,.92,.91],F),rung)
    col=K.mix(col,np.array([1,.96,.78],F),shoe)
    col=K.mix(col,np.array([.09,.19,.12],F),mark)
    M=10+30*region;R=28+70*grain;C=25+110*region
    M,R,C=over(M,R,C,heat,15+30*t,190+55*t,205+45*t)
    M,R,C=over(M,R,C,rail,170+80*t,28+85*t,30+140*t)
    M,R,C=over(M,R,C,rung,120+120*t,22+75*(1-t),22+125*t)
    M,R,C=over(M,R,C,shoe,225+25*t,16+30*t,16+55*t)
    M,R,C=over(M,R,C,mark,5,225,245)
    return K.pack(col,M,R,C)

def lsk_arc_weld(seed=42,attempt=1):
    """Stack-of-dimes molten tracks, not reptile scales or crater dots."""
    x,y=K.xy();u,v=K.warp(seed+1801,9,19);u,v=K.rot(u,v,F(-.42))
    j=np.floor(v/25).astype(np.int32);i=np.floor((u+j*7)/19).astype(np.int32)
    a=K.frac((u+j*7)/19)*19-9.5;b=K.frac(v/25)*25-12.5
    h=K.fhash(i,j,seed+1802);t=K.tiers(h)
    dome=np.sqrt((a+2)**2+(b*.84)**2)
    bead=1-K.sstep(9.0,11.8,dome)
    crescent=K.near(np.abs(np.hypot(a-3,b*.82)-9),.85)*bead
    ripple=K.iso(np.hypot(a+3,b*.8),8,.8)[0]*bead
    root=K.near(np.abs(b)-11.5,1.0)
    if attempt>=2:
        root=K.near(np.abs(np.abs(b)-11.5),.85)
    pore=1-K.sstep(1,2,np.hypot(a-3.5,b+h*3))
    spatter=K.sstep(.88,.97,K.fhash(np.floor(u/8),np.floor(v/8),seed+1803))*(1-bead)
    region=K.unit(K.fbm(seed+1804,(3,9,21),.60));roof=np.clip(1-dome/13,0,1)
    oxide=K.thin_film(.50*region+.15*h+.13*dome/12,.82,.65)
    if attempt>=2:
        # Cooled puddles retain coherent heat-colour families along a track.
        family=K.ramp(region,['244059','3e7390','618e83','ae9470','e9bc88'])
        oxide=K.mix(family,oxide,.24)
    col=K.mix(K.ramp(region,['212f41','4d626c','939c98']),oxide,bead)
    col *= (.65+.45*roof)[...,None]
    col=K.mix(col,np.array([.035,.045,.065],F),root*.8)
    col=K.mix(col,oxide*.28,ripple*.65)
    col=K.mix(col,np.array([.90,.92,.84],F),crescent*.8)
    col=K.mix(col,np.array([.04,.027,.045],F),pore)
    col=K.mix(col,np.array([.94,.70,.41],F),spatter*.75)
    M=150+85*t;R=65+90*(1-roof);C=30+120*t
    M,R,C=over(M,R,C,bead,175+70*t,24+70*(1-roof)+30*t,20+120*t)
    M,R,C=over(M,R,C,ripple,45+90*t,140+90*t,155+85*t)
    M,R,C=over(M,R,C,root,8+25*t,200+40*t,225+25*t)
    M,R,C=over(M,R,C,crescent,220+30*t,18+38*t,16+70*t)
    M,R,C=over(M,R,C,pore,5,235,250)
    M,R,C=over(M,R,C,spatter,200+50*t,25+50*t,25+110*t)
    return K.pack(col,M,R,C)

def lsk_sprite(seed=42,attempt=1):
    """Upper electrical caps feed several descending filament columns."""
    x,y=K.xy();u,v=K.warp(seed+1901,7,21)
    j=np.floor(v/31).astype(np.int32);i=np.floor((u+(j%2)*13)/28).astype(np.int32)
    a=K.frac((u+(j%2)*13)/28)*28-14;b=K.frac(v/31)*31-15.5
    h=K.fhash(i,j,seed+1902);t=K.tiers(h)
    capd=np.sqrt((a*.88)**2+((b+7)*1.7)**2)
    cap=1-K.sstep(9,11,capd)
    trench=K.near(np.abs(capd-8),.8)*cap
    phase=a+1.8*np.sin(b*.45+h*6)
    column=K.iso(phase,8,1.15)[0]*K.sstep(-7,-4,b)*(1-K.sstep(11,14,b))*K.sstep(12,3,np.abs(a))
    segment=column*K.sstep(.50,.67,K.frac((b+h*4)/8))
    mist=K.near(np.abs(b-12),1.5)*K.iso(phase,8,1.5)[0]
    region=K.unit(K.fbm(seed+1903,(5,10,29),.64));dust=K.unit(K.noise(seed+1904,190))
    col=K.ramp(region,['291735','594a6c','92718d','cfaca9'])*(.85+.15*dust)[...,None]
    col=K.mix(col,K.ramp(t,['62242f','bd4b57','edaf82']),cap*.87)
    col=K.mix(col,np.array([.14,.045,.13],F),trench)
    col=K.mix(col,K.ramp(.6*t+.4*region,['39549a','9698df','f2cfec']),column)
    col=K.mix(col,np.array([.86,.91,1],F),segment*.65)
    col=K.mix(col,np.array([.99,.71,.60],F),mist*.78)
    M=15+50*dust;R=35+60*dust;C=25+100*region
    M,R,C=over(M,R,C,cap,100+125*t,45+105*(1-t),30+140*t)
    M,R,C=over(M,R,C,trench,8,225,245)
    M,R,C=over(M,R,C,column,145+95*t,22+70*t,30+130*t)
    M,R,C=over(M,R,C,segment,215+35*t,18+35*t,20+60*t)
    M,R,C=over(M,R,C,mist,80+150*t,40+100*t,65+140*t)
    return K.pack(col,M,R,C)

def lsk_static_creep(seed=42,attempt=1):
    """Doubled creeping conductor on a fine percolation maze."""
    x,y=K.xy();field=K.noise(seed+2001,145)+F(.30)*K.noise(seed+2002,255)
    gx,gy=K.grad(field);slope=np.maximum(np.hypot(gx,gy),.018)
    d=field/slope
    track=K.near(np.abs(d),1.1)
    paired=K.near(np.abs(d-3.4),.65)
    frost=K.near(np.abs(d+3.8),1.3)
    island=K.sstep(-1,1,d)
    pin=K.sstep(.86,.96,K.unit(K.noise(seed+2003,210)))*K.near(np.abs(d),3.0)
    junction=K.sstep(.015,.004,slope)*K.near(np.abs(d),5)
    region=K.unit(K.fbm(seed+2004,(4,12,22),.56));tone=K.tiers(K.unit(field))
    col=K.ramp(.8*region+.2*K.unit(field),['092d3e','196375','54929b','c4c9ad'])
    col *= (.78+.25*island)[...,None]
    col=K.mix(col,np.array([.075,.15,.18],F),frost*.65)
    col=K.mix(col,K.ramp(tone,['442340','8e4787','dc8eb2','ffe1c1']),paired)
    col=K.mix(col,np.array([.90,.96,.89],F),track*.9)
    col=K.mix(col,np.array([.97,.52,.23],F),junction*.8)
    col=K.mix(col,np.array([.87,.82,.95],F),pin)
    hair=None
    if attempt>=2:
        # Insulating islands carry charge-aligned fine etching. This is
        # clipped to their actual substrate, not a decorative spec overlay.
        direction=x+35*K.noise(seed+2011,65)+8*K.noise(seed+2012,160)
        hair=K.iso(direction,8,.75)[0]*(1-K.near(np.abs(d),2.4))
        col=K.mix(col,K.ramp(tone,['173f54','36778a','9cc7c9']),hair*.55)
    M=25+70*tone;R=30+35*tone+20*island;C=16+120*region
    M,R,C=over(M,R,C,frost,12+18*tone,165+65*tone,185+55*tone)
    M,R,C=over(M,R,C,paired,115+125*tone,45+85*tone,45+165*tone)
    M,R,C=over(M,R,C,track,185+65*tone,18+38*tone,16+70*tone)
    M,R,C=over(M,R,C,junction,150+95*tone,40+90*tone,35+155*tone)
    M,R,C=over(M,R,C,pin,240,16,16)
    if hair is not None:
        M,R,C=over(M,R,C,hair,30+90*tone,115+100*tone,110+130*tone)
    return K.pack(col,M,R,C)

def lsk_carbon_track(seed=42,attempt=1):
    """Carbon-contaminant ropes with fused shoulders in porcelain."""
    x,y=K.xy();u,v=K.rot(x,y,F(.44))
    v+=5*K.noise(seed+2101,53)+2*K.noise(seed+2102,170)
    j=np.floor(v/19).astype(np.int32);local=v-(j+.5)*19
    h=K.fhash(np.floor(u/13),j,seed+2103);t=K.tiers(h)
    wav=2.5*np.sin(u/11+j*.7)+2*K.noise(seed+2104,190)
    width=1.3+2.5*h;d=np.abs(local-wav)
    rope=K.smooth(d-width,1)
    shoulder=K.near(np.abs(d-width-1.7),.75)
    fibre=K.iso(local+wav*.4,8,.8)[0]*rope
    bridge=K.near(np.abs(K.frac((u+j*8)/23)*23-11),1.1)*K.near(d,7)*(h>.5)
    pore=(1-K.sstep(1.1,2.0,np.hypot(K.frac(u/13)*13-6.5,local-wav)))*(h>.62)
    grain=K.unit(K.noise(seed+2105,210));region=K.unit(K.fbm(seed+2106,(4,10,23),.58))
    porcelain=K.ramp(.75*region+.25*grain,['365a57','83aea1','ced8b8','f3edd5'])
    col=porcelain*(.87+.15*grain)[...,None]
    carbon=K.ramp(t,['030a0e','112026','273f46','4e6867'])
    col=K.mix(col,carbon,rope)
    col=K.mix(col,K.ramp(t,['337b82','86d1c4','d6f4d0']),shoulder)
    col=K.mix(col,carbon*.30,fibre*.70)
    col=K.mix(col,np.array([.85,.50,.26],F),bridge*.78)
    col=K.mix(col,np.array([.018,.008,.025],F),pore)
    M=20+75*grain;R=65+70*grain;C=25+100*region
    M,R,C=over(M,R,C,rope,2+15*t,175+65*t,210+40*t)
    M,R,C=over(M,R,C,shoulder,15+65*t,18+52*t,16+60*t)
    M,R,C=over(M,R,C,fibre,4,235,250)
    M,R,C=over(M,R,C,bridge,150+100*t,38+100*t,60+130*t)
    M,R,C=over(M,R,C,pore,0,245,255)
    return K.pack(col,M,R,C)

def lsk_bead(seed=42,attempt=1):
    """Unequal decaying droplets follow a broken, wandering discharge channel."""
    x,y=K.xy();u,v=K.warp(seed+2201,11,28);u,v=K.rot(u,v,F(-.55))
    j=np.floor(v/23).astype(np.int32);shift=K.fhash(j,None,seed+2202)*19
    i=np.floor((u+shift)/19).astype(np.int32);a=K.frac((u+shift)/19)*19-9.5
    b=v-(j+.5)*23-3*np.sin(u/17+j*.8)
    h=K.fhash(i,j,seed+2203);t=K.tiers(h)
    q=np.sqrt((a/(6.0+2.3*h))**2+(b/(2.2+2.4*h))**2)
    bead=1-K.sstep(.85,1.12,q)
    rim=K.near(np.abs(q-1)*(3+2*h),.65)
    head=bead*K.sstep(-1,3,a)
    tail=bead*(1-head)*K.sstep(-9,-6,a)
    neck=K.near(np.abs(b),1.3)*(1-bead)
    hair=K.near(np.abs(b-4*np.sin(a*.55+h*4)),.7)*(1-bead)*(h>.5)
    region=K.unit(K.fbm(seed+2204,(4,13,26),.60));grain=K.unit(K.noise(seed+2205,200))
    col=K.ramp(region,['231144','593865','a0758e','e3b9ad'])*(.83+.19*grain)[...,None]
    col=K.mix(col,np.array([.035,.028,.07],F),neck*.75)
    surface=K.ramp(t,['3f6395','709dc1','bcdce2','fff0c5'])*(.60+.5*np.clip(1-q,0,1))[...,None]
    col=K.mix(col,surface,bead)
    col=K.mix(col,K.ramp(t,['77324d','c46b71','f7c699']),tail*.75)
    col=K.mix(col,np.array([.97,.97,.87],F),head*.55)
    col=K.mix(col,np.array([.52,.80,.91],F),rim*.6)
    col=K.mix(col,np.array([.85,.49,.72],F),hair*.6)
    M=15+40*grain;R=35+45*grain;C=18+110*region
    M,R,C=over(M,R,C,neck,8,210+35*t,220+25*t)
    M,R,C=over(M,R,C,bead,120+110*t,25+85*q,25+125*t)
    M,R,C=over(M,R,C,tail,160+85*t,45+100*t,65+130*t)
    M,R,C=over(M,R,C,head,195+55*t,16+35*t,16+65*t)
    M,R,C=over(M,R,C,rim,210+40*t,20+50*t,20+65*t)
    M,R,C=over(M,R,C,hair,50+120*t,85+110*t,105+125*t)
    return K.pack(col,M,R,C)

def lsk_streamer_front(seed=42,attempt=1):
    """Advancing bent comb fronts with unequal precursor hooks."""
    x,y=K.xy();u,v=K.warp(seed+2301,11,23);u,v=K.rot(u,v,F(.73))
    j=np.floor(v/29).astype(np.int32);i=np.floor((u+j*9)/28).astype(np.int32)
    a=K.frac((u+j*9)/28)*28;b=K.frac(v/29)*29
    h=K.fhash(i,j,seed+2302);t=K.tiers(h)
    leading=9+3*np.sin(a/8+h*6)+a*.18
    d=b-leading
    skirt=K.sstep(-1,2,d)*(1-K.sstep(10,14,d))
    front=K.near(np.abs(d),1.1)
    comb=K.iso(a+2.5*np.sin(d*.35+h*6),8,1.1)[0]*skirt
    hook=K.near(np.abs(d+4.5*np.sin(a*.35+h*3)+3),.85)*(d<0)*(h>.3)
    trench=K.near(np.abs(d-11),1.1)
    tip=K.near(np.abs(d-2),1.4)*K.iso(a+h*8,9,1.3)[0]
    region=K.unit(K.fbm(seed+2303,(4,9,27),.63));grain=K.unit(K.noise(seed+2304,185))
    base=K.ramp(region,['462341','8b4b5c','cb916c','f1d99b'])
    col=base*(.83+.15*grain)[...,None]
    field=K.ramp(.6*region+.4*t,['245561','488a8d','93d8c4','edf7c0'])
    col=K.mix(col,field,skirt*.70)
    col=K.mix(col,field*.23,trench*.9)
    col=K.mix(col,np.array([.94,.97,.87],F),comb*.8)
    col=K.mix(col,np.array([.89,.41,.30],F),hook*.9)
    col=K.mix(col,np.array([.96,.83,.51],F),front)
    col=K.mix(col,np.array([.68,.91,1],F),tip*.85)
    M=25+75*grain;R=40+35*grain;C=22+95*region
    M,R,C=over(M,R,C,skirt,70+100*t,45+65*t,25+115*t)
    M,R,C=over(M,R,C,trench,5,225,250)
    M,R,C=over(M,R,C,comb,150+95*t,25+65*t,25+100*t)
    M,R,C=over(M,R,C,hook,135+110*t,40+100*t,55+140*t)
    M,R,C=over(M,R,C,front,185+65*t,18+45*t,16+75*t)
    M,R,C=over(M,R,C,tip,225+25*t,16+30*t,16+55*t)
    return K.pack(col,M,R,C)

def lsk_fulgurite(seed=42,attempt=1):
    """Hollow glass tube lace fused around fine sintered sand grains."""
    x,y=K.xy();field=15*K.noise(seed+2401,105)+6*K.noise(seed+2402,185)
    bore,level,phase=K.iso(field,10,3.0)
    wall=1-bore;roof=np.sin(np.pi*phase)**2
    stria=K.iso(field+2.4*K.noise(seed+2403,250),10,.7)[0]*wall
    lab,d,pts=K.voronoi(K.sites(seed+2404,10,1.0))
    h=K.hash01(np.arange(len(pts)),seed+2405)[lab];t=K.tiers(h)
    granule=(1-K.sstep(2.2,4.2,d))*wall
    bubble=(1-K.sstep(.9,1.9,d))*(h>.77)*wall
    fusion=K.near(np.abs(d-3),.65)*wall
    region=K.unit(K.fbm(seed+2406,(3,11,29),.60))
    glass=K.ramp(.65*region+.35*roof,['3b251b','956234','d0a352','f7ddaa'])
    glass *= (.66+.44*roof)[...,None]
    col=K.mix(glass,np.array([.08,.052,.065],F),bore*.85)
    sand=K.ramp(t,['5c4754','a58e81','e2d9b0','f9f1d2'])
    col=K.mix(col,sand,granule*.8)
    col=K.mix(col,np.array([.42,.60,.64],F),fusion*.50)
    col=K.mix(col,glass*.26,stria*.8)
    col=K.mix(col,np.array([.88,.96,.86],F),bubble*.85)
    M=15+45*t;R=20+50*(1-roof);C=16+75*region
    M,R,C=over(M,R,C,bore,0,220+30*t,230+25*t)
    M,R,C=over(M,R,C,granule,35+100*t,110+115*t,160+85*t)
    M,R,C=over(M,R,C,fusion,70+95*t,45+90*t,35+125*t)
    M,R,C=over(M,R,C,stria,10+30*t,145+85*t,160+75*t)
    M,R,C=over(M,R,C,bubble,100+110*t,18+50*t,18+65*t)
    return K.pack(col,M,R,C)

def lsk_spark_gap(seed=42,attempt=1):
    """Opposed fine contacts, open ceramic gaps and unequal arc bridges."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+2501,29 if attempt==1 else 16,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+2502)[lab];t=K.tiers(h)
    a,b=K.rot(u,v,h*F(np.pi))
    contact=K.smooth(np.maximum(np.abs(b)-(2.5+2*h),np.abs(np.abs(a)-7)-3),1)
    shoulder=K.near(np.abs(np.abs(a)-10.5),.85)*K.near(np.abs(b),6)
    arc=K.near(np.abs(b-1.7*np.sin(a*.8+h*5)),.65)*(1-contact)*K.near(np.abs(a),7)
    pit=1-K.sstep(1.1,2.2,np.hypot(np.abs(a)-3.8,b))
    guard=K.near(np.abs(np.hypot(a*.82,b)-11),.8)*(1-contact)
    ruling=K.iso(a-b*.2,8,.7)[0]*contact
    region=K.unit(K.fbm(seed+2503,(4,12,24),.58));grain=K.unit(K.noise(seed+2504,180))
    base=K.ramp(region,['4b252b','99513e','d88859','f4c398'])
    col=base*(.82+.18*grain)[...,None]
    col=K.mix(col,K.ramp(t,['334e64','719ca5','cde2d6']),contact)
    col=K.mix(col,np.array([.86,.43,.20],F),shoulder*.85)
    col=K.mix(col,np.array([.95,.97,.85],F),arc)
    col=K.mix(col,np.array([.055,.035,.07],F),guard*.8)
    col=K.mix(col,col*.28,ruling*.6)
    col=K.mix(col,np.array([.025,.017,.032],F),pit)
    M=15+40*grain;R=75+50*grain;C=80+120*region
    M,R,C=over(M,R,C,contact,180+70*t,24+75*t,25+120*t)
    M,R,C=over(M,R,C,shoulder,125+115*t,45+95*t,45+155*t)
    M,R,C=over(M,R,C,guard,5,215+35*t,230+20*t)
    M,R,C=over(M,R,C,ruling,70+110*t,145+75*t,125+95*t)
    M,R,C=over(M,R,C,arc,210+40*t,16+35*t,16+50*t)
    M,R,C=over(M,R,C,pit,0,235,255)
    return K.pack(col,M,R,C)

def lsk_tesla_streamer(seed=42,attempt=1):
    """Individual winding coils with insulation breaks, feed vias and hooks."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+2601,27 if attempt==1 else 16,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+2602)[lab];t=K.tiers(h)
    theta=np.arctan2(v,u);hand=np.where(h>.5,1.,-1.).astype(F)
    phase=d+hand*theta*F(2.1)+h*4
    coil=K.iso(phase,8,1.2)[0]*K.sstep(1.5,3,d)*(1-K.sstep(11,14,d))
    window=K.sstep(.25,.5,np.cos(theta-h*6))*(1-K.sstep(12,15,d))
    insulated=coil*(1-window);exposed=coil*window
    hook=K.near(np.abs(d-11-2.1*np.sin(theta*2+h*6)),.8)*K.sstep(.25,.65,np.cos(theta-h*6))
    via=1-K.sstep(1.4,2.8,d)
    tip=K.near(np.hypot(u-12*np.cos(h*6),v-12*np.sin(h*6)),1.2)
    region=K.unit(K.fbm(seed+2603,(4,10,25),.59));grain=K.unit(K.noise(seed+2604,210))
    col=K.ramp(region,['321326','76304d','af676f','e4aaa0'])*(.85+.15*grain)[...,None]
    col=K.mix(col,np.array([.035,.027,.065],F),insulated*.8)
    col=K.mix(col,K.ramp(t,['763b35','c17650','f6d198']),exposed)
    col=K.mix(col,np.array([.58,.81,.90],F),hook*.85)
    col=K.mix(col,np.array([.94,.98,.84],F),via)
    col=K.mix(col,np.array([1,.71,.51],F),tip)
    M=20+50*grain;R=35+45*grain;C=22+115*region
    M,R,C=over(M,R,C,insulated,5,195+45*t,205+45*t)
    M,R,C=over(M,R,C,exposed,155+95*t,30+90*t,30+140*t)
    M,R,C=over(M,R,C,hook,140+110*t,22+70*t,22+120*t)
    M,R,C=over(M,R,C,via,225+25*t,16+35*t,16+65*t)
    M,R,C=over(M,R,C,tip,240,16,16)
    return K.pack(col,M,R,C)

def lsk_corona_ring(seed=42,attempt=1):
    """Irregular oval guards with seated torus roots and short corona fringe."""
    x,y=K.xy();lab,d,pts=K.voronoi(K.sites(seed+2701,27 if attempt==1 else 17,1.0))
    u,v=K.cell_local(lab,pts,x,y);h=K.hash01(np.arange(len(pts)),seed+2702)[lab];t=K.tiers(h)
    a,b=K.rot(u,v,h*F(K.TAU));theta=np.arctan2(b,a)
    er=np.sqrt((a*.88)**2+(b*1.15)**2)+.7*np.sin(theta*3+h*5)
    radius=7.5+3*h
    ring=K.near(np.abs(er-radius),1.5)
    seat=K.near(np.abs(er-radius),3.8)*(1-ring)
    fringe=K.iso(theta*radius+er*.6,8,.9)[0]*K.sstep(radius+1,radius+2,er)*(1-K.sstep(radius+5,radius+7,er))
    aperture=1-K.sstep(2.2,3.7,er)
    ruling=K.iso(theta*radius,8,.65)[0]*ring
    region=K.unit(K.fbm(seed+2703,(3,9,27),.63));grain=K.unit(K.noise(seed+2704,190))
    col=K.ramp(region,['123948','286e7d','74b7b8','bfe6cc'])*(.86+.14*grain)[...,None]
    col=K.mix(col,np.array([.045,.055,.11],F),seat*.9)
    col=K.mix(col,K.ramp(t,['623b40','af754f','f2c896']),ring)
    col=K.mix(col,np.array([.82,.87,1],F),fringe*.8)
    col=K.mix(col,np.array([.31,.65,.70],F),aperture*.5)
    col=K.mix(col,col*.27,ruling*.8)
    M=20+55*grain;R=40+50*grain;C=20+100*region
    M,R,C=over(M,R,C,seat,8,190+55*t,200+45*t)
    M,R,C=over(M,R,C,ring,150+95*t,28+75*t,25+115*t)
    M,R,C=over(M,R,C,fringe,115+125*t,35+85*t,45+130*t)
    M,R,C=over(M,R,C,aperture,10+30*t,65+70*t,40+120*t)
    M,R,C=over(M,R,C,ruling,30+70*t,160+65*t,170+70*t)
    return K.pack(col,M,R,C)

def _st_elmo_facet_forest(seed,attempt):
    """Point discharge rooted in a complete fine faceted electrode surface.

    A2 rejects little brush icons on flat enamel. Every sharp facet owns its
    apex fan, seated root, copper guard and local pearl/metal tiers.
    """
    points=K.sites(seed+1511,17,.95)
    subdiv=cv2.Subdiv2D((0,0,N,N))
    for px,py in points:
        subdiv.insert((float(px),float(py)))
    tris=subdiv.getTriangleList().reshape(-1,3,2)
    tris=tris[np.all((tris>=0)&(tris<N),axis=(1,2))]
    ids=np.zeros((N,N),np.int32);edges=np.zeros((N,N),np.uint8)
    brush=np.zeros((N,N),np.uint8);tips=np.zeros_like(brush)
    r=K.rng(seed+1512);paths=[]
    if attempt>=3:
        integer_tris=np.rint(tris).astype(np.int32)
        active=tris[::2];centers=active.mean(1)
        apex=active[np.arange(len(active)),r.integers(0,3,len(active))]
        direction=apex-centers;direction/=np.maximum(np.linalg.norm(direction,axis=1),.1)[:,None]
        normal=np.stack((-direction[:,1],direction[:,0]),axis=1)
        lens=r.uniform(7,12,(len(active),3)).astype(F);skew=np.array([-.52,0,.52],F)[None,:]
        start=np.broadcast_to(apex[:,None,:],(len(active),3,2))
        middle=start+direction[:,None,:]*lens[...,None]*F(.48)+normal[:,None,:]*(lens*skew)[...,None]*F(.22)
        end=start+direction[:,None,:]*lens[...,None]+normal[:,None,:]*(lens*skew)[...,None]
        paths=list(np.rint(np.stack((start,middle,end),axis=2)*16).astype(np.int32).reshape(-1,3,2))
        for point in np.rint(apex*16).astype(int):cv2.circle(tips,tuple(point),16,200,-1,cv2.LINE_AA,4)
    for index,tri in enumerate(tris):
        p=integer_tris[index] if attempt>=3 else np.round(tri).astype(np.int32)
        cv2.fillConvexPoly(ids,p,index+1)
        if index%2==0 and attempt<3:
            centre=tri.mean(0);apex=tri[int(r.integers(0,3))]
            direction=apex-centre;direction/=max(float(np.hypot(*direction)),.1)
            normal=np.array([-direction[1],direction[0]],F)
            for skew in (-.52,0,.52):
                length=r.uniform(7,12)
                end=apex+direction*length+normal*skew*length
                mid=apex+direction*length*.48+normal*skew*length*.22
                paths.append(np.round(np.array([apex,mid,end])*16).astype(np.int32))
            cv2.circle(tips,tuple(np.round(apex*16).astype(int)),16,200,-1,cv2.LINE_AA,4)
    edgepaths=list(np.rint(tris*16).astype(np.int32))
    cv2.polylines(edges,edgepaths,True,255,1,cv2.LINE_AA,4)
    cv2.polylines(brush,paths,False,255,1,cv2.LINE_AA,4)
    h=K.hash01(np.arange(len(tris)+1),seed+1513)[ids];tier=K.tiers(h)
    angles=K.hash01(np.arange(len(tris)+1),seed+1514)[ids]*F(K.TAU)
    x,y=K.xy();region=K.unit(K.fbm(seed+1515,(3,9,25),.59))
    ripple=K.iso(x*np.cos(angles)+y*np.sin(angles),9,.65)[0]
    # Per-facet polished planes cover the canvas; fine etching is facet-owned.
    enamel=K.ramp(.65*region+.35*tier,['211637','4d367b','a965b0','eaaabb'])
    metal=K.ramp(.55*region+.45*tier,['183746','327f98','69cbb9','d6f5ce'])
    cone=(h>.47).astype(F)
    col=K.mix(enamel,metal,cone)*(.78+.22*np.sin(angles+x*.025+y*.03))[...,None]
    ef=edges.astype(F)/255;bf=brush.astype(F)/255;tip=tips.astype(F)/255
    cuff=K.blur(bf,1.5)
    col=K.mix(col,col*.26,ef*.83)
    col=K.mix(col,col*.48,ripple*.25)
    guard=K.near(cv2.distanceTransform(255-tips,cv2.DIST_L2,3),2.0)*(1-tip)
    col=K.mix(col,np.array([.96,.54,.26],F),guard*.65)
    col+=cuff[...,None]*np.array([.08,.18,.33],F)
    col=K.mix(col,K.ramp(tier,['477de0','88d8f0','e2ffff']),bf*.90)
    col=K.mix(col,np.array([.99,.93,.74],F),tip)
    M=30+90*tier+95*cone;R=28+65*(1-tier)+35*(1-cone);C=16+140*tier
    M,R,C=over(M,R,C,ef,8,210+35*tier,220+30*tier)
    M,R,C=over(M,R,C,ripple,20+70*tier,135+90*tier,140+100*tier)
    M,R,C=over(M,R,C,guard,145+100*tier,35+85*tier,40+145*tier)
    M,R,C=over(M,R,C,bf,140+100*tier,20+70*tier,20+120*tier)
    M,R,C=over(M,R,C,tip,240,16,16)
    return K.pack(col,M,R,C)
