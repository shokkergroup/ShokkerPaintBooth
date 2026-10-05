"""SPB owner rebuild / 2026-09-18 / tick FLAW-R1.
Owner: 'totally rebuild them'; M7 diagnostic per explicit PASS override.
Twenty-one independent inspection constructions, baked losslessly for runtime.
No generated raster source, quadrant copies, or common decorative noise carrier.
"""
from pathlib import Path
import math,json,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw
import cv2
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).parent/'authored';OUT.mkdir(exist_ok=True)
N=2048
# Each list names the actual layers drawn below, not interchangeable style labels.
DESIGNS={
'penetrant_bleed':('Penetrant Bleed','branched fatigue fissures with capillary dye reservoirs', ['developer wash','wicking halos','open fissures','dye reservoirs','satellite indications'],['112a45','55a060','edff65','ff7a18','caffee']),
'brittle_lacquer':('Brittle Lacquer','ranked tensile crack combs with arrested tips and lifted lacquer lips',['lacquer islands','tension cracks','lifted lips','arrest bars','detached flakes'],['26244b','ff3c89','fabb64','40dcdd','cbd0ff']),
'macro_etch':('Macro Etch','bent forging grain ribbons flowing around die bosses',['grain ribbons','etched boundaries','die bosses','compressed bands','inclusion strings'],['132e46','11bfa9','e4a642','ee6577','b4f5ea']),
'hardness_indent':('Hardness Indent','diamond pyramid impressions with four independently polished faces',['indent wells','pyramid faces','pileup rims','corner cracks','traverse dots'],['132e59','f376ac','e8b354','3de0ea','e8f7ff']),
'crack_tip':('Crack Tip Field','open cracks ending in paired butterfly yield lobes',['crack stems','yield lobes','stress contours','slip fans','arrest tips'],['131d42','ee4174','ffc660','31c8cb','eabfff']),
'strain_rosette':('Strain Rosette','three directional serpentine foil gauges with separate solder pads',['polyimide pads','serpentine conductors','return bends','terminal lands','lead wires'],['8c3d18','ffd260','fc8b52','48d8d4','fff1a4']),
'chladni':('Chladni Figure','intersecting standing wave nodes with granular ridges and scoured antinodes',['modal ridges','node grains','intersection heaps','scoured bellies','stray powder'],['152948','fab448','f773ce','27dbba','e0fbba']),
'holo_interfero':('Holographic Interferogram','eccentric contour orders surrounding displaced skin blisters',['bulge contours','order shoulders','disbond rims','phase discontinuities','isolated fringe glints'],['172956','f742bb','f9c770','31dbe2','d6fffc']),
'moire_deflect':('Moire Deflectometry','two locally displaced Ronchi gratings with beat envelopes',['first ruling','crossed ruling','beat knots','deflection seams','registration slits'],['221440','fb7653','9a6bf5','4beac7','f0e277']),
'shearography':('Shearography','opposed fringe lobes separated by a displacement derivative null',['positive fringes','negative fringes','null seams','coherent grains','disbond edges'],['122c4e','ff638e','44dcd2','f4cd57','b495ff']),
'schlieren':('Schlieren','directional density gradients curling into knife edge flow streaks',['compression ribbons','expansion ribbons','curl cores','shear threads','shock ticks'],['112d49','2be1df','ff8456','a396ff','efffba']),
'shadowgraph':('Shadowgraph','paired bright and dark shock fronts with refracted crossing wakes',['compression fronts','shadow doubles','shock intersections','wake arcs','fine caustics'],['151f51','f44bac','4cb8ff','ffbf65','c4fce5']),
'barkhausen':('Barkhausen Noise','jagged avalanche domains with pinned walls and burst ladders',['domain plates','jump boundaries','avalanche spikes','pinning inclusions','switching ladders'],['351a42','ff694a','efc060','47d5a4','ca8eff']),
'c_scan':('Ultrasonic C-Scan','raster echo cells quantizing irregular defect islands',['sample cells','echo plateaus','defect margins','dropout pixels','probe steps'],['132a69','1ccbd1','f44586','f4d75d','a899ff']),
'a_scan_gate':('A-Scan Gate','stacked oscilloscope echo trains enclosed by independent gate cursors',['trace baselines','entry pulses','backwall echoes','gate brackets','ringdown ripples'],['0c3543','36eec2','ffa13d','ff65b6','d9e8ff']),
'phased_array':('Phased Array','rotated fan sectors divided into angular beams and curved range gates',['sector wedges','range arcs','hot echo cells','dead beams','focus points'],['251a57','794bdf','ff7859','f7d768','34e2d4']),
'radiograph_weld':('Weld Radiograph','sinuous multipass weld beads showing internal pores and lack of fusion',['bead ribbons','overlap scallops','gas pores','fusion gaps','dense inclusions'],['18224e','648bf2','f889ba','ffd183','33d9c7']),
'ct_slice':('CT Slice','asymmetric hollow sections with detector ring artifacts and metal streaks',['section walls','internal cavities','detector rings','metal streaks','density islands'],['192b45','38d4c1','ff9562','a080ed','ffe4a3']),
'tsa_stress':('Thermoelastic Stress','opposed thermal stress lobes around loaded perforations sampled on detector pixels',['loaded webs','hot lobes','cool lobes','detector cuts','stress concentration rims'],['211849','f63d7e','22bad2','fcad52','e2f7a2']),
'pulse_thermo':('Pulse Thermography','nested delayed heat islands with independently diffusing perimeters',['warm plateaus','cooling halos','delamination cores','depth contours','sound material channels'],['152455','f25041','ffcc57','d147af','29d6c6']),
'acoustic_emission':('Acoustic Emission','intersecting partial arrival rings and triangulated burst sites',['arrival rings','sensor vertices','triangulation chords','burst stars','attenuation dots'],['0f304b','f9bb43','f477b8','47e1d0','e3eaff'])}

