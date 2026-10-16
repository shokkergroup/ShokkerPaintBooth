"""Native active layered-import draft gate; whole-project extension is separate."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2];out=root/'_codex_mcp_work/chatgpt-dev/59910'
def read(n):return json.loads((out/n).read_text(encoding='utf-8'))
a=read('source-loading-native-held-dom.json');b=read('source-loading-native-ready-dom.json');c=read('source-loading-native-final-dom.json')
assert a['sendDisabled'] and not b['sendDisabled'] and not c['sendDisabled']
assert a['draft']==b['draft']=='Anything unusual about this car template? Explain only.' and c['draft']==''
assert 'Loading paint' in a['chat'] and 'paint is loading' in a['chat']
assert len(a['layers'])==3 and len(b['layers'])==len(c['layers'])==42
assert any('source verified' in x for x in b['alert'])
assert b['preview']==c['preview'] and b['layers']==c['layers']
assert c['chat'].count(b['draft'])==1 and 'UV panel positions remain unverified' in c['chat']
result={'pass':True,'scope':'Native retained ARCA open: active PSD import holds draft, verified ready releases Send, one explicit customer Send answers',
 'draft_preserved':True,'send_reenabled':True,'no_automatic_replay':True,'displayed_preview_and_layers_unchanged_by_question':True,
 'limits':['This native sequence used the initial PSD flag guard. Later whole-project persistence busy extension is component-tested.',
 'Cold pre-import/flat-source readiness still needs separate acceptance; DOM equality is not full-resolution source/spec proof.']}
(out/'source-loading-native-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
