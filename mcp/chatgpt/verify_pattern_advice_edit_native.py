"""Compare native discussion-to-edit, Undo and stale-selection receipts."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
files = {
    'before': 'pattern-advice-edit-before-2026-10-10T18-26-33-296Z.json',
    'after': 'pattern-advice-edit-successor-after-2026-10-10T18-29-01-436Z.json',
    'undo': 'pattern-advice-edit-successor-undo-2026-10-10T18-29-21-782Z.json',
    'refused': 'pattern-advice-edit-refusal-after-2026-10-10T18-29-55-789Z.json',
}
states = {k: json.loads((out / v).read_text(encoding='utf-8'))['state'] for k, v in files.items()}
controls = {k: v['editor_capabilities']['pattern_controls'] for k, v in states.items()}
assert [controls[k]['records'][0]['scale'] for k in files] == [0.6, 0.465, 0.6, 0.6]
for s in states.values():
    assert s['layers'] == states['before']['layers'] and s['zones'] == states['before']['zones']
for k in ('undo', 'refused'):
    assert controls[k] == controls['before']
a, b = controls['before']['records'][0].copy(), controls['after']['records'][0].copy()
a.pop('scale'); b.pop('scale'); assert a == b
assert controls['before']['selected_zone'] == controls['after']['selected_zone']
images = {
    'before': 'pattern-advice-edit-before.png',
    'after': 'pattern-advice-edit-successor-after.png',
    'undo': 'pattern-advice-edit-successor-undo.png',
    'refused': 'pattern-advice-edit-refusal-after.png',
}
arrays = {k: np.asarray(Image.open(out / v).convert('RGBA')) for k, v in images.items()}
assert all(x.shape == (256, 256, 4) for x in arrays.values())
changed = np.any(arrays['before'] != arrays['after'], axis=2)
assert np.count_nonzero(changed) > 1000
assert np.array_equal(arrays['before'], arrays['undo'])
assert np.array_equal(arrays['before'], arrays['refused'])
protected = {}
for name in ('numbers', 'sponsors'):
    alpha = Image.open(root / f'_release_evidence/chatgpt-dev/59910/fixtures/layered-protection-a-{name}.png').getchannel('A')
    core = alpha.resize((256, 256), Image.Resampling.LANCZOS).point(lambda x: 255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))
    mask = np.asarray(core) > 0
    count, harm = int(np.count_nonzero(mask)), int(np.count_nonzero(changed & mask))
    assert count > 2000 and harm == 0, (name, count, harm)
    protected[name] = {'opaque_interior_preview_pixels': count, 'changed': harm}
chat = (out / 'pattern-advice-edit-successor-chat.txt').read_text(encoding='utf-8')
refused = (out / 'pattern-advice-edit-stale-selection.txt').read_text(encoding='utf-8')
assert 'Make it a little finer.' in chat and 'Body layer changed' in chat
assert 'Where should it go?' not in chat and 'Which part should I' not in chat
assert 'The selected pattern zone changed since that answer.' in refused
receipt = {
    'pass': True, 'port': 59910, 'native_advice_then_explicit_edit': True,
    'scales': [0.6, 0.465, 0.6, 0.6],
    'same_primary_pattern_and_other_exposed_settings': True,
    'layer_and_zone_summaries_unchanged': True,
    'changed_preview_pixels': int(np.count_nonzero(changed)), 'protected': protected,
    'undo_preview_every_rgba_channel_exact': True,
    'stale_selection_refused_with_exact_controls_and_preview': True,
    'redundant_target_chooser_absent_after_completion': True,
    'negative_baselines': ['pattern-advice-edit-baseline.txt', 'pattern-advice-edit-chat.txt'],
    'state_files': files, 'preview_files': images,
    'screenshots': ['pattern-advice-edit-successor-chat.png', 'pattern-advice-edit-stale-selection.png'],
    'new_saved_projects': 0,
    'limits': 'Private native Offline prototype and generated route/compiler guards. No full raster/project capture, full-output or translucent-edge proof, calibrated UV geometry, actual model-directed edit/Undo, Claude parity or shared runtime adoption claim.',
}
(out / 'pattern-advice-edit-native-acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'scales': receipt['scales'], 'changed_preview_pixels': receipt['changed_preview_pixels'], 'protected': protected, 'undo_exact': True, 'stale_selection_refused': True}))
