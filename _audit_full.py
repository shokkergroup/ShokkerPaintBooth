"""
COMPREHENSIVE FINISH AUDIT — Bases, Patterns, Specials, & Expansion Packs
=========================================================================
Tests ALL ~1362 finishes across every registry:
  - spec_* functions (bases)
  - PATTERN_REGISTRY entries (patterns)
  - MONOLITHIC_REGISTRY entries (specials)
  - All expansion pack registrations (24K, Paradigm, Color Monolithics)

For each finish, checks:
  1. Does it crash?
  2. Is the output flat/invisible?
  3. Are the M/R/CC values plausible for the description?
  4. Alphabetical ordering
  5. Duplicate detection (same spec+paint combo)
"""
import sys, os, io, json, time, traceback, inspect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import numpy as np

# ================================================================
# IMPORT ENGINE + ALL EXPANSION PACKS
# ================================================================
print("Loading engine modules...")
t0 = time.time()

import shokker_engine_v2 as eng

# Find all expansion modules
expansion_modules = []
for mod_name in [
    'shokker_24k_expansion',
    'shokker_paradigm_expansion',
    'shokker_color_monolithics',
]:
    try:
        mod = __import__(mod_name)
        expansion_modules.append((mod_name, mod))
        print(f"  Loaded: {mod_name}")
    except ImportError as e:
        print(f"  MISSING: {mod_name} ({e})")

print(f"  Engine loaded in {time.time()-t0:.1f}s")

# ================================================================
# COLLECT ALL REGISTRIES
# ================================================================

# 1. Standalone spec_* functions (bases)
base_specs = {}
for name in dir(eng):
    if name.startswith('spec_') and callable(getattr(eng, name)):
        base_specs[name] = getattr(eng, name)

# Also check expansion modules for spec_ functions
for mod_name, mod in expansion_modules:
    for name in dir(mod):
        if name.startswith('spec_') and callable(getattr(mod, name)):
            if name not in base_specs:
                base_specs[name] = getattr(mod, name)

# 2. PATTERN_REGISTRY
pattern_reg = getattr(eng, 'PATTERN_REGISTRY', {})

# 3. MONOLITHIC_REGISTRY
mono_reg = getattr(eng, 'MONOLITHIC_REGISTRY', {})

# 4. Check expansion modules for additional registries
exp_registries = {}
for mod_name, mod in expansion_modules:
    for attr_name in dir(mod):
        val = getattr(mod, attr_name)
        if isinstance(val, dict) and len(val) > 5:
            # Check if it looks like a registry (has tuples or dicts with fn refs)
            sample = next(iter(val.values()), None)
            if sample is not None:
                if isinstance(sample, tuple) and len(sample) >= 2 and callable(sample[0]):
                    exp_registries[f"{mod_name}.{attr_name}"] = val
                    print(f"  Found expansion registry: {mod_name}.{attr_name} ({len(val)} entries)")
                elif isinstance(sample, dict) and any(k in sample for k in ['texture_fn', 'paint_fn', 'spec_fn']):
                    exp_registries[f"{mod_name}.{attr_name}"] = val
                    print(f"  Found expansion registry: {mod_name}.{attr_name} ({len(val)} entries)")

# ================================================================
# SUMMARY
# ================================================================
print("\n" + "=" * 80)
print("FINISH AUDIT SUMMARY")
print("=" * 80)
print(f"  Base spec functions (spec_*): {len(base_specs)}")
print(f"  PATTERN_REGISTRY entries:     {len(pattern_reg)}")
print(f"  MONOLITHIC_REGISTRY entries:  {len(mono_reg)}")
for name, reg in exp_registries.items():
    print(f"  {name}: {len(reg)} entries")
total = len(base_specs) + len(pattern_reg) + len(mono_reg) + sum(len(r) for r in exp_registries.values())
print(f"  TOTAL finish components:      {total}")
print()

# ================================================================
# TEST PARAMETERS
# ================================================================
TEST_SHAPE = (128, 128)  # Smaller for speed (1362 finishes!)
TEST_MASK = np.ones(TEST_SHAPE, dtype=np.float32)
TEST_PAINT = np.full((TEST_SHAPE[0], TEST_SHAPE[1], 3), 0.5, dtype=np.float32)  # Mid-gray paint
TEST_SEED = 42
TEST_SM = 1.0    # spec modifier
TEST_PM = 1.0    # paint modifier
TEST_BB = 0.5    # brightness boost

