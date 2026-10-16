"""Sequential finalization after authoring is frozen; fail at the first error."""
from pathlib import Path
import subprocess,sys,time,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'_astra_rebuild_20260922_work'
steps=[['scripts/spb_astra_rebuild_install.py','bake'],
       ['scripts/spb_astra_rebuild_install.py','sync'],
       ['spb_server_supervisor.py','refresh'],
       ['scripts/spb_astra_rebuild_install.py','live'],
       ['scripts/spb_astra_rebuild_pipeline.py'],
       ['scripts/spb_astra_rebuild_metrics.py'],
       ['scripts/spb_astra_rebuild_similarity.py'],
       ['scripts/spb_astra_rebuild_review.py']]
history=[]
for args in steps:
    print('START',*args,flush=True);start=time.time()
    code=subprocess.call([sys.executable,*args],cwd=ROOT)
    history.append(dict(command=args,exit_code=code,seconds=round(time.time()-start,2)))
    (OUT/'finalization.json').write_text(json.dumps(history,indent=2))
    if code:raise SystemExit(code)
    print('DONE',*args,flush=True)
