"""Verify actual on-disk TGA pixels, alpha and recorded full-render stage time."""
from pathlib import Path
import json
import re
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'_astra40_work/full_pipeline/report.json'; rows=json.loads(path.read_text())
    assert len(rows)==40,'Need all forty real exports'
    native=json.loads((ROOT/'_astra40_work/native_report.json').read_text())
    for fid,row in rows.items():
        out=path.parent/fid
        log=(out/'engine.log').read_text(encoding='utf-8')
        row['finish_stage_seconds']=float(re.findall(r'All finishes applied: ([0-9.]+)s',log)[-1])
        for kind,prefix in [('paint','car_num'),('spec','car_spec')]:
            exported=Image.open(out/(prefix+'_ASTRA_REVIEW.tga'))
            assert exported.size==(2048,2048),(fid,kind,exported.size)
            if kind=='spec':
                assert 'A' in exported.getbands(),(fid,exported.mode)
                row['tga_alpha_range']=list(exported.getchannel('A').getextrema())
                assert row['tga_alpha_range']==[255,255],fid
            actual=np.asarray(exported.convert('RGB'))
            expected=np.asarray(Image.open(ROOT/'_astra40_work'/fid/(kind+'.png')).convert('RGB'))
            row[kind+'_tga_mae']=float(np.abs(actual.astype(np.float32)-expected).mean())
            assert row[kind+'_tga_mae']<1.0,(fid,kind,row[kind+'_tga_mae'])
            if native[fid]['lane']=='MAD SCIENTIST':
                q=actual.astype(np.uint32)
                count=int(np.unique(q[...,0]*65536+q[...,1]*256+q[...,2]).size)
                row.setdefault('distinct_rgb',{})[kind]=count
                assert count>=2000000,(fid,kind,count)
        assert row['alpha_range']==[255,255],fid
        assert len(row['generator_calls'])==1,fid
        assert row['finish_stage_seconds']<=3.,(fid,row['finish_stage_seconds'])
    path.write_text(json.dumps(rows,indent=2)+'\n')
    print('40/40 actual TGA pairs match native; alpha 255; one native build each; render stages',
          min(r['finish_stage_seconds'] for r in rows.values()),'to',max(r['finish_stage_seconds'] for r in rows.values()),'seconds')
    print('Maximum pigment MAE',max(r['paint_tga_mae'] for r in rows.values()),
          'maximum packed-spec MAE',max(r['spec_tga_mae'] for r in rows.values()))
if __name__=='__main__':main()
