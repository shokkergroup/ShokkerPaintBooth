"""Blend Paint Booth registry finishes (bases + monolithics) into one spec map.

Uses the same ``_resolve_finish_spec`` path as ``engine.compose.mix_finishes`` so
Spec Sculpt catalog mode matches full-app material resolution. Patterns are not
included — they are overlay modifiers in the zone composer, not standalone M/R/Cc.

See ``engine.registry`` / ``BASE_REGISTRY`` / ``MONOLITHIC_REGISTRY``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib

import cv2
import numpy as np

# Match procedural preset stack depth (spec-sculpt UI).
MAX_CATALOG_STACK = 5
_CATALOG_TYPE_SEPARATOR = "::"
_CATALOG_TYPES = {"base", "monolithic"}
_PAINT_AWARE_SOURCE: ContextVar[np.ndarray | None] = ContextVar(
    "spb_catalog_paint_aware_source",
    default=None,
)


@contextmanager
def paint_aware_spatial_mix(
    source_rgb_hwc: np.ndarray,
    *,
    enabled: bool = True,
):
    """Opt one catalog blend into livery-aware spatial material routing.

    The context is deliberately scoped to one render and uses ``ContextVar`` so
    concurrent preview jobs cannot leak one car's pixels into another.  The
    source array is read-only input; no copy or mutation of diffuse paint occurs.
    Existing callers never enter this context and remain byte-identical.
    """
    if not enabled:
        yield
        return
    source = np.asarray(source_rgb_hwc)
    if source.ndim != 3 or source.shape[2] < 3:
        raise ValueError("source_rgb_hwc must be HxWx3 for paint-aware catalog mixing")
    token = _PAINT_AWARE_SOURCE.set(source[:, :, :3])
    try:
        yield
    finally:
        _PAINT_AWARE_SOURCE.reset(token)


def _split_catalog_token(value: object) -> tuple[str | None, str]:
    """Return (explicit registry, finish id) while preserving legacy bare ids."""
    raw = str(value or "").strip()
    prefix, separator, finish_id = raw.partition(_CATALOG_TYPE_SEPARATOR)
    if separator and prefix in _CATALOG_TYPES and finish_id:
        return prefix, finish_id
    return None, raw


def _catalog_token(finish_id: str, registry_type: str | None) -> str:
    return f"{registry_type}{_CATALOG_TYPE_SEPARATOR}{finish_id}" if registry_type in _CATALOG_TYPES else finish_id


def ensure_full_catalog_registries():
    """Load every shipping runtime finish into the shared catalog registries.

    ``engine.registry`` is the fast-start subset while ``shokker_engine_v2`` owns
    several lazy expansion packs. Spec Sculpt used to list one registry and
    validate against the other, which made fresh-start counts incomplete and
    could turn a visible card into an empty stack. Only missing IDs are added;
    the canonical package entries continue to win for every shared ID.
    """
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY
    import shokker_engine_v2 as runtime_engine

    runtime_engine._ensure_expansions_loaded()
    for finish_id, entry in runtime_engine.BASE_REGISTRY.items():
        BASE_REGISTRY.setdefault(finish_id, entry)
    for finish_id, entry in runtime_engine.MONOLITHIC_REGISTRY.items():
        MONOLITHIC_REGISTRY.setdefault(finish_id, entry)
    return BASE_REGISTRY, MONOLITHIC_REGISTRY


def normalize_catalog_stack(
    raw: object,
    *,
    max_layers: int = MAX_CATALOG_STACK,
) -> list[tuple[str, float]]:
    """Parse API payload into normalized ``(finish token, weight)`` rows.

    Legacy callers may send a bare id. Easy Spec Sculpt additionally sends an
    explicit ``registry_type`` so a base and monolithic that share an id remain
    two honest choices: the thumbnail's registry is the registry that renders.
    """
    BASE_REGISTRY, MONOLITHIC_REGISTRY = ensure_full_catalog_registries()

    allowed: set[str] = set(BASE_REGISTRY.keys()) | set(MONOLITHIC_REGISTRY.keys())
    items: list[tuple[str, float]] = []
    if raw is None:
        return []
    if isinstance(raw, list):
        for entry in raw[:max_layers]:
            registry_type = None
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                registry_type = str(entry[2]).strip().lower() if len(entry) >= 3 else None
                encoded_type, fid = _split_catalog_token(entry[0])
                registry_type = registry_type if registry_type in _CATALOG_TYPES else encoded_type
                try:
                    w = float(entry[1])
                except (TypeError, ValueError):
                    continue
                registry = BASE_REGISTRY if registry_type == "base" else MONOLITHIC_REGISTRY if registry_type == "monolithic" else None
                if (fid not in registry if registry is not None else fid not in allowed) or w <= 0:
                    continue
                items.append((_catalog_token(fid, registry_type), w))
            elif isinstance(entry, dict):
                encoded_type, fid = _split_catalog_token(entry.get("id") or entry.get("finish_id") or "")
                registry_type = str(entry.get("registry_type") or entry.get("catalog_type") or entry.get("swatch_type") or "").strip().lower()
                registry_type = registry_type if registry_type in _CATALOG_TYPES else encoded_type
                try:
                    w = float(entry.get("weight", 1.0))
                except (TypeError, ValueError):
                    w = 1.0
                registry = BASE_REGISTRY if registry_type == "base" else MONOLITHIC_REGISTRY if registry_type == "monolithic" else None
                if (fid not in registry if registry is not None else fid not in allowed) or w <= 0:
                    continue
                items.append((_catalog_token(fid, registry_type), w))
    if not items:
        return []
    tw = sum(w for _, w in items) or 1.0
    return [(fid, w / tw) for fid, w in items]


def _mirror_tile_to(arr: np.ndarray, H: int, W: int) -> np.ndarray:
    """Tile ``arr`` (h0×w0) up to (H×W) using REFLECT tiling so adjacent copies mirror
    at their shared edge — seamless for any content (noise, gradient, radial alike)."""
    h0, w0 = arr.shape[:2]
    ky = int(np.ceil(H / float(h0)))
    kx = int(np.ceil(W / float(w0)))
    rows = []
    for i in range(ky):
        cols = []
        for j in range(kx):
            t = arr
            if i & 1:
                t = t[::-1, ...]
            if j & 1:
                t = t[:, ::-1, ...]
            cols.append(t)
        rows.append(np.concatenate(cols, axis=1))
    grid = np.concatenate(rows, axis=0)
    return grid[:H, :W, ...]


def _full_monolithic_registry():
    """SPEC-SCULPT 2026-06-18 (overnight): `_resolve_finish_spec` defaults to
    `engine.registry.MONOLITHIC_REGISTRY` (~843), which does NOT contain the FRACTURED
    library — those finishes register only into the runtime `shokker_engine_v2`
    registry (~1339). Merge the two so Spec Sculpt can use FRACTURED finishes as
    materials. `engine.registry` entries WIN on shared keys, so every existing preset
    resolves byte-IDENTICALLY; the merge ONLY ADDS the finishes that currently fail to
    resolve (cannot regress working finishes). Returns None on any failure → caller
    falls back to the default registry (original behaviour). Not cached: registries are
    stable post-boot and the merge is cheap, but recomputing avoids any stale-before-
    expansions-loaded race."""
    try:
        import engine.registry as _R
        base = dict(getattr(_R, "MONOLITHIC_REGISTRY", {}) or {})
    except Exception:
        return None
    try:
        import shokker_engine_v2 as _E
        runtime = getattr(_E, "MONOLITHIC_REGISTRY", None)
        if runtime:
            merged = dict(runtime)   # ~1339, includes FRACTURED
            merged.update(base)      # engine.registry wins on shared keys → existing behaviour preserved
            return merged
    except Exception:
        pass
    return base or None


def _robust_unit_field(field: np.ndarray, coverage: np.ndarray) -> np.ndarray:
    """Normalize a livery cue to 0..1 without letting one outlier own the mix."""
    a = np.asarray(field, dtype=np.float32)
    selected = a[np.asarray(coverage, dtype=np.float32) > 0.05]
    if selected.size < 16:
        selected = a.reshape(-1)
    lo, hi = np.percentile(selected, (8.0, 92.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or float(hi - lo) < 1.0e-5:
        return np.full(a.shape, 0.5, dtype=np.float32)
    return np.clip((a - float(lo)) / float(hi - lo), 0.0, 1.0).astype(np.float32)


def _rank_roles(values: np.ndarray, tokens: list[str]) -> np.ndarray:
    """Return stable -1..1 material roles, resolving equal stats by finish id."""
    count = len(tokens)
    if count <= 1:
        return np.zeros(count, dtype=np.float32)
    order = sorted(range(count), key=lambda idx: (float(values[idx]), tokens[idx]))
    roles = np.empty(count, dtype=np.float32)
    roles[np.asarray(order, dtype=np.intp)] = np.linspace(-1.0, 1.0, count, dtype=np.float32)
    return roles


def _paint_aware_spatial_shares(
    source_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    material_stats: list[tuple[float, float, float, float]],
    tokens: list[str],
    priors: np.ndarray,
    output_shape: tuple[int, int],
) -> np.ndarray:
    """Return ``NxHxW`` smooth shares whose masked means match user priors.

    Work is bounded to 512 px on the long side.  Material *identity* comes from
    the actual authored M/R/Cc layer statistics: shinier layers naturally favor
    brighter/saturated paint, while highly textured layers favor quieter paint
    regions so logos and existing livery detail do not become muddy.  A small,
    stable finish-id vector breaks ties without randomness.  Iterative vectorized
    calibration keeps each slider value the global coverage prior even though the
    material varies locally.
    """
    out_h, out_w = int(output_shape[0]), int(output_shape[1])
    ratio = min(1.0, 512.0 / float(max(out_h, out_w)))
    ah = max(32, int(round(out_h * ratio)))
    aw = max(32, int(round(out_w * ratio)))

    source = np.asarray(source_rgb_hwc[:, :, :3], dtype=np.float32)
    source = np.nan_to_num(source, nan=0.0, posinf=255.0, neginf=0.0)
    if float(np.max(source)) > 1.5:
        source = source / 255.0
    source = np.clip(source, 0.0, 1.0)
    if source.shape[:2] != (ah, aw):
        interpolation = cv2.INTER_AREA if max(source.shape[:2]) > max(ah, aw) else cv2.INTER_LINEAR
        source = cv2.resize(source, (aw, ah), interpolation=interpolation)

    coverage = np.clip(np.asarray(mask_hw, dtype=np.float32), 0.0, 1.0)
    if coverage.shape != (ah, aw):
        coverage = cv2.resize(coverage, (aw, ah), interpolation=cv2.INTER_AREA)
    if float(np.sum(coverage)) < 1.0e-4:
        coverage = np.ones((ah, aw), dtype=np.float32)

    red, green, blue = source[..., 0], source[..., 1], source[..., 2]
    luminance = red * 0.299 + green * 0.587 + blue * 0.114
    maximum = np.maximum(np.maximum(red, green), blue)
    minimum = np.minimum(np.minimum(red, green), blue)
    saturation = np.where(maximum > 1.0e-6, (maximum - minimum) / (maximum + 1.0e-6), 0.0)
    soft_luminance = cv2.GaussianBlur(luminance, (0, 0), 1.35)
    detail = cv2.GaussianBlur(np.abs(luminance - soft_luminance), (0, 0), 0.85)

    lum_cue = _robust_unit_field(soft_luminance, coverage) - 0.5
    sat_cue = _robust_unit_field(cv2.GaussianBlur(saturation, (0, 0), 1.10), coverage) - 0.5
    detail_cue = _robust_unit_field(detail, coverage) - 0.5

    stats = np.asarray(material_stats, dtype=np.float32)
    flash = (
        stats[:, 0] * (0.40 / 255.0)
        + (255.0 - stats[:, 1]) * (0.30 / 255.0)
        + stats[:, 2] * (0.30 / 255.0)
    )
    texture = stats[:, 3]
    flash_role = _rank_roles(flash, tokens)
    texture_role = _rank_roles(texture, tokens)

    token_vectors = np.empty((len(tokens), 3), dtype=np.float32)
    for idx, finish_token in enumerate(tokens):
        digest = hashlib.blake2s(finish_token.encode("utf-8"), digest_size=3).digest()
        token_vectors[idx] = np.frombuffer(digest, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0
    token_vectors -= np.mean(token_vectors, axis=0, keepdims=True)

    affinities = np.empty((len(tokens), ah, aw), dtype=np.float32)
    bright_material_cue = lum_cue * 0.72 + sat_cue * 0.28
    for idx in range(len(tokens)):
        # [Easy Whole Car owner request 2026-07-22: "tries to figure out how
        # to apply the finishes correctly"] Real authored material statistics
        # choose paint roles; no finish recipe changes, therefore M7 is N/A.
        logit = (
            flash_role[idx] * bright_material_cue * 1.55
            - texture_role[idx] * detail_cue * 0.72
            + (
                token_vectors[idx, 0] * lum_cue
                + token_vectors[idx, 1] * sat_cue
                + token_vectors[idx, 2] * detail_cue
            )
            * 0.28
        )
        np.exp(np.clip(logit, -1.6, 1.6), out=affinities[idx])
        # Keep material handoffs soft at paint boundaries. At the 512 analysis
        # cap this is roughly a 9 px transition on a 2048 template: visible as
        # intentional material zoning, never a jagged one-pixel cutout.
        routing_sigma = max(1.25, float(max(ah, aw)) / 220.0)
        affinities[idx] = cv2.GaussianBlur(affinities[idx], (0, 0), routing_sigma)

    target = np.clip(np.asarray(priors, dtype=np.float64), 1.0e-8, None)
    target /= float(np.sum(target))
    scales = target.copy()
    coverage64 = coverage.astype(np.float64, copy=False)
    coverage_sum = max(float(np.sum(coverage64)), 1.0e-8)
    # Four materials x 14 vectorized passes over at most 512² is far cheaper
    # than one additional authored finish bake and contains no Python pixel loop.
    for _iteration in range(14):
        denominator = np.zeros((ah, aw), dtype=np.float64)
        for idx in range(len(tokens)):
            denominator += affinities[idx] * scales[idx]
        denominator = np.maximum(denominator, 1.0e-12)
        actual = np.asarray(
            [
                float(np.sum(coverage64 * affinities[idx] * scales[idx] / denominator)) / coverage_sum
                for idx in range(len(tokens))
            ],
            dtype=np.float64,
        )
        if float(np.max(np.abs(actual - target))) < 2.5e-5:
            break
        scales *= target / np.maximum(actual, 1.0e-9)
        scales /= float(np.sum(scales))

    denominator = np.zeros((ah, aw), dtype=np.float32)
    for idx in range(len(tokens)):
        denominator += affinities[idx] * np.float32(scales[idx])
    denominator = np.maximum(denominator, np.float32(1.0e-12))
    shares = affinities * scales.astype(np.float32).reshape(-1, 1, 1)
    shares /= denominator[None, :, :]
    return shares.astype(np.float32, copy=False)


def _material_stat_tuple(
    metallic: np.ndarray,
    roughness: np.ndarray,
    clearcoat: np.ndarray,
) -> tuple[float, float, float, float]:
    """(mean M, mean R, mean Cc, mean channel std) for one authored material.

    Extracted 2026-08-08 so the Easy Mode "where does each material land" map
    computes material identity from the SAME numbers the render routes on. If
    these two ever diverge the map becomes a confident lie, which is worse than
    not showing one.
    """
    return (
        float(np.mean(metallic)),
        float(np.mean(roughness)),
        float(np.mean(clearcoat)),
        float((np.std(metallic) + np.std(roughness) + np.std(clearcoat)) / 3.0),
    )


def _resolved_material_channels(
    finish_token: str,
    render_shape: tuple[int, int],
    render_mask: np.ndarray,
    seed_i: int,
    sm_f: float,
    mono_registry: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resolve one catalog token to sanitized M/R/Cc planes (shared seam)."""
    from engine.compose import _resolve_finish_spec

    registry_type, finish_id = _split_catalog_token(finish_token)
    metallic, roughness, clearcoat = _resolve_finish_spec(
        finish_id,
        render_shape,
        render_mask,
        seed_i,
        sm_f,
        monolithic_registry=mono_registry,
        registry_type=registry_type,
    )
    safe_channels = []
    for channel, neutral in zip((metallic, roughness, clearcoat), (0.0, 160.0, 255.0)):
        arr = np.asarray(channel, dtype=np.float32)
        arr = np.nan_to_num(arr, nan=neutral, posinf=255.0, neginf=0.0)
        np.clip(arr, 0.0, 255.0, out=arr)
        safe_channels.append(arr)
    return safe_channels[0], safe_channels[1], safe_channels[2]


