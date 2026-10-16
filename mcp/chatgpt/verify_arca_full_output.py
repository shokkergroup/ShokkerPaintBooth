"""Compare real 2048px ARCA output with independently composed saved layers.

Reports both guide-included and guide-omitted references. Neither reference is
silently selected to hide an output-contract mismatch. No app/image mutation.
"""
import base64
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_release_evidence/chatgpt-dev/59910'
EVIDENCE = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def guide(layer):
    return any(re.search(r'turn\s*off\s*before\s*export', str(v), re.I) for v in
               [layer.get('groupName', ''), layer.get('path', '')] +
               [g.get('name') or g.get('path', '') for g in layer.get('groupChain', [])])


def compose(doc, omit_guides):
    result = Image.new('RGBA', (2048, 2048))
    for layer in doc['layers']:
        if not layer.get('visible') or (omit_guides and guide(layer)):
            continue
        assert layer.get('blendMode') == 'source-over' and layer.get('opacity') == 255
        assert not layer.get('effects') and not layer.get('clippingMask')
        assert not any(layer.get(k) for k in ('adjHue', 'adjSat', 'adjBri'))
        assert all(g.get('mode') == 'pass-through' and g.get('opacity') == 255 for g in layer.get('groupChain', []))
        image = Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA')
        canvas = Image.new('RGBA', result.size)
        canvas.paste(image, tuple(layer['bbox'][:2]))
        result = Image.alpha_composite(result, canvas)
    return np.asarray(result.convert('RGB')).astype(np.int16)


def main(job_name, project_name, label, compare_job=None):
    job, project = (OUT / job_name).resolve(), (OUT / 'projects' / project_name).resolve()
    assert job.parent == OUT.resolve() and job.name.startswith('job_render_')
    assert project.parent == (OUT / 'projects').resolve() and project.suffix == '.spbproj'
    assert re.fullmatch(r'[a-z0-9-]+', label)
    doc = json.loads(project.read_text(encoding='utf-8'))
    assert len(doc['layers']) == 42
    expected = {'guides_omitted': compose(doc, True), 'guides_included': compose(doc, False)}
    results = []
    for name in ['car_num_23371.tga', 'RENDER_paint.png', 'paint_with_decals.png', 'ORIGINAL_paint_with_decals.png', 'PREVIEW_paint.png']:
        image = Image.open(job / name)
        assert image.size == (2048, 2048)
        actual = np.asarray(image.convert('RGB')).astype(np.int16)
        row = {'file': name, 'sha256': hashlib.sha256((job / name).read_bytes()).hexdigest()}
        for mode, ref in expected.items():
            delta = np.abs(actual - ref).max(axis=2)
            row[mode] = {'maximum_channel_error': int(delta.max()), 'different_pixels': int((delta > 0).sum()), 'pixels_over_2': int((delta > 2).sum())}
        results.append(row)
    spec = np.asarray(Image.open(job / 'car_spec_23371.tga').convert('RGBA'))
    result = {'scope': 'Actual native full render of saved 42-layer ARCA project. Independent source-over composition; no new model inference, UV calibration or simulator acceptance.',
              'job': job_name, 'project': project_name, 'project_sha256': hashlib.sha256(project.read_bytes()).hexdigest(),
              'visible_guide_layers': [l['id'] for l in doc['layers'] if l.get('visible') and guide(l)],
              'files': results, 'spec_tga_matches_spec_png': bool(np.array_equal(spec, np.asarray(Image.open(job / 'PREVIEW_spec.png').convert('RGBA'))))}
    if compare_job:
        other = (OUT / compare_job).resolve()
        assert other.parent == OUT.resolve() and other.name.startswith('job_render_')
        result['spec_matches_comparison_job'] = bool(np.array_equal(spec, np.asarray(Image.open(other / 'car_spec_23371.tga').convert('RGBA'))))
        result['comparison_job'] = compare_job
    result['paint_tolerance'] = 'Maximum2 RGB levels for independent Pillow versus browser source-over composition; no claim of byte equality.'
    result['accepted'] = all(row['guides_omitted']['pixels_over_2'] == 0 for row in results) and result['spec_tga_matches_spec_png'] and result.get('spec_matches_comparison_job', True)
    (EVIDENCE / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    assert result['accepted'], 'Full output differs: inspect the retained receipt before accepting.'


if __name__ == '__main__':
    main(*sys.argv[1:])
