"""Spec INDEX + diversity picker for Spec Sculpt.

Every registered base + monolithic finish has a spec function. This module renders
each one once (small, no-VM, via the catalog path), stores a compact feature vector
+ a quality score, and offers ``pick_diverse()`` — a greedy farthest-point selection
that returns N maximally-different, above-quality finishes for Shokk the World.

Why this matters: the library has ~1,500 specs but lots of near-neighbors (color-shift
families etc.). Picking randomly floods a gallery with look-alikes; farthest-point
picking guarantees genuinely distinct results and naturally dedups clusters.

Build offline:  ``python scripts/build_spec_index.py``  → engine/spec_sculpt/spec_index.json
Use at runtime: ``from engine.spec_sculpt.spec_index import pick_diverse``
"""
from __future__ import annotations

import base64
import json
import os
import re
from functools import lru_cache

import numpy as np

_INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec_index.json")
_GRID = 10  # feature downsample grid (GRID x GRID x 3)
_FEAT_DIM = _GRID * _GRID * 3


def pretty_name(fid: str) -> str:
    """Human label from a finish id (strip known family prefixes, title-case)."""
    s = str(fid)
    for pre in ("cs_", "cx_", "pp_", "rs_", "uj_", "vm_", "fd_", "cc_", "gd_", "efx_",
                "grad_", "f_", "p_", "enh_", "pf_"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s.replace("_", " ").strip().title()


# [SPB-SPEC-SCULPT 2026-06-02] Auto-generated fusion ids like `gf_x_426203826_fc914006_…`,
# `gf_x_13845`, `gf_x_29035` title-case into garbage gallery labels ("Gf X 426203826 …").
# They are hash-named procedural combos, NOT curated looks — keep them OUT of Shokk the World
# so the world list feels hand-picked. Named gf_x_ fusions (e.g. gf_x_chrome_candy) are kept.
def _is_garbage_id(fid: str) -> bool:
    s = str(fid).lower()
    if not s.startswith("gf_x_"):
        return False
    toks = [t for t in s[5:].split("_") if t]
    if not toks:
        return False
    first = toks[0]
    return bool(re.fullmatch(r"[0-9a-f]{4,}", first)) and any(c.isdigit() for c in first)


# [SPB-SPEC-SCULPT fix#10 2026-06-02] A few index finishes (e.g. the 'ui_' UI-only aliases
# ui_groovy_waves / ui_canary_break_point / ...) are registered enough to land in the spec index
# but are REJECTED by the render path (normalize_catalog_stack -> []). When pick_diverse selects one,
# the batch hits `if not cat and not ps: continue` and silently DROPS that look -> the gallery returns
# 23 instead of 24 and a diverse pick is wasted (root cause of the persistent "23 looks"). Exclude any
# render-unusable id from the world picker so every pick actually renders. Cached (computed once).
@lru_cache(maxsize=1)
def _unrenderable_ids() -> frozenset:
    try:
        from engine.spec_sculpt.catalog_blend import normalize_catalog_stack
        idx = load_spec_index()
        if not idx or not idx.get("ids"):
            return frozenset()
        return frozenset(i for i in idx["ids"] if not normalize_catalog_stack([[i, 1.0]]))
    except Exception:  # noqa: BLE001 — never let the picker crash over this
        return frozenset()


# [SPB-SPEC-SCULPT fix#11 2026-06-02] Owner-curated denylist (world_denylist.json next to this module).
# Auto-detecting "too blobby / low-frequency" looks was ruled out (iter13: a frequency scalar mis-targets —
# it flags chrome/reptile and misses swirls), so the right tool is human curation: the owner lists finish
# ids to drop from SHOKK THE WORLD and they're excluded here. EMPTY by default => zero behaviour change.
@lru_cache(maxsize=1)
def _denylist_ids() -> frozenset:
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_denylist.json")
        if not os.path.exists(path):
            return frozenset()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return frozenset(str(x) for x in (data.get("exclude_ids") or []))
    except Exception:  # noqa: BLE001
        return frozenset()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def _feature_and_quality(comp_u8: np.ndarray):
    """comp_u8 = HxWx3 spec composite. Return (feat uint8 [D], quality float 0..1, cmean[3])."""
    import cv2
    small = cv2.resize(comp_u8, (_GRID, _GRID), interpolation=cv2.INTER_AREA).astype(np.float32)
    feat = np.clip(small.reshape(-1), 0, 255).astype(np.uint8)
    f = comp_u8.astype(np.float32)
    cmean = f.reshape(-1, 3).mean(0)
    # quality: spatial structure (not flat) + tonal contrast - pegged penalty
    structure = float(np.mean(small.std(axis=(0, 1)))) / 64.0           # variation across the tile
    contrast = float(np.percentile(f, 95) - np.percentile(f, 5)) / 200.0
    pegged = float(np.mean((f <= 2) | (f >= 253)))                      # too many dead/blown pixels
    q = 0.55 * min(contrast, 1.0) + 0.45 * min(structure, 1.0) - 0.35 * pegged
    return feat, float(np.clip(q, 0.0, 1.0)), cmean.tolist()


def build_spec_index(size: int = 64, out_path: str | None = None, *, log=print) -> dict:
    """Render every base+monolithic spec and write the index json. Returns summary."""
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY
    from engine.spec_sculpt.catalog_blend import blend_registered_specs_float

    ids = sorted(set(BASE_REGISTRY.keys()) | set(MONOLITHIC_REGISTRY.keys()))
    m = np.ones((size, size), dtype=np.float32)
    entries, feats = [], []
    failed = 0
    for i, fid in enumerate(ids):
        try:
            s = blend_registered_specs_float((size, size), m, seed=9101, sm=1.0, stack=[(fid, 1.0)])
            comp = np.stack([s[:, :, 0], s[:, :, 1], s[:, :, 2]], axis=2).astype(np.uint8)
            feat, q, cmean = _feature_and_quality(comp)
        except Exception as e:  # noqa: BLE001
            failed += 1
            if failed <= 10:
                log(f"  [spec-index] skip {fid}: {e}")
            continue
        entries.append({
            "id": fid,
            "name": pretty_name(fid),
            "family": fid.split("_")[0],
            "quality": round(q, 4),
            "cmean": [round(c, 1) for c in cmean],
            "kind": "base" if fid in BASE_REGISTRY else "monolithic",
        })
        feats.append(feat)
        if (i + 1) % 200 == 0:
            log(f"  [spec-index] {i + 1}/{len(ids)} ({len(entries)} ok, {failed} skipped)")

    feats_arr = np.asarray(feats, dtype=np.uint8) if feats else np.zeros((0, _FEAT_DIM), np.uint8)
    payload = {
        "version": 1,
        "size": size,
        "grid": _GRID,
        "feat_dim": _FEAT_DIM,
        "registry_count": len(ids),
        "count": len(entries),
        "entries": entries,
        "feats_b64": base64.b64encode(feats_arr.tobytes()).decode("ascii"),
    }
    out = out_path or _INDEX_PATH
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    log(f"[spec-index] wrote {out}: {len(entries)} finishes ({failed} skipped) of {len(ids)}")
    return {"count": len(entries), "failed": failed, "path": out}


# ---------------------------------------------------------------------------
# Load + pick
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_spec_index() -> dict | None:
    """Load the prebuilt index (cached). Returns None if it hasn't been built."""
    if not os.path.exists(_INDEX_PATH):
        return None
    try:
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        n = int(data.get("count", 0))
        d = int(data.get("feat_dim", _FEAT_DIM))
        raw = base64.b64decode(data.get("feats_b64", ""))
        feats = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        feats = feats.reshape(n, d) if n and len(feats) == n * d else np.zeros((n, d), np.float32)
        return {
            "entries": data.get("entries", []),
            "ids": [e["id"] for e in data.get("entries", [])],
            "quality": np.asarray([e.get("quality", 0.0) for e in data.get("entries", [])], np.float32),
            "feats": feats,
            "registry_count": int(data.get("registry_count", 0)),
        }
    except Exception:  # noqa: BLE001
        return None


def index_available() -> bool:
    idx = load_spec_index()
    return bool(idx and idx["ids"])


def pick_diverse(n: int = 24, *, seed: int = 9101, quality_floor: float | None = None,
                 star_ids: set[str] | None = None, star_bonus: float = 0.35,
                 exclude: set[str] | None = None) -> list[dict]:
    """Greedy farthest-point pick of ``n`` distinct, above-quality finishes.

    Returns list of ``{"id","name","quality"}``. Deterministic per ``seed``
    (the seed only offsets the starting finish so 'reroll' gives a different,
    still-diverse set). ``star_ids`` (e.g. audit KEEPers) get a quality bonus.
    """
    idx = load_spec_index()
    if not idx or not idx["ids"]:
        return []
    ids = idx["ids"]
    feats = idx["feats"]
    quality = idx["quality"].copy()
    N = len(ids)
    star_ids = star_ids or set()
    exclude = exclude or set()

    # star bonus + exclusion
    score0 = quality.copy()
    _unrenderable = _unrenderable_ids()  # [fix#10] render-unusable ids -> never pick (the gallery would silently drop them)
    _denied = _denylist_ids()            # [fix#11] owner-curated exclusions (world_denylist.json)
    for i, fid in enumerate(ids):
        if fid in star_ids:
            score0[i] += star_bonus
        if fid in exclude or _is_garbage_id(fid) or fid in _unrenderable or fid in _denied:  # junk + render-unusable + owner-denied
            score0[i] = -1e9

    # adaptive quality floor (percentile) so we keep enough candidates
    if quality_floor is None:
        quality_floor = float(np.percentile(quality, 45))
    eligible = (quality >= quality_floor) & (score0 > -1e8)
    if int(eligible.sum()) < n:  # relax if too strict
        eligible = score0 > -1e8
    elig_idx = np.where(eligible)[0]
    if len(elig_idx) == 0:
        return []
    n = min(n, len(elig_idx))

    # Seeded RNG: farthest-point converges to the same set regardless of start, so we
    # add small multiplicative jitter to the scores → different seeds give a different
    # (still highly diverse) set, enabling "reroll". Deterministic per seed.
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    # seeded start among the top-quality eligible finishes
    order = elig_idx[np.argsort(-score0[elig_idx])]
    topk = min(24, len(order))
    start = int(order[int(rng.integers(0, topk))])

    selected = [start]
    # running min distance from each eligible candidate to the selected set
    mind = np.linalg.norm(feats[elig_idx] - feats[start], axis=1)
    qn = quality[elig_idx]
    qn = (qn - qn.min()) / (float(np.ptp(qn)) + 1e-6)
    pos = {int(g): k for k, g in enumerate(elig_idx)}  # global idx -> local row
    mind[pos[start]] = -1.0

    while len(selected) < n:
        jitter = 1.0 + 0.22 * rng.standard_normal(len(elig_idx)).astype(np.float32)
        cand = mind * (0.6 + 0.4 * qn) * np.clip(jitter, 0.4, 1.6)  # diversity + seed variety
        cand[mind < 0] = -1.0  # exclude already-selected
        nxt_local = int(np.argmax(cand))
        nxt_global = int(elig_idx[nxt_local])
        if mind[nxt_local] < 0:
            break
        selected.append(nxt_global)
        d = np.linalg.norm(feats[elig_idx] - feats[nxt_global], axis=1)
        mind = np.minimum(mind, d)
        mind[nxt_local] = -1.0

    return [{"id": ids[i], "name": idx["entries"][i].get("name", ids[i]),
             "quality": float(quality[i])} for i in selected]
