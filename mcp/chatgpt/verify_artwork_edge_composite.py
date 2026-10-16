"""Adjudicate retained artwork contribution in saved native preview evidence.

Only use isolated 2x2 source blocks: red target + one fractional-alpha normal
art layer, with every other overlying layer transparent. This excludes both
downsampling ambiguity and overlapping artwork. No runtime/source mutation.
"""
import base64
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
PROJECT = ROOT / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj'


def rgba(layer):
    im = Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA')
    out = Image.new('RGBA', (2048, 2048))
    out.paste(im, tuple(layer['bbox'][:2]))
    return np.asarray(out).astype(np.float32)


def blocks(a):
    return a.reshape(1024, 2, 1024, 2, -1).transpose(0, 2, 1, 3, 4).reshape(1024, 1024, 4, -1)


def main():
    names = sys.argv[1:] or ['helper-ownership-before-native.png', 'helper-ownership-after-native.png', 'artwork-edge-composite.json']
    assert len(names) == 3 and all(Path(n).name == n for n in names)
    assert names[0].endswith('.png') and names[1].endswith('.png') and names[2].endswith('.json')
    project = json.loads(PROJECT.read_text())
    before_path = E / names[0]
    after_path = E / names[1]
    before, after = [np.asarray(Image.open(p).convert('RGB')).astype(np.float32) for p in (before_path, after_path)]
    assert before.shape == after.shape == (1024, 1024, 3)
    target = next(l for l in project['layers'] if l['id'] == 'psd_23')
    red = np.all(rgba(target) == [255, 0, 0, 255], axis=2)
    layers = [l for l in project['layers'] if int(l['id'].split('_')[1]) > 23 and l.get('visible')]
    arrays = [rgba(l) for l in layers]
    occupied = sum((a[:, :, 3] > 0).astype(np.uint8) for a in arrays)
    rows = []
    for layer, a in zip(layers, arrays):
        assert layer.get('opacity') == 255 and layer.get('blendMode') == 'source-over'
        assert not layer.get('effects') and not layer.get('rotation')
        assert not layer.get('clippingMask') and not layer.get('adjHue') and not layer.get('adjSat') and not layer.get('adjBri')
        assert all(g.get('opacity') == 255 and g.get('mode') == 'pass-through' for g in layer.get('groupChain', []))
        b = blocks(a)
        eligible = red & (occupied == (a[:, :, 3] > 0)) & (a[:, :, 3] < 128)
        clean = blocks(eligible[:, :, None]).all(axis=(2, 3)) & (b[:, :, :, 3].sum(axis=2) > 0)
        if not clean.any():
            continue
        alpha = b[:, :, :, 3:4] / 255
        expected_before = (alpha * b[:, :, :, :3] + (1 - alpha) * [255, 0, 0]).mean(axis=2)
        expected_after = (alpha * b[:, :, :, :3] + (1 - alpha) * [179, 154, 88]).mean(axis=2)
        # Baseline agreement validates the simple compositing model per pixel.
        qualified = clean & (np.max(abs(before - expected_before), axis=2) <= 1)
        err = np.max(abs(after - expected_after), axis=2)
        flat = np.all(after == [179, 154, 88], axis=2)
        lost = qualified & flat & (err > 3)
        examples = []
        for y, x in np.argwhere(lost)[:6]:
            examples.append({'preview_xy': [int(x), int(y)], 'source_xy': [int(2*x), int(2*y)],
                             'art_rgba_2x2': b[y, x].astype(int).tolist(), 'before': before[y, x].astype(int).tolist(),
                             'after': after[y, x].astype(int).tolist(), 'expected_after': expected_after[y, x].round(2).tolist()})
        rows.append({'id': layer['id'], 'name': layer['name'], 'isolated_blocks': int(clean.sum()),
                     'baseline_qualified': int(qualified.sum()), 'lost_artwork_contribution': int(lost.sum()),
                     'largest_expected_composite_error': float(err[lost].max()) if lost.any() else 0,
                     'correct_composite_within_1': int((qualified & (err <= 1)).sum()), 'examples': examples})
    total = sum(r['lost_artwork_contribution'] for r in rows)
    result = {'defect_proven': False, 'historical_box_estimate': True, 'candidate_pixels': total, 'layers': rows,
              'evidence_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (PROJECT, before_path, after_path)},
              'scope': 'Historical 2x2 BOX estimate only. SPB uses LANCZOS, so this calculation can flag correct native output and does not prove a defect. Use verify_native_replace_composite.py and its full-stack LANCZOS receipt. Earlier receipts remain historical and are superseded.'}
    (E / names[2]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'defect_proven': False, 'historical_box_estimate': True, 'candidate_pixels': total}))


if __name__ == '__main__':
    main()
