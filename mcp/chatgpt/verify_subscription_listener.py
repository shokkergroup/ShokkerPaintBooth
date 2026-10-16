"""Verify the actual controller/model receipt; no customer Send UI claim."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
proof = json.loads((out / 'subscription-listener-recovery-2026-10-11T01-42-28-229Z.json').read_text(encoding='utf-8'))
worker = json.loads((out / 'subscription-listener-turn-2026-10-11T01-42-10-787Z.json').read_text(encoding='utf-8'))
assert proof['port'] == worker['port'] == 59910
assert worker['authentication'] == 'ChatGPT' and not worker['apiFallback']
assert worker['exitCode'] == 0 and not worker['errors']
assert [c['tool'] for c in worker['calls']] == ['spb_wait_for_message', 'spb_assistant_context', 'spb_reply']
assert all(c['status'] == 'completed' and not c['result'].get('isError') for c in worker['calls'])
wait, context, reply = worker['calls']
sequence = proof['checkpoint']['messages'][-1]['seq']
assert json.loads(wait['result']['content'][0]['text'])['reply_to'] == sequence
assert context['arguments']['query'] == proof['checkpoint']['messages'][-1]['text']
assert context['arguments']['include_paint'] is True
assert reply['arguments']['reply_to'] == proof['answer']['reply_to'] == sequence
assert json.loads(reply['result']['content'][0]['text'])['shown_in_app'] is True
assert reply['arguments']['text'] == proof['answer']['text']
for path in ['received', 'blocked', 'settled']:
    assert proof[path]['events'][-1]['model_inferences_started'] == 0
assert proof['recovered']['events'][-1]['model_inferences_started'] == 1
assert proof['settled']['events'][-1]['stopped'] == 'already_replied'
assert proof['before'] == proof['after'] and len(proof['before']) == 8
assert len(proof['fixture_hashes']) == 2
assert 'psd_0' in proof['answer']['text'] and 'geometry have not been verified' in proof['answer']['text']
print(json.dumps({'pass': True, 'actual_subscription_model_turns': 1, 'fresh_exact_context': True,
    'shown_in_app': True, 'checkpoint_restart_recovery': True,
    'lost_terminal_receipt_settled_without_inference': True, 'preserved_fields': 8,
    'customer_send_ui_exercised': False, 'unattended_production_listener': False}))
