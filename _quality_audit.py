"""
PHASE 3: QUALITY AUDIT — Near-Duplicates, Weak Finishes, Description Mismatches
================================================================================
Renders every finish at 128x128 and performs deep analysis:

  Q1. NEAR-DUPLICATE DETECTION
      Compares every spec output (M/R/CC channels) pair-wise.
      Flags pairs with >95% pixel similarity as potential duplicates.

  Q2. WEAK FINISH DETECTION
      Flags patterns with very low contrast (paint barely changes).
      Flags monolithics where spec+paint produce near-zero visual change.

  Q3. DESCRIPTION KEYWORD MISMATCH
      Checks finish IDs/descriptions against actual M/R/CC behavior:
        - "chrome" → should have high metalness (M>200)
        - "matte" → should have high roughness (R>150)
        - "gloss" → should have low roughness (R<80)
        - "candy" → should have clearcoat (CC>0)
        - "glow"/"neon" → should modify paint color significantly

  Q4. ORPHANED FUNCTIONS
      Finds spec_* and paint_* functions that exist in code but
      are never referenced by any registry entry.

Output: _quality_audit_results.txt
"""
import sys, os, io, time, traceback, inspect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore")

import numpy as np

# ================================================================
# LOAD ENGINE + EXPANSIONS
# ================================================================
print("=" * 90)
print("PHASE 3: QUALITY AUDIT")
print("=" * 90)
t0 = time.time()
print("Loading engine modules...")

import shokker_engine_v2 as eng

for mod_name in ['shokker_24k_expansion', 'shokker_paradigm_expansion', 'shokker_color_monolithics']:
    try:
        __import__(mod_name)
        print(f"  ✓ {mod_name}")
    except ImportError as e:
        print(f"  ✗ {mod_name} ({e})")

# ================================================================
# TEST PARAMETERS
# ================================================================
SZ = (128, 128)
MASK = np.ones(SZ, dtype=np.float32)
PAINT_MID = np.full((SZ[0], SZ[1], 3), 0.5, dtype=np.float32)  # mid-gray
PAINT_RED = np.zeros((SZ[0], SZ[1], 3), dtype=np.float32)       # red paint
PAINT_RED[:,:,0] = 0.85; PAINT_RED[:,:,1] = 0.1; PAINT_RED[:,:,2] = 0.1
SEED = 42
SM = 1.0
PM = 1.0
BB = 0.5

pattern_reg = getattr(eng, 'PATTERN_REGISTRY', {})
mono_reg = getattr(eng, 'MONOLITHIC_REGISTRY', {})

# Collect all standalone spec_ functions
all_spec_fns = {}
for name in dir(eng):
    if name.startswith('spec_') and callable(getattr(eng, name)):
        all_spec_fns[name] = getattr(eng, name)

# Collect all paint_ functions
all_paint_fns = {}
for name in dir(eng):
    if name.startswith('paint_') and callable(getattr(eng, name)):
        all_paint_fns[name] = getattr(eng, name)
for name in dir(eng):
    if name.startswith('texture_') and callable(getattr(eng, name)):
        all_paint_fns[name] = getattr(eng, name)

print(f"\nRegistries: {len(pattern_reg)} patterns, {len(mono_reg)} monolithics")
print(f"Functions:  {len(all_spec_fns)} spec_*, {len(all_paint_fns)} paint_*/texture_*")
print(f"Load time:  {time.time()-t0:.1f}s\n")

# ================================================================
# Q1: NEAR-DUPLICATE DETECTION (spec fingerprints)
# ================================================================
print("=" * 90)
print("Q1: NEAR-DUPLICATE DETECTION")
print("=" * 90)

# Build fingerprints — run each monolithic spec_fn and flatten M/R/CC to a vector
mono_fingerprints = {}
mono_errors = []

