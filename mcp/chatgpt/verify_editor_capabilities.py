"""Compare retained native read-only evidence; no fresh app calls or writes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
names = {
    'offline_pre':'paint-editor-cap-fixed-pre-2026-10-10T08-30-12-662Z.json',
    'offline_post':'paint-editor-cap-fixed-post-2026-10-10T08-30-50-788Z.json',
    'assigned':'paint-editor-material-assigned-2026-10-10T08-31-47-453Z.json',
    'online_post':'paint-editor-material-chat-post-2026-10-10T08-39-04-794Z.json',
    'undo':'paint-editor-material-undo-2026-10-10T08-40-47-591Z.json',
}
receipts = {key:json.loads((EVIDENCE / name).read_text()) for key,name in names.items()}
def state(receipt):
    return json.loads(next(c['text'] for c in receipt['calls'] if c['tool']=='spb_get_state'))
def image_hashes(receipt):
    return [(x['name'],x['sha256']) for x in receipt['images']]
checks = []
for before,after in [('offline_pre','offline_post'),('assigned','online_post'),('offline_post','undo')]:
    a,b = state(receipts[before]),state(receipts[after])
    assert len(a['layers']) == len(b['layers']) == 42
    assert len(a['zones']) == len(b['zones']) == 5
    for key in ('layers','zones','editor_capabilities'):
        assert a[key] == b[key], (before,after,key)
    assert image_hashes(receipts[before]) == image_hashes(receipts[after]), (before,after,'preview images')
    checks.append(dict(before=names[before],after=names[after],layer_records=42,zones=5,
        identical_preview_hashes=3,other_state_differences=[k for k in a if a[k]!=b.get(k)]))
assignment = state(receipts['assigned'])['editor_capabilities']['layer_materials']['assignments']
assert len(assignment)==1 and assignment[0]['id']=='psd_29' and assignment[0]['description']=='Matte Vinyl'
assert not state(receipts['undo'])['editor_capabilities']['layer_materials']['assignments']
probe_name='context-session-probe-2026-10-10T08-32-07-267Z.json'
probe=json.loads((EVIDENCE/probe_name).read_text())
assert probe['delivery']['pass'] and probe['delivery']['delivered']==1
assert any(c['tool']=='spb_get_state' and c['status']=='failed' for c in probe['calls'])
out=dict(schema='spb-editor-capability-acceptance/1',checks=checks,assignment=assignment,
    online_reply=dict(receipt=probe_name,delivered=1,fresh_state_timed_out=True,full_online_acceptance=False),
    limits=['Layer records and returned preview hashes only; no raw-raster byte or full-render claim.',
            'Undo capture followed candidate regeneration; it proves restoration, not that the browser loaded the new routing generation.'])
(EVIDENCE/'editor-capabilities-native-verification.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'pass':True,'comparisons':len(checks),'online_fresh_read':'failed, retained','native_material_undo':True}))
