"""Scratch helper (lane C v3): print hand-written articles of a domain compactly. python enc_v3_dump.py <domain> [id-substring]"""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
d = json.load(open(R/'data/encyclopedia'/(sys.argv[1]+'.json'), encoding='utf-8'))
for a in d['articles']:
    if len(sys.argv) > 2 and sys.argv[2] not in a['id']: continue
    print('##', a['id'], '|', a['title'], '| quick' if a.get('quick') else '')
    print('S:', a['summary']); print('W:', a['what'][:900])
    for k in ('how','tips','pitfalls'):
        if a.get(k): print(k[0].upper()+':', ' // '.join(a[k]))
    if a.get('controls'): print('C:', '; '.join('%s [%s|%s] %s' % (c['label'], c.get('range',''), c.get('default',''), c.get('effect','')) for c in a['controls']))
    print('R:', a.get('related'), 'SRC:', a['sources'][:4])
