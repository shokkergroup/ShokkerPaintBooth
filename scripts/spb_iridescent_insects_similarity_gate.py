"""Cross-card visual-similarity audit for IRIDESCENT INSECTS.

The owner's 2026-09-01 review found that several live picker cards looked like
palette swaps of the same diagonal-wave carrier.  M7 is an intra-finish gate;
it cannot catch duplication between two otherwise high-scoring finishes.  This
script therefore compares paint and combined-spec halves independently after
removing color information, and also checks every shipped picker against the
accepted evidence image that promoted it. The copy detector is deliberately
invariant to palette, M/R/Cc channel order, cyclic phase shifts, flips and 90°
rotations: none of those operations creates a new design.

It is deliberately diagnostic by default.  Pass ``--fail`` to make excessive
cross-card similarity a release-gate failure after the current rebuild lane has
been adjudicated and the threshold has been locked.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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
    "firefly_ember": "firefly_ember_i1_p2",
    "ant_velvet": "ant_velvet_i1_p3",
    "mantis_orchid": "mantis_orchid_i1_p4",
    "mantis_leaf": "mantis_leaf_i1_p6",
    "katydid_leafglass": "katydid_leafglass_i1_p4",
    "stick_insect_bark": "stick_insect_bark_i1_p2",
    "cockroach_onyx": "cockroach_onyx_i1_p12",
    "weevil_opal": "weevil_opal_i1_p4",
    "weevil_gilded": "weevil_gilded_i1_p4",
    "scarab_sunplate": "scarab_sunplate_i1_p4",
    "scarab_night": "scarab_night_i1_p6",
    "jewel_spider": "jewel_spider_i1_p2",
    "orb_weaver_silk": "orb_weaver_silk_i1_p3",
    "praying_mantis_verdigris": "praying_mantis_verdigris_i1_p6",
    "hornet_titanium": "hornet_titanium_i1_p6",
    "leafcutter_copper": "leafcutter_copper_i1_p8",
    "dung_beetle_oil": "dung_beetle_oil_i1_p5",
    "bluebottle_mercury": "bluebottle_mercury_i1_p2",
    "caddiscase_river": "caddiscase_river_i1_p3",
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


def _structure(image: np.ndarray) -> np.ndarray:
    """Return a palette- and channel-invariant boundary/relief map."""
    small = cv2.resize(image, (128, 128), interpolation=cv2.INTER_AREA).astype(np.float32)
    maps = []
    for channel in cv2.split(small):
        lo, hi = np.percentile(channel, (2.0, 98.0))
        normalized = (channel - lo) / max(float(hi - lo), 1.0)
        normalized = np.clip(normalized, 0.0, 1.0).astype(np.float32)
        gx = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
        edge = cv2.magnitude(gx, gy)
        local = np.abs(normalized - cv2.GaussianBlur(normalized, (0, 0), 1.4))
        maps.append(edge + local * 2.0)
    structure = np.maximum.reduce(maps)
    return cv2.GaussianBlur(structure, (3, 3), 0).astype(np.float32)


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


def _d4_variants(image: np.ndarray) -> Iterable[np.ndarray]:
    """The eight rotations/reflections that do not create a new carrier."""
    for turns in range(4):
        rotated = np.rot90(image, turns)
        yield np.ascontiguousarray(rotated)
        yield np.ascontiguousarray(np.fliplr(rotated))


def _phase_response(a: np.ndarray, b: np.ndarray) -> float:
    """Cyclic-shift similarity for deterministic copied carriers."""
    aa = (a - float(a.mean())) / (float(a.std()) + 1e-6)
    bb = (b - float(b.mean())) / (float(b.std()) + 1e-6)
    shift, response = cv2.phaseCorrelate(aa.astype(np.float32), bb.astype(np.float32))
    dx, dy = int(round(shift[0])), int(round(shift[1]))
    aligned = max(
        _corr(aa, np.roll(bb, (dy, dx), axis=(0, 1))),
        _corr(aa, np.roll(bb, (-dy, -dx), axis=(0, 1))),
    )
    return float(np.clip(max(response, aligned), -1.0, 1.0))


@dataclass(frozen=True)
class IdentitySimilarity:
    direct: float
    gray: float
    edge: float
    transformed: float
    phased: float


def _identity_similarity(a: np.ndarray, b: np.ndarray) -> IdentitySimilarity:
    direct, gray, edge = _similarity(a, b)
    left, right = _structure(a), _structure(b)
    transformed = -1.0
    phased = -1.0
    for variant in _d4_variants(right):
        transformed = max(transformed, _corr(left, variant))
        phased = max(phased, _phase_response(left, variant))
    return IdentitySimilarity(direct, gray, edge, transformed, phased)


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
        "--copy-threshold", type=float, default=0.97,
        help="Exact-copy tolerance for palette/channel/phase/D4 transforms",
    )
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
        result = _identity_similarity(
            _half(live[finish_id], "spec"), _half(evidence, "spec")
        )
        print(
            f"  {finish_id:28s} score={result.direct:.3f} gray={result.gray:.3f} "
            f"edge={result.edge:.3f} xform={result.transformed:.3f} phase={result.phased:.3f}"
        )

    breaches: list[tuple[str, float, str, str, str]] = []
    print("\nCROSS-CARD COLOR-INVARIANT SIMILARITY")
    for side in ("paint", "spec"):
        rows = []
        for left, right in _pairs(ids):
            result = _identity_similarity(
                _half(live[left], side), _half(live[right], side)
            )
            rows.append((result.direct, left, right, result))
            if result.direct >= args.threshold:
                breaches.append(("direct", result.direct, side, left, right))
            if result.transformed >= args.copy_threshold:
                breaches.append(("transform", result.transformed, side, left, right))
            if result.phased >= args.copy_threshold:
                breaches.append(("phase", result.phased, side, left, right))
        print(f"  [{side.upper()}]")
        for score, left, right, result in sorted(rows, reverse=True)[:15]:
            copied = max(result.transformed, result.phased) >= args.copy_threshold
            marker = " BREACH" if score >= args.threshold or copied else ""
            print(
                f"    {score:.3f} {left:24s} {right:24s} "
                f"gray={result.gray:.3f} edge={result.edge:.3f} "
                f"xform={result.transformed:.3f} phase={result.phased:.3f}{marker}"
            )

    unique_breaches = {(side, left, right) for _kind, _score, side, left, right in breaches}
    print(
        f"\nthreshold={args.threshold:.3f} copy_threshold={args.copy_threshold:.3f} "
        f"breaches={len(unique_breaches)}"
    )
    for kind, score, side, left, right in sorted(breaches, key=lambda row: row[1], reverse=True):
        print(f"  {kind:9s} {score:.3f} [{side}] {left} == {right}")
    if args.fail and unique_breaches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
