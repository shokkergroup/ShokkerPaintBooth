"""Retained native evidence after document-bound tool routing."""
import json
from pathlib import Path

p = Path(__file__).resolve().parents[2] / '_codex_mcp_work/chatgpt-dev/59910'
def receipt(name):
    return json.loads((p / name).read_text(encoding='utf-8'))
a = receipt('paint-document-bridge-pre-2026-10-10T08-47-29-159Z.json')
b = receipt('paint-document-bridge-post-2026-10-10T08-49-00-806Z.json')
def state(r):
    return json.loads(next(c['text'] for c in r['calls'] if c['tool']=='spb_get_state'))
x,y = state(a),state(b)
assert len(x['layers']) == 42 and len(x['zones']) == 5
for key in ('layers','zones','editor_capabilities'):
    assert x[key] == y[key], key
assert [(i['name'],i['sha256']) for i in a['images']] == [(i['name'],i['sha256']) for i in b['images']]
model = receipt('context-session-probe-2026-10-10T08-47-38-702Z.json')
assert model['delivery']['pass']
assert all(c['status']=='completed' for c in model['calls'])
wait = next(i for i,c in enumerate(model['calls']) if c['tool']=='spb_wait_for_message')
assert any(c['tool']=='spb_assistant_context' for c in model['calls'][wait+1:])
out = dict(schema='spb-document-bridge-native/1',before=a['started'],after=b['started'],
    delivery=model['delivery'],fresh_context_after_buyer=True,all_tool_calls_completed=True,
    unchanged_layers=42,unchanged_zones=5,unchanged_images=3,
    other_state_differences=[k for k in x if x[k]!=y.get(k)],
    limits=['Read-only native acceptance with another stale page open; no concurrent multi-tab paint-write acceptance.',
            'Prior timeout retained; reproduced routing defects do not uniquely explain that timeout.'])
(p/'document-bridge-native-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out))
