"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_oil_slick_puddle", "display_name": "Sprawl: Oil Interference", "promise": "Fine rose, gold and teal oil-film loops with violet meniscus pits.", "carrier_grammar": "Fine rose, gold and teal oil-film loops with violet meniscus pits. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "The approved aligned material anatomy for rose oil film, gold interference bands, teal film loops, violet meniscus pits, black capillary splits, pale wet pinpoints is reconstructed with cubic boundary curves and continuous bounded M/R/Cc polynomial fields. Metallic shoulders, rough valleys and coat transitions retain their source-feature locations; no unrelated house carrier is introduced.", "reference_physics": {"mechanism": "Fine rose, gold and teal oil-film loops with violet meniscus pits. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_oil_slick_puddle.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "rose oil film", "role": "Actual shared paint and spec geometry: rose oil film"}, {"name": "gold interference bands", "role": "Actual shared paint and spec geometry: gold interference bands"}, {"name": "teal film loops", "role": "Actual shared paint and spec geometry: teal film loops"}, {"name": "violet meniscus pits", "role": "Actual shared paint and spec geometry: violet meniscus pits"}, {"name": "black capillary splits", "role": "Actual shared paint and spec geometry: black capillary splits"}, {"name": "pale wet pinpoints", "role": "Actual shared paint and spec geometry: pale wet pinpoints"}], "material_binding": {"M": ["rose oil film", "gold interference bands", "teal film loops", "violet meniscus pits", "black capillary splits", "pale wet pinpoints"], "R": ["rose oil film", "gold interference bands", "teal film loops", "violet meniscus pits", "black capillary splits", "pale wet pinpoints"], "Cc": ["rose oil film", "gold interference bands", "teal film loops", "violet meniscus pits", "black capillary splits", "pale wet pinpoints"]}, "material_tiers": ["matte cut or sleeve", "satin substrate", "glossy pigment face", "pink polished foil rim", "red chrome shoulder", "green rough undercut", "cool smooth inset", "fine silver glint"], "nearest_neighbors": [{"finish_id": "cbp_puddle_neon", "difference": "This finish uses Dense tiny thin-film oil interference loops, rose gold teal narrow banded crescents, violet meniscus pits, black capillary splits and pale wet pinpoints. Micro concentric curved film fragments, no broad rainbow waves or large oil puddles, no glass shards.; compare boundaries and relief independently of color."}, {"finish_id": "at_disc_rainbow", "difference": "This finish uses Dense tiny thin-film oil interference loops, rose gold teal narrow banded crescents, violet meniscus pits, black capillary splits and pale wet pinpoints. Micro concentric curved film fragments, no broad rainbow waves or large oil puddles, no glass shards.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Multicolor crescent films curl over a bronze and violet wet surface.", "Dark round pores interrupt the interference films.", "Fine bright film rims and black cracks distinguish wet edges from dry breaks."], "scale_redraw_required": false, "source_sha256": "1fa1ddf68530768f53d0cb6f5f2d68cc72b0e6ea20574056384fe653796d2c5b", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "cbp_oil_slick_puddle-authored-Fine rose, gold and teal oil-film loops with violet meniscus pits. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_oil_slick_puddle-feature-bound-vector-material-states", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 50.9, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'cbp_oil_slick_puddle_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_oil_slick_puddle_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_oil_slick_puddle_'+kind+".png"))
