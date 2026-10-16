"""Attach measured revision provenance without changing renderer pixels."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra.wave2 import MODULES
OUT=ROOT/'_astra40_work'
def main():
    before=json.loads((OUT/'m7_w4_report.json').read_text()) if (OUT/'m7_w4_report.json').exists() else {}
    after=json.loads((OUT/'m7_report.json').read_text())
    assert all(v['composite']>=85 for v in after.values())
    hashes={}
    for m in MODULES:
        p=Path(m.__file__);raw=p.read_text(encoding='utf-8')
        lines=[line for line in raw.splitlines() if not line.startswith('# SPB-105 / ASTRA W8 measured')]
        lines[0]='"""SPB-105 / ASTRA W8. Fine independent construction; measured evidence in the expansion report."""'
        prior=before.get(m.FID,{}).get('composite','new')
        lines.insert(1,f'# SPB-105 / ASTRA W8 measured. Owner: "more diverse designs"; M7 {prior} -> {after[m.FID]["composite"]}. Native identity and actual exports are separate gates.')
        p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        for kind in ('base','picker_split/base'):
            a=ROOT/'thumbnails'/kind/(m.FID+'.png');hashes[a.relative_to(ROOT).as_posix()]=hashlib.sha256(a.read_bytes()).hexdigest()
    (OUT/'pre_final_picker_hashes.json').write_text(json.dumps(hashes,indent=2))
    print('Recorded measured M7 provenance on forty modules; pixels unchanged')
if __name__=='__main__':main()
