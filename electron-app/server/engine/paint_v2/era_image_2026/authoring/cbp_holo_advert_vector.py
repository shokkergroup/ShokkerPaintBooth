"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_holo_advert", "display_name": "Street: Holo Advert Foil", "promise": "Tiny cyan and rose lenticular foil slivers flash between violet enamel gaps.", "carrier_grammar": "Tiny cyan and rose lenticular foil slivers flash between violet enamel gaps. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Independently graded cyan engraved combs, rose foil prisms, gold pin prisms, dielectric violet enamel gaps and silver razor rims. Enamel distances bind narrow pink polished lips and rough green embossed shoulders; rib relief modulates each material continuously.", "reference_physics": {"mechanism": "Tiny cyan and rose lenticular foil slivers flash between violet enamel gaps. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_holo_advert.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "lenticular foil slivers", "role": "Actual shared paint and spec geometry: lenticular foil slivers"}, {"name": "cyan engraved combs", "role": "Actual shared paint and spec geometry: cyan engraved combs"}, {"name": "rose foil prisms", "role": "Actual shared paint and spec geometry: rose foil prisms"}, {"name": "gold pin prisms", "role": "Actual shared paint and spec geometry: gold pin prisms"}, {"name": "violet enamel gaps", "role": "Actual shared paint and spec geometry: violet enamel gaps"}, {"name": "silver razor rims", "role": "Actual shared paint and spec geometry: silver razor rims"}], "material_binding": {"M": ["lenticular foil slivers", "cyan engraved combs", "rose foil prisms", "gold pin prisms", "violet enamel gaps", "silver razor rims"], "R": ["lenticular foil slivers", "cyan engraved combs", "rose foil prisms", "gold pin prisms", "violet enamel gaps", "silver razor rims"], "Cc": ["lenticular foil slivers", "cyan engraved combs", "rose foil prisms", "gold pin prisms", "violet enamel gaps", "silver razor rims"]}, "material_tiers": ["cyan anodized engraved comb", "rose coated foil prism", "gold polished pin prism", "violet dielectric enamel", "silver razor rim", "dark enamel slot", "polished foil lip", "rough embossed shoulder"], "nearest_neighbors": [{"finish_id": "at_holo_sticker", "difference": "This finish uses Microscopic lenticular advertising foil: dense narrow cyan rose angular comb slivers with staggered line engravings, violet enamel gaps, gold pin prisms and silver razor rims. No signs or letters, no broad rainbow waves, no large hologram panels.; compare boundaries and relief independently of color."}, {"finish_id": "cbp_mirror_shades", "difference": "This finish uses Microscopic lenticular advertising foil: dense narrow cyan rose angular comb slivers with staggered line engravings, violet enamel gaps, gold pin prisms and silver razor rims. No signs or letters, no broad rainbow waves, no large hologram panels.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Cyan parallel comb slivers describe lenticular foil.", "Pink angular foil fragments interrupt the tracks.", "Gold edges and purple recesses give a layered holographic film."], "scale_redraw_required": false, "source_sha256": "4457df99cc46c89a56f66726681c7b2f1cefd6f78043b5c5728a611d7ea23200", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "cbp_holo_advert-authored-Tiny cyan and rose lenticular foil slivers flash between violet enamel gaps. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_holo_advert-lenticular-foil-enamel-razor-anatomy-v2", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 67.1, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

def path_from_record(row):
    tokens=re.findall(r'[MCZ]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',row['d']);p=skia.Path();i=0
    while i<len(tokens):
        op=tokens[i];i+=1
        if op=='M':p.moveTo(*map(float,tokens[i:i+2]));i+=2
        elif op=='C':p.cubicTo(*map(float,tokens[i:i+6]));i+=6
        elif op=='Z':p.close()
        else:raise ValueError(op)
    p.offset(*row['shift']);return p


def labels(rows,size,work):
 surf=skia.Surface(size,size);c=surf.getCanvas();c.clear(skia.ColorBLACK);c.scale(size/work,size/work)
 for j,row in enumerate(rows,1):c.drawPath(path_from_record(row),skia.Paint(Color=skia.ColorSetRGB(j&255,(j>>8)&255,(j>>16)&255),AntiAlias=False))
 a=surf.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
 return a[...,0].astype(np.int32)+a[...,1].astype(np.int32)*256+a[...,2].astype(np.int32)*65536


def render(recipe,size=2048):
 rows=recipe['rows'];lab=labels(rows,size,recipe['work']);coef=np.zeros((len(rows)+1,6,6),np.float32);box=np.ones((len(rows)+1,4),np.float32);low=np.zeros((len(rows)+1,6),np.float32);high=low+255
 for j,r in enumerate(rows,1):
  fit=r['fit'];coef[j]=fit['coef'];box[j]=fit['box'];low[j]=fit['low'];high[j]=fit['high']
 # Scanline blocks keep memory bounded and avoid six full-canvas temp arrays.
 result=np.empty((size,size,6),np.uint8)
 for top in range(0,size,128):
  ids=lab[top:top+128];yy,xx=np.mgrid[top:min(top+128,size),:size].astype(np.float32);u=(xx/size-box[ids,0])/box[ids,2];v=(yy/size-box[ids,1])/box[ids,3];out=coef[ids,0].copy()
  for k,a in enumerate([u,v,u*u,u*v,v*v],1):out+=coef[ids,k]*a[...,None]
  out=np.maximum(low[ids],np.minimum(high[ids],out));result[top:top+len(ids)]=np.rint(out).clip(0,255).astype(np.uint8)
 cc=result[...,5];cc[(cc>0)&(cc<16)]=16
 return result[...,:3],result[...,3:]


def generate_base(size=2048):
    root=Path(__file__).parent
    with gzip.open(root/'cbp_holo_advert_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_holo_advert_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s


def foil_spec(paint,fid):
    assert fid=='cbp_holo_advert'
    z=paint.astype(np.float32)/255;scale=paint.shape[0]/2048
    smooth=cv2.GaussianBlur(z,(0,0),max(.5,.75*scale))
    h,s,v=cv2.split(cv2.cvtColor(smooth,cv2.COLOR_RGB2HSV))
    gray=cv2.cvtColor(z,cv2.COLOR_RGB2GRAY)
    relief=np.clip((gray-cv2.GaussianBlur(gray,(0,0),max(.8,3*scale)))*6,-1,1)
    cyan=np.clip(1-np.abs(h-191)/45,0,1)*np.clip(s/.4,0,1)
    rose=np.clip(1-np.abs(h-328)/53,0,1)*np.clip(s/.45,0,1)
    gold=np.clip(1-np.abs(h-45)/32,0,1)*np.clip(s/.4,0,1)
    violet=np.clip(1-np.abs(h-269)/40,0,1)*np.clip(s/.5,0,1)
    silver=np.clip((v-.63)/.32,0,1)*np.clip((.35-s)/.3,0,1)
    deep=np.clip((.21-v)/.17,0,1)
    spec=np.stack([215+20*v,42+32*(1-v),110+90*s],-1)
    def bind(weight,target):
        nonlocal spec
        spec=spec*(1-weight[...,None])+np.stack(target,-1)*weight[...,None]
    bind(cyan,(44+131*v,35+75*(1-v),175+65*v))
    bind(rose,(225+25*v,15+36*(1-v),145+90*s))
    bind(gold,(240+15*v,9+40*(1-v),20+34*(1-v)))
    bind(violet,(8+19*v,45+95*(1-v),150+91*v))
    bind(deep,(8+15*v,175+55*(1-v),155+69*(1-v)))
    # Distances from actual dark enamel slots create a narrow polished foil
    # rim and a separately rough embossed shoulder, never unrelated waves.
    face=((v>.30)&(violet<.5)).astype(np.uint8)
    distance=cv2.distanceTransform(face,cv2.DIST_L2,5)/max(scale,.01)
    lip=np.exp(-((distance-1.2)/.8)**2)*face
    shoulder=np.exp(-((distance-4.2)/1.9)**2)*face
    bind(shoulder,(45+35*v,170+63*v,43+55*s))
    bind(lip,(242+13*v,8+17*(1-v),172+67*s))
    bind(silver,(248+7*v,4+10*(1-v),16+14*(1-v)))
    spec+=relief[...,None]*np.array([11,-24,31],np.float32)
    spec=np.rint(spec).clip(0,255).astype(np.uint8)
    spec[...,2]=np.maximum(16,spec[...,2])
    return spec


def generate(size=2048):
    p,_=generate_base(size)
    return p,foil_spec(p,'cbp_holo_advert')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_holo_advert_'+kind+".png"))
