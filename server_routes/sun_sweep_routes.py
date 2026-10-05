"""Sun Sweep — angle-flash relight preview routes (2026-06-19).

Relights any finish (its paint albedo + M/R/Cc spec map) under a virtual sun swept across azimuths on
a flat material chip, so SPB's normally-invisible angle-reactive flash plays IN-APP and can be exported
as a looping hero GIF. No 3D/mesh. Engine: engine/spec_sculpt/sun_sweep.py.

Renders the finish to (paint, spec) via the SAME unified path the swatch route uses (handles every
finish-closure signature), so it works on any MONOLITHIC_REGISTRY finish — including the angle-reactive
COLORSHOXX / Money-Shokk flip families. Modeled on server_routes/dual_shift_routes.py.
"""
from __future__ import annotations

import base64
import io
import traceback

from flask import jsonify, request, Response


_SUN_SWEEP_PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Sun Sweep — SPB</title>
<style>
:root{--bg:#0c0d11;--panel:#15161d;--bd:#24252e;--txt:#e8e8ee;--dim:#8a8a99;--accent:#36d0ff;}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:22px}
h1{font-size:24px;margin:.1em 0}.sub{color:var(--dim);margin-bottom:16px}
.row{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.stage{background:#000;border:1px solid var(--bd);border-radius:12px;width:420px;height:420px;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.stage img{width:100%;height:100%;object-fit:cover;image-rendering:auto}
.stage .hint{color:var(--dim);font-size:13px}
.panel{flex:1;min-width:280px;background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:16px}
label{display:block;font-size:12px;color:var(--dim);margin:12px 0 4px}
input[type=text],select{width:100%;background:#0e0f14;border:1px solid var(--bd);color:var(--txt);border-radius:7px;padding:8px}
input[type=range]{width:100%}
.btn{background:var(--accent);color:#03222b;border:0;border-radius:8px;padding:10px 16px;font-weight:700;cursor:pointer;margin-top:14px}
.btn.ghost{background:#22232c;color:var(--txt)}
.quick{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.chip{background:#1c1d25;border:1px solid var(--bd);color:#bfe3cf;border-radius:14px;padding:3px 10px;font-size:12px;cursor:pointer}
.chip:hover{border-color:var(--accent)}
.controls{display:flex;gap:10px;align-items:center;margin-top:10px}
a.dl{color:var(--accent);font-size:13px;display:inline-block;margin-top:10px}
.err{color:#ff7a7a;font-size:13px;margin-top:8px;min-height:1.2em}
</style></head><body><div class="wrap">
<h1>🌅 Sun Sweep</h1>
<div class="sub">Relight a finish under a moving sun — watch the angle-flash that's normally only visible in iRacing. Export a looping hero GIF.</div>
<div class="row">
  <div>
    <div class="stage" id="stage"><span class="hint" id="hint">Pick a finish &amp; hit Sweep</span></div>
    <div class="controls">
      <button class="btn" id="play" disabled>⏸ Pause</button>
      <input type="range" id="scrub" min="0" max="0" value="0" disabled title="Scrub the sun">
    </div>
    <a class="dl" id="dl" style="display:none" download="sun_sweep.gif">⬇ Download hero GIF</a>
  </div>
  <div class="panel">
    <label>Finish ID</label>
    <input type="text" id="fid" list="fidlist" placeholder="e.g. optics2_dvd" value="optics2_dvd">
    <datalist id="fidlist"></datalist>
    <div class="quick" id="quick"></div>
    <label>Frames: <span id="nfv">24</span></label>
    <input type="range" id="nf" min="12" max="36" value="24">
    <label>Sun elevation: <span id="elv">34</span>&deg;</label>
    <input type="range" id="el" min="14" max="60" value="34">
    <label>Chip size: <span id="szv">320</span>px</label>
    <input type="range" id="sz" min="200" max="460" value="320" step="20">
    <button class="btn" id="go">☀ Sweep</button>
    <button class="btn ghost" id="gif">Make GIF</button>
    <div class="err" id="err"></div>
  </div>
</div></div>
<script>
var QUICK=["optics2_dvd","optics2_thinfilm","optics2_holo","optics2_aurora","materials2_titanium","materials2_crystal","grd_iridescent","grd_holo_foil"];
var q=document.getElementById('quick'), dl_=document.getElementById('fidlist');
QUICK.forEach(function(id){var c=document.createElement('span');c.className='chip';c.textContent=id;c.onclick=function(){document.getElementById('fid').value=id;sweep(false);};q.appendChild(c);var o=document.createElement('option');o.value=id;dl_.appendChild(o);});
['nf','el','sz'].forEach(function(k){var s=document.getElementById(k);var v=document.getElementById(k=='nf'?'nfv':k=='el'?'elv':'szv');s.oninput=function(){v.textContent=s.value;};});
var frames=[],idx=0,timer=null,playing=true;
var stage=document.getElementById('stage'),scrub=document.getElementById('scrub'),playBtn=document.getElementById('play'),errEl=document.getElementById('err');
function show(i){if(!frames.length)return;idx=((i%frames.length)+frames.length)%frames.length;var im=stage.querySelector('img')||document.createElement('img');im.src=frames[idx];if(!im.parentNode){stage.innerHTML='';stage.appendChild(im);}scrub.value=idx;}
function play(){stop();playing=true;playBtn.textContent='⏸ Pause';timer=setInterval(function(){show(idx+1);},1000/16);}
function stop(){if(timer){clearInterval(timer);timer=null;}}
playBtn.onclick=function(){if(playing){stop();playing=false;playBtn.textContent='▶ Play';}else play();};
scrub.oninput=function(){stop();playing=false;playBtn.textContent='▶ Play';show(parseInt(scrub.value));};
function sweep(wantGif){
  errEl.textContent='';var fid=document.getElementById('fid').value.trim();if(!fid){errEl.textContent='Enter a finish id';return;}
  document.getElementById('hint')&&(document.getElementById('hint').textContent='Sweeping…');
  var body={finish_id:fid,frames:parseInt(document.getElementById('nf').value),elevation:parseFloat(document.getElementById('el').value),size:parseInt(document.getElementById('sz').value),gif:!!wantGif};
  fetch('/api/sun-sweep',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json();}).then(function(d){
    if(!d||!d.success){errEl.textContent=(d&&d.error)||'Sweep failed';return;}
    frames=d.frames;scrub.max=frames.length-1;scrub.disabled=false;playBtn.disabled=false;idx=0;show(0);play();
    var dle=document.getElementById('dl');if(d.gif){dle.href=d.gif;dle.download=fid+'_sunsweep.gif';dle.style.display='inline-block';}else{dle.style.display='none';}
  }).catch(function(e){errEl.textContent=''+e;});
}
document.getElementById('go').onclick=function(){sweep(false);};
document.getElementById('gif').onclick=function(){sweep(true);};
</script></body></html>"""


def register_sun_sweep_routes(app, *, engine_getter, invoke_monolithic_spec_fn,
                              normalize_spec_result_to_rgba, logger) -> None:

    @app.route('/sun-sweep')
    def sun_sweep_page():
        return Response(_SUN_SWEEP_PAGE, mimetype='text/html')

    def _render_paint_spec(finish_id, size):
        """Render a finish to (paint_rgb float01, spec_u8 HxWx4) — mirrors get_mono_swatch."""
        import numpy as np
        eng = engine_getter()
        reg = getattr(eng, 'MONOLITHIC_REGISTRY', {})
        if finish_id not in reg:
            return None, None, f"Unknown finish: {finish_id}"
        entry = reg[finish_id]
        if isinstance(entry, (tuple, list)) and len(entry) >= 2:
            spec_fn, paint_fn = entry[0], entry[1]
        elif isinstance(entry, dict):
            spec_fn, paint_fn = entry.get("spec_fn"), entry.get("paint_fn")
        elif callable(entry):
            spec_fn, paint_fn = None, entry
        else:
            spec_fn, paint_fn = None, None
        if not callable(spec_fn) or not callable(paint_fn):
            return None, None, f"Finish has no renderer: {finish_id}"
        shape = (size, size)
        mask = np.ones(shape, dtype=np.float32)
        spec = normalize_spec_result_to_rgba(
            invoke_monolithic_spec_fn(spec_fn, shape, mask, 51, 1.0, reg_entry=entry),
            shape, strict_shapes=True,
        )
        if spec is None:
            return None, None, f"Spec renderer returned nothing: {finish_id}"
        neutral = np.ones((size, size, 3), dtype=np.float32) * 0.5
        paint = paint_fn(neutral, shape, mask, 51, 1.0, 0.10)
        paint = np.clip(np.asarray(paint, dtype=np.float32)[:, :, :3], 0.0, 1.0)
        return paint, spec, None

    @app.route('/api/sun-sweep', methods=['POST'])
    def api_sun_sweep():
        """POST {finish_id, size?, frames?, elevation?, gif?, fps?} -> base64 PNG frames (+ optional GIF)."""
        import numpy as np  # noqa: F401
        try:
            data = request.get_json(force=True, silent=True) or {}
            if not isinstance(data, dict):
                return jsonify({"error": "Request body must be a JSON object"}), 400
            finish_id = data.get('finish_id') or data.get('finish')
            if not finish_id:
                return jsonify({"error": "finish_id required"}), 400
            size = max(120, min(480, int(data.get('size', 320))))
            n_frames = max(8, min(48, int(data.get('frames', 24))))
            elevation = float(data.get('elevation', 34.0))
            want_gif = bool(data.get('gif', False))
            fps = max(6, min(30, int(data.get('fps', 16))))

            paint, spec, err = _render_paint_spec(finish_id, size)
            if err:
                return jsonify({"error": err}), 404

            from engine.spec_sculpt import sun_sweep as ss
            frames = ss.sun_sweep(paint, spec, n_frames=n_frames, elevation_deg=elevation)

            from PIL import Image
            out_frames = []
            for f in frames:
                im = Image.fromarray((np.clip(f, 0, 1) * 255).astype('uint8'), 'RGB')
                buf = io.BytesIO()
                im.save(buf, 'PNG', optimize=True)
                out_frames.append('data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'))

            resp = {"success": True, "finish_id": finish_id, "frames": out_frames,
                    "elevation": elevation, "count": len(out_frames)}
            if want_gif:
                gbuf = io.BytesIO()
                ss.frames_to_gif(frames, gbuf, fps=fps, max_size=size)
                resp["gif"] = 'data:image/gif;base64,' + base64.b64encode(gbuf.getvalue()).decode('ascii')
            return jsonify(resp)

        except Exception as e:
            logger.error(f"/api/sun-sweep error: {e}\n{traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500
