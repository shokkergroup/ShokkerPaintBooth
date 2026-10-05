# -*- coding: utf-8 -*-
"""Build IMAGE_FORGE_GUIDE.html — the owner's lookup for Image Forge drops:
every finish id / display name / picker category, searchable. Re-run whenever
categories change. Reads the LIVE registries (same payload the booth uses)."""
import os, sys, json, logging

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
import shokker_engine_v2 as E
import server_routes.finish_catalog_routes as FC


class _FakeApp:
    def route(self, *a, **k):
        def deco(f):
            return f
        return deco


helpers = FC.register_finish_catalog_routes(
    _FakeApp(), engine_getter=lambda: E, cache_headers=lambda r, **k: r,
    logger=logging.getLogger("guide"))
payload = helpers["prewarm"]() if isinstance(helpers, dict) else helpers[1]()

rows = []
for kind in ("specials", "bases", "patterns"):
    for e in payload[kind]:
        rows.append((e["id"], e["name"], e.get("category") or "—", e["type"]))

rows.sort(key=lambda r: (r[3], r[2], r[1]))
trs = "\n".join(
    "<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>"
    % r for r in rows)

html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>IMAGE FORGE GUIDE — finish ids, names, categories</title>
<style>
 body{background:#0d0d16;color:#dfe3ee;font:13px/1.5 'Segoe UI',sans-serif;margin:0;padding:24px;}
 h1{color:#7ce8ff} code{color:#ffd24a;font-size:12px}
 .how{background:#141425;border:1px solid #2a2a4a;border-radius:8px;padding:14px 18px;max-width:980px;margin-bottom:16px}
 .how b{color:#7ce8ff}
 input{width:420px;padding:8px 12px;background:#141425;border:1px solid #2a2a4a;border-radius:6px;color:#fff;font-size:14px;margin-bottom:12px}
 table{border-collapse:collapse;width:100%%;max-width:1100px}
 th,td{padding:5px 12px;border-bottom:1px solid #1d1d33;text-align:left}
 th{color:#7ce8ff;position:sticky;top:0;background:#0d0d16;cursor:default}
 tr:hover td{background:#15152a}
</style></head><body>
<h1>&#127912; IMAGE FORGE GUIDE</h1>
<div class="how">
<b>How to use Image Forge</b> (folder: <code>image_forge\\</code> in the project root):<br>
&bull; <b>Replace a finish:</b> name your square image <code>&lt;finish id&gt;.jpg</code> (exact id from the table below) and drop it in <code>image_forge\\</code>. The folder doesn't matter for replacements — the id decides.<br>
&bull; <b>Brand-new finish:</b> invent a new id (snake_case) and drop the file inside a <b>category subfolder</b>, e.g. <code>image_forge\\spectrum shift\\spectrum_molten_sky.jpg</code> — folder names match the categories below (emoji/case don't matter). New <code>spectrum_*</code> ids at the root auto-join Spectrum Shift.<br>
&bull; Display name for a new id = the filename in Title Case (<code>spectrum_molten_sky</code> &rarr; "Spectrum Molten Sky"). Replacements keep their existing display name.<br>
&bull; Square images; any size (auto-fit at render) — but pre-shrinking to ~1024&times;1024 JPG keeps the install lean.<br>
&bull; FRESH START the app after dropping files. Paint = your art verbatim; the spec map is derived from the image automatically.
</div>
<input id="q" placeholder="filter by id, name or category..." oninput="f()">
<table id="t"><thead><tr><th>finish id (= filename)</th><th>display name</th><th>picker category</th><th>type</th></tr></thead>
<tbody>
%s
</tbody></table>
<script>
function f(){var q=document.getElementById('q').value.toLowerCase();
 document.querySelectorAll('#t tbody tr').forEach(function(tr){
  tr.style.display=tr.textContent.toLowerCase().indexOf(q)>=0?'':'none';});}
</script></body></html>""" % trs

out = os.path.join(ROOT, "IMAGE_FORGE_GUIDE.html")
open(out, "w", encoding="utf-8").write(html)
print("WROTE IMAGE_FORGE_GUIDE.html (%d finishes)" % len(rows))
