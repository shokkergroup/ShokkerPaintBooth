"""
Registry Sorter — Alphabetically sorts PATTERN_REGISTRY and MONOLITHIC_REGISTRY
in shokker_engine_v2.py, preserving section comments and structure.
"""
import re, sys

ENGINE_FILE = r"c:\Shokker Paint Booth - AntiGravity\shokker_engine_v2.py"

def find_registry_bounds(lines, registry_name):
    """Find start/end line indices of a dict-style registry."""
    start = None
    for i, L in enumerate(lines):
        if registry_name in L and '=' in L and '{' in L:
            start = i
            break
    if start is None:
        return None, None
    
    depth = 0
    end = None
    for j in range(start, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth == 0:
            end = j
            break
    return start, end

def parse_pattern_registry_entries(lines, start, end):
    """Parse individual entries from PATTERN_REGISTRY (dict of dicts).
    Each entry is like: "key": {...},
    Also captures section comments (lines starting with #)
    """
    entries = []
    comments_before = []
    
    # Skip first line (the registry name = {)
    i = start + 1
    while i <= end:
        line = lines[i]
        stripped = line.strip()
        
        # Skip the closing brace
        if stripped == '}' or stripped == '}\n' or stripped.rstrip('\r\n') == '}':
            break
        
        # Blank line
        if not stripped:
            i += 1
            continue
        
        # Comment line — associate with next entry
        if stripped.startswith('#'):
            comments_before.append(lines[i])
            i += 1
            continue
        
        # Entry line — extract key
        m = re.match(r'\s*"([^"]+)"', stripped)
        if m:
            key = m.group(1)
            entries.append({
                'key': key,
                'line': lines[i],
                'comments': list(comments_before)
            })
            comments_before = []
        else:
            # Unknown line, keep as-is
            entries.append({
                'key': f'_unknown_{i}',
                'line': lines[i],
                'comments': list(comments_before)
            })
            comments_before = []
        
        i += 1
    
    return entries, comments_before  # remaining comments (if any before closing brace)

def parse_monolithic_registry_entries(lines, start, end):
    """Parse MONOLITHIC_REGISTRY entries (tuples).
    Each entry is like: "key": (spec_fn, paint_fn),
    May span multiple lines.
    """
    entries = []
    comments_before = []
    
    i = start + 1
    while i <= end:
        line = lines[i]
        stripped = line.strip()
        
        if stripped == '}' or stripped.rstrip('\r\n') == '}':
            break
        
        if not stripped:
            i += 1
            continue
        
        if stripped.startswith('#'):
            comments_before.append(lines[i])
            i += 1
            continue
        
        m = re.match(r'\s*"([^"]+)"', stripped)
        if m:
            key = m.group(1)
            # Check if entry spans multiple lines
            entry_lines = [lines[i]]
            # Count parens to see if tuple is complete
            depth = stripped.count('(') - stripped.count(')')
            while depth > 0 and i + 1 <= end:
                i += 1
                entry_lines.append(lines[i])
                depth += lines[i].count('(') - lines[i].count(')')
            
            entries.append({
                'key': key,
                'lines': entry_lines,
                'comments': list(comments_before)
            })
            comments_before = []
        else:
            entries.append({
                'key': f'_unknown_{i}',
                'lines': [lines[i]],
                'comments': list(comments_before)
            })
            comments_before = []
        
        i += 1
    
    return entries, comments_before

def sort_and_rebuild_pattern_registry(lines, start, end):
    """Sort PATTERN_REGISTRY entries alphabetically, preserving header."""
    entries, trailing = parse_pattern_registry_entries(lines, start, end)
    
    # Sort entries by key
    sorted_entries = sorted(entries, key=lambda e: e['key'])
    
    # Rebuild the section
    new_lines = [lines[start]]  # Keep the "PATTERN_REGISTRY = {" line
    
    for entry in sorted_entries:
        # Drop old section comments - they don't make sense alphabetically
        # Just write the entry
        new_lines.append(entry['line'])
    
    # Add trailing comments + closing brace
    for c in trailing:
        new_lines.append(c)
    new_lines.append(lines[end])  # closing }
    
    return new_lines

def sort_and_rebuild_monolithic_registry(lines, start, end):
    """Sort MONOLITHIC_REGISTRY entries alphabetically, preserving header."""
    entries, trailing = parse_monolithic_registry_entries(lines, start, end)
    
    sorted_entries = sorted(entries, key=lambda e: e['key'])
    
    new_lines = [lines[start]]  # Keep the header line
    
    for entry in sorted_entries:
        for el in entry['lines']:
            new_lines.append(el)
    
    for c in trailing:
        new_lines.append(c)
    new_lines.append(lines[end])
    
    return new_lines


# === MAIN ===
print(f"Reading {ENGINE_FILE}...")
with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"  {len(lines)} lines")

# Find PATTERN_REGISTRY
p_start, p_end = find_registry_bounds(lines, 'PATTERN_REGISTRY')
print(f"  PATTERN_REGISTRY: lines {p_start+1}-{p_end+1} ({p_end-p_start+1} lines)")

# Find MONOLITHIC_REGISTRY
m_start, m_end = find_registry_bounds(lines, 'MONOLITHIC_REGISTRY')
print(f"  MONOLITHIC_REGISTRY: lines {m_start+1}-{m_end+1} ({m_end-m_start+1} lines)")

# Sort PATTERN_REGISTRY
new_pat = sort_and_rebuild_pattern_registry(lines, p_start, p_end)
print(f"  Sorted PATTERN_REGISTRY: {len(new_pat)} lines (was {p_end-p_start+1})")

# Sort MONOLITHIC_REGISTRY  
new_mono = sort_and_rebuild_monolithic_registry(lines, m_start, m_end)
print(f"  Sorted MONOLITHIC_REGISTRY: {len(new_mono)} lines (was {m_end-m_start+1})")

# Rebuild the file
output = lines[:p_start] + new_pat + lines[p_end+1:m_start] + new_mono + lines[m_end+1:]
print(f"  Output: {len(output)} lines (was {len(lines)})")

# Write to file
with open(ENGINE_FILE, 'w', encoding='utf-8') as f:
    f.writelines(output)
print("  DONE — file written!")

# Verify by re-reading
with open(ENGINE_FILE, 'r', encoding='utf-8') as f:
    verify_lines = f.readlines()
print(f"  Verification: {len(verify_lines)} lines")
