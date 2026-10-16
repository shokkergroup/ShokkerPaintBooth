"""Record private process acceptance without replacing other agents' Wiki lanes."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
heading = '## Listener ownership and cooperative stop — Oct10 22:26EDT'
summary = heading + '''

Private subscription listener now owns its lock by exact instance UUID plus PID; status/stop and terminal cleanup stay bound to that instance. New subscription-control.cjs never kills a PID or automatically clears stale, unreadable, legacy or replacement ownership. Its status explicitly distinguishes process presence and recorded activity from unverified MCP/model availability; PID reuse cannot certify readiness. Model-start counts survive terminal status. A malformed lock is reported as requiring review, not “not running.” Only matching cooperative stop requests take effect; an old request cannot stop a replacement. An idle stop may wait for the bounded local poll; an active read-only worker may finish before its worker deadline. No new turn starts after stop. Pending questions remain committed before inference; stop during claim preserves the exact question without starting a worker.

Actual installed ChatGPT-authenticated private process test on59910: two starts/idle waits/cooperative stops, distinct UUIDs, prior-instance stop ignored by the second process, exit0/owner_stop terminal status, matching stop and lock removed. Zero model inferences/API fallback; pending journal and both original project SHA-256 hashes unchanged. subscription-lifecycle-acceptance.json binds six implementation/test/probe hashes; verify_subscription_lifecycle.py independently checks it. Component tests additionally cover exclusive startup, replacement ownership, stale/unknown/malformed locks, stop during claim and busy completion/failure without another turn. Prior actual read-only recovery and native named-material Send evidence retained. No new paint, saves or outside messages. Bounded proof processes are stopped, not left as background customer services.

Files: subscription-control.cjs, subscription-listener.cjs/core, test_subscription_control.cjs, test_subscription_listener.cjs, probe_subscription_lifecycle.cjs and verify_subscription_lifecycle.py under mcp/chatgpt. Shared Claude-owned sources remain read-only. This closes private idle ownership/stop acceptance, not automatic customer startup/wake, installed Claude parity, safe editing recovery, arbitrary crash recovery or packaging. Review stale locks with process identity and pending scope before any manual removal; never assume PID presence or a stored “waiting” state proves availability. Preserve drafts/uncertain delivery and subscription-only/no API fallback behavior when adopting. Main goal remains ACTIVE through Oct11 13:38:35UTC.

'''
for name in ['REPORT.md', 'SMARTER_AI.md', 'REQUESTS_FOR_CLAUDE.md']:
    p = here / name
    text = p.read_text(encoding='utf-8')
    if heading not in text:
        p.write_text(summary + text, encoding='utf-8')
p = here / 'SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md'
text = p.read_text(encoding='utf-8')
if heading not in text:
    marker = '## Measured continuation work\n'
    assert marker in text
    p.write_text(text.replace(marker, marker + '\n' + summary, 1), encoding='utf-8')
p = root / 'SPB_WIKI.html'
text = p.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('| **Codex — sixteen-hour AI / Offline Helper improvement**'):
        lines[i] = '| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner window ends Oct11 09:38EDT/13:38UTC; smarter online/Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE22:26EDT — exact-instance listener ownership/status/cooperative stop:2 real idle starts/stops, old stop ignored,0 inference, pending/two fixtures exact. Previous4 native Offline/1 native subscription answer retained.290 facts/62 beyond metadata/130 metadata-only; zero UV. Next: customer startup/reconnect, supported writes without replay, Claude adoption. | 2026-10-10 |\n'
text = ''.join(lines)
start = text.index('### 2026-10-10 - Codex: AI and Offline Helper')
end = text.index('\n### ', start + 5)
entry = text[start:end]
first = entry.splitlines()[0]
entry = entry.replace(first, '### 2026-10-10 - Codex: AI and Offline Helper (updated 22:26EDT)', 1)
old = next(line for line in entry.splitlines() if line.startswith('- Online:'))
entry = entry.replace(old, '- Online: private exact-instance ownership/status/cooperative stop passes2 actual idle starts/stops, distinct IDs/old stop ignored,0 models, pending/two fixture hashes unchanged.6 source hashes frozen; `verify_subscription_lifecycle.py` passes. Stale/malformed/replacement locks preserved for review; status does not certify availability. Stop during claim and busy finish/failure without next turn pass components. Prior actual plan recovery and native Send proof retained. Customer startup/wake/reconnect, editing recovery, Claude parity and shared/package adoption remain open; [checkpoint](mcp/chatgpt/SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md).')
old = next(line for line in entry.splitlines() if line.startswith('- Cleanup/sync:'))
entry = entry.replace(old, '- Cleanup/sync: scoped40 documentation/depth/review mirrors current; no runtime adoption implied. Bounded proof processes stopped. Next customer gap: reliable startup/wake/reconnect and supported edits without uncertain replay or idle inference; Claude requests contain exact review files and limits. No new saves; main goal incomplete. Stop/delete continuation and report measured gaps at deadline.')
p.write_text(text[:start] + entry + text[end:], encoding='utf-8')
print(json.dumps({'checkpoint': heading, 'wiki_lane_active': True, 'shared_runtime_adopted': False}))
