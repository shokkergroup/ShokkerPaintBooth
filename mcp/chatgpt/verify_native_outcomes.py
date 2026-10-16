"""Bounded native reporting/Undo proof; no claim of full-raster verification."""
from pathlib import Path
import json

E = Path(__file__).resolve().parents[2] / '_codex_mcp_work/chatgpt-dev/59910'
names = [
    'paint-outcome-noop-before-2026-10-10T06-38-17-122Z.json',
    'paint-outcome-capture-applied-2026-10-10T06-44-36-606Z.json',
    'paint-outcome-capture-noop-2026-10-10T06-45-12-726Z.json',
    'paint-outcome-capture-undo-2026-10-10T06-45-30-563Z.json',
]
receipts = [json.loads((E / n).read_text()) for n in names]
def call(receipt, tool):
    return json.loads(next(c['text'] for c in receipt['calls'] if c['tool'] == tool))
states = [call(r, 'spb_get_state') for r in receipts]
assert len(states[0]['layers']) == 42
assert states[1]['layers'] == states[2]['layers']
assert states[0]['layers'] == states[3]['layers']
assert all(s['zones'] == states[0]['zones'] for s in states)
for left, right in [(1, 2), (0, 3)]:
    assert len(receipts[left]['images']) == len(receipts[right]['images']) == 3
    for a, b in zip(receipts[left]['images'], receipts[right]['images']):
        assert (E / a['file']).read_bytes() == (E / b['file']).read_bytes()
measured = call(receipts[1], 'spb_check')['measured']
assert measured['verdict'] == 'ok'
assert measured['coverage']['changed_paint_cells'] > 0
assert measured['scope']['layers'] == ['psd_0']
assert measured['outside_px'] == measured['decal_px'] == measured['spec_px'] == 0
text = (E / 'outcome-noop-builder-pass.txt').read_text(encoding='utf-8')
assert 'no colour change was made.' in text and 'No change made:' in text
assert 'Not done yet:' not in text
result = dict(pass_native=True, receipts=names, preview_measurement=measured,
              repeated_request_preserves_42_records_zones_and_returned_images=True,
              chat_undo_restores_42_records_zones_and_returned_images=True,
              builder_no_change_wording=True, builder_undo_disabled_observed_in_browser=True,
              loaded_pro_ai='d0ee9d942ee8', loaded_builder='afe2591cd0e9',
              loaded_native_colour='7ccf6e878887',
              later_report_id_filter_component_only=True,
              full_raster_or_export_verification=False, actual_model_inference=False)
(E / 'native-outcomes-acceptance.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['receipts','preview_measurement']}))
