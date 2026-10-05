"""SPB-105 ERA120: exact owner-approved Chrome Bevel authoring.
Offline signed-distance geometry bake, not the runtime hot path.
Original function bodies preserved from the approved procedural comparison.
M7 is reported separately; owner explicitly requested this version unchanged.
"""
from pathlib import Path
import json,time
import numpy as np
import cv2
from scipy.spatial import Voronoi
from scipy.stats import qmc
from shapely.geometry import Polygon, box, Point
from shapely.affinity import rotate
from PIL import Image
def ramp(t,colors):
    colors=np.asarray(colors,np.float32);u=np.clip(t,0,1)*(len(colors)-1)
    i=np.minimum(u.astype(np.int32),len(colors)-2);a=(u-i)[...,None]
    return colors[i]*(1-a)+colors[i+1]*a

def render(size=2048):
    start=time.perf_counter();rng=np.random.default_rng(170917)
    pts=qmc.PoissonDisk(2,radius=.058,seed=917).fill_space()*size
    offsets=np.array([(x,y) for y in [-size,0,size] for x in [-size,0,size]])
    cloud=np.concatenate([pts+o for o in offsets]);vor=Voronoi(cloud)
    paint=np.zeros((size,size,3),np.float32)+[5,10,26]
    spec=np.zeros((size,size,3),np.float32)+[14,148,142]
    counts={};ss=2
    for index,center in enumerate(pts):
        region=vor.regions[vor.point_region[4*len(pts)+index]]
        cell=Polygon(vor.vertices[region]).buffer(-5,join_style=2)
        x,y=center;kind=index%6;counts[str(kind)]=counts.get(str(kind),0)+1
        if kind==1:
            cell=cell.difference(rotate(box(x+8,y+3,x+160,y+160),rng.uniform(0,360),origin=(x,y)))
        elif kind==2:
            cell=cell.difference(rotate(box(x-18,y-75,x+22,y+17),rng.uniform(0,360),origin=(x,y)))
        elif kind==3:
            cell=cell.difference(Point(x+48,y-28).buffer(40,resolution=32))
        elif kind==4:
            slot=box(x-38,y-6,x+38,y+6).buffer(5)
            cell=cell.difference(rotate(slot,rng.uniform(0,360),origin=(x,y)))
        # Rounded chamfers suppress raster spikes without smoothing the design.
        cell=cell.buffer(-3,join_style=2).buffer(3,quad_segs=4)
        if cell.is_empty:continue
        if cell.geom_type=='MultiPolygon':cell=max(cell.geoms,key=lambda g:g.area)
        minx,miny,maxx,maxy=cell.bounds
        bx,by=int(np.floor(minx))-3,int(np.floor(miny))-3
        w,h=int(np.ceil(maxx))-bx+4,int(np.ceil(maxy))-by+4
        mask=np.zeros((h*ss,w*ss),np.uint8)
        def points(ring):return np.rint((np.array(ring.coords)-[bx,by])*ss).astype(np.int32)
        cv2.fillPoly(mask,[points(cell.exterior)],255)
        for hole in cell.interiors:cv2.fillPoly(mask,[points(hole)],0)
        d=cv2.distanceTransform(mask,cv2.DIST_L2,5)/ss
        nx=cv2.Sobel(d,cv2.CV_32F,1,0,ksize=3);ny=cv2.Sobel(d,cv2.CV_32F,0,1,ksize=3)
        norm=np.maximum(np.hypot(nx,ny),.0001);nx/=norm;ny/=norm
        yy,xx=np.mgrid[:h*ss,:w*ss].astype(np.float32);xx=xx/ss+bx-x;yy=yy/ss+by-y
        angle=rng.uniform(0,2*np.pi);u=np.clip(.5+(xx*np.cos(angle)+yy*np.sin(angle))/170,0,1)
        face=ramp(u,[[4,12,49],[11,38,138],[13,87,235],[79,205,250],[13,37,121]])
        if index%4==0:face=ramp(u,[[16,7,52],[50,18,110],[166,15,147],[251,66,185],[43,13,90]])
        depth=np.clip((d-17)/max(float(d.max())-17,8),0,1)
        pp=face*(.52+.48*depth[...,None])
        # Every enamel/foil face owns a distinct, broad interior material state.
        # Shape depth and its local gradient stay causal across all three channels.
        centers=[[28,28,235],[65,45,185],[20,105,220],[119,25,215],
                 [205,32,190],[36,180,126],[160,52,230],[235,35,72]]
        end=np.array(centers[index%len(centers)],np.float32)
        sp=ramp(depth,[[18,185,55],[24,135,135],end*.8+np.array([10,8,20]),end])
        sp+=np.stack([(u-.5)*35,(u-.5)*24,(u-.5)*38],axis=-1)
        def band(lo,hi,p,s):
            k=(d>=lo)&(d<hi)
            pp[k]=np.broadcast_to(p,pp.shape)[k];sp[k]=np.broadcast_to(s,sp.shape)[k]
        # Chrome shoulder: polished reflection ribbons with clean face normals.
        reflect=np.clip(.5+.43*(nx*.62-ny*.78),0,1)
        silver=ramp(reflect,[[10,21,49],[55,78,116],[202,223,244],[250,252,255],[60,88,130]])
        bevel=np.clip((d-3)/10,0,1)
        silver*= (.65+.35*np.sin(bevel*np.pi))[...,None]
        band(2.3,13,silver,ramp(bevel,[[246,18,27],[231,62,94],[253,22,18]]))
        # Thin colored foil glints run along selected facet normals, not noise.
        ribbon=((nx*np.cos(angle)+ny*np.sin(angle))>.72)&(d>5)&(d<8)
        pp[ribbon]=ramp(u,[[24,84,232],[64,224,255],[247,38,167]])[ribbon]
        sp[ribbon]=ramp(u,[[230,22,166],[251,35,238],[192,65,208]])[ribbon]
        band(.6,2.3,ramp(reflect,[[85,52,28],[251,208,123],[254,242,216]]),ramp(u,[[235,15,183],[255,29,248]]))
        band(13,15,[3,6,17],ramp(u,[[8,175,91],[21,91,116]]))
        band(15,17,ramp(u,[[22,78,221],[159,239,255],[254,76,188]]),ramp(u,[[240,18,211],[253,32,252]]))
        band(0,.6,[5,9,24],[14,148,142])
        alpha=cv2.resize(mask.astype(np.float32)/255,(w,h),interpolation=cv2.INTER_AREA)[...,None]
        pp=cv2.resize(pp,(w,h),interpolation=cv2.INTER_AREA)
        sp=cv2.resize(sp,(w,h),interpolation=cv2.INTER_AREA)
        # Wrap unique boundary-crossing pieces; no repeating quadrant canvas.
        for dx in [-size,0,size]:
            for dy in [-size,0,size]:
                left,top=bx+dx,by+dy;x0,y0=max(left,0),max(top,0);x1,y1=min(left+w,size),min(top+h,size)
                if x0>=x1 or y0>=y1:continue
                sl=np.s_[y0-top:y1-top,x0-left:x1-left];a=alpha[sl]
                paint[y0:y1,x0:x1]=paint[y0:y1,x0:x1]*(1-a)+pp[sl]*a
                spec[y0:y1,x0:x1]=spec[y0:y1,x0:x1]*(1-a)+sp[sl]*a
    paint=np.clip(np.rint(paint),0,255).astype(np.uint8);spec=np.clip(np.rint(spec),0,255).astype(np.uint8)
    spec[...,2]=np.maximum(spec[...,2],16);spec[...,1]=np.where(spec[...,0]>=240,spec[...,1],np.maximum(spec[...,1],15))
    return paint,spec,{'seconds':round(time.perf_counter()-start,3),'pieces':len(pts),'shape_family_counts':counts}


