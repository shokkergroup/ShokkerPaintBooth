"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_vector_horizon", "display_name": "Grid: Vector Terrain", "promise": "Tiny cyan and pink contour facets etched into violet glass with gold junction sparks.", "carrier_grammar": "Tiny cyan and pink contour facets etched into violet glass with gold junction sparks. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Cold continuously graded facet basins, separately identified pink/cyan contour ridges, bright gold/white node flashes.", "reference_physics": {"mechanism": "Tiny cyan and pink contour facets etched into violet glass with gold junction sparks. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/rad_vector_horizon.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "violet contour glass", "role": "Actual shared paint and spec geometry: violet contour glass"}, {"name": "cyan contour edges", "role": "Actual shared paint and spec geometry: cyan contour edges"}, {"name": "pink elevation steps", "role": "Actual shared paint and spec geometry: pink elevation steps"}, {"name": "gold node sparks", "role": "Actual shared paint and spec geometry: gold node sparks"}, {"name": "deep contour valleys", "role": "Actual shared paint and spec geometry: deep contour valleys"}], "material_binding": {"M": ["violet contour glass", "cyan contour edges", "pink elevation steps", "gold node sparks", "deep contour valleys"], "R": ["violet contour glass", "cyan contour edges", "pink elevation steps", "gold node sparks", "deep contour valleys"], "Cc": ["violet contour glass", "cyan contour edges", "pink elevation steps", "gold node sparks", "deep contour valleys"]}, "material_tiers": ["matte cut or sleeve", "satin substrate", "glossy pigment face", "pink polished foil rim", "red chrome shoulder", "green rough undercut", "cool smooth inset", "fine silver glint"], "nearest_neighbors": [{"finish_id": "rad_vector_glow", "difference": "This finish uses Fine irregular triangular contour fragments: tiny cyan wireframe elevations, pink contour steps, narrow violet facets and minute gold junction points. All flat and multidirectional, no horizon or vanishing point. Unequal open triangular topology, not diamond tile grid or laser X strokes.; compare boundaries and relief independently of color."}, {"finish_id": "rad_grid_floor", "difference": "This finish uses Fine irregular triangular contour fragments: tiny cyan wireframe elevations, pink contour steps, narrow violet facets and minute gold junction points. All flat and multidirectional, no horizon or vanishing point. Unequal open triangular topology, not diamond tile grid or laser X strokes.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Small filled triangles show etched terrain facets.", "Fine ridge lines divide the triangular faces.", "Gold nodes punctuate the facet corners and distinguish it from open wireframe glow."], "scale_redraw_required": false, "source_sha256": "88b4fbd9f171e2ca6fcd3bece269dd1f3c45ccd0a13ad9ae1a4a8b800d6edbd8", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "rad_vector_horizon-authored-Tiny cyan and pink contour facets etched into violet glass with gold junction sparks. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "rad_vector_horizon-named-signal-materials-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 75.3, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'rad_vector_horizon_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'rad_vector_horizon_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
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
    else:raise ValueError(fid)
    out=np.rint(out).clip(0,255).astype(np.uint8);cc=out[...,2];cc[(cc>0)&(cc<16)]=16
    return out


def generate(size=2048):
    p,_=generate_base(size)
    return p,signal_spec(p,'rad_vector_horizon')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('rad_vector_horizon_'+kind+".png"))
