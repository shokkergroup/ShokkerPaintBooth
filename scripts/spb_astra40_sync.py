"""Sync ASTRA-owned runtime paths without converging unrelated finish drift."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    files=['paint-booth-0-finish-data.js','paint-booth-0-catalog-scorecard.js','paint-booth-v2.html',
           'SPB_WIKI.html','thumbnails/picker_split/_manifest.json']
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'engine/expansions/astra').rglob('*.py')]
    for kind in ('base','picker_split/base'):
        files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'thumbnails'/kind).glob('astra_*.png')]
    out=ROOT/'_astra40_work'
    archived=ROOT/'_archive/root_cleanup_2026-09-05/lane_work/_astra40_work'
    if not out.exists() and archived.exists():out=archived
    out.mkdir(exist_ok=True)
    manifest=out/'runtime-sync-astra.json'
    manifest.write_text(json.dumps(dict(schema_version=1,version='2026.09.05-astra',
        source_of_truth='repo_root',targets=['electron-app/server'],files=files,directories=[]),indent=2))
    run=subprocess.run(['node','scripts/sync-runtime-copies.js','--manifest',str(manifest),'--write','--verify','--quiet'],cwd=ROOT,capture_output=True,text=True)
    (out/'sync.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:
        # Windows can memory-map a live module and forbid truncation. Atomic
        # replacement preserves the existing mapping while updating the path.
        # Scope is still exactly the reviewed manifest; no unrelated sync.
        for index,file in enumerate(files):
            source=ROOT/file; target=ROOT/'electron-app/server'/file
            if target.exists() and source.read_bytes()==target.read_bytes():continue
            staged=out/f'mirror-{index}.next'
            staged.write_bytes(source.read_bytes())
            target.parent.mkdir(parents=True,exist_ok=True)
            try:
                os.replace(staged,target)
            except PermissionError:
                # A Windows reader can allow writing while denying rename or
                # truncation. Only use the in-place path when no shortening is
                # needed, retain the old bytes, then require exact SHA parity.
                data=source.read_bytes()
                if not target.exists() or target.stat().st_size>len(data):raise
                (out/f'mirror-{index}.before').write_bytes(target.read_bytes())
                with target.open('r+b') as stream:
                    stream.write(data);stream.flush();os.fsync(stream.fileno())
    hashes={}
    for file in files:
        a=hashlib.sha256((ROOT/file).read_bytes()).hexdigest()
        b=hashlib.sha256((ROOT/'electron-app/server'/file).read_bytes()).hexdigest()
        assert a==b,file
        hashes[file]=a
    (out/'runtime_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(f'ASTRA runtime: {len(hashes)} root/mirror SHA-256 pairs match')
    return 0
if __name__=='__main__':raise SystemExit(main())