IDENTITY_CONTRACT=json.loads('{"schema": "spb-finish-identity/1", "finish_id": "rad_chrome_type", "display_name": "Grid: Chrome Bevel", "promise": "Tiny blue-to-pink beveled strokes with sharp silver edges and purple enamel valleys.", "carrier_grammar": "Periodic irregular packing of clipped chamfered plates, elbow fragments, crescent terminals, slotted bars and stepped wedges. Analytic inset boundaries and bevel normals; no image sampling.", "spec_grammar": "The same signed edge distance and per-piece face coordinates define fractured perimeter lips, polished shoulders, inset grooves, cool enamel basins, gold trim and facet glints.", "reference_physics": {"mechanism": "The substrate, inlaid materials, polished shoulders, recesses and micro-wear follow their own dielectric or conductive material profiles, with independent roughness and inverse clearcoat response.", "sources": ["SPB_WIKI.html#specbible \\u00e2\\u20ac\\u201d literal packed material rules", "Owner overnight rebuild brief 2026-09-17"]}, "native_scale_px": [60, 220], "mark_types": [{"name": "fractured perimeter lip", "role": "Shared geometric boundary: fractured perimeter lip"}, {"name": "polished bevel shoulder", "role": "Shared geometric boundary: polished bevel shoulder"}, {"name": "colored reflection ribbon", "role": "Shared geometric boundary: colored reflection ribbon"}, {"name": "recessed inset groove", "role": "Shared geometric boundary: recessed inset groove"}, {"name": "enamel depth basin", "role": "Shared geometric boundary: enamel depth basin"}, {"name": "gold perimeter trim", "role": "Shared geometric boundary: gold perimeter trim"}], "material_binding": {"M": ["fractured perimeter lip", "polished bevel shoulder", "colored reflection ribbon", "recessed inset groove", "enamel depth basin", "gold perimeter trim"], "R": ["fractured perimeter lip", "polished bevel shoulder", "colored reflection ribbon", "recessed inset groove", "enamel depth basin", "gold perimeter trim"], "Cc": ["fractured perimeter lip", "polished bevel shoulder", "colored reflection ribbon", "recessed inset groove", "enamel depth basin", "gold perimeter trim"]}, "material_tiers": [{"feature": "fractured perimeter lip", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}, {"feature": "polished bevel shoulder", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}, {"feature": "colored reflection ribbon", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}, {"feature": "recessed inset groove", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}, {"feature": "enamel depth basin", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}, {"feature": "gold perimeter trim", "low": [8, 15, 20], "high": [255, 196, 252], "tiers": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92]}], "nearest_neighbors": [{"finish_id": "rad_big_hair_chrome", "difference": "This finish uses Abstract tiny extruded typographic stroke fragments WITHOUT letters: short beveled wedges, disconnected chamfered elbows and razor thin triangular strokes. Faces gradate cyan into hotpink, edges nearwhite chrome, deep purple sidewalls. Every fragment small and rotated independently; no words, giant shards or bubble metal.; compare boundaries and relief independently of color."}, {"finish_id": "at_y2k_chrome", "difference": "This finish uses Abstract tiny extruded typographic stroke fragments WITHOUT letters: short beveled wedges, disconnected chamfered elbows and razor thin triangular strokes. Faces gradate cyan into hotpink, edges nearwhite chrome, deep purple sidewalls. Every fragment small and rotated independently; no words, giant shards or bubble metal.; compare boundaries and relief independently of color."}], "name_truth": {"hidden_title_verdict": "pass", "visible_evidence": ["Clean silver bevel shoulders", "Blue cyan and magenta recessed faces", "Abstract multidirectional chrome graphic fragments"], "source_sha256": "590d97f46b017412f3db3acc5f1ed811a2adce2a258aa474030aa014c04fc9c9", "owner_verdict": "REBUILD (except this one it is good to go)", "evidence_scope": "Exact approved procedural preview pixels, unchanged"}, "construction_key": "procedural-chrome-geometry-r1", "spec_key": "procedural-chrome-shared-distance-r1", "live_evidence": {"report": "docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md", "structural_threshold_flags": 0, "native_scale_certified": false, "M7": 62.3, "M7_ship_bar_pass": false, "owner_verdict": "pending"}, "owner_scale_authorization": "ERA120-20260917-reviewed-concepts", "fine_detail_scale_px": [1, 16], "owner_approved_concept_version": "7693aee2e701a18512b8127a61edf142382b72aea5619876add8c963f2b489a8"}')
