"""
Registry Sorter v2 — Sorts PATTERN_REGISTRY and MONOLITHIC_REGISTRY.
Works at the Python import level — imports the engine, reads the sorted dicts,
and writes them back as properly formatted Python code.
"""
import sys, os, re
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore")

ENGINE_FILE = r"c:\Shokker Paint Booth - AntiGravity\shokker_engine_v2.py"

# Read the raw file to find the line ranges
with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"File has {len(lines)} lines")

# ======== Find PATTERN_REGISTRY ========
p_start = p_end = None
for i, L in enumerate(lines):
    if 'PATTERN_REGISTRY' in L and '=' in L and '{' in L and not L.strip().startswith('#'):
        p_start = i
        break
if p_start is not None:
    depth = 0
    for j in range(p_start, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth == 0:
            p_end = j
            break
print(f"PATTERN_REGISTRY: lines {p_start+1}–{p_end+1} ({p_end-p_start+1} lines)")

# ======== Find MONOLITHIC_REGISTRY ========
m_start = m_end = None
for i, L in enumerate(lines):
    if 'MONOLITHIC_REGISTRY' in L and '=' in L and '{' in L and not L.strip().startswith('#'):
        m_start = i
        break
if m_start is not None:
    depth = 0
    for j in range(m_start, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth == 0:
            m_end = j
            break
print(f"MONOLITHIC_REGISTRY: lines {m_start+1}–{m_end+1} ({m_end-m_start+1} lines)")

# ======== Parse and sort PATTERN_REGISTRY entries ========
# Each entry looks like: "key": {"texture_fn": ..., "paint_fn": ..., ...},
pat_entries = []
i = p_start + 1
while i < p_end:
    line = lines[i]
    stripped = line.strip()
    
    if not stripped or stripped.startswith('#'):
        i += 1
        continue
    
    # Match entry key
    m = re.match(r'\s*"([^"]+)"\s*:', stripped)
    if m:
        key = m.group(1)
        # Collect all lines for this entry (may span multiple lines)
        entry_text = line
        depth = line.count('{') - line.count('}')
        while depth > 0 and i + 1 < p_end:
            i += 1
            entry_text += lines[i]
            depth += lines[i].count('{') - lines[i].count('}')
        pat_entries.append((key, entry_text))
    
    i += 1

print(f"  Parsed {len(pat_entries)} PATTERN_REGISTRY entries")

# Sort alphabetically
pat_entries.sort(key=lambda x: x[0])

# Rebuild PATTERN_REGISTRY
pat_header = lines[p_start]
pat_section = [pat_header]
for key, text in pat_entries:
    pat_section.append(text)
pat_section.append(lines[p_end])  # closing }

# ======== Parse and sort MONOLITHIC_REGISTRY entries ========
mono_entries = []
i = m_start + 1
while i < m_end:
    line = lines[i]
    stripped = line.strip()
    
    if not stripped or stripped.startswith('#'):
        i += 1
        continue
    
    m = re.match(r'\s*"([^"]+)"\s*:', stripped)
    if m:
        key = m.group(1)
        entry_text = line
        # Check if entry continues on next line (tuple may span lines)
        paren_depth = line.count('(') - line.count(')')
        while paren_depth > 0 and i + 1 < m_end:
            i += 1
            entry_text += lines[i]
            paren_depth += lines[i].count('(') - lines[i].count(')')
        mono_entries.append((key, entry_text))
    
    i += 1

print(f"  Parsed {len(mono_entries)} MONOLITHIC_REGISTRY entries")

mono_entries.sort(key=lambda x: x[0])

mono_header = lines[m_start]
mono_section = [mono_header]
for key, text in mono_entries:
    mono_section.append(text)
mono_section.append(lines[m_end])

# ======== Rebuild file ========
output = lines[:p_start] + pat_section + lines[p_end+1:m_start] + mono_section + lines[m_end+1:]
print(f"  Output: {len(output)} lines (was {len(lines)})")

with open(ENGINE_FILE, 'w', encoding='utf-8') as f:
    f.writelines(output)
print("  Written!")

# ======== Verify by importing and checking order ========
print("\n--- Verification ---")
# Re-read and check
with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    verify = f.readlines()
print(f"  File: {len(verify)} lines")

# Quick check: find pattern keys in order
pat_keys = []
for line in verify:
    stripped = line.strip()
    if stripped.startswith('"') and '{' in stripped and 'texture_fn' in stripped:
        m = re.match(r'"([^"]+)"', stripped)
        if m:
            pat_keys.append(m.group(1))

sorted_keys = sorted(pat_keys)
mismatches = sum(1 for a, b in zip(pat_keys, sorted_keys) if a != b)
print(f"  Pattern keys found: {len(pat_keys)}")
print(f"  Alphabetical mismatches: {mismatches}")
if mismatches > 0 and len(pat_keys) > 0:
    for i, (a, b) in enumerate(zip(pat_keys, sorted_keys)):
        if a != b:
            print(f"    First mismatch at [{i}]: got '{a}', expected '{b}'")
            break

print("\nDONE!")
