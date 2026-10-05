> **SHIPPED 2026-09-05 19:10 local.** Feed live at 10.0.1 (latest.yml sha 31234be2…). Payload 4.11 GB. Remaining owner step: PayHip upload of `ShokkerPaintBooth-10.0.1-Payhip.zip` + changelog from `RELEASE_NOTES_10.0.1.md`. Lessons folded into docs/RELEASE_PROCESS.md.

# DEPLOY NOW — 10.0.1 beta (written 2026-09-05)

**Where things stand.** The public update feed serves **10.0.0**. The local tree is **10.0.1-beta**
and was never staged or published (`.\spb_release.ps1 -Phase verify`, 2026-09-05). So the next
beta **is 10.0.1 as it stands — no version bump**. `VERSION.txt`, `electron-app/package.json`,
`config.py` and `CLIENT_VERSION` already agree (`node scripts/spb_current_state.js --check-version`).

What this beta carries: the three 2026-09-05 fixes (File Picker setting works in a browser tab,
small version badge, visible BASE COLOR lock box) plus everything uncommitted since 10.0.0.
Owner install checklist: `RELEASE_GATE_10.0.1.txt`.

---

## The whole flow — one script, four commands

```powershell
.\spb_release.ps1 -Phase build                    # trust gates + ~1 h build + PayHip kit. No credentials.
.\spb_release.ps1 -Phase stage -UseStoredKey      # uploads payload + stub to R2. Feed UNTOUCHED.
#   -> install the staged stub, walk RELEASE_GATE_10.0.1.txt
.\spb_release.ps1 -Phase activate -UseStoredKey   # type GO. Publishes latest.yml. IRREVERSIBLE.
.\spb_release.ps1 -Phase verify                   # read the feed cold; confirm 10.0.1 is live
```

One-time only: `.\spb_release.ps1 -SaveKey` if `.r2_credentials.xml` is missing (you type the R2
keys; nobody else ever sees them). `-TestKey` shows bucket usage — two ~4.9 GB payloads fit in the
free tier, so delete payloads older than the LIVE one before staging (keep 10.0.0: it is the rollback).

---

## Why `-Phase build` refuses today, and what unblocks each gate

`node scripts/spb_release_preflight.js --mode=prebuild` on 2026-09-05, after the day's fixes:

| Gate | State | What it needs |
|---|---|---|
| version identity | PASS | — |
| context target integrity | PASS | fixed today (an archived doc path in `scripts/spb_context_targets.json`) |
| Layer / Easy suite manifests, Easy featured audit, canonical fixture | PASS | — |
| **runtime mirror sync** | **FAIL** | 0 writable drift, but **242 report-only drifts under `engine/`** (that directory is `check_only` in `scripts/runtime-sync-manifest.json`: `--write` never touches it, "owner converges manually"). Root is the source of truth, so converging = copying root `engine/` over the mirror once you have eyeballed the list: `node scripts/sync-runtime-copies.js --check` (the list), then `robocopy "engine" "electron-app\server\engine" /E /NFL /NDL`, then `--check` must print `no drift detected`. Without this the installer ships stale engine code. |
| **file-budget gate** | **FAIL** | Five files are over their hard ceilings in `scripts/spb_file_budget.js`: `paint-booth-3-canvas.js` 35 364 (ceiling 25 400), `paint-booth-2-state-zones.js` 20 665 (19 200), `js/spb-easy-mode.js` 6 674 (6 500), `shokker_engine_v2.py` 23 543 (19 400), `paint-booth-v2.css` 13 666 (11 850). No beta can meet these without a refactor. **Owner decision:** raise those five ceilings to current size + ~5 % (one reviewable edit, cite this file), or hold the beta. |
| **generated-drift gate** | **FAIL** | `engine/spec_patterns.py` is 37 007 lines vs `maxLines: 13880` in `scripts/spb_generated_drift_guard.js`. Same decision shape: re-baseline with a reason, or hold. |
| **release evidence** | **FAIL** | `_release_evidence/10.0.1/release-evidence.json` does not exist (the 08-23 runs in `_release_evidence/10.0.1-beta/` belong to the previous candidate and old hashes). Produce it: (1) commit the tree — the gate needs the proof to match `git HEAD` with no dirty tracked/untracked files, and the tree has ~2 800 dirty entries incl. ~390 load-bearing untracked runtime files; (2) `node scripts/spb_isolated_verify.js --suite all` (disposable server + Chrome profile, does not touch :59876) — writes a hashed `isolated-proof.json`; (3) write the schema-2 manifest with `version`, `sourceHash`, `gitHead`, isolated-proof path + SHA-256, dated gauntlet PASS/fixture/record (see `docs/RELEASE_PROCESS.md`, "Candidate requirements"); (4) `node scripts/spb_release_evidence_gate.js --mode=source` must PASS. |

**Recommendation.** The three "owner decision" gates (budget ceilings, drift baseline, mirror
convergence) are each a five-minute, reviewable edit. The evidence gate is the real work
(commit + isolated suite + manifest) and it is what makes the release contract mean something.
Do them in this order: commit → converge `engine/` → raise ceilings/baseline with a dated reason →
isolated suite → manifest → `-Phase build`. Do **not** hand-edit gate scripts silently; the
CHANGELOG entry for the release should name each threshold you moved.

---

## If you decide to ship the beta WITHOUT the gauntlet (explicit, documented)

The script has no bypass flag on purpose. The manual path is exactly what the script does minus
the gates, and `deploy_r2.py` still wants an evidence manifest (`--evidence=`) — so a real bypass
is: build by hand, then run the R2 script yourself with the key in your own shell.

```powershell
cd electron-app; $env:SPB_BUNDLE_ALL = "1"; npm run build      # confirm "bundle-all premium bundle: ... MiB" in the log
#   payload must be >= 4.8 GB (decimal) or the finish packs are missing
#   then verify the fixes are in electron-app\dist\win-unpacked\resources\server\  (RELEASE_GATE_10.0.1.txt, section D)
py -3 deploy_r2.py "electron-app\dist" --hold-latest            # stage; needs R2_ENDPOINT / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY in YOUR shell
#   install test -> RELEASE_GATE_10.0.1.txt
py -3 deploy_r2.py "electron-app\dist" --only-latest            # activate. IRREVERSIBLE.
```

Owner-only steps either way: the install test, typing GO / activating, PayHip upload + changelog.
Never publish `latest.yml` before the payload is uploaded AND you have installed it — electron-updater
will not downgrade users who already took a bad update.
