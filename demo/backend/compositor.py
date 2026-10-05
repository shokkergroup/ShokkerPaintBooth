"""Generic material-snapshot compositor for SHOKK DEMO.

The shipping runtime consumes only pre-rendered ``.npz`` material fields.  It
does not know how the paid product constructs a finish.  This is intentional:
extracting the demo package reveals at most the 26 looks selected for it, not
the full renderer or catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import threading
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageOps

from .catalog import DemoCatalog, DemoFinish
from .images import decode_png_data_url, load_source_image


SNAPSHOT_SCHEMA = "spb-demo-material-snapshot/1"
NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 128, 0),
    "purple": (128, 0, 255),
    "pink": (255, 64, 160),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}


class SnapshotError(RuntimeError):
    pass


def _resized_field(field: np.ndarray, width: int, height: int) -> np.ndarray:
    """Scale a captured field to the render canvas without panning or tiling it."""

    if field.shape[0] == height and field.shape[1] == width:
        return np.asarray(field[:, :, :3], dtype=np.uint8)
    image = Image.fromarray(np.asarray(field[:, :, :3], dtype=np.uint8), mode="RGB")
    return np.asarray(image.resize((width, height), Image.Resampling.BILINEAR), dtype=np.uint8)


def _three_knot(
    low: np.ndarray, mid: np.ndarray, high: np.ndarray, source_rgb: np.ndarray
) -> np.ndarray:
    """Interpolate a captured response at the real source value, per pixel per channel.

    Knots sit at source 0 / 128 / 255.  Most finishes are linear enough that the midpoint
    is redundant, but a few are not (predicting cherry_polka's neutral capture from the
    endpoints alone is off by up to 31.87/255), and the neutral capture already exists.
    """

    height, width = source_rgb.shape[:2]
    lo = _resized_field(low, width, height).astype(np.float32)
    md = _resized_field(mid, width, height).astype(np.float32)
    hi = _resized_field(high, width, height).astype(np.float32)
    s = np.clip(source_rgb.astype(np.float32), 0.0, 255.0)
    blended = np.where(
        s <= 128.0,
        lo + (md - lo) * (s / 128.0),
        md + (hi - md) * ((s - 128.0) / 127.0),
    )
    return np.clip(blended, 0.0, 255.0)


def _linear_axis(n_out: int, n_in: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """cv2 INTER_LINEAR taps for one axis: out i reads (i + 0.5) * s - 0.5 of the source."""

    s = n_in / float(n_out)
    f = (np.arange(n_out, dtype=np.float64) + 0.5) * s - 0.5
    i0 = np.floor(f)
    frac = (f - i0).astype(np.float32)
    i0 = np.clip(i0.astype(np.int64), 0, n_in - 1)
    i1 = np.clip(i0 + 1, 0, n_in - 1)
    return i0, i1, frac


def _resize_linear(arr: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Bilinear resize matching cv2.INTER_LINEAR, in numpy only.

    [SPB-DEMO-SCALE 2026-09-03] The demo cannot import the paid engine, and PIL's BILINEAR
    is not the same filter, so the arithmetic is reproduced here.  Plain bilinear sampling,
    no area averaging on downscale — exactly what cv2 does.
    """

    if arr.shape[0] == target_h and arr.shape[1] == target_w:
        return arr.astype(np.float32, copy=False)
    out = arr.astype(np.float32, copy=False)
    if out.shape[1] != target_w:
        x0, x1, fx = _linear_axis(target_w, out.shape[1])
        out = out[:, x0] * (1.0 - fx) + out[:, x1] * fx
    if out.shape[0] != target_h:
        y0, y1, fy = _linear_axis(target_h, out.shape[0])
        fy = fy[:, None]
        out = out[y0, :] * (1.0 - fy) + out[y1, :] * fy
    return out.astype(np.float32, copy=False)


def _tile_fractional(arr: np.ndarray, factor: float, target_h: int, target_w: int) -> np.ndarray:
    """Tile a 2D plane by a fractional factor then resize — port of the engine's placement."""

    h, w = arr.shape[:2]
    reps = min(10, max(2, int(np.ceil(factor))))
    crop_h = min(h * reps, max(4, int(round(h * factor))))
    crop_w = min(w * reps, max(4, int(round(w * factor))))
    horiz = _resize_linear(np.tile(arr, (1, reps))[:, :crop_w], h, target_w)
    return _resize_linear(np.tile(horiz, (reps, 1))[:crop_h, :], target_h, target_w)


def _crop_center(arr: np.ndarray, crop_frac: float, target_h: int, target_w: int) -> np.ndarray:
    """Keep the centre 1/crop_frac of a plane then resize — port of the engine's placement."""

    h, w = arr.shape[:2]
    ch = max(4, int(h / crop_frac))
    cw = max(4, int(w / crop_frac))
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return _resize_linear(arr[y0 : y0 + ch, x0 : x0 + cw], target_h, target_w)


def _placed_field(
    field: np.ndarray,
    width: int,
    height: int,
    *,
    scale: float = 1.0,
    rotation: float = 0.0,
    flip_h: bool = False,
    flip_v: bool = False,
    offset_x: float = 0.5,
    offset_y: float = 0.5,
) -> np.ndarray:
    """Place a captured field the way the paid engine places a colour source.

    [SPB-DEMO-SCALE 2026-09-03] Mirrors engine/compose.py _transform_base_color_source:
    scale < 1 tiles the pattern finer, scale > 1 crops the centre, 0.5 offsets are neutral,
    and nothing happens at all when every control sits at its rest value.  The demo's old
    resize-then-tile-then-crop displaced the field by half a canvas at rest and produced
    different pixels from the engine at every other scale.

    Both finishes in the owner's 2026-09-03 report take the engine's tiling fallback rather
    than consuming the placement inside their generator, so this reproduces the paid result
    rather than approximating it.
    """

    use_scale = max(0.05, min(5.0, float(scale if scale is not None else 1.0)))
    rot = float(rotation or 0.0) % 360.0
    ox = max(0.0, min(1.0, float(offset_x if offset_x is not None else 0.5)))
    oy = max(0.0, min(1.0, float(offset_y if offset_y is not None else 0.5)))

    src = np.asarray(field, dtype=np.float32)[:, :, :3]
    planes = []
    for channel in range(3):
        plane = src[:, :, channel]
        if abs(use_scale - 1.0) > 0.01:
            plane = (
                _tile_fractional(plane, 1.0 / use_scale, height, width)
                if use_scale < 1.0
                else _crop_center(plane, use_scale, height, width)
            )
        if plane.shape[0] != height or plane.shape[1] != width:
            plane = _resize_linear(plane, height, width)
        planes.append(plane)
    out = np.stack(planes, axis=2)

    if abs(rot) > 0.5:
        turns = int(round(rot / 90.0)) % 4
        if abs(rot - turns * 90.0) < 0.5:
            out = np.rot90(out, k=-turns).copy()
        else:
            image = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")
            image = image.rotate(-rot, resample=Image.Resampling.BILINEAR, expand=False)
            out = np.asarray(image, dtype=np.float32)
    if flip_h:
        out = np.fliplr(out).copy()
    if flip_v:
        out = np.flipud(out).copy()
    if abs(ox - 0.5) > 0.001 or abs(oy - 0.5) > 0.001:
        # Engine convention (_apply_pattern_offset): roll by the NEGATIVE shift, so a
        # slider above 0.5 pans the field left/up rather than right/down.
        out = np.roll(
            out,
            (-int(round((oy - 0.5) * height)), -int(round((ox - 0.5) * width))),
            axis=(0, 1),
        )
    return np.clip(out, 0, 255).astype(np.uint8)


