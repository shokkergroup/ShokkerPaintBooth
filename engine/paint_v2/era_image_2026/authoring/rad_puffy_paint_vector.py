"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_puffy_paint", "display_name": "Radical: Puffy Paint", "promise": "Tiny raised pink, teal and yellow paint curls on violet cotton.", "carrier_grammar": "Approved pink raised resin curls, teal rubber curls and yellow puffy dots retain their fitted cubic silhouettes and native placement over violet cotton. Fine substrate threads, paint shoulders, convex pigment centers and pinhole pores own distinct physical states.", "spec_grammar": "Cotton-effect substrate is rough matte dielectric; teal rubber-effect curls use satin-to-matte coating roughness; pink/yellow resin profiles use per-component normalized distance for edge-to-center roughness and coat roughness. B0 means no coat; B16 means maximum coat gloss, B255 dull. Pinhole pits raise roughness and remove coat; no chrome is invented to satisfy a metric.", "reference_physics": {"mechanism": "Approved pink raised resin curls, teal rubber curls and yellow puffy dots retain their fitted cubic silhouettes and native placement over violet cotton. Fine substrate threads, paint shoulders, convex pigment centers and pinhole pores own distinct physical states. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_puffy_paint.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "cotton thread", "role": "Actual shared paint and spec geometry: cotton thread"}, {"name": "pink resin curl", "role": "Actual shared paint and spec geometry: pink resin curl"}, {"name": "teal rubber curl", "role": "Actual shared paint and spec geometry: teal rubber curl"}, {"name": "yellow puffy dot", "role": "Actual shared paint and spec geometry: yellow puffy dot"}, {"name": "convex pigment center", "role": "Actual shared paint and spec geometry: convex pigment center"}, {"name": "pinhole pore", "role": "Actual shared paint and spec geometry: pinhole pore"}], "material_binding": {"M": ["cotton thread", "pink resin curl", "teal rubber curl", "yellow puffy dot", "convex pigment center", "pinhole pore"], "R": ["cotton thread", "pink resin curl", "teal rubber curl", "yellow puffy dot", "convex pigment center", "pinhole pore"], "Cc": ["cotton thread", "pink resin curl", "teal rubber curl", "yellow puffy dot", "convex pigment center", "pinhole pore"]}, "material_tiers": ["matte cotton thread", "compressed cotton crossing", "satin rubber center", "rough rubber shoulder", "gloss resin center", "satin resin shoulder", "uncoated pinhole pit"], "nearest_neighbors": [{"finish_id": "rad_bezel_black", "difference": "This finish uses Thousands of minute domed fabric-paint dots, short squeezed comma curls, thin little squiggles in pink teal yellow on violet cotton. Visibly rounded raised rubbery paint with fine bubble pinholes, soft cloth between. All motifs microscopic, no letters, hearts or large cartoon forms.; compare boundaries and relief independently of color."}, {"finish_id": "rad_trapper_sticker", "difference": "This finish uses Thousands of minute domed fabric-paint dots, short squeezed comma curls, thin little squiggles in pink teal yellow on violet cotton. Visibly rounded raised rubbery paint with fine bubble pinholes, soft cloth between. All motifs microscopic, no letters, hearts or large cartoon forms.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["S paint dollop is visible in the authored geometry", "domed pigment drop is visible in the authored geometry", "rounded comma deposit is visible in the authored geometry", "glossy top ridge is visible in the authored geometry", "meniscus outline is visible in the authored geometry", "squeezed dot is visible in the authored geometry"], "source_sha256": "acd4847d29b9ebc928b01d228af3aa500fc4bcc9dde65345770e39b2d4aff3c6", "evidence_scope": "Internal visual review of staged paired geometry; owner approved the source concept, not a second review of this reconstruction."}, "construction_key": "rad_puffy_paint-authored-Approved pink raised resin curls, teal rubber curls and yellow puffy dots retain their fitted cubic silhouettes and native placement over violet cotton. Fine substrate threads, paint shoulders, convex pigment centers and pinhole pores own distinct physical states.", "spec_key": "rad_puffy_paint-feature-bound-vector-material-states", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 69.8, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts", "owner_approved_concept_version": "db4effe86bb6028f66a9a97ce950d80981cb39c16d6a44cb7ee790c271b15788"}')

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


def build(paint):
 size=paint.shape[0];scale=size/2048;f=cv2.GaussianBlur(paint,(0,0),max(.5,scale));hsv=cv2.cvtColor(f,cv2.COLOR_RGB2HSV);h=hsv[...,0];s=hsv[...,1]
 labels=np.zeros(h.shape,np.uint8);labels[((h>145)|(h<5))&(s>75)]=1;labels[(h>65)&(h<112)&(s>70)]=2;labels[(h>12)&(h<40)&(s>90)]=3
 yy,xx=np.mgrid[:size,:size];weave=(np.sin(xx/scale*np.pi/4)*np.sin(yy/scale*np.pi/4)+1)/2
 # Registry printed 2026-09-18: matte M0/R200/CC160; satin M0/R95/CC70;
 # gloss M0/R30/CC16. Cotton's raised threads extend toward duller coat.
 result=np.zeros_like(paint,dtype=np.float32);result[...,0]=2+3*weave;result[...,1]=232+23*weave;result[...,2]=160+94*weave
 gray=cv2.cvtColor(paint,cv2.COLOR_RGB2GRAY).astype(float)/255;local=cv2.GaussianBlur(gray,(0,0),max(1,6*scale));pore=np.clip((local-gray-.025)*10,0,1)
 for k in [1,2,3]:
  mask=(labels==k).astype(np.uint8);dist=cv2.distanceTransform(mask,cv2.DIST_L2,5);n,cc=cv2.connectedComponents(mask);peak=np.zeros(n,np.float32);np.maximum.at(peak,cc.ravel(),dist.ravel());depth=dist/np.maximum(peak[cc],1)
  crown=np.sin(depth*np.pi/2);lip=np.exp(-((depth-.16)/.13)**2);tier=((cc*47+13)%101)/100
  m=3+6*crown+4*tier
  if k==1:r=136-122*crown+18*tier-11*lip;c=148-111*crown+17*tier-15*lip
  elif k==2:r=171-65*crown+17*tier;c=230-118*crown+12*tier
  else:r=129-102*crown+23*tier;c=174-145*crown+16*tier
  r=r*(1-pore)+228*pore;c=c*(1-pore)
  val=np.stack([m,r,c],-1);result[mask.astype(bool)]=val[mask.astype(bool)]
 spec=np.rint(result).clip(0,255).astype(np.uint8);cc=spec[...,2];cc[(cc>0)&(cc<16)]=16
 # Restore fine cotton thread visibility lost when tracing removed bitmap
 # grain. Only the actual violet substrate receives this restrained weave.
 p=paint.astype(float);delta=(weave-.5)*2.5;p[labels==0]+=delta[labels==0,None]
 return np.rint(p).clip(0,255).astype(np.uint8),spec


def generate(size=2048):
    root=Path(__file__).parent
    with gzip.open(root/'rad_puffy_paint_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    return build(p)

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_puffy_paint_'+kind+".png"))
