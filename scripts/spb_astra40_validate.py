"""Sequential evidence stages; avoid concurrent rendering contention."""
from pathlib import Path
import subprocess,sys,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra.wave2 import MODULES
OUT=ROOT/'_astra40_work'
def stage(name,args):
    print('START',name,flush=True)
    with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
        code=subprocess.call([sys.executable,*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    print('DONE',name,'exit',code,flush=True)
    if code:raise SystemExit(code)
def main():
    stage('native_w3',['scripts/spb_astra40_audit.py'])
    rows=json.loads((OUT/'native_report.json').read_text())
    failed=[k for k,v in rows.items() if not v['law']['pass']]
    assert len(rows)==40 and not failed,failed
    failed=[k for k,v in rows.items() if v['lane']=='MAD SCIENTIST' and min(v['distinct_rgb'].values())<2000000]
    assert not failed,failed
    stage('bake_standard',['rebuild_thumbnails.py','--type','base','--keys',*[m.FID for m in MODULES],'--size','256','--quiet'])
    stage('bake_picker',['rebuild_picker_swatches.py','--force','--ids',*['base:'+m.FID for m in MODULES]])
    stage('workbook',['scripts/spb_astra40_workbook.py'])
    stage('similarity',['scripts/spb_astra40_audit.py','--similarity'])
    stage('daylight',['scripts/spb_astra40_daylight.py'])
    print('ASTRA40 audit, bakes, M7, identity and daylight stages complete',flush=True)
if __name__=='__main__':main()
