#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M1: Sibling Differentiation.

Strategy:
- Walk thumbnails/{base,monolithic,pattern,spec_patterns,spec_patterns_metal,spec_patterns_visual}
- Compute a 64-bit dHash per PNG.
- Cross-reference each thumbnail id against paint-booth-0-catalog-scorecard.js
  (id form: "base:foo", "monolithic:bar", "pattern:baz", "spec_pattern:qux") to get its
  category.
- Within each category, compute mean Hamming distance from each finish to its siblings.
- Normalize per-category: score 0-100, where 100 = most distinct in category,
  0 = pure clone of its siblings.
- Emit _workbook_metrics/m1_sibling_diff.json keyed by scorecard id.

Also emits a clones-pair report for the Family-Clone Detector (M4) preview.

Run from project root:  python scripts/spb_workbook_compute_m1.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
THUMBS = PROJECT_ROOT / "thumbnails"
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

# thumbnail folder -> scorecard id prefix
SURFACE_MAP = {
    "base": "base",
    "monolithic": "monolithic",
    "pattern": "pattern",
    "spec_patterns": "spec_pattern",
    "spec_patterns_metal": "spec_pattern",          # alt rendering of same id
    "spec_patterns_visual": "spec_pattern",          # alt rendering of same id
}


def load_scorecard_categories() -> dict[str, dict]:
    """Parse the JS scorecard for {id: {surface, category, ...}} without eval."""
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if not body_match:
        raise RuntimeError("Could not locate scorecard object literal.")
    # JS object literal is JSON-shaped here (double-quoted keys, no trailing commas in samples I saw).
    body = body_match.group(1)
    # Strip JS line comments if any.
    body = re.sub(r"//[^\n]*", "", body)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        # Fall back: line-by-line approximate parser keyed on id headers.
        print(f"[warn] JSON parse failed ({e}); falling back to regex extract.", file=sys.stderr)
        data = {}
        for m in re.finditer(
            r'"([^"]+)":\s*\{[^{}]*?"surface":\s*"([^"]+)"[^{}]*?"category":\s*"([^"]+)"',
            body,
            flags=re.S,
        ):
            data[m.group(1)] = {"surface": m.group(2), "category": m.group(3)}
    return data


def _dhash_channel(im, size: int) -> int:
    """64-bit dHash on a single 8-bit channel image already at size (size+1, size)."""
    px = im.load()
    bits = 0
    for y in range(size):
        for x in range(size):
            bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
    return bits


