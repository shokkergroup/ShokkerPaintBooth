"""Actual subscription report acceptance; retains the lost-scope negative control."""
from pathlib import Path
import json

E = Path(__file__).resolve().parents[2] / '_codex_mcp_work/chatgpt-dev/59910'
probe_name = 'context-session-probe-2026-10-10T06-48-55-391Z.json'
probe = json.loads((E / probe_name).read_text())
assert probe['authentication'] == 'ChatGPT' and not probe['apiFallback']
assert probe['exitCode'] == 0 and not probe['errors']
edits = [c for c in probe['calls'] if c['tool'] == 'spb_edit_layer']
assert len(edits) == 1
assert edits[0]['arguments'] == dict(layer='Paintable Area / Car Patterns / car_pattern_001.tga', source_colour='#ff0000', colour='#b39a58', replace_tolerance=0)
out = json.loads(next(c['text'] for c in edits[0]['result']['content'] if c['type'] == 'text'))
assert out['layer_colour_outcomes'][0]['status'] == 'applied'
assert out['layer_colour_outcomes'][0]['matched_pixels_before_selection'] == 2315143
m = out['measured']; assert m['verdict'] != 'not_measured'
assert m['coverage']['changed_paint_cells'] == 18695 and m['decal_px'] == 256
assert not m['scope']['layers'] and 'hood' in m['line']  # preserved defect, not an accepted scope claim
reply = next(c['arguments']['text'] for c in probe['calls'] if c['tool'] == 'spb_reply')
assert '256' in reply and 'unverified' in reply and 'saved or exported' in reply
names = [probe['fixtureReceipt'], 'paint-source-report-after-2026-10-10T06-55-00-830Z.json', 'paint-source-report-undo-2026-10-10T06-55-30-330Z.json']
rows = [json.loads((E / n).read_text()) for n in names]
states = [json.loads(next(c['text'] for c in r['calls'] if c['tool'] == 'spb_get_state')) for r in rows]
assert len(states[0]['layers']) == 42
assert all(s['layers'] == states[0]['layers'] and s['zones'] == states[0]['zones'] for s in states)
for a,b in zip(rows[0]['images'],rows[2]['images']): assert (E/a['file']).read_bytes() == (E/b['file']).read_bytes()
assert (E/'source-report-before.png').read_bytes() == (E/'source-report-undo.png').read_bytes()
assert (E/'source-report-before.png').read_bytes() != (E/'source-report-after.png').read_bytes()
initial = json.loads((E/'paint-source-report-preflight-2026-10-10T06-47-49-632Z.json').read_text())
assert (E/initial['images'][3]['file']).read_bytes() == (E/rows[2]['images'][3]['file']).read_bytes()
assert (E/initial['images'][3]['file']).read_bytes() != (E/rows[1]['images'][3]['file']).read_bytes()
result = dict(pass_measurement_and_truthful_model_reply=True, probe=probe_name, receipts=names,
              chatgpt_subscription=True, api_fallback=False, exact_source_tolerance=0,
              measured_preview_cells=18695, estimated_protected_artwork_pixels=256,
              lost_scope_negative_control=True, scope_fix_component_only=True,
              undo_42_metadata_zones_previews_and_raw_thumbnail_exact=True,
              full_raster_verification=False, full_export_verification=False)
(E/'online-source-report-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
