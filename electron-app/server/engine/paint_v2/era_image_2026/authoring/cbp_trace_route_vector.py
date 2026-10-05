"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_trace_route", "display_name": "Netrun: Trace Route", "promise": "Fine cyan right-angle traces link orange nodes across magenta etched enamel.", "carrier_grammar": "Fine cyan right-angle traces link orange nodes across magenta etched enamel. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "The approved aligned material anatomy for magenta etched enamel, cyan route traces, orange solder nodes, violet via rims, silver jumper nicks, black insulating cuts is reconstructed with cubic boundary curves and continuous bounded M/R/Cc polynomial fields. Metallic shoulders, rough valleys and coat transitions retain their source-feature locations; no unrelated house carrier is introduced.", "reference_physics": {"mechanism": "Fine cyan right-angle traces link orange nodes across magenta etched enamel. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_trace_route.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "magenta etched enamel", "role": "Actual shared paint and spec geometry: magenta etched enamel"}, {"name": "cyan route traces", "role": "Actual shared paint and spec geometry: cyan route traces"}, {"name": "orange solder nodes", "role": "Actual shared paint and spec geometry: orange solder nodes"}, {"name": "violet via rims", "role": "Actual shared paint and spec geometry: violet via rims"}, {"name": "silver jumper nicks", "role": "Actual shared paint and spec geometry: silver jumper nicks"}, {"name": "black insulating cuts", "role": "Actual shared paint and spec geometry: black insulating cuts"}], "material_binding": {"M": ["magenta etched enamel", "cyan route traces", "orange solder nodes", "violet via rims", "silver jumper nicks", "black insulating cuts"], "R": ["magenta etched enamel", "cyan route traces", "orange solder nodes", "violet via rims", "silver jumper nicks", "black insulating cuts"], "Cc": ["magenta etched enamel", "cyan route traces", "orange solder nodes", "violet via rims", "silver jumper nicks", "black insulating cuts"]}, "material_tiers": ["matte cut or sleeve", "satin substrate", "glossy pigment face", "pink polished foil rim", "red chrome shoulder", "green rough undercut", "cool smooth inset", "fine silver glint"], "nearest_neighbors": [{"finish_id": "cbp_encryption_lattice", "difference": "This finish uses Microscopic short cyan right-angle route traces with orange solder nodes, magenta etched enamel, violet broken via rims, silver jumper nicks and black insulating cuts. Dense tiny disconnected trace islands with varied rotations, no giant circuit board or long paths.; compare boundaries and relief independently of color."}, {"finish_id": "cbp_datastream", "difference": "This finish uses Microscopic short cyan right-angle route traces with orange solder nodes, magenta etched enamel, violet broken via rims, silver jumper nicks and black insulating cuts. Dense tiny disconnected trace islands with varied rotations, no giant circuit board or long paths.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Cyan right-angle tracks end in small beads.", "Pink bridges cross orange contacts and violet ports.", "Black recessed gaps keep individual route fragments separate."], "scale_redraw_required": false, "source_sha256": "5e8b2b09b01a27c5c4c6c1cfadb8560b1aa4e77943695775c9fde1b2e17ae14d", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "cbp_trace_route-authored-Fine cyan right-angle traces link orange nodes across magenta etched enamel. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_trace_route-feature-bound-vector-material-states", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 77.3, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'cbp_trace_route_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_trace_route_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_trace_route_'+kind+".png"))
