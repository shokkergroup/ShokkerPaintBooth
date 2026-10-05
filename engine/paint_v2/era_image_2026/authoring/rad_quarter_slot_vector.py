"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_quarter_slot", "display_name": "Arcade: Token Jackpot", "promise": "Burnished gold token-edge teeth, red enamel arcs and polished nickel chips.", "carrier_grammar": "Burnished gold token-edge teeth, red enamel arcs and polished nickel chips. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "The approved aligned material anatomy for gold token plating, cherry enamel ticks, purple lacquer residue, nickel wear chips, dark die recesses is reconstructed with cubic boundary curves and continuous bounded M/R/Cc polynomial fields. Metallic shoulders, rough valleys and coat transitions retain their source-feature locations; no unrelated house carrier is introduced.", "reference_physics": {"mechanism": "Burnished gold token-edge teeth, red enamel arcs and polished nickel chips. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_quarter_slot.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "gold token plating", "role": "Actual shared paint and spec geometry: gold token plating"}, {"name": "cherry enamel ticks", "role": "Actual shared paint and spec geometry: cherry enamel ticks"}, {"name": "purple lacquer residue", "role": "Actual shared paint and spec geometry: purple lacquer residue"}, {"name": "nickel wear chips", "role": "Actual shared paint and spec geometry: nickel wear chips"}, {"name": "dark die recesses", "role": "Actual shared paint and spec geometry: dark die recesses"}], "material_binding": {"M": ["gold token plating", "cherry enamel ticks", "purple lacquer residue", "nickel wear chips", "dark die recesses"], "R": ["gold token plating", "cherry enamel ticks", "purple lacquer residue", "nickel wear chips", "dark die recesses"], "Cc": ["gold token plating", "cherry enamel ticks", "purple lacquer residue", "nickel wear chips", "dark die recesses"]}, "material_tiers": ["matte cut or sleeve", "satin substrate", "glossy pigment face", "pink polished foil rim", "red chrome shoulder", "green rough undercut", "cool smooth inset", "fine silver glint"], "nearest_neighbors": [{"finish_id": "at_mouse_ball_grime", "difference": "This finish uses Dense fine crescent segments of arcade token edges, tiny milled gold teeth, nickel notch fragments, cherry enamel jackpot tick marks and purple worn lacquer. No whole coins or lettering. Much finer and flatter than overlapping coin piles, distinctive short toothed semicircular fragments.; compare boundaries and relief independently of color."}, {"finish_id": "rad_high_score", "difference": "This finish uses Dense fine crescent segments of arcade token edges, tiny milled gold teeth, nickel notch fragments, cherry enamel jackpot tick marks and purple worn lacquer. No whole coins or lettering. Much finer and flatter than overlapping coin piles, distinctive short toothed semicircular fragments.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["gold token plating is visible in the authored geometry", "cherry enamel ticks is visible in the authored geometry", "purple lacquer residue is visible in the authored geometry", "nickel wear chips is visible in the authored geometry", "dark die recesses is visible in the authored geometry"], "source_sha256": "c3b8ffaf66cd3791ebc0603e5bcc51a53196e34ca7294ab8501f43aef25d5850", "evidence_scope": "Internal visual review of staged paired geometry; owner approved the source concept, not a second review of this reconstruction."}, "construction_key": "rad_quarter_slot-authored-Burnished gold token-edge teeth, red enamel arcs and polished nickel chips. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "rad_quarter_slot-feature-bound-vector-material-states", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 69.2, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts", "owner_approved_concept_version": "856303fa2f31ccb959324b2a6994af0c1973edf68b7538ba89f61e3a6142c2e2"}')

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


def generate(size=2048):
    root=Path(__file__).parent
    with gzip.open(root/'rad_quarter_slot_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'rad_quarter_slot_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_quarter_slot_'+kind+".png"))
