"""Verify recorded private Offline car follow-up conversation; DOM scope only."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'_codex_mcp_work/chatgpt-dev/59910'
a=json.loads((E/'reference-followup-native-before.json').read_text(encoding='utf-8'))
b=json.loads((E/'reference-followup-native-after.json').read_text(encoding='utf-8'))
h=json.loads((E/'reference-followup-native-held.json').read_text(encoding='utf-8'))
chat=(E/'reference-followup-native-chat.txt').read_text(encoding='utf-8')
assert h['disabled'] and h['send']=='Loading paint…'
assert h['draft']==a['draft'] and not a['disabled'] and a['send']=='Send'
for key in ['source','folder','layers','zones','preview']:assert a[key]==b[key],key
assert 'ARCA Chevy SS.tga' in a['source']
assert 'Is that the Legacy one?' in chat and 'What about green?' in chat and 'Can I still paint it?' in chat
assert chat.count('this exact reference is classified as Legacy')>=2
assert 'Chevrolet Camaro ZL1 Gen 6.psd reference (not a verification of your open paint)' in chat
assert 'Green/roughness: 0 is smooth and reflective; 255 is rough' in chat
assert 'current simulator painting availability' in chat
projects=ROOT/'_release_evidence/chatgpt-dev/59910/projects'
expected={'ARCA recovered hidden rasters - private59910.spbproj':'3265ac9b4fed1ccc4a949a5045d2bae38471f28106d7637966bc55a781998001','Layered protection baseline - private59910.spbproj':'72ceb22f1ecbb11a01f56a4623f881d17c66df782592846800e555f63858500d'}
assert {p.name for p in projects.glob('*.spbproj')}==set(expected)
for n,d in expected.items():assert hashlib.sha256((projects/n).read_bytes()).hexdigest()==d
r={'pass':True,'native_offline_turns':4,'open_car':'ARCA','discussed_reference':'Camaro Gen 6','held_draft_survives_recovery_choice':True,'DOM_source_folder_layers_zones_preview_exact':True,'two_original_project_hashes_exact':True,'limits':['DOM view preservation only; no full-resolution pixel or simulator claim','Source import required explicit Start Fresh recovery choice','Provider invalidation and shared adoption not native-proven']}
(E/'reference-followup-native-acceptance.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
