"""Dump the pinned Foundation spec constants (M, R, CC) from the live engine registry -> enc_foundation_pinned.json.
FACTCHECK 2026-10-04: the atlas 'measured' numbers for base::semi_gloss (60/16) disagree with the registry (55/40); code wins.
Run:  python scripts/ai_atlas/enc_dump_pinned.py   (one engine boot)"""
import sys, os, io, json, contextlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')); os.chdir(ROOT); sys.path.insert(0, ROOT)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import engine
    from engine import base_registry_data as B
ids = ["wet_look", "gloss", "semi_gloss", "satin", "eggshell", "matte", "primer", "flat_black", "f_powder_coat", "f_pearl", "f_satin_pearl", "f_metallic",
       "f_matte_metallic", "f_candy", "f_brushed", "f_frozen", "f_bead_blast", "f_chrome", "f_dark_chrome", "f_satin_chrome"]
out = {i: [engine.BASE_REGISTRY[i]['M'], engine.BASE_REGISTRY[i]['R'], engine.BASE_REGISTRY[i]['CC']] for i in ids if i in engine.BASE_REGISTRY}
json.dump({'_doc': 'Pinned flat Foundation spec (metal, roughness, coat) from engine.BASE_REGISTRY after the pinning pass; code wins over atlas measurements.', 'pinned': out},
          open(os.path.join(ROOT, 'scripts', 'ai_atlas', 'enc_foundation_pinned.json'), 'w'), indent=0)
print(len(out))
