"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_zigzag_runner", "display_name": "Memphis: Zigzag Runner", "promise": "Fine mustard, teal and raspberry woven zigzags with cream yarn knots.", "carrier_grammar": "Fine mustard, teal and raspberry woven zigzags with cream yarn knots. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Dielectric mustard satin yarn, rough teal warp, raspberry weft shoulders, matte cream knots and dull deep weave gaps.", "reference_physics": {"mechanism": "Fine mustard, teal and raspberry woven zigzags with cream yarn knots. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_zigzag_runner.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "teal woven ground", "role": "Actual shared paint and spec geometry: teal woven ground"}, {"name": "mustard zigzag yarn", "role": "Actual shared paint and spec geometry: mustard zigzag yarn"}, {"name": "raspberry weft runs", "role": "Actual shared paint and spec geometry: raspberry weft runs"}, {"name": "cream yarn knots", "role": "Actual shared paint and spec geometry: cream yarn knots"}, {"name": "dark weave gaps", "role": "Actual shared paint and spec geometry: dark weave gaps"}], "material_binding": {"M": ["teal woven ground", "mustard zigzag yarn", "raspberry weft runs", "cream yarn knots", "dark weave gaps"], "R": ["teal woven ground", "mustard zigzag yarn", "raspberry weft runs", "cream yarn knots", "dark weave gaps"], "Cc": ["teal woven ground", "mustard zigzag yarn", "raspberry weft runs", "cream yarn knots", "dark weave gaps"]}, "material_tiers": ["teal woven ground dielectric material with independent continuous roughness/coating response", "mustard zigzag yarn dielectric material with independent continuous roughness/coating response", "raspberry weft runs dielectric material with independent continuous roughness/coating response", "cream yarn knots dielectric material with independent continuous roughness/coating response", "dark weave gaps dielectric material with independent continuous roughness/coating response", "raised fiber tips and compressed seams"], "nearest_neighbors": [{"finish_id": "rad_outrun_stripe", "difference": "This finish uses Extremely fine flatwoven rug texture: short thin mustard teal raspberry zigzag yarn runs in independent directions, tiny cream knots, visible fine interlaced warp and black weave gaps. Micro textile ribs, no giant chevron stripes or connected whole-width bands.; compare boundaries and relief independently of color."}, {"finish_id": "at_thrift_cardigan", "difference": "This finish uses Extremely fine flatwoven rug texture: short thin mustard teal raspberry zigzag yarn runs in independent directions, tiny cream knots, visible fine interlaced warp and black weave gaps. Micro textile ribs, no giant chevron stripes or connected whole-width bands.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Small stepped yellow and red yarn runs form zigzags.", "Teal loop pile and ivory stitch knots read as carpet.", "Dark gaps separate individual woven loops."], "scale_redraw_required": false, "source_sha256": "4144e07b22dc1506f76235e6248bfec0fb3eda883cb6c35931415d4b94fa5161", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "rad_zigzag_runner-authored-Fine mustard, teal and raspberry woven zigzags with cream yarn knots. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "rad_zigzag_runner-named-dielectric-yarn-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 67.6, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'rad_zigzag_runner_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'rad_zigzag_runner_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s


def textile_spec(paint,fid):
    assert fid in ('rad_peach_fuzz','rad_aerobics_gym','rad_zigzag_runner')
    z=paint.astype(np.float32)/255;scale=paint.shape[0]/2048
    smooth=cv2.GaussianBlur(z,(0,0),max(.6,1.3*scale));hsv=cv2.cvtColor(smooth,cv2.COLOR_RGB2HSV);h,s,v=cv2.split(hsv)
    gray=cv2.cvtColor(z,cv2.COLOR_RGB2GRAY);broad=cv2.GaussianBlur(gray,(0,0),max(1,6*scale))
    tips=np.clip((gray-broad)*7+.5,0,1);seam=np.clip((broad-gray)*6,0,1)
    # Tick33, same owner verdict: replace metallic fiber islands with named
    # dielectric yarn/elastic states. M7 movement remains pending actual bake.
    if fid=='rad_aerobics_gym':
        lime=np.clip(1-np.abs(h-85)/45,0,1)*s
        violet=np.clip(1-np.abs(h-278)/55,0,1)*s
        coral=np.maximum(np.clip(1-np.abs(h-15)/40,0,1),np.clip((h-330)/30,0,1))*s
        ivory=np.clip((v-.5)*3,0,1)*(1-s)
        gaps=np.clip((.35-v)/.3,0,1)
        m=2+10*tips+4*seam
        r=180-88*coral-35*lime+40*violet+35*ivory+48*gaps+20*tips
        cc=186-119*coral-69*lime+29*violet+34*ivory+47*gaps+20*seam
        return np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)
    if fid=='rad_zigzag_runner':
        mustard=np.clip(1-np.abs(h-43)/34,0,1)*s
        teal=np.clip(1-np.abs(h-178)/45,0,1)*s
        raspberry=np.clip(1-np.abs(h-333)/43,0,1)*s
        cream=(1-s)*np.clip((v-.45)*3,0,1)
        gaps=np.clip((.32-v)/.28,0,1)
        m=1+8*tips+3*cream
        r=179-40*mustard+29*teal+10*raspberry+35*cream+42*gaps+29*tips
        cc=172-44*mustard+37*teal+20*raspberry+36*cream+46*gaps+30*seam
        return np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)
    lilac=np.clip(1-np.abs(h-278)/48,0,1)*np.clip(s/.3,0,1)
    compressed=np.clip((.62-v)/.4,0,1)*(1-lilac)
    # The pigment remains dielectric throughout. Raised fibers are rougher;
    # compressed nap is satin, while deep seams have duller coating response.
    m=2+9*tips+5*lilac
    r=190+58*tips-43*compressed+12*seam-12*lilac
    cc=176+65*tips+22*seam-20*compressed+12*lilac
    return np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)


def generate(size=2048):
    p,_=generate_base(size)
    return p,textile_spec(p,'rad_zigzag_runner')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_zigzag_runner_'+kind+".png"))
