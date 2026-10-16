"""Verify actual native saved projects and PNGs, not simulated mutation output."""
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '_codex_mcp_work/chatgpt-dev/59910'
FIX = ROOT / '_release_evidence/chatgpt-dev/59910/fixtures'
PROJECTS = ROOT / '_release_evidence/chatgpt-dev/59910/projects'

def project(stage):
    return json.loads((PROJECTS / f'Layered protection {stage} - private59910.spbproj').read_text(encoding='utf-8'))

MODEL = '--model' in sys.argv
baseline, after, undo = (project(n) for n in ('baseline', 'model-after' if MODEL else 'after', 'model-undo' if MODEL else 'undo'))
assert len(baseline['layers']) == 3
assert after['layers'] == undo['layers'] == baseline['layers'], 'Source layer pixels/settings changed'
assert undo['config']['zones'] == baseline['config']['zones'], 'Undo did not restore all original zones'
assert len(after['config']['zones']) == len(baseline['config']['zones']) + 1
new = [z for z in after['config']['zones'] if z not in baseline['config']['zones']]
assert len(new) == 1
# Zone layer binding is verified below from the saved zone, independently of UI text.
bindings = {k:v for k,v in new[0].items() if 'layer' in k.lower()}
body = next(l for l in baseline['layers'] if l['name'] == 'Body')
assert new[0]['sourceLayers'] == [body['id']], bindings
assert new[0]['sourceLayerBindings'][body['id']]['parts'] == ['Body'], bindings
prefix = 'layered-model' if MODEL else 'layered'
b, a, u, r = [Image.open(OUT / f'{prefix}-{n}-native.png').convert('RGBA') for n in ('before','after','undo','reopened')]
assert b.size == a.size == u.size == r.size == (256,256)
assert b.tobytes() == u.tobytes(), 'Undo changed RGBA pixels'
assert (OUT/f'{prefix}-before-native.png').read_bytes() == (OUT/f'{prefix}-undo-native.png').read_bytes(), 'Undo PNG bytes differ'
assert a.tobytes() == r.tobytes(), 'Reopened saved project differs from actual after preview'
changed = [x != y for x,y in zip(b.get_flattened_data(),a.get_flattened_data())]
assert sum(changed) > 50000, 'Body change was not executed'
protected = {}
for name in ('numbers','sponsors'):
    alpha = Image.open(FIX / f'layered-protection-a-{name}.png').getchannel('A')
    core = alpha.resize(b.size,Image.Resampling.LANCZOS).point(lambda x:255 if x==255 else 0).filter(ImageFilter.MinFilter(3))
    count = sum(x>0 for x in core.get_flattened_data())
    harm = sum(c and x>0 for c,x in zip(changed,core.get_flattened_data()))
    assert count > 2000 and harm == 0, (name,count,harm)
    protected[name] = {'opaque_core_preview_pixels':count,'changed':harm}
result = {'scope':'Synthetic ORA; native 256x256 preview plus all saved 512x512 source-layer records. Not real car UV or full-resolution rendered output.',
          'model_directed':MODEL,
          'changed_preview_pixels':sum(changed),'protected':protected,'saved_layers_exact':True,'zone_bindings':bindings,
          'undo_rgba_and_png_bytes_exact':True,'undo_zones_exact':True,'reopened_preview_rgba_exact':True,
          'before_sha256':hashlib.sha256((OUT/f'{prefix}-before-native.png').read_bytes()).hexdigest(),
          'after_sha256':hashlib.sha256((OUT/f'{prefix}-after-native.png').read_bytes()).hexdigest()}
if MODEL:
    receipt=OUT/'layered-model-probe-2026-10-09T22-10-11-509Z.json'
    probe=json.loads(receipt.read_text(encoding='utf-8'))
    assert probe['exitCode']==0 and not probe['apiFallback'] and probe['authentication']=='ChatGPT'
    writes=[c for c in probe['calls'] if c['tool']=='spb_do']
    assert len(writes)==1
    frame=writes[0]['arguments']['frame']
    assert len(frame['ops'])==1 and frame['ops'][0]['target']=={'kind':'layer','layers':['Body']}
    assert frame['keep']==[{'kind':'layer','layers':['Numbers','Sponsors']}]
    assert any(c['tool']=='spb_check' for c in probe['calls'])
    assert sum(c['tool']=='spb_preview' for c in probe['calls'])>=2
    assert sum(c['tool']=='spb_reply' for c in probe['calls'])==1
    result['model_receipt']=receipt.name
(OUT/f'{prefix}-pixel-acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
