"""Import pipeline for USER IMPORTS — normalize paint plates and bake/detect spec maps."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from engine.paint_v2.user_imports_spec_dna import (
    bake_import_spec_dna,
    content_aware_square,
    dna_metadata,
    make_import_preview_payload,
    make_paint_channel_split,
    make_preview_combined,
    pil_to_data_url,
    render_spec_channel_rgb,
    spec_to_rgb_preview,
    suggest_import_intent,
)
from engine.paint_v2.user_imports_paths import (
    CANVAS_SIZE,
    CATEGORY_NAME,
    DROP_PACK_EXT,
    ID_PREFIX,
    SCHEMA_VERSION,
    is_drop_pack_filename,
    user_imports_root,
)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tga", ".bmp"}

_COMMUNITY_PACK_MAX_BYTES = 32 * 1024 * 1024
_COMMUNITY_MEMBER_MAX_BYTES = 24 * 1024 * 1024
_COMMUNITY_TOTAL_MAX_BYTES = 64 * 1024 * 1024
_COMMUNITY_MAX_MEMBERS = 24
_COMMUNITY_MAX_RATIO = 120
_COMMUNITY_ALLOWED_FIXED = {"manifest.json", "dna.json", "preview.png", "readme.txt"}
_COMMUNITY_ALLOWED_SUFFIXES = (
    ".png", "_spec.png", "_metallic.png", "_roughness.png",
    "_pattern.png", "_spec_overlay.png", "_preview.png",
)


def _load_viva_builder():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "build_cultural_viva_mexico.py"
    spec = importlib.util.spec_from_file_location("build_cultural_viva_mexico", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load spec builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slugify(text: str) -> str:
    text = (text or "import").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "import"
    if text[0].isdigit():
        text = "x_" + text
    slug = text[:40]
    return f"{ID_PREFIX}{slug}"


def unique_finish_id(root: Path, base_slug: str, manifest: dict) -> str:
    existing = {e.get("id") for e in manifest.get("entries", [])}
    candidate = base_slug
    n = 2
    while candidate in existing or (root / f"{candidate}.png").exists():
        candidate = f"{base_slug}_{n}"
        n += 1
    return candidate


def normalize_paint_image(img: Image.Image, *, smart_crop: bool = False) -> Image.Image:
    """Stretch/compact ANY imported image to FILL the full 2048x2048 canvas.

    Owner-requested fill behavior: the whole image is resized to exactly
    CANVAS_SIZE x CANVAS_SIZE (no center-crop that discards edges). Pass
    smart_crop=True to opt into the legacy content-aware square crop first
    (still ends fill-to-canvas, never losing the chosen square's content).
    """
    if smart_crop:
        img = content_aware_square(img)
    img = img.convert("RGB")
    # Stretch/compact the WHOLE image to exactly the canvas — fill, no crop-away.
    plate = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
    plate = ImageEnhance.Color(plate).enhance(1.08)
    plate = ImageEnhance.Contrast(plate).enhance(1.10)
    plate = ImageEnhance.Sharpness(plate).enhance(1.12)
    return plate.filter(ImageFilter.UnsharpMask(radius=1.0, percent=75, threshold=2))


def swatch_hex(img: Image.Image) -> str:
    sample = img.resize((32, 32), Image.Resampling.LANCZOS)
    arr = np.asarray(sample, dtype=np.uint8)
    r, g, b = int(arr[:, :, 0].mean()), int(arr[:, :, 1].mean()), int(arr[:, :, 2].mean())
    return f"#{r:02x}{g:02x}{b:02x}"


def bake_auto_spec(
    paint: Image.Image,
    name: str,
    vibe_ref: Optional[str] = None,
    style_override: Optional[str] = None,
) -> Tuple[Image.Image, dict]:
    result = bake_import_spec_dna(
        paint, name, vibe_ref=vibe_ref, style_override=style_override, run_gauntlet=True
    )
    return result.spec, dna_metadata(result)


def preview_import(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    vibe_ref: Optional[str] = None,
    style_override: Optional[str] = None,
) -> dict:
    """Analyze + DNA bake without saving to library."""
    paint_path = None
    for name, path in saved_files:
        ext = Path(name).suffix.lower()
        if ext in _IMAGE_EXTS and "spec" not in name.lower():
            paint_path = path
            break
    if paint_path is None:
        raise ValueError("No paint image in upload")
    raw = Image.open(paint_path)
    name = (display_name or paint_path.stem).strip() or paint_path.stem
    paint_img = normalize_paint_image(raw)
    spec_mode, _ = detect_spec_mode({n: p for n, p in saved_files}, paint_path.stem)
    if spec_mode != "auto":
        raise ValueError("Preview only supports auto-spec paint imports")
    spec_img, dna = bake_auto_spec(paint_img, name, vibe_ref=vibe_ref, style_override=style_override)
    previews = make_import_preview_payload(paint_img, spec_img)
    intent = suggest_import_intent(raw)
    return {
        **previews,
        "suggested_intent": intent,
        "dna": dna,
        "name": name,
    }


def preview_fracture_import(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
) -> dict:
    """Preview the FRACTURE auto-derive without saving — ignite the paint's own geometry.

    [SPB FRACTURE auto-derive 2026-06-16] Mirrors import_paint_files(fracture=True): the spec is
    FRACTURE-derived from the paint (near-chrome metal, maxed clearcoat, roughness woven along the
    art's edges) rather than auto-DNA baked, so the BEFORE-commit preview matches what saves.
    """
    from engine.spec_sculpt.fracture import fracture_spec

    paint_path = None
    for name, path in saved_files:
        ext = Path(name).suffix.lower()
        if ext in _IMAGE_EXTS and "spec" not in name.lower():
            paint_path = path
            break
    if paint_path is None:
        raise ValueError("No paint image in upload")
    raw = Image.open(paint_path)
    name = (display_name or paint_path.stem).strip() or paint_path.stem
    paint_img = normalize_paint_image(raw)
    tex = np.asarray(paint_img.convert("RGB"), dtype=np.float32) / 255.0
    mask = np.ones(tex.shape[:2], dtype=np.float32)
    spec_arr = fracture_spec(tex, mask, as_uint8=True)
    spec_img = Image.fromarray(spec_arr, "RGBA")
    return {
        **make_import_preview_payload(paint_img, spec_img),
        "suggested_intent": "paint",
        "preview_kind": "paint",
        "name": name,
        "spec_source": "fractured",
    }


def normalize_spec_rgba(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    if img.size != (CANVAS_SIZE, CANVAS_SIZE):
        img = img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
    return img


def _clamp_spec_strength(value: Any, default: float = 1.0) -> float:
    try:
        return float(max(0.0, min(2.0, float(value))))
    except (TypeError, ValueError):
        return default


def normalize_spec_channel_strengths(
    *,
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
    legacy_channel: Optional[str] = None,
    legacy_strengths: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Per-finish M/R/CC multipliers for authored spec overlay plates."""
    if legacy_strengths:
        return {
            "M": _clamp_spec_strength(legacy_strengths.get("M", 1.0)),
            "R": _clamp_spec_strength(legacy_strengths.get("R", 1.0)),
            "C": _clamp_spec_strength(legacy_strengths.get("C", legacy_strengths.get("Cc", 1.0))),
        }
    if spec_m is not None or spec_r is not None or spec_c is not None:
        return {
            "M": _clamp_spec_strength(spec_m if spec_m is not None else 1.0),
            "R": _clamp_spec_strength(spec_r if spec_r is not None else 1.0),
            "C": _clamp_spec_strength(spec_c if spec_c is not None else 1.0),
        }
    if legacy_channel:
        ch = legacy_channel if legacy_channel in {"M", "R", "C", "Cc"} else "M"
        base = {"M": 0.0, "R": 0.0, "C": 0.0}
        key = "C" if ch in {"C", "Cc"} else ch
        base[key] = 1.0
        return base
    return {"M": 1.0, "R": 1.0, "C": 1.0}


def entry_spec_channel_strengths(entry: dict) -> Dict[str, float]:
    return normalize_spec_channel_strengths(
        legacy_strengths=entry.get("spec_channel_strengths"),
        legacy_channel=entry.get("spec_channel"),
    )


def make_spec_overlay_preview_payload(spec_img: Image.Image, *, thumb: int = 384) -> dict:
    """SHOKK DROP spec overlay preview — upload plate + M/R/CC channel views."""
    sq = thumb
    rgba = spec_img.convert("RGBA").resize((sq, sq), Image.Resampling.LANCZOS)
    s_sq = spec_to_rgb_preview(spec_img).resize((sq, sq), Image.Resampling.LANCZOS)
    return {
        "preview": pil_to_data_url(s_sq),
        "preview_paint": pil_to_data_url(rgba.convert("RGB")),
        "preview_spec": pil_to_data_url(s_sq),
        "preview_channels": {
            "r": pil_to_data_url(render_spec_channel_rgb(spec_img, "r").resize((sq, sq), Image.Resampling.LANCZOS)),
            "g": pil_to_data_url(render_spec_channel_rgb(spec_img, "g").resize((sq, sq), Image.Resampling.LANCZOS)),
            "b": pil_to_data_url(render_spec_channel_rgb(spec_img, "b").resize((sq, sq), Image.Resampling.LANCZOS)),
        },
    }


def preview_spec_overlay_import(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
) -> dict:
    """Analyze authored spec overlay without saving to library."""
    src_name, src_path = _first_image_file(saved_files)
    raw = Image.open(src_path)
    name = (display_name or Path(src_name).stem).strip() or Path(src_name).stem
    spec_img = normalize_spec_rgba(raw)
    strengths = normalize_spec_channel_strengths(spec_m=spec_m, spec_r=spec_r, spec_c=spec_c)
    return {
        **make_spec_overlay_preview_payload(spec_img),
        "suggested_intent": "spec_overlay",
        "preview_kind": "spec_overlay",
        "name": name,
        "spec_channel_strengths": strengths,
    }


def normalize_gray(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    if gray.size != (CANVAS_SIZE, CANVAS_SIZE):
        gray = gray.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
    return gray


def _read_manifest(root: Path) -> dict:
    # [2026-09-05 codebase-health S3] a corrupt manifest is quarantined (<file>.corrupt-<ts>)
    # and logged instead of silently emptying the whole user-import catalog.
    from engine.atomic_io import atomic_write_json, load_json_guarded
    path = root / "manifest.json"
    fresh = lambda: {"schema_version": SCHEMA_VERSION, "category": CATEGORY_NAME, "entries": []}
    if not path.exists():
        data = fresh()
        atomic_write_json(path, data, indent=2, ensure_ascii=True)
        return data
    data = load_json_guarded(path, default=fresh, what="user_imports/manifest.json")
    return data if isinstance(data, dict) else fresh()


def _write_manifest(root: Path, manifest: dict) -> None:
    # [2026-09-05 codebase-health S3] atomic write (temp + os.replace)
    from engine.atomic_io import atomic_write_json
    atomic_write_json(root / "manifest.json", manifest, indent=2, ensure_ascii=False)


def detect_spec_mode(files: Dict[str, Path], paint_stem: str) -> Tuple[str, Dict[str, Path]]:
    """Return (spec_mode, companion_paths). spec_mode: auto | combined_spec | metallic_roughness."""
    stem = paint_stem.lower()
    for key, path in files.items():
        k = key.lower()
        if k.endswith("_spec.png") or k.endswith("_spec.jpg") or k.endswith("_spec.jpeg"):
            return "combined_spec", {"spec": path}
        if k.endswith("_metallic.png") or k.endswith("_metallic.jpg"):
            for key2, path2 in files.items():
                k2 = key2.lower()
                if "rough" in k2 and k2.rsplit(".", 1)[-1] in {"png", "jpg", "jpeg"}:
                    return "metallic_roughness", {"metallic": path, "roughness": path2}
    # loose pairing by stem prefix
    spec_candidates = [p for n, p in files.items() if "spec" in n.lower() and n != paint_stem]
    if spec_candidates:
        return "combined_spec", {"spec": spec_candidates[0]}
    met = [p for n, p in files.items() if "metallic" in n.lower()]
    rough = [p for n, p in files.items() if "rough" in n.lower()]
    if met and rough:
        return "metallic_roughness", {"metallic": met[0], "roughness": rough[0]}
    return "auto", {}


# Authored-spec channel convention (matches /api/export-spec-channels):
#   R -> Metallic, G -> Roughness, B -> Clearcoat, A -> Spec Mask.
_SPEC_CHANNEL_KEYS = {
    "metallic": {"metallic", "metal", "_m", "_r_", "channel_r", "spec_metallic"},
    "roughness": {"roughness", "rough", "_g_", "channel_g", "spec_roughness"},
    "clearcoat": {"clearcoat", "clear", "_cc", "_b_", "channel_b", "spec_clearcoat", "coat"},
}


def _match_channel_file(files: Dict[str, Path], tokens: set) -> Optional[Path]:
    for name, path in files.items():
        low = name.lower()
        if any(tok in low for tok in tokens):
            return path
    return None


def combine_channel_specs(
    *,
    metallic: Optional[Image.Image] = None,
    roughness: Optional[Image.Image] = None,
    clearcoat: Optional[Image.Image] = None,
    mask: Optional[Image.Image] = None,
) -> Image.Image:
    """Combine separate grayscale R/G/B(/A) channel plates into ONE RGBA spec map.

    R=Metallic, G=Roughness, B=Clearcoat, A=Spec Mask — verbatim, no DNA bake.
    Missing channels fill with 0 (mask defaults to fully opaque 255).
    """
    size = (CANVAS_SIZE, CANVAS_SIZE)
    zero = np.zeros(size, dtype=np.uint8)

    def _band(img: Optional[Image.Image], default: np.ndarray) -> np.ndarray:
        if img is None:
            return default
        gray = img.convert("L")
        if gray.size != size:
            gray = gray.resize(size, Image.Resampling.LANCZOS)
        return np.asarray(gray, dtype=np.uint8)

    r = _band(metallic, zero)
    g = _band(roughness, zero)
    b = _band(clearcoat, zero)
    a = _band(mask, np.full(size, 255, dtype=np.uint8))
    rgba = np.stack([r, g, b, a], axis=-1)
    return Image.fromarray(rgba, "RGBA")


def resolve_authored_spec(
    file_map: Dict[str, Path],
    paint_stem: str,
    *,
    spec_path: Optional[Path] = None,
) -> Tuple[Image.Image, str]:
    """Build an authored RGBA spec from a combined plate OR separate R/G/B plates.

    Returns (spec_rgba_2048, source_desc). Used verbatim — NO DNA bake.
    """
    if spec_path is not None:
        return normalize_spec_rgba(Image.open(spec_path)), "combined_spec"

    spec_mode, companions = detect_spec_mode(file_map, paint_stem)
    if spec_mode == "combined_spec":
        return normalize_spec_rgba(Image.open(companions["spec"])), "combined_spec"
    if spec_mode == "metallic_roughness":
        spec = combine_channel_specs(
            metallic=Image.open(companions["metallic"]),
            roughness=Image.open(companions["roughness"]),
        )
        return spec, "metallic_roughness"

    # Separate R/G/B(/A) channel plates by filename token.
    met = _match_channel_file(file_map, _SPEC_CHANNEL_KEYS["metallic"])
    rough = _match_channel_file(file_map, _SPEC_CHANNEL_KEYS["roughness"])
    clear = _match_channel_file(file_map, _SPEC_CHANNEL_KEYS["clearcoat"])
    if met or rough or clear:
        spec = combine_channel_specs(
            metallic=Image.open(met) if met else None,
            roughness=Image.open(rough) if rough else None,
            clearcoat=Image.open(clear) if clear else None,
        )
        return spec, "channel_split"

    raise ValueError(
        "No authored spec found — supply a combined _spec image or separate "
        "metallic/roughness/clearcoat channel images."
    )


def import_paint_files(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    vibe_ref: Optional[str] = None,
    also_pattern: bool = False,
    style_override: Optional[str] = None,
    fracture: bool = False,
) -> dict:
    """Import one paint finish from saved temp files. Returns manifest entry.

    fracture=True (no authored spec channels): tag the entry spec_mode="fractured"
    so the spec is FRACTURE-derived from the paint at render time (engine ignition)
    instead of the auto-DNA Viva bake. The paint plate is the only asset saved.
    """
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)

    paint_path = None
    file_map: Dict[str, Path] = {}
    for name, path in saved_files:
        file_map[name] = path
        ext = Path(name).suffix.lower()
        if ext in _IMAGE_EXTS and "spec" not in name.lower() and "metallic" not in name.lower() and "rough" not in name.lower():
            if paint_path is None:
                paint_path = path

    if paint_path is None:
        raise ValueError("No paint image found in upload (PNG/JPEG required)")

    paint_stem = Path(paint_path.name).stem
    name = (display_name or paint_stem).strip() or paint_stem
    finish_id = unique_finish_id(root, slugify(name), manifest)
    spec_mode, companions = detect_spec_mode(file_map, paint_stem)

    paint_img = normalize_paint_image(Image.open(paint_path))
    paint_out = root / f"{finish_id}.png"
    paint_img.save(paint_out, "PNG", optimize=True)

    entry: Dict[str, Any] = {
        "id": finish_id,
        "name": name,
        "kind": "paint_monolithic",
        "spec_mode": spec_mode,
        "swatch": swatch_hex(paint_img),
        "imported": datetime.now(timezone.utc).isoformat(),
        "source_file": paint_path.name,
    }

    if spec_mode == "combined_spec":
        spec_img = normalize_spec_rgba(Image.open(companions["spec"]))
        spec_out = root / f"{finish_id}_spec.png"
        spec_img.save(spec_out, "PNG", optimize=True)
    elif spec_mode == "metallic_roughness":
        met_out = root / f"{finish_id}_metallic.png"
        rough_out = root / f"{finish_id}_roughness.png"
        normalize_gray(Image.open(companions["metallic"])).save(met_out, "PNG", optimize=True)
        normalize_gray(Image.open(companions["roughness"])).save(rough_out, "PNG", optimize=True)
        entry["invert_roughness"] = False
    elif fracture:
        # [SPB FRACTURE auto-derive 2026-06-16] Owner dropped ONLY a paint and chose "FRACTURE
        # the spec". No spec PNG is baked — the spec is FRACTURE-derived from the paint plate at
        # render time (_spec_from_fracture). Just tag the mode so _make_spec_fn routes there.
        entry["spec_mode"] = "fractured"
    else:
        spec_img, dna = bake_auto_spec(paint_img, name, vibe_ref=vibe_ref, style_override=style_override)
        spec_out = root / f"{finish_id}_spec.png"
        spec_img.save(spec_out, "PNG", optimize=True)
        entry["spec_mode"] = "auto_dna"
        entry["import_dna"] = dna

    manifest.setdefault("entries", []).append(entry)
    if also_pattern:
        pat_id = f"{finish_id}_pat"
        pat_out = root / f"{pat_id}_pattern.png"
        paint_img.save(pat_out, "PNG", optimize=True)
        pat_entry = {
            "id": pat_id,
            "name": name + " (pattern)",
            "kind": "pattern",
            "intent": "pattern_design",
            "swatch": entry["swatch"],
            "imported": entry["imported"],
            "source_file": entry["source_file"],
            "linked_paint_id": finish_id,
        }
        manifest["entries"].append(pat_entry)

    if entry.get("spec_mode", "").startswith("auto") and (root / f"{finish_id}_spec.png").exists():
        try:
            combo = make_preview_combined(paint_img, Image.open(root / f"{finish_id}_spec.png"))
            combo.save(root / f"{finish_id}_preview.png", "PNG", optimize=True)
        except Exception:
            pass

    _write_manifest(root, manifest)
    return entry


def import_paint_with_spec_files(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    kind: str = "paint",
    also_pattern: bool = False,
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
) -> dict:
    """Import a PAINT image + AUTHORED spec map as an EXACT finish (NO DNA bake).

    The user supplies a paint image plus EITHER a combined SPEC image
    (RGB = M/R/Cc, auto-split) OR separate R/G/B channel images (combined).
    Spec is saved verbatim. kind: "paint" (paint finish), "pattern", or
    "spec_overlay".
    """
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)

    kind = (kind or "paint").strip().lower()
    file_map: Dict[str, Path] = {name: path for name, path in saved_files}

    # The paint plate = first non-spec/non-channel image.
    paint_path = None
    for name, path in saved_files:
        ext = Path(name).suffix.lower()
        low = name.lower()
        if ext not in _IMAGE_EXTS:
            continue
        if any(tok in low for tok in (
            "spec", "metallic", "metal", "rough", "clear", "coat", "channel_",
        )):
            continue
        paint_path = path
        break
    if paint_path is None:
        raise ValueError("No paint image found in upload (PNG/JPEG required)")

    paint_stem = Path(paint_path.name).stem
    name = (display_name or paint_stem).strip() or paint_stem
    spec_img, spec_source = resolve_authored_spec(file_map, paint_stem)

    finish_id = unique_finish_id(root, slugify(name), manifest)
    paint_img = normalize_paint_image(Image.open(paint_path))

    if kind == "spec_overlay":
        out = root / f"{finish_id}_spec_overlay.png"
        spec_img.save(out, "PNG", optimize=True)
        strengths = normalize_spec_channel_strengths(spec_m=spec_m, spec_r=spec_r, spec_c=spec_c)
        try:
            spec_to_rgb_preview(spec_img).save(root / f"{finish_id}_preview.png", "PNG", optimize=True)
        except Exception:
            pass
        entry: Dict[str, Any] = {
            "id": finish_id,
            "name": name,
            "kind": "spec_overlay",
            "spec_mode": "authored_set",
            "spec_source": spec_source,
            "spec_channel_strengths": strengths,
            "swatch": swatch_hex(spec_img.convert("RGB")),
            "imported": datetime.now(timezone.utc).isoformat(),
            "source_file": paint_path.name,
        }
        manifest.setdefault("entries", []).append(entry)
        _write_manifest(root, manifest)
        return entry

    # Paint finish OR pattern — paint + verbatim spec (exact, no DNA bake).
    if kind == "pattern":
        pat_img = normalize_pattern_image(Image.open(paint_path))
        pat_img.save(root / f"{finish_id}_pattern.png", "PNG", optimize=True)
        swatch_src = pat_img.convert("RGB") if pat_img.mode == "RGBA" else pat_img
        entry = {
            "id": finish_id,
            "name": name,
            "kind": "pattern",
            "intent": "pattern_design",
            "spec_mode": "authored_set",
            "spec_source": spec_source,
            "swatch": swatch_hex(swatch_src),
            "imported": datetime.now(timezone.utc).isoformat(),
            "source_file": paint_path.name,
        }
    else:
        paint_img.save(root / f"{finish_id}.png", "PNG", optimize=True)
        entry = {
            "id": finish_id,
            "name": name,
            "kind": "paint_monolithic",
            "spec_mode": "authored_set",
            "spec_source": spec_source,
            "swatch": swatch_hex(paint_img),
            "imported": datetime.now(timezone.utc).isoformat(),
            "source_file": paint_path.name,
        }

    spec_img.save(root / f"{finish_id}_spec.png", "PNG", optimize=True)

    manifest.setdefault("entries", []).append(entry)

    if also_pattern and kind != "pattern":
        pat_id = f"{finish_id}_pat"
        normalize_pattern_image(Image.open(paint_path)).save(
            root / f"{pat_id}_pattern.png", "PNG", optimize=True
        )
        manifest["entries"].append({
            "id": pat_id,
            "name": name + " (pattern)",
            "kind": "pattern",
            "intent": "pattern_design",
            "swatch": entry["swatch"],
            "imported": entry["imported"],
            "source_file": entry["source_file"],
            "linked_paint_id": finish_id,
        })

    try:
        combo = make_preview_combined(paint_img.convert("RGB"), spec_img)
        combo.save(root / f"{finish_id}_preview.png", "PNG", optimize=True)
    except Exception:
        pass

    _write_manifest(root, manifest)
    return entry


def preview_paint_with_spec_files(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    kind: str = "paint",
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
) -> dict:
    """LIVE preview of a PAINT + AUTHORED spec set — SAVES NOTHING.

    Byte-faithful to import_paint_with_spec_files: resolve_authored_spec builds
    the authored RGBA spec from EITHER a combined plate (RGB = M/R/Cc auto-split)
    OR separate R/G/B channel plates — verbatim, NO DNA bake. The preview the
    user sees BEFORE commit is exactly what import will save.

    kind: "paint" / "pattern" (paint cell + blended spec + R/G/B channel tiles)
    or "spec_overlay" (paint is discarded; spec-only overlay preview).
    If no paint plate is supplied yet, the spec/channel preview still renders
    (paint cell may be blank).
    """
    kind = (kind or "paint").strip().lower()
    file_map: Dict[str, Path] = {name: path for name, path in saved_files}

    # The paint plate = first non-spec/non-channel image (mirror import loop).
    paint_path = None
    for name, path in saved_files:
        ext = Path(name).suffix.lower()
        low = name.lower()
        if ext not in _IMAGE_EXTS:
            continue
        if any(tok in low for tok in (
            "spec", "metallic", "metal", "rough", "clear", "coat", "channel_",
        )):
            continue
        paint_path = path
        break

    paint_stem = Path(paint_path.name).stem if paint_path is not None else ""
    name = (display_name or paint_stem).strip() or (paint_stem or "Untitled")

    spec_img, spec_source = resolve_authored_spec(file_map, paint_stem)

    if kind == "spec_overlay":
        # Paint is discarded in overlay mode — reflect that honestly.
        strengths = normalize_spec_channel_strengths(spec_m=spec_m, spec_r=spec_r, spec_c=spec_c)
        return {
            **make_spec_overlay_preview_payload(spec_img),
            "name": name,
            "spec_source": spec_source,
            "preview_kind": "paint_spec_set",
            "suggested_intent": "spec_overlay",
            "spec_channel_strengths": strengths,
        }

    if paint_path is not None:
        paint_img = normalize_paint_image(Image.open(paint_path))
    else:
        # No paint plate yet — blank canvas so the spec/channel tiles still show.
        paint_img = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), (24, 24, 24))

    return {
        **make_import_preview_payload(paint_img, spec_img),
        "name": name,
        "spec_source": spec_source,
        "preview_kind": "paint_spec_set",
    }