def paint_aware_share_maps(
    source_rgb_hwc: np.ndarray,
    stack: list[tuple[str, float]],
    *,
    shape_hw: tuple[int, int],
    seed: int = 0,
    sm: float = 0.5,
    analysis_px: int = 256,
) -> np.ndarray:
    """NxHxW routing shares for a stack — the map behind "Shokker maps the rest".

    This is the SAME routing the render uses (`_paint_aware_spatial_shares`, fed
    by the same `_resolved_material_channels` + `_material_stat_tuple`), just
    resolved at a small analysis size because it is being drawn as a guide, not
    baked into a car. Two or more materials only; one material covers
    everything and needs no map.
    """
    if len(stack) < 2:
        raise ValueError("a material map needs at least two materials")
    mono_registry = _full_monolithic_registry()
    h, w = int(shape_hw[0]), int(shape_hw[1])
    ah = max(32, min(int(analysis_px), h))
    aw = max(32, min(int(analysis_px), w))
    render_mask = np.ones((ah, aw), dtype=np.float32)
    material_stats: list[tuple[float, float, float, float]] = []
    tokens: list[str] = []
    priors: list[float] = []
    for finish_token, weight in stack:
        metallic, roughness, clearcoat = _resolved_material_channels(
            finish_token, (ah, aw), render_mask, int(seed) & 0xFFFFFFFF,
            float(np.clip(sm, 0.0, 1.0)), mono_registry,
        )
        material_stats.append(_material_stat_tuple(metallic, roughness, clearcoat))
        tokens.append(finish_token)
        priors.append(float(weight))
    return _paint_aware_spatial_shares(
        source_rgb_hwc,
        np.ones((h, w), dtype=np.float32),
        material_stats,
        tokens,
        np.asarray(priors, dtype=np.float64),
        (h, w),
    )


