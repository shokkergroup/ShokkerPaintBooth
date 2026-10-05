"""Report actual named-feature coverage; contract prose alone is not evidence."""
from pathlib import Path
import sys,json,importlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from engine.spec_overlay_v2.geometry import Surface,sat
from engine.spec_overlay_v2.catalog import definitions
class Probe(Surface):
    def __init__(self):super().__init__((1024,1024),42);self.marks=[]
    def mark(self,name,mask,m,r,cc,shade=.5,coat_shade=None,rough_shade=None,coverage=1.):
        a=sat(mask*coverage)
        self.marks.append({'name':name,'mean_coverage':round(float(a.mean()),6),'pixels_over_half':int((a>.5).sum()),'finite':bool(np.isfinite(a).all())})
def main():
    rows={};fingerprints={}
    for item in definitions()['items']:
        slug=item['id'][6:];module=importlib.import_module('engine.spec_overlay_v2.designs.'+slug);s=Probe();getattr(module,slug)(s);rows[item['id']]=s.marks;fingerprints[item['id']]=module.render._spb_source_fingerprint
    (ROOT/'_spec_overlays_v2_work/bake/feature-coverage.json').write_text(json.dumps(rows,indent=2))
    (ROOT/'_spec_overlays_v2_work/bake/feature-fingerprints.json').write_text(json.dumps(fingerprints,indent=2))
    weak=[(pid,m) for pid,marks in rows.items() for m in marks if m['mean_coverage']<.002 or not m['finite']]
    print(json.dumps({'designs':len(rows),'weak_features':weak},indent=2))
if __name__=='__main__':main()
