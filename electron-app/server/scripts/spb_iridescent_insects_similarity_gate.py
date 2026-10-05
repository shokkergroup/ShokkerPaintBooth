"""Cross-card visual-similarity audit for IRIDESCENT INSECTS.

The owner's 2026-09-01 review found that several live picker cards looked like
palette swaps of the same diagonal-wave carrier.  M7 is an intra-finish gate;
it cannot catch duplication between two otherwise high-scoring finishes.  This
script therefore compares paint and combined-spec halves independently after
removing color information, and also checks every shipped picker against the
accepted evidence image that promoted it.

It is deliberately diagnostic by default.  Pass ``--fail`` to make excessive
cross-card similarity a release-gate failure after the current rebuild lane has
been adjudicated and the threshold has been locked.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Iterable

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = ROOT / "thumbnails" / "picker_split" / "base"
EVIDENCE_ROOT = ROOT / "_iridescent_insects_2026"
CATALOG_PATH = ROOT / "paint-booth-0-finish-data.js"


ACCEPTED_EVIDENCE = {
    "beetle_buprestid": "beetle_buprestid_i2_p4",
    "beetle_click": "beetle_click_i2_p4_perf",
    "butterfly_emperor": "butterfly_emperor_i2_p3_perf",
    "butterfly_glasswing": "butterfly_glasswing_i2_p3",
    "beetle_ground": "beetle_ground_i2_p5_perf",
    "beetle_longhorn": "beetle_longhorn_i2_p2",
    "moth_owl": "moth_owl_i1_p3",
    "butterfly_peacock": "butterfly_peacock_i2_p4",
    "beetle_rose_chafer": "beetle_rose_chafer_i2_p4_perf",
    "beetle_tiger": "beetle_tiger_i2_p3_perf",
    "moth_tiger": "moth_tiger_i1_p2",
    "cicada_membrane": "cicada_membrane_i1_p5",
}


def _catalog_ids() -> list[str]:
    """Read the live shelf so new cards cannot silently escape the gate."""
    # The legacy catalog contains a few preserved single-byte Windows glyphs;
    # latin-1 is the lossless byte-to-text bridge for our ASCII-only anchors.
    text = CATALOG_PATH.read_text(encoding="latin-1")
    block = re.search(
        r'const _SPECIALS_IRIDESCENT_INSECTS\s*=\s*\{.*?\[(.*?)\]',
        text,
        flags=re.DOTALL,
    )
    if not block:
        raise RuntimeError("IRIDESCENT INSECTS catalog group not found")
    ids = re.findall(r'"([a-z0-9_]+)"', block.group(1))
    if not ids:
        raise RuntimeError("IRIDESCENT INSECTS catalog group is empty")
    return ids


def _read(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def _half(image: np.ndarray, side: str) -> np.ndarray:
    midpoint = image.shape[1] // 2
    return image[:, :midpoint] if side == "paint" else image[:, midpoint:]


def _features(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.magnitude(gx, gy)
    return gray.astype(np.float32), edge


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    av = a.reshape(-1) - float(a.mean())
    bv = b.reshape(-1) - float(b.mean())
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom <= 1e-9:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.dot(av, bv) / denom)


def _similarity(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    a_gray, a_edge = _features(a)
    b_gray, b_edge = _features(b)
    gray = _corr(a_gray, b_gray)
    edge = _corr(a_edge, b_edge)
    return max(gray, edge), gray, edge


def _pairs(items: Iterable[str]) -> Iterable[tuple[str, str]]:
    ordered = list(items)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            yield left, right


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ids", nargs="*", default=None,
        help="Explicit subset; default is every ID on the live insects shelf",
    )
    parser.add_argument("--threshold", type=float, default=0.68)
    parser.add_argument(
        "--replace", action="append", default=[], metavar="ID=PNG",
        help="Audit an isolated candidate in place of its current live picker",
    )
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()

    ids = list(args.ids or _catalog_ids())
    replacement_paths: dict[str, Path] = {}
    for replacement in args.replace:
        finish_id, separator, raw_path = replacement.partition("=")
        if not separator:
            raise ValueError(f"--replace must be an ID=PNG pair: {replacement}")
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        replacement_paths[finish_id] = path
        if finish_id not in ids:
            ids.append(finish_id)
    live = {
        finish_id: _read(replacement_paths.get(finish_id, LIVE_ROOT / f"{finish_id}.png"))
        for finish_id in ids
    }
    replaced = set(replacement_paths)

    print("LIVE-TO-ACCEPTED EVIDENCE (spec half; 1.000 means identical structure)")
    for finish_id in ids:
        if finish_id in replaced:
            print(f"  {finish_id:28s} isolated replacement (evidence check skipped)")
            continue
        evidence_name = ACCEPTED_EVIDENCE.get(finish_id)
        if not evidence_name:
            print(f"  {finish_id:28s} no evidence mapping")
            continue
        evidence = _read(EVIDENCE_ROOT / evidence_name / "picker_split.png")
        score, gray, edge = _similarity(
            _half(live[finish_id], "spec"), _half(evidence, "spec")
        )
        print(f"  {finish_id:28s} score={score:.3f} gray={gray:.3f} edge={edge:.3f}")

    breaches: list[tuple[float, str, str, str, float, float]] = []
    print("\nCROSS-CARD COLOR-INVARIANT SIMILARITY")
    for side in ("paint", "spec"):
        rows = []
        for left, right in _pairs(ids):
            score, gray, edge = _similarity(
                _half(live[left], side), _half(live[right], side)
            )
            rows.append((score, left, right, gray, edge))
            if score >= args.threshold:
                breaches.append((score, side, left, right, gray, edge))
        print(f"  [{side.upper()}]")
        for score, left, right, gray, edge in sorted(rows, reverse=True)[:15]:
            marker = " BREACH" if score >= args.threshold else ""
            print(
                f"    {score:.3f} {left:24s} {right:24s} "
                f"gray={gray:.3f} edge={edge:.3f}{marker}"
            )

    print(f"\nthreshold={args.threshold:.3f} breaches={len(breaches)}")
    if args.fail and breaches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
