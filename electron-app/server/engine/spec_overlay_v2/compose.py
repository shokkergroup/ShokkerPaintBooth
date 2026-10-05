"""SPB-105 v2 tick 1: apply versioned spec overlays to the completed material.

Owner: 'Do everything you suggested ... BETTER'. Legacy golden movement:
235/235 expected unchanged. New paths share this implementation across single
and stacked bases; Cc=0 is supported and paint arrays never enter this module.
"""
from __future__ import annotations
import numpy as np
from .contract import version,opacity,seed,apply_material

def apply_stacks(spec,primary,options,zone_mask,base_seed,sm,side_masks=None,side_bases=()):
    from engine.spec_patterns import PATTERN_CATALOG
    from engine.compose import _cached_spec_pattern_array,_apply_spec_pattern_to_channels
    from engine.gpu import to_cpu
    # Keep the legacy path zero-work and byte exact. Unknown IDs are handled by
    # the existing catalog resolver; no new fallback material is manufactured.
    keys=('overlay_spec_pattern_stack','third_overlay_spec_pattern_stack',
          'fourth_overlay_spec_pattern_stack','fifth_overlay_spec_pattern_stack')
    groups=[(primary,zone_mask,5000)]
    for index,key in enumerate(keys):
        layers=options.get(key,[]) or []
        mask=(side_masks or {}).get(key)
        if mask is None:mask=np.zeros(spec.shape[:2],np.float32)
        if not np.any(mask) and not (index<len(side_bases) and side_bases[index]):mask=zone_mask
        groups.append((layers,mask,7000+index*1000))
    modern=[(layers,mask,offset) for layers,mask,offset in groups if any(
        version(layer,PATTERN_CATALOG.get(layer.get('pattern','')))>=2 for layer in layers)]
    if not modern:return spec
    planes=[spec[:,:,i].astype(np.float32) for i in range(3)]
    changed=False
    for layers,mask,offset in modern:
        active=[layer for layer in layers if not layer.get('muted')]
        # Solo is saved with the recipe so preview and export cannot disagree.
        solo=any(layer.get('solo') for layer in active)
        mask=np.clip(np.asarray(to_cpu(mask),np.float32),0,1)
        for layer in active:
            fn=PATTERN_CATALOG.get(layer.get('pattern',''))
            if fn is None or version(layer,fn)<2 or (solo and not layer.get('solo')):continue
            amount=opacity(layer,fn);channels=layer.get('channels','MRC')
            if amount==0 or not channels or not np.any(mask):continue
            field=_cached_spec_pattern_array(fn,layer['pattern'],spec.shape[:2],seed(layer,fn,base_seed,offset),
                min(1.,max(0.,float(sm))),layer.get('params',{}),float(layer.get('scale',1)),float(layer.get('rotation',0)),
                float(layer.get('offset_x',.5)),float(layer.get('offset_y',.5)),int(layer.get('box_size',100)))
            if field.ndim==3 and field.shape[2]==4:
                scoped=field.copy();scoped[:,:,3]*=mask
                planes=list(apply_material(scoped,*planes,amount,channels))
            else:
                # A newly added legacy design may opt into v2 placement/seed/
                # no-op semantics while keeping its authored delta fields.
                updated=_apply_spec_pattern_to_channels(field,*planes,float(layer.get('range',40)),amount,
                    layer.get('blend_mode','normal'),channels)
                planes=[a+(b-a)*mask for a,b in zip(planes,updated)]
            changed=True
    if not changed:return spec
    out=spec.copy()
    for i,plane in enumerate(planes):out[:,:,i]=np.rint(np.clip(plane,0,255)).astype(np.uint8)
    return out