def normalize_pattern_image(img: Image.Image) -> Image.Image:
    """Center-crop + resize pattern plate; preserve alpha when present."""
    if img.mode == "RGBA":
        rgb = img.convert("RGB")
        alpha = img.split()[3]
        plate = normalize_paint_image(rgb)
        alpha = alpha.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
        out = plate.convert("RGBA")
        out.putalpha(alpha)
        return out
    return normalize_paint_image(img.convert("RGB"))


def _first_image_file(saved_files: List[Tuple[str, Path]]) -> Tuple[str, Path]:
    for name, path in saved_files:
        if Path(name).suffix.lower() in _IMAGE_EXTS:
            return name, path
    raise ValueError("No image file in upload")


def import_pattern_files(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
) -> dict:
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    src_name, src_path = _first_image_file(saved_files)
    name = (display_name or Path(src_name).stem).strip() or Path(src_name).stem
    finish_id = unique_finish_id(root, slugify(name), manifest)
    img = normalize_pattern_image(Image.open(src_path))
    out = root / f"{finish_id}_pattern.png"
    img.save(out, "PNG", optimize=True)
    swatch_src = img.convert("RGB") if img.mode == "RGBA" else img
    entry = {
        "id": finish_id,
        "name": name,
        "kind": "pattern",
        "intent": "pattern_design",
        "swatch": swatch_hex(swatch_src),
        "imported": datetime.now(timezone.utc).isoformat(),
        "source_file": src_name,
    }
    manifest.setdefault("entries", []).append(entry)
    _write_manifest(root, manifest)
    return entry


