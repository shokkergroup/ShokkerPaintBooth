"""Remove the Color Shift block from shokker_engine_v2 (now in engine/color_shift + core)."""
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(root, 'shokker_engine_v2.py')
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
# Find "# COLOR SHIFT CORE" and "# PRIZM V4 FUNCTIONS"
start = end = None
for i, line in enumerate(lines):
    if "# COLOR SHIFT CORE" in line:
        start = i  # drop from this line (the section header)
        break
for i, line in enumerate(lines):
    if "# PRIZM V4 FUNCTIONS" in line and "EXTRACTED TO" in line:
        end = i  # keep from this line
        break
if start is None or end is None:
    print("Could not find block boundaries", start, end)
    exit(1)
new_lines = lines[:start] + lines[end:]
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Removed lines', start+1, '-', end, '(', end-start, 'lines)')
print('Total lines', len(lines), '->', len(new_lines))
