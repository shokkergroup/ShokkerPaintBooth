"""Optional local GPU bridge for Smart TGA / Auto-build Layers.

This module intentionally keeps the production CPU path safe: if the local
_gpuenv or model files are missing, slow, or fail, callers get None and fall
back to the existing heuristic separator.
"""
from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

def _default_runtime_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] if len(here.parents) > 2 else here.parent


def _runtime_root_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    env_root = os.environ.get("SPB_SMART_TGA_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(_default_runtime_root())
    candidates.extend(here.parents)

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def _find_runtime_root() -> Path:
    for root in _runtime_root_candidates():
        if (root / "_separate_image.py").is_file() and (root / "_logo_data" / "maskcls.npz").is_file():
            return root
    return _default_runtime_root()


_ROOT = _find_runtime_root()
_SCRIPT = _ROOT / "_separate_image.py"
_MODEL = _ROOT / "_logo_data" / "maskcls.npz"
_SAM = _ROOT / "_logo_data" / "sam_vit_b.pth"
_MODEL_META = _ROOT / "_logo_data" / "model.json"
_CACHE_VERSION = "smart_tga_gpu_v24_mirror_corroborated_only"
_CACHE_ROOT = _ROOT / "_smart_tga_runs" / "gpu_cache"
_LAST_INFO = {
    "available": False,
    "cache": "unknown",
    "cache_key": None,
    "elapsed_sec": 0.0,
    "reason": None,
    "runtime_root": str(_ROOT),
    "profile_path": None,
}


def _gpu_python() -> Path:
    if os.name == "nt":
        return _ROOT / "_gpuenv" / "Scripts" / "python.exe"
    return _ROOT / "_gpuenv" / "bin" / "python"


def _enabled() -> bool:
    return _availability()[0]


def _availability() -> tuple[bool, str]:
    v = os.environ.get("SPB_SMART_TGA_GPU", "auto").strip().lower()
    if v in {"0", "false", "off", "no"}:
        return False, "disabled"
    checks = (
        ("gpu_python", _gpu_python()),
        ("script", _SCRIPT),
        ("model", _MODEL),
        ("sam", _SAM),
    )
    missing = [name for name, path in checks if not path.is_file()]
    if missing:
        return False, "missing:" + ",".join(missing)
    return True, "ok"


def _set_last_info(**kwargs) -> None:
    _LAST_INFO.clear()
    _LAST_INFO.update({
        "available": False,
        "cache": "unknown",
        "cache_key": None,
        "elapsed_sec": 0.0,
        "reason": None,
        "runtime_root": str(_ROOT),
        "profile_path": None,
    })
    _LAST_INFO.update(kwargs)


def last_info() -> dict:
    return dict(_LAST_INFO)


def _read_mask(path: Path, target_shape: tuple[int, int]) -> np.ndarray:
    h, w = target_shape
    img = Image.open(path).convert("L")
    if img.size != (w, h):
        img = img.resize((w, h), Image.Resampling.NEAREST)
    return (np.asarray(img) > 127).astype(np.uint8) * 255


def _read_ocr_regions(path: Path, target_shape: tuple[int, int]) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        regions = list(payload.get("regions") or ())
        source_shape = payload.get("shape") or target_shape
    else:  # Legacy development sidecars were already target-space lists.
        regions = list(payload or ())
        source_shape = target_shape
    source_h, source_w = [max(1, int(value)) for value in source_shape[:2]]
    target_h, target_w = target_shape
    scale_x = target_w / float(source_w)
    scale_y = target_h / float(source_h)
    scaled = []
    for item in regions:
        region = dict(item)
        bbox = region.get("bbox")
        if bbox is not None and len(bbox) >= 4:
            x, y, width, height = [float(value) for value in bbox[:4]]
            region["bbox"] = [
                int(round(x * scale_x)), int(round(y * scale_y)),
                max(1, int(round(width * scale_x))),
                max(1, int(round(height * scale_y))),
            ]
        polygon = region.get("polygon", region.get("poly"))
        if polygon is not None:
            region["polygon"] = [
                [float(point[0]) * scale_x, float(point[1]) * scale_y]
                for point in polygon
                if len(point) >= 2
            ]
        scaled.append(region)
    return scaled


def _cache_enabled() -> bool:
    v = os.environ.get("SPB_SMART_TGA_GPU_CACHE", "1").strip().lower()
    return v not in {"0", "false", "off", "no"}


def _file_fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dependency_stamp() -> str:
    parts = [_CACHE_VERSION]
    for p in (_SCRIPT, _MODEL, _SAM, _MODEL_META):
        try:
            st = p.stat()
            parts.append(f"{p.name}:{int(st.st_mtime_ns)}:{st.st_size}")
        except OSError:
            parts.append(f"{p.name}:missing")
    return "|".join(parts)


def _worker_env_stamp(target_shape: tuple[int, int]) -> str:
    auto_work = str(max(512, min(1024, max(target_shape))))
    env_defaults = {
        "SEP_WORK": auto_work,
        "SEP_OCR_MODE": "adaptive",
        "SEP_OCR_ADAPTIVE_ROT_SEC": "8.0",
        "SEP_OCR_ADAPTIVE_MIN_DIGITS": "12",
        "SEP_MIRROR_OCR": "1",
        "SEP_MIRROR_OCR_BROAD_MAX_DIM": "0.24",
        "SEP_MIRROR_OCR_BROAD_MIN_CONF": "0.55",
        "SEP_MIRROR_OCR_SINGLETON_MIN_CONF": "0.80",
        "SEP_MIRROR_OCR_SCALE": "1.0",
        "SEP_MIRROR_OCR_ALLOW_SINGLETON": "0",
        "LOGO_MIN": "0.30",
        "LOGO_MARGIN": "0.20",
        "LOGO_MAX_AREA": "0.04",
        "NUMBER_SEG_MAX_AREA": "0",
        "NUMBER_BOX_COVER": "0.18",
        "NUMBER_SEG_MIN_INSIDE_BOX": "0.06",
        "NUMBER_MAX_DENSE_FILL": "0.88",
        "NUMBER_DENSE_FILL_MIN_AREA": "0.0015",
        "NUMBER_CLIP_CONFIRM": "1",
        "NUMBER_CLIP_REJECT_MAX_NUMBER": "0.20",
        "NUMBER_CLIP_REJECT_MIN_OTHER": "0.72",
        "NUMBER_CLIP_REJECT_MAX_TOTAL": "0.08",
        "NUMBER_REJECTED_LARGE_DIGIT_RESCUE": "0",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_COUNT": "2",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_TOTAL": "0.012",
        "NUMBER_REJECTED_LARGE_DIGIT_MAX_TOTAL": "0.075",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_AREA": "0.004",
        "NUMBER_REJECTED_LARGE_DIGIT_MAX_AREA": "0.040",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_LONG": "100",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_SHORT": "38",
        "NUMBER_REJECTED_LARGE_DIGIT_MAX_ASPECT": "4.2",
        "NUMBER_REJECTED_LARGE_DIGIT_MIN_FILL": "0.18",
        "NUMBER_REJECTED_LARGE_DIGIT_MAX_FILL": "0.88",
        "NUMBER_COMPONENT_CLEAN": "0",
        "NUMBER_COMPONENT_MIN_AREA": "0.0002",
        "NUMBER_COMPONENT_REJECT_MAX_NUMBER": "0.08",
        "NUMBER_COMPONENT_REJECT_MIN_OTHER": "0.65",
        "NUMBER_COMPONENT_WORD_OVERLAP": "0.35",
        "NUMBER_COMPONENT_MAX_REMOVE": "0.035",
        "NUMBER_LARGE_DIGIT_STROKE": "1",
        "NUMBER_LARGE_DIGIT_MIN_BOX_AREA": "0.0015",
        "NUMBER_LARGE_DIGIT_MIN_LONG": "70",
        "NUMBER_LARGE_DIGIT_MIN_SHORT": "16",
        "NUMBER_LARGE_DIGIT_MAX_ADD": "0.006",
        "NUMBER_GIANT_MONO_DIGIT": "1",
        "NUMBER_GIANT_MONO_MIN_AREA": "0.004",
        "NUMBER_GIANT_MONO_MAX_AREA": "0.06",
        "NUMBER_GIANT_MONO_MAX_ADD": "0.05",
        "NUMBER_GIANT_MONO_MAX_SAT": "26",
        "NUMBER_GIANT_MONO_MAX_CHROMA": "18",
        "NUMBER_GIANT_MONO_MAX_BBOX_SAT_FRAC": "0.18",
        "NUMBER_REPEATED_LIGHT_PLATE": "1",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_COUNT": "2",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_AREA": "0.004",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_AREA": "0.022",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_BBOX": "0.0075",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_BBOX": "0.032",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_LONG": "135",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_SHORT": "52",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_ASPECT": "1.45",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_ASPECT": "3.0",
        "NUMBER_REPEATED_LIGHT_PLATE_MIN_FILL": "0.35",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_FILL": "0.78",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_SAT90": "105",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_CHROMA90": "62",
        "NUMBER_REPEATED_LIGHT_PLATE_GEOM_TOL": "0.35",
        "NUMBER_REPEATED_LIGHT_PLATE_MAX_ADD": "0.035",
        "NUMBER_ROUND_ZERO_BADGE": "1",
        "NUMBER_ROUND_ZERO_MIN_RADIUS": "34",
        "NUMBER_ROUND_ZERO_MAX_RADIUS": "125",
        "NUMBER_ROUND_ZERO_MIN_RING_RED": "0.38",
        "NUMBER_ROUND_ZERO_MIN_RING_RATIO": "2.1",
        "NUMBER_ROUND_ZERO_MAX_DISK_RED": "0.24",
        "NUMBER_ROUND_ZERO_MIN_CANDIDATES": "2",
        "NUMBER_ROUND_ZERO_MAX_ADD": "0.04",
        "NUMBER_ROUND_ZERO_MASK_MODE": "stroke",
        "NUMBER_ROUND_ZERO_STROKE_INNER_RATIO": "0.62",
        "NUMBER_ROUND_ZERO_STROKE_OUTER_RING_RATIO": "0.76",
        "NUMBER_ROUND_ZERO_STROKE_HALO_RATIO": "1.15",
        "NUMBER_COMPANION_SUPPLEMENT": "1",
        "NUMBER_COMPANION_SOURCE_MAX": "0.16",
        "NUMBER_COMPANION_MAX": "0.075",
        "NUMBER_COMPANION_LOOSE_MAX": "0.16",
        "NUMBER_COMPANION_REPLACE": "1",
        "TEXT_STROKE_SUPPLEMENT": "1",
        "TEXT_STROKE_MAX_ADD": "0.008",
    }
    return "|".join(f"{k}={os.environ.get(k, default)}" for k, default in env_defaults.items())


def _cache_dir(image_path: str, target_shape: tuple[int, int]) -> Path | None:
    if not _cache_enabled():
        return None
    try:
        src = Path(image_path)
        h = hashlib.sha256()
        h.update(_file_fingerprint(src).encode("ascii"))
        h.update(str(tuple(int(v) for v in target_shape)).encode("ascii"))
        h.update(_dependency_stamp().encode("utf-8"))
        h.update(_worker_env_stamp(target_shape).encode("utf-8"))
        return _CACHE_ROOT / h.hexdigest()[:32]
    except Exception:
        return None


def _read_cached_masks(cache_dir: Path, target_shape: tuple[int, int]) -> dict[str, np.ndarray] | None:
    required = ["numbers", "text", "logos", "paint"]
    try:
        if not (cache_dir / "complete.txt").is_file():
            return None
        if not all((cache_dir / f"{k}.png").is_file() for k in required):
            return None
        ocr_path = cache_dir / "ocr_regions.json"
        if not ocr_path.is_file():
            return None
        result = {k: _read_mask(cache_dir / f"{k}.png", target_shape) for k in required}
        result["_ocr_regions"] = _read_ocr_regions(ocr_path, target_shape)
        return result
    except Exception as exc:
        print(f"[SmartTGA GPU] cache miss: {exc}")
        return None


def _write_cached_masks(cache_dir: Path, source_dir: Path) -> None:
    required = ["numbers", "text", "logos", "paint"]
    try:
        tmp = cache_dir.with_name(cache_dir.name + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        for k in required:
            shutil.copyfile(source_dir / f"{k}.png", tmp / f"{k}.png")
        shutil.copyfile(source_dir / "ocr_regions.json", tmp / "ocr_regions.json")
        (tmp / "complete.txt").write_text("ok\n", encoding="ascii")
        shutil.rmtree(cache_dir, ignore_errors=True)
        tmp.rename(cache_dir)
    except Exception as exc:
        print(f"[SmartTGA GPU] cache write skipped: {exc}")


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:80] or "paint"


def _copy_worker_profile(source_dir: Path, image_path: str, cache_key: str | None) -> str | None:
    """Persist _separate_image.py profile.json when explicitly requested."""
    profile_dir = os.environ.get("SPB_SMART_TGA_PROFILE_DIR")
    if not profile_dir:
        return None
    src = source_dir / "profile.json"
    if not src.is_file():
        return None
    try:
        dst_dir = Path(profile_dir)
        if not dst_dir.is_absolute():
            dst_dir = _ROOT / dst_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_name(Path(image_path).stem)
        suffix = cache_key or str(int(time.time() * 1000))
        dst = dst_dir / f"{stem}_{suffix}_profile.json"
        shutil.copyfile(src, dst)
        return str(dst)
    except Exception as exc:
        print(f"[SmartTGA GPU] profile copy skipped: {exc}")
        return None


def separate_file_if_available(image_path: str, target_shape: tuple[int, int]) -> dict[str, np.ndarray] | None:
    """Return GPU masks resized to target_shape, or None for graceful fallback.

    Output keys match _separate_image.py: numbers, text, logos, paint.
    """
    gpu_ok, unavailable_reason = _availability()
    if not gpu_ok:
        _set_last_info(available=False, cache="unavailable", reason=unavailable_reason)
        return None

    started = time.time()
    timeout = int(os.environ.get("SPB_SMART_TGA_GPU_TIMEOUT", "240"))
    work = str(max(512, min(1024, max(target_shape))))
    py = str(_gpu_python())
    cache_dir = _cache_dir(image_path, target_shape)
    cache_key = cache_dir.name if cache_dir is not None else None
    if cache_dir is not None:
        cached = _read_cached_masks(cache_dir, target_shape)
        if cached is not None:
            print(f"[SmartTGA GPU] cache hit: {cache_dir.name}")
            _set_last_info(available=True, cache="hit", cache_key=cache_key,
                           elapsed_sec=round(time.time() - started, 3))
            return cached
    elif not _cache_enabled():
        _set_last_info(available=True, cache="off")

    tmp = tempfile.mkdtemp(prefix="spb_smart_tga_gpu_")
    try:
        env = os.environ.copy()
        env.setdefault("SEP_WORK", work)
        proc = subprocess.run(
            [py, str(_SCRIPT), image_path, tmp],
            cwd=str(_ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            print(f"[SmartTGA GPU] fallback: _separate_image.py exited {proc.returncode}: {(proc.stderr or proc.stdout)[-800:]}")
            _set_last_info(available=True, cache="fallback", cache_key=cache_key,
                           elapsed_sec=round(time.time() - started, 3))
            return None

        out = Path(tmp)
        required = ["numbers", "text", "logos", "paint"]
        if not all((out / f"{k}.png").is_file() for k in required):
            print("[SmartTGA GPU] fallback: missing one or more mask outputs")
            _set_last_info(available=True, cache="fallback", cache_key=cache_key,
                           elapsed_sec=round(time.time() - started, 3))
            return None

        cache_status = "off"
        if cache_dir is not None:
            _write_cached_masks(cache_dir, out)
            cache_status = "miss"

        profile_path = _copy_worker_profile(out, image_path, cache_key)
        _set_last_info(available=True, cache=cache_status, cache_key=cache_key,
                       elapsed_sec=round(time.time() - started, 3), profile_path=profile_path)
        ocr_path = out / "ocr_regions.json"
        if not ocr_path.is_file():
            print("[SmartTGA GPU] fallback: missing OCR provenance output")
            return None
        result = {k: _read_mask(out / f"{k}.png", target_shape) for k in required}
        result["_ocr_regions"] = _read_ocr_regions(ocr_path, target_shape)
        return result
    except subprocess.TimeoutExpired:
        print(f"[SmartTGA GPU] fallback: timeout after {timeout}s")
        _set_last_info(available=True, cache="timeout", cache_key=cache_key,
                       elapsed_sec=round(time.time() - started, 3))
        return None
    except Exception as exc:
        print(f"[SmartTGA GPU] fallback: {exc}")
        _set_last_info(available=True, cache="error", cache_key=cache_key,
                       elapsed_sec=round(time.time() - started, 3))
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
