"""Register only verified v2 thumbnail bakes with the production cache contract."""
from pathlib import Path
import os,sys,json,hashlib,contextlib,io
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('SHOKKER_NO_CLEAN','1');os.environ.setdefault('SPB_NO_BOOT_SWATCH_WARM','1');os.environ.setdefault('SPB_NO_LIVE_LINK','1')
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from engine.spec_patterns import PATTERN_CATALOG
    from server import _get_fn_hash
from engine.atomic_io import atomic_write_json
from datetime import datetime,timezone

def main():
    stats=json.loads((ROOT/'_spec_overlays_v2_work/bake/stats.json').read_text())
    path=ROOT/'thumbnails/_manifest.json';manifest=json.loads(path.read_text())
    for row in stats:
        pid=row['id'];fn=PATTERN_CATALOG[pid]
        if row['renderer_fingerprint']!=fn._spb_source_fingerprint:raise ValueError('Stale bake: '+pid)
        picker=ROOT/'thumbnails/spec_patterns_combined'/(pid+'_160.png')
        if hashlib.sha256(picker.read_bytes()).hexdigest()!=row['picker_sha256']:raise ValueError('Changed picker: '+pid)
        entry={'hash':_get_fn_hash(fn),'generated':datetime.now(timezone.utc).isoformat()}
        for key in ('spec_pattern_visuals','spec_pattern_combined'):
            manifest.setdefault(key,{})[pid+':160']=entry
    atomic_write_json(path,manifest,indent=2,ensure_ascii=True)
    print(f'Registered {len(stats)} verified overlay thumbnail pairs.')
if __name__=='__main__':main()