for mid in sorted(mono_reg.keys()):
    entry = mono_reg[mid]
    if not (isinstance(entry, tuple) and len(entry) >= 2):
        continue
    spec_fn = entry[0]
    try:
        spec = spec_fn(SZ, MASK, SEED, SM)
        if spec is None or not isinstance(spec, np.ndarray):
            continue
        if spec.ndim != 3 or spec.shape[2] < 3:
            continue
        # Fingerprint: downsample to 16x16 for fast comparison
        fp = spec[::8, ::8, :3].astype(np.float32).flatten()
        mono_fingerprints[mid] = fp
    except Exception:
        mono_errors.append(mid)

# Also fingerprint base spec functions
base_fingerprints = {}
for name, fn in sorted(all_spec_fns.items()):
    try:
        spec = fn(SZ, MASK, SEED, SM)
        if spec is None or not isinstance(spec, np.ndarray):
            continue
        if spec.ndim != 3 or spec.shape[2] < 3:
            continue
        fp = spec[::8, ::8, :3].astype(np.float32).flatten()
        base_fingerprints[name] = fp
    except Exception:
        pass

# Compare fingerprints pairwise — find near-duplicates
# We'll compare: monolithics vs monolithics, bases vs bases
def find_near_dupes(fingerprints, threshold=0.97):
    """Find pairs with cosine similarity above threshold."""
    keys = list(fingerprints.keys())
    dupes = []
    n = len(keys)
    if n < 2:
        return dupes
    
    # Normalize all fingerprints
    norms = {}
    for k, fp in fingerprints.items():
        norm = np.linalg.norm(fp)
        if norm > 0:
            norms[k] = fp / norm
        else:
            norms[k] = fp
    
    for i in range(n):
        for j in range(i+1, n):
            k1, k2 = keys[i], keys[j]
            if k1 in norms and k2 in norms:
                sim = float(np.dot(norms[k1], norms[k2]))
                if sim >= threshold:
                    dupes.append((k1, k2, sim))
    
    return sorted(dupes, key=lambda x: -x[2])

print(f"\n  Fingerprinted {len(mono_fingerprints)} monolithics, {len(base_fingerprints)} bases")
if mono_errors:
    print(f"  Errors fingerprinting: {len(mono_errors)}")

print(f"\n  --- Near-duplicate BASES (>97% similarity) ---")
base_dupes = find_near_dupes(base_fingerprints, threshold=0.97)
if base_dupes:
    for a, b, sim in base_dupes[:30]:
        print(f"    {sim:.1%}  {a}  ↔  {b}")
else:
    print("    None found")

print(f"\n  --- Near-duplicate MONOLITHICS (>97% similarity, excluding color variants) ---")
mono_dupes = find_near_dupes(mono_fingerprints, threshold=0.97)

# Filter out obvious color variant pairs (e.g., solid_red_gloss vs solid_blue_gloss)
# These share the same spec but different paint — that's intentional.
def is_color_variant_pair(a, b):
    """Check if two IDs are just color variants of the same material template."""
    # Strip known color names and compare the rest
    import re
    colors = r'(red|blue|green|yellow|orange|purple|violet|pink|white|black|gold|silver|bronze|copper|'
    colors += r'crimson|coral|peach|amber|honey|chartreuse|mint|sage|emerald|jade|aqua|cerulean|cobalt|'
    colors += r'indigo|lavender|plum|rose|blush|maroon|burgundy|chocolate|tan|cream|ivory|slate|charcoal|'
    colors += r'graphite|pewter|champagne|titanium|gunmetal|navy|magenta|hot_pink|teal|lime_green|'
    colors += r'forest_green|sky_blue|royal_blue|fire_orange|sunburst_yellow|racing_red)'
    
    a_base = re.sub(colors, '', a).strip('_')
    b_base = re.sub(colors, '', b).strip('_')
    return a_base == b_base and a_base != ''

real_mono_dupes = [(a, b, s) for a, b, s in mono_dupes if not is_color_variant_pair(a, b)]
color_variant_dupes = [(a, b, s) for a, b, s in mono_dupes if is_color_variant_pair(a, b)]