def import_spec_overlay_files(
    saved_files: List[Tuple[str, Path]],
    *,
    display_name: Optional[str] = None,
    spec_channel: str = "M",
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
) -> dict:
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    src_name, src_path = _first_image_file(saved_files)
    name = (display_name or Path(src_name).stem).strip() or Path(src_name).stem
    finish_id = unique_finish_id(root, slugify(name), manifest)
    spec_img = normalize_spec_rgba(Image.open(src_path))
    out = root / f"{finish_id}_spec_overlay.png"
    spec_img.save(out, "PNG", optimize=True)
    strengths = normalize_spec_channel_strengths(
        spec_m=spec_m,
        spec_r=spec_r,
        spec_c=spec_c,
        legacy_channel=spec_channel if spec_m is None and spec_r is None and spec_c is None else None,
    )
    preview = root / f"{finish_id}_preview.png"
    try:
        spec_to_rgb_preview(spec_img).save(preview, "PNG", optimize=True)
    except Exception:
        pass
    entry = {
        "id": finish_id,
        "name": name,
        "kind": "spec_overlay",
        "spec_channel_strengths": strengths,
        "swatch": swatch_hex(spec_img.convert("RGB")),
        "imported": datetime.now(timezone.utc).isoformat(),
        "source_file": src_name,
    }
    manifest.setdefault("entries", []).append(entry)
    _write_manifest(root, manifest)
    return entry


