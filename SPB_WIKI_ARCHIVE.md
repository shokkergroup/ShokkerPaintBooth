# SPB Living Wiki — ARCHIVE INDEX

**What this is:** the complete historical contents of `SPB_WIKI.html`. **Nothing was ever deleted** — every original byte is preserved verbatim in the files below.

The Living Wiki has been consolidated twice: **2026-07-19** (2.62 MB → 186 KB) and **2026-09-04** (1.37 MB → 383 KB, while *adding* three new sections). Both times the cause was the same: finished work never left the page.

---

## 2026-09-04 rollup

| File | Size | Contents |
|---|---|---|
| [`docs/wiki_archive/daily_log_full_2026-09-04_rollup.md`](docs/wiki_archive/daily_log_full_2026-09-04_rollup.md) | 1.01 MB | **All 220** Daily Work Log entries verbatim. The log had reached 1.02 MB — 75% of the whole wiki — and many entries were *per-run* on a single lane (the 2026-08-31 Houdini lane alone contributed ~26), which the lean mandate forbids. The wiki now keeps the **30 newest (day, agent, lane) groups at ≤6 bullets each**, plus a **76-row** compact history table covering the rest. |
| [`docs/wiki_archive/agent_board_full_2026-09-04.md`](docs/wiki_archive/agent_board_full_2026-09-04.md) | 85 KB | All **50** Agent Coordination Board rows with complete scope/files/status cells, before compression to **9 active lanes** + a *Recently shipped* list. |

Also on 2026-09-04, the **project root** was cut from **469 entries → 205**. ~30 GB of closed-lane scratch moved to `_archive/root_cleanup_2026-09-04/` (see its `MANIFEST.md`); only regenerable caches/logs (~138 MB) were deleted.

---

## 2026-07-19 consolidation

| File | Size | Contents |
|---|---|---|
| [`docs/wiki_archive/daily_log_full_2026-05-29_to_2026-07-19.md`](docs/wiki_archive/daily_log_full_2026-05-29_to_2026-07-19.md) | 1.63 MB | All **336** daily-log entries, 2026-05-29 → 2026-07-19, verbatim. Every Smart TGA cycle (560–740), every SHOKK FORGE run, every SPB-93 tool pass, every finish/catalog session. |
| [`docs/wiki_archive/agent_board_full.md`](docs/wiki_archive/agent_board_full.md) | 749 KB | All **397** Agent Coordination Board lanes with their complete scope, file-lane and status cells. |
| [`docs/wiki_archive/daily_log_full_2026-07-13_to_2026-07-22.md`](docs/wiki_archive/daily_log_full_2026-07-13_to_2026-07-22.md) | 104 KB | The next **46** entries, rolled out 2026-08-09 when the log hit 76 entries / 542 KB. |
| [`docs/wiki_archive/let_freedom_ring_campaign.md`](docs/wiki_archive/let_freedom_ring_campaign.md) | 90 KB | The "Let Freedom Ring — Next Big Update" campaign document (once pinned as the wiki's first section). |
| [`docs/wiki_archive/spec_sculpt_lane_2026-08-08_to_09_full.md`](docs/wiki_archive/spec_sculpt_lane_2026-08-08_to_09_full.md) | 43 KB | The SPEC SCULPT lane narrative — it had grown into a **43 KB single bullet** under *Recently shipped*: a diary inside an ownership table. |
| [`docs/wiki_archive/postmortems_full.md`](docs/wiki_archive/postmortems_full.md) | 38 KB | The complete original post-mortem write-ups. The wiki keeps the compressed lessons. |
| [`docs/wiki_archive/finish_audit_log_full.md`](docs/wiki_archive/finish_audit_log_full.md) | 11 KB | The full finish audit log. |

**Pre-2026-07-19 snapshot of the whole page:** `_archive/root_cleanup_2026-09-04/misc/SPB_WIKI.html.backup-20260717`

---

## Searching it

```bash
grep -rn "fm_basalt"     docs/wiki_archive/
grep -rn "Cycle 740"     docs/wiki_archive/daily_log_full_*.md
grep -rn "base_strength" docs/wiki_archive/
```

**Search here before assuming something is lost.** It almost never is.

---

## Keeping the wiki lean (owner mandate)

1. **Board rows are ownership, not a diary.** One row per *active* lane; compress a closed lane to one sentence under *Recently shipped* and delete the row.
2. **ONE log entry per agent, per lane, per day — not per run.** ~6 bullets max. Per-run evidence belongs in your lane's own state/handoff doc.
3. **Past ~30 entries**, roll the oldest into the compact history table and append the full text here.