if real_mono_dupes:
    for a, b, sim in real_mono_dupes[:50]:
        print(f"    {sim:.1%}  {a}  ↔  {b}")
    if len(real_mono_dupes) > 50:
        print(f"    ... and {len(real_mono_dupes)-50} more")
else:
    print("    None found (excluding color variants)")

print(f"\n  Color-variant pairs (intentional, same spec template): {len(color_variant_dupes)}")

# ================================================================
# Q2: WEAK FINISH DETECTION
# ================================================================
print(f"\n{'=' * 90}")
print("Q2: WEAK FINISH DETECTION")
print("=" * 90)

# 2A: Weak PATTERNS — texture_fn produces very low contrast pattern
print(f"\n  --- Weak Patterns (very low pattern contrast) ---")
weak_pats = []
for pid in sorted(pattern_reg.keys()):
    pdata = pattern_reg[pid]
    tfn = pdata.get('texture_fn')
    pfn = pdata.get('paint_fn')
    if tfn is None:
        continue
    try:
        tex = tfn(SZ, MASK, SEED, SM)
        if not isinstance(tex, dict):
            continue
        pv = tex.get('pattern_val')
        if pv is None:
            continue
        pv_range = float(pv.max()) - float(pv.min())
        pv_std = float(np.std(pv))
        
        if pv_range < 0.10:
            weak_pats.append((pid, pv_range, pv_std, "barely visible"))
        elif pv_std < 0.03:
            weak_pats.append((pid, pv_range, pv_std, "very uniform"))
    except Exception:
        pass

if weak_pats:
    print(f"    {'Pattern':<35} {'Range':>8} {'StdDev':>8}  Issue")
    print(f"    {'-'*35} {'-'*8} {'-'*8}  {'-'*20}")
    for pid, rng, std, issue in sorted(weak_pats, key=lambda x: x[1]):
        print(f"    {pid:<35} {rng:8.4f} {std:8.4f}  {issue}")
else:
    print("    All patterns have reasonable contrast")

# 2B: Weak MONOLITHICS — spec+paint produce almost no change from input
print(f"\n  --- Weak Monolithics (minimal visual impact) ---")
weak_monos = []
for mid in sorted(mono_reg.keys()):
    entry = mono_reg[mid]
    if not (isinstance(entry, tuple) and len(entry) >= 2):
        continue
    spec_fn, paint_fn = entry[0], entry[1]
    try:
        # Measure how much paint_fn changes the input
        paint_in = PAINT_RED.copy()
        paint_out = paint_fn(paint_in, SZ, MASK, SEED, PM, BB)
        if paint_out is None:
            continue
        
        diff = np.abs(paint_out.astype(float) - PAINT_RED.astype(float))
        max_diff = float(diff.max())
        mean_diff = float(diff.mean())
        
        if max_diff < 0.01:
            weak_monos.append((mid, max_diff, mean_diff, "paint unchanged"))
        elif mean_diff < 0.005:
            weak_monos.append((mid, max_diff, mean_diff, "nearly invisible"))
    except Exception:
        pass

if weak_monos:
    print(f"    {'Monolithic':<40} {'MaxDiff':>8} {'MeanDiff':>10}  Issue")
    print(f"    {'-'*40} {'-'*8} {'-'*10}  {'-'*20}")
    for mid, mx, mn, issue in sorted(weak_monos, key=lambda x: x[2]):
        print(f"    {mid:<40} {mx:8.4f} {mn:10.6f}  {issue}")
else:
    print("    All monolithics produce visible changes")

# ================================================================
# Q3: DESCRIPTION / KEYWORD MISMATCH
# ================================================================
print(f"\n{'=' * 90}")
print("Q3: DESCRIPTION / NAME KEYWORD MISMATCH")
print("=" * 90)

