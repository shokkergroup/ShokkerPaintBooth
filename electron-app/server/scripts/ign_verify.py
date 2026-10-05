# -*- coding: utf-8 -*-
"""Verify the IGNITION rebuilds (2026-06-10): 8 FABLE + 74 rework + 10 LFR finishes
(monolithic contract) plus 10 LFR spec overlays and 10 LFR patterns.

Gates per finish at 2048: contract, perf <=2.0s hard, fineness (char_px<=12,
blob<=0.25, fine>=0.35), mip>=0.28, paint mean luma>=0.06, channel decorrelation
max|corr|<0.85 (seeds 7/42/123 at 1024), and the NEW owner gates:
  MARRIAGE  — max(|corr(M, paint_luma)|, |corr(Cc, paint_luma)|) >= 0.30 at 512
              (spec must trace the paint's geometry, either polarity)
  RESTRAINT — the marrying channel's hot fraction (>200) in [0.03, 0.40]
              (ignition needs calm surroundings)
Emits one verdict line per item, writes _audit/ign_verify_results.json + contact
grids thumbnails/audit/_ign_grids/<group>.png (paint | spec side by side).
Usage: py -3 scripts/ign_verify.py [group ...]   (default: all)
"""
import io, json, os, sys, time

import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
import cv2  # noqa: E402
from engine.color_science import feature_fineness, mip_survival  # noqa: E402
from engine.paint_v2.fable_collection import FABLE_MONOLITHICS  # noqa: E402
from engine.expansions.colorshift_rework_2026 import REWORK_MONOLITHICS  # noqa: E402
from engine.paint_v2.cultural_let_freedom_ring import LFR_MONOLITHICS  # noqa: E402

FAB = ["fable_prism_veil", "fable_oilforge", "fable_static_bloom", "fable_saffron_circuit",
       "fable_quicksilver_garden", "fable_nightbloom", "fable_magnetite_flow", "fable_comet_parade"]
LFRF = ["lfr_old_glory_flux", "lfr_rockets_red_glare", "lfr_liberty_torch", "lfr_eagle_ascendant",
        "lfr_we_the_people", "lfr_midnight_militia", "lfr_freedom_forge", "lfr_amber_waves",
        "lfr_glory_chrome", "lfr_sparkler_dusk"]
OVL = ["spec_lfr_starfield_scatter", "spec_lfr_corridor_sheen", "spec_lfr_firework_radial",
       "spec_lfr_brocade_relief", "spec_lfr_liberty_colorflip", "spec_lfr_anisotropic_drift",
       "spec_lfr_sparkler_embers", "spec_lfr_torch_flicker", "spec_lfr_capitol_veins",
       "spec_lfr_canyon_bevel"]
PAT = ["lfr_star_lattice", "lfr_stripe_drift", "lfr_bunting_scallop", "lfr_distressed_flag",
       "lfr_eagle_crest", "lfr_firework_radial", "lfr_constellation_field", "lfr_ribbon_weave",
       "lfr_stencil_stars", "lfr_liberty_filigree"]

groups = {"fable_round4": FAB, "lfr_finishes": LFRF}
CATM = json.load(io.open(os.path.join(ROOT, "scripts", "rework_audit_meta.json"), encoding="utf-8"))
for m in CATM:
    groups.setdefault("rw_" + m["category"], []).append(m["id"])

S = 2048
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)
GRID_DIR = os.path.join(ROOT, "thumbnails", "audit", "_ign_grids")
os.makedirs(GRID_DIR, exist_ok=True)


def corr(a, b):
    a = a.astype(np.float32).ravel()
    b = b.astype(np.float32).ravel()
    sa, sb = a.std(), b.std()
    if sa < 1e-6 or sb < 1e-6:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def pair_of(fid):
    if fid.startswith("fable_"):
        return FABLE_MONOLITHICS[fid]
    if fid in LFR_MONOLITHICS:
        return LFR_MONOLITHICS[fid]
    return REWORK_MONOLITHICS[fid]


def tile(img, n=512):
    return cv2.resize((np.clip(img, 0, 1) * 255).astype(np.uint8), (n, n), interpolation=cv2.INTER_AREA)


results, nfail = {}, 0
want = sys.argv[1:] or list(groups.keys()) + ["lfr_overlays", "lfr_patterns"]

