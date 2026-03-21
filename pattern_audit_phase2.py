"""
Phase 2: Remove orphaned pattern entries from the PATTERNS array.
Patterns not in any PATTERN_GROUPS category get removed from the array.
Also removes entries for categories that were already deleted from PATTERN_GROUPS.
"""
import re
import os
import shutil
import json

V5 = os.path.dirname(os.path.abspath(__file__))
JS_FILE = os.path.join(V5, 'paint-booth-0-finish-data.js')
JS_COPY = os.path.join(V5, 'electron-app', 'server', 'paint-booth-0-finish-data.js')

with open(JS_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# ── Extract all pattern IDs currently in PATTERN_GROUPS ──
groups_match = re.search(r'const PATTERN_GROUPS\s*=\s*\{(.*?)\};', content, re.DOTALL)
if not groups_match:
    print("ERROR: Could not find PATTERN_GROUPS!")
    exit(1)

groups_text = groups_match.group(1)
valid_ids = set()
for m in re.finditer(r'"([^"]+)"\s*:\s*\[(.*?)\]', groups_text):
    cat_name = m.group(1)
    ids = re.findall(r'"([^"]+)"', m.group(2))
    valid_ids.update(ids)
    print(f"  {cat_name}: {len(ids)} patterns")

print(f"\nTotal valid pattern IDs (in groups): {len(valid_ids)}")

# ── Find the PATTERNS array and extract all entries ──
# Find the start and end of the PATTERNS array
pat_start = content.find('const PATTERNS = [')
if pat_start == -1:
    print("ERROR: Could not find PATTERNS array!")
    exit(1)

# Find matching closing bracket
bracket_count = 0
pat_end = -1
for i in range(pat_start, len(content)):
    if content[i] == '[':
        bracket_count += 1
    elif content[i] == ']':
        bracket_count -= 1
        if bracket_count == 0:
            pat_end = i + 1
            break

if pat_end == -1:
    print("ERROR: Could not find end of PATTERNS array!")
    exit(1)

patterns_text = content[pat_start:pat_end]
print(f"\nPATTERNS array: chars {pat_start}-{pat_end} ({pat_end - pat_start} chars)")

# ── Extract each { id: "xxx", ... } entry ──
# Pattern entries look like: { id: "xxx", name: "Yyy", desc: "...", swatch: "..." }
entry_pattern = re.compile(r'\{\s*id:\s*"([^"]+)"[^}]*\}')
all_entries = list(entry_pattern.finditer(patterns_text))
print(f"Found {len(all_entries)} pattern entries in PATTERNS array")

# ── Determine which to remove ──
to_remove_ids = set()
for m in all_entries:
    pid = m.group(1)
    if pid not in valid_ids:
        to_remove_ids.add(pid)

print(f"Entries to REMOVE (not in any group): {len(to_remove_ids)}")
print(f"Entries to KEEP: {len(all_entries) - len(to_remove_ids)}")

# ── Rebuild the PATTERNS array with only valid entries ──
kept_entries = []
for m in all_entries:
    pid = m.group(1)
    if pid in valid_ids:
        kept_entries.append(m.group(0))

# Rebuild with clean formatting (4 entries per line for readability)
lines = ['const PATTERNS = [']
for i in range(0, len(kept_entries), 3):
    chunk = kept_entries[i:i+3]
    line = '    ' + ',\n    '.join(chunk) + ','
    lines.append(line)
lines.append('];')
new_patterns_text = '\n'.join(lines)

# ── Replace in content ──
new_content = content[:pat_start] + new_patterns_text + content[pat_end:]

# ── Write back ──
with open(JS_FILE, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f"\nWrote {JS_FILE}")

if os.path.isfile(JS_COPY):
    shutil.copy2(JS_FILE, JS_COPY)
    print(f"Synced to {JS_COPY}")

# ── Print removed IDs for reference ──
print(f"\n{'='*60}")
print(f"REMOVED {len(to_remove_ids)} patterns:")
for pid in sorted(to_remove_ids):
    print(f"  - {pid}")
print(f"\nKEPT {len(kept_entries)} patterns")
print(f"{'='*60}")

# Write results to file
with open(os.path.join(V5, 'audit_phase2_results.txt'), 'w') as f:
    f.write(f"Removed: {len(to_remove_ids)}\nKept: {len(kept_entries)}\n\n")
    f.write("REMOVED:\n")
    for pid in sorted(to_remove_ids):
        f.write(f"  {pid}\n")
    f.write("\nKEPT:\n")
    for pid in sorted(valid_ids):
        f.write(f"  {pid}\n")
