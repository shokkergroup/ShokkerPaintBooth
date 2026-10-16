"""Verify current selected-material facts, independent-material advice and Undo."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def packet(label):
    f, = OUT.glob(label+'-*.json')
    p = json.loads(f.read_text(encoding='utf-8'))
    assert p['port'] == 59910 and not p['result'].get('isError')
    return p, json.loads(p['result']['content'][0]['text'])


before = packet('layer-material-v3-before-state')[1]
assigned = packet('layer-material-v3-assigned-state')[1]
after = packet('layer-material-v3-undo-state')[1]
context = packet('layer-material-v3-online-context')[1]
assigned_context = packet('layer-material-v3-assigned-context')[1]
for s in [before, after]:
    c=s['convo']
    assert c['pending'] is None and c['last_target'] is None
    assert c['last_change'] is None and c['last_offer'] is None and c['live_changes'] == 0
    assert all(h['act']=='answer' and 'look' not in h and 'targets' not in h for h in c['history'])
assert len(after['convo']['history']) == 3
assert {k:v for k,v in before.items() if k!='convo'} == {k:v for k,v in after.items() if k!='convo'}
assert {k:v for k,v in before.items() if k!='editor_capabilities'} == {k:v for k,v in assigned.items() if k!='editor_capabilities'}
assert {k:v for k,v in before['editor_capabilities'].items() if k!='layer_materials'} == {k:v for k,v in assigned['editor_capabilities'].items() if k!='layer_materials'}
for s in [before,after]:
    rec, = s['editor_capabilities']['layer_materials']['selection']['records']
    assert rec['name']=='Sponsors' and rec['id']=='psd_2' and rec['state']=='none' and rec['material'] is None
rec, = assigned['editor_capabilities']['layer_materials']['selection']['records']
assert rec['name']=='Sponsors' and rec['state']=='assigned' and rec['description']=='Matte Vinyl'
assert rec['material']=={'v':1,'preset':'matte'}
assert assigned_context['editor_capabilities']['layer_materials']['selection']==assigned['editor_capabilities']['layer_materials']['selection']
assert context['editor_capabilities']['layer_materials']['selection']==before['editor_capabilities']['layer_materials']['selection']
assert context['request_intent']['mutation_allowed'] is False
inbox=packet('layer-material-v3-inbox')[1]
reply,_=packet('layer-material-v3-online-reply')
assert reply['arguments']['reply_to']==inbox['reply_to']==1
assert inbox['messages'][-1]['text']=='Can I keep my sponsors matte while the body stays chrome? Please explain only.'
online=(OUT/'layer-material-v3-online-chat.txt').read_text(encoding='utf-8')
assert reply['arguments']['text'] in online and 'ChatGPT is not listening yet' not in online
goal=(OUT/'layer-material-v3-goal.txt').read_text(encoding='utf-8')
assert 'leave the body settings alone' in goal and 'Matte Vinyl supplies a matte material' in goal
assert 'body is currently chrome' in goal and 'Spec Doctor is available' not in goal
assigned_chat=(OUT/'layer-material-v3-assigned-chat.txt').read_text(encoding='utf-8')
assert 'Sponsors: Matte Vinyl.' in assigned_chat
assert 'No Layer Material assignment does not mean' not in assigned_chat
undo=(OUT/'layer-material-v3-undo-chat.txt').read_text(encoding='utf-8')
assert 'Sponsors: None (zones decide); no stored Layer Material assignment.' in undo
assert 'Undid: Layer Material: Matte Vinyl' in undo and '0 actions' in undo
a=Image.open(OUT/'startup-final-preview.png').convert('RGBA')
b=Image.open(OUT/'layer-material-v3-final-preview.png').convert('RGBA')
assert a.size==b.size==(256,256)
assert all(x==(0,0) for x in ImageChops.difference(a,b).getextrema())
cleanup=json.loads((OUT/'project-cleanup-2026-10-10.json').read_text(encoding='utf-8'))
folder=Path(cleanup['directory']);kept=[r for r in cleanup['projects'] if r['action']=='keep']
assert {p.name for p in folder.glob('*.spbproj')}=={r['file'] for r in kept}
assert all(hashlib.sha256((folder/r['file']).read_bytes()).hexdigest()==r['sha256'] for r in kept)
report={'pass':True,'scope':'Private59910 current-material facts and independent artwork/body explanations',
        'native_offline_none_matte_undo_none':True,'actual_current_model_context_reply':True,
        'completed_material_answers_no_soft_missing_look':True,'no_inferred_single_chrome_target':True,
        'temporary_assignment_used_existing_owner_UI':True,'native_keyboard_undo_restores_exposed_state':True,
        'preview_256_rgba_exact_after_undo':True,'retained_project_hashes_match':True,'new_project_saves':0,
        'limits':['Questions do not apply material. No new material write tool or layer executor is advertised.',
                  'Stored assignments are not full-resolution material appearance/spec-output proof.',
                  'Missing/duplicate/disabled/unreadable/hidden/multi-selection and clone/genuine-ask/edit/offer/Undo/Redo guards have component coverage.',
                  'Actual Claude inference parity, shared/package adoption, unattended wake-up/reconnect and calibrated UV geometry remain open.'],
        'negative_receipts':['layer-material-natural-before.txt','layer-material-undo-state (old misleading soft look)','layer-material-v2-before-state (first staged fix missed actual producer payload)','layer-material-v3-goal-state (old document MCP read rejected before fresh buyer message)']}
(OUT/'layer-material-native-acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