def update_spec_overlay_channels(
    finish_id: str,
    *,
    spec_m: Optional[float] = None,
    spec_r: Optional[float] = None,
    spec_c: Optional[float] = None,
) -> dict:
    """Update per-finish M/R/CC multipliers on an existing spec overlay drop."""
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    root = user_imports_root()
    manifest = _read_manifest(root)
    entry = next((e for e in manifest.get("entries", []) if e.get("id") == finish_id), None)
    if not entry:
        raise FileNotFoundError(finish_id)
    if entry.get("kind") != "spec_overlay":
        raise ValueError("Channel update only supports spec overlay drops")
    current = entry_spec_channel_strengths(entry)
    strengths = {
        "M": _clamp_spec_strength(spec_m if spec_m is not None else current["M"]),
        "R": _clamp_spec_strength(spec_r if spec_r is not None else current["R"]),
        "C": _clamp_spec_strength(spec_c if spec_c is not None else current["C"]),
    }
    entry["spec_channel_strengths"] = strengths
    entry.pop("spec_channel", None)
    entry["channels_updated"] = datetime.now(timezone.utc).isoformat()
    for i, e in enumerate(manifest.get("entries", [])):
        if e.get("id") == finish_id:
            manifest["entries"][i] = entry
            break
    _write_manifest(root, manifest)
    return entry