def _blend_registered_specs_paint_aware_float(
    shape_hw: tuple[int, int],
    mask_hw: np.ndarray,
    *,
    source_rgb_hwc: np.ndarray,
    seed: int,
    sm: float,
    stack: list[tuple[str, float]],
    tile: float,
    render_cap_px: int | None,
) -> np.ndarray:
    """Blend 2–4 authored spec layers with livery-aware local coverage."""
    from engine.compose import _resolve_finish_spec

    mono_registry = _full_monolithic_registry()
    h, w = int(shape_hw[0]), int(shape_hw[1])
    mask = np.clip(np.asarray(mask_hw, dtype=np.float32), 0.0, 1.0)
    sm_f = float(np.clip(sm, 0.0, 1.0))
    seed_i = int(seed) & 0xFFFFFFFF
    tile_f = max(1.0, float(tile))
    if tile_f > 1.0:
        render_h = max(8, int(round(h / tile_f)))
        render_w = max(8, int(round(w / tile_f)))
        render_mask = np.ones((render_h, render_w), dtype=np.float32)
    else:
        render_h, render_w = h, w
        render_mask = mask

    cap = int(render_cap_px or 0)
    if cap >= 64 and max(render_h, render_w) > cap:
        cap_ratio = float(cap) / float(max(render_h, render_w))
        generated_h = max(64, int(round(render_h * cap_ratio)))
        generated_w = max(64, int(round(render_w * cap_ratio)))
        render_mask = cv2.resize(render_mask, (generated_w, generated_h), interpolation=cv2.INTER_AREA)
    else:
        generated_h, generated_w = render_h, render_w
    render_shape = (generated_h, generated_w)

    layers: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    material_stats: list[tuple[float, float, float, float]] = []
    tokens: list[str] = []
    priors: list[float] = []
    for finish_token, weight in stack:
        metallic, roughness, clearcoat = _resolved_material_channels(
            finish_token, render_shape, render_mask, seed_i, sm_f, mono_registry,
        )
        material_stats.append(_material_stat_tuple(metallic, roughness, clearcoat))
        # The common guided path is capped at 512. For an uncapped 2048
        # advanced call, float16 storage avoids retaining ~200 MB while mixing;
        # expansion converts one layer at a time back to float32.
        storage_dtype = np.float16 if max(render_shape) > 1024 else np.float32
        layers.append(
            tuple(np.asarray(channel, dtype=storage_dtype) for channel in (metallic, roughness, clearcoat))
        )
        tokens.append(finish_token)
        priors.append(float(weight))

    shares = _paint_aware_spatial_shares(
        source_rgb_hwc,
        mask,
        material_stats,
        tokens,
        np.asarray(priors, dtype=np.float64),
        (h, w),
    )
    output = np.zeros((h, w, 4), dtype=np.float32)

    def expand_channel(channel: np.ndarray) -> np.ndarray:
        expanded = np.asarray(channel, dtype=np.float32)
        if tile_f > 1.0:
            if expanded.shape != (render_h, render_w):
                expanded = cv2.resize(expanded, (render_w, render_h), interpolation=cv2.INTER_LINEAR)
            return _mirror_tile_to(expanded, h, w)
        if expanded.shape != (h, w):
            expanded = cv2.resize(expanded, (w, h), interpolation=cv2.INTER_LINEAR)
        return expanded

    for idx, (metallic, roughness, clearcoat) in enumerate(layers):
        local_share = shares[idx]
        if local_share.shape != (h, w):
            local_share = cv2.resize(local_share, (w, h), interpolation=cv2.INTER_LINEAR)
        output[..., 0] += expand_channel(metallic) * local_share
        output[..., 1] += expand_channel(roughness) * local_share
        output[..., 2] += expand_channel(clearcoat) * local_share

    output[..., 3] = 255.0
    np.nan_to_num(output, copy=False, nan=0.0, posinf=255.0, neginf=0.0)
    np.clip(output, 0.0, 255.0, out=output)
    return output


