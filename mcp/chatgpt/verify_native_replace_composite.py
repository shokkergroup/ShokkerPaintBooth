"""Compare native Color Replace and flattened-zone output to the source stack.

Use the engine's actual LANCZOS preview downsampling, not a 2x2 box estimate.
This is an evidence calculation; it does not edit any source or runtime image.
"""
import base64
import io
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
PROJECT = ROOT / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj'


def full(layer):
    im = Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA')
    result = Image.new('RGBA', (2048, 2048))
    result.paste(im, tuple(layer['bbox'][:2]))
    return result


def main():
    names = sys.argv[1:] or ['native-replace-before.png', 'native-replace-after.png', 'native-replace-composite.json']
    assert len(names) == 3 and all(Path(n).name == n for n in names)
    p = json.loads(PROJECT.read_text())
    layer = next(l for l in p['layers'] if l['id'] == 'psd_23')
    original = full(layer)
    data = np.array(original)
    assert np.all(data[:, :, 3] == 255)
    # Actual autoColorReplace distance/blend; equal-distance boundary is no-op.
    d = data[:, :, :3].astype(np.float32)
    dist = np.sqrt(np.sum((d - [255, 0, 0]) ** 2, axis=2))
    amount = np.maximum(0, 1 - dist / np.sqrt(40 ** 2 * 3))[:, :, None]
    data[:, :, :3] = np.floor(d * (1 - amount) + np.array([179, 154, 88]) * amount + 0.5).astype(np.uint8)
    changed = Image.fromarray(data)
    top = Image.new('RGBA', (2048, 2048))
    for l in p['layers']:
        if int(l['id'].split('_')[1]) <= 23 or not l.get('visible'):
            continue
        assert l.get('blendMode') == 'source-over' and l.get('opacity') == 255 and not l.get('effects')
        assert not l.get('clippingMask') and not any(l.get(k) for k in ('adjHue', 'adjSat', 'adjBri'))
        assert all(g.get('mode') == 'pass-through' and g.get('opacity') == 255 for g in l.get('groupChain', []))
        im = full(l)
        top = Image.alpha_composite(top, im)
        original = Image.alpha_composite(original, im)
        changed = Image.alpha_composite(changed, im)
    expected = [np.asarray(im.convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)).astype(np.int16) for im in (original, changed)]
    actual = [np.asarray(Image.open(E / n).convert('RGB')).astype(np.int16) for n in (names[0], names[1], 'helper-ownership-after-native.png')]
    delta = [np.max(abs(a-b), axis=2) for a,b in ((actual[0],expected[0]),(actual[1],expected[1]),(actual[2],expected[1]))]
    # Admit only baseline-matching pixels in the downsampled artwork edge band.
    alpha = np.asarray(top.getchannel('A').resize((1024,1024),Image.Resampling.LANCZOS))
    edge = (alpha > 0) & (alpha < 255) & (delta[0] <= 2)
    lost = edge & (delta[2] > 10) & (delta[1] <= 2)
    rows = []
    for y,x in np.argwhere(lost)[:12]:
        rows.append({'xy':[int(x),int(y)],'baseline':actual[0][y,x].tolist(), 'expected':expected[1][y,x].tolist(),
                     'native_replace':actual[1][y,x].tolist(),'zone_recolour':actual[2][y,x].tolist()})
    metrics = lambda a: {'max':int(a.max()),'mean':float(a.mean()),'p95':float(np.percentile(a,95)),'within_2':int((a<=2).sum())}
    result = {'baseline':metrics(delta[0]),'native_replacement':metrics(delta[1]),'zone_recolour':metrics(delta[2]),
              'qualified_art_edge_pixels':int(edge.sum()),'native_correct_zone_wrong_pixels':int(lost.sum()),'examples':rows,
              'preview_filter':'PIL LANCZOS per shokker_engine_v2.py preview source resize',
              'inputs':names[:2],
              'scope':'Normal source-over saved ARCA stack; source-layer Color Replace versus flattened exact-colour zone. This supersedes the earlier 2x2 BOX estimate. Caller/Undo proof is separate; not full export or other blend modes.'}
    (E/names[2]).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='examples'}))


if __name__ == '__main__':
    main()
