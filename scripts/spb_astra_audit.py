"""ASTRA native, identity and performance evidence. SPB-105 / ASTRA A1."""
from pathlib import Path
import argparse
import contextlib
import hashlib
import io
import itertools
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from engine.expansions.astra import MODULES
from scripts.spb_finish_identity import contract_from_module
from scripts.spb_iridescent_insects_similarity_gate import _identity_similarity
from scripts.spb_finish_law import scale_axis,follow_axis,coverage_axis,richness_axis,richness_eff,MIN_FINE,MIN_FOLLOW,MAX_DEAD
from scripts.spb_wilds_m7_evidence import _paint_metrics,_spec_metrics

OUT=ROOT/'_astra_work'

def save_json(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def render(ids=None):
    OUT.mkdir(exist_ok=True)
    rows=json.loads((OUT/'native_report.json').read_text()) if ids and (OUT/'native_report.json').exists() else {}
    for module in MODULES:
        if ids and module.FID not in ids: continue
        contract=contract_from_module(module,module.FID)
        run=OUT/module.FID; run.mkdir(exist_ok=True)
        times=[]
        for trial in range(3):
            start=time.perf_counter(); p,s=module.build((2048,2048),42)
            times.append(time.perf_counter()-start)
        pu=np.clip(p*255,0,255).astype(np.uint8); su=np.clip(s,0,255).astype(np.uint8)
        Image.fromarray(pu).save(run/'paint.png',compress_level=3)
        Image.fromarray(su).save(run/'spec.png',compress_level=3)
        pm,sm=_paint_metrics(p),_spec_metrics(s)
        pl=cv2.cvtColor(p,cv2.COLOR_RGB2GRAY)
        sl=cv2.cvtColor(s/255.,cv2.COLOR_RGB2GRAY)
        fine_p,_=scale_axis(pl); fine_s,_=scale_axis(sl)
        mi,edge=follow_axis(p,s); dead=coverage_axis(p)
        materials,shades=richness_axis(s)
        law=dict(fine_paint=fine_p,fine_spec=fine_s,follow_mi=mi,follow_edge=edge,dead=dead,
                 materials=materials,shades=shades,effective_materials=richness_eff(s))
        law['pass']=bool(max(fine_p,fine_s)>=MIN_FINE and edge>=MIN_FOLLOW and dead<=MAX_DEAD)
        rows[module.FID]=dict(name=module.NAME,seconds=times,paint_metrics=pm,spec_metrics=sm,law=law,
                paint_hash=hashlib.sha256(pu.tobytes()).hexdigest(),spec_hash=hashlib.sha256(su.tobytes()).hexdigest())
        save_json(run/'identity_contract.json',contract)
        print(module.FID,'seconds',','.join(f'{t:.3f}' for t in times),'law',law['pass'],
              'fine',round(max(fine_p,fine_s),3),'follow',round(edge,3),flush=True)
    save_json(OUT/'native_report.json',rows)
    contact()

def contact():
    try: font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    except OSError: font=ImageFont.load_default()
    sheet=Image.new('RGB',(1500,1220),'#10131d'); draw=ImageDraw.Draw(sheet)
    draw.text((20,14),'ASTRA / Native 2048 paint + literal M / Rough / Cc',font=font,fill='white')
    for i,m in enumerate(MODULES):
        x=(i%5)*300; y=48+(i//5)*584
        p=Image.open(OUT/m.FID/'paint.png'); s=Image.open(OUT/m.FID/'spec.png')
        draw.text((x+10,y),m.NAME,font=font,fill='#ebe6db')
        # Native 1:1 crop, no upscaling; immediately below: same-location spec.
        sheet.paste(p.crop((740,812,1020,1044)),(x+10,y+30))
        sheet.paste(s.crop((740,812,1020,1044)),(x+10,y+270))
        sheet.paste(p.resize((136,68),Image.Resampling.LANCZOS),(x+10,y+508))
        sheet.paste(s.resize((136,68),Image.Resampling.LANCZOS),(x+154,y+508))
    sheet.save(OUT/'contact_native.jpg',quality=94)

def similarity():
    records=[]
    # A standard full field, a native 384px crop, and actual picker paint/spec
    # when baked. Max channels detects reused individual material carriers too.
    bank={}
    for m in MODULES:
        p=cv2.imread(str(OUT/m.FID/'paint.png')); s=cv2.imread(str(OUT/m.FID/'spec.png'))
        bank[m.FID]={'full_paint':p,'full_spec':s,'native_paint':p[704:1088,768:1152],
                    'native_spec':s[704:1088,768:1152]}
        for c in range(3):
            bank[m.FID][f'channel_{c}']=np.repeat(s[...,c,None],3,axis=2)
            bank[m.FID][f'native_channel_{c}']=np.repeat(s[704:1088,768:1152,c,None],3,axis=2)
        pick=ROOT/'thumbnails/picker_split/base'/f'{m.FID}.png'
        standard=ROOT/'thumbnails/base'/f'{m.FID}.png'
        if pick.exists():
            z=cv2.imread(str(pick)); mid=z.shape[1]//2
            bank[m.FID].update(picker_paint=z[:,:mid],picker_spec=z[:,mid:])
            for c in range(3):
                bank[m.FID][f'picker_channel_{c}']=np.repeat(z[:,mid:,c,None],3,axis=2)
        if standard.exists(): bank[m.FID]['standard']=cv2.imread(str(standard))
    for a,b in itertools.combinations(bank,2):
        scores={}
        for space in bank[a].keys() & bank[b].keys():
            z=_identity_similarity(bank[a][space],bank[b][space])
            scores[space]=round(max(z.direct,z.transformed,z.phased),5)
        maximum=max(scores.values())
        records.append(dict(a=a,b=b,maximum=maximum,spaces=scores,
                            verdict='reject' if maximum>=.68 else 'owner_review' if maximum>=.55 else 'pass'))
    records.sort(key=lambda z:-z['maximum'])
    save_json(OUT/'similarity.json',records)
    print(json.dumps(dict(pairs=len(records),reject=sum(r['verdict']=='reject' for r in records),
              review=sum(r['verdict']=='owner_review' for r in records),top=records[:3]),indent=2))
    neighbours=[]
    for m in MODULES:
        for neighbor in m.IDENTITY_CONTRACT['nearest_neighbors']:
            fid=neighbor['finish_id']
            if fid in bank: continue
            paths=[ROOT/'thumbnails/picker_split'/kind/(fid+'.png') for kind in ('base','monolithic')]
            found=next((p for p in paths if p.exists()),None)
            if found is None:
                neighbours.append(dict(id=m.FID,neighbor=fid,status='missing_reference'))
                continue
            z=cv2.imread(str(found)); mid=z.shape[1]//2
            scores=[]
            for space,ref in [('picker_paint',z[:,:mid]),('picker_spec',z[:,mid:])]:
                candidate=bank[m.FID].get(space)
                if candidate is None: continue
                score=_identity_similarity(candidate,ref)
                scores.append(max(score.direct,score.transformed,score.phased))
            value=max(scores) if scores else None
            neighbours.append(dict(id=m.FID,neighbor=fid,maximum=value,
                status='reject' if value is not None and value>=.68 else 'review' if value is not None and value>=.55 else 'pass'))
    save_json(OUT/'neighbors.json',neighbours)
    print('Nearest existing material comparisons:',len(neighbours),'max',max((r.get('maximum') or 0) for r in neighbours),flush=True)
    return not any(r['verdict']!='pass' for r in records) and not any(r['status'] in ('reject','review') for r in neighbours)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--similarity',action='store_true'); ap.add_argument('--contact',action='store_true'); ap.add_argument('--ids',nargs='+')
    args=ap.parse_args()
    if args.similarity: raise SystemExit(0 if similarity() else 1)
    elif args.contact: contact()
    else: render(args.ids)
