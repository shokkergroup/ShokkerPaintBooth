"""FRACTURED SHOKK: twenty original, feature-bound light-response studies.

SPB-105 / FSH20-I1 / 2026-09-18. Owner: "TWENTY finishes. No more."
IMPROVE mode; replaces the visible HOUDINI shelf. M7: new -> pending measured
evidence, not an owner acceptance claim. No competitor pixels enter synthesis.
Paint is fixed pigment; view/light-dependent response comes from iRacing PBR.
"""
from functools import lru_cache
from pathlib import Path
import hashlib
import cv2
import numpy as np

GROUP = "⚡ FRACTURED SHOKK"
REVISION = "fsh-r3-colors-20260918"
# Each row owns a different geometric construction, NOT a palette variation.
DESIGNS = [
 ("spectral_silver", "Spectral Silver", "split triangular prism facets", "prism face|silver shoulder|cut ridge|etched pocket|facet tip"),
 ("ribbon_refraction", "Ribbon Refraction", "segmented bowed optical ribbons", "ribbon body|bowed edge|end cap|cross notch|gap enamel"),
 ("chromatic_comb", "Chromatic Comb", "interdigitated offset comb teeth", "comb spine|long tooth|short tooth|tooth root|groove bed"),
 ("opal_fault", "Opal Fault", "irregular nearest-seed mineral cells", "opal body|fault wall|mineral rim|inclusion|triple junction"),
 ("nacre_cascade", "Nacre Cascade", "staggered nested shell fans", "shell lip|shell bowl|growth ring|hinge|overlap shadow"),
 ("quasicrystal_fire", "Quasicrystal Fire", "five-axis aperiodic interference crystals", "crystal island|node|crossing|low saddle|crystal rim"),
 ("rosette_engine", "Rosette Engine", "eight-lobed engraved rosettes", "petal crest|petal trough|medallion|radial notch|interstice"),
 ("diamond_fold", "Diamond Fold", "opposed concave diamond foil folds", "fold face|ridge|valley|crease point|foil shoulder"),
 ("frost_voltage", "Frost Voltage", "six-armed branched ice dendrites", "ice trunk|branch|branch tip|hub|frost ground"),
 ("photon_circuit", "Photon Circuit", "alternating right-angle optical traces", "trace|elbow|terminal|contact pad|insulator"),
 ("caustic_lens", "Caustic Lens", "offset asymmetric elliptical lenslets", "lens well|inner caustic|outer rim|focus|lens gap"),
 ("spectral_satin", "Spectral Satin", "three-over-one interlaced optical tapes", "warp|weft|crossover|fiber channel|selvedge"),
 ("meteor_wake", "Meteor Wake", "staggered tapered comet wakes", "meteor head|split tail|wake|shoulder|dark pocket"),
 ("ferro_crown", "Ferro Crown", "five-point fluid crowns with rounded basins", "spike|basin|crown lip|central bead|magnetic saddle"),
 ("isobar_chrome", "Isobar Chrome", "labyrinthine broken contour terraces", "terrace|contour|saddle|crest|cut bank"),
 ("crystal_needle", "Crystal Needle", "crossed acicular crystal bundles", "needle body|cleavage|needle tip|crossing|matrix"),
 ("bubble_spectrum", "Bubble Spectrum", "polydisperse concentric film bubbles", "film bowl|film rim|inner ring|contact glint|interstitial film"),
 ("iris_turbine", "Iris Turbine", "curved seven-blade micro turbines", "blade|blade edge|hub|sweep groove|interblade pocket"),
 ("herringbone_flash", "Herringbone Flash", "interlocked angular optical parquet", "left plank|right plank|bevel|end grain|joint"),
 ("hex_resonance", "Hex Resonance", "offset hexagonal resonators with split centers", "hex wall|resonator bowl|split center|vertex|outer gasket"),
]

def catalog():
    return [{"id":"fsh_"+slug,"name":globals().get("R3_NAMES",{}).get("fsh_"+slug,name),"desc":globals().get("R3_DESCRIPTIONS",{}).get("fsh_"+slug,grammar.capitalize()+" with coordinated spectral paint and material states."),"swatch":"#91adb8"} for slug,name,grammar,_ in DESIGNS]

def _hash(a,b,s):
    z=(np.asarray(a,dtype=np.uint32)*np.uint32(1597334677)) ^ (np.asarray(b,dtype=np.uint32)*np.uint32(3812015801)) ^ np.uint32(s*7919+17)
    z ^= z>>16; z *= np.uint32(2246822519); z ^= z>>13
    return (z&65535).astype(np.float32)/65535

