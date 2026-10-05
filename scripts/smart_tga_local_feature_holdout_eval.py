"""Leave-one-out evaluation for reviewed local-feature decal families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_local_features import (
    LocalFeatureReference, extract_local_feature_signature, query_local_feature_library,
)
from scripts.smart_tga_embedding_library import _crop


def evaluate(entries, *, min_similarity=0.20, ambiguity_margin=0.035, min_family_support=2):
    items=[]
    for entry in entries:
        crop,mask=_crop(entry)
        items.append((entry,extract_local_feature_signature(crop,mask)))
    refs=[LocalFeatureReference(str(e["id"]),str(e["family_id"]),str(e["reviewed_owner"]),s) for e,s in items]
    counts={f:sum(str(e["family_id"])==f for e,_ in items) for f in sorted({str(e["family_id"]) for e,_ in items})}
    positives=[];negatives=[]
    for entry,signature in items:
        family=str(entry["family_id"])
        evidence=entry.get("intrinsic_evidence") or {}
        proposed=set(str(value) for value in evidence.get("proposed_owners") or ())
        digit=float(evidence.get("ocr_digit_coverage") or 0.0)
        # A Number-family visual resemblance may only corroborate independent
        # Number evidence. Sponsor/brand proposals with no digit signal cannot
        # be turned into Numbers by appearance alone.
        allow_number_family=("numbers" in proposed or digit>=0.05)
        def compatible(reference):
            return reference.reviewed_owner!="numbers" or allow_number_family
        if counts[family]>=min_family_support+1:
            result=query_local_feature_library(signature,[r for r in refs if r.reference_id!=str(entry["id"]) and compatible(r)],min_similarity=min_similarity,ambiguity_margin=ambiguity_margin,min_family_support=min_family_support)
            positives.append({"id":entry["id"],"expected_family_id":family,"passed":result.status=="corroborated" and result.family_id==family,**result.__dict__})
        result=query_local_feature_library(signature,[r for r in refs if r.family_id!=family and compatible(r)],min_similarity=min_similarity,ambiguity_margin=ambiguity_margin,min_family_support=min_family_support)
        negatives.append({"id":entry["id"],"excluded_family_id":family,"passed":result.status=="abstained",**result.__dict__})
    return {"schema":"smart-tga-local-feature-holdout-v1","family_counts":counts,"number_family_requires_independent_authority":True,"positive_trials":len(positives),"positive_passed":sum(x["passed"] for x in positives),"negative_trials":len(negatives),"negative_passed":sum(x["passed"] for x in negatives),"all_passed":all(x["passed"] for x in positives+negatives),"casts_votes":False,"ownership_authority":False,"positive_results":positives,"negative_results":negatives}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--manifest",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    report=evaluate(json.loads(a.manifest.read_text(encoding="utf-8")).get("entries") or ())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("positive_trials","positive_passed","negative_trials","negative_passed","all_passed","casts_votes","ownership_authority")},indent=2))
    return 0 if report["all_passed"] else 2


if __name__=="__main__": raise SystemExit(main())
