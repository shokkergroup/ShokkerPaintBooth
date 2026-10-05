"""Gate and stage all 110 Fractured Wilds real-engine metric thumbnails.

SPB-WILDS tick 5 (2026-08-23). Owner verdict: "Too much redundancy way
too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color
flipping stuff." The bake is staged under ``_wilds_work`` and only copied to
the root monolithic thumbnail tree after every image is non-flat and every
exact RGB hash is unique. Buyer-facing ``picker_split`` snapshots are rebuilt
separately through ``rebuild_picker_swatches.py`` after this gate passes.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import uuid
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_release_gate import canonical_wilds_110
from scripts.spb_wilds_quality_release_lock import (
    DEFAULT_MANIFEST as QUALITY_RELEASE_MANIFEST,
    QualityReleaseBlocked,
    validate_quality_release_manifest,
)

STAGE_PARENT = ROOT / "_wilds_work"
REPORT = ROOT / "_wilds_work" / "wilds_110_thumbnail_gate.json"
MONOLITHIC_CARD_SIZE = 256


def _install_and_ids():
    return canonical_wilds_110()


def _prepare_unique_stage(parent: Path = STAGE_PARENT) -> Path:
    """Create a new empty stage so output from any prior run is unreachable."""
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="wilds_110_bake_", dir=str(parent)))
    if any(stage.iterdir()):
        raise RuntimeError(f"Fresh Wilds stage was unexpectedly non-empty: {stage}")
    return stage


def _run_current_bake(baker, fid: str, stage: Path) -> Path:
    """Run one baker invocation and prove its output/manifest are from this call."""
    output = stage / "monolithic" / f"{fid}.png"
    manifest_path = stage / "rebuild_manifest.json"
    # Redundant with the unique stage by design: this keeps the helper safe if
    # it is ever retried within the same stage and makes stale-output rejection
    # an explicit invariant rather than an assumption.
    output.unlink(missing_ok=True)
    manifest_path.unlink(missing_ok=True)
    original_argv = list(sys.argv)
    captured = io.StringIO()
    try:
        sys.argv = [
            "rebuild_thumbnails.py", "--type", "monolithic", "--key", fid,
            "--size", str(MONOLITHIC_CARD_SIZE), "--output", str(stage), "--quiet",
        ]
        # The legacy builder still emits the full engine banner in --quiet
        # mode. Keep this release command bounded, retaining a diagnostic tail
        # only when a current invocation fails.
        with redirect_stdout(captured), redirect_stderr(captured):
            result = baker.main()
    except SystemExit as exc:
        result = exc.code
    except Exception as exc:
        tail = captured.getvalue()[-2000:]
        raise RuntimeError(f"{fid}: thumbnail baker crashed: {exc}; output tail={tail!r}") from exc
    finally:
        sys.argv = original_argv
    if result not in (None, 0):
        tail = captured.getvalue()[-2000:]
        raise RuntimeError(f"{fid}: thumbnail baker exited {result!r}; output tail={tail!r}")
    if not manifest_path.is_file():
        raise RuntimeError(f"{fid}: current bake did not write rebuild_manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{fid}: current bake manifest is unreadable: {exc}") from exc
    expected_key = f"monolithic/{fid}"
    if manifest.get("ok") != [expected_key] or manifest.get("fail"):
        raise RuntimeError(
            f"{fid}: current bake did not report exactly one success: {manifest}"
        )
    if not output.is_file():
        raise RuntimeError(f"{fid}: current bake did not create a fresh PNG")
    return output


def _promote_after_all_gates(ids: list[str], source_dir: Path, target_dir: Path) -> None:
    """Promote the complete set transactionally, rolling back partial failure."""
    target_dir.mkdir(parents=True, exist_ok=True)
    transaction = target_dir / f".wilds110-promote-{uuid.uuid4().hex}"
    incoming = transaction / "incoming"
    backup = transaction / "backup"
    incoming.mkdir(parents=True)
    backup.mkdir()

    try:
        for fid in ids:
            source = source_dir / f"{fid}.png"
            if not source.is_file():
                raise RuntimeError(f"Promotion source vanished before commit: {source}")
            staged_copy = incoming / source.name
            shutil.copy2(source, staged_copy)
            if hashlib.sha256(staged_copy.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
                raise RuntimeError(f"Promotion staging hash mismatch: {fid}")
            existing = target_dir / source.name
            if existing.is_file():
                shutil.copy2(existing, backup / source.name)

        replaced: list[str] = []
        try:
            for fid in ids:
                os.replace(incoming / f"{fid}.png", target_dir / f"{fid}.png")
                replaced.append(fid)
        except Exception as exc:
            rollback_errors = []
            for fid in reversed(replaced):
                destination = target_dir / f"{fid}.png"
                prior = backup / f"{fid}.png"
                try:
                    if prior.is_file():
                        os.replace(prior, destination)
                    else:
                        destination.unlink(missing_ok=True)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{fid}: {rollback_exc}")
            suffix = f"; rollback errors={rollback_errors}" if rollback_errors else ""
            raise RuntimeError(f"Wilds promotion failed and was rolled back: {exc}{suffix}") from exc
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def _write_report(report: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_name(f"{REPORT.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, REPORT)


def _contact_sheet(ids: list[str], source_dir: Path, target: Path) -> None:
    columns, cell_w, cell_h = 10, 144, 154
    rows = (len(ids) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (15, 18, 23))
    draw = ImageDraw.Draw(sheet)
    for index, fid in enumerate(ids):
        image = Image.open(source_dir / f"{fid}.png").convert("RGB")
        image.thumbnail((128, 128), Image.Resampling.LANCZOS)
        x = (index % columns) * cell_w + 8
        y = (index // columns) * cell_h + 4
        sheet.paste(image, (x, y))
        draw.text((x, y + 132), fid, fill=(224, 230, 238))
    sheet.save(target)


def main() -> int:
    from engine.registry import MONOLITHIC_REGISTRY

    lanes, ids = _install_and_ids()
    try:
        validate_quality_release_manifest(
            QUALITY_RELEASE_MANIFEST, ids, registry=MONOLITHIC_REGISTRY,
        )
    except (OSError, TypeError, QualityReleaseBlocked) as exc:
        print(f"[wilds-110-bake] QUALITY RELEASE LOCKED: {exc}", flush=True)
        return 1
    import rebuild_thumbnails as baker

    stage = _prepare_unique_stage()
    output_dir = stage / "monolithic"
    rows: list[dict] = []
    failures: list[str] = []
    for index, fid in enumerate(ids, 1):
        try:
            path = _run_current_bake(baker, fid, stage)
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                failures.append(f"{fid}: missing PNG")
                continue
            std = float(image.std())
            unique_rgb = int(np.unique(image.reshape(-1, 3), axis=0).shape[0])
            rgb_digest = hashlib.sha256(
                np.ascontiguousarray(image).tobytes()
            ).hexdigest()
            file_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append({
                "id": fid,
                "rgbStd": round(std, 6),
                "uniqueRgb": unique_rgb,
                "rgbSha256": rgb_digest,
                "fileSha256": file_digest,
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
            })
            if image.shape[:2] != (MONOLITHIC_CARD_SIZE, MONOLITHIC_CARD_SIZE) or std < 4.0 or unique_rgb <= 1:
                failures.append(
                    f"{fid}: shape={image.shape[:2]} std={std:.4f} unique={unique_rgb}"
                )
            print(f"[wilds-110-bake] {index:03d}/110 {fid} std={std:.2f}", flush=True)
        except Exception as exc:
            failures.append(str(exc))
            print(f"[wilds-110-bake] {index:03d}/110 FAIL {fid}: {exc}", flush=True)

    hashes = [row["rgbSha256"] for row in rows]
    duplicate_hashes = sorted({digest for digest in hashes if hashes.count(digest) > 1})
    if duplicate_hashes:
        failures.append(f"{len(duplicate_hashes)} duplicate exact RGB thumbnail hash(es)")

    report = {
        "schema": 2,
        "ticket": "SPB-WILDS 2026-08-23 tick 5",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "scope": {name: len(values) for name, values in lanes.items()},
        "count": len(rows),
        "allNonFlat": not failures and len(rows) == 110,
        "allExactHashesUnique": not duplicate_hashes and len(hashes) == 110,
        "exactHashBasis": (
            f"decoded {MONOLITHIC_CARD_SIZE}x{MONOLITHIC_CARD_SIZE} uint8 BGR "
            "pixel bytes (no PNG encoding/metadata)"
        ),
        "minimumRgbStd": min((row["rgbStd"] for row in rows), default=None),
        "minimumUniqueRgb": min((row["uniqueRgb"] for row in rows), default=None),
        "failures": failures,
        "stage": str(stage.relative_to(ROOT)).replace("\\", "/"),
        "promotionState": "blocked",
        "publishedToRoot": False,
        "finishes": rows,
    }
    if not failures and len(rows) == 110:
        try:
            contact = stage / "wilds_110_real_engine_contact.png"
            _contact_sheet(ids, output_dir, contact)
            report["contactSheet"] = str(contact.relative_to(ROOT)).replace("\\", "/")
            quality = validate_quality_release_manifest(
                QUALITY_RELEASE_MANIFEST,
                ids,
                registry=MONOLITHIC_REGISTRY,
            )
            report["qualityReleaseLock"] = {
                "status": quality["status"],
                "ownerAccepted": quality["owner_accepted"],
                "productionWired": quality["production_wired"],
                "manifestSha256": quality["manifest_sha256"],
                "reviewBundleSha256": quality["review_bundle_sha256"],
            }
            report["promotionState"] = "all-gates-passed; promotion-pending"
            _write_report(report)
            _promote_after_all_gates(ids, output_dir, ROOT / "thumbnails" / "monolithic")
            report["promotionState"] = "committed"
            report["publishedToRoot"] = True
        except Exception as exc:
            failures.append(str(exc))
            report["failures"] = failures
            report["promotionState"] = "failed; prior root set restored"
    _write_report(report)
    if failures or len(rows) != 110:
        print(f"[wilds-110-bake] FAIL: {failures}", flush=True)
        return 1
    print("[wilds-110-bake] PASS: 110/110 non-flat, exact hashes unique", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
