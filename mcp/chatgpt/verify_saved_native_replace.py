"""Full saved-raster proof for the native source-layer replacement journey."""
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
BASE = ROOT / '_release_evidence/chatgpt-dev/59910/projects/ARCA recovered hidden rasters - private59910.spbproj'


def rgba(layer):
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(layer['imgData'].split(',')[1]))).convert('RGBA'))


def main():
    after_path, undo_path = [Path(p).resolve() for p in sys.argv[1:]]
    for p in (after_path, undo_path):
        assert p.is_relative_to(ROOT / '_release_evidence/chatgpt-dev/59910/projects')
    docs = [json.loads(p.read_text(encoding='utf-8')) for p in (BASE, after_path, undo_path)]
    rows = [{l['id']: l for l in d['layers']} for d in docs]
    assert len(rows[0]) == 42 and rows[0].keys() == rows[1].keys() == rows[2].keys()
    changed = []
    for lid in rows[0]:
        a,b,c = [rgba(r[lid]) for r in rows]
        assert np.array_equal(a,c), f'Undo raw raster differs: {lid}'
        if not np.array_equal(a,b):
            changed.append(lid)
            assert lid == 'psd_23', f'Unrequested layer changed: {lid}'
            assert np.array_equal(a[:,:,3],b[:,:,3]), 'Alpha changed'
            d = a[:,:,:3].astype(np.float32)
            dist = np.sqrt(np.sum((d-[255,0,0])**2,axis=2))
            amount = np.maximum(0,1-dist/np.sqrt(40**2*3))[:,:,None]
            expected = np.floor(d*(1-amount)+np.array([179,154,88])*amount+.5).astype(np.uint8)
            expected[a[:,:,3]==0] = a[:,:,:3][a[:,:,3]==0]
            error = np.max(abs(expected.astype(np.int16)-b[:,:,:3].astype(np.int16)))
            assert error <= 1, f'Native source kernel mismatch: {error}'
            changed_pixels = int(np.any(a!=b,axis=2).sum())
            assert not np.any(a[dist>np.sqrt(40**2*3)] != b[dist>np.sqrt(40**2*3)])
        # Showing the chosen pattern is deliberate test preparation. All other
        # visibility, alpha locks, transforms, masks, effects and grouping agree.
        for r in rows[1:]:
            original={k:v for k,v in rows[0][lid].items() if k not in ('imgData','visible')}
            current={k:v for k,v in r[lid].items() if k not in ('imgData','visible')}
            assert original == current, f'Non-pixel layer metadata changed: {lid}'
            assert r[lid].get('visible') == (True if lid=='psd_23' else rows[0][lid].get('visible'))
    assert changed == ['psd_23']
    result={'pass':True,'only_changed_raster':'psd_23','changed_source_pixels':changed_pixels,
            'source_kernel_max_error':int(error),'all_42_raw_rasters_restored_by_chat_undo':True,
            'other_layer_pixels_and_metadata_preserved':True,
            'saved_projects':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,after_path,undo_path)},
            'scope':'Full saved RGBA buffers from native Offline Run/Save/chat Undo/Save. Original recovered ARCA source; showing pattern is explicit preparation. Preview composite proof separate; no full render/export, online inference, other-car or packaged-release claim.'}
    (E/'native-helper-replace-saved.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
