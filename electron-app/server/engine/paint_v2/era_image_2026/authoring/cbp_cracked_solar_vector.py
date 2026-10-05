"""SPB-105 ERA120 tick27: offline procedural authoring from the exact
owner-approved reference. Cubic curves and bounded fitted gradients, no runtime
source bitmap. The app consumes baked paired PNGs. Qualification is separate.
"""
from pathlib import Path
import gzip,json,re,sys
import numpy as np,cv2,skia
from PIL import Image

IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "cbp_cracked_solar", "display_name": "Sprawl: Solar Fracture", "promise": "Tiny sapphire solar-cell shards with copper busbars and magenta fractured edges.", "carrier_grammar": "Tiny sapphire solar-cell shards with copper busbars and magenta fractured edges. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_grammar": "Cold graded photovoltaic cell faces contrast with cyan rough glass shoulders, polished magenta fracture lips, metallic gold busbars and sparse white glints. Material changes follow the named painted cell and crack anatomy.", "reference_physics": {"mechanism": "Tiny sapphire solar-cell shards with copper busbars and magenta fractured edges. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology. These named surfaces bind the packed metallic, roughness and clearcoat states; painted highlights are not an emissive shader.", "sources": ["SPB_WIKI.html#spec_guide", "_era120_work/concept_review/briefs/cbp_cracked_solar.json", "_era120_work/implementation/owner_decisions_active.json"]}, "native_scale_px": [8, 420], "mark_types": [{"name": "sapphire wafer shards", "role": "Actual shared paint and spec geometry: sapphire wafer shards"}, {"name": "copper busbars", "role": "Actual shared paint and spec geometry: copper busbars"}, {"name": "magenta fracture edges", "role": "Actual shared paint and spec geometry: magenta fracture edges"}, {"name": "cyan crystal points", "role": "Actual shared paint and spec geometry: cyan crystal points"}, {"name": "black cell gaps", "role": "Actual shared paint and spec geometry: black cell gaps"}, {"name": "wafer polish sparks", "role": "Actual shared paint and spec geometry: wafer polish sparks"}], "material_binding": {"M": ["sapphire wafer shards", "copper busbars", "magenta fracture edges", "cyan crystal points", "black cell gaps", "wafer polish sparks"], "R": ["sapphire wafer shards", "copper busbars", "magenta fracture edges", "cyan crystal points", "black cell gaps", "wafer polish sparks"], "Cc": ["sapphire wafer shards", "copper busbars", "magenta fracture edges", "cyan crystal points", "black cell gaps", "wafer polish sparks"]}, "material_tiers": ["cold photovoltaic cell face", "rough cyan fractured shoulder", "polished magenta crack lip", "gold metal busbar", "dark cell separation", "white glass edge glint"], "nearest_neighbors": [{"finish_id": "cbp_subdermal_plate", "difference": "This finish uses Dense microscopic sapphire photovoltaic wafer shards, very fine copper busbar dashes, magenta fracture edges, cyan crystalline grain points and black cell gaps. Short parallel micro lines within irregular tiny wafers, no broad solar panels or big shards.; compare boundaries and relief independently of color."}, {"finish_id": "rad_laserdisc_rainbow", "difference": "This finish uses Dense microscopic sapphire photovoltaic wafer shards, very fine copper busbar dashes, magenta fracture edges, cyan crystalline grain points and black cell gaps. Short parallel micro lines within irregular tiny wafers, no broad solar panels or big shards.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Small blue plate fragments carry fine parallel grooves.", "Copper busbars cross violet fracture seams.", "Cyan splinters and black gaps distinguish broken solar faces from contacts."], "scale_redraw_required": false, "source_sha256": "3331a77c8f0b9311f35a283dece02bd2190712aae5a5519905193e96182f52d5", "review_stage": "Source visually reviewed; installed paint/spec, picker and export verified. Owner visual approval and strict fine-scale qualification remain open."}, "construction_key": "cbp_cracked_solar-authored-Tiny sapphire solar-cell shards with copper busbars and magenta fractured edges. The approved composition and native form scale are preserved as unique fitted cubic paths and bounded polynomial color fields; small source speckle is removed from topology.", "spec_key": "cbp_cracked_solar-cold-cell-fracture-busbar-v1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 85.1, "M7_ship_bar_pass": true, "owner_verdict": "pending"}, "fine_detail_scale_px": [1, 16], "owner_scale_authorization": "ERA120-20260917-reviewed-concepts"}')

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
    with gzip.open(root/'cbp_cracked_solar_paint.recipe.json.gz',"rt",encoding="utf8") as f: pr=json.load(f)
    p,_=render(pr,size)
    with gzip.open(root/'cbp_cracked_solar_spec.recipe.json.gz',"rt",encoding="utf8") as f: sr=json.load(f)
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
    elif fid=='cbp_cracked_solar':
        # Tick36: cold cell faces, fractured glass edges and metal busbars
        # replace the uniform hot-pink panel field without changing paint.
        out=ramp(v,[[3,184,60],[9,103,211],[20,42,238],[40,75,187],[17,23,228]])
        cell=hue_band(231,32)
        cell_state=ramp(v,[[4,45,223],[12,192,62],[42,120,225],[106,98,146],[146,25,204]])
        out=out*(1-cell[...,None])+cell_state*cell[...,None]
        cyan=hue_band(190,33)*np.clip((v-.28)/.6,0,1)
        shoulder=ramp(np.clip(v*.7+edge*.3,0,1),[[9,218,65],[27,158,127],[64,76,208],[183,24,236]])
        out=out*(1-cyan[...,None])+shoulder*cyan[...,None]
        fracture=hue_band(302,35)*np.clip(v/.65,0,1)
        lip=ramp(np.clip(v*.55+edge*.45,0,1),[[23,152,65],[87,71,184],[221,25,222],[253,9,240]])
        out=out*(1-fracture[...,None])+lip*fracture[...,None]
        cells=((h>212)&(h<259)&(s>.3)&(gray<.34)).astype(np.uint8)
        cells=cv2.morphologyEx(cells,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        signed=(cv2.distanceTransform(cells,cv2.DIST_L2,5)-cv2.distanceTransform(1-cells,cv2.DIST_L2,5))/max(scale,.01)
        shoulder_band=np.exp(-((signed+4)/2.8)**2)[...,None]
        out=out*(1-shoulder_band)+ramp(v,[[10,220,48],[24,173,105],[48,205,77]])*shoulder_band
        razor=np.exp(-((signed-.6)/1.35)**2)[...,None]
        out=out*(1-razor)+ramp(v,[[226,28,208],[249,9,238],[254,16,186]])*razor
        bars=np.clip(1-np.abs((h-43+180)%360-180)/36,0,1)*np.clip((s-.06)/.23,0,1)*np.clip((v-.25)/.45,0,1)
        metal=ramp(v,[[191,78,39],[238,24,16],[254,6,30]])
        out=out*(1-bars[...,None])+metal*bars[...,None]
        sparkle=np.clip((gray-.76)/.22,0,1)[...,None]
        out=out*(1-sparkle)+np.array([249,7,19],np.float32)*sparkle
    else:raise ValueError(fid)
    out=np.rint(out).clip(0,255).astype(np.uint8);cc=out[...,2];cc[(cc>0)&(cc<16)]=16
    return out


def generate(size=2048):
    p,_=generate_base(size)
    return p,signal_spec(p,'cbp_cracked_solar')

if __name__=="__main__":
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    p,s=generate()
    for kind,a in [("paint",p),("spec",s)]:Image.fromarray(a).save(out/('cbp_cracked_solar_'+kind+".png"))
