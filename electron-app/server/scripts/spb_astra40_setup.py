"""Preserve accepted ASTRA evidence before bounded expansion. SPB-105 / W1."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_astra40_work';OUT.mkdir(exist_ok=True)
paths=list((ROOT/'engine/expansions/astra').glob('*.py'))
paths=[p for p in paths if p.name!='__init__.py']
for kind in ('base','picker_split/base'):
    paths+=list((ROOT/'thumbnails'/kind).glob('astra_*.png'))
old=ROOT/'_archive/root_cleanup_2026-09-05/lane_work/_astra_work'
paths+=list(old.glob('astra_*/paint.png'))+list(old.glob('astra_*/spec.png'))
target=OUT/'original_hashes.json'
if not target.exists():
    target.write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
print('Protected originals:',len(json.loads(target.read_text())))