# Feature-bound M/R/Cc anchors, in the same semantic order as DESIGNS.
# Dyes/heat displays remain dielectric; etched and conductor layers can be metallic.
MATERIALS={
'penetrant_bleed':[(8,220,210),(18,95,130),(4,145,245),(5,18,16),(35,175,80)],
'brittle_lacquer':[(15,38,20),(20,200,240),(240,24,250),(70,130,90),(160,58,175)],
'macro_etch':[(175,105,120),(245,28,250),(235,18,20),(95,190,160),(65,70,230)],
'hardness_indent':[(35,165,225),(230,35,32),(252,18,250),(10,185,130),(160,95,20)],
'crack_tip':[(10,185,210),(85,80,240),(240,25,245),(35,160,80),(240,15,16)],
'strain_rosette':[(8,130,170),(225,35,20),(245,22,235),(180,75,55),(105,155,235)],
'chladni':[(10,200,210),(25,245,145),(5,175,250),(245,18,20),(30,120,65)],
'holo_interfero':[(190,32,245),(250,16,20),(70,170,180),(20,50,230),(245,10,16)],
'moire_deflect':[(210,25,235),(30,155,245),(250,38,20),(15,220,90),(145,90,175)],
'shearography':[(40,55,235),(235,25,245),(10,160,90),(145,140,45),(245,18,16)],
'schlieren':[(190,45,240),(15,150,220),(220,25,20),(35,210,85),(245,15,175)],
'shadowgraph':[(240,25,245),(5,190,220),(145,90,25),(30,40,200),(230,15,16)],
'barkhausen':[(170,75,190),(245,22,245),(210,20,20),(15,195,130),(70,130,240)],
'c_scan':[(25,65,240),(180,120,40),(245,28,230),(5,220,190),(125,20,16)],
'a_scan_gate':[(35,155,210),(240,25,235),(120,80,20),(10,210,120),(190,40,170)],
'phased_array':[(145,95,220),(245,18,235),(220,25,20),(10,210,190),(55,60,16)],
'radiograph_weld':[(180,115,65),(245,28,235),(15,210,220),(5,85,160),(245,15,16)],
'ct_slice':[(110,120,220),(15,210,130),(240,28,245),(245,15,20),(55,60,180)],
 'tsa_stress':[(15,140,200),(220,30,245),(25,180,220),(5,80,30),(245,20,16)],
'pulse_thermo':[(200,55,240),(30,190,220),(245,22,20),(90,95,170),(10,160,65)],
'acoustic_emission':[(220,30,235),(245,18,20),(20,170,220),(170,60,245),(10,220,110)]}