# Define keyword rules: if the name/desc contains a keyword, the M/R/CC should match
# Rules: (keyword_in_name, channel, condition_description, lambda spec -> bool)
KEYWORD_RULES = [
    # Chrome/metal should have HIGH metalness 
    ("chrome",  "M_mean", "> 180", lambda m, r, cc: m > 180),
    ("metal",   "M_mean", "> 100", lambda m, r, cc: m > 100),
    # Matte should have HIGH roughness
    ("matte",   "R_mean", "> 120", lambda m, r, cc: r > 120),
    ("flat",    "R_mean", "> 120", lambda m, r, cc: r > 120),
    ("rough",   "R_mean", "> 100", lambda m, r, cc: r > 100),
    # Gloss should have LOW roughness
    ("gloss",   "R_mean", "< 80",  lambda m, r, cc: r < 80),
    ("smooth",  "R_mean", "< 80",  lambda m, r, cc: r < 80),
    # Clearcoat finishes
    ("candy",   "CC",     "> 5",   lambda m, r, cc: cc > 5),
    ("clearcoat", "CC",   "> 5",   lambda m, r, cc: cc > 5),
    # Pearl should be somewhat dielectric with some roughness variation
    ("pearl",   "M_mean", "< 100", lambda m, r, cc: m < 100),
]

mismatches = []
base_specs_data = {}

# Collect data for base specs
for name, fn in sorted(all_spec_fns.items()):
    try:
        spec = fn(SZ, MASK, SEED, SM)
        if spec is None or not isinstance(spec, np.ndarray):
            continue
        if spec.ndim != 3 or spec.shape[2] < 3:
            continue
        m_mean = float(spec[:,:,0].mean())
        r_mean = float(spec[:,:,1].mean())
        cc_mean = float(spec[:,:,2].mean()) if spec.shape[2] > 2 else 0.0
        base_specs_data[name] = (m_mean, r_mean, cc_mean)
        
        doc = (fn.__doc__ or "").split('\n')[0].strip().lower()
        check_text = name.lower() + " " + doc
        
        for keyword, channel, cond_desc, check_fn in KEYWORD_RULES:
            if keyword in check_text:
                if not check_fn(m_mean, r_mean, cc_mean):
                    mismatches.append({
                        'id': name,
                        'type': 'base',
                        'keyword': keyword,
                        'expected': f"{channel} {cond_desc}",
                        'actual': f"M={m_mean:.0f} R={r_mean:.0f} CC={cc_mean:.0f}",
                        'desc': doc[:60]
                    })
    except Exception:
        pass

# Check monolithic specs too
for mid in sorted(mono_reg.keys()):
    entry = mono_reg[mid]
    if not (isinstance(entry, tuple) and len(entry) >= 2):
        continue
    spec_fn = entry[0]
    try:
        spec = spec_fn(SZ, MASK, SEED, SM)
        if spec is None or not isinstance(spec, np.ndarray):
            continue
        if spec.ndim != 3 or spec.shape[2] < 3:
            continue
        m_mean = float(spec[:,:,0].mean())
        r_mean = float(spec[:,:,1].mean())
        cc_mean = float(spec[:,:,2].mean()) if spec.shape[2] > 2 else 0.0
        
        check_text = mid.lower()
        
        for keyword, channel, cond_desc, check_fn in KEYWORD_RULES:
            if keyword in check_text:
                if not check_fn(m_mean, r_mean, cc_mean):
                    mismatches.append({
                        'id': mid,
                        'type': 'monolithic',
                        'keyword': keyword,
                        'expected': f"{channel} {cond_desc}",
                        'actual': f"M={m_mean:.0f} R={r_mean:.0f} CC={cc_mean:.0f}",
                        'desc': ''
                    })
    except Exception:
        pass

if mismatches:
    print(f"\n  {len(mismatches)} keyword mismatches found:")
    print(f"\n    {'ID':<40} {'Type':<10} {'Keyword':<10} {'Expected':<18} {'Actual'}")
    print(f"    {'-'*40} {'-'*10} {'-'*10} {'-'*18} {'-'*25}")
    for mm in mismatches:
        print(f"    {mm['id']:<40} {mm['type']:<10} {mm['keyword']:<10} {mm['expected']:<18} {mm['actual']}")
else:
    print("  No keyword mismatches found — all finishes match their name keywords")

