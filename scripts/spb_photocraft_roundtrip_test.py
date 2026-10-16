"""End-to-end Edit-in-PhotoCraft round-trip test. Prints ONE verdict line.

    python scripts/spb_photocraft_roundtrip_test.py --cli <photocraft-cli.exe> [--server http://127.0.0.1:59897] [--psd <layered.psd>] [--spec <spec.tga>]

Format part (always): layered PSD -> SPB export format -> PhotoCraft no-op -> read back; then a real edit
(move a layer + hue shift another) -> only those layers may differ, untouched layers max diff must be 0,
alpha of the hue-shifted layer must be unchanged, names/order/groups kept, spec group exact.
Server part (--server): the same through /api/photocraft/export|poll|import|ack on a running SPB server.
Exit code non-zero = FAIL.
"""
import argparse
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from server_routes import photocraft_psd as pcp  # noqa: E402


def src_layers(psd_path):
    from psd_tools import PSDImage
    src = PSDImage.open(psd_path)
    out = []
    for g, l in pcp._walk(src):
        out.append({"name": l.name, "group_path": list(g), "visible": bool(l.visible), "opacity": l.opacity,
                    "blend": pcp.blend_key(l.blend_mode), "clipping": False,
                    "bbox": [l.left, l.top, l.left + l.width, l.top + l.height],
                    "rgba": l.topil().convert("RGBA")})
    return src.width, src.height, out


def cli(exe, *args):
    r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"photocraft-cli {args[0]} failed: {r.stderr[-300:]}")
    return r.stdout


def layer_ids(exe, psd):
    info = json.loads(cli(exe, "info", psd, "--compact"))
    ids = {}

    def w(nodes):
        for n in nodes:
            if n["kind"] == "Group":
                w(n.get("children", []))
            else:
                ids[n["name"]] = n["id"]
    w(info["layers"])
    return ids


def post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Shokker-Internal": "1"})
    return json.load(urllib.request.urlopen(req, timeout=300))


