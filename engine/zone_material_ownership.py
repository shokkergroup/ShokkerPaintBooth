"""Release a promoted source's old Zone footprint when its member moves."""
import math
import numpy as np

def release_source_footprints(mask, zone):
    records=zone.get('material_instances')
    if not isinstance(records,list) or mask is None:
        return mask
    h,w=mask.shape
    output=mask
    for record in records:
        if not isinstance(record,dict) or record.get('version')!=2 or not record.get('isSource'):
            continue
        rect=record.get('sourceBbox');dest=record.get('instanceBbox')
        try:angle=float(record.get('rotation',0))
        except (TypeError,ValueError,OverflowError):continue
        if not math.isfinite(angle):continue
        if not record.get('muted') and rect==dest and angle%360==0:
            continue
        material=record.get('frozenMaterial')
        if material is None:
            master=next((r for r in records if isinstance(r,dict) and r.get('id')==record.get('masterId') and not r.get('detached')),None)
            material=master.get('frozenMaterial') if master else None
        # Legacy/incomplete topology cannot claim and erase source material.
        if not isinstance(material,dict) or material.get('format')!='spb-zone-material/1':
            continue
        try:
            dw,dh=float(record['documentWidth']),float(record['documentHeight'])
            coords=[float(rect[k]) for k in ('x1','y1','x2','y2')]
            if not all(math.isfinite(v) for v in [dw,dh,*coords]) or min(dw,dh)<=0:
                continue
            x1,y1,x2,y2=coords
            if x2<=x1 or y2<=y1:continue
            left,top=max(0,math.floor(x1*w/dw)),max(0,math.floor(y1*h/dh))
            right,bottom=min(w,math.ceil(x2*w/dw)),min(h,math.ceil(y2*h/dh))
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
        if right<=left or bottom<=top or not np.any(output[top:bottom,left:right]):
            continue
        if output is mask:output=mask.copy()
        output[top:bottom,left:right]=0
    return output
