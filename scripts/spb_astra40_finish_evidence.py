"""Final contract snapshot, original protection, live assets and compact report."""
from pathlib import Path
import hashlib,json,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.astra import MODULES as ORIGINALS
from engine.expansions.astra.wave2 import MODULES
from scripts.spb_finish_identity import contract_from_module
OUT=ROOT/'_astra40_work'
def main():
    original=json.loads((OUT/'original_hashes.json').read_text())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in original.items())
    for m in MODULES:
        c=contract_from_module(m,m.FID)
        (OUT/m.FID/'identity_contract.json').write_text(json.dumps(c,indent=2))
    served={};picker_api={}
    for m in ORIGINALS+MODULES:
        for kind in ('base','picker_split/base'):
            rel=f'thumbnails/{kind}/{m.FID}.png'
            data=urllib.request.urlopen('http://127.0.0.1:59876/'+rel,timeout=20).read()
            a=hashlib.sha256(data).hexdigest();b=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
            assert a==b,rel;served[rel]=a
        # The actual app card uses /api/swatch with prefer=live. Prove its
        # response is also the same 96x48 image used by the identity gate.
        url=f'http://127.0.0.1:59876/api/swatch/base/{m.FID}?color={m.SWATCH.lstrip("#")}&size=48&mode=split&prefer=live&v=c77c480df870'
        data=urllib.request.urlopen(url,timeout=20).read()
        sha=hashlib.sha256(data).hexdigest()
        assert sha==served[f'thumbnails/picker_split/base/{m.FID}.png'],m.FID
        picker_api[m.FID]=dict(url=url,sha256=sha)
    (OUT/'served_hashes.json').write_text(json.dumps(served,indent=2))
    (OUT/'picker_api_hashes.json').write_text(json.dumps(picker_api,indent=2))
    scores=json.loads((OUT/'m7_report.json').read_text());native=json.loads((OUT/'native_report.json').read_text())
    exports=json.loads((OUT/'full_pipeline/report.json').read_text())
    identity=json.loads((OUT/'similarity.json').read_text())
    summary=dict(new_finishes=len(MODULES),original_files_preserved=len(original),served_assets_verified=len(served),
        picker_api_assets_verified=len(picker_api),
        m7_min=min(v['composite'] for v in scores.values()),m7_max=max(v['composite'] for v in scores.values()),
        law_pass=sum(v['law']['pass'] for v in native.values()),identity_pairs=len(identity),
        identity_max=max(v['maximum'] for v in identity),identity_flags=[v for v in identity if v['status']!='pass'],
        mad_counts={k:exports[k]['distinct_rgb'] for k,v in native.items() if v['lane']=='MAD SCIENTIST'})
    (OUT/'final_summary.json').write_text(json.dumps(summary,indent=2))
    assert summary['m7_min']>=85 and summary['law_pass']==40
    assert summary['identity_pairs']==1225 and not summary['identity_flags']
    assert all(min(v.values())>=2000000 for v in summary['mad_counts'].values())
    print(json.dumps({k:v for k,v in summary.items() if k not in ('mad_counts','identity_flags')},indent=2))
if __name__=='__main__':main()
