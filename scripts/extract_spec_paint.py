"""One-off: extract spec_/paint_ block from shokker_engine_v2 to engine/spec_paint.py"""
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
monolith = os.path.join(root, 'shokker_engine_v2.py')
out_path = os.path.join(root, 'engine', 'spec_paint.py')

with open(monolith, 'r', encoding='utf-8') as f:
    lines = f.readlines()

header = '''"""
engine/spec_paint.py - Standard spec_ and paint_ functions (bases + effects).
Extracted from shokker_engine_v2 for easier editing.
"""
import numpy as np
from PIL import Image, ImageFilter
from engine.core import multi_scale_noise, get_mgrid
from engine.utils import perlin_multi_octave, generate_perlin_noise_2d

'''

# Line 74-1746 (1-based) = index 73-1745
block = ''.join(lines[73:1746])
with open(out_path, 'w', encoding='utf-8') as out:
    out.write(header + block)
print('Wrote', out_path, len(block), 'chars')
