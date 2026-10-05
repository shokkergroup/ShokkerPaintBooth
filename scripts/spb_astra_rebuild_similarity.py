"""Run the unchanged category gate on all 50 R1 native and actual baked assets."""
from pathlib import Path
import os,sys,json,argparse,itertools,types
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import scripts.spb_astra40_audit as gate
from engine.expansions.astra import ALL_MODULES
gate.ORIGINALS=()
gate.MODULES=ALL_MODULES
gate.OUT=ROOT/'_astra_rebuild_20260922_work'
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+');args=ap.parse_args()
    if args.ids:
        original=json.loads((gate.OUT/'similarity.json').read_text())
        assert len(original)==1225
        pairs=itertools.combinations
        gate.itertools=types.SimpleNamespace(combinations=lambda values,n:(pair for pair in pairs(values,n) if set(pair)&set(args.ids)))
        def save(name,value):
            updated={tuple(sorted([r['a'],r['b']])):r for r in original}
            for r in value:updated[tuple(sorted([r['a'],r['b']]))]=r
            result=sorted(updated.values(),key=lambda r:-r['maximum'])
            assert len(result)==1225
            (gate.OUT/name).write_text(json.dumps(result,indent=2))
            (gate.OUT/'similarity_refresh.json').write_text(json.dumps(dict(ids=args.ids,recomputed=len(value),retained=1225-len(value)),indent=2))
        gate.save=save
    gate.similarity()
