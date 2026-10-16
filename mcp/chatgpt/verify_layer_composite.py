"""Independent lossless preview comparison for the private three-layer fixture."""
import base64
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
PROJECT = ROOT / '_release_evidence/chatgpt-dev/59910/projects/Layered protection baseline - private59910.spbproj'


def check(after_name='protection-successor-after.png', label='zone-frame-composite'):
    data = json.loads(PROJECT.read_text(encoding='utf-8'))
    layers = [Image.open(io.BytesIO(base64.b64decode(l['imgData'].split(',')[1]))).convert('RGBA') for l in data['layers']]
    assert [l['name'] for l in data['layers']] == ['Body', 'Numbers', 'Sponsors']
    assert all(im.size == (512, 512) for im in layers)
    before = Image.open(OUT / 'protection-successor-before.png').convert('RGB')
    after = Image.open(OUT / after_name).convert('RGB')
    assert before.size == after.size == (256, 256)

    def composite(body):
        for im in layers[1:]:
            body = Image.alpha_composite(body, im)
        return body.convert('RGB').resize(before.size, Image.Resampling.LANCZOS)

    def diff(a, b):
        delta = np.abs(np.asarray(a).astype(int) - np.asarray(b).astype(int)).max(axis=2)
        return delta, {'maximum_channel_error': int(delta.max()), 'pixels_over_2': int((delta > 2).sum()), 'pixels_over_28': int((delta > 28).sum())}

    baseline_delta, baseline = diff(composite(layers[0].copy()), before)
    assert baseline_delta.max() <= 1, 'The reference compositor does not explain the unchanged baseline'
    expected = composite(Image.new('RGBA', (512, 512), '#b49a55'))
    delta, comparison = diff(expected, after)
    changed, _ = diff(before, after)
    cores = []
    for row, im in zip(data['layers'][1:], layers[1:]):
        mask = im.getchannel('A').resize(before.size, Image.Resampling.LANCZOS).point(lambda x: 255 if x == 255 else 0).filter(ImageFilter.MinFilter(3))
        core = np.asarray(mask) == 255
        cores.append({'layer': row['name'], 'opaque_core_pixels': int(core.sum()), 'changed_pixels': int(((changed != 0) & core).sum())})
    result = {'scope': 'Lossless 256px native preview of the synthetic three-layer fixture; not full export or calibrated UV evidence.',
              'method': 'Saved raw layers alpha-composited at 512px, then RGB Lanczos downsample. Unchanged baseline validates this reference within one RGB level.',
              'baseline': baseline, 'recoloured_composite': comparison, 'opaque_cores': cores,
              'preview_matches_reference_within_2': bool(delta.max() <= 2),
              'inputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [PROJECT, OUT / 'protection-successor-before.png', OUT / after_name]}}
    if label == 'native-frame-composite':
        saved = json.loads((PROJECT.parent / 'Layered native frame colour after - private59910.spbproj').read_text(encoding='utf-8'))
        undone = json.loads((PROJECT.parent / 'Layered native frame colour undo - private59910.spbproj').read_text(encoding='utf-8'))
        assert saved['config']['zones'] == data['config']['zones'] == undone['config']['zones']
        assert saved['layers'][1:] == data['layers'][1:]
        assert all(a['imgData'] == b['imgData'] for a, b in zip(saved['layers'], data['layers']))
        assert undone['layers'] == data['layers']
        assert (OUT / 'frame-native-colour-undo.png').read_bytes() == (OUT / 'protection-successor-before.png').read_bytes()
        assert delta.max() == 0
        result['native_project_checks'] = {'zones_exact': True, 'protected_layer_records_exact': True, 'all_source_rasters_exact': True, 'undo_all_layer_records_exact': True, 'undo_preview_bytes_exact': True}
    expected.save(OUT / (label + '-expected.png'))
    Image.fromarray(np.stack([np.clip(delta * 4, 0, 255), np.zeros_like(delta), np.zeros_like(delta)], axis=2).astype('uint8')).save(OUT / (label + '-error.png'))
    (OUT / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    import sys
    check(*sys.argv[1:])