def draw_local(key,rng):
    im=[Image.new('L',(384,384)) for _ in range(5)];d=[ImageDraw.Draw(i) for i in im]
    q=rng.uniform(.8,1.65);a=rng.uniform(0,6.28)
    def pts(ps):return [(192+q*(x*math.cos(a)-y*math.sin(a)),192+q*(x*math.sin(a)+y*math.cos(a))) for x,y in ps]
    def line(k,ps,w=3): d[k].line(pts(ps),fill=int(rng.integers(65,256)),width=w,joint='curve')
    def poly(k,ps):d[k].polygon(pts(ps),fill=int(rng.integers(65,256)))
    def ring(k,x,y,rx,ry=None,w=3,start=0,end=360):
        ry=rx if ry is None else ry
        line(k,[(x+rx*math.cos(t),y+ry*math.sin(t)) for t in np.linspace(math.radians(start),math.radians(end),90)],w)
    def dot(k,x,y,r):poly(k,[(x+r*math.cos(t),y+r*math.sin(t)) for t in np.linspace(0,6.283,16)])
    if key=='penetrant_bleed':
        path=[(-85,-35),(-48,-12),(-30,-20),(0,5),(25,0),(50,30),(85,22)]
        line(0,path,24);line(1,path,13);line(2,path,3)
        for x,y in path[1:-1]:
            side=[(x,y),(x-3,y-18),(x+10,y-33)];line(1,side,9);line(2,side,2);dot(3,x,y,5)
        for _ in range(16):dot(4,rng.uniform(-85,85),rng.uniform(-45,45),rng.uniform(1,3))
    elif key=='brittle_lacquer':
        for j in range(-3,4):
            x=j*23;path=[(x-7,-65),(x+4,-25),(x-2,15),(x+9,63)]
            poly(0,[(x-10,-64),(x+9,-58),(x+17,55),(x-6,65)]);line(2,[(u+4,v) for u,v in path],5);line(1,path,2);line(3,[(x-7,28),(x+5,22)],3)
            poly(4,[(x+8,-25),(x+16,-15),(x+10,-5)])
    elif key=='macro_etch':
        for j in range(-6,7):
            path=[(x,j*10+17*math.sin(x/36)*math.exp(-j*j/30)) for x in range(-90,91,3)]
            line(0,path,6);line(1,[(x,y+4) for x,y in path],2)
        ring(2,0,0,17,27,5);ring(3,4,0,28,39,3)
        for j in range(9):dot(4,-70+j*16,55+5*math.sin(j),2)
    elif key=='hardness_indent':
        poly(0,[(-58,0),(0,-58),(58,0),(0,58)])
        for j in range(4):
            t=j*math.pi/2;u=(52*math.cos(t),52*math.sin(t));v=(52*math.cos(t+math.pi/2),52*math.sin(t+math.pi/2));poly(1,[(0,0),u,v]);line(2,[u,v],4);line(3,[u,(u[0]*1.3+3,u[1]*1.3-2)],2)
        for x in (-80,80):dot(4,x,0,4)
    elif key=='crack_tip':
        line(0,[(-90,0),(-45,3),(-18,0),(0,0)],5)
        for s in (-1,1):
            for j in range(1,5):
                ring(1,20,s*20,j*11,j*8,5,0,290);ring(2,20,s*20,j*11+3,j*8+2,2,15,260)
            for j in range(4):line(3,[(0,0),(22+j*12,s*(35+j*10))],2)
        dot(4,0,0,5)
    elif key=='strain_rosette':
        for j in range(3):
            theta=j*2.094
            def rot(ps):return [(x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta)) for x,y in ps]
            poly(0,rot([(12,-19),(85,-19),(85,19),(12,19)]))
            ps=[]
            for z in range(8):ps.extend([(19+z*8,-12 if z%2==0 else 12),(19+z*8,12 if z%2==0 else -12)])
            line(1,rot(ps),3)
            for z in range(7):line(2,rot([(19+z*8,12 if z%2==0 else -12),(27+z*8,12 if z%2==0 else -12)]),3)
            poly(3,rot([(5,-7),(15,-7),(15,7),(5,7)]));line(4,rot([(8,0),(-5,0),(-15,8)]),2)
    elif key=='chladni':
        for s in (-1,1):
            path=[(x,s*(22+30*math.cos(x/32))) for x in range(-88,89,2)];line(0,path,7)
            for x,y in path[::4]:dot(1,x+rng.uniform(-3,3),y+rng.uniform(-3,3),2)
        for x in (-50,50):dot(2,x,0,6);ring(3,x,0,17,23,2)
        for _ in range(20):dot(4,rng.uniform(-85,85),rng.uniform(-65,65),1.2)
    elif key=='holo_interfero':
        for j in range(1,8):
            ring(0,j*1.8,0,j*11,j*8,4);ring(1,j*1.8,0,j*11+3,j*8+2,2,start=20,end=300)
        ring(2,10,0,91,69,3,start=50,end=310);line(3,[(-40,-60),(-27,-30),(-22,0)],3)
        for j in range(6):dot(4,j*13-35,j*7-20,2)
    elif key=='moire_deflect':
        for j in range(-9,10):
            line(0,[(j*9+10*math.sin(y/30),y) for y in range(-80,81,4)],3)
            line(1,[(x,j*9+.22*x+8*math.cos(x/40)) for x in range(-80,81,4)],2)
        ring(2,0,0,31,57,3);line(3,[(-70,-50),(-20,-10),(30,30),(70,40)],4)
        for y in (-64,64):line(4,[(-12,y),(12,y)],3)
    elif key=='shearography':
        for s,k in [(-1,0),(1,1)]:
            for j in range(1,6):ring(k,s*30,0,j*9,j*13,3,start=-75 if s<0 else 105,end=255 if s<0 else 435)
        line(2,[(0,-73),(4,-30),(0,0),(-4,30),(0,73)],4)
        for _ in range(45):dot(3,rng.uniform(-75,75),rng.uniform(-70,70),1)
        ring(4,0,0,87,76,2,start=20,end=150)
    elif key=='schlieren':
        for j in range(-3,4):
            path=[(x,j*16+16*math.tanh(x/20)+10*math.sin(x/38+j*.3)) for x in range(-90,91,2)]
            line(0,path,7);line(1,[(x,y+5) for x,y in path],3)
        for t in np.linspace(0,9,90):
            if t>0:line(2,[(20+3*(t-.1)*math.cos(t-.1),3*(t-.1)*math.sin(t-.1)),(20+3*t*math.cos(t),3*t*math.sin(t))],3)
        line(3,[(-80,70),(-35,60),(15,65),(80,50)],2);line(4,[(-30,-65),(-15,-40)],4)
    elif key=='shadowgraph':
        for j in range(4):
            path=[(-78,-68+j*24),(-15,-15+j*14),(78,65-j*20)]
            line(0,path,5);line(1,[(x+5,y-5) for x,y in path],4)
        dot(2,-15,0,6)
        for j in range(3):ring(3,20,10,30+j*15,20+j*8,2,start=25,end=200)
        line(4,[(-80,40),(-20,20),(55,34)],2)
    elif key=='barkhausen':
        for j in range(5):
            x=-75+j*32;poly(0,[(x,-60),(x+23,-48),(x+12,-6),(x+30,17),(x+17,64),(x-9,43),(x+3,6)])
            line(1,[(x,-60),(x+10,-25),(x-3,0),(x+16,30),(x+17,64)],3)
            line(2,[(x,0),(x+8,-24),(x+12,17),(x+21,-7)],3);dot(3,x+4,32,4)
            for z in range(4):line(4,[(x+4,-40+z*9),(x+14,-35+z*9)],2)
    elif key=='c_scan':
        for y in range(-8,9):
            for x in range(-8,9):
                value=math.sin(x*.37)*math.cos(y*.42)+.25*math.sin(x+y)
                k=0 if value<-.2 else (1 if value<.35 else 2)
                xx=x*10;yy=y*10;poly(k,[(xx,yy),(xx+8,yy),(xx+8,yy+8),(xx,yy+8)])
                if rng.random()<.025:poly(3,[(xx,yy),(xx+7,yy),(xx+7,yy+7),(xx,yy+7)])
        line(4,[(-90,-80),(-90,0),(-85,0),(-85,80)],3)
    elif key=='a_scan_gate':
        for j in range(-2,3):
            y=j*30;line(0,[(-90,y),(90,y)],1)
            for k,c,amp in [(1,-45,21),(2,35,14)]:
                path=[(x,y-amp*math.exp(-((x-c)/10)**2)*math.cos((x-c)*.7)) for x in np.linspace(c-22,c+22,80)];line(k,path,3)
            line(3,[(20,y-18),(20,y-24),(64,y-24),(64,y-18)],2)
            line(4,[(x,y+3*math.sin(x*1.1)*math.exp(-(x-50)/24)) for x in range(50,90)],2)
    elif key=='phased_array':
        for j in range(11):
            t=-1.12+j*.20;poly(0,[(0,65),(140*math.sin(t),65-140*math.cos(t)),(140*math.sin(t+.14),65-140*math.cos(t+.14))])
            if j%4==0:line(3,[(0,65),(130*math.sin(t),65-130*math.cos(t))],3)
        for r in range(30,141,18):ring(1,0,65,r,r,2,start=206,end=334)
        for j in range(7):dot(2,rng.uniform(-55,55),rng.uniform(-55,15),rng.uniform(3,7))
        dot(4,0,65,6)
    elif key=='radiograph_weld':
        for j in range(-2,3):
            y=j*28;line(0,[(x,y+7*math.sin(x/32)) for x in range(-90,91,3)],19)
            for x in range(-75,80,18):ring(1,x,y,12,10,3,start=-65,end=80)
            for z in range(4):ring(2,rng.uniform(-75,75),y+rng.uniform(-4,4),rng.uniform(3,6),w=3)
        line(3,[(-60,-12),(-25,-6),(7,-11),(25,-8)],3);poly(4,[(42,32),(63,29),(67,35),(47,38)])
    elif key=='ct_slice':
        path=[(70*math.cos(t)*(1+.17*math.sin(3*t)),60*math.sin(t)) for t in np.linspace(0,6.283,150)];line(0,path,14)
        for x,y,r in [(-27,0,18),(25,15,24),(8,-32,11)]:ring(1,x,y,r,r*.7,5)
        for r in (31,49,82):ring(2,5,-7,r,r,2)
        for j in range(8):t=j*.785;line(3,[(22,15),(22+80*math.cos(t),15+80*math.sin(t))],1)
        poly(4,[(-12,5),(-1,-12),(17,-3),(10,12)])
    elif key=='tsa_stress':
        poly(0,[(-90,-25),(90,-25),(90,25),(-90,25)])
        for s,k in [(-1,1),(1,2)]:
            for j in range(4):ring(k,0,s*21,27+j*9,12+j*5,5,start=0,end=180 if s<0 else 360)
        for x in range(-80,81,12):line(3,[(x,-60),(x,60)],1)
        ring(4,0,0,22,22,5)
    elif key=='pulse_thermo':
        for j in range(6,0,-1):
            k=0 if j<3 else 1
            path=[((12+j*11)*(1+.15*math.cos(3*t+.5))*math.cos(t),(8+j*8)*(1+.12*math.sin(4*t))*math.sin(t)) for t in np.linspace(0,6.283,120)]
            line(k,path,8);line(3,[(x*1.025,y*1.025) for x,y in path],2)
        poly(2,[(-15,-8),(8,-17),(25,2),(5,20),(-18,10)]);line(4,[(-80,50),(-40,30),(0,65),(80,45)],3)
    elif key=='acoustic_emission':
        for x,y in [(-40,-25),(37,-23),(0,47)]:
            for r in (22,43,64):ring(0,x,y,r,r,2,start=15,end=310)
            poly(1,[(x,y-6),(x+6,y+5),(x-6,y+5)]);line(2,[(x,y),(0,0)],2)
        for j in range(9):t=j*6.283/9;line(3,[(0,0),(14*math.cos(t),14*math.sin(t))],3)
        for j in range(16):t=j*6.283/16;dot(4,83*math.cos(t),83*math.sin(t),2)
    else:raise ValueError(key)
    return im

