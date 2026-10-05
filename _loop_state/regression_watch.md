=== TRACK D regression watch — 2026-05-27T07:11:45Z ===

[1] SCALE_BASE_MIN should be 0.05 in all 3 paint-booth-2-state-zones.js copies:
194:const SCALE_BASE_MIN = 0.05, SCALE_BASE_MAX = 10.0;
7506:    zones[index].baseScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
194:const SCALE_BASE_MIN = 0.05, SCALE_BASE_MAX = 10.0;
7506:    zones[index].baseScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));
194:const SCALE_BASE_MIN = 0.05, SCALE_BASE_MAX = 10.0;
7506:    zones[index].baseScale = Math.max(SCALE_BASE_MIN, Math.min(SCALE_BASE_MAX, v));

[2] swatch_routes.py should NOT gate on SHOKKER_SWATCH_LIVE_SPLIT:
138:            # Replaces the legacy env-var gate (SHOKKER_SWATCH_LIVE_SPLIT) so the
138:            # Replaces the legacy env-var gate (SHOKKER_SWATCH_LIVE_SPLIT) so the

[3] 3-copy mirror md5 for paint-booth-2-state-zones.js:
26f8439bafa4db11fc1356b44db2e1b4 *paint-booth-2-state-zones.js
26f8439bafa4db11fc1356b44db2e1b4 *electron-app/server/paint-booth-2-state-zones.js
26f8439bafa4db11fc1356b44db2e1b4 *electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js

[4] 3-copy mirror md5 for engine/spec_patterns.py (BUG HUNT reported drift):
0735a2946e5737f4fcd59c30e2d446eb *engine/spec_patterns.py
0735a2946e5737f4fcd59c30e2d446eb *electron-app/server/engine/spec_patterns.py
0735a2946e5737f4fcd59c30e2d446eb *electron-app/server/pyserver/_internal/engine/spec_patterns.py

[5] 3-copy mirror md5 for server.py:
df68e61cee5c10858718b147151aaaab *server.py
df68e61cee5c10858718b147151aaaab *electron-app/server/server.py
df68e61cee5c10858718b147151aaaab *electron-app/server/pyserver/_internal/server.py

=== Mirror-drift wide scan — 2026-05-27T07:53:45Z ===