def _placed_response(
    snapshot: "MaterialSnapshot",
    source_rgb: np.ndarray,
    width: int,
    height: int,
    placement: Mapping[str, Any],
) -> np.ndarray:
    """Place the finish, then let the un-scaled source drive its response.

    [SPB-DEMO-SCALE 2026-09-03] Order matters.  Base Scale positions the FINISH; the
    customer's artwork is never rescaled by it.  Transforming the already-modulated
    composite dragged the source art along and made the slider look dead on any finish
    that mostly tints its source.
    """

    if snapshot.paint_lo is None or snapshot.paint_hi is None:
        return _placed_field(snapshot.paint, width, height, **placement)
    lo = _placed_field(snapshot.paint_lo, width, height, **placement).astype(np.float32)
    mid = _placed_field(snapshot.paint, width, height, **placement).astype(np.float32)
    hi = _placed_field(snapshot.paint_hi, width, height, **placement).astype(np.float32)
    s = np.clip(source_rgb.astype(np.float32), 0.0, 255.0)
    blended = np.where(
        s <= 128.0,
        lo + (mid - lo) * (s / 128.0),
        mid + (hi - mid) * ((s - 128.0) / 127.0),
    )
    return np.clip(blended, 0, 255).astype(np.uint8)


@dataclass(frozen=True)
class MaterialSnapshot:
    """A finish captured as a RESPONSE to the source paint, not a frozen picture.

    [SPB-DEMO-PARITY 2026-09-03] The paid engine hands a zone's BASE MATERIAL the
    customer's real source art; every demo finish turns out to be a per-pixel,
    per-channel function of it, and a linear one (verified end-to-end: rebuilding an
    unseen render from ``paint_lo``/``paint_hi`` lands 0.30/255 mean against the engine,
    versus 5.10/255 for the old single-plate snapshot).  So we store the finish rendered
    over a black plate and over a white plate and interpolate by the real source at
    composite time.  Most spec_fns never receive the source paint, so ``spec`` is usually
    a single capture; the few finishes whose spec does track it (beetle_ground,
    cherry_polka) additionally carry ``spec_lo``/``spec_hi``.

    ``color_src`` is the SEPARATE field the engine builds when this finish is used as a
    "From special" base colour — its paint_fn over a flat 0.533 plate at ``seed + 4242``
    (engine/compose.py:_invoke_base_paint_fn_for_color_source / _mono_overlay_seed_paint).
    That role is genuinely source-independent, which is why one capture is exact.
    """

    paint: np.ndarray
    spec: np.ndarray
    paint_lo: np.ndarray | None = None
    paint_hi: np.ndarray | None = None
    color_src: np.ndarray | None = None
    spec_lo: np.ndarray | None = None
    spec_hi: np.ndarray | None = None
    synthetic: bool = False

    def spec_for_source(self, source_rgb: np.ndarray) -> np.ndarray:
        """Return this material's spec as the engine would render it over ``source_rgb``.

        Only the handful of finishes whose spec actually tracks the source carry a
        response pair; for everyone else the single capture is already exact.
        """

        if self.spec_lo is None or self.spec_hi is None:
            return self.spec.astype(np.float32)
        return _three_knot(
            self.spec_lo, self.spec, self.spec_hi, source_rgb
        )

    def paint_for_source(self, source_rgb: np.ndarray) -> np.ndarray:
        """Return this material's paint as the engine would render it over ``source_rgb``."""

        if self.paint_lo is None or self.paint_hi is None:
            return self.paint.astype(np.float32)
        return _three_knot(self.paint_lo, self.paint, self.paint_hi, source_rgb)


