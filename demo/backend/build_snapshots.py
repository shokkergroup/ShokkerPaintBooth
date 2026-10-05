"""Build-time exporter for reviewed SHOKK DEMO material snapshots.

This is the *only* demo module permitted to load the paid renderer.  Run it in
the source repository before staging Electron.  The generated ``.npz`` files
are then consumed by :mod:`demo.backend.compositor`, whose import graph has no
paid-engine dependency.

Typical release build::

    python -m demo.backend.build_snapshots --size 2048 --force
    python -m demo.backend.build_snapshots --verify --min-size 1024
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Iterable

import numpy as np
from PIL import Image

from .catalog import DemoCatalog
from .compositor import SNAPSHOT_SCHEMA


BACKEND_DIR = Path(__file__).resolve().parent
DEMO_DIR = BACKEND_DIR.parent
REPO_ROOT = DEMO_DIR.parent
DEFAULT_MANIFEST = DEMO_DIR / "product-manifest.json"
DEFAULT_OUTPUT = BACKEND_DIR / "assets" / "snapshots"
DEFAULT_THUMBNAILS = BACKEND_DIR / "assets" / "thumbnails"
# Demo cards use the same truthful picker contract as the full application:
# one square showing authored paint beside one square showing the literal
# combined spec RGB (R=metal, G=roughness, B=clearcoat).  ``THUMBNAIL_SIZE``
# remains the total asset width advertised by the demo manifest.
THUMBNAIL_SIZE = 384
THUMBNAIL_TILE_SIZE = THUMBNAIL_SIZE // 2
THUMBNAIL_DIMENSIONS = (THUMBNAIL_SIZE, THUMBNAIL_TILE_SIZE)


class SnapshotBuildError(RuntimeError):
    pass


def _load_paid_engine(repo_root: Path):
    """Import the full renderer only inside the explicit build-time command."""

    repo_text = str(repo_root.resolve())
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    # Do not move this import to module scope.  Shipping runtime modules never
    # call this function and the stage contains snapshots, not the paid source.
    return importlib.import_module("shokker_engine_v2")


def _read_rgb(path: Path) -> np.ndarray:
    if not path.is_file():
        raise SnapshotBuildError(f"Expected renderer output is missing: {path}")
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _read_spec(path: Path) -> np.ndarray:
    if not path.is_file():
        raise SnapshotBuildError(f"Expected renderer output is missing: {path}")
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("RGBA"), dtype=np.uint8)[:, :, :3]


def _renderer_zone(engine: Any, finish_id: str, manifest_kind: str, size: int = 2048) -> dict[str, Any]:
    in_bases = finish_id in getattr(engine, "BASE_REGISTRY", {})
    in_monos = finish_id in getattr(engine, "MONOLITHIC_REGISTRY", {})
    if not in_bases and not in_monos:
        raise SnapshotBuildError(f"Paid renderer has no registered finish {finish_id!r}")

    # [SPB-DEMO-PARITY 2026-09-03 — owner: "it just needs to work exactly like the main app"]
    # The old exact-RGB colour pick made the selector, not the finish, decide what got
    # captured: fs_core_emerald baked FLAT through it (paint std 0.00, spec std 0.00 at
    # every plate level and canvas size), while the same finish over the same plate with
    # forced full coverage renders with its real structure (paint std 11.47, spec std
    # 100.89).  A whole-canvas region mask is what the paid app's "Remaining" zone
    # actually gives the finish, so capture through that instead.
    common: dict[str, Any] = {
        "name": f"SHOKK DEMO snapshot: {finish_id}",
        "region_mask": np.ones((size, size), dtype=np.float32),
        "apply_area_shape_only": True,
        "intensity": 100,
        "base_strength": 1.0,
        "base_spec_strength": 1.0,
        "base_color": [1.0, 1.0, 1.0],
    }
    # Prefer the manifest's picker path when both registries expose an alias.
    if manifest_kind == "base" and in_bases:
        common.update({"base": finish_id, "pattern": "none", "base_color_mode": "source"})
        # Owner 2026-09-02: picker cards must show the FINISH beside its real
        # SPEC.  A blanket solid-color override flattened every authored base
        # paint_fn (Lava Lamp, Cherry Polka, insects, etc.) to gray.  Match the
        # paid picker's truthful contract: material-only foundations retain the
        # neutral plate, while non-noop paint renderers use their authored field.
        entry = getattr(engine, "BASE_REGISTRY", {}).get(finish_id) or {}
        paint_fn = entry.get("paint_fn") if isinstance(entry, dict) else None
        if paint_fn is not None:
            is_noop = getattr(engine, "_base_paint_fn_is_noop", None)
            try:
                authored = not bool(is_noop(paint_fn)) if callable(is_noop) else True
            except Exception:
                authored = True
            if authored:
                common["base_color_mode"] = "authored_swatch"
    elif in_monos:
        common["finish"] = finish_id
        common["base_color_mode"] = "authored_swatch"
        try:
            from finish_colors_lookup import get_finish_colors

            finish_colors = get_finish_colors(finish_id)
            if finish_colors:
                common["finish_colors"] = finish_colors
        except Exception:
            pass
    else:
        common.update({"base": finish_id, "pattern": "none", "base_color_mode": "source"})
    return common


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _square_field(field: np.ndarray) -> np.ndarray:
    image = Image.fromarray(field)
    edge = min(image.size)
    left = (image.width - edge) // 2
    top = (image.height - edge) // 2
    # BOX integrates fine authored marks honestly when shrinking the 2048px
    # snapshots to card size.  LANCZOS ringing made tiny spec flecks look like
    # features that were not present in the material field.
    resampling = (
        Image.Resampling.BOX
        if edge >= THUMBNAIL_TILE_SIZE
        else Image.Resampling.LANCZOS
    )
    return np.asarray(
        image.crop((left, top, left + edge, top + edge)).resize(
            (THUMBNAIL_TILE_SIZE, THUMBNAIL_TILE_SIZE), resampling
        ),
        dtype=np.uint8,
    )


def _write_thumbnail(paint: np.ndarray, spec: np.ndarray, destination: Path) -> None:
    """Write literal PAINT | COMBINED SPEC fields with no simulated lighting.

    The previous demo thumbnail pass painted the same diagonal Gaussian shine
    across every card.  Besides inventing a feature not present in any finish,
    it obscured subtle authored paint and made unrelated materials look alike.
    These two halves are now direct, deterministic reductions of the reviewed
    snapshot fields, matching the full application's buyer-facing contract.
    """

    paint_field = _square_field(paint)
    spec_field = _square_field(spec)
    combined = np.concatenate((paint_field, spec_field), axis=1)
    image = Image.fromarray(combined, mode="RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".png.tmp")
    with temporary.open("wb") as handle:
        image.save(handle, "PNG", optimize=True)
    os.replace(temporary, destination)


def _validate_renderer_changed_plate(
    finish_id: str, paint: np.ndarray, spec: np.ndarray
) -> None:
    """Reject a successful-looking paid render that skipped the finish."""

    neutral_paint = np.array([128, 128, 128], dtype=np.uint8)
    neutral_spec = np.array([5, 100, 16], dtype=np.uint8)
    if np.all(paint == neutral_paint) and np.all(spec == neutral_spec):
        raise SnapshotBuildError(
            f"Paid renderer produced unchanged neutral fields for {finish_id}; "
            "the build selector or registry route did not apply"
        )


def _color_source_field(engine: Any, finish_id: str, size: int) -> np.ndarray:
    """Capture the finish exactly as the paid app builds a "From special" base colour.

    engine/compose.py:_invoke_base_paint_fn_for_color_source calls the finish's paint_fn
    over ``_mono_overlay_seed_paint`` — a flat 0.533 plate — at ``seed + 4242`` with a
    full-canvas mask.  That role never sees the customer's art, so one capture is exact.
    Falls back to the neutral material capture when a finish exposes no callable paint_fn.
    """

    shape = (size, size)
    seed_paint = np.full((size, size, 3), 0.533, dtype=np.float32)
    mask = np.ones(shape, dtype=np.float32)
    paint_fn = None
    monos = getattr(engine, "MONOLITHIC_REGISTRY", {})
    if finish_id in monos:
        entry = monos[finish_id]
        paint_fn = entry[1] if isinstance(entry, (tuple, list)) and len(entry) > 1 else None
    if paint_fn is None:
        entry = getattr(engine, "BASE_REGISTRY", {}).get(finish_id) or {}
        paint_fn = entry.get("paint_fn") if isinstance(entry, dict) else None
    if paint_fn is None:
        return np.zeros((size, size, 3), dtype=np.uint8)
    try:
        raw = paint_fn(seed_paint.copy(), shape, mask, 51 + 4242, 1.0, 0.0)
    except Exception as exc:  # a finish with a different arity is not a build failure
        print(f"[shokk-demo] colour-source capture skipped for {finish_id}: {exc}")
        return np.zeros((size, size, 3), dtype=np.uint8)
    if raw is None:
        return np.zeros((size, size, 3), dtype=np.uint8)
    field = np.asarray(raw, dtype=np.float32)[:, :, :3]
    return np.clip(field * 255.0, 0, 255).astype(np.uint8)


def _capture_preview_size(
    engine: Any,
    finish_id: str,
    kind: str,
    size: int,
    temporary: Path,
    position: int,
) -> dict[str, np.ndarray] | None:
    """Capture the finish natively at the live-preview resolution.

    [SPB-DEMO-PREVIEW 2026-09-03 — owner: "if the MAIN APP colors look one way on the LIVE
    PREVIEW the DEMO should look EXACTLY the same"] The paid app previews at
    LIVE_PREVIEW_MAX_SCALE = 0.5 by re-running the renderer, and its 1024 output is not its
    2048 render downscaled — the two are 10.06/255 apart from each other.  Downscaling the
    2048 capture left the demo preview 9.48/255 from the paid preview with half the detail;
    a native capture at the same size takes that to 1.70.
    """

    preview_size = int(size) // 2
    if preview_size < 256:
        return None
    plate_dir = temporary / f"preview_{position:02d}_{finish_id}"
    plate_dir.mkdir(parents=True, exist_ok=True)

    def render(level: int, tag: str) -> tuple[np.ndarray, np.ndarray]:
        source = plate_dir / f"{tag}.tga"
        Image.new("RGB", (preview_size, preview_size), (level, level, level)).save(source, "TGA")
        out_dir = plate_dir / tag
        out_dir.mkdir(parents=True, exist_ok=True)
        engine.build_multi_zone(
            str(source),
            str(out_dir),
            [_renderer_zone(engine, finish_id, kind, preview_size)],
            iracing_id="00000",
            seed=51,
            save_debug_images=False,
            car_prefix="car_num",
            preview_mode=False,
        )
        return (
            _read_rgb(out_dir / "car_num_00000.tga"),
            _read_spec(out_dir / "car_spec_00000.tga"),
        )

    try:
        paint, spec = render(128, "neutral")
        paint_lo, spec_lo = render(0, "low")
        paint_hi, spec_hi = render(255, "high")
    except Exception as exc:
        print(f"[shokk-demo] preview-size capture skipped for {finish_id}: {exc}")
        return None
    fields = {
        "paint": paint,
        "spec": spec,
        "paint_lo": paint_lo,
        "paint_hi": paint_hi,
        "color_src": _color_source_field(engine, finish_id, preview_size),
    }
    if float(np.abs(spec_hi.astype(np.int16) - spec_lo.astype(np.int16)).max()) > 1.0:
        fields["spec_lo"] = spec_lo
        fields["spec_hi"] = spec_hi
    return fields


def _validate_capture_has_structure(
    finish_id: str,
    paint: np.ndarray,
    paint_lo: np.ndarray,
    paint_hi: np.ndarray,
    spec: np.ndarray,
) -> None:
    """Reject a capture that carries no detail at all.

    [SPB-DEMO-PARITY 2026-09-03] ``_validate_renderer_changed_plate`` only ever compared
    against an exact 128/(5,100,16) match, and every real render returns 127 — so it had
    never rejected anything, and fs_core_emerald shipped as a single flat colour in both
    its paint AND its spec.  "Did the pixels change" is not the question; "does the field
    carry any structure" is.  A finish may legitimately be flat in ONE channel set (the
    material-only foundations are flat paint over a live spec), but a capture that is flat
    in paint AND spec AND unresponsive to the source plates rendered nothing.
    """

    def spatial(field: np.ndarray) -> float:
        return float(min(field[:, :, channel].std() for channel in range(3)))

    responds = float(np.abs(paint_hi.astype(np.int16) - paint_lo.astype(np.int16)).max())
    if spatial(paint) < 0.5 and spatial(spec) < 0.5 and responds < 1.0:
        raise SnapshotBuildError(
            f"{finish_id}: capture is a flat constant in paint and spec and does not respond "
            f"to the source plates — the finish rendered nothing"
        )


def export_snapshots(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT,
    thumbnail_dir: Path = DEFAULT_THUMBNAILS,
    repo_root: Path = REPO_ROOT,
    size: int = 2048,
    force: bool = False,
    refresh_thumbnails: bool = False,
    only: Iterable[str] | None = None,
) -> dict[str, Any]:
    if size < 256 or size > 4096:
        raise SnapshotBuildError("Snapshot size must be between 256 and 4096")
    catalog = DemoCatalog(manifest_path)
    selected_ids = list(only or catalog.finishes.keys())
    unknown = [finish_id for finish_id in selected_ids if finish_id not in catalog.finishes]
    if unknown:
        raise SnapshotBuildError(f"Unknown manifest finish ids: {', '.join(unknown)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    # Keep thumbnail-only refreshes isolated from (and fast despite) the paid
    # renderer.  The engine is imported lazily only when a snapshot must be
    # rendered, never when existing reviewed arrays are merely repackaged.
    engine = None
    built = []
    skipped = []
    refreshed_thumbnails = []
    failures = []
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="shokk_demo_snapshot_") as temporary_text:
        temporary = Path(temporary_text)
        neutral_path = temporary / "neutral_source.tga"
        Image.new("RGB", (size, size), (128, 128, 128)).save(neutral_path, "TGA")
        # Two source plates bracket the finish's response to the customer's own art.
        low_path = temporary / "plate_low.tga"
        high_path = temporary / "plate_high.tga"
        Image.new("RGB", (size, size), (0, 0, 0)).save(low_path, "TGA")
        Image.new("RGB", (size, size), (255, 255, 255)).save(high_path, "TGA")

        for position, finish_id in enumerate(selected_ids, 1):
            destination = output_dir / f"{finish_id}.npz"
            if destination.is_file() and not force:
                thumbnail_path = thumbnail_dir / f"{finish_id}.png"
                if refresh_thumbnails or not thumbnail_path.is_file():
                    with np.load(destination, allow_pickle=False) as payload:
                        _write_thumbnail(
                            np.asarray(payload["paint"], dtype=np.uint8),
                            np.asarray(payload["spec"], dtype=np.uint8),
                            thumbnail_path,
                        )
                    refreshed_thumbnails.append(finish_id)
                skipped.append(finish_id)
                continue
            finish = catalog.finishes[finish_id]
            render_dir = temporary / f"render_{position:02d}_{finish_id}"
            render_dir.mkdir(parents=True, exist_ok=True)
            try:
                if engine is None:
                    engine = _load_paid_engine(repo_root)
                def _capture(source_path: Path, tag: str) -> tuple[np.ndarray, np.ndarray]:
                    out_dir = render_dir / tag
                    out_dir.mkdir(parents=True, exist_ok=True)
                    engine.build_multi_zone(
                        str(source_path),
                        str(out_dir),
                        [_renderer_zone(engine, finish_id, finish.kind, size)],
                        iracing_id="00000",
                        seed=51,
                        save_debug_images=False,
                        car_prefix="car_num",
                        preview_mode=False,
                    )
                    return (
                        _read_rgb(out_dir / "car_num_00000.tga"),
                        _read_spec(out_dir / "car_spec_00000.tga"),
                    )

                paint, spec = _capture(neutral_path, "neutral")
                paint_lo, spec_lo = _capture(low_path, "low")
                paint_hi, spec_hi = _capture(high_path, "high")
                # [SPB-DEMO-PREVIEW 2026-09-03] Also capture at the live-preview resolution.
                # The paid app previews by re-running the renderer at half scale, and the
                # engine's 1024 output is NOT its 2048 render downscaled (10.06/255 apart
                # from itself), so a downscaled 2048 capture can never match the preview.
                preview_fields = _capture_preview_size(
                    engine, finish_id, finish.kind, size, temporary, position
                )
                # Most spec_fns never see the source paint, so one capture is exact and a
                # response pair would just double the payload.  A few finishes DO vary
                # (beetle_ground drifted 13.2/255, cherry_polka 5.7/255 against the engine
                # on a single capture) — store the pair only for those.
                spec_responds = (
                    float(np.abs(spec_hi.astype(np.int16) - spec_lo.astype(np.int16)).max()) > 1.0
                )
                color_src = _color_source_field(engine, finish_id, size)
                for label, field in (
                    ("paint", paint), ("spec", spec), ("paint_lo", paint_lo), ("paint_hi", paint_hi)
                ):
                    if field.shape != (size, size, 3):
                        raise SnapshotBuildError(
                            f"Unexpected snapshot shape for {finish_id}.{label}: {field.shape}"
                        )
                _validate_renderer_changed_plate(finish_id, paint, spec)
                _validate_capture_has_structure(finish_id, paint, paint_lo, paint_hi, spec)
                spec_response = (
                    {"spec_lo": spec_lo, "spec_hi": spec_hi} if spec_responds else {}
                )
                if preview_fields is not None:
                    preview_destination = output_dir / f"{finish_id}@{size // 2}.npz"
                    preview_tmp = preview_destination.with_suffix(".npz.tmp")
                    with preview_tmp.open("wb") as handle:
                        np.savez_compressed(
                            handle,
                            schema=np.array(SNAPSHOT_SCHEMA),
                            finish_id=np.array(finish_id),
                            build_size=np.array([size // 2, size // 2], dtype=np.int32),
                            seed=np.array(51, dtype=np.int32),
                            **preview_fields,
                        )
                    os.replace(preview_tmp, preview_destination)
                temporary_output = destination.with_suffix(".npz.tmp")
                with temporary_output.open("wb") as handle:
                    np.savez_compressed(
                        handle,
                        **spec_response,
                        schema=np.array(SNAPSHOT_SCHEMA),
                        finish_id=np.array(finish_id),
                        build_size=np.array([size, size], dtype=np.int32),
                        seed=np.array(51, dtype=np.int32),
                        paint=paint,
                        spec=spec,
                        paint_lo=paint_lo,
                        paint_hi=paint_hi,
                        color_src=color_src,
                    )
                os.replace(temporary_output, destination)
                thumbnail_path = thumbnail_dir / f"{finish_id}.png"
                _write_thumbnail(paint, spec, thumbnail_path)
                built.append(
                    {
                        "id": finish_id,
                        "bytes": destination.stat().st_size,
                        "sha256": _sha256_file(destination),
                        "thumbnail": str(thumbnail_path.resolve()),
                    }
                )
            except Exception as exc:
                destination.unlink(missing_ok=True)
                failures.append({"id": finish_id, "error": str(exc)})

    report = {
        "schema": "spb-demo-snapshot-build-report/1",
        "manifest": str(Path(manifest_path).resolve()),
        "output_dir": str(Path(output_dir).resolve()),
        "thumbnail_dir": str(Path(thumbnail_dir).resolve()),
        "size": size,
        "built": built,
        "skipped": skipped,
        "refreshed_thumbnails": refreshed_thumbnails,
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    report_path = output_dir / "snapshot-build-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if failures:
        raise SnapshotBuildError(
            "Snapshot export failed for: " + ", ".join(item["id"] for item in failures)
        )
    return report


def verify_snapshots(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    output_dir: Path = DEFAULT_OUTPUT,
    thumbnail_dir: Path = DEFAULT_THUMBNAILS,
    min_size: int = 1024,
) -> dict[str, Any]:
    catalog = DemoCatalog(manifest_path)
    errors = []
    verified = []
    for finish_id in catalog.finishes:
        path = output_dir / f"{finish_id}.npz"
        if not path.is_file():
            errors.append(f"missing {finish_id}.npz")
            continue
        try:
            with np.load(path, allow_pickle=False) as payload:
                schema = str(np.asarray(payload["schema"]).item())
                embedded_id = str(np.asarray(payload["finish_id"]).item())
                paint = np.asarray(payload["paint"])
                spec = np.asarray(payload["spec"])
            if schema != SNAPSHOT_SCHEMA:
                errors.append(f"{finish_id}: wrong schema {schema!r}")
            elif embedded_id != finish_id:
                errors.append(f"{finish_id}: embedded id is {embedded_id!r}")
            elif paint.ndim != 3 or spec.ndim != 3 or paint.shape[2] != 3 or spec.shape[2] != 3:
                errors.append(f"{finish_id}: fields must be HxWx3")
            elif min(paint.shape[0], paint.shape[1], spec.shape[0], spec.shape[1]) < min_size:
                errors.append(f"{finish_id}: snapshot is smaller than {min_size}px")
            elif paint.shape[:2] != spec.shape[:2]:
                errors.append(f"{finish_id}: paint/spec dimensions differ")
            else:
                verified.append(finish_id)
        except Exception as exc:
            errors.append(f"{finish_id}: {exc}")
    for finish in catalog.visible:
        thumbnail = thumbnail_dir / f"{finish.id}.png"
        if not thumbnail.is_file():
            errors.append(f"missing thumbnail {finish.id}.png")
            continue
        try:
            with Image.open(thumbnail) as image:
                image.load()
                if image.format != "PNG" or image.size != THUMBNAIL_DIMENSIONS:
                    errors.append(
                        f"{finish.id}: thumbnail must be PNG "
                        f"{THUMBNAIL_DIMENSIONS[0]}x{THUMBNAIL_DIMENSIONS[1]}"
                    )
        except Exception as exc:
            errors.append(f"{finish.id}: invalid thumbnail: {exc}")
    result = {
        "ok": not errors and len(verified) == len(catalog.finishes),
        "expected": len(catalog.finishes),
        "verified": len(verified),
        "errors": errors,
        "min_size": min_size,
    }
    if not result["ok"]:
        raise SnapshotBuildError("Snapshot release gate failed: " + "; ".join(errors))
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--thumbnail-output", type=Path, default=DEFAULT_THUMBNAILS)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--refresh-thumbnails",
        action="store_true",
        help="Rewrite literal paint/spec card assets from existing snapshots without rerendering",
    )
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--min-size", type=int, default=1024)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.verify:
            result = verify_snapshots(
                manifest_path=args.manifest.resolve(),
                output_dir=args.output.resolve(),
                thumbnail_dir=args.thumbnail_output.resolve(),
                min_size=args.min_size,
            )
        else:
            result = export_snapshots(
                manifest_path=args.manifest.resolve(),
                output_dir=args.output.resolve(),
                thumbnail_dir=args.thumbnail_output.resolve(),
                repo_root=args.repo_root.resolve(),
                size=args.size,
                force=args.force,
                refresh_thumbnails=args.refresh_thumbnails,
                only=args.only or None,
            )
        print(json.dumps(result, indent=2))
        return 0
    except SnapshotBuildError as exc:
        print(f"SHOKK DEMO snapshot gate failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
