"""Golden pixels for legacy spec overlays, captured before SPB-105 v2 tick 1."""
from pathlib import Path
import argparse,contextlib,hashlib,io,json,os,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def main():
    p=argparse.ArgumentParser();p.add_argument('--capture',action='store_true');args=p.parse_args()
    assert os.environ.get('PYTHONHASHSEED')=='906','Use PYTHONHASHSEED=906 for the legacy process-hash baseline.'
    out=ROOT/'_spec_overlays_v2_work';out.mkdir(exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from engine.spec_patterns import PATTERN_CATALOG
        from engine.compose import compose_finish,compose_finish_stacked
    from scripts.audit_spec_pattern_quality import _load_ui_spec_patterns
    items,_=_load_ui_spec_patterns();items=[r for r in items if not r['id'].startswith('spov2_')]
    result={'renderer_hashes':{},'compose_hashes':{}}
    for row in items:
        a=PATTERN_CATALOG[row['id']]((128,128),42,1.,**row.get('defaults',{}))
        result['renderer_hashes'][row['id']]=hashlib.sha256(a.tobytes()).hexdigest()
    for base in ['metallic','f_electroplate','candy']:
        for name,fn,regular in [('single',compose_finish,'none'),('stacked',compose_finish_stacked,[])]:
            for channels in ['MRC','C','R']:
                for count in [0,1,5]:
                    layers=[dict(pattern=pid,opacity=.5,range=40,blend_mode='normal',channels=channels) for pid in ['hex_cells','brushed_diagonal','spec_fish_scales','wave_ripple','spec_brick_mortar'][:count]]
                    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                        a=np.asarray(fn(base,regular,(64,64),np.ones((64,64),np.float32),42,1.,dither=False,spec_pattern_stack=layers))
                    result['compose_hashes'][f'{base}/{name}/{channels}/{count}']=hashlib.sha256(a.tobytes()).hexdigest()
    path=out/'legacy-golden.json'
    if args.capture:
        assert not path.exists(),'Never overwrite the pre-edit golden baseline.'
        path.write_text(json.dumps(result,indent=2),encoding='utf-8');print('Captured',len(result['renderer_hashes']),'legacy renderers and',len(result['compose_hashes']),'composed fixtures')
    else:
        old=json.loads(path.read_text(encoding='utf-8'));changed=[]
        for section,rows in old.items():
            changed.extend(section+'/'+k for k,v in rows.items() if result[section].get(k)!=v)
        (out/'legacy-check.json').write_text(json.dumps({'changed':changed,'checked':sum(len(v) for v in old.values())},indent=2),encoding='utf-8')
        print('Legacy golden changes:',len(changed));assert not changed,changed
if __name__=='__main__':main()