def rebake_dna_spec(
    finish_id: str,
    *,
    vibe_ref: Optional[str] = None,
    style_override: Optional[str] = None,
) -> dict:
    """Re-run Import DNA on an existing auto-spec paint import (SPB tick 4)."""
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    root = user_imports_root()
    manifest = _read_manifest(root)
    entry = next((e for e in manifest.get("entries", []) if e.get("id") == finish_id), None)
    if not entry:
        raise FileNotFoundError(finish_id)
    if entry.get("kind", "paint_monolithic") != "paint_monolithic":
        raise ValueError("Re-DNA only supports paint monolithics")
    spec_mode = entry.get("spec_mode", "")
    if not spec_mode.startswith("auto"):
        raise ValueError("Re-DNA only for auto-spec imports (not author spec maps)")
    paint_path = root / f"{finish_id}.png"
    if not paint_path.exists():
        raise FileNotFoundError(f"Paint plate missing: {finish_id}")

    paint_img = Image.open(paint_path).convert("RGB")
    name = entry.get("name", finish_id)
    spec_img, dna = bake_auto_spec(paint_img, name, vibe_ref=vibe_ref, style_override=style_override)
    spec_out = root / f"{finish_id}_spec.png"
    spec_img.save(spec_out, "PNG", optimize=True)
    entry["spec_mode"] = "auto_dna"
    entry["import_dna"] = dna
    entry["dna_rebaked"] = datetime.now(timezone.utc).isoformat()
    try:
        combo = make_preview_combined(paint_img, spec_img)
        combo.save(root / f"{finish_id}_preview.png", "PNG", optimize=True)
    except Exception:
        pass
    for i, e in enumerate(manifest.get("entries", [])):
        if e.get("id") == finish_id:
            manifest["entries"][i] = entry
            break
    _write_manifest(root, manifest)
    return entry