def get(base, path):
    req = urllib.request.Request(base + path, headers={"X-Shokker-Internal": "1"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def png_url(img):
    b = io.BytesIO()
    img.save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", required=True)
    ap.add_argument("--server")
    ap.add_argument("--psd", default=os.path.join(ROOT, "SPB Chevy Truck Starting Example PSD.psd"))
    ap.add_argument("--spec", default="")
    ap.add_argument("--keep", default="")
    a = ap.parse_args()
    work = a.keep or tempfile.mkdtemp(prefix="spb_pc_rt_")
    os.makedirs(work, exist_ok=True)
    W, H, layers = src_layers(a.psd)
    spec = Image.open(a.spec).convert("RGBA") if a.spec else None
    wpsd = os.path.join(work, "work.psd")
    pcp.build_psd(wpsd, W, H, layers, spec)
    base = pcp.read_psd(wpsd)
    fails = []
    # 0. our own writer/reader is exact vs the source layers
    for s, b in zip(layers, base["layers"]):
        mx = pcp.pixel_diff(pcp.layer_full_canvas(s, W, H), pcp.layer_full_canvas(b, W, H))[0]
        if mx or s["name"] != b["name"] or s["bbox"] != b["bbox"]:
            fails.append(f"writer:{s['name']}")
    # 1. no-op through PhotoCraft
    noop = os.path.join(work, "noop.psd")
    cli(a.cli, "convert", wpsd, noop)
    n = pcp.read_psd(noop)
    d0 = pcp.diff_against_baseline(base, n)
    noop_max = max([v["max"] for v in d0["stats"].values()] or [0])
    same_struct = ([l["name"] for l in n["layers"]] == [l["name"] for l in base["layers"]]
                   and [l["group_path"] for l in n["layers"]] == [l["group_path"] for l in base["layers"]]
                   and [l["bbox"] for l in n["layers"]] == [l["bbox"] for l in base["layers"]]
                   and [(l["visible"], l["opacity"], l["blend"]) for l in n["layers"]] == [(l["visible"], l["opacity"], l["blend"]) for l in base["layers"]])
    spec_max = None
    if spec is not None:
        spec_max = int(np.abs(np.array(base["spec"]).astype(int) - np.array(n["spec"]).astype(int)).max())
    if noop_max or not same_struct or d0["added"] or d0["removed"] or spec_max:
        fails.append(f"noop(max={noop_max},struct={same_struct},spec={spec_max})")
    # 2. real edit
    names = [l["name"] for l in base["layers"] if l["bbox"][2] > l["bbox"][0]]
    move_name = "Sponsors" if "Sponsors" in names else names[1 if len(names) > 1 else 0]
    hue_name = "Car Paint" if "Car Paint" in names else names[0]
    ids = layer_ids(a.cli, wpsd)
    edited = os.path.join(work, "edited.psd")
    cli(a.cli, "run", wpsd, "--cmd", "layer.select", "--params", json.dumps({"layer": ids[move_name]}),
        "--cmd", "layer.translate", "--params", '{"dx":40,"dy":0}',
        "--cmd", "layer.select", "--params", json.dumps({"layer": ids[hue_name]}),
        "--cmd", "image.adjustments.hueSaturation", "--params", '{"hue":40,"saturation":10}', "--out", edited)
    e = pcp.read_psd(edited)
    d1 = pcp.diff_against_baseline(base, e)
    changed = sorted(e["layers"][i]["name"] for i in d1["changed"])
    untouched_max = max([d1["stats"][i]["max"] for i in d1["same"]] or [0])
    hue_i = [i for i, l in enumerate(e["layers"]) if l["name"] == hue_name][0]
    bl = base["layers"][d1["pairs"][hue_i]]
    alpha_diff = int(np.abs(pcp.layer_full_canvas(bl, W, H)[:, :, 3].astype(int) - pcp.layer_full_canvas(e["layers"][hue_i], W, H)[:, :, 3].astype(int)).max())
    if changed != sorted([move_name, hue_name]) or untouched_max or alpha_diff or d1["added"] or d1["removed"]:
        fails.append(f"edit(changed={changed},untouched_max={untouched_max},hue_alpha_diff={alpha_diff})")
    srv = ""
    if a.server:
        sres = server_roundtrip(a, W, H, layers, spec, edited, move_name, hue_name, work)
        srv = " " + sres["line"]
        fails += sres["fails"]
    verdict = "PASS" if not fails else "FAIL " + ";".join(fails)
    print(f"PHOTOCRAFT-ROUNDTRIP {verdict} | {len(layers)} layers {W}x{H} | noop max_diff={noop_max} spec_diff={spec_max} struct_kept={same_struct} "
          f"| edit changed={changed} untouched_max_diff={untouched_max} hue_alpha_diff={alpha_diff}{srv}")
    sys.exit(0 if not fails else 1)


def server_roundtrip(a, W, H, layers, spec, edited_psd, move_name, hue_name, work):
    base = a.server.rstrip("/")
    fails = []
    spec_path = ""
    if spec is not None:
        spec_path = os.path.join(work, "spec_in.tga")
        spec.save(spec_path)
    body = {"name": "rt test", "width": W, "height": H, "spec_path": spec_path, "launch": False,
            "layers": [{"id": f"psd_{i}", "name": l["name"], "group_path": l["group_path"], "visible": l["visible"],
                        "opacity": l["opacity"], "blend": l["blend"], "bbox": l["bbox"], "png": png_url(l["rgba"])}
                       for i, l in enumerate(layers)]}
    ex = post(base, "/api/photocraft/export", body)
    if not ex.get("ok"):
        return {"line": "server=export-failed", "fails": ["server-export:" + str(ex.get("error"))]}
    sid, psd = ex["session"], ex["psd_path"]
    p0 = get(base, "/api/photocraft/poll?session=" + sid)
    if p0.get("state") != "waiting":
        fails.append("poll-before:" + str(p0.get("state")))
    time.sleep(1.2)
    # "PhotoCraft saves": overwrite the session PSD with the edited one
    import shutil
    shutil.copy2(edited_psd, psd)
    states = []
    for _ in range(12):
        time.sleep(1.1)
        st = get(base, "/api/photocraft/poll?session=" + sid)["state"]
        states.append(st)
        if st == "saved":
            break
    if states[-1] != "saved":
        fails.append("poll-saved:" + ",".join(states))
    imp = post(base, "/api/photocraft/import", {"session": sid})
    got = sorted(l["name"] for l in imp.get("layers", []) if l["pixels_changed"])
    if got != sorted([move_name, hue_name]):
        fails.append(f"import-changed:{got}")
    # decode returned PNGs and compare to edited PSD pixel for pixel
    e = pcp.read_psd(edited_psd)
    worst = 0
    for l in imp.get("layers", []):
        img = Image.open(io.BytesIO(base64.b64decode(l["png"].split(",", 1)[1]))).convert("RGBA")
        ref = [x for x in e["layers"] if x["name"] == l["name"]][0]
        worst = max(worst, pcp.pixel_diff(np.array(img), np.array(ref["rgba"]))[0])
        if l["bbox"] != ref["bbox"]:
            fails.append("import-bbox:" + l["name"])
    if worst:
        fails.append(f"import-pixels:{worst}")
    if imp.get("unchanged") != len(layers) - 2:
        fails.append(f"unchanged:{imp.get('unchanged')}")
    post(base, "/api/photocraft/ack", {"session": sid})
    p1 = get(base, "/api/photocraft/poll?session=" + sid)
    if p1.get("state") != "waiting":
        fails.append("poll-after-ack:" + str(p1.get("state")))
    return {"line": f"server=ok import_ms={imp.get('ms')} sent_png_layers={sum(1 for l in imp.get('layers', []) if l['png'])} "
                    f"returned_vs_psd_max_diff={worst} session_psd_mb={ex.get('size_mb')}", "fails": fails}


if __name__ == "__main__":
    main()
