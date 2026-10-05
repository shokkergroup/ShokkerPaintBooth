"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_splatter_tee", "display_name": "Radical: Splatter Tee", "promise": "Fine teal, purple and pink thrown paint with dry cotton showing between droplets.", "carrier_grammar": "Fine teal, purple and pink thrown paint with dry cotton showing between droplets. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Matte ivory cotton, satin teal thrown pigment, glossier purple cured ink, pink rubber splats, dry rough pigment edges and cotton fuzz. All remain dielectric; coating and roughness follow each named mark.", "reference_physics": {"mechanism": "Fine teal, purple and pink thrown paint with dry cotton showing between droplets. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_splatter_tee.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "ivory shirt cotton", "role": "Actual shared paint and spec geometry: ivory shirt cotton"}, {"name": "teal thrown paint", "role": "Actual shared paint and spec geometry: teal thrown paint"}, {"name": "purple paint flicks", "role": "Actual shared paint and spec geometry: purple paint flicks"}, {"name": "pink radial splats", "role": "Actual shared paint and spec geometry: pink radial splats"}, {"name": "hairline thrown paint threads", "role": "Actual shared paint and spec geometry: hairline thrown paint threads"}, {"name": "detached spherical satellite droplets", "role": "Actual shared paint and spec geometry: detached spherical satellite droplets"}], "material_binding": {"M": ["ivory shirt cotton", "teal thrown paint", "purple paint flicks", "pink radial splats", "hairline thrown paint threads", "detached spherical satellite droplets"], "R": ["ivory shirt cotton", "teal thrown paint", "purple paint flicks", "pink radial splats", "hairline thrown paint threads", "detached spherical satellite droplets"], "Cc": ["ivory shirt cotton", "teal thrown paint", "purple paint flicks", "pink radial splats", "hairline thrown paint threads", "detached spherical satellite droplets"]}, "material_tiers": ["ivory shirt cotton dielectric material with independent continuous roughness/coating response", "teal thrown paint dielectric material with independent continuous roughness/coating response", "purple paint flicks dielectric material with independent continuous roughness/coating response", "pink radial splats dielectric material with independent continuous roughness/coating response", "hairline thrown paint threads dielectric material with independent continuous roughness/coating response", "detached spherical satellite droplets dielectric material with independent continuous roughness/coating response"], "nearest_neighbors": [{"finish_id": "rad_rad_splatter_deck", "difference": "This finish uses Tiny real thrown fabric-paint marks in teal purple pink on ivory cotton: pin spatters, thin arced flicks, little radial splat stars, hairline drips and dry broken pigment. Dense all-over micro splatter without big blotches; matte fabric and slightly raised paint, no gloss board finish.; compare boundaries and relief independently of color."}, {"finish_id": "at_airbrush_tee", "difference": "This finish uses Tiny real thrown fabric-paint marks in teal purple pink on ivory cotton: pin spatters, thin arced flicks, little radial splat stars, hairline drips and dry broken pigment. Dense all-over micro splatter without big blotches; matte fabric and slightly raised paint, no gloss board finish.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Tiny teal purple and pink splashes show short radial ink tails.", "Fine satellite ink dots sit on pale cotton grain.", "The visible light fabric ground separates this from glossy deck splatter."], "scale_redraw_required": false, "source_sha256": "b5e542bdf60f434a417af01900d9c1a026e4f11282d7c40f5227e7383aeab63b", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "rad_splatter_tee-authored-Fine teal, purple and pink thrown paint with dry cotton showing between droplets. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "rad_splatter_tee-dielectric-pigment-on-cotton-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 63.7, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'rad_splatter_tee_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'rad_splatter_tee_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s


def textile_spec(paint,fid):
    assert fid in ('rad_peach_fuzz','rad_aerobics_gym','rad_zigzag_runner','rad_hypercolour','rad_neon_spandex','rad_splatter_tee')
    z=paint.astype(np.float32)/255;scale=paint.shape[0]/2048
    smooth=cv2.GaussianBlur(z,(0,0),max(.6,1.3*scale));hsv=cv2.cvtColor(smooth,cv2.COLOR_RGB2HSV);h,s,v=cv2.split(hsv)
    gray=cv2.cvtColor(z,cv2.COLOR_RGB2GRAY);broad=cv2.GaussianBlur(gray,(0,0),max(1,6*scale))
    tips=np.clip((gray-broad)*7+.5,0,1);seam=np.clip((broad-gray)*6,0,1)
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
    return p,textile_spec(p,'rad_splatter_tee')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_splatter_tee_'+kind+".png"))
