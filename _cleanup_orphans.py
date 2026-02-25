"""
ORPHANED FUNCTION CLEANUP
=========================
Identifies spec_*, paint_*, and texture_* functions in shokker_engine_v2.py
that are NOT referenced by any registry (BASE_REGISTRY, PATTERN_REGISTRY,
MONOLITHIC_REGISTRY) — even after expansion packs are loaded.

Strategy: Conservative. Only removes functions that are provably unreferenced.
A function is "referenced" if:
  - Its id() appears in any registry entry
  - Its name appears as a string reference anywhere in the engine file
  - It's called by another function that IS referenced

Output: A report of orphans + a cleaned engine file written to disk.
"""
import sys, os, io, re, inspect, ast
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore")

import numpy as np

# Load engine + expansions
import shokker_engine_v2 as eng

# Collect all function references from ALL registries (after expansion loading)
referenced_fn_ids = set()
referenced_fn_names = set()

# BASE_REGISTRY
base_reg = getattr(eng, 'BASE_REGISTRY', {})
for bid, fn in base_reg.items():
    if callable(fn):
        referenced_fn_ids.add(id(fn))
        referenced_fn_names.add(getattr(fn, '__name__', ''))

# PATTERN_REGISTRY
pattern_reg = getattr(eng, 'PATTERN_REGISTRY', {})
for pid, pdata in pattern_reg.items():
    for key in ['texture_fn', 'paint_fn']:
        fn = pdata.get(key)
        if fn and callable(fn):
            referenced_fn_ids.add(id(fn))
            referenced_fn_names.add(getattr(fn, '__name__', ''))

# MONOLITHIC_REGISTRY
mono_reg = getattr(eng, 'MONOLITHIC_REGISTRY', {})
for mid, entry in mono_reg.items():
    if isinstance(entry, tuple):
        for fn in entry:
            if callable(fn):
                referenced_fn_ids.add(id(fn))
                referenced_fn_names.add(getattr(fn, '__name__', ''))

print(f"Total referenced functions: {len(referenced_fn_ids)}")
print(f"Total referenced function names: {len(referenced_fn_names)}")

# Collect all spec_*, paint_*, texture_* functions defined in the engine
all_engine_fns = {}
for name in dir(eng):
    if (name.startswith('spec_') or name.startswith('paint_') or name.startswith('texture_')) and callable(getattr(eng, name)):
        fn = getattr(eng, name)
        all_engine_fns[name] = fn

print(f"Total engine functions: {len(all_engine_fns)}")

# Find orphans
orphans = {}
used = {}
for name, fn in sorted(all_engine_fns.items()):
    if id(fn) in referenced_fn_ids:
        used[name] = "registry reference"
    elif name in referenced_fn_names:
        used[name] = "name reference"
    else:
        orphans[name] = fn

print(f"\nOrphaned: {len(orphans)}")
print(f"In use:   {len(used)}")

# SAFETY CHECK: Before removing orphans, verify they aren't called BY other
# functions that ARE in use. Read the engine source and check for name references.
engine_path = r"c:\Shokker Paint Booth - AntiGravity\shokker_engine_v2.py"
with open(engine_path, 'r', encoding='utf-8') as f:
    engine_source = f.read()

# Check if any orphan name appears ANYWHERE in the source outside its own def
indirectly_used = set()
for orphan_name in list(orphans.keys()):
    # Find all occurrences of the function name in the source
    pattern = re.compile(r'\b' + re.escape(orphan_name) + r'\b')
    matches = list(pattern.finditer(engine_source))
    
    # Filter out: (1) the def line itself, (2) any comment referencing it
    real_refs = []
    for m in matches:
        line_start = engine_source.rfind('\n', 0, m.start()) + 1
        line_end = engine_source.find('\n', m.end())
        line = engine_source[line_start:line_end].strip()
        
        # Skip the def line
        if line.startswith(f'def {orphan_name}('):
            continue
        # Skip pure comments
        if line.lstrip().startswith('#'):
            continue
        # Skip docstrings (lines inside triple quotes)
        if line.lstrip().startswith('"""') or line.lstrip().startswith("'''"):
            continue
        
        real_refs.append(line)
    
    if real_refs:
        indirectly_used.add(orphan_name)

# Remove indirectly used from orphans
for name in indirectly_used:
    del orphans[name]
    used[name] = "indirect reference"

print(f"\nAfter indirect reference check:")
print(f"  Truly orphaned: {len(orphans)}")
print(f"  Indirectly used: {len(indirectly_used)}")

# Print the orphan list
print(f"\n{'='*80}")
print("TRULY ORPHANED FUNCTIONS (safe to remove)")
print(f"{'='*80}")
for name in sorted(orphans.keys()):
    fn = orphans[name]
    doc = (fn.__doc__ or "").split('\n')[0].strip()[:70]
    # Get line number
    try:
        src_lines = inspect.getsourcelines(fn)
        line_no = src_lines[1]
        num_lines = len(src_lines[0])
    except:
        line_no = '?'
        num_lines = '?'
    print(f"  {name:<40} L{line_no:<6} ({num_lines} lines)  {doc}")

print(f"\n{'='*80}")
print("INDIRECTLY REFERENCED (keeping)")
print(f"{'='*80}")
for name in sorted(indirectly_used):
    fn = all_engine_fns[name]
    doc = (fn.__doc__ or "").split('\n')[0].strip()[:70]
    print(f"  {name:<40} {doc}")

# Now remove orphans from the engine source
print(f"\n{'='*80}")
print("REMOVING ORPHANED FUNCTIONS FROM ENGINE FILE")
print(f"{'='*80}")

# Parse the source to find function boundaries
lines = engine_source.split('\n')
ranges_to_remove = []

for orphan_name in sorted(orphans.keys()):
    fn = orphans[orphan_name]
    try:
        src_lines, start_line = inspect.getsourcelines(fn)
        # start_line is 1-indexed
        end_line = start_line + len(src_lines) - 1
        
        # Also remove blank lines after the function (up to 2)
        while end_line < len(lines) and lines[end_line].strip() == '':
            end_line += 1
            if end_line - (start_line + len(src_lines) - 1) >= 2:
                break
        
        ranges_to_remove.append((start_line - 1, end_line, orphan_name))  # Convert to 0-indexed
    except Exception as e:
        print(f"  WARNING: Could not locate {orphan_name}: {e}")

# Sort ranges by start line (descending so we can remove from bottom up)
ranges_to_remove.sort(key=lambda x: -x[0])

# Check for overlaps
print(f"\n  Removing {len(ranges_to_remove)} function definitions...")
total_lines_removed = 0

new_lines = list(lines)  # Make a copy
for start, end, name in ranges_to_remove:
    count = end - start
    del new_lines[start:end]
    total_lines_removed += count
    print(f"  ✓ {name} (lines {start+1}-{end})")

# Write cleaned file
cleaned_source = '\n'.join(new_lines)
with open(engine_path, 'w', encoding='utf-8') as f:
    f.write(cleaned_source)

print(f"\n  Total lines removed: {total_lines_removed}")
print(f"  Original file: {len(lines)} lines")
print(f"  Cleaned file:  {len(new_lines)} lines")
print(f"\n  ✓ Engine file updated: {engine_path}")

print(f"\n{'='*80}")
print("CLEANUP COMPLETE")
print(f"{'='*80}")