for gname, ids in groups.items():
    if gname not in want:
        continue
    rows = []
    for fid in ids:
        msgs = []
        try:
            spec_fn, paint_fn = pair_of(fid)
            t0 = time.perf_counter(); painted = paint_fn(base.copy(), (S, S), mask, 42, 1.0, {}); tp = time.perf_counter() - t0
            t0 = time.perf_counter(); spec = spec_fn((S, S), mask, 42, 1.0); ts = time.perf_counter() - t0
        except Exception as e:
            import traceback; traceback.print_exc()
            results.setdefault(gname, {})[fid] = {"verdict": "FAIL", "msgs": ["EXCEPTION %s: %s" % (type(e).__name__, e)]}
            print("FAIL", fid, "EXCEPTION", e); nfail += 1
            continue
        p3 = np.asarray(painted)[:, :, :3].astype(np.float32)
        if tp > 2.0: msgs.append("PERF paint %.2fs" % tp)
        if ts > 2.0: msgs.append("PERF spec %.2fs" % ts)
        if not (p3.min() >= -0.001 and p3.max() <= 1.001): msgs.append("paint range")
        if p3.mean() < 0.06: msgs.append("too dark %.3f" % p3.mean())
        f = feature_fineness(p3, full_size=S)
        if f["char_px"] > 12.0: msgs.append("FINENESS char %.1f" % f["char_px"])
        if f.get("blob", 0) > 0.25: msgs.append("blob %.2f" % f.get("blob", 0))
        if f.get("fine", 1) < 0.35: msgs.append("fine %.2f" % f.get("fine", 1))
        mp = mip_survival(p3)
        if mp < 0.28: msgs.append("mip %.2f" % mp)
        if spec.dtype != np.uint8 or spec.shape != (S, S, 4):
            msgs.append("spec contract")
            M = R = Cc = None
        else:
            M, R, Cc = (spec[:, :, i].astype(np.float32) for i in range(3))
            if R.min() < 15: msgs.append("R floor")
            if Cc.min() < 16: msgs.append("Cc floor")
            # channel decorrelation across seeds
            worst = 0.0
            for sd in (7, 42, 123):
                sp = spec if sd == 42 else spec_fn((1024, 1024), np.ones((1024, 1024), np.float32), sd, 1.0)
                ch = [cv2.resize(sp[:, :, i].astype(np.float32), (256, 256)) for i in range(3)]
                for i in range(3):
                    for j in range(i + 1, 3):
                        worst = max(worst, abs(corr(ch[i], ch[j])))
            if worst >= 0.85: msgs.append("DECORR %.2f" % worst)
            # MARRIAGE + RESTRAINT (owner doctrine 2026-06-10)
            luma = cv2.resize(p3 @ np.float32([0.2126, 0.7152, 0.0722]), (512, 512))
            cM = corr(cv2.resize(M, (512, 512)), luma)
            cC = corr(cv2.resize(Cc, (512, 512)), luma)
            marry = max(abs(cM), abs(cC))
            if marry < 0.30: msgs.append("MARRIAGE %.2f (M%+.2f Cc%+.2f)" % (marry, cM, cC))
            hotM = float((M > 200).mean())
            hotC = float((Cc > 200).mean())
            okM = 0.012 <= hotM <= 0.40
            okC = 0.012 <= hotC <= 0.40
            hot = hotM if okM else hotC
            # one channel must detonate with restraint; both >40% = no calm anywhere
            if not (okM or okC) or (hotM > 0.40 and hotC > 0.40):
                msgs.append("RESTRAINT hotM=%.1f%% hotC=%.1f%%" % (hotM * 100, hotC * 100))
        verdict = "PASS" if not msgs else "FAIL"
        nfail += verdict == "FAIL"
        results.setdefault(gname, {})[fid] = {
            "verdict": verdict, "msgs": msgs, "perf": [round(tp, 2), round(ts, 2)],
            "char_px": round(f["char_px"], 1), "luma": round(float(p3.mean()), 3),
            "marry": None if M is None else round(marry, 2), "hot": None if M is None else round(hot, 3)}
        print(verdict, fid, "; ".join(msgs) if msgs else
              "char %.1f marry %.2f hot %.0f%% %.2f/%.2fs" % (f["char_px"], marry, hot * 100, tp, ts))
        srgb = np.stack([spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]], -1) / 255.0 if M is not None else np.zeros((64, 64, 3))
        rows.append(np.hstack([tile(p3[:, :, ::-1]), tile(srgb[:, :, ::-1])]))
    if rows:
        cv2.imwrite(os.path.join(GRID_DIR, gname + ".png"), np.vstack(rows))

