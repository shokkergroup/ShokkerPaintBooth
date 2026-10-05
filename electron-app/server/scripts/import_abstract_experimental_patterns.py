"""
One-off: Copy pattern examples from basespatterns_examples/patternexamples
to assets/patterns/abstract_experimental/ as PNG (engine expects PNG).
Run from V5 folder: python scripts/import_abstract_experimental_patterns.py
"""
import os
from PIL import Image

V5_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(V5_ROOT, "basespatterns_examples", "patternexamples")
DST = os.path.join(V5_ROOT, "assets", "patterns", "abstract_experimental")

# (source filename, pattern_id.png)
MAPPING = [
    ("biomechanical1.JPG", "biomechanical.png"),
    ("biomechanical2.JPG", "biomechanical_2.png"),
    ("fractal1.JPG", "fractal.png"),
    ("fractal2.JPG", "fractal_2.png"),
    ("fractal3.JPG", "fractal_3.png"),
    ("interference.jpg", "interference.png"),
    ("opticalillusion1.JPG", "optical_illusion.png"),
    ("opticalillusion2.JPG", "optical_illusion_2.png"),
    ("soundwave.JPG", "sound_wave.png"),
    ("stardust1.JPG", "stardust.png"),
    ("stardust2.JPG", "stardust_2.png"),
    ("voronoi1.JPG", "voronoi_shatter.png"),
]

os.makedirs(DST, exist_ok=True)
for src_name, out_name in MAPPING:
    src_path = os.path.join(SRC, src_name)
    out_path = os.path.join(DST, out_name)
    if not os.path.isfile(src_path):
        print(f"Skip (missing): {src_name}")
        continue
    img = Image.open(src_path).convert("RGBA")
    img.save(out_path, "PNG")
    print(f"OK: {src_name} -> {out_name}")

print("Done.")
