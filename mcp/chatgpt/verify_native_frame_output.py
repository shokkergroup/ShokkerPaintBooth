"""Check saved native render files, independently of preview/tool verdicts."""
import base64
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / '_release_evidence/chatgpt-dev/59910'
EVIDENCE = ROOT / '_codex_mcp_work/chatgpt-dev/59910'


def verify(job_name, label, colour='#b49a55', compare_spec_job=None):
    job = (OUTPUT / job_name).resolve()
    assert job.parent == OUTPUT.resolve() and job.name.startswith('job_render_')
    baseline = json.loads((OUTPUT / 'projects/Layered protection baseline - private59910.spbproj').read_text(encoding='utf-8'))
    layers = [Image.open(io.BytesIO(base64.b64decode(l['imgData'].split(',')[1]))).convert('RGBA') for l in baseline['layers']]
    expected = layers[0].copy() if colour == 'baseline' else Image.new('RGBA', layers[0].size, colour)
    for layer in layers[1:]:
        expected = Image.alpha_composite(expected, layer)
    expected = np.asarray(expected.convert('RGB'))
    files = []
    for name in ['car_num_23371.tga', 'RENDER_paint.png', 'paint_with_decals.png', 'ORIGINAL_paint_with_decals.png']:
        image = Image.open(job / name)
        assert image.size == (512, 512)
        delta = np.abs(np.asarray(image.convert('RGB')).astype(int) - expected.astype(int))
        # Browser alpha compositing of the original navy fixture differs from
        # Pillow by one channel level at674 pixels; retained baseline evidence.
        # The new solid-colour operation must still match exactly (tolerance0).
        tolerance = 1 if colour == 'baseline' else 0
        assert delta.max() <= tolerance, name + ' differs from independently composited paint'
        files.append({'file': name, 'maximum_channel_error': int(delta.max()), 'different_pixels': int((delta.max(axis=2) > 0).sum()), 'reference_tolerance': tolerance, 'sha256': hashlib.sha256((job / name).read_bytes()).hexdigest()})
    spec = np.asarray(Image.open(job / 'car_spec_23371.tga').convert('RGBA'))
    assert spec.shape == (512, 512, 4)
    assert np.array_equal(spec, np.asarray(Image.open(job / 'PREVIEW_spec.png').convert('RGBA')))
    if compare_spec_job:
        other = (OUTPUT / compare_spec_job).resolve()
        assert other.parent == OUTPUT.resolve() and other.name.startswith('job_render_')
        assert np.array_equal(spec, np.asarray(Image.open(other / 'car_spec_23371.tga').convert('RGBA')))
    result = {'scope': 'Private synthetic three-layer fixture: actual native full Render output at source resolution512px. No real-car UV, in-simulator or installer acceptance.',
              'job': job_name, 'colour': colour, 'files': files,
              'spec_tga_matches_spec_png': True, 'spec_exact_to_comparison_job': compare_spec_job,
              'spec_sha256': hashlib.sha256((job / 'car_spec_23371.tga').read_bytes()).hexdigest()}
    (EVIDENCE / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    import sys
    verify(*sys.argv[1:])
