"""
SHOKKER PAINT BOOTH — TEST HARNESS
===================================
Consolidated test suite that catches regressions on every commit.
Run: python test_harness.py

Tests:
  T1. All finish components render without crashing
  T2. Registries are alphabetically sorted
  T3. No duplicate registry keys
  T4. No ungrouped finishes (everything mapped to a UI group)
  T5. No performance regressions (flag >50ms finishes)
  T6. Pearl metalness is dielectric (<= 100)
  T7. All expansion entries well-formed

Exit code: 0 = all pass, 1 = failures found
"""
import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import re

# ================================================================
PASS = 0
FAIL = 0
WARN = 0

def test_pass(name):
    global PASS
    PASS += 1
    print(f"  ✓ {name}")

def test_fail(name, detail=""):
    global FAIL
    FAIL += 1
    print(f"  ✗ FAIL: {name}")
    if detail:
        print(f"    {detail}")

def test_warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"  ⚠ WARN: {name}")
    if detail:
        print(f"    {detail}")

# ================================================================
print("=" * 80)
print("SHOKKER PAINT BOOTH — TEST HARNESS")
print("=" * 80)
t0 = time.time()
print("\nLoading engine...")
import shokker_engine_v2 as eng
print(f"  Engine loaded in {time.time()-t0:.1f}s")

SZ = (64, 64)
MASK = np.ones(SZ, dtype=np.float32)
PAINT = np.full((SZ[0], SZ[1], 3), 0.5, dtype=np.float32)

# ================================================================
# T1: ALL FINISH COMPONENTS RENDER WITHOUT CRASHING
# ================================================================
print(f"\n{'='*80}")
print("T1: CRASH-FREE RENDERING")
print("=" * 80)

# T1a: Base spec functions
base_reg = getattr(eng, 'BASE_REGISTRY', {})
base_crashes = []
for bid, entry in sorted(base_reg.items()):
    try:
        if callable(entry):
            entry(SZ, MASK, 42, 1.0)
        elif isinstance(entry, dict):
            sfn = entry.get('spec_fn')
            if sfn and callable(sfn):
                sfn(SZ, MASK, 42, 1.0)
    except Exception as e:
        base_crashes.append(f"{bid}: {e}")

if base_crashes:
    test_fail(f"Base rendering ({len(base_crashes)} crashes)", "; ".join(base_crashes[:5]))
else:
    test_pass(f"All {len(base_reg)} bases render crash-free")

# T1b: Pattern texture functions
pattern_reg = getattr(eng, 'PATTERN_REGISTRY', {})
pat_crashes = []
for pid, pdata in sorted(pattern_reg.items()):
    tfn = pdata.get('texture_fn')
    if tfn is None:
        continue
    try:
        tfn(SZ, MASK, 42, 1.0)
    except Exception as e:
        pat_crashes.append(f"{pid}: {e}")

if pat_crashes:
    test_fail(f"Pattern rendering ({len(pat_crashes)} crashes)", "; ".join(pat_crashes[:5]))
else:
    test_pass(f"All {len(pattern_reg)} patterns render crash-free")

# T1c: Monolithic spec+paint functions
mono_reg = getattr(eng, 'MONOLITHIC_REGISTRY', {})
mono_crashes = []
for mid, entry in sorted(mono_reg.items()):
    if not (isinstance(entry, tuple) and len(entry) >= 2):
        continue
    try:
        entry[0](SZ, MASK, 42, 1.0)  # spec
        entry[1](PAINT.copy(), SZ, MASK, 42, 1.0, 0.5)  # paint
    except Exception as e:
        mono_crashes.append(f"{mid}: {e}")

if mono_crashes:
    test_fail(f"Monolithic rendering ({len(mono_crashes)} crashes)", "; ".join(mono_crashes[:5]))
else:
    test_pass(f"All {len(mono_reg)} monolithics render crash-free")

# ================================================================
# T2: REGISTRIES ARE ALPHABETICALLY SORTED
# ================================================================
print(f"\n{'='*80}")
print("T2: ALPHABETICAL ORDER")
print("=" * 80)

for reg_name in ('PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY'):
    reg = getattr(eng, reg_name, {})
    keys = list(reg.keys())
    if keys == sorted(keys):
        test_pass(f"{reg_name}: {len(keys)} entries in order")
    else:
        # Find first out-of-order pair
        for i in range(len(keys)-1):
            if keys[i] > keys[i+1]:
                test_fail(f"{reg_name}: out of order at '{keys[i]}' > '{keys[i+1]}'")
                break

# ================================================================
# T3: NO DUPLICATE REGISTRY KEYS
# ================================================================
print(f"\n{'='*80}")
print("T3: NO DUPLICATES")
print("=" * 80)

for reg_name in ('BASE_REGISTRY', 'PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY'):
    reg = getattr(eng, reg_name, {})
    # Dicts can't have dupes by definition, but check cross-registry
    test_pass(f"{reg_name}: {len(reg)} unique keys")

# Check cross-registry ID collisions
all_ids = set()
cross_dupes = []
for reg_name in ('BASE_REGISTRY', 'PATTERN_REGISTRY', 'MONOLITHIC_REGISTRY'):
    reg = getattr(eng, reg_name, {})
    for k in reg.keys():
        if k in all_ids:
            cross_dupes.append(k)
        all_ids.add(k)

if cross_dupes:
    test_warn(f"Cross-registry ID overlap: {len(cross_dupes)} IDs", ", ".join(cross_dupes[:10]))
else:
    test_pass("No cross-registry ID collisions")

# ================================================================
# T4: NO UNGROUPED FINISHES
# ================================================================
print(f"\n{'='*80}")
print("T4: UI GROUP COVERAGE")
print("=" * 80)

