"""After the build: record the three distributables + latest.yml in the manifest (the prestage contract).

    python scripts/release/spb_add_built_evidence.py --version 10.0.3

Expects electron-app/dist/nsis-web/*<version>*.nsis.7z, *<version>*Web-Setup.exe, latest.yml and the
PayHip zip ShokkerPaintBooth-<version>-Payhip.zip at the repo root (spb_make_kits.py builds it).
"""
import argparse, glob, hashlib, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--version", required=True); a = ap.parse_args()
VER = a.version
MAN = f"_release_evidence/{VER}/release-evidence.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def one(pattern):
    hits = [p for p in glob.glob(pattern) if VER in os.path.basename(p)]
    assert len(hits) == 1, (pattern, hits)
    return hits[0].replace("\\", "/")


def row(role, path, channels):
    return {"role": role, "channels": channels, "path": path, "bytes": os.path.getsize(path), "sha256": sha256(path)}


updater = one("electron-app/dist/nsis-web/*.nsis.7z")
installer = one("electron-app/dist/nsis-web/*Web-Setup.exe")
payhip = one(f"*-{VER}-Payhip.zip")
latest = "electron-app/dist/nsis-web/latest.yml"
assert os.path.isfile(latest), latest
m = json.load(open(MAN, encoding="utf-8"))
m["distributables"] = [row("updaterPackage", updater, ["r2"]), row("webInstaller", installer, ["r2", "payhip"]), row("payhipBundle", payhip, ["payhip"])]
m["latestYml"] = {"path": latest, "bytes": os.path.getsize(latest), "sha256": sha256(latest),
                  "mappings": {"filesUrl": "webInstaller", "path": "webInstaller", "packagesX64Path": "updaterPackage", "packagesX64File": "updaterPackage"}}
json.dump(m, open(MAN, "w", encoding="utf-8"), indent=2)
for r in m["distributables"]:
    print(f"{r['role']:15s} {r['bytes']/1e9:6.3f} GB  {r['path']}")
print("latest.yml", m["latestYml"]["bytes"], "bytes; manifest updated")
