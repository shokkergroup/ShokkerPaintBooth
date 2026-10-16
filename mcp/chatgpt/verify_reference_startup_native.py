"""Verify visible cold-reference loading without claiming source-restore recovery."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'

before_click = json.loads((OUT / 'startup-early-click.json').read_text(encoding='utf-8'))
assert 'Car references are not ready yet' in before_click['helper']
assert before_click['sourceCanvas'] == {'height': 512, 'width': 512}
assert before_click['render']['disabled'] is False
early = (OUT / 'startup-early-send.txt').read_text(encoding='utf-8')
assert 'Loading car template reference' in early
assert 'Working…" [disabled]' in early
assert 'Working. You can write your next message.' in early
finished = (OUT / 'startup-early-final.txt').read_text(encoding='utf-8')
assert 'the loaded file has not been verified against it' in finished
assert 'Reference details and sources — ARCA Chevrolet SS' in finished
assert 'Working…' not in finished
pending = (OUT / 'startup-draft-pending.txt').read_text(encoding='utf-8')
assert 'Loading car template reference' in pending and 'Working…" [disabled]' in pending
final = (OUT / 'startup-final-chat.txt').read_text(encoding='utf-8')
assert 'simulator artwork, not a 4K custom-paint export requirement' in final
assert final.count('generic: Anything unusual about the Skip Barber template? Explain only.') == 1
assert 'What does Car_Decal mean? Explain only.' in final

# Select the actual successful tool receipt; the first offline bridge refusal is
# separately retained as expected provider-state evidence, never called a pass.
success = []
for p in OUT.glob('startup-reference-final-state-*.json'):
    packet = json.loads(p.read_text(encoding='utf-8'))
    if not packet['result'].get('isError'):
        assert packet['port'] == 59910
        success.append(json.loads(packet['result']['content'][0]['text']))
assert len(success) == 1
state = success[0]
assert len(state['convo']['history']) == 1
assert state['convo']['history'][0]['act'] == 'answer'
assert state['convo']['pending'] is None and state['convo']['live_changes'] == 0
baseline_file, = OUT.glob('car-natural-final-before-state-*.json')
baseline = json.loads(json.loads(baseline_file.read_text(encoding='utf-8'))['result']['content'][0]['text'])
assert {k: v for k, v in state.items() if k != 'convo'} == {k: v for k, v in baseline.items() if k != 'convo'}
a = Image.open(OUT / 'car-natural-v2-before-preview.png').convert('RGBA')
b = Image.open(OUT / 'startup-final-preview.png').convert('RGBA')
assert a.size == b.size == (256, 256)
assert all(x == (0, 0) for x in ImageChops.difference(a, b).getextrema())
cleanup = json.loads((OUT / 'project-cleanup-2026-10-10.json').read_text(encoding='utf-8'))
folder = Path(cleanup['directory'])
kept = [x for x in cleanup['projects'] if x['action'] == 'keep']
assert {p.name for p in folder.glob('*.spbproj')} == {x['file'] for x in kept}
assert all(hashlib.sha256((folder/x['file']).read_bytes()).hexdigest() == x['sha256'] for x in kept)
report = {'pass': True, 'scope': 'Native first Send with a visibly cold reference index on private59910',
          'loading_visible_and_send_disabled': True, 'first_request_completed_without_retry': True,
          'unsent_draft_remains_unsent': True, 'single_completed_history_turn': True,
          'exposed_state_matches_retained_baseline': True, 'preview_256_rgba_exact': True,
          'retained_project_hashes_match': True, 'new_project_saves': 0,
          'limits': ['Source canvas and Render were already ready at Send. This does not resolve the earlier initial source-restoration race.',
                     'The second draft is visibly retained and not dispatched; its keystroke timing relative to completion is not established. Concurrent draft preservation remains component evidence.',
                     'Read-only MCP inspection required selecting ChatGPT after the Offline answer; no online model request was sent.',
                     'No shared/package adoption, actual Claude parity, unattended connection, full output or calibrated UV geometry established.']}
(OUT / 'reference-startup-native-acceptance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
