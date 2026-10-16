"""Maintain the bounded SPEC OVERLAYS v2 implementation lane in the Living Wiki."""
from pathlib import Path
import argparse,os,re
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--status',default='Foundation contracts, saved-recipe baseline and shared-picker integration.');parser.add_argument('--log',default='Owner approved the complete 09-05 assessment plan: composition/preview fixes, Bases picker parity, ten families and a distinct library.');parser.add_argument('--complete',action='store_true');parser.add_argument('--postmortem');args=parser.parse_args()
    work=ROOT/'_spec_overlays_v2_work';work.mkdir(exist_ok=True)
    path=ROOT/'SPB_WIKI.html';s=path.read_text(encoding='utf-8')
    row='| **Codex — SPEC OVERLAYS v2 implementation** | Owner 09-06: implement the complete approved overhaul; preserve legacy recipes; shared Bases picker; distinct fine spec-only designs and live verification. | `engine/spec_overlay_v2/`, new overlay modules/catalog/assets/tests/scripts; overlay paths only in `engine/compose.py`, `server.py`, `paint-booth-2-state-zones.js`, `paint-booth-0-finish-data.js`, Bases picker adapters/Atlas, HTML load tokens; owned runtime mirrors; `_spec_overlays_v2_work/`, `docs/SPEC_OVERLAYS_V2_2026-09-06.md`, Wiki. Does not touch the ARCA viewer or other finish lanes. | **ACTIVE — '+args.status+'** | 2026-09-06 |\n'
    marker='| **Codex — SPEC OVERLAYS v2 implementation**'
    if args.complete:row=row.replace('**ACTIVE — ','**COMPLETE — ')
    if marker in s:s=re.sub(r'^\| \*\*Codex — SPEC OVERLAYS v2 implementation\*\*.*\n',lambda m:row,s,count=1,flags=re.M)
    else:
        anchor='| Agent / lane | Scope | Files claimed — don\'t touch if not yours | Status | Updated |\n|---|---|---|---|---|\n';assert anchor in s;s=s.replace(anchor,anchor+row,1)
    heading='### 2026-09-06 — Codex / SPEC OVERLAYS v2 implementation'
    entry=heading+'\n\n'+args.log+'\n\nImplementation state/evidence: `docs/SPEC_OVERLAYS_V2_2026-09-06.md`, `_spec_overlays_v2_work/`.\n'
    if heading in s:
        start=s.index(heading);end=s.find('\n### ',start+len(heading));assert end>start;s=s[:start]+entry+s[end:]
    else:
        anchor='<script type="text/markdown" data-section="dailylog">\n';assert anchor in s;s=s.replace(anchor,anchor+'\n'+entry,1)
    if args.postmortem:
        heading='### 2026-09-06 — SPEC OVERLAYS: live integration traps'
        if heading not in s:
            anchor='<script type="text/markdown" data-section="postmortems">';assert anchor in s
            s=s.replace(anchor,anchor+'\n\n'+heading+'\n\n'+args.postmortem+'\n',1)
    tmp=work/'wiki.next.html';tmp.write_text(s,encoding='utf-8')
    try:os.replace(tmp,path)
    except PermissionError:
        old=path.read_bytes();payload=s.encode('utf-8');(work/'wiki.before.html').write_bytes(old)
        payload+=b' ' * max(0,len(old)-len(payload))
        with path.open('r+b') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        assert path.read_bytes()==payload
        tmp.unlink()
    print(args.status)
if __name__=='__main__':main()