Comparing root paint-booth-*.js + engine/*.py + key server files against electron-app/server/ and electron-app/server/pyserver/_internal/

  ⚠ DRIFT: engine/paint_v2/iridescent_insects.py
      root: c976dfa17e45f2880e0857203a7c7aa0
      m1:   c976dfa17e45f2880e0857203a7c7aa0
      m2:   8258c529d6e3f19a777d14878699eeae
  ⚠ DRIFT: engine/paint_v2/military_tactical.py
      root: a31b45092ace43d1aaf2fa240f308bcb
      m1:   a31b45092ace43d1aaf2fa240f308bcb
      m2:   33d2aa5b3a243bc09bd82390674e8773
  ⚠ DRIFT: engine/paint_v2/owner_review_carbon_composite.py
      root: 16951fc1bcdbd77d5f751d8cc9224d13
      m1:   16951fc1bcdbd77d5f751d8cc9224d13
      m2:   7ae8807e257b285fe73543159ffeda09
  ⚠ DRIFT: engine/paint_v2/owner_review_oem_automotive.py
      root: a19ef1784edcf2acc7e9f2f66943f11c
      m1:   a19ef1784edcf2acc7e9f2f66943f11c
      m2:   bb0c3eb72ff0b6d6fa043d021bdb68a3
  ⚠ DRIFT: engine/paint_v2/prism_forge.py
      root: 52f534b42c33e303cf2f4276e0327f16
      m1:   52f534b42c33e303cf2f4276e0327f16
      m2:   34f29440fd0ebe0ecf581e2456c86ca3
  ⚠ DRIFT: engine/paint_v2/raw_weathered.py
      root: 8c269214dddb390bdc30593ac47b0b2f
      m1:   8c269214dddb390bdc30593ac47b0b2f
      m2:   87bb68b40f37e8b4d3fc9a91aab4970d
  ⚠ DRIFT: engine/paint_v2/spectrum_shift.py
      root: ae6ce2140a30326b0f6709a91e5e2098
      m1:   ae6ce2140a30326b0f6709a91e5e2098
      m2:   b53395403c8958ab68714be752cc1fc0
  ⚠ DRIFT: engine/paint_v3/paradigm_v3.py
      root: c329ee31afd50106642d8156322c0aa1
      m1:   c329ee31afd50106642d8156322c0aa1
      m2:   a987f9ee8e195b9afedf2874ae7504dd
  ⚠ DRIFT: engine/paint_v3/primitives.py
      root: 230d9e421807bbda2bac24f739fb6c4d
      m1:   230d9e421807bbda2bac24f739fb6c4d
      m2:   30baf6eaa2b82e6c933f42e691449a6c
  ⚠ DRIFT: engine/registry_patches/racing_heritage_reg.py
      root: 1cc56ac569bd37741d4296c2776ba55e
      m1:   1cc56ac569bd37741d4296c2776ba55e
      m2:   68e677248f0dcc81ac3e70fa130c9202

Summary: 153 files in sync · 10 files with drift

=== Mirror-drift fix — root → pyserver/_internal — 2026-05-27T07:54:37Z ===
Root and electron-app/server/ agree; pyserver/_internal/ is stale on 10 files.
Re-mirroring root copies to pyserver/_internal/ ...

  ✓ engine/paint_v2/iridescent_insects.py
  ✓ engine/paint_v2/military_tactical.py
  ✓ engine/paint_v2/owner_review_carbon_composite.py
  ✓ engine/paint_v2/owner_review_oem_automotive.py
  ✓ engine/paint_v2/prism_forge.py
  ✓ engine/paint_v2/raw_weathered.py
  ✓ engine/paint_v2/spectrum_shift.py
  ✓ engine/paint_v3/paradigm_v3.py
  ✓ engine/paint_v3/primitives.py
  ✓ engine/registry_patches/racing_heritage_reg.py

Verifying py_compile on all 10 mirrored files (catches accidental corruption):
  ✓ compile OK: engine/paint_v2/iridescent_insects.py
  ✓ compile OK: engine/paint_v2/military_tactical.py
  ✓ compile OK: engine/paint_v2/owner_review_carbon_composite.py
  ✓ compile OK: engine/paint_v2/owner_review_oem_automotive.py
  ✓ compile OK: engine/paint_v2/prism_forge.py
  ✓ compile OK: engine/paint_v2/raw_weathered.py
  ✓ compile OK: engine/paint_v2/spectrum_shift.py
  ✓ compile OK: engine/paint_v3/paradigm_v3.py
  ✓ compile OK: engine/paint_v3/primitives.py
  ✓ compile OK: engine/registry_patches/racing_heritage_reg.py

=== HTML/JSON mirror drift scan — 2026-05-27T08:08:53Z ===

[1] Check all root *.html + *.json against electron-app/server/ mirror:
  → 7 in sync, 0 drift

[2] Files present in pyserver/_internal/engine/ but NOT at root engine/ (orphans):
> engine/cultural_mortal_shokk.py
> engine/cultural_viva_mexico.py

[3] Files present at root engine/ but NOT in pyserver/_internal/ (would silently miss in packaged build):
< engine/expansions/owner_review_standalone_v2.py
< engine/paint_v3/paradigm_v3_batch_1.py
< engine/paint_v3/paradigm_v3_batch_2.py
< engine/spec_pattern_families/_v2_palette_fix.py

[4] Engine files where electron-app/server/ DIFFERS from both root and pyserver/_internal/ (rarely seen, would mean only one copy is canonical):
  → 0 triple-drift entries

=== TRACK D regression watch — 2026-05-27T09:23:47Z ===

[1] SCALE_BASE_MIN — root: 'SCALE_BASE_MIN = 0.05' · m1: 'SCALE_BASE_MIN = 0.05' · m2: 'SCALE_BASE_MIN = 0.05'
    ✅ all 3 match

[2] swatch_routes.py env-gate ACTIVE? '0' hit(s) — expected 0 (just a comment reference is fine)
    ✅ env-gate removed

[3] 3-copy md5 spot check (recently touched):
    ✅ paint-booth-2-state-zones.js (26f8439bafa4db11fc1356b44db2e1b4)
    ⚠ DRIFT: engine/spec_patterns.py
        root=1e08a498d7b77bf6be198a14a54bb899 · m1=bb47742338b811d98bcababbe2b3cd79 · m2=bb47742338b811d98bcababbe2b3cd79
    ✅ server.py (df68e61cee5c10858718b147151aaaab)
    ✅ server_routes/swatch_routes.py (4a34ce12e96deaa0460a5e01836d4f62)

[4] Re-verify the 10 files I re-mirrored at 07:54 — drift status now:
    ✅ all 10 still in sync

[5] Tick summary: 09:23:49Z regression watch complete.

### 🟡 NEW drift detected — engine/spec_patterns.py

Root copy diverged from both mirror copies between 07:11 and 09:23. Mirrors agree with each other, root is ahead.
    root: 1e08a498d7b77bf6be198a14a54bb899
    m1:   bb47742338b811d98bcababbe2b3cd79
    m2:   bb47742338b811d98bcababbe2b3cd79

**NOT auto-mirrored.** Owner mentioned earlier: 'CODEX is working on the SPEC Maps right now' — auto-mirroring root → mirrors could clobber Codex's in-flight edits, or stamp a partial state across all 3 copies. Owner should:
1. Confirm Codex is done with spec_patterns.py edits
2. Once stable, re-mirror manually: `cp engine/spec_patterns.py electron-app/server/engine/spec_patterns.py` (and pyserver/_internal/ same)
3. Run `scripts/sync-runtime-copies.js --check` (if it exists) for canonical sync

## TICK 8 — py_compile sweep (2026-05-27T10:08:40Z)

Compiling every .py under engine/ + scripts/ + server_routes/ + root *.py to catch silent syntax errors.

[Errno 22] Invalid argument: 'audit_finish_quality.py*'  ⚠ audit_finish_quality.py*
    [Errno 22] Invalid argument: 'audit_finish_quality.py*'

Summary: 335 Python files compiled · 1 failed

### Investigating the 1 'failed' file

Files matching audit_finish_quality.py* (note the trailing wildcard in error msg):
-rwxr-xr-x 1 Ricky's PC 197121 13343 Apr 19 14:37 audit_finish_quality.py*

Is it a literal asterisk in the filename, or is the shell expanding to nothing?
-rwxr-xr-x 1 Ricky's PC 197121    13343 Apr 19 14:37 audit_finish_quality.py*
✓ audit_finish_quality.py compiles cleanly

The 'failed' result was a false positive — the literal trailing '*' in the shell expansion is just the ls -F executable indicator. The 1 'failure' in TICK 8 was a shell-quoting artifact, not a real bug.

True py_compile state: **335/335 files clean** across engine + scripts + server_routes + root.
