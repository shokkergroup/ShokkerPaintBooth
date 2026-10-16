"""Scoped ASTRA R1 render, contact boards and honest diagnostic evidence."""
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import argparse,json,sys,time,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from engine.expansions.astra import ALL_MODULES
from engine.expansions.astra.rebuild_tools import Surface
from scripts.spb_finish_identity import contract_from_module
OUT=ROOT/'_astra_rebuild_20260922_work'


def render(ids=None):
    report=OUT/'native_report.json'
    rows=json.loads(report.read_text()) if report.exists() else {}
    for m in ALL_MODULES:
        if ids and m.FID not in ids:continue
        contract_from_module(m,m.FID)
        target=OUT/m.FID;target.mkdir(exist_ok=True)
        start=time.perf_counter();p,s=m.build((2048,2048),42);elapsed=time.perf_counter()-start
        assert p.shape==s.shape==(2048,2048,3)
        assert np.isfinite(p).all() and np.isfinite(s).all()
        assert 0<=p.min()<=p.max()<=1 and 0<=s.min()<=s.max()<=255
        pu=np.rint(p*255).astype(np.uint8);su=np.rint(s).astype(np.uint8)
        Image.fromarray(pu).save(target/'paint.png',compress_level=2)
        Image.fromarray(su).save(target/'spec.png',compress_level=2)
        gray=cv2.cvtColor(pu,cv2.COLOR_RGB2GRAY)
        # Diagnostics only. Local energy and lag peaks do not decide identity.
        small=cv2.resize(gray,(256,256),interpolation=cv2.INTER_AREA).astype(float)
        lag={}
        for axis in [0,1]:
            vals=[]
            for d in range(2,33):
                a=small[:-d,:] if axis==0 else small[:,:-d]
                b=small[d:,:] if axis==0 else small[:,d:]
                vals.append(float(np.corrcoef(a.ravel(),b.ravel())[0,1]))
            lag['vertical' if axis==0 else 'horizontal']=max(vals)
        rows[m.FID]=dict(name=m.NAME,lane=m.LANE,seconds=round(elapsed,3),
            paint_hash=hashlib.sha256(pu.tobytes()).hexdigest(),spec_hash=hashlib.sha256(su.tobytes()).hexdigest(),
            spec_range=[[int(su[...,i].min()),int(su[...,i].max())] for i in range(3)],
            spec_std=[round(float(su[...,i].std()),3) for i in range(3)],
            lag_peak=lag,owner_verdict='pending',revision='ASTRA-R1-20260922')
        (target/'identity_contract.json').write_text(json.dumps(m.IDENTITY_CONTRACT,indent=2),encoding='utf-8')
        report.write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(m.FID,round(elapsed,3),'seconds',flush=True)
    assert len({r['paint_hash'] for r in rows.values()})==len(rows)
    assert len({r['spec_hash'] for r in rows.values()})==len(rows)
    contacts()


def contacts():
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    tiny=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13)
    for lane in dict.fromkeys(m.LANE for m in ALL_MODULES):
        sheet=Image.new('RGB',(1550,820),'#101820');draw=ImageDraw.Draw(sheet)
        draw.text((12,8),'ASTRA R1 / '+lane+' | full paint + physical spec; native paint crop below',font=font,fill='white')
        for i,m in enumerate(m for m in ALL_MODULES if m.LANE==lane):
            if not (OUT/m.FID/'paint.png').exists():continue
            x=(i%5)*310;y=40+(i//5)*385
            draw.text((x+7,y),m.NAME,font=font,fill='white')
            paint=Image.open(OUT/m.FID/'paint.png');spec=Image.open(OUT/m.FID/'spec.png')
            sheet.paste(paint.resize((144,144),Image.Resampling.LANCZOS),(x+7,y+28))
            sheet.paste(spec.resize((144,144),Image.Resampling.LANCZOS),(x+157,y+28))
            sheet.paste(paint.crop((730,830,1026,1010)),(x+7,y+179))
            draw.text((x+7,y+361),'Native 1:1 crop / materials shown above',font=tiny,fill='#9db0bb')
        sheet.save(OUT/('contact_'+lane.lower().replace(' ','_')+'.jpg'),quality=94)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+');ap.add_argument('--contacts',action='store_true');args=ap.parse_args()
    contacts() if args.contacts else render(args.ids)
