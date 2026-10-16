"""Independent full-raster and composed-preview proof for the actual scheme conversation."""
from pathlib import Path
import base64, hashlib, io, json, re
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'_codex_mcp_work/chatgpt-dev/59910'
P=ROOT/'_release_evidence/chatgpt-dev/59910/projects'
base_name='ARCA recovered hidden rasters - private59910.spbproj'
after_name='ARCA black gold scheme refined - private59910.spbproj'
undo_name='ARCA black gold scheme Undo - private59910.spbproj'
def read(name): return json.loads((P/name).read_text(encoding='utf-8'))
def rgba(layer): return np.asarray(Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA'))
base,after=map(read,[base_name,after_name])
undo=read(undo_name)
a={l['id']:l for l in base['layers']};b={l['id']:l for l in after['layers']}
assert len(a)==42 and a.keys()==b.keys()
assert [l['id'] for l in base['layers']]==[l['id'] for l in after['layers']]
mapping=[('#ff0000','#151515'),('#01ff00','#282828'),('#0000ff','#b49a55'),('#b49a55','#c2a56a')]
rgb=lambda h:np.array([int(h[i:i+2],16) for i in (1,3,5)],dtype=np.uint8)
changed=[];counts=[]
for lid in a:
    old,new=rgba(a[lid]),rgba(b[lid])
    if lid=='psd_23':
        expected=old.copy()
        for source,target in mapping:
            mask=np.all(expected[:,:,:3]==rgb(source),axis=2)&(expected[:,:,3]>0)
            counts.append(int(mask.sum()));expected[mask,:3]=rgb(target)
        assert np.array_equal(expected,new),'Saved pattern does not equal exact approved mapping'
        changed_pixels=int(np.any(old!=new,axis=2).sum())
        assert np.array_equal(old[:,:,3],new[:,:,3])
    else: assert np.array_equal(old,new),'Unrequested raw layer changed: '+lid
    if not np.array_equal(old,new):changed.append(lid)
assert changed==['psd_23']
# POLISH-F/NUQ: live preview intentionally omits the export-guide group.
# SOURCE and saved guide rasters still retain it. Do not mistake this for damage.
def guide(layer):
    return any(re.search(r'turn\s*off\s*before\s*export',str(v),re.I) for v in
               [layer.get('groupName',''),layer.get('path','')]+[g.get('name') or g.get('path','') for g in layer.get('groupChain',[])])
for old,new,restored in zip(base['layers'],after['layers'],undo['layers']):
    assert np.array_equal(rgba(old),rgba(restored)), 'Undo pixels differ: '+old['id']
    expected_meta={k:v for k,v in old.items() if k!='imgData'}
    if old['id']=='psd_23': expected_meta['visible']=True  # explicit fixture preparation
    assert expected_meta=={k:v for k,v in new.items() if k!='imgData'}
    assert expected_meta=={k:v for k,v in restored.items() if k!='imgData'}
assert after['config']==undo['config']
assert base['config']['zones']==after['config']['zones']
# Composite the actual normal source-over preview stack independently at full size.
composite=Image.new('RGBA',(2048,2048))
for layer in after['layers']:
    if not layer.get('visible') or guide(layer):continue
    assert layer.get('blendMode')=='source-over' and layer.get('opacity')==255 and not layer.get('effects')
    assert not layer.get('clippingMask') and not any(layer.get(k) for k in ('adjHue','adjSat','adjBri'))
    assert all(g.get('mode')=='pass-through' and g.get('opacity')==255 for g in layer.get('groupChain',[]))
    canvas=Image.new('RGBA',(2048,2048));canvas.paste(Image.fromarray(rgba(layer)),tuple(layer['bbox'][:2]));composite=Image.alpha_composite(composite,canvas)
expected_preview=np.asarray(composite.convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS)).astype(np.int16)
actual_preview=np.asarray(Image.open(E/'scheme-refined-preview.png').convert('RGB')).astype(np.int16)
delta=np.max(abs(expected_preview-actual_preview),axis=2)
result={'schema':'spb-black-gold-scheme/2','only_changed_raw_layer':'psd_23','exact_source_pixel_mapping':True,'replacement_pixel_counts':counts,'total_changed_pixels':changed_pixels,'other_41_raw_layers_exact':True,'pattern_alpha_exact':True,'all_42_undo_rasters_exact':True,'layer_metadata_preserved':True,'zones_preserved':True,'composite_preview_max_error':int(delta.max()),'composite_preview_pixels_over_2':int((delta>2).sum()),'all_preview_pixels':int(delta.size),'preview_contract':'POLISH-F/NUQ export-guide omission; full saved guide pixels remain exact','preview_excluded_visible_layers':[l['id'] for l in after['layers'] if l.get('visible') and guide(l)],'mixed_edge_colours_intentionally_preserved':True,'full_export_verified':False,'saved_projects':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in [base_name,after_name,undo_name]}}
(E/'black-gold-scheme-pixels.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
assert delta.max()<=2,'Actual preview differs from the independently composed saved stack'