def render(key):
    rng=np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8],16));layers=[np.zeros((N,N),np.uint8) for _ in range(5)]
    # Torus stamping keeps edge-crossing geometry intact without duplicating quadrants.
    step={'c_scan':155,'moire_deflect':150,'macro_etch':155,'strain_rosette':147,'penetrant_bleed':110,'hardness_indent':130,'chladni':140,'acoustic_emission':175,'phased_array':165}.get(key,145)
    for y in np.arange(0,N,step):
        for x in np.arange(0,N,step):
            xx=int(x+rng.uniform(-48,48));yy=int(y+rng.uniform(-48,48))
            local=draw_local(key,rng)
            for k,im in enumerate(local):
                a=np.array(im);xs=(np.arange(384)+xx-192)%N;ys=(np.arange(384)+yy-192)%N
                layers[k][np.ix_(ys,xs)]=np.maximum(layers[k][np.ix_(ys,xs)],a)
    colors=np.array([[int(c[i:i+2],16) for i in (0,2,4)] for c in DESIGNS[key][3]],np.float32)
    paint=np.zeros((N,N,3),np.float32)+colors[0]*.48
    # Per-finish and per-feature material states. Layers encode actual named forms.
    metallic=key in ('macro_etch','hardness_indent','strain_rosette','barkhausen','radiograph_weld')
    base=np.array([85,70,125] if metallic else [12,62,120],np.float32)
    spec=np.zeros_like(paint)+base
    for k,a in enumerate(layers):
        mask=a>0;dist=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,3)
        interior=np.clip(dist/(3+k*1.4),0,1);local=a.astype(np.float32)/255
        edge=np.clip(1-dist/3,0,1)
        shade=.68+.32*interior;col=colors[k]*shade[...,None]*(.65+.45*local[...,None])+edge[...,None]*colors[(k+1)%5]*.30
        alpha=mask.astype(np.float32)[...,None]
        paint=paint*(1-alpha)+col*alpha
        # Continuous shoulder -> polished lip -> satin face, with feature-specific local tiers.
        offset=(int(hashlib.sha256((key+str(k)).encode()).hexdigest()[:4],16)%7)/7
        # Per-site material intensity is independent of layer coverage. Broad ranges
        # do not collapse to a few constant colors on thin edges at picker scale.
        anchor=np.array(MATERIALS[key][k],np.float32)
        # Eight intra-feature tiers interpolate continuously: local stamped values
        # change independently; contours stay tied to the exact geometric layer.
        phase=np.clip(.16+.62*interior+.22*local,0,1)
        shoulder=np.array(MATERIALS[key][(k+1)%5],np.float32)
        target=anchor[None,None,:]*phase[...,None]+shoulder[None,None,:]*(1-phase[...,None])
        target+=np.stack([35*(local-.6),48*np.sin(local*8+interior*3),42*np.sin(local*11-interior*4)],axis=-1)
        target[...,0:2]=np.clip(target[...,0:2],0,255);target[...,2]=np.clip(target[...,2],16,255)
        spec=spec*(1-alpha)+target*alpha
    return np.uint8(np.clip(paint,0,255)),np.uint8(np.clip(spec,0,255))

if __name__=='__main__':
    for key in sys.argv[1:] or DESIGNS:
        p,s=render(key)
        for kind,a in [('paint',p),('spec',s)]:Image.fromarray(a).save(OUT/f'fl_{key}_{kind}.png')
        print(key,flush=True)
