"""Bounded, canonical applied-material inspector for spec-only overlays."""
import io,json,math
from functools import lru_cache
from flask import request,send_file,jsonify

def register_spec_overlay_routes(app):
    @lru_cache(maxsize=48)
    def cached(pid,kind,size,seed,reference,strength,settings,fingerprint):
        from engine.spec_overlay_v2.preview import image
        out=io.BytesIO();image(pid,kind,size,seed,reference,strength,json.loads(settings)).save(out,format='PNG');return out.getvalue()

    @app.get('/api/spec-overlay-inspect/<pid>/<kind>')
    def spec_overlay_inspect(pid,kind):
        from engine.spec_patterns import PATTERN_CATALOG
        from engine.spec_overlay_v2.preview import REFERENCES,dependency_fingerprint
        if pid not in PATTERN_CATALOG or kind not in ('channels','combined','visual','whole'):return jsonify(error='Unknown material preview'),404
        try:
            size=max(64,min(768,int(request.args.get('size',384))));seed=max(0,min(2147483647,int(request.args.get('seed',42))))
            strength=float(request.args.get('strength',1));reference=request.args.get('reference','neutral')
            if not math.isfinite(strength):raise ValueError('strength')
            strength=max(0.,min(1.,strength))
            settings=json.loads(request.args.get('settings','{}'))
            if not isinstance(settings,dict):raise ValueError('settings')
            allowed={'scale':(.05,5),'rotation':(-360,360),'offset_x':(0,1),'offset_y':(0,1),'box_size':(1,100),'range':(0,100)}
            clean={}
            for key,(lo,hi) in allowed.items():
                if key in settings:
                    value=float(settings[key])
                    if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(key)
                    clean[key]=value
            if 'channels' in settings:
                if not isinstance(settings['channels'],str) or any(c not in 'MRC' for c in settings['channels']):raise ValueError('channels')
                clean['channels']=settings['channels']
            if 'params' in settings:
                if not isinstance(settings['params'],dict) or len(settings['params'])>32:raise ValueError('params')
                if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in settings['params'].values()):raise ValueError('params')
                clean['params']=settings['params']
            if 'blend_mode' in settings:
                if settings['blend_mode'] not in ('normal','multiply','screen','overlay','hardlight','softlight'):raise ValueError('blend')
                clean['blend_mode']=settings['blend_mode']
            clean['muted']=bool(settings.get('muted',False));settings=json.dumps(clean,sort_keys=True)
            if reference not in REFERENCES:raise ValueError('reference')
        except (TypeError,ValueError,OverflowError):return jsonify(error='Invalid preview settings'),400
        data=cached(pid,kind,size,seed,reference,strength,settings,dependency_fingerprint(PATTERN_CATALOG[pid]))
        return send_file(io.BytesIO(data),mimetype='image/png',max_age=0)
