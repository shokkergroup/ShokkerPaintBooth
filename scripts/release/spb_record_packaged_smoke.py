"""Record the owner's install test as packagedSmoke in the manifest (the activate contract).

    python scripts/release/spb_record_packaged_smoke.py --version 10.0.3 --summary "Owner: installed the staged stub in Windows Sandbox ... PASS"
        [--not-clean]      # only if the test was NOT on a clean machine (the gate then FAILS by design)

Writes _release_evidence/<version>/packaged-smoke-<date>.md, hashes it into the manifest, appends a
G9 line to the gauntlet record and re-hashes that record. Then: node scripts/spb_release_evidence_gate.js --mode=activate
"""
import argparse, datetime, glob, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--version", required=True); ap.add_argument("--summary", required=True)
ap.add_argument("--not-clean", action="store_true"); a = ap.parse_args()
VER, clean = a.version, not a.not_clean
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
today = now[:10]
MAN = f"_release_evidence/{VER}/release-evidence.json"
REC = f"_release_evidence/{VER}/packaged-smoke-{today}.md"
GAUNT = (sorted(glob.glob(f"_release_evidence/{VER}/gauntlet-record-*.md")) or [None])[-1]
if not GAUNT:
    sys.exit("gauntlet record missing")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


m = json.load(open(MAN, encoding="utf-8"))
d = {r["role"]: r for r in m["distributables"]}
open(REC, "w", encoding="utf-8").write(
    f"# Packaged install smoke - {VER} - {now}\n\n"
    f"Environment: {'Windows Sandbox (clean machine) via SPB_' + VER + '_sandbox.wsb' if clean else 'NOT a clean machine'}\n"
    f"Installer run: {os.path.basename(d['webInstaller']['path'])} (sha256 {d['webInstaller']['sha256']})\n"
    f"Package fetched: {os.path.basename(d['updaterPackage']['path'])} (sha256 {d['updaterPackage']['sha256']}, {d['updaterPackage']['bytes']} bytes) from the staged R2 object\n\n"
    f"Owner result (verbatim):\n{a.summary}\n\nResult: PASS\n")
m["packagedSmoke"] = {"result": "PASS", "completedAt": now, "cleanMachine": bool(clean), "record": REC, "recordSha256": sha256(REC),
                      "artifactRoles": ["webInstaller", "updaterPackage"]}
open(GAUNT, "a", encoding="utf-8").write(f"\n| G9 owner smoke ({now}) | PASS | {a.summary} Record: {REC} (cleanMachine={clean}) |\n")
m["gauntlet"]["recordSha256"] = sha256(GAUNT)
json.dump(m, open(MAN, "w", encoding="utf-8"), indent=2)
print("packagedSmoke recorded; cleanMachine =", clean, "; gauntlet record re-hashed")
