"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_skin_weave", "display_name": "Chrome: Signal Weave", "promise": "Coral synthetic fibers cross turquoise conductive threads and tiny gold stitch nodes.", "carrier_grammar": "Coral synthetic fibers cross turquoise conductive threads and tiny gold stitch nodes. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Dielectric coral synthetic yarn and rough violet elastic cross metallic turquoise conductive threads and polished gold nodes. Pale fiber fuzz and dark gaps remain matte; fiber shoulders and thread grooves carry independent continuous roughness/coating states.", "reference_physics": {"mechanism": "Coral synthetic fibers cross turquoise conductive threads and tiny gold stitch nodes. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_skin_weave.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "coral synthetic fibers", "role": "Actual shared paint and spec geometry: coral synthetic fibers"}, {"name": "turquoise conductor threads", "role": "Actual shared paint and spec geometry: turquoise conductor threads"}, {"name": "gold stitch nodes", "role": "Actual shared paint and spec geometry: gold stitch nodes"}, {"name": "violet elastic loops", "role": "Actual shared paint and spec geometry: violet elastic loops"}, {"name": "pale fiber fuzz", "role": "Actual shared paint and spec geometry: pale fiber fuzz"}, {"name": "dark weave gaps", "role": "Actual shared paint and spec geometry: dark weave gaps"}], "material_binding": {"M": ["coral synthetic fibers", "turquoise conductor threads", "gold stitch nodes", "violet elastic loops", "pale fiber fuzz", "dark weave gaps"], "R": ["coral synthetic fibers", "turquoise conductor threads", "gold stitch nodes", "violet elastic loops", "pale fiber fuzz", "dark weave gaps"], "Cc": ["coral synthetic fibers", "turquoise conductor threads", "gold stitch nodes", "violet elastic loops", "pale fiber fuzz", "dark weave gaps"]}, "material_tiers": ["coral dielectric satin fibers", "turquoise metallic conductors", "polished gold stitch nodes", "rough violet elastic", "matte pale fiber fuzz", "dull weave gaps", "conductive ridge glints"], "nearest_neighbors": [{"finish_id": "cbp_carbon_limb", "difference": "This finish uses Fine coral synthetic filament weave with tiny turquoise conductive stitches, gold node grains, violet elastic loops, pale fiber fuzz and dark weave gaps. Many short interlaced filament bundles, technical textile not skin, no flesh or anatomy, no broad regular carbon checker.; compare boundaries and relief independently of color."}, {"finish_id": "rad_neon_spandex", "difference": "This finish uses Fine coral synthetic filament weave with tiny turquoise conductive stitches, gold node grains, violet elastic loops, pale fiber fuzz and dark weave gaps. Many short interlaced filament bundles, technical textile not skin, no flesh or anatomy, no broad regular carbon checker.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["coral fiber bundle is visible in the authored geometry", "turquoise link loop is visible in the authored geometry", "violet underpass is visible in the authored geometry", "gold tie knot is visible in the authored geometry", "pale fiber glint is visible in the authored geometry", "connector sleeve is visible in the authored geometry"], "source_sha256": "65732bc8a12dc9fe207d19ac8c027228260f633d13d31d119e414f45c26a3279", "evidence_scope": "Internal visual review of staged paired geometry; owner approved the source concept, not a second review of this reconstruction."}, "construction_key": "cbp_skin_weave-authored-Coral synthetic fibers cross turquoise conductive threads and tiny gold stitch nodes. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_skin_weave-dielectric-fiber-conductive-yarn-gold-node-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 82.9, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts", "owner_approved_concept_version": "0c104642848e0df81f73fd183161501bbca62feb297504a1a7751f4784114b9b"}')

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
    with gzip.open(root/'cbp_skin_weave_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_skin_weave_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s


def textile_spec(paint,fid):
    assert fid in ('rad_peach_fuzz','rad_aerobics_gym','rad_zigzag_runner','rad_hypercolour','rad_neon_spandex','rad_splatter_tee','cbp_skin_weave')
    z=paint.astype(np.float32)/255;scale=paint.shape[0]/2048
    smooth=cv2.GaussianBlur(z,(0,0),max(.6,1.3*scale));hsv=cv2.cvtColor(smooth,cv2.COLOR_RGB2HSV);h,s,v=cv2.split(hsv)
    gray=cv2.cvtColor(z,cv2.COLOR_RGB2GRAY);broad=cv2.GaussianBlur(gray,(0,0),max(1,6*scale))
    tips=np.clip((gray-broad)*7+.5,0,1);seam=np.clip((broad-gray)*6,0,1)
    if fid=='cbp_skin_weave':
        # Conductive yarn and nodes are metal; coral synthetic fibers and
        # violet elastic are not. This hybrid uses all three channels.
        cyan=np.clip(1-np.abs(h-185)/35,0,1)*np.clip(s/.45,0,1)
        gold=np.clip(1-np.abs(h-46)/28,0,1)*np.clip(s/.4,0,1)
        violet=np.clip(1-np.abs(h-271)/42,0,1)*s
        fuzz=(1-s)*np.clip((v-.64)*4,0,1)
        gap=np.clip((.21-v)/.18,0,1)
        m=3+9*tips+cyan*(150+79*tips)+gold*(224+18*tips)
        r=134+36*tips+60*violet+56*fuzz+72*gap-cyan*(81+21*tips)-gold*(99+23*tips)
        cc=144+38*seam+51*violet+39*fuzz+47*gap+cyan*(29+31*tips)-gold*(108+9*tips)
        out=np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)
        out[...,2]=np.maximum(16,out[...,2]);return out
    if fid=='rad_splatter_tee':
        teal=np.clip(1-np.abs(h-185)/42,0,1)*s
        purple=np.clip(1-np.abs(h-268)/41,0,1)*s
        pink=np.clip(1-np.abs(h-327)/42,0,1)*s
        cotton=(1-s)*np.clip((v-.45)*3,0,1)
        dry=np.clip(np.abs(gray-broad)*12,0,1)
        m=2+5*tips+5*dry
        r=197-58*teal-91*purple-43*pink+32*cotton+26*dry
        cc=207-66*teal-135*purple-97*pink+26*cotton+21*dry
        return np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)
    if fid=='rad_hypercolour':
        violet=np.clip(1-np.abs(h-270)/48,0,1)*s
        lime=np.clip(1-np.abs(h-86)/40,0,1)*s
        orange=np.clip(1-np.abs(h-25)/30,0,1)*s
        fuzz=(1-s)*np.clip((v-.55)*3,0,1)
        capillary=np.clip(np.abs(gray-broad)*13,0,1)
        m=2+8*tips+4*capillary
        r=187-47*violet+20*lime-19*orange+44*fuzz+25*tips
        cc=196-56*orange-21*lime+28*violet+33*fuzz+23*seam
        return np.rint(np.stack([m,r,cc],-1)).clip(0,255).astype(np.uint8)
    if fid=='rad_neon_spandex':
        lime=np.clip(1-np.abs(h-83)/48,0,1)*s
        cyan=np.clip(1-np.abs(h-185)/40,0,1)*s
        pink=np.clip(1-np.abs(h-321)/43,0,1)*s
        violet=np.clip(1-np.abs(h-273)/37,0,1)*s
        gaps=np.clip((.3-v)/.25,0,1)
        shoulder=np.clip((gray-broad)*10,0,1)
        m=2+9*shoulder+6*seam
        r=120-55*lime+17*cyan-33*pink+82*violet+85*gaps+19*seam
        cc=111-72*lime-35*pink+48*cyan+91*violet+91*gaps+29*shoulder
        return np.rint(np.stack([m,r,np.maximum(16,cc)],-1)).clip(0,255).astype(np.uint8)
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
    return p,textile_spec(p,'cbp_skin_weave')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_skin_weave_'+kind+".png"))
