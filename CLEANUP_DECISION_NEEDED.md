# SPB Cleanup — Decisions Needed from Ricky

**Status Date:** 2026-03-30
**Cleanup Progress:** Sessions 1–5 complete. All safe, low-risk cleanup done. Remaining items require product/archive decisions.

---

## 🔴 Blockers — Action Needed

### 1. **_archive/ Directory** (4.2 GB)
- **Contents:** Old builds, test images, backups from prior versions
- **Risk:** Very low — no active code depends on it
- **Options:**
  - A) Delete entirely (~4.2 GB saved)
  - B) Compress to single .zip for offsite backup
  - C) Move to external storage (USB, cloud)
- **Recommended:** Option A (delete) unless you have regulatory retention needs
- **Impact:** Agents no longer index archive metadata on every heartbeat

### 2. **output/ Directory** (1.2 GB)
- **Contents:** Likely accumulated render outputs, test results, debug images
- **Risk:** Medium — may contain useful debug data, but likely stale
- **Options:**
  - A) Review and selectively delete files older than 30 days
  - B) Archive to `_archive_output.zip` for offline storage
  - C) Keep (low token impact, takes disk space)
- **Recommended:** Option A (clean stale outputs)
- **Impact:** +100 MB freed, cleaner working directory

### 3. **PayHip-upload/ Directory** (144 MB)
- **Contents:** Upload staging files (possibly test payloads from distribution testing)
- **Risk:** Medium — unclear if still needed for active distribution
- **Status:** Likely from older product phase; probably safe to clean
- **Recommended:** Delete unless actively uploading to PayHip
- **Impact:** +144 MB freed

---

## ✅ Auto-Archivable (by Date)

| File | Earliest Entry | Archivable After | Days Until |
|------|---|---|---|
| **PRIORITIES.md** | 2026-03-28 | 2026-04-04 | 5 days |
| **RESEARCH.md** | 2026-03-28 | 2026-04-11 | 12 days |
| **CHANGELOG.md** | 2026-03-29 | 2026-04-12 | 13 days |

Once these dates pass, I will automatically:
1. Create `PRIORITIES_ARCHIVE.md`, `RESEARCH_ARCHIVE.md`, `CHANGELOG_ARCHIVE.md`
2. Move entries older than the threshold date
3. Keep only recent entries in the active files
4. Update pointers in `MEMORY.md`

---

## 📊 Current Cleanup Achievement

**Total Saved (Sessions 1–5):**
- Disk: ~18.6 MB (logs) + 0.8 MB (scripts) + 0.4 MB (cache) + 0.9 MB (IDE artifacts) = **~20.7 MB**
- Token efficiency: MEMORY.md reduced 91.6% (40.5 KB → 3.4 KB)
- Code quality: 0 blockers; 4 issues flagged for cleanup after ~2026-04-06

**Potential Additional Savings (pending your decision):**
- _archive/ deletion: 4.2 GB
- output/ cleanup: ~100 MB
- PayHip-upload/ deletion: 144 MB
- **Total potential:** ~4.4 GB + token reduction from absent metadata indexing

---

## Next Cleanup Cycle (Starting 2026-04-04)

1. **Auto-archive PRIORITIES.md** entries (7-day rule kicks in)
2. **Scan for new untracked files** (IDE sessions, debug logs)
3. **Clean dead code** in modified files (once 7-day grace passes ~2026-04-06)
4. **Review _staging/ integration** (decide if it can be deleted as fully merged)

---

**Action:** Please reply with decisions on items 1–3 above so cleanup can proceed with full impact.
