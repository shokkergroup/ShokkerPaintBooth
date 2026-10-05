"""Private Houdini I22 P1 evidence; never writes a live catalog card."""
from pathlib import Path
import sys, cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.expansions.fractured_houdini_latticework_nocturne_i22_2026 import paint_latticework_nocturne_i22, spec_latticework_nocturne_i22

pass_name = sys.argv[1] if len(sys.argv) > 1 else 'p1'
OUT = ROOT / f'_houdini_i22_{pass_name}_native'; OUT.mkdir(exist_ok=True)
n = 2048; source = np.full((n, n, 3), 132, np.uint8); mask = np.full((n, n), 255, np.uint8)
paint = paint_latticework_nocturne_i22(source, (n, n), mask, 77, 1, None)
spec = spec_latticework_nocturne_i22((n, n), 77, 1, 0, 0)
p8 = np.uint8(np.clip(paint*255, 0, 255))
for name, image in {'standard.png': p8, 'combined.png': np.concatenate((p8, spec), 1), 'metallic.png': spec[...,0], 'roughness.png': spec[...,1], 'clearcoat.png': spec[...,2], 'picker.png': np.concatenate((cv2.resize(p8,(64,64),interpolation=cv2.INTER_AREA), cv2.resize(spec,(64,64),interpolation=cv2.INTER_AREA)),1)}.items():
    cv2.imwrite(str(OUT/name), image)
print({'paint_std': round(float(paint.std()), 4), 'MRC_std': [round(float(spec[...,i].std()),2) for i in range(3)]})
