"""Reproduce actual private page refusals and exact-layer/Undo acceptance."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
folder=root/'_codex_mcp_work/chatgpt-dev/59910'
rs=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('source-bound-page-*.json'))]
r=next(x for x in reversed(rs) if x.get('roundtrip'))
assert r['valid_read'] and len(r['attempts'])==4
for a in r['attempts']:
    assert a['response']['ok'] is False and 'no changes were applied' in a['response']['error']
assert r['before']==r['after'] and len(r['before'])==9
v=r['roundtrip']
assert v['exact_layer']=='psd_0'
assert v['preview_before']==v['preview_after']
assert len(v['restored_fields'])==5
assert v['initial_fields']==v['final_fields']
assert v['during_layers']!=v['initial_fields']['layers']
fixtures=root/'_release_evidence/chatgpt-dev/59910/projects'
expected={'ARCA recovered hidden rasters - private59910.spbproj':'3265ac9b4fed1ccc4a949a5045d2bae38471f28106d7637966bc55a781998001',
 'Layered protection baseline - private59910.spbproj':'72ceb22f1ecbb11a01f56a4623f881d17c66df782592846800e555f63858500d'}
assert len(list(fixtures.glob('*.spbproj')))==2
for name,sha in expected.items():
    assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==sha,name
print('PASS four real page refusals, fresh bound read, exact body-layer edit/Undo, encoded preview equality and two original fixtures. Mid-edit source-switch/native named-part/kit calibration remains open.')