# ================================================================
# AUDIT 1: BASE SPEC FUNCTIONS
# ================================================================
print("=" * 80)
print("AUDIT 1: BASE SPEC FUNCTIONS (spec_*)")
print("=" * 80)

spec_results = {'ok': [], 'crash': [], 'flat': [], 'suspicious': []}

for name in sorted(base_specs.keys()):
    fn = base_specs[name]
    try:
        result = fn(TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_SM)
        if result is None:
            spec_results['crash'].append(f"{name}: returned None")
            continue

        if isinstance(result, np.ndarray):
            if result.ndim == 3 and result.shape[2] >= 3:
                # Analyze M, R, CC channels
                m_ch = result[:,:,0].astype(float)
                r_ch = result[:,:,1].astype(float)
                cc_ch = result[:,:,2].astype(float) if result.shape[2] > 2 else np.zeros_like(m_ch)

                m_range = m_ch.max() - m_ch.min()
                r_range = r_ch.max() - r_ch.min()
                m_mean = m_ch.mean()
                r_mean = r_ch.mean()
                cc_mean = cc_ch.mean()

                info = f"M={m_mean:.0f}({m_range:.0f}) R={r_mean:.0f}({r_range:.0f}) CC={cc_mean:.0f}"

                # Check if totally flat (no variation at all)
                total_range = m_range + r_range
                if total_range < 1:
                    spec_results['flat'].append(f"{name}: {info} — completely flat spec map")
                else:
                    # Get docstring for description matching
                    doc = (fn.__doc__ or "").split('\n')[0].strip()
                    spec_results['ok'].append({
                        'name': name,
                        'M_mean': m_mean, 'M_range': m_range,
                        'R_mean': r_mean, 'R_range': r_range,
                        'CC_mean': cc_mean,
                        'doc': doc,
                        'info': info
                    })
            else:
                spec_results['suspicious'].append(f"{name}: unexpected shape {result.shape}")
        else:
            spec_results['suspicious'].append(f"{name}: returned {type(result).__name__}, not ndarray")

    except Exception as e:
        spec_results['crash'].append(f"{name}: {type(e).__name__}: {str(e)[:100]}")

print(f"\n  OK: {len(spec_results['ok'])}")
print(f"  CRASH: {len(spec_results['crash'])}")
print(f"  FLAT: {len(spec_results['flat'])}")
print(f"  SUSPICIOUS: {len(spec_results['suspicious'])}")

if spec_results['crash']:
    print(f"\n  --- CRASHES ---")
    for c in spec_results['crash']:
        print(f"    [CRASH] {c}")

if spec_results['flat']:
    print(f"\n  --- FLAT (no variation) ---")
    for f in spec_results['flat']:
        print(f"    [FLAT] {f}")

if spec_results['suspicious']:
    print(f"\n  --- SUSPICIOUS ---")
    for s in spec_results['suspicious']:
        print(f"    [???] {s}")

# Print all OK specs with their channel values for manual review
print(f"\n  --- ALL SPECS (M/R/CC analysis) ---")
print(f"  {'Name':<35} {'M_mean':>6} {'M_rng':>6} {'R_mean':>6} {'R_rng':>6} {'CC':>4}  Description")
print(f"  {'-'*35} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*4}  {'-'*40}")
for s in sorted(spec_results['ok'], key=lambda x: x['name']):
    print(f"  {s['name']:<35} {s['M_mean']:6.0f} {s['M_range']:6.0f} {s['R_mean']:6.0f} {s['R_range']:6.0f} {s['CC_mean']:4.0f}  {s['doc'][:60]}")

# ================================================================
# AUDIT 2: PATTERN_REGISTRY
# ================================================================
print("\n" + "=" * 80)
print("AUDIT 2: PATTERN_REGISTRY")
print("=" * 80)

pat_results = {'ok': 0, 'crash': [], 'flat': [], 'no_fn': []}
texture_fn_usage = {}  # Track which texture functions are shared

