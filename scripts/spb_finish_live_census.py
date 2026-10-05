"""Capture actual base picker responses, read-only with respect to finish sources.

GET requests use the normal content-addressed cache (may warm missing thumbnails).
Protected favorites are measured only from an already present matching master.
"""
import argparse
import concurrent.futures
import hashlib
import io
import json
import time
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import urlopen

from PIL import Image
from spb_finish_intent_audit import ROOT, OUT, measure

FAVORITES = {'fl_eddy_impedance','fl_photoelastic_iso','fl_isoclinic_dark','fl_magnetic_particle'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    catalog = json.loads((OUT/'catalog_snapshot.json').read_text(encoding='utf8'))
    with urlopen(args.server+'/api/swatch-fingerprints',timeout=20) as response:
        fingerprints = json.load(response)
    (OUT/'served_fingerprints.json').write_text(json.dumps(fingerprints),encoding='utf8')
    fp = fingerprints['fp']
    cache = ROOT/'thumbnails/swatch_cache/faithful_split_v1'
    output = OUT/'live_base_pairs'
    output.mkdir(exist_ok=True)
    protected = set(json.loads((ROOT/'scripts/protected_finishes.json').read_text(encoding='utf8'))['locked']) | FAVORITES
    previous = {}
    if args.resume and (OUT/'live_progress.jsonl').is_file():
        previous = {r['key']: r for r in (json.loads(line) for line in (OUT/'live_progress.jsonl').read_text(encoding='utf8').splitlines()) if r['status']=='ok'}

    def capture(item):
        fid = item['id']; color = item.get('swatch','888888').lstrip('#')
        color = ''.join(c*2 for c in color) if len(color)==3 else color
        fingerprint = fp.get('base:'+fid) or fingerprints['v']
        old = previous.get('base:'+fid)
        if old and old.get('fingerprint')==fingerprint and old.get('color')==color and (OUT/old['asset']).is_file():
            return old
        params = dict(color=color,size=128,mode='split',prefer='live',source='faithful-v1',seed=42,v=fingerprint)
        url = args.server+'/api/swatch/base/'+quote(fid,safe='')+'?'+urlencode(params)
        row = {'key':'base:'+fid,'name':item.get('name',fid),'url':url,'fingerprint':fingerprint,
               'color':color,'seed':42,'protected':fid in protected,'native_verified':False}
        start = time.monotonic()
        try:
            if fid in protected:
                key = hashlib.sha256(json.dumps(['faithful-v1',fingerprint,'base',fid,color,42]).encode()).hexdigest()
                path = cache/(key+'.png')
                if not path.is_file():
                    row.update(status='protected_no_current_cached_master', seconds=0)
                    return row
                raw = path.read_bytes()
                row['evidence'] = 'fingerprint-matched existing master; no GET or bake'
            else:
                with urlopen(url,timeout=45) as response:
                    raw=response.read()
                row['evidence'] = 'actual HTTP faithful picker response'
            with Image.open(io.BytesIO(raw)) as im:
                w,h=im.size
                if w!=2*h:raise ValueError('Unexpected split dimensions')
                paint=im.crop((0,0,h,h)).convert('RGB').resize((128,128),Image.Resampling.BOX)
                spec=im.crop((h,0,w,h)).convert('RGB').resize((128,128),Image.Resampling.BOX)
                saved=Image.new('RGB',(256,128));saved.paste(paint,(0,0));saved.paste(spec,(128,0))
                saved.save(output/(fid+'.png'))
                row['measured']=measure(paint,spec)
                row['response_dimensions']=[w,h]
            row.update(status='ok',response_sha256=hashlib.sha256(raw).hexdigest(),
                       asset='live_base_pairs/'+fid+'.png')
        except Exception as exc:
            row.update(status='error',error=str(exc))
        row['seconds']=round(time.monotonic()-start,3)
        return row

    results=[]
    with (OUT/'live_progress.jsonl').open('w',encoding='utf8') as log:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for result in executor.map(capture,catalog['bases']):
                results.append(result);log.write(json.dumps(result,ensure_ascii=False)+'\n');log.flush()
                if len(results)%50==0:print(f'{len(results)}/{len(catalog["bases"])} checked; {sum(r["status"]=="ok" for r in results)} usable',flush=True)
    report={'server':args.server,'rows':results,'count':len(results),'ok':sum(r['status']=='ok' for r in results),
            'limits':['Picker samples are not native maps or on-car renders.','Request latency includes cache and networking; not a renderer benchmark.']}
    (OUT/'live_census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
