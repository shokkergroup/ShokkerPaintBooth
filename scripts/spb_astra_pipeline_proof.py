"""Exercise ASTRA in the real 2048 export pipeline without touching iRacing files."""
from pathlib import Path
import contextlib
import argparse
import io
import json
import re
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from engine.expansions.astra import MODULES
from engine.expansions.astra.common import clear_cache
from rebuild_thumbnails import make_zone_for_finish

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+');args=ap.parse_args()
    out=ROOT/'_astra_work/full_pipeline';out.mkdir(exist_ok=True)
    source=out/'neutral.png';Image.new('RGB',(2048,2048),(136,136,136)).save(source)
    engine_log=io.StringIO()
    with contextlib.redirect_stdout(engine_log),contextlib.redirect_stderr(engine_log):
        import shokker_engine_v2 as eng
    existing=out/'report.json'
    rows=json.loads(existing.read_text()) if args.ids and existing.exists() else {}
    for m in MODULES:
        if args.ids and m.FID not in args.ids:continue
        clear_cache()
        zone=make_zone_for_finish('base',m.FID)
        target=out/m.FID;target.mkdir(exist_ok=True)
        calls=[]; original_build=m.build
        def tracked_build(shape,seed):
            start=time.perf_counter(); result=original_build(shape,seed)
            calls.append(dict(shape=shape,seed=seed,seconds=time.perf_counter()-start))
            return result
        m.build=tracked_build
        with (target/'engine.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            start=time.perf_counter()
            paint,spec,_=eng.build_multi_zone(str(source),str(target),[zone],iracing_id='ASTRA_REVIEW',seed=42,save_debug_images=False)
            elapsed=time.perf_counter()-start
        m.build=original_build
        alpha_range=[int(spec[...,3].min()),int(spec[...,3].max())] if spec.shape[2]==4 else None
        spec=spec[...,:3]
        native_p=np.asarray(Image.open(ROOT/'_astra_work'/m.FID/'paint.png').convert('RGB'))
        native_s=np.asarray(Image.open(ROOT/'_astra_work'/m.FID/'spec.png').convert('RGB'))
        paint_error=float(np.abs(paint.astype(float)-native_p).mean())
        # The engine returns the OpenCV BGR-packed spec buffer; verify rather
        # than assuming channel order from the visual colour.
        direct=float(np.abs(spec.astype(float)-native_s).mean())
        reversed_error=float(np.abs(spec[...,::-1].astype(float)-native_s).mean())
        spec_error=min(direct,reversed_error)
        stage=re.findall(r'All finishes applied: ([0-9.]+)s',(target/'engine.log').read_text(encoding='utf-8'))
        rows[m.FID]=dict(seconds=elapsed,paint_mae=paint_error,spec_mae=spec_error,
                        finish_stage_seconds=float(stage[-1]) if stage else None,
                        generator_calls=calls,
                        alpha_range=alpha_range,
                        spec_order='BGR' if reversed_error<direct else 'RGB',
                        output_files=[p.name for p in target.glob('*.tga')])
        print(m.FID,round(elapsed,3),'paint MAE',round(paint_error,4),'spec MAE',round(spec_error,4),flush=True)
    (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'engine.log').write_text(engine_log.getvalue(),encoding='utf-8')
    return 0 if all(r['paint_mae']<1.1 and r['spec_mae']<1.1 for r in rows.values()) else 1
if __name__=='__main__':raise SystemExit(main())