for pid in sorted(pattern_reg.keys()):
    pdata = pattern_reg[pid]
    tfn = pdata.get('texture_fn')
    pfn = pdata.get('paint_fn')

    if tfn is None:
        pat_results['no_fn'].append(f"{pid}: texture_fn is None")
        continue

    # Track texture function reuse
    tfn_name = getattr(tfn, '__name__', str(tfn))
    texture_fn_usage.setdefault(tfn_name, []).append(pid)

    try:
        tex = tfn(TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_SM)
        if not isinstance(tex, dict):
            pat_results['crash'].append(f"{pid}: texture_fn returned {type(tex).__name__}, not dict")
            continue
        pv = tex.get('pattern_val')
        if pv is None:
            pat_results['crash'].append(f"{pid}: no pattern_val in result")
            continue
        pvrange = float(pv.max()) - float(pv.min())
        if pvrange < 0.01:
            pat_results['flat'].append(f"{pid}: range={pvrange:.6f} (invisible)")
        elif pvrange < 0.05:
            pat_results['flat'].append(f"{pid}: range={pvrange:.4f} (very subtle)")
        else:
            pat_results['ok'] += 1
    except Exception as e:
        pat_results['crash'].append(f"{pid}: {type(e).__name__}: {str(e)[:100]}")

print(f"\n  OK: {pat_results['ok']}")
print(f"  CRASH: {len(pat_results['crash'])}")
print(f"  FLAT: {len(pat_results['flat'])}")
print(f"  NO_FN: {len(pat_results['no_fn'])}")

if pat_results['crash']:
    print(f"\n  --- PATTERN CRASHES ---")
    for c in pat_results['crash']:
        print(f"    [CRASH] {c}")

if pat_results['flat']:
    print(f"\n  --- FLAT PATTERNS ---")
    for f in pat_results['flat']:
        print(f"    [FLAT] {f}")

# ================================================================
# AUDIT 3: MONOLITHIC_REGISTRY (Specials)
# ================================================================
print("\n" + "=" * 80)
print("AUDIT 3: MONOLITHIC_REGISTRY (Specials)")
print("=" * 80)

mono_results = {'ok': 0, 'crash': [], 'flat_spec': [], 'flat_paint': []}

for mid in sorted(mono_reg.keys()):
    entry = mono_reg[mid]
    if isinstance(entry, tuple) and len(entry) >= 2:
        spec_fn, paint_fn = entry[0], entry[1]
    else:
        mono_results['crash'].append(f"{mid}: unexpected entry format")
        continue

    # Test spec function
    try:
        spec = spec_fn(TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_SM)
        if spec is None:
            mono_results['crash'].append(f"{mid}: spec_fn returned None")
            continue
    except Exception as e:
        mono_results['crash'].append(f"{mid} spec: {type(e).__name__}: {str(e)[:100]}")
        continue

    # Test paint function
    try:
        paint_copy = TEST_PAINT.copy()
        paint_out = paint_fn(paint_copy, TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_PM, TEST_BB)
        if paint_out is None:
            mono_results['crash'].append(f"{mid}: paint_fn returned None")
            continue
        mono_results['ok'] += 1
    except Exception as e:
        mono_results['crash'].append(f"{mid} paint: {type(e).__name__}: {str(e)[:100]}")

print(f"\n  OK: {mono_results['ok']}")
print(f"  CRASH: {len(mono_results['crash'])}")

if mono_results['crash']:
    print(f"\n  --- MONOLITHIC CRASHES ---")
    for c in mono_results['crash']:
        print(f"    [CRASH] {c}")

# ================================================================
# AUDIT 4: EXPANSION PACK REGISTRIES
# ================================================================
for reg_name, reg_data in exp_registries.items():
    print(f"\n{'=' * 80}")
    print(f"AUDIT 4: EXPANSION — {reg_name}")
    print("=" * 80)

    exp_ok = 0
    exp_crash = []

    for eid in sorted(reg_data.keys()):
        entry = reg_data[eid]

        try:
            if isinstance(entry, tuple) and len(entry) >= 2:
                spec_fn, paint_fn = entry[0], entry[1]
                # Test spec
                spec = spec_fn(TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_SM)
                # Test paint
                paint_copy = TEST_PAINT.copy()
                paint_out = paint_fn(paint_copy, TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_PM, TEST_BB)
                exp_ok += 1
            elif isinstance(entry, dict):
                tfn = entry.get('texture_fn') or entry.get('spec_fn')
                pfn = entry.get('paint_fn')
                if tfn:
                    tex = tfn(TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_SM)
                if pfn:
                    paint_copy = TEST_PAINT.copy()
                    paint_out = pfn(paint_copy, TEST_SHAPE, TEST_MASK, TEST_SEED, TEST_PM, TEST_BB)
                exp_ok += 1
            else:
                exp_crash.append(f"{eid}: unknown entry format: {type(entry).__name__}")
        except Exception as e:
            exp_crash.append(f"{eid}: {type(e).__name__}: {str(e)[:120]}")

    print(f"\n  OK: {exp_ok}")
    print(f"  CRASH: {len(exp_crash)}")
    if exp_crash:
        print(f"\n  --- CRASHES ---")
        for c in exp_crash[:50]:
            print(f"    [CRASH] {c}")
        if len(exp_crash) > 50:
            print(f"    ... and {len(exp_crash) - 50} more")

