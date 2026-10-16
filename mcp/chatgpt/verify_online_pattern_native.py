"""Verify actual MCP/model edits, live Undo and private full-render output."""
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
renders = root / '_release_evidence/chatgpt-dev/59910'

def packet(name):
    return json.loads((out / name).read_text(encoding='utf-8'))

def value(name):
    d = packet(name)
    assert not d['result'].get('isError')
    return json.loads(d['result']['content'][0]['text'])

context_file = 'online-pattern-successor-context-2026-10-10T18-43-20-003Z.json'
after_file = 'online-pattern-successor-after-2026-10-10T18-43-44-817Z.json'
undo_file = 'online-pattern-successor-undo-state-2026-10-10T18-48-24-337Z.json'
tweak_file = 'online-pattern-successor-tweak-2026-10-10T18-43-30-264Z.json'
before, after, undo = value(context_file)['paint']['state']['data'], value(after_file), value(undo_file)
controls = [s['editor_capabilities']['pattern_controls'] for s in (before, after, undo)]
assert [c['records'][0]['scale'] for c in controls] == [0.6, 0.465, 0.6]
assert before['layers'] == after['layers'] == undo['layers']
assert before['zones'] == after['zones'] == undo['zones']
assert controls[0] == controls[2]
a, b = controls[0]['records'][0].copy(), controls[1]['records'][0].copy()
a.pop('scale'); b.pop('scale'); assert a == b
assert controls[0]['selected_zone'] == controls[1]['selected_zone']
tweak = value(tweak_file)
assert tweak['changed'] and tweak['zones'] == {'added': [], 'edited': ['Everything Else']}
assert tweak['measured']['scope']['layers'] == ['Body'] and not tweak['measured']['scope']['whole_car']
assert sorted(tweak['measured']['scope']['protected_decal_layers']) == ['Numbers', 'Sponsors']
assert tweak['verify']['verdict'] == 'ok' and not tweak['verify']['failed']
negative = value('online-pattern-edit-tweak-2026-10-10T18-34-12-849Z.json')
assert negative['measured']['scope']['whole_car'], 'Retain the actual incorrect-scope baseline'
preview_before = np.asarray(Image.open(out / 'online-pattern-edit-before.png').convert('RGBA'))
preview_after = np.asarray(Image.open(out / 'online-pattern-successor-after-preview.png').convert('RGBA'))
preview_undo = np.asarray(Image.open(out / 'online-pattern-successor-undo-preview.png').convert('RGBA'))
assert preview_before.shape == preview_after.shape == preview_undo.shape == (256, 256, 4)
assert np.array_equal(preview_before, preview_undo)
preview_changed = np.any(preview_before != preview_after, axis=2)
assert np.count_nonzero(preview_changed) > 1000
baseline_job = renders / 'job_render_1791658194_23371_ab838fe63771'
after_job = renders / 'job_render_1791657845_23371_22ca8c24f049'
captures = out / 'full-output/online-pattern'
captures.mkdir(parents=True, exist_ok=True)
for label, job in [('restored', baseline_job), ('after', after_job)]:
    for kind, name in [('paint', 'car_num_23371.tga'), ('spec', 'car_spec_23371.tga')]:
        destination = captures / f'{label}-{kind}.tga'
        if not destination.exists():
            shutil.copyfile(job / name, destination)
full_before = np.asarray(Image.open(captures / 'restored-paint.tga').convert('RGBA'))
full_after = np.asarray(Image.open(captures / 'after-paint.tga').convert('RGBA'))
assert full_before.shape == full_after.shape == (512, 512, 4)
full_changed = np.any(full_before != full_after, axis=2)
assert np.count_nonzero(full_changed) > 1000
assert np.array_equal(np.asarray(Image.open(captures / 'restored-spec.tga')), np.asarray(Image.open(captures / 'after-spec.tga')))
protected = {}
for name in ('numbers', 'sponsors'):
    alpha = Image.open(renders / f'fixtures/layered-protection-a-{name}.png').getchannel('A')
    core = alpha.point(lambda x: 255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(core) > 0
    assert mask.shape == full_changed.shape
    count, harm = int(np.count_nonzero(mask)), int(np.count_nonzero(mask & full_changed))
    assert count > 2000 and harm == 0
    small = np.asarray(alpha.resize((256, 256), Image.Resampling.LANCZOS).point(lambda x: 255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))) > 0
    assert np.count_nonzero(small & preview_changed) == 0
    protected[name] = {'full_512px_opaque_interior_pixels': count, 'changed': harm, 'preview_opaque_interior_pixels': int(np.count_nonzero(small))}
for name in ['online-pattern-successor-render-2026-10-10T18-44-05-821Z.json', 'online-pattern-undo-render-2026-10-10T18-39-11-659Z.json']:
    render = value(name)
    assert render['rendered'] and render['files_saved'] == 0 and not render['pushed_live']
for name in ['online-pattern-successor-reply-2026-10-10T18-44-44-030Z.json', 'online-pattern-successor-undo-reply-2026-10-10T18-48-30-977Z.json']:
    assert not packet(name)['result'].get('isError')
receipt = {
    'pass': True, 'port': 59910, 'controlled_current_Codex_model_MCP_acceptance': True,
    'scales': [0.6, 0.465, 0.6], 'same_other_exposed_controls_and_summary_records': True,
    'correct_native_tool_and_chat_Body_scope': True, 'artwork_and_spill_checks_retained': True,
    'preview_undo_every_rgba_channel_exact': True,
    'preview_changed_pixels': int(np.count_nonzero(preview_changed)),
    'full_512px_paint_changed_pixels': int(np.count_nonzero(full_changed)),
    'full_512px_spec_exact': True, 'protected': protected,
    'context': context_file, 'after': after_file, 'undo': undo_file, 'tweak': tweak_file,
    'baseline_job': str(baseline_job.relative_to(root)), 'after_job': str(after_job.relative_to(root)),
    'full_output_captures': str(captures.relative_to(root)),
    'baseline_note': 'Restored0.6 full output was rendered again after native MCP Undo. The earlier baseline job expired from temporary render retention; preserve these four scoped TGA witnesses for reproducibility.',
    'negative_baseline': 'online-pattern-edit-tweak-2026-10-10T18-34-12-849Z.json',
    'render_modal_negative': 'online-pattern-send-overlay.png',
    'separate_model_API_calls': 0, 'new_saved_projects': 0,
    'limits': 'Synthetic three-layer512px fixture, finite controlled current-model MCP interaction. Full paint/spec output and opaque fixture interiors inspected; no translucent-edge/source-buffer audit, real-car UV/in-simulator acceptance, actual Claude parity, unattended customer setup/wake-up or shared adoption proof. Render files stay in private workspace; external deployment blocked. Render-modal successor acceptance is recorded separately.',
}
(out / 'online-pattern-native-acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: receipt[k] for k in ['pass', 'scales', 'preview_changed_pixels', 'full_512px_paint_changed_pixels', 'full_512px_spec_exact', 'protected']}))