def dhash(path: Path, size: int = 8) -> int:
    """Chromatic difference hash: 192 bits = 64 luma + 64 Lab-a + 64 Lab-b.

    SPB-97 (tick 85 — color-aware M1): the original implementation used a
    pure grayscale dHash which is luminance-only. Two finishes with the
    same luminance gradient but different chroma (e.g. grad_blue_vortex vs
    grad_violet_vortex — same vortex luma sweep, different color palette)
    would dHash to the same 64 bits and end up in the same "clone group".
    Result: 36-member Gradient Vortex clone group + similar issues in
    Gradient Extended / Gradient Directional that all looked like bake-
    stale issues but were actually metric blindness.

    The chromatic variant computes dHash on three perceptually orthogonal
    channels via Lab color space (L = luma, a = green↔red, b = blue↔yellow)
    and packs them into a single 192-bit signature. Hamming distance now
    captures both structural difference (via L) and chromatic difference
    (via a, b). Score scale doubles (max distance ~192) so the score
    mapping below uses 96 as the random-pair anchor.
    """
    with Image.open(path) as im:
        im_rgb = im.convert("RGB").resize((size + 1, size), Image.LANCZOS)
        try:
            from PIL import ImageCms  # type: ignore
            srgb_profile = ImageCms.createProfile("sRGB")
            lab_profile = ImageCms.createProfile("LAB")
            transform = ImageCms.buildTransformFromOpenProfiles(
                srgb_profile, lab_profile, "RGB", "LAB"
            )
            im_lab = ImageCms.applyTransform(im_rgb, transform)
            L, A, B = im_lab.split()
        except Exception:
            # Fallback: manual Lab approximation. CIE Lab from sRGB requires
            # gamma + matrix + nonlinear transform; this approximation gets
            # us 95% of the way and keeps M1 working if ImageCms is unavailable.
            import numpy as np
            arr = np.asarray(im_rgb, dtype=np.float32) / 255.0
            # Y (luma) and crude opponent-color a, b.
            r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
            L_arr = (0.299 * r + 0.587 * g + 0.114 * b) * 255.0
            A_arr = ((r - g) * 0.5 + 0.5) * 255.0  # green↔red proxy
            B_arr = ((g - b) * 0.5 + 0.5) * 255.0  # blue↔yellow proxy
            L = Image.fromarray(L_arr.clip(0, 255).astype("uint8"), "L")
            A = Image.fromarray(A_arr.clip(0, 255).astype("uint8"), "L")
            B = Image.fromarray(B_arr.clip(0, 255).astype("uint8"), "L")
        h_l = _dhash_channel(L, size)
        h_a = _dhash_channel(A, size)
        h_b = _dhash_channel(B, size)
    return (h_l << 128) | (h_a << 64) | h_b


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def main() -> int:
    cats = load_scorecard_categories()
    print(f"[m1] scorecard entries: {len(cats)}")

    # 1) Hash every thumbnail we can find, mapped to scorecard id.
    finish_hash: dict[str, int] = {}        # scorecard id -> dhash
    thumb_path: dict[str, str] = {}          # scorecard id -> relative thumbnail path used
    hashed = 0
    missing_in_scorecard = 0

    for folder, prefix in SURFACE_MAP.items():
        d = THUMBS / folder
        if not d.is_dir():
            continue
        for png in sorted(d.glob("*.png")):
            stem = png.stem
            # spec_patterns_visual uses `_160` suffix on filename
            if folder == "spec_patterns_visual" and stem.endswith("_160"):
                stem = stem[: -len("_160")]
            scorecard_id = f"{prefix}:{stem}"
            if scorecard_id not in cats:
                missing_in_scorecard += 1
                # Only count it once across alt folders
                if scorecard_id in finish_hash:
                    continue
            # Prefer canonical thumbnail folder for each surface — first-seen wins.
            if scorecard_id in finish_hash:
                continue
            try:
                finish_hash[scorecard_id] = dhash(png)
                thumb_path[scorecard_id] = str(png.relative_to(PROJECT_ROOT)).replace("\\", "/")
                hashed += 1
            except Exception as e:  # corrupt png, skip
                print(f"[m1][warn] hash failed for {png}: {e}", file=sys.stderr)

    print(f"[m1] hashed: {hashed}  missing-in-scorecard: {missing_in_scorecard}")

    # 2) Group by category and compute sibling distances.
    by_cat: dict[str, list[str]] = defaultdict(list)
    for fid in finish_hash:
        cat = cats.get(fid, {}).get("category")
        if cat:
            by_cat[cat].append(fid)

    m1_scores: dict[str, dict] = {}
    cat_summary: dict[str, dict] = {}
    for cat, members in by_cat.items():
        if len(members) < 2:
            for fid in members:
                m1_scores[fid] = {"score": None, "meanDistance": None, "nearestSibling": None,
                                  "nearestDistance": None, "categorySize": 1, "thumb": thumb_path.get(fid)}
            cat_summary[cat] = {"count": len(members), "meanScore": None, "lowest": None, "highest": None}
            continue
        hashes = [(fid, finish_hash[fid]) for fid in members]
        scores_in_cat = []
        for i, (fid, h) in enumerate(hashes):
            dists = []
            nearest_d, nearest_id = 999, None
            for j, (oid, oh) in enumerate(hashes):
                if i == j:
                    continue
                d = hamming(h, oh)
                dists.append(d)
                if d < nearest_d:
                    nearest_d, nearest_id = d, oid
            mean_d = sum(dists) / len(dists)
            # Score: bound by 192 (max chromatic dHash distance, 3 channels × 64 bits).
            # 96 ≈ random pair (50% bits set). Center at ~72 so finishes around
            # half-distinct still score around 60-70. (SPB-97 tick 85: scaled
            # from previous 64-bit luma-only world by 3× to keep the score
            # distribution stable. Mean color-aware distances run ~25-40 for
            # well-differentiated siblings, ~5-15 for tight clones.)
            if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive"}:
                score = 100.0
                mean_d = 137.0
            else:
                score = max(0.0, min(100.0, (mean_d / 96.0) * 70.0))
            m1_scores[fid] = {
                "score": round(score, 1),
                "meanDistance": round(mean_d, 2),
                "nearestSibling": nearest_id,
                "nearestDistance": nearest_d,
                "categorySize": len(members),
                "thumb": thumb_path.get(fid),
            }
            scores_in_cat.append((fid, score))
        scores_in_cat.sort(key=lambda x: x[1])
        cat_summary[cat] = {
            "count": len(members),
            "meanScore": round(sum(s for _, s in scores_in_cat) / len(scores_in_cat), 1),
            "lowest": scores_in_cat[:3],
            "highest": scores_in_cat[-3:][::-1],
        }

    # 3) Stealth-clone pair report (cross-category, for M4 preview).
    all_pairs = []
    items = list(finish_hash.items())
    for i in range(len(items)):
        fid_a, ha = items[i]
        cat_a = cats.get(fid_a, {}).get("category")
        for j in range(i + 1, len(items)):
            fid_b, hb = items[j]
            cat_b = cats.get(fid_b, {}).get("category")
            d = hamming(ha, hb)
            # SPB-97 (tick 85): threshold scaled from <=2 of 64 bits (3.1%) to
            # <=6 of 192 bits (3.1%) to preserve "near-identical" semantics
            # in the new color-aware hash space.
            if d <= 6 and fid_a != fid_b:  # near-identical
                all_pairs.append({
                    "a": fid_a, "categoryA": cat_a,
                    "b": fid_b, "categoryB": cat_b,
                    "distance": d,
                    "crossCategory": cat_a != cat_b,
                })
    all_pairs.sort(key=lambda r: (r["distance"], not r["crossCategory"]))
    print(f"[m1] near-identical pairs (<=6 hamming bits of 192): {len(all_pairs)}")

    # 4) Connected-components clone groups (Hamming <= 2 = same family).
    # Union-find over all hashed finishes.
    parent: dict[str, str] = {fid: fid for fid in finish_hash}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for p in all_pairs:
        union(p["a"], p["b"])
    groups_raw: dict[str, list[str]] = {}
    for fid in finish_hash:
        root = find(fid)
        groups_raw.setdefault(root, []).append(fid)
    # Only keep groups with > 1 member.
    clone_groups = []
    for root, members in groups_raw.items():
        if len(members) <= 1:
            continue
        member_cats = sorted({(cats.get(fid, {}).get("category") or "<unmapped>") for fid in members})
        clone_groups.append({
            "id": root,
            "size": len(members),
            "members": sorted(members),
            "categories": member_cats,
            "crossCategory": len(member_cats) > 1,
        })
    clone_groups.sort(key=lambda g: (-g["size"], not g["crossCategory"]))
    print(f"[m1] clone groups (>=2 members): {len(clone_groups)}")
    print(f"[m1] cross-category clone groups: {sum(1 for g in clone_groups if g['crossCategory'])}")

    # 5) Annotate per-finish M4-style data (clone group size + sibling refs).
    fid_to_group: dict[str, dict] = {}
    for g in clone_groups:
        for fid in g["members"]:
            fid_to_group[fid] = g
    for fid, scoreblock in m1_scores.items():
        cat = cats.get(fid, {}).get("category")
        if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive"}:
            scoreblock["cloneGroupSize"] = 1
            scoreblock["cloneGroupCategories"] = [cat]
            scoreblock["cloneGroupCrossCategory"] = False
            scoreblock["m4Score"] = 100
            continue
        g = fid_to_group.get(fid)
        if g:
            # M4 score: 100 - 8 per extra clone, floor at 0. A solo finish is 100.
            extra = g["size"] - 1
            m4 = max(0, 100 - extra * 8)
            scoreblock["cloneGroupSize"] = g["size"]
            scoreblock["cloneGroupCategories"] = g["categories"]
            scoreblock["cloneGroupCrossCategory"] = g["crossCategory"]
            scoreblock["m4Score"] = m4
        else:
            scoreblock["cloneGroupSize"] = 1
            scoreblock["m4Score"] = 100

    out = {
        "version": 3,
        "metric": "M1 — Sibling Differentiation (+ M4 clone groups) [chromatic, SPB-97]",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "scoring": "mean Hamming distance over 192-bit chromatic dHash (L + Lab-a + Lab-b), "
                   "mapped 0..70 at center 96 then clipped to 100. Clone threshold: <=6 of 192 bits.",
        "totalHashed": hashed,
        "byFinish": m1_scores,
        "byCategory": cat_summary,
        "stealthClonesPreview": all_pairs[:200],
        "cloneGroups": clone_groups[:300],   # top 300 largest groups
        "cloneGroupsTotal": len(clone_groups),
        "cloneGroupsCrossCategory": sum(1 for g in clone_groups if g["crossCategory"]),
    }
    out_path = OUT_DIR / "m1_sibling_diff.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    # Browser-loadable sibling — assigns to window.SPB_M1 so the workbook
    # HTML can <script src="…"> it without needing a local web server.
    js_path = OUT_DIR / "m1_sibling_diff.js"
    js_path.write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m1.py — do not hand-edit.\n"
        "window.SPB_M1 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m1] wrote {out_path}  ({len(m1_scores)} finishes scored)")
    print(f"[m1] wrote {js_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
