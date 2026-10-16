"""Reproduce the scoped actual-RPC refusal/state/fixture acceptance from its receipt."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
folder=root/'_codex_mcp_work/chatgpt-dev/59910'
receipt=sorted(folder.glob('named-part-preflight-*.json'))[-1]
r=json.loads(receipt.read_text(encoding='utf-8'))
assert len(r['calls'])==4
for c in r['calls']:
    v=c['result']
    assert v['changed'] is False and v['refused'] is True
    assert v['reason'] in ('part_geometry_unconfirmed','kit_geometry_unverified')
assert r['before']==r['after']
assert len(r['before'])==9
projects=root/'_release_evidence/chatgpt-dev/59910/projects'
assert len(list(projects.glob('*.spbproj')))==2
for f in r['fixtures']:
    assert hashlib.sha256((projects/f['name']).read_bytes()).hexdigest()==f['sha256']
print('PASS four actual private MCP refusals, nine exposed state fields exact, two original fixtures unchanged. Native positive/pixels/atomic source switch/shared adoption remain open.')
