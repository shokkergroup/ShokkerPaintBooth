"""Promote one archived class-template history statement to three exact cars."""
from pathlib import Path
import hashlib
import json
import runpy

HERE = Path(__file__).resolve().parent
REVIEW = HERE / "research/oval/arca2025_primary_2026-10-11"
runpy.run_path(str(REVIEW / "verify_evidence.py"), run_name="__main__")
load = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
proposal = load(REVIEW / "proposed-facts.json")
fact = proposal["facts"][0]
ids = ["stockcars2-arcachevy25", "stockcars2-arcaford25", "stockcars2-arcatoyota25"]
assert fact["car_ids"] == ids and fact["topic"] == "custom-paint-restriction"
compiled = load(HERE / "build/knowledge.json")
archived = {c["id"]: c for c in load(REVIEW / "existing-car-entries.json")}
for car in compiled["cars"]:
    if car["id"] in ids:
        parent = archived[car["id"]]
        assert all(car[k] == parent[k] for k in ["name", "paint_folder", "template_metadata"])
sources = {}
for key, source in proposal["sources"].items():
    assert sha((REVIEW / source["source_file"]).read_bytes()) == source["sha256"]
    text = (REVIEW / source["local_text_file"]).read_text(encoding="utf-8").splitlines()
    title = next(line for line in text if "Release Notes [" in line)
    sources[key] = dict(source, title=title, url=source["final_url"],
                        evidence_file=(REVIEW / source["source_file"]).relative_to(HERE).as_posix())
out = HERE / "research/arca2025_primary/runtime_facts.json"
out.parent.mkdir(exist_ok=True)
bundle = {"schema": "spb-car-research-facts/1", "sources": sources, "facts": [fact],
          "unknowns": {cid: ["The2025 manufacturer-art lock note identifies no specific current layer or forced simulator decal; inspect current source/template/output before any change."] for cid in ids},
          "limitations": ["One class history statement applies to three explicitly bound new2025 ARCA models; it is not three independently discovered quirks.",
                          "Older ARCA, Gen4 and NASCAR Chevrolet SS identities are excluded."]}
raw = (json.dumps(bundle, indent=2) + "\n").encode("utf-8")
if out.exists():
    assert out.read_bytes() == raw, "Existing promotion changed; re-review before replacing it"
else:
    assert sha((HERE / "build/knowledge.json").read_bytes()) == load(REVIEW / "review-manifest.json")["compiled_parent_sha256"], "Compiled parent drift; re-review"
    out.write_bytes(raw)
proof = {"pass": True, "promoted_statement": fact["id"], "exact_car_ids": ids,
         "runtime_facts_sha256": sha(raw), "frozen_research_proposal_preserved": True,
         "scope": "One dated source-qualified class-template lock statement, three exact members. No current forced decal, named layer lock, template revision hash, UV authority or editing permission."}
(REVIEW / "promotion-proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"promoted_statements": 1, "exact_class_members": len(ids), "UV_authority": False}))
