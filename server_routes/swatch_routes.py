"""Swatch thumbnail routes for Shokker Paint Booth."""

from __future__ import annotations

import inspect
import io
import os
import time
import traceback

from flask import Response, jsonify, request, send_file
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

# Cached directory index for the per-color warm cache so the hash-drift-tolerant
# fallback (step 2 of the split path) does not os.listdir() on every request when
# a whole picker grid of thumbnails loads at once. Keyed by dir; short TTL so
# freshly-written warm files become visible quickly. {dir: (mono_time, name_set)}
_WARM_DIR_INDEX: dict = {}
_WARM_DIR_INDEX_TTL = 5.0


def _warm_dir_names(split_cache_dir):
    """Set of *.png filenames in the warm-cache dir, cached for a few seconds."""
    now = time.monotonic()
    cached = _WARM_DIR_INDEX.get(split_cache_dir)
    if cached is not None and (now - cached[0]) < _WARM_DIR_INDEX_TTL:
        return cached[1]
    try:
        names = {nm for nm in os.listdir(split_cache_dir) if nm.endswith('.png')}
    except Exception:
        names = set()
    _WARM_DIR_INDEX[split_cache_dir] = (now, names)
    return names


def register_swatch_routes(
    app,
    *,
    engine_getter,
    thumbnail_dir_getter,
    swatch_folder_getter,
    swatch_cache,
    swatch_cache_lock,
    swatch_cache_token,
    render_swatch_bytes,
    render_fast_split_swatch_bytes,
    render_picker_split_snapshot_bytes,
    picker_split_static_path,
    read_picker_split_png_bytes,
    truthy_env,
    normalize_spec_result_to_rgba,
    invoke_monolithic_spec_fn,
    logger,
    picker_finish_renderer_hash=None,
    external_write_guard=None,
    quality_write_guard=None,
) -> None:
    """Register live, picker, and legacy swatch preview endpoints."""

    def _disk_write_allowed(path, operation):
        return (
            external_write_guard is None
            or not external_write_guard(path, operation)
        )

    def _serve_generated_png(image, cache_file):
        if _disk_write_allowed(cache_file, "legacy-swatch-cache-write"):
            image.save(cache_file, 'PNG')
            return send_file(cache_file, mimetype='image/png')
        buffer = io.BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)
        return send_file(buffer, mimetype='image/png')

    def _cache_headers():
        # [2026-06-12 thumbnail-cache fix] 1 year, not 24h: swatch URLs carry
        # the engine-fingerprint ?v= token, so they're genuinely immutable —
        # when a finish changes, the token changes and the URL is new. The
        # browser should keep these forever ("load once, stored forever").
        return {'Cache-Control': 'public, max-age=31536000, immutable'}

    @app.route('/api/swatch-version', methods=['GET'])
    def api_swatch_version():
        """Engine-fingerprint token for browser-side swatch cache busting.

        2026-06-11 owner bug: thumbnails stayed STALE after server restart +
        hard reload — the JS swatch URLs used a localStorage token that never
        changed ('stable-v1') while responses are immutable/max-age=86400, so
        the BROWSER kept serving old PNGs without ever hitting the server. The
        UI now syncs its token to this fingerprint at boot: engine code changed
        -> new token -> every swatch URL changes -> fresh fetch; nothing
        changed -> same URLs -> instant browser cache."""
        try:
            tok = swatch_cache_token() if callable(swatch_cache_token) else str(swatch_cache_token)
        except Exception:
            tok = 'fallback'
        return jsonify({'v': str(tok)})

    _FINGERPRINT_CACHE = {'ts': 0.0, 'data': None, 'v': None}
    _FINGERPRINT_TTL = 30.0

    @app.route('/api/swatch-fingerprints', methods=['GET'])
    def api_swatch_fingerprints():
        """Per-finish content fingerprints for SMART, per-thumbnail cache busting.

        [2026-06-17 smart-cache] The global /api/swatch-version token busts EVERY
        swatch URL whenever ANY engine file changes — correct but coarse. This map
        gives the UI a PER-FINISH token (the same renderer hash the server bakes
        into the warm-cache filename), so getSwatchUrl() can build a URL that
        changes ONLY for the finishes whose render actually changed. Unchanged
        finishes keep their exact URL -> instant browser cache hit; a changed
        finish (e.g. a re-tuned FRACTURED MINDS id) gets a new URL -> fresh fetch.

        Returns {"v": <global token>, "fp": {"<type>:<id>": "<hash>", ...}}.
        The global token is included so the UI can fall back to it for any id the
        map omits (dynamic catalog-only ids absent from the engine registries)."""
        now = time.time()
        try:
            gtok = swatch_cache_token() if callable(swatch_cache_token) else str(swatch_cache_token)
        except Exception:
            gtok = 'fallback'
        cached = _FINGERPRINT_CACHE
        if (cached['data'] is not None and cached['v'] == gtok
                and (now - cached['ts']) < _FINGERPRINT_TTL):
            return jsonify({'v': str(gtok), 'fp': cached['data']})
        fp = {}
        if callable(picker_finish_renderer_hash):
            eng = engine_getter()
            regs = (
                ('base', getattr(eng, 'BASE_REGISTRY', {})),
                ('pattern', getattr(eng, 'PATTERN_REGISTRY', {})),
                ('monolithic', getattr(eng, 'MONOLITHIC_REGISTRY', {})),
            )
            for ftype, reg in regs:
                for fid in list(reg.keys()):
                    try:
                        h = picker_finish_renderer_hash(ftype, fid)
                    except Exception:
                        h = None
                    if h:
                        fp[f'{ftype}:{fid}'] = h
        _FINGERPRINT_CACHE.update({'ts': now, 'data': fp, 'v': gtok})
        return jsonify({'v': str(gtok), 'fp': fp})

    def _safe_swatch_key(*parts):
        return "_".join(str(part or "") for part in parts).replace('/', '_').replace('\\', '_').replace(':', '_')

    @app.route('/api/swatch/<finish_type>/<finish_key>', methods=['GET'])
    def api_swatch(finish_type, finish_key):
        """Return an engine-accurate swatch thumbnail as a PNG image."""
        engine = engine_getter()
        color_hex = request.args.get('color', '888888').lstrip('#').ljust(6, '0')[:6]
        try:
            size = max(32, min(512, int(request.args.get('size', 64))))   # 512: click-to-enlarge preview
        except (TypeError, ValueError):
            size = 64
        try:
            seed = int(request.args.get('seed', 42))
        except (TypeError, ValueError):
            seed = 42
        nocache = request.args.get('nocache') == '1'
        mode = request.args.get('mode', '')
        cache_token = swatch_cache_token()

        cache_key = f"{cache_token}:{finish_type}:{finish_key}:{color_hex}:{size}:{mode}"
        prefer = (request.args.get('prefer') or '').lower()
        prefer_live = prefer != 'static' and prefer != 'prerender'
        allow_prerender = not prefer_live

        if finish_key and str(finish_key).startswith('ui_'):
            try:
                from engine.paint_v2.user_imports_paths import user_imports_root
                from engine.paint_v2.user_imports_spec_dna import make_preview_combined
                from PIL import Image as PILImage

                root = user_imports_root()
                prev = root / f"{finish_key}_preview.png"
                if not prev.exists():
                    paint_p = root / f"{finish_key}.png"
                    spec_p = root / f"{finish_key}_spec.png"
                    if paint_p.exists() and spec_p.exists():
                        combo = make_preview_combined(PILImage.open(paint_p), PILImage.open(spec_p), width=max(128, size * 2))
                        combo.save(prev, "PNG", optimize=True)
                if prev.exists():
                    img = PILImage.open(prev).convert("RGB")
                    img = img.resize((size, size // 2 if img.width > img.height else size), PILImage.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    buf.seek(0)
                    return Response(buf.getvalue(), mimetype="image/png", headers=_cache_headers())
            except Exception as ex:
                logger.debug(f"[swatch] ui_ preview fallback: {ex}")

        def _validate_swatch_request():
            mono_reg = getattr(engine, 'MONOLITHIC_REGISTRY', {})
            base_reg = getattr(engine, 'BASE_REGISTRY', {})
            pattern_reg = getattr(engine, 'PATTERN_REGISTRY', {})
            dynamic_mono_prefixes = ('grad_', 'grad3_', 'gradm_', 'ghostg_', 'clr_', 'cs_duo_', 'mc_')
            is_dynamic_mono = bool(finish_key and any(finish_key.startswith(p) for p in dynamic_mono_prefixes))
            has_dynamic_colors = False
            if is_dynamic_mono:
                try:
                    from finish_colors_lookup import get_finish_colors
                    has_dynamic_colors = bool(get_finish_colors(finish_key))
                except Exception:
                    has_dynamic_colors = False
            if finish_type not in ('base', 'pattern', 'monolithic'):
                raise ValueError(f"Unknown swatch type: {finish_type}")
            if finish_type == 'base' and finish_key not in base_reg and finish_key not in mono_reg:
                raise ValueError(f"Unknown swatch base: {finish_key}")
            if finish_type == 'pattern' and finish_key not in pattern_reg:
                raise ValueError(f"Unknown swatch pattern: {finish_key}")
            if finish_type == 'monolithic' and finish_key not in mono_reg and not has_dynamic_colors:
                raise ValueError(f"Unknown swatch monolithic: {finish_key}")

        if finish_key and str(finish_key).startswith('pf_'):
            base_reg = getattr(engine, 'BASE_REGISTRY', {})
            if finish_key in base_reg:
                finish_type = 'base'

        try:
            _validate_swatch_request()
        except Exception as e:
            logger.warning(f"/api/swatch rejected [{finish_type}/{finish_key}]: {e}")
            status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown swatch") else 500
            return jsonify({
                "error": "swatch_render_failed",
                "type": finish_type,
                "key": finish_key,
                "message": str(e),
            }), status_code

        cache_headers = _cache_headers()
        swatch_cache_dir = os.path.join(thumbnail_dir_getter(), 'swatch_cache')
        disk_path = os.path.join(
            swatch_cache_dir,
            _safe_swatch_key(cache_token, finish_type, finish_key, color_hex, size, mode) + '.png',
        )

        if mode == 'split' and finish_type in ('pattern', 'monolithic', 'base'):
            if request.args.get('source') == 'faithful-v1':
                from server_routes.faithful_swatch import faithful_split_bytes
                try:
                    baked_only = request.args.get('baked') == '1'
                    # Read-only category hits do not need a publication/quality
                    # decision (or thousands of repeated manifest reads).
                    publish = not nocache and not baked_only and _disk_write_allowed(swatch_cache_dir, 'swatch-cache-write')
                    if publish and callable(quality_write_guard):
                        try:
                            quality_write_guard([(finish_type, finish_key)])
                        except Exception:
                            publish = False
                    renderer_hash = picker_finish_renderer_hash(finish_type, finish_key) if picker_finish_renderer_hash else ''
                    png = faithful_split_bytes(
                        cache_dir=swatch_cache_dir,
                        # A change elsewhere in the engine must not invalidate
                        # this finish. Retain the global fallback only for ids
                        # without a renderer fingerprint. Migrate existing bakes.
                        identity=[renderer_hash or cache_token, finish_type, finish_key, color_hex, seed],
                        legacy_identity=[cache_token, renderer_hash, finish_type, finish_key, color_hex, seed],
                        size=size, cache_allowed=publish, read_allowed=not nocache,
                        allow_render=not baked_only,
                        render=lambda master_size: render_picker_split_snapshot_bytes(
                            finish_type, finish_key, color_hex, master_size, seed),
                    )
                    return Response(png, mimetype='image/png', headers={
                        **cache_headers, 'X-SPB-Swatch-Source': 'faithful-disk' if request.args.get('baked') == '1' else 'faithful',
                    })
                except Exception as exc:
                    logger.warning('Faithful swatch failed [%s/%s]: %s', finish_type, finish_key, exc)
                    return jsonify(error='real_swatch_render_failed', message=str(exc)), 503, {'Cache-Control': 'no-store'}
            static_path = picker_split_static_path(finish_type, finish_key)

            # [2026-06-13 thumbnail-cache fix — 5th/infrastructural cause]
            # The picker grid ALWAYS requests prefer=live, which used to (a) skip
            # the shipped color-agnostic static snapshot entirely and (b) fall
            # through to a live re-render whenever the per-color/hash warm-cache
            # file was missing. Two real defects made warm-cache misses the norm,
            # not the exception, so EVERY restart re-rendered most thumbnails
            # ("pop in like Windows 3.1"):
            #   1. Renderer-hash DRIFT: rebuilt patterns/monolithics share a
            #      wrapper-closure source, so any edit to the wrapper factory
            #      bumps the hash for hundreds of finishes at once. The warm
            #      files baked under the old hash never match the new key.
            #   2. NEVER-WARMED dynamic finishes: grad_*/spectrum_*/etc. are
            #      JS-catalog-only ids absent from the engine registries, so the
            #      boot warm's validity gate skips them — no warm file ever.
            # Fix: serve from disk first (exact warm file -> any warm file for
            # this id+color -> shipped static snapshot), and only render live as
            # a true last resort. The static snapshot is keyed by {type}/{key}
            # (no hash, no color), so it is immune to hash drift AND collisions
            # and survives every restart. When we do render live we also persist
            # a static snapshot so the next launch is instant even if the hash
            # drifts again.
            def _serve_static_snapshot():
                if not os.path.isfile(static_path):
                    return None
                try:
                    return Response(
                        read_picker_split_png_bytes(static_path, size),
                        mimetype='image/png', headers=cache_headers,
                    )
                except Exception as static_err:
                    logger.debug(f"Picker split static read failed [{finish_type}/{finish_key}]: {static_err}")
                    return None

            # When the caller explicitly asked for the prerendered/static form,
            # honor it up front (unchanged behavior for prefer=static).
            if allow_prerender and not nocache:
                resp = _serve_static_snapshot()
                if resp is not None:
                    return resp

            # Per-finish disk cache keyed on the renderer hash so the cache
            # invalidates automatically whenever the finish definition changes.
            # The fast/fake painter is only used as a last-resort fallback if
            # the real path raises.
            split_cache_dir = os.path.join(thumbnail_dir_getter(), 'swatch_cache', 'picker_split')
            split_hash = ''
            if picker_finish_renderer_hash is not None:
                try:
                    split_hash = picker_finish_renderer_hash(finish_type, finish_key) or ''
                except Exception as he:
                    logger.debug(f"Picker split hash failed [{finish_type}/{finish_key}]: {he}")
                    split_hash = ''
            split_disk_path = os.path.join(
                split_cache_dir,
                _safe_swatch_key(finish_type, finish_key, color_hex, size, split_hash) + '.png',
            ) if split_hash else None

            # 1) Exact warm-cache hit (color + size + CURRENT renderer hash).
            #    Content-correct by construction: the filename carries split_hash,
            #    so this only matches when the finish's renderer is unchanged.
            if (not nocache) and split_disk_path and os.path.isfile(split_disk_path):
                try:
                    with open(split_disk_path, 'rb') as df:
                        return Response(df.read(), mimetype='image/png', headers=cache_headers)
                except Exception as cache_err:
                    logger.debug(f"Picker split disk-cache read failed [{finish_type}/{finish_key}]: {cache_err}")

            # 2) Shipped per-finish static snapshot. This is the SMART, content-
            #    aware fast path: rebuild_picker_swatches.py re-bakes this PNG
            #    whenever picker_split_needs_rebuild() detects a renderer-hash or
            #    catalog-color change, so it always reflects the CURRENT render.
            #    [2026-06-17 stale-thumbnail fix] It is now preferred over the
            #    hash-IGNORING warm scan below. The old order served any warm file
            #    for this id+color regardless of hash, which meant a finish whose
            #    RENDER actually changed (e.g. the crushed FRACTURED MINDS/SOULS
            #    re-bake) kept serving its pre-change warm PNG forever. Serving the
            #    hash-validated static snapshot first guarantees changed finishes
            #    show their new render while unchanged finishes still hit an
            #    instant file-serve (no live render).
            if not nocache:
                resp = _serve_static_snapshot()
                if resp is not None:
                    return resp

            # 3) Hash-drift-tolerant warm hit: a baked file for this exact
            #    id+color+size whose embedded hash MATCHES the current renderer
            #    hash, else (only when we cannot compute a current hash) any such
            #    file as a last resort before a live render. We deliberately skip
            #    warm files whose hash differs from the current one so a genuine
            #    render change is never masked by a stale warm PNG, and we delete
            #    those stale files opportunistically so the dir does not grow
            #    unbounded across engine edits. Reached only for finishes with no
            #    static snapshot (dynamic/never-baked ids), so the common case is
            #    already handled above.
            if not nocache:
                try:
                    prefix = _safe_swatch_key(finish_type, finish_key, color_hex, size) + '_'
                    cur_hash_suffix = ('_' + split_hash + '.png') if split_hash else None
                    drift_match = None
                    for nm in _warm_dir_names(split_cache_dir):
                        if not nm.startswith(prefix):
                            continue
                        if cur_hash_suffix is not None:
                            # Content-aware: only serve a warm file that matches
                            # the CURRENT renderer hash. (The exact-name lookup in
                            # step 1 already covers split_disk_path, but a scan is
                            # still cheap insurance against safe-key drift.)
                            if nm.endswith(cur_hash_suffix):
                                with open(os.path.join(split_cache_dir, nm), 'rb') as df:
                                    return Response(df.read(), mimetype='image/png', headers=cache_headers)
                            else:
                                # Stale-hash warm file for a finish that changed —
                                # never serve it; prune it so it stops shadowing.
                                try:
                                    stale_path = os.path.join(split_cache_dir, nm)
                                    if _disk_write_allowed(stale_path, "swatch-cache-prune"):
                                        os.remove(stale_path)
                                except Exception as _spb_ex:
                                    _spb_swallow('api_swatch@L359', _spb_ex)
                        else:
                            # No current hash available (cannot judge freshness):
                            # remember one as a last-resort fallback only.
                            drift_match = drift_match or nm
                    if drift_match is not None:
                        with open(os.path.join(split_cache_dir, drift_match), 'rb') as df:
                            return Response(df.read(), mimetype='image/png', headers=cache_headers)
                except Exception as scan_err:
                    logger.debug(f"Picker split warm-scan failed [{finish_type}/{finish_key}]: {scan_err}")

            # 4) Last resort: render live (cold finish never seen on this box).
            png_bytes = None
            try_real = bool(prefer_live)
            real_failed = False
            cache_publish_allowed = True
            if try_real:
                try:
                    # A picker request is a read operation: it must be able to
                    # render the actual current material even while the owner
                    # review manifest deliberately blocks *publishing* Wilds
                    # thumbnail files.  Previously this write gate ran before
                    # the render, so every 512px click-to-enlarge request became
                    # a 503 "Preview Unavailable" despite a healthy renderer.
                    # Keep the gate intact below by withholding warm/static
                    # cache writes when it rejects the unreviewed card.
                    if callable(quality_write_guard):
                        try:
                            quality_write_guard([(finish_type, finish_key)])
                        except Exception as quality_err:
                            cache_publish_allowed = False
                            logger.info(
                                f"/api/swatch live preview is ephemeral "
                                f"[{finish_type}/{finish_key}]: {quality_err}"
                            )
                    png_bytes = render_picker_split_snapshot_bytes(finish_type, finish_key, color_hex, size, seed)
                except Exception as e:
                    real_failed = True
                    # Owner 2026-07-21: visual material choices must be the real
                    # Paint Booth thumbnails, never plausible-looking invented
                    # pixels. A prefer=live request therefore fails honestly and
                    # lets the picker show PREVIEW UNAVAILABLE; the fast painter
                    # remains only for callers that did not request real output.
                    logger.warning(f"/api/swatch split live-engine failed [{finish_type}/{finish_key}]: {e}")
                    return jsonify({
                        "error": "real_swatch_render_failed",
                        "type": finish_type,
                        "key": finish_key,
                        "message": str(e),
                    }), 503
            if png_bytes is None:
                try:
                    png_bytes = render_fast_split_swatch_bytes(finish_type, finish_key, color_hex, size, seed)
                except Exception as e:
                    logger.warning(f"/api/swatch split failed [{finish_type}/{finish_key}]: {e}")
                    status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown swatch") else 500
                    return jsonify({
                        "error": "swatch_render_failed",
                        "type": finish_type,
                        "key": finish_key,
                        "message": str(e),
                    }), status_code

            # Persist real-engine output to disk so subsequent picker loads are
            # instant. We deliberately skip caching the fake-painter fallback
            # (real_failed=True) so a transient engine error doesn't poison the
            # cache with synthetic pixels.
            if (not nocache) and (not real_failed) and try_real and cache_publish_allowed:
                if split_disk_path:
                    try:
                        if _disk_write_allowed(split_disk_path, "swatch-cache-write"):
                            os.makedirs(os.path.dirname(split_disk_path), exist_ok=True)
                            with open(split_disk_path, 'wb') as df:
                                df.write(png_bytes)
                    except Exception as cache_err:
                        logger.debug(f"Picker split disk-cache write failed [{finish_type}/{finish_key}]: {cache_err}")
                # Also persist a color-agnostic static snapshot keyed only by
                # {type}/{key}. This is the hash-drift-proof fallback that keeps
                # the next launch instant even after a renderer-hash bump, and it
                # populates static snapshots for dynamic finishes the boot warm
                # never bakes (grad_*/spectrum_* etc.).
                if not os.path.isfile(static_path):
                    try:
                        if _disk_write_allowed(static_path, "swatch-static-write"):
                            os.makedirs(os.path.dirname(static_path), exist_ok=True)
                            with open(static_path, 'wb') as sf:
                                sf.write(png_bytes)
                    except Exception as snap_err:
                        logger.debug(f"Picker split static snapshot write failed [{finish_type}/{finish_key}]: {snap_err}")

            return Response(png_bytes, mimetype='image/png', headers=cache_headers)

        if not nocache and os.path.isfile(disk_path):
            try:
                with open(disk_path, 'rb') as disk_file:
                    return Response(disk_file.read(), mimetype='image/png', headers=cache_headers)
            except Exception as _spb_ex:
                _spb_swallow('api_swatch@L456', _spb_ex)

        def _pre_path_for_key(key):
            safe = (key or '').replace('/', '_').replace('\\', '_').replace(':', '_').replace('-', '_').strip() or 'none'
            return os.path.join(thumbnail_dir_getter(), finish_type, safe + '.png')

        pre_path = None
        if allow_prerender and mode != 'split' and finish_type in ('base', 'pattern', 'monolithic'):
            safe_key = (finish_key or '').replace('/', '_').replace('\\', '_').replace(':', '_').strip() or 'none'
            pre_path = os.path.join(thumbnail_dir_getter(), finish_type, safe_key + '.png')
            if not os.path.isfile(pre_path):
                alt_path = _pre_path_for_key(finish_key)
                if os.path.isfile(alt_path):
                    pre_path = alt_path

        if pre_path is None or not os.path.isfile(pre_path):
            with swatch_cache_lock:
                if not nocache and cache_key in swatch_cache:
                    return Response(swatch_cache[cache_key], mimetype='image/png', headers=cache_headers)

        if allow_prerender and mode != 'split' and finish_type in ('base', 'pattern', 'monolithic'):
            if os.path.isfile(pre_path):
                try:
                    mtime = int(os.path.getmtime(pre_path))
                    prerender_cache_key = f"prerender:{finish_type}:{finish_key}:{size}:{mtime}"
                    with swatch_cache_lock:
                        if prerender_cache_key in swatch_cache:
                            return Response(swatch_cache[prerender_cache_key], mimetype='image/png', headers=cache_headers)
                    from PIL import Image as PILImage
                    with open(pre_path, 'rb') as pre_file:
                        img = PILImage.open(pre_file).convert('RGB')
                    if img.size != (size, size):
                        img = img.resize((size, size), PILImage.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format='PNG', optimize=True)
                    png_bytes = buf.getvalue()
                    with swatch_cache_lock:
                        swatch_cache[prerender_cache_key] = png_bytes
                    return Response(png_bytes, mimetype='image/png', headers=cache_headers)
                except Exception as e:
                    logger.debug(f"Pre-rendered thumbnail failed [{finish_type}/{finish_key}]: {e}")

        try:
            if finish_type == 'monolithic' and callable(quality_write_guard):
                quality_write_guard([(finish_type, finish_key)])
            png_bytes = render_swatch_bytes(finish_type, finish_key, color_hex, size, seed)
        except Exception as e:
            logger.warning(f"/api/swatch failed [{finish_type}/{finish_key}]: {e}")
            logger.debug(f"Swatch traceback: {traceback.format_exc()}")
            status_code = 404 if isinstance(e, ValueError) and str(e).startswith("Unknown swatch") else 500
            return jsonify({
                "error": "swatch_render_failed",
                "type": finish_type,
                "key": finish_key,
                "message": str(e),
            }), status_code

        with swatch_cache_lock:
            swatch_cache[cache_key] = png_bytes

        try:
            if _disk_write_allowed(disk_path, "swatch-cache-write"):
                os.makedirs(swatch_cache_dir, exist_ok=True)
                with open(disk_path, 'wb') as disk_file:
                    disk_file.write(png_bytes)
        except Exception as _spb_ex:
            _spb_swallow('api_swatch@L522', _spb_ex)

        return Response(png_bytes, mimetype='image/png', headers=cache_headers)

    def _api_swatch_test_impl(finish_key):
        """Render ONE monolithic at 256x256 and return PNG."""
        size = 256
        engine = engine_getter()
        if finish_key not in getattr(engine, 'MONOLITHIC_REGISTRY', {}):
            return jsonify({"error": f"Unknown monolithic: {finish_key}"}), 404
        try:
            png_bytes = render_swatch_bytes('monolithic', finish_key, '888888', size, 42)
            return Response(png_bytes, mimetype='image/png', headers={'Cache-Control': 'no-store'})
        except Exception as e:
            logger.exception(f"swatch-test {finish_key}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/swatch-test/<finish_key>', methods=['GET'])
    def api_swatch_test(finish_key):
        """Render ONE monolithic at 256x256 and return PNG."""
        return _api_swatch_test_impl(finish_key)

    @app.route('/api/swatch_test/<finish_key>', methods=['GET'])
    def api_swatch_test_underscore(finish_key):
        """Same as swatch-test; underscore URL for compatibility."""
        return _api_swatch_test_impl(finish_key)

    @app.route('/swatch/<base_id>/<pattern_id>')
    def get_swatch(base_id, pattern_id):
        """Generate a 64x64 swatch thumbnail for a base+pattern finish combination."""
        try:
            from PIL import Image as PILImage
            import numpy as np

            engine = engine_getter()
            if base_id not in engine.BASE_REGISTRY:
                return jsonify({"error": f"Unknown base: {base_id}"}), 404
            if pattern_id != "none" and pattern_id not in engine.PATTERN_REGISTRY:
                return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

            cache_file = os.path.join(swatch_folder_getter(), f"{base_id}_{pattern_id}.png")
            if os.path.exists(cache_file):
                return send_file(cache_file, mimetype='image/png')

            render_shape = (128, 128)
            output_size = (64, 64)
            mask = np.ones(render_shape, dtype=np.float32)
            spec = engine.compose_finish(base_id, pattern_id, render_shape, mask, 51, 1.0)

            metallic = spec[:, :, 0].astype(np.float32) / 255.0
            roughness = spec[:, :, 1].astype(np.float32) / 255.0
            clearcoat = np.clip(1.0 - spec[:, :, 2].astype(np.float32) / 64.0, 0, 1)

            r = np.clip(0.3 + metallic * 0.5 - roughness * 0.15 + clearcoat * 0.1, 0, 1)
            g = np.clip(0.3 + metallic * 0.45 - roughness * 0.15 + clearcoat * 0.15, 0, 1)
            b = np.clip(0.35 + metallic * 0.4 - roughness * 0.1 + clearcoat * 0.2, 0, 1)

            rgb = np.stack([r, g, b], axis=2)
            img = PILImage.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), 'RGB')
            img = img.resize(output_size, PILImage.LANCZOS)
            return _serve_generated_png(img, cache_file)

        except Exception as e:
            logger.error(f"Swatch error {base_id}/{pattern_id}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/swatch/pattern/<pattern_id>')
    def get_pattern_swatch(pattern_id):
        """Generate a 64x64 swatch showing the actual pattern texture."""
        try:
            from PIL import Image as PILImage
            import numpy as np

            engine = engine_getter()
            if pattern_id not in engine.PATTERN_REGISTRY:
                return jsonify({"error": f"Unknown pattern: {pattern_id}"}), 404

            registry = engine.PATTERN_REGISTRY[pattern_id]
            tex_fn = registry.get("texture_fn")
            if tex_fn is None:
                return jsonify({"error": f"Pattern has no texture renderer: {pattern_id}"}), 500

            cache_file = os.path.join(swatch_folder_getter(), f"pat_{pattern_id}.png")
            if os.path.exists(cache_file):
                return send_file(cache_file, mimetype='image/png')

            render_shape = (256, 256)
            output_size = (64, 64)
            mask = np.ones(render_shape, dtype=np.float32)

            sig = inspect.signature(tex_fn)
            n_params = len(sig.parameters)
            if n_params >= 4:
                tex = tex_fn(render_shape, mask, 42, 1.0)
            elif n_params >= 2:
                tex = tex_fn(render_shape, 42)
            else:
                tex = tex_fn(render_shape)

            if isinstance(tex, dict):
                pv = tex.get("pattern_val", np.zeros(render_shape, dtype=np.float32))
                m_pat = tex.get("M_pattern")
                r_pat = tex.get("R_pattern")
            else:
                pv = tex if isinstance(tex, np.ndarray) else np.zeros(render_shape, dtype=np.float32)
                m_pat = None
                r_pat = None

            if pv.shape != render_shape:
                pv_img = PILImage.fromarray((np.clip(pv, 0, 1) * 255).astype(np.uint8))
                pv_img = pv_img.resize(render_shape, PILImage.LANCZOS)
                pv = np.array(pv_img, dtype=np.float32) / 255.0

            swatch_color = registry.get("_swatch_rgb")
            if swatch_color is None:
                tint_r, tint_g, tint_b = 0.55, 0.65, 0.85
            else:
                tint_r, tint_g, tint_b = swatch_color

            if m_pat is not None and r_pat is not None:
                m_pat = np.asarray(m_pat, dtype=np.float32)
                r_pat = np.asarray(r_pat, dtype=np.float32)
                m_p = np.clip(m_pat, 0, 1) if m_pat.shape == render_shape else np.clip(pv, 0, 1)
                r_p = np.clip(r_pat, 0, 1) if r_pat.shape == render_shape else np.clip(1.0 - pv, 0, 1)
                brightness = m_p * 0.6 + (1.0 - r_p) * 0.4
                r = np.clip(brightness * tint_r + 0.1, 0, 1)
                g = np.clip(brightness * tint_g + 0.08, 0, 1)
                b = np.clip(brightness * tint_b + 0.12, 0, 1)
            else:
                pv_n = np.clip(pv, 0, 1)
                r = np.clip(pv_n * tint_r * 0.8 + 0.12, 0, 1)
                g = np.clip(pv_n * tint_g * 0.8 + 0.10, 0, 1)
                b = np.clip(pv_n * tint_b * 0.8 + 0.14, 0, 1)

            rgb = np.stack([r, g, b], axis=2)
            img = PILImage.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), 'RGB')
            img = img.resize(output_size, PILImage.LANCZOS)
            return _serve_generated_png(img, cache_file)

        except Exception as e:
            logger.error(f"Pattern swatch error {pattern_id}: {e}")
            logger.debug(f"Pattern swatch traceback: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @app.route('/swatch/mono/<finish_id>')
    def get_mono_swatch(finish_id):
        """Generate a swatch for a monolithic finish."""
        try:
            from PIL import Image as PILImage
            import numpy as np

            engine = engine_getter()
            if finish_id not in engine.MONOLITHIC_REGISTRY:
                return jsonify({"error": f"Unknown monolithic: {finish_id}"}), 404

            cache_file = os.path.join(swatch_folder_getter(), f"{swatch_cache_token()}_mono_{finish_id}.png")
            if os.path.exists(cache_file):
                return send_file(cache_file, mimetype='image/png')

            if callable(quality_write_guard):
                quality_write_guard([('monolithic', finish_id)])

            render_size = (256, 256)
            output_size = (64, 64)
            shape = render_size
            mask = np.ones(shape, dtype=np.float32)
            entry = engine.MONOLITHIC_REGISTRY[finish_id]
            if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                spec_fn, paint_fn = entry[0], entry[1]
            elif isinstance(entry, dict):
                spec_fn, paint_fn = entry.get("spec_fn"), entry.get("paint_fn")
            elif callable(entry):
                spec_fn, paint_fn = None, entry
            else:
                spec_fn, paint_fn = None, None
            if not callable(spec_fn) or not callable(paint_fn):
                return jsonify({"error": f"Finish has no swatch renderer: {finish_id}"}), 404

            spec = normalize_spec_result_to_rgba(
                invoke_monolithic_spec_fn(spec_fn, shape, mask, 51, 1.0, reg_entry=entry),
                shape,
                strict_shapes=True,
            )
            if spec is None:
                raise RuntimeError(f"Monolithic swatch spec renderer returned no spec data: {finish_id}")

            neutral = np.ones((render_size[0], render_size[1], 3), dtype=np.float32) * 0.5
            painted = paint_fn(neutral, shape, mask, 51, 1.0, 0.10)

            metallic = spec[:, :, 0].astype(np.float32) / 255.0
            roughness = spec[:, :, 1].astype(np.float32) / 255.0

            paint_rgb = np.clip(painted, 0, 1)
            brightness = 0.6 + metallic * 0.4 - roughness * 0.2
            result = paint_rgb * brightness[:, :, None]

            img = PILImage.fromarray((np.clip(result, 0, 1) * 255).astype(np.uint8), 'RGB')
            if render_size != output_size:
                img = img.resize(output_size, PILImage.LANCZOS)
            return _serve_generated_png(img, cache_file)

        except Exception as e:
            logger.error(f"Mono swatch error {finish_id}: {e}")
            return jsonify({"error": str(e)}), 500
