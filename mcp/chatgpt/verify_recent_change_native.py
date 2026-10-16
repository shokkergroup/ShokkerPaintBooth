"""Current-ID history retrieval: actual Offline/edit/ChatGPT/Undo evidence."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def packet(label):
    files = list(OUT.glob('recent-change-v2-' + label + '-*.json'))
    assert len(files) == 1, (label, len(files))
    p = json.loads(files[0].read_text(encoding='utf-8'))
    assert p['port'] == 59910 and not p['result'].get('isError'), label
    return p, json.loads(next(c['text'] for c in p['result']['content'] if c['type'] == 'text'))


before = packet('before')[1]
edited = packet('edited')[1]
read = packet('read-state')[1]
online = packet('online-read-state')[1]
final = packet('final-state')[1]
context = packet('online-context')[1]
undo_context = packet('undo-online-context')[1]
old_change = edited['convo']['last_change']
e = edited['editor_capabilities']['recent_change']
assert old_change['targets'] == '' and old_change['zone_ids'] == [e['zones'][0]['zone_id']]
assert e['available'] and e['read_only'] and not e['record']['marked_undone']
assert e['record']['request'] == 'Make it a little finer.'
assert e['zones'][0]['current_name'] == 'Everything Else'
assert e['zones'][0]['current_source_layers'][0]['current_name'] == 'Body'
assert e['zones'][0]['current_primary_pattern']['name'] == 'Diner Checkerboard'
assert e['zones'][0]['current_primary_pattern']['scale'] == .465
assert context['editor_capabilities']['recent_change'] == e
assert context['request_intent']['mutation_allowed'] is False
assert edited['convo']['live_changes'] == read['convo']['live_changes'] == 1
assert edited['convo']['pending'] is read['convo']['pending'] is None
assert read['convo']['history'][-1]['act'] == 'answer'
assert {k:v for k,v in edited.items() if k != 'convo'} == {k:v for k,v in read.items() if k != 'convo'}
assert online == read, 'Actual connected answer did not change exposed project/conversation state'
assert final['convo']['last_change']['undone'] and final['convo']['live_changes'] == 0
assert final['convo']['pending'] is None and final['convo']['history'][-1]['act'] == 'answer'
assert final['editor_capabilities']['recent_change']['record']['marked_undone']
assert undo_context['editor_capabilities']['recent_change'] == final['editor_capabilities']['recent_change']
assert undo_context['request_intent']['mutation_allowed'] is False
assert final['editor_capabilities']['pattern_controls'] == before['editor_capabilities']['pattern_controls']
for key in ('zones', 'layers', 'paint_colours', 'selected_zone', 'template_identity', 'saved_design_brief'):
    assert before.get(key) == edited.get(key) == final.get(key), key
for key in ('export_guides', 'kits', 'layer_materials', 'preview', 'spec_doctor', 'edge_bleed'):
    assert before['editor_capabilities'].get(key) == edited['editor_capabilities'].get(key) == final['editor_capabilities'].get(key), key
# The existing status/verification path warmed derived unnamed-panel evidence.
# This is explicitly distinct from mutable paint settings or verified geometry.
assert before['car'] is None and edited['car'] == final['car']
assert 'unnamed separate panels' in edited['car']['panels_note']
assert edited['car']['parts_not_known_yet']
assert before['editor_capabilities']['panel_locations']['status'] == 'unavailable'
assert edited['editor_capabilities']['panel_locations'] == final['editor_capabilities']['panel_locations']

for inbox_label, reply_label in [('inbox', 'online-reply'), ('undo-inbox', 'undo-online-reply')]:
    inbox = packet(inbox_label)[1]
    reply, result = packet(reply_label)
    assert inbox['request_intent']['mode'] == 'advice' and not inbox['request_intent']['mutation_allowed']
    assert reply['arguments']['reply_to'] == inbox['reply_to']
    assert inbox['messages'][-1]['text'].endswith('Explain only.')

chat = (OUT / 'recent-change-v2-final-chat.txt').read_text(encoding='utf-8')
assert 'Current primary pattern: Diner Checkerboard, scale 0.465.' in chat
assert 'Current primary pattern: Diner Checkerboard, scale 0.6.' in chat
assert 'The latest recorded edit was “Make it a little finer”. It is marked undone.' in chat
assert 'Yes. The latest recorded edit is marked undone' in chat
assert 'ChatGPT is not listening yet' not in chat
assert 'zone_25c42048' not in chat and '[psd_0]' not in chat

images = {k:np.asarray(Image.open(OUT / f'recent-change-v2-{k}-preview.png').convert('RGBA')) for k in ('before', 'edited', 'undo')}
assert all(x.shape == (256, 256, 4) for x in images.values())
assert np.array_equal(images['before'], images['undo'])
changed = np.any(images['before'] != images['edited'], axis=2)
changed_count = int(np.count_nonzero(changed))
assert changed_count > 1000
protected = {}
for name in ('numbers', 'sponsors'):
    alpha = Image.open(ROOT / f'_release_evidence/chatgpt-dev/59910/fixtures/layered-protection-a-{name}.png').getchannel('A')
    core = alpha.resize((256,256),Image.Resampling.LANCZOS).point(lambda x:255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(core) > 0
    count, harm = int(np.count_nonzero(mask)), int(np.count_nonzero(changed & mask))
    assert count > 2000 and harm == 0
    protected[name] = {'opaque_interior_preview_pixels':count,'changed':harm}
cleanup = json.loads((OUT / 'project-cleanup-2026-10-10.json').read_text(encoding='utf-8'))
kept = [p for p in cleanup['projects'] if p['action'] == 'keep']
directory = Path(cleanup['directory'])
assert {p.name for p in directory.glob('*.spbproj')} == {p['file'] for p in kept}
assert all(hashlib.sha256((directory/p['file']).read_bytes()).hexdigest() == p['sha256'] for p in kept)
report = {'pass':True,'scope':'Private59910 actual Offline/edit/current-model ChatGPT/context/Undo; read-only history retrieval, not complete product acceptance',
          'blank_recorded_target_resolved_by_exact_live_zone_id':True,'current_names_and_layer_selectors':True,'historical_deltas_not_invented':True,
          'native_answer_lifecycle_and_pending':True,'actual_model_replies_match_latest_buyer_sequences':True,'exposed_paint_settings_preserved_by_reads':True,
          'scale':{'before':.6,'edited':.465,'undone':.6},'preview':{'size':[256,256],'changed_pixels':changed_count,'undo_rgba_exact':True,'protected':protected},
          'projects':{'remaining':len(kept),'original_hashes_match':True,'new_saves':0},
          'derived_state_note':'Existing edit/status path warmed unnamed-panel evidence; no calibrated geometry claim.',
          'limits':['Actual Claude model parity/shared adoption/installer acceptance not established.','This reader does not provide historical property deltas, complete affected scope or edit authority.','No full-resolution output, translucent-edge/source-buffer audit, real-car UV calibration or unattended connection acceptance in this turn.']}
(OUT / 'recent-change-native-acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
