"""Exact fresh-install delivery transformation for private MCP candidate."""
import importlib.util
from pathlib import Path

def index_candidate(source):
    script=Path(__file__).resolve().parent/'fresh-install/delivery/candidate_edits.py'
    spec=importlib.util.spec_from_file_location('spb_fresh_delivery_edits',script)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    first = mod.index_edits(source,module_path='../chatgpt/fresh-install/delivery/review/fresh-knowledge-v2.cjs')
    review_spec=importlib.util.spec_from_file_location('spb_fresh_precedence_edits',script.parent/'review/review_edits.py')
    review=importlib.util.module_from_spec(review_spec);review_spec.loader.exec_module(review)
    return review.index_edits(first)