def geometry(i,n=2048):
    """Five named semantic masks and local optical phase; 8–32px motifs.

    Coordinate transformations below belong to the named constructions. No
    category-wide low-frequency overlay is applied to paint or spec.
    """
    y,x=np.mgrid[:n,:n].astype(np.float32); x*=2048/n; y*=2048/n
    p=32.; u=x/p; v=y/p
    if i==0: u=(x+.5*y)/24;v=y/24
    elif i==1: u=x/32;v=(y+5*np.sin(x/81))/18
    elif i==2: u=x/32;v=y/24
    elif i==4: u=x/28+.5*(np.floor(y/24)%2);v=y/24
    elif i==6: u=(x+6*np.sin(y/80))/29+.5*(np.floor(y/27)%2);v=y/27
    elif i==7: u=(x+y)/28;v=(x-y)/28
    elif i==8: u=x/32+.5*(np.floor(y/28)%2);v=y/28
    elif i==9: u=x/24;v=y/24
    elif i==10: u=(x+3*np.sin(y/77))/30;v=(y+4*np.sin(x/111))/24
    elif i==11: u=x/8;v=y/8
    elif i==12: u=(x+.38*y)/32;v=y/22
    elif i==13: u=x/30+.5*(np.floor(y/28)%2);v=y/28
    elif i==15: u=(x+.6*y)/28;v=(y-.15*x)/24
    elif i==16: u=x/32+.5*(np.floor(y/30)%2);v=y/30
    elif i==17: u=x/32;v=y/32
    elif i==18: u=(x+y)/11.314;v=(y-x)/11.314
    elif i==19: u=x/28+.5*(np.floor(y/24)%2);v=y/24
    gx=np.floor(u).astype(np.int32);gy=np.floor(v).astype(np.int32)
    a=(u-gx-.5).astype(np.float32);b=(v-gy-.5).astype(np.float32)
    h=_hash(gx,gy,i+5);r=np.hypot(a,b);t=np.arctan2(b,a)
    role=np.zeros((n,n),np.uint8)
    if i==0:
        f=a+b;role[f>0]=1;role[np.abs(f)<.09]=2;role[(a<-.24)&(b>.05)]=3;role[(a>.21)&(b>.21)]=4
        phase=(gx*.025+gy*.018+np.where(f>0,.11,0));relief=np.abs(f)
    elif i==1:
        f=b+.16*np.cos(a*5);role[np.abs(f)<.30]=1;role[np.abs(a)>.34]=2;role[(np.abs(a)<.14)&(f<-.08)]=3;role[np.abs(f)>.42]=4
        phase=(gy*.027+np.sin(gx*.07)*.23+a*.15);relief=1-np.abs(f)
    elif i==2:
        tooth=(a+.5)*3%1;role[(tooth<.45)&(b>-.2)]=1;role[(tooth>.55)&(b<.2)]=2;role[np.abs(b)<.13]=3;role[np.abs(a)>.43]=4
        phase=gx*.018+gy*.041+tooth*.24;relief=tooth
    elif i==3:
        # Irregular Voronoi: independent jittered nuclei, including neighbor cells.
        d0=np.full((n,n),99,np.float32);d1=d0.copy();cx=a.copy();cy=b.copy()
        for oy in (-1,0,1):
            for ox in (-1,0,1):
                dx=a-ox-(_hash(gx+ox,gy+oy,91)-.5)*.65;dy=b-oy-(_hash(gx+ox,gy+oy,93)-.5)*.65;d=dx*dx+dy*dy
                win=d<d0;d1=np.where(win,d0,np.minimum(d1,d));cx=np.where(win,dx,cx);cy=np.where(win,dy,cy);d0=np.minimum(d0,d)
        gap=d1-d0;role[gap<.13]=1;role[(gap>=.13)&(gap<.24)]=2;role[d0<.055]=3;role[(gap<.09)&(d0>.27)]=4
        phase=np.arctan2(cy,cx)/6.28*.18+gx*.032-gy*.023;relief=np.sqrt(d0)
    elif i==4:
        q=np.hypot(a,b+.36);ring=(q*3)%1;role[q>.60]=1;role[ring<.22]=2;role[q<.20]=3;role[q>.79]=4
        phase=gy*.032+np.arctan2(b+.36,a)*.14;relief=q
    elif i==5:
        waves=[np.cos((x*np.cos(k*np.pi/5)+y*np.sin(k*np.pi/5))*2*np.pi/25) for k in range(5)]
        f=sum(waves)/5;role[f>.29]=1;role[(waves[0]*waves[2]>.38)&(f<.29)]=2;role[f<-.25]=3;role[(f>.08)&(f<.17)]=4
        phase=(waves[1]-waves[3])*.15+(x+y)/1600;relief=(f+1)*.5
    elif i==6:
        q=r+.095*np.cos(8*t);role[q<.34]=1;role[(q>.36)&(q<.45)]=2;role[r<.13]=3;role[q>.53]=4
        phase=np.cos(8*t)*.2+r*.55+gy*.006;relief=q
    elif i==7:
        q=np.abs(a)+np.abs(b);role[a*b>0]=1;role[q<.23]=2;role[q>.74]=3;role[np.abs(np.abs(a)-np.abs(b))<.095]=4
        phase=(gx-gy)*.021+np.sign(a*b)*.12;relief=q
    elif i==8:
        sector=(t+np.pi/6)%(np.pi/3)-np.pi/6;aa=r*np.cos(sector);bb=r*np.sin(sector)
        role[:]=4;role[(np.abs(bb)<.04)&(aa<.46)]=0
        branch=np.minimum(np.abs(np.abs(bb)-(.27-aa)*.7),np.abs(np.abs(bb)-(.42-aa)*.7))
        role[(branch<.035)&(aa>.12)&(aa<.40)&(r<.48)]=1
        role[(aa>.37)&(np.abs(bb)<.075)&(aa<.48)]=2;role[r<.11]=3;q=np.abs(bb)
        phase=gy*.022+gx*.012+t*.16;relief=1-q
    elif i==9:
        flip=(gx+gy)%2;aa=np.where(flip,a,-a);q=np.minimum(np.abs(aa+.19),np.abs(b-.19));role[q<.12]=1;role[(aa<-.05)&(b>.04)]=2;role[(aa>.1)&(np.abs(b+.22)<.16)]=3;role[q>.30]=4
        phase=gx*.031+gy*.013+flip*.18;relief=q
    elif i==10:
        q=np.hypot(a*.8,b*1.2);role[q<.24]=1;role[(q>.32)&(q<.44)]=2;role[((a-.14)**2+(b+.1)**2)<.025]=3;role[q>.55]=4
        phase=gy*.04+np.sin(gx*.10)*.22+q*.45;relief=q
    elif i==11:
        over=(gx-gy)%4;role[over==0]=1;role[(np.abs(a)<.25)&(over!=0)]=2;role[(np.abs(b)<.18)&(over==0)]=3;role[(np.abs(a)>.35)&(np.abs(b)>.35)]=4
        phase=(gx*.007+gy*.008)+np.where(over==0,.32,0);relief=np.where(over==0,np.abs(b),np.abs(a))
    elif i==12:
        q=np.abs(b)-(.46-(a+.5)*.35);role[q<-.17]=1;role[(np.abs(b)<.1)&(a<.15)]=2;role[(a>.14)&(r<.38)]=3;role[q>.04]=4
        phase=(gx*.037-gy*.013+a*.27);relief=q+.5
    elif i==13:
        q=r*(1+.30*np.cos(5*t));role[q<.34]=1;role[(q>.36)&(q<.46)]=2;role[r<.14]=3;role[q>.57]=4
        phase=(gx+gy)*.018+np.cos(5*t)*.19;relief=q
    elif i==14:
        f=np.sin(x/4.3+1.1*np.sin(y/7.2))+np.cos(y/4.1+.8*np.cos(x/8.2));q=(f*2.5)%1
        role[q<.23]=1;role[(f>1.1)&(q>.3)]=2;role[(f<-.9)&(q>.3)]=3;role[(q>.72)&(q<.88)]=4
        phase=f*.19+x/1800-y/2500;relief=q
    elif i==15:
        q=np.abs(b-.65*a);q2=np.abs(b+.8*a);role[q<.12]=1;role[(q2<.09)&(a<.28)]=2;role[(np.abs(a)>.30)&(q<.18)]=3;role[(q>.30)&(q2>.23)]=4
        phase=gx*.04+gy*.017+np.where(q<q2,.15,.46);relief=np.minimum(q,q2)
    elif i==16:
        radius=.27+.19*h;q=r/radius;role[q<.63]=1;role[(q>.79)&(q<1.02)]=2;role[((a+.13)**2+(b+.17)**2)<.024]=3;role[q>1.15]=4
        phase=gy*.019+gx*.011+q*.28;relief=q*.5
    elif i==17:
        q=(t/6.283*7+r*2)%1;role[q<.37]=1;role[q>.79]=2;role[r<.16]=3;role[r>.49]=4
        phase=gx*.012+gy*.032+q*.30;relief=q
    elif i==18:
        # True staggered two-cell parquet: horizontal and vertical dominoes
        # meet on a zigzag joint, rather than circuit-like L cells.
        k=(gx+gy)%4;horizontal=k<2;along=np.where(horizontal,k+a+.5,k-2+b+.5)/2
        across=np.where(horizontal,b,a);edge=np.minimum(np.minimum(along,1-along),.5-np.abs(across))
        role[~horizontal]=1;role[edge<.14]=2;role[(along<.21)|(along>.79)]=3;role[edge<.055]=4
        phase=along*.43+horizontal*.25
        relief=np.clip(1-np.abs(across)*2,0,1)
    else:
        q=np.maximum(np.abs(a)*.866+np.abs(b)*.5,np.abs(b));role[q<.28]=1;role[(q<.3)&(a>0)]=2;role[(q>.37)&(q<.45)]=3;role[q>.47]=4
        phase=gx*.026+gy*.019+np.where(a>0,.22,-.10)+q*.13;relief=q
    # I2: remove repeated broad rainbow stripes. Each optical topology owns
    # its own color distribution and lobe population; no category-wide wave.
    X=x/2048;Y=y/2048
    if i==0: phase=.08+.72*X+.16*(role==2)
    elif i==1: phase=.18+.48*np.sin(X*2.2)+.28*Y+a*.08
    elif i==2: phase=.06+tooth*.72+.13*np.sin(gy*.15)
    elif i==3: phase=np.arctan2(cy,cx)/6.28*.65+.2*np.hypot(X-.2,Y-.8)
    elif i==4: phase=np.arctan2(b+.36,a)*.23+Y*.23
    elif i==5: phase=(waves[1]-waves[3])*.23+(waves[2]*waves[4])*.18
    elif i==7: phase=(a*b*1.3)+.26*np.abs(X-Y)+.28*(role==1)
    elif i==8: phase=t/6.283+.18*np.hypot(X-.65,Y-.23)
    elif i==9: phase=.08+((gx//5+gy//7)%5)*.145+flip*.11
    elif i==10: phase=q*.80+.11*np.sin(X*4+Y*7)
    elif i==11: phase=.16+.33*(over==0)+.24*X*Y+np.abs(a)*.20
    elif i==12: phase=(a+.5)*.63+.22*Y
    elif i==13: phase=np.cos(5*t)*.22+q*.39+.16*X
    elif i==14: phase=f*.21+.15
    elif i==15: phase=np.minimum(q,q2)*1.1+.25*(q<q2)+Y*.19
    elif i==16: phase=q*.5+.19*h
    elif i==17: phase=q*.60+r*.42+X*.15
    elif i==19: phase=q*.67+.22*(a>0)+.24*Y*X
    return role,np.mod(phase,1).astype(np.float32),np.clip(relief,0,1).astype(np.float32),h

def synthesize(fid,n=2048):
    # SPB-105 / FSH-R3: preserve authored nonband source at every requested size.
    # Owner: "Anything but bands". R1 M7 historical -> R3 diagnostics pending.
    if fid in globals().get("R3_NAMES",{}):
        return tuple(cv2.resize(a,(n,n),interpolation=cv2.INTER_AREA) for a in render(fid,2048))
    i=next(j for j,row in enumerate(DESIGNS) if 'fsh_'+row[0]==fid)
    role,phase,relief,jitter=geometry(i,n)
    # Eight pigment/material tiers per feature. Local hue follows the named
    # geometry; phase is never a generic rainbow mask pasted over the category.
    tier=np.minimum((jitter*8).astype(np.int32),7)
    hue=(phase*179).astype(np.uint8)
    hsv=np.stack((hue,np.full_like(hue,205),np.full_like(hue,140)),axis=2)
    color=cv2.cvtColor(hsv,cv2.COLOR_HSV2RGB).astype(np.float32)/255
    light=np.array([.60,.92,.40,1.13,.22],np.float32)[role]
    pigment=color*(light*(.64+.055*tier)+.12*relief)[...,None]
    # Silver body and fractured optical faces: subdued neutral matrix, saturated
    # metallic cells, coat restrained on colored reflectors to avoid white wash.
    neutral=np.clip(.24+.15*relief+.025*tier,0,1)
    neutral_role=(role==4) if i!=0 else ((role==1)|(role==4))
    pigment[neutral_role]=np.stack([neutral*.93,neutral*.98,neutral],axis=2)[neutral_role]
    # Unique role assignment and tier direction for each construction. M/R/Cc
    # follow actual face/edge/pocket masks. Saturation isn't a spec channel.
    decks=np.array([
      [248,34,252],[226,76,210],[252,12,246],[184,116,116],[28,174,54]
    ],np.float32)
    decks[1]=[210+(i*7)%40,52+(i*11)%55,164+(i*13)%82]
    decks[3]=[114+(i*17)%110,100+(i*7)%55,64+(i*19)%150]
    if i==0:decks[1]=[168,110,112]
    spec=decks[role]
    spec[...,0]+=np.where(role<3,(tier-3)*1.5,(tier-3)*5)
    spec[...,1]+=(tier-3)*3+relief*(10+i%5*3)
    spec[...,2]+=np.where(role<3,-tier*2,(tier-3)*7)
    # I3 identity audit: regional phase staircases made dissimilar fine geometry
    # converge at picker scale (R correlation .87). Lobe width now follows the
    # actual surface relief inside each named feature, never the pigment phase.
    spectral=(role<3)
    lobe=np.clip(relief,0,1)
    spec[...,1]+=spectral*(lobe*94)
    spec[...,0]-=spectral*(np.maximum(lobe-.5,0)*46)
    spec[...,2]-=spectral*((1-lobe)*74)
    spec=np.clip(spec,[0,2,16],[255,240,255]).astype(np.uint8)
    paint=np.clip(pigment*255,0,255).astype(np.uint8)
    paint.flags.writeable=False;spec.flags.writeable=False
    return paint,spec

@lru_cache(maxsize=2)
def render(fid,n=2048):
    # SPB-105 / FSH20-I2-PERF: exact pre-bakes retain the authored pixels.
    # Opal source generation ~3.5s -> measured load path in bake_report.json.
    asset_dir=Path(__file__).with_name('fractured_shokk_assets')
    if asset_dir.is_dir() and n==2048:
        pair=[]
        for kind in ('paint','spec'):
            path=asset_dir/(fid+'_'+kind+'.png');raw=path.read_bytes()
            expected=globals().get('ASSET_SHA256',{}).get(path.name)
            if expected and hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('FRACTURED SHOKK asset integrity failure: '+str(path))
            a=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
            if a is None or a.shape!=(2048,2048,3):raise ValueError('Missing/corrupt FRACTURED SHOKK asset: '+str(path))
            a=cv2.cvtColor(a,cv2.COLOR_BGR2RGB);a.flags.writeable=False;pair.append(a)
        return tuple(pair)
    return synthesize(fid,n)

def make_pair(fid):
    def paint_fn(paint,shape,mask,seed,pm,bb):
        h,w=map(int,shape[:2]);src=np.asarray(paint,np.float32)[...,:3]
        if src.max()>1.5:src=src/255
        art=cv2.resize(render(fid)[0],(w,h),interpolation=cv2.INTER_AREA).astype(np.float32)/255
        m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
        if m.shape!=(h,w):m=cv2.resize(m,(w,h))
        return src*(1-np.clip(m*pm,0,1)[...,None])+art*np.clip(m*pm,0,1)[...,None]
    def spec_fn(shape,mask,seed,sm):
        h,w=map(int,shape[:2]);return cv2.resize(render(fid)[1],(w,h),interpolation=cv2.INTER_AREA).astype(np.float32)
    for fn in (paint_fn,spec_fn):
        fn._spb_picker_dependency_modules=(__name__,)
    return spec_fn,paint_fn

def install_into_engine(mono_reg,base_reg=None,fusion_reg=None):
    for row in catalog():mono_reg[row['id']]=make_pair(row['id'])
    return '20 FRACTURED SHOKK finishes installed'

def identity_contract(i):
    slug,name,grammar,marks=DESIGNS[i];names=marks.split('|');fid='fsh_'+slug
    return dict(schema='spb-finish-identity/1',finish_id=fid,display_name=name+' — FRACTURED SHOKK',
        promise='Fine '+grammar+' reveal saturated metallic reflections as illumination changes.',
        carrier_grammar=grammar+' with five separate geometric feature masks and eight local material tiers.',
        spec_grammar='Each '+grammar+' feature owns a metallic/rough/coat response tied to its visible boundaries.',
        reference_physics={'mechanism':'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.',
          'sources':['SPB_WIKI.html#spec_guide','https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']},
        native_scale_px=[8,32],mark_types=[{'name':m,'role':m+' defines one distinct material-bearing feature'} for m in names],
        material_binding={'M':names,'R':names,'Cc':names},material_tiers=[float(x) for x in (.18,.28,.38,.48,.58,.68,.78,.92)],
        nearest_neighbors=[{'finish_id':'xlab_hologram_metal','difference':'Original '+grammar+' instead of rotated square plates.'},{'finish_id':'hou_veiled_skull','difference':'All-over optical surface rather than a concealed skull silhouette.'}],
        name_truth={'hidden_title_verdict':'pending','visible_evidence':[grammar, names[0]+' visible geometry',names[1]+' visible geometry']},
        construction_key='fsh20:'+slug+':'+grammar,spec_key='fsh20:'+slug+':feature-bound-eight-tier-PBR')

# Written before renders. Name-test verdicts are completed by visual review,
# never preemptively asserted by the renderer.
IDENTITY_CONTRACTS={"fsh_"+row[0]:identity_contract(i) for i,row in enumerate(DESIGNS)}

# Exact installed assets and reviewed contracts participate in the picker module fingerprint.
ASSET_SHA256 = {'fsh_spectral_silver_paint.png': 'a5eacd408111ec5adf67d5cdf43c22dd06d4596d7e3ed017fcd5a6d096e3d65f', 'fsh_spectral_silver_spec.png': '11cad3a9a3c81d233c1b7a92726b73173296eb890db385557123ea6461eef204', 'fsh_ribbon_refraction_paint.png': 'ca48e76abac43d335b1cfffc59948654fce1d6b705d00e3caf8080812bdb7904', 'fsh_ribbon_refraction_spec.png': '61620a567cfc30b3ec117488d70230a3eee39f2193e98221ddbe68b3f9a843bc', 'fsh_chromatic_comb_paint.png': 'c8fc87b4ab1c55e3558fa4a11d2c5317626389311aa13bd1ab8e44cc6ea0bf02', 'fsh_chromatic_comb_spec.png': 'e11bf270f207008508f25d068dd8014882530565b74143d9a2434c19dafb6b04', 'fsh_opal_fault_paint.png': '8f9d45b047fc97e682405399a78ca31284c5da84c3c5671f931d60d41061f8ec', 'fsh_opal_fault_spec.png': 'e6561c582fc2c4b2ad525d5b6a20afa478d411ae6100f2606cc2b701cac0fba8', 'fsh_nacre_cascade_paint.png': '0fe4faf582e3255cddcc6eb44bc9d74d5970bfd5247637d121a43382353d3a1a', 'fsh_nacre_cascade_spec.png': '7e96658a479a10f1635972bc9ad03fd944d6c37e3a1908bae67bb9f30a4e25af', 'fsh_quasicrystal_fire_paint.png': 'b7d3213949d488fe4f4a14486ece2fe350c08e5b9f0b437156f0c40fbf4ffb22', 'fsh_quasicrystal_fire_spec.png': '3cb7695a1e0352f0284bcaea52b9b0e724e6d7c440ecd16e5983b7838d715503', 'fsh_rosette_engine_paint.png': '69ce8609846f9e1d772992647c167bbcd41e15cf2f832f339b59351778749bfd', 'fsh_rosette_engine_spec.png': '12509a7f2f961d119c6b79c40dc53fa6637815c7e8f968ed782a7940982cc599', 'fsh_diamond_fold_paint.png': '36388b1cf0e9b664c739b85e94c5a6850f0dd9c1cf8223d436e7e6d45c626324', 'fsh_diamond_fold_spec.png': 'a357188bfdb4547d2b5f82c93652f3f44cc3d1101897d172ceec441ae8f1651c', 'fsh_frost_voltage_paint.png': 'b847601631a2a65027320e482247e125561686c110876de80c5b9cc55179e445', 'fsh_frost_voltage_spec.png': '92d2c3f57d02b83334a60d22dbdf9e7edc529dd2fae2ced4c1452d33cf3f7c1f', 'fsh_photon_circuit_paint.png': 'd2489246ad21681e3722226b79e674c4d3aec64e76c2951d883e3e823bf608b4', 'fsh_photon_circuit_spec.png': 'd195dc1a90aeef4eb32c4d2970a1f197ba6ccb253e11d71dda92e0b320fca413', 'fsh_caustic_lens_paint.png': 'e56c19084dc8cf9b8d75da6430b8aa5d8a3483acf46a3403c0dc2acae408d332', 'fsh_caustic_lens_spec.png': '2cead5f93d4b52c951831637d89968367d34a770b79e5928ee89234aa0a27207', 'fsh_spectral_satin_paint.png': '1e3c3751dafa06d2167e390f58fb3ace5962f1a85cce5d231e106726393fd968', 'fsh_spectral_satin_spec.png': '83b7303bc44643d52d61a0b4bc9cb17eef3417b92e33c3cbe8f02873e2e88857', 'fsh_meteor_wake_paint.png': '990277e4b5d2e48616c96e6cfd53a308c6eeee37e0c02480e029763eca12b051', 'fsh_meteor_wake_spec.png': 'c44647bc855bec1fd5d447ef1a393d93f4f146c91309604d3e9f05efece8d8b5', 'fsh_ferro_crown_paint.png': 'bd6425c6bfeae038cbd748cef814ddb19a1c5f128b55c49bf5ecbd1c2b1462df', 'fsh_ferro_crown_spec.png': 'dc696593dd49eb3e222253a22d7a49f9f8ee84d74425dd1cb649f856807f5667', 'fsh_isobar_chrome_paint.png': 'a2a875dca5f56d8914a578180bb91ff4195b5133bf43f07ec036443e4d5b38fc', 'fsh_isobar_chrome_spec.png': '63261fc9af84f62e36d65a72bba71c13b95901df1d189900c7094063d1f682bc', 'fsh_crystal_needle_paint.png': '0e179947332c9c343786ccc18e7ea3dded0509034adc6323735bf306c6a08f55', 'fsh_crystal_needle_spec.png': '74e9ca3b8cca7257c6eb77341b732fa0124a07b3a2789d7fc133f0d813dda007', 'fsh_bubble_spectrum_paint.png': '3f42953e2717fc0664f80c4f8f6386ce0d0fa5b42e67e554742da3373d089400', 'fsh_bubble_spectrum_spec.png': '75de7a441ce242621c564026f0f8fc9735c397589eff3d44da1b1268e30cb121', 'fsh_iris_turbine_paint.png': '5f507ea9689fbdcdfa141ab0c79ff20c3071263cadba831457f284b26aea50a2', 'fsh_iris_turbine_spec.png': 'c98fb477f06c0419be366555074e545ec30a56f31dd94cd2633e86a932b71334', 'fsh_herringbone_flash_paint.png': '0c10465e38dc8c8ef492dafbfb8257a2012ff7c3a0df9358c571429d489b16b4', 'fsh_herringbone_flash_spec.png': '4ceff4531f7d97d9b016f5ae636e0c870776a749904961e261627302da78830f', 'fsh_hex_resonance_paint.png': '4d55ca0a966ede3dea77098ed2254a38fa2fed4cab90c54d886fd35edc57c230', 'fsh_hex_resonance_spec.png': '449b4229fab34510c680357ea39357c19b0274de5ea9366a9e19034041947046'}
IDENTITY_CONTRACTS.update({'fsh_spectral_silver': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_spectral_silver', 'display_name': 'Spectral Silver — FRACTURED SHOKK', 'promise': 'Fine split triangular prism facets reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'split triangular prism facets with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each split triangular prism facets feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'prism face', 'role': 'prism face defines one distinct material-bearing feature'}, {'name': 'silver shoulder', 'role': 'silver shoulder defines one distinct material-bearing feature'}, {'name': 'cut ridge', 'role': 'cut ridge defines one distinct material-bearing feature'}, {'name': 'etched pocket', 'role': 'etched pocket defines one distinct material-bearing feature'}, {'name': 'facet tip', 'role': 'facet tip defines one distinct material-bearing feature'}], 'material_binding': {'M': ['prism face', 'silver shoulder', 'cut ridge', 'etched pocket', 'facet tip'], 'R': ['prism face', 'silver shoulder', 'cut ridge', 'etched pocket', 'facet tip'], 'Cc': ['prism face', 'silver shoulder', 'cut ridge', 'etched pocket', 'facet tip']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original split triangular prism facets instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['split triangular faces', 'bright silver shoulders', 'thin diagonal cut ridges'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:spectral_silver:split triangular prism facets', 'spec_key': 'fsh20:spectral_silver:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'a5eacd408111ec5adf67d5cdf43c22dd06d4596d7e3ed017fcd5a6d096e3d65f', 'spec': '11cad3a9a3c81d233c1b7a92726b73173296eb890db385557123ea6461eef204'}}, 'fsh_ribbon_refraction': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_ribbon_refraction', 'display_name': 'Ribbon Refraction — FRACTURED SHOKK', 'promise': 'Fine segmented bowed optical ribbons reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'segmented bowed optical ribbons with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each segmented bowed optical ribbons feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'ribbon body', 'role': 'ribbon body defines one distinct material-bearing feature'}, {'name': 'bowed edge', 'role': 'bowed edge defines one distinct material-bearing feature'}, {'name': 'end cap', 'role': 'end cap defines one distinct material-bearing feature'}, {'name': 'cross notch', 'role': 'cross notch defines one distinct material-bearing feature'}, {'name': 'gap enamel', 'role': 'gap enamel defines one distinct material-bearing feature'}], 'material_binding': {'M': ['ribbon body', 'bowed edge', 'end cap', 'cross notch', 'gap enamel'], 'R': ['ribbon body', 'bowed edge', 'end cap', 'cross notch', 'gap enamel'], 'Cc': ['ribbon body', 'bowed edge', 'end cap', 'cross notch', 'gap enamel']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original segmented bowed optical ribbons instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['bowed segmented tapes', 'contrasting end caps', 'alternating raised ribbon edges'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:ribbon_refraction:segmented bowed optical ribbons', 'spec_key': 'fsh20:ribbon_refraction:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'ca48e76abac43d335b1cfffc59948654fce1d6b705d00e3caf8080812bdb7904', 'spec': '61620a567cfc30b3ec117488d70230a3eee39f2193e98221ddbe68b3f9a843bc'}}, 'fsh_chromatic_comb': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_chromatic_comb', 'display_name': 'Chromatic Comb — FRACTURED SHOKK', 'promise': 'Fine interdigitated offset comb teeth reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'interdigitated offset comb teeth with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each interdigitated offset comb teeth feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'comb spine', 'role': 'comb spine defines one distinct material-bearing feature'}, {'name': 'long tooth', 'role': 'long tooth defines one distinct material-bearing feature'}, {'name': 'short tooth', 'role': 'short tooth defines one distinct material-bearing feature'}, {'name': 'tooth root', 'role': 'tooth root defines one distinct material-bearing feature'}, {'name': 'groove bed', 'role': 'groove bed defines one distinct material-bearing feature'}], 'material_binding': {'M': ['comb spine', 'long tooth', 'short tooth', 'tooth root', 'groove bed'], 'R': ['comb spine', 'long tooth', 'short tooth', 'tooth root', 'groove bed'], 'Cc': ['comb spine', 'long tooth', 'short tooth', 'tooth root', 'groove bed']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original interdigitated offset comb teeth instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['interdigitated vertical teeth', 'crossing horizontal spines', 'recessed comb gaps'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:chromatic_comb:interdigitated offset comb teeth', 'spec_key': 'fsh20:chromatic_comb:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'c8fc87b4ab1c55e3558fa4a11d2c5317626389311aa13bd1ab8e44cc6ea0bf02', 'spec': 'e11bf270f207008508f25d068dd8014882530565b74143d9a2434c19dafb6b04'}}, 'fsh_opal_fault': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_opal_fault', 'display_name': 'Opal Fault — FRACTURED SHOKK', 'promise': 'Fine irregular nearest-seed mineral cells reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'irregular nearest-seed mineral cells with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each irregular nearest-seed mineral cells feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'opal body', 'role': 'opal body defines one distinct material-bearing feature'}, {'name': 'fault wall', 'role': 'fault wall defines one distinct material-bearing feature'}, {'name': 'mineral rim', 'role': 'mineral rim defines one distinct material-bearing feature'}, {'name': 'inclusion', 'role': 'inclusion defines one distinct material-bearing feature'}, {'name': 'triple junction', 'role': 'triple junction defines one distinct material-bearing feature'}], 'material_binding': {'M': ['opal body', 'fault wall', 'mineral rim', 'inclusion', 'triple junction'], 'R': ['opal body', 'fault wall', 'mineral rim', 'inclusion', 'triple junction'], 'Cc': ['opal body', 'fault wall', 'mineral rim', 'inclusion', 'triple junction']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original irregular nearest-seed mineral cells instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['irregular mineral cells', 'bright cell walls', 'enclosed inclusions'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:opal_fault:irregular nearest-seed mineral cells', 'spec_key': 'fsh20:opal_fault:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '8f9d45b047fc97e682405399a78ca31284c5da84c3c5671f931d60d41061f8ec', 'spec': 'e6561c582fc2c4b2ad525d5b6a20afa478d411ae6100f2606cc2b701cac0fba8'}}, 'fsh_nacre_cascade': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_nacre_cascade', 'display_name': 'Nacre Cascade — FRACTURED SHOKK', 'promise': 'Fine staggered nested shell fans reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'staggered nested shell fans with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each staggered nested shell fans feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'shell lip', 'role': 'shell lip defines one distinct material-bearing feature'}, {'name': 'shell bowl', 'role': 'shell bowl defines one distinct material-bearing feature'}, {'name': 'growth ring', 'role': 'growth ring defines one distinct material-bearing feature'}, {'name': 'hinge', 'role': 'hinge defines one distinct material-bearing feature'}, {'name': 'overlap shadow', 'role': 'overlap shadow defines one distinct material-bearing feature'}], 'material_binding': {'M': ['shell lip', 'shell bowl', 'growth ring', 'hinge', 'overlap shadow'], 'R': ['shell lip', 'shell bowl', 'growth ring', 'hinge', 'overlap shadow'], 'Cc': ['shell lip', 'shell bowl', 'growth ring', 'hinge', 'overlap shadow']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original staggered nested shell fans instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['overlapping shell fans', 'nested growth arcs', 'small dark hinge bowls'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:nacre_cascade:staggered nested shell fans', 'spec_key': 'fsh20:nacre_cascade:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '0fe4faf582e3255cddcc6eb44bc9d74d5970bfd5247637d121a43382353d3a1a', 'spec': '7e96658a479a10f1635972bc9ad03fd944d6c37e3a1908bae67bb9f30a4e25af'}}, 'fsh_quasicrystal_fire': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_quasicrystal_fire', 'display_name': 'Quasicrystal Fire — FRACTURED SHOKK', 'promise': 'Fine five-axis aperiodic interference crystals reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'five-axis aperiodic interference crystals with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each five-axis aperiodic interference crystals feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'crystal island', 'role': 'crystal island defines one distinct material-bearing feature'}, {'name': 'node', 'role': 'node defines one distinct material-bearing feature'}, {'name': 'crossing', 'role': 'crossing defines one distinct material-bearing feature'}, {'name': 'low saddle', 'role': 'low saddle defines one distinct material-bearing feature'}, {'name': 'crystal rim', 'role': 'crystal rim defines one distinct material-bearing feature'}], 'material_binding': {'M': ['crystal island', 'node', 'crossing', 'low saddle', 'crystal rim'], 'R': ['crystal island', 'node', 'crossing', 'low saddle', 'crystal rim'], 'Cc': ['crystal island', 'node', 'crossing', 'low saddle', 'crystal rim']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original five-axis aperiodic interference crystals instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['aperiodic crystal islands', 'five-direction crossings', 'curved interlocking rims'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:quasicrystal_fire:five-axis aperiodic interference crystals', 'spec_key': 'fsh20:quasicrystal_fire:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'b7d3213949d488fe4f4a14486ece2fe350c08e5b9f0b437156f0c40fbf4ffb22', 'spec': '3cb7695a1e0352f0284bcaea52b9b0e724e6d7c440ecd16e5983b7838d715503'}}, 'fsh_rosette_engine': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_rosette_engine', 'display_name': 'Rosette Engine — FRACTURED SHOKK', 'promise': 'Fine eight-lobed engraved rosettes reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'eight-lobed engraved rosettes with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each eight-lobed engraved rosettes feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'petal crest', 'role': 'petal crest defines one distinct material-bearing feature'}, {'name': 'petal trough', 'role': 'petal trough defines one distinct material-bearing feature'}, {'name': 'medallion', 'role': 'medallion defines one distinct material-bearing feature'}, {'name': 'radial notch', 'role': 'radial notch defines one distinct material-bearing feature'}, {'name': 'interstice', 'role': 'interstice defines one distinct material-bearing feature'}], 'material_binding': {'M': ['petal crest', 'petal trough', 'medallion', 'radial notch', 'interstice'], 'R': ['petal crest', 'petal trough', 'medallion', 'radial notch', 'interstice'], 'Cc': ['petal crest', 'petal trough', 'medallion', 'radial notch', 'interstice']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original eight-lobed engraved rosettes instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['eight-lobed rosettes', 'central medallions', 'staggered engraved floral rings'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:rosette_engine:eight-lobed engraved rosettes', 'spec_key': 'fsh20:rosette_engine:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '69ce8609846f9e1d772992647c167bbcd41e15cf2f832f339b59351778749bfd', 'spec': '12509a7f2f961d119c6b79c40dc53fa6637815c7e8f968ed782a7940982cc599'}}, 'fsh_diamond_fold': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_diamond_fold', 'display_name': 'Diamond Fold — FRACTURED SHOKK', 'promise': 'Fine opposed concave diamond foil folds reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'opposed concave diamond foil folds with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each opposed concave diamond foil folds feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'fold face', 'role': 'fold face defines one distinct material-bearing feature'}, {'name': 'ridge', 'role': 'ridge defines one distinct material-bearing feature'}, {'name': 'valley', 'role': 'valley defines one distinct material-bearing feature'}, {'name': 'crease point', 'role': 'crease point defines one distinct material-bearing feature'}, {'name': 'foil shoulder', 'role': 'foil shoulder defines one distinct material-bearing feature'}], 'material_binding': {'M': ['fold face', 'ridge', 'valley', 'crease point', 'foil shoulder'], 'R': ['fold face', 'ridge', 'valley', 'crease point', 'foil shoulder'], 'Cc': ['fold face', 'ridge', 'valley', 'crease point', 'foil shoulder']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original opposed concave diamond foil folds instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['opposed diamond planes', 'central creases', 'alternating valley and ridge faces'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:diamond_fold:opposed concave diamond foil folds', 'spec_key': 'fsh20:diamond_fold:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '36388b1cf0e9b664c739b85e94c5a6850f0dd9c1cf8223d436e7e6d45c626324', 'spec': 'a357188bfdb4547d2b5f82c93652f3f44cc3d1101897d172ceec441ae8f1651c'}}, 'fsh_frost_voltage': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_frost_voltage', 'display_name': 'Frost Voltage — FRACTURED SHOKK', 'promise': 'Fine six-armed branched ice dendrites reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'six-armed branched ice dendrites with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each six-armed branched ice dendrites feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'ice trunk', 'role': 'ice trunk defines one distinct material-bearing feature'}, {'name': 'branch', 'role': 'branch defines one distinct material-bearing feature'}, {'name': 'branch tip', 'role': 'branch tip defines one distinct material-bearing feature'}, {'name': 'hub', 'role': 'hub defines one distinct material-bearing feature'}, {'name': 'frost ground', 'role': 'frost ground defines one distinct material-bearing feature'}], 'material_binding': {'M': ['ice trunk', 'branch', 'branch tip', 'hub', 'frost ground'], 'R': ['ice trunk', 'branch', 'branch tip', 'hub', 'frost ground'], 'Cc': ['ice trunk', 'branch', 'branch tip', 'hub', 'frost ground']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original six-armed branched ice dendrites instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['six-armed dendrites', 'forked side branches', 'small central hubs'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:frost_voltage:six-armed branched ice dendrites', 'spec_key': 'fsh20:frost_voltage:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'b847601631a2a65027320e482247e125561686c110876de80c5b9cc55179e445', 'spec': '92d2c3f57d02b83334a60d22dbdf9e7edc529dd2fae2ced4c1452d33cf3f7c1f'}}, 'fsh_photon_circuit': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_photon_circuit', 'display_name': 'Photon Circuit — FRACTURED SHOKK', 'promise': 'Fine alternating right-angle optical traces reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'alternating right-angle optical traces with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each alternating right-angle optical traces feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'trace', 'role': 'trace defines one distinct material-bearing feature'}, {'name': 'elbow', 'role': 'elbow defines one distinct material-bearing feature'}, {'name': 'terminal', 'role': 'terminal defines one distinct material-bearing feature'}, {'name': 'contact pad', 'role': 'contact pad defines one distinct material-bearing feature'}, {'name': 'insulator', 'role': 'insulator defines one distinct material-bearing feature'}], 'material_binding': {'M': ['trace', 'elbow', 'terminal', 'contact pad', 'insulator'], 'R': ['trace', 'elbow', 'terminal', 'contact pad', 'insulator'], 'Cc': ['trace', 'elbow', 'terminal', 'contact pad', 'insulator']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original alternating right-angle optical traces instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['right-angle traces', 'contrasting contact pads', 'dark insulating pockets'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:photon_circuit:alternating right-angle optical traces', 'spec_key': 'fsh20:photon_circuit:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'd2489246ad21681e3722226b79e674c4d3aec64e76c2951d883e3e823bf608b4', 'spec': 'd195dc1a90aeef4eb32c4d2970a1f197ba6ccb253e11d71dda92e0b320fca413'}}, 'fsh_caustic_lens': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_caustic_lens', 'display_name': 'Caustic Lens — FRACTURED SHOKK', 'promise': 'Fine offset asymmetric elliptical lenslets reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'offset asymmetric elliptical lenslets with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each offset asymmetric elliptical lenslets feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'lens well', 'role': 'lens well defines one distinct material-bearing feature'}, {'name': 'inner caustic', 'role': 'inner caustic defines one distinct material-bearing feature'}, {'name': 'outer rim', 'role': 'outer rim defines one distinct material-bearing feature'}, {'name': 'focus', 'role': 'focus defines one distinct material-bearing feature'}, {'name': 'lens gap', 'role': 'lens gap defines one distinct material-bearing feature'}], 'material_binding': {'M': ['lens well', 'inner caustic', 'outer rim', 'focus', 'lens gap'], 'R': ['lens well', 'inner caustic', 'outer rim', 'focus', 'lens gap'], 'Cc': ['lens well', 'inner caustic', 'outer rim', 'focus', 'lens gap']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original offset asymmetric elliptical lenslets instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['elliptical lens bowls', 'nested colored caustic rims', 'offset focus glints'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:caustic_lens:offset asymmetric elliptical lenslets', 'spec_key': 'fsh20:caustic_lens:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'e56c19084dc8cf9b8d75da6430b8aa5d8a3483acf46a3403c0dc2acae408d332', 'spec': '2cead5f93d4b52c951831637d89968367d34a770b79e5928ee89234aa0a27207'}}, 'fsh_spectral_satin': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_spectral_satin', 'display_name': 'Spectral Satin — FRACTURED SHOKK', 'promise': 'Fine three-over-one interlaced optical tapes reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'three-over-one interlaced optical tapes with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each three-over-one interlaced optical tapes feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'warp', 'role': 'warp defines one distinct material-bearing feature'}, {'name': 'weft', 'role': 'weft defines one distinct material-bearing feature'}, {'name': 'crossover', 'role': 'crossover defines one distinct material-bearing feature'}, {'name': 'fiber channel', 'role': 'fiber channel defines one distinct material-bearing feature'}, {'name': 'selvedge', 'role': 'selvedge defines one distinct material-bearing feature'}], 'material_binding': {'M': ['warp', 'weft', 'crossover', 'fiber channel', 'selvedge'], 'R': ['warp', 'weft', 'crossover', 'fiber channel', 'selvedge'], 'Cc': ['warp', 'weft', 'crossover', 'fiber channel', 'selvedge']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original three-over-one interlaced optical tapes instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['fine interlaced tapes', 'regular over-under crossovers', 'directional fiber channels'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:spectral_satin:three-over-one interlaced optical tapes', 'spec_key': 'fsh20:spectral_satin:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '1e3c3751dafa06d2167e390f58fb3ace5962f1a85cce5d231e106726393fd968', 'spec': '83b7303bc44643d52d61a0b4bc9cb17eef3417b92e33c3cbe8f02873e2e88857'}}, 'fsh_meteor_wake': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_meteor_wake', 'display_name': 'Meteor Wake — FRACTURED SHOKK', 'promise': 'Fine staggered tapered comet wakes reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'staggered tapered comet wakes with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each staggered tapered comet wakes feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'meteor head', 'role': 'meteor head defines one distinct material-bearing feature'}, {'name': 'split tail', 'role': 'split tail defines one distinct material-bearing feature'}, {'name': 'wake', 'role': 'wake defines one distinct material-bearing feature'}, {'name': 'shoulder', 'role': 'shoulder defines one distinct material-bearing feature'}, {'name': 'dark pocket', 'role': 'dark pocket defines one distinct material-bearing feature'}], 'material_binding': {'M': ['meteor head', 'split tail', 'wake', 'shoulder', 'dark pocket'], 'R': ['meteor head', 'split tail', 'wake', 'shoulder', 'dark pocket'], 'Cc': ['meteor head', 'split tail', 'wake', 'shoulder', 'dark pocket']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original staggered tapered comet wakes instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['tapering wake triangles', 'rounded leading regions', 'split trailing channels'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:meteor_wake:staggered tapered comet wakes', 'spec_key': 'fsh20:meteor_wake:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '990277e4b5d2e48616c96e6cfd53a308c6eeee37e0c02480e029763eca12b051', 'spec': 'c44647bc855bec1fd5d447ef1a393d93f4f146c91309604d3e9f05efece8d8b5'}}, 'fsh_ferro_crown': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_ferro_crown', 'display_name': 'Ferro Crown — FRACTURED SHOKK', 'promise': 'Fine five-point fluid crowns with rounded basins reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'five-point fluid crowns with rounded basins with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each five-point fluid crowns with rounded basins feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'spike', 'role': 'spike defines one distinct material-bearing feature'}, {'name': 'basin', 'role': 'basin defines one distinct material-bearing feature'}, {'name': 'crown lip', 'role': 'crown lip defines one distinct material-bearing feature'}, {'name': 'central bead', 'role': 'central bead defines one distinct material-bearing feature'}, {'name': 'magnetic saddle', 'role': 'magnetic saddle defines one distinct material-bearing feature'}], 'material_binding': {'M': ['spike', 'basin', 'crown lip', 'central bead', 'magnetic saddle'], 'R': ['spike', 'basin', 'crown lip', 'central bead', 'magnetic saddle'], 'Cc': ['spike', 'basin', 'crown lip', 'central bead', 'magnetic saddle']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original five-point fluid crowns with rounded basins instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['five-point fluid crowns', 'rounded central basins', 'contrasting crown lips'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:ferro_crown:five-point fluid crowns with rounded basins', 'spec_key': 'fsh20:ferro_crown:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'bd6425c6bfeae038cbd748cef814ddb19a1c5f128b55c49bf5ecbd1c2b1462df', 'spec': 'dc696593dd49eb3e222253a22d7a49f9f8ee84d74425dd1cb649f856807f5667'}}, 'fsh_isobar_chrome': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_isobar_chrome', 'display_name': 'Isobar Chrome — FRACTURED SHOKK', 'promise': 'Fine labyrinthine broken contour terraces reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'labyrinthine broken contour terraces with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each labyrinthine broken contour terraces feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'terrace', 'role': 'terrace defines one distinct material-bearing feature'}, {'name': 'contour', 'role': 'contour defines one distinct material-bearing feature'}, {'name': 'saddle', 'role': 'saddle defines one distinct material-bearing feature'}, {'name': 'crest', 'role': 'crest defines one distinct material-bearing feature'}, {'name': 'cut bank', 'role': 'cut bank defines one distinct material-bearing feature'}], 'material_binding': {'M': ['terrace', 'contour', 'saddle', 'crest', 'cut bank'], 'R': ['terrace', 'contour', 'saddle', 'crest', 'cut bank'], 'Cc': ['terrace', 'contour', 'saddle', 'crest', 'cut bank']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original labyrinthine broken contour terraces instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['concentric contour terraces', 'saddles joining contours', 'sharply separated contour banks'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:isobar_chrome:labyrinthine broken contour terraces', 'spec_key': 'fsh20:isobar_chrome:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': 'a2a875dca5f56d8914a578180bb91ff4195b5133bf43f07ec036443e4d5b38fc', 'spec': '63261fc9af84f62e36d65a72bba71c13b95901df1d189900c7094063d1f682bc'}}, 'fsh_crystal_needle': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_crystal_needle', 'display_name': 'Crystal Needle — FRACTURED SHOKK', 'promise': 'Fine crossed acicular crystal bundles reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'crossed acicular crystal bundles with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each crossed acicular crystal bundles feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'needle body', 'role': 'needle body defines one distinct material-bearing feature'}, {'name': 'cleavage', 'role': 'cleavage defines one distinct material-bearing feature'}, {'name': 'needle tip', 'role': 'needle tip defines one distinct material-bearing feature'}, {'name': 'crossing', 'role': 'crossing defines one distinct material-bearing feature'}, {'name': 'matrix', 'role': 'matrix defines one distinct material-bearing feature'}], 'material_binding': {'M': ['needle body', 'cleavage', 'needle tip', 'crossing', 'matrix'], 'R': ['needle body', 'cleavage', 'needle tip', 'crossing', 'matrix'], 'Cc': ['needle body', 'cleavage', 'needle tip', 'crossing', 'matrix']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original crossed acicular crystal bundles instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['crossing long narrow needles', 'diagonal cleavage lines', 'crystal tips within a matrix'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:crystal_needle:crossed acicular crystal bundles', 'spec_key': 'fsh20:crystal_needle:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '0e179947332c9c343786ccc18e7ea3dded0509034adc6323735bf306c6a08f55', 'spec': '74e9ca3b8cca7257c6eb77341b732fa0124a07b3a2789d7fc133f0d813dda007'}}, 'fsh_bubble_spectrum': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_bubble_spectrum', 'display_name': 'Bubble Spectrum — FRACTURED SHOKK', 'promise': 'Fine polydisperse concentric film bubbles reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'polydisperse concentric film bubbles with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each polydisperse concentric film bubbles feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'film bowl', 'role': 'film bowl defines one distinct material-bearing feature'}, {'name': 'film rim', 'role': 'film rim defines one distinct material-bearing feature'}, {'name': 'inner ring', 'role': 'inner ring defines one distinct material-bearing feature'}, {'name': 'contact glint', 'role': 'contact glint defines one distinct material-bearing feature'}, {'name': 'interstitial film', 'role': 'interstitial film defines one distinct material-bearing feature'}], 'material_binding': {'M': ['film bowl', 'film rim', 'inner ring', 'contact glint', 'interstitial film'], 'R': ['film bowl', 'film rim', 'inner ring', 'contact glint', 'interstitial film'], 'Cc': ['film bowl', 'film rim', 'inner ring', 'contact glint', 'interstitial film']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original polydisperse concentric film bubbles instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['bubbles of varying diameter', 'inner film rings', 'isolated contact glints'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:bubble_spectrum:polydisperse concentric film bubbles', 'spec_key': 'fsh20:bubble_spectrum:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '3f42953e2717fc0664f80c4f8f6386ce0d0fa5b42e67e554742da3373d089400', 'spec': '75de7a441ce242621c564026f0f8fc9735c397589eff3d44da1b1268e30cb121'}}, 'fsh_iris_turbine': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_iris_turbine', 'display_name': 'Iris Turbine — FRACTURED SHOKK', 'promise': 'Fine curved seven-blade micro turbines reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'curved seven-blade micro turbines with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each curved seven-blade micro turbines feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'blade', 'role': 'blade defines one distinct material-bearing feature'}, {'name': 'blade edge', 'role': 'blade edge defines one distinct material-bearing feature'}, {'name': 'hub', 'role': 'hub defines one distinct material-bearing feature'}, {'name': 'sweep groove', 'role': 'sweep groove defines one distinct material-bearing feature'}, {'name': 'interblade pocket', 'role': 'interblade pocket defines one distinct material-bearing feature'}], 'material_binding': {'M': ['blade', 'blade edge', 'hub', 'sweep groove', 'interblade pocket'], 'R': ['blade', 'blade edge', 'hub', 'sweep groove', 'interblade pocket'], 'Cc': ['blade', 'blade edge', 'hub', 'sweep groove', 'interblade pocket']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original curved seven-blade micro turbines instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['seven curved turbine blades', 'round central hubs', 'spiral interblade channels'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:iris_turbine:curved seven-blade micro turbines', 'spec_key': 'fsh20:iris_turbine:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '5f507ea9689fbdcdfa141ab0c79ff20c3071263cadba831457f284b26aea50a2', 'spec': 'c98fb477f06c0419be366555074e545ec30a56f31dd94cd2633e86a932b71334'}}, 'fsh_herringbone_flash': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_herringbone_flash', 'display_name': 'Herringbone Flash — FRACTURED SHOKK', 'promise': 'Fine interlocked angular optical parquet reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'interlocked angular optical parquet with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each interlocked angular optical parquet feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'left plank', 'role': 'left plank defines one distinct material-bearing feature'}, {'name': 'right plank', 'role': 'right plank defines one distinct material-bearing feature'}, {'name': 'bevel', 'role': 'bevel defines one distinct material-bearing feature'}, {'name': 'end grain', 'role': 'end grain defines one distinct material-bearing feature'}, {'name': 'joint', 'role': 'joint defines one distinct material-bearing feature'}], 'material_binding': {'M': ['left plank', 'right plank', 'bevel', 'end grain', 'joint'], 'R': ['left plank', 'right plank', 'bevel', 'end grain', 'joint'], 'Cc': ['left plank', 'right plank', 'bevel', 'end grain', 'joint']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original interlocked angular optical parquet instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['interlocked short planks', 'zigzag herringbone joints', 'opposed plank directions'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:herringbone_flash:interlocked angular optical parquet', 'spec_key': 'fsh20:herringbone_flash:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '0c10465e38dc8c8ef492dafbfb8257a2012ff7c3a0df9358c571429d489b16b4', 'spec': '4ceff4531f7d97d9b016f5ae636e0c870776a749904961e261627302da78830f'}}, 'fsh_hex_resonance': {'schema': 'spb-finish-identity/1', 'finish_id': 'fsh_hex_resonance', 'display_name': 'Hex Resonance — FRACTURED SHOKK', 'promise': 'Fine offset hexagonal resonators with split centers reveal saturated metallic reflections as illumination changes.', 'carrier_grammar': 'offset hexagonal resonators with split centers with five separate geometric feature masks and eight local material tiers.', 'spec_grammar': 'Each offset hexagonal resonators with split centers feature owns a metallic/rough/coat response tied to its visible boundaries.', 'reference_physics': {'mechanism': 'Fixed pigments tint metallic reflections; roughness shapes lobes and clearcoat controls the white overlay. This approximates spectral light play, not physical wavelength diffraction.', 'sources': ['SPB_WIKI.html#spec_guide', 'https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']}, 'native_scale_px': [8, 32], 'mark_types': [{'name': 'hex wall', 'role': 'hex wall defines one distinct material-bearing feature'}, {'name': 'resonator bowl', 'role': 'resonator bowl defines one distinct material-bearing feature'}, {'name': 'split center', 'role': 'split center defines one distinct material-bearing feature'}, {'name': 'vertex', 'role': 'vertex defines one distinct material-bearing feature'}, {'name': 'outer gasket', 'role': 'outer gasket defines one distinct material-bearing feature'}], 'material_binding': {'M': ['hex wall', 'resonator bowl', 'split center', 'vertex', 'outer gasket'], 'R': ['hex wall', 'resonator bowl', 'split center', 'vertex', 'outer gasket'], 'Cc': ['hex wall', 'resonator bowl', 'split center', 'vertex', 'outer gasket']}, 'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], 'nearest_neighbors': [{'finish_id': 'xlab_hologram_metal', 'difference': 'Original offset hexagonal resonators with split centers instead of rotated square plates.'}, {'finish_id': 'hou_veiled_skull', 'difference': 'All-over optical surface rather than a concealed skull silhouette.'}], 'name_truth': {'hidden_title_verdict': 'pass', 'visible_evidence': ['hexagonal bowls', 'split resonator centers', 'contrasting outer gaskets'], 'evidence_scope': 'Agent structural recognition at native crop and whole sheet,2026-09-18; no owner acceptance or in-sim motion verdict implied.'}, 'construction_key': 'fsh20:hex_resonance:offset hexagonal resonators with split centers', 'spec_key': 'fsh20:hex_resonance:feature-bound-eight-tier-PBR', 'review_asset_sha256': {'paint': '4d55ca0a966ede3dea77098ed2254a38fa2fed4cab90c54d886fd35edc57c230', 'spec': '449b4229fab34510c680357ea39357c19b0274de5ea9366a9e19034041947046'}}})

# OWNER_REJECTION_R1_GLOBAL / SPB-105 / FSH-R2 / 2026-09-18.
# Owner: "not at ALL doing what the car in his example was doing."
# Prior M7 scores are historical; owner rejects the promised effect.
for _rejected_contract in IDENTITY_CONTRACTS.values():
    _rejected_contract['owner_review'] = {'verdict':'reject','date':'2026-09-18','reason':'First direction misses reference motion; full reset.'}
    _rejected_contract['name_truth']['hidden_title_verdict'] = 'fail'

# FSH-R3 NONBAND DEVELOPMENT / SPB-105 / 2026-09-18
# FSH-R3-COLOR: owner requests the whole rainbow and shades within each family.
# Twenty-eight pigment anchors; spec unchanged. M7 pending -> pending.
# Owner: "Prizms, other gradient types, grunge, paintbrush effects ... NOT bands".
# Only these four rejected R1 assets are superseded; the other sixteen stay rejected.
R3_NAMES = {'fsh_frost_voltage': 'Chromatic Grunge',
 'fsh_opal_fault': 'Opal Bloom',
 'fsh_ribbon_refraction': 'Brushed Spectrum',
 'fsh_spectral_silver': 'Prism Shards'}
R3_DESCRIPTIONS = {'fsh_frost_voltage': 'Irregular pitted and abraded multicolor metal reveal localized spectral highlights '
                      'without repeated rainbow bands. R3 development: in-game validation and owner review '
                      'pending.',
 'fsh_opal_fault': 'Irregular overlapping irregular mineral blooms reveal localized spectral highlights '
                   'without repeated rainbow bands. R3 development: in-game validation and owner review '
                   'pending.',
 'fsh_ribbon_refraction': 'Irregular layered short paintbrush strokes reveal localized spectral highlights '
                          'without repeated rainbow bands. R3 development: in-game validation and owner '
                          'review pending.',
 'fsh_spectral_silver': 'Irregular irregular angular prism chips reveal localized spectral highlights '
                        'without repeated rainbow bands. R3 development: in-game validation and owner review '
                        'pending.'}
ASSET_SHA256.update({'fsh_spectral_silver_paint.png': '9e7c8f1ce24836c86a3184b6ff0c766e5a2155b08b38fdfd5f2302261174e53b',
 'fsh_spectral_silver_spec.png': '6533e5abbd3593bafff9f695e874762b92c38c1951197e1a4b895067a054c7b3',
 'fsh_ribbon_refraction_paint.png': '769b2f393412d1d331e97a71a0f70b35cf5eb6b3f4f8bc1ef2e41a1ea1f4c8f5',
 'fsh_ribbon_refraction_spec.png': 'c571f9b9a201de0bae1b6e64d8838d0c870b76c617f9df67840a88380f58a9f6',
 'fsh_frost_voltage_paint.png': 'f74c02504a67e53c0c4c4666e8a0041452b029875b52a03595f2627a3fa6a489',
 'fsh_frost_voltage_spec.png': 'c7a642c0a4449c5bef960b3bc805fa02083b3d4d6cfaa70e62bea286cce2ca99',
 'fsh_opal_fault_paint.png': '8c3f370c130b392b07f5de017774dee00be500f5081eff03be466db0c17f126e',
 'fsh_opal_fault_spec.png': 'e9d57de46dd0884056989cee713eb56b58355d8ff0742eb874b40b4efdbd15a5'})
IDENTITY_CONTRACTS.update({'fsh_spectral_silver': {'schema': 'spb-finish-identity/1',
                         'finish_id': 'fsh_spectral_silver',
                         'display_name': 'Prism Shards — FRACTURED SHOKK prototype',
                         'promise': 'Irregular irregular angular prism chips reveal localized spectral '
                                    'highlights without repeated rainbow bands.',
                         'carrier_grammar': 'irregular angular prism chips with five overlapping '
                                            'purpose-built material features and nonperiodic chromatic '
                                            'gradients.',
                         'spec_grammar': 'Each named irregular angular prism chips feature has a separate '
                                         'eight-tier response near the actual-game spectral-metal window.',
                         'reference_physics': {'mechanism': 'Fixed saturated pigment tints metallic '
                                                            'reflections. Roughness and clearcoat determine '
                                                            'highlight response. Actual-game calibration '
                                                            'anchor255/40/218; no physical wavelength '
                                                            'diffraction or animated paint claimed.',
                                               'sources': ['R2_MECHANISM/DAYLIGHT_BREAKTHROUGH.md']},
                         'native_scale_px': [8, 32],
                         'mark_types': [{'name': 'prism face',
                                         'role': 'prism face owns a visible material-bearing part of this '
                                                 'construction'},
                                        {'name': 'cut shoulder',
                                         'role': 'cut shoulder owns a visible material-bearing part of this '
                                                 'construction'},
                                        {'name': 'split face',
                                         'role': 'split face owns a visible material-bearing part of this '
                                                 'construction'},
                                        {'name': 'buried chip',
                                         'role': 'buried chip owns a visible material-bearing part of this '
                                                 'construction'},
                                        {'name': 'point glint',
                                         'role': 'point glint owns a visible material-bearing part of this '
                                                 'construction'}],
                         'material_binding': {'M': ['prism face',
                                                    'cut shoulder',
                                                    'split face',
                                                    'buried chip',
                                                    'point glint'],
                                              'R': ['prism face',
                                                    'cut shoulder',
                                                    'split face',
                                                    'buried chip',
                                                    'point glint'],
                                              'Cc': ['prism face',
                                                     'cut shoulder',
                                                     'split face',
                                                     'buried chip',
                                                     'point glint']},
                         'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92],
                         'nearest_neighbors': [{'finish_id': 'fsh_r3_brushed_spectrum',
                                                'difference': 'irregular angular prism chips versus layered '
                                                              'short paintbrush strokes'},
                                               {'finish_id': 'fsh_r3_chromatic_grunge',
                                                'difference': 'irregular angular prism chips versus pitted '
                                                              'and abraded multicolor metal'},
                                               {'finish_id': 'fsh_r3_opal_bloom',
                                                'difference': 'irregular angular prism chips versus '
                                                              'overlapping irregular mineral blooms'}],
                         'name_truth': {'hidden_title_verdict': 'pending',
                                        'visible_evidence': ['irregular angular prism chips',
                                                             'prism face',
                                                             'cut shoulder',
                                                             'split face',
                                                             'buried chip',
                                                             'point glint']},
                         'owner_review': {'verdict': 'pending',
                                          'instruction': 'NO BANDS; prisms, gradients, grunge, brushwork'},
                         'construction_key': 'fsh:r3:prism_shards',
                         'spec_key': 'fsh:r3:prism_shards:five-bound-feature-populations',
                         'development_status': 'R3 nonband proof; actual-game validation and owner review '
                                               'pending',
                         'previous_revision': {'id': 'R1',
                                               'verdict': 'reject',
                                               'reason': 'Owner rejected the promised light response'},
                         'qualification_errors': ["name_truth.hidden_title_verdict must be 'pass'"],
                         'review_asset_sha256': {'paint': '9e7c8f1ce24836c86a3184b6ff0c766e5a2155b08b38fdfd5f2302261174e53b',
                                                 'spec': '6533e5abbd3593bafff9f695e874762b92c38c1951197e1a4b895067a054c7b3'},
                         'palette_revision': {'date': '2026-09-18',
                                              'owner_request': 'whole rainbow; yellow orange pink purple '
                                                               'seafoam and shades within families',
                                              'anchors': [['scarlet', 0, 0.96],
                                                          ['ruby', 350, 0.92],
                                                          ['coral', 12, 0.68],
                                                          ['vermillion', 20, 0.95],
                                                          ['orange', 30, 0.96],
                                                          ['amber', 42, 0.91],
                                                          ['gold', 51, 0.95],
                                                          ['lemon', 61, 0.86],
                                                          ['chartreuse', 79, 0.86],
                                                          ['lime', 95, 0.92],
                                                          ['leaf green', 115, 0.85],
                                                          ['emerald', 140, 0.91],
                                                          ['jade', 155, 0.72],
                                                          ['seafoam', 162, 0.48],
                                                          ['mint', 147, 0.38],
                                                          ['turquoise', 176, 0.81],
                                                          ['cyan', 188, 0.93],
                                                          ['azure', 206, 0.91],
                                                          ['cobalt', 228, 0.93],
                                                          ['periwinkle', 245, 0.58],
                                                          ['violet', 266, 0.89],
                                                          ['lavender', 280, 0.48],
                                                          ['purple', 291, 0.87],
                                                          ['orchid', 309, 0.63],
                                                          ['fuchsia', 324, 0.93],
                                                          ['rose', 339, 0.55],
                                                          ['pink', 350, 0.42],
                                                          ['salmon', 9, 0.5]],
                                              'measured_coverage': {'hue_30_degree_percent': [15.328,
                                                                                              10.475,
                                                                                              6.823,
                                                                                              6.695,
                                                                                              7.211,
                                                                                              10.239,
                                                                                              7.353,
                                                                                              4.447,
                                                                                              6.383,
                                                                                              5.496,
                                                                                              8.37,
                                                                                              11.18],
                                                                    'seafoam_mint_percent': 6.071,
                                                                    'soft_pink_percent': 10.502,
                                                                    'lavender_percent': 4.741,
                                                                    'saturation_range': [0.269,
                                                                                         0.673,
                                                                                         0.932]},
                                              'spec_pixels_unchanged': True}},
 'fsh_ribbon_refraction': {'schema': 'spb-finish-identity/1',
                           'finish_id': 'fsh_ribbon_refraction',
                           'display_name': 'Brushed Spectrum — FRACTURED SHOKK prototype',
                           'promise': 'Irregular layered short paintbrush strokes reveal localized spectral '
                                      'highlights without repeated rainbow bands.',
                           'carrier_grammar': 'layered short paintbrush strokes with five overlapping '
                                              'purpose-built material features and nonperiodic chromatic '
                                              'gradients.',
                           'spec_grammar': 'Each named layered short paintbrush strokes feature has a '
                                           'separate eight-tier response near the actual-game spectral-metal '
                                           'window.',
                           'reference_physics': {'mechanism': 'Fixed saturated pigment tints metallic '
                                                              'reflections. Roughness and clearcoat '
                                                              'determine highlight response. Actual-game '
                                                              'calibration anchor255/40/218; no physical '
                                                              'wavelength diffraction or animated paint '
                                                              'claimed.',
                                                 'sources': ['R2_MECHANISM/DAYLIGHT_BREAKTHROUGH.md']},
                           'native_scale_px': [8, 32],
                           'mark_types': [{'name': 'stroke belly',
                                           'role': 'stroke belly owns a visible material-bearing part of '
                                                   'this construction'},
                                          {'name': 'dry bristle',
                                           'role': 'dry bristle owns a visible material-bearing part of this '
                                                   'construction'},
                                          {'name': 'loaded tip',
                                           'role': 'loaded tip owns a visible material-bearing part of this '
                                                   'construction'},
                                          {'name': 'cross stroke',
                                           'role': 'cross stroke owns a visible material-bearing part of '
                                                   'this construction'},
                                          {'name': 'feathered end',
                                           'role': 'feathered end owns a visible material-bearing part of '
                                                   'this construction'}],
                           'material_binding': {'M': ['stroke belly',
                                                      'dry bristle',
                                                      'loaded tip',
                                                      'cross stroke',
                                                      'feathered end'],
                                                'R': ['stroke belly',
                                                      'dry bristle',
                                                      'loaded tip',
                                                      'cross stroke',
                                                      'feathered end'],
                                                'Cc': ['stroke belly',
                                                       'dry bristle',
                                                       'loaded tip',
                                                       'cross stroke',
                                                       'feathered end']},
                           'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92],
                           'nearest_neighbors': [{'finish_id': 'fsh_r3_prism_shards',
                                                  'difference': 'layered short paintbrush strokes versus '
                                                                'irregular angular prism chips'},
                                                 {'finish_id': 'fsh_r3_chromatic_grunge',
                                                  'difference': 'layered short paintbrush strokes versus '
                                                                'pitted and abraded multicolor metal'},
                                                 {'finish_id': 'fsh_r3_opal_bloom',
                                                  'difference': 'layered short paintbrush strokes versus '
                                                                'overlapping irregular mineral blooms'}],
                           'name_truth': {'hidden_title_verdict': 'pending',
                                          'visible_evidence': ['layered short paintbrush strokes',
                                                               'stroke belly',
                                                               'dry bristle',
                                                               'loaded tip',
                                                               'cross stroke',
                                                               'feathered end']},
                           'owner_review': {'verdict': 'pending',
                                            'instruction': 'NO BANDS; prisms, gradients, grunge, brushwork'},
                           'construction_key': 'fsh:r3:brushed_spectrum',
                           'spec_key': 'fsh:r3:brushed_spectrum:five-bound-feature-populations',
                           'development_status': 'R3 nonband proof; actual-game validation and owner review '
                                                 'pending',
                           'previous_revision': {'id': 'R1',
                                                 'verdict': 'reject',
                                                 'reason': 'Owner rejected the promised light response'},
                           'qualification_errors': ["name_truth.hidden_title_verdict must be 'pass'"],
                           'review_asset_sha256': {'paint': '769b2f393412d1d331e97a71a0f70b35cf5eb6b3f4f8bc1ef2e41a1ea1f4c8f5',
                                                   'spec': 'c571f9b9a201de0bae1b6e64d8838d0c870b76c617f9df67840a88380f58a9f6'},
                           'palette_revision': {'date': '2026-09-18',
                                                'owner_request': 'whole rainbow; yellow orange pink purple '
                                                                 'seafoam and shades within families',
                                                'anchors': [['scarlet', 0, 0.96],
                                                            ['ruby', 350, 0.92],
                                                            ['coral', 12, 0.68],
                                                            ['vermillion', 20, 0.95],
                                                            ['orange', 30, 0.96],
                                                            ['amber', 42, 0.91],
                                                            ['gold', 51, 0.95],
                                                            ['lemon', 61, 0.86],
                                                            ['chartreuse', 79, 0.86],
                                                            ['lime', 95, 0.92],
                                                            ['leaf green', 115, 0.85],
                                                            ['emerald', 140, 0.91],
                                                            ['jade', 155, 0.72],
                                                            ['seafoam', 162, 0.48],
                                                            ['mint', 147, 0.38],
                                                            ['turquoise', 176, 0.81],
                                                            ['cyan', 188, 0.93],
                                                            ['azure', 206, 0.91],
                                                            ['cobalt', 228, 0.93],
                                                            ['periwinkle', 245, 0.58],
                                                            ['violet', 266, 0.89],
                                                            ['lavender', 280, 0.48],
                                                            ['purple', 291, 0.87],
                                                            ['orchid', 309, 0.63],
                                                            ['fuchsia', 324, 0.93],
                                                            ['rose', 339, 0.55],
                                                            ['pink', 350, 0.42],
                                                            ['salmon', 9, 0.5]],
                                                'measured_coverage': {'hue_30_degree_percent': [15.461,
                                                                                                14.413,
                                                                                                7.734,
                                                                                                7.12,
                                                                                                6.976,
                                                                                                8.136,
                                                                                                6.133,
                                                                                                4.861,
                                                                                                5.19,
                                                                                                5.559,
                                                                                                7.106,
                                                                                                11.311],
                                                                      'seafoam_mint_percent': 5.118,
                                                                      'soft_pink_percent': 10.379,
                                                                      'lavender_percent': 3.926,
                                                                      'saturation_range': [0.274,
                                                                                           0.667,
                                                                                           0.929]},
                                                'spec_pixels_unchanged': True}},
 'fsh_frost_voltage': {'schema': 'spb-finish-identity/1',
                       'finish_id': 'fsh_frost_voltage',
                       'display_name': 'Chromatic Grunge — FRACTURED SHOKK prototype',
                       'promise': 'Irregular pitted and abraded multicolor metal reveal localized spectral '
                                  'highlights without repeated rainbow bands.',
                       'carrier_grammar': 'pitted and abraded multicolor metal with five overlapping '
                                          'purpose-built material features and nonperiodic chromatic '
                                          'gradients.',
                       'spec_grammar': 'Each named pitted and abraded multicolor metal feature has a '
                                       'separate eight-tier response near the actual-game spectral-metal '
                                       'window.',
                       'reference_physics': {'mechanism': 'Fixed saturated pigment tints metallic '
                                                          'reflections. Roughness and clearcoat determine '
                                                          'highlight response. Actual-game calibration '
                                                          'anchor255/40/218; no physical wavelength '
                                                          'diffraction or animated paint claimed.',
                                             'sources': ['R2_MECHANISM/DAYLIGHT_BREAKTHROUGH.md']},
                       'native_scale_px': [8, 32],
                       'mark_types': [{'name': 'pit bowl',
                                       'role': 'pit bowl owns a visible material-bearing part of this '
                                               'construction'},
                                      {'name': 'scuffed rim',
                                       'role': 'scuffed rim owns a visible material-bearing part of this '
                                               'construction'},
                                      {'name': 'abrasion',
                                       'role': 'abrasion owns a visible material-bearing part of this '
                                               'construction'},
                                      {'name': 'oxide fleck',
                                       'role': 'oxide fleck owns a visible material-bearing part of this '
                                               'construction'},
                                      {'name': 'polished island',
                                       'role': 'polished island owns a visible material-bearing part of this '
                                               'construction'}],
                       'material_binding': {'M': ['pit bowl',
                                                  'scuffed rim',
                                                  'abrasion',
                                                  'oxide fleck',
                                                  'polished island'],
                                            'R': ['pit bowl',
                                                  'scuffed rim',
                                                  'abrasion',
                                                  'oxide fleck',
                                                  'polished island'],
                                            'Cc': ['pit bowl',
                                                   'scuffed rim',
                                                   'abrasion',
                                                   'oxide fleck',
                                                   'polished island']},
                       'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92],
                       'nearest_neighbors': [{'finish_id': 'fsh_r3_prism_shards',
                                              'difference': 'pitted and abraded multicolor metal versus '
                                                            'irregular angular prism chips'},
                                             {'finish_id': 'fsh_r3_brushed_spectrum',
                                              'difference': 'pitted and abraded multicolor metal versus '
                                                            'layered short paintbrush strokes'},
                                             {'finish_id': 'fsh_r3_opal_bloom',
                                              'difference': 'pitted and abraded multicolor metal versus '
                                                            'overlapping irregular mineral blooms'}],
                       'name_truth': {'hidden_title_verdict': 'pending',
                                      'visible_evidence': ['pitted and abraded multicolor metal',
                                                           'pit bowl',
                                                           'scuffed rim',
                                                           'abrasion',
                                                           'oxide fleck',
                                                           'polished island']},
                       'owner_review': {'verdict': 'pending',
                                        'instruction': 'NO BANDS; prisms, gradients, grunge, brushwork'},
                       'construction_key': 'fsh:r3:chromatic_grunge',
                       'spec_key': 'fsh:r3:chromatic_grunge:five-bound-feature-populations',
                       'development_status': 'R3 nonband proof; actual-game validation and owner review '
                                             'pending',
                       'previous_revision': {'id': 'R1',
                                             'verdict': 'reject',
                                             'reason': 'Owner rejected the promised light response'},
                       'qualification_errors': ["name_truth.hidden_title_verdict must be 'pass'"],
                       'review_asset_sha256': {'paint': 'f74c02504a67e53c0c4c4666e8a0041452b029875b52a03595f2627a3fa6a489',
                                               'spec': 'c7a642c0a4449c5bef960b3bc805fa02083b3d4d6cfaa70e62bea286cce2ca99'},
                       'palette_revision': {'date': '2026-09-18',
                                            'owner_request': 'whole rainbow; yellow orange pink purple '
                                                             'seafoam and shades within families',
                                            'anchors': [['scarlet', 0, 0.96],
                                                        ['ruby', 350, 0.92],
                                                        ['coral', 12, 0.68],
                                                        ['vermillion', 20, 0.95],
                                                        ['orange', 30, 0.96],
                                                        ['amber', 42, 0.91],
                                                        ['gold', 51, 0.95],
                                                        ['lemon', 61, 0.86],
                                                        ['chartreuse', 79, 0.86],
                                                        ['lime', 95, 0.92],
                                                        ['leaf green', 115, 0.85],
                                                        ['emerald', 140, 0.91],
                                                        ['jade', 155, 0.72],
                                                        ['seafoam', 162, 0.48],
                                                        ['mint', 147, 0.38],
                                                        ['turquoise', 176, 0.81],
                                                        ['cyan', 188, 0.93],
                                                        ['azure', 206, 0.91],
                                                        ['cobalt', 228, 0.93],
                                                        ['periwinkle', 245, 0.58],
                                                        ['violet', 266, 0.89],
                                                        ['lavender', 280, 0.48],
                                                        ['purple', 291, 0.87],
                                                        ['orchid', 309, 0.63],
                                                        ['fuchsia', 324, 0.93],
                                                        ['rose', 339, 0.55],
                                                        ['pink', 350, 0.42],
                                                        ['salmon', 9, 0.5]],
                                            'measured_coverage': {'hue_30_degree_percent': [14.616,
                                                                                            12.038,
                                                                                            6.97,
                                                                                            7.038,
                                                                                            7.537,
                                                                                            8.102,
                                                                                            5.142,
                                                                                            4.932,
                                                                                            5.863,
                                                                                            7.25,
                                                                                            7.951,
                                                                                            12.56],
                                                                  'seafoam_mint_percent': 5.537,
                                                                  'soft_pink_percent': 11.633,
                                                                  'lavender_percent': 5.127,
                                                                  'saturation_range': [0.274, 0.661, 0.929]},
                                            'spec_pixels_unchanged': True}},
 'fsh_opal_fault': {'schema': 'spb-finish-identity/1',
                    'finish_id': 'fsh_opal_fault',
                    'display_name': 'Opal Bloom — FRACTURED SHOKK prototype',
                    'promise': 'Irregular overlapping irregular mineral blooms reveal localized spectral '
                               'highlights without repeated rainbow bands.',
                    'carrier_grammar': 'overlapping irregular mineral blooms with five overlapping '
                                       'purpose-built material features and nonperiodic chromatic gradients.',
                    'spec_grammar': 'Each named overlapping irregular mineral blooms feature has a separate '
                                    'eight-tier response near the actual-game spectral-metal window.',
                    'reference_physics': {'mechanism': 'Fixed saturated pigment tints metallic reflections. '
                                                       'Roughness and clearcoat determine highlight '
                                                       'response. Actual-game calibration anchor255/40/218; '
                                                       'no physical wavelength diffraction or animated paint '
                                                       'claimed.',
                                          'sources': ['R2_MECHANISM/DAYLIGHT_BREAKTHROUGH.md']},
                    'native_scale_px': [8, 32],
                    'mark_types': [{'name': 'mineral pool',
                                    'role': 'mineral pool owns a visible material-bearing part of this '
                                            'construction'},
                                   {'name': 'growth lip',
                                    'role': 'growth lip owns a visible material-bearing part of this '
                                            'construction'},
                                   {'name': 'inclusion',
                                    'role': 'inclusion owns a visible material-bearing part of this '
                                            'construction'},
                                   {'name': 'fracture',
                                    'role': 'fracture owns a visible material-bearing part of this '
                                            'construction'},
                                   {'name': 'pearl nodule',
                                    'role': 'pearl nodule owns a visible material-bearing part of this '
                                            'construction'}],
                    'material_binding': {'M': ['mineral pool',
                                               'growth lip',
                                               'inclusion',
                                               'fracture',
                                               'pearl nodule'],
                                         'R': ['mineral pool',
                                               'growth lip',
                                               'inclusion',
                                               'fracture',
                                               'pearl nodule'],
                                         'Cc': ['mineral pool',
                                                'growth lip',
                                                'inclusion',
                                                'fracture',
                                                'pearl nodule']},
                    'material_tiers': [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92],
                    'nearest_neighbors': [{'finish_id': 'fsh_r3_prism_shards',
                                           'difference': 'overlapping irregular mineral blooms versus '
                                                         'irregular angular prism chips'},
                                          {'finish_id': 'fsh_r3_brushed_spectrum',
                                           'difference': 'overlapping irregular mineral blooms versus '
                                                         'layered short paintbrush strokes'},
                                          {'finish_id': 'fsh_r3_chromatic_grunge',
                                           'difference': 'overlapping irregular mineral blooms versus pitted '
                                                         'and abraded multicolor metal'}],
                    'name_truth': {'hidden_title_verdict': 'pending',
                                   'visible_evidence': ['overlapping irregular mineral blooms',
                                                        'mineral pool',
                                                        'growth lip',
                                                        'inclusion',
                                                        'fracture',
                                                        'pearl nodule']},
                    'owner_review': {'verdict': 'pending',
                                     'instruction': 'NO BANDS; prisms, gradients, grunge, brushwork'},
                    'construction_key': 'fsh:r3:opal_bloom',
                    'spec_key': 'fsh:r3:opal_bloom:five-bound-feature-populations',
                    'development_status': 'R3 nonband proof; actual-game validation and owner review pending',
                    'previous_revision': {'id': 'R1',
                                          'verdict': 'reject',
                                          'reason': 'Owner rejected the promised light response'},
                    'qualification_errors': ["name_truth.hidden_title_verdict must be 'pass'"],
                    'review_asset_sha256': {'paint': '8c3f370c130b392b07f5de017774dee00be500f5081eff03be466db0c17f126e',
                                            'spec': 'e9d57de46dd0884056989cee713eb56b58355d8ff0742eb874b40b4efdbd15a5'},
                    'palette_revision': {'date': '2026-09-18',
                                         'owner_request': 'whole rainbow; yellow orange pink purple seafoam '
                                                          'and shades within families',
                                         'anchors': [['scarlet', 0, 0.96],
                                                     ['ruby', 350, 0.92],
                                                     ['coral', 12, 0.68],
                                                     ['vermillion', 20, 0.95],
                                                     ['orange', 30, 0.96],
                                                     ['amber', 42, 0.91],
                                                     ['gold', 51, 0.95],
                                                     ['lemon', 61, 0.86],
                                                     ['chartreuse', 79, 0.86],
                                                     ['lime', 95, 0.92],
                                                     ['leaf green', 115, 0.85],
                                                     ['emerald', 140, 0.91],
                                                     ['jade', 155, 0.72],
                                                     ['seafoam', 162, 0.48],
                                                     ['mint', 147, 0.38],
                                                     ['turquoise', 176, 0.81],
                                                     ['cyan', 188, 0.93],
                                                     ['azure', 206, 0.91],
                                                     ['cobalt', 228, 0.93],
                                                     ['periwinkle', 245, 0.58],
                                                     ['violet', 266, 0.89],
                                                     ['lavender', 280, 0.48],
                                                     ['purple', 291, 0.87],
                                                     ['orchid', 309, 0.63],
                                                     ['fuchsia', 324, 0.93],
                                                     ['rose', 339, 0.55],
                                                     ['pink', 350, 0.42],
                                                     ['salmon', 9, 0.5]],
                                         'measured_coverage': {'hue_30_degree_percent': [14.515,
                                                                                         13.682,
                                                                                         7.789,
                                                                                         6.801,
                                                                                         8.199,
                                                                                         9.276,
                                                                                         8.121,
                                                                                         4.448,
                                                                                         4.333,
                                                                                         5.608,
                                                                                         6.387,
                                                                                         10.842],
                                                               'seafoam_mint_percent': 6.467,
                                                               'soft_pink_percent': 10.43,
                                                               'lavender_percent': 3.78,
                                                               'saturation_range': [0.275, 0.649, 0.929]},
                                         'spec_pixels_unchanged': True}}})
