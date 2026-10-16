"""Reconcile browser observations with actual MCP render and follow-up receipts."""
import json
from pathlib import Path

out = Path(__file__).resolve().parents[2] / '_codex_mcp_work/chatgpt-dev/59910'

def read(name):
    return json.loads((out / name).read_text(encoding='utf-8'))

def value(name):
    packet = read(name)
    assert not packet['result'].get('isError')
    return json.loads(packet['result']['content'][0]['text'])

observed = read('mcp-render-dialog-native-observations.json')
assert not observed['completed_mcp_render_modal_visible']
assert all(observed[k] for k in ['send_ready_after_mcp_render', 'send_center_hit_actual_send', 'mouse_send_followup_visible', 'manual_render_results_visible', 'manual_close_worked'])
render = value('online-quiet-render-result-2026-10-10T18-49-54-994Z.json')
assert render['rendered'] and render['files_saved'] == 0 and not render['pushed_live']
inbox = value(observed['followup_inbox'])
assert inbox['messages'][-1]['text'] == 'What is my current pattern scale? Do not change anything.'
assert inbox['request_intent']['mutation_allowed'] is False
context = value('online-quiet-render-followup-context-2026-10-10T18-51-22-601Z.json')
restored = value('online-pattern-successor-undo-state-2026-10-10T18-48-24-337Z.json')
state = context['paint']['state']['data']
assert restored['layers'] == state['layers'] and restored['zones'] == state['zones']
assert restored['editor_capabilities']['pattern_controls'] == state['editor_capabilities']['pattern_controls']
reply = read('online-quiet-render-followup-reply-2026-10-10T18-51-59-544Z.json')
assert not reply['result'].get('isError') and reply['arguments']['reply_to'] == inbox['reply_to']
receipt = {
    'pass': True, 'port': 59910,
    'completed_MCP_render_does_not_cover_composer': True,
    'mouse_Send_reaches_real_current_document_inbox': True,
    'current_model_reply_delivered': True,
    'manual_Render_results_still_open_and_close': True,
    'render_seconds': render['seconds'], 'external_files_saved': render['files_saved'],
    'restored_primary_settings_and_layer_zone_summaries_exact': True,
    'observations': 'mcp-render-dialog-native-observations.json',
    'screenshot': 'online-quiet-render-followup-chat.png',
    'negative': 'online-pattern-send-overlay.png',
    'limits': 'Private current-model MCP/page acceptance plus generated render contract tests. Pre-existing manual dialog/document replacement/failure/kill guards are component-tested; arbitrary simultaneous manual modal interaction, unattended customer connection and actual Claude parity remain open. No renderer, geometry or external-write permission change.',
}
(out / 'mcp-render-dialog-native-acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'MCP_render_nonblocking': True, 'mouse_followup_and_reply': True, 'manual_render_preserved': True, 'settings_unchanged': True}))
