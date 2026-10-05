"""Verify current ASTRA bakes survive an actual supervised server restart."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_astra_rebuild_20260922_work'


def main():
    live=json.loads((OUT/'live_report.json').read_text())
    stamps={rel:(ROOT/rel).stat().st_mtime_ns for row in live for rel in row['persistent_files']}
    result=subprocess.call([sys.executable,'scripts/spb_astra_rebuild_install.py','sync'],cwd=ROOT)
    assert result==0
    result=subprocess.call([sys.executable,'spb_server_supervisor.py','refresh'],cwd=ROOT)
    assert result==0
    base='http://127.0.0.1:59876';fp=json.load(urllib.request.urlopen(base+'/api/swatch-fingerprints',timeout=60))['fp']
    manifest=json.loads((ROOT/'thumbnails/picker_split/_manifest.json').read_text())['finishes'];rows=[]
    for row in live:
        fid=row['id'];key='base:'+fid;assert fp[key]==row['fingerprint'],('fingerprint changed',fid)
        query=urllib.parse.urlencode(dict(color=manifest[key]['color_hex'],size=256,mode='split',prefer='live',source='faithful-v1',seed=42,v=fp[key]))
        start=time.perf_counter();data=urllib.request.urlopen(base+'/api/swatch/base/'+fid+'?'+query,timeout=60).read()
        assert hashlib.sha256(data).hexdigest()==row['served_256']['sha256'],fid
        rows.append(dict(id=fid,seconds=round(time.perf_counter()-start,4),exact=True))
    assert all((ROOT/rel).stat().st_mtime_ns==stamp for rel,stamp in stamps.items()),'Persistent master/derivative was regenerated'
    checks=json.loads((OUT/'runtime_hashes.json').read_text())
    for rel,digest in checks.items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest
        assert hashlib.sha256((ROOT/'electron-app/server'/rel).read_bytes()).hexdigest()==digest
    result=dict(status='pass',finishes=50,cache_files_unchanged=len(stamps),runtime_exact_pairs=len(checks),responses=rows)
    (OUT/'restart_report.json').write_text(json.dumps(result,indent=2))
    print('Restart PASS: 50 stable fingerprints and exact responses;',len(stamps),'persistent files unchanged;',len(checks),'runtime pairs exact')


if __name__=='__main__':main()
