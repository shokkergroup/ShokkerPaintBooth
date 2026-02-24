"""Pattern Audit Script v2 — ASCII-safe output."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"c:\Shokker Paint Booth - AntiGravity")
os.chdir(r"c:\Shokker Paint Booth - AntiGravity")

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

from shokker_engine_v2 import PATTERN_REGISTRY
import numpy as np

print(f"PATTERN AUDIT - {len(PATTERN_REGISTRY)} total patterns")
print("=" * 70)

# Test each texture function
shape = (256, 256)  # Smaller for speed
mask = np.ones(shape, dtype=np.float32)
errors = []
flat_patterns = []
ok_count = 0

for pid, pdata in sorted(PATTERN_REGISTRY.items()):
    tfn = pdata.get("texture_fn")
    if tfn is None:
        errors.append(f"{pid}: texture_fn is None")
        continue
    try:
        tex = tfn(shape, mask, 42, 1.0)
        if not isinstance(tex, dict):
            errors.append(f"{pid}: returned {type(tex).__name__}, not dict")
            continue
        pv = tex.get("pattern_val")
        if pv is None:
            errors.append(f"{pid}: no pattern_val")
            continue
        pvrange = float(pv.max()) - float(pv.min())
        if pvrange < 0.01:
            flat_patterns.append(f"{pid}: range={pvrange:.6f} (effectively invisible)")
        elif pvrange < 0.05:
            flat_patterns.append(f"{pid}: range={pvrange:.4f} (very subtle)")
        else:
            ok_count += 1
    except Exception as e:
        errors.append(f"{pid}: CRASH - {type(e).__name__}: {e}")

print(f"\nRESULTS: {ok_count} OK, {len(errors)} errors, {len(flat_patterns)} flat/subtle")

if errors:
    print(f"\n--- ERRORS ({len(errors)}) ---")
    for e in errors:
        print(f"  [ERR] {e}")

if flat_patterns:
    print(f"\n--- FLAT/SUBTLE PATTERNS ({len(flat_patterns)}) ---")
    for f in flat_patterns:
        print(f"  [FLAT] {f}")

# Show texture function reuse counts
print(f"\n--- TEXTURE FUNCTION REUSE ---")
tex_fn_count = {}
tex_fn_patterns = {}
for pid, pdata in sorted(PATTERN_REGISTRY.items()):
    tfn = pdata.get("texture_fn")
    if tfn is None:
        continue
    # Get the REAL name (unwrap wrapped_ functions)
    tfn_name = tfn.__name__
    # Chase __wrapped__ attribute for expansion wrappers
    real_fn = tfn
    for _ in range(5):
        if hasattr(real_fn, '__wrapped__'):
            real_fn = real_fn.__wrapped__
        else:
            break
    real_name = real_fn.__name__
    tex_fn_count[real_name] = tex_fn_count.get(real_name, 0) + 1
    tex_fn_patterns.setdefault(real_name, []).append(pid)

for name, count in sorted(tex_fn_count.items(), key=lambda x: -x[1]):
    if count > 1:
        pids = tex_fn_patterns[name]
        print(f"\n  {name} ({count} patterns):")
        for p in sorted(pids):
            desc = PATTERN_REGISTRY[p].get("desc", "")
            print(f"    {p:30s}  {desc}")

# Check alphabetical order in the PATTERN_REGISTRY
print(f"\n--- ALPHABETICAL ORDER CHECK ---")
all_ids = list(PATTERN_REGISTRY.keys())
# The registry has sections - check if v7 aliases are alphabetical
alias_start = None
for i, pid in enumerate(all_ids):
    if pid == "aero_flow":  # First v7 alias
        alias_start = i
        break
if alias_start:
    aliases = all_ids[alias_start:]
    sorted_aliases = sorted(aliases)
    out_of_order = []
    for i, (actual, expected) in enumerate(zip(aliases, sorted_aliases)):
        if actual != expected:
            out_of_order.append(f"  Position {i}: got '{actual}', expected '{expected}'")
    if out_of_order:
        print(f"  {len(out_of_order)} out-of-order aliases:")
        for o in out_of_order[:20]:
            print(o)
    else:
        print("  All v7 aliases are in alphabetical order")

print("\n" + "=" * 70)
print("DONE")
