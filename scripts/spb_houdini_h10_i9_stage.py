"""H10-I9 P9 private visual gate — never a live promotion."""
from pathlib import Path
import sys,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.expansions.fractured_houdini_marble_rose_i9_2026 import paint_marble_rose_i9,spec_marble_rose_i9
out=ROOT/'_houdini_h10_i9_p9_dev';out.mkdir(exist_ok=True);n=1024;src=np.full((n,n,3),132,np.uint8);mask=np.full((n,n),255,np.uint8);p=paint_marble_rose_i9(src,(n,n),mask,42,1,None);s=spec_marble_rose_i9((n,n),42,1,0,0);p8=np.uint8(np.clip(p*255,0,255));M,R,C=(s[...,i].astype(np.float32)/255 for i in range(3));g=np.dstack([np.clip(1.18*C*(1-R)+.22*M,0,1),np.clip(1.27*M*(1-R)+.18*C,0,1),np.clip(.86*R*(1-M),0,1)])
for name,img in {'standard.png':p8,'combined.png':np.concatenate((p8,s),1),'metallic.png':s[...,0],'roughness.png':s[...,1],'clearcoat.png':s[...,2],'neutral.png':np.uint8(np.clip(p8*.82+25,0,255)),'grazing_sim.png':np.uint8(g*255),'picker.png':np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA),cv2.resize(s,(64,64),interpolation=cv2.INTER_AREA)),1)}.items():cv2.imwrite(str(out/name),img)
print({'paint_std':round(float(p.std()),4),'MRC_std':[round(float(s[...,i].std()),2) for i in range(3)]})
