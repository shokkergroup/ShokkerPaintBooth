"""H9 Velvet Dagger I2 staged proof — not a live-catalog promotion."""
from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_velvet_dagger_i2_2026 import paint_velvet_dagger_i2,spec_velvet_dagger_i2
out=ROOT/'_houdini_h9_i2_p1_dev';out.mkdir(exist_ok=True);n=1024;src=np.full((n,n,3),132,np.uint8);mask=np.full((n,n),255,np.uint8)
p=paint_velvet_dagger_i2(src,(n,n),mask,42,1,None);s=spec_velvet_dagger_i2((n,n),42,1,0,0);p8=np.clip(p*255,0,255).astype(np.uint8);M,R,C=(s[...,i].astype(np.float32)/255 for i in range(3))
neutral=np.clip(p8*.86+20,0,255).astype(np.uint8);graze=np.dstack([np.clip(1.18*C*(1-R)+.22*M,0,1),np.clip(1.27*M*(1-R)+.18*C,0,1),np.clip(.86*R*(1-M),0,1)]);combo=np.concatenate((p8,s),1);picker=np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(s,(64,64),interpolation=cv2.INTER_AREA)),1)
cv2.imwrite(str(out/'standard.png'),p8);cv2.imwrite(str(out/'combined.png'),combo);cv2.imwrite(str(out/'neutral.png'),neutral);cv2.imwrite(str(out/'grazing_sim.png'),np.uint8(graze*255));cv2.imwrite(str(out/'picker.png'),picker)
print({'seconds':'staged','paint_std':round(float(p.std()),4),'MRC_std':[round(float(s[...,i].std()),2) for i in range(3)],'MRC_range':[(int(s[...,i].min()),int(s[...,i].max())) for i in range(3)]})