class SnapshotStore:
    def __init__(
        self,
        directory: str | Path,
        catalog: DemoCatalog,
        *,
        allow_synthetic: bool = False,
    ):
        self.directory = Path(directory).resolve()
        self.catalog = catalog
        self.allow_synthetic = bool(allow_synthetic)
        self._cache: dict[str, MaterialSnapshot] = {}
        self._lock = threading.Lock()

    # [SPB-DEMO-PREVIEW 2026-09-03 — owner: "if the MAIN APP colors look one way on the LIVE
    # PREVIEW the DEMO should look EXACTLY the same"] The paid app's live preview re-runs the
    # renderer at half resolution (LIVE_PREVIEW_MAX_SCALE = 0.5), and the engine's output at
    # 1024 is NOT its 2048 render downscaled — measured 10.06/255 apart from itself.  So a
    # single 2048 capture can never match the preview: downscaling it lost half the detail
    # (paint error 9.48/255).  Capturing natively at each render size takes that to 1.70.
    CAPTURE_SIZES = (2048, 1024)

    def path_for(self, finish_id: str, size: int | None = None) -> Path:
        if size is None or int(size) == self.CAPTURE_SIZES[0]:
            return self.directory / f"{finish_id}.npz"
        return self.directory / f"{finish_id}@{int(size)}.npz"

    @classmethod
    def capture_size_for(cls, canvas: int) -> int:
        """Pick the captured resolution nearest the canvas we are about to render."""

        return min(cls.CAPTURE_SIZES, key=lambda candidate: abs(candidate - int(canvas)))

    def inventory(self) -> dict[str, Any]:
        present = [finish_id for finish_id in self.catalog.finishes if self.path_for(finish_id).is_file()]
        missing = [finish_id for finish_id in self.catalog.finishes if finish_id not in present]
        return {
            "expected": len(self.catalog.finishes),
            "present": len(present),
            "missing": missing,
            "release_ready": not missing,
        }

    def get(self, finish_id: str, canvas: int | None = None) -> MaterialSnapshot:
        finish = self.catalog.get(finish_id)
        if finish is None:
            raise SnapshotError(f"Unknown demo finish: {finish_id}")
        size = self.capture_size_for(canvas) if canvas else self.CAPTURE_SIZES[0]
        key = f"{finish_id}@{size}"
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached

        path = self.path_for(finish_id, size)
        if not path.is_file() and size != self.CAPTURE_SIZES[0]:
            # A finish without its preview-size capture still renders from the full one.
            path = self.path_for(finish_id)
        if path.is_file():
            snapshot = self._load(path, finish)
        elif self.allow_synthetic:
            snapshot = self._synthetic(finish)
        else:
            raise SnapshotError(
                f"Reviewed material snapshot is missing for {finish_id}; "
                "run the SHOKK DEMO snapshot exporter"
            )
        with self._lock:
            self._cache[key] = snapshot
        return snapshot

    @staticmethod
    def _load(path: Path, finish: DemoFinish) -> MaterialSnapshot:
        try:
            with np.load(path, allow_pickle=False) as payload:
                paint = np.asarray(payload["paint"], dtype=np.uint8)
                spec = np.asarray(payload["spec"], dtype=np.uint8)

                def optional(key: str) -> np.ndarray | None:
                    if key not in payload:
                        return None
                    field = np.asarray(payload[key], dtype=np.uint8)
                    if field.ndim != 3 or field.shape[2] != 3 or field.shape[:2] != paint.shape[:2]:
                        raise SnapshotError(
                            f"Snapshot field {key!r} for {finish.id} must match paint HxWx3"
                        )
                    return field

                # Resolve while the archive is still open: NpzFile loads lazily and
                # every member is unreadable once the `with` block exits.
                paint_lo = optional("paint_lo")
                paint_hi = optional("paint_hi")
                color_src = optional("color_src")
                spec_lo = optional("spec_lo")
                spec_hi = optional("spec_hi")
                if "finish_id" in payload:
                    embedded = str(np.asarray(payload["finish_id"]).item())
                    if embedded != finish.id:
                        raise SnapshotError(
                            f"Snapshot identity mismatch: expected {finish.id}, found {embedded}"
                        )
                if "schema" in payload:
                    schema = str(np.asarray(payload["schema"]).item())
                    if schema != SNAPSHOT_SCHEMA:
                        raise SnapshotError(f"Unsupported snapshot schema for {finish.id}: {schema}")
        except SnapshotError:
            raise
        except Exception as exc:
            raise SnapshotError(f"Invalid snapshot for {finish.id}: {exc}") from exc
        if paint.ndim != 3 or paint.shape[2] != 3:
            raise SnapshotError(f"Snapshot paint field for {finish.id} must be HxWx3")
        if spec.ndim != 3 or spec.shape[2] < 3:
            raise SnapshotError(f"Snapshot spec field for {finish.id} must be HxWx3")
        return MaterialSnapshot(
            paint=paint,
            spec=spec[:, :, :3],
            paint_lo=paint_lo,
            paint_hi=paint_hi,
            color_src=color_src,
            spec_lo=spec_lo,
            spec_hi=spec_hi,
            synthetic=False,
        )

    @staticmethod
    def _synthetic(finish: DemoFinish, size: int = 384) -> MaterialSnapshot:
        """Development-only visual fallback; release checks require real snapshots."""

        seed_bytes = hashlib.sha256(finish.id.encode("utf-8")).digest()
        seed = int.from_bytes(seed_bytes[:8], "big")
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        base = np.array(_hex_rgb(finish.swatch), dtype=np.float32)

        f1 = 0.5 + 0.5 * np.sin(xx * (0.10 + seed_bytes[8] / 2100) + yy * 0.035)
        f2 = 0.5 + 0.5 * np.sin(yy * (0.13 + seed_bytes[9] / 1800) - xx * 0.027)
        radius = np.hypot(xx - size * 0.48, yy - size * 0.53)
        rings = 0.5 + 0.5 * np.sin(radius * (0.18 + seed_bytes[10] / 1600))
        cells = 0.5 + 0.5 * np.sin(xx * 0.39) * np.sin(yy * 0.43)
        flecks = (rng.random((size, size)) > 0.965).astype(np.float32)
        noise = rng.normal(0, 1, (size, size)).astype(np.float32)
        structure = np.clip(0.26 * f1 + 0.22 * f2 + 0.22 * rings + 0.18 * cells + 0.12 * noise, 0, 1)

        accent_a = np.roll(base, 1)
        accent_b = np.roll(base, 2)
        paint = (
            base[None, None, :] * (0.38 + structure[:, :, None] * 0.72)
            + accent_a[None, None, :] * (f1[:, :, None] - 0.5) * 0.32
            + accent_b[None, None, :] * (rings[:, :, None] - 0.5) * 0.24
            + flecks[:, :, None] * (90 + seed_bytes[11] % 100)
        )
        paint = np.clip(paint, 0, 255).astype(np.uint8)

        metallic = np.clip(35 + 190 * f1 + 30 * flecks, 0, 255)
        roughness = np.clip(220 - 175 * f2 + 25 * cells, 0, 255)
        clearcoat = np.clip(20 + 205 * rings + 25 * flecks, 0, 255)
        spec = np.stack([metallic, roughness, clearcoat], axis=-1).astype(np.uint8)
        return MaterialSnapshot(paint=paint, spec=spec, synthetic=True)


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = str(value or "#808080").lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except (TypeError, ValueError):
        return (128, 128, 128)