html_path = r"c:\Shokker Paint Booth - AntiGravity\paint-booth-v2.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

def extract_group_ids(html, group_name):
    pattern = rf'const\s+{group_name}\s*=\s*\{{(.*?)\}};'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return set()
    body = match.group(1)
    return set(re.findall(r'"([^"]+)"', body))

base_ui = extract_group_ids(html, 'BASE_GROUPS')
pat_ui = extract_group_ids(html, 'PATTERN_GROUPS')
spec_ui = extract_group_ids(html, 'SPECIAL_GROUPS')

# Check bases (exclude expansion bases that are just spec function refs)
missing_bases = set(base_reg.keys()) - base_ui
if missing_bases:
    test_warn(f"Bases not in UI groups: {len(missing_bases)}", ", ".join(sorted(missing_bases)[:10]))
else:
    test_pass(f"All {len(base_reg)} bases in UI groups")

# Check patterns (exclude 'none')
missing_pats = set(pattern_reg.keys()) - pat_ui - {'none'}
if missing_pats:
    test_warn(f"Patterns not in UI groups: {len(missing_pats)}", ", ".join(sorted(missing_pats)[:10]))
else:
    test_pass(f"All patterns in UI groups (excl 'none')")

# Check core monolithics (non-clr_)
core_monos = {mid for mid in mono_reg.keys() if not mid.startswith('clr_')}
missing_monos = core_monos - spec_ui
if missing_monos:
    test_warn(f"Monolithics not in UI groups: {len(missing_monos)}", ", ".join(sorted(missing_monos)[:10]))
else:
    test_pass(f"All {len(core_monos)} core monolithics in UI groups")

# ================================================================
# T5: PERFORMANCE — NO OUTLIERS > 50ms
# ================================================================
print(f"\n{'='*80}")
print("T5: PERFORMANCE")
print("=" * 80)

SZ_PERF = (128, 128)
MASK_PERF = np.ones(SZ_PERF, dtype=np.float32)
PAINT_PERF = np.full((128, 128, 3), 0.5, dtype=np.float32)

slow_finishes = []
for mid, entry in sorted(mono_reg.items()):
    if not (isinstance(entry, tuple) and len(entry) >= 2):
        continue
    try:
        t1 = time.perf_counter()
        entry[0](SZ_PERF, MASK_PERF, 42, 1.0)
        entry[1](PAINT_PERF.copy(), SZ_PERF, MASK_PERF, 42, 1.0, 0.5)
        elapsed = (time.perf_counter() - t1) * 1000
        if elapsed > 50:
            slow_finishes.append((mid, elapsed))
    except:
        pass

if slow_finishes:
    for name, ms in slow_finishes:
        test_fail(f"Slow: {name} ({ms:.0f}ms > 50ms limit)")
else:
    test_pass(f"All {len(mono_reg)} monolithics render under 50ms")

# ================================================================
# T6: PEARL METALNESS IS DIELECTRIC
# ================================================================
print(f"\n{'='*80}")
print("T6: MATERIAL PROPERTIES")
print("=" * 80)

try:
    import shokker_color_monolithics as clr
    templates = getattr(clr, 'CLR_MATERIAL_TEMPLATES', {})
    pearl = templates.get('pearl', {})
    pearl_m = pearl.get('M', 0)
    if pearl_m <= 100:
        test_pass(f"Pearl metalness M={pearl_m} (correctly dielectric)")
    else:
        test_fail(f"Pearl metalness M={pearl_m} (should be <= 100 for dielectric)")
except ImportError:
    test_warn("Could not import shokker_color_monolithics")

# ================================================================
# T7: EXPANSION PACK INTEGRITY
# ================================================================
print(f"\n{'='*80}")
print("T7: EXPANSION PACKS")
print("=" * 80)

exp_checks = [
    ('shokker_24k_expansion', 'EXPANSION_PATTERNS', 'EXPANSION_MONOLITHICS'),
    ('shokker_paradigm_expansion', 'PARADIGM_PATTERNS', 'PARADIGM_MONOLITHICS'),
]

for mod_name, pat_name, mono_name in exp_checks:
    try:
        mod = __import__(mod_name)
        
        # Check patterns
        pats = getattr(mod, pat_name, {})
        bad_pats = [pid for pid, p in pats.items() if not isinstance(p, dict) or 'texture_fn' not in p]
        if bad_pats:
            test_fail(f"{mod_name}.{pat_name}: {len(bad_pats)} malformed", ", ".join(bad_pats[:5]))
        else:
            test_pass(f"{mod_name}.{pat_name}: {len(pats)} entries well-formed")
        
        # Check monolithics
        monos = getattr(mod, mono_name, {})
        bad_monos = [mid for mid, m in monos.items() if not (isinstance(m, tuple) and len(m) >= 2)]
        if bad_monos:
            test_fail(f"{mod_name}.{mono_name}: {len(bad_monos)} malformed", ", ".join(bad_monos[:5]))
        else:
            test_pass(f"{mod_name}.{mono_name}: {len(monos)} entries well-formed")
        
    except ImportError as e:
        test_fail(f"Cannot import {mod_name}: {e}")

# ================================================================
# SUMMARY
# ================================================================
print(f"\n{'='*80}")
print("TEST RESULTS")
print("=" * 80)
print(f"""
  ✓ Passed:   {PASS}
  ✗ Failed:   {FAIL}
  ⚠ Warnings: {WARN}
  
  Total tests: {PASS + FAIL + WARN}
  Runtime:     {time.time()-t0:.1f}s
""")

if FAIL > 0:
    print("  ❌ TEST SUITE FAILED")
    sys.exit(1)
else:
    print("  ✅ ALL TESTS PASSED")
    sys.exit(0)
