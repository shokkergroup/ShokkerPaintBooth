"""Private I29 proof. Never writes catalog assets."""
from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_verdant_script_i29_2026 import paint_verdant_script_i29,spec_verdant_script_i29
n=2048;name=sys.argv[1]if len(sys.argv)>1 else'p1';out=ROOT/f'_houdini_i29_{name}_native';out.mkdir(exist_ok=True);src=np.full((n,n,3),132,np.uint8);mask=np.ones((n,n),np.float32);p=paint_verdant_script_i29(src,(n,n),mask,1667,1,None);s=spec_verdant_script_i29((n,n),1667,1,0,0);p8=np.uint8(np.clip(p*255,0,255))
for fn,img in {'standard.png':p8,'combined.png':np.concatenate((p8,s),axis=1),'metallic.png':s[...,0],'roughness.png':s[...,1],'clearcoat.png':s[...,2],'picker.png':np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(s,(64,64),interpolation=cv2.INTER_AREA)),axis=1)}.items():cv2.imwrite(str(out/fn),img)
c=n//2;cv2.imwrite(str(out/'native_crop.png'),np.concatenate((p8[c-256:c+256,c-256:c+256],s[c-256:c+256,c-256:c+256]),axis=1));print({'paint_std':round(float(p.std()),4),'MRC_std':[round(float(s[...,i].std()),2)for i in range(3)]})