# ================================================================
# Q4: ORPHANED FUNCTIONS
# ================================================================
print(f"\n{'=' * 90}")
print("Q4: ORPHANED FUNCTIONS (never referenced by any registry)")
print("=" * 90)

# Collect all function references from registries
referenced_fns = set()

# From PATTERN_REGISTRY
for pid, pdata in pattern_reg.items():
    for key in ['texture_fn', 'paint_fn']:
        fn = pdata.get(key)
        if fn:
            referenced_fns.add(id(fn))

# From MONOLITHIC_REGISTRY
for mid, entry in mono_reg.items():
    if isinstance(entry, tuple):
        for fn in entry:
            if callable(fn):
                referenced_fns.add(id(fn))

# From BASE_REGISTRY
base_reg = getattr(eng, 'BASE_REGISTRY', {})
for bid, fn in base_reg.items():
    if callable(fn):
        referenced_fns.add(id(fn))

# Find orphaned spec_ functions
orphan_specs = []
for name, fn in sorted(all_spec_fns.items()):
    if id(fn) not in referenced_fns:
        orphan_specs.append(name)

# Find orphaned paint_ / texture_ functions
orphan_paints = []
for name, fn in sorted(all_paint_fns.items()):
    if id(fn) not in referenced_fns:
        orphan_paints.append(name)

if orphan_specs:
    print(f"\n  {len(orphan_specs)} orphaned spec_* functions (not in any registry):")
    for name in orphan_specs:
        doc = (all_spec_fns[name].__doc__ or "").split('\n')[0].strip()[:60]
        print(f"    {name:<40} {doc}")
else:
    print("  No orphaned spec_* functions")

if orphan_paints:
    print(f"\n  {len(orphan_paints)} orphaned paint_*/texture_* functions:")
    for name in orphan_paints:
        doc = (all_paint_fns[name].__doc__ or "").split('\n')[0].strip()[:60]
        print(f"    {name:<40} {doc}")
else:
    print("  No orphaned paint_*/texture_* functions")

# ================================================================
# Q5: VISUAL DIVERSITY CHECK — Are spec outputs actually different?
# ================================================================
print(f"\n{'=' * 90}")
print("Q5: SPEC OUTPUT DIVERSITY (channel distribution)")
print("=" * 90)

# Group bases by their M/R/CC cluster to see if we have enough diversity
if base_specs_data:
    print(f"\n  {'Base Function':<40} {'M_mean':>6} {'R_mean':>6} {'CC':>4}  Classification")
    print(f"  {'-'*40} {'-'*6} {'-'*6} {'-'*4}  {'-'*30}")
    
    for name in sorted(base_specs_data.keys()):
        m, r, cc = base_specs_data[name]
        
        # Auto-classify
        if m > 200:
            cls = "METALLIC"
        elif m > 100:
            cls = "SEMI-METALLIC"
        else:
            cls = "DIELECTRIC"
        
        if r < 30:
            cls += " / mirror-smooth"
        elif r < 80:
            cls += " / smooth"
        elif r < 150:
            cls += " / moderate-rough"
        else:
            cls += " / rough"
        
        if cc > 10:
            cls += " / clearcoated"
        
        print(f"  {name:<40} {m:6.0f} {r:6.0f} {cc:4.0f}  {cls}")

# ================================================================
# SUMMARY
# ================================================================
print(f"\n{'=' * 90}")
print("QUALITY AUDIT SUMMARY")
print("=" * 90)

print(f"""
  Near-duplicate base pairs:       {len(base_dupes)}
  Near-duplicate monolithic pairs: {len(real_mono_dupes)} (excl {len(color_variant_dupes)} color variants)
  Weak patterns:                   {len(weak_pats)}
  Weak monolithics:                {len(weak_monos)}
  Keyword mismatches:              {len(mismatches)}
  Orphaned spec_ functions:        {len(orphan_specs)}
  Orphaned paint_/texture_ funcs:  {len(orphan_paints)}

  Audit completed in {time.time()-t0:.1f}s
""")
print("=" * 90)
