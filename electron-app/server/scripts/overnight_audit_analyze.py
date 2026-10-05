# -*- coding: utf-8 -*-
"""Analyze _overnight_audit/catalog_audit.json into a prioritized findings report.

Buckets every finish into actionable categories:
  - ERROR        : render threw at one or more sizes (pearl_micro-class)
  - SIZE_FRAGILE : errored at a SMALL size but rendered at another (size-dependent bug)
  - NONFINITE    : NaN/inf in output
  - DEAD         : flat / near-zero variance ("finish does nothing")
  - SLOW         : paint render over the perf budget
  - WEAK_SPEC    : spec map channel spread below the quality floor
  - DUP_SPEC     : near-duplicate spec map within the same family (uniqueness)
  - CASE_DUP     : finish IDs colliding only by case (Art_Deco vs art_deco)

Writes _overnight_audit/FINDINGS.md (human) + findings.json (machine).
"""
import os, json, math, re
from collections import defaultdict

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
OUT = os.path.join(ROOT, "_overnight_audit")
data = json.load(open(os.path.join(OUT, "catalog_audit.json"), encoding="utf-8"))

SLOW_MS = 800.0          # paint render budget per swatch
WEAK_STD = 0.04          # spec overall-std floor (0-1 scale) below which it's "weak"
DUP_DIST = 0.06          # L2 distance between 8x8 sigs below which two specs are "near-dup"

findings = {k: [] for k in
            ["ERROR", "SIZE_FRAGILE", "NONFINITE", "DEAD", "SLOW", "WEAK_SPEC", "DUP_SPEC", "CASE_DUP"]}


def fam(fid):
    # family = leading token before first underscore-number or a known prefix group
    m = re.match(r"([a-zA-Z]+)", fid)
    return m.group(1) if m else fid


# ---- swatch finishes (base/pattern/monolithic): paint + spec ----
sig_by_type = {}
for ftype, recs in data.get("paint", {}).items():
    sigs = {}
    for fid, e in recs.items():
        paint = e.get("paint", {})
        spec = e.get("spec")
        # errors / fragility across paint sizes
        sizes = {str(k): v for k, v in paint.items()}
        errored = {s: v["error"] for s, v in sizes.items() if isinstance(v, dict) and "error" in v}
        oksizes = [s for s, v in sizes.items() if isinstance(v, dict) and "error" not in v]
        if errored and oksizes:
            findings["SIZE_FRAGILE"].append((ftype, fid, "ok@%s err@%s: %s" % (",".join(oksizes), ",".join(errored), list(errored.values())[0])))
        elif errored:
            findings["ERROR"].append((ftype, fid, "paint err: " + list(errored.values())[0]))
        for s, v in sizes.items():
            if isinstance(v, dict) and "error" not in v:
                if not v.get("finite", True):
                    findings["NONFINITE"].append((ftype, fid, "paint@%s nonfinite" % s))
                if v.get("ms", 0) > SLOW_MS:
                    findings["SLOW"].append((ftype, fid, "paint@%s %.0fms" % (s, v["ms"])))
        # dead paint at the largest rendered size
        big = sizes.get("160") or sizes.get("64")
        if isinstance(big, dict) and "error" not in big and big.get("dead"):
            findings["DEAD"].append((ftype, fid, "paint flat (std=%.3f)" % big.get("std", 0)))
        # spec health + signature
        if isinstance(spec, dict):
            if "error" in spec:
                findings["ERROR"].append((ftype, fid, "spec err: " + spec["error"]))
            else:
                if not spec.get("finite", True):
                    findings["NONFINITE"].append((ftype, fid, "spec nonfinite"))
                if spec.get("std", 1) < WEAK_STD:
                    findings["WEAK_SPEC"].append((ftype, fid, "spec std=%.3f" % spec.get("std", 0)))
                if spec.get("sig"):
                    sigs[fid] = spec["sig"]
    sig_by_type[ftype] = sigs

