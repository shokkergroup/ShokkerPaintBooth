from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_ghost_orbit_i2_2026 import paint_ghost_orbit_i2,spec_ghost_orbit_i2
out=ROOT/'_houdini_h3_i2_p1_dev';out.mkdir(exist_ok=True);n=1024;src=np.full((n,n,3),132,np.uint8);mask=np.full((n,n),255,np.uint8);p=paint_ghost_orbit_i2(src,(n,n),mask,42,1,None);s=spec_ghost_orbit_i2((n,n),42,1,0,0);p8=np.clip(p*255,0,255).astype(np.uint8);pick=np.concatenate((cv2.resize(p8,(48,48),interpolation=cv2.INTER_AREA),cv2.resize(s,(48,48),interpolation=cv2.INTER_AREA)),1);pick[:,47:49]=20
M,R,C=(s[...,i].astype(np.float32)/255 for i in range(3));grazing=np.dstack([np.clip(1.18*C*(1-R)+.22*M,0,1),np.clip(1.27*M*(1-R)+.18*C,0,1),np.clip(.86*R*(1-M),0,1)]);tuples=np.array([[250,14,249],[155,68,142],[216,35,203],[91,129,92],[238,25,234],[173,81,171],[122,108,116],[200,47,190]],np.uint8);hit=np.zeros(s.shape[:2],bool)
for q in tuples:hit|=np.all(s==q,2)
secret=np.zeros((*hit.shape,3),np.uint8);secret[hit]=[190,116,255]
for name,a in {'standard.png':cv2.resize(p8,(256,256),interpolation=cv2.INTER_AREA),'picker_split.png':pick,'literal_mrc.png':np.concatenate([np.dstack([s[...,i]]*3) for i in range(3)],1),'grazing_diagnostic_not_track.png':cv2.resize(grazing,(1024,512),interpolation=cv2.INTER_LINEAR),'exact_secret_diagnostic_not_track.png':cv2.resize(secret,(1024,1024),interpolation=cv2.INTER_NEAREST)}.items():cv2.imwrite(str(out/name),cv2.cvtColor((np.clip(a*255,0,255).astype(np.uint8) if a.dtype.kind=='f' else a),cv2.COLOR_RGB2BGR))
print('paint_std=%.4f mrc_std=%.2f/%.2f/%.2f'%(p.std(),*(s[...,i].std() for i in range(3))))
