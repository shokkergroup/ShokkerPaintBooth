"""Natural car questions reach shared facts without changing the open paint."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def packet(label):
    files = list(OUT.glob(label + '-*.json'))
    assert len(files) == 1, (label, len(files))
    p = json.loads(files[0].read_text(encoding='utf-8'))
    assert p['port'] == 59910 and not p['result'].get('isError')
    return p, json.loads(next(x['text'] for x in p['result']['content'] if x['type'] == 'text'))


before = packet('car-natural-final-before-state')[1]
after = packet('car-natural-v2-after-state')[1]
online_after = packet('car-natural-v2-online-after-state')[1]
context = packet('car-natural-v2-online-context')[1]
assert {k:v for k,v in before.items() if k != 'convo'} == {k:v for k,v in after.items() if k != 'convo'}
assert after['convo']['live_changes'] == 0 and after['convo']['last_change'] is None
assert after['convo']['pending'] is None
questions = ['Anything unusual about the Skip Barber template? Explain only.', 'Are there any gotchas with the Ruf RT12R AWD template? Explain only.', 'What should I know before painting this car? Explain only.']
assert [h['said'] for h in after['convo']['history']] == [q[:60] for q in questions]
assert all(h['act'] == 'answer' for h in after['convo']['history'])
# Existing status reading warms derived unnamed-panel observations, not paint.
assert {k:v for k,v in after.items() if k not in ('car','editor_capabilities')} == {k:v for k,v in online_after.items() if k not in ('car','editor_capabilities')}
assert {k:v for k,v in after['editor_capabilities'].items() if k != 'panel_locations'} == {k:v for k,v in online_after['editor_capabilities'].items() if k != 'panel_locations'}
assert 'unnamed separate panels' in online_after['car']['panels_note']
assert online_after['car']['parts_not_known_yet']
assert context['request_intent']['mutation_allowed'] is False
assert context['car_reference_request'] == {'question':True,'current_context':False,'overview':True,'mixed_or_edit':False,'read_only':True}
assert context['car_reference']['resolved'] and context['car_reference']['car']['id'] == 'rt2000'
facts = context['car_reference']['car']['facts']
assert any('2048' in f['text'] for f in facts)
assert any('simulator artwork' in f['text'] for f in facts)
assert context['car_reference']['car']['can_target_panels'] is False
assert all(f['source_ids'] and all(s in context['car_reference']['car']['sources'] for s in f['source_ids']) for f in facts)
inbox = packet('car-natural-v2-inbox')[1]
reply, result = packet('car-natural-v2-online-reply')
assert inbox['messages'][-1]['text'] == questions[0]
assert reply['arguments']['reply_to'] == inbox['reply_to']
assert '2048' in reply['arguments']['text'] and 'simulator artwork' in reply['arguments']['text']
chat = (OUT / 'car-natural-v2-chat.txt').read_text(encoding='utf-8')
assert 'Formula Skip Barber 2000.psd, is 2048 by 2048 pixels' in chat
assert 'not a 4K custom-paint export requirement' in chat
assert 'top-level group named base' in chat and 'Wing Braces and Wing' in chat
assert 'the loaded file has not been verified against it' in chat
assert 'choose one main colour' not in chat and "Didn't do what I asked" not in chat
online_chat = (OUT / 'car-natural-v2-online-chat.txt').read_text(encoding='utf-8')
assert reply['arguments']['text'] in online_chat and 'ChatGPT is not listening yet' not in online_chat
first = Image.open(OUT / 'car-natural-v2-before-preview.png').convert('RGBA')
last = Image.open(OUT / 'car-natural-v2-after-preview.png').convert('RGBA')
assert first.size == last.size == (256,256)
assert all(v == (0,0) for v in ImageChops.difference(first,last).getextrema())
cleanup = json.loads((OUT / 'project-cleanup-2026-10-10.json').read_text(encoding='utf-8'))
kept = [x for x in cleanup['projects'] if x['action'] == 'keep']
folder = Path(cleanup['directory'])
assert {p.name for p in folder.glob('*.spbproj')} == {x['file'] for x in kept}
assert all(hashlib.sha256((folder/x['file']).read_bytes()).hexdigest() == x['sha256'] for x in kept)
report = {'pass':True,'scope':'Three native Offline natural questions plus this current model\'s actual MCP context/ChatGPT reply on private59910',
          'native_questions':questions,'same_source_limits_in_chat_and_expanded_answer':True,'factual_answers_not_pending_asks':True,
          'exposed_paint_state_unchanged':True,'preview_rgba_exact':True,'preview_size':[256,256],'projects':{'retained':3,'original_hashes_match':True,'new_saves':0},
          'component_coverage':'192 compiled catalog records; cold local loading, draft retention, document/provider/load-failure/kill/mixed/design/negation guards are component checks.',
          'rebase':'Review candidates retain owner Undo stash and W28 settled-preview confirmation; shared sources never written.',
          'limits':['First settled-page question is native; cold loading is component-tested. An earlier click during source restoration left its draft unsent and needed a retry; startup behavior remains open.','Online reply required explicit waiting; unattended connection and actual Claude model parity remain open.','No new car facts, verified UV maps, historical layout calibration, full-resolution output or shared/package adoption established by this turn.']}
(OUT / 'car-natural-native-acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