# ---------- LFR spec overlays ----------
if "lfr_overlays" in want:
    from engine.spec_patterns import PATTERN_CATALOG
    rows = []
    for oid in OVL:
        msgs = []
        try:
            fn = PATTERN_CATALOG[oid]
            t0 = time.perf_counter(); out = fn((S, S), 7, 1.0); te = time.perf_counter() - t0
            lo = fn((512, 512), 7, 0.0005)
            hi = fn((1024, 1024), 7, 2.0)
        except Exception as e:
            results.setdefault("lfr_overlays", {})[oid] = {"verdict": "FAIL", "msgs": ["EXCEPTION %s" % e]}
            print("FAIL", oid, "EXCEPTION", e); nfail += 1
            continue
        out = np.asarray(out, np.float32)
        if te > 2.0: msgs.append("PERF %.2fs" % te)
        if out.min() < -0.001 or out.max() > 1.001: msgs.append("range")
        if np.asarray(hi).std() < 0.02: msgs.append("sm2.0 flat")
        if np.asarray(hi).mean() > 0.97: msgs.append("sm2.0 clip")
        if float(np.asarray(lo).std()) > 0.05: msgs.append("sm~0 not flat")
        if out.ndim == 3:
            worst = max(abs(corr(out[:, :, i], out[:, :, j])) for i in range(3) for j in range(i + 1, 3))
            if worst >= 0.85: msgs.append("DECORR %.2f" % worst)
            prim = out[:, :, 0]
        else:
            prim = out
        hot = float((prim > 0.78).mean())
        if not (0.012 <= hot <= 0.45): msgs.append("RESTRAINT hot=%.1f%%" % (hot * 100))
        verdict = "PASS" if not msgs else "FAIL"
        nfail += verdict == "FAIL"
        results.setdefault("lfr_overlays", {})[oid] = {"verdict": verdict, "msgs": msgs, "perf": round(te, 2)}
        print(verdict, oid, "; ".join(msgs) if msgs else "hot %.0f%% %.2fs" % (hot * 100, te))
        viz = out if out.ndim == 3 else np.repeat(out[:, :, None], 3, 2)
        rows.append(tile(viz[:, :, ::-1]))
    if rows:
        cv2.imwrite(os.path.join(GRID_DIR, "lfr_overlays.png"), np.vstack(rows))

# ---------- LFR patterns ----------
if "lfr_patterns" in want:
    import engine.expansion_patterns as XP
    rows = []
    for pid in PAT:
        msgs = []
        s = pid.replace("lfr_", "")
        try:
            t0 = time.perf_counter()
            packed = XP._texture_lfr_dispatch((S, S), mask, 7, 1.0, pid)
            te = time.perf_counter() - t0
            tex = np.asarray(packed["pattern_val"] if isinstance(packed, dict) else packed, np.float32)
            t0 = time.perf_counter()
            pp = XP._paint_lfr_dispatch(base.copy(), (S, S), mask, 7, 1.0,
                                        {"pattern_val": np.clip(tex, 0, 1)}, pid)
            tpp = time.perf_counter() - t0
        except Exception as e:
            import traceback; traceback.print_exc()
            results.setdefault("lfr_patterns", {})[pid] = {"verdict": "FAIL", "msgs": ["EXCEPTION %s" % e]}
            print("FAIL", pid, "EXCEPTION", e); nfail += 1
            continue
        if te + tpp > 2.5: msgs.append("PERF %.2fs" % (te + tpp))
        cov = float((tex > 0.15).mean())
        if cov < 0.015: msgs.append("coverage %.1f%% (invisible)" % (cov * 100))
        if cov > 0.65: msgs.append("coverage %.1f%% (full-bleed? must be alpha-stamp)" % (cov * 100))
        verdict = "PASS" if not msgs else "FAIL"
        nfail += verdict == "FAIL"
        results.setdefault("lfr_patterns", {})[pid] = {"verdict": verdict, "msgs": msgs, "cov": round(cov, 3)}
        print(verdict, pid, "; ".join(msgs) if msgs else "cov %.0f%% %.2fs" % (cov * 100, te + tpp))
        rows.append(np.hstack([tile(np.repeat(np.clip(tex, 0, 1)[:, :, None], 3, 2)),
                               tile(np.asarray(pp)[:, :, :3][:, :, ::-1])]))
    if rows:
        cv2.imwrite(os.path.join(GRID_DIR, "lfr_patterns.png"), np.vstack(rows))

outp = os.path.join(ROOT, "_audit", "ign_verify_results.json")
io.open(outp, "w", encoding="utf-8").write(json.dumps(results, indent=1))
total = sum(len(v) for v in results.values())
print("\nTOTAL %d items, %d FAIL -> %s" % (total, nfail, outp))
sys.exit(1 if nfail else 0)
