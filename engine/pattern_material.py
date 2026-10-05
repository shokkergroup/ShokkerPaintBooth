"""Independent pattern spec plates, using the catalog's existing chrome carrier.

SPB-105 tick5, owner09-07: "100% ... totally taking over ... 0 as default".
No new finish geometry/M7 claim. The selected pattern's existing compiled spec
replaces M/R/Cc linearly; paint opacity/strength and H/S do not alter its spec.
"""
from functools import lru_cache
import numpy as np


def has_pattern_spec(zone):
    if 'pattern_spec_opacity' not in zone:
        return False
    primary = zone.get('pattern') not in (None, '', 'none') and float(zone['pattern_spec_opacity']) > 0
    return primary or any(layer.get('id') not in (None, '', 'none') and
        float(layer.get('spec_opacity', 0)) > 0 for layer in zone.get('pattern_stack', [])[:4])


@lru_cache(maxsize=4)
def _native_pattern_spec(pattern_id, shape, seed):
    from engine.compose import compose_finish
    from shokker_engine_v2 import _parse_intensity
    full = np.ones(shape, np.float32)
    result = compose_finish('chrome', pattern_id, shape, full, seed,
                            _parse_intensity('100')[0], dither=False)
    result = np.asarray(result)[:, :, :3].copy()
    result.setflags(write=False)
    return result


def pattern_spec_plate(pattern_id, shape, seed, mask, *, scale=1., rotation=0.,
                       offset_x=.5, offset_y=.5, flip_h=False, flip_v=False,
                       fit_zone=False):
    from engine.pattern_paint_placement import render_pattern_paint
    plate = _native_pattern_spec(pattern_id, tuple(shape[:2]), int(seed)).astype(np.float32)/255.
    neutral = np.full_like(plate, .5)
    def ink(background, _shape, coverage, _seed, _pm, _bb):
        return background + (plate-.5)*coverage[:, :, None]
    ink._spb_pattern_direct_paint = True
    # Transform the pure material, not a masked car silhouette. Fit is applied
    # with the same destination bounds as the paint plate.
    placed = render_pattern_paint(ink, neutral, shape, np.ones(shape,np.float32),
        seed, 1., 0., scale=scale, rotation=rotation, offset_x=offset_x,
        offset_y=offset_y, flip_h=flip_h, flip_v=flip_v)
    if fit_zone:
        from engine.compose import _fit_pattern_to_mask_bbox
        placed = _fit_pattern_to_mask_bbox(placed, mask)
    return np.clip(placed*255., 0, 255)


def apply_zone_pattern_spec(spec, zone, shape, mask, seed, *, auto_scale=False):
    if spec is None or 'pattern_spec_opacity' not in zone:
        return spec  # Legacy non-app rendering remains unchanged.
    layers=[]
    if zone.get('pattern') not in (None, '', 'none'):
        layers.append(dict(id=zone['pattern'], spec_opacity=zone['pattern_spec_opacity'],
            scale=zone.get('scale',1), rotation=zone.get('rotation',0),
            **{key:zone.get('pattern_'+key, default) for key,default in
               [('offset_x',.5),('offset_y',.5),('flip_h',False),('flip_v',False),('fit_zone',False)]}))
    layers.extend(zone.get('pattern_stack',[])[:4])
    output=None
    for index,layer in enumerate(layers):
        amount=float(np.clip(layer.get('spec_opacity',0),0,1))
        pid=layer.get('id')
        if amount<=0 or pid in (None,'','none'):continue
        fit=bool(layer.get('fit_zone',zone.get('pattern_fit_zone',False)))
        scale=float(layer.get('scale',1))
        if auto_scale and not fit:
            from shokker_engine_v2 import _compute_zone_auto_scale
            scale *= _compute_zone_auto_scale(mask,shape)
        plate=pattern_spec_plate(pid,shape,seed+index*7,mask,
            scale=scale, rotation=float(layer.get('rotation',0)),
            offset_x=float(layer.get('offset_x',.5)),offset_y=float(layer.get('offset_y',.5)),
            flip_h=bool(layer.get('flip_h',False)),flip_v=bool(layer.get('flip_v',False)),fit_zone=fit)
        if output is None:output=np.asarray(spec).astype(np.float32).copy()
        # Destination zone coverage is applied by the dispatcher once, after
        # this replacement. Preserve alpha (the separate lighting mask).
        output[:,:,:3]=output[:,:,:3]*(1-amount)+plate*amount
    return spec if output is None else np.clip(np.rint(output),0,255).astype(np.uint8)
