"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_sodium_vapour", "display_name": "Street: Amber Discharge", "promise": "Amber plasma filaments and violet glass specks form a fine branching discharge texture.", "carrier_grammar": "Amber plasma filaments and violet glass specks form a fine branching discharge texture. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Violet glass cells grade continuously through cold smooth faces and rough dark seams. Amber branches own satin shoulders and polished hot glints; cobalt pits have separate cold basins and bright narrow rims; pale gold ion points are sparse polished foil.", "reference_physics": {"mechanism": "Amber plasma filaments and violet glass specks form a fine branching discharge texture. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_sodium_vapour.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "violet glass field", "role": "Actual shared paint and spec geometry: violet glass field"}, {"name": "amber discharge threads", "role": "Actual shared paint and spec geometry: amber discharge threads"}, {"name": "cobalt micro pits", "role": "Actual shared paint and spec geometry: cobalt micro pits"}, {"name": "pale gold ion points", "role": "Actual shared paint and spec geometry: pale gold ion points"}, {"name": "dark glass seams", "role": "Actual shared paint and spec geometry: dark glass seams"}], "material_binding": {"M": ["violet glass field", "amber discharge threads", "cobalt micro pits", "pale gold ion points", "dark glass seams"], "R": ["violet glass field", "amber discharge threads", "cobalt micro pits", "pale gold ion points", "dark glass seams"], "Cc": ["violet glass field", "amber discharge threads", "cobalt micro pits", "pale gold ion points", "dark glass seams"]}, "material_tiers": ["violet smooth glass", "rough dark glass seam", "amber satin branch shoulder", "polished filament glint", "cobalt cold pit basin", "pit rim glint", "pale gold ion foil"], "nearest_neighbors": [{"finish_id": "cbp_overpass_sodium", "difference": "This finish uses Dense tiny amber branching discharge filament fragments in violet glass, orange core needles, cobalt micro pits, pale gold ion pinpoints and dark glass seams. Short Y-shaped electrical branches never long connected lightning bolts. No bulbs or objects, no horizon, no generic polygon network.; compare boundaries and relief independently of color."}, {"finish_id": "rad_phosphor_green", "difference": "This finish uses Dense tiny amber branching discharge filament fragments in violet glass, orange core needles, cobalt micro pits, pale gold ion pinpoints and dark glass seams. Short Y-shaped electrical branches never long connected lightning bolts. No bulbs or objects, no horizon, no generic polygon network.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Tiny amber branching discharge marks cross dark violet resin.", "Blue pores interrupt the discharge texture.", "Fine isolated crackle replaces long oversized bolts."], "scale_redraw_required": false, "source_sha256": "bf7b4e33d3bd7aa620a8c7440d7a1955e82697dadefc7d8de7004e627f3547df", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "cbp_sodium_vapour-authored-Amber plasma filaments and violet glass specks form a fine branching discharge texture. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_sodium_vapour-branch-glass-pit-ion-materials-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 75.4, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'cbp_sodium_vapour_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_sodium_vapour_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
    _,s=render(sr,size)
    return p,s


def signal_spec(paint,fid):
    z=paint.astype(np.float32)/255;hsv=cv2.cvtColor(z,cv2.COLOR_RGB2HSV);h,s,v=cv2.split(hsv)
    scale=paint.shape[0]/2048;gray=cv2.cvtColor(z,cv2.COLOR_RGB2GRAY)
    dx=cv2.Sobel(gray,cv2.CV_32F,1,0);dy=cv2.Sobel(gray,cv2.CV_32F,0,1)
    edge=np.clip(np.hypot(dx,dy)*1.2,0,1)
    def ramp(t,colors):
        c=np.array(colors,np.float32);u=np.clip(t,0,1)*(len(c)-1);i=np.minimum(u.astype(np.int32),len(c)-2);a=(u-i)[...,None]
        return c[i]*(1-a)+c[i+1]*a
    def hue_band(center,width):
        d=np.abs((h-center+180)%360-180);return np.clip(1-d/width,0,1)*np.clip((s-.18)/.5,0,1)
    if fid=='rad_static_snow':
        # Cold television glass and dark dropout pits remain visible between
        # the actual RGB shards. No image-wide random noise or rainbow carrier.
        out=ramp(v,[[3,198,50],[8,130,92],[12,48,218],[28,22,178],[18,60,230]])
        families=[(0,42,[[238,35,24],[253,16,55],[214,80,40]]),
                  (58,30,[[225,108,16],[252,65,32],[239,132,48]]),
                  (120,55,[[8,220,60],[24,155,112],[14,195,44]]),
                  (220,55,[[10,75,225],[22,24,180],[35,52,242]]),
                  (306,38,[[226,45,220],[252,16,241],[210,72,180]])]
        for center,width,colors in families:
            w=(hue_band(center,width)*np.clip((v-.1)/.4,0,1))[...,None]
            field=ramp(np.clip(v*.7+edge*.3,0,1),colors);out=out*(1-w)+field*w
        # The glass catches sparse polished lips at actual bright tear edges.
        lip=np.clip((edge-.48)/.52,0,1)*np.clip((v-.55)/.45,0,1)*.5
        out=out*(1-lip[...,None])+np.array([250,20,226],np.float32)*lip[...,None]
    elif fid=='rad_vector_horizon':
        # Facet basins have continuous cold material fields; wire color and
        # actual local contrast identify raised pink/cyan contour ridges.
        out=ramp(v,[[5,174,68],[18,102,204],[42,48,235],[90,35,185],[28,82,220]])
        contour=np.maximum(hue_band(196,38),hue_band(308,32))*np.clip((v-.3)/.55,0,1)
        ridges=np.clip(contour*.75+edge*.55,0,1)
        # The etched ridge owns a real sequence of material zones inside its
        # facet: pink metal lip, dark groove, rough green shoulder, cold glass
        # basin. Distance is measured from this painting's wires, never a
        # generic wave laid over the design.
        distance=cv2.distanceTransform((ridges<.27).astype(np.uint8),cv2.DIST_L2,5)
        depth=np.clip(distance/max(24*scale,1),0,1)
        bands=ramp(depth,[[249,20,236],[24,28,64],[18,208,88],[30,85,184],[12,38,224]])
        core=ramp(v,[[5,98,235],[22,42,218],[42,132,172],[18,65,240]])
        core_weight=np.clip((depth-.65)/.35,0,1)[...,None]*.55
        out=bands*(1-core_weight)+core*core_weight
        hot=ramp(np.clip(v*.6+edge*.4,0,1),[[210,70,180],[247,22,232],[254,15,44],[236,52,218]])
        out=out*(1-ridges[...,None])+hot*ridges[...,None]
        node=np.maximum(hue_band(48,34)*np.clip((v-.5)/.4,0,1),np.clip((gray-.8)/.2,0,1))
        nodes=ramp(v,[[225,88,32],[250,20,16],[254,5,24]])
        out=out*(1-node[...,None])+nodes*node[...,None]
    elif fid=='cbp_sodium_vapour':
        # Tick35: amber branches, violet glass cells and cobalt pits must each
        # own material anatomy instead of flat blue plus pink branch stamps.
        out=ramp(v,[[5,183,65],[10,108,226],[22,36,197],[16,83,238],[35,24,154]])
        amber=hue_band(39,43)*np.clip((v-.25)/.65,0,1)
        branch=ramp(np.clip(amber*.7+edge*.3,0,1),[[15,162,88],[24,73,204],[168,52,183],[239,20,223],[253,8,38]])
        weight=np.clip(amber*1.4,0,1)[...,None];out=out*(1-weight)+branch*weight
        pit=hue_band(229,27)*np.clip((.72-gray)/.6,0,1)
        basins=ramp(v,[[2,202,62],[4,120,240],[18,45,225],[28,86,180]])
        out=out*(1-pit[...,None])+basins*pit[...,None]
        rim=np.clip(edge*pit*2.1,0,1)[...,None]
        out=out*(1-rim)+ramp(v,[[42,145,72],[219,40,214],[250,12,230]])*rim
        seam=np.clip((.16-gray)/.12,0,1)[...,None]
        out=out*(1-seam)+np.array([5,214,55],np.float32)*seam
        ions=np.clip((gray-.64)/.3,0,1)*np.clip((.55-s)/.4,0,1)
        out=out*(1-ions[...,None])+ramp(v,[[212,75,32],[250,18,16],[255,5,27]])*ions[...,None]
    else:raise ValueError(fid)
    out=np.rint(out).clip(0,255).astype(np.uint8);cc=out[...,2];cc[(cc>0)&(cc<16)]=16
    return out


def generate(size=2048):
    p,_=generate_base(size)
    return p,signal_spec(p,'cbp_sodium_vapour')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_sodium_vapour_'+kind+".png"))
