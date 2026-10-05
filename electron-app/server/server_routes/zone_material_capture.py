"""File-free, atomic native/preview material capture and color matching."""
import copy

class MaterialCapture:
    def __init__(self, request, zones):
        if not isinstance(request, dict) or type(request.get('zoneIndex')) is not int or request['zoneIndex'] < 0:
            raise ValueError('Invalid material capture Zone')
        self.batch = 'ids' in request
        self.ids = request.get('ids') if self.batch else [request.get('id')]
        if not isinstance(self.ids,list) or not 0<len(self.ids)<=256 or any(not isinstance(x,str) or not x for x in self.ids) or len(set(self.ids))!=len(self.ids):
            raise ValueError('Invalid material copy selection')
        self.id = self.ids[0]
        self.appearance = request.get('appearance')
        if self.appearance is not None:
            from engine.zone_material_appearance import MODES
            if self.appearance not in MODES:raise ValueError('Unknown material color operation')
        selected=[];index=None
        for target_id in self.ids:
            matches=[(i,z,r) for i,z in enumerate(zones) for r in z.get('material_instances',[]) if isinstance(r,dict) and r.get('version')==2 and r.get('id')==target_id]
            if len(matches)!=1:raise ValueError('Material copy is missing or ambiguous')
            current_index,self.zone,record=matches[0]
            if index is not None and index!=current_index:raise ValueError('Select copies in one Zone')
            index=current_index;selected.append(record)
        self.references={}
        capture_ids=list(self.ids)
        if self.appearance is not None:
            records=self.zone['material_instances'];canonical={}
            for record in selected:
                master_id=record.get('masterId')
                if master_id:
                    if not any(isinstance(r,dict) and r.get('id')==master_id and not r.get('detached') for r in records):
                        raise ValueError('Material master is missing')
                else:
                    rect=record.get('renderSourceBbox',record.get('sourceBbox'))
                    key=repr((rect,record.get('documentWidth'),record.get('documentHeight')))
                    master_id=canonical.get(key)
                    if master_id is None:
                        master_id='__material_reference_'+str(len(canonical))
                        while any(isinstance(r,dict) and r.get('id')==master_id for r in records):master_id+='x'
                        records.append(dict(version=2,id=master_id,sourceBbox=copy.deepcopy(rect),instanceBbox=copy.deepcopy(rect),
                            documentWidth=record.get('documentWidth'),documentHeight=record.get('documentHeight')))
                        canonical[key]=master_id
                self.references[record['id']]=master_id
                if master_id not in capture_ids:capture_ids.append(master_id)
        self.zone['_material_capture_ids'] = capture_ids
        # preview_render resizes masks in-place; retain exact native inputs.
        self.native_zones = copy.deepcopy(zones)
        self.native_zone = self.native_zones[index]

    def _level(self,zone):
        captures=zone.get('_material_captures',{});result={};stats={}
        for target_id in self.ids:
            captured=captures.get(target_id)
            if captured is None:raise ValueError('Material copy could not be captured')
            if self.appearance is not None:
                from engine.zone_material_appearance import match_material
                master=captures.get(self.references[target_id])
                if master is None:raise ValueError('Material master could not be captured')
                captured,stats[target_id]=match_material(captured,master,self.appearance)
            result[target_id]=captured
        return result,stats

    def finish(self, result, preview_scale, render, paint_file, **options):
        paint, spec, elapsed = result
        captures,stats = self._level(self.zone)
        if preview_scale < 1.0:
            previews={k:dict(documentWidth=paint.shape[1],documentHeight=paint.shape[0],material=v) for k,v in captures.items()}
            preview_stats=stats
            paint, spec, elapsed = render(paint_file, self.native_zones, preview_scale=1.0, **options)
            captures,stats=self._level(self.native_zone)
            for target_id,captured in captures.items():
                captured['preview']=previews[target_id]
                if target_id in stats:stats[target_id]['previewChangedPixels']=preview_stats[target_id]['changedPixels']
        if self.appearance is not None:
            for target_id,captured in captures.items():captured['operation']=dict(mode=self.appearance,**stats[target_id])
        response=dict(success=True,resolution=[paint.shape[1],paint.shape[0]])
        response['material_captures' if self.batch else 'material_capture']=captures if self.batch else captures[self.id]
        return response

def prepare_capture(value, zones):
    return None if value is None else MaterialCapture(value,zones)