def blend_registered_specs_float(
    shape_hw: tuple[int, int],
    mask_hw: np.ndarray,
    *,
    seed: int,
    sm: float,
    stack: list[tuple[str, float]],
    tile: float = 1.0,
    render_cap_px: int | None = None,
) -> np.ndarray:
    """Weighted blend of registry specs → ``HxWx4`` float32 (R=M, G=R, B=Cc, A=255).

    Same resolution contract as ``_scratch_spec_from_paint`` output before uint8 cast.

    ``tile`` > 1 makes the finish PATTERN finer for a car-sized canvas: each finish is
    rendered at ``(h/tile, w/tile)`` and reflect-tiled back up to ``(h, w)``, so its
    cells repeat ``tile`` times across the frame instead of being stretched whole-frame.
    ``tile=1`` keeps the original whole-frame scale. Reflect tiling stays seamless even
    for gradient / radial finishes (adjacent tiles mirror at the shared edge).

    Default behavior is the original uniform weighted average.  A caller must
    explicitly enter :func:`paint_aware_spatial_mix` to route two or more
    materials across source-paint brightness, saturation, and detail.
    """
    paint_source = _PAINT_AWARE_SOURCE.get()
    if paint_source is not None and len(stack) > 1:
        return _blend_registered_specs_paint_aware_float(
            shape_hw,
            mask_hw,
            source_rgb_hwc=paint_source,
            seed=seed,
            sm=sm,
            stack=stack,
            tile=tile,
            render_cap_px=render_cap_px,
        )

    from engine.compose import _resolve_finish_spec
    _mono_reg = _full_monolithic_registry()  # incl. FRACTURED; engine.registry wins on shared keys

    h, w = int(shape_hw[0]), int(shape_hw[1])
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    acc = np.zeros((h, w, 4), dtype=np.float32)
    sm_f = float(np.clip(sm, 0.0, 1.0))
    seed_i = int(seed) & 0xFFFFFFFF

    t = max(1.0, float(tile))
    if t > 1.0:
        # Spec Sculpt always renders full-frame (mask all ones); render each finish small
        # then reflect-tile. rh/rw are the per-tile render size.
        rh = max(8, int(round(h / t)))
        rw = max(8, int(round(w / t)))
        rmask = np.ones((rh, rw), dtype=np.float32)
    else:
        rh, rw = h, w
        rmask = m

    # SPB-BETA-2026-07-20: guided renders may cap the expensive authored
    # finish bake, then resize that material field before seamless tiling. This
    # preserves the user's material-scale contract while turning a pair of
    # 2048² procedural bakes into a pair of 512² bakes. At 4× expansion their
    # 2-8 px primitives land at the owner's required 8-32 px on-car range.
    cap = int(render_cap_px or 0)
    if cap >= 64 and max(rh, rw) > cap:
        ratio = float(cap) / float(max(rh, rw))
        gh = max(64, int(round(rh * ratio)))
        gw = max(64, int(round(rw * ratio)))
        rmask = cv2.resize(rmask, (gw, gh), interpolation=cv2.INTER_AREA)
    else:
        gh, gw = rh, rw
    rshape = (gh, gw)

    for finish_token, wt in stack:
        registry_type, fid = _split_catalog_token(finish_token)
        M_arr, R_arr, CC_arr = _resolve_finish_spec(
            fid, rshape, rmask, seed_i, sm_f,
            monolithic_registry=_mono_reg,
            registry_type=registry_type,
        )
        M_arr = np.asarray(M_arr, dtype=np.float32)
        R_arr = np.asarray(R_arr, dtype=np.float32)
        CC_arr = np.asarray(CC_arr, dtype=np.float32)
        if t > 1.0:
            if M_arr.shape != (rh, rw):
                M_arr = cv2.resize(M_arr, (rw, rh), interpolation=cv2.INTER_LINEAR)
            if R_arr.shape != (rh, rw):
                R_arr = cv2.resize(R_arr, (rw, rh), interpolation=cv2.INTER_LINEAR)
            if CC_arr.shape != (rh, rw):
                CC_arr = cv2.resize(CC_arr, (rw, rh), interpolation=cv2.INTER_LINEAR)
            M_arr = _mirror_tile_to(M_arr, h, w)
            R_arr = _mirror_tile_to(R_arr, h, w)
            CC_arr = _mirror_tile_to(CC_arr, h, w)
        else:
            if M_arr.shape != (h, w):
                M_arr = cv2.resize(M_arr, (w, h), interpolation=cv2.INTER_LINEAR)
            if R_arr.shape != (h, w):
                R_arr = cv2.resize(R_arr, (w, h), interpolation=cv2.INTER_LINEAR)
            if CC_arr.shape != (h, w):
                CC_arr = cv2.resize(CC_arr, (w, h), interpolation=cv2.INTER_LINEAR)
        wf = float(wt)
        acc[:, :, 0] += M_arr * wf
        acc[:, :, 1] += R_arr * wf
        acc[:, :, 2] += CC_arr * wf

    acc[:, :, 3] = 255.0
    np.clip(acc, 0.0, 255.0, out=acc)
    return acc
