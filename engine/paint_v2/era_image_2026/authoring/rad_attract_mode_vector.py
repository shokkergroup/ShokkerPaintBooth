"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_attract_mode", "display_name": "Arcade: Attract Mode", "promise": "Electric pixel comets and collision bursts on deep ultraviolet arcade glass.", "carrier_grammar": "Electric pixel comets and collision bursts on deep ultraviolet arcade glass. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "The approved aligned material anatomy for ultraviolet glass field, cyan pixel heads, pink animation trails, yellow collision sparks, dark frame gaps is reconstructed with cubic boundary curves and continuous bounded M/R/Cc polynomial fields. Metallic shoulders, rough valleys and coat transitions retain their source-feature locations; no unrelated house carrier is introduced.", "reference_physics": {"mechanism": "Electric pixel comets and collision bursts on deep ultraviolet arcade glass. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_attract_mode.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "ultraviolet glass field", "role": "Actual shared paint and spec geometry: ultraviolet glass field"}, {"name": "cyan pixel heads", "role": "Actual shared paint and spec geometry: cyan pixel heads"}, {"name": "pink animation trails", "role": "Actual shared paint and spec geometry: pink animation trails"}, {"name": "yellow collision sparks", "role": "Actual shared paint and spec geometry: yellow collision sparks"}, {"name": "dark frame gaps", "role": "Actual shared paint and spec geometry: dark frame gaps"}], "material_binding": {"M": ["ultraviolet glass field", "cyan pixel heads", "pink animation trails", "yellow collision sparks", "dark frame gaps"], "R": ["ultraviolet glass field", "cyan pixel heads", "pink animation trails", "yellow collision sparks", "dark frame gaps"], "Cc": ["ultraviolet glass field", "cyan pixel heads", "pink animation trails", "yellow collision sparks", "dark frame gaps"]}, "material_tiers": ["matte cut or sleeve", "satin substrate", "glossy pigment face", "pink polished foil rim", "red chrome shoulder", "green rough undercut", "cool smooth inset", "fine silver glint"], "nearest_neighbors": [{"finish_id": "rad_sprite_sheet", "difference": "This finish uses Dense minuscule four-color arcade animation fragments: stepped cyan comet heads, pink pixel trails, yellow collision crosses, cobalt stair-step particles and tiny dark square pauses. Every tiny cluster faces a different direction; no game characters, icons or text.; compare boundaries and relief independently of color."}, {"finish_id": "cbp_packet_loss", "difference": "This finish uses Dense minuscule four-color arcade animation fragments: stepped cyan comet heads, pink pixel trails, yellow collision crosses, cobalt stair-step particles and tiny dark square pauses. Every tiny cluster faces a different direction; no game characters, icons or text.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Cyan stepped pixel heads read as arcade fragments.", "Pink trailing bits and gold crosses interrupt the pixel clusters.", "The sparse dark gaps preserve the silhouette of individual raster marks."], "scale_redraw_required": false, "source_sha256": "331b518aed641acdf68884660750892053451584d840789b7114f1a8d8bbff76", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "rad_attract_mode-authored-Electric pixel comets and collision bursts on deep ultraviolet arcade glass. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "rad_attract_mode-feature-bound-vector-material-states", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 81.4, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts", "owner_approved_concept_version": "c099aa53ac91dc516d5a4bb9265b765a771ad49b236282bb6140db32da327fee"}')

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
    with gzip.open(root/'rad_attract_mode_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'rad_attract_mode_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_attract_mode_'+kind+".png"))
