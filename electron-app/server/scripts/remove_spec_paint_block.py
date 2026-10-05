"""Remove the spec_gloss..paint_diamond_sparkle block from shokker_engine_v2 (now in engine/spec_paint)."""
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(root, 'shokker_engine_v2.py')
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# spec_gloss at 1-based 81, CHAMELEON at 1755. Remove 80:1754 (0-based).
new_lines = lines[:80] + lines[1754:]
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Removed lines 81-1754', len(lines), '->', len(new_lines))
