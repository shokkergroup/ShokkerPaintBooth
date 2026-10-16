"""Staging-only H4-I2 proof; diagnostic images are not track captures."""
from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_cinder_cross_i2_2026 import paint_cinder_cross_i2,spec_cinder_cross_i2
n=1024;out=ROOT/'_houdini_h4_i2_p5_dev';out.mkdir(exist_ok=True);src=np.full((n,n,3),132,np.uint8);mask=np.full((n,n),255,np.uint8);p=paint_cinder_cross_i2(src,(n,n),mask,42,1,None);s=spec_cinder_cross_i2((n,n),42,1,0,0);p8=np.clip(p*255,0,255).astype(np.uint8);pick=np.concatenate((cv2.resize(p8,(48,48),interpolation=cv2.INTER_AREA),cv2.resize(s,(48,48),interpolation=cv2.INTER_AREA)),1);pick[:,47:49]=20;M,R,C=(s[...,i].astype(np.float32)/255 for i in range(3));graze=np.dstack([np.clip(1.18*C*(1-R)+.22*M,0,1),np.clip(1.27*M*(1-R)+.18*C,0,1),np.clip(.86*R*(1-M),0,1)]);tu=np.array([[250,14,249],[155,68,142],[216,35,203],[91,129,92],[238,25,234],[173,81,171],[122,108,116],[200,47,190]],np.uint8);hit=np.zeros((n,n),bool)
for q in tu:hit|=np.all(s==q,2)
sec=np.zeros((n,n,3),np.uint8);sec[hit]=[255,160,48]
for name,a in {'standard.png':cv2.resize(p8,(256,256),interpolation=cv2.INTER_AREA),'picker_split.png':pick,'literal_mrc.png':np.concatenate([np.dstack([s[...,i]]*3) for i in range(3)],1),'grazing_diagnostic_not_track.png':cv2.resize(graze,(1024,512),interpolation=cv2.INTER_LINEAR),'exact_secret_diagnostic_not_track.png':sec}.items():cv2.imwrite(str(out/name),cv2.cvtColor((np.clip(a*255,0,255).astype(np.uint8) if a.dtype.kind=='f' else a),cv2.COLOR_RGB2BGR))
print('paint_std=%.4f mrc_std=%.2f/%.2f/%.2f'%(p.std(),*(s[...,i].std() for i in range(3))))
