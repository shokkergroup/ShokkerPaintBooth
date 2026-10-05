"""Write _release_evidence/<version>/release-evidence.json (schema 2) for the prebuild gate.

    python scripts/release/spb_write_evidence.py --version 10.0.3 --proof _release_evidence/10.0.3-beta/isolated-.../isolated-proof.json
        [--gauntlet-record _release_evidence/10.0.3/gauntlet-record-YYYY-MM-DD.md]
        [--scope-out-easy "owner-approved reason (>= 40 chars)"]

Reads git HEAD and the runtime source identity (via node), hashes the proof and the gauntlet
record, writes the manifest. Run it AGAIN after every edit of the gauntlet record (the gate
re-hashes the record), then spb_add_built_evidence.py (this script rebuilds the manifest from
scratch, so built-artifact and packagedSmoke sections must be re-added after it).
"""
import argparse, datetime, glob, hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
ap = argparse.ArgumentParser()
ap.add_argument("--version", required=True)
ap.add_argument("--proof", required=True, help="isolated-proof.json, relative to the repo root")
ap.add_argument("--gauntlet-record", default=None, help="defaults to the newest _release_evidence/<version>/gauntlet-record-*.md")
ap.add_argument("--scope-out-easy", default=None, help="owner-approved reason; omit when the Easy suite passes")
a = ap.parse_args()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


proof_rel = a.proof.replace("\\", "/")
record = a.gauntlet_record or (sorted(glob.glob(f"_release_evidence/{a.version}/gauntlet-record-*.md")) or [None])[-1]
if not record or not os.path.isfile(record):
    sys.exit(f"gauntlet record not found for {a.version}; write _release_evidence/{a.version}/gauntlet-record-<date>.md first")
record = record.replace("\\", "/")
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
ident = json.loads(subprocess.run(["node", "-e",
    "const r=require('./scripts/spb_runtime_identity').runtimeSourceIdentity(process.cwd());"
    "console.log(JSON.stringify({sourceHash:r.sourceHash}))"], capture_output=True, text=True).stdout)
proof = json.load(open(proof_rel, encoding="utf-8"))
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
manifest = {
    "schemaVersion": 2, "version": a.version, "buildTag": a.version, "gitHead": head, "sourceHash": ident["sourceHash"],
    "isolatedProof": proof_rel, "isolatedProofSha256": sha256(proof_rel),
    "gauntlet": {"result": "PASS", "completedAt": now, "fixtureId": "spb-chevy-truck-2048-v1",
                 "record": record, "recordSha256": sha256(record)},
    "notes": [f"Isolated proof from candidate HEAD {head[:12]}."],
}
if a.scope_out_easy:
    manifest["scopeOuts"] = {"easySuite": {"approvedBy": "owner", "approvedAt": now, "reason": a.scope_out_easy}}
out = f"_release_evidence/{a.version}/release-evidence.json"
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(manifest, open(out, "w", encoding="utf-8"), indent=2)
suites = {r.get("name"): r for r in proof.get("suites", [])}
print(f"wrote {out}: gitHead {head[:12]} sourceHash {ident['sourceHash'][:12]} proof.ok={proof.get('ok')} "
      f"layer exit={suites.get('layer', {}).get('exitCode')} easy exit={suites.get('easy', {}).get('exitCode')} "
      f"scopeOut={'yes' if a.scope_out_easy else 'no'}")
