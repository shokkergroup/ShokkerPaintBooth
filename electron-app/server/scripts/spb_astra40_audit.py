"""Forty-card native proof and complete fifty-card identity comparison.

SPB-105 / W1. Preserve original artifacts; use unchanged gates and thresholds.
"""
from pathlib import Path
import os
# Tiny 128x128 identity descriptors do not benefit from a large BLAS pool.
# The math, transform coverage and thresholds remain exactly the same.
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,json,sys,time,itertools,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from engine.expansions.astra import MODULES as ORIGINALS
from engine.expansions.astra.wave2 import MODULES
from scripts.spb_finish_identity import contract_from_module
from scripts.spb_finish_law import scale_axis,follow_axis,coverage_axis,richness_axis,richness_eff,MIN_FINE,MIN_FOLLOW,MAX_DEAD
from scripts.spb_wilds_m7_evidence import _paint_metrics,_spec_metrics
from scripts.spb_iridescent_insects_similarity_gate import _features,_structure,_corr,_d4_variants,_phase_response
OUT=ROOT/'_astra40_work'
OLD=ROOT/'_archive/root_cleanup_2026-09-05/lane_work/_astra_work'
def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def count_rgb(p):
    q=p.astype(np.uint32);return int(len(np.unique(q[...,0]*65536+q[...,1]*256+q[...,2])))
def render(ids=None):
    report=OUT/'native_report.json';rows=json.loads(report.read_text()) if report.exists() else {}
    for m in MODULES:
        if ids and m.FID not in ids:continue
        c=contract_from_module(m,m.FID);target=OUT/m.FID;target.mkdir(exist_ok=True)
        times=[]
        for trial in range(3):
            t=time.perf_counter();p,s=m.build((2048,2048),42);times.append(time.perf_counter()-t)
        pu=np.clip(p*255,0,255).astype(np.uint8);su=np.clip(s,0,255).astype(np.uint8)
        Image.fromarray(pu).save(target/'paint.png',compress_level=2);Image.fromarray(su).save(target/'spec.png',compress_level=2)
        pm,sm=_paint_metrics(p),_spec_metrics(s)
        fp,_=scale_axis(cv2.cvtColor(p,cv2.COLOR_RGB2GRAY));fs,_=scale_axis(cv2.cvtColor(s/255,cv2.COLOR_RGB2GRAY))
        mi,edge=follow_axis(p,s);dead=coverage_axis(p);materials,shades=richness_axis(s)
        law=dict(fine_paint=fp,fine_spec=fs,follow_mi=mi,follow_edge=edge,dead=dead,materials=materials,shades=shades,effective_materials=richness_eff(s))
        law['pass']=bool(max(fp,fs)>=MIN_FINE and edge>=MIN_FOLLOW and dead<=MAX_DEAD)
        counts=dict(paint=count_rgb(pu),spec=count_rgb(su))
        rows[m.FID]=dict(name=m.NAME,lane=m.LANE,seconds=times,paint_metrics=pm,spec_metrics=sm,law=law,distinct_rgb=counts,
            paint_hash=hashlib.sha256(pu.tobytes()).hexdigest(),spec_hash=hashlib.sha256(su.tobytes()).hexdigest())
        (target/'identity_contract.json').write_text(json.dumps(c,indent=2))
        save('native_report.json',rows)
        print(m.FID,'sec',round(max(times),2),'law',law['pass'],'follow',round(edge,3),'colors',counts,flush=True)
    contact()
def contact():
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    for lane in dict.fromkeys(m.LANE for m in MODULES):
        sheet=Image.new('RGB',(1500,1190),'#111621');draw=ImageDraw.Draw(sheet)
        draw.text((14,10),'ASTRA / '+lane+' / native paint & packed spec',font=font,fill='white')
        for i,m in enumerate(q for q in MODULES if q.LANE==lane):
            if not (OUT/m.FID/'paint.png').exists():continue
            x=i%5*300;y=45+i//5*570
            draw.text((x+8,y),m.NAME,font=font,fill='white')
            for j,kind in enumerate(('paint','spec')):
                p=Image.open(OUT/m.FID/(kind+'.png'))
                sheet.paste(p.crop((740,812,1024,1052)),(x+8,y+28+j*252))
        sheet.save(OUT/(lane.lower().replace(' ','_')+'.jpg'),quality=94)
def similarity():
    # Cache descriptors once. Arithmetic and phase gate are identical to the
    # canonical insect gate; no threshold tuning or sparse pair sampling.
    bank={}
    for m in ORIGINALS+MODULES:
        src=OLD if m in ORIGINALS else OUT
        p=cv2.imread(str(src/m.FID/'paint.png'));s=cv2.imread(str(src/m.FID/'spec.png'))
        z=cv2.imread(str(ROOT/'thumbnails/picker_split/base'/f'{m.FID}.png'))
        standard=cv2.imread(str(ROOT/'thumbnails/base'/f'{m.FID}.png'))
        assert z is not None and standard is not None,m.FID
        mid=z.shape[1]//2
        views=dict(full_paint=p,full_spec=s,native_paint=p[704:1088,768:1152],native_spec=s[704:1088,768:1152],
                   picker_paint=z[:,:mid],picker_spec=z[:,mid:],standard=standard)
        for c in range(3):
            for label,img in [('full',s),('native',s[704:1088,768:1152]),('picker',z[:,mid:])]:
                views[f'{label}_channel_{c}']=np.repeat(img[...,c,None],3,axis=2)
        bank[m.FID]={k:(*_features(v),_structure(v)) for k,v in views.items()}
    rows=[]
    for i,(a,b) in enumerate(itertools.combinations(bank,2)):
        spaces={}
        for k in bank[a]:
            ag,ae,ast=bank[a][k];bg,be,bst=bank[b][k]
            value=max(_corr(ag,bg),_corr(ae,be))
            for variant in _d4_variants(bst):value=max(value,_corr(ast,variant),_phase_response(ast,variant))
            spaces[k]=round(value,5)
        # Also compare cross-channel copies: a reused M carrier moved into R
        # is still the same material construction, even if other channels differ.
        for scale in ('full','native','picker'):
            for ac in range(3):
                for bc in range(3):
                    if ac==bc:continue
                    ag,ae,ast=bank[a][f'{scale}_channel_{ac}'];bg,be,bst=bank[b][f'{scale}_channel_{bc}']
                    value=max(_corr(ag,bg),_corr(ae,be))
                    for variant in _d4_variants(bst):value=max(value,_corr(ast,variant),_phase_response(ast,variant))
                    spaces[f'{scale}_channel_{ac}_to_{bc}']=round(value,5)
        maximum=max(spaces.values());rows.append(dict(a=a,b=b,maximum=maximum,spaces=spaces,status='reject' if maximum>=.68 else 'owner-review' if maximum>=.55 else 'pass'))
        if i%50==0:print('identity pairs',i+1,'/1225',flush=True)
    rows.sort(key=lambda r:-r['maximum']);save('similarity.json',rows)
    print('Pairs',len(rows),'max',rows[0]['maximum'],'flagged',sum(r['status']!='pass' for r in rows),flush=True)
def preserve():
    old=json.loads((OUT/'original_hashes.json').read_text())
    bad=[p for p,h in old.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not bad,bad
    print('Original byte-preservation:',len(old),'PASS')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+');ap.add_argument('--similarity',action='store_true');ap.add_argument('--contact',action='store_true');ap.add_argument('--preserve',action='store_true');args=ap.parse_args()
    if args.similarity:similarity()
    elif args.contact:contact()
    elif args.preserve:preserve()
    else:render(args.ids)
