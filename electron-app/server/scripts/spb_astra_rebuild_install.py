"""ASTRA-only R1 installation, persistent bakes and served-output verification."""
from pathlib import Path
import argparse,hashlib,io,json,shutil,subprocess,sys,time,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'_astra_rebuild_20260922_work'
ROWS=json.loads((OUT/'inventory.json').read_text())
IDS=[r['FID'] for r in ROWS]


def bake():
    commands=[('standard_bake',[sys.executable,'rebuild_thumbnails.py','--type','base','--keys',*IDS,'--size','128','--quiet']),
              ('split_bake',[sys.executable,'rebuild_picker_swatches.py','--force','--release-gate','--ids',*['base:'+fid for fid in IDS]])]
    for name,cmd in commands:
        with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
            code=subprocess.call(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        assert code==0,(name,code)
        print(name,'complete',flush=True)
    before=json.loads((OUT/'before_hashes.json').read_text())
    for folder in ['base','picker_split/base']:
        for fid in IDS:
            p=ROOT/'thumbnails'/folder/(fid+'.png')
            assert p.is_file(),str(p)
            assert hashlib.sha256(p.read_bytes()).hexdigest()!=before.get(p.relative_to(ROOT).as_posix()),str(p)
    print(f'{len(IDS)*2}/{len(IDS)*2} thumbnail paths changed from baseline',flush=True)


def sync():
    files=[p.relative_to(ROOT) for p in (ROOT/'engine/expansions/astra').rglob('*.py')]
    files += [Path('thumbnails')/folder/(fid+'.png') for folder in ['base','picker_split/base'] for fid in IDS]
    # This file is shared. Merge only our fifty records into the runtime copy.
    rel=Path('thumbnails/picker_split/_manifest.json')
    source=json.loads((ROOT/rel).read_text());target_path=ROOT/'electron-app/server'/rel
    target=json.loads(target_path.read_text())
    for fid in IDS:target['finishes']['base:'+fid]=source['finishes']['base:'+fid]
    target_path.write_text(json.dumps(target,indent=2),encoding='utf-8')
    checks={}
    for rel in files:
        a=ROOT/rel;b=ROOT/'electron-app/server'/rel;b.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(a,b)
        digest=hashlib.sha256(a.read_bytes()).hexdigest()
        assert digest==hashlib.sha256(b.read_bytes()).hexdigest(),str(rel)
        checks[rel.as_posix()]=digest
    (OUT/'runtime_hashes.json').write_text(json.dumps(checks,indent=2))
    print('Scoped runtime mirror:',len(checks),'exact pairs; 50 manifest entries',flush=True)


def live():
    import numpy as np
    from PIL import Image
    base='http://127.0.0.1:59876'
    fp=json.load(urllib.request.urlopen(base+'/api/swatch-fingerprints',timeout=60))
    (OUT/'served_fingerprints.json').write_text(json.dumps(fp,indent=2))
    manifest=json.loads((ROOT/'thumbnails/picker_split/_manifest.json').read_text())['finishes']
    previous=OUT/'live_report.json'
    report=[r for r in json.loads(previous.read_text()) if r['id'] not in IDS] if len(IDS)<50 and previous.exists() else []
    for i,fid in enumerate(IDS):
        key='base:'+fid;record={'id':fid,'fingerprint':fp['fp'][key]}
        for size in [512,256,128,48]:
            params=dict(color=manifest[key]['color_hex'],size=size,mode='split',prefer='live',source='faithful-v1',seed=42,v=fp['fp'][key])
            url=base+'/api/swatch/base/'+fid+'?'+urllib.parse.urlencode(params)
            start=time.perf_counter()
            with urllib.request.urlopen(url,timeout=180) as res:
                raw=res.read();assert res.status==200
            im=Image.open(io.BytesIO(raw)).convert('RGB');assert im.size==(size*2,size)
            (OUT/fid/('served_'+str(size)+'.png')).write_bytes(raw)
            record['served_'+str(size)]=dict(bytes=len(raw),seconds=round(time.perf_counter()-start,3),sha256=hashlib.sha256(raw).hexdigest())
            # Compare to independently saved current full native images.
            errors=[]
            for side,kind in enumerate(['paint','spec']):
                expected=Image.open(OUT/fid/(kind+'.png')).resize((size,size),Image.Resampling.BOX)
                actual=np.asarray(im.crop((side*size,0,(side+1)*size,size))).astype(float)
                errors.append(float(np.abs(actual-np.asarray(expected)).mean()))
            record['mae_'+str(size)]=errors
            assert max(errors)<1.6,(fid,size,errors)
        for folder in ['base','picker_split/base']:
            url=base+'/thumbnails/'+folder+'/'+fid+'.png'
            raw=urllib.request.urlopen(url,timeout=30).read()
            assert raw==(ROOT/'thumbnails'/folder/(fid+'.png')).read_bytes(),(fid,folder)
        # Full masters persist under renderer identity and are mirrored by name.
        identity=[fp['fp'][key],'base',fid,manifest[key]['color_hex'],42]
        digest=hashlib.sha256(json.dumps(['faithful-v1',*identity]).encode()).hexdigest()
        cache=ROOT/'thumbnails/swatch_cache/faithful_split_v1'
        persisted=[]
        for suffix in ['','_256','_128','_48']:
            p=cache/(digest+suffix+'.png')
            assert p.is_file(),('not persisted',fid,str(p))
            target=ROOT/'electron-app/server'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target);assert p.read_bytes()==target.read_bytes()
            persisted.append(p.relative_to(ROOT).as_posix())
        record['persistent_files']=persisted
        report.append(record);(OUT/'live_report.json').write_text(json.dumps(report,indent=2))
        if i%5==0 or i==len(IDS)-1:print('Live verified',i+1,'/',len(IDS),'native + standard + four picker sizes + persistent mirrors',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['bake','sync','live']);ap.add_argument('--ids',nargs='+');args=ap.parse_args()
    if args.ids:
        assert set(args.ids)<=set(IDS)
        IDS=args.ids
    globals()[args.action]()
