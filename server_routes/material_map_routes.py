# -*- coding: utf-8 -*-
"""Easy Mode "SHOW ME WHERE" — the real material routing map.  (E28, 2026-08-08)

The WHOLE CAR mix told the buyer "Shokker maps the rest" and then showed them
nothing. Where each material actually lands is decided by real math in
``engine.spec_sculpt.catalog_blend``: per-material affinity built from the
AUTHORED M/R/Cc statistics of each finish (how much flash it has, how textured
it is) crossed with per-pixel cues from the buyer's own paint (luminance,
saturation, local detail), softened at paint boundaries, then iteratively
calibrated so each material's mean coverage equals the share the buyer asked
for.

That is not reproducible in the browser, and an approximation would be a
confident lie — worse than showing nothing. So this route asks the engine for
the same shares the render routes on (``paint_aware_share_maps``, which feeds
``_paint_aware_spatial_shares`` through the same ``_resolved_material_channels``
and ``_material_stat_tuple`` seams the blend uses) and returns them as a small
colour-coded PNG.

  POST /api/material-map
    {paint_file, materials:[{id, registry_type, weight}], seed?}
  ->  {ok, png (data URL), width, height,
       materials:[{id, color, share_pct, leads_pct}]}

``share_pct`` is what the buyer asked for. ``leads_pct`` is the share of pixels
where that material is the DOMINANT one — the two differ honestly (a material
can be present everywhere and lead nowhere), so both are reported rather than
blurring them into one number.

Registered from server.py exactly like the other optional route modules; a
failure here can never block boot.
"""
from __future__ import annotations

import base64
import io
import os
import time
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows

# Four widely separable hues; also distinguishable in the common
# red-green colour deficiencies (orange / blue / yellow / violet).
MAP_COLORS = ['#ff5a3c', '#35c2ff', '#ffd23c', '#a678ff']
ANALYSIS_PX = 384          # the map is a guide, not a bake
ALLOWED_EXT = {'.tga', '.png', '.jpg', '.jpeg', '.bmp', '.psd'}


def register_material_map_routes(app, server_dir=None, logger=None):
    from flask import jsonify, request

    def _log(message):
        try:
            if logger:
                logger.info('[material-map] %s', message)
        except Exception as _spb_ex:
            _spb_swallow('_log@L54', _spb_ex)

    @app.route('/api/material-map', methods=['POST'])
    def api_material_map():
        started = time.time()
        try:
            import numpy as np
            from PIL import Image
            from engine.spec_sculpt.catalog_blend import (
                normalize_catalog_stack,
                paint_aware_share_maps,
            )

            data = request.get_json(force=True, silent=True) or {}
            paint_file = str(data.get('paint_file') or '').strip()
            materials = data.get('materials') or []

            if len(materials) < 2:
                return jsonify({'ok': False,
                                'error': 'A map needs at least two materials — '
                                         'one material covers the whole car.'}), 400
            if not paint_file:
                return jsonify({'ok': False, 'error': 'No paint loaded yet.'}), 400
            if os.path.splitext(paint_file)[1].lower() not in ALLOWED_EXT:
                return jsonify({'ok': False, 'error': 'Unsupported paint file type.'}), 400
            if not os.path.isfile(paint_file):
                return jsonify({'ok': False, 'error': 'That paint file is not on disk.'}), 404

            with Image.open(paint_file) as handle:
                image = handle.convert('RGB')
                width, height = image.size
                ratio = min(1.0, float(ANALYSIS_PX) / float(max(width, height)))
                out_w = max(32, int(round(width * ratio)))
                out_h = max(32, int(round(height * ratio)))
                small = image.resize((out_w, out_h), Image.LANCZOS)
            source = np.asarray(small, dtype=np.float32) / 255.0

            stack = normalize_catalog_stack(materials, max_layers=4)
            # Seed only perturbs the authored noise inside each finish, and the
            # statistics this routes on are plane-wide means/stds, so a fixed
            # seed keeps the map stable between clicks instead of shimmering.
            shares = paint_aware_share_maps(
                source, stack, shape_hw=(out_h, out_w),
                seed=int(data.get('seed') or 51), analysis_px=ANALYSIS_PX,
            )

            lead = np.argmax(shares, axis=0)
            rgba = np.zeros((out_h, out_w, 4), dtype=np.uint8)
            rows = []
            total = float(out_h * out_w)
            for index, (token, weight) in enumerate(stack):
                colour = MAP_COLORS[index % len(MAP_COLORS)]
                red, green, blue = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
                owned = (lead == index)
                # 120, not 170: the point is WHERE each material lands ON THEIR
                # PAINT. At 170 the overlay hid the livery it is annotating.
                rgba[owned] = (red, green, blue, 120)
                rows.append({
                    'id': token.split('::')[-1],
                    'token': token,
                    'color': colour,
                    'share_pct': round(float(weight) * 100.0),
                    'leads_pct': round(float(np.count_nonzero(owned)) / total * 100.0),
                })

            buffer = io.BytesIO()
            Image.fromarray(rgba, mode='RGBA').save(buffer, format='PNG', optimize=True)
            payload = base64.b64encode(buffer.getvalue()).decode('ascii')
            _log('%dx%d map for %d materials in %dms'
                 % (out_w, out_h, len(stack), int((time.time() - started) * 1000)))
            return jsonify({
                'ok': True,
                'png': 'data:image/png;base64,' + payload,
                'width': out_w, 'height': out_h,
                'elapsed_ms': int((time.time() - started) * 1000),
                'materials': rows,
            })
        except Exception as error:                    # never 500 into the UI
            _log('failed: %s' % error)
            return jsonify({'ok': False, 'error': str(error)[:200]}), 200
