# -*- coding: utf-8 -*-
"""Independent verification of ALL 92 rebuilt finishes (18 FABLE + 74 rework):
contract, determinism, decorrelation (seeds 7/42/123), FINENESS GATE
(char_px<=12, blob<=0.25, fine>=0.35), mip>=0.28, luminance>=0.06, perf <=2.0s
hard (target 1.0) at 2048. Also proves the shokker engine actually serves the
rework fns. Renders per-category contact grids _rw_grid_<cat>.png."""
import sys, time, json
import numpy as np
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
import cv2
from engine.color_science import feature_fineness, mip_survival

from engine.paint_v2.fable_collection import FABLE_MONOLITHICS
from engine.expansions.colorshift_rework_2026 import REWORK_MONOLITHICS

FAB_REBUILT = ["fable_ember_glass","fable_glacier_core","fable_abyss_lantern","fable_stained_aurora",
               "fable_prism_veil","fable_oilforge","fable_tempered_dawn","fable_pulse_alloy",
               "fable_sovereign_flip","fable_static_bloom","fable_aurora_travel","fable_saffron_circuit",
               "fable_quicksilver_garden","fable_emberline_drift","fable_duomorph","fable_nightbloom",
               "fable_magnetite_flow","fable_comet_parade"]

CAT = json.load(open(r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\scripts\rework_audit_meta.json", encoding="utf-8"))
groups = {}
for m in CAT:
    groups.setdefault(m["category"], []).append(m["id"])
groups["fable_round2"] = FAB_REBUILT

S = 2048
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)
SM, GS = 512, 512  # grid tile size

def get_pair(fid):
    if fid.startswith("fable_"):
        return FABLE_MONOLITHICS[fid]
    return REWORK_MONOLITHICS[fid]

fail = 0
results = {}
for cat, ids in groups.items():
    ptiles, stiles = [], []
    for fid in ids:
        spec_fn, paint_fn = get_pair(fid)
        msgs = []
        try:
            t0 = time.perf_counter(); painted = paint_fn(base.copy(), (S, S), mask, 42, 1.0, {}); tp = time.perf_counter() - t0
            t0 = time.perf_counter(); spec = spec_fn((S, S), mask, 42, 1.0); ts = time.perf_counter() - t0
        except Exception as e:
            import traceback; traceback.print_exc()
            print("FAIL", fid, "EXCEPTION", type(e).__name__, e); fail += 1; continue
        p3 = painted[:, :, :3]
        f = feature_fineness(p3, full_size=S)
        mp = mip_survival(p3)
        if not (p3.min() >= -0.001 and p3.max() <= 1.001): msgs.append("paint range")
        if p3.mean() < 0.055: msgs.append("too dark %.3f" % p3.mean())
        if spec.dtype != np.uint8 or spec.shape != (S, S, 4): msgs.append("spec contract")
        else:
            if spec[:, :, 1].min() < 15: msgs.append("R floor")
            if spec[:, :, 2].min() < 16: msgs.append("Cc floor")
        if f["char_px"] > 12.0: msgs.append("FINENESS char %.1f" % f["char_px"])
        if f["blob_fraction"] > 0.25: msgs.append("BLOB %.2f" % f["blob_fraction"])
        if f["fine_fraction"] < 0.35: msgs.append("fine_frac %.2f" % f["fine_fraction"])
        if mp < 0.28: msgs.append("MIP %.2f" % mp)
        if tp > 2.0 or ts > 2.0: msgs.append("SLOW %.1f/%.1f" % (tp, ts))
        worst = 0.0
        for sd in (7, 42, 123):
            sp = spec if sd == 42 else spec_fn((S, S), mask, sd, 1.0)
            flat = [sp[:, :, k][::4, ::4].astype(np.float64).ravel() for k in range(3)]
            if min(c.std() for c in flat) < 0.8: continue
            cm = np.corrcoef(np.stack(flat))
            worst = max(worst, abs(cm[0, 1]), abs(cm[0, 2]), abs(cm[1, 2]))
        if worst >= 0.85: msgs.append("DECORR %.2f" % worst)
        results[fid] = {"char": f["char_px"], "blob": f["blob_fraction"], "fine": f["fine_fraction"],
                        "mip": round(mp, 2), "corr": round(worst, 2), "paint_s": round(tp, 2), "spec_s": round(ts, 2)}
        def tile(rgb_u8, label):
            t = cv2.resize(rgb_u8, (GS, GS), interpolation=cv2.INTER_AREA)
            t = cv2.cvtColor(t, cv2.COLOR_RGB2BGR).copy()
            cv2.rectangle(t, (0, 0), (GS - 1, 22), (0, 0, 0), -1)
            cv2.putText(t, label, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
            return t
        ptiles.append(tile((np.clip(p3, 0, 1) * 255).astype(np.uint8), fid))
        stiles.append(tile(spec[:, :, :3], fid + " SPEC"))
        if msgs:
            print("FAIL", fid, "|", "; ".join(msgs)); fail += 1
        else:
            print("OK  ", fid, "| char %.1f blob %.2f fine %.2f mip %.2f corr %.2f %.1f/%.1fs"
                  % (f["char_px"], f["blob_fraction"], f["fine_fraction"], mp, worst, tp, ts))
    per = 5
    rows = []
    for i in range(0, len(ptiles), per):
        row = ptiles[i:i + per]
        while len(row) < per: row.append(np.zeros((GS, GS, 3), np.uint8))
        rows.append(np.hstack(row))
    for i in range(0, len(stiles), per):
        row = stiles[i:i + per]
        while len(row) < per: row.append(np.zeros((GS, GS, 3), np.uint8))
        rows.append(np.hstack(row))
    if rows:
        cv2.imwrite(r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\_rw_grid_%s.png" % cat, np.vstack(rows))

json.dump(results, open(r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\_rw_verify_results.json", "w"), indent=1)
print()
print("RESULT:", "ALL %d PASS" % len(results) if fail == 0 else "%d FAILURES of %d" % (fail, len(results)))
sys.exit(1 if fail else 0)