# ---- spec patterns ----
sp_sigs = {}
for sid, e in data.get("spec_pattern", {}).items():
    szs = {str(k): v for k, v in e.items() if k not in ("sig",)}
    errored = {s: v["error"] for s, v in szs.items() if isinstance(v, dict) and "error" in v}
    oksizes = [s for s, v in szs.items() if isinstance(v, dict) and "error" not in v]
    if errored and oksizes:
        findings["SIZE_FRAGILE"].append(("spec_pattern", sid, "ok@%s err@%s: %s" % (",".join(oksizes), ",".join(errored), list(errored.values())[0])))
    elif errored:
        findings["ERROR"].append(("spec_pattern", sid, list(errored.values())[0]))
    for s, v in szs.items():
        if isinstance(v, dict) and "error" not in v and not v.get("finite", True):
            findings["NONFINITE"].append(("spec_pattern", sid, "nonfinite@%s" % s))
    big = szs.get("160") or szs.get("64")
    if isinstance(big, dict) and "error" not in big:
        if big.get("dead"):
            findings["DEAD"].append(("spec_pattern", sid, "flat (std=%.3f)" % big.get("std", 0)))
        if big.get("std", 1) < WEAK_STD:
            findings["WEAK_SPEC"].append(("spec_pattern", sid, "std=%.3f" % big.get("std", 0)))
    if e.get("sig"):
        sp_sigs[sid] = e["sig"]
sig_by_type["spec_pattern"] = sp_sigs


def l2(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) / math.sqrt(len(a))


# ---- near-duplicate specs within each family, per type ----
for ftype, sigs in sig_by_type.items():
    byfam = defaultdict(list)
    for fid, s in sigs.items():
        byfam[fam(fid)].append((fid, s))
    for f, items in byfam.items():
        if len(items) < 2:
            continue
        seen = set()
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a[0] in seen and b[0] in seen:
                    continue
                d = l2(a[1], b[1])
                if d < DUP_DIST:
                    findings["DUP_SPEC"].append((ftype, "%s ~= %s" % (a[0], b[0]), "fam=%s dist=%.3f" % (f, d)))
                    seen.add(a[0]); seen.add(b[0])

# ---- case-collision IDs ----
allids = []
for ftype, recs in data.get("paint", {}).items():
    allids += [(ftype, k) for k in recs]
allids += [("spec_pattern", k) for k in data.get("spec_pattern", {})]
low = defaultdict(list)
for ftype, k in allids:
    low[(ftype, k.lower())].append(k)
for (ftype, lk), variants in low.items():
    if len(set(variants)) > 1:
        findings["CASE_DUP"].append((ftype, " / ".join(sorted(set(variants))), "case-collision"))

# ---- write reports ----
order = ["ERROR", "SIZE_FRAGILE", "NONFINITE", "DEAD", "WEAK_SPEC", "SLOW", "DUP_SPEC", "CASE_DUP"]
desc = {
    "ERROR": "Render THREW (broken finish — fix or pull)",
    "SIZE_FRAGILE": "Errors at one size but not another (pearl_micro-class size bug)",
    "NONFINITE": "NaN/inf in output",
    "DEAD": "Flat / near-zero variance — the finish does nothing visible",
    "WEAK_SPEC": "Spec map channel spread below the quality floor (weak material)",
    "SLOW": "Paint render over the %.0fms budget" % SLOW_MS,
    "DUP_SPEC": "Near-identical spec map to a sibling in the same family",
    "CASE_DUP": "Finish IDs that collide only by case (lookup/filesystem hazard)",
}
with open(os.path.join(OUT, "findings.json"), "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=1)

lines = ["# SPB Overnight Catalog Audit — Findings", ""]
lines.append("Counts audited: " + ", ".join("%s=%d" % (k, v) for k, v in data["meta"]["counts"].items()))
lines.append("Paint sizes %s, spec %s, spec-pattern sizes %s. Render time %ss." % (
    data["meta"]["paint_sizes"], data["meta"]["spec_size"], data["meta"]["spec_pattern_sizes"], data["meta"].get("elapsed_s")))
lines.append("")
lines.append("## Summary")
for k in order:
    lines.append("- **%s** (%d): %s" % (k, len(findings[k]), desc[k]))
lines.append("")
for k in order:
    items = findings[k]
    if not items:
        continue
    lines.append("## %s — %d  (%s)" % (k, len(items), desc[k]))
    for ftype, fid, note in items[:60]:
        lines.append("- `%s` **%s** — %s" % (ftype, fid, note))
    if len(items) > 60:
        lines.append("- ... +%d more (see findings.json)" % (len(items) - 60))
    lines.append("")
open(os.path.join(OUT, "FINDINGS.md"), "w", encoding="utf-8").write("\n".join(lines))

print("=== AUDIT FINDINGS ===")
for k in order:
    print("  %-13s %4d" % (k, len(findings[k])))
print("wrote", os.path.join(OUT, "FINDINGS.md"))
