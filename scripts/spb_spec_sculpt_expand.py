"""Expand the Spec Sculpt preset roster with diverse, above-quality REAL finishes.

Balanced, per-category farthest-point selection over the prebuilt spec index
(engine/spec_sculpt/spec_index.json). For each of the 6 spec-sculpt categories we
pick the most mutually-distinct finishes *within that category*, seeded against the
finishes the existing presets already use — so the additions are diverse AND spread
across categories (not all dumped into the library's big color/glow families).

Each pick maps to a real registered finish id (the same proven specs the Paint Booth
uses) — nothing procedural.

Output: a ready-to-paste block of ``_p(...)`` lines (grouped by category) at
``C:\\temp\\spb_new_presets.txt`` + a histogram on stdout.

Run:  python scripts/spb_spec_sculpt_expand.py --n 47
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.spec_sculpt.presets import PRESET_CATALOG_BY_ID, VALID_SPEC_SCULPT_PRESET_IDS  # noqa: E402
from engine.spec_sculpt.spec_index import load_spec_index, pretty_name  # noqa: E402

CATEGORY_ORDER = [
    "Chrome & metal", "Carbon & matte", "Candy & pearl",
    "Flake & sparkle", "Holo & shift", "Exotic & glow",
]

# Keyword -> category, checked in this (specific -> general) order; first hit wins.
# Exotic & glow is the catch-all and is handled by the fallback, not a rule here.
_CAT_RULES = [
    ("Flake & sparkle", ("flake", "sparkle", "glitter", "quilt", "mosaic", "sequin",
                         "confetti", "metalflake", "stardust", "glitz", "speckle",
                         "tile")),
    ("Holo & shift", ("chameleon", "holo", "spectral", "spectrum", "prism", "prizm",
                      "oil_slick", "oilslick", "hyperflip", "hypershift", "dichroic",
                      "iridescent", "rainbow", "thin_film", "opal", "flip", "shift",
                      "pf_", "cs_", "cx_", "hyper")),
    ("Chrome & metal", ("chrome", "mirror", "mercury", "gunmetal", "steel", "titanium",
                        "aluminum", "alloy", "platinum", "nickel", "silver", "metal",
                        "machined", "brushed", "foil", "damascus", "chainmail",
                        "tungsten", "pewter")),
    ("Candy & pearl", ("candy", "pearl", "ghost", "anodized", "gloss", "jelly",
                       "lacquer", "glass", "wet_", "mother", "nacre", "opalescent",
                       "clearcoat")),
    ("Carbon & matte", ("carbon", "matte", "satin", "weave", "fiber", "suede",
                        "velvet", "frozen", "ceramic", "fabric", "denim", "canvas",
                        "burlap", "stone", "slate", "granite", "sandstone", "concrete",
                        "flat", "tweed", "linen", "leather", "wood", "patina", "rust",
                        "weather", "worn", "oxid", "forged")),
]

_CAT_DESC = {
    "Chrome & metal": "reflective metal pick",
    "Carbon & matte": "matte / weave pick",
    "Candy & pearl": "candy / pearl gloss pick",
    "Flake & sparkle": "flake / sparkle pick",
    "Holo & shift": "color-shift / holo pick",
    "Exotic & glow": "exotic / glow pick",
}


def categorize(fid: str, cmean) -> str:
    f = str(fid).lower()
    for cat, kws in _CAT_RULES:
        if any(k in f for k in kws):
            return cat
    # Catch-all: most color/cultural/gradient finishes -> Exotic & glow, but use the
    # spec composite mean to rescue obvious metals / mattes that slipped the keywords.
    if cmean is not None:
        m, r = float(cmean[0]), float(cmean[1])   # R-channel=Metallic, G=Roughness
        if m >= 150 and r <= 90:
            return "Chrome & metal"
        if r >= 170 and m <= 90:
            return "Carbon & matte"
    return "Exotic & glow"


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")
    return s or "finish"


# Guest/AI-import/user-import plates have meaningless ids (hashes, UUIDs, raw numbers,
# "digital illustration" titles) — never good curated presets. Exclude them.
_JUNK_RE = re.compile(r"(?:^gf_)|(?:^ui_)|[0-9a-f]{8,}|\d{4,}|illustration|magnific|"
                      r"untitled|screenshot|export|img_\d", re.IGNORECASE)


def is_junk(fid: str) -> bool:
    return bool(_JUNK_RE.search(str(fid)))


def farthest_point(cand_local_idx, feats_cand, qn_cand, seed_rows_feats, k):
    """Greedy farthest-point pick of k rows from feats_cand (subset given by
    cand_local_idx into the *category* arrays), seeded by seed_rows_feats. Returns
    local indices (into the category arrays) of the picks, most-distinct first."""
    if k <= 0 or len(cand_local_idx) == 0:
        return []
    C = feats_cand[cand_local_idx]
    qn = qn_cand[cand_local_idx]
    mind = np.full(len(cand_local_idx), np.inf, dtype=np.float32)
    if len(seed_rows_feats):
        for sf in seed_rows_feats:
            mind = np.minimum(mind, np.linalg.norm(C - sf, axis=1))
    else:
        mind[:] = 1.0
    picks: list[int] = []
    k = min(k, len(cand_local_idx))
    while len(picks) < k:
        score = mind * (0.55 + 0.45 * qn)
        for p in picks:
            score[p] = -1.0
        nxt = int(np.argmax(score))
        if score[nxt] <= 0 and picks:
            break
        picks.append(nxt)
        mind = np.minimum(mind, np.linalg.norm(C - C[nxt], axis=1))
    return [int(cand_local_idx[p]) for p in picks]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=47)
    ap.add_argument("--quality-pct", type=float, default=50.0)
    ap.add_argument("--out", default=r"C:\temp\spb_new_presets.txt")
    args = ap.parse_args()

    idx = load_spec_index()
    if not idx or not idx["ids"]:
        print("ERROR: spec_index.json missing/empty - run scripts/build_spec_index.py first")
        sys.exit(1)

    ids = idx["ids"]
    feats = idx["feats"].astype(np.float32)
    quality = idx["quality"].astype(np.float32)
    entries = idx["entries"]
    pos = {fid: i for i, fid in enumerate(ids)}

    used_fids = set()
    for stack in PRESET_CATALOG_BY_ID.values():
        for fid, _w in stack:
            used_fids.add(fid)

    qn_all = (quality - quality.min()) / (float(np.ptp(quality)) + 1e-6)
    floor = float(np.percentile(quality, args.quality_pct))

    # Categorize the whole index once.
    cat_of = [categorize(fid, entries[i].get("cmean")) for i, fid in enumerate(ids)]

    # Per-category: candidate rows (unused + above floor) and seed rows (existing used).
    cand_by_cat: dict[str, list[int]] = {c: [] for c in CATEGORY_ORDER}
    seed_by_cat: dict[str, list[int]] = {c: [] for c in CATEGORY_ORDER}
    for i, fid in enumerate(ids):
        c = cat_of[i]
        if fid in used_fids:
            seed_by_cat[c].append(i)
        elif quality[i] >= floor and not is_junk(fid):
            cand_by_cat[c].append(i)

    avail = {c: len(cand_by_cat[c]) for c in CATEGORY_ORDER}
    print(f"index={len(ids)} used={len(used_fids)} floor=q{args.quality_pct:.0f}={floor:.3f}")
    print("candidates per category:", {c: avail[c] for c in CATEGORY_ORDER})

    # Quota: even split of n across 6, then redistribute shortfalls to spare capacity.
    base, rem = divmod(args.n, len(CATEGORY_ORDER))
    target = {c: base + (1 if k < rem else 0) for k, c in enumerate(CATEGORY_ORDER)}
    take = {c: min(target[c], avail[c]) for c in CATEGORY_ORDER}
    shortfall = args.n - sum(take.values())
    while shortfall > 0:
        spare = [c for c in CATEGORY_ORDER if avail[c] - take[c] > 0]
        if not spare:
            break
        for c in spare:
            if shortfall <= 0:
                break
            take[c] += 1
            shortfall -= 1
    print("take per category:", {c: take[c] for c in CATEGORY_ORDER})

    rows = []
    for c in CATEGORY_ORDER:
        cand = np.asarray(cand_by_cat[c], dtype=int)
        if len(cand) == 0 or take[c] == 0:
            continue
        seed_feats = [feats[r] for r in seed_by_cat[c]]
        picks = farthest_point(np.arange(len(cand)), feats[cand], qn_all[cand],
                               seed_feats, take[c])
        for pl in picks:
            gi = int(cand[pl])
            rows.append((c, gi))

    # Build preset dicts, dedupe slugs/labels.
    used_slugs = set(VALID_SPEC_SCULPT_PRESET_IDS)
    out_rows = []
    for cat, gi in rows:
        fid = ids[gi]
        label = pretty_name(fid)
        slug = slugify(label)
        base_s = slug
        k = 2
        while slug in used_slugs:
            slug = f"{base_s}_{k}"
            k += 1
        used_slugs.add(slug)
        fam = entries[gi].get("family") or fid.split("_")[0]
        tag_src = [t for t in slug.split("_") if len(t) > 1][:3]
        tags = list(dict.fromkeys(tag_src + [fam]))[:4]
        desc = f"{label} - {_CAT_DESC[cat]}."
        out_rows.append({"slug": slug, "label": label, "category": cat, "fid": fid,
                         "desc": desc, "tags": tags, "q": round(float(quality[gi]), 3)})

    hist = {c: 0 for c in CATEGORY_ORDER}
    for r in out_rows:
        hist[r["category"]] += 1
    print("\nNew picks per category:")
    for c in CATEGORY_ORDER:
        print(f"  {c:<16} +{hist[c]}")
    total = len(VALID_SPEC_SCULPT_PRESET_IDS) + len(out_rows)
    print(f"  TOTAL new = {len(out_rows)}  =>  roster {len(VALID_SPEC_SCULPT_PRESET_IDS)} + "
          f"{len(out_rows)} = {total}")

    lines = ["    # ==== Auto-expanded batch (diverse spec-index picks; audit me) ===="]
    for c in CATEGORY_ORDER:
        crows = [r for r in out_rows if r["category"] == c]
        if not crows:
            continue
        lines.append(f"    # ---- {c} ----")
        for r in crows:
            a = json.dumps(r["slug"]); b = json.dumps(r["label"]); cc = json.dumps(r["category"])
            ff = json.dumps(r["fid"]); dd = json.dumps(r["desc"]); tt = json.dumps(r["tags"])
            lines.append(f"    _p({a}, {b}, {cc}, {ff},")
            lines.append(f"       {dd}, {tt}),")
    block = "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(block)
    print(f"\nwrote paste-block -> {args.out} ({len(out_rows)} presets, {len(block)} chars)")


if __name__ == "__main__":
    main()
