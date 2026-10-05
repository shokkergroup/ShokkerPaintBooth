"""Refresh final source digests and detect any change to audited picker pixels."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra.wave2 import MODULES
OUT=ROOT/'_astra40_work'
def main():
    with (OUT/'picker_final.log').open('w',encoding='utf-8') as log:
        result=subprocess.call([sys.executable,'rebuild_picker_swatches.py','--force','--ids',*['base:'+m.FID for m in MODULES]],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result==0,result
    hashes=json.loads((OUT/'pre_final_picker_hashes.json').read_text())
    changed=[p for p,h in hashes.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    (OUT/'final_picker_changes.json').write_text(json.dumps(changed,indent=2))
    print('Final source digests refreshed. Audited assets changed:',len(changed),changed)
if __name__=='__main__':main()