def delete_entry(finish_id: str) -> bool:
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    root = user_imports_root()
    manifest = _read_manifest(root)
    entries = manifest.get("entries", [])
    linked_ids = {e.get("id") for e in entries if e.get("linked_paint_id") == finish_id}
    new_entries = [e for e in entries if e.get("id") != finish_id and e.get("id") not in linked_ids]
    if len(new_entries) == len(entries):
        return False
    for suffix in ("", "_spec", "_metallic", "_roughness", "_pattern", "_spec_overlay", "_preview"):
        path = root / f"{finish_id}{suffix}.png"
        if path.exists():
            path.unlink()
    for lid in linked_ids:
        for suffix in ("", "_pattern", "_preview"):
            p = root / f"{lid}{suffix}.png"
            if p.exists():
                p.unlink()
    manifest["entries"] = new_entries
    _write_manifest(root, manifest)
    return True


def resolve_preview_image(finish_id: str) -> Path:
    """Return paint|spec split preview PNG path, generating if needed."""
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    root = user_imports_root()
    prev = root / f"{finish_id}_preview.png"
    if prev.exists():
        return prev
    paint_p = root / f"{finish_id}.png"
    spec_p = root / f"{finish_id}_spec.png"
    if paint_p.exists() and spec_p.exists():
        combo = make_preview_combined(Image.open(paint_p), Image.open(spec_p))
        combo.save(prev, "PNG", optimize=True)
        return prev
    for suffix in ("_pattern", "_spec_overlay", ""):
        path = root / f"{finish_id}{suffix}.png"
        if path.exists():
            return path
    raise FileNotFoundError(finish_id)


def resolve_paint_image(finish_id: str) -> Path:
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    path = user_imports_root() / f"{finish_id}.png"
    if not path.exists():
        raise FileNotFoundError(finish_id)
    return path


def resolve_spec_image(finish_id: str) -> Path:
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    path = user_imports_root() / f"{finish_id}_spec.png"
    if not path.exists():
        raise FileNotFoundError(finish_id)
    return path


def render_channel_preview_png(finish_id: str, channel: str, *, width: int = 640) -> bytes:
    """PNG bytes for paint|tinted-channel split (saved library entry)."""
    ch = channel.lower()
    if ch not in ("r", "g", "b"):
        raise ValueError("channel must be r, g, or b")
    paint = Image.open(resolve_paint_image(finish_id))
    spec = Image.open(resolve_spec_image(finish_id))
    split = make_paint_channel_split(paint, spec, ch, width=width)
    buf = BytesIO()
    split.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def resolve_spec_overlay_image(finish_id: str) -> Path:
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Invalid user import id")
    path = user_imports_root() / f"{finish_id}_spec_overlay.png"
    if not path.exists():
        raise FileNotFoundError(finish_id)
    return path