# ================================================================
# AUDIT 5: ALPHABETICAL ORDER CHECK
# ================================================================
print(f"\n{'=' * 80}")
print("AUDIT 5: ALPHABETICAL ORDER")
print("=" * 80)

# Check PATTERN_REGISTRY
all_pids = list(pattern_reg.keys())
sorted_pids = sorted(all_pids)
out_of_order = [(i, actual, expected) for i, (actual, expected) in enumerate(zip(all_pids, sorted_pids)) if actual != expected]
if out_of_order:
    print(f"\n  PATTERN_REGISTRY: {len(out_of_order)} out of order (showing first 20)")
    for i, actual, expected in out_of_order[:20]:
        print(f"    [{i}] got '{actual}', expected '{expected}'")
else:
    print(f"  PATTERN_REGISTRY: All {len(all_pids)} entries in alphabetical order")

# Check MONOLITHIC_REGISTRY
all_mids = list(mono_reg.keys())
sorted_mids = sorted(all_mids)
out_of_order_m = [(i, a, e) for i, (a, e) in enumerate(zip(all_mids, sorted_mids)) if a != e]
if out_of_order_m:
    print(f"\n  MONOLITHIC_REGISTRY: {len(out_of_order_m)} out of order (showing first 20)")
    for i, actual, expected in out_of_order_m[:20]:
        print(f"    [{i}] got '{actual}', expected '{expected}'")
else:
    print(f"  MONOLITHIC_REGISTRY: All {len(all_mids)} entries in alphabetical order")

# ================================================================
# AUDIT 6: DUPLICATE DETECTION
# ================================================================
print(f"\n{'=' * 80}")
print("AUDIT 6: DUPLICATE DETECTION")
print("=" * 80)

# Find patterns that use the exact same texture_fn + paint_fn combo
combo_map = {}
for pid, pdata in pattern_reg.items():
    tfn = pdata.get('texture_fn')
    pfn = pdata.get('paint_fn')
    key = (id(tfn), id(pfn))
    combo_map.setdefault(key, []).append(pid)

dupes = {k: v for k, v in combo_map.items() if len(v) > 1}
if dupes:
    print(f"\n  {len(dupes)} duplicate texture+paint combos found:")
    for key, pids in sorted(dupes.items(), key=lambda x: -len(x[1])):
        # Get fn names
        sample = pattern_reg[pids[0]]
        tfn_name = getattr(sample['texture_fn'], '__name__', '?')
        pfn_name = getattr(sample['paint_fn'], '__name__', '?')
        print(f"\n    {tfn_name} + {pfn_name} ({len(pids)} patterns):")
        for p in sorted(pids):
            desc = pattern_reg[p].get('desc', '')
            print(f"      {p:<30s} {desc[:55]}")
else:
    print("  No exact duplicates found")

# ================================================================
# FINAL TOTALS
# ================================================================
print(f"\n{'=' * 80}")
print("FINAL TOTALS")
print("=" * 80)
total_ok = len(spec_results['ok']) + pat_results['ok'] + mono_results['ok']
total_crash = len(spec_results['crash']) + len(pat_results['crash']) + len(mono_results['crash'])
total_flat = len(spec_results['flat']) + len(pat_results['flat'])
print(f"  Total tested:  {total_ok + total_crash + total_flat}")
print(f"  Passing:       {total_ok}")
print(f"  Crashes:       {total_crash}")
print(f"  Flat/Invisible: {total_flat}")
print(f"\nAudit completed in {time.time()-t0:.1f}s")
print("=" * 80)
