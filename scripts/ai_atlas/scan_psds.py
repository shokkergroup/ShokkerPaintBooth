#!/usr/bin/env python
"""Scan a folder tree of PSDs and record their LAYER NAMES (no pixel decoding): used to find the owner's own livery PSDs, and the car TEMPLATE PSDs (those with Mask + Wire layers)
for the car library.  Incremental JSONL: re-running skips files already scanned.  SPB-AI 2026-09-30.
python scripts/ai_atlas/scan_psds.py "C:/1A - Master Graphics Folder/iRACING Graphics Folders" _easy_claude_work/atlas/psd_scan.jsonl"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from psd_tools import PSDImage
root, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(out), exist_ok=True)
done = set()
if os.path.exists(out):
    for ln in open(out, encoding='utf-8'):
        try: done.add(json.loads(ln)['path'])
        except Exception: pass
n = 0; t0 = time.time()
for dp, dns, fns in os.walk(root):
    for fn in sorted(fns):
        if not fn.lower().endswith('.psd'): continue
        p = os.path.join(dp, fn)
        if p in done: continue
        rec = {'path': p, 'size_mb': round(os.path.getsize(p) / 1e6, 1)}
        try:
            psd = PSDImage.open(p)
            names = []
            def walk(layers, depth=0):
                for l in layers:
                    names.append(('  ' * depth) + l.name)
                    if l.is_group(): walk(l, depth + 1)
            walk(psd)
            low = [x.strip().lower() for x in names]
            rec.update(w=psd.width, h=psd.height, layers=names[:80], n_layers=len(names),
                       has_mask=any(x == 'mask' for x in low), has_wire=any(x in ('wire', 'wireframe') for x in low))
        except Exception as e:
            rec['error'] = str(e)[:120]
        open(out, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
        n += 1
        if n % 25 == 0: print(n, 'scanned', round(time.time() - t0), 's', fn[:50], flush=True)
print('done', n, 'new files')