def render_spec_overlay_channel_preview_png(finish_id: str, channel: str, *, width: int = 640) -> bytes:
    """PNG bytes for upload|tinted-channel split on spec overlay drops."""
    ch = channel.lower()
    if ch not in ("r", "g", "b"):
        raise ValueError("channel must be r, g, or b")
    spec = Image.open(resolve_spec_overlay_image(finish_id))
    tint = render_spec_channel_rgb(spec, ch)
    # [ULTRACODE 2026-08-22 M2] cap request-supplied width — unbounded values
    # were an allocation bomb on this preview endpoint.
    width = min(int(width), 4096)
    h = max(128, width // 2)
    upload = spec.convert("RGB").resize((h, h), Image.Resampling.LANCZOS)
    tint = tint.resize((h, h), Image.Resampling.LANCZOS)
    combo = Image.new("RGB", (h * 2, h))
    combo.paste(upload, (0, 0))
    combo.paste(tint, (h, 0))
    buf = BytesIO()
    combo.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_spec_overlay_preview_urls(finish_id: str) -> dict:
    """Relative API URLs for spec overlay preview grid."""
    base = "/api/user-imports"
    ts = ""
    return {
        "preview_paint": f"{base}/spec-overlay-image/{finish_id}{ts}",
        "preview_spec": f"{base}/spec-overlay-preview/{finish_id}{ts}",
        "preview_channels": {
            "r": f"{base}/spec-overlay-channel/{finish_id}/r{ts}",
            "g": f"{base}/spec-overlay-channel/{finish_id}/g{ts}",
            "b": f"{base}/spec-overlay-channel/{finish_id}/b{ts}",
        },
    }


def build_saved_preview_urls(finish_id: str, *, kind: Optional[str] = None) -> dict:
    """Relative API URLs for full preview grid on committed drops."""
    if kind == "spec_overlay":
        return build_spec_overlay_preview_urls(finish_id)
    base = "/api/user-imports"
    ts = ""
    return {
        "preview_paint": f"{base}/paint-image/{finish_id}{ts}",
        "preview_spec": f"{base}/spec-image/{finish_id}{ts}",
        "preview_channels": {
            "r": f"{base}/channel-preview/{finish_id}/r{ts}",
            "g": f"{base}/channel-preview/{finish_id}/g{ts}",
            "b": f"{base}/channel-preview/{finish_id}/b{ts}",
        },
    }


def export_all_packs(dest: Path, ids: Optional[Iterable[str]] = None) -> Path:
    """Batch-export library entries as nested .spbdrop packs.

    ``ids`` (SHOKK DROP loop 2026-08-09, additive): when given, export only
    those entries and write a manifest containing just them — this powers the
    gallery's "export selected" bulk action. When ``None`` the behaviour is
    byte-for-byte the previous whole-library export.
    """
    root = user_imports_root()
    manifest = _read_manifest(root)
    entries = manifest.get("entries", [])
    if ids is not None:
        wanted = [str(i) for i in ids]
        if not wanted:
            raise ValueError("No ids given to export")
        by_id = {e.get("id"): e for e in entries}
        missing = [i for i in wanted if i not in by_id]
        if missing:
            raise FileNotFoundError("Unknown id(s): " + ", ".join(missing))
        entries = [by_id[i] for i in wanted]
        manifest = dict(manifest)
        manifest["entries"] = entries
    if not entries:
        raise ValueError("No imports to export")
    dest.parent.mkdir(parents=True, exist_ok=True)
    packs_dir = root / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr(
            "README.txt",
            "SHOKK DROP batch — import each packs/* pack via Shokk Drop Lab.\n",
        )
        for entry in entries:
            fid = entry.get("id")
            if not fid:
                continue
            pack_path = packs_dir / f"{fid}{DROP_PACK_EXT}"
            export_entry_zip(fid, pack_path)
            zf.write(pack_path, f"packs/{fid}{DROP_PACK_EXT}")
    return dest


def export_entry_zip(finish_id: str, dest: Path) -> Path:
    root = user_imports_root()
    manifest = _read_manifest(root)
    entry = next((e for e in manifest.get("entries", []) if e.get("id") == finish_id), None)
    if not entry:
        raise FileNotFoundError(finish_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        mini = {"schema_version": SCHEMA_VERSION, "category": CATEGORY_NAME, "entries": [entry]}
        zf.writestr("manifest.json", json.dumps(mini, indent=2))
        for suffix in ("", "_spec", "_metallic", "_roughness", "_pattern", "_spec_overlay"):
            path = root / f"{finish_id}{suffix}.png"
            if path.exists():
                zf.write(path, path.name)
        zf.writestr("dna.json", json.dumps(entry.get("import_dna", {}), indent=2))
        preview_path = root / f"{finish_id}_preview.png"
        if preview_path.exists():
            zf.write(preview_path, "preview.png")
        elif (root / f"{finish_id}.png").exists() and (root / f"{finish_id}_spec.png").exists():
            p = Image.open(root / f"{finish_id}.png")
            s = Image.open(root / f"{finish_id}_spec.png")
            combo = make_preview_combined(p, s)
            import io
            buf = io.BytesIO()
            combo.save(buf, format="PNG")
            zf.writestr("preview.png", buf.getvalue())
        zf.writestr(
            "README.txt",
            "SHOKK DROP pack — open in Shokk Drop Lab or Paint Booth finish picker.\n",
        )
    return dest


def validate_community_drop_pack(zip_path: Path) -> dict:
    """Strictly validate a downloaded community ``.spbdrop`` before import.

    The public service validates uploads first; this deliberately repeats the
    security boundary on the customer's machine.  No path, executable, nested
    archive, encrypted member, or oversized decompression is accepted.
    """
    path = Path(zip_path)
    if not path.is_file() or path.stat().st_size > _COMMUNITY_PACK_MAX_BYTES:
        raise ValueError("Community SHOKK DROP exceeds the 32 MB package limit")
    if not zipfile.is_zipfile(path):
        raise ValueError("Community SHOKK DROP is not a valid ZIP package")

    with zipfile.ZipFile(path, "r") as zf:
        infos = zf.infolist()
        if not infos or len(infos) > _COMMUNITY_MAX_MEMBERS:
            raise ValueError("Community SHOKK DROP has an invalid member count")
        names = []
        total_uncompressed = 0
        for info in infos:
            raw_name = info.filename.replace("\\", "/")
            if info.is_dir() or raw_name.startswith("/") or "/" in raw_name:
                raise ValueError("Community SHOKK DROP may only contain flat files")
            if raw_name in {".", ".."} or ".." in Path(raw_name).parts:
                raise ValueError("Community SHOKK DROP contains an unsafe path")
            if info.flag_bits & 0x1:
                raise ValueError("Encrypted SHOKK DROP members are not supported")
            if info.file_size > _COMMUNITY_MEMBER_MAX_BYTES:
                raise ValueError("Community SHOKK DROP member exceeds the size limit")
            total_uncompressed += info.file_size
            if total_uncompressed > _COMMUNITY_TOTAL_MAX_BYTES:
                raise ValueError("Community SHOKK DROP expands beyond the safety limit")
            if info.compress_size and info.file_size / info.compress_size > _COMMUNITY_MAX_RATIO:
                raise ValueError("Community SHOKK DROP has an unsafe compression ratio")
            names.append(raw_name)

        by_lower = {name.lower(): name for name in names}
        if len(by_lower) != len(names) or "manifest.json" not in by_lower:
            raise ValueError("Community SHOKK DROP has duplicate files or no manifest")
        try:
            pack_manifest = json.loads(zf.read(by_lower["manifest.json"]).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Community SHOKK DROP manifest is invalid") from exc
        entries = pack_manifest.get("entries") if isinstance(pack_manifest, dict) else None
        if (
            not isinstance(pack_manifest, dict)
            or pack_manifest.get("schema_version") != SCHEMA_VERSION
            or pack_manifest.get("category") != CATEGORY_NAME
            or not isinstance(entries, list)
            or len(entries) != 1
            or not isinstance(entries[0], dict)
        ):
            raise ValueError("Community SHOKK DROP manifest schema is not supported")
        entry = entries[0]
        old_id = str(entry.get("id") or "")
        if not re.fullmatch(r"ui_[a-z0-9_]{1,64}", old_id):
            raise ValueError("Community SHOKK DROP finish id is invalid")
        if entry.get("kind", "paint_monolithic") != "paint_monolithic":
            raise ValueError("Community submissions must contain one paint finish")

        required = {f"{old_id}.png", f"{old_id}_spec.png", "preview.png"}
        if not required.issubset(by_lower):
            raise ValueError("Community SHOKK DROP is missing paint, spec, or preview PNG")
        allowed = set(_COMMUNITY_ALLOWED_FIXED)
        allowed.update(old_id + suffix for suffix in _COMMUNITY_ALLOWED_SUFFIXES)
        unexpected = sorted(name for name in by_lower if name not in allowed)
        if unexpected:
            raise ValueError("Community SHOKK DROP contains unsupported files")

        verified_images = []
        for lower_name, source_name in by_lower.items():
            if not lower_name.endswith(".png"):
                continue
            try:
                with Image.open(BytesIO(zf.read(source_name))) as image:
                    width, height = image.size
                    if width < 1 or height < 1 or width > 4096 or height > 4096:
                        raise ValueError("PNG dimensions exceed the safety limit")
                    if width * height > 16_777_216:
                        raise ValueError("PNG pixel count exceeds the safety limit")
                    image.verify()
            except Exception as exc:
                raise ValueError(f"Community SHOKK DROP contains an invalid PNG: {source_name}") from exc
            verified_images.append(lower_name)

    return {
        "manifest": pack_manifest,
        "entry": entry,
        "finish_id": old_id,
        "members": len(names),
        "uncompressed_bytes": total_uncompressed,
        "verified_images": verified_images,
    }


def import_pack_zip(zip_path: Path, *, community_source: Optional[dict] = None) -> List[dict]:
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    imported: List[dict] = []
    if community_source:
        checked = validate_community_drop_pack(zip_path)
        drop_id = str(community_source.get("id") or "")
        version = int(community_source.get("version") or 1)
        for existing in manifest.get("entries", []):
            source = existing.get("community_source") or {}
            if source.get("id") == drop_id and int(source.get("version") or 1) == version:
                return [existing]
    with zipfile.ZipFile(zip_path, "r") as zf:
        pack_manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        for item in pack_manifest.get("entries", []):
            old_id = item.get("id", "")
            name = item.get("name", old_id)
            new_id = unique_finish_id(root, slugify(name), manifest)
            item = dict(item)
            item["id"] = new_id
            item["imported"] = datetime.now(timezone.utc).isoformat()
            if community_source:
                item["name"] = str(community_source.get("finish_name") or name)[:120]
                item["author"] = str(community_source.get("author_name") or "")[:120]
                item["author_website"] = str(community_source.get("website") or "")[:500]
                item["community_source"] = {
                    "id": str(community_source.get("id") or "")[:80],
                    "version": int(community_source.get("version") or 1),
                    "sha256": str(community_source.get("sha256") or "")[:64],
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                }
            for name_in_zip in zf.namelist():
                if not name_in_zip.lower().endswith(".png"):
                    continue
                base = Path(name_in_zip).name
                if base.startswith(old_id):
                    suffix = base[len(old_id):]
                    data = zf.read(name_in_zip)
                    (root / f"{new_id}{suffix}").write_bytes(data)
            manifest.setdefault("entries", []).append(item)
            imported.append(item)
    _write_manifest(root, manifest)
    return imported