def _float01(value: Any, default: float = 1.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result > 1.0:
        result /= 100.0
    return max(0.0, min(1.0, result))


def _spec_strength_ratio(value: Any, default: float = 1.0) -> float:
    """Return a capped ratio while accepting either ratio or UI-percent input."""

    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(result):
        return default
    if result > 3.0:
        result /= 100.0
    return max(0.0, min(3.0, result))


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _transformed_field(
    field: np.ndarray,
    width: int,
    height: int,
    *,
    scale: float = 1.0,
    rotation: float = 0.0,
    flip_h: bool = False,
    flip_v: bool = False,
    offset_x: float = 0.5,
    offset_y: float = 0.5,
) -> np.ndarray:
    scale = max(0.05, min(5.0, float(scale or 1.0)))
    # [SPB-DEMO-PARITY 2026-09-03 — owner: "the demo has to work exactly like the main app"]
    # 0.5 is the NEUTRAL offset, not "pan to the middle of a 2x2 tiling".  The paid engine
    # short-circuits placement entirely at scale 1.0 / rotation 0 / offset 0.5 / no flips
    # (engine/compose.py:_transform_base_color_source), so every demo render was displaced by
    # exactly (-1024, -1024) against the paid app, with a hard wrap seam at row/col 1024
    # measured at 3.3-3.7x the field's typical gradient.  Match the engine's guard.
    if (
        abs(scale - 1.0) <= 0.01
        and abs(float(rotation or 0.0)) <= 0.5
        and not flip_h
        and not flip_v
        and abs(float(offset_x) - 0.5) <= 0.001
        and abs(float(offset_y) - 0.5) <= 0.001
    ):
        # Neutral placement: fit the capture to the canvas, never pan or tile it.
        return _resized_field(field, width, height)
    tile_width = max(8, min(width * 5, int(round(width * scale))))
    tile_height = max(8, min(height * 5, int(round(height * scale))))
    image = Image.fromarray(field[:, :, :3].astype(np.uint8), mode="RGB")
    image = image.resize((tile_width, tile_height), Image.Resampling.BILINEAR)
    if flip_h:
        image = ImageOps.mirror(image)
    if flip_v:
        image = ImageOps.flip(image)
    if rotation:
        image = image.rotate(-float(rotation), resample=Image.Resampling.BILINEAR, expand=True)
    tile = np.asarray(image, dtype=np.uint8)
    th, tw = tile.shape[:2]

    # Crop oversized transformed fields before repetition.  Without this guard
    # a 5x scale could allocate a 10x-by-10x intermediate just to return one
    # canvas, which is needless and hostile to 2048-square liveries.
    if tw > width:
        start_x = int(round((tw - width) * max(0.0, min(1.0, float(offset_x)))))
        tile = tile[:, start_x : start_x + width, :]
        tw = tile.shape[1]
    if th > height:
        start_y = int(round((th - height) * max(0.0, min(1.0, float(offset_y)))))
        tile = tile[start_y : start_y + height, :, :]
        th = tile.shape[0]

    # Repeat in both axes, then take an offset crop.  This preserves fine detail
    # when scale < 1 and gives predictable pan behavior for the UI sliders.
    repeat_x = max(1, int(np.ceil(width / max(1, tw))) + 1)
    repeat_y = max(1, int(np.ceil(height / max(1, th))) + 1)
    tiled = np.tile(tile, (repeat_y, repeat_x, 1))
    max_x = max(0, tiled.shape[1] - width)
    max_y = max(0, tiled.shape[0] - height)
    ox = int(round(max_x * max(0.0, min(1.0, float(offset_x)))))
    oy = int(round(max_y * max(0.0, min(1.0, float(offset_y)))))
    return tiled[oy : oy + height, ox : ox + width, :]


def _decode_rle(value: Any, width: int, height: int) -> np.ndarray | None:
    if isinstance(value, Mapping) and not isinstance(value.get("runs"), list):
        nested = _first(
            value,
            "mask",
            "rle",
            "source_layer_mask",
            "sourceLayerMask",
            "region_mask",
            "regionMask",
        )
        if nested is not None and nested is not value:
            return _decode_rle(nested, width, height)
    if not isinstance(value, Mapping) or not isinstance(value.get("runs"), list):
        return None
    try:
        source_width = int(value.get("width"))
        source_height = int(value.get("height"))
    except (TypeError, ValueError):
        raise ValueError("Mask width and height must be integers")
    if source_width <= 0 or source_height <= 0 or source_width * source_height > 4096 * 4096:
        raise ValueError("Mask dimensions are invalid")
    flat = np.zeros(source_width * source_height, dtype=np.uint8)
    position = 0
    for run in value["runs"]:
        if not isinstance(run, (list, tuple)) or len(run) != 2:
            raise ValueError("Mask runs must be [value, count] pairs")
        try:
            run_value = int(run[0])
            count = int(run[1])
        except (TypeError, ValueError):
            raise ValueError("Mask run values must be integers")
        if count <= 0 or position + count > flat.size:
            raise ValueError("Mask RLE length is invalid")
        flat[position : position + count] = max(0, min(255, run_value))
        position += count
    if position != flat.size:
        raise ValueError("Mask RLE does not cover its declared dimensions")
    mask = flat.reshape(source_height, source_width)
    if (source_width, source_height) != (width, height):
        mask = np.asarray(
            Image.fromarray(mask, mode="L").resize((width, height), Image.Resampling.NEAREST),
            dtype=np.uint8,
        )
    return mask


def _parse_color(value: Any) -> tuple[np.ndarray, float] | None:
    tolerance = 40.0
    byte_color = False
    if isinstance(value, Mapping):
        tolerance = _number(value.get("tolerance"), 40.0)
        value = value.get("color_rgb") or value.get("rgb") or value.get("color")
    if isinstance(value, str):
        byte_color = True
        lowered = value.strip().lower()
        if lowered in NAMED_COLORS:
            value = NAMED_COLORS[lowered]
        elif lowered.startswith("#"):
            value = _hex_rgb(lowered)
        else:
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            color = np.array([float(value[0]), float(value[1]), float(value[2])], dtype=np.float32)
        except (TypeError, ValueError):
            return None
        if not byte_color and float(color.max(initial=0)) <= 1.0:
            color *= 255.0
        return np.clip(color, 0, 255), max(0.0, min(441.7, tolerance))
    return None


def _color_mask(source_rgb: np.ndarray, value: Any) -> np.ndarray:
    height, width = source_rgb.shape[:2]
    if value is None:
        return np.ones((height, width), dtype=bool)
    keyword = value.strip().lower() if isinstance(value, str) else ""
    if keyword == "remaining":
        # The engine's {"remainder": True} really is every pixel, narrowed afterwards by
        # whatever the zones above already claimed.  Verified on a real template: engine
        # coverage 'remaining' = 100.0% of pixels.
        return np.ones((height, width), dtype=bool)
    if keyword in {"everything", "all", "body"}:
        # [SPB-DEMO-COVERAGE 2026-09-03] "Everything" is NOT every pixel — the engine's
        # all_painted selector is "painted OR dark":
        #     (sat > 0.08) | (brightness < 0.25)      engine/core.py build_zone_mask
        # so unsaturated near-white art (logos, numbers, sponsor decals) is deliberately
        # left alone.  The demo claimed all of it: measured on a real template the engine
        # painted 71.3% where the demo painted 100%, obliterating 28.7% of the car —
        # every near-white decal (untouched pixels averaged RGB 240.6/241.0/240.8).
        pixels = np.clip(source_rgb.astype(np.float32) / 255.0, 0.0, 1.0)
        high = pixels.max(axis=2)
        low = pixels.min(axis=2)
        saturation = np.where(high > 0.0, (high - low) / np.maximum(high, 1e-6), 0.0)
        brightness = (
            pixels[:, :, 0] * 0.299 + pixels[:, :, 1] * 0.587 + pixels[:, :, 2] * 0.114
        )
        return (saturation > 0.08) | (brightness < 0.25)
    if isinstance(value, list) and value:
        candidates = [value] if len(value) >= 3 and not isinstance(value[0], (Mapping, list, tuple)) else value
    else:
        candidates = [value]
    mask = np.zeros((height, width), dtype=bool)
    pixels = source_rgb.astype(np.float32)
    for candidate in candidates:
        parsed = _parse_color(candidate)
        if parsed is None:
            continue
        color, tolerance = parsed
        delta = pixels - color[None, None, :]
        # Paid picker parity: perceptual BT.601 channel weighting.  A plain
        # Euclidean RGB radius over-penalizes blue differences and underweights
        # green, so identical tolerance values otherwise select different art.
        distance_squared = (
            delta[:, :, 0] * delta[:, :, 0] * 0.30
            + delta[:, :, 1] * delta[:, :, 1] * 0.59
            + delta[:, :, 2] * delta[:, :, 2] * 0.11
        )
        mask |= distance_squared <= tolerance * tolerance
    return mask


def _source_layer_scope(
    zone: Mapping[str, Any], width: int, height: int
) -> tuple[bool, np.ndarray]:
    source_layer_values = zone.get("_demo_source_layer_masks")
    source_layer_restricted = bool(zone.get("_demo_source_layer_restricted", False))
    if not isinstance(source_layer_values, list):
        source_layer_values = []
        for key in ("source_layer_mask", "sourceLayerMask"):
            if zone.get(key) is not None:
                source_layer_restricted = True
                source_layer_values.append(zone[key])
        plural = _first(zone, "source_layer_masks", "sourceLayerMasks")
        if isinstance(plural, (list, tuple)):
            source_layer_restricted = True
            source_layer_values.extend(plural)
    source_layer_union = np.zeros((height, width), dtype=bool)
    decoded_any = False
    if source_layer_restricted:
        for source_layer_value in source_layer_values:
            source_layer = _decode_rle(source_layer_value, width, height)
            if source_layer is not None:
                source_layer_union |= source_layer > 0
                decoded_any = True
    # A layer id without raster coverage must never broaden into the whole
    # paint.  This matches the paid builder's all-zero fail-closed mask.
    if source_layer_restricted and not decoded_any:
        source_layer_union.fill(False)
    return source_layer_restricted, source_layer_union


def _source_layer_rgba(
    zone: Mapping[str, Any], width: int, height: int
) -> np.ndarray | None:
    """Decode the selected layer set's own flattened PNG, when supplied.

    The paid client sends raw base64 while newer clients may send a complete
    data URL.  Invalid/expired optional layer color data deliberately falls
    back to composite-paint matching; the separately supplied layer mask
    remains authoritative for containment.
    """

    value = _first(
        zone,
        "source_layer_rgb_png",
        "sourceLayerRgbPng",
        "source_layer_rgb",
        "sourceLayerRgb",
    )
    if not isinstance(value, str) or not value.strip():
        return None
    data_url = value.strip()
    if not data_url.startswith("data:"):
        data_url = "data:image/png;base64," + data_url
    try:
        payload = decode_png_data_url(data_url)
        image = load_source_image(payload=payload).convert("RGBA")
        if image.size != (width, height):
            image = image.resize((width, height), Image.Resampling.BILINEAR)
        return np.asarray(image, dtype=np.uint8)
    except Exception:
        return None


def _zone_mask(
    zone: Mapping[str, Any],
    source_rgba: np.ndarray,
    occupied: np.ndarray,
    prior_claims: Sequence[tuple[np.ndarray, np.ndarray | None]] = (),
    *,
    source_layer_restricted: bool | None = None,
    source_layer_scope: np.ndarray | None = None,
    source_layer_rgba: np.ndarray | None = None,
) -> np.ndarray:
    height, width = source_rgba.shape[:2]
    color_value = zone.get("color", "everything")
    is_remaining = isinstance(color_value, str) and color_value.strip().lower() == "remaining"
    if source_layer_restricted is None or source_layer_scope is None:
        source_layer_restricted, source_layer_scope = _source_layer_scope(zone, width, height)
    if source_layer_restricted and source_layer_rgba is None:
        source_layer_rgba = _source_layer_rgba(zone, width, height)
    use_layer_rgb = (
        source_layer_restricted
        and source_layer_rgba is not None
        and not is_remaining
        and not (
            isinstance(color_value, str)
            and color_value.strip().lower() in {"everything", "all"}
        )
    )
    match_rgba = source_layer_rgba if use_layer_rgb else source_rgba
    mask = _color_mask(match_rgba[:, :, :3], color_value)
    if use_layer_rgb:
        mask &= match_rgba[:, :, 3] > 0

    region = _decode_rle(_first(zone, "region_mask", "regionMask"), width, height)
    if region is not None:
        mask &= region > 0

    if source_layer_restricted:
        mask &= source_layer_scope

    spatial = _decode_rle(_first(zone, "spatial_mask", "spatialMask"), width, height)
    if spatial is not None:
        include = spatial == 1
        if np.any(include):
            mask &= include
        mask &= spatial != 2
    exclusions = zone.get("exclusions")
    if isinstance(exclusions, (list, tuple)):
        for exclusion in exclusions:
            mask &= ~_color_mask(source_rgba[:, :, :3], exclusion)
    mask &= source_rgba[:, :, 3] > 0

    if is_remaining and source_layer_restricted:
        # A layer-local remainder owns what remains in its selected PSD layer
        # scope.  Earlier unrestricted composite zones intentionally do not
        # erase it; only earlier claims that were themselves layer-restricted
        # and overlap this scope participate.  This mirrors paid
        # _build_remainder_zone_mask rather than applying global occupancy.
        layer_claimed = np.zeros((height, width), dtype=bool)
        for prior_mask, prior_scope in prior_claims:
            if prior_scope is None:
                continue
            overlap_scope = prior_scope & source_layer_scope
            if np.any(overlap_scope):
                layer_claimed |= prior_mask & overlap_scope
        mask &= ~layer_claimed
    else:
        # Top-to-bottom is strict FIRST-WINS for every normal zone and for a
        # non-layer-restricted Remaining zone.
        mask &= ~occupied
    return mask


def _requested_color(zone: Mapping[str, Any]) -> np.ndarray | None:
    value = _first(zone, "base_color", "baseColor")
    parsed = _parse_color(value)
    if parsed is not None:
        return parsed[0]
    colors = zone.get("finish_colors")
    if isinstance(colors, list) and colors:
        parsed = _parse_color(colors[0])
        if parsed is not None:
            return parsed[0]
    return None


def _apply_hsb_controls(painted: np.ndarray, zone: Mapping[str, Any]) -> np.ndarray:
    hue = _number(_first(zone, "base_hue_offset", "baseHueOffset"), 0.0)
    saturation = _number(
        _first(zone, "base_saturation_adjust", "baseSaturationAdjust"), 0.0
    )
    brightness = _number(
        _first(zone, "base_brightness_adjust", "baseBrightnessAdjust"), 0.0
    )
    if abs(hue) < 0.5 and abs(saturation) < 0.5 and abs(brightness) < 0.5:
        return painted
    hsv_image = Image.fromarray(np.clip(painted, 0, 255).astype(np.uint8), mode="RGB").convert("HSV")
    hsv = np.asarray(hsv_image, dtype=np.uint8).copy()
    if abs(hue) >= 0.5:
        shifted = hsv[:, :, 0].astype(np.int16) + int(round((hue / 360.0) * 255.0))
        hsv[:, :, 0] = np.mod(shifted, 256).astype(np.uint8)
    if abs(saturation) >= 0.5:
        hsv[:, :, 1] = np.clip(
            hsv[:, :, 1].astype(np.float32) * (1.0 + saturation / 100.0), 0, 255
        ).astype(np.uint8)
    if abs(brightness) >= 0.5:
        hsv[:, :, 2] = np.clip(
            hsv[:, :, 2].astype(np.float32) * (1.0 + brightness / 100.0), 0, 255
        ).astype(np.uint8)
    return np.asarray(Image.fromarray(hsv, mode="HSV").convert("RGB"), dtype=np.float32)


def _apply_color_lab_controls(
    material_paint: np.ndarray,
    color_source: np.ndarray,
    zone: Mapping[str, Any],
) -> np.ndarray:
    depth_value = _first(zone, "base_color_depth", "baseColorDepth")
    strength = _float01(
        _first(zone, "base_color_strength", "baseColorStrength"), 1.0
    )
    # [SPB-DEMO-COLOR 2026-09-03] Owner: selected colors must not mutate.
    # Old clients/sessions always supplied 65%; that is NOT consent to candy tinting.
    # Only an explicit opt-in may enter this path.
    enabled = _first(zone, "base_color_lab_enabled", "baseColorLabEnabled") is True
    if not enabled or depth_value is None:
        return material_paint * (1.0 - strength) + color_source * strength

    p3 = np.clip(material_paint.astype(np.float32) / 255.0, 0.0, 1.0)
    s3 = np.clip(color_source.astype(np.float32) / 255.0, 0.0, 1.0)
    depth = _float01(depth_value, 0.65)
    flip_degrees = _number(_first(zone, "base_color_flip", "baseColorFlip"), 0.0) % 360.0
    underglow = _float01(
        _first(zone, "base_color_underglow", "baseColorUnderglow"), 0.0
    )
    value = 0.299 * p3[:, :, 0] + 0.587 * p3[:, :, 1] + 0.114 * p3[:, :, 2]
    lift = (value * 0.72 + 0.45)[:, :, None]
    transmittance = np.clip(s3, 0.02, 1.0) ** (0.30 + 2.1 * depth)
    candy = np.clip(
        lift * transmittance
        + np.clip(value - 0.90, 0.0, 1.0)[:, :, None] * 1.3,
        0.0,
        1.0,
    )
    alpha = min(1.0, depth * 3.0)
    # SPB-DEMO-COLOR 2026-09-06 — zero effects must preserve the SELECTED
    # color, not replace it with the source-responsive material. This makes
    # enabling Color Lab neutral; deliberate depth still adds candy absorption.
    out = s3 * (1.0 - alpha) + candy * alpha
    if depth == 0 and flip_degrees == 0 and underglow == 0:
        return material_paint * (1.0 - strength) + color_source * strength

    if underglow > 0.001:
        mean_rgb = s3.reshape(-1, 3).mean(axis=0)
        under = (
            np.array([1.0, 0.82, 0.35], dtype=np.float32)
            if float(mean_rgb[0]) >= float(mean_rgb[2])
            else np.array([0.92, 0.95, 1.0], dtype=np.float32)
        )
        weight = underglow * (
            0.22 + 0.78 * np.clip((value - 0.30) / 0.55, 0.0, 1.0) ** 1.3
        )
        out = 1.0 - (1.0 - out) * (
            1.0 - under[None, None, :] * weight[:, :, None] * 0.85
        )

    if flip_degrees > 0.5:
        radians = np.deg2rad(flip_degrees)
        cosine, sine = float(np.cos(radians)), float(np.sin(radians))
        rgb_to_yiq = np.array(
            [[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]],
            dtype=np.float32,
        )
        yiq_to_rgb = np.linalg.inv(rgb_to_yiq).astype(np.float32)
        rotate = np.array(
            [[1, 0, 0], [0, cosine, -sine], [0, sine, cosine]], dtype=np.float32
        )
        matrix = (yiq_to_rgb @ rotate @ rgb_to_yiq).astype(np.float32)
        flipped = np.clip(out @ matrix.T, 0.0, 1.0)
        dark_weight = np.clip((0.55 - value) / 0.35, 0.0, 1.0) ** 1.2
        out = out * (1.0 - dark_weight[:, :, None]) + flipped * dark_weight[:, :, None]

    controlled = material_paint * (1.0 - strength) + np.clip(out * 255.0, 0, 255) * strength
    return np.clip(controlled, 0, 255)


def _finish_own_paint(texture: np.ndarray, finish: DemoFinish) -> np.ndarray:
    """Return the finish's authored/demo color field.

    Monolithic snapshots contain their authored paint.  Foundation snapshots
    are deliberately baked over neutral gray so their material response is
    reusable; restore their manifest swatch while retaining neutral luminance
    detail for the ``Use finish's own color`` choice.
    """

    tex = texture.astype(np.float32)
    if finish.kind != "base":
        return tex
    luma = (
        tex[:, :, 0] * 0.2126
        + tex[:, :, 1] * 0.7152
        + tex[:, :, 2] * 0.0722
    ) / 255.0
    chroma = tex - (luma[:, :, None] * 255.0)
    swatch = np.array(_hex_rgb(finish.swatch), dtype=np.float32)
    # A neutral 50% build plate maps to the exact swatch.  Any authored fine
    # luminance/chroma in the base snapshot survives around it.
    gain = np.clip(0.65 + 0.70 * luma, 0.45, 1.35)
    return np.clip(swatch[None, None, :] * gain[:, :, None] + chroma * 0.35, 0, 255)


def _gradient_field(
    stops: Any,
    direction: str,
    width: int,
    height: int,
) -> np.ndarray:
    parsed_stops: list[tuple[float, np.ndarray]] = []
    if isinstance(stops, (list, tuple)):
        for stop in stops:
            if not isinstance(stop, Mapping):
                continue
            position = _number(_first(stop, "pos", "position", "offset"), -1.0)
            if position > 1.0:
                position /= 100.0
            parsed = _parse_color(_first(stop, "color", "color_rgb", "rgb"))
            if parsed is not None:
                parsed_stops.append((max(0.0, min(1.0, position)), parsed[0]))
    if len(parsed_stops) < 2:
        raise ValueError("Custom gradient needs at least two valid color stops")
    parsed_stops.sort(key=lambda item: item[0])
    positions = np.array([item[0] for item in parsed_stops], dtype=np.float32)
    colors = np.stack([item[1] for item in parsed_stops], axis=0).astype(np.float32)

    direction = str(direction or "horizontal").strip().lower()
    yy = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    if direction == "vertical":
        coordinate = np.broadcast_to(yy, (height, width))
    elif direction == "diagonal_down":
        coordinate = (xx + yy) * 0.5
    elif direction == "diagonal_up":
        coordinate = (xx + (1.0 - yy)) * 0.5
    elif direction == "radial":
        cy, cx = height / 2.0, width / 2.0
        grid_y = np.arange(height, dtype=np.float32)[:, None] - cy
        grid_x = np.arange(width, dtype=np.float32)[None, :] - cx
        coordinate = np.hypot(grid_x, grid_y) / max(float(np.hypot(cx, cy)), 1e-6)
    elif direction == "angular":
        cy, cx = height / 2.0, width / 2.0
        grid_y = np.arange(height, dtype=np.float32)[:, None] - cy
        grid_x = np.arange(width, dtype=np.float32)[None, :] - cx
        coordinate = (np.arctan2(-grid_y, grid_x) + np.pi) / (2.0 * np.pi)
    else:
        coordinate = np.broadcast_to(xx, (height, width))
    coordinate = np.clip(coordinate, 0.0, 1.0)
    channels = [
        np.interp(coordinate.ravel(), positions, colors[:, channel]).reshape(height, width)
        for channel in range(3)
    ]
    return np.stack(channels, axis=2).astype(np.float32)


def _paint_field(
    source_rgb: np.ndarray,
    texture: np.ndarray,
    finish: DemoFinish,
    zone: Mapping[str, Any],
    color_source: np.ndarray | None = None,
    authored: bool = False,
) -> np.ndarray:
    src = source_rgb.astype(np.float32)
    # [SPB-DEMO-PARITY 2026-09-03] A response-captured material already carries the paint the
    # engine renders; only a legacy single-plate capture of a material-only foundation still
    # needs its swatch restored.
    own_paint = texture.astype(np.float32) if authored else _finish_own_paint(texture, finish)
    mode = str(_first(zone, "base_color_mode", "baseColorMode", default="finish")).strip().lower()
    if mode in {"source", "source-paint", "source_paint", "spec-only", "spec_only"}:
        painted = src
    elif mode in {"finish", "finish-own", "finish_own", "own", "material"}:
        painted = own_paint
    else:
        if color_source is None:
            color_source = own_paint
        painted = _apply_color_lab_controls(
            own_paint,
            np.clip(color_source.astype(np.float32), 0, 255),
            zone,
        )
    return np.clip(_apply_hsb_controls(painted, zone), 0, 255)


def _spec_field(spec: np.ndarray, zone: Mapping[str, Any]) -> np.ndarray:
    result = spec.astype(np.float32)
    remap = _first(zone, "spec_material_remap", "specMaterialRemap")
    if isinstance(remap, Mapping):
        for index, key in enumerate(("m", "r", "cc")):
            value = remap.get(key)
            if isinstance(value, Mapping):
                low = max(0.0, min(255.0, _number(value.get("low"), 0.0)))
                high = max(low, min(255.0, _number(value.get("high"), 255.0)))
                result[:, :, index] = low + (result[:, :, index] / 255.0) * (high - low)
    override = _first(zone, "spec_material_override", "specMaterialOverride")
    if isinstance(override, Mapping):
        for index, key in enumerate(("m", "r", "cc")):
            if key in override:
                result[:, :, index] = max(0.0, min(255.0, _number(override[key], 0.0)))
    shifts = zone.get("spec_channel_shift")
    if not (isinstance(shifts, (list, tuple)) and len(shifts) >= 3):
        shifts = [
            _number(zone.get("specShiftR"), 0.0),
            _number(zone.get("specShiftG"), 0.0),
            _number(zone.get("specShiftB"), 0.0),
        ]
    if isinstance(shifts, (list, tuple)) and len(shifts) >= 3:
        result += np.array([_number(shifts[i], 0.0) for i in range(3)], dtype=np.float32)[None, None, :]
    return np.clip(result, 0, 255)


def _blend_spec(base: np.ndarray, layer: np.ndarray, opacity: np.ndarray, mode: str) -> np.ndarray:
    mode = str(mode or "normal").strip().lower()
    b = np.clip(base / 255.0, 0.0, 1.0)
    p = np.clip(layer / 255.0, 0.0, 1.0)
    if mode == "multiply":
        blended = b * p
    elif mode == "screen":
        blended = 1.0 - (1.0 - b) * (1.0 - p)
    elif mode == "overlay":
        blended = np.where(b < 0.5, 2.0 * b * p, 1.0 - 2.0 * (1.0 - b) * (1.0 - p))
    elif mode == "hardlight":
        blended = np.where(p < 0.5, 2.0 * b * p, 1.0 - 2.0 * (1.0 - b) * (1.0 - p))
    elif mode == "softlight":
        blended = (1.0 - 2.0 * p) * b * b + 2.0 * p * b
    elif mode == "ghost_carve":
        blended = np.stack(
            [np.maximum(b[:, :, 0], p[:, :, 0]), np.minimum(b[:, :, 1], p[:, :, 1]), np.maximum(b[:, :, 2], p[:, :, 2])],
            axis=2,
        )
    elif mode == "chrome_inlay":
        gate = p[:, :, 0]
        blended = np.stack([np.maximum(b[:, :, 0], gate), b[:, :, 1] * (1.0 - 0.7 * gate), np.maximum(b[:, :, 2], gate)], axis=2)
    elif mode == "frost_etch":
        gate = p[:, :, 1]
        blended = np.stack([b[:, :, 0] * (1.0 - 0.6 * gate), np.maximum(b[:, :, 1], gate), b[:, :, 2] * (1.0 - 0.5 * gate)], axis=2)
    elif mode == "angle_flip":
        blended = p[:, :, [2, 1, 0]]
    elif mode == "ember_gate":
        gate = p[:, :, 2]
        blended = np.stack([np.maximum(b[:, :, 0], gate), np.minimum(b[:, :, 1], 1.0 - gate * 0.75), np.maximum(b[:, :, 2], gate)], axis=2)
    elif mode == "depth_press":
        depth = (p[:, :, 0] + p[:, :, 2]) * 0.5
        blended = np.stack([b[:, :, 0] * (0.5 + 0.5 * depth), np.maximum(b[:, :, 1], 1.0 - depth), b[:, :, 2] * (0.35 + 0.65 * depth)], axis=2)
    else:
        blended = p
    return np.clip((b * (1.0 - opacity) + blended * opacity) * 255.0, 0, 255)


class DemoCompositor:
    def __init__(self, catalog: DemoCatalog, snapshots: SnapshotStore):
        self.catalog = catalog
        self.snapshots = snapshots

    def render(self, source: Image.Image, zones: list[Mapping[str, Any]]) -> tuple[Image.Image, Image.Image]:
        source_rgba = np.asarray(source.convert("RGBA"), dtype=np.uint8)
        height, width = source_rgba.shape[:2]
        paint = source_rgba[:, :, :3].astype(np.float32).copy()
        spec = np.empty((height, width, 3), dtype=np.float32)
        spec[:, :, 0] = 0
        spec[:, :, 1] = 128
        spec[:, :, 2] = 0
        spec_output_alpha = source_rgba[:, :, 3].astype(np.float32).copy()
        occupied = np.zeros((height, width), dtype=bool)
        # Each claim keeps its optional PSD-layer scope.  One global occupied
        # mask is enough for normal first-wins priority, but layer-restricted
        # Remaining needs provenance so it can ignore earlier unrestricted
        # composite claims while subtracting overlapping restricted claims.
        prior_claims: list[tuple[np.ndarray, np.ndarray | None]] = []
        decoded_source_scopes: dict[
            str, tuple[bool, np.ndarray, np.ndarray | None]
        ] = {}

        for zone in zones:
            finish_id = str(zone["_demo_finish_id"])
            finish = self.catalog.get(finish_id)
            if finish is None:
                raise SnapshotError(f"Finish is not included in SHOKK DEMO: {finish_id}")
            snapshot = self.snapshots.get(finish_id, max(width, height))
            shared_scope_id = str(zone.get("_demo_source_layer_scope_id") or "")
            cached_scope = decoded_source_scopes.get(shared_scope_id) if shared_scope_id else None
            if cached_scope is not None:
                source_layer_restricted, source_layer_scope, source_layer_rgba = cached_scope
            else:
                source_layer_restricted, source_layer_scope = _source_layer_scope(
                    zone, width, height
                )
                source_layer_rgba = (
                    _source_layer_rgba(zone, width, height)
                    if source_layer_restricted
                    else None
                )
                if shared_scope_id:
                    decoded_source_scopes[shared_scope_id] = (
                        source_layer_restricted,
                        source_layer_scope,
                        source_layer_rgba,
                    )
            mask = _zone_mask(
                zone,
                source_rgba,
                occupied,
                prior_claims,
                source_layer_restricted=source_layer_restricted,
                source_layer_scope=source_layer_scope,
                source_layer_rgba=source_layer_rgba,
            )
            if not np.any(mask):
                continue

            base_scale = max(
                0.05,
                min(5.0, _number(_first(zone, "base_scale", "baseScale"), 1.0)),
            )
            base_rotation = _number(
                _first(zone, "base_rotation", "baseRotation", "rotation"), 0.0
            )
            # [SPB-DEMO-PARITY 2026-09-03] The paid engine renders the BASE MATERIAL over the
            # customer's own source art, so replay the finish's captured response to it
            # instead of a picture frozen over a build plate.
            #
            # [SPB-DEMO-SCALE 2026-09-03 — owner: "Base Scale ... not scaling at all in the
            # DEMO"] Base Scale must place the FINISH, never the customer's artwork.  Scaling
            # the already-source-modulated composite scaled the car's own art along with it,
            # which for a finish that mostly tints the source (fs_core_emerald) reads as the
            # slider doing nothing at all.  Place each captured response field FIRST, then
            # modulate by the un-scaled source — matching the engine, where base_scale reaches
            # the finish's generator and the source art is never rescaled.
            placement = dict(
                scale=base_scale,
                rotation=base_rotation,
                flip_h=bool(_first(zone, "base_flip_h", "baseFlipH", default=False)),
                flip_v=bool(_first(zone, "base_flip_v", "baseFlipV", default=False)),
                offset_x=_number(_first(zone, "base_offset_x", "baseOffsetX"), 0.5),
                offset_y=_number(_first(zone, "base_offset_y", "baseOffsetY"), 0.5),
            )
            texture = _placed_response(
                snapshot, source_rgba[:, :, :3], width, height, placement
            )
            # [SPB-DEMO-SCALE 2026-09-03] Base Scale COMPOSES with Color Scale for a
            # "From special" source, exactly as the engine does in
            # _zone_monolithic_color_source_scale: base_transform["scale"] * base_color_scale.
            # The demo read base_color_scale alone, and the demo UI always sends 1.00x for it,
            # so Base Scale could never reach the colour source at all.
            color_scale = max(
                0.05,
                min(
                    5.0,
                    base_scale
                    * max(
                        0.01,
                        min(
                            5.0,
                            _number(
                                _first(zone, "base_color_scale", "baseColorScale"), 1.0
                            ),
                        ),
                    ),
                ),
            )
            color_rotation = _number(
                _first(zone, "base_color_rotation", "baseColorRotation"), base_rotation
            )
            mode = str(
                _first(zone, "base_color_mode", "baseColorMode", default="finish")
            ).strip().lower()
            color_source: np.ndarray | None = None
            if mode == "solid":
                requested = _requested_color(zone)
                if requested is not None:
                    color_source = np.broadcast_to(
                        requested[None, None, :], (height, width, 3)
                    ).astype(np.float32)
            elif mode == "special":
                color_finish_id = str(zone.get("_demo_color_finish_id") or "")
                color_finish = self.catalog.get(color_finish_id)
                if color_finish is None:
                    raise SnapshotError(
                        f"Base color source is not included in SHOKK DEMO: {color_finish_id}"
                    )
                color_snapshot = self.snapshots.get(color_finish_id, max(width, height))
                # [SPB-DEMO-PARITY 2026-09-03] "From special" is its own engine path: the
                # finish's paint_fn over a flat 0.533 plate, NOT the material capture and
                # NOT a manifest-swatch recolor.  _finish_own_paint used to rebuild every
                # kind=="base" source from its hex swatch, which crushed Cherry Polka's
                # contrast 60% and cut it from 33 distinct colours to 10.
                color_field = (
                    color_snapshot.color_src
                    if color_snapshot.color_src is not None
                    else color_snapshot.paint
                )
                transformed_color = _placed_field(
                    np.clip(color_field, 0, 255).astype(np.uint8),
                    width,
                    height,
                    scale=color_scale,
                    rotation=color_rotation,
                    flip_h=bool(_first(zone, "base_flip_h", "baseFlipH", default=False)),
                    flip_v=bool(_first(zone, "base_flip_v", "baseFlipV", default=False)),
                    offset_x=_number(_first(zone, "base_offset_x", "baseOffsetX"), 0.5),
                    offset_y=_number(_first(zone, "base_offset_y", "baseOffsetY"), 0.5),
                )
                color_source = (
                    transformed_color.astype(np.float32)
                    if color_snapshot.color_src is not None
                    else _finish_own_paint(transformed_color, color_finish)
                )
            elif mode == "gradient":
                color_source = _gradient_field(
                    _first(zone, "gradient_stops", "gradientStops"),
                    str(
                        _first(
                            zone,
                            "gradient_direction",
                            "gradientDirection",
                            default="horizontal",
                        )
                    ),
                    width,
                    height,
                )
                color_offset_x = _number(
                    _first(zone, "base_offset_x", "baseOffsetX"), 0.5
                )
                color_offset_y = _number(
                    _first(zone, "base_offset_y", "baseOffsetY"), 0.5
                )
                if (
                    abs(color_scale - 1.0) > 0.01
                    or abs(color_rotation) > 0.5
                    or bool(_first(zone, "base_flip_h", "baseFlipH", default=False))
                    or bool(_first(zone, "base_flip_v", "baseFlipV", default=False))
                    or abs(color_offset_x - 0.5) > 0.001
                    or abs(color_offset_y - 0.5) > 0.001
                ):
                    color_source = _placed_field(
                        np.clip(color_source, 0, 255).astype(np.uint8),
                        width,
                        height,
                        scale=color_scale,
                        rotation=color_rotation,
                        flip_h=bool(
                            _first(zone, "base_flip_h", "baseFlipH", default=False)
                        ),
                        flip_v=bool(
                            _first(zone, "base_flip_v", "baseFlipV", default=False)
                        ),
                        offset_x=color_offset_x,
                        offset_y=color_offset_y,
                    ).astype(np.float32)
            painted = _paint_field(
                source_rgba[:, :, :3],
                texture,
                finish,
                zone,
                color_source=color_source,
                authored=snapshot.paint_lo is not None,
            )

            intensity = _float01(zone.get("intensity"), 1.0)
            paint_strength = intensity * _float01(
                _first(zone, "base_strength", "baseStrength"), 1.0
            )
            paint_alpha = mask.astype(np.float32) * paint_strength
            paint = paint * (1.0 - paint_alpha[:, :, None]) + painted * paint_alpha[:, :, None]

            # [SPB-DEMO-SCALE 2026-09-03 — owner: "the BASE and SPEC SCALES ARE SUPPOSED TO
            # STAY IN LOCKSTEP UNLESS WE USE THE CHECKBOX ON SPEC SCALE"] Same contract as the
            # paid app: spec follows base unless the zone is explicitly independent
            # (paint-booth-2-state-zones.js _spbResolveSpecScale).  The demo used to hardcode
            # specScaleMode 'independent' and always send 1.00x, so spec was permanently
            # unlinked from Base Scale.
            spec_independent = (
                str(_first(zone, "spec_scale_mode", "specScaleMode", default="match"))
                .strip()
                .lower()
                == "independent"
            )
            spec_scale = max(
                0.05,
                min(
                    5.0,
                    _number(_first(zone, "spec_scale", "specScale"), base_scale)
                    if spec_independent
                    else base_scale,
                ),
            )
            spec_rotation = (
                _number(_first(zone, "spec_rotation", "specRotation"), base_rotation)
                if spec_independent
                else base_rotation
            )
            material = _placed_field(
                np.clip(snapshot.spec_for_source(source_rgba[:, :, :3]), 0, 255).astype(np.uint8),
                width,
                height,
                scale=spec_scale,
                rotation=spec_rotation,
                flip_h=bool(
                    _first(
                        zone,
                        "spec_flip_h",
                        "specFlipH",
                        "base_flip_h",
                        "baseFlipH",
                        default=False,
                    )
                ),
                flip_v=bool(
                    _first(
                        zone,
                        "spec_flip_v",
                        "specFlipV",
                        "base_flip_v",
                        "baseFlipV",
                        default=False,
                    )
                ),
                offset_x=_number(
                    _first(zone, "spec_offset_x", "specOffsetX", "base_offset_x", "baseOffsetX"),
                    0.5,
                ),
                offset_y=_number(
                    _first(zone, "spec_offset_y", "specOffsetY", "base_offset_y", "baseOffsetY"),
                    0.5,
                ),
            )
            material = _spec_field(material, zone)
            spec_strength = intensity * _spec_strength_ratio(
                _first(zone, "base_spec_strength", "baseSpecStrength"), 1.0
            )
            spec_alpha = mask.astype(np.float32)[:, :, None] * spec_strength
            blend_mode = str(
                _first(zone, "base_spec_blend_mode", "baseSpecBlendMode", default="normal")
            )
            spec = _blend_spec(spec, material, spec_alpha, blend_mode)
            alpha_override = None
            override = _first(zone, "spec_material_override", "specMaterialOverride")
            if isinstance(override, Mapping) and override.get("a") is not None:
                alpha_override = _number(override.get("a"), 255.0)
            lighting_mask = _first(zone, "spec_lighting_mask", "specLightingMask")
            if lighting_mask is not None:
                alpha_override = _number(lighting_mask, 255.0)
            if alpha_override is not None:
                spec_output_alpha[mask] = max(0.0, min(255.0, alpha_override))
            occupied |= mask
            prior_claims.append(
                (mask, source_layer_scope if source_layer_restricted else None)
            )

        paint_u8 = np.clip(paint, 0, 255).astype(np.uint8)
        spec_u8 = np.clip(spec, 0, 255).astype(np.uint8)
        alpha = np.clip(spec_output_alpha, 0, 255).astype(np.uint8)[:, :, None]
        spec_rgba = np.concatenate([spec_u8, alpha], axis=2)
        return Image.fromarray(paint_u8, mode="RGB"), Image.fromarray(spec_rgba, mode="RGBA")
